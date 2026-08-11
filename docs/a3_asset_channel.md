# A3: the asset channel

**Rewritten 2026-08-10, third hand-off session.** The previous document is kept
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
| `s` = `stretch` | how far short a node may be and still enter | `3.0` | `{1, 2, 3, 5}` |
| `stretch_cost` | `uncounted` or `counted` | `uncounted` | both |
| `max_units` | cap on units per node; `0` is no cap | `0` | `1` runs and produces zero trades |
| `open_tiers` | tiers forced open regardless of claims | `()` | A3-5 only |
| `bins` | centrality bins for the product-graph `δ` | `4` | `{2, 4, 8}` |
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
| **A3-8** | **the holonomy is load-bearing** | see §5.2 | **pass**; see §5.2 |

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

---

## 6. Failures and limits about the modelled world

Implementation failures are in the expired document. These are not.

### 6.1 Eleven measurement-validity failures, and the file that exists because of them

None was a fact about the world; every one was a measure whose name and content
disagreed. They are catalogued as six failure modes with a seven-point checklist
in `MEASUREMENT.md`. **That file is the long tail that does not survive
compression into a hand-off note, and it is why the same error kept recurring
under different names.**

Four more were added by this session, all on the P-C measure, and they are worth
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
disclosed rather than hidden: it is being applied to a new domain by a session
that had already seen the richest node's number, and it is kept because
lowering it would be worse than carrying it.

**Three consequences, and the third is the one that matters for A4.**

*The contrast is the finding, not the verdict.* A one-off transfer to a node
with no asset is recaptured within a generation — `0.1%` — while the same
transfer to a holder is not. Retention rises steeply with position and does so
non-monotonically in claims. **That is the redistribution-futility result, and
it is what A6 goes on to price.**

*The stock A3 was built to supply is thin.* `PROJECT_PLAN.md` §12.6 recorded
that A0 and A2 had no stock and A4 therefore could not run, and A3 exists partly
to supply one. It supplies a stock for **16 of 200 nodes, all upstairs**, whose
median holder retains **14%** over forty rounds.

*So A4 remains blocked, and for a better-stated reason than before.* Its four
competitors act on wealth. Measured where the wealth is, they describe
stratification **within** those sixteen upstairs nodes, not the economy's — and
inheritance in particular, which is a generation-scale channel, has a
forty-round median retention of 14% to transmit. **A4 must not be run as
designed until this is resolved**, and switching its domain silently to the
holders would reproduce exactly the error refused above.

### 6.5 The registered §7 grid has not been run

`{η, κ, τ, φ, s}` and the centrality binning have not been swept, and "no
conclusion may live at one value of any of them" is a registered promise. **This
is a breach of a registered commitment, not a todo.** The exception is `η`,
swept between `0` and `1` in the rent arm and in A3-5, and `κ`, swept in A3c.

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
would make them ours, has not started.

So the resonance between this result and ordinary observation is the third
correspondence standard, 解释力, which is the weakest of the ones that touch the
world: the phenomenon was there first. **Persistence is the fourth standard,
预测力, because no data used in building this model contains it.**

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
