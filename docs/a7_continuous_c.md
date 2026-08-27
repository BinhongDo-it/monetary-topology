# A7: connectivity as a continuum

**Status: pre-registration, block 1 of 3. Nothing here scores anything yet.**
Sections 1 to 3 are the origin, the rulings that have to be in place before any
line of stage code is written, and the split into two legs. The criteria for
leg A live in section 4 and the criteria for leg B in section 5, and neither is
written at the time this block is filed. No number in `RESULTS.md` comes from
this file.

The availability check is `experiments/a7a_continuous_c.py`, already written and
already run (2026-08-14), and it holds the place `b5_orphan_availability.md` and
`b6_cuba_availability.md` hold for their stages: before the pre-registration,
not after.

---

## 1. What this stage is for, and what it can end

`docs/a4_causal_primitive.md` §11 closes A4 with `A(X)` void, and §12.1 calls
that voiding the stage's largest single result. The reason is not a threshold
and not the choice of scalar summary. `A(X)` is a ratio across two arms, and no
competitor is readable in both: transmitting mechanisms die on the complete
graph because it is an attractor, generating mechanisms die on the stratified
graph because twenty nodes hold `99.7%` of the stock. §12.1's own words for the
economic content are that **the two arms are not two settings of one economy,
they are two economies with different state**, so a ratio between them measures
the difference in state as much as the difference in mechanism.

A continuous connectivity parameter replaces that ratio with a slope along a
path. A slope does not require both endpoints to be live at once, and it does
not require any competitor to be readable at more than one point at a time.

There is a second thing only a continuum can do. `docs/a4_causal_primitive.md`
§10 asserts `C = 0 ⇒ H¹ ≡ 0` from a measured fact, that the centrality spread
under `uniform_access` is exactly zero. That makes `H¹` a switch. The framework's
own chain is stated as `C → H¹ → D`, with `H¹` an intermediate quantity, and in
that form it has never been measured anywhere in this repository. A continuum
turns `H¹` from a switch into a regressor.

**What A7 can end.** If the slope of the outcome on the construction parameter
is flat across the whole grid at every seed, the upstream diagram loses its
arrow on this carrier by measurement rather than by non-computability, which is
a strictly better outcome than A4-4's void whichever way it comes out.

**What A7 cannot end.** It cannot rank the four competitors. §12.3's first limit
stands: they are uncalibrated, and nothing in this stage calibrates them.

---

## 2. What the availability check settled, and the rulings that precede any run

### 2.1 The construction parameter runs against `C`, and it gets its own letter

A4's convention is fixed and is not being changed here: `C = 1` is the
stratified arm, `C = 0` is `uniform_access`, and `mechanisms.py` line 281 spells
it `uniform_access = not switches.connectivity`.

The availability check's grid parameter runs the other way. In
`a7a_continuous_c.py`, `c = 0` returns `build_graph(spec)` bit for bit and
`c = 1` returns the complete graph, so the script's `c` is `1 − C` in spirit and
identical to it at neither endpoint by name.

**Ruling.** The stage's parameter is `s`, the shortcut rate, with `s = 0`
stratified and `s = 1` complete. `C` is never written for a continuum quantity
anywhere in this stage. The availability check currently spells it `c`; the
implementation renames that symbol to `s` and does not delete the file or any
part of it.

The reason for a ruling rather than a note: every sentence of the form
"connectivity rises" is ambiguous under two coordinates that run opposite ways,
and this project has already lost a round to a variable that moved without a
name of its own (A6-9's `R* = λ`).

### 2.2 `uniform_access` is five collapses, and only one of them is the mechanism

Reading `network.py`, the flag collapses five things, each with its own comment
in the source saying the collapse follows from a complete graph having no
layers:

| # | What collapses | Site | Stratified rule | Under `uniform_access` |
|---|---|---|---|---|
| 1 | adjacency | `build_graph`, ~line 427 | sampled stratified graph, seeded | `1 - eye(n)`, no seed enters |
| 2 | payroll incidence | ~line 687 | payers are the intermediate, or the top quarter of financial nodes by scaffold in-degree; receivers are a permuted half of households | everyone pays, everyone receives |
| 3 | discretionary routing | ~line 726 | `clip(adjacency - wage_mask, 0, 1)` | `adjacency.copy()`, the subtraction is skipped |
| 4 | spending propensities | ~line 757 | two values assigned by layer | one claim-weighted value |
| 5 | opening holdings | ~line 785 | layer split by `layer1_initial_share`, in-degree weighted within layer | flat, or §9.3's permuted marginal |

**Ruling: `s` moves the adjacency and nothing else.** Rules 2 to 5 are held at
their stratified definitions across the whole grid, and the routing always
subtracts. `COMMIT_MSG_9.txt` records the opportunity in one line: the binary
switch changes the adjacency and the wage distribution together and declines to
separate them, and a continuum can hold the other four fixed and move one thing.

### 2.3 Two of the four held rules still move, because they read the graph

This is the part that would be false if it were left as "the other four are
fixed", and it has to be in the file before anything runs.

Rule 2 selects payers by `build_graph(spec).sum(axis=0)`, an in-degree. Rule 5
weights within-layer holdings by in-degree. Both are functions of the adjacency,
so both have outputs that move with `s` even though their rules do not. Rules 3
and 4 are genuinely fixed: the subtraction is unconditional and the propensities
are assigned by layer, and layers stay defined because `uniform_access` is never
switched on anywhere in this stage.

**Ruling: the rules run, the index sets are not frozen.** At each `s` the payer
set and the opening vector are whatever the rule returns at that `s`.

The alternative, freezing the payer and receiver sets at their `s = 0` values,
is an exact defect this repository names: **a quantity that reality assigns by a
measured property written in code as a fixed list of node indices.** That defect has already been found four times in this repository (A6's
tax base, A6's rebate side, A3's rent liability, A3-6's two points).

**Registered diagnostic, reported and never scored.** At every grid point,
report the Jaccard overlap of the payer set and of the receiver set against
their `s = 0` values, and the rank correlation of the opening holdings vector
against its `s = 0` value. If the payer set has turned over completely by the
second grid point, the stage is moving two things and the reading has to say so.

### 2.4 The `s = 1` endpoint is not A4's `C = 0` arm, and it differs in five of six ways

The availability check states this for the routing alone. Under §2.2's ruling it
is broader, so the full statement goes here:

| | at `s = 1` | A4's `C = 0` |
|---|---|---|
| adjacency | complete | complete, identical |
| payroll payers | first quarter of financial nodes, by index, since in-degree ties everywhere | everyone |
| payroll receivers | permuted half of households | everyone |
| routing | subtracts the wage mask | does not subtract |
| propensities | two values by layer | one claim-weighted value |
| opening holdings | layer split, flat within layer | flat overall, or permuted marginal |

The routing row is the one that could not have gone the other way. The
subtraction is skipped at the endpoint only because there the payroll mask is
the whole matrix, so subtracting would empty the discretionary graph and the
null arm would be a payroll wash where holdings never move: `network.py`'s own
comment calls that a dead economy reporting clean numbers, and
`test_uniform_access_leaves_the_discretionary_graph_alive` guards it. At any
interior `s` the mask is partial and the subtraction is well defined.

**Ruling: no number produced at `s = 1` is compared to any published `C = 0`
number, in this stage or in any writing that cites it.** The endpoint is a
complete graph carrying layered payroll, layered propensities and a layered
opening, and A4's `C = 0` arm is a different economy. A7's readings are slopes
along its own path.

**The fork that was available, recorded so it is not rediscovered.** A continuum
could instead interpolate all five collapses together, which buys comparability
with A4's published `C = 0` numbers and pays for it by confounding five things
again, which is the condition A7 exists to escape. It is not taken. If a later
session wants it, it is a separate leg with its own registration and it does not
reuse anything below.

### 2.5 Read the standard deviation, not the range

The check's own instruction. The range is set by the least central node and sits
at `1.000` through the first two grid points, so it is flat where the interesting
region is. Every criterion below that mentions dispersion means the standard
deviation of normalised in-degree centrality.

### 2.6 The continuum is constructible, and this is the check's result

Interpolation is by edge addition: `A(s)` is the stratified adjacency with every
remaining ordered pair present independently with probability `s`, drawn on a
fresh stream (`_SHORTCUT_OFFSET = 20_749`) so the added edges cannot correlate
with the stratified graph's own draw, the payroll receiver order (`seed + 4241`)
or the opening permutation (`seed + 9301`). Edges are monotone in `s` by
construction, and both endpoints are exact rather than limits.

What the check found, at five seeds:

- centrality standard deviation goes from `0.161` to `0.000` monotonically **in
  the five-seed mean**, with no cliff;
- the gap between the two layers' mean positions closes along with it rather
  than surviving it, so this is a continuum in structure and not only in
  dispersion;
- `s = 0` matches `build_graph(spec)` bit for bit and `s = 1` matches what
  `uniform_access` returns, at every seed.

Why this had to be checked before the stage was written: `terms = base (1 + κ (1 − c_i))`,
so the terms dispersion the loop sum is built from is proportional to the
centrality dispersion. Had that dispersion sat flat and then fallen off a cliff,
the sweep would have been a two-point comparison wearing a grid.

**Monotone in the mean, and not at every seed. Measured 2026-08-15.** The check
prints five-seed means and the sentence above is a statement about those means.
Per seed the dispersion is monotone at **eighteen of twenty** seeds. The two
exceptions rise by at most `7.6e-4`, which is `0.62%` of that seed's own `s = 0`
value, and every violation sits at the single grid step `0.01 → 0.02`, the
densest part of the low-`s` region. Both the five-seed and the twenty-seed means
are monotone with no exception.

This is recorded here because §4.4's A7-A-5 was filed as a per-seed claim about a
quantity proportional to this one, and it would have failed for a reason with no
mechanism in it. **The correction is to the guard, not to a result**, and it was
made before any stage code produced a number. `tests/test_a7_shortcut_rate.py`
asserts the mean form exactly and the per-seed form within `1e-3`, a tolerance
that is a measurement rather than a theoretical bound.

**Provenance flag, and one obligation.** The check writes no file, so the three
figures above are quoted from `COMMIT_MSG_9.txt`'s record of that run and are not
reproducible from the repository as it stands. The stage's first commit re-runs
the check and pastes its table into this section under a dated heading. Until
that happens, no criterion below may cite `0.161` or `0.000` as a registered
constant.

**Obligation discharged, 2026-08-16.** `experiments/a7a_continuous_c.py`,
five seeds, means:

| `s` | edges | mean degree | centrality range | centrality sd | layer gap |
|---|---|---|---|---|---|
| 0.00 | 1028 | 5.14 | 1.000000 | **0.160664** | 0.394149 |
| 0.01 | 1411 | 7.06 | 1.000000 | 0.151740 | 0.369881 |
| 0.02 | 1791 | 8.96 | 0.993376 | 0.150086 | 0.364558 |
| 0.05 | 2955 | 14.77 | 0.933253 | 0.138640 | 0.326750 |
| 0.10 | 4880 | 24.40 | 0.858040 | 0.125483 | 0.274499 |
| 0.15 | 6811 | 34.06 | 0.772109 | 0.115946 | 0.235391 |
| 0.20 | 8776 | 43.88 | 0.696534 | 0.104650 | 0.202950 |
| 0.30 | 12634 | 63.17 | 0.576690 | 0.084915 | 0.141650 |
| 0.40 | 16492 | 82.46 | 0.491478 | 0.072559 | 0.106844 |
| 0.50 | 20374 | 101.87 | 0.382842 | 0.062822 | 0.078613 |
| 0.60 | 24264 | 121.32 | 0.305162 | 0.053575 | 0.056161 |
| 0.70 | 28124 | 140.62 | 0.239650 | 0.044160 | 0.039606 |
| 0.80 | 32012 | 160.06 | 0.193620 | 0.033604 | 0.024136 |
| 0.90 | 35894 | 179.47 | 0.123085 | 0.023182 | 0.015335 |
| 0.95 | 37850 | 189.25 | 0.088229 | 0.016084 | 0.005740 |
| 0.99 | 39413 | 197.06 | 0.033166 | 0.007088 | 0.000151 |
| 1.00 | 39800 | 199.00 | 0.000000 | **0.000000** | 0.000000 |

Endpoints exact at all five seeds, `c = 0` matching `build_graph(spec)` bit for
bit and `c = 1` matching what `uniform_access` returns. The sd column is
strictly decreasing with no exception, which is the mean form §2.6 corrected to.
The range column sits at `1.000000` through the first two rows, which is why
§2.5 forbids reading it.

**A units note that will otherwise read as a defect.** This table is
**five-seed means**. §6 and §11 quote graph columns at **seed zero**, because the
row builder takes them from `NetworkSpec(seed=seeds.start)`. So `s = 0` appears
here as `1028` edges and `0.160664`, and there as `1039` and `0.157337`. Both are
correct and neither is a discrepancy.

---

## 3. Two legs, and why they are two rather than one

`H¹` is not computable on A4's carrier, and this is structural rather than a
matter of effort. The loop sum is defined on the `terms` matrix, which lives on
`A3Model`. `A4Model` subclasses `Network` and has no edge field at all
(`asset.py` line 857 against `mechanisms.py` line 309), so there is no holonomy
to compute on it. The availability check names this gap and declines to choose
between the two stages it implies.

**Ruling, 2026-08-15: both, in one registration, as two legs run in order.**
Sections 2.1 to 2.6 are shared by both legs and are settled once. The legs do
not share an estimator, a criterion or an outcome measure.

### 3.1 A7-A, on the A3 carrier: `s → H¹ → D`

Measures the chain the framework states, with `H¹` as a regressor rather than a
switch. No competitors are in this leg, because `A3Model` has none. Its
criteria are section 4, unwritten at filing.

Implementation note carried forward: `A3Model` takes its adjacency from
`Network.__init__`, which calls `build_graph(spec)`, so `s` enters through a new
`NetworkSpec` field rather than through a subclass. **That field defaults to
`0.0` and the default must reproduce every existing A3 number bitwise, verified
by running rather than by argument.**

### 3.2 A7-B, on the A4 carrier: four competitors, slope in place of the ratio

Measures what A4-4 could not: whether connectivity amplifies the four
competitors. `H¹` does not appear in this leg at all, and the leg's write-up may
not claim it as an intermediate. Its criteria are section 5, unwritten at
filing.

### 3.3 Order, and the one thing that could stop leg B

A7-A first. It is the leg whose quantity has never been measured, and it is the
leg whose carrier already has the machinery.

A7-B inherits §12.3's second limit unchanged: the model's only stock is a
transaction balance whose half-life is about one round on the complete graph and
five on the stratified one, while `generation_length` is forty, so every
generational mechanism fires on a variable that has already forgotten. §12.3's
third limit records that `PROJECT_PLAN` §16.2's injection does not repair it, and
measures why: the stock is `credit / drain rate`, a fixed point rather than an
accumulation. **If the slope in leg B is flat, that limit is a live alternative
explanation for the flatness and the leg's reading must carry it.** Section 5
has to register a discriminant between the two before leg B runs, or register
that it cannot and say what the leg is then worth.

---

## 4. Pre-registered criteria, leg A7-A

### 4.1 What leg A actually tests, and the one link that is not a test

The chain is `s → H¹ → D`, and the two links have different standing.

**`s → H¹` is a construction identity and gets no criterion.** `terms = base (1 + κ (1 − c_i))`
and `c_i` is normalised in-degree, so flattening the graph flattens the terms
matrix, which flattens the square sums the holonomy is made of. Registering that
as a finding would repeat exactly what §5.1 demoted A3-3 for: an identity read
back at machine precision and tabled as a result. It is reported as an
assertion with a guard, and §4.4 gives it no row.

**`H¹ → D` is the content, and the reason it is worth running again is that
A3-8 already removed the holonomy once by a different route.** A3-8 zeroed
`κ_pay`, a parameter intervention on a fixed graph, and found the divergence
collapsed from `+23.267` to `+1.409`. A7-A removes the same object by changing
the topology instead, with every κ left alone. **Two independent routes to the
same zero is a stronger identification than either route alone**, and a
divergence that survives the structural route while collapsing on the parameter
route would say that something co-moving with `κ_pay` was doing the work.

**The confound that shapes every criterion below.** At `s = 1` the graph is
complete, and A4-1 measured that the complete graph is an attractor: two hundred
identical agents end three hundred rounds at a Gini of `0.00711`. So `D → 0` at
the far endpoint is overdetermined and carries no information about holonomy.
**No criterion below is of the form "D falls as s rises" read across the whole
grid.** The content lives in the interior and in the placebo of §4.3.

### 4.2 The estimator, and the ruling on which population carries it

`D` is A3-8's fourth-version gap, unchanged: `delta = (net_worth − baseline) / max(claims_0, 1e-12)`,
each node paired against itself in the separately built null, split into a
central and a peripheral bin on centrality with width `centrality_bins`, and
`D = mean(delta[central]) − mean(delta[peripheral])`. The three earlier versions
and why each failed stay where they are in `a3c_load_bearing.py`'s docstring.

`H¹` is the mean absolute `loop_sum(terms, a, b, tier, periods)` over the pairs
in the measured population at the registered tier, with `periods` set to the
same window `D` is read on.

**The population ruling, and it is the population error in a new dress.** A3-8
intersects the agents completing a round trip in every cell, which
`MEASUREMENT.md` rule 5 exists for. A grid adds a second axis, and intersecting
across it as well is not the same decision.

- **`D_fixed(s)`, the scored estimator**: the population is the intersection
  across every cell **and** every grid point. Composition is then constant along
  the grid, which is what a slope requires.
- **`D_reach(s)`, reported and never scored**: the within-`s` intersection, so
  the set moves with the treatment. It exists to show what the carrier reaches
  at each `s` and may not be quoted as a slope.

**And the arithmetic consequence has to be stated before the run rather than
discovered from it.** `D_fixed`'s population is a subset of the `s = 0`
population, so it is at most A3-8's `41.6` shared nodes and it sits inside the
band §5.3 measured, the top eighth of the production layer by centrality.
**`D_fixed` therefore cannot clear A3-8′'s stated precondition**, which asks for
a carrier whose measured population is not one eighth of one layer. Any
quotation of `D_fixed` carries that band with it, on the same terms §5.3
imposes on A3-8 itself. Whether the carrier's reach improves at all is a
separate question and it is A7-A-1's.

### 4.3 Guards and arms

**G1. The default reproduces A3 bitwise.** The new `NetworkSpec` field defaults
to `0.0` and every existing A3 number must come back bit for bit, verified by
running and comparing rather than by argument (a rule that has already held four
times: the ratchet's `λ = 0`, the tax base's
`layer`, the rebate side's `layer`, `centrality_bins = 3`).

**G2. The obstruction stays all squares, asserted in code at every grid point.**
`s` moves the payment adjacency, which sets `centrality`, which sets `terms`. It
does not touch `tier_positions`, which is a star, so `b₁(G) = 0` holds along the
whole grid and by `b1_theorem.md` §5 the entire obstruction is squares at every
point, with `gate_spread` contributing no holonomy anywhere. This is what
licenses reading `H¹` off the square sums alone, and it is asserted rather than
assumed because it is the hinge the whole leg hangs from.

**G3. Inert-cell detection, reusing the sweep's own.** `a3c_load_bearing.sweep`
already flags a grid cell whose four gaps are bit-identical to the registered
point and names it in the summary. A7-A inherits it unchanged
(`centrality_bins` had a field, validation and
documentation and no line of code reading it, and the grid swept it twice and
reported clean).

**G4. Every grid row carries its control variables in its own units.** Realised
edge count, mean degree, centrality standard deviation, layer gap, participating
count, and the §2.3 churn diagnostics, all on the same row as the gap
(A6-9 swept `λ` at fixed `R` while `R* = λ`, and
the second thing moving had no variable name until A6-21).

**A1. The placebo arm, which is what separates density from dispersion.** Edge
addition does two things at once: it raises mean degree and it lowers centrality
dispersion. The placebo adds the **same number of edges** at each grid point and
targets them in proportion to existing in-degree, so mean degree tracks the
uniform arm while dispersion is held near its `s = 0` value. If `D` responds to
density, both arms fall together. If `D` responds to dispersion, only the
uniform arm falls.

The realised centrality standard deviation is reported for both arms on every
row. The tolerance within which the placebo's dispersion counts as held is an
**arbitrary calibration value with no theoretical provenance**, so per
methodological discipline 5 it may gate the arm's readability and may not serve
as a falsification basis: an arm whose dispersion drifts outside it is **void**
rather than negative.

### 4.4 The criteria

Twenty seeds, three hundred rounds, the availability check's grid. Twenty rather
than A3's registered five because §5.3 measured five to be insufficient for sign
stability on this exact estimator, and the gate arm's range widened rather than
narrowed on the way from five to twenty.

| # | claim | what is registered | scored |
|---|---|---|---|
| **A7-A-1** | the structural route changes the carrier's reach | peripheral-tercile participation is `0.0` at `s = 0` at twenty seeds, already measured in §5.3, and becomes **strictly positive** at some grid point `s < 1` | yes, direction only |
| **A7-A-2** | the second route reaches the same zero | on `D_fixed`, the Spearman rank correlation of the gap against `s` over the **interior** grid is **negative**, same sign at every seed | yes, direction only |
| **A7-A-3** | it is dispersion and not density | at matched added-edge count, the uniform arm's fall in `D_fixed` exceeds the placebo arm's in magnitude, same sign at every seed | yes, ordering only |
| **A7-A-4** | A3-8′, scored for the first time | at every grid point whose cell state is readable: the loop-sum-only cell is same-sign across all seeds **and** its gap exceeds the gate-only cell's. Shares reported, never gated | yes |
| **A7-A-5** | the identity holds along the grid | mean absolute loop sum falls monotonically in `s` **in the seed mean**, and per seed within the tolerance §2.6 measured on the dispersion it is proportional to, with every violation named | **no**, assertion with a guard, §4.1 |
| **A7-A-6** | reach, described | `D_reach(s)`, the within-`s` participating count, and the §2.3 churn diagnostics | **no**, reported |

**Nothing in this table contains a number this repository invented.** `0.0` in
A7-A-1 is a measured value from §5.3's twenty-seed run, and every other clause
is a sign, an ordering or a rank correlation.

**A7-A-4's readability clause is not an escape hatch.** As `s` rises the terms
dispersion falls, so at high `s` every cell approaches zero together and the
ordering stops being readable for a reason the leg itself predicts. Points where
all four cells are indistinguishable from zero are reported as such and counted
in neither direction. The clause is registered here rather than applied later,
and the count of such points is reported with the criterion.

### 4.5 Falsification

**A7-A-1 fails, participation stays exactly zero below `s = 1` at every seed.**
Then adding edges does not fix the scope problem, every A3-family divergence
reading stays confined to the top eighth of the production layer, and the route
"build a better carrier by densifying the graph" is closed. **This is a
reportable negative and it retires a route rather than a claim.**

**A7-A-2 fails, the interior slope is flat or positive at a majority of seeds.**
Then the structural route does not reproduce what the parameter route found, and
A3-8's `+23.267 → +1.409` is put back in question: something co-moving with
`κ_pay` becomes the live alternative and this leg does not identify it.

**A7-A-3 fails, the placebo falls as far as the uniform arm.** Then `D` on this
carrier responds to density, the structural route measures the wrong thing, and
A7-A-2 passing would not be evidence for the chain. **A7-A-3 is prior to A7-A-2
in reading order**, and A7-A-2 may not be quoted without A7-A-3's outcome
attached.

**A7-A-4 fails.** A3-8′ was registered forward in §5.3 and is scored here for
the first time. A failure is recorded against A3-8′ and not against A3-8, whose
state stays `void` for the reason already on record.

### 4.6 What leg A cannot establish

1. **It has no competitors in it.** `A3Model` has none, so nothing here speaks
   to whether connectivity amplifies inheritance, education, capital returns or
   assortative mating. That is leg B and leg B has no `H¹`.
2. **`D_fixed`'s population is the top eighth of the production layer** (§4.2),
   whatever A7-A-1 finds about reach.
3. **The far endpoint is uninformative** (§4.1) and the interior grid is where
   every scored claim lives.
4. **Nothing here is a measurement of the world.** §6.6's boundary stands: this
   supports statements about a running stratified economy in simulation, and the
   external side is B2 and B3.
5. **A3-4's `3.05%` is not re-earned here.** The identity between the realised
   terms differential and the loop sum is not re-tested along the grid, and no
   A7 number may be quoted as evidence for it.

### 4.7 Compute, and the order this runs in

The sweep re-runs the whole four-cell factorial and its separately built null at
every grid point, so seventeen points times five model builds times twenty seeds
is seventeen hundred three-hundred-round runs per arm, and there are two arms.

**Before the grid runs, a timing probe at one interior grid point at one seed,
reported.** If the full grid does not fit in a sitting, the registered
contraction is to drop grid points from the dense low-`s` region inward,
recording which were dropped, and never to drop seeds: §5.3 is the record of
what five seeds cost on this exact estimator.

This runs locally. Nothing in leg A is executed in the sandbox.

## 5. Pre-registered criteria, leg A7-B

### 5.1 The quantity that replaces `A(X)`

For each competitor `X`, define the effect at a grid point,

```
d(X, s)  =  R(s, X on)  −  R(s, X off)
```

and leg B's quantity is the slope of `d(X, s)` in `s`, taken within seed. No
ratio is ever formed across two grid points, which is the one thing §12.1 says
A4-4 could not survive.

**Registered outcome: `R = log(1/HHI)`, the log effective number of holders.**
The Gini is computed and reported beside it on every row and is not primary. §3
provides for the two measures disagreeing and calls the disagreement the
finding, and **that clause has already fired**: §11.3 measured `A(E) = 0.00` and
`A(K) = 0.06` on the Gini against `A(K) = 5.31` on `log(1/HHI)`, the second in
the registered direction and the first two produced by the bound. Both measures
travel together in every quotation from this leg.

The production-layer-only pair from §11.6 is computed and reported as well, on
the same rows, for the units reason recorded there.

### 5.2 Which competitors are readable, decided before the run

**Both pairs are confounded along this grid, in opposite directions, and both
confounds are already measured in the repository.**

**`I` and `M` read a stock that stops existing.** `Switches.demography_active`
is `inheritance or mating`, so the split is an object the code already names
rather than one invented here. §9's retention table:

| arm | node | half-life | left after 10 rounds | left after 40, one generation |
|---|---|---|---|---|
| `C = 1` stratified | richest | 2 rounds | 32.2% | **28.06%** |
| `C = 1` stratified | median | 5 rounds | 0.2% | 0.00% |
| `C = 0` uniform | richest | 1 round | 0.0% | **0.00%** |
| `C = 0` uniform | median | 1 round | 0.0% | 0.00% |

What a generational mechanism has left to transmit runs from `23.72%` to
`0.00%` along this axis, **in the same direction as the amplification the leg
would be claiming**. A declining slope on `I` or `M` is manufactured by the
carrier's own decay whatever connectivity does.

> **This corrects §3.3 as filed.** §3.3 registers the memory limit as a live
> alternative explanation for a *flat* slope. The table says it is an
> alternative explanation for a *declining* slope, which is the predicted
> direction, so the exposure is a false positive rather than a false negative.
> §3.3's text stands and this is the correction, dated in the changelog.

**The table above was corrected 2026-08-16 and the correction is A7-B's first
act.** Section 9 had no producer in the repository, and `experiments/a7b_probes.py`
is now that instrument. Its numbers are **seed zero**: at twenty seeds the
richest node keeps `+0.2372` with a range of `[+0.1957, +0.2863]` rather than
`+0.2806`, the half-life of `2` reproduces at twenty of twenty seeds, and the
median row reproduces as zero while its stated half-life of `5` does not. Full
record in `a4_causal_primitive.md` section 13.

**The ruling is unaffected.** `+0.2372` to `0.00` carries exactly what `+0.2806`
to `0.00` carried, and the direction that makes `I` and `M` unreadable is the
same. One thing is sharper: the surviving quarter belongs to a **financial-layer**
node at every seed and the median **production-layer** node keeps nothing, so
what a generational mechanism has to transmit exists only upstairs, in a
twenty-node layer, while leg B's outcome is a whole-population concentration
measure.

Carried with them regardless: §11.4 measured that `99.6%` of what `I` and `M`
did on the stratified arm was the zero-cost transfer across the thermocline that
a straddling household provides, and none of it was the channel. **`pooling`
travels with every `I` and `M` number in this leg.**

**`E` and `K` are compressed by a bound.** §11.3: the control cell reaches a
Gini of `0.935`, so a competitor under `C = 1` has `0.065` of room while the same
competitor under `C = 0` has `0.99`. The room therefore moves by a factor near
fifteen along the axis the slope is taken over, and §11.3 measured that this
compression alone is the difference between `A(K) = 0.06` and `A(K) = 5.31`.

`log(1/HHI)` reduces the exposure and does not remove it. Competitors push the
effective holder count **down**, away from the upper bound, and the distance to
the floor runs from about `log 14` at `s = 0` to about `log 200` at `s = 1`, a
factor near two against the Gini's fifteen. §5.3's second probe measures it
rather than assuming it is small enough.

**Ruling.** `E` and `K` are scored, on `log(1/HHI)`, over the region §5.3's
probes declare readable. `I` and `M` are reported with the retention curve and
the `pooling` value attached and are **not scored for direction**.

### 5.3 Two probes, and they run before anything is scored

**P1, retention.** At every grid point and seed, the fraction of a marked unit
surviving `generation_length` rounds, by node rank. Reported on every row. `I`
and `M` become scoreable over any contiguous region where this curve is flat
within a registered band, and over no other region.

**P2, room.** At every grid point and seed, the control-arm level and the
distance to the bound, on the Gini, on `log(1/HHI)`, and on the
production-layer-only pair. Reported on every row.

**The trigger, registered in advance.** If the room on `log(1/HHI)` moves
outside a registered band across the scoring region, the slope in `s` is not
separable from the slope in room on a one-dimensional grid, and leg B takes one
of two exits, chosen before seeing any `d`:

1. run a coarse second axis, `s` crossed with `layer1_initial_share` (registered
   at `0.679`), which moves the opening concentration and therefore the room
   through a channel that is not the graph, and report the partial slope in `s`
   at held room;
2. or record leg B as **not identified** on this carrier and score nothing.

**Exit 2 is A4-4's void wearing a grid and must be labelled that way** rather
than as a negative result about connectivity.

Both bands are **arbitrary calibration values with no theoretical provenance**.
Per methodological discipline 5 they gate readability and may not serve as a
falsification basis.

### 5.4 Cells, and what is not run

`{none, E, K, E+K}` crossed with the grid. A4's `E+I`, `E+M`, `K+I`, `K+M` exist
for §11.5's repair, which measures a transmitting mechanism on top of a
generating source; with `I` and `M` unscored they are diagnostics and are not
put on the grid. `pooling` runs at the registered `round`, with `generation` run
at the two endpoints only, as §11.4's fence.

Twenty seeds, three hundred rounds, the same grid as leg A, the same guards G1
to G4 from §4.3.

### 5.5 The criteria

| # | claim | what is registered | scored |
|---|---|---|---|
| **A7-B-1** | connectivity amplifies capital returns | `|d(K, s)|` on `log(1/HHI)` decreases in `s` over the scoring region, with `sign(d)` stable, same direction at every seed | yes, direction only |
| **A7-B-2** | the same for education | as A7-B-1 for `E`, scored only where `d(E, s)` clears the seed noise floor at the low-`s` end | yes, conditional |
| **A7-B-3** | the two measures are read together | if the Gini and `log(1/HHI)` disagree in the sign of the slope, that is reported as the finding per §3 and neither is quoted alone | yes, reporting rule |
| **A7-B-4** | the probes | P1 and P2 on every row, and the §5.3 trigger evaluated before any `d` is read | **no**, gates |
| **A7-B-5** | the unreadable pair | `d(I, s)` and `d(M, s)` with retention and `pooling` attached | **no**, reported |

**No number in this table was invented here.** Every figure quoted in §5.2 is a
measurement already in `a4_causal_primitive.md`, and every clause above is a
sign, an ordering or a monotone direction.

### 5.6 Falsification

**A7-B-1 fails, the slope is flat or reversed at a majority of seeds.** Then
connectivity does not amplify capital returns on this carrier, **measured rather
than non-computable**, which is the thing A4-4 could not deliver. That is a real
negative against `PROJECT_PLAN` §8.3's amplification arrow, and §12.2 already
records that the arrow was never measured, so this would be the first reading of
it in either direction.

**The room trigger fires and exit 2 is taken.** Leg B scores nothing and is
recorded as not identified. It may not be written up as evidence that
connectivity does not amplify.

**P1 shows the retention curve is flat across the interior** and `I` or `M` then
score against direction. That reopens §11.3's re-sequencing question, and it is
recorded against A7-B and not against A4.

### 5.7 What leg B cannot establish

1. **No `H¹` anywhere in it.** `A4Model` has no edge field, so this leg may not
   claim an intermediate, and nothing in it supports or weakens leg A.
2. **It cannot rank the competitors.** §8 and §12.3's first limit stand: they are
   uncalibrated and nothing here calibrates them.
3. **`I` and `M` are unreadable on this carrier**, which is a statement about the
   carrier and repeats §11.3's own finding rather than adding to it.
4. **Every `C = 1`-like number carries `pooling`** (§12.3's fourth limit).
5. **The rounds-to-time mapping is still not pinned** (§12.3's fifth limit), and
   it bites hardest on exactly the two mechanisms this leg declines to score.

### 5.8 Order

P1, then P2, then the §5.3 trigger, then the grid. The trigger is evaluated on
the probes alone, before any `d(X, s)` is computed, so the choice between exit 1
and exit 2 cannot be made after seeing the result it decides how to read.

This runs locally. Nothing in leg B is executed in the sandbox.

## 6. Leg A7-A: the run, 2026-08-15

Twenty seeds, three hundred rounds, the registered grid, both arms. The `s = 0`
row reproduces `a3_asset_channel.md` §5.3's twenty-seed re-read to the digit
(`+18.9854` / `+22.2119` / `−0.2997`, paired `41.6`, peripheral tercile `0.0`),
so this is the same instrument at a different graph.

### 6.1 A7-A-1, reach: **PASS**, and the shape is the content

Peripheral-tercile participation, uniform arm: `0.00` at every seed from `s = 0`
through `s = 0.7`, then `0.25` at `0.8`, `5.45` at `0.9`, `18.30` at `0.95`,
`25.90` at `0.99`, `60.00` at `1.0`. Strictly positive at `s = 0.8 < 1`, so the
registered clause is met.

**The reading that has to travel with it.** At `s = 0.8` the graph carries
`80.5%` of the complete graph's edges and the layer gap has fallen from `0.394`
to `0.030`, which is `92%` closed. **There is no interior region with both a
stratified structure and a peripheral population.** The placebo settles the
mechanism: with the same edges aimed at already-central targets, peripheral
participation is still `0.15` at `s = 0.9` and only reaches `12.30` at `0.95`.
Edges pointed at the centre never let the periphery in.

So the carrier gains a measurable population by ceasing to be stratified. That
is a sharper statement of §5.3's scope problem rather than a repair of it.

### 6.2 A7-A-2: the registered shape is wrong

The registered claim is a negative rank correlation over the interior. What the
grid shows is a **step at the first grid point and then flat**: `both` goes
`+18.9854` at `s = 0` to `−0.1157` at `s = 0.01`, and stays inside `[−0.4, +1.4]`
from there to `s = 0.9`. A rank correlation would return a negative number and
would read as a gradient, which the data do not contain.

Recorded as an actual-result-disagrees-with-registration item under the project's
engineering rule 8. Not repaired.

This also fixes the scope of §2.6's "no cliff": **there is no cliff in the
dispersion and there is one in the measured quantity.** The availability check
asked whether the construction parameter carries a continuum. It does. It did
not ask whether the outcome is a continuous function of it, and the outcome is
not.

### 6.3 A7-A-3, the placebo: satisfied in letter, and the pass is not evidence

At `s = 0.01`, matched at `1389` edges in both arms:

| | edges | sd / sd(s=0) | layer gap | `both` | fall |
|---|---|---|---|---|---|
| `s = 0` | 1039 | 1.000 | 0.394 | **+18.9854** | — |
| uniform | 1389 | **0.972** | **0.385** | −0.1157 | 19.101 |
| preferential | 1389 | **1.053** | **0.421** | +0.6615 | 18.324 |

`19.101 > 18.324`, so the registered inequality holds, by `4%`. It holds again at
`s = 0.02`, by `2%`.

**The criterion cannot separate "the placebo falls slightly less" from "the
placebo does not fall".** Both arms lose `97%` to `99%`, and an unnormalised
difference of falls returns a small correctly-signed margin whenever both
collapse. That is a defect in the criterion's shape, of the same kind as A6-1's
scope defect, and it is **recorded rather than repaired**.

**What actually settles it needs no tolerance.** The two arms moved the
dispersion in **opposite directions** at matched edge count, `0.972` against
`1.053`, and moved the layer gap in opposite directions, `0.385` against `0.421`,
and the gap collapsed in both. If `D` were a function of dispersion with an
elasticity large enough for a `2.8%` fall to remove `98%`, then the arm that
raised dispersion by `5.3%` would have raised `D`. It did not.

**Everything else the pre-registration named as a confound is held or moves the
wrong way.** Preferential arm at `s = 0.01` against `s = 0`: payer Jaccard
`1.000`, opening rank correlation `+0.972`, paired population `43.0` against
`41.6`, production participation `25.0` against `24.6`. Population and
participation **rise** while the gap collapses.

### 6.4 The collapse is a moved distribution, not a mean pulled to zero

§4.4 requires this and it is the one thing that could have overturned the
reading. Per seed, `H1_only`:

| | range over twenty seeds | same sign |
|---|---|---|
| `s = 0`, both arms | `[+7.1073, +37.4222]` | **20/20** |
| `s = 0.01` uniform | `[−2.3636, +1.7105]` | no |
| `s = 0.01` preferential | `[−1.3005, +1.8237]` | no |

**The two distributions are disjoint.** The smallest value at `s = 0` is `3.9`
times the largest value at `s = 0.01` in either arm. Twenty against twenty, no
overlap, so no test is required. For `both`, nineteen of the twenty `s = 0` seeds
sit above the whole `s = 0.01` range.

Retained fraction of the `s = 0` gap, `H1_only`: uniform `+1.59% / −0.33% /
+1.03%` at `s = 0.01 / 0.02 / 0.05`; preferential `+2.03% / +1.87% / +1.32%`.

### 6.5 A7-A-4, A3-8′: holds at `s = 0` and nowhere else

A3-8′ asks that the loop-sum-only cell be same-sign across all seeds and exceed
the gate-only cell. At `s = 0`: same sign `20/20`, `+22.2119` against `−0.2997`,
**holds**. At `s = 0.01`, `0.02` and `0.05`, in both arms: same sign is false at
every point. **The criterion registered forward in `a3_asset_channel.md` §5.3
survives only at the point it was derived from.**

A7-A-3′, registered forward one message before this run and therefore **not
scored here**, asks whether the two arms' retained fractions differ by an order
of magnitude. Measured: `+1.59%` against `+2.03%`, a ratio of `1.28`.

A7-A-5 is not computed. The mean absolute loop sum is not read by
`experiments/a7_continuous_c.py`.

### 6.6 What this costs A3

§5.3 attaches one limit to every quotation of A3-8: it is measured on the top
eighth of the production layer by centrality. **A second limit is now required
and it is harder.**

> **A3-8's `+23.267` is a reading at mean out-degree `5.20`, and it is gone at
> mean out-degree `6.95`.** Adding `350` edges to `1039`, in any direction,
> removes `98%` of it. A3's registered sweep never varied graph density, so this
> sensitivity was neither measured nor excluded before now.

---

## 7. What the result says as economics

**Status: a reading, offered as a hypothesis with a registered discriminant in
§8.** Nothing in §6 depends on it.

### 7.1 The hypothesis

**The advantage of a central position is not a property of being central. It is
a property of the counterparty having nowhere else to go.**

Centrality barely moved in this experiment and rose in the placebo arm. What both
arms did was give every peripheral node one or two more places to send flow, from
about `5.2` counterparties to about `7.0`. The routing is row-normalised, so each
existing counterparty's share of that node's outflow falls to about `5/7`. The
central node's capture per relationship falls about a quarter.

### 7.2 Why a quarter becomes ninety-eight per cent

> **WITHDRAWN 2026-08-15 by §8's own falsification clause. The section is left
> in place because the way it failed is the finding. §10 replaces it.**
>
> Compounding predicts a smaller positive drift, so the gap at `s = 0.01` should
> still grow with the round count. Measured across a fourfold change in rounds it
> does not grow at all. What the edges do is not dilute the rate, it is remove it.


§5.2 records that the payment premium is a per-round-trip multiplier compounding
over some twenty traversals. `0.75ⁿ` is `3.2%` at `n = 12` and `1.0%` at `n = 16`,
against a measured retention of `1%` to `2%`. **Same order, nothing fitted.**

So the candidate mechanism is: **positional rent is a small per-transaction
margin that compounds into a large stock by repeated traversal of the same
cycle.** Dilute the margin and compounding erases the stock.

### 7.3 Five consequences if it holds

1. **Concentration instruments are aimed at the wrong side of the network.**
   HHI, top shares, network centralisation and degree Gini all measure the
   centre. The load-bearing variable is at the periphery: how many counterparties
   the marginal agent has. Two economies with identical concentration can carry
   positional rents that differ by orders of magnitude. This is consistent with
   and sharpens the fingerprint register conclusion 34, which found top-end concentration
   realised by turnover rather than by incumbent lock-in.
2. **Breaking up the top and adding alternatives at the bottom are different
   interventions, and the second dominates exponentially.** The first moves the
   measured quantity, the second moves the base of the compounding.
3. **It explains why the rent is invisible in aggregate data.** The rent lives in
   the traversal count, which is transaction-frequency. Annual data integrate the
   compounding away and leave a stock difference with no visible margin, so a
   failure to find excess returns is not evidence against the mechanism.
4. **It predicts a threshold rather than a slope.** An exponential in a
   counterparty count is sharp. Sectors or regions just below look extractive and
   just above look competitive with little in between, which is a bimodality that
   can be looked for.
5. **It makes `PROJECT_PLAN` §12.3's fifth limit binding rather than
   incidental.** If rent is exponential in traversal count, no quantitative claim
   about the size of positional rent is interpretable until the rounds-to-time
   mapping is pinned. A3-8's `+23.267` is then a function of an unfixed free
   parameter.

### 7.4 The alternative, and why it points the same way

**H′: the divergence requires specific closed cycles that are traversed
repeatedly, and added edges give flow alternative routes so it stops returning
around the same cycle.** Then the object needs near-tree or near-ring structure
with few bypasses, and in a dense real economy it would be a property of specific
sparse subnetworks: sole-supplier chains, company towns, tied credit, single
distribution channels.

**Both hypotheses send the empirical work to the same place: look for the rent
where alternatives are few, not where concentration is high.** They differ only
in functional form.

---

## 8. A registered discriminant, filed before the run that decides it

**Filed 2026-08-15, before any run at a round count other than three hundred.**

The retained fraction under §7.2 is about `(d₀/d)ⁿ` with `n` proportional to the
round count. Under H′ the cycles are bypassed or they are not, and the round
count does not enter.

| rounds | H predicts retained fraction | H′ predicts |
|---|---|---|
| 300 | `1%` to `2%` (measured) | measured, same |
| 150 | about `10%` to `14%`, the square root | unchanged, `1%` to `2%` |
| 75 | about `30%` to `37%`, the fourth root | unchanged, `1%` to `2%` |

**A7-A-6.** The retained fraction of the `s = 0` gap at `s = 0.01`, on
`H1_only`, is **monotone increasing as the round count falls**, and the value at
seventy-five rounds exceeds the value at three hundred by at least a factor of
five. Both arms, direction only.

**Falsification.** A flat ladder within a factor of two supports H′ and refuses
H, and the compounding account in §7.2 is then withdrawn from this document
rather than qualified.

**Guards.** The retained fraction is normalised at each round count against that
round count's own `s = 0` gap, so a smaller baseline at fewer rounds cannot
manufacture the ladder. The paired population is reported at every rung, because
fewer rounds means fewer completed round trips and the estimator may become
unreadable before the ladder is visible. A rung whose population falls below the
`s = 0` paired count at three hundred rounds by more than half is reported as
unreadable rather than as a value.

---

## 10. A7-A-6: **FAIL**, and what the round-count ladder actually shows

### 10.1 The verdict

`H1_only` retained fraction at `s = 0.01`:

| rounds | uniform | preferential |
|---|---|---|
| 300 | +1.59% | +2.03% |
| 150 | +2.78% | +5.40% |
| 75 | **−0.37%** | +9.85% |

§8 requires monotone increase as rounds fall and a factor of at least five from
three hundred to seventy-five, **in both arms**. The uniform arm is not
monotone. The preferential arm gives `4.85`. **FAIL.**

### 10.2 The criterion was normalised by something that moves with the treatment

The `s = 0` baseline scales with the round count: `H1_only` reads `+22.2119`,
`+11.3979`, `+6.4887` at three hundred, one hundred and fifty and seventy-five,
which is close to proportional. A retained *fraction* therefore goes as `1/R`
even with a numerator that never moves, giving a factor of four from three
hundred to seventy-five. The preferential arm's `4.85` is that and nothing else.

**This is the second criterion in this stage whose behaviour is dominated by its
own normaliser**, after A7-A-3's unnormalised difference of falls. Recorded as a
discipline candidate in §10.5 rather than repaired.

### 10.3 Unnormalised, the answer is clean

Absolute `H1_only` gap:

| rounds | `s = 0.01` uniform | `s = 0.01` preferential | `s = 0` |
|---|---|---|---|
| 300 | +0.3525 | +0.4511 | **+22.2119** |
| 150 | +0.3165 | +0.6160 | **+11.3979** |
| 75 | −0.0243 | +0.6390 | **+6.4887** |

**Change the round count by a factor of four, the `s = 0` gap changes by a
factor of four, and the `s = 0.01` gap does not move.**

### 10.4 §7.2 is withdrawn and H′ is what survives

Compounding predicts a smaller positive drift, so the gap should still grow with
rounds, only slowly. It does not grow. **The added edges do not slow the
accumulation, they end it.** §8's clause fires as written and §7.2 is withdrawn
rather than qualified.

**The economics, restated on what survives.**

At mean out-degree `5.20`, position buys a **rate**: run the economy longer and
the gap widens roughly in proportion. At mean out-degree `6.95`, position stops
buying a rate. Running twice as long no longer widens anything.

So what one or two extra counterparties destroy is not the margin on each
transaction. It is the **repetition** of that margin against the same
counterparty. **Positional rent is a lock-in rather than a spread.** It requires
flow to return along the same cycle, and one alternative route is enough to stop
it returning.

The policy corollary is stronger than §7.3's and replaces its second item: the
target is not the size of the margin, it is whether the relationship repeats. A
single alternative is sufficient, and **how large the per-transaction margin is
does not enter**. A large margin applied once is a level, and a small margin
applied two hundred times is the whole result.

§7.3's other four items survive the withdrawal: they turn on where the
load-bearing variable sits, not on the functional form that was withdrawn.

### 10.5 Registered forward, not scored here

**A7-A-7.** At matched added-edge count, the arm whose edges point at the centre
keeps a positive gap at low `s` that is same-sign across all seeds and does not
grow with the round count; the arm whose edges are spread does not keep one.

Measured, and this is what suggested it, so it governs the next stage rather than
this one: preferential arm, seventy-five rounds, `s = 0.01`, `H1_only` is
**20 of 20 positive**, range `[+0.0214, +1.8444]`, mean `+0.6390`. The uniform
arm at the same cell reads `−0.0243`. Position keeps a **level** when the new
relationships still run to the centre, and keeps nothing when they do not.

**Discipline candidate.** A normalised statistic whose normaliser moves with the
treatment tests the normaliser. Both A7-A-3 and A7-A-6 failed this way in one
stage. The check is cheap and belongs beside methodological discipline 5: before
registering a ratio or a difference, report how the denominator or the subtracted
term behaves under the treatment, and register the unnormalised quantity as well.

---

## 11. `D_fixed`, the registered estimator, computed 2026-08-16

Everything in §6 and §10 was read on `D_reach`, the within-`s` intersection,
which §4.2 registers as **reported and never scored**. §4.2's scored estimator is
`D_fixed`, the population intersected across every cell and every grid point.
This section is that estimator, over §4.3's readable region.

The population survives: **`24.20` nodes in the uniform arm and `35.95` in the
preferential arm**, against a within-`s` paired count of `41.6` at `s = 0`. The
outcome §4.2 warned about, an intersection too small to bin, did not happen.

### 11.1 The headline does not move

`H1_only`, split recomputed at each `s`:

| | `s = 0` | `s = 0.01` | retained |
|---|---|---|---|
| uniform | +23.3206 | +0.3604 | **+1.5%** |
| preferential | +24.8347 | +0.4224 | **+1.7%** |

`both`: uniform `+20.1927 → −0.2439`, preferential `+20.6382 → +0.7422`. The two
bin conventions differ by less than half a percentage point everywhere, so §4.2's
unspecified split does not carry the result. **Every economic statement in §7 and
§10.4 stands on the registered estimator.**

### 11.2 A7-A-3 is **void** on the estimator it was registered on

The criterion names `D_fixed` explicitly. On `D_fixed` each arm's population is
intersected across **its own** grid, and the two grids are different graphs, so
the two arms end up with different node sets, `24.20` against `35.95`. An
unnormalised difference of falls then compares quantities defined on two
different populations.

The falls also invert, `22.960` for uniform against `24.412` for preferential,
which on `D_reach` ran the other way. **That inversion carries no information**
for the same reason: the two numbers are not taken over the same agents.

**Verdict: void, and the reason is measured rather than asserted.** §6.3's
letter-pass on `D_reach` is demoted to a diagnostic. §10.5's A7-A-3′ is
comparable because it normalises each arm against its own `s = 0`, and it reads
`+1.5%` against `+1.7%`, a ratio of `1.13`.

**Registered forward.** A cross-arm comparison on this estimator needs a
population intersected across **both** arms' grids. That is a construction this
stage did not have and it is not built after seeing these numbers.

### 11.3 A7-A-4 loses its one surviving point

A3-8′ requires the loop-sum-only cell to be same-sign across all seeds. On
`D_reach` that held at `s = 0` at `20/20`. On `D_fixed` it is **`17/20`** in the
uniform arm's population and **`19/20`** in the preferential arm's.

**A3-8′ now holds nowhere on this axis, including at the point it was derived
from.** The clause that fails is sign stability, and what breaks it is removing
about forty per cent of the population by intersecting across grid points.

> **A3-8′'s sign stability is not robust to the choice among two defensible
> populations.** Both are intersections of agents who complete a round trip; one
> intersects across cells, the other across cells and grid points. The criterion
> passes on the first and fails on the second.

**Added 2026-08-27.** A3-8′ is a conjunction of two clauses and only one of them
is what Theorem 2 licenses. Stage A3i (`experiments/a3i_pooled_ordering.py`)
pools every point on record at which both cells were computed, this section's
grids among them, and tallies the clauses separately: **the ordering clause holds
at 54 of 57 points, the sign-stability clause at 9, and the gate-only cell is
sign-stable at none of them.** The three points where the ordering does not hold
are `s = 0.95` and `s = 0.99` and the complete graph, and the gate cell reads
exactly `0.0000` at all three. The failure recorded here stands as recorded: the
conjunction fails, and the clause that fails it is stability. Nothing in this
section's numbers changes.

This is recorded against A3-8′ and not against A3-8, whose state stays `void` for
the reason already on record.

### 11.4 One thing `D_fixed` changes about reading the `s = 0` row

Under `D_fixed` the `s = 0` row is **no longer arm-independent**, because each
arm's fixed population is different. `H1_only` at `s = 0` reads `+23.3206` in one
and `+24.8347` in the other, and `H0_only` reads `+2.9375` against `−0.5807`.
Nothing is wrong: they are the same economy read over different agents. **No
`s = 0` number from this section may be quoted without the arm attached**, which
is not true of any `D_reach` number.

### 11.5 What is still only on `D_reach`

**A7-A-6's round-count ladder.** It was run at one hundred and fifty and
seventy-five rounds on `D_reach` only, and is not recomputed here. Its verdict
stands as recorded in §10 with that limitation attached, and §10.3's
unnormalised reading, which is what the conclusion rests on, is a comparison
within one estimator rather than across two.

---

## 12. Leg A7-B: the two probes, and the section 5.3 trigger decided

**Nothing scored. Section 5.8's order is P1, P2, the trigger, then the grid, and
the trigger is decided on the probes alone so that the choice between its exits
cannot be made after seeing the result it decides how to read.**

### 12.1 P1, retention: a cliff rather than a decline

`experiments/a7b_probes.py`, twenty seeds, three hundred rounds. Retention of a
one-off transfer at forty rounds, richest node:

| `s` | uniform | preferential |
|---|---|---|
| 0.0 | +0.2372 | +0.2372 |
| 0.01 | +0.1363 | +0.1423 |
| 0.02 | **+0.0005** | +0.1028 |
| 0.05 | +0.0000 | +0.0039 |
| 0.1 | +0.0000 | +0.0002 |
| ≥ 0.2 | +0.0000 | **+0.0000** |

**Section 5.2 registered this as a decline from `28.06%` to `0.00%` along the
axis. It is not a decline, it is a cliff**: gone by `s = 0.02` when the edges are
spread and by `s = 0.1` when they point at the centre.

**That strengthens the ruling on `I` and `M` and changes its ground.** Above the
cliff they are not confounded, they have nothing to transmit, so `d(I, s)` and
`d(M, s)` are identically zero there for a reason with no connectivity in it.

**It does not mean the model has no holdings.** What is erased is the memory of a
perturbation. Steady-state holdings still circulate, so `E`, which acts on the
wage flow, and `K`, which acts on the current holdings each round, are untouched.

**A fourth criterion whose shape does not say what it meant.** Section 5.3 makes
`I` and `M` scoreable over any region where this curve is flat within a band. The
curve is flat from `s = 0.05`, **flat at zero**. By the letter they become
scoreable exactly where the mechanism cannot fire. The clause needed "and
non-zero" and does not have it. Recorded, not repaired.

### 12.2 P2, room, and two numbers that reproduce

`s = 0` aggregate Gini `0.9368` against section 11.3's `0.935`, and
`log(1/HHI) = 2.6196`, an effective holder count of `13.7` against that section's
"about fourteen of two hundred". Both reproduce.

**Independent confirmation of section 2.4.** At `s = 1` the aggregate Gini is
`0.0746` while A4's `C = 0` control sits at `0.00711`, an order of magnitude
apart. The ruling that `s = 1` is not `C = 0` was made by reading code; it is now
measured.

Room relative to `s = 0`, largest value over the grid, identical in both arms:

| measure | max ratio |
|---|---|
| Gini, aggregate | **15.81** |
| `log(1/HHI)`, aggregate | **2.00** |
| Gini, production layer only | **2.36** |
| **`log(1/HHI)`, production layer only** | **1.20** |

The aggregate Gini's `15.81` is section 11.3's ceiling problem measured on this
axis, and it is the same order as the `0.065` against `0.99` recorded there.

### 12.3 The trigger: satisfied through the registered substitution

The band, **registered before this run and an arbitrary calibration value with no
theoretical provenance**, is a factor of `1.5`. It gates readability and may not
serve as a falsification basis. It was chosen by order of magnitude rather than
by precision: section 11.3 measured that a room movement near fifteen is enough
to turn `A(K) = 5.31` into `A(K) = 0.06`, and `1.5` is an order of magnitude
below that.

Registered with it, before the run: **if the aggregate `log(1/HHI)` leaves the
band while the production-layer-only version stays inside, leg B's primary
outcome becomes the production-layer-only pair.**

That is what happened. `2.00` outside, `1.20` inside.

> **Decision.** Leg B proceeds on **one axis**. Exit one, the
> `layer1_initial_share` second axis, is not taken. Exit two, recording the leg
> as not identified, is not taken. The primary outcome is the
> **production-layer-only `log(1/HHI)`**, with the aggregate `log(1/HHI)` and
> both Ginis reported beside it on every row.

Section 11.6 of `a4_causal_primitive.md` introduced the production-layer-only
pair for a units reason, that the aggregate is taken over a population containing
a twenty-node financial layer holding `99.7%` of the stock. P1 adds a second
reason pointing the same way: what survives a generation lives in that layer at
every seed, so the measure leg B now scores on excludes the only place a
generational mechanism has anything to work with.

---

## 13. Leg A7-B: the verdicts

Twenty seeds, three hundred rounds, uniform arm, the section 5.4 cells, primary
outcome the production-layer-only `log(1/HHI)` per section 12.3. `d(X, s)` is
taken **within seed** against that seed's own control, so the graph draw cancels.

| `s` | `d(E)` | negative seeds | `d(K)` | negative seeds |
|---|---|---|---|---|
| 0.0 | **−0.02701** | 17/20 | −0.00039 | 12/20 |
| 0.01 | −0.00539 | 15/20 | −0.00035 | 10/20 |
| 0.02 | −0.00156 | 13/20 | −0.00009 | 13/20 |
| 0.05 | −0.00101 | 16/20 | −0.00006 | 13/20 |
| 0.1 | −0.00034 | 14/20 | −0.00003 | 14/20 |
| 0.2 | −0.00005 | 11/20 | −0.00002 | 13/20 |
| ≥ 0.5 | ≤ 2e-05 | mixed | ≤ 1e-05 | mixed |

### 13.1 A7-B-1, capital returns: **unreadable**

The criterion asks that `|d(K, s)|` decrease in `s` with `sign(d)` stable. **The
sign is unstable at every grid point including `s = 0`**, where the mean is
`−0.00039` against a range of `[−0.0020, +0.0010]` whose width is five times the
mean and which straddles zero. A quantity with no sign has no magnitude to trend,
so the slope cannot be asked. `K` is not distinguishable from zero anywhere on
this carrier.

**Not a negative result.** It does not say connectivity fails to amplify capital
returns. It says the effect is not measurable here, which is where A4-4 was, on a
different estimator.

### 13.2 A7-B-2, education: not adjudicable as registered

The clause scores `E` only where `d(E, s)` "clears the seed noise floor at the
low-`s` end", and **that floor was never given a numeric form**. Measured against
the same all-seeds-same-sign standard A7-B-1 uses, `E` fails it too, at `17/20`
rather than `20/20`.

### 13.3 A7-B-3, the two measures: does not fire

Section 3's disagreement clause needs the two measures to disagree in the sign of
the slope. On the aggregate `log(1/HHI)` both competitors are also sign-unstable
and also near zero. The two measures agree, and what they agree on is that
nothing is readable.

### 13.4 A7-B-4, the probes: done, section 12

### 13.5 A7-B-5, `I` and `M`: not run, and the reason is measured

Section 5.2 ruled them unreadable for direction. Section 12.1 measured something
stronger: above `s = 0.02` in the uniform arm a one-off transfer leaves nothing
after a generation, so a transmitting mechanism has no stock to transmit and
`d(I, s)` and `d(M, s)` are identically zero there by construction. Running them
would produce zeros whose cause is the carrier. **Recorded as not run rather than
as measured.**

### 13.6 The section 5.4 fence: no-op confirmed

`pooling = generation` against `round` at both endpoints, twenty seeds, every
cell and every measure identical. `pooling` is read only where the demographic
layer fires and leg B's cells keep `I` and `M` off. Verified by running, which is
the point.

### 13.7 The pattern that is visible and is not licensed

`|d(E)|` falls by a factor near **2700** from `s = 0` to `s = 0.2`, and `|d(K)|`
by about twenty. The control cell's production-layer effective holder count rises
from `75` to `180` of `180` across the same range.

**This may not be reported as an effect**, because the quantities whose
magnitudes are falling are, by the registered standard, indistinguishable from
zero at every point. What can be said is that exogenously imposed heterogeneity
does not survive either: `E` injects dispersion into the wage flow every round and
a dense graph flattens it every round, so the steady state keeps none of it. That
is the same mechanism section 12.1 measured for a one-off transfer.

### 13.8 Registered forward, and a discipline point

> **A7-B-6.** The direction of `d(X, s)` is judged by a sign test rather than by
> all-seeds-same-sign, at the α this project uses elsewhere.

All-seeds-same-sign is the standard `a3_asset_channel.md` section 5.2 uses for a
share decomposition, where refusing to quote a share whose sign moves is right.
Carried onto a twenty-seed difference it is a different and much stricter object:
at `s = 0`, `d(E)` is negative at seventeen of twenty seeds, which a two-sided
sign test puts at `p ≈ 0.003`, and the registered clause calls that unreadable.
**The clause was inherited rather than chosen.** A7-B-6 governs the next stage and
is not applied here.

### 13.9 What the two legs say together

Leg A: the divergence A3-8 measures exists only on the sparse graph, and thirty-
four per cent more edges remove ninety-eight per cent of it whichever way they
are aimed.

Leg B: on a different carrier, with a different outcome and different mechanisms,
the two competitors that could be measured are indistinguishable from zero
everywhere, and what magnitude they have follows the same collapse.

**Two carriers, two quantities, one shape.** Whatever this model has to say about
position and about competing explanations, it says only at mean out-degree near
five, and the sensitivity to that number was neither measured nor excluded before
this stage.

---

## 14. "So you have rediscovered supply and demand"

**The objection is the one this stage will meet first, and part of it lands.**
Written here so that the concession and the defence travel together and neither
is quoted without the other.

### 14.1 The formal answer

`b1_theorem.md` §5 defines the object. If the terms could be written as a
potential on positions, which is one number per position and is what a price
vector is, the loop sum would be **identically zero**. A non-zero loop sum is
formally equivalent to "no price system represents these terms".

Supply and demand is the claim that outcomes are generated by a price vector.
**If this were that, A3-4 would read zero.** It reads `+0.36536` against a
holonomy of `+0.37686`.

**The obvious rejoinder, and why it fails.** "Your `γ` is a price under another
name." A price vector assigns one number **per position**. `γ` is one number per
**agent and position pair**, and the content of the framework is that two agents
facing different terms on the same transition has nowhere to sit in a price
system. That is a theorem rather than a phrasing.

### 14.2 The measured answer: two shape differences, both falsifiable

**Supply and demand predicts the margin falls. The margin rose.** More
counterparties is supposed to reduce extraction. Measured at matched added-edge
count, `H¹` read directly off the terms matrix over the paired population is
`+4.9%` and `+7.0%` **higher** at `s = 0.01` than at `s = 0` in the two arms, and
the preferential arm raises the centrality dispersion and the layer gap as well.
`D` falls `98%` in both. **Whatever removed it, it was not the margin.**

**Supply and demand predicts a smaller rate. The rate went to zero.** Cournot
from five competitors to seven takes the markup from `1/5` to `1/7`, a `29%`
reduction, and the result still accumulates, only more slowly. Measured across a
fourfold change in the round count, the gap at `s = 0` moves with the rounds and
the gap at `s = 0.01` **does not move at all** (§10.3). That is a phase change in
the dynamics rather than a displacement along one, and it was measured on three
round counts rather than argued.

### 14.3 What the objection is right about, conceded without qualification

**The policy implication is not new.** "More alternatives at the periphery beats
breaking up the top" is competition policy's oldest sentence. Nothing in §7.3's
second item or §10.4's replacement of it may be presented as a discovery, and
this document's §7.3 should be read with that attached.

### 14.4 What remains claimable

1. **The instruments are aimed at the wrong side.** HHI, top shares, network
   centralisation and degree Gini all measure the centre, while the load-bearing
   variable is the counterparty count at the periphery. This is a claim about
   measurement rather than about mechanism, and it is actionable and falsifiable.
2. **The empirical signature is a threshold rather than a slope**, since the
   accumulation goes from present to absent rather than from large to small, and
   annual data integrate the accumulation away and leave no visible margin. Both
   are things to look for rather than things to assert.
3. **The stage's own product is a negative result about the model.** §6.6's
   boundary stands: this supports statements about a running stratified economy
   in simulation and not about any real one. The objection assumes a claim about
   an economic law is being made. What is being reported is a property of a
   mechanism model and the discovery that its domain is far narrower than the
   manuscript assumed, in a dimension the manuscript never named.

### 14.5 The one-sentence form

> Supply and demand predicts that adding counterparties lowers the margin. The
> margin rose by five to seven per cent and the outcome fell by ninety-eight.
> So the margin is not what removed it. And the object is defined as the part of
> the terms that no price vector can represent, so if it were a price phenomenon
> it would be zero by construction.

---

## 15. Close-out, 2026-08-16

**Both legs run. Eleven criteria, all with verdicts.** One pass, four fails, one
void, one shape-wrong, three unreadable or not adjudicable, one not run with the
reason measured.

**Two decisions, taken and registered rather than left open.**

**`diagnostic_only` stays on.** Every A7 record keeps it and no A7 heading enters
`RESULTS.md`. Flipping it needs a job in `run_all.py`, that file is currently
carrying another line of work, and the reproducibility this flag protects is
already met: the records are on disk and the verdicts are in this document. **To
be revisited when that work lands**, not deferred indefinitely.

**`D_reach` stays the default output of `experiments/a7_continuous_c.py`, and
this is a registered known state rather than an oversight.** `D_fixed` runs under
`--dfixed`, §11 measured the difference, and the difference does not move the
headline. What it does move is recorded there: A7-A-3 becomes void and A7-A-4
loses its last point. Anyone quoting a gap from this stage has to say which
estimator it came from, and §11.4 records that `s = 0` is not even arm-independent
under `D_fixed`.

**What A7 hands forward.** The limit in §6.6 for A3. The four registered-forward
criteria in §10.5, §11.2 and §13.8. The discipline candidate on normalised
statistics, which this stage tripped four times. And the correction to
`a4_causal_primitive.md` §9, whose retention table had no producer and was a
single seed.

---

## 9. Changelog

### 2026-08-15, block 1 filed

Sections 1 to 3 written. Six rulings: the parameter is `s` and runs against `C`
(§2.1); `s` moves the adjacency alone (§2.2); the held rules run rather than
freeze, with a registered diagnostic on payer-set churn (§2.3); the `s = 1`
endpoint is not comparable to any `C = 0` number (§2.4); dispersion means the
standard deviation (§2.5); the availability check must be re-run into this file
before its figures may be cited as constants (§2.6). One decision: both legs, one
registration, A7-A first (§3).

Nothing has been scored and no stage code exists at the time of this entry.

### 2026-08-15, block 2 filed

Section 4 written: leg A7-A's criteria. Four scored (A7-A-1 reach, A7-A-2 the
interior slope, A7-A-3 the placebo, A7-A-4 A3-8′), two reported and not scored
(A7-A-5 the construction identity, A7-A-6 reach description). Four guards and
one placebo arm registered. Two rulings that were decisions rather than
transcriptions: the scored population is the grid-wide intersection and
therefore cannot clear A3-8′'s precondition, stated in advance (§4.2); and no
criterion reads the whole grid, because the complete-graph endpoint is an
attractor by A4-1 and its zero is overdetermined (§4.1).

A3-8′ is scored here for the first time since being registered forward in
`a3_asset_channel.md` §5.3. A3-8's own state is untouched and stays `void`.

Still nothing scored, still no stage code.

### 2026-08-15, block 3 filed, and one correction to block 1

Section 5 written: leg A7-B's criteria. Two scored (A7-B-1 capital returns,
A7-B-2 education conditional on clearing its noise floor), one reporting rule,
two gates.

**The correction.** §3.3 registers §12.3's memory limit as an alternative
explanation for a flat slope in leg B. §9's retention table says it is an
alternative explanation for a **declining** slope, which is the direction the
leg would be claiming, so the exposure is a false positive. §3.3's text is left
as filed and §5.2 carries the correction.

**A second confound, found while writing §5 and not present in block 1's
account.** `E` and `K` are exposed in the opposite direction through the Gini
ceiling, which §11.3 had already measured: `0.065` of room at `C = 1` against
`0.99` at `C = 0`, and that compression alone is the difference between
`A(K) = 0.06` and `A(K) = 5.31`. The registered outcome for leg B is therefore
`log(1/HHI)` with the Gini reported beside it, and §5.3's room probe measures the
residual exposure rather than assuming it away.

Consequence for the leg's reach: two of the four competitors are reported and
not scored, decided before the run and for reasons already measured in
`a4_causal_primitive.md`. Leg B keeps `E` and `K`, and A4-3 measured `E` as the
largest of the four on the arm where any of them moved.

Still nothing scored, still no stage code.

### 2026-08-15, code block 1, and a guard corrected by its own test

`NetworkSpec.shortcut_rate` added, defaulting to `0.0`, wired into `build_graph`
between the stratified construction and the payroll fold, with
`tests/test_a7_shortcut_rate.py` alongside it. The field is in `replace`'s
hand-written list, without which the sweep would have reached every cell through
a silent reset to the default.

**The test refuted a sentence in this file before any stage code ran.** §2.6 said
the dispersion falls monotonically and §4.4's A7-A-5 turned that into a per-seed
claim. Measured over twenty seeds: monotone in the mean with no exception,
monotone at eighteen of twenty seeds individually, and the two exceptions rise by
at most `7.6e-4` (`0.62%` of that seed's `s = 0` value) at the single step
`0.01 → 0.02`. Both statements are corrected in place, which is permitted because
nothing has been scored, and the correction is recorded rather than made
silently.

The bitwise reproduction of A2 to A6 under the new default is **not yet
verified**. It is verified by running, not by argument, and that run is local.

### 2026-08-15, bitwise reproduction verified, and leg A7-A run

`run_all.py` plus the three A3 scripts and `a6_ratchet` under the new default.
`a6_ratchet`, which is the long one and goes through `build_graph` at every cell,
came back with no diff at all. `a0`, `a0b`, `a2`, `a2c`, `a3b`, `a4` and `a5`
likewise. Two records moved and neither is A7's: `a6_siphon_cost.json` gained a
`criteria` block with zero deletions, and the two A3 records had three
machine-precision floats replaced by a bounded phrase and gained a
`from_an_earlier_run` field. Both are records older than the writers that produce
them, dated 08-12 and 08-13, and both are `MEASUREMENT.md` failure mode 9 in the
half a job-existence guard does not cover: such a guard asks whether
a job could regenerate a record, not whether the committed record equals what the
job now produces.

Blocks 2 to 4 of the code: `a3c_load_bearing.build()` routes keywords by which
dataclass declares them, with the two field sets checked disjoint at import;
`experiments/a7_continuous_c.py` with `--probe`, `--grid` and `--low`;
`NetworkSpec.shortcut_mode` and the preferential placebo, matched edge for edge
against the uniform arm at every rate and seed.

**Two knobs wired to nothing, both caught before they mattered.** A `seed` guard
in `build()` that could never fire, since `seed` is a named parameter and binds
before the body runs, replaced by a comment and a test. And `--arm` not threaded
into the probe path, so the probe reported the uniform arm while claiming to run
the placebo. **A knob wired to nothing, twice in one afternoon.**

Sections 6, 7 and 8 written: the run record, the economic reading as an explicit
hypothesis, and A7-A-6 registered before the round-count ladder that decides it.
A7-A-1 passes, A7-A-2's registered shape is wrong and is recorded as such,
A7-A-3 is satisfied in letter by a margin its own shape cannot interpret,
A7-A-4 holds only at `s = 0`, A7-A-5 is not computed.

### 2026-08-15, A7-A-6 run and failed, and §7.2 withdrawn

The round-count ladder at seventy-five, one hundred and fifty and three hundred
rounds, both arms. A7-A-6 **fails**: the uniform arm is not monotone and the
preferential arm gives `4.85` against a registered five. §10.2 is why, and it is
the second criterion in this stage whose behaviour is dominated by its own
normaliser: the `s = 0` baseline scales with the round count, so a retained
fraction goes as `1/R` with a numerator that never moves.

Unnormalised the reading is clean and is in §10.3. The gap at `s = 0.01` does not
move across a fourfold change in rounds while the gap at `s = 0` moves with it.
**§7.2's compounding account is withdrawn under §8's own clause**, left in place
struck through because the way it failed is the finding, and replaced by §10.4:
the added edges end the accumulation rather than slowing it, so positional rent
on this carrier is a lock-in rather than a spread.

A7-A-7 registered forward in §10.5, with the measurement that suggested it, plus
a discipline candidate on normalised statistics.

### 2026-08-16, records written, A7-A-5 failed, `D_fixed` computed

`experiments/a7_continuous_c.py` now writes to `results/`, declared
`diagnostic_only` with the reason in the record. Every figure in §6, §10 and §11
has a file behind it rather than a terminal.

**A7-A-5 fails.** Its first implementation read the null cell, where
`terms_spread = 0` flattens the terms matrix and every loop sum is exactly zero
by construction; it printed `0.000000` at every tier and rate, which is what
caught it. Its second read the paired population, which moves with the treatment,
and came out rising at the low end for that reason. On the fixed
production-layer set at twenty seeds it still rises before it falls, peaking at
`1.44` times its `s = 0` value in the uniform arm and `4.13` times in the
preferential one. **§4.1's argument that `s → H¹` is a construction identity
holds for global centrality dispersion and not for the quantity the loop sum is
built on over the measured population**, and the two are different objects.

The measurement that follows from it is the stage's cleanest: on the paired
population at `s = 0.01`, `H¹` read directly off the terms matrix is `+4.9%`
higher than at `s = 0` in the uniform arm and `+7.0%` higher in the preferential
arm, while `D` is down `98%` in both. **`H¹` up, `D` down, no proxy and no
tolerance.**

That is the third statistic in this stage dominated by something moving with the
treatment, after A7-A-3 and A7-A-6, and it is why §10.5's discipline candidate is
worth promoting.

§11 is `D_fixed`. The headline does not move, A7-A-3 becomes **void** on the
estimator it was registered on, and A7-A-4 loses its one surviving point.
