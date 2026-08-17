# B8: the slice summand on a household carrier, from loan modification

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
conflict.** Source: `b8_inputs_availability.md`'s run record, on 170,013,011 rows
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
`b8_inputs_availability.md`:

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
flips** (`b8_inputs_availability.md` §6.6.23.1). The same applies to the payment:
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
(§17.8's count, `b8_inputs_availability.md` §6.6.6) returns **38** loops across all
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
   `b8_inputs_availability.md`, not to a results file only.
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

# 16. B8-0a(i) 拆闸（2026-08-16）

**§1 到 §15 不变，本节在冲突处覆盖它们。** 陛下裁，全文与量化在
`claude-docs/B8_0a闸容差裁定_v1.md`，实跑记录在 `b8_inputs_availability.md`
§6.2.6 到 §6.2.8。**写于 `omega` 编码之前，B8-0a(i) 从未跑过。**

## 16.1 §14.5 的隐含假设，以及否掉它的数

§14.5 把 B8-0a(i) 定为「清洁自愈往返，只用合同三元组，**精确回零到浮点容差**」，
理由是那个零是算术的：欠缴月份的正残差与复原月份的负残差相消。

**相消要成立，得有一个 §14.5 没写出来的前提：余额路径精确回到计划表。**
1.4 亿个安静履约月份上量出来的是：

- 约四分之一的安静履约月份**不落在计划表上**（C8-1c(b)）。
- 其中约一半是**余额一个月纹丝不动**，六档合计占全部安静月份的 **4.881%**（C8-1e）。
- 冻结之后 lag 1 补回只有 26%–28%，六个月内 52%–59%，**约四成永不恢复**（C8-1f）。
- **一次未恢复的冻结对 `r` 的贡献等于欠缴一个月的 ω₁**（参照贷款上都是 1.336e-3）。
- 带冻结的段落后计划表的 p10 是 −2.6% 到 −9.9%，**无冻结的段是 −0.0000**。

## 16.2 拆法

| id | 跑在什么上 | 判据 | 地位 |
|---|---|---|---|
| **B8-0a(i-a)** | 清洁自愈贷款中**每一个安静月份都落在其段众数簇内**的那些 | **精确回零到浮点容差** | **闸。** 不过则构造坏了，后面一律不能读 |
| **B8-0a(i-b)** | **全部**清洁自愈环 | 环和分布，对着从未违约贷款在同长度窗口上的噪声底 | **读数，不是闸** |

**§8 第一条证伪线改挂到 B8-0a(i-a)。** §14.5 的 B8-0a(ii)（带费用与资本化）不变，
但按 §6.2.1 它已经收窄：字段 64 在六档上零笔为正，**减免那一项在本样本上恒为零**。

## 16.3 (i-a) 的样本与两条必带的限定

**19,090 笔**，即清洁自愈形状 154,768 笔的 **12.35%**，
逐档 138 / 238 / 256 / 2,652 / 7,862 / 7,944。

1. **样本严重偏向新档。** 2002Q1 只留 2.40%，2019Q1 留 19.94%。
   **闸主要在 2017 与 2019 的 cohort 上被认证。**
2. **该子样本按支付规则性选出**，而支付规则性与 §5 的类指标（信用分、DTI）合理相关，
   **故它不是类分布上的随机样本，不得复用为任何 B8-4 形状读数的样本。**

## 16.4 一条加进 §9 的结构性限制

> 一次落在环内且未恢复的余额冻结，往 `omega` 里注入的东西与一个真实欠缴月份
> **不可区分且大小相同**，因为两者在 `V` 上是同一件事，唯一区别是字段 40 读 `00`。
> **这给 B8-1 的噪声底定了一个不由样本量决定的下界，引用 B8-1 的地方必须带这一句。**

## 16.5 §14.10 的两处更正

**字段 44 不必进过滤器。** 早先登记的「quiet 过滤器漏查零余额码、结清月份在样本里」
那条担心**已撤回**：字段 44 在六档、约四千万个安静月份上一个都没设（`b8_inputs_availability.md`
§6.2.6.3）。

> **【2026-08-16 二次更正】上面这条撤回本身是错的，见 §16.6。**
> 字段 44 那半仍然对，但**终止由余额归零标记，不由零余额码标记**，
> 而 quiet 过滤器当时确实漏查了余额归零。**过滤器已加 `upb[当前行] > 0`。**

**月供作为逐段 carry 的状态量**，这条已由 §6.2.5 定死，`V` 与 `V̂` 都用它。

## 16.6 §16.5 那条撤回本身是错的，quiet 过滤器已加一条（2026-08-16）

§16.5 写「字段 44 不必进过滤器，结清月份在样本里那条担心已撤回」。
**那条撤回是错的。字段 44 那半仍然对（它在约四千万个安静月份上确实一个都没设），
但终止由余额归零标记，不由零余额码标记，而 quiet 过滤器当时确实漏查了余额归零。**

起因是量出了 Fannie 的一条报送惯例：**每一笔贷款的第一行 UPB 都是零**，
六档 1.0000 一笔不漏，每笔平均 6.70 到 6.94 行，终止之后也不报
（`b8_inputs_availability.md` §6.2.9）。于是「正 → 零」这一对能通过旧过滤器，
`obs` 等于整个余额。

**更正**：`quiet_pairs` 现同时要求 `upb[当前行] > 0`。旧口径由
`require_cur_positive=False` 保留可逐位复现，`selftest` 同时验两套并要求它们真的不同。
全文与影响范围在 `b8_inputs_availability.md` §6.2.10 与
`claude-docs/B8_0a闸结果与报送惯例_v1.md` §3。

**【2026-08-16 同日更正】此处原写「污染落在高于众数那一侧」。实测推翻：
这条更正在六档上删掉零个对**（`b8_inputs_availability.md` §6.2.10.2，
`results/b8_quiet_delta.md`）。§6.2.6 那 8.8% 与中位数确实不受影响，
**但理由是根本没有污染，不是污染在另一侧**。

**这条更正因此是防呆不是修复。** 判据不变，变的是它在真机上不承重：
结清那一行的**剩余法定期限是空的**（六档漏网 5 / 2 / 5 / 1 / 0 / 0），
票面利率也空（各漏几百个），两条已经把结清对全挡在外面。
**这把 §16.6 开头那条报送惯例推广了：终止行报一个余额零，然后把合同状态整体停报。**

## 16.7 B8-0a(i-a) 六档全过，但过它的是计数不是比值

**§10 第 3 步到此结清。** 六档 `over 1` 全零，合格率 0.5195 到 0.6597。
表在 `b8_inputs_availability.md` §6.2.11.1，结果在 `results/b8_0a_gate.md`。

**必须跟着判定一起写的一句**：`max ratio` 六档全部落在 0.399–0.400，
那是结构性上限 `(1 + (1+i)^(k+1)) / ((2+i)(k+1) + (1+i)^(k+1))`，
因为路径容差与符合度的界共用同一个 `1/B`。
**符合度那一半在数学上被路径那一半蕴含，不携带独立信息；闸的全部判别力在合格计数上。**

判别力是实的：月供估错 1% 会把终点移动 $30.55，对着 $0.0101 的容差，三千倍，
合格计数会塌到接近零。

**§16.3 那两条限定之外，凡引用 (i-a) 处再加这一条。**

## 16.8 (i-b) 有数：环带着 172 到 2,343 倍于噪声底的残差

`b8_inputs_availability.md` §6.2.11.4。闭式已被减掉，剩下的是观测路径对理想路径的偏离，
主要来自复原那一个月的费用、部分复原与托管。**§14.5 拆 0a 时说要保住的那个信号，
现在有数了。**

## 16.9 §7 的过滤器：三条挣不回来，一条用行为代理

核心表没有产品类型列，而产品类型、单元数、留置权都不在 C0b 确认的锚点表里。
**固息一条用行为挣回**：一笔贷款的利率只在修改月变动，它就是固息。
浮动形状占比在 2006 与 2007 上峰值（2.46% / 3.34%），2012 之后是万分之一，
**峰值精确落在 ARM 那一波，而臣妾没给它任何产品类型信息**。
**这是代理，凡引用处标为代理。** 自住可筛（字段 30 已确认），单户与第一留置权不行。
详见 `b8_inputs_availability.md` §6.2.12.2。

## 16.10 §14.10 之后的顺序，按本轮结果重排

**B8-0b 在国债 CMT 曲线之后，不在它之前。** 理由：`b8_omega.py` 的 P2 证明合同三元组上
贴现曲线完全抵消，所以 B8-0a 不需要国债数据；但抵消的条件是 `V` 与 `V̂` 共用同一个
`(i, n, d)`，而**修改当月利率变、期限也变**，`k(i, d, n)` 两侧不同，曲线进来
（实测 `r` 在 CMT 0.5% 到 15% 上从 −0.000487 变到 −0.000494）。
B8-0b 的 `N` 是修改三角上匹配贷款的环和离散度，**算它就得先给修改月定价**。

| 序 | 站 | 理由 |
|---|---|---|
| 1 | **C9**（每格观测数，`min_size = 20`） | 核心表上约二十秒。它决定逐类底要不要做、B8-4 在哪张网格上跑、要不要下载全年份 |
| 2 | **CMT 曲线站** | B8-1 之后每一条的硬阻塞。**开工前两个构造选择必须先钉死**，见 §16.11 |
| 3 | **B8-0b 池化底**，然后 B8-1 / B8-2 / B8-3 | §15.7 的头条只需要池化 `N` |
| 4 | **逐类底与 B8-4a / B8-4b** | §15.4 才需要 `√Z(a)/√N(a)`，且按 §15.3 被 C9 闸住 |

**逐类噪声底不是必须的，它是条件性的，条件是 C9。**

## 16.11 CMT 曲线站开工前必须钉死的两条（与 C8 同性质）

**一、怎么插值到剩余期限**：线性于期限还是线性于对数期限。注册里只写了「插值」。

**二、期限超出最长可得档位时怎么办**，而这是一个有日期的真实缺口：
**三十年期 CMT 在 2002-02 到 2006-02 之间不存在**（财政部停发三十年债），
那正好是 2002Q1 那批贷款年轻、剩余期限接近 360 个月的窗口；
二十年期在 1987 到 1993 之间也缺。**外推还是封顶，跑前写下来。**

## 16.12 C9 已跑：B8-4a 有五张网格，B8-4b 没有（2026-08-16）

§15.3 的闸有答案了。全文 `b8_inputs_availability.md` §6.4 与
`claude-docs/B8_C9闸结果与分档来源_v1.md`，结果 `results/b8_c9_cells.md`。

**B8-4a 可用的五张，全部挂在借款人身上**（地板 20，`(类 × §6 四窗口)`，六档合并）：
`purpose` 826 / `fthb` 237 / `fico_llpa_coarse5` 74 / `dti_complement15` 49 /
`fico_llpa9` 36。`ltv_llpa_coarse4`（82）与 `occupancy`（36）过地板但按 §2.4
挂在房屋上，不是 B8-4 可用的网格。**两道闸独立，都要过。**

**必带的一句：过闸的里面舒服的都是粗的，细的都贴着地板。** `fthb` 两层、
`purpose` 三层，粗到几乎不构成类指标；有分辨力的 `fico_llpa9` 九层只到 36。
DTI 唯一过闸的是 `complement15`，而 §3.3 量出那张网格的秩是 0。
**过 C9 只是说可以尝试读，不是说读出来可信。**

**B8-4b 十一张全不过**，min 0 或 1，argmin 大半在 `2019Q1`：Flex 修改窗口是
2017-2019，2019Q1 那批在窗口里最多一年账龄。**§15.6 的分支因此落地，
第二域指向公司信用**，条件是 B8-3 过。**§15.3 明写这不是 B8 的失败。**

## 16.13 分档边界的来源，与一条随引用一起走的不对称

§5 只写「band」。**FICO 与 LTV 取发行人自己的定价划分**（Fannie LLPA Matrix
Table 1，现行版生效 2026-01-28），与 §3.3 主 `q` 网格取「延滞状态字段自己的划分」同理。
**DTI 没有发行人划分**：所有基于 DTI 的 LLPA 在 **2023-05-17 被移除**，
所以 DTI 取监管的 HMDA 公布分档，即 §3.3 已量过的那张。
**两者不是同一种来源，这条不对称随每一处 DTI 分档引用一起走。**

## 16.14 §3.3 的结论被一个纯计数独立重现

`dti_complement15` 十五层过闸（49），`dti_coarse6` 六层不过（11），
差别只在 complement 把 `>60` 并进「36-49 之外」而 coarse6 单独留着。
**层更多的活，层更少的死。** §3.3 是在 B7 的秩统计量上量的，
**这次是一个纯计数、在另一批数据上，给出同一条结构性结论。**

## 16.15 三角已搬上核心表，逐窗口对上 C3/C4

`experiments/b8_triangles.py`，五个窗口全部 +0，合计 51,286。
**这一份是三角判据在核心表上的唯一拷贝**，C9 与其后任何按三角取样的站都从它取，
不许再手写第二份。抄写风险两处（`cured_after_mod` 的递延臂、延滞编码的长度约定）
都量出来了，后者六档全零。

## 16.16 曲线站已跑：两条构造规则实测不承重，但门后面的人估不出月供（2026-08-17）

§16.11 有答案了。全文 `b8_inputs_availability.md` §6.5 与
`claude-docs/B8_曲线站与敏感度_v1.md`。

**一、30 Yr 的 47 个月缺口是曲线的性质。** Treasury 缺 2002-03 到 2006-01，FRED 不缺，
而 **CMT 由发行人定义，发行人没发就是没有**，FRED 在那里的是别的东西。
落在缺口里的修改 1,506 / 50,958，2.96%。

**二、两条构造规则在可测总体上够不到读数。** 环和极差最大 4.974e-14，
对 (i-b) 噪声底 6.5e-6 **低八个数量级**。P2 的抵消对每一个无递延余额的真实行都成立，
最大极差 3.553e-15，判据是有来源的 `4·|log V|·eps`。
**但仍须在跑前把两条规则写下来**，一个看不见的选择也要写下来，
否则下一个人不知道它是被看过还是被漏了。

**三、`log V` 单腿的敏感度是错的对象。** 第一次量出 267 到 7,110 倍噪声底，
而那个量在 `r` 里精确约掉，因为 `r_month` 两条腿共用 `(i, n, d)`。作废件留档。

## 16.17 新阻塞，排在曲线之前，且挡住 B8-3

**递延腿估不出合同月供。** `r` 只在月供已知处算，月供从安静月份估，
`quiet_pairs(require_never_deferred=True)` 排掉递延过的贷款。
六档共 **703,504 个递延行，月供已知的是 0**，这是构造上的必然不是数据缺失。

**§14.4 的 B8-3 主路径对是「修改」对「递延」，两侧各占一个**，
所以 **B8-3 卡在这里，而它是 §5 里唯一不需要赢下节点同一性反驳的那条**。

待验的路：递延不改月供，从递延前的安静月份估再 carry 过去。**那是推理，要量。**

## 16.18 修改三角的环窗口至今没有定义

`find_clean_cures` 定的是无修改的清洁自愈。**修改三角的环窗口哪里都没定义过。**
`b8_cmt_sensitivity2.py` 里用的「首个延滞行到修改后首个自愈行」是为了有个东西可以求和
而临时定的，代码与结果件里都标死了**不得作为注册件引用**。
**B8-1 之后每一条都要它，这是一条待注册项。**

---

# 17. 环窗口的注册，与曲线的两条构造规则（2026-08-17）

**注册件。不读任何一行预测，不改任何已跑的数。** 结清 `OBJECTIONS.md` 的
**O25**（环窗口未定义）与 **O21**（曲线两条规则未钉死）。
全文另存 `claude-docs/B8_环窗口与曲线规则_预注册_v1.md`。

## 17.0 这一节接在哪里，以及它不是新造的

**环窗口的概念层 §14.6 已经写过了**：「the duration of the closed loop, from the
last current month before the episode to the first current month after it」。
缺的是行级操作化，而**那个操作化已经存在一份**：`b8_0a_gate.find_clean_cures`
的 `t0 / start / end`，它的 docstring 自己就引 §14.6，残差跑在 `t0+1 .. end` 上。

**所以本节不发明窗口，它把已有的那一份推广到修改与递延两条臂，并把推广时必须
做的选择钉死。** `find_clean_cures` 是本节 `事件起始沿计数 == 0` 的特例。

## 17.1 三个行下标与求和范围

```
t_A   出发顶点，current
t_M   修改（或递延）起始行
t_B   归位顶点，修改之后的第一个 current
ω(环) = Σ_{t = t_A+1}^{t_B} r(t)
```

`r(t)` 定义在相邻行对 `(t-1, t)` 上，所以求和从 `t_A+1` 起、到 `t_B` 止，
含两端那两个行对。**出发顶点那一行本身不贡献残差**，它是 `V` 的锚。
窗口长度 `t_B − t_A` 个月，正是 §14.6 的分母。

## 17.2 起点靠修改反向锚定，且整个窗口内部一个 current 行都没有

两条，缺一不可：

- **(a)** 从 `t_M` 往回走到最近的 `current` 行 `t_A`，要求 `(t_A, t_M)` 之间每一行
  都不是 `current`；
- **(b)** `t_B` 取 `t_M` 之后的第一个 `current` 行，于是 `(t_M, t_B)` 之间按定义
  也没有 `current`。

**合起来：窗口内部 `(t_A, t_B)` 一个 `current` 行都没有。这一句是「它是一个环
而不是两个」的全部内容，写成一句话而不是让读者自己从 (a)(b) 推。**

这是与 `b8_cmt_sensitivity2.triangle_window` 的实质分歧，而且必须分歧。
那一份取的是**贷款的首个**延滞行（`_first_pos_per_loan(is_del)`）。三条理由：

1. **中途经过 `current` 的走法不是一个环，是两个。** 并成一个求和，正好抹掉
   B8-3 要的那个区分：§5 的候选路径对里明写着「自愈-再违约-再修改」对
   「首次违约即修改」。
2. **与 `find_clean_cures` 同形。** 清洁自愈按构造就是一段连续延滞。两个零标定
   用同一种切法，B8-0a 才是 B8-1 的零标定而不是另一个对象。
3. **临时窗口会把更早那次已自愈的发作吞进来**，而那一段正是 B8-0a 的样本。
   吞进来等于把闸的样本混进读数。

## 17.3 修改与自愈落在同一行：`t_M == t_B`，leg 3 是构造上的空

`b8_triangles.py` 的转写规矩写着「a row that turns the flag on and reads `00`
counts as cured after modification, not before it」。**所以修改那一行可以同时
读 `00`**，此时 `t_M == t_B`，`leg 3` 是空区间，环 `= leg 1 + leg 2`。

**这类环要单独计数，不许混进 `ω₃` 的读数。** §14.3 写着 `ω₃ ≈ 0` 是
「measured rather than assumed」，而在这类环上它是**构造上的恒等零**。
两者混报，「`ω₃` 实测近零」这句话就会被一批本来就为零的环撑起来。
**这是坑 23 的同一族：空集的和与量出来是零印得一模一样。**

## 17.4 一个环里两类起始沿：那条边不在 §14.4 注册的图里

连续延滞段内**同时**出现修改起始沿与递延起始沿的环，走的是
`deferred → modified`（或反向）这条边，而 **§14.4 注册的五条边里没有它**
（`current→delinquent`、`delinquent→modified`、`modified→current`、
`delinquent→deferred`、`deferred→current`）。

**处置：单独识别、单独计数、从两条三角臂里都排除。** 它是一个更长的走法，
属于 §17.5 的路径材料，不是 B8-1 的三角。
臂的归属按段内第一个起始沿的类型命名，**仅用于给这类环起名，不用于把它塞回
某一臂**。

## 17.5 路径累积 `Ω` 是另一个对象，两处引用都要写清是哪一个

| 记号 | 是什么 |
|---|---|
| `ω(环)` | 一次闭合走法的残差和。**原子。B8-1 / B8-2 读它。** |
| `Ω(路径)` | 到终点为止，该笔贷款走过的**所有**环的 `ω` 之和。**B8-3 读它。** |

「自愈-再违约-再修改」的 `Ω` 有两项（一个清洁自愈环加一个修改三角），
「首次违约即修改」的 `Ω` 有一项。**B8-3 的原话是 accumulated `ω`，那是 `Ω`。**
不分开命名，B8-3 会在实现时被写成单环比较，而单环比较测不到它要测的东西。

## 17.6 两个顶点的条件：两条承重，一条防呆

出发顶点 `t_A` 与归位顶点 `t_B` 同样三条：

| 条件 | 地位 | 来源 |
|---|---|---|
| `delinq == 0` | 承重 | 顶点定义 |
| `rem_legal` 非空 | **承重** | 坑 13 二次更正：终止行报一个余额零然后把合同状态整体停报，**挡住终止行的是这一条**（六档漏网 5/2/5/1/0/0） |
| `upb > 0` | **防呆** | 同一条更正在六档上删掉零个对，地位是防呆不是修复，照 §16.6 的处置 |

**额外一条并入 `upb > 0`：出发顶点不得是贷款的首行**（坑 13，首行 UPB 恒零，
六档 1.0000）。它被 `upb > 0` 蕴含，**但要单独印计数**，因为它是构造截断不是
数据缺陷，两者的裁定不同。

**再加一条从 `find_clean_cures` 原样继承**：窗口内报送月份必须连续
（`period` 逐月差恒为 1）。断月的窗口做不了逐月 carry，丢弃并计数。

## 17.7 不闭合的三种，分开数，不许合并成一个「掉样」

1. **档末仍在延滞** —— 右删失。
2. **已终止且从未自愈** —— 真的没有环。
3. **修改前没有连续延滞段** —— 不是三角（字段 42 在 `current` 上翻 `Y`）。

三种的计数分开报。§7 的规矩：silence about a dropped record is how a sample
becomes a selection。**第 1 类与第 2 类合并是最容易犯的那个**：一个是观测窗口
的性质，一个是贷款的性质。

## 17.8 环内多次同类起始沿，归一个环，并单独印计数

`t_M` 取连续延滞段内的**第一个**起始沿。段内之后的同类起始沿仍在窗口内，
落进环和。**归位之后的起始沿开新环。**

**段内同类起始沿多于一个的环要单独印计数**：那是 HAMP 试用期转正的
population，§14.3 已经写了它「measured rather than assumed」，这里给它一个
可数的载体。（不同类的起始沿走 §17.4。）

## 17.9 递延臂同一条窗口规则，起始列是开着的问题，本节不裁

递延三角 `current → delinquent → deferred → current` 同形，**窗口规则一字不改**。

**递延起始沿是字段 108。** 两列上升沿实测差 13 到 18 倍（2012Q1 是 267 对 4,882，
2019Q1 是 1,124 对 14,777）。**本注册写一句：窗口规则与起始沿的列选择是两件事，
换列不改窗口。**

**原文把列的选择写成 O24 与 B10 §19.9 开着的问题，那句已删除。**
问题在 2026-08-17 关了，而本节写的保证正是它关掉之后兑现的东西。
C10-4 在两列的上升沿上同时读合同是否移动：字段 63 那一侧动利率 46.1%、动期限
84.2%，字段 108 那一侧 `still = 0.9966`（利率与期限都不动）。**递延起始沿是字段
108**，`b8_inputs_availability.md` §6.6.11 落的判乙，O27 已结为 D20。

**换列没有改动本节任何一个字**，这是本节当初写那句保证的全部意义：
`b8_loops.py` 的 `DEFER_FIELD` 从 63 改到 108 之后，§17.1 到 §17.8 的窗口规则
一行未动，重跑的窗口计数按新起始沿移动而窗口的定义没有移动。
**一个写在裁定之前、在裁定之后被兑现的保证，比一个事后补的说明可信。**

## 17.10 可测性：整段月供已知，掉样按修改前后两侧分开印

`r(t)` 只在合同月供已知处算，**而要的是前一行的月供**（§14.2 的反事实是 `t−1`
的合同往前推一个月）。修改臂的窗口按构造跨一个合同期边界，递延臂不跨。
**所以环可测的条件是：窗口内每一个月的前一行都有已知月供。**

**掉样计数必须按修改前 / 修改后两侧分开印。**

**2026-08-17 两处删除与更正。原文有两句已删：一句写 `contract_periods`
「在修改起始沿与递延起始沿上都切」，一句写递延行月供已知 0（六档 703,504）。
掉样按两侧分开印这条留着，挂在上面的理由整个换掉了。**

**一、切点。** `contract_periods` **不在字段 108 上切**，而且 §6.6.17.2 明裁
不许切：C10-4 在字段 108 的上升沿读 `still = 0.9966`，利率与期限都不动，
合同月供不可能变，切一刀只会把一个合同期劈成两段、每段的安静月更少、
估计更差。**它切的是字段 63 的上升沿**，因为那一侧是再签约。
**所以窗口跨不跨合同期边界，取决于这个环走的是哪条臂**，
修改臂跨，递延臂不跨。原文那半句把两条臂说成同一形状。

**二、703,504 这个数不是递延行。** 它是**字段 63 的在行数**，也就是修改
population 的行数，被当成递延行引了一路（O24 已按这个重写）。
递延臂的实测在 §6.6.15：**全路径月供已知的占 92.86%**，不是 0。

**所以「本站现在最大的阻塞」这个判断也不成立，而两侧分开印这条要求活下来。**
它现在的理由不是「有一侧恒为零」，而是**两条臂的合同期结构本来就不一样**
（见上一条），合并的掉样数把两种不同的可测性搅在一起。
**一个理由被推翻的要求，如果本身还站得住，要重新给它一个理由，
而不是靠原来那句话的惯性留着。**

## 17.11 腿的切分是记账，环和不依赖它，但要断言恒等式

§14.2 已定。切点：

```
leg 1 = (t_A, t_M)      current → delinquent
leg 2 = t_M 那一个月     delinquent → modified
leg 3 = (t_M, t_B]      modified → current
```

**三段之和恒等于环和，这是恒等式不是判据**，但要在代码里断言它。
**`t_M == t_B` 时 leg 3 是空和，断言照样成立**，所以断言不能代替 §17.3 的计数。

**2026-08-17 删除并更正：原文给的理由是「它能抓住窗口实现的错位」，那句已删，
因为它不成立。要求本身留着。**
四个量都从同一个前缀和数组来，三条腿望远镜式抵消，**`t_M` 取什么都成立**
——错一行、错十行、甚至属于另一笔贷款都成立。**在前缀和实现下这条断言测的是
浮点加法器，抓不住它被写下来要抓的那个错位。**

断言留着（它确实能抓住前缀和或范围助手本身写坏），
**另加一条真的能干那件事的**：`b8_loop_omega.replay` 从窗口下标出发、
逐月用 Python 重新求和，与向量化的答案比。自检里把 `t_M` 故意挪一行，
**断言恒等式仍然成立而 `replay` 报不符**，那一条是对检查本身的检查。

**教训不在这一节，在方法层**：一条断言写下来的时候要问它在**将要采用的实现下**
能不能失败，而不是在概念上能不能失败。详见 `b8_inputs_availability.md` §6.6.23.3。

## 17.12 这条注册取代什么，欠谁一笔账

`b8_cmt_sensitivity2.triangle_window` **作废为注册件**（它自己已标死不得引用）。

`results/b8_cmt_sensitivity2.md` §3 的环级数字是在那个临时窗口下出的。
按 R01，改口径要双报：**下一次在注册窗口下重跑曲线敏感度，必须同时印两个窗口的
环数与环和，且必须印 delta**（坑 18：一次没法跟旧口径做差的重跑不结清双报）。

临时窗口的环数留档：**6,272 / 13,134 / 17,061 / 2,954 / 5,411 / 4,647**。

## 17.13 一条必须先说清的非冲突：C3/C4 数的是贷款，§17 数的是环

`b8_triangles.py` 的 C3/C4 判据是**每笔贷款一次**
（`if s.mod_period and s.seen_current and s.first_delinq and s.cured_after_mod`），
六档合计 **51,286** 是**贷款数**。

**§17 的环是每次闭合走法一个，一笔贷款可以有多个。** 两个数不是同一个对象，
而且方向不是单向的：

- 一笔贷款可以贡献多个环 → 环数可以多于 51,286；
- 一笔被 C3/C4 数进去的贷款可以贡献**零**个注册环（例如在 `current` 上翻 `Y`
  再违约再自愈的走法，§17.7 第 3 类）。

**两个数的差必须量出来印，不许假设它小。** §16.15「三角判据唯一一份」那条纪律
指的是三角的判据只写一份，**不是说环等于三角**。

---

## 17.14 曲线，插值：线性于期限（`linear_in_tenor`）

**来源。** 财政部按固定档位公布 CMT，**档位之间没有发行人约定**，
所以 §16.13 那条「取发行人自己的划分」在这里没有对象。
落到次级规则：**取不引入自由参数的那一条**，即线性于期限。

## 17.15 曲线，超出最长可得档位：封顶（`cap`）

**来源不是「保守」，是与已下的裁定一致。** §16.16 第一条裁的是
**CMT 由发行人定义，发行人没发就是没有**，30 Yr 那 47 个月缺口据此判成曲线的
性质而不是下载工件（两来源互校）。

**外推等于给一个发行人不卖的期限造一个价，与那条裁定直接冲突。**
同一条原则，两处结论必须一致，否则那条裁定就只是为了解释缺口临时找的说法。

**后果，写明并随引用一起走：** 2002-03 到 2006-01 之间，剩余期限 360 个月的
贷款读到的是当月最长可得档位（那段里是 20 Yr）。
落在缺口里的修改 **1,506 / 50,958，2.96%**。

## 17.16 这两条规则今天够不着任何一行，而这**不等于**「实测不承重」

§16.16 写的「两条构造规则实测不承重」**偏松，本节把它改准**。逐条：

1. **无递延余额的行上，六种构造的 `r` 逐位相同**（最大极差 3.553e-15，
   判据 `4·|log V|·eps` = 1.243e-14）。**那是代数抵消，不是曲线鲁棒**：
   `V = LP(bal, i, n)·A(d, n)`，`LP` 线性于余额，两腿共用 `(i, n, d)`，
   年金因子整个约掉。
2. **曲线唯一进得来的门是气球项** `nib·(1+d)^-bn`。
3. **带气球的行里月供已知的是 0，带气球的环是 0**，六档全零。
4. 所以 **4.974e-14 不是曲线规则的效应量，是抵消之后剩下的舍入**。
   正确的写法是**今天够不着**，不是「不承重」。
5. **什么时候会变**：O24 解开、递延臂进来之后，气球项才第一次有已知月供的行。
   **那一天要重跑这张表。不许引今天的读数说它不承重。**

**2026-08-17：那一天到了，这张表现在是欠的。** 触发条件是本节第 5 条自己写的，
两半都已发生：O24 已按 §6.6.15 重写（那 703,504 是字段 63 的行数，递延臂的
全路径月供覆盖率是 **92.86%**），载体也已由 C10-4 定到字段 108。
**气球项第一次有已知月供的行，所以第 3 条的「带气球的环是 0」不再成立。**

**账记在这里：`b8_cmt_sensitivity` 的六种构造对比要在 `V` 改口径之后重跑**，
而且要在**带气球且月供已知**的行上重读，那是第 2 条说的曲线唯一进得来的门。
**在重跑之前，本节 1 到 4 条的读数只对无气球的行成立，不许引它们说曲线规则
不承重。** 本节当初把「不承重」改成「今天够不着」，就是为了让这一天到来时
有一笔可以还的账，而不是一个已经写死的结论。

## 17.17 一条新登记的缺陷：空集印零，坑 23 在同一份文件里隔一节复发

`results/b8_cmt_sensitivity2.md` §2 已经把不可测的格子改成 `not measurable`，
**而 §3 的「loops with a balloon / their p50 / their max」三列仍然印
`0` 与 `0.000e+00`。** 空集上的中位数与「量出来是零」印得一模一样，
正是坑 23 的原话。**同一轮、同一份文件、隔一节复发。**
已加进 `HANDOFF_B8.md` 坑表第 26 条。

## 17.18 本节不裁什么

| 项 | 为什么不在这里裁 |
|---|---|
| **递延起始沿：已裁为字段 108** | C10-4 判乙，O27 结为 D20（2026-08-17）。**§17.9 保证的「换列不改窗口」已经兑现**，换列时本节一字未动 |
| `MIN_QUIET_FOR_PAYMENT` 提不提高 | 覆盖分布已印，是另一件事 |
| §7 的三个未施加过滤器（单户 / 一顺位 / 自住） | 与窗口无关，另记 |
| O18 那 46.65% 未命名的少付月份 | 与窗口无关 |
| 环和的符号预期 | §14.3 已写，是两项赛跑，事先定不下来 |

---

# 18. B8-0b 的预注册：`Z` 与 `N` 到底是什么

**写于 2026-08-17，环和已经跑出来但一个数都没往这里引。**
本节定义 B8-0b 的两个量、匹配格的构造、以及每一种结局对应的处置。
**§8 管着它：跑完不许回头改。**

## 18.1 `Z` 的形状是 B3 给的，照抄

`b3_cip_slice.md` §3：

```
Z(g) := (1 / k²) · Σ_{i,j ∈ g} ( x(i) − x(j) )²      =  2 · Var_i( x(i) )
```

在 B8 上，`x(i)` 是**环 `i` 的环和 `ω`**，`g` 是被比较的那一组环。
**两条路都算，必须机器精度一致**，这条 B3-1 的检查照抄：
枚举有序对与方差，相对误差要在 `1e-12` 以下。

**单位**：`ω` 是对数比，无量纲。`√Z` 与 `ω` 同单位，可以直接并排读。

## 18.2 `N` 有两个候选，注册文字在它们之间是含混的，**这里裁**

§4 写的是「loans matched on class and on the full realised path should carry
the same loop sum. Their dispersion is `N`」。
§14.5 写的是 B8-0a(ii) 是「the tightest zero calibration this stage has」。
**这是两个不同的对象，而 B3 的 `N` 是后一种。**

| 候选 | 构造 | 问题 |
|---|---|---|
| **甲：匹配格内离散** | 按（类、实现路径）分格，格内 `2·Var(ω)` | **它不是测量噪声。** 同一条延滞路径上的两笔贷款，修改条款可以完全不同（一个降息一个展期），`ω` 因此不同，**而那个差是真实异质性不是噪声**。用它当底会把信号算进底里 |
| **乙：零校准臂** | 清洁自愈的环和，**真值按构造为零** | 这是 B3 的 `N` 的形状（两种构造读同一个对象），也是 §14.5 已经点名的东西 |

**裁定：`N` 取乙，匹配格内离散另立名字叫 `M`，两个都报。**

三条理由，按承重排序：

1. **甲把信号算进底里。** `Z` 度量的正是「同样走一圈的两个人拿到的 `ω` 不同」。
   甲的格内离散度量的是同一件事的一个子集。**用一个量的子集当它自己的底，
   比值会被压向 1，而压多少取决于格切得多细** —— 那是一个可以被切法操纵的判据。
2. **乙有真值。** 清洁自愈的合同**确实没有改变**，所以 `ω` 的真值是零，
   剩下的全部是构造误差、报送噪声与冻结（§6.2.7 已量过冻结）。
   **这是「真值为零的臂走同一套机器」，`MEASUREMENT.md` 第 7 条要的就是这个。**
3. **`M` 仍然值得报，但它是别的东西**：它是「路径解释不了多少 `ω`」的读数，
   是 B8-4 的前置，不是 B8-1 的底。**报，标清楚，不进比值。**

## 18.3 `N` 的具体口径，逐条

```
N := 2 · Var( ω(环) )   在清洁自愈环上
```

**清洁自愈环的定义直接用 `b8_0a_gate.find_clean_cures`**，不另写一份：
延滞过、回到 current、**从不带字段 42 的 `Y`、从不带正的字段 63、
从不带正的字段 108**（O28 之后的口径）。

四条附加约束，都写在跑之前：

| # | 约束 | 为什么 |
|---|---|---|
| N1 | 环和走**同一条代码路径**（`b8_omega.row_residuals` + `b8_loop_omega.loop_sums`），不许为清洁自愈另写求和 | B3 的 `z(i,i)=0` 那条：零校准必须过同一套机器，不许短路 |
| N2 | 窗口用 §17 的窗口规则，`t_M` 取延滞段的第一个月 | 清洁自愈没有修改起始沿，所以 `t_M` 的定义要单独说：**取第一个延滞月**，腿的切分因此仍然成立而 leg 2 不再是「修改月」 |
| N3 | 可测性条件与 §17.10 一字不改 | 底与信号必须画在同一个可测集上，否则比的是两个人群 |
| N4 | **按档分别算，也报池化**。池化的那个是 B8-1 用的（§15.4） | §15.4 已定 |

**N2 是本节唯一的新构造，它有一个已知的后果**：清洁自愈的 leg 2 不是再签约，
所以三腿切分在这条臂上是记账中的记账。**`N` 只用环和，不用腿。**

## 18.4 匹配格 `M`：怎么切，以及**不许**按什么切

```
M := 2 · Var( ω )  在格内，然后按格大小加权平均
```

格的键，**三个，全部在 `ω` 的算术之外**：

| 键 | 取值 | 为什么它不循环 |
|---|---|---|
| 臂 | 修改 / 递延 | §14.4 的层，与 `ω` 的算术无关 |
| 错过的月份数 | `t_M − t_A`，按 §3.3 的粗网格分档 | 是路径，不是合同 |
| 归位耗时 | `t_B − t_M`，同样分档 | 是路径，不是合同 |

**明确不许进格键的：利率、期限、余额、月供、气球、类别索引里任何
由合同派生的东西。** 理由一句话：**`ω` 是这些量的函数，
按它们分格等于按因变量分格，格内方差会趋于零而比值会趋于无穷。**
这是 C11 判据 B 那个循环的同一个形状（§6.6.16），**那一次是跑完才发现的。**

`MIN_CELL` 用 §6.4 的 20，格小于它的合并进「其余」并印计数。

## 18.5 结局到处置的全映射，**写在跑之前，而它可以改**

**2026-08-17 陛下裁定，本节的地位改了，§8 在这一点上一并改。**
跑之前写下映射照写，**但它是「跑之前臣妾以为会怎样」的记录，不是承诺**。
现实说话之后就改，改的时候记下改了什么、为什么、以及原来那条错在哪。

理由是陛下的：**不跑怎么知道映射什么。** 一个在信息最少的时刻定死、
之后不许动的判据，是拿「一开始猜中」当正确性的标准，
而科学积累从来不是那样发生的。**留下的价值不是它约束了什么，
是它记录了预期与现实的差**，那个差本身是信息。

**本节跑完之后立刻改了两处，见 §6.6.26。**

| 结局 | 处置 |
|---|---|
| `√Z/√N > 3`，两张 `q` 网格都过 | B8-1 的**必要条件**成立。**不等于 B8-1 成立**，B8-1 还要 §3.3 的两网格与 §6 的窗口 |
| `√Z/√N` 在 1 与 3 之间 | **B8-1 判不成立并照登**。不许改底、不许改格、不许换统计量 |
| `√Z/√N ≤ 1` | 信号在底以下。**整站的头条按 §15.7 已经移到 B8-3**，所以这不停站，但 B8-1 记为 fail |
| `N` 的样本 `< MIN_CELL`（20） | **B8-0b 判不可测**，B8-1 不跑，理由印在结果件顶部 |
| `N` 逐档差一个数量级以上 | 池化的底不可用，**只报逐档**，并把差异当成一条待解释的读数登记 |
| `M < N` | **格内离散比零校准还小** → 格切得太细或格键漏进了合同量。**回头查格键，不是接受这个数** |
| 枚举与 `2·Var` 不一致（相对误差 > 1e-12） | **闸。代码坏了，下面全部不可读**（B3-1 照抄） |

## 18.6 本节不裁什么

| 项 | 为什么 |
|---|---|
| B8-1 本身 | 它要两张 `q` 网格，本节只给底 |
| 逐类底 `√Z(a)/√N(a)` | §15.4 要的，且被 §15.3 的 C9 闸住，B8-4a 才用 |
| `M` 的读数说明什么 | 它是 B8-4 的前置，不在这里解释 |
| 递延臂要不要单独的底 | **要，N4 已写「按档分别算」，臂同理**，但两臂的底怎么合并是 B8-1 的事 |


## 18.7 实测之后：判据从 `√Z/√N` 换成 MAD 比值（2026-08-17）

**§18.1 定的 `Z = 2·Var` 是照抄 B3 的，而 B3 的 `x` 是有界的基点量级偏离。
`ω` 在清洁自愈臂上从中位 8.9e-6 到最大 4.1e-1，跨五个数量级。那个形状搬不过来。**

读数在 `b8_inputs_availability.md` §6.6.26.5：底臂的 `2·Var` 从 n=100 的
5.3e-09 单调爬到全样本的 1.5e-05，**2,900 倍，最后一步还在爬**，
p10–p90 倍差长到 293x；同一条臂的 MAD 从 n=100 起就平到三位有效数字。
**信号臂两个都收敛。**

**改：**

```
判据 = MAD(信号臂 ω) / MAD(清洁自愈臂 ω)
```

两边同一个估计量，这正是 B3 那个形状真正要求的；唯一的改动是尺度估计量。
`√Z/√N` 与余额匹配版按 R01 并排留着，**收敛表就是那份双报的理由**。

**门槛不在这里定。** §5 的 `> 3` 是给 `√Z/√N` 写的，MAD 比值是另一个量，
它的门槛要么单独立、要么这条预测降级为「报数不设门槛」。
**2019Q1 实测 6,501 / 50,680 / 4,931，任何合理门槛都不接近边界**，
所以这一条不急，登记为开着的。

**保留意见**：Theorem 3 是方差分解，MAD 不是那条定理里的量。
但一个不收敛的方差也检验不了方差分解。**`Z` 本身估得很好且收敛，
不收敛的只有底**，所以能说的是「信号的中心在底的中心之上五万倍」，
**不能说的是「方差分解成立」**。


## 18.8 §14.5 那句「must return zero」是错的，P4 一直在断言正确的那句

§14.5 写 B8-0a(i)「the clean-cure round trip ... **Must return zero to
floating-point tolerance**」。**`b8_omega.py` 的 P4 同时证明并断言它不为零**，
读 −9.04e-06 / −5.45e-05 / −1.93e-04（k = 1 / 3 / 6），
并且 P4 的注释原话就是「**The clean-cure round trip does NOT return zero, and
this is a property of the construction**」。

两句话在同一份仓库里并存了很久，**而找底的时候读到的是 §14.5 那句**，
于是一个确定量被当成了噪声。实测（`b8_inputs_availability.md` §6.6.27）：
`corr(ω, closed)` 五档 `+1.0000`、一档 `+0.9993`，中位绝对值对到四位有效数字。

**更正：**

```
B8-0a(i)：清洁自愈的往返和返回 `loop_residual_ideal(B0, i, P, k)`，
          误差在字段 12 的分位取整以内（半分钱 / 余额 ≈ 3.0e-8）。
          闸的判据是这个误差，不是环和本身。
B8-0b：   `N = MAD(ω − closed)`，量出来 2.68e-08 到 5.22e-08。
```

**B8-0a(i-a) 的既有读数不受影响**：它比的本来就是 `stream` 对 `closed`，
量的一直是这个误差（`ratio_max = 0.400`）。**错的只有 §14.5 的散文。**

**保留**：修改臂也带一个同类的确定性离散分量而它**没有闭式解**。
若与清洁自愈臂同量级（1e-5），占信号（1.4e-1）的万分之一，可忽略；
**这是推断不是测量**，登记为开着的。

---

# 19. B8-3 的读法：制度对比，跑之前写下来的预期

**写于 2026-08-17，`ω` 与底都已在盘上，B8-3 一个数都没读。**
按 §18.5 已改的地位：**这是「跑之前臣妾以为会怎样」的记录，不是承诺**，
现实说话之后就改，改的时候记下改了什么、原来错在哪。

## 19.1 B8-3 要的是什么，以及它**不**要什么

§5：**两条可实现的路径到同一终态，携带不同的累积 `ω`。**
§15.7：这是 Corollary-1 形状的**存在性主张**，由一条边上的一个不等式决定。

**所以 B8-3 不需要赢因果识别。** 它不主张「服务商选了哪条路导致了 `ω` 的差」，
它主张「到达同一个 `current` 的两条已实现路径，累积 `ω` 不同」。
**这是关于状态空间的陈述，不是关于选择的陈述。**

**但组分差异仍然要报**，因为读者一定会问，而且不报就等于假装它不存在。
所以本节分两层：**存在性**（B8-3 本身）与**分层后的差**（更强，但不是 B8-3 的门槛）。

## 19.2 路径对

**主对**（§14.4 已定）：

```
delinquent → modified → current      对      delinquent → deferred → current
```

两条都在 §17 的窗口下有环和，六档合计修改臂 49,649、递延臂 35,659。

**次对**（§5 注册，本节不跑，登记）：一次 90 天延滞对两次 30 天延滞；
先自愈再违约再修改对第一次延滞就修改。**它们是时序对比，
而 §14.4 已经说明时序对比会被「两个终点的欠款史不同」挡住。**

## 19.3 统计量：中位数差，以底为单位

`ω` 在两条臂上都是重尾（§6.6.26 量过），**所以不用均值也不用方差**。

```
Δ    := median(ω | 修改臂) − median(ω | 递延臂)
Δ/底 := Δ / MAD(ω − closed)          底在 §6.6.27，约 3e-08
```

**离散度用 MAD**，与 B8-0b 同一个估计量，理由同 §18.7。

## 19.4 分层：用什么切，以及**不许**用什么切

| 键 | 为什么它可以进 |
|---|---|
| §6 的事件窗口 | 日历，与路径和合同都无关 |
| 错过的月份数 `t_M − t_A` | 路径 |
| 归位耗时 `t_B − t_M` | 路径 |

**不许进的：利率、期限、月供、气球、余额。** 前四个是 `ω` 的自变量。
**余额单独说一句**：`ω` 对 `(余额, 气球)` 是零次齐次的（`V` 线性于两者，
而 `ω` 是对数比），**所以按余额分层不会机械地驱动结果**；
不进是因为它是合同量而本节的分层只用路径与日历，**这是一条比必要更严的线**，
理由是 §6.6.16 那次循环是跑完才发现的。

`MIN_CELL = 20`，小格合并进「其余」并印计数。

## 19.5 读法：三样一起看

1. **存在性**：`Δ` 与 `Δ/底`，池化与逐档。
2. **分层后的差**：格内 `Δ`，按格大小加权；**以及符号一致性**——
   多少个格的 `Δ` 同号。**这一条是关键**：若差来自组分，符号会在格间翻；
   若来自路径，符号会稳。
3. **格内置换零假设**：在格内打乱臂标签，重算加权 `Δ`，做 999 次，
   报观测值在零分布中的位置。**打乱在格内做**，所以它检验的是
   「给定路径与窗口，臂标签还携带信息吗」。

## 19.6 已经知道会咬人的两件，写在前面

**一、递延几乎全在 COVID 窗口。** 六档 32,533 个递延三角里 31,057 在 COVID
（§14.4 已更正，1,476 在窗口外）。**所以跨窗口的分层里，
COVID 之外的递延格多半过不了 `MIN_CELL`。** 那不是失败，是可数的事实，
**要印格数与掉样，不许把「窗口不可比」写成「没有差」**。O30 记着这件事。

**二、两条臂的可测率不同**（§6.6.25：修改臂 0.7286–0.9068，
递延臂 0.8386–0.9853）。**可测性本身与臂相关**，
所以本节要印两条臂各自的可测率，**并且承认分层不能修掉这一条**：
不可测的环没有 `ω`，它们不在任何格里。

## 19.7 结局到处置：**跑之前的预期，可改**

| 结局 | 当下的处置 |
|---|---|
| `Δ/底` 远大于 1 且符号在格间一致 | **B8-3 的存在性成立**，且分层没有推翻它 |
| `Δ/底` 远大于 1 而符号在格间翻 | **存在性仍成立**（它不需要赢组分），但要明写「差与路径的关联不稳」 |
| `Δ` 在底的量级 | B8-3 判不成立并照登 |
| 置换零假设里观测值不极端 | **格内臂标签不携带信息**。存在性不受影响，第 2 层的读数作废 |
| COVID 之外的格全部不过 `MIN_CELL` | **照实印**：主对只在 COVID 上分层可读，其余窗口只有池化 |

## 19.8 本节不裁什么

| 项 | 为什么 |
|---|---|
| B8-1 与 B8-2 | 各自的判据不同，另跑 |
| 次对（时序对比） | 已登记未跑 |
| 因果 | **B8-3 不主张因果**，§19.1 |
| 两条臂可测率不同要不要修 | 不能修，只能报，§19.6 |
