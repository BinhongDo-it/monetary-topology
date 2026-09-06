"""B41-3, basis free: how much of the price structure is not a scalar potential.

The opponent says the basis at a position for a commodity is a commodity term
minus a position term, b(c,p) = f(c) - g(p). That is an additive two-way model,
and everything it forbids lives in the residual after row and column effects are
removed. The residual space has dimension (m-1)(n-1), which is the same b1 the
cycle count gives, and its norm does not depend on which cycles are picked as a
basis. That is the whole point of doing it this way: the anchored count in the
companion file moved between four and eight depending on the anchor, and a norm
cannot move.

Two readings come out, and they answer different questions:

  the share      what fraction of the spatial and commodity structure the
                 additive model fails to reproduce, unitless
  the level      the root mean square persistent residual per independent
                 cycle, in cents per bushel, against the one cent floor

The test is a moving block bootstrap, recentred: under the null the persistent
residual is zero, so the null distribution of the statistic is approximated by
the bootstrap deviations from the observed mean. Blocks keep the serial
dependence, and the same date blocks are used for every cell at once so the
cross-sectional dependence survives too.

The additive fit is alternating centring rather than a matrix solve, so that its
convergence is a printed number rather than a library's promise. It is checked
against a least squares solve on one day.

Reads only what b41_ams_probe.py has cached. No network, no key.

    python experiments/b41_joint.py --report 3186
    python experiments/b41_joint.py --report 3186 --blocks 20 60 100 250
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from itertools import combinations
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_persistence as P  # noqa: E402
import b41_square_smoke as S  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "b41"
TEST_WEIGHT_60 = {"Soybeans", "Wheat"}


def as_date(d: str) -> date:
    return date(int(d[6:]), int(d[:2]), int(d[3:5]))


def day_cells(rows: list[dict]) -> dict[tuple, float]:
    """(commodity key, position) -> basis midpoint, on the current window only.

    Matrices built from these cells in this file are (commodity, position).
    b41_magnitude builds the transpose. The numbers are the same either way;
    anything that indexes a row or column by meaning is not.

    A commodity whose futures month is not the same at every position that day
    is dropped for that day: differencing across months would import a calendar
    spread. A cell whose own range straddles two months is dropped outright."""
    raw: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r.get("quote_type") != "Basis" or r.get("sale Type") != "Bid":
            continue
        if r.get("commodity") not in TEST_WEIGHT_60:
            continue
        if r.get("delivery_start") or r.get("delivery_end"):
            continue
        m_lo, m_hi = r.get("basis Min Futures Month"), r.get("basis Max Futures Month")
        if not m_lo or m_lo != m_hi:
            continue
        lo, hi = r.get("basis Min"), r.get("basis Max")
        pos = S.position(r)
        if lo is None or hi is None or not pos:
            continue
        com = (r.get("commodity"), r.get("class") or "", r.get("grade") or "",
               r.get("protein") or "", r.get("conventional") or "",
               r.get("freight") or "", r.get("trans_mode") or "")
        raw[(com, pos)].append(((float(lo) + float(hi)) / 2, m_lo))
    months: dict[tuple, set] = defaultdict(set)
    for (com, _), vs in raw.items():
        months[com].update(m for _, m in vs)
    return {k: sum(v for v, _ in vs) / len(vs)
            for k, vs in raw.items() if len(months[k[0]]) == 1}


def additive_residual(mat: np.ndarray, mask: np.ndarray, tol=1e-10, cap=10000):
    """Alternating centring. Returns residual, sweeps used, worst leftover mean."""
    r = np.where(mask, mat, 0.0).astype(float)
    for k in range(cap):
        worst = 0.0
        for axis in (1, 0):
            cnt = mask.sum(axis=axis)
            tot = np.where(mask, r, 0.0).sum(axis=axis)
            with np.errstate(invalid="ignore", divide="ignore"):
                mu = np.where(cnt > 0, tot / np.maximum(cnt, 1), 0.0)
            worst = max(worst, float(np.abs(mu).max()) if cnt.size else 0.0)
            r = r - (mu[None, :] if axis == 0 else mu[:, None])
        r = np.where(mask, r, 0.0)
        if worst < tol:
            return r, k + 1, worst
    return r, cap, worst


def check_against_lstsq(mat, mask, resid) -> float:
    """Same fit through a least squares solve, for one day. Max abs difference."""
    n, m = mat.shape
    idx = np.argwhere(mask)
    A = np.zeros((len(idx), n + m))
    y = np.empty(len(idx))
    for t, (i, j) in enumerate(idx):
        A[t, i] = 1.0
        A[t, n + j] = 1.0
        y[t] = mat[i, j]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    fit = coef[:n][:, None] + coef[n:][None, :]
    alt = np.where(mask, mat - fit, 0.0)
    return float(np.abs(alt - resid).max())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, nargs="+", required=True,
                    help="one or more report ids; several print a summary table")
    ap.add_argument("--blocks", type=int, nargs="+", default=[20, 60, 100, 250])
    ap.add_argument("--draws", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--min-coverage", type=float, default=0.60)
    ap.add_argument("--one-commodity", metavar="NAME", default=None,
                    help="restrict the columns to grades of one commodity, "
                         "which is the shape Montana's block has")
    a = ap.parse_args()

    rows = []
    for rep in a.report:
        print(f"\n{'=' * 74}\nreport {rep}\n{'=' * 74}")
        try:
            got = analyse(a, rep)
        except SystemExit as exc:
            print(f"  skipped: {exc}")
            continue
        if got is not None:
            rows.append(got)
    if len(rows) > 1:
        print(f"\n{'=' * 74}\nacross states, one line each\n{'=' * 74}")
        hdr = (f"{'report':>7}{'days':>7}{'m':>4}{'n':>4}{'df':>4}"
               f"{'RMS c/bu':>10}{'share':>8}" +
               "".join(f"{'p@' + str(b):>9}" for b in a.blocks))
        print(hdr); print("-" * len(hdr))
        for r in rows:
            print(f"{r['report']:>7}{r['days']:>7}{r['positions']:>4}"
                  f"{r['commodities']:>4}{r['df']:>4}{r['rms']:>10.2f}"
                  f"{r['share']:>8.3f}" +
                  "".join(f"{r['p'][str(b)]:>9.4f}" for b in a.blocks))
        print("\nThe root mean square is per independent cycle, against a one "
              "cent floor. The share is the part of a day's variation the "
              "additive model cannot reproduce, in variance terms.")



def rectangle(per_day: dict, min_coverage: float,
              one_commodity: str | None = None):
    """The complete rectangle carrying the most independent cycles.

    Factored out so that the companion magnitude reading selects the same block
    this file selects, rather than a second copy of the rule that could drift
    from it. The body is unchanged from where it used to sit inline.

    A complete rectangle rather than whatever cells happen to clear the
    coverage bar. Illinois quotes soybeans and wheat at largely different
    positions, so the loose filter left a set with fewer cells than the
    additive model has parameters and no day could ever be fitted. Choosing
    the rectangle that maximises (|C|-1)(|P|-1) picks the block carrying the
    most independent cycles, which is the quantity the station is after, and
    it makes the centring exact and the degrees of freedom the plain formula.

    one_commodity restricts the columns to grades of a single named commodity.
    Left at None the behaviour is exactly what it was, which is the default
    every recorded reading was taken under. It exists so that the shape of
    Montana's block, eight grades of one commodity, can be built somewhere
    else and read against that state's own floor, which is the only way to
    tell a property of Montana from a property of that shape."""
    seen = defaultdict(int)
    for c in per_day.values():
        for k in c:
            seen[k] += 1
    need = min_coverage * len(per_day)
    keep = {k for k, v in seen.items() if v >= need}
    all_coms = sorted({k[0] for k in keep})
    if one_commodity is not None:
        all_coms = [c for c in all_coms if c[0] == one_commodity]
    best = None
    for r in range(2, len(all_coms) + 1):
        for subset in combinations(all_coms, r):
            ps = sorted({k[1] for k in keep
                         if all((c, k[1]) in keep for c in subset)})
            if len(ps) < 2:
                continue
            df_here = (len(ps) - 1) * (len(subset) - 1)
            if best is None or df_here > best[0]:
                best = (df_here, list(subset), ps)
    return best


def analyse(a, report: int) -> dict:
    by_day = P.load_all(report)
    per_day = {d: day_cells(rows) for d, rows in by_day.items()}
    per_day = {d: c for d, c in per_day.items() if c}
    best = rectangle(per_day, a.min_coverage,
                     getattr(a, 'one_commodity', None))
    if best is None:
        print(f"\nno commodity pair shares two positions at coverage >= "
              f"{a.min_coverage:.0%}. This carrier has no rectangle to read.")
        return None
    _, coms, poss = best
    ci = {c: i for i, c in enumerate(coms)}
    pi = {p: j for j, p in enumerate(poss)}
    keep = {(c, p) for c in coms for p in poss}
    print(f"\n{len(per_day)} usable days; largest complete rectangle at "
          f"coverage >= {a.min_coverage:.0%}: {len(coms)} x {len(poss)}")
    print(f"{len(coms)} commodity columns x {len(poss)} positions")
    for c in coms:
        print(f"   commodity: {c[0]} {c[1]} {c[2]} {c[3]}".rstrip())
    for p in poss:
        print(f"   position : {p}")

    dates = sorted(per_day, key=as_date)
    resid_by_day, checked = {}, None
    for d in dates:
        cells = {k: v for k, v in per_day[d].items() if k in keep}
        if len(cells) < len(keep):
            continue   # the rectangle must be complete on the day it is used
        mat = np.zeros((len(coms), len(poss)))
        mask = np.zeros_like(mat, dtype=bool)
        for (c, p), v in cells.items():
            mat[ci[c], pi[p]] = v
            mask[ci[c], pi[p]] = True
        if not (mask.any(axis=1).all() and mask.any(axis=0).all()):
            continue
        r, sweeps, worst = additive_residual(mat, mask)
        resid_by_day[d] = (r, mask, sweeps, worst)
        if checked is None:
            checked = (d, sweeps, worst, check_against_lstsq(mat, mask, r))

    print(f"\n{len(resid_by_day)} days with the rectangle complete")
    if checked is None:
        print("no day carries the whole rectangle. Lower --min-coverage or "
              "read a different commodity pair on this carrier.")
        return None
    d0, sw, worst, diff = checked
    print(f"alternating centring on {d0}: {sw} sweeps, worst leftover mean "
          f"{worst:.2e}; max difference against a least squares solve {diff:.2e}")

    days = sorted(resid_by_day, key=as_date)
    stack = np.stack([resid_by_day[d][0] for d in days])
    msk = np.stack([resid_by_day[d][1] for d in days])
    cnt = msk.sum(axis=0)
    rbar = np.where(cnt > 0, stack.sum(axis=0) / np.maximum(cnt, 1), 0.0)
    df = int(msk[0].sum()) - (len(coms) + len(poss) - 1)
    print(f"interaction degrees of freedom (m-1)(n-1) = {df}")

    print("\nthe persistent residual, cell by cell, in cents per bushel:")
    head = f"{'position':<38}" + "".join(f"{c[0][:4]+' '+c[1][:9]:>16}" for c in coms)
    print(head); print("-" * len(head))
    for p in poss:
        line = f"{p:<38}"
        for c in coms:
            line += f"{rbar[ci[c], pi[p]]:>+16.2f}"
        print(line)

    T = float(np.linalg.norm(rbar) / np.sqrt(df))
    tot = float(np.nanmean([np.var(stack[t][msk[t]]) for t in range(len(days))]))
    inter = float(np.nanmean([np.var(np.stack([resid_by_day[d][0]])[0][msk[t]])
                              for t, d in enumerate(days)]))
    raw_var = []
    share = []
    for t, d in enumerate(days):
        m_ = msk[t]
        vals = np.array([per_day[d][(c, p)] for c in coms for p in poss
                         if (c, p) in per_day[d]])
        v_tot = float(np.var(vals))
        v_int = float(np.var(stack[t][m_]))
        raw_var.append(v_tot)
        if v_tot > 0:
            share.append(v_int / v_tot)
    print(f"\nroot mean square persistent residual per independent cycle: "
          f"{T:.2f} cents per bushel, against a one cent floor")
    print(f"share of the day's variation the additive model cannot reproduce: "
          f"median {np.median(share):.3f}, mean {np.mean(share):.3f}")

    rng = random.Random(a.seed)
    n = len(days)
    results = {}
    print()
    for block in a.blocks:
        nb = max(n // block, 1)
        starts = max(n - block + 1, 1)
        worse = 0
        for _ in range(a.draws):
            picked = []
            for _ in range(nb):
                s0 = rng.randrange(starts)
                picked.extend(range(s0, min(s0 + block, n)))
            idx = np.array(picked)
            c2 = msk[idx].sum(axis=0)
            r2 = np.where(c2 > 0, stack[idx].sum(axis=0) / np.maximum(c2, 1), 0.0)
            if np.linalg.norm(r2 - rbar) >= np.linalg.norm(rbar):
                worse += 1
        p = worse / a.draws
        results[block] = p
        print(f"block {block:>4} trading days: recentred bootstrap p = "
              f"{p:.4f}  ({worse} of {a.draws} draws reach the observed norm)")

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"joint_{report}.json"
    dest.write_text(json.dumps(dict(
        report=report, days=len(days), df=df, rms_per_cycle=T,
        interaction_share_median=float(np.median(share)),
        p_by_block={str(k): v for k, v in results.items()},
        commodities=[list(c) for c in coms], positions=poss,
        residual={p: {str(c): float(rbar[ci[c], pi[p]]) for c in coms} for p in poss},
    ), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {dest.relative_to(REPO)}")
    return dict(report=report, days=len(days), df=df, rms=T,
                share=float(np.median(share)), positions=len(poss),
                commodities=len(coms),
                p={str(k): v for k, v in results.items()})


if __name__ == "__main__":
    main()
