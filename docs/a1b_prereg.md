# A1b: the default cascade on a measured population

Pre-registration for **stage A1b**. A separate document rather than an edit to
[`a1_prereg.md`](a1_prereg.md), for two reasons: that document's sections 1 to 10
are frozen, A1-1 having produced a result; and this stage changes the
**observable**, not an arm. Adding an arm rearranges margins. This replaces them.

The mechanism is unchanged. `monetary_topology.cascade` is not modified except to
gain a second constructor, the cost rule is the same rule with the same
attributes, and the criteria are A1's, inherited by reference. What changes is
where a household's balance sheet comes from.

---

## 1. Why this stage exists

A1 built its population by crossing two rankings. Income, the necessities
basket, rents and housing tenure came from the CEX by income decile; consumer
credit and mortgage debt came from the DFA by net-worth group; and every
household inside a wealth group carried that group's **average** debt, because
neither source says how debt and income covary inside a group.

`a1_prereg.md` §11 records the four findings that closed that route. Two are
load-bearing here:

**Every stratum in A1 is a crossed cell, so §2.6's rule had no scope.** That rule
says a group which cannot service its published debt out of its published
disposable raises rather than rescales, because that would be the data speaking.
It holds for a group a publisher reports. A cell made by crossing two rankings is
published for nobody, and its failure to service itself is a statement about the
crossing. A1 raised on three such cells and none of them was a finding.

**The uniform-within-group debt is wrong by a factor of two, and the level by
four.** [`a1a_joint_probe.py`](../experiments/a1a_joint_probe.py) measured both
against the joint the SCF already publishes. Consumer credit rises steeply with
income *inside* every wealth group: `5,506 / 17,804 / 22,138` across the income
groups of the bottom half by wealth. And A1 puts `38,674` on a bottom-half
household where the SCF measures `8,964`.

---

## 2. The population

**Every model household is a weighted SCF household.** Not a cell mean, not a
draw around a mean: a record. Income, net worth, tenure, whether a mortgage is
outstanding, the mortgage balance and payment, the rent, the credit card balance
and the vehicle instalment debt all come from the same respondent under one
weight, so their covariance is measured rather than assumed.

Source: Survey of Consumer Finances 2022 summary extract, the same archive
`data/fetch_scf.py` already retrieves, read by
`monetary_topology.scf_joint` under the selection pinned in
`data/scf_joint_variables.json`. Five implicates, `WGT` already split across
them, 22,975 records weighing 131,306,389 families.

### 2.1 What this deletes

**The service-share draw is gone, and with it a free parameter.** A1 drew each
household's debt service as a Beta share of its disposable, because it knew a
group mean and had to invent a spread. The spread is now measured, so
`population.dispersion` is not a parameter of this stage. The free-parameter
count falls from six to five and `DrawDegenerate` cannot arise: no draw, no
degeneracy.

**The copula is gone.** The coupling between the rankings is measured, not
modelled. `experiments/a1a_joint_probe.py` records what the Gaussian copula at
Kennickell's `0.76` got right, which was most of it, and it is not needed.

**The Z.1 scale and the DFA shares are gone from the population.** Both remain
in the record as the aggregates this stage does *not* reproduce; see §4.

### 2.2 What still crosses, and why it is weaker

**The necessities basket.** The SCF collects food at home and collects neither
utilities, healthcare nor commuting, so the basket is still the CEX's, assigned
to a household by its income group. That is a crossing, and it is a crossing on
**one variable that both sources measure**, matched by rank on that variable,
rather than a crossing of two different rankings. The registered assignment is by
**rank, not by level**, because the two sources' income levels differ by a third
(SCF mean family income `141,390` against the CEX's `104,207` before taxes) and
the SCF's better coverage of the top is the documented reason. A rank is
comparable across the two; a dollar figure is not.

**Registered consequence.** The basket is therefore constant within an income
group and carries no within-group variation at all. Where a criterion turns on
the basket, that flatness is a limit of this stage and is named in §6.

---

## 3. Baseline stress is a property of the data, not a construction error

Some real households in this extract owe more each month than they take in.
A1 could not have them: its Beta draw made every household feasible by
construction. Here they are kept, because they exist and because excluding them
would select on the outcome the stage is about.

**Registered before any run:**

- The count and the weight of households whose scheduled obligations exceed
  their income at baseline is **reported**, by reporting group. It is a fact
  about the population.
- No household is dropped, rescaled or repaired. §2.6's rule now has its scope:
  these are published households, so their infeasibility is the data speaking.
- **A1b-0 replaces A1-1's zero calibration.** With every income multiplier at
  one, the delinquency series must be **constant from the second period onward**,
  to floating point, on every rung and every reporting group. Exact zero is the
  wrong test on a population with genuine baseline stress; drift with no shock
  is the instrument, and that is what this detects. The constant it settles at is
  reported as the **baseline** and every shocked reading is reported against it.

---

## 4. Two measured discrepancies, and the choice on each

Both are recorded here rather than reconciled. Neither is rescaled.

### 4.1 Consumer credit: SCF `1.332` trillion against Z.1 `5.073` trillion

Ratio `0.263`; adding student debt, which has no rung in this cascade, reaches
`2.671` trillion.

**This stage uses the SCF measure, and the reason is not that a source had to be
picked.** The two measure different things. Z.1 consumer credit counts all
outstanding balances including the float of a household that pays its card in
full every month. `CCBAL` is the balance *after the last payment*, which is the
balance that revolves. The cascade charges a minimum payment on this stock, and a
minimum payment is owed on what revolves. Charging it on the float is charging a
household for money it does not owe, and `a1_prereg.md` §11 records that this is
most of where A1's 94% service share came from.

### 4.2 Income: SCF `141,390` against CEX `104,207`

The SCF oversamples the wealthy by design and captures top incomes that
household surveys miss. Income here is the SCF's, because it must be the same
respondent's as the balance sheet. The CEX enters only through the basket, by
rank (§2.2).

### 4.3 Mortgages, for contrast

SCF primary-residence mortgages `11.568` trillion against Z.1 home mortgages
`13.821`, ratio `0.837`, the gap being second homes and vintage. The leg that
disagreed was the one the cascade's first two rungs are made of.

---

## 5. Criteria

### 5.1 Inherited from `a1_prereg.md`, unchanged in statement

**A1-2** the order is an output. **A1-3** the K shape, ordinally, with its
attached parameter gate. **A1-6** the subprime gradient, on sign. **A1-7** the
rent gradient, monotone across the groups containing renters. **A1-9** the
representative arm as a localizer. **A1-10** one behavioural parameter vector
across every rung. **A1-11** the free-parameter bound, now at five rather than
six.

**A1-4 and A1-5 remain reported and not gated**, and this stage adds a reason to
the two already registered: the population is 2022 and the targets are 2026Q1.

### 5.2 A1b-0. The zero calibration, restated

§3. Constant from the second period, not zero.

### 5.3 A1b-1. The delinquency gradient, against a target on the model's own cut

The extract carries `LATE60`: whether the household was sixty days or more late
on any payment in the last year. Nationally `4.91%` of households, weighted.

**This is the stratified delinquency reading `a1_availability.md` §4 recorded as
not existing in public form.** It exists, on the same households the population
is built from, cut the same way.

**It is not circular.** `LATE60` enters no part of the construction: the
population is built from income, net worth, tenure and balances, and `LATE60` is
a separate response. The model predicts who falls behind from a balance sheet;
this says who reported falling behind.

**Registered as ordinal only, and the direction comes from the manuscript rather
than from the data.** Volume One section 18 says the failure concentrates in the strata
holding consumer credit against little net worth. So:

> the model's share of households ever behind is **decreasing in net-worth
> group**, and the ordering of the four groups matches `LATE60`'s ordering of the
> same four groups, **in every cell of the shock sweep**.

**Written before the gradient was measured.** The national rate above is an
availability fact and was read before this criterion was written; the gradient
across groups was not, and this sentence is here so that the order of the two is
on the record.

**Four denominator facts, each of which forbids a level comparison**, and they
are why this criterion is a gradient and never a level:

| `LATE60` | the model |
|---|---|
| sixty days | ninety days |
| a household count | A1-3's rungs are a balance share |
| any payment, not by loan type | four rungs, separately |
| ever in twelve months | a point-in-time stock |

Self-reported delinquency also runs below credit-file measures, and the
direction of that bias is known and is not corrected here.

### 5.4 Reported and never scored

`FORECLLAST5`, a foreclosure in the last five years, weighted `0.47%`, beside the
model's displacement of mortgaged households. `BNKRUPLAST5`, weighted `1.27%`.
Both are counts over a five-year window against a monthly model, which is
`MEASUREMENT.md` checklist item 1, and both are on the resource side of the line
`a1_prereg.md` A1-8 draws.

`TURNDOWN`, `FEARDENIAL` and `TURNFEAR`, weighted `10.1%`, `12.9%` and `18.4%`,
are the observable counterpart of the cost rule's `cost_later`, the degraded
future claim price. They are **diagnostic**: a share of households is not a price
and cannot calibrate `access_penalty`. Whether credit denial follows delinquency
in this file is worth looking at and is not a criterion.

---

## 6. Scope: what A1b is not evidence for

**Not a level.** The population is 2022 and the delinquency targets are 2026Q1.
Nothing here licenses a level comparison, and A1-4 and A1-5 stay reported.

**Not a top-end contrast in the basket.** The CEX publishes to the top decile, so
`next9` and `top1` receive the same basket. Within an income group the basket is
constant, so no criterion may rest on basket variation inside a group.

**Not a claim about imputation.** The five implicates carry the SCF's imputation
of missing values. This stage pools them and reports the spread across implicates
where a figure is close to a threshold; it does not model imputation variance.

**Not a replacement for A1.** A1 stands as written, with its levels unreadable
and its ordinal criteria readable. Where the two stages disagree on an ordinal
verdict, both are reported and the disagreement is the finding.

---

## 7. Outputs

`results/a1b_default_cascade.json`, `data/processed/a1b_model_v1.csv` in the
shape the measurement side requires, and rows in `RESULTS.md` written by
the renderer.

---

## 8. Changelog

### 2026-08-15, written

Sections 1 to 7 are fixed at this date. **No result exists for this stage**, and
the `LATE60` gradient of §5.3 has not been computed.

Two things were seen before this document was written and both are recorded so
that the order is not in doubt: the joint's coupling and conditional debt, in
`results/a1a_joint_probe.json`, which is what closed A1's route and is the reason
this stage exists; and the *national* rates of `LATE60`, `FORECLLAST5`,
`BNKRUPLAST5` and the three credit-access variables, which are availability facts
about whether a column is usable. **No gradient, no cross-tabulation and no
model output was seen.**

### 2026-08-16, the skeleton ran. Three changes, no criterion of §5.1 scored

**The basket is assigned by income decile, not by the four groups.** The first
run reported `24.7%` of households owing more each month than they take in, and
`89%` of those were short on **basket plus shelter alone**, before any debt. The
four-group mean handed the bottom half's `15,025` a year to households far below
their group. The CEX publishes ten deciles, `10,593` at the lowest against
`35,286` at the highest, and assigning by the household's own income decile
takes the stress to `11.1%`: bottom half `19.0%`, next 40% `3.7%`, next 9%
`1.4%`, top 1% none. What remains is within-decile variation, which the table
does not publish and which this stage reports rather than invents.

**A1b-0 was restated, and §3's version was wrong too.** §3 asked for a
constancy. The run showed the no-shock population does not settle: renters fall
behind, are displaced at the rent grace, the obligation is removed, the freed
cash clears other arrears, and the series is still moving at sixty periods.
Neither zero nor constant is the right demand on a population with real baseline
stress. What a zero calibration is *for* is detecting an instrument that
produces readings from nothing, so the **cause** is removed rather than the
shock: every household's income is raised to cover its own scheduled
obligations, nothing else is touched, the same code path runs, and every rung
must report exactly `0.000000`. It now does.

**Its first failure was a defect in the shared mechanism**, recorded in
[`a1_prereg.md`](a1_prereg.md) §11 as well because `step` belongs to both
stages: 589 of 20,000 relieved households were judged short by `2e-13` dollars,
because the constructor totals a household's dues in the order it built them and
`step` totals them in the order of `Obligation`. A half-cent tolerance now
stands in both comparisons.

**The baseline, as measured**, at 20,000 households over 60 periods with no
shock: card `0.0589`, auto `0.0191`, mortgage `0.0001`, basket `0.0135`, and
`1,744` of `6,292` renters displaced. Every shocked reading in this stage is
reported against these and never against zero.

**A scope item that belongs in §6 and cannot go there**, sections 1 to 7 being
fixed now that A1b-0 has a result: **this model has no transfers in kind.** The
SCF's `INCOME` includes cash transfers and does not include SNAP, Medicaid or
housing vouchers, and the model has no family support, no food bank and no
arrears forgiveness. A household below its own necessities in this population is
not thereby a household that goes without in the world. The baseline displacement
figure above is an upper bound for that reason, and no reading of it as a
prediction is licensed.

### 2026-08-16, the income path, registered before it is run on

`monetary_topology.income_path` takes the shock from A0 rather than inventing
one, which `cascade.py` has listed among the things it refuses to invent since
it was written. What was never written down is the **identification**, and it is
written here before any criterion runs on it.

**The quantity is `History.terminating[t, s]`**, the claims landing on stratum
`s` in round `t`, normalised by the same stratum's opening round. That is the
quantity Volume One section 18 is about, what reaches a household against what it owes, and
the normalisation makes period zero exactly one by construction rather than by a
level this project chose.

**The population is the same population.** A0's DFA-calibrated preset carries
counts `(50, 40, 9, 1)` and net worth shares `(0.025, 0.296, 0.363, 0.316)`,
which are the cascade's. The mapping is therefore by construction. The
source-faithful preset carries `(49, 40, 10, 1)` and would need an
approximation, so the module refuses it rather than rescaling quietly.

**One A0 round is one model month, and that is a declaration.** Nothing
publishes A0's round length. What the identification sets is how fast the
path's transition plays out against the cost rule's grace periods, and
`months_per_round` is the registered robustness arm: **a verdict that moves when
the same path is stretched is a verdict about this identification and is
reported as one.**

**The seed is A0's.** A1b draws nothing, so A0's propensity draw is the only
randomness reaching it.

**The control is built as an explicit vector of ones and is never asked of the
mechanism.** A retention mechanism that turned out to move nothing would
otherwise be indistinguishable from the zero-shock arm, and the module refuses a
path in which no stratum moves.

The path at seed 7, as multipliers on each stratum's income:

| month | bottom 50% | next 40% | next 9% | top 1% |
|---|---|---|---|---|
| 0 | `1.000` | `1.000` | `1.000` | `1.000` |
| 1 | `0.891` | `0.743` | `0.841` | `1.070` |
| 11 | `0.594` | `0.476` | `1.019` | `2.549` |
| 59 | `0.577` | `0.461` | `4.021` | `10.020` |

This is A0's K shape at the source, and it is an **input** to these stages. No
criterion may be read as having produced it.

### 2026-08-16, the first scored run. A1-3 holds, A1-2 fails, and the failure is located

At 20,000 households over 60 months on A0's path at seed 7.

**A1-3 holds, raw and over baseline.** Mortgage `0.0024` < auto `0.0995` < card
`0.1867`; as an increase over the no-shock baseline, `+0.0022` < `+0.0805` <
`+0.1279`. The attached gate passes on its own terms: `cost_now` names no
obligation class, so every pair is one rule applied to per-class attributes and
the mortgage leg carries no multiplier the others do not. **The K shape is
ordinally reproduced on a population every figure of which was measured on the
same respondent.** No level is claimed and none can be: the population is 2022
and the target is 2026Q1.

**A1-2 fails, and not on the card.** Among 7,277 defaulting households the first
default is card `0.4278`, auto `0.0627`, shelter `0.3500` (rent `0.2379`,
mortgage `0.1121`), basket `0.1595`. The registered inequality is
`card > auto > shelter` and what breaks it is **auto being the smallest of the
three**. Among the 5,054 households not already short at baseline the shares are
card `0.4865`, auto `0.0602`, shelter `0.3192`: the same failure, so it is not
an artefact of baseline stress.

**Where it comes from, measured.** The share of households holding each rung at
all: card `0.456`, mortgage `0.413`, auto `0.349`, rent `0.315`. Card and car
together, `0.212`; neither, `0.406`. And the distribution of *the cheapest rung
a household holds* at zero arrears is card `0.456`, mortgage `0.189`, basket
`0.159`, rent `0.131`, auto `0.065`, which reproduces the observed first-default
shares almost exactly.

So the measured quantity is, to a very good approximation, **the cost rule
composed with the holdings and nothing else**. A car loan is a household's
cheapest rung only when it holds no card, the card costing nothing to skip, and
no mortgage, one missed payment there consuming a twelfth of the foreclosure
clock against a third of the repossession clock. Only `6.5%` of households are
in that position.

**What this refutes, stated precisely.** Volume One section 18's sequence describes *one*
squeezed household walking down its own rungs. A1-2 turned that into a
cross-section of first defaults, and a cross-section is dominated by which rungs
a household holds at all. In a population where 40.6% hold neither a revolving
balance nor a car loan, the registered inequality cannot hold whatever the cost
ordering is. **A1-2 as registered is refuted, and the finding is about the
criterion's fit to the claim as much as about the claim.** This entry records
that before anything is decided about it, because the alternative readings all
arrive after the result and must be dated accordingly.

`monetary_topology.cascade`'s own note anticipated the shape of this: it says
A1-2 is a joint test of the cost ordering and the holdings structure and can
come out in any order. What it did not anticipate is that the holdings would
dominate it.

### 2026-08-16, the rest of §5.1, and two definitions A1b-1 needed

**Seven of eight criteria pass**, A1-2 being the recorded failure above.

| criterion | verdict | figure |
|---|---|---|
| A1b-0 zero calibration | pass | every rung exactly `0.000000` once the cause is removed |
| A1-3 K shape | pass | `0.0024 < 0.0995 < 0.1867`, and `+0.0022 < +0.0805 < +0.1279` over baseline |
| A1-6 subprime gradient | pass | bottom `0.1490` against middle `0.0754`, ratio `x1.98` |
| A1-7 rent gradient | pass | `0.6589 / 0.3606 / 0.0000`, top 1% excluded at 6 renters |
| A1-9 representative arm | pass | every rung in `{0, 1}` at all three tenures |
| A1-10 one parameter set | pass | one rule, one attribute table, one grace table |
| A1-11 free parameters | pass | five against twelve |

**A1-7's level is far from SHED's and that is registered, not a surprise.** The
model puts `0.6241` of renters behind at some point against the survey's `0.23`.
The window is sixty months against twelve, and this model has no transfers in
kind. A1-7 gates on the gradient and reports the level, and the gap is what the
registration said it would be.

**A1-6's ratio is `x1.98` against published readings of `5.33` to `5.85`.** The
sign is what is gated. The source is at thirty days on balances and the model at
ninety, and the two are printed side by side rather than against each other.

**Two definitions A1b-1 needs and §5.3 did not fix.** Both are written here
**before the gradient is computed**, and nothing about it has been.

*The shock sweep.* §5.3 requires the ordering to match "in every cell of the
shock sweep" and no sweep was defined. It is **A0 seeds 7, 8 and 9 crossed with
`months_per_round` 1 and 3**: six cells. The seeds are A0's only randomness and
the second factor is the identification registered on this date as the one arm
on "a round is a month".

*The model's counterpart to `LATE60`.* The survey asks about being sixty days or
more late on **loan payments**. The model's counterpart is therefore a household
that ever missed the card, the car or the mortgage. **Rent is excluded**: an
ordinary tenancy is not a loan and is not furnished to the bureaus, which is
already why `REPORTS_TO_CREDIT` marks it apart in `cascade.py`. The variant that
includes rent is **reported beside it and never gated**, because the survey
question's exact scope is a codebook fact this stage has not read and reporting
both is cheaper than guessing which one it is.

### 2026-08-16, A1b complete at 100,000 households. 6 of 8 live, 1 void

Sweep at 20,000 under A1-10's licence, everything else at 100,000.

| criterion | verdict |
|---|---|
| A1b-0 zero calibration | pass |
| A1-2 the order is an output | **fail**, recorded above |
| A1-3 K shape | pass, `0.0027 < 0.0924 < 0.1879` |
| A1-6 subprime gradient | pass, `0.1438` against `0.0680`, `x2.12` |
| A1-7 rent gradient | **void**, the two readings disagree |
| A1-9 representative arm | pass |
| A1-10 one parameter set | pass |
| A1b-1 delinquency gradient | **fail** |
| A1-11 free parameters | pass, five of twelve |

**A1-7 is void because the registration names two rankings and they disagree.**
Its title is "the rent gradient is monotone in **income**" and its source is
SHED's `33 / 31 / 17 / 5` by income band; its body says "across the **strata**",
and the strata are net worth. A1 had one ranking and could not see the
difference. Here both are measured:

| ranking | bottom 50% | next 40% | next 9% | top 1% | |
|---|---|---|---|---|---|
| net worth | `0.6577` (28,776) | `0.3584` (2,888) | `0.0000` (397) | `0.1351` (37) | not monotone |
| income | `0.8129` (23,585) | `0.1046` (7,581) | `0.0000` (897) | `0.0000` (35) | monotone |

The break on the wealth ranking is `37` renters in the top 1% by net worth, five
of whom fall behind. They are the asset-rich and low-income, the same households
the joint measured at 2.2% of the top wealth group sitting in the bottom half by
income. On the income ranking they sit where their income puts them and the
gradient is monotone.

**Reported on both and gated on neither**, which is this project's registered
treatment for a verdict that flips between two readings. **The implementation
originally computed only the wealth ranking**, which was a choice this session
made and not one the registration made; reading both is bringing the
implementation into line with a registration that named both, and it is recorded
here because the ambiguity was found by the two disagreeing.

**A1b-1 fails, on the top pair and by four basis points.** `LATE60` by net
worth is `0.0847 / 0.0163 / 0.0022 / 0.0026`: the survey puts the top 1%
`0.0004` above the next 9%. The model is `0.301 / 0.174 / 0.017 / 0.000` at
seed 7, and **strictly decreasing in every one of the six sweep cells**. So the
gradient's direction, which is what Volume One section 18 says, holds everywhere; the
ordering does not match, and the whole of the mismatch is that the survey's two
smallest cells are the wrong way round by four basis points while the model's
are the right way round.

The criterion as registered asks for both, and it fails. **That stands.** The
smallest adjacent gap is now printed at every run so no reading of this verdict
arrives without it.

**Two defects fixed during this run**, both found by the criteria rather than by
inspection:

*A population too small emptied a group and the comparison failed on its own
shape.* At 6,000 households the top 1% received no member, because each of its
records weighs about 570 against the 21,883 a copy costs at that size, so the
model returned three numbers where the target had four and the two could never
match. `ever_behind_by_group` now takes the group count rather than inferring
it, and A1b-1 refuses a size that empties a group instead of scoring it.

*The sweep needed its own size.* Six full runs at 100,000 households did not
finish in ten minutes. The size is an estimation setting chosen per criterion
under A1-10's licence, which is the licence's purpose, and the sweep runs at
20,000 with its group sizes printed: `[9993, 7998, 1895, 114]`.

### 2026-08-16, the diagnosis of A1-7 and A1b-1

**Nothing in §1 to §7 changes and no verdict is revised.** A1-7 stays void and
A1b-1 stays failed, both on the readings in `results/a1b_default_cascade.json`.
What is added is why each came out as it did, because both were carried forward
into `docs/a1d_prereg.md` and a successor built on an unexplained failure is
building on a guess.

**A1-7. Why the two rankings disagree, and where.** The break is the `top1`
cell and only that cell: `0.6577 / 0.3584 / 0.0000 / 0.1351` at 100,000
households, on renter counts `28,776 / 2,888 / 397 / 37`.

| net-worth group | renters | income/mo | rent/mo | rent/income |
|---|---|---|---|---|
| bottom50 | 28,776 | 4,319 | 1,145 | 0.265 |
| next40 | 2,888 | 11,364 | 1,940 | 0.171 |
| next9 | 397 | 98,553 | 3,316 | 0.034 |
| top1 | 37 | 53,970 | 4,032 | 0.075 |

The top group's renters have **half the income of the group below them and a
higher rent**. Behind those 37 model households are 90 SCF respondents with a
median net worth of `38,901,000` whose income-group membership is
`{bottom50: 20, next40: 5, next9: 26, top1: 39}`. Renting at the top of the
wealth distribution selects for the asset-rich and flow-poor.

The mechanism then treats them as poor, because **net worth has no channel into
it**. `NETWORTH` appears in this stage exactly once, in
`rank_groups(households, "networth")`, which assigns a label; the cushion is
`scheduled × buffer_months` and is the same shape for every household. A
gradient across an inert stratifier is a gradient in whatever that stratifier
correlates with, and the two rankings agree where income bounds net worth and
come apart where it does not: `66.0%` of respondents fall in the same group on
both, by group `74.4% / 57.5% / 55.4% / 73.8%`, and the bottom half's renters
sit in income groups `{0: 5039, 1: 1305, 2: 49}`.

`docs/a1d_prereg.md` §3 is the repair and §6.4 is the criterion that tests it.

**A1b-1. Two reasons, and neither is a level.** First, **the failing pair is
below the source's own resolution.** `LATE60` by group, with the sample behind
each figure:

| group | families | reporting | rate | naive s.e. |
|---|---|---|---|---|
| bottom50 | 1,857 | 886 | 0.0847 | 0.0065 |
| next40 | 1,475 | 155 | 0.0163 | 0.0033 |
| next9 | 694 | **11** | 0.0022 | 0.0018 |
| top1 | 569 | **5** | 0.0026 | 0.0021 |

The criterion turns on `next9` against `top1`: a gap of `0.0004` against a
standard error of the difference of `0.0028`, which is `0.14` standard errors,
computed on family counts (rows over five implicates) and before any design
effect. Eleven households against five. The model's side is no better: `114`
households in `top1` at 20,000, expecting `0.3` events at the target's rate, so
a zero there is entirely consistent. **Both sides of that pair are under their
own resolution**, and requiring the model to reproduce the ordering was
requiring it to reproduce noise. On the pairs both sides resolve the model
matched: `0.301 > 0.174 > 0.017` against `0.0847 > 0.0163 > 0.0022`.

Second, **the quantities are not the same event.** The model reads
`ever_missed` over sixty periods; `LATE60` is sixty or more days late in twelve
months. Five times the exposure and a different threshold, which is
`MEASUREMENT.md` failure mode 1 twice. §5.3 listed four denominator facts and
this is a fifth, and unlike the others it is not confined to levels: a long
window inflates low-rate groups more than high-rate ones in ratio terms, because
the high-rate group saturates, so it manufactures shape as well. Converting the
model's sixty-month rates to twelve-month rates under independent months gives
`0.0691 / 0.0375 / 0.0034 / 0` against the target's
`0.0847 / 0.0163 / 0.0022 / 0.0026`, collapsing the ratios from
`3.56 / 10.70 / 7.65` to `0.82 / 2.30 / 1.56`. Independence is the wrong
assumption and that arithmetic is not a result; it is the size of the thing the
window was hiding.

`docs/a1d_prereg.md` §4 and §5 are the repairs.

**The disposition.** A1b-1's failure is neither a calibration debt nor a
refutation. It is a criterion that required matching a difference its source
cannot resolve, which is `MEASUREMENT.md` checklist item 8. That is recorded
here rather than corrected, because this stage has a result.

### 2026-08-16, three code changes that move no figure in this stage

Made while building A1d, listed because `experiments/a1b_default_cascade.py` is
this stage's record and a silent edit to it would be failure mode 9.

1. `to_records` carries `liquid` onto each `HouseholdRecord`, and
   `representative` carries its mean. A1b builds with `Cushion.SCHEDULED`,
   which never reads the field.
2. `a1_9` takes a `cushion` argument defaulting to `Cushion.SCHEDULED`, so A1d
   can run the collapsed arm on its own mechanism.
3. `relieved` now raises a household's **cash** to its scheduled obligations as
   well as its income. Under `Cushion.SCHEDULED` the buffer already equals that
   sum, summed in the same dict order, so the new line is `max(x, x)` and this
   stage's arithmetic is unmoved;
   `test_the_relief_arm_does_not_move_a_scheduled_cushion` asserts it bit for
   bit. The reason for the change is in `docs/a1d_prereg.md` §10.

`data/scf_joint_variables.json` also gained `liquid_column` and two anchor
columns, and `scf_joint.extract` gained the nesting anchor that guards them.
None of the three is read by any quantity this stage computes.

### Anything altered after this date

Goes here with the date, the reason, and what had been seen at the time.
