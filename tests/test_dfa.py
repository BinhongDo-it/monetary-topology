"""Tests for the DFA reader and the Z.1 ratio, on synthetic archives, no network.

What these guard is the one failure this input can produce silently: a group
whose column was mis-selected or whose series did not resolve leaves a hole, the
other three absorb it, and four numbers that look like shares come out. Every
check below exists to turn that into an exception.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from monetary_topology.dfa import (
    NET_WORTH_ANCHOR_2026Q1,
    AnchorProblem,
    Selection,
    SelectionProblem,
    ShareSumProblem,
    format_inventory,
    inventory,
    mortgage_to_consumer_credit,
    normalise,
    read_fred_csv,
    read_instrument,
    shares_at,
    validate,
)

DATE = "2026:Q1"
# Percentages, as the publisher writes them, and in the publisher's own
# categories: the top 1% arrives as two rows.
NET_WORTH = {"Bottom50": 2.5, "Next40": 29.6, "Next9": 36.3,
             "RemainingTop1": 17.2, "TopPt1": 14.4}
CONSUMER_CREDIT = {"Bottom50": 51.8, "Next40": 34.9, "Next9": 10.1,
                   "RemainingTop1": 2.2, "TopPt1": 1.1}
MORTGAGES = {"Bottom50": 22.5, "Next40": 49.0, "Next9": 24.4,
             "RemainingTop1": 3.2, "TopPt1": 0.9}
CATEGORIES = ("Bottom50", "Next40", "Next9", "RemainingTop1", "TopPt1")
GROUP_CATEGORIES = {
    "bottom50": ["Bottom50"],
    "next40": ["Next40"],
    "next9": ["Next9"],
    "top1": ["RemainingTop1", "TopPt1"],
}
MEMBER = "dfa-networth-shares.csv"


def write_archive(
    path: Path,
    net_worth: dict[str, float] | None = None,
    consumer_credit: dict[str, float] | None = None,
    mortgages: dict[str, float] | None = None,
    categories: tuple[str, ...] = CATEGORIES,
    extra_member: str | None = None,
) -> Path:
    net_worth = NET_WORTH if net_worth is None else net_worth
    consumer_credit = CONSUMER_CREDIT if consumer_credit is None else consumer_credit
    mortgages = MORTGAGES if mortgages is None else mortgages

    lines = ["Date,Category,Net worth,Home mortgages,Consumer credit"]
    for date in ("2025:Q4", DATE):
        for category in categories:
            nudge = 0.0 if date == DATE else -0.1
            lines.append(
                f"{date},{category},{net_worth[category] + nudge:.4f},"
                f"{mortgages[category] + nudge:.4f},"
                f"{consumer_credit[category] + nudge:.4f}"
            )
    body = "\n".join(lines) + "\n"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(MEMBER, body)
        z.writestr("dfa-age-shares.csv", body)
        z.writestr("readme.txt", "not a csv, and must be ignored")
        if extra_member:
            z.writestr(extra_member, "Date,Category\n2026:Q1,Bottom50\n")
    return path


def write_selection(path: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "vintage": "2026Q1",
        "source": "test",
        "date": DATE,
        "member": MEMBER,
        "date_column": "Date",
        "category_column": "Category",
        "groups": {k: list(v) for k, v in GROUP_CATEGORIES.items()},
        "value_column": {
            "net_worth": "Net worth",
            "home_mortgages": "Home mortgages",
            "consumer_credit": "Consumer credit",
        },
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def setup(tmp_path: Path, **archive_kwargs) -> tuple[Path, Selection, Path]:
    archive = write_archive(tmp_path / "dfa.zip", **archive_kwargs)
    sel_path = write_selection(tmp_path / "dfa_series.json")
    return archive, Selection.load(sel_path), sel_path


# ---------------------------------------------------------------------------
# Discovery replaces guessing
# ---------------------------------------------------------------------------
def test_the_inventory_lists_every_csv_and_ignores_the_rest(
    tmp_path: Path,
) -> None:
    archive = write_archive(tmp_path / "dfa.zip", extra_member="notes/extra.csv")
    members = inventory(archive)
    names = [m.name for m in members]
    assert "readme.txt" not in names
    assert "notes/extra.csv" in names
    assert len(names) == 3
    body = format_inventory(members)
    assert MEMBER in body
    assert "Bottom50" in body


def test_the_inventory_reports_row_counts_and_a_sample(tmp_path: Path) -> None:
    archive = write_archive(tmp_path / "dfa.zip")
    member = next(m for m in inventory(archive) if "networth" in m.name)
    assert member.n_rows == 2 * len(CATEGORIES)
    assert member.header[:2] == ("Date", "Category")
    assert member.first_rows[0][0] == "2025:Q4"


# ---------------------------------------------------------------------------
# Reading under a pinned selection
# ---------------------------------------------------------------------------
def test_an_instrument_reads_as_a_group_vector(tmp_path: Path) -> None:
    archive, selection, _ = setup(tmp_path)
    series = read_instrument(archive, selection, "consumer_credit")
    assert series[DATE] == pytest.approx((51.8, 34.9, 10.1, 3.3))


def test_the_top_one_percent_is_the_sum_of_two_published_categories(
    tmp_path: Path,
) -> None:
    """Reading TopPt1 alone would silently drop nine tenths of the group."""
    archive, selection, _ = setup(tmp_path)
    top1 = read_instrument(archive, selection, "net_worth")[DATE][3]
    assert top1 == pytest.approx(NET_WORTH["TopPt1"] + NET_WORTH["RemainingTop1"])
    assert top1 == pytest.approx(31.6)


def test_a_category_absent_at_that_date_is_refused(tmp_path: Path) -> None:
    archive = write_archive(
        tmp_path / "dfa.zip",
        categories=("Bottom50", "Next40", "Next9", "RemainingTop1"),
    )
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(SelectionProblem) as caught:
        read_instrument(archive, selection, "net_worth")
    assert "TopPt1" in str(caught.value)


def test_percentages_become_fractions_and_fractions_are_left_alone() -> None:
    assert normalise((51.8, 34.9, 10.1, 3.3)) == pytest.approx(
        (0.518, 0.349, 0.101, 0.033)
    )
    already = (0.518, 0.340, 0.110, 0.032)
    assert normalise(already) == pytest.approx(already)


def test_shares_at_a_date_are_fractions(tmp_path: Path) -> None:
    archive, selection, _ = setup(tmp_path)
    vector = shares_at(archive, selection, "home_mortgages", DATE)
    assert sum(vector) == pytest.approx(1.0)
    assert vector[0] == pytest.approx(0.225)


def test_a_missing_date_names_the_dates_that_exist(tmp_path: Path) -> None:
    archive, selection, _ = setup(tmp_path)
    with pytest.raises(SelectionProblem) as caught:
        shares_at(archive, selection, "net_worth", "2099:Q4")
    assert DATE in str(caught.value)


# ---------------------------------------------------------------------------
# The hole a mis-selection leaves
# ---------------------------------------------------------------------------
def test_a_missing_group_is_refused_rather_than_absorbed(tmp_path: Path) -> None:
    """The whole point: three groups summing to less than one must not pass."""
    holed = dict(CONSUMER_CREDIT)
    holed["Next40"] = 0.0
    archive, selection, _ = setup(tmp_path, consumer_credit=holed)
    with pytest.raises(ShareSumProblem):
        shares_at(archive, selection, "consumer_credit", DATE)


def test_a_vector_summing_to_more_than_one_is_refused(tmp_path: Path) -> None:
    doubled = dict(MORTGAGES)
    doubled["Next9"] = 44.4
    archive, selection, _ = setup(tmp_path, mortgages=doubled)
    with pytest.raises(ShareSumProblem):
        shares_at(archive, selection, "home_mortgages", DATE)


def test_published_rounding_is_tolerated_and_a_group_sized_hole_is_not() -> None:
    """Four shares rounded to a tenth of a percent can miss the total by two
    tenths. The tolerance admits that and refuses anything the size of a group.

    The assertions are on the returned value rather than on its distance from
    one, because a test written as ``sum(...) == approx(1.0, rel=1e-3)`` sits
    exactly on its own tolerance and passes or fails on the last bit."""
    assert sum(normalise((51.8, 34.1, 11.0, 3.2))) == pytest.approx(1.001)
    assert sum(normalise((51.7, 33.9, 11.0, 3.2))) == pytest.approx(0.998)
    with pytest.raises(ShareSumProblem):
        normalise((51.8, 34.0, 11.0, 4.0))


def test_a_column_that_is_not_in_the_member_names_the_header(
    tmp_path: Path,
) -> None:
    archive = write_archive(tmp_path / "dfa.zip")
    sel = write_selection(
        tmp_path / "sel.json",
        value_column={
            "net_worth": "Net worth",
            "home_mortgages": "Home mortgages",
            "consumer_credit": "NotAColumn",
        },
    )
    with pytest.raises(SelectionProblem) as caught:
        read_instrument(archive, Selection.load(sel), "consumer_credit")
    assert "Net worth" in str(caught.value)


def test_a_member_that_is_not_in_the_archive_is_refused(tmp_path: Path) -> None:
    archive = write_archive(tmp_path / "dfa.zip")
    sel = write_selection(tmp_path / "sel.json", member="gone.csv")
    with pytest.raises(SelectionProblem):
        read_instrument(archive, Selection.load(sel), "consumer_credit")


def test_a_selection_missing_a_group_fails_at_load(tmp_path: Path) -> None:
    partial = {k: list(v) for k, v in GROUP_CATEGORIES.items() if k != "next9"}
    sel = write_selection(tmp_path / "sel.json", groups=partial)
    with pytest.raises(SelectionProblem):
        Selection.load(sel)


def test_a_selection_with_an_empty_group_fails_at_load(tmp_path: Path) -> None:
    empty = {k: list(v) for k, v in GROUP_CATEGORIES.items()}
    empty["top1"] = []
    sel = write_selection(tmp_path / "sel.json", groups=empty)
    with pytest.raises(SelectionProblem):
        Selection.load(sel)


def test_a_selection_missing_an_instrument_fails_at_load(tmp_path: Path) -> None:
    sel = write_selection(
        tmp_path / "sel.json",
        value_column={"net_worth": "Net worth", "home_mortgages": "Home mortgages"},
    )
    with pytest.raises(SelectionProblem):
        Selection.load(sel)


# ---------------------------------------------------------------------------
# The anchor: a selection that reads cleanly can still be the wrong columns
# ---------------------------------------------------------------------------
def test_validate_checks_net_worth_against_the_vector_a0_already_carries(
    tmp_path: Path,
) -> None:
    archive, selection, _ = setup(tmp_path)
    out = validate(archive, selection, DATE)
    assert out["net_worth"] == pytest.approx(NET_WORTH_ANCHOR_2026Q1)
    assert set(out) == {"consumer_credit", "home_mortgages", "net_worth"}


def test_a_selection_that_sums_to_one_but_is_the_wrong_columns_is_caught(
    tmp_path: Path,
) -> None:
    """Reversed groups still sum to one. Only the anchor separates them."""
    reversed_groups = dict(
        zip(CATEGORIES, [NET_WORTH[c] for c in reversed(CATEGORIES)])
    )
    archive, selection, _ = setup(tmp_path, net_worth=reversed_groups)
    with pytest.raises(AnchorProblem):
        validate(archive, selection, DATE)


# ---------------------------------------------------------------------------
# The Z.1 ratio
# ---------------------------------------------------------------------------
FRED_HM = "observation_date,HMLBSHNO\n2025-10-01,13700000\n2026-01-01,13820984\n"
FRED_CC = "observation_date,CCLBSHNO\n2025-10-01,5000000\n2026-01-01,5073031\n"


def test_a_fred_payload_parses_and_skips_missing_observations() -> None:
    series = read_fred_csv(
        "observation_date,X\n2026-01-01,1.5\n2026-04-01,.\n2026-07-01,\n"
    )
    assert series == {"2026-01-01": 1.5}


def test_an_empty_fred_payload_is_refused() -> None:
    with pytest.raises(ValueError):
        read_fred_csv("observation_date,X\n")


def test_the_ratio_is_two_named_instruments_at_one_quarter() -> None:
    hm = read_fred_csv(FRED_HM)
    cc = read_fred_csv(FRED_CC)
    ratio = mortgage_to_consumer_credit(hm, cc, "2026-01-01")
    assert ratio == pytest.approx(13820984 / 5073031)
    assert ratio == pytest.approx(2.7244, abs=1e-3)


def test_the_seasonally_adjusted_twin_is_caught_by_the_anchor() -> None:
    """HHMSDODNS carries the same title and a different value."""
    adjusted = read_fred_csv(
        "observation_date,HHMSDODNS\n2026-01-01,13852982\n"
    )
    cc = read_fred_csv("observation_date,HCCSDODNS\n2026-01-01,5132355\n")
    with pytest.raises(AnchorProblem):
        mortgage_to_consumer_credit(adjusted, cc, "2026-01-01")


def test_a_quarter_that_is_absent_names_the_quarters_present() -> None:
    hm = read_fred_csv(FRED_HM)
    cc = read_fred_csv(FRED_CC)
    with pytest.raises(AnchorProblem) as caught:
        mortgage_to_consumer_credit(hm, cc, "2030-01-01")
    assert "2026-01-01" in str(caught.value)


def test_the_anchor_can_be_switched_off_for_another_vintage() -> None:
    hm = read_fred_csv(FRED_HM)
    cc = read_fred_csv(FRED_CC)
    ratio = mortgage_to_consumer_credit(hm, cc, "2025-10-01", anchor=None)
    assert ratio == pytest.approx(13700000 / 5000000)


def test_zip_reading_does_not_depend_on_a_byte_order_mark(
    tmp_path: Path,
) -> None:
    plain = write_archive(tmp_path / "plain.zip")
    with zipfile.ZipFile(plain) as z:
        body = z.read(MEMBER).decode("utf-8")
    marked = tmp_path / "marked.zip"
    with zipfile.ZipFile(marked, "w") as z:
        z.writestr(MEMBER, io.BytesIO(body.encode("utf-8-sig")).getvalue())
    sel = Selection.load(write_selection(tmp_path / "sel.json"))
    assert shares_at(marked, sel, "net_worth", DATE) == pytest.approx(
        NET_WORTH_ANCHOR_2026Q1
    )
