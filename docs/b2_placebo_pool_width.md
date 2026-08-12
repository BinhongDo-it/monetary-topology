# B2 placebo, pool width: testing the premise the placebo asserts

**Status.** Design and criteria fixed here before the measurement was run.
Executed by `experiments/b2_placebo_pool_width.py`; results in `RESULTS.md`.

---

## 0. Summary

Stage B2's graded placebo turns on one premise it argues rather than measures.
`docs/b2_measurement.md` §8 says VA eligibility is service-based rather than
credit-based, so the VA pool spans a range comparable to conventional and wider
than FHA, while the VA price grid is flat. **That is an institutional argument
about a programme rule, and the pool it describes was never looked at.**

If the premise is false, the duller rival account reclaims the result. The
observed gap is `within_share(conventional) = 0.8480` against
`within_share(VA) = 0.6666`, and a narrower VA pool would produce that gap with
no agent index anywhere. The load-bearing comparison of the whole placebo is
conventional against VA, so this premise carries the placebo, and the placebo
carries loop A's attribution.

This document fixes what is measured instead, why credit score itself is
unavailable from every public source that keeps VA and FHA apart, and the
criteria.

---

## 1. Credit score is not available, and the obvious substitute is worse

The public HMDA loan-level file **redacts credit score**, recorded already in
`docs/b2_measurement.md` §5. So the premise cannot be tested in the variable it
is stated in.

The natural substitute is FHFA's NMDB aggregate statistics, which do publish
credit-score bands (`AVE_VANTAGESCR`, `PCT_VS_VERYPOOR` through
`PCT_VS_EXCELLENT`). **They cannot answer this question, and the reason is
structural rather than a matter of coverage.** Appendix A of the *NMDB Aggregate
Statistics Data Dictionary and Technical Notes* defines the `MARKET` dimension,
and the only government value in it is `Government / Non-Conventional`, defined
as FHA **plus** VA **plus** USDA RHS. There is no VA-only market and no FHA-only
market. FHA is the narrow arm and VA is the wide arm of the comparison being
validated, so the one available aggregation merges exactly the two things that
have to stay apart.

What is left is the set of borrower fields HMDA does publish, on the same loans:
`income`, `debt_to_income_ratio`, `loan_to_value_ratio`. They are already on
disk; `data/fetch_hmda.py` kept them.

**This measures capacity, not credit.** Nothing below licenses a statement about
credit scores. The claim it can support is narrower and it is the one the
placebo actually needs: that the VA pool at a fixed position is not a narrow
pool.

---

## 2. Which fields can carry this and which cannot

| field | set by programme rule? | role here |
|---|---|---|
| `income` | no rule sets it; the top tail is truncated by loan limits | **primary** |
| `debt_to_income_ratio` | ceilings differ by programme | secondary, contamination signed below |
| `loan_to_value_ratio` | **set almost entirely by rule** | excluded from the pool measure, used as a negative control |

**Why LTV is excluded rather than merely caveated.** VA permits no down payment
and most VA loans sit at 100; FHA's floor is 3.5% down and most FHA loans sit at
96.5; conventional down payments are spread. LTV dispersion for those programmes
therefore measures the down-payment rule and nothing about who the borrower is.
Using it as a pool-width proxy would return "VA and FHA pools are both narrow"
as a mechanical consequence of the rules and would look like a refutation of the
premise while containing no information about it. It is kept as a **negative
control**: the method should detect that rule-pinned concentration, and if it
does not, the method is not measuring dispersion properly.

**Why income is primary.** No programme rule sets borrower income. The one
distortion is at the top: FHA county loan limits are the lowest, conventional in
this sample includes jumbo and has no ceiling, and VA's limit was removed for
full-entitlement borrowers in 2020. **That truncation runs against the premise
being confirmed**, because it inflates conventional's spread relative to both
others, and the premise needs VA to reach conventional. A field whose bias
opposes the result is the right field to lead with.

**Why DTI is secondary, and the direction of its contamination.** FHA and VA
underwrite to higher debt-to-income ceilings than conventional lending does, so
their observed DTI range can be wide for reasons of rule. That inflates FHA's
figure, which is the arm the premise needs to be *narrow*. **So DTI is
informative only when it fails**: `bound(VA) < bound(FHA)` would be evidence
against the premise that survives the contamination, while `bound(VA) >
bound(FHA)` is consistent with the premise and also with the rule difference and
therefore proves little on its own.

---

## 3. Sample and statistic

The sample is the placebo's, so this validates that measurement and not a
neighbouring one:

- the three programme directories, same `VALID_NAME` file convention;
- rows whose `rate_spread` parses and falls inside the plausibility band of
  `effective_price.SPREAD_BOUND`;
- restricted to **tract-years present in all three programmes**, which is
  prediction 3 of `docs/b2_measurement.md` §8 and removes the geographic
  composition difference between programmes;
- cells are `effective_price.CELL_KEYS`, minimum size 20, as in the headline.

### The statistic is the within-cell dispersion, absolute rather than a share

Loop A reports a within *share* because its question is whether a position-only
potential can reproduce a price field, and that question is inherently a ratio.
**Pool width is not that question.** "How spread out are the borrowers
transacting at this position" is the within-cell dispersion in the units of the
attribute. Dividing it by a total that also contains between-cell variance would
let a programme whose borrowers sort strongly across tracts read as narrow at
fixed position when it is not, and a programme whose attribute is pinned
everywhere read as wide because its between-cell variance is pinned too. Shares
are reported alongside for continuity with loop A and are not what the criteria
read.

### Two income measures, because one of them has a known weakness

Log income here is right-tailed, and the tail is programme-specific by rule:
conventional in this sample includes jumbo and has no ceiling, FHA has the lowest
county loan limits, VA's limit was removed for full-entitlement borrowers in
2020. A variance in log income therefore hands conventional a tail no government
programme is allowed to have. §2 signs that bias as running against the premise,
which is the right direction for a nuisance, but a variance is dominated by its
tail and signing it is not the same as removing it.

So the same dispersion is computed a second time on the **within-programme rank**
of income, the device loop A already uses for its ranked analogue. Ranks are
bounded, so no tail can dominate, and each programme is ranked against its own
distribution, so a level difference cannot enter either. Ranks are built from an
exact histogram of the reported values rather than a sample, since HMDA publishes
income rounded to thousands and the distinct values number in the thousands.

**The criteria require the conclusion on both measures.** If they disagree, that
is reported as a disagreement and the reason is the one named here.

### Debt-to-income is a bound, not an estimate

The column is a mixture of point values on `[36, 50)` and bands elsewhere, so the
statistic is the loan-weighted mean of the per-cell variance **lower bound** of
`binned_dispersion`, applied per cell instead of per quarter. No within-bucket
shape has to be assumed and the error runs one way. Integer values are widened to
`[v, v+1)`, which can only shrink the gaps and therefore only lower the bound.

### One sample for every figure in a comparison

Because everything is restricted to common tract-years, **the rate-spread figures
recomputed here will not equal the placebo's headline**, which is unrestricted.
The restricted figures are the ones the criteria use, so every quantity in a
comparison comes off one sample.

The minimum-size threshold selects each programme's *dense* cells, and the three
programmes are dense in different places. VA lending concentrates near
installations, where pay scales compress incomes, so the threshold plausibly
narrows VA's measured pool. Every quantity is therefore folded at 5, 20 and 50 in
the same pass and PW-7 requires the verdict to survive all three.

---

## 4. Pre-registered criteria

Fixed before any national figure existed. Two of them were restated against
subset smoke runs, before that: PW-6 was written on the within *share* of LTV,
which cannot detect a rule-pinned variable at all because such a variable is
pinned between cells as well as within them, and PW-7 was written on the ordering
of all three programmes rather than on the verdict the design actually asserts.
Both were the wrong object for the question and neither produced a figure, so
they are corrected here rather than carried as results.

Write `d(x, p)` for the within-cell dispersion of field `x` in programme `p`.

**PW-0. Every programme has surviving cells at the headline threshold.**
A programme with no cell of at least the minimum size reports a dispersion of
exactly zero, and zero here means "nothing to measure" while every criterion
below reads it as "this pool has no width". Those are opposite conclusions and
the number does not distinguish them, so the count is checked first. **A failure
voids everything below it**, and it is what a state-level subset run will fail on
for VA.

**PW-1. The VA pool is wider than the FHA pool.**
`d(income, VA) > d(income, FHA)` on **both** the log and the ranked measure.
This is the premise's minimum content. If it fails, the VA arm is not a wide pool
with a flat grid, it is a second narrow pool, and the placebo has one arm.

**PW-2. The VA pool is comparable to the conventional pool.**
`d(income, VA) / d(income, conventional) ≥ 0.80` on both measures. "Comparable"
needs a number fixed in advance and 0.80 is it. The truncation of §2 biases the
log ratio down and cannot touch the ranked one.

**PW-3. Conventional converts pool width into rate dispersion at a higher rate
than the flat-grid programmes do.**
With `r(p) = d(rate spread, p) / d(ranked income, p)`, require
`r(conventional) > r(VA)` and `r(conventional) > r(FHA)`. The ranked measure is
used here because a ratio whose denominator is tail-driven is a statement about
the tail.

This is the criterion that discriminates the two accounts rather than merely
describing the pools. A pure pool-width account says rate dispersion at fixed
position is a function of pool width alone, so `r` is a constant across
programmes and this fails. The agent-index account says the credit-graded grid
converts a given pool into more rate dispersion than a flat grid does, so `r` is
larger where the grid is graded, and this passes.

**PW-4. DTI does not contradict the premise.**
`bound(VA) ≥ bound(FHA)`. Read as stated in §2: a pass is weak evidence and a
failure is strong evidence against.

**PW-5. The three samples are comparable at all.**
Every programme's share of rows dropped for an unusable `income` and for an
unusable `debt_to_income_ratio` is within 0.10 of the mean rate across the three.
Differential missingness would mean PW-1 through PW-4 compare different
populations, so **a failure here voids them** rather than standing beside them.

**PW-6. Negative control on LTV.**
`d(LTV, conventional) > d(LTV, VA)` and `d(LTV, conventional) > d(LTV, FHA)`.
This is a check on the instrument, not on the pool: the down-payment rules pin
LTV for both government programmes, so a method that cannot see that
concentration is not measuring what it claims and PW-1 through PW-4 should not
be believed either.

**PW-7. The minimum-size threshold is not carrying the verdict.**
PW-1 and PW-2 together give one verdict per measure per threshold. Require the
same verdict at 5, 20 and 50 on both measures. The threshold selects each
programme's dense cells and the programmes are dense in different places, so a
verdict that moves with it is a statement about density rather than about pools.

**PW-8. The plausibility band is not carrying the verdict.**
Added with the bands of §6. PW-1 and PW-2 on log income give one verdict per
income band; require the same verdict at every band, including no band at all.
The exclusion counts are reported in the same line, so a reader can see both what
the band removes and whether removing it changes anything.

---

## 5. What a failure would mean for stage B2

**PW-1 or PW-2 fails.** The premise of `docs/b2_measurement.md` §8 is false as
stated. The conventional-VA gap is then not attributable to grid flatness and
the graded placebo is withdrawn as an identification argument, leaving loop A's
within share as a measurement of dispersion whose carrier is unattributed. Loop
A itself is unaffected; §9 of that document already says attribution is a
separate and weaker claim.

**PW-3 fails.** The pool-width account survives with the premise intact, which
is the more interesting failure: the pools differ in width by about as much as
the rates differ in dispersion, and the grid is doing no visible work. Same
consequence for the placebo.

**PW-5 fails.** Nothing is concluded and the design has to be redone on the
intersection where all three programmes report the field.

**PW-6 fails.** The instrument is wrong and no other criterion in this document
is evidence about anything.

---

## 6. Changes after the design was written

**Plausibility bands on income and loan-to-value, added after the first national
run.** Recorded here in full rather than presented as if they had always been
there, on the precedent of `docs/b2_measurement.md` §10.

What went wrong. The first national run reported a within-cell dispersion of
loan-to-value of **91,970,479** for conventional against 11,412 for VA. A ratio
of loan to value has no such number in it. Sampling the published columns finds
rows at 89,759 and 993,446 against a 99.99th percentile of about 130, so a
handful of rows carrying something that is not a percentage were setting a
headline. Income has the same shape: a maximum of 2,302,773, which in HMDA's
thousands is an annual income of 2.3 billion dollars.

This is the same failure as the rate spread of `-9999997` that produced a within
share of exactly `39/40`, and the remedy is the one that worked then. Values
above `150` are not loan-to-value ratios and values above `10,000` are not annual
incomes in thousands. Both bands are swept, `(110, 150, none)` and
`(1000, 10000, none)`, every figure is folded at every band in the same pass, and
**PW-8 requires the verdict to survive the choice**. The exact numbers are
therefore not load-bearing, which is the only claim a band of this kind can make.

The ranked measure was already immune, since a rank does not care how far out an
outlier sits, and that is a further reason for it to be the measure PW-3 reads.

**PW-0, added after a subset run.** A programme with no surviving cell reports a
dispersion of exactly zero, which every other criterion reads as a pool of zero
width. That is the opposite of what it means. Registered as its own check rather
than left as a caveat.

**PW-6 and PW-7 restated before any figure existed**, as recorded at the head of
§4: PW-6 was written on a within share, which cannot see a rule-pinned variable
because such a variable is pinned between cells as well as within them, and PW-7
was written on an ordering the design never asserts.

---

## 7. What the run found

Six of nine criteria pass on 23.6 million loans across 409,181 tract-years common
to all three programmes. **The premise holds on the measure built to be immune to
the contaminant this design named in advance, and fails on the measure that
contaminant attacks.** That split is stable across every threshold and every
band, so it is a property of the two measures and not of the sample.

| | conventional | VA | FHA | VA / conventional |
|---|---|---|---|---|
| ranked income | 0.05396 | 0.05271 | 0.04887 | **0.9769** |
| log income | 0.27483 | 0.14545 | 0.13994 | 0.5292 |
| LTV, negative control | 226.009 | 84.795 | 26.428 | |

**PW-1 passes on both measures.** The VA pool is wider than the FHA pool however
it is measured, so the VA arm is not a second narrow pool and the placebo has two
arms.

**PW-2 fails, and it fails only through the log arm.** On ranks the VA pool is
97.7% as wide as the conventional pool at fixed position, comfortably above the
registered floor of 0.80. On logs it is 52.9%, and the whole of that difference
is conventional's upper tail: §2 signed that bias in advance, §6 removed the part
of it that was a data error, and PW-8 shows the verdict does not move when the
band moves. What is left is jumbo lending, which is a real feature of the
conventional sample and a thing no government programme is allowed to have.

**PW-7 reports the same split rather than a fragility.** The log verdict fails at
5, 20 and 50; the ranked verdict holds at 5, 20 and 50. The threshold is not
carrying anything.

**PW-3 fails only on its FHA leg.** The load-bearing comparison passes:
conventional converts a unit of pool width into 6.336 units of rate dispersion
against VA's 5.168, which is the graded grid doing visible work. FHA comes out at
7.445, above conventional. That is not a new problem: `docs/b2_measurement.md` §8
already states that FHA alone discriminates nothing because the pool-width and
agent-index accounts predict the same sign there, and this is the quantitative
form of that concession. FHA's low within share is substantially its narrow pool.

**PW-6, the negative control, behaves.** Conventional's LTV dispersion is 2.7
times VA's and 8.6 times FHA's, which is the down-payment rules being visible to
the instrument.

### The conclusion, stated at the width it is entitled to

The pool-width premise of `docs/b2_measurement.md` §8 **survives** for the
comparison it carries. The VA pool at fixed position is within 3% of the
conventional pool on the measure that is not contaminated by loan limits, and it
is wider than the FHA pool on every measure tried. The conventional-VA gap in
rate dispersion is therefore not attributable to a narrower VA pool, and the
graded placebo keeps its identifying power.

This is a statement about borrower **capacity**, not credit score. §1 is why no
public source can make it about credit score while keeping VA and FHA apart, and
§8 is what would still be needed.

---

## 8. What this does not establish

It does not test the premise in credit score, and no public source that
separates VA from FHA carries credit score at loan level. Ginnie Mae's
pool-level disclosures do identify programme and do carry score bands, which
makes them the candidate for a future check; they are registered as a candidate
in `PROJECT_PLAN.md` §12.12 and not promised here.

It does not establish that income, DTI and credit score move together. If a
reader holds that VA borrowers have conventional-like incomes and FHA-like
credit scores, this document does not refute them; it establishes that the pool
is not narrow in capacity, and says so in those words.

It changes nothing about loop A's headline figures, which are a measurement of
dispersion and do not depend on any placebo.
