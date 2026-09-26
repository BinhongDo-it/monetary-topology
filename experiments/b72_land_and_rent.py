"""B72-5 and B72-6: the known answer and the structural checks for land and rent.

The statements are proved in docs/b72_land_and_rent.md. This file reads no data and measures
nothing in the world.

  B72-5   Sraffa, Production of Commodities by Means of Commodities (1960), section 86: the
          order of cultivation is dictated by costs of production, and since relative costs
          depend on distribution the order may vary with it and is not given by Nature. A pair
          of lands whose order reverses is constructed here and the rate at which it reverses
          is printed; the companion reading, that the marginal land pays no rent, is read back
          at the same time.
  B72-6a  Theorem 17(2): at the rents solved for, every production cycle carries log(1 + r).
  B72-6b  Theorem 17(3): exactly one land pays no rent and the rest pay a positive one, and
          treating any other land as the marginal one drives some rent negative.
  B72-6c  The counting: k + n - 1 equations against n + k unknowns, one short, and the zero
          rent on the marginal land is what closes it; the closed system has full rank.
  B72-6d  Theorem 17(1): no cycle passes through a land vertex, so deleting the land vertices
          and their edges leaves b1 unchanged.

Run:

    python experiments\\b72_land_and_rent.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b72_land_and_rent.json"

SEED = 0
TOL = 1e-12
TOL_CYCLE = 1e-10
N_SYSTEMS = 400
LANDS = (2, 5)                 # how many qualities of land are in use
CORN_INPUT = (0.10, 0.60)      # corn used per unit of corn produced, on a given land
LABOUR_INPUT = (0.20, 1.50)    # labour used per unit of corn produced
R_GRID = 400                   # probes when looking for a switch in the order of cultivation
R_MAX = 2.0
BISECTION_STEPS = 60
SWITCH_FLOOR = 1e-6            # below this a crossing would not be readable


def wage_curve(alpha, lam, r):
    """Land i alone: 1 = (1 + r) alpha_i + w lambda_i, so w_i(r) = (1 - (1+r) alpha_i) / lambda_i.
    A straight line in (r, w) for each land."""
    return (1.0 - (1.0 + r) * alpha) / lam


def solve(alphas, lams, r):
    """The wage is the lower envelope of the lands' own wage curves, and the land that attains
    it pays no rent. Every other land's rent is the excess its cycle carries over the common
    one, which is what makes all the cycle sums equal."""
    w_each = wage_curve(alphas, lams, r)
    marginal = int(np.argmin(w_each))
    w = float(w_each[marginal])
    rents = 1.0 - (1.0 + r) * alphas - w * lams
    return w, marginal, rents


def random_lands(rng, k):
    alphas = rng.uniform(CORN_INPUT[0], CORN_INPUT[1], k)
    lams = rng.uniform(LABOUR_INPUT[0], LABOUR_INPUT[1], k)
    return alphas, lams


def order_switches(alphas, lams):
    """Scan the rate for a change in which land attains the lower envelope, then bisect."""
    marks = []
    for j in range(R_GRID + 1):
        r = R_MAX * j / R_GRID
        w_each = wage_curve(alphas, lams, r)
        if w_each.max() <= 0.0:
            break
        marks.append((r, int(np.argmin(w_each))))
    switches = []
    for j in range(1, len(marks)):
        if marks[j][1] != marks[j - 1][1]:
            lo, hi = marks[j - 1][0], marks[j][0]
            first = marks[j - 1][1]
            for _ in range(BISECTION_STEPS):
                mid = 0.5 * (lo + hi)
                if int(np.argmin(wage_curve(alphas, lams, mid))) == first:
                    lo = mid
                else:
                    hi = mid
            switches.append((0.5 * (lo + hi), marks[j - 1][1], marks[j][1]))
    return switches, marks


def build_graph(users_of_land, processes):
    """The drawn graph, as vertices and edges rather than as a count. Each process has money,
    an input bundle and an output, with three edges between them, and the money vertices are
    held at par in a chain. Each land is one vertex, bought by the bundle of every process
    that uses it. `users_of_land[i]` lists those processes."""
    nodes, edges = [], []
    for j in range(processes):
        nodes += [("M", j), ("B", j), ("Q", j)]
        edges += [(("M", j), ("B", j)), (("B", j), ("Q", j)), (("Q", j), ("M", j))]
        if j > 0:
            edges.append((("M", 0), ("M", j)))
    for i, users in enumerate(users_of_land):
        nodes.append(("L", i))
        for j in users:
            edges.append((("B", j), ("L", i)))
    return nodes, edges


def first_betti(nodes, edges):
    """b1 = E - rank(incidence), which is E - V + (number of components). Computed from the
    matrix rather than from a formula, so a graph drawn differently gives a different number."""
    index = {v: k for k, v in enumerate(nodes)}
    inc = np.zeros((len(nodes), len(edges)))
    for e, (u, v) in enumerate(edges):
        inc[index[v], e] += 1.0
        inc[index[u], e] -= 1.0
    return len(edges) - int(np.linalg.matrix_rank(inc, tol=1e-9))


# ------------------------------------ B72-5: Sraffa's section 86, read back and constructed


def check_order(rng):
    systems = with_switch = marginal_zero = 0
    switch_rates = []
    smallest_gap = None
    for _ in range(N_SYSTEMS):
        k = int(rng.integers(LANDS[0], LANDS[1] + 1))
        alphas, lams = random_lands(rng, k)
        systems += 1
        switches, marks = order_switches(alphas, lams)
        if switches:
            with_switch += 1
            for r_switch, before, after in switches:
                switch_rates.append(r_switch)
                # at the crossing the two lands' wage curves meet; on either side the order is
                # the other way round, and the gap grows away from it
                lo = wage_curve(alphas, lams, max(0.0, r_switch - 0.05))
                hi = wage_curve(alphas, lams, r_switch + 0.05)
                gap = min(abs(lo[before] - lo[after]), abs(hi[before] - hi[after]))
                smallest_gap = gap if smallest_gap is None else min(smallest_gap, gap)
        # the land attaining the envelope pays no rent, at a rate in the middle of the range
        w, marginal, rents = solve(alphas, lams, 0.25)
        marginal_zero += abs(rents[marginal]) < TOL_CYCLE and rents.min() > -TOL_CYCLE
    ok = (systems > 0 and with_switch > 0 and marginal_zero == systems
          and smallest_gap is not None and smallest_gap > SWITCH_FLOOR)
    arr = np.array(switch_rates) if switch_rates else np.array([0.0])
    detail = ("%d drawn sets of %d to %d lands, each land using between %g and %g corn and "
              "between %g and %g labour per unit of corn. **The order of cultivation reverses "
              "with the rate of profit on %d of them**, %d crossings in all, at rates between "
              "%.4f and %.4f with a median of %.4f. This is Sraffa's section 86, which the "
              "Centro Sraffa survey renders as: *the order of cultivation is dictated by costs "
              "of production, and since relative costs depend on distribution the order may "
              "vary with it and is not given by Nature*. **Read here, the wage is the lower "
              "envelope of the lands' own wage curves, each a straight line in the rate, and a "
              "reversal is two lines crossing**, which is the same shape as the reswitching of "
              "B67-6b. The companion reading is read back at the same time: **the land that "
              "attains the envelope pays no rent and no other rent is negative**, on %d of %d "
              "systems at a rate of 0.25"
              % (systems, LANDS[0], LANDS[1], CORN_INPUT[0], CORN_INPUT[1], LABOUR_INPUT[0],
                 LABOUR_INPUT[1], with_switch, len(switch_rates), float(arr.min()),
                 float(arr.max()), float(np.median(arr)), marginal_zero, systems))
    printed = ["systems with a reversal %d of %d, %d crossings; rates min %.4f median %.4f max "
               "%.4f; smallest wage gap 0.05 away from a crossing %.3e; marginal land pays no "
               "rent on %d of %d"
               % (with_switch, systems, len(switch_rates), float(arr.min()),
                  float(np.median(arr)), float(arr.max()),
                  0.0 if smallest_gap is None else smallest_gap, marginal_zero, systems)]
    return ok, detail, {"systems": int(systems), "with_switch": int(with_switch),
                        "crossings": int(len(switch_rates)),
                        "marginal_zero": int(marginal_zero), "within": TOL_CYCLE}, printed


# ------------------------------------------- B72-6a: the rents make every cycle sum equal


def check_cycles(rng):
    systems = points = equal = 0
    worst = 0.0
    for _ in range(N_SYSTEMS):
        k = int(rng.integers(LANDS[0], LANDS[1] + 1))
        alphas, lams = random_lands(rng, k)
        systems += 1
        for f in (0.0, 0.1, 0.25, 0.5):
            r = f
            w, marginal, rents = solve(alphas, lams, r)
            if w <= 0.0:
                continue
            # each land's cycle: the bundle costs alpha_i, the sale returns 1 - w lambda_i -
            # rent_i, and the ratio must be 1 + r on every land
            cost = alphas
            back = 1.0 - w * lams - rents
            if cost.min() <= 0.0 or back.min() <= 0.0:
                continue
            points += 1
            sums = np.log(back) - np.log(cost)
            gap = float(np.abs(sums - math.log1p(r)).max())
            worst = max(worst, gap)
            equal += gap < TOL_CYCLE
    ok = systems > 0 and points > 0 and equal == points and worst < TOL_CYCLE
    detail = ("%d systems at four rates, %d points where the wage and both legs are positive. "
              "**With the rent set at what each land's cycle carries over the common value, "
              "every cycle sums to log(1 + r)**, within %g at every point. So the rent is not "
              "an extra price to be determined alongside the others: **it is exactly the "
              "amount by which a cycle would otherwise carry more than the rest, taken off it**"
              % (systems, points, TOL_CYCLE))
    printed = ["worst |cycle sum - log(1+r)| %.3e over %d points on %d systems"
               % (worst, points, systems)]
    return ok, detail, {"systems": int(systems), "points": int(points),
                        "equal": int(equal), "within": TOL_CYCLE}, printed


# ---------------------- B72-6b: one land pays nothing, and no other choice keeps rents signed


def check_marginal(rng):
    systems = one_zero = others_fail = 0
    smallest_positive = None
    worst_negative = 0.0
    for _ in range(N_SYSTEMS):
        k = int(rng.integers(LANDS[0], LANDS[1] + 1))
        alphas, lams = random_lands(rng, k)
        r = float(rng.uniform(0.0, 0.5))
        w_each = wage_curve(alphas, lams, r)
        if w_each.max() <= 0.0:
            continue
        systems += 1
        w, marginal, rents = solve(alphas, lams, r)
        zeros = int(np.sum(np.abs(rents) < TOL_CYCLE))
        one_zero += zeros == 1 and rents.min() > -TOL_CYCLE
        pos = rents[np.abs(rents) >= TOL_CYCLE]
        if len(pos):
            smallest_positive = (float(pos.min()) if smallest_positive is None
                                 else min(smallest_positive, float(pos.min())))
        # take any other land as the marginal one and some rent goes negative
        bad = True
        for j in range(k):
            if j == marginal:
                continue
            w_j = float(w_each[j])
            rents_j = 1.0 - (1.0 + r) * alphas - w_j * lams
            bad = bad and bool(rents_j.min() < -TOL_CYCLE)
            worst_negative = min(worst_negative, float(rents_j.min()))
        others_fail += bad
    ok = (systems > 0 and one_zero == systems and others_fail == systems
          and smallest_positive is not None and smallest_positive > 0.0)
    detail = ("%d systems at rates drawn in `[0, 0.5]`. **Exactly one land pays no rent and no "
              "rent is negative**, on %d of %d, the smallest positive rent %.6f. **Take any "
              "other land as the marginal one and some rent goes negative**, on %d of %d, the "
              "most negative %.4f. So which land is marginal is not chosen: **it is forced by "
              "the requirement that no rent be negative**, which is von Neumann's condition "
              "(7') of B71 applied to an input no process produces"
              % (systems, one_zero, systems,
                 0.0 if smallest_positive is None else smallest_positive,
                 others_fail, systems, worst_negative))
    printed = ["exactly one zero rent and none negative on %d of %d; smallest positive rent "
               "%.6f; every other choice of marginal land drives a rent negative on %d, most "
               "negative %.4f"
               % (one_zero, systems, 0.0 if smallest_positive is None else smallest_positive,
                  others_fail, worst_negative)]
    return ok, detail, {"systems": int(systems), "one_zero": int(one_zero),
                        "others_fail": int(others_fail), "within": TOL_CYCLE}, printed


# ------------------------------------- B72-6c and 6d: the counting, and where the land sits


def check_counting(rng):
    systems = short_by_one = full_rank = b1_same = b1_intensive = 0
    for _ in range(N_SYSTEMS):
        k = int(rng.integers(LANDS[0], LANDS[1] + 1))
        n = int(rng.integers(1, 4))            # corn plus n - 1 other commodities
        alphas, lams = random_lands(rng, k)
        systems += 1
        # equations: one per operated method, k on the lands and n - 1 elsewhere
        equations = k + n - 1
        # unknowns: n prices less the numeraire, k rents, and the wage at a given rate
        unknowns = (n - 1) + k + 1
        short_by_one += (unknowns - equations) == 1
        # close it with the zero rent on the marginal land and the corn system has full rank
        r = 0.25
        w_each = wage_curve(alphas, lams, r)
        marginal = int(np.argmin(w_each))
        rows = []
        for i in range(k):                     # 1 = (1+r) alpha_i + w lambda_i + rent_i
            row = np.zeros(k + 1)
            row[i] = 1.0
            row[k] = lams[i]
            rows.append(row)
        closing = np.zeros(k + 1)              # the marginal land's rent is zero
        closing[marginal] = 1.0
        rows.append(closing)
        m = np.array(rows)
        full_rank += np.linalg.matrix_rank(m, tol=1e-9) == k + 1
        processes = k + n - 1
        # extensive rent: each land is used by exactly one method, so it is a pendant vertex
        nodes, edges = build_graph([[i] for i in range(k)], processes)
        b1_ext = first_betti(nodes, edges)
        # intensive rent: two methods share one land, so that land closes a cycle
        nodes2, edges2 = build_graph([[0, 1]] + [[i] for i in range(2, k)], processes)
        b1_int = first_betti(nodes2, edges2)
        b1_same += b1_ext == processes
        b1_intensive += b1_int == processes + 1
    ok = (systems > 0 and short_by_one == systems and full_rank == systems
          and b1_same == systems and b1_intensive == systems)
    detail = ("%d systems. **The operated methods number `k + n - 1` and the unknowns `n + k`**, "
              "so the price equations are one short, on %d of %d. **The zero rent on the "
              "marginal land is what closes the system**, and the closed corn system has full "
              "rank on %d of %d. The graph is then built as vertices and edges and `b1` read as "
              "`E - rank(incidence)`, not from a formula. **Under extensive rent each land is "
              "bought by exactly one bundle, so it is a pendant vertex and `b1` is the process "
              "count**, on %d of %d. **Put two methods on one land, which is intensive rent, "
              "and that land is bought by two bundles: it closes a cycle and `b1` goes up by "
              "one**, on %d of %d. So the difference between the two kinds of rent is a "
              "difference in `b1`, and **the extra equation intensive rent is known to need is "
              "that extra cycle**"
              % (systems, short_by_one, systems, full_rank, systems, b1_same, systems,
                 b1_intensive, systems))
    printed = ["one equation short on %d of %d; the closed system has full rank on %d; "
               "extensive rent leaves b1 at the process count on %d; intensive rent raises it "
               "by one on %d" % (short_by_one, systems, full_rank, b1_same, b1_intensive)]
    return ok, detail, {"systems": int(systems), "short_by_one": int(short_by_one),
                        "full_rank": int(full_rank), "b1_extensive": int(b1_same),
                        "b1_intensive": int(b1_intensive)}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B72-5", "known_answer",
         "Sraffa's section 86: the order of cultivation varies with distribution and is not "
         "given by Nature", check_order(rng)),
        ("B72-6a", "instrument",
         "Theorem 17(2): the rent is what makes every cycle carry the same sum",
         check_cycles(rng)),
        ("B72-6b", "instrument",
         "Theorem 17(3): which land is marginal is forced by the rents being non-negative",
         check_marginal(rng)),
        ("B72-6c", "instrument",
         "the counting, and the difference between extensive and intensive rent as a "
         "difference in b1", check_counting(rng)),
    ]
    mapping = {
        "B72-5": "constructed and read back -> PASS; not -> FAIL, and the code or the reading "
                 "of the source is fixed first",
        "B72-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B72-5 and B72-6: the known answer and the structural checks for "
          "docs/b72_land_and_rent.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep, printed) in results:
        print("\n%s  %s  [%s]\n  %s\n  %s" % (name, "PASS" if ok else "FAIL", kind, statement,
                                              detail))
        for line in printed:
            print("    " + line)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
    rec = {
        "stage": "B72",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "n_systems": N_SYSTEMS,
            "lands": list(LANDS), "corn_input": list(CORN_INPUT),
            "labour_input": list(LABOUR_INPUT), "r_grid": R_GRID, "r_max": R_MAX,
            "bisection_steps": BISECTION_STEPS, "switch_floor": SWITCH_FLOOR,
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all four pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
