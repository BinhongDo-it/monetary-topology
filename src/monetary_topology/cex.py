"""Income before taxes and the necessities basket, from the CEX decile table.

``docs/a1_inputs_availability.md`` §3: both quantities come from one published
table, so they share a denominator and a unit of observation. The model needs
them because the basket is senior to every obligation in the cascade
(``docs/a1_prereg.md`` §2.4b): without it a household banks its whole margin and
no income path short of collapse ever produces a default.

This module parses. ``data/fetch_cex.py`` retrieves.

The xlsx reader is imported from ``monetary_topology.hhdc`` rather than copied.
It is a generic standard-library reader, already covered by ``tests/test_hhdc.py``
against a real workbook, and a second copy of ninety lines of zip and xml
handling would be worse than one import across two stages.

Two disclosures that travel with every number this module returns
------------------------------------------------------------------
**The ranking is income, and the model's population is ranked by wealth.** No
source publishes a consumption basket by net worth percentile: the CEX has no
wealth ranking and the BLS points users to the SCF for wealth; the SCF collects
food at home and rent and neither utilities, healthcare nor commuting; the PSID
has both and covers about 72% of the CE definition of outlays, biennially. The
pre-registration handles this as an arm rather than an assumption, with a second
run permuting the assignment consistently with a rank correlation of 0.76.

*Which is why tenure is read here.* A shelter flow published per consumer unit
has to be divided by the share of consumer units that pays it, and that share
must be ranked the way the flow is. Taking the flow from an income decile and
the share from a net-worth percentile is the population error in
``MEASUREMENT.md``, and it is not a rounding question: it put the next 40%
group's rent at 6,145 dollars a month, which is not a rent anyone pays but the
whole group's rent spending divided by the few of them who rent *by wealth*.
The two sources agree on the national level, 0.65 here against the SCF's 0.6605,
and disagree about the distribution, which is what a different ranking means.

**Shelter is not in the basket.** ``docs/a1_prereg.md`` §2.4b: the CEX
``Shelter`` line is rent plus owned-dwelling costs, so a basket containing it
charges a household its rent once as an undefaultable necessity and again as a
defaultable rung. Worse than the arithmetic, it asserts that the dwelling cannot
be given up, which is the opposite of what the cascade says. The basket is the
five other items, and the shelter flows are read separately as their own rungs.

**The top 1% is not separately observed.** The finest published cut is a decile,
so this project's top 1% and next 9% both inherit the top decile's figures. Any
criterion that needs those two groups to differ in income or in the basket cannot
be scored on this input, and A1 registers none that does.

Three properties of the workbook that a reader has to survive
---------------------------------------------------------------
All three were read off the file rather than assumed, and each one would have
produced a number rather than an error.

**The item label row carries no numbers.** Every item is a label on its own row
followed by ``Mean``, ``Share``, ``SE`` and ``RSE``. The value this stage wants
is on the ``Mean`` row.

**``Share`` sits directly under ``Mean``**, and it is a percentage of total
expenditure. A reader that took the first numeric row under the label would
return shares where dollars were asked for, and the internal anchor would not
notice because shares also average across deciles.

**The column headers carry embedded newlines**: the all-units column is written
``All\nconsumer\nunits`` and the first decile ``Lowest\n10\npercent``. Matching
on the literal text fails; whitespace is collapsed before any comparison.

One more, recorded because it is luck rather than design otherwise:
``Income before taxes`` appears **twice**, once among the consumer-unit
characteristics near the top and once heading the income-source breakdown near
the bottom. The first occurrence is the one taken, and there is a test for that.

And one that is the opposite of all three: ``Number of consumer units (in
thousands)`` carries its values **on the label row itself**, with no ``Mean``
beneath. The generic reader raises on it, which is the correct behaviour, so it
is read by its own path and the difference is asserted rather than smoothed over
with a fallback.

**The owner's two shelter lines do not share a sign.** ``Mortgage interest and
charges`` is an expenditure; ``Mortgage principal paid on owned property`` sits
in the addenda under "Other financial information" and is published negative at
every decile, because it records a reduction in liabilities rather than an
outlay. Added as published they net: all consumer units read 3,646 and -2,924,
so the owner's annual payment would come out at 722 and would stop rising with
income. The cash the household hands over is the magnitude of each line, and the
sign is read off the file rather than pinned, with a mixed-sign label refused.

Why the consumer-unit count is read at all
--------------------------------------------
The financial accounts publish stocks for a whole sector and the model carries
one household at a time, so somewhere a national aggregate has to be divided by
a number of households. That number decides the level of every obligation in the
stage, and the unit of observation it counts has to be the one the income and
the basket already belong to. The CE consumer unit is not the Census household
and not the SCF family; taking the count from this table rather than from
another source is what keeps the numerator and the denominator on the same
population, which is ``MEASUREMENT.md``'s population error and not a rounding
question. It also arrives at the same vintage as the income it divides.

The three anchors
-------------------
**Internal, on the money columns.** Deciles are equal-sized by construction, so
the simple mean of the ten decile columns must reproduce the table's own "All
consumer units" column. This catches a column selected off by one, a header row
read at the wrong height, and a decile column silently missing.

**Internal, on the counts.** The ten decile counts must sum to the all-units
count. This is a separate check rather than a restatement: a decile column read
from the wrong position can still average correctly on money and will not sum
correctly on counts.

**External.** For reference year 2024 the published all-consumer-unit figures are
income before taxes ``104,207`` and average annual expenditure ``78,535``. The
internal anchors alone would pass on a table for the wrong year; this one fixes
the vintage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from monetary_topology.hhdc import read_sheet, sheet_names

#: The four groups, bottom half first, as everywhere else in this project.
GROUPS = ("bottom50", "next40", "next9", "top1")

#: Reference year 2024, released 2025-12-19. Reference year 2025 is scheduled
#: for 2026-10-29 and carries a shutdown gap: the CEX could not collect in
#: October and November 2025, and the Diary survey doubles the September and
#: December weights to stand in. A 2025 table is therefore not comparable to
#: earlier years without a footnote, and this stage pins 2024.
REFERENCE_YEAR = "2024"

#: Published with the reference-year 2024 release, all consumer units.
PUBLISHED_2024 = {
    "income_before_taxes": 104_207.0,
    "total_expenditure": 78_535.0,
}

#: The decile means average to the all-units column only up to rounding and to
#: the deciles being equal-sized, which they are by construction.
INTERNAL_TOLERANCE = 0.02
EXTERNAL_TOLERANCE = 0.01

#: The three tenure rows this stage reads. ``homeowner`` is the sum of the two
#: ownership rows and is read separately rather than derived, so the table's own
#: arithmetic is a check rather than an assumption.
TENURE_ROLES = ("homeowner", "mortgaged", "renter")

#: Tenure is published as whole percents, so a group's share carries at most
#: half a point of rounding and the three roles reconcile only to about that.
TENURE_TOLERANCE = 0.02

#: The consumer-unit count is published **in thousands**, and a unit slip there
#: is invisible to every ratio the stage computes: it would divide an aggregate
#: by a thousandth of the right denominator and make consumer credit per
#: household a thousand times too large, which the Beta constructor would then
#: refuse as a group unable to service its own debt. This band is the guard that
#: makes the unit an assertion rather than a comment. Roughly 135 million
#: consumer units in 2024, and no plausible American vintage sits outside this.
CONSUMER_UNIT_BAND = (100e6, 200e6)


class SelectionProblem(ValueError):
    """The workbook does not have the shape the pinned selection describes."""


class AnchorProblem(ValueError):
    """A computed quantity does not reproduce a published one."""


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def inventory(path: Path, rows: int = 40, columns: int = 14) -> str:
    """Every sheet, and the top-left corner of each, so a layout can be read."""
    lines: list[str] = []
    for name in sheet_names(path):
        grid = read_sheet(path, name)
        lines.append(f"== {name}  ({len(grid)} rows)")
        for i, row in enumerate(grid[:rows]):
            cells = [
                "" if c is None else (c if isinstance(c, str) else f"{c:g}")
                for c in row[:columns]
            ]
            if any(cell.strip() for cell in cells):
                lines.append(f"  r{i:<3} " + " | ".join(cells))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    """What ``data/cex_items.json`` says, after a human has read the inventory.

    ``group_columns`` maps each of this project's groups to the list of decile
    column headers averaged to make it. The list is where the two disclosures
    above become concrete: ``next9`` and ``top1`` name the same single column.
    """

    reference_year: str
    source: str
    sheet: str
    label_column: int
    all_units_column: str
    income_label: str
    expenditure_label: str
    necessity_labels: tuple[str, ...]
    #: The rent line, read as its own rung rather than folded into the basket.
    rent_label: str
    #: The owner's shelter flow. Two lines, because the published interest and
    #: charges exclude the principal the household also pays every month.
    mortgage_labels: tuple[str, ...]
    #: The consumer-unit count. **Its value sits on the label row itself**,
    #: not on a ``Mean`` row beneath it, which is why it is named separately and
    #: read by its own path: the ordinary reader would look one row down, find
    #: ``Lower limit``, and raise. The count is what turns an aggregate from the
    #: financial accounts into a per-household figure, so its unit of
    #: observation has to be the same one the income and the basket carry, and
    #: taking it from this table is how that is guaranteed rather than hoped.
    consumer_units_label: str
    #: Housing tenure, by the same income deciles as everything else here.
    #: Three roles: ``homeowner``, ``mortgaged`` and ``renter``. Published as
    #: whole percents on the label row, like the consumer-unit count.
    #:
    #: This is read from the CEX rather than the SCF because the shelter flows
    #: it divides are published by income decile. Dividing an income-ranked
    #: rent by a wealth-ranked renter share is ``MEASUREMENT.md``'s population
    #: error, and it is not small: the SCF route puts the next-40% group's rent
    #: at 6,145 dollars a month, which is nobody's rent. The two sources agree
    #: nationally, 0.65 here against 0.6605 there; they disagree about the
    #: distribution, which is what a different ranking means.
    tenure_labels: dict[str, str]
    group_columns: dict[str, list[str]]
    #: The statistic row under each item label. ``Share`` is a percentage of
    #: total expenditure and sits right beneath it, so this is named rather
    #: than taken as "the first numeric row".
    statistic_label: str = "Mean"

    @staticmethod
    def load(path: Path) -> Selection:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("sheet", "all_units_column", "income_label",
                    "expenditure_label"):
            if not raw.get(key):
                raise SelectionProblem(f"{path.name} has no {key}")
        if not raw.get("necessity_labels"):
            raise SelectionProblem(
                f"{path.name} lists no necessity_labels; the basket must be "
                f"named rather than inferred"
            )
        if any("shelter" in label.lower()
               for label in raw["necessity_labels"]):
            raise SelectionProblem(
                f"{path.name} puts shelter in the basket. Shelter is a rung, "
                f"and counting it as a necessity charges a household its rent "
                f"twice; see docs/a1_prereg.md 2.4b"
            )
        for key in ("rent_label", "mortgage_labels", "consumer_units_label",
                    "tenure_labels"):
            if not raw.get(key):
                raise SelectionProblem(f"{path.name} has no {key}")
        absent_roles = [r for r in TENURE_ROLES
                        if not raw["tenure_labels"].get(r)]
        if absent_roles:
            raise SelectionProblem(
                f"{path.name} names no tenure row for "
                f"{', '.join(absent_roles)}; every household in the model has "
                f"one of the three and a missing role would silently become "
                f"another"
            )
        absent = [g for g in GROUPS if not raw.get("group_columns", {}).get(g)]
        if absent:
            raise SelectionProblem(
                f"{path.name} is missing group(s) {', '.join(absent)}"
            )
        return Selection(
            reference_year=raw.get("reference_year", REFERENCE_YEAR),
            source=raw.get("source", ""),
            sheet=raw["sheet"],
            label_column=int(raw.get("label_column", 0)),
            all_units_column=raw["all_units_column"],
            income_label=raw["income_label"],
            expenditure_label=raw["expenditure_label"],
            necessity_labels=tuple(raw["necessity_labels"]),
            rent_label=raw["rent_label"],
            mortgage_labels=tuple(raw["mortgage_labels"]),
            consumer_units_label=raw["consumer_units_label"],
            tenure_labels={r: raw["tenure_labels"][r] for r in TENURE_ROLES},
            group_columns={g: list(raw["group_columns"][g]) for g in GROUPS},
            statistic_label=raw.get("statistic_label", "Mean"),
        )


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
#: The rows that belong to the item above them rather than starting a new item.
STATISTIC_ROWS = ("Mean", "Share", "SE", "RSE")


def normalise(text: object) -> str:
    """Collapse whitespace, because the headers carry embedded newlines."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())


def _header_row(grid: list[list[object]], wanted: str) -> int:
    for i, row in enumerate(grid):
        if any(normalise(c) == wanted for c in row):
            return i
    raise SelectionProblem(
        f"no row carries the column header {wanted!r}; the sheet's layout is "
        f"not what the selection describes"
    )


def _statistic_row(
    grid: list[list[object]], start: int, selection: Selection
) -> list[object]:
    """The ``Mean`` row belonging to the item label at ``start``.

    Stops at the next row whose label is not one of this item's statistics, so a
    missing ``Mean`` fails here rather than borrowing the next item's.
    """
    for offset in range(1, 8):
        if start + offset >= len(grid):
            break
        row = grid[start + offset]
        label = normalise(row[selection.label_column]) if row else ""
        if label == selection.statistic_label:
            return row
        if label and label not in STATISTIC_ROWS:
            break
    raise SelectionProblem(
        f"no {selection.statistic_label!r} row follows the item at row {start}; "
        f"the value rows are not laid out as the selection describes"
    )


def _grid_and_columns(
    path: Path, selection: Selection
) -> tuple[list[list[object]], dict[str, int], int]:
    """The sheet, its column index by header name, and where the header sits."""
    if selection.sheet not in sheet_names(path):
        raise SelectionProblem(
            f"sheet {selection.sheet!r} is not in the workbook; the sheets are "
            f"{', '.join(sheet_names(path))}"
        )
    grid = read_sheet(path, selection.sheet)
    header_at = _header_row(grid, selection.all_units_column)
    header = grid[header_at]

    columns: dict[str, int] = {}
    for j, cell in enumerate(header):
        name = normalise(cell)
        if name:
            columns.setdefault(name, j)

    wanted_columns = {selection.all_units_column}
    for names in selection.group_columns.values():
        wanted_columns.update(names)
    missing = sorted(c for c in wanted_columns if c not in columns)
    if missing:
        raise SelectionProblem(
            f"column(s) {', '.join(missing)} are not in the header row; it "
            f"carries {', '.join(sorted(columns))}"
        )
    return grid, columns, header_at


def read_label_row(path: Path, selection: Selection, label: str,
                   scale: float = 1.0, why: str = "") -> dict[str, float]:
    """The values a row carries **on its own label row**, by column.

    The consumer-unit count and the three tenure rows are laid out this way and
    every item is laid out the other way, so they do not go through
    :func:`_statistic_row`. The two paths are kept separate rather than made one
    path with a fallback: a fallback would silently accept an item whose
    ``Mean`` row had gone missing, which is the failure the statistic path
    exists to catch.
    """
    grid, columns, header_at = _grid_and_columns(path, selection)
    wanted = normalise(label)
    for i in range(header_at + 1, len(grid)):
        row = grid[i]
        if selection.label_column >= len(row):
            continue
        if normalise(row[selection.label_column]) != wanted:
            continue
        out = {
            name: float(row[index]) * scale
            for name, index in columns.items()
            if index < len(row) and isinstance(row[index], float)
        }
        if selection.all_units_column not in out:
            raise SelectionProblem(
                f"the row {label!r} carries no number under "
                f"{selection.all_units_column!r}. This row is expected to hold "
                f"its values on the label row itself; if the publisher has "
                f"moved them to a statistic row beneath, the selection has to "
                f"say so rather than this reader guessing"
            )
        return out
    raise SelectionProblem(f"no row carries the label {label!r}{why}")


def read_counts(path: Path, selection: Selection) -> dict[str, float]:
    """The consumer-unit count per column, converted out of thousands."""
    return read_label_row(
        path, selection, selection.consumer_units_label, scale=1_000.0,
        why="; without it an aggregate cannot be turned into a per-household "
            "figure",
    )


def read_tenure(path: Path, selection: Selection) -> dict[str, dict[str, float]]:
    """``{role: {column: share}}``, converted out of whole percents."""
    return {
        role: read_label_row(
            path, selection, selection.tenure_labels[role], scale=0.01,
            why="; without it the rent a renter pays cannot be separated from "
                "the rent a group spends",
        )
        for role in TENURE_ROLES
    }


def read_table(path: Path, selection: Selection) -> dict[str, dict[str, float]]:
    """``{item label: {column header: value}}`` for every label the selection names."""
    grid, columns, header_at = _grid_and_columns(path, selection)

    labels = {selection.income_label, selection.expenditure_label,
              selection.rent_label, *selection.mortgage_labels,
              *selection.necessity_labels}
    out: dict[str, dict[str, float]] = {}
    for i in range(header_at + 1, len(grid)):
        row = grid[i]
        if selection.label_column >= len(row):
            continue
        label = normalise(row[selection.label_column])
        # The first occurrence wins: "Income before taxes" appears again lower
        # down, heading the breakdown by income source.
        if label not in labels or label in out:
            continue
        values_row = _statistic_row(grid, i, selection)
        values: dict[str, float] = {}
        for name, index in columns.items():
            if index < len(values_row) and isinstance(values_row[index], float):
                values[name] = float(values_row[index])
        out[label] = values

    absent = sorted(labels - set(out))
    if absent:
        raise SelectionProblem(
            f"item label(s) {', '.join(absent)} were not found in column "
            f"{selection.label_column} of sheet {selection.sheet!r}"
        )
    return out


def group_value(
    table: dict[str, dict[str, float]], selection: Selection, label: str,
    group: str
) -> float:
    """A group is the simple mean of its decile columns, which are equal-sized."""
    names = selection.group_columns[group]
    values = [table[label][n] for n in names if n in table[label]]
    if len(values) != len(names):
        missing = [n for n in names if n not in table[label]]
        raise SelectionProblem(
            f"{label}: column(s) {', '.join(missing)} carry no number"
        )
    return sum(values) / len(values)


def read_inputs(path: Path, selection: Selection,
                check_anchors: bool = True) -> dict[str, object]:
    """Income and the basket, per group, with every anchor checked."""
    table = read_table(path, selection)
    counts = read_counts(path, selection)
    tenure_columns = read_tenure(path, selection)

    income = {g: group_value(table, selection, selection.income_label, g)
              for g in GROUPS}
    necessities = {
        g: sum(group_value(table, selection, label, g)
               for label in selection.necessity_labels)
        for g in GROUPS
    }

    # The basket per decile, which is the finest cut this table publishes.
    # A group mean handed to a household whose income is far below its group's
    # is not that household's outlay: the CEX measures expenditure, and a poorer
    # household's measured expenditure is lower. Stage A1b assigns by decile for
    # that reason and reports what within-decile variation is left, which this
    # table does not publish.
    necessities_by_decile = {
        column: sum(table[label].get(column, 0.0)
                    for label in selection.necessity_labels)
        for column in sorted({n for names in selection.group_columns.values()
                              for n in names})
    }

    rent = {g: group_value(table, selection, selection.rent_label, g)
            for g in GROUPS}

    # The owner's shelter flow is two published lines that do not share a sign.
    # ``Mortgage interest and charges`` is an expenditure. ``Mortgage principal
    # paid on owned property`` sits in the addenda under "Other financial
    # information" and is published **negative** at every decile, because it
    # records a reduction in liabilities rather than an outlay. Adding them as
    # published nets the household's own payment against itself: all consumer
    # units read 3,646 and -2,924, so the sum is 722 a year, and by decile the
    # result stops being monotone in income. What the model wants is the cash
    # the household hands over, which is the magnitude of each line.
    #
    # The sign is taken from the file rather than pinned, and a label whose
    # columns disagree about it is refused: a mixed-sign line is not a pure
    # outlay and this reader would be inventing a convention for it.
    signs: dict[str, float] = {}
    for label in selection.mortgage_labels:
        values = list(table[label].values())
        negative = sum(1 for v in values if v < 0.0)
        positive = sum(1 for v in values if v > 0.0)
        if negative and positive:
            raise SelectionProblem(
                f"{label!r} carries {positive} positive and {negative} "
                f"negative columns. A shelter flow published with a mixed sign "
                f"is not one line taken one way, and this reader will not pick "
                f"a convention for it"
            )
        signs[label] = -1.0 if negative else 1.0
    mortgage = {
        g: sum(signs[label] * group_value(table, selection, label, g)
               for label in selection.mortgage_labels)
        for g in GROUPS
    }

    all_columns = [n for names in selection.group_columns.values()
                   for n in names]
    deciles = sorted(set(all_columns))
    mean_income = sum(table[selection.income_label][n] for n in deciles) / len(
        deciles
    )
    published_all = table[selection.income_label][selection.all_units_column]

    consumer_units = counts[selection.all_units_column]
    missing_counts = sorted(n for n in deciles if n not in counts)
    if missing_counts:
        raise SelectionProblem(
            f"decile column(s) {', '.join(missing_counts)} carry no "
            f"consumer-unit count"
        )
    decile_units = sum(counts[n] for n in deciles)

    # A group's tenure is the simple mean of its decile columns, exactly as its
    # money is, so the two are aggregated the same way and a reader comparing
    # them is comparing like with like.
    tenure = {
        role: {
            group: sum(by_column[n] for n in selection.group_columns[group])
            / len(selection.group_columns[group])
            for group in GROUPS
        }
        for role, by_column in tenure_columns.items()
    }

    if check_anchors:
        for role, by_column in tenure_columns.items():
            published = by_column[selection.all_units_column]
            average = sum(by_column[n] for n in deciles) / len(deciles)
            if abs(average - published) > TENURE_TOLERANCE:
                raise AnchorProblem(
                    f"{role}: the decile columns average to {average:.3f} "
                    f"against the table's own all-units {published:.3f}"
                )
        for group in GROUPS:
            total = tenure["homeowner"][group] + tenure["renter"][group]
            if abs(total - 1.0) > TENURE_TOLERANCE:
                raise AnchorProblem(
                    f"{group}: homeowner {tenure['homeowner'][group]:.3f} and "
                    f"renter {tenure['renter'][group]:.3f} sum to {total:.3f}. "
                    f"Every consumer unit is one or the other, so a third "
                    f"category has appeared or a row was read from the wrong "
                    f"position"
                )
            if tenure["mortgaged"][group] > tenure["homeowner"][group] + \
                    TENURE_TOLERANCE:
                raise AnchorProblem(
                    f"{group}: {tenure['mortgaged'][group]:.3f} carry a "
                    f"mortgage against {tenure['homeowner'][group]:.3f} who "
                    f"own; the mortgaged are a subset of the owners"
                )
        low, high = CONSUMER_UNIT_BAND
        if not low <= consumer_units <= high:
            raise AnchorProblem(
                f"the table reports {consumer_units:,.0f} consumer units, "
                f"outside [{low:,.0f}, {high:,.0f}]. The published figure is in "
                f"thousands and this reader multiplies by a thousand; a value "
                f"this far out means the unit changed or the wrong row was read"
            )
        # The deciles partition the consumer units, so their counts sum to the
        # all-units count. This is a different check from the income anchor
        # below: that one would still pass if a decile column were read from
        # the wrong position, as long as the ten values it read happened to
        # average correctly.
        if abs(decile_units - consumer_units) > INTERNAL_TOLERANCE * consumer_units:
            raise AnchorProblem(
                f"the decile consumer-unit counts sum to {decile_units:,.0f} "
                f"against the table's own all-units {consumer_units:,.0f}; the "
                f"deciles do not partition the population as read"
            )
        if abs(mean_income - published_all) > INTERNAL_TOLERANCE * published_all:
            raise AnchorProblem(
                f"the decile columns average to {mean_income:,.0f} against the "
                f"table's own all-units {published_all:,.0f}. A column is "
                f"missing or the header row was read at the wrong height"
            )
        if selection.reference_year == REFERENCE_YEAR:
            for key, column_label in (
                ("income_before_taxes", selection.income_label),
                ("total_expenditure", selection.expenditure_label),
            ):
                got = table[column_label][selection.all_units_column]
                want = PUBLISHED_2024[key]
                if abs(got - want) > EXTERNAL_TOLERANCE * want:
                    raise AnchorProblem(
                        f"{key} for all units reads {got:,.0f} against the "
                        f"published {want:,.0f} for reference year "
                        f"{REFERENCE_YEAR}; this is a different vintage"
                    )

    return {
        "reference_year": selection.reference_year,
        "income": income,
        "necessities": necessities,
        "rent": rent,
        "mortgage_payment": mortgage,
        "all_units_income": published_all,
        "decile_mean_income": mean_income,
        #: All consumer units, in units rather than the published thousands.
        #: This is the denominator that turns a Z.1 aggregate into a figure per
        #: household, and it comes from this table so that the household it
        #: divides by is the same consumer unit the income belongs to.
        "consumer_units": consumer_units,
        "consumer_units_by_decile": {n: counts[n] for n in deciles},
        "necessities_by_decile": necessities_by_decile,
        #: ``{role: {group: share}}``. The denominator of every shelter flow
        #: above, and the reason they are read from this table rather than
        #: from a source ranked another way.
        "tenure": tenure,
        #: Which of the owner's two shelter lines the publisher writes negative.
        #: Recorded rather than assumed, so a vintage that changes the
        #: convention shows up in the manifest instead of in the results.
        "mortgage_label_signs": signs,
        "necessity_labels": list(selection.necessity_labels),
        "top_groups_share_a_column": (
            selection.group_columns["next9"] == selection.group_columns["top1"]
        ),
    }
