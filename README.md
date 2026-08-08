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

**Status: stages A0 and A2 complete, 29/29 criteria pass**, across two
independent parameterisations, one of them calibrated to published Federal
Reserve data, and across 12 graph seeds. See [RESULTS.md](RESULTS.md) for the
full record and [ROADMAP](#roadmap) for what is not built yet.

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

pytest                                       # 119 tests
python experiments/a0_retention.py           # figures 1-3, 9 criteria
python experiments/a0_derived_wages.py       # figures 4-5, 6 criteria x 2 presets
python experiments/a2_support_contraction.py # figures 6-8, 8 criteria
python scripts/render_results.py             # regenerates RESULTS.md
```

Every experiment script exits non-zero if a criterion fails, so every published
claim is re-checked on each commit rather than trusted. `.github/workflows/ci.yml`
runs lint, the test suite, all three experiments, and a check that `RESULTS.md`
matches what the code currently produces.

Optional arguments: `--rounds N`, `--seed N`. Results are reproducible for a
given seed, and every qualitative finding above was verified to hold across
seeds 0-19: the spending-sweep spread is exactly 0.0 in all twenty, the churn
factor is 15.0 in all twenty, and the edge-opening jump ranges from x1.89 to
x2.01.

---

## Repository layout

```
src/monetary_topology/
  config.py        all parameters, with sources and justifications
  economy.py       the block model (A0)
  network.py       the graph model and the intermediate layer (A2)
  calibration.py   the two presets, with series IDs and citations
  variants.py      config copying, so a sweep cannot re-default a field
  plotting.py      figure style
experiments/
  a0_retention.py           figures 1-3, criteria A0-1..9
  a0_derived_wages.py       figures 4-5, criteria A0b-1..6 under both presets
  a2_support_contraction.py figures 6-8, criteria A2-1..8
scripts/
  render_results.py    regenerates RESULTS.md from results/*.json
tests/
  test_a0_economy.py        25 tests
  test_a0b_derived_wages.py 26 tests
  test_a2_network.py        68 tests
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
| A0 | retention and allocation | **complete, 9/9** |
| A0b | derived demand on the downward edge | **complete, 6/6 under both presets** |
| A2 | support-set contraction, and the intermediate layer | **complete, 8/8 over 12 graph seeds** |
| A1 | default waterfall, calibrated to delinquency cross-sections | not started |
| A3 | integrated simulator | gated on A0-A2 |

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

The working approach is discrete rather than smooth. On a finite graph, curl is
a sum around a cycle, the cycle space has dimension `E − V + C`, and the first
cohomology is a rank computation on the incidence matrix. The discrete Hodge
decomposition splits any flow into gradient, curl, and harmonic parts — which is
exactly the three-way split the argument needs, and it is computable on real
input-output data. The headline quantity is one scalar: what fraction of an
observed price field is integrable.

Track B needs no simulation output and does not wait on Track A.

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
