# Volume II speedrun, Part 2: B7 through B11

**Part 2 of 3.** Part 1 covers B0 through B6, Part 3 covers B12 through B14. These five stations are where the carriers are, and
where most of the retractions are.

Same four fields per entry. Figures quoted exactly as the record carries them; where the record
supersedes itself, the later reading is given and the earlier is named.

> **One correction is delivered by this document.** B10's holonomy ladder was received into B9 on
> 2026-08-17 from a run whose later sections had already voided the comparison. The reading given
> below is the current one, and it is weaker than the one B9's account and stage report currently
> carry. See the note at the end.

---

## B7 — HMDA: how many independent ways does a local market deviate from the national table?

*Empirical. 20,071,900 loans parsed, 16,035,398 after filters, 326,872 cells, 19 published DTI
levels, fill 0.7222.*

**Asked.** Is the cell-by-class interaction in mortgage rate spreads one ordered ladder of borrower
classes, or does it need more than one independent direction?

**Answered.** In two acts. The first estimator read rank 2 and that reading was **withdrawn**. A
second estimator, built after the station closed, recovers rank **two** at about **1.5% of the
first estimator's magnitude**: `λ₁ = 0.02293` with an off-diagonal share of **36.4%** and
`z = +13.32`; `λ₂ = 0.01481` against a second-largest diagonal of `0.00358`, `z = +16.04`. The
economics: `v₁` is a **tilt** (monotone along DTI, sign change between 38 and 39), `v₂` is a
**bend** (both ends against the middle), and the deviation is **multiplicative**,
`γ(c,a) ≈ f(c)·m(a)`. The national table's shape is shared; the amplitude is local. At the lowest
DTI cell, local disagreement is **0.136 against a national gradient spanning 0.1807, which is 75%**.

**Withdrawn, refuted, or undecidable.** This station withdrew more than any other.

- **B7-4, the stage's number, was withdrawn.** Rank 2 turned out to be the diagonal entries of the
  two thinnest classes: `>60%` and `50%-60%` hold **1.18 and 1.37 loans per cell-class entry**
  against 10.00, 9.32, 3.81 and 2.16–2.90 for the rest. `S` is diagonal: largest off-diagonal
  correlation **0.1417** over 171 pairs, off-diagonal magnitudes **4.5%** of the diagonal.
- **B7-13 is what killed it, and it is a measurement rather than an argument.** A constructed field
  with **zero interaction**, differing from a pure additive fit only in drawing each loan's noise at
  its own class's dispersion, reads back rank 2 in **20/20** at both brackets, leading direction
  `>60%` in 20/20. At the **upper** bracket it reproduces **95.0%** of the observed `λ₁` and
  **92.9%** of `λ₂`; at the lower bracket, 0.623× and 0.817×.
- **B7-6 failed, and then the failure itself was voided.** Two grid cuts disagreed (fine 2 against
  coarse 1) and the headline was withdrawn. Then the cause was found: class levels were stored
  alphabetically and read positionally, so the "coarse grid" had put `<20%` in the same class as
  `49`. Nothing caught it because the group count was right, the fill was right, the loan counts
  were right, and every gate passed. Corrected, both grids read 2. The record refuses to enjoy it:
  **it passes and it was never testing anything else**, because both grids keep the same two thin
  classes apart.
- **A benchmark error inside the second estimator**, caught by its own guard. `λ₂` was compared
  against the **largest** diagonal entry, found smaller, and written up as "rank one". Under a
  diagonal matrix the eigenvalues **are** the diagonal entries, so `λ₂`'s benchmark is the **second
  largest**. Drawn properly the verdict is rank two. (In the run where the error was caught the
  figures were `0.01649` against `0.01860` and, corrected, `0.00434` at `z = +18.41`; a subsequent
  code review (`results/b7_crossfold.json`, `seed_null = 20260817`, arm `drop_thinnest_2_balanced`)
  superseded them with the current `0.01481` against `0.00358` at `z = +16.04`. The
  verdict did not move and both runs are kept side by side.)
- Four code defects in the second estimator, one of which was that "same data, two estimators" was
  **false**: the two ran on different entry sets, and the entries left out are exactly the noisiest.

**Caveat that travels.** The class index accounts for **0.3036** of stage B2's within-cell term, so
every rank statement is a fact about that share, and it must be printed next to the rank rather than
in a footnote. Everything the second estimator recovers is a small fraction of the naive `λ₁` of
1.4674, **and the withdrawal stands.** The fraction itself is one of the station's open
inconsistencies: it is written as **1.5%** in one section and **0.5%** in two others, and on the
common mask the two estimators actually share it is **2.5%**, because the naive spectrum runs on
4,485,519 entries and the cross-fold on the 2,969,372 holding two or more loans. Quote the range,
not a point. Public HMDA carries no credit score (27 fields redacted), so any reading is
"one ladder in the coordinates the public file carries", not in the world. Not claimed: causality,
cross-year stability (never measured), or exclusion of the measurement-shift account, which still
clears at `z = +2.32`.

**The strongest single result here** is the one a competing story gets wrong rather than also
predicts: the recovered direction's monotonicity along the **external** DTI scale, after dropping
its largest-loading coordinate by rule, is `|τ| = 0.700` against a null of `0.157 ± 0.077`,
**`z = +7.06`**, while the 19-class control reads `z = −1.17` in the same run. The estimator sees
classes as unordered labels and the null randomises the off-diagonals, so no account that produces
an arbitrary loading can generate an ordering.

---

## B8 — Fannie Mae: does one household's terms depend on the path it walked?

*Empirical. 170,013,011 rows, 2,942,295 loans, six acquisition quarters, 85,308 loops.*

**Asked.** One loan at a fixed position. The states are servicing tiers: `current`, `delinquent`,
`modified`, and (after a correction) `deferred`. `ω` on an edge is the sum over that leg's months of
`log V(t) − log V̂(t)`, where `V` is the present value of the household's remaining contractual
obligation and `V̂` is the **unchanged prior contract carried one month forward**, priced on the
Treasury curve. A month in which nothing contractual happens contributes exactly zero, so the loop
sum contains the events and nothing else. **The loop is zero if and only if the arrears the
delinquency added equal the relief the modification gave, loan by loan.** No accounting identity
forces that and no servicer targets it.

**Answered, criterion by criterion.**

| | outcome | figure |
|---|---|---|
| **B8-0a** construction gate | pass, six cohorts | the target is the closed form, not zero: `corr(ω, closed)` = **+1.0000** on five cohorts |
| **B8-0b** floor | pass | `N = MAD(ω − closed)` = **2.68e-08 to 5.22e-08**, which **equals half a cent over the median balance** |
| **B8-1** signal | necessary condition holds, six cohorts | MAD ratio **2.41e+06 to 6.77e+06**; net of the leg-1 closed form, 0.885 to 1.022 |
| **B8-2** cross-window sign | pass | **29 readable cells, leg 2 positive in all 29**, five windows |
| **B8-3** two paths | **pass, and this is the headline** | `delta/floor` **1.07e+05 to 4.18e+06**, six cohorts same sign; permutation null **0/999**, p = 0.0010, in all six |
| **B8-4a** class ordering | pass on `fico_llpa9` only | six cohorts same direction, sign test **p = 0.0312** |
| **B8-4b** | **not run** | killed by a pre-run gate, below |
| **B8-5** admission | the threshold differs by class; **it is not a hole** | 554 cells, 132 endpoint-stable, 20 significant; FICO direction 12/12, **to be cited as 4/2** |
| **B8-6** two grids | satisfied **by construction** on B8-1/2/3; a real test only on B8-5, where **no adjudication is recorded** | |

**B8-3 in words**, because it is the result that needs no other argument: two realisable routes end
at the same `current` state, one through modification and one through deferral, and they carry
different accumulated `ω` in every one of six cohorts, at five to six orders of magnitude above an
instrument constant. Stratifying by path **enlarges** the gap rather than shrinking it. It needs no
claim about node identity, no causal identification, and no assumption about who chose which route.

**Withdrawn, refuted, or undecidable.** Eight that matter.

- **`§14.5`'s gate criterion, "the clean-cure round trip must return zero to floating-point
  tolerance", is wrong.** The round trip returns a deterministic closed form. The station's own
  earlier work had been asserting exactly that all along, in a different section, and the two
  statements coexisted until someone looking for the noise floor read the wrong one and **mistook a
  deterministic quantity for noise**. Had the gate been enforced as written, the stage would have
  terminated on a real signal.
- **The floor was run four times and each round's conclusion was unknowable before running it.** The
  first read 1,669× to 6,592× too large and moved by 70× on a subsample: it was a tail statistic,
  and the tail was five payoff loans carrying 78% of it. The third round found the floor had been
  **drawn on the wrong population from the start**. The fourth found three defensible population
  choices pushing the ratio through 1.45 → 54.70 → 1,008, which is how the statistic itself came to
  be changed.
- **`§14.3`'s registered prediction that leg 2 is negative is falsified**: 29 of 29 cells positive.
- **The deferral tier was implemented on the wrong column for several rounds.** The tier was argued
  from one field and implemented on another. When corrected, loops went **45,070 → 85,308** and the
  deferral arm **3,055 → 35,659, an 11.7× increase**. The marginal contribution of the wrong field,
  across 170 million rows and six cohorts, is **2**.
- **B8-3 was declared "stuck" and named the station's largest blocker for a full round, on a number
  that was not what it was said to be.** "703,504 deferral rows, payment known 0" is field 63's
  row count, which is the *modification* population. Measured properly, the deferral arm has
  **92.86% full-path coverage**. The blocker did not exist.
- **B8-4 as registered was withdrawn and rebuilt**: dispersion across classes at fixed path is B7's
  dead estimator in a different costume.
- **B8-5's "12/12" must be reported as 4/2.** Only four of the twelve significant FICO cells sit on
  the registered pool bands; the other eight sit on bands that split a registered bucket. Direction
  is still 4/4 consistent, but they rest on **two cohorts**, and three of the four are nested bands.
- **B8-5's stability criterion was changed after the first real run**, because its pass rate
  collapsed monotonically with layer count (2 layers 51.3%, 3 layers 24.4%, 5 layers 4.4%, 9 layers
  **0/80**, 15 layers **0/53**) for two reasons neither of which was the thing the criterion existed
  to catch. Recorded lesson: **a criterion whose pass rate changes with the coarseness of the
  partition is measuring the coarseness.**

**Pre-run gates that stopped work, with the number that stopped each.**

| gate | stopped | number |
|---|---|---|
| C9 on `(class × cohort)` inside the Flex window | **B8-4b, entirely** | eleven grids, min **0 or 1**, against a floor of 20 |
| C9's attachment rule | two grids barred from B8-4 despite clearing the floor | they attach to the **dwelling**, not the borrower |
| `k ≥ 3` | a two-level grid barred from B8-4a | Spearman on two levels can only take ±1 |
| C13 | `V` and `ω` not computed on 1,276 loans | four candidate readings all at **11.6–46.2%** error against 0.0000–0.0004 elsewhere |
| structural | the deferral arm's cross-window comparison | **0** comparable term bands in three of five windows; payment deferral did not exist before COVID, and more years would not create a 2005 deferral triangle |

**Caveat that travels.** GSE conforming loans exclude subprime, jumbo, FHA and VA, so the most
access-constrained households are absent, and the truncation runs **toward the null**. Modification
is endogenous (servicer discretion, programme eligibility), so B8-4 and B8-5 are **association,
never causation**; B8-1 and B8-3 are unaffected, because Corollary 1 needs one realisable loop and
selection cannot un-realise a realised loop. B8-4a and B8-5 point the same way on the same class
index (**lower score, larger loop sum**, and **lower score, higher modification rate given
delinquency**) and the record forbids upgrading the agreement to a mechanism: both share the same
pool selection.

**"More layers live, fewer layers die."** Recorded **three times on three unrelated statistics**: on
B7's rank statistic (a coarsening carries the fine grid's leading direction at 0.15% while another
carries it at 97.9%), on a pure cell count (fifteen levels of one variable pass C9 at min 49, six
levels of the **same variable** fail at min 11), and on the class-ordering statistic (nine FICO
levels carry B8-4a at p = 0.0312, five levels of the same variable do not, p = 0.3750). The record's
gloss: **coarsening is not conservative, it grinds the structure away with everything else.**

---

## B9 — the ETF creation triangle: the cleanest carrier, and its ceiling

*Empirical. 16 funds × 404 trading days, 6,201 fund-days of closing NBBO midpoint.*

**Asked.** On the cleanest available carrier, where all three positions are institutional objects
and there is no grid to choose, is `λ` zero?

**Answered.** No. `λ` = **1.2 to 1.7 basis points**, standing at **1.05 to 5.08 times the
measurement floor** with the main arm at 11/11 when the fee is set to zero, and at **about 1 against
the cost floor**. Two structural readings support it. The **quantisation explanation is falsified**:
tick size spans **15.8×** across twelve US equity funds while `|λ|` spans **1.42×**, and a
measurement floor falls when measurement improves while a cost floor does not. The **hole is
contractual**: creation and redemption run only through a Participant Agreement in units of 50,000
shares, and no price completes that edge. `λ` rises with stress (D1 median +0.076 → +0.121, 10/11)
and the distribution shifts toward discount (0.453 → 0.508, 10/11).

**Withdrawn, refuted, or undecidable.** Three, all the same family: **a quantity placed against the wrong
reference.** The station once treated the measurement floor and the arbitrage cost as one object.
It once set a tolerance **9.3× below the statistic's own noise floor**, which made fifteen cells
break by necessity, and then a mechanism was invented for the breakage. It once derived `π`'s
degeneracy from `b₁ = 1`, when a fee schedule disclosing a cash-creation route makes **`b₁ = 2`**;
the conclusion survived and the derivation did not.

**Every instrument defect is logged with the channel that caught it**, and the pattern is the
finding rather than the tally: **guards written to bite, and criteria registered before the run,
catch nearly all of them; reading the code straight through catches none.** A minority are the
writer's error rather than the instrument's, including one asserted property the instrument never
claimed, written into an instruction handed to another station.

**Caveat that travels.** The fourth link is not closed. `λ` moves with stress, and **every direction
observed is also predicted by ordinary microstructure or arbitrage-capacity accounts.** Three
registered routes to a discriminating prediction were closed, all three by derivation rather than by
a negative measurement: a size gradient where the competing account predicts the same curve; an
LTV threshold that the servicing rulebook fixes before the first loan is read; and an arbitrage
threshold that an indivisible 50,000-share creation unit produces for unrelated reasons. The only
test ever built with an **opposed** registered sign ran, and lost. The window is 404 days because
the disclosure rule requires only the most recent calendar year plus quarters, and that history was
never anyone's obligation to retain.

**On the word "zero".** The mathematical zero (`λ ≡ 0`, a potential exists) and the economic zero
(`|λ|` below the cost of removing it) are different statements measured against different floors.
This carrier has the second and not the first, and better measurement moves **away** from the first,
not toward it. A mathematical zero lives where one leg is **derived** rather than independently
quoted, which this carrier cannot supply.

---

## B10 — Freddie Mac: a second carrier, and the shape of the state graph

*Empirical. 1,362,490 loans, 74,937,616 monthly rows, 28 vintages, 17,875 closed triangles.*

**Asked.** Can a second, independent GSE carrier hold the design B8 registered on Fannie, and does
the observed state graph have room for a slice obstruction at all?

**Answered.** The graph result is the substantive one and it is cheap to state. Of 10,816 possible
ordered state pairs, only **1,496 ever occur: 13.83%. Eighty-six percent of transitions never
happen**, and self-transitions are **97.38%** of all rows. The cycle space is real but small, and it
has a plateau: at support thresholds spanning a twentyfold range the count does not move, so it is
not carried by rare edges. **The hardest line in the station: merge the servicing states back into
`delinquent` and `b₁` reads 0.** The position graph becomes a tree and the slice has nowhere to
live. The two carriers agree: Fannie `108 → 9 → 2 → 0`, Freddie `108 → 10 → 3 → 0`, both differences
of 1 explained by one state that exists only in the Freddie file. Two limits on that sentence: the
Freddie `g3` zero holds at the support threshold of 100 and reads 1 at thresholds 5 and 10, where
that same extra state survives; and the document prints Freddie's `g0m` as **83** in one section and
**108** in another without reconciling them, which is almost certainly a walkable-versus-undirected
distinction the text never states.

**Withdrawn, refuted, or undecidable.** Six, and two are worth naming for outside readers.

- **The first run measured the wrong object entirely.** It computed the directed circuit space
  rather than the cohomology, so a mutual pair counted twice. All v1 results are void and not cited.
  Logged as a named failure mode: generalisation error.
- **A falsifiable criterion literally failed and was voided rather than repaired**, because its
  correct form was a different function; repairing it after seeing the failure would have been
  choosing the shape from the outcome.
- **A servicer explanation was killed by its own placebo.** The candidate instrument produced
  dispersion far above sampling, and then a placebo grouping carrying **no servicing information at
  all** (each loan's first payment month) produced **larger** dispersion in **5 of 5** windows. The
  verdict was written before the run: the reading is void. The record then states the honest
  conclusion, which is weaker than the tempting one: **not "servicing practice does not explain the
  freezes", but "this instrument cannot answer either way".** A second placebo on the calendar was
  larger in only 3 of 5, so the two are not interchangeable.
- **B10 ruled an open question about which column carries the deferral event, and the answer changed
  another station's arm.** The candidate column's rising edge coincides with the modification flag
  in **99.63% to 100%** of cases across six cohorts, so **it is a modification, not a deferral**;
  the correct column's onsets pile into the same three calendar bins independent of vintage. B10
  made the same mis-copy itself first, taking the column out of another station's script where it
  had meant a segmentation boundary rather than a deferral layer.

### B10 §21 — the holonomy ladder, and what it does and does not say

**Asked.** Does a non-zero holonomy reading survive coarsening of the state grid, or is it an
artefact of how the states were cut? This is the single objection B9 named at its own opening and
could not answer on its own carrier.

**Answered, and the answer is weaker than it first appeared.** The instrument checks pass: the
three-way shape-by-path cross-tabulation has **zero off-diagonal**, and the ladder is monotone (a
coarsening can only kill cycles, never create them), though the monotonicity check was written after
reading the first run rather than registered in advance. The measured cycle-class counts, one
vintage, one carrier:

| | `g0m` | `g1` | `g2` | `g3` |
|---|---|---|---|---|
| cycle classes, deferral arm | 503 | 41 | 2 | 0 |
| cycle classes, modification arm | 431 | 25 | 2 | 0 |
| `b₁`, *different aggregation* | 108 | 9 | 2 | 0 |

**The ends agree and the middle does not**, which converts a prohibition asserted elsewhere into a
measurement: the way `b₁` collapses does not tell you how holonomy collapses.

Two qualifications on that table, both from the record. **The two rows are not from the same run.**
The `b₁` ladder pools six cohorts at a support threshold of 100; the cycle-class counts are a single
vintage, and on that vintage alone `g1`'s `b₁` reads **7**, not 9. The station registered that the
class count be printed beside its own grid's `b₁`, and the run's table carries no `b₁` column, so
the side-by-side was never actually printed. And the two zeros in the `g3` column **are a
construction, not a reading**: the station forbids citing them as a result.

**Withdrawn, refuted, or undecidable.** The between-class-over-within-class comparison, which is the part that would
have answered the actual question, **has been withdrawn and currently has no reading.**

- The cross-grid comparison on the deferral arm was voided when the sign of the difference
  **flipped across vintages** (+0.363, −0.034, −0.164, and one vintage exactly zero to the last
  digit). Under the station's own pre-registered reading rule, a sign that flips is noise.
- A five-vintage "all positive" result on the modification arm was retracted because **the paired
  comparison was not paired**: the statistic computed was the difference of medians, and the paired
  form is the median of differences. Under the correct form one vintage reverses (−0.0179 against
  +0.004) and that arm's verdict changes from `all_positive` to `mixed`. One vintage cell flips sign
  outright between the two forms, **−0.164 unpaired against +0.0675 paired**.
- The cell-sign matrix reads **`neither` on both arms**: no row is homogeneous, on 38 cells
  (23 positive, 11 negative, 4 ties) and 51 cells (32, 16, 3).
- One arm's ratio is **void on coverage**: 0.7%, one surviving layer, 27 loops. A later section
  narrowed the diagnosis from "this grid crushes that arm to one class" to "on *this vintage* it
  does", since two other vintages read 54.1% and 78.1%.
- The deepest stratum, where the objection bites hardest, **has no reading at all**: every window
  longer than fourteen months is dropped, 2,971 loops, because the coarse grid cannot assemble two
  classes there.
- **Stratifying by window length was required before any of this could be read**, since on the
  finest grid the class label is close to the window length itself while `ω` is a sum over the
  window. Stratified, ten of twelve cells fall (4.260 → 1.535, 0.558 → 0.223) but **one rises**
  (0.726 → **1.716**), and that reversal killed the reference frame the criterion had been
  registered against.

The station's own verdict: **the registered question has no reading. On this carrier, with this
ruler, the answer is neither "the cut decides" nor "the cut does not decide"; this ruler cannot
measure it.**

**Caveat that travels.** One vintage for the main table and **one carrier for everything**. The
`b₁` transfer function has two carriers; holonomy has one, and that asymmetry must be cited
alongside. Grid coarsening **changes no `ω` value**; it only changes which loops count as the same
loop. And the sample is vintage-equal-weighted, so nothing extrapolates to the population without
re-weighting.

---

## B11 — corporate credit: the second domain, gated

*Availability established, markers measured, the domain's own gate not yet computed.*

**Asked.** Can the mortgage ring be replicated in a second domain, `investment grade → downgrade →
distressed exchange → re-rating`, where the distressed exchange is the counterpart of a mortgage
modification because the contract is re-signed there?

**Answered.** The domain was **not chosen; it was fixed by a branch table registered before B8
ran**, and B8's realised outcome selected this row. Ratings histories are free under an SEC
disclosure rule, **but only from 2012-06-15**, because the earlier rule required only a 10% random
sample with a six-month lag. One agency's distressed-exchange marker is measured and real:
**422 rows across 227 issuers**. A second agency's supposed marker **does not exist** (224 symbols
checked, none of them it). A third agency is absent from the free archive entirely. Price is no
longer the binding constraint, because `V` is re-registered as the present value of the contractual
coupon stream on the Treasury curve, copying B8's definition verbatim: **B8 never read a market
price, start to finish.**

**Withdrawn, refuted, or undecidable.** The availability register's assumption that the marker could only come from
one agency's annual default study by name-matching is superseded and shown redundant: the gate can
be computed inside a single file with zero name matching. Registered as unavailable with reasons:
two European regulatory archives, a public bond-index series, and one vendor's anonymous bulk
download. One vendor's default database costs **£175,000 to £280,000 per year**. Two things are
pre-registered as **not to be claimed**: cross-generation replication, because corporate credit has
no acquisition-generation axis and B8 had six; and widening the ring to "any default", which would
raise the ceiling but only after the ceiling was seen to be small.

**Caveat that travels, and it is a live constraint rather than a footnote.** The domain is
**gated, not open**. The free gate requires **200 issuers** that were investment grade before the
exchange and were re-rated after. **The arithmetic ceiling is already measured at 227**, and the
investment-grade filter can only cut downward, so **the filter must retain 88% for the gate to
clear.** That was registered in advance precisely so that neither outcome is a surprise. Nothing
downstream may be read and no paid data may be bought before it passes. If all free sources fall
short, the station stops and the second domain returns to the branch table.

---

## What Part 2 adds up to

**Three carriers produced measured non-zero cycle sums**, and they are of very different quality.
B8-3 is the strongest single reading in the programme: two realisable routes to the same state carry
different accumulated `ω` in six of six cohorts, five to six orders of magnitude above an instrument
constant that a zero-parameter prediction reproduces to within 15%, with a permutation null
returning 0 of 999 in all six. B7's surviving reading is real and **1.5% of the number the station
originally reported**. B9's is distinguishable and small, and its own record forbids reporting it as
a zero.

**Two stations exist mainly to say what cannot be concluded.** B10's ladder answers the sharpest
objection in the programme with "this ruler cannot measure it", after retracting a comparison that
had appeared to answer it. B11 is gated at 200 against a measured ceiling of 227.

**The retraction column is the load-bearing one.** B7 withdrew its headline on a constructed
counterexample rather than on an argument. B8 discovered that a gate written as "must return zero"
would have terminated the stage on a real signal, and that a blocker it had carried for a full round
rested on a row count of the wrong population. B10 killed its own servicer result with a placebo
that beat it in five windows of five. B9 logs each instrument defect with the channel that caught it, and no
channel that reads code catches any of them.

**What none of them has yet.** No station has produced a prediction that a competing account gets
**wrong**, as opposed to one that a competing account also gets right. Every registered route to
one has so far closed by derivation. The single test ever built with an opposed sign ran, and lost.
That is the open problem, and it is stated here rather than left for a reader to notice.

> **This paragraph is answered in part by a station written after it.** B13 delivered the
> programme's first zero domain, and the discriminating part of it is not the zero but the **sort**:
> the same apparatus returns exact zero on the member of a family whose edge is derived and non-zero
> on the member whose edge is quoted, with the framework naming which in advance. An account that
> calls `ω` noise, or a spread artefact, gets that sort wrong. The account that gets it right is the
> framework's own mechanism in the exchange's vocabulary. **It is short of the thing this paragraph
> asks for and it is closer than "none".** See [Part 3](volume-ii-part-3.md), and note that B13's own
> record is what forbids calling it the answer.
