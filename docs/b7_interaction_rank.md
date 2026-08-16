# B7: is there one ladder or several? The rank of the interaction

Pre-registration. **Written before anything below was computed.** Every class
index, filter, estimator, null and criterion is fixed here.

Companion to [`b1_theorem.md`](b1_theorem.md) §13, which supplies the object, and
[`b2_measurement.md`](b2_measurement.md), whose sample, cells and bounds this
stage inherits by reference rather than re-deriving.

**Status, added 2026-08-15.** §§1 to 9 are the pre-registration and are what was
fixed before anything ran, except where a subsection carries its own date and says
what it adds. **§10 is the result.** A reader who wants the outcome should read §10
and nothing else; the dated subsections of §3 are the amendment trail and §10.7
indexes them. **The stage is complete except for B7-7 and B7-8, which are
registered in §6 and have never been run** (§10.8).

**A naming collision, flagged once so it does not recur.** "Rank" appears in this
repository in two unrelated senses. Stage B2 reports a **rank-transformed** arm,
meaning spreads replaced by their within-date ranks. This stage is about
**matrix rank**, the number of independent directions in a two-way interaction.
Where confusion is possible the words are written out in full.

---

## 1. What this stage is for, in one sentence

`b1_theorem.md` Corollary 4 says the interaction term `γ_ag` is non-zero, and
stage B2 measured its magnitude. **Corollary 4 says nothing about its shape.**
This stage asks whether `γ` is one-dimensional, so that a single scalar per
borrower class and a single scalar per cell reproduce it, or whether it needs
more.

The two answers are different economics and both are already named in the
literature this project has to live beside.

| matrix rank of `γ` | what the economy looks like |
|---|---|
| **1** | **one ladder.** Borrower classes are ordered, cells differ only in how steeply that one order is priced. This is the shape of every standard stratification model: one credit score, one income rank, one risk index, scaled by a market |
| **≥ 2** | **no single ladder.** A class that is disadvantaged in one cell is not the disadvantaged class in another, and no one scalar per class can express the pattern |

**The second answer is the one no one-dimensional model can produce**, and by
`b1_theorem.md` §13.4 the mortgage carrier's square summand is otherwise within
reach of a saturated two-way specification. So this stage is the test of whether
the mortgage carrier has any content that standard practice does not already
have. **It may well come back saying no**, and §7 declares that reading in
advance.

---

## 2. The class index, which is the binding constraint

Stage B2's cells are deliberately built from **loan and property attributes
only**. `effective_price.CELL_KEYS` carries the comment "Everything here is a
property of the loan or the property, never of the borrower", and that is what
makes the within-cell dispersion attributable to the agent index at all. The
consequence for this stage is that **B2 has no labelled agent class**: within a
cell every loan is a different agent and the classes are anonymous.

A matrix rank needs labelled columns. So this stage must introduce a class index,
and introducing one is the only place where researcher choice could enter. It is
therefore fixed here, with its source.

### 2.1 What the retrieved file actually carries

`data/fetch_hmda.py` retrieves twenty columns. Recorded verbatim, because
`PROJECT_PLAN.md` §11.4 counts four separate errors in this repository from
assuming a schema:

```
activity_year, derived_msa-md, state_code, county_code, census_tract,
occupancy_type, lien_status, loan_purpose, derived_loan_product_type,
derived_dwelling_category, action_taken, rate_spread, interest_rate,
loan_term, loan_to_value_ratio, debt_to_income_ratio, discount_points,
total_loan_costs, income, applicant_credit_score_type
```

Seven of these are cell keys. Of the rest, three are borrower attributes rather
than loan or property attributes: **`debt_to_income_ratio`**,
**`loan_to_value_ratio`**, **`income`**.

`applicant_credit_score_type` is **not** a borrower attribute and is not used as
one. It records which scoring model the lender pulled, so it is a property of the
lender's vendor relationship. Naming it here so that nobody later mistakes it for
a credit score: **the public file does not contain a credit score**, which
`b2_measurement.md` §2 already states and which §8 of this document returns to,
because it bounds what a negative result can mean.

### 2.2 The primary class index has no free parameter

**`debt_to_income_ratio`, as published, one level per distinct published value.**

The regulator has already coarsened this field, and coarsened it unevenly: values
below 36 and above 49 arrive as buckets (`<20%`, `20%-<30%`, `30%-<36%`,
`50%-60%`, `>60%`), while 36 through 49 arrive as integers. **We adopt that
partition exactly and add nothing.** Every level is one distinct string the
regulator chose to publish, so the class index contains no band boundary selected
by this project.

That is roughly nineteen levels, which bounds the matrix rank at eighteen and is
far more than the trichotomy in §5 needs.

`NA`, empty and missing values form no level. They are dropped, and the dropped
count is reported per arm.

### 2.3 The secondary class index, and where its boundaries come from

**`debt_to_income_ratio` crossed with `loan_to_value_ratio` banded on the
published GSE loan-level price adjustment grid.**

LTV arrives as a number, so any banding is a choice, and the choice is removed by
taking it from outside: the LTV breakpoints are **transcribed at implementation
from the GSE LLPA matrix in force in the sample's first year, recorded verbatim
in the results, and no boundary is set by this project.** That grid is the
lender's own pricing partition, so it is the partition under which a rank-one
answer would be least surprising, which makes it the harder arm for the `≥ 2`
reading and the right place to put it.

`income` is available and is **not** used as a class index in any registered arm,
because every banding of it would be ours. It is left for a later stage.

### 2.4 Why these are agent attributes and not positions

`b1_theorem.md` §8 A3 requires that a cell be one edge: if the class index is
secretly a position, the interaction inflates for a reason that has nothing to do
with the agent. DTI is the ratio of the borrower's obligations to the borrower's
income and moves with neither the dwelling nor the tract. LTV is jointly
determined by the loan and the property value, so it is the weaker of the two on
this test, which is the second reason it is the secondary arm and not the
primary.

---

## 3. The estimator

### 3.1 The object

For cell `c` and class `a`, let `m(c, a)` be the mean rate spread over loans in
that cell and class. Write

```
m(c, a)  =  φ(c)  +  A(a)  +  γ(c, a)  +  noise
```

`γ` is the interaction of `b1_theorem.md` Corollary 4 and this stage estimates
its **matrix rank**.

### 3.2 The design is incomplete, and the estimator is built for that

Not every class appears in every cell, and with nineteen classes against a
minimum cell size of twenty, **a complete block does not exist and no arm of this
stage waits for one.** Restricting to complete blocks would select cells on the
diversity of their borrowers, which is a selection on the object being measured.

So the rank is taken from a **pairwise-complete class second-moment matrix**,
which is estimable without imputation:

1. **Alternating centring.** Remove the cell effect, then the class effect, then
   iterate. On an incomplete design the two centrings do not commute, so the
   iteration runs to a fixed point and both the iteration count and the residual
   are reported rather than assumed negligible.
2. **The class second-moment matrix.**
   ```
   S(a, b)  =  mean over cells holding both a and b  of  γ̂(c,a) · γ̂(c,b)
   ```
   Cells are dropped pairwise and the dropped count is reported per arm. This is
   `b3_cip_slice.md` §7's rule, adopted verbatim: silence about a dropped cell is
   how a sample becomes a selection.
3. **The rank estimate** is the number of eigenvalues of `S` exceeding the null
   of §4.

**Pairwise-complete second-moment matrices need not be positive semidefinite.**
The negative eigenvalues are reported with the positive ones. Their magnitude is
the diagnostic on how much work the missingness pattern is doing, and if the
largest negative eigenvalue exceeds the null of §4 in absolute value, §7 says
what happens.

### 3.3 What the estimator inherits and does not re-choose

| inherited from | what |
|---|---|
| `b2_measurement.md` §5 | the sample: states, years, action taken, purpose |
| `effective_price.CELL_KEYS` | the seven cell keys, unaltered |
| `effective_price.MIN_CELL_SIZE` | twenty loans per cell |
| `effective_price.SPREAD_BOUND` and `BOUND_SWEEP` | the `±20` band and the sweep it must survive |
| `b2_measurement.md` §10.3 | the rank-**transformed** arm, run here as well |

Nothing in that list is re-argued here. If a reader disputes any of it the
dispute is with stage B2 and this stage moves with it.

### 3.4 Two specification points, fixed 2026-08-15, before any HMDA row was read

Both were needed to write `src/monetary_topology/interaction_rank.py` and neither
was in §3.2 when §3.2 was written.

1. **The centring is count-weighted.** An entry standing for one loan and an entry
   standing for two hundred are not equally informative, and centring them equally
   is a choice too, and the one that puts the most weight where the least data is.
   The weights are the loan counts behind each cell-class mean.
2. **`S` is a plain mean over co-occurring cells.** That is §3.2's literal wording
   and it is left literal rather than reweighted.

They are specification and not tuning **only because of when they were fixed**,
and the only thing that makes that checkable is that the run had not happened.
`experiments/b7_interaction_rank.py` opens no data file.

### 3.5 What the dry run found, and the correction it forces

**Added 2026-08-15, after step 2 of §9 and before step 3.** The estimator was
exercised on constructed fields, which is what §9 orders and what this is for.
It found a limit that changes what this stage may claim.

**The resolving power is set by the fill of the cell-by-class design.** At a fill
of `0.60` and above the constructed rank comes back exactly, at every rank from
zero to three. At `0.35` and below it does not:

| fill | constructed 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0.85 | 0 | 1 | 2 | 3 |
| 0.60 | 0 | 1 | 2 | 3 |
| 0.35 | 0 | 1 | **3** | **4** |
| 0.20 | 0 | 1 | **3** | **6** |
| 0.15 | 0 | 1 | **3** | **2** |

**Three consequences, and the third is the expensive one.**

**§4's conservatism claim is corrected.** §4 argues the null is conservative in
the direction of the interesting reading, because permuting redistributes the
class main effect and inflates the null. That argument is about the null and it
stands. **It does not cover the table above**, which is about the estimator, and
the table runs the other way at every fill from `0.35` down to `0.20`. §4's
sentence should be read as scoped to what it argues about, and this section is
the part it does not reach.

**A claim of ours was refuted by our own sweep and is withdrawn rather than
restated.** The first form of criterion B7-4 asserted the error runs upward and
never downward, on a narrower sweep that showed only over-counts. The `0.15` row
refutes it: three reads back as two. B7-4 is now **reported and not judged**, in
the shape of `b3_cip_slice.md`'s B3-7. Outside its usable regime the estimate is
unreliable in either direction and no signed statement about it is available.

**The trichotomy of §5 is now conditional, and the condition is B7-0.** What
survives unconditionally is the **zero-versus-non-zero** split, which returns zero
at every fill tested. That split is already settled by `b1_theorem.md` Corollary 4
and B2's within share, so **on its own it is not new knowledge**. Everything this
stage could add lives in separating `1` from `>= 2`, and that separation is only
available where the design supports it.

**B7-0, the gate, registered here.** Take the observed design, keep every cell,
class, loan count and hole, and replace the values with a **rank-one** field
scaled to the observed interaction's own Frobenius norm plus noise at the
observed within-entry dispersion. Run the whole estimator on it.

- **Returns `1`.** The design separates one ladder from several at this signal
  strength. §5's trichotomy is available and B7-4's number may be read.
- **Returns anything else.** The design does not separate them. **Only the
  zero-versus-non-zero split may be reported, and §5's `1` and `>= 2` rows are
  unavailable**, whatever B7-4 returns.

The gate is not vacuous, which is itself checked: on constructed designs it
returns `1` at a fill of `0.85`, `3` at `0.60` and `4` at `0.35`. A gate that
passed everywhere would not be one.

**Why no wider null repairs this.** The leak grows with the signal, and the
permutation null has no signal, so the null cannot see it at any draw count. That
is why the gate is a calibration at the observed signal strength on the observed
design rather than a larger null.

**This may kill the stage before it costs anything, and that is the point of
running step 2 first.** §6's B7-9 already asks for the number that predicts the
gate: the count of distinct class levels present in the median cell. If a cell of
twenty loans shows three DTI levels out of nineteen, the fill is near `0.15` and
the gate will not pass. **Nobody should be surprised later by a result this
document did not warn about in advance.**

### 3.6 The gate, completed. Registered 2026-08-15, after B7-9 and before B7-0

**What B7-9 returned**, so that the state of knowledge when this section was
written is on the record: `326,872` cells, `19` classes, `16,035,398` loans,
**fill `0.7222`**, a median cell holding `14` of the `19` levels, and the class
index carrying **`0.3036`** of stage B2's within term. `results/b7_design.json`.
**No rank of the observed field has been computed**, by this or any file.

The fill sits between the `0.60` at which §3.5's constructed sweep still failed
and the `0.85` at which it worked, so the sweep does not settle it. It could not
settle it in any case: the constructed designs drop entries uniformly at random
and the real design's holes are structured, since a cell holding few loans shows
few classes. The question has to be put to the real pattern.

**§3.5's gate was registered incomplete and is completed here.** It checked only
that a constructed rank of one reads back as one. That guards against inflation
and **not** against the opposite: if the design cannot resolve a second dimension
at all, an observed `1` would be a failure to resolve rather than one ladder, and
§3.5 had no arm that would have caught it. Two arms are needed because the
trichotomy has two boundaries.

| arm | constructed field on the observed design | must return | gates |
|---|---|---|---|
| **B7-0c** | rank `0` | `0` | everything. A failure means the null is broken on this design |
| **B7-0a** | rank `1` | `1` | the **`>= 2`** reading. Without it a `>= 2` could be the sparsity of the design |
| **B7-0b** | rank `2` | `2` | the **`1`** reading. Without it a `1` could be a dimension the design cannot see |

Each is run in **three repetitions** differing only in the constructed factors,
and passes only if **every** repetition returns the constructed rank. Strict,
because the cost of a false "available" is a spurious headline and the cost of a
false "unavailable" is a stage that reports less than it could.

**The four outcomes and what each licenses, fixed here:**

| B7-0a | B7-0b | licensed |
|---|---|---|
| pass | pass | **the full trichotomy of §5** |
| pass | fail | **`>= 2` only.** A `1` may not be read as one ladder |
| fail | pass | **`1` only.** A `>= 2` may not be read at all |
| fail | fail | **zero-versus-non-zero only**, which Corollary 4 already settled |

**Draw count.** The null statistic is the largest eigenvalue over the draws, so
too few draws understate it and the estimate inflates. On constructed designs the
verdict at `30` draws and at `200` agreed, and the verdict at `15` did not. That
puts a floor above `15` and says nothing about a ceiling. The gate runs at `50`
and again at `200`, and **§3.6's criterion is that the two agree**. Neither number
is a threshold on a result; the agreement is.

**What is deliberately not written yet.** `experiments/b7_rank.py`, which would
read the observed field, does not exist. `b7_gate.py` cannot compute it. The
ordering of §9 is therefore enforced by what the code can do rather than by
anyone remembering the order.

### 3.7 What B7-0 returned, and two things §3.5 got wrong. Registered 2026-08-15

**B7-0 passed exactly.** On the real design, three constructed ranks by three
repetitions, at fifty draws and again at two hundred: `0 -> [0,0,0]`,
`1 -> [1,1,1]`, `2 -> [2,2,2]`. §3.6's two-draw-count criterion is met and the
verdict is **full trichotomy available**. `results/b7_gate_draws50.json` and
`results/b7_gate_draws200.json`. **No rank of the observed field has been
computed by any file that produced those.**

**First correction: fill is not the sufficient statistic.** §3.5 swept fill and
read a boundary off it at `0.60`, and the real design's `0.7222` clears it. But
constructed designs at the *same* fill do not recover cleanly: over five seeds at
fill `0.72` on three hundred cells, a constructed rank of two came back as three
in two of them, and the real design at the same fill returned two, three times
out of three, twice over.

The difference is not fill, it is **how many cells every entry of `S` averages
over**. The real design carries `326,872` cells with a median of fourteen classes
each; the constructed designs carry three hundred. So **§3.5's table is a lower
bound on what a real design of that fill can do**, not an upper one, and B7-0 on
the real pattern supersedes it. Recorded because the opposite reading was
available: taking §3.5's table as a ceiling would have declared the stage dead on
evidence that could not support it.

**Second correction: §3.6's gate ran under one null of the two.** §4 registers a
primary null, which permutes class labels within cells, and a secondary null,
which permutes residuals. `b7_gate.py` used the primary. Since §6's B7-5 requires
the two nulls to agree on the reading, **the gate has to clear under both**, and
discovering a disagreement after the headline exists is exactly the order this
document was written to prevent.

So `b7_rank.py` runs **B7-0r**, the same three arms under the secondary null,
*before* it reads the observed field, and does not compute an observed rank if
B7-0r fails. The concern is not idle: on constructed designs at fill `0.72` the
two nulls disagree on a rank-one field in three of five seeds. The primary null
is the more conservative of the two, because permuting labels redistributes the
class main effect and inflates it, which is §4's own argument read as a statement
about magnitude rather than direction.

**A wrong first implementation of the secondary null, recorded.** It differenced
against the cell-class mean rather than against the additive fit, which removes
the interaction *and* the between-entry noise from the shuffled pool. It
understated the null by roughly a factor of two and read a constructed rank of one
back as six. The two differences look alike and only one of them is a null.

### 3.8 B7-6's second class grid, sourced without an external file

§2.3 registers the second grid as DTI crossed with LTV bands transcribed from the
published GSE LLPA matrix. **That transcription has not been made**, so the arm
below is what B7-6 runs in the meantime, and the LTV arm stays registered and
unrun rather than being quietly replaced.

The published DTI field buckets everything below `36` and above `49` and reports
`36` through `49` as bare integers. Collapsing those integers into a single level
reconstructs the range the regulator's own bucket scheme leaves open, giving

```
<20%,  20%-<30%,  30%-<36%,  36-49,  50%-60%,  >60%
```

**Both boundaries are the regulator's**, `36` and `50`, at exactly the points
where its buckets stop and resume. This project chooses neither, so the coarse
grid is a second class index with no more researcher freedom in it than the fine
one has. B7-6 requires the two grids to agree on §5's **reading**, not on the
integer, since six levels and nineteen cap the rank differently.

### 3.9 B7-6 failed, and one of the two numbers it compared was never licensed

> **VOID, 2026-08-16. Read §3.21 and §3.22 before this section and the three that
> follow it.** §3.9 through §3.12 are one argument and all four rest on the coarse
> grid reading `1`. The class levels were stored alphabetically and read
> positionally, so that grid merged four published buckets with ten integers and
> put `<20%` in the same class as `49`. **On the corrected partition the coarse
> grid reads `2` under both nulls and B7-6 does not fail.** Every "the headline is
> withdrawn" below is void, every localisation deduction below is void, and the
> sections are kept whole and unedited because the argument they make was sound on
> the input it was given and the record of it is what shows where the input
> entered.


**Registered 2026-08-15, after `b7_rank.py --draws 50` and before any grid gate
was run.** `results/b7_rank_draws50.json`.

**What returned.** The secondary-null gate B7-0r passed on the fine grid,
`0 -> [0,0,0]`, `1 -> [1,1,1]`, `2 -> [2,2,2]`. B7-4 returned **matrix rank 2**,
read as **no single ladder**, with eigenvalues `1.467, 0.754, 0.277, 0.224, …`
against a null maximum of `0.382`: the second is `1.98x` the null and the third
is `0.72x`, so the reading is not marginal. B7-5 passed, and the two nulls agree
to within `0.3%` on the real design (`0.38171` and `0.38061`) rather than
disagreeing as they did on the small constructed ones. **B7-6 failed**: the coarse
grid returned `1`, which is a different reading.

**§7's row fires: the headline is withdrawn and both grids are reported.** That
stands unless the paragraph below resolves it, and it is written here in advance
of the run that could resolve it so that neither outcome can be chosen later.

**The gate is a precondition on the design a reading is taken from, and the
coarse grid is a different design.** §3.6's B7-0b exists because "an observed `1`
could be a second dimension this design cannot resolve". `b7_gate.py` and
`b7_rank.py`'s B7-0r both ran on the **fine** grid only. Collapsing nineteen
levels to six changes the class count, the distinct classes per cell and the whole
co-occurrence structure. So the coarse grid's `1` is, as things stand, an ungated
reading, and B7-6 compares one licensed number against one unlicensed one.

**B7-6r, registered now.** Run `b7_gate.py --grid coarse` at fifty draws and at
two hundred, three repetitions, the same three constructed ranks. **Both outcomes
are declared here and the criterion cuts both ways:**

| coarse grid on B7-0b | consequence |
|---|---|
| **passes** (constructed `2` reads back as `2`) | its `1` is a licensed reading. **B7-6 genuinely fails, §7 applies, the headline is withdrawn** and both grids are reported side by side with no trichotomy claimed |
| **fails** | its `1` is a failure to resolve and is not evidence against the fine grid. B7-6 is recorded as **"the coarse grid is unusable as a comparison arm"**, which is not a pass, and §2.3's LTV grid stops being optional |

**A post-hoc observation that is not used as an explanation.** Collapsing `36`
through `49` buries `43`, which is the qualified-mortgage debt-to-income
threshold, inside a single level. That is a story available only after seeing the
result and **it explains nothing here.** It may be registered forward as a later
arm with its own criterion; it may not be offered as the reason B7-6 failed, and
it is written down so that it cannot quietly become one.

### 3.10 B7-6r returned. B7-6 fails, and the headline is withdrawn

**Registered outcome, 2026-08-15.** `results/b7_gate_coarse_draws50.json` and
`..._draws200.json`. The coarse grid returned `0 -> [0,0,0]`, `1 -> [1,1,1]`,
`2 -> [2,2,2]` at **both** draw counts, so §3.6's two-count criterion is met and
the verdict on that grid is **full trichotomy available**.

**§3.9's `passes` branch fires, and it is the one that costs.** The coarse grid
can resolve a rank-two field on this design and it read the observed field as
`1`. Its `1` is a licensed reading. **B7-6 therefore genuinely fails, §7 applies,
and the headline is withdrawn.**

### What this stage now claims, exactly

**It does not claim the trichotomy.** B7 may not say the mortgage carrier has one
ladder and may not say it has none. §5's table is not delivered.

**It holds two licensed readings that disagree.** Both grids passed the same three
gate arms at two draw counts. Both are the regulator's own partition with no
boundary chosen by this project. On the fine grid (nineteen levels) the rank is
`2`; on the coarse grid (six levels) it is `1`. Both figures are stable across
two draw counts and both nulls.

| grid | levels | gated | rank | reading |
|---|---|---|---|---|
| fine | 19 | pass, both draw counts, both nulls | **2** | no single ladder |
| coarse | 6 | pass, both draw counts | **1** | one ladder |

**A deduction the two licensed results support, which is arithmetic and not a
story.** The grids differ in exactly one respect: the fourteen integer levels
`36` through `49` are one level in the coarse grid. The coarse design can express
rank two and did not. **So the fine grid's second direction is not a function of
the six coarse levels, and must distinguish levels the coarse grid merges.** The
second dimension, if it is real, lives inside `36-49`. That is a constraint on
where an explanation has to live and it is not an explanation.

### Two things registered forward, neither of which reopens B7-6

**A limitation of every gate run so far.** `calibration_sample` scales the
constructed interaction to the observed one's Frobenius norm and then splits that
energy roughly evenly across its directions. The observed spectrum is `1.4674`
against `0.7544`, about two to one. So each gate established that its design
resolves an **evenly split** rank-two field of the observed total energy, not a
`2:1` skewed one. **This is recorded as a limitation and is not a reason to
reopen B7-6**: §3.9's table was fixed before the run and its `passes` branch
fired. It binds any future grid comparison, which must gate at the observed
skew rather than at an even split.

**The arm that would isolate the second dimension.** A third grid that keeps
`36` through `49` separate and coarsens elsewhere would carry the second
direction if the deduction above is right and lose it if it is not. Registered
with its criterion in advance: **that grid must pass all three gate arms, and it
resolves the question only if it returns `2` where the coarse grid returned `1`.**
Any boundary in it must come from outside this project, on §2.2's standard, or
the arm is not runnable.

**§2.3's LTV grid stays optional.** §3.9 made it mandatory only on the branch that
did not fire.

**The qualified-mortgage threshold at `43` is still not offered as an
explanation.** §3.9 fenced it and the fence holds: it is a post-hoc story, the
localisation above was reached without it, and it may enter only as a forward
registration with its own criterion.

### 3.11 The complement grid. Registered 2026-08-15, before it was built or run

**§3.10's condition is met, not waived.** §3.10 required that any boundary in the
isolating grid come from outside this project on §2.2's standard. It does: the
grid below uses `36` and `50`, which are the regulator's, and which the coarse
grid already used. **No new boundary is needed and none is taken.** A remark made
in conversation that this arm was unrunnable for want of an external source was
wrong and is withdrawn here; the document never said it.

**The grid.** The exact complement of the coarse grid. The coarse grid keeps the
five published buckets apart and merges the fourteen integers `36` to `49`; this
one keeps the fourteen integers apart and merges the five buckets into one.
**Fifteen levels.** `b7_design.complement_classes`.

**What it tests, and what it cannot.** §3.10's deduction is a **necessity**
claim and it is arithmetic: the fine grid sees a second direction, the coarse
grid can express one and does not, so that direction must distinguish levels the
coarse grid merges. **Nothing below can refute that.** What this grid tests is
**sufficiency**: whether the distinctions inside `36-49` are enough on their own.

**Three readings, fixed here.**

| complement grid returns | reading |
|---|---|
| **`2`** | the within-`36-49` distinctions **suffice**. The second direction is expressible using only them, and §3.10's localisation sharpens from necessary to necessary-and-sufficient |
| **`1`** | they are **necessary but not sufficient**. The second direction also needs the five buckets kept apart, so it is a joint property of both sides of `36`. §3.10's deduction is untouched; only the stronger reading of it is refused |
| **`≥ 3`** | merging the buckets while splitting the integers exposes **more** structure than the fine grid resolves. That is a fact about the fine grid's own resolution and would put B7-4's `2` itself in question; it would be reported and nothing would be concluded from it without a further arm |

**The gate applies, and nothing here is readable without it.** Nine-tenths of
§3.9's lesson is that a grid without a gate contributes no evidence, and this is
a third grid. `b7_gate.py --grid complement` must pass all three arms at both
draw counts before B7-10's number may be read at all. Registered as criterion
**B7-10, reported and not gated**, in the shape of `b3_cip_slice.md`'s B3-7.

**This does not restore the headline.** B7-6 failed and §7 applies whatever this
returns. The trichotomy of §5 is not recoverable by adding a third grid, because
two licensed grids already disagree. What this arm can do is say **where** the
disagreement comes from, which is a smaller claim and the only one still open.

**Nor is it the qualified-mortgage story.** §3.9's fence holds. If the complement
grid returns `2`, the second direction is localised to fourteen levels; naming
`43` among them as the mechanism would still be a post-hoc identification and
would still need its own forward-registered arm with its own criterion.

### 3.12 B7-10 returned `1`. The second direction spans the whole partition

**Registered outcome, 2026-08-15.** `results/b7_gate_complement_draws50.json`,
`..._draws200.json`, `results/b7_rank_draws50.json`.

**The complement grid passed the gate at both draw counts**, `0 -> [0,0,0]`,
`1 -> [1,1,1]`, `2 -> [2,2,2]`. It is licensed. On the observed field it returned
**`1`**, under the primary null and under the residual null alike.

**§3.11's middle branch fires**: the distinctions inside `36-49` are **necessary
but not sufficient**.

### Three licensed grids, and what they jointly say

| grid | levels | gated | rank |
|---|---|---|---|
| **fine** | 19 = five buckets + fourteen integers | pass, both counts, both nulls | **2** |
| **coarse** | 6 = five buckets + `36-49` merged | pass, both counts | **1** |
| **complement** | 15 = buckets merged + fourteen integers | pass, both counts | **1** |

Merging the integers kills the second direction. Merging the buckets kills it
too. **So its class loading varies substantially on both sides of `36`, and no
single-sided coarsening preserves it.** §3.10's deduction stands and is joined by
its mirror: the second direction must distinguish levels the coarse grid merges
**and** levels the complement grid merges. Both necessary, neither sufficient.

**Whatever the second direction is, it is a property of the regulator's full
partition and not of either half.**

### A forward-registered negative on the qualified-mortgage story

§3.9 fenced the observation that `43` is the QM debt-to-income threshold and that
the coarse grid buries it. **That fence can now be replaced by evidence.**

A second direction that were purely a function of position relative to `43` would
be **fully representable in the complement grid**, which keeps all fourteen
integers apart. The complement grid passed the same three gate arms at both draw
counts and returned `1`. **A purely within-`36-49` second direction is therefore
inconsistent with B7-10.**

That is a forward-registered arm returning against a post-hoc story, which is
the only way this project allows such a story to be touched at all. The `43`
reading is not merely unlicensed now; it is **disfavoured**. It is not refuted:
a direction that loads on `43` *and* on the buckets is untouched by this. What is
excluded is the clean version, and the clean version was the whole appeal.

### What this does not do

**§7 still applies and B7-6 still failed.** Understanding *why* three grids
disagree does not un-fire a registered falsification, and the argument "the
disagreement has a mechanism, so the finest reading is the right one" is exactly
the move the registration exists to forbid. **B7 does not claim §5's trichotomy.**

**Two readings sit side by side and this stage does not choose between them.**
B7-0a licenses that the fine design does not manufacture a second direction out of
a rank-one truth at the observed energy, which argues the `2` is real. B7-6 says
the reading is not stable under a licensed change of class index, which argues it
is fragile. **Both are outputs of gated arms and neither retires the other.**
Naming that standoff is the honest terminal state of the stage as it stands.

### Outstanding

`b7_rank.py --draws 200` predates B7-10 and carries no complement column. The
observed spectrum does not depend on the draw count and both other grids returned
the same rank at fifty and at two hundred, so the confirmation is expected to be
routine, **and it has not been run.** Until it is, B7-10's `1` rests on one draw
count while every other number in this stage rests on two.

### 3.13 B7-7 and B7-8 split into a census and an estimation. Registered 2026-08-16

**Neither is voided and neither should be.** `VOID` means one thing in this
repository, and stage A3-8 is the specimen: a criterion that **could not be
scored** because no threshold was registered before it ran. B7-7 and B7-8 carry
registered criteria in §6, they are scorable, and the machinery to run them
exists. Retiring them because §10's headline is already withdrawn would be
declining to run the tests that can still go against the remaining reading, and
one of them guards a failure this very sample has produced once: `b2_measurement`
§10 records a single sentinel value of `-9999997` driving a within share to
`0.975`. **A record that never says whether the band was doing the work is worse
than a failed criterion.**

**What they can still do.** §10.6 names the terminal state as a standoff: B7-0a
argues the fine grid's `2` is real, B7-6 argues it is fragile. B7-7 and B7-8 are
the only registered arms that can move it. If the `2` dies under a band change, a
rank transform or a split by year, the standoff resolves toward fragile. If it
survives all three, the disagreement is pinned to class resolution alone. **The
headline is not recoverable either way** and §7 is not in question.

**The problem the criteria did not anticipate.** A different spread band keeps a
different set of loans, so a different set of cells clears `MIN_CELL_SIZE`, so
the fill and the co-occurrence counts move. **Every band is a different design**,
the rank-transformed arm is another (`rank_decomposition` is deliberately
computed with no band at all), and B7-8's two halves are two more. Nine arms.
`MEASUREMENT.md` failure mode 10, written into this repository out of B7-6's own
failure, says **every design a number is read from needs its own calibration**.
Nine gates is several hours.

**So the arms are counted before they are gated.**

- **Step a, the census.** `experiments/b7_robustness.py`. One read of the files,
  every arm's design described and none estimated. The deciding statistic is the
  **symmetric difference of the surviving cell sets** against the registered
  `±20` design: how many cells are in one and not the other. Two designs holding
  the same cells with the same classes are the same design, whatever their loan
  counts do at the third decimal, and the registered band excludes `115` rows out
  of `20,071,900`.
- **Step b, the estimation.** Gates and ranks, **only on the arms the census
  marks as different designs.** Arms that come back identical are the registered
  design and §10.2's gate already covers them.

**Registered before step a runs**: whichever arms come back different get a full
three-arm gate at two draw counts before any rank of theirs is read, on exactly
§3.6's terms. **No arm's rank is readable on the strength of another arm's gate**,
and an arm whose gate fails is reported as ungated rather than dropped.

**This is failure mode 10's first application rather than its first evasion.**
The rule was written on 2026-08-15 out of B7-6; it costs something here, three
days later, in the same stage.

### 3.14 The census returned. Five arms need gates, three do not. Registered 2026-08-16

`results/b7_robustness_census.json`, step a of §3.13.

| arm | loans | cells | fill | cells only here / only in reference | verdict |
|---|---|---|---|---|---|
| `band_10` | 16,035,185 | 326,869 | 0.7222 | 0 / **3** | new design |
| `band_15` | 16,035,350 | 326,871 | 0.7222 | 0 / **1** | new design |
| `band_20` (reference) | 16,035,398 | 326,872 | 0.7222 | 0 / 0 | registered |
| `band_25` | 16,035,409 | 326,872 | 0.7222 | 0 / 0 | **identical** |
| `band_30` | 16,035,418 | 326,872 | 0.7222 | 0 / 0 | **identical** |
| `band_50` | 16,035,428 | 326,872 | 0.7222 | 0 / 0 | **identical** |
| `rank_unbanded` | 16,035,535 | 326,874 | 0.7222 | **2** / 0 | new design |

**The rule earned its keep and it also cost.** Three arms come back identical cell
for cell, so §10.2's gate covers them and §3.13's split saved three gates.
`band_10` differs by **three cells out of 326,872** and is still a different
design, and it gets its own gate: §3.13 fixed the exact-match rule before the
census ran, and reading it afterwards as "close enough at three cells" is the
move registration exists to prevent.

**A correction to the census script's own note.** It said the year split "halves
every cell". It does not. **`activity_year` is one of the seven cell keys**, so
every cell lies wholly inside one parity: the split **partitions** the cells,
`160,645` odd and `166,227` even, summing exactly to `326,872`, and no cell is
halved or needs re-filtering for size. That makes B7-8 a stronger test than it
was registered as, because the two halves share **no cell at all**.

**So five arms are gated in step b**: `band_10`, `band_15`, `rank_unbanded`,
`odd_years`, `even_years`. Three arms carry §10.2's gate. `experiments/
b7_robustness_rank.py`, one read of the files, five gates and eight estimates.

**B7-8's form, restated because the estimator had to grow for it.** The criterion
is not a rank comparison between halves. It estimates the **leading class
loading** on the odd years and checks its **signs** on the even years, requiring
agreement on more than half the classes. An eigenvector is defined up to sign, so
the two are oriented by the larger overlap before the signs are counted; **that
is a convention and it is not a result**, and the cosine is reported beside the
count so a reader can see whether the orientation step did any work.
`interaction_rank.spectrum` now returns eigenvectors as well as eigenvalues,
because an estimator that returns a count and discards the direction cannot
answer a question about whether the direction is stable.

**Neither criterion can restore the headline** and §7 is not in question. What
they move is §10.6's standoff: a `2` that dies under a band change, a rank
transform or a year split resolves it toward fragile, and a `2` that survives all
three pins the disagreement to class resolution and nothing else.

### 3.15 Three criteria voided as mis-specified, and what replaces them. 2026-08-16

**None of these is voided because of what it returned.** Each defect below is
stated without reference to any result and survives deleting every number this
stage has produced. That is the test, and it is the only test that distinguishes
repairing a broken instrument from moving a goalpost.

**A criterion defended by "it was registered before the run" is not thereby
correct.** Registration protects against choosing the answer. It does not protect
against a criterion that was mis-shaped when it was written, and treating it as
if it did is procedure standing in for judgement. §3.9 and §3.12 both did that
and both are corrected here.

---

#### VOID 1. The gate's unanimity rule (§3.6)

**What it said.** Three repetitions, and the arm passes only if **every**
repetition returns the constructed rank.

**The defect, with no result in it.** The gate asks whether a design recovers a
rank. That is a **rate**, and this rule does two wrong things to it. It estimates
the rate with three trials, which can only return `0`, `1/3`, `2/3` or `1` and
cannot separate a rate of `0.9` from one of `0.6`. And it then thresholds that
unestimated quantity at `1`, so a design whose true recovery rate is `0.9` fails
`27%` of the time **because it is being asked to be perfect three times running**.
The rule is anti-correlated with what it means to measure.

**Replacement, and it invents no number.** The estimator's null statistic is the
**maximum over `d` draws**. Under the null the observed value and the `d`
permuted ones are exchangeable, so

```
P(observed exceeds all d)  =  1 / (d + 1)
```

**That is the test's own nominal size and it comes from its construction, not
from anyone's judgement.** So:

| arm | what it measures | against |
|---|---|---|
| **B7-0c** | rate at which a constructed rank `0` reads `>= 1` | the nominal `1/(d+1)` |
| **B7-0a** | rate at which a constructed rank `1` reads `>= 2` | the nominal `1/(d+1)` |
| **B7-0b** | rate at which a constructed rank `2` reads `2` | **no nominal exists**; this is power |

**All three are reported and none is gated.** The two size arms are compared
against a sourced expectation and the exact binomial tail is printed beside them.
The power arm has no sourced threshold, so it gets a Wilson interval and no line.

**Every reading taken from a design must be quoted with that design's three
numbers.** A binary "gated / ungated" was throwing away the only information the
gate actually produces. This is strictly more informative and it fixes nothing by
fiat.

**Repetitions: at least twenty**, so the rate is estimated rather than sampled.
Twenty trials against a nominal of `1/51` expect `0.39` failures and detect a
five-fold size inflation; twenty trials at a power of `0.9` give a Wilson
interval of about `±0.1`. Both numbers are consequences of the binomial, not
choices.

**One draw count, matching the reading's.** §3.6 required two, which was a proxy
for "is the answer stable". The rate against nominal answers that directly and at
a fraction of the cost, because the nominal moves with `d` and the comparison
stays valid at any `d`.

---

#### VOID 2. The design-identity rule (§3.13)

**What it said.** Two designs are the same when their surviving cell sets have
symmetric difference exactly zero; otherwise the second needs its own gate.

**The defect, with no result in it.** It is an exact-match test on a set of
`326,872` elements with the threshold at zero. At the "same" end it is
informative. At the "different" end it cannot separate a difference of three
cells from a difference of three hundred thousand, and the quantity the gate
actually depends on is not the cell set but the **co-occurrence counts**, which
three cells move by about `1e-5`.

**Replacement.** The rule existed to skip gates and save time. **It is withdrawn
and nothing replaces it: every design a reading is taken from gets its own
gate.** With VOID 1's gate that is about ten minutes per design, and buying a
skipped gate with an invented tolerance is a bad trade at any price. The
co-occurrence comparison is still computed and still reported, as **description
of how similar two designs are** and not as a licence to skip anything.

---

#### VOID 3. The calibration's spectrum shape (§3.12)

**What it said.** Recorded as a limitation, "and is not a reason to reopen B7-6:
§3.9's table was fixed before the run and its `passes` branch fired."

**That sentence is the error.** A gate that is mis-calibrated is mis-calibrated
whatever was fixed beforehand. Registration cannot repair an instrument.

**The defect, with no result in it.** `calibration_sample` draws random factors
and scales the constructed interaction to the observed one's Frobenius norm. Random
factors put **roughly equal** energy in each direction. So a constructed rank-two
field has a flat spectrum, and every gate run so far established that its design
resolves a **flat** rank-two field. Whether it resolves a **skewed** one was never
asked, and the skew is exactly what determines whether the second direction is
near the null.

**Replacement.** The constructed field's spectrum is matched to the **observed
design's own** spectrum: for a constructed rank `r`, the `i`-th direction is
scaled by `sqrt(lambda_i)` of that design's observed top `r` eigenvalues, then the
whole field is scaled to the observed Frobenius norm as before. The shape comes
from the data and not from a choice, exactly as the total energy and the noise
level already do.

**Consequence, stated plainly: every gate this stage has run is superseded.**
B7-0, B7-0r, B7-6r and B7-10's gate were all run on flat calibration. They must
be re-run on all eight designs under VOID 1's rate criterion and VOID 3's shape.
**Until they are, no reading in §10 is licensed**, including the ones that passed.
A repair applied only to the arms that failed would be the cherry-pick this
section exists to avoid.

---

**What is not touched.** §10.6's "understanding why three grids disagree does not
un-fire a registered falsification" stands: that defence is about the logic of the
finding and survives deleting the procedure. `b1_theorem.md` Corollary 4 and stage
B2's figures are 1-skeleton quantities and no gate bears on them.

---

### 3.16 The calibration matched, not only shaped. Registered 2026-08-16, before it was run

§3.15's VOID 3 replaced a flat constructed spectrum with a shaped one and left
the rest of `calibration_sample` alone. **Writing that replacement exposed two
more defects in the same construction, both of the same kind and both larger.**
They are stated here without reference to any result, and VOID 3's paragraph
saying what the replacement is, is superseded by this section.

**Both defects push the same way: they made the gate easier than the reading it
licenses.** That direction is the one that matters. A gate's whole job is to say
whether a reading may be taken, and a gate run on an easier problem than its
reading certifies nothing.

#### Defect A. The constructed sample carried no class main effect

`calibration_sample` returned `gamma + noise` and no additive part at all. The
estimator centres the additive part out, so this looked harmless. **The null does
not centre it out before it draws.** The primary null shuffles class labels among
the loans of a cell, so what it draws from is the spread of values *inside* that
cell, and a class main effect `A(a)` is part of that spread in the observed
sample and was absent from it in the constructed one. So the constructed sample
faced a **thinner null** than the reading faces, on the same design, for no
reason other than that the construction omitted something the data has.

This is not a claim about how large `A(a)` is. Whatever its size, it is in the
observed sample and it was not in the constructed one, and the sign of the
resulting error is fixed: less spread inside a cell gives a lower null maximum,
which lets more directions clear it, which makes the gate pass more easily than
the reading warrants.

**Replacement.** The constructed sample is the **observed additive fit**, plus
the constructed interaction, plus noise. The cell effect comes along with it,
which is free: it is constant within a cell and a within-cell null cannot see it.

#### Defect B. The constructed interaction was scaled to the trace, not to the top

`calibration_sample` scaled its rank-`r` construction so that the Frobenius norm
of the whole constructed `gamma` matched the Frobenius norm of the whole observed
`gamma`. **The observed `gamma` is not rank `r`.** Its energy is spread over all
the class directions, `S`'s trace is the whole of it, and its top `r` eigenvalues
are a proper part of that. Handing a rank-`r` construction the entire trace gives
those `r` directions everything the tail was carrying.

The sign is again fixed and again by construction: the sum of all the eigenvalues
exceeds the sum of the top `r` on any design whose tail is non-zero, which is
every design with noise in it. So the constructed field's top directions are
**stronger** than the observed field's top directions, always, and the gate then
certifies that the design can resolve a rank-`r` field larger than the one the
reading claims to see.

**Replacement.** The construction is scaled so that its **own** `S` carries the
observed `lambda_1`, with the remaining directions in the observed ratios. `S` is
quadratic in `gamma` and the mask does not move, so one scalar rescale sets every
eigenvalue exactly and no iteration is involved. The construction now presents
the observed top `r` in level as well as in shape.

#### What survives from VOID 3

The shape rule survives verbatim and is now one of three things matched rather
than the only one. Its stated consequence survives and widens: **every gate this
stage has run is superseded**, and so is every gate the shape fix alone would
have produced.

#### The construction is checked before the gate is paid for

`experiments/b7_calib_check.py` builds the constructed field at ranks `0` to `3`
on a design, runs one pass of the same estimator the reading uses, and prints the
**recovered** spectrum against the **observed** one. No null is drawn, so it costs
one pass rather than three thousand.

**Declared before it was run.** The level match is applied to `gamma` before the
estimator re-centres it and before the sampling noise adds its own energy, so the
recovered spectrum is expected to sit a little **above** the observed one rather
than on it. A few percent is the construction working. A multiple is not, and on
the superseded construction a multiple is what should appear, of roughly the
trace over the sum of the top two.

**The gate is not run until this has been read.** Six hours spent on a
construction nobody measured is how §3.15 came about.

#### Two things this section does not fix, deliberately

The constructed noise is homoskedastic at the pooled within-entry dispersion and
the observed noise is not. And the gate runs under the **primary** null, which
`permute_within_cells` documents as inflated by the class main effect it
redistributes.

Both are left alone on purpose. The reading is taken under the same primary null,
on a sample with the same `A(a)` in it, so whatever those two do to the gate they
do to the reading, and the comparison is between two objects carrying the same
bias. That is the argument `estimate_rank` already makes for running the null
through the identical code path, and it is the reason the gate must not be
"improved" into a cleaner construction than the thing it gates.

**One consequence to state rather than bury.** Under a null inflated by `A(a)`,
VOID 1's nominal `1/(d+1)` is an **upper bound** on the size and not the size
itself. The exact binomial line stays exactly as registered and it is one-sided:
a rate significantly **above** `1/(d+1)` says the estimator's size is broken on
that design; a rate below it is expected and says nothing.

---

### 3.17 The observed eigenvalues already contain the noise. Registered 2026-08-16, before the corrected construction was run

§3.16 declared its own reading before it ran: a recovered spectrum "a few percent"
above observed is the construction working, a multiple is not. **It came back at
`+16%` on `lambda_1` and `+27%` on `lambda_2`. By its own registered standard that
is not working, so it gets one more turn rather than a re-reading of what "a few"
means.**

**The defect, with no result in it.** `S` is a second moment of a `gamma`
recovered from cell-by-class **means**, and a mean of `n` loans carries sampling
noise of order `sd^2 / n`. So the observed `lambda_i` is not the `i`-th
eigenvalue of the field. It is that eigenvalue **plus** whatever the noise
contributes to that direction. §3.16 set the constructed **signal** to
`lambda_i`, and then handed it the same sampling noise, which lands it at
`lambda_i + c`. The constructed field is stronger than the observed field by `c`,
and `c > 0` on any design whose cell-class entries hold finitely many loans,
which is every design.

The sign is the same one §3.16 exists to fix, so §3.16 was incomplete and not
wrong. Both sections' corrections stand together.

**Replacement.** The constructed signal is set to `lambda_i - c`, so that the
**recovered** spectrum lands on the observed one instead of above it.

**`c` is measured on the design, not derived.** It has a closed form, the mean
over classes of the mean over cells of `sd^2 / n_ca`, and that form ignores the
alternating centring, which removes part of the noise before `S` ever sees it.
`measure_noise_floor` instead builds a **rank-zero matched sample**, the observed
additive part and the observed noise level on the observed design with no
interaction at all, and takes `trace(S) / n_classes` from one pass of the
estimator the reading uses. That gets the centring for free and it costs one
pass. It is the same argument `estimate_rank` makes for putting its null through
the identical code path, applied to the calibration.

Averaged over three draws, and **the per-draw values are printed and stored**. A
floor whose draws disagree is a floor that is not the same object on every
repetition, and that should be visible rather than folded into a mean.

**The isotropy this assumes, and how it is checked rather than trusted.** One `c`
is subtracted from every direction, which is exact only if the noise's expected
second moment is a multiple of the identity in class space. It is not, because
classes hold very different loan counts. The approximation is not defended by
argument: `b7_calib_check.py` measures what the corrected construction actually
recovers against what it aimed at, on every design, before any gate is paid for.
If the approximation were bad, the recovery would miss and the check would say so
for the price of one pass.

**An arm can now be unavailable, and that is information.** If a design's
observed `lambda_r` does not exceed `c`, then that design's `r`-th direction is
not separable from its own noise floor and there is no observed level for a
rank-`r` construction to be set to. The arm is recorded as unavailable and
nothing is substituted for it. That is a fact about the design, not a gap in the
gate, and it is reported as such.

**The condition on paying for the gate, fixed here before the corrected check was
run.** At `floor = c`, the recovered `lambda_1` and `lambda_2` land within a
couple of percent of the observed ones and the recovered ratio within a couple of
percent of the observed ratio. If they do, the gate runs. If they do not, the
construction gets another turn and the gate keeps waiting, because hours spent on
a construction that misses its target buy nothing.

---

### 3.18 The floor is solved for, not assumed isotropic. Registered 2026-08-16, before the solved construction was run

§3.17's check returned, and it is a partial pass. At `floor = c` the recovered
`lambda_1` landed `2.0%` above observed and `lambda_2` landed `4.1%` above.
Against `+16%` and `+27%` at `floor = 0`, and against `+52%` and `+163%` on the
construction §3.15 voided, that is most of the distance. **It is not the couple
of percent §3.17 declared, and §3.17 said what happens then: the construction
gets another turn.**

**The defect, with no result in it.** §3.17 subtracts one number from every
direction. That is exact only if the noise's expected second moment is a multiple
of the identity in class space. It is not: classes hold very different loan
counts, so the noise contributes unequally across directions, and a rank-`r`
construction's directions are not the noise's own eigendirections. One scalar
therefore cannot land every direction, and the residue it leaves is in the same
direction as every defect from §3.15 onward, which is the constructed field
sitting **above** the observed one and the gate being easier than the reading.

**Replacement.** The floor is **solved for** rather than assumed: build the
rank-`r` construction at §3.17's `c`, measure what it recovers, and move the
floor by the mean excess. One step, three draws at each floor, and the floor is
per rank, because a rank-one and a rank-two construction do not distribute the
same energy over the same directions and have no reason to want the same floor.

**What is solved for is the construction's input, and not the gate's answer.**
The target is the observed spectrum, fixed before any of this ran and not movable
by it. Whether the estimator then returns `r` on the constructed field is not an
input to the solve, is not compared to anything inside it, and is not touched by
it. A calibration that reaches its declared target is the precondition for a gate
meaning anything; reaching it by measurement rather than by an isotropy
assumption is the same choice `measure_noise_floor` already makes over the closed
form.

**One hard condition, and no threshold on the miss.** The condition is that **the
solve reduces the miss**. A step that makes the miss worse is not doing what it
claims, and the construction falls back to §3.17's floor with the miss reported.
That condition needs no number chosen by anyone.

There is deliberately **no cutoff on the miss itself**, for VOID 1's reason. A
threshold converts a measured quantity into a bit and throws the quantity away.
**The achieved miss travels with every rate the arm produces**, in the printed
line and in the result record, so a reader can see when an arm's rate and its
calibration's miss are of the same order and when they are not. That is the same
move VOID 1 made on the gate's unanimity rule and it is made here for the same
reason.

**Where the iteration stops.** At one step, declared here. The map from floor to
recovered spectrum is `lambda_i - floor` plus an offset that is nearly flat in
the floor, so a step of the mean excess lands inside its own sampling error and a
second step would be chasing noise. Every iterate is recorded, so a solve that
did not converge is visible rather than assumed away.

#### Two things the check established that stand whatever the calibration does

**The observed tail is this design's noise floor, measured.** A rank-zero
construction, which is the observed additive part and the observed noise on the
observed design with no interaction at all, recovered
`[0.2953, 0.2676, 0.2113, 0.2102, 0.2039, 0.2021]`. The observed spectrum from
`lambda_3` down is `[0.2768, 0.224, 0.2199, 0.2155, 0.2125, 0.2096]`. Those are
the same object. §3.7 assumed the tail was noise; it is now measured on the
design, and `S`'s trace splits `41.6%` into the top two and the rest into a floor
that a field with no interaction reproduces.

**A true rank-one field at the observed strength puts its second eigenvalue at
that floor.** The rank-one arm recovered `lambda_2 = 0.291` against the rank-zero
arm's `lambda_1` of `0.295`. The observed `lambda_2` is `0.754`. This is one draw
of a construction and it is not a gate, and it says the observed second direction
is `2.6x` what this design manufactures out of a single ladder plus its own
sparsity. **It is the first evidence in the stage that bears on §10.6's standoff
from the calibration side rather than the reading side**, and it runs against the
"fragile" branch. The gate is what decides it, at a rate rather than at one draw.

#### What the superseded construction was actually gating

For the record, on the fine grid, against an observed `lambda_2` of `0.7544`:

| construction | recovered `lambda_2` | times observed |
|---|---|---|
| `calibration_sample`, flat (every gate before §3.15) | `1.982` | `2.63x` |
| `calibration_sample`, shaped (VOID 3's fix alone) | `1.391` | `1.84x` |
| `matched_sample`, `floor = 0` (§3.16) | `0.9618` | `1.275x` |
| `matched_sample`, `floor = c` (§3.17) | `0.7854` | `1.041x` |

**VOID 3's fix alone would have made `lambda_1` worse**, from `1.52x` observed to
`1.94x`, because shaping a construction whose total is pinned to the trace pushes
energy into the first direction. That is why §3.16 sits on top of it rather than
beside it, and it is a second reason the shape fix could not have been applied to
the failing arms alone.

---

### 3.19 §3.18's solve is voided. The residue is under the construction's own scatter. Registered 2026-08-16

§3.18 solved for the floor in one step and its own hard condition fired: on the
rank-one arm the step made the miss **worse**, `3.51%` to `3.88%`. On the
rank-two arm it improved, `6.23%` to `3.48%`.

**Applying the solve only where it improved would be selection on the outcome**,
and it would be selection on an outcome measured with three draws. So the branch
is not taken and the whole solve is voided.

**The defect, with no result in it.** §3.18 computes its step from a three-draw
mean and **never measured that mean's sampling error**. A step computed from an
unmeasured error is a step of unknown size. Worse, its acceptance test, "the
solve reduces the miss", is evaluated with the same three-draw measurement, so
the test cannot separate a real improvement from the draw it happened to get.
A procedure whose correction and whose test for the correction share one
unmeasured noise source cannot report on itself.

That argument is available before any of it runs and does not need the outcome.
The outcome only confirms it: the same rank-two arm read `4.11%` off one draw and
`6.23%` off a three-draw mean, so the per-draw scatter is of the same order as
the residue being chased.

**Replacement: §3.17's floor stands and nothing further is solved.** The
construction lands within a few percent of the observed spectrum, the residue is
comparable to the construction's own draw-to-draw scatter, and a bias smaller
than the spread the gate already samples over is not worth an hour of anyone's
compute. §3.15's voided construction was out by `2.63x` on the deciding
eigenvalue; §3.17 is out by about `1.04x` with a scatter of about the same size.
That is where the instrument stops being the binding constraint.

**The achieved level is measured, not assumed, and it costs nothing.** The gate
constructs a fresh field on every repetition and the estimator already returns
that field's spectrum. So each arm's twenty repetitions **are** twenty
independent measurements of what the construction achieved, and the gate reports
the mean and the standard deviation of `recovered lambda_i / observed lambda_i`
beside every rate, per design, per arm. No extra pass is drawn for it.

**That is what §3.18 got right and is kept**: the miss travels with the rate. What
is dropped is the attempt to tune the miss to zero with an instrument that cannot
see it.

**`solve_floor` and `SolvedFloor` stay in `interaction_rank.py`, unused by the
gate.** Nothing in this repository is deleted, and a reader who wants to check
that the solve is noise-dominated needs the function that produced the numbers.

---

### 3.20 B7-11: what a coarsening can carry. Registered 2026-08-16, before it was built or run

**Registered before the code existed.** The readings below were fixed first and the
script was written against them.

#### Why the gate could not ask this and this can

§10.6's standoff is between "the fine grid's `2` is real" and "it is fragile",
and B7-6 is the arm that put it there: the fine grid reads `2` and the coarse
grid reads `1`. The old gate licensed reading the coarse `1` as a real absence by
showing that the coarse design recovers a **constructed** rank two. §3.16 voided
that gate, and repairing it does not help, because under §3.17 the constructed
level comes from the design's **own** observed spectrum. On a grid whose observed
`lambda_2` already sits below its own null, that arm asks whether a design can
resolve a thing it has already failed to resolve. **The answer is forced by the
construction and the arm carries no information.**

The question B7-6 actually needs is different: **if the fine grid's second
direction were real, would the coarse index see it at all?** That is not a
question about the estimator and it needs no null and no repetitions. It is a
question about what a coarsening does to a direction, and coarsening is a linear
operation whose coefficients are in the data.

#### The operation, stated exactly

The coarse cell-class mean is the loan-count-weighted average of the fine ones
inside the cell:

```
m_coarse(c, b)  =  sum over a in b of  n_ca * m_fine(c, a)  /  n_cb
```

So a fine class loading `v` arrives at the coarse index as its **count-weighted
bucket means**. A direction whose loading varies inside the buckets and averages
to nothing in each of them is destroyed by the coarsening no matter how strong it
is. A direction whose loading is roughly constant inside buckets survives intact.
**Nothing about the estimator enters this.**

#### What B7-11 computes

1. The fine grid's `gamma` and its eigen-decomposition, one pass.
2. For each direction `i`, the rank-one part of `gamma` that loads on `v_i`:
   `gamma_i = (Gamma v_i) v_i^T`, masked by the observed presence pattern.
3. `gamma_i` written back to the loans, with **no additive part and no noise**, and
   run through the identical pipeline on the coarse class index. Its top
   eigenvalue is `lambda_i -> coarse`, what the coarse index can carry of fine
   direction `i`.
4. The same against the complement partition.
5. The **carry fraction** `lambda_i -> coarse / lambda_i`, per direction, per
   partition.

The additive part is excluded from step 3 on purpose: `gamma`'s directions are by
construction orthogonal to the fine additive part, so the question is about
`gamma_i` alone.

#### A confound this exposes, named before it is measured

**A fine class main effect does not stay a class main effect under coarsening.**
`A(a)` depends on the class only, but its coarse image is

```
A_coarse(c, b)  =  sum over a in b of  (n_ca / n_cb) * A(a)
```

which depends on the **cell**, through that cell's class composition inside the
bucket. So a pure fine main effect **manufactures a coarse interaction** wherever
the class mix varies from cell to cell. The fine cell effect has no such problem:
it is constant across classes within a cell, so every bucket average returns it
unchanged.

Nothing in this stage has named that. It means the coarse grid's observed `gamma`
contains a component that the fine grid's does not and that no coarsening can
avoid. **B7-11 measures it**: `A(a)` alone, coarsened, run through the same
pipeline, top eigenvalue reported beside the others.

#### The readings, all declared here before the run

**Control, and it is the arm's own floor.** Direction `1` must carry well to both
partitions, because both grids demonstrably read at least rank one. **A small
carry fraction for direction 1 falsifies the computation, not the data**, and the
run is discarded rather than interpreted.

**On direction 2 against the coarse partition:**

| what comes back | what it means | what it does to §10.6 |
|---|---|---|
| carried `lambda_2` **below** the coarse grid's own `null_max` | the coarse index **cannot** carry the fine grid's second direction even if it is real | B7-6's failure is explained by the coarsening geometry alone. The standoff resolves toward "the `2` is real and the coarse grid is blind to it". **B7-6 stays a fired falsification** and §5's trichotomy stays undelivered; what changes is that "fragile" is replaced by "grid-limited", and those are different claims |
| carried `lambda_2` **comfortably above** it, and the coarse grid still reads `1` | the coarse index **could** have shown it and did not | runs against the fine grid's `2`. The standoff resolves toward fragile |
| carried `lambda_2` **near** it | not decisive | and only then is a constructed-and-coarsened gate arm worth building |

**None of those three rows fired, and the reason is worth more than the table.**
Every one of them is conditioned on the coarse grid reading `1`. It reads `2`.
The carried `lambda_2` came back at `0.7382`, well above the coarse grid's
`null_max` of `0.3931`, which is row two's first clause; row two's second clause,
"and the coarse grid still reads `1`", is false.

**That is the third registration in this stage to declare its outcomes on top of
the scrambled partition**, after §3.11's three readings for the complement grid
and §3.20's own control. **Registering an outcome table in advance does not
protect against a mis-computed input**, and the three of them together are the
clearest statement of that this document contains. §3.22 records what actually
came back.

**On direction 2 against the complement partition**, the same three rows. §3.12
deduced from B7-10's `1` that the second direction spans the whole partition.
**B7-11 tests that deduction directly rather than by inference from two ranks.** A
poor carry to both partitions confirms it and puts a number on it. A good carry to
either one refutes it, and §3.12 is then wrong and is voided rather than
reinterpreted.

**On the coarsened main effect:** its top eigenvalue is reported against the
coarse grid's `null_max`. Above it, the coarse grid's `gamma` carries a component
manufactured by the coarsening, and every comparison between the two grids in
§10.5 has a confound that nothing in the stage has accounted for. Below it, there
is no such confound and §10.5 stands on that point.

#### Cost, and why this is registered instead of the gate

Twelve estimator passes and two null runs of fifty draws. Under five minutes.
Against roughly five hours for a corrected gate sweep whose most consequential arm
is forced by its own construction.

---

### 3.21 The partitions were never the regulator's. Every grid comparison in this stage is void. 2026-08-16

B7-11 ran and its control failed. Chasing the control found something larger.

#### The bug

`load_with_class` assigns each class level a code **by first appearance in the
CSV files**. `design_from_loaded` stored the level names as
`sorted(meta["levels"])`, which is the same strings in **alphabetical** order.
`coarse_classes` and `complement_classes` then read that list **positionally**:
`levels[i]` is taken to be the level of code `i`.

**It is not.** On the retrieved sample the code order is

```
41, 36, 30%-<36%, 39, 44, 43, 20%-<30%, 42, 37, 50%-60%, 48, 49, <20%, 45, 40,
38, 47, 46, >60%
```

and the alphabetical order is

```
20%-<30%, 30%-<36%, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
50%-60%, <20%, >60%
```

`coarse_classes` merges the positions whose alphabetical entry is a bare integer,
which is positions `2` through `15`. In code order those positions hold

```
30%-<36%, 39, 44, 43, 20%-<30%, 42, 37, 50%-60%, 48, 49, <20%, 45, 40, 38
```

**four published buckets and ten integers, in one group**, leaving `41`, `36`,
`47`, `46` and `>60%` each alone. The grid this stage called "the regulator's own
bucket scheme" put `<20%` in the same class as `49`.

#### Why nothing caught it

The scrambled partition has six groups, because fourteen positions carry bare
integers whichever levels sit in them. **The group count is right, the fill is
right, the loan counts are right, every criterion in §6 is satisfiable, and every
gate passes.** A partition's name is not its membership and nothing in the stage
ever printed the membership. §3.8 argued at length that both boundaries are the
regulator's and this project chooses neither, which is true of the intent and was
false of the code.

#### What is void

| | |
|---|---|
| **B7-6** fine `2` against coarse `1` | **void.** The "coarse grid" was a scramble |
| **B7-6r**, the coarse grid's gate | **void**, and it was already superseded by §3.16 |
| **B7-10** and §3.12, the complement grid's `1` | **void** |
| **§10.5**, both claims | **void**: "merging either half destroys the second direction", and "a qualified-mortgage cliff at `43` is disfavoured". Both are inferences from the two scrambled grids |
| **§10.6**'s standoff | **void as posed.** One of its two branches was B7-6 |
| **B7-11**'s partition rows | **void.** The machinery is sound and the input was not |

#### What survives untouched

**Nothing that uses no partition is affected.** B7-4 and B7-5, the fine grid's
rank `2` under both nulls; B7-7's band sweep; B7-8's `19/19` and `|cos| = 0.9991`;
B7-9's `0.3036`; the whole design audit; every calibration correction in §3.15
through §3.19, which is about a construction and not about a class index. **The
class codes themselves are correct**; only the mapping from a code to its printed
name was permuted, and the estimator is invariant to class labelling.

#### The fix, and the guard

`class_levels` is now stored in **code order**, through `levels_by_code`, which is
named after this bug. The two partition functions carry a comment saying they read
the list positionally, and both raise if its length does not match the class
count, which is the only misalignment a callee can detect from inside.

**The guard that would have caught this is printing the membership.**
`b7_carry.py` now prints every group's contents before it computes anything. A
scrambled partition is invisible in a count and obvious in a list.

#### §3.20's control is voided too, on its own merits

**What it said.** Fine direction `1` must carry to both partitions, because both
partitions demonstrably read at least rank one.

**The defect, with no result in it, and it is a quantifier error.** Reading rank
one means **some** direction survives the coarsening. It says nothing about
**which**. A partition that annihilates direction `1` and carries direction `2`
reads rank one and violates the control while being exactly what a rank-two truth
predicts. The control confused a direction with the direction, and that is wrong
before any data is seen.

**Replacement, and it has power the old one did not.** **The number of fine
directions that clear a partition's own `null_max` must equal that partition's own
observed rank**, and the largest carried value must match that partition's
observed `lambda_1`. Both are computed from what the arm already produces, neither
names a direction in advance, and a disagreement is a real inconsistency between
the carry computation and the reading rather than a violated expectation.

---

### 3.22 B7-11 on the corrected partitions. B7-6 does not fail, and the whole localisation chain is void at its root. 2026-08-16

The memberships are now what §3.8 and §3.11 say they are, and they are printed
before anything is computed:

* **coarse**, six groups: `<20%`, `20%-<30%`, `30%-<36%`, the fourteen integers
  `36` to `49` as one group, `50%-60%`, `>60%`.
* **complement**, fifteen groups: each of the fourteen integers alone, and the
  five published buckets merged into one.

#### What came back

| | coarse (buckets apart, integers merged) | complement (integers apart, buckets merged) |
|---|---|---|
| observed rank | **2** | **0** |
| observed spectrum | `1.453, 0.749, 0.2622, 0.0745` | `0.2241, 0.2199, 0.2156, 0.2125` |
| `null_max` | `0.3931` | `0.2410` |
| fine direction 1 carries | `1.437`, **`97.9%`** | `0.00218`, **`0.15%`** |
| fine direction 2 carries | `0.7382`, **`97.9%`** | `0.00359`, **`0.48%`** |
| fine direction 3 carries | `0.2478`, `89.6%` | `0.02343`, `8.5%` |
| fine direction 4 carries | `0.001118`, `0.5%` | `0.1663`, `74.3%` |
| main effect `A(a)` alone | `2.5e-05` | `4.0e-04` |

**Both controls pass.** Two fine directions clear the coarse partition's null and
the coarse partition's own observed rank is two; zero clear the complement's and
its own observed rank is zero. The leading carried value matches each partition's
own `lambda_1` to `0.989` and `0.742`.

#### B7-6 does not fail

**The fine grid reads `2`. The coarse grid reads `2`.** They agree. The
disagreement B7-6 recorded was between the fine grid and a scrambled index that
put `<20%` in the same class as `49`.

**§7's falsification did not fire on the thing it is about.** That is not the same
as un-firing it by argument, which §10.6 rightly forbids. It is a statement that
the input was mis-computed, and a criterion evaluated on a mis-computed input has
not been evaluated. B7-6 is re-run by its own script under `b7_rank.py`, and the
number above is the same estimator on the same design and says what it will find.

#### The localisation chain is void at its root, not at its conclusion

§3.9, §3.10, §3.11 and §3.12 are one argument and every link rests on a single
premise: **"the coarse grid can express a second direction and does not."** The
coarse grid does. So:

* §3.10's deduction that the second direction "must distinguish levels the coarse
  grid merges" is **void**;
* §3.11's three declared readings for the complement grid were built on it and are
  **void with it**, and §3.11 did not declare a `0` in any case, which is recorded
  as a gap rather than filled after the fact;
* §3.12's conclusion that "the second direction spans the whole partition" is
  **void**;
* §10.5's two claims, already voided by §3.21, are void at their source as well.

#### What is true instead, and it is the opposite

**The interaction is a bucket-level object in its entirety.** Both directions
carry at ninety-eight percent into the six-level index that keeps the five
published buckets apart and merges every integer from `36` to `49`. Merging those
fourteen levels costs two percent of the first direction and two percent of the
second.

**The integer resolution carries nothing.** The fifteen-level index that keeps all
fourteen integers apart and merges the buckets reads **rank zero**, and its entire
spectrum, `0.2241, 0.2199, 0.2156, 0.2125`, is flat at its own noise floor.

**A qualified-mortgage cliff at `43` is excluded**, and on evidence stronger than
§3.9's fence contemplated. A cliff at `43` is a contrast between `36-42` and
`43-49`, which the complement index represents exactly. That index finds nothing
at all above its null, from any direction, not merely nothing that matches a
cliff.

**The obvious objection, and the answer.** Are the integer levels simply too thin
to see anything, so that the complement grid's `0` is a power failure? No. Its
fourteen integer classes are **the same classes as the fine grid's**, with the
same cells, the same entries and the same loan counts; the only change is that
five buckets become one, which makes that one class larger and none of them
smaller. Its `null_max` is `0.2410` against the fine grid's `0.3817`, so it is
**less** noise-limited than the index that does see two directions, not more.

#### The confound named in §3.20 is measured and absent

The fine class main effect, coarsened alone, arrives at `2.5e-05` on the coarse
index and `4.0e-04` on the complement, against nulls of `0.393` and `0.241`.
Whatever cell-to-cell variation there is in class composition, it is nowhere near
enough to manufacture an interaction either index can see. **Named before it was
measured, and cleared.**

#### What this does not do

**It does not restore the headline.** The gate has not been run under §3.15's
VOID 1 or §3.16 through §3.19's calibration, so the rank-two reading is not
licensed on the fine grid or on the coarse one. What has changed is that the
obstacle is no longer a disagreement between grids. **It is a calibration that
has not been paid for**, and §10 stays superseded until it is.

**Direction 4 is not a finding.** It carries `74%` into the complement index,
which makes it the one direction that lives in the integer contrast, and at
`0.224` it is below the fine grid's own null and below the complement's. It is
recorded and nothing is read from it.

---

### 3.23 The two directions load on the two thinnest classes. B7-12 registered before it is run. 2026-08-16

Both gates returned clean. Fine grid: `0/20`, `0/20`, `20/20`. Coarse grid: the
same three. Every arm's calibration landed within a few percent of the observed
level on the fine grid, and within a third of it on the coarse one with a spread
of the same size, which is a `6`-class construction being noisier than a `19`-class
one and is reported rather than repaired.

**Then B7-11's loading table came back and it is the most important thing this
stage has produced.**

#### What the two directions actually are

| level | `v1` | `v2` |
|---|---|---|
| `>60%` | **`+0.9917`** | `-0.0697` |
| `50%-60%` | `+0.0579` | **`+0.9920`** |
| every one of the other seventeen | `-0.019` to `-0.037` | `-0.019` to `-0.038` |

**They are not gradients in DTI. They are two near-pure indicator contrasts, each
isolating one single published bucket**, and the two buckets are the two highest.
`43` loads at `-0.0286` and `-0.0208`, which is the same as everything else. The
coarse grid reproduces both at `+0.9973` and `+0.9964`.

#### And those two buckets are the two thinnest in the sample, by a wide margin

| level | loans | share | cells holding it | **loans per cell-class entry** |
|---|---|---|---|---|
| `20%-<30%` | `3,238,092` | `0.202` | `323,815` | `10.00` |
| `30%-<36%` | `3,033,223` | `0.189` | `325,432` | `9.32` |
| `<20%` | `1,040,292` | `0.065` | `272,717` | `3.81` |
| the fourteen integers | `474,187` to `730,209` each | `0.030` to `0.046` | | `2.16` to `2.90` |
| **`50%-60%`** | `131,860` | `0.008` | `96,175` | **`1.37`** |
| **`>60%`** | `35,285` | `0.002` | `29,998` | **`1.18`** |

**The direction ordering is the thinness ordering.** `>60%` is thinnest and is
`v1`; `50%-60%` is second thinnest and is `v2`.

#### The threat, stated as arithmetic

`S(a,a)` is the mean over cells of `gamma(c,a)^2`, and `gamma(c,a)` is built from a
cell-class **mean**. A mean of `n_ca` loans carries sampling noise of order
`Var(a) / n_ca`. At `1.18` loans per entry that is essentially the full residual
variance of **one loan**. At `10.00` it is a tenth of it.

**Noise is independent across entries, so it inflates `S`'s diagonal and not its
off-diagonals. A symmetric matrix with two inflated diagonal entries has
near-indicator eigenvectors on exactly those two coordinates.** That is the
observed pattern, in the observed order.

The arithmetic closes. Taking the flat tail of `0.21` as the noise level of a class
at `2.5` loans per entry gives a single-loan residual variance of about `0.52`.
Scaling that to `1.18` and `1.37` loans per entry gives `0.44` and `0.38`, which is
**not** `1.467` and `0.754`, so the tail's own dispersion does not explain them.
**What would explain them is a single-loan residual variance of about `1.73` for
`>60%` and `1.03` for `50%-60%`, against about `0.52` for the integer classes**, a
ratio of about `3.3` in variance and `1.8` in standard deviation. High-DTI lending
is largely non-qualified and priced far more heterogeneously, so a dispersion ratio
of that size is not exotic. **It is a number, it is measurable in one pass, and
nothing in this stage has measured it.**

#### Why neither null sees it

**The primary null shuffles class labels within a cell.** Under it, the label
`>60%` lands on a randomly chosen loan of that cell, and the cells are overwhelmingly
made of `20%-<30%` and `30%-<36%` loans. So the null's `gamma(c, >60%)` is a
single **typical** loan of that cell, and the observed one is a single **`>60%`**
loan. **If a `>60%` loan is intrinsically more dispersed than a typical loan of the
same cell, the null understates the noise for that class and the estimator reports
a direction.**

**The secondary null shuffles residuals within a cell and has the identical blind
spot.** Both nulls assume loans are exchangeable across classes **within** a cell.
That assumption is exactly what class-specific dispersion violates.

**And the gate does not cover it either.** `matched_sample` draws its noise
homoskedastically, `rng.normal(scale=basis.sd)`, one standard deviation for every
loan. §3.16 named that approximation and left it. So the rank-zero arm established
that a field with **uniform** noise reads back zero on this design. **Whether a
field with the observed class-specific noise reads back zero was never asked**,
and that is the question the whole reading now turns on.

**`S` is a second moment and a second moment cannot separate "this class's mean
moves with the cell" from "this class's mean is one noisy loan".** The estimator
was never able to. Nothing about it is broken; it is being asked a question it does
not answer.

#### B7-12, registered here before it is run

**Step one, deterministic, one pass, no draws.** For each class, report the
within-cell residual dispersion and the within-entry residual dispersion, the
loans per entry, the observed `S(a,a)`, and the noise contribution each dispersion
predicts for that diagonal. The within-cell figure is an **upper** bound on the
noise, because it still contains the class effect and `gamma`; the within-entry
figure is a **lower** bound, and is estimable for every class because even
`>60%` has thousands of entries holding two or more loans.

**Declared before the run.**

| what comes back | reading |
|---|---|
| the **lower** bound already accounts for `S(>60%,>60%)` and `S(50-60%,50-60%)` | **the observed rank two is heteroskedasticity, not interaction.** B7-4 is withdrawn and the stage's reading collapses to zero-versus-non-zero, which Corollary 4 already had |
| the **upper** bound falls short of them | the diagonals carry more than any class-specific dispersion can produce. The rank two survives this threat and the loadings become a finding about the two top buckets |
| the two bounds straddle them | not decisive, and step two is required |

**Step two, only if step one straddles.** Re-run the rank-zero gate arm with
**class-specific** noise: each constructed loan drawn at its own class's measured
within-entry dispersion instead of the pooled one. If a field with no interaction
at all and realistic noise reads back `2` with near-indicator loadings on those two
buckets, the observed `2` is that artefact. Twenty repetitions at fifty draws, one
arm, about ten minutes.

**This is not a defence of the reading and it is not an attack on it.** The
declared table above cuts both ways and step one is a description with no threshold
in it. **It is registered before it is run because that is the only thing that
makes the answer worth having**, and because this stage has now twice discovered
that a table declared in advance on a wrong input protects nothing (§3.11, §3.20).
The input here is a dispersion measured from the same sample the reading comes
from, so there is no separate input to get wrong.

#### What this does not touch

**B7-11's carry result is unaffected.** It is a statement about what a coarsening
does to a direction, and it holds whatever the direction turns out to be. If the
two directions are heteroskedasticity on the two thinnest classes, then what B7-11
measured is that the coarse index preserves those two classes intact and the
complement index merges them away, which is exactly what its partitions do. **The
carry computation was right about the geometry either way.**

**B7-6's status is unaffected.** Fine and coarse agree at `2` whatever the `2` is
made of.

**B7-8's `19/19` becomes a warning rather than a comfort.** The leading loading is
an indicator on `>60%`, and it agrees in sign across the two year-halves because
`>60%` is thin in both halves. **A stability check on a direction cannot
distinguish a stable economic direction from a stable design defect.** That was not
visible before the loadings were printed.

---

### 3.24 §3.23's table is voided as mis-specified. What replaces it needs no bound. 2026-08-16

B7-12 step one returned and its script printed `clear`. **That verdict is not
taken.** Its `clear` branch fired on `>60%` because an upper bound of `1.4469`
was strictly below an observed `1.4471`, a margin of **fourteen parts in a hundred
thousand**, on a criterion written with an exact inequality and no width. §3.23's
table is voided, on three defects, each of which is stated without reference to
any number this arm produced.

#### VOID. The three defects

**1. The upper bound is nearly an algebraic identity exactly where it is needed.**
It is `Var(a) * E[1/n_ca]` with `Var(a)` the dispersion of a class-`a` loan about
its **cell** mean. For a class holding about one loan per entry, `gamma(c,a)` and
`value - cell_mean` are nearly the same quantity, so that product and `S(a,a)` are
nearly the same computation. **The bound carries almost no information for the
thinnest classes, which are the only classes the arm was built to adjudicate.**

**2. The lower bound is estimated on a different population from the one it
bounds.** It uses only entries holding two or more loans of that class. For a
class at one loan per entry those are a small **selected** minority: the cells
where that class is common. `S(a,a)` is dominated by the cells where it is rare.
**The direction of that bias is not signable in advance**, which is worse than a
bias that is.

**3. The table thresholds two defective bounds against `S(a,a)` with exact
inequalities and no width.** That is `MEASUREMENT.md` failure mode 6 with the
tolerance set to zero, and it is the same shape as the unanimity rule §3.15's
VOID 1 struck out: a quantity estimated with error, then compared to a line with
no width.

**All three were available before the arm ran.** None of them needs the result to
be true, and the result only made the third one embarrassing.

#### There is also a systematic correction the prediction omits, and it is visible in the arm's own controls

The alternating centring removes a row mean and a column mean before `S` is
formed, which removes part of the noise. So `E[gamma^2]` is **below** `Var/n` by
roughly one part in the number of classes present per cell. The arm's prediction
does not include it, and on the fourteen integer classes, where signal is
negligible, the predicted lower bound sits **above** the observed diagonal by
about eight to nine percent throughout. **That is the correction showing itself on
the classes where nothing else is happening**, and it is the right size. It is
recorded because it means both bounds are high by about that much, and correcting
it moves the two leading classes in the direction the arm was trying to test.

#### Replacement, and it needs no bound at all

**Noise between entries is independent, so it contributes to `S`'s diagonal and to
nothing else.** A real interaction direction is a set of classes that move
together across cells, which is off-diagonal correlation. So the question "is this
rank two, or is it two noisy classes" is answered by asking **how much of `S` is
off the diagonal**, and it needs no variance estimate, no bound, and no selected
subsample.

**B7-12b, registered here before it is computed.** Report:

* the ratio of off-diagonal to diagonal mass in `S`;
* the correlation matrix `S(a,b) / sqrt(S(a,a) S(b,b))`, its largest off-diagonal
  entry and the distribution of the rest;
* the same two things with the two thinnest classes removed, which says whether
  the remaining seventeen carry any joint structure at all.

**Declared now.**

| what comes back | reading |
|---|---|
| `S` is essentially diagonal, and the leading eigenvector's near-indicator shape is that diagonality showing itself | **there is no interaction for a rank to count.** B7-4 is withdrawn and the stage's reading collapses to zero-versus-non-zero, which Corollary 4 already held |
| `S` carries substantial off-diagonal correlation, and the two leading directions still isolate single classes | the two thinnest classes carry an inflated diagonal **and** there is real joint structure among the rest. The rank is real but its leading directions are not what it says; the reading is taken on `S` with those two classes dropped |
| `S` carries substantial off-diagonal correlation and the leading directions spread across classes | the near-indicator loadings were a property of two classes and not of the field. B7-4 stands as read |

**A near-indicator eigenvector is already most of this answer.** A vector with
`0.99` on one coordinate and `0.02` to `0.04` on the other eighteen says the
leading direction of `S` **is a coordinate axis**, which is what a diagonal matrix
has and what a matrix of correlated classes does not. B7-12b puts a number on it
rather than reading it off a table by eye.

#### And step two, which is now the decisive arm rather than a contingency

**Re-run the rank-zero gate arm with class-specific noise, at both dispersions.**
Each constructed loan drawn at its own class's measured dispersion instead of the
pooled one, once at the within-entry figure and once at the within-cell figure.
The two bracket the truth and **the arm runs the full estimator and its null
rather than an algebraic comparison, so the two bounds' defects bound an outcome
instead of being compared to one.**

| what comes back | reading |
|---|---|
| even at the **lower** dispersion, a field with no interaction reads back `2` with indicator loadings on those two classes | **withdraw B7-4** |
| even at the **upper** dispersion it reads back `0` | the observed `2` is not this artefact |
| they disagree | reported as the interval it is, and the reading is taken on `S` with the two thinnest classes dropped |

One arm, twenty repetitions, fifty draws, twice. About twenty minutes.

#### What this episode is, in one line for `MEASUREMENT.md`

**A criterion that compares an estimated quantity to a line with no width is not a
criterion, however carefully the quantity was defined.** §3.15's VOID 1 struck one
of those and this is the second, written by the same hand eight sections later.

---

### 3.25 B7-12b returned. `S` is diagonal, and B7-4 is withdrawn. 2026-08-16

**§3.24's first row fired.**

| | |
|---|---|
| largest off-diagonal correlation, over all `171` pairs | **`0.1417`** |
| mean absolute off-diagonal correlation | `0.0528` |
| ninetieth percentile | `0.0857` |
| the same three with the two thinnest classes dropped | `0.1417`, `0.0493`, unchanged |
| mean magnitude, diagonal entry | `5.3444 / 19` = `0.2813` |
| mean magnitude, off-diagonal entry | `4.2893 / 342` = `0.0125`, **`4.5%`** of the diagonal |

`>60%` correlates with the other eighteen classes between `-0.045` and `-0.127`,
`50%-60%` between `-0.043` and `-0.102`, and the two correlate with **each other**
at `+0.031`. Every one of those is the small negative correlation that column
centring forces on any set of centred columns. **There is no pair of classes in
this sample that moves together.**

#### And the arithmetic that closes it

Drop the two thinnest classes and take the spectrum of the remaining `17 x 17`:

```
0.2770   0.2241   0.2199   0.2156   0.2125   0.2097
```

against the full nineteen-class spectrum

```
1.4674   0.7544   0.2768   0.2240   0.2199   0.2155
```

**The seventeen-class spectrum is the nineteen-class one with its first two
entries removed.** Flat, and its largest entry `0.2770` sits **below** this
design's own `null_max` of `0.3817`. **With `>60%` and `50%-60%` removed, the
observed rank is zero.**

`S` is a diagonal matrix of nineteen independent class noise levels. Its
eigenvalues are its diagonal entries in order, its eigenvectors are coordinate
axes, and the two that clear the null are the two classes holding `1.18` and
`1.37` loans per cell-class entry, which are exactly the two classes for which
§3.23 shows the permutation null is biased low.

#### The reading, as declared in §3.24 before this was computed

> `S` is essentially diagonal, and the leading eigenvector's near-indicator shape
> is that diagonality showing itself → **there is no interaction for a rank to
> count. B7-4 is withdrawn and the stage's reading collapses to zero-versus-non-
> zero, which Corollary 4 already held.**

**B7-4 is withdrawn.** Not qualified, not scoped, withdrawn. The stage has no
rank to report.

#### What this does to everything else in the stage

**Every rank-type result in B7 is the same two diagonal entries seen from a
different angle**, and each one now reads as a fact about those two classes:

* **B7-11's carry result** is unaffected as geometry and its object was noise. The
  coarse grid keeps `>60%` and `50%-60%` as groups of their own, so it keeps both
  diagonal entries and reads `2`; the complement grid merges them into its single
  `BUCKET` group and reads `0`. **"The interaction is a bucket-level object" is
  "the two thin classes are their own buckets."** The carry computation was right
  about what a coarsening does and the direction it carried was an artefact.
* **B7-6** compared two grids that both keep those two classes apart. It passes
  and it was never testing anything else.
* **B7-7's nine arms** all read `2` because all nine keep those two classes.
* **B7-8's `19/19` and `|cos| = 0.9991`** are the stability of an indicator on
  `>60%` across two halves in which `>60%` is thin in both. **A stability check
  cannot distinguish a stable direction from a stable defect**, which §3.23 said
  and this confirms.
* **B7-10's `0`** on the complement grid is correct and now trivial.
* **The gates are unaffected and were never wrong.** They established that this
  design recovers a constructed rank under **homoskedastic** noise, which it does.
  §3.16 named the homoskedasticity as an unfixed approximation and that was the
  approximation that mattered.

#### What is untouched

**`b1_theorem.md` Corollary 4 and stage B2 are untouched.** Corollary 4 is a
theorem about the framework, not a measurement, and B2's within-cell variance is a
1-skeleton quantity that contains no rank. **B7-9's `0.3036`** is a variance share
and stands.

**Nothing outside B7 rests on B7-4.** `b8_fannie_slice.md` and
`b9_zero_holonomy.md` cite B7's **grid dependence**, and §3.22's carry numbers
support that citation whatever the direction turns out to be, since a coarsening
that annihilates a direction annihilates it whether the direction is signal or
noise.

#### What the stage's binding constraint actually was

§3.5 said **fill**. §3.7 corrected it to the **co-occurrence counts**. Both were
wrong, and the third answer is the one that decided the stage:

> **The loans per cell-class entry, class by class.** A class index whose tail
> classes sit at one loan per entry gives `S` a diagonal that no permutation null
> on this design can reproduce, because the null replaces a thin class's loan with
> a typical loan of the same cell.

Neither of the first two answers is a function of the class-level counts at all.
`0.7222` fill and `326,872` cells describe a design that looks generous and holds
two classes at `1.18` and `1.37` loans per entry. **The sufficient statistic for a
rank on an incomplete design is the per-class entry depth, and this repository
found it by having a reading die on it.**

#### B7-13, the confirmation, registered before it is run

**One thing is still an inference rather than a measurement.** B7-12b shows `S` is
diagonal and shows the two exceedances sit on the two classes where the null is
biased low. It does not **build** a field with no interaction and show that it
reproduces `1.4674` and `0.7544`.

**B7-13.** Re-run the rank-zero gate arm with class-specific noise, each
constructed loan drawn at its own class's dispersion, once at the within-entry
figure and once at the within-cell figure. One arm, twenty repetitions, fifty
draws, twice.

| what comes back | reading |
|---|---|
| a field with **no interaction** reads back `2` with indicator loadings on those two classes, at either dispersion | the mechanism is confirmed and B7-4's withdrawal is a measurement rather than an inference |
| it reads back `0` at both | **the withdrawal stands on §3.24's declared table regardless**, because a diagonal `S` has no interaction for a rank to count whatever produced its diagonal. What would change is the explanation, and the explanation would then be unknown and said to be |

**The withdrawal does not wait for it.** §3.24's table was declared before B7-12b
ran and its first row fired. B7-13 explains; it does not license.

---

### 3.26 Self-check of §3.21 through §3.25. One hole, one over-statement, and three things that hold. 2026-08-16

Asked directly whether the correction itself could be wrong. Five load-bearing
claims, attacked one at a time.

#### Holds. The partition bug, and the fix

The code order is `41, 36, 30%-<36%, 39, ...` and the stored order was
alphabetical; `levels_by_code` sorts the lookup by its **value**, which is the
code, so it returns names indexed by code. That is the correct direction and the
membership printout shows the intended grid.

**And there is an independent confirmation nobody asked for.** The pre-fix coarse
grid read `1` with spectrum `1.45, 0.2195, 0.2087, 0.203`. Under the scramble,
positions `2` to `15` of the alphabetical list were merged, and in code order those
positions hold `50%-60%` but **not** `>60%`, which sat alone at code `18`. So the
scrambled grid kept `>60%` apart and buried `50%-60%` in the blob. **That predicts
exactly one surviving direction at about `1.45` and a tail at the noise floor,
which is what it returned.** The bug and §3.25's diagnosis together retrodict the
pre-fix numbers quantitatively. Neither was fitted to them.

#### Holds. `S` is diagonal

Largest off-diagonal correlation `0.1417` over `171` pairs, mean `0.0528`, and the
off-diagonal entries are `4.5%` of the diagonal per entry. **The objection worth
raising is that the alternating centring induces negative correlations and might
be masking positive ones.** It does induce them, and the observed off-diagonals
are all small and negative, which is the constraint alone. Centring removes a
column-constant component, which is a class main effect and not an interaction; it
does not cancel correlation among the residual columns. The claim stands.

#### **A hole. §3.25 compared a seventeen-class spectrum to a nineteen-class null**

§3.25 wrote that dropping `>60%` and `50%-60%` leaves a spectrum topping out at
`0.2770` against a `null_max` of `0.3817`, "which is rank zero".

**`0.3817` is the nineteen-class design's null and it does not belong to the
seventeen-class design.** A null belongs to the design it was drawn on. Dropping
those two classes removes the two largest noise sources and shrinks the matrix, and
both push a permutation null **down**. So the threshold that comparison used is
expected to be too high, in the direction that makes the conclusion easier.
**That is the same defect §3.16 and §3.21 were both about, committed inside the
section that corrected them.**

**B7-14, the correction.** Drop those two classes' loans, renumber, **re-apply
`MIN_CELL_SIZE`** so the result is a legitimate design rather than a submatrix,
and estimate its rank against **its own** null. Registered here; the number goes
into §10.2 and §10.5 and **§3.25's sentence is not to be quoted until it is
there.**

**What does not move.** The two claims that carry the withdrawal are that `S` is
diagonal and that its two clearing eigenvalues are the diagonal entries of the two
classes for which the null is biased low. Neither uses the seventeen-class
comparison. **B7-4's withdrawal does not depend on the hole**, and the sentence
that does is being repaired rather than defended.

#### **An over-statement. "There is no interaction for a rank to count"**

§3.24's first row says that and §3.25 quotes it. **It is stronger than what was
measured.**

A diagonal `S` whose entries all sat **above** the noise level would be an
interaction of rank nineteen, not of rank zero: every class varying with the cell,
independently of every other. The estimator would report nineteen. It reported two,
which says seventeen diagonal entries are at the noise level **and says nothing
about whether the remaining two are**.

**The precise claim, which replaces it.** `S` carries no structure **shared across
classes**: no pair of the nineteen moves together beyond `|r| = 0.1417`. Whether
any individual class carries its own cell-specific variation is **not separable
from that class's own sampling noise on this design**, and for the two classes
where the reading came from, the null is known to be biased low by construction.

**B7-4's withdrawal is unchanged.** A rank is a count of shared directions and
there are none to count. What is withdrawn is the over-statement about the world,
which said "no interaction" where the evidence says "no measurable shape, and one
class's own variation is confounded with its own thinness".

#### A sixth claim, made in conversation and not in this document, and it was wrong

**Said while answering what B7's death means for B1: "B-track still has no
measurement that is not an identity."** That is false and the way it was reached
is worth more than the correction.

**The chain.** `b1_theorem.md` §12 withdraws the **curl/harmonic split**, because
filling the squares reports curl `100%` and harmonic `0%` and that is an identity
dressed as a measurement. §12.2 was then added **to save the within share from
that withdrawal**: Theorem 3's quantity contains no 2-cells, so the within share
is a function of `(Gamma's 1-skeleton, omega)` alone and is invariant under every
choice of `C2`. **The invariance argument exists to show the within share is
untouched.** `claude/根本性问题审查_v1.md` read it as showing the within share
**is** an identity, which is the sign reversed; that document cites it as "B2
§12.2" while `b2_measurement.md` ends at §11; and that document's own §七 states
that its §二·4 is a second-hand reconstruction with the originals unread. **This
stage picked up the reconstruction, dropped the caveat it carried, and built a
stronger claim on top of it.** Three steps, each stronger than the last.

**What `b1_theorem.md` actually concedes is narrow and immediately bounded.**
Theorem 3's **number** equals stage B2's within-cell variance to `1e-16`, so
citing it as a new quantity is citing an analysis of variance. The same passage
says Corollary 1 cannot be dissolved by renaming. **What is conceded is quoting
Theorem 3's number as an increment. What is not conceded is stage B2.**

**Checked at source rather than relayed**, `results/b2_placebo_products.json`:

| | conventional | VA | FHA |
|---|---|---|---|
| within share | **`0.847959`** | `0.666584` | `0.475714` |
| restricted to common tract-years | `0.860806` | | `0.474659` |
| rank decomposition | `0.818060` | `0.732534` | `0.552458` |

`conventional - VA = 0.181375` against a `registered_min_gap` of `0.05`, and the
same sign survives the rank decomposition at `0.085526`. `FHA - VA = -0.190870`,
registered in advance as predicted by neither direction and reported unexplained.

**An identity cannot tell you which of two products has the larger within share.**
It tells you what a within share equals. And the split-half zero calibration is
the direct refutation: if the quantity were forced by its definition, splitting
the same product at random would produce the definitional thing, and its largest
gap over twenty splits is `0.0014` against an observed `0.1814`.

**B3 was omitted from the claim as well.** `results/b3_cip_slice.json`, `1,513,471`
rows from Du, Keerati and Schreger (2025), verdicts B3-1 through B3-8 all true.
Its `worst_identity_error` of `7.41e-16` is a per-band zero calibration and not its
headline, and reading it as the headline is the same substitution.
`PROJECT_PLAN.md` §21.14 already logged that omission once as a factual error.
**This stage committed it again**, which is what a lesson recorded in one place and
not carried into another looks like.

**The defensible version of what was said, and it is a different claim.**
Theorem 3's number carries no increment over an ANOVA, so it should not be cited
as one. And B2's product gap and B3's slice holonomy are real measurements whose
problem is **load-bearing**, not identity: whether a competing model predicts the
same ordering. That is what `根本性问题审查_v1.md` §一 actually establishes, and it
is a serious problem. **Substituting "it is an identity" for "it is not
load-bearing" makes an unproven conclusion look proven**, and it does so in the
direction of the speaker's own argument.

**Nothing above softens B7.** The rank died and the five claims checked in this
section stand as written.

#### Holds, and it is the one that matters. There is a live alternative and B7-13 is aimed at exactly it

**"The two thin classes carry a real cell-specific interaction, and they clear the
null because their interaction is genuinely large, not because their noise is."**
High-DTI lending is largely non-qualified and priced by market and vintage far
more variably than conforming lending, so both its interaction **and** its noise
are plausibly large, and `S` cannot separate them.

That reading is not excluded by anything in §3.25. **It is exactly what B7-13
tests**, by building a field with **zero** interaction at each class's own measured
dispersion and asking whether it reproduces `1.4674` and `0.7544`. The arm was
registered before this self-check and its declared table already covers both
outcomes.

**One note on which way the thinness cuts.** If the interaction were real and
per-class, the classes that clear the null first would be the ones with the best
signal-to-noise, and the thin classes have the **worst**. Them clearing first is
the wrong way round for the real-interaction reading and the right way round for
the noise reading. **That is an argument and not a measurement**, which is why
B7-13 is run.

---

### 3.27 B7-13 returned at both brackets. The withdrawal is a measurement. B7-14 returned `1`, and B7-15 is registered. 2026-08-16

#### B7-13. A field with no interaction at all reads back `2`, twenty times out of twenty, at both brackets

| | lower bracket (within-entry) | upper bracket (within-cell) |
|---|---|---|
| reads exactly `2` | **`20/20`** | **`20/20`** |
| recovered `lambda_1` | `0.9137 ± 0.0079`, **`0.623x`** observed | `1.3945 ± 0.0133`, **`0.950x`** observed |
| recovered `lambda_2` | `0.6164 ± 0.0028`, **`0.817x`** observed | `0.7007 ± 0.0031`, **`0.929x`** observed |
| leading direction | `>60%`, `20/20` | `>60%`, `20/20` |
| second direction | `50%-60%`, `20/20` | `50%-60%`, `20/20` |

**The constructed field has zero interaction.** Its only departure from a pure
additive fit is that each loan's noise is drawn at its own class's dispersion
instead of the pooled one. The class dispersions it used are `0.53` to `0.59` for
seventeen of the nineteen classes, `0.86` and `1.00` for `50%-60%` and `>60%` at
the lower bracket, and `0.92` and `1.25` at the upper.

**§3.25's declared first row fired at both brackets, which is more than it asked
for.** It required the reading at either. **B7-4's withdrawal is now a measurement
and not an inference.**

**And the magnitudes are not approximate.** At the upper bracket a field with no
interaction reproduces `95.0%` of the observed `lambda_1` and `92.9%` of the
observed `lambda_2`, with the identical eigenvector structure, twenty times out of
twenty with a spread under `1%`. **What is left over is five and seven percent, and
it is not attributed to anything.** The constructed noise is homoskedastic *within*
each class and the real dispersion is not, so a residual of that size is inside the
construction's own model error; that is a reason not to claim the residual is
interaction, and it is not a demonstration that it is not.

#### B7-14. §3.26's hole was real, and closing it changes the answer

The seventeen-class design, rebuilt with the two thinnest classes' loans removed,
cells renumbered and `MIN_CELL_SIZE` re-applied: `323,830` cells, `15,811,056`
loans.

```
spectrum   0.27553  0.22319  0.21932  0.21483  0.21160  0.20881
its own null_max   0.23332       ->   rank 1
```

**§3.25 said "rank zero" by comparing `0.2770` to the nineteen-class design's
`0.3817`. Its own null is `0.2333`, and `0.2755` clears it.** §3.26 predicted both
the direction and the reason: dropping the two largest noise sources and shrinking
the matrix pushes a permutation null down, so the threshold §3.25 used was too
high in the direction that made its conclusion easier. **The self-check was right
and the section it corrected was wrong.**

**So one direction survives, by `18%`.** Margin `0.2755 / 0.2333 = 1.18`. Nothing
below it clears: `0.2232`, `0.2193`, `0.2148` are all under the null.

#### A recording omission, and it is the second time

**The first version of B7-14 stored the rank and left the leading loading unset**,
so the direction that survived could not be read. That is exactly the omission
already on this stage's outstanding list, where the complement grid's eigenvalues
were not recorded and only its rank was, and it was committed a second time in the
section that was correcting a different error. **A rank with no loading behind it
cannot be read**, and §3.22's loading table is the whole reason this stage knows
what it knows. `b7_hetero.py` now prints and stores the seventeen-class `v1` and
`v2` by level.

#### B7-15, registered here before it is run

**The residual `1` gets the same treatment as the `2` did, and it gets it before
anyone says what it is.** `b7_class_noise.py --drop-thinnest 2` rebuilds the
seventeen-class design the same way B7-14 does and runs the rank-zero arm on it at
both class dispersions.

| what comes back | reading |
|---|---|
| a field with no interaction on the seventeen-class design reads back `>= 1`, at either bracket | the residual is the same artefact one rung down. **The stage has no reading at any class resolution**, and the withdrawal is total |
| it reads back `0` at both brackets | the residual `1` is not this artefact. **It is then the first surviving rank-type reading this stage has**, and it must be quoted with its margin of `1.18`, with its loading, and with the observation that it appears only after two classes are removed by a rule this stage wrote |
| the brackets disagree | reported as the interval, and nothing is read from it |

**The candidate is named in advance.** After `>60%` and `50%-60%`, the thinnest
class is `<20%` at `3.81` loans per entry, and it is the only other class whose
`S(a,a)` exceeded both of §3.23's bounds, by about `39%`. **If the seventeen-class
leading loading is an indicator on `<20%`, the first row above is the reading
whatever B7-15 returns.** Naming it now is what keeps that from being a story told
after the fact.

**What does not wait for B7-15.** B7-4 was the reading of `2` on the nineteen-class
grid, and B7-13 killed it at both brackets. Nothing below can restore it.

---

### 3.28 B7-15 returned. Two rows of its table fire at once, the brackets are not brackets, and one number is missing. 2026-08-16

```
seventeen-class observed      lambda1 0.2755   its own null_max 0.2333   margin 1.181

within_entry ("lower")   reads [1,1,1,1,1]   lambda1 0.2189 +- 0.0009   null ~0.2159   margin 1.014
within_cell  ("upper")   reads [0,0,0,0,0]   lambda1 0.2127 +- 0.0009   null ~0.2169   margin 0.981
leading direction of the constructed field, both arms   `46`, 10 of 10
```

#### The table is not exclusive, and that is the third one this stage has written badly

§3.27's first row fires on "reads back `>= 1`, **at either bracket**", and the
within-entry arm reads `1` five times out of five. §3.27's third row fires on "the
brackets disagree", and they do. **Both rows fire and they say opposite things.**

Rows written as "at either" and rows written as "they disagree" are not disjoint,
which was true when it was written and needed no result to see. **This is the
third mis-specified criterion table in this stage**, after §3.20's control
(a quantifier error) and §3.23's bounds table (a zero-width threshold). All three
were written by the same hand across sixteen sections, and the pattern is worth
more than any of them: **a declared outcome table protects nothing if its rows are
not checked for exclusivity and exhaustiveness before it is declared.**

**Neither row is taken.** Picking the one that suits the argument is exactly what
the table exists to prevent.

#### The brackets are not brackets, and §3.24 predicted it

`within_cell` was called the **upper** figure because dispersion about the cell
mean still contains the class effect and `gamma`. **For five of the seventeen
classes it is the smaller of the two**: `45`, `46`, `47`, `48` and `49` all have
`within_cell` below `within_entry`.

§3.24 named the reason when it voided the bound comparison: **the within-entry
figure is estimated only on entries holding two or more loans of that class, which
is a selected subsample, and the direction of that selection is not signable in
advance.** For a class at about `2.2` loans per entry, the entries holding two or
more sit in the denser cells, and those are more dispersed. **The bias runs the
other way there, and it has now shown itself.**

**So the two arms are not a bracket. They are two estimates with opposite
selection problems**, and the names `lower` and `upper` are struck. That the
larger-noise arm produced the **smaller** `lambda_1` is the same fact seen from the
other side: `within_cell` is not uniformly larger.

#### What is measurable, with no row taken

**Class-specific noise alone, on the seventeen-class design, produces a leading
eigenvalue that sits within `1.4%` of its own null on one arm and `2%` below it on
the other. The observed one sits `18%` above.** That is an order of magnitude in
margin, and it is the comparison that matters, not the `1` and the `0`.

**And in both arms the constructed leading direction is `46`, ten times out of
ten.** The seventeen-class observed leading direction **is not recorded**, because
`b7_hetero.py`'s fix for that omission has not been re-run.

#### The one number that decides it, named before it is in

**If the observed seventeen-class leading direction is `46`, the residual is the
same artefact one rung down** and the `18%` margin is then a magnitude question
about one class rather than a direction to be read. **If it is anything else**, the
constructed artefact and the observed reading are different objects and the
residual survives this arm.

**That is the reading, declared here before the number exists**, and it replaces
§3.27's table rather than repairing it. It has one condition, it is exclusive, and
it is exhaustive.

#### What does not move

**B7-4's withdrawal.** It is the nineteen-class reading of `2`, and B7-13 settled
it at both class dispersions with `20/20` and `20/20`, `95.0%` and `92.9%` of the
observed eigenvalues, and the identical eigenvector structure in all forty
repetitions. Nothing in this section touches it.

---

### 3.29 The deciding number. B7 closes with no reading at any class resolution. 2026-08-16

```
seventeen-class observed  v1:  <20%  +0.9575    every other level  -0.0019 to -0.0929
                          lambda1 0.2755   its own null 0.2333   margin 1.181
constructed, class noise  leading direction `46` in 10 of 10
                          lambda1 0.2189 / 0.2127   margins 1.014 / 0.981
```

**A near-pure indicator again**, the third one, on `<20%`.

#### Which declaration governs, and neither is taken

§3.28's test was `46` against not-`46`, and the answer is not-`46`, so by its letter
the residual survives. **That test does not govern.** It was written after the
constructed run reported `46`, and it made that incidental output the comparison.
**Anchoring a test on a result is available to see when it is written**, and it is
the fourth criterion this stage has written badly.

§3.27 is earlier, more specific, and named `<20%` **by name before any of this
ran**: "if the seventeen-class leading loading is an indicator on `<20%`, the first
row above is the reading whatever B7-15 returns." That is the more binding
declaration.

**But §3.27's stated reason for naming it is factually wrong.** It called `<20%`
"the thinnest class" after the two dropped. It is not. `<20%` holds `3.81` loans
per cell-class entry against `2.16` to `2.90` for the fourteen integers. **It named
the right class for the wrong reason**, and the constructed artefact leads on `46`
at `2.16`, the class that is actually thinnest, which is what the thinness story
predicts and is not what the observation shows.

**So neither declaration resolves it and neither is taken.** What is on the record
is what was measured.

#### What was measured

* the observed seventeen-class `lambda_1` is `0.2755` on `<20%`, `1.181` times its
  own null;
* class-specific noise alone gives `0.2189` and `0.2127`, margins `1.014` and
  `0.981`, leading on `46` in ten of ten;
* `<20%` is the one class whose `S(a,a)` of `0.2614` exceeds **both** of §3.23's
  dispersion predictions, `0.1685` and `0.1880`, by about `39%`. Every other class
  sits at or below its own prediction.

**The residual is one class's diagonal entry**, and `S` is still diagonal with
`<20%` in it: the largest off-diagonal correlation over all `171` pairs is
`0.1417`.

#### Why that closes the stage rather than reopening it

**A rank of one on a diagonal matrix is one coordinate axis clearing a threshold,
and a coordinate axis is not a ladder.** §5's trichotomy asks how many independent
directions the class space carries. One class's own variance, uncorrelated with
every other class at `|r| <= 0.1417`, is not a direction in that sense and cannot
be read as one however large its margin.

**B7 closes with no reading of §5's trichotomy at any class resolution.** B7-4 is
withdrawn and nothing replaces it.

#### One post-hoc candidate, registered as post-hoc and not offered as a reading

The three classes with excess diagonal are `<20%`, `50%-60%` and `>60%`, and those
are the three whose published bucket spans the widest range of underlying DTI: the
integers span one point each, `30%-<36%` six, `20%-<30%` ten, and those three span
twenty, ten and unbounded. A cell-class mean of a few loans drawn from a wide range
is a noisy estimate of a heterogeneous group, and that is **within-class
heterogeneity, not a cell-by-class interaction.**

**§3.9's fence applies in full.** This is a story told after the numbers, it may
not be offered as the reading, and it is not measurable on this file at all: HMDA
publishes exact DTI only inside `36` to `49`, which is precisely the range where
there is no excess. **It is registered as a candidate for a carrier with continuous
DTI and for nothing else.**

---

## 4. The null, which the data supplies

`MEASUREMENT.md` checklist item 7 requires an arm whose true value is known.
Here it is a permutation with the right invariances.

**Primary null: class labels permuted within cells.** For each cell, the class
labels of its loans are shuffled among those same loans. This preserves the cell
size, the class counts in that cell, the within-cell dispersion and the entire
missingness pattern. **It destroys only the one thing at issue: whether a class's
position in a cell travels to other cells.** The permuted data then runs the
identical code path, including the same centring iteration, so any bias the
centring leaves is present in the null as well.

The null statistic is the **largest eigenvalue of `S` over the permutation
draws**, so no percentile and no threshold is chosen by this project. The draw
count is computational and is reported with the result.

**This null is conservative in the direction of the interesting claim.**
Permuting labels within cells redistributes the class main effect `A(a)` across
cells, which adds variance to the null and makes its largest eigenvalue larger
than a null with `γ = 0` alone would give. Fewer observed eigenvalues clear a
larger bar, so the estimated rank is biased **down**, and the interesting reading
in §5 is `rank ≥ 2`. Stated here so that a `rank ≥ 2` result cannot be attributed
to a loose null.

**Secondary null: residuals permuted within cells.** The additive model is fitted
first and the residuals are shuffled within cells, which removes the `A(a)`
redistribution above. Registered as an arm and not as a replacement, because §6
makes the two nulls agreeing a criterion.

---

## 5. What each answer means, declared before the run

| estimated matrix rank | reading, fixed here |
|---|---|
| **0** | No interaction structure survives the null on this class index. The dispersion B2 measured is real and is **not carried by any borrower coordinate the public file holds**. The agent-index attribution would then rest entirely on `b2_measurement.md` §8.1's graded placebo and this stage adds nothing to it |
| **1** | **One ladder.** A single scalar per DTI level and a single scalar per cell reproduce the interaction. The mortgage carrier's square summand compresses to a one-dimensional stratification model, which is what standard practice already builds, and `b1_theorem.md` §13.4's first row is the whole story on this carrier |
| **≥ 2** | **No single ladder.** The disadvantaged class is not the same class across cells. This is content no one-dimensional model expresses, and it is the mortgage carrier's non-substitutable claim |

**All three are publishable and none is a failure of the stage.** This is written
here because the temptation, if the answer comes back `1`, will be to look for a
class index under which it comes back `2`, and §2 exists to make that visible if
it happens.

---

## 6. Pre-registered criteria

**B7-1 — the estimator recovers a known rank.** On synthetic fields built with
`γ` at rank `0, 1, 2, 3`, with the observed cells' own missingness pattern
imposed, the estimator returns the constructed rank. **A floor: failure here
voids everything after it.**

**B7-2 — the additive null returns zero.** On a synthetic field with `γ = 0` and
non-trivial `A(a)` and `φ(c)`, the estimated rank is `0` through the full code
path, not short-circuited.

**B7-3 — the permuted data returns zero.** The permuted matrix's own estimated
rank, computed through the identical path, is `0`. This is the null checking
itself and it is the analogue of `b3_cip_slice.md`'s B3-2.

**B7-4 — the estimate.** The number of eigenvalues of `S` exceeding the largest
eigenvalue over the permutation draws, on the primary class index of §2.2. **This
is the stage's number.** Its three readings are in §5 and no threshold is
attached to it.

**B7-5 — the answer does not live in the null.** The primary and secondary nulls
of §4 agree on which of the three readings in §5 applies. Disagreement means the
null is doing the work; reported as null-dependent and the headline withdrawn.

**B7-6 — the answer does not live in the class grid.** The DTI-only arm of §2.2
and the DTI × LTV arm of §2.3 agree on which of the three readings applies. They
will not agree on the integer, since the two grids have different maximum ranks,
and agreement is required on the trichotomy only.

**B7-7 — the answer does not live in the spread band.** The reading is unchanged
across `BOUND_SWEEP`, and the rank-**transformed** arm gives the same reading.
Same discipline as `b2_measurement.md` §10.3 and `b3_cip_slice.md` §7: the
headline is the widest band at which the reading is unchanged.

**B7-8 — selection axis disjoint from test axis.** The leading eigenvector's
class loadings are estimated on odd activity years and their signs checked on
even years, with agreement required on more than half the classes. Estimating and
testing on the same rows would make part of any agreement a property of the
selection. Borrowed from `b3_cip_slice.md` B3-6.

**B7-9 — reported, not gated: how much of B2's within term this touches at all.**
Before any rank is read, report the share of the within-cell variance that the
labelled class index accounts for, and the number of distinct DTI levels present
in the median cell.

**This one is not optional and it is why the stage could be uninformative even if
B7-4 returns a clean number.** `A3-8_作用域诊断_v1.md` §5 is the rule: a treatment
that barely varies on the measured population reads as zero, and the zero carries
no information about the mechanism. Here the mirror case is live. If DTI levels
account for a sliver of the within-cell dispersion, then the rank of that sliver
is a fact about the sliver, and the number must be printed next to the rank
rather than in a footnote.

---

## 7. Falsification

| observation | consequence |
|---|---|
| B7-1, B7-2 or B7-3 fails | the machinery is wrong; nothing after it may be read |
| B7-5 fails | the reading is null-dependent; the headline is withdrawn and both nulls are reported |
| B7-6 fails | the reading is grid-dependent; both grids are reported and no trichotomy is claimed |
| B7-7 fails | the reading lives in the spread band, which is the failure `b2_measurement.md` §10 already registered for stage B2 and it propagates here |
| B7-8 fails | the leading direction is not stable across years and no class ordering may be named, whatever the rank |
| the largest **negative** eigenvalue of `S` exceeds the null in absolute value | the missingness pattern is generating structure. The pairwise-complete estimator is not usable on this design and the stage reports that rather than a rank |
| B7-9 shows the class index accounts for a negligible share | **the rank is reported and explicitly declared uninformative about the mechanism.** Not suppressed, and not promoted either |
| B7-4 returns `1` and a second class index is then tried | a process failure, not a data failure. §2 fixes the indices in advance and §5 declares `1` publishable, so trying a third grid after seeing `1` is choosing the answer |

---

## 8. What this stage cannot establish

**It does not test Theorem 1, Corollary 1 or Corollary 4.** Those are settled. A
rank of `1` would not restore the one-index null: `γ ≠ 0` either way, and a single
non-zero interaction term is still enough.

**It says nothing about the slice summand.** By `b1_theorem.md` Corollary 2 the
mortgage carrier cannot reach it, and stage B3 is where it lives.

**Its two possible readings are not symmetric in strength, and this is the most
important limitation.** The public file does not contain a credit score;
twenty-seven fields are redacted. So:

- `rank ≥ 2` is **informative**, because a second dimension found using only DTI
  and LTV would still be there if a credit score were added.
- `rank ≤ 1` is **bounded by the file**, because the coordinate most likely to
  carry a second dimension is the one the regulator removed.

A `1` therefore reads as "one ladder **in the coordinates the public file
carries**", and any sentence reporting it must carry that clause. FHFA's NMDB
publishes rates by credit-score band but not at loan level, so the restriction is
a property of the public data and not of the question.

**It carries no welfare content.** That the disadvantaged class differs across
markets is a statement about the shape of a field. It does not say anyone behaves
badly, and no step toward that is taken here.

---

## 9. Order of execution

1. **This document.** Fix the class indices, the estimator, the nulls and the
   readings. Done.
2. **B7-1 to B7-3** on synthetic fields, before any HMDA row is loaded. If any
   fails, stop and fix the estimator with the criteria untouched.
3. **B7-9** on the real sample, before any rank is read, so that the stage knows
   how much of B2's within term it is talking about before it starts talking.
4. **B7-4** on the primary index, then **B7-5 to B7-8**.
5. Write results, including any falsification in §7 that fired.

**What was known when this was written.** The twenty column names in §2.1, the
distinct published values of `debt_to_income_ratio` and their relative frequency
in one state-year file, stage B2's published within shares, and stage B3's
published figures. **No value of `γ`, of `S`, or of any eigenvalue has been
computed.** If that seems a thin line, it is the same line `b3_cip_slice.md`
§10.2 drew, and stating where it falls is what makes it a line.


---

## 10. Results

**Rewritten 2026-08-16 after §3.21 and §3.25. The superseded §10 is kept whole and
unedited as §10.9**, because nothing in this repository is deleted and because the
record of what the stage said before is what shows where the error entered.

**The verdict in one line. B7 has no rank to report.** What the estimator returned
was two diagonal entries of `S`, belonging to the two DTI classes that hold about
one loan per cell-class entry, and `S` carries no off-diagonal structure at all.
**B7-4 is withdrawn.** What the stage delivers instead is a measurement of its own
instrument's binding constraint, which turned out to be worth more than the reading
would have been.

Records: `results/b7_design.json`, `b7_gate_draws50_reps20.json`,
`b7_gate_coarse_draws50_reps20.json`, `b7_rank_draws50.json`, `b7_carry.json`,
`b7_hetero.json`, `b7_calib_check_fine.json`, `b7_robustness_rank_draws50.json`,
`b7_robustness_census.json`. Eight superseded records carry the suffix
`.expired_20260816_pre_partition_fix`.

### 10.1 The sample, the design, and the number that decided the stage

| | |
|---|---|
| files retrieved / loans parsed | 408 / **20,071,900** |
| dropped, blank DTI | 164,692 |
| dropped, filer-exempt DTI | 4,253 |
| loans after the band and the cell-size filter | **16,035,398** |
| cells | **326,872** |
| class levels (the regulator's published DTI partition) | **19** |
| fill of the cell-by-class design | **0.7222** |
| distinct classes per cell, min / q1 / median / q3 / max | 3 / 12 / **14** / 16 / 19 |

`20,071,900` matches the count recorded in `effective_price.SPREAD_BOUND`'s own
docstring digit for digit, which is how this stage confirms it is on stage B2's
sample rather than asserting it.

**B7-9, reported and not gated: the class index carries `0.3036` of stage B2's
within-cell term.** The variance decomposition it comes from is exact to `2.8e-17`,
which it should be, being an identity. **This number stands.** It is a variance
share and contains no rank.

**And the number none of the above shows.** Loans per cell-class entry, by class:

| class | loans | share | cells holding it | **loans per entry** |
|---|---|---|---|---|
| `20%-<30%` | 3,238,092 | 0.202 | 323,815 | 10.00 |
| `30%-<36%` | 3,033,223 | 0.189 | 325,432 | 9.32 |
| `<20%` | 1,040,292 | 0.065 | 272,717 | 3.81 |
| the fourteen integers `36` to `49` | 474,187 to 730,209 each | 0.030 to 0.046 | 219,851 to 264,618 | **2.16 to 2.90** |
| **`50%-60%`** | 131,860 | 0.008 | 96,175 | **1.37** |
| **`>60%`** | 35,285 | 0.002 | 29,998 | **1.18** |

**A fill of `0.7222` over `326,872` cells describes a design that looks generous
and holds two of its nineteen classes at about one loan per entry.** That is the
statistic the stage turned on and it appears in none of the design summaries above.

### 10.2 What the estimator returned, and what it was

| grid | levels | primary null | residual null | spectrum | `null_max` |
|---|---|---|---|---|---|
| fine | 19 | **2** | **2** | `1.4674  0.7544  0.2768  0.2240  0.2199` | `0.3817` / `0.3806` |
| coarse | 6 | **2** | **2** | `1.4526  0.7490  0.2622  0.0745  0.0559` | `0.3784` |
| complement | 15 | **0** | **0** | `0.2241  0.2199  0.2156  0.2125  0.2097` | `0.2405` |

**Then the eigenvectors were printed for the first time** (B7-11, §3.22):

| level | `v1` | `v2` |
|---|---|---|
| `>60%` | **`+0.9917`** | `-0.0697` |
| `50%-60%` | `+0.0579` | **`+0.9920`** |
| every one of the other seventeen | `-0.019` to `-0.037` | `-0.019` to `-0.038` |

**Two near-pure indicator contrasts, each isolating one class, and the two classes
are the two thinnest.** `43` loads at `-0.0286` and `-0.0208`, the same as
everything else.

**And then `S` was looked at directly** (B7-12b, §3.25):

| | |
|---|---|
| largest off-diagonal correlation, over all 171 pairs | **`0.1417`** |
| mean absolute off-diagonal correlation | `0.0528` |
| mean magnitude, off-diagonal entry, against diagonal | **`4.5%`** |
| spectrum with `>60%` and `50%-60%` removed | `0.2770  0.2241  0.2199  0.2156  0.2125` |
| the seventeen-class design against **its own** null (B7-14) | spectrum `0.2755  0.2232  0.2193  0.2148`, `null_max` `0.2333`, **rank 1**.  §3.25 said rank zero by using the nineteen-class null of `0.3817`; §3.26 caught it and this is the correct number |

**`S` is a diagonal matrix of nineteen independent class noise levels.** Its
eigenvalues are its diagonal entries in order, its eigenvectors are coordinate
axes, and the two that clear the null are the two classes for which §3.23 shows the
permutation null is biased low: the null replaces a thin class's loan with a
typical loan of the same cell, and a `>60%` loan is not a typical loan.

**With those two classes removed the spectrum is flat and one direction survives
by `18%` against the seventeen-class design's own null.** B7-15 puts that residual
through the same arm that killed the `2`, and is registered before it runs.

**And a field with no interaction reproduces the nineteen-class reading exactly.**
B7-13, twenty repetitions at each of two class dispersions: `20/20` read back `2`,
leading direction `>60%` in all forty, second direction `50%-60%` in all forty,
and at the upper dispersion `lambda_1` and `lambda_2` come back at `95.0%` and
`92.9%` of the observed values with a spread under one percent. **B7-4's
withdrawal is a measurement.**

### 10.3 The gates, which passed and were never the problem

Twenty repetitions per arm, fifty draws, under §3.15's VOID 1 rate criterion and
§3.16 to §3.19's calibration. Nominal size `1/(d+1) = 0.0196`.

| grid | B7-0c, constructed `0` | B7-0a, constructed `1` | B7-0b, constructed `2` | calibration achieved on the power arm |
|---|---|---|---|---|
| fine | `0/20` | `0/20` | **`20/20`**, Wilson `[0.839, 1.000]` | `l1 1.0400 ± 0.0575`, `l2 1.0383 ± 0.0462` |
| coarse | `0/20` | `0/20` | **`20/20`**, Wilson `[0.839, 1.000]` | `l1 1.3235 ± 0.3174`, `l2 1.1734 ± 0.1464` |

**Nothing here is wrong and nothing here was ever the problem.** The gates
establish that this design recovers a constructed rank under **homoskedastic**
noise, and it does. §3.16 named the homoskedasticity as an approximation it was
leaving in place, and **that was the approximation that decided the stage.** The
coarse grid's calibration is markedly noisier than the fine grid's, which is a
six-class construction against a nineteen-class one and is reported rather than
repaired.

### 10.4 Criteria

| criterion | status | |
|---|---|---|
| B7-1 estimator recovers a constructed rank | **pass** | synthetic, near-complete design |
| B7-2 no interaction returns rank zero | **pass** | at every fill swept |
| B7-3 permuted data returns rank zero | **pass** | through the identical path |
| **B7-4 the estimate** | **WITHDRAWN** | §3.25. `S` is diagonal; there is no interaction for a rank to count |
| B7-5 the answer does not live in the null | pass, and now vacuous | both nulls give the same two diagonal entries |
| B7-6 the answer does not live in the class grid | **pass** | fine `2`, coarse `2`. Its earlier failure was against a scrambled index (§3.21) and now it passes on two grids that both keep the two thin classes apart |
| B7-7 the answer does not live in the spread band | pass, and now vacuous | all nine arms keep those two classes |
| B7-8 selection axis disjoint from test axis | pass, and now a warning | `19/19`, `\|cos\| = 0.9991`: the stability of an indicator on a class that is thin in both halves |
| **B7-9 what the class index touches at all** | **reported, and stands** | `0.3036` |
| B7-0a / B7-0b / B7-0c on both grids | **pass**, §10.3 | under homoskedastic noise |
| B7-10 where the second direction lives | reported | complement grid `0` |
| **B7-11 what a coarsening can carry** | **reported, and stands** | §10.5 |
| **B7-12b how much of `S` is off the diagonal** | **reported, and it withdrew B7-4** | §3.25 |
| **B7-13 the confirmation** | **returned: `20/20` at both brackets** | §3.27. The withdrawal is a measurement |
| **B7-14 the seventeen-class design against its own null** | **returned: rank `1`** | §3.27. §3.25's "rank zero" used the wrong design's null and §3.26 caught it |
| B7-15 the residual `1` through B7-13's arm | **returned, and its table was not exclusive** | §3.28. Class noise alone gives a margin of `1.014` and `0.981` against the observed `1.181`; the deciding number is the observed seventeen-class leading direction and it is not recorded |

Three criteria were **withdrawn or voided rather than restated**: B7-4's first
gated form (§3.5), §3.23's bound table (§3.24), and the §3.9 to §3.12 localisation
chain (§3.21). Four registered outcome tables were declared on inputs that turned
out to be wrong: §3.11's, §3.20's, §3.20's control, and §3.23's.

### 10.5 What the stage claims

**1. The class index carries `0.3036` of stage B2's within-cell term.** Reported,
not gated, exact to `2.8e-17`.

**2. On this sample, the class-by-cell interaction is not separable from sampling
noise on any class holding more than about two loans per cell-class entry.** The
largest correlation among all `171` class pairs is `0.1417`, and a constructed
field with **no interaction** at each class's own dispersion reproduces the
observed `lambda_1` and `lambda_2` to `95%` and `93%` and reads back `2` in
`40/40` repetitions (B7-13, §3.27). **The seventeen classes that remain after the
two thinnest are removed carry one direction above their own null by `18%`, and
that residual is B7-15 and is not yet read.** **This is a statement about the instrument on this design, not about the
economy.**

**3. The sufficient statistic for a rank on an incomplete design is the per-class
entry depth.** §3.5 said fill and §3.7 corrected it to the co-occurrence counts.
Neither is a function of the class-level counts at all. **A permutation null that
replaces a thin class's loan with a typical loan of the same cell cannot reproduce
that class's own dispersion**, and every eigenvalue this stage read above its null
came from exactly that.

**4. A coarsening acts on a class direction as its count-weighted bucket means,
and it can annihilate a direction entirely.** Measured (B7-11): the fifteen-level
index that keeps the fourteen integers apart and merges the five published buckets
carries the fine grid's first direction at `0.15%` and its second at `0.48%`, and
reads rank `0`. The six-level index that does the reverse carries both at `97.9%`.
**This holds whatever the directions are**, which is why it survives B7-4's
withdrawal, and it is the instrument `b8_fannie_slice.md` and `b9_zero_holonomy.md`
now cite for their grid rules.

**5. Coarsening a class main effect manufactures a cell-dependent interaction, and
on this design it is negligible.** `A(a)` alone, coarsened, arrives at `2.5e-05`
and `4.0e-04` against nulls of `0.393` and `0.241`. Named before it was measured
(§3.20) and cleared.

### 10.6 What the stage does not claim

**It has no rank.** Not `1`, not `2`, not "one ladder", not "several". §5's
trichotomy is not delivered and the reason is not a grid disagreement, which was a
bug (§3.21), but the instrument.

**It does not claim there is no interaction.** §3.26 struck that phrase as
stronger than the measurement. `S` carries no structure **shared across classes**;
whether any single class carries its own cell-specific variation is not separable
from that class's own sampling noise on this design.

**It does not claim the interaction is zero.** `b1_theorem.md` Corollary 4 is a
theorem about the framework and is untouched by a measurement failing. What the
stage claims is that the interaction's **shape** is not measurable on this design
with this class index. **Zero-versus-non-zero is what remains readable, and
Corollary 4 already had it, so B7 adds nothing there.**

**It says nothing about the slice summand**, which Corollary 2 puts out of the
mortgage carrier's reach entirely and which stage B3 measures.

**It does not license B7-8's `19/19` as evidence of anything.** A stability check
across two disjoint halves cannot distinguish a stable economic direction from a
stable design defect, and here it was the second.

**Nothing outside B7 rests on B7-4.** `b8_fannie_slice.md` §3.3 and
`b9_zero_holonomy.md` §3 cite B7's **grid dependence**, which §10.5's fourth claim
supports on its own.

### 10.7 The amendment trail, indexed

Everything in §3 after §3.3 is dated and was added while the stage ran. A reader
who wants only the outcome does not need any of it; a reader checking whether the
outcome was chosen after the fact needs all of it.

| § | what it added | when |
|---|---|---|
| 3.4 | two specification points, fixed before any HMDA row was read | before step 2 |
| 3.5 | the estimator's usable regime, and a withdrawn claim about its bias | after step 2 |
| 3.6 | the gate completed from one arm to three, with four outcomes declared | after B7-9, before B7-0 |
| 3.7 | B7-0 passed; fill is not the sufficient statistic; the gate ran under one null of two | after B7-0 |
| 3.8 | the coarse grid, sourced without an external file | before B7-6 |
| 3.9 | B7-6 failed; the coarse arm was never licensed; B7-6r registered both ways | after step 4b |
| 3.10 | B7-6r passed; the failure is genuine; the localisation deduction | after B7-6r |
| 3.11 | the complement grid registered with three readings | before B7-10 |
| 3.12 | B7-10 returned `1`; the second direction spans the partition | after B7-10 |
| 3.13 | B7-7 and B7-8 split into a cheap census and an expensive estimation | before step 4c |
| 3.14 | the census returned; which arms are new designs | after step 4c-a |
| 3.15 | three criteria voided as mis-specified, with defect arguments containing no results | after step 4c-b |
| 3.16 | two further defects in the same construction; the calibration matched, not only shaped | after §3.15, before any re-run |
| 3.17 | §3.16's own declared check failed; the level is set net of the measured noise floor | after the first calibration check |
| 3.18 | §3.17 landed at +2% and +4%; the floor is solved for per rank, and the miss travels with every rate | after the second calibration check |
| 3.19 | the solve is noise-dominated and is voided; §3.17's floor stands and the gate measures its own achieved level | after the third calibration check |
| 3.20 | B7-11 registered: what a coarsening can carry, and the main effect it manufactures | before B7-11 was built |
| 3.21 | the class levels were stored alphabetically and read positionally; every grid comparison in the stage is void | after B7-11's first run |
| 3.22 | B7-11 on the corrected partitions: B7-6 does not fail, and the interaction is a bucket-level object | after B7-11's corrected run |
| 3.23 | both gates pass; the two directions load on the two thinnest classes; B7-12 registered | after the gates and B7-11's loadings |
| 3.24 | §3.23's table voided as a zero-width threshold on two defective bounds; the off-diagonal test replaces it | after B7-12 step one |
| 3.25 | B7-12b returned: `S` is diagonal, the two directions are the two thinnest classes, **B7-4 withdrawn** | after B7-12b |
| 3.26 | self-check of §3.21 to §3.25: one hole (a seventeen-class spectrum against a nineteen-class null), one over-statement, three claims holding | asked for directly |
| 3.27 | B7-13 confirms the withdrawal at both brackets, `20/20`; B7-14 returns `1` not `0`; B7-15 registered | after B7-13 and B7-14 |
| 3.28 | B7-15 returned; two rows of its table fire at once; the brackets are not brackets; one number outstanding | after B7-15 |
| 3.29 | the seventeen-class leading direction is `<20%`; the residual is one class's diagonal entry; **B7 closes with no reading** | after the last run |

### 10.8 Registered and not run

- ~~The seventeen-class leading direction~~ **returned**, §3.29: `<20%` at
  `+0.9575`. The residual is one class's diagonal entry and **B7 is closed**.
- ~~B7-15~~ **returned**, §3.28. Its declared table had two rows firing at once
  and neither was taken.
- ~~B7-13~~ **returned**, §3.27: `20/20` at both brackets, `95%` and `93%` of the
  observed eigenvalues from a field with no interaction.
- **§2.3's LTV class grid.** Registered, unrun, and **its value has risen**: it is
  an independent regulator-published dimension rather than a re-cut of the same
  one, so it is the only registered arm that could show whether any rank-type
  reading survives a change of dimension. Its per-class entry depth must be
  reported before any rank is read from it, which is §10.5's third claim applied
  forward.
- **B7-7 and B7-8 have not been re-run under the rewritten
  `b7_robustness_rank.py`.** Their readings in `b7_robustness_rank_draws50.json`
  use no partition and stand as readings; their gates in that file are void under
  §3.15 and §3.16 and are not quoted anywhere.
- **`run_all.py` carries no B7 entry** and `RESULTS.md`'s B7 sections render from
  records that now carry the `.expired_20260816_pre_partition_fix` suffix. Both
  wait for a re-render.
- **`interaction_rank.py` has no test.**
- The result records store the `--jobs` flag rather than the thread count actually
  used, which affects no figure because the estimates are identical at any thread
  count, and is still the wrong thing to store. The coarse gate record's `design`
  block reports the fine design's class count and levels; its substantive fields,
  `observed_eigenvalues` and `noise_floor`, are the coarse grid's and are correct.

---

### 10.9 The superseded §10, kept whole and unedited

**Everything below stood as this stage's Results until 2026-08-16 and every claim
in it is void.** It is kept because this repository does not delete, and because
the record of what a stage said before an error was found is what shows where the
error entered. §3.21 explains the partition bug, §3.25 the withdrawal.

#### The superseded preamble and sections

**Superseded in part, 2026-08-16, and marked here rather than rewritten while the
re-run is in flight.** Read this block before anything below it.

**Every gate figure in §10.2 is superseded by §3.16, and no reading in §10.3 is
currently licensed.** The four gates were run on a construction that carried no
class main effect and that was out by `2.63x` on the fine grid's second
eigenvalue, which is the eigenvalue the whole stage turns on. "Thirty-six exact
recoveries out of thirty-six, twice over" is a true statement about an instrument
this document has since disowned. The replacement is registered in §3.15 VOID 1,
§3.16, §3.17 and §3.19 and has not returned.

**§3.6's two-draw-count criterion is gone** (VOID 1), so the preamble's "at fifty
draws and again at two hundred" no longer licenses anything. The
`..._draws200.json` records stay on disk, because nothing here is deleted. On
2026-08-16 all six superseded gate records and both `b7_rank_draws*.json` were
renamed with the suffix `.expired_20260816_pre_partition_fix` and left where they
are, so `results/` holds only records this document still stands behind. They are
no longer evidence for anything. The two-count agreement was a proxy for
"is the answer stable"; a rate against the estimator's own nominal `1/(d+1)`
answers that directly and at a fraction of the cost.

**One two-hundred-draw run was killed in flight and never wrote a file.**
`b7_robustness_rank.py --draws 200`, started 2026-08-16 and stopped the same day
when §3.15 landed. Its gate portion was void under all three VOIDs and its
estimate portion was superseded by §3.16. Recorded because a run that was started
and stopped belongs in the trail whether or not it produced a file.

**§3.25 is the one to read first, and it withdraws B7-4.** `S` is a diagonal
matrix of class noise levels: the largest off-diagonal correlation among all `171`
pairs is `0.1417`, and dropping the two classes that hold `1.18` and `1.37` loans
per cell-class entry leaves a flat seventeen-class spectrum topping out at `0.2770`
against a `null_max` of `0.3817`, which is **rank zero**. **The stage has no rank
to report.** Every rank-type number in §10 is those two diagonal entries seen from
a different angle.

**§3.22 is the second one to read.** On the corrected partitions the coarse grid
reads `2`, not `1`. **B7-6's disagreement was with a scrambled index and does not
exist.** §10.6's standoff, §10.5's claims and the whole §3.9 to §3.12 localisation
chain are void at their root. The stage's remaining obstacle is a calibration that
has not been paid for, and no longer a disagreement between grids.

**§3.21 voids more than the gates.** The class levels were stored alphabetically
and read positionally, so **every partition this stage built merged the wrong
classes**. B7-6, B7-6r, B7-10 and both of §10.5's claims are void, and §10.6's
standoff is void as posed because one of its two branches was B7-6. What survives
is everything that uses no partition: B7-4, B7-5, B7-7, B7-8, B7-9.

#### §10.4 and §10.8's "not run" rows for B7-7 and B7-8 are wrong

**Both ran**, on 2026-08-16, at fifty draws and three repetitions. The record is
`results/b7_robustness_rank_draws50.json`.

**B7-7 passed.** All nine arms returned `2`: the six spread bands, the unbanded
rank transform, and both halves of the year split.

**B7-8 failed, and it failed on exactly the rule VOID 1 voided.** The `odd_years`
design's rank-zero floor arm returned `[1, 0, 0]`, one repetition of three, so the
unanimity rule called that whole design ungated, and the criterion's
`both_gated` clause declared its result not readable. The result it declared
unreadable was **19 of 19 class loadings agreeing in sign across two halves that
share no cell, with `|cos| = 0.9991`.**

Under VOID 1 the same observation is one failure in three trials of a size arm
whose nominal is `1/51`, a one-sided `P(at least 1) = 0.058`. Suggestive, not
decisive, and **estimable at twenty repetitions where it is not at three.** The
most consequential thing the unanimity rule did in this stage was to kill B7-8 on
that single draw.

**The `19/19` and the `0.9991` survive every correction in §3.15 through §3.19
and are invariant to the draw count.** They are computed from the eigenvectors of
the **observed** `S` on each half, and no null enters an eigenvector. What was
ever in question was not those numbers but whether the design was licensed for
them to be read from, and that question is now a rate and is being re-measured.

---

**Everything below ran on the retrieved HMDA sample between 2026-08-15 and
2026-08-16, at fifty draws and again at two hundred, and every figure quoted is
the same at both counts unless the text says otherwise.** Records:
`results/b7_design.json`, `b7_gate_draws{50,200}.json`,
`b7_gate_coarse_draws{50,200}.json`, `b7_gate_complement_draws{50,200}.json`,
`b7_rank_draws{50,200}.json`.

**The verdict in one line.** Criterion B7-6 failed, §7 applies, and **this stage
does not deliver §5's trichotomy.** What it holds instead is three separately
licensed readings that disagree, and a statement about why.

##### 10.1 (superseded) The sample and the design

| | |
|---|---|
| files retrieved / loans parsed | 408 / **20,071,900** |
| dropped, blank DTI | 164,692 |
| dropped, filer-exempt DTI | 4,253 |
| loans after the band and the cell-size filter | **16,035,398** |
| cells | **326,872** |
| class levels (the regulator's published DTI partition) | **19** |
| fill of the cell-by-class design | **0.7222** |
| distinct classes per cell, min / q1 / median / q3 / max | 3 / 12 / **14** / 16 / 19 |

`20,071,900` matches the count recorded in `effective_price.SPREAD_BOUND`'s own
docstring digit for digit, which is how this stage confirms it is on stage B2's
sample rather than asserting it.

**B7-9, reported and not gated: the class index carries `0.3036` of stage B2's
within-cell term.** Not a sliver. The variance decomposition it comes from is
exact to `2.8e-17`, which it should be, being an identity.

##### 10.2 (superseded) The four gates

Each gate lays a **constructed** field of known matrix rank on the observed
design, keeping every cell, class, loan count and hole, and checks that the
estimator reads the rank back. Three constructed ranks by three repetitions.

| gate | grid | null | constructed `0` / `1` / `2` | verdict |
|---|---|---|---|---|
| **B7-0** | fine (19) | primary | `[0,0,0]` / `[1,1,1]` / `[2,2,2]` | pass |
| **B7-0r** | fine (19) | residual | `[0,0,0]` / `[1,1,1]` / `[2,2,2]` | pass |
| **B7-6r** | coarse (6) | primary | `[0,0,0]` / `[1,1,1]` / `[2,2,2]` | pass |
| **B7-10 gate** | complement (15) | primary | `[0,0,0]` / `[1,1,1]` / `[2,2,2]` | pass |

**Thirty-six exact recoveries out of thirty-six, twice over.** §3.6's two-count
criterion is met on every one. Every reading in §10.3 is therefore licensed, and
that is the only reason any of them may be read at all.

##### 10.3 (superseded) The three readings

All three class grids are cuts of the regulator's own published DTI partition.
**This project chooses no boundary in any of them**; the only boundaries used are
`36` and `50`, which are where the regulator's own bucketing stops and resumes.

| grid | levels | composition | rank |
|---|---|---|---|
| **fine** | 19 | five published buckets + fourteen integers | **2** |
| **coarse** | 6 | five buckets + `36-49` merged | **1** |
| **complement** | 15 | buckets merged + fourteen integers | **1** |

Identical under the primary and the residual null, and identical at fifty draws
and two hundred.

**The fine grid's spectrum**, which does not depend on the draw count:

```
1.4674   0.7544   0.2768   0.2240   0.2199   0.2155   0.2125   0.2096
```

against a null maximum of `0.3817` at fifty draws and `0.3892` at two hundred.
The second eigenvalue is `1.94x` the null and the third is `0.72x`, so the fine
grid's `2` is not a marginal call. No negative eigenvalue clears the null in
absolute value, no class pair fails to co-occur, and the centring converges in
twelve iterations to `5.5e-13`.

The two nulls come within `0.3%` of each other on the real design (`0.38171` and
`0.38061`) after disagreeing on small constructed ones, which is §3.7's point
about co-occurrence counts showing up again.

##### 10.4 (superseded) Criteria

| criterion | status | |
|---|---|---|
| B7-1 estimator recovers a constructed rank | **pass** | synthetic, near-complete design |
| B7-2 no interaction returns rank zero | **pass** | at every fill swept |
| B7-3 permuted data returns rank zero | **pass** | through the identical path |
| B7-4 the estimate | **reported** | rank `2` on the fine grid |
| B7-5 the answer does not live in the null | **pass** | both nulls give `2` |
| **B7-6 the answer does not live in the class grid** | **FAIL** | fine `2`, coarse `1` |
| B7-7 the answer does not live in the spread band | **not run** | §10.8 |
| B7-8 selection axis disjoint from test axis | **not run** | §10.8 |
| B7-9 what the class index touches at all | **reported** | `0.3036` |
| B7-0a / B7-0b / B7-0c, B7-0r, B7-6r | **pass** | §10.2 |
| B7-10 where the second direction lives | **reported** | complement grid `1` |

One criterion was **withdrawn rather than restated**: the first, gated form of
B7-4 asserted the estimator errs upward and never downward, and a wider sweep
refuted it at a fill of `0.15`. It is now reported and not judged (§3.5).

##### 10.5 (superseded) What the stage claims

**Merging either half of the regulator's partition destroys the second
direction.** Merging the fourteen integers does it; merging the five buckets does
it too. Both coarsenings passed the same gate as the fine grid, so neither `1` is
a failure to resolve. **The second direction's class loading therefore varies
substantially on both sides of `36`, and no single-sided coarsening preserves
it.** Whatever it is, it is a property of the full published partition and not of
either half.

**A qualified-mortgage cliff at `43` is disfavoured.** A second direction that
were purely a function of position relative to `43` would be fully representable
in the complement grid, which keeps all fourteen integers apart and passed the
gate at both draw counts. It returned `1`. That does not refute a direction which
loads on `43` **and** on the buckets; what it excludes is the clean version, and
the clean version was the whole appeal. **This is a forward-registered arm
returning against a post-hoc story (§3.9, §3.11), which is the only way this
document permits such a story to be touched.**

##### 10.6 (superseded) What the stage does not claim

**It does not deliver §5's trichotomy.** B7 may not say the mortgage carrier has
one ladder and may not say it has several.

**It does not adjudicate between two live readings, and this is the honest
terminal state.** B7-0a licenses that the fine design does not manufacture a
second direction out of a rank-one truth at the observed energy, which argues the
`2` is real. B7-6 says the reading is not stable under a licensed change of class
index, which argues it is fragile. **Both are outputs of gated arms and neither
retires the other.**

**It says nothing about the slice summand**, which `b1_theorem.md` Corollary 2
puts out of the mortgage carrier's reach entirely and which stage B3 measures.

**A `1` anywhere here would have been bounded by the file in a way a `2` is not.**
The public HMDA file carries no credit score; twenty-seven fields are redacted.
So the coordinate most likely to carry a second dimension is the one the regulator
removed, and every `1` in §10.3 is a statement about the coordinates the public
file happens to carry (§8).

**§5's answer set was incomplete and §7 caught it.** §5 declared three readings
for a single grid and never declared what to report when two licensed grids
disagree. §7's falsification row covered the case, but a reader reads §5's table,
and the gap is recorded here rather than repaired in place.

#### The superseded "Registered and not run"

**B7-7 and B7-8 are in §6 and have never been executed.** Neither is blocked by
anything this stage found; both are blocked by plumbing.

- **B7-7** needs the sample rebuilt at each bound in `BOUND_SWEEP`, and
  `build_design` currently reads every CSV inside itself, so six bounds means six
  reads of the whole file set.
- **B7-8** needs `activity_year` per loan for the odd-even split, and
  `build_design` does not return it.

**The headline is already withdrawn, so neither can restore it.** What they can
do is test whether each of the three readings in §10.3 survives a change of
spread band, a rank transform, and a split of the sample by year. If the fine
grid's `2` does not survive one of those, that is new information and it runs
against the reading, not for it.

**Also outstanding**: §2.3's LTV class grid is registered, unrun, and currently
carries no disposition beyond "optional"; the complement grid's eigenvalues were
not recorded, only its rank; and the result records store the `--jobs` flag rather
than the thread count actually used, which does not affect any figure because the
estimates are identical at any thread count, and is still the wrong thing to
store.
