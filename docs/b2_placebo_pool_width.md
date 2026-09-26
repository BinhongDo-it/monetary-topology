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
transacting at this position" is the absolute within-cell term. Dividing it by a
total that also contains between-cell variance would let a programme whose
borrowers sort strongly across tracts read as narrow at fixed position when it is
not, and a programme whose attribute is pinned everywhere read as wide because
its between-cell variance is pinned too. Shares are reported alongside for
continuity with loop A and are not what the criteria read.

**`d(x, p)` is a variance, and every ratio below is a ratio of variances.** The
fold is `within = Σ n_c·var_c / N`, the within term of the law of total variance,
which is the numerator of the share the paragraph above declines to use. The
distinction earns its sentence rather than being pedantry: a ratio of variances
is the square of a ratio of standard deviations, and PW-2's floor is close enough
to the reading that the two fall on opposite sides of it. **The floor sits on the
variance**, and the run prints both numbers on the same line, so the choice is
visible rather than available.

### Three income measures, and which one the criteria read

Log income here is right-tailed, and the tail is programme-specific by rule:
conventional in this sample includes jumbo and has no ceiling, FHA has the lowest
county loan limits, VA's limit was removed for full-entitlement borrowers in
2020. A variance in log income therefore hands conventional a tail no government
programme is allowed to have. §2 signs that bias as running against the premise,
which is the right direction for a nuisance, but a variance is dominated by its
tail and signing it is not the same as removing it.

So the same dispersion is computed a second time on the **within-programme rank**
of income, the device loop A already uses for its ranked analogue. Ranks are
bounded, so no tail can dominate. Ranks are built from an exact histogram of the
reported values rather than a sample, since HMDA publishes income rounded to
thousands and the distinct values number in the thousands.

Ranking each programme against its own distribution removes the tail and removes
the level difference with it, and that second removal takes one step too many
here. PW-1 through PW-3 compare one programme's pool to another's, and a
within-programme rank cannot carry such a comparison: three borrowers at 50, 100
and 150 and three at 99, 100 and 101 hold the same ranks, so the measure reports
two pools of equal width where the income spread differs by a factor of
twenty-five. The transform is a monotone relabelling of each programme's own
scale, so what comes out of it is a statement about shape.

So the dispersion is computed a third time on a **pooled** ladder. The three
programmes' income histograms are added, one rank is assigned to each income
value, and every loan is placed on that single ladder whatever programme wrote
it. The result is bounded like the within-programme rank, so no tail dominates,
and one scale runs across the three programmes, so a difference in spread
survives it.

**PW-2 and PW-3 read the pooled ladder.** Log income and the within-programme
rank are reported beside it. PW-1 asks only for an ordering and is required on
all three. PW-7 and PW-8 sweep the measures as they always did.

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

**Each criterion carries a kind, and a failure means a different thing in each.**
An `instrument` criterion asks whether this run's reading is usable at all. An
`own_reading` criterion is a reading this station registered, and its failure
withdraws that reading. A `rival` criterion is a point prediction of the
competing account, and it passes when that prediction fails. A count that adds
the three together names nothing, so the run reports them apart.

Write `d(x, p)` for the within-cell **variance** of field `x` in programme `p`,
folded within cells as §3 sets out.

**PW-0. Every programme has surviving cells at the headline threshold.**
A programme with no cell of at least the minimum size reports a dispersion of
exactly zero, and zero here means "nothing to measure" while every criterion
below reads it as "this pool has no width". Those are opposite conclusions and
the number does not distinguish them, so the count is checked first. **A failure
voids everything below it**, and it is what a state-level subset run will fail on
for VA.

**PW-1. The VA pool is wider than the FHA pool.**
`d(income, VA) > d(income, FHA)` on **all three** measures: log income, the
within-programme rank, and the pooled ladder. What is asked here is an ordering
rather than a comparison of widths, so the within-programme rank answers it.
This is the premise's minimum content. If it fails, the VA arm is not a wide pool
with a flat grid, it is a second narrow pool, and the placebo has one arm.

**PW-2. The VA pool is comparable to the conventional pool.**
`d(income, VA) / d(income, conventional) ≥ 0.80` **on the pooled ladder**.
"Comparable" needs a number fixed in advance and 0.80 is it. The log ratio and
the within-programme ratio are printed on the same line and do not enter the
verdict: the truncation of §2 biases the log ratio down, and a ratio of two
within-programme ranks divides one programme's own scale by another's, which is
not a ratio of widths.

**PW-3 is two claims and they are registered as two criteria.** It was written as
one, scored as one, and the one boolean it produced was ours: the rival's half
was described in the detail line and never given a verdict of its own. The two
claims can fail independently, and on this carrier they do, so they are split.

**PW-3a. Rival: rate dispersion at fixed position does not follow pool width.**
`kind = rival`, so it **passes when the rival's prediction fails**. The pool-width
account says rate dispersion at a fixed position is a function of the pool
standing there and of nothing else. Write `d(rate, p) = f(d(income, p))` with one
`f` shared by the three programmes; the account asserts only that `f` increases,
and every increasing `f` preserves order, so the ordering of rate dispersion
across programmes must equal the ordering of pool width. **No functional form is
assumed and no parameter is fitted.** Any pair of programmes holding more pool
and less price contradicts the premise. The premise is written out for this
carrier in [`b2_measurement.md`](b2_measurement.md) §8, whose table assigns high
rate dispersion to the wide pools and low to the narrow one.

The grid cell is **B**: the rival is wrong here and this framework is not, because
it reads a position as carrying different terms for different classes and so
never required the two orderings to agree. Rule 0b scores each account against
reality rather than the two against each other, and B is that cell.

**PW-3b. The graded grid converts a given pool into more rate dispersion than a
flat grid does.**
`kind = own_reading`. With `r(p) = d(rate spread, p) / d(pooled-ladder income,
p)`, require `r(conventional) > r(VA)` and `r(conventional) > r(FHA)`. A ranked
denominator is used because a ratio whose denominator is tail-driven is a
statement about the tail, and the pooled ladder is the ranked measure that keeps
one scale across the three programmes, which is what makes the denominator a
width. The same ratio on log income and on the within-programme rank is printed
beside it. **This is a reading this station registers on top of PW-3a**, stronger
than it and independent of it, and a failure withdraws the reading rather than
the framework.

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
PW-1 and PW-2 together give one verdict per measure per threshold. Require
the same verdict at 5, 20 and 50 **within each measure**, on all three of them.
The threshold selects each programme's dense cells and the programmes are dense
in different places, so a verdict that moves with it is a statement about
density rather than about pools.

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

**PW-3a fails.** The rival's own entailment holds and rate dispersion at fixed
position follows pool width across the three programmes. Nothing is refuted and
the pool-width account stands where it stood, the premise intact.

**PW-3b fails.** One reading this station registers on top of PW-3a does not
hold: the grid is doing no visible work in this ratio, whatever PW-3a says about
the rival. Same consequence for the placebo as PW-1 or PW-2 failing. It withdraws
a reading of this station rather than reaching the framework, which supplies no
mapping from "graded grid" to this particular ratio and never did.

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

Both ranked measures are immune, since a rank does not care how far out an
outlier sits, and that is a further reason for PW-3's denominator to be a ranked
one.

**A pooled income ladder, added 2026-09-12, and PW-2, PW-3 and PW-7 restated on
it.** External review of the code read the within-programme rank correctly: it is
a monotone relabelling of each programme's own income scale, so it reports the
same dispersion for two pools of the same shape however far apart their incomes
sit, and PW-2's ratio and PW-3's denominator were both asking it for a comparison
of widths it cannot make. The remedy is one more fold in the same pass. The three
income histograms are added, one rank is assigned per income value, and every
loan is placed on that single ladder. Bounded like a rank, one scale like a
level, so it answers what PW-2 and PW-3 ask. The within-programme figure is kept
and printed, since PW-1 asks only for an ordering and PW-7 sweeps each measure on
its own.

Corrected in the same pass: PW-7's code pooled every measure and every threshold
into one set and required the set to hold one verdict, which asks whether the
measures agree with each other. §4 registers the comparison **within** each
measure across thresholds. The code now does that. The object was written
correctly and read wrongly, which is the third time on this station that a
criterion's registered object and its wiring came apart, so it is recorded here
rather than repaired silently.

**PW-3 split into PW-3a and PW-3b, and a kind on every criterion, 2026-09-12.**
The pooled ladder made the two orderings readable for the first time, and they
disagree, so the two claims PW-3 had always contained stopped agreeing with each
other. Only ours had ever been scored. They are now two criteria carrying
discipline 11d's `kind`, which is also put on the other eight: a failure of an
`instrument` criterion says this run's reading is unusable, a failure of an
`own_reading` criterion withdraws one reading, and a `rival` criterion passes
when the competing account's prediction fails. The three do not add up into one
number and the run stops reporting them as though they did.

**§5 restated for the split, same date.** Its consequence for PW-3 was written
when PW-3 was one criterion, so it pointed at a name the run no longer produces.
The two consequences are written from what each of PW-3a and PW-3b means and not
from what this run read, and PW-1, PW-2, PW-5 and PW-6's entries are untouched.

**§3's statistic named properly, same date.** §3 called `d(x, p)` "the within-cell
dispersion in the units of the attribute", and the fold is a variance, which is
in squared units. The sentence had been carrying the contrast with loop A's
*share* and nobody had asked it the other question. It is load-bearing here:
PW-2's floor of 0.80 falls on opposite sides of the variance ratio and the
standard-deviation ratio. The variance is what was registered, on two independent
readings of the design's own text: §6 below reports a within-cell dispersion of
loan-to-value of 91,970,479, which is only coherent as a variance, since as a
standard deviation it would need values a hundred times larger than the largest
row the sampling found; and the share §3 declines to use is
`within / (within + between)`, whose numerator is a variance by construction. The
floor stays on the variance and both numbers are now printed together.

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

**RUN: 2026-09-12.** Eight of ten criteria pass on 23.6 million loans across
409,181 tract-years common to all three programmes. The two that do not are PW-2
and PW-3b, and they are failures of two different claims.

| within-cell variance, threshold 20 | conventional | VA | FHA | VA / conv |
|---|---|---|---|---|
| **pooled-ladder rank**, what PW-2 and PW-3 read | 0.05680 | 0.04086 | 0.03519 | **0.7195** |
| log income | 0.27483 | 0.14545 | 0.13994 | 0.5292 |
| within-programme rank, carries no width (§3) | 0.05396 | 0.05271 | 0.04887 | 0.9769 |
| **rate spread** | 0.34185 | 0.27239 | 0.36385 | 0.7968 |
| LTV, negative control | 226.009 | 84.795 | 26.428 | 0.3752 |

### The pools order one way and the prices order the other

```
pool width       conventional > VA > FHA      on both width measures
rate dispersion  FHA > conventional > VA
```

Conventional holds **1.614 times** FHA's pool on the pooled ladder and **1.964
times** on log income, against **0.940 times** its rate dispersion. VA holds 1.161
times FHA's pool against 0.749 times its rate dispersion. Two inversions, the
same two under both width measures.

This is the reading the pooled ladder of §6 was built to make possible and the
measure it replaced could not produce. On the within-programme rank the three
pools read 0.05396, 0.05271 and 0.04887, a span of ten percent, because each
programme was ranked against its own distribution. On one scale they span a
factor of 1.61.

**PW-3a passes, which is to say the pool-width account's prediction fails here.**
That account has rate dispersion at a fixed position as a function of the pool
standing there and of nothing else. Every increasing function preserves order, so
the two orderings had to agree. They do not, and the violation rests on no
functional form, no fitted parameter and no choice between the two width
measures. The grid cell is **B**: this framework reads a position as carrying
different terms for different classes, so it never required the orderings to
agree.

**One part of the failure reaches further than PW-3a scores.**
[`b2_measurement.md`](b2_measurement.md) §8's table puts FHA at `low` under
**both** accounts and treats that agreement as the reason FHA discriminates
nothing. FHA is the highest of the three. A premise the two accounts shared is
false on this sample and neither of them holds anything that produces the reading.
By rule 0b that is the cell where neither account reached reality, which is a line
to open rather than a score to take on either side. It is registered in §8.

### PW-1 passes on all three measures

The VA pool is wider than the FHA pool on the pooled ladder (0.04086 against
0.03519), on log income (0.14545 against 0.13994) and on the within-programme
rank (0.05271 against 0.04887). The VA arm is not a second narrow pool, so the
placebo has two arms. That is the premise's minimum content and it holds.

### PW-2 fails at 0.7195 against a floor of 0.80

At fixed position the VA pool is 72% of the conventional pool as a variance and
85% as a standard deviation. §3 puts the floor on the variance, and the run prints
both numbers on one line, so nothing here turns on picking between them after the
fact. The registered bar is missed by 0.08.

**The 0.9769 this section used to report is withdrawn rather than
reinterpreted.** It is the within-programme rank, which ranks each programme
against its own distribution and so reports the same width for two pools of the
same shape however far apart their incomes sit. §3 sets out why it carries no
comparison of widths at all. The log figure of 0.5292 stands where it always did,
biased down by conventional's jumbo tail as §2 signed in advance, and the pooled
ladder sits between the two because it is bounded like a rank and keeps one scale
like a level.

### PW-3b does not hold, and the reading it registered is withdrawn

Rate dispersion per unit of pooled-ladder pool width runs conventional 6.019, VA
6.666, FHA 10.339. The registered reading was that this ratio is largest where the
grid is graded. It is smallest there, and the ordering is the same on log income
(1.244, 1.873, 2.600).

**That withdraws one reading of this station.** It leaves PW-3a, which is the
weaker claim and holds. It does not reach the framework: the framework has a
position carrying different terms for different classes and supplies no mapping
from "graded grid" to this particular ratio. That mapping was this station's, it
ran through income as a proxy for credit position, and §1 recorded before any
figure existed that credit score is unavailable and that the obvious substitute
is worse. What the run refutes is the ordering read through that proxy. Whether
the proxy's fidelity differs by programme is a further question, this sample
cannot answer it, and §8 says what it would take.

### PW-7 passes, and what it used to report was its own wiring

Each measure holds one verdict across 5, 20 and 50: log income fails at all three,
the within-programme rank holds at all three, the pooled ladder fails at all
three. The threshold is not carrying anything. §4 had always registered the
comparison **within** each measure; the code pooled all measures and all
thresholds into one set and asked whether that set held a single verdict, which
is a question about whether the measures agree with each other. The failure it
reported was its own.

### PW-6, the negative control, behaves

Conventional's LTV variance is 2.7 times VA's and 8.6 times FHA's, which is the
down-payment rules being visible to the instrument. PW-0, PW-4, PW-5 and PW-8
pass, and no number of theirs moved when the pooled ladder was added.

### The conclusion, stated at the width it is entitled to

**The VA pool is wide.** It is wider than FHA's on every measure tried, and at
fixed position it is 72% of the conventional pool by variance and 85% by standard
deviation. It is not a second narrow pool and the placebo has two arms.

**It does not reach "comparable" as this design fixed that word in advance.** The
floor is 0.80, the reading is 0.7195, and the figure that used to clear the floor
does not measure width. §5 registered what follows from a PW-2 failure before any
figure existed, and it follows: the premise of
[`b2_measurement.md`](b2_measurement.md) §8 is false as stated, and **the graded
placebo is withdrawn as an identification argument**, leaving loop A's within
share as a measurement of dispersion whose carrier is unattributed. Loop A itself
is unaffected, as §5 says and as §9 of that document said before this one was
written.

**What the station does establish, it was never given a line to fail on.** Across
the three programmes rate dispersion at fixed position does not follow pool width:
the widest pool carries less price dispersion than the narrowest. An account under
which position alone fixes the schedule has nowhere to put that, under either
width measure and under any increasing function allowed to stand between them.
The two results sit at different strengths and the difference is worth naming: the
0.80 of PW-2 is a convention this design fixed in advance and says so, while the
ordering of PW-3a is an entailment of the rival's own premise with nothing free
in it.

All of this is about borrower **capacity** rather than credit score. §1 is why no
public source can make it about credit score while keeping VA and FHA apart, and
§8 is what would still be needed.

## 8. What this does not establish

It does not test the premise in credit score, and no public source that
separates VA from FHA carries credit score at loan level. Ginnie Mae's
pool-level disclosures do identify programme and do carry score bands, which
makes them the candidate for a future check; they are registered as a candidate
and not promised here.

It does not establish that income, DTI and credit score move together. If a
reader holds that VA borrowers have conventional-like incomes and FHA-like
credit scores, this document does not refute them; it establishes that the pool
is not narrow in capacity, and says so in those words.

It changes nothing about loop A's headline figures, which are a measurement of
dispersion and do not depend on any placebo.

**Registered, open: why FHA carries the largest rate dispersion at fixed position
while holding the narrowest pool.** Both accounts of
[`b2_measurement.md`](b2_measurement.md) §8 put FHA low and neither produces the
reading, so this is a question for a wider account than either and not a score for
one of them. Two candidates are worth separating before any data is bought. One,
the denominator: income is a proxy for credit position and its fidelity may differ
by programme, since two borrowers at one income in one tract-year are plausibly
more alike in credit inside conventional underwriting than inside FHA. Two, the
numerator: an FHA note rate is set by a lender against a programme whose insurance
premium sits outside the rate, so the rate spread may carry dispersion that is not
about the borrower's position at all. **The first is testable with the Ginnie Mae
pool-level score bands already registered above; the second needs a rate-sheet
source this project does not have.** Neither is promised here.
