# B9: the measured zero, and the path share

**Status: pre-registration. No data retrieved.** Registered 2026-08-16.

Sibling of [`b3_cip_slice.md`](b3_cip_slice.md) and [`b8_fannie_slice.md`](b8_fannie_slice.md).
Defines `π`, the statistic `PROJECT_PLAN.md` §22.4 registers as the cross-domain
currency, and calibrates it on real data rather than on a construction.

---

## 1. What this stage is for

Two jobs, and the first one is the load-bearing one.

**Job one: produce a measured zero.** Every holonomy reading in this repository is
currently a non-zero read against a synthetic or permutation baseline. B3-2's
`z(i,i) = 0` and B8-0a's out-and-back both check the **code**. Neither checks the
code **plus the state-space definition plus the `ω` construction** on real data.
Until some real carrier returns zero, a non-zero reading elsewhere cannot be
distinguished from an artefact of how states were cut.

**Job two: a within-instrument gradient.** The same fund, the same day's close,
with the arbitrage channel open on some days and impaired on others. That is
`b1_setup.md` §3's canonical loop with more held fixed: there the dwelling, street,
building and unit are held and only the holder's entry date varies; here the CUSIP
and the trading date are held and only **who you are** and **what the arbitrage
channel is doing** vary.

**What this stage is not.** It is not a claim that ETF premiums are a discovery.
They are a published, regulated, extensively documented quantity. §9 states what
is and is not new.

### 1.1 Why the zero is the informative half, which is not the intuitive reading

A non-zero at the calm end would be the **ambiguous** outcome, not the good one. It
admits two readings that this stage cannot separate: either terms are agent-specific
all the way down, or `π` has a floor coming from state coarseness or the noise
floor. **A zero, with §5's three guards cleared, is the clean outcome.**

The ABM cannot supply this. `a3_asset_channel.md` sets `κ = 0` and holonomy
vanishes **by construction**, which is the A3-3 family: an identity read at machine
precision. `a3_asset_channel.md` §6.6 states the same limit from the other side.
**A real-data zero is a different object, because nothing in real data forces it.**

---

## 2. The graph, and the two routes

Positions, held to three:

```
cash        the numeraire position
basket      the fund's published creation basket, held directly
etf         shares of the fund
```

Edges, all realisable and all with published terms:

| edge | route | who can traverse it |
|---|---|---|
| `cash → etf` | secondary market, at the closing price `P` | **anyone** |
| `cash → basket` | buy the constituents at their closing prices, value `NAV` | anyone |
| `basket → etf` | **creation**, one creation unit, at a disclosed transaction fee `f` | **Authorized Participants only** |

Three vertices, three edges, `b₁(G) = 3 − 3 + 1 = 1`. A triangle, not an
out-and-back, which is Corollary 2's scoping condition.

**The loop.** Traverse `cash → basket → etf → cash`, against the direct
`cash → etf`. In logs the sum is

```
λ  =  log(1 + premium)  −  log(1 + f)          premium = (P − NAV)/NAV
```

**Under a gradient field `λ ≡ 0`**, whatever the fee is, because the fee would
itself be a difference of potentials on that edge. The fee does not make `λ`
non-zero; it is subtracted. **`λ ≠ 0` is the violation and `λ = 0` is the
hypothesis**, which is `b1_setup.md` §3's structure unchanged.

**The hole is in the same object.** The closing leg `basket → etf` is absent to a
non-AP **at any price**, so a non-AP holding the wrong side of `λ` cannot recover
it. That is `b1_setup.md` §5's rule: it contributes to `H⁰`, not to the curl. **It
is an institutional fact and it is reported, not estimated.**

### 2.1 Two arms, and only one of them is free

- **B9-A, the loop.** Daily `P`, `NAV`, shares outstanding, median bid-ask spread
  and the creation fee are public. Rule 6c-11 requires the premium/discount and the
  median bid-ask spread on the fund website. **Runnable now.**
- **B9-B, the size gradient.** `PROJECT_PLAN.md` §22.12's within-instrument scan of
  `π` against order size over ADV. It needs trade-level data with size. TAQ is
  behind WRDS; TRACE disseminates with a **size cap**, and that cap is itself a
  ninth-form risk that would have to be diagnosed first. **Availability-gated. If it
  fails, B9 reports A only and says so.**

**These two arms measure different summands.** B9-A's hole is `H⁰`; B9-B's size
channel is the curl, `H¹`. `a3_asset_channel.md` §2 split exactly these two objects
and gave them different homes. Their data availability differs, so they are
separated here rather than run together.

---

## 3. `π`, defined

For a set of traversals indexed by `k`, each with an accumulated `ω_k` and a
terminal state `s_k`:

```
π  =  Var( ω_k | s_k ) / Var( ω_k )
```

the residual share from a regression of accumulated `ω` on terminal-state fixed
effects.

Three properties, and all three are required for it to serve as the cross-domain
currency:

1. **Under exactness `π ≡ 0`.** If `ω = d⁰ψ`, the accumulation depends on the
   endpoint alone. **The null is hard and is not calibrated.**
2. **Dimensionless and bounded `[0, 1]`.** Basis points, percentages and currency
   units cancel.
3. **The machinery exists.** It is the slice-side counterpart of Theorem 3's square
   within-share; both are variance decompositions.

**`π` is defined relative to what you condition on, and that is reported rather
than hidden.** Conditioning more finely lowers `π` mechanically. The reported
object is therefore **`π` as a function of state-grid fineness**, not a single
number. Whether it reaches zero or plateaus above zero is the finding. This is
B7's grid lesson applied before the fact rather than after.

**Grid rule, inherited from B7 and not re-argued here:** every reading is
computed on at least two terminal-state grids. **A reading on one grid is not a
result.**

**Correction, 2026-08-16. B7-6 did not fail, and the rule it supports now rests on
something stronger.** `b7_interaction_rank.md` §3.21 found that B7's class levels
were stored alphabetically and read positionally, so **every partition that stage
built merged the wrong classes**: the grid it called the regulator's bucket scheme
put `<20%` in the same class as `49`. On the corrected partitions the fine grid
reads `2` and the coarse grid reads `2` under both nulls. **B7-6 passes.**

**Further correction, 2026-08-16 evening. That `2` is withdrawn** (`b7_interaction_
rank.md` §3.25 to §3.29): it was two diagonal entries of a class second-moment
matrix belonging to the two classes holding about one loan per cell-class entry,
and a constructed field with **zero interaction** reproduces it in forty
repetitions out of forty. **B7 closed with no rank at any class resolution.**

**This document's grid rule is unaffected and its evidence is the carry, not the
rank.** B7-11 measures what a coarsening does to a direction, `0.15%` and `0.48%`
into one partition against `97.9%` into the other, and that holds whether the
direction is signal or noise. **It is the one result in that stage that survived
the withdrawal, which is why it is the one cited here.**

**And one thing B7's death is worth to this stage, before it runs anything.** B7
died of a statistic that appeared in none of its design summaries: the observations
per state-cell entry, state by state. A terminal state holding one or two
observations per cell gives any second-moment reading a diagonal that no
permutation null can reproduce. **Report observations per state-cell entry for
every terminal state before any `π` is read**, and print the loading or the state
ordering beside the magnitude. B7 read a rank for a day and a half before anyone
printed the eigenvectors.

**What survives, on better evidence.** §3.22's B7-11 lays each fine eigendirection
on each coarsening and measures what arrives. The complement grid, a legitimate
coarsening of the same regulator-published variable, carries the fine grid's first
direction at **`0.15%`** and its second at **`0.48%`**, and reads rank `0` where
the fine grid reads `2`. **A coarsening can take a rank from two to zero, measured,
with a number.** That is a sharper statement than "two grids disagreed" and it is
what this document's grid rule now rests on. **The rule is unchanged and is not
re-argued here.**

**What does not survive is the precedent.** There is no longer a "B7-6 disposition"
in which a reading is reported as grid-dependent with no trichotomy claimed,
because B7-6 did not fail. This document's own rule for what to do when two grids
disagree stands as this document's registered rule; only the citation is
corrected, and no disposition of this stage is changed here.

**And there is an upgrade available, not taken here.** When two grids disagree,
B7-11's carry computation answers whether the disagreeing grid could carry the
direction **at all**, deterministically and without a null. That turns
"grid-dependent, nothing claimed" from a terminal state into a measurable
question. Whether this stage adopts it is this stage's decision and is not taken
in a correction note.



---

## 4. The noise floor, which the data supplies

`√N` is the median bid-ask spread at the close, published under Rule 6c-11, plus
the closing-auction imprecision. **`λ` is reported as `λ / √N`**, which is
`b3_cip_slice.md` §11.1's shape, so that a reader who distrusts the level still has
the comparison.

**This is not optional.** §5's third false zero is exactly a `λ` that sits below
`√N`, and without `√N` there is no way to tell that from a real zero.

---

## 5. The three false zeros, each with its guard

A zero is only informative if all three are cleared. **Any one of them unclear and
the zero is filed as uninformative**, in the same class as A3-3's machine-precision
identity.

| # | false zero | why it happens | guard, fixed here |
|---|---|---|---|
| **F1** | **path degeneracy** | if only one route exists, there is no cycle and the sum is zero for want of a comparison, not because the field is exact. This is the out-and-back that sums to zero by antisymmetry | **both routes must be verified traversable in the window.** For B9-A: creation or redemption activity must be non-zero in the fund-day's neighbourhood, inferred from the shares-outstanding path. Fund-days with no primary activity in ±5 days are reported separately and **do not enter the zero** |
| **F2** | **state coarseness** | condition on enough and everything is explained by state, `π → 0` mechanically | **report `π` against grid fineness**, on at least two grids, per §3. A zero on the coarse grid only is not a zero |
| **F3** | **the noise floor** | `λ` below `√N` reads as zero | **report `λ / √N`, never `λ` alone**, per §4 |

---

## 6. Pre-registered predictions

| id | statement | role |
|---|---|---|
| **B9-0** | the degenerate loop `cash → etf → cash` returns **exactly** zero, computed through the same machinery and **not short-circuited on the repeated edge** | **gate.** B3-2's rule adopted verbatim. Fails → nothing after it is read |
| **B9-A-1** | **the measured zero.** On calm fund-days for funds whose underlying trades contemporaneously, `\|λ\| / √N < 1`, with F1, F2 and F3 all cleared | **the load-bearing half.** See §1.1 |
| **B9-A-2** | **the gradient.** On the same funds, `\|λ\| / √N` rises with a pre-specified stress measure | the substantive half |
| **B9-A-3** | the closing leg is AP-only, so the non-AP faces `λ` as an unrecoverable wedge | **reported, not estimated.** An institutional fact, `H⁰` |
| **B9-A-4** | `π` computed over fund-days is non-zero on the stress subsample and indistinguishable from zero on the calm one, **on both grids** | the `π` calibration proper |
| **B9-B-1** | availability: trade-level data with size, without a dissemination cap that is correlated with size | **gate for B9-B.** Fails → B9-B does not run and B9 reports A only |
| **B9-B-2** | `π` rises monotonically in order size over ADV, within instrument | `PROJECT_PLAN.md` §22.12 |

**The stress measure is fixed here, before retrieval**, so that it is not chosen to
make B9-A-2 work: the fund's own trailing 60-day realised volatility of its NAV
return, split at its own median. **Its own distribution, not an absolute
threshold**, which is discipline 8.

**"Calm" is the complement of the same split.** No third category.

### 6.1 The confound that would otherwise eat this stage

**Stale NAV.** For a fund whose underlying trades in a non-overlapping session, the
4pm NAV is struck on closing prices that are hours old, so `premium` partly measures
genuine price discovery rather than an unclosed loop. **This is not a small effect
and it is the standard reading of international ETF premiums.**

**Fixed here:** the main arm is restricted to funds whose underlying trades
**contemporaneously** with the fund, that is US-listed funds on US-listed equities.
International and fixed-income funds are **reported beside** the main arm and are
**not** in it, and the difference between the two is itself reported, because it is
the size of the confound measured rather than assumed.

---

## 7. Filters, fixed here

US-listed, Rule 6c-11 funds, primary listing only. Fund-days are dropped pairwise
and **the dropped count is reported per arm**, which is `b3_cip_slice.md` §7's rule:
silence about a dropped record is how a sample becomes a selection. Funds are
dropped if the creation fee is not disclosed as a determinate number, and that count
is reported separately from funds dropped for missing price or NAV, because an
undisclosed term and a missing observation are different objects.

Leveraged, inverse and single-stock funds are excluded, declared here rather than
after seeing them.

---

## 8. Falsification

- **B9-0 returns non-zero** → the `ω` construction is broken. Stage stops. Nothing
  from it is quotable, including numbers already computed.
- **B9-A-1 fails, that is `\|λ\|/√N ≥ 1` even on calm days with all three guards
  cleared** → `π` has no measured zero on this carrier. **Report it.** The stage does
  not move to a calmer subsample to find one. `PROJECT_PLAN.md` §22.9's first killing
  condition is then live and the cross-domain programme is in question, not just this
  stage.
- **B9-A-1 passes but only because F1, F2 or F3 is unclear** → filed as
  **uninformative**, not as a pass. Same class as A3-3.
- **B9-A-2 fails, the gradient is flat** → the loop sum does not track arbitrage
  capacity. That contradicts B3's own reading of the same channel and is a real
  finding about one of the two, reported as such.
- **B9-A-1 and B9-A-2 both pass but the difference is entirely explained by the
  international/fixed-income comparison in §6.1** → the reading is a stale-NAV
  reading, and it is reported as one.
- **B9-B-1 fails** → B9-B does not run. **This is not a failure of B9** and must not
  be written as one.

All six are mapped before retrieval. An outcome not on this list is filed as
**mixed** and the criteria are not rewritten afterwards.

---

## 9. What this stage cannot establish

**ETF premiums are not a discovery.** They are published under Rule 6c-11, and
there is a literature on their behaviour in fixed income and in stress. **Nothing
here claims the quantity is new.** What is claimed is that it is the same object
Theorem 2 names, computed in the same statistic as B3 and B8, with the closing leg's
availability recorded as a hole rather than as a cost.

**It is not a profit.** APs do close this loop and are compensated for doing so. The
claim is that the loop is **not closed for everyone**, which is the two-index
structure, not an inefficiency.

**It says nothing about Volume I.** Like B3, this carrier's content is arbitrage
capacity and access, not who the borrower is. **B8 remains the only registered
carrier that reaches slice with agent stratification.**

**A zero here does not establish a zero anywhere else.** It establishes that the
statistic **can** return zero on real data, which is what every other reading needs
and does not currently have.

**B9-B, if it runs, does not settle the size channel in general.** One instrument
family is one instrument family.

---

## 10. Order of execution

1. **Availability check, and it may terminate B9-B before any design work on it.**
   Confirm for a small sample of funds: daily NAV, daily close, shares outstanding,
   median bid-ask spread, and a determinate creation fee are all retrievable without
   a terminal. Report per field, per fund. **Write the result down whichever way it
   comes out.**
2. Write the `ω` construction for all three edges in full before touching data.
   §2's loop is stated in logs; the inclusive definition of each edge is not yet
   written and that is where a stage like this goes wrong.
3. B9-0. Then the F1 traversability audit, which defines the sample the zero is
   computed on.
4. B9-A-1, then B9-A-2, then B9-A-4, each on both grids, with §6.1's comparison arm
   run beside them.
5. B9-B-1. If it passes, B9-B-2. If it fails, stop and report.

---

## 11. Status

Nothing retrieved. No code. `π` has never been computed on anything. §6's stress
measure and §6.1's restriction are fixed as of this document and **may not be moved
after retrieval**.

---

# 12. Restructuring after B7's withdrawal

**Written 2026-08-16.** §3 already carries the withdrawal note. This section is what
follows for **this stage's design**, and the exposure here is worse than B8's for a
reason worth stating first.

**Rules N1, N2 and N3 are stated in full in [`b8_fannie_slice.md`](b8_fannie_slice.md)
§15.1 and are adopted here without re-argument.** N1: a null belongs to the design
that drew it. N2: a cross-class second-moment estimator reads shared structure only.
N3: the binding quantity is observations per cell in the sparsest class.

## 12.1 This stage is maximally exposed to N1, because its headline is a zero

B7's threshold was drawn on the wrong design and sat **too high**, which made rank
`0` easier to reach. **B9-A-1's finding is `|λ| / √N < 1`.** A `√N` estimated on a
larger or different sample than the one `λ` is computed on, or estimated too
generously, makes the zero cheap in exactly the same way, and this stage's whole
claim in §1.1 is that the zero is the load-bearing half.

**Fixed here, and it is a change to §4.** `√N` is computed on **exactly the fund-days
that enter the zero**, after §5's F1 traversability filter has already removed the
fund-days with no primary activity within ±5 days, not before. The two figures, `√N`
on the full sample and `√N` on the F1-cleared sample, are **both reported**, and the
headline uses the second. If they differ materially, that difference is itself the
measurement of how much of the zero was the filter.

**And the guard runs the other way too.** Any subsample this stage reports on, calm
against stress in §6, one grid against another in §3, contemporaneous against
international in §6.1, **regenerates the design and gets its own `√N`.** A single
pooled floor applied across arms is the B7 defect with the sign flipped.

## 12.2 B9-B-2 is B7's shape and needs a second axis

**The problem, precisely.** `π` rising monotonically in order size over ADV is a
statistic indexed by a band, and **the largest size bands are the thinnest**. `π`'s
sampling variance rises as `n` falls, so a `π` that rises with size is exactly what
a rising noise floor would produce, and the direction of the artefact is the
direction of the prediction. This is B7's disease with the axis renamed.

**Two requirements, registered here rather than after the gradient is seen.**

- **Equal `n`.** Subsample every band to the sparsest band's `n` and recompute the
  gradient. Both figures reported. **A gradient present only at unequal `n` is a
  thinness artefact and is reported as one.**
- **Replication across instruments.** The gradient must hold **within each of at
  least two funds separately**, not only pooled. Sampling noise does not replicate
  across instruments; a size channel does. A pooled-only gradient is reported
  without the claim.

**N3's gate.** Report observations per `(band × terminal state)` cell and the
minimum over bands, before `π` is read. Floor `min_size = 20`, sourced from
`b2_measurement.md` §10 as in `b8_fannie_slice.md` §15.3. **Bands below it are
excluded and the excluded count is reported.** §3's existing instruction to report
observations per state-cell entry stands and this extends it to the band axis.

**B9-A-4 takes the same two requirements**, since calm against stress is also a
two-band comparison with unequal `n`.

## 12.3 §3's citation of B7 is amended, because it is currently too strong

§3 says **"B7 closed with no rank at any class resolution"** and cites a constructed
zero-interaction field reproducing the reading forty times out of forty.

**That demonstration is a sufficiency argument and not an exclusion.** It shows zero
interaction *can* produce the reading. It does not show interaction was absent, and
`b7_interaction_rank.md` §3.26 records the live alternative it cannot rule out:
those two thin classes may carry real cell-specific interaction, since high-DTI
lending is largely non-QM and is priced with more variation across market and year,
so a class can have large interaction and large noise together and `S` cannot
separate them. **B7-13 aims at exactly this and B7-14 has not returned.**

**The sayable version, and the one this document uses:** `S` carries no structure
shared across classes, no pair of the 171 exceeding a correlation of `0.1417`;
whether any single class carries its own cell-specific variation is inseparable from
that class's own sampling noise on this estimator. **This stage cites B7 for the
carry, the grid rule and N1 to N3. It cites no rank number and it does not cite B7
for the absence of interaction.**

## 12.4 The re-weighting, which this stage was already on the right side of

`b1_theorem.md`'s order is Corollary 1, then Corollary 2, then Theorem 3, and B7 was
the Theorem-3-shaped station.

**B9-A-1 is Corollary-1-shaped**: a single inequality, `|λ| / √N < 1`, on a pooled
statistic with a **published** noise floor rather than an estimated one. §1.1 already
made it the load-bearing half for an unrelated reason. **It stays there and its
standing rises**, because the stations that survived the B-track's worst week are the
ones decided by one comparison.

**B9-A-4 and B9-B-2 are the `π` statistics** and they move behind it, with 12.2's
requirements attached. This does not weaken the cross-domain programme:
`PROJECT_PLAN.md` §22.4 makes `π` the currency, and a currency that has never been
computed anywhere needs its first reading to be **defensible** more than it needs it
to be large.

## 12.5 What this section does not change

§2's graph, §3's definition of `π`, §5's three false zeros and their guards, §6's
stress measure and its median split, §6.1's stale-NAV restriction, §7's filters,
§8's six falsification lines, §9's four scope limits, §10's order of execution.
**B9-0 and B9-A-1 are unaffected in kind.** What changed is where `√N` is estimated,
and what a band-indexed `π` has to survive before it is quoted.
