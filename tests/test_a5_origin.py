"""Stage A5's origin: three named points, and the count that has to hold still.

`docs/a5_reachability.md` section 8.2 recorded that A5-4's crossing round is
counted from an origin two steps removed from the parameter that was set, and
left the repair undone. Section 8.3 is the repair. These tests are what make it
a repair rather than a rewrite.

**The configuration must have one call site.** `run` and `build` need the same
`A3Config`, and this repository has already paid for the case where a parameter
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

**Who enters and who stays are two readings** (section 8.10). Entry is the
opening allocation; who is still holding is the unit matrix at the end, and it
is read by `holdings_now` on the same model. The cap moves the second as well as
the first, the region closes with or without it, and the tests at the end of
this file hold each of those in place, together with the two sentences in the
criteria that are now computed where they were once fixed strings.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from a5_reachability import (  # noqa: E402
    A5_3_BENIGN,
    A5_3_HOSTILE,
    A5_4_MEDIAN_CROSSING,
    A5_4_RETURN_SHARE,
    A5_4_START,
    OPENING_FINE_GRID,
    RHO_GRID,
    ROUNDS,
    A5_6_DRIFT,
    _config,
    a5_3,
    a5_6,
    baseline,
    build,
    crossing,
    entrants_still_holding,
    entry_participation,
    holdings_now,
    opening_reading,
    opening_table,
    price_for,
    production_share,
    rho_opening,
    rho_series,
    run,
    seed_means,
    trajectory,
)

from monetary_topology.asset import A3Model, AssetSpec  # noqa: E402

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


def test_trajectory_passes_the_cap_through() -> None:
    """A capped history gets the same origin handling as an uncapped one."""
    for seed in SEEDS:
        model, traj = trajectory(seed, A5_4_START, max_units=1)
        direct = run(seed, A5_4_START, max_units=1)
        assert np.array_equal(model.units, direct.units)
        assert model.units.sum(axis=1).max() <= 1
        assert float(traj[0]) == rho_opening(build(seed, A5_4_START, max_units=1))
        assert np.array_equal(traj[1:], rho_series(model))


def test_holdings_now_reads_the_unit_matrix() -> None:
    """Two planted states, each of which has to move the reading it names."""
    model = build(0, A5_4_START)
    layer1 = model.a3.network.spec.layer1_size
    before = holdings_now(model)
    assert before["holding_share"] == entry_participation(0, A5_4_START)
    # The opening walk hands out one unit per holding, so resale's one draw
    # per holding is one draw per unit there and nowhere else.
    assert before["cells_per_unit"] == 1.0 and before["largest_holding"] == 1.0

    # Two more units in a holding that already has one. The units held rise
    # and the number of holdings does not, so fewer are offered per unit held.
    node, tier = np.argwhere(model.units > 0)[0]
    assert node < layer1
    model.units[node, tier] += 2.0
    piled = holdings_now(model)
    assert piled["largest_holding"] == 3.0
    assert piled["cells_per_unit"] < 1.0
    assert piled["unowned"] == before["unowned"] - 2.0
    assert piled["holding_share"] == before["holding_share"]

    # The production layer emptied. Nobody in it holds; the other layer's
    # units are untouched.
    model.units[layer1:, :] = 0.0
    emptied = holdings_now(model)
    assert emptied["holding_share"] == 0.0
    assert emptied["production_units"] == 0.0
    assert emptied["financial_units"] == piled["financial_units"]


def test_seed_means_pools_the_ratio_and_keeps_the_extremes() -> None:
    rows = [
        {
            "holding_share": 0.5,
            "production_holders": 2.0,
            "production_units": 5.0,
            "financial_units": 1.0,
            "unowned": 0.0,
            "largest_holding": 4.0,
            "cells_per_unit": 0.5,
        },
        {
            "holding_share": 0.0,
            "production_holders": 0.0,
            "production_units": 0.0,
            "financial_units": 3.0,
            "unowned": 2.0,
            "largest_holding": 1.0,
            "cells_per_unit": 1.0,
        },
    ]
    out = seed_means(rows)
    # Pooled: five units over two holders. The second seed has no holder and
    # so no ratio, and a mean of ratios would have had to invent one for it.
    assert out["units_per_production_holder"] == 2.5
    assert out["seeds"] == 2.0 and out["seeds_with_unowned"] == 1.0
    assert out["largest_holding"] == 4.0 and out["cells_per_unit_min"] == 0.5
    assert out["cells_per_unit"] == 0.75 and out["financial_units"] == 2.0
    assert seed_means([rows[1]])["units_per_production_holder"] is None


def test_the_cap_keeps_the_entrants_holding() -> None:
    """Who stays is read off the unit matrix, and the cap moves it.

    With no cap the production layer's entrants are sold out by the end of the
    run. With one unit per agent they are still holding. The reachable region
    closes in both, on the same round, which is why A5-4 and A5-7 cannot stand
    in for who stays: they read the buyer's claims against the price.
    """
    for seed in SEEDS:
        free, free_traj = trajectory(seed, A5_4_START)
        capped, capped_traj = trajectory(seed, A5_4_START, max_units=1)
        opened = holdings_now(build(seed, A5_4_START, max_units=1))
        assert holdings_now(free)["holding_share"] == 0.0
        assert holdings_now(capped)["holding_share"] == opened["holding_share"]
        assert opened["holding_share"] > 0.0
        crossed = [crossing(traj) for traj in (free_traj, capped_traj)]
        assert crossed[0] == crossed[1]
        assert crossed[0][0] is not None and crossed[0][1] == 0.0
        # The entrants themselves, and not only their number.
        assert entrants_still_holding([build(seed, A5_4_START).units], [free]) == 0.0
        kept = entrants_still_holding(
            [build(seed, A5_4_START, max_units=1).units], [capped]
        )
        assert kept is not None and kept > 0.9


def test_entrants_still_holding_follows_the_nodes_and_not_the_count() -> None:
    """A unit passed from one production node to another: same share, one
    entrant fewer."""
    model = build(0, A5_4_START, max_units=1)
    layer1 = model.a3.network.spec.layer1_size
    opened = model.units.copy()
    assert entrants_still_holding([opened], [model]) == 1.0
    holders = np.flatnonzero(model.units[layer1:].sum(axis=1) > 0) + layer1
    empty = np.flatnonzero(model.units[layer1:].sum(axis=1) == 0) + layer1
    tier = int(np.flatnonzero(model.units[holders[0]] > 0)[0])
    model.units[holders[0], tier] -= 1.0
    model.units[empty[0], tier] += 1.0
    assert holdings_now(model)["holding_share"] == entry_participation(
        0, A5_4_START, 1
    )
    assert entrants_still_holding([opened], [model]) == 1.0 - 1.0 / holders.size
    # Nobody got in: there is no share to give.
    opened[layer1:, :] = 0.0
    assert entrants_still_holding([opened], [model]) is None


def test_opening_reading_is_computed_and_not_carried() -> None:
    """The sentence moves when the allocation behind it moves."""
    both = tuple(sorted(set(RHO_GRID) | set(OPENING_FINE_GRID)))
    table = opening_table(range(2), both)
    for rho in RHO_GRID:
        assert table[rho]["holding_share"] == float(
            np.mean([entry_participation(seed, rho) for seed in range(2)])
        )
    text = opening_reading(table)
    planted = {rho: dict(row) for rho, row in table.items()}
    planted[min(RHO_GRID)]["units_per_production_holder"] = 9.999
    assert "9.999" in opening_reading(planted) and "9.999" not in text
    # No point at which every unit sells: the two-regime sentence is refused
    # instead of being printed about an allocation it does not describe.
    for row in planted.values():
        row["seeds_with_unowned"] = 1.0
    with pytest.raises(ValueError, match="two regimes"):
        opening_reading(planted)


def test_opening_reading_finds_where_cheapening_raises_entry() -> None:
    """The point from which entry falls at every step is read off the table."""
    both = tuple(sorted(set(RHO_GRID) | set(OPENING_FINE_GRID)))
    table = opening_table(range(2), both)
    planted = {rho: dict(row) for rho, row in table.items()}
    order = sorted(planted)
    planted[4.0]["holding_share"] = planted[order[order.index(4.0) - 1]][
        "holding_share"
    ] + 0.1
    assert "From rho=4 up, entry falls at every step" in opening_reading(planted)
    assert "From rho=4 up" not in opening_reading(table)


def test_a5_3_is_void_only_where_a5_4_holds() -> None:
    grid = {
        A5_3_BENIGN: {"share_start": 0.2, "share_end": 0.3},
        A5_3_HOSTILE: {"share_start": 0.3, "share_end": 0.1},
    }
    held = a5_3(grid, True)
    assert held.void and not held.passed
    live = a5_3(grid, False)
    assert not live.void and live.passed
    grid[A5_3_BENIGN]["share_end"] = 0.1
    assert not a5_3(grid, False).passed


def test_a5_3_and_a5_4_are_not_complements() -> None:
    """The configuration A5-3's detail cites, reproduced.

    With the wage bill at four times its registered value, on seed 0, the
    production layer's share of net worth falls at both ends of the grid, which
    fails A5-3's benign half, and the configured ``rho = 0.5`` reaches one late
    and is mostly back below it afterwards, which fails both of A5-4's
    thresholds. Both fail, so neither is the negation of the other.
    """

    def widened(rho: float):
        config = _config(0, rho)
        wages = replace(config.network.wages, bill=4.0 * config.network.wages.bill)
        model = A3Model(replace(config, network=replace(config.network, wages=wages)))
        opening = rho_opening(model)
        model.run()
        return model, np.concatenate(([opening], rho_series(model)))

    for rho in (A5_3_BENIGN, A5_3_HOSTILE):
        share = production_share(widened(rho)[0])
        assert share[-1] < share[0]
    first, back = crossing(widened(A5_4_START)[1])
    assert first is None or first >= A5_4_MEDIAN_CROSSING
    assert back >= A5_4_RETURN_SHARE

def test_a5_6_is_void_only_where_a5_7_holds() -> None:
    held = a5_6(range(1), True)
    assert held.void and not held.passed
    live = a5_6(range(1), False)
    assert not live.void
    assert "A5-7 does not hold on this run" in live.detail


def test_a5_6_and_a5_7_are_not_complements() -> None:
    """With the wage bill at four times its value, both fail on the frozen arm.

    The frozen series drifts by far more than A5-6's threshold and never
    reaches one, which fails A5-7. Neither is the negation of the other.
    """
    config = _config(0, A5_4_START, eta=0.0)
    wages = replace(config.network.wages, bill=4.0 * config.network.wages.bill)
    model = A3Model(replace(config, network=replace(config.network, wages=wages)))
    opening = rho_opening(model)
    model.run()
    series = rho_series(model)
    assert float(np.abs(series / series[0] - 1.0).max()) > A5_6_DRIFT
    first, _ = crossing(np.concatenate(([opening], series)))
    assert first is None or first >= A5_4_MEDIAN_CROSSING
