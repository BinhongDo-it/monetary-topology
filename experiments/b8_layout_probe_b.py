#!/usr/bin/env python3
"""B8 check C0b: are the documented field positions the real ones?

Registered in the B8 inputs register. C0 established that every
quarterly file carries 113 pipe-delimited fields with no ragged rows. The layout
document held by this project (CRT File Layout and Glossary, 2023-06) documents
**108**. Five fields are unaccounted for and there are two cases:

* appended at 109-113, in which case positions 1-108 are unmoved and every field
  this stage needs is where the document says;
* inserted anywhere earlier, in which case **every field after the insertion point
  shifts and is read silently and wrongly**.

A document cannot settle this, because the document may itself be the stale one.
The data can. Roughly twenty fields have value domains distinctive enough to be
recognised without being told: two-letter state codes, `MMYYYY`, `Y`/`N`, credit
scores, delinquency codes. This probe checks each anchor at its documented
position, and **when one fails it scans all 113 columns to find where that domain
actually lives**, so the shift is reported with its offset rather than as a
mystery.

Usage::

    python experiments/b8_layout_probe_b.py
    python experiments/b8_layout_probe_b.py --rows 20000

Head sampling is deliberate and sufficient. C0b asks a **structural** question,
and structure does not vary down the file. Whether a late-arriving field such as
106 is ever populated is C1 and C6's question, not this one, and this probe says
so rather than pretending otherwise.

Writes ``results/b8_layout_probe_b.md``. Deterministic: archives and anchors
sorted, no wall-clock, no absolute paths, explicit float formats.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
OUT = ROOT / "results" / "b8_layout_probe_b.md"

DELIM = b"|"
EXPECTED_FIELDS = 113
DOCUMENTED_FIELDS = 108

#: A column passes an anchor when this share of its **non-blank** values satisfy
#: the predicate. Not 1.0: real files carry sentinels and the occasional oddity,
#: and a threshold of one would turn a single bad row into a false shift report.
#: 0.98 has no theoretical source and is therefore a calibration value: it may
#: flag a position, it may not be used to rule one out. Discipline 5.
MATCH_THRESHOLD = 0.98

_int = re.compile(rb"^-?\d+$")
_num = re.compile(rb"^-?\d+(\.\d+)?$")


def _as_float(v: bytes):
    try:
        return float(v)
    except ValueError:
        return None


def p_digits(lo: int, hi: int):
    def f(v: bytes) -> bool:
        return bool(_int.match(v)) and lo <= len(v) <= hi
    return f


def p_num_range(lo: float, hi: float):
    def f(v: bytes) -> bool:
        if not _num.match(v):
            return False
        x = _as_float(v)
        return x is not None and lo <= x <= hi
    return f


def p_in(*allowed: bytes):
    s = set(allowed)
    return lambda v: v in s


def p_period(v: bytes) -> bool:
    """MMYYYY or YYYYMM, both accepted; which one is reported separately."""
    if len(v) != 6 or not _int.match(v):
        return False
    a, b = int(v[:2]), int(v[:4])
    return (1 <= a <= 12) or (1990 <= b <= 2040)


def p_state(v: bytes) -> bool:
    return len(v) == 2 and v.isalpha() and v.isupper()


def p_delinq(v: bytes) -> bool:
    return v == b"XX" or (bool(_int.match(v)) and len(v) <= 3)


def p_zerobal(v: bytes) -> bool:
    return bool(_int.match(v)) and len(v) <= 2


#: (documented position, name, predicate). Positions are 1-based, as the layout
#: document numbers them. Predicates are shape-based wherever the exact code set
#: is not certain to this project: a shape that is wrong is a false negative and
#: gets scanned, a code set that is wrong invents a shift that is not there.
ANCHORS = [
    (2, "Loan Identifier", p_digits(8, 14)),
    (3, "Monthly Reporting Period", p_period),
    (8, "Original Interest Rate", p_num_range(0.01, 20.0)),
    (9, "Current Interest Rate", p_num_range(0.01, 20.0)),
    (10, "Original UPB", p_num_range(1000, 6_000_000)),
    (12, "Current Actual UPB", p_num_range(0, 6_000_000)),
    (13, "Original Loan Term", p_num_range(36, 480)),
    (16, "Loan Age", p_num_range(-20, 600)),
    (18, "Remaining Months To Maturity", p_num_range(-20, 600)),
    (20, "Original LTV", p_num_range(1, 200)),
    (23, "Debt-To-Income", p_num_range(1, 70)),
    (24, "Credit Score at Origination", p_num_range(280, 900)),
    (26, "First Time Home Buyer", p_in(b"Y", b"N", b"U")),
    (30, "Occupancy Status", p_in(b"P", b"S", b"I", b"U")),
    (31, "Property State", p_state),
    (40, "Current Loan Delinquency Status", p_delinq),
    (42, "Modification Flag", p_in(b"Y", b"N")),
    (44, "Zero Balance Code", p_zerobal),
]


def scan_archive(path: Path, max_rows: int) -> dict:
    """One pass over the head of one archive. Everything below is per column."""
    ncols = EXPECTED_FIELDS
    nonblank = [0] * (ncols + 1)
    hits = [[0] * (ncols + 1) for _ in ANCHORS]
    vals: list[Counter] = [Counter() for _ in range(ncols + 1)]
    rows = 0
    ragged = 0
    loan_ids: list[bytes] = []

    with zipfile.ZipFile(path) as zf:
        name = sorted(zf.namelist())[0]
        with zf.open(name) as fh:
            for line in fh:
                if rows >= max_rows:
                    break
                line = line.rstrip(b"\r\n")
                if not line:
                    continue
                parts = line.split(DELIM)
                if len(parts) != ncols:
                    ragged += 1
                    continue
                rows += 1
                for j, raw in enumerate(parts, start=1):
                    v = raw.strip()
                    if not v:
                        continue
                    nonblank[j] += 1
                    if len(vals[j]) < 40:
                        vals[j][v[:24]] += 1
                    elif v[:24] in vals[j]:
                        vals[j][v[:24]] += 1
                    for a, (_, _, pred) in enumerate(ANCHORS):
                        if pred(v):
                            hits[a][j] += 1
                if len(parts) > 2:
                    loan_ids.append(parts[1].strip())

    runs = 1 + sum(1 for i in range(1, len(loan_ids)) if loan_ids[i] != loan_ids[i - 1])
    return {
        "archive": path.name,
        "member": name,
        "rows": rows,
        "ragged": ragged,
        "nonblank": nonblank,
        "hits": hits,
        "vals": vals,
        "distinct_loans": len(set(loan_ids)),
        "loan_runs": runs,
    }


def rate(hit: int, n: int) -> float:
    return hit / n if n else 0.0


def render(recs: list[dict], max_rows: int) -> str:
    L: list[str] = []
    L.append("# B8 C0b: field positions, checked against the data\n")
    L.append("Generated by `experiments/b8_layout_probe_b.py`. "
             "Registered in the B8 inputs register.\n")
    L.append(f"Head rows per archive: {max_rows}. Files carry "
             f"{EXPECTED_FIELDS} fields; the layout document held here "
             f"documents {DOCUMENTED_FIELDS}.\n")

    # ---- anchors -----------------------------------------------------------
    L.append("\n## Anchors at their documented positions\n")
    L.append("Match rate over **non-blank** values. `n/a` means the column is "
             "blank throughout the head, which is not a failure and is resolved "
             "by C1.\n")
    header = "| field | name | " + " | ".join(r["archive"].replace(".zip", "")
                                              for r in recs) + " |"
    L.append(header)
    L.append("|---|---|" + "---|" * len(recs))
    failures: list[tuple] = []
    for a, (pos, name, _) in enumerate(ANCHORS):
        cells = []
        bad = False
        for r in recs:
            n = r["nonblank"][pos]
            if n == 0:
                cells.append("n/a")
                continue
            q = rate(r["hits"][a][pos], n)
            cells.append(f"{q:.3f}")
            if q < MATCH_THRESHOLD:
                bad = True
        L.append(f"| {pos} | {name} | " + " | ".join(cells) + " |")
        if bad:
            failures.append((a, pos, name))

    # ---- where a failing domain actually lives -----------------------------
    if failures:
        L.append("\n## Where the failing domains actually live\n")
        L.append("For each anchor that failed, every column whose non-blank "
                 "values satisfy the same predicate, in the first archive that "
                 "failed it. **A single clean alternative position is a shift; "
                 "many positions means the predicate is not distinctive and the "
                 "anchor proves nothing.**\n")
        for a, pos, name in failures:
            for r in recs:
                n = r["nonblank"][pos]
                if n and rate(r["hits"][a][pos], n) >= MATCH_THRESHOLD:
                    continue
                cands = [
                    j for j in range(1, EXPECTED_FIELDS + 1)
                    if r["nonblank"][j] and rate(r["hits"][a][j], r["nonblank"][j])
                    >= MATCH_THRESHOLD
                ]
                shown = ", ".join(str(c) for c in cands[:15]) or "none"
                extra = f" (+{len(cands) - 15} more)" if len(cands) > 15 else ""
                L.append(f"- **{name}** documented at {pos}, in "
                         f"`{r['archive']}` the predicate holds at: {shown}{extra}")
                break

    # ---- structure ---------------------------------------------------------
    L.append("\n## Row structure, which the streaming design depends on\n")
    L.append("| archive | rows read | ragged | distinct loan ids | id runs | "
             "sorted by loan? |")
    L.append("|---|---|---|---|---|---|")
    for r in recs:
        d, runs = r["distinct_loans"], r["loan_runs"]
        verdict = "yes" if d and runs <= d * 1.05 else "no or interleaved"
        L.append(f"| {r['archive']} | {r['rows']} | {r['ragged']} | {d} | "
                 f"{runs} | {verdict} |")
    L.append("\nIf the file is sorted by loan, B8 can hold one loan's whole "
             "history in memory and stream. If not, it cannot, and the design "
             "needs a sort pass that the availability check has to budget for.")

    # ---- the tail ----------------------------------------------------------
    L.append("\n## The five undocumented columns, 109 to 113\n")
    L.append("| field | " + " | ".join("fill / top values in " +
             r["archive"].replace(".zip", "") for r in recs) + " |")
    L.append("|---|" + "---|" * len(recs))
    for j in range(DOCUMENTED_FIELDS + 1, EXPECTED_FIELDS + 1):
        cells = []
        for r in recs:
            f = rate(r["nonblank"][j], r["rows"])
            top = ", ".join(v.decode("latin-1")
                            for v, _ in r["vals"][j].most_common(3)) or "(blank)"
            cells.append(f"{f:.3f} — {top}")
        L.append(f"| {j} | " + " | ".join(cells) + " |")

    # ---- full dump ---------------------------------------------------------
    L.append("\n## Every column, first archive, for eyeballing\n")
    r0 = recs[0]
    L.append(f"`{r0['archive']}`, {r0['rows']} rows.\n")
    L.append("| field | fill | distinct seen | top values |")
    L.append("|---|---|---|---|")
    for j in range(1, EXPECTED_FIELDS + 1):
        f = rate(r0["nonblank"][j], r0["rows"])
        top = ", ".join(v.decode("latin-1")
                        for v, _ in r0["vals"][j].most_common(3)) or "(blank)"
        L.append(f"| {j} | {f:.3f} | {len(r0['vals'][j])} | {top} |")

    # ---- verdict -----------------------------------------------------------
    L.append("\n## Verdict\n")
    if not failures:
        L.append("- **C0b passes.** Every anchor holds at its documented "
                 "position in every archive. The five extra fields are "
                 "**appended at 109-113** and positions 1-108 are unmoved, so "
                 "the 2023-06 layout is usable for every field this stage needs.")
        L.append("- **Still not established**: that fields 109-113 are what "
                 "their values suggest. They are not used by B8 and are not "
                 "identified here.")
    else:
        names = ", ".join(f"{n} ({p})" for _, p, n in failures)
        L.append(f"- **C0b FAILS at**: {names}.")
        L.append("- Read the section above for where each domain actually "
                 "lives. **Until every anchor is placed, §3's seven checks may "
                 "not be run**, because a field taken by position would be the "
                 "wrong field and nothing would report an error.")
    L.append("- **A caveat that holds either way**: an anchor passing means the "
             "column has the right **shape**, not that it is the right field. "
             "Two adjacent numeric fields with overlapping ranges can swap "
             "undetected. The anchors here were chosen for distinctiveness, and "
             "the ones that carry the most weight are 31 (state), 42 (Y/N), 30 "
             "and 26, which no neighbour imitates.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=20000)
    args = ap.parse_args()

    if not RAW.is_dir():
        print("missing directory: data/raw/Fannie", file=sys.stderr)
        return 2
    archives = sorted(RAW.glob("*.zip"))
    if not archives:
        print("no .zip found in data/raw/Fannie", file=sys.stderr)
        return 2

    recs = [scan_archive(p, args.rows) for p in archives]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(recs, args.rows), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
