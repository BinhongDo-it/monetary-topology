"""What A1b reads before a run, and the payment carriers it sets beside each other.

A run removes the shelter rung of every household it displaces. Three things the
stage reports depend on reading the population first: who was short at
baseline, how many households carried each rung, and which tenure a displaced
household started in. The carrier arms replace one leg's payment and must leave
every other figure of the record alone.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from monetary_topology.cascade import (  # noqa: E402
    CascadeModel,
    CostRule,
    HouseholdRecord,
    Obligation,
    PAYMENT_RATE,
    Tenure,
    build_from_records,
)
from experiments.a1b_default_cascade import (  # noqa: E402
    ARM_CARD,
    ARM_PRIMARY,
    ARM_VEHICLE,
    CARD_PUBLISHER_RATE,
    EXPECTED_EVENT_FLOOR,
    IMPLICATES,
    OTHER_PROPERTY,
    PRIMARY_MORTGAGE,
    VEHICLE_PAYMENTS,
    carrier_arms,
    carrier_reading,
    displaced_by_tenure,
    first_default_shares_by_tenure,
    gradient_verdict,
    payment_coverage,
    starting_state,
)


def record(**overrides) -> HouseholdRecord:
    base = dict(weight=1.0, group=0, income_group=0, income_monthly=3_000.0,
                basket_monthly=800.0, tenure=Tenure.RENTER, rent_monthly=1_000.0,
                mortgage_payment_monthly=0.0, mortgage_balance=0.0,
                card_balance=4_000.0, card_payment_monthly=150.0,
                vehicle_balance=6_000.0)
    base.update(overrides)
    return HouseholdRecord(**base)


def person(**extra):
    base = dict.fromkeys((*PRIMARY_MORTGAGE, *VEHICLE_PAYMENTS, "BNPL"), 0.0)
    base.update(extra)
    return SimpleNamespace(extra=base)


def test_the_population_is_read_before_the_run_removes_a_rung() -> None:
    """A renter with no income is displaced inside the run. Afterwards its rent
    rung is gone and its bills are below what they were, so both the carrier
    count and the short flag have to be the ones taken at the start."""
    cost = CostRule()
    broke = record(income_monthly=0.0)
    fine = record(income_monthly=9_000.0)
    households = build_from_records([broke, fine, fine], 3, cost)
    start = starting_state(households)
    assert start["short"] == [True, False, False]
    assert start["carriers"]["RENTER"]["RENT"] == 3
    assert start["tenure"] == {"MORTGAGED": 0, "OUTRIGHT": 0, "RENTER": 3}

    result = CascadeModel(households, cost).run([(1.0,)] * 24)
    moved = displaced_by_tenure(households)
    assert moved == {"MORTGAGED": 0, "OUTRIGHT": 0, "RENTER": 1}
    # what the run left: the displaced renter no longer carries rent
    after = starting_state(households)
    assert after["carriers"]["RENTER"]["RENT"] == 2
    assert result.exposure_by_tenure["RENTER"]["RENT"] == 2

    rows = first_default_shares_by_tenure(result, start["carriers"])
    renter = rows["RENTER"]
    assert renter["carriers_at_start_rent"] == 3
    assert renter["exposed_rent"] == 2
    first_rent = round(renter["share_rent"] * renter["defaulting_households"])
    assert renter["per_carrier_at_start_rent"] == first_rent / 3
    assert renter["per_exposed_rent"] == first_rent / 2


def test_the_start_rate_is_absent_when_no_start_is_given() -> None:
    result = SimpleNamespace(
        first_default_counts_by_tenure={"RENTER": {k.value: 0 for k in Obligation}
                                        | {"RENT": 3}},
        exposure_by_tenure={"RENTER": {"RENT": 2}})
    row = first_default_shares_by_tenure(result)["RENTER"]
    assert row["per_exposed_rent"] == 1.5
    assert "per_carrier_at_start_rent" not in row
    row = first_default_shares_by_tenure(result, {"RENTER": {"RENT": 6}})["RENTER"]
    assert row["per_carrier_at_start_rent"] == 0.5
    assert row["per_carrier_at_start_card"] is None


def test_each_carrier_arm_changes_one_payment_and_nothing_else() -> None:
    owner = record(tenure=Tenure.MORTGAGED, rent_monthly=0.0,
                   mortgage_payment_monthly=2_000.0, mortgage_balance=300_000.0)
    renter = record()
    people = [person(PAYMORT1=1_200.0, PAYMORT2=300.0, PAYVEH1=250.0, PAYVEO1=80.0),
              person(PAYMORT1=999.0, PAYVEH2=410.0)]
    arms = carrier_arms(people, [owner, renter])
    assert set(arms) == {ARM_PRIMARY, ARM_CARD, ARM_VEHICLE}

    primary = arms[ARM_PRIMARY]
    assert primary[0].mortgage_payment_monthly == 1_500.0
    # a renter has no mortgage rung, whatever the file carries in that column
    assert primary[1].mortgage_payment_monthly == 0.0
    assert primary[0].card_payment_monthly == owner.card_payment_monthly
    assert primary[0].vehicle_payment_monthly == owner.vehicle_payment_monthly

    card = arms[ARM_CARD]
    assert card[0].card_payment_monthly == CARD_PUBLISHER_RATE * 4_000.0 == 100.0
    assert card[0].mortgage_payment_monthly == 2_000.0

    vehicle = arms[ARM_VEHICLE]
    assert vehicle[0].vehicle_payment_monthly == 330.0
    assert vehicle[1].vehicle_payment_monthly == 410.0
    assert owner.vehicle_payment_monthly == 6_000.0 * PAYMENT_RATE[Obligation.AUTO]
    assert vehicle[0].card_payment_monthly == 150.0
    assert vehicle[0].mortgage_payment_monthly == 2_000.0

    # the built household follows: the vehicle due is the published one, and the
    # scheduled cushion is one month of the bills as that arm has them
    cost = CostRule()
    built = build_from_records([vehicle[1]], 1, cost)[0]
    assert built.due[Obligation.AUTO] == 410.0
    assert built.buffer == sum(built.due.values())
    plain = build_from_records([renter], 1, cost)[0]
    assert plain.due[Obligation.AUTO] == 100.0
    assert built.buffer - plain.buffer == 310.0


def test_no_arm_is_built_when_the_file_lacks_the_components() -> None:
    assert carrier_arms([SimpleNamespace(extra={})], [record()]) == {}
    assert payment_coverage([SimpleNamespace(extra={})]) == {}


def test_the_coverage_of_each_payment_column_is_counted() -> None:
    def resp(**kw):
        base = dict(weight=1.0, owns=False, mortgaged=False, card=0.0, vehicle=0.0,
                    card_payment=0.0, mortgage_payment=0.0,
                    extra=dict.fromkeys((*PRIMARY_MORTGAGE, *OTHER_PROPERTY,
                                         *VEHICLE_PAYMENTS, "BNPL"), 0.0))
        extra = kw.pop("extra", {})
        base.update(kw)
        base["extra"] = base["extra"] | extra
        return SimpleNamespace(**base)

    people = [
        # a mortgage on the home and a payment on a second property
        resp(owns=True, mortgaged=True, mortgage_payment=2_500.0,
             extra={"PAYMORT1": 1_500.0, "PAYORE1": 1_000.0}),
        resp(owns=True, mortgaged=True, mortgage_payment=1_000.0,
             extra={"PAYMORT1": 1_000.0}),
        resp(owns=True, mortgaged=True, mortgage_payment=500.0,
             extra={"PAYMORT2": 500.0}),
        # a land contract, and a home-equity line on the home beside it
        resp(owns=True, mortgaged=True, mortgage_payment=700.0,
             extra={"PAYMORT1": 400.0, "PAYLC1": 200.0}),
        # the home-equity line on the home and nothing else beyond the loans
        resp(owns=True, mortgaged=True, mortgage_payment=900.0,
             extra={"PAYMORT1": 600.0}),
        # a card and a buy-now-pay-later balance: 0.025 * 4000 + 0.33 * 300
        resp(card=4_000.0, card_payment=199.0, extra={"BNPL": 300.0}),
        # a card and nothing else: the payment is the card rate
        resp(card=2_000.0, card_payment=50.0),
        # a revolving payment and no card balance
        resp(card_payment=50.0),
        # a vehicle whose published payment is not a sixtieth of its balance
        resp(vehicle=6_000.0, extra={"PAYVEH1": 250.0}),
        # a published vehicle payment and no vehicle balance: no rung is built
        resp(extra={"PAYVEH2": 260.0}),
    ]
    copies = [1] * len(people)
    copies[-1] = 3
    got = payment_coverage(people, copies)
    assert got["mortgage"]["rows_mortgaged"] == 5
    assert got["mortgage"]["rows_paying_beyond_the_NH_MORT_loans"] == 3
    assert got["mortgage"]["rows_with_other_property_or_land_contract_payments"] == 2
    assert got["mortgage"][
        "rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans"] == 1
    assert got["mortgage"]["mean_MORTPAY"] == 5_600.0 / 5
    assert got["mortgage"]["mean_nh_mort_loans"] == 4_000.0 / 5
    assert got["mortgage"]["mean_other_property_and_land_contracts"] == 1_200.0 / 5
    assert got["mortgage"]["mean_primary_residence_home_equity_line"] == 400.0 / 5
    assert got["card"]["rows_with_a_card_balance"] == 2
    assert got["card"]["rows_with_more_than_the_card_rate"] == 1
    assert got["card"]["mean_card_at_the_publisher_rate"] == 75.0
    assert got["card"]["mean_bnpl_at_the_publisher_rate"] == 49.5
    assert got["card"]["rows_with_a_revolving_payment_and_no_card_balance"] == 1
    assert got["vehicle"]["rows_with_a_vehicle_balance"] == 1
    # counted on the rows with a balance; the unheld payment is counted apart
    assert got["vehicle"]["rows_with_a_vehicle_balance_where_the_two_differ"] == 1
    assert got["vehicle"][
        "rows_with_a_published_vehicle_payment_and_no_vehicle_balance"] == 1
    assert got["vehicle"][
        "copies_with_a_published_vehicle_payment_and_no_vehicle_balance"] == 3
    assert ("copies_with_a_published_vehicle_payment_and_no_vehicle_balance"
            not in payment_coverage(people)["vehicle"])
    assert got["vehicle"]["mean_published_holders"] == 250.0
    assert got["vehicle"]["mean_sixtieth_holders"] == 100.0


def test_a_carrier_reading_is_the_last_period_of_the_three_loan_rungs() -> None:
    result = SimpleNamespace(
        delinquent_share={"CARD": [0.0, 0.2], "AUTO": [0.0, 0.1],
                          "MORTGAGE": [0.0, 0.01], "RENT": [0.0, 0.5],
                          "BASKET": [0.0, 0.3]},
        defaulting_households=7)
    got = carrier_reading(result)
    assert got["final"] == {"CARD": 0.2, "AUTO": 0.1, "MORTGAGE": 0.01}
    assert got["k_shape"] is True
    result.delinquent_share["AUTO"][-1] = 0.3
    assert carrier_reading(result)["k_shape"] is False

# ---------------------------------------------------------------------------
# A1b-1 on the pairs both sides resolve
# ---------------------------------------------------------------------------
#: The survey's net-worth cut as the 2022 extract gives it, rates and family
#: equivalents, and the group sizes of a 50,000 and a 20,000 population.
SURVEY = ((0.0847, 0.0163, 0.0022, 0.0026), (1856.6, 1474.6, 694.4, 569.4))
SIZES_50K = [25_310, 20_078, 4_322, 290]
SIZES_20K = [9_993, 7_998, 1_895, 114]


def survey_target(rate=SURVEY[0], families=SURVEY[1]) -> dict:
    import math

    return {
        "rate": list(rate),
        "family_equivalents": list(families),
        "rows": [round(f * IMPLICATES) for f in families],
        "reporting_rows": [round(p * f * IMPLICATES) for p, f in zip(rate, families)],
        "standard_error": [math.sqrt(p * (1 - p) / f) for p, f in zip(rate, families)],
    }


def sweep_of(model, sizes) -> list[dict]:
    return [{"seed": 7, "months_per_round": 1, "model": list(model),
             "model_with_rent": list(model), "sizes": sizes}]


def test_the_top_pair_is_reported_and_not_scored() -> None:
    """The survey's own top pair is inverted at four basis points; the model may
    order it either way and the verdict does not move."""
    for top in (0.000, 0.020):
        criterion, payload = gradient_verdict(
            survey_target(), sweep_of((0.30, 0.20, 0.017, top), SIZES_50K), 50_000)
        assert criterion.passed and not criterion.void
        assert payload["scored_pairs"] == [0, 1]
        assert payload["pairs"][2]["scored"] is False
        assert not payload["pairs"][2]["source_resolves"]


def test_a_scored_pair_out_of_order_fails() -> None:
    criterion, payload = gradient_verdict(
        survey_target(), sweep_of((0.30, 0.015, 0.017, 0.0), SIZES_50K), 50_000)
    assert not criterion.passed and not criterion.void
    assert payload["cells"][0]["decreasing"] is False


def test_a_size_too_thin_for_a_resolved_pair_is_refused() -> None:
    """At 20,000 the survey resolves next40/next9 and the model would expect 4.2
    events in next9, so the size is refused rather than the pair dropped."""
    criterion, payload = gradient_verdict(
        survey_target(), sweep_of((0.30, 0.20, 0.017, 0.0), SIZES_20K), 20_000)
    assert criterion.void and not criterion.passed
    refused = [r for r in payload["pairs"]
               if r["source_resolves"] and not r["model_resolves"]]
    assert [r["pair"] for r in refused] == ["next40/next9"]
    assert min(refused[0]["expected_events"]) < EXPECTED_EVENT_FLOOR

def test_a_survey_reversed_on_a_scored_pair_is_not_matched() -> None:
    """The direction comes from the theory and the order from the survey. Where
    the survey resolves a pair the other way, a decreasing model cannot match
    it, and the half of the verdict that reads the survey is what says so."""
    rate = (0.0163, 0.0847, 0.0022, 0.0026)
    families = (1474.6, 1856.6, 694.4, 569.4)
    criterion, payload = gradient_verdict(
        survey_target(rate, families),
        sweep_of((0.30, 0.20, 0.017, 0.0), SIZES_50K), 50_000)
    assert payload["cells"][0]["decreasing"] is True
    assert payload["cells"][0]["matches"] is False
    assert not criterion.passed and not criterion.void
