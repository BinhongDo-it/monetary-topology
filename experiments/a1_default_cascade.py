"""A1: the default cascade. Evaluates the criteria, designs nothing.

Registered in ``docs/a1_prereg.md``. Every threshold, population, denominator
and window this file uses is fixed there, and this file may not introduce one.

Usage::

    python experiments/a1_default_cascade.py
    python experiments/a1_default_cascade.py --seeds 5      # a faster smoke run
    python experiments/a1_default_cascade.py --inputs       # print the inputs
                                                            # and stop

Writes ``results/a1_default_cascade.json``.

**This file is being written in parts, and it says so rather than looking
finished.** The driver prints which criteria exist and which do not, and the
JSON carries ``complete: false`` until every one of A1-1 to A1-11 is in it. A
partial run that reads as a whole stage is the failure mode this note exists to
prevent.

Where every number comes from
-------------------------------
Four retrieved files, each with its own fetcher, its own anchors and its own
manifest. Nothing here is typed in:

===========================================  =============================
``data/processed/cex_income_necessities.csv``  income, basket, rent, payment
``data/processed/cex_consumer_units.csv``      the household count
``data/processed/scf_homeownership.csv``       tenure by net-worth group
``data/processed/dfa_shares.csv``              each instrument by group
``data/processed/z1_ratio.csv``                the two aggregate levels
===========================================  =============================

The one thing this file does decide is the **arithmetic that turns published
per-consumer-unit annual figures into monthly per-household ones**, and it is
three operations: divide by twelve, divide each shelter flow by the share of
consumer units that actually pays it, and divide each aggregate stock by the
consumer-unit count. Each has a guard.

The two arms
--------------
The **stratified arm** is the population of ``docs/a1_prereg.md`` §2.1.

The **representative arm** is that population with the household dimension
collapsed to one vertex, by taking the population-weighted mean of every input.
That is the operation §2.4 calls a category error, performed deliberately, so
the control arm is the collapse itself rather than a separately parameterised
model that might differ for some other reason. ``b1_theorem.md`` Corollary 1 is
what makes it a control rather than a simplification.

A single household has one tenure, so the representative arm is run at each of
them: an owner and a renter. A1-1 says every rung reports zero in both arms, and
with one tenure only half the rungs exist to report anything. This is an
implementation consequence of the arm rather than a change to the criterion, and
§11 of the pre-registration records it.
"""

from __future__ import annotations

import argparse
import copy
import csv
import math
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.cascade import (  # noqa: E402
    BaselineInfeasible,
    CascadeModel,
    CascadeSpec,
    CostRule,
    DrawDegenerate,
    Obligation,
    PopulationSpec,
    StratumInputs,
    Tenure,
    build_population,
    credit_per_household,
    free_parameters,
    literature_parameters,
    max_dispersion,
    mortgage_stock_per_mortgaged,
    per_tenure,
    realised_consumer_credit,
    sourced_parameters,
)

PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"

#: The four groups, bottom half first, as everywhere else in this project.
GROUPS = ("bottom50", "next40", "next9", "top1")

#: ``docs/a1_prereg.md`` §6, from the A3-8 scope diagnostic.
REGISTERED_SEEDS = 20

#: §A1-11. Printed and asserted, never quietly exceeded.
FREE_PARAMETER_BOUND = 12

#: Z.1 is published in millions of dollars. A slip here is invisible to every
#: ratio in the stage and moves every level by a factor of a million, so the
#: unit is named once and the result is banded below.
Z1_UNIT = 1e6

#: Consumer credit per household, from the two published aggregates. Roughly
#: 37,000 dollars at the 2026Q1 level over 135.8 million consumer units. The
#: band is wide enough for any plausible vintage and narrow enough that a unit
#: slip in either term cannot pass.
CREDIT_PER_HOUSEHOLD_BAND = (5_000.0, 200_000.0)

#: The pre-registered population weights, which are the percentile widths.
POPULATION_WEIGHTS = (0.50, 0.40, 0.09, 0.01)

#: ``docs/a1_prereg.md`` §6. Stated, not derived from the arms; see
#: :func:`dispersion_report` for why deriving it has no fixed point.
REGISTERED_DISPERSION = 0.25

#: ``docs/a1_inputs_availability.md`` §4 route (A). Kennickell (1999) on the
#: 1995 SCF: Spearman correlation between income and net worth of 0.76, with
#: the author's own conclusion that "the relationship is not strong". A
#: thirty-year-old vintage, cited as such, and the only rank correlation the
#: inputs check could verify. It is the parameter of the permutation arm and
#: not of the main one.
REGISTERED_RANK_CORRELATION = 0.76


class InputProblem(ValueError):
    """A processed file is absent, or is not the shape this stage reads."""


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else ("pass" if self.passed else "FAIL")
        return f"  {mark}  {self.name}\n        {self.detail}"


# ---------------------------------------------------------------------------
# Reading the four inputs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Inputs:
    """Everything read off disk, in the units the publishers use.

    Annual, per consumer unit, before any tenure division. Keeping the raw
    shape and converting in one place means the conversion is auditable in one
    place, and a reader can print this and compare it against the source
    without undoing three operations first.
    """

    reference_year: str
    income_annual: tuple[float, ...]
    basket_annual: tuple[float, ...]
    rent_annual: tuple[float, ...]
    mortgage_annual: tuple[float, ...]
    #: The three tenures, from whichever source this arm uses. They sum to one.
    renter_share: tuple[float, ...]
    mortgaged_share: tuple[float, ...]
    outright_share: tuple[float, ...]
    #: Which source they came from, carried so the output can say it.
    tenure_source: str
    #: ``cell_to_group[stratum]`` is the wealth group a stratum reports under.
    #: ``None`` in every arm but the permutation one, where a stratum is a
    #: (wealth, income) cell and the criteria are still read by wealth group.
    cell_to_group: tuple[int, ...] | None
    #: The SCF's homeownership by net-worth percentile, kept whichever source
    #: this arm uses, because the second arm is built from it and because a
    #: reader comparing the two rankings needs both in one place.
    scf_homeownership: tuple[float, ...]
    population_share: tuple[float, ...]
    consumer_credit_shares: tuple[float, ...]
    mortgage_shares: tuple[float, ...]
    net_worth_shares: tuple[float, ...]
    mortgage_to_consumer_credit: float
    z1_consumer_credit_millions: float
    z1_home_mortgages_millions: float
    consumer_units: float

    @property
    def n_strata(self) -> int:
        return len(self.income_annual)

    @property
    def credit_per_household(self) -> float:
        """The Z.1 aggregate over the CEX's own count of consumer units."""
        return self.z1_consumer_credit_millions * Z1_UNIT / self.consumer_units


def _shown(path: Path) -> str:
    """Repository-relative where possible, absolute otherwise.

    ``relative_to`` raises on a path outside the tree, and a message that
    raises while reporting a missing file replaces the diagnosis with a
    traceback about the diagnosis.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise InputProblem(
            f"{_shown(path)} is absent. Run its fetcher: this stage "
            f"reads retrieved files and invents no input"
        )
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _by_group(rows: list[dict[str, str]], key: str, column: str,
              where: str) -> tuple[float, ...]:
    """One value per group, in this project's order, refusing a missing group."""
    index = {row[key]: row for row in rows}
    missing = [g for g in GROUPS if g not in index]
    if missing:
        raise InputProblem(
            f"{where} carries no row for {', '.join(missing)}; a group read as "
            f"absent would be silently dropped from every share"
        )
    absent_column = [g for g in GROUPS if column not in index[g]]
    if absent_column:
        raise InputProblem(
            f"{where} has no {column!r} column; it carries "
            f"{', '.join(sorted(index[GROUPS[0]]))}. A processed file written "
            f"by an older fetcher is the usual cause, and re-running the "
            f"fetcher is the fix"
        )
    return tuple(float(index[g][column]) for g in GROUPS)


def read_inputs() -> Inputs:
    """The four processed files, with the guards that make them one population."""
    cex = _rows(PROCESSED / "cex_income_necessities.csv")
    units = _rows(PROCESSED / "cex_consumer_units.csv")
    scf = _rows(PROCESSED / "scf_homeownership.csv")
    dfa = _rows(PROCESSED / "dfa_shares.csv")
    z1 = _rows(PROCESSED / "z1_ratio.csv")

    if len(units) != 1:
        raise InputProblem(
            f"cex_consumer_units.csv has {len(units)} rows; it carries one "
            f"national count and more than one row means two vintages"
        )
    if len(z1) != 1:
        raise InputProblem(
            f"z1_ratio.csv has {len(z1)} rows; it carries one dated pair"
        )

    instrument = {row["instrument"]: row for row in dfa}
    for name in ("consumer_credit", "home_mortgages", "net_worth"):
        if name not in instrument:
            raise InputProblem(
                f"dfa_shares.csv carries no {name} row; the K shape rests on "
                f"the first two and the population on the third"
            )

    def dfa_row(name: str) -> tuple[float, ...]:
        return tuple(float(instrument[name][g]) for g in GROUPS)

    homeowner = _by_group(cex, "group", "homeowner", "the CEX")
    mortgaged = _by_group(cex, "group", "mortgaged", "the CEX")
    renter = _by_group(cex, "group", "renter", "the CEX")
    inputs = Inputs(
        reference_year=units[0]["reference_year"],
        income_annual=_by_group(cex, "group", "income_before_taxes", "the CEX"),
        basket_annual=_by_group(cex, "group", "necessities", "the CEX"),
        rent_annual=_by_group(cex, "group", "rent", "the CEX"),
        mortgage_annual=_by_group(cex, "group", "mortgage_payment", "the CEX"),
        renter_share=renter,
        mortgaged_share=mortgaged,
        outright_share=tuple(o - m for o, m
                             in zip(homeowner, mortgaged, strict=True)),
        tenure_source="CEX Table 1110, by income decile",
        cell_to_group=None,
        scf_homeownership=_by_group(
            scf, "group", "homeownership_rate", "the SCF"
        ),
        population_share=_by_group(scf, "group", "population_share", "the SCF"),
        consumer_credit_shares=dfa_row("consumer_credit"),
        mortgage_shares=dfa_row("home_mortgages"),
        net_worth_shares=dfa_row("net_worth"),
        mortgage_to_consumer_credit=float(
            z1[0]["mortgage_to_consumer_credit"]
        ),
        z1_consumer_credit_millions=float(z1[0]["consumer_credit"]),
        z1_home_mortgages_millions=float(z1[0]["home_mortgages"]),
        consumer_units=float(units[0]["consumer_units"]),
    )

    low, high = CREDIT_PER_HOUSEHOLD_BAND
    got = inputs.credit_per_household
    if not low <= got <= high:
        raise InputProblem(
            f"consumer credit comes to {got:,.0f} per household, outside "
            f"[{low:,.0f}, {high:,.0f}]. Z.1 is in millions of dollars and the "
            f"consumer-unit count is in units; one of the two is not"
        )

    # The population shares are the percentile widths by construction, so a
    # disagreement here means the SCF cut did not land where it was asked to
    # and every per-household level built on it is wrong.
    for group, got_share, want in zip(
        GROUPS, inputs.population_share, POPULATION_WEIGHTS, strict=True
    ):
        if abs(got_share - want) > 0.005:
            raise InputProblem(
                f"the SCF puts {got_share:.4f} of the population in {group} "
                f"against the percentile width {want:.2f}"
            )

    # The two legs are read separately and their ratio is read a third time.
    # It costs nothing to check that the third agrees with the first two, and
    # a disagreement means one of the three columns is from another date.
    implied = (inputs.z1_home_mortgages_millions
               / inputs.z1_consumer_credit_millions)
    if abs(implied - inputs.mortgage_to_consumer_credit) > 1e-6 * implied:
        raise InputProblem(
            f"z1_ratio.csv reports {inputs.mortgage_to_consumer_credit:.6f} "
            f"against {implied:.6f} implied by its own two levels"
        )
    return inputs


def collapse(inputs: Inputs) -> Inputs:
    """The population with its household dimension collapsed to one vertex.

    Every per-group quantity becomes its population-weighted mean and every
    share becomes one. This is the representative arm, and it is built by
    performing the collapse rather than by parameterising a second model, so
    that any difference between the arms is the collapse and nothing else.
    """
    w = inputs.population_share

    def mean(values: tuple[float, ...]) -> tuple[float]:
        return (sum(v * s for v, s in zip(values, w, strict=True)) / sum(w),)

    return replace(
        inputs,
        income_annual=mean(inputs.income_annual),
        basket_annual=mean(inputs.basket_annual),
        rent_annual=mean(inputs.rent_annual),
        mortgage_annual=mean(inputs.mortgage_annual),
        renter_share=mean(inputs.renter_share),
        mortgaged_share=mean(inputs.mortgaged_share),
        outright_share=mean(inputs.outright_share),
        scf_homeownership=mean(inputs.scf_homeownership),
        population_share=(1.0,),
        consumer_credit_shares=(1.0,),
        mortgage_shares=(1.0,),
        net_worth_shares=(1.0,),
    )


def with_scf_tenure(inputs: Inputs) -> Inputs:
    """The registered second arm: tenure ranked by net worth instead.

    ``docs/a1_prereg.md`` §11 registers the ranking mismatch as an arm rather
    than an assumption. The SCF publishes who owns, by net-worth percentile,
    and publishes nothing about how many of those owners carry a mortgage at
    this cut. That split is therefore taken from the CEX and applied to the SCF
    rate, which is stated here because it is a composition of two sources and
    not a reading of one: **who owns** is the SCF's, **what fraction of owners
    still owe** is the CEX's.

    The arm exists to be compared, not to be preferred. If a gated criterion
    comes out differently here, the stage reports both and gates on neither.
    """
    owner = inputs.scf_homeownership
    borrower_share_of_owners = tuple(
        m / (m + o) if (m + o) > 0.0 else 0.0
        for m, o in zip(inputs.mortgaged_share, inputs.outright_share,
                        strict=True)
    )
    mortgaged = tuple(r * f for r, f
                      in zip(owner, borrower_share_of_owners, strict=True))
    return replace(
        inputs,
        renter_share=tuple(1.0 - r for r in owner),
        mortgaged_share=mortgaged,
        outright_share=tuple(r - m for r, m in zip(owner, mortgaged,
                                                   strict=True)),
        tenure_source="SCF 2022, by net-worth percentile, with the CEX's "
                      "mortgaged share of owners",
    )


# ---------------------------------------------------------------------------
# The permutation arm: income rank and wealth rank are not the same ranking
# ---------------------------------------------------------------------------
def _normal_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _normal_quantile(p: float) -> float:
    """Acklam's rational approximation, refined once by Halley's method.

    Written out because the standard library has no inverse normal and this
    file will not take a dependency for one number. The refinement puts the
    error below 1e-15, which is far tighter than the 0.76 it is applied to.
    """
    if not 0.0 < p < 1.0:
        return -math.inf if p <= 0.0 else math.inf
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    low, high = 0.02425, 1 - 0.02425
    if p < low:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p <= high:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    e = _normal_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def _bivariate_normal_cdf(x: float, y: float, rho: float,
                          steps: int = 2000) -> float:
    """``P(X <= x, Y <= y)`` by integrating the conditional over ``X``.

    Trapezoidal over a fixed grid rather than a series expansion: the whole use
    is a four-by-four table of cut points, so a slow exact-enough integral is
    the right trade and its error is checked against the marginals below.
    """
    if x <= -8.0 or y <= -8.0:
        return 0.0
    lo = max(-8.0, -8.0)
    hi = min(x, 8.0)
    if hi <= lo:
        return 0.0
    root = math.sqrt(max(1.0 - rho * rho, 1e-12))
    total = 0.0
    width = (hi - lo) / steps
    for i in range(steps + 1):
        t = lo + i * width
        density = math.exp(-0.5 * t * t) / math.sqrt(2 * math.pi)
        weight = 0.5 if i in (0, steps) else 1.0
        total += weight * density * _normal_cdf((y - rho * t) / root)
    return total * width


def coupling(marginal: tuple[float, ...],
             spearman: float = REGISTERED_RANK_CORRELATION
             ) -> tuple[tuple[float, ...], ...]:
    """``P[wealth group][income group]``, a joint law with those margins.

    A Gaussian copula, because it is the one construction that takes a rank
    correlation and two marginals and returns a joint law without a further
    assumption anyone has to defend. Spearman's rho and the copula's parameter
    are related by ``rho_s = (6 / pi) * arcsin(rho / 2)``, which is exact for
    the Gaussian copula rather than an approximation.

    Both marginals are this project's own percentile widths. That is not an
    assumption about income: the CEX groups are the same 50/40/10 cut, and the
    top decile is split 9 to 1 exactly as the wealth side is, which is the same
    ruling ``data/cex_items.json`` already records.

    Returns rows that sum to one, so ``P[w]`` is the income mix of wealth group
    ``w``. At ``spearman = 1`` it is the identity and the arm collapses onto
    the main one, which is the check that the machinery is doing nothing when
    it is told to do nothing.
    """
    if not -1.0 < spearman < 1.0:
        if spearman == 1.0:
            return tuple(
                tuple(1.0 if i == w else 0.0 for i in range(len(marginal)))
                for w in range(len(marginal))
            )
        raise InputProblem(f"spearman must lie in [-1, 1], got {spearman}")
    rho = 2.0 * math.sin(math.pi * spearman / 6.0)

    edges = [0.0]
    for share in marginal:
        edges.append(edges[-1] + share)
    cuts = [_normal_quantile(min(max(e, 1e-12), 1 - 1e-12)) for e in edges]

    n = len(marginal)
    joint = [[0.0] * n for _ in range(n)]
    for w in range(n):
        for i in range(n):
            joint[w][i] = (
                _bivariate_normal_cdf(cuts[w + 1], cuts[i + 1], rho)
                - _bivariate_normal_cdf(cuts[w], cuts[i + 1], rho)
                - _bivariate_normal_cdf(cuts[w + 1], cuts[i], rho)
                + _bivariate_normal_cdf(cuts[w], cuts[i], rho)
            )
    # The integral is numerical, so the margins come back close rather than
    # exact. They are restored by iterative proportional fitting, which is the
    # standard way to put a table back on known margins without choosing which
    # cell absorbs the error.
    for _ in range(200):
        for w in range(n):
            total = sum(joint[w])
            if total > 0:
                scale = marginal[w] / total
                joint[w] = [v * scale for v in joint[w]]
        for i in range(n):
            total = sum(joint[w][i] for w in range(n))
            if total > 0:
                scale = marginal[i] / total
                for w in range(n):
                    joint[w][i] *= scale
    worst = max(
        max(abs(sum(joint[w]) - marginal[w]) for w in range(n)),
        max(abs(sum(joint[w][i] for w in range(n)) - marginal[i])
            for i in range(n)),
    )
    if worst > 1e-6:
        raise InputProblem(
            f"the coupling does not reproduce its own margins, worst error "
            f"{worst:.2e}; the arm would silently change the population"
        )
    return tuple(
        tuple(v / sum(row) for v in row) for row in (list(r) for r in joint)
    )


def permuted(inputs: Inputs,
             spearman: float = REGISTERED_RANK_CORRELATION) -> Inputs:
    """The registered permutation arm, as a re-stratification.

    ``docs/a1_inputs_availability.md`` §4 route (A). The population is rebuilt
    as one stratum per **(wealth group, income group) cell**, so a household in
    the bottom half by net worth may hold a middle income. Everything published
    by income decile follows the income index; everything published by wealth
    group follows the wealth index; and the model is untouched, because a cell
    is a stratum like any other. The reporting map returned in
    ``cell_to_group`` puts the criteria back on wealth groups.

    Why this rather than a mixture of means: the mismatch is a fact about
    *which households* hold what, and averaging it away would leave the group
    means intact and destroy exactly the heterogeneity this project says the
    dynamics live in.
    """
    n = inputs.n_strata
    table = coupling(inputs.population_share, spearman)
    cells = [(w, i) for w in range(n) for i in range(n)]

    def by_income(values: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(values[i] for _, i in cells)

    def by_wealth(values: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(values[w] for w, _ in cells)

    weight = tuple(table[w][i] * inputs.population_share[w] for w, i in cells)
    total_weight = sum(weight)

    # Each wealth group's instrument share splits across its own cells in
    # proportion to their weight, so the per-household level inside the group
    # is unchanged and only who sits there has moved.
    def split(shares: tuple[float, ...]) -> tuple[float, ...]:
        out = []
        for index, (w, _) in enumerate(cells):
            row = sum(weight[j] for j, (ww, _) in enumerate(cells) if ww == w)
            out.append(shares[w] * weight[index] / row if row > 0 else 0.0)
        return tuple(out)

    return replace(
        inputs,
        income_annual=by_income(inputs.income_annual),
        basket_annual=by_income(inputs.basket_annual),
        rent_annual=by_income(inputs.rent_annual),
        mortgage_annual=by_income(inputs.mortgage_annual),
        renter_share=by_income(inputs.renter_share),
        mortgaged_share=by_income(inputs.mortgaged_share),
        outright_share=by_income(inputs.outright_share),
        scf_homeownership=by_wealth(inputs.scf_homeownership),
        tenure_source=inputs.tenure_source
        + f", permuted onto wealth groups at Spearman {spearman:g}",
        population_share=tuple(w / total_weight for w in weight),
        consumer_credit_shares=split(inputs.consumer_credit_shares),
        mortgage_shares=split(inputs.mortgage_shares),
        net_worth_shares=split(inputs.net_worth_shares),
        cell_to_group=tuple(w for w, _ in cells),
    )


# ---------------------------------------------------------------------------
# Turning them into a population
# ---------------------------------------------------------------------------
def counts_for(inputs: Inputs, households: int) -> tuple[int, ...]:
    """Strata sizes at the requested population size.

    The size is an **estimation setting** and not a behavioural one
    (``docs/a1_prereg.md`` A1-10): households do not interact, so it buys
    precision and changes no behaviour. The licence is tested rather than
    asserted; see :func:`no_interaction_licence`.
    """
    if households < len(inputs.population_share):
        raise InputProblem(
            f"{households} households cannot fill "
            f"{len(inputs.population_share)} strata"
        )
    counts = tuple(round(households * s) for s in inputs.population_share)
    if inputs.cell_to_group is None:
        if any(c == 0 for c in counts):
            raise InputProblem(
                f"{households} households leaves an empty stratum at shares "
                f"{inputs.population_share}; the criteria that compare strata "
                f"would be undefined and would report zero rather than say so"
            )
        return counts
    # In the permutation arm a stratum is a (wealth, income) cell and an empty
    # cell is a fact about the coupling rather than a defect: the top 1% by
    # wealth almost never sits in the bottom half by income. What must not be
    # empty is a **reporting group**, because that is what the criteria compare.
    per_group: dict[int, int] = {}
    for count, group in zip(counts, inputs.cell_to_group, strict=True):
        per_group[group] = per_group.get(group, 0) + count
    empty = sorted(g for g, n in per_group.items() if n == 0)
    if empty:
        raise InputProblem(
            f"{households} households leaves reporting group(s) {empty} with "
            f"no members; the criteria that compare groups would report zero "
            f"rather than say they are undefined"
        )
    return counts


def redistribute(shares: tuple[float, ...], counts: tuple[int, ...],
                 groups: tuple[int, ...]) -> tuple[float, ...]:
    """Move an empty cell's instrument share to the rest of its wealth group.

    A cell that rounds to no households cannot carry debt, and dropping its
    share would quietly shrink the group's aggregate. Its share goes to the
    cells of the same wealth group in proportion to theirs, so the group's
    total is exactly preserved and only its internal distribution moves, which
    is a distribution over households that do not exist.
    """
    out = list(shares)
    for group in sorted(set(groups)):
        members = [i for i, g in enumerate(groups) if g == group]
        alive = [i for i in members if counts[i] > 0]
        total = sum(shares[i] for i in members)
        kept = sum(shares[i] for i in alive)
        if not alive or kept <= 0.0:
            continue
        for i in members:
            out[i] = shares[i] * total / kept if i in alive else 0.0
    return tuple(out)


#: Set by the driver when --dispersion is passed, so every arm is built the
#: same way and the override cannot reach one arm and miss another.
DISPERSION_OVERRIDE: float | None = None


def population_spec(inputs: Inputs, households: int, **overrides) -> PopulationSpec:
    counts = counts_for(inputs, households)
    credit = inputs.consumer_credit_shares
    mortgages = inputs.mortgage_shares
    if inputs.cell_to_group is not None:
        credit = redistribute(credit, counts, inputs.cell_to_group)
        mortgages = redistribute(mortgages, counts, inputs.cell_to_group)
    return PopulationSpec(
        consumer_credit_shares=credit,
        mortgage_shares=mortgages,
        mortgage_to_consumer_credit=inputs.mortgage_to_consumer_credit,
        counts=counts,
        net_worth_shares=inputs.net_worth_shares,
        **({"dispersion": DISPERSION_OVERRIDE}
           if DISPERSION_OVERRIDE is not None and "dispersion" not in overrides
           else {}),
        **overrides,
    )


def stratum_inputs(
    inputs: Inputs, spec: PopulationSpec, tenure: Tenure | None = None
) -> StratumInputs:
    """Monthly, per household, with each shelter flow on the share that pays it.

    ``tenure`` forces every household into one of the three, which is what the
    representative arm needs: a single household holds its dwelling one way, and
    the arm is run once for each way so that no rung goes unexercised. It is not
    available to the stratified arm, where the shares are the published ones.
    """
    if tenure is None:
        renter = inputs.renter_share
        mortgaged = inputs.mortgaged_share
        outright = inputs.outright_share
    else:
        one = (1.0,) * inputs.n_strata
        zero = (0.0,) * inputs.n_strata
        renter = one if tenure is Tenure.RENTER else zero
        mortgaged = one if tenure is Tenure.MORTGAGED else zero
        outright = one if tenure is Tenure.OUTRIGHT else zero

    def monthly(values: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(v / 12.0 for v in values)

    # A share of zero means the arm has no household of that tenure, so the
    # per-payer figure is not merely large, it is undefined. Zero is written
    # rather than a division, and the model never reads it because no household
    # of that tenure is built.
    rent = tuple(
        per_tenure(r / 12.0, share) if share > 0.0 else 0.0
        for r, share in zip(inputs.rent_annual, renter, strict=True)
    )
    mortgage = tuple(
        per_tenure(m / 12.0, share) if share > 0.0 else 0.0
        for m, share in zip(inputs.mortgage_annual, mortgaged, strict=True)
    )
    if all(share == 0.0 for share in mortgaged):
        # An arm with no mortgaged household holds no mortgage stock. The
        # allocator refuses to put debt where no one can carry it, which is the
        # right refusal in the stratified arm and the wrong question here.
        stock = (0.0,) * inputs.n_strata
    else:
        stock = mortgage_stock_per_mortgaged(
            spec, inputs.credit_per_household, mortgaged
        )
    return StratumInputs(
        income=monthly(inputs.income_annual),
        basket=monthly(inputs.basket_annual),
        rent_per_renter=rent,
        mortgage_per_mortgaged=mortgage,
        mortgage_stock_per_mortgaged=stock,
        renter_share=renter,
        mortgaged_share=mortgaged,
        outright_share=outright,
        consumer_credit_per_household=credit_per_household(
            spec, inputs.credit_per_household
        ),
    )


def flat_path(periods: int, n_strata: int, multiplier: float = 1.0):
    """No shock. A1-1's cell, and the baseline every other path departs from."""
    return [tuple([multiplier] * n_strata) for _ in range(periods)]


# ---------------------------------------------------------------------------
# The dispersion the published means will carry
# ---------------------------------------------------------------------------
#: A Beta at mean ``m`` cannot have a coefficient of variation above
#: ``sqrt((1 - m) / m)``, so the spread a stage can ask for is bounded by its
#: own tightest cell. This is derived from the data rather than chosen, and the
#: value it produces is printed and recorded rather than left implicit.
BLENDED_PAYMENT_RATE = 1.0 / (0.5 / 0.02 + 0.5 / (1.0 / 60.0))


def arm_dispersion(inputs: Inputs, households: int
                   ) -> tuple[float | None, str]:
    """The largest dispersion this arm's own means support, and what binds it.

    ``None`` when some cell's published debt exceeds its published disposable:
    that arm has no population at any dispersion, and the reason is a level
    rather than a spread.
    """
    spec = population_spec(inputs, households)
    built = stratum_inputs(inputs, spec)
    per_household = credit_per_household(spec, inputs.credit_per_household)
    weight = {
        Tenure.MORTGAGED: inputs.mortgaged_share,
        Tenure.OUTRIGHT: inputs.outright_share,
        Tenure.RENTER: inputs.renter_share,
    }
    limit, binding = math.inf, ""
    for i in range(inputs.n_strata):
        if spec.counts[i] == 0:
            continue
        service = per_household[i] * BLENDED_PAYMENT_RATE
        for tenure in (Tenure.MORTGAGED, Tenure.OUTRIGHT, Tenure.RENTER):
            if round(spec.counts[i] * weight[tenure][i]) == 0:
                continue
            disposable = built.disposable(i, tenure)
            if disposable <= 0.0:
                return None, (f"stratum {i}, {tenure.value.lower()}: no "
                              f"disposable at all")
            share = service / disposable
            if share >= 1.0:
                return None, (
                    f"stratum {i}, {tenure.value.lower()}: the published debt "
                    f"takes {share:.3f} of the disposable"
                )
            supported = max_dispersion(share)
            if supported < limit:
                limit, binding = supported, (
                    f"stratum {i}, {tenure.value.lower()}, mean {share:.3f}"
                )
    return (None if limit is math.inf else limit), binding


def dispersion_report(inputs: Inputs, households: int
                      ) -> list[tuple[str, float | None, str]]:
    """Each arm's own cap, reported and **not** minimised into a parameter.

    This function used to return the smallest cap across the arms and the
    experiment used it as the dispersion. That was wrong, and the reason is
    worth keeping in the file rather than only in the changelog.

    The cap is ``sqrt((1 - m) / (m (k + 1)))`` at the tightest cell's mean
    ``m``. Every arm added to the list brings a fresh set of off-diagonal
    cells, and among them there is always one with a more extreme ``m``, so the
    minimum falls monotonically towards zero as arms accumulate. **The rule has
    no fixed point.** It is well defined only over a closed list of arms, and
    this stage's list was not closed: the permutation arm exists because a
    tenure ruling made it necessary, days after the criteria were written. An
    infimum over an open set is not an estimate of anything.

    The same shape as the defect the ``复检 i`` note records: a derived quantity
    read as if it were an estimator, when it was never defined on a closed
    object.

    So the caps are printed and the dispersion is whatever the caller states.
    An arm whose cap falls below it is reported as having no population at that
    spread, with the binding cell named.
    """
    report: list[tuple[str, float | None, str]] = []
    for label, arm, tenure in arms(inputs, households):
        if tenure is not None:
            continue
        value, binding = arm_dispersion(arm, households)
        report.append((label, value, binding))
    return report


# ---------------------------------------------------------------------------
# A1-1. Zero calibration
# ---------------------------------------------------------------------------
ZERO_PERIODS = 24


class ArmRefused(Exception):
    """An arm's inputs do not describe a population that can exist.

    ``docs/a1_prereg.md`` §2.6: a group whose published debt cannot be serviced
    out of its published disposable raises rather than rescales. Raised here so
    that one arm being unconstructible is reported as a finding about that arm's
    inputs, and does not take the run down with it.
    """


def build_arm(inputs: Inputs, households: int, seed: int, cost: CostRule,
              tenure: Tenure | None):
    """The population of one arm, or a refusal saying why there is none."""
    spec = population_spec(inputs, arm_households(inputs, households))
    try:
        return build_population(
            spec, stratum_inputs(inputs, spec, tenure), seed, cost
        )
    except (BaselineInfeasible, DrawDegenerate) as exc:
        raise ArmRefused(str(exc)) from exc


def a1_1(inputs: Inputs, seeds: range, households: int,
         cost: CostRule) -> tuple[Criterion, dict[str, str]]:
    """Retention off, every rung exactly zero, every arm, every seed.

    ``MEASUREMENT.md`` item 7, and ``docs/a1_prereg.md`` A1-1: a nonzero here
    voids the stage rather than being reported beside it. The comparison is to
    ``0.0`` exactly and not to a tolerance, because the quantity is a ratio of
    sums of balances and a household that never misses contributes nothing to
    the numerator, so any drift is a defect and not floating point.

    Returns the criterion and the arms that refused to be built, so the caller
    can report them once rather than have them disappear into a detail line.
    """
    worst: list[str] = []
    refused: dict[str, str] = {}
    cells = 0
    for label, arm, tenure in arms(inputs, households):
        for seed in seeds:
            try:
                houses = build_arm(arm, households, seed, cost, tenure)
            except ArmRefused as exc:
                refused[label] = str(exc)
                break
            model = CascadeModel(houses, cost, groups=arm.cell_to_group)
            result = model.run(flat_path(ZERO_PERIODS, arm.n_strata))
            cells += 1
            for kind in Obligation:
                series = result.delinquent_share[kind.value]
                bad = [v for v in series if v != 0.0]
                if bad:
                    worst.append(
                        f"{label} seed {seed} {kind.value} reaches "
                        f"{max(bad):.6f}"
                    )
    built = [label for label, _, _ in arms(inputs, households)
             if label not in refused]
    detail = (
        f"{cells} cells over {len(seeds)} seeds and {ZERO_PERIODS} periods "
        f"in {len(built)} arms, every rung exactly 0.000000"
        if not worst
        else f"{len(worst)} nonzero: " + "; ".join(worst[:4])
    )
    if refused:
        detail += (
            f". {len(refused)} arm(s) could not be built and are reported "
            f"rather than scored: " + ", ".join(sorted(refused))
        )
    return Criterion("A1-1  zero calibration", not worst, detail), refused


def arms(inputs: Inputs, households: int):
    """``(label, inputs, tenure override)`` for every registered arm.

    Five, in two families. The **stratified** family is the population of
    ``docs/a1_prereg.md`` §2.1, once with tenure ranked by income and once
    ranked by net worth, which is the ranking-mismatch arm §11 registers. The
    **representative** family is that population collapsed to one vertex, run
    once at each of the three tenures, because a single household holds its
    dwelling one way and A1-1 asks every rung to report.
    """
    collapsed = collapse(inputs)
    return (
        ("stratified", inputs, None),
        ("stratified:permuted", permuted(inputs), None),
        ("stratified:scf-tenure", with_scf_tenure(inputs), None),
        ("representative:mortgaged", collapsed, Tenure.MORTGAGED),
        ("representative:outright", collapsed, Tenure.OUTRIGHT),
        ("representative:renter", collapsed, Tenure.RENTER),
    )


def arm_households(arm: Inputs, households: int) -> int:
    """One household in the collapsed arm, whatever the stratified size is.

    ``docs/a1_prereg.md`` §2.4: the representative arm is one household. Running
    it at the stratified population size would make it a homogeneous population,
    which is a third thing and not the control this stage registered.
    """
    return households if arm.n_strata > 1 else 1


# ---------------------------------------------------------------------------
# A1-10's licence: households do not interact
# ---------------------------------------------------------------------------
LICENCE_HOUSEHOLDS = 10_000
LICENCE_PERIODS = 18
#: Each stratum's income is cut to this multiple of the watched household's own
#: scheduled obligations, so **every** watched household is squeezed rather than
#: only the poorest. A household that never misses has an arrears series of
#: zeros and agrees with itself under any amount of interaction, which is what
#: ``MEASUREMENT.md`` checklist item 8 asks of this guard: would it say the same
#: thing if the thing it guards were broken? A flat cut does not do it. The next
#: 9% survives a cut to a fifth of its income, because its published basket and
#: shelter are small against an income of 347,000, so the squeeze is calibrated
#: per stratum instead of tuned to a number that happens to work.
LICENCE_SQUEEZE = 0.9


def no_interaction_licence(inputs: Inputs, cost: CostRule) -> Criterion:
    """A household's arrears are identical alone and inside a crowd.

    ``docs/a1_prereg.md`` A1-10 licenses choosing the population size per
    criterion on this property. It is tested rather than asserted, and if it
    fails the licence is withdrawn and every criterion runs at one size.

    **The same household object is used in both runs**, deep-copied so the two
    do not share state. Rebuilding it at two population sizes would not test
    this: the per-household level is computed as an aggregate over a count, so
    a hundred households and ten thousand agree to within a last-bit rounding
    and the comparison would fail on arithmetic that has nothing to do with
    interaction. What is being asked is whether the *presence of others*
    changes a trajectory, so everything except the presence of others is held
    identical and the comparison is exact.

    One household per stratum is watched rather than one household, so a pass
    cannot come from the one index that happens to be insulated.
    """
    spec = population_spec(inputs, LICENCE_HOUSEHOLDS)
    try:
        houses = build_population(spec, stratum_inputs(inputs, spec), 0, cost)
    except (BaselineInfeasible, DrawDegenerate) as exc:
        return Criterion(
            "A1-10 licence  the population size is an estimation setting",
            False,
            f"not tested: the main arm has no population at "
            f"{LICENCE_HOUSEHOLDS:,} households. {exc}",
            void=True,
        )

    first_of: dict[int, int] = {}
    for index, house in enumerate(houses):
        first_of.setdefault(house.stratum, index)
    watched = sorted(first_of.values())

    multipliers = tuple(
        LICENCE_SQUEEZE
        * sum(houses[first_of[s]].due.values())
        / houses[first_of[s]].income
        for s in range(inputs.n_strata)
    )

    def arrears_series(population: list, index: int) -> list[tuple[float, ...]]:
        model = CascadeModel(population, cost)
        series: list[tuple[float, ...]] = []
        for period in range(LICENCE_PERIODS):
            model.step(period, multipliers)
            series.append(tuple(
                population[index].arrears.get(k, 0.0) for k in Obligation
            ))
        return series

    # One deep copy of the whole population, stepped once, and each watched
    # household read out of it. Copying per watched household would be the
    # same answer at four times the cost.
    crowd = copy.deepcopy(houses)
    crowd_model = CascadeModel(crowd, cost)
    crowd_series: dict[int, list[tuple[float, ...]]] = {i: [] for i in watched}
    for period in range(LICENCE_PERIODS):
        crowd_model.step(period, multipliers)
        for index in watched:
            crowd_series[index].append(tuple(
                crowd[index].arrears.get(k, 0.0) for k in Obligation
            ))

    disagreeing: list[int] = []
    moved = 0
    for index in watched:
        alone = arrears_series([copy.deepcopy(houses[index])], 0)
        if alone != crowd_series[index]:
            disagreeing.append(index)
        if any(any(v > 0.0 for v in row) for row in alone):
            moved += 1

    holds = not disagreeing and moved > 0
    return Criterion(
        "A1-10 licence  the population size is an estimation setting",
        holds,
        f"{len(watched)} households, one per stratum, each run alone and "
        f"inside {LICENCE_HOUSEHOLDS:,} at income multipliers "
        + "/".join(f"{m:.3f}" for m in multipliers)
        + ": "
        + (
            f"every arrears series identical over {LICENCE_PERIODS} periods, "
            f"and {moved} of {len(watched)} leave zero, so the comparison has "
            f"something in it. The licence to choose the population size per "
            f"criterion holds"
            if holds
            else f"household(s) {disagreeing} differ, {moved} of "
                 f"{len(watched)} leave zero. The licence is withdrawn and "
                 f"every criterion runs at one size"
        ),
    )


# ---------------------------------------------------------------------------
# A1-11. The parameter budget
# ---------------------------------------------------------------------------
def a1_11(spec: PopulationSpec, cost: CostRule,
          cascade: CascadeSpec) -> Criterion:
    free = free_parameters(spec, cost, cascade)
    return Criterion(
        "A1-11 free parameters within the registered bound",
        len(free) <= FREE_PARAMETER_BOUND,
        f"{len(free)} free against {FREE_PARAMETER_BOUND}: "
        + ", ".join(f"{name}={value:g}" for name, value in free),
    )


# ---------------------------------------------------------------------------
# Printing, which is half of A1-3's attached gate and all of A1-11's
# ---------------------------------------------------------------------------
def print_inputs(inputs: Inputs) -> None:
    print(f"\ninputs, reference year {inputs.reference_year}, annual and per "
          f"consumer unit as published")
    print(f"  {inputs.consumer_units:,.0f} consumer units; Z.1 consumer credit "
          f"{inputs.z1_consumer_credit_millions * Z1_UNIT / 1e12:.3f} trillion "
          f"-> {inputs.credit_per_household:,.0f} per household")
    print(f"  tenure from {inputs.tenure_source}")
    print(f"  {'group':<10}{'income':>10}{'basket':>10}{'rent':>9}"
          f"{'mortgage':>10}{'rent%':>7}{'mtg%':>7}{'out%':>7}"
          f"{'credit':>10}{'mtg stock':>12}")
    spec = population_spec(inputs, 100)
    per_household = credit_per_household(spec, inputs.credit_per_household)
    stock = mortgage_stock_per_mortgaged(
        spec, inputs.credit_per_household, inputs.mortgaged_share
    )
    for i, group in enumerate(GROUPS[: inputs.n_strata]):
        print(f"  {group:<10}{inputs.income_annual[i]:>10,.0f}"
              f"{inputs.basket_annual[i]:>10,.0f}{inputs.rent_annual[i]:>9,.0f}"
              f"{inputs.mortgage_annual[i]:>10,.0f}"
              f"{inputs.renter_share[i]:>7.3f}{inputs.mortgaged_share[i]:>7.3f}"
              f"{inputs.outright_share[i]:>7.3f}"
              f"{per_household[i]:>10,.0f}{stock[i]:>12,.0f}")
    # The per-payer figures, which are what the model actually charges and the
    # place the tenure ruling of 2026-08-15 is visible.
    print(f"\n  per payer, monthly: {'group':<10}{'rent/renter':>13}"
          f"{'payment/mortgaged':>19}")
    for i, group in enumerate(GROUPS[: inputs.n_strata]):
        rent = (inputs.rent_annual[i] / 12.0 / inputs.renter_share[i]
                if inputs.renter_share[i] > 0 else 0.0)
        payment = (inputs.mortgage_annual[i] / 12.0
                   / inputs.mortgaged_share[i]
                   if inputs.mortgaged_share[i] > 0 else 0.0)
        print(f"  {'':<22}{group:<10}{rent:>13,.0f}{payment:>19,.0f}")


def print_parameters(spec: PopulationSpec, cost: CostRule,
                     cascade: CascadeSpec) -> None:
    """A1-10 and A1-11. The behavioural vector is printed once, here."""
    print("\nthe behavioural parameter vector, printed once for every rung")
    for name, value in free_parameters(spec, cost, cascade):
        print(f"    free        {name:<28} {value:g}")
    for name, value, why in literature_parameters(cost):
        print(f"    literature  {name:<28} {value:g}   {why[:60]}")
    print("\n  taken from a publication, not free")
    for name, value, why in sourced_parameters(spec):
        shown = value if isinstance(value, str) else f"{value}"
        print(f"    {name:<28} {shown[:34]:<34} {why[:48]}")


def print_cost_table(cost: CostRule) -> None:
    """A1-3's attached gate: every pair with the attributes that produced it."""
    print("\nthe cost rule at zero arrears, one rule and no per-class multiplier")
    print(f"    {'class':<10}{'c_now':>8}{'c_later':>9}{'resource':>10}"
          f"{'grace':>7}{'bureau':>8}")
    for name, now, later, resource, grace, reports in cost.table():
        print(f"    {name:<10}{now:>8.3f}{later:>9.3f}{resource:>10.3f}"
              f"{grace:>7d}{str(reports):>8}")


def print_feasibility(inputs: Inputs, households: int) -> None:
    """What §2.6 says must be reported rather than absorbed.

    The service a household of this group would pay on its published consumer
    credit, against what is left of its published income after the basket and
    its own tenure's shelter payment. That ratio is the mean of the Beta draw,
    so it has to lie strictly inside zero and one for the group to be feasible
    at baseline by construction. A group approaching one is a finding about the
    data and the constructor is not allowed to rescale it away.
    """
    spec = population_spec(inputs, households)
    per_household = credit_per_household(spec, inputs.credit_per_household)
    built = stratum_inputs(inputs, spec)
    blended = 1.0 / (0.5 / 0.02 + 0.5 / (1.0 / 60.0))
    print("\nbaseline feasibility, the mean of the drawn service share")
    print(f"    {'group':<10}{'tenure':>11}{'share of grp':>13}"
          f"{'disposable':>12}{'service':>10}{'draw mean':>11}"
          f"{'max disp':>10}")
    weight = {
        Tenure.MORTGAGED: inputs.mortgaged_share,
        Tenure.OUTRIGHT: inputs.outright_share,
        Tenure.RENTER: inputs.renter_share,
    }
    for i, group in enumerate(GROUPS[: inputs.n_strata]):
        service = per_household[i] * blended
        for tenure in (Tenure.MORTGAGED, Tenure.OUTRIGHT, Tenure.RENTER):
            if weight[tenure][i] <= 0.0:
                continue
            disposable = built.disposable(i, tenure)
            share = service / disposable if disposable > 0 else float("inf")
            limit = max_dispersion(share) if 0.0 < share < 1.0 else 0.0
            flag = "" if limit >= spec.dispersion else "  <- degenerate"
            print(f"    {group:<10}{tenure.value.lower():>11}"
                  f"{weight[tenure][i]:>13.3f}{disposable:>12,.0f}"
                  f"{service:>10,.0f}{share:>11.3f}{limit:>10.3f}{flag}")
    print(f"    the registered dispersion is {spec.dispersion:g}; a cell whose "
          f"maximum is below it cannot be drawn")


def print_realisation(inputs: Inputs, cost: CostRule, households: int) -> None:
    """The drawn stock against the published target it was built to reproduce."""
    spec = population_spec(inputs, households)
    try:
        houses = build_population(spec, stratum_inputs(inputs, spec), 0, cost)
    except (BaselineInfeasible, DrawDegenerate) as exc:
        print(f"\nrealised consumer credit: the main arm has no population\n"
              f"    {exc}")
        return
    target = credit_per_household(spec, inputs.credit_per_household)
    got = realised_consumer_credit(houses, inputs.n_strata)
    print(f"\nrealised consumer credit against the published target, "
          f"{households:,} households, seed 0")
    for i, group in enumerate(GROUPS[: inputs.n_strata]):
        ratio = got[i] / target[i] if target[i] else 0.0
        print(f"    {group:<10}{got[i]:>12,.0f} against {target[i]:>12,.0f}"
              f"   x{ratio:.4f}")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
#: Criteria not yet written. Named so a partial run cannot read as a whole one.
NOT_YET_WRITTEN = (
    "A1-2 the order is an output",
    "A1-3 K shape",
    "A1-4 and A1-5 card and auto levels, reported",
    "A1-6 the subprime gradient",
    "A1-7 the rent gradient",
    "A1-8 the eviction rung, reported",
    "A1-9 the representative arm as a localizer",
    "A1-10 one parameter set across every rung",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--households", type=int, default=100,
                    help="stratified population size, an estimation setting")
    ap.add_argument("--dispersion", type=float, default=None,
                    help="force a service-share dispersion instead of the "
                         "largest one every arm's published means support; "
                         "whatever is used is reported in the output")
    ap.add_argument("--inputs", action="store_true",
                    help="print the inputs and stop")
    args = ap.parse_args()

    global DISPERSION_OVERRIDE
    DISPERSION_OVERRIDE = args.dispersion

    print("A1: the default cascade")
    if DISPERSION_OVERRIDE is not None:
        print(f"  service-share dispersion overridden to "
              f"{DISPERSION_OVERRIDE:g}, against the registered 0.25")
    try:
        inputs = read_inputs()
    except InputProblem as exc:
        print(f"  FAILED {exc}", file=sys.stderr)
        return 1

    print_inputs(inputs)
    if args.inputs:
        return 0

    caps = dispersion_report(inputs, args.households)
    print("\nthe dispersion each arm's own cells will carry, reported only")
    for label, value, binding in caps:
        shown = "none at any spread" if value is None else f"{value:.3f}"
        print(f"    {label:<24}{shown:>18}   {binding}")
    print(f"    using {DISPERSION_OVERRIDE if DISPERSION_OVERRIDE is not None else REGISTERED_DISPERSION:g}"
          f", stated rather than derived. These caps are NOT minimised into a "
          f"parameter: the minimum falls towards zero as arms are added and the "
          f"arm list is not closed. See docs/a1_prereg.md 11")
    print("    Every cell above is a crossing of two rankings, so a cap is a "
          "property of the crossing and not a finding about any household.")
    if DISPERSION_OVERRIDE is None:
        DISPERSION_OVERRIDE = REGISTERED_DISPERSION

    cost = CostRule()
    cascade = CascadeSpec()
    spec = population_spec(inputs, args.households)
    print_parameters(spec, cost, cascade)
    print_cost_table(cost)
    print_feasibility(inputs, args.households)
    print_realisation(inputs, cost, args.households)

    seeds = range(args.seeds)
    zero_calibration, refused = a1_1(inputs, seeds, args.households, cost)
    if refused:
        print("\narms that could not be built, and why")
        for label, why in sorted(refused.items()):
            print(f"    {label}\n        {why}")
    criteria = [
        zero_calibration,
        no_interaction_licence(inputs, cost),
        a1_11(spec, cost, cascade),
    ]

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed")
    print("\n  not yet written, and this run is not the stage:")
    for name in NOT_YET_WRITTEN:
        print(f"    {name}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a1_default_cascade.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A1",
                "complete": False,
                "not_yet_written": list(NOT_YET_WRITTEN),
                "seeds": args.seeds,
                "households": args.households,
                "reference_year": inputs.reference_year,
                "consumer_units": inputs.consumer_units,
                "credit_per_household": inputs.credit_per_household,
                "tenure_source": inputs.tenure_source,
                "dispersion": DISPERSION_OVERRIDE,
                "dispersion_is_derived": False,
                "dispersion_caps_by_arm": [
                    {"arm": label, "cap": value, "binding": binding,
                     "note": "a property of that arm's crossing of two "
                             "rankings, reported and not minimised into a "
                             "parameter"}
                    for label, value, binding in caps
                ],
                "rank_correlation": REGISTERED_RANK_CORRELATION,
                "arms_refused": refused,
                "free_parameters": [
                    {"name": n, "value": v}
                    for n, v in free_parameters(spec, cost, cascade)
                ],
                "cost_table": [
                    {
                        "class": name,
                        "cost_now": now,
                        "cost_later": later,
                        "resource": resource,
                        "grace": grace,
                        "reports_to_credit": reports,
                    }
                    for name, now, later, resource, grace, reports
                    in cost.table()
                ],
                "criteria": [
                    {
                        "name": c.name,
                        "passed": bool(c.passed),
                        "void": bool(c.void),
                        "detail": c.detail,
                    }
                    for c in criteria
                ],
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
