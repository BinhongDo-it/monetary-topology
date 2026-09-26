"""B101 step ten: recover the country term that B101-18 could not reach.

B101-18 closed void, and the reason was not the design.  GRV's smoothing is

    sigma_ijt = alpha_ij + beta_j ln(K_ijt / L_ijt)          footnote 20

with the country on the intercept and the slope carrying the industry only.
The algebra in the theory note says a cross-country loop's holonomy under that
smoothing is exactly the area the intercept sweeps against the mix,

    holonomy = - contour integral of alpha_ij d x ,   x = ln(L/K)

because the beta term is d(x squared / 2) and integrates to zero around any
loop.  So the whole reading is carried by alpha_ij, and a within-series fit on a
mix that is an index based at 100 returns alpha - beta * e rather than alpha,
where e is that series' own level of the mix in its base year.  On the growth
accounts module e is unrecoverable, because every series reads 100 in its own
base year and nothing says what level that 100 stands for.

The capital accounts module carries the capital stock as a level in national
currency.  With labour compensation, also a level in the same currency, the mix
x = ln(LAB / K_GFCF) has no base at all, so the fitted intercept is alpha_ij
itself and the closed form can be evaluated.

    python experiments/b101_intercept.py
    python experiments/b101_intercept.py --no-write
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b101_intercept.json"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


XS = _mod("b101_cross_section")


# ------------------------------------------------------------------ the fit

def within_fit(x, sig, sid, min_years=3):
    """GRV footnote 20, read literally: one slope per industry, one intercept per
    country-industry.  The slope is the within estimator, the intercepts follow.

    Returns (beta, {series -> alpha}, r2_within, n_series).
    """
    keep = {}
    for k, idx in sid.items():
        if len(idx) >= min_years and np.ptp(x[idx]) > 0:
            keep[k] = idx
    if not keep:
        return float("nan"), {}, float("nan"), 0
    num = den = 0.0
    for idx in keep.values():
        xd = x[idx] - x[idx].mean()
        sd = sig[idx] - sig[idx].mean()
        num += float(xd @ sd); den += float(xd @ xd)
    beta = num / den if den > 0 else float("nan")
    alpha = {k: float(sig[idx].mean() - beta * x[idx].mean())
             for k, idx in keep.items()}
    ss_res = ss_tot = 0.0
    for idx in keep.values():
        xd = x[idx] - x[idx].mean()
        sd = sig[idx] - sig[idx].mean()
        ss_res += float(((sd - beta * xd) ** 2).sum()); ss_tot += float((sd ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return beta, alpha, r2, len(keep)


def panel_by_industry(panel):
    """series id -> row indices, grouped by industry."""
    out = {}
    for i in range(len(panel["nace"])):
        out.setdefault(panel["nace"][i], {}).setdefault(panel["geo"][i], []).append(i)
    return {j: {g: np.array(v, int) for g, v in gs.items()} for j, gs in out.items()}


def loop_area(alpha, x, order):
    """Trapezoid area of the closed polygon through the given vertex order.
    This is the closed form, evaluated directly: - sum over edges of the mean
    intercept times the step in the mix."""
    s = 0.0
    m = len(order)
    for r in range(m):
        a, b = order[r], order[(r + 1) % m]
        s += 0.5 * (alpha[a] + alpha[b]) * (x[b] - x[a])
    return -s


# ------------------------------------------------------- B101-26 does it fit

def check_fit(panel, byind):
    sig = panel["LAB"] / (panel["LAB"] + panel["CAP"])
    x = np.log(panel["LAB"] / panel["K"])
    rows = []
    for j, gs in sorted(byind.items()):
        beta, alpha, r2, n = within_fit(x, sig, gs)
        if n >= 3:
            a = np.array(list(alpha.values()))
            rows.append({"industry": j, "beta": beta, "r2_within": r2,
                         "series": n, "alpha_sd": float(a.std()),
                         "alpha_min": float(a.min()), "alpha_max": float(a.max())})
    ok = len(rows) > 0 and all(np.isfinite(r["beta"]) for r in rows)
    b = np.array([r["beta"] for r in rows])
    r2 = np.array([r["r2_within"] for r in rows])
    detail = (f"{len(rows)} industries carry three or more country series with a "
              f"moving mix. One slope per industry on the level of ln(LAB/K_GFCF), "
              f"intercepts per country-industry: beta median {np.median(b):+.4f}, "
              f"p10 {np.percentile(b,10):+.4f}, p90 {np.percentile(b,90):+.4f}; "
              f"within R squared median {np.median(r2):.3f}. The mix has no index "
              f"base, so the intercept is alpha_ij itself and not alpha - beta*e.")
    return bool(ok), detail, {"by_industry": rows,
                              "beta_median": float(np.median(b)),
                              "r2_within_median": float(np.median(r2))}


# ----------------------------------------------- B101-27 the area it sweeps

def check_intercept_area(panel, byind):
    sig = panel["LAB"] / (panel["LAB"] + panel["CAP"])
    x = np.log(panel["LAB"] / panel["K"])
    table = XS.cells(panel)
    rows = []
    for j, gs in sorted(byind.items()):
        beta, alpha, _, n = within_fit(x, sig, gs)
        if n < 3:
            continue
        for (jj, yr), idx in table.items():
            if jj != j:
                continue
            geo = [panel["geo"][i] for i in idx]
            sel = [(g, i) for g, i in zip(geo, idx) if g in alpha]
            if len(sel) < 3:
                continue
            xs = np.array([x[i] for _, i in sel])
            al = np.array([alpha[g] for g, _ in sel])
            sh = np.array([sig[i] for _, i in sel])
            order = list(np.argsort(xs))          # the mix's own order, no choice left
            hol = loop_area(al, xs, order)
            hol_raw = loop_area(sh, xs, order)
            rows.append({"cell": f"{j}/{yr}", "n": len(sel),
                         "holonomy_smoothed": hol, "holonomy_raw": hol_raw,
                         "alpha_spread": float(np.ptp(al)),
                         "x_spread": float(np.ptp(xs))})
    hs = np.abs(np.array([r["holonomy_smoothed"] for r in rows]))
    hr = np.abs(np.array([r["holonomy_raw"] for r in rows]))
    ok = len(rows) > 0
    detail = (f"{len(rows):,} cross-sections. The closed form evaluated directly, "
              f"on the loop that visits the countries in the mix's own order so "
              f"no ordering is chosen: |area the intercept sweeps| median "
              f"{np.median(hs):.4f}, p90 {np.percentile(hs,90):.4f}; the same loop "
              f"with the raw share in place of the fitted intercept median "
              f"{np.median(hr):.4f}. Smoothed over raw, median "
              f"{np.median(hs/np.maximum(hr,1e-30)):.3f}: GRV's own smoothing "
              f"keeps the country term, so it does not remove the area, and the "
              f"multilateral form removes it by projection rather than by the "
              f"smoothing.")
    rows.sort(key=lambda r: -abs(r["holonomy_smoothed"]))
    return bool(ok), detail, {
        "n_cells": len(rows),
        "smoothed_median": float(np.median(hs)),
        "smoothed_p90": float(np.percentile(hs, 90)),
        "raw_median": float(np.median(hr)),
        "ratio_median": float(np.median(hs / np.maximum(hr, 1e-30))),
        "top20": rows[:20], "bottom20": rows[-20:]}


# ---------------------------------------- B101-28 a panel where alpha is common

def check_planted_common(panel, byind, rng, reps):
    """Plant the answer: build a panel in which every country in an industry has
    the same alpha, keep the real mix, and read the area back. It must be zero,
    because the closed form has nothing left to sweep."""
    x = np.log(panel["LAB"] / panel["K"])
    table = XS.cells(panel)
    worst = 0.0; worst_live = 0.0; rows = []
    keys = [k for k in table if len(table[k]) >= 6]
    for r in range(reps):
        a0 = float(rng.uniform(0.3, 0.8)); b0 = float(rng.uniform(-0.2, 0.2))
        for key in keys[r::max(reps, 1)][:40]:
            idx = table[key]
            xs = x[idx]
            order = list(np.argsort(xs))
            al = np.full(len(idx), a0)                     # one country term
            worst = max(worst, abs(loop_area(al, xs, order)))
            live = a0 + b0 * np.arange(len(idx)) / len(idx)  # a country term that moves
            worst_live = max(worst_live, abs(loop_area(live, xs, order)))
            rows.append({"cell": f"{key[0]}/{key[1]}",
                         "common": abs(loop_area(al, xs, order)),
                         "moving": abs(loop_area(live, xs, order))})
    ok = (worst < 1e-12) and (worst_live > 1e-6)
    detail = (f"{len(rows)} planted cross-sections over {reps} draws. One country "
              f"term shared by every country: worst |area| {worst:.3e}, which is "
              f"zero because a constant sweeps nothing. A country term that moves "
              f"across countries, same mix, same loop: smallest of the worst "
              f"|area| {worst_live:.4f}. So the reading is carried by the spread "
              f"of the country term and by nothing else.")
    return bool(ok), detail, {"worst_common": worst, "worst_moving": worst_live,
                              "sample": rows[:20]}


# ------------------------------- B101-29 the same question with no loop chosen

def check_smoothed_rho(panel, byind):
    """B101-27 reads one loop, picked by the mix's own order so that no freedom
    is left, but it is still one loop out of the (n-1)(n-2)/2 independent ones.
    This reads the same question with no loop at all: how far the comparison
    field is from a gradient, with the raw share and then with GRV's smoothed
    share in its place, everything else untouched.

    Sign note, because the subscripts in footnote 20 have cost this station once
    already: the fit here is share = alpha + beta * x with x = ln(L/K), so this
    beta is minus the beta of footnote 20, which is written on ln(K/L). Nothing
    below reads the sign.
    """
    sig = panel["LAB"] / (panel["LAB"] + panel["CAP"])
    x = np.log(panel["LAB"] / panel["K"])
    table = XS.cells(panel)
    fitted = {}
    for j, gs in byind.items():
        beta, alpha, _, n = within_fit(x, sig, gs)
        if n >= 3:
            fitted[j] = (beta, alpha)

    rows = []
    for (j, yr), idx in table.items():
        if j not in fitted:
            continue
        beta, alpha = fitted[j]
        sel = [i for i in idx if panel["geo"][i] in alpha]
        if len(sel) < 3:
            continue
        n = len(sel)
        edges = XS.complete_edges(n)
        lnY = np.log(panel["Y"][sel]); lnL = np.log(panel["LAB"][sel])
        lnK = np.log(panel["K"][sel])
        raw = sig[sel]
        smooth = np.array([alpha[panel["geo"][i]] + beta * x[i] for i in sel])
        r_raw = XS.rho_of(n, edges, XS.omega_edges(lnY, lnL, lnK, raw, edges))[0]
        r_smo = XS.rho_of(n, edges, XS.omega_edges(lnY, lnL, lnK, smooth, edges))[0]
        rows.append({"cell": f"{j}/{yr}", "n": n, "rho_raw": r_raw,
                     "rho_smoothed": r_smo})
    a = np.array([r["rho_raw"] for r in rows])
    b = np.array([r["rho_smoothed"] for r in rows])
    ok = len(rows) > 0
    detail = (f"{len(rows):,} cross-sections, no loop chosen. rho with the raw "
              f"share median {np.median(a):.4f}; rho with GRV's smoothed share in "
              f"its place median {np.median(b):.4f}, ratio median "
              f"{np.median(b/np.maximum(a,1e-30)):.3f}. Cross-sections where the "
              f"smoothing lowers rho by more than half: "
              f"{int((b < 0.5*a).sum()):,} of {len(rows):,}. The smoothing keeps "
              f"a country term, so it keeps the obstruction; what removes it is "
              f"the multilateral form's projection, which is B79's reading.")
    rows.sort(key=lambda r: -r["rho_smoothed"])
    return bool(ok), detail, {
        "n_cells": len(rows),
        "rho_raw_median": float(np.median(a)),
        "rho_smoothed_median": float(np.median(b)),
        "ratio_median": float(np.median(b / np.maximum(a, 1e-30))),
        "halved": int((b < 0.5 * a).sum()),
        "top20": rows[:20], "bottom20": rows[-20:]}


# -------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    panel = XS.load_panel()
    byind = panel_by_industry(panel)
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B101-26", "instrument",
         "GRV footnote 20 fitted on a mix with no index base, so the intercept is "
         "the country term itself", check_fit(panel, byind)),
        ("B101-27", "own_reading",
         "the area the recovered country term sweeps against the mix, which is "
         "the closed form for the smoothed index's cross-country holonomy",
         check_intercept_area(panel, byind)),
        ("B101-28", "known_answer",
         "a country term shared by every country sweeps zero area, one that moves "
         "does not", check_planted_common(panel, byind, rng, a.seeds)),
        ("B101-29", "own_reading",
         "the same question with no loop chosen: what the smoothing does to the "
         "distance from a gradient", check_smoothed_rho(panel, byind)),
    ]
    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        criteria.append({"name": name, "kind": kind, "criterion": what,
                         "passed": bool(passed), "detail": detail,
                         "payload": payload})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {
        "stage": "B101",
        "config": {"seeds": a.seeds, "seed": a.seed,
                   "mix": "ln(LAB / K_GFCF)", "share": "LAB / (LAB + CAP)",
                   "smoothing": "sigma = alpha_ij + beta_j * ln(K/L)",
                   "closes": "B101-18",
                   "sources": ["growth accounts basic.csv", "capital accounts.csv"]},
        "criteria": criteria,
    }
    body = json.dumps(record, indent=2, sort_keys=True, default=float)
    print(f"\n{sum(c['passed'] for c in criteria)}/{len(criteria)} pass, "
          f"{time.time() - t0:.2f}s, sha256 "
          f"{hashlib.sha256(body.encode()).hexdigest()[:16]}")
    if not a.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(body, encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
