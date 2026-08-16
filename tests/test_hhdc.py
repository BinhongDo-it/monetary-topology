"""Tests for the HHDC reader, built on synthetic workbooks and no network.

What these guard is not that the arithmetic is right, since there is none. They
guard the three ways this particular source breaks a reader: sheet names that
carry no meaning, a table of contents that disagrees with the sheets, and two
tables that do not share a column order. Each of those returns wrong data
without raising, which is the silent-guard shape in ``MEASUREMENT.md`` mode 7,
so each gets a case that would fail if the guard were removed.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from monetary_topology.hhdc import (
    ANCHORS_2026Q1,
    LOAN_TYPES,
    AnchorMismatch,
    ColumnMissing,
    SheetMissing,
    TooFewQuarters,
    quarter_to_iso,
    read_flow,
    read_stock,
    read_table,
    validate,
    workbook_path,
    workbook_url,
)

STOCK_TITLE_ROW = "Percent of Balance 90+ Days Delinquent by Loan Type "
FLOW_TITLE_ROW = "New Seriously Delinquent* Balances by Loan Type "

# The order the two real sheets use. They differ, and that difference is the
# point of the header-keyed lookup.
STOCK_ORDER = ("MORTGAGE", "HELOC", "AUTO", "CC", "STUDENT LOAN", "OTHER", "ALL")
FLOW_ORDER = ("AUTO", "CC", "MORTGAGE", "HELOC", "STUDENT LOAN", "OTHER", "ALL")


# ---------------------------------------------------------------------------
# A minimal xlsx writer, so the fixtures exercise the same path as the source:
# shared strings, one worksheet per sheet, cells addressed by A1 reference.
# ---------------------------------------------------------------------------
def _col_letters(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def write_workbook(path: Path, sheets: dict[str, list[list[object]]]) -> Path:
    strings: list[str] = []
    index_of: dict[str, int] = {}

    def intern(text: str) -> int:
        if text not in index_of:
            index_of[text] = len(strings)
            strings.append(text)
        return index_of[text]

    sheet_xml: dict[str, str] = {}
    for name, rows in sheets.items():
        body = []
        for r, row in enumerate(rows, start=1):
            cells = []
            for c, value in enumerate(row):
                if value is None:
                    continue
                ref = f"{_col_letters(c)}{r}"
                if isinstance(value, str):
                    cells.append(
                        f'<c r="{ref}" t="s"><v>{intern(value)}</v></c>'
                    )
                else:
                    cells.append(f'<c r="{ref}"><v>{value!r}</v></c>')
            body.append(f'<row r="{r}">{"".join(cells)}</row>')
        sheet_xml[name] = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main">'
            f'<sheetData>{"".join(body)}</sheetData></worksheet>'
        )

    entries = []
    rels = []
    for i, name in enumerate(sheets, start=1):
        entries.append(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>')
        rels.append(
            f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/worksheet"/>'
        )

    shared = "".join(f"<si><t>{s}</t></si>" for s in strings)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats'
            '.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(entries)}</sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/'
            f'package/2006/relationships">{"".join(rels)}</Relationships>',
        )
        z.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
            f'2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">'
            f"{shared}</sst>",
        )
        for i, name in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml[name])
    return path


def quarter_labels(n: int, last_year: int = 26, last_q: int = 1) -> list[str]:
    """The n quarter labels ending at ``last_year:Q{last_q}``, oldest first."""
    out = []
    year, quarter = last_year, last_q
    for _ in range(n):
        out.append(f"{year:02d}:Q{quarter}")
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1
    return list(reversed(out))


def table_rows(
    title: str,
    order: tuple[str, ...],
    n_quarters: int,
    values: dict[str, float],
    last_row_values: dict[str, float] | None = None,
    blank: str | None = None,
) -> list[list[object]]:
    """A sheet shaped like the real ones: title, unit, source, header, data."""
    rows: list[list[object]] = [
        [title],
        ["Percent"],
        ["Return to Table of Contents", "Source: New York Fed CCP/Equifax"],
        [None, *order],
    ]
    labels = quarter_labels(n_quarters)
    for i, label in enumerate(labels):
        last = i == len(labels) - 1
        row: list[object] = [label]
        for name in order:
            if blank == name and not last:
                row.append(None)
            elif last and last_row_values and name in last_row_values:
                row.append(last_row_values[name])
            else:
                row.append(values[name])
        rows.append(row)
    return rows


BASE = dict.fromkeys(LOAN_TYPES, 1.0)


# ---------------------------------------------------------------------------
# The three properties of the source
# ---------------------------------------------------------------------------
def test_sheet_is_found_by_title_not_by_name(tmp_path: Path) -> None:
    """Page numbers move between vintages, so the sheet name must not be used."""
    path = write_workbook(
        tmp_path / "wb.xlsx",
        {
            "Page 3 Data": [["Total Debt Balance and its Composition"]],
            "Page 99 Data": table_rows(STOCK_TITLE_ROW, STOCK_ORDER, 80, BASE),
        },
    )
    table = read_stock(path)
    assert table.sheet == "Page 99 Data"
    assert len(table.dates) == 80


def test_flow_sheet_title_differs_from_the_table_of_contents(
    tmp_path: Path,
) -> None:
    """The contents page says 'Flow into Serious Delinquency'; the sheet does not."""
    path = write_workbook(
        tmp_path / "wb.xlsx",
        {"Page 14 Data": table_rows(FLOW_TITLE_ROW, FLOW_ORDER, 80, BASE)},
    )
    assert read_flow(path).sheet == "Page 14 Data"
    with pytest.raises(SheetMissing):
        read_table(path, "Flow into Serious Delinquency (90+) by Loan Type")


def test_columns_are_keyed_by_header_not_position(tmp_path: Path) -> None:
    """The two real tables disagree on column order; the reader must not care."""
    marked = {**BASE, "AUTO": 5.60, "CC": 13.12}
    stock = write_workbook(
        tmp_path / "stock.xlsx",
        {"Page 12 Data": table_rows(STOCK_TITLE_ROW, STOCK_ORDER, 80, marked)},
    )
    flow = write_workbook(
        tmp_path / "flow.xlsx",
        {"Page 14 Data": table_rows(FLOW_TITLE_ROW, FLOW_ORDER, 80, marked)},
    )
    a = read_stock(stock)
    b = read_flow(flow)
    assert a.values["AUTO"][-1] == 5.60
    assert b.values["AUTO"][-1] == 5.60
    assert a.values["CC"] == b.values["CC"]


# ---------------------------------------------------------------------------
# Coverage against corruption
# ---------------------------------------------------------------------------
def test_a_blank_cell_is_none_and_does_not_shorten_the_series(
    tmp_path: Path,
) -> None:
    """The flow table has no student loan figure for its earliest quarters."""
    path = write_workbook(
        tmp_path / "wb.xlsx",
        {
            "Page 14 Data": table_rows(
                FLOW_TITLE_ROW, FLOW_ORDER, 80, BASE, blank="STUDENT LOAN"
            )
        },
    )
    table = read_flow(path)
    assert len(table.dates) == 80
    assert table.values["STUDENT LOAN"][0] is None
    assert table.values["STUDENT LOAN"][-1] == 1.0
    assert table.values["AUTO"][0] == 1.0


def test_a_short_table_is_refused_rather_than_read(tmp_path: Path) -> None:
    short = write_workbook(
        tmp_path / "short.xlsx",
        {"Page 12 Data": table_rows(STOCK_TITLE_ROW, STOCK_ORDER, 79, BASE)},
    )
    with pytest.raises(TooFewQuarters):
        read_stock(short)
    ok = write_workbook(
        tmp_path / "ok.xlsx",
        {"Page 12 Data": table_rows(STOCK_TITLE_ROW, STOCK_ORDER, 80, BASE)},
    )
    assert len(read_stock(ok).dates) == 80


def test_a_missing_loan_type_is_refused(tmp_path: Path) -> None:
    dropped = tuple(n for n in STOCK_ORDER if n != "AUTO")
    path = write_workbook(
        tmp_path / "wb.xlsx",
        {"Page 12 Data": table_rows(STOCK_TITLE_ROW, dropped, 80, BASE)},
    )
    with pytest.raises(ColumnMissing):
        read_stock(path)


def test_no_matching_sheet_is_refused(tmp_path: Path) -> None:
    path = write_workbook(
        tmp_path / "wb.xlsx", {"Page 3 Data": [["Total Debt Balance"]]}
    )
    with pytest.raises(SheetMissing):
        read_stock(path)


# ---------------------------------------------------------------------------
# Labels, paths, and the pinned vintage
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("label", "iso"),
    [
        ("03:Q1", "2003-01-01"),
        ("26:Q1", "2026-01-01"),
        ("12:Q4", "2012-10-01"),
        ("99:Q3", "1999-07-01"),
    ],
)
def test_quarter_labels(label: str, iso: str) -> None:
    assert quarter_to_iso(label) == iso


def test_a_non_quarter_label_raises() -> None:
    with pytest.raises(ValueError):
        quarter_to_iso("2026Q1")


def test_one_file_per_vintage(tmp_path: Path) -> None:
    """A later quarter must not be able to land on an earlier one's file."""
    q1 = workbook_path(tmp_path, "2026Q1")
    q2 = workbook_path(tmp_path, "2026Q2")
    assert q1 != q2
    assert q1.name == "hhd_c_report_2026q1.xlsx"
    assert "2026Q2" in workbook_url("2026Q2")


def _pinned_workbook(path: Path, cc_stock: float = 13.12) -> Path:
    return write_workbook(
        path,
        {
            "Page 12 Data": table_rows(
                STOCK_TITLE_ROW, STOCK_ORDER, 80, BASE,
                last_row_values={"CC": cc_stock, "AUTO": 5.60},
            ),
            "Page 14 Data": table_rows(
                FLOW_TITLE_ROW, FLOW_ORDER, 80, BASE,
                last_row_values={"CC": 7.10, "AUTO": 2.97},
            ),
        },
    )


def test_the_pinned_vintage_passes_its_own_anchors(tmp_path: Path) -> None:
    summary = validate(_pinned_workbook(tmp_path / "wb.xlsx"), "2026Q1")
    assert summary["stock_last"] == "2026-01-01"
    assert summary["anchors_checked"] == len(ANCHORS_2026Q1)


def test_a_revised_pinned_vintage_is_refused(tmp_path: Path) -> None:
    """A pinned vintage that no longer publishes its values must fail loudly."""
    path = _pinned_workbook(tmp_path / "wb.xlsx", cc_stock=13.13)
    with pytest.raises(AnchorMismatch):
        validate(path, "2026Q1")


def test_an_unpinned_vintage_checks_no_anchors(tmp_path: Path) -> None:
    summary = validate(_pinned_workbook(tmp_path / "wb.xlsx"), "2026Q2")
    assert summary["anchors_checked"] == 0
