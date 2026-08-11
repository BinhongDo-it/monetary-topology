"""Tests for stage A4: the demographic layer and the four competing channels.

Most of these are guards rather than findings. The load-bearing one is
``test_control_cell_reproduces_a2_bitwise``: if the cell with connectivity on and
every competitor off is not the stage A2 run to the last bit, then A4 is a
different model rather than a generalisation of A2, the amplification ratios are
comparing two models instead of two switch positions, and nothing in the stage
means what it says.

The second group guards conservation. Every channel here is a reshuffle, so an
arm that silently created claims would raise the Gini partly by inflating the top
rather than by concentrating a fixed stock. Those are not the same finding and
only one of them is the stage's subject.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from monetary_topology.mechanisms import (
    A4Config,
    A4Model,
    MechanismParams,
    Switches,
    cell_configs,
    cross_layer_baseline,
    gini,
    run_a4,
)
from monetary_topology.network import (
    NetworkConfig,
    NetworkSpec,
    build_graph,
    run_network,
)

SEEDS = range(3)
ROUNDS = 200


def a4(
    *,
    C=True,
    I=False,  # noqa: E741 -- the pre-registration names the switch I
    E=False,
    K=False,
    M=False,
    seed=0,
    rounds=ROUNDS,
    params=None,
    order="capital_first",
    event_order="inherit_first",
    pooling="round",
):
    switches = Switches(
        connectivity=C, inheritance=I, education=E, capital=K, mating=M
    )
    base = NetworkConfig(rounds=rounds)
    cfg = cell_configs(
        switches, seeds=range(seed, seed + 1), base=base, params=params,
        channel_order=order, event_order=event_order, pooling=pooling,
    )[0]
    return run_a4(cfg)


# -- the Gini itself ---------------------------------------------------------


def test_gini_of_a_constant_is_zero() -> None:
    assert gini(np.full(50, 3.0)) == pytest.approx(0.0, abs=1e-12)


def test_gini_of_a_point_mass_approaches_one() -> None:
    x = np.zeros(1000)
    x[0] = 1.0
    assert gini(x) == pytest.approx(1.0 - 1.0 / 1000)


def test_gini_is_scale_invariant() -> None:
    rng = np.random.default_rng(0)
    x = rng.random(200)
    assert gini(x) == pytest.approx(gini(1000.0 * x))


def test_gini_of_empty_or_zero_is_zero() -> None:
    assert gini(np.zeros(10)) == 0.0
    assert gini(np.array([])) == 0.0


def test_gini_rejects_negative_holdings() -> None:
    with pytest.raises(ValueError, match="negative"):
        gini(np.array([1.0, -1.0]))


def test_cross_layer_baseline_matches_a_simulated_matching() -> None:
    n, k = 200, 20
    rng = np.random.default_rng(7)
    labels = np.zeros(n, dtype=bool)
    labels[:k] = True
    rates = []
    for _ in range(4000):
        seat = rng.permutation(n)
        rates.append((labels[seat[0::2]] != labels[seat[1::2]]).mean())
    assert np.mean(rates) == pytest.approx(cross_layer_baseline(n, k), abs=5e-3)


# -- strict generalisation ---------------------------------------------------


def test_control_cell_reproduces_a2_bitwise() -> None:
    """C on, every competitor off, must be stage A2 to the last bit."""
    for seed in SEEDS:
        spec = NetworkSpec(seed=seed)
        base = run_network(NetworkConfig(spec=spec, seed=seed, rounds=ROUNDS))
        got = a4(seed=seed).history
        for name in (
            "total_volume",
            "effective_support",
            "effective_support_l2",
            "realized_support",
            "layer1_volume",
            "layer2_inflow",
            "wage_owed",
            "wage_paid",
            "issuance",
            "holdings",
        ):
            assert (
                np.asarray(getattr(base, name)) == np.asarray(getattr(got, name))
            ).all(), f"{name} differs at seed {seed}"


def test_control_cell_is_order_independent() -> None:
    """With no channel firing, the two orderings cannot differ."""
    for seed in SEEDS:
        a = a4(seed=seed, order="capital_first").history.holdings
        b = a4(seed=seed, order="pooling_first").history.holdings
        assert (np.asarray(a) == np.asarray(b)).all()


def test_uniform_access_does_not_disturb_the_stratified_graph() -> None:
    """The C switch is additive: its default leaves A2's graph untouched."""
    for seed in SEEDS:
        spec = NetworkSpec(seed=seed)
        assert (
            build_graph(spec) == build_graph(replace(spec, uniform_access=False))
        ).all()


# -- what "C off" is ---------------------------------------------------------


def test_uniform_access_graph_is_complete_and_seed_free() -> None:
    a = build_graph(NetworkSpec(seed=0, uniform_access=True))
    b = build_graph(NetworkSpec(seed=11, uniform_access=True))
    assert (a == b).all(), "a complete graph is not a draw and cannot depend on a seed"
    assert np.trace(a) == 0.0
    assert a.sum() == a.shape[0] * (a.shape[0] - 1)


def test_uniform_access_leaves_the_discretionary_graph_alive() -> None:
    """The null arm must be a live economy, not a payroll wash.

    Under uniform access every node both funds and receives payroll, so the mask
    subtracted from the discretionary graph elsewhere would be the full matrix.
    If that subtraction ever returns, holdings stop moving entirely and every
    competing mechanism reports zero against a perfectly uniform reference. The
    factorial would then be comparing four channels on a dead economy.
    """
    model = A4Model(A4Config(switches=Switches(connectivity=False)))
    assert model._route.sum() > 0.0
    assert (model._route.sum(axis=1) > 0).all()


def test_uniform_access_starts_uniform_and_stays_nearly_so() -> None:
    # ``history.holdings[0]`` is the end of round zero, so the starting vector
    # is read off the model instead.
    model = A4Model(A4Config(switches=Switches(connectivity=False)))
    assert np.ptp(model.holdings) == pytest.approx(0.0, abs=1e-12)
    assert a4(C=False).gini_final < 0.02, "the null calibration of prediction A4-1"


def test_uniform_access_preserves_the_aggregate_spending_flow() -> None:
    """Claim-weighted, not node-weighted. See the note in ``network.py``."""
    strat = A4Model(A4Config(switches=Switches(connectivity=True)))
    flat = A4Model(A4Config(switches=Switches(connectivity=False)))
    mid = lambda m: 0.5 * (m._p_low + m._p_high)  # noqa: E731
    aggregate_strat = float((mid(strat) * strat.holdings).sum())
    aggregate_flat = float((mid(flat) * flat.holdings).sum())
    assert aggregate_flat == pytest.approx(aggregate_strat, rel=0.02)


# -- conservation ------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {},
        {"I": True},
        {"E": True},
        {"K": True},
        {"M": True},
        {"I": True, "E": True, "K": True, "M": True},
    ],
)
@pytest.mark.parametrize("C", [True, False])
def test_claims_are_conserved_in_every_arm(C, kw) -> None:
    """The stock-flow assertion lives inside the run; reaching the end is the
    test. The total is then checked against issuance explicitly."""
    r = a4(C=C, rounds=120, **kw)
    holdings = np.asarray(r.history.holdings)
    expected = 100.0 + np.cumsum(np.asarray(r.history.issuance))
    assert holdings.sum(axis=1) == pytest.approx(expected, rel=1e-9)


def test_capital_returns_do_not_create_claims() -> None:
    model = A4Model(
        A4Config(
            switches=Switches(capital=True),
            params=MechanismParams(capital_sd=0.5),
        )
    )
    model._draw_generation_traits()
    before = float(model.holdings.sum())
    model._apply_returns()
    assert float(model.holdings.sum()) == pytest.approx(before, rel=1e-12)
    assert not np.allclose(model.holdings, model.holdings[0])


def test_equal_division_is_inheritance_at_zero_retention() -> None:
    model = A4Model(A4Config(switches=Switches(inheritance=True)))
    model._retention = 0.0
    model.holdings = np.linspace(1.0, 5.0, model._n)
    total = float(model.holdings.sum())
    model._inherit()
    assert float(model.holdings.sum()) == pytest.approx(total, rel=1e-12)
    assert np.ptp(model.holdings) == pytest.approx(0.0, abs=1e-12)


def test_full_retention_is_the_identity() -> None:
    model = A4Model(A4Config(switches=Switches(inheritance=True)))
    model._retention = 1.0
    model.holdings = np.linspace(1.0, 5.0, model._n)
    before = model.holdings.copy()
    model._inherit()
    assert model.holdings == pytest.approx(before, rel=1e-12)


# -- the household layer -----------------------------------------------------


def test_demography_does_not_fire_with_both_channels_off() -> None:
    """Pinned in the pre-registration. Pairing plus pooling plus an equal split
    reshuffles holdings even with both channels nominally off, which would break
    the bitwise reproduction above."""
    for kw in ({}, {"E": True}, {"K": True}, {"E": True, "K": True}):
        r = a4(**kw)
        assert r.generational_events == 0
        assert np.isnan(r.cross_layer_rate)


def test_partners_hold_the_same_amount_after_pooling() -> None:
    model = A4Model(A4Config(switches=Switches(mating=True)))
    model._rematch()
    model.holdings = np.linspace(1.0, 9.0, model._n)
    total = float(model.holdings.sum())
    model._pool_households()
    assert float(model.holdings.sum()) == pytest.approx(total, rel=1e-12)
    assert model.holdings == pytest.approx(model.holdings[model._partner], rel=1e-12)


def test_pairing_is_an_involution_without_fixed_points() -> None:
    model = A4Model(A4Config(switches=Switches(mating=True)))
    model._rematch()
    p = model._partner
    assert (p[p] == np.arange(model._n)).all()
    assert (p != np.arange(model._n)).all()


def test_partners_draw_one_propensity_between_them() -> None:
    """The lockstep. Two agents holding the same amount and choosing separately
    is a transfer; the shared draw is what makes it a household."""
    model = A4Model(A4Config(switches=Switches(mating=True)))
    model._rematch()
    model.holdings = np.full(model._n, 1.0)
    matrix = model._discretionary_flow()
    # Spending, not holdings. Partners spend the same because they hold the
    # same and share the draw; their holdings then diverge again within the
    # round because they receive over different edges, and the pooling step is
    # what closes that gap.
    spent = matrix.sum(axis=1)
    assert spent == pytest.approx(spent[model._partner], rel=1e-12)
    assert spent.std() > 0.0, "a constant spend vector would pass vacuously"


def test_ties_in_holdings_are_broken_at_random_not_by_index() -> None:
    """Guards the artefact described in ``_rematch``.

    With every agent holding the same amount a stable sort ranks them by slot
    index, adjacent slots pair, and the cross-layer rate collapses to roughly
    one over the financial layer's size. That number is a property of the sort
    routine, and it lands in exactly the arm prediction A4-6 uses as its
    reference.
    """
    n = 200
    k = NetworkSpec().layer1_size
    rates = []
    for seed in range(12):
        model = A4Model(
            A4Config(
                switches=Switches(connectivity=False, mating=True),
                params=MechanismParams(assortativity=1.0),
                network=replace(NetworkConfig(), seed=seed),
            )
        )
        model.holdings = np.full(model._n, 0.5)
        model._rematch()
        rates.append(model._cross_layer_events[-1])
    assert np.mean(rates) == pytest.approx(cross_layer_baseline(n, k), abs=0.05)
    assert np.mean(rates) > 0.10, "index-order pairing would land near 0.05"


def test_matching_never_reads_the_layer_label() -> None:
    """Prediction A4-6 is only meaningful if the rule is blind to the layer.

    Relabelling which slots count as the financial layer must leave the pairing
    identical, since the label enters the measurement and nothing else.
    """
    model = A4Model(A4Config(switches=Switches(mating=True)))
    model._rematch()
    first = model._partner.copy()

    other = A4Model(A4Config(switches=Switches(mating=True)))
    other._is_layer1 = ~other._is_layer1
    other._rematch()
    assert (other._partner == first).all()


def test_assortative_matching_pairs_similar_holdings() -> None:
    model = A4Model(
        A4Config(
            switches=Switches(mating=True),
            params=MechanismParams(assortativity=1.0),
        )
    )
    model.holdings = np.random.default_rng(3).random(model._n)
    model._rematch()
    gap = np.abs(model.holdings - model.holdings[model._partner]).mean()

    model._assortativity = 0.0
    model._rematch()
    random_gap = np.abs(model.holdings - model.holdings[model._partner]).mean()
    assert gap < 0.25 * random_gap


# -- the competing channels are not decoration -------------------------------


def test_education_redistributes_payroll_without_enlarging_it() -> None:
    model = A4Model(
        A4Config(
            switches=Switches(education=True),
            params=MechanismParams(education_sd=1.0),
        )
    )
    assert model._wage_weights is not None
    assert model._wage_weights.sum() == pytest.approx(1.0, rel=1e-12)
    assert model._wage_weights.std() > 0.0


def test_education_off_leaves_payroll_weights_unset() -> None:
    model = A4Model(A4Config(switches=Switches()))
    assert model._wage_weights is None, (
        "an equal split must stay the untouched branch: total / k and "
        "total * (1 / k) are not the same float"
    )


def test_pooling_rule_is_validated() -> None:
    with pytest.raises(ValueError, match="pooling must be one of"):
        A4Config(pooling="sometimes")
    with pytest.raises(ValueError, match="event_order must be one of"):
        A4Config(event_order="whenever")


def test_generation_pooling_settles_only_at_the_event() -> None:
    """The two pooling rules must actually be different runs.

    Under ``generation`` the partners' holdings are equal on the round the
    household forms and have diverged again by the round before the next event.
    Under ``round`` they are equal at the close of every round.
    """
    per_round = a4(M=True, rounds=90, pooling="round").history.holdings
    per_gen = a4(M=True, rounds=90, pooling="generation").history.holdings
    assert not np.allclose(per_round, per_gen)


def test_the_cross_layer_conduit_is_what_the_pooling_rule_controls() -> None:
    """Pooling every round is a zero-cost transfer of unbounded bandwidth
    between two arbitrary nodes, so a household straddling the thermocline is a
    permanent conduit across it. This test pins the size of that effect, because
    it is large enough to be mistaken for the ``M`` channel itself: measured on
    the stratified arm it is most of what ``I`` and ``M`` appear to do.
    """
    control = a4(rounds=200).gini_final
    per_round = a4(M=True, rounds=200, pooling="round").gini_final
    per_gen = a4(M=True, rounds=200, pooling="generation").gini_final
    assert control - per_round > 0.10, "the conduit should be large under round pooling"
    assert abs(control - per_gen) < 0.02, "and nearly gone under generation pooling"


def test_event_order_changes_what_the_matching_rule_sees() -> None:
    """A4-5's second half. Matching before the estate is settled is matching on
    family background; matching after it is matching on realised endowment."""
    first = a4(I=True, M=True, rounds=200, event_order="inherit_first")
    second = a4(I=True, M=True, rounds=200, event_order="match_first")
    assert not np.allclose(first.history.holdings, second.history.holdings)


def test_channel_order_is_vacuous_under_generation_pooling() -> None:
    """Stated so that a future reader does not take a null A4-5 result on the
    within-round ordering as evidence when the pooling rule made it untestable.
    """
    a = a4(M=True, K=True, rounds=90, pooling="generation", order="capital_first")
    b = a4(M=True, K=True, rounds=90, pooling="generation", order="pooling_first")
    assert (
        np.asarray(a.history.holdings) == np.asarray(b.history.holdings)
    ).all()


def test_traits_are_drawn_once_when_there_is_no_demography() -> None:
    """A cohort with no generational event lasts the whole run.

    This guards a bug that made the stage report nothing: the trait draw used to
    hang off the generational event, so with I and M off it never fired and both
    E and K silently did nothing while still appearing in the factorial.
    """
    model = A4Model(
        A4Config(
            switches=Switches(education=True, capital=True),
            params=MechanismParams(education_sd=1.0, capital_sd=0.1),
        )
    )
    assert model._education.std() > 0.0
    assert model._returns.std() > 0.0
