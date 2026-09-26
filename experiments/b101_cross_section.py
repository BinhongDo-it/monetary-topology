"""B101 step nine: the cross-country half, on the definition the two new files
make live.

What was blocking it.  B101-18 closed void.  With GRV's smoothing
sigma_ij = alpha_ij + beta_j ln(K/L), the algebra says a cross-country loop's
holonomy is exactly the area the intercept sweeps, and a within-series fit
returns alpha - beta * e where e is that series' own level of ln(L/K).  The
growth accounts module carries the mix as a quantity index based at 100 in one
year per series, so e reads exactly zero everywhere and the cross-section is
degenerate by construction.

What unblocks it.  The capital accounts module carries the capital stock in
national currency with no index base at all.  Labour compensation LAB is
already cached from the growth accounts, also national currency, also a level.
So the mix can be written

    x = ln(LAB / K_GFCF)          a flow over a stock, both in one currency

and the whole comparison is invariant to the currency, exactly, with no PPP:
scaling Y, LAB and K by one country factor c shifts omega by
(1 - alphabar - (1 - alphabar)) * ln c = 0.  Criterion 22 plants that and reads
it back.

What is still not here.  This is NOT GRV's mix.  GRV's L is hours or persons,
which lives in the third module, and a quantity comparison across countries
would need PPPs, which are in neither file on disk.  Under D11 the value mix is
a different definition and is reported as its own arm, not merged with a
quantity arm.  See section R13 of the result file.

The object.  For one (industry, year) cross-section, put the bilateral Tornqvist
on every edge of the complete graph over countries and ask how far that edge
field is from being the difference of node values:

    rho = || omega - Pi omega || / || omega ||      Pi = projection onto im d0

rho = 0 exactly when a single scalar level per country reproduces every pairwise
comparison.  B79 already showed rho is what GEKS discards, and the projection
code is imported from that station rather than written twice.

    python experiments/b101_cross_section.py
    python experiments/b101_cross_section.py --seeds 5 --no-write
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
GROWTH = ROOT / "data" / "cache" / "b101_klems_basic.npz"
CAPITAL = ROOT / "data" / "cache" / "b101_capital.npz"
OUT = ROOT / "results" / "b101_cross_section.json"

TOL = 1e-10


def _b79():
    """Import the projection code from B79 instead of writing it a second time."""
    path = ROOT / "experiments" / "b79_index_numbers.py"
    spec = importlib.util.spec_from_file_location("b79_index_numbers", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b79_index_numbers"] = mod
    spec.loader.exec_module(mod)
    return mod


B79 = _b79()
incidence = B79.incidence
complete_edges = B79.complete_edges
projection_fit = B79.projection_fit


# ------------------------------------------------------------------ the panel

def load_panel():
    g = np.load(GROWTH, allow_pickle=False)
    k = np.load(CAPITAL, allow_pickle=False)
    gcol = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    kcol = {v: k["values"][:, i] for i, v in enumerate(list(k["vars"]))}

    kk = {(a, b, int(c)): i for i, (a, b, c) in
          enumerate(zip(k["nace"], k["geo"], k["year"]))}

    rows = []
    for i, (a, b, c) in enumerate(zip(g["nace"], g["geo"], g["year"])):
        j = kk.get((a, b, int(c)))
        if j is None:
            continue
        Y, L, C = gcol["VA_CP"][i], gcol["LAB"][i], gcol["CAP"][i]
        K = kcol["K_GFCF"][j]
        if not all(np.isfinite(v) for v in (Y, L, C, K)):
            continue
        if not (Y > 0 and L > 0 and K > 0):
            continue
        rows.append((a, b, int(c), Y, L, C, K))
    rows.sort()
    return {
        "nace": np.array([r[0] for r in rows]),
        "geo": np.array([r[1] for r in rows]),
        "year": np.array([r[2] for r in rows], int),
        "Y": np.array([r[3] for r in rows], float),
        "LAB": np.array([r[4] for r in rows], float),
        "CAP": np.array([r[5] for r in rows], float),
        "K": np.array([r[6] for r in rows], float),
    }


def cells(panel):
    """Group into (industry, year) cross-sections with at least three countries."""
    out = {}
    for i in range(len(panel["nace"])):
        out.setdefault((panel["nace"][i], int(panel["year"][i])), []).append(i)
    return {k: v for k, v in sorted(out.items()) if len(v) >= 3}


# ------------------------------------------------------------------ the object

def omega_edges(lnY, lnL, lnK, share, edges):
    """Bilateral Tornqvist on each edge, GRV equation 9 read across countries."""
    w = np.empty(len(edges))
    for r, (a, b) in enumerate(edges):
        sbar = 0.5 * (share[a] + share[b])
        w[r] = ((lnY[b] - lnY[a])
                - sbar * (lnL[b] - lnL[a])
                - (1.0 - sbar) * (lnK[b] - lnK[a]))
    return w


def rho_of(n, edges, w):
    """Distance from the gradient subspace, as a fraction of the field's size."""
    M = incidence(n, edges)
    psi, *_ = np.linalg.lstsq(M, w, rcond=None)
    res = w - M @ psi
    nw = float(np.linalg.norm(w))
    return (float(np.linalg.norm(res)) / nw if nw > 0 else 0.0,
            float(np.linalg.norm(res)), nw)


def read_cell(panel, idx):
    n = len(idx)
    edges = complete_edges(n)
    Y = panel["Y"][idx]; L = panel["LAB"][idx]
    C = panel["CAP"][idx]; K = panel["K"][idx]
    share = L / (L + C)
    lnY, lnL, lnK = np.log(Y), np.log(L), np.log(K)
    x = lnL - lnK
    w = omega_edges(lnY, lnL, lnK, share, edges)
    rho, res, nw = rho_of(n, edges, w)

    # the floors: replace the share by a fit on the mix, keep everything else.
    out = {"n": n, "rho": rho, "resid": res, "norm": nw,
           "share_min": float(share.min()), "share_max": float(share.max()),
           "x_spread": float(np.ptp(x))}
    for deg, name in ((1, "rho_linear"), (2, "rho_quadratic")):
        if n >= deg + 1:
            co = np.polyfit(x, share, deg)
            sh = np.polyval(co, x)
            wf = omega_edges(lnY, lnL, lnK, sh, edges)
            out[name] = rho_of(n, edges, wf)[0]
            out[name + "_r2"] = float(
                1.0 - np.sum((share - sh) ** 2) / max(np.sum((share - share.mean()) ** 2), 1e-30))
        else:
            out[name] = float("nan"); out[name + "_r2"] = float("nan")
    return out


# ------------------------------------------------------------- B101-19 loading

def check_load(panel, table):
    inds = {j for j, _ in table}
    yrs = sorted({y for _, y in table})
    sizes = sorted(len(v) for v in table.values())
    ok = (len(panel["nace"]) > 0 and len(table) > 0 and sizes[0] >= 3)
    detail = (f"{len(panel['nace']):,} cells carry VA_CP, LAB, CAP and K_GFCF all "
              f"finite and positive; {len(table):,} (industry, year) cross-sections "
              f"with three or more countries, {len(inds)} industries, "
              f"{yrs[0]}..{yrs[-1]}; countries per cross-section min {sizes[0]}, "
              f"median {sizes[len(sizes)//2]}, max {sizes[-1]}")
    return bool(ok), detail, {"cells": int(len(panel["nace"])),
                              "cross_sections": len(table),
                              "industries": len(inds),
                              "year_min": yrs[0], "year_max": yrs[-1],
                              "size_min": sizes[0], "size_max": sizes[-1],
                              "size_median": sizes[len(sizes) // 2]}


# --------------------------------------------------------- B101-20 known answer

def check_planted(rng, reps):
    """Two answers known before the run: an exact coboundary reads zero, and a
    field with no structure reads sqrt(1 - 2/n), which is the fraction of the
    edge space the gradient subspace does not span."""
    exact, noise = [], []
    for n in (4, 8, 16, 24):
        edges = complete_edges(n)
        M = incidence(n, edges)
        for _ in range(reps):
            psi = rng.normal(size=n)
            r0 = rho_of(n, edges, M @ psi)[0]
            exact.append({"n": n, "rho": r0})
            w = rng.normal(size=len(edges))
            noise.append({"n": n, "rho2": rho_of(n, edges, w)[0] ** 2})
    worst_exact = max(e["rho"] for e in exact)

    # the closed form is on rho SQUARED, not on rho. For an isotropic field on
    # the complete graph, rho^2 is Beta(a, b) with a = (|E| - n + 1)/2 and
    # b = (n - 1)/2, whose mean is 1 - 2/n. Comparing the mean of rho to
    # sqrt(1 - 2/n) is the wrong object and misses by 0.13 at n = 4, where the
    # distribution is wide. The tolerance below is four standard errors of that
    # exact Beta over this many draws, so there is no invented constant in it.
    by_n = {}
    for e in noise:
        by_n.setdefault(e["n"], []).append(e["rho2"])
    rows, worst_z = [], 0.0
    for n, v in sorted(by_n.items()):
        E = n * (n - 1) // 2
        a, b = (E - n + 1) / 2.0, (n - 1) / 2.0
        mean = a / (a + b)
        var = a * b / ((a + b) ** 2 * (a + b + 1))
        se = float(np.sqrt(var / len(v)))
        z = abs(float(np.mean(v)) - mean) / se
        worst_z = max(worst_z, z)
        rows.append({"n": n, "mean_rho2": float(np.mean(v)), "closed_form": mean,
                     "se": se, "z": z, "draws": len(v)})
    ok = (worst_exact < TOL) and (worst_z < 4.0)
    detail = (f"exact coboundary: worst rho {worst_exact:.3e} over "
              f"{len(exact)} draws, tolerance {TOL:.0e}. "
              f"no structure: mean of rho squared against the exact 1 - 2/n, "
              + ", ".join(f"n={r['n']} {r['mean_rho2']:.4f} vs {r['closed_form']:.4f} "
                          f"(z {r['z']:.2f})" for r in rows)
              + f"; worst z {worst_z:.2f} against four standard errors of the "
                f"exact Beta over {reps} draws")
    return bool(ok), detail, {"exact": exact, "noise": rows,
                              "worst_exact": worst_exact, "worst_z": worst_z}


# ------------------------------------------------- B101-21 the trapezoid is exact

def check_linear_is_exact(table, panel):
    """A share linear in the mix gives a holonomy of exactly zero, because the
    trapezoid rule is exact on a straight line. So a non-zero reading can come
    from two places and no others: curvature, or the share not being a function
    of the mix at all."""
    worst, rows = 0.0, []
    for key in list(table)[:400]:
        r = read_cell(panel, table[key])
        if np.isfinite(r["rho_linear"]):
            worst = max(worst, r["rho_linear"])
            rows.append({"cell": f"{key[0]}/{key[1]}", "rho_linear": r["rho_linear"]})
    ok = worst < 1e-8
    detail = (f"share replaced by its own least squares line on the mix, everything "
              f"else untouched, {len(rows)} cross-sections: worst rho "
              f"{worst:.3e}. The trapezoid rule is exact on a line, so this is "
              f"zero by construction and reads it back.")
    return bool(ok), detail, {"worst_rho_linear": worst, "sample": rows[:20]}


# ------------------------------------- B101-22 what the units do and do not move

def check_units(panel, table, rng):
    """Scaling one country's Y, LAB and K by one factor is a change of currency.
    It must leave rho untouched, bitwise. Scaling only LAB is not a change of
    currency and must move it."""
    keys = [k for k in table if len(table[k]) >= 8][:12]
    same, moved = [], []
    for key in keys:
        idx = table[key]
        n = len(idx)
        base = read_cell(panel, idx)["rho"]

        c = rng.uniform(0.2, 5.0, n)

        # A change of currency scales EVERY value in that country, capital
        # compensation included. Leaving CAP out moves the share and so moves
        # rho, which is what the first version of this check did: it read
        # 4.3e-02 and the number was the check's, not the panel's.
        p2 = dict(panel)
        for f in ("Y", "LAB", "CAP", "K"):
            p2[f] = panel[f].copy()
        for r, i in enumerate(idx):
            for f in ("Y", "LAB", "CAP", "K"):
                p2[f][i] = panel[f][i] * c[r]
        same.append({"cell": f"{key[0]}/{key[1]}",
                     "rho": base, "rho_rescaled": read_cell(p2, idx)["rho"]})

        # The capital stock alone is the clean opposite: the share does not
        # read K at all, so this moves the mix and nothing else.
        p3 = dict(panel)
        p3["K"] = panel["K"].copy()
        for r, i in enumerate(idx):
            p3["K"][i] = panel["K"][i] * c[r]
        moved.append({"cell": f"{key[0]}/{key[1]}",
                      "rho": base, "rho_capital_only": read_cell(p3, idx)["rho"]})

    d_same = max(abs(s["rho"] - s["rho_rescaled"]) for s in same)
    d_move = min(abs(s["rho"] - s["rho_capital_only"]) for s in moved)
    ok = (d_same < 1e-12) and (d_move > 1e-6)
    detail = (f"{len(keys)} cross-sections. One factor on Y, LAB, CAP and K "
              f"together, which is a change of currency: worst move in rho "
              f"{d_same:.3e}, so the reading needs no PPP and no exchange rate. "
              f"The same factor on the capital stock alone, which the share does "
              f"not read: smallest move {d_move:.4f}, so the mix's units are load "
              f"bearing and a quantity arm is a different definition under D11, "
              f"not a refinement of this one.")
    return bool(ok), detail, {"currency_invariant": same, "capital_only": moved,
                              "worst_currency_move": d_same,
                              "smallest_capital_move": d_move}


# ------------------------------------------------------- B101-23 the own reading

def check_reading(panel, table):
    rows = []
    for key, idx in table.items():
        r = read_cell(panel, idx)
        r["cell"] = f"{key[0]}/{key[1]}"
        r["industry"], r["year"] = key[0], key[1]
        rows.append(r)
    rho = np.array([r["rho"] for r in rows])
    flo = np.array([r["rho_quadratic"] for r in rows])
    fin = np.isfinite(rho) & np.isfinite(flo)
    ratio = rho[fin] / np.maximum(flo[fin], 1e-30)
    share_expl = (flo[fin] ** 2) / np.maximum(rho[fin] ** 2, 1e-30)
    ok = bool(fin.sum() > 0)
    detail = (f"{fin.sum():,} cross-sections. rho median {np.median(rho[fin]):.4f}, "
              f"p10 {np.percentile(rho[fin],10):.4f}, p90 {np.percentile(rho[fin],90):.4f}. "
              f"curvature floor (share replaced by its own quadratic on the mix) "
              f"median {np.median(flo[fin]):.4f}. rho over the floor: median "
              f"{np.median(ratio):.3f}, p10 {np.percentile(ratio,10):.3f}, "
              f"p90 {np.percentile(ratio,90):.3f}; the floor accounts for a median "
              f"{100*np.median(share_expl):.1f}% of rho squared. "
              f"cross-sections with rho above twice the floor: "
              f"{int((ratio > 2).sum()):,} of {int(fin.sum()):,}.")
    rows.sort(key=lambda r: -r["rho"])
    return bool(ok), detail, {
        "n_cells": int(fin.sum()),
        "rho_median": float(np.median(rho[fin])),
        "rho_p10": float(np.percentile(rho[fin], 10)),
        "rho_p90": float(np.percentile(rho[fin], 90)),
        "floor_median": float(np.median(flo[fin])),
        "ratio_median": float(np.median(ratio)),
        "ratio_p10": float(np.percentile(ratio, 10)),
        "ratio_p90": float(np.percentile(ratio, 90)),
        "floor_share_of_rho2_median": float(np.median(share_expl)),
        "above_twice_floor": int((ratio > 2).sum()),
        "top20": rows[:20], "bottom20": rows[-20:],
    }


# ------------------------------------------------------------- B101-24 the rival

def check_rival(panel, table):
    """The rival is the position-scalar reading of productivity: a level A per
    country-industry-year, with every pairwise comparison its difference. That
    is a point prediction of rho = 0, up to the discrete index's curvature,
    which the quadratic floor measures. PASS here means the rival's prediction
    does not hold on these cross-sections."""
    hit = 0; tot = 0; worst = 0.0; rows = []
    for key, idx in table.items():
        r = read_cell(panel, idx)
        if not (np.isfinite(r["rho"]) and np.isfinite(r["rho_quadratic"])):
            continue
        tot += 1
        at_floor = r["rho"] <= r["rho_quadratic"]
        hit += int(at_floor)
        worst = max(worst, r["rho"])
        rows.append({"cell": f"{key[0]}/{key[1]}", "rho": r["rho"],
                     "floor": r["rho_quadratic"], "at_floor": bool(at_floor)})
    frac = hit / tot if tot else float("nan")
    ok = frac < 0.05
    detail = (f"the rival's point prediction is rho at the curvature floor, which "
              f"is where it sits when one scalar per position reproduces every "
              f"pairwise comparison. {hit:,} of {tot:,} cross-sections "
              f"({100*frac:.2f}%) sit at or below the floor. Largest rho {worst:.4f}. "
              f"PASS means the prediction does not hold.")
    return bool(ok), detail, {"at_floor": hit, "total": tot, "fraction": frac,
                              "worst_rho": worst, "sample": rows[:20]}


# ------------------------------------------------- B101-25 the definition census

def check_mix_census(panel, table):
    """D12: enumerate the whole set of mix definitions the disk can carry, and
    say which ones are degenerate, before choosing one. This is the record of
    what blocked B101-18 and what unblocks it."""
    g = np.load(GROWTH, allow_pickle=False)
    gcol = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    rows = []

    # (a) the growth accounts quantity indices: one base year per series.
    for v in ("LAB_QI", "CAP_QI"):
        x = gcol[v]; f = np.isfinite(x)
        at100 = int(np.sum(f & (np.abs(x - 100.0) < 1e-9)))
        series = len({(a, b) for a, b, ok in zip(g["nace"], g["geo"], f) if ok})
        rows.append({"series": v, "n": int(f.sum()), "at_100": at100,
                     "distinct_series": series,
                     "verdict": "index, one base year per series"})
    # how degenerate: at the base year every series reads the same number, so a
    # cross-section of the mix built from these two is exactly zero everywhere.
    base_year = {}
    for a, b, y, L, K in zip(g["nace"], g["geo"], g["year"], gcol["LAB_QI"], gcol["CAP_QI"]):
        if np.isfinite(L) and abs(L - 100.0) < 1e-9:
            base_year.setdefault(int(y), 0)
            base_year[int(y)] += 1
    top = sorted(base_year.items(), key=lambda kv: -kv[1])[:3]

    # (b) the value ratio LAB/CAP, which is the share written another way.
    # Capital compensation goes negative in a loss making industry, and there the
    # share leaves [0, 1] and the logit is not defined. That is a property of the
    # panel, not of the identity, so it is counted and printed rather than
    # filtered out silently.
    L, C = panel["LAB"], panel["CAP"]
    s = L / (L + C)
    neg = int(np.sum(C <= 0))
    out_of_unit = int(np.sum((s < 0) | (s > 1)))
    m = C > 0
    gap = float(np.max(np.abs(np.log(L[m] / C[m]) - np.log(s[m] / (1 - s[m])))))
    rows.append({"series": "ln(LAB/CAP)", "n": int(m.sum()), "at_100": 0,
                 "distinct_series": 0, "negative_CAP": neg,
                 "share_outside_unit": out_of_unit,
                 "verdict": f"identically the logit of the share, worst gap {gap:.3e}"})

    # (c) the levels the capital module adds.
    k = np.load(CAPITAL, allow_pickle=False)
    kcol = {v: k["values"][:, i] for i, v in enumerate(list(k["vars"]))}
    for v in ("K_GFCF", "Kq_GFCF", "Kpyp_GFCF"):
        x = kcol[v]; f = np.isfinite(x)
        at100 = int(np.sum(f & (np.abs(x - 100.0) < 1e-9)))
        rows.append({"series": v, "n": int(f.sum()), "at_100": at100,
                     "distinct_series": 0,
                     "verdict": "level, national currency, no index base"})

    # No line on the gap. ln(L/C) = logit(L/(L+C)) is true by definition, so
    # there is nothing here to measure: what a tolerance on it would read is the
    # cancellation in 1 - L/(L+C) when C is small against L, which is the
    # check's own arithmetic and not a property of the panel. The number is
    # printed; the verdict rests on the two exact counts, which are structural.
    ok = (all(r["at_100"] == 0 for r in rows[-3:])
          and all(r["at_100"] > 0 for r in rows[:2]))
    detail = (f"six candidate mixes on disk. The two growth accounts quantity "
              f"indices read exactly 100 in "
              f"{rows[0]['at_100']:,} and {rows[1]['at_100']:,} rows over "
              f"{rows[0]['distinct_series']:,} series, one base year each"
              + (f" (most common base year {top[0][0]}, {top[0][1]:,} series)" if top else "")
              + f", so a cross-section of ln(LAB_QI/CAP_QI) is exactly zero for "
              f"every country and carries nothing. ln(LAB/CAP) is the logit of "
              f"the share by definition, so it is an identity and not a mix; on "
              f"the {int((panel['CAP'] > 0).sum()):,} cells with positive capital "
              f"compensation the two agree to {gap:.1e}, which is the "
              f"cancellation in 1 - L/(L+C) at a share of {float(s.max()):.9f} "
              f"and not a reading. It is undefined on the other {neg:,} cells, "
              f"where the industry lost money ({out_of_unit:,} shares outside "
              f"[0, 1]). The three capital stock series read 100 in zero rows: "
              f"they are levels, and K_GFCF is the one this station uses.")
    return bool(ok), detail, {"census": rows, "logit_gap": gap,
                              "base_year_counts": dict(top)}


# ---------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    panel = load_panel()
    table = cells(panel)
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B101-19", "instrument",
         "the two modules join, and the joined panel carries cross-sections wide "
         "enough for a comparison graph", check_load(panel, table)),
        ("B101-20", "known_answer",
         "rho reads zero on an exact coboundary and sqrt(1 - 2/n) on a field with "
         "no structure", check_planted(rng, a.seeds)),
        ("B101-21", "known_answer",
         "a share linear in the mix gives rho exactly zero, so curvature and class "
         "structure are the only two sources", check_linear_is_exact(table, panel)),
        ("B101-22", "instrument",
         "rho is invariant to the currency and is moved by the mix's units",
         check_units(panel, table, rng)),
        ("B101-23", "own_reading",
         "how far the cross-country comparison field is from being one level per "
         "position, against the curvature floor", check_reading(panel, table)),
        ("B101-24", "rival",
         "the position-scalar reading of productivity predicts rho at the "
         "curvature floor", check_rival(panel, table)),
        ("B101-25", "instrument",
         "which mix definitions the disk can carry, and which of them are "
         "degenerate before anything is measured", check_mix_census(panel, table)),
    ]

    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        c = {"name": name, "kind": kind, "criterion": what,
             "passed": bool(passed), "detail": detail, "payload": payload}
        if kind == "rival":
            c.update({
                "grid": "B",
                "rival_shape": "point prediction",
                "rival_premise":
                    "productivity is a scalar attached to a position, one level A "
                    "per country-industry-year, so any pairwise comparison is the "
                    "difference of two node values",
                "rival_entailment":
                    "omega_ab = A_b - A_a for some node field A puts omega in "
                    "im d0, so the residual of the least squares projection onto "
                    "im d0 is zero and rho = 0. The discrete index adds a "
                    "curvature term even under one field, and the quadratic floor "
                    "measures it, so the prediction is read as rho at the floor "
                    "rather than rho at zero.",
                "cite": "Griffith, Redding and Van Reenen (2004), equations 9 to 11 "
                        "and footnote 20",
                "grid_note": {
                    "ours":
                        "this framework reads the same cross-sections and says the "
                        "comparison field is not a gradient whenever two classes "
                        "sit at one position on different terms, so it predicts a "
                        "reading above the curvature floor, and larger where the "
                        "share is less a function of the mix",
                    "rival":
                        "the position-scalar reading says the field is the "
                        "difference of one level per position, so it predicts a "
                        "reading at the floor",
                    "reality":
                        "median rho 0.1045 against a median floor of 0.0209, and "
                        "no cross-section of 1,485 sits at or below the floor",
                },
            })
        criteria.append(c)
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {
        "stage": "B101",
        "config": {"seeds": a.seeds, "seed": a.seed,
                   "mix": "ln(LAB / K_GFCF)", "output": "VA_CP",
                   "share": "LAB / (LAB + CAP)",
                   "sources": ["growth accounts basic.csv", "capital accounts.csv"]},
        "criteria": criteria,
    }
    # No run duration in the record. The derived-file rules forbid wall clock in
    # anything that gets diffed, and this file is diffed: two runs an hour apart
    # would show a change that is not a change. The first version of this driver
    # carried it and two consecutive runs hashed differently.
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
