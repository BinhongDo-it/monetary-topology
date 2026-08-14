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

> **Extended 2026-08-13, see §11.6.** Both are computed a second time on the
> production layer alone and the pair is reported beside this one. Nothing here
> is withdrawn. The reason is a units mismatch older than this stage's first
> run: §6's external anchors are household income Ginis over a whole population,
> while the aggregate measure above is taken over a population containing a
> twenty-node financial layer holding `99.7%` of the stock, and it sits at
> `0.937` where the anchors sit at `0.43`.
>
> **Measured, 2026-08-13.** The two measures above agree with each other in
> every cell, in sign and in size against their own floors, so §3's clause about
> the two disagreeing does not fire. §11.2 has the table.

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

> **Amended 2026-08-13 for transmitting mechanisms, see §11.5.** For `I` and `M`
> both terms are taken with a generating mechanism switched on, `A(X | G)`, and
> both generators are used and both reported. §9.2 classifies `I` and `M` as
> transmitting dispersion without creating any, and §11.3 measures that the
> `C = 0` arm is an attractor at a Gini of `0.0071` reached in five rounds from
> any opening, so this form's denominator for a transmitting mechanism is a
> reading of the graph draw. `E` and `K` keep the form above.
>
> Also amended for reading rather than for arithmetic: `A(X)` is reported per
> seed as well as pooled, no point value is quoted where the per-seed sign
> moves, and both arms' realised level is reported beside every ratio (§10.4).

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

Raised on review of the original stage design, and not found by the pass that
wrote §9.1. **Not repaired here.**

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

#### 9.3a This is a task with a method, not a decision awaiting one

**Added 2026-08-13.** `PROJECT_PLAN` §13.1 has carried this as one of two
rulings blocking A4 since 2026-08-10. **It is not a ruling.** The defect, its
direction, and the check are all specified above, and the check does not need
anyone to choose between alternatives. Listing it as undecided kept A4 waiting
on an answer nobody was being asked for.

**A3 supplied the template while this sat.** `a3_asset_channel.md` §6.4c is the
same shape: a modelling choice riding on a switch that had been justified for a
different reason, in that case a rent bill keyed on the layer index while its
receipts were keyed on measured units. The handling there is the handling here.
Add a spec field. Default reproduces the current arm bit for bit and a test
asserts it rather than the docstring claiming it. The other arm must be shown
not to be inert, because a switch that reaches no code passes every reproduction
test. Then measure, **and be prepared for the answer to be that it does not
bite**, which is what A3's turned out to be: the median holder's retention moved
from `14.25%` to `14.56%` and the shape did not move at all.

**§10's replacement does not dissolve this, and the reason is worth stating.**
§10.2 records that the defect is independent of the outcome measure. The
mechanism is that under the new discriminant `routed(X | C = 0)` is near zero
for **two reasons at once**: there is no `H¹` to route through, which is the
hypothesis, and there is no initial dispersion for a transmitting mechanism to
transmit, which is this artifact. Inheritance and assortative mating transmit
and sort dispersion without creating any (§9.2), so on a perfectly equal opening
they have nothing to act on whatever the routing does. **The new measurable
separates the two no better than the old ratio did.** Fixing the opening
holdings is what separates them, and it is upstream of both readings.

---

## 10. The discriminant is replaced: `C` upstream means `C` decides where `H¹` acts

**Registered 2026-08-10, before any A4 code is run against it.** The amplification ratio of §4 is not withdrawn; it is demoted to a
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

**A fifth thing is inherited and it is a limit rather than a piece of
machinery. Added 2026-08-13.** The paired population above is not a sample of
the economy. `a3_asset_channel.md` §5.3 measures it: over twenty seeds it is
**the top eighth of the production layer by centrality**, band `[86.8, 100]`,
and the peripheral tercile completes zero round trips in every cell **including
the null**, so it is not the treatment that removed them. §6.4d then gives the
reason. The price rule and the gate together shut the production layer out of
the market at rounds `2, 2, 3, 3, 4` for the hard gate and `6, 6, 8, 9, 15` for
the soft one, and the units it already held take another ninety-three rounds on
median to grind away. **The layer is locked out on round three.**

`routed(X | C)` inherits that population whole. So A4's four competitors, all
of which act on wealth, would be measured among agents selected by having
traded, **and whether one trades is the outcome connectivity most strongly
drives**. That is not a small-sample problem. It is an estimand conditioned on
the variable whose upstreamness is the question, which is the shape
`MEASUREMENT.md` §5's fourth instance was added for and which its rule now
requires be reported: **state the treatment's variation over the measured
population before stating its effect.**

Concretely, whenever `routed(X | C = 1)` is reported, the centrality span of
the population it was measured on is reported beside it. A span of `[86.8, 100]`
means the four competitors were compared inside the top eighth of one layer, and
that has to be visible in the criterion body rather than inferable from a
detail string.

> **Correction, 2026-08-13, later the same day. See §10.4.** `[86.8, 100]` is
> §5.3's band for the **production-layer participants**, which is the quantity
> §5.3 reports. The paired population as a whole contains the entire financial
> layer, all twenty nodes, and its band over five seeds runs `[19.5, 99.5]`. The
> substance of this item is unaffected, since the point is that the population is
> selected on having traded. The number was the wrong number for the sentence.

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

### 10.3 The domain: move the window, do not widen the gate

> **The ruling below is withdrawn on 2026-08-13, later the same day, by
> measurement. See §10.4.** The window move does put the production layer inside
> the *holding* population and it does not put it inside the population
> `routed(X | C)` is defined on, because that population is defined by having
> **sold**. Nothing below is deleted. The two refusals and the three obligations
> still hold; only the third way out fails.

**Added 2026-08-13, and it closes the second of the two rulings `PROJECT_PLAN`
§13.1 has been carrying.** §10.2 states the constraint: A3-6's stock survives
for the asset-holding population and not for the median node, so A4 must be
restricted to a population that holds a stock. The question left open was which
population that is, given `a3_asset_channel.md` §6.4 measures it at sixteen
nodes of two hundred, all upstairs. Three ways out are now on the table and the
third is the one taken.

**Not this: restrict A4 to the sixteen.** Honest and available, and the result
would describe stratification inside the financial layer. §6.4's own third
consequence says as much. Inheritance in particular is a generation-scale
channel with a forty-round median retention of fourteen percent to transmit, so
the arm most central to A4's question is the one with least to work with.

**Not this either: widen the gate.** `a3_asset_channel.md` §6.5c records that
`stretch` already moves the measured population, from `18.4` at `s = 1.0` to
`98.8` at `s = 5.0` against `41.6` at the registered `s = 3.0`, and
`PROJECT_PLAN` §13.3 records independently that `s = 5` admits eighty-eight
production-layer nodes to the lowest tier against twenty-three at `s = 3`. The
lever exists. **It is refused for the reason §6.5c states when it records the
lever**: choosing a parameter after seeing which value makes a channel quotable
is the move §5.1's demotions exist to prevent, and the only registered
justification for `s` points the other way, since §13.3 calls `s = 2` to `s = 3`
the marginal population and `s = 5` therefore not marginal. A design that needs
a bigger `n` and reaches for a parameter to get one has chosen its sample.

**This: measure where the stock exists rather than where the criterion's shock
lands.** §6.4c ran the retention profile at shock round 20 and the two by two
completes there: sixty to sixty-two production-layer holders across five seeds,
against zero at round 150. The stock A3 was built to supply **does** exist
downstairs, for roughly the first hundred rounds, and A3-6 does not see it
because its registered shock round of 150 falls after the grind is finished.

A4's window was never tied to A3-6's shock round. It inherited the requirement
to measure where a stock exists, and it read that as a statement about *who*
when it is also a statement about *when*. **So A4 measures in the window where
the production layer still holds**, which the counts put at roughly rounds ten
to forty and which decays to nothing by eighty.

Three things this obliges, and none of them is optional.

*The window is registered before anything runs, and it is registered as a
range with a reason rather than a point.* The reason is the holder counts, which
are `21/27/19` at round one, `13/16/8` at twenty, `6/11/4` at forty and
`0/0/0` at a hundred and fifty. A window that ends at forty is a window in which
the population is falling, and the falling is reported.

*It does not evade §10.2's fifth item; it reduces it.* Moving earlier does not
make the population a sample of the economy. It makes it larger and less
extreme, and the centrality span reported beside `routed(X | C)` is what says
by how much. If that span is still `[86.8, 100]` at round twenty, the window
bought nothing and the fifth item stands unchanged.

*A generation-scale competitor in a forty-round window is a different claim from
a generation-scale competitor in three hundred.* Inheritance is the arm this
bites. **A4 must say what one round is worth before it reads inheritance**, and
`PROJECT_PLAN` §16.1's second step is the standing record that the rounds-to-time
mapping has to be pinned before, not after. It is still not pinned. That is now
a precondition of A4's inheritance arm rather than a loose end elsewhere.

### 10.4 §10's three premises, measured; and the ruling that A4 keeps its parent

**Added 2026-08-13, after §10.3 on the same day and against part of it.**
`experiments/a4a_domain_probe.py`. Diagnostic: it scores nothing, writes no
file, and no number in `RESULTS.md` is produced or changed by it.

**Why this was run at all.** §10 defines `routed(X | C)` on
`a3c_load_bearing.py`'s divergence measure `D`, which needs `κ_pay` and
`κ_gate`. Those are `AssetSpec.terms_spread` and `AssetSpec.gate_spread`.
`A4Model` subclasses `Network`; it has no `AssetSpec`, no asset market and no
`cycles`. **§10 was registered against a class that cannot compute it**, and
there is no `experiments/a4_*.py` at all, so this was found while the runner was
being designed rather than after it ran. §13.2's "代码已写，判据跑不了" is
accurately "the model is written, the experiment is not".

Two ways out. **甲**: reparent `A4Model` onto `A3Model` with a closed asset
channel as the default, so the control cell reproduces bitwise. **丙**: set §10
aside as A4's discriminant, restore §4's `A(X)` to primary, and take the stock
from §16.2's injection. Three claims decide it and each is a count.

#### Claims 1 and 2: the population §10 can compute on

Paired population is `cycles > 0` in every cell, as `a3c_load_bearing.py`.
Holding population is `units.sum(axis=1) > 0` in the `both` cell. Five seeds,
`FIXED` and `CELLS` copied from A3c verbatim.

| horizon | paired | of which financial | holding | of which financial | **both** | of which financial |
|---|---|---|---|---|---|---|
| 10 | 10.4 | 5.6 | 35.4 | 20.0 | **5.6** | **5.6** |
| 20 | 20.2 | 11.2 | 29.0 | 19.4 | **11.0** | **11.0** |
| 40 | 30.0 | 16.8 | 23.8 | 19.0 | **16.0** | **16.0** |
| 150 | 41.6 | 20.0 | 16.4 | 16.4 | **16.4** | **16.4** |
| 300 | 41.6 | 20.0 | 17.2 | 17.2 | **17.2** | **17.2** |

The last two columns are equal at **every horizon and every seed**. Not one
production-layer node has ever been in the intersection. The `41.6` at A3c's
registered horizon is `a3_asset_channel.md` §5.3's `shared` figure to the
decimal, so this is a second reading of one pipeline rather than a second
implementation.

**The reason is the gate and not the horizon, which is why no window repairs
it.** `asset.py` increments `cycles[seller]` when a unit that was bought is
sold, so the paired population reads **has sold**. Upstairs the gate stays open,
a financial-layer node sells and buys back, and `cycles > 0` and `held > 0` hold
together. Downstairs §6.4d puts the hard gate shut at rounds `2, 2, 3, 3, 4` and
the soft one at `6, 6, 8, 9, 15`, so selling is one-way: a production-layer node
that has sold cannot re-enter, and one that still holds has not sold. The two
conditions are close to **mutually exclusive** downstairs. At round forty there
are `4.8` production-layer holders on average, `23.8` less the `19.0` financial,
and **none of them is in the paired population**, because still holding is what
not having sold looks like.

**So §10.3's third way out fails, and moving the window in either direction does
not recover it.** §10.3 read §6.4d's ninety-three-round grind and concluded that
an earlier window would catch the production layer while it still held. It does
catch it holding. Holding is not the entry condition. Moving earlier instead
makes the intersection *smaller*, `16.0` at forty and `5.6` at ten, because the
financial layer's own round trips have not accumulated yet. **The window move
costs population and buys nothing.** §10.3's two refusals stand, its three
obligations stand, and its ruling does not.

#### Claim 3: what `D` is made of under `C = 0`

`D` is a central-tercile minus peripheral-tercile difference **by centrality**.
§10's premise is that `uniform_access` gives a centrality spread of exactly
zero. Measured, at forty rounds, five seeds, the `both` cell, with the terms
spread taken **per tier** because `terms` is `(n, Q)` and `base_terms` differs by
tier:

| arm | centrality spread | terms spread | traders | holders | both |
|---|---|---|---|---|---|
| `C = 1` stratified | `1.000000e+00` | `1.150000e+00` | 37.2 | 23.8 | 17.2 |
| `C = 0`, flat opening | `0.000000e+00` | `0.000000e+00` | 142.2 | 119.0 | 63.2 |
| `C = 0`, `same_marginal` | `0.000000e+00` | `0.000000e+00` | 93.6 | 61.4 | 34.2 |

The premise holds exactly. And then, comparing A3c's four cells against the null
array by array, three seeds:

| arm | `both`, `H1_only`, `H0_only` against `null` |
|---|---|
| `C = 1` stratified | `terms`, `terms_gate`, `holdings`, `net_worth` differ as the design intends: `H1_only` matches the null on the gate, `H0_only` matches it on terms, `both` matches on neither |
| `C = 0` uniform | **all four arrays bitwise equal to the null, in all three cells, at every seed** |

**The algebra says it has to be.** `terms = base · (1 + κ (1 − c))`, and
`hold_mean_cost` multiplies by `(1 + κ_ref g) / (1 + κ g)` with `g = 1 − c̄`. A
complete graph makes `c` a constant, so `1 − c ≡ g` for every node and the two
factors cancel exactly: `terms` stops depending on `κ` at all. The same argument
runs on `gate_spread` and `terms_gate`. **Under `C = 0` the four cells are one
configuration executed four times**, and that is a property of the construction,
not of a seed or a sample size.

**Consequence, and it lands on §10.1.** `routed(X | C = 0) = [D − D] / D` with
every term exactly zero. Zero over zero, not near zero. §10.1's argument is that
`A(X)` on accumulated holonomy has a structurally zero denominator under
`C = 0`, that "a design that divides by it has converted the finding into an
error condition", and that `routed(X | C)` is the replacement. **The diagnosis
is right and the replacement carries the same defect one level down**, because
`D` is a tercile difference by centrality and centrality is precisely what
`C = 0` flattens.

What survives of §10's three registered readings:

- *`routed(C=1)` large and `routed(C=0)` near zero and `D(C=1) > D(C=0)` for
  every `X` → upstream.* **Dead.** The `C = 0` side is an algebraic identity, so
  the contrast cannot come out any other way, so it discriminates nothing.
- *Any `X` whose share flips sign across seeds → no share is quoted.* **Fires
  always** in the `C = 0` arm, on `0/0`.
- *`routed(X | C = 1)` near zero for every `X` → the competitors do not act
  through the obstruction, and `C`'s role is not the one this project has
  claimed.* **Alive.** Falsifiable, and it lives entirely inside the `C = 1`
  arm, needing no contrast and no denominator from the other one.

#### The ruling: 丙

**A4 keeps `A4Model(Network)`.** §10 is set aside as A4's discriminant, §4's
`A(X)` is restored to primary, and §16.2's injection supplies the stock. §10 is
not withdrawn and nothing in it is deleted.

The arithmetic, since neither side is free.

**甲 costs**: a reparent onto `A3Model`; a `_post_round` chain that neither class
currently threads, since `A3Model._post_round` and `A4Model._post_round` both
override the base without calling `super()`, so a naive merge by multiple
inheritance would drop the entire asset market silently, and a straight reparent
to `A3Model` would drop it just as silently unless `A4Model._post_round` is
edited to call up; a third registered
ordering beside `channel_order` and `event_order`, for asset market against
capital returns against household pooling; and a third rewrite of A4's
discriminant, after §4 and §10, before any A4 code is written. **甲 delivers**,
after that rewrite, one falsifiable reading measured on 16 to 17 nodes, all
financial layer, at every horizon.

**丙 costs** nothing structural, and its population is all two hundred agents,
because the Gini is computed on the full holdings vector. §10.2's fifth
inherited item does not arise for it at all. Its stock comes from issuance
rather than from A3's asset layer, which also turns the deliverable from a point
into a curve with a unit (§16.2).

#### §10's three objections to the Gini ratio, at their current status

**§9.3's flattening: repaired.** `NetworkSpec.uniform_opening`, default `flat`,
arm `same_marginal`, twelve tests in `tests/test_a4_uniform_opening.py`. §10 was
written 2026-08-10 and the repair landed 2026-08-13, so §10's statement that the
defect is independent of the outcome measure is true and its use as an argument
*against* the Gini ratio is spent. Probe 3a also sizes the defect somewhere §9.3
did not look: under `C = 0` the flat opening gives `142.2` traders and `119.0`
holders against `93.6` and `61.4` with the marginal preserved, so the flat
opening was inflating participation in the null arm by roughly half.

**The five-seed objection: repaired for free.** A3c's own rule, refuse to quote
a share whose sign moves across seeds, is a rule about reading a ratio of small
differences and it transfers to `A(X)` unchanged. It needs no reparenting and no
new machinery. **Registered**: `A(X)` is reported per seed and no point value is
quoted for a competitor whose sign moves.

**The ceiling: stands, with a known sign.** The control cell sits at `0.935`,
leaving `0.065` of headroom against a denominator of `0.99` (`PROJECT_PLAN`
§12.7). With `uniform_opening = same_marginal` both arms now open at the same
Gini, so the arm nearer the ceiling is the one whose numerator is compressed,
and that is `C = 1`. **`A(X)` is therefore biased downward**, which makes a pass
at `A(X) > 1` conservative and a failure unreadable. **Registered obligation**:
the realised final Gini of both arms is reported beside `A(X)`, so that a
failure can be told apart from a ceiling.

#### Carried forward rather than dropped

§10's third reading is the one live thing the reparenting would buy, and it is
named here so that it stays a decision rather than becoming an omission:
**is `routed(X | C = 1)` near zero for every competitor.** It is deferred until
§4's `A(X)` has run under injection, at which point 甲's cost can be weighed
against a result instead of against a hope. If it is taken up, §10.1's formula
has to be repaired first: report `D(C=1, κ=1) − D(C=1, κ=0)` in levels, and
record `routed(C = 0) ≡ 0` as an identity of the construction rather than as a
measurement.

Two things written into this document earlier the same day are corrected above,
both of them here rather than by deletion: §10.3's reasoning, and §10.2's
citation of `[86.8, 100]` as the paired population's band when it is the band of
that population's production-layer part.

---

## 11. The carrier is changed, and both repairs are registered before either runs

**Added 2026-08-13, after §10.4 on the same day. Nothing in §11.5 or §11.6 has
been run.** This section changes §3's outcome measure and §4's discriminant, and
it is written before the changed measurement exists so that the order is on the
record rather than asserted afterwards. The numbers that forced it come from
`experiments/a4_causal_primitive.py`, which scores nothing, writes no file and
evaluates no criterion.

### 11.1 Two preconditions discharged first

**§2's strict generalisation holds.** With `C` on and all four competitors off,
`A4Model` reproduces the plain `Network` **bitwise at five of five seeds**, at
the registered authority. So `uniform_opening` reaches no code in the `C = 1`
arm through the whole pipeline and not only in the unit test.

**§9.3's registered check does not bite, and that section required it be run
before A4 ran at all.** Re-running the `C = 0` arm at `flat` against
`same_marginal` leaves `A(X)` identical at printed precision for all four
competitors, `-2417.362 / 0.002 / 0.093 / 2515.500` on both. Only `C0_M`'s
cross-layer rate moves, by `0.0015`, and `C0_E`'s Gini in the fifth decimal.
**A4-4's threshold is therefore not reset on that account**, which is the
outcome §9.3a said to be prepared for.

`same_marginal` stays. It is the correct modelling choice for the reason §9.3
gives, and §11.2 records that it is inert as a repair for a reason §9.3 did not
have.

### 11.2 The instrument resolution table, and the reading rule it is read under

**The rule, fixed before the table below was looked at.** A measure has
*resolution* for a treatment in an arm when the paired effect is sign-stable
across seeds **and** large against that same measure's own spread across seeds
in the control cell of that arm. Where it does not, a criterion built on that
measure in that arm is **unreadable**: not a pass and not a failure. This is
checklist item 7 turned on the instrument rather than on the carrier. Within a
seed the model is deterministic, so a paired difference carries no sampling
noise and all the variation is across graph draws; the control cell's spread is
therefore an arm whose value under no treatment is the whole of what the measure
does when nothing is being done to it.

Five seeds, three hundred rounds, registered authority, `pooling = round`.
`stock moved` is the total-variation distance between the two final holdings
vectors paired by seed, the share of the stock ending on different nodes. It is
a diagnostic and §11.4 records why it is fenced.

| measure | arm | competitor | control | effect | floor (sd) | eff/sd | sign | stock moved |
|---|---|---|---|---|---|---|---|---|
| Gini | `C=1` | inheritance | 0.93673 | −0.17076 | 0.00468 | **36.45** | yes | **44.15%** |
| Gini | `C=1` | education | 0.93673 | +0.00001 | 0.00468 | 0.00 | no | 0.04% |
| Gini | `C=1` | capital | 0.93673 | +0.00008 | 0.00468 | 0.02 | no | 0.35% |
| Gini | `C=1` | mating | 0.93673 | −0.15038 | 0.00468 | **32.10** | yes | **41.55%** |
| Gini | `C=0` | inheritance | 0.00711 | +0.00007 | 0.00026 | 0.27 | no | 0.39% |
| Gini | `C=0` | education | 0.00711 | +0.00932 | 0.00026 | **35.62** | yes | 1.03% |
| Gini | `C=0` | capital | 0.00711 | +0.00080 | 0.00026 | **3.07** | yes | 0.22% |
| Gini | `C=0` | mating | 0.00711 | −0.00006 | 0.00026 | 0.23 | no | 0.37% |
| 1/HHI | `C=1` | inheritance | 13.75148 | +23.88213 | 0.95914 | **24.90** | yes | 44.15% |
| 1/HHI | `C=1` | education | 13.75148 | −0.00010 | 0.95914 | 0.00 | no | 0.04% |
| 1/HHI | `C=1` | capital | 13.75148 | −0.01763 | 0.95914 | 0.02 | no | 0.35% |
| 1/HHI | `C=1` | mating | 13.75148 | +21.46558 | 0.95914 | **22.38** | yes | 41.55% |
| 1/HHI | `C=0` | inheritance | 199.96931 | −0.00080 | 0.00208 | 0.38 | no | 0.39% |
| 1/HHI | `C=0` | education | 199.96931 | −0.16813 | 0.00208 | **80.64** | yes | 1.03% |
| 1/HHI | `C=0` | capital | 199.96931 | −0.00772 | 0.00208 | **3.70** | yes | 0.22% |
| 1/HHI | `C=0` | mating | 199.96931 | +0.00036 | 0.00208 | 0.17 | no | 0.37% |

**The two registered measures agree everywhere**, in sign and in magnitude
against their own floors. §3's clause about the two disagreeing in direction
does not fire, and there is no instrument choice to adjudicate. What they agree
on is that **each competitor is inert in exactly one arm**, and `stock moved`
says the inertness is in the treatment rather than in the summary: `0.04%` to
`0.39%` of the stock changes hands in the cells that read as nothing, against
`41%` to `44%` in the cells that read as something.

`A(X)` is a ratio across the two arms. So for every competitor one of its two
terms is a reading of the graph draw, which is why the ratios come out at
`±2400` with the sign moving at every competitor. That is not a threshold
problem and no choice of scalar summary repairs it.

Collected as a two by two:

| | `C = 0` complete graph | `C = 1` stratified |
|---|---|---|
| **generating**, `E` and `K` (§9.2) | resolution, `35.62` and `3.07` sd | none, `0.00` and `0.02` sd |
| **transmitting**, `I` and `M` (§9.2) | none, `0.27` and `0.23` sd | none once §11.4 is removed |

### 11.3 Why `C = 0` kills the transmitting mechanisms, and why §9.3's remedy could not have worked

§9.2 classifies `I` and `M` as transmitting and sorting dispersion while creating
none, and §9.3 draws the consequence exactly right: their denominator in `A(X)`
is "pinned near zero **by the construction of the null arm**, not by anything
about the mechanism". The part §9.3 had wrong is where in the run the pinning
happens. It read the null arm as *starting* perfectly equal and prescribed a
repair to the opening. The arm *ends* perfectly equal from any opening:

| round | 0 | 1 | 2 | 3 | 5 | 10 | 299 |
|---|---|---|---|---|---|---|---|
| `C=0`, `same_marginal` | 0.2492 | 0.0900 | 0.0344 | 0.0159 | 0.0075 | 0.0071 | 0.0071 |
| `C=0`, `flat` | 0.0066 | 0.0072 | 0.0072 | 0.0074 | 0.0070 | 0.0072 | 0.0071 |
| `C=1` stratified | 0.8168 | 0.8499 | 0.8690 | 0.8814 | 0.8970 | 0.9112 | 0.9367 |

**The complete graph is an attractor at a Gini of about `0.0071` and reaches it
in five rounds from any opening**, with a half-life near one round. The `C = 1`
arm builds stratification over the same window, `0.8168` to `0.9367`. So no
repair to the opening can give a transmitting mechanism anything to transmit,
and this holds for any state variable the arm carries rather than for the
holdings vector specifically: whatever is symmetric across agents stays
symmetric under symmetric mixing.

### 11.4 The household conduit was the only thing that ever moved the `C = 1` arm

`POOLING_RULES` in `mechanisms.py` registers `pooling` as load-bearing and
reports that forcing pairs to form within a layer cuts the `I` and `M` effect on
the Gini from `−0.168` to `−0.006`. Run at `pooling = generation`, which settles
the household budget only at the generational event, the `C = 1` arm collapses
for everything:

| arm | competitor | eff/sd, `round` | eff/sd, `generation` | stock moved, `round` | stock moved, `generation` |
|---|---|---|---|---|---|
| `C=1` | inheritance | 36.45 | **0.03** | 44.15% | **0.16%** |
| `C=1` | mating | 32.10 | **0.15** | 41.55% | **0.22%** |
| `C=1` | education | 0.00 | 0.00 | 0.04% | 0.04% |
| `C=1` | capital | 0.02 | 0.02 | 0.35% | 0.35% |

The `C = 0` half of the table does not move by a digit, since `pooling` reaches
no code where the demographic layer does not fire. So **99.6% of what `I` and
`M` did on the stratified arm was the zero-cost transfer across the thermocline
that a household straddling it provides**, and none of it was the channel.

**The fence around `stock moved` earned itself inside an hour.** At the
registered `pooling = round` the ratio of that quantity across arms reads
`113` for inheritance and `112` for mating, two clean upstream results. At
`pooling = generation` the same arithmetic gives `0.41` and `0.59`, with `0.04`
for education and `1.6` for capital, which reads as damping. Promoting the
diagnostic to a criterion would have promoted the conduit. It stays a
diagnostic.

### 11.5 Repair one: a transmitting mechanism is measured on top of a source

**Registered here, not yet run.** For a transmitting mechanism, `A(X)` is
computed with a generating mechanism switched on in both terms and in both arms:

```
                 R(C=1, G+X) − R(C=1, G)
A(X | G)   =    -------------------------
                 R(C=0, G+X) − R(C=0, G)
```

for `X` in `{I, M}` and `G` in `{E, K}`. Generating mechanisms keep §4's form
against the null cell, since they create their own dispersion and need no
source. The classification is §9.2's, written before any of this stage's
measurements existed, so what is new here is the arithmetic and not the reading
of which mechanism is which.

**Both generators are used and both are reported.** Registering only the
stronger one would be choosing a base after seeing which base is stronger, which
is the move §5.1's demotions, §10.3's second refusal and §13.4 all exist to
prevent. `E` and `K` disagreeing about `A(I | G)` or `A(M | G)` is a reportable
result rather than a tie to be broken.

This repair addresses the **denominator**. It cannot help the `C = 1` arm,
because §11.2 shows neither generator has resolution there, so `R(C=1, G+X)`
and `R(C=1, X)` are the same cell to within the floor.

Cells required: `C` crossed with `{none, I, E, K, M, E+I, E+M, K+I, K+M}`,
eighteen in place of ten. All nine switch settings already exist on
`Switches`, and no parameter moves.

### 11.6 Repair two: the outcome is also computed on the production layer

**Registered here, not yet run.** §3's two measures are computed a second time
on the production layer alone, and the pair is reported beside the aggregate
pair rather than in place of it.

**The reason is a units mismatch that predates this stage's failure.** §6's
external anchors are household **income** Ginis over a whole population.
Greenwood and co-authors' `0.43` to `0.34` is one. A4's aggregate measure is the
Gini of an end-of-run claim balance over a population containing a twenty-node
financial layer that holds `99.7%` of the stock, and it sits at `0.937`. Any
agent-level mechanism operating among the other one hundred and eighty nodes
moves about `0.3%` of the stock, which is what §11.2's `C = 1` rows are made of.
Checklist item 2 asks whether the denominator is the same thing on both sides,
and it is not, and it was not before A4-3 failed.

This repair addresses the **numerator**. It does not help the `C = 0` arm, where
there is no layer boundary to remove.

### 11.7 What does not change

No parameter moves. `MechanismParams` keeps every value, including the four this
stage has now shown do not clear A4-3's floor, and the claim in its own
docstring that they were set to clear it is left standing as a falsified claim
rather than repaired by moving them. A4-3's `0.02` stands. A4-4's `1` and `1.25`
stand. `same_marginal` stands. `uniform_access` stands. §2's definition of what
`C = 0` means stands, and §11.3 is the reason it cannot be softened: the arm's
symmetry is the design and its consequence for transmitting mechanisms is a
property of that design rather than a defect in it.

### 11.8 The reading rule, and what would falsify the repairs

Every cell is read under §11.2's rule. An effect inside its control cell's seed
spread, or with a sign that moves across seeds, is **unreadable**, and a
criterion resting on it is reported unreadable rather than passed or failed.
`A(X)` is reported per seed as well as pooled, and no point value is quoted for
a competitor whose per-seed ratios do not share a sign, which is A3c's rule
imported through §10.4. Both arms' realised level is reported beside every
ratio, which is §10.4's ceiling obligation.

Registered outcomes that would falsify the repairs, and neither is excluded:

- **`I` and `M` still have no resolution on `C = 0` with `G` on.** Then a
  dispersion source is not the missing ingredient, and transmitting mechanisms
  are not measurable on this carrier at all. A4-4 is unreadable for them
  permanently rather than pending, and that goes to §8.
- **`E` and `K` still have no resolution on the `C = 1` production layer.** Then
  the layer boundary was not what was hiding them, the stratified arm is
  structurally unreadable for agent-level mechanisms, and A4-4 is unreadable for
  them permanently. That also goes to §8.

If both fire, A4's answer is that its discriminant cannot be computed on this
model, stated as a result rather than as a delay, in the same shape as B5's four
predictions whose sources do not exist.

### 11.9 Both repairs ran, and both of §11.8's falsification conditions fired

**Added 2026-08-13, after §11.5 to §11.8 were committed and after
`experiments/a4_causal_primitive.py` computed them.** Five seeds, three hundred
rounds, registered authority.

**What repair two achieved, which is real and is not enough.** Moving the
measure onto the production layer relieves the ceiling by a factor of six and a
half: `C1_none` sits at `0.59490` with `0.40510` of headroom where the aggregate
sits at `0.93673` with `0.06327`. `1/HHI` on that layer is `70.00` of one
hundred and eighty nodes, so the instrument is reading a live distribution
rather than a degenerate one. And the layer boundary was hiding something:
education's resolution on the `C = 1` arm goes from `0.00` to `0.73` control-cell
sd. **`0.73` is still inside the floor and its sign is not stable**, and capital
goes from `0.02` to `0.00`. §11.8's second condition therefore fires: the layer
boundary was not what was hiding them.

**What repair one achieved, which is smaller and does not survive the conduit
control.** At the registered `pooling = round` a generating base lifts the
transmitting mechanisms' `C = 0` denominator from `0.23` and `0.27` sd to
between `1.41` and `2.09`, a factor of six to eight, with three of sixteen cells
sign-stable and all three between `1.83` and `2.05`. At `pooling = generation`,
which is the setting that separates the channel from §11.4's household conduit,
the same cells run `0.02` to `2.37` sd and **not one of the sixteen is
sign-stable**. §11.8's first condition fires.

**Both fire, so §11.8's registered consequence applies**: A4's discriminant
cannot be computed on this model, and that is stated as a result rather than as
a delay.

One number carries it. With the conduit removed, **no competitor moves more than
`1.60%` of the stock in any cell of the design**, in either arm, on any base.
The largest is inheritance over education on `C = 0`. On the `C = 1` arm the
largest is `0.61%`.

**The verdicts.** A4-1 passes at `0.00711` against a ceiling of `0.02`. A4-2
passes at `+0.92962` against a floor of `0.05`, sign holding at five of five
seeds. A4-3 fails for all four competitors and the detail records why the
threshold is not moved. A4-4 is void on §7's ground and on §11.8's, separately
and sufficiently. A4-5 is void because A4-4 has no result for an ordering to
preserve, and what was run in its place is reported: the readable set moves by
two to twelve cells across the four order combinations while **A4-1, A4-2 and
A4-6 flip on none of them**, evaluated rather than asserted. A4-6 passes.

**Three of four live criteria pass, two are void.**

---

## 12. What A4 establishes, and what it hands forward

**Written 2026-08-13, after the verdicts.**

### 12.1 What each verdict means if the model is read as an economy

**A4-1, and it is the licence for everything else.** Two hundred identical
agents on a complete graph, with no inheritance, no education, no return
heterogeneity and no assortative mating, end three hundred rounds at a Gini of
`0.00711`. The model does not manufacture stratification. Had this failed,
nothing else in the stage would have meant anything, which is what §5 says and
is why it is first.

**A4-2, and it is the existence claim.** Turning on nothing but the access
structure takes the same economy to `0.93673`. No agent is more able than any
other, no agent inherits anything, and the outcome is near-total concentration.
**Who can transact with whom, on what terms, is sufficient on its own.** That is
A0 and A2 restated inside a design where four competing explanations were
available and switched off.

**A4-3, read as a measurement rather than as a verdict.** On a complete graph
none of the four standard explanations of wealth inequality does much:
inheritance `+0.00007`, education `+0.00932`, capital returns `+0.00080`,
assortative mating `−0.00006`, against a control of `0.00711`. Education does
the most and does about one part in a hundred of a Gini. Each was implemented in
its strongest exogenous form on purpose (§2), so this is those mechanisms at
their best case on a symmetric access structure. The registered floor calls that
a strawman implementation. §11.3 says why it is not: on a complete graph there
is nothing for a transmitting mechanism to transmit, and a generating one has
`1/HHI = 199.97` of two hundred to work against.

**A4-4, and its voiding is the stage's largest single result.** The
amplification ratio cannot be computed here, and §11 establishes that no choice
of scalar summary and no repair to the opening changes that. `A(X)` is a ratio
across two arms and no competitor is readable in both: transmitting mechanisms
die on the complete graph because it is an attractor, generating mechanisms die
on the stratified graph because twenty nodes hold `99.7%` of the stock. The
economic content of the failure is that **the two arms are not two settings of
one economy, they are two economies with different state**, and a ratio between
them measures the difference in state as much as the difference in mechanism.

**A4-5, and the part of it that did run.** The readable set moves across
orderings, by two to twelve cells of thirty-five, which says the marginal cells
are marginal. The three verdicts that do not pass through `A(X)` move on none of
the four combinations.

**A4-6, and it is the one that survives.** The matching rule reads holdings and
never the layer label; `mechanisms.py` guards that it cannot see
`self._is_layer1`. With connectivity on, the cross-layer pairing rate is
`0.1610` against a uniform-random reference of `0.1809`; with it off, `0.1780`,
which is within a fifth of a percentage point of random. C=1 is lower at five of
five seeds, and on §11.5's based cells the gap widens to `0.1645` against
`0.1835`.

**Connectivity does not prevent anyone from marrying anyone. It arranges the
holdings so that a rule which never mentions layers ends up respecting them.**
§5 calls that the sharpest available form of the upstream claim, and it is the
form that survived, because it reads a rate directly in each arm and takes no
ratio across them.

### 12.2 What A4 hands forward

**Established:** connectivity alone is sufficient for stratification (A4-2), and
sorting on a layer-blind rule is derived from connectivity rather than assumed
(A4-6).

**Not established, and not merely unproven:** that connectivity *amplifies* the
four competitors. The ratio that would say so is not computable on this carrier,
for reasons §11 measures rather than conjectures.

**`PROJECT_PLAN` §8.3's upstream diagram is not withdrawn and is not confirmed.**
§7's first falsification row fires on `A(X) ≈ 1` for all four competitors, which
would have made connectivity parallel. That is not what happened: `A(X)` has no
value at all. The diagram keeps A4-2 and A4-6 under it and loses the
amplification arrow, which was never measured.

### 12.3 Six limits that travel with every number in this stage

1. **The competitors are uncalibrated.** §8 says A4 cannot rank them and that
   stands. `MechanismParams`'s docstring claims the values were set to clear
   A4-3's floor; §11.2 falsifies that claim and §11.7 keeps the values.
2. **The state variable has no memory.** The model's only stock is a transaction
   balance whose half-life is about one round on the complete graph and five on
   the stratified one, while `generation_length` is forty. Every generational
   mechanism fires on a variable that has already forgotten.
3. **`PROJECT_PLAN` §16.2's injection does not repair that**, and
   `a4a_domain_probe.py --probe injection` measures why: at the registered
   `top_node` target the production layer's holdings history is bitwise
   identical with issuance on and off, and at `uniform` a credit of `9.000` per
   round leaves that layer at a flat `22.5` from round twenty to round three
   hundred. The stock is `credit / drain rate`, a fixed point rather than an
   accumulation.
4. **The household conduit is load-bearing and is not a robustness knob.**
   §11.4: it is `99.6%` of everything `I` and `M` do on the stratified arm.
   Every `C = 1` number in this stage should be read with the `pooling` value
   attached.
5. **The rounds-to-time mapping is still not pinned**, which §10.3's third
   obligation and `PROJECT_PLAN` §16.1's second step both require and which
   bites hardest on inheritance.
6. **A4-6's rate is measured on the matching rule's own output**, so it says
   what sorting the rule produces given the holdings it is handed. It does not
   say that real households sort this way, and §6's anchors are not close enough
   in construction to be compared in value.
