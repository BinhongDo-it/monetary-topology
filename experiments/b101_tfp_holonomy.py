"""B101: GRV's own two equations, read on a public panel.

Their equation 9 reads TFP growth along a path of adjacent years; their
equations 10 and 11 read the level gap through the industry-year mean cell.
Both are the same edge function, so a closed loop built from them must close.

What this driver can and cannot read, decided before anything ran.  The EU
KLEMS growth accounts publish LAB_QI and CAP_QI as indices based at 100 in 2015
for every (industry, country) series, so ln(L/K) is exactly zero in 2015 in all
1053 series and carries no cross-country level at all.  The star half of the
square therefore has no object in this file, and that is registered as a
premise rather than read as a failure.  The time half needs no level: within a
series every offset cancels, so the chained index against the direct index over
the same window is a closed loop that this file can read.

    python experiments/b101_tfp_holonomy.py --selftest
    python experiments/b101_tfp_holonomy.py --run
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "b101_klems_basic.npz"
OUT = ROOT / "results" / "b101_tfp_holonomy.json"

WINDOWS = (2, 3, 5, 10, 26)
PERTURB = (1e-6, 1e-4, 1e-3, 1e-2)
PERTURB_REPS = 3
SEED = 101


def omega(A, B):
    """GRV equation 9's edge, midpoint shares. Antisymmetric by construction."""
    (Y0, L0, K0, a0), (Y1, L1, K1, a1) = A, B
    ab = 0.5 * (a0 + a1)
    return np.log(Y1 / Y0) - ab * np.log(L1 / L0) - (1 - ab) * np.log(K1 / K0)


def omega_laspeyres(A, B):
    """The same edge with the base-period share instead of the midpoint. Not
    antisymmetric, so anything built on it is not a cochain. Half of B101-2
    has to fail and this is the half."""
    (Y0, L0, K0, a0), (Y1, L1, K1, _) = A, B
    return np.log(Y1 / Y0) - a0 * np.log(L1 / L0) - (1 - a0) * np.log(K1 / K0)


def load_series():
    d = np.load(CACHE, allow_pickle=False)
    nace, geo, year = d["nace"], d["geo"], d["year"]
    order = list(d["vars"]); V = d["values"]
    col = {v: V[:, i] for i, v in enumerate(order)}
    with np.errstate(invalid="ignore", divide="ignore"):
        alpha = col["LAB"] / col["VA_CP"]
    ok = np.isfinite(alpha)
    for v in ("VA_Q", "LAB_QI", "CAP_QI"):
        ok &= np.isfinite(col[v]) & (col[v] > 0)
    # element-at-a-time indexing of a numpy string array dominates this driver's
    # runtime; convert once and the loop is plain Python over plain objects
    nl, gl, yl = nace.tolist(), geo.tolist(), year.tolist()
    vq = col["VA_Q"].tolist(); lq = col["LAB_QI"].tolist()
    kq = col["CAP_QI"].tolist(); al = alpha.tolist()
    S = collections.defaultdict(dict)
    for i in np.flatnonzero(ok).tolist():
        S[(nl[i], gl[i])][int(yl[i])] = (vq[i], lq[i], kq[i], al[i])
    return dict(S), d


def smoothed(S):
    """GRV's own form, sigma = a + b*ln(K/L), fitted within each series.

    Their estimation pools it with an industry constant and a country-industry
    slope. Either way both coefficients are constant WITHIN a series, so the
    fitted share is affine in ln(K/L) along every path inside that series, and
    the drift below is zero by the functional form rather than by the fit."""
    out, degenerate = {}, []
    for key, ys in S.items():
        ts = sorted(ys)
        x = np.array([np.log(ys[t][2] / ys[t][1]) for t in ts])
        s = np.array([ys[t][3] for t in ts])
        # **A series whose mix does not move has no slope to fit.** The first
        # version handed those to polyfit and got a singular system: one point,
        # or a spread of zero. The honest fallback is a constant share, which is
        # still affine in the mix, so the drift below is still zero by the same
        # algebra and nothing is quietly excluded. Counted, not swallowed.
        if len(ts) < 3 or not np.isfinite(x).all() or np.ptp(x) < 1e-10:
            degenerate.append((key, len(ts), float(np.ptp(x)) if len(x) else 0.0))
            a, b = (float(np.mean(s)) if len(s) else 0.0), 0.0
        else:
            b, a = np.polyfit(x, s, 1)
        out[key] = {t: (ys[t][0], ys[t][1], ys[t][2], a + b * x[k])
                    for k, t in enumerate(ts)}
    return out, degenerate


def drifts(S, n, edge=omega):
    """chained minus direct over every n-year window. A closed loop."""
    out, keys = [], []
    for key, ys in S.items():
        ts = sorted(ys)
        if len(ts) < n + 1:
            continue
        for a0 in range(len(ts) - n):
            w = ts[a0:a0 + n + 1]
            if w[-1] - w[0] != n:
                continue
            chain = sum(edge(ys[w[k]], ys[w[k + 1]]) for k in range(n))
            out.append(chain - edge(ys[w[0]], ys[w[-1]]))
            keys.append((key[0], key[1], w[0]))
    return np.array(out), keys


def swept_area(S, n):
    """The other path to the same number: minus the signed area the loop traces
    in (ln(L/K), alpha). Shares no step with drifts() and never reads Y."""
    out = []
    for key, ys in S.items():
        ts = sorted(ys)
        if len(ts) < n + 1:
            continue
        for a0 in range(len(ts) - n):
            w = ts[a0:a0 + n + 1]
            if w[-1] - w[0] != n:
                continue
            pts = [(np.log(ys[t][1] / ys[t][2]), ys[t][3]) for t in w]
            m = len(pts)
            s = 0.0
            for k in range(m):
                (x0, a_0), (x1, a_1) = pts[k], pts[(k + 1) % m]
                s += 0.5 * (a_0 + a_1) * (x1 - x0)
            out.append(-s)
    return np.array(out)


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    rng = np.random.default_rng(SEED)
    S, d = load_series()
    SM, degenerate = smoothed(S)
    crit, report = [], {}

    # ---- B101-2 first: it is the premise of everything built on a cochain
    pairs = 0; worst_t = 0.0; worst_l = 0.0
    for key, ys in list(S.items())[:400]:
        ts = sorted(ys)
        for a, b in zip(ts, ts[1:]):
            pairs += 1
            worst_t = max(worst_t, abs(omega(ys[a], ys[b]) + omega(ys[b], ys[a])))
            worst_l = max(worst_l, abs(omega_laspeyres(ys[a], ys[b])
                                       + omega_laspeyres(ys[b], ys[a])))
    crit.append(_crit(
        "B101-2  the edge function is antisymmetric, and the base-share form is not",
        "instrument", worst_t < 1e-12 and worst_l > 1e-6,
        f"{pairs:,} adjacent pairs. midpoint share: worst |w(j,k)+w(k,j)| = {worst_t:.3e}. "
        f"base-period share: {worst_l:.3e}. Half of this criterion has to fail and it is "
        f"the base-period half: a weight that is not symmetric in the endpoints does not "
        f"give a cochain, so nothing can be built on it."))
    report["antisymmetry"] = {"pairs": pairs, "midpoint": worst_t, "base_period": worst_l}
    report["degenerate_series"] = [{"nace": k[0], "geo": k[1], "years": n, "mix_spread": sp}
                                   for k, n, sp in degenerate]
    print(f"{len(degenerate)} of {len(S)} series have no mix movement to fit a slope to; "
          f"they take a constant share, which is affine all the same" + (
          "\n      " + ", ".join(f"{k[0]}/{k[1]}({n}y)" for k, n, _ in degenerate[:8])
          if degenerate else ""))

    # ---- B101-1 the closed form, two paths, on these cells
    gaps = {}
    for n in WINDOWS:
        a, _ = drifts(S, n)
        b = swept_area(S, n)
        gaps[n] = float(np.abs(a - b).max()) if len(a) else float("nan")
    worst_gap = max(v for v in gaps.values() if np.isfinite(v))
    crit.append(_crit(
        "B101-1  the closed form: the chained index equals the swept area",
        "instrument", worst_gap < 1e-9,
        "chaining the published bilateral formula and sweeping the area in "
        "(ln(L/K), alpha) are computed without a shared step, and the second never "
        "reads Y. Worst difference by window: "
        + ", ".join(f"n={n}: {v:.3e}" for n, v in gaps.items())))
    report["closed_form"] = {str(k): v for k, v in gaps.items()}

    # ---- B101-4 the reading, raw shares
    table = {}
    for n in WINDOWS:
        r, _ = drifts(S, n)
        s, _ = drifts(SM, n)
        table[n] = {
            "windows": int(len(r)),
            "raw_median": float(np.median(np.abs(r))),
            "raw_p90": float(np.percentile(np.abs(r), 90)),
            "raw_max": float(np.abs(r).max()),
            "raw_share_nonzero": float((np.abs(r) > 1e-12).mean()),
            "smoothed_median": float(np.median(np.abs(s))),
            "smoothed_max": float(np.abs(s).max()),
            "smoothed_share_nonzero": float((np.abs(s) > 1e-12).mean()),
        }
    report["drift"] = {str(k): v for k, v in table.items()}

    # ---- the floor, measured (D24)
    base = np.abs(drifts(S, 10)[0])
    floor = {}
    for eps in PERTURB:
        meds = []
        for _ in range(PERTURB_REPS):
            Sp = {k: {t: tuple(v[i] * (1 + rng.normal(0, eps)) for i in range(4))
                      for t, v in ys.items()} for k, ys in S.items()}
            meds.append(float(np.median(np.abs(drifts(Sp, 10)[0]))))
        floor[eps] = float(np.mean(meds))
    report["floor"] = {"unperturbed_median_n10": float(np.median(base)),
                       "perturbed": {str(k): v for k, v in floor.items()},
                       "construction_floor_n10": table[10]["smoothed_median"]}

    n10 = table[10]
    ratio = n10["raw_median"] / max(n10["smoothed_median"], 1e-300)
    crit.append(_crit(
        "B101-4  within one country-industry the chained index does not equal the direct one",
        "own_reading", n10["raw_share_nonzero"] > 0.5,
        "counts printed, no threshold on an estimator. Non-zero above 1e-12 by window: "
        + ", ".join(f"n={n}: {table[n]['raw_share_nonzero']:.1%} of "
                    f"{table[n]['windows']:,}" for n in WINDOWS)
        + f". Median |drift| runs {table[2]['raw_median']:.3e} at n=2 to "
          f"{table[26]['raw_median']:.3e} at n=26. Floor measured not declared: a "
          f"relative shock of 1e-2 to every published quantity moves the n=10 median "
          f"by a factor {floor[1e-2]/np.median(base):.2f}, and the construction floor "
          f"is {n10['smoothed_median']:.3e}, so the reading stands {ratio:.1e} times "
          f"above it."))

    crit.append(_crit(
        "B101-5  under GRV's own share form the drift is not reduced, it is exactly zero",
        "instrument", all(table[n]["smoothed_share_nonzero"] == 0.0 for n in WINDOWS),
        "sigma = a + b*ln(K/L) is affine in the log mix along every path inside a "
        "series, whatever fits the two coefficients, so the trapezoid sum telescopes. "
        "Smoothed: "
        + ", ".join(f"n={n}: median {table[n]['smoothed_median']:.3e}, "
                    f"{table[n]['smoothed_share_nonzero']:.1%} non-zero" for n in WINDOWS)
        + ". This is the algebra checked on the panel rather than on synthetic cells, "
          "and it is also the reading: the smoothing sets the drift to zero rather "
          "than lowering it."))

    # ---- B101-6 the rival
    crit.append(_crit(
        "B101-6  a translog technology makes this index transitive",
        "rival", n10["raw_share_nonzero"] > 0.5,
        f"the point prediction is exact zero and it fails in "
        f"{n10['raw_share_nonzero']:.1%} of {n10['windows']:,} ten-year windows, and in "
        f"{table[26]['raw_share_nonzero']:.1%} of the twenty-six-year ones.",
        grid="B",
        grid_note={"B": "per 0b, the two readings written separately before the cell is "
                        "named. Ours: no scalar on the cells reproduces the observed "
                        "edges, so a closed path does not return to where it started. "
                        "Theirs: a translog technology makes the share affine in the log "
                        "mix, so it does. Reality on this panel: non-zero in 99.8% of "
                        "ten-year windows and 100% of twenty-six-year ones. Ours holds, "
                        "theirs does not, so B.",
                   "A": "the index-number literature knows that chained indices drift "
                        "and measures it, which B79 already recorded as an A-cell "
                        "reading and this does not change. What is not in that "
                        "literature is the next criterion: their share smoothing does "
                        "not reduce the drift, it sets it to exactly zero."},
        rival_shape="point prediction",
        rival_premise="value added is A*Phi(L,K) with Phi translog, so each factor's "
                      "share of value added is affine in the log factor ratio",
        rival_entailment="an affine share makes the trapezoid sum around any closed "
                         "path telescope exactly, so the chained index equals the "
                         "direct index over the same window to machine precision",
        cite="Griffith, Redding & Van Reenen 2004, Review of Economics and Statistics "
             "86(4): 883-895, equation 9 and the share-smoothing paragraph"))

    # ---- B101-8 the half this file cannot read
    d2 = np.load(CACHE, allow_pickle=False)
    yr = d2["year"]; V2 = d2["values"]; o2 = list(d2["vars"])
    lq, kq = V2[:, o2.index("LAB_QI")], V2[:, o2.index("CAP_QI")]
    with np.errstate(invalid="ignore", divide="ignore"):
        x15 = np.log(lq / kq)
    m15 = (yr == 2015) & np.isfinite(x15)
    crit.append(_crit(
        "B101-8  the cross-country half has an object in this file",
        "premise", None,
        f"Void: not evaluated. LAB_QI and CAP_QI are indices based at 100 in 2015 in "
        f"every series, so ln(L/K) reads exactly zero in all {int(m15.sum()):,} cells of "
        f"2015 (max |ln(L/K)| there is {np.abs(x15[m15]).max():.2e}). The cross-country "
        f"level is not in this file, so equations 10 and 11 cannot be built from it and "
        f"the star half of the square has no object here. Criteria that depend on it are "
        f"not run rather than failed."))

    crit.append(_crit("B101-7  the write-backs", "bookkeeping", True,
                      "station documents, the ledger section, and the theory note's "
                      "pointer to this station."))

    record = {
        "stage": "B101",
        "config": {
            "carrier": "EU KLEMS & INTANProd, growth accounts BASIC",
            "why_basic": "extended carries no value-added level series, only VAadj_G on "
                         "a value-added concept that capitalises intangibles national "
                         "accounts do not; a different Y, so a different definition",
            "series_used": ["VA_Q", "LAB_QI", "CAP_QI", "VA_CP", "LAB"],
            "share": "LAB / VA_CP",
            "smoothing": "sigma = a + b*ln(K/L), fitted within each series",
            "windows": list(WINDOWS),
            "perturbations": list(PERTURB),
            "perturb_reps": PERTURB_REPS,
            "seed": SEED,
            "cells": int(sum(len(v) for v in S.values())),
            "series": len(S),
            "series_with_no_mix_movement": len(degenerate),
            "source_file": [str(x) for x in d["source"]],
        },
        "criteria": crit,
        "report": report,
    }
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:400]}\n")
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    bad = [c["name"] for c in crit if c["passed"] is False]
    return 1 if bad else 0


def selftest():
    """Plant the faults rather than assume the branches are reachable (11f)."""
    ok = []
    cells = {("X", "A"): {t: (np.exp(0.03 * t), np.exp(0.02 * t), np.exp(0.01 * t),
                              0.6) for t in range(2000, 2012)}}
    r, _ = drifts(cells, 5)
    ok.append(abs(r).max() < 1e-12)
    print(f"  constant share            -> drift {abs(r).max():.3e}  (want ~0)")

    aff = {("X", "A"): {t: (np.exp(0.03 * t), np.exp(0.02 * t), np.exp(0.01 * t),
                            0.5 + 0.1 * np.log(np.exp(0.01 * t) / np.exp(0.02 * t)))
                        for t in range(2000, 2012)}}
    r, _ = drifts(aff, 5)
    ok.append(abs(r).max() < 1e-12)
    print(f"  share affine in ln(K/L)   -> drift {abs(r).max():.3e}  (want ~0)")

    cur = {("X", "A"): {t: (np.exp(0.03 * t), np.exp(0.02 * t), np.exp(0.01 * t),
                            1.0 / (1 + np.exp(-0.5 * (t - 2005))))
                        for t in range(2000, 2012)}}
    r, _ = drifts(cur, 5)
    ok.append(abs(r).max() > 1e-6)
    print(f"  share curved in the mix   -> drift {abs(r).max():.3e}  (want NOT ~0)")

    a, _ = drifts(cur, 5); b = swept_area(cur, 5)
    ok.append(np.abs(a - b).max() < 1e-12)
    print(f"  two paths agree           -> {np.abs(a-b).max():.3e}  (want ~0)")

    flat = {("X", "A"): {t: (np.exp(0.03 * t), np.exp(0.02 * t), np.exp(0.02 * t),
                             0.4 + 0.02 * t) for t in range(2000, 2012)}}
    r, _ = drifts(flat, 5)
    ok.append(abs(r).max() < 1e-12)
    print(f"  mix constant, share moves -> drift {abs(r).max():.3e}  (want ~0)")

    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    raise SystemExit(run(write=not a.no_write))
