"""B105: what cutting a relation rewrites, read before the cut.

B103 reads an action that adds a relation, from the world before it. This station reads the
action that removes one, from the world before it: every quantity in the statements is
computed on the graph that still holds the relation.

For a relation e = (i -> j) with weight w_e and term omega_e, put u = L^+ (e_j - e_i),
R = (e_j - e_i)' u, the leverage h_e = w_e R, and r_e = omega_e - (phi*(j) - phi*(i)), the
residual the fit leaves on e. For a package F, H_F = W_F^{1/2} B_F L^+ B_F' W_F^{1/2}.

  B105-1  h_e = 1 exactly when e is a bridge; otherwise cutting e leaves its two ends at the
          relative level omega_e - r_e / (1 - h_e), moves every potential by
          -(w_e r_e / (1 - h_e)) u, and lowers rho^2 by w_e r_e^2 / (1 - h_e).
  B105-2  cutting F disconnects the graph exactly when det(I - H_F) = 0; otherwise the gaps
          it leaves on F are g_F = W_F^{-1/2} (I - H_F)^{-1} W_F^{1/2} r_F, every potential
          moves by -L^+ B_F' W_F g_F, and rho^2 falls by r_F' W_F g_F.
  B105-3  weakening e to the weight (1 - kappa) w_e, 0 < kappa < 1, leaves its two ends at the
          relative level omega_e - r_e / (1 - kappa h_e), moves every potential by
          -(kappa w_e r_e / (1 - kappa h_e)) u, and lowers rho^2 by
          kappa w_e r_e^2 / (1 - kappa h_e). kappa = 1 is the cut of B105-1.
  B105-4  moving e's term by Delta, with every weight and every other term where it was,
          moves its two ends' relative level by h_e Delta, its residual by (1 - h_e) Delta,
          every potential by w_e Delta u and rho^2 by w_e Delta (2 r_e + (1 - h_e) Delta), and
          no pair of positions by more than h_e |Delta|. The share read from two fits, with the
          move m of a later cut of e read from a third, returns e's residual as
          -m (1 - h_e) / h_e.
  B105-5  moving the terms of a package F by Delta_F moves its members' levels by
          W_F^{-1/2} H_F W_F^{1/2} Delta_F, and after e is weakened to (1 - kappa) w_e its
          share is (1 - kappa) h_e / (1 - kappa h_e).

Each closed form is compared with a second fit on the graph after the cut or the weakening.
Its float error is multiplied by the factor that multiplies the residual, 1/(1 - h_e),
1/(1 - kappa h_e) or the norm of (I - H_F)^{-1}, so the tolerance is scaled by that factor;
the floor is measured on cuts and weakenings that should move nothing. A term that moves
changes no weight, so B105-4 and B105-5 compare against the tolerance itself, except the
residual recovered from a share and a cut, which divides by the share and by 1 - h_e and is
read divided by the larger of the two factors; their floor is a move of every term along a
potential difference, which moves every potential by exactly that potential.

Paper station: zero data. The projection and the graph helpers are imported from B103.

Run:
    python experiments/b105_cutting_relations.py
    python experiments/b105_cutting_relations.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b103_time_reachability as B103                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b105_cutting_relations.json"

SEED = 105
#: Every connected labelled graph on 2 to 6 vertices: every edge cut alone, every pair of
#: edges cut together. Every triple of edges on 2 to 5 vertices.
MAX_ENUM_N = 6
MAX_TRIPLE_N = 5
#: Sparse random connected graphs, as in B104: every edge cut alone, and a few packages.
SIZES = (16, 32, 64)
GRAPHS_PER_SIZE = 200
PACKAGES_PER_GRAPH = 5
PACKAGE_SIZES = (2, 3, 4)
EXTRA_SCALE = 1.5
#: B105-3 weakens every edge that B105-1 cuts, to (1 - kappa) of its weight, at each of these
#: fractions: on every enumerated graph, and on the random graphs of the sizes below. The
#: fractions are fixed, so no random draw is added and B105-1 and B105-2 read the graphs they
#: read before B105-3 existed.
KAPPAS = (0.3, 0.8)
WEAK_SIZES = (16, 32)
#: B105-4 moves the term of every edge that B105-1 cuts by DELTA, and B105-5 moves the terms of
#: every package that B105-2 cuts by DELTA with alternating signs and reads the share of every
#: edge that B105-3 weakens. The amounts are fixed, so no random draw is added and B105-1 to
#: B105-3 read the graphs they read before B105-4 and B105-5 existed.
DELTA = 0.7
#: a share below this, or between 1 - this and one, counts toward B105-4's exercised shares
SHARE_EDGE = 0.1
#: Closed forms are compared at TOL times the factor that multiplies the residual. A relation
#: counts as a bridge when its leverage is within TOL_EDGE of one, and a package as
#: disconnecting when det(I - H_F) is within TOL_EDGE of zero. Only the tolerances go into
#: the record; what the run reaches is printed, because the last digits belong to the BLAS
#: build.
TOL = 1e-9
TOL_EDGE = 1e-9


def sig(x, digits=6):
    """A float through an explicit format spec, so the record does not carry BLAS digits."""
    return float(f"{x:.{digits}g}")


def base_fit(n, edges, w, om):
    phi, rho2, _, Lp = B103.fit(n, edges, w, om)
    return {"phi": phi, "rho2": rho2, "Lp": Lp, "B": B103.incidence(n, edges),
            "c": B103.components(n, edges)}


def finite_ratio(err, scale):
    return err / scale if np.isfinite(err) and np.isfinite(scale) else np.inf


# ------------------------------------------------- one cut

def cut_one(n, edges, w, om, base, k, mutate_amp=None, mutate_lev=None, mutate_bridge=None):
    """Everything B105-1 reads about cutting edge k, from the graph before the cut.

    Seeded errors for the self-test: `mutate_amp="drop"` releases the residual itself, and
    `"slip"` releases it off by one part in a million; `mutate_lev="unweighted"` takes R for
    the leverage; `mutate_bridge="h99"` calls every relation with leverage above 0.99 a bridge.
    """
    i, j = edges[k]
    b = B103.unit(n, i, j)
    u = base["Lp"] @ b
    R = float(b @ u)
    h = R if mutate_lev == "unweighted" else float(w[k]) * R
    r = float(om[k] - b @ base["phi"])
    rest = edges[:k] + edges[k + 1:]
    bridge = B103.components(n, rest) > base["c"]
    said = h > 0.99 if mutate_bridge == "h99" else h >= 1.0 - TOL_EDGE
    row = {"bridge": bridge, "mismatch": int(bridge != said), "h": h, "amp": None,
           "err": 0.0, "abs_err": 0.0, "level_after": None}
    if bridge:
        return row
    den = 1.0 - h
    amp = 1.0 / den if den != 0.0 else np.inf
    released = r if mutate_amp == "drop" else r * amp * (1.0 + 1e-6 * (mutate_amp == "slip"))
    phi2, rho22, _, _ = B103.fit(n, rest, np.delete(w, k), np.delete(om, k))
    level = abs((om[k] - released) - float(b @ phi2))
    pot = float(np.max(np.abs((phi2 - base["phi"]) + (w[k] * released) * u)))
    rho = abs((base["rho2"] - rho22) - w[k] * r * released)
    worst = max(level, pot, rho)
    row.update(amp=amp, abs_err=worst, err=finite_ratio(worst, max(1.0, abs(amp))),
               level_after=float(b @ phi2))
    return row


def null_cut(n, edges, w, om, k, offset=0.0):
    """The same cut with the term set to the level the rest of the graph gives: nothing moves.

    `offset` moves the term off that level, which the self-test uses to see the floor move.
    """
    i, j = edges[k]
    rest = edges[:k] + edges[k + 1:]
    phim, _, _, _ = B103.fit(n, rest, np.delete(w, k), np.delete(om, k))
    om0 = om.copy()
    om0[k] = phim[j] - phim[i] + offset
    phia, _, _, _ = B103.fit(n, edges, w, om0)
    return float(np.max(np.abs(phia - phim)))


# ------------------------------------------------- one weakening

def weaken_one(n, edges, w, om, base, k, kappa, mutate_weak=None):
    """Everything B105-3 reads about weakening edge k to (1 - kappa) of its weight.

    Seeded errors for the self-test: `mutate_weak="full"` puts 1 - h_e where 1 - kappa h_e
    belongs, `"nokappa"` drops kappa from the potential shift and the fall in rho^2, and
    `"slip"` puts the residual left on the edge off by one part in a million.
    """
    i, j = edges[k]
    b = B103.unit(n, i, j)
    u = base["Lp"] @ b
    h = float(w[k]) * float(b @ u)
    r = float(om[k] - b @ base["phi"])
    kh = h if mutate_weak == "full" else kappa * h
    den = 1.0 - kh
    amp = 1.0 / den if den != 0.0 else np.inf
    with np.errstate(invalid="ignore"):
        gap = r * amp * (1.0 + 1e-6 * (mutate_weak == "slip"))
    kap = 1.0 if mutate_weak == "nokappa" else kappa
    w2 = w.copy()
    w2[k] = (1.0 - kappa) * w[k]
    phi2, rho22, _, _ = B103.fit(n, edges, w2, om)
    with np.errstate(invalid="ignore"):
        level = abs((om[k] - gap) - float(b @ phi2))
        pot = float(np.max(np.abs((phi2 - base["phi"]) + (kap * w[k] * gap) * u)))
        rho = abs((base["rho2"] - rho22) - kap * w[k] * r * gap)
    worst = max(level, pot, rho) if all(np.isfinite([level, pot, rho])) else np.inf
    return {"bridge": h >= 1.0 - TOL_EDGE, "h": h, "kappa": kappa, "kh": kappa * h,
            "amp": amp, "abs_err": worst, "err": finite_ratio(worst, max(1.0, abs(amp)))}


def null_weak(n, edges, w, om, k, kappa, offset=0.0):
    """The same weakening with the term set to the level the rest of the graph gives."""
    i, j = edges[k]
    rest = edges[:k] + edges[k + 1:]
    phim, _, _, _ = B103.fit(n, rest, np.delete(w, k), np.delete(om, k))
    om0 = om.copy()
    om0[k] = phim[j] - phim[i] + offset
    phi0, _, _, _ = B103.fit(n, edges, w, om0)
    w2 = w.copy()
    w2[k] = (1.0 - kappa) * w[k]
    phia, _, _, _ = B103.fit(n, edges, w2, om0)
    return float(np.max(np.abs(phia - phi0)))


# ------------------------------------------------- a package of cuts

def leverage_matrix(base, w, ks, mutate_H=None):
    BF = base["B"][ks]
    M = BF @ base["Lp"] @ BF.T
    if mutate_H == "unweighted":
        return BF, M
    sq = np.sqrt(w[ks])
    return BF, sq[:, None] * M * sq[None, :]


def cut_package(n, edges, w, om, base, ks, mutate_pack=None, mutate_sing=None, mutate_H=None):
    """Everything B105-2 reads about cutting the edges `ks` together.

    Seeded errors for the self-test: `mutate_pack="additive"` adds the single cuts' gaps and
    drops H_F's off-diagonal, and `"slip"` puts the gaps off by one part in a million;
    `mutate_sing="hmax"` calls a package disconnecting when its largest single leverage is
    one; `mutate_H="unweighted"` builds H_F without the weights.
    """
    ks = list(ks)
    BF, H = leverage_matrix(base, w, ks, mutate_H)
    A = np.eye(len(ks)) - H
    det = float(np.linalg.det(A))
    hmax = float(np.max(np.diag(H)))
    drop = set(ks)
    keep = [t for t in range(len(edges)) if t not in drop]
    rest = [edges[t] for t in keep]
    cuts = B103.components(n, rest) > base["c"]
    said = hmax >= 1.0 - TOL_EDGE if mutate_sing == "hmax" else abs(det) <= TOL_EDGE
    row = {"cuts": cuts, "mismatch": int(cuts != said), "size": len(ks),
           "joint": bool(cuts and hmax < 1.0 - TOL_EDGE), "err": 0.0, "abs_err": 0.0,
           "interacting": False, "det": det, "norm": None}
    if cuts:
        return row
    wF = w[ks]
    sq = np.sqrt(wF)
    rF = om[ks] - BF @ base["phi"]
    if mutate_pack == "additive":
        gap = rF / (1.0 - np.diag(H))
    else:
        gap = (1.0 / sq) * np.linalg.solve(A, sq * rF) * (1.0 + 1e-6 * (mutate_pack == "slip"))
    phi2, rho22, _, _ = B103.fit(n, rest, w[keep], om[keep])
    level = float(np.max(np.abs((om[ks] - gap) - BF @ phi2)))
    pot = float(np.max(np.abs((phi2 - base["phi"]) + base["Lp"] @ (BF.T @ (wF * gap)))))
    rho = abs((base["rho2"] - rho22) - float(rF @ (wF * gap)))
    worst = max(level, pot, rho)
    norm = float(np.linalg.norm(np.linalg.inv(A), 2))
    off = float(np.max(np.abs(H - np.diag(np.diag(H))))) if len(ks) > 1 else 0.0
    row.update(abs_err=worst, err=finite_ratio(worst, max(1.0, norm)), norm=norm,
               interacting=off > 1e-6)
    return row


def null_package(n, edges, w, om, ks):
    """The same package with its terms set to the levels the rest of the graph gives."""
    ks = list(ks)
    drop = set(ks)
    keep = [t for t in range(len(edges)) if t not in drop]
    rest = [edges[t] for t in keep]
    phim, _, _, _ = B103.fit(n, rest, w[keep], om[keep])
    BF = B103.incidence(n, [edges[t] for t in ks])
    om0 = om.copy()
    om0[ks] = BF @ phim
    phia, _, _, _ = B103.fit(n, edges, w, om0)
    return float(np.max(np.abs(phia - phim)))



# ------------------------------------------------- a term moved in place

def shift_one(n, edges, w, om, base, k, delta, cut_level=None, mutate_shift=None):
    """Everything B105-4 reads about moving edge k's term by delta, from the graph before.

    `cut_level` is the relative level B105-1's second fit leaves on edge k after cutting it,
    and the residual is recovered from it with the share read from this move's second fit.
    Seeded errors for the self-test: `mutate_shift="unweighted"` takes R for the share,
    `"whole"` moves the residual by the whole of delta, `"linear"` drops the quadratic term of
    the change in rho^2, `"slip"` puts the share off by one part in a million, `"bound"`
    bounds the pairs by half the share, and `"recover"` returns the residual as
    -m h_e / (1 - h_e).
    """
    i, j = edges[k]
    b = B103.unit(n, i, j)
    u = base["Lp"] @ b
    R = float(b @ u)
    h = float(w[k]) * R
    share = R if mutate_shift == "unweighted" else h * (1.0 + 1e-6 * (mutate_shift == "slip"))
    r = float(om[k] - b @ base["phi"])
    om2 = om.copy()
    om2[k] += delta
    phi2, rho22, _, _ = B103.fit(n, edges, w, om2)
    moved = float(b @ phi2) - float(b @ base["phi"])
    level = abs(moved - share * delta)
    res_move = delta if mutate_shift == "whole" else (1.0 - share) * delta
    resid = abs(((om2[k] - float(b @ phi2)) - r) - res_move)
    pot = float(np.max(np.abs((phi2 - base["phi"]) - (w[k] * delta) * u)))
    quad = 0.0 if mutate_shift == "linear" else (1.0 - share) * delta
    rho = abs((rho22 - base["rho2"]) - w[k] * delta * (2.0 * r + quad))
    bound = share * abs(delta) * (0.5 if mutate_shift == "bound" else 1.0)
    spread = float(w[k]) * abs(delta) * float(np.max(u) - np.min(u))
    over = max(0.0, spread - bound)
    worst = max(level, resid, pot, rho, over)
    row = {"bridge": h >= 1.0 - TOL_EDGE, "h": h, "abs_err": worst,
           "err": worst / max(1.0, abs(delta)), "recovered": False, "rec_err": 0.0}
    if cut_level is not None and not row["bridge"]:
        m = cut_level - float(b @ base["phi"])
        hm = moved / delta
        with np.errstate(divide="ignore", invalid="ignore"):
            got = -m * hm / (1.0 - hm) if mutate_shift == "recover" else -m * (1.0 - hm) / hm
        scale = max(1.0, 1.0 / hm, 1.0 / (1.0 - hm))
        row.update(recovered=True, rec_err=finite_ratio(abs(got - r), scale), rec_scale=scale)
    return row


def null_shift(n, edges, w, om, base, k=0, offset=0.0):
    """Every term moved along a potential difference: every potential moves by that potential.

    `offset` also moves edge k's term off that difference, which the self-test uses to see the
    floor move.
    """
    psi = np.sin(1.0 + np.arange(n, dtype=float))
    om2 = om + base["B"] @ psi
    om2[k] += offset
    phi2, _, _, _ = B103.fit(n, edges, w, om2)
    return float(np.max(np.abs((phi2 - base["phi"]) - (psi - psi.mean()))))


def shift_package(n, edges, w, om, base, ks, mutate_pshift=None):
    """What B105-5 reads about moving the terms of the edges `ks` together.

    The terms move by DELTA with alternating signs. Seeded errors for the self-test:
    `mutate_pshift="diag"` keeps only the diagonal of H_F, `"unweighted"` drops W_F, and
    `"slip"` puts the moves off by one part in a million.
    """
    ks = list(ks)
    BF = base["B"][ks]
    M = BF @ base["Lp"] @ BF.T
    wF = w[ks]
    d = DELTA * np.array([1.0 if t % 2 == 0 else -1.0 for t in range(len(ks))])
    if mutate_pshift == "diag":
        pred = np.diag(M) * wF * d
    elif mutate_pshift == "unweighted":
        pred = M @ d
    else:
        pred = (M @ (wF * d)) * (1.0 + 1e-6 * (mutate_pshift == "slip"))
    om2 = om.copy()
    om2[ks] += d
    phi2, _, _, _ = B103.fit(n, edges, w, om2)
    worst = float(np.max(np.abs(BF @ (phi2 - base["phi"]) - pred)))
    sq = np.sqrt(wF)
    off = (float(np.max(np.abs((sq[:, None] * M * sq[None, :]) * (1.0 - np.eye(len(ks))))))
           if len(ks) > 1 else 0.0)
    return {"size": len(ks), "abs_err": worst, "err": worst / max(1.0, DELTA),
            "interacting": off > 1e-6}


def weakened_share(n, edges, w, om, k, kappa, mutate_wshare=None):
    """B105-5's second reading: edge k's share after it is weakened to (1 - kappa) of its weight.

    Seeded errors for the self-test: `mutate_wshare="plain"` gives (1 - kappa) h_e, and
    `"nokappa"` gives h_e.
    """
    i, j = edges[k]
    b = B103.unit(n, i, j)
    _, _, _, Lp = B103.fit(n, edges, w, om)
    h = float(w[k]) * float(b @ Lp @ b)
    w2 = w.copy()
    w2[k] = (1.0 - kappa) * w[k]
    _, _, _, Lp2 = B103.fit(n, edges, w2, om)
    got = float(w2[k]) * float(b @ Lp2 @ b)
    if mutate_wshare == "plain":
        pred = (1.0 - kappa) * h
    elif mutate_wshare == "nokappa":
        pred = h
    else:
        pred = (1.0 - kappa) * h / (1.0 - kappa * h)
    return abs(got - pred)

# ------------------------------------------------- aggregation, so nothing large is held

def new_single():
    return {"cuts": 0, "bridges": 0, "mismatch": 0, "worst": 0.0, "worst_abs": 0.0,
            "amps": [], "over_half": 0, "near_bridge": 0, "max_h": 0.0, "floor": 0.0,
            "vertices_over_cuts": 0}


def add_single(agg, row):
    agg["cuts"] += 1
    agg["mismatch"] += row["mismatch"]
    if row["bridge"]:
        agg["bridges"] += 1
        return
    agg["worst"] = max(agg["worst"], row["err"])
    agg["worst_abs"] = max(agg["worst_abs"], row["abs_err"])
    agg["amps"].append(row["amp"])
    agg["over_half"] += int(row["h"] > 0.5)
    agg["near_bridge"] += int(0.99 < row["h"] < 1.0 - TOL_EDGE)
    agg["max_h"] = max(agg["max_h"], row["h"])


def new_package():
    return {"packages": 0, "by_size": {}, "cuts": 0, "joint": 0, "mismatch": 0, "worst": 0.0,
            "worst_abs": 0.0, "interacting": 0, "connected": 0, "det_min": np.inf,
            "norm_max": 0.0, "floor": 0.0}


def add_package(agg, row):
    agg["packages"] += 1
    agg["by_size"][row["size"]] = agg["by_size"].get(row["size"], 0) + 1
    agg["mismatch"] += row["mismatch"]
    if row["cuts"]:
        agg["cuts"] += 1
        agg["joint"] += int(row["joint"])
        return
    agg["connected"] += 1
    agg["worst"] = max(agg["worst"], row["err"])
    agg["worst_abs"] = max(agg["worst_abs"], row["abs_err"])
    agg["interacting"] += int(row["interacting"])
    agg["det_min"] = min(agg["det_min"], row["det"])
    agg["norm_max"] = max(agg["norm_max"], row["norm"])


def new_weak():
    return {"weakenings": 0, "bridges": 0, "worst": 0.0, "worst_abs": 0.0, "over_half": 0,
            "by_kappa": {}, "max_amp": 0.0, "max_amp_non_bridge": 0.0, "floor": 0.0}


def add_weak(agg, row):
    agg["weakenings"] += 1
    agg["by_kappa"][row["kappa"]] = agg["by_kappa"].get(row["kappa"], 0) + 1
    agg["bridges"] += int(row["bridge"])
    agg["over_half"] += int(row["kh"] > 0.5)
    agg["worst"] = max(agg["worst"], row["err"])
    agg["worst_abs"] = max(agg["worst_abs"], row["abs_err"])
    if np.isfinite(row["amp"]):
        agg["max_amp"] = max(agg["max_amp"], row["amp"])
        if not row["bridge"]:
            agg["max_amp_non_bridge"] = max(agg["max_amp_non_bridge"], row["amp"])


def judge_single(agg):
    exercised = agg["bridges"] > 0 and agg["cuts"] > agg["bridges"] and agg["over_half"] > 0
    ok = agg["cuts"] > 0 and agg["mismatch"] == 0 and agg["worst"] <= TOL and exercised
    return ok, agg["worst"], agg["mismatch"]


def judge_package(agg):
    exercised = (agg["joint"] > 0 and agg["interacting"] > 0
                 and max(agg["by_size"], default=0) >= 3)
    ok = agg["packages"] > 0 and agg["mismatch"] == 0 and agg["worst"] <= TOL and exercised
    return ok, agg["worst"], agg["mismatch"]


def judge_weak(agg):
    exercised = (agg["bridges"] > 0 and agg["weakenings"] > agg["bridges"]
                 and agg["over_half"] > 0 and len(agg["by_kappa"]) == len(KAPPAS))
    ok = agg["weakenings"] > 0 and agg["worst"] <= TOL and exercised
    return ok, agg["worst"]


def new_shift():
    return {"shifts": 0, "bridges": 0, "worst": 0.0, "worst_abs": 0.0, "low_share": 0,
            "high_share": 0, "recovered": 0, "rec_worst": 0.0, "floor": 0.0}


def add_shift(agg, row):
    agg["shifts"] += 1
    agg["bridges"] += int(row["bridge"])
    agg["low_share"] += int(row["h"] < SHARE_EDGE)
    agg["high_share"] += int(1.0 - SHARE_EDGE < row["h"] < 1.0 - TOL_EDGE)
    agg["worst"] = max(agg["worst"], row["err"])
    agg["worst_abs"] = max(agg["worst_abs"], row["abs_err"])
    if row["recovered"]:
        agg["recovered"] += 1
        agg["rec_worst"] = max(agg["rec_worst"], row["rec_err"])


def judge_shift(agg):
    exercised = (agg["bridges"] > 0 and agg["low_share"] > 0 and agg["high_share"] > 0
                 and agg["recovered"] > 0)
    worst = max(agg["worst"], agg["rec_worst"])
    ok = agg["shifts"] > 0 and worst <= TOL and exercised
    return ok, worst


def new_pshift():
    return {"packages": 0, "by_size": {}, "interacting": 0, "worst": 0.0, "worst_abs": 0.0,
            "weakened": 0, "by_kappa": {}, "w_worst": 0.0, "floor": 0.0}


def add_pshift(agg, row):
    agg["packages"] += 1
    agg["by_size"][row["size"]] = agg["by_size"].get(row["size"], 0) + 1
    agg["interacting"] += int(row["interacting"])
    agg["worst"] = max(agg["worst"], row["err"])
    agg["worst_abs"] = max(agg["worst_abs"], row["abs_err"])


def add_wshare(agg, kappa, err):
    agg["weakened"] += 1
    agg["by_kappa"][kappa] = agg["by_kappa"].get(kappa, 0) + 1
    agg["w_worst"] = max(agg["w_worst"], err)


def judge_pshift(agg):
    exercised = (agg["interacting"] > 0 and max(agg["by_size"], default=0) >= 3
                 and len(agg["by_kappa"]) == len(KAPPAS))
    worst = max(agg["worst"], agg["w_worst"])
    ok = agg["packages"] > 0 and agg["weakened"] > 0 and worst <= TOL and exercised
    return ok, worst


# ------------------------------------------------- graphs

def connected_graphs(rng, max_n):
    """Every connected labelled graph on 2..max_n vertices, with a random orientation,
    weights and terms drawn once per graph."""
    for n in range(2, max_n + 1):
        pairs = list(itertools.combinations(range(n), 2))
        for code in range(1 << len(pairs)):
            und = [pairs[k] for k in range(len(pairs)) if code >> k & 1]
            if B103.components(n, und) != 1:
                continue
            edges = [(a, b) if rng.random() < 0.5 else (b, a) for (a, b) in und]
            w = np.exp(rng.normal(0.0, 1.0, len(edges)))
            om = rng.normal(0.0, 1.0, len(edges))
            yield n, edges, w, om


def weaken_all(n, edges, w, om, base, weaks, floors, pshifts=None, wshare_kw=None, **weak_kw):
    floored = False
    for k in range(len(edges)):
        for kappa in KAPPAS:
            row = weaken_one(n, edges, w, om, base, k, kappa, **weak_kw)
            add_weak(weaks, row)
            if floors and not floored and not row["bridge"]:
                weaks["floor"] = max(weaks["floor"], null_weak(n, edges, w, om, k, kappa))
                floored = True
            if pshifts is not None:
                add_wshare(pshifts, kappa,
                           weakened_share(n, edges, w, om, k, kappa, **(wshare_kw or {})))


def run_enumeration(rng, max_n, triple_n, singles, packages, floors=True, weaks=None,
                    shifts=None, pshifts=None, **mutate):
    single_kw = {k: v for k, v in mutate.items() if k in ("mutate_amp", "mutate_lev",
                                                           "mutate_bridge")}
    package_kw = {k: v for k, v in mutate.items() if k in ("mutate_pack", "mutate_sing",
                                                            "mutate_H")}
    weak_kw = {k: v for k, v in mutate.items() if k == "mutate_weak"}
    shift_kw = {k: v for k, v in mutate.items() if k == "mutate_shift"}
    pshift_kw = {k: v for k, v in mutate.items() if k == "mutate_pshift"}
    wshare_kw = {k: v for k, v in mutate.items() if k == "mutate_wshare"}
    for n, edges, w, om in connected_graphs(rng, max_n):
        base = base_fit(n, edges, w, om)
        floored = False
        for k in range(len(edges)):
            row = cut_one(n, edges, w, om, base, k, **single_kw)
            add_single(singles, row)
            if floors and not floored and not row["bridge"]:
                singles["floor"] = max(singles["floor"], null_cut(n, edges, w, om, k))
                floored = True
            if shifts is not None:
                add_shift(shifts, shift_one(n, edges, w, om, base, k, DELTA,
                                            cut_level=row["level_after"], **shift_kw))
        if shifts is not None and floors:
            shifts["floor"] = max(shifts["floor"], null_shift(n, edges, w, om, base))
        if weaks is not None:
            weaken_all(n, edges, w, om, base, weaks, floors, pshifts=pshifts,
                       wshare_kw=wshare_kw, **weak_kw)
        sizes = (2, 3) if n <= triple_n else (2,)
        floored = False
        for size in sizes:
            for ks in itertools.combinations(range(len(edges)), size):
                row = cut_package(n, edges, w, om, base, ks, **package_kw)
                add_package(packages, row)
                if floors and not floored and not row["cuts"]:
                    packages["floor"] = max(packages["floor"],
                                            null_package(n, edges, w, om, ks))
                    floored = True
                if pshifts is not None:
                    add_pshift(pshifts, shift_package(n, edges, w, om, base, ks, **pshift_kw))


def run_random(rng, sizes, per_size, singles, packages, floors=True, weaks=None, shifts=None,
               pshifts=None):
    for n in sizes:
        for _ in range(per_size):
            edges, _ = B103.random_connected(rng, n, EXTRA_SCALE / n)
            w = np.exp(rng.normal(0.0, 1.0, len(edges)))
            om = rng.normal(0.0, 1.0, len(edges))
            base = base_fit(n, edges, w, om)
            floored = False
            for k in range(len(edges)):
                row = cut_one(n, edges, w, om, base, k)
                add_single(singles, row)
                if floors and not floored and not row["bridge"]:
                    singles["floor"] = max(singles["floor"], null_cut(n, edges, w, om, k))
                    floored = True
                if shifts is not None:
                    add_shift(shifts, shift_one(n, edges, w, om, base, k, DELTA,
                                                cut_level=row["level_after"]))
            if shifts is not None and floors:
                shifts["floor"] = max(shifts["floor"], null_shift(n, edges, w, om, base))
            if weaks is not None and n in WEAK_SIZES:
                weaken_all(n, edges, w, om, base, weaks, floors, pshifts=pshifts)
            floored = False
            for _ in range(PACKAGES_PER_GRAPH):
                size = int(rng.choice(PACKAGE_SIZES))
                ks = sorted(int(x) for x in rng.choice(len(edges), size, replace=False))
                row = cut_package(n, edges, w, om, base, ks)
                add_package(packages, row)
                if floors and not floored and not row["cuts"]:
                    packages["floor"] = max(packages["floor"],
                                            null_package(n, edges, w, om, ks))
                    floored = True
                if pshifts is not None:
                    add_pshift(pshifts, shift_package(n, edges, w, om, base, ks))


def summary_single(agg):
    amps = np.array(agg["amps"]) if agg["amps"] else np.array([np.nan])
    non_bridge = agg["cuts"] - agg["bridges"]
    return {"cuts": agg["cuts"], "bridges": agg["bridges"], "non_bridges": non_bridge,
            "non_bridges_with_leverage_above_half": agg["over_half"],
            "share_of_non_bridges_with_leverage_above_half":
                sig(agg["over_half"] / non_bridge, 4) if non_bridge else None,
            "non_bridges_with_leverage_above_0_99": agg["near_bridge"],
            "median_amplification": sig(float(np.median(amps)), 3),
            "largest_amplification": sig(float(np.max(amps)), 3)}


def summary_weak(agg):
    return {"weakenings": agg["weakenings"],
            "weakenings_by_kappa": {f"{k:g}": v for k, v in sorted(agg["by_kappa"].items())},
            "bridges_weakened": agg["bridges"],
            "weakenings_with_kappa_times_leverage_above_half": agg["over_half"],
            "largest_amplification": sig(agg["max_amp"], 3),
            "largest_amplification_on_non_bridges": sig(agg["max_amp_non_bridge"], 3)}


def summary_shift(agg):
    return {"term_moves": agg["shifts"], "of_bridges": agg["bridges"],
            "with_share_below_0_1": agg["low_share"],
            "non_bridges_with_share_above_0_9": agg["high_share"],
            "residuals_recovered_from_a_share_and_a_cut": agg["recovered"]}


def summary_pshift(agg):
    return {"package_term_moves": agg["packages"],
            "package_term_moves_by_size": {str(k): v for k, v in sorted(agg["by_size"].items())},
            "with_interacting_members": agg["interacting"],
            "weakened_shares": agg["weakened"],
            "weakened_shares_by_kappa": {f"{k:g}": v for k, v in sorted(agg["by_kappa"].items())}}


def summary_package(agg):
    return {"packages": agg["packages"],
            "packages_by_size": {str(k): v for k, v in sorted(agg["by_size"].items())},
            "disconnecting": agg["cuts"],
            "disconnecting_with_every_member_replaceable": agg["joint"],
            "connected_after": agg["connected"],
            "connected_after_with_interacting_members": agg["interacting"],
            "smallest_det_among_connected_after":
                sig(agg["det_min"], 3) if np.isfinite(agg["det_min"]) else None,
            "largest_norm_of_the_inverse": sig(agg["norm_max"], 3)}


# ------------------------------------------------- self-test

def near_cut_fixture():
    edges = [(0, 2), (2, 1), (0, 3), (3, 1), (0, 4), (4, 1)]
    w = np.array([1.0, 1.5, 0.7, 1.2, 1e-7, 1e-7])
    om = np.array([0.3, -0.2, 0.5, 0.1, -0.4, 0.6])
    return edges, w, om, [0, 2]


def spanning_tree_weight(n, edges, w):
    total = 0.0
    for sub in itertools.combinations(range(len(edges)), n - 1):
        if B103.components(n, [edges[t] for t in sub]) == 1:
            total += float(np.prod(w[list(sub)]))
    return total


def selftest() -> int:
    """Each criterion passes on a clean fixture and fails on planted errors (rule 11f)."""
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    def singles_on(**mutate):
        s, p = new_single(), new_package()
        run_enumeration(np.random.default_rng(11), 4, 4, s, p, floors=False, **mutate)
        single_kw = {a: b for a, b in mutate.items()
                     if a in ("mutate_amp", "mutate_lev", "mutate_bridge")}
        package_kw = {a: b for a, b in mutate.items()
                      if a in ("mutate_pack", "mutate_sing", "mutate_H")}
        # near-bridges: a triangle whose edge 0 is 1e2 and then 1e7 times stronger than the
        # path around it, so its leverage is 1e2 / (1e2 + 0.5) and then 1 - 5e-8
        for strong in (1e2, 1e7):
            edges = [(0, 1), (1, 2), (2, 0)]
            w = np.array([strong, 1.0, 1.0])
            om = np.array([0.4, -0.3, 0.2])
            base = base_fit(3, edges, w, om)
            for k in range(3):
                add_single(s, cut_one(3, edges, w, om, base, k, **single_kw))
        # a nearly disconnecting package: two strong routes from 0 to 1 and a third route of
        # weight 1e-7; cutting the two first edges of the strong routes leaves the weak one,
        # so det(I - H_F) is of order 1e-7 and the graph stays connected
        edges, w, om, ks = near_cut_fixture()
        base = base_fit(5, edges, w, om)
        add_package(p, cut_package(5, edges, w, om, base, ks, **package_kw))
        return s, p

    # known answers: leverage is a spanning-tree probability and sums to n - c, and
    # det(I - H_F) is the share of spanning-tree weight that avoids F
    rng = np.random.default_rng(3)
    worst_tree, worst_foster, tested = 0.0, 0.0, 0
    for _ in range(40):
        n = int(rng.choice([4, 5]))
        edges, _ = B103.random_connected(rng, n, 0.6)
        if len(edges) > 9:
            continue
        w = np.exp(rng.normal(0.0, 1.0, len(edges)))
        base = base_fit(n, edges, w, np.zeros(len(edges)))
        tau = spanning_tree_weight(n, edges, w)
        lev = [float(w[k]) * float(B103.unit(n, *edges[k]) @ base["Lp"] @ B103.unit(n, *edges[k]))
               for k in range(len(edges))]
        worst_foster = max(worst_foster, abs(sum(lev) - (n - base["c"])))
        for size in (1, 2, 3):
            for ks in itertools.combinations(range(len(edges)), size):
                _, H = leverage_matrix(base, w, list(ks))
                keep = [t for t in range(len(edges)) if t not in ks]
                ratio = spanning_tree_weight(n, [edges[t] for t in keep], w[keep]) / tau
                worst_tree = max(worst_tree, abs(float(np.linalg.det(np.eye(size) - H)) - ratio))
                tested += 1
    expect(tested > 0 and worst_tree <= 1e-12,
           "det(I - H_F) differs from the spanning-tree weight that avoids F")
    expect(worst_foster <= 1e-12, "leverages do not sum to n - c")

    clean_s, clean_p = singles_on()
    expect(judge_single(clean_s)[0], "B105-1 fails on a clean fixture")
    expect(clean_s["bridges"] > 0 and clean_s["over_half"] > 0,
           "seed not planted: no bridge, or no relation with leverage above one half")
    expect(clean_s["near_bridge"] > 0, "seed not planted: no relation with leverage in (0.99, 1)")
    edges = [(0, 1), (1, 2), (2, 0)]
    w = np.array([1e7, 1.0, 1.0])
    near = cut_one(3, edges, w, np.zeros(3), base_fit(3, edges, w, np.zeros(3)), 0)
    expect(not near["bridge"] and 1e-8 < 1.0 - near["h"] < 1e-6 and near["mismatch"] == 0,
           "seed not planted: no relation within 1e-6 of leverage one, or it is misread")
    expect(not judge_single(singles_on(mutate_amp="slip")[0])[0],
           "B105-1 passes with the released residual off by one part in a million")
    for field in ("bridges", "over_half"):
        expect(not judge_single(dict(clean_s, **{field: 0}))[0],
               f"B105-1 passes on a run with no {field.replace('_', ' ')}")
    expect(not judge_single(singles_on(mutate_amp="drop")[0])[0],
           "B105-1 passes with the residual released unamplified")
    expect(not judge_single(singles_on(mutate_lev="unweighted")[0])[0],
           "B105-1 passes with R taken for the leverage")
    expect(not judge_single(singles_on(mutate_bridge="h99")[0])[0],
           "B105-1 passes with leverage above 0.99 called a bridge")

    expect(judge_package(clean_p)[0], "B105-2 fails on a clean fixture")
    expect(clean_p["joint"] > 0,
           "seed not planted: no disconnecting package whose every member is replaceable")
    expect(clean_p["interacting"] > 0,
           "seed not planted: no connected-after package with interacting members")
    for field in ("joint", "interacting"):
        expect(not judge_package(dict(clean_p, **{field: 0}))[0],
               f"B105-2 passes on a run with no {field} package")
    expect(not judge_package(dict(clean_p, by_size={2: clean_p["packages"]}))[0],
           "B105-2 passes on a run with no package of three edges or more")
    edges, w, om, ks = near_cut_fixture()
    nearp = cut_package(5, edges, w, om, base_fit(5, edges, w, om), ks)
    expect(not nearp["cuts"] and 0.0 < nearp["det"] < 1e-6 and nearp["mismatch"] == 0,
           "seed not planted: no package within 1e-6 of disconnecting, or it is misread")
    path = [(0, 1), (1, 2)]
    square = [(0, 1), (1, 2), (2, 3), (3, 0)]
    for edges, ks, joint in ((path, [0, 1], False), (square, [0, 2], True)):
        n = len({v for e in edges for v in e})
        w = np.ones(len(edges))
        row = cut_package(n, edges, w, np.zeros(len(edges)), base_fit(n, edges, w, np.zeros(len(edges))), ks)
        expect(row["cuts"] and row["joint"] == joint,
               "a package of bridges is called replaceable member by member, or a square's "
               "opposite pair is not")
    for kw, what in ((dict(mutate_pack="additive"), "the single cuts' gaps added up"),
                     (dict(mutate_pack="slip"), "the gaps off by one part in a million"),
                     (dict(mutate_sing="hmax"), "disconnection read off the largest single "
                                                "leverage"),
                     (dict(mutate_H="unweighted"), "H_F built without the weights")):
        expect(not judge_package(singles_on(**kw)[1])[0], f"B105-2 passes with {what}")

    # B105-3: weakening. A clean run passes, and each planted error fails it.
    def weaks_on(**mutate):
        s, p, wk = new_single(), new_package(), new_weak()
        run_enumeration(np.random.default_rng(11), 4, 4, s, p, floors=False, weaks=wk,
                        **mutate)
        return wk

    clean_w = weaks_on()
    expect(judge_weak(clean_w)[0], "B105-3 fails on a clean fixture")
    expect(clean_w["bridges"] > 0 and clean_w["over_half"] > 0
           and len(clean_w["by_kappa"]) == len(KAPPAS),
           "seed not planted: no bridge weakened, no kappa h_e above one half, or a kappa missing")
    for kw, what in ((dict(mutate_weak="full"), "1 - h_e where 1 - kappa h_e belongs"),
                     (dict(mutate_weak="nokappa"), "kappa dropped from the shift and the fall"),
                     (dict(mutate_weak="slip"), "the residual left on the edge off by one part "
                                                "in a million")):
        expect(not judge_weak(weaks_on(**kw))[0], f"B105-3 passes with {what}")
    for field in ("bridges", "over_half"):
        expect(not judge_weak(dict(clean_w, **{field: 0}))[0],
               f"B105-3 passes on a run with no {field.replace('_', ' ')}")
    expect(not judge_weak(dict(clean_w, by_kappa={KAPPAS[0]: clean_w["weakenings"]}))[0],
           "B105-3 passes on a run that weakens at one fraction only")
    # known answer: weakening all the way, kappa = 1, is the cut of B105-1
    edges = [(0, 1), (1, 2), (2, 0), (0, 3), (3, 1)]
    w = np.array([2.0, 0.5, 1.3, 0.8, 1.7])
    om = np.array([0.4, -0.3, 0.2, 0.6, -0.1])
    base = base_fit(4, edges, w, om)
    whole = weaken_one(4, edges, w, om, base, 0, 1.0)
    cut = cut_one(4, edges, w, om, base, 0)
    expect(not cut["bridge"] and whole["abs_err"] <= 1e-11 and cut["abs_err"] <= 1e-11
           and abs(whole["amp"] - cut["amp"]) <= 1e-12,
           "weakening with kappa = 1 does not reproduce the cut")


    # B105-4 and B105-5: terms moved in place. A clean run passes, and each planted error fails.
    def shifts_on(**mutate):
        s, p, wk, sh, ps = new_single(), new_package(), new_weak(), new_shift(), new_pshift()
        run_enumeration(np.random.default_rng(11), 4, 4, s, p, floors=False, weaks=wk,
                        shifts=sh, pshifts=ps, **mutate)
        enumerated_recoveries = sh["recovered"]
        shift_kw = {a: b for a, b in mutate.items() if a == "mutate_shift"}
        # a share close to one: a triangle whose edge 0 is 1e2 times stronger than the path
        # around it, so that edge's share is 1e2 / (1e2 + 0.5)
        edges = [(0, 1), (1, 2), (2, 0)]
        w = np.array([1e2, 1.0, 1.0])
        om = np.array([0.4, -0.3, 0.2])
        base = base_fit(3, edges, w, om)
        for k in range(3):
            cut = cut_one(3, edges, w, om, base, k)
            add_shift(sh, shift_one(3, edges, w, om, base, k, DELTA, cut_level=cut["level_after"],
                                    **shift_kw))
        return sh, ps, enumerated_recoveries

    clean_sh, clean_ps, clean_enum_rec = shifts_on()
    expect(clean_enum_rec > 0, "the enumeration recovers no residual from a share and a cut")
    expect(judge_shift(clean_sh)[0], "B105-4 fails on a clean fixture")
    expect(clean_sh["bridges"] > 0 and clean_sh["low_share"] > 0 and clean_sh["high_share"] > 0
           and clean_sh["recovered"] > 0,
           "seed not planted: no bridge, no share below or above the edge, or no recovery")
    expect(clean_sh["low_share"] < clean_sh["shifts"] and clean_sh["high_share"] < clean_sh["shifts"]
           and clean_sh["recovered"] < clean_sh["shifts"] and clean_sh["bridges"] < clean_sh["shifts"],
           "the exercised counts count every move")
    for kw, what in ((dict(mutate_shift="unweighted"), "R taken for the share"),
                     (dict(mutate_shift="whole"), "the residual moved by the whole of the move"),
                     (dict(mutate_shift="linear"), "the quadratic term of rho^2 dropped"),
                     (dict(mutate_shift="slip"), "the share off by one part in a million"),
                     (dict(mutate_shift="bound"), "the pairs bounded by half the share"),
                     (dict(mutate_shift="recover"), "the residual recovered as -m h_e / (1 - h_e)")):
        expect(not judge_shift(shifts_on(**kw)[0])[0], f"B105-4 passes with {what}")
    for field in ("bridges", "low_share", "high_share", "recovered"):
        expect(not judge_shift(dict(clean_sh, **{field: 0}))[0],
               f"B105-4 passes on a run with no {field.replace('_', ' ')}")
    expect(judge_pshift(clean_ps)[0], "B105-5 fails on a clean fixture")
    expect(clean_ps["interacting"] > 0 and max(clean_ps["by_size"], default=0) >= 3
           and len(clean_ps["by_kappa"]) == len(KAPPAS),
           "seed not planted: no interacting package, no package of three, or a kappa missing")
    for kw, what in ((dict(mutate_pshift="diag"), "the off-diagonal of H_F dropped"),
                     (dict(mutate_pshift="unweighted"), "W_F dropped"),
                     (dict(mutate_pshift="slip"), "the package moves off by one part in a million"),
                     (dict(mutate_wshare="plain"), "(1 - kappa) h_e for the weakened share"),
                     (dict(mutate_wshare="nokappa"), "the share left where it was")):
        expect(not judge_pshift(shifts_on(**kw)[1])[0], f"B105-5 passes with {what}")
    expect(not judge_pshift(dict(clean_ps, interacting=0))[0],
           "B105-5 passes on a run with no interacting package")
    expect(not judge_pshift(dict(clean_ps, by_size={2: clean_ps["packages"]}))[0],
           "B105-5 passes on a run with no package of three edges or more")
    expect(not judge_pshift(dict(clean_ps, by_kappa={KAPPAS[0]: clean_ps["weakened"]}))[0],
           "B105-5 passes on a run that weakens at one fraction only")
    # known answers: a triangle of equal weights passes two thirds of a moved term to its pair,
    # and a bridge passes all of it and leaves its residual where it was
    tri = [(0, 1), (1, 2), (2, 0)]
    w = np.ones(3)
    om = np.array([0.4, -0.3, 0.2])
    base = base_fit(3, tri, w, om)
    phi2, _, _, _ = B103.fit(3, tri, w, om + np.array([DELTA, 0.0, 0.0]))
    b = B103.unit(3, 0, 1)
    expect(abs(float(b @ (phi2 - base["phi"])) - 2.0 * DELTA / 3.0) <= 1e-12,
           "a triangle of equal weights does not pass two thirds of a moved term")
    rec = shift_one(3, tri, w, om, base, 0, DELTA, cut_level=cut_one(3, tri, w, om, base, 0)["level_after"])
    expect(rec["recovered"] and abs(rec["rec_scale"] - 3.0) <= 1e-9 and rec["rec_err"] <= 1e-12,
           "the residual recovered on a triangle of equal weights is off, or its error is not read "
           "divided by 1/(1 - h_e) = 3")
    path = [(0, 1), (1, 2)]
    w = np.array([1.3, 0.6])
    om = np.array([0.5, -0.2])
    base = base_fit(3, path, w, om)
    row = shift_one(3, path, w, om, base, 0, DELTA)
    expect(row["bridge"] and row["abs_err"] <= 1e-12 and abs(row["h"] - 1.0) <= 1e-12,
           "a bridge does not pass the whole of a moved term")

    # the floor: cuts that should move nothing move by float noise only
    rng = np.random.default_rng(5)
    edges, _ = B103.random_connected(rng, 12, 0.3)
    w = np.exp(rng.normal(0.0, 1.0, len(edges)))
    om = rng.normal(0.0, 1.0, len(edges))
    base = base_fit(12, edges, w, om)
    nb = [k for k in range(len(edges)) if not cut_one(12, edges, w, om, base, k)["bridge"]]
    expect(len(nb) >= 2 and null_cut(12, edges, w, om, nb[0], offset=1.0) > 1e-3,
           "the floor does not move when the cut term is set off the level the rest gives")
    expect(len(nb) >= 2 and null_cut(12, edges, w, om, nb[0]) <= 1e-11
           and null_package(12, edges, w, om, nb[:2]) <= 1e-11,
           "a cut that should move nothing moves")
    expect(len(nb) >= 2 and null_weak(12, edges, w, om, nb[0], KAPPAS[-1], offset=1.0) > 1e-3
           and null_weak(12, edges, w, om, nb[0], KAPPAS[-1]) <= 1e-11,
           "a weakening that should move nothing moves, or the floor does not move off that level")
    expect(len(nb) >= 1 and null_shift(12, edges, w, om, base) <= 1e-11
           and null_shift(12, edges, w, om, base, k=nb[0], offset=1.0) > 1e-3,
           "a move of every term along a potential difference moves the potentials by more "
           "than that potential, or the floor does not move off it")

    for f in fails:
        print(f"SELFTEST FAIL  {f}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


# ------------------------------------------------- the run

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    t0 = time.perf_counter()
    es, ep, ew = new_single(), new_package(), new_weak()
    es4, ep5 = new_shift(), new_pshift()
    run_enumeration(np.random.default_rng(a.seed + 0), MAX_ENUM_N, MAX_TRIPLE_N, es, ep,
                    weaks=ew, shifts=es4, pshifts=ep5)
    rs, rp, rw = new_single(), new_package(), new_weak()
    rs4, rp5 = new_shift(), new_pshift()
    run_random(np.random.default_rng(a.seed + 1), SIZES, GRAPHS_PER_SIZE, rs, rp, weaks=rw,
               shifts=rs4, pshifts=rp5)

    ok1e, w1e, m1e = judge_single(es)
    ok1r, w1r, m1r = judge_single(rs)
    ok2e, w2e, m2e = judge_package(ep)
    ok2r, w2r, m2r = judge_package(rp)
    ok3e, w3e = judge_weak(ew)
    ok3r, w3r = judge_weak(rw)
    ok4e, w4e = judge_shift(es4)
    ok4r, w4r = judge_shift(rs4)
    ok5e, w5e = judge_pshift(ep5)
    ok5r, w5r = judge_pshift(rp5)
    ses4, srs4, sep5, srp5 = summary_shift(es4), summary_shift(rs4), summary_pshift(ep5), summary_pshift(rp5)
    ses, srs, sep, srp = summary_single(es), summary_single(rs), summary_package(ep), summary_package(rp)
    sew, srw = summary_weak(ew), summary_weak(rw)
    print(f"one cut: enumeration {ses['cuts']} ({ses['bridges']} bridges), random {srs['cuts']} "
          f"({srs['bridges']} bridges)")
    print(f"B105-1  bridge calls mismatched {m1e} and {m1r}; worst closed-form error over the "
          f"amplification {w1e:.2e} and {w1r:.2e} (unscaled {es['worst_abs']:.2e} and "
          f"{rs['worst_abs']:.2e}); floor {es['floor']:.2e} and {rs['floor']:.2e}")
    print(f"packages: enumeration {sep['packages']} {sep['packages_by_size']}, random "
          f"{srp['packages']} {srp['packages_by_size']}")
    print(f"B105-2  disconnection calls mismatched {m2e} and {m2r}; worst closed-form error "
          f"over the norm {w2e:.2e} and {w2r:.2e} (unscaled {ep['worst_abs']:.2e} and "
          f"{rp['worst_abs']:.2e}); floor {ep['floor']:.2e} and {rp['floor']:.2e}")
    print(f"weakenings: enumeration {sew['weakenings']} ({sew['bridges_weakened']} of bridges), "
          f"random {srw['weakenings']} ({srw['bridges_weakened']} of bridges)")
    print(f"B105-3  worst closed-form error over the amplification {w3e:.2e} and {w3r:.2e} "
          f"(unscaled {ew['worst_abs']:.2e} and {rw['worst_abs']:.2e}); floor {ew['floor']:.2e} "
          f"and {rw['floor']:.2e}")
    print(f"term moves: enumeration {ses4['term_moves']} ({ses4['of_bridges']} of bridges), "
          f"random {srs4['term_moves']} ({srs4['of_bridges']} of bridges)")
    print(f"B105-4  worst closed-form error {es4['worst']:.2e} and {rs4['worst']:.2e}; worst "
          f"recovered residual over the larger of 1/h and 1/(1 - h) {es4['rec_worst']:.2e} and "
          f"{rs4['rec_worst']:.2e}; floor {es4['floor']:.2e} and {rs4['floor']:.2e}")
    print(f"B105-5  worst package move error {ep5['worst']:.2e} and {rp5['worst']:.2e}; worst "
          f"weakened share error {ep5['w_worst']:.2e} and {rp5['w_worst']:.2e}")

    criteria = [{
        "name": "B105-1", "kind": "own_reading", "passed": bool(ok1e and ok1r),
        "statement": "a relation's leverage h_e = w_e R is one exactly when it is a bridge, "
                     "and otherwise cutting it leaves its two ends at the relative level "
                     "omega_e - r_e / (1 - h_e), moves every potential by "
                     "-(w_e r_e / (1 - h_e)) u and lowers rho^2 by w_e r_e^2 / (1 - h_e), "
                     "all read on the graph before the cut",
        "detail": (f"every connected labelled graph on 2 to {MAX_ENUM_N} vertices with random "
                   f"weights and terms, every edge cut once ({ses['cuts']} cuts, "
                   f"{ses['bridges']} of them bridges), and {srs['cuts']} cuts on sparse random "
                   f"connected graphs of {', '.join(map(str, SIZES))} vertices "
                   f"({srs['bridges']} bridges). A leverage within {TOL_EDGE:.0e} of one calls "
                   f"a bridge, mismatches {m1e} and {m1r}. On every other cut the three closed "
                   f"forms match a second fit on the graph after the cut to within {TOL:.0e} "
                   f"times the amplification 1/(1 - h_e). "
                   f"{ses['non_bridges_with_leverage_above_half']} of {ses['non_bridges']} and "
                   f"{srs['non_bridges_with_leverage_above_half']} of {srs['non_bridges']} "
                   f"non-bridges have leverage above one half, where the rewrite exceeds the "
                   f"residual seen before the cut; the amplification has median "
                   f"{ses['median_amplification']:.3g} and {srs['median_amplification']:.3g} "
                   f"and reaches {ses['largest_amplification']:.3g} and "
                   f"{srs['largest_amplification']:.3g}")}, {
        "name": "B105-2", "kind": "own_reading", "passed": bool(ok2e and ok2r),
        "statement": "cutting a package F disconnects the graph exactly when "
                     "det(I - H_F) = 0, and otherwise the gaps it leaves on F are "
                     "W_F^{-1/2} (I - H_F)^{-1} W_F^{1/2} r_F, every potential moves by "
                     "-L^+ B_F' W_F times those gaps and rho^2 falls by r_F' W_F times them",
        "detail": (f"every pair of edges of every connected labelled graph on 2 to "
                   f"{MAX_ENUM_N} vertices and every triple on 2 to {MAX_TRIPLE_N} "
                   f"({sep['packages_by_size'].get('2', 0)} pairs and "
                   f"{sep['packages_by_size'].get('3', 0)} triples), and {srp['packages']} "
                   f"packages on the random graphs "
                   f"({', '.join(f'{v} of {k} edges' for k, v in srp['packages_by_size'].items())}). det(I - H_F) within {TOL_EDGE:.0e} of zero "
                   f"calls a disconnecting package, mismatches {m2e} and {m2r}; "
                   f"{sep['disconnecting']} and {srp['disconnecting']} packages disconnect, "
                   f"and {sep['disconnecting_with_every_member_replaceable']} and "
                   f"{srp['disconnecting_with_every_member_replaceable']} of them do so with "
                   f"every member's leverage below one. On the "
                   f"{sep['connected_after']} and {srp['connected_after']} packages that leave "
                   f"the graph connected the three closed forms match a second fit to within "
                   f"{TOL:.0e} times the norm of (I - H_F)^{{-1}}; "
                   f"{sep['connected_after_with_interacting_members']} and "
                   f"{srp['connected_after_with_interacting_members']} of them have members "
                   f"that interact through H_F's off-diagonal")}, {
        "name": "B105-3", "kind": "own_reading", "passed": bool(ok3e and ok3r),
        "statement": "weakening a relation to the weight (1 - kappa) w_e, 0 < kappa < 1, "
                     "leaves its two ends at the relative level omega_e - r_e / (1 - kappa h_e), "
                     "moves every potential by -(kappa w_e r_e / (1 - kappa h_e)) u and lowers "
                     "rho^2 by kappa w_e r_e^2 / (1 - kappa h_e), all read on the graph before "
                     "the weakening; kappa = 1 is the cut of B105-1",
        "detail": (f"every edge of every connected labelled graph on 2 to {MAX_ENUM_N} vertices, "
                   f"and every edge of the random graphs of {', '.join(map(str, WEAK_SIZES))} "
                   f"vertices, weakened at kappa = {', '.join(f'{k:g}' for k in KAPPAS)} "
                   f"({sew['weakenings']} and {srw['weakenings']} weakenings, "
                   f"{sew['bridges_weakened']} and {srw['bridges_weakened']} of them of bridges, "
                   f"which carry no residual and move nothing). The three closed forms match a "
                   f"second fit on the weakened graph to within {TOL:.0e} times the "
                   f"amplification 1/(1 - kappa h_e); "
                   f"{sew['weakenings_with_kappa_times_leverage_above_half']} and "
                   f"{srw['weakenings_with_kappa_times_leverage_above_half']} of them have "
                   f"kappa h_e above one half. Off the bridges the amplification reaches "
                   f"{sew['largest_amplification_on_non_bridges']:.3g} and "
                   f"{srw['largest_amplification_on_non_bridges']:.3g}, below 1/(1 - kappa), "
                   f"which only bridges reach ({sew['largest_amplification']:.3g} at "
                   f"kappa = {max(KAPPAS):g}) and where it multiplies a residual of zero")},
    ]

    criteria.append({
        "name": "B105-4", "kind": "own_reading", "passed": bool(ok4e and ok4r),
        "statement": "moving a relation's term by Delta, with every weight and every other term "
                     "where it was, moves its two ends' relative level by h_e Delta, its residual "
                     "by (1 - h_e) Delta, every potential by w_e Delta u and rho^2 by "
                     "w_e Delta (2 r_e + (1 - h_e) Delta), and no pair of positions by more than "
                     "h_e |Delta|; the share read from two fits, with the move m of a later cut "
                     "of the same relation, returns its residual as -m (1 - h_e) / h_e",
        "detail": (f"every edge of every connected labelled graph on 2 to {MAX_ENUM_N} vertices "
                   f"and of the sparse random graphs of {', '.join(map(str, SIZES))} vertices, its "
                   f"term moved by {DELTA:g} ({ses4['term_moves']} and {srs4['term_moves']} moves, "
                   f"{ses4['of_bridges']} and {srs4['of_bridges']} of them of bridges). The level, "
                   f"the residual, the potentials and rho^2 match a second fit to within "
                   f"{TOL:.0e}, and no pair of positions moves further than h_e |Delta|; "
                   f"{ses4['with_share_below_0_1']} and {srs4['with_share_below_0_1']} moves have "
                   f"a share below {SHARE_EDGE:g}, and {ses4['non_bridges_with_share_above_0_9']} "
                   f"and {srs4['non_bridges_with_share_above_0_9']} non-bridges a share above "
                   f"{1.0 - SHARE_EDGE:g}. On every non-bridge the share read from the two fits and "
                   f"the level B105-1's cut leaves return the residual the fit leaves on the edge to "
                   f"within {TOL:.0e} times the larger of 1/h_e and 1/(1 - h_e) "
                   f"({ses4['residuals_recovered_from_a_share_and_a_cut']} and "
                   f"{srs4['residuals_recovered_from_a_share_and_a_cut']} recoveries)")})
    criteria.append({
        "name": "B105-5", "kind": "own_reading", "passed": bool(ok5e and ok5r),
        "statement": "moving the terms of a package F by Delta_F moves its members' levels by "
                     "W_F^{-1/2} H_F W_F^{1/2} Delta_F, and after a relation is weakened to "
                     "(1 - kappa) w_e its share is (1 - kappa) h_e / (1 - kappa h_e)",
        "detail": (f"every package B105-2 cuts, its terms moved by {DELTA:g} with alternating "
                   f"signs ({sep5['package_term_moves']} and {srp5['package_term_moves']} "
                   f"packages; {', '.join(f'{v} of {k}' for k, v in sep5['package_term_moves_by_size'].items())} "
                   f"edges in the enumeration and "
                   f"{', '.join(f'{v} of {k}' for k, v in srp5['package_term_moves_by_size'].items())} "
                   f"on the random graphs): the members' levels match a second fit to within "
                   f"{TOL:.0e}, and {sep5['with_interacting_members']} and "
                   f"{srp5['with_interacting_members']} of the packages have members that "
                   f"interact through H_F's off-diagonal. Every edge B105-3 weakens, at kappa = "
                   f"{', '.join(f'{k:g}' for k in KAPPAS)}, has the share "
                   f"(1 - kappa) h_e / (1 - kappa h_e) on the weakened graph to within {TOL:.0e} "
                   f"({sep5['weakened_shares']} and {srp5['weakened_shares']} shares)")})
    report = {"enumeration": {"one_cut": ses, "packages": sep, "weakening": sew,
                              "term_move": ses4, "package_terms_and_weakened_shares": sep5},
              "random_sparse": {"one_cut": srs, "packages": srp, "weakening": srw,
                                "term_move": srs4, "package_terms_and_weakened_shares": srp5},
              "compared_below": {"closed_forms": f"{TOL:.0e} times the amplification",
                                 "bridge_and_disconnection_calls": f"{TOL_EDGE:.0e}"}}

    print(f"(run took {time.perf_counter() - t0:.1f} s; not written to the record)")
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['detail'][:160]}")

    rec = {"stage": "B105",
           "config": {"seed": a.seed, "max_enum_n": MAX_ENUM_N, "max_triple_n": MAX_TRIPLE_N,
                      "sizes": list(SIZES), "graphs_per_size": GRAPHS_PER_SIZE,
                      "packages_per_graph": PACKAGES_PER_GRAPH,
                      "package_sizes": list(PACKAGE_SIZES), "extra_scale": EXTRA_SCALE,
                      "kappas": list(KAPPAS), "weak_sizes": list(WEAK_SIZES),
                      "delta": DELTA, "share_edge": SHARE_EDGE,
                      "tol": f"{TOL:.0e}", "tol_edge": f"{TOL_EDGE:.0e}",
                      "imports": ["b103_time_reachability"]},
           "criteria": criteria, "report": report}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
