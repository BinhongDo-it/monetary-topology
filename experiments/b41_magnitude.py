"""B41-3, the companion reading: how big the interaction is, not how persistent.

The joint statistic in the neighbouring file fits the additive model to the time
averaged matrix, so what it reports is the part of the interaction that survives
averaging. That was a deliberate choice and it buys something real: a wedge that
holds its sign for years is not measurement jitter. But it has a consequence that
went unwritten until a state forced it. A square that is large and reverses sign
averages to nothing, and the persistent statistic then reads near zero, which is
indistinguishable in the output from a square that was small all along.

Those two are opposite signals. Against a scalar potential on positions, which
predicts every square is exactly zero on every day, magnitude is what refutes and
persistence is a separate and additional property. So the two are read together
here rather than one standing for both.

    persistent   RMS residual per cycle of the time averaged matrix   (existing)
    magnitude    median over days of the per day RMS residual per cycle
    persistence  persistent / magnitude, unitless, in [0, ~1]

A cell level sign split is printed alongside, because a fraction near one half is
what reversal looks like at the level of the object rather than of a summary.

Reads only what is cached. No network, no key.

    python experiments/b41_magnitude.py --report 3186 3088
    python experiments/b41_magnitude.py --all
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_joint as J
import b41_persistence as P

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "cache"
OUT = REPO / "data" / "b41" / "magnitude.json"

# The coverage each state's rectangle was chosen at, so this file reads the same
# object the joint file read rather than re-selecting one.
COVERAGE = {2892: 0.45, 3088: 0.40}


def iso(s: str) -> str:
    s = (s or "").strip()
    return f"{s[6:10]}-{s[0:2]}-{s[3:5]}" if len(s) >= 10 and s[2] == "/" else s[:10]


def panel(rid: int, cov: float):
    """Days, the chosen rectangle, and the residual matrix for each complete day.

    The matrix is (position, commodity). b41_joint and b41_known_answer build
    the transpose, (commodity, position). Both orientations give identical
    numbers, because the two-way residual commutes with transposition and the
    sum of squares and (m-1)(n-1) are symmetric, so nothing reported has ever
    depended on which one a file uses. Code that indexes a row or a column by
    what it means does depend on it: reading the left singular vectors of this
    matrix as commodities names positions as grades and prints a table that
    looks fine.

    Rows come through the same loader the other two files use. A private one
    written here globbed the same directory without its de-duplication, and the
    single-day cache file overlaps the year file it sits inside, so a cell could
    be counted twice on one day. That inflated the coverage fraction, which
    selected a rectangle that does not exist: Montana came out 6 x 8 over 835
    days instead of 5 x 8 over 445. Two readers of one panel have to load it the
    same way."""
    by_day = P.load_all(rid)
    per_day = {}
    for day, rs in by_day.items():
        c = J.day_cells(rs)
        if c:
            per_day[iso(day)] = c
    best = J.rectangle(per_day, cov)
    if best is None:
        return None
    _, coms, poss = best
    days, mats = [], []
    for day in sorted(per_day):
        c = per_day[day]
        if not all((cm, p) in c for cm in coms for p in poss):
            continue
        m = np.array([[c[(cm, p)] for cm in coms] for p in poss], float)
        days.append(day)
        mats.append(m)
    return coms, poss, days, mats


def per_cycle(res: np.ndarray, df: int) -> float:
    """Same normalisation as the joint file, so the persistent column here must
    reproduce the number printed there. A stray factor of two in the first
    version made every persistent value exactly half of it, which is the kind of
    difference that reads as a finding rather than as an arithmetic slip."""
    return float(np.sqrt((res ** 2).sum() / df))


def run(rid: int, cov: float) -> dict | None:
    got = panel(rid, cov)
    if not got:
        print(f"report {rid}: no rectangle at coverage {cov}")
        return None
    coms, poss, days, mats = got
    if len(days) < 30:
        print(f"report {rid}: only {len(days)} complete days")
        return None
    df = (len(poss) - 1) * (len(coms) - 1)
    mask = np.ones(mats[0].shape, bool)
    daily = []
    cell_signs = defaultdict(list)
    for m in mats:
        r, _, _ = J.additive_residual(m, mask)
        daily.append(per_cycle(r, df))
        for i in range(r.shape[0]):
            for j in range(r.shape[1]):
                cell_signs[(i, j)].append(r[i, j])
    mean_mat = np.mean(mats, axis=0)
    rp, _, _ = J.additive_residual(mean_mat, mask)
    persistent = per_cycle(rp, df)
    magnitude = statistics.median(daily)
    stable = []
    for k, v in cell_signs.items():
        pos = sum(1 for x in v if x > 0)
        stable.append(max(pos, len(v) - pos) / len(v))
    yr = defaultdict(list)
    for d, x in zip(days, daily):
        yr[d[:4]].append(x)
    out = dict(report=rid, coverage=cov, df=df, days=len(days),
               positions=len(poss), commodities=len(coms),
               persistent=persistent, magnitude=magnitude,
               persistence=persistent / magnitude if magnitude else float("nan"),
               cell_sign_stability_median=statistics.median(stable),
               cell_sign_stability_min=min(stable))
    print(f"\n=== report {rid}   {len(poss)}x{len(coms)}  df {df}  "
          f"{len(days)} days  coverage {cov}")
    print(f"    persistent {persistent:7.2f}   magnitude {magnitude:7.2f}   "
          f"persistence {out['persistence']:.3f}")
    print(f"    cell sign stability: median {out['cell_sign_stability_median']:.2f}, "
          f"worst cell {out['cell_sign_stability_min']:.2f}  "
          f"(0.50 is a coin, 1.00 never reverses)")
    print("    per-day magnitude by year: " +
          "  ".join(f"{y}:{statistics.median(v):.1f}" for y, v in sorted(yr.items())))
    return out



def seasonal(rid: int, cov: float) -> dict | None:
    """Whether a low persistence is transience or an unbalanced calendar.

    The persistent statistic averages over whatever days a state's sample holds.
    Basis in this carrier has an annual term, so a state whose coverage sits in a
    few months of the year has its average taken over a season rather than over a
    year, and a second difference that reverses with the crop calendar is then
    beaten down by the composition of the sample rather than by anything about the
    place. The month balanced version weights each calendar month equally: take the
    mean residual matrix inside each month, then average those means. If the low
    reading was composition it rises; if it was transience it does not.
    """
    got = panel(rid, cov)
    if not got:
        return None
    coms, poss, days, mats = got
    if len(days) < 30:
        return None
    df = (len(poss) - 1) * (len(coms) - 1)
    mask = np.ones(mats[0].shape, bool)
    res = [J.additive_residual(m, mask)[0] for m in mats]
    by_month = defaultdict(list)
    for d, r in zip(days, res):
        by_month[d[5:7]].append(r)
    plain = per_cycle(np.mean(res, axis=0), df)
    month_means = [np.mean(v, axis=0) for _, v in sorted(by_month.items())]
    balanced = per_cycle(np.mean(month_means, axis=0), df)
    counts = {m: len(v) for m, v in sorted(by_month.items())}
    n = len(days)
    shares = [c / n for c in counts.values()]
    # effective number of months: the exponential of the entropy of the month
    # shares, so twelve even months read twelve and one month reads one.
    ent = -sum(x * math.log(x) for x in shares if x > 0)
    eff_months = math.exp(ent)
    return dict(report=rid, days=n, months=len(counts),
                effective_months=eff_months,
                plain=plain, balanced=balanced,
                lift=balanced / plain if plain else float("nan"),
                month_counts=counts)


def seasonal_report(ids: list[int], default_cov: float) -> None:
    rows = []
    for rid in ids:
        r = seasonal(rid, COVERAGE.get(rid, default_cov))
        if r:
            rows.append(r)
    rows.sort(key=lambda r: r["effective_months"])
    print(f"{'report':>7} {'days':>5} {'months':>7} {'eff months':>11} "
          f"{'persistent':>11} {'month balanced':>15} {'lift':>7}")
    for r in rows:
        print(f"{r['report']:7d} {r['days']:5d} {r['months']:7d} "
              f"{r['effective_months']:11.2f} {r['plain']:11.2f} "
              f"{r['balanced']:15.2f} {r['lift']:7.2f}")
    print("\nEffective months is the exponential of the entropy of the month shares: "
          "twelve even months read 12.00 and a sample inside one month reads 1.00.")
    print("Lift is the month balanced reading over the plain one. A state whose low "
          "reading came from an uneven calendar lifts; one that is genuinely "
          "transient does not.")
    (REPO / "data" / "b41" / "seasonal.json").write_text(
        json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=1),
        encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, nargs="+")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seasonal", action="store_true",
                    help="month balanced persistence, per state")
    ap.add_argument("--min-coverage", type=float, default=0.60)
    a = ap.parse_args()
    ids = a.report
    if a.all:
        s = json.loads((REPO / "data" / "b41" / "structure.json").read_text(encoding="utf-8"))
        ids = [r["report"] for r in s["reports"]]
    if not ids:
        ap.print_help(); return 0
    if a.seasonal:
        seasonal_report(ids, a.min_coverage)
        return 0
    rows = []
    for rid in ids:
        r = run(rid, COVERAGE.get(rid, a.min_coverage))
        if r:
            rows.append(r)
    if rows:
        rows.sort(key=lambda r: -r["magnitude"])
        print(f"\n{'report':>7} {'df':>3} {'days':>5} {'persistent':>11} "
              f"{'magnitude':>10} {'persistence':>12} {'sign stab':>10}")
        for r in rows:
            print(f"{r['report']:7d} {r['df']:3d} {r['days']:5d} {r['persistent']:11.2f} "
                  f"{r['magnitude']:10.2f} {r['persistence']:12.3f} "
                  f"{r['cell_sign_stability_median']:10.2f}")
        OUT.write_text(json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=1),
                       encoding="utf-8", newline="\n")
        print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
