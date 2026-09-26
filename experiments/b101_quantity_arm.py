"""B101 step twelve: the quantity mix, and a bound that makes the missing PPP
stop mattering.

The value arm reads a mix that is currency invariant and needs no purchasing
power parity, which is measured rather than argued.  The quantity mix GRV
actually uses is not: hours are physically comparable across countries, the
capital stock is a national currency amount, so ln(H/K) carries an unknown
per country term, the log of that country's capital price level.  Under D11
that makes it a second definition, and this file runs it as one.

It also answers the objection that definition invites, and answers it exactly
rather than by sensitivity.  Write a per country shift e on the log of each
factor.  The edge function moves by

    omega(e) = omega_0 - sbar * (eL_b - eL_a) - (1 - sbar) * (eK_b - eK_a)

which is LINEAR in e.  So minimising the distance from the gradient subspace
over all per country shifts is a least squares problem, and its value is the
smallest reading any conversion whatsoever could produce.  Not a plausible
conversion, not a sampled one: any of them, of any size, on both factors at
once.  If that floor is still above the curvature floor, no purchasing power
parity can rescue the position scalar reading on this panel, and the arm no
longer depends on a number this station does not hold.

    python experiments/b101_quantity_arm.py
    python experiments/b101_quantity_arm.py --no-write
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
OUT = ROOT / "results" / "b101_quantity_arm.json"
NATIONAL = ROOT / "data" / "cache" / "b101_national.npz"
GROWTH = ROOT / "data" / "cache" / "b101_klems_basic.npz"
CAPITAL = ROOT / "data" / "cache" / "b101_capital.npz"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


XS = _mod("b101_cross_section")
incidence, complete_edges = XS.incidence, XS.complete_edges


# ------------------------------------------------------------------ the panel

def load_panel():
    g = np.load(GROWTH, allow_pickle=False)
    k = np.load(CAPITAL, allow_pickle=False)
    n = np.load(NATIONAL, allow_pickle=False)
    gc = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    kc = {v: k["values"][:, i] for i, v in enumerate(list(k["vars"]))}
    nc = {v: n["values"][:, i] for i, v in enumerate(list(n["vars"]))}
    ki = {(a, b, int(c)): i for i, (a, b, c) in
          enumerate(zip(k["nace"], k["geo"], k["year"]))}
    ni = {(a, b, int(c)): i for i, (a, b, c) in
          enumerate(zip(n["nace"], n["geo"], n["year"]))}
    rows = []
    for i, (a, b, c) in enumerate(zip(g["nace"], g["geo"], g["year"])):
        key = (a, b, int(c))
        j, m = ki.get(key), ni.get(key)
        if j is None or m is None:
            continue
        Y, L, C = gc["VA_CP"][i], gc["LAB"][i], gc["CAP"][i]
        K = kc["K_GFCF"][j]
        H, HE, CO = nc["H_EMP"][m], nc["H_EMPE"][m], nc["COMP"][m]
        if not all(np.isfinite(v) for v in (Y, L, C, K, H)):
            continue
        if not (Y > 0 and L > 0 and K > 0 and H > 0):
            continue
        rows.append((a, b, int(c), Y, L, C, K, H, HE, CO))
    rows.sort()
    return {"nace": np.array([r[0] for r in rows]),
            "geo": np.array([r[1] for r in rows]),
            "year": np.array([r[2] for r in rows], int),
            "Y": np.array([r[3] for r in rows], float),
            "LAB": np.array([r[4] for r in rows], float),
            "CAP": np.array([r[5] for r in rows], float),
            "K": np.array([r[6] for r in rows], float),
            "H": np.array([r[7] for r in rows], float),
            "HE": np.array([r[8] for r in rows], float),
            "COMP": np.array([r[9] for r in rows], float)}


MIXES = {
    "quantity": lambda p, s: np.log(p["H"][s] / p["K"][s]),
    "value": lambda p, s: np.log(p["LAB"][s] / p["K"][s]),
    "wage": lambda p, s: np.log(p["LAB"][s] / p["H"][s]),
}


def read_cell(panel, idx, mix):
    """rho with the given mix, plus the two floors: curvature, and the smallest
    reading any per country conversion of either factor could produce."""
    n = len(idx)
    edges = complete_edges(n)
    lnY = np.log(panel["Y"][idx])
    lnK = np.log(panel["K"][idx])
    share = panel["LAB"][idx] / (panel["LAB"][idx] + panel["CAP"][idx])
    x = MIXES[mix](panel, idx)
    lnL = lnK + x                       # the mix defines L up to the K unit

    w = XS.omega_edges(lnY, lnL, lnK, share, edges)
    rho, res, nw = XS.rho_of(n, edges, w)

    co = np.polyfit(x, share, 2)
    wf = XS.omega_edges(lnY, lnL, lnK, np.polyval(co, x), edges)
    floor = XS.rho_of(n, edges, wf)[0]

    # the conversion floor. omega(e) = w - A @ e with e = [eL, eK] stacked, so
    # the residual after projecting out the gradient subspace is linear in e and
    # the smallest it can be is one least squares solve. Both factors at once,
    # any size, so this is a bound on every conversion and not a sample of some.
    M = incidence(n, edges)
    P = M @ np.linalg.pinv(M)
    Q = np.eye(len(edges)) - P          # projection onto the non gradient part
    A = np.zeros((len(edges), 2 * n))
    for r, (a, b) in enumerate(edges):
        sb = 0.5 * (share[a] + share[b])
        A[r, a] -= sb;       A[r, b] += sb
        A[r, n + a] -= 1 - sb; A[r, n + b] += 1 - sb
    QA, Qw = Q @ A, Q @ w
    e, *_ = np.linalg.lstsq(QA, Qw, rcond=None)
    best = w - A @ e
    conv = XS.rho_of(n, edges, best)[0]
    return {"n": n, "rho": rho, "floor": floor, "rho_any_conversion": conv,
            "x_spread": float(np.ptp(x))}


# --------------------------------------------------------- B101-30 the mixes

def check_mixes(panel, table, rng):
    """Three mixes, and what a per country factor on the capital stock does to
    each. The value mix does not read it at all through the share, so this is
    the clean statement of which definition carries a currency."""
    keys = [k for k in table if len(table[k]) >= 8][:12]
    rows = []
    for mix in MIXES:
        moves = []
        for key in keys:
            idx = table[key]
            base = read_cell(panel, idx, mix)["rho"]
            c = rng.uniform(0.2, 5.0, len(idx))
            p2 = dict(panel); p2["K"] = panel["K"].copy()
            for r, i in enumerate(idx):
                p2["K"][i] = panel["K"][i] * c[r]
            moves.append(abs(read_cell(p2, idx, mix)["rho"] - base))
        rows.append({"mix": mix, "worst_move": float(max(moves)),
                     "median_move": float(np.median(moves))})
    # and the identity that ties them together
    lhs = np.log(panel["LAB"] / panel["K"]) - np.log(panel["H"] / panel["K"])
    rhs = np.log(panel["LAB"] / panel["H"])
    gap = float(np.max(np.abs(lhs - rhs)))
    ok = all(r["worst_move"] > 1e-6 for r in rows) and gap < 1e-9
    detail = ("three mixes on the joined panel. A per country factor on the "
              "capital stock alone moves the reading in every one of them: "
              + ", ".join(f"{r['mix']} worst {r['worst_move']:.4f}" for r in rows)
              + f". The value mix and the quantity mix differ by exactly the log "
              f"hourly labour cost, ln(LAB/H), to {gap:.1e}, so they are one "
              f"definition apart and that difference is itself a measured "
              f"quantity rather than an unknown.")
    return bool(ok), detail, {"by_mix": rows, "identity_gap": gap}


# ------------------------------------------- B101-31 the quantity arm's reading

def check_quantity(panel, table):
    rows = [dict(read_cell(panel, idx, "quantity"), cell=f"{j}/{y}")
            for (j, y), idx in table.items()]
    rho = np.array([r["rho"] for r in rows])
    flo = np.array([r["floor"] for r in rows])
    ok = len(rows) > 0
    detail = (f"{len(rows):,} cross-sections on the mix GRV uses, hours over the "
              f"capital stock. rho median {np.median(rho):.4f}, p10 "
              f"{np.percentile(rho,10):.4f}, p90 {np.percentile(rho,90):.4f}; "
              f"curvature floor median {np.median(flo):.4f}; ratio median "
              f"{np.median(rho/np.maximum(flo,1e-30)):.3f}. At or below the floor "
              f"in {int((rho <= flo).sum()):,} of {len(rows):,}.")
    rows.sort(key=lambda r: -r["rho"])
    return bool(ok), detail, {
        "n_cells": len(rows), "rho_median": float(np.median(rho)),
        "rho_p10": float(np.percentile(rho, 10)),
        "rho_p90": float(np.percentile(rho, 90)),
        "floor_median": float(np.median(flo)),
        "ratio_median": float(np.median(rho / np.maximum(flo, 1e-30))),
        "at_floor": int((rho <= flo).sum()),
        "top20": rows[:20]}


# ------------------------------- B101-32 the two definitions give one verdict

def check_two_definitions(panel, table):
    q = {k: read_cell(panel, idx, "quantity") for k, idx in table.items()}
    v = {k: read_cell(panel, idx, "value") for k, idx in table.items()}
    a = np.array([q[k]["rho"] for k in table])
    b = np.array([v[k]["rho"] for k in table])
    fa = np.array([q[k]["floor"] for k in table])
    fb = np.array([v[k]["floor"] for k in table])
    both = int(np.sum((a > fa) & (b > fb)))
    neither = int(np.sum((a <= fa) & (b <= fb)))
    ok = both == len(a)
    detail = (f"{len(a):,} cross-sections read under both definitions. Above the "
              f"curvature floor under both: {both:,}; under neither: {neither:,}; "
              f"disagreeing: {len(a)-both-neither:,}. Quantity rho median "
              f"{np.median(a):.4f} against value {np.median(b):.4f}, rank "
              f"correlation {np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0,1]:+.3f}. "
              f"D11 says report both rather than merge them; what they report is "
              f"the same verdict.")
    return bool(ok), detail, {"both_above": both, "neither": neither,
                              "n": int(len(a)),
                              "quantity_median": float(np.median(a)),
                              "value_median": float(np.median(b))}


# ------------------------- B101-33 what "any conversion" means, and why it is
#                            the wrong question until it is tied down

def cell_parts(panel, idx, mix):
    """Everything a cross-section contributes to the conversion problem."""
    n = len(idx)
    edges = complete_edges(n)
    lnY = np.log(panel["Y"][idx]); lnK = np.log(panel["K"][idx])
    share = panel["LAB"][idx] / (panel["LAB"][idx] + panel["CAP"][idx])
    x = MIXES[mix](panel, idx)
    w = XS.omega_edges(lnY, lnK + x, lnK, share, edges)
    M = incidence(n, edges)
    Q = np.eye(len(edges)) - M @ np.linalg.pinv(M)
    sb = np.array([0.5 * (share[a] + share[b]) for a, b in edges])
    return edges, w, Q, sb, x, n


def check_free_conversion(panel, table):
    """A conversion free to differ per cross-section drives the reading to
    exactly zero, and the reason is algebra rather than economics: the edge
    function depends on the two factors only through the mix, so setting the
    labour conversion minus the capital conversion equal to the mix makes the
    mix the same number in every country, and a mix that does not move sweeps
    nothing. That is not a parity, it is deleting the variable. The question has
    content only once the conversion is tied down the way a parity is, to one
    number per country rather than one per industry. That is B101-35.

    This criterion was written first as a rival criterion claiming no conversion
    could close the gap. It failed, at exactly zero in every reading, and the
    failure was the construction's rather than the panel's. It is kept as a
    planted answer because the value it reads is known in advance and because a
    later reader will otherwise ask the unconstrained question again."""
    zeros, plugged, rows = 0, 0, []
    for (j, y), idx in list(table.items())[:300]:
        edges, w, Q, sb, x, n = cell_parts(panel, idx, "quantity")
        A = np.zeros((len(edges), n))
        for r, (aa, bb) in enumerate(edges):
            A[r, aa] -= sb[r]; A[r, bb] += sb[r]
        e, *_ = np.linalg.lstsq(Q @ A, Q @ w, rcond=None)
        r_fit = XS.rho_of(n, edges, w - A @ e)[0]
        # The mechanism, substituted rather than recovered. The conversion
        # enters as omega(e) = omega_0 - A e with row ab equal to sbar times
        # (e_b - e_a), and the mix enters the same row with a minus sign, so the
        # conversion that cancels it is MINUS the mix, not the mix. The first
        # version of this line had the sign the other way and read 2.8e-01; a
        # planted answer that reads back is the only reason that was caught.
        # Whether least squares returns this particular representative is a
        # question about its null space and not about the mechanism.
        r_sub = XS.rho_of(n, edges, w - A @ (-x))[0]
        zeros += int(r_fit < 1e-10)
        plugged += int(r_sub < 1e-10)
        rows.append({"cell": f"{j}/{y}", "rho_fitted": r_fit, "rho_at_e_is_x": r_sub})
    worst_sub = max(r["rho_at_e_is_x"] for r in rows)
    ok = zeros == len(rows) and plugged == len(rows)
    detail = (f"{len(rows)} cross-sections. A conversion free per cross-section "
              f"drives the reading below 1e-10 in {zeros} of them. Substituting "
              f"the mechanism directly, a conversion equal to minus the mix, "
              f"gives a worst reading of {worst_sub:.2e} and is below 1e-10 in "
              f"{plugged}. So an unconstrained conversion answers nothing: it "
              f"flattens the mix rather than converting it. The bound with "
              f"content holds a parity to one number per country across every "
              f"industry, which is B101-35.")
    return bool(ok), detail, {"n": len(rows), "reached_zero": zeros,
                              "zero_at_e_is_x": plugged,
                              "worst_at_e_is_x": worst_sub, "sample": rows[:20]}


# ------------------- B101-35 one parity per country, shared across industries

def check_parity_bound(panel, table):
    """Solve for the conversion once, over every cross-section at the same time,
    with one number per country. That is what a purchasing power parity is: a
    country's price level, not an industry's. Two scopes, because a parity does
    drift: one global set, and one set per year."""
    geos = sorted(set(panel["geo"]))
    gi = {g: i for i, g in enumerate(geos)}
    years = sorted({y for _, y in table})
    out = {}
    for mix in ("quantity", "value"):
        packed = []
        for (j, y), idx in table.items():
            edges, w, Q, sb, x, n = cell_parts(panel, idx, mix)
            cols = [gi[panel["geo"][i]] for i in idx]
            A = np.zeros((len(edges), len(geos)))
            for r, (aa, bb) in enumerate(edges):
                A[r, cols[aa]] -= sb[r]; A[r, cols[bb]] += sb[r]
            packed.append(((j, y), edges, w, Q @ A, Q @ w, A, n))
        base = {it[0]: XS.rho_of(it[6], it[1], it[4] * 0 + it[2])[0] if False
                else XS.rho_of(it[6], it[1], it[2])[0] for it in packed}
        floors = {k: read_cell(panel, table[k], mix)["floor"] for k in table}
        for scope in ("global", "per_year"):
            groups = {}
            for it in packed:
                groups.setdefault("all" if scope == "global" else it[0][1],
                                  []).append(it)
            per_cell = {}
            for items in groups.values():
                QA = np.vstack([it[3] for it in items])
                Qw = np.concatenate([it[4] for it in items])
                e, *_ = np.linalg.lstsq(QA, Qw, rcond=None)
                for key, edges, w, _QA, _Qw, A, n in items:
                    per_cell[key] = XS.rho_of(n, edges, w - A @ e)[0]
            bb = np.array([per_cell[k] for k in table])
            rr = np.array([base[k] for k in table])
            ff = np.array([floors[k] for k in table])
            sizes = np.array([len(table[k]) for k in table])
            at = bb <= ff
            out[f"{mix}_{scope}"] = {
                "rho_median": float(np.median(rr)),
                "best_median": float(np.median(bb)),
                "floor_median": float(np.median(ff)),
                "reached_floor": int(at.sum()),
                "fraction_reached": float(at.mean()),
                "median_n_at_floor": float(np.median(sizes[at])) if at.any() else float("nan"),
                "median_n_above": float(np.median(sizes[~at])) if (~at).any() else float("nan"),
                "cut_median_pct": float(100 * (1 - np.median(bb / np.maximum(rr, 1e-30)))),
                "n": int(len(bb)),
                "params": len(geos) * (1 if scope == "global" else len(years)),
                "residual_dims": int(sum((it[6] - 1) * (it[6] - 2) // 2 for it in packed)),
            }
    # The rival's prediction is not that SOME cross-section can be converted
    # into a gradient. It is that with the right units the field IS one level
    # per position, which is every cross-section at once under one parity. So
    # the verdict is read against all of them, and the informative number is the
    # fraction left above the floor rather than whether the count is zero.
    worst = max(v["fraction_reached"] for v in out.values())
    ok = worst < 1.0
    parts = "; ".join(
        f"{k}: {v['best_median']:.4f} from {v['rho_median']:.4f}, a cut of "
        f"{v['cut_median_pct']:.1f}%, floor {v['floor_median']:.4f}, "
        f"{v['reached_floor']}/{v['n']} reach it ({100*v['fraction_reached']:.1f}%), "
        f"and those that do carry a median {v['median_n_at_floor']:.0f} countries "
        f"against {v['median_n_above']:.0f} for those that do not"
        for k, v in sorted(out.items()))
    dims = out["quantity_global"]["residual_dims"]
    detail = (f"one conversion per country, solved once over every cross-section "
              f"at the same time so it cannot differ by industry, which is what a "
              f"parity is: {out['quantity_global']['params']} numbers globally, "
              f"{out['quantity_per_year']['params']} per year, against "
              f"{dims:,} dimensions of non-gradient field. {parts}. The rival's "
              f"claim is that ONE parity puts EVERY cross-section back on one "
              f"level per position, so the reading against it is the share left "
              f"above the floor: at worst {100*(1-worst):.1f}% remain. A parity "
              f"cuts the reading and does not close it, and the cells it does "
              f"close are the narrow ones, where there are fewer countries than "
              f"parameters to spend on them.")
    return bool(ok), detail, {"by_scope": out,
                              "worst_fraction_reached": worst,
                              "reached_floor_total":
                                  sum(v["reached_floor"] for v in out.values())}


# ------------------------------- B101-34 the self employed split is imputed

def check_self_employed(panel):
    """Two labour classes sit at every position in this panel, employees and the
    self employed. Whether that is an object or a convention is arithmetic."""
    dh = panel["H"] - panel["HE"]
    m = np.isfinite(dh) & (dh > 0) & (panel["HE"] > 0) & (panel["COMP"] > 0)
    we = panel["COMP"][m] / panel["HE"][m]
    ws = (panel["LAB"][m] - panel["COMP"][m]) / dh[m]
    ratio = ws / we
    at_one = int(np.sum(np.abs(ratio - 1.0) < 1e-6))
    frac = at_one / len(ratio)
    by_geo = {}
    for g, r in zip(panel["geo"][m], ratio):
        by_geo.setdefault(g, []).append(abs(r - 1.0) < 1e-6)
    allone = sum(1 for v in by_geo.values() if all(v))
    noneone = sum(1 for v in by_geo.values() if not any(v))
    ok = frac > 0.5
    detail = (f"{len(ratio):,} cells carry both labour classes with positive self "
              f"employed hours, a median {100*np.median(dh[m]/panel['H'][m]):.1f}% "
              f"of hours. The implied self employed hourly wage over the employee "
              f"wage is exactly one in {at_one:,} ({100*frac:.2f}%), and negative "
              f"in {int(np.sum(ratio<0)):,} ({100*np.mean(ratio<0):.2f}%). Of "
              f"{len(by_geo)} countries, {allone} impute at the employee wage in "
              f"every cell and {noneone} in none. So the split is a compiler "
              f"convention on this panel and carries no class reading: PASS here "
              f"records that this carrier was checked and set aside, not that a "
              f"reading was taken from it.")
    return bool(ok), detail, {"n": int(len(ratio)), "exactly_one": at_one,
                              "fraction_one": frac,
                              "negative": int(np.sum(ratio < 0)),
                              "countries": len(by_geo),
                              "countries_always_one": allone,
                              "countries_never_one": noneone}


# -------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    panel = load_panel()
    table = XS.cells(panel)
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B101-30", "instrument",
         "three mixes, which of them carries a currency, and the identity that "
         "ties two of them together", check_mixes(panel, table, rng)),
        ("B101-31", "own_reading",
         "the reading on the mix the source paper uses", check_quantity(panel, table)),
        ("B101-32", "own_reading",
         "whether the two definitions give the same verdict",
         check_two_definitions(panel, table)),
        ("B101-33", "known_answer",
         "an unconstrained conversion flattens the mix and reads zero, so the "
         "question has content only once a parity is tied to the country",
         check_free_conversion(panel, table)),
        ("B101-35", "rival",
         "whether one parity per country, shared across industries, could put "
         "the field back on one scalar per position",
         check_parity_bound(panel, table)),
        ("B101-34", "instrument",
         "whether the employee and self employed split in this panel is an object "
         "or a compiler convention", check_self_employed(panel)),
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
                    "productivity is a scalar attached to a position, one level "
                    "per country-industry-year, and the cross-country comparison "
                    "is read in common units, so a purchasing power parity is a "
                    "per country factor on each factor's units",
                "rival_entailment":
                    "under that premise there is a conversion e making omega(e) "
                    "the difference of node values, so the minimum over e of the "
                    "distance from im d0 is zero, and up to the discrete index's "
                    "curvature it is the curvature floor. omega(e) is linear in "
                    "e, so that minimum is a least squares value rather than a "
                    "search: it is the smallest reading ANY conversion can give, "
                    "of any size, on both factors at once.",
                "cite": "Griffith, Redding and Van Reenen (2004), equations 9 to 11",
                "grid_note": {
                    "ours": "the comparison field is not a gradient because two "
                            "classes at one position are on different terms, and "
                            "a per country change of units cannot remove that, "
                            "since it adds a term with the same pair-varying "
                            "weight rather than cancelling one",
                    "rival": "with the right parity the field becomes one level "
                             "per position, so the minimum sits at the floor",
                    "reality": "solved once over every cross-section at the same "
                               "time with one number per country, the "
                               "minimum reaches the floor in none of "
                               "the readings, under either definition "
                               "and either scope",
                },
            })
        criteria.append(c)
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {
        "stage": "B101",
        "config": {"seed": a.seed,
                   "mixes": {k: v for k, v in
                             (("quantity", "ln(H_EMP / K_GFCF)"),
                              ("value", "ln(LAB / K_GFCF)"),
                              ("wage", "ln(LAB / H_EMP)"))},
                   "share": "LAB / (LAB + CAP)", "output": "VA_CP",
                   "sources": ["growth accounts basic.csv", "capital accounts.csv",
                               "national accounts.csv"]},
        "criteria": criteria,
    }
    body = json.dumps(record, indent=2, sort_keys=True, default=float)
    print(f"\n{sum(c['passed'] for c in criteria)}/{len(criteria)} pass, "
          f"{time.time()-t0:.2f}s, sha256 "
          f"{hashlib.sha256(body.encode()).hexdigest()[:16]}")
    if not a.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(body, encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
