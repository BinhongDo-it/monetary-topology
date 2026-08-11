# A4: is connectivity a covariate or the space the covariates act in?

Pre-registration. **Written before any A4 code existed.** Every switch, outcome
measure and threshold below is fixed here.

---

## 1. The question

The usual way to write the problem treats connectivity as one regressor among
several:

```
R  =  f(inheritance, education, capital returns, assortative mating, institutions, C)
```

The hypothesis this stage tests is that `C` does not belong in that list, because
it is not parallel to the others but underneath them:

```
C  →  { claim accumulation, access to opportunities, return heterogeneity,
        network position, future connectivity }  →  R
```

On that reading `C` changes the **space the other mechanisms act in**. Inheritance
transmits a position, and what a position is worth depends on what it is connected
to. Education raises a wage, and what a wage buys depends on which markets the
earner can reach on what terms.

These two readings differ in a way a factorial design can see. If `C` is parallel,
switching it off leaves the other mechanisms working at close to full strength.
If `C` is upstream, switching it off attenuates them.

---

## 2. Design

A `2 × 2⁴` factorial: connectivity on or off, crossed with four competing
mechanisms each on or off. Thirty-two cells, `SEEDS` replications each.

| switch | on means | off means |
|---|---|---|
| `C` | the stratified adjacency structure of stages A0 and A2 | **complete graph, uniform access** |
| `I` inheritance | holdings transmitted across generations with a retention coefficient | no transmission |
| `E` education | heterogeneous, persistent wage multipliers | uniform multiplier |
| `K` capital returns | return on holdings varies across agents, exogenously | uniform return |
| `M` assortative mating | agents pair by similarity of holdings and merge | random pairing |

### What "C off" must mean, and why this is the whole design

If `C = 0` meant "no economy", the test would be rigged and worthless. It means
**a complete graph with uniform access**: every agent can reach every other on
identical terms. Nothing else is removed.

Under that definition the four competitors keep working. Inheritance concentrates
holdings across generations whether or not a network exists — the
Bowles-Gintis line and ordinary OLG models have no network at all and still
generate substantial persistence. Exogenous return heterogeneity makes holdings
diverge regardless of who transacts with whom. Assortative mating merges similar
holdings on any graph. So the null arm is a live economy in which the competing
explanations are free to do their work.

### Each competitor is implemented in its strongest exogenous form

This is the second and more important guard against a rigged result.

Return heterogeneity, on this project's own account, is **downstream of** `C`:
better-connected agents obtain better terms, which is exactly what stage B2
measured. Implementing it that way would build the conclusion into the mechanism.
So in A4 it is imposed **exogenously**, drawn from a fixed distribution, with no
dependence on the graph at all. The same applies to education and to mating.

Each competitor is therefore handed its best case: it acts directly, at full
strength, without needing `C` for anything. If `C` still amplifies it, the
amplification was not put there by construction.

### The wage edge under `C = 0`

Stage A0's only downward edge is the wage bill, and switching `C` off cannot mean
removing it: a production layer with no income is a dead economy, and comparing
four mechanisms on a dead economy establishes nothing.

So the wage edge **persists in both arms and its distribution becomes uniform**
when `C = 0`. "Connectivity off" means access is undifferentiated, not that
nothing flows. The production layer can be subdivided further in principle, but
that subdivision is not what any claim here turns on, so a uniform distribution
loses nothing the argument needs.

This does mean the `C` switch changes two things at once, the adjacency structure
and the wage distribution. They are not separated into a fifth factor because in
this framework they are the same object seen twice: who can reach whom, and on
what terms the reaching happens.

### Households, generations, and what "off" means for each

Inheritance and mating need a demographic layer that stage A0 does not have. It is
added as follows, and every switch position below is fixed here.

**Marriage is a merge, not an average.** Two agents pair into a **household** that
acts as a single agent from then on. Averaging would leave two agents holding the
same amount while still choosing separately, which is a transfer rather than a
marriage; a household binds action and consequence together. Dissolution is not
modelled.

**The generational cycle.** `N` agents pair into `N/2` households; households act
for `G` rounds; at the generational event each household dissolves into two
offspring agents, so the unit count returns to `N` and is stable in steady state.
`G` is a parameter and no criterion depends on it.

**`M` off means random matching, not celibacy.** The merge still happens; only the
matching rule changes, from similarity in holdings to uniform at random. This
isolates assortativity rather than marriage, and it is the same contrast the
published counterfactual in §6 draws.

**`I` off means equal division, not destruction.** At the generational event with
`I` off, the dissolved households' holdings are pooled and divided equally among
all offspring. Total claims are conserved either way, so the stock-flow assert in
`economy.py` holds in both arms, and "no transmission" does not smuggle in a
wealth shock.

**With `I` and `M` both off the generational event does not fire at all.** Random
pairing followed by a merge followed by an equal split would reshuffle holdings
even with both channels nominally off, which would break the reproduction
requirement below. The demographic layer is therefore itself conditional on at
least one of its two channels being on.

### Strict generalisation

With `C` on and all four competitors off, A4 must reproduce the existing A0 and
A2 results **bitwise**. A4 is built on `economy.py` and `network.py` rather than
on a new model, so that this is checkable rather than asserted. A generalisation
that cannot reproduce its own special case is not a generalisation, and the same
discipline already governs `elasticity`, `intermediate_size` and `min_size`
elsewhere in the repository.

---

## 3. Outcome measures

**Registered: the Gini coefficient of claim holdings** at the end of the run. It
is the measure the competing literature reports, which is what makes the
diagnostic comparisons in §6 possible at all.

**Reported alongside: `1/HHI`**, the effective number of holders, which is
threshold-free and is the measure stage A2 already uses. If the two disagree in
direction that fact is reported and the disagreement is the finding.

Both are computed on the same final-round holdings vector, so no weighting choice
separates them.

---

## 4. The discriminant

For each competitor `X`, define the **amplification**

```
              R(C=1, X=1) − R(C=1, X=0)
A(X)   =     ---------------------------
              R(C=0, X=1) − R(C=0, X=0)
```

the effect of switching `X` on with connectivity present, divided by its effect
with connectivity absent. Both differences are averaged over seeds before the
ratio is taken, and the denominator is required to clear the strawman floor of §5
before the ratio is reported at all.

**Upstream predicts `A(X) > 1` for every `X`.** Parallel predicts `A(X) ≈ 1`. The
two readings give opposite predictions, which is what makes this a test rather
than an illustration.

---

## 5. Pre-registered predictions

**A4-1 — the null calibration.** With `C` off and all four competitors off,
identical agents on a complete graph, the Gini is below `0.02`. If a model of
identical agents with no mechanism produces stratification, the stratification is
an artefact of the implementation and nothing below means anything.

**A4-2 — connectivity alone is sufficient.** With `C` on and all four competitors
off, the Gini exceeds the null arm by at least `0.05`. This is the existence claim
and it is the only one stage A restates from A0 and A2.

**A4-3 — no competitor is a strawman.** Each competitor alone, with `C` off,
raises the Gini by at least `0.02` over the null. A competitor that does nothing
on its own has been implemented too weakly for the comparison in A4-4 to mean
anything, and if this fails the run reports the comparison as **void** rather than
reporting a favourable ratio.

**A4-4 — connectivity is upstream.** `A(X) > 1` for all four competitors, and
`A(X) > 1.25` for at least three of them. The second half exists so that four
ratios of 1.01 cannot pass.

**A4-6 — caste is derived, not assumed.** The matching rule looks only at
similarity in **holdings**. It never sees which layer an agent belongs to. So if
households form predominantly within a layer, that is a derived result rather than
an input.

Registered direction: **at the same assortativity parameter, `C = 1` produces a
lower cross-layer pairing rate than `C = 0`.** With connectivity off, holdings are
not separated by layer in the first place, so similarity matching has nothing to
lock onto and the cross-layer rate should sit near what random matching gives.
With connectivity on, the separation exists and matching preserves it.

This is the sharpest available form of the upstream claim: connectivity does not
prevent anyone from marrying anyone. It arranges the holdings so that a rule which
never mentions layers ends up respecting them.

**A4-5 — order does not decide it.** The result holds under both orderings in
which the channels are applied within a round. If it does not, the finding is
about the update order rather than about connectivity, and is reported that way.

---

## 6. Diagnostics, reported and not registered

External anchors, to show the competitor implementations are not toys. These are
**not criteria**: the models differ, so the magnitudes are comparable in order and
not in value.

| mechanism | published counterfactual | what A4 reports |
|---|---|---|
| assortative mating | Greenwood and co-authors: reassigning US 2005 matching at random takes the Gini from about 0.43 to about 0.34 | the Gini change from switching `M` off with `C` off |
| inheritance | OLG and Bowles-Gintis style models generate substantial wealth persistence with no network | the Gini change from switching `I` off with `C` off |
| education | decompositions attribute a material share of the time trend in earnings inequality to changing education returns | the Gini change from switching `E` off with `C` off |

If A4's mating channel moves the Gini by a thousandth where the published
counterfactual moves it by nine hundredths, the channel is a strawman and A4-3
should have caught it. The table is here so a reader can check that judgement
independently rather than take A4-3's threshold on trust.

---

## 7. Falsification

| observation | consequence |
|---|---|
| `A(X) ≈ 1` for all four competitors | Connectivity is **parallel**, not upstream. The claim in `PROJECT_PLAN.md` §8.3 is withdrawn and rewritten, and the upstream diagram is removed from the plan rather than qualified. |
| `A(X) < 1` for any competitor | Connectivity *dampens* that mechanism. Reported prominently; the upstream reading survives only for the mechanisms where it holds, and must be restated per mechanism. |
| A4-3 fails for any competitor | The comparison against that competitor is **void**, not favourable. Reported as void. |
| A4-2 fails | Connectivity alone is not sufficient, and stages A0 and A2 do not say what this project has said they say. That would be the most serious failure available here. |
| the result flips under A4-5's alternative ordering | The finding is about update order. Reported as such, and no upstream claim is made. |
| the cross-layer pairing rate is the same with `C` on and off | Connectivity does not arrange holdings into anything a similarity rule can lock onto. A4-6 fails and the sharp form of the upstream claim is withdrawn, whatever the amplification ratios say. |
| the cross-layer rate is *higher* with `C` on | Connectivity mixes rather than sorts. Reported prominently, because it would run against the framework's account of stratification and not only against A4-6. |

---

## 8. What A4 cannot establish

**It cannot give a share.** A4 shows whether connectivity is upstream of the other
mechanisms in a model where all five are switchable. It says nothing about how
much of observed stratification connectivity accounts for in the actual economy.
That is an empirical question and a simulation cannot answer it. Any statement of
the form "connectivity explains N% of inequality" is outside what this stage
licenses, and the repository does not make one.

**It cannot rank the competitors.** The competitors are implemented at whatever
strength makes them non-trivial, not at calibrated real-world magnitudes. Their
relative sizes in A4 are properties of the parameterisation.

**It is a simulation.** Its status is the same as A0's and A2's: it establishes
that a mechanism *can* work this way, which is a claim about possibility. The
empirical counterpart, whether the connectivity channel is present in real terms
at all, is stage B2, and the two have not been linked in code. That gap is
recorded in `PROJECT_PLAN.md` §12.1 as the largest open seam in the project and A4 does
not close it.

---

## 9. Changes after pre-registration

Entries carry the timing of each change, and any change made after a result was
read is flagged in bold, in the same format as `b2_measurement.md` §10.

### 9.1 Made before any A4 code was run

**Strict generalisation reduces to stage A2 alone.** §2 requires the control cell
to reproduce "the existing A0 and A2 results bitwise". A0 is a block model whose
state is a four-vector of strata, and every outcome measure here — the Gini,
`1/HHI`, households, inheritance — is defined on per-agent holdings. Bitwise
reproduction of A0 is not a demanding requirement that A4 fails, it is not
defined: the two models do not share a state space. A4 is built on `network.py`,
whose state is a two-hundred-node holdings vector, and the control cell
reproduces the stage A2 run bitwise. Enforced by
`test_control_cell_reproduces_a2_bitwise`.

**The `C` switch also flattens the spending propensity, and the initial
holdings.** §2 says the switch sets the adjacency and the wage distribution, and
declines to separate those two on the ground that they are one object seen
twice. Two further quantities turn out to belong to the same object. Stage A2
assigns the spending propensity *by layer* and distributes the initial claim
stock *by in-degree within a layer*. With a complete graph there is no layer for
either to be assigned by, so both collapse: every node draws the same propensity
and holds the same opening balance. Neither is an extra assumption; each is what
its own definition returns when connectivity is removed.

The propensity is flattened at the **claim-weighted** mean of the two layers'
values, not the node-weighted mean. The invariant being held is the economy's
aggregate spending flow at `t = 0`. Node-weighting would instead hold the mean
propensity per node fixed, and since ninety percent of nodes sit in the
production layer the null arm would then turn its whole claim stock over about
twice as fast as the arm it is the reference for. Every mechanism acting on a
stock would be washed out in the null arm by a turnover difference the switch was
never meant to introduce, and `A(X)` would be reporting the weighting.

**Under `C = 0` the payroll edges are not subtracted from the discretionary
graph.** Stage A2 routes discretionary spending along the graph minus the payroll
edges, so that the financial layer's consumption cannot ride down the employment
channel. With uniform access every node both funds and receives payroll, so that
mask is the entire matrix and the subtraction empties the discretionary graph.
The null arm would consist of a payroll transfer that is a wash for every node,
holdings would never move, every competing mechanism would report exactly zero
against a perfectly uniform reference, and the whole factorial would be measured
against a dead economy. The subtraction exists to keep two distinct channels
distinct, and with a complete graph every edge is already both, so it has nothing
to separate. Guarded by `test_uniform_access_leaves_the_discretionary_graph_alive`.

**Marriage is an average under lockstep rather than a merge into one slot.** §2
pinned the merge and ruled out averaging, on the ground that averaging "would
leave two agents holding the same amount while still choosing separately, which
is a transfer rather than a marriage". The implemented household pools and splits
its holdings evenly each round *and draws a single spending propensity between
its two members*, so the separate choosing is gone and the stated reason is
satisfied. Both members keep their slot and both keep their edges.

The letter was changed because the merge introduces two artefacts, and neither is
cosmetic:

1. A merge leaves the vacated slot holding zero. The Gini is computed on that
   vector, so the existence of marriage alone would push it toward one half in
   every cell where `I` or `M` is on, with no mechanism involved.
2. A merge must discard one partner's adjacency row. Marriage would then be
   mechanically reducing connectivity, which places a term with the same sign as
   `C` inside the `M` channel and makes `A(M)` uninterpretable.

**Ties in the matching key are broken at random, never by slot index.** In the
`C = 0` arm every agent holds the same amount by construction, so a stable sort
ranks them in index order, the matching key becomes the index, adjacent slots
pair, and the cross-layer rate falls to roughly one over the financial layer's
size — about `0.05` against a random baseline of `0.181`. That number is a
property of the sort routine presented as a property of assortative mating, in
the same family as the `0.975` incident recorded in `PROJECT_PLAN.md` §11.2, and it
lands in exactly the arm prediction A4-6 uses as its reference. Guarded by
`test_ties_in_holdings_are_broken_at_random_not_by_index`.

**Persistent traits are drawn once when no generational event fires.** With `I`
and `M` both off the demographic layer does not fire, so a trait draw hung off
the generational event never happens and `E` and `K` silently do nothing while
still appearing in the factorial. With no generations there is one cohort and it
lasts the whole run. Guarded by
`test_traits_are_drawn_once_when_there_is_no_demography`.

### 9.2 Made after a first exploratory run, and marked as such

**This stage depends on stage A3, and the pre-registration did not notice.**

The four competitors registered here are mechanisms that act on wealth. The
model they were registered on top of has no wealth. Stage A0 and stage A2 carry
one state variable, a transaction balance that each node spends down at its
propensity every round, and an endowment handed to a node does not survive to
the next generation:

| arm | node | half-life | left after 10 rounds | left after 40, one generation |
|---|---|---|---|---|
| `C = 1` stratified | richest | 2 rounds | 32.2% | 28.06% |
| `C = 1` stratified | median | 5 rounds | 0.2% | 0.00% |
| `C = 0` uniform | richest | 1 round | 0.0% | 0.00% |
| `C = 0` uniform | median | 1 round | 0.0% | 0.00% |

Measured by injecting ten percent of the claim stock into one node at round 150
and tracking the deviation from that node's unperturbed path.

So inheritance transmits a balance that has evaporated before the heirs act,
assortative mating sorts a quantity that evaporates, and heterogeneous returns
compound against a per-round decay they have to overpower first. Education is
the exception and the exception is diagnostic: it acts on the payroll **flow**
rather than on the stock, and it is the one competitor that clears A4-3 at a
defensible strength.

This is not a coding fault and it is not a weak implementation, which matters
because A4-3's falsification row assumes those are the only two ways a
competitor can come out flat. It is a missing layer. `PROJECT_PLAN.md` already
recorded the same absence from the other side, before A4 was written: stages A0
to A2c report *levels* and cannot produce a widening gap, because no asset holds
a value that responds to where claims accumulate, and compounding lives in the
stage A3 asset-price channel.

**Consequence.** A4 is re-sequenced after A3. Until a stock exists, A4-3 returns
void for `I` and `M` at every parameter setting, and the void is a statement
about the carrier rather than about the two mechanisms. The observed figures are
`+0.00006` for `I` and `-0.0001` for `M`, unmoved by pushing the retention
coefficient to 1.0 or the assortativity to 1.0, and unmoved by supplying an
exogenous source of dispersion through `E`.

**The Gini ceiling is a second and separate defect in the discriminant.** The
control cell reaches a Gini of `0.935`, so a competitor switched on under
`C = 1` has `0.065` of room while the same competitor under `C = 0` has `0.99`.
`A(X)` is compressed by the bound and not by anything about connectivity:
`A(E) = 0.00` and `A(K) = 0.06` against a registered prediction of `A(X) > 1`,
while the same comparison on `log(1/HHI)`, which has no ceiling, gives
`A(K) = 5.31` in the registered direction. This survives the A3 dependency,
since the ceiling comes from the graph driving the effective holder count to
about fourteen of two hundred. Not resolved here; §3 already provides for the
two measures disagreeing and calls the disagreement the finding.

**Household pooling frequency is an explicit switch and both endpoints are
run.** §2 says a household "acts as a single agent from then on", which reads as
settling its internal budget every round. Every round is also a zero-cost
transfer of unbounded bandwidth between two arbitrary nodes, so a household
straddling the thermocline is a permanent conduit across it. On the stratified
arm that conduit is almost the whole of what `I` and `M` appear to do: forcing
pairs to form within a layer cuts their effect on the Gini from `-0.168` to
`-0.006`, and pooling only when the estate is settled cuts it to `+0.0001`.

Neither endpoint is privileged. `A4Config.pooling` takes `"round"` and
`"generation"` and both are reported. Note what this rules out as well: the
originally pinned merge into a single slot has the mirror defect, since it must
discard one partner's adjacency row and so makes marriage reduce connectivity
mechanically. Any household model on a graph has to decide what becomes of the
pair's two network positions, and there is no choice that leaves the graph
alone. The honest form is to make the decision a parameter.

Because pooling under `"generation"` empties the within-round ordering, A4-5
gains a second axis: `A4Config.event_order` tests `inherit_first` against
`match_first`, which is matching on realised endowment against matching on
family background.

### 9.3 Open defect: `uniform_access` also flattens the opening holdings, and that biases `A(X)` upward

Raised by the original stage-design session on review, and not found by the
session that wrote §9.1. **Not repaired here.**

§9.1 justified four consequences of switching `C` off on one ground: each is
defined *by layer* in stage A2 and a complete graph has no layers to define it
by. That holds for the adjacency, for payroll and for the spending propensity.

**It does not hold for the opening holdings.** Holdings can be drawn from the
same marginal distribution without any reference to a layer. Collapsing them to
an equal split is a stronger move than the argument licenses, and it has a
direction:

- With `C = 0` the null arm starts **perfectly equal**, so every competing
  mechanism has to generate stratification from nothing.
- Inheritance and assortative mating transmit and sort dispersion; neither
  creates any (§9.2). Their denominator in `A(X)` is therefore pinned near zero
  **by the construction of the null arm**, not by anything about the mechanism.
- `A(X)` is inflated, and inflated **in the direction the hypothesis wants**.

In the world, inheritance acts on a distribution that is already unequal. The
null arm as built removes that, and it removes it only on the side that makes
connectivity look more upstream than it is.

**The check, which is cheap.** Run the `C = 0` arm with the *same* opening
holdings distribution as `C = 1` — same values, assigned at random rather than
by layer and in-degree — and recompute `A(X)`. If the conclusion is unchanged
this defect does not bite. If `A(X)` falls materially, **A4-4's threshold has to
be reset before A4 is run at all**, and the reset must be recorded here as a
pre-result change since no A4 criterion has yet been evaluated.

---

## 10. The discriminant is replaced: `C` upstream means `C` decides where `H¹` acts

**Registered 2026-08-10, third hand-off session, before any A4 code is run
against it.** The amplification ratio of §4 is not withdrawn; it is demoted to a
secondary reading, for three reasons already on the record and one new one.

**Why the Gini ratio is the wrong instrument.** The Gini is bounded and the
control cell already sits at `0.935`, so the numerator has `0.065` of headroom
against a denominator of `0.99` (`PROJECT_PLAN.md` §12.7). `A(X)` is a ratio of
differences reported as a point with no sampling distribution behind it, and on
five seeds a ratio of small differences can straddle `1` without anyone seeing
it. And §9.3's defect — `uniform_access` also flattens the opening holdings —
biases `A(X)` upward.

**The new one comes from a measured fact and a run.**

*Measured, not assumed*: under `uniform_access` the centrality spread is
**exactly zero**, therefore the terms spread is **exactly zero**, therefore

> **`C = 0` ⇒ `H¹ ≡ 0`.**

*Run*: `a3_asset_channel.md` §5.2 established by intervention that the loop sum
carries the divergence — removing it takes the gap from `+23.267` to `+1.409` —
while the admission gate's contribution is not distinguishable from zero across
seeds.

Put together, the upstream hypothesis stops being a statement about effect sizes
and becomes a statement about **routing**:

> **Upstream**: with `C` on, each competitor's contribution to divergence is
> routed through `H¹`, so a large share of it vanishes under `do(κ_pay = 0)`.
> With `C` off there is no `H¹` to route through, so the competitor falls back
> on its own direct channel and does less.
>
> **Parallel**: the competitors' effects are indifferent to `do(κ_pay = 0)` and
> roughly equal with `C` on and off.

### 10.1 It must be a decomposition, not a ratio

`A(X)` computed on accumulated holonomy has a **structurally zero denominator**
under `C = 0`, because `H¹ ≡ 0` there for every competitor. **That is not a
numerical inconvenience to be worked around. It is the hypothesis.** A design
that divides by it has converted the finding into an error condition.

The measurable is instead, within each `C` arm and for each competitor `X`:

```
routed(X | C)  =  [ D(C, X, κ_pay=1) − D(C, X, κ_pay=0) ] / D(C, X, κ_pay=1)
```

where `D` is the divergence measure of `a3c_load_bearing.py`: each node paired
against **itself** in the null cell, normalised by its own opening claims, the
central tercile's mean minus the peripheral tercile's, over the agents who
complete a round trip in every cell.

Registered readings:

- `routed(X | C=1)` large and `routed(X | C=0)` near zero **and** `D(C=1)` above
  `D(C=0)` for every `X` → upstream.
- `routed(X | C=1)` near zero for every `X` → the competitors do not act through
  the obstruction, and `C`'s role, whatever it is, is not the one this project
  has claimed.
- Any `X` whose `routed` share flips sign across seeds → **no share is quoted
  for that competitor**, per the rule adopted in `a3c_load_bearing.py`.

### 10.2 What this inherits, and what it does not fix

Inherited from A3c and not re-argued here: the mean-cost hold, so cells differ
in dispersion and not in level; the paired population, fixed to the intersection
of traders across cells; the zero calibration built from two independent
executions rather than an alias; and the refusal to decompose when a cell's sign
is unstable across seeds.

**Three properties the Gini ratio lacks.** It is unbounded, so §12.7's ceiling
does not arise. It is measured on the object the framework says is doing the
work rather than on a summary of the outcome. And its degenerate case under
`C = 0` is the hypothesis rather than a division by zero to be patched.

**Not fixed, and both still block.** §9.3's opening-holdings flattening under
`uniform_access` still contaminates any comparison across `C`, and it is
independent of which outcome measure is used. And `a3_asset_channel.md` §6.4:
A3-6's stock survives for the asset-holding population and not for the median
node, so **A4 must be restricted to the population that holds a stock**, and the
criterion body must say so rather than leaving it in a detail string.
