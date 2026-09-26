"""B96: basics are where the vertically integrated subsystems intersect.

Two named objects that the chain had not touched. **Sraffa's basics**: a commodity is basic when
it enters, directly or indirectly, into the production of every commodity, and the classical
results are that the maximum rate of profit is fixed by the basic part alone and that a tax on a
non-basic leaves the rest of the system where it was. **Pasinetti's vertically integrated
subsystems**: for each good, the sub-economy that delivers one net unit of it with its whole chain
of inputs.

**They are the same object read twice.** A vertically integrated subsystem is the set of positions
reachable backwards from a good, and a good is basic when it is reachable backwards from every
good. **So the basics are exactly the intersection of the subsystems**, and Sraffa's chapter six
and Pasinetti's construction meet on the graph rather than in the algebra.

**The rate result carries a condition and it is a spectral one.** Block triangularity gives the
whole system's spectral radius as the larger of the core's and the non-basic block's, so the basic
part fixes the maximum rate only while the non-basic block's radius is the smaller. **The main
generator here holds it there and therefore cannot test it**, which is worth nothing on its own, so
B96-8 sweeps one non-basic's own use across that boundary and reads both sides. A good no one else
uses still caps the system when it eats enough of itself, which is Sraffa's own Appendix B case.

B69's system generator, Perron solver and labour values are imported rather than rewritten.

Run:
    python experiments/b96_basics_and_subsystems.py
    python experiments/b96_basics_and_subsystems.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import b69_okishio as B69                                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b96_basics_and_subsystems.json"

SEED = 96
N_SYSTEMS = 200
N_NONBASIC = (1, 3)            # extra non-basic goods appended to an irreducible core
NB_USES_CORE = (0.02, 0.15)
NB_OWN_USE = (0.0, 0.10)       # small on purpose: see BOUNDARY_OWN_USE and B96-8
NB_LABOUR = (0.2, 2.0)
# The classical statement needs the non-basic block's own spectral radius to stay under the
# core's, and the generator above holds it there. **An arm whose answer the generator forces
# is not an arm**, so B96-8 sweeps a single non-basic's own use across that boundary instead.
BOUNDARY_OWN_USE = np.linspace(0.02, 0.95, 40)
N_BOUNDARY = 40
TAX = 1.5                      # a tax raises a coefficient by half again
TOL = 1e-9
REACH_TOL = 0.0


def reach_matrix(A):
    """`R[i, j]` is true when good `i` enters the production of good `j` directly or not.

    `A[i, j]` is good `i` used by the process making good `j`, so one step is `A > 0` and the
    closure is that relation composed with itself until it stops growing.
    """
    n = A.shape[0]
    step = np.asarray(A) > REACH_TOL
    R = step.copy()
    for _ in range(n):
        nxt = R | (R @ step)
        if (nxt == R).all():
            return R, True
        R = nxt
    return R, bool((R | (R @ step) == R).all())


def basics_of(A):
    R, _closed = reach_matrix(A)
    return [i for i in range(A.shape[0]) if R[i].all()]


def subsystem_of(A, j):
    """Pasinetti's vertically integrated subsystem for good `j`: what one net unit calls up."""
    inv = np.linalg.inv(np.eye(A.shape[0]) - A)
    return set(np.nonzero(inv[:, j] > 1e-12)[0].tolist())


def max_rate(A):
    lam, _v = B69.perron(A)
    return (1.0 / lam - 1.0) if lam > 0.0 else None


def prices_at(A, l, r):
    """Prices with labour as the unit, `p = l [I - (1+r)A]^{-1}`."""
    try:
        inv = np.linalg.inv(np.eye(A.shape[0]) - (1.0 + r) * A)
    except np.linalg.LinAlgError:
        return None
    p = l @ inv
    return p if np.isfinite(p).all() and p.min() > 0.0 else None


def spectral_radius(A):
    return float(max(abs(np.linalg.eigvals(A)))) if A.size else 0.0


def boundary_sweep(rng, n_systems=N_BOUNDARY):
    """One non-basic whose own use runs from well under the core's spectral radius to well over.

    The classical reading, that the basic part fixes the maximum rate, is a statement about the
    larger of two spectral radii. **The main generator keeps the non-basic's under the core's,
    so on that sample the reading cannot fail**, which is worth nothing on its own. Here the
    non-basic's own use is swept across the boundary and both sides are read, including what a
    tax on the non-basic then does.
    """
    rows = []
    for _ in range(n_systems):
        core, l_core = B69.random_system(rng)
        if core is None:
            continue
        k = core.shape[0]
        rho_core = spectral_radius(core)
        uses = rng.uniform(*NB_USES_CORE, k)
        lab = float(rng.uniform(*NB_LABOUR))
        cells = []
        for own in BOUNDARY_OWN_USE:
            A = np.zeros((k + 1, k + 1))
            A[:k, :k] = core
            A[:k, k] = uses
            A[k, k] = float(own)
            if sorted(basics_of(A)) != list(range(k)):
                continue
            R_all, R_core = max_rate(A), max_rate(core)
            if R_all is None or R_core is None:
                continue
            taxed = A.copy()
            taxed[k, k] = min(taxed[k, k] * TAX, 0.99)
            cells.append({"own_use": float(own), "rho_core": rho_core,
                          "R_all": float(R_all), "R_core": float(R_core),
                          "agrees": bool(abs(R_all - R_core) < TOL),
                          "own_above_core": bool(own > rho_core),
                          "R_taxed_nonbasic": max_rate(taxed)})
        if cells:
            rows.append({"core": k, "rho_core": rho_core, "cells": cells})
    return rows


def with_nonbasics(rng):
    """An irreducible core with goods appended that use the core and are used by nobody."""
    core, l_core = B69.random_system(rng)
    if core is None:
        return None
    k = core.shape[0]
    m = int(rng.integers(*N_NONBASIC))
    n = k + m
    A = np.zeros((n, n))
    A[:k, :k] = core
    for j in range(k, n):
        A[:k, j] = rng.uniform(*NB_USES_CORE, k)
        A[j, j] = float(rng.uniform(*NB_OWN_USE))
    l = np.concatenate([l_core, rng.uniform(*NB_LABOUR, m)])
    return A, l, k, m


def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        got = with_nonbasics(rng)
        if got is None:
            continue
        A, l, k, m = got
        bs = basics_of(A)
        if sorted(bs) != list(range(k)):
            continue
        R_all, R_core = max_rate(A), max_rate(A[:k, :k])
        if R_all is None or R_core is None:
            continue
        taxed_nb = A.copy(); taxed_nb[k:, k:] *= TAX
        taxed_b = A.copy(); taxed_b[0, 0] = min(taxed_b[0, 0] * TAX + 0.01, 0.5)
        r_probe = 0.5 * max(R_all, 0.0)
        p0 = prices_at(A, l, r_probe)
        p_nb = prices_at(taxed_nb, l, r_probe)
        p_b = prices_at(taxed_b, l, r_probe)
        subs = [subsystem_of(A, j) for j in range(A.shape[0])]
        values = B69.labour_values(A, l)
        inv = np.linalg.inv(np.eye(A.shape[0]) - A)
        contents = [float(l @ inv[:, j]) for j in range(A.shape[0])]
        out.append({
            "goods": int(A.shape[0]), "basics": bs, "core": k, "non_basics": m,
            "R_all": float(R_all), "R_core": float(R_core),
            "R_taxed_nonbasic": max_rate(taxed_nb), "R_taxed_basic": max_rate(taxed_b),
            "intersection": sorted(set.intersection(*subs)),
            "subsystem_sizes": [len(s) for s in subs],
            "price_gap_nonbasic_on_basics": (None if p0 is None or p_nb is None
                                             else float(np.abs(p_nb[:k] - p0[:k]).max())),
            "price_gap_basic_on_basics": (None if p0 is None or p_b is None
                                          else float(np.abs(p_b[:k] - p0[:k]).max())),
            "value_gap": float(np.abs(np.asarray(contents) - np.asarray(values)).max()),
            "closure_settled": bool(reach_matrix(A)[1]),
            "rho_core": spectral_radius(A[:k, :k]),
            "rho_nonbasic": spectral_radius(A[k:, k:]),
        })
    return out


# ------------------------------------------------- criteria

def crit_known(sample):
    """B96-1: an irreducible system has every good basic, and the subsystem is B69's value."""
    rng = np.random.default_rng(690)
    all_basic = tried = 0
    for _ in range(15):
        A, _l = B69.random_system(rng)
        if A is None:
            continue
        tried += 1
        all_basic += int(len(basics_of(A)) == A.shape[0])
    worst_value = max((s["value_gap"] for s in sample), default=float("inf"))
    ok = tried > 0 and all_basic == tried and worst_value < 1e-9
    detail = (f"on {all_basic} of {tried} systems from B69's own generator every good is basic, "
              f"which is what an irreducible input matrix means and is the case Sraffa's chapter "
              f"six has nothing to say about. **And a vertically integrated subsystem's labour "
              f"content is the labour value**: `l [I - A]^{{-1}}` agrees with B69's own "
              f"`labour_values` to {worst_value:.2e} over {len(sample)} systems. Both anchors "
              f"are imported, so this station and B69 can disagree")
    return ok, detail, {"irreducible_tried": tried, "all_basic": all_basic,
                        "worst_value_gap": worst_value}


def crit_rate_from_basics(sample):
    """B96-2: the maximum rate is fixed by the basic part alone."""
    worst = max((abs(s["R_all"] - s["R_core"]) for s in sample), default=float("inf"))
    agree = sum(1 for s in sample if abs(s["R_all"] - s["R_core"]) < TOL)
    ok = bool(sample) and agree == len(sample)
    if not sample:
        return None, ("no system was drawn, so there is no rate to compare and no "
                      "object; not evaluated, and it lands in the third cell"), {}
    rc = [s.get("rho_core", 0.0) for s in sample]
    rn = [s.get("rho_nonbasic", 0.0) for s in sample]
    under = sum(1 for a, b in zip(rn, rc) if a < b)
    detail = (f"the maximum rate of profit of the whole economy equals that of its basic part on "
              f"{agree} of {len(sample)} systems, worst gap {worst:.2e}. **On the graph this is "
              f"block triangularity**: the non-basics use the core and the core uses none of "
              f"them, so the whole system's spectral radius is the larger of the core's and the "
              f"non-basic block's. **That makes the reading conditional and the condition is "
              f"that the non-basic block's is the smaller**, which holds here on {under} of "
              f"{len(sample)}: core radius at least {min(rc):.3f}, non-basic block at most "
              f"{max(rn):.3f}. **This generator cannot violate it**, so the count above is worth "
              f"nothing by itself and `B96-8` sweeps across the boundary instead. Sraffa states "
              f"the same condition in Appendix B for a non-basic that reproduces itself")
    return ok, detail, {"systems": len(sample), "agree": agree, "worst_gap": worst,
                        "nonbasic_radius_under_core": under,
                        "min_core_radius": min(rc) if rc else None,
                        "max_nonbasic_radius": max(rn) if rn else None}


def crit_tax(sample):
    """B96-3: a tax on a non-basic leaves the rest where it was, on a basic does not."""
    nb_same = sum(1 for s in sample
                  if s["R_taxed_nonbasic"] is not None
                  and abs(s["R_taxed_nonbasic"] - s["R_all"]) < TOL)
    b_moves = sum(1 for s in sample
                  if s["R_taxed_basic"] is not None
                  and abs(s["R_taxed_basic"] - s["R_all"]) > TOL)
    p_nb = [s["price_gap_nonbasic_on_basics"] for s in sample
            if s["price_gap_nonbasic_on_basics"] is not None]
    p_b = [s["price_gap_basic_on_basics"] for s in sample
           if s["price_gap_basic_on_basics"] is not None]
    nb_prices = sum(1 for x in p_nb if x < TOL)
    b_prices = sum(1 for x in p_b if x > TOL)
    ok = (bool(sample) and nb_same == len(sample) and b_moves == len(sample)
          and nb_prices == len(p_nb) and b_prices == len(p_b))
    if not sample:
        return None, ("no system was drawn, so there is nothing to tax and no "
                      "object; not evaluated, and it lands in the third cell"), {}
    rc = [s.get("rho_core", 0.0) for s in sample]
    rn_taxed = [min(s.get("rho_nonbasic", 0.0) * TAX, 0.99) for s in sample]
    under = sum(1 for a, b in zip(rn_taxed, rc) if a < b)
    detail = (f"raising a non-basic's own coefficient by half again leaves the maximum rate on "
              f"{nb_same} of {len(sample)} systems and leaves every basic price on {nb_prices} "
              f"of {len(p_nb)}, by less than {TOL:.0e}. **Doing the same to a basic moves the "
              f"rate on {b_moves} and the basic prices on {b_prices}**, the latter by a median "
              f"of {float(np.median(p_b)) if p_b else float('nan'):.4f}. **Both halves are "
              f"counted on the same systems**, so the contrast is not between two samples, and "
              f"the null half alone would be a check that cannot fail. **The null half is also "
              f"conditional, and on a tighter condition than `B96-2`'s**: what has to stay "
              f"under the core's radius is the non-basic block's radius after the tax, not "
              f"before it, so the boundary sits at the core's radius divided by the tax. It "
              f"holds here on {under} of {len(sample)}: core radius at least {min(rc):.3f}, "
              f"taxed non-basic block at most {max(rn_taxed):.3f}. **This generator cannot "
              f"violate it either**, so the null half's count is worth nothing by itself and "
              f"`B96-9` sweeps across that boundary instead")
    return ok, detail, {"systems": len(sample), "nonbasic_rate_same": nb_same,
                        "basic_rate_moves": b_moves, "nonbasic_prices_same": nb_prices,
                        "basic_prices_move": b_prices,
                        "median_basic_price_gap": float(np.median(p_b)) if p_b else None}


def crit_intersection(sample):
    """B96-4: the basics are exactly where the subsystems intersect."""
    agree = sum(1 for s in sample if s["intersection"] == sorted(s["basics"]))
    sizes = [n for s in sample for n in s["subsystem_sizes"]]
    lo = min(sizes) if sizes else 0
    hi = max(sizes) if sizes else 0
    ok = bool(sample) and agree == len(sample)
    detail = (f"the intersection of the vertically integrated subsystems equals the set of "
              f"basics on {agree} of {len(sample)} systems. **A subsystem is what one net unit "
              f"of a good calls up, and a good is basic when every good calls it up**, so the "
              f"two definitions are one reachability relation read along its two arguments. "
              f"**Sraffa's chapter six and Pasinetti's construction meet on the graph**, not in "
              f"the algebra. Subsystem sizes run from {lo} to {hi} goods, so "
              f"they are not all the whole economy and the intersection is not trivially "
              f"everything")
    return ok, detail, {"systems": len(sample), "agree": agree,
                        "smallest_subsystem": lo, "largest_subsystem": hi}


def crit_construction(sample):
    """B96-5: the generator really produces non-basics, which everything above needs."""
    with_nb = sum(1 for s in sample if s["non_basics"] > 0)
    proper = sum(1 for s in sample if len(s["basics"]) < s["goods"])
    counts = {}
    for s in sample:
        counts[s["non_basics"]] = counts.get(s["non_basics"], 0) + 1
    ok = (bool(sample) and with_nb == len(sample) and proper == len(sample)
          and len(counts) > 1)
    detail = (f"every one of {len(sample)} systems carries at least one non-basic and has a "
              f"basic set strictly smaller than its good set, {proper} of {len(sample)}, with "
              f"the number of non-basics distributed " +
              ", ".join(f"{k} on {v}" for k, v in sorted(counts.items())) +
              ". **Without a non-basic every statement above is vacuous**: on an irreducible "
              "system the basics are everything, the intersection is everything, and there is "
              "no non-basic to tax")
    return ok, detail, {"systems": len(sample), "with_nonbasics": with_nb,
                        "proper_subsets": proper, "counts": counts}


def crit_closure(sample):
    """B96-6: the reachability closure is a closure, and that is checked not assumed."""
    settled = sum(1 for s in sample if s["closure_settled"])
    n = 6
    chain = np.zeros((n, n))
    for i in range(n - 1):
        chain[i, i + 1] = 0.3                      # good i enters good i+1 only
    R, ok_chain = reach_matrix(chain)
    indirect = bool(R[0, n - 1])                   # reached only through the chain
    ok = bool(sample) and settled == len(sample) and ok_chain and indirect
    detail = (f"the reachability relation reaches a fixed point on {settled} of {len(sample)} "
              f"systems, checked rather than assumed by running one more step and requiring no "
              f"change. **And it is the indirect relation and not the direct one**: on a chain "
              f"of {n} goods where each enters only the next, the first is reported as entering "
              f"the last, which one step of `A > 0` would not report. **Sraffa's definition says "
              f"directly or indirectly**, and a direct-only reading would call almost nothing "
              f"basic")
    return ok, detail, {"systems": len(sample), "closure_settled": settled,
                        "chain_indirect": indirect}


def crit_spectral(boundary):
    """B96-8: the condition the classical statement needs, read on both sides of its boundary."""
    cells = [c for row in boundary for c in row["cells"]]
    below = [c for c in cells if not c["own_above_core"]]
    above = [c for c in cells if c["own_above_core"]]
    ok_below = sum(1 for c in below if c["agrees"])
    ok_above = sum(1 for c in above if not c["agrees"])
    # the boundary itself: per sweep, the largest own use that still agrees against the core
    edges = []
    for row in boundary:
        agree = [c["own_use"] for c in row["cells"] if c["agrees"]]
        if agree:
            edges.append(max(agree) - row["rho_core"])
    worst_edge = max((abs(e) for e in edges), default=float("inf"))
    step = float(BOUNDARY_OWN_USE[1] - BOUNDARY_OWN_USE[0])
    ok = (len(below) > 0 and len(above) > 0
          and ok_below == len(below) and ok_above == len(above)
          and worst_edge <= step)
    detail = (f"one non-basic's own use swept from {BOUNDARY_OWN_USE[0]:.2f} to "
              f"{BOUNDARY_OWN_USE[-1]:.2f} over {len(boundary)} cores. **Below the core's own "
              f"spectral radius the whole system's maximum rate is the core's**, on "
              f"{ok_below} of {len(below)} cells; **above it the non-basic sets the rate and "
              f"the two part**, on {ok_above} of {len(above)}. The last agreeing value sits "
              f"within one grid step ({step:.3f}) of the core's radius on every sweep, worst "
              f"{worst_edge:.3f}, **so the boundary is at the radius rather than anywhere "
              f"else**. This is what `B96-2` and `B96-3` are conditional on and what their own "
              f"generator cannot reach: a good no one else uses still caps the system when it "
              f"eats enough of itself, which is Sraffa's Appendix B case")
    return ok, detail, {"cores": len(boundary), "cells": len(cells),
                        "below": len(below), "below_agreeing": ok_below,
                        "above": len(above), "above_parting": ok_above,
                        "worst_edge_offset": worst_edge, "grid_step": step}


def crit_taxed_boundary(boundary):
    """B96-9: `B96-3`'s condition, read on both sides of the boundary the tax itself moves.

    `B96-8` sweeps the boundary the untaxed non-basic crosses. The tax raises the
    non-basic's own coefficient, so the radius that decides whether a tax on it can
    touch the maximum rate is the taxed one, and its boundary sits lower by the tax:
    at the core's radius over `TAX`. Nothing new is drawn. `boundary_sweep` has been
    computing `R_taxed_nonbasic` on every cell since it was written and no criterion
    has ever read that column.
    """
    cells = [c for row in boundary for c in row["cells"]
             if c["R_taxed_nonbasic"] is not None]
    if not cells:
        return None, ("the sweep produced no cell with a taxed rate, so there is "
                      "no object; not evaluated, and it lands in the third cell"), {}

    def taxed_radius(cell):
        return min(cell["own_use"] * TAX, 0.99)

    below = [c for c in cells if taxed_radius(c) < c["rho_core"]]
    above = [c for c in cells if taxed_radius(c) > c["rho_core"]]
    same_below = sum(1 for c in below if abs(c["R_taxed_nonbasic"] - c["R_all"]) < TOL)
    moves_above = sum(1 for c in above if abs(c["R_taxed_nonbasic"] - c["R_all"]) > TOL)
    # the boundary itself, against the place it was predicted rather than against
    # wherever the sweep happens to stop
    edges = []
    for row in boundary:
        harmless = [c["own_use"] for c in row["cells"]
                    if c["R_taxed_nonbasic"] is not None
                    and abs(c["R_taxed_nonbasic"] - c["R_all"]) < TOL]
        if harmless:
            edges.append(max(harmless) - row["rho_core"] / TAX)
    worst_edge = max((abs(e) for e in edges), default=float("inf"))
    step = float(BOUNDARY_OWN_USE[1] - BOUNDARY_OWN_USE[0])
    ok = (len(below) > 0 and len(above) > 0
          and same_below == len(below) and moves_above == len(above)
          and worst_edge <= step)
    detail = (f"the same sweep read for the tax. **Where the taxed non-basic block's radius "
              f"stays under the core's, a tax on it leaves the maximum rate exactly where it "
              f"was**, on {same_below} of {len(below)} cells; **where the tax carries it over, "
              f"the taxed non-basic sets the rate and `B96-3`'s null half is false**, on "
              f"{moves_above} of {len(above)}. The last harmless own use sits within one grid "
              f"step ({step:.3f}) of the core's radius over the tax, worst {worst_edge:.3f}, "
              f"**so this boundary is at {1.0 / TAX:.4f} of `B96-8`'s and not somewhere else**. "
              f"That factor is the tax, and it was written down before the sweep was read. "
              f"**A good no one else uses can still be the one that caps the system, and a tax "
              f"is enough to put it there**, which is Sraffa's Appendix B case reached by "
              f"taxation rather than by technique")
    return ok, detail, {"cells": len(cells), "below": len(below),
                        "below_unchanged": same_below, "above": len(above),
                        "above_moving": moves_above, "worst_edge": worst_edge,
                        "grid_step": step, "predicted_ratio_to_b96_8": 1.0 / TAX}


def crit_registration():
    """B96-7: the same round writes back to the two stations this one builds on."""
    want = ["b80_reducible.md", "b68_value_field.md"]
    missing = [f for f in want
               if "b96_basics_and_subsystems.md" not in
               (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the stations this one builds on "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}: "
              f"B80 for the reducible decomposition the basic part is a case of, and B68 for "
              f"the labour values a subsystem's content turns out to be. `D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(4)
    sample = draws(rng, 60)
    boundary = boundary_sweep(rng, 8)
    if len(sample) < 25:
        fails.append(f"the fixture drew only {len(sample)} systems")
    if not boundary:
        fails.append("the boundary sweep produced no core")

    got = crit_spectral(boundary)
    if not got[0]:
        fails.append(f"B96-8 does not pass on the fixture: {got[1][:150]}")
    if crit_spectral([])[0]:
        fails.append("B96-8 passes on an empty sweep")

    # B96-8: both sides of the boundary have to be reached, and the boundary has to sit at the
    # core's radius rather than wherever the sweep happens to stop
    for label, fn in (
            ("no cell sits above the core's radius",
             lambda row: dict(row, cells=[c for c in row["cells"] if not c["own_above_core"]])),
            ("no cell sits below it",
             lambda row: dict(row, cells=[c for c in row["cells"] if c["own_above_core"]])),
            ("a cell above the boundary still agrees",
             lambda row: dict(row, cells=[dict(c, agrees=True) for c in row["cells"]]))):
        if crit_spectral([fn(r) for r in boundary])[0]:
            fails.append(f"B96-8 passes when {label}")

    got = crit_taxed_boundary(boundary)
    if not got[0]:
        fails.append(f"B96-9 does not pass on the fixture: {got[1][:150]}")
    if crit_taxed_boundary([])[0]:
        fails.append("B96-9 passes on an empty sweep")

    # B96-9: both sides of the taxed boundary have to be reached, and that boundary has to
    # sit at the core's radius over the tax rather than at B96-8's
    def _keep(row, pred):
        return dict(row, cells=[c for c in row["cells"]
                                if c["R_taxed_nonbasic"] is None or pred(c)])
    for label, fn in (
            ("no cell sits above the taxed boundary",
             lambda row: _keep(row, lambda c: min(c["own_use"] * TAX, 0.99) < c["rho_core"])),
            ("no cell sits below it",
             lambda row: _keep(row, lambda c: min(c["own_use"] * TAX, 0.99) > c["rho_core"])),
            ("a taxed cell above the boundary still leaves the rate alone",
             lambda row: dict(row, cells=[dict(c, R_taxed_nonbasic=c["R_all"])
                                          for c in row["cells"]]))):
        if crit_taxed_boundary([fn(r) for r in boundary])[0]:
            fails.append(f"B96-9 passes when {label}")

    # B96-9 has to read a lower boundary than B96-8: if it used B96-8's, the cells
    # between the two boundaries would be counted on the wrong side
    mid = [c for row in boundary for c in row["cells"]
           if c["R_taxed_nonbasic"] is not None
           and c["own_use"] < c["rho_core"] < min(c["own_use"] * TAX, 0.99)]
    if not mid:
        fails.append("the fixture has no cell between the two boundaries, so B96-9 and "
                     "B96-8 are not separated on it")

    named = (("B96-1", crit_known), ("B96-2", crit_rate_from_basics), ("B96-3", crit_tax),
             ("B96-4", crit_intersection), ("B96-5", crit_construction),
             ("B96-6", crit_closure))
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:150]}")
        if fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B96-2: the core and the whole economy have to be able to disagree
    bent = [dict(s, R_core=s["R_core"] * 1.1) for s in sample]
    if crit_rate_from_basics(bent)[0]:
        fails.append("B96-2 passes when the core's rate differs from the whole economy's")

    # B96-3: the null half alone cannot fail, so a fixture where the basic tax also does
    # nothing has to be rejected
    flat = [dict(s, R_taxed_basic=s["R_all"], price_gap_basic_on_basics=0.0) for s in sample]
    if crit_tax(flat)[0]:
        fails.append("B96-3 passes when a tax on a basic changes nothing either")

    # B96-4: the intersection and the basics have to be able to differ
    off = [dict(s, intersection=sorted(s["basics"])[:-1]) for s in sample
           if len(s["basics"]) > 1]
    if off and crit_intersection(off)[0]:
        fails.append("B96-4 passes when the intersection is short of the basics")

    # B96-5: on an irreducible system every statement above is vacuous, and the criterion
    # exists to say the generator does not hand one back
    vac = [dict(s, non_basics=0, basics=list(range(s["goods"]))) for s in sample]
    if crit_construction(vac)[0]:
        fails.append("B96-5 passes on systems with no non-basic in them")

    # B96-6: a direct-only reading of the relation would call almost nothing basic, and the
    # chain probe is what separates the two readings
    n = 6
    chain = np.zeros((n, n))
    for i in range(n - 1):
        chain[i, i + 1] = 0.3
    direct = np.asarray(chain) > 0.0
    if bool(direct[0, n - 1]):
        fails.append("the chain fixture is reachable in one step, so it tests nothing")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} systems")
    return 1 if fails else 0


# ------------------------------------------------- main

def _crit(name, kind, ok, detail):
    """One criterion, with its third cell kept out of the two verdicts.

    A branch that finds no object to read returns None rather than False.
    Writing it as False would put it on the ledger as a reading that came out
    false, which the rule about the undecided cell forbids, and the census that
    counts failures reads a `void` field as well as the prose, so the field is
    set here rather than left to a word in the detail.
    """
    crit = {"name": name, "kind": kind, "detail": detail,
            "passed": None if ok is None else bool(ok)}
    if ok is None:
        crit["void"] = True
    return crit


def _mark(ok):
    return "NO OBJECT" if ok is None else ("PASS" if ok else "FAIL")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--systems", type=int, default=N_SYSTEMS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.systems)
    boundary = boundary_sweep(rng)
    print(f"{len(sample)} economies with a basic core and appended non-basics, and "
          f"{len(boundary)} cores swept across the spectral boundary\n")

    criteria, report = [], {}
    for name, kind, fn in (("B96-1", "known_answer", crit_known),
                           ("B96-2", "own_reading", crit_rate_from_basics),
                           ("B96-3", "own_reading", crit_tax),
                           ("B96-4", "own_reading", crit_intersection),
                           ("B96-5", "own_reading", crit_construction),
                           ("B96-6", "instrument", crit_closure)):
        ok, detail, rep = fn(sample)
        criteria.append(_crit(name, kind, ok, detail))
        report[name] = rep
        print(f"{_mark(ok)}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_spectral(boundary)
    criteria.append(_crit("B96-8", "own_reading", ok, detail))
    report["B96-8"] = rep
    print(f"{_mark(ok)}  B96-8  [own_reading]  {detail[:200]}\n")
    ok, detail, rep = crit_taxed_boundary(boundary)
    criteria.append(_crit("B96-9", "own_reading", ok, detail))
    report["B96-9"] = rep
    print(f"{_mark(ok)}  B96-9  [own_reading]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append(_crit("B96-7", "bookkeeping", ok, detail))
    report["B96-7"] = rep
    print(f"{_mark(ok)}  B96-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B96",
        "config": {"seed": args.seed, "systems": args.systems,
                   "non_basics": list(N_NONBASIC), "nb_uses_core": list(NB_USES_CORE),
                   "nb_own_use": list(NB_OWN_USE), "tax": TAX, "tol": TOL,
                   "imports": "b69_okishio"},
        "report": report,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    # An undecided cell is not a failure, so it does not set the exit code.
    bad = [c["name"] for c in criteria if c["passed"] is False]
    held = [c["name"] for c in criteria if c["passed"] is None]
    if held:
        print("no object, third cell: " + ", ".join(held))
    print(f"all {len(criteria)} criteria pass; record written" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
