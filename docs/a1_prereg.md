# A1: the default cascade

Pre-registration for **stage A1**. Every population, denominator, threshold,
window and criterion is fixed here, before any line of
`experiments/a1_default_cascade.py` exists.

Availability, sourcing, and the two rulings that opened this stage are in
[`a1_availability.md`](a1_availability.md). That document carries three things a
reader should see before this one: **two of the six registered targets turned out
to be one table rather than two sources**; **the stratification the shopping list
assumed does not exist in public form**; and **one of the six targets came from a
sample whose construction removes households that stop paying**, which is the
population this stage exists to model.

`b1_theorem.md` Corollary 1 is load-bearing in section 2.4 and again in A1-9. The
retention mechanism is A0's and is not re-derived here.

---

## 1. What this stage is for, and what it can end

**The claim under test** is 卷一·十八 and 卷一·四: when the claims reaching a
household fall below what it owes, it does not default on everything at once and
does not default at random. It defaults in an order, and the order is produced by
the relative cost of each default rather than by a rule written down in advance.
The cascade named in the manuscript is

    credit card (sacrifice the future) -> auto loan (sacrifice mobility)
      -> rent (sacrifice shelter) -> eviction (physical displacement)

**What it discriminates against.** A model in which a shortfall is absorbed
proportionally across obligations predicts no order and no K shape. A model in
which default probability is a function of income alone predicts a gradient in
income but the same product mix at every income. Both are ruled out by A1-2 and
A1-3 if those pass, and neither is ruled out by matching a level.

**This stage carries a termination right.** `PROJECT_PLAN.md` §5.3: if A0 and A1
are both substantively refuted, the A track stops and Volume One is rewritten.
A1 is therefore not a completion task and its failure criteria are not
formalities.

**What this stage cannot do.** It is a mechanism demonstration with published
levels substituted into it, on the same boundary A3 settled in its §6.6: it can
support "in a stratified economy under a retention shock, obligations fail in a
cost order and the failure concentrates by stratum", and it cannot support "the
observed 2026 delinquency pattern was produced by this mechanism". Section 8
states the boundary in full.

---

## 2. The model

### 2.1 The population, and where every number in it comes from

The stratified arm uses the DFA grouping already in `calibration.py` and already
shared with A0, so A1 introduces no new population: counts `(50, 40, 9, 1)` for
the bottom 50%, next 40%, next 9% and top 1%, net worth shares
`(0.025, 0.296, 0.363, 0.316)`, vintage Q1 2026.

Two further DFA figures, recorded in `calibration.py` since A0 and unused until
now, are what make the cascade bite in the right place:

> bottom 50% share of consumer credit **51.8%** (`WFRBSB50211`)
> bottom 50% share of total liabilities **30.4%** (`WFRBSB50208`)
> bottom 50% share of net worth **2.5%** (`WFRBSB50215`)

**The obligation structure is taken from published shares, not chosen.**
Consumer credit and home mortgages are each allocated across strata to reproduce
the DFA's own share for that instrument and that wealth group, so the mortgage
stock concentrates upward without any parameter saying so.

**Corrected 2026-08-13, before any run.** This section first said the mortgage
stock was the *residual* of total liabilities minus consumer credit. It cannot
be: at 2026Q1 Z.1 puts household liabilities at 21,560.0 bn against 13,821.0 bn
of one-to-four-family mortgages and 5,073.0 bn of consumer credit, so **12.4% of
the total is neither**, and a two-way split would push all of it into the
mortgage leg, which is the leg A1-3 rests on. Both legs are now read from the
DFA directly. See [`a1_inputs_availability.md`](a1_inputs_availability.md) §1.

Housing tenure is a separate input rather than a by-product of the split: a
household owns or rents according to `homeownership_by_stratum`, and only owners
carry a share of the stratum's mortgage stock. No published source gives
homeownership by net worth percentile, so it is computed from the SCF summary
extract; the same check §2 records that route and its 2022 vintage.

**This is where the K shape comes from, and it must be said before the run rather
than after.** Mortgage delinquency will come out low in this model for two
reasons: mortgage holders sit in strata whose income does not fall below their
obligations as often, and shelter is last in the cost order. Neither is a
mortgage-specific parameter, and A1-3 gates on exactly that distinction.

### 2.2 The cascade is a cost ordering, and the cost moves

Each obligation carries a **resource at stake** and a **grace period**, the
arrears after which the resource is actually lost. The cost of defaulting now is
the share of that grace the default consumes:

    cost_now(k) = 0                                       if k cannot be saved now
                = resource[k] × (missed[k] + 1) / grace[k]     otherwise

A household short of cash drops the cheapest-now obligation it holds, then the
next, until what remains can be paid. **No sequence is written anywhere in the
code.** The pairs come from the manuscript's own descriptions and from the
institutions; the order is an output, and it is not constant over time.

Three consequences, all of them the rule's rather than additions to it:

**Falling behind makes a rung harder to default on.** Shelter at no arrears costs
a quarter of the eviction clock; at three arrears the next miss *is* the
eviction. A household deep in rent arrears therefore starts cutting the basket to
keep the roof. **Whether that happens at all depends on `grace_basket`**: a
basket that cannot absorb even one period is as costly as an eviction, and the
household lets the dwelling go instead. That is why `grace_basket` is swept
rather than pinned, and it is registered here that the sweep decides the
existence of the phase and not merely its size.

**What cannot be saved is released first.** An obligation whose arrears could not
be cleared even by spending everything on hand is lost whatever the household
does, so its cost falls to zero **and it sorts ahead of everything still
savable**. Releasing it is what frees the cash that keeps the rest. Without it a
household sacrifices the card and the car to a dwelling it loses anyway.

**Renting and owning are two clocks.** An eviction runs in months; federal
servicing rules bar a first foreclosure filing until a borrower is more than 120
days delinquent, and the process runs well beyond that. One clock for both made
the mortgage, the largest obligation on the books, reach its cliff as fast as a
month's rent, and an owner abandoned it before a renter abandoned a tenancy.

**A registered consequence of the two clocks, recorded before the run**: at no
arrears the mortgage is the cheapest real obligation to skip, because one missed
payment consumes a twelfth of the foreclosure clock against a third of the
repossession clock. So a squeezed owner skips the mortgage before the car. This
is the reversal of the payment hierarchy reported after 2008, and it is a
prediction here rather than an input. It does not by itself move A1-3: mortgage
delinquency comes out low through **who holds mortgages**, not through owners
protecting them month by month. If A1-3 fails, this is the first thing to look
at, and the failure is then informative rather than opaque.

### 2.3 Settlement asymmetry is what makes a shortfall bite

卷一·四. Obligations fall due on a schedule and claims arrive on another, and a
claim arriving after the due date does not discharge an obligation due before it.
The model therefore has a due date and an arrival date per period, and a
shortfall is evaluated at the due date. **A model that nets income against
obligations over the period has removed the mechanism**: on a period-average
basis most defaulting households in this model are solvent.

### 2.4 The two arms, and why the second one is not a simplification

**Stratified arm (main).** The population of 2.1.

**Representative arm (control).** The single representative household of
`PROJECT_PLAN.md` §A1's original setting.

The representative household is an arm rather than the setting because this
project has already ruled that it does not exist. `b1_theorem.md` **Corollary 1**
removes the single-index representation from one inequality on one edge for one
pair of agents. In this carrier, collapsing the household dimension to a single
vertex leaves `Γ` as one copy of the position graph: **no position-agent
rectangle exists, so square holonomy is zero, and the agent-slice summand
`H¹(H)` is zero**, both by construction rather than by parameter. The
manuscript's methodological preface says the same thing in words, naming the
representative individual imposed on a population whose dynamics live in its
heterogeneity as a category error.

The arithmetic agrees: a single household's per-rung rate takes values in
`{0, 1}`. Every target in section 3 except the order is a rate.

### 2.4b Two structures added 2026-08-13, before any scored run

Both were added while implementing `cascade.py` and both move results, so they
are registered here rather than left in the code. Section 11 records what had
been seen when they were added, which was one smoke run with no scored quantity
in it.

**The necessities basket is a rung, and shelter is not in it.** A household
meets a basket of food, utilities, healthcare and commuting, and it is the rung
with the shortest grace: ordinarily the last thing given up, and not impossible
to give up. Without it the model is insensitive to a shock of any size that
leaves income above debt service, because the unspent remainder accumulates
forever.

**Corrected 2026-08-15**: the basket first included shelter, which double-counted
it. The CEX `Shelter` line is rent plus owned-dwelling costs, so a household paid
its rent once as an undefaultable necessity and again as a defaultable rung, and
the correction is not only arithmetic: putting shelter in a senior basket asserts
that the dwelling cannot be given up, which is the opposite of what 卷一·十八
says. Shelter is a rung; the basket is the five other items.

**Arrears carry forward.** A missed payment does not vanish; the household owes
it again next period, and becomes current only by clearing the arrears together
with the current due. Without this the delinquency counter oscillates between one
and zero and nothing ever reaches ninety days, which would make section 2.5's
mapping unreachable in principle. This is also the ratchet 卷一·十八 describes:
falling behind makes catching up harder, at no extra parameter.

### 2.6 How a household is built, and why none of them can be infeasible

Every per-stratum quantity is monthly, per household, and published: income and
the basket from the CEX decile table; the rent a renter pays and the payment an
owner makes from the same table, each divided by its own tenure's share rather
than spread over every household; homeownership from the SCF, computed because
nobody publishes it by wealth; the consumer credit of that group, and the
mortgage balance an owner of that group carries, from the DFA shares at the Z.1
scale.

**The mortgage rung carries a stock and a flow and they are two sources.** The
balance is the DFA mortgage share of the Z.1 aggregate over that stratum's
owners; the payment is the CEX line. The distinction is not bookkeeping: A1-3 is
scored on a *percent of balance*, so which owners carry how much debt is what
the criterion weighs, and that is exactly what the DFA publishes. Section 11
records that until 2026-08-15 the balance was one month of the payment and both
DFA mortgage inputs read nothing.

**The count that turns an aggregate into a household is the CEX's own.** A
national stock has to be divided by a number of households somewhere, and the
number decides the level of every obligation in the stage. It is taken from the
same table as the income, so the unit of observation in the denominator is the
one in the numerator: 135,760,000 consumer units, reference year 2024. A Census
household and an SCF family are different objects and a different count.

What is left after the basket and the shelter payment is the **disposable**, and
the card and car service is a **Beta share of it**, so it lies strictly inside
zero and one and every household can meet its obligations at baseline **by
construction**. The draw's mean reproduces the group's published consumer credit,
so the aggregate is data and the spread is the model's. The stock is therefore an
output, and the experiment reports its realisation against the published target
rather than assuming they agree.

**A group whose published debt cannot be serviced out of its published
disposable raises rather than rescales.** That would be a finding about the data,
and the constructor must not absorb it.

### 2.5 Period length, and what "90+ days" means in a model with no days

**One model period is one month.** An obligation is *90+ delinquent* when it has
been unpaid at three consecutive due dates. Both come from the target definition
rather than from tuning: the source counts a balance as 90+ days delinquent, and
three monthly due dates is the shortest span that satisfies it.

This mapping is registered because it is the kind of choice that later looks
innocent. A two-period rule would raise every model rate and could be selected
after seeing the levels.

---

## 3. The measurement

### 3.1 Stock, declared once, before any column is quoted

**A1 emits a stock: the share of outstanding balance in each obligation class
that is 90+ delinquent at the end of the period.** It is scored against HHDC
Page 12, `Percent of Balance 90+ Days Delinquent by Loan Type`.

The workbook also publishes a flow, Page 14, and for 2026Q1 the two differ by
close to a factor of two on the same product: auto `5.60` against `2.97`, card
`13.12` against `7.10`. The flow is annualised and computed on balances that were
current or less than 90 days late in the previous quarter. **A1 does not emit
it**, and no criterion below may be scored against Page 14.

Denominators, one line each, since half of `MEASUREMENT.md`'s failure modes enter
through this door:

| quantity | denominator |
|---|---|
| model card, auto, mortgage 90+ | outstanding balance of that obligation class, all households |
| model subprime gradient | outstanding auto balance within a stratum |
| model rent arrears | renter households, not balances, because the source counts households |
| model displacement | renter households |

### 3.2 What each rung is scored against

| rung | source | vintage | quantity |
|---|---|---|---|
| card | HHDC Page 12, `CC` | 2026Q1 | `13.12` % of balance 90+ |
| auto | HHDC Page 12, `AUTO` | 2026Q1 | `5.60` % of balance 90+ |
| mortgage | HHDC Page 12, `MORTGAGE` | 2026Q1 | `1.09` % of balance 90+, used ordinally |
| subprime auto | FEDS Note 2025-11-24, CCP | 2025Q3 | subprime `<620` `15.78` against near-prime `2.92`, 30+ days, balances |
| rent | Fed SHED | 2025 | `23%` of renters behind at some point in twelve months; by income `33 / 31 / 17 / 5` |
| eviction | Eviction Lab ETS | 2025 | `1.23M` filings across monitored sites, about one third of renter households |

Everything in the "literature, never fitted" column of
[`a1_availability.md`](a1_availability.md) §8 item 4 stays out of this table.

---

## 4. The arms that keep it honest

### 4.1 Zero calibration

Standard equipment (`MEASUREMENT.md` item 7). A cell with the retention path set
to zero, so no household ever faces a shortfall, must report **exactly zero** on
every rung, in both arms, for every seed, through the same code path as the
scored cells. A5-6 is the precedent for why this is not optional.

### 4.2 An inert-cell detector

Every swept parameter gets the check `HANDOFF.md` lesson two requires: if a
cell's results are bit-identical to the registered point, it is reported as
`inert` and named, and it does not count as evidence. `centrality_bins` was a
field with documentation, validation and no reader, and the grid scanned it twice
and reported clean.

### 4.3 The representative arm is a localizer

See A1-9. It is the instrument that separates "the cost ordering is wrong" from
"the population is missing", which no other cell in this stage can do.

---

## 5. Pre-registered criteria

Gated criteria are ordinal or sign-based except A1-4 and A1-5, and those two are
gated on the model's own dispersion rather than on a tolerance. Section 11
records why, since it departs from what the availability check proposed.

### A1-1. Zero calibration

Retention off, every rung reports `0.000000` in both arms and every seed, bit for
bit. **Fails** if any rung is nonzero, and a nonzero here voids every other
criterion in the stage rather than being reported beside them.

### A1-2. The order is an output

Among households defaulting at least once:

    share whose first default is the card
      > share whose first default is the auto loan
      > share whose first default is rent or mortgage

Strict inequalities, no level. **Source of the ordering**: 卷一·十八. **Fails**
if any inequality reverses. A reversal is the manuscript's sequence being wrong,
not the code being wrong, and it is recorded as such.

### A1-3. K shape, ordinally, and with the parameter check attached

    model mortgage 90+ < model auto 90+ < model card 90+

**Source of the order**: the workbook itself, 2026Q1, `1.09 < 5.60 < 13.12`.

**Attached gate**: the experiment prints `(c_now, c_later)` for all four
obligation classes and the rule that produced them. If the mortgage pair is
produced by a different rule, or carries a multiplier no other class carries, the
criterion **fails even if the inequality holds**, and the stage records "the K
shape requires an exogenous homeowner-protection assumption", which
`PROJECT_PLAN.md` §A1 already names as a finding with content.

### A1-4 and A1-5. Card and auto levels: reported, not gated

**Changed 2026-08-15, before any run.** These were gated on the published value
lying inside the model's cross-seed interval, with a width cap from the series'
own range. That gate is a function of the population size, and the population
size is not a behavioural parameter: it is an estimation setting that this stage
now chooses per criterion (§A1-10). A gate whose width follows a setting nobody
registered is a tolerance chosen after the fact, which is exactly what the
inherited `±1.5` percentage points was rejected for.

So the levels are **reported and not scored**:

| | target | reporting unit | full published range |
|---|---|---|---|
| card | `13.12` | `0.475` pp | `7.08` to `13.74` |
| auto | `5.60` | `0.180` pp | `1.99` to `5.60` |

The reporting unit is the standard deviation of that series' own quarterly first
differences over 2003Q1 to 2026Q1, computed by the experiment from the workbook
rather than typed in. The distance from the model's cross-seed median to the
target is printed in those units, beside the cross-seed interval and its width.
A reader can then see how far off the model is in units of the source's own
movement, and no verdict rests on it.

**What still gates the levels is A1-3's ordering**, which is ordinal and needs no
tolerance, and A1-10's requirement that one parameter set produce all of them.

### A1-6. The subprime gradient

**Gated on sign only**: model bottom-stratum auto delinquency exceeds
middle-stratum auto delinquency.

**Reported, not gated**: the model's ratio, beside the four published readings of
the same ratio at 30+ days on balances, `5.33` (2000Q1), `5.85` (2019Q4), `5.58`
(2024Q4), `5.40` (2025Q3). The gate is only the sign because the source's
threshold is 30 days and the model's is 90; a level comparison across two
thresholds is the denominator error this project has now recorded seven times.

### A1-7. The rent gradient is monotone in income

Weakly monotone decreasing **across the strata that contain renters**, with the
bottom strictly above the highest such stratum. **Source**: SHED 2025,
`33 / 31 / 17 / 5` by income band, itself weakly monotone with two adjacent bands
nearly equal.

**Restricted 2026-08-15, before any run.** The SCF homeownership rates are
`0.391 / 0.925 / 0.953 / 0.961`, so at a hundred households the top two strata
round to zero renters and the criterion is undefined on half its range. A stable
rate in the top 1% needs roughly eighty thousand households, and the population
size is an estimation setting rather than a behavioural one (§A1-10), so this
criterion runs at whatever size gives every stratum it scores at least thirty
renters. The strata that fall below that floor at the size used are **named in
the output and excluded from the comparison**, rather than scored on a handful.

**Reported, not gated**: the model's overall renter arrears level against SHED's
`23%`. The source counts households behind *at some point in twelve months* and
the model emits a point-in-time stock. That is `MEASUREMENT.md` checklist item 1,
and it is why `23%` and a monthly rate near `11%` are not in conflict.

### A1-8. The eviction rung is reported and never scored

Three independent reasons, each sufficient: the public series counts **filings**,
a claim-side event, while the model's last rung is **displacement**, a
resource-side event, and the Eviction Lab's 2022 methodology states its records
cannot measure how many households were displaced; coverage is about one third of
renter households and is stated by the publisher to be not nationally
representative; and the quantity is a **count**, on which a percentage-point
tolerance is undefined.

**Reported**: the model's displacement share, and the model's ratio of rent
defaults to displacements, beside the only anchor that carries both quantities,
2016's roughly `2.35M` filings against `0.90M` evictions.

### A1-9. The representative arm, and what it localizes

**Registered expectation, sourced from `b1_theorem.md` Corollary 1 and from the
degeneracy in §2.4**: the representative arm's per-rung rates take values in
`{0, 1}`, so A1-4 and A1-5 cannot be met there except at a boundary, and A1-3,
A1-6 and A1-7 are undefined there because each is a contrast across households.

**What is actually learned, registered both ways:**

| representative arm | stratified arm | reading |
|---|---|---|
| A1-2 passes | A1-2 passes | the cost ordering is doing the work; the population supplies the rates |
| A1-2 **fails** | either | **the cost-ordering rule is wrong**, and no amount of population fixes it |
| A1-2 passes, rates degenerate | rates non-degenerate | the difference between the arms is the population, which is Corollary 1 with a number attached |
| A1-2 passes, rates **non-degenerate** | any | the setting is not what §2.4 says it is; stop and find the heterogeneity that leaked in |

The last row is the one that would be a surprise, and it is registered so that it
cannot be explained away afterwards.

### A1-10. One parameter set across every rung

`PROJECT_PLAN.md` §A1's own failure criterion, promoted to a gate: **every scored
rung comes from one behavioural parameter vector.** The experiment prints the
vector once and asserts a single vector produced every rung. Any per-rung
adjustment fails the stage, and by §A1 that failure is the coverage test failing,
which requires stopping and redesigning rather than reporting a partial pass.

**Behavioural and estimation settings are distinguished, registered 2026-08-15.**
The behavioural vector is the cost rule, the graces, the buffer and the
dispersion. The **population size and the seed count are estimation settings**,
chosen per criterion, and the licence for that is a property of this model rather
than a convenience: **households do not interact.** Each household's trajectory
depends only on its own income, basket, obligations and buffer, so the population
size buys precision and changes no behaviour. The experiment carries a test that
a household's arrears series is identical alone and inside a population of ten
thousand, and if that test fails the licence is withdrawn and every criterion
runs at one size.

### A1-11. The free-parameter count

**Free** means not taken from a cited published source. `PROJECT_PLAN.md` §A1
registers `参数总数 ≤ 12`, counted when the setting was one household. The count
is re-taken here for the stratified arm and the bound is kept: **at most twelve
free parameters**, printed by the experiment with a provenance line each. Values
from DFA, from Fagereng, Holm & Natvik, from the HHDC workbook and from the
90-day definition are not free and are printed in a separate list.

---

## 6. Registered constants, and the source of each

| constant | value | source |
|---|---|---|
| strata counts | `50 / 40 / 9 / 1` | DFA percentile widths, `calibration.py` |
| net worth shares | `0.025 / 0.296 / 0.363 / 0.316` | DFA Q1 2026, four series in `calibration.py` |
| bottom 50% consumer credit share | `51.8%` | DFA `WFRBSB50211` |
| bottom 50% liabilities share | `30.4%` | DFA `WFRBSB50208` |
| spending propensities | range and ordering only | Fagereng, Holm & Natvik (2021) |
| card target, width cap, reporting unit | `13.12` / `6.66` / `0.475` | HHDC 2026Q1 Page 12, computed from the same series |
| auto target, width cap, reporting unit | `5.60` / `3.61` / `0.180` | as above |
| mortgage ordinal position | `1.09`, used only as an order | HHDC 2026Q1 Page 12 |
| subprime ratio band | `5.33 – 5.85` | FEDS Note 2025-11-24, four dated readings |
| rent gradient | `33 / 31 / 17 / 5` | SHED 2025 by income band |
| eviction anchor | `2.35M / 0.90M` (2016) | Eviction Lab national estimates |
| seeds | `20` | project precedent: the A3-8 scope diagnostic |
| delinquency persistence | `3` periods, period = one month | the 90-day definition itself |
| necessities basket | by stratum, no default | CEX Table 1101/1110, reference year 2024; see [`a1_inputs_availability.md`](a1_inputs_availability.md) §3 |
| housing tenure by stratum | three shares, no default | CEX Table 1110 by income decile: `Homeowner`, `With mortgage`, `Renter`. The SCF's net-worth version is the second arm; see §11 |
| debt split by wealth group | consumer credit and home mortgages, per group | DFA. **Not** a residual of total liabilities: 12.4% of Z.1 household liabilities is neither mortgage nor consumer credit; see the same check §1 |
| household count | `135,760,000` consumer units | CEX Table 1110, reference year 2024, the same table the income comes from |
| tenure, all units | `0.65` own, `0.37` mortgaged, `0.35` rent | CEX Table 1110. The SCF's national rate is `0.6605`, which agrees; the two disagree about the distribution |
| owner's shelter payment | interest plus principal, as magnitudes | CEX Table 1110. The principal line is published negative at every decile; see §11 |

**No constant in this table was chosen by this repository.** The two computed
ones, `6.66 / 0.475` and `3.61 / 0.180`, are functions of the published series
and are recomputed by the experiment from the workbook rather than typed in.

---

## 7. Falsification

| outcome | what it refutes |
|---|---|
| A1-2 reverses (rent defaults before the card) | 卷一·十八's cost ordering. The manuscript's sequence is wrong and is rewritten |
| A1-10 fails: rungs need per-rung parameters | the coverage test of 第十三节. This is not a cascade model, it is four fits, and the stage stops rather than reporting a partial pass |
| A1-3 holds only with a mortgage-specific parameter | the K shape as an emergent property. Recorded as "K requires an exogenous homeowner-protection assumption", which is itself a claim about policy rather than about the mechanism |
| A1-1 nonzero | the instrument. Nothing else in the stage is readable |
| A1-2 fails in **both** arms | the ordering rule, localized by A1-9 |

**Termination.** `PROJECT_PLAN.md` §5.3: A0 and A1 both substantively refuted
stops the A track. A1-2 reversing plus A1-10 failing is that condition on this
stage's side.

---

## 8. Scope, and what A1 is not evidence for

**Supported if the criteria pass**: in a stratified economy where claims reaching
households fall short of obligations at a due date, obligations fail in an order
set by relative default cost, the failure concentrates in the strata holding
consumer credit against little net worth, and removing the stratification removes
the rates while leaving the order.

**Not supported**: that the 2026 delinquency pattern was produced by this
mechanism. The levels enter as substituted published values, not as an estimated
fit, and a mechanism model reproducing a level is the Copernican criterion's
weakest kind of evidence: agreement with observation does not distinguish a right
model from an overfitted one.

**Also not supported**: anything about displacement. A1-8 reports the last rung
and scores nothing on it, because the data for it is on the other side of the
claim/resource line.

---

## 9. What this stage does not contain

- **No stratified delinquency series**, because none is published; see
  [`a1_availability.md`](a1_availability.md) §4. The stratification enters
  through holdings, not through the target.
- **No credit score dimension.** The workbook carries credit score only at
  origination and never crosses it with delinquency.
- **No top-end income contrast.** The CEX's finest published cut is a decile, so
  `next9` and `top1` read one column and carry identical income, basket and
  shelter figures. The permutation arm's coupling therefore cannot separate them
  on the income side: sixteen strata carry twelve distinct income values, and
  the bottom-right of its table, where a top-1% wealth household draws a next-9%
  income, is the same data either way. **The income-to-wealth mismatch at the top
  cannot be measured in this construction**, and no A1-2 or A1-3 reading at the
  top end may be reported as if it had been.
- **No age dimension**, although the workbook publishes one. The model has no
  age, and adding a dimension because the data has it is how a criterion acquires
  a population it was not designed for.
- **No mortgage cascade.** Mortgage enters as an obligation class for the K shape
  and does not get a rung; the manuscript's cascade is a renter's cascade.

---

## 10. Outputs

`results/a1_default_cascade.json`, and rows in `RESULTS.md` written by the
renderer rather than by hand.

Also `data/processed/a1_model_v1.csv`, the model V1 series that
`claude/模型对表规格_v1.md` requires of the simulation side: the default rate by
claim type per model period, first column the period index, csv, utf-8, LF,
explicit float formatting, no wall clock. The shape it is compared against is the
K type and the rung-by-rung transmission, not a numerical fit, and the comparison
is made on the measurement side.

---

## 11. Changelog

### 2026-08-13, written

Sections 1 to 10 are fixed at this date. No result exists for this stage.

**What changed from [`a1_availability.md`](a1_availability.md) §8 item 3, and
why.** That document proposed "four scoreable quantities plus an order test",
scoring levels "only where the model's denominator is the source's denominator".
Two of the four turned out to have a denominator problem no rewrite removes: the
subprime rung is 30 days against the model's 90, and the rent rung is
twelve-month-ever against a point-in-time stock. Those two are therefore gated on
their gradients and their levels are reported. The remaining two, card and auto,
share the model's denominator exactly, and they are gated on the model's own
cross-seed dispersion plus a width cap taken from the published series.

The alternative was the inherited `±1.5` percentage points, and it is worth
recording why that number could not be kept. It has no source. Against the
series' own quarterly movement it is loose by a factor of three for the card and
**eight** for the auto loan, so a model could sit inside it while missing by two
years of drift. Tightening it to one quarterly standard deviation would have
produced the opposite fault: an unfitted mechanism model landing inside `±0.18`
pp of an observed level would be luck rather than evidence, and a criterion no
honest model can pass is not a criterion. Gating on the model's own dispersion
avoids inventing either number.

**Registered under the two rulings of 2026-08-13**: the stage runs both arms, and
the subprime rung keeps its cut on the CCP reading. Both are recorded in the
availability check where they were taken.

### 2026-08-13, while implementing the model. Two structures added, nothing scored

`cascade.py` and its twenty-five tests were written and run. **No criterion was
evaluated and no target was compared against anything**; what follows was seen in
a smoke run whose parameters were scaffolding.

**What was seen.** A forty-five percent income cut at the bottom stratum produced
**zero** defaults on every rung. The cause was structural rather than numerical:
with nothing else claiming income, a household banks its entire margin every
period and only a shock below debt service itself can ever bite. After the basket
was added, defaults appeared but **no rung ever reached ninety days**, because a
missed payment left no trace and one good month erased two bad ones.

**What was added**: the necessities basket as a senior claim, and arrears carried
forward. Both are in section 2.4b. Neither adds a scored quantity, and the second
adds no parameter at all.

**Why this is recorded rather than merely done.** Both structures move results,
and both were chosen with a model in front of me. Discipline 3 permits a design
to be settled before it runs; it does not permit the choice to be invisible
afterwards. The registered criteria are unchanged.

### 2026-08-13, the inputs check, and one input removed

[`a1_inputs_availability.md`](a1_inputs_availability.md) covers the four
quantities the model refuses to invent. Two consequences bind this
pre-registration:

**The mortgage stock is read, not residualised.** Z.1 at 2026Q1 puts household
liabilities at 21,560.0 bn against 13,821.0 bn of one-to-four-family mortgages
and 5,073.0 bn of consumer credit, leaving **12.4% that is neither**. A two-way
split of total liabilities pushes all of it into the mortgage leg, which is the
leg A1-3 rests on. The DFA publishes consumer credit and home mortgages by the
same wealth groups this stage already uses, so both are read directly.

**The ranking mismatch is registered as an arm rather than absorbed.** The
population is ranked by net worth and the income and basket inputs are published
only by income rank; no source publishes a consumption basket by wealth
percentile. The mismatch is worst at the tails, where this stage lives: in the
SCF 2022 Bulletin the lowest income group's mean net worth (129.7) exceeds the
second group's median (71.0). The registered treatment is in the inputs check §4,
route (A): a main arm assigning by matching rank, and a second arm permuting the
assignment consistently with a rank correlation of 0.76, with every gated
criterion re-run. **Whether a verdict flips is then measured.** If any gated
criterion flips between the two arms, the stage reports both and gates on
neither.

### 2026-08-15, the model met its inputs. Six changes, no result computed

All six were found by building the population out of the four retrieved inputs
and running the constructor. **No criterion was evaluated.**

**The basket double-counted shelter** (§2.4b). Rent was paid once as an
undefaultable necessity and again as a defaultable rung.

**The cost of a default is not constant** (§2.2). Rent that is senior and rent
that is defaultable are not in conflict, they are the same thing at different
severities: the longer the arrears, the closer the cliff, the more binding the
rung. That gave the ramp, the crowding-out of the basket, and the release of what
cannot be saved. All three come out of one rule with per-class attributes, and
the rule now has fewer free parameters than the static version it replaced.

**Renting and owning got their own clocks** (§2.2), because one clock made the
mortgage reach its cliff as fast as a month's rent.

**Displacement ends the obligation** (§2.2). It is removed rather than carried,
the household leaves the delinquency denominator, and it stays in the renter
count it started in. This is not a claim that displaced households are housed for
free: **the stage does not know whether they rehouse or into what**, and a
post-displacement tenancy would be a number where there is no knowledge.

**The service share is drawn, and feasibility is structural** (§2.6). The old
draw put obligations on households independently of income, so infeasibility was
a tail event: never at a hundred households, always at a hundred thousand. A
guard that holds only at small samples is not a guard.

**The share-sum check was stricter than any published vector.** The real DFA
consumer credit shares sum to `1.001` by the publisher's rounding and the model
demanded `1e-9`. It now uses the tolerance the reader already used, and
renormalises explicitly.

Two of the six were caught by tests rather than by inspection: the reversal of
the payment hierarchy, and an arithmetic error where the two payment rates were
blended arithmetically instead of harmonically, which reproduced the published
credit to within a percent and biased every group the same way.

### 2026-08-15, wiring the experiment to the inputs. Three changes, no result computed

All three were found while writing `experiments/a1_default_cascade.py` against
the real files. **No criterion was evaluated.** Two are defects in this
repository's own code and one is a property of the published table.

**The DFA mortgage shares and the Z.1 ratio were an inert cell.** `PopulationSpec`
validated them, renormalised them, refused a vector that did not sum to one, and
printed them in the sourced-parameter list. Nothing read them. The mortgage
rung's *balance* was one month of the CEX payment, so every owner was weighted
by their own flow and the published concentration of mortgage debt entered
nowhere. This is §4.2's own failure mode, under A1-3, whose measure is a percent
of balance. The balance is now the DFA share of the Z.1 aggregate over that
stratum's owners, and there is a test that moving the published vector moves the
balance-weighted rate. **A1-3's registered content is unchanged**; what changed
is that its mortgage leg now reads the input the pre-registration says it reads.

**The owner's payment was two published lines added with their signs.**
`Mortgage interest and charges` is an expenditure. `Mortgage principal paid on
owned property` sits in the addenda under "Other financial information" and is
published **negative at every decile**, because it records a reduction in
liabilities rather than an outlay. Added as published, the owner's annual
payment came out at `283 / 1,386 / 242` across the groups: an order of magnitude
too small, and **falling** at the top, which is the visible half of the error.
Taken as magnitudes it is `2,296 / 8,301 / 20,916` and monotone. The sign is now
read off the file rather than pinned, and a line whose columns disagree about it
is refused rather than given a convention by this repository.

**The household count is the CEX's own.** Dividing a Z.1 aggregate by a number
of households sets the level of every obligation in the stage. The count now
comes from the same table as the income, `135,760,000` consumer units at
reference year 2024, so the denominator counts the unit of observation the
numerator belongs to. The alternative on hand was the SCF's `131,306,389`
families, which is a different object at a 2022 vintage and would have raised
every obligation by about three percent for a reason nobody could see. The
reader carries a band guard, because the figure is published in thousands and a
unit slip there is invisible to every ratio downstream.

None of the three adds a parameter and none changes a criterion. The first two
change results and would have done so silently.

### 2026-08-15, the tenure ruling, and two refusals the model now makes

Found while wiring the income path. **No criterion was evaluated.**

**Tenure is read from the CEX and no longer from the SCF.** A shelter flow
published by income decile has to be divided by a tenure share ranked the same
way. The SCF publishes tenure by net-worth percentile, and dividing one by the
other put the next 40% group's rent at **6,145 dollars a month**: not a rent
anyone pays, but that group's whole rent spending divided by the few of them who
rent *by wealth*. The CEX publishes tenure on the same table, same ranking, same
year, and gives `1,074 / 1,799 / 2,993`. The two sources agree nationally,
`0.65` against `0.6605`. This is ``MEASUREMENT.md``'s population error and it is
the reason the SCF route is now the **second arm** rather than the main one; a
gated criterion that comes out differently between them is gated in neither.

**There are three tenures, not two.** About two fifths of American owners hold
their dwelling free of any mortgage: `0.65` own and `0.37` carry a mortgage. An
outright owner has **no shelter rung**, cannot be displaced, and is in neither
shelter denominator. The mortgage payment and the DFA mortgage stock are both
divided by the **mortgaged** rather than by every owner, which moves the payment
from `366 / 932 / 1,937` to `1,007 / 1,370 / 2,490` a month. Both rulings were
put to the author and taken before the model was rewritten.

**Two things now refuse to be built, and both refusals are results.**

*The second arm has no population.* Under net-worth-ranked tenure the bottom
half's mortgaged households face a payment of `1,345` a month against a
disposable that leaves `476`, while their published consumer credit needs `703`
of service. §2.6 says a group that cannot service its published debt out of its
published disposable raises rather than rescales, so the arm raises. Its
criteria are reported as unbuilt rather than failed.

*The registered dispersion cannot be drawn at the published means.* The service
share is a Beta draw and a Beta with mean `m` cannot have a coefficient of
variation above `sqrt((1 - m) / m)`. At the published inputs the bottom half's
mortgaged households spend `0.862` of their disposable on debt service and its
renters `0.940`, which cap the dispersion at `0.231` and `0.146`. The registered
`0.25` sits above both, and what it produced was not a wide distribution but two
point masses: at ten thousand households, **93% of bottom-half renters drew a
service share above 0.99** and 6% drew below 0.05. The model now refuses rather
than clamps, because clamping would report results under a registered parameter
that was not the one used.

**What this leaves open, stated rather than settled.** The `0.862` and `0.940`
are themselves partly the ranking mismatch: the DFA's bottom 50% is by *net
worth* and carries 51.8% of consumer credit, while the income assigned to it is
the CEX's bottom five *income* deciles. A household with 36,891 of income
carrying 38,674 of consumer credit is that mismatch. The permutation arm this
document registers at rank correlation 0.76 is not yet built, and until it is,
no level from the bottom stratum should be read as a measurement.

### 2026-08-15, the permutation arm, and the dispersion becomes derived

**No criterion was evaluated.** The arm §11 registered but had not built is now
built, and building it changed one registered free parameter.

**The permutation arm is a re-stratification, not a re-weighting.** Route (A) of
[`a1_inputs_availability.md`](a1_inputs_availability.md) §4 asked for the
assignment to be permuted consistently with a rank correlation of `0.76`,
Kennickell (1999) on the 1995 SCF. That is implemented as a Gaussian copula on
the two rankings' own percentile widths, giving a joint law whose margins are
exactly this project's, and the population is rebuilt as **one stratum per
(wealth group, income group) cell**. Everything published by income decile
follows the income index; everything published by wealth group follows the
wealth index; the model is untouched, because a cell is a stratum like any
other, and the criteria are read back on wealth groups through a reporting map
the model carries. A mixture of group means was the alternative and was rejected:
it would leave every group mean intact and destroy the heterogeneity the
mismatch is actually about.

The coupling at `0.76`, as the income mix of each wealth group:

| wealth group | bottom 50% | next 40% | next 9% | top 1% |
|---|---|---|---|---|
| bottom 50% | `0.782` | `0.213` | `0.005` | `0.000` |
| next 40% | `0.266` | `0.624` | `0.107` | `0.003` |
| next 9% | `0.027` | `0.475` | `0.440` | `0.059` |
| top 1% | `0.001` | `0.121` | `0.533` | `0.346` |

At a correlation of one it is the identity and the arm collapses onto the main
one, which is the check that the machinery does nothing when told to.

**The dispersion is now derived rather than registered, and the value is
`0.089`.** A Beta at mean `m` cannot carry a coefficient of variation above
`sqrt((1 - m) / m)`, so the spread a stage can ask for is bounded by its own
tightest cell. The main arm supports `0.146`, bound by the bottom half's renters
at a mean of `0.940`. The permutation arm supports `0.089`, bound by the cell of
next-9%-by-wealth households who sit in the bottom half by income, at a mean of
`0.977`. The experiment computes both, prints them with the binding cell named,
and uses **the largest value every constructible arm supports**, because two
arms drawn at different spreads are two models rather than a sensitivity.

The registered `0.25` is therefore not used, and the reason is not a
preference. At `0.25` the draw was not a wide distribution: at ten thousand
households, 93% of bottom-half renters drew a service share above `0.99` and 6%
drew below `0.05`. The model refuses that rather than clamping it, so the number
in the output is always the number that was drawn.

**What the permutation arm exposes, and what it does not fix.** Its binding cell
is worse than the main arm's, and the reason is worth stating: the arm re-couples
income rank to wealth rank while leaving each wealth group's consumer credit
spread **uniformly within the group**, because no source publishes that
distribution at this cut. Pairing a group-average debt with a below-average
income is therefore possible in the model in a way it is rarely possible in the
world. The arm still does what it was registered to do, which is to measure
whether a verdict depends on the rank assumption; it does not repair the
within-group uniformity, and no criterion may be read as if it did.

**One arm remains unbuildable at any dispersion.** Under net-worth-ranked tenure
the bottom half's mortgaged households need `1.476` of their disposable to
service their published consumer credit. That is a level rather than a spread,
so it is excluded from the dispersion minimum and reported on its own.

### 2026-08-15, the diagnosis, and what the joint says

A read of the construction returned four findings. The first three are accepted
in full and are recorded here; the fourth is a measurement made in answer to
them, in `experiments/a1a_joint_probe.py`, which registers nothing.

**The derived dispersion had no fixed point, and it is withdrawn.** The rule was
"use the largest dispersion every constructible arm supports". The cap is
`sqrt((1 - m) / (m (k + 1)))` at the tightest cell's mean, every arm added brings
fresh off-diagonal cells, and among them there is always one with a more extreme
mean, so the minimum falls monotonically towards zero as arms accumulate. The
rule is well defined only over a **closed** list of arms, and this stage's list
was not closed: the permutation arm exists because a tenure ruling three entries
above made it necessary. An infimum over an open set is not an estimate. This is
the same shape as the defect the `复检 i` note records, a derived quantity read as
an estimator when it was never defined on a closed object. The caps are now
printed per arm, labelled as properties of that arm's crossing, and the
dispersion is the registered `0.25` unless a run states otherwise.

**§2.6's rule needed a scope condition**, now added above. It holds for a group
a publisher reports and not for a cell made by crossing two rankings. Every
stratum in this construction is such a cell, so neither `1.476` nor `0.977` nor
`0.940` is a finding about the data; all three are findings about the crossing.

**The permutation arm binds tighter because it invents cells, not because it is
conservative.** The cell "next 9% by wealth, bottom half by income" does not
exist in the main arm at all; the coupling creates it, and it is then handed its
wealth group's *average* consumer credit against the bottom half's income. Debt
and income are independent inside a group by construction, so that cell is
necessarily the tightest in the table. The main arm's tightest cell is
information about the same households under a different assumption; this one is
a new household.

**What the joint measures, and it is worse than the dispersion.** The SCF 2022
summary extract carries income, net worth, tenure, mortgage debt and payment,
rent, credit card balances and vehicle debt for the same household under one
weight. It is a joint, not two margins. Three readings:

*The coupling was approximately right.* Measured, the income mix of the bottom
half by wealth is `0.721 / 0.272 / 0.007 / 0.000` against the Gaussian copula's
`0.782 / 0.213 / 0.005 / 0.000` at Kennickell's `0.76`. The stand-in was
serviceable. It was also unnecessary, since the joint is published.

*Within-group uniformity is wrong by a factor of two, in the direction the
diagnosis predicted.* Consumer credit rises steeply with income **inside** every
wealth group: in the bottom half by wealth it runs `5,506 / 17,804 / 22,138`
across the income groups. The binding cell of the permutation arm, next-9% wealth
at bottom-half income, measures `5,495` against the `10,011` its group average
would give it and the `41,893` this stage actually gave it.

*The level is off by four.* This stage puts `38,674` of consumer credit on a
bottom-half household. The SCF measures `8,964`. In aggregate the SCF's cards
plus vehicle debt is `1.332` trillion against the Z.1 consumer credit of `5.073`
trillion the stage scales by, a ratio of `0.263`; adding student debt, which has
no rung here, reaches `2.671` trillion. The mortgage leg is close, `11.568`
against `13.821`, ratio `0.837`. So the leg that was wrong is the one the
cascade's first two rungs are made of, and **the 94% service share is largely a
2%-a-month minimum payment charged on a stock that includes balances nobody
revolves.**

**What follows, and what does not.** Adding arms cannot repair within-group
uniformity, because an arm only rearranges margins. The repair is a change of
observable rather than a change of arm: build the population from the joint. That
is a separate station with its own pre-registration, and it is not this document.
Until it exists, **no level emitted by this stage is a measurement**, and the
ordinal criteria are the only ones that can be read at all.

### 2026-08-16, a half-cent tolerance in the shared step, found by A1b

`monetary_topology.cascade.step` now treats a household as short only when it is
short by **more than half a cent**, in both the savable test and the drop loop.
Money is denominated in cents; the comparison is between two sums of the *same*
obligations reached by different routes, and floating-point addition is not
associative.

**A1's own zero calibration could not have found this and did not.** A1's
constructor draws a service share strictly inside zero and one, so every
household carries slack and none sits on the knife edge. It was found by A1b's
calibration on a population built from records, where 589 of 20,000 households
whose income had been raised to cover their obligations exactly were judged
short by `2e-13` dollars and defaulted with no shock at all. A guard that passes
only because nothing was ever near the boundary is `MEASUREMENT.md` checklist
item 8 unanswered, and this is that item answered against A1-1.

**A1-1 still passes** and no criterion is restated. The stage's records should be
regenerated on the changed mechanism rather than carried forward, which is
failure mode 9 and is why `scripts/run_all.py` now carries a job for this stage.

### 2026-08-16, the income path, registered before it is run on

`monetary_topology.income_path` takes the shock from A0 rather than inventing
one, which `cascade.py` has listed among the things it refuses to invent since
it was written. What was never written down is the **identification**, and it is
written here before any criterion runs on it.

**The quantity is `History.terminating[t, s]`**, the claims landing on stratum
`s` in round `t`, normalised by the same stratum's opening round. That is the
quantity 卷一·十八 is about, what reaches a household against what it owes, and
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

### Anything altered after this date

Goes in this section with the date, the reason, and what had been seen at the
time. Sections 1 to 10 are not edited once a result exists.
