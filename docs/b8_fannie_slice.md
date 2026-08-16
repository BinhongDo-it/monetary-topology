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
V(t) =  PV[ level payment on the interest-bearing balance
            at rate (9), over (17) months ]
      + PV[ the non-interest-bearing balance (63) as a balloon at (19) ]
      -  principal forgiven to date (64)
```

Discounted on the constant-maturity Treasury par yield at month `t`, interpolated to
`(17)`, as §3.1 fixes. **`ω < 0` is a gain to the household.** Stated once here and
used with this sign everywhere in the stage.

The horizon is **17**, not 18, per §13.2. Where 19 is present it agrees with 17
exactly and either may be used; 17 is primary because it needs no arithmetic on the
reporting date.

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

**One thing the deferral route cannot do, declared now.** Deferral exists only in the
COVID window, so **B8-2 cannot be run on the deferral triangle**. B8-2 remains a
modification-route test across §6's four windows, and the deferral route is reported
without a window comparison.

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

**Sample:** 366,345 clean cures across the six archives, from C5.

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
| **C8-6** | do 107 and 108 describe the deferral, and does 108 agree with the change in 63 | 14.4's deferred tier needs the deferred amount to be readable from one field, not inferred |

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
