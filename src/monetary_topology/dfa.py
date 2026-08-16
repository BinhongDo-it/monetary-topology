"""Distributional Financial Accounts, and the one Z.1 ratio stage A1 needs.

``docs/a1_inputs_availability.md`` §1 rules that A1 reads each debt instrument's
distribution across wealth groups from the DFA directly, rather than computing a
mortgage stock as the residual of total liabilities minus consumer credit. That
residual carries the 12.4% of household liabilities which is neither instrument,
and it carries it into the one leg A1-3 rests on.

This module parses. ``data/fetch_dfa.py`` retrieves.

Why nothing here guesses a series identifier
----------------------------------------------
The inputs check verified exactly one of the eight identifiers this stage needs:
``WFRBSB50211``, the bottom 50%'s share of consumer credit, which
``calibration.py`` has carried since A0. The other seven are **unverified**, and
the identifiers follow a pattern regular enough to guess wrongly with confidence:
net worth runs ``WFRBST01134`` / ``WFRBSN09161`` / ``WFRBSN40188`` /
``WFRBSB50215``, a stride of 27 between adjacent groups. A guess that lands on a
real series with the wrong meaning fails silently, which is the worst shape of
error this project catalogues.

So the identifiers come from the publisher. ``fetch_dfa.py --discover``
downloads the DFA archive, enumerates every member and every column, and writes
an inventory. The selection is then pinned in ``data/dfa_series.json``, reviewed
once, and read from there. Nothing in this module contains a series identifier.

The archive turned out to carry no series identifiers at all. It is twenty-four
long-format csv files, one per demographic cut crossed with levels or shares, and
each row is a date, a category, and one column per instrument. So the selection
names a member, a category per group, and a column per instrument, and the eight
identifiers this stage would have had to guess never enter the picture.

**The model's top 1% is the sum of two published categories.** The wealth cut
publishes ``TopPt1`` and ``RemainingTop1`` separately, so a group in the
selection maps to a *list* of category values, summed. Anything that reads
``TopPt1`` alone silently drops nine tenths of the group.

What is checked, and why each check exists
--------------------------------------------
**Shares sum to one, at every date, for every instrument.** A group whose column
was mis-selected or whose series did not resolve leaves a hole, and four numbers
that do not sum to one is the only signal that would show. Silent absorption of a
missing group into the other three is exactly the failure the model's own
``PopulationSpec`` refuses at construction.

**The two Z.1 legs are both named instruments.** ``mortgage_to_consumer_credit``
is one-to-four-family residential mortgages over consumer credit, at the same
quarter, both not seasonally adjusted. The seasonally adjusted twins carry the
same titles and different values, so the fetcher pins the series and this module
checks the published anchor.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

#: The four wealth groups, in the order every vector in this project uses:
#: bottom half first, top 1% last. The strings are the model's names for them,
#: not the publisher's labels; the labels live in ``data/dfa_series.json``.
GROUPS = ("bottom50", "next40", "next9", "top1")

#: The instruments A1 needs distributed. Net worth is included because A0
#: already uses it and reading it here lets the fetcher check its own selection
#: against a vector this repository has held since A0.
INSTRUMENTS = ("consumer_credit", "home_mortgages", "net_worth")

#: Published in ``calibration.py`` since A0, DFA Q1 2026. Used as a selection
#: check rather than as an input: if the net worth vector this module reads does
#: not reproduce these, the selection is wrong and every other vector from the
#: same archive is suspect.
NET_WORTH_ANCHOR_2026Q1 = (0.025, 0.296, 0.363, 0.316)

#: Z.1 2026Q1, NSA, from the S1M.b table: FL153165105 and FL153166000.
Z1_ANCHOR_2026Q1 = {"home_mortgages": 13_821.0, "consumer_credit": 5_073.0}

#: Shares are published to one decimal of a percent, so four of them sum to one
#: only to within rounding. This tolerance admits rounding and refuses a missing
#: group, whose absence would move the sum by at least a whole group's share.
SHARE_SUM_TOLERANCE = 5e-3


class SelectionProblem(ValueError):
    """The archive does not have the shape the pinned selection describes."""


class ShareSumProblem(ValueError):
    """Four group shares do not sum to one, so a group is missing or wrong."""


class AnchorProblem(ValueError):
    """A published value this module checks itself against has moved."""


# ---------------------------------------------------------------------------
# Discovery: what is actually in the archive
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Member:
    name: str
    header: tuple[str, ...]
    first_rows: tuple[tuple[str, ...], ...]
    n_rows: int


def inventory(archive: Path, sample: int = 3) -> list[Member]:
    """Enumerate every csv member with its header and a few rows.

    This is the step that replaces guessing. It writes nothing and decides
    nothing; the selection is pinned by a human after reading it.
    """
    out: list[Member] = []
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not name.lower().endswith(".csv"):
                continue
            text = z.read(name).decode("utf-8-sig", errors="replace")
            rows = list(csv.reader(io.StringIO(text)))
            if not rows:
                out.append(Member(name, (), (), 0))
                continue
            out.append(
                Member(
                    name=name,
                    header=tuple(rows[0]),
                    first_rows=tuple(tuple(r) for r in rows[1 : 1 + sample]),
                    n_rows=len(rows) - 1,
                )
            )
    return out


def format_inventory(members: list[Member]) -> str:
    lines = [f"{len(members)} csv members", ""]
    for member in members:
        lines.append(f"== {member.name}  ({member.n_rows} rows)")
        lines.append("   header: " + " | ".join(member.header))
        for row in member.first_rows:
            lines.append("      row: " + " | ".join(row))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Selection: the pinned mapping from instrument and group to a column
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    """What ``data/dfa_series.json`` says, after a human has read the inventory.

    ``groups`` maps each of this project's four groups to the list of published
    category values that make it up. The list exists because the publisher splits
    the top 1% into ``TopPt1`` and ``RemainingTop1``.
    """

    vintage: str
    source: str
    date: str
    member: str
    date_column: str
    category_column: str
    groups: dict[str, list[str]]
    value_column: dict[str, str]

    @staticmethod
    def load(path: Path) -> Selection:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("member", "date", "date_column", "category_column"):
            if not raw.get(key):
                raise SelectionProblem(f"{path.name} has no {key}")
        missing = [k for k in INSTRUMENTS if not raw.get("value_column", {}).get(k)]
        if missing:
            raise SelectionProblem(
                f"{path.name} has no value column for {', '.join(missing)}"
            )
        absent = [g for g in GROUPS if not raw.get("groups", {}).get(g)]
        if absent:
            raise SelectionProblem(
                f"{path.name} is missing group(s) {', '.join(absent)}; a partial "
                f"vector must fail here rather than be absorbed by the others"
            )
        return Selection(
            vintage=raw["vintage"],
            source=raw["source"],
            date=raw["date"],
            member=raw["member"],
            date_column=raw["date_column"],
            category_column=raw["category_column"],
            groups={g: list(raw["groups"][g]) for g in GROUPS},
            value_column={k: raw["value_column"][k] for k in INSTRUMENTS},
        )


def _rows(archive: Path, selection: Selection) -> list[dict[str, str]]:
    with zipfile.ZipFile(archive) as z:
        if selection.member not in z.namelist():
            raise SelectionProblem(
                f"member {selection.member!r} is not in the archive; run "
                f"--discover"
            )
        text = z.read(selection.member).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    needed = [selection.date_column, selection.category_column,
              *selection.value_column.values()]
    for column in needed:
        if column not in header:
            raise SelectionProblem(
                f"{selection.member}: column {column!r} not present; header is "
                f"{' | '.join(header)}"
            )
    return list(reader)


def read_instrument(
    archive: Path, selection: Selection, instrument: str
) -> dict[str, tuple[float, ...]]:
    """Return ``{date: (bottom50, next40, next9, top1)}`` for one instrument.

    A group is the sum of its listed categories. A listed category absent from a
    date raises rather than contributing zero, because a silent zero is a hole
    the other groups would absorb.
    """
    column = selection.value_column[instrument]
    by_date: dict[str, dict[str, float]] = {}
    for row in _rows(archive, selection):
        date = (row.get(selection.date_column) or "").strip()
        category = (row.get(selection.category_column) or "").strip()
        raw = (row.get(column) or "").strip()
        if not date or not category or not raw:
            continue
        try:
            by_date.setdefault(date, {})[category] = float(raw)
        except ValueError:
            continue

    out: dict[str, tuple[float, ...]] = {}
    for date, categories in by_date.items():
        values = []
        for group in GROUPS:
            wanted = selection.groups[group]
            absent = [c for c in wanted if c not in categories]
            if absent:
                raise SelectionProblem(
                    f"{selection.member}, {instrument} at {date}: category "
                    f"{', '.join(absent)} is not present. The categories at that "
                    f"date are {', '.join(sorted(categories))}"
                )
            values.append(sum(categories[c] for c in wanted))
        out[date] = tuple(values)
    if not out:
        raise SelectionProblem(
            f"{selection.member}: no numeric rows for {column!r}"
        )
    return out


def normalise(values: tuple[float, ...]) -> tuple[float, ...]:
    """Percentages to fractions, leaving fractions alone.

    The DFA publishes shares as percentages. A vector already summing to one is
    passed through, so the same reader survives either convention without a flag
    that could be set the wrong way.
    """
    total = sum(values)
    if abs(total - 1.0) <= SHARE_SUM_TOLERANCE:
        return values
    if abs(total - 100.0) <= SHARE_SUM_TOLERANCE * 100.0:
        return tuple(v / 100.0 for v in values)
    raise ShareSumProblem(
        f"four group shares sum to {total:.6f}, which is neither one nor one "
        f"hundred; a group is missing or the wrong column was selected"
    )


def shares_at(
    archive: Path, selection: Selection, instrument: str, date: str
) -> tuple[float, ...]:
    series = read_instrument(archive, selection, instrument)
    if date not in series:
        available = ", ".join(sorted(series)[-4:])
        raise SelectionProblem(
            f"{instrument}: no row for {date!r}; the last dates present are "
            f"{available}"
        )
    return normalise(series[date])


def validate(
    archive: Path, selection: Selection, date: str
) -> dict[str, tuple[float, ...]]:
    """Read every instrument at one date, check the sums and the anchor."""
    out: dict[str, tuple[float, ...]] = {}
    for instrument in INSTRUMENTS:
        out[instrument] = shares_at(archive, selection, instrument, date)

    net_worth = out["net_worth"]
    for got, want in zip(net_worth, NET_WORTH_ANCHOR_2026Q1, strict=True):
        if abs(got - want) > 1e-3:
            raise AnchorProblem(
                f"net worth shares read as {net_worth}, and calibration.py has "
                f"carried {NET_WORTH_ANCHOR_2026Q1} since A0. Either the "
                f"selection is wrong or the publisher revised; both must be "
                f"looked at rather than absorbed"
            )
    return out


# ---------------------------------------------------------------------------
# The Z.1 aggregate ratio
# ---------------------------------------------------------------------------
def read_fred_csv(text: str) -> dict[str, float]:
    """Parse a keyless ``fredgraph.csv`` payload into ``{date: value}``.

    The first column is the date under either of the two header spellings FRED
    has used; the second is the value, and a missing observation is a dot.
    """
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r]
    if not rows:
        raise ValueError("empty FRED payload")
    header = [c.strip() for c in rows[0]]
    if len(header) < 2:
        raise ValueError(f"unexpected FRED header: {header}")
    out: dict[str, float] = {}
    for row in rows[1:]:
        if len(row) < 2:
            continue
        date, raw = row[0].strip(), row[1].strip()
        if not date or raw in {"", "."}:
            continue
        try:
            out[date] = float(raw)
        except ValueError:
            continue
    if not out:
        raise ValueError("FRED payload carried no observations")
    return out


def mortgage_to_consumer_credit(
    home_mortgages: dict[str, float],
    consumer_credit: dict[str, float],
    date: str,
    anchor: dict[str, float] | None = Z1_ANCHOR_2026Q1,
    anchor_scale: float = 1_000.0,
) -> float:
    """The ratio at one quarter, from two named instruments and no residual.

    ``anchor_scale`` converts the FRED unit (millions) to the unit the Z.1 table
    prints (billions). The anchor check is what catches the seasonally adjusted
    twins, which carry the same titles and different values.
    """
    for name, series in (("home mortgages", home_mortgages),
                         ("consumer credit", consumer_credit)):
        if date not in series:
            last = ", ".join(sorted(series)[-3:])
            raise AnchorProblem(
                f"{name}: no observation at {date!r}; last dates are {last}"
            )
    hm, cc = home_mortgages[date], consumer_credit[date]
    if anchor is not None:
        pairs = (
            ("home_mortgages", hm / anchor_scale),
            ("consumer_credit", cc / anchor_scale),
        )
        for key, got in pairs:
            want = anchor[key]
            if abs(got - want) > 1.0:
                raise AnchorProblem(
                    f"{key} at {date} reads {got:,.1f} bn against the published "
                    f"{want:,.1f} bn. The seasonally adjusted series carry the "
                    f"same titles as the unadjusted ones; check which was pinned"
                )
    if cc <= 0.0:
        raise AnchorProblem("consumer credit is not positive")
    return hm / cc
