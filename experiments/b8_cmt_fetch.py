#!/usr/bin/env python3
"""B8: fetch the Treasury CMT curve and measure what is actually there.

Registered in ``docs/b8_fannie_slice.md`` §16.11. **This file measures; it does
not settle the two construction choices §16.11 requires.** Those are ruled after
this runs, on the numbers, because the last time this stage reasoned from a
document instead of counting it was wrong (`b8_inputs_availability.md` §6.2.10.2).

**Why the curve matters and where it sits.** `b8_omega.py` P2 proves the
discount curve cancels on a contract triple, so B8-0a needed no Treasury data.
The cancellation needs `V` and `V-hat` to share one `(i, n, d)`, and **at a
modification the rate moves and the term moves**, so `k(i, d, n)` differs on the
two sides and the curve enters. B8-0b's `N` is the dispersion of loop sums on
the modification triangle, so **the curve is upstream of B8-0b**, not beside it.

**Two sources, cross-checked, and that is the point of the file.**

  * **Treasury's own publication** is primary: the issuer publishes the curve it
    defines. Same principle as taking the LLPA grid from Fannie and the
    delinquency partition from the file's own field.
  * **FRED's `DGS*` series** is a re-publisher and is fetched as a second
    opinion.

A gap that appears in one and not the other is a **download artefact**. A gap in
both, on the same months, is a **property of the curve**. Nothing downstream can
tell those apart from one source, and this stage has already paid once for
treating an unverified inference as a fact.

**Nothing is deleted.** Raw responses land under ``data/raw/cmt/`` and stay.

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_cmt_fetch.py fetch          # both sources, to disk
    python experiments/b8_cmt_fetch.py fetch --source fred
    python experiments/b8_cmt_fetch.py report         # census + cross-check
    python experiments/b8_cmt_fetch.py need           # what B8 actually demands
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

RAW = K.ROOT / "data" / "raw" / "cmt"
OUT = K.ROOT / "results" / "b8_cmt_availability.md"

#: The Treasury publishes one CSV per calendar year. The endpoint has been
#: written more than one way over the years, so every documented shape is tried
#: and **the one that worked is recorded in the output**, rather than a single
#: guess failing silently.
TREASURY_URLS = [
    ("daily-treasury-rates.csv/{y}/all",
     "https://home.treasury.gov/resource-center/data-chart-center/"
     "interest-rates/daily-treasury-rates.csv/{y}/all"
     "?type=daily_treasury_yield_curve&field_tdr_date_value={y}"
     "&page&_format=csv"),
    ("daily-treasury-rates.csv/all/{y}",
     "https://home.treasury.gov/resource-center/data-chart-center/"
     "interest-rates/daily-treasury-rates.csv/all/{y}"
     "?type=daily_treasury_yield_curve&field_tdr_date_value={y}"
     "&page&_format=csv"),
]

#: FRED's constant-maturity series. No key needed for the graph CSV endpoint.
FRED_SERIES = {
    "1 Mo": "DGS1MO", "3 Mo": "DGS3MO", "6 Mo": "DGS6MO",
    "1 Yr": "DGS1", "2 Yr": "DGS2", "3 Yr": "DGS3", "5 Yr": "DGS5",
    "7 Yr": "DGS7", "10 Yr": "DGS10", "20 Yr": "DGS20", "30 Yr": "DGS30",
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

#: The tenors a mortgage horizon can land on, in months, so a remaining term can
#: be matched to what the curve actually carries.
TENOR_MONTHS = {
    "1 Mo": 1, "2 Mo": 2, "3 Mo": 3, "4 Mo": 4, "6 Mo": 6,
    "1 Yr": 12, "2 Yr": 24, "3 Yr": 36, "5 Yr": 60, "7 Yr": 84,
    "10 Yr": 120, "20 Yr": 240, "30 Yr": 360,
}

#: The archives cover originations from 2002, and a 360-month loan originated in
#: 2002 is still alive in 2032. The window is deliberately wider than the data
#: so a gap at either end is visible rather than clipped away.
YEAR_LO, YEAR_HI = 1990, 2026

UA = {"User-Agent": "b8-research/1.0 (monetary-topology; academic use)"}


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_treasury(years) -> dict:
    """One CSV per year, saved raw. Returns {year: (shape_used, n_bytes)}."""
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    for y in years:
        dest = RAW / f"treasury_{y}.csv"
        if dest.exists():
            log[y] = ("cached", dest.stat().st_size)
            continue
        last = None
        for shape, tmpl in TREASURY_URLS:
            try:
                body = _get(tmpl.format(y=y))
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError) as e:
                last = f"{shape}: {e}"
                continue
            head = body[:200].decode("utf-8", "replace")
            if "Date" not in head:
                last = f"{shape}: no Date header, head={head!r}"
                continue
            dest.write_bytes(body)
            log[y] = (shape, len(body))
            break
        else:
            log[y] = ("FAILED", last)
        print(f"  treasury {y}: {log[y][0]}", file=sys.stderr)
    return log


def fetch_fred() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    for label, sid in FRED_SERIES.items():
        dest = RAW / f"fred_{sid}.csv"
        if dest.exists():
            log[label] = ("cached", dest.stat().st_size)
            continue
        try:
            body = _get(FRED_URL.format(sid=sid))
            dest.write_bytes(body)
            log[label] = ("ok", len(body))
        except Exception as e:                                  # noqa: BLE001
            log[label] = ("FAILED", str(e))
        print(f"  fred {sid}: {log[label][0]}", file=sys.stderr)
    return log


# ---------------------------------------------------------------------------


def _month(datestr: str) -> int | None:
    """`MM/DD/YYYY` or `YYYY-MM-DD` to a month index on b8_core's epoch."""
    s = datestr.strip()
    if not s:
        return None
    if "/" in s:
        p = s.split("/")
        if len(p) != 3:
            return None
        m, y = int(p[0]), int(p[2])
    elif "-" in s:
        p = s.split("-")
        if len(p) != 3:
            return None
        y, m = int(p[0]), int(p[1])
    else:
        return None
    if y < K.EPOCH_YEAR:
        return None
    return (y - K.EPOCH_YEAR) * 12 + (m - 1)


def _yyyymm(mi: int) -> str:
    return f"{K.EPOCH_YEAR + mi // 12:04d}-{mi % 12 + 1:02d}"


def load_treasury() -> tuple[dict, list[str]]:
    """``({(month_index, tenor_label): [values]}, filenames)``.

    **The annotation said `-> dict` until 2026-08-17 and the docstring
    described only the first element.** `b8_loop_omega.curve_table` was written
    against that and passed the whole pair on, which died on its first real run
    with `'tuple' object has no attribute 'items'`. A stale signature is a
    stale name (pit 34) with a type attached.
    """
    out = defaultdict(list)
    files = sorted(RAW.glob("treasury_*.csv"))
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        rd = csv.DictReader(io.StringIO(text))
        for row in rd:
            dk = next((k for k in row if k and k.strip().lower() == "date"),
                      None)
            if dk is None:
                continue
            mi = _month(row[dk] or "")
            if mi is None:
                continue
            for k, v in row.items():
                if not k or k is dk:
                    continue
                lab = k.strip()
                if lab not in TENOR_MONTHS:
                    continue
                v = (v or "").strip()
                if not v or v.upper() in {"N/A", "NA", "."}:
                    continue
                try:
                    out[(mi, lab)].append(float(v))
                except ValueError:
                    continue
    return out, [f.name for f in files]


def load_fred() -> tuple[dict, list[str]]:
    """``({(month_index, tenor_label): [values]}, filenames)``, as above."""
    out = defaultdict(list)
    files = []
    for label, sid in FRED_SERIES.items():
        f = RAW / f"fred_{sid}.csv"
        if not f.exists():
            continue
        files.append(f.name)
        rd = csv.reader(io.StringIO(f.read_text(encoding="utf-8",
                                                errors="replace")))
        rows = list(rd)
        if not rows:
            continue
        for row in rows[1:]:
            if len(row) < 2:
                continue
            mi = _month(row[0])
            if mi is None:
                continue
            v = row[1].strip()
            if not v or v == ".":
                continue
            try:
                out[(mi, label)].append(float(v))
            except ValueError:
                continue
    return out, files


def _runs(missing: list[int]) -> list[tuple[int, int]]:
    """Consecutive months collapsed into (first, last) runs."""
    if not missing:
        return []
    missing = sorted(missing)
    runs, s, p = [], missing[0], missing[0]
    for m in missing[1:]:
        if m == p + 1:
            p = m
            continue
        runs.append((s, p))
        s = p = m
    runs.append((s, p))
    return runs


def report() -> int:
    tre, tre_files = load_treasury()
    fre, fre_files = load_fred()
    if not tre and not fre:
        print("nothing under data/raw/cmt. Run: "
              "python experiments/b8_cmt_fetch.py fetch", file=sys.stderr)
        return 1

    lo = K.EPOCH_YEAR
    span = [(y - lo) * 12 + m for y in range(YEAR_LO, YEAR_HI + 1)
            for m in range(12)]
    tenors = [t for t in TENOR_MONTHS if t in FRED_SERIES or
              any(k[1] == t for k in tre)]

    L = []
    A = L.append
    A("# B8: what the CMT curve actually carries, month by month\n")
    A("Generated by `experiments/b8_cmt_fetch.py`. Registered in "
      "`docs/b8_fannie_slice.md` §16.11.\n")
    A("**This measures. It does not settle §16.11's two construction "
      "choices**, which are ruled after this, on these numbers.\n")
    A("**Reads no prediction.**\n")

    A("\n## 0. What was fetched\n")
    A(f"Treasury: {len(tre_files)} yearly files. FRED: {len(fre_files)} "
      f"series. Raw responses are under `data/raw/cmt/` and are not deleted.\n")

    A("\n## 1. Coverage per tenor, and the gaps, on each source separately\n")
    A("A month counts as present when the source reports at least one "
      "business day of that tenor in it. **Gaps are printed as dated runs, "
      "not as a count**, because §16.11's question is whether a specific "
      "window is missing, not how many months are.\n")
    for src_name, src in (("Treasury", tre), ("FRED", fre)):
        if not src:
            continue
        A(f"\n### 1.{'12'[src_name != 'Treasury']} {src_name}\n")
        A("| tenor | first | last | months present | **gaps inside the "
          "covered span** |")
        A("|---|---|---|---|---|")
        for t in tenors:
            got = sorted(mi for (mi, lab) in src if lab == t)
            if not got:
                A(f"| `{t}` | - | - | 0 | **absent entirely** |")
                continue
            inner = [m for m in range(got[0], got[-1] + 1)
                     if m not in set(got)]
            runs = _runs(inner)
            gap = ", ".join(f"**{_yyyymm(a)}..{_yyyymm(b)}** ({b - a + 1}m)"
                            for a, b in runs) or "none"
            A(f"| `{t}` | {_yyyymm(got[0])} | {_yyyymm(got[-1])} | "
              f"{len(got):,} | {gap} |")

    A("\n## 2. The cross-check: is a gap a property of the curve or of the "
      "download\n")
    A("**A gap in one source only is a download artefact. A gap in both, on "
      "the same months, is the curve.** One source cannot tell those apart "
      "and this stage has already paid once for treating an unverified "
      "inference as a fact.\n")
    if tre and fre:
        A("| tenor | months in both | **only Treasury** | **only FRED** | "
          "max abs difference of monthly means |")
        A("|---|---|---|---|---|")
        for t in tenors:
            a = {mi for (mi, lab) in tre if lab == t}
            b = {mi for (mi, lab) in fre if lab == t}
            both = a & b
            worst = 0.0
            for mi in both:
                ma = sum(tre[(mi, t)]) / len(tre[(mi, t)])
                mb = sum(fre[(mi, t)]) / len(fre[(mi, t)])
                worst = max(worst, abs(ma - mb))
            A(f"| `{t}` | {len(both):,} | {len(a - b):,} | {len(b - a):,} | "
              f"{worst:.4f} |")
        A("\n**A non-trivial difference column means the two sources are not "
          "the same series** and the primary one governs, with the "
          "discrepancy recorded rather than averaged away.\n")
    else:
        A("**Only one source is on disk, so this check did not run and no "
          "gap below is established as a property of the curve.**\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def need() -> int:
    """What B8 actually demands of the curve, so a gap can be weighted.

    A dated gap only matters where the stage needs that tenor in that month.
    The demand is one cell per modification: the month it happened and the
    remaining legal term at that row, which is the horizon `V` has to discount.
    """
    import numpy as np
    import b8_triangles as T

    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()
                   and not p.name.startswith("209")) if root.exists() else []
    if not names:
        print("no core table.", file=sys.stderr)
        return 1

    cells = defaultdict(int)
    rem_at = defaultdict(list)
    for n in names:
        with K.Core(n) as c:
            t = T.triangles(c)
            tri = t["triangle"]
            period = c.row["period"].astype(np.int32)
            rem = c.row["rem_legal"].astype(np.int32)
            is_mod = c.row["mod_flag"] == K._Y
            first_mod = T._first_pos_per_loan(c, is_mod)
            sel = tri & (first_mod >= 0)
            rows = first_mod[sel]
            mi = period[rows]
            rl = rem[rows]
            ok = (mi != K.U16_NA) & (rl != K.U16_NA)
            for m, r in zip(mi[ok].tolist(), rl[ok].tolist()):
                cells[m] += 1
                rem_at[m].append(r)
        print(f"  {n}: {int(sel.sum()):,} modifications on triangles",
              file=sys.stderr)

    L = []
    A = L.append
    A("\n## 3. What B8 actually demands of the curve\n")
    A("One cell per triangle-completing modification: the month it happened "
      "and the **remaining legal term at that row**, which is the horizon "
      "`V` has to discount. **A dated gap in the curve only bites where this "
      "table has mass.**\n")
    A("**§16.11's second question is two questions.** A remaining term of 362 "
      "months is one month past the longest tenor and any capping rule moves "
      "the discount by nothing. A remaining term of 480 is a **term "
      "extension**, which is the population B8 exists to measure, and capping "
      "it at 30 years discards the thing being measured. The split is counted "
      "below rather than read off a `max` column.\n")
    tot = sum(cells.values())
    allr = np.concatenate([np.asarray(v) for v in rem_at.values()]) \
        if rem_at else np.zeros(0)
    A("| horizon | modifications past it | share |")
    A("|---|---|---|")
    for b in BEYOND:
        n = int((allr > b).sum())
        A(f"| > {b} months | {n:,} | {n / tot:.4f} |" if tot else
          f"| > {b} months | {n:,} | - |")
    A("")
    A("| month | modifications | remaining term p10 | p50 | p90 | max | "
      "**needs a tenor beyond 30 Yr?** |")
    A("|---|---|---|---|---|---|---|")
    import numpy as np
    for m in sorted(cells):
        r = np.asarray(rem_at[m])
        q = np.quantile(r, [.1, .5, .9])
        A(f"| {_yyyymm(m)} | {cells[m]:,} | {q[0]:.0f} | {q[1]:.0f} | "
          f"{q[2]:.0f} | {r.max():.0f} | "
          f"{'**yes**' if r.max() > 360 else 'no'} |")

    txt = "\n".join(L) + "\n"
    if OUT.exists():
        OUT.write_text(OUT.read_text(encoding="utf-8") + txt,
                       encoding="utf-8", newline="\n")
        print(f"appended §3 to {OUT}", file=sys.stderr)
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(txt, encoding="utf-8", newline="\n")
        print(f"wrote {OUT}", file=sys.stderr)
    return 0


#: Horizons past the longest published tenor, split so that "one month past
#: 30 years" is not counted as the same problem as "forty-year term". The
#: first is rounding and any capping rule moves the discount by nothing; the
#: second is a term extension, which is the population B8 exists to measure.
BEYOND = [360, 366, 372, 396, 420, 480]


def probe() -> int:
    """The two questions §16.11 asks, measured rather than reasoned about.

    **One.** Treasury and FRED disagree on 47 months of the 30-year tenor and
    the 30-year is also the one tenor whose monthly means differ by an order of
    magnitude more than any other. One of the two is carrying something in
    those months that the other is not, and **which one it is decides whether
    the gap exists at all**. The values are printed beside the neighbouring
    tenors, because a spliced long-term composite sits between the 10 and 20
    year and a genuine 30-year does not have to.

    **Two.** Where the maximum disagreement sits in time, for every tenor. A
    five-basis-point maximum in 1990 and the same number inside the disputed
    window are different findings.
    """
    tre, _ = load_treasury()
    fre, _ = load_fred()
    if not tre or not fre:
        print("both sources are needed for this probe", file=sys.stderr)
        return 1

    def mean(src, mi, lab):
        v = src.get((mi, lab))
        return sum(v) / len(v) if v else None

    L = ["\n## 4. The two sources disagree on the 30-year, and this is where\n"]
    A = L.append
    A("**Neither source is trusted over the other by assertion here.** "
      "Treasury is the issuer and governs, but *what FRED is carrying in the "
      "disputed months* is the thing that says whether the gap is a property "
      "of the curve or a splice, and that is a number, not a judgement.\n")

    disputed = sorted({mi for (mi, lab) in fre if lab == "30 Yr"}
                      - {mi for (mi, lab) in tre if lab == "30 Yr"})
    A(f"{len(disputed)} months are in FRED's 30-year and not in Treasury's. "
      "Below, every fourth one, with the neighbouring tenors from **FRED** so "
      "the comparison is inside one source.\n")
    A("| month | FRED 30 Yr | FRED 20 Yr | FRED 10 Yr | **30 Yr minus 20 Yr** "
      "| Treasury 20 Yr |")
    A("|---|---|---|---|---|---|")
    for mi in disputed[::4]:
        a = mean(fre, mi, "30 Yr")
        b = mean(fre, mi, "20 Yr")
        c = mean(fre, mi, "10 Yr")
        d = mean(tre, mi, "20 Yr")
        gap = f"{a - b:+.4f}" if (a is not None and b is not None) else "-"
        A(f"| {_yyyymm(mi)} | {a if a is None else f'{a:.4f}'} | "
          f"{b if b is None else f'{b:.4f}'} | "
          f"{c if c is None else f'{c:.4f}'} | **{gap}** | "
          f"{d if d is None else f'{d:.4f}'} |")
    A("\n**A 30-year that sits below the 20-year, or that tracks it to within "
      "rounding, is not a 30-year.** A genuine long bond in this period traded "
      "above the 20-year for most of it.\n")

    A("\nWhere the maximum monthly-mean disagreement sits, per tenor.\n")
    A("| tenor | max abs difference | **in which month** | difference in the "
      "disputed window |")
    A("|---|---|---|---|")
    dis = set(disputed)
    for t in TENOR_MONTHS:
        both = ({mi for (mi, lab) in tre if lab == t}
                & {mi for (mi, lab) in fre if lab == t})
        if not both:
            continue
        worst, at = 0.0, None
        for mi in both:
            d = abs(mean(tre, mi, t) - mean(fre, mi, t))
            if d > worst:
                worst, at = d, mi
        # **A zero here can mean two opposite things** and printing the same
        # 0.0000 for both is the same defect as printing a minimum without
        # naming its level. An empty overlap is `no overlap`, not agreement.
        ov = both & dis
        inw = f"{max((abs(mean(tre, mi, t) - mean(fre, mi, t)) for mi in ov)):.4f}" \
            if ov else "**no overlap**"
        A(f"| `{t}` | {worst:.4f} | {_yyyymm(at) if at else '-'} | {inw} |")

    txt = "\n".join(L) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.write_text(OUT.read_text(encoding="utf-8") + txt,
                       encoding="utf-8", newline="\n")
        print(f"appended §4 to {OUT}", file=sys.stderr)
    else:
        OUT.write_text(txt, encoding="utf-8", newline="\n")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command",
                    choices=["fetch", "report", "need", "probe"])
    ap.add_argument("--source", choices=["treasury", "fred", "both"],
                    default="both")
    ap.add_argument("--from-year", type=int, default=YEAR_LO)
    ap.add_argument("--to-year", type=int, default=YEAR_HI)
    args = ap.parse_args()

    if args.command == "fetch":
        if args.source in ("treasury", "both"):
            fetch_treasury(range(args.from_year, args.to_year + 1))
        if args.source in ("fred", "both"):
            fetch_fred()
        print("fetched into " + str(RAW), file=sys.stderr)
        raise SystemExit(0)
    if args.command == "report":
        raise SystemExit(report())
    if args.command == "probe":
        raise SystemExit(probe())
    raise SystemExit(need())


if __name__ == "__main__":
    main()
