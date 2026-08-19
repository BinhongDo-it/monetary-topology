# B8: the slice summand on a household carrier, from loan modification

> **[2026-08-18] This file is B8's pre-registration and it is the authority for
> the eight criteria published in `RESULTS.md`.** The instrument conclusions the
> published criteria depend on are summarised in `b8_instrument_notes.md`; the
> full inputs register and the per-station design and result files are maintained
> outside this repository. **References to sections of those files are provenance;
> nothing here depends on reading them.**



**Status: pre-registration. No Fannie row has been read.** Registered 2026-08-16.

Sibling of [`b3_cip_slice.md`](b3_cip_slice.md), whose estimator shape, zero
calibration and pairwise filter rule this stage adopts rather than re-invents.
Sibling of [`b7_interaction_rank.md`](b7_interaction_rank.md), whose grid lesson
this stage is bound by from its first line.

---

## 1. What this stage is for, in one sentence

**B3 reached the slice summand and B3 §9 says in its own words that it says
nothing about Volume I.** Theorem 2 gives the two summands different economic
content, and B3's content is arbitrage capacity, not who the agent is. Stage B2
and stage B7 reach agent stratification but, by Corollary 2's scoping block, only
in the square summand, because a B2 cell is one edge and a two-vertex graph has no
cycles to lift.

So the repository currently holds:

| | square | slice |
|---|---|---|
| **agent stratification** | B2, B7 | **empty** |
| **no stratification** | — | B3 |

**B8 is the empty cell.** It is the first carrier on which one household walks
several positions, and it is therefore the first place the mathematics of Volume II
and the economics of Volume I are computed on the same object. That, and not the
existence of another non-zero loop, is the reason for the stage.

---

## 2. The graph, and where the cycles are

### 2.1 The positions

`b1_setup.md` §3 fixes nodes as triples `(a, g, q)`: agent class, position, tier.
The position here is a financed owned dwelling, held fixed. The tier index is the
servicing state, which is what varies:

```
q ∈ { current, delinquent, modified }
```

Edges, all three realisable and all three reported monthly:

```
current   → delinquent     the loan misses payments
delinquent → modified      the servicer re-contracts
modified  → current        the modified loan performs
```

Three distinct vertices, three distinct edges, so `b₁(G) = 3 − 3 + 1 = 1`. It is a
triangle and not an out-and-back, which is the condition Corollary 2's scoping
block states: *a slice cycle needs `b₁(G) ≥ 1`, so it needs at least three
positions with two distinct routes between some pair.* Here the two routes from
`delinquent` back to `current` are the direct cure and the route through
`modified`.

`b1_setup.md` §5's table is a star centred on cash and therefore a tree. **This
carrier is the first position graph in the repository that carries a cycle
without being built to.** The cycle is the servicer's own rulebook.

### 2.2 Why a non-zero loop sum is not an identity here

This was raised and it does not survive contact with `b1_setup.md`. Recording the
answer because the objection will be raised again.

The objection is that a modification re-contracts the loan by definition, so of
course the terms differ afterwards, so of course the loop sum is non-zero, so the
stage reads a tautology in the manner `PROJECT_PLAN.md` §11 records for A3-3.

**The identity runs the other way.** `b1_setup.md` §3: *a gradient field returns
zero on every loop, in every metro, in every year, by identity.* If `ω` were the
difference of a scalar on positions, the loop would sum to zero **however much the
contract changed**, because `current` would carry one potential value and the walk
returns to it. Terms changing is not what makes the sum non-zero. What makes it
non-zero is that the terms are not a function of the state.

Two objections in `b1_setup.md` §7 already cover the rest:

- *"These are transaction costs and risk premia, not arbitrage."* → *Integrability
  fails as soon as the loop sum is non-zero, whatever the gap is compensation for.
  A critic who wants to save integrability has to argue the loop sum is zero, not
  that it is deserved.*
- *"Then just define the price as the risk-adjusted effective price and it is
  integrable again."* → *This requires a scalar on positions alone that reproduces
  every agent's terms. If one exists, the field was a gradient and the framework is
  wrong about this economy, which is exactly the empirical question.*

The A3-3 family is a different failure. There the two sides of the reading were
definitionally the same quantity computed twice, so the machine printed `1.44e-15`
and nothing was learned. Here the two sides are a measured accumulation and zero,
and zero is the hypothesis.

**The one live version of the objection is about node identity**, and B8-3 is
designed so that it does not have to be won. See §5.

### 2.3 Why competition does not remove it, in the literal rather than the generic form

`b1_setup.md` §7 answers "arbitrage is competed away" generically: *only along
edges that exist*. On this carrier there is a stronger and literal version, and it
is `b3_slice_availability.md` §5's, written when that check named the domestic
slice carrier as the repository's remaining open item:

> its plausibility as a non-zero loop rests on the fact that **the leg cannot be
> reversed** — one cannot short one's own deposit — so it is **not an arbitrage
> that competition removes**.

**A borrower cannot short their own modification.** There is no position that pays
off when the terms they are handed are worse than the terms handed to someone else
on the same path. The loop is realisable in one direction and has no counterparty
on the other, so no amount of competition among borrowers closes it. This is not
an efficiency claim and it is not a claim that anyone is behaving badly; it is the
statement that the closing leg is absent, which is the same structure as the
AP-only leg in `b9_zero_holonomy.md` §2 and the non-assumable mortgage in
`b1_theorem.md` §8.

**Provenance, recorded because it matters for what this stage is.**
`b3_slice_availability.md` §5 wrote that a domestic slice cycle "**is new design
work and is not specified anywhere in this repository**", and offered
`cash → dwelling → home-equity credit → cash` as a candidate shape. B8 is that item
closed, with `current → delinquent → modified → current` as a second instance of
the same shape. The two are alternatives, not competitors, and if B8 terminates at
§10's availability check the home-equity form remains registered and unattempted.

---

## 3. The measurement

### 3.1 The field

`b1_setup.md` §3, unchanged:

```
w = log( total value at exit / total value at entry )   over a holding period T
```

Value of a position is the present value of the remaining contractual obligation:
the scheduled payment stream implied by `(current interest rate, current actual
UPB, remaining months to maturity)`, discounted on a common curve, plus fees paid
in the transition, less any principal forgiven.

**Fixed here, before any row is read.** Each is a number that would otherwise be a
free parameter, and `PROJECT_PLAN.md` §1's rule is that a number without a source
is a calibration and cannot support a rejection.

| choice | fixed value | source |
|---|---|---|
| discount curve | the constant-maturity Treasury par yield at the transition month, interpolated to the loan's remaining term | it is agent-invariant. Using the note rate would put the answer in the discounting |
| `T` | the realised duration of each leg in months; the primary statistic is **per period**, the total is reported beside it | `b1_setup.md` §3 states the ratchet as the per-period loop sum |
| non-interest-bearing UPB | counted at zero interest to its stated maturity, not written off | it is deferred, not forgiven, and the two are separate fields |
| fees | capitalised arrears and late fees, from the UPB path, not from a schedule | the schedule is not in the file |

### 3.2 The delinquency leg, which is the hard one and must not be padded

`modified → current` is the easy leg: the modification is a re-contracting whose
new parameters are printed. `current → delinquent` is not. Nothing in the contract
changes when a borrower misses a payment; what changes is compliance.

**Fixed here: `ω` on that leg carries fees and capitalised arrears and nothing
else.** In particular it does **not** carry the loss of refinancing access. That
loss is real and it is exactly what `b1_setup.md` §5 says must be handled as a
missing edge rather than as a price: *below the threshold the edge is absent at any
price, so it contributes to `H¹` rather than to the curl.* Folding it into `ω`
would be the padding that makes the headline whatever the analyst wants. It is
measured separately, in B8-5.

**Consequence, declared in advance:** the loop sum will be dominated by the
modification leg. That is expected and it is not a defect. The test is not whether
one leg is large. It is whether the total is zero, whether it depends on the path,
and whether it depends on the class.

### 3.3 The tier grid, which B7-6 makes mandatory

`q` indexes nodes of `G`. **Corrected 2026-08-16.** This section first cited B7-6's
failure, and that failure was an artefact of a scrambled partition index
(`b7_interaction_rank.md` §3.21). The corrected result is a **stronger** reason for
the same rule, not a weaker one.

On one body of data with one estimator, three licensed class grids return:

| grid | what it merges | rank |
|---|---|---|
| fine, 19 levels | nothing | **2** |
| coarse, 6 levels | the fourteen integers `36`-`49` | **2** |
| complement, 15 levels | the five published buckets | **0** |

**The reading is a function of *which* levels are merged, not of how many.**
Merging fourteen levels costs two percent of each direction; merging five costs
ninety-nine. **The same dependence applies here, on `q` instead of on `A`**, and it
is now demonstrated rather than inferred from a defect.

> **Every B8 reading is run on at least two `q` grids. A reading on one grid is
> not a result.**

Primary grid: `current` / `30` / `60` / `90+` / `modified`, which is the
delinquency status field's own partition. Secondary grid: `current` / `delinquent`
/ `modified`, collapsing the delinquency depths. Neither boundary is chosen by
this project. If the two grids disagree, §8 applies and the reading is reported as
grid-dependent with no trichotomy claimed, exactly as B7-6 was.

---

## 4. The zero calibration, which the data supplies for free

Two, and they check different things.

**B8-0a, the antisymmetry check.** Loans that go delinquent and cure without a
modification traverse `current → delinquent → current`. That is an out-and-back and
it must return **exactly** zero. Computed through the same machinery every other
number comes from and **not short-circuited on the repeated edge**, which is
`b3_cip_slice.md` B3-2's rule adopted verbatim. A non-zero return means the `ω`
construction is broken and nothing after it may be read.

**B8-0b, the noise floor.** Loans matched on class and on the full realised path
should carry the same loop sum. Their dispersion is `N`. The headline is reported
as `√Z / √N`, which is `b3_cip_slice.md` §11.1's shape, so that a reader who
distrusts the level still has the comparison.

---

## 5. Pre-registered predictions

| id | statement | load-bearing |
|---|---|---|
| **B8-0a** | the out-and-back path returns exactly zero | **gate.** Fails → stage stops, nothing is read |
| **B8-0b** | the noise floor is computable on matched cells and is reported per arm | gate |
| **B8-1** | `√Z / √N > 3` on the modification triangle, on **both** `q` grids | headline |
| **B8-2** | the sign of the per-period loop sum is stable across the four windows of §6 | discriminant against one-time repricing, and it is `b1_setup.md` §7's own pre-stated test |
| **B8-3** | **two realisable paths to the same terminal state carry different accumulated `ω`** | **the strongest form, and the only one that does not require winning the node-identity objection** |
| **B8-4** | conditional on identical path, `√Z` disperses across agent classes, **within the Flex Modification sub-population** | **the Volume I join, and the reason for the stage** |
| **B8-5** | the fraction of borrowers for whom `delinquent → modified` never exists differs by class | the hole. `H⁰` / `H¹`, not curl |
| **B8-6** | every one of the above holds on both `q` grids | §3.3 |

**Why B8-3 is written the way it is.** A critic who insists that
`current at 4%` and `current at 6%` are different nodes kills B8-1, because the
walk then does not close. B8-3 survives that: two borrowers **both** at
`current at 6%`, arrived by different routes, with different accumulated `ω`, is
non-integrability without any claim about node identity. Candidate path pairs,
fixed here: one 90-day episode against two 30-day episodes; cure-then-redefault-
then-modify against modify-on-first-episode.

**Why B8-4 is restricted to Flex Modification.** Flex Mod is rules-based: arrears
capitalised, rate moved to a posted benchmark, term extended, targeted at a stated
payment reduction. In that sub-population the terms change is not a function of
borrower risk, so **"the servicer priced the risk" does not explain class
dispersion**. Outside it, B8-4 is reported but is not discriminating and is
labelled so.

**Agent classes.** Taken from the acquisition file: credit score band, LTV band,
DTI band, first-time buyer flag, occupancy, state, loan purpose. `b7_interaction_
rank.md` §2.4's test applies unchanged: a class index must move with the borrower
and not with the dwelling or the tract.

---

## 6. Windows, fixed before the run

Four, non-overlapping, each a distinct modification regime:

```
pre-crisis        origination through 2008
HAMP              2009 – 2016
Flex Modification 2017 – 2019
COVID deferral    2020 – 2022
```

`b1_setup.md` §7's discriminant: *a structural wedge shows the same sign in each;
a repricing event shows up in one. If it shows up in one, that is the honest
finding and it gets reported as one.*

---

## 7. Filters, fixed here

Single-family, fixed-rate, first-lien, owner-occupied. Loans are dropped pairwise
and the dropped count is reported per arm, which is `b3_cip_slice.md` §7's rule:
silence about a dropped record is how a sample becomes a selection. Loans whose
`(rate, UPB, maturity)` triple is incomplete in any month on the path are dropped
and counted separately from loans that simply never modify, because a missing field
and an absent transition are different objects.

**Freddie Mac is a separate layout and is not merged in v1.** If B8-1 passes, the
Freddie replication is a distinct arm with its own record, not a sample extension.

---

## 8. Falsification

- **B8-0a returns non-zero** → the `ω` construction is broken. Stage stops. No
  number from it is quotable, including ones already computed.
- **B8-1 fails on both grids** → the slice summand is not reached on this carrier.
  Report it. The stage does not proceed to a third grid to find a passing one.
- **B8-1 passes on one grid and fails on the other** → grid-dependent, reported as
  such, **no trichotomy claimed**, exactly the B7-6 disposition. The LTV-class
  analogue of B7's §2.3 does not become mandatory on that account.
- **B8-2 shows the sign in one window only** → reported as a repricing event, which
  changes the magnitude of the claim and not its structure, per `b1_setup.md` §7.
- **B8-4 fails inside Flex Mod** → the slice holonomy exists but is not
  stratified. Volume II is served, Volume I is not, and the stage says so. **This
  outcome is not a failure of the stage and must not be re-run into a pass.**

All five are mapped before the run. An outcome not on this list is filed as
**mixed** and the criteria are not re-written afterwards.

---

## 9. What this stage cannot establish

**It is not a profit.** Nobody is arbitraging their own mortgage modification. The
claim is that the terms a household faces are not a scalar on servicing states.

**It says nothing about magnitude in any real economy.** As with B3, what
transfers is the comparison across classes, across paths and across windows, not
the level.

**The bottom of the class range is truncated by construction.** GSE conforming
loans exclude subprime, jumbo, FHA and VA, so the most access-constrained
households are not in the sample. The direction of that truncation is toward the
null: it makes B8-4 and B8-5 harder to pass, not easier. **This must be stated
wherever either is quoted.**

**Modification is endogenous.** Servicer discretion and programme eligibility
select who reaches the `modified` node. B8-4 and B8-5 are therefore association
and are labelled so. **B8-1 and B8-3 are not affected**: Corollary 1 needs one
realisable loop with a non-zero sum, and selection cannot make a realised loop
unrealisable.

**It does not settle per-agent integrability.** `b2_measurement.md` §3.3 makes
that assumption the necessary and sufficient condition for the mortgage carrier's
square half collapsing into econometrics. B8 does not test it and does not need it.

---

## 10. Order of execution

1. Write the three `ω` constructions in full, on paper, before touching the file.
   §3.2 is where a stage like this goes wrong.
2. Field-completeness audit: confirm `(current interest rate, current actual UPB,
   remaining months to maturity)` are populated across every vintage on both sides
   of a modification. Report gaps per vintage. **This is an availability check and
   it may terminate the stage.**
3. B8-0a, then B8-0b. Neither reads a prediction.
4. B8-1 on both grids, then B8-2, B8-3, B8-4, B8-5, each on both grids.
5. Freddie replication only if B8-1 passes, as a separate record.

---

## 11. The second domain, decided now rather than after the run

Registering this before the run, because choosing the replication after seeing the
result selects the replication to match it. That is the same error as anchoring a
feature search on the outcome.

| B8 outcome | second domain | why |
|---|---|---|
| B8-3 passes **and** B8-4 passes inside Flex Mod | **subprime auto ABS**, loan-level monthly from the ABS-EE disclosures on EDGAR | changes the institution and the asset class while keeping the design shape, and the hole is physical (repossession) |
| B8-3 passes, B8-4 fails inside Flex Mod | **corporate credit**: investment grade → downgrade → distressed exchange → re-rating | the reading is "path dependence exists and risk pricing carries it", so the next question is whether it survives changing the agent from a household to a firm |
| B8-3 fails, B8-5 passes | **student loan rehabilitation** | the claim contracts to access gating rather than path dependence, and rehabilitation is the cleanest institutional absorbing wall available: it returns the borrower to current, and it may be used once. Blocked on NSLDS availability, which is checked before this branch is taken |
| only B8-1 passes | **no second domain.** The stage reports a non-zero slice loop on a household carrier and stops | |

---

## 12. Status

Nothing has been run. No Fannie file has been opened. Code not written. No number
in `RESULTS.md` comes from this stage.

---

# Corrections after the availability run, 2026-08-16

**Sections 1 to 12 are unchanged. This section supersedes them where they
conflict.** Source: the B8 inputs register's run record, on 170,013,011 rows
and 2,942,295 loans across six acquisition quarters.

## 13.1 §2.1's `q` is right and §2's `modified` node needs restating

The three servicing states are there and the triangle closes. **What is not there
is a durable marker of having been modified.**

| | flag `Y` to the end | one `Y` block then `N` |
|---|---|---|
| six quarters, pooled | **13,327** | **38,970** |

**Three quarters of modified loans revert to `N`.** Field 63 reverts too, on about
eighty percent of the pre-2008 cohorts, and 1,329 of 2002Q1's modified loans never
carry 63 at all because that field has a later birth date.

**So neither field marks the state.** Field 42's first `Y` dates the **event**, and
the `modified` node is carried forward by the analyst from that date. This is
recorded rather than repaired: **a node the data does not mark is still a node, and
saying so is the honest form.** §2.2's answer to the node-identity objection is
unaffected, since it never relied on a field.

## 13.2 §3.1's horizon is field 17, not field 18

**Field 18 goes blank at the modification month in every quarter and does not
return** (`prev` 1.0000, `at` 0.0000, `next` ≤ 0.0056). Field 17, Remaining Months
to Legal Maturity, is populated at 0.9514 in the worst quarter and ≥ 0.9987 in the
other five; field 19, Maturity Date, matches it exactly.

**`ω` takes its horizon from 17, or from 19 minus the reporting period.** Rate and
UPB are at 1.0000 on both sides in every quarter. §3.1's table is amended
accordingly and 18 is recorded as the field that fails.

## 13.3 §3.2's `7` is a code and not a value

Field 106's values are `7`, `C`, `P`, `D`. **`7` means none of the above.** Fields
102 and 106 have **identical blank counts**, so they were introduced together, and
the difference in their `7` counts equals the difference in their non-`7` totals
exactly. **Only `P`, `C`, `D` count as a deferral.**

Deferral codes over six quarters: `C` 34,030, `P` 1,464, `D` 123.

## 13.4 §5's B8-4 must condition on the cohort's rate environment. This is new.

A term-extension fingerprint was proposed as a way to identify Flex Modification
without a programme field. **It does not work and is withdrawn.**

| quarter | maturity moved | median months added |
|---|---|---|
| 2002Q1 | 0.6713 | 35 |
| 2006Q1 | 0.7497 | 112 |
| 2007Q1 | 0.7413 | 113 |
| 2012Q1 | 0.9885 | 187 |
| 2017Q1 | 0.9850 | 173 |
| 2019Q1 | 0.9921 | 158 |

**Cohort and window are confounded in that table.** 2012Q1's modifications span
HAMP (1,145), Flex (1,044) and COVID (586) and still move the maturity 98.85% of
the time; 2007Q1's are ninety percent HAMP-window and move it 74%. **Same window,
different cohort, very different behaviour**, so the pattern is not a programme
signature.

**It is a signature of the loan's own origination rate.** The 2002-2007 cohorts
originated at six to seven percent, where cutting the rate is a lever; the
2012-2019 cohorts at three to four and a half, where it is not, and extending the
term is all that remains.

**Consequence for `ω` and for B8-4.** A present-value calculation absorbs both
levers, so `ω` is unaffected. **B8-4 is affected**: the modification's value change
decomposes differently by cohort, so **class dispersion must be estimated
conditional on the cohort's rate environment**, or a cohort effect will present as
a class effect. This is fixed here, before `ω` is written.

## 13.5 What the run does not change

§2.2's identity argument, §2.3's irreversibility argument, §3.3's two-grid rule,
§4's two zero calibrations, §5's seven predictions in their logic, §6's four
windows, §8's five falsification routes, §9's four scope limits, and §11's branch
table all stand. **The four windows all have samples**: modification triangles
3,315 / 33,316 / 4,655 / 7,122 by window, deferral triangles 31,057 in COVID, and
366,345 clean cures for B8-0a.

**§11's first branch is reachable but its B8-4 leg now carries 13.4's condition.**

---

# 14. The three `ω` constructions, written before the file is touched

**This is §10 step 1.** No row is read here. The section ends with a short list of
arithmetic questions that a small script settles before any `ω` is coded, and those
are numbered **C8** so they join the availability record rather than hiding inside
an experiment.

Field positions are the ones C0b confirmed: **9** current interest rate, **12**
current actual UPB, **17** remaining months to legal maturity, **19** maturity date,
**3** monthly reporting period, **40** delinquency status, **42** modification flag,
**63** non-interest-bearing UPB, **64** principal forgiveness, **106** alternative
delinquency resolution, **107** its count, **108** total deferral amount.

## 14.1 What `V` is, and which way the sign runs

`V(loan, t)` is the present value **of the household's remaining obligation**. It is
a liability and it is signed positive.

```
V(t) =  PV[ level payment on the interest-bearing balance  (12) − (63) − (108)
            at rate (9), over (17) months ]
      + PV[ the zero-interest balance  (63) + (108)  as a balloon at (19) ]
      -  principal forgiven to date (64)
```

Discounted on the constant-maturity Treasury par yield at month `t`, interpolated to
`(17)`, as §3.1 fixes. **`ω < 0` is a gain to the household.** Stated once here and
used with this sign everywhere in the stage.

The amortisation horizon is **17**, not 18, per §13.2. **The balloon horizon is 19**,
which is what the formula says and what `b8_omega.balloon_horizon` reads; where 19 is
missing, 17 is the fallback and the fallbacks are counted. C11-3 measured the two
agreeing on at least 99.78 per cent of deferral rows, so reading the wrong one would
have been invisible in every number, which is why the code refuses a balloon with no
stated horizon rather than quietly defaulting to 17.

**Corrected 2026-08-17, and the correction is one field wide.** Both terms above read
`(63)` alone until C10-4 and C11 landed. Three changes, each with its source in
the B8 inputs register:

| what changed | why | source |
|---|---|---|
| the interest-bearing balance is **written down**, as `(12) − (63) − (108)` | it was never written at all, only named "interest-bearing", and the implementation filled the gap with `12 − 63` | C8-1, C11-1 |
| the balloon carries **`(63) + (108)`**, not `(63)` | a field-63 rising edge moves the note rate on 46.1 per cent of onsets and the legal maturity on 84.2, so it is a re-contracting; the **deferral** carrier is field 108, which shares a first onset with field 106's ADR code on 35,617 loans with zero exceptions | C10-4, §6.6.11 |
| **`V` has a domain**, and it excludes the loans carrying both balances | all four candidate readings of field 12 sit between 11.6 and 46.2 per cent median error against the contract payment there, against 0.0000 for the same arithmetic on C11's sample. Field 12's content is not identified on them | C13, §6.6.20 |

**The exclusion count travels with every `ω` figure**, at the same rank as §9's
truncation limits. C13 counted 1,276 such loans by rising edges; the implementation
excludes the union of that predicate with "both positive in the same month", which
catches the left-truncated carriers a rising edge cannot see (pit 1), and prints the
two counts separately so the difference is read rather than assumed.

**On every loan that is not excluded the two carriers are never positive at once**,
so the three readings §6.6.20.6 tabulates collapse to the single expression above,
with every term that does not apply equal to zero. There is no branch in the
arithmetic. The only thing the classification decides is which loans may be read at
all.

## 14.2 `ω` is a sum of monthly residuals against a no-event counterfactual

This is the part that decides the stage, and the naive construction fails.

**Why the naive one fails.** If `ω` on an edge is the log ratio of `V` at the two
endpoints, the loop sum telescopes to `log V(return) − log V(departure)` and every
month of ordinary amortisation is inside it. A loan that never misses a payment and
never gets modified would then carry a large non-zero "loop sum" made entirely of
scheduled principal. That number is not holonomy. It is a calendar.

**The construction.** Let `V̂(t)` be the value at month `t` of the **unchanged**
contract carried one month forward from `t−1`: same note rate, balance reduced by the
scheduled principal payment, `(17)` reduced by one, same deferred balloon, no
forgiveness, no capitalisation. Then

```
r(t)  =  log V(t)  −  log V̂(t)
ω(leg) = Σ over the months of that leg of r(t)
```

**`V̂(t)` is priced on the curve at `t`, not at `t−1`.** If it were priced at `t−1`,
every month's residual would carry the month's move in the Treasury curve, and the
gate in 14.5 would fail for a reason that has nothing to do with the loan. This is
written here because it is invisible in code review and fatal.

**What follows immediately.** A month in which nothing contractual happens
contributes exactly zero. The loop sum therefore contains the events and nothing
else. That is the property the theorem needs: if the terms were a scalar `φ` on the
servicing state, each transition would contribute `φ(v) − φ(u)` and the triangle
would cancel; the amortisation drift is not a transition and never enters.

**`V̂` is priced on the OLD contract, and that had to be said twice.** "Same note
rate" and "`(17)` reduced by one" mean **`t−1`'s** rate and **`t−1`'s** term, not
`t`'s. On a quiet month the two coincide, so an implementation that uses `t`'s
passes every property proved on quiet months; **the month where they differ is the
modification month, which is the only month leg 2 has.** Measured 2026-08-17 on a
two point rate cut and a 120 month extension: `+1.670e-03` under the wrong reading
against `-1.792e-01` under the right one, **two orders of magnitude and the sign
flips** (the B8 inputs register §6.6.23.1). The same applies to the payment:
the counterfactual wants the **pre-event** payment, which lives in the previous
contract period.

**Attribution across legs is bookkeeping and the loop sum does not depend on it.**
Arrears capitalisation shows up in the file at the modification month, so it lands in
leg 2's residual rather than leg 1's, which is not what §3.2's wording implies. The
sum over the closed loop is identical either way. **The per-leg split is reported as
bookkeeping and no claim rests on it.** §3.2's substantive rule survives untouched:
the loss of refinancing access is not in `(rate, UPB, term)`, so it cannot enter `ω`
by accident, and it is measured separately in B8-5.

## 14.3 The legs, one at a time

**Leg 1, `current → delinquent`.** No payment is made, so `(12)` does not fall while
`V̂` says it should. Each delinquent month contributes a positive residual of roughly
one month's scheduled principal, plus any late fee that reaches the balance. The leg
is the whole episode, not one instant, so `ω₁` grows with the length of the
delinquency. Sign: **positive**, the obligation is heavier than the contract said it
would be.

**Leg 2, `delinquent → modified`.** The month `(42)` first reads `Y`, or `(63)` is
first set, whichever comes first, which is the onset rule the audit already used.
Everything the re-contracting does is in this one month's residual: the rate change
in `(9)`, the term extension in `(17)` and `(19)`, arrears capitalised into `(12)`,
principal moved to the deferred balloon in `(63)`, anything forgiven in `(64)`. Sign:
**negative** wherever the modification reduces the burden. This is the dominant term
and §3.2 already declared that in advance.

**Leg 3, `modified → current`.** Nothing is re-contracted when a modified loan
resumes performing; the delinquency status field simply returns to `00`. **The
expectation is `ω₃ ≈ 0`, and it is measured rather than assumed**, because a HAMP
trial period that converts to a permanent modification is a second re-contracting and
would land here. If `ω₃` is materially non-zero in the HAMP window and near zero
elsewhere, that is the trial period and it is reported as such.

**The carrier for that test is nearly empty, measured 2026-08-17.** The loop census
(§17.8's count, the B8 inputs register §6.6.6) returns **38** loops across all
six archives with more than one same-kind onset edge inside the window, which is the
population a trial-period conversion has to live in. And `ω₃` is measurable at all on
only **10,449** loops, because §17.3's `t_M == t_B` shape gives leg 3 zero length by
construction on the rest.

**So the HAMP test is registered and will read a number that cannot carry weight.**
It is still run and still printed, because a 38-loop carrier is a fact about the file
worth having on the record. **What it cannot do is decide anything**, and no result
in this stage may lean on it. This is a measurement of the test's own reach, not a
result, and it is written here so that leg 3's `ω₃ ≈ 0` is read as **mostly a
construction identity** rather than as a confirmed expectation.

**Leg 3′, `deferred → current`,** has the same shape and the same expectation.

**The consequence for what B8-1 is measuring, stated plainly.** With `ω₃ ≈ 0` the
loop sum is `ω₁ + ω₂`: the arrears the delinquency added, against the relief the
modification gave. That is a two-term race and its sign is not fixed in advance,
which is what makes B8-2 a real test rather than a confirmation.

## 14.4 Deferral is its own tier, and this is a change to §3.3

The audit returned **51,286 modification triangles and 32,533 deferral triangles**,
and inside the COVID window it returned **7,122 and 31,057**. Both routes are
populated and in that window the deferral route is the larger one.

**A COVID deferral and a Flex modification are not the same re-contracting.** A
deferral moves missed payments to a zero-interest balloon at the unchanged maturity
and leaves rate and term alone; a modification moves the rate, the term, or both.
Merging them into one `modified` tier is exactly the operation §3.3 records as
fatal in B7-6's complement grid: **what is merged matters, not how many levels are
merged.**

**Which column each tier is cut on, added 2026-08-17.** This section described the
two tiers in prose and named no column for either, and that gap is where the defect
lived: the implementation cut the `deferred` tier on **field 63**, which C10-4 then
measured to be the modification carrier. Named here so there is nothing left to
infer:

| tier | onset column | evidence |
|---|---|---|
| `modified` | **field 42, or field 63, whichever comes first** | §14.3 leg 2 already said this. C10-4: at a field-63 rising edge the note rate moves on 46.1 per cent of onsets and the legal maturity on 84.2, so field 63 is a re-contracting |
| `deferred` | **field 108** | C10-4: at a field-108 rising edge `still` reads 0.9966, so rate and term both hold, which is what a deferral is. Fields 108 and 106's ADR code share a first onset on 35,617 loans with zero exceptions, which is C0b behavioural identification |

**Field 108 is not a contract-period boundary** even though it is the deferral onset:
§6.6.17.2 rules that `contract_periods` must not cut there, because the payment does
not change and a cut would only cost coverage. Onset and boundary are two questions
and this file answers them differently on purpose.

So the tier index gains a level:

```
q ∈ { current, delinquent, modified, deferred }
```

Five edges over four vertices, `b₁ = 5 − 4 + 1 = 2`. The graph carries **two**
independent cycles, not one.

**This hands B8-3 a much stronger instance than the ones registered.** §5's candidate
path pairs were timing contrasts, one 90-day episode against two 30-day episodes, and
a critic answers that the two terminal nodes differ in arrears history. Modification
against deferral is an **institutional** contrast at the same terminal state, both
routes realised, both in the same window, both in volume. **B8-3's primary path pair
becomes `delinquent → modified → current` against `delinquent → deferred → current`,
and the timing pairs are retained as secondary.**

§3.3's grids are amended accordingly. Primary: `current / 30 / 60 / 90+ / modified /
deferred`. Secondary: `current / delinquent / modified / deferred`. Both still satisfy
the two-grid rule and neither boundary is chosen by this project.

**One thing the deferral route cannot do, declared now.** **B8-2 is not run on the
deferral triangle.** B8-2 remains a modification-route test across §6's four windows,
and the deferral route is reported without a window comparison.

**The reason was rewritten 2026-08-17 and the old one was deleted, not struck.** It
had read "deferral exists only in the COVID window", which this section's own audit
contradicts: **32,533** deferral triangles, **31,057** inside the COVID window,
**1,476 outside it.** Deferral is overwhelmingly a COVID phenomenon and it is not
only one. B8-2 compares a
quantity across §6's four windows. 1,476 triangles spread over three pre-COVID
windows will not populate that comparison at anything like the modification route's
density, so the deferral arm is still reported without a window comparison — **on
grounds of cell counts, which are measurable and printed, rather than on a claim of
non-existence that this section's own table refutes.** Whether any pre-COVID window
clears `MIN_CELL` is a number B8-2 reads, not a thing settled here.

**This matters beyond the wording.** A ban resting on "it does not exist" is checked
by looking; a ban resting on "there are too few" is checked by counting. The first
one had been carried for two sections without anybody looking.

## 14.5 B8-0a splits into a machine gate and a reading

§4 makes B8-0a a gate: the clean cure out-and-back must return exactly zero or the
stage stops. Under 14.2's construction that statement is ambiguous, and the
ambiguity has to be removed **before** the run rather than after it.

A borrower who reinstates pays every missed payment at once. The positive residuals
accumulated during delinquency are then offset exactly by the negative residual at
the reinstatement, and the round trip returns zero. **On the contract triple, that
zero is arithmetic**, so a non-zero return means the scheduled-principal model is
wrong, or a date is misaligned, or the curve was applied inconsistently across the
two sides. That is a gate and it is worth having.

But a cure that waives late fees, or one that settles for less than the full arrears,
returns non-zero **for a real reason**. Under §4 as written that reading would stop
the stage, and it would be discarding a signal.

**Fixed here, before anything is read:**

| id | what it computes | status |
|---|---|---|
| **B8-0a(i)** | the clean-cure round trip with `ω` on the contract triple `(9, 12, 17)` alone, fees and forgiveness excluded | **gate.** Must return zero to floating-point tolerance. Non-zero → the construction is broken and nothing after it may be read |
| **B8-0a(ii)** | the same loans with fees, capitalisation and forgiveness on | **reading, not a gate.** It is the tightest zero calibration this stage has, because the contract genuinely does not change on that path |

**This is not repairing a failed criterion.** Nothing has run. It is removing an
ambiguity that §10 step 1 exists to find, and it strictly strengthens both halves:
the gate becomes unambiguous, and a quantity that was going to be conflated with it
becomes a number that gets reported. §8's first falsification line now attaches to
B8-0a(i).

**Sample:** whatever `b8_0a_gate` prints under `require_no_defer=True`.
**The figure that stood here, 366,345 from C5, is deleted and superseded
2026-08-17.** It was drawn before the field-108 screen
existed, so it counts loans that deferred. `b8_0a_gate.find_clean_cures` screens both
zero-interest fields now, and O28 measured the cost: **removing up to 31.25 per cent
of the clean cures changed the verdict not at all**, because the gate's statistic is
a maximum over a shrinking set. The live figure is whatever `b8_0a_gate` prints under
`require_no_defer=True`, printed beside the legacy one in the same run, and **no
number in this stage should cite 366,345 without the word legacy attached.**

## 14.6 What "per period" divides by

§3.1 makes the primary statistic per period with the total beside it. Under 14.2's
construction `ω` on a leg is an accumulation and dividing it by that leg's own
duration would let a long delinquency dilute the modification jump.

**The denominator is the duration of the closed loop**, from the last current month
before the episode to the first current month after it, in months. The total is
reported beside it as §3.1 already requires.

## 14.7 What the construction makes falsifiable, in one line

```
loop sum = 0   ⟺   the arrears the delinquency added
                   equal the relief the modification gave, loan by loan
```

**No accounting identity forces that equality and no servicer targets it.** This is a
sharper form of §2.2's answer: rather than arguing in general that a gradient field
returns zero on every loop, it exhibits the exact quantity that would have to vanish
for the field to be a gradient on this carrier.

## 14.8 C8, the arithmetic that must be settled before `ω` is coded

Six questions, all answerable by counting on a few thousand loans, all cheap, none of
them a prediction. **They are registered here so that the answers land in the
availability record and not inside an experiment script.**

| # | question | why it changes `ω` |
|---|---|---|
| **C8-1** | does field 12 **include** field 63, or exclude it | it decides whether the interest-bearing balance is `12 − 63` or `12`. Read it at the deferral month: does 12 fall by roughly 63's value, or stay flat |
| **C8-2** | is field 64 a period amount or cumulative | a cumulative field subtracted every month forgives the same principal repeatedly |
| **C8-3** | is field 63 a balance or a cumulative deferral | the audit found 63 goes blank again on many loans, which a balance would do and a cumulative total would not |
| **C8-4** | at the modification month, does field 12 step **up** by the capitalised arrears | if it does not, arrears are not in the balance and leg 2's residual is missing them |
| **C8-5** | do 17 and 19 agree wherever both are present | the audit says they match exactly; confirm it on the modification months specifically |
| **C8-6** | **Answered.** 108 and field 106's ADR code share a first onset on 35,617 loans with **zero** exceptions (§6.6.11), and C11-1 settled that field 12 contains 108. **The original question's second half asked whether 108 agrees with the change in 63; that half is deleted, its premise killed by C10-4**, which settled that the two fields rise on different rows for different reasons, so there is no "change in 63" for 108 to agree with | 14.4's deferred tier needs the deferred amount to be readable from one field, not inferred. **It is: field 108** |

**C8 terminates nothing.** Every outcome is a construction choice, and the point of
asking first is that the choice is made against the file rather than against the
result.

## 14.9 What is still unidentified, and is not used

Fields **41**, **49** and **109–113** move at a modification and are not identified.
41 is a twenty-four character string, 49 is a number that reads as a payment in 2002
and as something smaller on modification rows, and 111 was born in late 2025. **None
of them enters `ω`, none of them enters a class index, and none is named in this
repository on the strength of what its values look like.** C0b's caveat governs: an
anchor passing means a column has the right shape, not that it is the right field.

## 14.10 Order after this section

1. **C8**, one script, six counts. Its output is appended to
   the B8 inputs register, not to a results file only.
2. `experiments/b8_omega.py`: `V`, `V̂`, `r(t)`, and nothing else. Unit-tested
   against a hand-computed amortisation schedule before it sees a real loan.
3. **B8-0a(i)**, the gate. Then B8-0a(ii).
4. B8-0b, then the predictions, each on both grids of 14.4.

---

# 15. Restructuring after B7's withdrawal

**Written 2026-08-16, before any `omega` is coded.** B7's rank is withdrawn at every
class resolution and B7-13 and B7-14 are open. What transfers to this stage is not
that finding. It is **three facts about the shape of the estimator that died**, and
B8-4 has that shape.

## 15.1 The three rules, stated once and cited by `b9_zero_holonomy.md`

**N1. A null belongs to the design that drew it.** `b7_interaction_rank.md` §3.25
compared a seventeen-class spectrum against a nineteen-class design's `null_max`.
Dropping two classes removes two of the largest noise sources **and** shrinks the
matrix, and both push a permutation null down, so the threshold was too high and too
high in the direction that made the conclusion easier. **Any operation that changes
the class set, the cell set or the sample regenerates the design.** A submatrix is
not a design. The threshold is redrawn on the new design, with `MIN_CELL_SIZE`
re-applied, or it is not used.

**N2. A cross-class second-moment estimator reads *shared* structure only.** A
diagonal `S` whose diagonal entries all sat above noise would be rank 19, one
independent direction per class, and the estimator would report 19. It reported 2.
**That licenses "no structure shared across classes" and does not license "no
structure".** Whether any single class carries its own cell-specific variation is
confounded with that class's own sampling noise and is **not separable on this
estimator at all**. No sample size fixes it, because the confound is in the
statistic and not in the precision.

**N3. The binding quantity is observations per cell in the sparsest class.** Fill
rate does not bound the reading. Co-occurrence count does not bound it. B7 died of a
number that appeared in none of its design summaries. This is the addition to
Corollary 2's scoping block that this repository bought with twenty million rows.

**And one thing that does not transfer.** B8 **may not cite B7 for "there is no
interaction"**. B7-13 aims at the live alternative that the two thin classes carry
real cell-specific interaction, and B7-14 has not returned. B8 may cite B7-11's
carry, the grid rule, and N1 to N3. It may cite no rank number.

## 15.2 §3.3's citation is void and the rule is re-based on the carry

The table in §3.3 reading fine `2`, coarse `2`, complement `0` is **withdrawn**. It
is left in place under the no-deletion rule and is not quotable.

**The two-grid rule is unchanged and its evidence is now B7-11.** Laying each fine
eigendirection on each coarsening and measuring what arrives, the complement grid
carries the fine grid's first direction at **0.15%** and its second at **0.48%**,
against **97.9%** into the six-level bucket index. **A coarsening can take a
direction from carried to not carried, measured, with a number, and that holds
whether the direction is signal or noise.** That is a sharper support for the rule
than "two grids disagreed", and it does not depend on the rank being real.

> **Every B8 reading is run on at least two `q` grids. A reading on one grid is not
> a result.** Unchanged.

## 15.3 C7 does not license B8-4, and C9 is the gate that does

C7 reported the class fields' **fill rate** on triangle-completing loans, worst
0.9621. **N3 says that statistic does not bound the reading.** C7 passing means the
fields are present. It says nothing about whether any class has enough loans per
cell for a second-moment statistic to be about the loans.

**C9, registered here.** For each class grid and each `q` grid, report the count of
triangle-completing loans per `(class x window)` cell, and the **minimum over
classes**. Print the whole distribution, not the mean.

**The floor is `min_size = 20`, and the source is this repository.**
`b2_measurement.md` §10 adopted 20 as the per-cell minimum after the `0.975`
artifact, and the graded placebo ran at it. It is not invented here. Cells below it
are excluded and **the excluded count is reported**, per §7's rule.

**If C9's minimum cannot be met on a class grid, B8-4 does not run on that grid.**
That is not a failure of B8 and must not be written as one.

## 15.4 B8-0b's noise floor is per class

§4's B8-0b reads: loans matched on class and on the full realised path carry the same
loop sum, their dispersion is `N`, the headline is `sqrt(Z)/sqrt(N)`.

**Fixed here: the class comparison uses `sqrt(Z(a)) / sqrt(N(a))`, a floor drawn per
class.** A pooled `N` makes a thin class look dispersed for the reason B7 died of.
The pooled figure is still reported beside it for B8-1, which is a pooled statistic
and for which a pooled floor is the right object.

## 15.5 B8-4 splits, and this is the substantive change

**The problem.** §5's B8-4, dispersion of `sqrt(Z)` across agent classes at fixed
path, is B7's estimator in a different costume. Thin classes disperse more from
sampling alone, and no null drawn on the pooled design separates that from a class
effect. Running it as written would reproduce B7 with mortgage servicing in place of
DTI buckets.

**The fix is a second axis.** Sampling noise does not replicate across an
independent split. A class effect does. B8 has two such axes for free.

| id | statement | axis | what it can claim |
|---|---|---|---|
| **B8-4a** | the ordering of classes by per-class median loop sum is **stable across §6's four windows**. Statistic: mean pairwise Spearman correlation of the four orderings. Null: class labels permuted **within window**, drawn on the same design | window | the class index carries structure that replicates. **All modifications, so the Flex restriction is absent and this is labelled association** |
| **B8-4b** | the same ordering is stable **across origination cohorts inside the Flex window** | cohort | **the registered discriminating version.** Flex Mod is rules-based, so "the servicer priced the risk" does not explain a stable ordering inside it |

**B8-4b's axis exists in the data already counted.** The Flex column of the C3/C4
table is populated in five of six archives: 292, 547, 607, 1,044 and 2,160. Cohort
is a registered dimension for an independent reason, since §13.4 requires
conditioning on the cohort's rate environment, so this axis costs nothing new.

**Both arms carry two further requirements, and neither is optional.**

- **Equal `n`.** Recompute after subsampling every class to the sparsest class's
  `n`. Report both figures. If the effect is present only at unequal `n`, it is a
  thinness artefact and is reported as one.
- **Print the loading.** Which classes carry the ordering, beside the magnitude.
  `b7_interaction_rank.md` read a rank for a day and a half before anyone printed
  the eigenvectors.

**What B8-4 cannot claim in any version, and this is N2 and is not fixable by
design here.** That a *particular* class carries idiosyncratic variation
distinguishable from that class's own sampling noise. The claim available is about
the class index carrying **shared, replicating** structure. **This is written into
the prediction rather than discovered afterwards.**

## 15.6 §11's branch table is re-registered, now rather than after the run

§11's first row required B8-3 and B8-4 to pass, and B8-4 is now two objects.

| B8 outcome | second domain |
|---|---|
| B8-3 passes **and B8-4b** passes | **subprime auto ABS**, as registered |
| B8-3 passes, **B8-4b** fails or does not run for want of C9 | **corporate credit**, as registered |
| B8-3 fails, B8-5 passes | **student loan rehabilitation**, as registered |
| only B8-1 passes | **no second domain** |

**B8-4a does not enter the branch table.** It is an association and choosing a
replication domain on an association is the error §11 exists to prevent.

## 15.7 The re-weighting, and why it is not ad hoc

`b1_theorem.md`'s load-bearing order, fixed 2026-08-15 and before any of this:
**Corollary 1, then Corollary 2, then Theorem 3.** Corollary 1 is an existence claim
decided by a single inequality on a single edge, and *nothing in it can be dissolved
by renaming*. Theorem 3 is the variance decomposition.

**B7 was the Theorem-3-shaped station and it is the one that died.** That is a
retrodiction of the repository's own ordering by an event the ordering did not
anticipate, so the ordering earns a use here.

**B8's headline moves from B8-1 to B8-3.**

- **B8-3** is Corollary-1-shaped: two realisable paths to the same terminal state
  carry different accumulated `omega`, an existence claim decided by a comparison of
  two populations. It survives the node-identity objection by construction, and
  §14.4 gave it an institutional contrast with **51,286 against 32,533** events
  rather than a timing contrast.
- **B8-1** remains a headline reading and is now the supporting one. It depends on
  the walk closing at a node whose identity a critic can dispute, and on a pooled
  noise floor.
- **B8-4a and B8-4b** are the second-moment statistics and they sit last, with
  15.5's requirements attached.

**Both are still run and both are still reported.** This is a re-weighting of
registered predictions made before the run and recorded here with its reason.

## 15.8 What this section does not change

§2.2's identity argument, §2.3's irreversibility argument, §14's entire `omega`
construction, C8, the four windows, §7's filters, §9's four scope limits. **B7's
death is about an estimator that reads a class-indexed second moment. `omega` is not
one, B8-0a is not one, B8-1 is not one and B8-3 is not one.**

---

# 16. Splitting the B8-0a(i) gate (2026-08-16)

**Sections 1 to 15 stand, and this section overrides them where they conflict.**
Ruled by the author; the full text and the quantification are in the project's
B8-0a tolerance ruling, and the run record is in the B8 inputs register
sections 6.2.6 to 6.2.8. **Written before `omega` was coded. B8-0a(i) has never
been run.**

## 16.1 Section 14.5's implicit assumption, and the numbers that refute it

Section 14.5 defined B8-0a(i) as "a clean-cure out-and-back, using only the
contractual triple, **returning to zero exactly within floating-point
tolerance**", on the grounds that the zero is arithmetic: the positive residual
of an underpaid month cancels the negative residual of the month that restores
it.

**For that cancellation to hold there is a premise section 14.5 never wrote
down: the balance path returns exactly to the schedule.** Measured on 140
million quiet performing months:

- about a quarter of quiet performing months **do not lie on the schedule**
  (C8-1c(b));
- about half of those are **a balance that does not move for a month**, which is
  **4.881 percent** of all quiet months across the six vintages (C8-1e);
- after a freeze, lag-1 recovery is only 26 to 28 percent and within six months
  52 to 59 percent, so **about four in ten never recover** (C8-1f);
- **one unrecovered freeze contributes to `r` exactly what one underpaid month's
  ω₁ contributes** (1.336e-3 on the reference loans in both cases);
- for segments containing a freeze, the p10 of the post-schedule deviation is
  −2.6 to −9.9 percent, while **for segments without one it is −0.0000**.

## 16.2 The split

| id | runs on | criterion | standing |
|---|---|---|---|
| **B8-0a(i-a)** | those clean-cure loans **every one of whose quiet months lies inside its segment's modal cluster** | **exact return to zero within floating-point tolerance** | **a gate.** If it fails the construction is broken and nothing after it may be read |
| **B8-0a(i-b)** | **all** clean-cure loops | the distribution of loop sums, against the noise floor from never-delinquent loans over windows of the same length | **a reading, not a gate** |

**Section 8's first falsification line moves to B8-0a(i-a).** Section 14.5's
B8-0a(ii) (with fees and capitalisation) is unchanged, but per section 6.2.1 it
has already been narrowed: field 64 is positive on zero loans in all six
vintages, so **the forgiveness term is identically zero on this sample**.

## 16.3 The (i-a) sample, and two qualifications that must travel with it

**19,090 loans**, which is **12.35 percent** of the 154,768 with the clean-cure
shape, at 138 / 238 / 256 / 2,652 / 7,862 / 7,944 by vintage.

1. **The sample is heavily skewed toward recent vintages.** 2002Q1 retains only
   2.40 percent and 2019Q1 retains 19.94 percent. **The gate is certified mainly
   on the 2017 and 2019 cohorts.**
2. **The subsample is selected on payment regularity**, and payment regularity is
   plausibly correlated with section 5's class indicators (credit score, DTI),
   **so it is not a random sample in class space and may not be reused for any
   B8-4 shaped reading.**

## 16.4 A structural limitation added to section 9

> One balance freeze that falls inside a loop and never recovers injects into
> `omega` something **indistinguishable from, and the same size as**, a real
> underpaid month, because in `V` they are the same event and the only
> difference is that field 40 reads `00`.
> **This sets a lower bound on B8-1's noise floor that no sample size can lower,
> and every citation of B8-1 must carry this sentence.**

## 16.5 Two corrections to section 14.10

**Field 44 does not need to be in the filter.** The earlier concern that "the
quiet filter fails to check the zero-balance code, so payoff months are in the
sample" **is withdrawn**: field 44 is not set on a single one of roughly forty
million quiet months across the six vintages (B8 inputs register section
6.2.6.3).

> **[second correction, 2026-08-16] That withdrawal was itself wrong, see section
> 16.6.** The field 44 half still holds, **but a termination is marked by the
> balance going to zero and not by the zero-balance code**, and the quiet filter
> did fail to check for the balance going to zero. **The filter now carries
> `upb[current row] > 0`.**

**The monthly payment is a state carried segment by segment**, fixed by section
6.2.5, and both `V` and `V̂` use it.

## 16.6 The withdrawal in section 16.5 was wrong, and the quiet filter has gained a condition (2026-08-16)

Section 16.5 said "field 44 need not be in the filter, and the concern about
payoff months in the sample is withdrawn". **That withdrawal was wrong. The
field 44 half still holds (it really is unset on some forty million quiet
months), but a termination is marked by the balance going to zero rather than by
the zero-balance code, and the quiet filter did fail to check for that.**

The cause was a measured Fannie reporting convention: **the first row of every
loan carries a zero UPB**, 1.0000 with no exceptions in all six vintages, at an
average of 6.70 to 6.94 such rows per loan, and nothing is reported after
termination (B8 inputs register section 6.2.9). So the pair "positive to zero"
could pass the old filter, with `obs` equal to the entire balance.

**The correction**: `quiet_pairs` now also requires `upb[current row] > 0`. The
old definition is preserved and bit-reproducible via `require_cur_positive=False`,
and `selftest` exercises both and requires them to differ. Full text and blast
radius in B8 inputs register section 6.2.10 and the project's B8-0a gate ruling
section 3.

**[same-day correction, 2026-08-16] This passage originally said the
contamination lay on the side above the mode. Measurement refutes it: this
correction deletes zero pairs in all six vintages** (B8 inputs register section
6.2.10.2, `results/b8_quiet_delta.md`). The 8.8 percent and the median in
section 6.2.6 are indeed unaffected, **but the reason is that there was no
contamination at all, not that it sat on the other side**.

**The correction is therefore a guard and not a fix.** The criterion does not
change; what changes is that it is inert on the real machine: on the termination
row **the remaining legal term is empty** (5 / 2 / 5 / 1 / 0 / 0 leak through
across the six) and the coupon rate is empty as well (a few hundred each), and
those two already block every payoff pair. **This generalises the reporting
convention at the top of this section: a termination row reports a zero balance
and then stops reporting the contract state altogether.**

## 16.7 B8-0a(i-a) passes in all six vintages, and what passes it is the count and not the ratio

**Step 3 of section 10 is closed here.** `over 1` is zero in all six vintages,
with qualification rates of 0.5195 to 0.6597. The table is in B8 inputs register
section 6.2.11.1 and the result in `results/b8_0a_gate.md`.

**A sentence that has to travel with the verdict**: `max ratio` lands between
0.399 and 0.400 in all six vintages, which is the structural upper bound
`(1 + (1+i)^(k+1)) / ((2+i)(k+1) + (1+i)^(k+1))`, because the path tolerance and
the agreement bound share a single `1/B`.
**The agreement half is mathematically implied by the path half and carries no
independent information. All of the gate's discriminating power is in the
qualifying count.**

That power is real: a 1 percent error in the monthly payment moves the endpoint
by $30.55 against a tolerance of $0.0101, a factor of three thousand, and the
qualifying count would collapse toward zero.

**Add this sentence wherever (i-a) is cited, on top of the two qualifications in
section 16.3.**

## 16.8 (i-b) has a number: loops carry a residual 172 to 2,343 times the noise floor

B8 inputs register section 6.2.11.4. The closed form has been subtracted, and
what remains is the observed path's deviation from the ideal path, coming mainly
from fees, partial restoration and escrow in the month of the cure. **The signal
that section 14.5 said splitting 0a was meant to preserve now has a number.**

## 16.9 Section 7's filters: three cannot be earned, one uses a behavioural proxy

The core table has no product type column, and product type, unit count and lien
position are not in the C0b anchor table. **Fixed rate can be earned
behaviourally**: if a loan's rate moves only in the month of a modification, it
is fixed rate. The floating shape peaks in 2006 and 2007 (2.46 and 3.34 percent)
and is one in ten thousand after 2012, **and the peak lands exactly on the ARM
wave without the procedure being given any product type information**.
**This is a proxy and is labelled as one wherever it is cited.**
Owner-occupancy can be filtered (field 30 is confirmed); single-family and first
lien cannot. See B8 inputs register section 6.2.12.2.

## 16.10 The order after section 14.10, re-sequenced on this round's results

**B8-0b comes after the Treasury CMT curve, not before it.** The reason: P2 in
`b8_omega.py` proves that on the contractual triple the discount curve cancels
completely, so B8-0a needs no Treasury data. But the cancellation requires `V`
and `V̂` to share one `(i, n, d)`, and **in the month of a modification both the
rate and the term change**, so `k(i, d, n)` differs between the two sides and
the curve enters (measured: `r` moves from −0.000487 to −0.000494 as CMT goes
from 0.5 to 15 percent). B8-0b's `N` is the dispersion of loop sums over matched
loans on the modification triangle, **so computing it requires pricing the month
of the modification first**.

| order | station | reason |
|---|---|---|
| 1 | **C9** (observations per cell, `min_size = 20`) | about twenty seconds on the core table. It decides whether a per-class floor is needed at all, which grid B8-4 runs on, and whether all vintages have to be downloaded |
| 2 | **the CMT curve station** | a hard blocker for everything after B8-1. **Two construction choices have to be fixed before it starts**, see section 16.11 |
| 3 | **B8-0b pooled floor**, then B8-1 / B8-2 / B8-3 | section 15.7's headline needs only the pooled `N` |
| 4 | **the per-class floor and B8-4a / B8-4b** | only section 15.4 needs `√Z(a)/√N(a)`, and per section 15.3 it is gated by C9 |

**The per-class noise floor is not mandatory. It is conditional, and the
condition is C9.**

## 16.11 Two things the CMT curve station has to fix before it starts (the same kind of thing as C8)

**One, how to interpolate to the remaining term**: linear in tenor or linear in
log tenor. The registration says only "interpolate".

**Two, what to do when the term exceeds the longest available tenor**, and this
is a real dated gap: **the thirty-year CMT does not exist between 2002-02 and
2006-02** (Treasury suspended the thirty-year bond), which is exactly the window
in which the 2002Q1 cohort is young and its remaining term is near 360 months;
the twenty-year is also missing between 1987 and 1993. **Extrapolate or cap:
write it down before the run.**

## 16.12 C9 has run: B8-4a has five grids and B8-4b has none (2026-08-16)

Section 15.3's gate has an answer. Full text in B8 inputs register section 6.4
and the project's C9 ruling; result in `results/b8_c9_cells.md`.

**The five usable for B8-4a all hang on the borrower** (floor 20, on
`(class × the four windows of section 6)`, six vintages pooled): `purpose` 826 /
`fthb` 237 / `fico_llpa_coarse5` 74 / `dti_complement15` 49 / `fico_llpa9` 36.
`ltv_llpa_coarse4` (82) and `occupancy` (36) clear the floor but hang on the
dwelling per section 2.4 and are not usable grids for B8-4. **The two gates are
independent and both have to be passed.**

**A sentence that must travel with it: among those that clear, the comfortable
ones are the coarse ones and the fine ones sit on the floor.** `fthb` has two
levels and `purpose` three, coarse enough to barely constitute a class
indicator; the one with resolution, `fico_llpa9` at nine levels, reaches only
36. The only DTI grid that clears is `complement15`, and section 3.3 measured
that grid's rank as 0. **Clearing C9 says a reading may be attempted, not that
the reading is credible.**

**All eleven fail for B8-4b**, with a minimum of 0 or 1 and the argmin mostly at
`2019Q1`: the Flex modification window is 2017 to 2019 and the 2019Q1 cohort has
at most one year of age inside it. **Section 15.6's branch therefore lands and
the second domain points to corporate credit**, conditional on B8-3 passing.
**Section 15.3 states explicitly that this is not a failure of B8.**

## 16.13 Where the band edges come from, and an asymmetry that travels with every citation

Section 5 says only "band". **FICO and LTV take the issuer's own pricing
partition** (the Fannie LLPA Matrix, Table 1, current version effective
2026-01-28), on the same principle by which section 3.3's main `q` grid takes
the delinquency status field's own partition. **DTI has no issuer partition**:
every DTI-based LLPA was **removed on 2023-05-17**, so DTI takes the regulatory
HMDA published bands, which is the grid section 3.3 already measured.
**The two are not the same kind of source, and this asymmetry travels with every
citation of a DTI band.**

## 16.14 Section 3.3's conclusion reproduced independently by a pure count

`dti_complement15` clears at fifteen levels (49) and `dti_coarse6` fails at six
(11), and the only difference is that complement folds `>60` into "outside
36-49" while coarse6 leaves it standing. **More levels survive and fewer levels
die.** Section 3.3 measured this on B7's rank statistic; **this time it is a pure
count, on different data, giving the same structural conclusion.**

## 16.15 The triangles are on the core table and reconcile with C3/C4 window by window

`experiments/b8_triangles.py`, all five windows at +0, totalling 51,286.
**This is the only copy of the triangle criterion on the core table**, and C9 and
every later station that samples on triangles draws from it; no second
hand-written copy is permitted. Both transcription risks (the deferral leg of
`cured_after_mod`, and the length convention of the delinquency encoding) were
measured, and the latter is zero in all six vintages.

## 16.16 The curve station has run: both construction rules are measured to be inert, but the population behind the gate cannot yield a monthly payment (2026-08-17)

Section 16.11 has an answer. Full text in B8 inputs register section 6.5 and the
project's curve-station ruling.

**One, the 47-month gap in the 30-year is a property of the curve.** Treasury is
missing 2002-03 to 2006-01 and FRED is not, and **CMT is defined by the issuer,
so what the issuer did not sell does not exist**; what FRED has there is
something else. Modifications falling in the gap are 1,506 of 50,958, or 2.96
percent.

**Two, on the measurable population both construction rules fall short of any
reading.** The maximum spread in loop sums is 4.974e-14, **eight orders of
magnitude below** the (i-b) noise floor of 6.5e-6. P2's cancellation holds on
every real row with no deferred balance, with a maximum spread of 3.553e-15
against a criterion with a source, `4·|log V|·eps`.
**The two rules still had to be written down before the run**: an invisible
choice has to be recorded too, or the next person cannot tell whether it was
considered or overlooked.

**Three, the single-leg sensitivity of `log V` was the wrong object.** The first
measurement gave 267 to 7,110 times the noise floor, and that quantity cancels
exactly inside `r`, because `r_month`'s two legs share `(i, n, d)`. The voided
document is on file.

## 16.17 A new blocker, ahead of the curve, and it blocks B8-3

**The deferral leg cannot yield a contractual monthly payment.** `r` is computed
only where the payment is known, the payment is estimated from quiet months, and
`quiet_pairs(require_never_deferred=True)` excludes ever-deferred loans. Across
the six vintages there are **703,504 deferral rows and the payment is known on
zero of them**, which is a consequence of the construction and not missing data.

**Section 14.4's main B8-3 path pair is "modification" against "deferral", one
on each side**, so **B8-3 is stuck here, and it is the one criterion in section 5
that does not need to win the node-identity objection**.

A route to test: a deferral does not change the payment, so estimate it from the
quiet months before the deferral and carry it forward. **That is inference and it
has to be measured.**

## 16.18 The loop window for the modification triangle has never been defined

`find_clean_cures` defines the clean cure without a modification. **The loop
window for the modification triangle has never been defined anywhere.** What
`b8_cmt_sensitivity2.py` uses, "first delinquent row to the first cure after the
modification", was defined ad hoc so that there would be something to sum over,
and both the code and the result file state that it **may not be cited as a
registration**.
**Everything after B8-1 needs it. This is an item awaiting registration.**

---

# 17. Registering the loop window, and the two curve construction rules (2026-08-17)

**A registration. It reads no prediction and changes no number already run.** It
closes **O25** (the loop window is undefined) and **O21** (the two curve rules
are not fixed) in the project's objection cache, which is held outside this
repository. The full text is also kept in the project's
loop-window and curve-rule pre-registration, outside this repository.

## 17.0 Where this attaches, and why it is not newly invented

**Section 14.6 already wrote the conceptual layer**: "the duration of the closed
loop, from the last current month before the episode to the first current month
after it". What was missing is the row-level operationalisation, **and one
already exists**: `t0 / start / end` in `b8_0a_gate.find_clean_cures`, whose
docstring cites section 14.6 and whose residual runs over `t0+1 .. end`.

**So this section invents no window. It generalises the existing one to the
modification and deferral legs and fixes the choices that generalising forces.**
`find_clean_cures` is this section's special case of `event onset count == 0`.

## 17.1 Three row indices and the range of the sum

```
t_A   departure vertex, current
t_M   the modification (or deferral) onset row
t_B   return vertex, the first current after the modification
ω(loop) = Σ_{t = t_A+1}^{t_B} r(t)
```

`r(t)` is defined on the adjacent row pair `(t-1, t)`, so the sum runs from
`t_A+1` to `t_B` inclusive, covering both end pairs. **The departure row itself
contributes no residual**; it is the anchor for `V`. The window is `t_B − t_A`
months long, which is section 14.6's denominator.

## 17.2 The start is anchored backwards from the modification, and there is no current row anywhere inside the window

Two conditions, both required:

- **(a)** walk back from `t_M` to the nearest `current` row `t_A`, requiring that
  no row in `(t_A, t_M)` is `current`;
- **(b)** take `t_B` as the first `current` row after `t_M`, so by definition
  there is no `current` in `(t_M, t_B)` either.

**Together: there is no `current` row anywhere inside `(t_A, t_B)`. That
sentence is the whole content of "this is one loop and not two", and it is
written out rather than left for the reader to derive from (a) and (b).**

This is a substantive disagreement with `b8_cmt_sensitivity2.triangle_window`,
and it has to be one. That one takes **the loan's first** delinquent row
(`_first_pos_per_loan(is_del)`). Three reasons:

1. **A walk that passes through `current` is not one loop, it is two.** Summing
   them as one erases exactly the distinction B8-3 needs: section 5's candidate
   path pair names "cure, redefault, then modify" against "modify on the first
   episode".
2. **It matches `find_clean_cures`.** A clean cure is by construction one
   continuous delinquency spell. Both zero calibrations have to cut the same way
   for B8-0a to be B8-1's zero calibration rather than a different object.
3. **The ad hoc window swallows an earlier episode that already cured**, and
   that stretch is B8-0a's sample. Swallowing it mixes the gate's sample into
   the reading.

## 17.3 Modification and cure on the same row: `t_M == t_B`, and leg 3 is empty by construction

The transcription rule in `b8_triangles.py` says "a row that turns the flag on
and reads `00` counts as cured after modification, not before it". **So the
modification row can read `00`**, in which case `t_M == t_B`, `leg 3` is an empty
interval, and the loop is `leg 1 + leg 2`.

**Loops of this kind are counted separately and may not be mixed into any
reading of `ω₃`.** Section 14.3 says `ω₃ ≈ 0` is "measured rather than assumed",
while on these loops it is **identically zero by construction**. Reported
together, the sentence "`ω₃` measures near zero" would be propped up by a batch
of loops that were zero to begin with.
**This is the same family as pit 23 in B8's pit ledger (kept outside this
repository): the sum over an empty set prints exactly like a measured zero.**

## 17.4 Two onset kinds in one loop: that edge is not in the graph section 14.4 registered

A loop whose continuous delinquency spell contains **both** a modification onset
and a deferral onset walks the edge `deferred → modified` (or its reverse), and
**that edge is not among the five section 14.4 registers**
(`current→delinquent`, `delinquent→modified`, `modified→current`,
`delinquent→deferred`, `deferred→current`).

**Disposition: identify separately, count separately, exclude from both triangle
legs.** It is a longer walk and belongs to section 17.5's path material, not to
B8-1's triangles. The leg is named after the type of the first onset in the
spell, **used only to give these loops a name and never to push them back into a
leg**.

## 17.5 The path accumulation `Ω` is a different object, and both citations have to say which

| notation | what it is |
|---|---|
| `ω(loop)` | the residual sum of one closed walk. **The atom. B8-1 and B8-2 read it.** |
| `Ω(path)` | the sum of `ω` over **all** loops the loan has walked up to the endpoint. **B8-3 reads it.** |

"Cure, redefault, then modify" has two terms in its `Ω` (a clean-cure loop plus
a modification triangle); "modify on the first episode" has one. **B8-3's own
words are accumulated `ω`, and that is `Ω`.** Without separate names, B8-3 gets
implemented as a single-loop comparison, and a single-loop comparison cannot
measure what it is for.

## 17.6 The vertex conditions: two load-bearing, one a guard

The departure vertex `t_A` and the return vertex `t_B` take the same three:

| condition | standing | source |
|---|---|---|
| `delinq == 0` | load-bearing | the vertex definition |
| `rem_legal` non-empty | **load-bearing** | the second correction to pit 13: a termination row reports a zero balance and then stops reporting the contract state altogether, and **this is what blocks termination rows** (5/2/5/1/0/0 leak through across the six vintages) |
| `upb > 0` | **a guard** | the same correction deletes zero pairs in all six vintages, so its standing is a guard and not a fix, per section 16.6 |

**One more folded into `upb > 0`: the departure vertex may not be the loan's
first row** (pit 13; the first row's UPB is identically zero, 1.0000 in all six
vintages). It is implied by `upb > 0`, **but its count is printed separately**,
because it is a construction truncation rather than a data defect and the two
are ruled on differently.

**And one inherited unchanged from `find_clean_cures`**: reported months inside
the window must be contiguous (`period` differences identically 1). A window with
a gap cannot be carried month by month; it is discarded and counted.

## 17.7 Three ways a loop fails to close, counted separately, never merged into one "dropped" figure

1. **still delinquent at the end of the file** — right censoring.
2. **terminated and never cured** — genuinely no loop.
3. **no continuous delinquency spell before the modification** — not a triangle
   (field 42 turns `Y` on a `current` row).

The three counts are reported separately. Section 7's rule: silence about a
dropped record is how a sample becomes a selection. **Merging 1 and 2 is the
easiest mistake to make**: one is a property of the observation window and the
other is a property of the loan.

## 17.8 Several onsets of the same kind inside one loop: one loop, with a separate count

`t_M` takes the **first** onset inside the continuous delinquency spell. Later
onsets of the same kind within the spell remain inside the window and enter the
loop sum. **An onset after the return opens a new loop.**

**Loops with more than one same-kind onset inside the spell are counted
separately**: that is the population of HAMP trial periods converting, which
section 14.3 already describes as "measured rather than assumed", and this gives
it a countable carrier. (Onsets of different kinds go to section 17.4.)

## 17.9 The deferral leg takes the same window rule; the onset column was an open question and this section does not rule on it

The deferral triangle `current → delinquent → deferred → current` has the same
shape, **and the window rule is unchanged word for word**.

**The deferral onset is field 108.** The rising edges of the two columns differ
by a factor of 13 to 18 in measurement (267 against 4,882 in 2012Q1; 1,124
against 14,777 in 2019Q1). **This registration writes one sentence: the window
rule and the choice of onset column are two different things, and changing the
column does not change the window.**

**The original text listed the column choice as an open question in O24 and B10
section 19.9, and that sentence has been deleted.** The question closed on
2026-08-17, and what this section guaranteed is what was then honoured. C10-4
read, on both columns' rising edges, whether the contract moves: on the field 63
side the rate moves 46.1 percent of the time and the term 84.2 percent, while on
the field 108 side `still = 0.9966` (neither rate nor term moves). **The deferral
onset is field 108**, which is verdict B in B8 inputs register section 6.6.11,
and O27 closed as D20.

**Changing the column changed not one word of this section**, which is the whole
point of writing that guarantee when it was written: after `DEFER_FIELD` in
`b8_loops.py` moved from 63 to 108, sections 17.1 to 17.8 did not move a line,
and the re-run window counts moved with the new onset while the definition of
the window did not.
**A guarantee written before a ruling and honoured after it is worth more than
an explanation added afterwards.**

## 17.10 Measurability: the payment must be known across the window, with drops printed separately for each side of the modification

`r(t)` is computed only where the contractual payment is known, **and what is
needed is the previous row's payment** (section 14.2's counterfactual carries the
`t−1` contract forward by one month). The modification leg's window crosses a
contract-period boundary by construction; the deferral leg's does not.
**So a loop is measurable when every month inside the window has a known payment
on its previous row.**

**The drop counts must be printed separately for the pre-modification and
post-modification sides.**

**Two deletions and a correction, 2026-08-17. Two sentences have been removed:
one saying `contract_periods` cuts at both the modification and the deferral
onset, and one saying the payment is known on zero deferral rows (703,504 across
the six vintages). The requirement to print drops per side survives, and the
reason attached to it has been replaced entirely.**

**One, the cut points.** `contract_periods` **does not cut at field 108**, and
section 6.6.17.2 rules explicitly that it must not: C10-4 reads `still = 0.9966`
at field 108's rising edge, neither rate nor term moves, the contractual payment
cannot have changed, and cutting there would only split one contract period into
two with fewer quiet months each and a worse estimate. **It cuts at field 63's
rising edge**, because that side is a re-signing.
**So whether the window crosses a contract-period boundary depends on which leg
the loop walks**: the modification leg crosses, the deferral leg does not. The
deleted half-sentence described both legs as one shape.

**Two, 703,504 is not a count of deferral rows.** It is **the on-row count of
field 63**, that is, of the modification population, and it was cited as deferral
rows throughout (O24 has been rewritten accordingly). The deferral leg's
measurement is in section 6.6.15: **the payment is known across the whole path
for 92.86 percent**, not zero.

**So the judgement that this was the station's largest blocker does not stand
either, while the requirement to print each side survives.** Its reason now is
not that one side is identically zero but that **the two legs have different
contract-period structure to begin with** (see above), and a merged drop count
mixes two different kinds of measurability.
**A requirement whose reason has been refuted, if it still stands on its own,
has to be given a new reason rather than kept on the momentum of the old one.**

## 17.11 Splitting into legs is bookkeeping, the loop sum does not depend on it, but the identity is asserted

Fixed by section 14.2. The cut points:

```
leg 1 = (t_A, t_M)      current → delinquent
leg 2 = the single month t_M     delinquent → modified
leg 3 = (t_M, t_B]      modified → current
```

**The three parts sum identically to the loop sum, which is an identity and not
a criterion**, but it is asserted in code.
**When `t_M == t_B`, leg 3 is an empty sum and the assertion still holds**, so
the assertion cannot substitute for the count in section 17.3.

**Deleted and corrected 2026-08-17: the original reason given was that it would
catch a misalignment in the window implementation, and that sentence has been
removed because it is false. The requirement itself stays.**
All four quantities come from the same prefix-sum array, the three legs telescope,
**and the identity holds for any `t_M`** — off by one row, off by ten, or even
belonging to a different loan. **Under a prefix-sum implementation this assertion
tests the floating-point adder and cannot catch the misalignment it was written
to catch.**

The assertion stays (it does catch a broken prefix sum or a broken range helper),
**and one that actually does the job has been added**: `b8_loop_omega.replay`
starts from the window indices and re-sums month by month in Python, comparing
against the vectorised answer. The self-test deliberately moves `t_M` by one row
and **asserts that the identity still holds while `replay` reports a mismatch**,
which is a check on the check.

**The lesson is not in this section, it is at the method layer**: when an
assertion is written down, ask whether it can fail **under the implementation
that will actually be used**, not whether it can fail in principle. See B8 inputs
register section 6.6.23.3.

## 17.12 What this registration supersedes, and what it owes

`b8_cmt_sensitivity2.triangle_window` **is void as a registration** (it already
states that it may not be cited).

The loop-level numbers in `results/b8_cmt_sensitivity2.md` section 3 were
produced under that ad hoc window. Under R01, changing a definition requires
reporting both: **the next re-run of the curve sensitivity under the registered
window must print the loop counts and loop sums under both windows, and must
print the delta** (pit 18: a re-run that cannot be differenced against the old
definition does not discharge the double report).

The ad hoc window's loop counts are on file:
**6,272 / 13,134 / 17,061 / 2,954 / 5,411 / 4,647**.

## 17.13 A non-conflict that has to be stated first: C3/C4 count loans, section 17 counts loops

The C3/C4 criteria in `b8_triangles.py` fire **once per loan**
(`if s.mod_period and s.seen_current and s.first_delinq and s.cured_after_mod`),
and the six-vintage total of **51,286** is **a loan count**.

**Section 17's loops are one per closed walk, and one loan can have several.**
The two numbers are not the same object, and the direction is not one-way:

- one loan can contribute several loops, so the loop count can exceed 51,286;
- a loan counted by C3/C4 can contribute **zero** registered loops (for example
  the walk that turns `Y` on a `current` row, then redefaults and cures, which is
  case 3 in section 17.7).

**The difference between the two numbers has to be measured and printed, and may
not be assumed small.** Section 16.15's rule that there is only one copy of the
triangle criterion means the criterion is written once. **It does not mean a loop
is a triangle.**

---

## 17.14 The curve, interpolation: linear in tenor (`linear_in_tenor`)

**Source.** Treasury publishes CMT at fixed tenors and **there is no issuer
convention between tenors**, so section 16.13's rule of taking the issuer's own
partition has no object here. That falls to the secondary rule: **take the one
that introduces no free parameter**, which is linear in tenor.

## 17.15 The curve, beyond the longest available tenor: cap (`cap`)

**The source is not conservatism, it is consistency with a ruling already made.**
Section 16.16's first item ruled that **CMT is defined by the issuer, so what the
issuer did not sell does not exist**, and on that basis the 47-month gap in the
30-year was judged a property of the curve rather than a download artefact (two
sources cross-checked).

**Extrapolating amounts to inventing a price for a tenor the issuer refused to
sell, which conflicts with that ruling directly.** One principle, and the two
conclusions have to agree, or that ruling was only an ad hoc way to explain the
gap.

**The consequence, stated and travelling with every citation:** between 2002-03
and 2006-01, a loan with 360 months remaining reads the longest tenor available
that month (20-year, in that stretch). Modifications falling in the gap are
**1,506 of 50,958, or 2.96 percent**.

## 17.16 Today these two rules cannot reach a single row, and that is **not** the same as "measured not load-bearing"

Section 16.16's phrase "both construction rules are measured to be inert" **is
too loose, and this section tightens it**. Item by item:

1. **On rows with no deferred balance, `r` is bit-identical across all six
   constructions** (maximum spread 3.553e-15, against a criterion of
   `4·|log V|·eps` = 1.243e-14). **That is algebraic cancellation, not curve
   robustness**: `V = LP(bal, i, n)·A(d, n)`, `LP` is linear in the balance, the
   two legs share `(i, n, d)`, and the annuity factor cancels entirely.
2. **The only door the curve can come through is the balloon term**
   `nib·(1+d)^-bn`.
3. **Among rows with a balloon, the payment is known on zero of them, and loops
   with a balloon are zero** in all six vintages.
4. So **4.974e-14 is not an effect size for the curve rules; it is the rounding
   left after the cancellation.** The correct phrasing is **out of reach today**,
   not "not load-bearing".
5. **When this changes**: once O24 is resolved and the deferral leg enters, the
   balloon term gets rows with a known payment for the first time.
   **That day this table has to be re-run, and today's readings may not be cited
   as showing the rules are not load-bearing.**

**2026-08-17: that day arrived and this table is now owed.** The trigger is item
5's own condition and both halves have occurred: O24 has been rewritten per
section 6.6.15 (the 703,504 is an on-row count of field 63, and the deferral
leg's whole-path payment coverage is **92.86 percent**), and the carrier has been
fixed to field 108 by C10-4.
**The balloon term has rows with a known payment for the first time, so item 3's
"loops with a balloon are zero" no longer holds.**

**The debt is recorded here: `b8_cmt_sensitivity`'s six-construction comparison
has to be re-run after `V`'s definition changes**, and re-read on rows that
**carry a balloon and have a known payment**, which is the only door item 2
identifies.
**Until it is re-run, items 1 to 4 hold only for rows without a balloon and may
not be cited as showing the curve rules are not load-bearing.** Changing "not
load-bearing" to "out of reach today" was done precisely so that when this day
came there would be a debt to pay rather than a conclusion already written down.

## 17.17 A newly registered defect: an empty set prints zero, and pit 23 recurs one section away in the same file

`results/b8_cmt_sensitivity2.md` section 2 already prints `not measurable` for
unmeasurable cells, **while section 3's three columns (loops with a balloon,
their p50, their max) still print `0` and `0.000e+00`.** A median over an empty
set prints exactly like a measured zero, which is pit 23 word for word.
**Same round, same file, one section apart.** Added as entry 26 of B8's pit
ledger.

## 17.18 What this section does not rule on

| item | why not here |
|---|---|
| **the deferral onset: already ruled to be field 108** | C10-4 verdict B, O27 closed as D20 (2026-08-17). **Section 17.9's guarantee that changing the column does not change the window has been honoured**: not a word of this section moved when the column changed |
| whether to raise `MIN_QUIET_FOR_PAYMENT` | the coverage distribution is printed; it is a separate matter |
| section 7's three unapplied filters (single family, first lien, owner-occupied) | unrelated to the window, recorded elsewhere |
| O18's 46.65 percent of unnamed underpaid months | unrelated to the window |
| the expected sign of the loop sum | section 14.3 covers it; it is a race between two terms and cannot be fixed in advance |

---


# 18. Pre-registering B8-0b: what `Z` and `N` actually are

**Written 2026-08-17. The loop sums had run and not one number from them was
cited here.** This section defines B8-0b's two quantities, the construction of
the matching cells, and the disposition for each outcome.
**Section 8 governs it: no changes after the run.**

## 18.1 `Z`'s shape comes from B3 and is copied

`b3_cip_slice.md` section 3:

```
Z(g) := (1 / k²) · Σ_{i,j ∈ g} ( x(i) − x(j) )²      =  2 · Var_i( x(i) )
```

On B8, `x(i)` is **loop `i`'s loop sum `ω`** and `g` is the group of loops being
compared. **Both routes are computed and must agree to machine precision**, which
is B3-1's check copied over: enumerate the ordered pairs and the variance, with a
relative error below `1e-12`.

**Units**: `ω` is a log ratio and dimensionless. `√Z` has the same units as `ω`
and can be read alongside it directly.

## 18.2 `N` has two candidates and the registration text is ambiguous between them; **this rules**

Section 4 says "loans matched on class and on the full realised path should carry
the same loop sum. Their dispersion is `N`".
Section 14.5 says B8-0a(ii) is "the tightest zero calibration this stage has".
**These are two different objects, and B3's `N` is the second kind.**

| candidate | construction | problem |
|---|---|---|
| **A: dispersion inside a matching cell** | cell on (class, realised path), then `2·Var(ω)` within the cell | **It is not measurement noise.** Two loans on the same delinquency path can be modified on completely different terms (one a rate cut, one a term extension), so their `ω` differs, **and that difference is real heterogeneity, not noise**. Using it as a floor puts signal into the floor |
| **B: the zero-calibration arm** | the loop sums of clean cures, whose true value is zero by construction | this is the shape of B3's `N` (two constructions reading one object) and it is what section 14.5 already named |

**Ruling: `N` takes B, and the within-cell dispersion gets its own name `M`.
Both are reported.**

Three reasons, in order of weight:

1. **A puts signal into the floor.** What `Z` measures is precisely "two people
   who walked the same circuit got different `ω`". A's within-cell dispersion
   measures a subset of that same thing. **Using a subset of a quantity as its
   own floor pushes the ratio toward 1, and how far depends on how finely the
   cells are cut**, which makes it a criterion the cutting can manipulate.
2. **B has a true value.** A clean cure's contract **really did not change**, so
   the true `ω` is zero and everything remaining is construction error, reporting
   noise and freezes (section 6.2.7 measured the freezes).
   **This is "an arm whose true value is zero, run through the same machine",
   which is what item 7 of `MEASUREMENT.md` asks for.**
3. **`M` is still worth reporting, but it is a different thing**: it is the
   reading "how little of `ω` the path explains", which is a prerequisite for
   B8-4 and not B8-1's floor. **Report it, label it, keep it out of the ratio.**

## 18.3 `N`'s exact definition, item by item

```
N := 2 · Var( ω(loop) )   over clean-cure loops
```

**The clean-cure loop is defined directly by `b8_0a_gate.find_clean_cures`**, with
no second copy: has been delinquent, returned to current, **never carried a `Y`
in field 42, never carried a positive field 63, never carried a positive field
108** (the post-O28 definition).

Four further constraints, all written before the run:

| # | constraint | why |
|---|---|---|
| N1 | loop sums go through **the same code path** (`b8_omega.row_residuals` plus `b8_loop_omega.loop_sums`), with no separate summation written for clean cures | B3's `z(i,i)=0` rule: a zero calibration has to run through the same machine and may not short-circuit it |
| N2 | the window uses section 17's rule, with `t_M` taken as the first month of the delinquency spell | a clean cure has no modification onset, so `t_M` needs its own definition: **take the first delinquent month**, which keeps the leg split valid while leg 2 stops being "the modification month" |
| N3 | the measurability condition is section 17.10's, word for word | the floor and the signal must be drawn on the same measurable set, or the comparison is between two populations |
| N4 | **computed per vintage, and pooled as well**. The pooled one is what B8-1 uses (section 15.4) | fixed by section 15.4 |

**N2 is this section's only new construction and it has a known consequence**: a
clean cure's leg 2 is not a re-signing, so the three-leg split is bookkeeping
within bookkeeping on this arm. **`N` uses only the loop sum, never the legs.**

## 18.4 The matching cell `M`: how it is cut, and what it may **not** be cut on

```
M := 2 · Var( ω )  within a cell, then averaged weighted by cell size
```

The cell keys, **three of them, all outside `ω`'s arithmetic**:

| key | values | why it is not circular |
|---|---|---|
| leg | modification / deferral | section 14.4's level, unrelated to `ω`'s arithmetic |
| months missed | `t_M − t_A`, banded on section 3.3's coarse grid | a path, not a contract |
| time to return | `t_B − t_M`, banded the same way | a path, not a contract |

**Explicitly barred from the cell keys: rate, term, balance, payment, balloon,
and anything in the class index derived from the contract.** The reason in one
sentence: **`ω` is a function of those quantities, so cutting cells on them is
cutting on the dependent variable, and within-cell variance will tend to zero
while the ratio tends to infinity.** This is the same shape as the circularity in
C11's criterion B (section 6.6.16), **and that one was only discovered after the
run.**

`MIN_CELL` takes 20 from section 6.4, and cells smaller than that are merged into
"other" with the count printed.

## 18.5 The full map from outcome to disposition, **written before the run, and changeable**

**Ruled 2026-08-17: the standing of this section has changed, and section 8
changes with it on this point.** The map is still written before the run,
**but it is a record of what I expected beforehand, not a promise**. Once
reality speaks it changes, and the change records what changed, why, and what
the original got wrong.

The reasoning: **how would you know what to map before running it?** A criterion
fixed at the moment of least information and then frozen makes "guessed right the
first time" the standard of correctness, and that is not how scientific
accumulation has ever worked. **What the record is worth is not that it
constrained anything; it is that it records the gap between expectation and
reality**, and that gap is itself information.

**Two entries were changed immediately after this ran, see section 6.6.26.**

| outcome | disposition |
|---|---|
| `√Z/√N > 3` on both `q` grids | B8-1's **necessary condition** holds. **It is not B8-1 holding**; B8-1 also needs section 3.3's two grids and section 6's windows |
| `√Z/√N` between 1 and 3 | **B8-1 fails and is recorded as failing.** No changing the floor, the cells or the statistic |
| `√Z/√N ≤ 1` | the signal is below the floor. **The stage's headline moved to B8-3 under section 15.7**, so this does not stop the stage, but B8-1 records a failure |
| `N`'s sample is `< MIN_CELL` (20) | **B8-0b is unmeasurable**, B8-1 does not run, and the reason is printed at the top of the result file |
| `N` differs by more than an order of magnitude between vintages | the pooled floor is unusable, **report per vintage only**, and register the difference as a reading that needs explaining |
| `M < N` | **within-cell dispersion below the zero calibration** means the cells are cut too finely or a contract quantity has leaked into the keys. **Go back and check the keys rather than accepting the number** |
| enumeration and `2·Var` disagree (relative error > 1e-12) | **a gate. The code is broken and nothing below is readable** (copied from B3-1) |

## 18.6 What this section does not rule on

| item | why |
|---|---|
| B8-1 itself | it needs both `q` grids; this section supplies only the floor |
| the per-class floor `√Z(a)/√N(a)` | section 15.4 needs it, it is gated by C9 in section 15.3, and only B8-4a uses it |
| what `M`'s reading means | it is a prerequisite for B8-4 and is not interpreted here |
| whether the deferral leg needs its own floor | **it does, and N4 already says "per vintage", which applies to legs equally**, but how the two legs' floors combine is B8-1's business |


## 18.7 After the measurement: the criterion moves from `√Z/√N` to a MAD ratio (2026-08-17)

**Section 18.1's `Z = 2·Var` was copied from B3, and B3's `x` is a bounded
basis-point deviation. On the clean-cure arm `ω` runs from a median of 8.9e-6 to
a maximum of 4.1e-1, five orders of magnitude. That shape does not carry over.**

The readings are in B8 inputs register section 6.6.26.5: the floor arm's `2·Var`
climbs monotonically from 5.3e-09 at n=100 to 1.5e-05 on the full sample,
**a factor of 2,900, still climbing at the last step**, with the p10 to p90 spread
stretching to 293x, while the MAD on the same arm is flat to three significant
figures from n=100 onward. **The signal arm converges on both.**

**The change:**

```
criterion = MAD(ω on the signal arm) / MAD(ω on the clean-cure arm)
```

The same estimator on both sides, which is what B3's shape actually requires; the
only change is the scale estimator. `√Z/√N` and the balance-matched variant are
kept alongside under R01, **and the convergence table is the reason for that
double report**.

**The threshold is not set here.** Section 5's `> 3` was written for `√Z/√N`, and
a MAD ratio is a different quantity, so its threshold either gets set separately
or this prediction is demoted to "report the number without a threshold".
**The measured 6,501 / 50,680 / 4,931 in 2019Q1 are nowhere near any plausible
boundary**, so it is not urgent and is registered as open.

**A reservation**: Theorem 3 is a variance decomposition and MAD is not a quantity
in that theorem. But a variance that does not converge cannot test a variance
decomposition either. **`Z` itself is well estimated and converges, and only the
floor fails to**, so what can be said is "the signal's centre is fifty thousand
times the floor's centre" and **what cannot be said is "the variance
decomposition holds"**.


## 18.8 Section 14.5's "must return zero" is wrong, and P4 has been asserting the right sentence all along

Section 14.5 says B8-0a(i) is "the clean-cure round trip ... **Must return zero
to floating-point tolerance**". **P4 in `b8_omega.py` simultaneously proves and
asserts that it does not return zero**, reading −9.04e-06 / −5.45e-05 /
−1.93e-04 at k = 1 / 3 / 6, and P4's own comment says "**The clean-cure round
trip does NOT return zero, and this is a property of the construction**".

The two sentences coexisted in one repository for a long time, **and the one read
while looking for a floor was section 14.5's**, so a deterministic quantity was
taken for noise. Measured (B8 inputs register section 6.6.27): `corr(ω, closed)`
is `+1.0000` in five vintages and `+0.9993` in one, with median absolute values
agreeing to four significant figures.

**The correction:**

```
B8-0a(i): the clean-cure round trip returns `loop_residual_ideal(B0, i, P, k)`,
          within the quantile rounding of field 12 (half a cent over the balance,
          about 3.0e-8). The gate's criterion is that error, not the loop sum.
B8-0b:    `N = MAD(ω − closed)`, measured at 2.68e-08 to 5.22e-08.
```

**B8-0a(i-a)'s existing readings are unaffected**: it was always comparing
`stream` against `closed` and has always measured this error
(`ratio_max = 0.400`). **Only section 14.5's prose was wrong.**

**A reservation**: the modification arm carries a deterministic discretisation
component of the same kind and it **has no closed form**. If it is the same order
as the clean-cure arm (1e-5) it is one ten-thousandth of the signal (1.4e-1) and
negligible; **that is inference and not measurement**, and it is registered as
open.

---

# 19. How to read B8-3: an institutional contrast, with the expectation written before the run

**Written 2026-08-17. `ω` and the floor were both on disk and B8-3 had read no
number.** Under the standing changed in section 18.5: **this is a record of what
I expected beforehand, not a promise**, to be changed once reality speaks, with
the change recording what was wrong.

## 19.1 What B8-3 asks for, and what it does **not**

Section 5: **two realisable paths to the same end state carry different
accumulated `ω`.**
Section 15.7: this is an **existence claim** of the Corollary-1 shape, settled by
one inequality on one edge.

**So B8-3 does not have to win causal identification.** It does not claim that
the servicer's choice of path caused the difference in `ω`; it claims that two
already-realised paths arriving at the same `current` carry different accumulated
`ω`. **That is a statement about the state space, not about choice.**

**Compositional differences still have to be reported**, because a reader will
ask and not reporting is pretending it does not exist. So this section has two
layers: **existence** (B8-3 itself) and **the difference after stratification**
(stronger, but not B8-3's bar).

## 19.2 The path pairs

**The main pair** (fixed by section 14.4):

```
delinquent → modified → current      against      delinquent → deferred → current
```

Both have loop sums under section 17's window, with six-vintage totals of 49,649
on the modification leg and 35,659 on the deferral leg.

**The secondary pair** (registered in section 5, not run here, recorded): one
90-day delinquency against two 30-day delinquencies; cure-then-redefault-then-
modify against modify-on-first-delinquency. **They are temporal contrasts, and
section 14.4 has already explained that a temporal contrast runs into the two
endpoints having different arrears histories.**

## 19.3 The statistic: a median difference, in units of the floor

`ω` is heavy-tailed on both legs (measured in section 6.6.26), **so neither the
mean nor the variance is used**.

```
Δ       := median(ω | modification leg) − median(ω | deferral leg)
Δ/floor := Δ / MAD(ω − closed)          the floor is in section 6.6.27, about 3e-08
```

**Dispersion uses MAD**, the same estimator as B8-0b, for the reason in section
18.7.

## 19.4 Stratification: what may be cut on, and what may **not**

| key | why it may enter |
|---|---|
| section 6's event windows | calendar, unrelated to path or contract |
| months missed `t_M − t_A` | a path |
| time to return `t_B − t_M` | a path |

**Barred: rate, term, payment, balloon, balance.** The first four are `ω`'s
arguments.
**The balance deserves its own sentence**: `ω` is homogeneous of degree zero in
`(balance, balloon)` (`V` is linear in both and `ω` is a log ratio), **so
stratifying on the balance would not mechanically drive the result**; it is
barred because it is a contract quantity while this section's stratification uses
only path and calendar. **That is a stricter line than necessary**, and the
reason is that the circularity in section 6.6.16 was only found after the run.

`MIN_CELL = 20`, with small cells merged into "other" and the count printed.

## 19.5 The reading: three things looked at together

1. **Existence**: `Δ` and `Δ/floor`, pooled and per vintage.
2. **The difference after stratification**: within-cell `Δ`, weighted by cell
   size, **and sign consistency**, meaning how many cells' `Δ` share a sign.
   **This is the key one**: if the difference comes from composition the sign
   flips between cells, and if it comes from the path the sign holds.
3. **A within-cell permutation null**: shuffle the leg labels inside each cell,
   recompute the weighted `Δ`, 999 times, and report where the observed value
   falls in the null distribution. **The shuffle is done within cells**, so what
   it tests is whether the leg label still carries information given the path and
   the window.

## 19.6 Two things already known to bite, written up front

**One, deferrals are almost entirely inside the COVID window.** Of 32,533
deferral triangles across the six vintages, 31,057 are in COVID (corrected in
section 14.4; 1,476 are outside it). **So in a cross-window stratification, most
non-COVID deferral cells will fail `MIN_CELL`.** That is not a failure, it is a
countable fact, **and the cell counts and drops have to be printed rather than
"the windows are not comparable" being written up as "there is no
difference"**. O30 records this.

**Two, the two legs have different measurability rates** (section 6.6.25:
modification leg 0.7286 to 0.9068, deferral leg 0.8386 to 0.9853).
**Measurability is itself correlated with the leg**, so this section prints each
leg's rate **and concedes that stratification cannot fix it**: an unmeasurable
loop has no `ω` and is in no cell at all.

## 19.7 Outcome to disposition: **the expectation before the run, changeable**

| outcome | disposition as it stands |
|---|---|
| `Δ/floor` far above 1 with consistent signs across cells | **B8-3's existence claim holds** and stratification has not overturned it |
| `Δ/floor` far above 1 with signs flipping across cells | **existence still holds** (it does not need to win composition), but it must be stated that the association between the difference and the path is unstable |
| `Δ` at the order of the floor | B8-3 fails and is recorded as failing |
| the observed value is not extreme in the permutation null | **the leg label carries no information within cells.** Existence is unaffected and layer 2's reading is void |
| every non-COVID cell fails `MIN_CELL` | **print it as it is**: the main pair is only readable stratified on COVID, and the other windows have pooled figures only |

## 19.8 What this section does not rule on

| item | why |
|---|---|
| B8-1 and B8-2 | different criteria, run separately |
| the secondary pair (temporal contrasts) | registered and not run |
| causation | **B8-3 makes no causal claim**, section 19.1 |
| whether the legs' differing measurability should be fixed | it cannot be fixed, only reported, section 19.6 |

---


# 20. How to read B8-2: the modification leg, five windows, stratified on term

**Written 2026-08-17. B8-3 had passed and B8-2 had read no number.**
Standing per section 18.5: **a record of the expectation before the run,
changeable.**

## 20.1 Only the modification leg runs, and the reason is structural rather than a choice

B8-3's section 5 measured the deferral leg at **zero in every term band** in
pre-crisis, HAMP and Flex (section 6.6.30.1). Payment deferral as a programme did
not exist before COVID, **so the cross-window version of a two-leg contrast does
not exist, and no number of additional acquisition quarters can produce one.**

**B8-2 therefore runs on the modification leg only, and this is not a
concession**: sections 5 and 6 say "the sign of the per-period loop sum is stable
across the four windows", **which was always a statement about one leg**.

## 20.2 The two `q` grids give the same loops here, and that is explained rather than passed off as a pass

Section 3.3's main grid cuts delinquency into `30 / 60 / 90+` and the secondary
grid keeps only `delinquent`.
**Section 17's window distinguishes only `current` from not-`current`** (`t_A` is
the last current and `t_B` the first return to current), **so the two grids give
loop-for-loop identical sets.**

**B8-6 is therefore automatically satisfied on B8-2, and that is a property of
the construction and not a test that was passed.** Written here so the result
file does not print it as a pass.

## 20.3 Stratification: the remaining term at `t_A`, and it is the main axis

Measured (section 6.6.30.2): within one window, the shortest term band and the
longest differ in median `ω` by a factor of 25 (HAMP) and 7.4 (COVID).
**The variation from term is larger than the variation between windows.**

Measured at `t_A`, before the event, a pre-treatment covariate. **Never at `t_M`
or `t_B`.** Term rather than age, because **what enters `ω` is the term**.

**A cell is readable when `n >= MIN_CELL` and more than one cohort contributes.**
The second half is load-bearing: inside a single-cohort cell, window and age are
perfectly collinear.

## 20.4 The criterion and its vacuity risk, written together

Section 6's discriminant (`b1_setup.md` section 7): **a structural wedge carries
the same sign in every window, while a one-off repricing appears in one window
only.**

```
B8-2 passes ⟺ in every readable (window × term band) cell,
              the median per-period loop sum has the same sign
              and the bootstrap interval does not cross zero
```

**And this criterion has a vacuity risk that has to be reported with it**:
section 14.3 says leg 1 is positive by construction (missed months make the
obligation heavier), so "the loop sum is always positive" could equally be
**"leg 1 dominates leg 2 everywhere"**, which is a fact about how servicers price
modifications and **not a structural wedge**.

**Disposition: print the medians of leg 1 and leg 2 side by side, cell by cell.**
Section 14.2 says the leg split is bookkeeping and not load-bearing, **and that
was said about conclusions; using it to diagnose whether the criterion itself is
vacuous is exactly what it is for.**
If leg 2's median is more than an order of magnitude below leg 1's in every cell,
**then this criterion is measuring arithmetic rather than a wedge, and it has to
be written up that way.**

## 20.4a Where leg 2's sign comes from (added after the run; section 8 has already ruled the map changeable)

**Section 14.3 expected leg 2 to be negative, and all 29 readable cells measured
positive.** Before reading that as "the modification made the obligation
heavier", **the part contributed by the construction has to be separated out**.
At `t_M`, `V = B·k(i, d, n)` with `k = LP(1, i, n)·A(d, n)`, so

```
r(t_M) = log(B_now / B_hat)   capitalised arrears
       + log(k_now / k_hat)   repricing
       + a remainder          the balloon; field 64 is identically zero in these six vintages
```

**This is an identity, not an approximation.** When `d = i`, `k` is exactly one
and the repricing term is exactly zero; when `d < i`, `k > 1` **and rises with
`n`**, so extending the term **mechanically** raises `V`. Over most of this
sample Treasury yields sit far below coupon rates, **so this channel is open and
has to be measured rather than assumed small**.

The repricing term is then split one contract item at a time:

```
rate  = log k(i_now,  d, n_hat) - log k(i_prev, d, n_hat)
term  = log k(i_prev, d, n_now) - log k(i_prev, d, n_hat)
cross = repricing - rate - term       the interaction, printed, never apportioned
```

**Outcome to disposition**:

| outcome | disposition |
|---|---|
| `term` carries `repricing` and `repricing` carries leg 2 | leg 2 being positive is the construction discounting a lengthened stream at a rate below the coupon, **not the modification making the household worse off**. B8-2's sign still holds, but **this sentence has to travel with every citation** |
| `balance` carries leg 2 | leg 2 is capitalised arrears, and section 14.3 merely guessed the wrong dominant term. **That expectation in section 14.3 is void and is deleted** |
| neither dominates, or they trade places cell by cell | claim neither reading and print the decomposition table |

**This section does not rule on** whether the term effect is mechanical or
compositional (section 6.6.30.2 already ruled that this data cannot separate
them).

## 20.5 Confidence: bootstrap, not permutation

A window is a calendar and shuffling it constitutes no meaningful null.
**Use the bootstrap**: resample within the cell with replacement 999 times and
report the 5th to 95th percentile of the median.
**"The sign holds" means that interval does not cross zero.**

## 20.6 Outcome to disposition: the expectation before the run, changeable

| outcome | disposition as it stands |
|---|---|
| every readable cell same sign with intervals clear of zero | **B8-2 holds**, in the version that balances term |
| same sign but some cells' intervals cross zero | it holds, but print which cells do not stand up, **and they may not be counted as "consistent"** |
| a whole window reverses sign | **B8-2 fails and is recorded as failing**, read under section 6's discriminant as a one-off repricing |
| leg 2's median is more than an order of magnitude below leg 1's everywhere | **the criterion is vacuous.** B8-2 is recorded as "what was measured is leg 1's arithmetic", not as a pass |
| fewer than two windows are readable | there is no cross-window comparison; print it as it is |

## 20.7 What this section does not rule on

| item | why |
|---|---|
| whether the term effect is mechanical or compositional | section 6.6.30.2: this data cannot separate them, so no claim |
| B8-1 | a different criterion, run separately |
| the deferral leg across windows | **it does not exist**, section 20.1 |
| downloading more vintages | ruled in section 6.6.30.1: no |

---

# 21. How to read B8-1 (written 2026-08-17, before the run)

Carrier `experiments/b8_1_signal.py`, result file `results/b8_1_signal.md`.

## 21.1 What section 5's registered sentence leaves after B8-0b

Section 5 registered `√Z/√N > 3` on both `q` grids. Two things have since moved
it.

**One, the estimator changed** (section 18.7). The floor arm's `2·Var` climbs by
a factor of 2,900 from n=100 to the full sample and is still climbing at the last
step, so both sides moved to MAD. **The `> 3` was written for a ratio of standard
deviations, and changing the scale estimator does not let it carry over by
declaration.**

**Two, and this is the important one: the floor is not noise at all.**
`corr(ω, closed)` is `+1.0000` in five vintages, and a clean cure's loop sum
**is** `loop_residual_ideal`, a deterministic function of four scalars.
Subtracting it leaves 2.68e-08 to 5.22e-08, which is half a cent over the median
balance: **the quantile rounding of field 12**.

## 21.2 The threshold: the ruling

`N` is instrument resolution, not sampling noise. "Three sigma above the noise"
is not a well-formed question where there is no sampling distribution. So:

```
operating line = 1.0        readability, not significance
```

**Below 1, the loop sum falls inside one quantisation step of field 12 and cannot
be read. Above 1, it can.** Section 5's `3` is printed alongside under R01,
labelled **inherited and not operative**.

**This is not worth a round of running to settle.** The measured 6,501 / 50,680 /
4,931 in 2019Q1 give the same conclusion at `>1`, `>3`, `>10` and `>100`.
**The threshold is not B8-1's blocker, and treating it as one is mistaking form
for content.**

## 21.3 The genuinely open item: how much of the signal is construction

Since the floor is a deterministic construction residual, **the modification arm
carries the same residual**, and a ratio of dispersions cannot see that. O32
records it as inference: same order, therefore one ten-thousandth, therefore
negligible. **That is inference and not measurement.**

It can be measured exactly, over the stretch where the contract has not yet
moved. **Nothing before `t_M` knows a modification is coming**, so the
modification arm's leg 1 and a clean-cure loop with its cure month removed are
the same object, with the same closed form:

```
l1_closed = n1 · ( log B_A − log( B_A·(1 + i/1200) − P ) )
```

This has already been pinned against `loop_residual_ideal` itself (`k` flat
delinquent months plus one cure month, and subtracting the former must leave
exactly the latter, verified on four sets of numbers), and measured on a fixture
where leg 1 equals it loan by loan.

## 21.4 Outcome to disposition (fixed before the run, changeable)

| outcome | disposition |
|---|---|
| leg 1 equals the closed form loan by loan, and the ratio stays far above 1 after removing it | **B8-1's necessary condition holds, and the part that holds is exactly the stretch where the contract really moved.** This is the strongest reading |
| leg 1 equals the closed form, but the ratio collapses toward 1 after removing it | **what B8-1 was measuring was the construction.** It fails and is recorded as failing, and the headline stays with B8-3 per section 15.7 |
| leg 1 does not equal the closed form | the flat-delinquency assumption does not hold on the real vintages (fees, escrow, partial payments). **Explain that before discussing the ratio**, and register it as a reading awaiting explanation |
| the net ratio differs by more than an order of magnitude between vintages | pooling is unusable, report per vintage only |

**The necessary condition holding is not B8-1 holding.** B8-1 also needs section
3.3's two grids (settled by construction in section 20.2) and section 6's windows
(that is B8-2, with its own result file).

## 21.5 What this section does not rule on

| item | why |
|---|---|
| whether legs 2 and 3 contain a deterministic component of the same kind | **there is no closed form**; the contract moves inside them. This section subtracts only the part that has one |
| the per-class floor | section 15.4 needs it, C9 in section 15.3 gates it, and only B8-4 uses it |
| a threshold for the deferral leg | section 5's B8-1 names the modification triangle. The deferral leg is printed alongside and does not enter the criterion |
| Theorem 3's variance decomposition | MAD is not a quantity in that theorem; section 18.7's reservation stands |

## 21.6 Measured: leg 1 differs from the closed form by **a number of months**, not by a proportion (2026-08-17)

Row three of section 21.4 fired. Only 0.4 to 12 percent are equal loan by loan,
and the median `closed/leg1` runs 1.2289 to 1.5668. The column
`eff = n1·leg1/closed` separates the three diagnoses:

| vintage | median `n1` | median `eff` | `n1 − eff` | `eff/n1` |
|---|---|---|---|---|
| 2002Q1 | 11 | 6.196 | **4.80** | 0.563 |
| 2006Q1 | 12 | 7.025 | **4.97** | 0.585 |
| 2007Q1 | 12 | 7.032 | **4.97** | 0.586 |
| 2012Q1 | 11 | 6.065 | **4.93** | 0.551 |
| 2017Q1 | 14 | 9.005 | **4.99** | 0.643 |
| 2019Q1 | 16 | 12.017 | **3.98** | 0.751 |

**The difference is an approximately constant integer number of months (about 5
in five vintages and about 4 in one), not a proportion.** `n1` goes from 11 to 16
while the difference does not move, and `eff/n1` goes from 0.55 to 0.75.
**A smooth balance drift during delinquency would give a proportion, not an
offset**, so that explanation is excluded.

The diagnosis is therefore: **about five months inside each leg 1 window do not
behave like missed months**, contributing near zero instead of `per_month`. The
most natural candidate is **that payments land in those months**: a loan that is
chronically one period behind never reads `current` in field 40 while paying
every month, so the balance amortises on schedule and `r(t) ≈ 0`. Section 17's
window is defined by `current`, **not by whether a payment arrived**, and the two
are not the same thing.

**This does not endanger B8-1.** The closed form being subtracted is 1.2 to 1.6
times the measured leg 1, so more is being removed than the construction residual
itself, and the net ratio moves only by −11.5 to +2.2 percent.
**A subtraction fifty percent larger than its target failed to move it, so the
construction residual cannot be carrying this result.**

**Nor does it endanger B8-2.** Section 20.4's vacuity criterion is
`|leg2|/|leg1|`, and if leg 1 is understated the true ratio only moves further
from vacuous, which is the favourable direction for B8-2.

**Registered as a reading awaiting explanation, with the discriminant already
written and one run enough to close it**: inside each leg 1 window, count the
months with `B(t) ≈ B(t−1)` (flat, no payment) and with `B(t) ≈ f(B(t−1))` (paid
on schedule). **If the flat count equals `eff`, this closes.** Both `pay_row` and
`quiet_pairs` are already in the pipeline and no new retrieval is needed. **Not
run this round**, because it changes no registered verdict.

---


# 22. How to read B8-5 (written 2026-08-17, before the run)

Carrier (to be written) `experiments/b8_5_hole.py`, result file
`results/b8_5_hole.md`.
**B8-5 uses no `ω`, no curve and no floor.** It is a count, and its object is
reachability, `b1_setup.md`'s `H⁰` and `H¹`, not curl.

## 22.1 First, what this data can and cannot give

Section 5 says "the share of borrowers for whom `delinquent → modified`
**never exists**, differing by class".
**"A share" and "never exists" are not the same object.** In a class with a 5
percent modification rate the edge exists and is merely rare. What the data gives
is a rate; what `H⁰` and `H¹` need is the existence of an edge.

**So B8-5's honest label at this station is "an admission threshold that differs
by class"**, and the `H⁰`/`H¹` reading needs an additional argument this station
does not make. Section 15.6's branch table already says this ("the reading
contracts to an admission threshold rather than path dependence"), and this moves
it forward into the criterion itself.

**And it is association, not causation**, alongside B8-4 (section 9):
modification is endogenous.
**The bottom of the class range is truncated by construction** (GSE-conforming
loans exclude subprime, jumbo, FHA and VA), and the truncation runs toward the
null, so **dispersion is harder to find and not easier**. That sentence travels
with every citation.

## 22.2 The denominator: who enters the pool

Entry requires having been delinquent, by field 40. **The two `q` grids give two
different pools here** rather than collapsing to one as in B8-2 (section 20.2),
**so B8-6 is a real test on B8-5**:

| grid | entry |
|---|---|
| coarse (`current` / not `current`) | field 40 ≥ 1, ever a period behind |
| fine (the delinquency field's own partition, section 3.3's main grid) | by band, each band entering separately |

**Both run and both are printed.** If they give opposite class orderings, B8-6
fails on B8-5 and is recorded as failing.

## 22.3 The numerator, and competing exits: "not modified" is not one thing

**The numerator is a modification**: field 42 or field 63, on the same definition
as section 17's modification onset.
**A deferral (field 108) is a different node per C10-4, counted separately and
never merged in.**

"Never modified" merges completely different outcomes into one sentence, so
**each exit is printed as its own column**, with the termination reason from
field 44 and termination itself taken as the balance going to zero per section
16.6:

```
modified | deferred | cured and never delinquent again | paid off | liquidated (foreclosure, short sale, deed in lieu) | still unresolved at the end of observation
```

**A foreclosure is not a hole, it is a different endpoint.** A borrower reaching
liquidation has left the delinquent node; he simply left by an edge other than
modification. **Counting it as a hole reads two opposite things as one.**

## 22.4 Censoring: this is the only thing that can manufacture a result

**A loan that first goes delinquent in the last month has had no time to be
modified.** If a class's delinquencies cluster at the end of the file, it will
appear to have a hole when it merely has no follow-up. **This is the only
mechanism in this section that can produce a false conclusion.**

Disposition: **do not fix a follow-up window; print the share as a function of
the follow-up period `H`**, with `H ∈ {6, 12, 18, 24, 36}` months, entry
requiring at least `H` further months of observation after the delinquency onset,
and the excluded counts printed cell by cell.

**The criterion hangs on the class ordering and not on the level**: if the
ordering is unstable in `H`, the conclusion is censoring rather than a hole and
is recorded as such. **A difference that holds at only one `H` does not count.**

## 22.4a One change to the criterion: stability is judged at the two ends, not over the whole ordering (2026-08-17, after the run)

Section 22.4 said "the class ordering is stable in `H`", and it was implemented as
**the entire ordering being identical across all five values of `H`**.
**That is the wrong test, and the first real run exposed it.**

| levels | stable / total | share | permutations at that level count |
|---|---|---|---|
| 2 | 78 / 152 | 51.3% | 2 |
| 3 | 29 / 119 | 24.4% | 6 |
| 5 | 4 / 90 | 4.4% | 120 |
| 9 | 0 / 80 | **0%** | 362,880 |
| 15 | 0 / 53 | **0%** | 1.31e12 |

**The pass rate collapses monotonically to zero with level count, and above seven
levels not one of 155 cells passes.** Two mechanisms push the same way: `k`
levels have `k!` orderings and five readings must land on the same one, which is
combinatorial; and more levels means thinner levels and noisier rates, which is
statistical. **Neither is censoring, and section 22.4 was written to catch
censoring.**

**Changed to**: `range` is `max − min`, so what actually has to be stable is
**that the level taking the highest rate and the level taking the lowest are the
same levels at every `H`**. A single swap in the middle of the ordering moves not
one digit of the reported number, while the old criterion recorded it as
unstable. Both ends matter: a swap at the bottom means "which class has the
lowest admission" changed hands, and that is half the claim.

**The old readings (whole-ordering identity) are kept alongside under R01**,
since they are numbers already published.
**And the minimum level observation count entering each comparison is printed
cell by cell**, so a reader can see the statistical mechanism directly rather
than take this ruling on trust.

**What the original sentence got wrong, stated plainly**: it mistook "the
criterion gets harder with more levels" for "the data is unstable". A criterion
whose pass rate moves with the coarseness of the stratification is measuring the
coarseness.

## 22.5 Class grids, windows and the floor

The grids are the five that clear C9 and hang on the borrower per section 2.4:
`purpose` / `fthb` / `fico_llpa_coarse5` / `dti_complement15` / `fico_llpa9`.
**C9 is not the binding gate here**: it counts observations per cell among loans
that completed a triangle, while B8-5's pool is all delinquent loans and is far
larger. **A separate floor `MIN_CELL = 20` applies, computed on the
denominator.**

**Read per window, never pooled.** Section 6's five windows are entirely
different modification regimes, and reading HAMP, Flex and COVID together is
meaningless.

## 22.6 What "differs by class" counts as

The statistic is the **range** of modification rates across classes within a cell
(window × grid).
The null is **a within-cell permutation of the class labels** (B8-3 already uses
the same shape): a class is a label attached to a loan and shuffling it is a
meaningful null, whereas shuffling the window is not (that is a calendar). 999
draws, report `p`.

## 22.7 Outcome to disposition (fixed before the run, changeable)

| outcome | disposition |
|---|---|
| the ordering is stable across all `H`, permutation `p < 0.05`, and both `q` grids agree | **B8-5 holds**, labelled "an admission threshold that differs by class" and not "the edge does not exist" |
| the ordering is stable but only one `q` grid is significant | **grid dependence, recorded as such**, and B8-6 fails on B8-5 |
| the ordering reverses with `H` | **censoring, not a hole.** B8-5 fails and is recorded as failing, with the reason printed at the top of the result file |
| the range is significant but the class ordering of liquidation rates matches that of modification rates | **two edges move together**, read as "the outcome distribution differs by class" rather than "the modification edge is blocked", which is a weaker claim |
| a grid's cells do not reach the floor | that grid does not run, it is printed, and the floor is not lowered |

## 22.8 What this section does not rule on

| item | why |
|---|---|
| the formal `H⁰`/`H¹` reading | it needs "the edge does not exist" and the data gives a rate. Section 22.1 |
| causation | modification is endogenous; like B8-4 this is association (section 9) |
| why servicers behave this way | this station has no servicer-side variable at all |
| B8-4 | it needs the per-class floor and runs separately |

## 22.9 Measured results (2026-08-17)

554 cells, **132 endpoint-stable, of which 20 have `p < 0.05`**. Under the old
definition (whole-ordering identity) the figures are 115 and 10, kept alongside.
**The verdict, per section 22.7, is "read cell by cell, never pooled".**

### What carries it is FICO, and the direction is one-sided

Of the twenty significant cells, **the two FICO grids hold 12, and the direction
is consistent 12 out of 12**:

| | at the bottom of the admission ordering | at the top |
|---|---|---|
| count | `>=760` 9, `760-779` 2, `>=780` 1 | `<=639` 11, `640-679` 1 |

**The lower the score, conditional on already being delinquent, the higher the
share modified.** Across six vintages, three windows (pre-crisis, HAMP, COVID),
five entry bands and two FICO grids, there is not one counterexample. The
within-cell range runs from 0.35 to 32 percentage points.

**[Correction after review, 2026-08-17; this sentence must travel with the
"12/12"]** Of those twelve cells, **only four sit on the entry bands section 3.3
registers (`d>=1/2/3`)**; the other eight sit on `d>=4` and `d>=6`, which are
obtained by splitting section 3.3's merged `90+` bucket and **are not the
registered grid** (section 22.2's description has been corrected). The four
registered cells are 2002Q1's `d>=1/2/3` and 2012Q1's `d>=3`, still consistent 4
out of 4 (with `>=760` at the bottom every time), **but they fall on only two
vintages, and 2002Q1's three are nested bands and therefore not independent**. So
on the registered grid this direction rests on **two vintages**, not twelve cells.
**Cite four cells on two vintages, not twelve cells.** The readings on the extra
bands are kept alongside and labelled as extra.

**A sentence that must travel with this number**: it is a share **conditional on
already being delinquent**, and entering delinquency at all differs by class.
High-score borrowers who go delinquent are more likely to climb out on their own
(self-cure is 60 to 90 percent in every cell) and low-score borrowers who go
delinquent are more likely to need a modification. **So what this measures is a
direction and not a mechanism**; section 9 already labels B8-5 as association,
and this only writes out the association's shape.
**It may not be read as "the system favours the weak", nor as its opposite.**

### `purpose`'s six cells are all in HAMP, and the direction is consistent too

Code `P` at the bottom and code `C` at the top, on the 2006Q1 and 2007Q1 crisis
vintages, with ranges of 1.6 to 8.3 percentage points.
**What those two codes are has only a layout document behind it, which does not
count as identification under C0b**, and they are handled like `purpose`'s `U` in
`b8_c9_cells`: print the code, claim no meaning.

### The remaining two are at noise scale

One `fthb` cell with a range of 0.2 to 2.4 percentage points, and one
`dti_complement15` cell whose smallest level has 29 loans.
**Visible statistically and nothing substantively**, and the range has to be
quoted with them.

### One R01

Switching to the closed-form null took the significant cells from 21 to 20. What
dropped out was 2019Q1 `fthb` in COVID, previously at `p = 0.046`. **Both nulls
are 4,000-draw Monte Carlo, and a cell at `p ≈ 0.05` changing sides under
re-estimation is what `p ≈ 0.05` means.** Both readings are kept.

### This section did not become section 5's sentence

Section 5 asks whether the edge **never exists**. What was measured is a rate,
and the class with the lowest rate is **high-score borrowers**, which is not a
hole anyone would have pre-registered. **Per section 22.1 the label is an
admission threshold that differs by class, not `H⁰`/`H¹`.** Section 15.6's branch
table reads this entry down the "admission threshold" branch.

---


# 23. How to read B8-4a (written 2026-08-17, before the run)

Carrier (to be written) `experiments/b8_4_class.py`, result file
`results/b8_4_class.md`.
**B8-4b has already been ruled not to run by C9 in section 16.12** (all eleven
grids have a minimum of 0 or 1), section 15.6's second domain points to corporate
credit, and section 15.3 states that this is not a failure of B8. **It may not be
reopened.**

## 23.1 What is being measured, and the ceiling N2 has already fixed

Section 15.5's entry: **whether the class ordering by per-class median loop sum
is stable across section 6's windows.** The statistic is the mean Spearman
correlation between window pairs, and the null shuffles class labels **within a
window**.

**N2, written into the prediction rather than discovered afterwards**: this
criterion **cannot** claim that any particular class carries idiosyncratic
variation distinguishable from that class's own sampling noise. All it can claim
is that **the class indicator carries structure that reproduces across windows**.

**Association, not causation** (section 9); modification is endogenous.
**The bottom of the class range is truncated by construction** (GSE-conforming
excludes subprime, jumbo, FHA and VA), and the truncation runs toward the null,
so **dispersion is harder to find**. That sentence travels with every citation.

## 23.2 Retrieval: the loop cache, plus the floor as it is understood after B8-1

Loop sums come from `b8_cache` and **are not rebuilt from the core table**. Class
labels come from `b8_c9_cells.build_grids`, which is at the `n_loans` scale, so
there is no full-table scan to pay for.

**A per-class floor is required by section 15.4**: a pooled `N` would make thin
classes look dispersed, which is exactly what killed B7. But the floor's
definition changed twice after B8-0b and B8-1, so it is written out once here:

```
N(a) = MAD( ω − closed )   on the clean-cure arm of class a
```

**Both corrections have to travel with it**: first, the estimator is MAD and not
`2·Var` (section 18.7; the floor arm's variance does not converge); second,
`closed` has to be subtracted, because a clean cure's loop sum **is**
`loop_residual_ideal`, a deterministic function and not noise (section 21.1), and
what remains after subtracting it is the quantile rounding of field 12.

**Here the floor is a gate and not the criterion**: if a class's median falls
inside its own floor, that class **does not enter the ordering** and is printed.
The criterion is the stability of the ordering.

## 23.3 The statistic, and the direct consequence of pit 47

**Pit 47 says: if a criterion's pass rate moves with the coarseness of the
stratification, what it measures is the coarseness.** Spearman has exactly this
problem, and harder:

| grid | levels | what Spearman is at that level count |
|---|---|---|
| `fthb` | 2 | **can only take ±1**. Two things have no ordering |
| `purpose` | 3 | six possible values |
| `fico_llpa_coarse5` | 5 | enough |
| `fico_llpa9` | 9 | enough |
| `dti_complement15` | 15 | enough |

**Ruling: run only at `k >= 3`, so `fthb` does not enter B8-4a, with the reason
printed at the top of the result file.** The null permutes at the same `k`, so
the scale problem is absorbed by the null; **a statistic that cannot take three
values is not something a null can rescue.**

**Only classes present on both sides of a window pair enter that pair**, with
classes appearing on only one side removed pair by pair and counted: ordering on
a set that changes is not an ordering (the same rule as section 22.4).
Section 5's text says "four windows" and section 6 now has five, so **run every
window that clears the floor and print how many entered, cell by cell**.

## 23.4 Section 13.4's vintage condition is not optional

Section 13.4 already ruled: the 2002-2007 vintages have original rates of six to
seven percent and a rate cut is the lever; the 2012-2019 vintages have three to
four and a half and only an extension is left. **The value of a modification
decomposes differently by vintage, so class dispersion has to be estimated inside
a vintage's rate environment, or the vintage effect will appear wearing the class
effect's clothes.**

In practice: **compute the ordering and the correlation per vintage and print
them side by side**, with the pooled figure on its own row and labelled as
pooled. **The difference between vintages is itself a reading** and not something
to be averaged away.

## 23.5 Equal `n` and loadings, neither optional (section 15.5's own text)

- **Equal `n`**: down-sample every class to the `n` of the sparsest class in that
  cell, recompute, print both numbers.
  **An effect that appears only at unequal `n` is a thinness artefact and is
  registered as one.**
- **Print the loadings**: which classes carry the ordering, alongside the
  magnitude. `b7_interaction_rank.md` spent a day and a half reading a rank
  before anyone printed the eigenvectors.

## 23.6 The null

**Shuffle class labels within a window, drawing on the same design** (section
15.5's own text). Both lessons from B8-5 apply: first, the null has to run on the
same set of loans as the observed statistic, and loans in levels below the floor
or otherwise excluded may not be washed into the surviving levels; second, use a
closed form rather than simulation where one exists, **but the closed form has to
be verified against the slow path** before it may be used.

## 23.7 Outcome to disposition (fixed before the run, changeable)

| outcome | disposition |
|---|---|
| mean Spearman significantly positive, still present at equal `n`, and most vintages in the same direction | **B8-4a holds**: the class indicator carries structure that reproduces across windows. **Still association** (section 9), and N2's ceiling stands |
| significantly positive, but it disappears at equal `n` | **a thinness artefact; it fails and is recorded as failing.** This is precisely why section 15.5 imposed that requirement |
| significantly positive, but carried by one vintage alone | **a vintage effect wearing the class effect's clothes** (section 13.4). It fails, and which vintage is printed |
| mean Spearman not significant | B8-4a fails and is recorded as failing. **The headline is with B8-3 per section 15.7 and the stage does not stop over this** |
| a grid fails `k >= 3` or fails the floor | that grid does not run and is printed; **neither the floor nor `k` is lowered** |

## 23.8 What this section does not rule on

| item | why |
|---|---|
| whether a particular class has its own idiosyncratic variation | **N2: not separable on this design**, and it is written into the prediction |
| B8-4b | C9 in section 16.12 already ruled it does not run |
| causation | modification is endogenous, section 9 |
| why servicers order things this way | this station has no servicer-side variable |
| whether these band edges are the right ones | ruled in section 16.13: FICO and LTV take the issuer's pricing partition, DTI takes HMDA, and that asymmetry travels with every citation |

## 23.9 Measured results (2026-08-17)

22 readable cells, 5 significantly positive, of which **4 survive equal `n`**,
spread over three vintages. But the verdict per section 23.7 hangs on **sign
consistency across vintages**, and only one grid clears that column:

| grid | vintages | positive | negative | zero | sign test `p` |
|---|---|---|---|---|---|
| `fico_llpa9` | 6 | **6** | 0 | 0 | **0.0312** |
| `fico_llpa_coarse5` | 6 | 4 | 1 | 1 | 0.3750 |
| `purpose` | 6 | 4 | 1 | 1 | 0.3750 |
| `dti_complement15` | 4 | 3 | 1 | 0 | 0.6250 |

**B8-4a holds on `fico_llpa9`**: rho by vintage is +0.05 / +0.09 / +0.76 / +0.37
/ +0.84 / +0.50, six vintages in the same direction, with 2007Q1, 2012Q1 and
2017Q1 each reaching `p < 0.05` on their own and all three surviving equal `n`.
**N2's ceiling stands**: the claim is that the class indicator carries structure
reproducing across windows, **never that any particular class has variation of
its own**. Association, not causation, and the truncated bottom of the class
range runs toward the null.

### Loadings: the ordering is monotone in FICO (**a post-hoc reading, labelled as one**)

Section 23's design asks whether the ordering reproduces across windows. **It does
not ask whether the ordering is monotone in the score.** What follows was read off
the loading table after the ordering was established, **and is post-hoc and
registered as post-hoc**:

| vintage | Spearman (FICO band order vs mean rank) |
|---|---|
| 2002Q1 | −0.6833 |
| 2006Q1 | −0.7667 |
| 2007Q1 | −0.9167 |
| 2012Q1 | −0.7667 |
| 2017Q1 | −0.9456 |
| 2019Q1 | −0.8787 |

**All six vintages negative, median −0.82, sign test `p` = 0.0312.
The lower the score, the larger the loop sum.** In 2017Q1 the ordering is
perfectly monotone across all nine bands with no transposition at all.

### Read together with B8-5

B8-5 measured: **the lower the score, conditional on already being delinquent,
the higher the share modified** (12 of 12 in the same direction).
B8-4a measured: **the lower the score, the larger the loop sum the modification
carries** (6 of 6 in the same direction).
**The same class indicator, the same direction, and two different objects**, one
reachability and one a loop sum.
**Both are association**, both are subject to the same entry selection (the
composition of the delinquent population differs by class), **so read together
they remain association**, and agreeing with one another does not promote them to
a mechanism.

### The third appearance of one structural fact

`fico_llpa9` (nine levels) carries the verdict and `fico_llpa_coarse5` (five
levels, the same variable) does not. Section 16.14 already recorded one of the
same shape: `dti_complement15` (fifteen levels) clears C9 while `dti_coarse6`
(six levels) does not, **more levels survive and fewer levels die**.
Section 3.3 was the first, on B7's rank statistic; C9's pure count was the
second; **this is the third, on a third kind of statistic**. Coarsening is not
conservative. It grinds the structure away along with everything else.
