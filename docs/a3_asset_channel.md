# A3: the asset channel

**Rewritten 2026-08-10.** The previous document is kept
in full at `a3_asset_channel.md.expired1` — nothing is deleted — and it remains
the record of how the stage got here. This one is what the stage *is*.

Two things are deliberately absent, and their absence is the reason for the
rewrite. **Implementation failures are not reported here.** A regex that matched
a docstring, a quadratic loop, a variable deleted with its neighbour: those are
in the expired document and in the commit history, they are not findings about
anything, and carrying them in the pre-registration made the pre-registration
unreadable. **Failures about the modelled world are reported here, in full**, and
so are the measurement-validity failures, because a measure that answers a
different question than its name is a fact about the experiment and not about
the code.

Companion documents, all live:

- `a3_restated.md` — why the stage's purpose had to be restated, and the
  argument for the intervention. This document states the conclusion; that one
  states the reasoning.
- `a3b_initial_construction.md` — the opening construction as a registered axis.
- `MEASUREMENT.md` — the six failure modes and the seven-point checklist. Read
  before touching any measure here.

---

## 1. What this stage is for

The source manuscript asserts that Volume I §5's **settlement ratchet** and
Volume II §2's **non-integrability** are one object read at two time scales
(`b1_setup.md` §3). A3 exists to test that assertion, and it decomposes into
three propositions.

**P-A. The cycle is actually traversed.** A theorem says a cycle exists in the
position-agent graph. It does not say anyone walks it. Whether two agents
repeatedly enter and leave the same tier, in an economy that also has turnover,
forced sales, a moving price, a wage bill and issuance, is a contingent fact
about the dynamics. **This is the one thing a simulation can supply that a
theorem cannot.**

**P-B. The algebra survives the embedding.** The derivation in §2 assumes both
agents enter and leave the same tier on the same dates against a common sale
price. A running economy does not guarantee that: holding periods can correlate
with terms, forced sales can select on them, the price moves in between. The
question is how far the embedding perturbs a relation that is exact in
isolation.

**P-C. The holonomy is load-bearing.** Remove it, hold everything else, and the
divergence must go.

**Only P-C can fail informatively.** P-A can only fail by switching turnover
off. P-B is close to guaranteed because the relation is an identity, so the
informative quantity there is the size of the perturbation, not the fact of
agreement. P-C is the only arm whose outcome is not fixed by construction, and
the only one that can falsify the identification of the ratchet with
non-integrability.

---

## 2. The claim, and why the price cancels

Let `P_q(t)` be the reference price of tier `q`, and let agent `a` acquire on
terms `γ_{a,q} ≥ 1`, paying `γ_{a,q} · P_q(t)`. On sale every holder receives
the market price. Over a holding period `T`,

```
w_a(cash → q)  =  log( P_q(t+T) / (γ_{a,q} · P_q(t)) )
```

and the four-cycle `(a, cash) → (a, q) → (b, q) → (b, cash)` sums to

```
w_a − w_b  =  log( γ_{b,q} / γ_{a,q} )
```

**The price cancels entirely.** The holonomy is the terms differential alone and
does not depend on the price path.

This is B1's structure and it is what B2 measured on 28.1 million mortgages:
same asset, same location, same date, different terms depending on who the
borrower is.

**One traversal is not compounding.** `exp(Tδ)` with `δ = log(γ_b/γ_a)/T` is
just `γ_b/γ_a`, a fixed ratio. Compounding requires the cycle to be walked
repeatedly: `N` round trips give `(γ_b/γ_a)^N`. Turnover is therefore not a
later refinement, it is the precondition for the stage's central claim to have a
referent at all.

**The two compared groups must both hold and both trade.** A holder-versus-
non-holder gap is produced by owning, not by the terms of owning, and can be
enormous while the loop sum is zero.

### 2.1 `γ` was doing two jobs, and they are now two parameters

`γ` set both the premium paid and the admission threshold. The earlier document
presented this as a feature: one parameter carrying the framework's own
distinction between a hole and a high price.

For an intervention it is a defect, and it is why P-C could not be run for as
long as it could not. Moving the dispersion moved the loop sum **and** the gate
together — `MEASUREMENT.md` rule 4, one switch changing two things.

The split follows the topology exactly:

- **`γ_pay`** — what is paid. This is what enters the cochain, so this is what
  the holonomy is computed from. `H¹`.
- **`γ_gate`** — the admission threshold. A restriction on the domain: a hole.
  Outside the cochain by construction. `H⁰`.

`gate_spread = None` ties them and recovers the single-parameter behaviour
bitwise, the same discipline as `elasticity = 0`.

---

## 3. The mechanism

One asset in `Q` tiers, and nothing else is added.

| element | rule | source-text anchor |
|---|---|---|
| pricing | `P_q(t) = P_q(0) · (pool_q(t)/pool_q(0))^η`, the pool being the claims of those admitted at opening prices | Vol. I §10, the stretch effect |
| terms | `γ_{i,q} = γ̄_q (1 + κ (1 − c_i))`, `c` centrality. Derived from the graph, never hand-filled | Vol. I §3, scale economies of money |
| gate | `claims_i ≥ γ^gate_{i,q} · P_q(0)`, softened by `s` | Vol. I §4, the collateral ladder |
| return | revaluation, plus rent from production-layer non-holders to holders pro rata | Vol. I §10 |
| turnover | `τ` of held units return to market each round; arm F adds forced sale below `φ` | Vol. I §5 |
| opening | three registered constructions; see `a3b_initial_construction.md` | Vol. I §15 |

**The gate is an opening-allocation concept and does not reach resale.** Resale
eligibility is affordability at the paid terms, because a resale has a
counterparty who must receive the market price. This is stated because it was
discovered the hard way; see §6.3.

**Rent is the channel by which holders take from non-holders**, and it is what
reattaches compounding to access. An earlier version excluded it on grounds of
parsimony, which traded away whether there is a mechanism at all in exchange for
one fewer parameter. `rent_rate = 0` recovers the no-rent behaviour bitwise.

**No service flow beyond rent, and no imputed rent.** Living in a dwelling you
own consumes something while nobody pays anybody. Booking it requires either
creating claims from nothing, which breaks conservation, or inventing a
housing-to-claims conversion rate, which is inventing a deflator. `PROJECT_PLAN`
§11.7 rules that out. Tenancy makes the transfer real instead.

**Tier-differential appreciation is not an input and does not need to be.**
Higher tiers appreciate faster because their bidder pool is the rich, whose
claims grow fastest. Measured over three hundred rounds: `120×`, `146×`, `191×`
nominal, and `1.151`, `1.399`, `1.832` against the total claim stock — flat
after round 50, so the tier spread is a **one-off repricing and not a
per-period wedge**. Recorded in `a3b_initial_construction.md` §8.

---

## 4. Registered parameters

**This table is complete.** The previous version claimed to be and was not: it
omitted `rent_rate`, `max_units`, `arm`, `open_tiers` and the whole A3b block,
while asserting that nothing outside it was free. Any parameter not listed here
is a defect in this table, not a freedom.

| symbol | meaning | registered | swept |
|---|---|---|---|
| `Q` | tiers; `0` is the closed-channel control | `3` | no |
| `N_q` | units per tier, low to high | `(60, 30, 10)` | see `units_per_node` |
| `units_per_node` | dwellings per node; `0` uses `N_q` verbatim | `0` for A3, **`1.1`** for A3b and A3c | A3b axis |
| `P_q(0)` | opening reference price | `(0.5, 1.0, 2.0)` | with `s`, §6.5 |
| `η` | price elasticity to the bidder pool | `1.0` | `{0, 0.5, 1.0, 1.5}`; `0` freezes the path |
| `γ̄_q` | base terms by tier | `(1.00, 1.05, 1.15)` | no |
| `κ` = `terms_spread` | dispersion in what is **paid** | `1.0` | `{0, 1}` in A3c |
| `κ_gate` = `gate_spread` | dispersion in the **gate**; `None` ties it to `κ` | `None` | `{0, 1}` in A3c |
| `hold_mean_cost` | hold the mean acquisition cost while dispersion moves | `False`; **`True` whenever `κ` varies** | — |
| `mean_cost_reference` | the `κ` whose mean cost is held | `1.0` | no |
| `τ` | exogenous turnover per round | `0.04` | `{0.02, 0.04, 0.08}` |
| `φ` | forced-sale trigger, arm F | `0.10` | `{0.05, 0.10, 0.20}` |
| `arm` | `exogenous` or `forced` | `exogenous` | both |
| `rent_rate` | rent per round as a share of the low tier's price | `0.05` | `{0, 0.002, 0.005, 0.01, 0.02, 0.05}` at `η = 0` |
| `rent_base` | which set the rent bill falls on. `layer` keys the payer set on the layer index fixed at construction, which is what every stored result was produced under; `holding` keys it on the measured units, so both sides of the instrument read the same magnitude. **Added 2026-08-13**, registering the status quo rather than changing it, because `MEASUREMENT.md` §8 lists the payer side as a membership error and requires the choice be registered as a choice | `layer` | `holding` in §16.1's profile arms |
| `s` = `stretch` | how far short a node may be and still enter | `3.0` | `{1, 2, 3, 5}` |
| `stretch_cost` | `uncounted` or `counted` | `uncounted` | both |
| `max_units` | cap on units per node; `0` is no cap | `0` | `1` runs and produces zero trades |
| `open_tiers` | tiers forced open regardless of claims | `()` | A3-5 only |
| `bins` | how many bins the trader population is cut into before the outer two are compared. **Corrected, §6.5b**: registered as `4` and as feeding the product-graph `δ`, and it reached no code at all. `3` is the value at which the wired parameter reproduces every stored result bit for bit | `3` | `{2, 8}` |
| `T` | holding period in the weight; must equal `1/τ` under arm E | `25` | tied to `τ` |
| `construction` | opening allocation rule | `auction` | A3b axis |
| `ownership_rate` | share owning at `t = 0`; ignored under `auction` | `0.70` / `0.653` | A3b |
| `opening_discount` | discount in the occupancy transfer | `0.44` | A3b |
| `residual_owner` | unsold stock keeps an owner | `False` for A3, **`True`** for A3b and A3c | — |
| `proceeds` | `equal` or `seller` | `equal` for A3, **`seller`** for A3b and A3c | — |
| rounds | run length | `300` | no |
| seeds | replications | `5` | no |

`tests/test_a3_asset.py::test_defaults_match_the_pre_registration` pins these.
It previously pinned sixteen of them and silently ignored seven, which meant the
promise that no parameter is tuned to make a criterion pass was unenforced for
exactly the parameters added most recently. **Every field of `AssetSpec` must
appear in that test.**

---

## 5. Criteria and results

Five seeds, three hundred rounds. Registered thresholds in the third column.

| # | claim | threshold | result |
|---|---|---|---|
| A3-1 | the closed channel reproduces A2 **bitwise** | exactly `0` | **pass**, `0.000e+00` |
| A3-2 | *diagnostic, not a criterion* | — | ratio `9.1`; see below |
| A3-3 | *assertion, not a criterion* | — | drift `1.44e-15`; see below |
| A3-4 | the realised terms differential is the loop sum | rel. err. `< 20%` | **pass**, `3.05%` (`+0.36536` against `+0.37686`) |
| A3-5 | the gate binds at the high tier | `low > ½ · shut > high` | **void**; see §6.3 |
| A3-6 | a stock survives a generation | `≥ 50%` at 40 rounds | **fail** on the median node (`0.0%`), **pass** on the richest (`62.2%`); see §6.4 |
| A3-7 | non-overlapping windows agree in sign | all three windows | **pass**, `100/100/100` |
| **A3-8** | **the holonomy is load-bearing** | see §5.2 | **unstable**; see §5.2 |

**A3-8's word in this table was `pass` until 2026-08-13 and that was stale, not
wrong-then-right.** The harness registers three states and `pass` is the only
one that carries an answer: `void` means the harness cannot be read and
`unstable` means a channel's sign moves across seeds so no share may be quoted.
At the registered point the harness reads fine (`0.000` zero calibration,
`1.86e-16` cost drift, a full cell that moves) and the gate channel's sign
moves, so the state is `unstable`. `RESULTS.md` shows `VOID` because that
renderer takes a boolean and the two non-verdict states collapse into it, which
`a3c_load_bearing.py` says at the point of writing and prints in the detail
string. **The directional reading of §5.2 stands; the share decomposition is
what may not be quoted.** No number changed here, only the word.

### 5.1 Two former criteria demoted, and why

**A3-2 is a diagnostic.** It compares owners against non-owners, which is a gap
produced by owning rather than by the terms of owning. Its own detail string
said "a floor, not a finding". A floor is worth printing and is not a criterion.

**A3-3 is an assertion.** `adjusted return ≡ −log γ` is true by construction,
and `1.44e-15` is a machine-precision reading of it. It belongs in the test
suite. Keeping it in the results table made five passing criteria look like five
findings when two of them were one identity read twice.

**A3-4 is kept, and what it reports is changed.** The headline is not that the
two numbers agree — an identity agreeing with itself is not news. The headline
is the **3.05%**, which is how far a running economy with prices, circulation, a
wage bill, issuance, supply limits, turnover and rent perturbs a relation that
is exact on paper. The two numbers are still produced by code that shares
nothing, and `main` asserts the absence of imports in both directions.

### 5.2 A3-8, the intervention

`experiments/a3c_load_bearing.py`. `γ` split, mean acquisition cost held fixed,
each node paired against **itself** in the null cell, measured on the agents who
complete a round trip in **every** cell.

| cell | `κ_pay` | `κ_gate` | gap | across seeds |
|---|---|---|---|---|
| both | 1 | 1 | **+23.267** | same sign, `[+10.96, +38.31]` |
| loop sum alive, gate levelled | 1 | 0 | **+21.671** | same sign, `[+8.43, +27.17]` |
| gate alive, loop sum removed | 0 | 1 | **+1.409** | **sign flips**, `[−16.26, +10.62]` |
| null | 0 | 0 | **0.000** | — |

Zero calibration exactly `0.000`, from two independent executions rather than an
alias. Mean cost identical across cells to `1.86e-16`. Paired population 41.6
nodes with 11 dropped to form the intersection. No deviations. Deducting the
stretch write-off moves nothing at the third digit.

**Registered reading, first case: the divergence collapses when the loop sum is
removed.** `+23.267 → +1.409`. Removing the gate instead leaves `+21.671`, and
the paired per-seed differences between those two cells flip sign twice, so
removing the gate does nothing five seeds can see.

**The holonomy is load-bearing on this carrier. The ratchet and the obstruction
are the same object.** That identification was previously asserted and is now
tested.

**Refused: any share for the gate channel.** Its five seeds are `4.02, 1.53,
10.62, 7.13, −16.26`. A mean of `+1.409` on a range that crosses zero is not a
small positive contribution, it is **not distinguishable from zero**, and the
harness now declines to decompose when a cell's sign is unstable across seeds.
An earlier pass quoted "93.9% / 6.9%"; that is withdrawn.

**Not a gain for the central group.** In the gate-alive cell both group means
are negative, `−1.274` and `−2.683`. Relative to the null, a differential gate
with uniform payment leaves the traded population worse off, the peripheral
third more so. The small positive gap is a difference of two negatives.

**The magnitude does not transfer.** `κ_pay = 1` and `κ_gate = 1` are the same
number and not the same strength of treatment: the payment premium is a
per-round-trip multiplier compounding over some twenty traversals, the gate acts
once. A compounding channel beating a one-off filter over three hundred rounds
is partly arithmetic. **Direction transfers, ratio does not.**

### 5.3 A3-8's population, and a criterion registered forward rather than back

**Added 2026-08-13, after a diagnostic that §5.2 had not been given.**
`experiments/a3d_gate_margin.py`. It reports and scores nothing; it re-reads the
same cells on three population rules and prints who is in them. Its five-seed
run reproduces §5.2's numbers exactly, `+23.2667 / +21.6714 / +1.4091` with the
gate range `[−16.2566, +10.6212]`, so what follows is a second reading of one
pipeline rather than a second implementation.

**The question it was built for has a negative answer, and that is worth
recording first.** The population is the intersection of agents completing a
round trip in every cell, and the obvious worry is that this drops exactly the
agents the gate excludes, so the gate arm would be blind by construction. It is
not. Participation is `24.6` nodes with the gate on and `21.9` with it off, over
twenty seeds; the gate **admits** two or three more rather than excluding any,
and `shared` at `41.6` against `any_cell` at `44.4` gives the same qualitative
picture on both rules. The population rule is not what is holding the gate arm
down.

**What the diagnostic found instead is a scope fact about the whole stage.**

| twenty seeds | production layer participating | peripheral tercile | share | centrality percentile of participants |
|---|---|---|---|---|
| gate on (`both`, `H0_only`) | 24.6 | **0.0** | 13.7% | `[86.8, 93.4, 100.0]` |
| gate off (`H1_only`, `null`) | 21.9 | **0.0** | 12.2% | `[88.3, 94.2, 100.0]` |

**A3-8 is measured on the top eighth of the production layer by centrality.**
The peripheral tercile walks the cycle zero times, in every cell, at every seed,
including the null, so the gate is not what removed it. The criterion's own
"peripheral" group therefore sits near the 87th percentile, and `κ_gate`, which
disperses admission along centrality, has almost no variation left to act on
inside a band that runs from 87 to 100. That is a statement about
the estimand's reach and it holds whatever the gap comes out to.

**One inference drawn from that row in 2026-08-13 was that the gate reads as
nothing because its treatment barely varies over the set it is read on. It was
measured on 2026-08-27 and it is false.** Taking the two cells that differ only
in the gate and the two that differ only in the terms, the gate moves `19.4`
nodes' cycle counts against the other channel's `16.8`, and `74.0` of total
absolute cycle change against `85.6`, **eighty-six per cent of it**
(`experiments/a3h_gate_acts.py`). It also moves `2.2` nodes into the trading set
and none out, so it acts on the intensive margin rather than the extensive one
this section assigned it to. **The scope fact above stands and the inertness
read off it does not**, and the general form is in `docs/MEASUREMENT.md` failure
mode 78: to decide whether a treatment is inert on a population, measure what it
does to the mechanism rather than where the population sits. **Swept along the
knob that widens the population, the ratio runs 0.748 at 18.4 nodes down to
exactly 0.000 at 178.4 and at 200 of 200, so the inertness is at the wide end**:
an admission rule that disperses entry has nothing left to ration once nearly
everyone is already inside.

**Any quotation of A3-8 must carry that population with it.** This is the same
disease §6.4 records for A3-6, whose holding population is 15.8 nodes of 200
with none downstairs, arriving through a different criterion.

**On the full production layer every treated cell is noise**: `+0.1064`,
`+0.7811`, `+0.9400`, all three sign-unstable. So the divergence lives inside
the participating band and vanishes when averaged over the layer. Not an
inversion, a range.

**Twenty seeds strengthen the positive content and refute one of §6.5b's
attributions.**

| population `shared`, 20 seeds | mean | range | sign |
|---|---|---|---|
| `both` | +18.9854 | `[+0.6042, +38.3108]` | stable, and the low end is now `+0.60` |
| **`H1_only`** | **+22.2119** | **`[+7.1073, +37.4222]`** | **stable, 20 of 20** |
| `H0_only` | −0.2997 | `[−16.2566, +21.6474]` | moves |

The loop-sum-only cell is the only channel that stays same-sign over twenty
seeds, and it is **steadier than the full treatment**: `both` drops to a low end
of `+0.60`, and on `any_cell` it goes negative at one seed and becomes
unquotable. Mechanically that follows from the row above, since the gate moves
two or three nodes in and out of the measured set without contributing a
direction, so switching it off removes composition noise and no signal.

**§6.5b reads the gate arm's instability as a sample-size effect. For that arm
it is not.** Going from five seeds to twenty widens the range, `[−16.26,
+10.62]` to `[−16.26, +21.65]`, rather than narrowing it. A quantity that
disperses further as the sample grows has no location parameter to find. §6.5b's
sample-size reading was about the loop-sum arm at high bin counts and remains
untouched there; it does not extend to the gate.

**A criterion, registered forward.**

`tier_positions` is a star, so `b₁(G) = 0`, so `Γ` carries no slice cycles and by
`b1_theorem.md` §5 the entire obstruction is squares. `terms_spread` is the only
thing that sets a square sum; `gate_spread` contributes no holonomy at all. That
licenses an **ordering** and not a level, and the distinction matters: Theorem 2
says the gate produces no holonomy, it does **not** say the gate produces no
divergence, and A3-2 already exhibits an ownership gap orders of magnitude wide
with a loop sum of exactly zero. So the registrable statement is:

> **A3-8′.** The loop-sum-only cell is same-sign across all seeds, **and** its
> gap exceeds the gate-only cell's. Shares continue to be reported and not
> gated.

Neither clause contains a number this repository invented, which is what §5.1's
demotions and the registered-provenance rule exist to enforce.

**It is registered forward and is not applied to A3-8.** It was written after
seeing that the ordering holds, so using it to convert A3-8's `void` into a pass
would be manufacturing the result it was chosen to fit. **A3-8's state stays
`void`, for the reason already on record: no threshold was registered for its
two shares before it ran.** A3-8′ governs the next stage that runs this design.

**Amended 2026-08-27.** The clause that once followed here, that such a stage
first needs a carrier whose measured population is not one eighth of one layer,
was built on the inertness inference this section now retires, and widening the
population was measured to remove the effect along with it. What the next stage
needs is that the treatment have a measurable effect on the mechanism, which
this carrier already has. **A3-8′ has since been scored three times**: by A7 as
`A7-A-4`, where the conjunction fails and the clause that fails it is sign
stability; on fresh seeds by A3h; and pooled across every point on record by
A3i, which counts the ordering clause holding at 54 of 57 points and the
gate-only cell sign-stable at none of them.

---

## 6. Failures and limits about the modelled world

Implementation failures are in the expired document. These are not.

### 6.1 Eleven measurement-validity failures, and the file that exists because of them

None was a fact about the world; every one was a measure whose name and content
disagreed. They are catalogued as six failure modes with a seven-point checklist
in `MEASUREMENT.md`. **That file is the long tail that does not survive
compression into a hand-off note, and it is why the same error kept recurring
under different names.**

Four more are added here, all on the P-C measure, and they are worth
naming because they were found in sequence on the same quantity:

1. A ratio of percentiles returned infinity, because the production layer's
   tenth percentile is zero — the layer is stripped.
2. The same measure put the **null cell above a treated cell**, which a floor
   cannot do. It was measuring ownership dispersion, not terms dispersion.
3. Normalising each node by its own opening claims and then comparing *groups*
   inverted the ranking, because central nodes hold larger opening claims and a
   small denominator produces a large multiple. Rule 2: the two sides of a
   comparison must share a denominator.
4. Measuring the production layer at round 300 reads the aftermath. A3b
   established the layer holds nothing by round 200 under every construction, so
   all four cells sat between `0.000` and `0.143`. Rule 1: the window must
   contain the thing the claim quantifies over.

The fifth version — pair each node against itself, population fixed to the
agents who traverse the cycle in every cell — is the one in §5.2.

### 6.2 The production layer is emptied, one way, under every construction

`a3b_initial_construction.md` §9.2. Opening ownership of 21.3% and of 72.0% both
end at about 8.6%, and the production layer reaches **zero** holders in every
arm. The opening distribution sets how long the drain takes and not where it
ends. Starting broad buys time and nothing else.

This is the stage's clearest statement about the modelled world, and it is the
one the source manuscript actually claims: not that ordinary people can never
get in, but that **they got in and it was taken back**.

### 6.2b The entry debt outlives the asset it was taken on to buy

Found by a test that started failing and was **not** repaired by loosening its
threshold.

Under the counted stretch variant, a node short of the acquisition cost enters
by taking on `stretch_debt`, amortised over `holding_period` rounds through its
own adjacency row. At `rent_rate = 0` the schedule retires the debt: `17.993`
down to zero over three hundred rounds. **At the registered `rent_rate = 0.05`,
`16.7%` of it is still outstanding**, and the composition is unambiguous:

- 22 nodes, **all** in the production layer;
- **none** still holding a unit;
- claims **exactly zero**;
- every one cash-constrained against its own instalment.

They stretched to get in, the unit was taken back by the one-way exit of §6.2,
and rent stripped what remained. **The debt taken on to enter outlives the asset
it bought.** Nothing in the code says a stretcher must end insolvent; this is
the interaction of three mechanisms that were each registered separately.

It is the source manuscript's Volume I §18 default waterfall in miniature, and
it arrives without being written in. Recorded as
`test_rent_outlives_the_asset_the_debt_was_taken_on_to_buy`, asserted as a range
rather than a point so that it pins the phenomenon and not a number.

**The test that broke is kept, pinned at `rent_rate = 0`.** It asserts that the
instalment schedule works, which is a claim about the schedule; at the
registered rent it was carrying two claims at once and reporting the interesting
one as a broken test.

### 6.3 A3-5 cannot be evaluated as registered, and the reason is a finding

The high-tier arm is a **bitwise no-op**. Three reasons, the first sufficient:
`open_tiers` is consulted only at the opening allocation and never in resale;
the high tier allocates fully at the opening in both arms, so forcing its gate
open admits newcomers to the back of a queue that ends before them; and
downstairs, of 180 production-layer nodes, the number that can reach the high
tier is **zero even at the soft gate**, against a production-layer claims median
of `0.162` and a high-tier price of `2.0`.

**So at the high tier the exclusion is a price wall, not a hole.** §2 registered
`γ` as carrying the hole-versus-high-price distinction in one parameter; this run
separates them and locates each. The hole is at the **low-tier margin**, where 23
nodes sit between the hard and the soft gate. The high tier is a wall, and the
framework's own A5 material says it should be.

Reducing `units` does not repair this. The criterion is now subsumed by the
`κ_gate` axis and should be rewritten there.

### 6.4 A3-6's domain was wrong; corrected, it still fails, and harder

**As first registered** the criterion shocked the **median node** and required
half the transfer to survive 40 rounds. The framework's own claim is that the
median node cannot hold a stock, so the criterion demanded the model contradict
its thesis before A4 could start. Measured `0.0%`.

**The obvious repair is to shock the richest node instead**, which measures
`62.2%` and passes. It was proposed by an external review and is **refused**,
for two reasons and then a third that the refusal turned up.

*It is picking the arm that passes after seeing that it passes.* The earlier
version of this criterion's own docstring named that as the move this repository
exists to avoid.

*A single richest node is not "the population that holds a stock".* Swapping one
single-node measurement for another and calling it a population is §11.10's
error — a quantile on a handful of units — relocated.

*And the `62.2%` is one seed.* Per seed the richest node retains
`36.5%, 24.5%, 39.8%, **177.2%**, 33.1%`. Four of five sit between 24% and 40%;
the mean clears the threshold **only because of the outlier**. This is the same
defect as the withdrawn `93.9% / 6.9%` attribution in §5.2: a mean quoted with
no dispersion beside it, hiding the one observation that produced it.

**Corrected domain.** The population is now the set that actually holds a unit
when the transfer arrives, read at the shock round, and the statistic is the
median over that set — legitimate on fifteen to eighteen nodes in a way a decile
on ten never was.

| quantity | value |
|---|---|
| median holder's retention after 40 rounds | **13.8%** |
| holders clearing the 50% threshold | **3% of 79** |
| a non-holder's retention | **0.1%** |
| holding population | **15.8 of 200 nodes** |
| of which in the production layer | **0.0** |

**A3-6 fails on the corrected domain, and the correction made it fail harder.**
The threshold is carried over from the median-node version and that is
disclosed rather than hidden: it is being applied to a new domain by an author
who had already seen the richest node's number, and it is kept because
lowering it would be worse than carrying it.

**Three consequences, and the third is the one that matters for A4.**

*The contrast is the finding, not the verdict.* A one-off transfer to a node
with no asset is recaptured within a generation — `0.1%` — while the same
transfer to a holder is not. Retention rises steeply with position and does so
non-monotonically in claims. **That is the redistribution-futility result, and
it is what A6 goes on to price.**

*The stock A3 was built to supply is thin.* A0 and A2 had no stock and A4
therefore could not run, and A3 exists partly
to supply one. It supplies a stock for **16 of 200 nodes, all upstairs**, whose
median holder retains **14%** over forty rounds.

*So A4 remains blocked, and for a better-stated reason than before.* Its four
competitors act on wealth. Measured where the wealth is, they describe
stratification **within** those sixteen upstairs nodes, not the economy's — and
inheritance in particular, which is a generation-scale channel, has a
forty-round median retention of 14% to transmit. **A4 must not be run as
designed until this is resolved**, and switching its domain silently to the
holders would reproduce exactly the error refused above.

### 6.4b The step in retention is a step in layer, and the asset's own step is a transient

§6.4 leaves A3-6 with two numbers, a holder statistic and a non-holder
statistic, and `PROJECT_PLAN` §16.1 proposed taking the *shape* between them to
external data as a distinguishing prediction: that a one-off transfer is
retained in a **step** on whether the recipient owns an asset, rather than along
a gradient in wealth. §16.1's own first instruction was that two points cannot
tell those apart and the profile had to be run internally first. It has been.
`experiments/a3_asset_channel.py --retention-profile`, every node shocked
separately, one full model run each, five seeds, a thousand runs. It is a
**diagnostic**: it registers nothing, feeds no criterion, and A3-6's seven
criteria are character-identical with it in the file.

**The two-point picture is real and it is enormous.** Holders retain a median
`14.25%` of the transfer over forty rounds; non-holders retain `0.00%`. Only
`0.8%` of non-holders beat the median holder and no holder falls below the
median non-holder.

**It cannot be attributed to the asset, because at the registered shock round
every holder is a financial-layer node.** Seventy-nine holders, all upstairs;
nine hundred production-layer node-seeds, not one of them holding. Holders
occupy wealth ranks `182` to `200` of `200` in every seed. So "holder against
non-holder" is also "layer 1 against layer 2", and the layer carries two things
of its own that have nothing to do with owning:

* `_collect_rent` bills `(held <= 0) & _is_production`. A financial-layer node
  holding nothing pays no rent; a production-layer node holding nothing pays,
  every round, at `rent_rate = 0.05` of the low tier's price. **Liability is
  keyed on the construction-time layer index while receipts are keyed on
  holding**, and that asymmetry is live in the registered run.
* `_prior_owner_weights` routes the opening proceeds and the unsold residual to
  `~_is_production`, weighted by opening claims. Defended in its docstring and
  the same shape all the same: a fixed index set receives.

`_is_production` is assigned once, by index, at `layer1_size`, and is never
updated. This is the same defect A6 had in its levy base, in a different place.

**The trade asymmetry is by design and is worth stating with it.** A buyer pays
`γ_{i,q} · P` and `γ` rises as centrality falls; a seller in `_settle` receives
the market price, and the seller's own `γ` never enters what it receives.
Reaching up costs, selling down is free, and a peripheral round trip is a net
loss of `(γ − 1) · P`, which is the holonomy. The premium is split equally
across all nodes rather than routed upstairs, deliberately, so that A3-4 can
tell the terms differential apart from the premium's destination.

**The denominator is already layer-determined.** The transfer is the same
absolute amount for every recipient, but the deviation it has produced by the
end of the round it lands in is a median of `36` upstairs and `3.8` downstairs.
Nine tenths of a transfer to the production layer is gone inside the landing
round. So A3-6's ratio **understates** the gap: at forty rounds the absolute
retained amounts are `9.83` and `0.017`, a factor of about `560`, where the
ratio shows a factor of `66`.

**`open_tiers` does not break the identification, and that was tested rather
than assumed.** It is the only switch in the model that admits regardless of
claims, which is what §16.1's problem needs. Opening the low tier admits **one**
production-layer node across three seeds. Allocated units rise from `61` to `89`
of a supply of `100` and the extra units go upstairs: the opening caps each node
at one unit, and the resale market then has no cap at all, so twenty financial
nodes absorb the stock over a hundred and fifty rounds. Opening the high tier is
a bitwise no-op, per §6.3.

**What does break it is the shock round.** Production-layer nodes holding a unit,
by round, over three seeds:

| round | 1 | 5 | 10 | 20 | 40 | 80 | 150 | 299 |
|---|---|---|---|---|---|---|---|---|
| holders downstairs | 21, 27, 19 | 21, 24, 17 | 20, 23, 15 | 13, 16, 8 | 6, 11, 4 | 1, 2, 1 | 0, 0, 0 | 0, 0, 0 |

A3-6's registered shock round is `150`. **The cell that answers §16.1 is empty
there**, and it is populated early. Profiled at round 20, with the horizon read
at five points off the same runs:

| group | n | median at 40 | h=10 | h=20 | h=40 | h=80 | h=149 |
|---|---|---|---|---|---|---|---|
| financial layer, holds | 88 | **24.33%** | 22.35% | 23.43% | 24.33% | 22.31% | 22.53% |
| financial layer, no asset | 12 | 1.39% | 1.68% | 1.57% | 1.39% | 2.00% | 0.89% |
| production layer, holds | 62 | **0.59%** | 6.17% | 10.95% | 0.59% | 0.28% | 0.01% |
| production layer, no asset | 838 | 0.37% | 0.01% | 0.23% | 0.37% | 0.16% | 0.00% |

The last two rows are the comparison §16.1 wanted: same layer, same rent
liability, same construction-time assignment, and the asset is the only thing
that differs.

**Read as three findings.**

*Between layers the step is permanent.* The upstairs rows are flat in the
horizon, `22%` at ten rounds and `22%` at a hundred and forty-nine.

*Within the production layer the asset's step is a transient.* `6.17%` against
`0.01%` at ten rounds, `10.95%` against `0.23%` at twenty, and by forty rounds
`0.59%` against `0.37%`, which in absolute terms is `0.0245` against `0.0174`, a
factor of `1.4`. By a hundred and forty-nine rounds it is gone. The asset is
sold or stripped and the advantage goes with it.

*Wealth is still doing work inside the groups.* Spearman of retention against
wealth, with holding held constant, is `+0.776` among holders at the registered
shock round and `+0.860` against net worth; at round 20 it is `+0.496`. A pure
step predicts these near zero. The boundary pair, the poorest holder against the
richest non-holder, splits two to two across seeds at round 150 and three to two
at round 20, and under a net-worth ordering it reads as a step in none of the
two seeds that can discriminate at all. The largest adjacent jump in the
rank-ordered curve sits at the holding boundary in **no** seed at either shock
round.

**So §16.1's shape is not established, and the reason is sharper than "not yet
measured".** There is a very large step and it is a step in **position**. The
asset contributes a step of its own that is real at a ten to twenty round scale
and has decayed to a factor of `1.4` by the forty rounds A3-6 measures at.
Taking "the model predicts retention jumps on asset ownership" to the child tax
credit or the SCE panel would be taking a shape the model did not produce.
**§16.1's steps two and three, pinning the round-to-time window and the priors
on the mapping, are idle until this is resolved**: they exist to carry the step
outward, and what would travel is the layer.

Nothing here changes A3-6. Its threshold, domain, verdict and detail string are
untouched, and the profile writes to its own file so that a diagnostic cannot
reach a criterion.

### 6.4c §6.4b's reading is a reading at one parameter, and the parameter is the rent

**Added 2026-08-13, after §6.4b. Diagnostic.** It registers nothing, feeds no
criterion and moves no threshold. `A3_6_SHOCK_ROUND` is untouched and A3-6's
seven criteria are unchanged word for word. Four profile runs, each written to
its own file: `--profile-arm rent-by-holding`, `--profile-arm rent-off`, and
both of those questions again at `--profile-shock-round 20` against the
registered control at the same round.

#### The membership error is real and it carries nothing

`MEASUREMENT.md` §8 lists this stage's rent liability as a membership error: the
payer set is `(held <= 0) & _is_production`, fixed at construction, while the
receipt set is `held > 0`, recomputed every round. The two sides of one
instrument are keyed on different kinds of thing. That is now registered as a
choice rather than left on the page as a fact: `AssetSpec.rent_base`, default
`layer`, §4's table, and `tests/test_a3_rent_base.py` asserts the default
reproduces the previous behaviour bitwise and that the other arm is not inert.

Keying the payer set on the measured magnitude instead moves almost nothing.

| shock round 150, median retention at 40 rounds | registered | `rent_base = "holding"` |
|---|---|---|
| financial layer, holds | **14.25%** | **14.56%** |
| financial layer, no asset | 0.31% | 0.19% |
| production layer, no asset | 0.00% | 0.00% |
| Spearman(retention, wealth) within holders | +0.776 | +0.771 |
| median wealth, financial layer non-holders | 13.492 | **9.337** |

The only column that moves is the last, and it moves for the right reason:
twenty-one financial-layer nodes that hold nothing now pay rent like any other
non-holder, and they get poorer by a third. They were already at 0.31%
retention, so nothing downstream notices.

**So the defect is where the census said it was and it is not load-bearing
here.** `PROJECT_PLAN` §16.4 judged that hard-coded layer membership mattered
for A6's levy and little for A3. Its conclusion survives this check. Its stated
reason does not: §16.4 argued that A3 already had the mechanism through the
`γ·P` gate, and §16.1's own run shows that gate admits production-layer nodes at
the opening and none of them still hold at round 150. And the 2026-08-13 census
puts three of the five instrument instances in A3, not in A6. **The defect lives
here; it just does not carry anything here.**

#### What carries it is the rent channel, and at round 150 it hides the question

| shock round 150, median retention at 40 rounds | registered | `rent_rate = 0` |
|---|---|---|
| financial layer, holds | 14.25% | **30.70%** |
| financial layer, no asset | 0.31% | 1.86% |
| **production layer, holds** | **EMPTY** | **EMPTY** |
| production layer, no asset | **0.00%** | **0.22%** |
| nodes whose shock left no measurable trace | 11 | **0** |

Two things follow and the second is the one that matters.

Rent is what drives the production layer's retention to **exactly zero**. With
it off the non-holder deciles come out as a clean monotone gradient
(`0.11, 0.11, 0.11, 0.11, 0.16, 0.22, 0.31, 0.47, 0.65, 3.11`); with it on that
curve is flattened onto the floor. An exact zero in a denominator is also why
§16.1's two summaries of the same gap disagree, one reporting 560-fold in
absolute retention and the other 66-fold as a ratio.

**And `production_layer_with_asset` is empty in every arm at round 150,
including with rent fully off.** So rent is not what strips the production layer
of holders before the registered shock lands. Whatever does that is elsewhere,
and this diagnostic does not identify it.

#### At round 20 the two-by-two completes, and the ordering reverses

The registered control at round 20 reproduces §6.4b exactly
(`6.17 / 10.95 / 0.59 / 0.28 / 0.01` against
`0.01 / 0.23 / 0.37 / 0.16 / 0.00`).

Production layer only, holders against non-holders, median retention:

| horizon | 10 | 20 | **40** | 80 | 149 |
|---|---|---|---|---|---|
| registered | 6.17% / 0.01% | 10.95% / 0.23% | **0.59% / 0.37%** | 0.28% / 0.16% | 0.01% / 0.00% |
| ratio | 617× | 47.6× | **1.59×** | 1.75× | both dead |
| `rent_rate = 0` | 2.76% / 0.23% | 8.88% / 0.44% | **4.89% / 0.86%** | 1.70% / 0.83% | 2.54% / 1.11% |
| ratio | 12.0× | 20.2× | **5.69×** | 2.05× | **2.29×** |

And the two steps against each other at horizon 40:

| | layer step, holders across layers | asset step, within the production layer | ratio |
|---|---|---|---|
| registered | 24.33 / 0.59 = **41.2×** | **1.59×** | **26 : 1** |
| `rent_rate = 0` | 33.82 / 4.89 = **6.92×** | **5.69×** | **1.2 : 1** |

**§6.4b's closing sentence, that the step which travels is the layer's and not
the asset's, is a reading at `rent_rate = 0.05`.** At zero the two are the same
order of magnitude at horizon 40.

**The `2.29×` at horizon 149 in that table does not survive the decomposition
below and is retracted as an asset effect.** It is a ratio of group medians, so
it carries whatever wealth difference the two groups have. Once the pairs are
matched on wealth the advantage at 149 is gone in both arms. The retraction is
left here rather than the table edited, because the table is what a reader
would otherwise reproduce and then wonder about.

**The mechanism is a floor, not an economic finding.** Under the registered rent
both production-layer groups sit at the bottom of the range by horizon 40, with
median wealth `0.319` and `0.032`, and a ratio between two numbers at the floor
has no resolution. The registered configuration does not have the dynamic range
downstairs to answer the question §16.1 asks. That is a statement about the
instrument.

#### Three limits, and none of them is optional when quoting the above

*`rent_rate = 0` is a bracket and not a world.* `AssetSpec.rent_rate`'s own note
records that at zero, production-layer nodes that never held anything end **253%
richer in claims** than in a run with no asset market at all, because they
collect the opening rebate and the transaction premium and the price never
reaches them. So the figures above measure how much the registered rent
compresses, not what the economy would be.

*Controlling for wealth by decile does not give a consistent answer.* At round
20 the tenth decile reads 15.9× registered (`26.00%` against `1.64%`, nine
non-holders) and 11.1× with rent off, while the **ninth** decile reads 1.8× and
1.29× with populations of fifty-eight against forty-two. A contrast that is
fourteen-fold in one decile, one-and-a-third in the next and eleven-fold in the
one after is not a step read through a bin.

*It is a step plus a gradient in both arms.* Spearman(retention, wealth) within
the holder group is `+0.496` registered and `+0.386` with rent off, `+0.510` and
`+0.431` against net worth. §16.1's own reading is that a pure step predicts
these near zero.

#### What this licenses and what it does not

It does **not** reinstate §16.1's prediction. It removes one of the two reasons
that prediction was withdrawn, and the other reason, that the shape is mixed,
is untouched and is now the open item.

It does **not** touch A3-6, which measures at round 150 under the registered
rent and fails there for the reasons §6.4 records.

It does **not** make `rent_rate = 0` quotable. Nothing above may be reported
without the 253% note beside it.

#### The decomposition, and it closes the question by dissolving it

`experiments/a3e_step_or_gradient.py`, a reading of the profile files already on
disk and not another set of runs. Each holder is matched to the nearest
non-holder by wealth at the shock round, inside the interval where both groups
exist; the same matcher is then run non-holder against non-holder to supply the
noise floor, which is checklist item 7's zero arm. Both quantities are
pre-treatment, so item 5 holds by construction.

    python experiments/a3e_step_or_gradient.py
    python experiments/a3e_step_or_gradient.py --horizon 149

| production layer, horizon 40 | registered | `rent_rate = 0` |
|---|---|---|
| seeds with any wealth overlap | **4 of 5** | 5 of 5 |
| holders matched | 42 of 62 | **59 of 60** |
| match balance, median \|Δwealth\| | 0.0364 | **0.0029** |
| paired median difference | +0.0012 | +0.0203 |
| paired upper quartile | +1.8639 | **+1.5413** |
| **holder wins the pair** | **57.1%** | **71.2%** |
| noise floor's share | **60.0%** | **50.0%** |
| spread of the share | 7.6% | 5.9% |
| noise floor's interquartile width | 0.0163 | 0.0328 |
| Spearman(retention, wealth), non-holders **on the support** | −0.377 (n=20) | **+0.071** (n=218) |
| the same over the **full** range, from §6.4b's reading | +0.068 | +0.293 |

Three readings and none of them is the shape §16.1 wanted.

***Under the registered rent the question cannot be asked downstairs.*** One
seed of five has **no wealth overlap at all**: its twelve production-layer
holders are each richer than every production-layer non-holder, which is
§16.1's collinearity arriving as an empty interval rather than as a weak
contrast. A third of the holders are dropped for want of a control. Among the
forty-two that match, the holder wins `57.1%` of pairs against a floor of
`60.0%`, which is **below** the floor. **The decile ratios in §6.4c above were
reading collinearity.**

***With the rent floor lifted the support becomes usable and something
survives, but it is not a step and not a gradient.*** Fifty-nine of sixty
holders match, all five seeds have overlap, and the match is an order of
magnitude tighter in wealth. The holder then wins `71.2%` of pairs against a
floor of `50.0%`, three and a half spreads away, **while the paired median
stays inside the floor's interquartile width**. The step's upper quartile is
`+1.5413` against the floor's `+0.0167`.

**Holding shifts the sign of the paired difference without shifting its middle.
What it buys is a skewed upper tail.** With wealth held fixed the typical holder
keeps about what a matched non-holder keeps, and a minority keep enormously
more. The profile's own amplification counter says the same thing from the other
side: `44` of a thousand nodes end with a larger deviation than they started
with under rent-off at round 20, against `5` to `7` at round 150.

***And the wealth gradient is a range effect.*** On the common support the
non-holder Spearman is `+0.071` with rent off, against `+0.293` over the full
range. The gradient lives **between** the support and the rest of the
distribution, not within it, so it is not a within-group slope in the sense
§16.1's external comparison would need.

**What this does to §16.1's remaining steps.** They stay stalled, and for a
third reason which replaces both earlier ones. Not because the step belongs to
the layer, and not because the asset's step is a transient. Because the shape is
a **tail**, and the external measurements it was to be taken to are central: the
CTC monthly-payment work and the SCE panel's marginal propensity to repay debt
report means and medians by income band. A quantity whose median is inside its
own noise floor and whose signal is in the upper quartile cannot be confirmed or
refuted by a median. **Taking it out as designed would compare a tail against a
centre**, and this repository has a name for that.

The sign statistic was promoted to the headline **after** the first run, because
the first version read the median alone and that rule discards a distribution
whose mass has moved into one tail. Both statistics are printed, neither is
scored, and the sequence is recorded in the module docstring rather than left in
the history.

#### The tail, measured on one fixed pair set at five horizons

`--tail`. Matching is on wealth at the shock round and does not depend on the
horizon, so the pair set is identical at all five and the series is within-pair.
Three questions: does the sign asymmetry hold at every horizon, is the advantage
a level or a lottery, and is it the same pairs winning each time.

Production layer, holder-wins share against the noise floor's share:

| horizon | 10 | 20 | **40** | 80 | 149 |
|---|---|---|---|---|---|
| registered, step | 85.7% | 85.7% | **57.1%** | 50.0% | 31.0% |
| registered, floor | 20.0% | 55.0% | 60.0% | 40.0% | 20.0% |
| `rent_rate = 0`, step | 66.1% | 64.4% | **71.2%** | **50.8%** | 44.1% |
| `rent_rate = 0`, floor | 49.5% | 49.5% | 50.0% | 47.7% | 49.1% |

**The advantage is a transient in both arms, and rent moves when it dies rather
than whether.** Registered, it is gone by horizon 40. With rent off it survives
to 40 and is gone by 80. The registered arm's floor is on twenty pairs and moves
between 20% and 60%, so its own readings are weak; the rent-off floor sits at
49.5% to 50.0% on two hundred and eighteen pairs, which is what a floor should
look like and is the reason the rent-off column is the one worth reading.

**So §6.4b's word for the asset's step, transient, was right.** What was wrong
was the reason. §6.4b had it dying because the asset does not survive
downstairs; it dies with the asset still held, and lifting the rent extends the
window by roughly one horizon step without removing the decay.

*Is it a level or a lottery.* The top tenth of pairs carries `75.0%` of the
positive total at horizon 40 with rent off. **But the floor carries `99.7%`,**
and between `96.9%` and `99.7%` at every horizon. **Concentration therefore
separates nothing here**, and that is the finding rather than a defect: the
retention distribution is itself heavy-tailed, so any difference of two
retentions is concentrated whether or not holding had anything to do with it.
The zero arm earned its place by taking a statistic away rather than by
confirming one.

*Does the winner rotate.* Against horizon 40, the share of that horizon's top
tenth still in the top tenth elsewhere is `16.7%`, `16.7%`, `33.3%`, `33.3%`,
with rank correlations of `+0.375`, `+0.588`, `+0.451`, `+0.330`. **The tail
rotates.** It is not a set of holders who are durably ahead; it is a different
few at each reading. This project's conclusion 34 is the same shape found in a
different place, and it was found there only because someone asked the floating
against fixed question rather than reporting the top share alone.

**The characterisation that survives all of this is weak, and it is the one to
carry forward.** With wealth held fixed, holding buys a **temporary and rotating
sign advantage**, present at ten to forty rounds, gone by eighty, whose
magnitude no tail statistic tried here can separate from the noise floor. It is
neither a step nor a gradient, and it is also not the durable lottery the
previous subsection's quartiles suggested before the floor was measured at every
horizon.

### 6.4d What empties the production layer, answered: the gate shuts in three rounds

**Added 2026-08-13. Diagnostic**, `experiments/a3f_who_empties_downstairs.py`.
It reads series from unmodified runs, changes no mechanism and scores nothing.
§6.4c left one open item, that `production_layer_with_asset` is empty at round
150 in every arm including rent-off and that whatever empties it was not
identified. This identifies it.

#### Two candidates with different fingerprints

Turnover is exogenous at `τ = 0.04`, so about four percent of held units return
to the market each round whoever holds them and a holder that never wins one
back decays with a half-life near seventeen rounds. **The units leave by
construction. The question is why none come back**, and there are two answers.

*The wall.* The price rises, the gate is `claims ≥ γ·P`, and production-layer
claims stop clearing it. Then the count that **could** buy at the current price
reaches zero before the unit count does, and the auction is thereafter
irrelevant.

*The auction.* They still clear the gate and lose every time, because the bidder
pool is claims-weighted. Then the clearing count stays positive while the units
go.

#### It is the wall, and it closes almost immediately

Registered parameters, five seeds, means:

| round | prod units | fin units | prod holders | can buy | can stretch | low price |
|---|---|---|---|---|---|---|
| 1 | 23.20 | 37.40 | 22.20 | **5.80** | **39.60** | 0.447 |
| 10 | 19.00 | 41.60 | 18.20 | **0.20** | **1.00** | 1.801 |
| 20 | 12.80 | 47.80 | 12.20 | 0.00 | 0.60 | 3.416 |
| 40 | 5.80 | 54.80 | 5.80 | 0.00 | 0.00 | 6.728 |
| 80 | 0.80 | 59.80 | 0.80 | 0.00 | 0.00 | 13.299 |
| 150 | **0.00** | 60.60 | **0.00** | 0.00 | 0.00 | 25.628 |
| 299 | 0.00 | 60.60 | 0.00 | 0.00 | 0.00 | 49.916 |

Per seed, the round each gate first shuts against the round the layer's units
run out for good:

| seed | units empty | hard gate shuts | soft gate shuts |
|---|---|---|---|
| 0 | 110 | **3** | 6 |
| 1 | 104 | **3** | 8 |
| 2 | 99 | **2** | 6 |
| 3 | 72 | **4** | 9 |
| 4 | 55 | **2** | 15 |

**The hard gate shuts in two to four rounds and the soft gate in six to fifteen,
in five seeds of five. The median distance from the soft gate shutting to the
units running out is ninety-three rounds.** So the production layer is locked
out of the market in the first ten rounds of a three-hundred-round run, and what
follows is exogenous turnover grinding away the units it already held, at four
percent a round, for the next hundred.

**Rent is not what builds the wall.** With `rent_rate = 0` the hard gate still
shuts at rounds `2, 2, 3, 3, 5` and the soft gate at `6, 7, 8, 9, 13`. Rent
steepens the price path a little, low-tier price `49.9` against `36.7` at round
299, and shortens the grind, units empty at `55` to `110` against `63` to `132`.
It changes the speed of the aftermath and not the event.

**What builds it is the price rule itself.** `P_q(t) = P_q(0)·(B_q(t)/B_q(0))^η`
at `η = 1`, with `B` the claims-weighted bidder pool. The low tier goes from
`0.447` to `1.801` in ten rounds, a fourfold rise, and the gate is
`claims ≥ γ·P`. Anyone whose claims do not also quadruple is out. That is the
stage's registered mechanism working exactly as written, not a defect.

#### This reframes §6.3, and the two readings converge

§6.3 concluded that at the high tier the exclusion is a price wall and not a
hole, and located the hole **at the low-tier margin, where twenty-three nodes
sit between the hard and the soft gate**. That is a reading at the opening.
**The low-tier hole shuts by round six to fifteen.** So `γ`, which §2 registers
as carrying the hole-against-high-price distinction in one parameter, carries a
hole for the first ten rounds and a wall for the remaining two hundred and
ninety, and nothing in the registered reporting says when it flips.

**And §5.3 is the same fact seen from the other end.** That section finds A3-8
measured on the top eighth of the production layer by centrality, with the
peripheral tercile trading zero times in every cell including the null. A layer
walled out of the market by round ten is exactly a layer that never appears in a
population defined by having traded. Two diagnostics built for different
questions land on one structural fact.

#### What it changes and what it does not

It changes **no verdict**. A3-6 still fails, A3-5 is still void, and the numbers
in every table above are untouched. What it supplies is the reason A3-6's shock
round finds nobody downstairs holding: **not that the layer was stripped over
time, but that it was locked out on round three and the stripping is the
aftermath.**

It closes §6.4c's open item, so **A3's registered re-check has an answer** and
the conclusions there stand rather than waiting on it.

It adds one thing a later stage must carry: **any A3 measurement taken after
round fifteen is taken on an economy in which the production layer cannot enter
the asset market at any price.** That is true of A3-4's three windows, of A3-7,
and of A3-8, and it is not a defect in any of them. It is the scope of the
carrier.

*One statistic was corrected after the first run and the reason is in the module
docstring.* The soft gate's *stays shut* round is one past the units' round in
every seed of both arms, which is mechanical: a node selling its last unit holds
the proceeds for a round and clears `γ·P / s` on that round alone. The round
each gate **first** shuts is the quantity the two candidates disagree about and
is what the table reports; the *stays shut* column is printed beside it so the
artifact is visible rather than removed.

### 6.5 The registered §7 grid has not been run

`{η, κ, τ, φ, s}` and the centrality binning have not been swept, and "no
conclusion may live at one value of any of them" is a registered promise. **This
is a breach of a registered commitment, not a todo.** The exception is `η`,
swept between `0` and `1` in the rent arm and in A3-5, and `κ`, swept in A3c.

### 6.5b The grid has now been run, and the first thing it found was a knob wired to nothing

§6.5 above is left as written. This section records what closing it produced.

Fourteen cells, one parameter at a time off the registered point, at the
registered five seeds and three hundred rounds, run twice: once against
`a3_asset_channel.py`'s six live criteria and once against A3-8 in
`a3c_load_bearing.py`. A3-1 is excluded from the first by construction, since
the closed channel is built from the module-level `CLOSED` spec that no asset
parameter reaches. `κ` is excluded from the second by construction, since A3-8's
four cells **are** the `κ` factorial and putting it on a robustness axis would
be sweeping the treatment.

**`centrality_bins` was declared, validated, documented, and read by nothing.**
It had a field in `AssetSpec`, a `< 1` validation, and a docstring saying it fed
the loop sum on the product graph. No line in the repository ever looked at it.
Two models differing only in it came out bit-identical in `terms`, `units`,
`cycles`, `centrality`, `uncounted_cost` and `net_worth`. The first run of this
grid duly swept it across `2` and `8`, reported "no state change" both times,
and **those two clean rows were worth nothing**: an axis that reaches no code
cannot move a verdict, and a grid that counts it as robustness is claiming
coverage it does not have. §6.5's promise names the centrality binning
explicitly, so the axis it names was the one axis the grid could not have been
testing.

**It is now wired at two sites, and the default moved from `4` to `3`.** Both
sites cut the population into thirds with a hardcoded `// 3`:
`terms_pair` in `a3_asset_channel.py`, ranking by `γ`, and `terciles` in
`a3c_load_bearing.py`, ranking on `centrality` directly. Sorting by `γ` is
sorting by centrality, since `γ = γ̄(1 + κ(1 − c))` is strictly monotone
decreasing in `c`, so the field's name describes both cuts accurately. The
parameter now sets how many equal bins of width `floor(n / bins)` the population
is cut into, with the outermost two compared; larger values mean narrower, more
extreme groups.

`3` is not a preference. It is the value at which the wired parameter reproduces
every stored A3 number **bit for bit**, and that was verified rather than
assumed: `criteria`, `market`, `rent_sweep` and `deviations` in
`a3_asset_channel.json`, and `cells` and `mean_cost_relative_drift` in
`a3c_load_bearing.json`, all compare identical against the pre-wiring files.
**The declared `4` was never the behaviour of anything**, and leaving it in
place would have changed every number in the stage the moment the wire was
connected, with nothing in the run looking wrong. This is the same reduction
guard A6-7 applies to the ratchet, for the same reason.

**Both sweeps now detect this class of defect rather than reasoning about it in
advance.** A cell whose criterion details, or whose four gaps, come out
identical to the registered point is flagged `inert` and named in the result
file. It is reported and not gated: inertness is a statement about coverage, not
a failure of the run. After the wiring, `a3_asset_channel` has twelve live cells
of fourteen and `a3c_load_bearing` has thirteen, the remainder being
`forced_sale_floor` at `0.05` and, for the first stage only, at `0.10`, which is
the registered default and therefore differs from the registered point by the
arm switch alone.

**A3-4 holds at every one of the fourteen points.** Relative error between the
realised terms differential and the product-graph holonomy ranges from `0.00%`
to `7.77%` against a registered tolerance of `20%`, with the holonomy itself
moving over `+0.282` to `+0.499`. The criterion that carries the stage does not
live at one value of any swept parameter.

**A3-7 fails at four of the fourteen, and is not repaired.** It asks that the
better-termed group beat the worse-termed group in all three non-overlapping
hundred-round windows, so that the result is not a single repricing. Registered
point: `100% / 100% / 100%` of seeds. The four failures:

| cell | `[0,100)` | `[100,200)` | `[200,300)` |
|---|---|---|---|
| `η = 1.5` | 80% | 0% | 0% |
| `τ = 0.02`, `T = 50` | 80% | 100% | 80% |
| `s = 1.0` | 20% | 0% | 0% |
| `s = 5.0` | 60% | 80% | 80% |

**So A3-7's conclusion lives at one value and A3-4's does not**, and that is the
grid's finding rather than a defect to be tuned away. A3-2, A3-3, A3-5 and A3-6
hold their states at all fourteen cells, which for the last two means the void
and the failure are as robust as the passes.

**A3-8's verdict held at every cell, and its reason did not.** The state is
`unstable` at all fourteen: the gate channel's per-seed sign moves everywhere on
the grid, so **no share may be quoted for the gate at any parameter value
tested**, which makes §5.2's refusal robust rather than local. But the loop-sum
channel also becomes sign-unstable at four cells, `η = 0.5`, `s = 1.0`,
`s = 2.0` and `centrality_bins = 8`. The verdict word is the same at those cells
for a different reason, so the sweep compares the **set** of channels
indistinguishable from zero and not merely the word. A3-8's negative content is
robust; its positive content is not everywhere.

**The binning axis, mapped.** Diagnostic, outside the registered grid, reported
because the single `bins = 8` cell above is not readable without it:

| bins | nodes per group | both | loop sum only | gate only | indistinguishable from zero |
|---|---|---|---|---|---|
| 2 | 21 | +13.421 | +14.569 | −0.443 | gate |
| **3** | **14** | **+23.267** | **+21.671** | **+1.409** | **gate** |
| 4 | 10 | +25.947 | +26.976 | +3.438 | gate |
| 5 | 8 | +32.151 | +28.524 | +1.780 | gate, loop sum |
| 6 | 7 | +26.418 | +28.375 | +3.099 | gate, loop sum |
| 8 | 5 | +20.123 | +23.010 | +2.587 | gate, loop sum |

The gap **levels** stay between `+13` and `+32` throughout; what breaks from
five bins on is the cross-seed sign consistency of a group mean taken over eight
nodes or fewer. That reads as a sample-size effect rather than the channel
disappearing, and it is written here as a reading and not as a repair: the
criterion reports what it reports. The never-real default of `4` falls on the
stable side.

**A design tie was violated in the first version of this grid, by this
repository.** Two cells swept `turnover` without moving `holding_period`, which
§4 registers as tied to `1/τ` under arm E, and `asset.py` said so on stderr
while the digest printed a clean row. The values are now tied through the
guard's own `round(1/turnover)`, and more to the point **both sweeps record
`model.deviations` per cell and refuse to call a cell clean if it has any**, so
a violated tie can no longer be visible only in stderr. The corrected re-run
still shows `τ = 0.02` failing A3-7, so the error had not manufactured the
finding.

**Three section references in `a3_asset_channel.py`'s docstring were stale** and
are corrected in the script rather than in this document: the grid is §4 and not
§7, this breach is §6.5 and not §9.10, and the rent arm is §6.2b and not §9.11.
The heading of §6.5 above still says §7 and is left alone.

**What this still does not cover.** The grid is one parameter at a time, so it
sees no interactions, and a pair of parameters that only moves a verdict jointly
would pass every cell. No threshold is registered for A3-8's two shares, so
their spread across the grid is reported and not judged. `forced_sale_floor` at
`0.05` reaches nothing either stage can see, which is a fact about that axis's
low end and not a second dead knob, since `0.2` moves both stages.

### 6.5c The grid re-run, and what its population column says

**Added 2026-08-13.** The grid was re-run after a fix to A3-6's non-holder arm,
and the re-run is reported here because a fix whose effect is not shown is an
assertion.

#### The fix, and that it moved no verdict

`a3_6` passed `**asset_kw` to `_shock_survival` in the holder loop and not in
the non-holder line three below it. `_shock_trace` builds its shocked model from
`AssetSpec(**asset_kw)` and differences it against the `base` it is handed, so
without the kwargs the non-holder arm differenced a **registered-parameter**
shocked run against a **swept-parameter** base, and the deviation carried the
parameter change rather than the transfer. At the registered point `asset_kw` is
empty and the two paths are the same object, so the only path that was ever
wrong is the one `--sweep` takes.

**A3-6's verdict never depended on it.** The verdict reads the holder median,
which always received the kwargs. What was wrong is the non-holder figure inside
the detail string, at thirteen of fourteen cells.

Checked rather than argued, five seeds, before against after: at the registered
point the detail string is **identical character for character**; at
`elasticity = 0.5` the non-holder figure moves from `0.2%` to `0.4%` and
**every other field in the string is unchanged**. The re-run then reproduces the
grid verdict for verdict: A3-7 fails at the same four cells (`η = 1.5`,
`τ = 0.02`, `s = 1.0`, `s = 5.0`), A3-8's zero-channel set moves at the same
four (`η = 0.5`, `s = 1.0`, `s = 2.0`, `bins = 8`), and both inert counts are
unchanged at twelve of fourteen live in the first stage and thirteen of fourteen
in the second, with `forced_sale_floor` at `0.05` and `0.10` the dead cells.

**This is `MEASUREMENT.md` §8's closing rule in a third place**, after the A6
rebate and this stage's rent liability: one call site corrected and its twin
left alone. It is added to that section's instance table.

#### The population column explains three of A3-8's four moved cells

`a3c_load_bearing.py --sweep` prints the paired population per cell and the
number had not been read against which cells move. With `bins` setting how many
equal buckets the population is cut into before the outer two are compared, the
size of each compared group is `pop / bins`:

| cell | pop | group | loop-sum channel quotable |
|---|---|---|---|
| registered and nine others | 41.6 | 13.9 | yes |
| **`s = 1.0`** | **18.4** | **6.1** | **no** |
| **`s = 2.0`** | **24.2** | **8.1** | **no** |
| **`bins = 8`** | 41.6 | **5.2** | **no** |
| `bins = 2` | 41.6 | 20.8 | yes |
| `s = 5.0` | **98.8** | 32.9 | yes |
| **`η = 0.5`** | 41.6 | 13.9 | **no** |

**Every cell whose compared groups fall below about eight nodes loses the
loop-sum channel, and every cell above about fourteen keeps it, with `η = 0.5`
the single exception.** So three of the four cells where §6.5b records that "the
set of channels indistinguishable from zero moved" are a statement about how
many nodes were left to compare, not about the mechanism. §6.5b's own reading of
the binning axis said as much for `bins = 8`; the `stretch` axis was not read
that way and should have been.

**And `stretch` is a lever on §5.3's problem.** §5.3 records that A3-8 is
measured on the top eighth of the production layer and that the next carrier
needs a larger measured population. The grid shows that parameter already
exists: `s = 5.0` carries `98.8` nodes against the registered `41.6`, and it
keeps both channels quotable. §13.3 of `PROJECT_PLAN` notes independently that
`s = 5` admits eighty-eight production-layer nodes to the lowest tier against
twenty-three at the registered `s = 3`.

**That is an observation and not a proposal to move the registered value.**
Choosing `s` after seeing which value makes a channel quotable is exactly the
move §5.1's demotions exist to prevent. It is recorded so that a stage designed
after this one starts from a population that can carry a reading, and so that
`s = 1.0` and `s = 2.0` are never quoted as evidence that the loop sum is weak
there.

`η = 0.5` remains unexplained. Its population and its groups are the registered
ones, so whatever moves it is not size.

### 6.6 What A3 cannot say, however it comes out

With P-A, P-B and P-C all established the stage supports exactly this:

> In a running stratified economy, agents repeatedly traverse the position-agent
> cycle; the holonomy of that cycle accumulates; and removing the holonomy while
> holding everything else removes the divergence.

It does **not** support "the real economy's holonomy causes the real economy's
distributional divergence". That needs the real-data counterpart of
`do(κ_pay = 0)` — setting mortgage terms uniform and re-running history — which
does not exist. The limit is structural and is not a defect of this experiment.

**And matching B2's magnitude is prohibited, not pending.** See
`a3_restated.md` §3: the only way to hit 78–85% is to tune `κ`, and `κ` is the
quantity being claimed. Calibrate on what you are not claiming, never on what
you are.

---

## 7. What A3 hands to A4

A4 asks whether connectivity `C` is one regressor among the four competitors or
the space they act in. Its registered discriminant is an amplification ratio on
the Gini, and that discriminant has three known problems: the Gini is bounded
and the control cell already sits at `0.935`, the ratio has no sampling
distribution behind it, and `uniform_access` also flattens the opening holdings.

**A3-8 supplies a sharper one, and it is a topological quantity rather than a
distributional summary.**

Measured fact, not assumption: under `uniform_access` the centrality spread is
**exactly zero**, therefore the terms spread is **exactly zero**, therefore

> **`C = 0` ⇒ `H¹ ≡ 0`.**

Combined with A3-8, which shows `H¹` carries the divergence and the gate does
not, the upstream hypothesis acquires a form that says where the competitors
must act:

> If `C` is upstream, each competitor's contribution to divergence is **routed
> through `H¹`** when `C` is on, and with `C` off there is **no `H¹` for it to
> route through**, so it must fall back on its own direct channel and does less.
> If `C` is parallel, the competitors' effects are indifferent to `do(κ_pay=0)`
> and roughly equal with `C` on and off.

**This must be stated as a decomposition and not as a ratio.** The amplification
ratio `A(X)` measured on accumulated holonomy has a **structurally zero
denominator** under `C = 0`, and that is not a numerical inconvenience — it is
the hypothesis. The measurable is instead, within each `C` arm and for each
competitor `X`, the share of `X`'s effect that vanishes under `do(κ_pay = 0)`.

Three properties this discriminant has and the Gini ratio does not: it is
unbounded, so §12.7's ceiling problem does not arise; it is measured on the
object the framework says is doing the work rather than on a summary of the
outcome; and it inherits A3c's guards — the mean-cost hold, the paired
population, the zero calibration, and the refusal to decompose when a cell's
sign is unstable across seeds.

`a4_causal_primitive.md` has not yet been updated to this and should be, before
A4 is run.

---

## 8. Falsification

| observation | consequence |
|---|---|
| A3-1 non-zero | the generalisation does not recover its special case; not a generalisation |
| A3-4 outside `20%` | the loop sum does not survive the embedding; P-B fails and the ratchet identification loses its arithmetic |
| A3-8's null cell non-zero | the harness is broken; nothing in the table may be read |
| A3-8's mean cost drifts | the cells differ in level as well as dispersion; the 2 × 2 is void, not favourable |
| A3-8's divergence unchanged with `κ_pay = 0` | **the loop sum is not load-bearing; `b1_setup.md` §3's identification is withdrawn for this carrier and A3-4's agreement is decorative.** Registered as an ordinary possible result |
| both single-channel cells collapse while the full cell does not | the channels interact; report the interaction, attribute to neither |
| A3-8 replicated with a cell's sign unstable across seeds | no share may be quoted for that cell, whatever its mean |

---

## 9. A registered distinguishing prediction: transfer persistence is a step in asset ownership, not a gradient in income

**Registered 2026-08-10. Untested, and no data in this repository can test it.**
Written down so that it is a prediction rather than a story told after the fact.

### 9.1 The three readings it rests on

All three are model output and **none of them is calibrated**. Survival of a
one-off transfer of 10% of the claim stock, measured against the same node's own
unshocked path:

| carrier | recipient | retained |
|---|---|---|
| A2, no asset channel | any | **0.00%** |
| A3 | holds nothing when the transfer arrives | **0.1%** |
| A3 | holds a unit, median over the holding set | **14%** |

And the shape, which matters more than the level. Median retention across
holders by horizon: `22.1%` at 5 rounds, `17.8%` at 10, `15.2%` at 25, `14.4%`
at 40, `14.6%` at 80, **`14.3%` at 149**. Two components, one fast and one
permanent: about four fifths of the transfer is gone inside five rounds, and
what is left **never decays again**.

The mechanism is legible and was not designed in. The fast part is the claim
flowing away through ordinary circulation, whose half-life A0 and A2 already
measured at two to five rounds. **The permanent part is exactly the portion
converted into the asset**, and converting requires already being able to hold.
A transfer to someone who cannot convert is not a small effect. It is no effect.

### 9.2 The prediction

> **Transfer persistence is a step function in asset ownership, not a gradient
> in income.** Two households at the same income, one holding an asset and one
> not, should retain a one-off transfer at rates differing by an order of
> magnitude, and the retained portion should show **no further decay** after the
> first few periods.

**The competing account predicts something else, and that is what makes it a
test.** A marginal-propensity story — high-MPC households spend transfers faster
— predicts a **smooth gradient in income or in MPC**, with no discontinuity at
asset ownership, and predicts **continuing decay** rather than a permanent
residual.

### 9.3 Why this is prediction rather than explanation

Nothing in this repository measures transfer persistence. B2 measures dispersion
in mortgage terms. `DFA_NET_WORTH_SHARES` is a wealth **stock** share and it is
an **input** to `calibration.py`, so any agreement between the model's
concentration and the DFA figures is a calibration echo and must never be quoted
as confirmation. The default-waterfall figures in the source manuscript — credit
card, auto, rent, evictions — are cited from the New York Fed, Fitch and
Eviction Lab; **they are not this project's measurements**, and stage A1, which
would make them mine, has not started.

So the resonance between this result and ordinary observation is the third
correspondence standard, 解释力 (*explanatory power*), which is the weakest of the
ones that touch the world: the phenomenon was there first. **Persistence is the
fourth standard, 预测力 (*predictive power*), because no data used in building
this model contains it.**

### 9.4 What would falsify it

| observation | consequence |
|---|---|
| retention rises smoothly with income and shows no discontinuity at asset ownership | the mechanism is MPC, not conversion, and this prediction is dead |
| the retained portion keeps decaying rather than levelling | there is no permanent component, and §9.1's flat tail is an artefact of the model's closed accounts |
| non-holders retain a substantial share | conversion is not the channel; the model has the mechanism wrong |
| holders and non-holders differ but the gap tracks a third variable — credit access, employment stability — that also predicts ownership | the step is real and the attribution to ownership is not. **This is the most likely way to be wrong** and it needs the third variable measured, not controlled away |

### 9.5 Where it could be tested, and by whom

Panel data on a one-off transfer, split by **whether the recipient held an
asset** rather than by income decile. The 2020–21 United States payments and the
expanded child tax credit are panels of the right shape; so are one-off
disbursements elsewhere. The split that matters is ownership, and the quantity
is retention at twelve and at thirty-six months, looking for a **level** rather
than a slope.

This is outside the scope of this project and is recorded as a hook, not a plan.

---

## 10. Stage closed: what each verdict says about an economy

**Added 2026-08-13 as the closing read.** Nothing below is a new measurement.
It says what the seven verdicts and the diagnostics mean if the model is taken
as a description of a stratified economy, and it says what §9's registered
prediction is now worth.

### 10.1 The verdicts, in economic terms

**A3-1, pass.** Not a finding. Switching the asset market off returns the
economy of stage A2 bit for bit, so everything A3 reports is attributable to
the asset channel rather than to the model having been rebuilt around it.

**A3-2, demoted.** Owning against not owning opens a ninefold net-worth gap
between nodes that started level. That is real and large, and it is **not** the
claim this stage exists to test. It is a gap produced by owning, and the claim
is about the terms on which one obtains. The two are independent: this gap can
be orders of magnitude wide while the loop sum is exactly zero.

**A3-3, demoted.** No economic content. An identity read at machine precision.

**A3-4, pass at 3.05%.** The load-bearing one. The framework says the gap
between two agents facing different terms on the same transition **is** the
holonomy of a four-cycle in the position-agent graph. On paper that is an
identity. What the run adds is that after embedding it in an economy with
moving prices, circulation, a wage bill, issuance, supply limits, turnover and
rent, the identity is perturbed by three percent. **The topological object
survives contact with a working economy.** It is not a validation of the theory
and §3.2's sixth reading applies: the relation was always going to agree with
itself, and the informative quantity is the perturbation.

**A3-5, void, and the void is the finding.** The framework compresses "a hole"
and "a price that is too high" into one parameter. This run separates them and
locates each. At the **top** of the asset ladder the exclusion is a price wall:
no production-layer node reaches the high tier even at the soft gate, against a
claims median of `0.162` and a price of `2.0`. A price wall is expressible
inside the price system, so it is not the framework's object. **The hole is at
the low-tier margin**, the twenty-three nodes between the hard and the soft
gate. §6.4d then adds the time quantifier the criterion never had: that hole
shuts between rounds six and fifteen. **The hole is a property of the opening.**

**A3-6, fail, and the failure is the economic result.** Two readings and the
second matters more. First, redistribution futility: a one-off transfer to a
node with no asset is recaptured within a generation, `0.1%` surviving forty
rounds, while the same transfer to a holder leaves `13.8%`. **Money handed to a
node with no in-edges to retain it does not stay.** That is §8's reachability
criterion at the scale of one agent, and it is what A6 goes on to price in tax
points. Second, the criterion asked whether a stock survives a generation and
the model says it does not, which is the model agreeing with the manuscript's
own path-dependence claim rather than contradicting it. And §6.4d supplies the
mechanism: the production layer holds nothing at the shock round because it was
**locked out on round three**, not because it was drained slowly.

**A3-7, pass, and it is the weaker of the two passes.** Better terms beat worse
terms in all three non-overlapping hundred-round windows in every seed, so the
advantage is a structural wedge and not one lucky repricing. But four of
fourteen grid cells fail it and are not repaired. **A3-7's conclusion lives at
the registered parameter values and A3-4's does not.**

**A3-8, unstable.** Removing the loop sum collapses the divergence from
`+23.27` to `+1.41`; removing the gate leaves `+21.67`. **Among agents already
in the market, what drives them apart is the terms and not the admission
threshold.** No share may be quoted for the gate because its sign moves across
seeds. §5.3 supplies the scope and it is what makes the reading honest: the
measurement lives on the top eighth of the production layer by centrality, and
the gate disperses **along** centrality, so it is read where it barely varies.
The two halves fit together rather than competing. **The gate decides who is in
the market; the terms decide how those inside come apart; and A3-8 can only see
the second, because its sample is the people already inside.**

### 10.2 What §9's registered prediction is now worth

§9 registers a prediction for external data: that retention of a one-off
transfer is a **step** on whether the recipient owns an asset rather than a
gradient in wealth. §6.4b through §6.4d took it apart in three moves and the
prediction is **suspended**, not falsified.

The step is not the asset's; at the registered shock round every holder is a
financial-layer node. Lifting the rent floor makes the asset's own step visible
and comparable to the layer's, so the earlier attribution was a reading at one
parameter. And once wealth is held fixed by matching, what remains is a
**temporary and rotating sign advantage**, present at ten to forty rounds, gone
by eighty, whose magnitude no tail statistic tried here separates from the noise
floor.

**So the shape is a tail, and the panels §9.5 names report centres.** The
child-tax-credit work and the SCE panel's marginal propensity to repay debt
report means and medians by income band. Comparing a quantity whose median is
inside its own noise floor against a median is comparing a tail to a centre.
**§9 is suspended until a carrier is found that reports the upper tail of a
distribution and does so at short horizons.** That is a fresh availability
check, not a step in §9's own plan.

### 10.3 What the stage is evidence for

**A3 is a mechanism demonstration on a constructed economy, not a measurement
of the world.** §6.6 states the boundary and it stands: the stage supports the
claim that in a running stratified economy the holonomy of the position-agent
cycle accumulates and that removing it while holding everything else removes
the divergence. It does not support the claim that the real economy's holonomy
causes the real economy's distributional divergence. That half is B2 on
mortgage terms and B3 on covered parity.

Six limits travel with every number above.

Five seeds throughout. The grid moves one parameter at a time and cannot see
interactions. A3-7 fails four of fourteen cells, unrepaired. A3-6's threshold
is carried from a different domain and disclosed. One grid cell, `η = 0.5`,
moves A3-8's zero-channel set for a reason that is not population size and is
not identified. And, from §6.4d, **every A3 measurement taken after round
fifteen is taken on an economy in which the production layer cannot enter the
asset market at any price**, which is the scope of the carrier rather than a
defect in any criterion.

### 10.4 Closed

There is no open registered re-check and no ruling waiting on this stage. The
one re-check §6.4c left open, what empties the production layer, is answered in
§6.4d. The ruling §16.1 was waiting on is dissolved: both of its options were
removed by data rather than chosen between.

What A3 hands forward is in §7, with one addition from §5.3 and §6.5c: **the
next stage built on this carrier needs a measured population larger than one
eighth of one layer, and `stretch` is an existing lever on it.** Recorded as an
observation. Choosing that parameter after seeing which value makes a channel
quotable is the move §5.1's demotions exist to prevent.


---

## 11. The zero domain, and A3 had already measured it

**Written 2026-08-28. Nothing was run for it beyond a re-read**, in
`experiments/a3k_zero_domain.py`, of records that were already on disk.

Objection O11 ruled the coverage test invalid as self-validation: it lists what
the framework explains and never what it forbids. The repair adopted was a
**zero domain** — the framework must name where its own quantity has to vanish,
and then measure it there. `b9_zero_holonomy.md` §56 records that repair
discharged on the B track, by B6's derived channel columns. **The A track had no
such reading on file. A3 has had one since 2026-08-13 and it had never been read
as one.**

### 11.1 The theorem names the zero, and names it exactly

`tier_positions` is a star. A star has `b₁(G) = 0`, so by Theorem 2 the cycle
space of the enlarged graph holds no slice cycles and **every obstruction on
this carrier is a square**. §2.1 above already classifies the two parameters
that came out of the old `γ`: `γ_pay` is what is paid and enters the cochain,
`H¹`; **`γ_gate` is an admission threshold, a restriction on the domain, outside
the cochain by construction, `H⁰`.**

> **So the gate channel's holonomy share is predicted to be zero. Not small and
> not bounded: zero, as a point prediction, from the theorem, with no constant
> chosen by anyone.**

There is nothing in the prediction to calibrate, which is what `D5` asks for and
rarely gets.

### 11.2 The reading, both channels, one machine

57 points pooled from 6 records, every one of them written before this section
existed. `results/a3k_zero_domain.json`.

| | exact `0` | median `|·|` | p90 `|·|` | max `|·|` | sign-stable |
|---|---|---|---|---|---|
| **gate channel, `H⁰`** | **5** | `0.1130` | `1.2264` | `2.9375` | **`0 / 57`** |
| **terms channel, `H¹`** | 1 | `0.3810` | `18.3683` | `24.8347` | `9 / 57` |

`|gate| < |terms|` at **48 of 57** points. Amplitude ratio `0.2967` at the
medians and `0.1183` at the maxima.

**The five points where the gate cell reads exactly zero carry nothing, and
`A3k-7` prints the reason beside each.** `A3j` measures the gate's mechanical
ratio as `0.000` at `stretch 20` and `40`, so a zero there is inertness and not
the prediction. The other four sit within five per cent of the complete graph,
whose endpoint §4.1 of `docs/a7_continuous_c.md` had already excluded as an
attractor with an over-determined zero. **They are listed in the record for
completeness and they are not evidence.**

**The amplitude is not the reading either.** A median `|gate|` of `0.1130` is
not a measurement of something non-zero: it is the size of a mean that never
survives its own seed dispersion. §5.2 established that directly at the
registered point, where a mean of `+1.409` sits on the seed range
`[−16.26, +10.62]` and the harness declined to decompose. **The sign-stability
count is the machine-readable form of the same fact, taken over every point on
file**, and `0 / 57` is the strongest single number here.

### 11.3 The load-bearing reading: the eight points where the gate is measurably active

**Restricting to where the treatment does something is the whole test**, and the
restriction is read off `A3j`'s own mechanical ratio rather than chosen. The
eight grid values at which that ratio is non-zero:

| point | `A3j` ratio | gate cell `H⁰` | terms cell `H¹` |
|---|---|---|---|
| `stretch=1.0` | `0.748` | `−0.5546` | `+2.8090` |
| `stretch=2.0` | `1.069` | `−2.4759` | `+19.7276` |
| `stretch=3.0` | `0.864` | `+1.4091` | `+21.6714` |
| `stretch=4.0` | `0.926` | `+1.3004` | `+11.5026` |
| `stretch=5.0` | `0.943` | `+1.4748` | `+4.4283` |
| `stretch=6.0` | `0.805` | `+0.0248` | `+0.7705` |
| `stretch=8.0` | `0.492` | `−0.0032` | `+0.0803` |
| `stretch=12.0` | `0.678` | `−0.0020` | `+0.0180` |

> **Terms positive at 8 of 8, zero sign changes along the grid.
> Gate positive at 4 of 8, two sign changes along the grid** — while doing
> `49%` to `107%` of the terms channel's mechanical work at those same values.

**That is the zero domain.** One channel holds a sign across the entire
population sweep; the other cannot, and it cannot while pushing the economy
about as hard.

**The gate's mechanical effect, from the records that measured it.** `A3h-1`:
total `|d cycles|` for the gate is **`74.0`** against the terms channel's
**`85.6`**, a ratio of **`86%`**; nodes with a changed cycle count `19.4`;
largest net-worth move `6.271e+02`.

> **A leaking decomposition would not look like this.** A leak shows up as a gate
> cell with a stable sign, and that is the one thing neither the eight active
> points nor the fifty-seven pooled ones ever produced.

**Written in this order, and the order is recorded because it is the finding's
own history**: this section's first draft rested on the five exact zeros. The
`A3i` entry in `RESULTS.md` names why they are over-determined, `A3k-6` and
`A3k-7` were added to answer it, and the reading moved to the eight active
points. **The exact zeros looked like the strongest evidence and were the
weakest.**

### 11.4 What this is not

**It is not a verdict on A3-8, which stays void.** `A3g-5` measured why: the two
clauses of A3-8′ sit at opposite ends of the population knob, the peripheral
third first enters the population at `stretch 8.0`, and by that value the
both-cell gap has fallen from `25.8305` to `0.0932`. **The zero domain needs
neither clause.** It needs the two cells side by side, which every record
prints, and it asks a different question of the same numbers.

**It is the third zero domain and the smallest, and the three must never be
quoted as one reading.** `B13` is the large one, `81,968` states of an exchange's
published implied spread against the two-leg derivation from its own outrights,
paired with the directly quoted member of the same family at `65%` to `96%`
non-zero. B6's is an arithmetic identity inside a third party's published table.
**This one is a mechanism model's own machinery agreeing with its own theorem**,
and it is the only one of the three on the A track. B6's is an arithmetic identity inside a third party's published
table, `3.5e-6` over 238 publication days on a real price system. **This one is a
mechanism model's own machinery agreeing with its own theorem.** What they share
is the only structure that makes either worth anything: **a zero and a non-zero
off the same instrument.**

**It is not an exact zero at every point**, and it is reported as amplitude and
sign stability rather than as a test statistic, which is what `D24` asks of a
point prediction of zero.

**It is carrier-specific.** `b₁(G) = 0` is a property of the star. On a position
graph with two distinct routes between some pair, slice cycles exist and this
argument does not run.

### 11.5 What it discharges

O11 said the coverage account never states what the framework forbids. **This
states one thing it forbids and shows the model obeying it**: on a star, an
admission threshold contributes nothing to a loop sum, however hard it pushes
the economy around. The A track now carries the same pairing the B track does,
and the two are independent in mechanism as well as in carrier — **one is a
publisher's arithmetic, one is a model's topology.**
