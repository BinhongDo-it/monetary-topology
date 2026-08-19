#!/usr/bin/env python3
"""B8 core table: parse the Fannie archives once, answer questions from numpy.

**Why this exists.** Measured on a synthetic 113-field file of the same shape as
the real one, the split is::

    parse, ``line.split(b"|")`` over 113 fields   0.21 M rows/s   93 per cent
    per-segment python work (cluster + arithmetic) 0.49 us/month     7 per cent

``maxsplit=108`` buys 6 per cent and is not worth having. ``pandas.read_csv``
with ``usecols`` is **four times slower**, because the C parser still tokenises
all 113 fields and then builds python objects for them. So the parse is the whole
cost, and the fix is to pay it once.

**And the reason that matters more than speed.** ``b8_c8_arithmetic.py``,
``b8_c8_1c_contract_payment.py`` and ``b8_c8_1c_contract_payment_b.py`` have each
hand-written the same quiet-month filter. One transcription slip and the three
readings stop being comparable **while every count stays plausible and every gate
still passes**. That is the shape of the A21 partition bug and of
``MEASUREMENT.md``'s eighth failure mode. ``quiet_pairs`` below is the single
copy, and a stage that wants a different filter writes a different function
rather than editing this one.

Layout::

    data/processed/fannie_core/v1/<archive>/
        manifest.json       source zip name, size, CRC, row and loan counts,
                            the field-position table, dtypes, byte order
        row_<name>.bin      one file per per-row column
        loan_<name>.bin     one file per per-loan column

**Per-row columns are the ones that move inside a loan. Per-loan columns are read
once from the loan's first row**, which is where the acquisition side lives. That
alone keeps the class fields off the row axis: 2.9 M loans instead of 170 M rows.

Sizing, six archives, 170,013,011 rows and 2,942,295 loans: about **6.1 GB**. The
source zips are 3.1 GB and their uncompressed content is 46.9 GB, so the core
table sits between the two and is read at memory-map speed. At the full vintage
download the same layout is about 100 GB, which is **not** the format to use
there; the encodings that fix it are registered in
the B8 inputs register §6.3 and are deliberately not implemented
here, because a dense format is the one that can be checked bit for bit against
the scripts it replaces.

Discipline. The build never deletes: a stale cache directory is renamed with an
``.expired`` suffix by hand and left in place. The build is resumable per
archive, skipping any archive whose manifest already matches its source zip's
CRC and size. A manifest that does not match refuses to load.

Usage::

    python experiments/b8_core.py build                  # all archives, parallel
    python experiments/b8_core.py build --workers 6
    python experiments/b8_core.py build --only 2002Q1 --force
    python experiments/b8_core.py status
    python experiments/b8_core.py verify --only 2019Q1   # re-read the zip, compare
    python experiments/b8_core.py selftest               # touches no real archive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from array import array
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
CACHE = ROOT / "data" / "processed" / "fannie_core"

SCHEMA_VERSION = "v1"
NFIELDS = 113
DELIM = b"|"

#: Rows are buffered this many at a time before being flushed to disk, so peak
#: memory does not scale with the archive.
FLUSH_ROWS = 2_000_000

#: Sentinels. Zero is a real value for every numeric column here, UPB included
#: at payoff, so missing needs its own code and it needs to be stated.
U8_NA = 255
U16_NA = 65535
U32_NA = 4294967295

#: Month index origin. 1990-01 is month 0, which leaves room below the earliest
#: acquisition quarter and above any modified maturity date inside uint16.
EPOCH_YEAR = 1990


def month_index(v: bytes) -> int:
    """``MMYYYY`` to months since ``EPOCH_YEAR``-01, or ``U16_NA``."""
    if len(v) != 6 or not v.isdigit():
        return U16_NA
    y = int(v[2:])
    m = int(v[:2])
    if not 1 <= m <= 12 or y < EPOCH_YEAR:
        return U16_NA
    k = (y - EPOCH_YEAR) * 12 + (m - 1)
    return k if k < U16_NA else U16_NA


def as_u16(v: bytes) -> int:
    v = v.strip()
    if not v:
        return U16_NA
    try:
        x = int(round(float(v)))
    except ValueError:
        return U16_NA
    return x if 0 <= x < U16_NA else U16_NA


def as_rate(v: bytes) -> int:
    """Interest rate in thousandths of a per cent, so 6.500 becomes 6500."""
    v = v.strip()
    if not v:
        return U16_NA
    try:
        x = int(round(float(v) * 1000.0))
    except ValueError:
        return U16_NA
    return x if 0 <= x < U16_NA else U16_NA


def as_cents(v: bytes) -> int:
    v = v.strip()
    if not v:
        return U32_NA
    try:
        x = int(round(float(v) * 100.0))
    except ValueError:
        return U32_NA
    return x if 0 <= x < U32_NA else U32_NA


def as_code(v: bytes) -> int:
    """First byte of a short code field, or ``U8_NA`` when blank.

    Delinquency status is the one that matters: ``00`` becomes ``48`` which is
    ASCII ``0``, ``01`` becomes ``48`` as well. **So this is not enough for field
    40** and that field gets its own parser below.
    """
    v = v.strip()
    return v[0] if v else U8_NA


def as_delinq(v: bytes) -> int:
    """Delinquency status. Field 40 is two characters and its leading digit is
    not the value, so this cannot use ``as_code``.

    ``00``-``98`` map to the integer, ``XX`` and anything unrecognised to 254,
    blank to 255. **A digit string of any length other than two maps to 253**
    rather than to its integer value, so that ``delinq == 0`` is exactly the
    predicate ``field.strip() == b"00"`` the hand-written filters used, and an
    off-convention field shows up as a distinct code instead of silently joining
    the performing rows.
    """
    v = v.strip()
    if not v:
        return U8_NA
    if not v.isdigit():
        return 254
    if len(v) != 2:
        return 253
    x = int(v)
    return x if x < 253 else 253


def as_state(v: bytes) -> int:
    """Two-letter postal code packed into uint16, blank to ``U16_NA``."""
    v = v.strip()
    if len(v) != 2:
        return U16_NA
    return v[0] * 256 + v[1]


def unpack_state(x: int) -> str:
    return "" if x == U16_NA else chr(x // 256) + chr(x % 256)


#: ``(name, 1-based field position, array typecode, parser)``. Positions are the
#: ones C0b confirmed by behaviour. **Fields 41, 49 and 109-113 are unidentified
#: and are deliberately absent**; C0b's caveat governs and this table does not
#: name a column on the strength of what its values look like.
ROW_COLS = [
    ("period",     3,   "H", month_index),
    ("rate",       9,   "H", as_rate),
    ("upb",        12,  "I", as_cents),
    ("loan_age",   16,  "H", as_u16),
    ("rem_legal",  17,  "H", as_u16),
    ("rem_matur",  18,  "H", as_u16),
    ("mat_date",   19,  "H", month_index),
    ("delinq",     40,  "B", as_delinq),
    ("mod_flag",   42,  "B", as_code),
    ("zero_bal",   44,  "B", as_code),
    ("zb_date",    45,  "H", month_index),
    ("nib_upb",    63,  "I", as_cents),
    ("forgiven",   64,  "I", as_cents),
    ("assist",     102, "B", as_code),
    ("adr",        106, "B", as_code),
    ("adr_count",  107, "B", as_code),
    ("defer_amt",  108, "I", as_cents),
]

#: Read once, from each loan's first row.
LOAN_COLS = [
    ("channel",    4,   "B", as_code),
    ("orig_term",  13,  "H", as_u16),
    ("ltv",        20,  "H", as_u16),
    ("dti",        23,  "H", as_u16),
    ("fico",       24,  "H", as_u16),
    ("fthb",       26,  "B", as_code),
    ("purpose",    27,  "B", as_code),
    ("occupancy",  30,  "B", as_code),
    ("state",      31,  "H", as_state),
]

#: Per loan, always written: where its rows start and how many there are.
LOAN_INDEX_COLS = [("row_start", "Q"), ("n_rows", "I")]

TYPECODE_TO_NP = {"B": "uint8", "H": "uint16", "I": "uint32", "Q": "uint64"}

#: ``mod_flag`` stores the raw first byte, so `Y` is this.
_Y = ord("Y")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def _flush(bufs: dict, handles: dict) -> None:
    for name, buf in bufs.items():
        if len(buf):
            buf.tofile(handles[name])
            del buf[:]


def build_archive(zip_path: Path, force: bool = False,
                  cache_root: Path | None = None) -> dict:
    """Parse one archive into the core table. Returns its manifest."""
    cache_root = cache_root or CACHE
    out = cache_root / SCHEMA_VERSION / zip_path.stem
    man_path = out / "manifest.json"

    with zipfile.ZipFile(zip_path) as zf:
        member = sorted(zf.namelist())[0]
        info = zf.getinfo(member)
        src = {"zip": zip_path.name, "member": member,
               "member_size": info.file_size, "member_crc": info.CRC,
               "zip_size": zip_path.stat().st_size}

        if man_path.exists() and not force:
            old = json.loads(man_path.read_text(encoding="utf-8"))
            if (old.get("source") == src
                    and old.get("schema_version") == SCHEMA_VERSION
                    and old.get("byte_order") == sys.byteorder):
                print(f"  {zip_path.stem}: cached, skipping", file=sys.stderr)
                return old
            print(f"  {zip_path.stem}: manifest differs, rebuilding",
                  file=sys.stderr)

        out.mkdir(parents=True, exist_ok=True)
        row_bufs = {n: array(tc) for n, _, tc, _ in ROW_COLS}
        loan_bufs = {n: array(tc) for n, _, tc, _ in LOAN_COLS}
        idx_bufs = {n: array(tc) for n, tc in LOAN_INDEX_COLS}
        loan_ids: list[bytes] = []

        row_h = {n: open(out / f"row_{n}.bin", "wb") for n in row_bufs}
        loan_h = {n: open(out / f"loan_{n}.bin", "wb") for n in loan_bufs}
        idx_h = {n: open(out / f"loan_{n}.bin", "wb") for n in idx_bufs}

        nrows = 0
        nloans = 0
        bad_width = 0
        cur_id = None
        cur_start = 0
        cur_count = 0
        since_flush = 0

        try:
            with zf.open(member) as fh:
                for line in fh:
                    line = line.rstrip(b"\r\n")
                    if not line:
                        continue
                    p = line.split(DELIM)
                    if len(p) != NFIELDS:
                        bad_width += 1
                        continue

                    lid = p[1]
                    if lid != cur_id:
                        if cur_id is not None:
                            idx_bufs["row_start"].append(cur_start)
                            idx_bufs["n_rows"].append(cur_count)
                            nloans += 1
                        cur_id = lid
                        cur_start = nrows
                        cur_count = 0
                        loan_ids.append(lid)
                        for name, pos, _, fn in LOAN_COLS:
                            loan_bufs[name].append(fn(p[pos - 1]))

                    for name, pos, _, fn in ROW_COLS:
                        row_bufs[name].append(fn(p[pos - 1]))
                    nrows += 1
                    cur_count += 1
                    since_flush += 1

                    if since_flush >= FLUSH_ROWS:
                        _flush(row_bufs, row_h)
                        since_flush = 0
                        print(f"  {zip_path.stem}: {nrows:,} rows",
                              file=sys.stderr)

            if cur_id is not None:
                idx_bufs["row_start"].append(cur_start)
                idx_bufs["n_rows"].append(cur_count)
                nloans += 1

            _flush(row_bufs, row_h)
            _flush(loan_bufs, loan_h)
            _flush(idx_bufs, idx_h)
        finally:
            for h in list(row_h.values()) + list(loan_h.values()) + \
                    list(idx_h.values()):
                h.close()

        (out / "loan_ids.txt").write_bytes(b"\n".join(loan_ids) + b"\n")

        man = {
            "schema_version": SCHEMA_VERSION,
            "archive": zip_path.stem,
            "source": src,
            "byte_order": sys.byteorder,
            "n_rows": nrows,
            "n_loans": nloans,
            "rows_wrong_width": bad_width,
            "epoch_year": EPOCH_YEAR,
            "sentinels": {"u8": U8_NA, "u16": U16_NA, "u32": U32_NA},
            "row_columns": {n: {"field": pos, "dtype": TYPECODE_TO_NP[tc]}
                            for n, pos, tc, _ in ROW_COLS},
            "loan_columns": {n: {"field": pos, "dtype": TYPECODE_TO_NP[tc]}
                             for n, pos, tc, _ in LOAN_COLS},
            "loan_index_columns": {n: {"dtype": TYPECODE_TO_NP[tc]}
                                   for n, tc in LOAN_INDEX_COLS},
        }
        man_path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"  {zip_path.stem}: done, {nrows:,} rows, {nloans:,} loans",
              file=sys.stderr)
        return man


def build_all(paths: list[Path], workers: int = 0, force: bool = False) -> None:
    """One process per archive. The parse is CPU bound and archives are
    independent, so wall clock falls to roughly the largest archive."""
    if workers <= 0:
        workers = min(len(paths), (os.cpu_count() or 2))
    if workers == 1 or len(paths) == 1:
        for p in paths:
            build_archive(p, force=force)
        return
    print(f"building {len(paths)} archives on {workers} workers",
          file=sys.stderr)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(build_archive, p, force) for p in paths]
        for f in futs:
            f.result()


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------

class Core:
    """One archive's core table, memory mapped.

    ``c.row['upb']`` is a uint32 array of cents, length ``c.n_rows``.
    ``c.loan['fico']`` is length ``c.n_loans``.
    ``c.row_start`` and ``c.n_per_loan`` give each loan's contiguous block, which
    C0b established is how the file is laid out.
    """

    def __init__(self, archive: str, cols: list[str] | None = None,
                 loan_cols: list[str] | None = None,
                 cache_root: Path | None = None):
        root = (cache_root or CACHE) / SCHEMA_VERSION / archive
        man_path = root / "manifest.json"
        if not man_path.exists():
            raise FileNotFoundError(
                f"no core table for {archive}. Run: "
                f"python experiments/b8_core.py build --only {archive}")
        self.manifest = json.loads(man_path.read_text(encoding="utf-8"))
        if self.manifest["byte_order"] != sys.byteorder:
            raise RuntimeError(
                f"core table for {archive} was written on a "
                f"{self.manifest['byte_order']}-endian machine")
        if self.manifest["schema_version"] != SCHEMA_VERSION:
            raise RuntimeError(f"schema mismatch for {archive}")
        self.archive = archive
        self.n_rows = self.manifest["n_rows"]
        self.n_loans = self.manifest["n_loans"]
        self.root = root

        def mm(fn, dtype, count):
            return np.memmap(root / fn, dtype=dtype, mode="r", shape=(count,))

        want = cols if cols is not None else list(self.manifest["row_columns"])
        self.row = {n: mm(f"row_{n}.bin",
                          self.manifest["row_columns"][n]["dtype"], self.n_rows)
                    for n in want}
        wantl = (loan_cols if loan_cols is not None
                 else list(self.manifest["loan_columns"]))
        self.loan = {n: mm(f"loan_{n}.bin",
                           self.manifest["loan_columns"][n]["dtype"],
                           self.n_loans)
                     for n in wantl}
        self.row_start = mm("loan_row_start.bin", "uint64", self.n_loans)
        self.n_per_loan = mm("loan_n_rows.bin", "uint32", self.n_loans)

    # -- lifetime ----------------------------------------------------------

    def close(self) -> None:
        """Release the memory maps.

        **Windows refuses to delete, rename or truncate a file while it is
        mapped**, and Linux allows all three, so this is invisible on one side
        and fatal on the other. Any caller that rebuilds a cache directory, or
        that hands its path to something which will, closes first.

        Arrays produced from these maps by ``astype``, fancy indexing or a
        comparison are already copies and stay valid. A plain slice is a view
        and does not.
        """
        for d in (self.row, self.loan):
            for a in d.values():
                m = getattr(a, "_mmap", None)
                if m is not None:
                    m.close()
            d.clear()
        for name in ("row_start", "n_per_loan"):
            a = getattr(self, name, None)
            m = getattr(a, "_mmap", None) if a is not None else None
            if m is not None:
                m.close()
            setattr(self, name, None)

    def __enter__(self) -> "Core":
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False

    # -- derived -----------------------------------------------------------

    def loan_of_row(self) -> np.ndarray:
        """Loan ordinal for every row."""
        return np.repeat(np.arange(self.n_loans, dtype=np.int32),
                         self.n_per_loan.astype(np.int64))

    def first_row_of_loan_mask(self) -> np.ndarray:
        m = np.zeros(self.n_rows, dtype=bool)
        m[self.row_start.astype(np.int64)] = True
        return m

    def cummax_within_loan(self, flag: np.ndarray) -> np.ndarray:
        """Has ``flag`` been true on this row or any earlier row of this loan."""
        idx = np.arange(self.n_rows, dtype=np.int64)
        last = np.maximum.accumulate(np.where(flag, idx, -1))
        start = np.repeat(self.row_start.astype(np.int64),
                          self.n_per_loan.astype(np.int64))
        return last >= start


# ---------------------------------------------------------------------------
# the shared predicates. one copy, cited rather than re-typed.
# ---------------------------------------------------------------------------

#: Per-loan carrier classes returned by :func:`zero_interest_carrier`.
CARRIER_NONE, CARRIER_63, CARRIER_108, CARRIER_BOTH, CARRIER_SEQ = 0, 1, 2, 3, 4

#: Human-readable names in class order, for renderers.
CARRIER_NAMES = ["none", "63 only", "108 only", "both (excluded)",
                 "63 and 108, never at once"]


def zero_interest_carrier(c: Core) -> tuple[np.ndarray, dict]:
    """Which zero-interest balance each loan carries. `b8_fannie_slice.md` §14.1
    as amended, disposition in the B8 inputs register §6.6.20.6.

    Returns ``(cls_of_loan, info)``, ``cls`` an int8 over **loans**::

        0  CARRIER_NONE   neither field 63 nor field 108 is ever positive
        1  CARRIER_63     field 63 only
        2  CARRIER_108    field 108 only
        3  CARRIER_BOTH   both, at once or by C13's reckoning -> **excluded**
        4  CARRIER_SEQ    both present, never at once, no C13 edge pair

    **Class 3 is a refusal, not a reading.** C13 (§6.6.20) put all four
    candidate readings of field 12 between 11.6 and 46.2 per cent median error
    against the contract payment on these loans, against 0.0000 for the same
    arithmetic on C11's sample, four orders of magnitude away. Field 12's
    content is not identified there, so no ``V`` is computed on them and the
    count travels with every ``V`` and ``omega`` figure, at the same rank as
    §9's truncation limits.

    **The class does not enter the arithmetic, only the refusal does.** On any
    loan that is not class 3 the two carriers are never positive in the same
    month, so §6.6.20.6's three readings collapse to the single expression
    ``12 - 63 - 108`` with balloon ``63 + 108`` and every term that does not
    apply is zero. That is why :func:`zero_interest_split` takes no class:
    **there is no branch to implement wrong.** The only thing the class decides
    is which rows may be read at all.

    **Class 3 is a union of two predicates, counted separately.** C13 drew its
    population from **rising edges** of the two fields and that is reproduced
    here as ``both_edges``, so the published 1,276 stays recoverable. But a
    rising edge needs a previous row inside the same loan, so a loan whose
    field 63 is already positive on its first row carries no edge at all (pit
    1, left truncation) while its field 12 is every bit as ambiguous.
    ``ever_both_positive`` catches those. **The union is excluded**, which is
    C13's disposition applied to a set at least as large as the one it was
    written for and never a smaller one. ``excluded_beyond_c13`` prints the
    difference, so whether the two predicates agree is a read number rather
    than an assumption.

    Class 4 is the residue: both carriers appear in the loan's life but never
    in the same month and never as a C13 edge pair, so C8-1 and C11-1 each hold
    on their own months and the arithmetic is sound. **It is given its own
    class rather than folded into 1 or 2 because a label that says "63 only"
    on a loan that also carries 108 is the kind of stale name §6.6.21.5 is a
    list of.**
    """
    starts = c.row_start.astype(np.int64)
    if c.n_rows == 0:
        z = np.zeros(c.n_loans, dtype=np.int8)
        return z, {"n_loans": int(c.n_loans), "both_edges": 0,
                   "ever_both_positive": 0, "excluded": 0,
                   "excluded_beyond_c13": 0,
                   "by_class": [int(c.n_loans), 0, 0, 0, 0]}
    if "defer_amt" not in c.row:
        raise KeyError(
            "zero_interest_carrier needs the `defer_amt` column; open Core "
            "with it in `cols`. Classifying on field 63 alone would put every "
            "field-108 loan into CARRIER_NONE and read its balance as a plain "
            "field 12, which is the C10-4 defect with a different sign.")

    n = c.n_rows
    loan = c.loan_of_row()
    nib = c.row["nib_upb"][:]
    dfr = c.row["defer_amt"][:]
    non = (nib != U32_NA) & (nib > 0)
    don = (dfr != U32_NA) & (dfr > 0)

    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]

    def any_per_loan(mask):
        return np.add.reduceat(mask.astype(np.int64), starts) > 0

    def has_edge(mask):
        e = np.zeros(n, dtype=bool)
        e[1:] = mask[1:] & ~mask[:-1] & same[1:]
        return any_per_loan(e)

    both_edges = has_edge(non) & has_edge(don)      # C13's population, verbatim
    ever_both = any_per_loan(non & don)
    excluded = both_edges | ever_both

    ever63, ever108 = any_per_loan(non), any_per_loan(don)
    cls = np.where(
        excluded, CARRIER_BOTH,
        np.where(ever63 & ever108, CARRIER_SEQ,
                 np.where(ever63, CARRIER_63,
                          np.where(ever108, CARRIER_108,
                                   CARRIER_NONE)))).astype(np.int8)
    info = {
        "n_loans": int(c.n_loans),
        "both_edges": int(both_edges.sum()),
        "ever_both_positive": int(ever_both.sum()),
        "excluded": int(excluded.sum()),
        "excluded_beyond_c13": int((excluded & ~both_edges).sum()),
        "by_class": [int((cls == k).sum()) for k in range(5)],
    }
    return cls, info


def zero_interest_split(c: Core) -> tuple[np.ndarray, np.ndarray]:
    """``(interest-bearing balance, zero-interest balloon)``, both in **cents**.

    ``12 - 63 - 108`` and ``63 + 108``, a blank in either read as zero. C8-1
    settled that field 12 contains field 63; C11-1 settled that it contains
    field 108. This is §6.6.20.6's whole table, because the branches it lists
    differ only in which term is zero.

    **This returns the arithmetic on every row, including the rows
    :func:`zero_interest_carrier` refuses.** The refusal is kept as a separate
    per-loan mask on purpose: ``quiet_pairs`` applies the arithmetic without
    the refusal, because every C8-1 and C11 figure already published was read
    that way, and folding the refusal in here would silently re-base results
    this change does not touch. **Whoever computes a ``V`` applies the mask.**

    **A blank field 12 is not screened here either.** It stores as ``U32_NA``
    and the subtraction would carry the sentinel straight into a balance.
    ``quiet_pairs`` and ``b8_0a_gate.noise_floor`` both already screen it
    before they get here; anything new that calls this must too, and
    :func:`b8_omega.rows_for_V` is where that screen lives for the loop
    assembly.
    """
    if "defer_amt" not in c.row:
        raise KeyError(
            "zero_interest_split needs the `defer_amt` column; open Core with "
            "it in `cols`. Netting field 63 alone is a silent half-correction, "
            "which is worse than failing here.")
    upb = c.row["upb"][:].astype(np.int64)
    nib = c.row["nib_upb"][:].astype(np.int64)
    dfr = c.row["defer_amt"][:].astype(np.int64)
    z63 = np.where((nib != U32_NA) & (nib > 0), nib, 0)
    z108 = np.where((dfr != U32_NA) & (dfr > 0), dfr, 0)
    return upb - z63 - z108, z63 + z108


def quiet_pairs(c: Core, require_never_deferred: bool = False,
                require_cur_positive: bool = True,
                ib_net: bool = True) -> dict:
    """The quiet-month filter, vectorised, as a set of adjacent row pairs.

    **This is the single copy of the predicate** that ``b8_c8_arithmetic.py``'s
    C8-1a control, ``b8_c8_1c_contract_payment.py`` and
    ``b8_c8_1c_contract_payment_b.py`` each implemented by hand. A pair
    ``(r - 1, r)`` qualifies when

      * both rows belong to the same loan and their reporting periods are one
        month apart,
      * delinquency status reads ``00`` on both,
      * the modification flag is unchanged,
      * field 17 falls by exactly one,
      * field 9 is unchanged,
      * the previous row's UPB is present and strictly positive,
      * **and, when ``require_cur_positive``, the current row's UPB is
        strictly positive too.**

        That condition was absent until 2026-08-16 and its absence was a
        real defect. Field 12 reads a **literal zero** on the opening rows
        of every loan in all six archives, and again after termination,
        about 6.7 to 6.9 rows per loan and 8.6 to 19.6 per cent of all
        rows. A pair whose later row was one of those passed the old
        filter with ``obs`` equal to the **entire balance** and landed at
        the top of every ratio histogram. A balance going to zero is a
        termination, which is an event, so it is not a quiet month.
        The flag exists so the old sample can be reproduced; **the default
        is the corrected one**, and ``n_dropped_cur_zero`` in the returned
        dict is how many pairs the correction removes.
      * and, when ``require_never_deferred``, no row of this loan **up to and
        including the current one** has carried a positive field 63. **The
        default became ``False`` on 2026-08-17** (§6.6.17): the exclusion
        existed because the reported balance contains field 63, and ``ib_net``
        now nets it out, so excluding the loan as well throws away 9,760 loans
        that C10-4 showed belong to the **modification** arm. The flag stays for
        reproducing the older sample. That
        inclusive bound is deliberate: ``b8_c8_arithmetic.py`` sets its
        ``nib_ever`` flag from the current row before it reads the pair, so the
        month a deferred balance first appears is excluded on both sides.

      * **``ib_net`` nets the deferred balances out of the reported one.** C8-1
        settled that field 12 contains field 63; C11-1 settled that it contains
        field 108 as well (the B8 inputs register §6.6.14.1, criterion B,
        median error exactly zero against 3.5 to 8.9 per cent for the
        alternative on 1.05 M months). The interest-bearing balance is therefore
        ``12 - 63 - 108``, and an implied payment computed on the reported
        balance is wrong wherever either field is set.

        **The default is ``True`` as of 2026-08-17** (§6.6.17, ruled after C12
        measured the blast radius). ``ib_net=False`` is kept, not deleted,
        because the C8-1a family's numbers were produced under it and a sample
        that cannot be reproduced is a sample that cannot be checked. The
        selftest still asserts the two agree wherever neither field is set, by
        running both and comparing the arrays rather than reasoning about them. On a loan carrying neither field
        the two agree by algebra, ``12 - 0 - 0 = 12``, so only loans with a
        deferred balance can differ at all.

        The positivity filters keep using the **reported** balance: a balance
        going to zero is a termination whether or not part of it was deferred.

    Returns index arrays over the pair, not over the row, plus the quantities the
    callers all need::

        {"cur": r, "prev": r - 1, "obs_cents", "p_upb_cents", "p_rem",
         "rate_milli", "loan"}
    """
    period = c.row["period"].astype(np.int32)
    rate = c.row["rate"].astype(np.int32)
    upb = c.row["upb"].astype(np.int64)      # cents exceed int32 above $21.4 M
    rem = c.row["rem_legal"].astype(np.int32)
    dq = c.row["delinq"]
    mf = c.row["mod_flag"]
    nib = c.row["nib_upb"].astype(np.int64)

    loan = c.loan_of_row()
    n = c.n_rows
    cur = np.arange(1, n, dtype=np.int64)
    prv = cur - 1

    ok = loan[cur] == loan[prv]
    ok &= period[cur] != U16_NA
    ok &= period[prv] != U16_NA
    ok &= (period[cur] - period[prv]) == 1
    ok &= dq[cur] == 0
    ok &= dq[prv] == 0
    # The hand-written filters compared the BOOLEAN `flag == b"Y"`, under which
    # `N` and blank are the same. Comparing the stored byte instead would treat
    # them as different and silently shrink the sample.
    ok &= (mf[cur] == _Y) == (mf[prv] == _Y)
    ok &= rem[cur] != U16_NA
    ok &= rem[prv] != U16_NA
    ok &= (rem[prv] - rem[cur]) == 1
    ok &= rate[cur] != U16_NA
    ok &= rate[prv] != U16_NA
    ok &= rate[cur] == rate[prv]
    ok &= upb[prv] != U32_NA
    ok &= upb[prv] > 0
    ok &= upb[cur] != U32_NA

    if require_never_deferred:
        seen = c.cummax_within_loan((nib != U32_NA) & (nib > 0))
        ok &= ~seen[cur]

    # applied last, so the count is of pairs this condition and nothing else
    # removes. Counting it earlier double-counts pairs the deferral condition
    # would have taken anyway.
    n_cur_zero = 0
    if require_cur_positive:
        n_cur_zero = int((ok & (upb[cur] == 0)).sum())
        ok &= upb[cur] > 0

    sel = cur[ok]
    bal = upb
    if ib_net:
        # **One copy of the arithmetic**, shared with `V`. It used to be typed
        # out here as well, and two copies of `12 - 63 - 108` is how the
        # netting and the balloon drift apart without either one looking wrong.
        # The per-loan refusal (`zero_interest_carrier`) is deliberately **not**
        # applied: see that function, and `zero_interest_split`'s docstring.
        bal, _balloon = zero_interest_split(c)
    return {
        "n_dropped_cur_zero": n_cur_zero,
        "cur": sel,
        "prev": sel - 1,
        "obs_cents": bal[sel - 1] - bal[sel],
        "p_upb_cents": bal[sel - 1],
        "p_rem": rem[sel - 1],
        "rate_milli": rate[sel - 1],
        "loan": loan[sel],
    }


def segment_ids(q: dict) -> np.ndarray:
    """Constant-rate runs of quiet pairs inside one loan.

    Matches the python state machine exactly, **including the part that is easy
    to get wrong**: a non-quiet month in the middle of a loan does not close the
    segment. Only a change of loan or a change of field 9 between successive
    quiet pairs does.
    """
    loan, rate = q["loan"], q["rate_milli"]
    if loan.size == 0:
        return np.zeros(0, dtype=np.int64)
    new = np.empty(loan.size, dtype=bool)
    new[0] = True
    new[1:] = (loan[1:] != loan[:-1]) | (rate[1:] != rate[:-1])
    return np.cumsum(new) - 1


def segment_bounds(seg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(start, count)`` for each segment id, for use with ``reduceat``."""
    if seg.size == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    start = np.flatnonzero(np.concatenate(([True], seg[1:] != seg[:-1])))
    count = np.diff(np.append(start, seg.size))
    return start, count


#: Two cent-roundings of the reported balance. The file prints UPB to two
#: decimals, so an implied payment inherits a rounding at each end and a
#: genuinely level payment still spreads by two cents. This bounds the smallest
#: deviation any payment test here can see.
CENT_TOL = 0.02

#: A cluster is a modal candidate when it carries at least this share of a
#: segment's months.
CAND_SHARE = 0.10


def modal_cluster(implied: list[float]) -> tuple[float, float, float, int]:
    """The modal cluster of implied payments: ``(mean, lo, hi, n_candidates)``.

    **Character-identical to the one in ``b8_c8_1c_contract_payment_b.py``**,
    lifted here so the next stage does not hand-copy it. Any script using this
    reproduces that script's at/below/above counts as its first table; a
    reproduction that fails means the two have drifted.

    **Clusters, not cent buckets.** Bucketing to the cent smears one true payment
    across two or three adjacent buckets, which makes every segment look like it
    has several candidates. Values within ``CENT_TOL`` of their neighbour join
    one cluster, the largest cluster is the estimate, and the estimate is that
    cluster's **mean** so the cent grid does not enter it. Ties break to the
    smallest value. Single linkage can chain, so callers report the width.
    """
    vals = sorted(implied)
    clusters, cur = [], [vals[0]]
    for v in vals[1:]:
        if v - cur[-1] <= CENT_TOL:
            cur.append(v)
        else:
            clusters.append(cur)
            cur = [v]
    clusters.append(cur)
    best = max(clusters, key=len)
    thr = CAND_SHARE * len(implied)
    return (sum(best) / len(best), best[0], best[-1],
            sum(1 for c in clusters if len(c) >= thr))


def segment_modes(q: dict, seg: np.ndarray):
    """Per-month modal payment, in currency units, plus the cluster bounds.

    Returns ``(mode, lo, hi, ncand, seg_start, seg_count)`` with the first four
    broadcast to one entry per quiet pair, so everything downstream is
    elementwise.
    """
    start, count = segment_bounds(seg)
    obs = q["obs_cents"].astype(np.float64) / 100.0
    p_upb = q["p_upb_cents"].astype(np.float64) / 100.0
    i = q["rate_milli"].astype(np.float64) / 1000.0 / 1200.0
    implied = obs + p_upb * i

    n = implied.size
    mode = np.empty(n)
    lo = np.empty(n)
    hi = np.empty(n)
    ncand = np.empty(n, dtype=np.int32)
    for s, c in zip(start.tolist(), count.tolist()):
        m, a, b, k = modal_cluster(implied[s:s + c].tolist())
        mode[s:s + c] = m
        lo[s:s + c] = a
        hi[s:s + c] = b
        ncand[s:s + c] = k
    return mode, lo, hi, ncand, start, count, implied


def level_payment(balance, rate_pct, n):
    """Vectorised level payment. ``balance`` in currency units, not cents.

    Returns ``nan`` where the inputs cannot support a payment, so the caller
    filters explicitly rather than inheriting a silent zero.
    """
    balance = np.asarray(balance, dtype=np.float64)
    rate_pct = np.asarray(rate_pct, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    i = rate_pct / 1200.0
    out = np.full(balance.shape, np.nan)
    good = (balance > 0) & (n > 0) & np.isfinite(i)
    zero = good & (i <= 0)
    pos = good & (i > 0)
    out[zero] = balance[zero] / n[zero]
    with np.errstate(over="ignore", invalid="ignore"):
        f = np.power(1.0 + i[pos], -n[pos])
        d = 1.0 - f
        v = np.where(d > 0, balance[pos] * i[pos] / np.where(d > 0, d, 1.0),
                     np.nan)
    out[pos] = v
    return out


def check_markdown_tables(text: str) -> list[str]:
    """Every table row must carry the same number of cells as its header.

    **Written 2026-08-17 because a published results file was malformed and
    nobody noticed, including the person who generated it, read it and quoted
    from it.** A section heading was inserted between a table's header row and
    its body rows, so one table rendered with no rows and the next got six
    eight-column rows under a five-column header. Markdown renders that without
    complaint; a reader sees a plausible table with the wrong labels.

    A renderer's selftest asserting that a heading string is present cannot see
    this. Shape can, and it is three lines of parsing.

    Returns a list of complaints, empty when the text is well formed. A row is
    part of a table when it starts and ends with a pipe; a run of such rows is
    one table and its first line is the header.

    **A backslash-escaped pipe is not a cell separator.** The first version of
    this counted them, which made it report a false complaint on the one table
    in the B8 inputs register that quotes ``|dP|/P`` inside a cell, and
    would have **hidden** a real width error in any table containing one. A
    checker that cries wolf gets its output skimmed, which is how the defect it
    was written for happened in the first place.
    """
    out, header, width, sep_seen, line_no = [], None, 0, False, 0
    for raw in text.splitlines():
        line_no += 1
        s = raw.strip()
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            cells = len(s.replace("\\|", "\x00").split("|")) - 2
            if header is None:
                header, width, sep_seen = line_no, cells, False
            elif set(s) <= set("|-: "):
                sep_seen = True
                if cells != width:
                    out.append(f"line {line_no}: separator has {cells} cells, "
                               f"header at line {header} has {width}")
            elif cells != width:
                out.append(f"line {line_no}: row has {cells} cells, header at "
                           f"line {header} has {width}: {s[:60]}")
        else:
            if header is not None and not sep_seen:
                out.append(f"line {header}: table header has no separator row "
                           "and no body")
            header = None
    if header is not None and not sep_seen:
        out.append(f"line {header}: table header has no separator row")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_status(paths: list[Path]) -> None:
    print(f"{'archive':10} {'cached':>7} {'rows':>14} {'loans':>12} "
          f"{'bytes on disk':>15}")
    for p in paths:
        d = CACHE / SCHEMA_VERSION / p.stem
        man = d / "manifest.json"
        if not man.exists():
            print(f"{p.stem:10} {'no':>7}")
            continue
        m = json.loads(man.read_text(encoding="utf-8"))
        size = sum(f.stat().st_size for f in d.iterdir() if f.is_file())
        print(f"{p.stem:10} {'yes':>7} {m['n_rows']:>14,} "
              f"{m['n_loans']:>12,} {size:>15,}")


def cmd_verify(paths: list[Path], nrows: int) -> int:
    """Re-read the head of each zip with the plain parser and compare it to the
    core table, field by field. A cache that cannot be checked is not evidence.
    """
    bad = 0
    for p in paths:
        c = Core(p.stem)
        with zipfile.ZipFile(p) as zf:
            member = sorted(zf.namelist())[0]
            with zf.open(member) as fh:
                k = 0
                for line in fh:
                    if k >= nrows:
                        break
                    line = line.rstrip(b"\r\n")
                    if not line:
                        continue
                    f = line.split(DELIM)
                    if len(f) != NFIELDS:
                        continue
                    for name, pos, _, fn in ROW_COLS:
                        want = fn(f[pos - 1])
                        got = int(c.row[name][k])
                        if want != got:
                            print(f"  {p.stem} row {k} {name}: "
                                  f"cache {got} vs file {want}", file=sys.stderr)
                            bad += 1
                    k += 1
        print(f"  {p.stem}: checked {k:,} rows x {len(ROW_COLS)} columns",
              file=sys.stderr)
    print("verify: ok" if not bad else f"verify: {bad} mismatch(es)",
          file=sys.stderr)
    return 1 if bad else 0




# ---------------------------------------------------------------------------
# selftest: does the vectorised filter reproduce the hand-written state machine?
# ---------------------------------------------------------------------------

_REF_DOC = """
This is the acceptance test for the whole module. It builds a synthetic archive
carrying every edge the real file has (reporting gaps, delinquency, the
modification flag turning on, the note rate moving at a modification, a deferred
balance appearing part way through, partial prepayments), builds the core table
from it, and compares ``quiet_pairs`` and ``segment_ids`` against a reference
state machine written in the same shape as the ones in
``b8_c8_arithmetic.py`` and ``b8_c8_1c_contract_payment_b.py``.

**Pair for pair and segment for segment, or it fails.** A vectorised filter that
is merely close is worse than no filter, because every count downstream stays
plausible.
"""


def _synth(path: Path, nloans: int = 1200, seed: int = 11) -> None:
    import random
    rng = random.Random(seed)
    lines = []
    for L in range(nloans):
        lid = f"{900000000000 + L}"
        rate = rng.choice([3.75, 4.5, 6.5, 7.0])
        bal = rng.uniform(80000, 350000)
        rem, y, m, age = 360, 2003, 1, 0
        i = rate / 1200.0
        pmt = float(level_payment([bal], [rate], [rem])[0])
        nmo = rng.randint(8, 60)
        nib_from = rng.randint(10, 80)
        ratechg = rng.randint(15, 80)
        # The real file reports a literal zero UPB on a loan's opening rows and
        # again after termination, about seven rows per loan. The fixture
        # carries the same shape so the ``require_cur_positive`` check is not
        # vacuous.
        zero_head = rng.randint(3, 8)
        for k in range(nmo):
            dq = "00"
            if rng.random() < 0.10:
                dq = rng.choice(["01", "02", "XX"])
            mod = "Y" if k >= ratechg else "N"
            nib = f"{rng.uniform(1000, 9000):.2f}" if k >= nib_from else ""
            if rng.random() < 0.05:                    # a reporting gap
                m += 1
                if m == 13:
                    m, y = 1, y + 1
                age += 1
                rem -= 1
                continue
            f = [""] * NFIELDS
            f[1] = lid
            f[2] = f"{m:02d}{y:04d}"
            f[3] = "R"
            f[8] = f"{rate:.3f}"
            f[11] = "0.00" if (k < zero_head or k == nmo - 1) else f"{bal:.2f}"
            f[12] = "360"
            f[15] = str(age)
            f[16] = str(rem)
            f[17] = str(rem)
            f[18] = "012032"
            f[19] = "80"
            f[22] = "35"
            f[23] = "720"
            f[25] = "N"
            f[26] = "P"
            f[29] = "P"
            f[30] = "CA"
            f[39] = dq
            f[41] = mod
            f[62] = nib
            f[101] = "7"
            f[105] = "7"
            lines.append("|".join(f))
            if dq == "00":
                bal = max(0.0, bal - (pmt - bal * i)
                          - rng.choice([0, 0, 0, 0, 500]))
            rem -= 1
            age += 1
            m += 1
            if m == 13:
                m, y = 1, y + 1
            if k == ratechg:                            # the modification
                rate = round(rate - 1.5, 3)
                i = rate / 1200.0
                pmt = float(level_payment([bal], [rate], [rem])[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")


def _reference(zip_path: Path, require_cur_positive: bool = True):
    """The hand-written state machine, kept in the shape the experiments use.

    ``require_cur_positive=False`` reproduces the filter as it stood before
    2026-08-16, which is what the C8-1a family ran on.
    """
    def num(v):
        v = v.strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def to_period(v):
        return int(v[2:]) * 100 + int(v[:2]) if len(v) == 6 and v.isdigit() else 0

    def mb(a, b):
        if not a or not b:
            return 0
        return (a // 100 - b // 100) * 12 + (a % 100 - b % 100)

    pairs, segs, seg = [], [], -1
    with zipfile.ZipFile(zip_path) as zf:
        member = sorted(zf.namelist())[0]
        with zf.open(member) as fh:
            cur_id = None
            prev = None
            nib_ever = False
            seg_rate = None
            r = -1
            for line in fh:
                line = line.rstrip(b"\r\n")
                if not line:
                    continue
                p = line.split(DELIM)
                if len(p) != NFIELDS:
                    continue
                r += 1
                if p[1] != cur_id:
                    cur_id, prev, nib_ever, seg_rate = p[1], None, False, None
                period = to_period(p[2])
                rate = num(p[8])
                upb = num(p[11])
                rem = num(p[16])
                rem = int(rem) if rem is not None else None
                dq = p[39].strip()
                mod = p[41].strip() == b"Y"
                nib = num(p[62])
                if nib is not None and nib > 0:
                    nib_ever = True
                if prev is not None:
                    pp, pr, pu, prm, pd, pm = prev
                    quiet = (mb(period, pp) == 1 and dq == b"00" and pd == b"00"
                             and mod == pm and rem is not None
                             and prm is not None and prm - rem == 1
                             and rate is not None and pr is not None
                             and abs(rate - pr) < 1e-9 and pu
                             and upb is not None and pu > 0 and not nib_ever
                             and (upb > 0 if require_cur_positive else True))
                    if quiet:
                        if seg_rate is None or abs(seg_rate - pr) >= 1e-9:
                            seg_rate = pr
                            seg += 1
                        pairs.append(r)
                        segs.append(seg)
                prev = (period, rate, upb, rem, dq, mod)
    return np.array(pairs, dtype=np.int64), np.array(segs, dtype=np.int64)


#: The selftest fixture lives on disk and **is never removed**. the project's engineering rule 5
#: forbids a script from containing a delete of any kind, ``shutil.rmtree``
#: named explicitly, and ``tempfile.TemporaryDirectory`` deletes on exit. Keeping
#: it also means a failure leaves something to look at, and a re-run skips the
#: synthesis. It sits under ``data/processed`` which ``.gitignore`` already
#: covers. Delete it by hand if it is ever in the way.
SELFTEST_DIR = CACHE / "_selftest"


def _open_after_build(zp: Path, cache_root: Path) -> Core:
    build_archive(zp, force=True, cache_root=cache_root)
    return Core(zp.stem, cache_root=cache_root)


def _fixture_tag() -> str:
    """Eight hex digits of the fixture generator's own source.

    **The fixture is an input to this test and it is cached, so it can go
    stale.** On 2026-08-16 it did, in exactly the way this module warns about
    elsewhere. ``_synth`` was changed to emit zero-UPB rows so the new
    ``require_cur_positive`` check would have something to bite on; a machine
    that had run ``selftest`` before reused its old archive, and the check
    reported ``0 of 23,389 removed``. The check itself caught it, but only
    because it was written to fail when the two conventions do not differ.
    **Had it only compared the two and not demanded that they differ, a stale
    fixture would have made it pass vacuously and stay green forever.**

    Keying the file name on the generator's source closes it without deleting
    anything: change ``_synth`` or ``_reference`` and the name changes, so the
    stale archive is never reached and stays on disk to look at.
    """
    import hashlib
    import inspect
    src = inspect.getsource(_synth) + inspect.getsource(_reference)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:8]


#: One loan per carrier class, hand-built. ``(suffix, f63, f108, f19)``: the two
#: lists are the per-month values of fields 63 and 108 with a blank written as
#: ``0``, and ``f19`` is the legal maturity date as ``MMYYYY``.
#: **Every class is here including the two that only exist because of pit 1**,
#: left truncation: a balance already standing on a loan's first row has no
#: rising edge, so C13's edge-pair predicate cannot see it while the arithmetic
#: is every bit as ambiguous.
#:
#: ``012050`` puts field 19 exactly 360 months after the first row, so it agrees
#: with field 17 month for month, which is what §14.1 says the real file does.
#: **Loan 7 breaks that agreement on purpose**, by five months: while the two
#: fields agree, no test can tell which one a horizon was read from, and
#: `b8_omega.balloon_horizon` has to be shown reading field 19.
CARRIER_FIXTURE = [
    # id  field 63 by month          field 108 by month       f19       class
    ("0", [0, 0, 0, 0, 0, 0],        [0, 0, 0, 0, 0, 0], "012050"),  # NONE
    ("1", [0, 0, 1500, 1500, 0, 0],  [0, 0, 0, 0, 0, 0], "012050"),  # 63
    ("2", [0, 0, 0, 0, 0, 0],   [0, 0, 900, 900, 900, 0], "012050"),  # 108
    ("3", [0, 0, 1500, 1500, 0, 0],
     [0, 0, 0, 900, 900, 0], "012050"),                    # BOTH, both ways
    ("4", [1200, 1200, 0, 0, 0, 0],
     [0, 0, 0, 900, 900, 0], "012050"),                    # SEQ
    ("5", [1200, 1200, 1200, 0, 0, 0],
     [700, 700, 700, 0, 0, 0], "012050"),                  # BOTH, no edges
    ("6", [0, 1500, 1500, 0, 0, 0],
     [0, 0, 0, 0, 900, 900], "012050"),                    # BOTH, no overlap
    ("7", [0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0], "062050"),                        # NONE, 19 != 17 + 0
]
CARRIER_EXPECT = [CARRIER_NONE, CARRIER_63, CARRIER_108, CARRIER_BOTH,
                  CARRIER_SEQ, CARRIER_BOTH, CARRIER_BOTH, CARRIER_NONE]

#: How far loan 7's field 19 sits past what field 17 says, in months.
CARRIER_F19_SKEW = 5


def _synth_carrier(path: Path) -> None:
    """One loan per line of :data:`CARRIER_FIXTURE`, six months each."""
    lines = []
    for li, (sfx, f63, f108, f19) in enumerate(CARRIER_FIXTURE):
        rem, y, m = 360, 2020, 1
        for kk in range(len(f63)):
            f = [""] * NFIELDS
            f[1] = f"9500000000{li:02d}"
            f[2] = f"{m:02d}{y:04d}"
            f[8] = "6.000"
            f[11] = "200000.00"
            f[12] = "360"
            f[15] = str(kk)
            f[16] = str(rem)
            f[17] = str(rem)
            f[18] = f19
            f[39] = "00"
            f[41] = "N"
            f[62] = f"{f63[kk]:.2f}" if f63[kk] else ""
            f[101] = "7"
            f[105] = "P" if f108[kk] else "7"
            f[107] = f"{f108[kk]:.2f}" if f108[kk] else ""
            lines.append("|".join(f))
            rem -= 1
            m += 1
            if m == 13:
                m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")


def _selftest_carrier(cache_root: Path) -> list[str]:
    """`zero_interest_carrier` and `zero_interest_split`, class by class.

    **The point of this fixture is the refusal, not the arithmetic.** The
    arithmetic is one expression with no branch (see `zero_interest_split`), so
    the thing that can be wrong is *which loans are allowed to be read*, and
    that has four ways to be wrong: missing an overlap, missing an edge pair,
    missing a left-truncated carrier, or refusing a loan that carries the two
    balances at different times and is perfectly readable. One loan each.
    """
    zp = SELFTEST_DIR / "raw" / "2096Q1_carrier.zip"
    _synth_carrier(zp)
    build_archive(zp, force=True, cache_root=cache_root)
    out: list[str] = []
    with Core(zp.stem, cols=["period", "upb", "nib_upb", "defer_amt"],
              cache_root=cache_root) as c:
        cls, info = zero_interest_carrier(c)
        bal, balloon = zero_interest_split(c)

        got = cls.tolist()
        if got != CARRIER_EXPECT:
            out.append(f"carrier classes {got} != expected {CARRIER_EXPECT}")
        # **Each half of the union is load-bearing on exactly one loan.** Loan 3
        # trips both predicates and proves nothing on its own; loan 5 is
        # left-truncated so only the overlap catches it, and loan 6 never
        # overlaps so only the edge pair catches it. Drop either half and one
        # of those two goes unexcluded.
        want_excl = sum(1 for k in CARRIER_EXPECT if k == CARRIER_BOTH)
        if info["both_edges"] != 2:
            out.append(f"both_edges {info['both_edges']} != 2; C13's edge-pair "
                       "predicate is not reproduced")
        if info["ever_both_positive"] != 2:
            out.append(f"ever_both_positive {info['ever_both_positive']} != 2")
        if info["excluded"] != want_excl:
            out.append(f"excluded {info['excluded']} != {want_excl}; the union "
                       "is wrong")
        if info["excluded_beyond_c13"] != 1:
            out.append(f"excluded_beyond_c13 {info['excluded_beyond_c13']} "
                       "!= 1; the left-truncated carrier is invisible, which "
                       "means the union collapsed to C13's predicate")

        # the arithmetic, per row, against the fixture's own numbers
        want_bal, want_bln = [], []
        for _sfx, f63, f108, _f19 in CARRIER_FIXTURE:
            for a, b in zip(f63, f108):
                want_bal.append(20000000 - 100 * (a + b))
                want_bln.append(100 * (a + b))
        if bal.tolist() != want_bal:
            out.append("zero_interest_split's balance is not 12 - 63 - 108")
        if balloon.tolist() != want_bln:
            out.append("zero_interest_split's balloon is not 63 + 108")
        # and the split must be non-trivial on this fixture, or it proves
        # nothing: **pit 32's family, an all-zero column reads as a pass**
        if not any(want_bln):
            out.append("the carrier fixture carries no balloon at all")
    print(f"  carrier: classes {cls.tolist()}, excluded {info['excluded']} "
          f"(C13 edge pairs {info['both_edges']}, "
          f"beyond {info['excluded_beyond_c13']})", file=sys.stderr)
    return out


#: ``(name, text, expected complaint count)`` for :func:`check_markdown_tables`.
#: **The checker is load-bearing in eight renderers and it had a bug**, so it
#: gets its own cases: the two shapes it exists to catch, the two shapes it must
#: not flag, and the escaped pipe that made it cry wolf.
TABLE_CASES = [
    ("well formed", "| a | b |\n|---|---|\n| 1 | 2 |\n", 0),
    ("wide row", "| a | b |\n|---|---|\n| 1 | 2 | 3 |\n", 1),
    ("wide separator", "| a | b |\n|---|---|---|\n| 1 | 2 |\n", 1),
    ("header with no body", "| a | b |\n\nprose\n", 1),
    ("prose between header and body",
     "| a | b |\n\nsomething\n\n|---|---|\n| 1 | 2 |\n", 2),
    ("escaped pipe in a cell",
     "| a | b |\n|---|---|\n| `\\|x\\|/y` | 2 |\n", 0),
    ("escaped pipe does not hide a wide row",
     "| a | b |\n|---|---|\n| `\\|x\\|` | 2 | 3 |\n", 1),
    ("no table at all", "just prose\nand more prose\n", 0),
]


def _selftest_tables() -> list[str]:
    out = []
    for name, text, want in TABLE_CASES:
        got = len(check_markdown_tables(text))
        if got != want:
            out.append(f"check_markdown_tables `{name}`: {got} complaints, "
                       f"expected {want}")
    print(f"  tables: {len(TABLE_CASES)} cases", file=sys.stderr)
    return out


def cmd_selftest() -> int:
    tag = _fixture_tag()
    zp = SELFTEST_DIR / "raw" / f"2098Q1_{tag}.zip"
    cache_root = SELFTEST_DIR / "cache"
    if not zp.exists():
        _synth(zp)
        print(f"  built fixture {zp.name} (generator {tag})", file=sys.stderr)
    else:
        print(f"  reusing fixture {zp.name} (generator {tag})", file=sys.stderr)

    with _open_after_build(zp, cache_root) as c:
        # **The reference state machine implements the LEGACY reading**, so it
        # is compared against the legacy parameters explicitly. After the
        # 2026-08-17 default flip, `quiet_pairs(c)` is a different object and
        # comparing it here would report a failure that is really a ruling.
        q = quiet_pairs(c, require_never_deferred=True, ib_net=False)
        seg = segment_ids(q)
        q_old = quiet_pairs(c, require_never_deferred=True, ib_net=False,
                            require_cur_positive=False)
        q_now = quiet_pairs(c)                          # the live default
    ref_p, ref_s = _reference(zp, require_cur_positive=True)
    ref_po, _ = _reference(zp, require_cur_positive=False)

    fails = []
    print(f"  reference  : {ref_p.size:,} quiet pairs, "
          f"{(ref_s[-1] + 1) if ref_s.size else 0:,} segments", file=sys.stderr)
    print(f"  vectorised : {q['cur'].size:,} quiet pairs, "
          f"{(seg[-1] + 1) if seg.size else 0:,} segments", file=sys.stderr)
    print(f"  identical  : pairs "
          f"{np.array_equal(ref_p, q['cur'])}, segments "
          f"{ref_s.size == seg.size and np.array_equal(ref_s, seg)}",
          file=sys.stderr)
    if ref_p.size == 0:
        fails.append("the synthetic archive produced no quiet pairs")
    if not np.array_equal(ref_p, q["cur"]):
        a, b = set(ref_p.tolist()), set(q["cur"].tolist())
        fails.append(f"pair sets differ: only-reference {sorted(a - b)[:8]}, "
                     f"only-vectorised {sorted(b - a)[:8]}")
    elif not np.array_equal(ref_s, seg):
        fails.append("pair sets match but segment ids differ")

    # the pre-2026-08-16 convention must still reproduce, since that is what
    # the C8-1a family ran on and its numbers stay on disk
    if not np.array_equal(ref_po, q_old["cur"]):
        fails.append("require_cur_positive=False no longer reproduces the "
                     "filter the C8-1a family used")
    # and the two must actually differ on this fixture, or the check is vacuous
    removed = q_old["cur"].size - q["cur"].size
    if removed <= 0:
        fails.append("the fixture carries no zero-UPB pair, so the "
                     "require_cur_positive check proves nothing")
    if removed != q["n_dropped_cur_zero"]:
        fails.append(f"n_dropped_cur_zero {q['n_dropped_cur_zero']} does not "
                     f"match the observed drop {removed}")
    print(f"  cur-UPB-zero pairs removed : {removed:,} of "
          f"{q_old['cur'].size:,}", file=sys.stderr)

    # **`ib_net`'s default must reproduce bit for bit, and the check is run
    # rather than reasoned about.** SESSION_INIT's fourth lesson: every new
    # switch's default reproduces the existing result and the comparison is
    # executed. The second half asserts the switch is not inert.
    with _open_after_build(zp, cache_root) as c2:
        q_net = quiet_pairs(c2, require_never_deferred=True, ib_net=True)
        q_off = quiet_pairs(c2, require_never_deferred=False, ib_net=False)
        q_on = quiet_pairs(c2, require_never_deferred=False, ib_net=True)
    for key in ("cur", "prev", "obs_cents", "p_upb_cents", "p_rem",
                "rate_milli"):
        if not np.array_equal(q[key], q_net[key]):
            fails.append(f"ib_net=True changes `{key}` under the default "
                         "filter; the switch is not a no-op where it must be")
    n_diff = int((q_off["obs_cents"] != q_on["obs_cents"]).sum())
    if not np.array_equal(q_off["cur"], q_on["cur"]):
        fails.append("ib_net changed which pairs qualify; it must only change "
                     "the balance the implied payment is computed on")
    if n_diff == 0:
        fails.append("ib_net changes nothing even with deferred loans in "
                     "sample, so the check is vacuous")
    print(f"  ib_net: inert under the legacy filter, and differs on "
          f"{n_diff:,} of {q_off['cur'].size:,} pairs once deferred loans are "
          f"admitted", file=sys.stderr)
    # the live default must actually differ from the legacy one, or the
    # 2026-08-17 ruling did not reach the code
    if q_now["cur"].size <= q["cur"].size:
        fails.append(f"the live default yields {q_now['cur'].size:,} pairs "
                     f"against the legacy {q['cur'].size:,}; the "
                     "`require_never_deferred` flip did not take effect")
    print(f"  live default : {q_now['cur'].size:,} pairs against the legacy "
          f"{q['cur'].size:,}", file=sys.stderr)

    fails += _selftest_carrier(cache_root)
    fails += _selftest_tables()

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the vectorised filter reproduces the state machine "
          "pair for pair and segment for segment", file=sys.stderr)
    return 0

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command",
                    choices=["build", "status", "verify", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--rows", type=int, default=20000,
                    help="verify: rows per archive to re-read")
    args = ap.parse_args()

    if args.command == "selftest":
        raise SystemExit(cmd_selftest())

    paths = sorted(RAW.glob("*.zip"))
    if args.only:
        keep = set(args.only)
        paths = [p for p in paths if p.stem in keep]
    if not paths:
        print(f"no archives under {RAW}", file=sys.stderr)
        raise SystemExit(1)

    if args.command == "build":
        build_all(paths, workers=args.workers, force=args.force)
    elif args.command == "status":
        cmd_status(paths)
    else:
        raise SystemExit(cmd_verify(paths, args.rows))


if __name__ == "__main__":
    main()
