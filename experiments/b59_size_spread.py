"""B59 size arm: the fed funds price by bank size as the Call Report reads it,
and the checks that decide whether that instrument can carry a cross-sectional
reading at all.

**The reading this arm is after.**  Every eligible institution reads one
administered rate, `IORB`.  The Board's own review prints that large domestic
banks pay 13 to 17 basis points less than smaller domestic banks for the same
overnight borrowing.  Reading that difference ourselves rather than citing it
needs a price per bank per quarter, and the only public source at that grain is
the Call Report.

**The instrument.**  `experiments/b59_call_report.py` builds the panel from the
public bulk archives: fed funds purchased (`B993`), repo sold (`B995`), total
assets (`2170`), and one expense line covering both liabilities (`4180`, filed
year to date).  Where a filer's repo is zero at quarter end the expense line is
read as its fed funds bill, and a cost is formed as

    annualised cost, percent = 400 x (the quarter's own expense) / (fed funds balance)

where the quarter's own expense is the year-to-date figure differenced against
the prior quarter, and Q1 stands alone.

**What the first pass read, and why it is not a size difference.**  The yearly
median cost tracks the effective fed funds rate closely, with a slope well
under one.  Across size bands, after removing each quarter's median, the
largest band sits about 13 basis points under the smallest over the whole
window, which lands on the Board's figure.  Split by rate environment the sign
reverses: about 25 under at the zero bound, above the smallest band once rates
leave the floor, and far above it in 2023-26.  A number that changes sign
between two eras of its own sample reports a mixture weight when pooled.

**The denominator check.**  The expense is a flow over the quarter and the
balance is a stock on its last day.  Where a bank borrows on some days of a
quarter and not others, the quarter-end balance can sit far from the balance
the expense accrued on, and a ratio of the two is a price only on average.
Two arms test it:

- `average`: the first pass's own rows, divided instead by the mean of this
  and the previous quarter-end balance.  Nothing else changes, including the
  filter, so a previous quarter that carried repo stays in.
- `persistent`: rows with fed funds at both quarter ends and repo at neither,
  read twice, once over each denominator.  The two readings share every row,
  so what separates them is the denominator and nothing else, and what
  separates this arm from the first pass is who is in it.

**The average the expense accrued on is filed.**  Schedule RC-K carries the
quarter's average of fed funds purchased and repo sold together (`3353`), and
the driver reads it from there.  The arm that uses it:

- `rc_k`: repo zero at both quarter ends, a positive expense, divided by the
  RC-K quarterly average.  No quarter-end fed funds balance enters.  2009 has
  no RC-K in the product used for that year, so this arm starts in 2010.
- `rc_k_persistent`, `rc_k_sporadic`: the same rows split by whether fed funds
  were carried at both quarter ends or at neither the previous one.  The form
  lets a filer compute the average from Wednesday closes instead of daily
  closes, and a bank that borrows on a few days is where that choice can move
  the average, so the split is where it would show.
- `rc_k_stable`: fed funds at both ends, each within a quarter of the RC-K
  average (the 0.8 to 1.25 band is a chosen tolerance and enters no criterion),
  the rows where all three balances describe the same position.

**The filter check, `--decompose`.**  Every RC-K arm keeps only filers with no
repo at either quarter end, and a filer that carries no repo may not be a
typical one.  The expense line is one bill for two liabilities, so for a filer
carrying both the cost is a blend,

    cost over EFFR = a + b x w,    w = the repo share of the two liabilities,

with `w` taken as the mean of the repo share at the two quarter ends (the
average itself is filed only for the two together).  Fitted by least absolute
deviations within a band and a rate environment, `a` is the fed funds spread a
filer at `w = 0` would pay and `a + b` the repo spread at `w = 1`.  Fitted on
the filers that carry both, `a` is a fed funds price read without the filter.
It leans on one assumption, that within a band and an environment the repo
price is common; the spread of repo-only filers' costs is printed next to it
so the assumption can be seen holding or failing.  Filers with neither
liability at either quarter end have no weight and are left out and counted.

For every arm the band medians are also printed against the quarter's mean
effective rate, cost minus EFFR in basis points, which is the level a reader
can check against what a bank of that size is known to pay.

`--balances` prints, for the rows where all three are defined, how the
quarter-end balance and the mean of two quarter ends sit against the RC-K
average, split by whether the bank carried fed funds at the previous quarter
end.  That is the direct look at the mechanism the other arms infer.

**`--fdic`** reads the RC-K arm against the nearest size class named in rule
text, the FDIC's $10 billion line between small and large institutions (12 CFR
327.8, four consecutive quarterly reports to change class).  The line's rate
schedules overlap between the two classes, and its large-institution scorecard
names fed funds purchased and repo while the small-institution ratios do not, so
the line writes a formula term on this position rather than a value per class.
It prints cost against EFFR by finer asset segment and by era (the base that
counts fed funds purchased took effect on 1 April 2011), and two steps read the
same way: across the line, and inside the small class.

**`--board`** rebuilds the Board's own classes, the fifteen largest holders of
reserve balances against the rest of the FR 2420 domestic panel, over the
Board's window from 2015Q4 to 2017Q1, and counts what the instrument can read in
each.  The Board's rates also pool Eurodollar borrowing, which a bank books as
deposits in foreign offices, and the archive files the interest on those on a
line of its own (`RIAD4172`, INTEREST ON DEPOSITS-FOREIGN OFFICES), apart from
the `4180` this instrument reads.

**`--bankers`** reads the one class rule text names on the lending side of this
position.  12 CFR 327.5(b) lets a banker's bank exclude from its assessment base
the reserve balances it passes through to the Federal Reserve, those it holds
there for its own account and its fed funds sold, up to its deposits of
depository institutions plus its fed funds purchased, and has it certify each
quarter.  A filer is in the class in a quarter when it certifies (`K656`) and
deducts (`K657`) in that quarter; the certification alone is also ticked by
filers whose deduction is zero, and those are listed.  The class's borrowing
price is the RC-K arm.  Its lending price is the same arm on the asset leg: the
quarter's income on fed funds sold and reverse repo (`4020`) over their RC-K
average (`3365`), where reverse repo is absent at both quarter ends.  Both, and
the margin between them, are printed against EFFR by era next to the filers
outside the class whose assets fall inside the class's range that quarter, with
the deduction against its limit (`K658`) and every class filer on its own.

**`--write`** runs all of it and writes `results/b59_size_spread.json` with its
criteria; `--selftest` plants the failures those criteria have to report.

**`--anchor`** reruns that first pass as it was run, with 2009Q2 treated as
absent (that period was not on disk yet; it arrived later from the one-year
product), and prints which of the first pass's numbers this code reproduces.

Units: balances and expenses in thousands of dollars as filed; costs in percent
a year; cross-sectional gaps in basis points.  Nothing here fetches anything;
the panel cache and the rate series are read from disk.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from b59_call_report import LEGS

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "b59_call_report.json"
EFFR_CSV = ROOT / "data" / "b59" / "EFFR.csv"
RESULT = ROOT / "results" / "b59_size_spread.json"

WINDOW = ("2009Q1", "2026Q2")

#: total assets are filed in thousands of dollars
BANDS = (
    ("10bn and over", 10_000_000, None),
    ("1bn to 10bn", 1_000_000, 10_000_000),
    ("250m to 1bn", 250_000, 1_000_000),
    ("under 250m", None, 250_000),
)
LARGEST, SMALLEST = BANDS[0][0], BANDS[-1][0]

#: calendar years, cut the way the first pass cut them
NEAR_ZERO = frozenset(range(2009, 2016)) | frozenset((2020, 2021))
REGIMES = (
    ("all", "whole window", lambda y: True),
    ("zero_bound", "near the zero bound, 2009-15 and 2020-21", lambda y: y in NEAR_ZERO),
    ("off_floor", "off the floor, every other year", lambda y: y not in NEAR_ZERO),
    ("high", "2023-26", lambda y: y >= 2023),
)

#: Bootstrap of band medians, two ways.  Resampling (filer, quarter)
#: observations is what the first pass did and is kept so its numbers can be
#: compared.  Resampling filers, each with all its quarters, is the one that
#: respects the independent unit: the largest band in 2023-26 is 93 observations
#: from 20 filers, and a quarter of one bank is not independent of its next
#: quarter.  The gap is read against the filer-level standard error.  Two seeds
#: are run and both printed, because a resampled standard error has a
#: resolution of its own and a single seed hides it.
DRAWS = 2000
SEEDS = (0, 1)

#: What the first pass printed, kept only so `--anchor` can say which of its
#: numbers this code reproduces.  Band medians and gaps were printed to one
#: decimal, the validity fit to four.
FIRST_PASS = {
    "rows": 14295,
    "median_rows_per_quarter": 192,
    "years": 18,
    "validity": {"corr": 0.9848, "slope": 0.5812, "intercept": 0.2534},
    "bands": {"10bn and over": (413, -6.8), "1bn to 10bn": (1609, -6.0),
              "250m to 1bn": (3878, -8.2), "under 250m": (8395, 6.6)},
    "gap": {"all": (413, 8395, -13.5), "zero_bound": (189, 3964, -25.3),
            "off_floor": (224, 4431, 43.4), "high": (93, 1393, 143.3)},
    "gap_se": {"all": 2.8, "zero_bound": 2.1, "off_floor": 9.1, "high": 37.7},
}


@dataclass(frozen=True)
class Row:
    period: str
    rssd: str
    ff: float
    rp: float
    ff_prev: float | None
    rp_prev: float | None
    expense: float
    assets: float
    average: float | None


def prev_quarter(per: str) -> str:
    y, q = int(per[:4]), int(per[-1])
    return f"{y}Q{q - 1}" if q > 1 else f"{y - 1}Q4"


def load_panel(path: Path = CACHE) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {per: rec["filers"] for per, rec in raw.items()}


def load_effr(path: Path = EFFR_CSV):
    """Calendar-year and calendar-quarter means of the daily series, business
    days only (the source leaves the others blank)."""
    years, quarters = collections.defaultdict(list), collections.defaultdict(list)
    with path.open(encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        #: ask the file what its column is before reading it as the rate
        if head[1:] != ["EFFR"]:
            raise SystemExit(f"{path.name}: expected one EFFR column, found {head}")
        for day, value in rd:
            if not value.strip():
                continue
            v = float(value)
            y, m = int(day[:4]), int(day[5:7])
            years[y].append(v)
            quarters[f"{y}Q{(m - 1) // 3 + 1}"].append(v)
    return ({k: sum(v) / len(v) for k, v in years.items()},
            {k: sum(v) / len(v) for k, v in quarters.items()})


def quarter_rows(panel: dict, start: str, end: str, absent=()) -> list[Row]:
    """One row per (filer, quarter) that has a quarter's own expense.

    `absent` names periods to treat as not on disk.  It exists for one use,
    reproducing a reading made before a period arrived, and it removes the
    period from the panel entirely: its own rows go, and so do the next
    quarter's, which need it to difference against.
    """
    have = {p: f for p, f in panel.items() if p not in absent}
    rows = []
    for per in sorted(p for p in have if start <= p <= end):
        cur, prev = have[per], have.get(prev_quarter(per))
        for rssd, v in cur.items():
            ytd, assets = v.get("4180"), v.get("2170")
            if ytd is None or assets is None:
                continue
            pv = prev.get(rssd) if prev is not None else None
            if per.endswith("Q1"):
                expense = ytd
            elif pv is None or pv.get("4180") is None:
                continue
            else:
                expense = ytd - pv["4180"]
            rows.append(Row(per, rssd, v.get("B993") or 0.0, v.get("B995") or 0.0,
                            None if pv is None else (pv.get("B993") or 0.0),
                            None if pv is None else (pv.get("B995") or 0.0),
                            expense, assets, v.get("3353")))
    return rows


def arm_quarter_end(rows: list[Row]):
    """The first pass: repo zero at this quarter end, fed funds positive at this
    quarter end, a positive expense, divided by this quarter end's balance."""
    return [(r, 400.0 * r.expense / r.ff) for r in rows
            if r.ff > 0 and r.rp == 0 and r.expense > 0]


def arm_average(rows: list[Row]):
    """The first pass's rows, over the mean of this and the previous quarter-end
    fed funds balance.  A row whose previous quarter is not on disk has no mean
    and drops out."""
    return [(r, 400.0 * r.expense / (0.5 * (r.ff + r.ff_prev))) for r in rows
            if r.ff > 0 and r.rp == 0 and r.expense > 0 and r.ff_prev is not None]


def arm_persistent(rows: list[Row], denominator: str):
    """Fed funds at both quarter ends, repo at neither, a positive expense; the
    same rows under either denominator."""
    keep = [r for r in rows if r.ff > 0 and r.rp == 0 and r.expense > 0
            and r.ff_prev is not None and r.ff_prev > 0 and r.rp_prev == 0]
    if denominator == "quarter_end":
        return [(r, 400.0 * r.expense / r.ff) for r in keep]
    if denominator == "average":
        return [(r, 400.0 * r.expense / (0.5 * (r.ff + r.ff_prev))) for r in keep]
    raise ValueError(denominator)


def arm_rc_k(rows: list[Row]):
    """Repo zero at both quarter ends, a positive expense, over the quarter's
    RC-K average of fed funds and repo together."""
    return [(r, 400.0 * r.expense / r.average) for r in rows
            if r.rp == 0 and r.rp_prev == 0 and r.expense > 0
            and r.average is not None and r.average > 0]


def arm_rc_k_split(rows: list[Row], which: str):
    """`arm_rc_k` split by the fed funds position at the two quarter ends."""
    keep = {
        "persistent": lambda r: r.ff > 0 and r.ff_prev > 0,
        "sporadic": lambda r: r.ff_prev == 0,
        "stable": lambda r: (r.ff > 0 and r.ff_prev > 0
                             and STABLE[0] <= r.ff / r.average <= STABLE[1]
                             and STABLE[0] <= r.ff_prev / r.average <= STABLE[1]),
    }[which]
    return [(r, c) for r, c in arm_rc_k(rows) if keep(r)]


#: the tolerance `rc_k_stable` uses; a chosen number, entering no criterion
STABLE = (0.8, 1.25)


ARMS = {
    "quarter_end": ("first pass: quarter-end balance, repo zero at quarter end",
                    arm_quarter_end),
    "average": ("first pass's rows over the mean of two quarter-end balances",
                arm_average),
    "persistent_quarter_end": ("fed funds at both ends, repo at neither; quarter-end balance",
                               lambda rows: arm_persistent(rows, "quarter_end")),
    "persistent_average": ("fed funds at both ends, repo at neither; mean balance",
                           lambda rows: arm_persistent(rows, "average")),
    "rc_k": ("repo at neither end; the RC-K quarterly average", arm_rc_k),
    "rc_k_persistent": ("as rc_k, fed funds at both quarter ends",
                        lambda rows: arm_rc_k_split(rows, "persistent")),
    "rc_k_sporadic": ("as rc_k, no fed funds at the previous quarter end",
                      lambda rows: arm_rc_k_split(rows, "sporadic")),
    "rc_k_stable": ("as rc_k_persistent, both ends within the stable band of the average",
                    lambda rows: arm_rc_k_split(rows, "stable")),
}


def levels(obs, effr_quarter: dict) -> dict:
    """Band medians of cost minus the quarter's mean EFFR, in basis points."""
    out = {}
    for key, label, keep in REGIMES:
        cells = collections.defaultdict(list)
        for r, c in obs:
            if keep(int(r.period[:4])):
                cells[band_of(r.assets)].append(100.0 * (c - effr_quarter[r.period]))
        out[key] = [{"band": name, "n": len(cells[name]),
                     "median_bp_over_effr": statistics.median(cells[name]) if cells[name] else None}
                    for name, *_ in BANDS]
    return out


def balances(rows: list[Row]) -> list[dict]:
    """Quarter-end and two-end-mean balances against the RC-K average, by band
    and by whether fed funds were carried at the previous quarter end.  Rows
    with repo at neither end and fed funds at this quarter end, so all three
    balances are defined and refer to the same liability."""
    cells = collections.defaultdict(list)
    for r in rows:
        if not (r.rp == 0 and r.rp_prev == 0 and r.ff > 0
                and r.average is not None and r.average > 0):
            continue
        start = "fed funds at the previous end" if r.ff_prev > 0 else "none at the previous end"
        cells[(band_of(r.assets), start)].append(
            (r.ff / r.average, 0.5 * (r.ff + r.ff_prev) / r.average))
    out = []
    for name, *_ in BANDS:
        for start in ("fed funds at the previous end", "none at the previous end"):
            v = cells.get((name, start), [])
            if not v:
                continue
            out.append({"band": name, "previous_end": start, "n": len(v),
                        "median_quarter_end_over_average": statistics.median(x for x, _ in v),
                        "median_two_end_mean_over_average": statistics.median(y for _, y in v)})
    return out


def _share(ff: float, rp: float):
    total = ff + rp
    return None if total <= 0 else rp / total


def decomposition_rows(rows: list[Row], effr_quarter: dict):
    """(row, repo weight, cost over EFFR in bp) for every filer with a positive
    expense, an RC-K average and a position at one quarter end or both."""
    out, no_weight = [], 0
    for r in rows:
        if not (r.expense > 0 and r.average is not None and r.average > 0
                and r.ff_prev is not None):
            continue
        shares = [s for s in (_share(r.ff, r.rp), _share(r.ff_prev, r.rp_prev))
                  if s is not None]
        if not shares:
            no_weight += 1
            continue
        out.append((r, sum(shares) / len(shares),
                    100.0 * (400.0 * r.expense / r.average - effr_quarter[r.period])))
    return out, no_weight


def lad_line(w, y, lo: float = -5000.0, hi: float = 5000.0, iters: int = 90):
    """Least absolute deviations for y = a + b w.  For a given slope the best
    intercept is the median of the residual, and the objective left over is
    convex in the slope, so a golden-section search on the slope finds it.
    The bracket is fifty percentage points either way."""
    w, y = np.asarray(w, dtype=float), np.asarray(y, dtype=float)

    def objective(b):
        res = y - b * w
        a = np.median(res)
        return float(np.abs(res - a).sum()), float(a)

    g = (5 ** 0.5 - 1) / 2
    x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
    f1, f2 = objective(x1)[0], objective(x2)[0]
    for _ in range(iters):
        if f1 <= f2:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - g * (hi - lo)
            f1 = objective(x1)[0]
        else:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + g * (hi - lo)
            f2 = objective(x2)[0]
    b = 0.5 * (lo + hi)
    return objective(b)[1], b


def lad_gap_se(big, small, draws: int, seed: int) -> float:
    """Filer-level bootstrap standard error of the difference between two LAD
    intercepts.  `big` and `small` are lists of (filer, weight, spread)."""
    rng = np.random.default_rng(seed)

    def prep(cell):
        _u, inv = np.unique(np.array([c[0] for c in cell]), return_inverse=True)
        return (np.array([c[1] for c in cell]), np.array([c[2] for c in cell]),
                inv, int(inv.max()) + 1)

    cells = (prep(big), prep(small))
    gaps = np.empty(draws)
    for i in range(draws):
        intercepts = []
        for w, y, inv, k in cells:
            counts = rng.multinomial(k, np.full(k, 1.0 / k))
            idx = np.repeat(np.arange(w.size), counts[inv])
            intercepts.append(lad_line(w[idx], y[idx])[0])
        gaps[i] = intercepts[0] - intercepts[1]
    return float(np.std(gaps))


#: bootstrap draws for the LAD gap; each draw is two golden-section fits
DECOMPOSE_DRAWS = 200


def decompose(rows: list[Row], effr_quarter: dict, draws: int = DECOMPOSE_DRAWS,
              seeds=SEEDS) -> dict:
    data, no_weight = decomposition_rows(rows, effr_quarter)
    out = {"left_out_no_position_at_either_end": no_weight, "regimes": {}}
    for key, label, keep in REGIMES:
        by_band = collections.defaultdict(list)
        for r, w, y in data:
            if keep(int(r.period[:4])):
                by_band[band_of(r.assets)].append((r.rssd, w, y))
        bands = []
        for name, *_ in BANDS:
            cell = by_band[name]
            strata = {"w=0": [c for c in cell if c[1] == 0.0],
                      "mixed": [c for c in cell if 0.0 < c[1] < 1.0],
                      "w=1": [c for c in cell if c[1] == 1.0]}
            row = {"band": name}
            for s, v in strata.items():
                row[s] = {"n": len(v), "filers": len({c[0] for c in v}),
                          "median_bp_over_effr": statistics.median(c[2] for c in v) if v else None}
            one = sorted(c[2] for c in strata["w=1"])
            if one:
                row["w=1"]["quartiles_bp_over_effr"] = [one[int(0.25 * (len(one) - 1))],
                                                         one[int(0.75 * (len(one) - 1))]]
            if strata["mixed"]:
                a, b = lad_line([c[1] for c in strata["mixed"]], [c[2] for c in strata["mixed"]])
                row["mixed_fit"] = {"fed_funds_at_w0_bp": a, "repo_at_w1_bp": a + b}
            a, b = lad_line([c[1] for c in cell], [c[2] for c in cell])
            row["all_fit"] = {"fed_funds_at_w0_bp": a, "repo_at_w1_bp": a + b}
            bands.append((row, strata))
        big_row, big_strata = bands[0]
        small_row, small_strata = bands[-1]
        z_big = [c[2] for c in big_strata["w=0"]]
        z_small = [c[2] for c in small_strata["w=0"]]
        gap_w0 = statistics.median(z_big) - statistics.median(z_small)
        se_w0 = {}
        for s in seeds:
            rng = np.random.default_rng(s)
            cb = cluster_boot_medians(z_big, [c[0] for c in big_strata["w=0"]], DRAWS, rng)
            cs = cluster_boot_medians(z_small, [c[0] for c in small_strata["w=0"]], DRAWS, rng)
            se_w0[str(s)] = float(np.std(cb - cs))
        gap_mixed = (big_row["mixed_fit"]["fed_funds_at_w0_bp"]
                     - small_row["mixed_fit"]["fed_funds_at_w0_bp"])
        se_mixed = {str(s): lad_gap_se(big_strata["mixed"], small_strata["mixed"], draws, s)
                    for s in seeds}
        out["regimes"][key] = {
            "label": label,
            "bands": [row for row, _s in bands],
            "gap_w0_medians_bp": gap_w0, "gap_w0_se_bp_resampling_filers": se_w0,
            "gap_mixed_fit_bp": gap_mixed, "gap_mixed_fit_se_bp_resampling_filers": se_mixed,
        }
    return out


def print_decompose(d: dict) -> None:
    print(f"  left out, no position at either quarter end: {d['left_out_no_position_at_either_end']:,}")
    for key, blk in d["regimes"].items():
        print(f"\n  {blk['label']}:  cost over EFFR, bp")
        print(f"    {'band':<14} {'w=0 n/filers':>14} {'median':>8}  {'mixed n/filers':>15} "
              f"{'fit a':>7} {'fit a+b':>8}  {'w=1 n/filers':>14} {'median':>8} {'quartiles':>15}  {'all-fit a':>9}")
        for b in blk["bands"]:
            z, mx, one = b["w=0"], b["mixed"], b["w=1"]
            q = one.get("quartiles_bp_over_effr")
            fit = b.get("mixed_fit", {})
            print(f"    {b['band']:<14} {str(z['n']) + '/' + str(z['filers']):>14} "
                  f"{z['median_bp_over_effr']:>+8.1f}  {str(mx['n']) + '/' + str(mx['filers']):>15} "
                  f"{fit.get('fed_funds_at_w0_bp', float('nan')):>+7.1f} {fit.get('repo_at_w1_bp', float('nan')):>+8.1f}  "
                  f"{str(one['n']) + '/' + str(one['filers']):>14} {one['median_bp_over_effr']:>+8.1f} "
                  f"{(format(q[0], '+.0f') + ' to ' + format(q[1], '+.0f')) if q else '-':>15}  "
                  f"{b['all_fit']['fed_funds_at_w0_bp']:>+9.1f}")
        s0, s1 = (str(s) for s in SEEDS)
        print(f"    largest minus smallest, w=0 medians: {blk['gap_w0_medians_bp']:+.1f} bp, filer se "
              f"{blk['gap_w0_se_bp_resampling_filers'][s0]:.2f}/{blk['gap_w0_se_bp_resampling_filers'][s1]:.2f}")
        print(f"    largest minus smallest, mixed-fit a: {blk['gap_mixed_fit_bp']:+.1f} bp, filer se "
              f"{blk['gap_mixed_fit_se_bp_resampling_filers'][s0]:.2f}/{blk['gap_mixed_fit_se_bp_resampling_filers'][s1]:.2f}")


def fit(x, y) -> dict:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return {"corr": sxy / (sxx * syy) ** 0.5, "slope": sxy / sxx,
            "intercept": my - sxy / sxx * mx}


def validity(obs, effr_year: dict) -> dict:
    """Yearly median cost against the yearly mean of the effective rate."""
    by_year = collections.defaultdict(list)
    for r, cost in obs:
        by_year[int(r.period[:4])].append(cost)
    table = [{"year": y, "n": len(by_year[y]),
              "median_cost_pct": statistics.median(by_year[y]),
              "effr_pct": effr_year[y]} for y in sorted(by_year)]
    per_q = collections.Counter(r.period for r, _ in obs)
    return {"rows": len(obs), "quarters": len(per_q),
            "median_rows_per_quarter": statistics.median(per_q.values()),
            "years": len(table),
            **fit([t["effr_pct"] for t in table], [t["median_cost_pct"] for t in table]),
            "by_year": table}


def band_of(assets: float) -> str:
    for name, lo, hi in BANDS:
        if (lo is None or assets >= lo) and (hi is None or assets < hi):
            return name
    raise ValueError(assets)


def boot_medians(values, draws: int, rng) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    out = np.empty(draws)
    step = max(1, 2_000_000 // max(1, v.size))
    for i in range(0, draws, step):
        k = min(step, draws - i)
        out[i:i + k] = np.median(v[rng.integers(0, v.size, size=(k, v.size))], axis=1)
    return out


def cluster_boot_medians(values, clusters, draws: int, rng) -> np.ndarray:
    """Medians of resamples that draw clusters with replacement and keep every
    observation of each drawn cluster, computed as weighted medians over the
    sorted values so no resample is materialised.  Even-sized resamples take
    the mean of the two middle values, as `np.median` does."""
    v = np.asarray(values, dtype=float)
    order = np.argsort(v, kind="stable")
    v = v[order]
    _ids, cidx = np.unique(np.asarray(clusters)[order], return_inverse=True)
    n_clusters = int(cidx.max()) + 1
    out = np.empty(draws)
    step = max(1, 4_000_000 // max(1, v.size))
    for i in range(0, draws, step):
        k = min(step, draws - i)
        m = rng.multinomial(n_clusters, np.full(n_clusters, 1.0 / n_clusters), size=k)
        cum = np.cumsum(m[:, cidx], axis=1)
        total = cum[:, -1]
        lo = np.argmax(cum >= ((total + 1) // 2)[:, None], axis=1)
        hi = np.argmax(cum >= (total // 2 + 1)[:, None], axis=1)
        out[i:i + k] = 0.5 * (v[lo] + v[hi])
    return out


def cross_section(obs, draws: int = DRAWS, seeds=SEEDS) -> dict:
    """Band medians of cost after removing each quarter's median, by regime."""
    by_q = collections.defaultdict(list)
    for r, c in obs:
        by_q[r.period].append(c)
    centre = {q: statistics.median(v) for q, v in by_q.items()}
    marked = [(r, 100.0 * (c - centre[r.period]), band_of(r.assets)) for r, c in obs]
    out = {}
    for key, label, keep in REGIMES:
        sub = [m for m in marked if keep(int(m[0].period[:4]))]
        vals = {name: [bp for _r, bp, b in sub if b == name] for name, *_ in BANDS}
        filers = {name: len({r.rssd for r, _bp, b in sub if b == name}) for name, *_ in BANDS}
        big, small = vals[LARGEST], vals[SMALLEST]
        big_ids = [r.rssd for r, _bp, b in sub if b == LARGEST]
        small_ids = [r.rssd for r, _bp, b in sub if b == SMALLEST]
        gap = statistics.median(big) - statistics.median(small)
        se_obs, se_filer = {}, {}
        for s in seeds:
            rng = np.random.default_rng(s)
            mb, ms = boot_medians(big, draws, rng), boot_medians(small, draws, rng)
            se_obs[str(s)] = float(np.std(mb - ms))
            rng = np.random.default_rng(s)
            cb = cluster_boot_medians(big, big_ids, draws, rng)
            cs = cluster_boot_medians(small, small_ids, draws, rng)
            se_filer[str(s)] = float(np.std(cb - cs))
        out[key] = {
            "label": label,
            "bands": [{"band": name, "n": len(vals[name]), "filers": filers[name],
                       "median_bp": statistics.median(vals[name]) if vals[name] else None}
                      for name, *_ in BANDS],
            "gap_largest_minus_smallest_bp": gap,
            "gap_se_bp_resampling_observations": se_obs,
            "gap_se_bp_resampling_filers": se_filer,
        }
    return out


def print_validity(v: dict) -> None:
    print(f"  validity: {v['rows']:,} (filer, quarter) rows over {v['quarters']} quarters, "
          f"median {v['median_rows_per_quarter']} a quarter, {v['years']} years")
    print(f"    yearly median cost on yearly mean EFFR: corr {v['corr']:.4f}  "
          f"slope {v['slope']:.4f}  intercept {v['intercept']:.4f}")
    print("    year      n   median cost %   EFFR %")
    for t in v["by_year"]:
        print(f"    {t['year']}  {t['n']:>5}   {t['median_cost_pct']:>12.4f}   {t['effr_pct']:>6.4f}")


def print_cross(xs: dict) -> None:
    for key, block in xs.items():
        print(f"  {block['label']}:")
        for b in block["bands"]:
            med = "     -" if b["median_bp"] is None else f"{b['median_bp']:>+8.2f}"
            print(f"    {b['band']:<14} n {b['n']:>6,}  filers {b['filers']:>5,}  median {med} bp")
        gap = block["gap_largest_minus_smallest_bp"]
        so, sf = block["gap_se_bp_resampling_observations"], block["gap_se_bp_resampling_filers"]
        print(f"    largest minus smallest {gap:+.2f} bp")
        print(f"      se resampling observations "
              + " / ".join(f"{so[str(s)]:.2f}" for s in SEEDS)
              + f"   resampling filers " + " / ".join(f"{sf[str(s)]:.2f}" for s in SEEDS)
              + f"   (seeds {', '.join(map(str, SEEDS))})")
        print(f"      |gap| / filer se {abs(gap) / sf[str(SEEDS[0])]:.2f}")


def print_summary(key: str, label: str, v: dict, xs: dict, lv: dict | None = None) -> None:
    """One arm in a few lines: the validity fit, then per regime the band
    medians, the gap and its filer-level standard error."""
    print(f"\n[{key}] {label}")
    print(f"  {v['rows']:,} rows, {v['quarters']} quarters; yearly median on EFFR: corr "
          f"{v['corr']:.4f}  slope {v['slope']:.4f}  intercept {v['intercept']:.4f}")
    names = [name for name, *_ in BANDS]
    print("  " + " " * 26 + "".join(f"{n:>15}" for n in names)
          + "      gap   filer se  |gap|/se")
    for rk, block in xs.items():
        meds = "".join(("            -" if b["median_bp"] is None else f"{b['median_bp']:>+13.2f}") + "  "
                       for b in block["bands"])
        sf = block["gap_se_bp_resampling_filers"]
        gap = block["gap_largest_minus_smallest_bp"]
        print(f"  {block['label'][:24]:<26}{meds}{gap:>+8.2f} {sf[str(SEEDS[0])]:>9.2f}"
              f"/{sf[str(SEEDS[1])]:<6.2f} {abs(gap) / sf[str(SEEDS[0])]:>6.2f}")
        print("  " + " " * 26 + "".join(f"{('n ' + format(b['n'], ',') + ' / ' + str(b['filers'])):>15}"
                                         for b in block["bands"]))
        if lv is not None:
            over = "".join(("            -" if b["median_bp_over_effr"] is None
                            else f"{b['median_bp_over_effr']:>+13.2f}") + "  " for b in lv[rk])
            print(f"  {'  over EFFR':<26}{over}")


def compare_first_pass(v: dict, xs: dict) -> list[tuple[str, str, str, bool]]:
    """Which printed numbers come back.  One-decimal numbers count as reproduced
    when this code's value rounds to them; four-decimal ones likewise."""
    rows = []
    def same(mine, theirs, places):
        return abs(mine - theirs) <= 0.5 * 10 ** -places + 1e-9
    rows.append(("rows", str(v["rows"]), str(FIRST_PASS["rows"]), v["rows"] == FIRST_PASS["rows"]))
    rows.append(("median rows a quarter", str(v["median_rows_per_quarter"]),
                 str(FIRST_PASS["median_rows_per_quarter"]),
                 v["median_rows_per_quarter"] == FIRST_PASS["median_rows_per_quarter"]))
    rows.append(("years", str(v["years"]), str(FIRST_PASS["years"]), v["years"] == FIRST_PASS["years"]))
    for k, theirs in FIRST_PASS["validity"].items():
        rows.append((f"validity {k}", f"{v[k]:.4f}", f"{theirs:.4f}", same(v[k], theirs, 4)))
    for b in xs["all"]["bands"]:
        n, med = FIRST_PASS["bands"][b["band"]]
        rows.append((f"band {b['band']} n", str(b["n"]), str(n), b["n"] == n))
        rows.append((f"band {b['band']} median bp", f"{b['median_bp']:+.2f}", f"{med:+.1f}",
                     same(b["median_bp"], med, 1)))
    for key, (nb, ns, gap) in FIRST_PASS["gap"].items():
        blk = xs[key]
        mine_nb, mine_ns = blk["bands"][0]["n"], blk["bands"][-1]["n"]
        rows.append((f"{key} n largest / smallest", f"{mine_nb} / {mine_ns}", f"{nb} / {ns}",
                     (mine_nb, mine_ns) == (nb, ns)))
        rows.append((f"{key} gap bp", f"{blk['gap_largest_minus_smallest_bp']:+.2f}", f"{gap:+.1f}",
                     same(blk["gap_largest_minus_smallest_bp"], gap, 1)))
        se0 = blk["gap_se_bp_resampling_observations"][str(SEEDS[0])]
        rows.append((f"{key} gap se bp", f"{se0:.2f}", f"{FIRST_PASS['gap_se'][key]:.1f}",
                     same(se0, FIRST_PASS["gap_se"][key], 1)))
    return rows


def load_cache(path: Path = CACHE):
    """The panel and, per period, what the driver recorded about reading it."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    panel = {per: rec["filers"] for per, rec in raw.items()}
    meta = {per: {"archive": rec["archive"],
                  "columns_used": rec.get("columns_used", {}),
                  "columns_refused": rec.get("columns_refused", [])}
            for per, rec in raw.items()}
    return panel, meta


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rounded(obj, places: int = 4):
    """Floats through one explicit precision, so two machines write one byte
    stream and a last-digit difference between numerical builds stays out."""
    if isinstance(obj, float):
        return round(obj, places)
    if isinstance(obj, dict):
        return {k: rounded(v, places) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [rounded(v, places) for v in obj]
    return obj


#: 12 CFR 327.8: a small institution has assets below $10 billion and a large one
#: $10 billion or more, and a filer changes class only after four consecutive
#: quarterly reports of condition on the other side of the line.
FDIC_LINE = 10_000_000
FDIC_QUARTERS = 4

#: finer asset segments around that line, in thousands of dollars
SEGMENTS = (
    ("under 1bn", None, 1_000_000),
    ("1bn to 5bn", 1_000_000, 5_000_000),
    ("5bn to 10bn", 5_000_000, 10_000_000),
    ("10bn to 20bn", 10_000_000, 20_000_000),
    ("20bn to 50bn", 20_000_000, 50_000_000),
    ("50bn and over", 50_000_000, None),
)

#: The new assessment base, which counts fed funds purchased, and the large
#: institution scorecard, which names them, took effect on 1 April 2011
#: (76 FR 10672), so the first era ends with 2011Q1.  The RC-K arm starts in 2010.
ERAS = (
    ("2010Q1-2011Q1", "2010Q1", "2011Q1"),
    ("2011Q2-2015Q4", "2011Q2", "2015Q4"),
    ("2016Q1-2019Q4", "2016Q1", "2019Q4"),
    ("2020Q1-2021Q4", "2020Q1", "2021Q4"),
    ("2022Q1-2026Q2", "2022Q1", "2026Q2"),
)


def next_quarter(per: str) -> str:
    y, q = int(per[:4]), int(per[-1])
    return f"{y}Q{q + 1}" if q < 4 else f"{y + 1}Q1"


def fdic_classes(panel: dict, line: float = FDIC_LINE, quarters: int = FDIC_QUARTERS):
    """(period, filer) to True where the four-quarter rule makes the filer large.

    Computed over the longest run of consecutive quarters in the panel.  A filer
    starts on the side of its first quarter in that run, and a quarter it did not
    file breaks its streak, since the rule counts consecutive reports.
    """
    pers = sorted(panel)
    runs, cur = [], [pers[0]]
    for p in pers[1:]:
        if p == next_quarter(cur[-1]):
            cur.append(p)
        else:
            runs.append(cur)
            cur = [p]
    runs.append(cur)
    run = max(runs, key=len)
    state, streak, last, out = {}, {}, {}, {}
    for p in run:
        for rssd, v in panel[p].items():
            assets = v.get("2170")
            if assets is None:
                continue
            side = assets >= line
            s = streak.get(rssd)
            if s is not None and s[0] == side and last.get(rssd) == prev_quarter(p):
                streak[rssd] = [side, s[1] + 1]
            else:
                streak[rssd] = [side, 1]
            last[rssd] = p
            if rssd not in state:
                state[rssd] = side
            elif state[rssd] != side and streak[rssd][1] >= quarters:
                state[rssd] = side
            out[(p, rssd)] = state[rssd]
    return out, (run[0], run[-1])


def segment_of(assets: float):
    for name, lo, hi in SEGMENTS:
        if (lo is None or assets >= lo) and (hi is None or assets < hi):
            return name
    return None


def fdic_line(panel: dict, rows: list[Row], effr_quarter: dict, draws: int = DRAWS,
              seeds=SEEDS) -> dict:
    """The RC-K arm against the FDIC size line: which rows the four-quarter rule
    would class differently from their quarter-end side, cost against EFFR by
    segment and era, and two steps read the same way, one across the line and
    one inside the small class."""
    classes, span = fdic_classes(panel)
    obs = arm_rc_k(rows)
    differs = sum(1 for r, _c in obs if (r.period, r.rssd) in classes
                  and classes[(r.period, r.rssd)] != (r.assets >= FDIC_LINE))
    unclassed = sum(1 for r, _c in obs if (r.period, r.rssd) not in classes)
    cells = collections.defaultdict(list)
    for r, c in obs:
        seg = segment_of(r.assets)
        for era, lo, hi in ERAS:
            if lo <= r.period <= hi:
                cells[(era, seg)].append((r.rssd, 100.0 * (c - effr_quarter[r.period])))
    table = []
    for era, _lo, _hi in ERAS:
        for name, *_x in SEGMENTS:
            v = cells.get((era, name), [])
            table.append({"era": era, "segment": name, "n": len(v),
                          "filers": len({k for k, _y in v}),
                          "median_bp_over_effr": statistics.median(y for _k, y in v) if v else None})

    def step(era, upper, lower):
        up, low = cells.get((era, upper), []), cells.get((era, lower), [])
        if not up or not low:
            return {"step_bp": None, "se_bp_resampling_filers": {}, "upper": upper, "lower": lower}
        se = {}
        for s in seeds:
            rng = np.random.default_rng(s)
            bu = cluster_boot_medians([y for _k, y in up], [k for k, _y in up], draws, rng)
            bl = cluster_boot_medians([y for _k, y in low], [k for k, _y in low], draws, rng)
            se[str(s)] = float(np.std(bu - bl))
        return {"upper": upper, "lower": lower,
                "step_bp": statistics.median(y for _k, y in up) - statistics.median(y for _k, y in low),
                "se_bp_resampling_filers": se,
                "filers_upper": len({k for k, _y in up}), "filers_lower": len({k for k, _y in low})}

    steps = [{"era": era,
              "across_line": step(era, "10bn to 20bn", "5bn to 10bn"),
              "inside_small_class": step(era, "1bn to 5bn", "under 1bn")}
             for era, _lo, _hi in ERAS]
    return {"line_thousands_of_dollars": FDIC_LINE, "consecutive_quarters": FDIC_QUARTERS,
            "class_run": list(span), "rows": len(obs),
            "rows_class_differs_from_quarter_end_side": differs,
            "rows_outside_the_class_run": unclassed,
            "segments": table, "steps": steps}


def print_fdic(f: dict) -> None:
    print(f"  FDIC size line {f['line_thousands_of_dollars'] / 1e6:.0f}bn, "
          f"{f['consecutive_quarters']} consecutive quarters, class run {f['class_run'][0]} "
          f"to {f['class_run'][1]}")
    print(f"  RC-K arm rows {f['rows']:,}; class differs from the quarter-end side on "
          f"{f['rows_class_differs_from_quarter_end_side']:,}; outside the run "
          f"{f['rows_outside_the_class_run']:,}")
    print(f"\n    {'segment':<14}" + "".join(f"{era:>26}" for era, *_x in ERAS))
    by = {(c["era"], c["segment"]): c for c in f["segments"]}
    for name, *_x in SEGMENTS:
        line = f"    {name:<14}"
        for era, *_y in ERAS:
            c = by[(era, name)]
            med = "-" if c["median_bp_over_effr"] is None else f"{c['median_bp_over_effr']:+.1f}"
            line += f"{(str(c['n']) + ' / ' + str(c['filers']) + ' / ' + med):>26}"
        print(line)
    print("\n    step, bp (filer-resampled se, two seeds)")
    for s in f["steps"]:
        parts = []
        for k in ("across_line", "inside_small_class"):
            x = s[k]
            if x["step_bp"] is None:
                parts.append(f"{k} -")
                continue
            se = x["se_bp_resampling_filers"]
            parts.append(f"{k} {x['step_bp']:+.1f} (se {se[str(SEEDS[0])]:.1f}/{se[str(SEEDS[1])]:.1f}, "
                         f"{abs(x['step_bp']) / se[str(SEEDS[0])]:.2f}x)")
        print(f"    {s['era']:<14} " + "   ".join(parts))


#: The Board's own classes (FEDS Notes 2018-03-01): "Within each FDIC status, the
#: top 15 banks by reserve balances each day are classified as 'larger,' while
#: the remainder are referred to as 'smaller'", November 2015 to March 2017, with
#: rates volume-weighted across overnight federal funds and Eurodollar
#: borrowing reported on the FR 2420.  The remainder is that report's domestic
#: panel: banks with $18 billion or more in total assets, and banks between $5
#: billion and $18 billion with fed funds activity above $200 million on two or
#: more days in the preceding three months (FR 2420 supporting statement).  The
#: activity test cannot be read off quarterly data, so the second group is taken
#: as filers in that size range carrying any RC-K average.  Reserve balances are
#: read at quarter end, not daily.
BOARD_QUARTERS = ("2015Q4", "2016Q1", "2016Q2", "2016Q3", "2016Q4", "2017Q1")
BOARD_TOP = 15
FR2420_LARGE = 18_000_000
FR2420_MID = 5_000_000
BOARD_CLASSES = ("larger", "smaller, 18bn and over", "smaller, 5bn to 18bn")


def board_classes(panel: dict, rows: list[Row], effr_quarter: dict,
                  draws: int = DECOMPOSE_DRAWS, seeds=SEEDS) -> dict:
    """Rebuild the Board's larger and smaller classes quarter by quarter and say
    what the instrument can read on each: how many filer-quarters carry fed
    funds with no repo at either quarter end, how the repo weight falls, and
    the fed funds gap the repo-weight fit gives with its standard error under
    two seeds."""
    no_repo = {(r.period, r.rssd) for r, _c in arm_rc_k(rows)}
    data, _left = decomposition_rows(rows, effr_quarter)
    weight = {(r.period, r.rssd): (w, y) for r, w, y in data}
    klass, quarters = {}, []
    for q in BOARD_QUARTERS:
        filers = panel.get(q, {})
        ranked = sorted((k for k, v in filers.items() if v.get("0090") is not None),
                        key=lambda k: (-filers[k]["0090"], k))
        top = set(ranked[:BOARD_TOP])
        for k, v in filers.items():
            assets = v.get("2170")
            if k in top:
                klass[(q, k)] = BOARD_CLASSES[0]
            elif assets is not None and assets >= FR2420_LARGE:
                klass[(q, k)] = BOARD_CLASSES[1]
            elif assets is not None and assets >= FR2420_MID and (v.get("3353") or 0) > 0:
                klass[(q, k)] = BOARD_CLASSES[2]
        row = {"quarter": q, "ranked_on_reserves": len(ranked)}
        for c in BOARD_CLASSES:
            ks = [k for (qq, k), cc in klass.items() if qq == q and cc == c]
            ws = [weight[(q, k)][0] for k in ks if (q, k) in weight]
            row[c] = {"filers": len(ks),
                      "with_rc_k_average": sum(1 for k in ks if (filers[k].get("3353") or 0) > 0),
                      "no_repo_at_either_end": sum(1 for k in ks if (q, k) in no_repo),
                      "weight_zero": sum(1 for w in ws if w == 0.0),
                      "weight_mixed": sum(1 for w in ws if 0.0 < w < 1.0),
                      "weight_one": sum(1 for w in ws if w == 1.0)}
        quarters.append(row)
    cells = {c: [] for c in BOARD_CLASSES}
    for (q, k), c in klass.items():
        if (q, k) in weight:
            w, y = weight[(q, k)]
            cells[c].append((k, w, y))
    pooled = {}
    for c, v in cells.items():
        if not v:
            pooled[c] = {"rows": 0}
            continue
        ws = sorted(w for _k, w, _y in v)
        a, b = lad_line([w for _k, w, _y in v], [y for _k, _w, y in v])
        pooled[c] = {"rows": len(v), "filers": len({k for k, _w, _y in v}),
                     "weight_p10": ws[int(0.1 * (len(ws) - 1))],
                     "weight_p50": ws[int(0.5 * (len(ws) - 1))],
                     "weight_p90": ws[int(0.9 * (len(ws) - 1))],
                     "share_of_rows_weight_below_half": sum(1 for x in ws if x < 0.5) / len(ws),
                     "fit_fed_funds_at_w0_bp": a, "fit_repo_at_w1_bp": a + b}
    gaps = {}
    if cells[BOARD_CLASSES[0]]:
        for other in BOARD_CLASSES[1:]:
            if cells[other]:
                gaps[f"larger minus {other}"] = {
                    "fit_gap_bp": pooled[BOARD_CLASSES[0]]["fit_fed_funds_at_w0_bp"]
                                  - pooled[other]["fit_fed_funds_at_w0_bp"],
                    "se_bp_resampling_filers": {str(s): lad_gap_se(cells[BOARD_CLASSES[0]], cells[other],
                                                                   draws, s) for s in seeds}}
    return {"quarters": quarters, "pooled": pooled, "fit_gaps": gaps,
            "top": BOARD_TOP, "fr2420_large": FR2420_LARGE, "fr2420_mid": FR2420_MID}


def print_board(bc: dict) -> None:
    print("  the Board's classes, rebuilt on quarter-end reserve balances")
    print(f"    {'quarter':<8} {'class':<24} {'filers':>6} {'RC-K avg':>8} {'no repo':>8} "
          f"{'w=0':>5} {'mixed':>6} {'w=1':>5}")
    for row in bc["quarters"]:
        for c in BOARD_CLASSES:
            x = row[c]
            print(f"    {row['quarter']:<8} {c:<24} {x['filers']:>6} {x['with_rc_k_average']:>8} "
                  f"{x['no_repo_at_either_end']:>8} {x['weight_zero']:>5} {x['weight_mixed']:>6} "
                  f"{x['weight_one']:>5}")
    print("\n    pooled over the window, repo weight and the LAD fit (bp over EFFR)")
    for c, x in bc["pooled"].items():
        if not x.get("rows"):
            print(f"    {c:<24} no rows")
            continue
        print(f"    {c:<24} rows {x['rows']:>4} filers {x['filers']:>3}  weight p10 {x['weight_p10']:.2f} "
              f"p50 {x['weight_p50']:.2f} p90 {x['weight_p90']:.2f}  below half "
              f"{x['share_of_rows_weight_below_half']:.2f}  fit a {x['fit_fed_funds_at_w0_bp']:+.1f} "
              f"a+b {x['fit_repo_at_w1_bp']:+.1f}")
    for k, g in bc["fit_gaps"].items():
        se = g["se_bp_resampling_filers"]
        print(f"    {k}: {g['fit_gap_bp']:+.1f} bp, filer se " + " / ".join(f"{se[str(s)]:.1f}" for s in SEEDS))


#: The class 12 CFR 327.5(b) names, certified each quarter on RC-O from 2011Q2,
#: so its eras are the eras that start there.  A deduction within `AT_LIMIT` of
#: its limit, relatively, is counted as at the limit.
BANKERS_CLASS = ("certification K656 is one and deduction K657 is positive, "
                 "in the same quarter")
BANKERS_ERAS = tuple(e for e in ERAS if e[1] >= "2011Q2")
AT_LIMIT = 1e-9
BANKERS_CELLS = ("class_borrowed", "peer_borrowed", "class_lent", "peer_lent",
                 "class_margin", "peer_margin")


def in_bankers_class(v: dict) -> bool:
    return v.get("K656") == 1.0 and (v.get("K657") or 0.0) > 0.0


def lent_rows(panel: dict, start: str, end: str) -> list[Row]:
    """`quarter_rows` on the asset leg, `LEGS["lent"]`.  The expense field carries
    the quarter's own income on fed funds sold and reverse repo, the repo fields
    carry reverse repo at this and the previous quarter end, and the average is
    their RC-K quarterly average; the fed funds fields carry nothing.  `arm_rc_k`
    on these rows reads the lending price under the filter the borrowing price
    is read under."""
    leg = LEGS["lent"]
    rows = []
    for per in sorted(p for p in panel if start <= p <= end):
        cur, prev = panel[per], panel.get(prev_quarter(per))
        for rssd, v in cur.items():
            ytd, assets = v.get(leg["flow"]), v.get("2170")
            if ytd is None or assets is None:
                continue
            pv = prev.get(rssd) if prev is not None else None
            if per.endswith("Q1"):
                income = ytd
            elif pv is None or pv.get(leg["flow"]) is None:
                continue
            else:
                income = ytd - pv[leg["flow"]]
            rows.append(Row(per, rssd, 0.0, v.get(leg["repo"]) or 0.0, None,
                            None if pv is None else (pv.get(leg["repo"]) or 0.0),
                            income, assets, v.get(leg["average"])))
    return rows


def _cell_se(cell, draws: int, seeds) -> dict:
    out = {}
    for s in seeds:
        rng = np.random.default_rng(s)
        out[str(s)] = float(np.std(cluster_boot_medians(
            [y for _k, y in cell], [k for k, _y in cell], draws, rng)))
    return out


def _gap_se(upper, lower, draws: int, seeds) -> dict:
    out = {}
    for s in seeds:
        rng = np.random.default_rng(s)
        bu = cluster_boot_medians([y for _k, y in upper], [k for k, _y in upper], draws, rng)
        bl = cluster_boot_medians([y for _k, y in lower], [k for k, _y in lower], draws, rng)
        out[str(s)] = float(np.std(bu - bl))
    return out


def bankers_bank(panel: dict, rows: list[Row], effr_quarter: dict, draws: int = DRAWS,
                 seeds=SEEDS) -> dict:
    """The banker's bank class against the filers outside it whose assets fall in
    the class's range that quarter: per quarter what can be read, per era both
    prices and the margin against EFFR with filer-resampled standard errors, the
    deduction against its limit, and every class filer on its own."""
    borrowed = {(r.period, r.rssd): c for r, c in arm_rc_k(rows)}
    lent = {(r.period, r.rssd): c for r, c in arm_rc_k(lent_rows(panel, *WINDOW))}
    quarters, per_filer, ratios, no_limit = [], {}, [], 0
    cells = {e: {n: [] for n in BANKERS_CELLS} for e, *_x in BANKERS_ERAS}
    ranges, certified, deducted = {}, set(), set()
    for q in sorted(p for p in panel if p >= BANKERS_ERAS[0][1]):
        f = panel[q]
        members = sorted(k for k, v in f.items() if in_bankers_class(v))
        certified |= {k for k, v in f.items() if v.get("K656") == 1.0}
        deducted |= set(members)
        quarters.append({"quarter": q, "class": len(members),
                         "class_borrowed": sum(1 for k in members if (q, k) in borrowed),
                         "class_lent": sum(1 for k in members if (q, k) in lent),
                         "certified_without_deduction": sum(
                             1 for v in f.values()
                             if v.get("K656") == 1.0 and not in_bankers_class(v))})
        era = next((e for e, lo_q, hi_q in BANKERS_ERAS if lo_q <= q <= hi_q), None)
        if not members or era is None or q not in effr_quarter:
            continue
        lo = min(f[k]["2170"] for k in members)
        hi = max(f[k]["2170"] for k in members)
        was = ranges.get(era, (lo, hi))
        ranges[era] = (min(lo, was[0]), max(hi, was[1]))
        e = effr_quarter[q]
        for k, v in f.items():
            assets = v.get("2170")
            member = in_bankers_class(v)
            if assets is None or not (member or lo <= assets <= hi):
                continue
            side = "class" if member else "peer"
            b, lend = borrowed.get((q, k)), lent.get((q, k))
            if b is not None:
                cells[era][side + "_borrowed"].append((k, 100.0 * (b - e)))
            if lend is not None:
                cells[era][side + "_lent"].append((k, 100.0 * (lend - e)))
            if b is not None and lend is not None:
                cells[era][side + "_margin"].append((k, 100.0 * (lend - b)))
            if not member:
                continue
            d = per_filer.setdefault(k, {"quarters": [], "assets": [], "borrowed": [],
                                         "lent": [], "ratio": []})
            d["quarters"].append(q)
            d["assets"].append(assets)
            if b is not None:
                d["borrowed"].append(100.0 * (b - e))
            if lend is not None:
                d["lent"].append(100.0 * (lend - e))
            limit = v.get("K658")
            if limit:
                ratios.append(v["K657"] / limit)
                d["ratio"].append(v["K657"] / limit)
            else:
                no_limit += 1

    def med(x):
        return statistics.median(x) if x else None

    eras = []
    for era, _lo_q, _hi_q in BANKERS_ERAS:
        c = cells[era]
        se = {n: _cell_se(c[n], draws, seeds)
              for n in ("class_borrowed", "class_lent", "class_margin") if c[n]}
        for side in ("borrowed", "lent"):
            if c["class_" + side] and c["peer_" + side]:
                se["class_minus_peer_" + side] = _gap_se(c["class_" + side],
                                                         c["peer_" + side], draws, seeds)
        eras.append({"era": era,
                     "class_asset_range_thousands": list(ranges[era]) if era in ranges else None,
                     "cells": {n: {"n": len(c[n]), "filers": len({k for k, _y in c[n]}),
                                   "median_bp": med([y for _k, y in c[n]])}
                               for n in BANKERS_CELLS},
                     "se_bp_resampling_filers": se})
    ratios.sort()
    return {"rule": "12 CFR 327.5(b)", "class_test": BANKERS_CLASS,
            "quarters": quarters, "eras": eras,
            "deduction_over_limit": {"rows": len(ratios), "median": med(ratios),
                                     "max": ratios[-1] if ratios else None,
                                     "rows_at_limit": sum(1 for x in ratios if x >= 1.0 - AT_LIMIT),
                                     "class_rows_without_limit": no_limit},
            "filers": [{"rssd": k, "quarters": len(d["quarters"]), "first": d["quarters"][0],
                        "last": d["quarters"][-1], "median_assets_thousands": med(d["assets"]),
                        "borrowed_quarters": len(d["borrowed"]),
                        "median_borrowed_bp": med(d["borrowed"]),
                        "lent_quarters": len(d["lent"]), "median_lent_bp": med(d["lent"]),
                        "median_deduction_over_limit": med(d["ratio"])}
                       for k, d in sorted(per_filer.items())],
            "certified_never_deducting": sorted(certified - deducted)}


def print_bankers(bk: dict) -> None:
    def num(v, spec):
        return "-" if v is None else format(v, spec)

    print(f"  the class {bk['rule']} names: {bk['class_test']}")
    print(f"    {'quarter':<8} {'class':>5} {'borrowing price':>15} {'lending price':>13} "
          f"{'certified, no deduction':>24}")
    for r in bk["quarters"]:
        print(f"    {r['quarter']:<8} {r['class']:>5} {r['class_borrowed']:>15} "
              f"{r['class_lent']:>13} {r['certified_without_deduction']:>24}")
    live = [r for r in bk["quarters"] if r["class"]]
    if live:
        wb = min(live, key=lambda r: (r["class_borrowed"], r["quarter"]))
        wl = min(live, key=lambda r: (r["class_lent"], r["quarter"]))
        print(f"    fewest with a borrowing price {wb['class_borrowed']} ({wb['quarter']}), "
              f"with a lending price {wl['class_lent']} ({wl['quarter']})")
    print("\n    against EFFR, bp: rows / filers / median, filer-resampled se under two seeds")
    for x in bk["eras"]:
        span = x["class_asset_range_thousands"]
        print(f"    {x['era']}   class assets "
              + (f"{span[0] / 1e3:,.0f}m to {span[1] / 1e3:,.0f}m" if span else "-"))
        se = x["se_bp_resampling_filers"]
        for n in BANKERS_CELLS:
            cc = x["cells"][n]
            tail = ("   se " + " / ".join(num(v, ".1f") for v in se[n].values())) if n in se else ""
            print(f"      {n:<16} {cc['n']:>6} / {cc['filers']:>5} / "
                  f"{num(cc['median_bp'], '+.1f'):>8}{tail}")
        for side in ("borrowed", "lent"):
            key = "class_minus_peer_" + side
            if key in se:
                gap = x["cells"]["class_" + side]["median_bp"] - x["cells"]["peer_" + side]["median_bp"]
                print(f"      {key:<26} {gap:+.1f}   se "
                      + " / ".join(num(v, ".1f") for v in se[key].values()))
    lim = bk["deduction_over_limit"]
    print(f"\n    deduction over limit: {lim['rows']} class rows, median {num(lim['median'], '.3f')}, "
          f"largest {num(lim['max'], '.3f')}, at the limit {lim['rows_at_limit']}, "
          f"no limit filed {lim['class_rows_without_limit']}")
    print(f"\n    {'rssd':>8} {'quarters':>8} {'first':<7} {'last':<7} {'assets':>8} "
          f"{'nb':>3} {'borrowed':>9} {'nl':>3} {'lent':>8} {'ded/limit':>9}")
    for d in bk["filers"]:
        print(f"    {d['rssd']:>8} {d['quarters']:>8} {d['first']:<7} {d['last']:<7} "
              f"{num(d['median_assets_thousands'] / 1e3, ',.0f'):>7}m {d['borrowed_quarters']:>3} "
              f"{num(d['median_borrowed_bp'], '+.1f'):>9} {d['lent_quarters']:>3} "
              f"{num(d['median_lent_bp'], '+.1f'):>8} {num(d['median_deduction_over_limit'], '.3f'):>9}")
    print("\n    certified in some quarter and never deducting: "
          + (", ".join(bk["certified_never_deducting"]) or "none"))


PREVIOUS_ENDS = ("fed funds at the previous end", "none at the previous end")
YEAR_PRODUCT = "Subset of Schedules"


def build_criteria(meta: dict, panel: dict, anchor_rows, balances_table, arms_out: dict,
                   decomp: dict, fdic: dict | None = None, board: dict | None = None,
                   bankers: dict | None = None) -> dict:
    """Every flag here is computed from the object it names (`11f`)."""
    crit = {}

    year = sorted(p for p, m in meta.items() if YEAR_PRODUCT in m["archive"])
    single = sorted(p for p in meta if p not in year)
    missing = [p for p in single if not meta[p]["columns_used"].get("3353")]
    refused = sorted(p for p, m in meta.items() if m["columns_refused"])
    short = {p: sum(1 for v in panel[p].values() if "3353" not in v) for p in single}
    crit["B59-S1"] = {
        "kind": "instrument",
        "passed": bool(single) and not missing and not refused,
        "name": "the RC-K quarterly average 3353 is read under the archive's own "
                "description in every period whose archive carries RC-K, and no "
                "wanted column is refused in any period",
        "detail": f"{len(single)} single-period archives; 3353 missing in "
                  f"{', '.join(missing) or 'none'}; refused columns in "
                  f"{', '.join(refused) or 'none'}; filers without a value, summed "
                  f"over those periods, {sum(short.values())}. The one-year product "
                  f"serves {', '.join(year) or 'no period'} and carries no RC-K, so "
                  f"those periods have no average"}

    def is_s3(item):
        return item.startswith("validity") or item.endswith("gap se bp")

    s2 = [r for r in anchor_rows if not is_s3(r[0])]
    s3 = [r for r in anchor_rows if is_s3(r[0])]
    crit["B59-S2"] = {
        "kind": "known_answer",
        "passed": bool(s2) and all(ok for *_x, ok in s2),
        "name": "with 2009Q2 treated as absent, this code gives back the first "
                "pass's row count, band counts, band medians and environment gaps",
        "detail": "; ".join(f"{i}: {m} against {t}" for i, m, t, ok in s2 if not ok)
                  or f"all {len(s2)} items come back"}
    crit["B59-S3"] = {
        "kind": "known_answer",
        "passed": bool(s3) and all(ok for *_x, ok in s3),
        "name": "the first pass's validity fit, to four decimals, and its "
                "observation-resampled standard errors, to one decimal, come back",
        "detail": "; ".join(f"{i}: {m} against {t}, {'back' if ok else 'not back'}"
                            for i, m, t, ok in s3)}

    cells = {(c["band"], c["previous_end"]): c["n"] for c in balances_table}
    want = [(b, s) for b, *_x in BANDS for s in PREVIOUS_ENDS]
    crit["B59-S4"] = {
        "kind": "own_reading",
        "passed": all(cells.get(k, 0) > 0 for k in want),
        "name": "the quarter-end balance and the mean of two quarter ends are "
                "printed against the RC-K average, by band and by the fed funds "
                "position at the previous quarter end",
        "detail": "; ".join(
            f"{c['band']}, {c['previous_end']}: n {c['n']}, quarter end "
            f"{c['median_quarter_end_over_average']:.3f}, mean of two ends "
            f"{c['median_two_end_mean_over_average']:.3f}" for c in balances_table)
            or "no cell"}

    def fin(x):
        return isinstance(x, float) and math.isfinite(x)

    crit["B59-S5"] = {
        "kind": "own_reading",
        "passed": set(arms_out) == set(ARMS) and all(
            a["validity"]["years"] >= 2 and fin(a["validity"]["slope"])
            for a in arms_out.values()),
        "name": "for every arm the yearly median cost is printed against the "
                "yearly mean effective rate with slope, correlation and intercept",
        "detail": "; ".join(
            f"{k}: slope {a['validity']['slope']:.4f}, corr {a['validity']['corr']:.4f}, "
            f"intercept {a['validity']['intercept']:.4f}, {a['validity']['rows']} rows"
            for k, a in arms_out.items())}

    def cell_ok(blk):
        b0, b1 = blk["bands"][0], blk["bands"][-1]
        return (b0["n"] > 0 and b1["n"] > 0 and fin(blk["gap_largest_minus_smallest_bp"])
                and all(fin(x) for x in blk["gap_se_bp_resampling_filers"].values()))

    crit["B59-S6"] = {
        "kind": "own_reading",
        "passed": set(arms_out) == set(ARMS) and all(
            len(a["cross_section"]) == len(REGIMES)
            and all(cell_ok(blk) for blk in a["cross_section"].values())
            for a in arms_out.values()),
        "name": "for every arm and rate environment the largest-minus-smallest "
                "band gap is printed with its filer-resampled standard error under "
                "two seeds, next to the band medians against the quarter median "
                "and against EFFR",
        "detail": "; ".join(
            f"{k} {rk}: {blk['gap_largest_minus_smallest_bp']:+.2f} bp, filer se "
            f"{blk['gap_se_bp_resampling_filers'][str(SEEDS[0])]:.2f}"
            for k, a in arms_out.items() for rk, blk in a["cross_section"].items())}

    def fit_ok(blk):
        b0, b1 = blk["bands"][0], blk["bands"][-1]
        return ("mixed_fit" in b0 and "mixed_fit" in b1 and fin(blk["gap_mixed_fit_bp"])
                and all(fin(x) for x in blk["gap_mixed_fit_se_bp_resampling_filers"].values()))

    crit["B59-S7"] = {
        "kind": "own_reading",
        "passed": len(decomp["regimes"]) == len(REGIMES)
                  and all(fit_ok(blk) for blk in decomp["regimes"].values()),
        "name": "without the no-repo filter, the repo-weight decomposition prints "
                "per band and environment the three strata, the repo-only spread "
                "quartiles and the fitted fed funds price, and the largest-minus-"
                "smallest gap of the fit with its filer-resampled standard error",
        "detail": f"left out, no position at either end: "
                  f"{decomp['left_out_no_position_at_either_end']}; " + "; ".join(
            f"{rk}: fit {blk['gap_mixed_fit_bp']:+.2f} bp (se "
            f"{blk['gap_mixed_fit_se_bp_resampling_filers'][str(SEEDS[0])]:.2f}), "
            f"no-repo medians {blk['gap_w0_medians_bp']:+.2f} bp (se "
            f"{blk['gap_w0_se_bp_resampling_filers'][str(SEEDS[0])]:.2f})"
            for rk, blk in decomp["regimes"].items())}
    if fdic is not None:
        def step_ok(x):
            return fin(x["step_bp"]) and len(x["se_bp_resampling_filers"]) == len(SEEDS) and all(
                fin(v) for v in x["se_bp_resampling_filers"].values())
        crit["B59-S8"] = {
            "kind": "own_reading",
            "passed": (len(fdic["segments"]) == len(ERAS) * len(SEGMENTS)
                       and all(c["n"] > 0 for c in fdic["segments"])
                       and len(fdic["steps"]) == len(ERAS)
                       and all(step_ok(s[k]) for s in fdic["steps"]
                               for k in ("across_line", "inside_small_class"))),
            "name": "on the RC-K arm, cost against EFFR is printed by asset segment and "
                    "era, with the step across the FDIC size line and the step inside "
                    "its small class, each with a filer-resampled standard error",
            "detail": f"the four-quarter class differs from the quarter-end side of the "
                      f"line on {fdic['rows_class_differs_from_quarter_end_side']} of "
                      f"{fdic['rows']} rows; " + "; ".join(
                f"{s['era']}: across {s['across_line']['step_bp']:+.1f} bp (se "
                f"{s['across_line']['se_bp_resampling_filers'].get(str(SEEDS[0]), float('nan')):.1f}), "
                f"inside small {s['inside_small_class']['step_bp']:+.1f} bp (se "
                f"{s['inside_small_class']['se_bp_resampling_filers'].get(str(SEEDS[0]), float('nan')):.1f})"
                for s in fdic["steps"]
                if fin(s["across_line"]["step_bp"]) and fin(s["inside_small_class"]["step_bp"]))}
    if board is not None:
        per_q = {row["quarter"]: row[BOARD_CLASSES[0]]["no_repo_at_either_end"] for row in board["quarters"]}
        lg = board["pooled"].get(BOARD_CLASSES[0], {})
        crit["B59-S9"] = {
            "kind": "premise",
            "passed": len(per_q) == len(BOARD_QUARTERS) and all(n >= 1 for n in per_q.values()),
            "name": "in every quarter of the Board's window, the Board's larger class has a "
                    "filer carrying fed funds with no repo at either quarter end, so a fed "
                    "funds price for that class can be read without extrapolating a repo weight",
            "detail": "larger-class filer-quarters with no repo at either end: " + ", ".join(
                f"{q} {n}" for q, n in per_q.items())
                + (f"; pooled repo weight at quarter ends p10 {lg['weight_p10']:.2f}, median "
                   f"{lg['weight_p50']:.2f}, share of rows below half "
                   f"{lg['share_of_rows_weight_below_half']:.2f}" if lg.get("rows") else "")
                + "; " + "; ".join(
                f"{k}: fit {g['fit_gap_bp']:+.1f} bp, filer se "
                + " / ".join(f"{v:.1f}" for v in g["se_bp_resampling_filers"].values())
                for k, g in board["fit_gaps"].items())
                + ". The Board's rates also pool Eurodollar borrowing, whose interest the "
                  "archive files on RIAD4172, apart from RIAD4180"}
    if bankers is not None:
        need = ("class_borrowed", "class_lent", "class_margin", "peer_borrowed", "peer_lent")
        gaps = ("class_borrowed", "class_lent", "class_margin",
                "class_minus_peer_borrowed", "class_minus_peer_lent")

        def era_ok(x):
            se = x["se_bp_resampling_filers"]
            return (all(x["cells"][n]["n"] > 0 for n in need)
                    and all(k in se and len(se[k]) == len(SEEDS)
                            and all(fin(v) for v in se[k].values()) for k in gaps))

        live = [r for r in bankers["quarters"] if r["class"]]
        head = "no quarter has a class filer; "
        if live:
            wb = min(live, key=lambda r: (r["class_borrowed"], r["quarter"]))
            wl = min(live, key=lambda r: (r["class_lent"], r["quarter"]))
            head = (f"{len(bankers['filers'])} class filers, "
                    f"{len(bankers['certified_never_deducting'])} more certify and never deduct; "
                    f"fewest class filers in a quarter with a borrowing price "
                    f"{wb['class_borrowed']} ({wb['quarter']}), with a lending price "
                    f"{wl['class_lent']} ({wl['quarter']}); ")
        crit["B59-S10"] = {
            "kind": "own_reading",
            "passed": (len(bankers["eras"]) == len(BANKERS_ERAS)
                       and all(era_ok(x) for x in bankers["eras"])
                       and bool(bankers["filers"])),
            "name": "the class 12 CFR 327.5(b) names is read off RC-O as filers that certify "
                    "and deduct in the same quarter, and in every era of the certification "
                    "its borrowing price, its lending price and its margin are printed "
                    "against EFFR next to filers outside the class in its asset range, with "
                    "filer-resampled standard errors under two seeds and every class filer "
                    "on its own",
            "detail": head + "; ".join(
                f"{x['era']}: class borrowing {x['cells']['class_borrowed']['median_bp']:+.1f} bp, "
                f"peers {x['cells']['peer_borrowed']['median_bp']:+.1f}; class lending "
                f"{x['cells']['class_lent']['median_bp']:+.1f}, peers "
                f"{x['cells']['peer_lent']['median_bp']:+.1f}; class margin "
                f"{x['cells']['class_margin']['median_bp']:+.1f} (se "
                f"{x['se_bp_resampling_filers']['class_margin'][str(SEEDS[0])]:.1f})"
                for x in bankers["eras"] if era_ok(x))}
        lim = bankers["deduction_over_limit"]
        crit["B59-S11"] = {
            "kind": "premise",
            "passed": lim["rows"] > 0 and lim["rows_at_limit"] == 0,
            "name": "on every class row read here the deduction sits below its limit, so "
                    "the exclusion the rule writes is not capped on those rows",
            "detail": (f"{lim['rows']} class rows with a limit filed; deduction over limit "
                       f"median {lim['median']:.3f}, largest {lim['max']:.3f}; rows at the "
                       f"limit {lim['rows_at_limit']}; class rows with no limit filed "
                       f"{lim['class_rows_without_limit']}")
                      if lim["rows"] else "no class row with a limit filed"}
    return crit


DIAGNOSTIC_REASON = (
    "the size arm is read here and not scored: the nearest size class named in "
    "rule text, the FDIC's $10 billion line between small and large institutions, "
    "coincides with the top band's lower edge, but its two rate schedules overlap "
    "and it names the fed funds position only on its large side, while the step "
    "that reads lies inside its small class; the one class rule text names on the "
    "lending side of this position, the banker's bank of 12 CFR 327.5(b), writes "
    "its term on its own assessment base, where it can lower and cannot raise what "
    "the class's borrowers pay, while the smaller filers pay more; no grid is "
    "assigned to any reading in this record")


def run_all(draws: int = DRAWS):
    panel, meta = load_cache()
    effr_year, effr_q = load_effr()
    anchor_obs = arm_quarter_end(quarter_rows(panel, *WINDOW, absent=("2009Q2",)))
    anchor_rows = compare_first_pass(validity(anchor_obs, effr_year),
                                     cross_section(anchor_obs, draws))
    rows = quarter_rows(panel, *WINDOW)
    arms_out = {}
    for key, (label, build) in ARMS.items():
        obs = build(rows)
        arms_out[key] = {"label": label, "validity": validity(obs, effr_year),
                         "cross_section": cross_section(obs, draws),
                         "levels_bp_over_effr": levels(obs, effr_q)}
    bal = balances(rows)
    decomp = decompose(rows, effr_q)
    fdic = fdic_line(panel, rows, effr_q, draws)
    board = board_classes(panel, rows, effr_q)
    bankers = bankers_bank(panel, rows, effr_q, draws)
    crit = build_criteria(meta, panel, anchor_rows, bal, arms_out, decomp, fdic, board,
                          bankers)
    rec = {
        "stage": "B59",
        "arm": "size",
        "diagnostic_only": True,
        "diagnostic_reason": DIAGNOSTIC_REASON,
        "config": {
            "window": list(WINDOW),
            "bands_thousands_of_dollars": [[n, lo, hi] for n, lo, hi in BANDS],
            "near_zero_years": sorted(NEAR_ZERO),
            "environments": [[k, label] for k, label, _f in REGIMES],
            "bootstrap_draws": draws, "seeds": list(SEEDS),
            "decompose_draws": DECOMPOSE_DRAWS,
            "stable_band": list(STABLE),
            "fdic_line_thousands_of_dollars": FDIC_LINE,
            "fdic_consecutive_quarters": FDIC_QUARTERS,
            "fdic_segments": [[n, lo, hi] for n, lo, hi in SEGMENTS],
            "fdic_eras": [list(e) for e in ERAS],
            "board_quarters": list(BOARD_QUARTERS), "board_top": BOARD_TOP,
            "fr2420_large_thousands_of_dollars": FR2420_LARGE,
            "fr2420_mid_thousands_of_dollars": FR2420_MID,
            "bankers_class": BANKERS_CLASS,
            "bankers_eras": [list(e) for e in BANKERS_ERAS],
            "bankers_at_limit_tolerance": AT_LIMIT,
            "anchor_absent": ["2009Q2"],
            "cache": "data/cache/b59_call_report.json",
            "cache_sha256": sha256_of(CACHE),
            "effr": "data/b59/EFFR.csv",
            "effr_sha256": sha256_of(EFFR_CSV),
        },
        "criteria": crit,
        "anchor_first_pass": [{"item": i, "this_code": m, "first_pass": t, "back": ok}
                              for i, m, t, ok in anchor_rows],
        "balances_over_rc_k_average": bal,
        "arms": arms_out,
        "decomposition": decomp,
        "fdic_line": fdic,
        "board_classes": board,
        "bankers_bank": bankers,
    }
    return rec


def print_criteria(crit: dict) -> None:
    def lab(c):
        return "NO-VERDICT" if c["passed"] is None else ("PASS" if c["passed"] else "FAILED")
    for k, c in crit.items():
        print(f"  {k:8s} {c['kind']:12s} {lab(c):10s} {c['name'][:88]}")
    print("\n  by kind (11d); no total across kinds")
    for kind in ("instrument", "premise", "known_answer", "rival", "own_reading", "bookkeeping"):
        g = [c for c in crit.values() if c["kind"] == kind]
        if g:
            print(f"    {kind:12s} pass {sum(1 for c in g if c['passed'] is True)}"
                  f"  fail {sum(1 for c in g if c['passed'] is False)}"
                  f"  no verdict {sum(1 for c in g if c['passed'] is None)}")


def selftest() -> int:
    """Plant the failures the flags and the helpers have to report."""
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    # quarter rows: Q1 alone, Q2 needs its prior quarter, `absent` takes two out
    #: filer 1 borrows at quarter ends; filer 2 borrows only inside 2020Q3, with
    #: nothing at either end, which is the row the decomposition cannot weight;
    #: filer 3 carries repo at the 2020Q1 end and none at the 2020Q2 end, which
    #: is the row the RC-K arm has to drop for the previous end alone
    panel = {
        "2020Q1": {"1": {"4180": 10.0, "2170": 500.0, "B993": 100.0, "B995": 0.0, "3353": 80.0},
                   "2": {"4180": 0.0, "2170": 90.0, "B993": 0.0, "B995": 0.0, "3353": 0.0},
                   "3": {"4180": 4.0, "2170": 70.0, "B993": 0.0, "B995": 10.0, "3353": 9.0}},
        "2020Q2": {"1": {"4180": 25.0, "2170": 500.0, "B993": 100.0, "B995": 0.0, "3353": 90.0},
                   "2": {"4180": 0.0, "2170": 90.0, "B993": 0.0, "B995": 0.0, "3353": 0.0},
                   "3": {"4180": 9.0, "2170": 70.0, "B993": 20.0, "B995": 0.0, "3353": 15.0}},
        "2020Q3": {"1": {"4180": 36.0, "2170": 500.0, "B993": 0.0, "B995": 0.0, "3353": 30.0},
                   "2": {"4180": 7.0, "2170": 90.0, "B993": 0.0, "B995": 0.0, "3353": 10.0}},
        "2020Q4": {"1": {"4180": 40.0, "2170": 500.0, "B993": 50.0, "B995": 5.0, "3353": 60.0}},
    }
    rows = quarter_rows(panel, "2020Q1", "2020Q4")
    by = {r.period: r for r in rows if r.rssd == "1"}
    expect(by["2020Q1"].expense == 10.0 and by["2020Q2"].expense == 15.0
           and by["2020Q3"].expense == 11.0,
           "Q1's year-to-date figure stands alone and later quarters difference")
    gone = {r.period for r in quarter_rows(panel, "2020Q1", "2020Q4", absent=("2020Q2",))}
    expect(gone == {"2020Q1", "2020Q4"},
           "a period treated as absent takes its own rows and the next quarter's")
    rck = {r.period for r, _c in arm_rc_k(rows) if r.rssd == "1"}
    expect("2020Q3" in rck and "2020Q4" not in rck,
           "the RC-K arm keeps a filer that borrowed only inside the quarter and "
           "drops one with repo at a quarter end")
    expect(not any(r.rssd == "3" and r.period == "2020Q2" for r, _c in arm_rc_k(rows))
           and any(r.rssd == "3" and r.period == "2020Q2" for r in rows),
           "and drops one whose repo sat at the previous quarter end only")
    expect(abs(dict((r.period, c) for r, c in arm_rc_k(rows) if r.rssd == "1")["2020Q3"]
               - 400.0 * 11.0 / 30.0) < 1e-12,
           "and divides the quarter's expense by the RC-K average")
    data, left = decomposition_rows(rows, {q: 1.0 for q in panel})
    expect(left == 1 and any(r.rssd == "1" and r.period == "2020Q3" for r, _w, _y in data)
           and not any(r.rssd == "2" and r.period == "2020Q3" for r, _w, _y in data),
           "the decomposition leaves out a filer with no position at either end, and counts it")

    # the weighted-median bootstrap equals the one it replaces
    rng = np.random.default_rng(7)
    vals = rng.normal(size=37)
    clus = rng.integers(0, 9, size=37)
    got = cluster_boot_medians(vals, clus, 50, np.random.default_rng(3))
    order = np.argsort(vals, kind="stable")
    _u, inv = np.unique(clus[order], return_inverse=True)
    r2 = np.random.default_rng(3)
    k = int(inv.max()) + 1
    ref = []
    for m in r2.multinomial(k, np.full(k, 1.0 / k), size=50):
        ref.append(np.median(np.repeat(vals[order], m[inv])))
    expect(np.allclose(got, ref), "the cluster bootstrap's weighted medians equal medians "
                                  "of the materialised resamples")
    expect(float(np.std(cluster_boot_medians([2.0] * 10, list(range(10)), 20,
                                             np.random.default_rng(1)))) == 0.0,
           "and a constant sample has a zero resampled spread")

    # least absolute deviations
    w = np.linspace(0, 1, 41)
    a, b = lad_line(w, 5.0 - 100.0 * w)
    expect(abs(a - 5.0) < 1e-6 and abs(b + 100.0) < 1e-6, "LAD recovers a noiseless line")
    y = 5.0 - 100.0 * w
    y[3] += 10_000.0
    a2, b2 = lad_line(w, y)
    expect(abs(a2 - 5.0) < 1e-6 and abs(b2 + 100.0) < 1e-6,
           "and one wild observation does not move it")

    # the flags, each planted to flip
    meta = {"2020Q1": {"archive": "x All Schedules 03312020.zip",
                       "columns_used": {"3353": ["RCON3353"]}, "columns_refused": []},
            "2009Q2": {"archive": "x Subset of Schedules 2009.zip",
                       "columns_used": {}, "columns_refused": []}}
    pan = {"2020Q1": {"1": {"3353": 1.0}}, "2009Q2": {"1": {}}}
    anchor = [("rows", "1", "1", True), ("validity corr", "0.1", "0.2", False)]
    bal = [{"band": b, "previous_end": s, "n": 1, "median_quarter_end_over_average": 1.0,
            "median_two_end_mean_over_average": 1.0} for b, *_x in BANDS for s in PREVIOUS_ENDS]
    blk = {"bands": [{"n": 1}] * len(BANDS), "gap_largest_minus_smallest_bp": -1.0,
           "gap_se_bp_resampling_filers": {"0": 1.0, "1": 1.0}}
    arms_ok = {k: {"validity": {"years": 3, "slope": 1.0, "corr": 1.0, "intercept": 0.0, "rows": 9},
                   "cross_section": {rk: dict(blk) for rk, *_x in REGIMES}} for k in ARMS}
    dblk = {"bands": [{"mixed_fit": {}}] * len(BANDS), "gap_mixed_fit_bp": -1.0,
            "gap_mixed_fit_se_bp_resampling_filers": {"0": 1.0, "1": 1.0},
            "gap_w0_medians_bp": -1.0, "gap_w0_se_bp_resampling_filers": {"0": 1.0, "1": 1.0}}
    dec_ok = {"left_out_no_position_at_either_end": 0,
              "regimes": {rk: dict(dblk) for rk, *_x in REGIMES}}
    c = build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok)
    expect(all(c[k]["passed"] for k in ("B59-S1", "B59-S2", "B59-S4", "B59-S5", "B59-S6", "B59-S7"))
           and c["B59-S3"]["passed"] is False,
           "on well formed inputs every flag reads its object, and the one planted "
           "not to come back does not")
    m2 = json.loads(json.dumps(meta))
    m2["2020Q1"]["columns_used"] = {}
    expect(build_criteria(m2, pan, anchor, bal, arms_ok, dec_ok)["B59-S1"]["passed"] is False,
           "S1 flips when a single-period archive yields no 3353")
    m3 = json.loads(json.dumps(meta))
    m3["2020Q1"]["columns_refused"] = [{"column": "RCON3353"}]
    expect(build_criteria(m3, pan, anchor, bal, arms_ok, dec_ok)["B59-S1"]["passed"] is False,
           "S1 flips when a wanted column was refused")
    expect(build_criteria(meta, pan, [("rows", "2", "1", False)] + anchor[1:], bal, arms_ok,
                          dec_ok)["B59-S2"]["passed"] is False,
           "S2 flips when a count does not come back")
    expect(build_criteria(meta, pan, anchor, bal[1:], arms_ok, dec_ok)["B59-S4"]["passed"] is False,
           "S4 flips when a balance cell is missing")
    a5 = json.loads(json.dumps(arms_ok))
    a5[next(iter(ARMS))]["validity"]["years"] = 1
    expect(build_criteria(meta, pan, anchor, bal, a5, dec_ok)["B59-S5"]["passed"] is False,
           "S5 flips when an arm's validity fit rests on one year")
    a6 = json.loads(json.dumps(arms_ok))
    a6[next(iter(ARMS))]["cross_section"]["high"]["bands"] = [{"n": 0}] * len(BANDS)
    expect(build_criteria(meta, pan, anchor, bal, a6, dec_ok)["B59-S6"]["passed"] is False,
           "S6 flips when a band is empty in one environment")
    d7 = json.loads(json.dumps(dec_ok))
    d7["regimes"]["high"]["bands"] = [{}] * len(BANDS)
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, d7)["B59-S7"]["passed"] is False,
           "S7 flips when the fit is missing in one environment")

    # the FDIC four-quarter rule: three quarters over the line change nothing,
    # the fourth does, a missed report starts the count again, and the way back
    # takes four quarters as well
    B, S = FDIC_LINE + 1.0, FDIC_LINE - 1.0
    seq = {"2011Q1": S, "2011Q2": B, "2011Q3": B, "2011Q4": B, "2012Q1": S,
           "2012Q2": B, "2012Q3": B, "2012Q4": B, "2013Q1": B, "2013Q2": S,
           "2013Q3": S, "2013Q4": S, "2014Q1": S}
    gap_filer = {"2011Q1": S, "2011Q2": B, "2011Q3": B, "2012Q1": B, "2012Q2": B}
    fp = {p: {"1": {"2170": a}} for p, a in seq.items()}
    for p, a in gap_filer.items():
        fp.setdefault(p, {})["2"] = {"2170": a}
    for p in ("2011Q4",):
        fp.setdefault(p, {})
    cl, _span = fdic_classes(fp)
    got = [cl[(p, "1")] for p in sorted(seq)]
    expect(got == [False, False, False, False, False, False, False, False, True, True, True, True, False],
           "the four-quarter rule: three quarters over change nothing, the fourth does, "
           "and the way back takes four as well")
    expect(cl[("2012Q2", "2")] is False,
           "a quarter without a report starts the count again")
    # exactly $10 billion is large, as 327.8 writes it ("$10 billion or more")
    expect(segment_of(float(FDIC_LINE)) == "10bn to 20bn"
           and segment_of(FDIC_LINE - 1.0) == "5bn to 10bn"
           and band_of(float(FDIC_LINE)) == "10bn and over",
           "a filer at exactly the line sits on the large side, in the segment and in the band")
    edge = {p: {"1": {"2170": float(FDIC_LINE) if p != "2011Q1" else S}}
            for p in ("2011Q1", "2011Q2", "2011Q3", "2011Q4", "2012Q1")}
    ce, _s = fdic_classes(edge)
    expect(ce[("2012Q1", "1")] is True and ce[("2011Q4", "1")] is False,
           "and four quarters at exactly the line make it large, three do not")

    # the two steps are read on the segments they name: one filer per segment,
    # known costs, EFFR at zero, so the steps are exact differences
    costs = {"under 1bn": (500_000.0, 0.70), "1bn to 5bn": (2_000_000.0, 0.30),
             "5bn to 10bn": (7_000_000.0, 0.10), "10bn to 20bn": (15_000_000.0, 0.04),
             "20bn to 50bn": (30_000_000.0, 0.01), "50bn and over": (60_000_000.0, 0.02)}
    tp = {"2011Q4": {}, "2012Q1": {}}
    for i, (seg, (assets, exp)) in enumerate(costs.items()):
        tp["2011Q4"][str(i)] = {"2170": assets, "B993": 1.0, "B995": 0.0, "4180": 0.0, "3353": 400.0}
        tp["2012Q1"][str(i)] = {"2170": assets, "B993": 1.0, "B995": 0.0, "4180": exp, "3353": 400.0}
    ft = fdic_line(tp, quarter_rows(tp, "2011Q4", "2012Q1"), {"2012Q1": 0.0, "2011Q4": 0.0}, draws=20)
    st_ = {s["era"]: s for s in ft["steps"]}["2011Q2-2015Q4"]
    expect(abs(st_["across_line"]["step_bp"] - (4.0 - 10.0)) < 1e-9
           and abs(st_["inside_small_class"]["step_bp"] - (30.0 - 70.0)) < 1e-9,
           "the step across the line is 10bn-20bn minus 5bn-10bn, and the step inside "
           "the small class is 1bn-5bn minus under 1bn")
    fd_ok = {"rows": 9, "rows_class_differs_from_quarter_end_side": 0,
             "segments": [{"era": e, "segment": s, "n": 1} for e, *_x in ERAS for s, *_y in SEGMENTS],
             "steps": [{"era": e,
                        "across_line": {"step_bp": -1.0, "se_bp_resampling_filers": {"0": 1.0, "1": 1.0}},
                        "inside_small_class": {"step_bp": -1.0, "se_bp_resampling_filers": {"0": 1.0, "1": 1.0}}}
                       for e, *_x in ERAS]}
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, fd_ok)["B59-S8"]["passed"] is True,
           "S8 reads a well formed FDIC-line object")
    f8 = json.loads(json.dumps(fd_ok))
    f8["segments"][3]["n"] = 0
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, f8)["B59-S8"]["passed"] is False,
           "S8 flips when one segment of one era is empty")
    f9 = json.loads(json.dumps(fd_ok))
    f9["steps"][0]["across_line"]["se_bp_resampling_filers"] = {}
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, f9)["B59-S8"]["passed"] is False,
           "S8 flips when a step has no standard error")

    # the Board's classes: ranked on reserves, the top taken per quarter, and the
    # premise read per quarter.  Year-to-date expense climbs by one a quarter so
    # every quarter has an expense of its own once its previous quarter is there.
    def board_panel(with_prior: bool) -> dict:
        qs = (("2015Q3",) if with_prior else ()) + BOARD_QUARTERS
        out = {}
        for q in qs:
            ytd = float(int(q[-1]))
            out[q] = {str(i): {"0090": float(1000 - i), "2170": 30_000_000.0, "B993": 0.0,
                               "B995": 5.0, "4180": ytd, "3353": 10.0}
                      for i in range(BOARD_TOP + 3)}
            out[q]["solo"] = {"0090": 999.5, "2170": 30_000_000.0, "B993": 5.0, "B995": 0.0,
                              "4180": ytd, "3353": 10.0}
            #: a larger filer whose repo is gone at the 2016Q2 end but was there
            #: at the 2016Q1 end, which the no-repo count has to leave out
            out[q]["pr"] = {"0090": 999.7, "2170": 30_000_000.0, "B993": 5.0,
                            "B995": 0.0 if q == "2016Q2" else 5.0, "4180": ytd, "3353": 10.0}
        return out

    short = board_panel(False)
    bc_short = board_classes(short, quarter_rows(short, "2015Q4", "2017Q1"),
                             {q: 0.0 for q in short}, draws=5)
    first = bc_short["quarters"][0]
    expect(first[BOARD_CLASSES[0]]["filers"] == BOARD_TOP
           and first[BOARD_CLASSES[1]]["filers"] == 5,
           "the larger class is the fifteen largest reserve balances and the rest of "
           "the 18bn-and-over filers fall to the smaller class")
    expect(first[BOARD_CLASSES[0]]["no_repo_at_either_end"] == 0
           and all(r[BOARD_CLASSES[0]]["no_repo_at_either_end"] == 1 for r in bc_short["quarters"][1:]),
           "the one larger filer carrying fed funds and no repo is counted in each quarter "
           "whose previous quarter is on disk, and not in the one whose is not")
    s9 = build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, bc_short)["B59-S9"]
    expect(s9["passed"] is False and "2015Q4 0" in s9["detail"],
           "S9 flips when one quarter of the window has no larger filer without repo")
    full = board_panel(True)
    bc_full = board_classes(full, quarter_rows(full, "2015Q3", "2017Q1"),
                            {q: 0.0 for q in full}, draws=5)
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, bc_full)["B59-S9"]["passed"] is True,
           "and reads true when every quarter has one")

    # the banker's bank class: certified and deducting in the same quarter, the
    # asset leg read under the borrowing leg's filter, filers outside the class
    # taken inside its asset range with the range closed at both ends, and the
    # deduction read against its limit.  2011Q4 is on disk only so that 2012Q1
    # has a previous quarter end; year-to-date flows climb within 2012.
    def bk_panel(at_limit: bool, deduct: bool = True) -> dict:
        out = {}
        for q, ytd_b, ytd_l in (("2011Q4", 8.0, 16.0), ("2012Q1", 2.0, 4.0), ("2012Q2", 5.0, 10.0)):
            base = {"B995": 0.0, "4180": ytd_b, "B989": 0.0, "4020": ytd_l}
            out[q] = {
                #: in the class; its two averages differ, so swapping them shows
                "bb1": {**base, "K656": 1.0, "K657": 50.0 if deduct else 0.0, "K658": 100.0,
                        "2170": 600.0, "3353": 400.0, "3365": 300.0},
                #: in the class; reverse repo at the 2012Q1 end only, so it has no
                #: lending price in 2012Q1 (this end) nor in 2012Q2 (the previous end)
                "bb2": {**base, "K656": 1.0,
                        "K657": (100.0 if at_limit and q == "2012Q2" else 60.0) if deduct else 0.0,
                        "K658": 100.0, "2170": 900.0, "3353": 200.0, "3365": 200.0,
                        "B989": 5.0 if q == "2012Q1" else 0.0},
                #: certifies and deducts nothing: outside the class, inside its range
                "cert0": {**base, "K656": 1.0, "K657": 0.0, "K658": 0.0, "2170": 700.0,
                          "3353": 100.0, "3365": 100.0},
                #: deducts and does not certify: outside the class, inside its range
                "ded0": {**base, "K656": 0.0, "K657": 30.0, "K658": 100.0, "2170": 650.0,
                         "3353": 100.0, "3365": 100.0},
                #: exactly at the top of the class's range
                "edge": {**base, "K656": 0.0, "2170": 900.0, "3353": 50.0, "3365": 50.0},
                #: far above it
                "far": {**base, "K656": 0.0, "2170": 5000.0, "3353": 10.0, "3365": 10.0},
            }
        return out

    effr_bk = {"2011Q4": 0.5, "2012Q1": 1.0, "2012Q2": 2.0}
    bp_ = bk_panel(False)
    expect([k for k in sorted(bp_["2012Q2"]) if in_bankers_class(bp_["2012Q2"][k])] == ["bb1", "bb2"],
           "the banker's bank class is the filers that certify and deduct in the same "
           "quarter, not either one alone")
    lr = {(r.period, r.rssd): r for r in lent_rows(bp_, "2011Q4", "2012Q2")}
    expect(lr[("2012Q1", "bb1")].expense == 4.0 and lr[("2012Q2", "bb1")].expense == 6.0
           and lr[("2012Q2", "bb1")].average == 300.0,
           "the asset leg differences its year-to-date income, Q1 alone, over its own average")
    bk = bankers_bank(bp_, quarter_rows(bp_, "2011Q4", "2012Q2"), effr_bk, draws=5)
    e1 = bk["eras"][0]["cells"]
    lent_q1 = 400.0 * 4.0 / 300.0
    expect(e1["class_lent"]["n"] == 2
           and abs(e1["class_lent"]["median_bp"] - 0.5 * (100.0 * (lent_q1 - 1.0) + 600.0)) < 1e-9,
           "the class's lending price is read where reverse repo is absent at both ends, "
           "and dropped at this end and at the previous end alone")
    expect(e1["class_borrowed"]["n"] == 4 and abs(e1["class_borrowed"]["median_bp"] - 200.0) < 1e-9,
           "the class's borrowing price is the RC-K arm's, against the quarter's EFFR")
    expect(abs(e1["class_margin"]["median_bp"] - 0.5 * (100.0 * (lent_q1 - 2.0) + 500.0)) < 1e-9,
           "the margin is the lending price less the borrowing price, where both are read")
    expect(e1["peer_borrowed"]["filers"] == 3 and e1["peer_borrowed"]["n"] == 6,
           "filers outside the class are taken inside its asset range, closed at both "
           "ends, and not beyond it")
    q2 = {r["quarter"]: r for r in bk["quarters"]}["2012Q2"]
    expect(q2 == {"quarter": "2012Q2", "class": 2, "class_borrowed": 2, "class_lent": 1,
                  "certified_without_deduction": 1}
           and bk["certified_never_deducting"] == ["cert0"],
           "per quarter the class and what can be read on it are counted, and a filer "
           "that certifies without deducting is named")
    lim = bk["deduction_over_limit"]
    expect(lim["rows"] == 6 and abs(lim["median"] - 0.55) < 1e-12 and lim["rows_at_limit"] == 0,
           "the deduction is read against its limit on every class row")
    s10 = build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None, bk)
    expect(s10["B59-S11"]["passed"] is True,
           "S11 reads true when no class row is at its limit")
    capped = bk_panel(True)
    bk_cap = bankers_bank(capped, quarter_rows(capped, "2011Q4", "2012Q2"), effr_bk, draws=5)
    expect(bk_cap["deduction_over_limit"]["rows_at_limit"] == 1
           and build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None,
                              bk_cap)["B59-S11"]["passed"] is False,
           "and flips when one class row's deduction equals its limit")
    none_ = bk_panel(False, deduct=False)
    bk_none = bankers_bank(none_, quarter_rows(none_, "2011Q4", "2012Q2"), effr_bk, draws=5)
    c_none = build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None, bk_none)
    expect(c_none["B59-S11"]["passed"] is False and c_none["B59-S10"]["passed"] is False,
           "and both flip when no filer is in the class")
    se_ok = {"0": 1.0, "1": 1.0}
    bk_ok = {"quarters": [{"quarter": "2012Q1", "class": 2, "class_borrowed": 1, "class_lent": 1,
                           "certified_without_deduction": 0}],
             "eras": [{"era": era_, "class_asset_range_thousands": [1.0, 2.0],
                       "cells": {n: {"n": 1, "filers": 1, "median_bp": 1.0} for n in BANKERS_CELLS},
                       "se_bp_resampling_filers": {k: dict(se_ok) for k in (
                           "class_borrowed", "class_lent", "class_margin",
                           "class_minus_peer_borrowed", "class_minus_peer_lent")}}
                      for era_, *_x in BANKERS_ERAS],
             "deduction_over_limit": {"rows": 1, "median": 0.5, "max": 0.5, "rows_at_limit": 0,
                                      "class_rows_without_limit": 0},
             "filers": [{"rssd": "1"}], "certified_never_deducting": []}
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None,
                          bk_ok)["B59-S10"]["passed"] is True,
           "S10 reads a well formed banker's bank object")
    b10 = json.loads(json.dumps(bk_ok))
    b10["eras"][-1]["cells"]["class_lent"]["n"] = 0
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None,
                          b10)["B59-S10"]["passed"] is False,
           "S10 flips when one era has no lending price for the class")
    b11 = json.loads(json.dumps(bk_ok))
    del b11["eras"][0]["se_bp_resampling_filers"]["class_minus_peer_lent"]
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None,
                          b11)["B59-S10"]["passed"] is False,
           "S10 flips when a gap to the peers has no standard error")
    b12 = json.loads(json.dumps(bk_ok))
    b12["eras"] = b12["eras"][1:]
    expect(build_criteria(meta, pan, anchor, bal, arms_ok, dec_ok, None, None,
                          b12)["B59-S10"]["passed"] is False,
           "S10 flips when an era of the certification is missing")

    if fails:
        print("\n  selftest FAILED")
        return 1
    print("\n  selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor", action="store_true",
                    help="rerun the first pass as it was run, 2009Q2 absent, and "
                         "print which of its numbers come back")
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--write", action="store_true",
                    help="run every arm, the anchor, the balances and the decomposition, "
                         "and write the record with its criteria")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--bankers", action="store_true",
                    help="the banker's bank class of 12 CFR 327.5(b) against filers in its asset range")
    ap.add_argument("--board", action="store_true",
                    help="the Board's larger and smaller classes over its own window")
    ap.add_argument("--fdic", action="store_true",
                    help="the RC-K arm against the FDIC $10 billion size line")
    ap.add_argument("--decompose", action="store_true",
                    help="the repo-weight decomposition on the RC-K average, without the no-repo filter")
    ap.add_argument("--balances", action="store_true",
                    help="quarter-end and two-end-mean balances against the RC-K average")
    ap.add_argument("--arm", choices=sorted(ARMS) + ["all"], default="all",
                    help="which arm to print in full; `all` prints a summary of every arm")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.write:
        rec = run_all(a.draws)
        RESULT.write_text(json.dumps(rounded(rec), ensure_ascii=False, indent=1,
                                     sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
        print(f"wrote {RESULT.relative_to(ROOT).as_posix()}")
        print_criteria(rec["criteria"])
        failed = [k for k, c in rec["criteria"].items() if c["passed"] is False]
        if failed:
            print("\n  FAILED[" + ",".join(rec["criteria"][k]["kind"] for k in failed)
                  + "]: " + ", ".join(failed))
        return 2 if failed else 0
    panel = load_panel()
    effr_year, effr_q = load_effr()
    absent = ("2009Q2",) if a.anchor else ()
    rows = quarter_rows(panel, *WINDOW, absent=absent)
    print(f"panel {len(panel)} periods; window {WINDOW[0]} to {WINDOW[1]}"
          + ("; 2009Q2 treated as absent" if a.anchor else ""))
    if a.anchor:
        obs = arm_quarter_end(rows)
        v, xs = validity(obs, effr_year), cross_section(obs, a.draws)
        print_validity(v)
        print_cross(xs)
        print("\n  the first pass against this code:")
        print(f"    {'item':<34} {'this code':>14} {'first pass':>14}")
        for item, mine, theirs, ok in compare_first_pass(v, xs):
            print(f"    {item:<34} {mine:>14} {theirs:>14}  {'reproduced' if ok else 'DIFFERS'}")
        return 0
    if a.fdic:
        print_fdic(fdic_line(panel, rows, effr_q, a.draws))
        return 0
    if a.board:
        print_board(board_classes(panel, rows, effr_q))
        return 0
    if a.bankers:
        print_bankers(bankers_bank(panel, rows, effr_q, a.draws))
        return 0
    if a.decompose:
        print("  decomposition on the RC-K average: cost over EFFR = a + b x repo weight, LAD")
        print_decompose(decompose(rows, effr_q))
        return 0
    if a.balances:
        print("  balance over the RC-K quarterly average, medians; repo at neither end")
        print(f"    {'band':<14} {'previous quarter end':<31} {'n':>6}  quarter end  mean of two ends")
        for c in balances(rows):
            print(f"    {c['band']:<14} {c['previous_end']:<31} {c['n']:>6,}  "
                  f"{c['median_quarter_end_over_average']:>11.3f}  "
                  f"{c['median_two_end_mean_over_average']:>15.3f}")
        return 0
    if a.arm != "all":
        label, build = ARMS[a.arm]
        obs = build(rows)
        print(f"arm {a.arm}: {label}")
        print_validity(validity(obs, effr_year))
        print_cross(cross_section(obs, a.draws))
        return 0
    for key, (label, build) in ARMS.items():
        obs = build(rows)
        print_summary(key, label, validity(obs, effr_year), cross_section(obs, a.draws),
                      levels(obs, effr_q))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
