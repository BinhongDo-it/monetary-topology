"""Tests for the derived-demand wage channel and the calibrated presets.

The first test is the most important one in the file: adding derived demand must
be a strict generalisation, so at zero elasticity every earlier result has to be
reproduced bitwise. If that fails, the published A0 figures are no longer the
figures this code produces.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from monetary_topology import EconomyConfig, WageChannel, run
from monetary_topology.calibration import (
    DFA_COUNTS,
    DFA_NET_WORTH_SHARES,
    dfa_calibrated,
    presets,
    source_faithful,
)
from monetary_topology.variants import variant


def with_wages(base, elasticity: float, floor_share: float = 0.0):
    return variant(
        base,
        wages=WageChannel(
            bill=base.wages.bill,
            elasticity=elasticity,
            floor_share=floor_share,
            source_shares=base.wages.source_shares,
            dest_shares=base.wages.dest_shares,
        ),
    )


ALL_PRESETS = [source_faithful, dfa_calibrated]


# -- validation --------------------------------------------------------------


def test_negative_elasticity_rejected() -> None:
    with pytest.raises(ValueError, match="elasticity must be non-negative"):
        WageChannel(elasticity=-0.1)


def test_floor_share_bounded() -> None:
    with pytest.raises(ValueError, match=r"floor_share must lie in \[0, 1\]"):
        WageChannel(floor_share=1.5)


def test_variant_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="unknown config fields"):
        variant(EconomyConfig(), elasticity=0.5)


# -- backward compatibility --------------------------------------------------


def test_zero_elasticity_is_bitwise_identical_to_a_fixed_bill() -> None:
    """The addition is a strict generalisation.

    At zero elasticity ``bill_at`` returns the baseline without consulting the
    reference level, so this is exact equality rather than approximate.
    """
    base = EconomyConfig(rounds=300, seed=7)
    fixed = run(base)
    derived = run(with_wages(base, 0.0))
    np.testing.assert_array_equal(derived.layer2_spending, fixed.layer2_spending)
    np.testing.assert_array_equal(derived.active_claims, fixed.active_claims)
    np.testing.assert_array_equal(derived.wage_bill, fixed.wage_bill)


def test_fixed_bill_is_actually_constant() -> None:
    base = EconomyConfig(rounds=200, seed=7)
    h = run(base)
    assert np.all(h.wage_bill == base.wages.bill)


# -- the boundary ------------------------------------------------------------


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_positive_steady_state_below_unit_elasticity(factory) -> None:
    base = variant(factory(), rounds=800, seed=7)
    for e in (0.0, 0.25, 0.5, 0.75, 0.9):
        h = run(with_wages(base, e))
        assert h.tail_mean("layer2_spending", 25) > 0.0
        assert not h.collapsed


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_no_steady_state_at_or_above_unit_elasticity(factory) -> None:
    """The boundary is structural, not numerical.

    Below one the bill retains a constant term W0*(1-e) that anchors a fixed
    point. At one that term is gone, so the only fixed point is zero.
    """
    base = variant(factory(), rounds=800, seed=7)
    for e in (1.0, 1.1, 1.5, 2.0, 3.0):
        h = run(with_wages(base, e))
        assert h.tail_mean("layer2_spending", 25) < 1e-6
        assert h.collapsed


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_level_falls_monotonically_in_elasticity(factory) -> None:
    base = variant(factory(), rounds=800, seed=7)
    levels = [
        run(with_wages(base, e)).tail_mean("layer2_spending", 25)
        for e in np.arange(0.0, 1.05, 0.05)
    ]
    assert all(b <= a + 1e-9 for a, b in pairwise(levels))


# -- what survives the boundary ----------------------------------------------


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_survival_is_exactly_linear_in_the_autonomous_share(factory) -> None:
    """Above the boundary, the surviving level is proportional to the part of
    the downward flow that Layer 2's own decline cannot cut.

    Tested as a line through the origin rather than a general fit: the intercept
    being zero is the substantive claim, since a non-zero intercept would mean
    something other than the autonomous flow was keeping the layer alive.
    """
    base = variant(factory(), rounds=800, seed=7)
    shares = np.array([0.0, 0.05, 0.10, 0.20, 0.40])
    levels = np.array(
        [
            run(with_wages(base, 1.5, float(fs))).tail_mean("layer2_spending", 25)
            for fs in shares
        ]
    )
    slope = float(levels[-1] / shares[-1])
    np.testing.assert_allclose(levels, slope * shares, atol=1e-9)


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_full_autonomous_share_recovers_the_fixed_bill_level(factory) -> None:
    """At floor_share = 1 the bill can never fall, so an elasticity above the
    boundary must give the same steady state as no elasticity at all."""
    base = variant(factory(), rounds=800, seed=7)
    floored = run(with_wages(base, 1.5, 1.0)).tail_mean("layer2_spending", 25)
    fixed = run(with_wages(base, 0.0)).tail_mean("layer2_spending", 25)
    assert floored == pytest.approx(fixed, rel=1e-9)


# -- calibration -------------------------------------------------------------


def test_dfa_shares_sum_to_one_and_match_the_release() -> None:
    """Guards against a typo in a transcribed published figure."""
    assert sum(DFA_NET_WORTH_SHARES) == pytest.approx(1.0, abs=1e-12)
    assert sum(DFA_COUNTS) == 100
    # Q1 2026 release, share of total net worth.
    assert DFA_NET_WORTH_SHARES == (0.025, 0.296, 0.363, 0.316)


def test_dfa_preset_has_strictly_ordered_retention() -> None:
    """The measured distribution gives a strict ordering where the toy figures
    only gave a weak one."""
    sigma = dfa_calibrated().spend.retention_rate
    assert sigma[3] > sigma[2] > sigma[1] > sigma[0]


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_death_zone_condition_holds_under_both_presets(factory) -> None:
    assert factory().flow_balance() > 1.0


def test_every_preset_declares_its_sources() -> None:
    for preset in presets():
        assert preset.sources
        assert all(s.strip() for s in preset.sources)


# -- the headline findings survive the real distribution ----------------------


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_spending_sweep_is_flat_under_both_presets(factory) -> None:
    base = variant(factory(), rounds=300, seed=7)
    levels = [
        run(variant(base, spend=base.spend.with_top_propensity(p))).tail_mean(
            "active_claims", 50
        )
        for p in (0.05, 0.1, 0.25, 0.5, 0.75, 1.0)
    ]
    spread = max(levels) - min(levels)
    assert spread < 1e-9 * max(1.0, float(np.mean(levels))), levels


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_opening_an_edge_still_moves_inflow_under_both_presets(factory) -> None:
    base = variant(factory(), rounds=300, seed=7)
    closed = run(base).tail_mean("active_claims", 50)
    opened = run(
        variant(base, adjacency=base.adjacency.with_downward_edge(0.05))
    ).tail_mean("active_claims", 50)
    assert opened > 1.5 * closed


@pytest.mark.parametrize("factory", ALL_PRESETS)
def test_issuance_accumulates_upward_under_both_presets(factory) -> None:
    base = variant(factory(), rounds=400, seed=7)
    h = run(base)
    assert h.tail_mean("layer1_share", 50) > 0.9
