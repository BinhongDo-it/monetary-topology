# B2 measurement design: the effective-price loops

**Status: pre-registration.** Written before any data is downloaded. Every
definition, series, sample rule, test and falsification condition below is fixed
in advance so that the result cannot be selected after the fact.

Prerequisite: [`b1_setup.md`](b1_setup.md), which fixes the field. This document
fixes two loops on it and states which one carries which part of the argument.

---

## 1. Two loops, and why both are needed

An earlier draft of this document measured only the vintage loop. That was a
specification error, caught before any data was retrieved, and it is recorded here
rather than silently fixed.

### The objection that sinks the vintage loop on its own

Two owners of the same dwelling, one locked at 3% and one at 7%, do not obviously
hold the same thing. A critic says:

> They hold different assets. One holds a dwelling plus a 3% contract, the other a
> dwelling plus a 7% contract. Different assets, different costs, perfectly
> integrable on the finer position space.

This is correct as stated. Entry date is not an attribute of the holder, it is a
coordinate, and a field that varies with `(position, date)` is the gradient of a
potential on `(position, date)`. **The vintage loop alone does not establish that
the field carries an agent index.**

It survives, but by a different route: the 3% contract is not purchasable. The
finer position space that restores integrability contains positions that cannot be
reached, and integrability on a space you cannot move around in is vacuous. So the
vintage loop's work is done by **the hole**, not by the wedge.

That is a real argument and it is worth making. It is also a second-order one, and
it should not be the first thing a reader meets.

### The loop that carries the agent index directly

Hold the date fixed. Same quarter, same census tract, same lien position, same loan
purpose, same occupancy type. Two applicants for materially the same financing on
materially the same property receive different rates, and a third pays cash and
carries no financing cost at all.

Position identical. Date identical. Market identical. **The terms differ by who is
transacting**, and there is no finer position space to retreat to, because the
position was already held fixed. Absorbing this into a position index requires
indexing positions by the buyer, which concedes the point being argued.

So:

| | loop A: credit | loop B: vintage |
|---|---|---|
| what varies | the buyer, at a fixed date | the date, for a fixed buyer type |
| what it establishes | the field carries an agent index | the gap can be very large |
| survives "different assets" by | nothing to retreat to; position and date both fixed | the unpurchasable contract, i.e. the hole |
| magnitude | rate spread across applicants, order 1-2 points | 3% against 7%, affecting roughly half of holders |
| role | **the logical anchor** | **the magnitude** |

Loop A without loop B is a small and easily dismissed spread. Loop B without loop
A is attackable as timing rather than stratification. Both are measured, and the
paper leads with A.

### Asset tier is not agent class

A second error, from the same draft, and it comes from the framework's own
material. That draft used price tier as though it indexed the agent. It does not.

An individual landlord buys down-market units to rent out and hold for
appreciation. The holder of a bottom-tier asset is then not a bottom-tier agent,
and pooling by price tier averages a landlord together with the household that
could only reach that tier. **Asset tier and agent class are separate indices and
the panel carries both.**

HMDA's occupancy type field separates them directly: principal residence, second
residence, investment property. Every quantity in section 5 is computed within the
cross of `(asset tier) x (occupancy type)`, never within tier alone.

This matters beyond bookkeeping. If the measured gap turns out to be between
occupancy types rather than between tiers, the finding is about **who is holding**
rather than about **what is held**, which is precisely the claim.

### The structure is already published

FHFA's National Mortgage Database reports the distribution of interest rates on
outstanding fixed-rate mortgages quarterly. The share of outstanding loans below
4% peaked at 65.1% in Q1 2022 and stood at 49.9% in Q1 2026, against new
originations at market. **Roughly half the holders of the same position face
materially different terms from the other half.** The two-index structure does not
have to be argued for. It is something the regulator publishes.

## 2. Loop A: same date, same tract, different buyers

Nodes are `(agent class a, owned dwelling, tract n, tier q)` at a single quarter
`t`. Agent classes are distinguished by financing terms received, not by anything
assumed about them.

| leg | definition |
|---|---|
| cash → owned | acquisition at the tract-and-tier price, financed at the rate that applicant actually received |
| owned → holding | debt service at that rate, plus tax, insurance, maintenance, all identical across applicants by construction |
| owned → cash | sale at the same price, same transaction cost |

Everything except the financing term is set identical across agent classes,
because the property, the tract, the tier and the quarter are all held fixed. The
loop sum is therefore the financing term alone:

```
δ_A(n, q, t; a, b)  =  rate_spread(a)  −  rate_spread(b)
```

using HMDA's rate spread, the difference between the loan's APR and the average
prime offer rate for a comparable transaction at the date the rate was set. Being
already expressed against a common benchmark, it is directly a pairwise difference
and needs no further normalisation.

**The cash buyer is the extreme point.** An all-cash purchaser has no financing
term at all, so for them the edge carries a weight no financed buyer can reach at
any rate. That is not the cheapest point on a spectrum, it is off the spectrum,
and the all-cash share of purchases is published.

### Why jurisdiction-level economics cannot contaminate this

Property tax rates, state income tax, and episodes like Florida's price surge are
the obvious worry, and they are the main advantage of measuring dispersion within
a cell rather than fitting a regression.

**Every one of them is constant within a census tract in a given year.** They are
absorbed entirely by the cell, contribute to between-cell variance, and cannot
enter the within-cell term. A surge moves a tract's mean spread; it cannot move the
spread of spreads inside that tract. A regression would have to control for them
one by one and would be asked what it had omitted. This design does not have the
question.

**They do enter through composition, and composition is the object.** If a surge
changes *who* buys in a tract, because cash-rich in-migrants displace marginal
financed buyers upward in tier or out of the market, then within-tract dispersion
moves. Not because a tax changed a price, but because the population of borrowers
changed. That is what the claim is about, so it is endogenous and is not
controlled. It is reported: the panel carries tract and year, so composition shifts
are visible as changes in dispersion over time within a tract.

### The estimate is a lower bound, and the censoring is worst where it matters most

HMDA records financed purchases. **An all-cash buyer generates no record at all.**

Cash purchasers are the extreme point of loop A: they face no financing term, which
is not the cheapest point on a spectrum but a point off it. Every one of them is a
missing observation at the favourable end of the distribution being measured.

So the measured within-cell dispersion understates the field's dispersion, and it
understates it most in exactly the markets where the in-migration pattern is
strongest, since those are where the cash share is highest. Any result should be
read as a floor, and the direction of the bias runs against the claim rather than
for it.

### What the public data can and cannot attribute

The public HMDA loan-level file **contains** rate spread, census tract, lien
status, loan purpose, occupancy type and action taken. It **does not contain
credit score**: 27 fields are redacted for privacy and 6 more are modified,
including debt-to-income ratio, loan amount and property value.

So the loan-level file gives the **dispersion** of terms at fixed position and
date, and cannot by itself attribute that dispersion to credit score. FHFA's NMDB
aggregate statistics publish rates by credit-score band but not at loan level.

Neither source alone is sufficient and the division is stated here rather than
discovered later:

| question | source |
|---|---|
| is there dispersion in terms at fixed position and date | HMDA loan-level rate spread |
| does that dispersion track credit score | NMDB credit-score-banded aggregates |
| is the holder an occupier or an investor | HMDA occupancy type |

The first question is the one that carries the argument. Non-integrability needs a
non-zero loop sum; **it does not need the loop sum to be explained.** Attribution
to credit score is a second and separate claim, made with the aggregates, and
labelled as the weaker of the two.

---

## 3. Loop B: same dwelling, different vintages

Nodes, for a fixed metro `m`, tier `q`, and quarter `t`:

```
  cash(a)  ──────────────►  owned(a, m, q, v)  ──────────────►  cash(a)
             entry leg              exit leg
```

where `v` is the vintage, the quarter in which the position was entered. Two agent
classes are distinguished only by `v`: an early entrant `a₁` with `v = v₁`, and a
current entrant `a₂` with `v = t`.

### Leg 1: entry

| component | definition | inclusive of |
|---|---|---|
| purchase price | metro-level house price index level at `v`, tier-adjusted | — |
| financing rate | the contract rate available at `v` | points, expressed as an effective rate |
| down payment | LTV at origination | — |
| closing costs | amortised over the holding period, not expensed at entry | title, origination, transfer tax |

### Leg 2: holding, per quarter

| component | definition | inclusive of |
|---|---|---|
| debt service | interest on the outstanding balance at the **contract** rate of vintage `v` | not the current market rate; this is the whole point |
| property tax | metro effective rate on assessed value, with the assessment cap applied by vintage | **not a nuisance to control: a second instance of the mechanism, written into statute.** See below |
| insurance | metro average premium | — |
| maintenance | fixed share of value, held constant across vintages | deliberately constant so it cannot generate the gap |
| service flow | imputed rent for the identical unit, **identical across vintages** | set equal by construction, since the unit is the same |

**Assessment caps deserve promotion out of the fine print.** California's
Proposition 13 and Florida's Save Our Homes hold assessed value to the entry basis
and cap its growth, so the same dwelling carries a different tax bill for two
owners purely by date of entry. This is the two-index effective cost written into
law rather than emerging from a market, which makes it a stronger instance than
mortgage lock-in, not a weaker one: nobody can argue it away as a pricing
convention, and its magnitude is a matter of public record. It is measured as part
of loop B rather than netted out of it.

The service flow is set identical across vintages on purpose. It is the same
dwelling delivering the same shelter. Any difference in outcome therefore comes
from the terms of holding rather than from what is held, which is what the loop is
supposed to isolate.

### Leg 3: exit

| component | definition |
|---|---|
| sale price | index level at `t`, same tier |
| transaction cost | brokerage plus transfer, as a share of price |
| **rate forfeiture** | the increase in debt service on repurchasing the same position at the current market rate |

The last row is the hole. For a holder whose contract rate is far below market,
the `owned → cash → owned` transition carries a cost that is not a price on the
dwelling at all: it is the loss of the contract. **The edge is not expensive, it is
absent in the sense that matters**, because the thing forfeited cannot be bought
back at any price.

### The loop sum

```
δ(m, q, v, t)  =  (1/T) · log [ value of holding from v to t under vintage-v terms
                                / value of the same holding under vintage-t terms ]
```

with `T = t − v` in quarters. This is the per-period loop sum of the setup
document. Integrability requires `δ = 0` for every `(m, q, v, t)`.

---

## 4. Series

| quantity | series | source | loop |
|---|---|---|---|
| **rate spread at loan level, by tract** | HMDA modified LAR, `rate_spread` field | FFIEC / CFPB, annual, ~4,800 filers | A |
| **occupancy type** | HMDA modified LAR | separates agent class from asset tier | A, B |
| all-cash purchase share | county deed records or NAR; stated where used | | A |
| **outstanding rate distribution by bucket** | NMDB Outstanding Residential Mortgage Statistics | FHFA, quarterly, national and by segment | B |
| contract rate at vintage | PMMS 30-year fixed, weekly, averaged to quarter | Freddie Mac |
| house price by metro | FHFA HPI, all-transactions and purchase-only, metro | FHFA, quarterly |
| price tier | FHFA HPI by price tier where published; else Zillow ZHVI tiers | FHFA / Zillow |
| imputed rent | Zillow ZORI by metro and bedroom count | Zillow, monthly |
| effective property tax rate | ACS 5-year, metro | Census |
| assessment caps | state statute, coded by hand, dated | state law |
| insurance premium | NAIC homeowners premium by state | NAIC, annual |
| LTV and credit score at origination | NMDB New Residential Mortgage Statistics | FHFA, quarterly |
| transaction cost | fixed at a stated constant, sensitivity-tested | — |

Every series is retrieved with its vintage recorded in `data/SOURCES.md` as
elsewhere in this repository. Anything hand-coded, meaning the assessment caps, is
committed as a dated table with the statute cited per row.

---

## 5. Sample

**Geography: all states, revised from the 50 largest CBSAs.** Recorded rather than
quietly changed, and made before any loop sum was computed.

The first draft named the 50 largest CBSAs by code. The first real call showed two
faults. Divided CBSAs return nothing, because HMDA reports the Metropolitan
Division code rather than the CBSA code for them, so New York and Los Angeles came
back with a header and zero rows. And metro is not a cell key in any case: cells
are defined by census tract, so the metro list only ever fixed the sample frame.

Replacing it with all states **enlarges** the sample from fifty chosen metros to
the whole country. A change that removes a selection cannot introduce one, which is
why it is admissible at this stage while the reverse would not be.

Cross-market dispersion is still reported and still carries the argument. It is
computed across tracts and metros from the returned `derived_msa-md` column rather
than imposed by the query, and nothing is ever pooled into a single national
number.

**Tiers.** Three, by price: bottom, middle, top third of the metro distribution.
Computed within metro, never pooled across metros.

**Occupancy.** Three, from HMDA: principal residence, second residence, investment
property. **Every cell is `(metro) x (tier) x (occupancy)`.** Tier is never used
alone as though it indexed the agent; section 1 says why.

**Vintages.** Every quarter from 2000 Q1 to the latest available.

**Evaluation quarters.** Every quarter from 2010 Q1 to the latest available.

**Holding periods.** All `T` from 4 to 80 quarters, subject to `v ≥ 2000 Q1`.

This yields a panel of `δ(m, q, v, t)`. Nothing is dropped after inspection. If a
cell cannot be computed for lack of data, the reason is recorded before results
are examined.

---

## 6. What gets computed

**Primary, loop A.** The distribution of `δ_A` across `(tract, tier, occupancy,
quarter)` and across applicant pairs within cell. Reported as a dispersion, since
a gradient field returns zero for every pair in every cell.

**Primary, loop B.** The distribution of `δ_B` across `(m, q, v, t)`. Reported as a
distribution, never as a single mean. The setup document's argument is that a
gradient field returns zero on every loop in every market and every year, so the
object of interest is the whole distribution and particularly its dispersion.

**Secondary.** The Hodge decomposition on the graph whose nodes are
`(metro, tier, vintage)` and whose edge weights are the pairwise `δ`, using the
machinery already built and validated in `src/monetary_topology/topology.py`. The
headline scalar is the gradient share: the fraction of the field that a scalar
potential on positions accounts for. Reported with magnitudes alongside shares,
for the reason stage A2c had to learn the hard way.

**Tertiary.** The rate-forfeiture term as a share of the total gap, which
separates the part of the wedge that is a price from the part that is a missing
edge.

---

## 7. The pre-registered discriminating test

The objection the return formulation must survive is that a measured gap is one
episode of repricing rather than a structural per-period wedge. The test is fixed
here, before any data is seen.

**Windows.** Four non-overlapping ten-year windows: 1990s where data permit,
2000-2009, 2010-2019, 2016-2025.

**Structural, if** the sign of median `δ` is the same in every window and the
magnitude is within one order of magnitude across them.

**Episodic, if** the sign holds in one or two windows and reverses or vanishes in
the others.

**Reported as episodic** if the criterion for structural is not met. That outcome
is not a failure of the measurement, it is a finding about the mechanism, and it
downgrades the compounding claim to an episodic one while leaving the
non-integrability claim untouched, since a non-zero loop sum is a non-zero loop
sum whatever produced it.

---

## 8. Falsification

Stated in advance, and none of these are recoverable by re-specification.

| observation | consequence |
|---|---|
| `δ` is statistically indistinguishable from zero across the panel | The field is a gradient on this loop. The vintage argument fails and the setup document's canonical example must be withdrawn. |
| `δ` is non-zero but its dispersion across metros and tiers is negligible | Consistent with a single scalar plus noise. Much weaker than claimed, and the framing in setup section 3 must be rewritten. |
| the gradient share of the Hodge decomposition exceeds roughly 0.9 | The field is nearly integrable. Volume II's claim would be technically true and practically empty on this data. |
| `δ` correlates with tier but vanishes within tier | The gap is between assets rather than between holders. That is price dispersion, not the two-index structure, and the argument would have to move to a different loop. |
| the structural criterion in section 7 fails | The compounding claim is downgraded to episodic. Reported, not hidden. |
| `δ_A` is indistinguishable from zero within cells | There is no dispersion in terms at fixed position and date. The agent index is not carried by the data and loop A is withdrawn, leaving only loop B and its weaker hole argument. |
| `δ_A` is non-zero but vanishes once occupancy type is conditioned on | The gap is between occupiers and investors rather than across agents generally. Still a two-index finding, but a narrower one, and it must be restated that way. |
| `δ_A` dispersion is entirely accounted for by loan characteristics that are themselves positions, such as lien or purpose | The position space was not held fixed after all. The cell definition must be tightened and the measurement rerun before anything is claimed. |
| | **Computed 2026-08-29. It does not fire: the accounting is partial, not entire. Reading in section 8.2.** |
| the conventional-VA gap in section 8.1 is absent, or runs the other way | The within share is measuring how wide the borrower pool is, not how much the lender prices the borrower. Loop A would still show non-integrability but could no longer attribute it to the agent index, and the attribution claim must be withdrawn. |
| the conventional-VA gap is present but no larger than the split-half null | The gap is sampling variability. Same consequence as above. |

---

## 8.2 The position-attribute falsification, computed

**Registered in section 8, row eight. Computed 2026-08-29 by
`experiments/b2c_position_attributes.py`, record in
`results/b2c_position_attributes.json`.** It had not been computed before that
date and it is not among the five conditions `LoopAResult.falsifications()`
evaluates. The columns it needs were retained at fetch time for it and were
otherwise unused.

**Why it took its own stage.** The question is whether the within-cell dispersion
is produced by loan attributes a scalar account is entitled to read, which are
contract terms rather than borrower characteristics. Answering it means refining
the cell, and **a refinement lowers within-cell dispersion whether or not the
added key explains anything**, because the cells get smaller and the degrees of
freedom go with them. On a six-state sample the artefact was larger than the
signal: a label drawn at random with the same bin count took the within-share
from `0.8379` to `0.1782`, while the real term-and-LTV refinement took it to
`0.4207`. Read against the baseline, the naive conclusion would have been
backwards.

**The control.** Each real arm is paired with a twin in which the added labels are
permuted **inside each baseline cell**. The refined partition then has, cell for
cell, the same sizes and the same label marginals as its real arm, and the only
thing destroyed is the association between the label and the rate spread. Five
draws per twin, and the spread across draws is reported so that a difference
smaller than it is not read as one.

**Readings, full sample, 20,071,740 loans.**

| arm | keys added | within | twin median | real − twin | twin spread | multiple |
|---|---|---:|---:|---:|---:|---:|
| A0 | none, the seven registered keys | `0.7831` | | | | |
| A1 | loan term | `0.7000` | `0.7441` | `−0.0440` | `0.00034` | 129 |
| A2 | loan term, LTV | `0.4720` | `0.5620` | `−0.0901` | `0.00071` | 127 |
| G1 | debt-to-income | `0.6003` | `0.6390` | `−0.0387` | `0.00058` | 66 |
| G2 | term, LTV, DTI | `0.2394` | `0.2947` | `−0.0553` | `0.00093` | 59 |

`A0` reproduces the registered `0.7831` exactly, which is the first thing the
stage checks.

**The condition does not fire, because the word it turns on is "entirely".** The
registered row asks whether the dispersion is *entirely* accounted for by
position-side loan characteristics. It is not. After both contract keys are held
fixed, `0.4720` of the variance is still inside the refined cells at a median
within-cell interquartile range of `0.4010` percentage points, about forty times
the quantum of a figure published to two and three decimals. The registered
consequence, that the cell must be redrawn and the measurement rerun before
anything is claimed, attaches to the entire case and is not triggered.

**What the stage does establish, in three parts, and the third is new.**

1. **Contract terms outside the cell account for part of the dispersion.** Term
   and LTV together are worth `0.0901` of within-share net of the refinement
   artefact, at 127 times the permutation spread. **Any statement that the
   within-cell dispersion is independent of unmodelled contract terms is refuted
   by this arm**, and no such statement should be made.
2. **They do not account for it.** The residual above is what a scalar field
   reading both keys still cannot generate.
3. **One contract key and one borrower key are worth about the same here.** Term
   alone nets `−0.0440` and debt-to-income alone nets `−0.0387`. So the residual
   cannot be assigned wholly to the agent index either. Section 10's reading
   carries this qualification: the within-cell dispersion is not shown to be
   agent-borne, it is shown to survive both of the position keys tested and both
   of the borrower keys available.

**Coverage, reported rather than hidden.** The refined arms lose cells to the
`min_size = 20` floor: `A2`'s surviving cells hold `15.0` per cent of loans and
`G2`'s hold `1.4` per cent. The within-share column is computed at `min_size = 0`
over the whole sample and is unaffected by that floor; the interquartile column
on those arms is computed on the smaller surviving set and is read with that in
mind. Missing rates on the added keys are `0.0005` for term, `0.0079` for LTV
and `0.0084` for debt-to-income.

**What is still not tested.** Discount points and total loan costs were retained
at fetch time and are not used here, because both are components of the price of
the same transaction rather than attributes of the position, so conditioning on
them would move part of the measured quantity into the control. Credit score is
not in the extract at all, and it is the borrower attribute the conventional
pricing grid is written on. **The borrower side of part 3 rests on
debt-to-income alone.**

---

## 8.1 The graded placebo: conventional against FHA and VA

**Written before any FHA or VA data was retrieved.** The retrieval script gained
`--product` in the same edit that added this section, and the conventional result
in section 10.4 was already fixed at that point.

### The problem this addresses

Loop A shows dispersion at fixed position and date. It does not show that the
dispersion is carried by the agent index rather than by something the cell keys
failed to hold fixed. A placebo needs a case where the agent index is
mechanically suppressed while the position keys stay identical.

Government-insured lending is that case. Conventional pricing runs an explicit
credit-graded surcharge grid, the loan-level price adjustments, which is a
published function of credit score against loan-to-value. FHA substitutes a
mortgage insurance premium set by a flat schedule, and VA substitutes a funding
fee that varies with down payment and with first against subsequent use but not
with credit score. Same tracts, same years, same dwellings, same lien, same
purpose; the borrower-graded component of the price is removed by programme rule.

### Why VA carries the test and FHA does not

The obvious prediction, `within_share(FHA) < within_share(conventional)`, has a
mundane rival that predicts the same sign. FHA borrowers are a narrower pool: if
the observed `a` values span a shorter interval, then `P(a, g)` varies less over
the realised sample even if the field is exactly as non-integrable. Sign
agreement means FHA alone discriminates nothing.

VA separates them. VA eligibility is service-based, not credit-based, so the VA
pool spans a credit range comparable to conventional and wider than FHA, while
the price grid is flat. The two accounts therefore disagree:

| | pool width | credit-graded price grid | pool-width account predicts | agent-index account predicts |
|---|---|---|---|---|
| conventional | wide | yes | high | high |
| FHA | narrow | no | low | low |
| **VA** | **wide** | **no** | **high, near conventional** | **low, near FHA** |

**The load-bearing comparison is conventional against VA.** FHA supplies the shape
of the gradation and nothing else.

### The pool-width row of that table is an assumption, and it is now tested

The `wide` in the VA row is argued from programme rule above and was not
measured. It carries the whole placebo: if the VA pool is narrow, the pool-width
account predicts `low` there too, the two columns stop disagreeing, and the
comparison identifies nothing. Prediction 3 below removes the *geographic*
composition difference between programmes and says nothing about this one.

**Tested in [`b2_placebo_pool_width.md`](b2_placebo_pool_width.md)**, on the
borrower-capacity fields the retrieval kept, on these same loans. Credit score
itself cannot be used: public HMDA redacts it, and FHFA's NMDB aggregates have no
VA-only market, only `Government / Non-Conventional` with FHA, VA and USDA
pooled, which merges the two arms this comparison needs kept apart.

**Outcome: the premise survives.** On the tail-insensitive measure the VA pool at
fixed position is 97.7% as wide as the conventional pool and wider than the FHA
pool, so the `wide` in the VA row stands and the conventional-VA gap is not a
pool artefact. Two qualifications belong here rather than in a footnote. The
result is about borrower **capacity** and not credit score, because no public
source carries a score while separating VA from FHA. And the same run puts a
number on the concession this section already makes about FHA: per unit of pool
width, FHA shows *more* rate dispersion than conventional, so FHA's low within
share is substantially its narrow pool and not its flat grid, exactly as the
paragraph above says it would be.

### Pre-registered predictions

Computed at `min_size = 20` with the plausibility band and the ranked analogue,
exactly as in section 10.3.

1. `within_share(conventional) - within_share(VA) > 0.05`, with the same sign in
   the ranked decomposition.
2. `within_share(conventional) > within_share(FHA)`.
3. Both hold when all three samples are restricted to tract-years present in all
   three, which removes the geographic composition difference: VA lending
   concentrates near installations and FHA in lower-income tracts, and neither
   should be allowed to stand in for the mechanism.
4. FHA against VA is **not** predicted in either direction. Whatever it comes out
   as is reported and not interpreted.

### The null calibration

A gap of 0.05 means nothing without knowing what a gap of zero looks like at this
sample size. So the conventional sample is split at random into halves and the
same difference computed between them. That difference has a true value of exactly
zero by construction, and its observed magnitude is the scale below which the
conventional-VA gap is indistinguishable from noise. Twenty splits, and the
reported figure is the largest absolute gap among them.

If the conventional-VA gap does not clear that, prediction 1 fails.

---

## 9. What this measurement does not establish

It does not show anyone behaves badly, that markets fail to clear, or that a
planner would allocate better. It shows whether a single scalar on positions can
reproduce the terms different holders face. That is a statement about
representations, and it is the only statement being made.

It also does not, on its own, support the universal non-existence claim of B1. It
supplies the field that claim is about and a measurement of how far from integrable
that field is. The theorem is separate and does not rest on this.

---

## 10. Changes after pre-registration

Everything here happened after this document was first written and is listed so a
reader reproducing the work can tell which figures came from which specification.
Nothing below was made after a loop sum was inspected except where noted, and the
one exception is marked.

| what changed | when | why | effect on the result |
|---|---|---|---|
| geography: 50 largest CBSAs to all states | before any retrieval | divided CBSAs return zero rows under their CBSA code, and metro was never a cell key | enlarges the sample; removes a selection rather than adding one |
| API filters cut from five to two | before any retrieval | five together return HTTP 400 while each works alone | none. The other three are applied locally in `keep_row` and the exclusion counts are in the manifest |
| `action_taken == 1` moved from API to local filter | before any retrieval | purchased loans report no rate spread; the first sample was almost entirely those | none in principle, decisive in practice: without it the field is unobservable |
| `derived_msa_md` corrected to `derived_msa-md` | before any retrieval | underscore does not match the returned header, so the column was silently absent | none. No downstream use, but a silently missing column is the failure mode that becomes a wrong number later |
| loop A window fixed at 2018 onward | before any retrieval | the API serves 2018-2025, and pre-2018 HMDA reported rate spread only for higher-priced loans | restricts loop A. The longer vintage range still applies to loop B |
| `variance_decomposition` and `cell_dispersion` vectorised | before any result was read | the per-cell implementation is quadratic and does not complete on twenty million rows | none. Verified against the naive version to 1e-12 on small samples |
| **`min_size` added to `variance_decomposition`, reported alongside the unrestricted figure** | **after the first result was read** | a cell of one has zero within-cell variance by construction, so sparse cells bias the share toward the integrable null | **raises the reported share.** Both figures are reported; the unrestricted one is the conservative bound and is the one to quote when a single number is wanted |
| **plausibility band `SPREAD_BOUND`, plus `bound_sensitivity` and `rank_decomposition`** | **after the first result was read** | 115 of 20,071,900 reported spreads are filer placeholders rather than interest-rate differences, and four of them carried essentially the entire sample variance | **invalidates the first reported shares and replaces them.** See below |

Two rows are flagged as post-result. The second one invalidated the first
published numbers, so it is set out in full.

### 10.1 The 0.975 artifact

The first run reported a within share of `0.9750000458` overall,
`0.9750000484` on principal residences and `0.9749976781` on principal residences
unrestricted. Three subsamples differing by hundreds of thousands of cells agreed
to six decimal places, at a round number. That is the signature of an artifact, and
it was one.

`0.975` is `39/40`, and it was literally that fraction. One row reported a rate
spread of `-9999997`, and that row sat in a cell holding forty loans.

An isolated value `M` in a cell of size `k`, with `M` far larger than everything
else in the sample, contributes

```
within   =  M^2 (k-1) / (n k)
between  =  M^2 / (n k)
```

so the share it forces is `(k-1)/k`, with `M` cancelling out entirely. The size of
the bad value is irrelevant; only the size of the cell it landed in shows up in the
answer.

The arithmetic closes to six significant figures. At `min_size = 20`,
`M^2/n` predicts a total variance of `6,181,523.5` against `6,181,526.7` observed.
The residual is `3.1`, which is the twenty million real loans plus the smaller
placeholders that also survived the cutoff. The real restricted total, once the
band is applied, is `0.397`. On the unrestricted sample the observed total divided
by `M^2/n` is `4.000020`, which counts the rows of that magnitude exactly.

The `min_size = 50` row of `scripts/diagnose_b2.py` is where this was visible
without the algebra: the `k = 40` cell drops out at that cutoff and the total
variance falls from `6,181,527` to `3.7`.

### 10.2 What the bad values are

160 rows lie outside `+-20` and 115 outside `+-50`, in a sample of 20,071,900.
They are filer placeholders, not a parsing fault. One
filer writes `1111` into rate spread, interest rate and loan term together. Others
write `99.99`, `100.0` or `123.0` as a ceiling sentinel. A few report an otherwise
ordinary loan, interest rate `3.49` and term `180`, with a single impossible spread
of `-968`. Different filers, different conventions, no common mechanism.

### 10.3 Why the band is not tuned

The band is argued from what the quantity is. Rate spread is the loan's APR minus
the average prime offer rate for a comparable transaction. Both are annual
percentage rates on a first-lien purchase mortgage. APOR has not exceeded nine
points in the series' history, so a spread below `-20` implies a negative APR and a
spread above `+20` implies an APR more than twenty points over prime, above every
state usury ceiling for this product. Nothing in that argument refers to the
result, and it could have been written before any retrieval. It was not, which is
why this row is flagged.

Two things make the number itself non-load-bearing.

`bound_sensitivity` recomputes the decomposition at bands of 10, 15, 20, 25, 30 and
50. Criterion **B2A-6** fails if the resulting shares span more than 0.05, and the
pre-registered falsification `bound_choice_drives_result` fires with it. If the
band were producing the answer, this is where it would show.

`rank_decomposition` computes the same decomposition on tie-averaged ranks of the
**raw sample, before any exclusion, including all 115 rows**. A rank is bounded by
the sample size however large the value is, so the placeholders can move it by at
most `115/20,071,900`. Ties are what make this a test of the same hypothesis:
under the integrable null every loan in a cell reports the same spread, tied values
receive identical ranks, and the within-cell rank variance is exactly zero. The
null survives the transform. Criterion **B2A-7** reports it, and the falsification
`vanishes_under_ranking` fires if it collapses.

### 10.4 What survived and what did not

Dead: every variance-based share in the first run. `0.6813` and `0.9750` are the
arithmetic of four rows. They are superseded by `0.7831` unrestricted and `0.8480`
restricted, on a total variance of `0.439` rather than `19,928,446`.

The correction did not run in the convenient direction and is worth reading twice
for that reason. Under the artifact the restricted share exceeded the unrestricted
one by 0.29 and both sat near a ceiling. Cleaned, the two are `0.7831` and
`0.8480`, the gap is 0.065, and the level is somewhere a real quantity can live.
The corrected figures are lower and they are the ones that mean something.

Alive, and untouched by any of this: the dispersion statistics. Median within-cell
IQR `0.5257` points, median `p90-p10` `1.0774` points, `98.9%` of cells with IQR
above 25bp. Medians and quantiles are unaffected by 115 rows in twenty million, so
criterion **B2A-3** stood before the fix and stands after it. It is also sufficient
on its own: a gradient field predicts every one of those cells at exactly zero.

The general lesson is worth stating because it is going to recur in loops B and
onward. Variance is not a robust statistic under heavy-tailed contamination, and a
decomposition of variance inherits that. Any future carrier gets the band sweep and
the ranked analogue as standard, not as a repair.

### Reproducing a specific figure

`results/b2_loop_a.json` records `min_cell_size`, `spread_bound`,
`excluded_implausible`, the full `bound_sweep`, and `rank_decomposition` alongside
`variance` and `variance_restricted`. Both knobs are overridable, and passing
`inf` reproduces the pre-fix behaviour exactly, artifact included:

```bash
python experiments/b2_loop_a.py --min-cell-size 30
python experiments/b2_loop_a.py --spread-bound 10
python experiments/b2_loop_a.py --spread-bound inf   # reproduces the 0.975 artifact
```

---

## 11. Order of execution

0. **Loop A before loop B**, because loop A carries the logical claim and loop B
   carries only magnitude. If loop A fails, loop B is not worth running.
1. Retrieve series, record vintages in `data/SOURCES.md`. **No computation.**
   Two faults found at this step are recorded in `data/fetch_hmda.py` rather than
   fixed silently: sending five filters to the API returns HTTP 400 while each
   works alone, so all filtering except two size-reducing ones now happens
   locally; and `action_taken == 1` is not optional, because purchased loans
   report no rate spread and the first sample returned was almost entirely those.
2. Build the panel. Record missing cells and their reasons. **Still no `δ`.**
3. Compute `δ`. Look at the distribution.
4. Run section 6's window test.
5. Run the Hodge decomposition.
6. Write results, including any falsification in section 7 that fired.

Steps 1 and 2 complete before step 3 begins, so that the sample is fixed before
any result is visible.
