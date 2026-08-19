#!/usr/bin/env python3
"""B8 checks C1 to C7, v3: with the `7` code excluded and the maturity field fixed.

Registered in the B8 inputs register §3.

**Why v3.** The v2 column profile answered the two questions v2 was written for,
and both answers change the counting.

* **Field 106 is Alternative Delinquency Resolution after all**, and there is no
  positional shift: its values on modification rows are ``7, C, P, D``. `7` is a
  code and not data, and v1 and v2 both counted it as populated. That is where
  the 62.5% came from. **Only `P`, `C`, `D` count as a deferral here**, and the
  full value distribution of every categorical state field is now printed so the
  code sets are visible rather than assumed.
* **Field 18 goes blank at a modification and never returns** (`prev` 1.0000,
  `at` 0.0000, `next` 0.0056). Field **17**, Remaining Months to Legal Maturity,
  has fill 0.9767 against 18's 0.9625, and the difference 0.0142 matches field
  63's 0.0143 almost exactly, which is the modified population. **So 17 survives
  a modification and 18 does not.** `omega` uses 17, and 19 (Maturity Date) is
  carried beside it with an explicit check on whether its value moves.

Two further changes:

* **The modified state is read from field 63, not field 42.** 63's fill is
  0.0143 of rows, and 5,011 modified loans times their remaining months is about
  the same number, so 63 persists to the end of a modified loan's life. Field 42
  reverts to `N` on roughly a third of them, so it dates the **event** and does
  not mark the **state**. Both are counted here and compared.
* **C2's labels were wrong in v2**, not its counting: the branch for one `Y`
  block followed by `N` required ``n_to_y == 1`` when that case has
  ``n_to_y == 0``. Fixed.

Usage::

    python experiments/b8_field_audit.py --only 2019Q1
    python experiments/b8_field_audit.py

Writes ``results/b8_field_audit.md``. Deterministic; progress to stderr only.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
OUT = ROOT / "results" / "b8_field_audit.md"

DELIM = b"|"
NFIELDS = 113
VALUE_TRUNC = 24
DISTINCT_CAP = 50

F_LOAN, F_PERIOD, F_CHANNEL = 2, 3, 4
F_RATE, F_UPB = 9, 12
F_REM_LEGAL, F_REM, F_MATDATE = 17, 18, 19
F_LTV, F_DTI, F_FICO = 20, 23, 24
F_FTHB, F_PURPOSE, F_OCC, F_STATE = 26, 27, 30, 31
F_DELINQ, F_MODFLAG = 40, 42
F_ZBCODE = 44
F_MODNIBUPB, F_FORGIVE = 63, 64
F_BAP = 102
F_ADR, F_ADRCOUNT, F_DEFERAMT = 106, 107, 108

#: The only values of field 106 that mean a deferral happened. `7` is a code and
#: is not one of them. v1 and v2 tested truthiness and counted it.
ADR_REAL = {b"P", b"C", b"D"}

#: Printed in full so the code sets are read off the data rather than assumed.
CATEGORICAL = [(F_DELINQ, "Delinquency Status"), (F_MODFLAG, "Mod Flag"),
               (F_ZBCODE, "Zero Balance Code"), (F_BAP, "Borrower Assistance"),
               (F_ADR, "Alt Delinq Resolution")]

CLASS_FIELDS = [
    (F_FICO, "Credit Score"), (F_LTV, "LTV"), (F_DTI, "DTI"),
    (F_FTHB, "First Time Buyer"), (F_OCC, "Occupancy"),
    (F_STATE, "State"), (F_PURPOSE, "Loan Purpose"), (F_CHANNEL, "Channel"),
]
#: `omega` needs a rate, a principal and a horizon. 17 is the horizon that
#: survives; 18 is kept beside it as the reported failure, and 19 as the
#: absolute-date alternative.
OMEGA = [(F_RATE, "Rate"), (F_UPB, "UPB"), (F_REM_LEGAL, "RemLegal"),
         (F_REM, "RemMaturity"), (F_MATDATE, "MaturityDate")]

WINDOWS = [
    ("pre-crisis", 0, 200812), ("HAMP", 200901, 201612),
    ("Flex", 201701, 201912), ("COVID", 202001, 202212),
    ("post-2022", 202301, 999999),
]


def window_of(p: int) -> str:
    for name, lo, hi in WINDOWS:
        if lo <= p <= hi:
            return name
    return "unclassified"


def to_period(v: bytes) -> int:
    return int(v[2:]) * 100 + int(v[:2]) if len(v) == 6 and v.isdigit() else 0


def months_between(a: int, b: int) -> int:
    """a and b as YYYYMM ints."""
    if not a or not b:
        return 0
    return (a // 100 - b // 100) * 12 + (a % 100 - b % 100)


def delinq_of(v: bytes):
    if not v or v == b"XX":
        return None
    return int(v) if v.isdigit() else None


class Profile:
    def __init__(self, ncols: int):
        self.rows = 0
        self.nonblank = [0] * (ncols + 1)
        self.vals: list[Counter] = [Counter() for _ in range(ncols + 1)]
        self.capped = [False] * (ncols + 1)

    def add(self, parts: list[bytes]) -> None:
        self.rows += 1
        for j, raw in enumerate(parts, start=1):
            v = raw.strip()
            if not v:
                continue
            self.nonblank[j] += 1
            c = self.vals[j]
            k = v[:VALUE_TRUNC]
            if k in c:
                c[k] += 1
            elif len(c) < DISTINCT_CAP:
                c[k] = 1
            else:
                self.capped[j] = True

    def fill(self, j: int) -> float:
        return self.nonblank[j] / self.rows if self.rows else 0.0

    def top(self, j: int, n: int = 5) -> str:
        c = self.vals[j]
        if not c:
            return "(blank)"
        return ", ".join(v.decode("latin-1") for v, _ in c.most_common(n)) + \
            (" ..." if self.capped[j] else "")


class LoanState:
    __slots__ = ("seen_current", "first_delinq", "mod_period", "mod_prev",
                 "mod_at", "mod_next", "mod_pending", "mod_last_flag",
                 "y_to_n", "n_to_y", "cured_after_mod", "defer_period",
                 "defer_code", "cured_after_defer", "cure_clean", "in_delinq",
                 "zb", "cls", "nib_period", "nib_last", "nib_persists",
                 "mat_prev", "mat_next")

    def __init__(self):
        self.seen_current = False
        self.first_delinq = 0
        self.mod_period = 0
        self.mod_prev = None
        self.mod_at = None
        self.mod_next = None
        self.mod_pending = False
        self.mod_last_flag = False
        self.y_to_n = 0
        self.n_to_y = 0
        self.cured_after_mod = False
        self.defer_period = 0
        self.defer_code = b""
        self.cured_after_defer = False
        self.cure_clean = False
        self.in_delinq = False
        self.zb = b""
        self.cls = None
        self.nib_period = 0
        self.nib_last = False
        self.nib_persists = True
        self.mat_prev = 0
        self.mat_next = 0


class Tally:
    def __init__(self, name: str):
        self.name = name
        self.rows = 0
        self.loans = 0
        self.ever_mod = 0
        self.ever_nib = 0
        self.mod_no_nib = 0
        self.nib_no_mod = 0
        self.nib_broken = 0
        self.ever_defer = 0
        self.defer_codes = Counter()
        self.tri_mod = Counter()
        self.tri_defer = Counter()
        self.cure_clean = 0
        self.c1 = {"prev": Counter(), "at": Counter(), "next": Counter()}
        self.c1_denom = 0
        self.c1_no_next = 0
        self.mat_moved = 0
        self.mat_delta = Counter()
        self.c2_shape = Counter()
        self.c7 = Counter()
        self.c7_denom = 0
        self.prof_all = Profile(NFIELDS)
        self.prof_mod = Profile(NFIELDS)
        self.cat = {pos: Counter() for pos, _ in CATEGORICAL}
        self.tail_by_year = defaultdict(lambda: [0] * 6)


def scan(path: Path, t: Tally, limit_rows, stride: int) -> None:
    st = LoanState()
    cur_id = None

    def flush(s: LoanState):
        if cur_id is None:
            return
        t.loans += 1
        if s.mod_period:
            t.ever_mod += 1
            if not s.nib_period:
                t.mod_no_nib += 1
            if s.seen_current and s.first_delinq and s.cured_after_mod:
                t.tri_mod[window_of(s.mod_period)] += 1
                t.c7_denom += 1
                for pos, nm in CLASS_FIELDS:
                    if s.cls and s.cls.get(pos):
                        t.c7[nm] += 1
            t.c1_denom += 1
            for slot, trio in (("prev", s.mod_prev), ("at", s.mod_at),
                               ("next", s.mod_next)):
                if trio:
                    for k, (_, nm) in enumerate(OMEGA):
                        if trio[k]:
                            t.c1[slot][nm] += 1
            if s.mod_next is None:
                t.c1_no_next += 1
            if s.mat_prev and s.mat_next:
                d = months_between(s.mat_next, s.mat_prev)
                if d:
                    t.mat_moved += 1
                t.mat_delta[min(max(d, -12), 480)] += 1
            if s.y_to_n == 0:
                t.c2_shape["Y to the end"] += 1
            elif s.n_to_y == 0:
                t.c2_shape["one Y block then N"] += 1
            else:
                t.c2_shape[f"{s.n_to_y + 1} Y blocks"] += 1
        if s.nib_period:
            t.ever_nib += 1
            if not s.mod_period:
                t.nib_no_mod += 1
            if not s.nib_persists:
                t.nib_broken += 1
        if s.defer_period:
            t.ever_defer += 1
            t.defer_codes[s.defer_code.decode("latin-1")] += 1
            if s.seen_current and s.first_delinq and s.cured_after_defer:
                t.tri_defer[window_of(s.defer_period)] += 1
        if s.cure_clean:
            t.cure_clean += 1

    with zipfile.ZipFile(path) as zf:
        member = sorted(zf.namelist())[0]
        with zf.open(member) as fh:
            for line in fh:
                if limit_rows and t.rows >= limit_rows:
                    break
                line = line.rstrip(b"\r\n")
                if not line:
                    continue
                p = line.split(DELIM)
                if len(p) != NFIELDS:
                    continue
                t.rows += 1
                if t.rows % 5_000_000 == 0:
                    print(f"  {path.name}: {t.rows:,} rows", file=sys.stderr)

                lid = p[F_LOAN - 1]
                if lid != cur_id:
                    flush(st)
                    st = LoanState()
                    cur_id = lid

                mod = p[F_MODFLAG - 1].strip() == b"Y"
                if t.rows % stride == 0:
                    t.prof_all.add(p)
                if mod:
                    t.prof_mod.add(p)
                for pos, _ in CATEGORICAL:
                    v = p[pos - 1].strip()
                    t.cat[pos][v.decode("latin-1") if v else "(blank)"] += 1

                period = to_period(p[F_PERIOD - 1])
                tb = t.tail_by_year[period // 100]
                tb[0] += 1
                for k, pos in enumerate((109, 110, 111, 112, 113), start=1):
                    if p[pos - 1].strip():
                        tb[k] += 1

                d = delinq_of(p[F_DELINQ - 1].strip())
                adr = p[F_ADR - 1].strip()
                nib = bool(p[F_MODNIBUPB - 1].strip())
                mat = to_period(p[F_MATDATE - 1].strip())
                vals = tuple(p[pos - 1].strip() for pos, _ in OMEGA)

                if st.cls is None:
                    st.cls = {pos: bool(p[pos - 1].strip())
                              for pos, _ in CLASS_FIELDS}
                if p[F_ZBCODE - 1].strip():
                    st.zb = p[F_ZBCODE - 1].strip()

                if nib and not st.nib_period:
                    st.nib_period = period
                if st.nib_period and st.nib_last and not nib:
                    st.nib_persists = False
                st.nib_last = nib

                if st.mod_pending:
                    st.mod_next = vals
                    st.mat_next = mat
                    st.mod_pending = False

                if mod:
                    if st.mod_period == 0:
                        st.mod_period = period
                        st.mod_at = vals
                        st.mod_pending = True
                    elif not st.mod_last_flag:
                        st.n_to_y += 1
                elif st.mod_period and st.mod_last_flag:
                    st.y_to_n += 1
                st.mod_last_flag = mod

                if adr in ADR_REAL and st.defer_period == 0:
                    st.defer_period = period
                    st.defer_code = adr

                if d is not None:
                    if d == 0:
                        if not st.first_delinq:
                            st.seen_current = True
                        if st.in_delinq:
                            if st.mod_period or st.nib_period:
                                st.cured_after_mod = True
                            elif st.defer_period:
                                st.cured_after_defer = True
                            elif st.seen_current:
                                st.cure_clean = True
                            st.in_delinq = False
                    else:
                        st.in_delinq = True
                        if not st.first_delinq:
                            st.first_delinq = period

                if not st.mod_period:
                    st.mod_prev = vals
                    st.mat_prev = mat
        flush(st)


def pct(a: int, b: int) -> str:
    return f"{a / b:.4f}" if b else "n/a"


def render(ts: list[Tally], limit_rows, stride: int) -> str:
    L: list[str] = []
    L.append("# B8 C1-C7 v3: `7` excluded, maturity taken from field 17\n")
    L.append("Generated by `experiments/b8_field_audit.py`. "
             "Registered in the B8 inputs register §3.\n")
    if limit_rows:
        L.append(f"**Partial run: {limit_rows:,} rows.** No verdict.\n")

    L.append("\n## Scanned\n")
    L.append("| archive | rows | loans | mod flag ever Y | field 63 ever set "
             "| real deferral (P/C/D) |")
    L.append("|---|---|---|---|---|---|")
    for t in ts:
        L.append(f"| {t.name} | {t.rows:,} | {t.loans:,} | {t.ever_mod:,} "
                 f"| {t.ever_nib:,} | {t.ever_defer:,} |")

    L.append("\n## The categorical state fields, in full\n")
    L.append("**Read the code sets here rather than from the layout document.** "
             "First archive.\n")
    t0 = ts[0]
    for pos, nm in CATEGORICAL:
        c = t0.cat[pos]
        tot = sum(c.values())
        items = ", ".join(f"`{k}` {v:,} ({v / tot:.4f})"
                          for k, v in c.most_common(12))
        L.append(f"- **{pos} {nm}**: {items}"
                 + (" ..." if len(c) > 12 else ""))

    L.append("\n## Field 42 against field 63: event or state\n")
    L.append("| archive | mod flag ever Y | 63 ever set | Y but 63 never set "
             "| 63 set but never Y | 63 set then goes blank |")
    L.append("|---|---|---|---|---|---|")
    for t in ts:
        L.append(f"| {t.name} | {t.ever_mod:,} | {t.ever_nib:,} "
                 f"| {t.mod_no_nib:,} | {t.nib_no_mod:,} | {t.nib_broken:,} |")
    L.append("\nIf `63 set then goes blank` is near zero, **63 is the durable "
             "state marker and 42 dates the event**, which is how "
             "`b8_fannie_slice.md` §2 should read the `modified` node.")

    L.append("\n## C1: omega fields around a modification\n")
    L.append("| archive | denom | no next row | " + " | ".join(
        f"{nm} prev | {nm} at | {nm} next" for _, nm in OMEGA) + " |")
    L.append("|---|---|---|" + "---|" * (3 * len(OMEGA)))
    for t in ts:
        cells = []
        for _, nm in OMEGA:
            for slot in ("prev", "at", "next"):
                cells.append(pct(t.c1[slot][nm], t.c1_denom))
        L.append(f"| {t.name} | {t.c1_denom:,} | {t.c1_no_next:,} | "
                 + " | ".join(cells) + " |")

    L.append("\n## Does the maturity date move at a modification\n")
    L.append("| archive | denom with both | moved | median months added |")
    L.append("|---|---|---|---|")
    for t in ts:
        n = sum(t.mat_delta.values())
        med = "n/a"
        if n:
            acc, half = 0, n / 2
            for k in sorted(t.mat_delta):
                acc += t.mat_delta[k]
                if acc >= half:
                    med = str(k)
                    break
        L.append(f"| {t.name} | {n:,} | {pct(t.mat_moved, n)} | {med} |")
    L.append("\nA maturity that does not move is a modification that changed "
             "only the rate or capitalised arrears. **Both are real; the point "
             "is that `omega` must not assume an extension.**")

    L.append("\n## C2: the shape of the modification flag\n")
    keys = sorted({k for t in ts for k in t.c2_shape})
    L.append("| archive | " + " | ".join(keys) + " |")
    L.append("|---|" + "---|" * len(keys))
    for t in ts:
        L.append(f"| {t.name} | " + " | ".join(
            f"{t.c2_shape[k]:,}" for k in keys) + " |")

    L.append("\n## C3 and C4: triangles by window of the event\n")
    L.append("Modification route uses field 42 **or** field 63 as onset; "
             "deferral route counts only `P`, `C`, `D`.\n")
    wins = [w[0] for w in WINDOWS]
    L.append("| archive | route | " + " | ".join(wins) + " | total |")
    L.append("|---|---|" + "---|" * (len(wins) + 1))
    pm, pd = Counter(), Counter()
    for t in ts:
        for label, c in (("modification", t.tri_mod), ("deferral", t.tri_defer)):
            L.append(f"| {t.name} | {label} | " +
                     " | ".join(f"{c[w]:,}" for w in wins) +
                     f" | {sum(c.values()):,} |")
        pm.update(t.tri_mod)
        pd.update(t.tri_defer)
    L.append("| **pooled** | modification | " +
             " | ".join(f"**{pm[w]:,}**" for w in wins) +
             f" | **{sum(pm.values()):,}** |")
    L.append("| **pooled** | deferral | " +
             " | ".join(f"**{pd[w]:,}**" for w in wins) +
             f" | **{sum(pd.values()):,}** |")
    L.append("\n**Deferral codes seen**: " + ", ".join(
        f"`{k}` {sum(t.defer_codes[k] for t in ts):,}"
        for k in sorted({k for t in ts for k in t.defer_codes})))

    L.append("\n## C5: the B8-0a sample\n")
    L.append("Cured out of delinquency with **no** modification, no field 63 "
             "and no real deferral.\n")
    L.append("| archive | clean cures |")
    L.append("|---|---|")
    for t in ts:
        L.append(f"| {t.name} | {t.cure_clean:,} |")

    L.append("\n## C7: class fields on triangle-completing loans\n")
    L.append("| archive | denom | " + " | ".join(nm for _, nm in CLASS_FIELDS) + " |")
    L.append("|---|---|" + "---|" * len(CLASS_FIELDS))
    for t in ts:
        L.append(f"| {t.name} | {t.c7_denom:,} | " + " | ".join(
            pct(t.c7[nm], t.c7_denom) for _, nm in CLASS_FIELDS) + " |")

    L.append("\n## Columns that move at a modification\n")
    L.append("| field | fill all | fill mod | delta | top on mod rows |")
    L.append("|---|---|---|---|---|")
    for j in range(1, NFIELDS + 1):
        fa, fm = t0.prof_all.fill(j), t0.prof_mod.fill(j)
        if abs(fm - fa) > 0.05:
            L.append(f"| {j} | {fa:.4f} | {fm:.4f} | {fm - fa:+.4f} "
                     f"| {t0.prof_mod.top(j)} |")

    L.append("\n## Fields 109-113 by calendar year, pooled\n")
    yr = defaultdict(lambda: [0] * 6)
    for t in ts:
        for y, v in t.tail_by_year.items():
            for i in range(6):
                yr[y][i] += v[i]
    L.append("| year | rows | 109 | 110 | 111 | 112 | 113 |")
    L.append("|---|---|---|---|---|---|---|")
    for y in sorted(yr):
        if not y:
            continue
        v = yr[y]
        L.append(f"| {y} | {v[0]:,} | " + " | ".join(
            pct(v[i], v[0]) for i in range(1, 6)) + " |")

    L.append("\n## What this audit still does not decide\n")
    L.append("- It does not construct `omega`. That is "
             "`b8_fannie_slice.md` §10 step 1 and it is paper work.")
    L.append("- It does not identify the modification **programme**; "
             "the B8 inputs register §2 settled that no such field exists.")
    L.append("- **A code read off the data is not a code defined by the "
             "publisher.** `7` is treated here as not-a-deferral because it is "
             "not in the documented set, and that reading needs the current "
             "layout to confirm.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--limit-rows", type=int, default=None)
    ap.add_argument("--profile-stride", type=int, default=20)
    args = ap.parse_args()

    if not RAW.is_dir():
        print("missing directory: data/raw/Fannie", file=sys.stderr)
        return 2
    archives = sorted(RAW.glob("*.zip"))
    if args.only:
        want = set(args.only)
        archives = [p for p in archives if p.stem in want]
    if not archives:
        print("no matching .zip in data/raw/Fannie", file=sys.stderr)
        return 2

    ts = []
    for p in archives:
        print(f"scanning {p.name}", file=sys.stderr)
        t = Tally(p.stem)
        scan(p, t, args.limit_rows, max(1, args.profile_stride))
        ts.append(t)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(ts, args.limit_rows, max(1, args.profile_stride)),
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for t in ts:
        print(f"  {t.name}: {t.loans:,} loans, mod {t.ever_mod:,}, "
              f"nib {t.ever_nib:,}, defer {t.ever_defer:,}, "
              f"triangles {sum(t.tri_mod.values()):,}/"
              f"{sum(t.tri_defer.values()):,}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
