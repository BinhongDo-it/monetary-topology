"""Tests for the CEX reader, on synthetic workbooks shaped like the real one.

The published table has three properties that each turn a reading error into a
number rather than an exception, and the fixture reproduces all three:

* an item label sits on its own row and carries no values;
* ``Share`` sits directly under ``Mean`` and is a percentage of total
  expenditure, so a reader taking "the first numeric row" returns percentages;
* the column headers carry embedded newlines.

It also reproduces two decoys the real table has: ``Food``, ``Food at home`` and
``Food away from home`` one under the other, and ``Income before taxes``
appearing twice.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from monetary_topology.cex import (
    CONSUMER_UNIT_BAND,
    GROUPS,
    PUBLISHED_2024,
    AnchorProblem,
    Selection,
    SelectionProblem,
    group_value,
    inventory,
    normalise,
    TENURE_ROLES,
    read_counts,
    read_inputs,
    read_tenure,
    read_table,
)

SHEET = "Table 1110"
#: Written as the publisher writes them, with the line breaks.
HEADERS = (
    "All\nconsumer\nunits",
    "Lowest\n10\npercent",
    "Second\n10\npercent",
    "Third\n10\npercent",
    "Fourth\n10\npercent",
    "Fifth\n10\npercent",
    "Sixth\n10\npercent",
    "Seventh\n10\npercent",
    "Eighth\n10\npercent",
    "Ninth\n10\npercent",
    "Highest\n10\npercent",
)
ALL_UNITS = "All consumer units"
DECILES = tuple(normalise(h) for h in HEADERS[1:])
NECESSITIES = ("Food at home", "Healthcare")
RENT_LABEL = "Rented dwellings"
MORTGAGE_LABELS = ("Mortgage interest and charges",
                   "Mortgage principal paid on owned property")
#: Carries the publisher's footnote marker, as the real table does.
COUNT_LABEL = "Number of consumer units (in thousands) a/"
#: In thousands, as published. Ten deciles near 13,576 each.
COUNT_DECILES = (13_665.0, 13_474.0, 13_580.0, 13_600.0, 13_520.0,
                 13_610.0, 13_590.0, 13_550.0, 13_570.0, 13_601.0)
COUNT_ALL_UNITS = 135_760.0
#: Whole percents, as published. Owner and renter partition the group and
#: the mortgaged are a subset of the owners.
TENURE_LABELS = {"homeowner": "Homeowner", "mortgaged": "With mortgage",
                 "renter": "Renter"}
OWNER_DECILES = (34.0, 51.0, 57.0, 59.0, 60.0, 64.0, 71.0, 77.0, 85.0, 90.0)
MORTGAGED_DECILES = (8.0, 15.0, 19.0, 23.0, 30.0, 36.0, 46.0, 55.0, 65.0, 70.0)
RENTER_DECILES = tuple(100.0 - v for v in OWNER_DECILES)

#: Rising across the deciles, and averaging exactly to the published figure so
#: the internal anchor is exercised rather than approximated.
SHAPE = (0.15, 0.25, 0.36, 0.50, 0.65, 0.82, 1.03, 1.32, 1.78)


def deciles_for(mean: float) -> tuple[float, ...]:
    values = [mean * f for f in SHAPE]
    values.append(mean * 10 - sum(values))
    return tuple(values)


INCOME = deciles_for(PUBLISHED_2024["income_before_taxes"])
EXPENDITURE = deciles_for(PUBLISHED_2024["total_expenditure"])
BASKET_ITEM = deciles_for(5_000.0)


def _col_letters(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def blocks(items=None, drop_decile: str | None = None):
    """``(label, mean values or None, has_share)`` in publication order."""
    if items is None:
        items = {
            "Income before taxes": INCOME,
            "Average annual expenditures": EXPENDITURE,
            "Food": deciles_for(9_000.0),
            "Food at home": BASKET_ITEM,
            "Food away from home": deciles_for(4_000.0),
            "Shelter": deciles_for(16_000.0),
            "Rented dwellings": deciles_for(6_000.0),
            "Mortgage interest and charges": deciles_for(1_300.0),
            "Mortgage principal paid on owned property": deciles_for(2_700.0),
            "Healthcare": deciles_for(6_000.0),
        }
    out = [(label, values, True) for label, values in items.items()]
    # The publisher repeats this label lower down, heading the breakdown by
    # income source. Its numbers differ, so taking the wrong one is visible.
    out.append(("Income before taxes", deciles_for(1.0), False))
    return out


def write_workbook(
    path: Path,
    items=None,
    header_at: int = 2,
    drop_decile: str | None = None,
    omit_mean_for: str | None = None,
    count_all_units: float | None = COUNT_ALL_UNITS,
    count_deciles=COUNT_DECILES,
    omit_count_row: bool = False,
    owner_deciles=OWNER_DECILES,
    mortgaged_deciles=MORTGAGED_DECILES,
    renter_deciles=RENTER_DECILES,
    tenure_all_units: dict[str, float] | None = None,
) -> Path:
    columns = [h for h in HEADERS if normalise(h) != drop_decile]

    rows: list[list[object]] = [
        ["Table 1110. Deciles of income before taxes, Consumer Expenditure "
         "Surveys, 2024"]
    ]
    while len(rows) < header_at:
        rows.append([])
    rows.append(["Item", *columns])

    # The count row, exactly as the publisher lays it out: values on the label
    # row itself, and ``Lower limit`` directly beneath it rather than ``Mean``.
    # That second row is the reason this one needs its own reader, so the
    # fixture carries it.
    if not omit_count_row:
        by_column = dict(zip(DECILES, count_deciles, strict=True))
        kept = [by_column[normalise(c)] for c in columns
                if normalise(c) != ALL_UNITS]
        all_units_cell: object = (
            "n.a." if count_all_units is None else count_all_units
        )
        rows.append([COUNT_LABEL, all_units_cell, *kept])
        rows.append(["Lower limit", "n.a.", *["n.a."] * len(kept)])

    # The three tenure rows, laid out the same way: values on the label row.
    for role, values in (("homeowner", owner_deciles),
                         ("mortgaged", mortgaged_deciles),
                         ("renter", renter_deciles)):
        by_column = dict(zip(DECILES, values, strict=True))
        kept = [by_column[normalise(c)] for c in columns
                if normalise(c) != ALL_UNITS]
        published = (tenure_all_units or {}).get(role,
                                                 sum(values) / len(values))
        rows.append([TENURE_LABELS[role], published, *kept])

    for label, values, has_share in blocks(items):
        by_column = dict(zip(DECILES, values, strict=True))
        kept = [by_column[normalise(c)] for c in columns
                if normalise(c) != ALL_UNITS]
        all_units = sum(values) / len(values)
        rows.append([label])
        if label != omit_mean_for:
            rows.append(["Mean", all_units, *kept])
        if has_share:
            # A percentage of total expenditure, and the trap: it is numeric and
            # it sits where a naive reader would look.
            rows.append(["Share", all_units / 100.0,
                         *[v / 100.0 for v in kept]])
        rows.append(["SE", 1.0, *[1.0] * len(kept)])
        rows.append(["RSE", 0.1, *[0.1] * len(kept)])

    strings: list[str] = []
    index_of: dict[str, int] = {}

    def intern(text: str) -> int:
        if text not in index_of:
            index_of[text] = len(strings)
            strings.append(text)
        return index_of[text]

    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            if value is None or value == "":
                continue
            ref = f"{_col_letters(c)}{r}"
            if isinstance(value, str):
                cells.append(f'<c r="{ref}" t="s"><v>{intern(value)}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{value!r}</v></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')

    escaped = [s.replace("&", "&amp;").replace("<", "&lt;") for s in strings]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook xmlns="http://schemas.'
            'openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{SHEET}" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship '
            'Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.'
            f'org/spreadsheetml/2006/main" count="{len(escaped)}">'
            + "".join(f"<si><t>{s}</t></si>" for s in escaped)
            + "</sst>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet xmlns="http://schemas.'
            'openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + "".join(body)
            + "</sheetData></worksheet>",
        )
    return path


def write_selection(path: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "reference_year": "2024",
        "source": "test",
        "sheet": SHEET,
        "label_column": 0,
        "statistic_label": "Mean",
        "all_units_column": ALL_UNITS,
        "income_label": "Income before taxes",
        "expenditure_label": "Average annual expenditures",
        "necessity_labels": list(NECESSITIES),
        "rent_label": RENT_LABEL,
        "mortgage_labels": list(MORTGAGE_LABELS),
        "consumer_units_label": COUNT_LABEL,
        "tenure_labels": dict(TENURE_LABELS),
        "group_columns": {
            "bottom50": list(DECILES[:5]),
            "next40": list(DECILES[5:9]),
            "next9": [DECILES[9]],
            "top1": [DECILES[9]],
        },
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def setup(tmp_path: Path, **kwargs) -> tuple[Path, Selection]:
    book = write_workbook(tmp_path / "cex.xlsx", **kwargs)
    return book, Selection.load(write_selection(tmp_path / "sel.json"))


# ---------------------------------------------------------------------------
# The three properties of the layout
# ---------------------------------------------------------------------------
def test_the_value_comes_from_the_mean_row_and_not_from_share(
    tmp_path: Path,
) -> None:
    """``Share`` is a percentage and sits where a naive reader would look."""
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    got = table["Food at home"][ALL_UNITS]
    assert got == pytest.approx(sum(BASKET_ITEM) / 10)
    assert got != pytest.approx(sum(BASKET_ITEM) / 1000)


def test_headers_with_embedded_newlines_are_matched(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    assert ALL_UNITS in table[RENT_LABEL]
    assert "Lowest 10 percent" in table[RENT_LABEL]


def test_the_first_occurrence_of_a_repeated_label_wins(tmp_path: Path) -> None:
    """``Income before taxes`` heads the income-source block as well."""
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    assert table["Income before taxes"][ALL_UNITS] == pytest.approx(
        PUBLISHED_2024["income_before_taxes"]
    )


def test_an_item_with_no_mean_row_is_refused(tmp_path: Path) -> None:
    book = write_workbook(tmp_path / "cex.xlsx", omit_mean_for=RENT_LABEL)
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(SelectionProblem) as caught:
        read_table(book, selection)
    assert "Mean" in str(caught.value)


def test_the_header_row_is_found_wherever_it_sits(tmp_path: Path) -> None:
    for height in (1, 2, 6):
        book, selection = setup(tmp_path, header_at=height)
        table = read_table(book, selection)
        assert table[RENT_LABEL][ALL_UNITS] == pytest.approx(6_000.0)


def test_the_layout_dump_shows_the_header_and_the_items(tmp_path: Path) -> None:
    body = inventory(write_workbook(tmp_path / "cex.xlsx"))
    assert SHEET in body
    assert "Income before taxes" in body
    assert "Mean" in body


# ---------------------------------------------------------------------------
# The decoy rows
# ---------------------------------------------------------------------------
def test_a_neighbouring_item_row_is_not_picked_up(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    assert set(table) == {
        "Income before taxes", "Average annual expenditures",
        "Food at home", "Healthcare", RENT_LABEL, *MORTGAGE_LABELS,
    }
    assert table["Food at home"][ALL_UNITS] == pytest.approx(5_000.0)


def test_an_item_label_that_is_absent_is_refused(tmp_path: Path) -> None:
    book = write_workbook(tmp_path / "cex.xlsx")
    sel = Selection.load(
        write_selection(tmp_path / "sel.json",
                        necessity_labels=["Food at home", "Rocket fuel"])
    )
    with pytest.raises(SelectionProblem) as caught:
        read_table(book, sel)
    assert "Rocket fuel" in str(caught.value)


def test_a_sheet_that_is_absent_names_the_sheets_present(tmp_path: Path) -> None:
    book = write_workbook(tmp_path / "cex.xlsx")
    sel = Selection.load(write_selection(tmp_path / "sel.json", sheet="Nope"))
    with pytest.raises(SelectionProblem) as caught:
        read_table(book, sel)
    assert SHEET in str(caught.value)


# ---------------------------------------------------------------------------
# The grouping, which is a ruling rather than a lookup
# ---------------------------------------------------------------------------
def test_a_group_is_the_mean_of_its_decile_columns(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    got = group_value(table, selection, "Income before taxes", "bottom50")
    assert got == pytest.approx(sum(INCOME[:5]) / 5)


def test_the_top_two_groups_read_the_same_column(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    result = read_inputs(book, selection)
    assert result["top_groups_share_a_column"] is True
    assert result["income"]["next9"] == result["income"]["top1"]
    assert result["necessities"]["next9"] == result["necessities"]["top1"]


def test_the_basket_is_the_sum_of_the_named_items(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    result = read_inputs(book, selection)
    expected = sum(
        sum(deciles_for(m)[:5]) / 5 for m in (5_000.0, 6_000.0)
    )
    assert result["necessities"]["bottom50"] == pytest.approx(expected)
    assert result["necessity_labels"] == list(NECESSITIES)


def test_a_selection_missing_a_group_fails_at_load(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem):
        Selection.load(
            write_selection(
                tmp_path / "sel.json",
                group_columns={"bottom50": list(DECILES[:5]),
                               "next40": list(DECILES[5:9])},
            )
        )


def test_a_selection_with_no_basket_fails_at_load(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem):
        Selection.load(
            write_selection(tmp_path / "sel.json", necessity_labels=[])
        )


# ---------------------------------------------------------------------------
# The two anchors
# ---------------------------------------------------------------------------
def test_the_internal_anchor_passes_on_a_consistent_table(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    result = read_inputs(book, selection)
    assert result["decile_mean_income"] == pytest.approx(
        result["all_units_income"]
    )


def test_a_missing_decile_column_is_refused(tmp_path: Path) -> None:
    """Nine columns still average to something; only the all-units row notices."""
    book = write_workbook(tmp_path / "cex.xlsx", drop_decile=DECILES[9])
    sel_path = write_selection(
        tmp_path / "sel.json",
        group_columns={
            "bottom50": list(DECILES[:5]),
            "next40": list(DECILES[5:9]),
            "next9": [DECILES[8]],
            "top1": [DECILES[8]],
        },
    )
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, Selection.load(sel_path))
    assert "all-units" in str(caught.value)


def test_the_external_anchor_fixes_the_vintage(tmp_path: Path) -> None:
    """A table that is internally consistent can still be the wrong year."""
    items = {
        "Income before taxes": deciles_for(83_000.0),
        "Average annual expenditures": EXPENDITURE,
        "Food": deciles_for(9_000.0),
        "Food at home": BASKET_ITEM,
        "Food away from home": deciles_for(4_000.0),
        "Shelter": deciles_for(16_000.0),
        "Rented dwellings": deciles_for(6_000.0),
        "Mortgage interest and charges": deciles_for(1_300.0),
        "Mortgage principal paid on owned property": deciles_for(2_700.0),
        "Healthcare": deciles_for(6_000.0),
    }
    book = write_workbook(tmp_path / "cex.xlsx", items=items)
    sel = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, sel)
    assert "vintage" in str(caught.value)


def test_the_published_pair_is_what_the_external_anchor_uses() -> None:
    assert PUBLISHED_2024["income_before_taxes"] == 104_207.0
    assert PUBLISHED_2024["total_expenditure"] == 78_535.0


def test_anchors_can_be_switched_off_for_another_vintage(tmp_path: Path) -> None:
    items = {
        "Income before taxes": deciles_for(83_000.0),
        "Average annual expenditures": EXPENDITURE,
        "Food": deciles_for(9_000.0),
        "Food at home": BASKET_ITEM,
        "Food away from home": deciles_for(4_000.0),
        "Shelter": deciles_for(16_000.0),
        "Rented dwellings": deciles_for(6_000.0),
        "Mortgage interest and charges": deciles_for(1_300.0),
        "Mortgage principal paid on owned property": deciles_for(2_700.0),
        "Healthcare": deciles_for(6_000.0),
    }
    book = write_workbook(tmp_path / "cex.xlsx", items=items)
    sel = Selection.load(write_selection(tmp_path / "sel.json"))
    result = read_inputs(book, sel, check_anchors=False)
    assert set(result["income"]) == set(GROUPS)


# ---------------------------------------------------------------------------
# Whitespace
# ---------------------------------------------------------------------------
def test_normalise_collapses_the_publishers_line_breaks() -> None:
    assert normalise("All\nconsumer\nunits") == ALL_UNITS
    assert normalise("  Shelter  ") == "Shelter"
    assert normalise(None) == ""
    assert normalise(3.0) == ""


def test_shelter_in_the_basket_is_refused(tmp_path: Path) -> None:
    """Counting it as a necessity charges a household its rent twice."""
    with pytest.raises(SelectionProblem) as caught:
        Selection.load(
            write_selection(tmp_path / "sel.json",
                            necessity_labels=["Food at home", "Shelter"])
        )
    assert "twice" in str(caught.value)


# ---------------------------------------------------------------------------
# The consumer-unit count, which is the one row laid out the other way round
# ---------------------------------------------------------------------------
def test_the_count_is_read_off_the_label_row_and_leaves_the_thousands(
    tmp_path: Path,
) -> None:
    book, selection = setup(tmp_path)
    counts = read_counts(book, selection)
    assert counts[ALL_UNITS] == pytest.approx(COUNT_ALL_UNITS * 1_000.0)
    assert counts["Lowest 10 percent"] == pytest.approx(
        COUNT_DECILES[0] * 1_000.0
    )


def test_the_count_row_is_not_read_through_the_mean_path(tmp_path: Path) -> None:
    """``Lower limit`` sits where ``Mean`` sits for every other item.

    If the count were ever routed through ``_statistic_row`` this is the row it
    would hit, so the fixture carries it and this test names the consequence.
    """
    book, selection = setup(tmp_path)
    table = read_table(book, selection)
    assert COUNT_LABEL not in table
    assert "Lower limit" not in table


def test_a_missing_count_row_is_refused(tmp_path: Path) -> None:
    book = write_workbook(tmp_path / "cex.xlsx", omit_count_row=True)
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(SelectionProblem) as caught:
        read_counts(book, selection)
    assert "per-household" in str(caught.value)


def test_a_count_row_with_no_number_under_all_units_is_refused(
    tmp_path: Path,
) -> None:
    book = write_workbook(tmp_path / "cex.xlsx", count_all_units=None)
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(SelectionProblem) as caught:
        read_counts(book, selection)
    assert "label row" in str(caught.value)


def test_a_count_outside_the_band_is_refused(tmp_path: Path) -> None:
    """The published unit is thousands, and a unit slip is otherwise silent."""
    book = write_workbook(
        tmp_path / "cex.xlsx",
        count_all_units=135.76,
        count_deciles=tuple(v / 1_000.0 for v in COUNT_DECILES),
    )
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, selection)
    assert "thousands" in str(caught.value)


def test_counts_that_do_not_partition_the_population_are_refused(
    tmp_path: Path,
) -> None:
    """Money columns can average correctly while a count column is misplaced."""
    book = write_workbook(
        tmp_path / "cex.xlsx",
        count_deciles=tuple(v * 0.5 for v in COUNT_DECILES),
    )
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, selection)
    assert "partition" in str(caught.value)


def test_the_count_reaches_the_result_in_units(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    result = read_inputs(book, selection)
    low, high = CONSUMER_UNIT_BAND
    assert low <= result["consumer_units"] <= high
    assert result["consumer_units"] == pytest.approx(COUNT_ALL_UNITS * 1_000.0)
    assert len(result["consumer_units_by_decile"]) == 10


def test_a_selection_with_no_count_label_fails_at_load(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem) as caught:
        Selection.load(
            write_selection(tmp_path / "sel.json", consumer_units_label="")
        )
    assert "consumer_units_label" in str(caught.value)


def test_the_shelter_flows_are_read_as_their_own_rungs(tmp_path: Path) -> None:
    book, selection = setup(tmp_path)
    result = read_inputs(book, selection)
    assert result["rent"]["bottom50"] == pytest.approx(
        sum(deciles_for(6_000.0)[:5]) / 5
    )
    assert result["mortgage_payment"]["bottom50"] == pytest.approx(
        sum(deciles_for(1_300.0)[:5]) / 5 + sum(deciles_for(2_700.0)[:5]) / 5
    )


# ---------------------------------------------------------------------------
# The sign convention on the owner's two lines
# ---------------------------------------------------------------------------
def _items_with(principal_sign: float) -> dict:
    return {
        "Income before taxes": INCOME,
        "Average annual expenditures": EXPENDITURE,
        "Food": deciles_for(9_000.0),
        "Food at home": BASKET_ITEM,
        "Food away from home": deciles_for(4_000.0),
        "Shelter": deciles_for(16_000.0),
        "Rented dwellings": deciles_for(6_000.0),
        "Mortgage interest and charges": deciles_for(1_300.0),
        "Mortgage principal paid on owned property": deciles_for(
            principal_sign * 2_700.0
        ),
        "Healthcare": deciles_for(6_000.0),
    }


def test_a_negative_principal_line_is_added_as_cash_handed_over(
    tmp_path: Path,
) -> None:
    """The publisher writes it negative. Added as published, it nets away."""
    book = write_workbook(tmp_path / "cex.xlsx", items=_items_with(-1.0))
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    result = read_inputs(book, selection)
    interest = sum(deciles_for(1_300.0)[:5]) / 5
    principal = sum(deciles_for(2_700.0)[:5]) / 5
    assert result["mortgage_payment"]["bottom50"] == pytest.approx(
        interest + principal
    )
    assert result["mortgage_label_signs"][
        "Mortgage principal paid on owned property"
    ] == -1.0
    assert result["mortgage_label_signs"]["Mortgage interest and charges"] == 1.0


def test_the_payment_rises_with_income_once_the_sign_is_taken(
    tmp_path: Path,
) -> None:
    """Netting the two lines is visible here and nowhere else: it does not
    change the all-units total by much, and it destroys the gradient."""
    book = write_workbook(tmp_path / "cex.xlsx", items=_items_with(-1.0))
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    payment = read_inputs(book, selection)["mortgage_payment"]
    assert payment["bottom50"] < payment["next40"] < payment["next9"]


def test_a_mortgage_line_with_a_mixed_sign_is_refused(tmp_path: Path) -> None:
    mixed = list(deciles_for(2_700.0))
    mixed[0] = -mixed[0]
    items = _items_with(1.0)
    items["Mortgage principal paid on owned property"] = tuple(mixed)
    book = write_workbook(tmp_path / "cex.xlsx", items=items)
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(SelectionProblem) as caught:
        read_inputs(book, selection)
    assert "mixed sign" in str(caught.value)


# ---------------------------------------------------------------------------
# Housing tenure, read here because the flows it divides are ranked this way
# ---------------------------------------------------------------------------
def test_tenure_is_read_off_the_label_row_and_leaves_the_percents(
    tmp_path: Path,
) -> None:
    book, selection = setup(tmp_path)
    tenure = read_tenure(book, selection)
    assert set(tenure) == set(TENURE_ROLES)
    assert tenure["homeowner"]["Lowest 10 percent"] == pytest.approx(0.34)
    assert tenure["renter"]["Lowest 10 percent"] == pytest.approx(0.66)
    assert tenure["mortgaged"]["Highest 10 percent"] == pytest.approx(0.70)


def test_a_group_tenure_is_the_mean_of_its_decile_columns(
    tmp_path: Path,
) -> None:
    book, selection = setup(tmp_path)
    tenure = read_inputs(book, selection)["tenure"]
    assert tenure["homeowner"]["bottom50"] == pytest.approx(
        sum(OWNER_DECILES[:5]) / 500
    )
    assert tenure["mortgaged"]["next40"] == pytest.approx(
        sum(MORTGAGED_DECILES[5:9]) / 400
    )
    assert tenure["renter"]["next9"] == tenure["renter"]["top1"]


def test_owner_and_renter_must_partition_the_group(tmp_path: Path) -> None:
    """A third category, or a row read from the wrong position."""
    book = write_workbook(
        tmp_path / "cex.xlsx",
        renter_deciles=tuple(v - 20.0 for v in RENTER_DECILES),
    )
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, selection)
    assert "one or the other" in str(caught.value)


def test_the_mortgaged_must_be_a_subset_of_the_owners(tmp_path: Path) -> None:
    book = write_workbook(
        tmp_path / "cex.xlsx",
        mortgaged_deciles=tuple(v + 40.0 for v in MORTGAGED_DECILES),
    )
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, selection)
    assert "subset of the owners" in str(caught.value)


def test_a_tenure_row_that_does_not_average_to_all_units_is_refused(
    tmp_path: Path,
) -> None:
    """The table publishes its own all-units figure, so a decile column read
    from the wrong position shows up against it.

    The published figure is moved rather than the deciles, so this trips the
    averaging anchor and not the partition anchor: two checks that would both
    fire on the same fixture would leave neither of them tested.
    """
    book = write_workbook(tmp_path / "cex.xlsx",
                          tenure_all_units={"homeowner": 0.0 + 80.0})
    selection = Selection.load(write_selection(tmp_path / "sel.json"))
    with pytest.raises(AnchorProblem) as caught:
        read_inputs(book, selection)
    assert "all-units" in str(caught.value)


def test_a_selection_missing_a_tenure_role_fails_at_load(
    tmp_path: Path,
) -> None:
    with pytest.raises(SelectionProblem) as caught:
        Selection.load(
            write_selection(tmp_path / "sel.json",
                            tenure_labels={"homeowner": "Homeowner",
                                           "renter": "Renter"})
        )
    assert "mortgaged" in str(caught.value)


def test_the_two_sources_agree_nationally_and_not_by_group() -> None:
    """The ruling of 2026-08-15, kept where it can be read.

    The SCF's 0.6605 and the CEX's 0.648 are the same national rate. Their
    bottom groups are 0.391 and 0.522, which is a third of the way apart, and
    that gap is what a different ranking means rather than a discrepancy to be
    reconciled.
    """
    cex_national = sum(OWNER_DECILES) / 1000
    assert cex_national == pytest.approx(0.648)
    assert abs(cex_national - 0.6605) < 0.02
    cex_bottom = sum(OWNER_DECILES[:5]) / 500
    assert abs(cex_bottom - 0.390550) > 0.10
