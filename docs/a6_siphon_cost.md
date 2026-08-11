# A6: what the siphon costs in redistribution, and whether topology is cheaper than quantity

Pre-registration. **Written before any A6 code existed.** Every switch,
parameter, outcome measure and threshold below is fixed here.

Uses stage A2's graph, stage A4's `uniform_access` switch and stage A0's
zero-issuance rule. It does not use the asset channel, so it depends on nothing
in A3 or A5.

---

## 1. The question

The source framework's earlier treatment has no access layer: money circulates
the whole economy and reaches everyone. This model has one, and the difference
is the subject.

The claim under test is the framework author's:

> Access itself creates a siphon, so even a *fair* retention rate keeps
> accumulating upward. Therefore more redistribution is needed than a model
> without access would call for. And if the extra redistribution exactly equals
> the siphon, a closed economy runs forever with no new money issued at all.

Every clause of that is measurable here, and the measurement has a unit: the
**tax rate that just holds the economy open**. Call it `R*`.

The stage also puts a second question next to it, because the machinery makes
the comparison free and the answer is the framework's own thesis stated as
policy: **is it cheaper to move claims or to change the graph?**

---

## 2. What "holding the economy open" means

**The support set must not contract. Nothing else is required.**

The measure is stage A2's effective support, `1 / HHI` of the inflow
distribution: threshold-free, continuous, and already the headline of that
stage. `R*` is the smallest tax rate at which its trend over the run is not
negative.

**The Palma ratio is reported and is not a criterion.** A closed economy
guarantees that no new money is needed. It does not guarantee where the money
sits at any given moment. Requiring the distribution to be stationary would be
requiring something the claim never made, and would almost certainly make `R*`
unreachable for a reason that has nothing to do with the siphon. Its shape is
expected to move and the movement is reported.

**Palma rather than the Gini, and why it is not an arbitrary swap.** The Palma
ratio is the top decile's share of holdings over the bottom four deciles'. On
this model's two hundred nodes split twenty to one hundred and eighty, **the top
decile is exactly the financial layer**, so Palma reads as the financial layer's
holdings over the poorest forty percent of the production layer's. It is the
model's own structure rather than a statistic imported over it. The Gini, by
contrast, is least informative precisely in the middle, which is where this model
has least to say, and most sensitive to redistribution among agents whose
position in the graph is identical.

**The Pareto index is a conditional secondary.** Where the top tail is heavy
enough to estimate, `α` is reported as a robustness note. It is not primary,
because a Hill estimator on the twenty nodes of the financial layer is too thin
to carry a claim, and reporting it as though it were would be inventing precision
the sample does not have.

That distinction is the whole reason this stage measures what it measures.
Circulation reaching everyone and wealth being evenly held are different
properties, and the framework's claim is about the first.

---

## 3. The two redistribution channels

Both are funded identically: a **progressive tax on holdings**, levied each round
at rate `R` on the financial layer only. What differs is where the proceeds go
and what they do.

### Arm T — transfer

Proceeds are divided **equally per capita** across the production layer and added
to holdings. Flat rather than proportional, for the same reason the opening
allocation's proceeds are flat elsewhere in this repository: a proportional
rebate would concentrate as it redistributes, and would put part of the answer
into the setup.

Claims move. The graph does not.

### Arm I — infrastructure

Proceeds are paid to the production layer as **payment for building**, so claims
move exactly as in arm T and conservation holds identically. The difference is
what the building does: it **permanently reduces the production layer's upward
leakage**, the share of each node's spending that terminates in the financial
layer, by an amount proportional to the cumulative investment.

The accounting is the one the framework's author sets out. Infrastructure is not
household wealth and is not added to any household's holdings. What it does is
make households need to spend less, and it does so mainly for ordinary
households rather than for the very rich, which is what licenses treating it as
common property rather than as somebody's asset.

Claims move exactly as in arm T. **The graph changes.**

### Why the pair is the point, and what it is not

Both arms are **topological interventions**, and saying otherwise was an error in
an earlier draft of this document. Redistribution is an edge: a channel running
from the top of the graph to the bottom that was not there before. Arm T **adds a
downward edge**. Arm I **attenuates the upward ones**. Neither is "quantity
against topology"; the question is *which edges*, which is a question entirely
inside the A track's own terms.

The distinction that does the work is what happens next. Claims delivered by the
new downward edge leak back up along the old upward edges at the rate those edges
always had. Attenuating those edges lowers the rate itself, so the same claims
stay in circulation longer. So arm T has to keep paying and arm I does not.

If arm I sustains the support set at a lower tax rate than arm T, that is the
framework's thesis in a form a finance ministry could act on: **where you put the
edge matters more than how much you push through it.** If it does not, the thesis
is decorative at the point where it would matter most.

---

## 4. The factorial

| switch | on | off |
|---|---|---|
| access | stage A2's stratified graph | `uniform_access`: complete graph, uniform terms |
| retention | stratified: the source's per-layer propensities | **fair**: one propensity for every node, at the claim-weighted mean |
| channel | arm T, transfer | arm I, infrastructure |

Issuance is **off** in every cell. That is what makes `R*` a measurement of the
economy rather than of the monetary authority.

**Fair retention** is one propensity for all nodes, set at the claim-weighted
mean of the two layers' values, which is the same construction stage A4 already
uses when it flattens access. It is implemented as a switch of its own so that
retention and access can move independently, which stage A4 could not do because
there the two were deliberately one object.

---

## 5. Pre-registered predictions

**A6-1 — there is something to fix.** With `R = 0` and no issuance, the support
set contracts in every cell: the trend of `1 / HHI` over the run is negative.
A floor. If a closed economy holds itself open with no redistribution at all,
nothing below is worth measuring.

**A6-2 — `R*` exists.** Some tax rate below `1.0` gives a non-negative trend. If
no rate does, the siphon cannot be offset by taxing the top at any rate, which
would be a more severe finding than any number this stage could report and is
recorded as such rather than as a failure.

**A6-3 — the siphon, in tax points. The stage's first number.** Under **fair
retention**, `R*` on the stratified graph is strictly positive, while `R*` on the
complete graph is zero.

The difference is the siphon: **the redistribution that access alone requires,
with retention already fair and no monetary injection anywhere.** Registered:
`R*(access, fair) > 0.02` and `R*(no access, fair) < 0.005`.

**A6-4 — topology is cheaper than quantity. The stage's second number.**
`R*(arm I) < R*(arm T)` under access, at every retention setting. Registered:
the ratio `R*(I) / R*(T)` is below `0.75`.

**A6-5 — the autarky runs.** At `R = R*` in arm I with access on and fair
retention, a two-thousand-round run at zero issuance keeps the support set
stationary end to end: the trend over the final five hundred rounds is not
negative, and `1 / HHI` at the end is within `10%` of its value at round five
hundred.

Three hundred rounds is enough to find `R*` and not enough to claim "forever".
The long run is a separate check for that reason.

**A6-6 — reported, not registered: the Palma ratio moves.** Its trajectory is
reported in every cell alongside the support set, with the two plotted together.
The expectation is that the support set can be held open while Palma drifts, and
if that is what happens it is the stage's most quotable result: **a closed
economy that stays reachable is not a closed economy that stays equal, and
conflating the two is what makes the first look impossible.**

---

## 6. Falsification

| observation | consequence |
|---|---|
| A6-1 fails | The economy holds itself open unaided and there is no siphon to price. Stage stops. |
| A6-2 fails | No tax on the top can offset the siphon. Reported prominently; it would say the access structure cannot be compensated from within the model's own instruments, which is worse for the policy reading than any value of `R*`. |
| **A6-3 fails: `R*(access, fair) ≈ R*(no access, fair)`** | The stratified graph demands no more redistribution than the flat one at these parameters. That is a finding about magnitude and **not** a refutation of the A track's premise: A6 prices the premise rather than testing it, since a redistribution channel *is* an edge and the whole exercise is conducted in the A track's own terms. What would be in question is the size of the siphon here, not whether topology determines distribution. |
| A6-4 fails: `R*(I) ≥ R*(T)` | Changing the graph is no cheaper than moving claims. The framework's central thesis, that topology dominates quantity, does not survive at the point where it would be actionable. Reported at the top of `RESULTS.md`. |
| A6-5 fails: stationary at 300 rounds, not at 2000 | `R*` is a three-hundred-round artefact. Reported as a bound with the horizon named. |
| Palma is stationary too | Unexpected and reported. It would mean the support set and the distribution move together here, and §2's reason for separating them was unnecessary in this model. |

---

## 7. What A6 cannot establish

**`R*` is not a tax rate for any real economy.** It is denominated in this
model's claim stock, over this model's graph, at this model's propensities. What
transfers is the *comparison* between arms and between access settings, not the
level.

**The infrastructure channel is a reduced form.** It reduces upward leakage by an
amount proportional to cumulative investment, with no construction lag, no
depreciation and no congestion. Each of those would raise `R*` in arm I, so their
absence makes A6-4 favourable to the framework's own thesis by construction, and
A6-4's threshold is set at `0.75` rather than at `1.0` for that reason.

**Zero issuance is a counterfactual, not a proposal.** The stage measures what
redistribution would be needed *instead of* monetary injection, which is a way of
pricing the siphon. It is not an argument that issuance should stop.

---

## 8. Parameters

| symbol | meaning | value |
|---|---|---|
| `R` | tax rate on financial-layer holdings, per round | searched over `[0, 1)` by bisection to `1e-3` |
| `ι` | leakage reduction per unit of cumulative investment, arm I | `1.0`, so a cumulative investment equal to the opening claim stock removes the whole of the production layer's upward leakage |
| seeds | replications | `5` |
| rounds | run length for the search | `300` |
| long run | A6-5 only | `2000` |
| issuance | in every cell | **off** |
| everything else | stage A2's registered values | see `PROJECT_PLAN.md` §2 |

---

## 9. Changes after pre-registration

None. Entries go here with the timing of each change marked, and any change made
after a result was read flagged in bold, in the same format as
`b2_measurement.md` §10.

### 9.1 First execution, three seeds. Both headline predictions hold.

Run from `redistribution.py` directly; `experiments/a6_siphon_cost.py` is not
yet written, so these are recorded here and are not yet in `results/`.

| access | retention | channel | `R*` | monotone above `R*` |
|---|---|---|---|---|
| on | stratified | transfer | `0.147` | 3/3 |
| on | stratified | infrastructure | `≤0.005` | 0/3 |
| on | fair | transfer | `0.060` | 3/3 |
| on | fair | infrastructure | `≤0.005` | 0/3 |
| **off** | any | any | **`0.000`** | — |

**A6-3 holds, and the siphon has a number.** Under fair retention the stratified
graph needs `6.0` tax points to hold the support set open; the complete graph
needs none, at every seed. Registered thresholds were `>0.02` and `<0.005`.

**That is the claim in its own units.** With retention already fair, with no
monetary injection anywhere, and with nothing different but who has an edge to
whom, the access structure alone demands six percent of the financial layer's
holdings every round.

**A6-4 holds overwhelmingly.** Infrastructure reaches stationarity at `≤0.005`
against `0.060` for the transfer, a ratio below `0.09` where the registered
threshold was `0.75`. Under stratified retention the gap is wider still,
`≤0.005` against `0.147`.

**Fixing retention halves the transfer's bill and does nothing to the
infrastructure's.** `0.147 → 0.060` for the transfer, `≤0.005` unchanged for
infrastructure. That is the two arms behaving as §3 said they would: a transfer
has to keep replacing what leaks away, so how fast it leaks matters to it;
attenuating the leak removes the dependence.

Three defects and one limit, all found here and none repaired by moving a
threshold.

**The stationarity test was measuring the wrong thing.** It asked whether the
tail slope of `1/HHI` was negative. At a zero levy that slope is `+1.1e-05`
while the support set has fallen from `35.7` to `26.0`: it contracts early and
then sits. A tail slope answers "is it still contracting" and the question is
"did it contract". Now: net level, with the slope reported beside it.

**Machine precision was destroying A6-3's own prediction.** The uniform-access
arm holds `1/HHI` at exactly two hundred, and `y[-1] < y[0]` failed it on the
last bit of a float, so every no-access cell returned "no rate works". A one
percent slack fixes it and is meaningful rather than cosmetic: the contraction
being measured is twenty-seven percent.

**`R*` is not monotone in the levy, and bisection assumed it was.** At a rate
near one the levy strips the financial layer every round and the support set
contracts for that reason instead of the original one. Replaced by a grid scan
that reports monotonicity as an observation. The infrastructure arm is **not**
monotone at any seed, so there is a band of high rates at which building more
makes things worse; where that band starts is not yet located.

**The grid cannot resolve `R*` for the infrastructure arm.** `0.005` is the first
non-zero point, so all that is established is `R*(I) ≤ 0.005`. That makes A6-4's
ratio an **upper bound**, which is conservative in the direction unfavourable to
the framework, so the criterion passes on a bound rather than on a value.

### 9.2 First full execution: 3/5, and the two failures are worth more than the three passes

`experiments/a6_siphon_cost.py`, five seeds, three hundred rounds, issuance off
in every cell. The script did not exist when §9.1 was written; §9.1's numbers
came from the library alone and only covered the two headline criteria.

**R\* by cell**, grid scan, per seed:

| cell | median | per seed |
|---|---|---|
| access / fair / transfer | **0.060** | `0.060` ×5 |
| access / fair / infrastructure | **0.005** | `0.005` ×5, on the grid's first non-zero point |
| access / stratified / transfer | 0.160 | `0.120, 0.160, 0.160, 0.120, 0.160` |
| access / stratified / infrastructure | 0.005 | `0.005` ×5, grid floor |
| all four flat cells | **0.000** | `0.000` ×5 |

**A6-2, A6-3 and A6-4 pass**, and A6-3 reproduces §9.1 exactly: with retention
already fair and no issuance anywhere, the stratified graph needs `6.0` tax
points and the flat graph needs none. **That difference is the siphon.**

#### A6-1 fails, and the reason is a contradiction inside this document

At `R = 0` the support set contracts in **4 of 8 cells**: all four access cells,
none of the four flat ones.

A6-1 as written requires **every** cell to contract. A6-3 requires
`R*(no access, fair) < 0.005`, which says the flat graph needs no redistribution
— that is, **it does not contract**. The two criteria cannot both hold, and the
contradiction is visible on paper without running anything.

A6-1's purpose — "there is something to fix" — is satisfied, and satisfied in
precisely the way A6-3 predicts. What is wrong is its scope: it should quantify
over the access cells, and the flat cells not contracting is the zero
calibration rather than a failure. **Not rewritten here**, because rewriting a
criterion after seeing which way it went is the move this repository refuses,
and the same refusal was applied to A3-6 an hour earlier. It is recorded as a
documentation defect for the stage designer to rule on.

#### A6-5 fails, and the failure is bimodal rather than a drift

Two thousand rounds at `R* = 0.005` in the infrastructure arm. End over start,
per seed: **`1.66×, 0.07×, 1.60×, 1.86×, 0.15×`**.

**Three seeds end more open than they began; two collapse to a fifteenth.** The
registered band is symmetric — "within `10%` of round five hundred" — so it
scores "grew by two thirds" and "collapsed to a fifteenth" as the same failure.
They are opposite outcomes and the script now prints the direction beside the
verdict.

#### And then the finding, which reverses A6-4 at the long horizon

`R*` measured at **two thousand** rounds rather than three hundred:

| arm | per seed | reading |
|---|---|---|
| transfer | `0.060` ×5 | holds every seed |
| infrastructure | `0.005, none, 0.005, 0.005, none` | **two seeds have no solution at any rate on the grid, up to `0.95`** |

Raising the levy does not help those two seeds. It makes them worse, and the
mechanism is legible in three measurements.

**The infrastructure channel has no steady state.** `invested` only ever
increases, and `removed = min(1, ι · invested / opening claims)`. So the arm
accumulates until it has removed **all** of the production layer's upward
leakage, and `R` sets how fast that happens, not where it stops. Measured on
seed 0: at three hundred rounds `R = 0.005` leaves `leak_factor = 0.134`, while
`R = 0.06` saturates by round one hundred and `R = 0.32` by round fifty. At two
thousand rounds every rate saturates.

**At saturation the financial layer is starved to nothing.** With the upward
edges gone it receives nothing and pays the levy every round: measured `L1
share = 0.0000` in every long run, at every rate.

**What happens next is decided by the production layer's own internal
connectivity**, and in two of five draws that layer cannot sustain circulation
by itself. Support falls from `27.7` to `2.0` and from `25.5` to `3.9`.

**So: cutting the leak is not the same as making a layer reachable.** Volume I
§8 defines the support set as reachability and warns against reading a flow
total as a topology; this is that warning applied to the instrument rather than
to the diagnosis. An intervention that removes every upward edge has sealed the
thermocline and done nothing whatever about whether the layer below it is
connected to itself.

**A6-4's registered pass stands at three hundred rounds and is a
short-horizon statement.** §7 already warned that the reduced form omits
construction lag, depreciation and congestion, and that their absence makes
A6-4 favourable to the framework's own thesis by construction. **That warning
now has a number.** Depreciation in particular is what would give the arm a
steady state: with it, cumulative investment would settle at a level set by `R`
and `R*` would be a price rather than a speed. Adding it is a design change and
is not made here.

**`R*` is therefore not a meaningful price for arm I beyond the short horizon**,
and the `R*(I)/R*(T)` ratio of `0.083` should be read as "the rate does not
control this channel" rather than as "this channel is twelve times cheaper".
