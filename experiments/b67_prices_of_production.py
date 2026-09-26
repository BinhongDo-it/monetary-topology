"""B67-6 and B67-7: the known answers and the structural checks for prices of
production.

The statements are proved in docs/b67_prices_of_production.md. This file checks
their algebra, and the implementation of the objects they use, on random
productive systems built by the industry generator of stage A19 and on two
examples from the literature. It reads no data and measures nothing in the
world.

  B67-6a  Sraffa's own result. With the standard commodity as the numeraire and
          the standard system scaled to one unit of labour, the wage is exactly
          1 - r / R at every rate of profits.
  B67-6b  Samuelson's (1966) double-switching example: two techniques whose
          costs are equal at two rates of profits, 50 and 100 per cent, with
          the second technique cheaper strictly between them.
  B67-7a  Theorem 12(1) and (2) on random systems: every production cycle of
          the graph sums to log(1 + r) and they are all equal; the maximum rate
          is 1 / lambda_PF(A) - 1; the wage falls in the rate of profits; and
          both wage conventions, paid out of the product and advanced, give
          equal cycle sums with their own reading of what is advanced.
  B67-7b  Theorem 12(4): the exchange edges carry a single price vector, the
          whole obstruction sits on the production edges, and the distance of
          Theorem 5 is proportional to log(1 + r) with a coefficient that
          belongs to the graph.
  B67-7c  Corollary 12.2: with the production edges walkable without a bound,
          a directed cycle is positive at every r > 0, so (NA) leaves only
          r = 0; with every producer bounded, no directed cycle is positive at
          any r. (NA) can give a zero rate and cannot give a uniform positive
          one.
  B67-7d  Corollary 10.2 of the post-Keynesian file on this system: the profits
          of the whole economy are the rate of profits times the value of what
          is advanced, for the standard system and for random scales alike.

Run:

    python experiments\\b67_prices_of_production.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monetary_topology.industry import IndustrySpec, build_io_matrix, check_feasible

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b67_prices_of_production.json"

SEED = 0
TOL = 1e-12            # identities on prices, cycle sums and distances
TOL_CYCLE = 1e-12      # a directed cycle counts as positive only above this sum
TOL_SWITCH = 1e-9      # a switching rate found by bisection, against its closed form
BISECTION_STEPS = 60
N_SYSTEMS = 200
SIZES = (3, 8)
COLUMN_SUMS = (0.3, 0.5, 0.7)
R_FRACTIONS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)
SCALE_DRAWS = 3        # random scales of the economy, for Corollary 10.2

# Samuelson (1966), A Summing Up: labour at one, two and three periods before the output
SAMUELSON_A = {2: 7.0}
SAMUELSON_B = {1: 6.0, 3: 2.0}
SAMUELSON_SWITCHES = (0.5, 1.0)
SAMUELSON_COSTS = (15.75, 28.0)


def incidence(nodes, edges):
    """Rows are nodes, columns edges: +1 at the head, -1 at the tail."""
    index = {v: k for k, v in enumerate(nodes)}
    B = np.zeros((len(nodes), len(edges)))
    for e, (u, v) in enumerate(edges):
        B[index[v], e] += 1.0
        B[index[u], e] -= 1.0
    return B


def distance(B, omega):
    """Theorem 5's distance from omega to the fields with a potential, and the
    residual, which is omega's component in the cycle space."""
    psi, *_ = np.linalg.lstsq(B.T, omega, rcond=None)
    comp = omega - B.T @ psi
    return float(np.linalg.norm(comp)), comp


def positive_cycle(edges) -> bool:
    """True iff some directed cycle has a sum above TOL_CYCLE."""
    index = {}
    for u, v, _ in edges:
        index.setdefault(u, len(index))
        index.setdefault(v, len(index))
    dist = [0.0] * len(index)
    arcs = [(index[u], index[v], -w) for u, v, w in edges]
    for _ in range(len(index) + 1):
        changed = False
        for u, v, c in arcs:
            if dist[u] + c < dist[v] - TOL_CYCLE:
                dist[v] = dist[u] + c
                changed = True
        if not changed:
            return False
    return True


def bisect_switch(lo, hi, positive_at):
    at_lo = positive_at(lo)
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        if positive_at(mid) == at_lo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------- the system


def irreducible(a) -> bool:
    """Sraffa's basic system: every commodity enters, directly or not, the
    production of every other. That is the input matrix being irreducible."""
    n = a.shape[0]
    reach = (a > 0.0).astype(float) + np.eye(n)
    for _ in range(int(math.ceil(math.log2(max(n, 2)))) + 1):
        reach = (reach @ reach > 0.0).astype(float)
    return bool((reach > 0.0).all())


def perron(a):
    """The dominant eigenvalue of A and its right eigenvector, the standard
    proportions. A's columns are buyers: A[i, j] is input i per unit of j."""
    values, vectors = np.linalg.eig(a)
    k = int(np.argmax(values.real))
    lam = float(values[k].real)
    s = np.real(vectors[:, k])
    if s.sum() < 0:
        s = -s
    return lam, s


def sraffa_prices(a, l, r, numeraire, advanced=False):
    """Solve the price equations at a rate of profits r, with `numeraire` the
    basket whose price is one. Wages out of the product: p = (1+r) p A + w l.
    Wages advanced: p = (1+r)(p A + w l)."""
    n = a.shape[0]
    m = np.eye(n) - (1.0 + r) * a
    base = l @ np.linalg.inv(m)               # p is proportional to this row
    if advanced:
        base = (1.0 + r) * base
    scale = float(base @ numeraire)
    w = 1.0 / scale
    return w * base, w


def production_graph(a, l, p, w, r, advanced=False):
    """The graph of the system at one rate of profits. Each industry has money,
    its input bundle and its output; it buys the bundle, produces, and sells.
    With wages paid out of the product the money a run of the cycle returns is
    the price less the wage bill, and what it advances is the bundle of
    commodities; with wages advanced they are in the bundle and the sale leg is
    the price itself. Money passes between industries at par."""
    n = a.shape[0]
    advance = p @ a + (w * l if advanced else 0.0)
    back = p if advanced else p - w * l
    nodes, edges, omega, production, potential = [], [], [], [], []
    for j in range(n):
        nodes += [(j, "M"), (j, "B"), (j, "Q")]
        potential += [0.0, -math.log(advance[j]), -math.log(back[j])]
        edges.append(((j, "M"), (j, "B")))
        omega.append(-math.log(advance[j]))
        production.append(0.0)
        edges.append(((j, "B"), (j, "Q")))
        omega.append(0.0)
        production.append(1.0)
        edges.append(((j, "Q"), (j, "M")))
        omega.append(math.log(back[j]))
        production.append(0.0)
        if j > 0:
            edges.append(((0, "M"), (j, "M")))
            omega.append(0.0)
            production.append(0.0)
    return (nodes, edges, np.array(omega), np.array(production), np.array(potential))


def cycle_sums(omega, n):
    """The sum of each industry's production cycle, read off the edge weights
    in the order `production_graph` writes them."""
    sums, k = [], 0
    for j in range(n):
        s = omega[k] + omega[k + 1] + omega[k + 2]
        k += 3 + (1 if j > 0 else 0)
        sums.append(float(s))
    return np.array(sums)


def na_edges(a, l, p, w, r, walkable=True):
    """The same graph as a directed one, with the production edge held only by
    a class that can walk it without a bound on quantity."""
    nodes, edges, omega, production, _ = production_graph(a, l, p, w, r)
    out = []
    for (u, v), x, is_prod in zip(edges, omega, production):
        if is_prod and not walkable:
            continue
        out.append((u, v, float(x)))
    return out


def random_system(rng):
    """A productive, irreducible input matrix from stage A19's generator, with
    a labour vector drawn positive."""
    n = int(rng.integers(SIZES[0], SIZES[1] + 1))
    column_sum = float(COLUMN_SUMS[int(rng.integers(0, len(COLUMN_SUMS)))])
    for _ in range(60):
        spec = IndustrySpec(count=n, financial_count=0, column_sum=column_sum,
                            seed=int(rng.integers(0, 2**31 - 1)))
        a = build_io_matrix(spec)
        check_feasible(a)
        if irreducible(a):
            return a, rng.uniform(0.2, 2.0, n), column_sum
    return None, None, column_sum


# ------------------------------------- B67-6a: the standard commodity's frontier


def check_standard(rng):
    systems = points = linear = 0
    worst_linear = worst_eigen = 0.0
    for _ in range(N_SYSTEMS):
        a, l, _ = random_system(rng)
        if a is None:
            continue
        lam, s = perron(a)
        if s.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        worst_eigen = max(worst_eigen, float(np.abs(a @ s - lam * s).max()))
        s = s / float(l @ s)                     # the standard system employs one unit of labour
        numeraire = (np.eye(len(s)) - a) @ s     # its net product is the unit of account
        for f in R_FRACTIONS:
            r = f * R
            p, w = sraffa_prices(a, l, r, numeraire)
            points += 1
            gap = abs(w - (1.0 - r / R))
            worst_linear = max(worst_linear, gap)
            linear += gap < TOL
    ok = systems > 0 and linear == points and worst_linear < TOL and worst_eigen < 1e-10
    detail = ("%d random productive systems of %d to %d industries from stage A19's generator, "
              "irreducible so that every commodity is basic, at %d rates of profits each. With "
              "the standard system scaled to one unit of labour and its net product as the unit "
              "of account, **the wage is 1 - r / R at every one of the %d points**, within %g, "
              "and R is 1 / lambda_PF(A) - 1. This is Sraffa's own result and it is the known "
              "answer here" % (systems, SIZES[0], SIZES[1], len(R_FRACTIONS), points, TOL))
    printed = ["worst |w - (1 - r/R)| %.3e over %d points; worst |A s - lambda s| %.3e"
               % (worst_linear, points, worst_eigen)]
    return ok, detail, {"systems": systems, "points": points, "linear_within": TOL}, printed


# ------------------------------------------- B67-6b: Samuelson's two switch points


def samuelson_cost(profile, r):
    return sum(n_labour * (1.0 + r) ** periods for periods, n_labour in profile.items())


def check_samuelson():
    def difference(r):
        return samuelson_cost(SAMUELSON_A, r) - samuelson_cost(SAMUELSON_B, r)

    switches = (bisect_switch(0.2, 0.8, lambda r: difference(r) < 0.0),
                bisect_switch(1.4, 0.8, lambda r: difference(r) < 0.0))
    worst = max(abs(got - want) for got, want in zip(sorted(switches), SAMUELSON_SWITCHES))
    costs = [samuelson_cost(SAMUELSON_A, r) for r in SAMUELSON_SWITCHES]
    worst_cost = max(abs(c - want) for c, want in zip(costs, SAMUELSON_COSTS))
    equal_at = max(abs(difference(r)) for r in SAMUELSON_SWITCHES)
    between = all(difference(r) > 0.0 for r in (0.55, 0.75, 0.95))
    outside = all(difference(r) < 0.0 for r in (0.0, 0.25, 0.45, 1.05, 1.5, 3.0))
    ok = (worst < TOL_SWITCH and worst_cost < TOL and equal_at < TOL and between and outside)
    detail = ("Samuelson's example of 1966: one technique spends 7 units of labour two periods "
              "before the output, the other 2 units three periods before and 6 units one period "
              "before. Their costs are equal at exactly two rates of profits, %g and %g, found "
              "here by bisection within %g, at %g and %g per unit; the second technique is the "
              "cheaper strictly between them and the first outside, at every probe. **The same "
              "technique is chosen at a low rate and at a high one and the other in between**, "
              "which is the reswitching the capital controversy turned on"
              % (SAMUELSON_SWITCHES[0], SAMUELSON_SWITCHES[1], TOL_SWITCH,
                 SAMUELSON_COSTS[0], SAMUELSON_COSTS[1]))
    printed = ["switches found at %.12f and %.12f; worst gap to the published pair %.3e; "
               "costs there %.6f and %.6f" % (min(switches), max(switches), worst,
                                              costs[0], costs[1])]
    return ok, detail, {"switches": list(SAMUELSON_SWITCHES), "within": TOL_SWITCH,
                        "costs": list(SAMUELSON_COSTS)}, printed


# --------------------------- B67-7a: equal cycle sums, the maximum rate, the frontier


def check_cycles(rng):
    systems = points = equal = 0
    worst_sum = worst_advanced = 0.0
    falling = True
    for _ in range(N_SYSTEMS):
        a, l, _ = random_system(rng)
        if a is None:
            continue
        lam, s = perron(a)
        if s.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        numeraire = np.ones(len(l))
        wages = []
        for f in R_FRACTIONS:
            r = f * R
            p, w = sraffa_prices(a, l, r, numeraire)
            nodes, edges, omega, prod, _ = production_graph(a, l, p, w, r)
            sums = cycle_sums(omega, a.shape[0])
            gap = float(np.abs(sums - math.log1p(r)).max())
            worst_sum = max(worst_sum, gap)
            points += 1
            equal += gap < TOL
            wages.append(w)
            p2, w2 = sraffa_prices(a, l, r, numeraire, advanced=True)
            _, _, omega2, _, _ = production_graph(a, l, p2, w2, r, advanced=True)
            worst_advanced = max(worst_advanced,
                                 float(np.abs(cycle_sums(omega2, a.shape[0])
                                              - math.log1p(r)).max()))
        falling &= all(x > y for x, y in zip(wages, wages[1:]))
    ok = systems > 0 and equal == points and worst_sum < TOL and worst_advanced < TOL and falling
    detail = ("%d systems at %d rates of profits each. **Every industry's production cycle sums "
              "to log(1 + r), and they are all equal**, within %g, at all %d points; the same "
              "holds with wages advanced instead of paid out of the product, where the bundle "
              "carries the wage and the sale leg carries the price; and the wage falls in the "
              "rate of profits on every system, reaching zero at R = 1 / lambda_PF(A) - 1"
              % (systems, len(R_FRACTIONS), TOL, points))
    printed = ["worst |cycle sum - log(1+r)| %.3e out of the product, %.3e with wages advanced; "
               "the wage falls on every system: %s" % (worst_sum, worst_advanced, falling)]
    return ok, detail, {"systems": systems, "points": points, "sums_within": TOL}, printed


# ------------------------------------------- B67-7b: where the obstruction sits


def check_distance(rng):
    systems = points = proportional = closed_form = 0
    worst_prop = worst_form = worst_exchange = 0.0
    for _ in range(N_SYSTEMS):
        a, l, _ = random_system(rng)
        if a is None:
            continue
        lam, s = perron(a)
        if s.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        n = a.shape[0]
        numeraire = np.ones(n)
        coefficient = None
        for f in R_FRACTIONS:
            r = f * R
            p, w = sraffa_prices(a, l, r, numeraire)
            nodes, edges, omega, prod, psi = production_graph(a, l, p, w, r)
            B = incidence(nodes, edges)
            rho, residual = distance(B, omega)
            # against the potential the prices themselves give, the departure is the same
            # number on every production edge and zero on every other
            departure = omega - B.T @ psi
            worst_exchange = max(worst_exchange,
                                 float(np.abs(departure - math.log1p(r) * prod).max()))
            if coefficient is None:
                coefficient = distance(B, prod)[0]     # the graph's own number
                worst_form = max(worst_form, abs(coefficient - math.sqrt(n / 3.0)))
                closed_form += abs(coefficient - math.sqrt(n / 3.0)) < TOL
            points += 1
            want = coefficient * math.log1p(r)
            worst_prop = max(worst_prop, abs(rho - want))
            proportional += abs(rho - want) < TOL
    ok = (systems > 0 and proportional == points and closed_form == systems
          and worst_prop < TOL and worst_form < TOL and worst_exchange < TOL)
    detail = ("%d systems at %d rates each. The exchange edges carry a single price vector, so "
              "**the whole of the field's departure from a potential sits on the production "
              "edges**, and the distance of Theorem 5 is that departure projected on the cycle "
              "space: `rho = c · log(1 + r)` within %g at all %d points, with `c` a number that "
              "belongs to the graph and not to the rate. Against the potential the prices "
              "themselves give, the departure is log(1 + r) on every production edge and zero on "
              "every other, within %g. For the graph drawn here, one cycle of three edges per "
              "industry and money at par between them, `c` is the square root of the industry "
              "count over three, matched within %g on every system. **The invariant is the sum "
              "on one cycle; the distance aggregates it and therefore counts how the graph was "
              "drawn**" % (systems, len(R_FRACTIONS), TOL, points, TOL, TOL))
    printed = ["worst |rho - c log(1+r)| %.3e; worst |c - sqrt(n/3)| %.3e; "
               "worst departure against the price potential %.3e"
               % (worst_prop, worst_form, worst_exchange)]
    return ok, detail, {"systems": systems, "points": points, "within": TOL}, printed


# ---------------------------------- B67-7c: what (NA) can and cannot give here


def check_no_arbitrage(rng):
    systems = unbounded_ok = bounded_ok = switch_ok = 0
    worst_switch = 0.0
    probes = (-0.3, -0.1, -0.01, 0.0, 0.01, 0.1, 0.3, 0.9)
    for _ in range(60):
        a, l, _ = random_system(rng)
        if a is None:
            continue
        lam, s = perron(a)
        if s.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        numeraire = np.ones(a.shape[0])

        def positive_at(r, walkable=True):
            p, w = sraffa_prices(a, l, min(r, 0.99 * R), numeraire)
            return positive_cycle(na_edges(a, l, p, w, r, walkable=walkable))

        unbounded_ok += all(positive_at(r) == (r > 0.0) for r in probes if abs(r) > 1e-9)
        bounded_ok += not any(positive_at(r, walkable=False) for r in probes)
        got = bisect_switch(0.5, -0.5, lambda r: positive_at(r))
        worst_switch = max(worst_switch, abs(got))
        switch_ok += abs(got) < TOL_SWITCH
    ok = (systems > 0 and unbounded_ok == systems and bounded_ok == systems
          and switch_ok == systems)
    detail = ("%d systems, each probed at rates of profits from -0.3 to +0.9. **With the "
              "production edges walkable without a bound, a directed cycle is positive at every "
              "positive rate and at none below zero**, in %d of %d, and the switching rate found "
              "by bisection is zero within %g in %d of %d. **With every producer bounded, no "
              "directed cycle is positive at any rate**, in %d of %d. So (NA) leaves `r = 0` and "
              "cannot leave a uniform positive rate: equalisation at a positive rate needs a "
              "bound and a flow that responds, neither of which is a no-arbitrage statement"
              % (systems, unbounded_ok, systems, TOL_SWITCH, switch_ok, systems,
                 bounded_ok, systems))
    printed = ["worst |switching rate| %.3e" % worst_switch]
    return ok, detail, {"systems": systems, "probes": list(probes), "within": TOL_SWITCH}, printed


# ------------------------- B67-7d: profits are the rate times what is advanced


def check_profits(rng):
    systems = draws = matched = 0
    worst = 0.0
    for _ in range(N_SYSTEMS):
        a, l, _ = random_system(rng)
        if a is None:
            continue
        lam, s = perron(a)
        if s.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        numeraire = np.ones(a.shape[0])
        for f in (0.25, 0.5, 0.9):
            r = f * R
            p, w = sraffa_prices(a, l, r, numeraire)
            advance = p @ a
            for scale in [s] + [rng.uniform(0.2, 3.0, a.shape[0]) for _ in range(SCALE_DRAWS)]:
                profits = float((p * scale).sum() - (advance * scale).sum()
                                - w * float(l @ scale))
                want = r * float((advance * scale).sum())
                draws += 1
                gap = abs(profits - want) / max(1.0, abs(want))
                worst = max(worst, gap)
                matched += gap < TOL
    ok = systems > 0 and matched == draws and worst < TOL
    detail = ("%d systems, three rates each, the standard proportions and %d random scales of "
              "the economy: **the profits of the whole economy are the rate of profits times the "
              "value of what is advanced**, within %g relative, in %d of %d. This is Corollary "
              "10.2 of the post-Keynesian file read on this system, with the value sent round "
              "each production cycle being what that industry advances"
              % (systems, SCALE_DRAWS, TOL, matched, draws))
    printed = ["worst relative gap %.3e over %d draws" % (worst, draws)]
    return ok, detail, {"systems": systems, "draws": draws, "within": TOL}, printed


# ---------------------------------------------------------------------- main


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B67-6a", "known_answer",
         "Sraffa's linear frontier: with the standard commodity as the unit of account the wage "
         "is 1 - r / R", check_standard(rng)),
        ("B67-6b", "known_answer",
         "Samuelson's 1966 example: two switch points, at 50 and 100 per cent",
         check_samuelson()),
        ("B67-7a", "instrument",
         "Theorem 12(1) and (2): equal cycle sums are the price equations, and the maximum rate "
         "is the Perron-Frobenius one", check_cycles(rng)),
        ("B67-7b", "instrument",
         "Theorem 12(4): the obstruction sits on the production edges and the distance is "
         "proportional to log(1 + r)", check_distance(rng)),
        ("B67-7c", "instrument",
         "Corollary 12.2: (NA) gives a zero rate and cannot give a uniform positive one",
         check_no_arbitrage(rng)),
        ("B67-7d", "instrument",
         "Corollary 10.2 on this system: profits are the rate times what is advanced",
         check_profits(rng)),
    ]
    mapping = {
        "B67-6": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B67-7": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed",
    }
    print("=" * 78)
    print("B67-6 and B67-7: known answers and structural checks for "
          "docs/b67_prices_of_production.md")
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
        "stage": "B67",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_switch": TOL_SWITCH,
            "bisection_steps": BISECTION_STEPS, "n_systems": N_SYSTEMS, "sizes": list(SIZES),
            "column_sums": list(COLUMN_SUMS), "r_fractions": list(R_FRACTIONS),
            "scale_draws": SCALE_DRAWS,
            "samuelson": {"technique_a": {str(k): v for k, v in SAMUELSON_A.items()},
                          "technique_b": {str(k): v for k, v in SAMUELSON_B.items()},
                          "switches": list(SAMUELSON_SWITCHES),
                          "costs": list(SAMUELSON_COSTS)},
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all six pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
