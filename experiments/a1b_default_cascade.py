"""A1b: the default cascade on a measured population. Evaluates, designs nothing.

Registered in ``docs/a1b_prereg.md``. The mechanism is A1's and is not
re-derived; what changes is where a household's balance sheet comes from.

Usage::

    python experiments/a1b_default_cascade.py
    python experiments/a1b_default_cascade.py --households 200000
    python experiments/a1b_default_cascade.py --records    # print and stop
    python experiments/a1b_default_cascade.py --carrier registered

Writes ``results/a1b_default_cascade.json``.

**This file is being written in parts and says so.** ``complete: false`` stands
until every criterion of §5 is in it, and the driver names the ones that are not.

Where every number comes from
-------------------------------
One archive and one table:

* ``data/raw/scfp2022excel.zip``, read by ``monetary_topology.scf_joint`` under
  ``data/scf_joint_variables.json``. Income, net worth, tenure, the rent, the
  mortgage, card and vehicle balances and the published payment columns, all
  from the same respondent under one weight.
* ``data/processed/cex_necessities_by_decile.csv`` for the necessities basket
  alone, assigned **by income rank** (``docs/a1b_prereg.md`` §2.2). It is the
  one field taken from outside the respondent, because the SCF collects food at
  home and neither utilities, healthcare nor commuting.

Each rung stands on the payment of its own stock (ruled 2026-10-17): the card
rung on the publisher's 2.5% of the card balance, the mortgage rung on the
payments on the loans the mortgage balance counts (``PAYMORT1`` to
``PAYMORT3``), the car-loan rung on the vehicle payments the extract carries
loan by loan. Every other published payment the respondent makes is carried as
an outflow on no rung: the rest of the revolving payment (buy-now-pay-later and
the lines of credit not secured by the residence), the rest of ``MORTPAY``
(other residential property, land contracts, the primary residence's
home-equity lines, and all of it on a household with no mortgage rung), and a
vehicle payment on a household with no vehicle balance. ``--carrier
registered`` runs the construction the stage was registered on: the whole
revolving payment on the card rung, the whole ``MORTPAY`` on the mortgage rung,
one sixtieth of the vehicle balance on the car-loan rung, and nothing on no
rung. The default run reads that construction as an arm beside it.

Nothing is drawn. The population is a deterministic largest-remainder allocation
of the weights, so this stage has **no seed**, and the service-share dispersion
that A1 needed is not a parameter here at all.

What this file must not do
----------------------------
It must not drop a household. Some records owe more each month than they take
in, and A1's constructor made that impossible; here it is reported by
:func:`baseline_stress` and the zero calibration is a constancy rather than a
zero (§3 of the pre-registration). Selecting on baseline stress would be
selecting on the outcome the stage is about.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.cascade import (  # noqa: E402
    PAYMENT_RATE,
    CascadeModel,
    CascadeSpec,
    CostRule,
    Cushion,
    HouseholdRecord,
    Obligation,
    Tenure,
    allocate,
    baseline_stress,
    build_from_records,
    distinct_records,
    literature_parameters,
)
from monetary_topology.income_path import (  # noqa: E402
    PathSpec,
    describe,
    retention_path,
)
from dataclasses import dataclass, fields, replace  # noqa: E402

from monetary_topology.scf import GROUPS  # noqa: E402
from monetary_topology.scf_joint import (  # noqa: E402
    DECILE_CUTS,
    JointSelection,
    Respondent,
    rank_by,
    rank_groups,
    read_respondents,
)

PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
ARCHIVE = ROOT / "data" / "raw" / "scfp2022excel.zip"
SELECTION = ROOT / "data" / "scf_joint_variables.json"

#: An estimation setting, not a behavioural one, on the same licence A1-10
#: registers: households do not interact. Large enough that most records get a
#: copy, which the coverage line reports.
DEFAULT_HOUSEHOLDS = 100_000

#: §A1-11, one lower than A1's because the service-share dispersion is measured
#: here rather than chosen.
FREE_PARAMETER_BOUND = 12

ZERO_PERIODS = 24
#: The unrelieved no-shock run, reported as the baseline. Long enough that the
#: slowest clock in the cost rule, the twelve-month foreclosure one, has run
#: out twice. It is a series and it does not settle; see A1b-0.
BASELINE_PERIODS = 60


class InputProblem(ValueError):
    """A retrieved file is absent, or is not the shape this stage reads."""


class Criterion:
    def __init__(self, name: str, passed: bool, detail: str,
                 void: bool = False) -> None:
        self.name, self.passed, self.detail, self.void = (
            name, passed, detail, void
        )

    def line(self) -> str:
        mark = "VOID" if self.void else ("pass" if self.passed else "FAIL")
        return f"  {mark}  {self.name}\n        {self.detail}"


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
def basket_by_decile() -> tuple[float, ...]:
    """The CEX basket, annual, by income decile. Ten values, publication order.

    Assigned to a household by the **rank** of its income and never by its
    level. ``docs/a1b_prereg.md`` §2.2: the two sources' income levels differ by
    a third, the SCF's better coverage of the top being the documented reason,
    so a rank is comparable across them and a dollar figure is not.

    **A decile and not a group.** The first run of this stage assigned the
    four-group mean, and 89% of its baseline stress was households whose basket
    plus shelter alone exceeded their income. A group mean handed to a household
    far below its group is not that household's outlay: the CEX measures
    expenditure, and a poorer household's measured expenditure is lower. The
    decile is the finest cut this table publishes; what is left is within-decile
    variation, which it does not publish and which this stage reports rather
    than invents.
    """
    path = PROCESSED / "cex_necessities_by_decile.csv"
    if not path.exists():
        raise InputProblem(
            f"{path.name} is absent; run data/fetch_cex.py. This stage measures "
            f"everything else on the respondent and still needs the basket"
        )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda r: int(r["decile"]))
    if len(rows) != 10:
        raise InputProblem(
            f"{path.name} has {len(rows)} rows; the table publishes ten deciles"
        )
    return tuple(float(r["necessities"]) for r in rows)


def tenure_of(person: Respondent) -> Tenure:
    """The tenure a respondent is built at."""
    if person.owns:
        return Tenure.MORTGAGED if person.mortgaged else Tenure.OUTRIGHT
    return Tenure.RENTER


def to_records(respondents: list[Respondent],
               basket_annual: tuple[float, ...],
               carrier: str | None = None) -> list[HouseholdRecord]:
    """One record per respondent, in the model's units.

    ``carrier`` says which payment each rung stands on, and is
    :data:`CARRIER_MATCHED` unless a run asks for :data:`CARRIER_REGISTERED`.
    See :func:`matched_payments`.

    Two rankings are taken here and they are different things. ``group`` is the
    **net-worth** group and is what the criteria report by. The basket is taken
    by the household's own **income decile**, because that is the ranking and
    the cut the CEX publishes on. Using the wealth ranking for both would put
    the mismatch this whole stage exists to remove straight back in.
    """
    wealth = rank_groups(respondents, "networth")
    decile = rank_by(respondents, "income", DECILE_CUTS)
    # The four-way income cut as well as the ten-way one. The basket needs the
    # decile, being published that way; a criterion banded by income needs the
    # four groups, so both are taken here rather than rebuilt downstream.
    income_four = rank_groups(respondents, "income")
    carrier = carrier or CARRIER_MATCHED
    if carrier not in CARRIERS:
        raise ValueError(f"carrier {carrier!r} is not one of {CARRIERS}")
    if carrier == CARRIER_MATCHED and respondents and any(
            c not in respondents[0].extra
            for c in (*PRIMARY_MORTGAGE, *VEHICLE_PAYMENTS)):
        raise ValueError(
            "the matched carrier needs the primary-residence and vehicle "
            "payment columns, and the selection does not carry them")
    out: list[HouseholdRecord] = []
    for person, group, income_group, band in zip(respondents, wealth, decile,
                                                 income_four, strict=True):
        tenure = tenure_of(person)
        if carrier == CARRIER_MATCHED:
            paid = matched_payments(person, tenure)
            card_payment, mortgage_payment = paid["card"], paid["mortgage"]
            vehicle_payment, outflow = paid["vehicle"], paid["outflow"]
        else:
            card_payment = person.card_payment
            mortgage_payment = (person.mortgage_payment
                                if tenure is Tenure.MORTGAGED else 0.0)
            vehicle_payment, outflow = None, 0.0
        out.append(HouseholdRecord(
            weight=person.weight,
            group=group,
            income_group=band,
            # The one conversion in this file, and the reason
            # ``scf_joint`` bands both units: income is annual, the rent and
            # the payments beside it are monthly.
            income_monthly=person.income / 12.0,
            basket_monthly=basket_annual[income_group] / 12.0,
            tenure=tenure,
            rent_monthly=person.rent if tenure is Tenure.RENTER else 0.0,
            mortgage_payment_monthly=mortgage_payment,
            mortgage_balance=(person.mortgage_debt
                              if tenure is Tenure.MORTGAGED else 0.0),
            card_balance=person.card,
            card_payment_monthly=card_payment,
            vehicle_balance=person.vehicle,
            vehicle_payment_published=vehicle_payment,
            outflow_monthly=outflow,
            # Carried and **not used by this stage**. A1b's cushion is
            # ``Cushion.SCHEDULED``, which never reads it, so every figure this
            # file produces is what it was before the column existed.
            # ``docs/a1d_prereg.md`` §3 is the stage that reads it.
            liquid=person.liquid,
        ))
    return out


# ---------------------------------------------------------------------------
# What has to be read before a run, because the run removes it
# ---------------------------------------------------------------------------
def starting_state(households: list) -> dict:
    """Who is short and who carries which rung, on the population as built.

    ``CascadeModel.run`` mutates the households it is given: displacement pops
    the shelter bill and its balance. A household classified afterwards is
    classified on what the run left, so a displaced renter no longer counts as
    carrying rent and a household whose bills fell below its income by losing
    its home reads as never having been short. Both are read here, first.
    """
    carriers = {t.value: {k.value: 0 for k in Obligation} for t in Tenure}
    for house in households:
        for kind in house.balances:
            carriers[house.tenure.value][kind.value] += 1
    return {
        "short": [sum(h.due.values()) + h.outflow > h.income
                  for h in households],
        "carriers": carriers,
        "tenure": {t.value: sum(1 for h in households if h.tenure is t)
                   for t in Tenure},
    }


def displaced_by_tenure(households: list) -> dict[str, int]:
    """Displaced households by the tenure they started with."""
    return {t.value: sum(1 for h in households
                         if h.tenure is t and h.displaced_at is not None)
            for t in Tenure}


# ---------------------------------------------------------------------------
# The payment carriers, one leg at a time
# ---------------------------------------------------------------------------
#: The Federal Reserve's variable-definition macro, which builds the extract's
#: payment columns. ``MORTPAY`` adds to these three the payments on other
#: residential property, on land contracts and on the home-equity lines the
#: primary residence secures. The three are the loans on the primary residence
#: that ``NH_MORT`` counts, and ``NH_MORT`` is net of the home-equity lines.
PRIMARY_MORTGAGE = ("PAYMORT1", "PAYMORT2", "PAYMORT3")
#: The other residential property (``PAYORE1``, ``PAYORE2``, ``PAYOREV``) and the
#: land contracts (``PAYLC1``, ``PAYLC2``, ``PAYLCO``) inside ``MORTPAY``. What
#: ``MORTPAY`` holds beyond these six and the three above is the payment on the
#: home-equity lines the primary residence secures, read as the remainder.
OTHER_PROPERTY = ("PAYORE1", "PAYORE2", "PAYOREV", "PAYLC1", "PAYLC2", "PAYLCO")
#: The vehicle payments the extract carries loan by loan.
VEHICLE_PAYMENTS = ("PAYVEH1", "PAYVEH2", "PAYVEH3", "PAYVEH4", "PAYVEHM",
                    "PAYVEO1", "PAYVEO2", "PAYVEOM")
#: ``CCPAY = .025 * CCBAL`` and ``BNPLPAY = 0.33 * BNPL`` in the same macro:
#: the card and buy-now-pay-later parts of ``REVPAY`` are the publisher's rates.
CARD_PUBLISHER_RATE = 0.025
BNPL_PUBLISHER_RATE = 0.33

#: Which payment each rung stands on. ``matched`` is the default, ruled
#: 2026-10-17: each rung on the payment of its own stock, every other published
#: payment on no rung. ``registered`` is the construction the stage was
#: registered on, run as an arm beside it.
CARRIER_MATCHED = "matched"
CARRIER_REGISTERED = "registered"
CARRIERS = (CARRIER_MATCHED, CARRIER_REGISTERED)

ARM_MATCHED = "each rung on the payment of its own stock (the default)"
ARM_REGISTERED = "as registered"
ARM_PRIMARY = "the primary residence's mortgage payment"
ARM_CARD = "the card payment at the publisher's rate on the card balance"
ARM_VEHICLE = "the published vehicle payments"


def matched_payments(person: Respondent, tenure: Tenure) -> dict[str, float]:
    """Each rung's payment read on its own stock, and what is left on no rung.

    The card rung pays the publisher's 2.5% of the card balance, the mortgage
    rung the payments on the loans ``NH_MORT`` counts, the car-loan rung the
    published vehicle payments. What the respondent pays beyond those is kept
    as an outflow on no rung: the rest of ``REVPAY``, the rest of ``MORTPAY``
    (all of it where the household has no mortgage rung), and a vehicle
    payment where there is no vehicle balance. A rung whose stock is zero is
    dropped by :func:`build_from_records`, so its payment here is zero too.
    """
    card = CARD_PUBLISHER_RATE * person.card if person.card > 0.0 else 0.0
    own = sum(person.extra[c] for c in PRIMARY_MORTGAGE)
    mortgage = own if tenure is Tenure.MORTGAGED else 0.0
    published = sum(person.extra[c] for c in VEHICLE_PAYMENTS)
    vehicle = published if person.vehicle > 0.0 else 0.0
    revolving_rest = max(person.card_payment - card, 0.0)
    mortgage_rest = max(person.mortgage_payment - mortgage, 0.0)
    vehicle_rest = published - vehicle
    return {"card": card, "mortgage": mortgage, "vehicle": vehicle,
            "revolving_rest": revolving_rest, "mortgage_rest": mortgage_rest,
            "vehicle_rest": vehicle_rest,
            "outflow": revolving_rest + mortgage_rest + vehicle_rest}


def carrier_construction(respondents: list[Respondent],
                         records: list[HouseholdRecord],
                         households: int) -> dict[str, object]:
    """What the matched carrier puts on each rung and on no rung, overall.

    Means are per family by weight over every row; rows are implicates and
    copies are the model households at this population size.
    """
    copies = allocate(records, households)
    total = sum(p.weight for p in respondents)
    paid = [matched_payments(p, tenure_of(p)) for p in respondents]

    def mean(get) -> float:
        return sum(p.weight * get(p, q) for p, q in zip(respondents, paid,
                                                       strict=True)) / total

    def rows(test) -> int:
        return sum(1 for p, q in zip(respondents, paid, strict=True)
                   if test(p, q))

    def copied(test) -> int:
        return sum(c for p, q, c in zip(respondents, paid, copies, strict=True)
                   if test(p, q))

    def no_loan_payment(p, q) -> bool:
        return (tenure_of(p) is Tenure.MORTGAGED and p.mortgage_debt > 0.0
                and q["mortgage"] <= 0.0)

    def no_vehicle_payment(p, q) -> bool:
        return p.vehicle > 0.0 and q["vehicle"] <= 0.0

    def registered(p, q) -> float:
        card = p.card_payment if p.card > 0.0 else 0.0
        mortgage = (p.mortgage_payment if tenure_of(p) is Tenure.MORTGAGED
                    and p.mortgage_debt > 0.0 else 0.0)
        vehicle = (p.vehicle * PAYMENT_RATE[Obligation.AUTO]
                   if p.vehicle > 0.0 else 0.0)
        return card + mortgage + vehicle

    def matched(p, q) -> float:
        mortgage = q["mortgage"] if p.mortgage_debt > 0.0 else 0.0
        return q["card"] + mortgage + q["vehicle"] + q["outflow"]

    return {
        "default": CARRIER_MATCHED,
        "outflow": {
            "rows_with_an_outflow": rows(lambda p, q: q["outflow"] > 0.01),
            "copies_with_an_outflow": copied(lambda p, q: q["outflow"] > 0.01),
            "mean_outflow": mean(lambda p, q: q["outflow"]),
            "mean_revolving_beyond_the_card_rate": mean(
                lambda p, q: q["revolving_rest"]),
            "mean_MORTPAY_beyond_the_mortgage_rung": mean(
                lambda p, q: q["mortgage_rest"]),
            "mean_vehicle_payment_with_no_vehicle_balance": mean(
                lambda p, q: q["vehicle_rest"]),
            "rows_with_REVPAY_and_no_card_balance": rows(
                lambda p, q: p.card <= 0.0 and p.card_payment > 0.01),
            "rows_with_MORTPAY_and_no_mortgage_rung": rows(
                lambda p, q: tenure_of(p) is not Tenure.MORTGAGED
                and p.mortgage_payment > 0.01),
            "rows_with_a_vehicle_payment_and_no_vehicle_balance": rows(
                lambda p, q: q["vehicle_rest"] > 0.01),
        },
        "rows_with_a_mortgage_rung_and_no_payment_on_its_loans": rows(
            no_loan_payment),
        "copies_with_a_mortgage_rung_and_no_payment_on_its_loans": copied(
            no_loan_payment),
        "rows_with_a_vehicle_balance_and_no_published_payment": rows(
            no_vehicle_payment),
        "copies_with_a_vehicle_balance_and_no_published_payment": copied(
            no_vehicle_payment),
        "mean_debt_payment_carried": {
            CARRIER_REGISTERED: mean(registered),
            CARRIER_MATCHED: mean(matched),
        },
    }


def carrier_arms(respondents: list[Respondent],
                 records: list[HouseholdRecord]) -> dict[str, list]:
    """The registered records with one leg's payment replaced, three times.

    ``records`` is the registered construction. Each arm changes one payment
    and nothing else, so the scheduled cushion, which is one month of the
    household's own bills, follows that one payment. The three arms are the
    sensitivity of the registered construction to each leg alone; the default
    replaces all three at once and carries the rest on no rung.
    """
    need = (*PRIMARY_MORTGAGE, *VEHICLE_PAYMENTS)
    if not respondents or any(c not in respondents[0].extra for c in need):
        return {}
    primary, card, vehicle = [], [], []
    for person, record in zip(respondents, records, strict=True):
        own = sum(person.extra[c] for c in PRIMARY_MORTGAGE)
        primary.append(replace(
            record,
            mortgage_payment_monthly=(own if record.tenure is Tenure.MORTGAGED
                                      else 0.0)))
        card.append(replace(
            record,
            card_payment_monthly=CARD_PUBLISHER_RATE * record.card_balance))
        vehicle.append(replace(
            record,
            vehicle_payment_published=sum(person.extra[c]
                                          for c in VEHICLE_PAYMENTS)))
    return {ARM_PRIMARY: primary, ARM_CARD: card, ARM_VEHICLE: vehicle}


def carrier_reading(result) -> dict[str, object]:
    """What one arm reads on the three loan rungs at the end of the path."""
    final = {k.value: result.delinquent_share[k.value][-1]
             for k in (Obligation.CARD, Obligation.AUTO, Obligation.MORTGAGE)}
    return {"final": final,
            "k_shape": final["MORTGAGE"] < final["AUTO"] < final["CARD"],
            "defaulting_households": result.defaulting_households}


def payment_coverage(respondents: list[Respondent],
                     copies: list[int] | None = None) -> dict[str, object]:
    """What each payment column covers beside the balance it is set against.

    Rows are implicates, five to a family, and the means are weighted. A row
    counts as carrying something extra when the difference passes one cent.

    ``MORTPAY`` beyond the ``NH_MORT`` loans is split in two, as A1a splits it:
    other property and land contracts, read from their six columns, and the
    primary residence's home-equity line, the remainder. A row paying beyond
    the ``NH_MORT`` loans has some payment on other property or a land contract,
    or the home-equity line alone.

    The vehicle comparison is counted on the rows with a vehicle balance, which
    are the rows the model gives a vehicle rung. Rows with a published vehicle
    payment and no vehicle balance are counted apart, and ``copies``, one count
    per row from :func:`allocate`, gives how many model households they become.
    """
    if not respondents or any(c not in respondents[0].extra
                              for c in (*PRIMARY_MORTGAGE, *OTHER_PROPERTY,
                                        *VEHICLE_PAYMENTS, "BNPL")):
        return {}

    def mean(rows, get) -> float:
        w = sum(r.weight for r in rows)
        return sum(r.weight * get(r) for r in rows) / w if w else 0.0

    def own(r):
        return sum(r.extra[c] for c in PRIMARY_MORTGAGE)

    def other(r):
        return sum(r.extra[c] for c in OTHER_PROPERTY)

    def veh(r):
        return sum(r.extra[c] for c in VEHICLE_PAYMENTS)

    def sixtieth(r):
        return r.vehicle * PAYMENT_RATE[Obligation.AUTO]

    mortgaged = [r for r in respondents if r.owns and r.mortgaged]
    beyond = [r for r in mortgaged if r.mortgage_payment - own(r) > 0.01]
    holders = [r for r in respondents if r.card > 0]
    drivers = [r for r in respondents if r.vehicle > 0]
    unheld = [i for i, r in enumerate(respondents)
              if r.vehicle <= 0 and veh(r) > 0.01]
    vehicle_unheld: dict[str, int] = {
        "rows_with_a_published_vehicle_payment_and_no_vehicle_balance":
            len(unheld),
    }
    if copies is not None:
        vehicle_unheld[
            "copies_with_a_published_vehicle_payment_and_no_vehicle_balance"
        ] = sum(copies[i] for i in unheld)
    return {
        "mortgage": {
            "rows_mortgaged": len(mortgaged),
            "rows_paying_beyond_the_NH_MORT_loans": len(beyond),
            "rows_with_other_property_or_land_contract_payments": sum(
                1 for r in beyond if other(r) > 0.01),
            "rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans": sum(
                1 for r in beyond if other(r) <= 0.01),
            "mean_MORTPAY": mean(mortgaged, lambda r: r.mortgage_payment),
            "mean_nh_mort_loans": mean(mortgaged, own),
            "mean_other_property_and_land_contracts": mean(mortgaged, other),
            "mean_primary_residence_home_equity_line": mean(
                mortgaged, lambda r: r.mortgage_payment - own(r) - other(r)),
        },
        "card": {
            "rows_with_a_card_balance": len(holders),
            "rows_with_more_than_the_card_rate": sum(
                1 for r in holders
                if r.card_payment - CARD_PUBLISHER_RATE * r.card > 0.01),
            "mean_REVPAY": mean(holders, lambda r: r.card_payment),
            "mean_card_at_the_publisher_rate": mean(
                holders, lambda r: CARD_PUBLISHER_RATE * r.card),
            "mean_bnpl_at_the_publisher_rate": mean(
                holders, lambda r: BNPL_PUBLISHER_RATE * r.extra["BNPL"]),
            "rows_with_a_revolving_payment_and_no_card_balance": sum(
                1 for r in respondents if r.card <= 0 and r.card_payment > 0),
            "REVPAY_over_card_balance_all_rows": (
                sum(r.weight * r.card_payment for r in respondents)
                / sum(r.weight * r.card for r in respondents)),
            "REVPAY_over_card_balance_card_holders": (
                sum(r.weight * r.card_payment for r in holders)
                / sum(r.weight * r.card for r in holders)),
        },
        "vehicle": {
            "rows_with_a_vehicle_balance": len(drivers),
            "rows_with_a_vehicle_balance_where_the_two_differ": sum(
                1 for r in drivers if abs(veh(r) - sixtieth(r)) > 0.01),
            **vehicle_unheld,
            "mean_published_all_households": mean(respondents, veh),
            "mean_sixtieth_all_households": mean(
                respondents, lambda r: r.vehicle * PAYMENT_RATE[Obligation.AUTO]),
            "mean_published_holders": mean(drivers, veh),
            "mean_sixtieth_holders": mean(
                drivers, lambda r: r.vehicle * PAYMENT_RATE[Obligation.AUTO]),
        },
    }


def flat_path(periods: int, n_strata: int, multiplier: float = 1.0):
    return [tuple([multiplier] * n_strata) for _ in range(periods)]


#: The scored horizon, the same sixty months the baseline is reported over so
#: the two are read side by side. Long enough that the slowest clock in the cost
#: rule, the twelve-month foreclosure one, has run out five times.
SCORED_PERIODS = 60
#: A0's seed. A1b draws nothing, so this is the only randomness in the stage.
PATH_SEED = 7


# ---------------------------------------------------------------------------
# Running the independent runs at the same time
# ---------------------------------------------------------------------------
#: The same rule ``monetary_topology.interaction_rank`` uses, and half the cores
#: for the same reason: a machine doing nothing else still has other work.
def default_jobs() -> int:
    return max(1, min(8, (os.cpu_count() or 2) // 2))


#: **The result does not depend on the worker count**, and that is a property
#: rather than a hope. Every task below builds its own population from the same
#: records by the same deterministic allocation and runs it whole in one
#: process, so each task's arithmetic is bit for bit what it would be alone.
#:
#: **Sharding a single run across processes was considered and refused.** The
#: households do not interact, which is A1-10's registered licence, so a run
#: could be split by household and the delinquency shares recombined from
#: partial sums. That would beat the 86-second floor a single 100,000-household
#: run sets. It would also make the last bits of every share depend on how many
#: workers added them up, and this repository's own convention on parallelism is
#: that the answer does not move with the worker count. A faster number that
#: changes when the machine changes is not the same number.
def _task(job: dict) -> dict:
    """One whole run in one process. Returns summaries, never a population."""
    records = job["records"]
    cost = CostRule()
    households = build_from_records(records, job["households"], cost)
    if job["kind"] == "relieved":
        households = relieved(households, cost)
    path = job["path"]
    start = starting_state(households)
    result = CascadeModel(households, cost).run(path)

    out: dict = {"kind": job["kind"], "result": result,
                 "carriers_at_start": start["carriers"],
                 "tenure_at_start": start["tenure"],
                 "displaced_by_tenure": displaced_by_tenure(households)}
    if job["kind"] == "carrier":
        out["arm"] = job["arm"]
    if job["kind"] == "scored":
        short = start["short"]
        clear = [h for h, s in zip(households, short, strict=True) if not s]
        defaulting = [h for h in clear if h.first_default is not None]
        if defaulting:
            n = len(defaulting)
            counts = {k: sum(1 for h in defaulting if h.first_default is k)
                      for k in Obligation}
            out["unstressed"] = {
                "n": n,
                "card": counts[Obligation.CARD] / n,
                "auto": counts[Obligation.AUTO] / n,
                "shelter": sum(counts[k] for k in SHELTER_CLASSES) / n,
            }
            out["unstressed"]["holds"] = (
                out["unstressed"]["card"] > out["unstressed"]["auto"]
                > out["unstressed"]["shelter"]
            )
        out["by_wealth"] = renter_gradient(households, "wealth")
        out["by_income"] = renter_gradient(households, "income")
    elif job["kind"] == "sweep":
        out["seed"] = job["seed"]
        out["months_per_round"] = job["months_per_round"]
        out["model"] = ever_behind_by_group(households, LOAN_CLASSES)
        out["model_with_rent"] = ever_behind_by_group(
            households, (*LOAN_CLASSES, Obligation.RENT)
        )
        out["sizes"] = [sum(1 for h in households if h.stratum == g)
                        for g in range(len(GROUPS))]
    return out


def run_tasks(jobs: list[dict], workers: int) -> list[dict]:
    """In order, whichever way they are run, so the caller cannot tell."""
    if workers <= 1 or len(jobs) == 1:
        return [_task(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_task, jobs))


# ---------------------------------------------------------------------------
# A1b-0. The zero calibration is a constancy, not a zero
# ---------------------------------------------------------------------------
def relieved(households: list, cost: CostRule) -> list:
    """The same population with every shortfall removed and nothing else.

    Each household's income is raised to whatever its scheduled obligations come
    to, where it falls short, and its cash on hand likewise. Same records, same
    balances, same tenure, same code path.

    **Both, because under this mechanism a shortfall has two components.**
    ``CascadeSpec.income_arrives_after_due`` is Volume One section 4's settlement asymmetry
    and it is ``True``: income lands after the due date. A household whose
    income exactly covers its bills and whose cash is zero therefore cannot pay
    in period 0, and no amount of income repairs that. Raising the flow alone
    leaves the stock cause in place, and a control arm that leaves a cause in
    place has not removed the cause.

    **This was found on 2026-08-16 by A1d-0 failing**, and the correction is
    recorded in ``docs/a1d_prereg.md`` §10 and ``docs/a1b_prereg.md`` §8 with
    what had been seen. It is a defect in this control arm rather than a change
    to any criterion: §6.2 of the A1d registration says *remove the cause*, and
    this is what that sentence requires when the cushion is measured.

    **Inert for A1b, provably.** A1b builds with ``Cushion.SCHEDULED``, whose
    buffer is ``sum(due.values()) * 1.0`` summed in this same dict order, so the
    new line is ``max(x, x)`` on every household and A1b's record is unmoved.
    ``test_the_relief_arm_does_not_move_a_scheduled_cushion`` is that claim as a
    test rather than as this paragraph.
    """
    import copy

    out = copy.deepcopy(households)
    for house in out:
        # The payments on no rung are bills too, and a shortfall on them is
        # part of the cause this arm removes.
        scheduled = sum(house.due.values()) + house.outflow
        house.income = max(house.income, scheduled)
        house.buffer = max(house.buffer, scheduled)
    return out


def a1b_0(clean, unrelieved) -> tuple[Criterion, dict[str, object]]:
    """Remove the cause and the reading must vanish. Exactly.

    ``docs/a1b_prereg.md`` §3 first stated this as a constancy, and the first run
    showed that was wrong too. A population carrying real baseline stress does
    not settle: renters fall behind, are displaced, the obligation is removed,
    the freed cash clears other arrears, and the series is still moving at sixty
    periods. Neither zero nor constant is the right thing to demand of it.

    What a zero calibration is actually for is detecting an instrument that
    produces readings from nothing. So the cause is removed rather than the
    shock: every household's income is raised to cover its own scheduled
    obligations, nothing else is touched, and **every rung must then report
    exactly 0.000000**. That works on any population, it runs through the same
    code path as a scored cell, and it fails if anything in ``step`` invents a
    default.

    The unrelieved no-shock run is reported beside it as the **baseline**, which
    is the reference every shocked reading in this stage is measured against.
    It is a series and not a number, and §6 of the pre-registration says so.
    """
    nonzero: list[str] = []
    for kind in Obligation:
        bad = [v for v in clean.delinquent_share[kind.value] if v != 0.0]
        if bad:
            nonzero.append(f"{kind.value} reaches {max(bad):.6f}")

    baseline = {
        kind.value: unrelieved.delinquent_share[kind.value]
        for kind in Obligation
    }
    reference = {
        "final": {k: v[-1] for k, v in baseline.items()},
        "displaced_all_tenures": unrelieved.displaced,
        "renters": unrelieved.renters,
        "periods": unrelieved.periods,
        "still_moving": any(
            v[-1] != v[-2] for v in baseline.values() if len(v) > 1
        ),
    }
    return Criterion(
        "A1b-0 zero calibration, by removing the cause",
        not nonzero,
        (f"income raised to cover each household's own obligations: every rung "
         f"exactly 0.000000 over {ZERO_PERIODS} periods"
         if not nonzero
         else "; ".join(nonzero[:4])),
    ), reference


# ---------------------------------------------------------------------------
# A1-2. The order is an output
# ---------------------------------------------------------------------------
#: The three the criterion names. ``BASKET`` can be a first default too and is
#: reported beside them, because a household that gives up food first is
#: something this stage should say out loud rather than fold into a residual.
SHELTER_CLASSES = (Obligation.RENT, Obligation.MORTGAGE)


def first_default_shares(result) -> dict[str, float]:
    total = result.defaulting_households
    if total == 0:
        return {}
    counts = result.first_default_counts
    return {
        "card": counts[Obligation.CARD.value] / total,
        "auto": counts[Obligation.AUTO.value] / total,
        "shelter": sum(counts[k.value] for k in SHELTER_CLASSES) / total,
        # The two halves of the gated aggregate, reported because they are what
        # it is made of. Reporting a component is not restating a criterion.
        "rent": counts[Obligation.RENT.value] / total,
        "mortgage": counts[Obligation.MORTGAGE.value] / total,
        "basket": counts[Obligation.BASKET.value] / total,
    }


#: Written into the record beside the per-tenure rows, so the record says which
#: rate to read. The row keys are these names with the rung appended.
TENURE_RATE_DEFINITIONS = {
    "share": "first defaults on the rung over the tenure's defaulting households",
    "carriers_at_start": (
        "households of the starting tenure that carried the rung when the run "
        "began, read before the run"),
    "per_carrier_at_start": (
        "first defaults on the rung over carriers_at_start; the rate to read"),
    "exposed": (
        "households of the starting tenure still carrying the rung when the run "
        "ended; displacement removes the shelter rung, so for rent and the "
        "mortgage this is fewer than carried it at the start"),
    "per_exposed": (
        "first defaults on the rung over exposed, kept under its own name; a "
        "displaced household whose first default was its shelter rung is in "
        "that rung's numerator and no longer in its denominator"),
}


def first_default_shares_by_tenure(result, carriers_at_start=None
                                   ) -> dict[str, dict[str, float]]:
    """The same shares inside each starting tenure, with its own denominator.

    **Two per-carrier rates are kept apart.** A first default is counted once,
    on the household that started in the tenure, so its rate per carrier is
    over the households that carried the rung at the start. The model's own
    ``exposure_by_tenure`` is taken after the run, when every displaced
    household has had its shelter rung removed, so dividing first defaults by
    it keeps a displaced household whose first default was its shelter rung in
    that rung's numerator and drops it from the denominator. That figure is kept under its own name, ``per_exposed``, and
    the rate to read is ``per_carrier_at_start``.

    The pooled version divides every rung by every defaulting household, and
    two of the rungs are not carried by every household: a mortgaged household
    has no rent to default on and an outright owner has neither. Dividing the
    rent rung by the pooled count therefore compares two rungs with different
    populations against one number. Volume One section 18 states its cascade
    about tenants, so the tenancy is where the rent rung belongs.

    Reported, not gated. A1-2 keeps its registered population.
    """
    by_tenure = getattr(result, "first_default_counts_by_tenure", None)
    if not by_tenure:
        return {}
    exposure = getattr(result, "exposure_by_tenure", None) or {}
    out: dict[str, dict[str, float]] = {}
    for tenure, counts in by_tenure.items():
        total = sum(counts.values())
        if total == 0:
            out[tenure] = {"defaulting_households": 0}
            continue
        exposed = exposure.get(tenure, {})
        row: dict[str, float] = {"defaulting_households": total}
        for kind in (Obligation.CARD, Obligation.AUTO, Obligation.RENT,
                     Obligation.MORTGAGE, Obligation.BASKET):
            n = counts[kind.value]
            row[f"share_{kind.value.lower()}"] = n / total
            # Per household standing on that rung. Zero exposure gives ``None``
            # rather than zero: nobody carries it, which is not the same as
            # nobody defaulting on it.
            e = exposed.get(kind.value, 0)
            row[f"per_exposed_{kind.value.lower()}"] = (n / e) if e else None
            row[f"exposed_{kind.value.lower()}"] = e
            if carriers_at_start is not None:
                s = carriers_at_start.get(tenure, {}).get(kind.value, 0)
                row[f"per_carrier_at_start_{kind.value.lower()}"] = (
                    (n / s) if s else None)
                row[f"carriers_at_start_{kind.value.lower()}"] = s
        out[tenure] = row
    return out


def a1_2(scored, unstressed) -> Criterion:
    """Card before car before shelter, as shares of the defaulting households.

    ``docs/a1_prereg.md`` A1-2, inherited unchanged. Strict inequalities and no
    level: a reversal is Volume One section 18's sequence being wrong rather than the code
    being wrong, and it is recorded as such.

    **The shares are of households that default at all**, which in this
    population includes households already short at baseline. Their first
    default is dated before the shock reaches them, so the criterion is also
    computed on the households that were **not** short at baseline and both are
    printed. The gate is on the registered population, all defaulters; a
    disagreement between the two is reported and is a finding about which
    households the ordering describes.
    """
    share = first_default_shares(scored)
    if not share:
        return Criterion("A1-2  the order is an output", False,
                         "no household defaulted, so there is no order", True)
    holds = share["card"] > share["auto"] > share["shelter"]
    detail = (
        f"first default among {scored.defaulting_households:,} defaulting "
        f"households: card {share['card']:.4f}, auto {share['auto']:.4f}, "
        f"shelter {share['shelter']:.4f} (rent {share['rent']:.4f}, mortgage "
        f"{share['mortgage']:.4f}), basket {share['basket']:.4f}"
    )
    if unstressed:
        detail += (
            f". Among the {unstressed['n']:,} defaulting households not short "
            f"at baseline: card "
            f"{unstressed['card']:.4f}, auto {unstressed['auto']:.4f}, "
            f"shelter {unstressed['shelter']:.4f}"
            + ("" if unstressed["holds"] == holds
               else "  <- DISAGREES with the registered population")
        )
    detail += (
        ". VOID as registered: the estimator and the object do not line up. "
        "This share is a distribution across households, and a distribution is "
        "decided both by how hard a rung is and by how many households stand "
        "on it, while the pooled denominator is every defaulter. Rent is "
        "carried only by tenants and the mortgage only by borrowers, so those "
        "two rungs are divided by a head count that includes households which "
        "could not default on them. Volume One section 18 states its cascade "
        "about tenants. The ordering claim itself is carried by A1c, which "
        "reads the sequence inside one household and holds. The tenure-split "
        "shares and the per-carrier-at-start rates are reported beside this "
        "line and are what the section 18 reading needs"
    )
    return Criterion("A1-2  the order is an output", holds, detail, True)


# ---------------------------------------------------------------------------
# A1-3. The K shape, ordinally, with the attached parameter gate
# ---------------------------------------------------------------------------
def one_rule_for_every_class(cost: CostRule) -> tuple[bool, str]:
    """``docs/a1_prereg.md`` A1-3's attached gate, as a check and not a promise.

    The criterion fails even where the inequality holds if the mortgage pair is
    produced by a different rule or carries a multiplier no other class carries.
    That is a property of the source, so it is read off the source: ``cost_now``
    must name no obligation class at all, and every class's resource must come
    from the same table the others come from.
    """
    import inspect

    source = inspect.getsource(CostRule.cost_now)
    named = [k.value for k in Obligation if k.value in source]
    if named:
        return False, (
            f"cost_now names {', '.join(named)}; a rule that branches on a "
            f"class is four rules wearing one name"
        )
    from monetary_topology.cascade import RESOURCE_SUPPORT

    outside = [k.value for k in Obligation
               if k is not Obligation.AUTO and k not in RESOURCE_SUPPORT]
    if outside:
        return False, f"{', '.join(outside)} draws its resource from elsewhere"
    return True, (
        "cost_now names no class; every pair is the same rule applied to "
        "per-class attributes"
    )


def a1_3(scored, cost: CostRule, baseline: dict[str, float]) -> Criterion:
    """mortgage 90+ < auto 90+ < card 90+, at the end of the scored horizon.

    Source of the order: the workbook itself, 2026Q1, `1.09 < 5.60 < 13.12`.

    **Reported against the baseline as well as raw.** This population carries
    delinquency before any shock, so the raw ordering and the ordering of the
    increment over baseline are different quantities. The gate is on the raw
    figure, which is what the criterion registers and what the target is; the
    increment is printed beside it and a disagreement is a finding.
    """
    final = {k.value: scored.delinquent_share[k.value][-1] for k in Obligation}
    raw = (final["MORTGAGE"] < final["AUTO"] < final["CARD"])
    rise = {k: final[k] - baseline.get(k, 0.0) for k in final}
    over = (rise["MORTGAGE"] < rise["AUTO"] < rise["CARD"])
    same_rule, why = one_rule_for_every_class(cost)

    detail = (
        f"mortgage {final['MORTGAGE']:.4f} < auto {final['AUTO']:.4f} < card "
        f"{final['CARD']:.4f}" if raw else
        f"NOT ordered: mortgage {final['MORTGAGE']:.4f}, auto "
        f"{final['AUTO']:.4f}, card {final['CARD']:.4f}"
    )
    detail += (
        f". Over baseline: mortgage {rise['MORTGAGE']:+.4f}, auto "
        f"{rise['AUTO']:+.4f}, card {rise['CARD']:+.4f}"
        + ("" if over == raw else "  <- DISAGREES with the raw ordering")
    )
    detail += f". Attached gate: {why}"
    if not same_rule:
        detail += (
            ". The K shape here requires an exogenous homeowner-protection "
            "assumption, which is a claim about policy rather than about the "
            "mechanism"
        )
    return Criterion("A1-3  K shape, ordinally", raw and same_rule, detail)


# ---------------------------------------------------------------------------
# A1-6. The subprime gradient, on sign
# ---------------------------------------------------------------------------
#: FEDS Note 2025-11-24 on the CCP, four dated readings of subprime against
#: near-prime auto delinquency at 30+ days on balances. **Reported and never
#: compared as a level**: the source's threshold is thirty days and the model's
#: is ninety, and a level comparison across two thresholds is the denominator
#: error this project has now recorded seven times.
PUBLISHED_SUBPRIME_RATIO = ((2000, 5.33), (2019, 5.85), (2024, 5.58),
                            (2025, 5.40))


def a1_6(scored) -> Criterion:
    """Bottom-group auto delinquency exceeds middle-group auto delinquency.

    ``docs/a1_prereg.md`` A1-6, inherited. **Gated on the sign only.** The
    model's ratio is printed beside the four published readings of the same
    ratio and nothing is scored on it.
    """
    bottom = scored.delinquent_share_by_group["AUTO:0"][-1]
    middle = scored.delinquent_share_by_group["AUTO:1"][-1]
    if bottom == 0.0 and middle == 0.0:
        return Criterion("A1-6  the subprime gradient", False,
                         "neither group carries auto delinquency, so the sign "
                         "is undefined rather than satisfied", True)
    ratio = bottom / middle if middle > 0.0 else float("inf")
    published = ", ".join(f"{year} {value:.2f}"
                          for year, value in PUBLISHED_SUBPRIME_RATIO)
    return Criterion(
        "A1-6  the subprime gradient",
        bottom > middle,
        f"bottom {bottom:.4f} against middle {middle:.4f}, ratio "
        f"x{ratio:.2f}. Published at 30 days on balances and reported only: "
        f"{published}. The model is at ninety days, so the ratio is beside "
        f"them and not against them",
    )


# ---------------------------------------------------------------------------
# A1-7. The rent gradient
# ---------------------------------------------------------------------------
#: ``docs/a1_prereg.md`` A1-7's floor, so a group with a handful of renters is
#: named and excluded rather than scored on noise.
RENTER_FLOOR = 30

#: Fed SHED 2025: 23% of renters behind at some point in twelve months, by
#: income band 33 / 31 / 17 / 5. **Reported and never gated**: the source counts
#: households behind *at some point in twelve months* and this model runs sixty,
#: which is `MEASUREMENT.md` checklist item 1.
SHED_OVERALL = 0.23
SHED_BY_BAND = (0.33, 0.31, 0.17, 0.05)


def renter_gradient(households: list, by: str) -> tuple[list, list[str]]:
    """Renter arrears by group, on one ranking, with thin groups excluded."""
    rates: list[tuple[int, float, int]] = []
    excluded: list[str] = []
    for group in range(len(GROUPS)):
        renters = [h for h in households
                   if h.started_renting
                   and (h.stratum if by == "wealth" else h.income_group) == group]
        if len(renters) < RENTER_FLOOR:
            excluded.append(f"{GROUPS[group]} ({len(renters)} renters)")
            continue
        behind = sum(1 for h in renters if h.ever_missed.get(Obligation.RENT))
        rates.append((group, behind / len(renters), len(renters)))
    return rates, excluded


def _monotone(rates: list) -> bool:
    values = [rate for _, rate, _ in rates]
    return (len(values) >= 2
            and all(a >= b for a, b in zip(values, values[1:]))
            and values[0] > values[-1])


def a1_7(scored, by_wealth, dropped_wealth, by_income,
         dropped_income) -> Criterion:
    """Weakly monotone decreasing across the groups that contain renters.

    Inherited from ``docs/a1_prereg.md`` A1-7, including its 2026-08-15
    restriction: a group below the renter floor is **named in the output and
    excluded** rather than scored on a handful.

    **Read on both rankings, because the registration names both.** Its title
    says "monotone in income" and its source is SHED's `33 / 31 / 17 / 5` by
    income band; its body says "across the strata", and the strata are net
    worth. In A1 there was one ranking and the ambiguity could not show. Here
    both are measured, and where the two readings disagree the criterion is
    **reported on both and gated on neither**, which is the treatment this
    project already registered for a verdict that flips between two arms.
    """
    if len(by_wealth) < 2 and len(by_income) < 2:
        return Criterion("A1-7  the rent gradient", False,
                         f"fewer than two groups clear {RENTER_FLOOR} renters "
                         f"on either ranking, so the gradient is undefined",
                         True)

    wealth_holds, income_holds = _monotone(by_wealth), _monotone(by_income)
    overall = (scored.renters_ever_behind / scored.renters
               if scored.renters else 0.0)

    def show(rates, dropped) -> str:
        body = ", ".join(f"{GROUPS[g]} {rate:.4f} ({n:,})"
                         for g, rate, n in rates)
        if dropped:
            body += f"; excluded below {RENTER_FLOOR}: " + ", ".join(dropped)
        return body

    detail = (
        f"by net worth: {show(by_wealth, dropped_wealth)}"
        f" [{'monotone' if wealth_holds else 'NOT monotone'}]. "
        f"By income: {show(by_income, dropped_income)}"
        f" [{'monotone' if income_holds else 'NOT monotone'}]"
    )
    detail += (
        f". Overall {overall:.4f} against SHED's {SHED_OVERALL:.2f}, reported "
        f"only: the source counts renters behind at some point in twelve "
        f"months and this is sixty months of a model. Published by income "
        f"band: " + "/".join(f"{v:.2f}" for v in SHED_BY_BAND)
    )
    if wealth_holds != income_holds:
        detail += (
            ". **The two readings of the registration disagree**, so this is "
            "reported on both and gated on neither. The source is banded by "
            "income and the model's strata are net worth, and A1 could not "
            "see the difference because it had one ranking"
        )
        return Criterion("A1-7  the rent gradient", False, detail, True)
    return Criterion("A1-7  the rent gradient", wealth_holds, detail)


# ---------------------------------------------------------------------------
# A1-9. The representative arm, and what it localizes
# ---------------------------------------------------------------------------
def representative(records: list[HouseholdRecord],
                   tenure: Tenure) -> HouseholdRecord:
    """Every record collapsed to one household by its weight.

    ``docs/a1_prereg.md`` §2.4: this is the operation `b1_theorem.md` Corollary
    1 calls a category error, performed deliberately so the control arm is the
    collapse itself. A single household has one tenure, so the arm is built at
    each of the three and each is run.

    The shelter flows are averaged over the households that pay them rather
    than over all of them, which is the same rule the population uses and the
    same rule a collapse has to use if it is to be a collapse of that
    population.
    """
    total = sum(r.weight for r in records)

    def mean(get, over=None) -> float:
        rows = [r for r in records if over is None or over(r)]
        weight = sum(r.weight for r in rows)
        return sum(r.weight * get(r) for r in rows) / weight if weight else 0.0

    return HouseholdRecord(
        weight=total,
        group=0,
        income_group=0,
        income_monthly=mean(lambda r: r.income_monthly),
        basket_monthly=mean(lambda r: r.basket_monthly),
        tenure=tenure,
        rent_monthly=mean(lambda r: r.rent_monthly,
                          lambda r: r.tenure is Tenure.RENTER),
        mortgage_payment_monthly=mean(
            lambda r: r.mortgage_payment_monthly,
            lambda r: r.tenure is Tenure.MORTGAGED,
        ),
        mortgage_balance=mean(lambda r: r.mortgage_balance,
                              lambda r: r.tenure is Tenure.MORTGAGED),
        card_balance=mean(lambda r: r.card_balance),
        card_payment_monthly=mean(lambda r: r.card_payment_monthly),
        vehicle_balance=mean(lambda r: r.vehicle_balance),
        vehicle_payment_published=(
            None if all(r.vehicle_payment_published is None for r in records)
            else mean(lambda r: r.vehicle_payment_monthly)),
        outflow_monthly=mean(lambda r: r.outflow_monthly),
        # The collapse of the cushion too, so that a stage running this arm on a
        # measured cushion collapses the same population rather than a different
        # one. A1b never reads it.
        liquid=mean(lambda r: r.liquid),
    )


def a1_9(records: list[HouseholdRecord], cost: CostRule, path,
         cushion: Cushion = Cushion.SCHEDULED) -> Criterion:
    """The registered expectation: a single household's rates are in {0, 1}.

    ``docs/a1_prereg.md`` A1-9 registers this from `b1_theorem.md` Corollary 1
    and from the arithmetic: one household's per-rung rate is a ratio of its own
    balance to itself. The row that would be a surprise is rates coming out
    **non-degenerate**, and it is registered so it cannot be explained away
    afterwards.
    """
    seen: dict[str, set[float]] = {}
    for tenure in Tenure:
        houses = build_from_records([representative(records, tenure)], 1, cost,
                                    cushion=cushion)
        result = CascadeModel(houses, cost).run(path)
        for kind in Obligation:
            for value in result.delinquent_share[kind.value]:
                seen.setdefault(f"{tenure.value}:{kind.value}", set()).add(value)
    strays = {
        key: sorted(v for v in values if v not in (0.0, 1.0))
        for key, values in seen.items()
        if any(v not in (0.0, 1.0) for v in values)
    }
    detail = (
        "every rung of the collapsed household takes values in {0, 1} across "
        "all three tenures, which is Corollary 1 with a number attached: the "
        "difference between the arms is the population"
        if not strays
        else "NON-DEGENERATE, which A1-9 registers as the surprising row: "
             + "; ".join(f"{k} {v[:3]}" for k, v in list(strays.items())[:3])
             + ". The setting is not what 2.4 says it is and the heterogeneity "
               "that leaked in has to be found before anything else is read"
    )
    return Criterion("A1-9  the representative arm is degenerate", not strays,
                     detail)


# ---------------------------------------------------------------------------
# A1-10. One behavioural parameter vector across every rung
# ---------------------------------------------------------------------------
def a1_10(cost: CostRule) -> Criterion:
    """No rung gets an adjustment of its own, checked against the source.

    A1's own failure criterion, promoted to a gate. A
    per-rung adjustment fails the stage, and that failure is the coverage
    test failing, which requires stopping and redesigning rather than reporting
    a partial pass.

    Read off the source rather than promised in prose: the same check A1-3's
    attached gate makes, extended to the two attribute tables. A class named in
    ``cost_now`` is a branch; a class absent from ``RESOURCE_SUPPORT`` and from
    ``grace`` is a class getting its number from somewhere else.
    """
    import inspect

    from monetary_topology.cascade import RESOURCE_SUPPORT

    problems: list[str] = []
    body = inspect.getsource(CostRule.cost_now)
    named = [k.value for k in Obligation if k.value in body]
    if named:
        problems.append(f"cost_now branches on {', '.join(named)}")
    for kind in Obligation:
        if kind is Obligation.AUTO:
            continue
        if kind not in RESOURCE_SUPPORT:
            problems.append(f"{kind.value} has no entry in RESOURCE_SUPPORT")
    graces = {k: cost.grace(k) for k in Obligation}
    if any(g < 1 for g in graces.values()):
        problems.append("a grace below one period")
    detail = (
        "one rule, one attribute table, one grace table; every rung's pair is "
        + ", ".join(f"{k.value} {cost.cost_now(k):.3f}/{cost.grace(k)}"
                    for k in Obligation)
        if not problems
        else "; ".join(problems)
        + ". This is the coverage test failing, and it requires stopping and "
          "redesigning rather than a partial pass"
    )
    return Criterion("A1-10 one parameter set across every rung",
                     not problems, detail)


# ---------------------------------------------------------------------------
# A1b-1. The delinquency gradient, against a target on the model's own cut
# ---------------------------------------------------------------------------
#: ``docs/a1b_prereg.md`` §8, registered 2026-08-16 **before the gradient was
#: computed**: A0's seeds crossed with the one identification arm.
SWEEP_SEEDS = (7, 8, 9)
SWEEP_MONTHS_PER_ROUND = (1, 3)

#: The sweep is six full runs, so it carries its own population size under the
#: licence ``docs/a1_prereg.md`` A1-10 registers: households do not interact, so
#: the size is an estimation setting chosen per criterion and buys precision
#: without changing behaviour. The licence is tested rather than asserted, in
#: A1's own experiment, and if that test fails this override goes with it.
#:
#: **The size is forced by the resolution rule below rather than chosen.** At
#: 20,000 households the ``next9`` group holds 1,895 and the survey's own rate
#: would put 4.2 events in it, under :data:`EXPECTED_EVENT_FLOOR`, while the
#: survey resolves the ``next40``/``next9`` pair, so the rule refuses that size.
#: At 50,000 the same group holds 4,322 and the expectation is 9.6. A1d's sweep
#: runs at the same size for the same reason. The group sizes are printed so a
#: reader can see how many households each scored pair rests on.
DEFAULT_SWEEP_HOUSEHOLDS = 50_000

#: The survey asks about being sixty days or more late on **loan payments**, so
#: the model's counterpart is the card, the car and the mortgage. Rent is
#: excluded: an ordinary tenancy is not a loan and is not furnished to the
#: bureaus, which is already why ``REPORTS_TO_CREDIT`` marks it apart. The
#: variant including rent is reported beside it and never gated.
LOAN_CLASSES = (Obligation.CARD, Obligation.AUTO, Obligation.MORTGAGE)


def ever_behind_by_group(households: list, classes,
                         n_groups: int = len(GROUPS)) -> list[float]:
    """Share of each net-worth group that ever missed any of these classes.

    The group count is passed rather than inferred from the households. A
    population too small to give the top 1% a single member would otherwise
    return three numbers where the target has four, and the two would be
    compared as orderings of different lengths and never match. That is a
    comparison failing on its own shape rather than on the world, and
    :func:`a1b_1` refuses the size instead.
    """
    behind = [0] * n_groups
    total = [0] * n_groups
    for house in households:
        total[house.stratum] += 1
        if any(house.ever_missed.get(k, False) for k in classes):
            behind[house.stratum] += 1
    return [b / t if t else 0.0 for b, t in zip(behind, total, strict=True)]


def late60_by_group(respondents: list[Respondent]) -> list[float]:
    """The survey's own answer, weighted, on the same net-worth cut.

    Not circular: ``LATE60`` enters no part of the construction. The population
    is built from income, net worth, tenure, balances and payments; this is a
    separate response, and the model predicts who falls behind from a balance
    sheet while this says who reported falling behind.
    """
    groups = rank_groups(respondents, "networth")
    behind = [0.0] * len(GROUPS)
    total = [0.0] * len(GROUPS)
    for person, group in zip(respondents, groups, strict=True):
        total[group] += person.weight
        behind[group] += person.weight * person.extra.get("LATE60", 0.0)
    return [b / t if t else 0.0 for b, t in zip(behind, total, strict=True)]


def ordering(values: list[float]) -> tuple[int, ...]:
    """Rank positions, so two gradients are compared as orders and not levels."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    rank = [0] * len(values)
    for position, index in enumerate(order):
        rank[index] = position
    return tuple(rank)


# ---------------------------------------------------------------------------
# The resolution rule, which A1d imports from here
# ---------------------------------------------------------------------------
#: ``docs/a1b_prereg.md`` §5.3 and ``docs/a1d_prereg.md`` §5, model side. A group
#: producing fewer than this many expected events under the survey's own rate
#: has produced a rounding rather than a rate.
EXPECTED_EVENT_FLOOR = 5.0

#: Survey side. Two standard errors of the adjacent difference, the standard
#: error naive binomial on the family equivalents, rows over five. Naive is the
#: conservative direction here: it ignores the SCF's design effect, so it
#: admits **more** pairs than a design-corrected rule would and is therefore
#: harder on the model.
PAIR_SIGMA = 2.0

#: The extract carries five implicates of each family, in blocks of five rows,
#: so rows over five is a count of family equivalents, and a standard error
#: taken on rows would be the sampling error of an imputation. Inside a
#: net-worth group there are at least as many distinct families as family
#: equivalents, and on this file more, because one family's implicates can rank
#: into different groups. :func:`distinct_families` counts them, a family being
#: a row index over this.
IMPLICATES = 5

#: Written into the record beside the survey counts, so the record says what
#: each one counts.
TARGET_COUNT_DEFINITIONS = {
    "rows": "implicate rows in the net-worth group",
    "reporting_rows": "implicate rows in the group with LATE60 above zero",
    "family_equivalents": (
        "rows over five, the extract's implicates per family; the standard "
        "errors are taken on this"),
    "distinct_families": (
        "SCF families with at least one implicate in the group; a family whose "
        "implicates rank into several groups is counted in each, so the four "
        "sum to more than the families in the file"),
    "distinct_families_reporting": (
        "of distinct_families, those with LATE60 above zero on at least one of "
        "their implicates in the group"),
}


def target_with_counts(respondents: list[Respondent]) -> dict[str, list]:
    """``LATE60`` by net-worth group, with the sample behind each figure.

    The rate alone cannot say whether an adjacent pair is resolvable. The top
    pair of the net-worth cut is separated by four basis points and eleven
    reporting implicate rows against five, which are four families against two,
    so the counts travel with the rates from here on.

    What each count is made of is in :data:`TARGET_COUNT_DEFINITIONS`, which
    the record carries beside them. The standard errors are taken on the
    family equivalents; the distinct-family counts are reported and enter no
    test.
    """
    groups = rank_groups(respondents, "networth")
    weight = [0.0] * len(GROUPS)
    behind = [0.0] * len(GROUPS)
    rows = [0] * len(GROUPS)
    reporting = [0] * len(GROUPS)
    for person, group in zip(respondents, groups, strict=True):
        weight[group] += person.weight
        behind[group] += person.weight * person.extra.get("LATE60", 0.0)
        rows[group] += 1
        if person.extra.get("LATE60", 0.0) > 0.0:
            reporting[group] += 1
    rate = [b / w if w else 0.0 for b, w in zip(behind, weight, strict=True)]
    equivalents = [n / IMPLICATES for n in rows]
    distinct, distinct_reporting = distinct_families(
        groups,
        [person.extra.get("LATE60", 0.0) > 0.0 for person in respondents],
        len(GROUPS),
    )
    return {
        "_definitions": TARGET_COUNT_DEFINITIONS,
        "rate": rate,
        "family_equivalents": equivalents,
        "rows": rows,
        "reporting_rows": reporting,
        "distinct_families": distinct,
        "distinct_families_reporting": distinct_reporting,
        "standard_error": [
            math.sqrt(p * (1.0 - p) / f) if f > 0 else float("inf")
            for p, f in zip(rate, equivalents, strict=True)
        ],
    }


def distinct_families(groups: list[int], flags: list[bool],
                      n_groups: int) -> tuple[list[int], list[int]]:
    """Distinct SCF families in each group, and those flagged in it.

    The rows come in blocks of :data:`IMPLICATES`, one block per family, so a
    family is a row index over that. A family is counted once in each group any
    of its implicates ranks into, and is flagged in a group when one of its
    implicates there carries the flag.
    """
    if len(groups) % IMPLICATES:
        raise ValueError(
            f"{len(groups)} rows do not come in blocks of {IMPLICATES}, so a row "
            f"index over {IMPLICATES} would not name a family")
    every: list[set[int]] = [set() for _ in range(n_groups)]
    flagged: list[set[int]] = [set() for _ in range(n_groups)]
    for index, (group, flag) in enumerate(zip(groups, flags, strict=True)):
        every[group].add(index // IMPLICATES)
        if flag:
            flagged[group].add(index // IMPLICATES)
    return [len(s) for s in every], [len(s) for s in flagged]


def scorable_pairs(target: dict[str, list],
                   sizes: list[int]) -> tuple[list[int], list[dict]]:
    """Which adjacent pairs both sides can resolve.

    ``docs/a1b_prereg.md`` §5.3 and ``docs/a1d_prereg.md`` §5. Returns the
    indices of the admitted pairs and a row per pair saying why it was admitted
    or not. A pair the source cannot resolve is not evidence about the model,
    and gating on one is `MEASUREMENT.md` checklist item 8: a guard that would
    say the same thing if the thing it guards were broken.
    """
    admitted: list[int] = []
    rows: list[dict] = []
    n = len(target["rate"])
    for i in range(n - 1):
        gap = target["rate"][i] - target["rate"][i + 1]
        sigma = math.hypot(target["standard_error"][i],
                           target["standard_error"][i + 1])
        sigmas = abs(gap) / sigma if sigma > 0 else 0.0
        expected = [sizes[j] * target["rate"][j] for j in (i, i + 1)]
        source_ok = sigmas >= PAIR_SIGMA
        model_ok = min(expected) >= EXPECTED_EVENT_FLOOR
        if source_ok and model_ok:
            admitted.append(i)
        rows.append({
            "pair": f"{GROUPS[i]}/{GROUPS[i + 1]}",
            "gap": gap,
            "sigmas": sigmas,
            "expected_events": expected,
            "source_resolves": source_ok,
            "model_resolves": model_ok,
            "scored": source_ok and model_ok,
        })
    return admitted, rows


def refused_pairs(pair_rows: list[dict]) -> list[dict]:
    """Pairs the source resolves and this population size does not.

    The code refuses any size at which a group admitted by the target-side test
    falls under the model-side floor. Dropping such a pair and scoring the rest
    would let the population size choose which comparisons the criterion makes,
    so a size that leaves one is refused and the criterion is void at it.
    """
    return [r for r in pair_rows if r["source_resolves"] and not r["model_resolves"]]


def _touched(admitted: list[int]) -> list[int]:
    """The groups the admitted pairs speak about, in order and without repeats."""
    out: list[int] = []
    for i in admitted:
        for g in (i, i + 1):
            if g not in out:
                out.append(g)
    return out


def a1b_1(respondents: list[Respondent], sweep: list[dict],
          households: int) -> tuple[Criterion, dict]:
    """Decreasing in net worth on the pairs both sides resolve.

    ``docs/a1b_prereg.md`` §5.3. **Ordinal only**, the direction taken from
    Volume One section 18 rather than from the data, and required in every cell
    of the sweep registered in §8. Four denominator facts forbid a level
    comparison and they are in §5.3; none of them touches an ordering. Which
    pairs are scored is decided by :func:`scorable_pairs`: a pair the survey
    cannot resolve is printed and not scored, and a size at which a pair the
    survey resolves falls under the model-side floor is refused.
    """
    return gradient_verdict(target_with_counts(respondents), sweep, households)


def gradient_verdict(target: dict, sweep: list[dict],
                     households: int) -> tuple[Criterion, dict]:
    """A1b-1 on a target already counted, so a known answer can be fed in."""
    name = "A1b-1 the delinquency gradient"
    sizes = sweep[0]["sizes"]
    payload = {"late60": target["rate"], "target": target, "cells": [],
               "pairs": [], "group_sizes": sizes}
    empty = [GROUPS[g] for g, n in enumerate(sizes) if n == 0]
    if empty:
        return Criterion(
            name, False,
            f"{households:,} households leaves {', '.join(empty)} with no "
            f"member, so the gradient has fewer groups than the target and "
            f"the comparison would fail on its own shape. Group sizes "
            f"{sizes}. Run at a size that fills every group",
            True,
        ), payload

    admitted, pair_rows = scorable_pairs(target, sizes)
    payload["pairs"] = pair_rows
    refused = refused_pairs(pair_rows)
    if refused:
        return Criterion(
            name, False,
            f"{households:,} households is refused as a size for this criterion: "
            + "; ".join(f"the source resolves {r['pair']} at {r['sigmas']:.2f} "
                        f"sigma and the model would expect "
                        f"{min(r['expected_events']):.1f} events in its thinner "
                        f"group, under the floor of {EXPECTED_EVENT_FLOOR}"
                        for r in refused)
            + ". Scoring the remaining pairs would let the population size "
              "choose the comparisons. Run at a size that clears the floor",
            True,
        ), payload
    if not admitted:
        return Criterion(
            name, False,
            "no adjacent pair is resolvable on both sides, so there is no "
            "ordinal statement left to make. "
            + "; ".join(f"{r['pair']} {r['sigmas']:.2f}sigma, expected "
                        f"{min(r['expected_events']):.1f}" for r in pair_rows),
            True,
        ), payload

    touched = _touched(admitted)
    want = ordering([target["rate"][g] for g in touched])
    cells = [
        {
            "seed": cell["seed"],
            "months_per_round": cell["months_per_round"],
            "model": cell["model"],
            "model_with_rent": cell["model_with_rent"],
            "decreasing": all(cell["model"][i] > cell["model"][i + 1]
                              for i in admitted),
            "matches": ordering([cell["model"][g] for g in touched]) == want,
        }
        for cell in sweep
    ]
    decreasing = all(c["decreasing"] for c in cells)
    matches = all(c["matches"] for c in cells)
    detail = (
        "LATE60 by net worth: "
        + ", ".join(
            f"{GROUPS[g]} {target['rate'][g]:.4f} "
            f"({target['reporting_rows'][g]:,} of {target['rows'][g]:,} "
            f"implicate rows, {target['family_equivalents'][g]:,.1f} "
            f"family equivalents)"
            for g in range(len(GROUPS))
        )
        + ". Scored pairs: "
        + ", ".join(pair_rows[i]["pair"] for i in admitted)
        + ". Reported and not scored: "
        + (", ".join(f"{r['pair']} ({r['sigmas']:.2f} sigma, expected events "
                     f"{min(r['expected_events']):.1f})"
                     for i, r in enumerate(pair_rows) if i not in admitted)
           or "none")
        + f". Model, any missed loan payment over the run, over {len(cells)} "
          f"sweep cells: "
        + "; ".join(
            f"seed {c['seed']}x{c['months_per_round']} "
            + "/".join(f"{v:.3f}" for v in c["model"])
            + ("" if c["decreasing"] and c["matches"] else "  <-")
            for c in cells
        )
        + f". Decreasing on every scored pair in every cell: {decreasing}. "
          f"Ordering matches the survey on those groups in every cell: "
          f"{matches}"
        + f". Group sizes at {households:,} households: {sizes}"
        + ". Including rent, reported only: "
        + "/".join(f"{v:.3f}" for v in cells[0]["model_with_rent"])
    )
    payload.update({"cells": cells, "scored_pairs": admitted})
    return Criterion(name, decreasing and matches, detail), payload


# ---------------------------------------------------------------------------
# A1-11. The parameter budget, one shorter than A1's
# ---------------------------------------------------------------------------
def free_list(cost: CostRule) -> list[tuple[str, float]]:
    """Values this repository chose, for a population it did not have to draw.

    ``monetary_topology.cascade.free_parameters`` counts A1's, which includes a
    ``PopulationSpec``. There is no spec here: the population is records, so the
    dispersion is measured and the counts are the file's.
    """
    return [
        ("cost.commute_dependency", cost.commute_dependency),
        ("cost.access_penalty", cost.access_penalty),
        ("cost.grace_basket", float(cost.grace_basket)),
        ("cost.grace_rent", float(cost.grace_rent)),
        ("population.buffer_months", 1.0),
    ]


def a1_11(cost: CostRule) -> Criterion:
    free = free_list(cost)
    return Criterion(
        "A1-11 free parameters within the registered bound",
        len(free) <= FREE_PARAMETER_BOUND,
        f"{len(free)} free against {FREE_PARAMETER_BOUND}: "
        + ", ".join(f"{n}={v:g}" for n, v in free)
        + ". A1 counted six; the service-share dispersion is measured here",
    )


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------
def print_population(records: list[HouseholdRecord], households: int,
                     built: list) -> None:
    covered = distinct_records(records, households)
    print(f"\npopulation, {households:,} households from {len(records):,} "
          f"records, {covered:,} of which got at least one copy "
          f"({covered / len(records):.1%})")
    print("    deterministic largest remainder on the weights; no seed, "
          "nothing drawn")

    by_group: dict[int, list] = {}
    for house in built:
        by_group.setdefault(house.stratum, []).append(house)
    print(f"\n    {'group':<10}{'n':>9}{'share':>8}{'income/mo':>12}"
          f"{'renter':>8}{'mtgd':>8}{'outr':>8}{'card':>10}{'vehicle':>10}")
    for group in sorted(by_group):
        members = by_group[group]
        n = len(members)
        def share(tenure: Tenure) -> float:
            return sum(1 for h in members if h.tenure is tenure) / n
        print(f"    {GROUPS[group]:<10}{n:>9,}{n / len(built):>8.4f}"
              f"{sum(h.income for h in members) / n:>12,.0f}"
              f"{share(Tenure.RENTER):>8.3f}{share(Tenure.MORTGAGED):>8.3f}"
              f"{share(Tenure.OUTRIGHT):>8.3f}"
              f"{sum(h.balances.get(Obligation.CARD, 0.0) for h in members) / n:>10,.0f}"
              f"{sum(h.balances.get(Obligation.AUTO, 0.0) for h in members) / n:>10,.0f}")


def print_stress(built: list) -> dict[str, object]:
    stress = baseline_stress(built)
    print(f"\nbaseline stress, before any shock: {stress['stressed']:,} of "
          f"{stress['households']:,} households ({stress['share']:.3%}) owe "
          f"more each month than they take in")
    print("    kept and counted. A1's constructor made this impossible; these "
          "are published households and dropping them would select on the "
          "outcome the stage is about")
    for group, (n, size) in enumerate(
        zip(stress["by_group"], stress["group_sizes"], strict=True)  # type: ignore[arg-type]
    ):
        if size:
            print(f"    {GROUPS[group]:<10}{n:>9,} of {size:>9,}"
                  f"   {n / size:>7.3%}")
    return stress


def print_payment_check(respondents: list[Respondent],
                        copies: list[int] | None = None) -> dict[str, object]:
    """The payment columns against the balances they are set beside.

    The vehicle leg keeps a literature rate of one sixtieth, and the first two
    lines compare it with the published instalment payment apportioned by
    balance, as this function always did. The extract also carries the vehicle
    payments themselves, the revolving payment is the publisher's construction
    and the mortgage payment covers loans beyond the ``NH_MORT`` ones, so the
    coverage of all three is printed as well. ``copies`` is passed through to
    :func:`payment_coverage`.
    """
    total_weight = sum(r.weight for r in respondents)
    modelled = sum(
        r.weight * r.vehicle * PAYMENT_RATE[Obligation.AUTO]
        for r in respondents
    ) / total_weight
    instalment_balance = sum(r.weight * (r.vehicle + r.extra.get("EDN_INST", 0.0))
                             for r in respondents)
    apportioned = 0.0
    if instalment_balance > 0:
        apportioned = sum(
            r.weight * r.instalment_payment
            * (r.vehicle / (r.vehicle + r.extra.get("EDN_INST", 0.0)))
            for r in respondents
            if (r.vehicle + r.extra.get("EDN_INST", 0.0)) > 0
        ) / total_weight
    card_rate = (
        sum(r.weight * r.card_payment for r in respondents)
        / sum(r.weight * r.card for r in respondents)
    )
    print("\nthe payment columns, checked against the file")
    print(f"    vehicle, one sixtieth of a measured balance   "
          f"{modelled:>8,.0f} a month")
    print(f"    vehicle, published instalment payment shared  "
          f"{apportioned:>8,.0f} a month")
    print(f"    card: the published revolving payment is "
          f"{card_rate:.4f} of the card balance a month over all rows, against "
          f"the {PAYMENT_RATE[Obligation.CARD]:.4f} this project cited. It is "
          f"the publisher's {CARD_PUBLISHER_RATE:.3f} of the card balance plus "
          f"buy-now-pay-later and other lines, not a payment the household "
          f"reported")
    out = {"vehicle_literature": modelled, "vehicle_apportioned": apportioned,
           "card_revpay_over_balance_all_rows": card_rate}
    cover = payment_coverage(respondents, copies)
    if cover:
        m, c, v = cover["mortgage"], cover["card"], cover["vehicle"]
        print(f"    mortgage: {m['rows_paying_beyond_the_NH_MORT_loans']:,} of "
              f"{m['rows_mortgaged']:,} mortgaged rows pay MORTPAY beyond the "
              f"NH_MORT loans, "
              f"{m['rows_with_other_property_or_land_contract_payments']:,} on "
              f"other property or land contracts and "
              f"{m['rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans']:,}"
              f" on the primary residence's home-equity line alone; weighted "
              f"mean {m['mean_MORTPAY']:,.2f} a month against "
              f"{m['mean_nh_mort_loans']:,.2f} on the NH_MORT loans, "
              f"{m['mean_other_property_and_land_contracts']:,.2f} on other "
              f"property and land contracts and "
              f"{m['mean_primary_residence_home_equity_line']:,.2f} on the "
              f"home-equity line")
        print(f"    card: {c['rows_with_more_than_the_card_rate']:,} of "
              f"{c['rows_with_a_card_balance']:,} rows with a card balance "
              f"carry more than the card rate; weighted mean "
              f"{c['mean_REVPAY']:,.2f} against "
              f"{c['mean_card_at_the_publisher_rate']:,.2f} on the card alone "
              f"({c['mean_bnpl_at_the_publisher_rate']:,.2f} of the difference "
              f"is buy-now-pay-later); "
              f"{c['rows_with_a_revolving_payment_and_no_card_balance']:,} rows "
              f"have a revolving payment and no card balance")
        print(f"    vehicle: the published payments average "
              f"{v['mean_published_all_households']:,.2f} a month over all "
              f"households against {v['mean_sixtieth_all_households']:,.2f} at "
              f"one sixtieth ({v['mean_published_holders']:,.2f} against "
              f"{v['mean_sixtieth_holders']:,.2f} among holders); "
              f"{v['rows_with_a_vehicle_balance_where_the_two_differ']:,} of "
              f"the {v['rows_with_a_vehicle_balance']:,} rows with a vehicle "
              f"balance differ")
        unheld = v["rows_with_a_published_vehicle_payment_and_no_vehicle_balance"]
        built = v.get(
            "copies_with_a_published_vehicle_payment_and_no_vehicle_balance")
        print(f"    vehicle: {unheld:,} rows carry a published vehicle payment "
              f"and no vehicle balance"
              + (f", {built:,} households in this population" if built is not None
                 else "")
              + "; the model gives them no vehicle rung, so every vehicle arm "
                "reads the payments on households with a vehicle balance")
        out["coverage"] = cover
    return out


NOT_YET_WRITTEN = ()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--households", type=int, default=DEFAULT_HOUSEHOLDS)
    ap.add_argument("--jobs", type=int, default=None,
                    help="worker processes; the answer does not depend on it")
    ap.add_argument("--sweep-households", type=int,
                    default=DEFAULT_SWEEP_HOUSEHOLDS,
                    help="population size for A1b-1's six-cell sweep, an "
                         "estimation setting under A1-10's licence")
    ap.add_argument("--records", action="store_true",
                    help="print the population and stop")
    ap.add_argument("--carrier", choices=CARRIERS, default=CARRIER_MATCHED,
                    help="which payment each rung stands on; the default puts "
                         "each rung on the payment of its own stock and reads "
                         "the registered construction as an arm")
    args = ap.parse_args()

    print("A1b: the default cascade on a measured population")
    if not ARCHIVE.exists():
        print(f"  {ARCHIVE.name} is absent; run data/fetch_scf.py",
              file=sys.stderr)
        return 1
    try:
        selection = JointSelection.load(SELECTION)
        respondents = read_respondents(ARCHIVE, selection)
        records = to_records(respondents, basket_by_decile(), args.carrier)
        registered_records = (records if args.carrier == CARRIER_REGISTERED
                              else to_records(respondents, basket_by_decile(),
                                              CARRIER_REGISTERED))
    except (InputProblem, ValueError) as exc:
        print(f"  FAILED {exc}", file=sys.stderr)
        return 1

    cost = CostRule()

    # Every run gets its own population. ``CascadeModel.run`` mutates the
    # households it is given, so a second criterion reading the first one's
    # population would be scoring a shock applied twice. Rebuilding is
    # deterministic and costs less than the copy it replaces.
    def fresh() -> list:
        return build_from_records(records, args.households, cost)

    built = fresh()
    print_population(records, args.households, built)
    stress = print_stress(built)
    payments = print_payment_check(respondents,
                                   allocate(records, args.households))
    construction = ({"default": CARRIER_REGISTERED}
                    if args.carrier == CARRIER_REGISTERED
                    else carrier_construction(respondents, records,
                                              args.households))
    if args.carrier == CARRIER_MATCHED:
        o = construction["outflow"]
        carried = construction["mean_debt_payment_carried"]
        print(f"\n  carrier: each rung on the payment of its own stock; "
              f"{o['rows_with_an_outflow']:,} rows pay on no rung, "
              f"{o['mean_outflow']:,.2f} a month per family (revolving "
              f"{o['mean_revolving_beyond_the_card_rate']:,.2f}, MORTPAY "
              f"{o['mean_MORTPAY_beyond_the_mortgage_rung']:,.2f}, vehicle "
              f"{o['mean_vehicle_payment_with_no_vehicle_balance']:,.2f}); "
              f"debt payments carried {carried[CARRIER_MATCHED]:,.2f} a month "
              f"per family against {carried[CARRIER_REGISTERED]:,.2f} as "
              f"registered")
    if args.records:
        return 0

    scored_path = retention_path(PathSpec(periods=SCORED_PERIODS,
                                          seed=PATH_SEED))
    jobs = [
        {"kind": "relieved", "records": records,
         "households": args.households,
         "path": flat_path(ZERO_PERIODS, len(GROUPS))},
        {"kind": "baseline", "records": records,
         "households": args.households,
         "path": flat_path(BASELINE_PERIODS, len(GROUPS))},
        {"kind": "scored", "records": records, "households": args.households,
         "path": scored_path},
    ]
    for seed in SWEEP_SEEDS:
        for months in SWEEP_MONTHS_PER_ROUND:
            jobs.append({
                "kind": "sweep", "records": records,
                "households": args.sweep_households, "seed": seed,
                "months_per_round": months,
                "path": retention_path(PathSpec(periods=SCORED_PERIODS,
                                                seed=seed,
                                                months_per_round=months)),
            })
    arms = carrier_arms(respondents, registered_records)
    if args.carrier == CARRIER_MATCHED:
        arms = {ARM_REGISTERED: registered_records, **arms}
    for arm, arm_records in arms.items():
        jobs.append({"kind": "carrier", "arm": arm, "records": arm_records,
                     "households": args.households, "path": scored_path})
    workers = args.jobs if args.jobs is not None else default_jobs()
    print(f"\n  {len(jobs)} independent runs on {workers} worker(s); the "
          f"answer does not depend on that number")
    done = run_tasks(jobs, workers)
    by_kind = {job["kind"]: out for job, out in zip(jobs, done, strict=True)
               if job["kind"] not in ("sweep", "carrier")}
    sweep = [out for out in done if out["kind"] == "sweep"]
    carriers = {out["arm"]: carrier_reading(out["result"])
                for out in done if out["kind"] == "carrier"}

    zero, reference = a1b_0(by_kind["relieved"]["result"],
                            by_kind["baseline"]["result"])
    scored = by_kind["scored"]["result"]
    unstressed = by_kind["scored"].get("unstressed")

    print(f"\nthe income path, from A0 at seed {PATH_SEED}, "
          f"{SCORED_PERIODS} months")
    for period, row in describe(scored_path):
        print(f"    t={period:<3}" + "".join(f"{v:>10.4f}" for v in row))

    by_wealth, dropped_wealth = by_kind["scored"]["by_wealth"]
    by_income, dropped_income = by_kind["scored"]["by_income"]
    gradient, gradient_detail = a1b_1(respondents, sweep,
                                      args.sweep_households)
    criteria = [
        zero,
        a1_2(scored, unstressed),
        a1_3(scored, cost, reference["final"]),
        a1_6(scored),
        a1_7(scored, by_wealth, dropped_wealth, by_income, dropped_income),
        a1_9(records, cost, scored_path),
        a1_10(cost),
        gradient,
        a1_11(cost),
    ]

    print(f"\nbaseline with no shock, {reference['periods']} periods: "
          + ", ".join(f"{k} {v:.4f}"
                      for k, v in reference["final"].items() if v > 0.0))
    moved = by_kind["baseline"]["displaced_by_tenure"]
    held = by_kind["baseline"]["carriers_at_start"]
    # A household is displaced from a shelter rung, so the denominator is the
    # households that carried one: renters paying rent, owners with a mortgage.
    began = {"RENTER": held["RENTER"]["RENT"],
             "MORTGAGED": held["MORTGAGED"]["MORTGAGE"]}
    reference["displaced_by_tenure"] = moved
    reference["shelter_carriers_at_start"] = began
    print(f"    {reference['displaced_all_tenures']:,} households displaced with "
          f"no shock at "
          f"all: {moved['RENTER']:,} of {began['RENTER']:,} renters and "
          f"{moved['MORTGAGED']:,} of {began['MORTGAGED']:,} mortgaged; the "
          f"series is "
          f"{'still moving' if reference['still_moving'] else 'settled'} at the "
          f"end. Every shocked reading in this stage is reported against this")

    by_tenure = first_default_shares_by_tenure(
        scored, by_kind["scored"]["carriers_at_start"])
    print("\nfirst defaults per household that carried the rung at the start")
    for tenure, row in by_tenure.items():
        cells = [f"{kind} {row[f'per_carrier_at_start_{kind}']:.4f} "
                 f"({row[f'carriers_at_start_{kind}']:,})"
                 for kind in ("card", "auto", "rent", "mortgage", "basket")
                 if row.get(f"per_carrier_at_start_{kind}") is not None]
        print(f"    {tenure:<10}" + ", ".join(cells))

    headline = carrier_reading(scored)
    arm_table = {(ARM_MATCHED if args.carrier == CARRIER_MATCHED
                  else ARM_REGISTERED): headline, **carriers}
    if carriers:
        print("\nthe payment carriers, last period (CARD, AUTO, MORTGAGE)")
        for arm, got in arm_table.items():
            f = got["final"]
            print(f"    {arm:<62}{f['CARD']:.6f}  {f['AUTO']:.6f}  "
                  f"{f['MORTGAGE']:.6f}  "
                  f"{'K shape holds' if got['k_shape'] else 'K SHAPE BREAKS'}")

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed")
    if NOT_YET_WRITTEN:
        print("\n  not yet written, and this run is not the stage:")
        for name in NOT_YET_WRITTEN:
            print(f"    {name}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a1b_default_cascade.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A1b",
                "complete": True,
                "not_yet_written": list(NOT_YET_WRITTEN),
                "late60_gradient": {**gradient_detail,
                                    "households": args.sweep_households},
                "wave": selection.wave,
                "households": args.households,
                "records": len(records),
                "records_covered": distinct_records(records, args.households),
                "seeds": "none; the population is a deterministic allocation",
                "baseline_stress": stress,
                "baseline_no_shock": reference,
                "workers": workers,
                "path": {
                    "source": "A0 retention, terminating claims by stratum",
                    "seed": PATH_SEED,
                    "periods": SCORED_PERIODS,
                    "months_per_round": 1,
                    "shown": [
                        {"period": t, "multipliers": list(row)}
                        for t, row in describe(scored_path)
                    ],
                },
                "first_default_shares": first_default_shares(scored),
                "first_default_shares_by_tenure": {
                    "_definitions": TENURE_RATE_DEFINITIONS, **by_tenure},
                "carrier": construction,
                "carrier_arms": arm_table,
                "first_default_unstressed": unstressed,
                "scored_final": {
                    k.value: scored.delinquent_share[k.value][-1]
                    for k in Obligation
                },
                "payment_check": payments,
                "free_parameters": [
                    {"name": n, "value": v} for n, v in free_list(cost)
                ],
                "literature_parameters": [
                    {"name": n, "value": v, "why": why}
                    for n, v, why in literature_parameters(cost)
                ],
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "void": bool(c.void), "detail": c.detail}
                    for c in criteria
                ],
                "cascade_spec": {"persistence": CascadeSpec().persistence},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
