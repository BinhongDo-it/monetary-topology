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
revaluation only. `PROJECT_PLAN.md` §12 lists them.

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
over three hundred rounds. Decomposed at `ρ(0) = 0.5` with the price live: the
price moves by `×40.4`, the median buyer's claims by `×1.013`.

**So the benign region is not an equilibrium, but not for the registered
reason.** The asset does not have to run away from ordinary agents. Ordinary
agents fall away from the asset. `ρ` crosses one in the **first round** at every
reachability and every issuance gain tried, and it crosses with the price held
still.

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
in the design rather than repaired here.

**Nothing above licenses a revision of A5-3.** The production layer's share falls
at both ends of the grid, so no sign flip was found. On this evidence the
analogy to the source's retention tilting point is not supported in the price,
and §1's claim that the shape transfers is withdrawn pending the `max_units`
interaction being resolved.

### 8.2 A5-4's crossing round is measured from the wrong origin

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
crossing against a stated origin. Not repaired here; recorded as a defect.

**The substantive reading is sharper than the registered one.** A doubling of `ρ`
in a single round with the price frozen is not the asset running away. It is the
production layer's balances draining at the rate stage A4 measured directly: a
half-life of one to five rounds. The same fact has now surfaced in three places
that were designed independently —

- A4: the competing mechanisms have no stock to act on (`PROJECT_PLAN.md` §12.6),
- A3-6: an endowment into a median node leaves `1.4%` after forty rounds,
- A5-4: reachability doubles in one round with the price held still.

Three stages, three measurement designs, one fact. **Whatever else is true, the
production layer in this model does not hold anything long enough for a price to
be the binding constraint.**
