"""Income, net worth and the household balance sheet, from one joint.

``monetary_topology.scf`` reads one margin of this file: homeownership by
net-worth percentile. This module reads the **joint**, and it exists because of
a defect the joint is the only thing that can fix.

What went wrong without it
----------------------------
Stage A1 built its population by crossing marginals. Income, the basket, the
rents and housing tenure came from the CEX by income decile; consumer credit and
mortgage debt came from the DFA by net-worth group; and every household inside a
net-worth group was given that group's *average* debt. Nothing in that
construction knows how debt and income covary inside a group, because neither
source says.

Two consequences, and the second is the one that matters:

**The cells the model refused were cells it had invented.** The permutation arm
put 2.7% of the next-9%-by-wealth households into the bottom half by income and
handed them their wealth group's average consumer credit. Their published debt
then exceeded what their published income could service, and the constructor
raised. That refusal was read as a finding about the data. It was not: the cell
is a crossing of two margins, and its numbers are not published for anyone.

**A rule about published groups was applied to constructed cells.**
``docs/a1_prereg.md`` §2.6 says a group that cannot service its published debt
out of its published disposable raises rather than rescales, because that would
be the data speaking. The rule is right and its scope was not stated: it holds
for a group a publisher actually reports, and it says nothing about a cell made
by crossing two rankings. In the marginal-crossing construction **every**
stratum is such a cell, so the rule had no purchase anywhere in it.

What this module reads instead
--------------------------------
The Survey of Consumer Finances summary extract carries, for the same household
and with one weight: income, net worth, housing tenure, whether a mortgage is
outstanding, the mortgage balance and payment, the rent paid, credit card
balances and vehicle instalment debt. That is a joint distribution rather than
two margins, so the debt a low-income household in a high-wealth group carries
is **measured** rather than assumed to be its group's average.

Everything here is per household and weighted. Nothing is scaled to an external
aggregate: where the SCF and the financial accounts disagree, the disagreement
is reported by the caller and is not absorbed here.

Six anchors, checked before any figure is returned
----------------------------------------------------
**The weights sum to a national family count.** The extract splits ``WGT``
across five implicates, so a divisor of five would report a fifth of the
population and no scale-free quantity would notice.

**Both rankings cut where they are asked to.** The net-worth and the income cuts
must each put 50%, 40%, 9% and 1% of the weight in their four groups. This is
the check that the ranking variable is the one intended: a column of codes
rather than dollars would still sort and would not land on those shares.

**The published overall homeownership rate is reproduced.** ``scf.py`` already
uses this and it is repeated here because this module cuts the file its own way.

**Income is annual and rent is monthly**, and each is banded. The extract mixes
the two periods and converting one and not the other makes a household pay a
year's rent every month, which no ratio downstream can see.

**The three published payments sum to the published total**, exactly, on every
row. Revolving, instalment and mortgage are given separately and so is their
sum, so reading the fourth column costs nothing and pins all four to one unit
and one period.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from monetary_topology.scf import (
    CUTS,
    GROUPS,
    OWNERSHIP_TOLERANCE,
    POPULATION_BAND,
    POPULATION_SHARES,
    POPULATION_TOLERANCE,
    AnchorProblem,
    SelectionProblem,
    read_rows,
)

#: Published in the 2022 Bulletin, and the anchor ``scf.py`` already uses.
PUBLISHED_OWNERSHIP = 0.661

#: The extract publishes income annually and its rents and payments monthly.
#: Converting one and not the other makes a household pay a year's rent every
#: month, and no scale-free quantity would notice, so both units are banded.
#: Annual family income near 141,000; monthly would be near 11,800.
INCOME_BAND = (50_000.0, 400_000.0)
#: Monthly rent per renter near 1,174; annual would be near 14,000.
RENT_BAND = (200.0, 6_000.0)
#: The three published payments must sum to the published total, per household.
PAYMENT_IDENTITY_TOLERANCE = 1.0
#: ``docs/a1d_prereg.md`` §3's cushion must nest inside financial assets, which
#: must nest inside all assets, on every row. A **relational** anchor and not a
#: band: it pins ``LIQ`` as a dollar stock that is a component of ``FIN``, so it
#: catches a share column, a flow, or a column that is not what it is named,
#: without reading a level. The registration is explicit that no level of this
#: column had been read when the design was fixed, and a band would have needed
#: one.
NESTING_COLUMNS = ("FIN", "ASSET")
NESTING_TOLERANCE = 1.0


@dataclass(frozen=True)
class JointSelection:
    """Which columns carry which quantity. Pinned by a human from the profile.

    Nothing here has a default beyond the weight divisor. Every column decides
    part of the answer, and a module that guessed one would be inventing the
    covariance this whole file exists to measure.
    """

    wave: str
    source: str
    weight_column: str
    networth_column: str
    income_column: str
    ownership_column: str
    owning_values: tuple[str, ...]
    #: Positive means an outstanding mortgage. Read rather than derived from
    #: tenure, because an owner without a mortgage is a third tenure and the
    #: whole shelter rung turns on the distinction.
    mortgage_debt_column: str
    mortgage_payment_column: str
    rent_column: str
    #: The two consumer-credit legs the cascade models. Student debt is a third
    #: leg in the financial accounts and is **not** summed in here: it has no
    #: rung in this stage, and folding it into the card and car service would
    #: charge households a payment on an obligation the model never gives them.
    card_column: str
    vehicle_column: str
    #: The **measured** monthly payments. The extract publishes what each class
    #: is actually paid, so the card rung needs no minimum-payment rate: the
    #: published revolving payment is 3.7% of the revolving balance a month
    #: against the 2% this project cited from practice.
    card_payment_column: str
    #: Vehicles, education and other together. The vehicle leg cannot be split
    #: out of it, so that one payment keeps a literature rate on a measured
    #: balance; this column is read to check that rate rather than to apply it.
    instalment_payment_column: str
    #: The sum of the three, published separately. Reading it costs nothing and
    #: buys the one anchor that pins every payment to the same unit and period:
    #: revolving plus instalment plus mortgage must equal it, exactly.
    total_payment_column: str
    #: Liquid assets, the model's cushion under ``docs/a1d_prereg.md`` §3.
    #: Checking, savings, money market and call accounts, and nothing else:
    #: retirement is a separate column and is registered as unreachable inside
    #: a month, and no non-financial asset is in it. **Optional on the
    #: selection**, because A1b was built and scored without it and a stage
    #: that never asks for a cushion must still be able to read this file.
    liquid_column: str = ""
    weight_divisor: int = 1
    member: str | None = None
    #: Columns read and reported without entering any computed quantity.
    extra_columns: tuple[str, ...] = ()

    @staticmethod
    def load(path: Path) -> JointSelection:
        raw = json.loads(path.read_text(encoding="utf-8"))
        required = (
            "wave", "weight_column", "networth_column", "income_column",
            "ownership_column", "mortgage_debt_column",
            "mortgage_payment_column", "rent_column", "card_column",
            "vehicle_column", "card_payment_column",
            "instalment_payment_column", "total_payment_column",
        )
        for key in required:
            if not raw.get(key):
                raise SelectionProblem(f"{path.name} has no {key}")
        owning = raw.get("owning_values") or []
        if not owning:
            raise SelectionProblem(
                f"{path.name} has no owning_values; the coding of "
                f"{raw['ownership_column']!r} must be read from the profile"
            )
        return JointSelection(
            wave=raw["wave"],
            source=raw.get("source", ""),
            weight_column=raw["weight_column"],
            networth_column=raw["networth_column"],
            income_column=raw["income_column"],
            ownership_column=raw["ownership_column"],
            owning_values=tuple(str(v) for v in owning),
            mortgage_debt_column=raw["mortgage_debt_column"],
            mortgage_payment_column=raw["mortgage_payment_column"],
            rent_column=raw["rent_column"],
            card_column=raw["card_column"],
            vehicle_column=raw["vehicle_column"],
            card_payment_column=raw["card_payment_column"],
            instalment_payment_column=raw["instalment_payment_column"],
            total_payment_column=raw["total_payment_column"],
            liquid_column=raw.get("liquid_column", "") or "",
            weight_divisor=int(raw.get("weight_divisor", 1)),
            member=raw.get("member") or None,
            extra_columns=tuple(raw.get("extra_columns", ())),
        )


@dataclass(frozen=True)
class Respondent:
    weight: float
    networth: float
    income: float
    owns: bool
    mortgage_debt: float
    mortgage_payment: float
    rent: float
    card: float
    vehicle: float
    card_payment: float
    instalment_payment: float
    total_payment: float
    #: Liquid assets. Zero when the selection names no column, which is what a
    #: stage built before ``docs/a1d_prereg.md`` sees, and a stage that wants a
    #: measured cushion must check the column is named rather than read this
    #: and get a population with no cushion at all.
    liquid: float = 0.0
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def mortgaged(self) -> bool:
        return self.owns and self.mortgage_debt > 0.0

    @property
    def outright(self) -> bool:
        return self.owns and self.mortgage_debt <= 0.0

    @property
    def consumer_credit(self) -> float:
        return self.card + self.vehicle


def _number(row: dict[str, str], column: str) -> float:
    try:
        return float(row[column])
    except (KeyError, TypeError, ValueError):
        return 0.0


def extract(rows: list[dict[str, str]],
            selection: JointSelection) -> list[Respondent]:
    """One record per implicate row, refusing a column that is not there."""
    header = list(rows[0])
    needed = (
        selection.weight_column, selection.networth_column,
        selection.income_column, selection.ownership_column,
        selection.mortgage_debt_column, selection.mortgage_payment_column,
        selection.rent_column, selection.card_column, selection.vehicle_column,
        selection.card_payment_column, selection.instalment_payment_column,
        selection.total_payment_column,
        *((selection.liquid_column,) if selection.liquid_column else ()),
        *selection.extra_columns,
    )
    missing = [c for c in needed if c not in header]
    if missing:
        raise SelectionProblem(
            f"column(s) {', '.join(missing)} are not in the extract, which "
            f"carries {len(header)} columns"
        )
    if selection.weight_divisor < 1:
        raise SelectionProblem("weight_divisor must be at least one")

    out: list[Respondent] = []
    for row in rows:
        weight = _number(row, selection.weight_column) / selection.weight_divisor
        if weight <= 0.0:
            continue
        value = (row.get(selection.ownership_column) or "").strip()
        out.append(Respondent(
            weight=weight,
            networth=_number(row, selection.networth_column),
            income=_number(row, selection.income_column),
            owns=value in selection.owning_values,
            mortgage_debt=_number(row, selection.mortgage_debt_column),
            mortgage_payment=_number(row, selection.mortgage_payment_column),
            rent=_number(row, selection.rent_column),
            card=_number(row, selection.card_column),
            vehicle=_number(row, selection.vehicle_column),
            card_payment=_number(row, selection.card_payment_column),
            instalment_payment=_number(row,
                                       selection.instalment_payment_column),
            total_payment=_number(row, selection.total_payment_column),
            liquid=(_number(row, selection.liquid_column)
                    if selection.liquid_column else 0.0),
            extra={c: _number(row, c) for c in selection.extra_columns},
        ))
    if not out:
        raise SelectionProblem("no usable rows under the selection")
    if selection.liquid_column:
        _check_nesting(out, selection)
    return out


def _check_nesting(people: list[Respondent],
                   selection: JointSelection) -> None:
    """``0 <= LIQ <= FIN <= ASSET`` on every row, or refuse the column.

    Placed here rather than in :func:`joint` because the cushion is read by a
    stage that never builds the sixteen cells, and an anchor a stage does not
    reach is `MEASUREMENT.md` failure mode 9: a guard nothing runs.

    The chain is checked in the order it nests, so the message names the link
    that broke rather than the whole chain.
    """
    have = [c for c in NESTING_COLUMNS if c in (people[0].extra or {})]
    if len(have) != len(NESTING_COLUMNS):
        raise SelectionProblem(
            f"{selection.liquid_column} is selected as the cushion but "
            f"{', '.join(c for c in NESTING_COLUMNS if c not in have)} is not "
            f"in extra_columns, so the nesting anchor cannot run. A cushion "
            f"read without it is a column taken on its name"
        )
    negative = sum(1 for p in people if p.liquid < 0.0)
    if negative:
        raise SelectionProblem(
            f"{negative} of {len(people)} rows carry a negative "
            f"{selection.liquid_column}; a cash balance is not signed and this "
            f"column is not the one intended"
        )
    chain = ("liquid", *NESTING_COLUMNS)

    def value(p: Respondent, name: str) -> float:
        return p.liquid if name == "liquid" else p.extra[name]

    for inner, outer in zip(chain[:-1], chain[1:], strict=True):
        broken = sum(1 for p in people
                     if value(p, inner) > value(p, outer) + NESTING_TOLERANCE)
        if broken:
            low = (selection.liquid_column if inner == "liquid" else inner)
            raise SelectionProblem(
                f"{broken} of {len(people)} rows have {low} above {outer}. "
                f"The cushion must nest inside financial assets, which must "
                f"nest inside all assets; one of these columns is not what "
                f"its name says"
            )


def rank_by(households: list[Respondent], key: str,
            cuts: tuple[float, ...]) -> list[int]:
    """The bin index of each household under one ranking, in input order.

    The position is taken at the midpoint of a record's own weight, the same
    rule ``scf.assign_groups`` uses, so one heavy record cannot be pushed whole
    into the bin above by an arbitrary tie-break.
    """
    order = sorted(range(len(households)),
                   key=lambda i: getattr(households[i], key))
    total = sum(h.weight for h in households)
    if total <= 0.0:
        raise SelectionProblem("total weight is not positive")
    index = [0] * len(households)
    cumulative = 0.0
    for i in order:
        weight = households[i].weight
        position = (cumulative + 0.5 * weight) / total
        index[i] = sum(1 for cut in cuts if position >= cut)
        cumulative += weight
    return index


#: Ten equal bins, for the one input published by decile.
DECILE_CUTS = tuple(i / 10.0 for i in range(1, 10))


def rank_groups(households: list[Respondent], key: str) -> list[int]:
    """The group index of each household under one ranking, in input order.

    The position is taken at the midpoint of a record's own weight, the same
    rule ``scf.assign_groups`` uses, so one heavy record cannot be pushed whole
    into the group above by an arbitrary tie-break.
    """
    return rank_by(households, key, CUTS)


def _weighted(values: list[tuple[float, float]]) -> float:
    total = sum(w for w, _ in values)
    return sum(w * v for w, v in values) / total if total > 0.0 else 0.0


@dataclass
class Cell:
    """One (net-worth group, income group) cell, entirely measured."""

    wealth: int
    income: int
    weight: float
    share_of_population: float
    share_of_wealth_group: float
    mean_income: float
    mean_card: float
    mean_vehicle: float
    mean_consumer_credit: float
    renter_share: float
    mortgaged_share: float
    outright_share: float
    rent_per_renter: float
    payment_per_mortgaged: float
    mortgage_debt_per_mortgaged: float
    households: int

    def as_dict(self) -> dict[str, object]:
        return {
            "wealth": GROUPS[self.wealth],
            "income": GROUPS[self.income],
            "weight": self.weight,
            "share_of_population": self.share_of_population,
            "share_of_wealth_group": self.share_of_wealth_group,
            "mean_income": self.mean_income,
            "mean_card": self.mean_card,
            "mean_vehicle": self.mean_vehicle,
            "mean_consumer_credit": self.mean_consumer_credit,
            "renter_share": self.renter_share,
            "mortgaged_share": self.mortgaged_share,
            "outright_share": self.outright_share,
            "rent_per_renter": self.rent_per_renter,
            "payment_per_mortgaged": self.payment_per_mortgaged,
            "mortgage_debt_per_mortgaged": self.mortgage_debt_per_mortgaged,
            "households": self.households,
        }


def joint(households: list[Respondent],
          check_anchors: bool = True) -> dict[str, object]:
    """The sixteen cells, plus both margins and the anchors that guard them."""
    wealth = rank_groups(households, "networth")
    income = rank_groups(households, "income")
    total = sum(h.weight for h in households)

    if check_anchors:
        low, high = POPULATION_BAND
        if not low <= total <= high:
            raise AnchorProblem(
                f"the weights sum to {total:,.0f}, outside "
                f"[{low:,.0f}, {high:,.0f}]. The extract splits its weight "
                f"across five implicates and the divisor decides the scale"
            )
        for name, index in (("net worth", wealth), ("income", income)):
            for group, want in enumerate(POPULATION_SHARES):
                got = sum(h.weight for h, g in zip(households, index,
                                                   strict=True) if g == group)
                if abs(got / total - want) > POPULATION_TOLERANCE:
                    raise AnchorProblem(
                        f"the {name} ranking puts {got / total:.4f} of the "
                        f"weight in {GROUPS[group]} against {want:.2f}; the "
                        f"column being cut is not the one intended"
                    )
        owning = sum(h.weight for h in households if h.owns) / total
        if abs(owning - PUBLISHED_OWNERSHIP) > OWNERSHIP_TOLERANCE:
            raise AnchorProblem(
                f"overall homeownership reads {owning:.4f} against the "
                f"published {PUBLISHED_OWNERSHIP}"
            )
        # The unit anchors. Both are one line and both catch the error that no
        # ratio downstream could see.
        mean_income = _weighted([(h.weight, h.income) for h in households])
        low, high = INCOME_BAND
        if not low <= mean_income <= high:
            raise AnchorProblem(
                f"mean family income reads {mean_income:,.0f}, outside "
                f"[{low:,.0f}, {high:,.0f}]. This column is annual and the "
                f"payments beside it are monthly"
            )
        renters = [h for h in households if not h.owns]
        mean_rent = _weighted([(h.weight, h.rent) for h in renters])
        low, high = RENT_BAND
        if not low <= mean_rent <= high:
            raise AnchorProblem(
                f"mean rent per renter reads {mean_rent:,.0f}, outside "
                f"[{low:,.0f}, {high:,.0f}]. This column is monthly and the "
                f"income beside it is annual"
            )
        # Revolving plus instalment plus mortgage is published separately as a
        # total, and the identity holds exactly on every row of the 2022 wave.
        # It pins all four to one unit and one period at no cost.
        broken = sum(
            1 for h in households
            if abs(h.card_payment + h.instalment_payment + h.mortgage_payment
                   - h.total_payment) > PAYMENT_IDENTITY_TOLERANCE
        )
        if broken:
            raise AnchorProblem(
                f"{broken} of {len(households)} rows break the identity "
                f"revolving + instalment + mortgage = total payment; the four "
                f"columns are not one unit and one period"
            )

    cells: list[Cell] = []
    for w in range(len(GROUPS)):
        wealth_weight = sum(h.weight for h, g in zip(households, wealth,
                                                     strict=True) if g == w)
        for i in range(len(GROUPS)):
            members = [h for h, gw, gi in zip(households, wealth, income,
                                              strict=True)
                       if gw == w and gi == i]
            weight = sum(h.weight for h in members)
            renters = [h for h in members if not h.owns]
            mortgaged = [h for h in members if h.mortgaged]
            cells.append(Cell(
                wealth=w,
                income=i,
                weight=weight,
                share_of_population=weight / total if total else 0.0,
                share_of_wealth_group=(weight / wealth_weight
                                       if wealth_weight else 0.0),
                mean_income=_weighted([(h.weight, h.income) for h in members]),
                mean_card=_weighted([(h.weight, h.card) for h in members]),
                mean_vehicle=_weighted([(h.weight, h.vehicle)
                                        for h in members]),
                mean_consumer_credit=_weighted(
                    [(h.weight, h.consumer_credit) for h in members]
                ),
                renter_share=(sum(h.weight for h in renters) / weight
                              if weight else 0.0),
                mortgaged_share=(sum(h.weight for h in mortgaged) / weight
                                 if weight else 0.0),
                outright_share=(sum(h.weight for h in members if h.outright)
                                / weight if weight else 0.0),
                rent_per_renter=_weighted([(h.weight, h.rent)
                                           for h in renters]),
                payment_per_mortgaged=_weighted(
                    [(h.weight, h.mortgage_payment) for h in mortgaged]
                ),
                mortgage_debt_per_mortgaged=_weighted(
                    [(h.weight, h.mortgage_debt) for h in mortgaged]
                ),
                households=len(members),
            ))

    def margin(index: list[int], attribute: str) -> list[float]:
        out = []
        for group in range(len(GROUPS)):
            members = [h for h, g in zip(households, index, strict=True)
                       if g == group]
            out.append(_weighted([(h.weight, getattr(h, attribute))
                                  for h in members]))
        return out

    return {
        "weighted_families": total,
        "records": len(households),
        "overall_ownership": sum(h.weight for h in households if h.owns) / total,
        "cells": [c.as_dict() for c in cells],
        "consumer_credit_by_wealth": margin(wealth, "consumer_credit"),
        "consumer_credit_by_income": margin(income, "consumer_credit"),
        "income_by_wealth": margin(wealth, "income"),
        "aggregate_card": sum(h.weight * h.card for h in households),
        "aggregate_vehicle": sum(h.weight * h.vehicle for h in households),
        "aggregate_mortgage": sum(h.weight * h.mortgage_debt
                                  for h in households),
    }


def read_respondents(archive: Path,
                     selection: JointSelection) -> list[Respondent]:
    """The records themselves, for a stage that builds a household per record."""
    return extract(read_rows(archive, selection.member), selection)


def read_joint(archive: Path, selection: JointSelection,
               check_anchors: bool = True) -> dict[str, object]:
    rows = read_rows(archive, selection.member)
    return joint(extract(rows, selection), check_anchors)
