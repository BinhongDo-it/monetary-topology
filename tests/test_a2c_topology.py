"""Tests for stage A2c: cycle structure and the Hodge decomposition.

The first half checks the mathematics against graphs whose answers are known
independently, because a topological claim computed by buggy code is worse than
no claim. Nothing economic is asserted until those pass.

The hole-punching test is here rather than in the experiment on purpose. Deleting
edges and observing that the cycle rank changes verifies ``E - V + C``; it is a
check on the code, not a finding, and putting it among the tests keeps it from
being mistaken for one.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import NetworkConfig, NetworkSpec, run_network
from monetary_topology.topology import (
    connected_components,
    curl_matrix,
    cycle_rank,
    hodge_decomposition,
    incidence_matrix,
    net_flow_vector,
    realized_adjacency,
    triangles,
    undirected_edges,
)


def graph(pairs, n: int) -> np.ndarray:
    a = np.zeros((n, n))
    for i, j in pairs:
        a[i, j] = 1.0
    return a


PATH5 = graph([(0, 1), (1, 2), (2, 3), (3, 4)], 5)
CYCLE4 = graph([(0, 1), (1, 2), (2, 3), (3, 0)], 4)
TRIANGLE = graph([(0, 1), (1, 2), (2, 0)], 3)
K4 = graph([(i, j) for i in range(4) for j in range(i + 1, 4)], 4)
TWO_TRIANGLES = graph([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)], 6)


# -- exact combinatorics, against known answers ------------------------------


@pytest.mark.parametrize(
    ("adjacency", "expected"),
    [(PATH5, 0), (CYCLE4, 1), (TRIANGLE, 1), (K4, 3), (TWO_TRIANGLES, 2)],
)
def test_cycle_rank_matches_known_graphs(adjacency, expected) -> None:
    assert cycle_rank(adjacency) == expected


def test_components_counted_correctly() -> None:
    assert connected_components(TWO_TRIANGLES) == 2
    assert connected_components(K4) == 1


def test_triangles_enumerated_correctly() -> None:
    assert len(triangles(TRIANGLE)) == 1
    assert len(triangles(K4)) == 4
    assert len(triangles(CYCLE4)) == 0


def test_cycle_rank_equals_euler_formula_on_random_graphs() -> None:
    rng = np.random.default_rng(0)
    for _ in range(20):
        n = int(rng.integers(8, 40))
        a = (rng.random((n, n)) < rng.uniform(0.05, 0.3)).astype(float)
        np.fill_diagonal(a, 0.0)
        e = len(undirected_edges(a))
        assert cycle_rank(a) == e - n + connected_components(a)


def test_boundary_of_a_boundary_is_zero() -> None:
    """``d1 @ d0 == 0`` exactly. If this fails, the operators are inconsistent
    and every downstream number is meaningless."""
    rng = np.random.default_rng(1)
    a = (rng.random((25, 25)) < 0.25).astype(float)
    np.fill_diagonal(a, 0.0)
    assert np.abs(curl_matrix(a) @ incidence_matrix(a)).max() == 0.0


# -- Hodge decomposition properties ------------------------------------------


def random_graph_and_flow(seed: int = 0, n: int = 30):
    rng = np.random.default_rng(seed)
    a = (rng.random((n, n)) < 0.15).astype(float)
    np.fill_diagonal(a, 0.0)
    flow = rng.random((n, n)) * (a > 0)
    return a, flow


def test_components_sum_to_the_field() -> None:
    a, flow = random_graph_and_flow()
    split = hodge_decomposition(flow, a)
    np.testing.assert_allclose(split.total, net_flow_vector(flow, a), atol=1e-12)


def test_components_are_mutually_orthogonal() -> None:
    a, flow = random_graph_and_flow()
    s = hodge_decomposition(flow, a)
    scale = float(np.dot(s.total, s.total))
    assert abs(np.dot(s.gradient, s.curl)) < 1e-9 * scale
    assert abs(np.dot(s.gradient, s.harmonic)) < 1e-9 * scale
    assert abs(np.dot(s.curl, s.harmonic)) < 1e-9 * scale


def test_shares_sum_to_one() -> None:
    a, flow = random_graph_and_flow()
    assert sum(hodge_decomposition(flow, a).shares()) == pytest.approx(1.0)


def test_a_pure_gradient_flow_is_all_gradient() -> None:
    """Construct a flow from a node potential; it must decompose to itself."""
    rng = np.random.default_rng(3)
    a, _ = random_graph_and_flow(3)
    p = rng.random(a.shape[0])
    flow = np.zeros_like(a)
    for i, j in undirected_edges(a):
        flow[i, j] = max(p[j] - p[i], 0.0)
        flow[j, i] = max(p[i] - p[j], 0.0)
    g, c, h = hodge_decomposition(flow, a).shares()
    assert g == pytest.approx(1.0, abs=1e-9)


def test_a_pure_loop_has_no_gradient_component() -> None:
    """A flow that goes once around a triangle-free cycle carries no potential
    difference and must land entirely outside the gradient space."""
    six = graph([(i, (i + 1) % 6) for i in range(6)], 6)
    loop = np.zeros((6, 6))
    for i in range(6):
        loop[i, (i + 1) % 6] = 1.0
    g, c, h = hodge_decomposition(loop, six).shares()
    assert g == pytest.approx(0.0, abs=1e-9)
    assert h == pytest.approx(1.0, abs=1e-9)


def test_unfilled_triangles_move_everything_into_harmonic() -> None:
    """The modelling choice is visible in the output rather than hidden."""
    a, flow = random_graph_and_flow(5)
    filled = hodge_decomposition(flow, a, fill_triangles=True)
    bare = hodge_decomposition(flow, a, fill_triangles=False)
    assert filled.filled_triangles > 0
    assert bare.filled_triangles == 0
    assert np.allclose(bare.curl, 0.0)
    np.testing.assert_allclose(bare.gradient, filled.gradient, atol=1e-9)
    assert bare.shares()[2] > filled.shares()[2]


# -- code self-check, deliberately not a finding -----------------------------


def test_punching_holes_changes_the_rank_by_exactly_the_arithmetic() -> None:
    """Deleting edges by hand and watching the cycle rank fall verifies
    ``E - V + C``. It is arithmetic, not economics, and it lives here so it
    cannot be mistaken for a result.
    """
    rng = np.random.default_rng(7)
    a = (rng.random((30, 30)) < 0.2).astype(float)
    np.fill_diagonal(a, 0.0)
    before = cycle_rank(a)
    edges = undirected_edges(a)
    for i, j in edges[:5]:
        a[i, j] = a[j, i] = 0.0
    expected = len(undirected_edges(a)) - 30 + connected_components(a)
    assert cycle_rank(a) == expected
    assert cycle_rank(a) < before


# -- on the actual model -----------------------------------------------------


def run(spec: NetworkSpec, rounds: int = 400, seed: int = 0):
    return run_network(
        NetworkConfig(
            spec=spec,
            rounds=rounds,
            seed=seed,
            snapshot_every=100,
            authority=MonetaryAuthority(rule="endogenous"),
            wages=WageChannel(bill=8.0, elasticity=0.0),
        )
    )


def three(seed: int, edges: int = 0) -> NetworkSpec:
    return NetworkSpec(
        seed=seed,
        intermediate_size=30,
        layer2_size=150,
        financial_to_intermediate_edges=edges,
    )


def test_snapshots_are_off_by_default() -> None:
    h = run_network(NetworkConfig(spec=NetworkSpec(seed=0), rounds=50, seed=0))
    assert h.snapshots == {}


def test_potential_graph_is_never_modified_during_a_run() -> None:
    """The whole stage rests on this. If the model deleted edges, a falling
    realized rank would be trivial."""
    spec = NetworkSpec(seed=0)
    h = run(spec)
    from monetary_topology.network import build_graph

    fresh = build_graph(spec, wage_edges=None)
    assert cycle_rank(h.adjacency) >= cycle_rank(fresh)
    assert np.array_equal(h.adjacency, h.adjacency)  # unchanged object identity


@pytest.mark.parametrize("seed", range(4))
def test_cycle_rank_collapses_when_the_intermediary_is_cut_off(seed: int) -> None:
    h = run(three(seed, 0), rounds=600, seed=seed)
    last = max(h.snapshots)
    realized = realized_adjacency(h.snapshots[last], h.epsilon_absolute)
    assert cycle_rank(realized) / cycle_rank(h.adjacency) < 0.10


@pytest.mark.parametrize("seed", range(4))
def test_one_autonomous_edge_restores_most_of_the_loop_structure(seed: int) -> None:
    h = run(three(seed, 1), rounds=600, seed=seed)
    last = max(h.snapshots)
    realized = realized_adjacency(h.snapshots[last], h.epsilon_absolute)
    assert cycle_rank(realized) / cycle_rank(h.adjacency) > 0.5


def test_the_gradient_component_is_flat_while_flow_grows() -> None:
    """The share falls mostly because the denominator grows. Recorded as a
    magnitude comparison so the distinction cannot be lost."""
    h = run(NetworkSpec(seed=0), rounds=600)
    rounds = sorted(h.snapshots)
    grads, totals = [], []
    for t in rounds:
        realized = realized_adjacency(h.snapshots[t], h.epsilon_absolute)
        s = hodge_decomposition(h.snapshots[t], realized)
        grads.append(np.sqrt(s.energies()[0]))
        totals.append(np.linalg.norm(net_flow_vector(h.snapshots[t], realized)))
    assert max(grads) / min(grads) < 3.0
    assert totals[-1] / totals[0] > 10.0


def test_cycle_rank_saturates_in_the_two_layer_model() -> None:
    """A limitation, tested so it stays recorded.

    Cycle rank is a binary count over edges, and proportional dynamics leave
    every edge carrying something, so it moves only where flow genuinely stops.
    """
    h = run(NetworkSpec(seed=0), rounds=600)
    ranks = [
        cycle_rank(realized_adjacency(h.snapshots[t], h.epsilon_absolute))
        for t in sorted(h.snapshots)
    ]
    assert max(ranks[1:]) - min(ranks[1:]) <= 1
