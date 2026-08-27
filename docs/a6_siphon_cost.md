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

> **On "the financial layer only", added 2026-08-12 and not a rewrite of the
> above.** That phrase turned out to be a design choice rather than a
> description: it makes the levy fall on a fixed set of node indices, which no
> real tax system does and which lets the base be drained to zero. It remains
> the registered default and is what every result up to §14 was produced under.
> §15 registers a second base assessed on a measured stock each round, and
> records what the difference measures. **Layer as position is not changed by
> that and is not in question**; only who the levy is assessed on.

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
| everything else | stage A2's registered values | as registered |

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

---

## 12. The frontier ratchet, ruled 2026-08-11, designed and not yet built

The same ruling is carried elsewhere in this project's own terms. This
section is the version a reader of *this* stage needs.

**On the number.** An earlier draft of this heading called the ratchet A6-6,
which is already taken: §5 registers A6-6 as the Palma trajectory, reported and
not judged, and `experiments/a6_siphon_cost.py` prints it under that name. The
ratchet's criteria are **A6-7 onward**, registered in §13, and §5 is left alone.
See §13.1.

### 12.1 Widening the scan is not the fix, and §11 already said why

A proposal to extend the tax-rate grid was considered and **rejected on the
evidence already in this document**. Three sentences above:

- the grid **already runs to `0.95`**;
- raising the levy makes the two failing seeds **worse**, not better;
- `invested` only ever increases, so `R` sets **how fast** the arm saturates
  rather than **where it stops**.

A monotone stock has no fixed point, whatever shape the effect function takes.
Scanning wider searches for something the model structurally cannot have, and
would return "still no steady state" after burning the compute.

### 12.2 The mechanism is obsolescence, and obsolescence is not depreciation

Depreciation says the asset wears out. What actually happens to social
infrastructure is that **the asset is fine and the world moved past it**.

Barefoot doctors, then township clinics, then hospitals. Anaesthesia from *make
the patient stop moving* to precision medicine. Prussian compulsory schooling to
a modern nine-year system. Each was **enormously useful in its own period**;
once absorbed into what is taken for granted, **the same provision at the same
position delivers less**, because the frontier rose.

Two state variables rather than one:

```
K ← K + I                  what has been built. Monotone. Nothing wears out.
B ← B + λ·(K − B)          the absorbed baseline. Monotone. This is the wall.
effect = g(K − B)          the effect comes from standing above the baseline,
                           not from K itself. g concave and bounded.
```

**Steady state.** With `dK/dt = I` and `dB/dt = λ(K−B)`, the gap settles at
**`K − B → I/λ`**. That is the fixed point A6-5 could not find, and it arrives
from the mechanism rather than being bolted on. Its comparative statics are also
the right ones: **investment must continue for the economy to stay above the
frontier, and stopping does not destroy the stock, it only stops buying
advantage.** Depreciation would say that stopping makes the bridge fall down,
which is false for a library and mostly false for a bridge.

### 12.3 The asymmetry, which must be carried verbatim into any write-up

`B` never falls, so **up and down are not the same curve**.

Going up: diminishing returns. One more library today buys less than one in
1900.

Coming down: **not a walk back along the marginal curve, but a cliff.** The
economy was built assuming `B`. If `K` falls below `B`, what is lost is the
**whole of `B`**, not the near-zero marginal quantity. Abolishing compulsory
schooling does not cost you this year's marginal contribution; it costs the
entire original block.

This is Volume II's absorbing wall applied to the **instrument** rather than to
the diagnosis: *losses to the real substrate are absorbing, quasi-money losses
can be refilled from another layer, and accounting treats the two as
interchangeable.* It is also §11.7's discipline against inventing a deflator:
two quantities that are not commensurable across directions may not be folded
into one number and then added.

**A6 does not simulate the cliff; it registers it.** The stage never reduces
`K`, so halting investment lets `B` catch up, drives `K − B → 0`, and takes the
effect to zero without ever falling below `B`. The cliff happens only on
deliberate abolition, which is not this experiment, and **simulating a path that
does not occur is the same as inventing a price for it**.

### 12.4 Where the four candidate mechanisms end up

| mechanism | standing | why |
|---|---|---|
| **frontier ratchet `λ`** | **primary; A6-6's headline** | the only one that yields a fixed point without assuming anything wears out |
| **smooth saturation `g`** | kept, separate | sets **where** the steady state sits, and replaces the `min(1,·)` wall. **On its own it does not fix A6-5** |
| proportional decay `δ` | kept, **registered default `0`** | physical stock does wear out, but most of the loss is relative. A robustness axis, not a headline |
| service life `L` | **excluded** | a special case of `δ` with an all-at-once hazard, needs a queue state, and **cannot express relative obsolescence**: a bridge usually loses its use because the centre of the city moved and other bridges were built, not because it fell down |

### 12.5 What the code does today, verified rather than remembered

`redistribution.py`:

```python
self._opening_claims = float(self.holdings.sum())   # __init__, never updated
...
self.invested += total                              # monotone
removed = min(1.0, spec.leak_response * self.invested / self._opening_claims)
```

So of the four mechanisms: **no decay, no service life, and diminishing returns
only as a wall.** `min(1,·)` is not a diminishing return. It is a constant
marginal effect running straight into a ceiling and then becoming exactly zero.
Clean water, the obvious saturating case, is smooth; the two behave very
differently near the top, because against a wall `R` only decides the arrival
time, while against a smooth saturation `R` still buys something at every level.

### 12.6 The reduction guard, which decides whether the new parameters may enter

§10.1's strict-generalisation rule: a generalisation that cannot reproduce its
special case is not a generalisation.

**With `λ = 0` the baseline `B` stays at zero, `g` set to the hard clip, and the
denominator left frozen at the opening stock, the effect must reduce to
`min(1, ι·K/claims₀)` — the line above — and every number in §11 must be
reproduced bit for bit.** If it does not, the two new parameters do not enter.

### 12.7 One scope limit that changes how `λ` may be read

A6 is a closed economy with no outside, so `B` can only chase `K`: **the
frontier is pushed only by what this economy itself built.** In the world the
frontier is also pushed from outside, by other countries and by technology, and
that part is not in this model.

**Therefore `λ` reads as an endogenous absorption rate and may not be reported
as a rate of progress.**

---

## 13. A6-7 to A6-13: the ratchet's pre-registration, written 2026-08-12

§12 fixed the mechanism and ruled out its three competitors. This section fixes
what the ratchet is expected to *do*, with thresholds and a falsification table,
and it is written before a line of the new code runs.

### 13.1 Numbering, and two defects in this document's own cross-references

**The ratchet's criteria are A6-7 onward.** §5 already registers **A6-6 as the
Palma trajectory**, reported and not judged, and the script prints it under that
name. §12's first draft used A6-6 for the ratchet as well, which put two
different objects on one number inside one pre-registration. Freeing the number
by renaming the older item would be a rewrite of a registered criterion for a
cosmetic gain, so the older item keeps it.

**Two dangling section numbers, recorded and not repaired here.** §12.1 and
§12.6 both point at "§11", and this document has no §11: the results they mean
are the block headed **§9.2, "First full execution"**, which is where the `R*`
table, the `4 of 8` zero-levy count, the five `end/start` ratios and the `0.083`
ratio all live. The numbering appears to have been demoted from `## 10` / `## 11`
to `### 9.1` / `### 9.2` in an earlier pass while the forward references kept the
old numbers. Recorded as a documentation defect for the stage designer, in the
same form §9.2 used for A6-1's scope defect. **A6-7 below names the target
explicitly so the guard does not depend on resolving the reference.**

### 13.2 What the three new parameters are

They live in `RatchetSpec` and sit on top of §8's `ι`, which does not move.

| symbol | meaning | registered values |
|---|---|---|
| `λ` | rate at which the absorbed baseline `B` chases the built stock `K` | grid `0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1`. `λ = 0` is the reduction point |
| `g` | the effect function on the gap | `clip` = `min(1, x)`, today's wall, used for the reduction only; `exp` = `1 − e^{−x}`, the registered default; `hill` = `x/(1+x)`, the robustness axis |
| `δ` | proportional decay on `K` | `0`. A robustness axis kept out of every headline, per §12.4 |

The state, per round, with `I` the levy collected that round:

```
B ← B + λ·(K − B)          the baseline absorbs what already stood
K ← (1 − δ)·K + I          then this round's building lands
x  = ι · max(0, K − B) / claims₀
removed     = g(x)
leak_factor = 1 − removed
```

**The baseline absorbs before the new building lands, and the order decides
where the fixed point is.** What was built this instant cannot already be taken
for granted, so absorption in a round operates on the stock as it stood at the
start of it. That reading is also the one whose fixed point is §12.2's
`K − B → I/λ`. Absorbing after the build instead settles at `I·(1−λ)/λ`, which
agrees to first order and is ten percent low at `λ = 0.1`, the top of the grid.
A6-8 checks the implemented recursion against `I/λ`, so the two orders are not
interchangeable and `tests/test_a6_ratchet.py` pins the choice rather than
leaving it to a comment.

`max(0, ·)` exists for the `δ > 0` axis alone. §12.3 registers the cliff and
refuses to simulate it, so if decay ever drives `K` under `B` the effect is
floored at zero rather than walked back down the marginal curve.

**The levy may collect nothing and the arm still runs.** A drained financial
layer pays no levy, so nothing is built that round, and the baseline absorbs
anyway. The gap decays, the leak reopens, the layer refills and the levy comes
back. That is the feedback the ratchet is adopted for, and it is why the round
hook does not return early on an empty levy the way the version without a
ratchet does. **At `λ = 0` this changes nothing observable**, which is what lets
A6-7 still hold: with the baseline frozen the effect is unchanged from the
previous round, and rebuilding the routing matrix from an unchanged
`leak_factor` returns the same bits.

**Both smooth shapes have `g'(0) = 1`**, which is the hard clip's slope at the
origin. The first tax point buys the same thing under all three, so the arms are
comparable where the arm is small, and they separate only at the top. That is
deliberate: the top is where §9.2's collapse mechanism lives.

### 13.3 Why this `λ` grid. Fixed by arithmetic, not by a run

At the fixed point `K − B → I/λ`, and `I = R · (financial layer's holdings)`.
Write `s` for the financial layer's share of the claim stock. Then the argument
of `g` at the fixed point is

```
x* = ι · R · s / λ
```

a pure number, independent of the size of the economy. With `ι = 1`, the opening
`s = 0.679` and `R = 0.005`, this is `x* ≈ 0.0034 / λ`. The registered grid
therefore sweeps `x*` from about `34` at `λ = 1e-4` down to about `0.034` at
`λ = 1e-1`: from *the leak is sealed as completely as it is today* to *the arm
buys almost nothing*. **The endpoints come from that arithmetic. Nothing on this
grid was chosen after looking at an outcome.**

The same arithmetic says where the two shapes must disagree. At `x = 5` the
residual leak is `0.007` under `exp` and `0.167` under `hill`; at `x = 34` it is
`1.7e-15` against `0.029`. §9.2's collapse runs through *the financial layer is
starved to `L1 share = 0.0000`, after which the production layer has to sustain
circulation alone and two of five draws cannot*. So **`exp` leaves that channel
open and `hill` closes it by construction**, which is exactly why `exp` is the
default and `hill` is an axis rather than the other way round: if the collapse
stops happening under `exp`, the credit goes to `λ`.

**Where each shape becomes the wall, measured rather than argued.** In real
arithmetic neither smooth shape ever reaches one. In float64 both do, and the
crossovers are far apart: **`exp` returns exactly `1.0` at `x ≥ 37.43`**, and
`hill` not until `x ≥ 1.2e16`. Two consequences, both registered here before the
run:

- **A6-9's block never enters the degenerate region.** It runs at the
  three-hundred-round `R* = 0.005`, where `x* ≈ 0.0034/λ` tops out near `34` at
  the grid's smallest `λ`. That is under `37.43`, so the `exp` arm is strictly
  below the wall at every point of the `λ` curve.
- **A6-10's rescan does enter it, and is meant to.** That scan runs the rate up
  to `0.95`, where `x* ≈ 0.645/λ` passes `37.43` for every `λ` at or below
  `1.7e-2`. So at high rates the `exp` arm *is* the wall, the leak is sealed and
  §9.2's collapse is available again. That is the mechanism A6-12 is trying to
  locate the edge of, not an artefact to be worked around: at the crossover the
  surviving leak is already under one part in `1e16`, so the route weight
  carrying it is below one ulp of the weights beside it and the layer is starved
  whether or not the last bit rounds away.

Under `hill` neither block reaches the crossover at any rate on the grid, which
is the same statement as "`hill` closes the collapse channel by construction",
now with the number attached.

### 13.4 The criteria

**A6-7 — the reduction guard. A gate, not a finding.** With `λ = 0`, `g = clip`,
`δ = 0` and the denominator left frozen at the opening stock, `A6RatchetModel`
and `A6Model` return **bit-identical** `effective_support`, `holdings`,
`leak_factor` and `invested`, across all eight cells of §4's factorial, five
seeds, three hundred rounds, at rates `0, 0.005, 0.06, 0.32`. One differing bit
and the three new parameters do not enter.

Two properties of this guard are worth stating because they are what make it
usable. **It compares two code paths inside one process**, so it says nothing
about two machines and cannot be broken by a BLAS difference. And **`A6Model` is
not modified**: the ratchet is a subclass that overrides `_post_round` only, so
the object the guard reduces to is the one that produced §9.2 and is still
sitting there to be read.

**A6-8 — the fixed point is where the algebra says it is.** On a constant
injection bench that iterates the two state equations and nothing else, `K − B`
converges to `I/λ` within `1e-9` relative, for `λ` in `{1e-4, 1e-3, 1e-2, 1e-1}`.
This checks arithmetic and not economics, and it exists because §12.2's whole
claim on the mechanism is that the fixed point falls out of it rather than being
bolted on. If the code's fixed point is somewhere else, the mechanism in the
document is not the mechanism in the model.

**A6-9 — the headline. There is a band of `λ` on which the long run stays open
in every seed.** In `access / fair / infrastructure`, at the three-hundred-round
`R*`, over two thousand rounds: there is at least one `λ` on the registered grid
at which all five seeds end with `1/HHI` at or above `0.9 ×` its opening value.
Both endpoints of that band are reported.

The prediction has a shape, and the shape is what makes it falsifiable rather
than a search. **Small `λ` should fail the way it fails today**: the gap runs
away, the leak is sealed, the financial layer starves and the seeds that cannot
self-circulate collapse. **Large `λ` should fail the other way**: the baseline
eats the stock as fast as it is built, the arm buys nothing, and the access cell
contracts as A6-1 says it does at `R = 0`. **So the band is interior, and both
failures are predicted before either is seen.** A criterion that only said
"some `λ` works" would be satisfied by a wide enough grid.

**The band is one-sided on purpose, and the reason was learned from A6-5.**
A6-5's registered band is symmetric, so it scored *grew by two thirds* and
*collapsed to a fifteenth* as the same failure, and §9.2 records that. A6-9 asks
only that the economy not close. **A6-5 is not rewritten**; it stays failed, with
its symmetric band, in §5 and in §9.2.

**A6-10 — `R*` stops being a speed and becomes a price.** In the infrastructure
arm at two thousand rounds, with the ratchet on: every seed has a solution on the
grid, and `R*` does **not** sit on the grid's first non-zero point
(`at_grid_floor` false). §9.2's finding is that `invested` is monotone, so `R`
sets how fast the arm saturates and not where it stops, and that `R*` is
therefore not a meaningful price for this arm beyond the short horizon. The
ratchet's only reason to exist is that it puts a stop where there was none.
**If `R*` still lands on the grid floor, or two seeds still have no solution, the
ratchet did not do the one thing it was adopted for.**

**A6-11 — topology is still cheaper than quantity at the long horizon.** With the
ratchet on, at two thousand rounds, `R*(I) / R*(T) < 0.75` under **access with
fair retention**, **as a value and not as an upper bound**. The threshold is
A6-4's, unchanged, and it is reused rather than re-derived because A6-4 passed on
a bound at three hundred rounds and §9.2 then withdrew the reading. This is the
first time the ratio is a number that means what A6-4 said it meant.

**A6-12 — reported, not judged: the upper end of the working band, in tax
points.** §9.1 recorded that the infrastructure arm is not monotone at any seed,
so there is a band of high rates at which building more makes things worse, and
that **where that band starts was not located**. The scan now reports the whole
verdict vector rather than its first entry, so the band's upper end is a number.
Reported per seed, per `λ`, per `g`. **Not judged**: no threshold was registered
for it before it existed, and inventing one now would be a threshold fitted to a
quantity nobody has seen.

**A6-13 — the conclusion does not rest on `g`'s tail.** A6-9's band and A6-10's
verdict point the same way under `exp` and under `hill`. If they point opposite
ways, the result is carried by the shape of the saturation and not by `λ`, the
headline is withdrawn, and what gets reported is the shape dependence itself.
§13.3 says in advance which direction each shape is expected to bend, so this is
a check and not a tie-breaker.

### 13.5 Falsification

| observation | consequence |
|---|---|
| **A6-7 fails** | The generalisation cannot reproduce its own special case. `λ`, `g` and `δ` do not enter, and nothing below is run. This is §10.1's rule, applied as a gate rather than as a remark. |
| A6-8 fails | The implemented recursion is not the one §12.2 describes. A coding defect, fixed, not a finding. |
| **A6-9 fails: no `λ` on the grid holds all five seeds open** | The ratchet is not what A6-5 was missing. Recorded, and the infrastructure arm keeps §9.2's verdict: it has no steady state and `R*` is a speed. It would also mean the fixed point in `K − B` does not translate into a fixed point in the economy, which is worth more than the criterion, because the two state equations are only half the loop and the other half is the levy responding to how starved the financial layer is. |
| A6-9 fails only at the ends | Not a failure. That is §13.4's predicted shape and the band is the deliverable. |
| **A6-10 fails: `R*` still on the grid floor** | The ratchet gives the *gap* a fixed point without giving *`R`* any purchase on where it sits. The mechanism would be right and useless, and A6-11 would be unreadable for the same reason A6-4's ratio was withdrawn. |
| **A6-11 fails: ratio ≥ 0.75** | Changing the graph is not cheaper than moving claims once the arm has a stop. The framework's central thesis does not survive at the long horizon at the point where it would be actionable. Reported at the top of `RESULTS.md`, in the same place A6-4's falsification clause sends it. |
| A6-13 fails: the two shapes disagree | The headline is withdrawn and the shape dependence is reported in its place. |

### 13.6 The guard against choosing `λ` after the fact

§12.7 leaves `λ` with no external anchor: this is a closed economy, `B` can only
chase what this economy itself built, so there is no observable outside the model
to calibrate against. **Report the whole curve, name both endpoints of the band,
nominate no preferred `λ`.**

This is the same guard that sits on A4's injection quantity, against the same
failure: **a parameter fixed after seeing where the criterion turns is a fit**,
and letting `σ` take a value per era lets the model fit anything and takes the
predictive power to zero.

### 13.7 The run, and where its cost is bounded before it starts

| block | runs | length |
|---|---|---|
| A6-7 reduction guard | 8 cells × 5 seeds × 4 rates × 2 models | 300 |
| A6-8 fixed-point bench | 4 `λ` | no economy, two scalars |
| A6-9 the `λ` curve | 7 `λ` × 2 `g` × 5 seeds | 2000 |
| A6-10, A6-11, A6-12 the rescan | 2 `λ` × 2 `g` × 5 seeds × 15 rates, arm I | 2000 |
| the transfer denominator for A6-11 | 5 seeds × 15 rates, once | 2000 |

**The rescan uses two `λ` and not seven, and the two are named here.** `1e-3` and
`1e-2` put `x*` at about `3.4` and `0.34` at `R = 0.005`, which brackets `x* = 1`,
the point where the default `g` has delivered `1 − e^{−1} = 0.632` of its bound.
That is the reason, it is arithmetic from §13.3, and it is on the page before the
scan runs. The other five `λ` are still swept in the A6-9 block, so the curve is
reported at full resolution and only the expensive scan is coarse.

**A6-9's rate is the three-hundred-round `R*` already on record**, `0.005`, and
not a rate chosen for this run.

**Three more scoping decisions, all made here rather than at reading time.**

- **A6-10 and A6-11 are judged under `g = exp` at both rescan `λ`, and both must
  hold.** A split result, working at one `λ` and not the other, is reported as a
  failure with the split named. Passing on whichever `λ` cooperated is the thing
  §13.6 forbids. The `hill` runs feed A6-13 and nothing else.
- **The rescan cell is `access / fair / infrastructure`,** which is the cell
  A6-3, A6-5 and §9.2's two-thousand-round table all use. The stratified
  retention setting is not rescanned; A6-11's denominator is measured in the
  same cell, once, since the transfer arm reads neither `λ` nor `g`.
- **`contracted`'s tail stays at its default `150` rounds even in the
  two-thousand-round scans.** That is what §9.2's table was produced with, and
  comparability with the numbers already on record is worth more than a longer
  window chosen now.

### 13.8 What A6-7 to A6-13 cannot establish

**`λ` is not a rate of progress.** §12.7 is the binding limit: the frontier here
is pushed only by what this economy built, so `λ` reads as an endogenous
absorption rate. Any sentence of the form "the world's frontier advances at `λ`"
is outside what this model contains.

**A finite `R*` is still not a tax rate for any real economy.** §7 stands
unchanged. What the ratchet buys is that the *comparison* in A6-11 survives the
long horizon, not that the level means anything outside this claim stock.

**The cliff is registered and not measured.** §12.3. `K` never falls in any
headline cell, so no number in this stage prices the loss from abolition, and any
write-up that quotes one is quoting something the model did not compute.

---

## 14. The ratchet's first execution, 2026-08-12

Five seeds, three hundred rounds for the guard, two thousand for the long runs,
issuance off in every cell. `results/a6_ratchet.json`.

**4 of 6 criteria pass, and the two failures are not where the interest is.**
The interest is in a sentence §12.4 registered that this run makes false, and in
what `λ` turned out to be doing instead.

### 14.1 The scoreboard

| criterion | verdict | reading |
|---|---|---|
| **A6-7** reduction guard | **pass** | 160 model pairs compared bit for bit, 0 mismatches, on a Windows build and on a Linux sandbox alike. The guard is a same-process comparison, so this was expected, and it means `A6Model` is still exactly the object §9.2 came from |
| **A6-8** fixed point | **pass** | `K − B` settles on `I/λ`, worst relative error `5.04e-11` against `1e-9` |
| **A6-9** the `λ` band | **pass on the letter** | band is `λ ∈ [0, 0.01]`, six of eight grid points, contiguous, under both smooth shapes. **Its predicted shape failed.** §14.4 |
| **A6-10** `R*` off the grid floor | **fail** | holds at `λ = 0.01` (`R* = 0.010`), fails at `λ = 0.001` (`R*` pinned at `0.005`). §13.7 registered that both must hold and that a split is reported as a failure with the split named. §14.5 |
| **A6-11** the ratio as a value | **fail** | same split. At `λ = 0.01` the ratio is `0.167` and is a value; at `λ = 0.001` it is `0.083` and is a bound |
| **A6-12** the top of the band | reported | §14.6 |
| **A6-13** shape agreement | **pass** | `exp` and `hill` agree on the band and on both scan verdicts |

### 14.2 The registered sentence that this run makes false

§12.4 says of the smooth saturation: **"On its own it does not fix A6-5."** It
does.

The `λ = 0` point of the curve is the ratchet turned off with the wall replaced
and nothing else changed. Its setting matches A6-5 item for item: `access / fair
/ infrastructure`, `R = 0.005`, two thousand rounds, five seeds.

| | `1/HHI` end over start, per seed |
|---|---|
| §9.2, under the wall `min(1, x)` | `1.66, 0.07, 1.60, 1.86, 0.15` |
| here, `λ = 0`, `g = 1 − e^{−x}` | `2.43, 1.77, 2.29, 2.45, 2.53` |
| here, `λ = 0`, `g = x/(1+x)` | `2.78, 2.69, 2.62, 2.69, 2.89` |

The two seeds that collapsed to a fifteenth come back at `1.77` and `2.53`. No
absorption was involved.

**The mechanism is legible in one number.** At two thousand rounds and
`R = 0.005` the argument of `g` reaches only `x ≈ 2.8`, and the surviving leak
under `exp` is `0.058` to `0.068`. The wall reaches exactly one at `x = 1`, which
at this rate arrives near **round 294**, and stays there for the remaining
seventeen hundred rounds. So §9.2's collapse is *the wall closing at round three
hundred and never reopening*, and it is not the absence of a fixed point in
cumulative investment. §12.5 had already said that `min(1,·)` "is a constant
marginal effect running straight into a ceiling and then becoming exactly zero".
What §12.4 got wrong is the next step, which assumed removing the ceiling was not
by itself enough.

**Recorded, not repaired.** §12.4's table keeps its wording and this section
carries the correction, which is the treatment §9.2 gave A6-1's scope defect.

### 14.3 What `λ` does instead

`λ` does not decide whether the economy survives. It decides **how far open it is
held**, and it is what gives the levy rate purchase on the outcome.

| `λ` | end over start, `exp`, five seeds | surviving leak | `K − B`, in opening claim stocks |
|---|---|---|---|
| `0` | `2.43, 1.77, 2.29, 2.45, 2.53` | `0.058–0.068` | `2.7–2.9`, still growing |
| `1e-4` | `2.56, 2.07, 2.41, 2.54, 2.67` | `0.073–0.085` | `2.5–2.6` |
| `1e-3` | `2.58, 2.50, 2.46, 2.51, 2.62` | `0.196–0.211` | `1.56–1.63` |
| `3e-3` | `1.43, 1.39, 1.40, 1.45, 1.40` | `0.367–0.379` | `0.97–1.00` |
| `1e-2` | `0.986, 0.964, 0.987, 1.004, 0.963` | `0.686–0.692` | `0.368–0.377` |
| `3e-2` | `0.897, 0.880, 0.901, 0.914, 0.879` | `0.876–0.879` | `0.129–0.132` |
| `1e-1` | `0.87, 0.86, 0.88, 0.89, 0.85` | `0.960–0.961` | `0.039–0.040` |

Monotone throughout, and the fixed point behaves as §13.3's arithmetic said it
would: the gap settles at a level proportional to `1/λ`, so the surviving leak
rises with `λ` and the arm buys less.

**The payoff shows up in the price, not in survival.** `R*(T) = 0.060` at every
seed. In the infrastructure arm:

| `λ`, `exp` | `R*(I)` per seed | on the grid floor | `R*(I)/R*(T)` |
|---|---|---|---|
| `1e-3` | `0.005` ×5 | yes | `0.083`, **a bound** |
| `1e-2` | `0.010, 0.010, 0.010, 0.005, 0.010` | no | **`0.167`, a value** |

So at `λ = 1e-2` the ratio is a number that means what A6-4 said it meant, which
is what A6-11 existed to obtain, and §9.2's withdrawal of A6-4's reading is
answered at that `λ`. Under `hill` at the same `λ` every seed gives `0.167`.

**No `λ` is nominated.** §13.6.

### 14.4 A6-9 passed its letter and failed its shape

§13.4 registered that the band would be **interior**, with the low end failing
the way §9.2 fails and the high end failing by buying nothing, and said in as
many words that a criterion satisfied by a wide enough grid would not be worth
much. The high end failed as predicted: `λ = 3e-2` puts three of five seeds under
the floor at `0.879` to `0.914`, and `λ = 1e-1` puts all five under. **The low end
never failed at all**, so what came back is the one-sided band `λ ≤ 0.01`.

The reason is §14.2. The curve's `λ = 0` point carries `g = exp`, so the wall was
already gone there and the low-end failure mode was never in play. **The
prediction assumed `λ = 0` under a smooth `g` would behave like `λ = 0` under the
wall.** That assumption is the same one §12.4 made, it is wrong for the same
reason, and it was not visible until the column existed. A6-14 and A6-15 below
are the control that separates the two.

The upper edge is also closer than the grid makes it look. At `λ = 3e-2` the five
readings are `0.897, 0.880, 0.901, 0.914, 0.879` against a floor of `0.9`: two
seeds clear it and three miss by one to two points. The transition is gradual and
the band's stated end at `0.01` is a grid point, not a cliff.

### 14.5 A6-10 and A6-11 fail on the split that §13.7 named

Both hold at `λ = 1e-2` and both fail at `λ = 1e-3`, where `R*` is pinned at the
grid's smallest non-zero point. **The blocker is grid resolution and not the
mechanism**: `R*(I)` at `λ = 1e-3` is somewhere at or below `0.005` and the scan
cannot say where.

This is a different proposal from the one §12.1 rejected. §12.1 refused to extend
the grid **upward**, on three grounds that are all about high rates: the grid
already runs to `0.95`, raising the levy made the failing seeds worse, and a
monotone stock has no fixed point. None of the three touches a request for points
**below** `0.005`. §14.7 registers that refinement, and **A6-10 and A6-11 keep
their failures.**

### 14.6 A6-12: §9.1's missing number, and the band is mostly not there

§9.1 recorded that the infrastructure arm is not monotone at any seed, so there
is a band of high rates at which building more makes things worse, and that where
that band ends was never located. With the ratchet on, at two thousand rounds:

| cell | `R*` per seed | top of the band per seed | contiguous |
|---|---|---|---|
| `exp`, `λ = 1e-3` | `0.005` ×5 | `0.950, 0.040, 0.950, 0.950, 0.950` | yes ×5 |
| `exp`, `λ = 1e-2` | `0.010, 0.010, 0.010, 0.005, 0.010` | `0.950` ×5 | yes ×5 |
| `hill`, `λ = 1e-3` | `0.005` ×5 | `0.950, 0.800, 0.950, 0.950, 0.950` | yes ×5 |
| `hill`, `λ = 1e-2` | `0.010` ×5 | `0.950` ×5 | yes ×5 |

**At `λ = 1e-2` there is no upper end on this grid at all**, under either shape:
every seed stays open to `0.95` and the arm is monotone above `R*`, which it was
at none of three seeds in §9.1. At `λ = 1e-3` one seed keeps a ceiling, and where
that ceiling sits moves with the shape, `0.040` under `exp` against `0.800` under
`hill`. Both facts point the same way: **the ceiling is a symptom of getting close
to sealing the leak**, and it recedes when either `λ` or a heavier-tailed `g`
keeps the leak open.

Not judged. No threshold for it was registered before it existed, and §13.4 says
inventing one now would be a threshold fitted to a quantity nobody had seen.

### 14.7 Registered after reading §14.1, and before the code for it exists

The three entries below were written on 2026-08-12 with §14.1 through §14.6 in
hand. **Each is marked with what it was allowed to see**, in the format §9 uses.

#### A6-14 — the control column reproduces §9.2. A gate on every comparison above

The `λ` curve is re-run with `g = clip`, everything else identical, as a control
column. **At `λ = 0` the five `end over start` readings must reproduce §9.2's
`1.66, 0.07, 1.60, 1.86, 0.15`** to the two decimals §9.2 printed.

This should hold exactly rather than approximately: `RatchetSpec(absorption=0,
shape="clip")` is the reduction point, so the run goes through the code path A6-7
already proved bit-identical to `A6Model`, at the same rate, seeds and horizon
§9.2 used. **If it does not reproduce, the two scripts are not measuring the same
thing and §14.2's comparison is void**, along with everything built on it.

#### A6-15 — under the wall the band is interior, and its low end is where `x*` crosses one

Under `clip` the effect saturates completely once `x ≥ 1`. With the ratchet on,
`x` settles at `x* = ι·R·s/λ`, where `s` is the financial layer's share of the
claim stock. So the wall seals if and only if `λ` is small enough, and the clip
column should close at small `λ`, open in the middle, and close again at the top
for the reason the `exp` column closes there.

Registered, on the eight-point grid at `R = 0.005`:

- **closed at `λ = 0` and `λ = 1e-4`.** At `λ = 0` the gap grows without bound and
  §9.2 is the observation. At `1e-4`, `x* ≥ 11` for any `s` above `0.2`.
- **open at `λ = 1e-2`.** `x* ≤ 0.5` for any `s` at or below unity.
- **closed at `λ = 1e-1`**, where the `exp` column already closes and the arm buys
  almost nothing.
- **the crossover from closed to open lies in `{3e-4, 1e-3, 3e-3}`, and its
  location is reported rather than predicted.** `s` is endogenous: sealing the
  leak drains the financial layer, which lowers `s`, which lowers `x*`, which
  unseals the leak. Measured `s` under `exp` runs from `0.32` at `λ = 1e-3` to
  `0.75` at `λ = 1e-2`, and it will differ again under the wall, so naming the
  crossover point in advance would be inventing a precision this stage does not
  have.

**If A6-15 holds, `λ`'s role is exact: it is what rescues the wall, and once the
wall is replaced by a smooth saturation, survival does not need it.** That is a
sharper statement than the one §12 set out to make, and it is the one the
evidence supports.

The clip column feeds A6-14 and A6-15 only. **It does not enter A6-13**, which
compares the two smooth shapes, and it is not rescanned for `R*`.

#### The rate grid is refined below `0.005`

`0.001`, `0.002` and `0.003` are added, giving an eighteen-point grid that
**contains the registered fifteen as a subset**. Consequences, all registered
here:

- **`RATE_GRID` itself does not change.** `experiments/a6_siphon_cost.py` reads it
  and §9.2's numbers must stay reproducible, so the refined grid is a separate
  constant used by the ratchet stage alone.
- **A6-10 and A6-11 keep their failures**, computed on the registered sub-grid
  with the registered `0.005` floor, and those are the verdicts that go to
  `criteria` and to `RESULTS.md`. The refined readings are reported beside them as
  a re-measurement at higher resolution, never as a repaired criterion.
- Both readings come from **one scan**, since the registered grid is a subset of
  the refined one, so the failed verdict and the refined number are guaranteed to
  be the same run.

#### A defect in the results file

`lambda_curve.cells[*].final_gap_over_opening_claims` holds the raw gap `K − B`
and not `ι·(K − B)/claims₀`, so the key names a quantity the value is not. No
criterion reads it. Replaced by two keys, `final_gap` and `final_x`, with `x` the
dimensionless argument of `g` that §13.3's arithmetic is about.

### 14.8 One measurement caveat, carried forward

`at_grid_floor` is a **cell-level** flag: it is true when the largest `R*` across
seeds sits at or below the grid's first non-zero point. At `λ = 1e-2` under `exp`
one seed returns `R* = 0.005` while the other four return `0.010`, so that seed's
own ratio is a bound while the cell is not flagged. The flag is inherited
unchanged from `a6_siphon_cost.py` and §13.4 registered it in that form, so it
stays. The per-seed `R*` values are printed beside every ratio for exactly this
reason.

---

## 15. Who pays: the levy base, ruled and rebuilt 2026-08-12

Section 3 registered the levy as falling "on the financial layer only". That
sentence hid a design choice that no real tax system makes, and the choice turns
out to have been carrying one of this stage's central findings. This section
records what was wrong, what replaced it, and what the replacement measured.

### 15.1 The defect: layer membership is an identity, and the levy inherited it

`network.py` assigns `self._l1 = spec.financial_nodes`, which is `arange(20)`,
once at construction, and never recomputes it. Layer membership fixes the graph's
edges, the spending propensities, who pays payroll, the injection point and the
opening allocation. It also, until now, fixed **who pays the levy**:

```python
levy = spec.rate * np.maximum(self.holdings[self._l1_idx], 0.0)
```

Twenty node indices, whatever they hold, and whoever else has become rich.

**Two different things were riding on one switch, and only one of them was
right.** Layer as *position*, meaning which edges a node has, is the framework's
own object and should not move: a household does not become a bank by getting
rich. The **levy base** is a policy instrument, and a real tax is assessed on a
measured quantity rather than on a category. The two coincide at the open and
come apart exactly when the intervention starts working, which is the whole
regime this stage is about.

**The counter-case is real and is why the position reading is not simply
correct either.** A production-layer household that accumulates enough does in
fact become a rentier. The evidence for that is causal rather than
correlational: a lottery windfall of one million kronor raises equity market
entry among prior non-participants by twelve percentage points, about
thirty-nine percent of prior non-participants entering on windfalls above two
million, with the effect immediate and still present ten years later, while
prior participants are unaffected (Briggs, Cesarini, Lindqvist and Östling,
*Journal of Financial Economics*, 2021). The implied **one-time** entry cost
exceeds a million kronor for over forty-five percent of non-participants against
a median per-period cost of about two hundred.

So the shape the evidence supports for *membership* is a threshold with a large
one-off cost and downward stickiness, and neither a fixed identity nor a
per-period recomputation. **Membership is not changed here.** Three reasons, all
recorded rather than argued from taste:

- the blast radius is the whole A track, since everything subclassing `Network`
  reads the partition;
- the thinnest part of the evidence is precisely the property such a change
  would need, namely reversibility. No study tracks whether households that
  *lose* wealth exit rentier behaviour; the downward stickiness is inferred from
  the entry-cost asymmetry rather than measured;
- stage A3 already contains the mechanism, in its `γ·P` asset-access threshold
  where one hundred and eighty production nodes yield twenty-three entrants.
  A6 declares in its own header that it does not use A3's machinery, so
  borrowing it is a coupling decision and not a local fix.

### 15.2 What real systems do, and the one number that decides it

Every net wealth tax in force assesses liability on a **measured stock,
recomputed every year**. Norway (worldwide net assets above NOK 1.9m, about
twelve percent of the population), Switzerland (cantonal, annual, thirty-four to
forty-two percent of filers, levied continuously since 1840 and still 3.9% of
total tax revenue), Spain (the regional *Patrimonio* plus the national
*Solidaridad* above €3m) and France's ISF before its 2018 replacement by the
real-estate-only IFI. **None uses a fixed set of payers.**

And the base does not drain. Norway's wealth tax revenue rose from NOK 27bn to
about 34bn between 2022 and 2025 *through* the largest documented emigration
episode, roughly 260 residents with over NOK 10m leaving in each of 2022 and
2023. Spain's rose 58% in a year; France's IFI rose 11% in 2024. The reason is
structural: a stock base recomputed each period is replenished by returns and by
new entrants crossing the threshold, and observed rates of 0.15% to 1.1% sit far
below the return on capital, so the tax **skims a flow rather than consuming the
stock**.

Behavioural response is large but runs through valuation and reclassification
rather than through holders disappearing: elasticity of *taxable* wealth to the
net-of-tax rate is 43% in Switzerland (24 points of it internal mobility, 21
house-price capitalisation), 0.7 long-run in Denmark, 0.09 to 0.27 in Sweden.

**So the model's property that taxing a fixed set drains it to zero, after which
the levy collects nothing forever, is an artefact of the fixed-category design
and not a feature of any real system.**

### 15.3 The threshold base, and why `θ` is one mean

`LevySpec.base = "threshold"` levies on **the excess above a threshold**, for
every node, recomputed each round:

```
levy_i = R · max(0, holdings_i − θ),      θ = k · (claim stock / node count)
```

Norway taxes what is above NOK 1.9m rather than the whole holding of everyone
above it, and this follows that. The disbursement side is **not changed**:
proceeds still go per capita to the production layer. One change at a time, so
the effect is attributable.

**`k = 1` is registered, on three grounds fixed before the run.**

- It catches **twenty-one to twenty-five of two hundred nodes at the open**,
  measured per seed as `23, 22, 25, 23, 21`, so ten and a half to twelve and a
  half percent. Norway's threshold catches roughly twelve percent of the
  population. That is an external anchor, not a tuned one.
- Under `uniform_access` every node opens holding exactly the mean, so the
  excess is exactly zero everywhere and **the levy is exactly zero. The zero
  calibration becomes a derivation rather than an assumption.** The layer base
  had no such property: in the flat cells it takes from twenty node indices that
  are structurally identical to the other hundred and eighty.
- Written as a multiple of the mean rather than as an absolute number, so it is
  scale-free and would index itself if issuance were ever turned on.

**One identity makes the base's behaviour predictable in advance.** Since
`Σ(h − mean) = 0`,

```
Σ max(0, h_i − mean) = (n/2) · mean absolute deviation
```

so **the threshold levy is proportional to the dispersion of holdings**. It is
exactly zero on a flat distribution, which is the zero calibration again, and it
*grows* as the economy concentrates. A base defined this way cannot die by
concentration, because concentration is what feeds it.

### 15.4 What section 3 now means

Section 3's sentence, "levied each round at rate `R` on the financial layer
only", **is left as written** and describes the `layer` base, which remains the
default and remains what every result before this section was produced under.
It is no longer the only base. What section 3 should be read as having
registered is *an* instrument, not *the* instrument, and section 15.3 is the
second one. Rewriting section 3 would be editing a pre-registration to match a
later ruling, which is what this repository refuses.

The same applies to the module docstring in `redistribution.py`, which is
updated because it is code documentation rather than registered text.

### 15.5 A6-18, registered before the threshold arm ran

**A6-18 — a base recomputed from a measured stock does not die.** In the
long-horizon cells under `threshold`, the levy collected in the **final** round
is at least `1e-6` of the opening claim stock, in every seed.

The floor is set at the scale of numerical noise rather than at a level chosen
to taste. The registered claim is that the base **does not die**, so the test is
that it is not approximately zero, and the magnitudes are reported beside the
verdict rather than being turned into a threshold nobody had seen. The `layer`
rows are run alongside as the comparison and are **not** judged by this
criterion.

**A renumbering, recorded because it happened after a result existed.** This
criterion was first written as A6-19, leaving A6-18 unused, and a gap in a
pre-registration reads as a withdrawn criterion. It was renumbered to A6-18
after the first registered run had already written `A6-19` into
`results/a6_ratchet.json`. Labels only: no threshold, no scope and no line of
logic changed, and `tests/test_a6_ratchet.py` passed unchanged across the
rename. A6-19 is reused below for a new criterion.

### 15.6 First execution. A6-18 passes, and the margin is the finding

Five seeds, twelve thousand rounds, `R = 0.005`, `access / fair /
infrastructure`. Levy collected, in units of the opening claim stock:

| cell | round 1 | round 12000 | gone |
|---|---|---|---|
| `layer / exp / λ=0` | `3.571e-03` | **`8.543e-05`** | **97.6%** |
| `layer / hill / λ=0` | `3.571e-03` | `5.134e-04` | 85.6% |
| `layer / clip / λ=1e-3` | `3.571e-03` | `8.652e-04` | 75.8% |
| `threshold / exp / λ=0` | `3.110e-03` | **`2.737e-03`** | **12.0%** |
| `threshold / hill / λ=0` | `3.110e-03` | `2.463e-03` | 20.8% |
| `threshold / clip / λ=1e-3` | `3.110e-03` | `2.737e-03` | 12.0% |

The fixed base is drained. The recomputed base is not, which is the shape
section 15.2 describes. The threshold base also collects **less in round one**,
`3.110e-03` against `3.571e-03`, because it takes only the excess above `θ` and
not the whole holding of those above it.

### 15.7 The tax ends up entirely inside the production layer

At round twelve thousand, in every threshold cell, the share of the levy coming
from production-layer nodes is **100%** (98% in one seed of one cell). The payer
count goes from twenty to between fifty and sixty-five. Not one financial-layer
node is above `θ` any more.

**The instrument changes category.** It was designed to move claims from the top
of the graph to the bottom. It ends as a transfer from the production layer to
the production layer, because it succeeded at destroying the position the top
occupied. This is the framework's own thesis biting the instrument built to act
on it: position determines everything, and once the position is gone a levy
assessed on **quantity** has no upstream left to assess.

### 15.8 A realistic base makes the arm more lethal, not safer

The fixed base carried an accidental safety brake: sealing the leak destroys the
levy base, which stops the building, which stops `x`. Section 14.2 read
`clip / λ=0` stopping at `x = 1.000000` as a fixed point of the building
process. **It was not. It was the tax base dying.**

Remove the artefact and the brake goes with it:

| cell | `x` at the end | surviving leak | seed 1 closed at round |
|---|---|---|---|
| `layer / exp / λ=0` | `4.49–5.01` | `0.0067–0.0113` | **3808** |
| `threshold / exp / λ=0` | **`32.56–44.14`** | **`0.0000`** | **1402** |
| `layer / clip / λ=1e-3` | `0.87–0.89` | `0.112–0.135` | never |
| `threshold / clip / λ=1e-3` | **`2.74–3.87`** | **`0.0000`** | **426** |

The collapse arrives between two and nine times sooner. `x` reaching thirty-two
to forty-four puts the `exp` arm across the `37.43` at which section 13.3
registered that it becomes the wall in float64, which is why the surviving leak
reads as exactly zero.

### 15.9 The control cell flipped, and `x* = I/λ` predicts both sides exactly

`clip / λ=1e-3` was A6-16's control, chosen because under the layer base it has
a genuine fixed point and stays open at any horizon. Under the threshold base
**the same cell closes**, and section 13.3's arithmetic says why to three
figures:

| base | levy `I` at the end | `x* = I/λ` | measured `x` |
|---|---|---|---|
| `layer` | `8.652e-04` | `0.865` | `0.87–0.89` |
| `threshold` | `2.737e-03` | `2.737` | `2.74–3.87`, seed 0 at `2.86` |

`λ`'s fixed point still exists and is still settled to within `0.29%` over six
thousand rounds. **It moved above the wall's corner at `x = 1`**, because a base
that does not drain keeps `I` three times higher.

**So the band of `λ` that works is a function of the levy base**, and section
14.7's interior band `[0.001, 0.01]` was measured under a base now known to be
unrealistic. It shifts upward under the threshold base and has not been
remeasured.

Every fixed point observed anywhere in this stage comes from either `λ` or from
the tax base collapsing. **Nothing in the evidence shows the building process
saturating on its own.**

### 15.10 The surviving-leak reading, and its one exception

Sorting all thirty cells measured so far by the leak surviving at the end
separates open from closed with **one** exception:

| leak | cell | verdict |
|---|---|---|
| `0.0000` | `threshold / clip / λ=1e-3` | closed |
| `0.0000` | `threshold / exp / λ=0` | closed |
| `0.0113` | `layer / exp / λ=0` | closed |
| `0.0130` | `layer / clip / λ=1e-4` | closed |
| **`0.0335`** | **`threshold / hill / λ=0`** | **open** |
| `0.0403` | `layer / clip / λ=3e-4` | closed |
| `0.0678` … `0.7286` | fifteen cells, all three shapes interleaved | open |
| `0.8709` … `0.9620` | six cells | closed, the arm buys too little |

The exception is diagnostic rather than noise. **Circulation reaching the
production layer has two sources**: the surviving upward leak, which recirculates
through the financial layer's spending, and the levy-and-rebate loop. Under the
fixed base the second source dies with the first, so the leak alone predicts the
verdict. Under the threshold base the second source survives as a purely
intra-production-layer redistribution, and a leak of `0.0335` therefore holds
where `0.0130` did not.

It does not substitute entirely. `threshold / exp` and `threshold / clip` have a
leak of exactly zero with the levy still flowing at full strength, and one seed
in five still closes. Once the graph is genuinely cut in two, redistribution
inside the lower half does not repair it.

### 15.11 A6-19, registered before its code exists

Section 14.4's A6-16 asks whether a smooth `g` removes the collapse or postpones
it, and it is judged on the `layer` base. **It stays there.** A criterion is not
moved to a different arm after it has returned a verdict, even a null one.

**A6-19 asks the same question on the threshold base**, as a separate criterion
with its own cells and its own control.

- **Judged**: `threshold / exp / λ=0` and `threshold / hill / λ=0`.
- **Control**: `threshold / clip / λ=1e-2`, and **not** the `λ=1e-3` cell A6-16
  uses, because section 15.9 shows that cell closes under this base. At
  `λ=1e-2` the fixed point is `x* ≈ 0.27`, below the wall's corner, so the
  control has a surviving leak of about `0.73` and should stay open at any
  horizon. **If it closes too, A6-19 returns no verdict**, exactly as A6-16 does.
- **Three-valued, on the same rule as A6-16.** Both judged cells closed is a
  pass; a judged cell open with `x` settled is a fail; a judged cell open with
  `x` still climbing is **no verdict**, because that is A6-5's mistake.

**The registered prediction is that both close**, and the argument is available
before the run, which is what makes it a prediction rather than a description.
The threshold base's levy is proportional to dispersion (section 15.3), so it
cannot die by concentration; at `λ = 0` the gap is cumulative investment and
therefore unbounded; a smooth `g` then drives the surviving leak to zero. The
chain uses only quantities already measured. `threshold / exp` reached the end of
that chain at twelve thousand rounds already.

**The horizon moves to sixty thousand rounds, and that is not a change of
criterion.** A6-16 was built three-valued precisely so that "the horizon is too
short" would trigger a longer run instead of a wrong answer, and it returned that
branch at twelve thousand rounds with `layer / hill`'s `x` still climbing at
fifty percent per six thousand rounds. Extending is the response the criterion
itself prescribes. Sixty thousand is set by two independent readings and not by
convenience:

- `layer / hill`'s `x` fits `4.50·ln t − 30.35` across five seeds, which puts a
  surviving leak of `0.05` at about **fifty-eight thousand** rounds;
- `threshold / hill`'s `x` grows close to linearly, `2.45e-3` per round, which at
  sixty thousand rounds gives `x ≈ 147` and a surviving leak of about `0.0068`,
  inside the range in which closure has already been observed.

The twelve-thousand-round readings in sections 15.6 to 15.10 stand as recorded
and are superseded as verdicts, not withdrawn as measurements.

### 15.12 What this still does not establish, and one thing it must not be read as

**`g`'s shape is an input, not an output.** The model cannot say whether
education, or infrastructure in general, saturates in the world. It says what
happens to circulation *given* an assumption about `g`. The registered default,
`exp`, encodes the assumption that marginal returns decay quickly but never
reach zero; `hill` encodes slower decay with the same property; `clip` encodes a
good that is genuinely finished at a point, which is the minority case and is
present only as the reduction point and as A6-14's control.

Anything in a write-up of the form "the model shows that public provision never
becomes sufficient" is quoting an assumption back as a result.

**What `g` bounded at one does encode is accounting and not a claim about the
good.** No more than a hundred percent of upward leakage can be removed. The
*shape* is a claim about what the last few percent of it costs.

**The two senses of "enough" are opposite, and both are real.** In the arm's
sense, `K − B` stops growing, and `λ > 0` is what delivers that. In the welfare
sense, investment can stop, and `λ > 0` is what destroys that: halting lets `B`
catch `K`, drives the gap to zero and gives up the whole advantage. Section
12.2's comparative statics said the second; the first is new here. **The rising
frontier is simultaneously the reason provision never becomes sufficient and the
reason accumulated provision does not run away and sever the economy.**

**A note on units that section 16 will have to settle.** `R*(transfer) = 0.060`
is six tax points per round against real net wealth taxes of 0.15% to 1.1% per
year. Section 7 already says `R*` is not a tax rate for any real economy, so
this is not a contradiction. It is a reminder that one rule applies here too:
**without a mapping from rounds to time, there is no
saying whether the model's `R` is above or below the return on capital, and that
is the single parameter deciding whether a base drains.**

---

## 16. The long horizon settles it, 2026-08-12

Five seeds. The `λ` curve at two thousand rounds, the rescan at two thousand,
the long-horizon block at sixty thousand with `layer/hill` carrying a registered
multiple of three. `results/a6_ratchet.json`.

**Nine of eleven criteria pass.** The two failures are A6-10 and A6-11, both on
the grid-floor split §14.5 records, and neither has moved.

### 16.1 A6-16 and A6-19 agree, and the answer is *postpones*

Both ask whether a smooth `g` removes the collapse or defers it. A6-16 asks it
on the `layer` base, A6-19 on `threshold`. **Both pass, and they pass in the
same direction.**

| cell | rounds | surviving leak | `end / start`, five seeds | closed at round |
|---|---|---|---|---|
| `threshold / exp / λ=0` | 60000 | `0.0000` | `1.68, **0.13**, 1.61, 1.86, 1.22` | 1402 |
| `layer / exp / λ=0` | 60000 | `0.0010–0.0022` | `1.69, **0.09**, 1.62, 1.88, **0.74**` | 3808, 50440 |
| `threshold / hill / λ=0` | 60000 | `0.0056–0.0064` | `1.77, **0.27**, 1.68, 1.93, 1.81` | 15522 |
| `layer / hill / λ=0` | **180000** | `0.0155–0.0196` | `1.90, **0.45**, 1.83, 2.06, 2.06` | **64854** |
| `layer / clip / λ=1e-3` (control) | 60000 | `0.112–0.135` | all `≥ 2.51` | never |
| `threshold / clip / λ=1e-2` (control) | 60000 | `0.665–0.676` | all `≥ 0.97` | never |

Both controls held, and held where they were registered to. `layer / clip`
settled at `x = 0.87–0.89`, `threshold / clip` at `x = 0.32` against a predicted
`x* ≈ 0.27`, both moving `0.01%` across the second half of thirty thousand
rounds.

**So the answer does not depend on who pays.** A smooth saturation buys time and
nothing else. Under the wall the leak is sealed by round three hundred; under
`exp` it takes to round three thousand eight hundred; under `hill` on the
threshold base to fifteen thousand and on the layer base to sixty-five thousand.
The ordering is the ordering of how fast each shape drives the leak down, and
every one of them arrives.

### 16.2 The correction of a correction. Three layers, all kept

| when | what was said |
|---|---|
| §12.4, registered before any of this ran | "smooth saturation `g` … **on its own it does not fix A6-5**" |
| §14.2, after two thousand rounds on the layer base | "that sentence is false. `g` alone does fix it" |
| **§16, after sixty and a hundred and eighty thousand rounds on both bases** | **§14.2 was wrong. It was a short horizon on a levy base since shown to be an artefact. §12.4 stands as registered.** |

**None of the three is rewritten.** §12.4 keeps its wording, §14.2 keeps its
correction, and this section carries the correction of the correction. What the
sequence is worth is exactly that it is on the page: a wrong reading was issued
with confidence from a run that looked long enough, on an arm that looked
faithful enough, and it took two independent changes, the horizon and the levy
base, to expose it.

### 16.3 Every fixed point in this stage comes from `λ`

At sixty thousand rounds, `x` in the two control cells moves by `0.01%` across
the second half. At the same horizon, `x` in every `λ = 0` cell is still
climbing: `+13%` for `layer / exp`, `+49%` for `layer / hill`, `+102%` and
`+117%` for the two threshold cells.

There is no cell anywhere in this stage in which the building process stops on
its own. The one that looked like it did, `clip / λ=0` halting at
`x = 1.000000`, was the tax base dying (§15.8). **`λ` is the only stop the
mechanism has**, and §12.2's comparative statics acquire a second meaning
because of it: the requirement to keep investing and the guarantee against
running away are the same condition.

### 16.4 Seeds fall one at a time, and the threshold base buys a lower floor

Sorting the six cells by surviving leak gives a monotone count of closures, with
one systematic inversion:

| leak | cell | seeds closed |
|---|---|---|
| `0.0000` | `threshold / exp` | 1 |
| `0.0022` | `layer / exp` | **2** |
| `0.0064` | `threshold / hill` | 1 |
| `0.0196` | `layer / hill` | 1 |
| `0.1345` | `layer / clip / λ=1e-3` | 0 |
| `0.6758` | `threshold / clip / λ=1e-2` | 0 |

The inversion is the finding. `layer / exp` at a **higher** leak has **more**
seeds closed than `threshold / exp` at zero. Seed 4 is the case: it closes under
`layer / exp` at round 50440 and ends at `1.22` under `threshold / exp`, at a
lower leak.

**The cleanest measurement is seed 1 under `hill` on the two bases**, same
shape, same `λ = 0`, differing only in who pays:

| base | closed at round | `x` there | leak at closure |
|---|---|---|---|
| `layer` | 64854 | `≈ 31.6` | **`0.031`** |
| `threshold` | 15522 | `≈ 38.6` | **`0.025`** |

The threshold base survives to a leak about a fifth lower. That is the second
circulation source §15.10 identified, now measured rather than inferred: the
levy keeps running as a purely intra-production-layer redistribution, and it
substitutes for part of the upward leak. It does not substitute for all of it,
since `threshold / exp` closes a seed at a leak of exactly zero.

### 16.5 A6-18 at the long horizon, and one base that grew

| cell | round 1 | final round | change |
|---|---|---|---|
| `layer / exp / λ=0` | `3.571e-03` | `1.693e-05` | **−99.5%** |
| `layer / hill / λ=0` | `3.571e-03` | `1.456e-04` | −95.9% |
| `layer / clip / λ=1e-3` | `3.571e-03` | `8.664e-04` | −75.7% |
| `threshold / exp / λ=0` | `3.110e-03` | `2.738e-03` | −11.9% |
| `threshold / hill / λ=0` | `3.110e-03` | `2.683e-03` | −13.7% |
| `threshold / clip / λ=1e-2` | `3.110e-03` | `3.241e-03` | **+4.2%** |

The last row is the identity of §15.3 doing its work. A threshold levy is
proportional to the mean absolute deviation of holdings, so a base that runs at
a `λ` high enough to keep the economy in a steady state **collects more at the
end than at the start**, because the distribution has spread. The fixed base
under the same conditions lost three quarters of its revenue.

Payer counts tell the same story from the other side: twenty in every layer
cell at every horizon, against twenty-four to sixty-six under `threshold`, and
one hundred percent of the levy coming from production-layer nodes in the two
`λ = 0` threshold cells.

### 16.6 A6-9's band has a horizon-dependent low end. Recorded, not withdrawn

A6-9 passed, and its band is `λ ∈ [0, 0.01]` on the two-thousand-round curve.
**That low endpoint is a two-thousand-round artefact.** At `λ = 0` the same
cells close under both smooth shapes once the horizon is long enough, at round
3808 for `exp` and 64854 for `hill`.

A6-9 is registered at two thousand rounds and is not withdrawn: it measured what
it said it would measure. What may not be said is that `λ = 0` holds the economy
open, and any write-up quoting the band's low end without the horizon attached
is quoting an artefact. **The band's upper end at `0.01` is unaffected**: that
failure is the arm buying too little, which a longer run does not repair.

This is the third time in this stage that a short horizon produced a confident
wrong reading, after A6-5 at three hundred rounds and §14.2 at two thousand.

### 16.7 Two sizing estimates, both wrong in the same direction

Recorded because the discipline is worth more than the estimates were.

- §14.7 fitted `layer / hill`'s `x` to `4.50·ln t − 30.35` on five points
  between two thousand four hundred and twelve thousand rounds, and predicted
  `x ≈ 19` at fifty-eight thousand. **Measured: `28–34` at sixty thousand.**
  Extrapolating a log fit five times beyond its data undershot.
- §15.11 then sized the extension from measured increments and put the crossing
  near a hundred and ten to a hundred and twenty thousand rounds. **Measured:
  round 64854.**

Both erred towards the cell moving faster than predicted, so the sixty-thousand
run missed the crossing by under eight percent and the three-times margin caught
it. The margin was registered on the grounds that overshooting costs three
minutes and undershooting costs a whole pass over the stage, and that is what it
bought.

### 16.8 What is still open

- **A6-10 and A6-11** remain failed on the split §14.5 names. The diagnosis is
  unchanged and is not a resolution problem: `R*` in this arm is proportional to
  `λ`, so it falls off any grid fixed in advance as `λ` shrinks. Asking for it
  as a level is the wrong question and a criterion asking the right one has not
  been written.
- **A6-15's interior band `[0.001, 0.01]` was measured on the layer base.**
  §15.9 shows the same `λ` gives a three times larger `x*` under `threshold`, so
  the band shifts upward there. Not remeasured.
- **The `λ` curve is entirely on the layer base at two thousand rounds.** §16.6
  is the reason that matters.
- **The rounds-to-time mapping.** §15.12. Without it there is no saying whether
  this model's `R` sits above or below the return on capital, and that is the
  parameter deciding whether a base drains.

---

## 17. What a round is, and what the horizon numbers are not

§16.8 left the rounds-to-time mapping open. It is closed here in the only way
that is honest, which is smaller than it sounds.

### 17.1 A round reads as a year, and the source is already in the repository

`calibration.py` takes the spending propensities from Fagereng, Holm & Natvik
(2021), Norwegian lottery wins in administrative panel data, and quotes them as:
low-liquidity winners of the smallest prizes spend essentially all of the win
**within the year**, high-liquidity winners of the largest prizes slightly below
one half. A propensity estimated over a year, applied once per round, makes a
round a year. That sentence has been in the file since the calibration was
written, as a caveat, and was never carried forward as a unit.

Read that way:

| reading | per year | against |
|---|---|---|
| `R*(transfer) = 0.060` | **6.0%** | Norway 1.0%, Switzerland 0–0.3%, Spain up to 3.5% |
| `R*(infrastructure) = 0.010` at `λ = 1e-2` | **1.0%** | Norway's rate exactly |
| the wall seals at round 294 | 294 years | |
| seed 1 closes, `threshold/exp` | 1,400 years | |
| seed 1 closes, `layer/hill` | 65,000 years | |

### 17.2 The horizons are ordinal. They are not a forecast

**Nothing in §16 should be read as a claim about the year 65,000.** By that
point every other assumption in this model has broken down thousands of times
over: the graph is fixed, there is no technical change, no population, no
external sector, and the claim stock is conserved. A real economy is not
stationary and is not driven by one mechanism.

§7 already registered the discipline this is an instance of: **what transfers is
the comparison, not the level.** Applied to time, the transferable content of
§16 is the *ordering and the ratios*, all measured inside one model under one
set of assumptions:

- the wall seals fastest, then `exp`, then `hill`;
- a realistic levy base brings the closure forward by a factor of two to nine;
- `λ > 0` stops it altogether, and is the only thing in the stage that does.

Those are internal comparisons. The absolute horizons are the units they were
measured in and are not a prediction of anything.

### 17.3 The one place the year reading earns its keep

§12.2's own worked example of the frontier moving is Prussian compulsory
schooling to a modern nine-year system, which is roughly a hundred and twenty
years. A gap half-life of a hundred and twenty years is
`λ = ln 2 / 120 ≈ 0.0058` per year.

**The registered band is `λ ∈ [0.001, 0.01]`**, fixed from the arithmetic
`x* = ι·R·s/λ` in §13.3 before anything ran and with no reference to any
historical example. The value implied by the document's own example lands
inside it, towards the upper end.

That is a check on the band's plausibility and it does not need the horizons to
be forecasts. It also sharpens what §16.1 established: **the collapse is a
statement about a counterfactual in which the frontier never moves.** At the
absorption rate the historical example implies, the arm has a fixed point and
holds it at sixty thousand rounds to within `0.01%`.

### 17.4 Three limits on the mapping, and what each one governs

- **The estimand does not match.** `calibration.py` says so itself: FHN measure
  a marginal propensity to consume out of a transitory income shock, and this
  model's propensity is a spending rate out of holdings. The analogy licenses
  the range, the ordering and the period, not the exact values, and the period
  inherits all of that looseness.
- **The wage channel and the issuance rule have not been checked against it.**
  `WageChannel(bill=6.0)` is six units of a hundred-unit claim stock per round,
  and the endogenous issuance rule is calibrated elsewhere. If those imply a
  different period, that is a finding rather than a detail: it would mean the
  model mixes timescales.
- **§7 is unchanged.** `R*` is still not a tax rate for any real economy. What
  §17.1 does is give the round counter a scale, not claim that the model is
  calibrated to anything.

---

## 18. The other side of the same instrument, 2026-08-13

§15 corrected **who pays** and did not look at **who receives**. This section is
that correction, and it is here because a repository-wide audit went looking for
the shape of the §15 defect elsewhere and found it three lines below §15's own
edit.

### 18.1 What was wrong, and how it survived §15

`_post_round` moved claims in two statements. §15 rewrote the first into
`_assess`, so under the threshold base the payers are recomputed from measured
holdings every round. The second was left as it stood:

```python
self.holdings[self._l2_idx] += total / self._l2_idx.size
```

`_l2_idx` is the hundred and eighty node indices assigned to the production
layer at construction. So the corrected instrument taxes a **measured**
magnitude and pays a **fixed address list**, and nothing in the run says so.

The consequence is not subtle once it is measured. At the registered
infrastructure cell over twenty thousand rounds, `λ = 1e-3`, `R = 0.005`,
threshold levy, five seeds:

| levy base | rebate base | nodes on **both** sides in one round, worst | recipients |
|---|---|---|---|
| layer | layer | 0 | 180 every round |
| layer | threshold | 5 | 133 to 183 |
| **threshold** | **layer** | **61** | 180 every round |
| threshold | threshold | 0 | 123 to 183 |

The third row is the shipped configuration of §15's correction. **Sixty-one
nodes pay the levy and receive the rebate in the same round**, and on a
seed-by-seed mean it is fifty-four. Meanwhile the financial-layer nodes that
have fallen below `θ` pay nothing, because they are below the threshold, and
receive nothing, because they are not in `_l2_idx`. At the twenty-thousandth
round of seed zero there are four of them.

The second row is the same error mirrored, and it is run to show that the
diagnosis is about **mismatch** and not about the word "layer": a layer levy
with a threshold rebate levies a financial-layer node that is below `θ` and
pays it a rebate in the same breath, because the layer levy never looks at `θ`.

### 18.2 `RebateSpec`, and why it is equal shares

The switch has the same shape as `LevySpec` and the same default, so everything
that ran before it exists is untouched and A6-7 still reduces the ratchet to the
`A6Model` that produced §9.2. Verified: ninety-six pairs across two access arms,
two retention arms, two channels, four rates and three seeds, zero mismatches on
`effective_support`, `holdings`, `total_volume`, `leak_factor`, `invested` and
the Palma trajectory.

`threshold` pays the nodes **below the same `θ`** the levy is assessed above, in
**equal shares**. Equal shares rather than in proportion to the shortfall is a
deliberate refusal to move two things at once: the existing rebate is an equal
split, so changing membership alone isolates the membership. A shortfall-weighted
rebate is a different arm and is not written here.

`θ` is the levy's own, not a second number. One instrument, one threshold, taxed
above it and paid below it. A rebate threshold free to differ would be a second
free parameter and would be the first thing anyone tuned.

**Both sides are read off the holdings before either moves, and that ordering is
load-bearing.** A real instrument assesses both sides on one measurement date.
Taking the recipients off the post-levy holdings would let a node pay and then
immediately qualify to receive, which is the overlap this switch exists to
remove, reintroduced through ordering rather than through membership. This is
the same class of within-round ordering decision as §12's `B` before `K`, and it
is checked rather than trusted: `both_sides_history` counts the intersection
every round.

**The empty-recipient case is handled and recorded rather than assumed away.**
If no node is below `θ`, the rule names nobody, and the claims still have to
land somewhere: conservation is not negotiable and holding them outside the
ledger would make the levy a destruction of claims rather than a transfer. They
are split across every node and the round is recorded in
`rebate_fallback_history`. It has never fired.

### 18.3 A6-20, and one scope correction disclosed

> **A6-20.** In every round of every cell: matched pairs, meaning `layer/layer`
> and `threshold/threshold`, put **no** node on both sides of the transfer;
> mismatched pairs put **at least one**; claims are conserved to within `1e-6`
> of the opening stock; and the empty-recipient fallback does not fire.

Every quantity is fixed by construction, so there is nothing here to tune. The
criterion is two-sided on purpose. A zero in the mismatched rows would not be a
success, it would mean the distribution never put anybody in the overlapping
region and the comparison was empty.

**The first draft demanded zero in all four cells and failed on the two
mismatched ones.** That is the criterion having the wrong scope, not the model
misbehaving: those cells are supposed to overlap. It is disclosed here rather
than silently repaired, and the repair is only legitimate because **nothing had
been registered when it happened**: the first form never left the experiment
file and A6-20 reaches this page in the corrected form. A criterion already on
this page would have been left failing, as A6-1 is.

**Result: pass.** Five seeds, twenty thousand rounds, four cells, at the
registered rate. Worst claim drift `1.9e-11` against the `1e-6` bound, zero
fallback rounds, the two matched rows at zero and the two mismatched rows at
sixty-one and five.

### 18.4 What the correction does to A6's numbers, and what is still open

Almost nothing, at the cell measured. Seed zero, twenty thousand rounds,
threshold levy, the rebate switched from `layer` to `threshold`:

| | layer rebate | threshold rebate |
|---|---|---|
| gap `K − B` | 243.855 | 243.757 |
| surviving leak | 0.087287 | 0.087373 |
| Palma, final round | 23.073 | 22.889 |

The gap moves by four hundredths of a percent and the Palma falls by eight
tenths of a percent, which is the direction the correction predicts: money that
was going to every downstairs node now goes only to the ones below `θ`.

**This is one cell and it is not a robustness claim.** No threshold for the
outcome comparison is registered and none is invented here. §16.6 and §15's
interior band are both still measured on the **layer** base at two thousand
rounds, and they now need re-measuring on a corrected instrument that has two
switches rather than one. That is the open item, and it is open on this page
rather than in a comment.

**What §18 does not touch.** A6-7 through A6-19 all ran with the default rebate,
which is `layer`, so every number in §13 to §17 stands exactly as printed. This
section adds a switch and a criterion; it withdraws nothing.

---

## 19. A6-21, registered before its code exists

§16.8 leaves A6-10 and A6-11 failed with a diagnosis and no criterion: `R*` in
this arm is proportional to `λ`, so it falls off any rate grid fixed in advance
as `λ` shrinks, and asking for it **as a level** is the wrong question. This
section writes the right one. It is registered here, in full, before the code
that evaluates it exists.

**A6-10 and A6-11 are not repaired and not withdrawn.** They keep their
failures, their thresholds and their split, in §5, §13.4 and §14.5. A6-21 is a
different question about the same mechanism, in the same relationship to them as
§15's A6-18 stands to A6-1.

### 19.1 Why the level was the wrong question

§12.2 registers the ratchet's fixed point as `K − B → I/λ`, and §15.9 confirms
it to three figures on both levy bases. The effect enters through
`x = ι·max(0, K − B)/claims₀`, so at the fixed point

`x* = ι · I / (λ · claims₀)`

Closure needs `g(x*)` past some level, so it needs `x*` past some level, so it
needs `I/λ` past some level. `I` is the levy actually collected per round and
rises with the rate. **The critical rate is therefore whatever makes `I/λ` big
enough, and that scales with `λ`.** A grid of rates fixed in advance is a grid
of the wrong variable: it is measuring `R*` when the mechanism only ever
determines `R*/λ`.

This is consistent with what §14.5 already measured. At `λ = 1e-2`, `R* = 0.010`
gives `R*/λ = 1.0`. If that ratio is the invariant, then at `λ = 1e-3` the
critical rate is `0.001`, which is **below** the registered grid's smallest
non-zero point of `0.005`, and "pinned at the floor" is exactly what a grid in
the wrong variable reports when the answer is underneath it.

### 19.2 The criterion

> **A6-21.** In the infrastructure arm under access with fair retention, with
> the ratchet on and `g = exp`, scan the levy rate as `R = ρ·λ` over the fixed
> ratio grid `ρ ∈ {0.125, 0.25, 0.5, 1, 2, 4, 8}` at `λ ∈ {1e-3, 3e-3, 1e-2}`.
> Let `ρ*` be the smallest `ρ` whose rate holds the support set open, taken per
> seed and reported as the median. The criterion holds when **`ρ*` is the same
> grid point at every `λ`, or differs by at most one step**, and **`ρ*` is at
> neither end of the `ρ` grid** at any `λ`, and **every seed has a solution**.

**The grid is the tolerance and no other tolerance is registered.** The ratio
grid is geometric with a factor of two, so `ρ*` is resolved to within a factor
of two by construction, and "the same, or one step apart" is the strongest
statement that resolution supports. Inventing a percentage band on top of it
would be inventing precision the scan does not have.

**Each of the three failure modes means something different and they are not
interchangeable.**

| Outcome | What it means |
|---|---|
| `ρ*` moves by more than one step across `λ` | `R*` is **not** proportional to `λ` and §14.5's diagnosis is wrong. The failure is the finding and the diagnosis is what gets withdrawn, not the criterion. |
| `ρ*` sits at the bottom of the `ρ` grid | The same defect as A6-10's, one variable up: the answer is under the grid again. Reported as a failure and **not** repaired by widening the grid inside the same run. |
| `ρ*` sits at the top of the `ρ` grid | As above, above. |
| A seed has no solution at some `λ` | The ratchet does not hold that seed open at any rate in the scanned range. A6-9's territory, reported here rather than absorbed. |

### 19.3 The horizon scales with `λ`, and that is not a convenience

The ratchet's relaxation time is `1/λ`: the gap approaches `I/λ` geometrically at
rate `λ` per round. A cell run for fewer rounds than a few multiples of `1/λ` has
not reached the fixed point the criterion is about, and would report a transient.
§16 is this stage's own precedent for extending a horizon when the criterion says
the horizon is too short.

**Registered: each `λ` runs for `max(2000, 10/λ)` rounds**, which is ten
relaxation times or the stage's registered long horizon, whichever is larger.

| `λ` | rounds | `1/λ` | relaxation times |
|---|---|---|---|
| `1e-2` | 2000 | 100 | 20 |
| `3e-3` | 3334 | 333 | 10 |
| `1e-3` | 10000 | 1000 | 10 |

Cost is 3 `λ` × 7 `ρ` × 5 seeds = 105 runs, 537,000 round-units, on the order of
ten minutes. **`λ = 3e-4` and below are excluded on cost**: at ten relaxation
times they need thirty-three thousand rounds each and would triple the stage.
That is a limit on the span this criterion tests, one decade, and it is a
budget decision rather than a finding.

### 19.4 Reported beside it and not judged

**`I(R*)/λ`, the measured steady-state levy at the critical rate over `λ`.**
This is the parameter-free form of the same hypothesis: §19.1's derivation
assumes `I` rises with `R`, and this quantity does not. If the mechanism is
`x* = I/λ` then this is constant across `λ` whatever `I(R)` looks like. **No
threshold is registered for it**, because none existed before the quantity did,
and §14.6 is the precedent for reporting such a thing rather than gating on it.

**The settledness of `x` in every cell**, by the same `X_SETTLED` reading §16
uses. A cell whose `x` is still climbing has not reached the fixed point the
criterion assumes, and it must be visible rather than inferred from the horizon
rule having been followed.

### 19.5 Result: `R* = λ`, and A6-21 passes

Five seeds, the registered ratio grid, the registered horizon rule, ten minutes.

| `λ` | rounds | `ρ*` per seed | median `ρ*` | `R* = ρ*·λ` | `I(R*)/λ`, mean | `x` |
|---|---|---|---|---|---|---|
| `1e-3` | 10000 | `1, 1, 1, 1, 1` | **1.0** | `0.00100` | `0.686` | settled, `+0.22%` |
| `3e-3` | 3334 | `1, 1, 1, 0.5, 1` | **1.0** | `0.00300` | `0.621` | settled, `+0.41%` |
| `1e-2` | 2000 | `1, 1, 1, 0.5, 1` | **1.0** | `0.01000` | `0.609` | settled, `+0.02%` |

**Pass.** Worst separation between medians: **zero grid steps**. Not at either
end of the ratio grid. No unsolved seed. `x` settled in every cell against the
`1%` reading §16 registered, so the horizon rule delivered what it was meant to
rather than merely having been obeyed.

**The critical levy rate equals the absorption rate**, to the factor of two the
grid resolves. That is the sharpest thing this stage has said about `R`, and it
is a statement §14.5's grid could not have made in either direction.

**§14.5's "pinned at the grid floor" is now explained rather than repaired.** At
`λ = 1e-3` the critical rate is `0.001`, five times below the registered grid's
smallest non-zero point of `0.005`. A6-10 asked where `R*` was on a grid that
did not extend to where it was. **A6-10 and A6-11 stay failed.** Nothing here is
carried back into them.

**The parameter-free form agrees.** §19.1's derivation assumes `I` rises with
`R`; `I(R*)/λ` does not, and it comes out at `0.686`, `0.621`, `0.609` across a
decade of `λ`, a spread of twelve percent on the means. Since `ι = 1` in every
registered cell, that is a direct reading of the closure condition:

`x* = ι · I(R*) / (λ · claims₀) ≈ 0.61 to 0.69`

**The critical `x*` is a pure number**, and everything else in the relation
follows from it. `R*` is not a property of the tax at all: it is whatever rate
makes the gap reach a fixed height, and the ratchet sets that height at `I/λ`.

**One seed carries the dispersion and it is not hidden.** Seed 3 solves at
`ρ* = 0.5` at the two larger `λ`, one grid step below the rest, which is what
drags its `I(R*)/λ` to `0.370` and the cell means below `0.686`. Five seeds with
one at one step is inside what the criterion registered as agreement, and it is
also the whole of the spread: the other four sit between `0.65` and `0.70` in
every cell.

**What this does not say.** It is one decade of `λ`, one shape, one levy base
and one channel. §19.3 records the cost reason for the span. The levy base is
`layer`, so this inherits §15.9's warning directly: under `threshold` the same
`λ` gives an `I` three times larger, so `x* = I/λ` moves and **`R*` should be
expected to move with it**. That re-measurement is §16.8's open item and this
criterion does not close it. What A6-21 establishes is the **form** of the
relation, `R* ∝ λ`, not the constant in front of it.

---

## 20. A6-22 and A6-23, registered before their code exists

§16.8 leaves two readings measured on an instrument now known to be wrong in
three separate ways, and §19.5 adds a fourth thing wrong with how they were
read. This section registers the re-measurement. **A6-9 and A6-15 are not
repaired and not withdrawn**: they keep their bands, their thresholds and their
horizons, on the layer base at two thousand rounds, in §13.4 and §14.7.

### 20.1 Four things wrong, and only one of them is the levy base

**The levy base.** §15.9: the same `λ` gives an `I` three times larger under
`threshold`, so `x* = I/λ` moves and the band of `λ` that works moves with it.

**The rebate base.** §18: the recipients were a fixed address list while the
payers were measured. Corrected there, never carried into the curve.

**The horizon.** §16.6: A6-9's low end is horizon-dependent, and §19.3 gives the
reason in one line. The ratchet relaxes at rate `λ` per round, so two thousand
rounds is twenty relaxation times at `λ = 1e-2` and two at `λ = 1e-3`. The curve
was comparing a settled cell against a transient and calling the difference an
effect of `λ`.

**And a fourth, which is new and is about the reading rather than the run.**
§19.5 measured `R* = λ`. A curve at a **fixed** rate therefore crosses every `λ`
at a different multiple of that `λ`'s own critical rate. At the registered
`R = 0.005`:

| `λ` | `R / R*` |
|---|---|
| `1e-3` | 5 |
| `3e-3` | 1.7 |
| `1e-2` | 0.5 |
| `3e-2` | 0.17 |
| `1e-1` | 0.05 |

**A6-9's curve was never a curve in `λ` alone.** It swept `λ` and the policy's
strength relative to `λ` together, in opposite directions, which is exactly the
stratification error `MEASUREMENT.md` §4 names. That is a reading of an existing
result and it is recorded here rather than by editing §13.4.

### 20.2 One change at a time

The re-measurement is a factorial in the two bases at the corrected horizon, so
that the three defects can be told apart instead of being fixed in one step and
attributed to whichever one is being discussed:

| column | levy | rebate | isolates |
|---|---|---|---|
| A | `layer` | `layer` | the **horizon** alone, against §13.4's own reading |
| B | `threshold` | `layer` | the **levy base**, added to A |
| C | `threshold` | `threshold` | the **rebate base**, added to B |

Column C is the corrected instrument and is what A6-22 and A6-23 are judged on.
A and B are run so that a difference between C and §13.4 can be attributed
rather than asserted.

**Registered `λ` set: `{1e-3, 3e-3, 1e-2, 3e-2, 1e-1}`, horizon
`max(2000, 10/λ)`**, which is §19.3's rule reused unchanged.

`λ = 3e-4` and below are excluded on cost, the same budget decision §19.3
records. **`λ = 0` is excluded for a different reason and it is not a budget
one**: it has no fixed point to relax to, so no horizon rule can make its
reading settled, and §16.6 already records that its two-thousand-round value is
an artefact. Excluding it here does not remove that record.

### 20.3 The criteria

> **A6-22.** On column C, at the registered rate `R = 0.005`, with `g = exp` and
> the registered horizon rule, the band of `λ` in which the support set stays
> open in every seed is **non-empty**, by A6-9's own one-sided test: end-over-
> start effective support at or above `0.9` in all five seeds.

> **A6-23.** On column C, with `g = clip`, the band is **interior to the scanned
> `λ` set**: at least one closed cell below the open block and at least one
> above it. This is §14.7's interior claim asked where §15.9 says it must have
> moved.

| Outcome | What it means |
|---|---|
| A6-22's band is empty | On a realistic base with a corrected rebate and an adequate horizon, **no absorption rate keeps this economy open at the registered levy**. That is a much harder result than A6-9's and it would be the stage's headline. |
| A6-23's band runs to the bottom of the scanned set | Not interior within what was scanned. The band has moved below `1e-3` rather than above, which is the **opposite** of what §15.9 predicts, and the prediction is what gets withdrawn. Reported as a failure and not repaired by extending the scan downward inside the same run. |
| A6-23's band runs to the top | The band has moved above `1e-1`, consistent with §15.9's direction but further than the scan reaches. Same treatment. |
| A6-22 passes and column A does not match §13.4 | The horizon alone moved the old reading, and §16.6's warning was larger than §16.6 stated. |

### 20.4 Reported beside them and not judged

**The `ρ = 1` column**, meaning `R = λ` rather than `R = 0.005`, on column C with
`g = exp`. §19.5 makes this available for the first time: it is the curve in `λ`
with the policy held at each `λ`'s own critical strength, which is the
comparison §20.1's fourth defect says the fixed-rate curve cannot make. **No
threshold is registered for it.** It is a quantity nobody has seen and §14.6 is
the precedent for reporting such a thing rather than gating on it.

**Both band ends and contiguity in every column**, since a band with a hole in
it is a different object from a band and A6-9's `bands` block already reports
the distinction.

### 20.5 Result: both pass, and the fixed-rate curve was mostly about the horizon

Five seeds, the registered `λ` set, the registered horizon rule, eight minutes.
End-over-start effective support, minimum over seeds, against A6-9's floor of
`0.9`:

| column | `1e-3` | `3e-3` | `1e-2` | `3e-2` | `1e-1` | band |
|---|---|---|---|---|---|---|
| A `exp` layer/layer | 2.473 | 1.388 | 0.963 | 0.879 | 0.854 | `0.001` to `0.01` |
| B `exp` threshold/layer | 2.319 | 1.355 | 0.946 | 0.873 | 0.851 | `0.001` to `0.01` |
| **C `exp` threshold/threshold** | 2.328 | 1.355 | 0.945 | 0.873 | 0.851 | **`0.001` to `0.01`** |
| C `clip` threshold/threshold | 0.136 | 2.482 | 0.972 | 0.875 | 0.851 | **`0.003` to `0.01`** |
| C `exp`, `ρ = 1` | 1.069 | 1.078 | 1.109 | 1.187 | 1.425 | `0.001` to `0.1` |

**A6-22 passes.** The band on the corrected instrument is non-empty and
contiguous, `0.001` to `0.01`.

**A6-23 passes.** The `clip` control band is `0.003` to `0.01`, closed at
`0.001` below it and at `0.03` above it, so it is interior to the scanned set.
**And it moved in the direction §15.9 predicted**: §14.7 measured `[0.001,
0.01]` on the layer base and the low end has moved up one grid step, which is
what a base that does not drain does when it keeps `I` three times higher and
pushes `x*` past the wall's corner.

### 20.6 Which of the three defects actually moved the number

**The horizon, almost entirely.** Column A is the *original* instrument, layer
levy and layer rebate, and at the corrected horizon it already gives the band
`0.001` to `0.01`. The two base changes then move the readings by six percent at
`λ = 1e-3` and by under two percent everywhere else, and the rebate change
alone moves them by less than half a percent, once in each direction.

So §16.8 listed three open items and they were not equally open. **§15.9's
warning about the band moving is true of the wall and not of the smooth shape**:
the `clip` column's low end moved a grid step, the `exp` column's did not move
at all. That is a sharper statement than the open item made, and it is only
visible because the columns were run one change at a time rather than corrected
in one step.

**The `clip` column at `λ = 1e-3` is where the levy base bites**, and it bites
unevenly: end-over-start runs `0.136` to `1.87` across five seeds, one economy
collapsing to a seventh while another grows by seven eighths. A cell whose seeds
disagree that violently is not a cell with a mean, and it is reported as the
spread rather than as a number.

### 20.7 The scaled column, and what it does to A6-9's shape

Reported and not judged, per §20.4, and it is the largest thing in this section.

With the policy held at each `λ`'s own critical strength, `R = λ`, **the band is
the entire scanned set** and end-over-start **rises monotonically with `λ`**:
`1.069, 1.078, 1.109, 1.187, 1.425`. Every absorption rate across a decade keeps
the economy open, and more absorption is monotonically better.

The fixed-rate curve says the opposite at its top end: it closes at `λ = 0.03`
and `λ = 0.1`. §20.1's table is why. At `R = 0.005` those two cells are running
a levy at `0.17` and `0.05` of their own critical rate. **They do not close
because absorption is too high. They close because the tax is too small for
them**, and the fixed-rate curve reads the second as the first.

**This is a reading of A6-9's shape and it does not repair A6-9.** A6-9 keeps
its curve, its band and its floor. What is registered here is that the top end
of that band is an artefact of holding `R` fixed while sweeping the quantity
that sets what `R` means, which is `MEASUREMENT.md` §4's stratification error in
this stage's own results, found by this stage's own later criterion.

**What it does not say.** One rate ratio, `ρ = 1`, which §19.5 measured as
critical and not as optimal. Nothing here scans `ρ` against `λ` jointly, so
"more absorption is better" holds along the line `R = λ` and is not a statement
about the plane. The registered limits of §19.3 and §20.2 on the `λ` span apply
unchanged.
