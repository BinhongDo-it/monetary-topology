# A1d: the cascade on a measured cushion

Pre-registration for **stage A1d**. A new station rather than a revision of
[`a1b_prereg.md`](a1b_prereg.md), because A1b has results and two of its
readings turned out to rest on things this project can now name.

Population, records, income path and cost rule are A1b's, inherited by
reference. **Two things change**, one in the mechanism and one in the
measurement, and the criteria below are written so that the two can be told
apart afterwards.

---

## 1. What is being repaired, and why each repair is forced

### 1.1 The cushion, a mechanism change

A1b gives every household `buffer = scheduled × buffer_months` with
`buffer_months = 1.0`. That is one month of its own bills, and it has no source.
It is the last constructed quantity in a stage whose whole claim is that the
population is measured rather than drawn.

It also means **net worth has no causal channel**. `NETWORTH` appears in A1b
exactly once, in `rank_groups(households, "networth")`, which assigns a label.
Nothing in the mechanism reads it. A stage that stratifies by an inert variable
and then reports a gradient across those strata is reporting a gradient in
whatever the stratifier happens to correlate with, and A1-7 is the symptom:

| net-worth group | renters | income/mo | rent/mo | rent/income |
|---|---|---|---|---|
| bottom50 | 28,776 | 4,319 | 1,145 | 0.265 |
| next40 | 2,888 | 11,364 | 1,940 | 0.171 |
| next9 | 397 | 98,553 | 3,316 | 0.034 |
| top1 | 37 | 53,970 | 4,032 | 0.075 |

The top group's renters have half the income and a higher rent than the group
below them. Behind those 37 model households are 90 SCF respondents whose
income-group membership is `{bottom50: 20, next40: 5, next9: 26, top1: 39}`,
against a median net worth of `38,901,000`. Renting at the top of the wealth
distribution selects for the asset-rich and flow-poor, and a model in which
`38,901,000` buys nothing treats them as poor households. A1-7's
non-monotonicity is that fact, correctly computed.

**The repair is to give net worth a channel**, and the SCF publishes the
variable that carries one.

### 1.2 The window, a measurement change

A1b-1 compares the model's `ever_missed` over sixty periods against the SCF's
`LATE60`, which is sixty or more days late **in the last twelve months**. Two
mismatches at once, `MEASUREMENT.md` failure mode 1 twice over: five times the
exposure, and any missed payment against a sixty-day threshold.

`a1b_prereg.md` §5.3 registered four denominator facts that forbid a level
comparison and made A1b-1 ordinal for that reason. The window is a fifth, and it
does not stop at levels: a long window inflates low-rate groups more than
high-rate groups in ratio terms, because the high-rate group saturates. So the
window can manufacture a shape as well as a level, and an ordinal criterion is
not protected from it.

---

## 2. What had been seen when this document was written

This section is the registration. Everything below it is designed against what
is listed here and against nothing else.

**Seen, in full:**

- Every number in `results/a1b_default_cascade.json` and
  `results/a1c_household_order.json`, all nine and all two criteria.
- The renter table in §1.1, and the respondent composition behind each of its
  four cells: counts, weights, median net worth, median income, income-group
  mix.
- The rank agreement between the two rankings: `66.0%` of respondents fall in
  the same group on both, by group `74.4% / 57.5% / 55.4% / 73.8%`.
- `LATE60` by net-worth group with its **sample counts**: families
  `1,857 / 1,475 / 694 / 569`, households reporting `886 / 155 / 11 / 5`, rates
  `0.0847 / 0.0163 / 0.0022 / 0.0026`, naive binomial standard errors
  `0.0065 / 0.0033 / 0.0018 / 0.0021`.
- The model-to-target ratios `3.56 / 10.70 / 7.65 / 0` and an analytic
  conversion of the model's sixty-month rates to twelve-month rates under
  independent months, giving `0.0691 / 0.0375 / 0.0034 / 0`.
- That the columns `LIQ`, `FIN`, `NFIN`, `RETQLIQ`, `CHECKING`, `SAVING`,
  `MMA`, `CALL`, `CDS`, `NMMF`, `STOCKS`, `BOND`, `KGTOTAL`, `ASSET`, `HOUSES`
  and `BUS` exist in the extract.

**Not seen, and this is what makes the design below a design rather than a fit:**

- **No value of `LIQ` or of any other asset column.** Not a mean, not a median,
  not a distribution, not a group summary, not a correlation with anything, not
  the share of households reporting zero. The existence check in §1 read the
  header row and stopped.
- **No model output on a measured cushion.** Nothing has been built, run or
  scored with `buffer` set from the file.
- **No twelve-month model rate.** The analytic conversion above is arithmetic on
  a number A1b already published; the model has never been asked for a rolling
  window and does not currently record what one would need.

**One contamination, declared.** The pair-resolution rule in §5 was written
after the standard errors above were seen, and it is therefore known in advance
that the rule excludes the `next9 / top1` pair and admits the other two. The
defence is that the rule's verdict is insensitive to its threshold: the admitted
pairs stand at `9.4` and `3.7` standard errors and the excluded pair at `0.14`,
so any threshold anywhere in `[1, 3.7)` selects the same set. That the rule was
chosen with the answer visible is recorded here rather than argued away.

---

## 3. The cushion, registered

> **`buffer = LIQ`**, the SCF's liquid assets, per respondent, in the file's own
> dollars. **No floor and no addition.** A household reporting zero liquid
> assets starts with a cushion of zero.

`LIQ` is checking, savings, money market and call accounts. It excludes
retirement balances, which the extract carries separately as `RETQLIQ`, and it
excludes every non-financial asset.

**Three consequences, registered before the run rather than explained after it:**

**The bottom gets more fragile, and the direction is against the model.** A1b's
one-month cushion was almost certainly larger than many bottom-half households'
liquid assets. Removing it raises their arrears, and their arrears are already
`3.56` times the target before any window correction. **A1d-1 is therefore
being made harder to pass, deliberately.** If the level still collapses onto
the target after §4's window correction, it collapses from further away.

**A free parameter is removed rather than retuned.** `population.buffer_months`
leaves the free list. A1-11's count goes from five to four against the bound of
twelve. This is the reason to prefer this rule over `max(LIQ, scheduled × 1.0)`
or `LIQ + scheduled × 1.0`: both of those keep a number that has no source and
that would then be doing work at exactly the point the stage is about.

**Three real sources of cushion are registered as unreachable.** Retirement
balances carry a penalty and are excluded. Home equity lines are not in the
extract. Family transfers are not measurable here. A household that would in
fact reach one of these is modelled as more fragile than it is, and this stage
does not correct for that in either direction.

**Units.** `LIQ` is a stock in dollars and `scheduled × buffer_months` was a
monthly flow times months, so the replacement is unit-for-unit. Every figure in
this population is in the wave's own dollars and none is deflated.

**Depletion is unchanged.** Whatever `CascadeModel.step` currently does with
`buffer` it continues to do. This stage changes where the number comes from and
nothing about how it is spent.

---

## 4. The window, registered

> A household counts as **behind** in a window when, in some period inside that
> window, its arrears on any loan class reached **two scheduled payments or
> more**.

Two missed payments in a monthly model is the sixty-day threshold the survey
asks about. Loan classes are A1b's `LOAN_CLASSES`, which is card, auto and
mortgage; **rent stays out of the scored quantity** and is reported beside it,
exactly as in A1b-1, because `LATE60` is asked about loan payments.

**The scored window is the run's last twelve periods**, `t = 48 … 59`. The
survey asks a household at interview about the year behind it, so the model's
counterpart is one fixed twelve-month window and not a maximum over windows. The
last is chosen over the first because the shock path has run by then, and the
first twelve periods are a transient of a population that has just been handed
its shock.

**Reported beside it and not scored**, so that the window's contribution is
legible rather than assumed:

- the first twelve periods, `t = 0 … 11`, on the same rule;
- the whole sixty periods on the same rule;
- the whole sixty periods on **A1b-1's exact quantity**, any missed payment
  rather than two, which is the number A1b published and is what makes the two
  stations comparable.

**What the model must record to support this.** Per household and per class, the
**first** and the **last** period at which arrears reached two payments. Two
integers per class, no trace, and the window test is a comparison on the last.
Nothing else in the mechanism changes to serve this.

---

## 5. The resolution rule, registered

An ordinal criterion across four groups is four ranks and three adjacent pairs.
**A pair is scored only when both sides can resolve it.**

**Target side.** The pair is admitted when the target's adjacent difference
exceeds **two standard errors of that difference**, the standard error taken as
naive binomial on the **family count**, which is rows divided by five because
the extract carries five implicates of each family. Naive is stated as the
conservative choice in the direction that matters: it ignores the SCF's design
effect, which on a list-sample-heavy top cell inflates the variance, so this
rule admits more pairs than a design-corrected one would and is therefore harder
on the model.

**Model side.** A group enters a scored pair only when its expected count under
the target's own rate, `n_group × target_rate`, is at least **five**. A group in
which the model would expect fewer than five events cannot be said to have
produced a rate rather than a rounding.

**A pair failing either test is reported with both sides' figures and scored on
neither.** The reason is on the record: an ordinal test between two cells that
neither the source nor the model can resolve is `MEASUREMENT.md` checklist item
8, a guard that would say the same thing if the thing it guards were broken.

**The population size this forces.** The model-side rule binds through the
sweep's population size, and A1-10's licence makes that size an estimation
setting. At `20,000` households the `next9` group holds about `1,895`, giving
`1,895 × 0.0022 ≈ 4.2` expected events, under the floor. **The sweep therefore
runs at `50,000`**, where the same group gives about `10.4`. The code refuses
any size at which a group admitted by the target-side test falls under the
model-side floor, rather than quietly scoring it.

---

## 6. Criteria

### 6.1 Inherited from `a1b_prereg.md`, unchanged in statement, re-scored

**A1-2** the order is an output. **A1-3** the K shape, ordinally, with its
attached parameter gate. **A1-6** the subprime gradient, on sign. **A1-9** the
representative arm as a localizer. **A1-10** one behavioural parameter vector
across every rung.

All five are computed on the measured cushion and scored. A1b's readings stand
as the readings on the constructed cushion, and neither record is superseded by
the other: they are two mechanisms and the difference between them is the
finding.

**A1-2 is expected to fail again**, and this sentence is here so that the
expectation is on the record and not produced afterwards. §1 of
`a1c_prereg.md` gives the reason and it is a property of the holdings rather
than of the cushion: two households in five hold neither of the first two rungs.
The cushion does not touch that.

### 6.2 A1d-0. The zero calibration, by removing the cause

A1b-0's form, unchanged: raise each household's income to cover its own
obligations and require every rung at exactly `0.000000` over twenty-four
periods. It must still hold, and with a cushion of zero for some households it
is a stronger statement than it was, because nothing is absorbing a shortfall.

### 6.3 A1d-1. The delinquency gradient, on a matched window

> Among the pairs §5 admits, the model's share of households behind is
> **decreasing in net-worth group**, and the model's ordering of those groups
> matches `LATE60`'s ordering of the same groups, **in every cell of the shock
> sweep**.

Ordinal only. The direction is Volume One section 18's and not the data's. The sweep is
A1b's registered one, three seeds by two round lengths.

**Still not a level, and the window correction does not make it one.** The model
runs a shock scenario from A0 over sixty months; the survey asks about the
twelve months before a 2022 interview. Matching the window makes the two the
same **kind** of quantity. It does not make them the same year or the same
world. Any reading of §7's arithmetic as a level validation is a misreading and
this sentence is where that is refused in advance.

### 6.4 A1d-2. The rent gradient, on net worth alone

A1-7 restated, and the restatement is the whole of the change:

> Renter arrears are **monotone decreasing in net-worth group**, across groups
> holding at least `RENTER_FLOOR` renters.

**One ranking, and it is net worth.** A1-7 named two rankings and they
disagreed, so it was void, and naming two was the defect. Net worth is the
ranking this thesis is about, and §3 is what gives it the channel that makes
stratifying by it mean something. **The income ranking is reported beside this
and scored on nothing.**

**This criterion is the test of §3.** A pass says that giving net worth a
measured channel produced the monotonicity a label could not. A failure says the
non-monotonicity survives the repair and belongs to the data rather than to the
missing channel. Both are readable and neither is a repair of the other.

### 6.5 A1d-3. The free-parameter bound

Four against twelve: `cost.commute_dependency`, `cost.access_penalty`,
`cost.grace_basket`, `cost.grace_rent`. `population.buffer_months` is gone.

### 6.6 Reported and never scored

Everything `a1b_prereg.md` §5.4 lists, unchanged. In addition: the share of
households whose measured cushion is zero, by group, which is the size of what
§3 removed; and the three alternative window readings of §4.

---

## 7. A prediction, registered so that it can be wrong

The analytic conversion in §2 says that if the model's misses were independent
across months, its twelve-month rates would be `0.0691 / 0.0375 / 0.0034 / 0`
against the target's `0.0847 / 0.0163 / 0.0022 / 0.0026`, collapsing the ratios
from `3.56 / 10.70 / 7.65` to `0.82 / 2.30 / 1.56`.

Arrears in this model are persistent by construction, so independence is the
wrong assumption and the true conversion will not be that one. Removing the
cushion pushes the other way. **The registered expectation is that the measured
rolling-window rates land between the two, with the bottom group inside a factor
of two of the target and the middle group above it.**

This is written down so that a result matching it is a prediction met and a
result missing it is on the record as missed. It gates nothing.

---

## 8. Scope: what A1d is not evidence for

**Not a level, and §6.3 says why at length.**

**Not a claim about what households actually reach for.** §3 registers
retirement balances, home equity and family transfers as unreachable inside a
month. All three exist and some households use them.

**Not independent of A1b or A1c.** Same records, same income path, same cost
rule, same holdings. If A1b's inputs move, this moves with them.

**Not a repair of A1-2.** §6.1.

**Not a claim about imputation.** The five implicates are pooled, as in A1b.

---

## 9. Outputs

`results/a1d_measured_cushion.json`, and rows in `RESULTS.md` written by the
renderer. The stage gets a job in `scripts/run_all.py` at the same time as its
first record, not afterwards.

---

## 10. Changelog

### 2026-08-16, written

Sections 1 to 9 are fixed at this date. **No result exists for this stage.** No
value of `LIQ` has been read, no population has been built on a measured
cushion, and no rolling-window rate has been computed. §2 is the full list of
what had been seen, including the one contamination this document declares
rather than argues away.

### 2026-08-16, §6.2's relief arm removed half of the cause

**What had been seen when this was written**: the first run of this stage, at
20,000 households, in which A1d-0 failed at `CARD 0.084180`, `AUTO 0.018265`,
`RENT 0.179602`, `MORTGAGE 0.023850`, `BASKET 0.022673`; and the §3 cushion
table below. No criterion of this stage had been scored except A1d-0, and the
sweep had not been run at the size §5 forces.

**What was found.** `relieved` raised each household's income to its scheduled
obligations and left its cash alone. `CascadeSpec.income_arrives_after_due` is
Volume One section 4's settlement asymmetry and it is `True`, so a household whose income
exactly covers its bills and whose cash is zero **still cannot pay in period 0**.
Raising the flow leaves the stock cause standing.

This is not the instrument inventing a default. Three checks, all on the 20,000
population:

- relieving the flow alone gives the rates above; relieving flow and stock
  together gives **exactly `0.000000` on every rung**;
- the set of households that missed anything is **identical**, element for
  element, to the set whose cash could not cover period 0: `6,440` of `20,000`;
- not every miss is dated at period 0, so the arrears that start there do
  propagate, which is the mechanism working rather than a period-0 artefact.

**The ruling, taken 2026-08-16.** This is a defect in the control arm rather
than a change to a criterion. §6.2 registers *remove the cause*; under a
measured cushion the cause has two components and the arm removed one, so the
arm did not implement the sentence that was registered. `relieved` now raises
both, A1d-0 is scored on the corrected arm, and the ruling is recorded here
rather than argued for in the code.

**The alternative reading is on the record too**, because the one above is the
one that lets the stage pass and that is exactly when a reading needs its
competitor written down: A1d-0 ran and failed, and the failure means that a
household with no cash defaults under settlement asymmetry whatever its income
is. That reading was put and was not taken.

**What the finding is worth regardless of the ruling.** `6,440` of `20,000`
households, `32%`, cannot meet period 0 out of cash even when their income
exactly covers their bills. That is Volume One section 4's settlement asymmetry with a
number attached, on a measured population, and it is a finding of this stage
whichever way A1d-0 is scored. It is reported and not gated: no criterion here
registers it in advance, and one written after seeing it would be a criterion
the data suggested.

### 2026-08-16, §3's registered prediction is missed

§3 registered that a measured cushion would make the bottom **more** fragile and
that A1d-1 was thereby being made harder to pass. The population says otherwise
at the mean, and the sentence stands as written and wrong:

| net-worth group | households | zero cash | zero share | mean cushion | months of bills |
|---|---|---|---|---|---|
| bottom50 | 50,117 | 1,125 | 2.245% | 7,080 | 2.71 |
| next40 | 40,096 | 243 | 0.606% | 50,309 | 15.65 |
| next9 | 8,919 | 0 | 0.000% | 258,995 | 56.41 |
| top1 | 868 | 0 | 0.000% | 1,005,748 | 170.14 |

A1b handed every household `1.00` month of its own bills. The bottom half's
measured cushion averages `2.71` months, so on average the bottom got **more**
resilient rather than less. `2.245%` of it has nothing at all.

The mean is not the mechanism: `32%` of the population cannot cover period 0 out
of cash, which is the entry above. Both readings are true of the same
population and the registration named only one of them.

### 2026-08-16, A1d-2 fails on one family, and the floor counts copies

**What had been seen when this was written**: the full-size run, 100,000
households with the sweep at 50,000, in which A1d-0, A1d-1, A1d-3, A1-3, A1-6,
A1-9 and A1-10 passed, A1-2 failed as §6.1 said it would, and **A1d-2 failed at
`0.5842 / 0.2562 / 0.0000 / 0.1351`**, which is A1-7's reading to four decimal
places. Then the trace below.

**§6.4's test of §3 returns a verdict, and it is not the one the criterion's
two branches anticipated.** §6.4 said a failure would mean the
non-monotonicity belongs to the data rather than to the missing channel. What
the trace shows is a third thing: **the channel was built, it worked, and it
lost to a zero.**

Five of the 37 `top1` model renters reach sixty days. Their state:

    income/mo 0    rent 2,400    cushion 98,000    net worth ~21,000,000
    first sixty days at t=30, displaced at t=32

**Reported income of exactly zero.** The measured cushion carried them thirty
months, which is §3's channel doing precisely what §3 said it would, and then it
ran out. No finite cushion survives sixty months of nothing.

**And the five are one household.** Records `20760` to `20764` are the five
implicates of a single SCF family: same `LIQ` of `98,000`, same rent, same zero
income, five imputations of one net worth. A1-7 failed on that family too.

**The floor counts the wrong thing.** `RENTER_FLOOR` is 30 and it counts model
households, which are copies twice: five implicates per family, then a
weight-proportional allocation over the implicates. Distinct families behind
each renter cell:

| group | model renters | families | behind | clears a floor of 30 families |
|---|---|---|---|---|
| bottom50 | 28,776 | 1,251 | 16,811 | yes |
| next40 | 2,888 | 150 | 740 | yes |
| next9 | 397 | **30** | 0 | yes, by nothing |
| top1 | 37 | **6** | 5 | no |

The cell that decides A1d-2 is **six families**, and one of them decides it. Five
of its six are behind on nothing.

**Two further things this table shows and the criterion cannot.** `next9` clears
a floor of thirty families by exactly zero margin, so the arm reports a number
sitting on its own threshold rather than comfortably past it. And the floor
decides the verdict through the population size, which A1-10's licence calls an
estimation setting: at 20,000 households the `top1` cell held 6 model renters,
was excluded, and A1d-2 passed monotone on three groups.

An earlier count taken by hand gave `1,311 / 157 / 33 / 7`, on records rather
than on built renters. The difference is records whose rent is zero, which build
no rent obligation and are therefore not renters in the criterion's sense. The
arm's numbers are the criterion's population and the hand count was not; both
are recorded because the hand count is what this ruling was argued from.

**The ruling, taken 2026-08-16: C.** Both readings go on the record. **A1d-2
stands as failed** on its registered count. A **reported and never scored** arm
is added giving each renter cell's distinct-family count and saying what the
criterion would have read under a floor counting families. Nothing is gated on
that arm.

**The reading that was available and was not taken**, recorded because this is
the second time in one day that a stage could have been repaired in the
direction of passing. It would have said: §6.4 registers a floor on *renters*,
renters are people, model households are copies, so counting copies is an
implementation defect and correcting it is not a criterion change. That argument
is the same shape as the one accepted for §6.2's relief arm earlier today, and
it was declined here. Two consecutive implementation repairs that both happen to
run toward a pass is a pattern worth being able to see, and it is now visible in
this document rather than distributed across two accepted arguments.

**Implementation.** `cascade.record_of_each` returns the record index behind
each built household by mirroring `build_from_records`'s own loop, with
`test_the_record_map_lines_up_with_the_population` asserting the alignment on
attributes only the record can supply. A family is a record index over
`IMPLICATES`, the same divisor §5's standard errors use. Nothing in the
mechanism reads any of it.

### Anything altered after this date

Goes here with the date, the reason, and what had been seen at the time.
