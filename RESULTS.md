# Results

Kept by hand. The run records are in `results/*.json`; this file is the ledger
of what each station concluded and which of its criteria passed.

This file used to be generated, and the generator was retired on 2026-08-21.
The programme opened stations faster than the generator could be taught to
describe them, and keeping the two in step stopped being worth the maintenance:
by the end it could only render a reading that fitted into a criterion row, four
whole stations were missing from this file, and nobody found that out from
anything the machinery reported. A ledger that has to be told how to describe a
finding will keep the findings it was already designed for and lose the rest.

Failed criteria are listed alongside passing ones. A results file that records
only successes is the same kind of object as a statistic designed to look good,
and this project's own argument is about that kind of object.

**No generation date here on purpose.** Git already records when a file was
committed and by whom.

## A0b — derived demand on the downward edge

`rounds=800` `seed=7`

### source-faithful parameters

**6/6 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A0b-1  zero elasticity reproduces the fixed-bill model exactly | series identical to bitwise equality; the addition is a strict generalisation and cannot have changed the earlier results |
| PASS | A0b-2  a positive steady state exists below unit elasticity | minimum level over e <= 0.9 is 2.8544 |
| PASS | A0b-3  no steady state exists at or above unit elasticity | maximum level over e >= 1.0 is 3.513e-83 |
| PASS | A0b-4  the level falls monotonically in elasticity | from 16.9540 at e=0 to 1.474e-171 at e=1.2 |
| PASS | A0b-5  above the boundary, survival is linear in the autonomous share | max deviation from a line through the origin is below 1e-6 of the largest level, slope 16.9540 |
| PASS | A0b-6  a zero autonomous share above the boundary collapses | level at floor_share=0 is 9.741e-172 |

Derived quantities:

- `wage_bill` = 8.0000
- `flow_balance` = 2.2135

### Fed DFA Q1 2026 calibration

**6/6 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A0b-1  zero elasticity reproduces the fixed-bill model exactly | series identical to bitwise equality; the addition is a strict generalisation and cannot have changed the earlier results |
| PASS | A0b-2  a positive steady state exists below unit elasticity | minimum level over e <= 0.9 is 2.0910 |
| PASS | A0b-3  no steady state exists at or above unit elasticity | maximum level over e >= 1.0 is 1.024e-85 |
| PASS | A0b-4  the level falls monotonically in elasticity | from 12.7069 at e=0 to 6.429e-171 at e=1.2 |
| PASS | A0b-5  above the boundary, survival is linear in the autonomous share | max deviation from a line through the origin is below 1e-6 of the largest level, slope 12.7069 |
| PASS | A0b-6  a zero autonomous share above the boundary collapses | level at floor_share=0 is 4.283e-171 |

Derived quantities:

- `wage_bill` = 6.0000
- `flow_balance` = 2.3685


## A0 — retention and allocation

`rounds=400` `seed=7`

**9/9 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A0-1  targeted ratio flat while total ratio rises | tail sd of M_a/R_a = 3.597e-03, M/R drift = 8.0038, threshold = 4.002e-01 |
| PASS | A0-2  M/R monotone under endogenous issuance | min first difference = 0.000e+00 |
| PASS | A0-3  issuance equals lagged retention | max absolute residual = 0.000e+00 |
| PASS | A0-4  Layer 2 inflow flat across the spending sweep (propensity >= 0.05) | spread = 0.000e+00 over propensities [0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0], level = 17.700656 |
| PASS | A0-5  the same sweep moves Layer 1 churn by an order of magnitude | churn ranged 356.20 to 5338.97, factor 15.0 |
| PASS | A0-6  opening one downward edge raises Layer 2 inflow | inflow rose from 17.7007 at weight 0 to 48.3919 at weight 0.85, factor 2.73 |
| PASS | A0-7  edge response monotone | sequence = [17.701, 35.436, 36.281, 37.706, 39.047, 40.386, 42.928, 45.846, 48.392] |
| PASS | A0-8  production layer settles at the payroll edge rather than zero | settled inflow = 17.7007 against net downward wage flow 7.2000 |
| PASS | A0-9  issuance accumulates in the layer it was issued to | Layer 1 holds 0.9982 of all claims at steady state, from 0.7291 at t=0 |

Derived quantities:

- `flow_balance` = 2.2135
- `net_downward_wage_flow` = 7.2000
- `upward_leakage` = 0.4250

<details><summary>Parameters</summary>

```json
{
  "strata_counts": [
    49,
    40,
    10,
    1
  ],
  "wealth_share": [
    0.1,
    0.3,
    0.3,
    0.3
  ],
  "propensity_low": [
    0.88,
    0.87,
    0.5,
    0.5
  ],
  "propensity_high": [
    1.0,
    1.0,
    0.5,
    0.5
  ],
  "retention_rate": [
    0.06000000000000005,
    0.06499999999999995,
    0.5,
    0.5
  ],
  "adjacency": [
    [
      0.35,
      0.25,
      0.1,
      0.3
    ],
    [
      0.2,
      0.35,
      0.15,
      0.3
    ],
    [
      0.0,
      0.0,
      0.45,
      0.55
    ],
    [
      0.0,
      0.0,
      0.1,
      0.9
    ]
  ],
  "wage_bill": 8.0,
  "wage_source_shares": [
    0.0,
    0.1,
    0.3,
    0.6
  ],
  "wage_dest_shares": [
    0.45,
    0.55,
    0.0,
    0.0
  ],
  "issuance_rule": "endogenous",
  "issuance_gain": 1.0,
  "initial_claims": 100.0,
  "total_resources": 100.0
}
```

</details>

## A1 — the default cascade on crossed marginals (superseded by A1b; no level from this construction is a measurement)

**2/2 live criteria passed, 1 void**

| | criterion | detail |
|---|---|---|
| PASS | A1-1  zero calibration | 60 cells over 20 seeds and 24 periods in 3 arms, every rung exactly 0.000000. 3 arm(s) could not be built and are reported rather than scored: stratified, stratified:permuted, stratified:scf-tenure |
| VOID | A1-10 licence  the population size is an estimation setting | not tested: the main arm has no population at 10,000 households. stratum 0, mortgaged: the published debt takes 0.862 of the disposable, and a Beta with that mean cannot carry a dispersion of 0.250. Its concentration would fall to 1.552, which is two point masses at zero and one rather than a spread. The largest dispersion this mean supports is 0.231 |
| PASS | A1-11 free parameters within the registered bound | 6 free against 12: cost.commute_dependency=0.35, cost.access_penalty=1, population.dispersion=0.25, population.buffer_months=1, cost.grace_basket=1, cost.grace_rent=4 |

## A1a — the joint the SCF publishes, against the crossing A1 built

**Diagnostic. It registers nothing, gates nothing and feeds no criterion.** It
exists because A1's population is built by crossing marginals, income and the
basket from the CEX, consumer credit and mortgage debt by net-worth group from
the DFA, every household inside a wealth group carrying that group's average
debt, and two cells were then read off that construction as if they were data:
the permutation arm's next-9%-by-wealth households sitting in the bottom half by
income, and the main arm's bottom-half renters at 94 per cent of disposable.
Neither is a published group. Both are crossings, and a crossing that cannot
service itself is a statement about the crossing.

This replaces the crossing with the joint the SCF already publishes: the 2022
wave, 22,975 records, 131,306,389 weighted families, overall ownership 0.6605.

| quantity, from the SCF joint | bottom 50 | next 40 | next 9 | top 1 |
|---|---|---|---|---|
| consumer credit by wealth group | 8,964 | 11,507 | 10,011 | 15,950 |
| consumer credit by income group | 5,741 | 14,083 | 15,329 | 26,222 |
| income by wealth group | 56,724 | 124,243 | 465,852 | 2,137,290 |

Aggregates from the same joint: card 363.5bn, vehicle 968.7bn, mortgage
11.57tn, against Z.1's 5.073tn consumer credit and 13.821tn home mortgages. The
per-group consumer credit A1's construction assumes is carried in the record
beside these under `model_consumer_credit`, and the two are on different
denominators, so the record reports both and this file draws no ratio between
them.

Cells and the wealth-income copula are in `results/a1a_joint_probe.json` and
`data/processed/scf_joint_cells.csv`.

## A1b — the cascade on a measured population: the K shape holds ordinally, one rule covers every rung, and the representative arm is degenerate

**6/8 live criteria passed, 1 void**

| | criterion | detail |
|---|---|---|
| PASS | A1b-0 zero calibration, by removing the cause | income raised to cover each household's own obligations: every rung exactly 0.000000 over 24 periods |
| **FAIL** | A1-2  the order is an output | first default among 36,292 defaulting households: card 0.4214, auto 0.0660, shelter 0.3567 (rent 0.2488, mortgage 0.1079), basket 0.1558. Among the 32,547 not short at baseline: card 0.4426, auto 0.0662, shelter 0.3915. The manuscript's sequence is what fails here, not the code |
| PASS | A1-3  K shape, ordinally | mortgage 0.0027 < auto 0.0924 < card 0.1879. Over baseline: mortgage +0.0024, auto +0.0721, card +0.1249. Attached gate: cost_now names no class; every pair is the same rule applied to per-class attributes |
| PASS | A1-6  the subprime gradient | bottom 0.1438 against middle 0.0680, ratio x2.12. Published at 30 days on balances and reported only: 2000 5.33, 2019 5.85, 2024 5.58, 2025 5.40. The model is at ninety days, so the ratio is beside them and not against them |
| VOID | A1-7  the rent gradient | by net worth: bottom50 0.6577 (28,776), next40 0.3584 (2,888), next9 0.0000 (397), top1 0.1351 (37) [NOT monotone]. By income: bottom50 0.8129 (23,585), next40 0.1046 (7,581), next9 0.0000 (897), top1 0.0000 (35) [monotone]. Overall 0.6220 against SHED's 0.23, reported only: the source counts renters behind at some point in twelve months and this is sixty months of a model. Published by income band: 0.33/0.31/0.17/0.05. **The two readings of the registration disagree**, so this is reported on both and gated on neither. The source is banded by income and the model's strata are net worth, and A1 could not see the difference because it had one ranking |
| PASS | A1-9  the representative arm is degenerate | every rung of the collapsed household takes values in {0, 1} across all three tenures, which is Corollary 1 with a number attached: the difference between the arms is the population |
| PASS | A1-10 one parameter set across every rung | one rule, one attribute table, one grace table; every rung's pair is CARD 0.000/6, AUTO 0.117/3, RENT 0.250/4, MORTGAGE 0.083/12, BASKET 1.000/1 |
| **FAIL** | A1b-1 the delinquency gradient | LATE60 by net worth: bottom50 0.0847, next40 0.0163, next9 0.0022, top1 0.0026. Model over 6 sweep cells: seed 7x1 0.301/0.174/0.017/0.000  <-; seed 7x3 0.258/0.140/0.017/0.000  <-; seed 8x1 0.301/0.177/0.017/0.000  <-; seed 8x3 0.262/0.144/0.017/0.000  <-; seed 9x1 0.280/0.158/0.017/0.000  <-; seed 9x3 0.233/0.122/0.017/0.000  <-. Decreasing in every cell: True. Ordering matches the survey in every cell: False. Group sizes at 20,000 households: [9993, 7998, 1895, 114]. Including rent, reported only: 0.483/0.191/0.017/0.000. The target's smallest adjacent gap is 0.0004, which is what the ordering turns on |
| PASS | A1-11 free parameters within the registered bound | 5 free against 12: cost.commute_dependency=0.35, cost.access_penalty=1, cost.grace_basket=1, cost.grace_rent=4, population.buffer_months=1. A1 counted six; the service-share dispersion is measured here |

## A1c — the order inside a household: the sequence holds with 2 inversions of 1,142, and all 13 inversions are attributed to the release clause

**2/2 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A1c-1 the sequence holds inside a household | card_before_auto: 607 in order, 533 tied, 2 inverted, of 1,142 in scope; auto_before_rent: 449 in order, 526 tied, 2 inverted, of 977 in scope; card_before_rent: 523 in order, 1,080 tied, 9 inverted, of 1,612 in scope. 17,499 of 20,000 households are in scope for no pair at all, which is the population A1-2 quantified over and the size of the mismatch between the claim and its cross-sectional form |
| PASS | A1c-2 every inversion is attributed | 13 inversions: 13 attributed to the release clause, the later class unsavable in the period it was first missed while the earlier one was savable; 0 unattributed |

## A1d — the cascade on a measured cushion (liquid assets, no floor, and a matched twelve-month window; the top pair is below both sides' resolution and is reported rather than scored)

**7/9 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A1d-0 zero calibration, by removing the cause | income raised to cover each household's own obligations: every rung exactly 0.000000 over 24 periods |
| **FAIL** | A1-2  the order is an output | first default among 44,578 defaulting households: card 0.3068, auto 0.0704, shelter 0.1564 (rent 0.0965, mortgage 0.0599), basket 0.4664. Among the 39,492 not short at baseline: card 0.3163, auto 0.0741, shelter 0.1647. The manuscript's sequence is what fails here, not the code |
| PASS | A1-3  K shape, ordinally | mortgage 0.0069 < auto 0.0807 < card 0.1810. Over baseline: mortgage +0.0054, auto +0.0615, card +0.1404. Attached gate: cost_now names no class; every pair is the same rule applied to per-class attributes |
| PASS | A1-6  the subprime gradient | bottom 0.1345 against middle 0.0518, ratio x2.60. Published at 30 days on balances and reported only: 2000 5.33, 2019 5.85, 2024 5.58, 2025 5.40. The model is at ninety days, so the ratio is beside them and not against them |
| PASS | A1-9  the representative arm is degenerate | every rung of the collapsed household takes values in {0, 1} across all three tenures, which is Corollary 1 with a number attached: the difference between the arms is the population |
| PASS | A1-10 one parameter set across every rung | one rule, one attribute table, one grace table; every rung's pair is CARD 0.000/6, AUTO 0.117/3, RENT 0.250/4, MORTGAGE 0.083/12, BASKET 1.000/1 |
| PASS | A1d-1 the delinquency gradient, matched window | LATE60 by net worth: bottom50 0.0847 (886 of 1,857 families), next40 0.0163 (155 of 1,475 families), next9 0.0022 (11 of 694 families), top1 0.0026 (5 of 569 families). Scored pairs: bottom50/next40, next40/next9. Reported and not scored: next9/top1 (0.13 sigma, expected events 0.8). Model on the last 12 periods over 6 sweep cells: seed 7x1 0.067/0.042/0.004/0.003; seed 7x3 0.066/0.045/0.005/0.000; seed 8x1 0.067/0.044/0.004/0.003; seed 8x3 0.068/0.045/0.005/0.000; seed 9x1 0.059/0.041/0.004/0.003; seed 9x3 0.061/0.038/0.005/0.000. Decreasing on every scored pair in every cell: True. Ordering matches the survey on those groups in every cell: True. Group sizes at 50,000: [25310, 20078, 4322, 290]. Reported and never scored, the other three windows on cell one: first 12 periods 0.167/0.059/0.013/0.000; whole run at sixty days 0.244/0.125/0.013/0.017; whole run on A1b-1's any-miss rule 0.361/0.177/0.024/0.034; last window including rent 0.071/0.042/0.004/0.003 |
| **FAIL** | A1d-2 the rent gradient, on net worth | by net worth, sixty days: bottom50 0.5842 (28,776), next40 0.2562 (2,888), next9 0.0000 (397), top1 0.1351 (37) [NOT monotone]. Reported and not scored, by income: bottom50 0.7162 (23,585), next40 0.0877 (7,581), next9 0.0000 (897), top1 0.0000 (35). A measured cushion did not produce the monotonicity a label could not, so the non-monotonicity is a property of the data. docs/a1b_prereg.md section 8 has what the cells are made of |
| PASS | A1d-3 free parameters within the registered bound | 4 free against 12: cost.commute_dependency=0.35, cost.access_penalty=1, cost.grace_basket=1, cost.grace_rent=4. A1b counted five; population.buffer_months left the list when the cushion became a measurement rather than a choice |

## A2 — support-set contraction and the intermediate layer

`rounds=600` `seed=0`

**8/8 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A2-1  without issuance, volume and support move the same way | volume x0.87, support x0.729 |
| PASS | A2-2  with issuance, volume rises while support contracts | volume x44.87, support x0.402; production layer falls to 0.51% of all circulation |
| PASS | A2-3  the sign flip holds across graph seeds | 12/12 seeds flip under issuance, 12/12 agree without it |
| PASS | A2-4  a maximal propensity with no in-edge still terminates at zero | final holdings across 12 seeds, maximum 0.000e+00. Propensity is a property of the agent; reachability is a property of the graph, and only the second one decides |
| PASS | A2-5  the two-layer payroll channel never narrows | funding ratio 1.0000 |
| PASS | A2-6  H1: the three-layer payroll channel closes with the bill unchanged | funding ratio 2.571e-139 while the bill owed stayed constant and the elasticity was zero |
| PASS | A2-7  H2: three-layer at zero elasticity matches two-layer at unity | three-layer 3.2428e-138 against two-layer at e=1 7.8382e-66 and at e=0 17.4309 |
| PASS | A2-8  zero autonomous edges collapses; one rescues | 0 edges 3.243e-138, 1 edge 22.7300 (75% of the maximum), 30 edges 30.4821 |

## A2c — cycle structure of the realized graph

`rounds=600` `seed=0`

**7/7 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A2c-1  net displacement is flat while circulation grows | gradient magnitude stays within a factor of 1.62; total flow grows x97.1 |
| PASS | A2c-2  the churn ratio rises by an order of magnitude | circulation over net displacement rises 4.4 -> 268 |
| PASS | A2c-3  the harmonic component is diluted, not removed | magnitude within a factor of 1.65 while its share falls 2.18e-02 -> 8.59e-07. Reporting the share alone would have said it vanished |
| PASS | A2c-4  cycle rank collapses with no edge deleted | potential rank 2846, realized fraction 0.029, and the potential graph is identical throughout |
| PASS | A2c-5  one autonomous edge restores most of the loop structure | 0 edges 0.029, 1 edge 0.783, 30 edges 0.891 |
| PASS | A2c-6  the collapse and the rescue hold across graph seeds | 6 seeds: collapsed 0.023-0.029, rescued 0.744-0.862 |
| PASS | A2c-7  limitation recorded: cycle rank saturates when nothing dies | in the two-layer model the realized rank is flat at 1074 after the transient, against a potential 1190. Cycle rank is a binary count, so it moves only where edges genuinely stop carrying claims. It is informative in the three-layer economy and inert in the two-layer one, and this criterion exists to keep that on the record |

## A3

`rounds=300` `5 seeds`

**3/4 live criteria passed, 1 void, 2 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | A3-1  the closed channel reproduces A2 bitwise | largest absolute difference over 5 seeds and four series: 0.000e+00. Not a tolerance: anything but zero is a different model |
| DIAG | A3-2  a gap opens between agents who started level | entry pair, 5 either side of the allocation boundary: mean net worth ratio 9.1 against a floor of 2.0. **A floor and not a criterion**, demoted in §5.1: this is owning against not owning, which is a gap produced by owning rather than by the terms of owning, and it can be orders of magnitude wide while the loop sum is exactly zero |
| DIAG | A3-3  the gap compounds rather than levelling off | largest drift between a node's first and second half of trades, over 101 nodes with four or more: at machine precision, below `1e-10` against a threshold of `0.05`. **An assertion and not a criterion**, demoted in §5.1: `adjusted return = -log gamma` holds by construction, so this is a machine-precision reading of an identity and belongs in the test suite. It is printed because a non-zero value here would mean the identity had been broken |
| PASS | A3-4  the realised terms differential is the loop sum | mean cell-adjusted return, better group minus worse: +0.36536 against a holonomy of +0.37686 from the product graph, relative error 3.05% against 20%. Price cancellation observed, not assumed: the largest holonomy shift under unrelated prices is at machine precision, below `1e-10` |
| VOID | A3-5  the gate binds at the high tier, not at ownership | price frozen, so opening a tier is a gate change and nothing else. Gap as a difference of growth multiples, each node against its own opening claims: gates shut +107.30, low tier open +130.89, high tier open +107.30, against the registered split at 50% of shut, +53.65. Ratios for continuity with the runs recorded before the rescale: shut 12.85, low 870.62, high 12.85 frozen; low 4.00, high 178.31 with the price free. VOID per §6.3: opening the high tier is a bitwise no-op, because open_tiers never reaches resale, the high tier allocates fully at the opening, and no production-layer node can reach it even at the soft gate. At the high tier the exclusion is a price wall and not a hole, so there is nothing there for a gate criterion to measure |
| **FAIL** | A3-6  a stock exists, and A4's domain is exactly who holds it | median holder retains 13.8% of the transfer after 40 rounds against 50% required, and **3% of 79 holders clear the threshold**; a non-holder retains 0.1%, against 0.00% on the A2 carrier. **The holding population is 15.8 nodes of 200, of which 0.0 are in the production layer.** So A4's domain is 15.8 nodes and they are upstairs, which is a constraint on A4 and not a licence: four competitors that act on wealth, measured where the wealth is, describe stratification *within* that set and not the economy's. Threshold carried over from the median-node version, disclosed in the docstring |
| PASS | A3-7  non-overlapping windows agree in sign | better terms beat worse in [0,100): 100%, [100,200): 100%, [200,300): 100% of seeds. One window only would be a repricing |

## A3b

`rounds=300` `5 seeds`

Record with no criteria block, kept as evidence and named here so it is findable:
`results/a3b_construction.json`, the initial-construction run. It adjudicates
nothing, and no criterion anywhere reads it.

## A3 P-C

`rounds=300` `5 seeds`

**0/0 live criteria passed, 1 void**

| | criterion | detail |
|---|---|---|
| VOID | A3-8  removing the holonomy removes the divergence | state: **unstable**. Gaps against the null: both +23.2667, loop sum only +21.6714, gate only +1.4091, null +0.000e+00. Mean-cost drift at machine precision, below `1e-10`. Indistinguishable from zero across seeds: H0_only |

## A3 §16.1 step one — retention at every node, not two of them

**Diagnostic. It registers nothing and decides nothing. A3-6 keeps its
threshold, its domain and its verdict**, and nothing here is read into that
criterion. It exists because §16.1 makes a claim about a *shape*, that a one-off
transfer is retained in a step on whether the recipient holds an asset rather
than along a gradient in wealth, and the evidence for that shape was **two
points**: one holder statistic and one non-holder statistic. Two points cannot
tell a step from a steep monotone gradient.

Every node in the population is shocked separately, one full model run each,
five seeds, 1,000 nodes, horizon 40. The sharp comparison needs no threshold: the
poorest node that holds a unit against the richest node that does not. Under a
gradient the richer non-holder retains more; under a step the poorer holder does.

| arm | shock | boundary pair reads *step* | holder block contiguous | holder / non-holder median |
|---|---|---|---|---|
| registered | 150 | 3 / 5 | 1 / 5 | 0.1425 / 3.99e-05 |
| rent by holding | 150 | 3 / 5 | 1 / 5 | 0.1456 / 5.61e-05 |
| rent off | 150 | 2 / 5 | 0 / 5 | 0.3070 / 2.25e-03 |
| registered | 20 | 3 / 5 | 0 / 5 | 0.0825 / 3.88e-03 |
| rent off | 20 | **0 / 5** | 0 / 5 | 0.1716 / 8.64e-03 |

**The two-point statistic reproduces and the shape it was taken as evidence for
does not.** The holder and non-holder medians are 20 to 3,568 times apart in
every arm, which is the two-point reading. The boundary pair, which is the
comparison that actually separates a step from a gradient, comes out *step* in
**11 of 25 seed-arm cells** and *gradient* in the other 14, and in the rent-off
shock-20 arm it is gradient in all five. And **the holders are a contiguous block
in the wealth ordering in 2 of 25 cells**: holders and non-holders are
interleaved, so on this population the two shapes are not cleanly separable in
the first place.

**What this does not say.** It does not touch A3-6. It does not say the step is
absent in the world; it says the internal profile does not carry the step that
§16.1 wanted to take to external data, and that the evidence which looked like a
step was a comparison of two medians.

Nodes whose deviation at the shock round is zero are counted separately rather
than recorded as retaining nothing: "the transfer left no trace to measure" and
"the transfer was recaptured" are different events, and folding the first into
the second would manufacture the step this is testing for.

## A4 — the causal primitive (A4-4 could not be computed: no competitor is readable in both arms)

`rounds=300` `5 seeds`

**3/4 live criteria passed, 2 void**

| | criterion | detail |
|---|---|---|
| PASS | A4-1 null calibration: identical agents on a complete graph do not stratify | C=0 all competitors off, Gini 0.00711 against a ceiling of 0.02. Production layer 0.00714. Spread across seeds 0.00026. |
| PASS | A4-2 connectivity alone is sufficient | Gini 0.93673 against 0.00711, gap +0.92962 against a floor of 0.05, and the sign holds at 5 of 5 seeds. Production layer 0.59490 against 0.00714. |
| **FAIL** | A4-3 no competitor is a strawman | Each competitor alone with C off, Gini rise over the null against a floor of 0.02: I +0.00007, E +0.00932, K +0.00080, M -0.00006. Below the floor: I, E, K, M. The floor is in absolute Gini units and the C=0 control sits at 0.00711, so it asks each competitor for 2.8 times the control's whole value; the threshold is registered and is not moved on that account. Education's rise is 35.6 control-cell sd and still below it. |
| VOID | A4-4 connectivity is upstream | **Void on two independent grounds and not evaluated.** §7's table: A4-3 fails for 4 of four competitors, and a failed strawman floor makes that competitor's comparison void rather than favourable. §11.8's rule: A(X) is a ratio across the two arms and no competitor is readable in both, so one of its two terms is a reading of the graph draw in every case. Readable Gini cells: C=0/K/I, C=0/null/E, C=0/null/K, C=1/E/I, C=1/E/M, C=1/K/I, C=1/K/M, C=1/null/I, C=1/null/M. Ratios whose per-seed sign happens to agree: I\|K = 440.7 (denominator -0.00042), and each rests on a denominator inside two control-cell sd, so the agreement is five draws landing the same way rather than a quantity. |
| VOID | A4-5 the update order does not decide it | **Void: A4-4 has no result for an ordering to preserve or overturn.** What was run in its place, on all four combinations of channel order and event order, and is reported: the set of cells clearing §11.2's floor, and the three verdicts that do not pass through A(X). Registered set has 35 cells; orderings whose set differs: capital_first/match_first (12 cells differ), pooling_first/inherit_first (2 cells differ), pooling_first/match_first (6 cells differ). A4-1, A4-2 and A4-6 evaluated on every alternative run; orderings where any of the three flips: none. |
| PASS | A4-6 caste is derived from holdings, not read off the layer | Matching reads holdings and never the layer label. Cross-layer pairing rate with M on: C=1 0.1610 against C=0 0.1780, uniform-random reference 0.1809, and C=1 is lower at 5 of 5 seeds. On §11.5's based cells the same direction holds and wider: E+M 0.1645 against 0.1835, K+M 0.1645 against 0.1835. This criterion reads a rate directly and takes no ratio across arms, which is why §11's collapse does not reach it. |

<details><summary>Parameters</summary>

```json
{
  "issuance_rule": "endogenous",
  "injection_target": "top_node",
  "uniform_opening": "same_marginal",
  "pooling": "round",
  "channel_order": "capital_first",
  "event_order": "inherit_first",
  "readable_sd": 1.0
}
```

</details>

## A5 — the reachability threshold: the crossing runs through the price channel and not the wage bill, issuance or turnover, measured at 654.51% against a 1% zero calibration

`rounds=300` `12 seeds`

**4/8 live criteria passed**

| | criterion | detail |
|---|---|---|
| **FAIL** | A5-1  participation falls with reachability | production-layer participation across the grid: rho=0.25: 22.2%, rho=0.5: 27.2%, rho=1.0: 29.2%, rho=2.0: 11.1%, rho=4.0: 0.6%, rho=8.0: 0.0% |
| **FAIL** | A5-2  the threshold sits where the definition puts it | at rho=0.5: 27.2% against a floor of 50%; at rho=2.0: 11.1% against a ceiling of 5%. rho=1 is where the median agent can just pay, not a fitted value |
| **FAIL** | A5-3  the sign of the production layer's trend flips | net worth share at rho=0.25: 0.279 -> 0.001; at rho=4.0: 0.260 -> 0.010. One mechanism, two regimes, nothing changed but reachability |
| PASS | A5-4  the benign side is not an equilibrium | configured rho=0.5, rho_opening=0.319: the configured value is never observed, because the opening allocation moves it before any round runs. Crossed in 12/12 seeds, median round 2 counted from rho_opening against 100, and 1 counted from the series origin, which is the count this stage reported before the origin was named. 0.0% of subsequent rounds back below one against 5%. Measured from the series origin, the price moves by x58.554 and the median production-layer agent's claims by no point value: the sign is not stable across seeds, [x0.036, x2.652], 7 of 12 below x1; which of the two closes the reachable region is what A5-7 and A5-8 are registered to score, and this line reports the pair rather than reading it |
| PASS | A5-5  issuance sets the clock | median crossing round counted from rho_opening, by issuance gain: gain=0.25: 2, gain=0.5: 2, gain=1.0: 2. Every median is equal, so the ordering is satisfied vacuously and this pass carries no information about issuance |
| **FAIL** | A5-6  freeze the price and the drift disappears | largest relative move in rho with the price frozen: 654.51% against 1%. Any crossing at a live price is therefore the price channel and not the wage bill, issuance or turnover |
| PASS | A5-7  the denominator crosses the threshold on its own | price frozen at eta=0, configured rho=0.5, rho_opening=0.319: crossed in 12/12 seeds, median round 2 counted from rho_opening against 100 inherited from A5-4, 0.0% of subsequent rounds back below one against 5%. The asset does not move and the reachable region closes anyway |
| PASS | A5-8  the drain is not a property of one reachability | price frozen: median production-layer claims end below their rho_opening value in 72/72 cells across 6 reachabilities and 12 seeds, ratio x0.045. Reported without a threshold, the same ratio with the price live is no point value: the sign is not stable across seeds, [x0.000, x2.496], 68 of 72 below x1: the two arms are two registered settings of one switch and this line reports both rather than choosing one |

## A6-7 to A6-23 — the frontier ratchet, who the levy falls on, who the rebate reaches, and R* as a slope in lambda

5 seeds `rounds=300` `long_run=2000` `horizon=60000`, one cell carrying a registered multiple

**13/15 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A6-7 | 160 model pairs compared against A6Model bit for bit, over 4 rates and 300 rounds in each of eight cells; 0 mismatches. A gate: nothing below it runs if it fails |
| PASS | A6-8 | K-B settles on I/lambda on a bench with no economy in it; the worst relative error is at machine precision, below 1e-09 |
| PASS | A6-9 | band of lambda holding all five seeds open at R = 0.005 over 2000 rounds: [0, 0.01], 6 of 8 grid points, judged on exp. No lambda is nominated, and the low end is an artefact of this horizon |
| **FAIL** | A6-10 | on the registered grid at 2000 rounds, R*(I) per judged cell: exp/lambda=0.001 median 0.005 on the grid floor; exp/lambda=0.01 median 0.010 off the floor |
| **FAIL** | A6-11 | R*(I)/R*(T) against 0.75, as a value not a bound: exp/lambda=0.001 0.083 (bound only); exp/lambda=0.01 0.167 |
| PASS | A6-13 | exp and hill point the same way: band agreement True, scan verdict agreement True |
| PASS | A6-14 | the wall at lambda = 0 reproduces section 9.2's end over start: recorded 1.66, 0.07, 1.60, 1.86, 0.15; measured 1.66, 0.07, 1.60, 1.86, 0.15; worst absolute difference 0.0048 against 0.005 |
| PASS | A6-15 | under the wall the band is interior: open at ['0.01'], closed at ['0', '0.0001', '0.1'], crossover at 0.001, inside the registered window True |
| PASS | A6-16 | both judged cells closed on the layer base, which is what the surviving-leak reading predicts: a smooth g postpones the collapse rather than removing it |
| PASS | A6-18 | levy collected in the final round, in units of the opening claim stock: layer/exp/lambda=0 1.69e-05 from 3.57e-03; layer/hill/lambda=0 1.46e-04 from 3.57e-03; layer/clip/lambda=0.001 8.66e-04 from 3.57e-03; threshold/exp/lambda=0 2.74e-03 from 3.11e-03; threshold/hill/lambda=0 2.68e-03 from 3.11e-03; threshold/clip/lambda=0.01 3.24e-03 from 3.11e-03 |
| PASS | A6-19 | both judged cells closed on the threshold base, which is what the surviving-leak reading predicts: a smooth g postpones the collapse rather than removing it |
| PASS | A6-20 | nodes on both sides of the transfer in one round, worst over seeds: levy=layer/rebate=layer 0; levy=layer/rebate=threshold 5; levy=threshold/rebate=layer 61; levy=threshold/rebate=threshold 0. Worst claim drift at machine precision, below 1e-06; fallback rounds 0 |
| PASS | A6-21 | rho* per lambda, median over seeds: lambda=0.001 1; lambda=0.003 1; lambda=0.01 1. Worst separation 0 grid steps against 1; at a grid end False; unsolved seeds 0 |
| PASS | A6-22 | band of lambda keeping every seed open, exp, on the corrected instrument: 0.001 to 0.01. The other columns, one change at a time: A exp laye/laye 0.001 to 0.01; B exp thre/laye 0.001 to 0.01; C clip thre/thre 0.003 to 0.01; C exp rho=1 0.001 to 0.1 |
| PASS | A6-23 | clip control band on the corrected instrument: 0.003 to 0.01, scanned over [0.001, 0.003, 0.01, 0.03, 0.1] |

## A6 — the siphon in tax points: the stratified graph needs R* = 0.060 where the flat graph needs 0.000, and that difference is the siphon

5 seeds `rounds=300` `long_run=2000`

**3/5 live criteria passed**

| | criterion | detail |
|---|---|---|
| **FAIL** | A6-1 | the support set contracts at R=0 in 4 of 8 cells, all seeds. The four that do are the access cells and the four that do not are the flat ones, which is what A6-3 predicts; the criterion's scope is what is wrong |
| PASS | A6-2 | 0 seed-cells with no rate on the grid holding the economy open |
| PASS | A6-3 | with retention already fair and no issuance anywhere, the stratified graph needs R* = 0.060 (> 0.02) and the flat graph 0.000 (< 0.005). That difference is the siphon |
| PASS | A6-4 | R*(I)/R*(T) under access against 0.75: fair 0.083 (an upper bound, R*(I) is on the grid floor), stratified 0.031 (an upper bound, R*(I) is on the grid floor) |
| **FAIL** | A6-5 | at R* = 0.005 over 2000 rounds, end over start per seed 1.66x, 0.07x, 1.60x, 1.86x, 0.15x. 2 of 5 seeds collapsed and the rest ended more open. The registered band is symmetric and scores those as the same failure |

## A7 — continuous connectivity

`rounds=300` `20 seeds`

Record with no criteria block, kept as evidence and named here so it is findable:
`results/a7_continuous_c.json`, the run itself. The criteria below are adjudicated
in `results/a7_verdicts.json`, which reads it.

**3/7 live criteria passed, 4 void**

| | criterion | detail |
|---|---|---|
| PASS | A7-A-1 | reach: peripheral-tercile participation is 0.0 at every seed through s = 0.7 and first strictly positive at s = 0.8, where the graph carries 32051 of 39800 edges and the layer gap has fallen from 0.394 to 0.030. The carrier gains a measurable population by ceasing to be stratified; docs section 6.1 |
| **FAIL** | A7-A-2 | the registered shape is wrong. Not a gradient: a step at the first grid point, both +18.9854 to -0.1157, then flat to s = 0.9. Recorded under the project's engineering rule 8 and not repaired; docs section 6.2 |
| VOID | A7-A-3 | void on the estimator it names. On D_fixed each arm's population is intersected across its own grid, so the two are 24.20 against 35.95 nodes and a difference of falls compares quantities on different agents; docs section 11.2 |
| **FAIL** | A7-A-4 | A3-8' holds nowhere including where it was derived. Loop-sum-only same-sign across seeds on D_fixed at s = 0: 17/20 and 19/20, against 20/20 on D_reach. A3-8's own state is untouched; docs section 11.3 |
| **FAIL** | A7-A-5 | the identity does not hold on the measured population. Mean \|loop sum\| over the fixed production layer rises before it falls, to 1.44 times its s = 0 value in the uniform arm and 4.13 in the preferential one; docs section 6 changelog |
| **FAIL** | A7-A-6 | the round-count ladder is not monotone in the uniform arm and gives 4.85 against a registered five in the preferential one. The retained fraction goes as 1/R because the s = 0 baseline scales with the round count; unnormalised the gap at s = 0.01 does not move at all across a fourfold change in rounds while the gap at s = 0 moves with it; docs sections 10.2 and 10.3 |
| VOID | A7-B-1 | unreadable. d(K, s) is sign-unstable at every grid point including s = 0, where the mean is -0.00039 against a range of [-0.0020, +0.0010] that straddles zero. A quantity with no sign has no magnitude to trend. This is A4-4's position on a different estimator; docs section 13.1 |
| VOID | A7-B-2 | not adjudicable as registered: the noise floor the clause conditions on was never given a numeric form. Against A7-B-1's standard E fails too, at 17/20 rather than 20/20; docs section 13.2 |
| PASS | A7-B-3 | the two-measure disagreement clause did not fire. On the aggregate log(1/HHI) both competitors are also sign-unstable and near zero, so the measures agree and what they agree on is that nothing is readable; docs section 13.3 |
| PASS | A7-B-4 | both probes ran before anything was scored and the section 5.3 trigger was decided on them alone. Room relative to s = 0, largest over the grid: aggregate log(1/HHI) 2.00 against a registered band of 1.5, production-layer-only 1.20. The substitution registered with the band fires and leg B proceeds on one axis; docs sections 12.2 and 12.3 |
| VOID | A7-B-5 | I and M recorded as not run. Above s = 0.02 in the uniform arm a one-off transfer leaves nothing after a generation, so a transmitting mechanism has no stock and their effects are identically zero by construction; docs sections 12.1 and 13.5 |

## B10 — the holonomy machinery rebuilt on a second carrier, and what that carrier stops recording in mid-2019

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b10_gridvar.json`, `results/b10_o18join.json`, `results/b10_pgrid.json`, `results/b10_pgrid.pre_h.json`.

Freddie Mac's single-family loan-level file: 1,362,490 loans, 74,937,616 monthly
rows, 28 vintages. Every record this stage writes is `diagnostic_only`, so none
of the tables above come from it; this section is where its readings are, and
they are written rather than rendered because the stage's register is held
outside this repository.

### What was built

A second carrier for the holonomy machinery, from the field enumeration up: the
interest-bearing balance, the zero-interest split, the balloon horizon, the
discount curve's reach, the noise floor, the residual driver, the loop sums, and
the three legs. **No residual formula is written here.** The driver feeds the
one implementation that already existed, and a construction cross-check proves
it is that object and not a second copy: eight lines, all passing, including a
worst-case path over all 128 half-cent sign combinations, which lands 6.4 times
inside its own bound.

### What it says

**The cut decides the reading, on both carriers.** Coarsening the state grid
moves the share of `omega`'s variance that class labels explain, on both arms,
in the same direction as the first carrier. That is the concern this programme
opened with, and two carriers agreeing that the cut matters is the concern
confirmed, not dissolved.

**Path dependence is a discrete event, not a drift.** Of the three legs of a
modification triangle, the modification month carries **98.71%** of `|omega|`.

**A third of the population is not on the contract path.** Of clean-cure round
trips, only **64.66%** carry the sign pattern an ideal cure must produce. The
other 35% do something else, and it is not noise: errors cluster, and at the
longest window the observed rate of the ideal pattern is **2.33 times** what
independent per-month errors would give.

### The register, and where each map landed

**This stage's criteria are not pass-or-fail rows.** Each one is an outcome map:
one variable, three or four exhaustive branches named before the run, and the
verdict is which branch the reading lands in. That form is what engineering
discipline 11 asks for, a printed object with a reading declared in advance and
no line drawn on an estimator, and it is why none of this stage's sixty records
carries a `criteria` block: a branch label out of an exhaustive set is not a
boolean, and there was nowhere in that shape to put one. The maps are here
instead.

**First, the carrier: what each field is, established by behaviour and not by
reading a layout document.** Nothing downstream is possible until these land.

| map | the variable | landed | reading |
|---|---|---|---|
| §2·5 | is this sample fixed-rate by behaviour | **1 of 3** | it is; the 544 exceptions touch 0.04% of 1,362,500 loans and cannot move the verdict |
| §5·4 | how a loan with no balance ever reported behaves | **3 of 3 empty** | the branch "never reported a balance at all" has no members |
| §5·5 | the phase of the thousand-dollar grid | **arms split, so branch 1 is refused** | two spikes; `499 + 500` together are **4.73%**, a 47-fold excess of half-thousand borrowers |
| §8·12 | does the state cut decide the reading | **1 of 3** | `E(g0m) − E(g2)` positive in all twelve cells: the cut decides it |
| §8·14 | how many columns behave like a zero-interest balance | **4 of 4** | thirteen do, and the registered handling for that branch could not be executed |
| §8·14·5 | the same question with the disjunction removed | **1 of 4** | exactly one column, signature two |
| §8·14·6 | the balloon horizon | **3 of 4** | more than one column holds it down, and the pre-run prediction that picked one was wrong |
| §8·14·6·5 | stratified by the data's own term values | **2 of 4** | no column is identical across strata |
| §8·14·6·6 | which of two loadings is larger, column by column | **1 of 4** | exactly one column has A > B: `orig col 4` is the maturity date |
| §8·14·6·7 | does term rewriting explain the 32.90% that disagree | **1 of 3** | it does, by a factor of **23** |
| §8·14·6·8 | which column `bn` takes | **1 of 3** | by a factor of **3,207** |
| §8·15 | what `delinq == 99` is | **2 of 3** | it is not a count of missed months. Three rows step `00 → 99` in one month, which no counter can do |
| §8·16 | no-modification round trips wholly inside age ≥ 8 | **1 of 3** | the construction's prediction is delivered |
| §8·17 | does the discount curve reach the horizons the round trips need | **1 of 3** | full coverage |
| §8·18 | which column is the interest-bearing balance | **1 of 3** | `col 3`, and it contains the deferred balance |

**Then the machine.** Section numbers are not consecutive here: registration
order and landing order are different, and this table is in the order things
ran. It is the entry point to this family.

| map | the question | landed | reading |
|---|---|---|---|
| §8·19 | does the residual's driver match the first carrier's | **1** | eight cross-checks pass; `603,609 − 123,792 − 53 − 13 = 479,751` |
| §8·20 | the clean-cure loop sum against the closed form | **1** | `ratio_max` 0.4004 against the first carrier's 0.400, **same fourth digit on all six vintages** |
| §8·21 | is there a rounding noise floor | **none of them** | the grid anchor reads 0.609 half-steps, which is the grid; the cent anchor reads **578 times** cent rounding, which is payment error. This carrier publishes no contract payment |
| §8·22 | does the triangle's loop window hold up | **1** | `rho(vintage, deferral share) = +0.8254`, **and the trend is a composition effect**: 2020–2021 are 51.2% of it |
| §8·23 | the three legs of `omega` | **1 and 1** | 20,846 of 20,850 measurable; **leg 2 carries 98.71% of `\|omega\|`** |
| §8·24 | `omega` against the floor | **1 and 1** | modification arm ratio 6,388,937, inside the first carrier's 2.4M–6.8M band |
| §8·25 | §8·12 re-asked on this carrier | **1** | `E(g0m) − E(g2)` = **+0.3048 / +0.2126**, both arms up, same direction as the first carrier |
| §8·26·1 | are those two 0.108 rates the same loans | **3** | lift **3.68**, each only 40% inside the other. Two rates near each other is a coincidence of magnitude |
| §8·26·2 | whose tail is `P_sub`'s | **3** | **35.97% out of bounds**, worst 1,338-fold. The grid explains at most 64% |
| §8·27 | is that 36% term or balance | **3, six rescued** | `h = age + rem − term ≡ 0` on 99.993%. Term is not the cause; `rem` is a derived field |
| §8·28 | are the out-of-bounds loans the same as the unnamed ones | **3** | lift **1.02**, 36.7% against 32.7%. Two independent populations |
| §8·29 | why the ratio rises with window length | **1** | coherence does not rise. **And that branch's pre-written explanation was refuted by the same run**: it predicted 2.57×, the measurement is 20.86× |
| §8·30 | where in the distribution that 20.86× lives | **1, peak in the middle** | by quantile 10.30 / **20.86** / 6.08 / 3.22. The denominator is small, the numerator is not large |
| §8·31 | are the two modes two kinds of loan | **2, and it is a theorem** | the sign alphabet: `+-` **64.66%**, `++` 17.18%, `--` 12.50%, `-+` 5.66% |
| §8·32 | are wrong-sign and out-of-bounds the same batch | **3** | lift within 0.956–0.986 of 1 at all four window lengths. Independent |
| §8·33 | why the ideal pattern's share collapses | **1** | observed over independent 1.02 → 1.26 → **2.33**. Errors cluster |
| §8·34 | who those 13,923 `++` loans are | **1** | monthly hazard **0.025197 against 0.014053, a factor of 1.79**; median FICO band 5 against 3 |
| §8·35 | is `++` a crisis-period thing | **1, and the reading is void** | two windows point opposite ways. **The by-year table shows a 2019 regime break**, 2018 against 2020 differing **12.6-fold**, and the calm window straddles it |
| §8·36 | is that break a reporting convention | **2** | frozen share **0.5452 → 0.9867**, the break inside the single month 2019-07. Of 306 unfrozen loops after 2020, **zero** have `r1 < 0` where the old regime implies about 180. The convention changed, and it does not explain all of it |
| §8·37 | conditional on frozen, did `r2` move too | **1** | `++ \| frozen` **0.2397 → 0.0245**, a factor of 9.78, both sides collapsing, **and this break is at 2019-05, two months before the freezing one**. Cut by origination vintage, ten thick vintages step in the same month while ranging from one to ten years of seasoning: **both breaks are calendar events** |
| §8·38 | is `++` the forbearance family | **2, and the pooled reading is a composition effect** | pooled `++` 0.0057 against `+-` 0.0321. **But the assistance column is blank for the first fifteen years**, and 42.7% of `+-` loops cure after 2020 against 4.1% of `++`. **Over 2014–2019 the direction reverses: `++` is 2.29 times higher** |

**Three of these are worth reading as a set.** §8·35's branch was registered
correctly and the reading is still void, because what broke was whether the
branches could be read pooled at all; what caught it was a registration clause
demanding every year be printed with none filtered. §8·38 is the same failure a
second time. **§8·37 is the opposite case**: a stronger per-class check caught
what a weaker pooled check could not, and both were registered, so one run
settled it.

### The finding that does not depend on this framework at all

**In GSE reporting, a cure is a status-field event.** The issuers' own
definitions say so: a cure covers reinstatement, repayment plans, workouts,
payoff, repurchase, and the resumption of accrual, and only some of those are a
borrower paying the arrears. This stage puts a size on the part that is not.

For **17.18%** of clean cures the delinquency counter clears while both months'
balances stay above the contract path. Those loans re-default at a **monthly
hazard of 0.025197 against 0.014053**, a factor of **1.79**, and right-censoring
runs against the finding rather than for it: they are observed longer, not less.
They are also a different population at origination, with a median FICO band two
steps lower and a first-time-buyer share of 10.1% against 14.3%. Debt-to-income
does not separate them.

**And that share is not stable in time.** It runs near a third before 2019 and
under a thirtieth after. The break is a calendar event, not a property of the
loans: cutting by origination vintage, **ten vintages with enough loans on both
sides all step in the same month**, and in 2019 those vintages ranged from one
to ten years of seasoning. A change in the loans cannot do that; a change in how
they are reported can.

Two breaks, two months apart. The delinquent month's balance goes from moving on
**45.5%** of cures to moving on **1.3%**, stepping between June and July 2019;
the cure month's sign turns over between April and May. Freezing the delinquent
balance accounts for the first and not the second: in the seven years after the
break, 306 loops still have an unfrozen delinquent month and **not one** reads
the sign that had appeared on 58.7% of such loops over the preceding twenty
years.

**The consequence for anyone using this data:** the 1.79 hazard difference is
measurable before mid-2019 and structurally unmeasurable after it. Not
unmeasured. The file stops carrying the quantity that separates the two kinds of
cure.

### What this stage cannot say

- **The contract payment is estimated, not published.** This carrier does not
  publish it. Changing the estimator moves the share of loops whose path
  qualifies from 0.108 to 0.092, and that will not go away.
- **The two carriers record a modification on two different clocks.** Here the
  flag is written after the cure, there during the delinquency. Any pooled
  comparison carries that.
- **What the off-pattern loops are is not established.** Servicing-assistance
  codes do not separate them once the years in which that column was not
  reported at all are excluded, and the issuers' list of cure types is a
  candidate set from documentation, not something this carrier's behaviour has
  earned.
- **Which institutional change the 2019 break is, this stage does not say.** It
  establishes only that the break is on the calendar. The carrier's own
  disclosure-change log records no 2019 change to either field.

## B11 — the second domain: corporate credit, and what it costs to count a loop there

**Station open. C11-0 has not been run**, so not one loop has been counted, and
every reading below was taken before it. Pre-registered design, criteria fixed
before the code, none rewritten after.

The domain was reached by the branch table: B8-3 passed and B8-4b is not run
because of C9, which lands the second domain on corporate credit.

**The ceiling on C11-0, counted rather than assumed.** Fitch's `RD` symbol, a
distressed exchange, appears on **422 rows over 227 issuers**, 2012-06-15 to
2025-07-01. By window, in issuers: energy 65, COVID 77, rates 95, outside any
window 185. Against a threshold of 200 loops, **a ceiling of 227 means the
investment-grade screen has to retain 88 per cent of them**.

**Which agency can carry the marker at all.**

| agency | distressed-exchange symbol | measured |
|---|---|---|
| Fitch | `RD` | present, 422 rows |
| Moody's | `/LD` suffix | **does not exist.** None of 224 symbols carries a slash. Only `D-PD`, 351 rows, which is default of any kind |
| S&P | `SD` | not on `ratingshistory.info`; the agency's own page 302s to a login |

So C11-0 can be computed **inside one agency's file**: the exchange, the rating
before it and the re-rating after it are all in Fitch's own history, with **no
name matching and no PDF extraction**. Moody's cannot serve as the marker source
because it cannot separate a distressed exchange from bankruptcy or a missed
payment.

**C11-1, contract-term fill on Moody's instrument rows, threshold 0.90.**

| column | fill | |
|---|---|---|
| `par_value` | 0.9976 | PASS |
| `maturity_date` | 0.9794 | PASS |
| `coupon_date` | **0.7856** | **FAIL** |

Coupon is the only binding constraint, and its denominator still has a layer to
peel: floating-rate notes, commercial paper and zero-coupon instruments carry no
fixed coupon by construction, so that blank is a property of the instrument. The
attribution patch is written and Moody's has to be re-run before there is a
reading. **Fitch fills nothing**: coupon, maturity and par all read 0.0, and
`rating_type_term` is empty on all **105,749** instrument rows, so the contract
leg can only run on Moody's.

**A column-name trap worth carrying forward.** `coupon_date` holds the coupon
*rate*: measured 7.25, quantiles [0.0, 3.3, 5.0, 6.75, 24.0]. The crawler wrote
the wrong name. The reader types by value and does not trust the column name.

**C11-2, is the snapshot rolling or cumulative.** The earliest snapshot on
`ratingshistory.info` is 2024-09-30, so the site is rolling. One listed file
carries `578778 lines` in its own anchor text, and half a million rows is not one
month of rating actions, so **a single snapshot is probably the full history and
the rolling window does not bind**. The regulator still does not say either way;
settling it means reading bytes, which is written and not run.

**The 2012 start holds.** Exactly one Fitch action predates 2012-06-15, a
singleton on 2003-09-04.

**Cross-agency key.** LEI: 279 of the 422 `RD` rows carry one, Moody's LEI fill
is 0.8645, and Fitch's `issuer_identifier` is the string `NRSRO` on 106,632
rows, an internal number with no value across agencies. C11-0 needs no
cross-agency pairing, so this matters only if the contract leg has to reach
Moody's.

**Availability, measured.** `ratingshistory.info` carries seven agencies and
**S&P is not one of them**: Egan-Jones, Fitch, JCR, Demotech, Kroll, Moody's,
DBRS. The regulator's schema marks `CR`, `PV` and `MD` optional, "only if
present in document"; the required fields are `RAD`, `R`, `IP` plus one of
`RAC` / `WST` / `ROL` / `OAN`. Optional fields in regulatory filings are
usually sparse and the threshold is 0.90, which is why this check was run early
and cheaply rather than skipped. The measurement bore the prior out.

**The exit if the count stays short.** Ruled 2026-08-19, before the attempt: if
the loop count is still under 200 after S&P is obtained, **the station stops and
a domain switch is registered separately. It does not rule that there is no
second domain.**

## B16 — Section 31 carrier: the pre-purchase checks, all of them free

**Station open and nothing has been judged.** Gate two cannot be computed yet:
it needs `Z90 * se_lower / band`, the se lower bound needs the observed
dispersion of rho, and that needs quotes. So the registered order is the one
D21 asks for: buy the smallest arm first, compute se from it, run gate two, and
only then decide about the other five. **Gate two failing means the other five
are never bought.**

**The screening rule is frozen, the symbol list is not.** The universe size N is
not known in advance, so N and the per-rule dropout counts are printed **before
any money is spent**, and an event whose N comes in under 40 is registered as
"insufficient symbols" and leaves the scored set at that point rather than after
the purchase. Parameters: price floor 300.0 as quoted, minimum 40 symbols, half
tick 0.005, rule 6 rejects any single-day `|log return|` above 0.4.

**Why the free price source cannot carry the screen.** stooq is split adjusted,
so a "above \$300 as quoted" rule cannot be applied to it at all. Measured on the
2026-08-20 stooq archive already on disk:

| symbol | 2019-03-14 in the archive | as quoted that day |
|---|---|---|
| GOOGL | 59.41 | about 1180 |
| AMZN | 84.31 | about 1700 |
| CMG | 12.85 | about 690 |
| NVR | 2722.77 | about 2900 (never split) |

stooq is kept for the trading calendar only, where the session list is taken at a
quorum of 500 symbols.

**The buy and no-buy halves are separated mechanically, not by convention.** The
cost module has no download path in it at all and its own selftest walks its AST
to prove that, so a metadata query cannot turn into a purchase by edit. Venue
codes are looked up rather than assumed: `metadata.list_datasets` for whether the
dataset exists spelled that way, `get_dataset_range` for when each venue's
history actually starts, `symbology.resolve` for which tickers fail or resolve
oddly, then `get_cost` and `get_billable_size`.

**The first arm's plan, as printed before buying**: arm e5, eight batches across
the registered venue pair `XNAS.ITCH` and `ARCX.PILLAR`, 3,077,367,520 billable
bytes, zero batches refused, and the quoted and extrapolated sizes differing by
0.64. The exclusion list carries 3,667 ETF tickers.

**One check in this set writes no record**: the theorem 6(5) invariance
calculation runs on exact arithmetic at 60 decimal digits with no network, no
data and no randomness, and reports to the console.

**Everything in `results/b16_*.json` is procurement and screening state, not a
reading.** None of it carries a criterion, and this section is where it is said
so rather than left to be inferred from an absence.

## B12 — whether a holonomy reading is an artefact of how the states were cut. Enumerated whole over every three-bin threshold cut of the delinquency ladder, so nothing is ranked and no null is needed. The between-class spread of median |omega| moves by 4 to 17 times across cuts: on the modification arm that exceeds the registered line on all six vintages, on the deferral arm on three of six with the other three within 12 per cent of it. **Per-loop `omega` is untouched, and that half is structural rather than measured**: coarsening changes which loops are the same loop and not what any one of them sums to. So what this binds is every quantity aggregated over cycle classes, and the 30/60-day convention is not neutral: it sits at opposite ends of the range on the two arms

6 vintages, 1,891 to 4,753 enumerated 3-bin cuts of the delinquency ladder, `min_cycles=20` `line=4.0`

**4/13 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B12-D  2002Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 3.58 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 301,562 to 1,079,408, the 30/60-day cut at 301,562 which is quantile 0.0007; 1,350 cuts give a finite spread |
| **FAIL** | B12-D  2002Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 8.85 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 774,017 to 6,849,833, the 30/60-day cut at 1,504,290 which is quantile 0.0300; 3,839 cuts give a finite spread |
| PASS | B12-D  2006Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 3.73 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 352,134 to 1,311,909, the 30/60-day cut at 414,154 which is quantile 0.1614; 1,512 cuts give a finite spread |
| **FAIL** | B12-D  2006Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 5.99 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 675,856 to 4,046,634, the 30/60-day cut at 2,510,057 which is quantile 0.5787; 4,213 cuts give a finite spread |
| PASS | B12-D  2007Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 3.75 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 283,561 to 1,064,286, the 30/60-day cut at 347,031 which is quantile 0.2174; 1,513 cuts give a finite spread |
| **FAIL** | B12-D  2007Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 17.29 across 4,753 enumerated 3-bin cuts, line at 4.0; spread in floor units 249,359 to 4,311,206, the 30/60-day cut at 1,700,517 which is quantile 0.3364; 4,257 cuts give a finite spread |
| **FAIL** | B12-D  2012Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 7.92 across 3,741 enumerated 3-bin cuts, line at 4.0; spread in floor units 124,206 to 983,162, the 30/60-day cut at 541,173 which is quantile 0.2086; 1,395 cuts give a finite spread |
| **FAIL** | B12-D  2012Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 14.21 across 3,741 enumerated 3-bin cuts, line at 4.0; spread in floor units 278,332 to 3,956,047, the 30/60-day cut at 1,482,163 which is quantile 0.3321; 2,108 cuts give a finite spread |
| **FAIL** | B12-D  2017Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 7.68 across 2,145 enumerated 3-bin cuts, line at 4.0; spread in floor units 144,368 to 1,109,199, the 30/60-day cut at 185,447 which is quantile 0.0018; 1,107 cuts give a finite spread |
| **FAIL** | B12-D  2017Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 14.74 across 2,145 enumerated 3-bin cuts, line at 4.0; spread in floor units 197,148 to 2,905,242, the 30/60-day cut at 737,949 which is quantile 0.1213; 1,674 cuts give a finite spread |
| **FAIL** | B12-D  2019Q1 defer: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 13.45 across 1,891 enumerated 3-bin cuts, line at 4.0; spread in floor units 84,825 to 1,140,772, the 30/60-day cut at 310,157 which is quantile 0.1550; 1,026 cuts give a finite spread |
| **FAIL** | B12-D  2019Q1 mod: between-class spread of median \|omega\| is invariant to where the delinquency ladder is cut | max/min 11.96 across 1,891 enumerated 3-bin cuts, line at 4.0; spread in floor units 173,137 to 2,071,535, the 30/60-day cut at 2,071,535 which is quantile 1.0000; 1,505 cuts give a finite spread |
| PASS | B12-D  the spread's position is not fixed by the class count | class-count quantile of the real cut spans 0.9942 to 1.0000 over 12 cells while its spread quantile spans 0.0007 to 1.0000: a near-constant class count against the full range of spread positions |

Derived quantities:

- `real_grid_quantile_2002Q1_defer` = 0.0007
- `real_grid_quantile_2002Q1_mod` = 0.0300
- `real_grid_quantile_2006Q1_defer` = 0.1614
- `real_grid_quantile_2006Q1_mod` = 0.5787
- `real_grid_quantile_2007Q1_defer` = 0.2174
- `real_grid_quantile_2007Q1_mod` = 0.3364
- `real_grid_quantile_2012Q1_defer` = 0.2086
- `real_grid_quantile_2012Q1_mod` = 0.3321
- `real_grid_quantile_2017Q1_defer` = 0.0018
- `real_grid_quantile_2017Q1_mod` = 0.1213
- `real_grid_quantile_2019Q1_defer` = 0.1550
- `real_grid_quantile_2019Q1_mod` = 1.0000
- `spread_max_over_min_2002Q1_defer` = 3.5794
- `spread_max_over_min_2002Q1_mod` = 8.8497
- `spread_max_over_min_2006Q1_defer` = 3.7256
- `spread_max_over_min_2006Q1_mod` = 5.9874
- `spread_max_over_min_2007Q1_defer` = 3.7533
- `spread_max_over_min_2007Q1_mod` = 17.2892
- `spread_max_over_min_2012Q1_defer` = 7.9156
- `spread_max_over_min_2012Q1_mod` = 14.2134
- `spread_max_over_min_2017Q1_defer` = 7.6831
- `spread_max_over_min_2017Q1_mod` = 14.7364
- `spread_max_over_min_2019Q1_defer` = 13.4485
- `spread_max_over_min_2019Q1_mod` = 11.9647

## B13 — the zero domain: the framework names where its own quantity must be zero, and then measures it on a venue where the order can actually be placed. Never worse than the two-leg derivation in 81,968 states over nine products, and exactly equal on six of them, while the directly quoted member of the same family is non-zero in 65 to 96 per cent of states. **Why those six and not all nine is not established**: the explanation the station first gave is withdrawn in B13-2

81,968 states over 9 products and 3 channels, one ten-minute window of 2023-07-17, from the vendor's free public sample

**7/7 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B13-0  the gate: one spread, both multicast sides, a book class that implements every action it is sent | 34923 end-of-event states with a book change on one of the three instruments, 2442 of them republished the spread's implied book and are paired. Update actions this book class does not implement: 0. Reading only the A-side of an A+B deduplicated capture had cost 2 per cent of updates and produced a bid agreement of 0.9229 that looked like a finding; with both sides it is 0.9990 |
| PASS | B13-1  section 4.A.2, load-bearing: the exchange's published implied price is never worse than the two-leg derivation | 0 violations in 63168 states on ch382, 0 in 5336 on ch386 and 0 in 13464 on ch360, over nine products and three channels. The criterion is a one-sided inequality and not an equality, which is what makes zero violations the whole of it |
| PASS | B13-2  on six of the nine products the inequality is an equality, bit for bit, and why those six is not established | equality rate 1.0000 on both sides of both ch386 and ch360, which is 2668 offer and 2668 bid states there and 6732 of each on ch360, 18800 in all. **The explanation the station first gave is withdrawn**: it said those products have only one derivation path, and the instrument listing says otherwise for every root measured, CL 906 of 906 multi-path, NG 1124 of 1127, GC 231 of 231, HG 820 of 820, MHG 780 of 780, QI 55 of 55. The reading stands and the attribution does not |
| PASS | B13-3  the same apparatus on the directly quoted member of the same family returns non-zero | share of states with a non-zero gap between the directly quoted book and the two-leg derivation, by channel: 0.8751 offer and 0.9240 bid on ch382, 0.7470 and 0.6516 on ch386, 0.9478 and 0.9610 on ch360. Nine products, no exception. **Not an economic statement**: it is ordinary queueing and market-making difference, and the design file forbids reading it as more |
| PASS | B13-4  section 5.2's precondition: the spread quotes on the same grid as its legs | equal 10 different 0 no data 0 on ch382, equal 7 different 0 no data 0 on ch386, equal 8 different 0 no data 0 on ch360. **This registered check was skipped when the gate first ran and was performed afterwards**, so the readings above stood on luck until it passed. Measured as the gcd of the observed prices rather than read off the definition field |
| PASS | B13-5  B4's section 5.1 split, both halves computed on live quotes for the first time in this repository | the split is available in 49116 of 50055 states, 0.981; Theorem 6(1)'s sign constraint has 0 counterexamples in those 49116; the index part is exactly zero in 12637 of them. B5 could report the index half and never the friction half, and this is the first carrier that quotes all four legs natively |
| PASS | B13-6  Theorem 6(4)'s bound, and section 5.1's own criterion for two agent classes, adjudicated per position edge | 0 violations of \|S - S'\| <= -(S + S') in 49116 states; rho median 0.2000 with 0 states at rho = 1. Under the parity control the index is zero in 0.5649 of the states where zero was available: CLU3-CLV3 takes it 716 times out of 716 and is one class, RBU3-RBX3 takes it 88 times out of 1978 and RBU3-RBV3 155 out of 1895, and those two are two classes |

## B14 — a dated, exogenous, symmetric friction change (the SEC tick size pilot), both halves. The friction half moves, on both venues, under every weighting convention tried, and after dropping the order types that carry most of the share weight without participating in the spread. **The index half was bought and cannot be adjudicated on this carrier, and the reason is structural**: `S - S'` is a difference of price levels and a tick-size change works by moving those levels onto a lattice, so projecting the post-release quotes back onto the nickel grid reproduces 88.7 per cent of the whole move and the residual sits inside a placebo band. Closed rather than paused. What the stage produced instead is a carrier specification: `docs/b4_directed_edges.md` section 9 now carries three conditions where it carried one, and Theorem 6(5) is new

### b14_gate0.authoritative

2,944 venue-symbols (N 679, P 2,265), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**13/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.515392 over 115 symbols, C +0.120200 over 338, margin +0.395193 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.399441 over 112 symbols, C +0.120200 over 338, margin +0.279242 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.454552 over 114 symbols, C +0.120200 over 338, margin +0.334352 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.158091 over 379 symbols, C +0.074414 over 1135, margin +0.083677 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.174435 over 375 symbols, C +0.074414 over 1135, margin +0.100021 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.178528 over 376 symbols, C +0.074414 over 1135, margin +0.104114 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.411207; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.307160; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.389522; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.191746; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.174114; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.190657; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.398135 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.282184 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.337295 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.061189 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.087231 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.075680 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.390106; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.281569; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.321898; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin +0.026127; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin +0.025701; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin +0.020256; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| **FAIL** | B14-0  the six registered margins reproduce on the v2 cache | 6 margins compared, 3 differ |

Derived quantities:

- `median_delta_N_C` = 0.1202
- `median_delta_N_G1` = 0.5154
- `median_delta_N_G2` = 0.3994
- `median_delta_N_G3` = 0.4546
- `median_delta_P_C` = 0.0744
- `median_delta_P_G1` = 0.1581
- `median_delta_P_G2` = 0.1744
- `median_delta_P_G3` = 0.1785

### b14_gate0

2,943 venue-symbols (N 679, P 2,264), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**14/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.515392 over 115 symbols, C +0.120200 over 338, margin +0.395193 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.399441 over 112 symbols, C +0.120200 over 338, margin +0.279242 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.454552 over 114 symbols, C +0.120200 over 338, margin +0.334352 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.158091 over 379 symbols, C +0.072771 over 1136, margin +0.085320 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.174556 over 374 symbols, C +0.072771 over 1136, margin +0.101785 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.178572 over 375 symbols, C +0.072771 over 1136, margin +0.105801 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.411207; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.307160; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.389522; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.191953; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.174736; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.192207; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.398135 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.282184 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.337295 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.061611 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.087728 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.076866 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.390106; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.281569; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.321898; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin +0.026542; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin +0.026354; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin +0.021057; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| PASS | B14-0  the six registered margins reproduce on the v2 cache | 6 margins compared, 0 differ |

Derived quantities:

- `median_delta_N_C` = 0.1202
- `median_delta_N_G1` = 0.5154
- `median_delta_N_G2` = 0.3994
- `median_delta_N_G3` = 0.4546
- `median_delta_P_C` = 0.0728
- `median_delta_P_G1` = 0.1581
- `median_delta_P_G2` = 0.1746
- `median_delta_P_G3` = 0.1786

### b14_gate0.sens_FULL

2,943 venue-symbols (N 679, P 2,264), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**14/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.515392 over 115 symbols, C +0.120200 over 338, margin +0.395193 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.399441 over 112 symbols, C +0.120200 over 338, margin +0.279242 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.454552 over 114 symbols, C +0.120200 over 338, margin +0.334352 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.158091 over 379 symbols, C +0.072771 over 1136, margin +0.085320 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.174556 over 374 symbols, C +0.072771 over 1136, margin +0.101785 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.178572 over 375 symbols, C +0.072771 over 1136, margin +0.105801 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.411207; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.307160; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.389522; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.191953; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.174736; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.192207; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.398135 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.282184 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.337295 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.061611 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.087728 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.076866 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.390106; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.281569; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.321898; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin +0.026542; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin +0.026354; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin +0.021057; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| PASS | B14-0  the six registered margins reproduce on the v2 cache | 6 margins compared, 0 differ |

Derived quantities:

- `median_delta_N_C` = 0.1202
- `median_delta_N_G1` = 0.5154
- `median_delta_N_G2` = 0.3994
- `median_delta_N_G3` = 0.4546
- `median_delta_P_C` = 0.0728
- `median_delta_P_G1` = 0.1581
- `median_delta_P_G2` = 0.1746
- `median_delta_P_G3` = 0.1786

### b14_gate0.sens_X16

2,943 venue-symbols (N 679, P 2,264), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**14/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.533369 over 115 symbols, C +0.121878 over 338, margin +0.411491 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.411119 over 112 symbols, C +0.121878 over 338, margin +0.289241 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.469203 over 114 symbols, C +0.121878 over 338, margin +0.347326 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.187636 over 379 symbols, C +0.079704 over 1136, margin +0.107932 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.211618 over 374 symbols, C +0.079704 over 1136, margin +0.131914 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.221109 over 375 symbols, C +0.079704 over 1136, margin +0.141405 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.433949; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.333199; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.382734; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.218058; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.206739; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.213833; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.413195 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.289987 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.349030 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.089152 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.112947 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.099522 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.389067; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.289802; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.340201; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin +0.050488; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin +0.062650; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin +0.058266; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| PASS | B14-0  the six registered margins reproduce on the v2 cache | 6 margins compared, 0 differ |

Derived quantities:

- `median_delta_N_C` = 0.1219
- `median_delta_N_G1` = 0.5334
- `median_delta_N_G2` = 0.4111
- `median_delta_N_G3` = 0.4692
- `median_delta_P_C` = 0.0797
- `median_delta_P_G1` = 0.1876
- `median_delta_P_G2` = 0.2116
- `median_delta_P_G3` = 0.2211

### b14_gate0.sens_X22

2,943 venue-symbols (N 679, P 2,264), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**14/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.494685 over 115 symbols, C +0.102310 over 338, margin +0.392375 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.329537 over 112 symbols, C +0.102310 over 338, margin +0.227227 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.424969 over 114 symbols, C +0.102310 over 338, margin +0.322659 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.235741 over 379 symbols, C +0.159808 over 1136, margin +0.075933 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.213012 over 374 symbols, C +0.159808 over 1136, margin +0.053205 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.195884 over 375 symbols, C +0.159808 over 1136, margin +0.036076 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.453265; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.292965; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.421564; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.173276; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.143390; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.172871; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.391521 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.222612 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.321812 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.040015 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.045753 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.000594 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.367357; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.213019; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.305434; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin -0.034562; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin -0.043898; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin -0.051181; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| PASS | B14-0  the six registered margins reproduce on the v2 cache | 6 margins compared, 0 differ |

Derived quantities:

- `median_delta_N_C` = 0.1023
- `median_delta_N_G1` = 0.4947
- `median_delta_N_G2` = 0.3295
- `median_delta_N_G3` = 0.4250
- `median_delta_P_C` = 0.1598
- `median_delta_P_G1` = 0.2357
- `median_delta_P_G2` = 0.2130
- `median_delta_P_G3` = 0.1959

### b14_gate0.sens_X2216

2,942 venue-symbols (N 679, P 2,263), 20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**14/14 live criteria passed, 12 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  G1 on venue N: median delta exceeds control | G1 +0.516354 over 115 symbols, C +0.103805 over 338, margin +0.412549 |
| PASS | B14-0  G2 on venue N: median delta exceeds control | G2 +0.368754 over 112 symbols, C +0.103805 over 338, margin +0.264950 |
| PASS | B14-0  G3 on venue N: median delta exceeds control | G3 +0.427029 over 114 symbols, C +0.103805 over 338, margin +0.323225 |
| PASS | B14-0  G1 on venue P: median delta exceeds control | G1 +0.247722 over 379 symbols, C +0.170058 over 1136, margin +0.077663 |
| PASS | B14-0  G2 on venue P: median delta exceeds control | G2 +0.263889 over 374 symbols, C +0.170058 over 1136, margin +0.093830 |
| PASS | B14-0  G3 on venue P: median delta exceeds control | G3 +0.246332 over 374 symbols, C +0.170058 over 1136, margin +0.076274 |
| PASS | B14-0  the verdict does not turn on the weighting convention | share-weighted verdict PASS, order-count-weighted verdict PASS (design file D3-3: disagreement makes the gate unadjudicable) |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on N | margin +0.467914; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on N | margin +0.330523; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on N | margin +0.416823; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G1 on P | margin +0.185548; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G2 on P | margin +0.176193; design file section 4 excludes this from the verdict |
| DIAG | B14-0  cross-check on the consolidated spread: G3 on P | margin +0.221901; design file section 4 excludes this from the verdict |
| PASS | B14-0/T5  adverse convention, G1 on venue N | margin +0.412549 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue N | margin +0.264950 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue N | margin +0.323225 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G1 on venue P | margin +0.063437 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G2 on venue P | margin +0.075149 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| PASS | B14-0/T5  adverse convention, G3 on venue P | margin +0.030830 with zero-spread rows admitted at their true share weight; design file section 4 supplement 1 |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue N | margin +0.382348; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue N | margin +0.235274; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue N | margin +0.315415; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G1 on venue P | margin -0.020374; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G2 on venue P | margin -0.021719; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| DIAG | B14-0/T6  blanks and zeros both forced to zero, G3 on venue P | margin -0.014172; a blank is a no-quote state, so this convention is a bound on the arithmetic and not on the world (design file section 4 supplement 2) |
| PASS | B14-0  the six registered margins reproduce on the v2 cache | no prior record to compare |

Derived quantities:

- `median_delta_N_C` = 0.1038
- `median_delta_N_G1` = 0.5164
- `median_delta_N_G2` = 0.3688
- `median_delta_N_G3` = 0.4270
- `median_delta_P_C` = 0.1701
- `median_delta_P_G1` = 0.2477
- `median_delta_P_G2` = 0.2639
- `median_delta_P_G3` = 0.2463

### b14_stage_two

XNYS.PILLAR and XNAS.ITCH, 27,602,417 cross-venue aligned quote-seconds, $34.6896 of purchased data

**6/8 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  the friction half moved on the 2016 round, and it is not carried by the orders that do not participate in the spread | the primary share-weighted convention holds all six inequalities, and so do the order-count convention, the adverse convention and the NBBO cross-check. A19 then drops the order types that the code table named: away-from-market orders, which carry the largest single block of the share weight, retail liquidity providing orders, and both together. The primary measure holds 6/6 in every one of the three variants. Same event, same data, only the weight composition changes. **One caveat travels with any citation of T6**: its own 6/6 depends entirely on order type 22, holding under the retail variant and falling to exactly 3/6 under the other two. T6 was excluded from the verdict before the run, so nothing moves, but the dependence must be quoted with it |
| **FAIL** | B14-A  leg A, the pilot's termination read as a reversed event, FAIL, and the failure is a zero rather than a reversal | the primary convention holds 3 of 6 on the 2018 round. The six raw gaps straddle zero, and the design file's own reading, fixed before the run, is that the nickel grid is a one-sided constraint: imposing it forces every venue, lifting it only permits, while the NBBO is a market-wide minimum. So the sign-flip prediction was never owed on the venue's own BBO, and the NBBO cross-check does hold 6/6. The FAIL stands on the record and is not reinterpreted |
| PASS | B14-B0  leg B was bought and the wire format was read correctly | 108 NYSE-listed pilot symbols on two venues over eight months of bbo-1s. The depth gate's four registered checks all passed before a cent of bulk data was bought, and the pull came to 34.689578 dollars against a quote of the same. The semantic check is exact: every treated name, on every second the pilot was in force, has all four prices on a whole nickel |
| PASS | B14-B1  gate one: the two venues are two classes in section 5.1's own sense | the framework hands over its own criterion, that S - S' is zero exactly when the two classes face the same antisymmetric terms, so the question is measurable. Per control symbol, the count of days whose sign leans positive against a binomial null: 9 of 47 symbols beyond three standard deviations where the null expects well under one, and a median \|z\| of 2.08 where the null gives 0.67. Run on the control arm only, because inside the pilot the grid pins both venues to one lattice point and that branch is unreachable there |
| PASS | B14-B2  gate two: the grid's arithmetic reproduces 88.7 per cent of the whole pre/post move | projecting the post-release quotes back onto the nickel grid, bid down and ask up, reproduces most of the inside/outside gap in the primary statistic. The projection is verified by being the identity on treated names inside the pilot, digit for digit, since those are already on the lattice. Theorem 6(5)'s spread term is 1 to 5 per cent of the numerator by mass, so rho is not measuring spread asymmetry |
| **FAIL** | B14-B3  gate three: the residual is inside the placebo band, and leg B is CLOSED rather than paused | the treatment-specific residual sits inside a range built from six month pairs with no grid change at all. Half-month resolution widens the sample of placebos to fourteen and does not overturn it. A three-bin split on the pre-pilot spread has one bin clear its own band, but that bin's gradient lives in the control arm, which is not treatment heterogeneity. **Closed, not paused**: the arithmetic share is a property of the mechanism, and no quantity of further data changes it. The narrow-band discontinuity is sealed and is the basis of nothing |
| PASS | B14-19  order-type sensitivity, askable only once T7's code table arrived | the specification gives thirteen order-type codes; twelve are on disk and the absent one is exactly the Not Held code, which is a check that was written before the document was fetched and could have failed. The weighting is share weighted, which settles D3-3 and demotes the order-count convention from a co-verdict to a cross-check without moving any verdict |
| PASS | B14-20  A11's candidate list reopened: the pilot's rule is an increment rule, so slack does not mean out of reach | a name whose spread already exceeds the increment can still have both sides off the lattice, and projecting widens it. One delta for every bin, bounded by the lattice arithmetic, fits at 0.0228 dollars with the gradient in the treated arm and an r-squared of 0.5074, and the tightest bin's observed margin is reproduced by the curve to a residual of 0.0045. A11's reading that the residue is real stands; its statement that spillover is the only remaining candidate is withdrawn |

### b14_t1_order_type

20160801 to 20161231, October 2016 dropped as the pilot's phase-in month

**1/1 live criteria passed, 6 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B14-0/T1a  the gate survives holding the order-type mix fixed | N/G1 +0.396871; N/G2 +0.297419; N/G3 +0.353596; P/G1 +0.124935; P/G2 +0.133975; P/G3 +0.116206 |
| DIAG | B14-0/T1b  order type 22 alone, share 0.2733 | N/G1 +0.356010; N/G2 +0.294862; N/G3 +0.324250; P/G1 +0.014818; P/G2 +0.023667; P/G3 -0.007879 |
| DIAG | B14-0/T1b  order type 14 alone, share 0.2395 | N/G1 +0.423699; N/G2 +0.278610; N/G3 +0.399114; P/G1 +0.106153; P/G2 +0.096050; P/G3 +0.082576 |
| DIAG | B14-0/T1b  order type 16 alone, share 0.1527 | N/G1 +0.269830; N/G2 +0.115138; N/G3 +0.313197; P/G1 -0.140343; P/G2 -0.120063; P/G3 -0.063262 |
| DIAG | B14-0/T1b  order type 12 alone, share 0.1300 | N/G1 +0.597949; N/G2 +0.435025; N/G3 +0.420669; P/G1 +0.374891; P/G2 +0.332816; P/G3 +0.306158 |
| DIAG | B14-0/T1b  order type 13 alone, share 0.1203 | N/G1 +0.414677; N/G2 +0.239191; N/G3 +0.335008; P/G1 +0.096932; P/G2 +0.077592; P/G3 +0.086523 |
| DIAG | B14-0/T1b  order type 11 alone, share 0.0772 | N/G1 +0.719268; N/G2 +0.530232; N/G3 +0.654006; P/G1 +0.165324; P/G2 +0.158829; P/G3 +0.135239 |

### leg B and candidate zero: the fourteen records that carry no criteria block

These fourteen files in `results/` hold no `criteria` block, so nothing about
them can be read off a pass or a fail. They are stated here instead of being
left to be inferred from an absence.

**Candidate zero, the nickel-lattice fit** (`b14_cand0.json`). 2,919 pure-slack
pairs, cut into three bins by median spread. The fitted lattice step is
`delta = 0.0228`, that is 2.28 cents, with `sse` 0.03008, `r2` 0.5074 and the
step inside its registered bound. **The margin it explains falls away as the
spread widens**: +0.1791 at a median spread of 0.1196, +0.2315 at 0.1781, then
+0.0333 at 0.2395, then **negative** at 0.3524 and beyond. Bin 1 holds 583 pairs
and is where the arithmetic works.

**Leg B: a second, later window on a second pair of venues.** 108 symbols
screened on the 2016-04/05 median spread below 0.05 with a stability screen,
run over 2018-05-01 to 2019-01-01 on `XNAS.ITCH` and `XNYS.PILLAR`. Both venues
resolve; one symbol resolves partially. **Effective N is 106**: two symbols are
set aside because one venue's coverage of them begins 2018-09-24, five sessions
before the event. The cache keeps every symbol and **the exclusion is applied in
the analysis layer, so the ruling stays reversible** rather than being burned
into the data on disk.

**Panel hygiene, per month and per venue** (`b14_legb_panel_checks.json`,
`b14_legb_audit.json`). Between 3.74 and 8.38 million quote rows kept per venue
month, **zero crossed and zero locked rows dropped**, seven to ten thousand null
or one-sided rows, and a maximum ask of 19,999,999 cents which is a placeholder
rather than a price. Off-cent quotes are not spread across the panel: two
symbols carry 205,587 and 178,332 of them and the rest of the book is in the
tens.

**What leg B's gates read.**

| gate | reading |
|---|---|
| gate 1 | control arm, symbol-day unit, null is `Binomial(days, 0.5)` on the count of days leaning positive; the share of exactly-zero symbol-days on the control arm sits at 0.486 to 0.513 across the eight months |
| gate 2 | **the two arms differ in the share at zero and not in the interior.** Treated `share_rho0` 0.8563 against control 0.5131, while the interior medians are 0.33305 and 0.33319, the same to four places |
| gate 3 | real `DiD` +0.011684 against a placebo range of -0.012266 to +0.020891. **Two of six placebos reach the real value, so it is not outside the band** |
| slice A | real +0.027634 against a placebo range of -0.034864 to +0.031327 over fourteen placebos. **Three reach the real value; `real_outside` is false** |
| slice B | three bins by relative tick, reals +0.038286, +0.034515, +0.022970, **monotone in relative tick, and only bin 1 clears** |

**The two halves say the same thing in the same shape.** Candidate zero's fitted
margin dies as the spread widens, and leg B's slice B clears only its narrowest
bin while falling monotonically across the other two. **Where the tick is large
relative to the price the arithmetic accounts for the move; where it is small it
does not, and leg B's own gate 3 and slice A do not clear their placebo bands at
all.**

**Sensitivity of the 2016 gate to the order-type mix** (`b14_ordertype_sens.json`)
holds the four re-runs under the FULL, X2216, X22 and X16 exclusions side by
side: 4,093 or 4,094 venue-symbol pairs in each, with the drop reasons printed
per arm. The verdict-level reading from those runs is in the criteria tables
above; this file is the console output kept whole so the four can be compared
line for line.

## B15 — Bolivia, run as the control carrier for B6's Cuban reading

**The register was sealed before a single Bolivian number had been downloaded**,
and four of its thresholds are B6's own values, so the two carriers are judged
by one ruler.

**B6 found an edge the law grants, that is posted, and that nobody walks, on
207 of 207 Cuban publication days. Bolivia reads 21 of 52**, against B6's own
95% carried over unchanged. **So the framework does not say of any controlled
economy what it said of Cuba**, and B6's finding is specific to its carrier
rather than something the framework confers.

**The reading is robust to everything the stage left open.** Swept across five
alignments of the date column and both readings of which published number is
the ceiling, the share runs 26.00% to 66.00% over ten cells; taking the helpful
end of both axes at once still gives 66.00%, which has probability `1.5e-10` if
the true share were the threshold.

**B15-4 was decided twice and both verdicts are on the record.** The registered
instrument reads the date convention off the local hour the official series
steps, and 31 of 36 steps land at 04:00 to 05:00, at neither the 20:00
publication hour nor the midnight flip: it was measuring the aggregator's
refresh rather than the statute's clock, and it returned VOID. **The live
verdict comes from the publisher's own two columns** — the BCB prints
`Fecha de corte` and `Vigencia` on every row of its series, and the official
column keys on `Vigencia` on 39 of 39 against 1 of 35 — which involves no
clock, no aggregator and no third party. `docs/b15_bolivia_results.md` sections
9 and 13 carry both.

74,623 observations at 15-minute resolution over 760 days, 2024-07-21 to
2026-08-19, one venue's Binance P2P book against the BCB's own official series
and its per-transaction microdata; the euro leg over 39 days against the ECB's
daily reference rate.

| | criterion | detail |
|---|---|---|
| PASS | B15-1 retrieval integrity | 760 of 760 days served, 74,623 observations, 0 absent, 0 fills, manifest present |
| PASS | B15-2 the known-answer arm | S3's prefix digest reproduces on the records before the event, and S1's external anchor, the customs comunicado's 6,96 Bs/USD for 26/06/2026, reproduces from the annual grid |
| VOID | B15-3 the side convention | **VOID over the registered window, which straddles the break in §3.5**: as published 15.0543% uncrossed, swapped 85.1681%, and neither clears 99%. The two figures are one orientation read on each side of the break rather than one orientation failing. **On the post-event segment, the only segment arm III runs on, it resolves**: orientation A is uncrossed on 99.960% of 4,966 rows |
| PASS | B15-4 the date column | **the column carries the date the rate governs**, from the publisher's own two columns: the BCB prints `Fecha de corte` and `Vigencia` on every row of its series, and keyed on `Vigencia` the official column matches on 39 of 39, keyed on `Fecha de corte` on 1 of 35. The customs comunicado agrees, every row dated 26/06 reading 6.96. **The registered instrument returned VOID and that verdict is kept**: it reads the convention off the local hour the series steps, and 31 of 36 steps land at 04:00 to 05:00, at neither hour Art. 5.III makes available, so it was measuring the aggregator's refresh rather than the statute's clock |
| PASS | B15-5 the statutory spread | the statutory 0.10 holds on 100.000% of non-degenerate official rows; the 5,156 rows whose two sides are equal leave the denominator as fills rather than counting as spread zero |
| PASS | B15-6 the published TCO is the statute's weighted average | recomputed from the per-bank microdata by Anexo II's formula and matched on 35 of 35 days and 484 of 484 bank-days, at the two decimals Anexo II section 4 fixes. Worst absolute gap 0.0049 Bs. **This settles which published number Art. 6's ceiling is measured against**, which arm III would otherwise have had to carry as two readings |
| **FAIL** | B15-7 the posted return leg | on the post-event segment the informal ask sits above Art. 6's ceiling on 21 of 52 days, 40.38%, median `a(t)` = -0.0048, against a registered 95%. **Cuba's B6-15 reads 207 of 207.** Swept across five alignments of the date column and both readings of which published number is the ceiling, the share runs 26.00% to 66.00% over 10 cells and no cell reaches, so the reading does not rest on either |
| PASS | B15-8 friction, and the cycle B6-B could not certify | the cycle weight is determined on 100% of the segment's days under both readings of the ceiling; a weight of exactly zero is certified non-positive, which is a determination and not a gap |
| PASS | B15-9 the customs edge | 8 of 8 weeks resolve from S1's annual grid under Art. 20 of `D.S. 25870`, which holds the week's rate at the previous week's last business day, and the Aduana comunicado's 6.96 for 2026-06-26 reproduces. **One published number, one agent class, one week at a time**: the edge is granted to Operadores de Comercio Exterior alone and to nobody else at that rate |
| **FAIL** | B15-10 the event | no single dated break at the reform: null draws 999, seed 0, break date 2026-06-29, and the reading does not depend on which orientation is taken (True). The banks' rate had already walked most of the way before the instruments were signed, so there is no step for a break test to find |
| **FAIL** | B15-11 zero calibration across publishers | publishers agree on 18.26% of the 745 days compared; the noise floor is 0.1650 Bs at the median and 1.9550 at its worst |
| **FAIL** | B15-12 the referee | the published Bs/EUR against the ECB reference rate times the published TCO, over 39 days. **The registered expectation is not met.** The register wrote that if Bolivia's euro were Cuba's, a mechanical restatement of its dollar times a world cross, this criterion would measure the pass-through. The nearest alignment is lag 0 and its mean deviation is still 15 times the referee's own last digit, so the euro leg tracks the cross without restating it and carries information the dollar leg does not. The registered band of one tick of the euro series sits below the floor the referee's four decimals put under any reconstruction (61 ticks), so that band cannot be met on any alignment |

**Nine passes and voids against three failures, and none of the three is an
instrument breaking**: the reform ratified a rate the banks had already reached,
two publishers of one book disagree by more than a cross-publisher calibration
allows, and the euro leg is not derived from the dollar leg. **Each is a fact
about the carrier.**

**The official surface here has two legs that are not tied to each other**,
where Cuba's euro was its dollar restated and any cycle through it was zero by
construction. The wedge between the BCB's own published cross and the world's
is small, a median of two and a half times the rounding the two published
precisions allow, and **it is not inside the BCB's own table**: `1/ME` equals
`EUR/TCO` on all 39 days, so a cycle drawn through the published pair alone
still closes at zero. Using it means drawing the outside leg in explicitly.

## L2 — what is left of the tick-size move after the arithmetic is taken out, and it has the wrong sign to be arithmetic

**Opened on B14's carrier and free.** B14 closed with its index half
unadjudicated because projecting the post-release quotes back onto the nickel
lattice reproduces 88.7 per cent of the whole move. L2 asks the next question:
is the pure-slack residue arithmetic, or did behaviour change. Sample, windows,
the pure-slack definition and the group assignment are **imported from B14's
recheck, not restated**, so they are the same objects character for character.
Real segment 2016-08/09 to 2016-11/12; placebo segment 2016-06/07 to 2016-08/09,
entirely before the pilot took effect. Pure slack is 2,952 (venue, symbol) pairs.
Criteria fixed before the code, none rewritten after.

### Gate one, on market-maker participation

The cut: projecting quotes onto the nickel lattice is arithmetic **on the
quote**. It widens a spread without anybody changing their mind, so it predicts
no change in how market makers participate. Every other candidate requires
behaviour to change. Participation therefore separates "pure arithmetic" from
"something behavioural" with **no exposure variable at all**, which matters
because the participation appendix carries no market-maker identifier and so
could never serve as an exposure.

**Criterion: does the real segment's treated-minus-control gap fall outside the
whole placebo range.**

| quantity | outside | |
|---|---|---|
| `inside_quote` | **6 / 6** | by more than an order of magnitude |
| `share_prtcp` | 4 / 6 | |
| `mm_count` | 2 / 6 | the quantity is near-degenerate, see below |
| total | **12 / 18** | |

```
inside_quote  real  -1.1031  -0.9439  -1.0903  -0.6690  -0.6167  -0.6597
              placebo -0.0274 -0.1183 +0.0217 -0.0335 +0.0121 +0.0160
```

Six of one sign, two venues, three treatment groups, and the smallest real gap
is more than five times the largest placebo gap. In levels, control inside-quote
participation **rises** at the pilot (+0.4349 and +0.2877) while treated
participation **falls** (-0.5089 to -0.6682 and -0.3290 to -0.3814).

**The load-bearing part: the arithmetic predicts the opposite sign.** The
appendix's four buckets are a partition, so it is possible to see where the mass
went.

| bucket | real gaps, six |
|---|---|
| `inside_quote` | -1.1031 -0.9439 -1.0903 -0.6690 -0.6167 -0.6597, all negative |
| `at_quote` | +0.0927 +0.0270 +0.0924 +0.2485 +0.2634 +0.2836, all positive |
| `outside_quote` | -0.6105 -0.6115 -0.5904 / +0.0000 -0.0763 -0.4055 |
| `cross_quote` | -0.0748 -0.0376 -0.0641 -0.0548 +0.0137 +0.0525, inside the placebo scale |

Lattice projection rounds the bid down and the ask up. A trade that used to sit
**at** the bid, say a fill at 10.23 against a quote of [10.23, 10.35], is
strictly **inside** the projected quote [10.20, 10.35] and is reclassified.
**Pure arithmetic therefore predicts inside-quote participation goes up.**
Measured, it falls hard and at-quote participation rises. So this is not
arithmetic failing to explain the residue; **arithmetic predicted the wrong
sign.**

**Candidate zero is not withdrawn.** It still holds on the spread residue in
bin 1, and the two readings measure different things: the projection did widen
the spread, and it could not have pushed participation from inside the quote to
at the quote. Both stand.

**G1 is the discriminant and it points away from the trading-side rules.** G1 has
its quoting increment changed and nothing else; G2 adds a trading increment and
G3 adds trade-at on top. On NYSE, G1's inside-quote gap is **-1.1031, the most
negative of the three**, against -0.9439 for G2 and -1.0903 for G3. The
trading-side rules cannot reach G1, so they are not the main driver; a
behavioural response to the quoting rule can reach it, and the direction matches.

**A hook that is reported and not claimed.** The exemptions in Rule
6191(4)/(5)(A)/(6)(A), retail liquidity provision and midpoint passive orders,
are exactly the two order classes that can rest inside a five-cent quote, which
is the bucket that collapsed by 0.33 to 0.67 log units on the treated side. That
the exempted classes live in the bucket that shrank is a correspondence, not an
explanation, and using it would need its own registration plus an account of why
the bucket the exemption exists for is the one that lost mass.

**One quantity is retired here rather than reported.** `mm_count` is the log
difference of a median of small integers, and all four groups on one venue read
exactly +0.0000 in both segments: the median did not move, so the log difference
is identically zero. **Its 2/6 is neither evidence nor counter-evidence.**
`inside_quote` and `share_prtcp` are the two usable ones.

### Gate two, part B, on the spread residue

| group | quoting increment | trading increment | trade-at |
|---|---|---|---|
| **G1** | **changed** | unchanged | none |
| G2 | changed | changed | none |
| G3 | changed | changed | **yes** |

**No mechanical netting is needed and none is done.** The quoting increment is
identical for G1, G2 and G3, so the mechanical term is the same number in all
three and differences out of any comparison among them; netting it would import
the error in the estimate of delta while cancelling nothing. A selftest checks
that `run()` contains no floating-point constant at all.

```
group   real raw_gap (N, P)      placebo (N, P)
G1      +0.1349  +0.0355         -0.0593  +0.0066
G2      +0.1207  +0.0700         +0.0085  +0.0262
G3      +0.1332  +0.0732         -0.0153  -0.0024

G1 mean +0.0852   G2/G3 mean +0.0993   difference -0.0141
largest placebo gap in absolute value            0.0593
```

Five of the six real gaps exceed the largest placebo gap, so **the residue is
real**. And **G1 is on a par with G2 and G3: their difference, -0.0141, is
smaller than the placebo band, 0.0593.** The trading-side rules are not the main
driver, and the residue goes to candidate zero plus candidate four.

**This closes a candidate that had been open, and it closes it on the treatment
design rather than on replication.** The earlier approach asked whether two
venues agree; they gave opposite answers, so it was undecidable. This one asks
whether G1 carries the trading-side rules at all, which is a reading of the rule
text and not an inference from data. As a consequence the six-venue re-opening of
that candidate leaves the path and is registered as optional, which is 36
downloads not made.

**Reachability, checked before the run.** The branch "all three inside the
placebo band" was reachable: P/G1's real gap of +0.0355 sits inside the 0.0593
band. It did not fire, and not because it could not.

### Where the candidates stand

| candidate | status |
|---|---|
| zero, lattice projection | **holds on the spread residue in bin 1** (delta = 2.28 cents, residual +0.0045). **Refuted on the distribution of quote positions**: it predicts mass moving from at-quote to inside-quote and the measurement is the reverse |
| four, behavioural response to the quoting rule | **holds**, supported twice and independently: participation moving from inside the quote to at the quote, and G1 carrying the residue as strongly as G2 and G3 |
| two, the trading-side rules | **not the main driver** |
| three, spillover | **untouched**, and the sign argument still stands against it: spillover is symmetric across the two arms and cannot produce the positive contrast |

**The one open decision** is whether candidate three is worth a third gate. Against:
zero and four already occupy both ends of the spread residue, and spillover has
the wrong sign to begin with. For: assigning bin 2's +0.1110 to candidate four is
an inference and not a measurement, since gate one established that behaviour
moved without establishing that this particular behaviour is that particular
number.

**Two independent quantities on two different carriers both say G1 has
everything it should have.** The quoting increment on its own is enough to
produce the whole phenomenon; adding a trading increment and trade-at buys
nothing further.

## B1H

**8/8 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B1H-1  the filled 5x6 grid has no first cohomology | V=  30  E=  49  c= 1  b1= 20  rank d2= 20  dim H1=  0   cells=20   (b1_setup section 5 quotes b1=20, rank d2=20, dim H1=0) |
| PASS | B1H-2  deleting an interior grid edge is a puncture | b1 20->19, rank d2 20->18, c 1->1, dim H1 0->1   verdict=puncture   (section 5 quotes 20->19, 20->18, c fixed, 0->1) |
| PASS | B1H-3  deleting a dumbbell bridge is a disconnection | c 1->2, b1 2->2   verdict=disconnection   (section 5 quotes c 1->2 with b1 fixed at 2) |
| PASS | B1H-4  with no 2-cells, dim H1 = b1 | V=  30  E=  49  c= 1  b1= 20  rank d2=  0  dim H1= 20   (b1_theorem section 12.2 first row: no d1, so every 1-cochain is closed and dim H1 = b1) |
| PASS | B1H-5  dim H1(Gamma) = b1(G) + b1(H) on six shapes | star(4 tiers) x K3: 1 vs 0+1; star(4 tiers) x K5: 6 vs 0+6; star(4 tiers) x K8: 21 vs 0+21; cycle(4) x K3: 2 vs 1+1; cycle(4) x K5: 7 vs 1+6; cycle(4) x K8: 22 vs 1+21 |
| PASS | B1H-6  product_squares reproduces squares element for element | six shapes, walks compared as lists rather than as sets, so an ordering change would fail here rather than pass quietly |
| PASS | B1H-7  a connected deletion need not be a puncture | grid boundary edge: c stays 1, b1 20->19, rank d2 20->19, dim H1 0->0, verdict=neither.  Section 5's connectivity test separates a disconnection from the rest and does NOT separate a puncture from a no-event |
| PASS | B1H-8  the accreditation row is a puncture on a star G and not on a G with a cycle | STAR (tier_positions, the carrier section 5's rows live on): star m=3 k=1: 1->2 (puncture); star m=3 k=2: 1->2 (neither); star m=5 k=1: 6->9 (puncture); star m=5 k=2: 6->11 (puncture); star m=8 k=1: 21->27 (puncture); star m=8 k=2: 21->32 (puncture).  CYCLE G: cycle m=3 k=1: 2->2 (neither); cycle m=3 k=2: 2->2 (neither); cycle m=5 k=1: 7->7 (neither); cycle m=5 k=2: 7->7 (neither); cycle m=8 k=1: 22->22 (neither); cycle m=8 k=2: 22->22 (neither).  Section 5's verdict on the accreditation row holds on the star. The reason it gives, that nothing disconnects, holds in both columns and therefore is not the reason |

## B1 — the enlarged graph, and what stage B2 measured

500 cells enumerated over 25,942 loans `spread_bound=20.0`

**9/9 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B1-1  a shared potential annihilates every cycle | largest \|cycle sum\| over squares and a spanning basis, across 8 shapes: below 1e-10, at machine epsilon. Theorem 1, (1) implies (3) |
| PASS | B1-2  the squares detect what no single agent can see | 7/7 shapes where every w_a is exact but the potentials differ: slice cycles vanish below 1e-10, squares reach 4.272, and no global potential exists. A family of gradients need not be a gradient |
| PASS | B1-3  the path integral reconstructs the potential | largest \|d0 psi - omega\| over every edge after integrating along a spanning tree: below 1e-10, at machine epsilon. Theorem 1, (3) implies (2) |
| PASS | B1-4  the generating set spans the cycle space | rank of the slice-plus-agent-plus-square matrix equals E - V + C on Gamma, for all 8 shapes. The two are computed by different code paths sharing nothing |
| PASS | B1-5  the closed form for the first Betti number is right | m*e_G + n*e_H - m*n + 1 equals E - V + C for all 8 shapes: 2, 3, 16, 10, 39, 37, 26, 18 |
| PASS | B1-6  stage B2's within term is the holonomy of the squares | over 500 real cells holding 25,942 loans, the mean squared four-cycle sum computed by enumeration matches 2*Var to a relative error at machine precision, below `1e-10`, both per cell and in aggregate: 0.33793923 against 0.33793923. 4 cells above 2,000 loans were held out because enumeration is quadratic |
| PASS | B1-7  one agent class reproduces the one-index case exactly | at m=1 there are no squares at all and b1(Gamma) = b1(G). The enlarged graph is a generalisation, not a substitution |
| PASS | B1-8  the slice summand fires where the squares are silent | 5/5 shapes with a shared but non-exact field: slice cycles reach 15.0 while every square sum is exactly 0.0. The mirror of B1-2, and the case every other field in this repository makes vacuous by construction |
| PASS | B1-9  on a mixture each summand comes back out unchanged | 5/5 shapes: adding a pure-slice field to a pure-square one leaves both sets of cycle sums identical as raw bytes, slice reaching 15.0 and squares 22.0. Integer fields, so this is exactness and not a tolerance. Without it the split of Theorem 2 is checked on one summand and asserted on the other |

Derived quantities:

- `half_mean_squared_holonomy` = 0.3379
- `within_cell_variance` = 0.3379
- `worst_relative_error_per_cell` = 0.0000

## B2A — dispersion in financing terms at fixed position and date

20,071,740 loans `min_cell_size=20` `spread_bound=20.0` 160 rows outside the plausibility band

**7/7 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B2A-1  variance decomposition is exact | between 0.095178 + within 0.343669 = 0.438848 |
| PASS | B2A-2  dispersion survives fixing position and date | within share 0.7831 over 1,103,962 cells and 20,071,740 loans. Integrability predicts exactly zero |
| PASS | B2A-3  the median cell has a non-trivial spread | median within-cell IQR 0.5257 points, median p90-p10 1.0774, over 328,902 cells of at least 20 loans |
| PASS | B2A-4  restricting to well-populated cells does not weaken it | all cells 0.7831 over 1,103,962 cells; cells of at least 20 loans 0.8480 over 328,902 cells and 16,177,088 loans. Sparse cells have zero within variance by construction, so the unrestricted figure is the conservative one |
| PASS | B2A-5  it does not vanish within occupancy type | principal residence: 0.8289 (0.8502 restricted), second residence: 0.6155 (0.8418 restricted), investment: 0.3482 (0.5049 restricted) |
| PASS | B2A-6  the exclusion band is not doing the work | within share across bands 10:0.8475, 15:0.8478, 20:0.8480, 25:0.8481, 30:0.8482, 50:0.8484; range 9.61e-04. 160 of 20,071,900 rows lie outside +-20 and are not interest-rate differences |
| PASS | B2A-7  it survives with nothing excluded at all | ranked within share 0.7654 over 20,071,900 loans including every implausible row; 0.8181 restricted. A rank is bounded by the sample size, so no placeholder value can dominate it, and the integrable null still predicts exactly zero |

Derived quantities:

- `within_share_all_cells` = 0.7831
- `within_share_restricted` = 0.8480
- `bound_sweep_range` = 0.0010
- `within_share_ranked_nothing_excluded` = 0.7654

## B2B — vintage separation in the outstanding stock (H-zero, not H-one)

53 quarters, 2013Q1 to 2026Q1

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | L1  the vintage bound exceeds loop A's within-cell variance | 2026Q1: bound 0.8479 (sd 0.9208) against loop A's 0.3363 (sd 0.5799), read from results/b2_loop_a.json. Ratio 2.52. The bound understates loop B and the spread-versus-APR gap understates loop A, so the comparison is not clean in one direction |
| PASS | L2  it is positive in every quarter, not only after 2022 | 53 quarters from 2013Q1; smallest 0.3018. Before 2022: 36 quarters, smallest 0.3018. A wedge present only after the repricing would be an episode rather than a structural feature |
| PASS | L3  it is positive in every state | 51/51 state geographies positive at 2026Q1; smallest 0.7549 (HI), largest 0.9245 (SD) |
| PASS | L4  the null calibration is exact | all mass in one bucket gives 0.0e+00 (registered 0); half below 3% and half at or above 6% gives 2.250000 (registered 2.25) |

Derived quantities:

- `latest_variance_lower_bound` = 0.8479
- `smallest_across_quarters` = 0.3018
- `loop_a_within_cell_variance` = 0.3363

## B2A placebo validation — is the VA pool actually wide?

`min_cell_size=20` `spread_bound=20.0` 409,181 tract-years common to all programmes

**6/9 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | PW-0  every programme has cells at the headline threshold | loans in cells of at least 20: conventional 13,256,641, fha 2,295,274, va 1,098,949. A programme with none reports zero dispersion, which is an absence and not a narrow pool, and every criterion below would read it as the second |
| PASS | PW-1  the VA pool is wider than the FHA pool | within-cell dispersion, log income: VA 0.14545 against FHA 0.13994, conventional 0.27483; ranked income: VA 0.05271 against FHA 0.04887, conventional 0.05396 |
| **FAIL** | PW-2  the VA pool is comparable to the conventional pool | VA over conventional: log income 0.5292, ranked income 0.9769, against the registered floor 0.80. Loan-limit truncation biases the log-income ratio down and cannot touch the ranked one |
| **FAIL** | PW-3  the graded grid converts pool width into rate dispersion | rate dispersion per unit of ranked-income dispersion: conventional 6.336, VA 5.168, FHA 7.445. A pure pool-width account makes this ratio constant across programmes |
| PASS | PW-4  debt-to-income does not contradict the premise | within-cell variance lower bound: VA 52.7425, FHA 33.4032, conventional 45.2571. FHA and VA underwrite to higher ceilings, which inflates both, so a pass here is weak and only a failure would be strong |
| PASS | PW-5  the three samples are comparable at all | largest deviation from the mean missing rate is 0.0056 on income against 0.10; income conventional 0.0137, fha 0.0058, va 0.0047; dti conventional 0.0073, fha 0.0058, va 0.0033 |
| PASS | PW-6  negative control: the down-payment rules pin loan-to-value | within-cell dispersion of LTV: conventional 226.009, VA 84.795, FHA 26.428. A check on the instrument and not on the pool: the rules pin LTV for both government programmes and a method that cannot see that is not measuring dispersion. A failure voids the rest |
| **FAIL** | PW-7  the minimum-size threshold is not carrying the verdict | PW-1 and PW-2 together, evaluated at every folded threshold: log_income@10000 at 5 fails; rank_income at 5 holds; log_income@10000 at 20 fails; rank_income at 20 holds; log_income@10000 at 50 fails; rank_income at 50 holds |
| PASS | PW-8  the plausibility band is not carrying the verdict | PW-1 and PW-2 on log income at each income band: 1000 fails; 10000 fails; inf fails. Rows removed at the headline band: conventional income 0.000104, ltv 0.000073, fha income 0.000072, ltv 0.000096, va income 0.000078, ltv 0.000032. LTV dispersion by band, conventional: 110 225.739, 150 226.009, inf 91970479.005 |

## B2A placebo — conventional against FHA and VA

`min_cell_size=20` `spread_bound=20.0` `registered_min_gap=0.05` 409,181 tract-years common to all programmes

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | P1  conventional exceeds VA by more than the registered margin | conventional 0.8480 - VA 0.6666 = +0.1814 (registered > 0.05); ranked 0.8181 - 0.7325 = +0.0855 (registered same sign). VA has a wide pool and a flat price grid, so the pool-width account predicts VA near conventional and this is where it fails or survives |
| PASS | P2  conventional exceeds FHA | conventional 0.8480 vs FHA 0.4757 = +0.3722. Both accounts predict this sign, so it grades the effect and discriminates nothing |
| PASS | P3  both hold on tract-years common to all three programmes | common tract-years: conventional 0.8608, FHA 0.4747, VA 0.6664; conventional - VA = +0.1944. Removes the geography difference between where the programmes lend |
| PASS | P5  the gap clears a gap whose true value is zero | conventional - VA = +0.1814 against a split-half null whose largest absolute gap over 20 random halvings of the conventional sample is 0.0014 (median 0.0005) |

Derived quantities:

- `conventional` = 0.8480
- `fha` = 0.4757
- `va` = 0.6666
- `gap_conventional_minus_va` = 0.1814
- `split_half_null_largest_gap` = 0.0014

## B3

Record with no criteria block, kept as evidence and named here so it is findable: `results/b3_cip_slice.json`. This stage registers outcome maps rather than pass-or-fail rows: the verdict is which branch a reading landed in, and a branch label out of an exhaustive set is not a shape a criteria table can hold.


## B4 — the directed theorem

`shapes_drawn=24`

**9/9 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B4-1  Theorem 4: Bellman-Ford agrees with cycle enumeration | 24 agree, 0 disagree over 24 graphs; 5 admit a sub-potential and 19 carry a positive cycle |
| PASS | B4-2  the returned potential satisfies every edge inequality | worst breach 0.000e+00 over 5 potentials against 1e-09 |
| PASS | B4-3  Theorem 5: a sink component gives an unbounded ray | 31 graphs with a proper sink; the worst violation over shifts up to 1e+06 is at machine precision for that scale, below 1e-09 |
| PASS | B4-4  Theorem 5: strong connectivity bounds the polytope | 24 strongly connected graphs; every proper subset breaks (smallest breach 1.000e+06); every coordinate interval is finite, non-empty and contains the returned potential, widest 2.055 |
| PASS | B4-5  Theorem 6(1): the symmetric part is non-positive | worst w_bar -4.284e-04 over 24 fields against 1e-09 |
| PASS | B4-6  Theorem 6(3): the antisymmetric case reproduces Theorem 1 bitwise | 12 fields, 0 mismatches; potentials compared as raw bytes after centring on the minimum |
| PASS | B4-7  section 5.1: the directed square splits into friction and index | \|S+S' - friction\| and \|S-S' - index\| are both at machine precision, below `1e-10`, over 226 squares |
| PASS | B4-8  section 5.1: a common spread moves the friction and not the index | index unchanged to machine precision, below `1e-10`; friction moved by at least 2.223e-01 |
| PASS | B4-9  Theorem 6(4): the index part is bounded by the friction part | `S <= 0 and S' <= 0` and `\|S-S'\| <= -(S+S')` agree on all 226 squares, 52 of which have both cycles non-positive; the bound is what Theorem 4 buys once it is applied to each cycle rather than to their sum |

## B5 source audit — the friction column has no source (REJECT)

The verdict is in the heading, which is where it belongs: this is a source audit and not a set of pre-registered criteria, so there is no table under it and there never was one.


## B5 source audit — the P2P control class has no usable source (REJECT)

The verdict is in the heading, which is where it belongs: this is a source audit and not a set of pre-registered criteria, so there is no table under it and there never was one.


## B5 pre-window guards — the edge premium reads 4.83x and 9.80x with no threshold in either leg, and the pre-window is measured to turn inside itself

**1/1 live criteria passed.** B5-14 is void and therefore in neither the
numerator nor the denominator: a criterion the run could not evaluate is not a
criterion the run failed.

| | criterion | detail |
|---|---|---|
| **VOID** | B5-14 whether a pre-existing trend can be read off this pre-window at all | Treated series turns inside the window: maximum at bucket 3, minimum at bucket 8 of 12. Series 0.314, 0.609, 0.814, 0.803, 0.630, 0.446, 0.373, 0.168, 0.280, 0.291, 0.274, 0.387. The fitted slope, −0.034792 per bucket, is set by where the series turned rather than by where it ended, so it cannot be extrapolated past the edge and the arm returns no verdict about the world. Slope differences against the three controls imply shares 0.898, 0.775, 0.844 of a 0.4488 collapse; **these are printed and compared to nothing.** Second rung, 24 buckets, turns likewise at 7 and 20 |
| PASS | B5-15 the premium at the window's edge, no threshold in either leg | (a) last pre bucket 0.3866 against post max 0.0801, 4.83x; (b) treated ratio 8.21 against the closest control informal-mep at 0.84, 9.80x; no threshold in either leg |

**Recorded 2026-08-11 as FAIL against a band of 0.25, withdrawn 2026-08-21.**
Two reasons, either sufficient. `D5`: the band had no theoretical source, being
the factor of four B5-3 and B5-6 use for a detection ratio, which is a different
quantity in a different role, and an arbitrary calibration value may not ground a
negative finding. Discipline 11: a criterion may not draw a line across an
estimator, and with the three shares inside a span of 0.12 the verdict was a step
function of where the band sat. The registered consequence, that B5-8's collapse
enters the headline as confounded with a pre-existing trend, **is withdrawn and
nothing replaces it**; it was not available on the day it was written.
`docs/b5_orphan_prereg.md` §6A void section and §11 carry the full entry. **B5-15 is
untouched: it never had a threshold.**

## B5 — the agent index on one conversion, and what the April 2025 intervention did to it

**5/5 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B5-1 walked square equals the closed form | at machine precision, below `1e-10`, against a tolerance of 1e-12, over 1,457 dates |
| PASS | B5-2 trivial square is exactly zero | worst diagonal 0.0e+00, off the same matrix every other number comes from |
| PASS | B5-6 headline clears the noise floor | S/N 385 against 4, floor 2.601e-03 from the calibration arm |
| PASS | B5-7 squares do not vanish before the intervention | pre-window rms 0.4996 over 236 dates, S/N 192 |
| PASS | B5-8 treated premia collapse, untouched ones do not | treated 0.102, 0.110, 0.177 (<= 0.333); control 0.712, 1.050, 0.999 (>= 0.667) |

## B5 calibration — the wholesale market read by two parsers

**2/2 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B5-4 two formats, each parser refuses the other | byte-identical False, cross-refusals True/True |
| PASS | B5-3 two parsers agree within the derived bounds | median 2.601e-03 against 0.02, 0 dates over 0.5, on 1,648 dates |

## B6-A — reachability typing inside the central bank's own table (the H-one arm is not in this half)

207 publication days, 2025-12-19 to 2026-08-12, `segment_channel=efectivo_ventanilla`

**9/10 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B6-1 the walked square equals the closed form | 16,098 squares over 4 two-sided channels of the float; worst departure below 1e-12 on both the index and the friction part |
| PASS | B6-2 the trivial square is exactly zero | read off the diagonal of the same matrix, not short-circuited; worst diagonal exactly 0.0 |
| PASS | B6-3 known answer: every pair of published columns | 1,763,580 comparisons, 190 pairs per date per file; exact against the truncated schedule, and drift from the ideal ratio stays inside the derived tolerance. A floor, not a finding |
| **FAIL** | B6-4 the implied euro cross matches an outside reference | 147 publication days carry an ECB reference and 60 do not; worst relative deviation 1.134% against a band of 1.0%, exceeded on 3 dates (2026-03-02, 2026-04-08, 2026-06-18). Each sits on a day the reference itself moved about a percent with the sign reversed; a one-business-day lag leaves 0 outside the band, reported and not re-registered |
| PASS | B6-5 the segment triangle is zero | implied EUR/USD agrees across the three segments on 207 dates, spread below 1e-12; cross ranges 1.1359 to 1.1977 |
| PASS | B6-8 the agent and position factors are separable | 5,174 ladder rungs over 13 currencies and 199 dates; worst relative departure 0.0018% at JPY III 2026-06-18, against a tolerance derived per currency per date. 0 rungs outside it |
| PASS | B6-6a maximal reading: no sub-potential exists | believing the published columns leaves a positive directed cycle on all 207 publication days, worst 3.2181; Bellman-Ford and enumeration agree on every date |
| PASS | B6-6b directed reading: not strongly connected | removing the two agent edges the regulation does not grant restores a sub-potential on all 207 dates; three components, sinks exactly [1, 3] |
| PASS | B6-6c the one-sided bound clears the float's band | segment I at least 2.7932; segment II at least 1.1838 against 4 x 0.0939 = 0.3756 |
| PASS | B6-7 the distance grows across the window | segment I 2.7981 to 3.2181; segment II 1.1887 to 1.6087 |

Derived quantities:

- `float_band_width` = 0.0400
- `four_bands` = 0.3756
- `smallest_distance_segment_I` = 2.7932
- `smallest_distance_segment_II` = 1.1838
- `worst_cycle_sum_maximal` = 3.2181

## B6-B

**9/9 live criteria passed, 1 void**

| | criterion | detail |
|---|---|---|
| PASS | B6-9 retrieval integrity | 2,056 of 2,056 days, 0 empty, 11 probe windows compared and 0 disagreeing; independent replay checked 7 with 0 disagreeing |
| PASS | B6-10 the known-answer arm | 2021-01-01 USD 40.0 against 40.0; 2025-09-30 EUR 500.0 against 500.0; 2026-08-11 USD 670.0 against 670.0 |
| PASS | B6-11 the informal edge has no friction column | asking for either side raises, and no reporting path names one |
| PASS | B6-12 a positive substituted cycle is not a finding | positive under substitution, which is an upper bound and therefore NOT established |
| PASS | B6-13 the euro crosses disagree, and the disagreement decays | 207 publication days, margin 27; floor 0.00328, band 0.01311; first block 0.05595, last block 0.01547; the verdict flips only if one hour holds 44% of a day's offers |
| PASS | B6-14 three claims on the dollar, three prices | USD/MLC 3 regimes, 94.3% against a null whose 99th percentile is 75.2%; tether 4 regimes, 85.9% against 62.4%; median \|log(USD/MLC)\| 0.2719 against a widest official round trip of 0.0939 |
| PASS | B6-15 the posted return leg does not clear the informal market | a(t) positive on 100.0% of 207 publication days; critical spread 0.0507 against a threshold of 0.02; a runs 0.0070 to 0.1925 |
| PASS | B6-16 assumption A1, measured on the dollar leg | published median inside the book on 95.4% of 1,321 days; 61 above the ask, 0 below the bid |
| VOID | B6-17 the informal round trip, measured | VOID: the round trip is measured 2021-07-23 to 2025-03-04 and the critical spread it is compared against is measured over B6-A's window from 2025-12-19. The spans do not overlap and cannot be made to: the order book ends before the window opens. The distribution stands as a reading: median 0.0148, p90 0.0392, p99 0.0747, max 0.1214 over 1,321 days |
| PASS | B6-18 the zero calibration the stage did not have | two paths to the same daily number over 1,321 days: median \|log gap\| 0.0000 against a median round trip of 0.0148; 112 days beyond one round trip, 18 beyond two |

## B7

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b7_class_noise_draws50_reps20.json`, `results/b7_class_noise_drop2_draws50_reps5.json`, `results/b7_gate_coarse_draws50_reps20.json`, `results/b7_gate_draws50_reps20.json`, `results/b7_interaction_rank.json`.

### b7_carry

16,035,398 loans

**6/6 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-11ctrl  coarse: the carry reproduces this partition's own reading | **2 fine directions clear this partition's `null_max` of 0.3931, and the partition's own observed rank is 2.** The largest carried value is direction 1 at 1.437 against this partition's observed `lambda_1` of 1.453, a ratio of 0.9892.  §3.21 replaced §3.20's control with this one: the old one required **direction 1** to carry, on the ground that both partitions read at least rank one. That is a quantifier error. Reading rank one means **some** direction carries and says nothing about which. This control asks the question the old one meant to ask and has power the old one did not |
| PASS | B7-11  reported, not gated: coarse carries direction 2 | fine `lambda_2` = 0.7544 arrives as **0.7382**, fraction **0.9786**, against this partition's own `null_max` of 0.3931: **it clears**, so this index could have shown the fine grid's second direction.  The observed rank on this partition is 2.  §3.20's table says what each combination does to §10.6 |
| PASS | B7-11m  reported, not gated: coarse manufactures an interaction | the fine class main effect alone, coarsened, arrives as **2.507e-05** against `null_max` 0.3931.  **Below it.** The coarsening manufactures nothing this index can see, and §10.5's comparison is clean on this point |
| PASS | B7-11ctrl  complement: the carry reproduces this partition's own reading | **0 fine directions clear this partition's `null_max` of 0.241, and the partition's own observed rank is 0.** The largest carried value is direction 4 at 0.1663 against this partition's observed `lambda_1` of 0.2241, a ratio of 0.7421.  §3.21 replaced §3.20's control with this one: the old one required **direction 1** to carry, on the ground that both partitions read at least rank one. That is a quantifier error. Reading rank one means **some** direction carries and says nothing about which. This control asks the question the old one meant to ask and has power the old one did not |
| PASS | B7-11  reported, not gated: complement carries direction 2 | fine `lambda_2` = 0.7544 arrives as **0.003593**, fraction **0.0048**, against this partition's own `null_max` of 0.241: **it does not clear**, so this index cannot carry the fine grid's second direction even if that direction is real.  The observed rank on this partition is 0.  §3.20's table says what each combination does to §10.6 |
| PASS | B7-11m  reported, not gated: complement manufactures an interaction | the fine class main effect alone, coarsened, arrives as **0.0004031** against `null_max` 0.241.  **Below it.** The coarsening manufactures nothing this index can see, and §10.5's comparison is clean on this point |


**2/2 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-13 within_entry  reported, not gated: no interaction, lower bracket | a field with **zero interaction** at each class's within_entry dispersion reads back `>= 1` in **20/20** repetitions and exactly `2` in **20/20**.  Recovered `lambda_1` = 0.9137 +- 0.0079 against the observed 1.4674, `lambda_2` = 0.6164 against 0.7544.  Leading direction is **>60%** in 20/20.  §3.25: reading back `2` here confirms the mechanism behind B7-4's withdrawal; reading back `0` leaves the withdrawal standing on §3.24's table and the explanation unknown |
| PASS | B7-13 within_cell  reported, not gated: no interaction, upper bracket | a field with **zero interaction** at each class's within_cell dispersion reads back `>= 1` in **20/20** repetitions and exactly `2` in **20/20**.  Recovered `lambda_1` = 1.3945 +- 0.0133 against the observed 1.4674, `lambda_2` = 0.7007 against 0.7544.  Leading direction is **>60%** in 20/20.  §3.25: reading back `2` here confirms the mechanism behind B7-4's withdrawal; reading back `0` leaves the withdrawal standing on §3.24's table and the explanation unknown |


**2/2 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-13 within_entry  reported, not gated: no interaction, lower bracket | a field with **zero interaction** at each class's within_entry dispersion reads back `>= 1` in **5/5** repetitions and exactly `2` in **0/5**.  Recovered `lambda_1` = 0.2189 +- 0.0009 against the observed 0.2755, `lambda_2` = 0.2145 against 0.2232.  Leading direction is **46** in 5/5.  §3.25: reading back `2` here confirms the mechanism behind B7-4's withdrawal; reading back `0` leaves the withdrawal standing on §3.24's table and the explanation unknown |
| PASS | B7-13 within_cell  reported, not gated: no interaction, upper bracket | a field with **zero interaction** at each class's within_cell dispersion reads back `>= 1` in **0/5** repetitions and exactly `2` in **0/5**.  Recovered `lambda_1` = 0.2127 +- 0.0009 against the observed 0.2755, `lambda_2` = 0.2088 against 0.2232.  Leading direction is **46** in 5/5.  §3.25: reading back `2` here confirms the mechanism behind B7-4's withdrawal; reading back `0` leaves the withdrawal standing on §3.24's table and the explanation unknown |

### b7_crossfold

16,035,398 loans 326,872 cells x 19 classes

Derived quantities:

- `lambda1_17class_balanced` = 0.0229
- `off_diagonal_share_of_lambda1` = 0.3643
- `z_lambda1` = 13.3222
- `z_lambda2` = 16.0380
- `z_ordering_tau` = 7.0628
- `z_corr_v1_class_profile` = 5.0866
- `z_corr_v1_profile_slope` = 2.3189
- `profile_slope_separability` = 0.1501
- `naive_lambda1_same_sample` = 1.4674
- `z_ordering_tau_19class_control` = -1.1654


### b7_crossfold_depth

16,035,398 loans 326,872 cells x 19 classes

Derived quantities:

- `min_usable_share` = 0.1274
- `max_usable_share` = 0.9805
- `median_usable_share` = 0.6259


### b7_design

326,872 cells x 19 classes

**3/3 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-9a  the decomposition is exact | within 0.327720 = between-class 0.099490 + within-class 0.228230, residual 2.776e-17. An identity, so a failure here is the code and nothing else |
| PASS | B7-9b  every retained loan lands in exactly one class | 16,035,398 of 16,035,398 retained loans placed; dropped before the design: 164,692 blank and 4,253 filer-exempt, counted separately because they are different absences |
| PASS | B7-9  reported, not gated: what this class index touches | **share of stage B2's within term carried by the class index: 0.3036**.  19 classes over 326,872 cells, 16,035,398 loans.  distinct classes per cell min/q1/median/q3/max = 3/12/14/16/19.  **fill = 0.7222**, against the 0.60 at which §3.5's sweep still recovered a constructed rank exactly, so B7-0 is may pass |


**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-0  structural: every available arm completed every repetition | 3 of 3 available arms ran, 20 repetitions each.  **This is the only gated criterion in the file.** It is about the code having finished and not about what it found; VOID 1 removed every threshold on a result |
| PASS | B7-0c  reported, not gated: size, constructed rank 0 | **0/20 = 0.000** against a nominal of 1/(d+1) = 0.0196.  P(at least 0 \| 20, 0.0196) = **1.0000**, one-sided: the primary null is inflated by the class main effect it redistributes, so the nominal is an upper bound and only a rate **above** it is informative.  calibration achieved on this arm: l1/obs 0.2022 sd 0.0017 |
| PASS | B7-0a  reported, not gated: size, constructed rank 1 | **0/20 = 0.000** against a nominal of 1/(d+1) = 0.0196.  P(at least 0 \| 20, 0.0196) = **1.0000**, one-sided: the primary null is inflated by the class main effect it redistributes, so the nominal is an upper bound and only a rate **above** it is informative.  calibration achieved on this arm: l1/obs 1.2284 sd 0.2176 |
| PASS | B7-0b  reported, not gated: power, constructed rank 2 | **20/20 = 1.000** of repetitions returned the constructed rank, Wilson 95% [0.839, 1.000].  No nominal exists for a power arm, so there is an interval here and no line.  calibration achieved on this arm: l1/obs 1.3235 sd 0.3174  l2/obs 1.1734 sd 0.1464 |


**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-0  structural: every available arm completed every repetition | 3 of 3 available arms ran, 20 repetitions each.  **This is the only gated criterion in the file.** It is about the code having finished and not about what it found; VOID 1 removed every threshold on a result |
| PASS | B7-0c  reported, not gated: size, constructed rank 0 | **0/20 = 0.000** against a nominal of 1/(d+1) = 0.0196.  P(at least 0 \| 20, 0.0196) = **1.0000**, one-sided: the primary null is inflated by the class main effect it redistributes, so the nominal is an upper bound and only a rate **above** it is informative.  calibration achieved on this arm: l1/obs 0.1989 sd 0.0017 |
| PASS | B7-0a  reported, not gated: size, constructed rank 1 | **0/20 = 0.000** against a nominal of 1/(d+1) = 0.0196.  P(at least 0 \| 20, 0.0196) = **1.0000**, one-sided: the primary null is inflated by the class main effect it redistributes, so the nominal is an upper bound and only a rate **above** it is informative.  calibration achieved on this arm: l1/obs 1.0245 sd 0.0410 |
| PASS | B7-0b  reported, not gated: power, constructed rank 2 | **20/20 = 1.000** of repetitions returned the constructed rank, Wilson 95% [0.839, 1.000].  No nominal exists for a power arm, so there is an interval here and no line.  calibration achieved on this arm: l1/obs 1.0400 sd 0.0575  l2/obs 1.0383 sd 0.0462 |

### b7_hetero

16,035,398 loans 326,872 cells x 19 classes

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-14  reported, not gated: the seventeen-class design against its own null | dropping 50%-60%, >60% and re-applying MIN_CELL_SIZE gives 323,830 cells and 15,811,056 loans; spectrum 0.2755, 0.2232, 0.2193, 0.2148 against its **own** `null_max` of 0.2333, **rank 1**.  §3.25 compared that spectrum to the nineteen-class design's null, which is a different design's null and is expected to be too high because the two dropped classes are the two largest noise sources.  **§3.26 is the correction and this line is the number it needed** |
| PASS | B7-12b  reported, not gated: how much of S is off the diagonal | off-diagonal mass / diagonal mass = **0.8026**; off-diagonal correlations max \|r\| = **0.1417**, mean \|r\| = 0.0528.  Dropping the two thinnest classes (>60%, 50%-60%): max \|r\| = 0.1417, mean \|r\| = 0.0493.  **Noise lands on the diagonal and nowhere else**, so a near-diagonal `S` has no interaction for a rank to count, whatever its eigenvalues are. §3.24 declares the three readings |
| PASS | B7-12a  VOIDED by §3.24, computed and printed only: does class-specific noise account for the two leading diagonals | **50%-60%**: 1.37 loans per entry, S(a,a) = 0.7477, noise predicts [0.6363, 0.7247]; **>60%**: 1.18 loans per entry, S(a,a) = 1.4471, noise predicts [0.9396, 1.4469].  **§3.23's table is voided by §3.24 and this line is not a verdict.** The upper bound is nearly an algebraic identity for a class at one loan per entry, the lower bound is estimated on the entries holding two or more and therefore on a different population from the one it bounds, and the table compared both to `S(a,a)` with exact inequalities and no width. B7-12b above replaces it |
| PASS | B7-12c  structural: the two leading directions are the two thinnest classes | thinnest two by loans per entry: >60%, 50%-60%.  B7-11's `v1` is a near-pure indicator on `>60%` and `v2` on `50%-60%`.  **This criterion is about the coincidence and not about its cause**: a failure here would mean §3.23's premise is wrong and the whole arm is misdirected |


**5/5 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B7-1  the estimator recovers a constructed rank on a near-complete design | fill=0.85, constructed -> estimated: 0->0, 1->1, 2->2, 3->3.  Scope: this says the estimator works where the design supports it. B7-4 is where it stops working |
| PASS | B7-2  a field with no interaction returns rank zero at every fill | constructed rank 0, fill -> estimated: 0.85->0, 0.6->0, 0.35->0, 0.2->0, 0.15->0.  **This is the one reading that survives everywhere**, and it is the zero-versus-non-zero split rather than the trichotomy |
| PASS | B7-3  permuted data returns rank zero through the identical path | estimated rank 0 on a permutation of a true-rank-2 sample, taken through the same centring and the same second-moment matrix rather than short-circuited |
| PASS | B7-4  reported, not judged: where the estimator stops working | fill 0.85: 0->0/1->1/2->2/3->3  fill 0.6: 0->0/1->1/2->2/3->3  fill 0.35: 0->0/1->1/2->3/3->3  fill 0.2: 0->0/1->1/2->3/3->6  fill 0.15: 0->0/1->1/2->3/3->1.  The gated form of this criterion asserted the error runs upward and never downward; that assertion is REFUTED by this sweep and was withdrawn on 2026-08-15 rather than restated until it passed. Outside its usable regime the estimate is unreliable in either direction, and a `rank >= 2` result is not admissible without B7-0 |
| PASS | B7-0  the gate is implemented and is not vacuous | a rank-one field at the observed signal strength, read back on the same design: fill 0.85 -> 1, fill 0.6 -> 3, fill 0.35 -> 4.  **A gate that passed everywhere would not be a gate.** It fails here on designs where B7-4 says it should, which is what makes a pass on the real design mean something |

## B8 — the modification triangle on Fannie Mae loan performance: eight of eight live criteria, on 49,649 modification loops and 35,659 deferral loops over 2,942,295 loans

2,942,295 loans

**8/8 live criteria passed, 1 void.** B8-4b does not run for want of C9, and
section 15.3 of the register fixes that as a gate that was never opened rather
than a criterion the stage failed.

| | criterion | detail |
|---|---|---|
| PASS | B8-0a | the gate holds on the split registered after the closed form was found. (i-a) runs on the clean cures whose every quiet month sits in its segment's modal cluster and requires an exact return to zero within floating-point tolerance; all six vintages pass. (i-b) is a reading and not a gate. What passes it is the qualifying count and not the ratio: max ratio reads 0.399 to 0.400 in every vintage because the path tolerance and the agreement bound share one 1/B, so the ratio is capped by the path filter itself and carries no independent information |
| PASS | B8-0b | the floor is MAD(omega - closed) on the clean-cure arm, 2.68e-08 to 5.22e-08, against a construction that predicts half a cent divided by the median balance, 3.03e-08. Two further quantities in this repository are also called a floor and one of them is a signal; they are named N_cure, N_placebo(L) and IB_RESIDUAL, and any quotation of a floor has to say which |
| PASS | B8-1 | necessary condition holds in all six vintages. Ratio 2,412,840 to 6,765,767; subtract the closed form for leg 1 and it is 2,135,051.8 to 6,632,538.5, a net-to-raw of 0.8849 to 1.0224, so at most 11.5 percent of the signal is construction. The threshold was demoted to a readability line rather than a significance test: corr(omega, closed) is +1.0000 in five of six vintages, which makes the residual instrument resolution rather than a sampling distribution. The leg-1 shortfall behind that subtraction is a constant integer month count, n1 - eff of 3.98 to 4.99, and not a proportion; section 21.6's discriminant does not settle it, since flat equals round(eff) on 0.5525 to 0.7137 of loops and on none of the six archives outright, though the residual class that would break the reading is zero at the median in all six. B8-1's verdict does not move on it: section 21.6 registered in advance that removing a quantity 1.2 to 1.6 times the measured leg 1 changes the net ratio by at most 11.5 per cent |
| PASS | B8-2 | sign agreement across windows. 29 readable cells of 32, all 29 same-sign with intervals clear of zero, in all five windows, and re-run under the far-corner curve construction with zero cells flipping. leg 2 came back positive in every readable cell where section 14.3 had registered negative, and is not small: \|leg2\|/\|leg1\| has a median of 3.67 |
| PASS | B8-3 | the two paths to the same state differ, and the verdict is carried by per-cell signs and permutation rather than by margin. Re-run under the far-corner construction: all six vintages keep their sign, permutation p is 0.001 throughout, and the per-cell sign counts are identical under both constructions. delta/N_cure is 5.78e4 to 4.30e6. The earlier exemption, that the gap ran two to four orders above the curve spread, used the wrong denominator and is withdrawn; at 2007Q1 the two are 1.4 times apart, not an order of magnitude |
| PASS | B8-4a | class ordering reproduces on fico_llpa9, the finest grid that clears both gates. Six vintages same direction, sign test p = 0.0312, three significant on their own and surviving equal-n. The loading monotonicity, median Spearman -0.82 and 6/6 negative, is a post-hoc reading, is labelled as one, and **no product on disk prints it**: section 3 of b8_4_class.md carries mean rank and span, not a Spearman, so that number is carried by this sheet alone and cannot be checked against the stage's own output (found 2026-08-19 by the number check below). Of eleven grids only five clear the floor of 20 and hang on the borrower rather than the house or the location, and the comfortable ones among them are the coarse ones |
| VOID | B8-4b | does not run, for want of C9. On (class x origination cohort) inside the Flex window every one of eleven grids has a minimum of 0 or 1. This is not a thin-cohort problem but the quantified form of a comparability one: the Flex window is 2017-2019, so the 2019Q1 vintage has at most a year of age in it and cannot complete a triangle, while 2002Q1 has fifteen. Section 15.3 registers this as not a failure of B8, and the branch table sends the second domain to corporate credit |
| PASS | B8-5 | read per cell and not pooled. 554 cells, 132 endpoint-stable, 20 with p < 0.05. Twelve of the twenty are on the two FICO grids and all twelve point the same way: conditional on already being delinquent, the lower the score the higher the share modified, with no counterexample across six vintages, three windows, five entry tiers and two grids. The label is an admission threshold that differs by class, not a hole: section 5 asks whether an edge never exists, and what was measured is a rate |
| PASS | B8-6 | satisfied by construction on B8-2 and a real test on B8-5, per sections 20.2 and 22.2 |

## B9 — the ETF creation triangle: eleven registered predictions, and the two that were designed so they could lose

**This stage's records carry no criteria block, and the reason is the same one
B10's section gives.** Its registrations are outcome maps: `§9·1` has four cells
(a zero / a resolvable non-zero / uninformative / fee-undetermined), `§10·1` has
four (pinned / composition / both / inconsistent-with-D1), `§11` has three, `§12`
has three, `§14·5` has five. The verdict is which cell a reading lands in, and a
cell label out of an exhaustive set is not a boolean. Exactly one record was ever
written in criteria shape, and it is the one rendered under `## B9-A §24` below.

**The carrier was chosen for being clean, and that is also its ceiling.** All
three positions are institutional objects rather than cuts of a continuum, so
"the reading is an artefact of how the states were cut" cannot apply here: there
is no grid to choose. **The immunity and the barrenness are the same fact**, and
the stage says so before any of the readings: with no grid to vary, it can supply
no cross-grid calibration either.

### The eleven registered predictions

| id | the bet | role | where it landed |
|---|---|---|---|
| **B9-0** | the degenerate loop returns exactly zero | gate | **re-labelled from test to construction check.** The reverse edge is implemented as the negation of the forward one, same state dict, same call, so `z = −x + x` **cannot fail**. 200,000 draws, zero non-zeros, because zero was the only reachable answer |
| **B9-A-1** | a measured zero: the reading is below its floor | load-bearing | **a resolvable non-zero.** The indicator part runs 1.050 to 5.083 times the measurement floor, **11 of 11 above 1**. This carrier has no zero, and the reason is measured rather than argued |
| **B9-A-2** | the ratio rises with stress | substantive | **9 of 11 rise**, median ratio 1.211, range 0.881 to 1.365 |
| **B9-A-3** | the closing leg is open only to authorised participants | reported, not estimated | institutional fact from the fund's own filings: the unit is **50,000 shares and indivisible**, and the wedge is 1.2 to 1.7 bp. **No price makes this edge appear**, so it is a hole and not a cost, and the two are never added |
| **B9-A-4** | `pi` is non-zero under stress and indistinguishable from zero when calm | calibration | **not constructible**, and that is a property of the carrier's topology rather than of the data. `pi` here is exactly `(V + d²)/(2V + d²)`, a monotone reparameterisation of mean premium over its own dispersion, matched to **8.09e-05**. It carries nothing about the size of the reading |
| **B9-A-5** | a free historical premium/discount table covering 2020 and 2022 exists | gate | **fails, and the reason is structural**: the disclosure rule covers the most recent calendar year plus the quarters after it, **and it replaced the older rule rather than adding to it. Nobody was ever required to retain that history** |
| **B9-A-6** | one venue's closing midpoint can stand in for the consolidated one | gate | **fails.** Listing venue 0.8975, four venues combined 0.5564, neither at the registered 0.90. **It is not rounded up**: 0.8975 is about fifteen fund-days short |
| **B9-A-7** | the reconstructed price survives the readings, not just the prices | direct criterion | **not usable.** `Δρ_c` goes **+0.06942 → +0.00010** and the four-cell verdict changes cell |
| **B9-A-9** | the redemption-side fee equals the creation-side fee | registered | **not run.** One day's work. Registered here so that "every registered prediction has a written disposition" is true again |
| **B9-B-1** | tick data with volume exists and has no size-dependent disclosure cap | gate | **passes.** Nothing has to be bought |
| **B9-B-2** | `pi` rises with order size over ADV | size channel | **route closed by derivation** |

**`B9-A-8` does not exist.** The numbering jumps from A-7 to A-9. That is a gap
in the register and not a lost prediction, written here so nobody looks for it.

### The outcome maps, and the cells they landed in

| map | the variable | landed | reading |
|---|---|---|---|
| §9·1 | the reading against the measurement floor | **resolvable non-zero, 4 cells** | 1.050 to 5.083, all eleven above 1. On the standard-deviation floor the same eleven run 3.64 to 17.61: **both columns are reported and the headline keeps the conservative one**, because a choice that changes no verdict should not be dressed up as a finding |
| §9·5 D1 | first-order autocorrelation of the signed reading | **rises, 10 of 11** | calm **+0.0762**, stress **+0.1211**. The noise null predicts a point, zero, **and calm was already positive before any stress comparison was made** |
| §9·5 D1b | the same after removing the daily cross-fund mean | **falls, 3 of 11** | calm **+0.0882**, stress **−0.0094**. So the per-fund loop persists on its own when calm, **and the amplification under stress is market-level rather than per-fund** |
| §9·5 D2 | share of days at a discount | **moves, 10 of 11** | 0.4532 → 0.5075. **A symmetric disturbance cannot move a share**, which is why this one is read on level and never on count |
| §10·1 | the variance decomposition | **both, 4 cells** | `V_c` ×2.518 and `V_e` ×2.130 with the mix barely moving, and `Δρ_c` = **+0.069132** |
| §11 | the cross term against a circular-shift null | **inside the body, 3 rows** | **0 of 22** cells at or above their own 95th percentile against a chance expectation of 1.1. The null's own floor is **0.09332**, which is **9.3 times** the tolerance that had been registered to be compared against |
| §12 | does the reconstruction survive the readings | **not usable, 3 rows** | the error is a fixed half-tick while the signal doubles under stress, **so a fixed error does most of its damage where the signal is smallest, which is the calm regime, which is the axis every reading here lives on** |
| §12·1 | the same question for the discount-share statistic | **the exception, and the asymmetry was predicted backwards** | 76% of the move survives and the direction holds. The registered row named the wrong side of the split; **the split is real and its handling still applies** |
| §14·5 | the gate-speed test mapped onto primary-market activity | **fund-flow, 5 cells** | the share of zero-change days **falls in 10 of 11**, and the intensive margin **rises in 8 of 11**. Under stress the primary market is both more frequent and larger. **The mapping onto this carrier is refused** |

### The two numbers that carry the most, and the one that carries the least

**Quantisation is refuted, and one fund is enough.** Across twelve US equity
funds the tick spans **15.83 times** while the median reading spans **1.42
times**. Quantisation noise must scale with the quantum and here it does not.
**And the comparison arm was excluded from this test before anything ran**: put
the stale-NAV funds back in and the same arithmetic reads "tick spans 26.0, the
reading spans 33.0", which is quantisation confirmed. The exclusion was
registered on the stale-NAV ground, not chosen afterwards.

**The threshold was earned by behaviour, and it was free.** The primary-market
unit is the gcd of non-zero share changes: **exactly 50,000, with 100% of changes
a multiple of it** on all eleven main-arm funds. Swept over eight candidate
values, **the cleared counts at 0 and at 50,000 are identical fund by fund**, and
nothing moves until the threshold passes 500,000. **A parameter that could have
been tuned until a zero appeared is shown to be untunable.**

**One quantity here is below the resolution of this window, and the day count
that would reach it is computed rather than guessed at.** `Δρ_c` is **0.693 of its
own standard error**, using the standard error of a difference between two disjoint
partitions of the same window and not one end's. Reaching two standard errors
needs about **3,348 trading days** against the 404 in hand, roughly 11.7 years at
one per day. **Nothing is concluded from it.** And the extrapolation that
produces that day count diverges: on the reconstruction arm the same formula
returns 1.7 billion trading days, because its divisor is near zero there. The
record carries a flag saying whether the point estimate exceeds its own standard
error, and a note saying the day count is readable only when that flag is true
and only as an order of magnitude.

### What this stage established, and what it could not

**Three of the four links hold. The fourth has no route, and both registered
routes were closed by derivation rather than by a negative measurement.** The
size gradient closed because the shock narrative and the framework **predict the
same curve**; the only shape that separates them is a jump at the 50,000 unit,
and that is visible only to participants whose trades the stage records as
unobserved. The collateral gate closed because **the servicing rule book fixes
the answer before the first loan is read**.

**One test in this stage was built so that it could lose, and it lost.** The
gate-speed test predicted the share of zero-change days would rise under stress;
it fell in ten of eleven. That is not a failure to report quietly. **It is the
only reading here that a competing account would have got wrong**, and what it
shows is that this carrier's hole is a contractual membership rather than a
collateral threshold: **a breathing hole moves with prices and a contract does
not**, and the test was aimed at the one that does not move.

**The general lesson the stage states about itself**: a shape is cheap. A
prediction has discriminating power because a competing account gets it wrong,
not because a competing account also gets it right. **A rate is a shape; a sign
is not.**

## B9-A-1

Record with no criteria block, kept as evidence and named here so it is findable: `results/b9_a1.json`. This stage registers outcome maps rather than pass-or-fail rows: the verdict is which branch a reading landed in, and a branch label out of an exhaustive set is not a shape a criteria table can hold.


## B9-A-2

Record with no criteria block, kept as evidence and named here so it is findable: `results/b9_a2.json`. This stage registers outcome maps rather than pass-or-fail rows: the verdict is which branch a reading landed in, and a branch label out of an exhaustive set is not a shape a criteria table can hold.


## B9 §31 variance decomposition

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b9_decomp.json`, `results/b9_decomp_control.json`, `results/b9_decomp_recon.json`.

## B9-A-2 discriminators

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b9_disc.json`, `results/b9_disc_control.json`, `results/b9_disc_recon.json`.

## B9-A §24

**2/2 live criteria passed, 1 diagnostic**

| | criterion | detail |
|---|---|---|
| PASS | B9-24-1  the disclosed price is a half-cent midpoint | off-grid share = 0.000 across 16 funds and 6464 reconstructed closes. Half a cent is not a price a trade can print at, so P is the closing NBBO midpoint and the reconstruction is exact rather than approximate. **Written after the data** (§24 exists because §4 was wrong); it could have failed, and a non-zero here would mean λ is not what this stage thinks |
| PASS | B9-24-2  \|λ\| does not scale with the tick, so it is not quantisation | on the 12 US-listed equity funds the tick spans 15.83x while \|λ\| spans 1.42x. Quantisation noise must scale with the quantum. SPY carries the point alone: its tick is the finest in the group and its \|λ\| is the same 1.7 bp as the rest |
| DIAG | B9-24-3  the same comparison inverts when the stale-NAV arm is pooled in | all 16 funds: tick spans 25.97x, \|λ\| spans 33.00x, which reads as quantisation confirmed. It is SPDW, SPEM and JNK carrying 11 to 39 bp of stale-NAV premium, a confound §6.1 registered before any of this ran. **This entry is here to show B9-24-2 could have failed**, and the first version of this run printed exactly this pooled line |

## B9-0

Record with no criteria block, kept as evidence and named here so it is findable: `results/b9_gate.json`. This stage registers outcome maps rather than pass-or-fail rows: the verdict is which branch a reading landed in, and a branch label out of an exhaustive set is not a shape a criteria table can hold.


## B9 §26 gate speed


### b9_datasets — the venue catalogue, enumerated before anything was selected

`results/b9_datasets.json` carries no `stage` key and no criteria, so nothing in
it is a reading. It is the vendor's own answer to eight questions asked before a
venue was chosen: for `ARCX.PILLAR`, `BATS.PITCH`, `DBEQ.BASIC`, `EQUS.MINI`,
`EQUS.SUMMARY`, `IEXG.TOPS`, `XNAS.ITCH` and `XNYS.PILLAR`, the date range the
dataset actually covers and the per-schema ranges inside it, plus the catalogue
listing itself. `ARCX.PILLAR`, for instance, begins 2018-05-01 rather than at
the start of the sample anyone would assume.

**This is D12 in its cheapest form**: take the catalogue, look at the whole set,
then select. A venue picked by name and found later to start three years into
the window costs a re-run; the same question asked of the catalogue first costs
one call.

## B9-A-1 and A-2 against the measurement floor (§24)

Record with no criteria block, kept as evidence and named here so it is findable: `results/b9_measured.json`. This stage registers outcome maps rather than pass-or-fail rows: the verdict is which branch a reading landed in, and a branch label out of an exhaustive set is not a shape a criteria table can hold.


## B9-A-6 four-venue (§39.3)

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b9_nbbo_combined.json`, `results/b9_nbbo_combined_sz100.json`.

## B9-A-6 (§36)

Records with no criteria block and no sample metadata, kept as evidence and listed so they are findable: `results/b9_nbbo_overlap.json`, `results/b9_nbbo_overlap_ARCX_PILLAR.json`, `results/b9_nbbo_overlap_ARCX_PILLAR_sz100.json`.

## B17 — how many independent directions the parallel-rate deviations occupy

**Carrier: Argentina's simultaneously quoted legal conversion tracks, daily, from
files already on disk. Nothing was bought for this stage.**

**Two carriers were rejected before this one and both cost paper only.** The
first was a GSE monthly mortgage panel: `b1` ran from 1275 down to 1 as the state
definition changed and no cut had a source, and the closing leg of the rulebook
triangle carried 121 transitions in one vintage and 1 in the other. The second
was competing unsponsored depositary receipt programs on one issuer. That design
assumed the competing programs are separately priced, and they are not:
Citibank's termination notice names CUSIP `150042109` for CECONOMY AG with
Citibank as depositary, and DTC notice 12945-20 lists the same CUSIP under Bank
of New York Mellon as depositary. `C` depositaries share one ticker, one CUSIP
and one ratio, and terminate jointly. The `2 <= r <= C` branch was therefore
unreachable by market structure rather than by thin data, so the stage never
opened on it. Iliev, Miller and Roth (JAR 2014) report the same thing directly,
along with the population: 1,194 unsponsored facilities on 748 firms, 186 firms
with two depositaries and 104 with three or more.

**A fourth specification for rank carriers was bought by that second rejection**,
alongside the three the first one bought: **the positions must be separately
priced in the market.** The test is whether each of the `C` positions has its own
quote symbol and settlement identifier. `C` positions sharing one identifier are
one position. Free, and answerable before anything is bought.

**What is measured.** Positions are ARS and USD. Each legal conversion track is
one parallel edge between them, so `b1 = E - V + 1 = C - 1`. The object is the
covariance of `dlog e * P`, where `P = I - 11'/C` projects the all-ones direction
out of track space, taken on daily changes with gaps longer than 7 days dropped.
Two class sets are run and both are reported: `C = 4` (`oficial`, `mep`, `ccl`,
`informal`) and `C = 5` (adding `mayorista`). The P2P track is excluded: its
liveness check reads a longest frozen run of 47 days against a threshold of 21.

**A structural check written into the pre-registration failed, and the
pre-registration is what was wrong.** It asked that both the rank and every
eigenvalue be unchanged when the reference track is swapped. The rank half is
right. The eigenvalue half is not: `Cov(R_ref) = M_ref' Sigma M_ref` is a
congruence, and a different basis of the same subspace has different eigenvalues.
Measured gaps across two references were `2.406e-04`, `1.932e-04`, `3.836e-04`
and `4.367e-05` against a tolerance of `1e-12`, so it fails by construction. It
was replaced by the zero-sum projection above together with three checks that are
invariant, and this happened before any eigenvalue was read.

| criterion | C4 full | C4 pre | C5 full | C5 pre |
|---|---|---|---|---|
| a. the `C-1` relatives rebuild every pairwise difference, tol `1e-12` | PASS `0.000e+00` | PASS `0.000e+00` | PASS `0.000e+00` | PASS `0.000e+00` |
| b1. all-ones direction carries no variance, and its eigenvector is `1/sqrt(C)` | PASS `3.51e-16`, align `1.000000000000` | PASS `5.76e-17` | PASS `2.56e-16` | PASS `1.03e-16` |
| b2. permuting the track order leaves every eigenvalue alone, tol `1e-12` | PASS `2.168e-19` | PASS `6.776e-20` | PASS `1.626e-19` | PASS `4.066e-20` |
| b3. every one-reference construction spans the same subspace | PASS `[3,3,3,3]` | PASS | PASS `[4,4,4,4,4]` | PASS |
| c. numerical rank of all pairwise differences equals `b1` | PASS `3` | PASS `3` | PASS `4` | PASS `4` |
| superseded: eigenvalues equal across two references | **FAIL by construction** `2.406e-04` | **FAIL** `1.932e-04` | **FAIL** `3.836e-04` | **FAIL** `4.367e-05` |

**The panel.** Four tracks are jointly quoted on 1,457 days from 2020-03-20 to
2026-06-29, giving 1,456 daily changes with zero gaps dropped; five tracks give
1,456 and 1,455. The registered pre-window gives 234 joint days and 233 changes.
Independently of the loader written for this stage, the carrier's own square
record reports `dates_checked = 1457`, the same integer. Per-track day counts
differ from that record by 4 to 5 days out of about 1,600, because this loader
does not apply the carrier's registered filter constants; the joint intersection
is unaffected. Every numeric token in the 105 source files has one shape,
`NNN,NN`, and no row was unreadable.

**The reading, four tracks, full window, `T = 1456`, all adjacent eigenvalue gaps
separated at 90 percent:**

| k | eigenvalue | share | loadings |
|---:|---:|---:|---|
| 1 | `3.2136e-04` | 0.4884 | ccl +0.6184, informal -0.3902, mep +0.3545, oficial -0.5828 |
| 2 | `2.5658e-04` | 0.3900 | ccl -0.1089, informal +0.7630, mep -0.0172, oficial -0.6369 |
| 3 | `8.0028e-05` | 0.1216 | ccl -0.5964, informal -0.1248, mep +0.7900, oficial -0.0688 |
| 4 | `-1.13e-19` | 0 | the all-ones direction |

Five tracks, full window, `T = 1455`, all gaps separated: shares 0.5762, 0.2850,
0.0794, 0.0594, with the fourth direction loading `oficial +0.7885` against
`mayorista -0.5867`.

**Verdict: `2 <= r <= b1`. The single-factor reading of the rate zoo is
rejected.** A single common gap factor requires the first eigenvalue to take
nearly all the variance. Measured `lambda2 / lambda1` is `0.798` on four tracks
and `0.495` on five, and the first gap exceeds its joint 90 percent resolution by
`1.84` and `5.54` times. The reading does not flip between `C = 4` and `C = 5`.

**One cell is undecidable rather than failed.** On four tracks in the pre-window,
`T = 233`, the first two eigenvalues are `1.2537e-04` and `1.0781e-04` and their
gap `1.757e-05` is smaller than their joint resolution `3.554e-05`, so the
loadings of that pair are not identified. The third eigenvalue in the same window
is separated and carries 5.8 percent. The registered three-way split has this
middle state in it; it is not a FAIL and it does not raise.

**A generous independent-noise null is also rejected, and it corrected the way
the loadings are read.** Taking each track's whole daily-change variance as its
own noise variance and projecting gives an almost flat spectrum: shares 0.3790,
0.3307, 0.2903 on four tracks against the observed 0.4884, 0.3900, 0.1216, so the
observed concentration ratio is `4.02` against the null's `1.31`, and `9.70`
against `1.68` on five tracks. **The same null showed that collinearity with a
single-track contrast cannot carry this reading on its own**: the null's own
eigenvectors reach `|cos|` of `0.9357` to `0.9984` with a single-track contrast,
while the observed second direction reaches `0.8810` to `0.9625`, and the two
ranges overlap. The spectrum is what separates the three stories; the cosines
say which regulatory boundary each direction sits on, and no verdict rests on
them.

**Where the directions sit.** On four tracks the second direction is `informal`
against `oficial`, the third is `mep` against `ccl`, and the first is the pair
`(ccl, mep)` against the pair `(informal, oficial)`. Adding `mayorista` adds a
fourth, `oficial` against `mayorista`. Read as boundaries: securities channel
against cash channel, parallel against official, onshore against offshore
securities dollar, and retail counter against wholesale.

**Levels are reported as a diagnostic and behave as the pre-registration said
they would.** On four tracks over the full window the level eigenvalues are
`4.949e-02`, `1.472e-03`, `3.300e-04`, the first taking 96.5 percent. That is one
non-stationary regime factor, which is why the criterion is on daily changes: on
levels only one outcome branch is reachable and it restates a result the carrier
already reported.

**Limits.** All five tracks come from one reporter, and a common reporting error
would push the rank toward one, which is the direction the opponent needs, so
this limit does not threaten the verdict. One country. Records:
`results/b17_rank.json` (structural half), `results/b17_rank_read.json` (the
reading), `results/b17_rank_null.json` (the null diagnostic); all three carry
`diagnostic_only` until the stage is closed.

**The same estimand was measured earlier on a different carrier, and the same
comparator was run against that carrier's committed record.** B7 measured the
rank of the non-integrable part of a price field on a US mortgage panel and
reported two dimensions, a tilt along DTI and a curvature of the ends against
the middle. Its two balanced arms are already the same construction used here:
their recorded all-ones components are `-1.17e-18` and `-5.66e-18`. Running the
independent-deviation comparator `P diag(d) P` on `results/b7_crossfold.json`,
with `d` the recorded cross-fold diagonal and two negative entries clipped to
zero, gives this, and nothing in B7 was re-run:

| arm | observed `l1` | comparator | ratio | observed `l2` | comparator | ratio |
|---|---:|---:|---:|---:|---:|---:|
| `drop_thinnest_2_balanced`, 17 classes | 0.022930 | 0.017470 | 1.31 | 0.014807 | 0.003536 | **4.19** |
| `all_19_balanced`, 19 classes | 0.485338 | 0.421973 | 1.15 | 0.067580 | 0.033689 | 2.01 |

**The comparator reproduces the number that stage already used.** B7 judged its
second eigenvalue against the second largest diagonal entry, `0.003582`; this
comparator's second eigenvalue is `0.003536`, a relative difference of `1.26`
percent, and `2.86` percent on the nineteen-class arm. Two constructions built
for different carriers meet on the same number.

**One quantity that stage did not report as a ratio**: the largest single
diagonal entry divided by the first eigenvalue is `0.8048` on the licensed arm
and `0.9169` on the nineteen-class arm, the latter being the `>60%` class. So the
first eigenvalue is largely one class's own variance, and the second is not,
which is the same fact as that stage's recorded `off_diag_part_of_lambda1` of
`36.43` percent, stated as a ratio.

**Two unrelated carriers reject the same two rival readings, and by opposite
routes.** Against a single common factor: on the mortgage panel the second
eigenvalue stands at `z = +16.04` against a permutation null, and here
`lambda2 / lambda1` is `0.798` with a separated gap. Against pure per-unit
independent deviation: on the mortgage panel the second eigenvalue is `4.19`
times its comparator, and here the spectrum is `4.02` times as concentrated as
its comparator against `1.31`. The mortgage panel is flatter than its comparator
and this carrier is steeper than its own, because their comparators differ in
shape: one class's diagonal dominates there (`0.0185` against a second largest
of `0.0036`), while the tracks here carry variances of one magnitude (`2.58e-04`
to `4.88e-04`). In both, the dimension is far below the number of observable
levels: nineteen DTI classes read two, six pairwise squares read three.

**What this carrier adds to that one is labels rather than numbers.** The
mortgage panel can say the non-integrable part is two dimensional and that the
two directions are a tilt and a curvature, but the market side of it is 11,264
anonymous cells and nothing external names what separates them. Here every
direction sits on a boundary with a name, an admission rule and a published
quote. Carried limits on the mortgage side are unchanged: rank two does not mean
standard econometrics cannot reach it, since interactive fixed effects is exactly
a two-way interaction of r factors; no causal reading; the measurement
explanation is not excluded there; cross-year stability was never measured; and
the magnitudes are 1.5 percent of what the naive estimator read. Code
`experiments/b17_b7_crossarm.py`, record `results/b17_b7_crossarm.json`, marked
`diagnostic_only`: it withdraws nothing and no criterion in either stage rests on
it.
