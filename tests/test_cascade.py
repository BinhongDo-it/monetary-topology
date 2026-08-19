"""Tests for the A1 cascade model.

These do not test that the stage's answer is right; the stage has no answer yet.
They test the four things ``docs/a1_prereg.md`` will read off this model and that
would otherwise fail silently: the zero calibration is exactly zero, the drop
order is read from the cost rule rather than written down, settlement asymmetry
is doing work, and the delinquency denominator is balance rather than headcount.
"""

from __future__ import annotations

import pytest

from monetary_topology.cascade import (
    RESOURCE_SUPPORT,
    SHORTFALL_TOLERANCE,
    BaselineInfeasible,
    CascadeModel,
    CascadeSpec,
    CostRule,
    Cushion,
    Household,
    Obligation,
    PopulationSpec,
    StratumInputs,
    allocate,
    baseline_stress,
    build_from_records,
    build_population,
    credit_per_household,
    distinct_records,
    PAYMENT_RATE,
    AllocationProblem,
    DrawDegenerate,
    HouseholdRecord,
    Tenure,
    free_parameters,
    max_dispersion,
    mortgage_stock_per_mortgaged,
    per_tenure,
    realised_consumer_credit,
    record_of_each,
    sourced_parameters,
)

# Per-stratum, per-household, monthly, in the shape the CEX and SCF deliver.
# The levels are the real ones divided by twelve; they are scaffolding here and
# the experiment sources its own.
INCOME = tuple(x / 12 for x in (36891.2, 127322.0, 346942.0, 346942.0))
BASKET = tuple(x / 12 for x in (15025.0, 24709.0, 35286.0, 35286.0))
#: CEX Table 1110 housing tenure by income decile, grouped 50/40/9/1. Read
#: from the same table as the shelter flows they divide.
OWNERSHIP = (0.522, 0.7425, 0.900, 0.900)
MORTGAGED = (0.190, 0.5050, 0.700, 0.700)
OUTRIGHT = tuple(o - m for o, m in zip(OWNERSHIP, MORTGAGED))
RENTERS = tuple(1.0 - o for o in OWNERSHIP)
RENT_PER_CU = tuple(x / 12 for x in (6162.0, 5560.0, 3592.0, 3592.0))
#: Interest plus principal, both taken as cash handed over. The published
#: principal line is negative, so the sum as published would be 283 a year at
#: the bottom and would fall at the top.
MORTGAGE_PER_CU = tuple(x / 12 for x in (2295.6, 8301.0, 20916.0, 20916.0))
CC_SHARES = (0.518, 0.349, 0.101, 0.033)
MORTGAGE_SHARES = (0.225, 0.490, 0.244, 0.041)
RATIO = 2.7244
#: Z.1 consumer credit over the CEX household count.
AGGREGATE_CREDIT = 5_073_031e6 / 135_760e3


#: Inside the limit the published means allow. At the real inputs the bottom
#: half's mortgaged households spend 0.862 of their disposable on debt service
#: and a Beta with that mean cannot carry a coefficient of variation above
#: 0.231, so the module's registered 0.25 is refused here rather than silently
#: degenerating. The fixture uses a value every cell supports; which value the
#: stage runs at is the experiment's to state.
FIXTURE_DISPERSION = 0.14


def make_spec(**overrides: object) -> PopulationSpec:
    kwargs: dict[str, object] = {
        "consumer_credit_shares": CC_SHARES,
        "mortgage_shares": MORTGAGE_SHARES,
        "mortgage_to_consumer_credit": RATIO,
        "dispersion": FIXTURE_DISPERSION,
    }
    kwargs.update(overrides)
    return PopulationSpec(**kwargs)  # type: ignore[arg-type]


def make_inputs(spec: PopulationSpec | None = None, **overrides: object):
    spec = spec or make_spec()
    kwargs: dict[str, object] = {
        "income": INCOME,
        "basket": BASKET,
        "rent_per_renter": tuple(
            per_tenure(r, s) for r, s in zip(RENT_PER_CU, RENTERS)
        ),
        "mortgage_per_mortgaged": tuple(
            per_tenure(m, s) for m, s in zip(MORTGAGE_PER_CU, MORTGAGED)
        ),
        "mortgage_stock_per_mortgaged": mortgage_stock_per_mortgaged(
            spec, AGGREGATE_CREDIT, MORTGAGED
        ),
        "renter_share": RENTERS,
        "mortgaged_share": MORTGAGED,
        "outright_share": OUTRIGHT,
        "consumer_credit_per_household": credit_per_household(
            spec, AGGREGATE_CREDIT
        ),
    }
    kwargs.update(overrides)
    return StratumInputs(**kwargs)  # type: ignore[arg-type]


def make_population(seed: int = 0, spec: PopulationSpec | None = None,
                    **input_overrides: object):
    spec = spec or make_spec()
    return build_population(spec, make_inputs(spec, **input_overrides), seed)


def flat_path(periods: int, multiplier: float = 1.0, n_strata: int = 4):
    return [tuple([multiplier] * n_strata) for _ in range(periods)]


def bare_household(due: dict[Obligation, float], buffer: float,
                   income: float = 0.0, necessities: float = 0.0) -> Household:
    """A household with exactly the obligations named.

    ``necessities`` is recorded for provenance; the basket only exists as a rung
    if ``Obligation.BASKET`` is in ``due``.
    """
    return Household(
        stratum=0,
        income_group=0,
        tenure=(Tenure.MORTGAGED if Obligation.MORTGAGE in due
                else Tenure.RENTER if Obligation.RENT in due
                else Tenure.OUTRIGHT),
        income=income,
        necessities=necessities,
        buffer=buffer,
        balances=dict(due),
        due=dict(due),
    )


# ---------------------------------------------------------------------------
# A1-1: the zero calibration
# ---------------------------------------------------------------------------
def test_no_shock_produces_exactly_zero_on_every_rung() -> None:
    model = CascadeModel(make_population(), CostRule())
    result = model.run(flat_path(24))
    for kind in Obligation:
        assert result.delinquent_share[kind.value] == [0.0] * 24
    assert result.first_default_counts == {k.value: 0 for k in Obligation}
    assert result.defaulting_households == 0
    assert result.displaced == 0
    assert result.renters_ever_behind == 0


def test_the_zero_calibration_holds_in_the_netting_arm_too() -> None:
    model = CascadeModel(
        make_population(),
        CostRule(),
        CascadeSpec(income_arrives_after_due=False),
    )
    result = model.run(flat_path(24))
    assert result.delinquent_share["CARD"] == [0.0] * 24


def test_a_population_that_cannot_pay_at_baseline_is_refused() -> None:
    """No disposable, so no share of it can be drawn."""
    starved = tuple(x * 4 for x in BASKET)
    with pytest.raises(BaselineInfeasible):
        make_population(basket=starved)


def test_a_group_that_cannot_service_its_published_debt_is_a_finding() -> None:
    """It must not be rescaled away inside the constructor."""
    spec = make_spec()
    heavy = tuple(x * 40 for x in credit_per_household(spec, AGGREGATE_CREDIT))
    with pytest.raises(BaselineInfeasible) as caught:
        make_population(spec=spec, consumer_credit_per_household=heavy)
    assert "finding" in str(caught.value)


def test_every_household_is_feasible_at_baseline_by_construction() -> None:
    """The property the Beta draw exists to guarantee, at a size that used to
    break the old lognormal draw."""
    big = make_spec(counts=(5000, 4000, 900, 100))
    houses = make_population(spec=big)
    assert len(houses) == 10_000
    for house in houses:
        assert sum(house.due.values()) <= house.income


# ---------------------------------------------------------------------------
# The cost ramp, and the three dynamics that fall out of it
# ---------------------------------------------------------------------------
def test_the_basket_is_the_last_rung_given_up_at_no_arrears() -> None:
    cost = CostRule()
    order = sorted(Obligation, key=lambda k: (cost.cost_now(k), -cost.grace(k)))
    assert order[0] is Obligation.CARD
    assert order[-1] is Obligation.BASKET
    assert cost.cost_now(Obligation.RENT) < cost.cost_now(Obligation.BASKET)


def test_at_no_arrears_the_mortgage_is_skipped_before_the_car() -> None:
    """A consequence of the two clocks, and it is not an accident.

    One missed mortgage payment consumes a twelfth of the foreclosure clock; one
    missed car payment consumes a third of the repossession clock. So a squeezed
    owner skips the mortgage first, which is the reversal of the payment
    hierarchy widely reported after 2008 rather than a defect here. It does not
    by itself move A1-3: mortgage delinquency comes out low through who holds
    mortgages, not through owners protecting them month by month.
    """
    cost = CostRule()
    order = sorted(Obligation, key=lambda k: (cost.cost_now(k), -cost.grace(k)))
    assert [k.value for k in order] == [
        "CARD", "MORTGAGE", "AUTO", "RENT", "BASKET"
    ]
    assert cost.cost_now(Obligation.MORTGAGE) < cost.cost_now(Obligation.AUTO)


def test_arrears_raise_the_cost_of_defaulting_again() -> None:
    """A quarter of the eviction grace at no arrears, all of it at three."""
    cost = CostRule()
    ramp = [cost.cost_now(Obligation.RENT, missed=m) for m in range(5)]
    assert ramp == pytest.approx([0.25, 0.5, 0.75, 1.0, 1.0])
    assert cost.cost_now(Obligation.CARD, missed=3) == 0.0


def _deep_arrears_step(grace_basket: int) -> Household:
    """One household, three rent arrears in, able to pay exactly one rung."""
    house = bare_household(
        {Obligation.RENT: 1.0, Obligation.BASKET: 1.0}, buffer=1.0
    )
    house.missed[Obligation.RENT] = 3
    cost = CostRule(grace_basket=grace_basket)
    CascadeModel([house], cost).step(0, (1.0,))
    return house


def test_whether_rent_arrears_crowd_out_the_basket_turns_on_its_grace() -> None:
    """The crowding-out is the ramp's consequence, and it has a condition.

    At three rent arrears the next miss is the eviction, so shelter costs the
    whole resource. Whether the household starts cutting the basket to keep the
    roof depends on whether the basket can absorb a period at all:

    * ``grace_basket = 1`` makes the first missed basket immediately total, so
      the two rungs cost the same and the household lets the dwelling go;
    * ``grace_basket = 2`` makes one short period survivable, so the basket is
      the cheaper sacrifice and the dwelling is kept.

    This is the free parameter earning its place: it decides whether
    crowding-out exists at all, which is why the stage sweeps it rather than
    pinning it.
    """
    instant = _deep_arrears_step(grace_basket=1)
    assert instant.missed[Obligation.RENT] == 4
    assert instant.missed[Obligation.BASKET] == 0

    absorbing = _deep_arrears_step(grace_basket=2)
    assert absorbing.missed[Obligation.BASKET] == 1
    assert absorbing.missed[Obligation.RENT] == 0


def test_shelter_goes_before_the_basket_at_no_arrears() -> None:
    house = bare_household(
        {Obligation.RENT: 1.0, Obligation.BASKET: 1.0}, buffer=1.0
    )
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert house.missed[Obligation.RENT] == 1
    assert house.missed[Obligation.BASKET] == 0


def test_a_dwelling_that_cannot_be_saved_is_released_first() -> None:
    """Otherwise the household gives up everything and is evicted anyway.

    The hopeless rung has to sort ahead of everything savable rather than level
    with the zero-cost ones: it is the largest obligation on the books, and
    releasing it is what leaves enough to keep the others.
    """
    house = bare_household(
        {Obligation.RENT: 10.0, Obligation.CARD: 0.5, Obligation.BASKET: 0.5},
        buffer=1.0,
    )
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert house.missed[Obligation.RENT] == 1
    assert house.missed[Obligation.CARD] == 0, "the card was payable and paid"
    assert house.missed[Obligation.BASKET] == 0


def test_the_hopeless_rung_sorts_ahead_of_a_zero_cost_savable_one() -> None:
    """The card also costs zero, and the order between them decides the outcome."""
    house = bare_household(
        {Obligation.RENT: 10.0, Obligation.CARD: 0.5, Obligation.BASKET: 0.5},
        buffer=1.0,
    )
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert house.first_default is Obligation.RENT


def test_when_nothing_can_be_saved_everything_defaults(tmp_path: Path) -> None:
    """Low enough income and heavy enough obligations: default regardless."""
    house = bare_household(
        {Obligation.RENT: 10.0, Obligation.CARD: 10.0, Obligation.BASKET: 10.0},
        buffer=1.0,
    )
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert all(n == 1 for n in house.missed.values())


def test_the_grace_periods_must_be_at_least_one_period() -> None:
    for bad in ({"grace_basket": 0}, {"grace_rent": -1}, {"grace_mortgage": 0}):
        with pytest.raises(ValueError):
            CostRule(**bad)


# ---------------------------------------------------------------------------
# A1-2: the order is read off the cost rule
# ---------------------------------------------------------------------------
def test_drop_order_is_derived_from_the_cost_rule_not_written_down() -> None:
    cost = CostRule()
    model = CascadeModel(make_population(), cost)
    expected = sorted(
        Obligation, key=lambda k: (cost.cost_now(k), -cost.grace(k), k.value)
    )
    assert model.drop_order == expected
    assert model.drop_order[0] is Obligation.CARD
    assert model.drop_order[-1] is Obligation.BASKET


def test_a_growing_shortfall_drops_the_cheapest_obligation_first() -> None:
    due = {
        Obligation.CARD: 1.0,
        Obligation.AUTO: 2.0,
        Obligation.MORTGAGE: 4.0,
    }
    # Cheapest first, and at no arrears the mortgage is cheaper than the car:
    # a twelfth of the foreclosure clock against a third of the repossession
    # clock. See test_at_no_arrears_the_mortgage_is_skipped_before_the_car.
    cases = [
        (7.0, set()),
        (6.5, {Obligation.CARD}),
        (4.5, {Obligation.CARD, Obligation.MORTGAGE}),
        (0.0, set(due)),
    ]
    for buffer, expected_missed in cases:
        house = bare_household(due, buffer)
        model = CascadeModel([house], CostRule())
        model.step(0, (1.0,))
        missed = {k for k, n in house.missed.items() if n > 0}
        assert missed == expected_missed, buffer


def test_the_first_default_is_recorded_once_and_is_the_cheapest_held() -> None:
    house = bare_household({Obligation.AUTO: 2.0, Obligation.RENT: 3.0}, 3.0)
    model = CascadeModel([house], CostRule())
    model.step(0, (1.0,))
    assert house.first_default is Obligation.AUTO


def test_a_household_holding_no_card_first_defaults_on_what_it_holds() -> None:
    """A1-2 is a joint test of the cost rule and the holdings, so this matters."""
    house = bare_household({Obligation.RENT: 3.0}, 0.0)
    model = CascadeModel([house], CostRule())
    model.step(0, (1.0,))
    assert house.first_default is Obligation.RENT


# ---------------------------------------------------------------------------
# A1-3: one rule for every class, no multiplier
# ---------------------------------------------------------------------------
def test_shelter_classes_share_the_rule_and_differ_only_in_the_clock() -> None:
    """One rule, no multipliers. Tenure enters through the grace, not a factor."""
    cost = CostRule()
    assert cost.resource(Obligation.RENT) == cost.resource(Obligation.MORTGAGE)
    assert RESOURCE_SUPPORT[Obligation.MORTGAGE] == 1.0
    assert RESOURCE_SUPPORT[Obligation.CARD] == 0.0
    # Same rule, same resource, different clock, therefore different cost.
    assert cost.grace(Obligation.MORTGAGE) != cost.grace(Obligation.RENT)
    assert cost.cost_now(Obligation.RENT) != cost.cost_now(Obligation.MORTGAGE)
    table = cost.table()
    assert len(table) == len(Obligation)
    assert {row[0] for row in table} == {k.value for k in Obligation}


def test_the_commute_share_must_sit_between_the_two_anchors() -> None:
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            CostRule(commute_dependency=bad)


def test_only_rent_is_outside_the_credit_file() -> None:
    cost = CostRule()
    assert cost.cost_later(Obligation.RENT) == 0.0
    assert cost.cost_later(Obligation.CARD) > 0.0


# ---------------------------------------------------------------------------
# Volume One section 4: settlement asymmetry
# ---------------------------------------------------------------------------
def test_income_arriving_after_the_due_date_cannot_pay_it() -> None:
    due = {Obligation.CARD: 1.0}
    late = bare_household(due, buffer=0.0, income=1.0)
    CascadeModel([late], CostRule()).step(0, (1.0,))
    assert late.missed[Obligation.CARD] == 1

    netted = bare_household(due, buffer=0.0, income=1.0)
    CascadeModel(
        [netted], CostRule(), CascadeSpec(income_arrives_after_due=False)
    ).step(0, (1.0,))
    assert netted.missed[Obligation.CARD] == 0


# ---------------------------------------------------------------------------
# Section 2.5: 90+ means three consecutive misses
# ---------------------------------------------------------------------------
def test_delinquency_needs_three_consecutive_misses() -> None:
    house = bare_household({Obligation.CARD: 1.0}, buffer=0.0)
    model = CascadeModel([house], CostRule())
    result = model.run(flat_path(4, multiplier=0.0, n_strata=1))
    assert result.delinquent_share["CARD"][0] == 0.0
    assert result.delinquent_share["CARD"][1] == 0.0
    assert result.delinquent_share["CARD"][2] == 1.0


def test_one_payment_resets_the_counter() -> None:
    house = bare_household({Obligation.CARD: 1.0}, buffer=0.0, income=1.0)
    model = CascadeModel([house], CostRule())
    model.step(0, (0.0,))
    model.step(1, (0.0,))
    assert house.missed[Obligation.CARD] == 2
    assert house.arrears[Obligation.CARD] == pytest.approx(2.0)
    # Clearing takes the arrears as well as this period's due: a missed payment
    # does not vanish, and one good month does not undo two bad ones.
    house.buffer = 2.0
    model.step(2, (0.0,))
    assert house.missed[Obligation.CARD] == 3
    house.buffer = 4.0
    model.step(3, (0.0,))
    assert house.missed[Obligation.CARD] == 0
    assert house.arrears[Obligation.CARD] == 0.0


# ---------------------------------------------------------------------------
# Section 3.1: the denominator is balance, not households
# ---------------------------------------------------------------------------
def test_the_share_is_weighted_by_balance_not_by_headcount() -> None:
    big = bare_household({Obligation.CARD: 1.0}, buffer=0.0)
    big.balances[Obligation.CARD] = 90.0
    small = bare_household({Obligation.CARD: 1.0}, buffer=99.0)
    small.balances[Obligation.CARD] = 10.0
    model = CascadeModel([big, small], CostRule())
    result = model.run(flat_path(3, multiplier=0.0, n_strata=1))
    assert result.delinquent_share["CARD"][2] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# The population reproduces the published shares
# ---------------------------------------------------------------------------
def test_the_published_credit_shares_become_per_household_levels() -> None:
    """The bottom half holds 51.8% of the credit against 50% of the households."""
    spec = make_spec()
    per_household = credit_per_household(spec, AGGREGATE_CREDIT)
    assert per_household[0] > AGGREGATE_CREDIT
    weighted = sum(
        p * c for p, c in zip(per_household, spec.counts, strict=True)
    ) / sum(spec.counts)
    assert weighted == pytest.approx(AGGREGATE_CREDIT)


def test_the_realised_credit_tracks_the_published_target() -> None:
    """The draw's realisation is reported rather than assumed to be exact."""
    spec = make_spec(dispersion=0.0, counts=(500, 400, 90, 10))
    houses = make_population(spec=spec)
    target = credit_per_household(spec, AGGREGATE_CREDIT)
    realised = realised_consumer_credit(houses, 4)
    for got, want in zip(realised, target, strict=True):
        assert got == pytest.approx(want, rel=1e-9)


def test_the_published_mortgage_shares_become_per_borrower_balances() -> None:
    """Weighted by the mortgaged, the stocks reproduce the Z.1 aggregate."""
    spec = make_spec()
    stock = mortgage_stock_per_mortgaged(spec, AGGREGATE_CREDIT, MORTGAGED)
    borrowers = [round(c * r)
                 for c, r in zip(spec.counts, MORTGAGED, strict=True)]
    total = sum(s * n for s, n in zip(stock, borrowers, strict=True))
    assert total == pytest.approx(
        AGGREGATE_CREDIT * sum(spec.counts) * spec.mortgage_to_consumer_credit
    )


def test_the_mortgage_concentrates_upward_without_a_parameter_saying_so() -> None:
    """0.041 of the stock over 1% of the households, against 0.225 over 50%."""
    stock = mortgage_stock_per_mortgaged(make_spec(), AGGREGATE_CREDIT, MORTGAGED)
    assert stock[0] < stock[1] < stock[2] < stock[3]


def test_the_mortgage_balance_is_the_stock_and_not_one_months_payment() -> None:
    """The inert-cell defect, named. Until 2026-08-15 these two were equal."""
    houses = make_population()
    owner = next(h for h in houses if h.stratum == 0 and h.owns)
    stock = mortgage_stock_per_mortgaged(make_spec(), AGGREGATE_CREDIT, MORTGAGED)
    assert owner.balances[Obligation.MORTGAGE] == pytest.approx(stock[0])
    assert owner.balances[Obligation.MORTGAGE] > 12 * owner.due[
        Obligation.MORTGAGE
    ]


def test_the_mortgage_shares_reach_the_balance_weighted_rate() -> None:
    """``docs/a1_prereg.md`` §4.2: an input nothing reads is not an input.

    Move the published concentration and the balance-weighted mortgage
    delinquency has to move with it. Before the stock existed this assertion
    failed, because every owner's balance was one month of their own payment
    and the DFA vector touched nothing.
    """
    spec = make_spec(dispersion=0.0)
    tilted = make_spec(dispersion=0.0,
                       mortgage_shares=(0.600, 0.250, 0.120, 0.030))

    # Only the bottom stratum loses its income. A shock that reaches everyone
    # drives the share to one under any weighting and would hide the input.
    path = [(0.0, 1.0, 1.0, 1.0)] * 8

    def rate(population_spec: PopulationSpec) -> float:
        houses = build_population(
            population_spec, make_inputs(population_spec), seed=0
        )
        model = CascadeModel(houses, CostRule())
        return model.run(path).delinquent_share["MORTGAGE"][-1]

    base, moved = rate(spec), rate(tilted)
    assert 0.0 < base < 1.0, base
    assert moved > base


def test_a_stratum_holding_mortgage_debt_with_no_borrowers_is_refused() -> None:
    spec = make_spec()
    with pytest.raises(ValueError) as caught:
        mortgage_stock_per_mortgaged(spec, AGGREGATE_CREDIT,
                                     (0.0, 0.5, 0.7, 0.7))
    assert "nowhere to sit" in str(caught.value)


def test_borrowers_without_a_mortgage_stock_are_refused() -> None:
    """Checked where the count is in hand rather than on the inputs object.

    An empty stratum carrying a zero stock is correct and common in the
    permutation arm's grid; a stratum with mortgaged households and a zero
    stock is a balance the K shape would be measured on and is not there.
    """
    with pytest.raises(ValueError) as caught:
        make_population(mortgage_stock_per_mortgaged=(0.0, 1.0, 1.0, 1.0))
    assert "K shape" in str(caught.value)


def test_a_stratum_with_no_borrowers_and_no_debt_is_allowed() -> None:
    spec = make_spec(mortgage_shares=(0.0, 0.5, 0.3, 0.2))
    stock = mortgage_stock_per_mortgaged(spec, AGGREGATE_CREDIT,
                                         (0.0, 0.5, 0.7, 0.7))
    assert stock[0] == 0.0


def test_a_per_household_mean_is_spread_over_the_tenure_that_pays_it() -> None:
    """A rent of six thousand across a group that is 39% owners is ten per renter."""
    assert per_tenure(6162.0, 1.0 - 0.3906) == pytest.approx(10111.6, rel=1e-4)
    with pytest.raises(ValueError):
        per_tenure(1.0, 0.0)


def test_tenure_is_three_way_and_follows_the_supplied_shares() -> None:
    houses = make_population()
    for house in houses:
        shelter = sum(k in house.balances for k in
                      (Obligation.MORTGAGE, Obligation.RENT))
        assert shelter == (0 if house.tenure is Tenure.OUTRIGHT else 1)
    bottom = [h for h in houses if h.stratum == 0]
    assert sum(1 for h in bottom
               if h.tenure is Tenure.MORTGAGED) == round(50 * MORTGAGED[0])
    assert sum(1 for h in bottom
               if h.tenure is Tenure.OUTRIGHT) == round(50 * OUTRIGHT[0])
    assert sum(1 for h in bottom if h.tenure is Tenure.RENTER) == 50 - round(
        50 * MORTGAGED[0]) - round(50 * OUTRIGHT[0])


def test_each_tenure_faces_its_own_shelter_payment() -> None:
    houses = make_population()
    renter = next(h for h in houses
                  if h.stratum == 0 and h.tenure is Tenure.RENTER)
    borrower = next(h for h in houses
                    if h.stratum == 0 and h.tenure is Tenure.MORTGAGED)
    outright = next(h for h in houses
                    if h.stratum == 0 and h.tenure is Tenure.OUTRIGHT)
    assert renter.due[Obligation.RENT] == pytest.approx(
        per_tenure(RENT_PER_CU[0], RENTERS[0])
    )
    assert borrower.due[Obligation.MORTGAGE] == pytest.approx(
        per_tenure(MORTGAGE_PER_CU[0], MORTGAGED[0])
    )
    assert Obligation.RENT not in outright.due
    assert Obligation.MORTGAGE not in outright.due


def test_an_outright_owner_cannot_be_displaced() -> None:
    """A third of American households hold their dwelling free of a mortgage,
    and no missed payment takes it. That is population, not leniency."""
    houses = [h for h in make_population() if h.tenure is Tenure.OUTRIGHT]
    assert houses
    model = CascadeModel(houses, CostRule())
    result = model.run(flat_path(24, multiplier=0.0))
    assert result.displaced == 0
    assert result.renters == 0
    assert result.delinquent_share["MORTGAGE"][-1] == 0.0
    assert result.delinquent_share["CARD"][-1] > 0.0


def test_the_inputs_refuse_a_ragged_set_of_vectors() -> None:
    with pytest.raises(ValueError):
        make_inputs(income=(1.0, 2.0))
    with pytest.raises(ValueError):
        make_inputs(renter_share=(1.4, 0.8, 0.9, 1.0))


def test_tenures_that_do_not_sum_to_one_are_refused() -> None:
    """A dropped share is a block of households with no dwelling at all."""
    with pytest.raises(ValueError) as caught:
        make_inputs(outright_share=tuple(v / 2 for v in OUTRIGHT))
    assert "three tenures" in str(caught.value)


def test_a_share_vector_that_does_not_sum_to_one_is_refused() -> None:
    """A group whose series identifier failed to resolve must not be absorbed."""
    with pytest.raises(ValueError):
        make_spec(consumer_credit_shares=(0.518, 0.340, 0.110, 0.0))
    with pytest.raises(ValueError):
        make_spec(mortgage_shares=(0.230, 0.450, 0.220, 0.200))


def test_the_published_rounding_is_accepted_and_renormalised() -> None:
    """The real DFA consumer credit vector sums to 1.001, and used to be refused."""
    spec = make_spec(consumer_credit_shares=(0.518, 0.349, 0.101, 0.033))
    assert sum(spec.consumer_credit_shares) == pytest.approx(1.0)
    assert spec.consumer_credit_shares[0] == pytest.approx(0.518 / 1.001)


def test_a_share_vector_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(ValueError):
        make_spec(consumer_credit_shares=(0.6, 0.4))


def test_a_negative_share_is_refused() -> None:
    with pytest.raises(ValueError):
        make_spec(mortgage_shares=(-0.1, 0.5, 0.4, 0.2))


def test_a_non_positive_aggregate_ratio_is_refused() -> None:
    with pytest.raises(ValueError):
        make_spec(mortgage_to_consumer_credit=0.0)


def test_the_same_seed_gives_the_same_population() -> None:
    a = make_population(seed=7)
    b = make_population(seed=7)
    c = make_population(seed=8)
    assert [h.balances for h in a] == [h.balances for h in b]
    assert [h.balances for h in a] != [h.balances for h in c]


def test_the_free_parameter_budget_is_within_the_registered_bound() -> None:
    free = free_parameters(make_spec(), CostRule(), CascadeSpec())
    names = [name for name, _ in free]
    assert len(free) <= 12, "docs/a1_prereg.md A1-11"
    assert len(set(names)) == len(names)


def test_every_sourced_parameter_carries_a_provenance_line() -> None:
    for name, _value, provenance in sourced_parameters(make_spec()):
        assert provenance.strip(), name


# ---------------------------------------------------------------------------
# Displacement, and the two shelter clocks
# ---------------------------------------------------------------------------
def test_displacement_ends_the_obligation_and_the_arrears() -> None:
    """The model claims nothing about a household after it is displaced."""
    house = bare_household({Obligation.RENT: 1.0}, buffer=0.0)
    model = CascadeModel([house], CostRule(grace_rent=3))
    result = model.run(flat_path(6, multiplier=0.0, n_strata=1))

    assert house.displaced_at == 2, "three arrears at a grace of three"
    assert Obligation.RENT not in house.due
    assert Obligation.RENT not in house.balances
    assert house.arrears[Obligation.RENT] == pytest.approx(3.0), (
        "the arrears at displacement are kept as a record and stop growing"
    )
    assert result.displaced == 1
    assert sum(result.displaced_by_group) == 1


def test_a_displaced_household_leaves_the_delinquency_denominator() -> None:
    housed = bare_household({Obligation.RENT: 1.0}, buffer=99.0)
    evicted = bare_household({Obligation.RENT: 1.0}, buffer=0.0)
    model = CascadeModel([housed, evicted], CostRule(grace_rent=2))
    result = model.run(flat_path(6, multiplier=0.0, n_strata=1))
    assert result.delinquent_share["RENT"][-1] == 0.0, (
        "the only delinquent renter was displaced out of the denominator"
    )
    assert result.displaced == 1


def test_a_displaced_renter_is_still_counted_among_the_renters() -> None:
    house = bare_household({Obligation.RENT: 1.0}, buffer=0.0)
    model = CascadeModel([house], CostRule(grace_rent=2))
    result = model.run(flat_path(6, multiplier=0.0, n_strata=1))
    assert result.renters == 1
    assert result.renters_ever_behind == 1


def test_the_mortgage_clock_is_slower_than_the_rent_clock() -> None:
    """Otherwise the largest obligation on the books is abandoned first."""
    cost = CostRule()
    assert cost.grace(Obligation.MORTGAGE) > cost.grace(Obligation.RENT)
    for missed in (1, 2, 3):
        assert cost.cost_now(Obligation.MORTGAGE, missed) < cost.cost_now(
            Obligation.RENT, missed
        )


def test_a_mortgage_clock_faster_than_rent_is_refused() -> None:
    with pytest.raises(ValueError) as caught:
        CostRule(grace_rent=6, grace_mortgage=3)
    assert "abandoned" in str(caught.value)


def test_an_owner_holds_on_longer_than_a_renter_under_the_same_squeeze() -> None:
    owner = bare_household(
        {Obligation.MORTGAGE: 1.0, Obligation.CARD: 1.0}, buffer=0.0
    )
    renter = bare_household(
        {Obligation.RENT: 1.0, Obligation.CARD: 1.0}, buffer=0.0
    )
    model = CascadeModel([owner, renter], CostRule())
    model.run(flat_path(6, multiplier=0.0, n_strata=1))
    assert renter.displaced_at is not None
    assert owner.displaced_at is None


# ---------------------------------------------------------------------------
# The draw's spread has to be a spread
# ---------------------------------------------------------------------------
def test_a_dispersion_a_mean_cannot_carry_is_refused() -> None:
    """A Beta at mean 0.94 with a coefficient of variation of 0.25 is not a
    wide distribution, it is a coin flip between zero and one."""
    spec = make_spec(dispersion=0.25)
    with pytest.raises(DrawDegenerate) as caught:
        make_population(spec=spec)
    assert "point masses" in str(caught.value)
    assert "largest dispersion" in str(caught.value)


def test_the_limit_is_the_beta_limit_and_not_a_chosen_number() -> None:
    """At concentration zero the variance is m(1-m), so the coefficient of
    variation cannot exceed sqrt((1-m)/m). The floor moves that limit down."""
    for mean in (0.05, 0.4, 0.86, 0.94):
        assert max_dispersion(mean, concentration=0.0) == pytest.approx(
            ((1 - mean) / mean) ** 0.5
        )
        assert max_dispersion(mean) < max_dispersion(mean, concentration=0.0)
    assert max_dispersion(0.94) == pytest.approx(0.1459, rel=1e-3)
    assert max_dispersion(0.0) == 0.0
    assert max_dispersion(1.0) == 0.0


def test_a_dispersion_inside_the_limit_still_draws() -> None:
    houses = make_population(spec=make_spec(dispersion=0.14))
    assert len(houses) == 100


# ---------------------------------------------------------------------------
# Reporting groups, for the arm where a stratum is a cell
# ---------------------------------------------------------------------------
def test_without_a_group_map_a_group_is_a_stratum() -> None:
    model = CascadeModel(make_population(), CostRule())
    assert model.n_groups == 4
    assert [model.group_of(s) for s in range(4)] == [0, 1, 2, 3]


def test_a_group_share_is_a_share_within_the_group() -> None:
    """Two strata reporting as one group, and the aggregate is balance-weighted
    rather than an average of the two shares."""
    a = bare_household({Obligation.CARD: 1.0}, buffer=0.0)
    a.balances[Obligation.CARD] = 90.0
    b = bare_household({Obligation.CARD: 1.0}, buffer=99.0)
    b.balances[Obligation.CARD] = 10.0
    b.stratum = 1
    model = CascadeModel([a, b], CostRule(), groups=(0, 0))
    result = model.run(flat_path(3, multiplier=0.0, n_strata=2))
    assert model.n_groups == 1
    assert result.delinquent_share_by_group["CARD:0"][2] == pytest.approx(0.9)


def test_a_group_map_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(ValueError) as caught:
        CascadeModel(make_population(), CostRule(), groups=(0, 0))
    assert "against 4 strata" in str(caught.value)


def test_an_empty_stratum_holding_credit_is_refused() -> None:
    """The permutation arm's grid has empty corners, and an empty cell holding
    debt is a different thing from an empty cell holding nothing."""
    spec = make_spec(counts=(50, 0, 40, 10),
                     consumer_credit_shares=(0.5, 0.2, 0.2, 0.1),
                     mortgage_shares=(0.5, 0.0, 0.4, 0.1))
    with pytest.raises(ValueError) as caught:
        credit_per_household(spec, AGGREGATE_CREDIT)
    assert "nowhere to sit" in str(caught.value)


def test_an_empty_stratum_holding_nothing_is_allowed() -> None:
    spec = make_spec(counts=(50, 0, 40, 10),
                     consumer_credit_shares=(0.6, 0.0, 0.3, 0.1),
                     mortgage_shares=(0.5, 0.0, 0.4, 0.1))
    assert credit_per_household(spec, AGGREGATE_CREDIT)[1] == 0.0


# ---------------------------------------------------------------------------
# A1b's population: one model household per measured record
# ---------------------------------------------------------------------------
def record(**overrides) -> HouseholdRecord:
    payload = dict(
        weight=100.0,
        group=0,
        income_group=0,
        income_monthly=3_000.0,
        basket_monthly=1_200.0,
        tenure=Tenure.RENTER,
        rent_monthly=900.0,
        mortgage_payment_monthly=0.0,
        mortgage_balance=0.0,
        card_balance=2_000.0,
        card_payment_monthly=74.0,
        vehicle_balance=6_000.0,
    )
    payload.update(overrides)
    return HouseholdRecord(**payload)  # type: ignore[arg-type]


def test_the_allocation_is_deterministic_and_hits_the_size() -> None:
    """No seed anywhere: largest remainder on the weights."""
    records = [record(weight=100.0), record(weight=50.0, group=1),
               record(weight=1.0, group=3)]
    counts = allocate(records, 1_000)
    assert sum(counts) == 1_000
    assert counts == allocate(records, 1_000)
    assert counts[0] > counts[1] > counts[2]


def test_a_record_too_light_for_the_size_gets_no_copy() -> None:
    """Representation rather than error, and the experiment reports it."""
    records = [record(weight=1_000.0), record(weight=0.4, group=1)]
    assert allocate(records, 10) == [10, 0]
    assert distinct_records(records, 10) == 1
    assert distinct_records(records, 10_000) == 2


def test_a_population_smaller_than_one_is_refused() -> None:
    with pytest.raises(AllocationProblem):
        allocate([record()], 0)


def test_every_measured_figure_reaches_the_household() -> None:
    houses = build_from_records([record()], 10)
    assert len(houses) == 10
    house = houses[0]
    assert house.income == 3_000.0
    assert house.due[Obligation.CARD] == 74.0, "the payment is measured"
    assert house.balances[Obligation.CARD] == 2_000.0
    assert house.due[Obligation.AUTO] == pytest.approx(6_000.0 / 60.0)
    assert house.due[Obligation.RENT] == 900.0
    assert Obligation.MORTGAGE not in house.due


def test_the_card_payment_is_not_a_rate_on_the_balance() -> None:
    """The one that would pass unnoticed. The published revolving payment is
    3.7% of the balance a month against the 2% this project cited."""
    house = build_from_records([record(card_payment_monthly=74.0)], 1)[0]
    assert house.due[Obligation.CARD] == 74.0
    assert house.due[Obligation.CARD] != pytest.approx(
        2_000.0 * PAYMENT_RATE[Obligation.CARD]
    )


def test_a_class_with_no_balance_is_not_held() -> None:
    """A zero balance left in would sit in the denominator counting as held."""
    house = build_from_records(
        [record(card_balance=0.0, card_payment_monthly=0.0,
                vehicle_balance=0.0)], 1
    )[0]
    assert Obligation.CARD not in house.balances
    assert Obligation.AUTO not in house.balances
    assert Obligation.RENT in house.balances


def test_an_outright_owner_from_a_record_holds_no_shelter() -> None:
    house = build_from_records(
        [record(tenure=Tenure.OUTRIGHT, rent_monthly=0.0)], 1
    )[0]
    assert Obligation.RENT not in house.due
    assert Obligation.MORTGAGE not in house.due
    assert house.owns


def test_a_household_that_cannot_pay_at_baseline_is_kept_and_counted() -> None:
    """A1's constructor raised here. A1b reports, because the record is real
    and dropping it would select on the outcome the stage is about."""
    houses = build_from_records(
        [record(income_monthly=500.0), record(weight=100.0, group=1)], 1_000
    )
    stress = baseline_stress(houses)
    assert stress["stressed"] > 0
    assert stress["share"] == pytest.approx(0.5, abs=0.01)
    assert stress["by_group"][0] > 0 and stress["by_group"][1] == 0


def test_the_reporting_group_is_the_stratum_with_records() -> None:
    """No cells, so the model needs no group map."""
    houses = build_from_records(
        [record(group=0), record(group=3, weight=100.0)], 100
    )
    model = CascadeModel(houses, CostRule())
    assert model.n_groups == 4
    assert model.groups is None


def test_records_carry_no_seed_and_no_dispersion() -> None:
    """The Beta draw existed because a group mean needed a spread invented.
    The spread is now the file's, so A1b has neither."""
    import inspect

    source = inspect.getsource(build_from_records)
    for absent in ("_beta", "random", "dispersion", "seed"):
        assert absent not in source, absent


def test_the_record_map_lines_up_with_the_population() -> None:
    """A mapping and not an estimate. If ``build_from_records`` ever changed its
    loop order this would go red rather than quietly mis-attributing."""
    records = [record(group=0, weight=100.0),
               record(group=2, weight=40.0, tenure=Tenure.OUTRIGHT,
                      rent_monthly=0.0),
               record(group=3, weight=7.0, income_monthly=9_999.0)]
    built = build_from_records(records, 500)
    owner = record_of_each(records, 500)
    assert len(owner) == len(built)
    for house, index in zip(built, owner, strict=True):
        assert house.stratum == records[index].group
        assert house.tenure is records[index].tenure
        assert house.income == records[index].income_monthly


def test_the_record_map_skips_a_record_that_got_no_copy() -> None:
    records = [record(weight=1_000.0), record(weight=0.4, group=1)]
    assert set(record_of_each(records, 10)) == {0}


# ---------------------------------------------------------------------------
# A1d's cushion: measured liquid assets, no floor
# ---------------------------------------------------------------------------
def test_the_default_cushion_is_still_a1bs_and_its_record_reproduces() -> None:
    """The reason ``Cushion`` has two members rather than one replacement."""
    house = build_from_records([record(liquid=999_999.0)], 1)[0]
    assert house.buffer == pytest.approx(sum(house.due.values()))
    assert house.buffer != pytest.approx(999_999.0)


def test_a_measured_cushion_is_the_records_liquid_assets() -> None:
    house = build_from_records([record(liquid=4_321.0)], 1,
                               cushion=Cushion.MEASURED)[0]
    assert house.buffer == pytest.approx(4_321.0)


def test_a_measured_cushion_has_no_floor() -> None:
    """docs/a1d_prereg.md section 3. A household reporting nothing starts with
    nothing, and this is the clause that makes the bottom more fragile."""
    houses = build_from_records(
        [record(liquid=0.0), record(liquid=5_000.0, group=1, weight=100.0)],
        2, cushion=Cushion.MEASURED,
    )
    assert min(h.buffer for h in houses) == 0.0


def test_buffer_months_beside_a_measured_cushion_is_refused() -> None:
    """Silently ignoring it would leave a free parameter the count cannot see."""
    with pytest.raises(AllocationProblem):
        build_from_records([record(liquid=100.0)], 1, buffer_months=1.0,
                           cushion=Cushion.MEASURED)


def test_a_population_with_no_liquid_assets_anywhere_is_refused() -> None:
    """The shape a column read under the wrong name makes."""
    with pytest.raises(AllocationProblem):
        build_from_records([record(liquid=0.0)], 1, cushion=Cushion.MEASURED)


def test_moving_the_liquid_column_moves_the_cushion() -> None:
    """Item 8: the guard above would pass on a record whose liquid assets were
    read and then discarded, so this asserts the value arrives."""
    small = build_from_records([record(liquid=10.0)], 1,
                               cushion=Cushion.MEASURED)[0]
    large = build_from_records([record(liquid=10_000.0)], 1,
                               cushion=Cushion.MEASURED)[0]
    assert large.buffer > small.buffer


# ---------------------------------------------------------------------------
# A1d's window: sixty days, first and last
# ---------------------------------------------------------------------------
def test_one_missed_payment_is_not_sixty_days() -> None:
    house = bare_household({Obligation.CARD: 100.0}, buffer=0.0)
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert house.ever_missed[Obligation.CARD]
    assert Obligation.CARD not in house.first_sixty


def test_two_consecutive_misses_are_sixty_days() -> None:
    """The same one-month-per-period convention ``persistence`` uses for 90."""
    house = bare_household({Obligation.CARD: 100.0}, buffer=0.0)
    model = CascadeModel([house], CostRule())
    model.step(0, (1.0,))
    model.step(1, (1.0,))
    assert house.first_sixty[Obligation.CARD] == 1
    assert house.last_sixty[Obligation.CARD] == 1


def test_the_two_ends_span_a_household_that_cleared_and_fell_again() -> None:
    """Why two integers and not one flag: a window test asks *when*, and a
    household behind at t=1 and again at t=9 is inside a late window and
    outside an early one."""
    house = bare_household({Obligation.CARD: 100.0}, buffer=0.0, income=0.0)
    model = CascadeModel([house], CostRule())
    model.step(0, (1.0,))
    model.step(1, (1.0,))
    # Hand it enough to clear the arrears, then take the income away again.
    house.buffer = 10_000.0
    model.step(2, (1.0,))
    assert house.missed[Obligation.CARD] == 0, "the arrears cleared"
    house.buffer = 0.0
    for period in (3, 4):
        model.step(period, (1.0,))
    assert house.first_sixty[Obligation.CARD] == 1, "the first spell"
    assert house.last_sixty[Obligation.CARD] == 4, "the second"


def test_the_sixty_day_threshold_is_registered_and_not_the_ninety() -> None:
    spec = CascadeSpec()
    assert spec.sixty_day_misses == 2
    assert spec.persistence == 3


def test_a_household_never_behind_records_neither_end() -> None:
    house = bare_household({Obligation.CARD: 100.0}, buffer=1_000.0)
    CascadeModel([house], CostRule()).step(0, (1.0,))
    assert house.first_sixty == {} and house.last_sixty == {}


def test_a_household_is_not_short_by_a_summation_order() -> None:
    """The defect A1b's zero calibration found, as a guard.

    The constructor totals a household's dues in the order it built them and
    ``step`` totals them in the order of ``Obligation``. Floating-point addition
    is not associative, so the two differ in the last bit, and a household whose
    buffer is exactly its scheduled obligations was judged short by 2e-13
    dollars and defaulted with no shock at all.
    """
    house = bare_household(
        {Obligation.CARD: 1.0 / 3.0, Obligation.RENT: 1_000.0 / 3.0,
         Obligation.BASKET: 100.0 / 3.0},
        buffer=0.0,
    )
    # Built the way the record constructor builds it: card, basket, rent.
    house.buffer = (house.due[Obligation.CARD] + house.due[Obligation.BASKET]
                    + house.due[Obligation.RENT])
    house.income = house.buffer
    step_order = sum(house.due[k] for k in Obligation if k in house.due)
    assert step_order != house.buffer, (
        "this fixture must sit on the knife edge or it tests nothing"
    )
    model = CascadeModel([house], CostRule())
    result = model.run(flat_path(12, n_strata=1))
    for kind in Obligation:
        assert result.delinquent_share[kind.value] == [0.0] * 12, kind


def test_the_tolerance_is_half_a_cent_and_not_a_free_hand() -> None:
    """A shortfall of a dollar is still a shortfall."""
    house = bare_household({Obligation.CARD: 100.0}, buffer=99.0, income=0.0)
    model = CascadeModel([house], CostRule())
    result = model.run(flat_path(6, n_strata=1))
    assert result.delinquent_share["CARD"][-1] == 1.0
    assert SHORTFALL_TOLERANCE == 0.005
