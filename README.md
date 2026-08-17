# monetary-topology

Mechanism models for a topological framework of claims and resources.

A monetary claim and the resource it points at are two different objects. Most
of what follows from that is uncontroversial and widely conceded in principle.
This repository is about the part that is not: once claim circulation is
stratified, **a quantity of money does not establish access to resources. An
adjacency matrix does.**

The models here are small on purpose. Each isolates one mechanism, exposes fewer
than a dozen parameters, and reports a criterion that can fail. The point is not
to build a simulator large enough to reproduce an economy. It is to make a
handful of structural claims checkable by someone who did not write them.

**Status, 2026-08-17.** Twelve B-track stations and eight A-track stages have run.
Three carriers have produced measured non-zero cycle sums on real transaction
data: mortgage origination terms, cross-currency funding, and the ETF creation
triangle. **One station's headline was withdrawn on its own constructed
counterexample, one failed its own pre-trend check and says so in its headline,
and one answers the sharpest objection in the programme with "this ruler cannot
measure it."** See [RESULTS.md](RESULTS.md) for the full record and the speedrun
below for what each station asked, answered and retracted.

The headline empirical number: hold census tract, year, lien position, loan
purpose, occupancy and dwelling type fixed, and **78 to 85 percent of the variance
in financing terms remains inside those cells.** A single price vector on
positions predicts zero. A pre-registered placebo, in which government programmes
replace the credit-graded price grid with a flat schedule, moves it in the
predicted direction by 130 times the scale of a gap known to be zero.

---

## Speedrun

**One line per station: what it asked, and where it landed.** Full four-field
entries, including the retraction attached to each station, are in
[Volume II, B0–B6](claude-docs/B轨speedrun_EN_part1_v1.md),
[Volume II, B7–B11](claude-docs/B轨speedrun_EN_part2_v1.md) and
[Volume I, the A track](claude-docs/A轨speedrun_EN_v1.md).

### Volume II — is there one global price field?

| | asked | landed |
|---|---|---|
| **B0** | what does non-integrability entail, and what does it deliberately not | scope fixed: one inequality on one cycle; no welfare criterion, no claim that planning is better |
| **B1** | is integrability a theorem of notation | yes on one index, no on two. Four theorems; the variance share **is** the square holonomy, verified to `1e-16` on 28 million vertices |
| **B2** | do two applicants for the same financing get the same terms | no. Within-cell variance share **0.7831**, median within-cell IQR **0.53 points**. A gradient field predicts zero |
| **B3** | do currency cycles that never touch the Treasury vanish | no. **30.9 to 45.6 bp** against a floor of 2.8 to 3.7, signal over floor **63 to 200**. CNH against CNY reads up to **1198×** |
| **B4** | does a one-way conversion still mean an obstruction | **no, and this runs against the framework**: directedness helps the null. A spread makes a non-zero round trip with no obstruction |
| **B5** | does the premium collapse when the eligibility rule is deleted | ratio **0.102** treated against **0.712 / 1.050 / 0.999** control — **and the pre-trend check failed**, accounting for 0.77 to 0.90 of the collapse |
| **B6** | can a hole get a positive reading | structure visible without estimation: two frozen rates, one float running **410 → 624**. The `H¹` arm is blocked on a token |
| **B7** | how many independent ways does a local market deviate | **two**: a tilt and a bend, multiplicative. **The original rank reading was withdrawn** on a constructed zero-interaction counterexample that reads it back 20/20 |
| **B8** | does one household's terms depend on the path it walked | **yes, and this is the strongest reading in the programme.** Two realisable routes to the same state differ by **1.07e+05 to 4.18e+06 times the floor**, six of six cohorts, permutation null **0/999** |
| **B9** | on the cleanest carrier, is it zero | no. **1.2 to 1.7 bp**, 1.05 to 5.08 times the measurement floor and about 1 against the cost floor. Quantisation falsified. **Twenty-two instrument defects on the ledger** |
| **B10** | does the reading survive coarsening the state grid | **86% of transitions never happen**; merge the servicing states and `b₁` reads 0. On the objection itself: **the registered question has no reading** |
| **B11** | can the ring be replicated in corporate credit | **gated, not open**: the gate needs 200 issuers against a measured ceiling of **227** |
| **B12** | *(registered 2026-08-17, not run)* | a new ruler for B10's question: does `ω` pull back from the coarse grid? **It predicts an exact zero, so it can fail** |

### Volume I — does position, rather than behaviour, decide who is reached?

| | asked | landed |
|---|---|---|
| **A0** | is spending inside your own stratum different from saving | 9/9. Slope indistinguishable from zero with the adjacency matrix held fixed |
| **A0b** | is there an elasticity above which the production layer cannot survive | 12/12. **Unit elasticity is the dividing line** |
| **A1** | does the default ordering emerge rather than being hard-coded | **never started**, and it is the only stage attached to real data |
| **A2** | can volume rise while reach shrinks | 8/8. **Flow `×44.87` while the support set goes `×0.402`**, sign flip in 12/12 seeds. Max propensity with no in-edges ends at **zero** |
| **A2c** | can the loops disappear without deleting an edge | 7/7. Cycle rank collapses to **0.029** of potential, no edge deleted |
| **A3** | is compound advantage literally a loop sum | the hinge: **`+0.36536` against `+0.37686`, 3.05% apart**, from two modules that share no code. **And its one externally checkable prediction failed its own diagnostic** |
| **A4** | is connectivity upstream of the four standard explanations | connectivity alone gives Gini **0.93673**; all four opponents alone stay **below the 0.02 floor**. Two criteria void |
| **A5** | is there a reachability threshold | 4/8. **And the stored results file could not be reproduced by the code committed beside it** |
| **A6** | what redistribution rate does the siphon cost | **six tax points**, and that difference is the siphon, in units of tax |
| **A7** | does continuous connectivity repair A4's void criteria | **run, both legs.** One pass, four fails, two voids, and the content is in the failures: `H¹` rises while `D` collapses 98% at the first grid point, so the divergence exists only near mean out-degree five |
| **X01–X05, X-G** | the external checks | registered, **zero started** |

### The two things this repository has not done

**The coverage test has never run.** No single parameter vector has produced all
four surfaces. Until it does, "one mechanism, many surfaces" is empty here, and
it is the only possible empirical form of the unified claim.

**No A-track prediction has been checked against real data.** The A track has
zero external carriers; the B track has four.

---

---

## Where the conclusions live

**This README states a few results and does not state most of them. Every
conclusion not written here is in `docs/`, one file per stage, and the machine
record of every criterion is in [RESULTS.md](RESULTS.md).** The division is
deliberate: a README that carried every reading would have to be rewritten every
time one moved, and the ones that moved most are the ones worth reading in full.

**What the three places are for.** `docs/` holds the pre-registration, the
amendment trail and the reading, including the readings that were withdrawn and
why. `RESULTS.md` is generated from the JSON records and lists failed criteria
beside passing ones. This README is an entry point and is the least current of
the three by construction.

**A stage's own document is the authority on that stage.** Where this README and
a `docs/` file disagree, the `docs/` file is right and this file is behind.

### Track A documents

| stage | document |
|---|---|
| A0, A0b, A2, A2c | **no separate document.** These four are recorded in [RESULTS.md](RESULTS.md) and in this README's Roadmap only. Their design lives in the experiment files |
| A1 | [`a1_prereg.md`](docs/a1_prereg.md), availability [`a1_availability.md`](docs/a1_availability.md), inputs [`a1_inputs_availability.md`](docs/a1_inputs_availability.md) |
| A1b, A1c, A1d | [`a1b_prereg.md`](docs/a1b_prereg.md), [`a1c_prereg.md`](docs/a1c_prereg.md), [`a1d_prereg.md`](docs/a1d_prereg.md) |
| A3 | [`a3_asset_channel.md`](docs/a3_asset_channel.md) |
| A3b | [`a3b_initial_construction.md`](docs/a3b_initial_construction.md) |
| A3c | [`a3_restated.md`](docs/a3_restated.md) |
| A4 | [`a4_causal_primitive.md`](docs/a4_causal_primitive.md) |
| A5 | [`a5_reachability.md`](docs/a5_reachability.md) |
| A6 | [`a6_siphon_cost.md`](docs/a6_siphon_cost.md) |
| A7 | [`a7_continuous_c.md`](docs/a7_continuous_c.md) |

### Track B documents

| stage | document |
|---|---|
| scope | [`b0_claim_scope.md`](docs/b0_claim_scope.md) — what is claimed and what is deliberately not |
| B1 | [`b1_setup.md`](docs/b1_setup.md), theorem [`b1_theorem.md`](docs/b1_theorem.md) |
| B2 | [`b2_measurement.md`](docs/b2_measurement.md), loop B [`b2_loop_b.md`](docs/b2_loop_b.md), placebo validation [`b2_placebo_pool_width.md`](docs/b2_placebo_pool_width.md) |
| B3 | [`b3_cip_slice.md`](docs/b3_cip_slice.md), availability [`b3_slice_availability.md`](docs/b3_slice_availability.md) |
| B4 | [`b4_directed_edges.md`](docs/b4_directed_edges.md) |
| B5 | [`b5_orphan_prereg.md`](docs/b5_orphan_prereg.md), availability [`b5_orphan_availability.md`](docs/b5_orphan_availability.md) |
| B6 | [`b6_cuba_prereg.md`](docs/b6_cuba_prereg.md), availability [`b6_cuba_availability.md`](docs/b6_cuba_availability.md) |
| B7 | [`b7_interaction_rank.md`](docs/b7_interaction_rank.md) — **the headline is withdrawn and the stage still returns something; §11 and §11.12** |
| B8 | [`b8_fannie_slice.md`](docs/b8_fannie_slice.md), availability [`b8_inputs_availability.md`](docs/b8_inputs_availability.md) |
| B9 | [`b9_zero_holonomy.md`](docs/b9_zero_holonomy.md) |
| B10 | [`b10_freddie_availability.md`](docs/b10_freddie_availability.md) |

### Across every stage

[`MEASUREMENT.md`](docs/MEASUREMENT.md) — **fourteen ways a measurement in this
repository went wrong, each with its instances named**, and a checklist of sixteen
questions to ask before reporting a number. Every entry was written after the
mistake, not before, and several of them cost a stage its headline. **It is the
most useful file here for anyone who wants to know how much to trust the rest.**

---

## The result

### Quantity does nothing; topology does everything

![quantity versus topology](figures/a0_fig3_quantity_vs_topology.png)

The standard objection to any account of stratified circulation is that the
money has to end up somewhere, so it must eventually reach the bottom. It does
end up somewhere. The somewhere has no edge to the bottom.

**Left panel.** The top stratum's spending propensity is swept from 0 to 1: from
hoarding everything to spending everything, every round. Claims landing in the
production layer are unchanged **to floating-point equality** across that entire
range. Over the same sweep, circulation inside the financial layer moves by a
factor of 15. Book velocity moves by an order of magnitude. Topological
displacement does not move at all.

**Right panel.** Now hold spending fixed and open a single edge from the top
stratum into the production layer. Inflow doubles the instant the edge exists at
weight 0.05, then rises only a further 37% as the edge is widened seventeenfold
to 0.85. **Existence dominates magnitude.** That asymmetry is what makes the
property topological rather than quantitative: the discontinuity is at zero, not
along the range.

One boundary case runs against the trickle-down reading and is reported rather
than smoothed over. At a propensity below roughly 0.05 the *intermediate*
stratum is never resupplied, its holdings fall below its share of payroll, and
the wage bill is capped by illiquidity. Inflow to the production layer then
falls. So the top's spending can matter, but only by keeping the intermediary
solvent enough to make payroll, never by arriving as demand. Above that
threshold, additional spending buys nothing.

### An instrument that cannot reach what it targets

![two ratios](figures/a0_fig2_two_ratios.png)

The monetary authority observes the ratio of *active* claims to *active*
resources and issues enough to restore it. Claims that have left cross-layer
circulation are outside the instrument's field of view by construction.

The targeted ratio holds at 0.177 ± 3.6e-03. The total ratio rises from 1.00 to
65.72 over 400 rounds, monotonically, without bound. Cumulative issuance equals
cumulative retention to floating-point identity — not as a fitted result but as
an algebraic consequence of the issuance rule, which is the content of the
claim.

By the end of the run the financial layer holds 99.8% of all claims, up from
72.9% at the start. Every unit was issued in order to restore circulation in the
production layer. The only downward edge is a fixed wage bill, so issuance
cannot reach the quantity it was issued to repair. This is stronger than saying
the instrument targets the wrong variable: it targets a variable it has no
transmission path to.

### The production layer settles at the payroll edge

![layer drain](figures/a0_fig1_layer_drain.png)

The production layer does not collapse to zero. It converges to whatever the one
downward edge delivers plus its own internal circulation, and sits there
indefinitely while the financial layer grows without bound beside it. Nothing in
any aggregate would show a crisis. The two layers are simply no longer part of
the same circuit.

That floor turns out to be an artefact of holding the wage bill fixed, which
leads to the next result.

### Only the autonomous part of the downward flow survives

![boundary and floor](figures/a0_fig5_boundary_and_floor_source.png)

Employment is not exogenous. The framework's own claim is that hiring derives
from final demand, so when the production layer's spending falls, payroll falls
with it, cutting the production layer's income further. Adding one parameter, the
derived-demand elasticity `e`, gives

```
W_t = W_0 · [ (1 − e) + e · S_(t−1)/S_0 ]
```

with `S` the production layer's spending. `e = 0` recovers the fixed bill
bitwise, so this is a strict generalisation and the earlier figures are unchanged.

**The boundary sits at `e = 1` exactly, and it is structural rather than
numerical.** Below one, the bill keeps a constant term `W_0(1−e)` that anchors a
positive fixed point, and the steady-state level vanishes linearly in `(1−e)`. At
one that term is gone and the only fixed point is zero. Nothing is tuned to
produce this; the boundary is where the autonomous component of the bill
disappears.

The right panel fixes `e = 1.5`, safely past the boundary so that collapse is
certain, then varies how much of payroll is contractually rigid within a period.
The surviving level is **exactly proportional to that autonomous share**, a line
through the origin to a residual of 8.9e-16. At an autonomous share of 1 it
recovers the fixed-bill level precisely.

So the mechanism has a sharp statement: **whatever is derived from the production
layer's own demand cancels itself in a decline. What keeps the layer alive is
only the part of the downward flow that the layer's own fall cannot cut.**

![derived demand trajectories](figures/a0_fig4_derived_demand_trajectories_source.png)

Note what the lower panel is not showing. The bill is not cut by any decision.
It falls because it is a function of a quantity that its own fall reduces.

### The findings do not depend on the invented numbers

The source framework's worked example uses round figures: three strata holding
30% each. Those could be doing the work. So every one of them is replaced with a
published estimate and everything is re-run.

**Wealth shares** come from the Fed Distributional Financial Accounts, Q1 2026,
share of total net worth, retrieved 2026-08-08. The DFA's own percentile grouping
is 1 / 9 / 40 / 50, which maps onto the model's four strata with no
interpolation:

| stratum | share | FRED series |
|---|---|---|
| top 1% | 31.6% | `WFRBST01134` |
| next 9% (90-99) | 36.3% | `WFRBSN09161` |
| next 40% (50-90) | 29.6% | `WFRBSN40188` |
| bottom 50% | 2.5% | `WFRBSB50215` |

**Propensities** come from Fagereng, Holm & Natvik, *MPC Heterogeneity and
Household Balance Sheets*, AEJ: Macroeconomics 2021: low-liquidity winners of
small lottery prizes spend essentially all of the win within the year,
high-liquidity winners of large prizes slightly below one half. Their estimand is
the MPC out of a transitory shock rather than a spending rate out of holdings, so
what this licenses is the range and the ordering, not the exact values. Stated in
`calibration.py` rather than left for a reader to discover.

Every finding survives, and barely moves:

| | source-faithful | DFA Q1 2026 |
|---|---|---|
| spending-sweep spread | 0.0 | 0.0 |
| Layer 1 churn factor over the sweep | 15.0 | 15.3 |
| jump from opening one edge | x2.00 | x2.02 |
| Layer 1 share of claims, steady state | 0.9982 | 0.9983 |
| derived-demand boundary | e = 1.00 | e = 1.00 |

The DFA distribution is more unequal than the toy one and produces a *stricter*
version of the retention ordering the framework assumes: 0.025 / 0.10 / 0.45 /
0.52 against the worked example's 0.06 / 0.065 / 0.50 / 0.50, where the top two
were tied.

Both presets are run by every experiment and both are recorded in RESULTS.md. A
finding that held under only one of them would be a finding about that preset.

---

## Stage A2: the same dynamics on a graph

A0 runs on four strata, which is the block aggregation of a network. A2 runs the
same rules on the network itself, which makes a question available that the block
model cannot pose: not how much is circulating, but **how many nodes the
circulation still reaches**.

The graph reduces correctly. Layer 1 ends holding 0.997 to 0.998 of all claims
across seeds, against the block model's 0.9982, so the two stages are describing
the same economy at different resolutions.

### The measure has no threshold, on purpose

Proportional claim dynamics on a fixed graph have a positive stationary
distribution: nothing ever reaches exactly zero. So any measure of the form
"count nodes above a cutoff" reports the cutoff as much as the economy. Adding a
minimum operating scale would fix that, but it would import the mechanism stage
A1 exists to study and would invite the fair objection that a threshold was
inserted in order to make nodes disappear.

The headline measure is therefore the **effective support**, the reciprocal
Herfindahl index of the inflow distribution: the effective number of firms from
industrial organisation, applied to circulation rather than market share. It
equals the node count under an even spread, falls as flow concentrates, needs no
cutoff. A cutoff-based reachability series is kept as a secondary check with the
cutoff swept.

### The injection is what breaks the sign relation

![injection breaks the sign](figures/a2_fig6_injection_breaks_the_sign.png)

|  | total volume | effective support | production layer's share of all circulation |
|---|---|---|---|
| no issuance | **x0.87** | x0.73 | 38% → 26% |
| issuance | **x44.9** | x0.40 | 38% → **0.5%** |

Without issuance the two move together and an aggregate flow statistic still
carries information: volume falls, the reachable economy contracts, and the
number tracks the problem.

Turn issuance on and the signs come apart. New claims enter at the top and
recirculate inside a dense core, so volume rises by a factor of forty-five, while
the effective number of nodes reached keeps falling. **The aggregate is not
merely a poor measure at this point, it is anti-correlated with what it is being
used to monitor.** 12 of 12 graph seeds flip under issuance; 12 of 12 agree
without it.

The uncomfortable part is the timing. The instrument is used precisely when there
is a problem, so the aggregate reads best exactly when the underlying position is
worst.

### Reachability decides, not propensity

The standard account of a demand shortfall runs through the marginal propensity
to consume, a property of the agent. The framework's claim is about edges.

Give one household node the **maximum possible propensity** and sever its
in-edges. Final holdings: exactly zero, on every seed. An agent that would spend
everything, spends nothing, because nothing arrives.

### The intermediate layer

![intermediate closes the channel](figures/a2_fig7_intermediate_closes_the_channel.png)

A third block sits between the two. It collects household spending as revenue,
pays rent and financing costs upward, and **operates the payroll channel
downward**. That is a position no node can occupy in a two-layer graph, where the
payer is rich and the recipient is the victim and nobody is both.

Two hypotheses were written into the module docstring before the code was run,
along with the null, so that any outcome could be reported.

**H1 holds.** The payroll channel closes on its own. The elasticity is zero and
the bill *owed* never moves off 8.00, so nothing in the rule cuts hiring and no
agent decides anything. What falls is the amount *paid*, because the entity
operating the channel is being drained upward at the same time and eventually
cannot fund what it owes. Funding ratio 0.68 → 0.000 across 6 seeds and three
block sizes. The two-layer control sits at exactly 1.0000 forever.

**H2 holds, in its strong form.** A three-layer economy with its elasticity
parameter set to **zero** lands where the two-layer economy only reaches at
elasticity **one**: the A0b collapse boundary. An intermediary funding payroll out
of revenue paid by the people payroll pays has no autonomous component left to
anchor a fixed point. The structure puts the system on the boundary; no parameter
was set to put it there.

### One customer in the layer above

![one customer above](figures/a2_fig8_one_customer_above.png)

Real intermediaries have another revenue source: they sell to the layer above.
Give the intermediary a single edge from the financial layer and the whole economy
is rescued.

| edges from the financial layer | household inflow | payroll funding ratio |
|---|---|---|
| 0 | **0.000** | 0.000 |
| 1 | 22.73 | 0.61 |
| 30 | 30.48 | 0.98 |

Zero collapses in all 36 tested configurations. One edge reaches 75% of the
eventual level. Thirty edges add a further 34%.

The economic reading is a firm-level K shape: an intermediary with one customer
in the financial layer survives, one with none dies, and it does not depend on how
much it sells but on whether it is connected at all.

**A caveat that belongs with this result rather than after it.** "Existence
dominates magnitude" has now appeared three times in this repository, with
strikingly similar saturation factors (x1.37 and x1.38). That is not three
independent pieces of evidence. A discontinuity at zero is unsurprising on its
own, because reachability is binary and an unreachable set is simply unreachable;
the construction guarantees the jump. What the runs supply is the size of the
step and the rate of saturation past it, and only those are results.

### Two things that turned out not to matter

Reported because they were expected to matter and did not.

- **Degree heterogeneity.** The heavy-tailed upward-leakage ratio, motivated by
  fixed costs falling hardest on the smallest firms, was expected to drive the
  contraction. The homogeneous control gives the same divergence to within 15%.
  What drives it is the layer structure together with the injection point.
- **The initial holdings distribution.** Spreading initial claims by in-degree
  and spreading them evenly give identical results.

---

## Stage A2c: cycle structure

Volume II of the source framework argues that a price field on an economy is
non-integrable, so local signals cannot be aggregated into a global view. That is
a structural, universal claim and **no simulation can establish it**. This stage
does not try. It measures, on runs stage A2 already produces, the object the
argument is about: cycle structure.

Two things are computable from a graph and a flow, neither requiring a price. The
first Betti number `E − V + C`, the number of independent cycles. And the discrete
Hodge decomposition of net flow into gradient, curl and harmonic parts.

**What is deliberately not done.** Decomposing net *claim flow* is not decomposing
a *price field*. The gradient part of a flow means the flow is explained by a
scalar node potential, a pressure. The gradient part of a price field means an
integrable price level. These are different objects sharing a name, and calling
one the other would be the substitution this project refused at stage A0. This
stage is an analogue, not an instance. Holes are also never punched by hand:
deleting edges and watching the rank fall verifies `E − V + C`, so that version
lives in the test suite labelled as a code check.

**The one modelling choice, stated rather than buried.** On a bare graph the Hodge
decomposition has only two parts. Splitting the cycle space into curl and harmonic
requires deciding which loops are filled in. The default fills every triangle,
which asserts that a three-way trading loop is not a structural hole. That is a
modelling decision, not a mathematical fact; `fill_triangles=False` reports the
two-way split and both are tested.

### Circulation grows, net displacement does not

![churn versus displacement](figures/a2c_fig9_churn_versus_displacement.png)

The gradient component of net flow is the part that actually moves claims from
somewhere to somewhere. Everything else returns to where it came from.

Over 600 rounds the total net flow grows by a factor of 97 while the gradient
component stays within a factor of 1.62. The ratio of circulation to net
displacement rises from 4.4 to 268.

That is the framework's claim about book velocity and topological displacement,
stated for the whole economy as one number instead of asserted about one stratum.

**A trap worth recording.** The gradient *share* falls from 5.1e-02 to 1.4e-05,
which reads like the displacing component vanishing. It is not: the magnitude is
flat and the denominator grew a hundredfold. The same applies to the harmonic
component, whose magnitude stays within a factor of 1.65 while its share falls by
four orders of magnitude. Every quantity here is reported as a magnitude
alongside its share, because reporting shares alone would have described a
dilution as a disappearance.

### Loops disappear with nothing deleted

![cycle rank collapse](figures/a2c_fig10_cycle_rank_collapse.png)

In the three-layer economy with the intermediary cut off from the layer above:

| | potential cycle rank | realized | surviving |
|---|---|---|---|
| 0 autonomous edges | 2846 | **83** | 2.9% |
| 1 autonomous edge | 2847 | 2230 | 78% |
| 30 autonomous edges | 2871 | 2557 | 89% |

The potential graph is identical throughout. No edge is deleted, no transaction is
forbidden, no price is refused. **97% of the independent loops stop existing
because nothing traverses them.** What the economy loses is not volume but the
number of distinct paths circulation could take, and 6 of 6 graph seeds agree.

### A limitation, kept as a criterion

Cycle rank is a binary count over edges. Proportional dynamics leave every edge
carrying something, so in the **two-layer** model the realized rank is flat at
1074 against a potential 1190 for the whole run: inert. It moves only where flow
genuinely stops, which is why the three-layer economy is where it says anything.

This is criterion A2c-7 rather than a footnote, so that a future refactor cannot
quietly drop it and leave the method looking more general than it is.

---

## Stage B2: the same claim, on twenty million real loans

Everything above is simulation. This is not.

The framework's structural claim is that the effective cost of holding a position
is a **two-index** field `P(a, g)`: the terms on which agent class `a` can hold
position `g`. A single price vector is the special case `P(a, g) = p(g)`, which
asserts that terms do not depend on who is transacting. If that special case held,
the field would be the gradient of a scalar on positions and every loop sum in it
would be zero.

That is testable without any topology at all. Fix the position and the date: same
census tract, same year, same lien position, same loan purpose, same occupancy
type, same dwelling category, same product. A gradient field predicts that every
applicant in such a cell faces **identical** terms, so the within-cell variance is
exactly zero. What is left over is the part no scalar on positions can reproduce.

```
Var(rate spread) = between-cell + within-cell
                   ^^^^^^^^^^^^   ^^^^^^^^^^^
                   what a         what no
                   position       position
                   index          index
                   explains       can explain
```

The sample is every conventional first-lien single-family home purchase
origination reported to HMDA for 2018 through 2025, all fifty states plus DC:
**20,071,900 loans in 1,103,962 cells.** The measured quantity is rate spread, the
loan's APR minus the average prime offer rate for a comparable transaction at the
date the rate was set, which is already stated against a common benchmark so that
a difference within a cell is a pairwise loop sum needing no further
normalisation. Every filter was fixed in
[`docs/b2_measurement.md`](docs/b2_measurement.md) before retrieval began, and
`data/raw/*_manifest.json` records the URL and timestamp of all 408 queries.

![within-cell dispersion](figures/b2_fig11_within_cell_dispersion.png)

**The within share is 0.7831 over all cells and 0.8480 over cells holding at least
twenty loans.** Integrability predicts 0.0000. The median cell's interquartile
range is 0.5257 points and its p90 minus p10 is 1.0774 points, against a
whole-sample standard deviation of 0.6625: **the spread inside a typical cell is
about as wide as the spread across the entire country.**

### The number was wrong first, and how it was wrong is the point

The first run reported 0.9750000458 overall, 0.9750000484 on principal residences
and 0.9749976781 on principal residences unrestricted. Three subsamples differing
by hundreds of thousands of cells, agreeing to six decimal places, at a round
number.

`0.975` is `39/40`, and it was literally that fraction. One filer had reported a
rate spread of `-9999997`, and that row happened to sit in a cell holding forty
loans. An isolated value `M` in a cell of size `k` contributes `M²(k−1)/(nk)` to
the within term and `M²/(nk)` to the between term, so the share it forces is
`(k−1)/k` — with `M` cancelling out entirely. The magnitude of the bad value never
appears in the answer; only the size of the cell it landed in does.

The arithmetic closes to six significant figures. `M²/n` predicts a total variance
of 6,181,523.5 against 6,181,526.7 observed. On the unrestricted sample, observed
total divided by `M²/n` is 4.000020, counting the offending rows exactly.

160 rows out of 20,071,900 are filer placeholders rather than interest-rate
differences: one filer writes `1111` into rate spread, interest rate and loan term
together; others use `99.99`, `100.0` or `123.0` as a ceiling sentinel. Excluding
them takes the total variance from 19,928,446 to **0.439**.

Two things make the exclusion non-load-bearing, and both are criteria rather than
prose. **B2A-6** recomputes the decomposition at exclusion bands of 10, 15, 20, 25,
30 and 50 points; the resulting shares span 9.6 × 10⁻⁴. **B2A-7** computes the same
decomposition on tie-averaged **ranks of the raw sample, excluding nothing at
all**, and gets 0.7654 and 0.8181. A rank is bounded by the sample size however
large the value is, and ties preserve the null exactly: under integrability every
loan in a cell reports the same spread, tied values receive identical ranks, and
the within-cell rank variance is exactly zero.

The corrected figures are **lower** than the artifact and are the ones that mean
something. The full arithmetic is in section 10 of the measurement document,
flagged as a post-result change, with the residual left unrounded.

The general lesson is recorded because it will recur: variance is not robust under
heavy-tailed contamination and a decomposition of variance inherits that. Every
future carrier gets the band sweep and the ranked analogue as standard, not as a
repair.

### A graded placebo, where one arm can fail and the other cannot

Dispersion at fixed position and date does not by itself show that the dispersion
is carried by the agent index. It could be something the cell keys failed to hold
fixed. The test needs a case where the agent index is suppressed **by rule** while
every position key stays identical.

Government-insured lending is that case. Conventional pricing runs an explicit
credit-graded surcharge grid. FHA replaces it with a flat insurance premium
schedule and VA with a funding fee that moves with down payment and prior use but
not with credit score.

The obvious prediction — FHA below conventional — has a duller rival that predicts
the same sign: FHA borrowers are a **narrower pool**, so `a` spans a shorter
interval and `P(a, g)` varies less over the realised sample even if the field is
exactly as non-integrable. Same sign, so FHA alone discriminates nothing.

**VA separates them.** Eligibility is service-based rather than credit-based, so
the pool is wide, while the price grid is flat. The two accounts disagree:

| | pool width | credit-graded grid | pool-width account predicts | agent-index account predicts |
|---|---|---|---|---|
| conventional | wide | yes | high | high |
| FHA | narrow | no | low | low |
| **VA** | **wide** | **no** | **high, near conventional** | **low, near FHA** |

![graded placebo](figures/b2_fig12_graded_placebo.png)

**Conventional 0.8480, VA 0.6666, FHA 0.4757.** VA lands nearer FHA. The
pool-width account is rejected.

The gap needs a scale. The conventional sample was split at random twenty times
and the same difference computed between halves, where the true value is zero by
construction: **the largest such gap is 0.0014.** The conventional-VA gap of 0.1814
is 130 times that, and 0.0855 in the ranked version is still 61 times it.
Restricting all three to the 409,181 tract-years common to every programme widens
the gap to 0.1944, so geography was masking it slightly rather than producing it.

All four pre-registered predictions passed, and the directions, the margin and the
null were fixed in section 8.1 before an FHA or VA row was retrieved.

### Two things found afterwards, kept separate because they were not predicted

The strongest surviving objection was that a VA cell needs twenty purchase loans in
one tract-year to qualify, which in practice means a tract near an installation,
where borrowers may be alike in pay grade and tenure. That would reintroduce the
narrow-pool story one level down. Lowering the cutoff from 20 to 5 takes VA from
24,880 cells to 157,807 — far past any installation effect — and moves its share
from 0.6666 to 0.6748. Raising it to 100 leaves 1,652 cells and gives 0.6322. The
objection predicted a large move and the observed move is 0.043 against a gap of
0.18. It fails. FHA, by contrast, moves three times as far over the same sweep,
which is what a genuinely narrow pool looks like.

Section 8.1 registered no direction for FHA against VA and said the outcome would
be reported and not interpreted. It came out at −0.1909, and the three programmes
then read as a design with one cell missing:

| | wide pool | narrow pool |
|---|---|---|
| **graded grid** | conventional 0.8480 | *(no programme)* |
| **flat schedule** | VA 0.6666 | FHA 0.4757 |

The pricing channel is 0.1814 and the pool-width channel is 0.1909; they are
close in magnitude and together span the whole distance. **This reading is
post-hoc**, additivity is assumed rather than shown, and it cannot be shown without
the fourth cell — which no programme occupies, because programme rules bundle who
may enter with how they are priced. It is stored under `post_hoc_not_pre_registered`
in the result record for that reason.

One more gradient appeared once the artifact was cleared. Within-share by occupancy
runs **principal residence 0.8289, second residence 0.6155, investment 0.3482.**
Investment property is underwritten on the asset — debt service coverage, loan to
value, rental income — so the lender is pricing the dwelling and `P(a, g)`
approaches `p(g)`. Owner-occupied lending is underwritten on the borrower. The
strength of non-integrability rises monotonically as the object being underwritten
moves from the asset to the person, which is a prediction the framework was not
built to produce.

### What stage B2 does not establish

It does not attribute the dispersion. HMDA's public file **redacts credit score**,
so this shows that terms disperse at fixed position and date without saying which
borrower attribute carries it. Non-integrability requires a non-zero loop sum; it
does not require the loop sum to be explained.

It is a lower bound. HMDA records financed purchases only, so all-cash buyers — who
face no financing term at all — are absent, and they are most absent in exactly the
markets where the pattern is strongest. The censoring runs against the claim.

---

## Stage B1: the number above is a cohomological quantity

Stage B2 computes a variance decomposition over a **partition**. There is no graph
in it. Calling the difference between two borrowers in one cell a "loop sum" was,
until this stage, borrowed authority: a loop of length two in a set with no edges
is not a loop.

So one of two things had to be true. Either the partition result is a shadow of a
cohomological statement, in which case the topological vocabulary is decoration and
should be dropped from the empirical claim; or it is a genuine instance, in which
case it must be possible to name the cycles, the graph and the weights.

It is the second, and the construction is short. [`docs/b1_theorem.md`](docs/b1_theorem.md)
carries the proofs.

**Enlarge the space.** Positions alone are the wrong domain: there the field is not
one cochain but a family indexed by agent, and "the family disagrees with itself"
is not a statement about any cochain's exactness. Put the agent index into the
space. `Γ = G □ H` has a vertex for each (agent class, position). Position edges
`(a,i)–(a,j)` carry agent `a`'s log cost ratio. Agent edges `(a,g)–(b,g)` carry
**zero**, because a position is the same position whoever holds it.

Then there is a four-cycle:

```
(a,i) ──w_a(i,j)──► (a,j)          sum = w_a(i,j) − w_b(i,j)
  ▲                    │
  │ 0                  │ 0          non-zero exactly when two classes
  │                    ▼            face different terms on one transition
(b,i) ◄──w_b(j,i)── (b,j)
```

**Theorem 1** makes that an equivalence: a single scalar price vector on positions
exists **iff** the cochain is exact on `Γ` **iff** every cycle sums to zero **iff**
every `w_a` is exact and they all coincide. The proof uses no equilibrium concept,
no continuity and no rationality assumption. One non-zero four-cycle is enough to
prove no such vector exists.

**Theorem 2** splits the cycle space into slice cycles and squares. Agent edges
carry zero, so agent cycles vanish identically and the obstruction lives in exactly
two places with distinct readings:

| summand | non-zero means | who can observe it |
|---|---|---|
| slice cycles | one agent faces arbitrage in their own opportunity set | one agent, several positions |
| squares | two agents face different terms on the same transition | many agents, one transition |

**Theorem 3** is the one that changes what stage B2 was. For a cell of `k` agents
with values `x₁…x_k`, the mean squared four-cycle sum over ordered pairs is

```
(1/k²) Σ_{p,q} (x_p − x_q)²  =  2 · Var(x)
```

so the within term of the B2 decomposition is exactly half the size-weighted mean
squared holonomy. **The within share is the fraction of the observed field that is
holonomy rather than potential, in `L²`.** Stage B2 did not measure a proxy. It
measured the quantity.

![squares and the identity](figures/b1_fig13_squares_and_identity.png)

Criterion **B1-6** checks this the slow way on the real sample: 500 HMDA cells,
four-cycles **enumerated** rather than differenced, against the variance the B2
code path already reported. Worst relative error per cell `1.07e-15`, aggregate
`1.64e-16`. Evaluating a closed form and comparing it to itself would establish
nothing, which is why the enumeration is there.

**What this settles about the next carrier.** By Theorem 2, mortgage data reaches
squares and nothing else — a borrower is observed at one transition, so no sample
size produces a slice cycle. Covered interest parity deviations are the opposite
shape: one dealer, several positions, a loop that closes. FX is therefore not a
second opinion on the mortgage result but **the other summand of the cycle space**,
and the mortgage carrier cannot reach it for structural reasons.

**What it assumes.** Agent edges carry zero only where the position trades at one
price independent of who holds it. A dwelling does. A 3% mortgage originated in
2021 does not, because it cannot be assumed: the agent edge is absent, `Γ`
disconnects, and the square is not a cycle. That is why loop B has to argue from
the hole rather than from the holonomy, which the setup document asserted and this
one derives. If agent edges carry a small non-zero weight instead, the existence
conclusion survives untouched and only the attribution does not.

**What it does not do.** The Hodge decomposition in `topology.py` builds 2-cells
from triangles, which is right for A2c's clique complex and wrong for `Γ`, whose
natural 2-cells are squares. Until a square complex is built, this stage claims a
gradient-versus-non-gradient split and no finer one. Flagged rather than papered
over, because the curl-versus-harmonic split is the more interesting question.

---

## What the model assumes

Stated plainly, because the results follow from these and a reader should be
able to attack them directly rather than reverse-engineer them from code.

**Load-bearing.** The financial layer has no discretionary edge into the
production layer. Its spending can land only inside itself. The single downward
connection is a wage bill, modelled separately because it is set by hiring
decisions rather than by how much anyone chooses to consume. Collapsing the two
would put the conclusion of the left panel into its premise.

If you think this zero is too strong, do not argue about it. `Adjacency.
with_downward_edge(w)` opens it, and the right panel reports exactly what
happens across the full range. That comparison is the deliverable of this stage.

**Also assumed.**

- Four strata. Under the source-faithful preset: 49 agents holding 10%, 40
  holding 30%, 10 holding 30%, 1 holding 30%. The last three come from the
  framework; the bottom 49 is our explicit completion of a residual it leaves
  implicit, and dropping it would have flattered the result. Under the DFA preset
  the strata are the published percentile groups.
- Spending is a propensity on holdings, not a fixed amount. Retention rate is
  then `1 - propensity`, which is what the source means by a rate of exit from
  cross-layer circulation rather than a hoarding rate.
- The production layer's outflow exceeds its downward inflow, by 2.214x under the
  source preset and 2.368x under the DFA one. **This is a parameter, not a
  result.** The stage traces what follows from a drained layer and does not claim
  to derive the shortfall. The wage bill that sets it is not calibrated under
  either preset; it is swept instead.
- The derived-demand elasticity is a free parameter swept from 0 to 1.2, and the
  sweep extends past unity deliberately. Employment adjusts in lumps, and both
  the framework's account and the standard derived-demand argument imply a fall
  in final demand is amplified rather than damped on the way into payroll. Where
  the boundary falls is the result, not the assumption.
- Claims and resources start one-to-one; resources are fixed with no real
  growth.

**Deliberately absent.** Credit creation, default, prices beyond a single index,
any network finer than stratum-level adjacency, and cross-layer bidding for a
shared resource pool. That last one matters: asset inflation squeezing the
production layer is a real mechanism and it is in the source framework, but
modelling it needs a price system with cross-layer asset markets. Inventing a
deflator here to get the result earlier would be using formalisation to endorse
a conclusion instead of checking it.

**A0 therefore reports claims, not real resource allocation.** That is a
limitation, and it is the reason stage A3 exists.

---

## What this is not

- Not a forecast. Nothing here predicts the timing of anything.
- Not *fitted* to data. Published levels are substituted directly into the model
  and nothing is estimated from a target. Stage A1 is the first stage where the
  model is asked to match a series.
- Not a claim that the standard stylised facts of the agent-based macro
  literature are reproduced. Most of them are reproduced by models with no
  layered structure at all, so reproducing them would carry no differential
  information. They are an entry ticket, reported in an appendix at stage A3,
  and they are not used as criteria here.
- Not a claim that the adjacency matrix or the wage bill are measured. They are
  the two places where the model is still assumption, which is why both are swept
  rather than defended, and why obtaining real adjacency data is the top item in
  `data/SOURCES.md`.

---

## Running it

```bash
git clone https://github.com/<user>/monetary-topology
cd monetary-topology
pip install -e ".[dev]"

python scripts/run_all.py            # lint, tests, every stage, one digest
python scripts/run_all.py --quick    # lint and tests only
python scripts/run_all.py --slow     # adds A6's ratchet, about twenty-five minutes
python scripts/run_all.py --b2       # adds the stages needing fetched data
python scripts/render_results.py     # regenerates RESULTS.md from results/*.json
```

`run_all.py` is the entry point. It prints a dozen pasteable lines: one per
stage, with its pass count, its exit code and its wall time, and a named line for
every criterion that failed. Criteria registered as failing carry the reason
inline, so a reader can tell a known negative from a regression without opening
anything. Individual stages still run on their own, for example
`python experiments/a0_retention.py`, and take `--rounds N` and `--seeds N`.

Every experiment script exits non-zero if a live criterion fails, so every
published claim is re-checked on each commit rather than trusted.
`.github/workflows/ci.yml` runs lint, the test suite, the stages that need no
fetched data, and a check that `RESULTS.md` matches what the code currently
produces. That last check is a byte comparison, which is why the rules in
`CLAUDE.md` about wall-clock content, float formatting and machine-dependent
values apply to anything a criterion writes into its detail string.

Results are reproducible for a given seed, and every qualitative finding above
was verified to hold across seeds 0-19: the spending-sweep spread is exactly 0.0
in all twenty, the churn factor is 15.0 in all twenty, and the edge-opening jump
ranges from x1.89 to x2.01.

---

## Repository layout

```
src/monetary_topology/   21 modules. The ones a reader starts from:
  config.py        all parameters, with sources and justifications
  economy.py       the block model (A0)
  network.py       the graph model and the intermediate layer (A2)
  topology.py      incidence operators, Betti number, Hodge split (A2c)
  asset.py         the asset price channel and its gate (A3)
  mechanisms.py    the four competitors and the demographic layer (A4)
  redistribution.py  the levy, the rebate and the frontier ratchet (A6)
  directed.py      one-way edges, friction and index (B4)
  calibration.py   the two presets, with series IDs and citations
  variants.py      config copying, so a sweep cannot re-default a field
experiments/     29 scripts, one per stage or diagnostic. A stage script
                 writes results/<name>.json; a diagnostic writes nothing and
                 says so in its first line
scripts/
  run_all.py           lints, tests, runs every stage, prints one digest
  render_results.py    regenerates RESULTS.md from results/*.json
tests/           25 files. Naming follows the stage, so `test_a4_*.py` are
                 A4's guards and each asserts one claim its docstring states
figures/         committed; they are the artefact
results/         committed; machine-readable run records
data/            not committed. SOURCES.md records provenance
```

No notebooks. Every result is produced by a script that runs start to finish
with no hidden state, and every parameter that affects a published figure is
declared in `config.py` where it can be read without reading the simulation
loop.

### Two invariants enforced in code

```python
# economy.py, every round. Raises on violation.
assert abs(claims_after - claims_before) <= 1e-9

# tests/. The identity behind "the rise in M/R equals cumulative retention".
np.testing.assert_allclose(h.issuance[1:], h.retention[:-1], atol=1e-9)
```

Stock-flow consistency is an assertion in the main loop rather than a check
performed afterwards. If it fails, the run stops and no figure is produced.

---

## Roadmap

Two tracks, run in parallel. They share no code because they answer different
kinds of question.

**Track A — distribution dynamics.** Computational claims: whether a support set
contracts depends on parameter magnitudes and cannot be settled structurally.

| stage | subject | status |
|---|---|---|
| A0 | retention and allocation | **complete, 9/9**; no separate document, see [RESULTS.md](RESULTS.md) |
| A0b | derived demand on the downward edge | **complete, 6/6 under both presets**; no separate document |
| A2 | support-set contraction, and the intermediate layer | **complete, 8/8 over 12 graph seeds**; no separate document |
| A2c | cycle structure of the realized graph | **complete, 7/7**; no separate document |
| A3 | **the asset price channel** | closed, **3/4 live, 1 void, 2 diagnostic**, [`docs/a3_asset_channel.md`](docs/a3_asset_channel.md) |
| A3b | the construction the channel opens from | complete, [`docs/a3b_initial_construction.md`](docs/a3b_initial_construction.md) |
| A3c | which parts of A3 are load-bearing | complete, A3-8 **void**, [`docs/a3_restated.md`](docs/a3_restated.md) |
| A5 | reachability against participation | **2/6**, [`docs/a5_reachability.md`](docs/a5_reachability.md) |
| A6 | the cost of the siphon | complete, [`docs/a6_siphon_cost.md`](docs/a6_siphon_cost.md) |
| A4 | four competitors on the causal primitive | ran, **3/4 live, 2 void**; the discriminant is one of the voids, see below, [`docs/a4_causal_primitive.md`](docs/a4_causal_primitive.md) |
| A7 | continuous connectivity | **run, both legs**, eleven verdicts, [`docs/a7_continuous_c.md`](docs/a7_continuous_c.md) §6 to §15. The stage's own result is a negative one: A3-8's divergence is a property of the sparse graph and does not survive a 34% thickening in any direction |
| A1 | default waterfall, calibrated to delinquency cross-sections | A1 superseded by A1b; A1b, A1c and A1d have run, see [RESULTS.md](RESULTS.md) and [`docs/a1_prereg.md`](docs/a1_prereg.md) |

**A3's two failures are reported rather than repaired, and they are different
kinds of failure.** A3-5 asks whether the gate binds at the high tier and comes
back void rather than negative: opening the high tier is a bitwise no-op in the
current calibration, because the tier allocates fully at the opening and no
production-layer node can reach it even at a soft gate, so at that tier the
exclusion is a price wall and not a hole and there is nothing for a gate
criterion to measure. A3-6 is a real negative. It asks whether a stock exists
and finds the holding population is 15.8 nodes of 200, none of them in the
production layer.

**A3-6 was also why A4 was blocked, and A4 has since run and answered it a
different way.** A4 sets four competing accounts against each other on wealth,
and A3-6 says the wealth is upstairs: sixteen nodes of two hundred, all in the
financial layer. The plan had been for A4 to inherit that stock. It does not.
[`docs/a4_causal_primitive.md`](docs/a4_causal_primitive.md) §10.4 rules that A4
keeps the plain network and takes its stock from issuance instead, because the
population A3's channel could hand it is that sixteen and no more.

**A4 ran, and its discriminant could not be computed.** Not "failed": three of
four live criteria pass and the two voids are voids on grounds registered before
the run. The amplification ratio `A(X)` compares a competitor's effect with
connectivity on against its effect with connectivity off, and no competitor is
readable in both arms. Inheritance and assortative mating transmit dispersion
without creating any, and the complete graph is an attractor at a Gini of
`0.0071` reached in five rounds from any opening, so on that arm they have
nothing to transmit. Education and capital returns create their own dispersion
and are invisible on the stratified arm, where twenty nodes hold `99.7%` of the
stock and any agent-level mechanism moves about `0.3%` of it. One of the two
terms of every ratio is therefore a reading of the graph draw.

Two repairs were registered in §11 before either was run, and both of the
falsification conditions written down with them fired. Measuring on the
production layer alone relieves the Gini ceiling by a factor of six and a half
and still leaves education inside the noise floor. Measuring a transmitting
mechanism on top of a generating one lifts the complete-graph denominator six to
eight fold and still yields no sign-stable cell once the household pooling rule
is set to settle at generations rather than every round. That last control
matters on its own: at the registered rule, ninety-nine point six percent of what
inheritance and assortative mating do on the stratified arm is a household
straddling the layer boundary and acting as a zero-cost conduit across it, not
the channel being measured.

**What A4 does establish is A4-2 and A4-6.** With every competitor off and every
agent identical, switching on nothing but the access structure takes the Gini
from `0.00711` to `0.93673`. And the matching rule, which reads holdings and is
guarded in code against seeing the layer label at all, pairs across the layer
boundary `16.1%` of the time with connectivity on against `17.8%` with it off,
where uniform random gives `18.1%`, at five of five seeds. Connectivity does not
prevent anyone from marrying anyone. It arranges the holdings so that a rule
which never mentions layers ends up respecting them.

**A7 is what A4's failure points at.** The two arms of a binary `C` are not two
settings of one economy, they are two economies with different state, and a ratio
between them measures the state difference as much as the mechanism difference. A
continuous `C` replaces that ratio with a slope along a path, which does not need
both endpoints live at once. The availability check is done and the continuum is
constructible: interpolating by edge addition takes the centrality dispersion from
`0.161` to `0.000` monotonically with no cliff, the layer gap closes with it
rather than surviving it, and both endpoints are exact rather than limits. It also
lets `C` move one thing at a time, which the binary switch does not: `uniform_access`
collapses the adjacency, the payroll incidence, the routing, the propensities and
the opening holdings together, and the design notes say so.

**A7 is now pre-registered and has not been run.** [`docs/a7_continuous_c.md`](docs/a7_continuous_c.md)
files one registration with two legs, because the holonomy is not computable on
A4's carrier: the loop sum is defined on the `terms` matrix, which lives on
`A3Model`, while `A4Model` subclasses `Network` and has no edge field. Leg A7-A
runs on the A3 carrier and measures `s -> H1 -> D`, where the content is that
A3-8 already removed the same holonomy once with a parameter (`kappa_pay = 0`,
graph fixed) and this removes it with the topology instead, with every kappa left
alone. Leg A7-B runs on the A4 carrier and replaces `A(X)`'s cross-arm ratio with
a slope, scoring `E` and `K` on `log(1/HHI)` and reporting `I` and `M` without
scoring them: the stock those two transmit runs from `28.06%` to `0.00%` of a
generation along the same axis, in the same direction as the amplification the
leg would be claiming, while `E` and `K` are compressed the other way by the Gini
ceiling that section 11.3 already measured. No criterion reads the whole grid,
because A4-1 measured the complete graph to be an attractor and its zero is
overdetermined. The construction parameter is `s`, it runs against `C`, and the
`s = 1` endpoint is not A4's `C = 0` arm.

**A3 has been redefined and it is no longer a merge.** The original plan made it
an integrated simulator that combined the earlier stages. That is now the wrong
target. Stages A0 through A2c measure claim circulation and report levels: a layer
drains, a support set contracts, loops stop being traversed. None of them can
produce a *widening gap* between agents who began level, because none of them has
an asset whose value responds to where claims accumulate.

That channel is where compounding comes from. Claims pile up in the financial
layer, the financial layer bids on assets, holders gain and non-holders are priced
out of entry, and the agents who could not enter at the start cannot enter later
either. The source framework describes this directly, and
[`docs/b1_setup.md`](docs/b1_setup.md) shows why it is load-bearing rather than
decorative: with an asset, a per-period loop sum `δ` opens a gap of `exp(Tδ)`, and
the framework's settlement ratchet turns out to be its non-integrability read at a
different horizon.

So A3 is one mechanism, not four glued together, and the same discipline applies as
before: with the asset channel switched off it must reproduce A0 through A2c
exactly, and those stages remain the control that the channel is measured against.

A0b changes what A1 needs. With a fixed wage bill the production layer settles,
and a default model bolted onto a settled layer can match a level but not a
dynamic. With derived demand the layer has a genuine downward trajectory whose
speed is governed by one parameter, which is the driver a default cascade
requires. Two DFA figures are already recorded in `calibration.py` as A1's
targets: the bottom half of the distribution holds 51.8% of all consumer credit
(`WFRBSB50211`) against 2.5% of net worth.

A3 is gated deliberately. A model with four layers, exhaust valves, quasi-money
creation and a default cascade has enough freedom to produce nearly any output.
Stages A0 through A2 exist so each mechanism carries two or three parameters and
a reader can verify by hand that a result is not an artefact of tuning.

**Track B — non-integrability.** Structural claims: the assertion is that a
global object does not exist, which is universal and cannot be established by
simulating instances.

| stage | subject | status |
|---|---|---|
| B1 setup | fixing the field so the claim is not vacuous | **complete**, [`docs/b1_setup.md`](docs/b1_setup.md) |
| B2 design | pre-registration, filters, falsifications | **complete**, [`docs/b2_measurement.md`](docs/b2_measurement.md) |
| B2 loop A | dispersion at fixed position and date | **complete, 7/7** on 20,071,900 loans |
| B2 placebo | conventional against FHA and VA | **complete, 4/4** on a further 8,066,085 |
| B1 theorem | is the partition result a case of the cohomological claim? | **complete, 7/7**, [`docs/b1_theorem.md`](docs/b1_theorem.md) |
| B2 loop B | same dwelling, different entry vintages | **complete, 4/4**, [`docs/b2_loop_b.md`](docs/b2_loop_b.md) |
| B2 placebo validation | is the VA pool actually wide? | **6/9**, the premise survives, [`docs/b2_placebo_pool_width.md`](docs/b2_placebo_pool_width.md) |
| B3 | CIP deviations: the other summand of the cycle space | complete, [`docs/b3_cip_slice.md`](docs/b3_cip_slice.md) |
| B4 | the directed theorem: what survives one-way edges | **complete, 8/8**, [`docs/b4_directed_edges.md`](docs/b4_directed_edges.md) |
| B5 | Argentina, and what the April 2025 intervention did to the agent index | squares **5/5**, zero calibration **2/2**, parallel trends **1/2**; two source audits returned REJECT, [`docs/b5_orphan_prereg.md`](docs/b5_orphan_prereg.md) |
| B6-A | reachability typing inside one central bank's own table (Cuba) | ran, the `H1` arm is not in this half, [`docs/b6_cuba_prereg.md`](docs/b6_cuba_prereg.md) |
| B7 | matrix rank of the cell-by-class interaction on 16m loans | **the rank-2 headline is withdrawn**; the cross-fold estimator then returns **rank two on the corrected diagonal**, a tilt and a bend, at 1.5% of the withdrawn magnitude, [`docs/b7_interaction_rank.md`](docs/b7_interaction_rank.md) §11 |
| B8 | the slice summand on a household carrier, from loan modification | pre-registered, [`docs/b8_fannie_slice.md`](docs/b8_fannie_slice.md) |
| B9 | the measured zero, and the path share | [`docs/b9_zero_holonomy.md`](docs/b9_zero_holonomy.md) |
| B10 | Freddie as a carrier: availability and the download ruling | [`docs/b10_freddie_availability.md`](docs/b10_freddie_availability.md) |
| square complex | curl against harmonic on `Γ` | **withdrawn**, see B1 §12 |

**Three of those rows are newer than the narrative that follows them**, which was
written when loop B was the next thing. B3 has since reached the slice summand
that Corollary 2 says no volume of mortgage data can touch; B4 removes the
standing prohibition on directed agent edges and replaces it with a narrower one,
that a carrier with a bid-ask spread may report `S − S'` and never a single
orientation; and the square complex is not merely unbuilt but **withdrawn**,
because filling the squares of `Γ` leaves the harmonic component identically zero
on every field this project runs, so the refinement it would deliver is an
identity dressed as a measurement.

**The placebo validation row exists because a premise was doing work unmeasured.**
The graded placebo's load-bearing comparison is conventional against VA, and it
rests on VA's borrower pool being as wide as conventional's. That was argued from
programme rule and never looked at. It now has been, on the borrower-capacity
fields the retrieval kept: at fixed position the VA pool is 97.7% as wide as the
conventional pool on the tail-insensitive measure, and wider than FHA's on every
measure tried. Three criteria fail and none of them touches that comparison.

**The B1 theorem was taken before any further retrieval, and it changed the
ordering that follows it.** The question it settled was whether stage B2 had
exercised the framework's machinery at all: loop A's decomposition runs over a
partition rather than a graph, so until Theorem 3 the honest description of the
result was "an analysis of variance we believe is related to a topological claim."
That description is worth little, because conditional dispersion in mortgage
pricing is already documented and a framework that re-derives it has contributed a
vocabulary rather than a result.

Theorem 3 shows the within share **is** the `L²` norm of the square component,
halved, and on this carrier the square component is the whole non-exact part
because the harmonic one is identically zero
([`docs/b1_theorem.md`](docs/b1_theorem.md) §12). Same number, different object,
and only the second is something the
framework can be judged on. Getting FX data first would have risked measuring the
wrong thing entirely — a mistake this project already made once on paper,
conflating carry returns, which are compensation for bearing risk, with
covered-parity deviations, which are the loop sums that actually fail to close.

Theorem 2 then reorders what remains. Mortgage data reaches squares only, and no
sample size changes that, so **FX stops being a robustness check and becomes the
only available carrier for the other summand**. Loop B goes first regardless: it
needs no retrieval, FHFA publishes the vintage shares as aggregates, and Theorem 1
has just shown its disconnection argument to be a structurally different claim
rather than a weaker version of the same one.

The working approach is discrete rather than smooth. On a finite graph, curl is
a sum around a cycle, the cycle space has dimension `E − V + C`, and the first
cohomology is a rank computation on the incidence matrix. The discrete Hodge
decomposition splits any flow into gradient, curl, and harmonic parts — which is
exactly the three-way split the argument needs, and it is computable on real
input-output data. The headline quantity is one scalar: what fraction of an
observed price field is integrable.

The first task in Track B is not a proof. On a single-currency price vector,
integrability holds **by identity**: writing `R_ij = p_j / p_i` makes every loop
sum zero as a matter of notation, so a theorem about that field would be a theorem
about the empty set. [`docs/b1_setup.md`](docs/b1_setup.md) fixes the object
instead: the field is the *two-index* effective cost `P(a, j)`, the terms on which
agent class `a` can obtain `j`. A single price vector is the special case where
terms do not depend on who is transacting, which is an assumption about an economy
rather than a description of one. That document also records a correction: the
obvious rent-versus-own example is currently false in the direction usually
assumed, and why the dispersion of the loop sum is better evidence than its sign.

What to measure is fixed in
[`docs/b2_measurement.md`](docs/b2_measurement.md), written as a pre-registration
before any data is retrieved. Two loops, and the division between them is the
substance of the design.

**Loop A holds the date fixed.** Same quarter, same census tract, same lien, same
purpose, same occupancy: applicants receive different rates, and a cash buyer
carries no financing term at all. Position identical, date identical, market
identical, terms different by who is transacting. There is no finer position space
to retreat to, because the position was already held fixed. This is the loop that
establishes the field carries an agent index at all.

**Loop A is done and it passed**, 7/7 with the placebo at 4/4, on 28,137,985 loans
across three programmes. The result, and the artifact it had to be corrected for,
are in [the B2 section above](#stage-b2-the-same-claim-on-twenty-million-real-loans).

**Loop B holds the dwelling fixed and varies the entry date.** This is where the
magnitude is: FHFA's National Mortgage Database reports the share of outstanding
fixed-rate mortgages below 4% peaked at 65.1% in Q1 2022 and stood at 49.9% in
Q1 2026, against new originations at market. Roughly half the holders of the same
position face materially different terms from the other half.

**Loop B is done and it passed**, 4/4 over 53 quarters of FHFA's National
Mortgage Database. The bound on vintage dispersion is 0.8479 in 2026 Q1 against
loop A's 0.3363, and it exceeds loop A in 46 of 53 quarters. The registered
prediction most likely to fail was that the wedge predates the 2022 repricing;
the mean over the 36 quarters before 2022 is 0.4043, so the repricing raised it by
64% rather than creating it. **The larger number is the weaker evidence**, and
[the B1 section](#stage-b1-the-number-above-is-a-cohomological-quantity) is why:
loop A's figure is a holonomy and loop B's is a component separation, because a
below-market mortgage cannot be transferred and so no cycle closes.

Loop B alone would not have been enough, and the document says so. A critic can
answer it by saying the two owners hold different assets, a dwelling plus a 3%
contract against a dwelling plus a 7% one, and that is correct as stated: entry
date is a coordinate rather than an attribute of the holder. Loop B survives, but
only via the hole, since the 3% contract cannot be purchased and integrability on
a space you cannot move around in is vacuous. That argument is worth making and it
is second-order, so the paper leads with A.

The document also records what the public data cannot do. HMDA's loan-level file
carries rate spread but **redacts credit score**, so it establishes that dispersion
exists at fixed position and date without attributing it. Non-integrability needs
a non-zero loop sum; it does not need the loop sum to be explained. Attribution is
a separate and weaker claim, made with FHFA's credit-score-banded aggregates and
labelled as such.

A third correction is recorded rather than quietly fixed: **asset tier is not agent
class.** A landlord buying down-market units to rent and hold is a high-class agent
holding a low-tier asset, and pooling by price tier averages that landlord together
with the household that could reach no higher tier. HMDA's occupancy type separates
them, and every cell in the panel is crossed by it.

Finally the document fixes, in advance, the test separating a structural
per-period wedge from one episode of repricing, and eight observations that would
falsify the claim.

Track B needs no simulation output and does not wait on Track A. Stage A2c is
*not* part of it: measuring cycle structure on our own graph is description, and
only the same computation on real data would be a finding. A2c can motivate the
theorem's introduction; it cannot support it.

That separation held until B1. It no longer describes the whole repository: by
Theorem 3, stage B2's within share is a cycle-sum norm on a graph built from real
loans, so the cohomology is now exercised on data and not only on a simulation.
The A2c caveat stands as written, because it is about A2c.

---

## Provenance

These models formalise mechanisms from a longer framework document, *A
Topological Framework of Claims and Resources*, which is not part of this
repository. Where the framework and the implementation disagree, the
implementation is annotated: three of its settings were changed during
development because the first version was not faithful to the source, and the
comments in `config.py` say which and why.

The framework's own standard for a good theory is internal consistency,
portability across parameter regimes, explanatory reach, and prediction of
phenomena not used in its construction. This repository is an attempt to make
the first and the last of those testable rather than asserted. Where a criterion
fails, RESULTS.md says so.

## License

MIT. See [LICENSE](LICENSE).
