"""What A1d writes for itself: the window, the resolution rule, the relief arm.

`docs/a1d_prereg.md` §6.1 inherits five criteria from A1b **as the same code**,
so they are tested where they live. This file covers the three things A1d does
not inherit, and one claim made in prose that ought not to stay prose: that the
corrected relief arm leaves A1b's population exactly where it was.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from monetary_topology.cascade import (  # noqa: E402
    CostRule,
    Cushion,
    HouseholdRecord,
    Obligation,
    Tenure,
    build_from_records,
)
from experiments.a1b_default_cascade import relieved  # noqa: E402
from experiments.a1d_measured_cushion import (  # noqa: E402
    EXPECTED_EVENT_FLOOR,
    IMPLICATES,
    PAIR_SIGMA,
    _touched,
    behind_in_window,
    ever_missed_by_group,
    free_list,
    scorable_pairs,
)


def record(**overrides) -> HouseholdRecord:
    payload = dict(
        weight=100.0, group=0, income_group=0, income_monthly=3_000.0,
        basket_monthly=1_200.0, tenure=Tenure.RENTER, rent_monthly=900.0,
        mortgage_payment_monthly=0.0, mortgage_balance=0.0,
        card_balance=2_000.0, card_payment_monthly=74.0,
        vehicle_balance=6_000.0, liquid=0.0,
    )
    payload.update(overrides)
    return HouseholdRecord(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The relief arm, corrected 2026-08-16
# ---------------------------------------------------------------------------
def test_the_relief_arm_does_not_move_a_scheduled_cushion() -> None:
    """A1b's record must stay reproducible on this code.

    Its buffer is already ``sum(due.values())``, summed in the same dict order,
    so the new line is ``max(x, x)``. Asserted bit for bit rather than
    approximately, because the defect this whole family of guards exists for was
    a difference of 2e-13.
    """
    before = build_from_records([record(liquid=5.0)], 4)
    after = relieved(before, CostRule())
    for old, new in zip(before, after, strict=True):
        assert new.buffer == old.buffer


def test_the_relief_arm_covers_a_household_with_no_cash() -> None:
    """The A1d-0 defect, as a guard.

    ``income_arrives_after_due`` is Volume One section 4's settlement asymmetry, so a
    household whose income exactly covers its bills and whose cash is zero still
    cannot pay in period 0. Raising the flow alone leaves that cause standing.
    """
    # Two records, because a population reading zero everywhere is refused by
    # the guard that catches a column read under the wrong name.
    built = build_from_records(
        [record(liquid=0.0), record(liquid=9_000.0, group=1, weight=100.0)],
        2, cushion=Cushion.MEASURED,
    )
    house = next(h for h in built if h.buffer == 0.0)
    fixed = relieved([house], CostRule())[0]
    assert fixed.buffer == pytest.approx(sum(house.due.values()))
    assert fixed.income >= sum(house.due.values())


def test_the_relief_arm_does_not_lower_a_cushion_it_finds() -> None:
    """``max`` and not an assignment: relief removes causes, it does not level."""
    house = build_from_records([record(liquid=500_000.0)], 1,
                               cushion=Cushion.MEASURED)[0]
    assert relieved([house], CostRule())[0].buffer == pytest.approx(500_000.0)


# ---------------------------------------------------------------------------
# The window quantity
# ---------------------------------------------------------------------------
def houses(*spells, groups: int = 1) -> list:
    """One household per spell, each spell a ``(first, last)`` on the card."""
    built = build_from_records([record()], len(spells))
    for house, spell in zip(built, spells, strict=True):
        house.stratum = 0
        house.first_sixty = {} if spell is None else {Obligation.CARD: spell[0]}
        house.last_sixty = {} if spell is None else {Obligation.CARD: spell[1]}
        house.ever_missed = {Obligation.CARD: spell is not None}
    return built


CARD = (Obligation.CARD,)


def test_the_whole_run_reading_counts_any_spell() -> None:
    assert behind_in_window(houses((0, 2), None), CARD, 1, None) == [0.5]


def test_a_spell_before_the_window_is_outside_it() -> None:
    """The reading that makes the window a window rather than a rename."""
    assert behind_in_window(houses((0, 3)), CARD, 1, 48) == [0.0]


def test_a_spell_inside_the_window_is_counted() -> None:
    assert behind_in_window(houses((50, 55)), CARD, 1, 48) == [1.0]


def test_a_spell_spanning_the_window_start_is_counted() -> None:
    """``last_sixty >= start`` is the whole test, and this is why it is enough."""
    assert behind_in_window(houses((10, 50)), CARD, 1, 48) == [1.0]


def test_the_early_window_excludes_a_later_spell() -> None:
    assert behind_in_window(houses((50, 55)), CARD, 1, 0, 11) == [0.0]
    assert behind_in_window(houses((3, 5)), CARD, 1, 0, 11) == [1.0]


def test_a_household_never_sixty_days_behind_is_never_counted() -> None:
    assert behind_in_window(houses(None), CARD, 1, None) == [0.0]


def test_the_any_miss_reading_and_the_sixty_day_one_are_different() -> None:
    """A1b-1's quantity beside A1d-1's. If these agreed on this population the
    window correction would be measuring nothing."""
    built = houses(None)
    built[0].ever_missed = {Obligation.CARD: True}
    assert ever_missed_by_group(built, CARD, 1) == [1.0]
    assert behind_in_window(built, CARD, 1, None) == [0.0]


# ---------------------------------------------------------------------------
# The resolution rule
# ---------------------------------------------------------------------------
def target(rate, families) -> dict:
    import math

    return {
        "rate": list(rate),
        "families": list(families),
        "rows": [f * IMPLICATES for f in families],
        "reporting_rows": [round(p * f) for p, f in zip(rate, families)],
        "standard_error": [math.sqrt(p * (1 - p) / f) if f else float("inf")
                           for p, f in zip(rate, families)],
    }


def test_a_well_separated_pair_is_scored() -> None:
    admitted, rows = scorable_pairs(target((0.30, 0.05), (1_500, 1_500)),
                                    [5_000, 5_000])
    assert admitted == [0]
    assert rows[0]["scored"] and rows[0]["sigmas"] > PAIR_SIGMA


def test_a_pair_the_source_cannot_resolve_is_not_scored() -> None:
    """The A1b-1 defect. Eleven households against five, four basis points."""
    admitted, rows = scorable_pairs(target((0.0022, 0.0026), (694, 569)),
                                    [500_000, 500_000])
    assert admitted == []
    assert not rows[0]["source_resolves"]
    assert rows[0]["model_resolves"], "the model side is not what refused it"


def test_a_pair_the_model_cannot_resolve_is_not_scored() -> None:
    """The rule that forces the sweep's size rather than letting it be chosen."""
    admitted, rows = scorable_pairs(target((0.30, 0.05), (1_500, 1_500)),
                                    [5_000, 10])
    assert admitted == []
    assert rows[0]["source_resolves"]
    assert not rows[0]["model_resolves"]
    assert min(rows[0]["expected_events"]) < EXPECTED_EVENT_FLOOR


def test_an_identical_pair_is_never_scored() -> None:
    """Item 8: a rule that admitted a zero gap would admit everything."""
    admitted, _ = scorable_pairs(target((0.10, 0.10), (1_500, 1_500)),
                                 [500_000, 500_000])
    assert admitted == []


def test_the_rule_admits_each_pair_on_its_own_merits() -> None:
    """Three groups, one resolvable pair and one not. Both verdicts, one call."""
    admitted, rows = scorable_pairs(
        target((0.30, 0.05, 0.048), (1_500, 1_500, 1_500)),
        [5_000, 5_000, 5_000],
    )
    assert admitted == [0]
    assert len(rows) == 2 and rows[1]["scored"] is False


def test_the_touched_groups_are_in_order_and_without_repeats() -> None:
    assert _touched([0, 1]) == [0, 1, 2]
    assert _touched([1]) == [1, 2]
    assert _touched([0, 2]) == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# The parameter count
# ---------------------------------------------------------------------------
def test_buffer_months_is_not_in_a1ds_free_list() -> None:
    names = [n for n, _ in free_list(CostRule())]
    assert "population.buffer_months" not in names
    assert len(names) == 4
