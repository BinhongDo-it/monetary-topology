"""§16.1's open item: how much of the contrast survives holding wealth fixed.

**Status: diagnostic, not a registered criterion.** It scores nothing, moves no
threshold and writes no file. `docs/a3_asset_channel.md` §6.4c leaves exactly
one question open and this answers it, or reports that it cannot be answered on
the support available, which is also an answer.

The question
------------

§6.4c ends with a shape that is mixed. Holders retain more than non-holders,
and within the holders retention still climbs with wealth
(`Spearman = +0.496` registered at shock round 20, `+0.386` with rent off),
which a pure step does not predict. Reading that contrast through wealth deciles
gives an inconsistent answer: fourteen-fold in one decile, one-and-a-third in
the next, eleven-fold in the one after. Bins are the wrong instrument here
because holders and non-holders barely overlap in wealth, so a bin either
contains almost no holders or almost no non-holders and its ratio is carried by
whichever side is thin.

So the contrast is taken pairwise on the **common support** instead: the wealth
interval where both groups actually exist. Each holder inside it is matched to
the nearest non-holder by wealth at the shock round, and the paired difference
is the step with wealth held fixed. Outside the support there is nothing to
control with, and holders there are dropped and counted rather than compared
against an extrapolation.

Everything this reads is pre-treatment. `wealth_at_shock` and `holder` are both
measured at the shock round, before the transfer lands, so `MEASUREMENT.md`
checklist item 5 is satisfied by construction rather than by argument.

The noise floor
---------------

A matched difference means nothing without a scale. Checklist item 7 asks for an
arm whose true value should be zero running the same machinery, so the same
matcher is run **non-holder against non-holder**: each non-holder in the support
is paired with its nearest *other* non-holder and the same statistic is taken.
Retention is smooth in wealth or it is not, and either way that distribution is
what a difference of zero looks like through this instrument. A step smaller
than its spread is not a step this instrument can see.

Reading
-------

* Paired median well above the noise floor, sign share above the floor's ->
  a step survives with wealth held fixed.
* Paired median inside the noise floor and the sign share at the floor's ->
  the contrast was wealth, and the deciles were reading collinearity.
* Support too thin to match -> neither, and the profile cannot answer it. That
  is the outcome §6.4c already flags as possible, since the holder block sits at
  the top of the wealth ranking.

**The sign share was promoted to the headline after the first run and the
reason is disclosed here rather than left in the history.** The first version
read the median against the noise floor's interquartile width alone. On the
data that rule discards the answer: the paired differences are extremely
skewed, with a median near zero and an upper quartile two orders of magnitude
above the floor's, so a median-only rule reports "nothing" for a distribution
whose mass has moved entirely into one tail. A sign test is the standard
nonparametric reading of matched pairs and it is not sensitive to that skew.
Both statistics are printed and neither is scored, so the change adds a column
rather than selecting one. The noise-floor arm supplies the null share
empirically, which is why the comparison is against it and not against a half.

Run
---

    python experiments/a3e_step_or_gradient.py
    python experiments/a3e_step_or_gradient.py --horizon 149
    python experiments/a3e_step_or_gradient.py --group financial
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

#: Read in this order every time, so the printed report does not depend on the
#: filesystem's glob order. A missing file is reported and skipped, because the
#: arms are produced by separate commands and a reader may have run only some.
FILES = (
    "a3_retention_profile.json",
    "a3_retention_profile.rent-by-holding.shock150.json",
    "a3_retention_profile.rent-off.shock150.json",
    "a3_retention_profile.registered.shock20.json",
    "a3_retention_profile.rent-off.shock20.json",
)

#: Below this many matched pairs the report is refused rather than printed. Not
#: a registered threshold: nothing here is scored. It exists so that a median
#: over three pairs is never displayed as if it were a reading.
MIN_PAIRS = 12


def rankdata(a: np.ndarray) -> np.ndarray:
    """Average ranks, ties shared. Enough for a Spearman without scipy."""
    order = np.argsort(a, kind="stable")
    ranks = np.empty(a.size, dtype=float)
    ranks[order] = np.arange(1, a.size + 1, dtype=float)
    # Average the ranks inside each tie group, so a tied pair does not get an
    # order-dependent rank and the statistic stays a function of the data.
    vals, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    for k in np.flatnonzero(counts > 1):
        m = inv == k
        ranks[m] = ranks[m].mean()
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3:
        return float("nan")
    rx, ry = rankdata(x), rankdata(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    d = float(np.sqrt((rx * rx).sum() * (ry * ry).sum()))
    return float((rx * ry).sum() / d) if d > 0 else float("nan")


def nearest(target: np.ndarray, pool: np.ndarray) -> np.ndarray:
    """Index into a **sorted** ``pool`` of the value nearest each ``target``."""
    j = np.searchsorted(pool, target)
    j = np.clip(j, 1, pool.size - 1)
    left = np.abs(target - pool[j - 1])
    right = np.abs(pool[j] - target)
    return np.where(left <= right, j - 1, j)


def nearest_other(w: np.ndarray) -> np.ndarray:
    """For each element of a **sorted** ``w``, the index of its nearest other.

    The noise-floor arm. Pairing a point with itself would report a difference
    of exactly zero for every pair and would calibrate nothing.
    """
    n = w.size
    out = np.empty(n, dtype=int)
    for i in range(n):
        if i == 0:
            out[i] = 1
        elif i == n - 1:
            out[i] = n - 2
        else:
            out[i] = i - 1 if (w[i] - w[i - 1]) <= (w[i + 1] - w[i]) else i + 1
    return out


def pairing(rows: list[dict]) -> dict:
    """The matched pairs and the noise-floor pairs for one seed.

    **Horizon-free on purpose.** Matching is on wealth at the shock round, which
    does not depend on how long afterwards retention is read, so the pair set is
    the same at every horizon. `--tail` relies on that: a series taken over a
    pair set that moved with the horizon would be measuring the matcher.
    """
    hold = [r for r in rows if r["holder"]]
    free = [r for r in rows if not r["holder"]]
    if not hold or len(free) < 3:
        return {"n_hold": len(hold), "n_free": len(free), "matched": 0}

    hw = np.array([r["wealth_at_shock"] for r in hold], dtype=float)
    fw = np.array([r["wealth_at_shock"] for r in free], dtype=float)

    o = np.argsort(fw, kind="stable")
    fw = fw[o]
    free = [free[i] for i in o]

    # Common support: the wealth interval where both groups exist. Holders
    # outside it have no control to be compared against and are counted, not
    # matched against an extrapolation.
    lo = max(hw.min(), fw.min())
    hi = min(hw.max(), fw.max())
    inside = (hw >= lo) & (hw <= hi)

    j = nearest(hw[inside], fw)
    hold_in = [r for r, m in zip(hold, inside, strict=True) if m]
    dist = np.abs(hw[inside] - fw[j])

    in_free = (fw >= lo) & (fw <= hi)
    fw_s = fw[in_free]
    free_s = [r for r, m in zip(free, in_free, strict=True) if m]
    if fw_s.size >= 3:
        k = nearest_other(fw_s)
        floor_a = free_s
        floor_b = [free_s[i] for i in k]
        floor_dist = np.abs(fw_s - fw_s[k])
    else:
        floor_a = floor_b = []
        floor_dist = np.array([])

    return {
        "n_hold": len(hold),
        "n_free": len(free),
        "support": (float(lo), float(hi)),
        "matched": int(inside.sum()),
        "dropped": int((~inside).sum()),
        "hold_rows": hold_in,
        "ctrl_rows": [free[i] for i in j],
        "floor_a": floor_a,
        "floor_b": floor_b,
        "dist": dist,
        "floor_dist": floor_dist,
        "free_support_w": fw_s,
        "hold_support_w": hw[inside],
    }


def at(rows: list[dict], horizon: str) -> np.ndarray:
    return np.array([r["retention_by_horizon"][horizon] for r in rows],
                    dtype=float)


def pairs_for_seed(rows: list[dict], horizon: str) -> dict:
    """``pairing`` read at one horizon. The default mode's view."""
    p = pairing(rows)
    if not p.get("matched"):
        return p
    return {
        **p,
        "step": at(p["hold_rows"], horizon) - at(p["ctrl_rows"], horizon),
        "floor": at(p["floor_a"], horizon) - at(p["floor_b"], horizon),
        "free_support_r": at(p["floor_a"], horizon),
        "hold_support_r": at(p["hold_rows"], horizon),
    }


def report(path: Path, horizon: str, group: str) -> None:
    blob = json.loads(path.read_text(encoding="utf-8"))
    rows = blob["rows"]
    arm = blob.get("arm", "?")
    shock = blob.get("shock_round", "?")
    print(f"\n{'=' * 78}\n{path.name}")
    print(f"  arm {arm}, shock round {shock}, horizon {horizon}, "
          f"group {group}")

    if group == "production":
        rows = [r for r in rows if r["production"]]
    elif group == "financial":
        rows = [r for r in rows if not r["production"]]

    seeds = sorted({r["seed"] for r in rows})
    agg: dict[str, list] = {
        "step": [], "dist": [], "floor": [], "floor_dist": [],
        "fw": [], "fr": [], "hw": [], "hr": [],
    }
    matched = dropped = n_hold = n_free = no_support = 0
    print("\n  per seed, so the arithmetic below is visible rather than pooled")
    print("    seed  holders  matched  dropped  support in wealth")
    for s in seeds:
        p = pairs_for_seed([r for r in rows if r["seed"] == s], horizon)
        n_hold += p["n_hold"]
        n_free += p["n_free"]
        if not p["matched"]:
            # A seed whose holders are all richer than every non-holder has no
            # common support at all. Counting it as zero matched pairs and
            # moving on would let it vanish from the totals, and its existence
            # is part of the answer: it is the collinearity §16.1 flagged,
            # showing up as an empty interval rather than as a weak contrast.
            no_support += 1
            dropped += p["n_hold"]
            print(f"    {s:>4}  {p['n_hold']:>7}  {0:>7}  {p['n_hold']:>7}  "
                  f"none: no wealth overlap")
            continue
        matched += p["matched"]
        dropped += p["dropped"]
        lo, hi = p["support"]
        print(f"    {s:>4}  {p['n_hold']:>7}  {p['matched']:>7}  "
              f"{p['dropped']:>7}  [{lo:.4f}, {hi:.4f}]")
        agg["step"].append(p["step"])
        agg["dist"].append(p["dist"])
        agg["floor"].append(p["floor"])
        agg["floor_dist"].append(p["floor_dist"])
        agg["fw"].append(p["free_support_w"])
        agg["fr"].append(p["free_support_r"])
        agg["hw"].append(p["hold_support_w"])
        agg["hr"].append(p["hold_support_r"])

    print(f"\n  holders {n_hold}, non-holders {n_free}, matched {matched}, "
          f"dropped outside the support {dropped}"
          + (f", seeds with no overlap at all {no_support}" if no_support
             else ""))
    if matched < MIN_PAIRS:
        print(f"  REFUSED: {matched} matched pairs is below {MIN_PAIRS}. The "
              f"support is too thin\n  for this reading, which is itself the "
              f"answer for this arm.")
        return

    step = np.concatenate(agg["step"])
    dist = np.concatenate(agg["dist"])
    floor = np.concatenate(agg["floor"])
    fdist = np.concatenate(agg["floor_dist"])
    fw = np.concatenate(agg["fw"])
    fr = np.concatenate(agg["fr"])
    hw = np.concatenate(agg["hw"])
    hr = np.concatenate(agg["hr"])

    # Balance first. A matched contrast whose pairs are far apart in wealth has
    # not controlled for wealth, and reading its median would be reporting the
    # confound under the name of the treatment.
    print("\n  balance of the match, in wealth at the shock round")
    print(f"    matched pairs      median |dw| = {np.median(dist):.4f}, "
          f"p90 = {np.quantile(dist, 0.90):.4f}")
    print(f"    noise-floor pairs  median |dw| = {np.median(fdist):.4f}, "
          f"p90 = {np.quantile(fdist, 0.90):.4f}")
    print(f"    wealth on the support: holders median {np.median(hw):.4f}, "
          f"non-holders median {np.median(fw):.4f}")

    print("\n  the step, wealth held fixed by the match")
    print(f"    median paired difference   {np.median(step):+.4f}")
    print(f"    quartiles                  {np.quantile(step, 0.25):+.4f} to "
          f"{np.quantile(step, 0.75):+.4f}")
    print(f"    share of pairs holder wins {np.mean(step > 0):.1%} of "
          f"{step.size}")

    print("\n  the noise floor, same matcher on non-holders only")
    print(f"    median paired difference   {np.median(floor):+.4f}")
    print(f"    quartiles                  {np.quantile(floor, 0.25):+.4f} to "
          f"{np.quantile(floor, 0.75):+.4f}")
    print(f"    share of pairs first wins  {np.mean(floor > 0):.1%} of "
          f"{floor.size}")
    iqr = np.quantile(floor, 0.75) - np.quantile(floor, 0.25)
    print(f"    interquartile width        {iqr:.4f}")

    print("\n  the gradient, on the same support")
    print(f"    Spearman(retention, wealth) within non-holders "
          f"{spearman(fw, fr):+.3f}  n={fw.size}")
    print(f"    Spearman(retention, wealth) within holders     "
          f"{spearman(hw, hr):+.3f}  n={hw.size}")

    med = float(np.median(step))
    share = float(np.mean(step > 0))
    null_share = float(np.mean(floor > 0))
    # Descriptive only. The spread of a share on this many pairs, printed so a
    # reader can see whether the gap between the two shares is larger than the
    # arithmetic allows, without a threshold being registered anywhere.
    se = float(np.sqrt(max(share * (1.0 - share), 1e-12) / step.size))
    print("\n  reading, both statistics, neither scored")
    print(f"    sign : holder wins {share:.1%} against the floor's "
          f"{null_share:.1%}, spread {se:.1%} on {step.size} pairs")
    inside = abs(med) <= iqr
    print(f"    level: median {med:+.4f} "
          + ("inside" if inside else "outside")
          + f" the floor's interquartile width {iqr:.4f}")
    if share - null_share > 2.0 * se and inside:
        print("    The two disagree, and that is the finding. Holding shifts "
              "the sign of the\n    paired difference without shifting its "
              "middle, so what it buys is a\n    skewed upper tail rather than "
              "a level. Read the quartiles above: the\n    step's upper "
              "quartile is orders of magnitude past the floor's while its\n"
              "    median is not.")
    elif share - null_share > 2.0 * se:
        print("    Both point the same way: a step survives with wealth held "
              "fixed, and its\n    size is the paired median above rather than "
              "any raw group ratio.")
    else:
        print("    Neither separates from the floor. On this support the "
              "contrast is not\n    distinguishable from what wealth alone "
              "produces, and the decile ratios\n    were reading "
              "collinearity.")
    print("    Not scored. No threshold is registered for any of it.")


#: The horizons the profile already stores, read in this order.
HORIZONS = ("10", "20", "40", "80", "149")

#: The horizon the other statistics are compared against, because it is the one
#: A3-6 registers and the one §6.4c's tables are taken at.
REF = "40"


def concentration(d: np.ndarray) -> float:
    """Share of the summed positive advantage carried by the top tenth of pairs.

    Threshold-free, which is why it is used instead of "pairs above `x`". A
    level shift spreads the total across the pairs and lands near a tenth; a
    lottery puts most of it in the few pairs that won, and lands near one.
    """
    pos = d[d > 0].sum()
    if d.size < 10 or pos <= 0:
        return float("nan")
    k = max(1, int(np.ceil(0.1 * d.size)))
    return float(np.sort(d)[-k:].sum() / pos)


def top_set(d: np.ndarray) -> set[int]:
    k = max(1, int(np.ceil(0.1 * d.size)))
    return set(np.argsort(d, kind="stable")[-k:].tolist())


def tail_report(path: Path, group: str) -> None:
    """The shape of the upper tail, on one pair set, across all five horizons.

    Three questions the default mode cannot answer, and all three are about the
    same fixed pairs read at different times.

    **Does the sign asymmetry hold at every horizon**, or is it one moment?

    **Is the advantage a level or a lottery**, measured as the share of the
    positive total carried by the top tenth of pairs, against the noise floor
    measured the same way. A level shift lands near a tenth; a lottery near one.

    **Is it the same pairs winning**, or does the winner rotate? Rank
    correlation against the registered horizon, and the overlap of the top
    tenth. Conclusion 34 of this project's own record is the reason to ask: top
    concentration there turned out to be entirely turnover, and the same two
    readings would have been indistinguishable without this check.
    """
    blob = json.loads(path.read_text(encoding="utf-8"))
    rows = blob["rows"]
    print(f"\n{'=' * 78}\n{path.name}   TAIL")
    print(f"  arm {blob.get('arm', '?')}, shock round "
          f"{blob.get('shock_round', '?')}, group {group}")

    if group == "production":
        rows = [r for r in rows if r["production"]]
    elif group == "financial":
        rows = [r for r in rows if not r["production"]]

    seeds = sorted({r["seed"] for r in rows})
    hold_rows: list[dict] = []
    ctrl_rows: list[dict] = []
    fa: list[dict] = []
    fb: list[dict] = []
    for s in seeds:
        p = pairing([r for r in rows if r["seed"] == s])
        if not p.get("matched"):
            continue
        hold_rows += p["hold_rows"]
        ctrl_rows += p["ctrl_rows"]
        fa += p["floor_a"]
        fb += p["floor_b"]

    if len(hold_rows) < MIN_PAIRS:
        print(f"  REFUSED: {len(hold_rows)} matched pairs is below "
              f"{MIN_PAIRS}.")
        return

    step = {h: at(hold_rows, h) - at(ctrl_rows, h) for h in HORIZONS}
    floor = {h: at(fa, h) - at(fb, h) for h in HORIZONS}
    print(f"  one fixed pair set of {len(hold_rows)}, matched on wealth at the "
          f"shock round,\n  read at five horizons. The floor has "
          f"{len(fa)} pairs.")

    print("\n  sign and level")
    print("    horiz   wins   floor      p50        p75        p90   floor p90")
    for h in HORIZONS:
        d, f = step[h], floor[h]
        print(f"    {h:>5}  {np.mean(d > 0):5.1%}  {np.mean(f > 0):5.1%}  "
              f"{np.median(d):+9.4f}  {np.quantile(d, 0.75):+9.4f}  "
              f"{np.quantile(d, 0.90):+9.4f}  {np.quantile(f, 0.90):+9.4f}")

    print("\n  is it a level or a lottery, and does the winner rotate")
    print("    horiz   top-tenth share   floor's   rho vs h40   top-tenth "
          "kept from h40")
    ref_top = top_set(step[REF])
    for h in HORIZONS:
        d = step[h]
        keep = len(top_set(d) & ref_top) / max(len(ref_top), 1)
        print(f"    {h:>5}          {concentration(d):6.1%}    "
              f"{concentration(floor[h]):6.1%}       "
              f"{spearman(d, step[REF]):+6.3f}          {keep:6.1%}")

    print("\n  reading, not scored")
    c = concentration(step[REF])
    cf = concentration(floor[REF])
    print(f"    At the registered horizon the top tenth of pairs carries "
          f"{c:.1%} of the\n    positive total against the floor's {cf:.1%}. "
          f"A level shift would land near\n    a tenth in both columns.")
    print("    The rotation column says whether the same holders keep winning "
          "or whether\n    the tail is a different set each time it is read. "
          "Both are findings and\n    they are different findings.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--horizon", default="40", choices=("10", "20", "40",
                                                        "80", "149"))
    ap.add_argument("--group", default="production",
                    choices=("production", "financial", "all"))
    ap.add_argument("--files", nargs="*", default=None,
                    help="profile JSONs to read; defaults to the five arms")
    ap.add_argument("--tail", action="store_true",
                    help="read one fixed pair set at all five horizons and "
                         "report the shape of the upper tail instead of the "
                         "single-horizon contrast")
    args = ap.parse_args()

    names = args.files if args.files else FILES
    seen = 0
    for name in names:
        path = Path(name) if args.files else RESULTS / name
        if not path.exists():
            print(f"\n  skipped, not on disk: {path.name}")
            continue
        if args.tail:
            tail_report(path, args.group)
        else:
            report(path, args.horizon, args.group)
        seen += 1
    if not seen:
        print("\n  nothing read. Run the profile arms first; "
              "`docs/a3_asset_channel.md` §6.4c lists the four commands.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
