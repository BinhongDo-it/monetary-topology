# B2 loop B: the vintage wedge, and why it is a different object

Pre-registration. **Written before any NMDB file was retrieved.** The retrieval
script `data/fetch_nmdb.py` was written in the same edit and every filter below is
fixed here.

Companion to [`b2_measurement.md`](b2_measurement.md), which pre-registered loop A,
and [`b1_theorem.md`](b1_theorem.md), which is what makes this document say
something the earlier design could not.

---

## 1. What loop B is for, and what it is not for

Loop A established that the effective cost field carries an agent index: at a fixed
position and date, terms differ by who is transacting. That is the logical claim
and it is settled.

Loop B was always described as carrying the **magnitude**: hold the dwelling fixed
and vary the entry date, and the differences are much larger than anything loop A
sees. What the earlier documents could not say was *what kind* of quantity that
magnitude is.

The B1 theorem answers it, and the answer is not the flattering one.

**Loop A's dispersion is holonomy.** A dwelling is transferable at one market
price, so the agent edge `(a,g)–(b,g)` exists with weight zero, the four-cycle
closes, and its sum is a genuine obstruction. Theorem 3 makes the within-cell
variance literally half the mean squared cycle sum.

**Loop B's dispersion is not.** A 3% mortgage originated in 2021 cannot be
transferred: conventional loans are not assumable. The agent edge is **absent**,
`Γ` disconnects in the agent direction, and the square is not a cycle. Whatever
loop B measures, it is not a cycle sum. It is the separation between connected
components — an `H⁰` statement where loop A's is `H¹`.

So the two numbers have the same units and the same algebraic form, and they are
different objects. Saying so is the point of this stage. **Reporting the larger
number as though it were the stronger evidence would be exactly the error this
project exists to avoid.**

---

## 2. What was known before this was written

Recorded because the honest version of a pre-registration says what the author
already had in hand.

- `b2_measurement.md` already cites FHFA's figures for the share of outstanding
  fixed-rate mortgages below 4%: 65.1% peak in 2022 Q1, 49.9% in 2026 Q1.
- While checking whether the data existed at all, a search result stated that at
  2024 Q1 there were 50.8 million outstanding mortgages, **21.9% with rates below
  3% and 14.3% at or above 6%**. That figure was read before this document was
  written.
- Loop A's results are complete and public in this repository.

So the **rough level** of the outstanding rate distribution was known. What was not
known, and what is registered below: the value of the dispersion bound, its
behaviour before 2022, its variation across states, and its size relative to loop
A. No NMDB file had been downloaded, and no state-level or quarterly series had
been seen in any form.

---

## 3. The measurement

FHFA's NMDB Outstanding Residential Mortgage Statistics report, per geography and
quarter, the share of outstanding mortgages in five contract-rate buckets:

```
B1 = [0, 3)    B2 = [3, 4)    B3 = [4, 5)    B4 = [5, 6)    B5 = [6, ∞)
```

Binned data cannot give the dispersion. It can give a **rigorous lower bound**, and
the bound has the same algebraic form as Theorem 3, which is what makes the
comparison to loop A meaningful rather than rhetorical.

For independent copies `X, X'` of the rate distribution,

```
Var(X)  =  ½ · E[(X − X')²]
```

which is Theorem 3 stated without any graph, because the identity is algebraic. If
`X ∈ B_b` and `X' ∈ B_c` with `c > b`, then `X' − X ≥ l_c − u_b`, so

```
Var(X)  ≥  Σ_{b < c}  p_b · p_c · d(b,c)²        d(b,c) = max(0, l_c − u_b)
```

Adjacent buckets contribute nothing, because two loans in adjacent buckets can be
arbitrarily close. Only the gaps count:

| | B2 | B3 | B4 | B5 |
|---|---|---|---|---|
| **B1** | 0 | 1 | 2 | 3 |
| **B2** | | 0 | 1 | 2 |
| **B3** | | | 0 | 1 |
| **B4** | | | | 0 |

The open top bucket is treated as starting at 6 and extending upward, which only
discards mass and can only lower the bound.

### Why a lower bound rather than a point estimate

Three reasons, in order of how much they matter.

It is the conservative direction. The framework wants this dispersion to be large.
A bound that can only understate it cannot be accused of being constructed to
flatter the claim.

It requires no distributional assumption. Fitting a within-bucket shape — uniform,
log-normal, anything — would put the answer partly in the assumption, and with five
buckets and an open top the assumption would be doing real work.

It is exact. The bound is not an approximation whose error has to be argued about.
Every configuration consistent with the reported shares has variance at least this
large, including the configuration that minimises it.

---

## 4. The comparison, and its one soft joint

Loop A reports a size-weighted mean within-cell variance of **0.3363** at
`min_size = 20`, in squared percentage points. Loop B's bound is in the same units.
Both are half a mean squared pairwise difference. They can be compared directly.

The soft joint is that the two measure slightly different variables. Loop A's is
the variance of **rate spread**, APR minus the average prime offer rate at the
rate-set date; loop B's is the variance of the **contract rate** itself.

```
Var(spread)  =  Var(APR) + Var(APOR) − 2·Cov(APR, APOR)
```

Within a tract-year, APOR moves with the market — in 2022 it moved a great deal —
and the subtraction removes exactly that common movement. So loop A's number is
**below** the within-cell variance of APR, which means the comparison understates
loop A relative to loop B rather than the reverse. The bias runs against the
prediction registered in L1, and is recorded here rather than discovered later.

A related point, and the one a critic should press. Loop B's dispersion **is** the
rate cycle: vintages differ because the market rate differed when they entered.
That is not a defect in the measurement, it is the mechanism. A rate cycle would
not leave a permanent cross-sectional wedge in the carrying cost of the *same
position* if the position could be transferred. The cycle supplies the variation;
the missing edge is what makes it persist. **L2 is what tests that reading**, by
asking whether the bound is positive in periods when the cycle was quiet.

---

## 5. Pre-registered predictions

Computed on `MARKET = "All Mortgages"`, `VALUE1` (loan-count weighted, matching
loop A's weighting), suppressed rows dropped.

**L1.** The national bound exceeds loop A's within-cell variance of `0.3363` in the
most recent quarter available. Direction registered; magnitude not.

**L2.** The bound is strictly positive in **every** quarter from 2013 Q1, including
the quarters before the 2022 repricing. This is the one that distinguishes a
structural wedge from one episode, and it is the prediction most likely to fail.

**L3.** The bound is strictly positive in all 51 state-level geographies in the
most recent quarter.

**L4.** Null calibration: a synthetic stock with all mass in one bucket returns a
bound of exactly `0.0`, and a synthetic stock split evenly between `B1` and `B5`
returns exactly `0.25 · 9 = 2.25`. Both are checked in code before the real series
are touched.

**Not registered, reported and not interpreted.** The wedge between the
new-origination rate and the outstanding average rate. It is reported because it is
the quantity readers will expect, and it is not interpreted because a stock's
average rate differs from the current market rate whenever rates move — that is
arithmetic, not an obstruction, and treating it as evidence would be the mistake
section 1 is about.

---

## 6. Falsification

| observation | consequence |
|---|---|
| the bound is below loop A's within-cell variance | Loop B is the *smaller* channel. The claim that loop B carries the magnitude, in `b1_setup.md` §3 and `b2_measurement.md` §1, is **withdrawn and rewritten**, and the withdrawal is recorded in this document rather than removed from the earlier ones. |
| the bound is zero or negligible before 2022 | The wedge is one repricing episode rather than a structural feature. Loop B is restated as an event study and the compounding argument loses its per-period reading. |
| the bound is positive nationally but vanishes in most states | The national figure is composition across states rather than dispersion within them. The claim must move to whichever geography survives. |
| the bound is large but tracks the new-origination rate one-for-one with no persistence | The wedge closes as fast as the cycle turns, and no component separation survives. Same consequence as the second row. |

---

## 7. Sample and filters, fixed here

| field | value | why |
|---|---|---|
| dataset | NMDB Outstanding Residential Mortgage Statistics, quarterly | the only public series with the rate distribution of the *stock* |
| period | 2013 Q1 – 2026 Q1 | the full published range; no window is chosen |
| `GEOLEVEL` | `National` for L1/L2, `State` for L3 | |
| `MARKET` | `All Mortgages` headline; `Conventional Market` reported alongside | loop A is conventional, so the second is the like-for-like comparison |
| `SERIESID` | `PCT_INTRATE_LT_3`, `PCT_INTRATE_3_4`, `PCT_INTRATE_4_5`, `PCT_INTRATE_5_6`, `PCT_INTRATE_GE_6`, `AVE_INTRATE`, `TOT_LOANS` | |
| weighting | `VALUE1` headline, `VALUE2` robustness | `VALUE1` is loan-count weighted, matching loop A |
| `SUPPRESSED` | rows with `1` are dropped and **counted** | fewer than three sample loans; the count goes in the result record |
| new-origination rate | NMDB New Residential Mortgage Statistics, quarterly, `AVE_INTRATE`, `All Mortgages` | only for the unregistered wedge and for L2's bookkeeping |

A quarter is used only if all five bucket shares are present and unsuppressed and
sum to within 1 percentage point of 100. Quarters failing that are dropped and
reported, never patched.

---

## 8. What loop B cannot do

**It is not evidence of non-integrability.** Section 1 is the whole point. The
agent edge is missing, so there is no cycle, so there is no holonomy. Loop B
measures how far apart the components are, which is a different and weaker
statement about a different cohomology group.

**It cannot separate the mechanism from the cycle.** The dispersion exists because
rates moved and because the position cannot be transferred. This design tests the
second through L2's persistence requirement, which is indirect. A direct test would
need a jurisdiction where mortgages *are* assumable, and would compare. That is not
available in this data and is not attempted.

**It says nothing about welfare.** A holder with a 3% loan is better off than one
with a 7% loan on the same dwelling. That the two cannot trade into each other's
position is a statement about the reachable set, not about whether either outcome
is deserved or efficient.

**The bound is loose and known to be loose.** Five buckets with an open top throw
away most of the information in the distribution. A tighter figure would need
loan-level data, which the public NMDB release does not provide. The looseness runs
in the conservative direction, which is why it is tolerable, not why it is
invisible.

---

## 9. Changes after pre-registration

| what changed | when | why | effect |
|---|---|---|---|
| series namespaced by source file in the loader | before any result was read | the outstanding and the new files both publish `AVE_INTRATE` for the same geography, market and quarter, so an unnamespaced key let whichever loaded last overwrite the other | none on any criterion, which read only bucket shares. It did put the new-origination rate in the slot labelled "outstanding average" in the first draft, which would have been a wrong number in the reported-not-interpreted section |

No change was made after a result was read. No bucket edge, weighting, market,
geography or period was touched at any point.

---

## 10. Results

All four predictions passed. 53 quarters, 2013 Q1 to 2026 Q1, `VALUE1` weighting,
`All Mortgages`, no suppressed rows in the retrieved sample.

| | value |
|---|---|
| latest quarter bound (2026 Q1) | **0.8479** (sd 0.9208) |
| smallest across all quarters | **0.3018** (2019 Q4) |
| largest | 0.8479 (2026 Q1) |
| loop A within-cell variance | 0.3363 (sd 0.5799) |
| quarters at or above loop A | **46 of 53** |
| mean before 2022 | 0.4043 |
| smallest from 2022 onward | 0.4478 |
| ratio of means, 2022 onward against before | **1.64** |
| states positive at 2026 Q1 | **51 of 51**, from 0.7549 (HI) to 0.9245 (SD) |

### What L2 turned out to say

L2 was registered as the prediction most likely to fail, because a wedge visible
only after the 2022 repricing would be an episode rather than a structural
feature. It did not fail, and the margin is larger than the criterion required.

**The 2022 repricing raised the wedge by 64% and did not create it.** The mean
bound over the 36 quarters before 2022 is 0.4043, which already exceeds loop A's
0.3363, and the smallest quarter from 2022 onward is above the largest quarter
before it. The dip to 0.3018 in 2019 Q4 is the only period where the vintage
channel falls materially below the agent channel.

### The comparison, stated carefully

The vintage bound is 2.52 times loop A's within-cell variance in the latest
quarter. Three things have to be said with that number and none of them are
optional.

**It is a lower bound and a loose one.** On a synthetic sample whose variance is
known, the five-bucket bound recovers about 27% of it. The true vintage dispersion
is plausibly three to four times what is reported here.

**The comparison is not clean in one direction.** Loop A measures the variance of
rate spread, which nets out the common movement in APOR and therefore sits below
the within-cell variance of APR. So loop A is understated relative to loop B by an
amount this design does not quantify.

**It is the smaller number that carries the argument.** Loop A's 0.3363 is a
holonomy: Theorem 3 makes it half the mean squared four-cycle sum on a graph where
the cycle closes. Loop B's 0.8479 is not, because a below-market mortgage cannot
be transferred, so the agent edge is absent and there is no cycle to sum around.

**The larger effect is the weaker evidence.** That is worth saying plainly because
the temptation runs the other way, and because a reader who takes the 2.52 as the
headline has been handed a number about `H⁰` and told a story about `H¹`.
