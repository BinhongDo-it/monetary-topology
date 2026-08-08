"""Tests for stage A2: the network model and the intermediate layer.

Two tests here are backward-compatibility guards rather than findings. The graph
model must reduce to the block model's qualitative results, and the three-layer
graph must reduce bitwise to the two-layer one when the intermediate is empty. If
either fails, A2 is a different model rather than a refinement of A0 and nothing
downstream can be compared across stages.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import (
    Network,
    NetworkConfig,
    NetworkSpec,
    build_graph,
    effective_support,
    reachable_from,
    run_network,
)

SEEDS = range(6)


def go(spec: NetworkSpec, *, rule="endogenous", e=0.0, rounds=400, seed=0):
    return run_network(
        NetworkConfig(
            spec=spec,
            rounds=rounds,
            seed=seed,
            authority=MonetaryAuthority(rule=rule),
            wages=WageChannel(bill=8.0, elasticity=e),
        )
    )


def three(seed=0, size=30, **kw):
    return NetworkSpec(seed=seed, intermediate_size=size, layer2_size=180 - size, **kw)


# -- validation --------------------------------------------------------------


def test_intermediate_needs_at_least_two_nodes() -> None:
    with pytest.raises(ValueError, match="at least two nodes"):
        NetworkSpec(intermediate_size=1)


def test_negative_autonomous_edges_rejected() -> None:
    with pytest.raises(ValueError, match="financial_to_intermediate_edges"):
        NetworkSpec(intermediate_size=10, financial_to_intermediate_edges=-1)


def test_zero_epsilon_rejected() -> None:
    with pytest.raises(ValueError, match="epsilon must be positive"):
        NetworkConfig(epsilon=0.0)


# -- primitives --------------------------------------------------------------


def test_effective_support_equals_node_count_when_flow_is_even() -> None:
    assert effective_support(np.ones(50)) == pytest.approx(50.0)


def test_effective_support_is_one_when_a_single_node_takes_everything() -> None:
    x = np.zeros(50)
    x[3] = 1.0
    assert effective_support(x) == pytest.approx(1.0)


def test_effective_support_is_zero_on_no_flow() -> None:
    assert effective_support(np.zeros(10)) == 0.0


def test_reachability_ignores_edges_below_the_cutoff() -> None:
    flow = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1e-9], [0.0, 0.0, 0.0]])
    assert reachable_from(flow, 0, 1e-6).tolist() == [True, True, False]
    assert reachable_from(flow, 0, 1e-12).tolist() == [True, True, True]


# -- backward compatibility --------------------------------------------------


def test_empty_intermediate_is_bitwise_identical_to_the_two_layer_graph() -> None:
    a = go(NetworkSpec(seed=0))
    b = go(NetworkSpec(seed=0, intermediate_size=0))
    np.testing.assert_array_equal(a.total_volume, b.total_volume)
    np.testing.assert_array_equal(a.effective_support, b.effective_support)


def test_graph_reproduces_the_block_model_accumulation_result() -> None:
    """A0-9 on the disaggregated graph.

    The block model puts 0.998 of all claims in the financial layer at steady
    state. The graph should land in the same place; if it did not, the two
    stages would not be describing the same economy.
    """
    for seed in SEEDS:
        h = go(NetworkSpec(seed=seed), seed=seed)
        share = (h.holdings[:, :20].sum(axis=1) / h.holdings.sum(axis=1))[-50:].mean()
        assert 0.99 < share < 1.0


# -- the injection breaks the sign relation ----------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_without_issuance_volume_and_support_agree(seed: int) -> None:
    v, s = go(NetworkSpec(seed=seed), rule="none", seed=seed).divergence
    assert (v - 1) * (s - 1) > 0


@pytest.mark.parametrize("seed", SEEDS)
def test_with_issuance_volume_rises_while_support_contracts(seed: int) -> None:
    v, s = go(NetworkSpec(seed=seed), rule="endogenous", seed=seed).divergence
    assert v > 1.0
    assert s < 1.0


# -- reachability decides, not propensity ------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_maximal_propensity_without_in_edges_still_dies(seed: int) -> None:
    """The framework's disagreement with the marginal-propensity account.

    Propensity is a property of the agent, reachability a property of the graph.
    Give a node the highest possible propensity and remove its in-edges, and it
    terminates at zero regardless.
    """
    spec = NetworkSpec(seed=seed)
    net = Network(NetworkConfig(spec=spec, rounds=200, seed=seed))
    node = int(spec.household_nodes[0])
    net._p_low[node] = net._p_high[node] = 1.0
    net.adjacency[:, node] = 0.0
    net._route[:, node] = 0.0
    rs = net._route.sum(axis=1, keepdims=True)
    net._route = np.divide(net._route, rs, out=np.zeros_like(net._route), where=rs > 0)
    net._wage_receivers = net._wage_receivers[net._wage_receivers != node]
    assert net.run().holdings[-1, node] == 0.0


# -- the intermediate layer, H1 and H2 ---------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_two_layer_payroll_channel_never_narrows(seed: int) -> None:
    h = go(NetworkSpec(seed=seed), seed=seed)
    assert h.wage_funding_ratio[-25:].mean() == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("size", [10, 30, 60])
def test_h1_intermediate_closes_the_channel_it_operates(seed: int, size: int) -> None:
    """The bill owed is constant and the elasticity is zero, so nothing in the
    rule cuts hiring. The channel closes because its operator runs out."""
    h = go(three(seed, size), rounds=600, seed=seed)
    assert np.all(h.wage_owed == h.wage_owed[0])
    assert h.wage_funding_ratio[-25:].mean() < 1e-6
    assert h.intermediate_holdings[-25:].mean() < 1e-6


@pytest.mark.parametrize("seed", SEEDS)
def test_h2_three_layer_at_zero_elasticity_sits_on_the_boundary(seed: int) -> None:
    """A three-layer economy with its elasticity parameter set to zero lands
    where the two-layer economy only reaches at unit elasticity."""
    at_zero = go(NetworkSpec(seed=seed), e=0.0, rounds=600, seed=seed)
    at_one = go(NetworkSpec(seed=seed), e=1.0, rounds=600, seed=seed)
    layered = go(three(seed), e=0.0, rounds=600, seed=seed)

    assert at_zero.layer2_inflow[-25:].mean() > 1.0
    assert at_one.layer2_inflow[-25:].mean() < 1e-6
    assert layered.layer2_inflow[-25:].mean() < 1e-6


# -- one customer in the layer above -----------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_a_single_autonomous_edge_rescues_the_economy(seed: int) -> None:
    """Existence dominates magnitude, for the third time in this repository.

    The caveat belongs with the claim: a discontinuity at zero is not surprising
    on its own, because reachability is binary and an unreachable set is simply
    unreachable. What the run supplies is the magnitude on the far side of the
    jump and how fast it saturates, and only those are results.
    """
    none = go(three(seed, financial_to_intermediate_edges=0), rounds=600, seed=seed)
    one = go(three(seed, financial_to_intermediate_edges=1), rounds=600, seed=seed)
    many = go(three(seed, financial_to_intermediate_edges=30), rounds=600, seed=seed)

    a = none.layer2_inflow[-25:].mean()
    b = one.layer2_inflow[-25:].mean()
    c = many.layer2_inflow[-25:].mean()

    assert a < 1e-6
    assert b > 0.5 * c
    assert c / b < 2.0


# -- structural sanity -------------------------------------------------------


def test_households_buy_from_the_intermediate_when_it_exists() -> None:
    spec = three(0)
    g = build_graph(spec)
    hh, mid = spec.household_nodes, spec.intermediate_nodes
    assert g[np.ix_(hh, hh)].sum() == 0
    assert g[np.ix_(hh, mid)].sum() > 0


def test_no_downward_discretionary_edge_by_default() -> None:
    spec = NetworkSpec(seed=0)
    g = build_graph(spec)
    assert g[np.ix_(spec.financial_nodes, spec.household_nodes)].sum() == 0


def test_leakage_ratio_is_heterogeneous_unless_uniform_is_requested() -> None:
    spec = NetworkSpec(seed=0)
    g = build_graph(spec)
    n1 = spec.layer1_size
    up = g[n1:, :n1].sum(axis=1)
    inside = g[n1:, n1:].sum(axis=1)
    ratio = up / np.maximum(up + inside, 1)
    assert len(np.unique(np.round(ratio, 4))) > 5

    uniform = build_graph(NetworkSpec(seed=0, uniform_degree=True))
    up_u = uniform[n1:, :n1].sum(axis=1)
    inside_u = uniform[n1:, n1:].sum(axis=1)
    ratio_u = up_u / np.maximum(up_u + inside_u, 1)
    assert len(np.unique(np.round(ratio_u, 4))) == 1


def test_claims_are_conserved_except_by_issuance() -> None:
    """The run raises on violation, so arriving here means every round passed."""
    for rule in ("none", "fixed", "endogenous"):
        h = go(NetworkSpec(seed=1), rule=rule, rounds=150, seed=1)
        total = h.holdings.sum(axis=1)
        expected = 100.0 + np.cumsum(h.issuance)
        np.testing.assert_allclose(total, expected, atol=1e-8)


def test_degree_heterogeneity_is_not_load_bearing() -> None:
    """Reported as a negative result rather than quietly kept.

    The heavy-tailed leakage ratio was expected to drive the contraction. It does
    not: the homogeneous control gives the same divergence. What drives it is the
    layer structure together with the injection point.
    """
    v_h, s_h = go(NetworkSpec(seed=0), seed=0).divergence
    v_u, s_u = go(NetworkSpec(seed=0, uniform_degree=True), seed=0).divergence
    assert abs(v_h - v_u) / v_h < 0.15
    assert abs(s_h - s_u) / s_h < 0.15
