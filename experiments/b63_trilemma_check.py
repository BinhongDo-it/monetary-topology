"""B63-8: structural checks for the trilemma station.

The statements are proved in docs/b63_trilemma.md. This file checks their
algebra and the implementation of the objects they use, on small graphs built
for the purpose. It reads no data and measures nothing in the world.

Four checks, as registered in docs/b63_trilemma.md section 11:

  B63-8a  The plaquette sum is unchanged by a change of units at its four
          positions, and equals the closed form of the setup section.
  B63-8b  Corollary 8.1 on random currency graphs. With rates constant on the
          components of the peg graph no directed cycle is positive; moving the
          rate of a currency that shares a component creates a positive cycle
          even after every forward re-prices; moving the rate of a currency that
          is alone in its component does not; and the rank count of the
          equalities gives the number of components. The one-way extension: a
          directed cycle of one-way pegs forces equal rates, and two strongly
          connected components joined one way leave their rates unrelated.
  B63-8c  Corollary 8.3's band. Under a credible peg with both orientations
          open, the feasible set of r_k - r_l is
          [-(sigma_bar + beta_k), sigma_bar + beta_l], endpoints found by
          bisection over random spreads.
  B63-8d  The shape of the feasible set in five configurations, Corollaries
          8.2 to 8.4.

(NA) is implemented as the condition of b4_directed_edges Theorem 4, no directed
cycle with a positive sum, by Bellman-Ford. The graphs contain exactly the edges
a walking class holds, and agent edges are trades between classes, so every
directed cycle in them is walkable.

Run:

    python experiments\\b63_trilemma_check.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b63_trilemma_check.json"

DIGITS = 12
SEED = 0
TOL_CYCLE = 1e-12        # a cycle counts as positive only above this sum
TOL_IDENTITY = 1e-12     # plaquette identities, B63-8a
TOL_BAND = 1e-9          # band endpoints against the closed form, B63-8c and B63-8d
R0 = 0.03                # the anchor rate r_l in the two-currency graphs
BIG = 1.0                # a difference of 100 per cent a period: the probe for "unbounded"
N_GAUGE = 1000
N_GRAPHS = 400
MIN_CURRENCIES, MAX_CURRENCIES = 3, 10
EDGE_P, PEG_P, FORWARD_P = 0.35, 0.5, 0.5
PERTURB = 1e-3
BAND_DRAWS = 20
BISECTION_STEPS = 90
SHAPE_SPREADS = {"sigma": 0.002, "sigma_locked": 0.002, "beta_k": 0.001, "beta_l": 0.001}
ZERO_SPREADS = {"sigma": 0.0, "sigma_locked": 0.0, "beta_k": 0.0, "beta_l": 0.0}


def _r(x):
    return None if x is None else round(float(x), DIGITS)


def positive_cycle(edges) -> bool:
    """True iff some directed cycle has a sum above TOL_CYCLE.

    Bellman-Ford on the negated weights from a virtual source at every node: a
    cycle with a positive sum has negative length, and relaxation keeps
    improving along it however long it runs."""
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


# ----------------------------------------------------------- two currencies


def pair_graph(d, spreads=None, e=0.0, lam=None, access=None,
               classes=("a",), agent=None):
    """Currencies k and l at dates 0 (t) and 1 (t+1); r_k = R0 + d, r_l = R0.

    spreads  sigma (spot), sigma_locked, beta_k, beta_l
    lam      weight of the locked conversion; None is the peg, lam = e
    access   {(class, date, 'kl' or 'lk'): True} for the conversions open to
             each class; None opens every conversion to every class
    agent    None for no agent edges, else the weight of a trade of any
             position between any two classes; 0.0 is a trade at par
    """
    s = spreads or ZERO_SPREADS
    lam = e if lam is None else lam
    rate = {"k": R0 + d, "l": R0}
    beta = {"k": s["beta_k"], "l": s["beta_l"]}
    edges = []
    for c in classes:
        for cur in "kl":
            edges.append(((cur, 0, c), (cur, 1, c), rate[cur]))
            edges.append(((cur, 1, c), (cur, 0, c), -(rate[cur] + beta[cur])))
        for date, w, half in ((0, e, s["sigma"] / 2), (1, lam, s["sigma_locked"] / 2)):
            if access is None or access.get((c, date, "kl")):
                edges.append((("k", date, c), ("l", date, c), w - half))
            if access is None or access.get((c, date, "lk")):
                edges.append((("l", date, c), ("k", date, c), -w - half))
    if agent is not None:
        for cur, date in itertools.product("kl", (0, 1)):
            for a, b in itertools.permutations(classes, 2):
                edges.append(((cur, date, a), (cur, date, b), agent))
    return edges


def feasible(d, **kw) -> bool:
    return not positive_cycle(pair_graph(d, **kw))


def endpoint(side, **kw):
    """The feasible end of r_k - r_l on one side, by bisection.

    None when the difference is still feasible at BIG, which in these graphs
    means no cycle through the pair constrains that side at all."""
    sign = 1.0 if side == "upper" else -1.0
    if feasible(sign * BIG, **kw):
        return None
    if not feasible(0.0, **kw):
        raise RuntimeError("infeasible at a zero difference")
    lo, hi = 0.0, BIG
    for _ in range(BISECTION_STEPS):
        mid = (lo + hi) / 2
        if feasible(sign * mid, **kw):
            lo = mid
        else:
            hi = mid
    return sign * lo


def check_a(rng):
    a = "a"
    q_plus = (("k", 0, a), ("k", 1, a), ("l", 1, a), ("l", 0, a), ("k", 0, a))
    q_minus = (("k", 0, a), ("l", 0, a), ("l", 1, a), ("k", 1, a), ("k", 0, a))
    worst_gauge = worst_form = 0.0
    for _ in range(N_GAUGE):
        d, e, lam = rng.normal(0, 0.05), rng.normal(0, 1), rng.normal(0, 1)
        s = {key: abs(float(rng.normal(0, 0.003))) for key in ZERO_SPREADS}
        w = {(u, v): x for u, v, x in pair_graph(d, spreads=s, e=e, lam=lam)}
        psi = {p: float(rng.normal(0, 1)) for p in set(q_plus)}
        sbar = (s["sigma"] + s["sigma_locked"]) / 2
        core = d + lam - e
        forms = ((q_plus, core - s["beta_l"] - sbar), (q_minus, -core - s["beta_k"] - sbar))
        for path, form in forms:
            legs = list(zip(path[:-1], path[1:]))
            total = sum(w[leg] for leg in legs)
            regauged = sum(w[(u, v)] + psi[v] - psi[u] for u, v in legs)
            worst_gauge = max(worst_gauge, abs(total - regauged))
            worst_form = max(worst_form, abs(total - form))
    ok = worst_gauge < TOL_IDENTITY and worst_form < TOL_IDENTITY
    detail = ("%d draws of rates, parities, forwards and spreads, each with a random "
              "change of units at the four positions. Both orientations of the plaquette "
              "keep their sum under the change of units, and every sum equals the closed "
              "form S(Q+) = (r_k - r_l + lam - e) - beta_l - sigma_bar, "
              "S(Q-) = -(r_k - r_l + lam - e) - beta_k - sigma_bar, to within %g"
              % (N_GAUGE, TOL_IDENTITY))
    return ok, detail, {"draws": N_GAUGE, "identity_residuals_below": TOL_IDENTITY}


# ------------------------------------------------------ many currencies


def components(n, pairs):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in pairs:
        parent[find(u)] = find(v)
    return [find(i) for i in range(n)]


def multi_graph(rates, phi, conv, pegged, forwards, one_way=()):
    """One class, no spreads. Spot conversions at date 0 on every pair in conv;
    locked conversions at date 1 on pegged pairs, at the parity, and on forward
    pairs, at the covered-parity forward for the rates given. one_way holds
    ordered pairs pegged in one direction only, at both dates."""
    edges = []
    for k, r in enumerate(rates):
        edges.append(((k, 0), (k, 1), r))
        edges.append(((k, 1), (k, 0), -r))
    for k, l in conv:
        e = phi[l] - phi[k]
        edges += [((k, 0), (l, 0), e), ((l, 0), (k, 0), -e)]
        if (k, l) in pegged:
            edges += [((k, 1), (l, 1), e), ((l, 1), (k, 1), -e)]
        elif (k, l) in forwards:
            lam = e + rates[l] - rates[k]
            edges += [((k, 1), (l, 1), lam), ((l, 1), (k, 1), -lam)]
    for k, l in one_way:
        e = phi[l] - phi[k]
        edges += [((k, 0), (l, 0), e), ((k, 1), (l, 1), e)]
    return edges


def check_b(rng):
    base_bad = rank_bad = moved_in_bad = moved_alone_bad = 0
    moved_in = moved_alone = 0
    sizes = []
    for _ in range(N_GRAPHS):
        n = int(rng.integers(MIN_CURRENCIES, MAX_CURRENCIES + 1))
        order = [int(x) for x in rng.permutation(n)]
        conv = {tuple(sorted((order[i], order[i + 1]))) for i in range(n - 1)}
        conv |= {(k, l) for k, l in itertools.combinations(range(n), 2)
                 if rng.random() < EDGE_P}
        conv = sorted(conv)
        pegged, forwards = set(), set()
        for pair in conv:
            if rng.random() < PEG_P:
                pegged.add(pair)
            elif rng.random() < FORWARD_P:
                forwards.add(pair)
        phi = [float(x) for x in rng.normal(0, 1, n)]
        comp = components(n, pegged)
        labels = sorted(set(comp))
        sizes.append(len(labels))
        level = {c: float(rng.uniform(0.0, 0.1)) for c in labels}
        rates = [level[comp[k]] for k in range(n)]
        if positive_cycle(multi_graph(rates, phi, conv, pegged, forwards)):
            base_bad += 1
        rows = np.zeros((max(len(pegged), 1), n))
        for i, (k, l) in enumerate(sorted(pegged)):
            rows[i, k], rows[i, l] = 1.0, -1.0
        nullity = n - int(np.linalg.matrix_rank(rows))
        if nullity != len(labels):
            rank_bad += 1
        j = int(rng.integers(n))
        moved = list(rates)
        moved[j] += PERTURB
        shares = sum(1 for k in range(n) if comp[k] == comp[j]) > 1
        positive = positive_cycle(multi_graph(moved, phi, conv, pegged, forwards))
        if shares:
            moved_in += 1
            moved_in_bad += (not positive)
        else:
            moved_alone += 1
            moved_alone_bad += positive
    phi3 = [0.0, 0.3, -0.2]
    cycle3 = [(0, 1), (1, 2), (2, 0)]
    cycle_unequal = positive_cycle(multi_graph([0.01, 0.02, 0.03], phi3, [], set(), set(), cycle3))
    cycle_equal = positive_cycle(multi_graph([0.02, 0.02, 0.02], phi3, [], set(), set(), cycle3))
    joined = {"conv": [(0, 1)], "pegged": {(0, 1)}, "one_way": [(1, 2)]}
    apart_up = positive_cycle(multi_graph([0.02, 0.02, 0.07], phi3, joined["conv"],
                                          joined["pegged"], set(), joined["one_way"]))
    apart_down = positive_cycle(multi_graph([0.02, 0.02, -0.03], phi3, joined["conv"],
                                            joined["pegged"], set(), joined["one_way"]))
    inside_moved = positive_cycle(multi_graph([0.02 + PERTURB, 0.02, 0.07], phi3, joined["conv"],
                                              joined["pegged"], set(), joined["one_way"]))
    one_way_ok = cycle_unequal and not cycle_equal and not apart_up and not apart_down and inside_moved
    ok = (base_bad == 0 and rank_bad == 0 and moved_in_bad == 0 and moved_alone_bad == 0
          and moved_in > 0 and moved_alone > 0 and one_way_ok)
    detail = ("%d random currency graphs of %d to %d currencies, %d to %d components. "
              "With rates constant on the components of the peg graph, no positive cycle "
              "in %d of %d. The rank count of the equalities equals the number of components "
              "in %d of %d. Moving one rate by %g, with every forward re-priced, creates a "
              "positive cycle in %d of %d graphs where that currency shares a component and "
              "in %d of %d where it is alone. One-way pegs: a directed 3-cycle is infeasible "
              "with unequal rates (%s) and feasible with equal ones (%s); two strongly "
              "connected components joined one way stay feasible with their rates 5 points "
              "apart in either direction (%s, %s) and become infeasible once a rate inside "
              "the two-way pair moves (%s)"
              % (N_GRAPHS, MIN_CURRENCIES, MAX_CURRENCIES, min(sizes), max(sizes),
                 N_GRAPHS - base_bad, N_GRAPHS, N_GRAPHS - rank_bad, N_GRAPHS, PERTURB,
                 moved_in - moved_in_bad, moved_in, moved_alone_bad, moved_alone,
                 "yes" if cycle_unequal else "NO", "yes" if not cycle_equal else "NO",
                 "yes" if not apart_up else "NO", "yes" if not apart_down else "NO",
                 "yes" if inside_moved else "NO"))
    report = {"graphs": N_GRAPHS, "components_min": min(sizes), "components_max": max(sizes),
              "constant_on_components_feasible": N_GRAPHS - base_bad,
              "rank_count_matches": N_GRAPHS - rank_bad,
              "moved_inside_component": moved_in, "moved_inside_made_positive": moved_in - moved_in_bad,
              "moved_alone": moved_alone, "moved_alone_made_positive": moved_alone_bad,
              "one_way_cycle_unequal_infeasible": cycle_unequal,
              "one_way_cycle_equal_feasible": not cycle_equal,
              "one_way_join_apart_up_feasible": not apart_up,
              "one_way_join_apart_down_feasible": not apart_down,
              "one_way_join_inside_moved_infeasible": inside_moved}
    return ok, detail, report


# ------------------------------------------------------------- band and shapes


def check_c(rng):
    cases = [dict(ZERO_SPREADS)]
    for _ in range(BAND_DRAWS - 1):
        cases.append({"sigma": float(rng.uniform(0, 0.004)),
                      "sigma_locked": float(rng.uniform(0, 0.004)),
                      "beta_k": float(rng.uniform(0, 0.003)),
                      "beta_l": float(rng.uniform(0, 0.003))})
    worst = 0.0
    for s in cases:
        e = float(rng.normal(0, 1))
        lo, hi = endpoint("lower", spreads=s, e=e), endpoint("upper", spreads=s, e=e)
        sbar = (s["sigma"] + s["sigma_locked"]) / 2
        want_lo, want_hi = -(sbar + s["beta_k"]), sbar + s["beta_l"]
        if lo is None or hi is None:
            worst = float("inf")
            break
        worst = max(worst, abs(lo - want_lo), abs(hi - want_hi))
    ok = worst < TOL_BAND
    detail = ("%d spread draws, the first with no spreads at all. In every draw the feasible "
              "r_k - r_l runs from -(sigma_bar + beta_k) to sigma_bar + beta_l, the endpoints "
              "found by bisection within %g of the closed form; the draw with no spreads "
              "collapses to r_k = r_l, which is Theorem 8" % (len(cases), TOL_BAND))
    return ok, detail, {"draws": len(cases), "endpoint_error_below": TOL_BAND}


def check_d():
    s = SHAPE_SPREADS
    sbar = (s["sigma"] + s["sigma_locked"]) / 2
    band = (-(sbar + s["beta_k"]), sbar + s["beta_l"])
    open_all = {("a", date, way): True for date in (0, 1) for way in ("kl", "lk")}
    closed_every_date = {key: v for key, v in open_all.items() if key[2] != "kl"}
    closed_t1_only = {key: v for key, v in open_all.items() if key != ("a", 1, "kl")}
    split = {("a", 0, "kl"): True, ("a", 1, "kl"): True,
             ("b", 0, "lk"): True, ("b", 1, "lk"): True}
    configs = {
        "one direction closed at every date": (
            dict(spreads=s, access=closed_every_date), (None, None)),
        "closed at t+1 only": (
            dict(spreads=s, access=closed_t1_only), (band[0], None)),
        "class-split one-way, agent edges at par": (
            dict(spreads=s, access=split, classes=("a", "b"), agent=0.0), band),
        "class-split one-way, agent edges removed": (
            dict(spreads=s, access=split, classes=("a", "b"), agent=None), (None, None)),
    }
    shapes, ok = {}, True
    for name, (kw, (want_lo, want_hi)) in configs.items():
        lo, hi = endpoint("lower", **kw), endpoint("upper", **kw)
        match = all((got is None and want is None)
                    or (got is not None and want is not None and abs(got - want) < TOL_BAND)
                    for got, want in ((lo, want_lo), (hi, want_hi)))
        ok &= match
        shapes[name] = {"lower": _r(lo), "upper": _r(hi),
                        "expected_lower": _r(want_lo), "expected_upper": _r(want_hi),
                        "match": match}
    probes = (-BIG, -0.5, -0.01, 0.0, 0.01, 0.5, BIG)
    float_ok = all(feasible(d, spreads=s, e=0.0, lam=-d) for d in probes)
    ok &= float_ok
    shapes["float with a forward that re-prices"] = {
        "probes": [_r(d) for d in probes], "all_feasible": float_ok, "match": float_ok}

    def show(v):
        return "unbounded" if v is None else "%+.6f" % v

    parts = ["%s: [%s, %s]" % (name, show(v["lower"]), show(v["upper"]))
             for name, v in shapes.items() if "lower" in v]
    parts.append("float with a forward that re-prices: every probe from -1 to +1 feasible"
                 if float_ok else "float with a forward: NOT every probe feasible")
    detail = ("band here is [%+.6f, %+.6f]. " % band) + "; ".join(parts)
    return ok, detail, shapes


def main():
    rng = np.random.default_rng(SEED)
    results = [("B63-8a", "the plaquette sum is invariant under a change of units and equals "
                          "its closed form", check_a(rng)),
               ("B63-8b", "Corollary 8.1: rates equal exactly within components of the peg "
                          "graph, and within strongly connected components for one-way pegs",
                check_b(rng)),
               ("B63-8c", "Corollary 8.3: the band is [-(sigma_bar + beta_k), "
                          "sigma_bar + beta_l]", check_c(rng)),
               ("B63-8d", "Corollaries 8.2 to 8.4: the feasible set has the registered shape "
                          "in five configurations", check_d())]
    print("=" * 78)
    print("B63-8: structural checks for docs/b63_trilemma.md")
    print("=" * 78)
    criteria, report = [], {}
    for name, statement, (ok, detail, rep) in results:
        print("\n%s  %s\n  %s\n  %s" % (name, "PASS" if ok else "FAIL", statement, detail))
        criteria.append({"name": name, "kind": "instrument", "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
    rec = {
        "stage": "B63-8",
        "config": {
            "seed": SEED, "tol_cycle": TOL_CYCLE, "tol_identity": TOL_IDENTITY,
            "tol_band": TOL_BAND, "r0": R0, "big": BIG, "n_gauge": N_GAUGE,
            "n_graphs": N_GRAPHS, "currencies": [MIN_CURRENCIES, MAX_CURRENCIES],
            "edge_p": EDGE_P, "peg_p": PEG_P, "forward_p": FORWARD_P,
            "perturb": PERTURB, "band_draws": BAND_DRAWS,
            "bisection_steps": BISECTION_STEPS, "shape_spreads": SHAPE_SPREADS,
        },
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
