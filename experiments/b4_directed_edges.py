"""B4: the directed theorem, executed.

Proved in ``docs/b4_directed_edges.md``. This checks the implementations, not the
mathematics. Every criterion below is one an error in ``directed.py`` could break
while the theorems stayed true.

Usage::

    python experiments/b4_directed_edges.py
    python experiments/b4_directed_edges.py --shapes 40   # wider sweep

Writes ``results/b4_directed_edges.json``. No data is read and no figure is
produced; the stage has no empirical content and a figure would suggest it does.

**B4-6 is the criterion that matters.** A generalisation that does not contain
the case it generalises is not a generalisation, so the directed machinery is
made to reproduce ``product_graph.potential_from_cochain`` **bitwise** on an
antisymmetric field. Integer potentials are used precisely so that "bitwise" is a
claim that can be made rather than a tolerance in disguise.

**B4-1 is the one that could be circular and is not.** Theorem 4's two sides are
computed by two routines that share no reasoning: ``sub_potential`` runs
Bellman-Ford and never sees a cycle, ``worst_directed_cycle`` enumerates every
simple directed cycle and never builds a potential.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.directed import (  # noqa: E402
    DirectedField,
    directed_square,
    from_antisymmetric,
    potential_interval,
    ray_is_valid,
    shift_breaks,
    simple_directed_cycles,
    sink_component,
    split,
    strongly_connected_components,
    sub_potential,
    violation,
    worst_directed_cycle,
)
from monetary_topology.product_graph import (  # noqa: E402
    box_product,
    cochain_from_field,
    complete_agent_graph,
    exact_field,
    potential_from_cochain,
    undirected_pairs,
    vertex,
)

RESULTS = ROOT / "results"

#: Small on purpose. The claims are algebraic, so a case that fails will fail at
#: n=4, and enumeration of simple directed cycles is exponential.
DEFAULT_SHAPES = 24
TOL = 1e-9


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    #: Discipline 11d. Written only where it is set, so the criteria that predate
    #: the field keep the bytes they had.
    kind: str | None = None

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def random_directed(n: int, rng: np.random.Generator, density: float = 0.45,
                    scale: float = 1.0) -> DirectedField:
    """A random directed field. Each ordered pair is drawn independently.

    No antisymmetry and no guarantee that a reverse leg exists, which is the
    whole point: a generator that quietly produced two-way edges would test
    Theorem 1 again under a new name.
    """
    weights: dict[tuple[int, int], float] = {}
    for u in range(n):
        for v in range(n):
            if u != v and rng.random() < density:
                weights[(u, v)] = float(rng.normal(0.0, scale))
    return DirectedField(weights, n)


def two_way_field(n: int, rng: np.random.Generator,
                  spread: float = 0.3) -> DirectedField:
    """A field where every edge is two-way, with an independent spread on each.

    Built as an exact antisymmetric part plus a non-positive symmetric part, so a
    sub-potential is guaranteed to exist and Theorem 6 has something to be true
    about. The spread is drawn strictly negative because ``w_bar <= 0`` is what
    no-arbitrage forces, and drawing it freely would be testing whether the
    generator obeys the theorem rather than whether the code does.
    """
    phi = rng.normal(0.0, 1.0, size=n)
    weights: dict[tuple[int, int], float] = {}
    for u in range(n):
        for v in range(u + 1, n):
            bar = -abs(float(rng.normal(0.0, spread)))
            hat = float(phi[v] - phi[u])
            weights[(u, v)] = hat + bar
            weights[(v, u)] = -hat + bar
    return DirectedField(weights, n)


def strongly_connected_field(n: int, rng: np.random.Generator) -> DirectedField:
    """Strongly connected, a sub-potential guaranteed, and **not** all two-way.

    Written because the first version of B4-4 drew from ``random_directed`` and
    the criterion came back vacuous: a random directed field that admits a
    sub-potential is almost never strongly connected, because strong
    connectivity puts every cycle in the sample twice, once in each orientation,
    and both sums must be non-positive. That is Theorem 4's condition biting, not
    a defect, so the generator is the thing that had to change.

    A Hamiltonian cycle forces strong connectivity. Weights are set to
    ``phi(v) - phi(u) - |noise|`` so ``phi`` is a sub-potential by construction
    and the existence question is not what is being tested here. Extra edges are
    added in one direction only, so the sample is not secretly the antisymmetric
    case under another name.
    """
    phi = rng.normal(0.0, 1.0, size=n)
    weights: dict[tuple[int, int], float] = {}

    def put(u: int, v: int) -> None:
        weights[(u, v)] = float(phi[v] - phi[u] - abs(rng.normal(0.0, 0.3)))

    order = rng.permutation(n)
    for t in range(n):
        put(int(order[t]), int(order[(t + 1) % n]))
    for u in range(n):
        for v in range(n):
            if u != v and (u, v) not in weights and rng.random() < 0.3:
                put(u, v)
    return DirectedField(weights, n)


def directed_product(adj_g: np.ndarray, m: int, forward: np.ndarray,
                     backward: np.ndarray) -> DirectedField:
    """``Gamma`` with independent legs in each direction and zero agent edges.

    ``forward[a, i, j]`` is class ``a`` going ``i -> j``; ``backward[a, i, j]`` is
    the same class coming back. They are separate arrays rather than one
    antisymmetric one, so there is no way to write a two-way assumption in by
    accident.
    """
    n = adj_g.shape[0]
    weights: dict[tuple[int, int], float] = {}
    for a in range(m):
        for i, j in undirected_pairs(adj_g):
            weights[(vertex(a, i, n), vertex(a, j, n))] = float(forward[a, i, j])
            weights[(vertex(a, j, n), vertex(a, i, n))] = float(backward[a, i, j])
    for i in range(n):
        for a, b in undirected_pairs(complete_agent_graph(m)):
            weights[(vertex(a, i, n), vertex(b, i, n))] = 0.0
            weights[(vertex(b, i, n), vertex(a, i, n))] = 0.0
    return DirectedField(weights, m * n)


# ---------------------------------------------------------------------------


def theorem_4(rng: np.random.Generator, shapes: int) -> tuple[list[Criterion], dict]:
    """B4-1 and B4-2: existence, against enumeration, in both directions."""
    agree = disagree = 0
    with_potential = 0
    worst_breach = -np.inf
    both_seen = {"exists": 0, "arbitrage": 0}
    detail_fail = []

    for _ in range(shapes):
        n = int(rng.integers(4, 7))
        # Two scales. The small one makes cycle sums cluster near zero so that
        # existence and non-existence are both common; the large one would make
        # a positive cycle almost certain and the criterion would never see the
        # case it is meant to distinguish.
        field = random_directed(n, rng, scale=float(rng.choice([0.25, 1.0])))
        if not field.weights:
            continue
        phi, reason = sub_potential(field)
        worst, _ = worst_directed_cycle(field)
        enumerated_ok = worst <= TOL or not np.isfinite(worst)

        if (phi is not None) == enumerated_ok:
            agree += 1
        else:
            disagree += 1
            detail_fail.append((n, worst, reason))

        if phi is not None:
            with_potential += 1
            both_seen["exists"] += 1
            worst_breach = max(worst_breach, violation(field, phi))
        else:
            both_seen["arbitrage"] += 1

    covered = both_seen["exists"] > 0 and both_seen["arbitrage"] > 0
    crits = [
        Criterion(
            "B4-1  Theorem 4: Bellman-Ford agrees with cycle enumeration",
            disagree == 0 and covered,
            f"{agree} agree, {disagree} disagree over {agree + disagree} graphs; "
            f"{both_seen['exists']} admit a sub-potential and "
            f"{both_seen['arbitrage']} carry a positive cycle"
            + ("" if covered else "; ONE SIDE NEVER OCCURRED, criterion vacuous"),
        ),
        Criterion(
            "B4-2  the returned potential satisfies every edge inequality",
            worst_breach <= TOL,
            f"worst breach {worst_breach:.3e} over {with_potential} potentials "
            f"against {TOL:.0e}",
        ),
    ]
    return crits, {
        "agree": agree, "disagree": disagree, "coverage": both_seen,
        "worst_breach": None if worst_breach == -np.inf else float(worst_breach),
        "failures": detail_fail,
    }


def theorem_5(rng: np.random.Generator, shapes: int) -> tuple[list[Criterion], dict]:
    """B4-3 and B4-4: the ray when not strongly connected, and its absence when."""
    shifts = np.array([0.0, 0.5, 2.0, 10.0, 1e3, 1e6])
    ray_worst = -np.inf
    rays_tested = 0
    bounded_tested = 0
    bounded_min_break = np.inf
    bounded_failures: list = []
    interval_failures: list = []
    widest = -np.inf

    for _ in range(shapes * 3):
        n = int(rng.integers(4, 7))
        field = random_directed(n, rng, density=0.35, scale=0.25)
        phi, _ = sub_potential(field)
        if phi is None:
            continue
        sink = sink_component(field)
        if sink is not None and len(sink) < n:
            rays_tested += 1
            ray_worst = max(ray_worst, ray_is_valid(field, phi, sink, shifts))

    # The bounded half is drawn from its own generator. See
    # ``strongly_connected_field`` for why sharing the generator made the
    # criterion vacuous rather than merely thin.
    for _ in range(shapes):
        n = int(rng.integers(4, 7))
        field = strongly_connected_field(n, rng)
        phi, _ = sub_potential(field)
        if phi is None or len(strongly_connected_components(field)) != 1:
            continue
        bounded_tested += 1
        # Every proper non-empty subset must break, because strong connectivity
        # means every such subset has a directed edge leaving it.
        worst_for_this_graph = np.inf
        for size in (1, n // 2, n - 1):
            subset = list(rng.permutation(n)[:size])
            worst_for_this_graph = min(
                worst_for_this_graph, shift_breaks(field, phi, subset, 1e6)
            )
        bounded_min_break = min(bounded_min_break, worst_for_this_graph)
        if worst_for_this_graph <= 0:
            bounded_failures.append(n)

        # The substantive half: the interval each coordinate difference is
        # confined to is finite, non-empty, and actually contains the
        # sub-potential that Bellman-Ford returned. Breaking a shift only shows
        # one direction is blocked; this shows both are.
        for u in range(n):
            for v in range(n):
                if u == v:
                    continue
                lo, hi = potential_interval(field, u, v)
                if not (np.isfinite(lo) and np.isfinite(hi)):
                    interval_failures.append(("infinite", n, u, v))
                    continue
                widest = max(widest, hi - lo)
                if hi - lo < -TOL:
                    interval_failures.append(("empty", n, u, v, hi - lo))
                gap = float(phi[v] - phi[u])
                if gap < lo - TOL or gap > hi + TOL:
                    interval_failures.append(("outside", n, u, v, gap, lo, hi))

    if rays_tested:
        print(
            f"  B4-3 sink-ray violation {ray_worst:.3e} against {TOL:.0e} "
            f"(not written to the record: machine-dependent rounding)"
        )

    crits = [
        Criterion(
            "B4-3  Theorem 5: a sink component gives an unbounded ray",
            rays_tested > 0 and ray_worst <= TOL,
            # The project's engineering rule 6, as for B4-7 and B4-8 below. The violation is
            # machine epsilon amplified by the shift magnitude, which is why it
            # reads `1e-11` rather than `1e-16`; its digits still come from the
            # BLAS build. The shift magnitude itself is a design constant and
            # stays.
            f"{rays_tested} graphs with a proper sink; the worst violation "
            f"over shifts up to {shifts.max():.0e} is at machine precision "
            f"for that scale, below {TOL:.0e}"
            if rays_tested
            else "no graph with a proper sink was drawn; criterion vacuous",
        ),
        Criterion(
            "B4-4  Theorem 5: strong connectivity bounds the polytope",
            bounded_tested > 0 and not bounded_failures and not interval_failures,
            f"{bounded_tested} strongly connected graphs; every proper subset "
            f"breaks (smallest breach {bounded_min_break:.3e}); every coordinate "
            f"interval is finite, non-empty and contains the returned potential, "
            f"widest {widest:.3f}"
            if bounded_tested
            else "no strongly connected graph was drawn; criterion vacuous",
        ),
    ]
    return crits, {
        "rays_tested": rays_tested,
        "ray_worst": None if ray_worst == -np.inf else float(ray_worst),
        "bounded_tested": bounded_tested,
        "bounded_failures": bounded_failures,
        "interval_failures": interval_failures,
        "widest_interval": None if widest == -np.inf else float(widest),
    }


def theorem_6(rng: np.random.Generator, shapes: int) -> tuple[list[Criterion], dict]:
    """B4-5: ``w_bar <= 0`` wherever a sub-potential exists."""
    worst_bar = -np.inf
    checked = 0
    for _ in range(shapes):
        n = int(rng.integers(4, 7))
        field = two_way_field(n, rng)
        phi, _ = sub_potential(field)
        if phi is None:
            continue
        _, bar = split(field)
        if bar:
            worst_bar = max(worst_bar, max(bar.values()))
            checked += 1
    return [
        Criterion(
            "B4-5  Theorem 6(1): the symmetric part is non-positive",
            checked > 0 and worst_bar <= TOL,
            f"worst w_bar {worst_bar:.3e} over {checked} fields against {TOL:.0e}",
        )
    ], {"checked": checked, "worst_bar": float(worst_bar)}


def reduction(rng: np.random.Generator) -> tuple[list[Criterion], dict]:
    """B4-6: the antisymmetric case reproduces Theorem 1's potential bitwise.

    Integer potentials, so float64 arithmetic is exact along every path and
    "bitwise" is a claim rather than a rounded tolerance. Bellman-Ford returns
    the longest-walk potential from a super source, which for an exact field is
    ``phi - min(phi)``; the spanning-tree integral returns ``phi - phi[0]``. Both
    are centred on their own minimum before comparison, and the two routines
    share no code path.
    """
    mismatches = []
    tested = 0
    for _ in range(12):
        n = int(rng.integers(3, 6))
        m = int(rng.integers(1, 4))
        adj_g = np.zeros((n, n), dtype=int)
        for i in range(n - 1):
            adj_g[i, i + 1] = adj_g[i + 1, i] = 1
        for i, j in [(0, n - 1)] if n > 2 else []:
            adj_g[i, j] = adj_g[j, i] = 1

        phi_int = rng.integers(-8, 9, size=n).astype(np.float64)
        field = exact_field(phi_int, m)
        omega = cochain_from_field(adj_g, field, m)
        adj_gamma = box_product(adj_g, complete_agent_graph(m))

        psi_tree, residual = potential_from_cochain(adj_gamma, omega)
        directed = from_antisymmetric(omega.weights, m * n)
        psi_bf, reason = sub_potential(directed)
        tested += 1

        if psi_bf is None:
            mismatches.append(("no potential", reason, n, m))
            continue
        a = psi_tree - psi_tree.min()
        b = psi_bf - psi_bf.min()
        if a.tobytes() != b.tobytes() or residual > 0.0:
            mismatches.append(
                ("bytes differ", float(np.abs(a - b).max()), float(residual))
            )

    return [
        Criterion(
            "B4-6  Theorem 6(3): the antisymmetric case reproduces Theorem 1 bitwise",
            not mismatches,
            f"{tested} fields, {len(mismatches)} mismatches; "
            f"potentials compared as raw bytes after centring on the minimum",
        )
    ], {"tested": tested, "mismatches": mismatches}


def directed_squares(rng: np.random.Generator) -> tuple[list[Criterion], dict]:
    """B4-7 and B4-8: the square splits, and the index part ignores a common spread."""
    worst_sum = worst_diff = -np.inf
    worst_invariance = -np.inf
    worst_friction_move = np.inf
    cases = 0
    # B4-9. Theorem 6(4), added 2026-08-19: `S` and `S'` are each a directed
    # four-cycle, so Theorem 4 forces **each** below zero and not merely their
    # sum, whence `-4 S S' <= 0` and `(S - S')^2 <= (S + S')^2`. The random
    # fields drawn here do **not** all admit a potential, so the inequality is
    # not expected to hold on all of them; what is checked is the equivalence
    # that carries it, `S <= 0 and S' <= 0  <=>  |S - S'| <= -(S + S')`.
    both_nonpos = 0
    bound_holds = 0
    equiv_breaks = 0

    for _ in range(20):
        n = int(rng.integers(3, 5))
        m = int(rng.integers(2, 4))
        adj_g = np.zeros((n, n), dtype=int)
        for i in range(n - 1):
            adj_g[i, i + 1] = adj_g[i + 1, i] = 1

        hat = rng.normal(0.0, 1.0, size=(m, n, n))
        hat = hat - np.swapaxes(hat, 1, 2)
        bar = -np.abs(rng.normal(0.0, 0.4, size=(m, n, n)))
        bar = 0.5 * (bar + np.swapaxes(bar, 1, 2))
        forward = hat + bar
        backward = -hat + bar

        field = directed_product(adj_g, m, forward, backward)
        for i, j in undirected_pairs(adj_g):
            for a in range(m):
                for b in range(m):
                    if a == b:
                        continue
                    s, s_rev = directed_square(field, a, b, i, j, n)
                    want_sum = 2.0 * (bar[a, i, j] + bar[b, i, j])
                    want_diff = 2.0 * (hat[a, i, j] - hat[b, i, j])
                    worst_sum = max(worst_sum, abs((s + s_rev) - want_sum))
                    worst_diff = max(worst_diff, abs((s - s_rev) - want_diff))
                    cases += 1
                    neg = (s <= TOL) and (s_rev <= TOL)
                    bnd = abs(s - s_rev) <= -(s + s_rev) + TOL
                    both_nonpos += neg
                    bound_holds += bnd
                    equiv_breaks += (neg != bnd)

        # A spread common to both classes: added to every leg of every class on
        # every position edge, which is what "the market widened" looks like.
        extra = -abs(float(rng.normal(0.0, 0.5)))
        wide = directed_product(adj_g, m, forward + extra, backward + extra)
        for i, j in undirected_pairs(adj_g):
            for a in range(m):
                for b in range(m):
                    if a == b:
                        continue
                    s0, r0 = directed_square(field, a, b, i, j, n)
                    s1, r1 = directed_square(wide, a, b, i, j, n)
                    worst_invariance = max(
                        worst_invariance, abs((s1 - r1) - (s0 - r0))
                    )
                    worst_friction_move = min(
                        worst_friction_move, abs((s1 + r1) - (s0 + r0))
                    )

    # The project's engineering rule 6. The three residuals below are deviations from an
    # identity and sit at machine epsilon, so their last digits are a property
    # of the BLAS build, so writing them into the record makes it differ
    # between machines on content that asserts the same thing. `worst_friction_move` is **not** one
    # of them: it is the magnitude the criterion needs to be large, so it stays
    # in the record.
    for label, value in (
        ("B4-7 |S+S' - friction|", worst_sum),
        ("B4-7 |S-S' - index|", worst_diff),
        ("B4-8 index invariance", worst_invariance),
    ):
        print(
            f"  {label}: {value:.3e} against {TOL:.0e} "
            f"(not written to the record: machine-dependent rounding)"
        )

    return [
        Criterion(
            "B4-7  section 5.1: the directed square splits into friction and index",
            max(worst_sum, worst_diff) <= TOL,
            f"|S+S' - friction| and |S-S' - index| are both at machine "
            f"precision, below `1e-10`, over {cases} squares",
        ),
        Criterion(
            "B4-8  section 5.1: a common spread moves the friction and not the index",
            worst_invariance <= TOL and worst_friction_move > TOL,
            f"index unchanged to machine precision, below `1e-10`; friction "
            f"moved by at least {worst_friction_move:.3e}",
        ),
        Criterion(
            "B4-9  Theorem 6(4): the index part is bounded by the friction part",
            equiv_breaks == 0 and both_nonpos > 0,
            f"`S <= 0 and S' <= 0` and `|S-S'| <= -(S+S')` agree on all "
            f"{cases} squares, {both_nonpos} of which have both cycles "
            f"non-positive; the bound is what Theorem 4 buys once it is "
            f"applied to each cycle rather than to their sum",
        ),
    ], {
        "cases": cases,
        # Dropped from the record 2026-09-08. The line printed above already
        # said they were not written, and they were, at full precision. Each is
        # a deviation from an identity sitting at machine epsilon, so its last
        # digits belong to the BLAS build, which is the case the derived-file
        # rules exist to stop: a phantom diff between two machines buries a real
        # one. The bound they were compared against is the part that is stable.
        "identity_residuals_below": TOL,
        "squares_both_cycles_nonpositive": int(both_nonpos),
        "squares_satisfying_the_index_bound": int(bound_holds),
        "equivalence_breaks": int(equiv_breaks),
        "worst_friction_move": float(worst_friction_move),
    }


def _hat(hat: dict, u: int, v: int) -> float:
    """``split`` keys on ``u < v``. Traversed the other way the antisymmetric
    part changes sign and the symmetric part does not, which is the whole content
    of the split and therefore the one place a cycle walk can go wrong."""
    return hat[(u, v)] if u < v else -hat[(v, u)]


def _bar(bar: dict, u: int, v: int) -> float:
    return bar[(u, v)] if u < v else bar[(v, u)]


def two_way_complete(n: int, rng: np.random.Generator, exact: bool,
                     per_direction: bool = False,
                     spread: float = 0.4) -> DirectedField:
    """A complete two-way field, with the antisymmetric part exact or not.

    ``per_direction`` draws the friction independently for each leg of an edge.
    That is **not** a symmetric friction: the difference between the two legs
    lands in the antisymmetric part, which is Theorem 6(5)'s mechanism one level
    down. It is here as the case the criterion has to be able to see.
    """
    weights: dict[tuple[int, int], float] = {}
    phi = rng.normal(0.0, 1.0, size=n)
    raw = {(u, v): float(rng.normal(0.0, 1.0))
           for u in range(n) for v in range(u + 1, n)}
    ceiling = max(abs(x) for x in raw.values())
    for u in range(n):
        for v in range(u + 1, n):
            hat = float(phi[v] - phi[u]) if exact else raw[(u, v)]
            if per_direction:
                weights[(u, v)] = hat - abs(float(rng.normal(0.0, spread)))
                weights[(v, u)] = -hat - abs(float(rng.normal(0.0, spread)))
            else:
                # A ceiling on the friction when the antisymmetric part is not
                # exact, so that a sub-potential still exists and Theorem 6 has
                # its hypothesis. |sum of hat over a cycle| <= ceiling * length.
                bar = -abs(float(rng.normal(0.0, spread))) - (0.0 if exact else ceiling)
                weights[(u, v)] = hat + bar
                weights[(v, u)] = -hat + bar
    return DirectedField(weights, n)


def cycle_ratio_max(field: DirectedField) -> tuple[float, int]:
    """The largest value of Theorem 6(4)'s ratio over every simple cycle.

    Returns the maximum and the number of cycles whose friction part vanished.
    Corollary 6.1 reads the ratio as zero on those, and that reading is forced:
    a frictionless cycle has both directed sums non-positive and opposite, so
    the numerator is zero there as well.
    """
    hat, bar = split(field)
    worst, degenerate = 0.0, 0
    for cyc in simple_directed_cycles(field):
        legs = list(zip(cyc, cyc[1:]))
        s_hat = sum(_hat(hat, u, v) for u, v in legs)
        s_bar = sum(_bar(bar, u, v) for u, v in legs)
        if abs(s_bar) < 1e-12:
            degenerate += 1
            continue
        worst = max(worst, abs(s_hat) / -s_bar)
    return worst, degenerate


def corollary_6_1(rng: np.random.Generator) -> tuple[list[Criterion], dict]:
    """B4-10 to B4-12: Corollary 6.1, on cycles rather than on the square.

    Section 5.1's square is one cycle of length four, walked in a fixed vertex
    order, with the agent legs set to zero in both directions. Corollary 6.1
    quantifies over every cycle and drops that setting, so what needs checking is
    that ``split`` and ``simple_directed_cycles`` agree about orientation when
    the walk is longer than four and the vertex order is whatever the enumerator
    produced. B4-7 cannot see that: its shape is fixed.
    """
    # B4-10. The identity, on cycles of every length the enumerator produces.
    worst_id, lengths = 0.0, {}
    for _ in range(6):
        field = two_way_complete(5, rng, exact=False)
        hat, bar = split(field)
        for cyc in simple_directed_cycles(field):
            legs = list(zip(cyc, cyc[1:]))
            fwd = sum(field.value(u, v) for u, v in legs)
            rev = sum(field.value(v, u) for u, v in legs)
            s_hat = sum(_hat(hat, u, v) for u, v in legs)
            s_bar = sum(_bar(bar, u, v) for u, v in legs)
            worst_id = max(worst_id, abs((fwd - rev) - 2 * s_hat),
                           abs((fwd + rev) - 2 * s_bar))
            lengths[len(legs)] = lengths.get(len(legs), 0) + 1

    # B4-11. The degenerate cell is forced. Build the case Corollary 6.1 says
    # cannot happen -- a cycle with no friction carrying a non-zero index part --
    # and ask whether a sub-potential exists. It must not, in every draw.
    drawn = admitted = 0
    for _ in range(200):
        n = 4
        raw = {(u, v): float(rng.normal(0.0, 1.0))
               for u in range(n) for v in range(u + 1, n)}
        weights: dict[tuple[int, int], float] = {}
        for (u, v), h in raw.items():
            weights[(u, v)] = h
            weights[(v, u)] = -h          # friction identically zero
        field = DirectedField(weights, n)
        hat, _ = split(field)
        loud = any(
            abs(sum(_hat(hat, u, v) for u, v in zip(c, c[1:]))) > TOL
            for c in simple_directed_cycles(field)
        )
        if not loud:
            continue
        drawn += 1
        admitted += sub_potential(field)[0] is not None

    # B4-12. The equivalence, both ways, with the two cases that must come back
    # non-zero. If ``split`` mixed the two parts the first two rows would move;
    # if the cycle walk lost orientation the last two could collapse to zero.
    rows = {
        "exact, one friction per edge": two_way_complete(5, rng, exact=True),
        "exact, friction an order of magnitude wider":
            two_way_complete(5, rng, exact=True, spread=4.0),
        "not exact": two_way_complete(5, rng, exact=False),
        "friction drawn per direction, so not symmetric":
            two_way_complete(5, rng, exact=True, per_direction=True),
    }
    ratios, degen, potentials = {}, {}, {}
    for label, field in rows.items():
        ratios[label], degen[label] = cycle_ratio_max(field)
        potentials[label] = sub_potential(field)[0] is not None
    zero_rows = [k for k in rows if k.startswith("exact,")]
    loud_rows = [k for k in rows if k not in zero_rows]
    quiet_ok = all(ratios[k] <= TOL for k in zero_rows)
    loud_ok = all(ratios[k] > TOL for k in loud_rows)

    for label in zero_rows:
        print(f"  B4-12 {label}: max ratio {ratios[label]:.3e} against {TOL:.0e} "
              f"(not written to the record: machine-dependent rounding)")
    print(f"  B4-10 identity on arbitrary cycles: {worst_id:.3e} against "
          f"{TOL:.0e} (not written to the record: same reason)")
    print(f"  B4-10 cycle lengths walked: "
          f"{', '.join(f'{k}:{v}' for k, v in sorted(lengths.items()))}")

    return [
        Criterion(
            "B4-10 Corollary 6.1: the square identity holds on a cycle of any length",
            worst_id <= TOL and max(lengths) > 4,
            f"`S-S' = 2*sum(w_hat)` and `S+S' = 2*sum(w_bar)` at machine "
            f"precision, below `1e-9`, over {sum(lengths.values())} cycles of "
            f"lengths {sorted(lengths)}; the square is the length-4 row",
            kind="instrument",
        ),
        Criterion(
            "B4-11 Corollary 6.1: a frictionless cycle cannot carry an index part",
            drawn > 0 and admitted == 0,
            f"{drawn} fields drawn with the friction identically zero and some "
            f"cycle carrying a non-zero index part; {admitted} of them admitted "
            f"a sub-potential, so the case the ratio would read as `0/0` is "
            f"unreachable under Theorem 6's hypothesis rather than handled by a "
            f"convention",
            kind="instrument",
        ),
        Criterion(
            "B4-12 Corollary 6.1: the ratio vanishes exactly on the exact fields",
            quiet_ok and loud_ok,
            "an exact antisymmetric part with a symmetric friction returns a "
            "ratio at machine precision on every cycle, and widening that "
            "friction does not move it; a non-exact part returns "
            f"{ratios['not exact']:.4f} and a friction drawn separately for each "
            f"leg returns "
            f"{ratios['friction drawn per direction, so not symmetric']:.4f}, so "
            "the check can see both sides",
            kind="instrument",
        ),
    ], {
        "identity_residuals_below": TOL,
        "cycles_walked": sum(lengths.values()),
        "cycle_lengths": {str(k): v for k, v in sorted(lengths.items())},
        "frictionless_fields_with_a_loud_cycle": drawn,
        "of_those_admitting_a_sub_potential": admitted,
        # The two the criterion needs to be large stay, as `worst_friction_move`
        # does above. The two it needs to be at machine epsilon do not.
        "ratio_not_exact": float(f"{ratios['not exact']:.6f}"),
        "ratio_friction_per_direction": float(
            f"{ratios['friction drawn per direction, so not symmetric']:.6f}"),
        "sub_potential_exists": potentials,
        "degenerate_cycles_seen": degen,
    }


def one_way_report(rng: np.random.Generator) -> dict:
    """Section 5.2, reported rather than scored: what the split does on one-way edges.

    Not a criterion. It records that ``split`` declines to produce a value where
    the reverse leg is absent, which is the behaviour section 5.2 requires, and it
    is stated as a count so a future change that starts imputing reverses shows up
    as a number moving rather than as silence.
    """
    field = random_directed(6, rng, density=0.4, scale=0.3)
    hat, _ = split(field)
    return {
        "edges": len(field.weights),
        "two_way_pairs": len(field.two_way()),
        "one_way_edges": len(field.one_way()),
        "split_entries": len(hat),
        "split_covers_only_two_way": len(hat) == len(field.two_way()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shapes", type=int, default=DEFAULT_SHAPES)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    print("B4: the directed theorem")
    print("  pure theory; no data is read and no parameter is calibrated\n")

    crits: list[Criterion] = []
    # ``shapes_drawn`` rather than ``shapes``: a key named ``shapes`` is B1's
    # list of graph shapes, and a reader of both would take one for the other.
    record: dict = {"stage": "B4", "seed": args.seed, "shapes_drawn": args.shapes}

    for name, fn in (
        ("theorem_4", lambda: theorem_4(rng, args.shapes)),
        ("theorem_5", lambda: theorem_5(rng, args.shapes)),
        ("theorem_6", lambda: theorem_6(rng, args.shapes)),
        ("reduction", lambda: reduction(rng)),
        ("squares", lambda: directed_squares(rng)),
        ("corollary_6_1", lambda: corollary_6_1(rng)),
    ):
        got, detail = fn()
        crits.extend(got)
        record[name] = detail

    record["one_way"] = one_way_report(rng)

    for c in crits:
        print(c.line())
    print()

    # The list-of-records shape is this repository's criterion shape. A
    # name->bool mapping loses the detail string, which is the part that says
    # what the criterion actually measured.
    record["criteria"] = [
        {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
        | ({"kind": c.kind} if c.kind else {})
        for c in crits
    ]
    n_pass = sum(c.passed for c in crits)
    print(f"  {n_pass}/{len(crits)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b4_directed_edges.json"
    out.write_text(
        json.dumps(record, indent=2, default=str) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
