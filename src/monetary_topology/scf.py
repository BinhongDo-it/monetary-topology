"""Homeownership by wealth group, computed from the SCF summary extract.

``docs/a1_inputs_availability.md`` §2: **no publisher gives homeownership by net
worth percentile.** The SCF's own Bulletin groups it by usual income; the DFA's
groups match this project's exactly but publish dollars with no household count,
so a share of aggregate real estate is not an ownership rate; Census HVS splits
at the median family income and gives two groups; ACS is income again. The only
route is to compute it, and this module computes it.

This module parses and computes. ``data/fetch_scf.py`` retrieves.

What is computed
------------------
Households are ranked by ``NETWORTH``, weighted, and cut at the 50th, 90th and
99th weighted percentiles to give this project's four groups. Within each group
the ownership rate is the weighted mean of an ownership indicator.

Two properties of this source decide the arithmetic, and both are recorded here
because neither is visible in the output:

**Five implicates per household, and the weight is already divided among them.**
The extract carries five rows per surveyed household, the survey's multiple
imputations: 22,975 rows for 4,595 households in the 2022 wave. The documented
practice for the raw ``X42001`` weight is to pool the five and divide by five,
and **this extract's ``WGT`` column is not that weight**. Measured on the file:
``WGT`` takes five *different* values within every one of the 4,595 households,
and summing it over all 22,975 rows gives 131,306,389, which is the family count
rather than five times it. So the divisor here is **one**, and applying five
would report a fifth of the population.

That error is invisible to both of the anchors below, because a share and a rate
are scale-free. It is caught only by the third check, on the weight total, which
exists for exactly this reason.

**The ownership variable's coding is not assumed.** ``fetch_scf.py --discover``
prints the distinct values of every candidate column with their frequencies, and
the selection pinned in ``data/scf_variables.json`` names which values mean
owning. Nothing here hardcodes a coding.

The two anchors, and what each one catches
--------------------------------------------
**Population shares.** After the cut, the four groups must weigh 0.50, 0.40,
0.09, 0.01 of the population. What this catches is a broken percentile routine:
a cut that assigns on unweighted rank, or that pushes a heavy record wholly into
the group above, breaks the identity immediately.

It is worth stating what it does **not** catch, because the first version of this
docstring claimed more. **A wrong weight column does not break it.** The cut is
defined on the weighted distribution, so whatever the weights are, the groups
come out weighing 0.50, 0.40, 0.09 and 0.01 of the total by construction; a wrong
weight changes *which* households land in each group and leaves the identity
intact. That is `MEASUREMENT.md` checklist item 8 in miniature: this guard would
say the same thing if the thing it guards were broken. A wrong weight column is
caught only by the published overall rate below, and only when it moves it.

**The published overall rate.** The 2022 SCF Bulletin reports primary-residence
holding at **66.1%** of all families. The weighted overall rate computed here
must reproduce it; measured, it is 0.6605. This is what catches an inverted
coding: a selection that reads renting as owning lands near 34% and fails loudly
rather than delivering a K shape upside down.

**The weight total.** After the divisor, the weights must sum to something like a
national family count rather than a fifth or a multiple of one. The band is wide
on purpose: it is not a calibration, and the only error it exists to catch is a
factor of five.

The vintage cost, stated rather than buried
---------------------------------------------
The latest completed wave is **2022**, while every other input in this stage is a
2024 to 2026 vintage. The 2025 wave was fielded from March to December 2025 and
the Board says summary results arrive late in 2026. A1 therefore carries one
input four years older than the rest, and the pre-registration says so.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

#: The four groups, bottom half first, as everywhere else in this project.
GROUPS = ("bottom50", "next40", "next9", "top1")

#: Weighted population share of each group, by construction of the cut. This is
#: an identity rather than a finding, and it is checked because a broken weight
#: or percentile routine breaks it.
POPULATION_SHARES = (0.50, 0.40, 0.09, 0.01)

#: Cut points, as weighted percentiles of net worth.
CUTS = (0.50, 0.90, 0.99)

#: Federal Reserve Bulletin, "Changes in U.S. Family Finances from 2019 to
#: 2022", Table 3: share of all families holding a primary residence.
PUBLISHED_OWNERSHIP_2022 = 0.661

#: Divisor applied to the weight column. **One** for this extract, whose ``WGT``
#: is already split across the five implicates; five would be right for the raw
#: ``X42001``. Pinned in the selection rather than assumed, and checked by the
#: weight total below.
WEIGHT_DIVISOR = 1

#: The weights, after the divisor, must sum to something like a national family
#: count. Wide on purpose: the only error this catches is a factor of five, and a
#: narrow band here would be a calibration nobody registered.
POPULATION_BAND = (100_000_000.0, 160_000_000.0)

POPULATION_TOLERANCE = 5e-3
OWNERSHIP_TOLERANCE = 1.5e-2


class SelectionProblem(ValueError):
    """The extract does not have the shape the pinned selection describes."""


class AnchorProblem(ValueError):
    """A computed quantity does not reproduce a published one."""


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Column:
    name: str
    n_values: int
    common: tuple[tuple[str, int], ...]


def read_rows(archive: Path, member: str | None = None) -> list[dict[str, str]]:
    """Read the one csv in the summary-extract archive."""
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if member is None:
            if len(names) != 1:
                raise SelectionProblem(
                    f"expected one csv in the archive, found {len(names)}: "
                    f"{', '.join(names) or 'none'}"
                )
            member = names[0]
        elif member not in z.namelist():
            raise SelectionProblem(f"member {member!r} is not in the archive")
        text = z.read(member).decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise SelectionProblem(f"{member}: no rows")
    return rows


def profile(
    rows: list[dict[str, str]], patterns: tuple[str, ...] = ("HOUS", "NETWORTH",
                                                             "X42001", "WGT")
) -> list[Column]:
    """Distinct values and frequencies for the columns a selection might name.

    This is the step that settles a coding rather than assuming one. A variable
    whose values are ``0`` and ``1`` says nothing about which one owns; the
    frequencies do, once they are read next to a published rate.
    """
    header = list(rows[0])
    wanted = [c for c in header if any(p in c.upper() for p in patterns)]
    out: list[Column] = []
    for name in wanted:
        counts = Counter((r.get(name) or "").strip() for r in rows)
        out.append(
            Column(
                name=name,
                n_values=len(counts),
                common=tuple(counts.most_common(12)),
            )
        )
    return out


def format_profile(columns: list[Column], header: list[str], n_rows: int) -> str:
    lines = [
        f"{n_rows} rows, {len(header)} columns",
        "",
        "candidate columns, with their most common values:",
        "",
    ]
    for column in columns:
        lines.append(f"== {column.name}  ({column.n_values} distinct)")
        for value, count in column.common:
            lines.append(f"      {value!r:>16}  {count}")
        lines.append("")
    lines.append("full header:")
    lines.append(" | ".join(header))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    """What ``data/scf_variables.json`` says, after a human has read the profile."""

    wave: str
    source: str
    weight_column: str
    networth_column: str
    ownership_column: str
    owning_values: tuple[str, ...]
    weight_divisor: int = WEIGHT_DIVISOR
    member: str | None = None

    @staticmethod
    def load(path: Path) -> Selection:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("wave", "weight_column", "networth_column",
                    "ownership_column"):
            if not raw.get(key):
                raise SelectionProblem(f"{path.name} has no {key}")
        owning = raw.get("owning_values") or []
        if not owning:
            raise SelectionProblem(
                f"{path.name} has no owning_values; the coding of "
                f"{raw['ownership_column']!r} must be read from the profile "
                f"rather than assumed"
            )
        return Selection(
            wave=raw["wave"],
            source=raw.get("source", ""),
            weight_column=raw["weight_column"],
            networth_column=raw["networth_column"],
            ownership_column=raw["ownership_column"],
            owning_values=tuple(str(v) for v in owning),
            weight_divisor=int(raw.get("weight_divisor", WEIGHT_DIVISOR)),
            member=raw.get("member") or None,
        )


@dataclass(frozen=True)
class Record:
    weight: float
    networth: float
    owns: bool


def extract(rows: list[dict[str, str]], selection: Selection) -> list[Record]:
    header = list(rows[0])
    for column in (selection.weight_column, selection.networth_column,
                   selection.ownership_column):
        if column not in header:
            raise SelectionProblem(
                f"column {column!r} is not in the extract; the profile lists "
                f"{len(header)} columns"
            )
    if selection.weight_divisor < 1:
        raise SelectionProblem("weight_divisor must be at least one")

    out: list[Record] = []
    seen_owning = 0
    for row in rows:
        try:
            weight = float(row[selection.weight_column]) / selection.weight_divisor
            networth = float(row[selection.networth_column])
        except (TypeError, ValueError):
            continue
        if weight <= 0.0:
            continue
        value = (row.get(selection.ownership_column) or "").strip()
        owns = value in selection.owning_values
        seen_owning += owns
        out.append(Record(weight=weight, networth=networth, owns=owns))
    if not out:
        raise SelectionProblem("no usable rows under the selection")
    if seen_owning == 0:
        raise SelectionProblem(
            f"no row carries any of owning_values {selection.owning_values} in "
            f"{selection.ownership_column!r}; the coding in the selection does "
            f"not match the file"
        )
    return out


# ---------------------------------------------------------------------------
# The computation
# ---------------------------------------------------------------------------
def assign_groups(records: list[Record]) -> list[list[Record]]:
    """Cut the weighted net worth distribution at the 50th, 90th and 99th."""
    ordered = sorted(records, key=lambda r: r.networth)
    total = sum(r.weight for r in ordered)
    if total <= 0.0:
        raise SelectionProblem("total weight is not positive")

    groups: list[list[Record]] = [[] for _ in GROUPS]
    cumulative = 0.0
    for record in ordered:
        # The share at the midpoint of this record's weight, so a single very
        # heavy record cannot be pushed wholly into the group above.
        position = (cumulative + 0.5 * record.weight) / total
        index = sum(1 for cut in CUTS if position >= cut)
        groups[index].append(record)
        cumulative += record.weight
    return groups


def population_shares(groups: list[list[Record]]) -> tuple[float, ...]:
    total = sum(r.weight for g in groups for r in g)
    return tuple(sum(r.weight for r in g) / total for g in groups)


def ownership_rate(records: list[Record]) -> float:
    total = sum(r.weight for r in records)
    if total <= 0.0:
        return 0.0
    return sum(r.weight for r in records if r.owns) / total


def homeownership_by_group(
    rows: list[dict[str, str]],
    selection: Selection,
    check_anchors: bool = True,
) -> dict[str, object]:
    """The four rates, with both anchors checked before they are returned."""
    records = extract(rows, selection)
    groups = assign_groups(records)
    shares = population_shares(groups)
    rates = tuple(ownership_rate(g) for g in groups)
    overall = ownership_rate(records)

    population = sum(r.weight for r in records)

    if check_anchors:
        low, high = POPULATION_BAND
        if not low <= population <= high:
            raise AnchorProblem(
                f"the weights sum to {population:,.0f} after a divisor of "
                f"{selection.weight_divisor}, outside the band "
                f"[{low:,.0f}, {high:,.0f}]. This extract's WGT is already split "
                f"across the five implicates, so the divisor is one; neither the "
                f"share check nor the rate check can see this error"
            )
        for group, got, want in zip(GROUPS, shares, POPULATION_SHARES,
                                    strict=True):
            if abs(got - want) > POPULATION_TOLERANCE:
                raise AnchorProblem(
                    f"{group} weighs {got:.4f} of the population against the "
                    f"{want:.2f} the cut defines. The weight column, the "
                    f"implicate divisor or the percentile routine is wrong"
                )
        if abs(overall - PUBLISHED_OWNERSHIP_2022) > OWNERSHIP_TOLERANCE:
            raise AnchorProblem(
                f"overall ownership computes to {overall:.4f} against the "
                f"published {PUBLISHED_OWNERSHIP_2022:.3f}. An inverted coding "
                f"lands near {1 - PUBLISHED_OWNERSHIP_2022:.3f}; check "
                f"owning_values before trusting any group rate"
            )

    return {
        "wave": selection.wave,
        "rates": rates,
        "population_shares": shares,
        "overall": overall,
        "records": len(records),
        "weighted_population": population,
    }
