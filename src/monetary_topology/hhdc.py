"""New York Fed Household Debt and Credit: the levels stage A1 scores against.

Stage A1 registers six calibration levels. Two of them are columns of one sheet
of one workbook, ``Percent of Balance 90+ Days Delinquent by Loan Type``: credit
card ``13.12`` and auto ``5.60`` for 2026Q1. ``docs/a1_availability.md`` traces
all six to their publishers and rules on which survive as measurement.

Retrieval lives in ``data/fetch_hhdc.py``; this module is the parsing and the
integrity check, so that both are covered by ``tests/test_hhdc.py`` without a
network.

Why this module exists rather than an import
--------------------------------------------
The same workbook is already extracted in the sibling repository
``topology-fingerprints`` (``fingerprints/hhdc_extract.py``, whose stdlib reader
the private helpers below are a port of). That repository has its own CI, its own
``RESULTS.md`` and its own retrieval rules, and nothing here has ever referenced
it. What crosses the boundary is a recipe verified against this workbook: locate
the sheet by a substring of its own title row, key the columns by their header
strings, and refuse a workbook that yields too few quarters. What does not cross
is a file.

Three properties of the source that the recipe exists to survive
-----------------------------------------------------------------
**Sheet names carry no meaning.** The sheets are ``Page 3 Data`` through
``Page 40 Data`` and those numbers are positions in the PDF report, which move
between quarters. Only the title row inside a sheet identifies its table.

**The table of contents and the sheets disagree on titles.** The contents page
calls the flow table ``Flow into Serious Delinquency (90+) by Loan Type``; that
sheet's own first row reads ``New Seriously Delinquent* Balances by Loan Type``.
The title keys below are taken from the sheets, not from the contents.

**The two tables do not share a column order.** Page 12 runs mortgage, HELOC,
auto, card, student, other, all; Page 14 runs auto, card, mortgage, HELOC,
student, other, all. A reader keyed on position returns the wrong series without
failing, which is the silent-guard shape recorded in ``MEASUREMENT.md`` mode 7.

Stock and flow are different quantities and both are readable here
-------------------------------------------------------------------
For 2026Q1: auto ``5.60`` against ``2.97``, card ``13.12`` against ``7.10``. The
first of each pair is the share of outstanding balance 90+ days late; the second
is the annualised share newly entering. ``docs/a1_availability.md`` 8 item 2
requires the pre-registration to declare which one A1 emits before a target is
quoted, so neither is privileged here.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# The pinned vintage
# ---------------------------------------------------------------------------
# A1's six targets were written against 2026Q1. The 2026Q2 workbook was released
# 2026-08-11 and the URL pattern below resolves for it, so "whatever is newest"
# would silently rewrite the targets. The vintage is therefore a constant in
# source, frozen by git, rather than whatever happens to sit in data/raw.
PINNED_VINTAGE = "2026Q1"

#: Verified 2026-08-13. The lower-case form ``hhd_c_report_2026q2.xlsx`` and an
#: extension-less form both resolve as well; older quarters resolve under this
#: same pattern, which is what makes a past vintage re-fetchable.
URL_TEMPLATE = (
    "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/"
    "data/xls/HHD_C_Report_{vintage}.xlsx"
)

#: Substrings of the sheets' own title rows, not of the table of contents.
STOCK_TITLE = "90+ Days Delinquent by Loan Type"
FLOW_TITLE = "Seriously Delinquent"

#: Header strings as they appear in the workbook, in no particular order because
#: order is exactly what must not be relied on.
LOAN_TYPES = ("MORTGAGE", "HELOC", "AUTO", "CC", "STUDENT LOAN", "OTHER", "ALL")

#: A quarterly series starting 2003Q1 has more than eighty observations by any
#: vintage this project will see. A workbook yielding fewer has been truncated
#: or restructured, and either way it must not be read in silently
#: (the project's engineering rule 6).
MIN_QUARTERS = 80

#: Retrieval integrity, not a criterion. These are the values the pinned vintage
#: published, so a mismatch says the bytes changed, whether by revision or by a
#: bad download. Nothing scores against them; A1's criteria live in the
#: pre-registration.
ANCHORS_2026Q1 = {
    ("stock", "CC"): 13.12,
    ("stock", "AUTO"): 5.60,
    ("flow", "CC"): 7.10,
    ("flow", "AUTO"): 2.97,
}


class WorkbookProblem(ValueError):
    """The workbook is not the shape this module knows how to read."""


class SheetMissing(WorkbookProblem):
    """No sheet carries the expected title row."""


class ColumnMissing(WorkbookProblem):
    """A sheet was found but does not carry the expected headers."""


class TooFewQuarters(WorkbookProblem):
    """The table is shorter than any real vintage, so it is truncated."""


class AnchorMismatch(WorkbookProblem):
    """The pinned vintage no longer publishes the values it published."""


# ---------------------------------------------------------------------------
# Minimal xlsx reading, standard library only
# ---------------------------------------------------------------------------
_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
_CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _sheet_target(z: zipfile.ZipFile, sheet_name: str) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = None
    for s in wb.find("m:sheets", _NS):
        if s.attrib["name"] == sheet_name:
            rid = s.attrib[f"{{{_NS['r']}}}id"]
    if rid is None:
        raise SheetMissing(f"no sheet named {sheet_name!r}")
    for rel in rels:
        if rel.attrib["Id"] == rid:
            target = rel.attrib["Target"].lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise SheetMissing(f"no relationship target for {rid}")


def sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        return [s.attrib["name"] for s in wb.find("m:sheets", _NS)]


def read_sheet(path: Path, sheet_name: str) -> list[list[object]]:
    """Return one sheet as a row grid: float, str, or None per cell."""
    with zipfile.ZipFile(path) as z:
        strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                strings.append(
                    "".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t"))
                )
        sheet = ET.fromstring(z.read(_sheet_target(z, sheet_name)))

    cells: dict[int, dict[int, object]] = {}
    max_col = 0
    for c in sheet.iter(f"{{{_NS['m']}}}c"):
        match = _CELL_RE.match(c.attrib["r"])
        if match is None:
            continue
        col, rownum = _col_index(match.group(1)), int(match.group(2))
        kind = c.attrib.get("t", "n")
        value: object = None
        if kind == "inlineStr":
            is_el = c.find("m:is", _NS)
            if is_el is not None:
                value = "".join(
                    x.text or "" for x in is_el.iter(f"{{{_NS['m']}}}t")
                )
        else:
            v = c.find("m:v", _NS)
            if v is not None and v.text is not None:
                if kind == "s":
                    value = strings[int(v.text)]
                elif kind == "str":
                    value = v.text
                else:
                    try:
                        value = float(v.text)
                    except ValueError:
                        value = v.text
        if value is not None:
            cells.setdefault(rownum, {})[col] = value
            max_col = max(max_col, col)

    n_rows = max(cells) if cells else 0
    grid: list[list[object]] = []
    for rn in range(1, n_rows + 1):
        row = cells.get(rn, {})
        grid.append([row.get(c) for c in range(max_col + 1)])
    return grid


# ---------------------------------------------------------------------------
# The tables
# ---------------------------------------------------------------------------
_QUARTER_RE = re.compile(r"^(\d{2}):Q([1-4])$")


def quarter_to_iso(label: str) -> str:
    """``26:Q1`` -> ``2026-01-01``. Two-digit years, 50 is the pivot."""
    match = _QUARTER_RE.match(label.strip())
    if match is None:
        raise ValueError(f"not a quarter label: {label!r}")
    yy, q = int(match.group(1)), int(match.group(2))
    year = 2000 + yy if yy < 50 else 1900 + yy
    return f"{year}-{(q - 1) * 3 + 1:02d}-01"


@dataclass(frozen=True)
class DelinquencyTable:
    """One loan-type table: dates, and one value per loan type per date.

    ``values[loan_type][i]`` may be ``None``. That is coverage rather than
    corruption: the flow table carries no student loan figure for its earliest
    quarters. A row is kept when its label parses, so a missing cell never
    silently shortens the series.
    """

    title: str
    sheet: str
    dates: tuple[str, ...]
    values: dict[str, tuple[float | None, ...]]

    def at(self, iso_date: str, loan_type: str) -> float | None:
        return self.values[loan_type][self.dates.index(iso_date)]


def locate_sheet(path: Path, title_key: str) -> tuple[str, list[list[object]]]:
    """Find the sheet whose own first rows carry ``title_key``.

    Sheet names are page numbers in the PDF and move between vintages, so they
    are never matched on.
    """
    for name in sheet_names(path):
        if not name.startswith("Page"):
            continue
        grid = read_sheet(path, name)
        head = " ".join(str(c) for row in grid[:4] for c in row if c)
        if title_key in head:
            return name, grid
    raise SheetMissing(
        f"no sheet carries {title_key!r} in its first four rows; the workbook "
        f"has been restructured"
    )


def read_table(
    path: Path,
    title_key: str,
    loan_types: tuple[str, ...] = LOAN_TYPES,
    min_quarters: int = MIN_QUARTERS,
) -> DelinquencyTable:
    """Read one loan-type table, keyed on header strings rather than position."""
    sheet, grid = locate_sheet(path, title_key)

    header_row = None
    for i, row in enumerate(grid):
        labels = {str(c).strip() for c in row if isinstance(c, str)}
        if set(loan_types) <= labels:
            header_row = i
            break
    if header_row is None:
        raise ColumnMissing(
            f"sheet {sheet!r} carries {title_key!r} but no row holds all of "
            f"{', '.join(loan_types)}"
        )

    column_of: dict[str, int] = {}
    for j, cell in enumerate(grid[header_row]):
        if isinstance(cell, str) and cell.strip() in loan_types:
            column_of.setdefault(cell.strip(), j)

    dates: list[str] = []
    series: dict[str, list[float | None]] = {name: [] for name in loan_types}
    for row in grid[header_row + 1:]:
        label = row[0]
        if not isinstance(label, str) or not _QUARTER_RE.match(label.strip()):
            continue
        dates.append(quarter_to_iso(label))
        for name in loan_types:
            cell = row[column_of[name]] if column_of[name] < len(row) else None
            series[name].append(cell if isinstance(cell, float) else None)

    if len(dates) < min_quarters:
        raise TooFewQuarters(
            f"sheet {sheet!r} yielded {len(dates)} quarters, below the floor of "
            f"{min_quarters}; treat the file as truncated rather than short"
        )

    title = str(grid[0][0]).strip() if grid and grid[0] and grid[0][0] else sheet
    return DelinquencyTable(
        title=title,
        sheet=sheet,
        dates=tuple(dates),
        values={name: tuple(vals) for name, vals in series.items()},
    )


def read_stock(path: Path) -> DelinquencyTable:
    """Percent of outstanding balance 90+ days delinquent, by loan type."""
    return read_table(path, STOCK_TITLE)


def read_flow(path: Path) -> DelinquencyTable:
    """Annualised share of balances newly 90+ days delinquent, by loan type."""
    return read_table(path, FLOW_TITLE)


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------
def validate(path: Path, vintage: str = PINNED_VINTAGE) -> dict[str, object]:
    """Read both tables and report. Raises on anything a caller must not ignore.

    This is the corruption and truncation check the project's engineering rule 6 requires:
    a workbook that is unreadable, restructured, short, or no longer carrying
    the values its vintage published fails loudly here rather than being read in
    silently and scored against later.
    """
    stock = read_stock(path)
    flow = read_flow(path)

    summary: dict[str, object] = {
        "vintage": vintage,
        "stock_sheet": stock.sheet,
        "stock_title": stock.title,
        "stock_quarters": len(stock.dates),
        "stock_last": stock.dates[-1],
        "flow_sheet": flow.sheet,
        "flow_title": flow.title,
        "flow_quarters": len(flow.dates),
        "flow_last": flow.dates[-1],
    }

    if vintage == "2026Q1":
        last = stock.dates[-1]
        if last != "2026-01-01":
            raise AnchorMismatch(
                f"vintage {vintage} should end at 2026-01-01, ends at {last}"
            )
        tables = {"stock": stock, "flow": flow}
        for (which, loan_type), expected in sorted(ANCHORS_2026Q1.items()):
            got = tables[which].at(last, loan_type)
            if got is None or not math.isclose(got, expected, abs_tol=1e-9):
                raise AnchorMismatch(
                    f"{which} {loan_type} at {last} is {got!r}, published "
                    f"{expected}; the source changed under a pinned vintage"
                )
        summary["anchors_checked"] = len(ANCHORS_2026Q1)
    else:
        summary["anchors_checked"] = 0

    return summary


def workbook_url(vintage: str = PINNED_VINTAGE) -> str:
    return URL_TEMPLATE.format(vintage=vintage)


def workbook_path(raw_dir: Path, vintage: str = PINNED_VINTAGE) -> Path:
    """One file per vintage, so a new quarter can never land on an old one."""
    return raw_dir / f"hhd_c_report_{vintage.lower()}.xlsx"
