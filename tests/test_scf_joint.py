"""The joint reader, and the one anchor A1d adds to it.

``scf_joint.py`` had no tests when ``docs/a1d_prereg.md`` was written. This file
starts with the guard that registration introduces, because a guard nothing
re-runs is `MEASUREMENT.md` failure mode 9 and the cushion is now a mechanism
input rather than a report. The rest of the module's surface is not covered here
and that is a gap, not a claim.
"""
from __future__ import annotations

import pytest

from monetary_topology.scf_joint import (
    JointSelection,
    SelectionProblem,
    extract,
)

COLUMNS = dict(
    wave="2022",
    source="",
    weight_column="WGT",
    networth_column="NETWORTH",
    income_column="INCOME",
    ownership_column="HOUSECL",
    owning_values=("1",),
    mortgage_debt_column="NH_MORT",
    mortgage_payment_column="MORTPAY",
    rent_column="RENT",
    card_column="CCBAL",
    vehicle_column="VEH_INST",
    card_payment_column="REVPAY",
    instalment_payment_column="CONSPAY",
    total_payment_column="TPAY",
)


def selection(**overrides) -> JointSelection:
    payload = dict(COLUMNS)
    payload.setdefault("liquid_column", "LIQ")
    payload.setdefault("extra_columns", ("FIN", "ASSET"))
    payload.update(overrides)
    return JointSelection(**payload)  # type: ignore[arg-type]


def row(**overrides) -> dict[str, str]:
    payload = {
        "WGT": "100", "NETWORTH": "50000", "INCOME": "60000",
        "HOUSECL": "2", "NH_MORT": "0", "MORTPAY": "0", "RENT": "900",
        "CCBAL": "2000", "VEH_INST": "6000", "REVPAY": "74",
        "CONSPAY": "100", "TPAY": "174",
        "LIQ": "3000", "FIN": "20000", "ASSET": "80000",
    }
    payload.update({k: str(v) for k, v in overrides.items()})
    return payload


# ---------------------------------------------------------------------------
# The cushion arrives
# ---------------------------------------------------------------------------
def test_the_liquid_column_reaches_the_respondent() -> None:
    person = extract([row(LIQ=4_321)], selection())[0]
    assert person.liquid == pytest.approx(4_321.0)


def test_moving_the_liquid_column_moves_the_value() -> None:
    """Item 8. A reader that parsed the column and dropped it would pass every
    anchor below, because all of them are satisfied by a constant zero."""
    low = extract([row(LIQ=10)], selection())[0]
    high = extract([row(LIQ=10_000)], selection())[0]
    assert high.liquid > low.liquid


def test_a_selection_naming_no_cushion_still_reads() -> None:
    """A1b was built and scored without this column and must stay reproducible.
    Its records carry a cushion of zero and ``build_from_records`` refuses to
    treat that as a measured population."""
    people = extract([row()], selection(liquid_column="", extra_columns=()))
    assert people[0].liquid == 0.0


# ---------------------------------------------------------------------------
# The nesting anchor, and whether it would notice
# ---------------------------------------------------------------------------
def test_the_nesting_anchor_passes_on_a_well_formed_row() -> None:
    assert extract([row()], selection())


def test_a_negative_cushion_is_refused() -> None:
    with pytest.raises(SelectionProblem) as exc:
        extract([row(LIQ=-1)], selection())
    assert "negative" in str(exc.value)


def test_a_cushion_above_financial_assets_is_refused() -> None:
    """The failure a share column makes: a fraction read as dollars sits below
    every asset total, and a dollar total read as a fraction sits above."""
    with pytest.raises(SelectionProblem) as exc:
        extract([row(LIQ=25_000, FIN=20_000)], selection())
    assert "LIQ above FIN" in str(exc.value)


def test_financial_assets_above_all_assets_are_refused() -> None:
    with pytest.raises(SelectionProblem) as exc:
        extract([row(FIN=90_000, ASSET=80_000)], selection())
    assert "FIN above ASSET" in str(exc.value)


def test_the_anchor_refuses_to_be_skipped_when_its_columns_are_absent() -> None:
    """The failure mode the anchor itself has: naming a cushion and quietly
    not checking it, because the columns that would check it were dropped."""
    with pytest.raises(SelectionProblem) as exc:
        extract([row()], selection(extra_columns=("FIN",)))
    assert "ASSET" in str(exc.value)


def test_the_tolerance_does_not_swallow_a_real_inversion() -> None:
    """One dollar of rounding is allowed and two thousand is not."""
    assert extract([row(LIQ=20_000, FIN=19_999.5)], selection())
    with pytest.raises(SelectionProblem):
        extract([row(LIQ=22_000, FIN=20_000)], selection())


# ---------------------------------------------------------------------------
# The reader's own refusals, which the cushion must not have loosened
# ---------------------------------------------------------------------------
def test_a_column_that_is_not_in_the_extract_is_refused() -> None:
    with pytest.raises(SelectionProblem):
        extract([row()], selection(liquid_column="NOT_A_COLUMN"))


def test_a_row_with_no_weight_is_dropped_rather_than_read() -> None:
    with pytest.raises(SelectionProblem):
        extract([row(WGT=0)], selection())
