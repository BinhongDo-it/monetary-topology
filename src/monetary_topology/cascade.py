"""Stage A1: the default cascade, as a population of dated balance sheets.

Pre-registered in ``docs/a1_prereg.md``. This module is the model only. It
computes no criterion, scores nothing, and writes no file; that belongs to
``experiments/a1_default_cascade.py``, so that the model is testable without a
run and the criteria cannot quietly change shape inside it.

What the manuscript says, and where each half lands in this file
-----------------------------------------------------------------
Volume One section 18 gives the cascade: card, then auto loan, then shelter, then
displacement. It is implemented in :class:`CostRule` and in
:meth:`CascadeModel.step`, and **no sequence is written down**. Each obligation
class carries a pair, the cost incurred now and the cost incurred later, and a
household short of cash drops the cheapest-now obligation it holds, then the
next, until what remains can be paid. The sequence is what comes out.

Volume One section 4 gives settlement asymmetry: an obligation due before income arrives
cannot be paid by that income. It is a switch in :class:`CascadeSpec`. Turning it
off is a control arm and is expected to remove most of the stage, because on a
period-average basis most of the defaulting households here are solvent.

The cost of a default is not constant, and three dynamics fall out of that
-----------------------------------------------------------------------------
Each obligation carries a **resource at stake** and a **grace period**, the
number of arrears after which the resource is actually lost. The cost of
defaulting now is the share of that grace the default consumes::

    cost_now(k) = 0                                     if k cannot be saved now
                = resource[k] * (missed[k] + 1) / grace[k]   otherwise

**Falling behind makes a rung harder to default on.** Shelter at no arrears costs
a quarter of its grace; at three arrears the next miss is the eviction, so it
costs the whole resource. A household deep in rent arrears therefore starts
cutting the basket to keep the roof, which is crowding-out arriving as a
consequence of the ramp rather than as a rule of its own.

**What cannot be saved is released first.** If a household could not clear an
obligation's arrears this period even by spending everything it has, paying
anything buys nothing, the cost drops to zero and that rung is dropped before
any other. Without this the greedy ordering would sacrifice the card and the car
to a dwelling that is lost anyway, which is a household that gives up everything
and is evicted regardless.

**Renting and owning are two different clocks.** An eviction is a matter of
months and a foreclosure is not: federal servicing rules bar the first
foreclosure filing until a borrower is more than 120 days delinquent, and the
process itself runs long after that. Giving both tenures one grace made the
mortgage, which is the largest obligation on the books, reach its cliff as fast
as a month's rent, and an owner would abandon it before a renter abandoned a
tenancy. That is backwards, and it was the grace rather than the rule.

**Displacement ends the obligation, and the model claims nothing after it.**
When a household is displaced its shelter obligation is removed rather than
carried: it leaves the delinquency denominator and stops accruing arrears. This
is not a claim that displaced households are housed for free. It is the opposite:
**this model does not know whether they rehouse, or into what**, and inventing a
post-displacement tenancy would put a number where there is no knowledge. The
count of displaced households is reported on its own, and nothing downstream may
read it as a housing outcome.

**Survival comes first, and it is the shorter grace that says so.** The basket
has the shortest grace, so it is the last thing dropped in ordinary conditions.
When income is low enough and obligations heavy enough that both ramps reach one
while what is payable covers neither, the household defaults whether or not it
wants to; that outcome is arithmetic here rather than a switch.

One limitation, stated because it is easy to overclaim
--------------------------------------------------------
**The per-household order is analytic, and the population pattern is not.** Given
distinct now-costs, a single household's default order follows from the rule by
construction; there is nothing to discover in it. What can fail is A1-2, which is
about the *shares* of households whose first default is each class, and those
depend on who holds what. The holdings come from the published DFA shares rather
than from this rule, so A1-2 is a joint test of the cost ordering and the
holdings structure, and it can come out in any order.
``docs/a1_prereg.md`` A1-2 registers the population form for that reason, and
this note exists so the analytic half is never reported as the emergent half.

Two ways to build a population, and they answer different questions
---------------------------------------------------------------------
:class:`StratumInputs` with :func:`build_population` is stage A1's: per-stratum
figures crossed from sources ranked differently, with each household's debt
service drawn as a Beta share of its disposable because the sources give a group
mean and not a spread.

:class:`HouseholdRecord` with :func:`build_from_records` is stage A1b's
(``docs/a1b_prereg.md``): one model household per weighted record from a survey
that measured income, net worth, tenure, balances and payments **on the same
respondent**, so the spread is the file's and nothing is drawn. It has no seed,
no dispersion parameter and no feasibility guarantee, the last because a
published household that cannot service its debts is a fact rather than a
construction error.

What follows describes the first route.

Every per-stratum quantity arrives from a published source through
:class:`StratumInputs`, monthly and per household:

* income and the basket from the CEX decile table, the basket being food,
  utilities, healthcare and commuting **without shelter**, since shelter is a
  rung and a rung has to be defaultable;
* the rent a renter pays and the payment a mortgaged household makes, also from
  the CEX, each divided by the share that actually pays it rather than spread
  over every household;
* housing tenure from the same CEX table, in three parts: renting, owning with a
  mortgage, and owning outright;
* the consumer credit a household of that group carries, and the mortgage
  balance a mortgaged household of that group carries, both from the DFA shares
  at the Z.1 scale.

**Tenure is read from the CEX and not from the SCF, and that is a ruling.** A
shelter flow published by income decile has to be divided by a tenure share
ranked the same way. The SCF publishes tenure by net-worth percentile, which is
the population's own ranking, and dividing one by the other put the next 40%
group's rent at 6,145 dollars a month: not a rent anyone pays, but that group's
whole rent spending divided by the few of them who rent *by wealth*. The two
sources agree nationally, 0.65 against 0.6605. The SCF version is the registered
second arm, and a gated criterion that flips between them is gated in neither.

**The mortgage rung carries a stock and a flow, and they come from different
sources.** The balance is the DFA share of Z.1 home mortgages over that
stratum's mortgaged households; the payment is the CEX line over the same
denominator. Until 2026-08-15 the balance was one month of the payment, which
meant the DFA mortgage shares and the Z.1 ratio were validated, renormalised,
printed and read by nothing: §4.2's inert cell, sitting under the one criterion
whose weighting is a balance.

What is left after the basket and the shelter payment is the household's
**disposable**, and the card and car service is drawn as a share of it. The share
is a Beta draw, so it lies strictly inside zero and one and **every household can
meet its obligations at baseline by construction**. The draw's mean is set to
reproduce the group's published consumer credit, so the aggregate is data and the
spread is the model's.

The earlier version drew obligations independently of income, which made
feasibility a matter of luck: at a hundred households the tail never bit and at a
hundred thousand it always did. A guard that holds only at small samples is not a
guard.

What this module refuses to invent
------------------------------------
Three quantities have **no default here** and must be supplied by the
experiment, because each one decides part of the answer:

- ``consumer_credit_shares`` and ``mortgage_shares``: how each instrument is
  distributed across the wealth groups, which feeds the K shape directly. These
  replaced a residual on 2026-08-13. The model used to set the mortgage stock to
  total liabilities minus consumer credit, and Z.1 at 2026Q1 shows **12.4% of
  household liabilities is neither** (2,666.0 of 21,560.0 bn), so the residual
  route pushed a mixture of municipal debt, commercial mortgages and trade
  payables into the one leg A1-3 rests on. Both legs are now read from the DFA,
  which publishes each instrument by the same wealth groups this model uses.
- ``mortgage_to_consumer_credit``: the aggregate ratio that sets the scale of one
  leg against the other. Unlike the ratio it replaced, both of its terms are
  named instruments, so it carries no residual.
- the three tenure shares: they decide who is exposed to which shelter rung, and
  whether a household is exposed to one at all. Without them a whole stratum
  would share one tenure and the cascade's third rung would exist or not by
  accident.
- ``income_by_stratum``: sets who can absorb a shortfall.
- ``necessities_by_stratum``: the basket, per period. It is a rung with the
  shortest grace rather than a deduction taken off the top. Without it a
  household with any margin banks the remainder forever and no income path short
  of total collapse ever produces a default.
- the income path itself: A0's retention mechanism supplies it. A model that
  invented its own shock would answer a different question from the one A0
  already measured.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Obligation classes
# ---------------------------------------------------------------------------


class Obligation(str, Enum):
    """The five classes. RENT and MORTGAGE are both shelter, differing in tenure.

    ``BASKET`` is food, utilities, healthcare and commuting. It is a rung rather
    than a senior deduction: ordinarily the last thing given up, and not
    impossible to give up. Shelter is deliberately **not** in it, because the
    cascade's whole content is that the dwelling is sacrificed late and can be
    sacrificed at all.
    """

    CARD = "CARD"
    AUTO = "AUTO"
    RENT = "RENT"
    MORTGAGE = "MORTGAGE"
    BASKET = "BASKET"


SHELTER = (Obligation.RENT, Obligation.MORTGAGE)


class Tenure(str, Enum):
    """How a household holds its dwelling, and therefore which rung it carries.

    Three rather than two, because about two fifths of American owners hold
    their dwelling free of any mortgage and the published tenure table says so
    directly: 65% own, 37% carry a mortgage, so 28% own outright. Treating
    every owner as a borrower spreads the mortgage stock and the mortgage
    payment over a denominator half again too large, which halves both.

    An ``OUTRIGHT`` household has **no shelter obligation in this model**. It
    cannot be displaced, and it is not in the denominator of either shelter
    rung. That is a real feature of the population rather than a modelling
    convenience: a third of households cannot lose their dwelling by missing a
    payment, and any cascade that says otherwise is describing someone else.

    It is also a stated limitation. Outright owners pay property tax,
    insurance and maintenance, and a tax lien can take a house. Those are
    separate lines in the CEX and a separate legal process, and this stage does
    not model them; what it claims about outright owners is only that the
    mortgage and rent rungs do not reach them.
    """

    RENTER = "RENTER"
    MORTGAGED = "MORTGAGED"
    OUTRIGHT = "OUTRIGHT"


#: Published tenure shares are whole percents, so three of them reconcile only
#: to about half a point.
TENURE_SUM_TOLERANCE = 2e-2

#: Whether missing a payment on this class degrades future access to claims.
#: Structural, from the institutions rather than from tuning: card, auto and
#: mortgage are furnished to the credit bureaus, ordinary rent is not.
REPORTS_TO_CREDIT = {
    Obligation.CARD: True,
    Obligation.AUTO: True,
    Obligation.MORTGAGE: True,
    Obligation.RENT: False,
    Obligation.BASKET: False,
}

#: The share of a household's own earning capacity that the defaulted resource
#: supports in the period of default. A card supports no resource, so zero.
#: Shelter supports all of it, so one. Both anchors are structural. The
#: vehicle's share is the single free number in the cost rule.
RESOURCE_SUPPORT = {
    Obligation.CARD: 0.0,
    Obligation.MORTGAGE: 1.0,
    Obligation.RENT: 1.0,
    Obligation.BASKET: 1.0,
}


#: Half a cent. Money is denominated in cents, and every comparison in
#: :meth:`CascadeModel.step` is between two sums of the *same* obligations
#: reached by different routes: the constructor totals a household's dues in the
#: order it built them, and the step totals them in the order of
#: :class:`Obligation`. Floating-point addition is not associative, so the two
#: differ in the last bit, and without this a household is judged short by
#: 2e-13 dollars and defaults.
#:
#: **A1b's zero calibration is what found it**, on 589 of 20,000 households
#: whose income had been raised to cover their obligations exactly. A1's
#: calibration could not: its constructor drew a service share strictly inside
#: zero and one, so every household had slack and none sat on the knife edge.
#: A guard that only passes because nothing was ever near the boundary is
#: ``MEASUREMENT.md`` checklist item 8 unanswered.
#:
#: Rounding to cents rather than using a bare epsilon, because the quantity has
#: a unit: nobody is short by a thousandth of a cent, and a tolerance tied to
#: the currency needs no justification tied to the machine.
SHORTFALL_TOLERANCE = 0.005


#: Published shares are rounded to a tenth of a percent, so four of them sum to
#: one only up to that rounding: the real DFA consumer credit vector sums to
#: 1.001. The model's own check used to demand 1e-9 and refused every real
#: vector. This is the tolerance ``monetary_topology.dfa`` already uses, and it
#: is wide enough for the rounding and far too narrow for a missing group, whose
#: absence would move the sum by at least three percentage points.
SHARE_SUM_TOLERANCE = 5e-3


#: Monthly payment as a share of the balance, by class. Literature rather than
#: fitted: card issuers' minimum payment is conventionally about two percent of
#: the balance, and a car loan amortises over sixty months. Both are cited in
#: ``literature_parameters`` and swept.
PAYMENT_RATE = {
    Obligation.CARD: 0.02,
    Obligation.AUTO: 1.0 / 60.0,
}

#: How the drawn service splits between the two consumer-credit rungs. An even
#: split is an assumption rather than a free parameter: nothing tunes it, and it
#: is stated here rather than buried in the constructor.
CARD_SHARE_OF_SERVICE = 0.5


#: A Beta with mean ``m`` cannot have a coefficient of variation above
#: ``sqrt((1 - m) / m)``: that is the limit as its concentration goes to zero,
#: where the distribution is two point masses at zero and one. Asking for a
#: spread near that limit does not give a wide distribution around the mean, it
#: gives a coin flip. The floor below is on the concentration rather than on the
#: dispersion, because the same dispersion is harmless at a mean of 0.1 and
#: degenerate at a mean of 0.94.
MIN_CONCENTRATION = 2.0


def max_dispersion(mean: float, concentration: float = MIN_CONCENTRATION
                   ) -> float:
    """The largest coefficient of variation this mean supports at that floor."""
    if not 0.0 < mean < 1.0:
        return 0.0
    return ((1.0 - mean) / (mean * (concentration + 1.0))) ** 0.5


class DrawDegenerate(ValueError):
    """The requested spread turns the service share into a coin flip.

    Raised rather than clamped. Clamping would silently replace a registered
    parameter with a different one and the results would be reported under the
    registered value, which is the failure ``docs/a1_prereg.md`` §11 exists to
    make impossible.
    """


class BaselineInfeasible(ValueError):
    """A household cannot meet its obligations even with no shock.

    This must be impossible before a run, or A1-1's zero calibration fails for a
    reason that has nothing to do with the mechanism.
    """


@dataclass(frozen=True)
class CostRule:
    """One rule, applied to per-class attributes. No class gets a multiplier.

    ``docs/a1_prereg.md`` A1-3 gates on this: the experiment prints every pair
    with the attributes that produced it, and a mortgage pair produced by a
    different rule fails that criterion even where the inequality holds.

    The grace periods are months. Three of the four have a source and one does
    not, and the one that does not is the one that decides the outcome, so it is
    swept rather than pinned.
    """

    #: Free. The fraction of earning capacity that reaching work by vehicle
    #: supports. Bounded strictly between the two structural anchors, so the
    #: ordering is derived rather than asserted.
    commute_dependency: float = 0.35
    #: Free. The cost of a degraded future claim price, in the same units.
    access_penalty: float = 1.0

    #: **Free, and load-bearing.** How long a household can under-eat before the
    #: shortfall is a loss rather than a postponement. Nothing publishes this;
    #: it is the parameter the stage sweeps.
    grace_basket: int = 1
    #: Literature: the FFIEC uniform retail credit classification charges off an
    #: open-end account at 180 days, which is six monthly cycles.
    grace_card: int = 6
    #: Literature, **unverified**: repossession practice clusters around ninety
    #: days. Cited rather than fitted, and swept beside the basket.
    grace_auto: int = 3
    #: **Free.** Months of rent arrears before the tenancy is lost. Notice
    #: periods are statutory and vary by state in days rather than months, and
    #: no single figure covers the completed process, so this is swept.
    grace_rent: int = 4
    #: Months of mortgage arrears before the dwelling is lost. Its floor has a
    #: source: federal servicing rules bar a first foreclosure filing until the
    #: borrower is more than 120 days delinquent, which is four monthly cycles,
    #: and the process runs well beyond that. The value beyond the floor is
    #: **unverified** and swept beside the rent grace.
    grace_mortgage: int = 12

    def __post_init__(self) -> None:
        if not 0.0 < self.commute_dependency < 1.0:
            raise ValueError(
                "commute_dependency must lie strictly between the card anchor "
                "(0) and the shelter anchor (1)"
            )
        for name in ("grace_basket", "grace_card", "grace_auto",
                     "grace_rent", "grace_mortgage"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least one period")
        if self.grace_mortgage < self.grace_rent:
            raise ValueError(
                "grace_mortgage below grace_rent would make the largest "
                "obligation on the books the first one abandoned; the "
                "regulatory floor alone is four monthly cycles"
            )

    def grace(self, kind: Obligation) -> int:
        if kind is Obligation.BASKET:
            return self.grace_basket
        if kind is Obligation.CARD:
            return self.grace_card
        if kind is Obligation.AUTO:
            return self.grace_auto
        if kind is Obligation.MORTGAGE:
            return self.grace_mortgage
        return self.grace_rent

    def resource(self, kind: Obligation) -> float:
        if kind is Obligation.AUTO:
            return self.commute_dependency
        return RESOURCE_SUPPORT[kind]

    def cost_now(self, kind: Obligation, missed: int = 0,
                 savable: bool = True) -> float:
        """The share of this obligation's grace that defaulting now consumes.

        Zero when the obligation cannot be saved this period: paying into
        something already lost buys nothing, so it is released before anything
        that can still be kept.
        """
        if not savable:
            return 0.0
        consumed = min(missed + 1, self.grace(kind)) / self.grace(kind)
        return self.resource(kind) * consumed

    def cost_later(self, kind: Obligation) -> float:
        return self.access_penalty if REPORTS_TO_CREDIT[kind] else 0.0

    def pair(self, kind: Obligation, missed: int = 0) -> tuple[float, float]:
        return self.cost_now(kind, missed), self.cost_later(kind)

    def table(self) -> list[tuple[str, float, float, float, int, bool]]:
        """Every pair with the attributes that produced it, for A1-3."""
        return [
            (
                kind.value,
                self.cost_now(kind),
                self.cost_later(kind),
                self.resource(kind),
                self.grace(kind),
                REPORTS_TO_CREDIT[kind],
            )
            for kind in Obligation
        ]


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StratumInputs:
    """Per-stratum, per-household, monthly. Every vector has a published source.

    The experiment builds this from the four processed inputs and records the
    vintage of each. Nothing here has a default, because every entry decides part
    of the answer.
    """

    income: tuple[float, ...]
    basket: tuple[float, ...]
    rent_per_renter: tuple[float, ...]
    #: The monthly payment a mortgaged household makes, from the CEX. A
    #: **flow**, and divided by the mortgaged rather than by every owner.
    mortgage_per_mortgaged: tuple[float, ...]
    #: The mortgage balance a mortgaged household carries, from the DFA shares
    #: at the Z.1 scale. A **stock**, and a different quantity from the line
    #: above.
    #:
    #: Both are needed and neither substitutes for the other. The payment is
    #: what a shortfall is measured against; the balance is what the target is
    #: measured on, since HHDC Page 12 is a percent of *balance* 90+ delinquent.
    #: Setting the balance to one month's payment, which is what this model did
    #: until 2026-08-15, weights each owner by their flow instead of their debt
    #: and leaves the published mortgage concentration reading nothing at all.
    mortgage_stock_per_mortgaged: tuple[float, ...]
    #: The three tenures, per stratum, summing to one. Published as whole
    #: percents, so the sum is checked to that rounding rather than exactly.
    renter_share: tuple[float, ...]
    mortgaged_share: tuple[float, ...]
    outright_share: tuple[float, ...]
    consumer_credit_per_household: tuple[float, ...]

    def __post_init__(self) -> None:
        lengths = {len(v) for v in (
            self.income, self.basket, self.rent_per_renter,
            self.mortgage_per_mortgaged, self.mortgage_stock_per_mortgaged,
            self.renter_share, self.mortgaged_share, self.outright_share,
            self.consumer_credit_per_household,
        )}
        if len(lengths) != 1:
            raise ValueError("every vector must have one entry per stratum")
        for name in ("renter_share", "mortgaged_share", "outright_share"):
            if any(not 0.0 <= r <= 1.0 for r in getattr(self, name)):
                raise ValueError(f"{name} must lie in [0, 1]")
        for stratum in range(len(self.income)):
            total = (self.renter_share[stratum] + self.mortgaged_share[stratum]
                     + self.outright_share[stratum])
            if abs(total - 1.0) > TENURE_SUM_TOLERANCE:
                raise ValueError(
                    f"stratum {stratum}: the three tenures sum to {total:.4f}. "
                    f"Every household holds its dwelling one of three ways, so "
                    f"a shortfall here is a share that was dropped rather than "
                    f"a rounding"
                )
            # Whether a zero stock is a defect depends on whether the stratum
            # has any households, which this object does not know. The check
            # lives in ``build_population``, where the count is in hand.

    def shelter_payment(self, stratum: int, tenure: Tenure) -> float:
        """What this tenure hands over for the dwelling each period.

        Zero for an outright owner. Property tax, insurance and maintenance are
        real and are not this: they are separate CEX lines and a separate legal
        process, and the stage says so rather than folding them in at a guess.
        """
        if tenure is Tenure.RENTER:
            return self.rent_per_renter[stratum]
        if tenure is Tenure.MORTGAGED:
            return self.mortgage_per_mortgaged[stratum]
        return 0.0

    def disposable(self, stratum: int, tenure: Tenure) -> float:
        """Income less the basket and the shelter payment of that tenure."""
        return (self.income[stratum] - self.basket[stratum]
                - self.shelter_payment(stratum, tenure))


def per_tenure(per_household: float, share: float) -> float:
    """A per-household mean spread over the tenure that actually pays it.

    The CEX reports a mean over every consumer unit in the group, owners
    included, so a rent of six thousand across a group that is forty percent
    owners is ten thousand per renter. Dividing by the wrong share understates
    the payment by the size of the other tenure.
    """
    if not 0.0 < share <= 1.0:
        raise ValueError(f"share must lie in (0, 1], got {share}")
    return per_household / share


@dataclass
class Household:
    stratum: int
    #: The income group this household's record fell in. Carried because the
    #: two rankings come apart and some criteria are banded by income.
    income_group: int
    tenure: Tenure
    income: float
    necessities: float
    buffer: float
    balances: dict[Obligation, float]
    due: dict[Obligation, float]
    missed: dict[Obligation, int] = field(default_factory=dict)
    ever_missed: dict[Obligation, bool] = field(default_factory=dict)
    #: What was owed and not paid, carried forward. A missed payment does not
    #: vanish, and a household becomes current only by clearing it. Without
    #: this the counter oscillates and nothing ever reaches ninety days.
    arrears: dict[Obligation, float] = field(default_factory=dict)
    first_default: Obligation | None = None
    #: The period at which each class was **first** missed, absent where it
    #: never was. ``docs/a1c_prereg.md`` §2: the manuscript's claim is about one
    #: household over time, and a first default alone cannot say whether the
    #: card went before the car, only which went first of all.
    #:
    #: Recorded rather than derived. Deriving the order from the cost rule would
    #: make A1c-1 a restatement of the rule, which is the failure mode
    #: `cascade.py`'s own note names for A1-2.
    first_missed: dict[Obligation, int] = field(default_factory=dict)
    #: For each class, **which classes were still savable in the period that
    #: class was first missed**. ``docs/a1c_prereg.md`` A1c-2 attributes an
    #: inversion to the release clause when the later class was unsavable in
    #: the period it was first missed *while the earlier one was savable*, and
    #: that is a statement about one period rather than about two.
    #:
    #: A flag per class was not enough and read as two anomalies that were not
    #: anomalies: a household that released its car in period 1 while still
    #: paying its card, and lost the card in period 6, recorded the card's
    #: savability at period 6 and compared it against the car's at period 1.
    #: The whole set is kept so the comparison is inside one period.
    savable_when_missed: dict[Obligation, frozenset] = field(
        default_factory=dict
    )
    #: The **first** and the **last** period at which each class stood at two
    #: or more consecutive missed due dates. ``docs/a1d_prereg.md`` §4: the
    #: survey asks whether a household was sixty days late inside a twelve-month
    #: window, and answering that needs a window test rather than an ever-flag.
    #:
    #: Two integers per class and no trace. A window ``[a, b]`` is answered by
    #: ``last_sixty >= a`` when ``b`` is the run's end, and the first twelve
    #: periods by ``first_sixty <= 11``. Storing the periods themselves would be
    #: sixty booleans a class a household, which at a hundred thousand
    #: households buys nothing these two do not already answer.
    first_sixty: dict[Obligation, int] = field(default_factory=dict)
    last_sixty: dict[Obligation, int] = field(default_factory=dict)
    displaced_at: int | None = None
    #: The tenure at construction. Kept because displacement removes the
    #: obligation, and a displaced renter must still be counted among the
    #: renters the stage started with.
    started_renting: bool = False

    def __post_init__(self) -> None:
        if not self.missed:
            self.missed = dict.fromkeys(self.balances, 0)
        if not self.ever_missed:
            self.ever_missed = dict.fromkeys(self.balances, False)
        if not self.arrears:
            self.arrears = dict.fromkeys(self.balances, 0.0)
        if Obligation.RENT in self.balances:
            self.started_renting = True

    @property
    def owns(self) -> bool:
        """Either kind of owner. Kept because several readers ask only this."""
        return self.tenure is not Tenure.RENTER


@dataclass(frozen=True)
class PopulationSpec:
    """Every share here is published. See ``docs/a1_prereg.md`` section 6.

    Three inputs have **no default on purpose**, and all three decide part of the
    answer: the two share vectors distribute each instrument across the wealth
    groups, and the aggregate ratio sets the scale of one leg against the other.
    A default would be this repository inventing the numbers that produce its own
    K shape. The experiment supplies them from the DFA and from Z.1, and records
    both vintages.
    """

    consumer_credit_shares: tuple[float, ...]
    mortgage_shares: tuple[float, ...]
    mortgage_to_consumer_credit: float
    counts: tuple[int, ...] = (50, 40, 9, 1)
    net_worth_shares: tuple[float, ...] = (0.025, 0.296, 0.363, 0.316)
    #: Free. The coefficient of variation of the drawn service share, so a
    #: stratum is a distribution rather than a point. Zero gives a deterministic
    #: population.
    dispersion: float = 0.25
    #: Free. Opening cash buffer, in months of scheduled obligations.
    buffer_months: float = 1.0

    def __post_init__(self) -> None:
        if len(self.counts) != len(self.net_worth_shares):
            raise ValueError("counts and net_worth_shares disagree in length")
        for name, shares in (
            ("consumer_credit_shares", self.consumer_credit_shares),
            ("mortgage_shares", self.mortgage_shares),
        ):
            if len(shares) != len(self.counts):
                raise ValueError(f"{name} must have one entry per stratum")
            if any(x < 0.0 for x in shares):
                raise ValueError(f"{name} carries a negative share")
            # A vector that does not sum to one means a group's identifier did
            # not resolve and its share was silently dropped, which is exactly
            # the failure the inputs check asked this model to refuse.
            if abs(sum(shares) - 1.0) > SHARE_SUM_TOLERANCE:
                raise ValueError(
                    f"{name} sums to {sum(shares):.6f} rather than 1; a missing "
                    f"group must fail here rather than be absorbed by the others"
                )
        if self.mortgage_to_consumer_credit <= 0.0:
            raise ValueError("mortgage_to_consumer_credit must be positive")
        # Renormalise explicitly, so the allocation is exact and the published
        # rounding is visible in one place rather than spread over every group.
        for name in ("consumer_credit_shares", "mortgage_shares"):
            shares = getattr(self, name)
            total = sum(shares)
            object.__setattr__(
                self, name, tuple(x / total for x in shares)
            )


def credit_per_household(
    spec: PopulationSpec, aggregate_mean: float
) -> tuple[float, ...]:
    """Per-household consumer credit by stratum, from the published shares.

    ``aggregate_mean`` is the mean over every household, which the experiment
    gets from Z.1 over the household count. A group holding a share of the total
    larger than its share of the households carries proportionately more, which
    is the whole content of the bottom half holding 51.8% of consumer credit
    against 50% of the households.
    """
    total = sum(spec.counts)
    out: list[float] = []
    for stratum, (share, count) in enumerate(
        zip(spec.consumer_credit_shares, spec.counts, strict=True)
    ):
        if count == 0:
            # An empty stratum holds nothing. It has to be allowed rather than
            # refused, because the permutation arm's population is a grid of
            # (wealth, income) cells and the corners of that grid are genuinely
            # empty: the top 1% by wealth is almost never in the bottom half by
            # income. A share sitting on an empty cell is a different matter and
            # is a debt with no holder.
            if share > 0.0:
                raise ValueError(
                    f"stratum {stratum} holds {share:.6f} of the consumer "
                    f"credit and has no households; the debt would have "
                    f"nowhere to sit"
                )
            out.append(0.0)
            continue
        out.append(aggregate_mean * total * share / count)
    return tuple(out)


def mortgage_stock_per_mortgaged(
    spec: PopulationSpec,
    consumer_credit_mean: float,
    mortgaged_share: tuple[float, ...],
) -> tuple[float, ...]:
    """Mortgage balance per mortgaged household, from the published shares.

    The twin of :func:`credit_per_household`, and the reason
    ``mortgage_shares`` and ``mortgage_to_consumer_credit`` exist. Until
    2026-08-15 neither was read by anything: both were validated, renormalised
    and printed, and the mortgage rung took its balance from one month of the
    CEX payment. That is ``docs/a1_prereg.md`` §4.2's inert cell, in the one
    place the stage could least afford it, since A1-3's mortgage leg is
    balance-weighted and the concentration of mortgage debt upward is exactly
    what the DFA publishes.

    The aggregate is set from the consumer-credit aggregate through the Z.1
    ratio, so one scale carries both legs and neither is a residual. The owner
    count uses the same rounding :func:`build_population` uses, so the model's
    realised aggregate reproduces the published one rather than missing it by
    the rounding of a stratum's owner count.

    The denominator is the **mortgaged**, not every owner. About two fifths of
    American owners hold their dwelling free of any mortgage, and putting the
    stock on all of them understates the balance of the households that
    actually owe it by that fraction. The CEX payment is divided by the same
    denominator, so the flow and the stock stay on one population and their
    ratio is the one the two sources imply.
    """
    total = sum(spec.counts)
    aggregate = consumer_credit_mean * total * spec.mortgage_to_consumer_credit
    out: list[float] = []
    for stratum, (share, count, rate) in enumerate(
        zip(spec.mortgage_shares, spec.counts, mortgaged_share, strict=True)
    ):
        borrowers = round(count * rate)
        if borrowers == 0:
            if share > 0.0:
                raise ValueError(
                    f"stratum {stratum} holds {share:.3f} of the mortgage stock "
                    f"and has no mortgaged households at {count} households "
                    f"and a rate of {rate:.3f}. The debt would have nowhere to "
                    f"sit, and silently dropping it would move the share the K "
                    f"shape rests on"
                )
            out.append(0.0)
            continue
        out.append(aggregate * share / borrowers)
    return tuple(out)


def build_population(
    spec: PopulationSpec,
    inputs: StratumInputs,
    seed: int,
    cost: CostRule | None = None,
) -> list[Household]:
    """One household per member of each stratum, feasible at baseline by design.

    Within a stratum the mortgaged come first, then the outright owners, then
    the renters, each block sized ``round(count * share)``. That keeps tenure
    reproducible without spending a random draw on it. The renters take what is
    left rather than their own rounded count, so the three blocks always fill
    the stratum exactly and no household is left without a tenure. The card and
    car service is the only drawn quantity: a Beta share of what is left after
    the basket and the shelter payment, with its mean set to reproduce the
    group's published consumer credit at the payment rates above.

    The consumer credit **stock** is therefore an output rather than an input,
    and ``realised_consumer_credit`` reports how far the draw's realisation sits
    from the published target.
    """
    cost = cost or CostRule()
    rng = random.Random(seed)
    if len(inputs.income) != len(spec.counts):
        raise ValueError("StratumInputs and counts disagree in length")

    # Harmonic, not arithmetic. The service splits by a fixed share and each
    # half buys stock at its own rate, so the stock a given service implies is
    # ``S * (w / r_card + (1 - w) / r_auto)`` and the rate that inverts it is the
    # weighted harmonic mean. An arithmetic mean here reproduces the published
    # credit to within a percent, which is small enough to pass unnoticed and
    # wrong enough to bias every group in the same direction.
    blended_rate = 1.0 / (
        CARD_SHARE_OF_SERVICE / PAYMENT_RATE[Obligation.CARD]
        + (1.0 - CARD_SHARE_OF_SERVICE) / PAYMENT_RATE[Obligation.AUTO]
    )

    households: list[Household] = []
    for stratum, count in enumerate(spec.counts):
        n_mortgaged = round(count * inputs.mortgaged_share[stratum])
        n_outright = round(count * inputs.outright_share[stratum])
        if n_mortgaged + n_outright > count:
            raise ValueError(
                f"stratum {stratum}: {n_mortgaged} mortgaged and {n_outright} "
                f"outright exceed {count} households"
            )
        # The service a household of this group would pay on the published
        # consumer credit, which is what the draw's mean has to reproduce.
        target_service = (
            inputs.consumer_credit_per_household[stratum] * blended_rate
        )
        for i in range(count):
            if i < n_mortgaged:
                tenure = Tenure.MORTGAGED
                if inputs.mortgage_stock_per_mortgaged[stratum] <= 0.0:
                    raise ValueError(
                        f"stratum {stratum} has {n_mortgaged} mortgaged "
                        f"households and no mortgage stock; the balance the K "
                        f"shape is measured on cannot be zero where the "
                        f"obligation exists"
                    )
            elif i < n_mortgaged + n_outright:
                tenure = Tenure.OUTRIGHT
            else:
                tenure = Tenure.RENTER
            disposable = inputs.disposable(stratum, tenure)
            if disposable <= 0.0:
                raise BaselineInfeasible(
                    f"stratum {stratum}: the basket and the shelter payment "
                    f"already exceed income before any debt, so no share of a "
                    f"disposable that does not exist can be drawn"
                )
            mean_share = target_service / disposable
            if not 0.0 < mean_share < 1.0:
                raise BaselineInfeasible(
                    f"stratum {stratum}: the published consumer credit implies "
                    f"a service of {target_service:.2f} against a disposable of "
                    f"{disposable:.2f}, a share of {mean_share:.3f}. A group "
                    f"whose data say it cannot service its own debt is a "
                    f"finding, and it must not be rescaled away here"
                )
            limit = max_dispersion(mean_share)
            if spec.dispersion > limit:
                raise DrawDegenerate(
                    f"stratum {stratum}, {tenure.value.lower()}: the published "
                    f"debt takes {mean_share:.3f} of the disposable, and a "
                    f"Beta with that mean cannot carry a dispersion of "
                    f"{spec.dispersion:.3f}. Its concentration would fall to "
                    f"{max((1.0 - mean_share) / (spec.dispersion ** 2 * mean_share) - 1.0, 0.0):.3f}, "
                    f"which is two point masses at zero and one rather than a "
                    f"spread. The largest dispersion this mean supports is "
                    f"{limit:.3f}"
                )
            share = _beta(rng, mean_share, spec.dispersion)
            service = share * disposable

            card_service = CARD_SHARE_OF_SERVICE * service
            auto_service = service - card_service
            balances = {
                Obligation.CARD: card_service / PAYMENT_RATE[Obligation.CARD],
                Obligation.AUTO: auto_service / PAYMENT_RATE[Obligation.AUTO],
            }
            due = {
                Obligation.CARD: card_service,
                Obligation.AUTO: auto_service,
            }

            # An outright owner carries no shelter rung at all. It is not in
            # either denominator and it cannot be displaced, which is a fact
            # about a third of American households rather than a simplification.
            #
            # For the other two the balance differs in kind. A mortgage has a
            # stock and the balance is that stock, because HHDC Page 12 is a
            # percent of balance and the DFA's published concentration of
            # mortgage debt has to be what carries the weight. Rent has no
            # stock at all: a tenancy is a flow, the rent rung's criteria are
            # counted over renter households rather than over balances
            # (``docs/a1_prereg.md`` §3.1), and one period is the only balance
            # it can carry.
            payment = inputs.shelter_payment(stratum, tenure)
            if tenure is Tenure.MORTGAGED:
                balances[Obligation.MORTGAGE] = (
                    inputs.mortgage_stock_per_mortgaged[stratum]
                )
                due[Obligation.MORTGAGE] = payment
            elif tenure is Tenure.RENTER:
                balances[Obligation.RENT] = payment
                due[Obligation.RENT] = payment

            balances[Obligation.BASKET] = inputs.basket[stratum]
            due[Obligation.BASKET] = inputs.basket[stratum]

            scheduled = sum(due.values())
            income = inputs.income[stratum]
            if scheduled > income:
                raise BaselineInfeasible(
                    f"stratum {stratum}: scheduled {scheduled:.2f} exceeds "
                    f"income {income:.2f} with no shock applied"
                )
            households.append(
                Household(
                    stratum=stratum,
                    income_group=stratum,
                    tenure=tenure,
                    income=income,
                    necessities=inputs.basket[stratum],
                    buffer=scheduled * spec.buffer_months,
                    balances=balances,
                    due=due,
                )
            )
    return households


def realised_consumer_credit(
    households: list[Household], n_strata: int
) -> list[float]:
    """Mean card plus auto stock per household, by stratum.

    Reported against ``StratumInputs.consumer_credit_per_household`` so the
    distance between the draw's realisation and the published target is visible
    rather than assumed to be zero.
    """
    totals = [0.0] * n_strata
    counts = [0] * n_strata
    for house in households:
        totals[house.stratum] += (
            house.balances.get(Obligation.CARD, 0.0)
            + house.balances.get(Obligation.AUTO, 0.0)
        )
        counts[house.stratum] += 1
    return [t / c if c else 0.0 for t, c in zip(totals, counts, strict=True)]


def _beta(rng: random.Random, mean: float, dispersion: float) -> float:
    """A share strictly inside zero and one, with the given mean.

    ``dispersion`` is the coefficient of variation the draw aims for; it is
    turned into a Beta concentration. Zero dispersion returns the mean, so a
    deterministic population is available for the arms that need one.
    """
    if dispersion <= 0.0:
        return mean
    concentration = max((1.0 - mean) / (dispersion**2 * mean) - 1.0, 1e-6)
    alpha = mean * concentration
    beta = (1.0 - mean) * concentration
    if alpha <= 0.0 or beta <= 0.0:
        return mean
    return rng.betavariate(alpha, beta)


# ---------------------------------------------------------------------------
# A population of measured households, for stage A1b
# ---------------------------------------------------------------------------


class AllocationProblem(ValueError):
    """The requested population cannot represent the records it is built from."""


@dataclass(frozen=True)
class HouseholdRecord:
    """One published household, every figure measured on the same respondent.

    ``docs/a1b_prereg.md`` §2. This is the alternative to :class:`StratumInputs`
    and it exists because the stratum route could not say how debt and income
    covary inside a group: it knew a group mean and had to invent a spread. Here
    the spread is the file's.

    **Units are in the names.** The SCF publishes income annually and its rent
    and mortgage payments monthly, so a reader converting one and not the other
    would produce a household paying its year's rent every month. Balances carry
    no suffix because a stock has no period.

    ``group`` is the reporting group, which is the net-worth group. It is the
    model's ``stratum``: with records there are no cells to aggregate over, so
    the two coincide and ``CascadeModel`` needs no group map.
    """

    weight: float
    #: The net-worth group. It is the model's ``stratum`` and what most criteria
    #: report by.
    group: int
    #: The income group, on the same four-way cut. A household has two rankings
    #: and they come apart: 2.2% of the top 1% by net worth sits in the bottom
    #: half by income. A criterion whose source is banded by income has to be
    #: read on this one, and carrying both is what makes that possible without
    #: building the population twice.
    income_group: int
    income_monthly: float
    #: The one quantity not measured on this respondent. The SCF collects food
    #: at home and neither utilities, healthcare nor commuting, so the basket is
    #: the CEX's, assigned by income rank. ``docs/a1b_prereg.md`` §2.2.
    basket_monthly: float
    tenure: Tenure
    rent_monthly: float
    mortgage_payment_monthly: float
    mortgage_balance: float
    card_balance: float
    #: Measured, not a rate applied to the balance. The published revolving
    #: payment is 3.7% of the revolving balance a month against the 2% minimum
    #: this project cited from practice, and the difference is a doubling of the
    #: card rung's service.
    card_payment_monthly: float
    #: The vehicle payment is **not** separately published: the extract's
    #: instalment payment covers vehicles, education and other together. So this
    #: leg keeps the literature rate of one sixtieth on a measured balance, and
    #: it is the only payment rate in A1b that is not measured. The check is in
    #: the experiment: apportioning the published instalment payment by balance
    #: gives 117 a month against this rule's 123.
    vehicle_balance: float
    #: Liquid assets, the measured cushion of ``docs/a1d_prereg.md`` §3.
    #: Checking, savings, money market and call accounts. **Zero by default**,
    #: which is what A1b's population carries, and a stage asking for a measured
    #: cushion has to say so: :func:`build_from_records` refuses
    #: ``Cushion.MEASURED`` on records that all read zero, because a population
    #: with no cushion anywhere is the shape a forgotten column makes.
    liquid: float = 0.0

    @property
    def vehicle_payment_monthly(self) -> float:
        return self.vehicle_balance * PAYMENT_RATE[Obligation.AUTO]


class Cushion(str, Enum):
    """Where a household's starting cash comes from.

    Two mechanisms, both on the record, neither replacing the other.
    ``docs/a1d_prereg.md`` §3 registers the second and says why: the first is
    the last constructed quantity in a stage whose claim is that the population
    is measured, and it leaves net worth with no channel into behaviour at all.
    """

    #: A1b. One month of the household's own scheduled obligations, scaled by
    #: ``buffer_months``. No source, and the same shape for every household.
    SCHEDULED = "SCHEDULED"
    #: A1d. The record's measured liquid assets, with **no floor**. A household
    #: reporting no liquid assets starts with nothing.
    MEASURED = "MEASURED"


def allocate(records: list[HouseholdRecord], households: int) -> list[int]:
    """How many model households each record becomes. Deterministic.

    Largest remainder on the weights, so the allocation is exact, reproducible
    and carries **no random draw at all**. A1's population needed a seed because
    its service share was drawn; nothing here is drawn, so A1b has no seed and
    its seed count is not a setting.

    A record whose weight is small against ``households / total`` gets no copy.
    That is representation rather than error, and the experiment reports how many
    records were dropped so a population too small to carry the file is visible
    rather than silent.
    """
    if households < 1:
        raise AllocationProblem("a population needs at least one household")
    total = sum(r.weight for r in records)
    if total <= 0.0:
        raise AllocationProblem("the weights do not sum to anything positive")

    exact = [households * r.weight / total for r in records]
    counts = [int(x) for x in exact]
    short = households - sum(counts)
    if short:
        order = sorted(
            range(len(records)),
            key=lambda i: (-(exact[i] - counts[i]), i),
        )
        for i in order[:short]:
            counts[i] += 1
    return counts


def build_from_records(
    records: list[HouseholdRecord],
    households: int,
    cost: CostRule | None = None,
    buffer_months: float | None = None,
    cushion: Cushion = Cushion.SCHEDULED,
) -> list[Household]:
    """One model household per allocated copy, nothing invented.

    Nothing here can raise :class:`BaselineInfeasible`. A household whose
    scheduled obligations exceed its income is kept, because it is in the file
    and because dropping it would select on the outcome the stage is about.
    :func:`baseline_stress` reports how many there are, and
    ``docs/a1b_prereg.md`` §3 registers that the zero calibration is a constant
    rather than a zero for exactly this reason.

    ``cushion`` selects which of :class:`Cushion`'s two mechanisms fills the
    buffer. The default is A1b's, so A1b's record stays reproducible on this
    code. ``buffer_months`` belongs to that mechanism alone and passing it
    beside ``MEASURED`` is refused rather than ignored: a silently discarded
    parameter is a free parameter the count would not see.
    """
    cost = cost or CostRule()
    if cushion is Cushion.MEASURED:
        if buffer_months is not None:
            raise AllocationProblem(
                "buffer_months belongs to the scheduled cushion and has no "
                "meaning beside a measured one. docs/a1d_prereg.md §3 removes "
                "it from the free list, and accepting it here would put it "
                "back without the count changing"
            )
        if not any(r.liquid > 0.0 for r in records):
            raise AllocationProblem(
                "a measured cushion was asked for and every record reads zero "
                "liquid assets. That is the shape a column read under the "
                "wrong name makes, and a population with no cushion anywhere "
                "would score as a mechanism finding"
            )
    elif buffer_months is None:
        buffer_months = 1.0
    counts = allocate(records, households)
    out: list[Household] = []
    for record, copies in zip(records, counts, strict=True):
        if copies == 0:
            continue
        balances = {
            Obligation.CARD: record.card_balance,
            Obligation.AUTO: record.vehicle_balance,
            Obligation.BASKET: record.basket_monthly,
        }
        due = {
            Obligation.CARD: record.card_payment_monthly,
            Obligation.AUTO: record.vehicle_payment_monthly,
            Obligation.BASKET: record.basket_monthly,
        }
        if record.tenure is Tenure.MORTGAGED:
            balances[Obligation.MORTGAGE] = record.mortgage_balance
            due[Obligation.MORTGAGE] = record.mortgage_payment_monthly
        elif record.tenure is Tenure.RENTER:
            balances[Obligation.RENT] = record.rent_monthly
            due[Obligation.RENT] = record.rent_monthly
        # A class with no balance is a class the household does not hold. Left
        # in, it would sit in the delinquency denominator at zero and dilute
        # nothing while counting as held, which is a membership error.
        balances = {k: v for k, v in balances.items() if v > 0.0}
        due = {k: v for k, v in due.items() if k in balances}

        scheduled = sum(due.values())
        buffer = (record.liquid if cushion is Cushion.MEASURED
                  else scheduled * buffer_months)
        for _ in range(copies):
            out.append(Household(
                stratum=record.group,
                income_group=record.income_group,
                tenure=record.tenure,
                income=record.income_monthly,
                necessities=record.basket_monthly,
                buffer=buffer,
                balances=dict(balances),
                due=dict(due),
            ))
    if not out:
        raise AllocationProblem(
            f"{households} households allocated no copies; the weights and the "
            f"population size do not meet"
        )
    return out


def baseline_stress(households: list[Household]) -> dict[str, object]:
    """Households owing more each month than they take in, before any shock.

    Reported rather than repaired. In A1 this was impossible by construction and
    the constructor raised; here it is a property of the file, and §2.6's rule
    finally has its scope, because these are published households.
    """
    n_strata = max((h.stratum for h in households), default=-1) + 1
    stressed = [h for h in households if sum(h.due.values()) > h.income]
    return {
        "households": len(households),
        "stressed": len(stressed),
        "share": len(stressed) / len(households) if households else 0.0,
        "by_group": [
            sum(1 for h in stressed if h.stratum == g) for g in range(n_strata)
        ],
        "group_sizes": [
            sum(1 for h in households if h.stratum == g)
            for g in range(n_strata)
        ],
    }


def distinct_records(records: list[HouseholdRecord], households: int) -> int:
    """How many records got at least one copy. A coverage report, not a guard."""
    return sum(1 for c in allocate(records, households) if c > 0)


def record_of_each(records: list[HouseholdRecord],
                   households: int) -> list[int]:
    """The index of the record behind each built household, in build order.

    ``docs/a1d_prereg.md`` §10, 2026-08-16: a criterion counting **model**
    households is counting copies. A survey with five implicates and a
    weight-proportional allocation multiplies one respondent into many, and a
    floor meant to keep a thin cell from being scored on noise does not do that
    if it counts the copies.

    This mirrors :func:`build_from_records`'s own loop exactly, which is what
    makes it a mapping rather than an estimate: that function skips a record
    with no copies and otherwise appends ``copies`` households in record order,
    so the k-th household here is the k-th household there.
    ``test_the_record_map_lines_up_with_the_population`` asserts the alignment
    on attributes only the record can supply, so the two cannot drift apart
    silently.

    A **reporting** helper. Nothing in the mechanism reads it and no criterion
    is gated on it.
    """
    out: list[int] = []
    for index, copies in enumerate(allocate(records, households)):
        out.extend([index] * copies)
    return out


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CascadeSpec:
    """Timing and accounting. Registered values, none of them tuned."""

    #: A model period is one month and 90+ delinquent is three consecutive
    #: missed due dates. Both follow from the target's own definition; see
    #: ``docs/a1_prereg.md`` section 2.5.
    persistence: int = 3
    #: Sixty days on the same convention, which is two consecutive missed due
    #: dates. ``docs/a1d_prereg.md`` §4. Registered rather than tuned: it is
    #: the SCF's ``LATE60`` threshold read through ``persistence``'s own
    #: one-month-per-period rule, and it is a separate field so that the two
    #: thresholds cannot drift into agreeing by arithmetic accident.
    sixty_day_misses: int = 2
    #: Volume One section 4. False nets income against obligations inside the period, which
    #: is the control arm that removes the mechanism.
    income_arrives_after_due: bool = True


@dataclass
class CascadeResult:
    """Every per-group figure is keyed by the model's **reporting group**.

    Ordinarily a group is a stratum and the two words mean the same thing. They
    come apart in the arm that assigns income-ranked inputs to wealth-ranked
    strata under an imperfect rank correlation: there the population is built as
    one stratum per (wealth group, income group) cell, and the criteria still
    have to be read by wealth group. The model carries the map and does the
    aggregation, because a share is a ratio and a caller summing the cells would
    get the wrong answer without noticing.
    """

    periods: int
    #: Share of each class's outstanding balance that is 90+ delinquent, per
    #: period. The stock measure of ``docs/a1_prereg.md`` section 3.1.
    delinquent_share: dict[str, list[float]]
    #: The same quantity computed within a reporting group, for the gradients.
    delinquent_share_by_group: dict[str, list[float]]
    first_default_counts: dict[str, int]
    #: The same counts within each starting tenure. The pooled counts above put
    #: every defaulting household in one denominator, and a household that holds
    #: its dwelling outright can never default on rent while a mortgaged one can
    #: never default on rent either. Comparing the rent rung against the auto
    #: rung out of the pooled counts therefore divides two rungs with different
    #: populations by the same number. The manuscript's cascade is stated about
    #: tenants, so the rent rung has to be read inside the tenancy.
    first_default_counts_by_tenure: dict[str, dict[str, int]]
    #: How many households of each starting tenure carry each obligation at all.
    #: The denominator the counts above need: a first-default share is decided
    #: both by how hard a rung is and by how many households are standing on it,
    #: and dividing every rung by the same head count folds the second into the
    #: first. A renter without a car loan cannot default on one.
    exposure_by_tenure: dict[str, dict[str, int]]
    defaulting_households: int
    displaced: int
    displaced_by_group: list[int]
    renters: int
    renters_ever_behind: int
    renters_ever_behind_by_group: list[int]
    renters_by_group: list[int]


class CascadeModel:
    """One population, stepped monthly under an injected income path."""

    def __init__(
        self,
        households: list[Household],
        cost: CostRule,
        spec: CascadeSpec | None = None,
        groups: tuple[int, ...] | None = None,
    ) -> None:
        """``groups[stratum]`` is the reporting group that stratum belongs to.

        Omitted, every stratum is its own group and nothing changes. Supplied,
        the result's per-group figures are aggregated over the strata that map
        into each group, which is the only correct way to do it for a share.
        """
        self.households = households
        self.cost = cost
        self.spec = spec or CascadeSpec()
        self.groups = groups
        #: The order at zero arrears, which is the cascade the manuscript
        #: names. It is a view rather than the mechanism: the live order is
        #: recomputed every period from each household's own arrears, because
        #: that is where the ramp lives.
        self.drop_order = sorted(
            Obligation,
            key=lambda k: (cost.cost_now(k), -cost.grace(k), k.value),
        )
        self.n_strata = (
            max((h.stratum for h in households), default=-1) + 1
        )
        if groups is not None:
            if len(groups) != self.n_strata:
                raise ValueError(
                    f"groups has {len(groups)} entries against "
                    f"{self.n_strata} strata"
                )
            self.n_groups = max(groups) + 1 if groups else 0
        else:
            self.n_groups = self.n_strata

    def group_of(self, stratum: int) -> int:
        return stratum if self.groups is None else self.groups[stratum]

    # -- one period ---------------------------------------------------------
    def step(self, period: int, income_multiplier: list[float] | tuple[float, ...]
             ) -> None:
        for house in self.households:
            arriving = house.income * income_multiplier[house.stratum]
            available = house.buffer
            if not self.spec.income_arrives_after_due:
                available += arriving

            held = [k for k in Obligation if k in house.due]
            owed_of = {k: house.due[k] + house.arrears[k] for k in held}

            # An obligation that could not be cleared even with everything in
            # hand is lost whatever the household does.
            savable = {
                k: owed_of[k] <= available + SHORTFALL_TOLERANCE for k in held
            }
            cost = {
                k: self.cost.cost_now(k, house.missed[k], savable[k])
                for k in held
            }
            # What cannot be saved goes first, ahead of everything savable and
            # not merely level with the zero-cost ones. Releasing the hopeless
            # obligation is what frees the cash that keeps the others, and it is
            # usually the largest of them, so its position in the order decides
            # whether anything else survives.
            #
            # Then cheapest first. Among equals the longer grace goes first,
            # because the shorter grace is the more urgent of the two.
            order = sorted(
                held,
                key=lambda k: (savable[k], cost[k], -self.cost.grace(k), k.value),
            )

            owed = sum(owed_of[k] for k in held)
            dropped = 0
            while (dropped < len(order)
                   and owed > available + SHORTFALL_TOLERANCE):
                owed -= owed_of[order[dropped]]
                dropped += 1
            paid = set(order[dropped:])
            available -= owed

            displaced: list[Obligation] = []
            for kind in house.due:
                if kind in paid:
                    house.missed[kind] = 0
                    house.arrears[kind] = 0.0
                    continue
                house.arrears[kind] = owed_of[kind]
                house.missed[kind] += 1
                if kind not in house.first_missed:
                    house.first_missed[kind] = period
                    house.savable_when_missed[kind] = frozenset(
                        k for k, ok in savable.items() if ok
                    )
                house.ever_missed[kind] = True
                if house.missed[kind] >= self.spec.sixty_day_misses:
                    house.first_sixty.setdefault(kind, period)
                    house.last_sixty[kind] = period
                if house.first_default is None:
                    house.first_default = kind
                if (
                    kind in SHELTER
                    and house.displaced_at is None
                    and house.missed[kind] >= self.cost.grace(kind)
                ):
                    house.displaced_at = period
                    displaced.append(kind)

            # The obligation ends with the tenancy or the title. What follows
            # is outside this model: whether the household rehouses, and into
            # what, is not something it knows.
            for kind in displaced:
                house.due.pop(kind, None)
                house.balances.pop(kind, None)

            if self.spec.income_arrives_after_due:
                available += arriving
            house.buffer = available

    # -- a run --------------------------------------------------------------
    def run(
        self, income_path: list[list[float]] | list[tuple[float, ...]]
    ) -> CascadeResult:
        """``income_path[t][stratum]`` multiplies that stratum's income."""
        shares: dict[str, list[float]] = {k.value: [] for k in Obligation}
        by_group: dict[str, list[float]] = {
            f"{k.value}:{g}": []
            for k in Obligation
            for g in range(self.n_groups)
        }

        for period, multipliers in enumerate(income_path):
            self.step(period, multipliers)
            for kind in Obligation:
                shares[kind.value].append(self._delinquent_share(kind))
                for group in range(self.n_groups):
                    by_group[f"{kind.value}:{group}"].append(
                        self._delinquent_share(kind, group)
                    )

        counts = {k.value: 0 for k in Obligation}
        for house in self.households:
            if house.first_default is not None:
                counts[house.first_default.value] += 1

        by_tenure: dict[str, dict[str, int]] = {
            tenure.value: {k.value: 0 for k in Obligation} for tenure in Tenure
        }
        for house in self.households:
            if house.first_default is not None:
                by_tenure[house.tenure.value][house.first_default.value] += 1

        exposure: dict[str, dict[str, int]] = {
            tenure.value: {k.value: 0 for k in Obligation} for tenure in Tenure
        }
        for house in self.households:
            for kind in house.balances:
                exposure[house.tenure.value][kind.value] += 1

        # A renter is a household carrying a rent obligation, rather than one
        # that merely lacks a mortgage: a household with no shelter obligation
        # at all is neither, and must not enter the rent rung's denominator.
        # By starting tenure rather than by current balance: displacement
        # removes the obligation, and a displaced renter is still one of the
        # renters this stage began with.
        renters = [h for h in self.households if h.started_renting]
        behind = [h for h in renters if h.ever_missed[Obligation.RENT]]
        return CascadeResult(
            periods=len(income_path),
            delinquent_share=shares,
            delinquent_share_by_group=by_group,
            first_default_counts=counts,
            first_default_counts_by_tenure=by_tenure,
            exposure_by_tenure=exposure,
            defaulting_households=sum(
                1 for h in self.households if h.first_default is not None
            ),
            displaced=sum(1 for h in self.households if h.displaced_at is not None),
            displaced_by_group=[
                sum(1 for h in self.households
                    if h.displaced_at is not None
                    and self.group_of(h.stratum) == g)
                for g in range(self.n_groups)
            ],
            renters=len(renters),
            renters_ever_behind=len(behind),
            renters_ever_behind_by_group=[
                sum(1 for h in behind if self.group_of(h.stratum) == g)
                for g in range(self.n_groups)
            ],
            renters_by_group=[
                sum(1 for h in renters if self.group_of(h.stratum) == g)
                for g in range(self.n_groups)
            ],
        )

    # -- the stock measure --------------------------------------------------
    def _delinquent_share(
        self, kind: Obligation, group: int | None = None
    ) -> float:
        """Share of this class's outstanding balance that is 90+ delinquent.

        The denominator is balance, not households, because the target is
        ``Percent of Balance 90+ Days Delinquent by Loan Type``. A share of
        households would be a different quantity carrying the same name.

        Restricted to a reporting group, the numerator and the denominator are
        both restricted, so the group figure is a share within the group and
        not that group's contribution to the whole.
        """
        total = 0.0
        late = 0.0
        for house in self.households:
            if group is not None and self.group_of(house.stratum) != group:
                continue
            balance = house.balances.get(kind)
            if balance is None:
                continue
            total += balance
            if house.missed[kind] >= self.spec.persistence:
                late += balance
        return 0.0 if total == 0.0 else late / total


# ---------------------------------------------------------------------------
# A1-11: the parameter budget, printed rather than asserted in prose
# ---------------------------------------------------------------------------
def free_parameters(
    pop: PopulationSpec, cost: CostRule, spec: CascadeSpec
) -> list[tuple[str, float]]:
    """Values this repository chose. ``docs/a1_prereg.md`` A1-11 bounds this at 12."""
    return [
        ("cost.commute_dependency", cost.commute_dependency),
        ("cost.access_penalty", cost.access_penalty),
        ("population.dispersion", pop.dispersion),
        ("population.buffer_months", pop.buffer_months),
        ("cost.grace_basket", float(cost.grace_basket)),
        ("cost.grace_rent", float(cost.grace_rent)),
    ]


def literature_parameters(cost: CostRule) -> list[tuple[str, float, str]]:
    """Grace periods taken from practice rather than chosen here."""
    return [
        (
            "cost.grace_card",
            float(cost.grace_card),
            "FFIEC uniform retail credit classification: an open-end account is "
            "charged off at 180 days, which is six monthly cycles",
        ),
        (
            "cost.grace_auto",
            float(cost.grace_auto),
            "repossession practice clusters near ninety days; unverified, and "
            "swept beside the basket",
        ),
        (
            "cost.grace_mortgage",
            float(cost.grace_mortgage),
            "federal servicing rules bar a first foreclosure filing until the "
            "borrower is more than 120 days delinquent, four monthly cycles, "
            "and the process runs beyond that; the value above the floor is "
            "unverified and swept",
        ),
    ]


def sourced_parameters(pop: PopulationSpec) -> list[tuple[str, object, str]]:
    """Values taken from a publication, listed separately so neither hides."""
    return [
        ("counts", pop.counts, "DFA percentile widths"),
        ("net_worth_shares", pop.net_worth_shares, "DFA Q1 2026"),
        (
            "consumer_credit_shares",
            pop.consumer_credit_shares,
            "DFA consumer credit by wealth group; the bottom-50% entry is "
            "WFRBSB50211 = 0.518, the other three identifiers are verified by "
            "the fetcher at retrieval",
        ),
        (
            "mortgage_shares",
            pop.mortgage_shares,
            "DFA home mortgages by wealth group; identifiers verified by the "
            "fetcher at retrieval",
        ),
        (
            "mortgage_to_consumer_credit",
            pop.mortgage_to_consumer_credit,
            "Z.1 2026Q1 NSA, FL153165105 / FL153166000 = 13,821.0 / 5,073.0; "
            "both named instruments, no residual; no default in this module",
        ),
        (
            "tenure_by_stratum",
            "supplied to build_population",
            "CEX Table 1110 housing tenure by income decile, the same table "
            "the shelter flows come from, because a flow ranked by income "
            "divided by a share ranked by wealth is a population error. The "
            "SCF's net-worth version is the registered second arm. No default "
            "in this module",
        ),
        (
            "mortgage_stock_per_mortgaged",
            "supplied to build_population",
            "DFA home mortgage shares at the Z.1 scale, over the mortgaged "
            "households of that stratum rather than over every owner. The "
            "balance HHDC Page 12's percent is taken of; no default here",
        ),
        (
            "income_by_stratum",
            "supplied to build_population",
            "supplied by the experiment; no default in this module",
        ),
        (
            "necessities_by_stratum",
            "supplied to build_population",
            "Consumer Expenditure Survey by income decile, the consuming-power "
            "basket already listed in data/SOURCES.md; no default here",
        ),
        ("persistence", 3, "the 90-day definition, at a monthly period"),
    ]
