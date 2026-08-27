# A5: the reachability threshold, and whether its benign side is an equilibrium

Pre-registration. **Written before any A5 code existed.** Every switch,
parameter, outcome measure and threshold below is fixed here.

Depends on stage A3's machinery and on nothing else in A3's conclusions. A5 can
run whether or not A3's criteria pass, and its result does not depend on theirs.

---

## 1. The question, and where it came from

Stage A3 treats the opening price `P_q(0)` as a nuisance parameter: the price
path has to start somewhere. It is not a nuisance. It encodes **how far out of
reach the good asset is for an ordinary agent on the first day**, and that is a
quantity with a name in the world.

Berkshire Hathaway's A share and its B share are claims on the same company with
the same underlying returns. The A share trades near seven hundred thousand
dollars and the B share near a few hundred. The B share exists *because* the A
share's price is itself a barrier. Nothing about liquidity or information
distinguishes them; what distinguishes them is whether an ordinary allocator can
hold one at all.

The source framework's author records a structurally identical finding in a
simpler setting: under moderate upstream retention the downstream layer grows
*richer* over time, which is roughly the 1945–73 pattern, and under high
retention it does not. **The simple case's conclusion does not transfer to this
model and is not claimed here.** What transfers is the shape of the finding —
that there is a **tilting point**, and that the benign side of it may be
unreachable in practice, because the upstream layer is permitted to retain as
much as it does. A5 asks whether the same shape appears in the price.

---

## 2. The measure: reachability

```
ρ_q  =  γ̃ · P_q(0) / m̃          divided by the stretch factor s
```

with `γ̃` the median terms and `m̃` the median opening claims **of the production
layer**. `ρ_q = 1` means the median production-layer agent can just afford tier
`q` on the opening day. It is a definition, not a fitted threshold.

At stage A3's registered parameters, measured over three seeds:

| | low tier | middle | high |
|---|---|---|---|
| production layer, `ρ` | `5.88` | `11.76` | `23.53` |
| effective `ρ / s` at `s = 3` | **`1.96`** | `3.92` | `7.84` |
| financial layer, low tier | **`0.25`** | | |

Two things follow immediately and both were previously read as noise.

**A3 is sitting just above the threshold.** An effective `ρ` of `1.96` at the low
tier is why one hundred and eighty production-layer nodes produced twenty-three
entrants and why the high tier saw zero resale trades in three hundred rounds.

**`s` and `P_q(0)` are one dial seen twice.** A stretch of `s` is exactly a price
divided by `s`. Stage A3's soft gate was arrived at from the gate side and landed
on `ρ_eff ≈ 2` by accident. A5 sweeps `ρ_eff` directly and treats `s` and
`P_q(0)` as two ways of setting it, which also removes a redundancy from A3's
parameter grid.

**The financial layer sits at `0.25` and the production layer at `5.88`, a factor
of `23.5`.** That ratio is the model's version of the A-share barrier.

---

## 3. Design

`ρ_eff` is swept over `{0.25, 0.5, 1.0, 2.0, 4.0, 8.0}`, set by scaling
`initial_price` to hit the target while every other stage A3 parameter stays at
its registered value. Five seeds per point, three hundred rounds, arm E, the
uncounted stretch cost.

`ρ_eff` is recomputed **every round** from the same formula on that round's
prices, terms and production-layer claims, giving a trajectory `ρ(t)` rather than
a single opening number. That trajectory is what A5-4 is about and it is the
reason this is a stage rather than a sweep appended to A3.

---

## 4. Pre-registered predictions

**A5-1 — participation falls with reachability.** The share of production-layer
nodes holding any unit at the end of the run is monotone decreasing in `ρ_eff`
across the sweep. A floor: if this fails the measure is not measuring
reachability and nothing below means anything.

**A5-2 — the threshold is where the definition says it is.** Production-layer
participation exceeds `50%` at `ρ_eff = 0.5` and falls below `5%` at
`ρ_eff = 2.0`. The point of stating it at the definitional value of one is that
`ρ = 1` was not chosen to make anything come out; it is where the median agent
can just pay.

**A5-3 — the tilting point proper: the sign flips.** Let `S(t)` be the production
layer's share of total net worth. Registered: `S` **rises** over the run at
`ρ_eff = 0.25` and **falls** at `ρ_eff = 4.0`, and the crossover lies between
`0.5` and `2.0`.

This is the transferable part of the source finding. Below the threshold the
production layer holds the appreciating asset and gains from it; above it, the
asset appreciates against them and the same mechanism runs the other way. One
mechanism, two regimes, no parameter changed except reachability.

**A5-4 — the benign side is not an equilibrium. This is the stage.** Starting at
`ρ_eff(0) = 0.5`, the trajectory `ρ(t)` crosses one and does not return.
Registered: median crossing round below `100`, and fewer than `5%` of rounds
after the crossing are spent back below one.

The reason to expect it is that the price is set by the bidder pool, and the
bidder pool is the financial layer's claims, which grow with issuance. A price
that ordinary agents can meet on day one is bid away from them by a mechanism
that no one has to choose. If A5-4 holds, then **setting the opening price low
enough for ordinary agents to buy is not a policy that can work, because the
price is endogenous** — which is a stronger and more useful statement than
locating the threshold.

**A5-5 — issuance sets the clock.** The crossing round of A5-4 falls as the
monetary authority's gain rises, swept over `{0.25, 0.5, 1.0}`. This is the
source's "the upstream layer is permitted to retain as much as it does" in the
form this model can carry: what makes the benign region evaporate is the rate at
which new claims arrive at the top.

**A5-6 — the null. Freeze the price and the drift disappears.** At `η = 0`,
`ρ(t)` has no trend: the largest absolute change from its opening value across
the run is below `1%`. Any crossing observed at `η > 0` is then the price channel
and not the wage bill, the issuance rule, or turnover moving claims around.

---

## 5. Falsification

| observation | consequence |
|---|---|
| A5-1 fails | `ρ` is not measuring reachability. The stage stops and the measure is rebuilt. |
| A5-2 fails | The threshold is not at the definitional point. Reported with the location it is actually at, and §2's claim that `ρ = 1` is not a fitted quantity is withdrawn. |
| A5-3 shows no sign flip | There is no tilting point in the price, only a monotone worsening. The analogy to the source's retention finding is withdrawn, and A5 reports a gradient rather than a regime boundary. |
| **A5-4 fails: `ρ(t)` stays below one** | **The benign region is self-sustaining, and an opening price low enough for ordinary agents is a policy that would hold. That is the opposite of what this stage expects and it is the more consequential result of the two.** |
| A5-4 holds but crossing takes longer than the run | Reported as a bound, not as a crossing time. |
| A5-5 shows no dependence on issuance | The drift is not driven by the arrival of new claims at the top, and §4's account of the mechanism is wrong even if A5-4 holds. |
| A5-6 shows drift at `η = 0` | Something other than the price is moving `ρ`, and every number in this stage is confounded until it is found. |

---

## 6. What A5 cannot establish

**It cannot say where a real economy sits.** `ρ = 23.5` between the layers is a
property of this parameterisation, not a measurement of anything. What the stage
can support is the shape: a threshold exists, and it is crossed from one side.

**It cannot price policy.** Showing that a low opening price is bid away is not
showing that no policy works. Supply, the issuance rule and the terms structure
are all untouched here, and each is a different lever. A5 rules out one lever and
says nothing about the others.

**It inherits every limit of A3.** One asset, no leverage, no collateral channel,
revaluation only.

---

## 7. Parameters

| symbol | meaning | value |
|---|---|---|
| `ρ_eff` | reachability, swept | `{0.25, 0.5, 1, 2, 4, 8}` |
| seeds | replications per point | `5` |
| rounds | run length | `300` |
| gain | issuance gain, for A5-5 | `{0.25, 0.5, 1.0}` |
| everything else | stage A3's registered values | see `a3_asset_channel.md` §8 |

`ρ_eff` is set by scaling `initial_price`; `s` is held at its A3 value so that the
sweep moves one dial and not two.

---

## 8. Changes after pre-registration

None. Entries go here with the timing of each change marked, and any change made
after a result was read flagged in bold, in the same format as
`b2_measurement.md` §10.

### 8.1 First execution: 2 of 6, and the mechanism is not the one registered

Three seeds, registered grid. Recorded before any criterion is revised.

> **This section is left unedited apart from two struck sentences, and three
> later sections bear on it.** `§8.7`: every figure below was produced in the
> economy before `rent_rate` existed, so these are the rent-free readings and
> not the registered ones. `§8.3`: every crossing round below is counted from an
> origin the criterion did not name. **`§8.9`: the live-price reading in this
> section is superseded.**

| criterion | verdict | figure |
|---|---|---|
| A5-1 participation monotone in `ρ` | fail | `22.2, 25.9, 29.3, 12.2, 1.1, 0.0` percent |
| A5-2 threshold at the definitional point | fail | `25.9%` at `ρ=0.5` against a floor of `50%` |
| A5-3 the sign flips | fail | share falls at both ends: `0.285→0.006` and `0.253→0.001` |
| A5-4 the benign side is not an equilibrium | **pass** | crossed at round 1 in 3/3, never returns |
| A5-5 issuance sets the clock | pass, vacuously | crossing is round 1 at every gain |
| A5-6 freeze the price, drift disappears | **fail** | `304%` drift with the price frozen |

**One measurement fault, fixed.** Participation was read at the end of the run.
The production layer is sold out by then at every reachability tried, so the
number is zero across the whole grid and cannot order it. Entry is what
reachability is about, so it is now read at the opening allocation and the
end-of-run figure is reported separately as survival. The table above is after
the fix.

**A5-6 did its job, and what it caught is the finding.** Reachability has a
numerator and a denominator, and the registered criterion named only the
numerator. With the price frozen exactly, `ρ` still rises by `304%`, because the
median production-layer agent's claims fall to `0.320` of their opening value
over three hundred rounds. ~~Decomposed at `ρ(0) = 0.5` with the price live: the
price moves by `×40.4`, the median buyer's claims by `×1.013`.~~
**Struck: see `§8.8` and `§8.9`.** That ratio is measured from the state after
round zero, and round zero alone takes those claims down by fifty-four to sixty
percent. Measured from the state the economy opens in, the claims side falls in
`68` of `72` cells with the price live, and its sign is not stable across seeds,
so it gets no point value at all.

**So the benign region is not an equilibrium, but not for the registered
reason.** The asset does not have to run away from ordinary agents. Ordinary
agents fall away from the asset. ~~`ρ` crosses one in the **first round** at
every reachability and every issuance gain tried~~ (**struck: see `§8.3`** for
the origin; counted from `rho_opening` the median is round two), and it crosses
with the price held still, which `§8.4` registers as A5-7 and `§8.8` records
passing in `12/12` seeds.

That is a stronger claim than the one registered and it is also a less
comfortable one, because it says the lever is not the price at all. What closes
the reachable region is the drain that stage A2 already measured as support-set
contraction, now visible as the buyer's side of a price they could once meet.
A5-5 passes vacuously for the same reason: at a crossing round of one there is
no clock for issuance to set.

**A5-1 and A5-2 fail in a way that is a result rather than a defect.** Entry
participation is not monotone: it *rises* from `22.2%` at `ρ = 0.25` to `29.3%`
at `ρ = 1.0` before collapsing. At the cheapest prices the whole stock sells at
the opening — sixty, thirty and ten units, all of it — and it sells to the
richest, because there is no cap on how much one node may hold. **Making the
asset cheaper does not put it in ordinary hands; it lets the rich buy more
units.** Ordinary participation peaks near the definitional threshold and is
crowded out on either side, by price above it and by competition below it.

`max_units` therefore interacts with `ρ` and the two cannot be swept
independently. That was not anticipated in §3 and is recorded as an open defect
in the design rather than repaired here. **The interaction is now measured**
(`§8.5`, `experiments/a5a_units_cap_probe.py`): the whole of the shape above is
the absent cap, and at a cap of one the ordering is monotone and the peak moves
to the cheapest price. The defect is measured and still not repaired, because
repairing it means choosing a cap.

**Nothing above licenses a revision of A5-3.** The production layer's share falls
at both ends of the grid, so no sign flip was found. On this evidence the
analogy to the source's retention tilting point is not supported in the price,
and §1's claim that the shape transfers is withdrawn pending the `max_units`
interaction being resolved.

### 8.2 A5-4's crossing round is measured from the wrong origin

> **Superseded in part.** The defect identified here is real and is **repaired
> in `§8.3`**. The figures are the rent-free economy's (`§8.7`), and the
> live-price reading is restated in **`§8.9`**.

The reported "median crossing round 1" is not wrong about the crossing but is
wrong about where the trajectory starts, and the difference matters for reading
it. Traced at `ρ` configured to `0.5`, three seeds:

| point | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| configured | `0.500` | `0.500` | `0.500` |
| after the opening allocation | `0.310` | `0.314` | `0.287` |
| first point of the recorded series | `0.675` | `0.669` | `0.669` |
| end of run | `34.4` | `19.1` | `34.0` |

Two things are happening and neither was named.

**The opening allocation lowers `ρ` before any round is run.** Proceeds are split
equally across all two hundred nodes, and the production layer is mostly
non-buyers, so it receives the rebate and its median claims rise. Reachability
improves to about `0.31` before the economy has done anything.

**The first recorded round more than doubles it, to `0.67`.** The configured value
is never observed, and the series' own origin is a state the criterion did not
name. `ρ` then crosses one on the next round.

So the crossing is real and fast, but "round 1" is a count from an origin two
steps removed from the parameter that was set. The fix is to record `ρ` at three
named points — configured, post-allocation, and per round — and to state the
crossing against a stated origin. ~~Not repaired here; recorded as a defect.~~
**Repaired in `§8.3`**, with the three points named and a reduction guard on the
count from the series origin.

**The substantive reading is sharper than the registered one.** A doubling of `ρ`
in a single round with the price frozen is not the asset running away. It is the
production layer's balances draining at the rate stage A4 measured directly: a
half-life of one to five rounds. The same fact has now surfaced in three places
that were designed independently —

- A4: the competing mechanisms have no stock to act on,
- A3-6: an endowment into a median node leaves `1.4%` after forty rounds,
- A5-4: reachability doubles in one round with the price held still.

Three stages, three measurement designs, one fact. **Whatever else is true, the
production layer in this model does not hold anything long enough for a price to
be the binding constraint.**

### 8.3 The origin, named at three points

`§8.2` recorded that A5-4's crossing round is counted from an origin two steps
removed from the parameter that was set, and left the repair undone. This is the
repair, registered before it is written.

**Three points, and each is a state the economy is actually in.**

| name | when it is read | what it is computed from |
|---|---|---|
| `rho_configured` | before the model exists | the target handed to `price_for`, by construction |
| `rho_opening` | on the constructed model, before any round runs | `model.terms`, `model.price`, and `model.holdings` after the opening allocation |
| `rho_series[t]` | after round `t` has settled and repriced | `price_history[t]` and `claims_history[t]` |

`price_history` and `claims_history` are both appended in `_post_round`, so
`rho_series[0]` is not an opening state and never was. That is the whole of the
defect.

**One thing checked rather than assumed.** `price_for` reads its `γ̃` off a bare
stage A2 network through `baseline`, and `rho_series` reads its `γ̃` off the
model's own `terms`. Those are two code paths and could have been two scales, in
which case the origin problem would be three steps rather than two. They are not:
`hold_mean_cost` is off by default, so `hold_mean_at` is `None` in both paths and
the matrices agree bitwise. Measured on seeds 0, 1 and 2: `1.905660377358`,
`1.893617021277`, `1.930555555556`, equal on both paths, and `rho_configured`
recomputed from `baseline`'s own pieces returns `0.5000` in all three. **The three
points are on one scale.**

**How a crossing is stated from here on.** Every crossing round is reported
against a named origin, and the default origin is `rho_opening`, because it is the
first state the economy is in. Reporting a crossing without naming its origin is
not permitted in this stage's output.

**A reduction guard, and it is the reason this is safe to write.** The crossing
counted from the series origin is the current behaviour, and the instrumented
version must reproduce the stored count for it bitwise. If it does not, the change
moved something other than the origin and the instrument is wrong rather than
sharper. **A5-4's verdict does not move under this repair and is not permitted
to**: from any of the three origins the crossing is far below the registered
`100`, so what changes is whether the number can be read, not whether the
criterion passes. A repair that flipped a verdict would be a criterion revision
wearing an instrument's clothes.

---

### 8.4 A5-7 and A5-8, registered forward

**Why they exist.** A5-6 failed, and `§8.1` recorded that what it caught is the
finding: reachability has a numerator and a denominator and the registered
criterion named only the numerator. That reading currently sits in prose and no
criterion scores it. These two do. **A5-6 stays FAIL and is not backfilled.**

**What was already visible when these were written, stated so it cannot be
mistaken for a blind bet.** A5-6's single figure: a largest relative move of
`304.64%` in `ρ` with the price frozen, five seeds, at one configured `ρ`.
(**`§8.7`, written later**: that figure is the rent-free economy's. At the
registered default the same quantity is `470.61%`. It was what was visible when
A5-7 was written, which is what this paragraph is recording, and it is not the
stage's current reading.) That
figure establishes that `ρ` moves under a frozen price. It does not establish that
`ρ` reaches one, because a largest relative move is a maximum over the run against
the series' own first point and carries no level; and it says nothing about when.
**The crossing round under a frozen price appears in no recorded number**, and
neither does the behaviour of the frozen arm anywhere on the `ρ` grid other than
at `0.5`.

**A5-7: the denominator crosses the threshold on its own.** With the price frozen
exactly (`η = 0`), starting from `rho_configured = 0.5`, `ρ(t)` reaches one and
does not return. Thresholds are **inherited from A5-4 rather than chosen**: median
crossing round below `100` counted from `rho_opening`, and fewer than `5%` of
subsequent rounds back below one.

If it holds, then the reachable region closes with the asset standing still, and
the lever is not the price. That is the claim `§8.2` already makes in words.

**A5-8: the drain is not a property of one reachability.** In the frozen-price
arm, the median production-layer agent's claims at the end of the run are below
their value at `rho_opening`, at **every** one of the six registered `ρ` points and
in **every** seed. A sign claim in every cell, no magnitude, no threshold
invented.

Reported alongside without a threshold: the same quantity in the live-price arm.
It is a diagnostic and not a criterion, for the same reason B3's emerging-market
group is reported without constituting evidence.

**Falsification.**

| observation | consequence |
|---|---|
| A5-7 fails: `ρ` stays below one with the price frozen | The denominator is a contributor and not a mechanism on its own. `§8.2`'s reading, that ordinary agents fall away from the asset rather than the asset running away from them, is withdrawn as stated, and A5-4's crossing is returned to the price channel. |
| A5-7 holds but only at some `ρ` | Reported with the set of `ρ` at which it holds, and A5-8 carries the scope. |
| A5-8 fails at any cell | The drain is not general across reachability, and A5-7's pass is a statement about `ρ = 0.5` and nothing wider. |
| The two arms disagree in sign on the denominator | Reported as measured. **Neither arm is dropped and neither is declared the real one**, because they are two registered settings of one switch and the disagreement is about what the switch does. |

**The last row is not a hedge and it is why A5-8's live-price twin is reported.**
The stage currently has one recorded decomposition, in A5-4's own detail line, and
it names a direction for the denominator. If the two arms disagree, that line is
about one arm and has to say which.

---

### 8.5 The `max_units` probe, registered as a diagnostic

`§8.1` recorded that `max_units` interacts with `ρ` and that the two cannot be
swept independently, and left it as an open defect in the design. This registers a
measurement of the interaction. **It produces no verdict and no number in it
reaches `RESULTS.md`**, on the model of `experiments/a4a_domain_probe.py`.

**It is not a proposal to change the default.** `max_units = 0` is defended in its
own docstring on structural grounds: at a cap of one, every node that can afford
anything already holds something within a few rounds, an offered unit has no
eligible buyer, three hundred rounds produce zero transactions, and A3-3, A3-4 and
A3-7 have nothing to be evaluated on. That argument is not touched here.

**Measured 2026-08-15, and the claim is narrower than it was stated.** The
zero-transaction sentence holds at `ρ_eff` of `1.0`, `2.0` and `4.0` and not at
`0.25`, `0.5` or `8.0`, where a cap of one still produces `12.6`, `4.2` and
`117.6` transactions. A3's registered parameters put its production layer at an
effective reachability of about `1.96`, **inside the band where the claim is
true**, so the argument for the default is sound at the operating point it was
written about and too strong as a statement about the mechanism. The table is in
`AssetSpec.max_units`'s own docstring, beside the original sentence, which is
left standing rather than corrected on the rule that keeps `MechanismParams`'s
falsified claim in place. **The default does not move on this account.**

**What it measures**, at each of the six registered `ρ` and at contrast caps of
`1`, `2` and `3`: units sold at the opening allocation, how those units are
distributed across the nodes that got them (largest holder's share, and the HHI of
unit ownership), and the production layer's share of both holders and units.

**The question it answers**, and it is the only one it answers: how much of A5-1's
non-monotonicity is the absence of a cap. `§8.1` reads the peak at `ρ = 1.0` as
ordinary participation being crowded out from below by the rich buying more units,
and that reading is currently an inference from the direction of the numbers
rather than a measurement of who bought what.

---

### 8.6 Seeds, five to twelve

Registered here, before the run. **Every A5 criterion is re-evaluated at twelve
seeds, including the four that fail, and no threshold moves.** The five-seed
verdicts stand recorded in `§8.1` and in the stored record so that the seed change
cannot be read as having rescued anything: if a verdict moves, it moves in view of
the number it moved from.

Reason: A5 has the cheapest run in the A track, seconds rather than the minutes A3
and A6 cost, and five seeds is thin for a criterion stated as a sign that has to
hold in every cell. A5-8 is stated on seventy-two cells for this reason.

---

### 8.7 The stored record was a reading of a different economy

**Found on 2026-08-15 by re-running the stage on unchanged code.** Not by a
guard, because there was none, and not by a number looking wrong, because none
did.

`results/a5_reachability.json`, as committed, **cannot be produced by the code
committed alongside it.**

| | A5-6 drift | price | median claims | share end, `ρ=0.25` | share end, `ρ=1.0` |
|---|---|---|---|---|---|
| the stored record | `304.64%` | `×40.7` | `×0.877` | `0.005573` | `0.011680` |
| registered defaults | `470.61%` | `×59.5` | `×1.213` | `0.000543` | `0.000984` |
| **`rent_rate = 0`** | **`304.64%`** | **`×40.7`** | **`×0.877`** | **`0.005573`** | **`0.011680`** |

**The stored record is the economy before rent existed.** The commit that
restated stage A3 introduced `rent_rate = 0.05` as a default-on mechanism, and
A5 runs entirely on A3's machinery. A5's existing record was carried into that
commit without the stage being re-run, so the record and the code that produces
it entered the repository together and disagreed from the first day. The
disagreement survived five further commits.

**Located rather than inferred.** The `asset.py` and `network.py` pair was taken
from each of the six commits touching either file since the record was written
and run against the same experiment script. All six return `470.61%`. The stored
figure is reproduced only by turning off a mechanism, and turning it off
reproduces all five quantities to every printed digit.

**Why nothing caught it, and both halves are needed.** The restatement preserved
the opening construction, so every construction-time quantity in the file still
reproduces bitwise, including the entry participation that A5-1 and A5-2 are
scored on. Only quantities that run rounds moved, and a file in which half the
numbers reproduce exactly does not look like a file that is wrong. And stage A5
is in neither `scripts/run_all.py`'s experiment list nor the continuous
integration reruns, so no comparison between record and code was ever performed.

**What it costs, stated in both directions.** It costs no verdict: two of six
live criteria pass under both settings, and the four failures fail under both.
It costs a reading. `§8.1` and `§8.2` decompose reachability into a price side
and a claims side and conclude that ordinary agents fall away from the asset
rather than the asset running away from them. In the frozen-price arm that
conclusion holds under both settings, and it is what A5-7 is registered to
score. In the **live-price** arm the claims side falls to `×0.877` without rent
and rises to `×1.213` with it. **The sign of the load-bearing term in that
decomposition depends on a mechanism that was not in the economy the reading was
taken in**, and `§8.1` and `§8.2` are therefore readings of the rent-free
economy wherever they speak about the live-price arm. Their text is left exactly
as written; this section is the scope statement that travels with it.

**Not repaired by editing anything.** The record is regenerated by running the
stage. Nothing in `§1` to `§7` moves, no threshold moves, and no verdict moves.

**The rule this produces**, and it is in `MEASUREMENT.md` as the ninth failure
mode: a stage that nothing re-runs does not have a record, it has a memory. When
a default on shared machinery moves, the stages standing on that machinery are
the ones whose stored numbers are now about a different economy, and the ones
outside the runner are exactly the ones that will not say so.

---

### 8.8 A5-7 and A5-8 executed, and what running them cost A5-4's decomposition

**Both pass at five seeds**, on the thresholds §8.4 inherited from A5-4 rather
than chose.

| criterion | verdict | figure |
|---|---|---|
| A5-7 the denominator crosses on its own | **pass** | price frozen, crossed in `5/5` seeds, median round `2` from `rho_opening` against `100` |
| A5-8 the drain is general across `ρ` | **pass** | `30/30` cells, six reachabilities by five seeds |

**The stage now reports four of eight.** No previously registered verdict moved
and no threshold moved.

**What A5-8 caught in A5-4.** A5-8 reports the median production-layer agent's
claims ending at `×0.154` of their `rho_opening` value with the price live.
A5-4's own detail line reported the same quantity as `×1.213`. Both were
correct and they measure the same runs, because the two lines started from
different origins and only one of them said so.

Traced at `ρ = 0.5`, five seeds, median production-layer claims:

| | seed 0 | seed 1 | seed 2 | seed 3 | seed 4 |
|---|---|---|---|---|---|
| post-allocation (`rho_opening`) | `0.26149` | `0.25934` | `0.28419` | `0.26110` | `0.26258` |
| after round zero (series origin) | `0.11632` | `0.11667` | `0.11493` | `0.11980` | `0.11437` |
| end of run | `0.29928` | `0.02604` | `0.30479` | `0.05159` | `0.02133` |
| end over `rho_opening` | `1.144` | `0.100` | `1.072` | `0.198` | `0.081` |
| end over series origin | `2.573` | `0.223` | `2.652` | `0.431` | `0.187` |

**Round zero alone takes the denominator down by fifty-four to sixty percent.**
That single round is the whole of the difference between the two lines, and it
is the same fact §8.2 recorded from the numerator's side when it noted that the
first recorded round more than doubles `ρ`.

**And the mean was hiding a bimodal set.** The five ratios from the series
origin are `2.573, 0.223, 2.652, 0.431, 0.187`. Three of five are below one,
two are above two and a half, and their mean is `1.213`, which reads as a rise
and is not a location of anything. A5-4 therefore now reports its claims side
through the rule A3c already registered for cross-seed instability: **a
quantity whose sign is not stable across seeds does not get a point value.** It
prints the range, the count below one, and a refusal. The price side is stable
and still prints as a multiple, and the contrast between a stable numerator and
an unreportable denominator is the substantive content of that line.

Applied to A5-8's untresholded live-price twin, the same rule replaces `×0.154`
with the range: **`28` of `30` cells fall and `2` rise, spanning `×0.000` to
`×1.144`.** The drain is close to universal with the price live as well, and
the two rising cells are two seeds at one reachability.

**Nothing here rescues anything.** A5-4 passed before this change and passes
after it, on an unchanged expression; what changed is that one of the two
numbers in its report is now refused instead of averaged. A5-6 stays failed and
is not backfilled: A5-7 is a separate line with its own registration, and the
two are reported side by side so a reader can see that the criterion which
failed and the criterion which passed are asking different questions of the
same arm.

---

### 8.9 The reading, restated at twelve seeds

**This section supersedes the live-price account in `§8.1` and `§8.2`.** Their
text stands unedited, and this is what replaces it as the reading. Three things
made the earlier one wrong and each is measured rather than argued: the figures
were taken in the rent-free economy (`§8.7`), from an origin one round late
(`§8.3`), and through a mean over a set whose sign is not stable across seeds
(`§8.8`). Twelve seeds, registered defaults, four of eight live criteria pass.

**What A5 did not establish.** There is no clean quantitative reachability
threshold. A5-1, A5-2 and A5-3 fail, three of the six original bets, and `§8.1`
records that their failures are results rather than defects. Entry participation
is not monotone in `ρ` and peaks near the definitional point, and
`experiments/a5a_units_cap_probe.py` locates the whole of that shape in the
absence of a holding cap: at a cap of one the ordering is monotone and the peak
moves to the cheapest price. The production layer's share of net worth falls at
both ends of the grid, so `§1`'s claim that the source's retention tilting point
transfers to the price is withdrawn.

**The first thing it did establish.** A price an ordinary agent can meet on the
opening day is not a self-sustaining state. Configured at `ρ = 0.5`, `ρ(t)`
reaches one in `12/12` seeds and does not return, at a median of round two
counted from `rho_opening`.

**The second, and it is the stronger one.** **The reachable region closes with
the asset standing still.** With the price frozen exactly, `ρ` crosses one in
`12/12` seeds on the same schedule (A5-7), and the median production-layer
agent's claims end below their opening value in **all seventy-two cells** of the
grid, six reachabilities by twelve seeds, at a median of `×0.045` (A5-8).

**Both sides move, and only one of them is necessary.** The price side is large
and stable: `×58.554` across seeds. The claims side with the price live is not
reportable as a point value, because its sign moves across seeds, but its
direction is nearly uniform: **`68` of `72` cells end below their opening value**
and four end above, spanning `×0.000` to `×2.496`. The asymmetry is what
decides the reading. The price channel can be removed while everything else runs,
and the region still closes. There is no corresponding experiment on the other
side: the production layer's balances cannot be held up without changing the
mechanism that drains them, so the denominator is not an arm that can be switched
off. **What is switchable turns out not to be necessary.**

**Where the earlier account went wrong, in one line.** It read
`median claims ×1.013` as ordinary agents holding their position while the asset
ran away from them. That ratio is measured from the state after round zero, and
round zero alone takes those claims down by fifty-four to sixty percent
(`§8.8`). Measured from the state the economy actually opens in, they do not
hold their position in either arm.

**The consequence for reading `ρ` at all.** Reachability is
`asset price / buyer resources` and has to be tracked as a ratio with two live
sides. Read as a price index it licenses the policy of setting the opening price
low enough, and this stage's own frozen-price arm is the counterexample to that
policy: the price was set low, then held there by force, and the region closed
anyway. A5-6's failure is what made this visible, which is what a zero
calibration is for, and A5-6 is not backfilled on that account.

**What is still not shown.** That any of this holds outside the model. `§6`
stands unchanged: `ρ = 23.5` between the layers is a property of this
parameterisation and not a measurement of anything, and A5 rules out one lever
while saying nothing about supply, the issuance rule or the terms structure.
