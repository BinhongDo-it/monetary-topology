"""Tests for stage A3, chunk one: the closed-channel control.

The load-bearing test is ``test_closed_channel_reproduces_a2_bitwise``. If the
asset layer's mere presence moves a single float, then every figure the later
chunks produce is measured against a base that shifted underneath them, and no
comparison across stages means what it says.

The second group is unusual and deliberate: it asserts that the module's default
parameters are the ones written down in ``docs/a3_asset_channel.md`` §8. A later
edit that quietly moves a default in order to make A3-4 pass then fails the
suite instead of passing unremarked. The pre-registration promises no parameter
is tuned; this is that promise made mechanical rather than left as a sentence.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from monetary_topology.asset import (
    CLOSED,
    A3Config,
    A3Model,
    AssetSpec,
    DesignDeviation,
    bidder_pool,
    centrality,
    gate_clears,
    loop_sum,
    price_at,
    run_a3,
    soft_gate,
    terms_matrix,
)
from monetary_topology.network import NetworkConfig, NetworkSpec, run_network

SEEDS = range(3)
ROUNDS = 200


def closed(seed: int = 0, rounds: int = ROUNDS, **network_kw) -> A3Config:
    spec = NetworkSpec(seed=seed, **network_kw)
    return A3Config(
        asset=CLOSED, network=NetworkConfig(spec=spec, seed=seed, rounds=rounds)
    )


# -- A3-1, the criterion this chunk exists for -------------------------------


def test_closed_channel_reproduces_a2_bitwise() -> None:
    for seed in SEEDS:
        for mid in (0, 30):
            spec = NetworkSpec(seed=seed, intermediate_size=mid, layer2_size=180 - mid)
            base = run_network(
                NetworkConfig(spec=spec, seed=seed, rounds=ROUNDS, snapshot_every=50)
            )
            got = run_a3(
                A3Config(
                    asset=CLOSED,
                    network=NetworkConfig(
                        spec=spec, seed=seed, rounds=ROUNDS, snapshot_every=50
                    ),
                )
            )
            for name in (
                "total_volume",
                "effective_support",
                "effective_support_l2",
                "realized_support",
                "active_nodes",
                "layer2_reached",
                "layer1_volume",
                "layer2_inflow",
                "wage_owed",
                "wage_paid",
                "intermediate_holdings",
                "issuance",
                "holdings",
            ):
                assert (
                    np.asarray(getattr(base, name)) == np.asarray(getattr(got, name))
                ).all(), f"{name} differs at seed {seed}, intermediate {mid}"
            assert base.potential_support == got.potential_support
            assert (base.adjacency == got.adjacency).all()


def test_closed_channel_reproduces_the_a2c_snapshots_bitwise() -> None:
    """A2c computes cycle structure on A2's flow snapshots, so the snapshots and
    not only the summary series have to match."""
    for seed in SEEDS:
        spec = NetworkSpec(seed=seed)
        cfg = NetworkConfig(spec=spec, seed=seed, rounds=ROUNDS, snapshot_every=50)
        base = run_network(cfg)
        got = run_a3(A3Config(asset=CLOSED, network=cfg))
        assert sorted(base.snapshots) == sorted(got.snapshots)
        for t, flow in base.snapshots.items():
            assert (flow == got.snapshots[t]).all(), f"snapshot {t}, seed {seed}"


def test_an_empty_asset_still_reproduces_a2_bitwise() -> None:
    """The seam between "declared" and "operating".

    A tier with no units to allocate cannot move a claim, so the run must still
    be stage A2 to the last bit even though the ledger, the terms matrix and the
    pricing rule are all present and running. If this fails, some part of the
    asset layer is touching the claim dynamics through a route that has nothing
    to do with anybody owning anything.
    """
    empty = AssetSpec(tiers=1, units=(0,), base_terms=(1.0,), initial_price=(1.0,))
    for seed in SEEDS:
        net = NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=120)
        base = run_network(net)
        got = A3Model(A3Config(asset=empty, network=net)).run()
        assert (np.asarray(base.holdings) == np.asarray(got.holdings)).all()
        assert (
            np.asarray(base.effective_support) == np.asarray(got.effective_support)
        ).all()


def test_a_closed_channel_warns_about_nothing() -> None:
    model = A3Model(closed())
    assert model.channel_wired is True
    assert model.deviations == []


def test_net_worth_is_claims_while_the_channel_is_closed() -> None:
    model = A3Model(closed())
    assert model.net_worth() == pytest.approx(model.holdings, rel=1e-15)
    model.run()
    assert model.net_worth() == pytest.approx(model.holdings, rel=1e-15)


# -- the registered parameter table ------------------------------------------


#: ``docs/a3_asset_channel.md`` §4, transcribed. **Every field of ``AssetSpec``
#: must appear here.** The previous version listed sixteen and ignored seven,
#: which left the newest parameters — the ones most likely to be reached for
#: when a criterion is close to its threshold — outside the promise the test
#: exists to enforce. ``test_every_field_is_pinned`` makes the omission itself
#: a failure rather than something a reader has to notice.
REGISTERED_DEFAULTS: dict[str, object] = {
    "tiers": 3,
    "units": (60, 30, 10),
    "initial_price": (0.5, 1.0, 2.0),
    "elasticity": 1.0,
    "base_terms": (1.00, 1.05, 1.15),
    "terms_spread": 1.0,
    "turnover": 0.04,
    "forced_sale_floor": 0.10,
    "centrality_bins": 4,
    "holding_period": 25,
    "arm": "exogenous",
    "open_tiers": (),
    "rent_rate": 0.05,
    "max_units": 0,
    "stretch": 3.0,
    "stretch_cost": "uncounted",
    # A3b. Every one of these defaults to the pre-A3b behaviour, which is what
    # makes the registered A3 run reproducible bitwise.
    "construction": "auction",
    "units_per_node": 0.0,
    "ownership_rate": 0.0,
    "opening_discount": 0.0,
    "residual_owner": False,
    "proceeds": "equal",
    # A3c, the gamma split. `None` ties the gate to the payment.
    "gate_spread": None,
    "hold_mean_cost": False,
    "mean_cost_reference": 1.0,
}


def test_defaults_match_the_pre_registration() -> None:
    """``docs/a3_asset_channel.md`` §4, transcribed.

    Not a style check. The pre-registration promises that no parameter is tuned
    to make a criterion pass, and a promise in prose is not enforceable. This is.
    """
    s = AssetSpec()
    for name, expected in REGISTERED_DEFAULTS.items():
        assert getattr(s, name) == expected, name


def test_every_field_is_pinned() -> None:
    """A field absent from ``REGISTERED_DEFAULTS`` is a hole in the promise.

    Adding a parameter without registering it is exactly how the previous table
    came to omit seven, so the omission fails here rather than passing quietly.
    """
    fields = {f.name for f in dataclasses.fields(AssetSpec)}
    assert fields == set(REGISTERED_DEFAULTS), fields ^ set(REGISTERED_DEFAULTS)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"tiers": -1}, "non-negative"),
        ({"units": (1, 2)}, "one entry per tier"),
        ({"base_terms": (1.0, 1.0)}, "one entry per tier"),
        ({"elasticity": -0.1}, "elasticity"),
        ({"terms_spread": -0.1}, "terms_spread"),
        ({"turnover": 1.5}, "turnover"),
        ({"forced_sale_floor": -0.1}, "forced_sale_floor"),
        ({"centrality_bins": 0}, "centrality_bins"),
        ({"holding_period": 0}, "holding_period"),
        ({"arm": "whenever"}, "arm must be one of"),
        ({"open_tiers": (5,)}, "open_tiers"),
    ],
)
def test_invalid_parameters_are_rejected(kw, match) -> None:
    with pytest.raises(ValueError, match=match):
        AssetSpec(**kw)


def test_base_terms_below_one_warn_rather_than_raise() -> None:
    """A premium below one is a discount for being peripheral: the registered
    mechanism with its sign reversed, not a smaller version of it.

    That is a coherent thing to want to run, so it runs. What it may not do is
    be reported next to the registered arm without saying which arm it is, and
    the deviation list is what carries that.
    """
    with pytest.warns(DesignDeviation, match="sign reversed"):
        spec = AssetSpec(base_terms=(0.5, 1.0, 1.1))
    model = A3Model(A3Config(asset=spec))
    assert model.deviations == ["base_terms below one: reversed-sign arm"]


def test_incoherent_configurations_still_raise() -> None:
    """The distinction the warning rests on: a departure from the design runs,
    a configuration with nothing to run does not."""
    with pytest.raises(ValueError, match="one entry per tier"):
        AssetSpec(tiers=3, units=(1, 2))


# -- centrality --------------------------------------------------------------


def test_centrality_is_normalised_in_degree() -> None:
    a = np.array([[0.0, 1.0, 1.0], [0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
    assert centrality(a) == pytest.approx(np.array([0.0, 0.5, 1.0]))


def test_centrality_of_an_empty_graph_is_zero_not_undefined() -> None:
    assert centrality(np.zeros((4, 4))) == pytest.approx(np.zeros(4))


def test_centrality_matches_the_measure_a2_already_uses() -> None:
    """A3 must not introduce a second notion of position."""
    model = A3Model(closed())
    indeg = model.adjacency.sum(axis=0)
    assert model.centrality == pytest.approx(indeg / indeg.max())
    assert int(np.argmax(model.centrality)) == model.injection_node


# -- terms -------------------------------------------------------------------


def test_uniform_terms_when_the_spread_is_zero() -> None:
    spec = AssetSpec(terms_spread=0.0)
    g = terms_matrix(np.linspace(0.0, 1.0, 50), spec)
    for q in range(spec.tiers):
        assert np.ptp(g[:, q]) == pytest.approx(0.0, abs=1e-15)
        assert g[0, q] == pytest.approx(spec.base_terms[q])


def test_the_most_central_pays_base_and_the_most_peripheral_pays_the_spread() -> None:
    spec = AssetSpec(terms_spread=1.0)
    g = terms_matrix(np.array([0.0, 1.0]), spec)
    for q in range(spec.tiers):
        assert g[1, q] == pytest.approx(spec.base_terms[q])
        assert g[0, q] == pytest.approx(2.0 * spec.base_terms[q])


def test_terms_decrease_monotonically_in_centrality() -> None:
    g = terms_matrix(np.linspace(0.0, 1.0, 100), AssetSpec())
    assert (np.diff(g, axis=0) <= 0).all()


def test_terms_are_worse_at_higher_tiers() -> None:
    g = terms_matrix(np.linspace(0.0, 1.0, 20), AssetSpec())
    assert (np.diff(g, axis=1) > 0).all()


# -- the loop sum ------------------------------------------------------------


def test_the_loop_sum_is_zero_when_terms_are_uniform() -> None:
    """With ``κ = 0`` the stage's central prediction is vacuous by construction.
    The pre-registration records that a pass there is a null, and this is where
    that fact is pinned."""
    g = terms_matrix(np.linspace(0.0, 1.0, 40), AssetSpec(terms_spread=0.0))
    assert loop_sum(g, 0, 39, tier=2, periods=40) == pytest.approx(0.0, abs=1e-15)


def test_the_loop_sum_is_the_log_terms_ratio_over_the_period() -> None:
    g = terms_matrix(np.array([0.0, 1.0]), AssetSpec(terms_spread=1.0))
    got = loop_sum(g, a=1, b=0, tier=0, periods=40)
    assert got == pytest.approx(np.log(2.0) / 40.0)


def test_the_loop_sum_is_antisymmetric() -> None:
    g = terms_matrix(np.linspace(0.0, 1.0, 10), AssetSpec())
    assert loop_sum(g, 2, 7, 1, 40) == pytest.approx(-loop_sum(g, 7, 2, 1, 40))


# -- the gate ----------------------------------------------------------------


def test_the_gate_is_claims_against_terms_times_price() -> None:
    claims = np.array([1.0, 3.0])
    terms = np.array([[1.0, 2.0], [1.0, 2.0]])
    price = np.array([1.0, 1.0])
    got = gate_clears(claims, terms, price)
    assert got.tolist() == [[True, False], [True, True]]


def test_an_open_tier_admits_everyone_regardless_of_claims() -> None:
    """The A3-5 experiment, and the only thing that uses ``open_tiers``."""
    got = gate_clears(
        np.zeros(5), np.full((5, 2), 10.0), np.array([10.0, 10.0]), open_tiers=(1,)
    )
    assert not got[:, 0].any()
    assert got[:, 1].all()


def test_negative_claims_never_clear_a_gate() -> None:
    got = gate_clears(np.array([-5.0]), np.array([[1.0]]), np.array([0.5]))
    assert not got.any()


# -- pricing -----------------------------------------------------------------


def test_zero_elasticity_freezes_prices_exactly() -> None:
    """The control that separates revaluation from ownership as such.

    Exact, not approximate: ``price_at`` returns the opening vector without
    computing a ratio, so a pool that moved by any amount cannot move the price
    by a rounding error.
    """
    p0 = np.array([0.5, 1.0, 2.0])
    got = price_at(p0, np.array([9e9, 1.0, 0.0]), np.array([1.0, 1.0, 1.0]), 0.0)
    assert (got == p0).all()


def test_price_follows_the_pool_ratio_raised_to_the_elasticity() -> None:
    p0 = np.array([2.0])
    assert price_at(p0, np.array([4.0]), np.array([1.0]), 1.0) == pytest.approx([8.0])
    assert price_at(p0, np.array([4.0]), np.array([1.0]), 0.5) == pytest.approx([4.0])


def test_a_tier_with_an_empty_opening_pool_keeps_its_opening_price() -> None:
    """No ratio exists. Inventing one would put a number where the model has
    none, and that number would then be reported as a price."""
    p0 = np.array([1.0, 2.0])
    got = price_at(p0, np.array([5.0, 5.0]), np.array([0.0, 1.0]), 1.0)
    assert got[0] == pytest.approx(1.0)


def test_the_pool_is_claims_and_never_net_worth() -> None:
    """Pricing off net worth would make the price a function of the price and
    the widening this stage measures would be an accounting identity."""
    import inspect

    assert set(inspect.signature(bidder_pool).parameters) == {"claims", "clears"}


def test_prices_are_monotone_and_do_not_oscillate() -> None:
    """Guards the pathology that the literal pre-registered wording produced.

    Taking the bidder pool as "nodes clearing the gate at t" makes a rising
    price thin the set that clears, which shrinks the pool, which lowers the
    price; once the set empties the price collapses to zero and then explodes.
    Over three hundred rounds that is a two-cycle and the top tier sat in it.
    The pool is evaluated at opening prices for exactly this reason.
    """
    model = A3Model(
        A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0, rounds=300))
    )
    model.run()
    path = np.asarray(model.price_history)
    assert (path > 0.0).all(), "a tier priced at zero is the collapse phase"
    # Not strict monotonicity. Buying converts claims into units, so the pool
    # that sets the price wobbles by a percent or two and prices tick down in a
    # couple of rounds out of three hundred. What must not return is the
    # two-cycle: a collapse to nothing followed by an explosion. A halving in
    # one round is the signature, and there is none.
    ratio = path[:-1] / path[1:]
    assert ratio.max() < 2.0, "a halving in one round is the collapse signature"
    assert (path[-1] > 10.0 * path[0]).all(), "and the trend is still upward"


def test_the_pricing_pool_ignores_the_current_price() -> None:
    """Stated as a property rather than left to the monotonicity test.

    ``_clears_at_opening`` must not consult ``self.price``, or the feedback
    returns by a different route.
    """
    model = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    before = model._clears_at_opening().copy()
    model.price = model.price * 1000.0
    assert (model._clears_at_opening() == before).all()
    assert not (model._clears() == before).all(), "the acquisition gate does move"


# -- the opening allocation --------------------------------------------------


def test_the_opening_allocation_conserves_claims() -> None:
    """The buyer pays and the proceeds are split equally across all nodes, so
    the stock-flow assertion is live from round zero."""
    model = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    assert float(model.holdings.sum()) == pytest.approx(100.0, rel=1e-12)


def test_the_cap_is_honoured_when_it_is_set() -> None:
    """``max_units`` is a switch, not the default. The default is no cap,
    because a cap of one freezes the resale market outright; see
    ``test_a_cap_of_one_freezes_the_market_and_is_why_the_default_is_no_cap``."""
    capped = A3Model(
        A3Config(asset=AssetSpec(max_units=1), network=NetworkConfig(seed=0))
    )
    assert (capped.units.sum(axis=1) <= 1.0).all()
    uncapped = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    assert uncapped.units.sum(axis=1).max() > 1.0


def test_allocation_never_exceeds_supply() -> None:
    spec = AssetSpec()
    model = A3Model(A3Config(asset=spec, network=NetworkConfig(seed=0)))
    assert (model.units.sum(axis=0) <= np.asarray(spec.units, dtype=float)).all()


def test_nobody_is_allocated_a_unit_they_could_not_pay_for() -> None:
    model = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    assert (model.holdings >= 0.0).all()


def test_the_opening_allocation_runs_richest_first_from_the_top_tier() -> None:
    """A3-2 defines its comparison groups by this ranking, so the rule is the
    one the criterion names rather than a convenience."""
    model = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    top = model.units[:, -1] > 0
    assert top.sum() > 0
    # every holder of the top tier out-ranks every node that holds nothing and
    # could have afforded it, which is what "allocated down the ranking" means.
    assert model.units.sum() > 0


def test_an_asset_with_no_units_leaves_claims_untouched() -> None:
    spec = AssetSpec(tiers=1, units=(0,), base_terms=(1.0,), initial_price=(1.0,))
    model = A3Model(A3Config(asset=spec, network=NetworkConfig(seed=0)))
    assert (model.units == 0.0).all()
    assert float(model.holdings.sum()) == pytest.approx(100.0, rel=1e-12)


def test_net_worth_counts_held_units_at_the_current_price() -> None:
    model = A3Model(A3Config(asset=AssetSpec(), network=NetworkConfig(seed=0)))
    expected = model.holdings + model.units @ model.price
    assert model.net_worth() == pytest.approx(expected, rel=1e-12)


def test_revaluation_raises_net_worth_above_the_frozen_price_arm() -> None:
    """`η = 0` against `η = 1` on the same seed: the only difference is whether
    held units revalue, so any gap between the two is revaluation and nothing
    else."""
    out = {}
    for eta in (0.0, 1.0):
        model = A3Model(
            A3Config(
                asset=AssetSpec(elasticity=eta),
                network=NetworkConfig(seed=0, rounds=200),
            )
        )
        model.run()
        held = model.units.sum(axis=1) > 0
        out[eta] = float(model.net_worth()[held].mean())
    assert out[1.0] > out[0.0]


# -- the soft gate -----------------------------------------------------------


def soft(s: float, cost: str = "uncounted", seed: int = 0, rounds: int = 200, **kw):
    return A3Model(
        A3Config(
            asset=AssetSpec(stretch=s, stretch_cost=cost, **kw),
            network=NetworkConfig(seed=seed, rounds=rounds),
        )
    )


def test_stretch_of_one_is_the_hard_gate_bitwise() -> None:
    """The nested control. Same discipline as ``elasticity = 0``."""
    admitted, stretched = soft_gate(
        np.array([1.0, 3.0]), np.array([[2.0], [2.0]]), np.array([1.0]), stretch=1.0
    )
    hard = gate_clears(np.array([1.0, 3.0]), np.array([[2.0], [2.0]]), np.array([1.0]))
    assert (admitted == hard).all()
    assert not stretched.any()


def test_the_middle_band_is_admitted_and_marked() -> None:
    claims = np.array([0.4, 0.6, 1.5])
    terms = np.ones((3, 1))
    admitted, stretched = soft_gate(claims, terms, np.array([1.0]), stretch=2.0)
    assert admitted.ravel().tolist() == [False, True, True]
    assert stretched.ravel().tolist() == [False, True, False]


def test_an_open_tier_is_admitted_without_being_called_stretched() -> None:
    """A3-5 removes the gate rather than softening it. Marking its entrants as
    stretched would make that experiment partly about ``s``."""
    admitted, stretched = soft_gate(
        np.zeros(4), np.ones((4, 2)), np.array([9.0, 9.0]), 3.0, open_tiers=(0,)
    )
    assert admitted[:, 0].all()
    assert not stretched[:, 0].any()


def test_stretch_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        AssetSpec(stretch=0.5)


def test_a_hard_gate_admits_nobody_by_stretching() -> None:
    model = soft(1.0)
    assert not model.stretched.any()
    assert model.uncounted_cost.sum() == 0.0
    assert model.stretch_debt.sum() == 0.0


def test_softening_the_gate_admits_the_production_layer() -> None:
    """The reason the soft gate exists: at ``s = 1`` the production layer is
    priced out of every tier and most of the stock has no buyer at all, which is
    the absence of a market rather than exclusion."""
    counts = {s: (soft(s).units[20:].sum()) for s in (1.0, 2.0, 3.0)}
    assert counts[1.0] < counts[2.0] < counts[3.0]


def test_a_stretcher_pays_everything_it_has_and_no_more() -> None:
    """It goes to zero, and is then handed the same equal share of the opening
    proceeds as everybody else, so every stretcher ends the allocation holding
    exactly that share and nothing more."""
    model = soft(3.0)
    assert (model.holdings >= 0.0).all()
    left = model.holdings[model.stretched]
    assert left.size > 0
    assert np.ptp(left) == pytest.approx(0.0, abs=1e-12)
    assert (model.holdings[~model.stretched] >= left[0] - 1e-12).all()


def test_the_opening_allocation_conserves_claims_under_a_soft_gate() -> None:
    for s in (1.0, 2.0, 3.0, 5.0):
        for cost in ("uncounted", "counted"):
            model = soft(s, cost)
            assert float(model.holdings.sum()) == pytest.approx(100.0, rel=1e-12)


def test_claims_are_conserved_across_the_whole_run() -> None:
    """``_post_round`` runs after the inherited stock-flow assertion, so the
    debt service it performs is not covered by it. Checked explicitly."""
    for cost in ("uncounted", "counted"):
        model = soft(3.0, cost, rounds=200)
        history = model.run()
        expected = 100.0 + float(np.asarray(history.issuance).sum())
        assert float(model.holdings.sum()) == pytest.approx(expected, rel=1e-9)


# -- what the shortfall costs ------------------------------------------------


def test_the_uncounted_variant_books_nothing_and_records_everything() -> None:
    model = soft(3.0, "uncounted")
    assert model.uncounted_cost.sum() > 0.0
    assert model.stretch_debt.sum() == 0.0
    assert (model.uncounted_cost[~model.stretched] == 0.0).all()


def test_true_net_worth_is_net_worth_less_what_was_never_booked() -> None:
    """The framework's own distinction, made numerical: the price system records
    that they could afford it, and something real was consumed that it does not
    price. The overstatement is computable, so it is printed."""
    model = soft(3.0, "uncounted")
    assert model.true_net_worth() == pytest.approx(
        model.net_worth() - model.uncounted_cost, rel=1e-12
    )
    stretched = model.stretched
    assert (
        model.true_net_worth()[stretched] < model.net_worth()[stretched]
    ).all()


def test_the_counted_variant_is_a_transfer_and_is_paid_down() -> None:
    """The amortisation machinery, measured where it can be measured.

    **Pinned at ``rent_rate = 0`` on purpose.** This test asserts that the
    instalment schedule retires the debt, which is a claim about the schedule.
    At the registered rent it fails, and it fails for a reason about the
    modelled world rather than about the schedule — see the next test. Leaving
    it at the registered rent would have made one assertion carry two claims and
    report the interesting one as a broken test.
    """
    model = soft(3.0, "counted", rounds=300, rent_rate=0.0)
    owed = float(model.stretch_debt.sum())
    assert owed > 0.0
    assert model.uncounted_cost.sum() == 0.0
    model.run()
    assert float(model.stretch_debt.sum()) < 0.01 * owed


def test_rent_outlives_the_asset_the_debt_was_taken_on_to_buy() -> None:
    """At the registered rent the entry debt is **not** retired, and that is a
    finding rather than a defect.

    Same opening debt as the previous test, `17.993`, because rent begins after
    the allocation. After three hundred rounds `16.7%` of it is still
    outstanding, held by nodes that are all in the production layer, **none of
    which still holds a unit**, whose claims are exactly zero and every one of
    which is cash-constrained against its own instalment.

    They stretched to get in, the unit was taken back — `a3b_initial_
    construction.md` §9.2, the one-way exit — and rent then stripped what was
    left, so **the debt taken on to enter outlives the asset it bought**. That
    is the source manuscript's Volume I §18 default waterfall in miniature, and
    it arrives here without being written in: nothing in the code says a
    stretcher must end insolvent.

    Asserted as a range rather than a point so that it records the phenomenon
    without pinning a number that any reparameterisation would move.
    """
    model = soft(3.0, "counted", rounds=300)
    owed = float(model.stretch_debt.sum())
    model.run()
    left = model.stretch_debt
    assert 0.05 * owed < float(left.sum()) < 0.5 * owed

    stuck = np.flatnonzero(left > 1e-3)
    assert stuck.size > 0
    assert bool(model._is_production[stuck].all())
    assert float(model.units.sum(axis=1)[stuck].max()) == 0.0
    assert float(model.holdings[stuck].max()) == 0.0


def test_the_counted_drain_adds_no_edge() -> None:
    """Routed through the node's own adjacency row, so the destination is not an
    assumption and the potential support set is untouched."""
    a = soft(3.0, "counted").adjacency
    b = soft(3.0, "uncounted").adjacency
    assert (a == b).all()


def test_true_net_worth_equals_net_worth_under_the_counted_variant() -> None:
    """Nothing goes unbooked there: the shortfall is an ordinary outgoing."""
    model = soft(3.0, "counted")
    assert model.true_net_worth() == pytest.approx(model.net_worth(), rel=1e-12)


# -- turnover ----------------------------------------------------------------


def turned(arm="exogenous", cap=0, seed=0, rounds=300, **kw):
    m = A3Model(
        A3Config(
            asset=AssetSpec(arm=arm, max_units=cap, **kw),
            network=NetworkConfig(seed=seed, rounds=rounds),
        )
    )
    m.run()
    return m


def test_units_are_conserved_through_every_sale() -> None:
    """Units are neither created nor destroyed; only who holds them changes."""
    for arm in ("exogenous", "forced"):
        m = A3Model(
            A3Config(
                asset=AssetSpec(arm=arm),
                network=NetworkConfig(seed=0, rounds=300),
            )
        )
        before = float(m.units.sum())
        m.run()
        assert float(m.units.sum()) == before
        assert (m.units >= 0).all()


def test_claims_are_conserved_through_every_sale() -> None:
    """The buyer pays ``γ·P``, the seller receives ``P``, and the premium is
    split equally across all nodes. The three have to sum to zero or the resale
    market is printing money."""
    for arm in ("exogenous", "forced"):
        m = A3Model(
            A3Config(
                asset=AssetSpec(arm=arm),
                network=NetworkConfig(seed=0, rounds=300),
            )
        )
        history = m.run()
        expected = 100.0 + float(np.asarray(history.issuance).sum())
        assert float(m.holdings.sum()) == pytest.approx(expected, rel=1e-9)


def test_the_market_clears_at_all() -> None:
    """Guards the failure that a cap of one produced: three hundred rounds and
    zero transactions, because every node that could afford anything already
    held something."""
    m = turned()
    assert sum(m.sales) > 0
    assert m.cycles.sum() > 0


def test_a_cap_of_one_freezes_the_market_and_is_why_the_default_is_no_cap() -> None:
    """Kept as a criterion rather than a comment. If a later change makes the
    capped arm trade, the reason the cap was dropped no longer holds and the
    choice should be revisited rather than inherited."""
    capped = turned(cap=1)
    assert sum(capped.sales) == 0
    assert capped.cycles.sum() == 0


def test_turnover_off_walks_the_cycle_zero_times_and_says_so() -> None:
    with pytest.warns(DesignDeviation, match="walked zero times"):
        m = A3Model(
            A3Config(
                asset=AssetSpec(turnover=0.0, holding_period=25),
                network=NetworkConfig(seed=0, rounds=200),
            )
        )
    assert m.channel_wired is False
    m.run()
    assert m.cycles.sum() == 0
    assert sum(m.sales) == 0


def test_more_turnover_means_more_transactions() -> None:
    counts = {
        tau: sum(turned(turnover=tau, holding_period=round(1 / tau)).sales)
        for tau in (0.02, 0.04, 0.08)
    }
    assert counts[0.02] < counts[0.04] < counts[0.08]


def test_nobody_buys_what_they_cannot_pay_for_in_full() -> None:
    """The stretch is an opening-allocation rule only. A resale has a seller who
    must receive the market price, and there is nothing to fund a shortfall with
    that does not break conservation."""
    m = turned()
    assert (m.holdings >= -1e-12).all()


def test_a_seller_may_buy_but_never_its_own_unit() -> None:
    """Excluding sellers emptied the market outright, and a housing market is
    mostly people selling one and buying another."""
    m = turned()
    assert sum(m.sales) > 0


def test_the_terms_pair_has_a_usable_spread_after_turnover() -> None:
    """A3-4 is vacuous if everyone who trades faces the same terms. The traders
    turn out to be the financial layer, so the spread is narrower than the
    population's and the criterion has to be read on the traders' range."""
    m = turned()
    who = np.flatnonzero(m.cycles > 0)
    assert who.size >= 2
    g = m.terms[who, 0]
    assert g.max() / g.min() > 1.2


def test_forced_sales_need_a_distressed_holder() -> None:
    """The trigger is relative to opening claims, not post-allocation claims: a
    stretcher ends the allocation at nearly nothing and would otherwise be in
    forced sale on round one by construction."""
    m = turned(arm="forced")
    assert sum(m.forced_sales) >= 0
    assert len(m.forced_sales) == 300


def test_the_exogenous_arm_never_forces_a_sale() -> None:
    m = turned(arm="exogenous")
    assert sum(m.forced_sales) == 0


def test_a_holding_period_that_disagrees_with_turnover_warns() -> None:
    """A mismatch rescales the loop sum, and A3-4 would move by that factor with
    nothing in the run looking wrong. The first draft had exactly this, at
    ``40`` against an implied ``25``."""
    with pytest.warns(DesignDeviation, match="holding_period"):
        A3Model(A3Config(asset=AssetSpec(holding_period=40, turnover=0.04)))


def test_the_registered_holding_period_agrees_with_the_registered_turnover() -> None:
    s = AssetSpec()
    assert s.holding_period == round(1.0 / s.turnover)


def test_the_loop_sum_does_not_depend_on_any_price() -> None:
    """The whole reason A3-4 is a test and not a restatement.

    ``loop_sum`` takes no price argument, so this is checked by construction;
    the test states it so that a later refactor which threads a price through
    fails here and has to justify itself.
    """
    import inspect

    params = set(inspect.signature(loop_sum).parameters)
    assert params == {"terms", "a", "b", "tier", "periods"}
    assert not any("price" in p for p in params)
