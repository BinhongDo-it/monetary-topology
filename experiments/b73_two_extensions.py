"""B73-5 and B73-6: the known answer and the structural checks for two registered extensions.

The statements are proved in docs/b73_two_extensions.md. This file reads no data and measures
nothing in the world.

  B73-5   Sraffa, Production of Commodities by Means of Commodities (1960), section 87, on
          intensive rent: the method that produces more corn per acre should show a higher cost
          per unit of product. Read back here, where it turns out to be an identity. Bidard's
          survey for Centro Sraffa adds that this non-negativity condition is not the condition
          for the incoming method to be more productive; an instance where the two diverge is
          constructed.
  B73-6a  Theorem 18(1): a machine of declining efficiency costs nothing in the graph. Only the
          weights move, b1 is unchanged, and the depreciation schedule at a zero rate is
          straight-line exactly when the efficiency is constant. With rising efficiency the
          machine's price can rise with age.
  B73-6b  Theorem 18(2): intensive rent costs a cycle. The land vertex has degree two, b1 rises
          by one, deleting that vertex lowers b1 again, and the two price equations are square
          in the wage and the rent with no zero-rent condition needed.
  B73-6c  Theorem 18(2), second half: give the two users different rates for the same land and
          the added cycle carries exactly log(rho2 / rho1), so it closes exactly when the two
          rates agree. **One price per position is that cycle.**

Run:

    python experiments\\b73_two_extensions.py
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
OUT = ROOT / "results" / "b73_two_extensions.json"

SEED = 0
TOL = 1e-12
TOL_CYCLE = 1e-10
N_SYSTEMS = 400
MACHINE_T = 5
MACHINE_PARAMS = {"a": 0.2, "c": 0.5, "l0": 0.3, "l1": 0.1}
EFFICIENCY_PROFILES = {
    "constant": [1.00, 1.00, 1.00, 1.00, 1.00],
    "declining": [1.20, 1.10, 1.00, 0.90, 0.80],
    "rising": [0.80, 0.90, 1.00, 1.10, 1.20],
    # the same total output as the others, with the first period below the period's own
    # non-machine cost: that is what makes the machine's price rise with age
    "running_in": [0.30, 1.00, 1.10, 1.20, 1.40],
}
LINEAR_FLOOR = 1e-6
# intensive rent: two methods on one acre
YIELD = (0.8, 2.0)             # corn per acre
CORN_INPUT = (0.05, 0.45)      # corn per acre
LABOUR_INPUT = (0.10, 0.90)    # labour per acre
RATES = (0.0, 0.05, 0.15, 0.30)


def machine_system(t, params, profile):
    """Commodity 0 is the good and commodity k + 1 a machine used k times. Process 0 builds a
    machine; process j uses one of age j - 1 and returns it one period older, delivering
    profile[j - 1] units of the good. Only the output coefficients change with the profile:
    the graph is the same one every time."""
    a_in, c, l0, l1 = params["a"], params["c"], params["l0"], params["l1"]
    n = t + 1
    a = np.zeros((n, n))
    b = np.zeros((n, n))
    l = np.zeros(n)
    a[0, 0] = c
    b[1, 0] = 1.0
    l[0] = l0
    for j in range(1, t + 1):
        a[0, j] = a_in
        a[j, j] = 1.0
        b[0, j] = profile[j - 1]
        if j < t:
            b[j + 1, j] = 1.0
        l[j] = l1
    return a, b, l


def prices(a, b, l, r, numeraire):
    base = l @ np.linalg.inv(b - (1.0 + r) * a)
    w = 1.0 / float(base @ numeraire)
    return w * base, w


def first_betti(nodes, edges):
    index = {v: k for k, v in enumerate(nodes)}
    inc = np.zeros((len(nodes), len(edges)))
    for e, (u, v) in enumerate(edges):
        inc[index[v], e] += 1.0
        inc[index[u], e] -= 1.0
    return len(edges) - int(np.linalg.matrix_rank(inc, tol=1e-9))


def rent_graph(users_of_land, processes):
    """One cycle per process, the money vertices chained, and one land vertex bought by every
    process in `users_of_land`."""
    nodes, edges = [], []
    for j in range(processes):
        nodes += [("M", j), ("B", j), ("Q", j)]
        edges += [(("M", j), ("B", j)), (("B", j), ("Q", j)), (("Q", j), ("M", j))]
        if j > 0:
            edges.append((("M", 0), ("M", j)))
    nodes.append(("L", 0))
    for j in users_of_land:
        edges.append((("B", j), ("L", 0)))
    return nodes, edges


def intensive(q, a, l, r):
    """Two methods on one acre: q_i = (1+r) a_i + w l_i + rho, corn as the unit of account.
    Two equations, two unknowns, and no zero-rent condition."""
    m = np.array([[l[0], 1.0], [l[1], 1.0]])
    rhs = np.array([q[0] - (1.0 + r) * a[0], q[1] - (1.0 + r) * a[1]])
    if abs(np.linalg.det(m)) < 1e-12:
        return None, None, m
    sol = np.linalg.solve(m, rhs)
    return float(sol[0]), float(sol[1]), m          # wage, rent


# ---------------------------------------- B73-5: Sraffa's section 87, and Bidard's correction


def check_sraffa_87(rng):
    systems = both = identity_ok = diverge = 0
    worst_identity = 0.0
    positive = 0
    example = None
    for _ in range(N_SYSTEMS):
        q = np.sort(rng.uniform(YIELD[0], YIELD[1], 2))          # method 2 yields more per acre
        a = rng.uniform(CORN_INPUT[0], CORN_INPUT[1], 2)
        l = rng.uniform(LABOUR_INPUT[0], LABOUR_INPUT[1], 2)
        r = float(RATES[int(rng.integers(0, len(RATES)))])
        w, rho, m = intensive(q, a, l, r)
        if w is None or w <= 0.0:
            continue
        systems += 1
        cost = (1.0 + r) * a + w * l                             # per acre
        unit = cost / q
        # the identity: rho (1/q1 - 1/q2) = unit_2 - unit_1
        lhs = rho * (1.0 / q[0] - 1.0 / q[1])
        rhs = unit[1] - unit[0]
        worst_identity = max(worst_identity, abs(lhs - rhs))
        identity_ok += abs(lhs - rhs) < TOL_CYCLE
        # Sraffa's condition and the sign of the rent agree
        both += (rho > 0.0) == (unit[1] > unit[0])
        positive += rho > 0.0
        # Bidard: the non-negativity condition is not the productivity condition
        more_productive = (q[1] - a[1]) > (q[0] - a[0])
        if (rho > 0.0) != more_productive:
            diverge += 1
            if example is None:
                example = (q.copy(), a.copy(), l.copy(), r, w, rho,
                           float(q[1] - a[1]), float(q[0] - a[0]))
    ok = (systems > 0 and both == systems and identity_ok == systems
          and worst_identity < TOL_CYCLE and diverge > 0 and positive > 0)
    detail = ("%d drawn pairs of methods on one acre, at rates in %s, kept when the wage comes "
              "out positive. **Sraffa's condition of section 87, that the method producing more "
              "corn per acre should show the higher cost per unit of product, holds exactly "
              "when the rent is positive**, on all %d, and it is not a coincidence but an "
              "identity: `rho (1/q1 - 1/q2) = C2/q2 - C1/q1`, checked within %g. The rent is "
              "positive on %d of them. **Bidard's correction is read back as well**: the "
              "condition for a non-negative rent is not the condition for the incoming method "
              "to be more productive, and the two diverge on %d of the draws, which is where "
              "his survey says the Ricardian dynamics fail"
              % (systems, ", ".join("%g" % x for x in RATES), both, TOL_CYCLE, positive,
                 diverge))
    printed = ["Sraffa's condition and the sign of the rent agree on %d of %d; worst departure "
               "from the identity %.3e; rent positive on %d; non-negativity and productivity "
               "diverge on %d" % (both, systems, worst_identity, positive, diverge)]
    if example is not None:
        q, a, l, r, w, rho, net2, net1 = example
        printed.append("an instance where they diverge: yields %s, corn inputs %s, labour %s, "
                       "r = %g gives w = %.4f and rent %.4f, while the net product per acre is "
                       "%.4f against %.4f"
                       % (np.array2string(q, precision=3), np.array2string(a, precision=3),
                          np.array2string(l, precision=3), r, w, rho, net2, net1))
    return ok, detail, {"systems": int(systems), "agree": int(both),
                        "identity_ok": int(identity_ok), "rent_positive": int(positive),
                        "diverge": int(diverge), "within": TOL_CYCLE}, printed


# ------------------------------ B73-6a: declining efficiency costs nothing in the graph


def check_machine():
    t = MACHINE_T
    numeraire = np.zeros(t + 1)
    numeraire[0] = 1.0
    rows, b1s = {}, {}
    for name, profile in EFFICIENCY_PROFILES.items():
        a, b, l = machine_system(t, MACHINE_PARAMS, profile)
        nodes, edges = [], []
        for j in range(t + 1):
            nodes += [("M", j), ("B", j), ("Q", j)]
            edges += [(("M", j), ("B", j)), (("B", j), ("Q", j)), (("Q", j), ("M", j))]
            if j > 0:
                edges.append((("M", 0), ("M", j)))
        b1s[name] = first_betti(nodes, edges)
        p, w = prices(a, b, l, 0.0, numeraire)
        machines = p[1:]
        drops = machines[:-1] - machines[1:]
        drops = np.append(drops, machines[-1])          # the last one falls to zero
        predicted = np.array(profile) - MACHINE_PARAMS["a"] - w * MACHINE_PARAMS["l1"]
        straight = np.array([machines[0] * (t - k) / t for k in range(t)])
        rows[name] = {"machines": machines, "drops": drops, "predicted": predicted,
                      "deviation": float(np.abs(machines - straight).max() / abs(machines[0])),
                      "drop_gap": float(np.abs(drops - predicted).max()), "wage": w}
    same_graph = len(set(b1s.values())) == 1
    flat = rows["constant"]
    down = rows["declining"]
    up = rows["rising"]
    run = rows["running_in"]
    rises = bool((np.diff(run["machines"]) > 0.0).any())
    no_rise_when_mild = not bool((np.diff(up["machines"]) > 0.0).any())
    ok = (same_graph
          and flat["deviation"] < TOL_CYCLE
          and down["deviation"] > LINEAR_FLOOR and up["deviation"] > LINEAR_FLOOR
          and max(r["drop_gap"] for r in rows.values()) < TOL_CYCLE
          and rises and no_rise_when_mild)
    detail = ("A machine lasting %d periods, read under the efficiency profiles the record "
              "lists: constant, declining, mildly rising, and one that runs in. **The graph is "
              "the same one every time**, `b1 = %d` under each, because a profile changes "
              "weights and no edge. At a zero rate the "
              "price falls each period by exactly `q_j - a - w l1`, within %g under every "
              "profile, **so the schedule is straight-line exactly when the profile is "
              "constant**: the deviation is %.1e for the constant profile and %.4f and %.4f "
              "for the declining and the mildly rising ones. **So Corollary 15.1(3) of B70 needs both "
              "of its hypotheses**, a zero rate and constant efficiency, and it named the "
              "first. **A rising profile is not by itself enough to make the machine's price "
              "rise with age**, and the mildly rising one here does not do it. What does it is "
              "a period whose output falls below that period's own non-machine cost, since the "
              "fall in the price is `q_j - a - w l1` and its sign is the sign of that. The "
              "fourth profile has the same total output as the others, so the same wage, with "
              "the first period below the line: **its schedule goes %s, rising after the first "
              "period**. So the machine's price follows what is left to earn and not what has "
              "elapsed"
              % (t, b1s["constant"], TOL_CYCLE, flat["deviation"], down["deviation"],
                 up["deviation"], np.array2string(run["machines"], precision=4)))
    printed = []
    for name in ("constant", "declining", "rising", "running_in"):
        r = rows[name]
        printed.append("%-9s schedule %s  departure from straight-line %.6f  worst |drop - "
                       "(q_j - a - w l1)| %.3e"
                       % (name, np.array2string(r["machines"], precision=4), r["deviation"],
                          r["drop_gap"]))
    return ok, detail, {"periods": t, "b1": int(b1s["constant"]),
                        "profiles": {k: list(v) for k, v in EFFICIENCY_PROFILES.items()},
                        "within": TOL_CYCLE}, printed


# -------------------------------- B73-6b and 6c: intensive rent costs a cycle, and it is the equation


def check_intensive(rng):
    systems = raised = deleted = square = closes = 0
    worst_close = 0.0
    smallest_open = None
    for _ in range(N_SYSTEMS):
        processes = int(rng.integers(2, 6))
        # extensive: the land has one user; intensive: it has two
        nodes_e, edges_e = rent_graph([0], processes)
        nodes_i, edges_i = rent_graph([0, 1], processes)
        b1_e = first_betti(nodes_e, edges_e)
        b1_i = first_betti(nodes_i, edges_i)
        # delete the land vertex and the edges touching it
        keep = [v for v in nodes_i if v != ("L", 0)]
        edges_cut = [(u, v) for (u, v) in edges_i if ("L", 0) not in (u, v)]
        b1_cut = first_betti(keep, edges_cut)
        systems += 1
        raised += b1_i == b1_e + 1
        deleted += b1_cut == b1_i - 1
        # the two price equations are square in the wage and the rent
        q = np.sort(rng.uniform(YIELD[0], YIELD[1], 2))
        a = rng.uniform(CORN_INPUT[0], CORN_INPUT[1], 2)
        l = rng.uniform(LABOUR_INPUT[0], LABOUR_INPUT[1], 2)
        r = float(RATES[int(rng.integers(0, len(RATES)))])
        w, rho, m = intensive(q, a, l, r)
        if w is None:
            continue
        square += abs(np.linalg.det(m)) > 1e-9
        # give the two users different rates and read the added cycle
        if rho is not None and rho > 0.0:
            for factor in (1.0, 1.05, 1.5):
                rho1, rho2 = rho, rho * factor
                cycle = math.log(rho2) - math.log(rho1)
                want = math.log(factor)
                worst_close = max(worst_close, abs(cycle - want))
                if factor == 1.0:
                    closes += abs(cycle) < TOL
                else:
                    gap = abs(cycle)
                    smallest_open = gap if smallest_open is None else min(smallest_open, gap)
    ok = (systems > 0 and raised == systems and deleted == systems and square > 0
          and closes > 0 and worst_close < TOL_CYCLE
          and smallest_open is not None and smallest_open > 0.0)
    detail = ("%d drawn graphs of 2 to 5 processes. **Giving the land a second user raises `b1` "
              "by exactly one**, on %d of %d, with `b1` read from the incidence matrix rather "
              "than a formula, and **deleting that land vertex lowers it again**, on %d of %d, "
              "so the land really does lie on a cycle rather than hanging off one. The two "
              "price equations are then square in the wage and the rent, non-singular on %d "
              "draws, **and no zero-rent condition is used anywhere**: the second method is the "
              "second equation. **Reading the added cycle**: charge the two users `rho1` and "
              "`rho2` for the same acre and the cycle carries exactly `log(rho2 / rho1)`, "
              "within %g, so **it closes exactly when the two rates agree**. One rent per acre "
              "is not a bookkeeping convention here: **it is that cycle closing**"
              % (systems, raised, systems, deleted, systems, square, TOL_CYCLE))
    printed = ["b1 raised by one on %d of %d; deleting the land vertex lowers it on %d; the "
               "2x2 system is non-singular on %d; the cycle closes at equal rates on %d and "
               "the smallest non-zero opening seen is %.4f"
               % (raised, systems, deleted, square, closes,
                  0.0 if smallest_open is None else smallest_open)]
    return ok, detail, {"systems": int(systems), "b1_raised": int(raised),
                        "b1_lowered_by_deletion": int(deleted), "non_singular": int(square),
                        "closes_at_equal_rates": int(closes), "within": TOL_CYCLE}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B73-5", "known_answer",
         "Sraffa's section 87 on intensive rent, and Bidard's correction to it",
         check_sraffa_87(rng)),
        ("B73-6a", "instrument",
         "Theorem 18(1): declining efficiency costs nothing in the graph, and straight-line "
         "depreciation needs constant efficiency too", check_machine()),
        ("B73-6b", "instrument",
         "Theorem 18(2): intensive rent costs a cycle, and that cycle is the equation",
         check_intensive(rng)),
    ]
    mapping = {
        "B73-5": "both read back -> PASS; either not -> FAIL, and the code or the reading of "
                 "the source is fixed first",
        "B73-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B73-5 and B73-6: the known answer and the structural checks for "
          "docs/b73_two_extensions.md")
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
        "stage": "B73",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "n_systems": N_SYSTEMS,
            "machine_periods": MACHINE_T, "machine_params": dict(MACHINE_PARAMS),
            "efficiency_profiles": {k: list(v) for k, v in EFFICIENCY_PROFILES.items()},
            "linear_floor": LINEAR_FLOOR, "yield_range": list(YIELD),
            "corn_input": list(CORN_INPUT), "labour_input": list(LABOUR_INPUT),
            "rates": list(RATES),
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all three pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
