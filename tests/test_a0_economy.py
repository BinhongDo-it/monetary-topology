"""Tests for stage A0.

Not a formality. Two of these are the self-consistency criterion from the plan
expressed as code: if stock-flow consistency or the issuance-equals-retention
identity fails, the model is broken and any figure it produces is noise.

The rest guard the stage's pass criteria so a later refactor cannot quietly
break a published result.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from monetary_topology import (
    Adjacency,
    EconomyConfig,
    MonetaryAuthority,
    SpendRule,
    Strata,
    run,
)
from monetary_topology.config import LAYER_1
from monetary_topology.variants import variant

# -- configuration validation ------------------------------------------------


def test_wealth_shares_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="wealth_share"):
        Strata(counts=(49, 40, 10, 1), wealth_share=(0.1, 0.3, 0.3, 0.2))


def test_agent_counts_must_sum_to_one_hundred() -> None:
    with pytest.raises(ValueError, match="100 agents"):
        Strata(counts=(49, 40, 10, 2), wealth_share=(0.1, 0.3, 0.3, 0.3))


def test_adjacency_rows_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="rows must sum"):
        Adjacency(
            flow=(
                (0.5, 0.5, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 0.5),
            )
        )


def test_adjacency_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Adjacency(
            flow=(
                (1.2, -0.2, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        )


def test_propensities_must_be_bounded() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        SpendRule(low=(0.5, 0.5, 0.5, 0.5), high=(1.0, 1.0, 1.0, 1.4))


def test_unknown_issuance_rule_rejected() -> None:
    with pytest.raises(ValueError, match="unknown issuance rule"):
        MonetaryAuthority(rule="helicopter")


def test_downward_edge_cannot_exceed_available_share() -> None:
    with pytest.raises(ValueError, match="available intra-layer share"):
        Adjacency().with_downward_edge(0.95)


# -- retention ordering ------------------------------------------------------


def test_retention_rate_is_weakly_ordered_top_to_bottom() -> None:
    """The source's ordering: upper strata withhold more.

    Weak rather than strict, because the source's own worked example gives the
    top two strata an identical propensity of one half.
    """
    sigma = SpendRule().retention_rate
    assert sigma[3] >= sigma[2] >= sigma[1] >= sigma[0]
    assert sigma[3] > sigma[0]


def test_default_parameters_put_layer_two_in_a_death_zone() -> None:
    """Outflow exceeds downward inflow. The criterion is a parameter, not a
    result: the stage traces consequences, it does not derive the shortfall."""
    assert EconomyConfig().flow_balance() > 1.0


# -- self-consistency --------------------------------------------------------


@pytest.mark.parametrize("rule", ["none", "fixed", "endogenous"])
def test_claims_change_only_by_issuance(rule: str) -> None:
    """Total claims change only by issuance, never by circulation.

    ``Economy.run`` raises on violation, so reaching the assertion means the
    within-round check passed every round. Here the across-round identity too.
    """
    cfg = EconomyConfig(authority=MonetaryAuthority(rule=rule), rounds=150, seed=1)
    h = run(cfg)
    np.testing.assert_allclose(
        h.total_claims, cfg.initial_claims + h.cumulative_issuance, atol=1e-9
    )


def test_holdings_never_go_negative() -> None:
    h = run(EconomyConfig(rounds=300, seed=2))
    assert h.holdings.min() >= -1e-12


def test_active_plus_dormant_equals_total() -> None:
    h = run(EconomyConfig(rounds=150, seed=3))
    np.testing.assert_allclose(
        h.active_claims + h.dormant_claims, h.total_claims, atol=1e-9
    )


def test_issuance_equals_lagged_retention() -> None:
    """Under the endogenous rule, what is issued is what retention removed.

    This is the identity behind "the rise in M/R equals cumulative retention".
    Issuance is credited one round after the observation that triggered it, so
    the series are compared with a one-round shift.
    """
    h = run(EconomyConfig(authority=MonetaryAuthority(rule="endogenous"), rounds=200))
    np.testing.assert_allclose(h.issuance[1:], h.retention[:-1], atol=1e-9)


def test_runs_are_reproducible() -> None:
    a = run(EconomyConfig(rounds=80, seed=11))
    b = run(EconomyConfig(rounds=80, seed=11))
    np.testing.assert_array_equal(a.active_claims, b.active_claims)


# -- pass criterion 1: the two ratios diverge --------------------------------


def test_active_ratio_flat_while_total_ratio_rises() -> None:
    """The targeted ratio settles; the untargeted one climbs without bound.

    Plan criterion: the active ratio's tail standard deviation must be under 5%
    of the total ratio's drift over the same window.
    """
    h = run(
        EconomyConfig(
            authority=MonetaryAuthority(rule="endogenous"), rounds=400, seed=4
        )
    )
    window = 50
    drift = float(h.total_ratio[-1] - h.total_ratio[-window])
    assert drift > 0, "total ratio must rise"
    assert h.tail_std("active_ratio", window) < 0.05 * drift


def test_total_ratio_is_monotone_under_endogenous_issuance() -> None:
    h = run(
        EconomyConfig(
            authority=MonetaryAuthority(rule="endogenous"), rounds=300, seed=5
        )
    )
    assert np.all(np.diff(h.total_ratio) >= -1e-12)


def test_issuance_accumulates_in_layer_one() -> None:
    """Issued to restore Layer 2 circulation, retained in Layer 1.

    The instrument cannot reach what it targets: the only downward edge is a
    fixed wage bill, so issuance raises Layer 1's holdings without raising the
    active pool.
    """
    h = run(
        EconomyConfig(
            authority=MonetaryAuthority(rule="endogenous"), rounds=400, seed=6
        )
    )
    assert h.layer1_share[-1] > h.layer1_share[0]
    assert h.tail_mean("layer1_share", 50) > 0.9


def test_layer_two_holdings_decline() -> None:
    h = run(EconomyConfig(rounds=300, seed=6))
    assert h.tail_mean("layer2_holdings", 50) < h.layer2_holdings[0]


# -- pass criterion 2 and 3: quantity versus topology ------------------------


#: Range over which the flatness claim is asserted. The lower bound is not
#: cosmetic: below roughly 0.05 the intermediate stratum cannot fund its share
#: of payroll, and the wage channel itself narrows. That boundary case is a
#: separate test rather than a loosened tolerance.
TOP_PROPENSITIES = (0.05, 0.1, 0.25, 0.5, 0.75, 1.0)


def test_top_spending_rate_does_not_change_layer_two_inflow() -> None:
    """The sweep is flat, to floating-point equality.

    Taking the top stratum from spending a twentieth of its holdings to spending
    all of them leaves Layer 2's claim inflow bit-for-bit unchanged, because the
    adjacency matrix gives that spending nowhere to land outside its own layer.

    This is the direct answer to the standard rebuttal that the money must end
    up somewhere and so must eventually reach the bottom. It ends up somewhere.
    The somewhere has no edge to Layer 2.
    """
    base = EconomyConfig(rounds=300, seed=7)
    outcomes = [
        run(variant(base, spend=base.spend.with_top_propensity(p))).tail_mean(
            "active_claims", 50
        )
        for p in TOP_PROPENSITIES
    ]
    spread = max(outcomes) - min(outcomes)
    assert spread < 1e-9 * max(1.0, float(np.mean(outcomes))), (
        f"Layer 2 inflow varied by {spread:.3e} across the spending sweep; "
        f"expected flat. outcomes={outcomes}"
    )


def test_total_hoarding_at_the_top_starves_the_wage_channel() -> None:
    """The one boundary where top spending does matter, and it points the wrong
    way for the trickle-down reading.

    At a propensity near zero the intermediate stratum is not resupplied, its
    holdings fall below its share of payroll, and the wage bill is capped. Layer
    2's inflow then falls. So the top's spending can matter to Layer 2, but only
    by keeping the intermediary solvent enough to make payroll, never by
    reaching Layer 2 as demand. More spending above that threshold buys nothing.

    This is the wage paradox in miniature: the intermediate layer is squeezed
    from both sides, and the pressure is visible on the payroll edge rather than
    in either party's discretionary behaviour.
    """
    base = EconomyConfig(rounds=300, seed=7)
    hoarding = run(variant(base, spend=base.spend.with_top_propensity(0.0)))
    spending = run(variant(base, spend=base.spend.with_top_propensity(0.05)))

    assert hoarding.tail_mean("active_claims", 50) < spending.tail_mean(
        "active_claims", 50
    )
    # The channel narrowed because the intermediary ran dry, not because
    # discretionary demand fell.
    intermediate = LAYER_1[0]
    payroll_share = base.wages.source_shares[intermediate] * base.wages.bill
    assert hoarding.holdings[-50:, intermediate].mean() < payroll_share
    assert spending.holdings[-50:, intermediate].mean() > payroll_share


def test_top_spending_rate_does_change_layer_one_churn() -> None:
    """The control showing the sweep is not inert.

    The same sweep that leaves Layer 2 untouched moves circulation inside
    Layer 1 by orders of magnitude. Money is demonstrably moving. It is simply
    moving where the production layer cannot reach it.
    """
    base = EconomyConfig(rounds=300, seed=7)
    low = run(variant(base, spend=base.spend.with_top_propensity(0.1))).tail_mean(
        "layer1_churn", 50
    )
    high = run(variant(base, spend=base.spend.with_top_propensity(1.0))).tail_mean(
        "layer1_churn", 50
    )
    assert high > 5.0 * low, f"churn moved only from {low:.3f} to {high:.3f}"


def test_opening_a_downward_edge_does_change_layer_two_inflow() -> None:
    """Topology moves what quantity could not.

    A single edge from the top stratum into Layer 2 raises its claim inflow
    substantially. Quantity of money is not what governs access; adjacency is.
    """
    base = EconomyConfig(rounds=300, seed=7)
    closed = run(base).tail_mean("active_claims", 50)
    opened = run(
        variant(base, adjacency=base.adjacency.with_downward_edge(0.40))
    ).tail_mean("active_claims", 50)
    assert opened > 1.5 * closed, (
        f"opening a 0.40 downward edge moved inflow from {closed:.4f} to "
        f"{opened:.4f}; expected a substantial rise"
    )


def test_downward_edge_response_is_monotone() -> None:
    """Widening the edge monotonically increases Layer 2 inflow."""
    base = EconomyConfig(rounds=300, seed=8)
    outcomes = [
        run(variant(base, adjacency=base.adjacency.with_downward_edge(w))).tail_mean(
            "active_claims", 50
        )
        for w in (0.0, 0.1, 0.2, 0.4, 0.6, 0.8)
    ]
    assert all(b >= a for a, b in pairwise(outcomes)), outcomes
