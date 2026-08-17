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

---

# 13. The noise floor is a per-fund constant, and the main arm moves to SPDR

**Ruled 2026-08-16, before any `λ` was computed.** §4 and §12.1 stand as written;
this section governs where they disagree with it. The availability findings behind
it are in `claude-docs/B9_可得性_iShares实测_v1.md` and
`claude-docs/B9_可得性_发行人普查与SSGA_v1.md`.

## 13.1 What was measured, since the ruling rests on it

**No issuer found publishes a bid-ask spread history.** iShares carries "30 Day
Median Bid/Ask" as one number on the product page. SSGA offers no spread history
file; the figure sits in the cross-fund product-data workbook at row 1, column 19,
covering about 199 funds in one 93 KB file. **Two issuers, the same answer**, so
this is not a statement about one publisher.

**What is available at SSGA**, as static files with no session and no product id:
daily NAV and **daily shares outstanding** from 2003-12-01 (5,714 dates), and daily
premium/discount for 2025-01-02 to 2026-08-14 (405 dates), the window Rule 6c-11
requires. The closing price is not published separately and is recovered as
`P = NAV · (1 + premium)` on the overlap.

## 13.2 The ruling

**`√N` is the fund's published 30-day median bid-ask spread, taken as a per-fund
constant over the window**, plus the closing-auction imprecision §4 already names.

**What this keeps.** The floor stays **published rather than estimated**, which is
the property §12.4 used when it made B9-A-1 the load-bearing half. A floor this
stage estimated from the same series that produces `λ` would make `|λ| / √N` a
ratio of a quantity to itself, and N1 is precisely about a null drawn on the design
it is then used to judge.

**What this gives up.** §12.1 requires every subsample to regenerate its own `√N`.
That now holds **across funds and not across days**. Calm against stress (§6), grid
against grid (§3) and contemporaneous against international (§6.1) are splits along
the date axis within a fund, so those arms share a floor. **This is a real loss and
it is not to be described as anything else.**

## 13.3 What must therefore be reported

1. **The constant, per fund, with its as-of date**, printed beside every reading
   that divides by it.
2. **The cross-fund dispersion of `√N`.** That is now the only dimension in which
   the floor varies, so it carries whatever discrimination the ratio has left.
3. §12.1's two figures, `√N` on the full sample and on the F1-cleared sample,
   **collapse to one, and that is stated rather than silently dropped.** A constant
   does not move when the F1 filter removes fund-days, so the comparison §12.1 asked
   for cannot be made and its absence is the finding.
4. **A daily capture of the cross-fund workbook starts now**, so that a later run of
   this stage has the series this one lacks. Its absence over 2025-01-02 to the
   capture start is a fact about **this** run and is written into the record.

## 13.4 The failure line this ruling adds

If `|λ| / √N < 1` holds on calm days **only because the constant is larger than the
day-specific floor would have been on those days**, the zero is cheap in exactly
N1's way, and §1.1 makes the zero this stage's whole claim.

**The check that is available without the history**: the constant is a 30-day median
struck at one date, so compare it against the same fund's realised dispersion of `λ`
over its own calmest decile of days. **If the constant exceeds that dispersion by
more than an order of magnitude, the zero is filed as uninformative under §5's F3**,
not reported as a pass. Registered here, before the constant is read.

## 13.5 The main arm moves to SPDR, and that is a selection

The registered fund table put three of seven main-arm funds at iShares. Retrieval
works at SSGA and does not at iShares, so the main arm moves to the Select Sector
SPDR family: open-end, US-listed, on US-listed equities, inside §6.1's definition.
SPY stays in neither arm, as a unit investment trust predating Rule 6c-11.

> **Declared**: this move is selected on the issuer's publishing practice and on
> nothing that touches `λ`. It is written here because it is a choice made **after**
> looking at what could be retrieved, and §7's rule is that a filter is declared
> rather than discovered.

## 13.6 What this section does not change

§2's graph, §3's `π` and its grid rule, §5's three false zeros and their guards,
§6's stress measure and its median split, §6.1's stale-NAV restriction, §8's
falsification lines, §10's order of execution, §12.2's equal-`n` and
replication-across-instruments requirements. **B9-0 and B9-A-1 are unchanged in
kind.** What changed is that `√N` is constant along the date axis, and which funds
the main arm holds.

---

# 14. The `ω` construction, all three edges, written before the data is touched

**§10 step 2, executed 2026-08-16, after step 1 and before any file is parsed.**
Step 2's own warning is that §2 states the loop in logs while "the inclusive
definition of each edge is not yet written and that is where a stage like this
goes wrong." This section is that definition. **No file has been read into a
program at the time of writing; the column names below come from §13.1's
availability pass, which read headers and nothing else.**

## 14.1 The cochain

`ω` is a 1-cochain on the position graph of §2, valued in log points of the
numeraire. For a directed edge `e` traversed on trading date `t`:

```
ω_t(e)  =  log( value in the numeraire arriving at the head of e )
         −  log( value in the numeraire leaving the tail of e )
```

**Antisymmetry is imposed by construction and is not an assumption about the
world**: `ω_t(e_reversed) ≡ −ω_t(e)`, computed by the same function from the same
inputs. This is what makes B9-0 a test of the machinery rather than a tautology:
the degenerate loop `cash → etf → cash` must return **exactly** zero through the
same code path, with the reversed edge built by that function and summed, **not
short-circuited on the repeated edge** (§6's B9-0, B3-2's rule).

## 14.2 The three edges, inclusively

All three legs are struck at **the same date `t`**, at that date's close. `NAV_t` is
the fund's published net asset value per share; `P_t` is the listing exchange's
official closing price; `f` is the published creation transaction fee per creation
unit, expressed as a fraction of the unit's value.

| edge | inclusive definition | `ω_t` |
|---|---|---|
| `cash → basket` | acquire the fund's published creation basket at the constituents' closing prices; by definition of NAV that costs `NAV_t` per fund-share-equivalent | **`0`** |
| `basket → etf` | deliver one creation unit and receive shares, paying the disclosed transaction fee `f` | **`−log(1 + f)`** |
| `etf → cash` | sell at the closing price `P_t` | **`log(P_t / NAV_t) = log(1 + premium_t)`** |

Summing the cycle `cash → basket → etf → cash`:

```
λ_t  =  0  −  log(1 + f)  +  log(1 + premium_t)  =  log(1 + premium_t) − log(1 + f)
```

which is §2's expression, now with each term's provenance fixed.

## 14.3 What is excluded from `ω`, and why each exclusion is a claim

**Excluded, and the exclusion is the substantive part of this section.**

1. **The bid-ask half-spread.** It is `√N` (§4, §13.2). Putting it inside `ω` as
   well would shrink `λ` and inflate the floor **in the same direction**, which
   makes `|λ| / √N < 1` easier to reach twice over. **Counted once, as the floor,
   never as a cost.**
2. **Brokerage commission.** Declared zero. On the cycle it cancels only if it is
   identical on the direct and the indirect leg, which it is not for a non-AP.
   **The exclusion is therefore a claim and not an accounting convenience**: it
   says the loop is measured gross of the traverser's own execution costs, so `λ`
   is a property of the terms on offer rather than of who is trading.
3. **Taxes, financing and borrow.** Out of scope for a same-day cycle in a single
   numeraire, declared rather than assumed away silently.

## 14.4 The one place this construction can be wrong, named

**`ω(cash → basket) = 0` is an identification assumption, not an identity.** It
holds if the published creation basket is worth `NAV_t` per share-equivalent at
the same closing prices used to strike NAV. It fails to the extent that the
creation basket carries **cash-in-lieu** for constituents the fund does not deliver
in kind, or is a sampled rather than pro-rata slice of the portfolio.

**Registered consequence**: if `λ` is non-zero on calm days, cash-in-lieu is a live
alternative to an unclosed loop, and this stage **cannot separate them from the
files it has**. §8's line for a non-zero at the calm end therefore gains one more
reading, and the honest report names all of them. The comparison arm of §6.1
bears on this: cash-in-lieu is heaviest in the international and fixed-income
funds, so a `λ` that is flat across the main arm and large in the comparison arm
is evidence about cash-in-lieu, not about arbitrage capacity.

## 14.5 The join, fixed before it is run

Two tables, two date columns, and they do not end on the same day: §13.1 measured
`navhist` to 2026-08-13 and `pdhist` to 2026-08-14.

> **`λ_t` is computed only on dates present in both tables for that fund.**
> The intersection is taken per fund, and **the count dropped from each side is
> reported per fund**, which is §7's rule that silence about a dropped record is
> how a sample becomes a selection.

**Dates are text** in these workbooks (`14-Aug-2026`), so both sides are parsed to
ISO and joined on the parsed value. **A row whose date fails to parse is counted
and reported, never dropped silently**, and the parse is the one in §13.1's
availability pass, already exercised on both files.

`pdhist` carries 425 rows against 405 dates; the twenty extra rows are quarterly
section headers under Rule 6c-11's tabular format. **They are identified by failing
the date parse, which is the same mechanism as the report above, so the two counts
must reconcile: rows dropped for an unparseable date equals rows that are section
furniture.** If they do not reconcile, the parser is wrong and nothing downstream
is read.

## 14.6 `f`, the one input not yet in hand

`f` is in the prospectus or the statement of additional information, as a dollar
amount per creation unit. Converting it to a fraction needs the creation unit size
and the fund's share price, both of which are in the files already retrieved.

**Until `f` is read for a fund, that fund's `λ` is not computed.** §7 already
requires that funds dropped for an indeterminate creation fee are counted
**separately** from funds dropped for a missing price, because an undisclosed term
and a missing observation are different objects. **That separation starts here.**

**Note the sign.** `f > 0` makes `λ` more negative, so a large fee cannot manufacture
a zero; it can only push `λ` away from zero. The direction is stated now so that it
is not discovered after seeing the readings.

## 14.7 What §14 does not change

§2's graph, §3's `π`, §5's three false zeros, §6's predictions and stress measure,
§6.1's restriction, §7's filters, §8's falsification lines, §10's order, §13's
ruling on `√N` and the SPDR sample. **This section only writes down what §10 step 2
requires to exist before step 3.**

---

# 15. The premium column is in percent, and what the depth pass measured

**§10 step 3's depth pass, run 2026-08-16 by `experiments/b9_omega.py --depth`,
which computed no `ω` and no `λ`.** Record: `results/b9_depth.json`, marked
`diagnostic_only`.

**Every criterion in §5, §6, §6.1, §8, §13 and §14 was registered before this run.
Nothing below moved any of them**, and this sentence is here so that a later
reader does not have to reconstruct the order from timestamps.

## 15.1 The units, settled by exclusion rather than chosen

`pdhist`'s second column is **in percent**. The conversion is applied once, at
parse:

```
premium_fraction  =  premium_column / 100
```

**The basis is an exclusion and not a preference.** Over the 405 dates, the raw
column reaches **6.25 for SPDW and 4.27 for SPEM**. Read as a fraction those are
premiums of 625% and 427%, which no exchange-traded fund exhibits and no
creation-redemption mechanism permits. Read as percent they are 6.25% and 4.27%
on a developed-ex-US and an emerging-markets fund, which is the ordinary size of
a stale-NAV premium on a volatile session.

The main arm agrees from the other side: the eleven sector funds run p01 between
`−0.049` and `−0.105` and p99 between `+0.040` and `+0.060`, that is **a typical
premium of about one basis point**. As fractions those would be 4 to 10 basis
points times a hundred, which sector SPDRs do not do.

**Registered guard, because a unit error of 100 is the failure this note exists to
prevent**: after conversion, `|premium_fraction| < 0.25` must hold. A row outside
it is **counted and reported, never clipped and never dropped silently**. The
observed maximum is `0.0625`, so the band is loose by design; it is there to catch
a future file that changes convention, not to filter this one.

## 15.2 The join, measured

| quantity | reading |
|---|---|
| `pdhist` rows, all sixteen funds | 405 dated + 20 section rows + 138 blank |
| §14.5's three-way identity | **holds for all sixteen** |
| `navhist` span | 2003-12-01 to 2026-08-13 for the funds that old; XLC from 2018-06-18, XLRE from 2015-10-07 |
| `pdhist` span | 2025-01-02 to 2026-08-14, identical across all sixteen |
| **intersection** | **404 dates, 2025-01-02 to 2026-08-13, identical across all sixteen** |
| dropped from `pdhist` | exactly 1 per fund, the 2026-08-14 row that `navhist` has not yet published |
| dropped from `navhist` | 1,646 (XLC) to 5,310 (the 2003 funds), all outside `pdhist`'s window |

**The twenty section rows are the quarterly furniture Rule 6c-11's tabular format
requires**, and they are identified by failing the date parse, which is §14.5's
registered mechanism. The identity `dated + furniture + blank = rows` is asserted
in the parser rather than checked afterwards.

**`λ` is therefore computed on 404 fund-days per fund**, and the binding constraint
is the disclosure window rather than anything this stage chose.

## 15.3 What was already visible in the raw column, declared rather than found later

§6.1's stale-NAV confound is **already legible before any `λ` is computed**: the
main arm's p99 sits near `0.05%` while SPDW and SPEM sit near `1.7%`, a factor of
about thirty. JNK and SPAB, the fixed-income pair, sit between them.

**This is recorded here because it will look like a result later.** It is not one.
It is the spread of a published column, and §6.1 already required the comparison
arm to be reported beside the main arm precisely so that this difference would be
measured rather than assumed. **What it does establish is that the comparison arm
is doing the job it was registered for.**

## 15.4 One order-of-magnitude remark, and its consequence for §13

SSGA publishes XLF's 30-day median bid-ask spread as `0.02%` and SPY's as `0.00%`.
The main arm's typical `|premium|` is about one basis point. **So `|λ| / √N` will
land near 1**, which is the boundary B9-A-1 is registered on.

This is a comparison of two already-published figures and **it is not a reading**.
Its consequence is registered: **§13's ruling that `√N` is a per-fund constant is
load-bearing rather than procedural**, and §13.4's check, comparing the constant
against the fund's realised dispersion of `λ` on its calmest decile, is the one
that decides whether a zero here is informative. That check runs whatever the
zero comes out to be.

## 15.5 What §15 does not change

Nothing. §15 records a unit, a join and an order of operations. §2's graph, §3's
`π`, §5's guards, §6's predictions, §8's falsification lines, §10's order, §13's
ruling and §14's construction all stand as written. **The next step is §10 step
3's remainder: B9-0 on real state, then the F1 traversability audit from
`navhist`'s shares-outstanding path.**

---

# 16. Three things §10 step 3 turned up: the F1 threshold, a share split, and a fee that is not per unit

**Written 2026-08-16 after `--gate` and `--f1`, before B9-A-1.** Records:
`results/b9_gate.json`, `results/b9_f1.json`.

## 16.1 B9-0 passed

**6,464 fund-days, sixteen funds, 404 dates each. Every one returned exactly
`0.0`, worst absolute deviation `0.0`, nothing skipped.** The fee was passed as
NaN so that a sum routed through the fee-bearing edge would return NaN rather
than zero. §6's gate is cleared and what follows it may be read.

## 16.2 The F1 threshold is one creation unit, and the ruling changes nothing

**Registered: `τ = 50,000` shares.** A fund-day enters the zero if the
split-adjusted change in shares outstanding exceeds `τ` on some day within five
trading days either side (§5's F1).

**`τ` is earned from behaviour, not taken from a document.** In the 404-day
window, eleven of sixteen funds show a gcd of exactly 50,000 over their non-zero
changes with **100% of changes a multiple of it**; SPDW and SPEM show 100,000,
SPAB 100,000, JNK 200,000. The five apparent exceptions are §16.3's split and
nothing else.

**And the ruling is free, which is the reportable part.** The threshold was
scanned over `0, 1, 1000, 25000, 50000, 100000, 500000, 1000000` and the cleared
count is **identical at `τ = 0` and `τ = 50,000` for every one of the sixteen
funds**. The parameter that could have been tuned until a zero appeared does not
move the sample at all until `τ` passes 500,000. **Discipline 8 asked for the
gradient rather than the level; the gradient here is flat, and that is the
finding.**

**What F1 removes.** The main arm loses nothing: all eleven sector funds clear
404 of 404 candidates. The comparison arm loses a great deal: **SPDW clears 305
of 404 and SPEM 240 of 404**, because their shares outstanding are unchanged on
87% and 88% of days in the window. XLF is unchanged on **0** of 404 days and SPY
on 2. This is F1 doing exactly what §5 registered it to do, and it means the
comparison arm's `λ` rests on a much thinner base than the main arm's, **which
must be said whenever the two are compared** (§6.1).

## 16.3 A 2-for-1 split on 2025-12-05, measured on three columns

**XLB, XLE, XLK, XLU and XLY split two-for-one on 2025-12-05.** XLK: NAV
`291.0433 → 146.6173` (ratio `0.5038`), shares `325,805,897 → 650,611,794`,
**total net assets ratio `1.0060`, that is continuous**. The third column is the
confirmation: a split moves NAV and shares in exact opposition and leaves assets
alone. XLF on the same day shows a NAV ratio of `1.0007` and continuous shares,
so it did not split, and the event is specific to those five.

**Each of the five reconciles exactly.** Dividing the post-split share count by
two and differencing against the day before leaves `−400,000`, `−350,000`,
`−500,000`, `+1,800,000` and `−2,550,000` respectively, **every one a multiple of
the 50,000 creation unit**. The split and the day's ordinary primary-market flow
separate cleanly, with no residual.

**Why it mattered.** Before adjustment these five days were the only non-multiples
of 50,000 in the whole window, and they were what dragged four funds' gcd to 25,
200, 1, 80 and 4. Read as primary-market activity they would have been creations
of 56 to 325 million shares, which is the eighth failure mode, membership error:
the quantity on that row is not what its column name says.

**Registered treatment**: the shares series is expressed in post-split units
throughout, splits are detected by the NAV ratio and confirmed by the continuity
of total net assets, and every detection is printed. **`λ` itself is unaffected**,
because the premium is a ratio and a split cancels in it.

## 16.4 The creation fee is charged per transaction, so `f` is a band and not a point

**Read from the Select Sector SPDR Trust SAI, supplement dated 2026-06-12, page
48**, via the fund's own document viewer:

> a fixed creation transaction fee of **$500** for each Fund except [XLC]; for
> [XLC] **$250**; an additional charge of up to three times the fixed fee for
> creations outside the Clearing Process, non-standard orders and cash creations,
> **for a total of up to $2,000** (XLC $1,000).

**This contradicts §14.2's phrasing and the contradiction is the substance.**
§14.2 called `f` "the published creation transaction fee per creation unit". The
SAI charges it **per transaction, regardless of how many Creation Units the
transaction contains** (the redemption section says so in those words). So `f`
expressed as a fraction of one unit's value depends on a quantity nobody
publishes: how many units were bundled into that order.

**The band, with numbers.** One creation unit of XLF at a NAV near `53.69` is
worth about `$2.68m`, so a `$500` fee on a single-unit transaction is
**`1.86` basis points**. XLF's median non-zero daily change is `4,550,000`
shares, that is `91` creation units; if a day's flow were one transaction the
same `$500` is **`0.02` basis points**. **Two orders of magnitude, and the upper
end is comparable to `√N` itself**, which SSGA publishes for XLF as `0.02%`.

**Registered treatment, and it uses §14.6's sign result rather than working
around it.** `f > 0` moves `λ` away from zero and can never manufacture a zero.
Therefore:

> **`λ` is reported as an interval, not a point.** The upper end is `λ(f = 0)`,
> which is `log(1 + premium)` and is the largest `λ` consistent with any fee. The
> lower end is `λ(f = f_max)` with `f_max` the fixed fee spread over **one**
> creation unit, which is the smallest `λ` consistent with any standard-process
> creation. **Both ends are printed for every fund-day**, and B9-A-1's
> `|λ| / √N < 1` must hold **at both ends** to count as a pass.

**If it holds at one end and not the other, that is not a pass and not a
failure**: it is filed as **fee-indeterminate** and reported with the interval,
which is a fourth outcome that §8's list did not contain and is added here rather
than after seeing the readings.

**The `$2,000` ceiling is not used.** It applies to creations outside the Clearing
Process, non-standard orders and cash creations, and this stage cannot observe
which orders those were. Using it would widen the band by a factor of four on the
strength of an assumption about unobserved order types. **Its existence is
recorded and its effect is not modelled**, which is a scope limit and is stated
in the report.

## 16.5 What is still not done

1. **The creation unit size is measured, not read.** 50,000 shares comes from the
   gcd of in-window changes. The SAI states a unit size and it has not been
   checked against that measurement. **The two agreeing would be a C0b-style
   confirmation and the check is cheap; it has not been run.**
2. The fee was read for the Select Sector SPDR Trust only. **SPDW, SPEM, SPAB and
   JNK sit in different trusts and their SAIs have not been opened**, so the
   comparison arm has no `f` and, per §14.6, no `λ`.
3. §14.4's cash-in-lieu question is untouched.

## 16.6 What §16 changes

**§14.2's definition of `f` is superseded** by §16.4 for this carrier: the fee is
per transaction and `λ` is an interval. **§8 gains a fourth outcome**,
fee-indeterminate, defined in §16.4. Everything else stands: §2's graph, §3's
`π`, §5's guards with `τ` now fixed at one creation unit, §6's predictions, §13's
`√N` ruling, §15's units.

---

# 17. The published noise floor has one basis point of resolution, and the reading is a rectangle

**Written 2026-08-16 from `--inputs`, before B9-A-1 is computed.** §13's ruling
and §16.4's interval both stand; this section says what their arithmetic actually
lands on.

## 17.1 What was read

`√N` comes from the cross-fund workbook as a **string with two decimal places in
percent**: `0.02%`, `0.01%`, `0.04%`, and for SPY `0.00%`. Across the sixteen
funds it takes **four distinct values**, `0.00`, `0.01`, `0.02`, `0.04`.

The main arm's spreads are therefore **one or two basis points, reported to a
resolution of one basis point**. A true spread of `0.0140%` prints as `0.01%` and
one of `0.0150%` prints as `0.02%`, so **two funds whose floors differ by 7% are
reported as differing by 100%**, and two whose floors differ by 100% may be
reported as identical.

## 17.2 What that does to §13.3 item 2

§13.3 item 2 required the **cross-fund dispersion of `√N`** to be reported, on the
grounds that after §13's ruling it is the only dimension in which the floor still
varies. **That dispersion is now known to be mostly quantisation.** With four
distinct values over sixteen funds and a quantum of one basis point sitting on
top of quantities of one to two basis points, the between-fund spread of `√N` is
not measuring between-fund differences in liquidity to any useful precision.

**§13's ruling is weaker than it looked when it was made**, and the weakening is
recorded here rather than discovered later. It does not reverse the ruling: the
alternatives in §13.5 were worse for reasons that have not changed. It does
change what may be claimed from the ratio's variation across funds, which is now
**nothing**, absent a finer floor.

## 17.3 The registered consequence: a rectangle, not a point

`λ` is already an interval by §16.4. `√N` is now an interval too, of width one
quantum. **The reading is therefore a rectangle and B9-A-1 is evaluated at its
worst corner.**

```
λ_hi   =  log(1 + premium)                       # f = 0
λ_lo   =  log(1 + premium) − log(1 + f_max)      # one creation unit per transaction
√N_lo  =  published − 0.005%                     # half a quantum down
√N_hi  =  published + 0.005%
```

> **B9-A-1 passes for a fund-day only if `|λ| / √N < 1` holds at the worst
> corner**, that is with the larger of `|λ_hi|` and `|λ_lo|` over `√N_lo`.
> **Passing at the best corner and failing at the worst is not a pass**; it is
> §16.4's `fee-indeterminate` outcome when the fee end is what flips it, and a
> new outcome, **`floor-indeterminate`**, when the quantum is. Both are reported
> with the rectangle printed, and neither is written as a failure.

**`√N_lo` is not allowed below zero.** For a fund published at `0.00%` the floor
is below the reporting resolution, no ratio is defined, and **the fund is
reported without a ratio rather than with an infinite one**. SPY is that fund
here, and it is in neither arm, so nothing in the main reading depends on it.

## 17.4 A prediction made now, from the inputs alone

`f_max` for one creation unit runs from `0.449` bp (XLC) to `2.389` bp (XLRE),
against published floors of one or two basis points. **For XLRE (`2.389` bp
against `0.02%`) and XLF (`1.919` bp against `0.02%`) the fee band alone is
comparable to the whole floor.**

> **Registered before the reading: several main-arm funds are expected to come
> back `fee-indeterminate`.** If they do, that is the predicted behaviour of a
> stage whose fee is published per transaction and whose floor is published to
> one basis point, and **it is not evidence about holonomy in either
> direction.**

If instead every fund passes at the worst corner, that is a stronger result than
§6 asked for, because it survives both indeterminacies at once. **Writing both
branches down now is what keeps the second one from being read as a surprise.**

## 17.5 What §17 changes

§8 gains `floor-indeterminate` beside §16.4's `fee-indeterminate`. §13.3 item 2's
claim about cross-fund dispersion is **withdrawn as uninformative at this
resolution**, and the requirement to print the figure stands so that a later run
with a finer floor can compare. Nothing else moves.

## 17.6 What would fix it, not done here

The median bid-ask spread is published to two decimals because Rule 6c-11 asks
for a website disclosure and not for a data feed. A finer floor would have to come
from **trade-level quotes**, which is §2.1's B9-B territory and is
availability-gated. **The daily capture registered in §13.3 item 4 does not help
with this**: capturing the same two-decimal figure every day builds a series of
quantised values, not a finer one. **That limitation is recorded now so the
capture is not later mistaken for a solution to it.**

---

# 18. B9-A-1's reading: uninformative, and why a finer floor would not change it

**Run 2026-08-16. Record `results/b9_a1.json`.** The first run's record is archived
as `b9_a1.json.expired_20260816_归因标反_双报`: its pass/fail/indeterminate layer
was correct and its **attribution sub-label was wrong for five funds**, because the
necessity test was written in the wrong order. Both are on disk; the archived one
is not deleted and the correction is stated rather than folded in.

## 18.1 The reading

**Main arm, eleven Select Sector SPDRs, 203 calm F1-cleared fund-days each.
Not one passes at §17.3's worst corner. Not one fails at the best corner.**

`|λ_hi| / √N` at the published floor with the fee set to zero, that is the most
favourable honest reading available:

> **median `1.027` across the eleven funds, range `0.562` to `1.683`.**

| verdict | funds | published `√N` |
|---|---|---|
| `floor_indeterminate` | XLC, XLI, XLK, XLP, XLV, XLY | all `0.01%` |
| `fee_indeterminate` | XLB, XLE, XLF, XLRE | all `0.02%` |
| `fee_and_floor_indeterminate` | XLU | `0.02%` |

**The verdict is determined by the published floor, not by the fund.** Every fund
quoted at `0.01%` fails on the floor; every fund quoted at `0.02%` fails on the
fee or on both. The worst corner divides by `published − 0.005%`, which halves the
denominator for the first group and cuts it by a quarter for the second.

**Comparison arm** (§6.1, reported beside and in no main-arm reading): JNK
`20.65`, SPDW `16.87`, SPEM `27.60`, all **fail**; SPAB `0.71`, **pass**; SPY has
no published floor (`0.00%`) and gets no ratio.

## 18.2 Disposition: uninformative, in A3-3's class, and **not** a failure

§8's killing line reads "`|λ|/√N ≥ 1` **even on calm days with all three guards
cleared**". **F3 is exactly the guard that is not cleared here**: §17 measured the
floor's resolution to be one basis point against a signal of one to two basis
points. The correct file is §8's third line, `filed as uninformative`, the same
class as A3-3's machine-precision identity.

**`PROJECT_PLAN.md` §22.9's first killing condition is therefore not live.** The
cross-domain programme is not in question on this evidence.

**And §1.1's job one is not done.** The repository still has no real-data zero, and
this carrier cannot supply one. §18.3 says why that is not a matter of trying
harder.

## 18.3 The floor is the mechanism, not the instrument

§4 treats `√N` as the instrument's noise floor. **On an efficiently arbitraged
carrier it is not.** The premium is held inside the band that arbitrage can
profitably close, and the dominant term in that band is the bid-ask spread
itself. So `|λ| ≈ √N` is **the equilibrium**, not a measurement failure, and the
test `|λ|/√N < 1` reduces to asking whether the premium sits inside the
no-arbitrage band, whose answer is "at its edge, by construction of the market".

**The operative consequence, registered so that money is not spent on it**: a
finer floor from trade-level quotes would turn a noisy `≈ 1` into a precise
`≈ 1.03`. **It buys resolution, not a zero.** TAQ, WRDS or any paid quote source
must not be acquired for the purpose of rescuing B9-A-1, and §2.1's B9-B gate is
not an answer to this.

It also retires §13.5's alternatives for good: estimating the floor from `pdhist`
itself would have produced a ratio near 1 **by construction**, and waiting to
accumulate spread snapshots accumulates the same quantised figure.

## 18.4 §12.4's re-weighting is reversed, by the standard §12.4 itself set

§12.4 moved B9-A-1 to the load-bearing position and moved `π` behind it, on the
stated ground that A-1 rests on "a **published** noise floor rather than an
estimated one".

**That ground has now been measured and it does not hold at this scale.** A floor
published to one basis point, standing against a signal of one to two basis
points, confers no advantage over an estimated one; §18.1's verdicts are decided
by its rounding.

> **Reversed: `π` (B9-A-4) returns to the load-bearing position for this stage,
> and B9-A-1 is demoted to what it turned out to be, a measurement of where the
> free-data resolution limit falls.**

`π`'s claim to that position is §3's first property, which is the one thing A-1
lacked: **under exactness `π ≡ 0`, hard, with no floor to calibrate against.**

## 18.5 What this run does not touch

1. **B9-0 passed**, 6,464 fund-days at exactly zero. The machinery is sound.
2. **B9-A-3 is unaffected.** The AP-only creation leg is `H⁰` and is reported
   rather than estimated. **`λ` measures the curl, `H¹`.** This run says the curl
   is arbitraged flat on this carrier and says **nothing whatever about the
   hole**, and the two must not be conflated in the write-up.
3. **The statistic's dynamic range is now measured, and it is wide.** The
   comparison arm reads 17 to 28 against the main arm's 1. `|λ|/√N` resolves ten
   to thirty basis points cleanly. What it cannot do is separate one basis point
   from a one-basis-point floor. **That is a measured range, not a defect**, and
   it is what makes B9-A-2 worth running.

## 18.6 B9-A-2 registered, including the trap that would fake it

**`√N` is a per-fund constant (§13.2), so it cancels in a within-fund comparison
of calm against stress.** §13.2 recorded that constancy as a loss, and for a
level test it was. For a gradient test it is not: **B9-A-2 is immune to §17's
quantum**, because the same constant sits on both sides.

**The trap, written before the run.** `f_max = fee / (creation unit × NAV)`, and
**NAV falls in stress**, so `f_max` rises mechanically exactly when the prediction
says `|λ|/√N` should rise. `λ_lo` therefore carries a stress-correlated component
that `λ_hi` does not.

> **Registered: both ends are reported, and the gradient counts as clean only if
> it holds at the `f = 0` end.** A rise visible only at the `f_max` end is the
> fee's mechanical response to a falling NAV and is reported as that.

**Aggregation, fixed here.** Per fund, the median of `|λ|/√N` on stress days
against the median on calm days, both ends. **Eleven funds give eleven
directions**; the count of funds showing a rise is reported beside the per-fund
ratio of medians. The comparison arm is reported beside and enters no main-arm
count.

**§8's line stands**: a flat gradient contradicts B3's own reading of the same
channel and is a real finding about one of the two, reported as such.

## 18.7 What §18 changes

§12.4's ordering is reversed (§18.4). B9-A-1 is filed **uninformative** and its
reading is §18.1. B9-A-2 gains the fee trap and the aggregation rule of §18.6.
Nothing else moves: §2's graph, §3's `π`, §5's guards, §6's predictions, §13's
`√N` ruling, §14's construction, §15's units, §16's `τ` and interval, §17's
rectangle.

---

# 19. B9-A-2's reading, the trap firing, and a hole in the prediction as written

**Run 2026-08-16. Record `results/b9_a2.json`.**

## 19.1 The reading

**Main arm, eleven funds, 203 calm against 201 stress fund-days each, at the
`f = 0` end (§18.6's clean end):**

> **nine of eleven funds rise. The median stress-to-calm ratio is `1.211`**,
> range `0.881` to `1.365`. The two that fall are **XLB `0.945`** and
> **XLV `0.881`**.

`|λ|` on stress days runs about a fifth higher than on calm days, per fund,
measured against each fund's own median volatility.

**Comparison arm** (§6.1, beside): SPDW `1.099`, JNK `1.175`, SPAB `1.020` rise;
**SPEM `0.920`** falls. Three of four, and the magnitudes are smaller than the
main arm's despite those funds' `|λ|` levels being ten to thirty times larger.

## 19.2 §18.6's trap fired, on a named fund

**XLB falls at the `f = 0` end (`0.945`) and rises at the `f_max` end
(`1.154`).** Its NAV mechanical factor, the ratio of median calm NAV to median
stress NAV, is **`1.70`**: the fee spread over one creation unit is seventy
percent larger on that fund's stress days for no reason connected to holonomy.
**XLP runs the other way**, rising at `f = 0` (`1.302`) and falling at `f_max`
(`0.964`).

The counts are **ten of eleven at the fee end against nine at the clean end, and
the extra fund is XLB**. §18.6 was written before this run and its rule, that the
gradient counts only at `f = 0`, is what keeps XLB out of the count. **Recorded
because a rule that never bites is a rule nobody has tested.**

## 19.3 The hole this run opened in the prediction as written

**`|λ|` is a folded quantity, so its median moves with dispersion alone.** Under a
null in which the field is exact and `λ` is mean-zero measurement noise **whose
scale rises with market volatility**, the median of `|λ|` rises with the stress
measure by arithmetic, with no holonomy anywhere.

> **B9-A-2 as specified in §6 does not discriminate against that null.** Nine of
> eleven rising is consistent with impaired arbitrage and equally consistent with
> a noise scale that tracks volatility, and this stage cannot presently tell them
> apart.

This is the same class as §14.4's cash-in-lieu: **an alternative the design
cannot separate, named rather than worked around.** It is a defect in the
prediction as written, not in the run.

## 19.4 Eleven funds are not eleven independent votes

The eleven are sectors of one market, on the same dates, cleared by the same
Authorized Participants. Their `λ` on a given day plausibly shares a market-wide
component, so a sign test over funds overstates its own evidence.

**A figure of `67/2048` under independence exists and is not a criterion**: it was
computed after seeing nine of eleven, and its independence assumption is the one
in question. **It is descriptive and is recorded as descriptive.**

**Required before the count is quoted as evidence**: the overlap of the eleven
stress-day sets, and whether the rise survives removing each day's cross-fund
mean. That is B7-11's lesson in another costume, and it has not been run.

## 19.5 Two discriminators, registered before they run

Both use data already on disk and, unlike §6's gradient, **both have a definite
prediction under the noise null**, which is what makes them discriminators rather
than more of the same.

**D1, persistence.** First-order autocorrelation of `λ` (signed, not folded), per
fund, computed separately on calm and on stress days.

- *Noise null*: measurement noise is not autocorrelated. **Predicts ≈ 0 on both
  subsamples.**
- *Impaired arbitrage*: an unclosed loop persists while capacity is impaired.
  **Predicts positive on stress, and larger than on calm.**
- Reported: both coefficients per fund, their difference, and the count of funds
  with a positive difference.

**D2, sign asymmetry.** The share of days with `premium < 0`, per fund, calm
against stress.

- *Noise null*: a mean-zero symmetric disturbance shifts dispersion, not sign.
  **Predicts no shift in the share.**
- *Impaired arbitrage*: capacity binds asymmetrically and the fund trades at a
  discount when it binds. **Predicts a shift toward discount on stress days.**
- Reported: both shares per fund and the count of funds shifting toward discount.

**Falsification, fixed here.** If D1 and D2 both come back null while §19.1's rise
stands, **the rise is filed as dispersion scaling and B9-A-2 is reported as not
discriminating on this carrier.** That is a real outcome and it is not a failure
of the framework; it is a measurement of what this prediction can and cannot
separate.

**If D1 or D2 is positive**, the rise is evidence about arbitrage capacity and is
reported with the discriminator that carried it named, **never with the count of
nine alone.**

## 19.6 What §19 changes

B9-A-2's status is **direction confirmed at the `f = 0` end, not yet separated
from dispersion scaling** (§19.3). §8 gains that as an outcome beside its existing
lines. D1 and D2 are registered by §19.5. §19.4's independence check is required
before the nine-of-eleven count is quoted as evidence. Nothing else moves.

---

# 20. D1 and D2: the noise null is rejected on levels, not on counts

**Run 2026-08-16. Record `results/b9_disc.json`.** §19.5 registered both
discriminators and their predictions before this run.

## 20.1 The readings

**D1, persistence of signed `λ`, main arm:**

| | median across the eleven | funds with stress above calm |
|---|---|---|
| calm days | **`+0.076`** | |
| stress days | **`+0.121`** | **10 of 11** (XLK the exception, `−0.103`) |

**D2, share of days at a discount, main arm:**

| | median across the eleven | funds shifting toward discount |
|---|---|---|
| calm days | **`0.453`** | |
| stress days | **`0.508`** | **10 of 11** (XLB the exception, `−0.0005`) |

Largest shifts: XLU `+0.158`, XLF `+0.143`, XLRE `+0.108`, XLK `+0.090`.

**§19.4's independence check:** mean pairwise Jaccard of the eleven stress-day
sets **`0.558`**; the day effect takes **`70.3%`** of pooled `λ` variance; after
removing each day's cross-fund mean, **8 of 11 funds still rise** against 9
before.

## 20.2 Why the rejection does not depend on the funds being independent

§19.5's noise null predicts **a point, not a direction**: measurement noise is
not autocorrelated, so D1 reads zero on both subsamples, and a mean-zero
symmetric disturbance does not move the discount share, so D2 reads no shift.

**Both levels are away from the point.** Calm-day autocorrelation is `+0.076`,
not zero, before any stress comparison is made; the discount share crosses from
`0.453` to `0.508`, and a symmetric disturbance cannot move a share at all.

> **A point prediction is not rescued by correlation across funds.** However
> dependent the eleven are, the null said zero and the measurement is not zero.
> **This is why the rejection is stated on levels and the counts are reported
> beside them rather than as the evidence.**

## 20.3 The internal control: the comparison arm runs the other way on D1

Stale NAV makes the premium mean-revert, because price moves first and NAV
catches up the next day, **so staleness predicts negative autocorrelation.**

**It is negative exactly where staleness is worst.** Stress-minus-calm on D1:
SPDW `−0.268`, JNK `−0.361`, SPAB `−0.101`, SPEM `−0.059`, against a main arm
that is positive in ten of eleven.

**Had the main arm's persistence been an artefact of NAV staleness, its sign
would match the comparison arm's. It is opposite.** §6.1's restriction of the
main arm to funds whose underlying trades contemporaneously is what makes this
control available, and this is the first place it has paid.

## 20.4 What the counts may be used for, and what they may not

The eleven are sectors of one market on the same days: **stress-day sets overlap
at a Jaccard of `0.558` and 70% of `λ`'s variance is a single daily common
component.**

> **Registered phrasing: "ten of eleven" is one market-wide pattern seen
> consistently across eleven sectors, and it is not eleven independent
> confirmations.** The count is reported as consistency, never as a sample size,
> and no test treating the eleven as independent draws may be quoted.

The gradient's survival of within-day demeaning, **8 of 11 against 9**, says the
rise is not purely the common component. It does not say the remainder is large.

## 20.5 Two things not done, and why one of them must not be

**D1b, registered here and not yet run.** D1 was computed on the raw series only.
On the within-day residual it asks a different and worth-asking question:
**does each fund carry persistence of its own, beyond the market-wide one?**
Registered as D1b with the same two predictions as D1.

**D2 must not be demeaned, and this is not an omission.** If every fund moves to
a discount together under stress, **that is what a market-wide capacity
constraint looks like**, and removing the daily cross-fund mean would subtract
precisely the object being measured. **The common part is the finding, not the
nuisance.**

## 20.6 Disposition

**§19.5's falsification branch is not taken.** D1 and D2 are both away from the
noise null's point prediction, so §19.1's rise is **not** filed as dispersion
scaling.

> **B9-A-2's gradient is evidence about arbitrage capacity, and it is reported
> with D1 and D2 named as what carries it.** The count of nine, or of ten, may
> not be quoted on its own (§20.4).

**What is still not established.** That `λ` is non-zero on this carrier in the
sense §1.1 wanted remains open: B9-A-1 is uninformative at this floor resolution
(§18.2) and nothing here changes that. **What D1 and D2 establish is about the
structure of `λ` over time and sign, not about its level against a floor.**

## 20.7 What §20 changes

§19.5's falsification branch is closed as not taken. D1b is registered (§20.5).
§20.4's phrasing rule binds every later write-up of these counts. Nothing else
moves.

---

# 21. D1b: the persistence is fund-specific in calm and market-wide in stress

**Run 2026-08-16, registered in §20.5 before it ran. Record `results/b9_disc.json`.**
203 calm and 200 stress lag-one pairs per fund, **no pair skipped for a gap**.

## 21.1 The decomposition

| | calm, median | stress, median | funds rising |
|---|---|---|---|
| **D1**, raw `λ` | `+0.076` | `+0.121` | **10 of 11** |
| **D1b**, within-day residual | **`+0.088`** | **`−0.009`** | **3 of 11** |

**Positive on calm days after demeaning: 10 of 11** (XLY the exception, `−0.116`).

Two statements, and they point in different directions:

1. **Each fund's own loop persists in calm.** Removing the market-wide daily mean
   does not remove the persistence; the residual's calm autocorrelation
   (`+0.088`) is **larger** than the raw series' (`+0.076`). **`λ` is not white
   noise at the fund level**, independently of any common factor.
2. **The stress amplification is market-wide, not fund-specific.** On the
   residual it is gone: the median falls to `−0.009` and only three of eleven
   rise. §20.1's raw ten-of-eleven is the **common** component becoming more
   persistent under stress.

**§20.4's phrasing rule was written before this ran and it holds**: the raw count
was one market-wide pattern, and D1b is what shows it.

## 21.2 What this settles and what it does not

**Settled: the noise null of §19.3 is rejected at the fund level.** A mean-zero
white disturbance has zero autocorrelation in every decomposition. Ten of eleven
funds show positive idiosyncratic persistence on calm days, before any stress
comparison, and D2's discount shift (§20.1) is a movement a symmetric
disturbance cannot produce at all.

**Not settled: why the idiosyncratic persistence vanishes under stress.** Two
readings, and this run separates neither.

- **A capacity constraint that binds commonly.** When Authorized Participant
  balance sheet or dealer inventory binds, it binds across funds at once, so the
  common part dominates and persists while fund-specific differences shrink. This
  is the reading §20.3's comparison-arm control supports.
- **An idiosyncratic disturbance that grows under stress.** If per-fund NAV
  measurement error rises when markets move, the residual becomes whiter and its
  autocorrelation falls toward zero for reasons that have nothing to do with
  arbitrage.

> **Registered: this stage does not distinguish them, and the write-up says so.**
> The observation is that stress makes `λ` a more common and more persistent
> object and a less fund-specific one. **Which of the two mechanisms produces
> that is open.**

## 21.3 The state of B9-A after this run

| | |
|---|---|
| **B9-0** | passed, 6,464 fund-days at exactly zero (§16.1) |
| **B9-A-1** | **uninformative** at the free-data floor resolution (§18.2). Not a failure; §22.9's killing condition is not live |
| **B9-A-2** | the gradient is real and is **not** dispersion scaling (§20.6), carried by D1 and D2, and the stress part of it is **one market-wide event** (§21.1) |
| **B9-A-3** | untouched. `H⁰`, reported not estimated |
| **B9-A-4** (`π`) | load-bearing after §18.4's reversal, **not started**, construction not yet registered |

**What §1.1 asked for is still missing.** No real-data zero has been produced,
and §18.3 says this carrier cannot produce one. **That is now B9-A-4's problem
rather than B9-A-1's**, and `π`'s null is hard precisely where A-1's was not.

## 21.4 What §21 changes

D1b's reading is §21.1 and its two-mechanism ambiguity is §21.2, registered as
unseparated. §20.6's disposition stands and is sharpened: the gradient's stress
component is market-wide. Nothing else moves. **The next registered work is
B9-A-4's construction**, which §12.4's reversal put at the front and which has no
section yet.

---

# 22. B9-A-4's construction, and why `π` is degenerate on a two-route carrier

**Written 2026-08-16 after §18.4 moved `π` to the load-bearing position. Derived
before any `π` was computed; §22.4 registers the numerical check of the
derivation itself.**

## 22.1 The construction, stated

§3 defines `π = Var(ω_k | s_k) / Var(ω_k)` over traversals `k` with terminal
states `s_k`. On this carrier:

- **traversals**: the two routes from `cash` to the `etf` position, per fund-day.
  From §14.2, the accumulated `ω` along each is

```
route 1, secondary:    a₁ = −log(1 + premium)
route 2, creation:     a₂ = −log(1 + f)
a₂ − a₁ = λ                                    (§14.2, unchanged)
```

- **terminal state**: `(fund, date)` at the finest grid, `(fund, month)` and
  `(sector-group, date)` as the coarsenings §3 requires.

**Under exactness the two routes cost the same, within-cell variance is zero and
`π = 0`.** The null is hard and needs no floor, which is why §18.4 moved it in
front of B9-A-1.

## 22.2 The arithmetic, worked before running it

With exactly two traversals per cell, the within-cell deviations are `∓λ/2` and
the cell mean is `m = −(log(1+premium) + log(1+f)) / 2`. Within and between are
orthogonal, so

```
π  =  E[λ²/4]  /  ( Var(m) + E[λ²/4] )
```

Write `V = Var(premium)`, `d = E[premium] − f`, and take `f` as near-constant
within a fund, which §16.4 measured it to be. To first order
`m ≈ −(premium + f)/2`, so `Var(m) ≈ V/4`, and `E[λ²] ≈ V + d²`. Then

```
π  ≈  (V + d²) / (2V + d²)
```

> **With `f = 0` and a centred premium this is `π = 1/2`, exactly, for every
> value of `V`.** The premium's size cancels. A fund whose premium is one basis
> point and a fund whose premium is one hundred basis points return the same `π`.

## 22.3 What that means, and it is not a coding problem

**The null stays hard and becomes useless.** `π = 0` still holds if and only if
`λ ≡ 0` identically. But **any** disturbance at all puts `π` at one half, and the
statistic's magnitude carries no information about how far the carrier sits from
exactness. On real data nothing sits exactly on the null, so a hard null with no
gradient beside it decides nothing.

**The cause is structural, not numerical.** The premium drives the within-cell
spread and the between-cell spread **through the same term**, because the cell
mean contains the premium as surely as the cell's deviations do. That happens
whenever a cell holds exactly two traversals whose difference is the whole
quantity of interest.

**And that is forced by the graph.** §2's position graph has three vertices and
`b₁(G) = 1`: the path space to any endpoint is one-dimensional, so two routes
exhaust it. **A richer traversal set does not exist on this carrier to be
chosen.**

> **Registered consequence: `π` is not informative on B9-A, and B9-A-4 as
> specified in §6 cannot deliver what §18.4 moved it forward to deliver.** This
> is a third disposition beside pass and fail: **not constructible**, and it is a
> property of the carrier's topology rather than of the data.

## 22.4 The check that this section owes, which tests the derivation and not the framework

**`π` will be computed anyway, once, on both grids.**

> **Registered prediction: `π` lands near `(V + d²) / (2V + d²)`, that is near
> `0.5` at the `f = 0` end and above it at the `f = f_max` end, for every fund
> and on every grid.**
>
> **A reading near the predicted value confirms §22.2's arithmetic and nothing
> about holonomy. A reading far from it means the derivation is wrong**, and then
> §22.3's disposition is withdrawn and the construction is reopened.

This is an instrument check in B10 §12.7's sense, run on real data because the
prediction is about the estimator rather than about the world.

## 22.5 What this does to §18.4's reversal

§18.4 reversed §12.4 and moved `π` in front of B9-A-1 because `π`'s null needs no
floor. **That reasoning survives; what fails is the assumption that B9-A could
supply `π`'s first reading.**

- **`π` remains `PROJECT_PLAN.md` §22.4's cross-domain currency.** Nothing here
  touches its definition or its role.
- **B9-A cannot calibrate it.** A carrier whose path space is one-dimensional
  cannot separate the within-cell and between-cell terms.
- **The calibration has to come from a carrier with a genuinely multi-dimensional
  path space.** B8 is the registered one: §6 of `b8_fannie_slice.md` puts two
  materially different realised routes to the same servicing state, with many
  loans per cell, which is the setting §3's decomposition was written for.

**This is worth stating in `PROJECT_PLAN.md` §22 as well**, because it is a
condition on which carriers can carry the currency at all: **`π`'s magnitude is
informative only where the between-cell variation is driven by something other
than the quantity that drives the within-cell variation.** On a two-route carrier
they are the same quantity. That condition was not in §22.4 and it belongs there.

## 22.6 The one alternative, registered and not adopted

The traversal set could be enlarged by making paths **multi-day**: enter on day
`t` by either route, exit on day `t'`, so that traversals to the same terminal
state differ by entry date as well as by route. `b1_setup.md` §3's canonical loop
has that shape.

**Not adopted here, for a stated reason**: the accumulated `ω` over a holding
period contains the fund's own price path, and separating that from holonomy
needs an argument this section does not have. **Registering it as unexplored is
the honest position**; adopting it to rescue `π` would be choosing a construction
because it gives the wanted shape.

## 22.7 What §22 changes

B9-A-4 is filed **not constructible on this carrier** (§22.3), subject to §22.4's
check of the derivation. §18.4's reversal stands as reasoning and is void as a
work plan for this stage. **B9-A has no remaining registered prediction that this
carrier can decide**: A-1 is uninformative, A-2 is read and reported, A-3 is an
institutional fact, A-4 is not constructible, and B9-B is availability-gated.
**That is the honest end state of B9-A on free data, and §23 should say what
follows for the programme rather than for this stage.**

---

# 23. The derivation checked, what `π` became here, and what B9-A delivered

**Run 2026-08-16. Record `results/b9_pi_check.json`.**

## 23.1 §22.4's check passed, to four decimal places

**Largest gap between the computed `π` and §22.2's closed form: `0.0004`.** All
eleven main-arm funds read `0.0000` at both ends. §22.2's arithmetic is confirmed
and **§22.3's disposition stands: `π` is not constructible informatively on this
carrier.**

At the `f = 0` end the main arm reads `0.5000` to `0.5066`. **SPAB reads `0.6181`
and JNK `0.5844`**, and the closed form reproduces both exactly, because those
two carry a mean premium large relative to its own dispersion, so `d²` is not
negligible.

## 23.2 What `π` degenerates into, named

```
π  =  (V + d²) / (2V + d²)        V = Var(premium),  d = E[premium] − f
```

is a **monotone reparametrisation of `d² / V`**, and nothing else. On a two-route
carrier `π` measures **the mean premium's size relative to its own dispersion**.

> **It carries no information about the magnitude of `λ`.** SPAB's `0.618` is
> higher than XLF's `0.500` because SPAB's premium has a steadier sign, not
> because SPAB is further from exactness.

Reading the ordering `π(SPAB) > π(XLF)` as a statement about holonomy would be
the eighth failure mode again: the statistic's name is not its content on this
carrier.

## 23.3 The condition this puts on `PROJECT_PLAN.md` §22.4

`PROJECT_PLAN.md` §22.4 gives `π` three properties: a hard zero under exactness,
dimensionlessness, and existing machinery. **All three hold and they are not
sufficient.** A fourth is now measured:

> **`π`'s magnitude is informative only on a carrier where the between-cell
> variation is driven by something other than the quantity that drives the
> within-cell variation.** Equivalently: the traversal set reaching a terminal
> state must be richer than the one degree of freedom that the cycle itself
> supplies.

On `b₁(G) = 1` with two routes they are the same quantity, and `π` collapses to
§23.2. **This condition belongs in §22.4 beside the other three**, and is written
into `PROJECT_PLAN.md` §26.

## 23.4 The cross-domain ordering loses its first term

`PROJECT_PLAN.md` §22.7 pinned `π(B9) < π(B3) < π(B8) ≤ π(B10)` before any of it
ran, and §22.13 replaced B9's entry with the size-graded scan, which is B9-B and
availability-gated.

> **`π(B9-A)` is not a measurement of holonomy, so it cannot occupy the low end
> of that ordering.** The prediction is not falsified; **its first term is
> withdrawn as not measurable on this carrier**, which is a different thing and
> is recorded as such.

What remains testable of §22.7 is `π(B3) < π(B8) ≤ π(B10)`, and **B8 is the
carrier that has to supply `π`'s first honest reading**, having many loans per
cell and two materially different realised routes to the same servicing state.

## 23.5 What B9-A did deliver

Listed because a station whose headline prediction came back uninformative is
easy to file as a loss, and this one is not.

**Measurements:**

1. **B9-0 passed** on 6,464 fund-days at exactly zero. The `ω` machinery works.
2. **`λ` computed for the first time anywhere in this repository**, on 404
   fund-days for each of sixteen funds.
3. **The free-data resolution limit located**: `|λ| ≈ √N` on the main arm,
   median ratio `1.027` (§18.1).
4. **The statistic's dynamic range measured**: 17 to 28 on the comparison arm
   against about 1 on the main arm (§18.5).
5. **§6.1's stale-NAV confound measured rather than assumed**, and it also
   supplied the D1 sign control that §20.3 used.
6. **`λ` is not white noise at the fund level**: idiosyncratic persistence
   positive in ten of eleven funds on calm days (§21.1).
7. **A discount shift under stress** in ten of eleven funds, up to 15 percentage
   points (§20.1), which a symmetric disturbance cannot produce.
8. **The stress response is market-wide, not fund-specific** (§21.1).

**Method, and these travel further than the numbers:**

9. **The floor can be the mechanism** (§18.3). On an arbitraged carrier the noise
   floor is the width of the no-arbitrage band, so `|λ|/√N ≈ 1` is the
   equilibrium and a finer floor buys resolution rather than a zero.
10. **A fee published per transaction makes `λ` an interval** (§16.4), and the
    interval's width is comparable to the floor.
11. **`π` needs a path space richer than the cycle** (§23.3).
12. **Seven instrument defects caught by the probes' own guards** before any of
    them reached a reading, each one of the class that turns "could not
    retrieve" into "does not exist" or the reverse.

## 23.6 What B9-A does not have

**No measured zero.** §1.1's job one is undone and this carrier cannot do it
(§18.3). **No `π`.** **No B9-B**, which is availability-gated and, after §18.3,
is not a route to rescuing A-1 either.

**B9-A is closed as a stage.** What is open is registered elsewhere: B9-B's gate,
and `π`'s calibration on B8.

---

# 24. §4 conflated the measurement floor with the arbitrage cost, and the data says which is which

**Measured 2026-08-16 from files already on disk, after §18 to §23 were written.
§18's disposition is withdrawn by §24.5. §22 and §23 are untouched: `π`'s
degeneracy is arithmetic and does not depend on any floor.**

## 24.1 The closing price is a half-cent midpoint, and the reconstruction is exact

`P = NAV · (1 + premium)` was recomputed for five funds over all 404 fund-days
and tested against the half-cent grid.

> **Every one of 2,020 reconstructed prices lands on a half cent. The share
> landing elsewhere is `0.000`.**

Half a cent is not a value a trade can print at. **`P` is the closing NBBO
midpoint**, which sits on a half cent whenever the spread is an odd number of
ticks. Two things follow at once: the premium column is computed from exactly
these two published numbers, so **this reconstruction is not an approximation**;
and **§14.3's exclusion of the half-spread from `ω` was right for a reason the
prereg did not know**, since `P` is already a midpoint and never contained it.

## 24.2 The spread's tick parity is observable per day, and it agrees with the published figure

`mid = bid + k/2` ticks, so **`k` odd puts the midpoint on a half cent and `k`
even on a whole one**. Measured share on a half cent: XLF `0.943`, XLRE `0.896`,
XLP `0.829`, XLK `0.619`, XLV `0.579`.

XLF is therefore at a one-tick spread on almost every day, that is `1.92` basis
points, against a published 30-day median of `0.02%`. XLK alternates one and two
ticks, `0.47` to `0.94` basis points, against a published `0.01%`. **The published
figure is reproduced from the tick structure**, which says the published spread is
essentially the tick and is pinned there by the minimum increment.

## 24.3 The decisive test: `|λ|` is flat in basis points across a five-fold range of tick size

Over the twelve US-listed equity funds, that is the main arm plus SPY, measured
on all sixteen with `off-grid = 0.000` everywhere:

| | SPY | XLK | XLY | XLI | XLV | XLC | XLB | XLE | XLP | XLU | XLF | XLRE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tick, bp | `0.151` | `0.468` | `0.504` | `0.653` | `0.685` | `0.899` | `1.184` | `1.212` | `1.228` | `1.287` | `1.918` | `2.389` |
| median `\|λ\|`, bp | `1.691` | `1.269` | `1.193` | `1.354` | `1.655` | `1.443` | `1.285` | `1.353` | `1.285` | `1.317` | `1.493` | `1.401` |
| `\|λ\|` ÷ half a tick | `22.4` | `5.42` | `4.74` | `4.15` | `4.84` | `3.21` | `2.17` | `2.23` | `2.09` | `2.05` | `1.56` | **`1.17`** |

**The tick spans `15.8×`. `|λ|` spans `1.42×`.** SPY carries the point on its own:
its tick is sixteen times finer than XLRE's and its `|λ|` is the same `1.7` basis
points as everything else.

**The comparison arm is excluded from this test and the exclusion is not
optional.** SPDW, SPEM and JNK carry `27.6`, `39.4` and `11.5` basis points of
premium, which §6.1 registered as stale NAV before any of this ran. Pooling them
in gives "tick spans `26.0×`, `|λ|` spans `33.0×`", **which reads as
quantisation confirmed and is an artefact of mixing a known confound into the
test.** The first `--grid` run printed exactly that pooled line; it is corrected
in the code and recorded here.

> **Quantisation noise must scale with the quantum. This does not.** The
> hypothesis that `λ` is an artefact of price discretisation is rejected, by a
> cross-fund comparison using no data beyond what was already retrieved.

## 24.4 The defect in §4, named

§4 set `√N` to "the median bid-ask spread at the close". **That quantity is a
cost, not a measurement error**, and §24.2 shows it is pinned at the minimum
increment rather than adjusting to anything.

**Two floors exist and they answer different questions.**

| floor | value | question it answers |
|---|---|---|
| **measurement**, `F_m` | the midpoint grid: half a cent, so `0.005 / NAV`; as a rounding standard deviation, `0.005 / (√12 · NAV)` | **is `λ` resolvable at all** |
| **cost**, `F_c` | the published 30-day median spread | **is `λ` arbitrageable** |

`F_c ≈ 2·F_m` in ticks and is published to one basis point; **`F_m` is exact, per
fund-day, and has no quantisation of its own.** §17's rectangle was a band around
a rounded `F_c`; **the honest object is an interval running from `F_m` to `F_c`**,
whose ends are derived rather than rounded.

**§1.1's job one is a question about `F_m`.** A "measured zero" asks whether the
statistic can return zero on real data, which is a question about resolution, not
about whether a trader could profit.

## 24.5 §18's disposition is withdrawn

Against `F_m`, `|λ| / √N` runs **`1.17` to `5.41`** across the five funds
measured, above one everywhere.

> **B9-A-1's reading against the measurement floor is a resolvable non-zero, not
> a zero and not an indeterminacy.** §18.2's file of `uninformative` was made
> against `F_c`, which §24.4 shows is the wrong floor for that question, and it
> is withdrawn.

**§18.1's numbers stand as a reading against `F_c`** and are relabelled: they say
`λ` sits inside the arbitrage cost band for the funds published at `0.02%` and
outside it for those at `0.01%`. **That is a statement about profitability and
§17's one-basis-point quantum still ruins its precision.** Both readings are kept,
against their own floors, and neither is quoted as the other.

## 24.6 Why §8's killing line is not triggered, ruled here

§8 reads: `|λ|/√N ≥ 1` on calm days with all guards cleared means `π` has no
measured zero on this carrier and `PROJECT_PLAN.md` §22.9's first killing
condition is live.

**It does not apply, and the reason predates this run.** §22.11 withdrew the
premise: the zero domain was mis-specified, because order size makes terms
agent-specific through `κ(1 − c)` and the creation gate is a hole rather than a
price. **A carrier with a hole and a published fee is not a carrier where zero is
predicted.** §22.12's replacement predicts `π → 0` only at the small-size end,
which is B9-B and has never run.

> **Ruled: a resolvable non-zero `λ` of about `1.4` basis points on a carrier
> with an AP-only leg and a `$500` fee is the revised prediction's shape, not its
> refutation.** §22.9's first killing condition stays dormant.

**The alternative reading is recorded rather than dismissed**: if a later carrier
that genuinely has no hole and no fee also returns a resolvable non-zero, that
would be §22.9's condition and this ruling would be the thing to revisit.

## 24.7 What must be re-run, and what stands

**Re-run against `F_m`**: B9-A-1's verdicts, and B9-A-2's ratios, which used `F_c`
as a per-fund constant. **A-2's direction is unaffected**, since any per-fund
constant cancels from a within-fund calm-to-stress comparison (§18.6), and `F_m`
varies with NAV so that immunity has to be re-checked rather than assumed.

**Stands unchanged**: B9-0 (§16.1), the split (§16.3), `τ` (§16.2), the units
(§15.1), the join (§15.2), D1, D1b and D2 (§20, §21), and **`π`'s degeneracy
(§22, §23), which is arithmetic and floor-free.**

**§17's `floor_indeterminate` category disappears against `F_m`**, since `F_m` has
no publication quantum. It remains defined for readings against `F_c`.

## 24.8 The lesson, stated for other stations

**A published number that looks like a noise floor may be a cost, and a cost
pinned at an institutional minimum tells you about the institution and not about
your instrument.** Before adopting any published quantity as `√N`, ask what would
happen to it if the measurement got better: **a measurement floor falls and a cost
floor does not.** The tick does not fall, and that is what gave it away.

---

# 25. B9-A-1 and B9-A-2 against the measurement floor, and B9-A's closing reading

**Run 2026-08-16. Record `results/b9_measured.json`. Floor `F_m = 0.005 / NAV`
(§24.4), exact per fund-day.**

## 25.1 B9-A-1: `λ` is resolvably non-zero

Median over calm, F1-cleared fund-days, main arm:

| | value | funds above 1 |
|---|---|---|
| `\|λ_hi\| / F_m`, that is `f = 0` | `1.05` (XLRE) to `5.08` (XLK) | **11 of 11** |
| conservative corner, `min\|λ\| / F_m` | `0.56` (XLRE) to `4.60` (XLK) | **7 of 11** |
| generous corner, `max\|λ\| / (F_m/√12)` | `7.08` to `22.85` | 11 of 11 |

> **Against the measurement floor, `λ` exceeds the resolution of the instrument
> on every main-arm fund when the fee is set to zero, and on seven of eleven at
> the near end of §16.4's fee interval.**

The comparison arm is far above: SPEM `36.2`, SPDW `20.3`, JNK `19.8`. **SPY
reads `19.3`**, which matters because SPY's tick is `0.151` basis points and its
`|λ|` is the same `1.7` as everything else (§24.3).

## 25.2 The four that fail the conservative corner fail on the fee, not on measurement

XLF `0.79`, XLP `0.98`, XLRE `0.56`, XLU `0.89`. Their median `f_max` is
`1.873`, `1.254`, `2.400` and `1.214` basis points; the seven that pass run
`0.389` to `1.135`.

**`f_max = fee / (creation unit · NAV)` and the tick as a fraction is
`0.01 / NAV`. Both scale as `1 / NAV`, so a low-priced fund is penalised twice**,
by a coarser measurement grid and by a larger per-unit fee, from the same cause.
The split is not a property of those funds' holonomy.

**Registered**: their `not_resolvable` is a statement about §16.4's unresolved
fee, and it disappears the moment the number of creation units per transaction
becomes observable. It is **not** evidence that their `λ` is small; their `f = 0`
readings are `1.48`, `1.80`, `1.05` and `1.39`.

## 25.3 B9-A-2 against `F_m`, with the mechanism measured

| | rising |
|---|---|
| floor frozen at its calm median | **9 of 11** |
| floor varying with NAV | **7 of 11** |

The frozen count reproduces §19.1's nine exactly, which it should: freezing makes
the floor a per-fund constant, the case §18.6 showed cancels.

**The three that flip are XLB, XLE and XLK, whose calm-to-stress NAV ratios are
`1.700`, `1.531` and `1.396`**, the three largest drawdowns in the arm. §24.7
registered the direction before the run: a falling NAV raises `F_m` and **lowers**
the ratio, so the varying column understates a real rise. **It does not
manufacture one**, which is the opposite of §18.6's fee trap and is why both
columns are reported.

## 25.4 What B9-A now reads

> **`λ` on this carrier is a resolvable non-zero of about `1.2` to `1.7` basis
> points, standing `1.05` to `5.08` times above the instrument's own resolution,
> flat across a `15.8×` range of tick size, persistent within fund on calm days,
> shifting toward discount under stress, and rising with stress in nine of eleven
> funds once the floor's own NAV dependence is held out.**

**This is not what §1.1 asked for and it is a definite answer rather than an
absence of one.** §1.1 wanted a measured zero so that non-zero readings elsewhere
could be trusted. **This carrier does not have one**, and now for a measured
reason rather than for want of resolution: **`λ` here is genuinely non-zero.**

**So the repository still has no real-data zero, and B9-A has settled that it
cannot come from here.** A carrier that can must have no hole and no fee, which
§22.11 already established this one does not.

## 25.5 What is withdrawn and what stands

**Withdrawn:** §18.2's `uninformative`, and with it §18.1's verdict labels as
statements about resolvability. §17's `floor_indeterminate` category, which was an
artefact of the published spread's one-basis-point rounding.

**Relabelled:** §18.1's numbers are a reading against the **cost** floor and
answer whether `λ` is arbitrageable, not whether it is measurable. Both readings
are kept, each against its own floor, and §24.4 is what separates them.

**Stands:** B9-0 (§16.1), the split (§16.3), `τ` (§16.2), the units (§15.1), the
join (§15.2), the fee interval (§16.4), D1, D1b and D2 (§20, §21), and **`π`'s
degeneracy (§22, §23)**, which is arithmetic and floor-free.

## 25.6 B9-A closes here

| | |
|---|---|
| **B9-0** | passed |
| **B9-A-1** | **resolvable non-zero** against the measurement floor; inside the cost band for the funds published at `0.02%` |
| **B9-A-2** | rises in 9 of 11 with the floor's NAV dependence held out, carried by D1 and D2, stress component market-wide |
| **B9-A-3** | untouched, `H⁰`, reported not estimated |
| **B9-A-4** | not constructible on a two-route carrier (§22, §23) |
| **B9-B** | availability-gated, and now the only place `π` could be constructed on this carrier family, since order size would add the second axis the path space lacks |

**The one thing worth carrying to `PROJECT_PLAN.md`**: §24's distinction. A
published quantity that looks like a noise floor may be a cost pinned at an
institutional minimum, and the test is whether it would fall if the measurement
improved. **That mistake cost this stage six sections and would have cost it the
result.**

---

# 26. The gate-speed test: A3 §6.4d mapped to the primary market, registered before it runs

**Written 2026-08-16. Nothing below has been computed.** This section exists
because §25's result closes "is `λ` real" and does not touch "is `λ` the
framework's". §26 is the first B9 test whose two candidate explanations **differ
in sign** rather than in magnitude.

## 26.1 What it tests, and what it must not be added to

`a3_asset_channel.md` §6.4d measured the gate closing far faster than quantity
drains: the count of nodes that can still buy runs `5.80` at round 1, `0.20` at
round 10 and **`0.00` at round 20**, while unit count does not bottom until round
80. **A3's finding is that access is a wall rather than an auction.**

Mapped to this carrier, the wall is the creation leg and the observable is
**whether the primary market moves at all** on a given fund-day.

> **This is a test about `H⁰`, the hole. `λ` is the curl, `H¹`.** §24.6 and §25.6
> already forbid conflating them, and that prohibition binds here: **§26's
> reading may not be added to B9-A-2's, and neither may be quoted as support for
> the other.**

## 26.2 The substitution, declared before it is used

A3's pressure is a balance-sheet and claims constraint. **This stage's stress
measure is the fund's own trailing realised volatility (§6), which is not that.**

> **Using volatility as a proxy for A-track pressure is a substitution, and it is
> declared here rather than assumed.** A result under it is evidence about the
> mapped statement, not about A3's own variable. **If the substitution is what
> carries the result, that is a finding about the proxy** and is reported as one.

## 26.3 Two predictions that differ in sign

| account | extensive margin under stress | why |
|---|---|---|
| **A3 §6.4d, the gate** | **share of days with no primary activity RISES** | access closes; the wall comes up |
| **ordinary flow** | **it FALLS** | volatility brings rebalancing and redemptions, so creations and redemptions happen more often |
| neither | flat | the primary market is insensitive to this measure, and A3's mapping fails on this carrier |

**This is the first B9 test where the competing account predicts the opposite
sign.** §19.3's problem, that a noise null predicted the same direction as the
framework, does not arise.

## 26.4 The statistic, fixed here

Per fund, over the in-window fund-days, split by that fund's own volatility
median (§6), on the split-adjusted share series (§16.3):

- **extensive margin**: the share of days with **zero** change in shares
  outstanding. Any change at all counts as activity; §16.2 measured every
  in-window non-zero change to be a multiple of the creation unit, so no
  threshold is needed and none is applied.
- **intensive margin**: on days that do move, the median of
  `|Δ shares| / shares outstanding`.

**Both margins are required, because A3's claim is about their contrast.** A wall
moves the extensive margin and leaves the intensive one; an auction shrinks the
intensive margin and leaves the extensive one.

## 26.5 What may be quoted

**§20.4's phrasing rule binds unchanged.** The eleven funds share days, an
issuer, and an AP set; a count over them is **one market-wide pattern seen
consistently**, never eleven independent draws. The comparison arm is reported
beside and enters no main-arm count. **SPDW and SPEM already sit at `0.87` and
`0.88` zero-change share (§16.2), so their extensive margin has little room to
rise**, and that ceiling is stated with any reading of theirs.

## 26.6 Falsification, mapped before the run

| reading | file as |
|---|---|
| extensive rises, intensive roughly flat | **A3's wall, reproduced on a real carrier** |
| extensive rises **and** intensive falls as much | gradual contraction, **not the wall**; A3's specific shape fails while its direction holds |
| intensive falls, extensive flat | **an auction**, which is what A3 §6.4d says it is not |
| extensive falls | **the flow account**, and A3's mapping to this carrier is rejected |
| neither moves | no sensitivity to this proxy; §26.2's substitution is the first suspect |

**All five are written down before the run.** An outcome not on the list is filed
as mixed and the list is not rewritten.

## 26.7 What §26 does not change

Nothing prior. §25's readings, §24's floors, §22's `π` degeneracy, §20's and
§21's discriminators all stand as written. **§26 adds one prediction with an
opposed alternative, which is the thing B9 did not have.**

---

# 27. The gate-speed reading: the flow account wins, and the carrier's hole is the wrong kind

**Run 2026-08-16. Record `results/b9_gate_speed.json`. §26 registered all five
outcomes before this.**

## 27.1 The reading

**Extensive margin, the share of fund-days with no primary-market activity,
calm → stress, main arm:**

> **It falls in ten of eleven funds.** XLRE `0.261 → 0.179`, XLC `0.069 → 0.025`,
> XLU `0.059 → 0.030`, XLI `0.059 → 0.035`, XLK `0.054 → 0.035`, XLY
> `0.084 → 0.070`, XLB `0.084 → 0.080`, XLP `0.034 → 0.030`, XLE
> `0.015 → 0.005`, XLF `0.000 → 0.000`. **Only XLV rises**, `0.020 → 0.035`.

**Intensive margin, median `|Δ shares| / shares` on days that move: it rises in
eight of eleven**, by `1.05×` to `1.27×`.

**Under stress the primary market is both more often active and moving more.**

## 27.2 Filed per §26.6, without amendment

§26.6's table assigns "extensive falls → **the flow account**, and A3's mapping to
this carrier is rejected". **That is the reading and it is filed as written.**

> **A3 §6.4d's wall does not reproduce here. Volatility brings creations and
> redemptions rather than shutting them off.**

The comparison arm splits: SPDW `+0.032` and SPEM `+0.028` rise, SPAB `−0.030`
and JNK `−0.038` fall. **The two that rise are the two whose zero-change share was
already near `0.8`**, so their extensive margin is measuring a market that is
mostly idle in both regimes, and §26.5 required that ceiling to be stated with any
reading of theirs.

## 27.3 Why, and this is worth more than the reading

**A3's gate is endogenous to prices. The AP gate is not.**

`a3_asset_channel.md` §3's gate is `claims_i ≥ γ^gate_{i,q} · P_q(0)`: **the
threshold moves with the price**, so a rally disqualifies nodes mechanically, and
§6.4d's collapse from `5.80` to `0.00` in twenty rounds is that mechanism running.

**Authorized Participant status is a contract.** It does not tighten when the
market moves. **The creation leg is a hole all the time and the same hole**, which
is exactly why §2 could call it institutional and B9-A-3 reports rather than
estimates it.

> **This carrier has an `H⁰` hole of the wrong kind for §26's test.** The test was
> well posed; the carrier does not have the object it interrogates. **That is a
> statement about the mapping, established by a prediction that could have gone
> the other way, and it is worth more than an untested assumption that the
> mapping held.**

## 27.4 What this touches and what it does not

**Untouched:** B9-A-3, the hole is real and AP-only, and nothing here says
otherwise. B9-A-2 and §25's readings, which are `H¹`; §26.1 forbade adding these
together and the prohibition did its work. `π`'s degeneracy (§22, §23). §24's
floors.

**Touched:** any claim that B9 demonstrates A3's gate dynamics on real data.
**There is no such claim and there was never a registered one**; §26 was the first
attempt and it failed on sign.

**§26.2's substitution is not the first suspect here.** It would be if nothing had
moved. Something moved, decisively, in the direction the competing account
predicts, and §27.3 gives a structural reason that does not depend on which
pressure variable is used.

## 27.5 What a carrier would need to test A3 §6.4d

**A gate whose threshold moves with the price.** Registered as the requirement,
not adopted as a plan:

- repo haircuts and margin requirements, which rise with volatility and with
  collateral price moves;
- accreditation and minimum-investment thresholds that scale, which
  `b1_setup.md` §5 already names as a pure hole (`SEC Reg D`);
- loan-to-value limits, which is A3's own `γ^gate` in its native setting and is
  where B8 lives.

**A contractual membership is a hole that does not breathe. A collateral
threshold is a hole that does.** §26's test needs the second kind.

## 27.6 The chain, answered straight

The chain being aimed at is `formal object → real carrier → measurable non-zero →
economic state dependence`.

| link | state |
|---|---|
| formal object | `b1_theorem.md`, unchanged |
| real carrier | ETF creation triangle, `b₁ = 1`, retrieved and joined |
| **measurable non-zero** | **established** (§25): `1.2` to `1.7` basis points, `1.05` to `5.08` times the instrument's resolution, flat across a `15.8×` tick range |
| **economic state dependence** | **not yet carried by anything framework-specific** |

`λ` does move with stress (§19, §25) and the movement is not dispersion scaling
(§20, §21). **But every one of those readings is a direction that an ordinary
microstructure or capacity account predicts equally well.** §26 was the first test
with an opposed sign, and it came back on the other side.

> **So the fourth link is open, and B9 has now measured two distinct reasons why
> this carrier struggles to close it**: its gate does not breathe (§27.3), and its
> path space is one-dimensional (§22.3).

**Two registered routes remain**, neither adopted here:

1. **B9-B, the size gradient** (§22.12). `κ(1 − c)` is A3's own term and the
   framework's extra claim is that **the hole does not vanish at small size**,
   which an impact model does not say. Availability-gated.
2. **A carrier with a breathing gate** (§27.5), which is where B8 already sits.

## 27.7 What §27 changes

§26's prediction is resolved against the framework's mapping and filed. **No
criterion is rewritten.** §27.3's structural reason is registered as the
explanation, and §27.5 states what a carrier would need for the test to be
meaningful. Nothing prior moves.

---

# 28. What B8's audit connects, what it does not, and the instrument it hands over

**Written 2026-08-17 after an audit run from the B8 side. Both findings verified
against the files here; nothing in B8 or B10 was modified.**

## 28.1 The two findings, verified

**One, the transfer function on two carriers.** `b10_freddie_availability.md`
§19.2, threshold 100, undirected `b₁`:

```
Fannie    g0m 108  →  g1  9  →  g2 2  →  g3 0
Freddie   g0m 108  →  g1 10  →  g2 3  →  g3 0
```

`g0m` reads **108 on both**. The two differences of one are explained by `RA`
(§19.4). Both carriers ran the **same code**, grids and invariants imported from
`b10_support`, zero invariant violations.

**Two, LTV clears the floor unaided.** `results/b8_c9_cells.md` §2.1:
`ltv_llpa_coarse4` has minimum cell **82**, per-window **82 / 274 / 192 / 796**,
**zero loans excluded**, and its clearance **does not depend on the blank-exclusion
ruling**. Of the eleven grids C9 censused, **exactly two clear the floor without
that ruling deciding it: `ltv_llpa_coarse4` and `occupancy`.**

## 28.2 The `b₁` transfer function does not discharge §1.1, and B10 said so first

§1.1's worry is that **a non-zero holonomy reading** cannot be told from an
artefact of how states were cut. B10 §17.2 states its own limit before anyone
could misuse it:

> this is **`b₁`'s** transfer function, not holonomy's. It says there are 3.3×
> fewer independent directions on `g2`; **it does not say any holonomy reading
> differs by 3.3×.** Extrapolating it to holonomy requires measuring holonomy's
> own transfer function, **and that is not this station.**

> **So the substitution is forbidden, and the prohibition is B10's own.** Taking
> `b₁`'s sensitivity as holonomy's would be discipline 11's third family in a new
> costume.

**What B10 does hand over is stronger than a coefficient.** §17.3 and §19.3, on
both carriers: **the entire cycle space comes from `modified` and `deferred`.**
Merge those into `delinquent` and the position graph becomes a tree, `b₁ = 0`, and
the slice has nowhere to live. **That is a structural statement about the cut**,
and it is the kind of thing §1.1 needed, in a different currency from the one it
asked for.

## 28.3 What would discharge §1.1, and why B9 cannot supply it

**Holonomy's own transfer function on the same ladder.** The pieces exist and are
not joined:

| piece | where | state |
|---|---|---|
| the grid ladder, five grids, threshold ladder, invariants | `experiments/b10_support.py`, `GRIDS = (g0, g0m, g1, g2, g3)` | **importable, run on two carriers** |
| the loop residual machinery | `experiments/b8_omega.py`: `V`, `carry_forward`, `r_month`, `loop_residual_ideal` | **written, at `selftest` / `probe`** |
| the two joined | — | **not started** |

> **Registered as the item that closes §1.1: compute the loop residual on the
> same ladder `b10_support` already defines, and report how it collapses from
> `g0m` to `g3`, on both carriers, with the same code.** If holonomy's collapse
> differs from `b₁`'s, that difference is the answer §1.1 wanted; if they
> coincide, that coincidence is measured rather than assumed.

**B9 cannot run the analogue.** Three vertices, `b₁ = 1`, no grid to coarsen. This
is §22.3's degeneracy from the other side: the carrier that cannot support `π`
also cannot support a grid-fineness curve. **The item is addressed to B8 and is
not started here.**

## 28.4 LTV turns §27.5 from a requirement into an instrument

§27.5 asked for a gate whose threshold moves with the price and named `γ^gate`
with B8 as its native site. **LTV is that gate, and the price direction reverses
in a way worth stating.** A3 loses buyers when `P` **rises**, because the
threshold is `claims ≥ γ · P`. A mortgage loses access when the collateral value
**falls**, because `LTV = balance / value`. **Same structure, opposite sign on the
price, because in one case you need claims to buy and in the other you need equity
to refinance.**

**§2.4's objection does not reach §26's test.** `b7_interaction_rank.md` §2.4
requires a class index to move with the borrower, and LTV hangs on the dwelling,
which is why C9 marks it unusable for B8-4. **§26 does not want an agent class. It
wants the gate**, and a collateral threshold's correct anchor is the collateral.
**The property that disqualifies LTV as a class is the property that qualifies it
as a gate.**

**And among the two grids that clear unaided, LTV is the only one that breathes.**
`occupancy` is a fixed attribute of the loan; it is a partition, not a threshold.

**§26's two margins transfer verbatim**, with the substitution of §26.2 discharged
rather than declared, since LTV is A3's own variable and not a proxy:

| | on the ETF (§26) | on the mortgage carrier |
|---|---|---|
| extensive | did the primary market move at all | **what share of loans can still reach the `delinquent → modified` edge** |
| intensive | how big when it moved | **how much relief those that reach it get** |

**A3 §6.4d predicts the extensive margin collapses far faster than the
intensive one.** §27 found the opposite on the ETF because AP status does not
breathe. **Here the gate does.**

## 28.5 What this does to §27.6's fourth link

§27.6 recorded the fourth link, economic state dependence, as carried by nothing
framework-specific, and named two registered routes. **One of them is now
instrumented**: the grid clears the floor, the windows are populated, the variable
is A3's own, and no proxy substitution is needed.

**This does not move the link.** Nothing has been run. What changed is that
§27.5's requirement went from "a carrier would need" to "the carrier has it, and
the grid is on disk and above the floor".

## 28.6 What §28 does not change

Nothing prior. §22's and §23's `π` degeneracy, §24's floors, §25's readings, §26's
registration and §27's filing all stand. **§28 records two verified facts, one
prohibition that B10 wrote first, and two items handed to B8.**

---

# 29. B9-A-3, reported at last: the closing leg is absent to a non-AP at any price

**§6 registered B9-A-3 as "reported, not estimated" and it has been cited through
§16 to §28 without ever being written down as a reading. §29 is that reading.**
Nothing here is estimated and nothing here is new data.

## 29.1 The institutional fact, with its source

The Select Sector SPDR Trust's statement of additional information, supplement
dated 2026-06-12, read through the fund's own document viewer for §16.4's fee:

- **Creation Units are issued and redeemed only in Creation Units**, through the
  Distributor, at the next determined NAV, on an order in proper form under a
  Participant Agreement.
- An investor whose broker has not executed that agreement must go, in the SAI's
  words, "through an Authorized Participant who has executed a Participant
  Agreement" (Select Sector SPDR Trust SAI, redemption section).

**So the `basket → etf` edge of §2's graph is traversable by a member of a
contractual set and by nobody else.** §16.2 measured the unit at 50,000 shares
from the gcd of in-window changes, so the edge is also indivisible: a holder of
fewer than one Creation Unit has no partial version of it.

## 29.2 Why this is `H⁰` and not a cost, restated because it decides the filing

`b1_setup.md` §5's rule is that an edge absent **at any price** contributes to
`H⁰` rather than to the curl. **The AP requirement meets that test exactly.** It
is not a fee a non-AP could pay, not a spread they could cross, and not a size
they could reach. There is no price at which the edge appears.

**This is the reason B9-A-3 is reported rather than estimated**, and it is why
§26.1 and §27.4 forbade adding it to `λ`. `λ` is the curl; this is the hole.

## 29.3 The size of the wedge, taken from readings already made

A non-AP holding shares on a day when the fund trades away from NAV faces
`λ` and has no route that closes it.

> **From §25.1: `|λ|` runs `1.2` to `1.7` basis points on the main arm, standing
> `1.05` to `5.08` times above the instrument's own resolution.**

**That is the wedge's size, and §24 is what makes it a size rather than a
maybe.** Before §24 the number sat inside a floor that was a cost; after §24 it
stands above a floor that is a measurement quantum.

**Order of magnitude, stated plainly**: on a `$50` share the wedge is under a
cent. **The point is not that it is large. The point is that it is not zero and
there is no price at which it can be recovered**, which is what an `H⁰`
obstruction means and what a cost never does.

## 29.4 What the measured asymmetry adds, and its limit

§20.1 measured the share of days at a discount rising from `0.453` to `0.508`
under stress, in ten of eleven funds, by up to `15.8` percentage points.

**A discount is the sign of the wedge that falls on the holder.** A shareholder
at a discount holds something worth less on the exchange than in the fund, and
**cannot take it to the fund**. So the measured asymmetry says the wedge lands on
the non-AP side more often exactly when the market is under stress.

**Limit, registered**: §21.2 could not separate a commonly binding constraint
from an idiosyncratic disturbance that whitens under stress. **§29.4 inherits
that ambiguity and does not resolve it.** What is reported is the sign shift and
its size; the mechanism behind it remains as §21.2 left it.

## 29.5 What is reported and what is not observed

**Reported**: the edge exists, its membership is contractual, its unit is 50,000
shares, and the wedge a non-member faces is `1.2` to `1.7` basis points and
resolvable.

**Not observed, and not estimated anywhere**: how many Authorized Participants
each fund has, which of them were active on which day, whether any declined to
act, and what an AP's own round-trip cost is. §16.4's fee is per transaction and
the number of units per transaction is unpublished (§25.2), so **even the AP's
side of the same edge is bounded rather than known.**

## 29.6 What §29 does not claim

**It is not a profit.** §9 said so before anything ran and it stands: APs do close
this loop and are compensated for doing so. **The claim is that the loop is not
closed for everyone**, which is the two-index structure and not an inefficiency.

**It is not evidence about `λ`'s behaviour.** §26.1's prohibition runs both ways:
`λ`'s readings do not support the hole and the hole does not support `λ`'s.

**It is not a claim about other carriers.** §27.3 measured that this gate does not
breathe, which distinguishes it from A3's `γ^gate`; §28.4 hands the breathing
version to B8. **A contractual membership and a collateral threshold are both
holes and they are not the same object.**

## 29.7 Status

**B9-A-3 is now reported.** With §25's A-1 and A-2, §22's and §23's A-4, and
§27's §26, **every registered prediction of B9-A has a written disposition.**
B9-B remains gated at §10 step 5, which has not run.

---

# 30. B9-B-1, the availability gate, run at last

**§10 step 5. Run 2026-08-17.** §6 states the gate as "trade-level data with size,
without a dissemination cap that is correlated with size", and it has never been
run.

## 30.1 What was found

**IEX publishes HIST, its historical market data, free on a T+1 basis**, subject
to agreeing to its terms of use. The DEEP and TOPS feeds carry **trade report
messages with trade size**, alongside aggregated resting-order depth. **There is
no dissemination cap**: a trade's size is reported as it printed, unlike TRACE's
capped corporate-bond dissemination that §2.1 named as the reason to be careful.

**Nothing has to be bought.** §18.3's prohibition was on acquiring quote data to
rescue B9-A-1; it does not reach B9-B, and this finding means the question does
not arise.

## 30.2 The gate as written: it passes

> **B9-B-1 passes.** Trade-level data with size exists, free, without a
> size-correlated dissemination cap.

## 30.3 The defect §6 did not anticipate, named rather than folded in

**IEX is one venue.** Its share of consolidated volume is a fraction, and **venue
choice is plausibly correlated with order size**: an exchange with a speed bump
attracts some order types and not others.

> **That is not a dissemination cap and §6's gate does not exclude it. It is the
> same failure by a different route**: a size-dependent filter between the market
> and the record.

**Registered as required before B9-B-2 runs**: measure whether IEX's captured
share of a fund's volume varies with trade size. **If it does, a size gradient
estimated on IEX alone is partly a gradient in venue selection**, which is
§12.2's thinness problem with the axis renamed once more.

**This is recorded as a new item and §6's gate is not rewritten to include it.**
The gate asked one question and got its answer.

## 30.4 A second gap, on the denominator

§22.12 and §6's B9-B-2 state the gradient as `π` against **order size over ADV**.
**ADV is consolidated average daily volume, and IEX supplies IEX volume.**

A denominator taken from one venue while the numerator is a trade on that venue
**cancels part of the very variation the prediction is about**. Free consolidated
daily volume exists on exchange websites, which §24's retrieval work found to be
bot-gated (`b9a_availability.py`'s iShares experience, §18's record).

**Registered as the second item**: source a consolidated ADV, or restate the
prediction against a denominator that IEX can supply, **and if the second, say so
in the prediction rather than in a footnote.**

## 30.5 Disposition

| | |
|---|---|
| **B9-B-1** | **passes** (§30.2) |
| **B9-B-2** | **does not start** until §30.3's venue-selection diagnosis and §30.4's denominator are closed |

**Why this matters beyond B9-B.** §22.3 showed `π` degenerates on a two-route
carrier because the path space is one-dimensional. **Order size is the second
axis**: traversals indexed by `(route, size band)` populate a cell with
accumulated `ω` that differs for a reason other than the route, which is exactly
the condition §23.3 registered as necessary. **B9-B is therefore the only place
`π` could be constructed on this carrier family**, and §30.3 and §30.4 are what
stand between here and there.

## 30.6 Status of B9 after §30

**Every registered prediction of B9-A has a written disposition** (§29.7).
**B9-B-1 is now run and passes.** **B9-B-2 has two named prerequisites**, both
about the record rather than about the market, and neither requires buying
anything.

**B9 is no longer waiting on B8 or B10 for anything.** §28's two items are
outbound.

---

# 31. §21.2's ambiguity taken apart before it is measured

**§21.2 recorded that stress-period idiosyncratic persistence vanishing admits two
readings, "a constraint binds commonly" and "per-fund disturbances whiten", and
that D1b could not separate them. §29.4 inherited the ambiguity without resolving
it.** §31 registers the split before running anything, and most of the work is
arithmetic on numbers §20 and §21 already reported.

## 31.1 The identity that ties D1 to D1b

Write the main arm's reading as `λ_{k,t} = c_t + e_{k,t}` with `c_t` the
cross-fund mean of the day (§19.4's `common`) and `e` the residual D1b runs on.
Under the model where each fund's own disturbance is drawn independently across
funds, both `Cov(c_t, e_{k,t})` and the lag-one cross terms `Cov(c_t, e_{k,t−1})`
and `Cov(e_{k,t}, c_{t−1})` are **exactly zero**, because the mean's own noise
term enters the two sides with the same coefficient and cancels. So

> **`ρ_λ = w·ρ_c + (1 − w)·ρ_e`, with `w = V_c / (V_c + V_e)`.**

**D1 measured `ρ_λ`. D1b measured `ρ_e`. `ρ_c` and `w` have never been measured.**
The identity says the three are not free of one another, and that is what §31
exploits.

## 31.2 What the identity forces with no new data

`ρ_λ` is a convex combination, so **it always lies between `ρ_c` and `ρ_e`**. That
gives a bound on `ρ_c` per fund that **does not require knowing `w`**:

- `ρ_λ > ρ_e` forces `ρ_c > ρ_λ` (a lower bound)
- `ρ_λ < ρ_e` forces `ρ_c < ρ_λ` (an upper bound)

Applied to `results/b9_disc.json`, main arm, calm days:

| | `ρ_λ` | `ρ_e` | bound on `ρ_c` |
|---|---|---|---|
| XLB | 0.139 | 0.165 | `< 0.139` |
| XLC | 0.040 | 0.088 | `< 0.040` |
| XLE | 0.130 | 0.113 | `> 0.130` |
| XLF | −0.005 | 0.007 | `< −0.005` |
| XLI | 0.038 | 0.113 | `< 0.038` |
| XLK | 0.076 | 0.033 | `> 0.076` |
| XLP | 0.093 | 0.226 | `< 0.093` |
| XLRE | 0.089 | 0.020 | `> 0.089` |
| XLU | 0.025 | 0.050 | `< 0.025` |
| XLV | 0.142 | 0.124 | `> 0.142` |
| XLY | −0.081 | −0.116 | `> −0.081` |

**Tightest lower bound `0.142`, tightest upper bound `−0.005`. On calm days the
eleven bounds cross.**

The same table on stress days:

| | `ρ_λ` | `ρ_e` | bound on `ρ_c` |
|---|---|---|---|
| XLB | 0.150 | 0.093 | `> 0.150` |
| XLC | 0.078 | −0.047 | `> 0.078` |
| XLE | 0.189 | 0.100 | `> 0.189` |
| XLF | 0.086 | −0.191 | `> 0.086` |
| XLI | 0.121 | −0.038 | `> 0.121` |
| XLK | −0.027 | −0.070 | `> −0.027` |
| XLP | 0.118 | −0.009 | `> 0.118` |
| XLRE | 0.149 | 0.070 | `> 0.149` |
| XLU | 0.049 | −0.019 | `> 0.049` |
| XLV | 0.166 | 0.166 | tied, no bound |
| XLY | 0.151 | 0.119 | `> 0.151` |

> **On stress days every fund that gives a bound gives a lower one, and they are
> mutually consistent: `ρ_c > 0.189`. On calm days they are not.**

## 31.3 Why that is a tension and not yet a result

**Two reasons the calm crossing is not a contradiction, both registered now so
that the run cannot be read as rescuing them afterwards.**

1. **The regime split is per fund.** §6 classes a day by the fund's own trailing
   sixty-day realised NAV vol against the fund's own median, so XLV's calm days
   and XLF's calm days are different sets and the two bounds are not bounds on
   the same number. §19.4 measured the mean pairwise Jaccard of the stress sets
   at `0.558`, so they overlap heavily but not enough for the bounds to be
   comparable without care.
2. **Sampling error swamps the gap.** With `202` calm pairs per fund the standard
   error of a lag-one correlation is about `1/√202 = 0.070`. The crossing gap is
   `0.147`, which is `2.1` standard errors taken as the spread between the
   extremes of eleven noisy estimates. **That is ordinary.**

**And the stress-side agreement must not be read off the count either.** §20.2
already settled that on this arm: the day effect takes `0.703` of the pooled
variance, so eleven funds are close to one observation and `10/11` is not
`2^{−10}`. **The stress side is suggestive on its level, `ρ_c` above `0.189`,
and the level is what §31 goes and measures.**

## 31.4 The three quantities the run adds, and the one definition it must fix

**Measured directly, none of them derived from the bounds above:**

1. `ρ_c`, the lag-one persistence of the common series `c_t` itself, by regime.
2. `V_c` and `V_{e,k}` by regime, hence `w` by regime.
3. Whether the identity of §31.1 closes fund by fund.

**`c_t` is one series for all eleven funds, so it needs a market-wide regime and
§6 only defines a per-fund one. Registered before the run:**

> **A day is a market-stress day when it is a stress day, by §6's existing
> per-fund rule, for at least six of the eleven main-arm funds.**

**This adds no new statistic and no new threshold beyond a majority.** It reuses
the classification already registered rather than inventing a twelfth median. The
count of market-stress days is reported whatever it is.

## 31.5 The registered table, signs opposed

**Every cell is forced by §31.1, so this is a derivation and not a menu.**

| `V_e` in stress | `ρ_c` in stress | filed as |
|---|---|---|
| **falls** | **rises** | **pinning.** A common object binds and becomes more persistent while the funds are pushed together, and the residual is what is left after the pinning. **§21.2 resolves toward "a constraint binds commonly."** |
| **falls** | **flat or falls** | **composition.** `w` rises, weight shifts onto a component that did not itself change, and D1's rise is a reweighting. **Nothing became more persistent, and D1's rise loses its economic content.** |
| **rises** | **rises** | **both.** A common object binds and idiosyncratic variance grows with it. **§21.2 stays open**, and D1b's fall is then partly a variance effect rather than a whitening. |
| **rises** | **flat or falls** | **inconsistent with D1.** With `w` falling and `ρ_e` falling, the identity cannot produce the measured rise. **That would be a defect in the pair construction and not a fact about the market**, and it is filed in §8's defect ledger rather than as a reading. |

**The pure form of "per-fund disturbances whiten" appears nowhere as a clean
cell.** Whitening on its own lowers `ρ_λ`; D1 measured it rising. **So §21.2's
second reading already requires something to happen on the common side, and §31
is asking what.**

## 31.6 Instrument checks registered with the prediction

1. **Identity closure.** Pearson pairs are demeaned list by list, so §31.1 holds
   approximately rather than exactly. **Registered tolerance: closure when
   `|ρ_λ(V_c+V_e) − ρ_c V_c − ρ_e V_e| / (V_c+V_e) < 0.01` for every fund in
   every regime.** A fund outside it means D1 and D1b are not running on the same
   pairs and its reading is void.
2. **Pair sets.** D1's loop has no `common` guard and D1b's does. For the main
   arm `common` covers every day any main fund has, so they should be identical.
   **Verified rather than assumed**, by printing both counts.

   **Amended while building the instrument, before the run.** The first draft of
   this check tried to make closure catch a pair-set mismatch, on the reasoning
   that a component measured on the wrong days would not add up. **It does not
   work.** On a synthetic where the components are periodic, halving the pair set
   leaves the covariance per pair unchanged and the residual is still exactly
   zero. So **§31.6(1) does not subsume §31.6(2)**, and the pair counts are
   compared directly. The selftest asserts both halves of this, that the counts
   differ and that closure does not notice, so the reasoning cannot quietly
   revert.

   **A rotation of the residual is also not a valid negative control**, for the
   same family of reason: a shift leaves a periodic series' own autocovariance
   unchanged, so the identity still closes. The control that bites is a
   component with the wrong scale.
3. **The shared calendar, and what the first run caught.** `c_t` needs day
   adjacency at market level, and §31's first draft took `order` to be
   comparable across funds. **It is not.** `order` is a row number in each
   fund's own NAV history, and the funds have different inception dates: XLC
   lists in 2018 and carries `1646` rows where an older fund carries `5310`, so
   `2025-01-02` is row `1646` in one and row `5310` in another.

   **The first `--decomp` run refused, reporting `1616` clashes.** That is the
   guard working. §15.2 established that the funds share a *calendar* over the
   connect window; **it never said they share an index**, and only the
   differences were ever comparable.

   **Fixed by anchoring**: every fund is offset to the earliest day present in
   all eleven, and the agreement §15.2 asserts is then checked on the normalised
   values. The selftest asserts three things about the fix, that a constant
   offset is not a clash, that a genuinely different calendar still is, and that
   no shared day is a refusal rather than an empty run. **The guard kept its
   teeth through the repair**, which is the property that matters about a repair
   to a guard.

   **This is defect nine for §8's ledger**, and it is the same family as the
   other eight: an artefact of the record mistaken for a fact about the world,
   caught by a check written before the run.

4. **Small-sample bias, checked and expected to pass.** The main arm is `203`
   calm and `201` stress days per fund, so the lag-one estimator's `−(1+3ρ)/T`
   bias is about `−0.006` in both regimes and differences out. **This is recorded
   as a check that passes rather than a correction applied**, and it would not
   pass on SPDW or SPEM, whose splits are `196/109` and `136/104`. Those two are
   not in the main arm and are not used here.

## 31.7 What §31 cannot do

**It does not close §7's fourth link.** Under the pinning reading, the ordinary
account, that arbitrage capacity is common and gets constrained under stress,
gives the same prediction on every quantity §31 measures. §31 tells §29.4 which
mechanism it inherited; it does not tell the two accounts apart.

**The fourth link stays where §27 left it**: B9-B's size gradient and the
breathing gate handed to B8 in §28.

---

# 32. §31's reading: the cell it landed in, the derivation it killed, and what the cross term turned out to be

**Run 2026-08-17, `results/b9_decomp.json`.** §31 registered four cells, three
instrument checks and one derivation. **The cells returned an answer, the
derivation was falsified, and the instrument checks turned out to be measuring
something.**

## 32.1 The registered verdict

| | calm | stress |
|---|---|---|
| `ρ_c` | `+0.0457` | `+0.1148` (se `0.0718`) |
| `V_c` | `2.312e−08` | `5.821e−08`, **`2.52×`** |
| `V_e` | `1.121e−08` | `2.389e−08`, **`2.13×`** |
| `w` | `0.673` | `0.709` |

Market-stress days `194` of `404` under §31.4's majority.

> **`V_e` rises and `ρ_c` rises, so §31.5 files this as `both`, and §21.2 stays
> open.**

**`Δρ_c = +0.0691`, which is `0.96` standard errors.** Both variances roughly
double, the mix barely moves, and the common component's persistence rises by
about one standard error. **Per fund `ρ_c` rises in ten of eleven and `V_e`
falls in three of eleven**, and §20.2's ruling applies to both counts: with the
day effect at `0.703` of pooled variance, eleven funds are near one observation.

**§21.2 is not resolved. That is the registered outcome and it is reported as
the registered outcome.**

## 32.2 §31.2's derivation is dead, and §31's own instrument killed it

§31.2 derived a weight-free bound on `ρ_c` from `ρ_λ` and `ρ_e`, and found the
bounds crossing on calm days and consistent on stress days at `ρ_c > 0.189`.

**Measured `ρ_c` on stress days is `0.1148`, below the bound.** Per fund the
bound is violated outright in five of eleven on calm days: XLE required
`ρ_c > 0.130` and reads `0.045`, XLK required `> 0.076` and reads `0.043`, XLV
required `> 0.142` and reads `0.092`, with XLF and XLU violated in the other
direction.

**A convex combination cannot fall outside its own endpoints, so the premise is
what failed.** §31.1 stated that premise explicitly: the lagged cross
covariances `Cov(c_{t−1}, e_{k,t})` and `Cov(e_{k,t−1}, c_t)` vanish. **They do
not.**

**The whole of §31.2 is withdrawn.** The algebra was right and the premise was
wrong, and it was written down as a premise, which is why one run could kill it.

**A second piece of evidence points the same way, and it is the cleaner one.**
Measured `ρ_c` runs `0.022` to `0.109` across the eleven on calm days, nearly the
same number in each, **which is what it must be**: `c_t` is one series and the
only thing that differs between funds is which days each calls calm. **The
quantity is well behaved. The bound that said it could not be there was not.**

## 32.3 The cross term, measured rather than tolerated

§31.6(1) registered a closure tolerance and a reason for a breach, that D1 and
D1b were not running on the same pairs. **Fifteen of twenty-two fund-regime
cells breached, and `pairs_match` is true in all twenty-two.** The registered
reason is falsified, so the registered disposition does not apply and the breach
had to be diagnosed instead.

`λ = c + e` is an identity and demeaning is linear, so

> **`Cov(λ_{t−1}, λ_t) = Cov(c_{t−1}, c_t) + Cov(e_{t−1}, e_t) +
> Cov(c_{t−1}, e_t) + Cov(e_{t−1}, c_t)` exactly.**

**The four-term form holds to machine precision on every fund, which is what
makes it the pair check.** §31.6(1)'s residual was the last two terms all along.

**Size.** `|cross| / |Cov(c_{t−1}, c_t)|` has median about `0.93` on calm days,
reaching `5.6` on XLY, `2.1` on XLE and XLC, and about `0.16` on stress days.
**On calm days the cross term is the same order as the common component's own
autocovariance.**

**Sign.** `cross` is positive in six funds and negative in five, **in both
regimes**. Split into halves, `Cov(c_{t−1}, e_t)` is positive in seven of eleven
and `Cov(e_{t−1}, c_t)` in six of eleven, in both regimes, and the repeated
counts were checked fund by fund and are a coincidence rather than a copied
value.

## 32.4 What an unsigned cross term is evidence for

**A propagation story signs consistently.** If yesterday's common wedge leads
individual funds, it leads them in one direction, and the eleven should agree.
**Six against five is not agreement.**

**An estimator artefact does not sign consistently.** `c_t` is the equal-weight
cross-sectional mean including fund `k` itself, and §31.1's cancellation is exact
only when the residuals' lagged cross-covariance matrix has equal column sums,
which requires both cross-sectional independence and comparable scale. **XLK and
XLU are not comparable in scale.** With heterogeneous variances the cancellation
fails by an amount that differs fund by fund **and carries no common sign**.

> **The cross term is behaving the way an artefact of the equal-weight mean
> behaves, not the way a lead-lag behaves.** That is a diagnosis and not yet a
> reading, and §32.5 is how to settle it.

**Its size across regimes fits the same account.** In stress `V_c` rises `2.5×`
and the common autocovariance rises three to five times, so an artefact of fixed
relative size becomes small next to it. The measured drop from `0.93` to `0.16`
is what that looks like.

## 32.5 The leave-one-out test, registered before it runs

**Recompute the residual against a common component that excludes the fund
itself**, `c_{−k,t}` being the mean over the other ten. The self-term of the
cancellation disappears entirely, and what is left is whatever the residuals'
genuine cross-structure contributes.

| leave-one-out result | filed as |
|---|---|
| **`\|cross\|` collapses** and most closure residuals fall under `0.01` | **artefact confirmed.** The cross term was the equal-weight mean including the fund, `c_t` is a poor common component on an arm this heterogeneous, and §31.1's identity is recovered on the corrected residual |
| **`\|cross\|` survives at similar size, still unsigned** | **neither.** The residuals have a genuine cross-sectional structure that no mean-based decomposition removes, and `ρ_c` against `ρ_e` is the wrong pair of coordinates on this arm |
| **`\|cross\|` survives and acquires a consistent sign** | **propagation.** A lead-lag between the market-wide wedge and individual funds, which is a real reading and would be the first thing on this carrier that a pure microstructure account does not obviously give |

**The third row is registered as the interesting one and is expected not to
happen.** Writing that down is the point of registering it.

**Thresholds, fixed before the run and named so they cannot drift.** "Collapses"
means the pooled median `|cross| / (G_c + G_e)` at least halves **and** at least
seventeen of the twenty-two cells fall under §31.6(1)'s own `0.01`. "Consistent
sign" means at least nine of eleven share a sign in some regime. **Collapse is
evaluated first**, because a cross term that has collapsed has nothing left to
sign, and the selftest asserts that ordering along with all three rows.

**Leave-one-out is a diagnostic and does not redefine D1b.** §21.1's reading
stands on the residual it was computed on. §32.5 asks what the cross term is,
not what D1b should have been.

## 32.6 A defect in §32's own reporting, found and fixed on the first print

The first version reported `cross / Cov(λ_{t−1}, λ_t)`. **That denominator
crosses zero**: XLF reads `ρ_λ = −0.005` on calm days, so the ratio printed
`10.03` and `−3.61` at the two ends of the range, which is a statement about the
denominator and not about the cross term.

**Replaced by `cross / (G_c + G_e)`**, the signed version of §31.6(1)'s own
residual, whose denominator is a sum of scales and cannot vanish. **The badly
normalised figure is kept in the record under its own name rather than removed**,
so that the range `[−3.61, 10.03]` cannot be rediscovered later as a finding.

**Defect ten for §8's ledger**, and the same family as the other nine: an
artefact of the instrument that reads like a fact about the world.

## 32.7 Disposition

| | |
|---|---|
| **§31.5's verdict** | **`both`. §21.2 stays open.** |
| **§31.2's bound derivation** | **withdrawn**, premise falsified by measurement |
| **§31.6(1)** | **reclassified**: it was measuring `cross`, not checking pairs. The four-term identity is the pair check |
| **§31.6(2), (3), (4)** | pairs match everywhere; calendar anchored; balanced samples as expected |
| **the cross term** | **large on calm days, unsigned, diagnosed as an equal-weight-mean artefact, and §32.5 registered to settle it** |

**§31.7 stands.** None of this closes §7's fourth link, and the leave-one-out
test's third row is the only cell anywhere in §31 or §32 that would.

---

# 33. The tolerance was set below the quantity's own noise floor, and §33 measures the floor

**§32.5's leave-one-out ran and returned `neither`: the cross term survived at
`0.0235 → 0.0232` with the sign still six against five.** §32.4's artefact
diagnosis is dead, killed by a test registered before it ran. **That is the
registration working and it is reported as such.**

**But §32.5 row 2's reading should not be accepted yet, because §32 never
established that the cross term is distinguishable from zero at all.**

## 33.1 The arithmetic that should have been done in §31.6

Each autocorrelation in this decomposition rests on about `200` pairs, so its
sampling standard error is around `1/√200 = 0.07`. The cross term normalised by
`G_c + G_e` is a combination of three such quantities and inherits a spread of
the same order.

**§31.6(1) registered a tolerance of `0.01`.**

> **A tolerance an order of magnitude below the quantity's own sampling spread
> is not a tolerance. It guarantees breaches, and a guaranteed breach invites a
> mechanism to explain it.** §32.4 supplied one, and §32.5 killed it.

**The observed median `|cross| / (G_c + G_e)` is `0.0235`.** Under a null of zero
with a spread of `0.07`, the expected median absolute value is
`0.6745 × 0.07 ≈ 0.047`. **The observed value is smaller than pure noise would
give**, which is the opposite of the direction §32 read it in.

## 33.2 This is §24's error with the axis renamed

§24 found that §4 had compared a reading to the wrong floor: an arbitrage cost
standing in for a measurement quantum. **§31.6(1) compared a residual to a
tolerance that is not its noise floor either.**

> **A quantity is only large or small against its own floor, and the floor has to
> be measured rather than assumed.** §24 established that once and §31 did not
> apply it.

**Defect eleven for §8's ledger, and it is the same family as §24's**, which is
the family the project has already paid for once.

## 33.3 The null, deterministic and with no random numbers

The cross term is `Cov(c_{t−1}, e_t) + Cov(e_{t−1}, c_t)`. **A null that
preserves each series' own autocorrelation and destroys only the relation
between them is a circular shift of `e` against `c`.**

> **Every circular shift `L` from `10` to `n − 10` is used, all of them, and the
> observed cross term's rank among them is reported.** No random number
> generator is involved, so the figure is reproducible to the digit.

**Why the shift and not a permutation**: a permutation destroys `e`'s own
autocorrelation as well, so it would test a different null and would make the
cross term look significant whenever `e` is persistent at all. **The shift keeps
`ρ_e` and `ρ_c` exactly as measured**, which is the null §31.1 actually asserted.

**Why `10` at each end**: a shift of one or two leaves the series nearly aligned
and the null would contain the alternative. **The lower bound is stated rather
than tuned, and it is not moved after seeing the answer.**

## 33.4 Registered outcomes, before the run

| observed `\|cross\|` against its own shift distribution | filed as |
|---|---|
| **inside the bulk**, with the count of cells above the `95`th percentile near the one in twenty-two chance predicts | **the cross term is not distinguishable from zero.** §31.1's premise stands, §31.6(1)'s tolerance was below the noise floor, and **§32.2 and §32.4 are both withdrawn.** §31.2's bound derivation stays withdrawn on the separate ground §31.3 already gave, that the bounds were `2.1` standard errors apart on eleven noisy estimates |
| **in the tail in a clear majority of cells** | **the cross term is real.** §32.5's `neither` stands with a measured significance behind it, and the one-factor decomposition is the wrong instrument on this arm for a reason that has been demonstrated rather than asserted |
| **in the tail in a few cells only, unsigned** | **not established either way.** Report the count, change nothing, and stop: this is the answer that says the arm is too small, eleven funds sharing `0.703` of their variance |

**The first row is the one expected.** Registering the expectation is the point.

**Thresholds, fixed before the run.** A cell counts as in the tail when its
observed `|cross|` sits at or above the `95`th percentile of its own shift
distribution. Row 1 is at most `3` such cells of `22`, which is two standard
deviations above the `1.1` a `Binomial(22, 0.05)` predicts. Row 2 is `12` or
more, a clear majority. Row 3 is everything between. **The selftest asserts both
boundaries in both directions**, and asserts that the null detects a series
constructed to lag (percentile `1.000`) while leaving two independent series
alone (percentile `0.187`).

## 33.5 What §33 repairs even if the first row holds

**The noise floor itself is the deliverable.** Once the shift distribution is
measured, §31.6(1)'s tolerance can be set to a percentile of it rather than to a
number picked because zero looked exact. **A closure check with a floor measured
from the same data is a check; one with a floor picked by eye is a generator of
false findings**, and this stage has now produced one.

**§31.5's four cells lose their forcing claim regardless.** The table said every
cell was forced by §31.1's identity, and that identity has a fourth term whether
or not the term is distinguishable from zero. **Row 4's impossibility argument in
particular does not survive**: with a cross term of any size the identity can
produce a rise that §31.5 called impossible. The verdict `both` remains the cell
the measured signs land in, and the claim that the four cells exhaust the
possibilities is withdrawn.

## 33.6 What does not change

**`V_e` rising `2.13×`, `V_c` rising `2.52×`, and `ρ_c` rising `0.0691` are
direct measurements and do not depend on the cross term at all.** §32.1 stands
in full. **§21.2 stays open**, and after §33 it will be open with a reason
attached rather than open by default.

---

# 34. Row 1 fires, two sections are withdrawn, and §21.2 closes as open with a reason

**Run 2026-08-17.** §33.4's first row, the one registered as expected.

## 34.1 The reading

| | |
|---|---|
| cells at or above their own `95`th percentile | **`0` of `22`** |
| chance predicts | about `1.1` |
| shifts per cell | `384`, deterministic, every one of them |
| **median null `\|cross\|`** | **`0.0334`** |
| **median null `95`th percentile, the floor** | **`0.0933`** |
| **§31.6(1)'s registered tolerance** | **`0.01`** |

> **The floor is `9.3` times the tolerance that was registered against it.**

**Observed median `|cross|` is `0.0235`, below the null's own median of
`0.0334`.** Not merely inside the distribution, on the low side of it.

## 34.2 The withdrawals, as registered

**§32.2 is withdrawn.** It claimed §31.1's premise was falsified. The evidence
was fifteen cells breaching a tolerance nine times smaller than the quantity's
sampling spread. **The premise was never tested by that comparison.**

**§32.4 is withdrawn in full.** It diagnosed a mechanism, the equal-weight mean
including the fund itself, for a breach that was not a breach. §32.5's
leave-one-out killed the mechanism and §33 killed the thing it was explaining.
**Both were registered before they ran, and both did their job.**

**§31.2 stays withdrawn, on the other ground.** §31.3 had already recorded that
the crossing was `2.1` standard errors taken as the spread between the extremes
of eleven noisy estimates, which is ordinary. **That reason survives; the
cross-term reason does not, and §32.2 should never have replaced it.**

**§31.6(1)'s tolerance is replaced by the measured floor**, `0.0933`, and the
fifteen breaches become zero at the floor that belongs to the quantity.

## 34.3 A construction found while reading, which makes §32.3's sign report empty

`e_{k,t} = λ_{k,t} − c_t` and `c_t` is the mean over the same funds, so
`Σ_k e_{k,t} = 0` identically. Therefore

> **`Σ_k Cov(c_{t−1}, e_{k,t}) = Cov(c_{t−1}, Σ_k e_{k,t}) = 0` exactly.**
> **The eleven cross terms are constrained to sum to zero, so they must carry
> mixed signs.**

**Measured**: the eleven sum to `−1.02e−09` on calm days and `+0.30e−09` on
stress days, against a typical individual magnitude near `2e−09` and a random
sum of eleven such terms near `6.6e−09` and `8e−09`. **The constraint is
measured and not merely asserted**, and it does not bind exactly only because
each fund's pairs sit on its own regime split.

**So §32.3's "six positive and five negative, in both regimes" was reporting a
construction.** It was not evidence about the market and it should not have been
written as though it were.

**§32.5's sign test survives, barely and for a reason worth stating**: the
leave-one-out mean differs per fund, so the sum constraint does not hold there,
and the sign majority was a test that could in principle have fired. **On the
all-fund version it could not have.** That is the same defect family as the three
inert selftest cells this stage has already replaced.

## 34.4 The null's own limit, named rather than left out

**The shift breaks `e`'s identity as `c`'s residual**, so a shifted `e` is free to
covary with `c` in a way the real residual is not. **The null is therefore wider
than the truth and the test is conservative.**

**It does not change the answer.** With `0` of `22` and the observed median
sitting below the null median, the null would have to narrow by roughly a factor
of four for any cell to reach its tail. **And the direction of the bias is
exactly what §34.3 predicts**: a mechanically constrained residual should sit
below a null that has released the constraint, which is what it does.

**The sharper null is named and not built**: a shift applied to the whole panel
at once, preserving `Σ_k e_{k,t} = 0`. **It is not built because the answer is
not close**, and building it would be work spent to move `0/22` to `0/22`.

## 34.5 What §31.5's table keeps and what it loses

**Loses**: the claim that the four cells are forced by §31.1's identity. The
identity has a fourth term whether or not that term is distinguishable from
zero, and **row 4's impossibility argument in particular does not survive** it.

**Keeps**: everything measured. `V_e` rising `2.13×`, `V_c` rising `2.52×`,
`ρ_c` rising `0.0691`, `w` moving `0.673` to `0.709`. **The verdict `both` is
the cell the measured signs land in**, and with the cross term at zero the
decomposition is a valid orthogonal split, so the cell means what it says.

## 34.6 §21.2's disposition, and why it is a clean answer

> **§21.2 stays open, and after §33 it is open because `Δρ_c = 0.0691` is `0.96`
> standard errors, not because the instrument is wrong.**

**The instrument is now known to be sound.** The cross term is zero, the identity
closes, the pairs match, the calendar is anchored, and the samples are balanced
at `203` against `201`. **The test ran correctly and the arm is too small.**

**How much too small, stated as a number.** Two standard errors on a difference
of `0.069` needs a standard error near `0.035`, hence about `800` pairs per
regime, hence about `1,600` trading days. **The window is `404`.**

## 34.7 Why the window is `404` and why only one route lengthens it

**Rule 6c-11 requires premium and discount history for the most recent calendar
year and the quarters since.** `405` dates is the rule, not the vendor and not
the retrieval. §15.2's `404`-day connect window is a disclosure limit.

**The NAV history runs `5,734` rows, about twenty-two years**, so the obvious
move is to reconstruct the premium from a free closing price over the long
history. **It does not work, and §24 is why.**

§24.1 established that every reconstructed close lands exactly on the half-cent
grid across sixteen funds and `404` days, `off-grid = 0.000`, **so the disclosed
price is the closing NBBO midpoint**. A free price source supplies the official
close or the last trade. **The difference between those conventions and the
midpoint is up to half a spread, which §24 measured at the tick, and the tick is
the same order as `λ` itself at `1.2` to `1.7` basis points.**

> **The substitute price is wrong by more than the quantity being measured.**
> This is §24's lesson a second time: a reading is only meaningful against a
> floor of the right kind, and a price of the wrong convention is a floor of the
> wrong kind.

**So the window lengthens forward and only forward**, one trading day at a time.

**Corrected the same day, after reading the capture code rather than
remembering it.** §34.7 first said the registered daily capture is what
lengthens the window. **It is not, as written.** `--daily-capture` fetches one
file, SSGA's cross-fund `spdr-product-data-us-en.xlsx`, which is what §13.3(4)
registered it for: the `30`-day median bid-ask spread is published as a current
value with no history, which is why §4's `√N` could only ever be a per-fund
constant.

**The premium history is a different file and a different problem.** `pdhist`
holds a rolling `404` days: a new day enters at the front and an old day leaves
at the back. **Capturing only the product-data workbook leaves the window
sliding rather than growing.**

> **To grow the window, `pdhist` must be archived before its oldest day falls
> off.** Retention is `404` days, so any capture interval under about four
> hundred days loses nothing, and daily is simplest at roughly `640` kB across
> the sixteen funds. **`navhist` does not need it**: it only grows.

**Registered as the correction to §34.7**, and the reason it matters is exactly
§34.6's arithmetic: the arm needs about `1,600` trading days and has `404`.
**Every day the archive does not run is a day that leaves the record
permanently**, which is the same statement §34.7 made and now attaches to the
right file.

## 34.8 Status after §34

| | |
|---|---|
| **§31.5's verdict** | **`both`**, on a decomposition now known to be a valid split |
| **§21.2** | **open, for a measured reason**: `0.96` standard errors on a `404`-day window |
| **§31.2, §32.2, §32.4** | **withdrawn** |
| **§31.6(1)** | **tolerance replaced** by the measured floor `0.0933` |
| **§32.3's sign report** | **empty by construction** (§34.3) |
| **defects 9, 10, 11** | calendar index, the vanishing normaliser, the tolerance below the noise floor |
| **§7's fourth link** | **untouched.** §31.7 stands |

---

# 35. "Why does this need the future, can the past not be used?" — three layers, and one of them was not looked at

**陛下 asked it after §34, and the answer has three layers rather than one.**
Two of them were already in the record. **The third was not, and it is a route
this stage never went down.**

## 35.1 Layer one: the daily premium before 2025-01-02 is gone, and that is retention

`pdhist` holds a rolling `404` days. The days before the window were in the file
a year ago and nobody archived it. **This is a retention rule, not a retrieval
failure**, and §34.7's correction is the fix going forward: archive the file
before its oldest day falls off the back.

## 35.2 Layer two: reconstruction from a free price fails, for a measured reason

The NAV history runs twenty-two years and closing prices are free, so
`premium = P/NAV − 1` looks available for the whole span.

§24.1 measured that every reconstructed close lands exactly on the half-cent
grid, sixteen funds and `404` days, `off-grid = 0.000`, **so the disclosed price
is the closing NBBO midpoint**. A free source gives the official close or the
last trade, and the gap between those and the midpoint is up to half a spread.
§24 measured the spread at the tick, and the tick is the same order as `λ` at
`1.2` to `1.7` basis points.

**And the contaminant is not zero-mean.** A trade prints at the bid or the ask
depending on which side initiated, and the initiating side is not balanced under
stress. **So the error's sign correlates with the very axis every B9-A reading
is measured along**, which is worse than an error of the same size that averaged
out.

> **A substitute price is wrong by more than the quantity, in a direction that
> tracks the regime.** That is §24's lesson a second time.

## 35.3 Layer three: the quarterly counts exist, are free, go back years, and were never fetched

**Issuers publish historical premium and discount tables as counts of trading
days**: days the close was above NAV, at NAV, and below NAV, tallied by period.
One iShares example read `92 / 3 / 157` for a period and is served as a plain
document with no session.

> **That is D2's object.** §20.1's discount share is exactly the count of days
> below NAV over the total, and this is that count for periods this stage cannot
> otherwise reach.

**What it cannot do**: `ρ_c`, `ρ_e`, `V_c`, `V_e` and everything in §31 to §34
need day-to-day pairs. **A quarterly tally has no lag-one structure and §21.2 is
not reachable this way.** That gap stays exactly as §34.6 left it.

**What it can do**: extend D2, and D2 alone, across periods the `404`-day window
does not contain.

## 35.4 Why that is worth more than it first looks

**The stress split in every B9-A reading is relative.** §6 classes a day by the
fund's own trailing sixty-day realised NAV vol against the fund's own median, so
`203` days are "calm" and `201` are "stress" **by construction**, whatever the
window contains. If the window holds no crisis, "stress" means the busier half of
an ordinary period.

**D2's `0.453 → 0.508` shift was measured on that split.** Testing the same
prediction across `2020` and `2022`, where the stress is not relative, is a
different and much stronger test of the one B9-A reading that carries economic
content.

## 35.5 B9-A-5, registered as a gate before anything is fetched

**The gate, in §6's form**: does a historical premium and discount day-count
table exist for the main arm, free, without a session, covering periods before
`2025-01-02` and including `2020` and `2022`?

**Three things to establish and to report whatever they are:**

1. **Coverage.** Which of the eleven, and back how far. A table that starts in
   `2024` is not the test.
2. **Resolution.** Counts of days above, at and below NAV are the minimum.
   **Bands** (`0` to `0.5%`, `0.5` to `1%`, and so on) would give a crude
   distribution rather than a share, which is more than D2 needs and worth
   recording if present.
3. **Price convention.** §35.2's whole argument is about which price. **The
   table's "closing price" must be checked against the disclosed midpoint before
   its counts are placed next to §20.1's**, and if it is a different convention
   the two series are not one series.

**Registered outcome if the gate fails**: report it and stop. **B9-A-5 does not
substitute for §34.7's archive**, which is the only route to `ρ_c` and remains
the reason the scheduled task matters.

**Registered outcome if the gate passes**: D2 across real stress becomes a stage,
and it inherits §20.5's ruling that D2 is not demeaned on purpose.

## 35.6 What this does not do

**It does not close §7's fourth link either.** A wider discount under real stress
is still something an arbitrage-capacity account predicts. **What it buys is
range**, and range is what §34.6 says this arm is short of.

**It does not reopen §31 to §34.** Those ran on daily data, correctly, and the
answer there is `0.96` standard errors on a `404`-day window.

---

# 36. B9-A-6: can a single venue's closing BBO stand in for the disclosed NBBO midpoint, tested against 404 days of ground truth

**Registered 2026-08-17, before any data is fetched.**

## 36.1 The ruling this rests on

陛下 ruled that a free signup credit is not a purchase, **and that anyone can
obtain the same credit, so a result built on it is reproducible without payment,
only with more trouble.** §18.3's prohibition was on buying a quote source to
rescue B9-A-1; this is neither a purchase nor B9-A-1. **The reproducibility
argument is the load-bearing half of the ruling and is recorded as such.**

## 36.2 What is fetched, and why this dataset rather than the obvious one

**Not `EQUS.MINI`.** It is the cheap consolidated-looking option and it fails on
its own terms: coverage begins `2023-03-28`, so **it cannot reach `2020` or
`2022`**, which is the entire reason for going. It is also a synthetic composite
rather than the true national best bid and offer.

**Not `EQUS.SUMMARY`.** End-of-day consolidated prices are a closing price, which
is the wrong convention by §35.2's whole argument.

**Not the eighteen single-venue feeds aggregated by hand.** That moves the error
from someone else's convention into our own construction, which is worse because
it is unmeasured.

> **`XNAS.ITCH`, one venue, coverage from `2018`, `$0.40/GB`.** Schema `bbo-1s`,
> a one-second subsampled top of book. **The last record at or before
> `16:00:00` America/New_York**, which is when NAV is struck and therefore the
> instant Rule 6c-11's market price refers to.

## 36.3 Why one venue might be enough, derived before the run

**§24 measured that these funds sit at the minimum tick**: the tick spans `15.8×`
across the twelve US equity funds while `|λ|` spans `1.42×`, which is what
falsified the quantisation account.

> **When the spread is one tick, every venue quoting at all is quoting at the
> same tick, and a single venue's best bid and offer is the national one.**

**The fact that made §24's argument work is the fact that makes this test
plausible.** It is not certain: Nasdaq can be absent from the inside and quote
two ticks wide on an NYSE Arca listing, and then its midpoint need not be the
NBBO midpoint. **That is exactly what the test measures.**

## 36.4 The criterion is exact equality, not a tolerance

§24.1 measured that every reconstructed close lands on the half-cent grid across
sixteen funds and `404` days, `off-grid = 0.000`, **so `P_disclosed = NAV × (1 +
premium_disclosed)` is a half-cent multiple and is known to the digit.**

> **The test is whether the fetched midpoint equals `P_disclosed` exactly**, to
> within `0.0001` dollars, which on a half-cent grid is floating-point equality.

**A tolerance is refused here on purpose.** §31.6(1) set one below the noise
floor and generated a false finding out of it (§33, §34). **This quantity has no
noise floor to be below: two numbers on the same half-cent grid are equal or they
are not.**

## 36.5 Registered outcomes, with the sub-test that decides the middle row

| exact-match rate over the `404`-day overlap | filed as |
|---|---|
| **`≥ 99%`** | **passes.** A single venue's closing BBO is the NBBO midpoint for these funds, and `XNAS.ITCH` back to `2018` gives about `1,700` further trading days. §34.6's requirement of about `1,600` is met and `ρ_c` becomes reachable |
| **`90%` to `99%`** | **decided by the sub-test below**, not by the headline rate |
| **`< 90%`** | **fails.** Report the discrepancy distribution in basis points **against `λ`'s own `1.2` to `1.7`**, which is the number §35.2 argued for and never measured, and stop |

**The sub-test, registered now because it decides the middle row and because it
is the failure that matters**: are the mismatches concentrated on stress days?

> **A mismatch rate that is flat across regimes is noise the extension can carry.
> A mismatch rate that rises with stress contaminates the extension exactly where
> every B9 reading is taken.** Measured as the mismatch rate on §6's stress days
> against calm days, per fund and pooled.

**Even a `99%` headline fails if the one percent is all in stress**, and that
disposition is registered here rather than argued afterwards.

## 36.6 Two diagnostics that run with it, not after

1. **Crossed or locked books.** The closing auction runs at `16:00:00` and the
   displayed book near it can be wide, locked or crossed. **The rate of
   `bid ≥ ask` in the sampled records is reported**, and a non-trivial rate means
   the sampling instant is wrong rather than that the venue is wrong.
2. **Cost before spend.** The job's cost is estimated through the vendor's own
   cost endpoint and **printed before anything is fetched**, and the fetch
   refuses to run without an explicit confirmation flag. **A credit that expires
   in six months is not a reason to spend it quickly.**

## 36.7 What passing buys, and what it does not

**Buys**: about `1,700` extra trading days, which reaches `2020` and `2022`, and
with them §21.2, `ρ_c`, `V_e`, D1, D1b and D2 all on real stress rather than on
§6's relative split. **§35.4's objection to the current window, that its "stress"
is the busier half of an ordinary period, is answered by range rather than by
argument.**

**Does not buy**: §7's fourth link. **A longer window measures the same
quantities better and does not make any of them something an arbitrage-capacity
account fails to predict.** §31.7 stands unchanged.

**Does not replace §34.7's archive.** If this passes, the archive still matters
for the forward direction and for the spread series, which no venue feed carries.

---

# 37. What the venue feed unlocks, and what it leaves exactly where it was

**Recorded 2026-08-17, with `404` days captured and §36's comparison not yet
run.** Everything in §37 is **conditional on §36 passing**; it is written now so
that the list is not assembled afterwards to fit whatever the answer turns out
to be.

## 37.1 The price side of §18's survey collapses

§18 spent a stage on which issuer would let a script retrieve anything: iShares
behind bot management returning soft `404`s with a CSV content type, Vanguard and
Schwab and Invesco never reached, SSGA the one that publishes static files.
**That survey was about the price and the fund data together, and the two
separate here.**

> **A venue feed carries quotes and trades for every US-listed symbol, and does
> not care whose website blocks scripts.**

**So the sample is no longer bounded by whose price is retrievable.** It is
bounded by whose **NAV** is retrievable, which is still issuer by issuer, and by
the fee, shares outstanding and published spread, which are the same.

**The retired rows in the fund table stay retired for the reason they were
retired**: §18 could not get their NAV history, and §37 does not change that.

## 37.2 §30.3 and §30.4 become addressable, at a cost that is engineering rather than money

§30 gated B9-B on IEX HIST and then named a defect §6 had not anticipated: **IEX
is one venue and venue choice is plausibly correlated with order size**, which is
the same size-dependent filter arriving by a different route. §30.4 added that
`order size over ADV` needs consolidated volume while IEX supplies IEX volume.

**A multi-venue feed answers both**, in principle: trades with size from many
venues, and a volume denominator built from the same source rather than from one
venue.

**Registered as a caveat and not as a solution.** Per-venue coverage depths
differ, and a consolidation assembled by hand is a construction whose error is
ours and is unmeasured, which is exactly §36.2's reason for refusing to build one
there. **B9-B-2 therefore still needs its own gate**, and §30.3's and §30.5's
prerequisites are not discharged by §37.

## 37.3 §12.1's missing spread history exists after all, on the other side of the market

§12.1 recorded that **no issuer publishes a bid-ask spread history**, measured on
two issuers rather than argued from one, and that is what forced the ruling of
2026-08-16: `√N` a per-fund constant, option 甲.

**A quote feed carries the spread at any instant**, so the history the issuers do
not publish is constructible from `2018` for any symbol.

**What that touches and what it does not:**

- **Does not touch §25.** §24 established that the readings stand against the
  **measurement** floor, the half-cent quantum, and that floor is a property of
  the price grid, not of the spread.
- **Touches §18.1**, whose figures §24 relabelled as readings against the
  **cost** floor. Those could become time-varying rather than constant.
- **Touches §18.5's dynamic range**, `|λ|` over the cost floor, which is
  currently one number per fund and would become a series.

> **The ruling of 甲 was correct given what was retrievable and its premise has
> changed.** It is not reopened here, and it is recorded as reopenable.

## 37.4 §34.6's window, which is the whole point and is not yet established

**Conditional on §36.** If a single venue's closing midpoint reproduces the
disclosed price, `2018` onward becomes available and §34.6's requirement of about
`1,600` trading days is met. **If it does not, §37.4 is void and the escalation
is more venues, tested against the same `404` days of ground truth until the gate
passes or the approach is abandoned.**

## 37.5 What stays exactly where it was

| | |
|---|---|
| **The published `30`-day median spread** | fund disclosure, **no venue feed carries it**. §34.7's daily archive is still the only source and still only builds forward |
| **NAV** | issuer only |
| **The fee** | issuer only, and §25.2's per-transaction ambiguity is untouched |
| **Shares outstanding** | issuer only, and `τ = 50,000` was earned from it (§16.2) |
| **§7's fourth link** | **untouched.** More data measures the same quantities better. §31.7 stands |
| **The AP hole (§29)** | a contractual fact, not a data problem |

## 37.6 The order this is written in, on purpose

**§37 lists what would be unlocked before knowing whether it is.** §36's
comparison has not run. **If it fails, §37.1 and §37.3 survive** (they concern
retrieval and the spread, not the midpoint's fidelity) **and §37.2 and §37.4 do
not.**

**That split is registered now** so that a failing gate cannot later be narrated
as having unlocked less than was hoped, or a passing one as having unlocked more.

---

# 38. B9-A-6 fails on Nasdaq, the mechanism is confirmed, and the venue was chosen wrongly

**Run 2026-08-17 on the full `404`-day overlap, `6,178` fund-days.**

## 38.1 The reading

| | |
|---|---|
| **exact-match rate** | **`0.5256`** |
| §36.5's threshold | `≥ 0.99` passes, `< 0.90` fails |
| calm / stress | `0.5448` / `0.5055` |
| crossed or locked at the mark | **`2` of `6,178`** |
| Nasdaq spread of one tick at the mark | `0.5783` |

**Half-cent steps, pooled**: `0` step `52.6%`, `1` step `26.6%`, `2` steps
`12.0%`, `3` or more `8.8%`.

> **B9-A-6 fails as registered.** A single venue's closing midpoint does not
> reproduce the disclosed price.

**§36.5's stress sub-test does not bite**: `0.545` against `0.505` is a gap of
four points on a rate near a half, not a regime effect worth a ruling. **The
headline fails on its own.**

## 38.2 The mechanism §36.3 predicted, confirmed on one half and wrong on the other

§36.3 derived that a one-tick spread makes any quoting venue's best bid and offer
the national one, and that Nasdaq quoting two ticks wide would break it.

**Confirmed.** The per-fund one-tick rate tracks the match rate almost
monotonically: SPAB `0.943 → 0.925`, XLRE `0.943 → 0.767`, XLF `0.858 → 0.779`,
down through XLK `0.092 → 0.235` and XLY `0.182 → 0.242`.

**Wrong on the other half.** The prediction written before the run was that
misses would concentrate overwhelmingly on one half-cent step. **They do not**:
`2` steps or more accounts for `21.2%`, nearly as much as `1` step's `26.6%`.
**When Nasdaq is not at the inside it is often several ticks away**, not one.

## 38.3 The venue was chosen for the wrong reason, and that is §38's own defect

§36.2 chose `XNAS.ITCH` for two stated reasons: coverage from `2018`, and its
being the most active US equities venue. **Neither reason is about these
symbols.**

> **The eleven Select Sector SPDRs are NYSE Arca listings.** The listing venue
> should have been the first candidate and was not considered.

**SPY is the tell that should have been read earlier**: the most liquid ETF in
the market shows a one-tick Nasdaq spread only `22.3%` of the time at the close.
That is not a statement about SPY's liquidity. **It is a statement about where
SPY's liquidity is at `16:00:00`, which is not Nasdaq.**

**Defect twelve for §8's ledger, and it is a design error rather than a code
error**: an instrument was chosen by a property of the market rather than by a
property of the object being measured.

## 38.4 Two diagnostics before any escalation, both registered before running

**Escalating straight to more venues would skip a question that costs nothing to
ask.**

### (a) The sampling instant, on data already on disk

The captures span `15:59:55` to `16:00:05`, so the mark can be moved without
fetching anything. **The exact-match rate is computed at every offset from `−5`
to `+5` seconds.**

| result | filed as |
|---|---|
| **the rate is flat across offsets** | **the instant is right and the venue is wrong.** §38.3's escalation is the only route |
| **the rate peaks away from `0`** | **the instant was wrong**, §36.2's reading of when NAV strikes is wrong by that offset, and the venue verdict is void until it is re-run at the peak |

**The second row is the one that would void §38.1**, and it is registered here
rather than discovered afterwards.

### (b) The venue's coverage, asked of the vendor rather than of a marketing page

`ARCX.PILLAR` exists and is described as NYSE Arca Integrated for ETPs and ETFs.
**Its historical start is not stated on the page and is not guessed.** The
vendor's own dataset-range endpoint is queried for it and for the other
candidates, and whatever it returns is what gets recorded.

**If Arca's coverage does not reach `2018`**, the escalation's premise fails and
the whole `2020` and `2022` objective needs restating, which would be a finding
about the route rather than about the market.

## 38.5 What §38.1 does and does not settle

**Settles**: a single venue chosen for market share does not reproduce the
disclosed price for these symbols. **That is a real and reusable result** and it
is the first measurement anywhere in this stage of how wrong a substitute price
is: `47%` of fund-days disagree, and `21%` disagree by two half-cents or more,
against `λ` at `1.2` to `1.7` basis points.

**Does not settle**: whether the listing venue reproduces it, whether a
two-venue or three-venue best reproduces it, or whether the mark is at the right
instant.

**§37's split holds as written.** §37.1 and §37.3 survive this, since they concern
retrieval and the spread rather than the midpoint's fidelity. **§37.2 and §37.4
remain conditional and are still unmet.**

---

# 39. The instant is right to the second, four venues reach 2018, and the escalation is defined

**Run 2026-08-17. §38.4's two diagnostics, both answered.**

## 39.1 The sampling instant, and a word §38.4 got wrong

| offset | exact rate |
|---|---|
| `−2 s` | `0.3392` |
| `−1 s` | `0.3851` |
| **`0 s`** | **`0.5256`** |
| `+1 s` | `0.4291` |
| `+2 s` | `0.4242` |

> **A sharp peak at the mark. One second either way costs fourteen points.**

**§38.4(a) offered "the rate is flat across offsets" as the first row, and that
word was wrong.** A rate equal everywhere and a rate spiking at zero both leave
zero as the best offset, and they say different things: the first would say the
instrument cannot see the instant, the second says it sees it to the second.
**The drop to the neighbour is what separates them and is now reported as
`peak_sharpness`.** Here it is `+0.0965`.

**So the DST arithmetic, the epoch-nanosecond mark and the NAV-strike reading are
all confirmed by the data rather than by their selftests.** §38.1's venue verdict
stands and is not void.

## 39.2 Coverage, asked of the vendor

| dataset | start | reaches `2020` and `2022` |
|---|---|---|
| **`ARCX.PILLAR`** NYSE Arca, **the listing venue** | **`2018-05-01`** | **yes** |
| `XNAS.ITCH` Nasdaq | `2018-05-01` | yes |
| `XNYS.PILLAR` NYSE | `2018-05-01` | yes |
| `BATS.PITCH` Cboe BZX | `2018-05-01` | yes |
| `IEXG.TOPS` | `2023-03-28` | no |
| `DBEQ.BASIC` | `2023-03-28` | no |
| `EQUS.MINI` | `2023-03-28` | no |
| `EQUS.SUMMARY` | `2024-07-01` | no |

> **Every single-venue feed reaches `2018-05-01`. Every composite one starts in
> `2023` or later.**

**That inverts the usual convenience ordering** and it retroactively strengthens
§36.2's refusal of `EQUS.MINI`, which was made on coverage and on its being
synthetic. **The coverage half was right for a reason §36.2 stated and the
composite half is now moot**: the composites cannot reach the target period at
all.

**A second consequence, for §30.** `IEXG.TOPS` starts `2023-03-28`, so §30's plan
to estimate B9-B's size gradient on IEX cannot reach `2020` or `2022` either.
**§37.2's caveat is sharper than it was written**: multi-venue is not merely
better for B9-B, it is the only option that reaches the period where the
prediction is interesting.

## 39.3 The escalation, registered in order and with its stopping rule

1. **`ARCX.PILLAR` alone.** The listing venue, the candidate §36.2 should have
   started with. Same `404` days, same criterion, same ground truth.
2. **If that fails, the four-venue best**: Arca, Nasdaq, NYSE and Cboe BZX,
   highest bid and lowest ask across the four at the mark.
3. **Stopping rule, registered now**: if the four-venue best does not reach
   `0.99`, the approach is abandoned rather than extended venue by venue until
   it fits. **A construction tuned until it matches is not a measurement**, and
   the ground truth is `404` days, which is not enough to keep spending
   degrees of freedom against.

**Cost of steps 1 and 2 together is a few cents**, so cost is not what decides
this at any point.

## 39.4 The criterion is reproduction, not identity

**A four-venue best is not the NBBO.** There are more than a dozen quoting
venues, and no combination short of all of them is the national best bid and
offer by definition.

> **It does not need to be.** The test is whether it reproduces the disclosed
> price on `6,178` fund-days of ground truth. **If it does, it works; if it does
> not, no argument about its formal status would save it.**

**This is why the `404`-day overlap was the design and not a nicety**: it turns a
question about definitions into a question with an answer.

## 39.5 What passing would give, stated so it can be checked afterwards

`2018-05-01` to `2025-01-01` is about `1,675` trading days. With the existing
`404`, about **`2,080`**.

**§34.6 asked for about `1,600`** to bring `Δρ_c` to two standard errors. **So a
pass would make §21.2 answerable**, and would put D1, D1b, D2, `V_e` and `ρ_c` on
`2020` and `2022` rather than on §6's relative split.

**§7's fourth link would still be untouched.** §31.7 stands, and §37.5 already
recorded that more data measures the same quantities better.

---

# 40. `ARCX` alone fails by two and a half thousandths, and the criterion that should decide this is a different one

**Run 2026-08-17, `6,176` fund-days.**

## 40.1 The reading, and it is a failure as registered

| | Nasdaq (§38) | **NYSE Arca** |
|---|---|---|
| exact-match rate | `0.5256` | **`0.8975`** |
| `\|discrepancy\|` 90th percentile | `1.21` bp | **`0.074` bp** |
| crossed at the mark | `2` | `0` |
| calm / stress | `0.545` / `0.505` | `0.903` / `0.892` |

Half-cent steps: `0` step `5,543`, `1` step `440`, `2` steps `125`, `3` or more
`50`, **with a thin tail of genuine outliers** reaching `227` steps, about
`$1.135`, which is not a grid disagreement and is something else.

> **`0.8975` is below §36.5's `0.90`, so B9-A-6 fails on the listing venue too.
> That is about fifteen fund-days of margin and it is not rounded up.**

**§39.3's step 2 runs as registered.** Nothing here changes it.

## 40.2 The criterion §36.4 chose was a proxy, and the direct one is available

§36.4 chose exact equality for a stated and still-good reason: §31.6(1) had set a
tolerance below its quantity's noise floor and manufactured a false finding out
of it, and two numbers on the same half-cent grid are equal or they are not.

**But reproduction of the price was never the object.** §36 exists so that
`2018` to `2024` can carry D1, D1b, D2, `V_e` and `ρ_c`. **The question that
decides whether the extension is usable is whether those readings change**, not
whether the price matches.

> **And it is directly measurable, on data already on disk**: the same `404`
> days carry both the disclosed premium and the reconstructed one, so every
> stage reading can be computed twice and compared.

**This is registered as a different and better test, not as a reinterpretation
of §36.4.** §38's and §40.1's gate results stand as recorded. **A gate that
failed is not un-failed by finding a kinder question.**

## 40.3 B9-A-7, registered before it runs

**Run `--decomp`, `--disc` and `--measured` twice on the `404`-day window**, once
on the disclosed premium and once on the premium reconstructed from the best
venue candidate, and compare the readings that §31 to §34 reported.

**The quantities compared, fixed now**: `ρ_c` in each regime, `V_c`, `V_e`, `w`,
D1's and D1b's autocorrelations per fund, D2's discount share per regime, and
`|λ|` against the measurement floor.

| result | filed as |
|---|---|
| **every compared quantity moves by less than a quarter of its own standard error** | **fit for purpose.** The reconstruction carries the readings and the extension to `2018` proceeds on it |
| **`ρ_c` or `V_e` moves by more than half a standard error** | **not fit.** The residual error is doing work at the scale the readings live at, and the extension would be measuring the reconstruction |
| **D2 moves and the others do not** | **fit for `ρ`, not for D2.** D2 is a sign count and is the most fragile to a half-cent error, and it is also the one §35.4 most wanted range for. Report the split rather than a single verdict |

**The middle row is the one that ends this route**, and the third is the one that
would be genuinely awkward, so both are written down before the run.

**A quarter of a standard error is chosen as the threshold** because §34.6 put
the whole question at `0.96` standard errors: a perturbation of a quarter of one
cannot flip a conclusion that turns on a full one, and a perturbation of half of
one might.

## 40.4 The outliers are their own question and are not averaged away

The tail reaching `227` half-cents is not the grid disagreeing. **A dollar of
disagreement on a fund-day is a stale quote, a halt, or a corporate action**, and
whatever it is, it is not what §40.3 is measuring.

**Registered**: the outlier fund-days are listed and examined separately, and
**the §40.3 comparison is run both with and without them**. If it passes only
without them, that is a filter and a filter is a decision that has to be
declared, not a cleaning step.

## 40.5 Order

1. §39.3 step 2, the four-venue best. **Registered and unchanged.**
2. §40.3 on whichever candidate scores best, **including `ARCX` alone if the
   four-venue best does not improve on it.**
3. §39.3's stopping rule still binds: **the venue-combining stops at four.**

---

# 41. Combining four venues makes it worse, and that is informative

**Run 2026-08-17, `6,188` fund-days.**

## 41.1 The reading

| candidate | exact-match rate |
|---|---|
| `XNAS.ITCH` alone (§38) | `0.5256` |
| **`ARCX.PILLAR` alone (§40)** | **`0.8975`** |
| **four-venue best (§39.3 step 2)** | **`0.5564`** |

Half-cent steps for the combination: `0` step `3,443`, `1` step `1,779`, `2`
steps `545`, tail beyond.

> **Adding three venues to the listing venue destroyed thirty-four points of
> agreement.** §39.3's stopping rule fires and the combining stops here.

## 41.2 Why a wider net gives a worse answer

**Each venue's record is "the last quote at or before the mark", and those
instants are not the same instant.** Taking the highest bid across venues and the
lowest ask across venues therefore pairs a bid from one moment with an ask from
another.

> **The result is a book that never existed**, systematically narrower than any
> real one, and a midpoint pulled off the grid the disclosed price sits on.

**The `1`-step count is the fingerprint**: it rises from `440` on Arca alone to
`1,779` on the combination. **The combination is not making random errors, it is
making one specific error over and over**, which is what a synchronisation
artefact looks like and is not what a wrong-venue error looks like.

## 41.3 Where the inside actually is

Times each venue held the best bid or the best ask, out of `12,376`:

| venue | count | share |
|---|---|---|
| **`ARCX.PILLAR`** | **`9,628`** | **`77.8%`** |
| `XNYS.PILLAR` | `1,288` | `10.4%` |
| `XNAS.ITCH` | `1,085` | `8.8%` |
| `BATS.PITCH` | `375` | `3.0%` |

**The listing venue holds the inside more than three quarters of the time**, and
the `22%` where another venue appears to improve on it is where the agreement is
lost rather than gained.

## 41.4 What this says about the disclosed price

**The disclosed price tracks the listing venue's own midpoint far more closely
than it tracks a naive multi-venue best.** Two readings are consistent with that
and §41 does not choose between them:

1. The publisher derives its market price from the primary listing venue.
2. The publisher uses the true consolidated NBBO, which has round-lot
   requirements, quote-condition filters and proper synchronisation, **none of
   which a max-and-min over asynchronous snapshots reproduces**, and the true
   NBBO happens to sit at Arca's quote most of the time for these funds.

**The second is more likely and neither is testable with what is on disk.**
**It does not matter for §40.3**, which asks whether the reconstruction carries
the readings, not why it works.

## 41.5 §36.2 refused to hand-build a consolidation, and §39.3 built one anyway

§36.2 rejected aggregating single-venue feeds on the grounds that it "moves the
error from someone else's convention into our own construction, which is worse
because it is unmeasured."

**§39.3 then registered exactly that as step 2.** That was not a contradiction
and the difference is the whole design: **here the construction's error was
measured, against `6,188` fund-days of ground truth, and it failed.** The
objection in §36.2 was to an unmeasured construction.

> **The refused thing, done under measurement, is a different act.** And the
> measurement said no, which is what the ground truth was for.

## 41.6 Disposition

| | |
|---|---|
| **§39.3 step 2** | **fails and stops.** No fifth venue |
| **best candidate** | **`ARCX.PILLAR` alone, `0.8975`** |
| **§40.3 (B9-A-7)** | **runs on `ARCX` alone**, as §40.5 already provided for |
| **§36.4's gate** | still failed on every candidate. **Not revisited** |

---

# 42. §41.2's mechanism was asserted too confidently, and the odd-lot account is testable for free

**陛下 asked whether the asynchrony can be solved, whether the records carry
timestamps, and whether the venues can be pulled at the same instant.**

## 42.1 The records do carry timestamps, and they were already used correctly

Each record has `ts_event` and `ts_recv` in epoch nanoseconds, and §36's
comparison takes each venue's **last record at or before the mark**.

> **A quote stands until it is replaced, so a venue's last update before the mark
> is its state at the mark.** That is the textbook consolidation and it is what
> the code does.

**So there is no synchronisation to fix, and §41.2 named a mechanism that does
not survive being asked this question.**

## 42.2 §41.2 is withdrawn as a mechanism and kept as a measurement

§41.2 said the combination "pairs a bid from one moment with an ask from
another" and offered the rise in `1`-step errors from `440` to `1,779` as a
fingerprint.

**The measurement stands. The mechanism does not.** A `1`-step error is half a
tick, and **every account of a wrong inside quote produces half-tick errors**, so
the fingerprint does not distinguish between them. **It was read as confirming
the account it was written next to**, which is the failure §33 and §34 already
cost this stage once.

**Defect thirteen for §8's ledger**: an explanation attached to a measurement
that could not have discriminated it.

## 42.3 The odd-lot account, and what it predicts

**The national best bid and offer is a round-lot construct.** A venue's top of
book is not: an odd-lot order can sit inside the round-lot quote and appear as
that venue's best bid or ask.

> **Taking the highest bid and lowest ask across four venues collects four
> venues' worth of odd lots**, so the constructed book is narrower than the true
> NBBO and its midpoint is displaced by up to half a tick.

**This account predicts, without being fitted to anything:**

1. **Errors concentrated at one half-cent step.** Observed: `1,779` of `2,745`
   misses.
2. **The combination worse than any single venue**, because more venues means
   more chances that one of them shows an odd lot inside. Observed: `0.5564`
   against `0.8975`.
3. **The listing venue best among singles**, because its round-lot depth at the
   inside is deepest and least often displaced by an odd lot. Observed.

**Three predictions, all already satisfied by readings taken before the account
was written.** That is not proof and it is better than the account §41.2 gave.

## 42.4 The free test, registered before it runs

`bid_sz_00` and `ask_sz_00` are already in every cached capture. **Require at
least `100` shares on both sides and recompute**, for `ARCX` alone and for the
four-venue combination.

| result | filed as |
|---|---|
| **both improve, the combination by more** | **odd lots confirmed** as the mechanism, exactly as §42.3 predicts the sizes of the two improvements |
| **both improve by about the same** | **partly odd lots**, and something else is displacing the inside as well |
| **neither improves** | **odd lots are not it**, and §42.3 joins §41.2 in the withdrawn column |

## 42.5 The limit of the test, stated before the result

**`bbo-1s` carries only level zero.** If a venue's best bid is an odd lot, the
round-lot bid behind it is not in the data, so a record failing the size filter
is **dropped rather than corrected**, and the comparison falls back to an earlier
second's snapshot.

> **That reintroduces staleness in exactly the records the filter removes.** So a
> clean improvement is evidence for §42.3, and a muddy one is not evidence
> against it.

**If §42.3 is confirmed, the fix is not this filter.** It is book data deep
enough to find the round-lot level, `mbp-10` or `mbo`, which is a far larger
fetch and would need its own cost estimate and its own gate. **That is registered
as the consequence and is not started here.**

## 42.6 Order

1. §42.4's size filter, free, on both candidates.
2. **§40.3 regardless of the outcome**, on whichever candidate scores best.
   B9-A-7 asks whether the readings survive the reconstruction, and that question
   does not wait on the mechanism behind the residual error.

---

# 43. The round-lot filter voids its own test, in the way §42.5 said it would

**Run 2026-08-17.**

| | rate | `0` step | `1` step | `3`+ steps | p90 |
|---|---|---|---|---|---|
| `ARCX` `sz0` | **`0.8975`** | `5,543` | `440` | `48` | `0.074` bp |
| `ARCX` `sz100` | `0.8967` | `5,521` | **`235`** | **≈`150`** | `0.139` bp |
| four-venue `sz0` | `0.5564` | `3,443` | `1,779` | — | — |
| four-venue `sz100` | `0.5456` | `3,366` | `1,604` | — | — |

## 43.1 The reading

**The `1`-step errors nearly halve and do not become exact.** Zero-step falls by
`22`, three-or-more rises from `48` to about `150`, and the sample shrinks by
only `19`. **The half-tick errors became multi-tick errors.**

> **That is staleness, not correction.** §42.5 registered it in advance: a record
> failing the size filter is dropped rather than corrected, because `bbo-1s`
> carries no deeper level, so the comparison falls back to an earlier second.

## 43.2 The disposition, and a registration defect

**§42.4's third row would withdraw §42.3 on the headline rate. §42.5 says a
muddy result is not evidence against it. Both were registered and they are not
mutually exclusive**, which is a defect in how §42 was written rather than in
what was measured.

**Defect fourteen for §8's ledger: two registered rules that can both fire on the
same result.** §42.5 governs here because it was written about this exact failure
mode and names the mechanism that produced it, and that ruling is recorded rather
than assumed.

> **The test is void, not negative. §42.3 is neither confirmed nor withdrawn.**

**Testing it needs `mbp-10` or `mbo`**, which §42.5 already registered as the
consequence and did not start. **It is not started here either**, because §40.3
does not depend on it.

## 43.3 What carries forward

| | |
|---|---|
| **best candidate** | **`ARCX.PILLAR`, `sz0`, `0.8975`** |
| `sz100` | **worse on every candidate.** Not used |
| §42.3 odd lots | **untested**, route registered, not taken |
| **next** | **§40.3, B9-A-7**, as §42.6 ordered regardless of this outcome |

---

# 44. B9-A-7: the reconstruction does not carry the readings, and the way it fails is the useful part

**Run 2026-08-17. `--recon control` against `--recon recon`, identical fund-days,
differing in the price and in nothing else.**

## 44.1 The reading

| | control | recon | |
|---|---|---|---|
| `V_c` calm | `2.33e−08` | **`8.49e−08`** | **`3.6×`** |
| `V_e` calm | `1.12e−08` | **`2.60e−08`** | **`2.3×`** |
| `V_c` stress | `5.80e−08` | `5.69e−08` | unchanged |
| `V_e` stress | `2.387e−08` | `2.397e−08` | unchanged |
| `ρ_c` calm | `+0.0476` | `+0.0639` | `0.24` se |
| `ρ_c` stress | `+0.1170` | `+0.0640` | **`0.74` se** |

**Consequences on the registered quantities:**

- **`V_e` stress over calm: `2.133 → 0.923`. The direction reverses.**
- **`Δρ_c`: `+0.0694 → +0.0001`. The rise disappears entirely.**
- **§31.5's verdict: `both` → `pinning`. The registered cell changes.**
- D1 calm `+0.0762 → +0.0427`, D1b calm `+0.0888 → +0.0376`, both nearly halved.
- Day-effect variance share `0.7027 → 0.6403`.

> **§40.3's second row fires. The reconstruction is not fit for purpose.**
> `ρ_c` stress moves `0.74` standard errors against a threshold of half of one.

## 44.2 The shape of the failure, which is worth more than the verdict

**The error inflates calm variance and leaves stress variance alone.**

The reconstruction's error is a fixed quantum, one half-cent, set by the price
grid. `λ`'s own amplitude doubles under stress (§32.1's `V_c` at `2.52×` and
`V_e` at `2.13×`). **A fixed error against a signal that grows therefore does
almost all its damage where the signal is smallest, which is calm.**

> **So it does not add noise evenly. It flattens the regime contrast**, and the
> regime contrast is the axis every B9-A reading is measured along.

**This is §24's lesson a third time**, in its sharpest form yet: §24 was about
comparing a reading to the wrong floor, §33 about a tolerance below its noise
floor, and §44 about an error whose size is fixed while the quantity's is not.

## 44.3 Why the proxy criterion would have got this wrong

`0.8975` reads as almost good enough, and the `90`th percentile discrepancy of
`0.074` basis points reads as one twentieth of `λ`. **Both are true and both are
misleading**, because neither is a statement about the calm-period variance,
which is where the reading lives.

**§40.2 registered the direct test on exactly this reasoning and it was right
to.** A gate on price fidelity would have passed this reconstruction into the
extension and the extension would have measured the reconstruction.

## 44.4 D2 survives, and §40.3's third row came out reversed

| | control | recon |
|---|---|---|
| D2 discount share, calm | `0.4532` | `0.4554` |
| D2 discount share, stress | `0.5050` | `0.4950` |
| **shift** | **`+0.0518`** | **`+0.0396`** |
| funds shifting toward discount | `10/11` | `9/11` |

**`76%` of the shift is retained and the direction holds.** §40.3's third row
anticipated an asymmetry and named it the other way round, "fit for `ρ`, not for
D2". **The asymmetry is real and reversed**, and that row's disposition, report
the split rather than a single verdict, applies as written.

**D2 on the extension is therefore possibly usable, with the attenuation
declared.** It is not started here and would need its own registration, because
an attenuation measured on `404` days is not automatically the attenuation on
`2020`.

## 44.5 What the whole venue-feed arc bought, stated plainly

| | |
|---|---|
| **`ρ_c`, `V_e`, `V_c`, D1, D1b on `2018` to `2024`** | **not available.** The reconstruction destroys the regime contrast |
| **§21.2** | **still open, and §34.6's arithmetic is unchanged**: about `1,600` trading days are needed and `404` exist |
| **§34.7's forward archive** | **still the only route to `ρ_c`**, exactly as §34.7 said before any of this |
| **§37.4** | **void** |
| **§37.1, §37.3** | survive, as §37.6 registered they would |
| **§37.2, B9-B** | **unaffected.** It concerns trade size, not premium reconstruction, and §39.2 sharpened its case |
| **D2 on the extension** | **open, with a measured attenuation of about a quarter** |

## 44.6 The deeper-book route, and the bar it now has to clear

§42.5 registered `mbp-10` or `mbo` as the route to testing the odd-lot account,
and it was not taken. **It remains open and its bar has risen**: it would have to
carry the readings, not merely match the price better, **and §40.3's machinery
now exists to test any candidate directly.**

**Registered**: no deeper fetch is made on the strength of a better match rate
alone. **The test is `--recon control` against `--recon recon`, and it is
cheap.**

---

# 45. The catalogue has no off-exchange data at all, and a prior question that should have been asked before §36

**Run 2026-08-17. Full catalogue enumerated rather than a hand-written list,
because a hand-written list cannot discover a dataset nobody thought of.**

## 45.1 What exists

`29` datasets. **Fourteen US exchange feeds**, covering NYSE Arca, Nasdaq, NYSE,
Cboe BZX, BYX, EDGA and EDGX, MEMX, MIAX Pearl, NYSE American, Nasdaq BX and
PSX, NYSE Chicago and NYSE National. Four reach `2018-05-01`.

> **There is no FINRA, TRF, ADF or OTC dataset. Off-exchange execution, roughly
> four tenths of US equity volume, is not in this vendor's catalogue at all.**

## 45.2 What that does to B9-B

**§30.4's denominator.** The first registered option, source a consolidated ADV,
**is not available here**. The second option therefore binds: restate the
prediction against a denominator that can be supplied, **and say so in the
prediction rather than in a footnote**, which is what §30.4 required.

**§30.3's defect survives in full and is worse than it looked.** Off-exchange
share is not uniform in trade size and **is not biased in one direction**:
retail marketable flow is internalised by wholesalers at the small end, and
institutional blocks cross away from the exchanges at the large end. **Both tails
are partly invisible.**

> **That is exactly §30.3's "size-dependent filter between the market and the
> record", relocated and undiminished.** Adding thirteen exchange feeds to one
> does not fix it, because the missing venue class is not an exchange.

**FINRA publishes OTC transparency data free**, per security, weekly, by ATS and
with non-ATS aggregated. **It would supply the denominator and a bound on the
bias, and not the size distribution itself.** Recorded as the partial route and
not taken yet, because of §45.3.

## 45.3 The question that should have been asked before §36, asked now

**§30's B9-B-1 was an availability gate. §36's B9-A-6 was an availability gate.
Neither asked what the reading would discriminate if it succeeded.** §36 to §44
then spent an arc, and its negative result was useful, but the arc was entered
without that question having an answer.

> **Registered as a standing rule: before any further data pipeline is built for
> B9-B, the discriminating power of B9-B-2 must be derived and written down.**

**The specific worry, stated so it can be attacked.** §7 records the framework's
extra claim as "the hole does not vanish at any size". §29 already established
the hole institutionally: the AP requirement is **contractual and not
size-based**, so no size closes it, and that was reported rather than estimated.

**And `λ(s)` for a non-AP should grow with size**, because a larger order pays
more impact. **An ordinary market-impact account predicts the same growth.** So
before building anything:

| must be derived | |
|---|---|
| **what shape of `λ(s)`** the framework predicts that an impact account does not | if the answer is "the same shape", B9-B-2 does not discriminate and should not be built |
| **whether `π` on `(route, size band)`** is constructible at all, given that §22.3's degeneracy came from the path space and a size band is not a path | §23.3 registered size as the candidate second axis and never checked this |
| **what the off-exchange blindness does to each** | a prediction about the size gradient measured on a size-filtered sample |

**Nothing is fetched for B9-B until those three have written answers.** The cost
of skipping this once is already recorded in §36 to §44.

## 45.4 Status

| | |
|---|---|
| **off-exchange data** | **absent from this vendor**. FINRA free weekly is the partial route |
| **§30.4** | second option forced, denominator to be restated **in the prediction** |
| **§30.3** | **survives in full**, and in both size directions |
| **B9-B-2** | **blocked on a derivation, not on data** (§45.3) |
| §7's fourth link | **untouched**, and §45.3 questions whether this route reaches it |

---

# 46. B9-B-2 does not discriminate, derived before anything is built

**§45.3 required three written answers before any pipeline. They are derived
here, from the record, with no data fetched.**

## 46.1 Is `(route, size band)` a dimension of the path space?

**Formally the enrichment works, and §23.3's condition is met.** The `etf → cash`
edge carries `log(P/NAV)`, and the price a trader gets depends on the size
traded, so the **same route** accumulates a different `ω` at a different size.
Within a cell, traversals become `2` routes times `N` size bands rather than `2`
routes, and §22.3's degeneracy is broken: `π` stops being pinned at `1/2` and
starts depending on how much `λ` varies across sizes relative to across cells.

> **So `π` becomes constructible. §23.3's registration was right about that and
> it is confirmed rather than withdrawn.**

**But a cochain is a function on edges**, and a value that depends on how much is
carried is not one. Two repairs exist and they are not equivalent:

| repair | consequence |
|---|---|
| enlarge the graph so vertices are `(position, size band)` | size becomes a position coordinate, and the object measured is no longer the carrier §2 defined |
| keep the graph and take a **family** `ω_s`, one cochain per size band | **size does not enrich one path space; it gives a family of copies of the same `b₁ = 1` triangle**, each still with two routes |

**The second is the honest reading of what the data would be.** Under it, `π`
within a band degenerates exactly as §22.3 showed, and `π` across bands compares
different carriers, which is discipline 11's problem.

**`π` is therefore constructible only in the first reading, and in that reading
the variation it feeds on is the next question.**

## 46.2 What the size-dependence actually is

`λ(s) − λ(0)` is the extra wedge a larger trade faces. **That is market impact,
and market impact is a cost.**

§24 established the governing distinction on this very carrier: **the published
spread is a cost pinned at the tick, not a measurement floor**, and readings are
taken against the floor rather than the cost. §26.1 and §27.4 established the
sibling prohibition: **the `H⁰` hole may not be added to `λ`.**

> **A `π` built on size-band variation would measure the variance share of
> market impact.** That is a microstructure quantity. It is not a measure of how
> much path-dependence survives conditioning on the state, which is what §22.4
> defined `π` to be.

**So the first reading of §46.1 buys a constructible `π` that is measuring
something else.**

## 46.3 What shape would discriminate, and whether it is observable

The framework's registered extra claim (§7) is that **the hole does not vanish at
any size**. §29 established it institutionally: the Authorized Participant
requirement is **contractual and not size-based**, so no size closes it, and that
was reported rather than estimated.

**Both accounts predict the same shape.**

| | impact account | framework |
|---|---|---|
| `λ(s)` rises with `s` | yes, concave, roughly square-root | yes, the same, since a non-AP pays impact too |
| non-zero intercept as `s → 0` | yes, half the spread | yes, the hole |
| behaviour at `τ = 50,000` shares | nothing | **a discontinuity: at one Creation Unit the loop closes** |

> **The only shape the framework predicts and the impact account does not is a
> discontinuity at `τ`. And it applies to Authorized Participants, whose
> executions are exactly what §29.5 recorded as not observed.**

**For the population that can be observed, the non-AP, the two accounts predict
the same curve**, because §29's hole is a step in membership and not a step in
size.

## 46.4 The answer to §45.3

> **B9-B-2 does not discriminate. It is not built.**

**And §29 had already reported what it was going to establish.** §7 recorded the
extra claim as "the hole does not vanish at any size"; §29.2 established it from
the SAI by the `b1_setup.md` §5 test, at any price and therefore at any size.
**B9-B-2 would have re-established empirically, on a size-filtered sample, a fact
already reported from the instrument's constitution.**

**§45.2's off-exchange blindness is now moot for the decision** and is recorded
anyway: it would have biased the size axis in both tails, which is the one axis
the stage would have been built on.

## 46.5 What this costs, stated plainly

**§7 recorded two routes to the fourth link. This closes one of them.**

| route | status |
|---|---|
| **B9-B's size gradient** | **closed by derivation.** Does not discriminate |
| **a carrier whose gate breathes (LTV)** | **open**, handed to B8 in §28.4, native ground there |

**B9's own remaining path to the fourth link is empty.** That is a result about
the carrier and it is the same result §22.3, §26 and §29 kept arriving at from
different directions: **`b₁ = 1` with a contractual hole gives readings that no
competing account fails to predict.**

## 46.6 What survives on this carrier

| | |
|---|---|
| §21.2 | open, `0.96` standard errors, needs `1,600` days, has `404` (§34.6) |
| **§34.7's forward archive** | **the only instrument still accumulating**, and it accumulates one day at a time |
| D2 on `2020` and `2022` | open, attenuation measured at about a quarter (§44.4) |
| §14.4 cash-in-lieu | **untouched, and now the only unexamined structure on this carrier** |
| §7's fourth link | **reachable from B8, not from B9** |

---

# 47. B9-A-5 runs and fails: nobody was ever required to keep the history

**§35.5's gate, run 2026-08-17.** It asked whether a historical premium and
discount day-count table exists for the main arm, free, covering `2020` and
`2022`.

## 47.1 What was checked and what came back

| source | result |
|---|---|
| `sectorspdrs.com/premiumdiscount` | `302` to the issuer's home page |
| FY2024 annual shareholder report (XLE) | **no such table** |
| FY2018 N-CSR, before Rule 6c-11 | **no such table either** |
| EDGAR N-CSR series, CIK `0001064641`, `2010` to `2024` | the table does not live in these filings |
| iShares historical premium/discount PDF | **exists only for a terminated fund** (ERUS, frozen after `2022`); the live-fund path returns `404` |

> **B9-A-5 fails. §35.5 registered "report it and stop", and that is what this
> is.**

## 47.2 The structural reason, which is the useful part

**Rule 6c-11's website disclosure covers the most recent calendar year and the
quarters since, and it replaced the older disclosure rather than adding to it.**

> **So the historical record was never required to be retained by anyone.** It is
> not that the archive is hard to reach. **There is no archive.**

**This is §34.7's fact seen from a second angle.** §34.7 said the `404`-day
window is a disclosure limit and only grows forward. §47 adds that the past was
not merely un-archived by us; **it was never anyone's obligation to keep**, which
is why no third party has it either.

**The ERUS document is the exception that shows the rule**: a terminated fund's
page freezes, so its last published history survives. **A live fund's page rolls
and the old quarters fall off it.**

## 47.3 What remains for D2 on real stress, with each route's defect named

| route | defect |
|---|---|
| **WRDS / TAQ consolidated NBBO** | **parked** pending access. Would give the disclosed convention directly and would reopen §44, not just D2. §18.3's prohibition was written about B9-A-1 and this is not that, and the reproducibility argument is weaker than the one 陛下 ruled on for a public signup credit: it needs an institutional affiliation |
| **free official closing prices** | **a different measurement, not an extension.** §20.1's series is on the NBBO midpoint; an auction close is a real trade at the bid or the ask. It could be run as its own object with the convention declared, and it would not be D2 continued |
| **another fund family's published table** | **does not exist for live funds** (§47.1) |

**No route is available now.** D2 on `2020` and `2022` stays open and is not
blocked on anything B9 can do this week.

## 47.4 Where that leaves the carrier

| | |
|---|---|
| §21.2 | open, `0.96` se, needs `1,600` days, has `404` |
| D2 on real stress | **open, no free route** (§47.3) |
| B9-B | **closed by derivation** (§46) |
| §7's fourth link | **reachable from B8, not from B9** (§46.5) |
| **§34.7's archive** | **the only instrument still accumulating** |
| **§14.4 cash-in-lieu** | **the only unexamined structure left on this carrier** |

---

# 48. §14.4 closed: the carrier has four edges and `b₁ = 2`, and the quote saying so has been in the record since §16.4

**Derived 2026-08-17 from a document already retrieved. Nothing new was
fetched.**

## 48.1 The provision, in the record since §16.4

§16.4 quoted the Select Sector SPDR Trust SAI, supplement dated `2026-06-12`,
page `48`:

> a fixed creation transaction fee of `$500` for each Fund except XLC; for XLC
> `$250`; an additional charge of up to three times the fixed fee for creations
> outside the Clearing Process, non-standard orders **and cash creations**, for a
> total of up to `$2,000`.

> **"Cash creations" is a named fee category, so a Creation Unit may be
> purchased for cash.** §16.4 used this quote for the per-transaction ambiguity
> and did not read what it says about the graph.

## 48.2 The graph has four edges, not three

§2 built the carrier as `cash → basket → etf → cash`: three vertices, three
edges, `b₁ = 3 − 3 + 1 = 1`.

**With cash creation there is a second way from `cash` to `etf` that does not
pass through `basket`.** Four edges, three vertices:

> **`b₁ = 4 − 3 + 1 = 2`.**

Two independent cycles, and their holonomies:

| cycle | holonomy |
|---|---|
| `C₁` `cash → basket → etf → cash` | `λ₁ = log(P/NAV) − log(1 + f_inkind)` |
| `C₂` `cash → etf → cash` | `λ₂ = log(P/NAV) − log(1 + f_cash)` |
| **difference** | **`λ₁ − λ₂ = log(1+f_cash) − log(1+f_inkind) ≡ δ`, with no price in it** |

## 48.3 The size of `δ`, and it is not small

One XLF Creation Unit at a NAV near `53.69` is worth about `$2.68m` (§16.4).

| | fee | as a fraction |
|---|---|---|
| in-kind | `$500` | `1.86` bp |
| cash, at the stated maximum | `$2,000` | `7.46` bp |
| **`δ` at the maximum** | | **`≈ 5.6` bp** |

> **`δ` is three to four times `λ` itself, which §25.1 measured at `1.2` to
> `1.7` basis points.**

**So the carrier's largest path-dependence is a fee schedule.** And a fee is a
cost, so §24's distinction governs: **`δ` is a cost, `λ` is measured against the
measurement floor, and the two may not be added** for the same reason §26.1
forbade adding the `H⁰` hole to `λ`.

## 48.4 What this does to §22.3

**§22.3 derived `π`'s degeneracy from `b₁ = 1` and "two routes exhaust the path
space". That premise is false.** With `b₁ = 2` there are four traversals per
cell, `±λ₁` and `±λ₂`, not two.

**The conclusion survives and the derivation does not.** Re-derived: `λ₂ = λ₁ − δ`
and `δ` carries no price, so the extra traversals differ from the original pair
by an **offset** rather than by a second source of variation. `π` gains a
constant term and does not gain an axis.

> **§23.3's registered condition, "accumulated `ω` differs for a reason other
> than the route", is met formally and by a constant.** A constant is not a
> second axis, which is the same conclusion §46.1 reached about size bands by a
> different route.

**And `δ` is not observable per transaction**: the SAI says "up to" three times,
at the fund's discretion, and no filing reports what was charged. **So the second
cycle's holonomy is bounded and not measured.**

## 48.5 What this does to §29

**§29's substance is unaffected and its wording is corrected.** §29.1 said "the
`basket → etf` edge of §2's graph is traversable by a member of a contractual set
and by nobody else."

> **Both creation edges are AP-only.** Cash creation is a Creation Unit
> transaction under a Participant Agreement exactly as in-kind creation is, so
> the `H⁰` hole covers `cash → etf` as well. **A non-AP gains no route from
> §48.**

**The hole is larger than §29 described and no easier to cross.**

## 48.6 The defect, which is the reason to record all of this

**The quote was retrieved on the day §16.4 was written, used for the fee band,
and its topological content went unread until §14.4 was finally opened.**

> **Defect fifteen for §8's ledger: a fact was retrieved, quoted, and used for
> one purpose while its consequence for the carrier's definition sat in the same
> sentence unexamined.**

**This is not the same as the other fourteen.** Those were instruments reporting
wrongly. **This is the instrument reporting correctly and the reader taking one
clause out of two.**

## 48.7 §14.4 is closed

| | |
|---|---|
| **cash creation** | **permitted**, a named fee category |
| **`b₁`** | **`2`, not `1`.** §2's graph is corrected |
| **`δ`** | bounded at about `5.6` bp for XLF, **larger than `λ`**, a cost, not observable per transaction |
| **§22.3's conclusion** | **survives, re-derived** |
| **§22.3's premise** | **withdrawn** |
| **§29** | substance unaffected, wording corrected: **both creation edges are behind the hole** |
| **§14.4** | **closed.** No structure on this carrier is now unexamined |

---

# 49. Code audit: three recorded claims are weaker than they read, and no measured number is wrong

**Run 2026-08-17 by two independent adversarial passes over `b9_omega.py` and
`b9a_availability.py`, with every claim below re-verified here against the shipped
code and the result files. Nothing was taken on report.**

> **The audit found no wrong number. It found three tests that could not fail
> and were cited as if they had.**

## 49.1 B9-0 is a tautology, and everything downstream was gated on it

```python
DEGENERATE = ("cash", "etf", "cash")
...
z = path_sum(DEGENERATE, st)          # gate(), and three selftest checks
```

`omega` implements the reversal as `return -omega(v, u, st)` **on the same state
dict**. So `z = −x + x` for one evaluation of `log(price/nav)`.

> **Verified here: `200,000` random legal fund-days, `nav` spanning `e^{−18}` to
> `e^{18}`, `|premium| < 0.24`. Non-zero results: `0`.**

**§6 made `--a1`, `--a2` and `--f1` conditional on `b9_gate.json["passed"]`, and
that field reduces to "at least one fund had a workbook on disk".** The account's
first established row, "B9-0 通过, `6,464` fund-days exactly `0.0`", is `6,464`
evaluations of `−x + x`.

**What it did test**: antisymmetry, which §14.1 enforces by construction. **What
it was documented as testing**, a state dict rebuilt between the legs or a factor
read from the wrong date, **cannot occur**: there is one dict and one call.

**What survives**: the `NaN` guard is real but sits on the **other** path.
Verified: `path_sum(LOOP, {fee: NaN})` returns `nan`. **The gate reads
`DEGENERATE`, not `LOOP`.**

> **Defect sixteen. B9-0 is relabelled from a test to a construction check.**

## 49.2 Two of §32.5's three rows could not fire

| row | requirement | reachable |
|---|---|---|
| `artefact_confirmed` | `≥ 17` of `22` cells under **`0.01`** | **no.** §33 measured the floor at **`0.0933`**. Actual: `6` of `22` |
| `propagation` | `≥ 9` of `11` same sign | **no.** §34.3 proved the cross terms sum to zero across the arm, so mixed signs are forced |
| `neither` | everything else | **the only reachable cell** |

> **The leave-one-out test could only return `neither`, whatever the data said.**

**§43 called that test "void, not negative" on the staleness ground. There was a
second and prior ground: the table was rigged by its own thresholds**, and §43
did not know it.

**This is the third occurrence of defect eleven's family** — a threshold set
without reference to the scale of the thing it judges. §24 was the first, §31.6(1)
the second, §32.5 the third. **The lesson has now cost this stage three times.**

> **Defect seventeen.**

## 49.3 §31.6(2)'s pair check cannot return False

`lx`, `cx` and `ex` come from three `lag1_pairs` calls over the **same** ordered
day list with the **same** keep predicate, and no `value_of` can return `None`.
The three lengths are equal by construction. **Verified: `22` of `22` cells
`True`, and no reachable path to `False`.**

**§43.2 leaned on "`pairs_match` is true in all twenty-two" as evidence that the
closure breach had a cause other than mismatched pairs. That evidence was
vacuous.** The conclusion happened to be right, established later by §33's shift
null, and the reasoning that reached it first was empty.

**The irony is on the record.** §31.6's own selftest demonstrates that closure
misses a halved pair set, `100` against `200` pairs with residual still
`0.0e+00`, and concludes "which is why §31.6(2) is a separate check". **§31.6(2)
was then implemented as a tautology.**

> **Defect eighteen.**

## 49.4 What was checked and found sound

| | |
|---|---|
| **`--recon control` against `--recon recon`** | **identical samples.** `2,304` calm and `2,123` stress fund-days on both sides, `211` and `193` days, and **`0` of `22` cells differ in pair count.** §44's comparison stands |
| `_days_from_civil` | verified against date arithmetic for every day `1900` to `2099`: `0` mismatches |
| `mark_ns` | verified against a timezone library for every day `2007` to `2026`: `0` mismatches |
| the half-cent step histogram | its bucket zero is looser than `HALF_CENT_EQUAL`, **and it did not bite**: the zero-step count equals the exact count to the unit, because the prices are on the grid |
| `--a1`'s attribution truth table | correct across all four quadrants |

## 49.5 Live defects that touch no recorded conclusion

1. **`daily_capture`'s workbook guard is the bug the pdhist branch fixed.** The
   verdict is a literal and the bytes are never re-read, so an HTML error page
   under `spdr-product-data-<day>.xlsx` cements itself and is counted in
   `capture_index.json`. **The archive that §34.7 depends on has this today.**
2. **`nbbo_compare`'s denominator is what was retrieved.** `25` of `6,201`
   registered fund-days never appear, and nothing counts them.
3. **`nbbo_combine`'s coverage guard is per dataset, not per fund-day.** `12`
   fund-days had records in some venue other than Arca and were counted as
   four-venue observations. **And the combination reports no crossed-book
   count**, though max-bid-over-venues with min-ask-over-venues can produce a
   locked or crossed book. §41's reading was taken without that number.
4. **`lambda_series` drops fund-days with four bare `continue`s and counts
   none**, while `--a1` counts its own drops in four named buckets. Every stage
   that consumes it inherits a sample with no denominator.
5. **`--recon` is a no-op for `--a1`, `--a2`, `--gate`, `--f1`, `--grid`,
   `--inputs` and `--depth`**, which never touch `lambda_series`, **and prints
   the mode banner anyway**. `dump_days`, `pi_check` and `gate_speed` do not use
   `out_path`, so a `--recon` run overwrites the stage's own files.
6. **`market_day_order` returns the map it just found to be inconsistent**, last
   writer winning. `decomp` refuses on the clash so nothing acts on it today.
7. **Inert selftest cells in both files**, including `abs(x)/s == abs(x)/s`, a
   `db_key() is None or len(db_key()) > 0` tautology, and a word-boundary matcher
   whose two fixtures are filtered by extension before the matcher runs, so the
   regex the header names as a fixed defect has **zero coverage**.

## 49.6 Disposition

**No measured quantity changes.** `λ` at `1.2` to `1.7` bp, the half-cent grid at
`off-grid = 0.000`, the tick comparison at `15.8×` against `1.42×`, `ρ_c`,
D1, D1b, D2, the `0.8975` and the `0.5564` all stand.

**Three claims are relabelled:**

| was | is |
|---|---|
| "B9-0 passes on `6,464` fund-days" | **a construction check, not a test** |
| "the leave-one-out test returned `neither`" | **it could return nothing else** |
| "`pairs_match` true in all `22`, so the breach had another cause" | **the check cannot be false; the conclusion was reached later and elsewhere** |

**And the standing rule this stage keeps relearning is now stated with its
count**: a check that cannot fail is not a check, and a threshold set without
reference to its quantity's own scale will manufacture a finding. **Three times
in one stage.**

---

# 50. The repair introduced the nineteenth defect, and it was caught by reading its own output

**2026-08-17, within an hour of §49.**

## 50.1 What happened

§49.1 replaced B9-0's tautology with a real assertion: the loop sum through the
cochain must equal an expression written without `omega`, `path_sum` or
`CANONICAL_FACTORS`. **The gate then passed on `6,464` fund-days across `16`
funds, `0` non-zero, `0` skipped — and reported
`worst_abs_cochain_vs_direct = 0.0`.**

**That figure was a branch artefact.** `worst = max(worst, abs(a - b))` sat
inside the `else`, so it accumulated **only on failures**. A clean run left it at
its initial `0.0`, which reads as "the two expressions agree to the last bit."

> **They do not.** Measured here on `200,000` random fund-days: bit-identical in
> **`0.2%`** of cases, **maximum gap `9.67e−16`**. The `1e−12` tolerance is the
> right order and the `0.0` said nothing.

## 50.2 Why it matters more than its size

**Nothing was wrong with the verdict.** The gate did pass, and it passed for the
reason it claims. **What was wrong was a field that reads as a measurement and is
a property of the branch it sits in** — which is defect eleven's family, defect
sixteen's family, and the family §49.6 had just finished naming.

> **Defect nineteen, produced while fixing defects sixteen through eighteen, in
> the same hour, by the same hand.**

**It was caught by reading the output rather than the code**: `0.0` on a
floating-point comparison of two differently-associated logarithms is not a
plausible reading, and that implausibility is what surfaced it.

## 50.3 The repair, and what it now reports

`worst` accumulates on **every** fund-day. The record carries a note saying so,
**and saying that an exactly-zero value there is a branch artefact rather than
agreement**, so the next reader does not have to rediscover it.

## 50.4 The rule, restated with its real count

§49.6 said a check that cannot fail is not a check, three times in one stage.
**§50 adds a fourth occurrence and a sharper form:**

> **A number that can only be produced by one branch is a statement about the
> branch. Read every reported field and ask which branch wrote it.**

**Four times in one stage. The pattern is not the individual mistakes; it is
that they are all the same mistake wearing different clothes.**

---

# 51. The second handover's premise is false against the core table, and the item has to be restated

**2026-08-17, checked before writing any registration for it.**

## 51.1 What §28.4 handed over, and what the data says

§28.4 handed B8 the gate-speed test on a breathing gate, and named LTV:

> 十一个网格里过地板且不靠裁定的只有两个：`ltv_llpa_coarse4` 与 `occupancy`。
> **这两个里只有 LTV 会呼吸**，`occupancy` 是固定属性，是分割不是阈值。

**`experiments/b8_core.py` puts `ltv` in `LOAN_COLS`, whose own comment reads
"Read once, from each loan's first row."** It is the acquisition file's
origination LTV, recorded once and never updated. **It sits in exactly the same
structural position as `occupancy`.**

> **The sentence that distinguished them is false. Neither breathes.**

**And the sharper form**: every one of C9's eleven class grids resolves to
`fico`, `ltv`, `dti`, `fthb`, `occupancy`, `purpose` or `state`, and **all seven
are in `LOAN_COLS`**. **There is no breathing gate among the eleven at all.**

**Defect twenty.** It is defect fifteen's family, one turn worse: fifteen was
reading half of what the instrument said; **twenty is asserting a property the
instrument never claimed**, and asserting it in a document handed to another
stage as an instruction.

## 51.2 The item is not dead, and what it now costs

**The institution does apply a mark-to-market gate.** Flex Modification and its
predecessors evaluate against a current property value, not the origination one.
**So the gate exists; the core table does not record it.**

A breathing LTV is constructible from what is on disk plus one free external
series:

| piece | where |
|---|---|
| `upb`, per month | **`ROW_COLS`, already there** |
| origination value | `upb` at the first row divided by `ltv/100` |
| `state` | `LOAN_COLS`, already there |
| a house price index by state, monthly | **external, free (FHFA), not on disk** |

> **`mtm_ltv(t) = upb(t) / (orig_value × HPI_state(t) / HPI_state(t₀))`**

## 51.3 The defect that construction would carry, named before anything is built

**A state-level index applied to each dwelling is ours, not the servicer's.**
Within-state dispersion in house prices is large, so the constructed gate is a
proxy for the gate the institution applies.

> **If modifications then track the constructed LTV, that is consistent with
> them tracking house prices, which is not the same claim as tracking the gate.**

**This is §45.3's standing rule arriving one level earlier than it did for
B9-B.** There the question was what the reading would discriminate. **Here the
prior question is whether the gate exists in the data at all, and the answer is
that it exists institutionally and not in the record.**

## 51.4 The item, restated

| was | is |
|---|---|
| "LTV is the breathing gate, `ltv_llpa_coarse4`, min cell 82, zero exclusions" | **C9's grid is origination LTV and does not breathe. The census numbers stand; the property claimed of them does not** |
| "run the gate-speed test on it" | **first construct a mark-to-market LTV from `upb`, `state` and an external house price index, and declare the proxy** |
| implied cost: a run | **actual cost: an external series, a join, a proxy declaration, and only then the test** |

**What survives from §28.4 unchanged**: the price direction is still reversed
against A3 (`claims ≥ γ·P` tightens when price rises; `LTV = balance / value`
tightens when value falls), and the two margins are still the ones §28.2·1
wrote. **What does not survive is that the gate was ready.**

## 51.5 Why this is recorded here and not in B8's documents

**The error is B9's**, in B9's own handover file, written from C9's census
without checking which table the field lives in. **B8 was handed an instruction
with a false premise and this is the correction, issued by the stage that issued
the instruction.**

---

# 52. The second handover cannot discriminate either, and both of §7's routes are now closed

**Derived 2026-08-17 under §45.3's standing rule, before any pipeline. The
rulebook was read rather than remembered.**

## 52.1 What the Servicing Guide says

Fannie Mae Servicing Guide **D2-3.2-06, Fannie Mae Flex Modification**, current
version:

1. **The eligibility table contains no LTV criterion.** "In order to be eligible
   for a Fannie Mae Flex Modification, all of the criteria in the following
   table must be met", and no loan-to-value threshold appears among them.
2. **MTMLTV is a post-modification quantity.** "The servicer must determine the
   **post-modification** MTMLTV ratio, which must include capitalized
   arrearages."
3. **The valuation is servicer-ordered**, by the *Obtaining a Property
   Valuation* procedure, **not an index.**

## 52.2 What that does to §28.4's mapping

§28.4 mapped A3 §6.4d onto the mortgage carrier as: **LTV gates the extensive
margin (the wall), and the intensive margin is roughly flat.**

> **The rulebook says the opposite. LTV is not an eligibility criterion, so it
> gates nothing extensively; and MTMLTV enters the terms, so it touches the
> intensive margin by formula.**

Against §28.2·2's registered disposition table, copied there from B9 §26.6:

| reading | filed as |
|---|---|
| extensive collapses, intensive flat | A3's wall reproduced |
| both collapse equally | gradual, not a wall |
| **intensive collapses, extensive flat** | **auction, exactly what A3 §6.4d says it is not** |
| **extensive does not collapse** | **A3's mapping falsified here too** |

> **The Servicing Guide fixes rows three and four before a single loan is read.**

**So the test would report the rulebook.** That is §46.4's shape a second time:
a stage that would establish empirically what the instrument's own constitution
already states. **§45.3's rule caught it, which is what §45.3 was written for.**

## 52.3 And the proxy problem is worse than §51.3 said

§51.3 registered that a state index applied per dwelling is our proxy rather
than the servicer's gate. **The Guide says the servicer orders a valuation.**

> **So the constructed MTM-LTV is not a noisy version of the quantity the
> institution uses. It is a different quantity**, and the one the institution
> uses is not in the record at any resolution.

**A regression-discontinuity repair fails for the same reason**: a discontinuity
at a threshold can only be seen in the variable the rule reads, and that variable
is a servicer-ordered appraisal that the data does not carry.

## 52.4 One rescue considered and rejected

**The rulebook changed across the sample.** The archives span `2002` to `2019`,
so pre-crisis, HAMP and Flex are all present, and HAMP's forbearance did
reference an LTV target. A design could use the rule change as the variation.

> **Rejected: that tests the rule change.** It measures when a written rule took
> effect, which is dated in the Guide and needs no data.

## 52.5 §7's fourth link now has no registered route

| route | status |
|---|---|
| **B9-B's size gradient** | **closed by derivation** (§46.3): impact and framework predict the same curve, and the only distinguishing shape lives at `τ`, on a population §29.5 recorded as unobserved |
| **a carrier whose gate breathes** | **closed by derivation** (§52.2): the named gate is not an eligibility rule, and the rulebook fixes the outcome |

> **Both routes registered in §7 are closed, each for a structural reason, and
> neither closed because a measurement came back negative.**

**This is the honest state of the chain**: formal object → real carrier →
measurable non-zero → **economic state dependence that no competing account also
predicts**. The first three links hold on B9's carrier and on B8's. **The fourth
has no route on either.**

## 52.6 What a route would have to look like, derived rather than hoped for

From §46.3 and §52.2 together, a gate that could discriminate must be all three:

1. **price-responsive**, so that it breathes (§27.5's requirement, unchanged);
2. **recorded per period in the data**, so the breathing is observable;
3. **not written in a rulebook**, so that measuring it is not reading the rule.

**The third is the one both closed routes failed.** AP status is contractual;
Flex eligibility is a published table. **A gate an agent applies against a market
price, rather than one an institution publishes, is what is missing.**

**One candidate exists in the data already and it belongs to a different stage**:
`rate` is in `ROW_COLS` and therefore breathes, the market rate is free and
external, and the refinance decision is a threshold an agent applies against a
price that no institution sets. **Named here so the search is not started from
nothing, and not begun here.**

---

# 53. The refinance candidate, one better candidate it turned up, and why the fourth link's prediction is the wrong kind

**Derived 2026-08-17. No data touched. §45.3's rule applied at the earliest
point, which §52 showed is where it pays.**

## 53.1 The refinance gate passes §52.6's three conditions and fails on a fourth

§52.6 required a gate that is price-responsive, recorded per period, and **not
written in a rulebook**. Refinancing clears all three:

| condition | refinancing |
|---|---|
| price-responsive | **yes.** The gate is `rate_loan − rate_market ≥ threshold` and the market rate is a price |
| recorded per period | **yes.** `rate` is in `ROW_COLS`; the market rate is free and public back to 1971 |
| **not in a rulebook** | **yes.** No institution publishes a refinancing threshold. Streamlined programs have criteria; ordinary refinancing has none |

**It fails on a condition §52.6 did not think to state.**

> **The intensive margin is unobservable.** A refinanced loan leaves the data
> as a `zero_bal` code and the new loan is a different record in a different
> cohort with no link. **What the refinancer received is not in the file at any
> resolution.**

**So the two-margin test cannot run**, and the failure is about the record rather
than about the economics. **§52.6's list was incomplete and is amended: a
candidate needs both margins observable in the same record.**

## 53.2 That amendment turns up a better candidate, on B9's own carrier

Applying all four conditions at once:

| | modification (§52) | refinancing (§53.1) | **ETF creation, the arbitrage threshold** |
|---|---|---|---|
| price-responsive gate | no, LTV is not an eligibility rule | yes | **yes: an AP acts when `premium ≥ cost`** |
| recorded per period | yes | yes | **yes: premium daily, `pdhist`** |
| not in a rulebook | **no** | yes | **yes: the AP's own threshold, not published** |
| **both margins observable** | yes | **no** | **yes: shares outstanding, daily, the series §16.2 earned `τ` from** |

> **It is the only candidate of the three that clears all four, and it is the
> carrier B9 already holds.**

**And §26 did not test this gate.** §26 mapped A3's gate to **AP eligibility**,
which §27.3 then measured as not breathing. **The AP's decision threshold is a
different object and it does breathe**, because the premium does.

## 53.3 And it fails, on the fact that earned `τ`

Extensive would be whether a creation happens at all; intensive would be its
size. A3 §6.4d predicts the extensive collapses far faster.

> **§16.2 measured `τ = 50,000` shares from the gcd of in-window changes. The
> creation unit is indivisible.**

**So as the premium falls toward the cost, an AP cannot do a smaller creation.
It does at least one unit or none.** The extensive margin collapses and the
intensive stays pinned at the unit, **by indivisibility, for any account
whatever.**

**The measurement that earned `τ` is the measurement that makes this gate
non-discriminating.** A3's wall and a lot size produce the same shape, and the
data cannot say which produced it.

## 53.4 Three closures, and the pattern they make

| | why it closed |
|---|---|
| **§46**, B9-B's size gradient | impact and the framework **predict the same curve** |
| **§52**, the LTV gate | **the rulebook fixes the answer** before any loan is read |
| **§53**, the arbitrage threshold | **an indivisible lot produces the predicted shape** for an unrelated reason |

**Three distinct reasons, and one thing in common.**

> **A3 §6.4d predicts a *shape*: the extensive margin collapses faster than the
> intensive. Shapes are cheap. Impact curves, published eligibility tables and
> lot indivisibility each produce that shape without the framework being true.**

**A prediction discriminates when a competing account gets it *wrong*, not when
a competing account also gets it right.** A rate is a shape; **a sign is not.**

## 53.5 The stage has built exactly one test of the right kind, and it lost

**§26 is the only prediction anywhere in B9 registered with opposed signs**: A3's
mapping said the extensive margin falls, the flow account said it rises, and the
two could not both be right.

**It ran, and it landed on the flow account's side**: extensive fell in ten of
eleven, and §27 filed it there. **The structural reason was that AP status does
not breathe** — which §53.2 now shows was a property of the gate §26 chose, not
of the carrier.

> **So the honest position is not that the fourth link is untested. It is that
> the one properly discriminating test built for it was aimed at the wrong gate
> and lost, and every route since has failed at the design stage for predicting
> a shape.**

## 53.6 Disposition, and the one thing §53 leaves open

**Closed**: refinancing (§53.1, the intensive margin is not in the record) and
the arbitrage threshold (§53.3, indivisibility gives the shape for free).

**Open, and it is the only thing §53 leaves open**: **redo §26's opposed-sign
design against the AP's decision threshold rather than AP eligibility.** The
sign, not the rate, is what would have to be registered, and what the two
accounts disagree about on that gate has not been derived here.

**Not started.** §45.3's rule applies to it as to everything else: **derive the
opposed signs first, and if they cannot be derived, do not build it.**

---

# 54. The catalogue had no NBBO either, which explains §38 to §44 better than anything §41 or §42 offered

**2026-08-17, amending §45.1.**

## 54.1 What §45.1 said and what it should also have said

§45.1 enumerated the vendor's whole catalogue and reported: **no FINRA, TRF, ADF
or OTC dataset.** That was correct and it was half the finding.

> **There is also no consolidated NBBO.** No CTA, UTP or SIP product appears
> anywhere in the twenty-nine.

The three composites are not it and could not reach the target period anyway:

| | is it the SIP NBBO | start |
|---|---|---|
| `EQUS.MINI` | **no**, the vendor's own words are "synthetic **mini** NBBO" | `2023-03-28` |
| `DBEQ.BASIC` | no, a partial-venue composite | `2023-03-28` |
| `EQUS.SUMMARY` | no, end-of-day consolidated **closing prices** | `2024-07-01` |
| the fourteen venue feeds | each venue's own BBO | four reach `2018-05-01` |

## 54.2 This explains the whole arc more cleanly than its own sections did

**§38 to §44 never held the NBBO, at any point, from any source used.** §41's
four-venue best was four of fourteen, **and all fourteen would still not be the
NBBO**: the national best bid and offer has round-lot requirements, quote-
condition filters and the SIP's own sequencing, none of which venue feeds carry.

> **§41.2 offered asynchrony and withdrew it (§42.1). §42.3 offered odd lots and
> could not test it (§43). The plain reason was upstream of both: the object was
> never in hand.**

**This does not change any verdict.** §38, §40, §41 and §44 all failed and stay
failed. **It changes what they were failing at**, and it is worth recording that
neither §41 nor §42 reached for it.

## 54.3 What is in hand, and it is exactly `404` days

§24.1 measured that every reconstructed close lands on the half-cent grid across
sixteen funds and `404` days, `off-grid = 0.000`, **and that is what identified
the disclosed price as the closing NBBO midpoint.**

> **`disclosed_price` in `results/b9_days.json` is `6,201` fund-days of true
> closing NBBO midpoint.** It is the ground truth §36 was designed around, and
> it is the only NBBO this stage has ever held.

## 54.4 What institutional access reopens, and what it does not

**The TRF half reopens nothing.** It was sought for B9-B, and §46 closed B9-B on
discriminating power. **Data does not repair a prediction that a competing
account also makes.**

**The NBBO half reopens a great deal, and the machinery is already built:**

| | |
|---|---|
| **§36's gate** | re-runs as `--nbbo-compare`, unchanged |
| **§40.3's B9-A-7** | re-runs as `--recon control` against `--recon recon`, identical samples, differing only in the price |
| **if both pass** | the binding constraint moves from the price to the NAV history: `navhist` carries `5,734` rows, about twenty-two years. **§34.6 asked for about `1,600` trading days** |
| **what that puts on real stress** | `ρ_c`, `V_e`, `V_c`, D1, D1b and D2 across `2008`, `2020` and `2022`, which answers §35.4's objection with range rather than with argument |
| **§12.1** | relaxes further: a quote feed carries the spread at any instant, so §37.3's note that the ruling of 甲 is reopenable gains a second source |

**What it does not reopen**, and each was closed by derivation rather than by
data: **`π`** (§48), **§7's fourth link** (§46, §52, §53), and the issuer-side
series — the published `30`-day median spread, the fee, shares outstanding.

> **More data measures the same quantities better. It does not turn a prediction
> a competing account also makes into one it gets wrong.**

---

# 55. The two zeros, and why this stage's wedge is not one of them

**Ruling, recorded 2026-08-17. Nothing was run for it.** It is here because the
stage is named for zero holonomy and every reading it took is non-zero, so a
reader is entitled to ask where the zero is. **No verdict below is new; every
number is §18.5, §24 or §25.1.**

## 55.1 Two zeros, and §24's discriminator is what separates them

| | the statement | this stage |
|---|---|---|
| **mathematical zero** | `λ ≡ 0` on every cycle: `ω` is exact, a potential exists, closed walks cancel | **no.** `1.05` to `5.08` times `F_m`, `11/11` at `f = 0` (§25.1) |
| **economic zero** | `\|λ\| / F_c ≤ 1`: the wedge exists and no one can act on it | **yes, and it is measured: the main arm reads about `1`** (§18.5) |

The separation is §24's, and it is the same discriminator that falsified
quantisation: **a measurement floor falls when the measurement improves, a cost
floor does not.** Two floors, two zeros, **and a reading has a size only against
one of them.**

> **The main arm's reading is that the wedge is about the size of the cost of
> removing it.** That is the empirical content of no free lunch, **and it is a
> different sentence from `λ = 0`.**

The comparison arm at `17` to `28` is the control and it points the other way:
that premium is stale-NAV measurement, **not an opportunity** (§20.3).

## 55.2 Improving the measurement moves away from the mathematical zero

By §24.8, `F_m` falls when the instrument improves and `λ` does not follow it
down. **So no improvement in measurement can produce a mathematical zero here.**
It can leave `|λ| / F_m` where it is or raise it.

**One correction to how this was first stated.** Obtaining TAQ does **not** lower
`F_m` for the reading actually taken, because §54.3 established that
`disclosed_price` **already is** the closing NBBO midpoint. The closing price is
not improvable, it is the object. What an intraday NBBO buys is a **different**
price object, an average over many midpoints whose quantisation error falls as
`1/√n`, **and that is what would lower the floor.** §25.1's generous corner
already carries the one-sample version of this, `F_m/√12`.

**The looser first version was written into the stage report before this section
was drafted, and is carried in the ledger as defect twenty-one**, caught by
reconciling a new section against §54.3 rather than by any guard. **The sign and
the verdict did not move; the mechanism was wrong.**

> **The sign is the same either way, and it is the point: §54.4's route leads to
> a more distinguishable non-zero, never to a zero.** Anyone expecting better
> data to close this gap has the discriminator backwards.

## 55.3 Where a mathematical zero lives, and it is not this carrier

`λ ≡ 0` is a property of **how the prices are made**, not of how well the market
clears. It holds by construction wherever one leg is **derived from** the others
rather than quoted against them.

> **The standard case is a cross rate computed from two majors: the triangle
> closes identically, to the last digit, because the third quote was never
> independent.** The same instrument family also carries independently made
> crosses, **and those do not close.** A family holding both is a calibration:
> the same machine reads exact zero on one member and non-zero on another.

**This carrier cannot supply it**, and the reason is structural rather than
effort: `b₁` is small (§48 raises it to `2`, not further), there is no grid to
vary (§14 is why §1.1 does not bite here), and **every edge has someone charging
for it** (§16.4's fee interval, §48's `δ ≈ 5.6` basis points). **No member of
this family has a derived third leg.**

**This is a statement about where to look. B9 does not open it and does not
claim it.**

## 55.4 Standing prohibition

**The wedge may not be reported as a found zero.** A reading of `1.05` to `5.08`
against `F_m` is a non-zero, and calling it zero is reading it against the wrong
floor — **the error §24 charged this stage for once and §33 charged it for a
second time.**

**What it may be reported as, and this is worth as much:**

> **the main arm sits at about `1` against `F_c`, which is direct evidence the
> wedge was not left on the table.** The framework's non-zero and the market's
> no-arbitrage **both hold here and do not conflict**, because they are distances
> to two different floors.

**Any later stage citing §18.5 or §25.1 must carry the floor with the number.**
A ratio without its denominator is not a reading.
