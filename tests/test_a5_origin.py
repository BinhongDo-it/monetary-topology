"""Stage A5's origin: three named points, and the count that has to hold still.

`docs/a5_reachability.md` section 8.2 recorded that A5-4's crossing round is
counted from an origin two steps removed from the parameter that was set, and
left the repair undone. Section 8.3 is the repair. These tests are what make it
a repair rather than a rewrite.

**The configuration must have one call site.** `run` and `build` need the same
`A3Config`, and `PROJECT_PLAN.md` section 11.12 is the case where a parameter
reached one of two call sites: the default path was the correct one, so the
guard on the default path never fired and only a sweep took the wrong branch.
`_config` exists so that the two cannot drift, and `test_build_then_run_matches_run`
is what says so.

**The series must not move.** `rho_series` is the quantity every stored A5
number was produced from. The trajectory prepends one element to it and changes
nothing else, so the tail has to be bitwise equal. A repair that also moved the
series would be a new instrument wearing a repair's name, and A5-4's pass would
no longer be the pass that was recorded.

**The shift must be exactly one.** If `rho_opening` is itself below one, then
prepending it can only push the first crossing one index later. Anything else
means the prepended value is not what it claims to be. This is the identity the
detail line leans on when it prints both counts, and it is asserted here rather
than in the detail's prose.

**The two paths to gamma must agree.** `price_for` reads the median terms off a
bare stage A2 network and `rho_series` reads them off the model's own matrix.
Section 8.3 records that they agree bitwise because `hold_mean_cost` is off by
default. That is a fact about the current defaults, not a theorem, so it is
tested: if a later change turns `hold_mean_cost` on by default, the origin
problem becomes three steps rather than two and this test is where that surfaces.

**And the opening state must be unreadable after the run.** `rho_opening` reads
`model.price` and `model.holdings`, which hold the final state once the model
has run. Returning a number there would be an end value wearing an origin's
name, which is the exact failure section 8.2 records.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from a5_reachability import (  # noqa: E402
    A5_4_START,
    RHO_GRID,
    ROUNDS,
    baseline,
    build,
    crossing,
    price_for,
    rho_opening,
    rho_series,
    run,
    trajectory,
)

from monetary_topology.asset import AssetSpec  # noqa: E402

#: Three is enough for every claim here: each is an identity that holds seed by
#: seed rather than on an average over seeds.
SEEDS = (0, 1, 2)


def test_build_then_run_matches_run() -> None:
    """One configuration, two entry points, and no room between them."""
    for seed in SEEDS:
        built = build(seed, A5_4_START)
        built.run()
        direct = run(seed, A5_4_START)
        assert np.array_equal(
            np.asarray(built.price_history), np.asarray(direct.price_history)
        )
        assert np.array_equal(
            np.asarray(built.claims_history), np.asarray(direct.claims_history)
        )
        assert np.array_equal(built.units, direct.units)


def test_trajectory_tail_is_rho_series_bitwise() -> None:
    """The stored series is the same object, one index later."""
    for seed in SEEDS:
        model, traj = trajectory(seed, A5_4_START)
        assert np.array_equal(traj[1:], rho_series(model))
        assert traj.size == ROUNDS + 1


def test_trajectory_origin_is_the_opening_state() -> None:
    for seed in SEEDS:
        _, traj = trajectory(seed, A5_4_START)
        assert float(traj[0]) == rho_opening(build(seed, A5_4_START))


def test_the_configured_value_is_never_the_opening_value() -> None:
    """Section 8.2's finding, as a standing property rather than a trace.

    The opening allocation splits the proceeds across every node while the
    production layer is mostly non-buyers, so its median claims rise and
    reachability improves before the economy has done anything. If this ever
    stops being true the origin has one step rather than two and section 8.3's
    table is wrong.
    """
    for seed in SEEDS:
        assert rho_opening(build(seed, A5_4_START)) < A5_4_START


def test_crossing_shifts_by_exactly_one() -> None:
    """Prepending a value below one moves the first crossing one index later."""
    for seed in SEEDS:
        _, traj = trajectory(seed, A5_4_START)
        assert traj[0] < 1.0
        from_opening, _ = crossing(traj)
        from_series, _ = crossing(traj[1:])
        assert from_opening is not None and from_series is not None
        assert from_opening == from_series + 1


def test_crossing_reads_an_index_and_nothing_else() -> None:
    """The function is pure; the origin lives entirely in what is passed to it."""
    assert crossing(np.array([0.2, 0.4, 1.0, 2.0])) == (2, 0.0)
    assert crossing(np.array([1.0, 0.5, 2.0])) == (0, pytest.approx(1 / 3))
    assert crossing(np.array([0.1, 0.2])) == (None, 0.0)


def test_gamma_agrees_on_both_paths() -> None:
    """Bitwise, so the three named points are on one scale."""
    for seed in SEEDS:
        terms, _, production = baseline(seed)
        model = build(seed, A5_4_START)
        assert float(np.median(terms[production, 0])) == float(
            np.median(model.terms[production, 0])
        )


def test_price_for_hits_the_target_at_every_swept_point() -> None:
    """`rho_configured` is what it says it is, across the registered grid."""
    for seed in SEEDS:
        for target in RHO_GRID:
            terms, median_claims, production = baseline(seed)
            spec = AssetSpec()
            prices = price_for(target, seed, spec)
            gamma = float(np.median(terms[production, 0]))
            got = gamma * prices[0] / median_claims / spec.stretch
            assert got == pytest.approx(target, rel=1e-12)


def test_price_for_keeps_the_tier_ratio() -> None:
    """Only the scale moves, so the tiers stay three different things."""
    base = AssetSpec().initial_price
    for seed in SEEDS:
        prices = price_for(2.0, seed, AssetSpec())
        for p, b in zip(prices[1:], base[1:], strict=True):
            assert p / prices[0] == pytest.approx(b / base[0], rel=1e-12)


def test_rho_opening_refuses_a_model_that_has_run() -> None:
    model = run(0, A5_4_START)
    with pytest.raises(ValueError, match="already run"):
        rho_opening(model)


def test_max_units_defaults_reproduce_bitwise() -> None:
    """`_config`'s cap parameter is a strict generalisation, asserted not argued.

    `None` and the registered value have to give the same object, or the
    diagnostic in section 8.5 would have moved the criteria it was written to
    diagnose. `AssetSpec()`'s own default is the reference, so this test does
    not carry a number of its own.
    """
    registered = AssetSpec().max_units
    for seed in SEEDS:
        a = build(seed, A5_4_START)
        b = build(seed, A5_4_START, max_units=registered)
        assert a.a3.asset.max_units == registered
        assert np.array_equal(a.units, b.units)
        assert np.array_equal(a.holdings, b.holdings)
        a.run()
        b.run()
        assert np.array_equal(
            np.asarray(a.price_history), np.asarray(b.price_history)
        )


def test_a_cap_reaches_code() -> None:
    """The other arm must not be inert, the lesson `centrality_bins` taught.

    A field that reaches no code passes every reproduction test perfectly, so
    the probe's contrast arms are worth nothing unless at least one of them
    changes the opening allocation. One node holding more than one unit under
    the registered cap is what makes a cap of one bite.
    """
    moved = False
    for seed in SEEDS:
        capped = build(seed, A5_4_START, max_units=1)
        assert capped.units.sum(axis=1).max() <= 1
        if not np.array_equal(capped.units, build(seed, A5_4_START).units):
            moved = True
    assert moved
