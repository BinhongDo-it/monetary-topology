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

**A criterion is not to be read out of its carrier.** Every criterion here was
registered against one construction, and several stations have since been read a
second time on a different one: with A3's asset layer added, at a different node
count, with an edge scope restricted. A pass or a failure on such a re-read is a
statement about that carrier and not about the station's registered reading,
which stays where it is and is quoted unchanged. Where the two disagree, both
are printed and the section says which construction each belongs to. Taking a
failure out of that context and reporting it as the station's result is the
error this paragraph exists to prevent.

**What `diagnostic_only` means on a record.** It gates nothing. The generator it
used to be read by was retired on 2026-08-21 and so was the runner ratchet, so
the field no longer excludes a record from anything, this ledger included.
It is a sentence the record says about itself, and it says one of three things:
the station is not closed yet, or this number has been superseded and the file is
kept as the evidence, or the run was made on a carrier the station did not
register. **Everything that produced a number is in this ledger**, whether or not
its record carries the field.

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

## A1 — the default cascade on crossed marginals

**2/2 live criteria passed, 1 void**

**Scope.** A1b carries the current construction for this station. What A1 establishes is the calibration identity below; **a level read off this construction is not a measurement of anything in the world**, and the criteria are written so that none is claimed.

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

## A1b — the cascade on a measured population: the K shape holds ordinally, one rule covers every rung, and the first-default reading is now split by tenure

**6/7 live criteria passed, 2 void**

| | criterion | detail |
|---|---|---|
| PASS | A1b-0 zero calibration, by removing the cause | income raised to cover each household's own obligations: every rung exactly 0.000000 over 24 periods |
| VOID | A1-2  the order is an output | void as registered: the estimator and the object do not line up. The pooled share is a distribution across households, decided both by how hard a rung is and by how many households stand on it, while its denominator is every defaulter. Rent is carried only by tenants and the mortgage only by borrowers. The ordering claim is carried by A1c, which reads the sequence inside one household and holds |
| PASS | A1-3  K shape, ordinally | mortgage 0.0027 < auto 0.0924 < card 0.1879. Over baseline: mortgage +0.0024, auto +0.0721, card +0.1249. Attached gate: cost_now names no class; every pair is the same rule applied to per-class attributes |
| PASS | A1-6  the subprime gradient | bottom 0.1438 against middle 0.0680, ratio x2.12. Published at 30 days on balances and reported only: 2000 5.33, 2019 5.85, 2024 5.58, 2025 5.40. The model is at ninety days, so the ratio is beside them and not against them |
| VOID | A1-7  the rent gradient | by net worth: bottom50 0.6577 (28,776), next40 0.3584 (2,888), next9 0.0000 (397), top1 0.1351 (37) [NOT monotone]. By income: bottom50 0.8129 (23,585), next40 0.1046 (7,581), next9 0.0000 (897), top1 0.0000 (35) [monotone]. Overall 0.6220 against SHED's 0.23, reported only: the source counts renters behind at some point in twelve months and this is sixty months of a model. Published by income band: 0.33/0.31/0.17/0.05. **The two readings of the registration disagree**, so this is reported on both and gated on neither. The source is banded by income and the model's strata are net worth, and A1 could not see the difference because it had one ranking |
| PASS | A1-9  the representative arm is degenerate | every rung of the collapsed household takes values in {0, 1} across all three tenures, which is Corollary 1 with a number attached: the difference between the arms is the population |
| PASS | A1-10 one parameter set across every rung | one rule, one attribute table, one grace table; every rung's pair is CARD 0.000/6, AUTO 0.117/3, RENT 0.250/4, MORTGAGE 0.083/12, BASKET 1.000/1 |
| **FAIL** | A1b-1 the delinquency gradient | LATE60 by net worth: bottom50 0.0847, next40 0.0163, next9 0.0022, top1 0.0026. Model over 6 sweep cells: seed 7x1 0.301/0.174/0.017/0.000  <-; seed 7x3 0.258/0.140/0.017/0.000  <-; seed 8x1 0.301/0.177/0.017/0.000  <-; seed 8x3 0.262/0.144/0.017/0.000  <-; seed 9x1 0.280/0.158/0.017/0.000  <-; seed 9x3 0.233/0.122/0.017/0.000  <-. Decreasing in every cell: True. Ordering matches the survey in every cell: False. Group sizes at 20,000 households: [9993, 7998, 1895, 114]. Including rent, reported only: 0.483/0.191/0.017/0.000. The target's smallest adjacent gap is 0.0004, which is what the ordering turns on |
| PASS | A1-11 free parameters within the registered bound | 5 free against 12: cost.commute_dependency=0.35, cost.access_penalty=1, cost.grace_basket=1, cost.grace_rent=4, population.buffer_months=1. A1 counted six; the service-share dispersion is measured here |


### First default by starting tenure, with each rung on its own denominator

Volume One section 18 states its cascade about tenants, so the rent rung belongs
inside the tenancy. Two denominators are reported for each rung: the share of that
tenure's defaulting households, and the rate per household that carries the rung at
all. The second is what the section 18 reading needs, since a renter without a car
loan cannot default on one. The structural zeros are a check on the split: a
mortgaged household carries no rent and an outright owner carries neither.

| tenure | defaulting | rung | share | households carrying it | per carrier |
|---|---|---|---|---|---|
| RENTER | 21,478 | rent | 0.4204 | 12,754 | **0.7080** |
| | | card | 0.3910 | 15,636 | **0.5370** |
| | | auto | 0.0897 | 10,618 | **0.1814** |
| | | basket | 0.0989 | 34,054 | 0.0624 |
| | | mortgage | 0.0000 | **0** | — |
| MORTGAGED | 10,168 | card | 0.5925 | 22,174 | **0.2717** |
| | | mortgage | 0.3852 | 31,970 | **0.1225** |
| | | basket | 0.0157 | 40,894 | 0.0039 |
| | | auto | 0.0065 | 18,481 | 0.0036 |
| | | rent | 0.0000 | **0** | — |
| OUTRIGHT | 4,646 | basket | 0.7256 | 25,052 | 0.1346 |
| | | card | 0.1879 | 7,472 | 0.1168 |
| | | auto | 0.0865 | 5,722 | 0.0703 |
| | | rent / mortgage | 0.0000 | **0** | — |

**Among mortgaged households the card goes first**, 0.2717 per carrier against
0.1225 for the mortgage, which is the manuscript's order. The pooled reading mixed
this tenure with the tenancy and produced a shelter aggregate that sat above the
card.

**Among tenants the rent goes first**, 0.7080 per carrier against 0.5370 for the
card and 0.1814 for the car loan, and switching to the per-carrier denominator
widens the gap rather than closing it: 3 points on shares becomes 17 points here.
So the car loan sitting last is not an exposure artefact. 10,618 of the 12,754
tenants carry one, and they still default on it far less often than on either of
the other two.

**Rent is the largest single obligation a tenant holds**, which is the reading this
supports: a rung is abandoned first because it cannot be met, and the cost rule
already prices shelter as supporting all of a household's earning capacity. That is
consistent with A1c holding: among households that fall behind on several rungs the
sequence inside the household is what the manuscript describes, with 2 inversions in
1,142, while which rung breaks first across the population is set by size.
## A1c — the order inside a household: the sequence holds with 2 inversions of 1,142, and all 13 inversions are attributed to the release clause

**2/2 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A1c-1 the sequence holds inside a household | card_before_auto: 607 in order, 533 tied, 2 inverted, of 1,142 in scope; auto_before_rent: 449 in order, 526 tied, 2 inverted, of 977 in scope; card_before_rent: 523 in order, 1,080 tied, 9 inverted, of 1,612 in scope. 17,499 of 20,000 households are in scope for no pair at all, which is the population A1-2 quantified over and the size of the mismatch between the claim and its cross-sectional form |
| PASS | A1c-2 every inversion is attributed | 13 inversions: 13 attributed to the release clause, the later class unsavable in the period it was first missed while the earlier one was savable; 0 unattributed |

## A1d — the cascade on a measured cushion

**Scope.** Liquid assets, no floor, and a matched twelve-month window. The top pair sits below both sides' resolution and is reported rather than scored.

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

## A2d — what selects the terminal distribution: not sigma, and not where issuance enters

`rounds=300` `seeds=5` `53 cells`

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A2d-1  every cell of all three grids ran and returned a finite share | sigma 24/24, structure 23/23, issuance 6/6; the stock-flow assertion in the loop held in every round of every cell |
| PASS | A2d-2  sigma's span on terminal top1% wealth against the structural span | sigma grid 0.220472-0.227116, width 0.006644; structure grid 0.151491-0.307930, width 0.156439; structural width is 23.55x the sigma width |
| PASS | A2d-3  issuance on against issuance off | on 0.219094-0.222925, off 0.181641, gap 0.037453 against sigma's span 0.006644; separated by more than sigma's whole span |
| PASS | A2d-4  the entry point, at matched rule and matched sigma | largest \|diff\| 0.003831 (endogenous), 0.002652 at matched issuance volume (fixed, 2990.0 both arms), 0.000000 with no issuance; all below the on-off gap 0.037453 |

Readings:

- Sigma does not select the terminal distribution. Financial-layer retention over
  a fourfold range (0.20 to 0.80) crossed with production-layer retention from
  0.00 to 0.30 moves terminal top1% wealth share by 0.0066. This is A0-4 on a
  second carrier: the block model read a spending sweep as flat to `0.000e+00`,
  and the network reads the whole sigma vector as flat to 0.0066.
- What the terminal distribution is sensitive to is whether the authority issues
  at all. With issuance the close is top1% 0.2229, Gini 0.9367, effective support
  13.98; without it, 0.1816, 0.8829, 24.93.
- Where issuance enters is close to immaterial. At an identical issued volume of
  2990.0, putting every unit into the single most central financial node against
  spreading it over all 200 nodes moves terminal top1% wealth share by 0.0027.
  A0-9's numbers stand; its phrase `the layer it was issued to` does not carry
  the mechanism on this carrier.
- Control: with `rule="none"` the two entry points return bitwise identical
  closes (0.181641 and 0.181641, support 24.928 and 24.928), which is what the
  switch must do when there is nothing to place.

Structural knobs, printed rather than counted:

| knob | from | to | terminal top1% |
|---|---|---|---|
| `layer1_out_degree` | 3 | 10 | 0.3079 to 0.1625 |
| `layer1_size` | 10 | 40 | 0.2664 to 0.1600 (non-monotone: 0.1515 at 30) |
| `layer1_initial_share` | 0.50 | 0.90 | 0.2235 to 0.1837 (flat over the first four steps, the last one is a different regime) |
| `upward_out_degree` | 1 | 4 | 0.2218 to 0.2237 |
| `layer2_out_degree` | 2 | 6 | 0.2236 to 0.2223 |

Not measured here: the `layer1_initial_share=0.90` regime, which feeds no
criterion; and any 1925-29 target, which fails gate zero with one value in the
world.



Scope, M/R levels only (A13, 2026-08-23): the `mr_close` column is taken on a
graph fixed at construction. With endogenous rewiring on, M/R moves between −47%
and +14%; the starvation, topology and Gini readings are unaffected.

### Read again with A3's asset layer on the carrier (2026-08-24)

`--asset` puts A3's asset layer on the same carrier and writes
`a2d_terminal_selector_asset.json`. The default is off and reproduces the record above key for
key. **Every concentration number this stage reports is read without asset
revaluation**, and the empirical decomposition puts the weight on that channel:
Montecino and Epstein give an employment channel of about −0.5 points on the
90/10 ratio against an equity channel of about +6.3 on the 95/10 ratio.

**The ordering survives and the margin does not.** Sigma's span on terminal top
one percent wealth goes from **0.006644 to 0.031873**, nearly five times wider,
while the structural span barely moves, **0.156439 to 0.153907**. The ratio that
is this stage's headline goes from **23.5 to 4.83**. The mechanism is plain:
sigma is a retention rate and retained claims can sit in an appreciating asset,
so retention buys more when there is something to retain into. **Quote the
ordering, not the multiple, unless the carrier is named with it.**

**A four-corner probe is not enough to get this number.** Run first on the four
corners the plain carrier's extremes sit at, the sigma span read 0.015829 and the
ratio 9.7, both off by about a factor of two. **The extremes move when the
carrier moves**, so corners chosen on one carrier are not corners on another.

## A13 — whether position can be bought and sold, and whether the terminal distribution notices

`rounds=300` `seeds=5` `17 arms`

**9/9 live criteria passed. Closed.** Most arms here buy edges only: promotion
does not hand over the financial layer's spending propensity or its payroll
role, so those arms read what buying access does rather than what becoming a
layer's other two properties does. A financial-layer node differs from a
production-layer node in three ways, not one: the edges it holds, the spending
propensity it draws from, and whether it pays wages. Handing over all three at
once attributes nothing, so it is a ladder with one rung per property, added
2026-08-24, and A13-8 reads the steps.

Every stage before this one ran on a graph fixed at construction, which is the
framework's thesis written into the construction. This stage opens that channel.
The two rates are read off published work rather than chosen: the cluster fires
at 0.5 because Chetty et al. (2022) find perfect exposure by status still leaves
nearly half the connection gap standing, and retention is 1/3 because Eckbo,
Thorburn and Wang (2015) find one third of the CEOs of bankrupt firms keep
full-time executive employment with no median pay change while two thirds leave.

| | criterion | detail |
|---|---|---|
| PASS | A13-1  every arm ran and returned a finite share | 17/17 arms, 85 runs. The stock-flow identity is asserted inside the loop, so reaching here is also the claim that it held in every round of every run |
| PASS | A13-2  the off arm moves nothing | 0 promoted, 0 demoted over 5 runs; with the switch off the rewire path is unreachable, so every record taken before this stage is this arm |
| PASS | A13-3  mobility's span on terminal top1% wealth, against sigma's and the structure's | mobility 0.220184-0.223509, width **0.003325**; from A2d's record on the same quantity, sigma width 0.006644 and structure width 0.156439. The criterion prints the three and draws no line |
| PASS | A13-4  the terminal core size, rank alone against rank with a share | rank alone reaches **200.0 of 200** in all four such arms; with a share, 33.0 and 27.8, from an opening core of 20. A rank always has somebody in it, so rank alone admits somebody every round for ever; the share is what bounds the object |
| PASS | A13-5  every arm that can fire, fired | counts per arm reported; the two that cannot fire by construction are named rather than filtered |
| PASS | A13-5a  retaining every candidate is bitwise the construction | four readings per seed over 5 seeds, identical |
| PASS | A13-6  what mobility does move: M/R | off 33.132214, and across the mobility arms 17.436912-37.660813, per-arm values printed |
| PASS | A13-7  demotions counted, outbound-only against inbound-cut | both 218, against 63 once the demoted node's inbound edges are cut too; demote .005 reads 2 either way; every arm's count printed |
| PASS | A13-8  what a promoted node acquires, one mechanism per rung | `both` 0.221707 → `+ propensity` 0.220951 (**−0.000756**) → `+ payroll` 0.221488 (**+0.000537**); whole ladder −0.000219 against the off arm at 0.222923. Prints the steps, draws no line |

Readings:

- **Mobility does not select the terminal distribution.** Letting position be
  bought and sold, in both directions, at every cluster and retention rate
  tried, moves terminal top1% wealth share by 0.0033. That is half what the
  savings rate moves it and a forty-seventh of what the structural knobs move
  it.
- The sharpest arm is rank-only acquisition with no cluster: 180 nodes buy in,
  the terminal core is all 200 nodes so the core-periphery split has ceased to
  exist, and terminal top1% wealth reads 0.2229 against the control's 0.2229.
- **A rank alone is unbounded.** There is always a highest-holding node outside
  the core, so one joins every round for ever. The share condition is what
  bounds the object, and the two conditions together are required rather than
  redundant.
- **What moves is M/R.** Both directions open takes it from 33.13 to 23.36, and
  to 17.44 when acquisition adds edges instead of redirecting them. The
  endogenous issuance rule targets active claims per active resource, and
  rewiring circulates claims more widely, so less issuance is called for.
  Concentration and the money stock separate under this mechanism.
- Rewiring every tenth round reads the same as rewiring every round (top1%
  0.2211 against 0.2217, M/R 23.20 against 23.36). The frequency is not
  load-bearing.
- **Demotion that only cuts outbound edges is not demotion.** With both
  directions open the stage counts 218 demotions; cutting the demoted node's
  inbound edges as well takes that to 63. What the core keeps sending a demoted
  node carries its share back over the promotion condition, so it re-enters and
  is demoted again. The two `inbound cut` arms are what separate the two
  readings, and terminal top1% barely notices either: 0.2230 with the cut
  against 0.2217 without.
- **A promoted node could acquire three things, and taken one at a time they
  cancel.**
  The arms above buy edges only. The ladder added 2026-08-24 hands over the
  spending propensity and then the payroll role, one rung at a time, so each
  step's difference belongs to the thing that step added. The two steps go
  **opposite ways** and are the same order of magnitude: taking on the core's
  propensity moves terminal top1% by **−0.000756**, taking on the payroll role
  by **+0.000537**, and the whole ladder lands at −0.000219 against an off arm
  at 0.222923. **The ladder's whole range sits inside the span edge-buying
  already covers**, so A13-3's width is unchanged at 0.003325 with the two arms
  in the grid.
- What the two rungs do move is churn and `M/R`. Demotions go 218 → **271** with
  the propensity and back to **188** with the payroll role; `M/R` goes 23.36 →
  **19.91** → **22.20** against the off arm's 33.13. A node that takes on the
  core's low propensity spends less, falls back under the demotion share sooner,
  and crosses more often; giving it the payroll role puts a claim outflow back
  on it and undoes about half of that. **Neither shows up in the terminal
  distribution**, which is the same separation A13-6 reads on the arms above.

Why the qualification is a rank and a share rather than a level, measured before
the arms were written: the richest production node peaks in round zero at 1.0477
and falls monotonically to 0.4518 while the claim stock grows from 100 to 3412.
A level in claim units is crossed in 300 of 300 rounds at 0.25, in 7 at 0.50, in
1 at 1.00 and in none at 2.00. There is no usable band, and the same level
loosens for the core and tightens for the periphery as the stock grows.

Consequence for the readings taken before this stage: the fixed graph is not
load-bearing for concentration, so top1%, Gini, effective support and the four
surfaces stand unchanged. Quoted M/R **levels** carry a scope line instead. M/R
**directions** are unaffected: the minimum across every mobility arm is 17.44
against an opening ratio of one, so any reading of the form "M/R rises" holds
with a seventeen-fold margin.


### Read again with A3's asset layer on the carrier (2026-08-24)

`--asset` puts A3's asset layer on the same carrier and writes
`a13_mobility_asset.json`. The default is off and reproduces the record above key for
key. **Every concentration number this stage reports is read without asset
revaluation**, and the empirical decomposition puts the weight on that channel:
Montecino and Epstein give an employment channel of about −0.5 points on the
90/10 ratio against an equity channel of about +6.3 on the 95/10 ratio.

Mobility's span on terminal top one percent wealth goes from **0.003325 to
0.010028**, and it stays the smallest of the three: structure 0.154, sigma 0.032,
mobility 0.010 on that carrier. **The ordering survives; the margin against sigma
narrows from a factor of two to a factor of three in mobility's favour, and
against structure it stays an order of magnitude.**

**A13-8's two rungs both reverse sign on this carrier**, and by about eight
times the magnitude:

| step | registered carrier | asset carrier |
|---|---|---|
| `both` → `+ propensity` | **−0.000756** | **+0.006026** |
| `+ propensity` → `+ payroll` | **+0.000537** | **−0.005068** |
| whole ladder | −0.000219 | +0.000958 |

On the registered carrier a node that takes the core's low propensity spends
less and its terminal share falls; with revaluation on the carrier the claims it
does not spend are the ones that get revalued, so the same move raises its share
instead. The payroll rung undoes it in both cases and it too changes sign.
**Which mechanism helps and which hurts is decided by whether the carrier
revalues**, so neither step's sign is a property of the mechanism alone. Nine of
nine criteria pass on both carriers, and the registered reading is the one
without the asset layer.

## A14 — which readings are scale free, and which are artefacts of two hundred nodes

`rounds=300` `seeds=5` `27 cells`

**7/7 live criteria passed. Closed.** A8's and A12's four surfaces are outside
this stage because `f2i` is an absolute edge count whose maximum of 30 is 7.5%
of the possible financial-to-intermediate edges at 200 nodes and 0.3% at 1000,
so the same grid would test a different regime. The rescaling that settles that
was ruled on 2026-08-24 and `scaled_carrier` solves `f2i` for the registered
share rather than the registered count, but this stage is not re-run on it: what
this stage measures is which quantities move with `n`, and rescaling is what
removes exactly that. The four surfaces are read in A8's and A12's own records.

Two knobs carry no derivation anywhere in this repository: `n = 200`, and the
core as a share of nodes at 0.10. A2d's structure grid held both fixed.

| | criterion | detail |
|---|---|---|
| PASS | A14-1  every cell ran, and the construction's own cell reproduces | 27/27 cells; at n=200, fraction 0.10 the two degree arms coincide by definition and both read 0.222923 |
| PASS | A14-2  the structural span with both knobs in the grid | **0.096596-0.479285, width 0.382689**, against A2d's 0.151491-0.307930, width 0.156439 |
| PASS | A14-3  the two degree arms, same quantity, direction compared | five of six quantities **reverse**; only `support_close` agrees in direction, and by a factor of 1.7 in magnitude |
| PASS | A14-4  the core fraction axis at n=1000, density held | 0.05: top1% 0.3704, Gini 0.9641; 0.10: 0.1874, 0.9275; 0.20: 0.0966, 0.8543 |
| PASS | A14-5  what the top percentiles are, in nodes, at each size | n=200: top1% is 2 nodes, top0.1% is 1 by the floor rather than the construction; n=1000: 10 and 1 |
| PASS | A14-6  A4's null stays under its registered ceiling at every size | n=200 / 500 / 1000: null 0.007112, 0.007128, 0.007071 against a ceiling of 0.02; gap 0.9296, 0.9383, 0.9462 |
| PASS | A14-7  Gini per doubling of population, against the published figure | fixed-degree arm **+0.75% per doubling**; density-preserving arm −0.43%; published intra-urban reference about +8% |

Readings:

- **A2d's structural span is a lower bound.** With node count and core share in
  the grid it is 0.3827, two and a half times the 0.1564 A2d reports.
- **A sweep of node count alone is a sweep of density.** The degree parameters
  are absolute edge counts, so raising `n` thins the financial layer from 32%
  internal density at 20 nodes to 6% at 100 and gives preferential attachment
  room to build hubs it did not have. Terminal top1% wealth rises 0.2229 to
  0.3419 with degrees fixed and **falls** to 0.1874 with density held. Five of
  six headline quantities reverse the same way.
- **The fixed-degree arm is the one with a source.** Personal network size does
  not scale with the size of the surrounding population, so a node's count of
  trading partners should not rise with `n`. Its consequence, that within-group
  inequality rises with population, is itself an observed regularity: income in
  the poorest decile of US urban areas scales with city population at 0.97 while
  the richest decile scales at 1.15-1.16, and intra-urban Gini scales
  super-linearly with population across 11,000 global urban centres.
- The model reproduces that direction and misses the magnitude by an order:
  **+0.75% per doubling against a published reference near +8%**. The gap is
  bounded by the model's closing Gini already sitting at 0.937, which is a
  reading about this construction's top tail rather than about population.
- **The core share is a steeper axis than the node count.** Moving it from 0.10
  to 0.05 doubles terminal top1% wealth, 0.1874 to 0.3704, and 0.10 carries no
  derivation while 0.05 has two published sources.
- A4's null holds at 0.0071 at every size and the gap widens with `n`.

Sources for the two published references are in the stage's design note; both
are literature rather than measurement, they place the grid and carry no verdict,
and all three are urban and about income or activity rather than claim holdings.


### Read again with A3's asset layer on the carrier (2026-08-24)

`--asset` puts A3's asset layer on the same carrier and writes
`a14_scale_asset.json`. The default is off and reproduces the record above key for
key. **Every concentration number this stage reports is read without asset
revaluation**, and the empirical decomposition puts the weight on that channel:
Montecino and Epstein give an employment channel of about −0.5 points on the
90/10 ratio against an equity channel of about +6.3 on the 95/10 ratio.

**A14-6 fails on this carrier and the failure is the finding.** That criterion
asks whether A4's null stays under its registered ceiling of 0.02. With the asset
layer it reads **0.030177 at n=200 and 0.065545 at n=500**, over the ceiling; at
n=1000 it is back to 0.007071. On a complete graph with identical agents there
are no positions, so nothing here is topology: **the asset market's opening
allocation generates the dispersion by itself.** A hundred units walked out in
descending order of claims with no per-agent cap turns a negligible opening
difference into three units against none. Capping at one unit returns the null
to 0.0194, under the ceiling. The A8 section carries the full reading.
**Read this against its carrier.** A4's ceiling was registered on a construction
with no asset layer, and that registered reading is unchanged. What the failure
locates is a second generator of dispersion inside the asset layer, which is a
finding about the asset layer rather than a result about A14.

## A4 — the causal primitive: connectivity does not scale the other mechanisms, it selects which of them operate

`rounds=300` `5 seeds`

**3/4 live criteria passed, 2 void**

| | criterion | detail |
|---|---|---|
| PASS | A4-1 null calibration: identical agents on a complete graph do not stratify | C=0 all competitors off, Gini 0.00711 against a ceiling of 0.02. Production layer 0.00714. Spread across seeds 0.00026. |
| PASS | A4-2 connectivity alone is sufficient | Gini 0.93673 against 0.00711, gap +0.92962 against a floor of 0.05, and the sign holds at 5 of 5 seeds. Production layer 0.59490 against 0.00714. |
| **FAIL** | A4-3 no competitor is a strawman | Each competitor alone with C off, Gini rise over the null against a floor of 0.02: I +0.00007, E +0.00932, K +0.00080, M -0.00006. Below the floor: I, E, K, M. The floor is in absolute Gini units and the C=0 control sits at 0.00711, so it asks each competitor for 2.8 times the control's whole value; the threshold is registered and is not moved on that account. Education's rise is 35.6 control-cell sd and still below it. |
| VOID | A4-4 connectivity is upstream | **Void on two independent grounds and not evaluated.** §7's table: A4-3 fails for 4 of four competitors, and a failed strawman floor makes that competitor's comparison void rather than favourable. §11.8's rule: A(X) is a ratio across the two arms and no competitor is readable in both, so one of its two terms is a reading of the graph draw in every case. Readable Gini cells: C=0/K/I, C=0/null/E, C=0/null/K, C=1/E/I, C=1/E/M, C=1/K/I, C=1/K/M, C=1/null/I, C=1/null/M. Ratios whose per-seed sign happens to agree: I\|K = 440.7 (denominator -0.00042), and each rests on a denominator inside two control-cell sd, so the agreement is five draws landing the same way rather than a quantity. |
| FAIL | A4-5 the update order does not decide A4-4c's disjointness | **Reshaped 2026-08-24**; the registered form was void because A4-4 had no result for an ordering to preserve, and A4-4c has one. Judged on 4 of 4 orderings. **Intersection non-empty at capital_first/match_first and pooling_first/match_first**, both of which apply matching first, and in both it is mating that enters the C=0 set. **It enters at 1.01 against a floor of 1.00.** Registered ordering C=1 {I, M} smallest score 32.10, C=0 {E, K} smallest 4.35, intersection empty; pooling_first/inherit_first identical to it. Readable set has 35 cells; orderings whose set differs: capital_first/match_first 12, pooling_first/inherit_first 2, pooling_first/match_first 6. A4-1, A4-2 and A4-6 flip on none. |
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

Added 2026-08-24. Three criteria beside the originals, which are unchanged:

| | criterion | detail |
|---|---|---|
| PASS | A4-3b  the same question in control-cell spread rather than absolute Gini units | rise over the null in control-cell sd: I 0.3, E **35.6**, K **3.1**, M −0.2; clearing two sd: E, K |
| PASS | A4-4b  the amplification on a measure with no ceiling | `holders` (1/HHI) was in SCORED_MEASURES from the start and A4-4 took its ratio on Gini alone; on the unbounded measure the readable set is the same one and the single quotable ratio is the same cell |
| PASS | A4-4c  the two arms' readable competitors, as sets | **C=1 {I, M}, C=0 {E, K}, intersection empty**; passes because both arms are live, which is the only way the disjointness could be an artefact |

Reading:

- The four competitors split into two disjoint pairs and each pair is readable in
  exactly one arm. With connectivity on, inheritance and assortative mating clear
  the resolution floor by 36 and 32 control-cell sd while education and capital
  read **0.00 and 0.02**. With connectivity off the four exchange places: 35.6 and
  3.1 against 0.3 and −0.2.
- The stock-moved diagnostic agrees and takes no ratio: inheritance relocates
  **44.15%** of the closing stock under C=1 and **0.39%** under C=0.
- So `A(X)` has no domain, and the reason is not the instrument. A ratio across
  arms needs a competitor with an effect in both. The Gini ceiling and the noisy
  denominators are both real and A4-4b shows neither was binding.
- Section 1 offered two readings, the others near full strength with C off, or
  the others attenuated. **An exchange is neither.** Connectivity does not scale
  the other mechanisms; it selects which of them can operate. Inheritance and
  mating transmit a position and a complete graph has none to transmit; education
  and capital returns are properties of an agent and survive the graph's removal.
- A4-3 stays FAIL and A4-4 stays VOID, as registered.
- **A4-5 is no longer void and it fails.** Its registered form had no object,
  because A4-4 has no result; A4-4c's pair of sets is an object an ordering can
  move, and two of the four orderings move it. **What the disjointness is
  fragile to is specifically matching-first**: apply matching before the other
  channels and mating becomes readable under `C = 0` as well, so `A(X)` acquires
  a domain of `{M}` on those two orderings. **The margin is 1.01 against a floor
  of 1.00**, which the criterion prints beside every set for this reason, so the
  reading is that the disjointness holds away from the floor on the registered
  ordering and is decided at the detection limit on the two matching-first ones.
  **What to quote**: `A(X)` has no domain on the registered ordering, with the
  ordering named, not `A(X)` has no domain full stop.

## A5 — the reachability threshold: the region closes through the denominator, and freezing the price does not stop it

`rounds=300` `12 seeds`

**4 of 5 live criteria passed, 3 void, 1 diagnostic.** Three of the eight
registered criteria were voided on 2026-08-24 and one was marked diagnostic. The
reasons are below and none of them is a number changing: two were registered as
the complements of criteria that hold, one asked for a share the construction
cannot reach, and one is satisfied by an ordering over three equal values.

**What this stage establishes.** Reachability is `terms x price / median
production-layer claims`, so it has a numerator and a denominator, and the stage
was registered expecting the numerator to close the region: the price is set
against a bidder pool made of the financial layer's claims, and those grow with
issuance. **Measured, the denominator closes it.** With the price frozen at
`eta = 0` the region still closes in 12 of 12 seeds, and the median production
agent's claims end below their opening value in 72 of 72 cells across six
reachabilities and twelve seeds, at a ratio of `x0.045`. The earlier headline on
this section named the price channel and has been corrected.

| | criterion | detail |
|---|---|---|
| **FAIL** | A5-1  participation falls with reachability | 22.2%, 27.2%, 29.2%, 11.1%, 0.6%, 0.0% across `rho` = 0.25 to 8. **It rises and then falls, and the turn is a regime boundary.** Entry is read at the opening allocation before any round runs, so this is not drift. Below the peak every unit sells and cheapening lets the head of the descending-claims walk take more each, 1.250 units per production buyer at `rho=0.25` against 1.004 at `rho=1`; above it units go unsold, 2.4 at `rho=1.25` rising to 83.6 at `rho=8`. Peak 30.0% near `rho=1.1`, which is where the median production agent can just pay. The registered form assumed price is the only rationing device |
| **VOID** | A5-2  the threshold sits where the definition puts it | **the registered floor of 50% is above what the construction can reach.** 100 units over 180 production-layer nodes bounds entry at 55.6%, and that bound needs every unit to reach a different production node with none to the financial layer, which heads the walk and takes 36 to 50 units at every reachability. The high half was decidable and is reported: 11.1% at `rho=2` against a registered ceiling of 5% |
| **VOID** | A5-3  the sign of the production layer's trend flips | share at `rho=0.25`: 0.279 to 0.001; at `rho=4`: 0.260 to 0.010. **A5-4 is this criterion's complement and it holds**: with no benign equilibrium there is no benign end state for the share to rise to, so the two cannot both pass. Both regimes fall, which is the finding |
| PASS | A5-4  the benign side is not an equilibrium | configured `rho=0.5` is never observed, since the opening allocation moves it to 0.319 before any round runs. Crossed in 12/12 seeds, median round 2 from `rho_opening` against a registered 100, 0.0% of subsequent rounds back below one against 5% |
| **diag** | A5-5  issuance sets the clock | medians by issuance gain: 2, 2, 2. **Every median is equal, so the ordering is satisfied by every ordering and the arms cannot be told apart.** The line is kept and the verdict is not |
| **VOID** | A5-6  freeze the price and the drift disappears | largest relative move in `rho` with the price frozen: 654.51% against a registered 1%. **A5-7 is this criterion's complement on the same frozen-price arm and it holds.** This number is that evidence with the sign of the claim reversed |
| PASS | A5-7  the denominator crosses the threshold on its own | price frozen at `eta=0`: crossed in 12/12 seeds, median round 2, 0.0% of subsequent rounds back below one. The asset does not move and the reachable region closes anyway |
| PASS | A5-8  the drain is not a property of one reachability | price frozen: median production-layer claims end below their opening value in 72/72 cells across six reachabilities and twelve seeds, ratio `x0.045` |
| PASS | A5-9  one unit per agent makes entry monotone | registered 2026-08-24 to test A5-1's reading by removing the thing it names. With `max_units=1`: 44.4%, 44.4%, 43.3%, 11.1%, 0.6%, 0.0%. **Monotone.** The cap is an existing field and a policy that exists |

Readings:

- **The reachable region closes through the denominator.** The registered design
  put the price channel in the load-bearing position and the frozen-price arm
  closes the region anyway, in every seed and at every reachability. **Four of
  the stage's failures are one fact read four ways rather than four failures.**
- **Entry has two rationing regimes and they meet where the median agent can
  just pay.** Below that point every unit sells, so cheapening does not admit
  more people; it lets the front of the queue take more each. Above it units go
  unsold and cheapening does admit more.
- **A cap of one unit per agent removes the rise, and the number it lands on is
  arithmetic.** A hundred units to a hundred distinct agents gives the twenty
  financial-layer nodes one each and the production layer eighty, and `80/180`
  is 44.4%, which is what it reads. The cap doubles entry at the cheap end,
  22.2% to 44.4%, **and changes nothing at `rho >= 2`, where price is what
  rations.** No supply was added; the gain is entirely units returned from
  multiple holders.
- **Even with the cap the registered 50% floor is out of reach**, by the 5.6
  points the financial layer holds. Reaching it needs the cap and the exclusion
  of that layer together, and the registered form asked for neither.
- **The cap changes who enters and not who stays.** Entry is the opening
  allocation; A5-4 and A5-7 read the other side and the region closes on it
  regardless.

Every number here is read off `results/a5_reachability.json` as it stands.

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
| **FAIL** | A7-A-2 | the registered shape is wrong. Not a gradient: a step at the first grid point, both +18.9854 to -0.1157, then flat to s = 0.9. Recorded under the project's engineering rule 8 and not repaired; docs section 6.2. **Scope, added 2026-08-24: it is a step in downward edges and not a step in connectivity.** See the scope reading below |
| VOID | A7-A-3 | void on the estimator it names. On D_fixed each arm's population is intersected across its own grid, so the two are 24.20 against 35.95 nodes and a difference of falls compares quantities on different agents; docs section 11.2 |
| **FAIL** | A7-A-4 | A3-8' holds nowhere including where it was derived. Loop-sum-only same-sign across seeds on D_fixed at s = 0: 17/20 and 19/20, against 20/20 on D_reach. A3-8's own state is untouched; docs section 11.3 |
| **FAIL** | A7-A-5 | the identity does not hold on the measured population. Mean \|loop sum\| over the fixed production layer rises before it falls, to 1.44 times its s = 0 value in the uniform arm and 4.13 in the preferential one; docs section 6 changelog |
| **FAIL** | A7-A-6 | the round-count ladder is not monotone in the uniform arm and gives 4.85 against a registered five in the preferential one. The retained fraction goes as 1/R because the s = 0 baseline scales with the round count; unnormalised the gap at s = 0.01 does not move at all across a fourfold change in rounds while the gap at s = 0 moves with it; docs sections 10.2 and 10.3 |
| VOID | A7-B-1 | unreadable. d(K, s) is sign-unstable at every grid point including s = 0, where the mean is -0.00039 against a range of [-0.0020, +0.0010] that straddles zero. A quantity with no sign has no magnitude to trend. This is A4-4's position on a different estimator; docs section 13.1 |
| VOID | A7-B-2 | not adjudicable as registered: the noise floor the clause conditions on was never given a numeric form. Against A7-B-1's standard E fails too, at 17/20 rather than 20/20; docs section 13.2 |
| PASS | A7-B-3 | the two-measure disagreement clause did not fire. On the aggregate log(1/HHI) both competitors are also sign-unstable and near zero, so the measures agree and what they agree on is that nothing is readable; docs section 13.3 |
| PASS | A7-B-4 | both probes ran before anything was scored and the section 5.3 trigger was decided on them alone. Room relative to s = 0, largest over the grid: aggregate log(1/HHI) 2.00 against a registered band of 1.5, production-layer-only 1.20. The substitution registered with the band fires and leg B proceeds on one axis; docs sections 12.2 and 12.3 |
| VOID | A7-B-5 | I and M recorded as not run. Above s = 0.02 in the uniform arm a one-off transfer leaves nothing after a generation, so a transmitting mechanism has no stock and their effects are identically zero by construction; docs sections 12.1 and 13.5 |

### The step is in the downward edges (2026-08-24)

The shortcut draw is uniform over ordered pairs, and on a 20/180 graph that is
not uniform over kinds of edge: 80.95 percent of ordered pairs are production to
production and 0.95 percent are financial to financial. At `s = 0.01` the
registered arm adds 350 edges, of which **282 land inside the production layer
and 21 point downward**. `NetworkSpec.downward_edges` is zero by default and its
own docstring calls zero the framework's specification, and A0-6 measured what
one downward edge does: production-layer inflow 17.7007 to 48.3919, a factor of
2.73. **Every arm with a positive rate therefore moves two things at once.**

`NetworkSpec.shortcut_scope` holds the count and moves only where the edges land,
the same discipline `shortcut_mode` already applies to targets. Five arms, all
matched to what the registered arm draws, `H1_only` range:

| arm | edges at `s=0.01` | `H1_only` | width | lower bound positive |
|---|---|---|---|---|
| `s = 0`, shared | 0 | `[7.107, 37.422]` | 30.31 | yes |
| **registered, anywhere** | 350, of which **21 downward** | `[-2.364, 1.711]` | 4.07 | **no** |
| **downward only** | **350 downward** | **`[-0.966, 1.776]`** | **2.74** | **no** |
| production only | 350 | `[-30.301, 63.063]` | **93.36** | no, but see below |
| upward only | 350 | `[14.138, 36.915]` | 22.78 | **yes** |
| financial only | **260, saturated** | `[5.478, 33.288]` | 27.81 | **yes** |

- **Only the downward arm reproduces the collapse, and it reproduces it almost
  exactly.** The same edge count placed inside the production layer or pointing
  upward leaves the gap where it was.
- **A collapse is not a widening.** The production arm takes the range from 30.31
  to 93.36 and its lower bound to -30.3. That is the gap becoming unreadable
  rather than the gap going to zero, and a criterion that only asks whether the
  lower bound is still positive reads the two as the same event.
- **Twenty one edges are enough.** The registered arm has 21 downward edges at
  `s = 0.01` and collapses as far as 350 do. The channel saturates almost at
  once, which is what A0-6's factor of 2.73 per edge implies.
- The financial arm exhausts its 380 ordered pairs at 260 edges and reads the
  same at every rate, so it is printed and not judged. It also says that 260
  edges inside the financial layer do close to nothing to the gap.

**What this changes.** The shape reading stands: a step at the first grid point,
flat afterwards. What the step is a step in does not. **Do not write that the gap
disappears as connectivity rises without saying how many of that point's edges
point downward.** No number in `results/a7_continuous_c.json` moves; what moves
is what those numbers carry.

## A8 — the coverage test: four surfaces on one curve, and the edge width that takes them off it

`rounds=600` `seed=0` `5 graph seeds`

Pre-registered, with the criteria fixed before the run and none changed after it.
The grid is not this stage's: the edge counts, the elasticities, the intermediate
size and the tail window are imported at runtime from stage A2's module, and
criterion A8-1 checks that the import is what actually supplied them. Volume One
section 13 asks whether four symptoms reduce to one topological fact; this stage
reports the curve over A2's grid and asks whether any single setting puts all four
on the table, which is the form section 13 of the restated A3 document requires.
Selecting a setting because it lands where one wants it is what that document
forbids, and nothing here is selected.

Each surface is read as a direction, so there is no threshold anywhere in the
adjudication: a ratio above one, a ratio below one, a count equal to one. The
magnitudes sit beside the flags in `results/a8_coverage.json`, which holds all 90
runs.

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A8-1  the grid comes from A2, not from this stage | imported from A2's module at runtime: edges [0,1,2,3,5,8,12,20,30], elasticities [0.0,0.5,0.9,0.99,1.0], intermediate 30, tail 25 |
| PASS | A8-2  the real side is a level, not state | across 90 runs, the count of distinct resource values within a run is 1 every time |
| PASS | A8-3  claims are conserved across the grid | 90/90 runs hold the identity between the holdings row sum and opening-plus-issuance at machine precision, below `1e-9`. The bound rather than the residue, because the residue is decided by accumulation order. Checked across the whole run rather than inside the loop: the loop's own assertion spans the transfer stage, while issuance lands before it and the asset settlement of stage A3 runs after it |
| PASS | A8-4  one setting puts all four surfaces on the table | all four present at edges [1,2,3,5,8,12,20]; absent at [0,30]; no surface is absent everywhere on the grid |

The two ends of the curve lose different surfaces. At zero autonomous edges the
consuming-power surface is the one that goes: `M_a/R_a` reads 0.000, which is
circulation having stopped rather than the ratio a price index reads holding
steady. At thirty edges the support surface is the one that goes: effective
support ends at 1.016 of its opening value, so nothing contracted.

Across the whole 45-cell grid `M_a/R_a` stays between 1.008 and 1.028 of its
opening value while `M/R` runs from 1.02 to 132. Claims per unit of resource rise
by two orders of magnitude and the ratio a price index reads moves by under three
percent. `network.layer2_inflow` and `economy.active_claims` carry the same
definition, claims landing in Layer 2, so this is the same quantity A0 reports.

Two objects are printed without being criteria, and neither can pass or fail. The
first is the paired reading of payroll: at zero edges and unit elasticity the
funding ratio reads 0.7559 while the bill it is measured against has gone to zero,
so the pair is what makes that cell read as an absent surface rather than a healthy
one, and the pairing was written down before the run. The second is the response
of each surface across elasticity: holding the edge count at one and moving
elasticity from zero to unity moves the funding ratio by 10.6% while `M/R` moves
4.9%, the closing Gini 0.0%, and effective support 0.5%. The surfaces respond to
the two axes differently, which is the evidence that they are not one collapse
seen four ways.

Ordering was measured and is not decidable on this carrier, which is a reading
rather than an omission. Volume One section 12 states a causal chain, so the round
each surface first holds is printed for all 45 cells in
`results/a8_coverage.json`. The order does flip between eight and twelve edges,
support contracting first below that and the claim ratios opening first above it,
but the gap is one round out of six hundred, all five elasticities give the same
flip point, and the payroll surface opens at round zero by construction because the
intermediate block is itself the payer. An order that responds only to the opening
graph and not at all to any behavioural parameter is reading the initialisation, so
no criterion is written on it at this resolution.

Scope: this is a statement about this carrier. The stage buys no data. The four
surfaces are the four symptoms Volume One section 13 lists. The default cascade of
section 18 is not among them and is not read here; it runs on a separate machine
that takes published shares rather than the spending propensity this curve is
drawn over.

**The carrier has no asset revaluation on it, and that is the channel the
empirical work weights most heavily.** Montecino and Epstein decompose QE into an
employment channel worth about −0.5 points on the 90/10 ratio and an equity
channel worth about +6.3 points on the 95/10 ratio, the second dwarfing the
first. Every concentration reading taken on this carrier and on the stages
downstream of it therefore carries one channel and not the other. `--asset` puts
A3's asset layer on the same carrier and writes `a8_coverage_asset.json`; the
default is off and reproduces this record key for key.

**Read together, the two carriers answer one half of the registered question
each.** On the registered carrier the four surfaces are present at edges 1
through 20 and absent at 0 and 30, so widening the edge takes them off the table,
which is the half section 13 states as the contrast. On the asset carrier they
are present at every edge on the grid, so that carrier answers whether a setting
exists and not whether widening removes it; A8-4 prints `NO CONTRAST` when its
miss list is empty, for exactly this reason. Neither carrier replaces the other.

**The asset layer has two parts and only one of them is a multiplier.**

**Revaluation is a multiplier on position.** Measured on the subsistence arm:
removing the terms gradient across centrality moves the closing Gini from +0.0772
to +0.0713, freezing the price while keeping ownership moves it to −0.1856, and
putting the same asset layer on a complete graph gives a change of −0.0607 with
claims growing 1.01-fold. **With no positions to multiply, that part returns
nothing.** This is A4-4c's finding on a second object: connectivity does not
scale the other mechanisms, it decides which of them can operate.

**The opening allocation is a generator and it does not need positions.**
Corrected 2026-08-24 after A14-6 read the level rather than the change. On a
complete graph with identical agents the closing Gini is **0.0075 with no asset
layer and 0.0307 with one**, against the ceiling of 0.02 A4-1 registers for that
null. The change over the run is negative because the dispersion arrives at the
opening auction and then erodes; the level it erodes to is still four times the
null. **A hundred units are walked out in descending order of claims with no cap
on units per agent, so an opening difference too small to matter becomes three
units against none, and units are worth something.**

**The cap is what decides it.** Same complete graph, same asset layer, one unit
per agent: **0.0194, back under the ceiling.** Three units per agent: 0.0332,
over it again. **This is A5-9's finding on a different object** — there, capping
at one unit doubles entry at the cheap end because the head of the queue stops
taking multiples; here it keeps a null under its registered ceiling for the same
reason.

## A9 — the New Deal switch: one structure, two parameter settings, and the rate at which both readings turn

`rounds=600` `5 graph seeds`

Pre-registered, with the criteria fixed before the run. Volume One section 15
states that 1945 to 1973 is the only period in which productivity and wages grew
together and the only one in which inequality fell, and that the actions were
dismantled one by one after 1980. This stage makes the second half of the
extensibility standard executable: one structure, run twice with nothing changed
but the fiscal parameters, and whether both readings turn together.

Criterion A9-1 is what makes "change the parameters, not the structure" machine
checkable rather than asserted: every arm is the control object with its fiscal
field replaced, and the criterion reports the set of fields that differ.

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A9-1  one structure, the fiscal parameters only | fields differing from the control across all six arms: ['fiscal'] |
| PASS | A9-2  the real side is a level and claims are conserved | 30 runs, one distinct resource value within each; 30/30 conserve claims at machine precision below 1e-9 |
| PASS | A9-3  one rate turns both readings at once | both hold at rates [0.20, 0.35]; exactly one holds at [0.005, 0.02, 0.06]. Wage share retained by rate: 0.034, 0.113, 0.371, 0.768, 0.995, 0.990 |
| PASS | A9-4  switching it off reverses both | 5/5 control runs have inequality rising and the wage share falling: median gini 0.8166 to 0.9369, median wage share 0.0730 to 0.0025 |

The levy grid is anchored on stage A6's own registered values rather than chosen
here: 0.005 is A6's first non-zero rate and 0.060 is the R* it measured on the
stratified graph, the smallest rate at which the support set stops contracting.
The other three rates are spacing and carry no verdict.

A6's R* sits at 0.060 and both readings here need 0.20. **The rate that stops the
support set from contracting is not enough to hold the wage share and lower
concentration at the same time.** That is this stage's increment over A6, which
measured the support set alone.

The coupling reading is scored against the control arm rather than against each
run's own opening, and the reason is in the manuscript's wording. "Grew together"
means the share is unchanged, and an unchanged share tested against itself is an
equality rather than a direction. The control arm supplies the direction: it keeps
3.4% of its opening share while the arms that redistribute keep 99%. The reference
is the control's ceiling rather than its median, since a group compared to its own
centre has half its members above it by construction.

Two objects are printed without being criteria. The injection target is compared
between the top node and a uniform spread, because direct injection into Layer 2
is the first of the five actions section 15 lists. And the five actions are
inventoried against the knobs that exist: three have one, while unions have no
bargaining side in this model and Glass-Steagall would mean changing the graph,
which is changing the structure and would fail A9-1 by construction.

Scope: a statement about this carrier, with no data bought. The levy is a share of
financial-layer holdings taken each round, so it is not comparable with any
historical marginal tax rate. This is the second half of the extensibility
standard; the first half needs a subsistence level, and this model has a constant
resource pool and no absolute requirement anywhere in it.

## A10 — the write-off chain: one switch, and the aggregate stops showing what the distribution still shows

`rounds=300` `12 graph seeds` `204 runs`

Pre-registered, with the criteria fixed before the run. Volume One section 14
gives an accounting chain and then states what this stage reads: the mechanism is
the same and the power topology is different, so the outcome is opposite. Whether
the head grows back is not endogenous, so it enters as a switch rather than a
rule. Three of the mechanism's decisions come from that section and none is
invented here: claims are destroyed at write-off, the loss falls on every holder
by dilution because nobody can name what they paid, and the refill is conditional.

**4/4 live criteria passed, 1 void**

| | criterion | detail |
|---|---|---|
| PASS | A10-1  one structure, the write-off field only | fields differing from the control across all 17 arms: ['writeoff'] |
| PASS | A10-2  the identity holds with destruction in it | 204/204 runs satisfy holdings = opening + issuance - write-offs at machine precision below 1e-9 |
| PASS | A10-3  destruction shows on the aggregate only where it is not refilled | paired by seed and setting, the refilled arm is nearer its own control than the unrefilled one in 96/96 pairs. Median M/R 32.53 with refill and 7.30 without, against a control at 33.22 |
| PASS | A10-4a  the refilled arm concentrates further than the control | every seed at 8 of 8 settings; median gini 0.9397 with refill against 0.9348 in the control |
| VOID | A10-4b  the refilled arm reaches fewer nodes than the control | the reach gap changes sign between seeds, the best setting carrying 10 of 12. Not a seed-count problem: at five seeds it was 4 of 5 and the proportion is not converging |

Same code, same graph, same random stream, one boolean flipped: M/R lands at 2.03
without the refill and back at 32.29 with it, against a control at 33.22. The
diagnostic block carries the other half of that: **refilling multiplies cumulative
destruction by 7.85**, because write-off, refill and write-off again is itself a
loop. Every one of the sixteen firing arms did fire, so none of them passes a
criterion by never triggering.

The fourth criterion was registered as a conjunction, concentration up **and**
reach down, and printed per seed it splits: the concentration gap is one-signed
across every seed and every setting, between +0.0007 and +0.0082, while the reach
gap runs from -0.0160 to +0.0104. Reported apart, one holds everywhere and the
other is undecidable. So section 17's claim that financial activity conceals the
real economy's dysfunction has **half** its support here: refilling concentrates
further than doing nothing on every seed, and what it does to circulation's reach
has no fixed direction.

Scope: a statement about this carrier, with no data bought. The refill is
exogenous by construction and the stage cannot decide it, which is section 14's
own claim rather than a modelling omission. The real side of that section, that
the accounting entry vanishes while the resource transfer does not, is not tested:
R is a constant here and the write-off touches only the claim side.

Horizon (added 2026-08-23; the main table above is 300 rounds, three seeds at
600, 1200 and 2400):

| arm | M/R at 300 / 600 / 1200 / 2400 | closing support |
|---|---|---|
| control, no write-off | 33.54 → 66.44 → 132.24 → **263.84** | 13.67 |
| refilled, low rate | 33.52 → 66.46 → 132.32 → **264.05** | 13.73 |
| unrefilled, low rate | 5.48 → 5.49 → 5.49 → **5.49** | 15.48 |
| unrefilled, high rate | 9.37 → 9.52 → 9.50 → **9.12** | 14.70 |

- The refill returns the aggregate to the no-crisis path to **0.08%** at 2400
  rounds, and returns effective support to within 0.43% of it. A10-3 read this
  as "nearer its own control"; over four horizons the two are the same
  magnitude.
- What the refill costs shows in the top of the distribution instead: top1%
  wealth share runs **1.3 to 6.2 points above the control**, 0.2306 to 0.2927 at
  the high destruction rate, while cumulative destruction reaches 3,456,069
  against an opening claim stock of 100.
- The unrefilled arms settle at 4 to 6 percent of the control's aggregate and
  hold there across an eightfold change of horizon, with **more** effective
  support than the control, 8 to 13 percent, and a lower Gini.
- Event ordering is not readable on this carrier and the reason is a reading
  rather than an absence: both groups reach a steady state, so the argmin of a
  flat series is the horizon. Every refilled arm and **the control** return the
  same last-round position. The one stable interior event is the M/R peak of the
  unrefilled high-rate arm at round 86, identical at all four horizons.

Scope, M/R levels only (A13, 2026-08-23): the M/R figures quoted here are taken
on a graph fixed at construction. With endogenous rewiring on, M/R moves between
−47% and +14%; concentration readings and the direction of every M/R statement
are unaffected, the minimum across all mobility arms being 17.44 against an
opening ratio of one.


### Read again with A3's asset layer on the carrier (2026-08-24)

`--asset` puts A3's asset layer on the same carrier and writes
`a10_writeoff_asset.json`. The default is off and reproduces the record above key for
key. **Every concentration number this stage reports is read without asset
revaluation**, and the empirical decomposition puts the weight on that channel:
Montecino and Epstein give an employment channel of about −0.5 points on the
90/10 ratio against an equity channel of about +6.3 on the 95/10 ratio.

**A10-4a fails on this carrier.** It asks whether the refilled arm concentrates
further than the control, and on the registered carrier that holds at 8 of 8
settings. With the asset layer it holds at **4 of 8**, and every split is at rate
0.02, the mildest write-off on the grid: 8/12, 8/12, 11/12 and 11/12 seeds at
triggers 2, 5, 10 and 20. **The asset layer's own concentration is of the same
order as the write-off's at that rate**, so the two are separable only at the
higher rates. Median closing Gini is 0.9406 with refill against 0.9353 in the
control, close to the registered 0.9397 against 0.9348.
**Read this against its carrier.** A10-4a was registered on a construction with
no asset layer and holds there at 8 of 8; that reading is unchanged. The 4 of 8
is a statement about how far the write-off separates from asset revaluation at
the mildest rate on the grid, and it is not A10 failing.

## A11 — the subsistence floor: on a stratified graph position decides who starves, and erasing the topology removes the question

`rounds=300` `5 graph seeds` `90 runs`

Pre-registered. Volume One section 8 states that MPC is a property of an agent
while this framework talks about the edges of a graph, and that an agent with a
high marginal propensity and no in-edge starves anyway. That is falsifiable here,
because the repository already carries an arm that erases the topology and leaves
every behavioural parameter alone: `uniform_access` puts every node on a complete
graph. The floor itself is derived rather than transcribed, and the derivation
sits in the spec's own docstring: it is a level on the real side rather than a
ratio on the claim side, it is a floor on inflow rather than on holdings, leaving
is absorbing, and leaving destroys nothing because destruction is the write-off
of section 14 and has its own switch.

**4/4 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | A11-1  one structure, the subsistence field only | fields differing from the control across all arms: ['subsistence'] |
| PASS | A11-2  leaving destroys nothing | 90/90 runs hold the claim identity with the floor on, below 1e-9 |
| PASS | A11-3  on the stratified graph starvation lands on the production side | 40/40 firing runs; median starvation rates 0.050 in the financial layer against 0.986 in the production layer |
| PASS | A11-4  erasing the topology closes the gap | paired by seed, floor and grace, the gap is narrower on the complete graph in 10/10 pairs. Median gap +0.000 complete against +0.936 stratified |

On the stratified graph the production side dies out step by step while the
financial layer barely moves: raising the floor twentyfold takes the financial
layer from zero losses to four out of twenty, while the production layer goes from
42 of 180 to all 180. On the complete graph there is no middle state at all.
Below the resource pool per node nobody leaves, and at it all two hundred leave
together. The two graphs share every behavioural parameter and differ only in
their edges, so what the comparison isolates is the asymmetry of the edges: with
no asymmetry there is no question of who starves first, only whether everyone has
enough.

Three readings come with it. **The Gini falls as the floor rises**, 0.934 to
0.715, and it is not the economy becoming equal. **Where the claims go is the
whole of it, and the record names them**: at a floor of 0.5 the frozen set is 182
nodes holding **2,382 claims of the 6,031 outstanding, 39.5 per cent**, against
zero at a floor of zero. An economy that has moved most of its population out of
circulation reports a better Gini, which is this framework's own thesis about
aggregates appearing inside its own model.

**The accumulation is a property of this arm's exit rule, and the two rules now
separate it.** A frozen node here stops trading and goes on drawing wages,
because `cut_payroll` is false in the registered arm, and it never spends what
arrives. That is the same construction A12-6 isolated on A8's carrier, where the
frozen set ends holding 85.6 per cent of every claim outstanding, and A12
answers it with a second exit rule, `drawdown`, under which a node below the
floor stays in the graph and spends `min(need, holdings)` instead of leaving.
**Both rules have now been run across this grid** with two fields added to every
run, the closing frozen share and the closing Gini among nodes still trading.
The fields are additive: 180 places appear in each record and not one value the
records already carried moves. Paired by seed against each graph's own
zero-floor control:

| graph | floor | rule | ΔGini, all nodes | frozen share | starved |
|---|---|---|---|---|---|
| stratified | 0.5 | `exit` | **−0.2229 ± 0.0023**, 5/5 negative | 39.7% | 182.4 |
| stratified | 0.5 | `drawdown` | **+0.00024 ± 0.00001**, 5/5 positive | 0.21% | 172.0 |
| complete | 1.0 | `exit` | **+0.9822 ± 0.0003** | 100% | 200 |
| complete | 1.0 | `drawdown` | **−0.0027 ± 0.0002** | 0% | 0 |

**All of the fall is the freeze and none of it is the exit.** The same floor
starves a comparable population under both rules, 182 against 172 on the
stratified graph, so the two rules agree on who leaves. They differ on what
happens to the claims those nodes were holding when they left. Under `drawdown` those claims are spent
down, the frozen share closes at two tenths of one per cent, and the Gini does
not move: **+0.00024 against a control of 0.9367**, a thousandth of the
magnitude `exit` reports and pointing the other way. **What the exit itself does
to the distribution is raise the Gini very slightly**, which is the direction the
construction implies, since a node that spends its way to nothing and then stops
leaves the survivors marginally more concentrated than before.

**The sign of the `exit` number is a property of the graph rather than of the
mechanism.** The same switch at the same depth reads −0.22 on the stratified
graph and **+0.98 on the complete one**, where the whole population freezes and
the statistic has no trading object left at all. A statistic that moves most of
its range in either direction depending on the carrier is reporting when the
snapshot was taken. `docs/MEASUREMENT.md` failure mode 55 records the shape.

**All four criteria hold under `drawdown` as well**, which is measured rather
than argued, and it is why they were written the way they were: they read
starvation rates by layer and the complete-graph comparison, and none of them
passes through the frozen set's holdings. The layer asymmetry is the same object
under both rules, median production rate 1.000 against a financial rate of 0.150
under `exit` and 0.950 against 0.100 under `drawdown`. A11-4 passes for a
stronger reason on the second rule: on the complete graph `drawdown` puts nobody
below the floor at any depth on this grid, so erasing the topology removes the
question rather than narrowing a gap.

**The Gini among nodes still trading is recorded and is not judged.** It falls
steeply as the floor rises, 0.9367 to 0.303 under `exit` and to 0.555 under
`drawdown` at a floor of 0.5, and both are computed over a set that is
shrinking, 200 nodes down to 18 and 28. What that column measures is how alike
the survivors are, and the survivors are the top of the distribution by
construction. It is here because the frozen share is only half of the
decomposition, and it is left unjudged for the same reason the all-node column
could not be read on its own. **Production-side exit drives issuance up**, M/R from 34 to 60, because
the issuance rule watches the shortfall in Layer 2 inflow and exit is what opens
that shortfall. And the complete-graph control reads M/R 1.00 with a Gini of
0.0072: an economy with no stratification concentrates nothing and issues nothing,
because its active circulation never runs a shortfall.

Scope: a statement about this carrier, with no data bought. The floor's absolute
value is not comparable with anything outside the model; the resource pool per node
is a construction scale. Leaving being irreversible is a design choice taken from
the framework's own absorbing-wall mechanism rather than a measured property.

### Read again with A3's asset layer on the carrier (2026-08-24)

`--asset` puts A3's asset layer on the same carrier and writes
`a11_subsistence_asset.json`. The default is off and reproduces the record above key for
key. **Every concentration number this stage reports is read without asset
revaluation**, and the empirical decomposition puts the weight on that channel:
Montecino and Epstein give an employment channel of about −0.5 points on the
90/10 ratio against an equity channel of about +6.3 on the 95/10 ratio.

All four criteria hold on this carrier as they do on the registered one.

## A12 — the coverage result under the two later mechanisms

`rounds=300` `seed=0` `14 arms` `630 runs`

**7/7 criteria passed.** A8 read four surfaces off one parameter curve with the
write-off chain and the subsistence floor both switched off, because neither
existed then. Both act on quantities those surfaces are read from, so this is a
question rather than a re-run. **The answer is that the coverage result stands:
on every arm whose subsistence state describes a household, the edges carrying
all four surfaces are `[1, 2, 3, 5, 8, 12, 20]`, which is the control's set
edge for edge.**

**What this stage cost, and what that bought.** Its first form put a node that
fell below the floor out of the graph, and left its payroll edge open. Such a
node draws a wage every round and spends nothing. Measured: a hundred and sixty
five of them leave by round five, and the claims they hold then grow linearly by
four per round for the rest of the run, ending at **85.6 percent of every claim
outstanding**. The stage read that as monetary expansion favouring the middle of
the distribution, and the middle in question was those hundred and sixty five
accounts. **Receiving and not passing on is retention, which this framework
assigns to the top layer**, so the exit state applied a top-layer operation to
the bottom. `docs/MEASUREMENT.md` failure mode 29 records the shape: a behaviour
implemented through a membership rule inherits membership's properties, which
are binary, absorbing and total, while a behaviour is a rate.

The state that has a household in it is `mode="drawdown"`: the node stays in the
graph and spends `min(need, holdings)`, so it goes on consuming, consumes less,
and eats its savings. No absorbing wall, and none is needed, since a node with
nothing spends nothing and one whose edge returns is not below the floor any
more. **On that arm the frozen stock ends at 0.2 rather than 1202.4, claims grow
1.7-fold rather than 14.1-fold, and the closing Gini moves +0.0344 against the
no-mechanism control's +0.0328.**

**One floor depth, and that is a scope on two of the recorded fields.** This
grid holds the floor at `0.20` and does not vary it, so the `top1_wealth` and
`top10_wealth` recorded here are readings at that depth. It is not a neutral
one. At `0.20` the nodes that leave freeze holding **94 per cent** of the
closing stock, so every concentration measure moves with that accumulation and
they cannot separate; at `0.05` the leavers hold **0.3 per cent** and the same
three measures do separate, with the top percentile falling while the top decile
and the Gini rise. **A16's floor scan is the reading where depth is the axis**,
and the two fields are recorded here without a criterion resting on them, which
was already the right handling.

| | criterion | detail |
|---|---|---|
| PASS | A12-1  one structure, the two mechanism fields only | fields differing from the control across 14 arms: `subsistence`, `writeoff` |
| PASS | A12-2  the identity holds with destruction in it | 630/630 runs, below 1e-09 |
| PASS | A12-3  the both-off arm reproduces A8 | this stage `[1, 2, 3, 5, 8, 12, 20]` against `a8_coverage.json` `[1, 2, 3, 5, 8, 12, 20]` |
| PASS | A12-4  the coverage result survives each mechanism | judged on the arms whose subsistence state has somebody in it: drawdown `[1,2,3,5,8,12,20]`, write-off `[1,2,3,5,8,12,20]`, drawdown with write-off `[1,2,3,5,8,12,20]`, against the control's `[1,2,3,5,8,12,20]`. The exit arms are printed and not judged on, for the reason above: floor `[]`, both `[1]`, floor payroll kept `[]` |
| PASS | A12-5  the transfer channel, and who is left in circulation | reshaped: its first form asked whether the transfer arm carries all four surfaces, and surface three needs the closing Gini above the opening one while a per-head transfer lowers it by construction, 90 of 90 paired cells, range −0.20 to −0.86. Judged instead on who is still in circulation, cell by cell. Branch C: excluded nodes 11 down / 12 level / 22 up, support ratio 17 / 0 / 28, the two quantities pointing opposite ways and reported separately |
| PASS | A12-6  which of the exit floor's two booleans carries the construction artefact | the payroll one. Closing Gini: floor 0.5903, payroll severed 0.9121, payroll kept 0.5908, drawdown 0.9179, against the control's 0.9172. Wage funding 0.5000 / 0.0000 / 0.5000 / 0.7382 against 0.7381 |
| PASS | A12-7  every write-off-bearing arm fired in at least one cell | write-off 10/45, both 45/45, both with transfers 45/45, write-off refill 10/45, severed without refill 15/45, kept with refill 44/45 |


Grid position, so the two edge grids can be compared. The registered grid is
`(0, 1, 2, 3, 5, 8, 12, 20, 30)`; at a thousand nodes each count is solved to
reproduce its autonomous share and reads `(0, 2, 5, 8, 15, 28, 45, 72, 128)`.

| arm | 200 | 200 + asset layer | 1000 |
|---|---|---|---|
| control, no mechanism | 1–7 | 0–8 | 1–7 |
| **drawdown floor** | **1–7** | **0–8** | **1–7** |
| **drawdown floor with write-off** | **1–7** | **0–8** | **1–7** |
| write-off alone | 1–7 | 0–8 | 1–7 |
| exit floor, payroll left on | **empty** | 0–8 | **1** |
| exit floor, payroll severed | 1–8 | 1–8 | 1–8 |

Closing Gini, drawdown against the control: 0.9179 / 0.9172 at two hundred,
0.9153 / 0.9177 with the asset layer, 0.9377 / 0.9369 at a thousand.

Readings:

- **The coverage result survives both later mechanisms.** Three arms carrying a
  subsistence state that describes a household return the control's edge set
  exactly, and the write-off fires in ten of forty five cells on the arms that
  carry it, so the mechanism ran rather than passing by never running.
- **A subsistence floor, modelled so that the household below it still eats,
  does not change where concentration goes.** It changes who is consuming. Every
  distributional reading this stage produced under the exit state was that
  state's accumulation, not the floor's.
- **Transfers repair the flow and not the membership.** Wage funding rises in 37
  to 38 of 45 paired cells, by up to a full point, while the count of nodes out
  of circulation rises in 22 of 45 at two hundred nodes and in 42 of 45 at a
  thousand. A per-head transfer breaks a concentrated inflow into an even
  trickle, and the floor is a threshold on inflow.
- **The drawdown result holds on all three carriers, in grid position.** Two
  hundred nodes, two hundred with A3's asset layer, and a thousand with the edge
  grid solved for equal autonomous share: on every one the drawdown arm returns
  the control's positions exactly, `1` to `7` on the two plain carriers and `0`
  to `8` on the asset one, and the closing Gini differs from the control by at
  most 0.003. The exit arm is empty at two hundred, a single position at a
  thousand, and every position on the asset carrier, so the asset layer masks
  the accumulation rather than removing it. Both variants are marked diagnostic
  in their own records and are reported beside this run, never in place of it.


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

**Station open, registered and sequenced. C11-0 is the next run**, and every
reading below was taken before it. Pre-registered design, criteria fixed
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

**Registered and sequenced.** Gate two cannot be computed yet:
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

## B12 — how much of a holonomy reading depends on how the states were cut

Enumerated whole over every three-bin threshold cut of the delinquency ladder, so nothing is ranked and no null is needed. The between-class spread of median `|omega|` moves by 4 to 17 times across cuts: on the modification arm that exceeds the registered line on all six vintages, on the deferral arm on three of six with the other three within 12 per cent of it. **Per-loop `omega` is untouched, and that half is structural rather than measured**: coarsening changes which loops are the same loop and not what any one of them sums to. So what this binds is every quantity aggregated over cycle classes, and the 30/60-day convention is not neutral: it sits at opposite ends of the range on the two arms.

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

## A3h — a channel that moves the mechanism and carries no holonomy

`5 registered seeds` `5 seeds never drawn` `300 rounds` `nothing bought`

**The framework names where its own quantity must vanish, and this goes and
measures it there.** ``tier_positions`` is a star, so `b_1(G) = 0`, so the
product graph carries no slice cycle, so by section 5 of `docs/b1_theorem.md`
every obstruction is a square, so ``terms_spread`` is the only source of a square
sum and **``gate_spread`` cannot enter the holonomy at all**. The theorem gives
an ordering and no level, so the shares are reported and not scored.

**A zero from a treatment that does nothing proves nothing, and that objection
is answered by measurement rather than by argument.** Taking the two cells that
differ only in the gate, and then the two that differ only in the terms:

| mean over five seeds | gate | terms |
|---|---|---|
| nodes with a changed cycle count | 19.4 | 16.8 |
| total absolute cycle change | **74.0** | 85.6 |
| largest absolute move in net worth | 6.271e+02 | 5.764e+02 |
| trades only with the channel on | 2.2 | 0.0 |

**The gate's mechanical effect is 86 per cent of the other channel's**, so it is
not inert. It also moves 19.4 nodes' cycle counts while moving 2.2 in and none
out, **so it acts on the intensive margin**, which is not where an earlier
diagnostic assigned it.

**The criterion is scored on seeds that did not exist when it was written.** It
was registered on 2026-08-13 after the ordering had been seen at the registered
point, and its own note forbids retroactive use, so seeds 0 to 4 are printed as
calibration and seeds 5 to 9 carry the verdict. Five is this repository's
reference count and is not raised.

| cell | seeds 0-4, calibration | **seeds 5-9, the test** | same sign |
|---|---|---|---|
| both | 23.2667 | 15.5575 | yes |
| **loop sum only** | 21.6714 | **+18.3683** | **yes**, range [+7.11, +30.67] |
| **gate only** | +1.4091 | **−1.2264** | **no**, range [−14.29, +8.70] |
| null | 0.0000 | 0.0000 | exact, the calibration |

**Both halves hold on the fresh seeds**, and the gate cell reverses sign between
the two blocks as well as within them, which is a second reading that it sits at
zero rather than at a small positive value.

**What this does not do.** It does not thaw A3-8, which stays void for its own
reason, that no threshold was registered for its two shares before it ran. It
does not score the shares, which the registration reserves for report. And an
earlier attempt to answer the same objection by widening the population instead
found that the knob which widens it also removes the effect; **the population
was never the problem, and measuring what the treatment does to the mechanism
took two subtractions where widening took a ten-point grid.**

**Where this sits, from A3i.** Stage A7 scored the same criterion as `A7-A-4` on
2026-08-15 and recorded a failure against the conjunction, so the seeds above are
one more point on it rather than its first. A3i counts the two clauses apart.


## A3i — the two clauses of one criterion, counted apart

`57 points` `4 carriers` `2 arms` `2 population conventions` `no model run`

**4/4 criteria passed**

**A3-8′ is a conjunction, and only one of its clauses is what the theorem
licenses.** It asks that the loop-sum-only cell be same-sign across seeds
(stability) **and** that its gap exceed the gate-only cell's (ordering).
`b_1(G) = 0` gives an ordering and no level, so the second clause is the
theorem's and the first is a stability requirement added beside it.

This station runs no model. It reads every record on disk at which both cells
were computed, de-duplicates rows that are one run read twice by exact value
match and prints what it dropped, and counts the clauses apart.

| over 57 points | |
|---|---|
| **ordering: the loop cell exceeds the gate cell** | **54** |
| stability: the loop cell is same-sign across seeds | 9 |
| **the gate cell is same-sign across seeds** | **0** |
| largest absolute gate cell anywhere | **2.9375** |
| largest absolute loop cell anywhere | 24.8347 |

**The gate cell is sign-stable at none of the fifty-seven points**, across four
carriers, two attachment arms, two population conventions, two density axes and
three seed blocks, and it never reaches three in absolute value while the loop
cell reaches twenty-four. **The prediction that the gate carries no holonomy has
no counterexample on record.**

**The three points where the ordering does not hold are printed with the gate
value beside them**, and the gate cell reads exactly `0.0000` at all three:
`s = 0.95` and `s = 1.0` on one arm and `s = 0.99` on the other, all of them
within five per cent of the complete graph, whose endpoint section 4.1 of
`docs/a7_continuous_c.md` had already excluded from criteria as an attractor
with an over-determined zero.

**What this does not do.** It does not thaw A3-8, which stays void for its own
reason. It does not withdraw A7's failure: the conjunction did fail, and this
adds which half failed it and how often the other half did not. It does not
touch A7's density limit on the level of the loop cell, which is about a level
and not about an ordering. And it changes no criterion's text.


## B23 — the same statutory wedge, priced by treaty in sixteen countries

`20 countries` `no price data` `2/2 criteria passed`

**B21's wedge is set by Chinese tax law, and the obvious question is whether the
object is Chinese.** This asks it with arithmetic and no prices. The class pair
is two foreign holders of one ordinary share, one covered by a treaty with the
United States and one not, **both withheld at source and both flat**, so the two
rates come from published instruments and nothing is estimated.

**Sixteen of twenty countries carry a binding wedge**, and the treatment takes
**eleven distinct values** against the single value the A and H carrier offers.
At a three per cent yield the index runs **11.7 to 73.2 basis points, median
34.2**; Belgium is the widest at 25 points of rate, and China, the Netherlands,
India and the United Kingdom read exactly zero because their treaty rate does not
sit below their statutory one.

**That range brackets B21's own measured edges** of 14.8 and 30.5 basis points on
the two withholding legs and 52.7 on the twelve-month threshold. **The wedge is
not a Chinese artefact.**

**What this does not do.** It does not ask whether any market prices the wedge.
That needs two lines with different marginal holders, and an ordinary
convertible receipt does not provide them: a holder who can move between the
legs at the published cancellation fee cannot be a different marginal holder on
each. **Two of the station's four arms were closed on that reading rather than
on a measurement**, and the successor carrier with restricted convertibility was
closed on a depth count of twenty programmes against the ninety-seven dividend
events its own gate needs.


## B19 — closed at gate two, and the ratio that closed it was not measured

`20,335 firm-quarters` `3,516 firms` `51 quarters of filings` `stage not opened`

**Gate zero passed with room.** The thinnest cell carries 268 treated against 895
control across the compliance boundary, over eight quarters of 2023 and 2024
built from structured filings: 47,672 filings down to 20,337 with a share count,
15,482 priced, 15,099 with a return.

**Gate two did not pass**, at a readable-threshold ratio of 6.1 with the lower
bound on the larger side, and **the stage was not opened**. Nothing in the record
is a licensed reading of anything and the record says so.

**The ratio that closed it deserves its own line, because three numbers went into
it and none came from a document.** The compliant money was reached by taking
5.98 trillion at five per cent, halving it, then taking three tenths; the
denominator was the whole market rather than the compliant subset that money can
hold; and the quarterly dispersion of institutional ownership was written as
"typically 2 to 5 points" with 5 taken. **Moving the two checkable inputs to
defensible values takes the ratio from 6.1 to about 1.0, and nothing between
those two ends had been measured.**

**The third input has now been measured, and it does not slot into the ratio.**
`experiments/b19_dispersion.py` reads fifty-one quarters of structured filings,
2013Q3 to 2026Q1, sums share holdings by security over all filers, drops options
and anything not reported in shares, and takes the cross-sectional dispersion of
the quarter-on-quarter change over securities present in both quarters. Fourteen
to nineteen thousand securities a quarter, fifty quarter pairs, every one
printed.

| across the fifty quarter pairs | |
|---|---|
| median standard deviation of `dlog(shares held)` | **1.1253** |
| median interquartile range | 0.1752 |
| in points of a holding | 112.53 and 17.52 |

**Gate two took five points of a source that said two to five, in points of
ownership. This measures 112.53 points as the standard deviation of a relative
change. They are not the same quantity**, and converting between them needs an
ownership level this file does not have and does not assume, so **the ratio is
not recomputed here**. The interquartile range is printed beside the standard
deviation because holdings changes are heavy-tailed and gate two takes the noise
as its numerator, where a standard deviation on a heavy tail overstates what a
median security carries.

**The finding is that the number was measurable all along and was written down
instead.** What it does not do is reopen B19: the gate has to be restated in one
unit first, and that restatement is the next step rather than this one.

**One archive is packed differently and it stopped the first pass after
forty-eight quarters had been cached.** `form13f_2025q3.zip` puts its tables under
a dated directory while the other fifty put them at the archive root, so a lookup
by exact name found nothing. The member is now located by its base name and
**which spelling was found is printed**, because a layout that changed once can
change again.


## B17 x B7 — a comparator computed from a committed record

`no data retrieved` `withdraws nothing`

A cross-arm comparator built from `results/b7_crossfold.json` and reported beside
it. **It revises no coefficient and no criterion in either stage rests on it.**

On the balanced nineteen-class arm, the observed second eigenvalue is **twice**
the comparator's, `0.0676` against `0.0337`, while the first is only `1.15` times
it. The comparator's largest eigenvalue is carried `0.917` by a single class, the
one above sixty per cent, whose diagonal entry is `0.445`. Against a permutation
null the recorded second eigenvalue sits at `z = 3.19`. The all-ones component of
the recorded object is `-5.7e-18`, which is the calibration.


## B24 — the square lands inside the published cost band where a path exists

`62 pairs` `465 same-bell pairings` `197 A and H pairs` `one window` `one function`

**6/6 criteria passed**

**Availability was checked before anything was built** and the check is its own
record, `results/adr_availability.json`: thirty-two pairs attempted, **thirty-one
with both legs**, five years of daily bars each and 366 dividend events counted
on the thinner leg. The one pair missing a leg, `WBK`, is named there rather than
dropped.

**The framework says a square vanishes where a path between the two positions
exists.** A sponsored receipt can be cancelled into its home line, so the path is
there and its price is published in the depositary agreement. A and H shares
cannot be exchanged for one another at any price, so the restriction is a hole
rather than a term. **The class pair is two holders of a country whose treaty
rate equals its statutory rate, so the statutory term is exactly zero rather than
a difference of two numbers, and the index is not forced non-zero before the data
is read.** The receipt ratio never enters: every statistic here is translation
invariant, which is why none was looked up.

Both carriers, the same function, the same window of 2021-08-30 to 2026-08-27:

| carrier | pairs | p10-p90 | range | daily sd |
|---|---|---|---|---|
| convertible, statutory term zero | 11 | 237 | 1,044 | 111 |
| **A and H, statutory term zero** | **197** | **3,223** | 5,859 | 202 |

basis points on the log parity deviation. **The ordering holds at 13.6 times, and
the convertible side is still two orders above the published cost band.** That
distance is in the instrument, and this station measures it rather than arguing
about it.

**One series in the construction is not a price of either leg.** The daily
exchange rate is cut at its own hour and neither closing bell is that hour. **Two
pairs at one venue share that series exactly, so the difference of their
deviations carries no exchange rate at all** — nothing modelled, one term removed
by subtraction.

| venue | clock gap | pairings | min | median | p90 | max |
|---|---|---|---|---|---|---|
| **Toronto** | **0.0 h, one bell all year** | **465** | **12.1** | **16.4** | 38.7 | **54.9** |
| Sao Paulo | 0 h or 1 h | 1 | | 103.9 | | |
| London | 4.5 h | 21 | 166.3 | 223.8 | | 536.7 |
| Tokyo | 15.0 h | 6 | 131.8 | 244.1 | | 317.6 |

**The same-bell cell is thirty-two interlisted names rather than two**, and its
465 pairings run from 12.1 to 54.9 with no tail.

**Sao Paulo is not a clean zero.** Its bell is 17:00 local and Brazil has kept no
summer time since 2019, so the gap against New York is zero from March to
November and one hour for the rest of the year. **Toronto is the only venue here
that keeps one bell all year**, because it moves its clocks on New York's dates.

> **At a zero clock gap with the exchange rate removed, the dispersion between
> two listings of one claim has a median of 16.4 basis points over 465 pairings
> of thirty-one companies.**

**The ruler for that cell is not the depositary fee, and an earlier draft of this
section said it was.** `TD` and `BNS` are interlisted common shares on the New
York exchange rather than receipts: no depositary, no ratio, **no fee**, the same
shares on one register trading in two places. The published band of 0.01 to 0.05
per receipt does not apply to them at all, and their theoretical bound is
exchange-transfer and settlement friction, which is smaller and is not published
as a single number.

**That splits the registered comparison in half and each half is missing
something.** The venue with no clock gap charges no fee; every pair the fee band
applies to sits at least four and a half hours away from the New York bell, where
the bell alone contributes 150 to 320 basis points and covers a 4 to 20 point
band completely. **So "inside the published band" has no cell to be read in this
round, and it is recorded as undecidable at daily-close resolution rather than as
a failure.** The ordering does not depend on which band applies and it stands.

**The shared term is measured and the caveat it carried is now half answered.**
With the rate left in, thirty-one of the thirty-two read between 56.6 and 69.1,
median 59.5, and `sqrt(59.5^2 - 16.4^2)` is **57.2** — the same shared term the
first two names gave at 57.5. **Thirty-one companies across banking, pipelines,
rail, mining, telecoms and utilities agree on it to within 12.5 basis points, and
the one object all of them literally share is the exchange-rate series.** A
dislocation common to all of them is still not excluded by this design; it would
have to be uniform across six industries to that precision.

**The pooled median hid this and the per-pair rows showed it.** With the rate
removed the pool's median is 244 against 219 with it in, which reads as "the rate
is not the main term" and is wrong: at a zero clock gap removing the rate takes
59 down to 12.8, while at a large clock gap the bell dominates and differencing
two pairs only adds two helpings of it. **Both readings are right and the
aggregate cancelled them.**

**The instrument's floor, measured in three layers rather than asserted**: about
13 bp between two listings, about 57 bp from the exchange rate's cut, and 150 to
320 bp from the closing bells, rising with the gap. The clock gradient is printed
and not scored, and the zero-gap venue was named before the run rather than
picked after it.

**Named and not explained away**: `PHG` at 860, `NVS` at 610 and `UL` at 527 each
had a corporate action inside the window and this station did not check whether
both legs handled it on the same day and in the same ratio.

**One pair was wrong and correcting it exposed a second defect.** `PBR` is the
receipt on the ordinary share and it had been paired with the preferred line;
with the right line it reads 155.2 against the preferred line's 797.6, and 155.2
sits beside the other Sao Paulo pair's 147.4. **The wrong pair stays in the list
and keeps printing**, which is what this repository's no-deletion rule asks for,
**and that is what broke the next table**: the dictionary behind the
rate-cancelled figures was keyed on the receipt alone, so the second row
overwrote the first and printed `PBR − PBR` at exactly `0.0` beside a real
reading of `12.8`. **A perfect zero in the one table where a small number is the
finding.** The key now carries both legs, a receipt against two home lines is
named and not run, and every row is labelled with both tickers.

**What may be quoted**: one square formula reads a median 16.4 basis points where
the two listings are freely transferable into one another, over 465 pairings of
thirty-one companies spanning 12.1 to 54.9, and **196 times that** where they
cannot be exchanged at any price. **What may not**: that the square is zero on
the convertible side; that 12.8 sits inside a depositary agreement's published
band, since that pair pays no depositary fee; or the 237 pooled median as the
convertible reading, since that number has the bells in it.

**One more name behaves like the corporate actions above.** `TRP` reads 953.7
against the other thirty-one's 56.6 to 69.1; TC Energy spun off South Bow in
October 2024 and this station did not check whether both legs took it on the same
date and in the same ratio. Dropping it takes the pairwise maximum from 950.8 to
54.9, and it stays in the list and keeps printing.

**The thin part that remains is the venue dimension.** Toronto is the only venue
here that keeps one bell all year, so the replication is across companies rather
than across venues, and adding another venue would add a clock gap rather than
information. **Two rechecks are registered and both want the same thing**: an
intraday snapshot with both legs and the rate taken at one instant, which is what
reading the depositary band needs and what B21's second layer needs.


## B21 census — what a criterion has to look like to reach Corollary 1

`26 criteria` `7 records` `no model run` `no price read`

**4/4 criteria passed**

The station closed with a note beside it that none of its criteria's failures
would reach the framework. **That was a judgement, and this turns it into a
count.** Every criterion in every `b21_*` record is classified, and the file
refuses to run if one of them is unclassified.

| class | n | what it means |
|---|---|---|
| arithmetic | 7 | a closed form evaluated at prices; with `D > 0` and `P > 0` the sign and shape follow from algebra |
| **world** | **9** | a measurement whose failure would say something beyond this pipeline |
| instrument | 5 | failure impugns the pipeline, the tax story, or two estimators' agreement |
| structural | 4 | an identity to machine precision, a cell that must carry a centre, coverage |
| void | 1 | withdrawn |

**Two criteria reach Corollary 1, and both of them are arithmetic.** B21-1 says
the class index is non-zero on every leg-year and B21-15 says neither statutory
index is zero anywhere; both are `log((P1 + D) / (P1 + 0.9 D))` and neither can
come out zero while a dividend is positive. **The nine that measure the world all
speak to the instrument or to the tax story.**

> **The framework-bearing criteria and the world-measuring criteria are disjoint
> sets on this carrier.** That is the finding, and it is a design requirement
> rather than a defect in any one criterion: a criterion that reaches Corollary 1
> **and** can be answered by the data has to have a class pair whose statutory
> term is zero, so that the index is not forced non-zero before the data is read,
> while the measured square is still free to be either.

**One weak entry is named rather than counted quietly.** B21-25 asks that the
implied withholding rate sit between zero and twenty-five per cent, which is the
whole statutory support, so almost any reading sits inside it. It is classed as
world and flagged in the record.


## D14 and D17 — the two gates are one inequality written twice

`no model run` `24 combinations of alpha and se` `11 bands`

**3/3 criteria passed**

`D17` records a failure as undecidable when the test's power is below `0.50`, and
`D5` requires every number in a criterion to have a source. **The `0.50` is not a
convention.** For a one-sided test that rejects when `theta_hat / se > z`, power
is `Phi(theta / se - z)`, so **power is exactly one half at `theta = z * se`,
which is the critical value itself.** Power below the floor therefore says one
thing: the effect being tested is smaller than the value the instrument needs
before it will call anything non-zero.

**And that is gate two.** `D14` asks whether `z * se` fits inside the band the
criterion must resolve. Substituting the band for the effect, **gate two passes
if and only if the power at the band exceeds one half.** No other floor makes the
two the same line.

Measured: the departure from one half at `theta = z * se` is at most `1.110e-16`
over twenty-four combinations of `alpha` and `se`, and at B21's measured
`se = 0.012672` the two gates return the same verdict at all eleven bands.

**What a failure is worth is printed beside it.** A non-rejection carries
likelihood ratio `(1 - alpha) / (1 - power)` for the null, which is its entire
evidential content. At the floor that is `1.90`, and one bit arrives at power
`0.525`. **The floor sits just below the one-bit line**, so a failure between
`0.50` and `0.55` is recorded as a failure while being worth less than one bit;
the ratio is reported next to the verdict rather than the line being moved.

At zero power the ratio is `0.95`, **below one**: a test that can never reject
gives, when it does not reject, weak evidence against the null rather than none,
because the null would have rejected `alpha` of the time.


## A3j — where the gate is inert, and it is the opposite end of the knob

`10 stretch values` `5 seeds` `300 rounds` `gap column read from A3g's record`

**4/4 criteria passed**

**A3h answered the inertness objection at one point and A3i counted the readings
at fifty-seven, and the join between them was one point wide.** Everywhere else,
"the gate cell is noise" and "the gate does nothing there" were not yet
separated. This takes A3h's two subtractions along A3g's declared stretch grid
and prints the gate cell beside them. Every value is printed and none is
selected.

| stretch | population | gate total abs Δ cycles | terms | **ratio** | gate cell |
|---|---|---|---|---|---|
| 1.0 | 18.4 | 68.8 | 92.0 | **0.748** | −0.5546 |
| 2.0 | 24.2 | 68.4 | 64.0 | **1.069** | −2.4759 |
| 3.0 | 41.6 | 74.0 | 85.6 | **0.864** | 1.4091 |
| 4.0 | 66.4 | 67.2 | 72.6 | **0.926** | 1.3004 |
| 5.0 | 98.8 | 76.6 | 81.2 | **0.943** | 1.4748 |
| 6.0 | 128.8 | 69.2 | 86.0 | **0.805** | 0.0248 |
| 8.0 | 138.8 | 44.2 | 89.8 | **0.492** | −0.0032 |
| 12.0 | 153.2 | 64.0 | 94.4 | **0.678** | −0.0020 |
| **20.0** | 178.4 | **0.0** | 98.0 | **0.000** | 0.0000 |
| **40.0** | 200.0 | **0.0** | 93.0 | **0.000** | 0.0376 |

**The objection said a narrow population leaves the treatment nothing to act on.
At the narrowest end, 18.4 nodes, the ratio is 0.748 and the gate is acting. At
the two widest, 178.4 and 200.0 of 200, it is exactly zero and the gate changes
not one cycle.** The inertness is at the wide end, and the reason is in A3g's own
population column: an admission rule that disperses entry has nothing left to
ration once nearly everyone is already in. **A rule needs somebody it keeps out.**

**So A3g's reading that the two requirements sit at opposite ends of one knob
holds, and the reason it recorded for it does not.** Turning that knob up first
removes the effect being read, the gap falling from 25.83 to 0.09, and then
removes the treatment itself.

**What it does to A3i.** Two of the fifty-seven pooled points are now known to
carry an inert treatment. Dropping them leaves both counts saying the same
thing: the ordering holds at 52 of 55 and the gate cell is sign-stable at none
of them. A3i's record is unchanged, since its pool is defined as the points at
which both cells were computed.

**Stretch 3.0 reproduces A3h's registered block to the digit**, 74.0 against
74.0 and 85.6 against 85.6.

**No threshold is placed on the ratio.** The eight interior values are reported
and not scored; the two zeros are a printed object and not a line crossed.


## B13 — the zero domain, measured where the order can actually be placed

`81,968 states` `9 products` `3 channels` `one ten-minute window of 2023-07-17` `the vendor's free public sample`

**7/7 live criteria passed**

**The framework names where its own quantity must be zero and this station goes and measures it there.** Never worse than the two-leg derivation in 81,968 states over nine products, exactly equal on six of them, while the directly quoted member of the same family is non-zero in 65 to 96 per cent of states.

**Why six and not all nine is open.** The explanation the station first gave is superseded in B13-2, and the six are not distinguished from the other three by anything established here.

| | criterion | detail |
|---|---|---|
| PASS | B13-0  the gate: one spread, both multicast sides, a book class that implements every action it is sent | 34923 end-of-event states with a book change on one of the three instruments, 2442 of them republished the spread's implied book and are paired. Update actions this book class does not implement: 0. Reading only the A-side of an A+B deduplicated capture had cost 2 per cent of updates and produced a bid agreement of 0.9229 that looked like a finding; with both sides it is 0.9990 |
| PASS | B13-1  section 4.A.2, load-bearing: the exchange's published implied price is never worse than the two-leg derivation | 0 violations in 63168 states on ch382, 0 in 5336 on ch386 and 0 in 13464 on ch360, over nine products and three channels. The criterion is a one-sided inequality and not an equality, which is what makes zero violations the whole of it |
| PASS | B13-2  on six of the nine products the inequality is an equality, bit for bit, and why those six is not established | equality rate 1.0000 on both sides of both ch386 and ch360, which is 2668 offer and 2668 bid states there and 6732 of each on ch360, 18800 in all. **The explanation the station first gave is withdrawn**: it said those products have only one derivation path, and the instrument listing says otherwise for every root measured, CL 906 of 906 multi-path, NG 1124 of 1127, GC 231 of 231, HG 820 of 820, MHG 780 of 780, QI 55 of 55. The reading stands and the attribution does not |
| PASS | B13-3  the same apparatus on the directly quoted member of the same family returns non-zero | share of states with a non-zero gap between the directly quoted book and the two-leg derivation, by channel: 0.8751 offer and 0.9240 bid on ch382, 0.7470 and 0.6516 on ch386, 0.9478 and 0.9610 on ch360. Nine products, no exception. **Not an economic statement**: it is ordinary queueing and market-making difference, and the design file forbids reading it as more |
| PASS | B13-4  section 5.2's precondition: the spread quotes on the same grid as its legs | equal 10 different 0 no data 0 on ch382, equal 7 different 0 no data 0 on ch386, equal 8 different 0 no data 0 on ch360. **This registered check was skipped when the gate first ran and was performed afterwards**, so the readings above stood on luck until it passed. Measured as the gcd of the observed prices rather than read off the definition field |
| PASS | B13-5  B4's section 5.1 split, both halves computed on live quotes for the first time in this repository | the split is available in 49116 of 50055 states, 0.981; Theorem 6(1)'s sign constraint has 0 counterexamples in those 49116; the index part is exactly zero in 12637 of them. B5 could report the index half and never the friction half, and this is the first carrier that quotes all four legs natively |
| PASS | B13-6  Theorem 6(4)'s bound, and section 5.1's own criterion for two agent classes, adjudicated per position edge | 0 violations of \|S - S'\| <= -(S + S') in 49116 states; rho median 0.2000 with 0 states at rho = 1. Under the parity control the index is zero in 0.5649 of the states where zero was available: CLU3-CLV3 takes it 716 times out of 716 and is one class, RBU3-RBX3 takes it 88 times out of 1978 and RBU3-RBV3 155 out of 1895, and those two are two classes |

## B14 — a dated, exogenous, symmetric friction change: the SEC tick size pilot

**The friction half moves in both directions.** The 5-cent grid widens the treated spread against the control in 2016, six inequalities of six, and lifting it narrows them again in 2018, six of six, once both rounds are read on the population they share. It holds on both venues under every weighting convention tried, and after dropping the order types that carry most of the share weight without participating in the spread.

**The index half is beyond this carrier's reach, and the reason is structural rather than a matter of power.** `S - S'` is a difference of price levels and a tick-size change works by moving those levels onto a lattice, so projecting the post-release quotes back onto the nickel grid reproduces 88.7 per cent of the whole move and the residual sits inside a placebo band. Closed rather than paused. **What the stage produced instead is a carrier specification**: `docs/b4_directed_edges.md` section 9 now carries three conditions where it carried one, and Theorem 6(5) is new.

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

**7/8 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B14-0  the friction half moved on the 2016 round, and it is not carried by the orders that do not participate in the spread | the primary share-weighted convention holds all six inequalities, and so do the order-count convention, the adverse convention and the NBBO cross-check. A19 then drops the order types that the code table named: away-from-market orders, which carry the largest single block of the share weight, retail liquidity providing orders, and both together. The primary measure holds 6/6 in every one of the three variants. Same event, same data, only the weight composition changes. **One caveat travels with any citation of T6**: its own 6/6 depends entirely on order type 22, holding under the retail variant and falling to exactly 3/6 under the other two. T6 was excluded from the verdict before the run, so nothing moves, but the dependence must be quoted with it |
| PASS | B14-A  leg A, the pilot's termination read as a reversed event, on the population the two rounds share | the two rounds had been reading different symbol universes. The venue's Appendix B coverage runs 618 distinct symbols in 201803 and 2110 in 201804, between the rounds, and from 201804 on it matches the other venue's where before it carried about a third of it. Restricted to the 618, which is a coverage fact and predates both of the round's windows, the primary window holds 6 of 6, every one of the four venue weighting conventions agreeing in sign and in the predicted direction, and the control group's own delta is 0.0594 where the unrestricted run gave 0.2766. Four of the six cells sit outside every gap measured on window pairs where nothing happened, whether those pairs are taken inside the pilot, widest 0.1299, or after it, widest 0.0593. The unrestricted run stands unaltered in results/b14_gate_exit.json and its own numbers are not touched; what changed is the population it was read on, not the criterion |
| PASS | B14-B0  leg B was bought and the wire format was read correctly | 108 NYSE-listed pilot symbols on two venues over eight months of bbo-1s. The depth gate's four registered checks all passed before a cent of bulk data was bought, and the pull came to 34.689578 dollars against a quote of the same. The semantic check is exact: every treated name, on every second the pilot was in force, has all four prices on a whole nickel |
| PASS | B14-B1  gate one: the two venues are two classes in section 5.1's own sense | the framework hands over its own criterion, that S - S' is zero exactly when the two classes face the same antisymmetric terms, so the question is measurable. Per control symbol, the count of days whose sign leans positive against a binomial null: 9 of 47 symbols beyond three standard deviations where the null expects well under one, and a median \|z\| of 2.08 where the null gives 0.67. Run on the control arm only, because inside the pilot the grid pins both venues to one lattice point and that branch is unreachable there |
| PASS | B14-B2  gate two: the grid's arithmetic reproduces 88.7 per cent of the whole pre/post move | projecting the post-release quotes back onto the nickel grid, bid down and ask up, reproduces most of the inside/outside gap in the primary statistic. The projection is verified by being the identity on treated names inside the pilot, digit for digit, since those are already on the lattice. Theorem 6(5)'s spread term is 1 to 5 per cent of the numerator by mass, so rho is not measuring spread asymmetry |
| **FAIL** | B14-B3  gate three: the residual is inside the placebo band, and leg B is CLOSED rather than paused | the treatment-specific residual sits inside a range built from six month pairs with no grid change at all. Half-month resolution widens the sample of placebos to fourteen and does not overturn it. A three-bin split on the pre-pilot spread has one bin clear its own band, but that bin's gradient lives in the control arm, which is not treatment heterogeneity. **Closed, not paused**: the arithmetic share is a property of the mechanism, and no quantity of further data changes it. The narrow-band discontinuity is sealed and is the basis of nothing |
| PASS | B14-19  order-type sensitivity, askable only once T7's code table arrived | the specification gives thirteen order-type codes; twelve are on disk and the absent one is exactly the Not Held code, which is a check that was written before the document was fetched and could have failed. The weighting is share weighted, which settles D3-3 and demotes the order-count convention from a co-verdict to a cross-check without moving any verdict |
| PASS | B14-20  B14_A11's candidate list reopened: the pilot's rule is an increment rule, so slack does not mean out of reach | a name whose spread already exceeds the increment can still have both sides off the lattice, and projecting widens it. One delta for every bin, bounded by the lattice arithmetic, fits at 0.0228 dollars with the gradient in the treated arm and an r-squared of 0.5074, and the tightest bin's observed margin is reproduced by the curve to a residual of 0.0045. B14_A11's reading that the residue is real stands; its statement that spillover is the only remaining candidate is withdrawn |

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

### the placebo band, and what it does to leg A's reading

`results/b14_placebo_band.json`. Eighteen five-month blocks shaped exactly like
leg A (two months of pre, one dropped, two of post), every one wholly inside the
pilot, where the treatment does not change and the true gap is zero by
construction. Block nine is the calendar twin: the same months as leg A with the
pilot running throughout. The blocks overlap, so their count is consistency and
not a sample size; the largest non-overlapping subset has three members and its
spread matches the eighteen.

**The control group's own delta settles what leg A was reading.** On venue N the
placebo runs from -0.1335 to +0.1097 with a median of -0.0099, and the calendar
twin reads +0.0028. Leg A reads +0.2766, larger than all eighteen. The move is
the fourth quarter of 2018 and not the calendar: the same months a year earlier,
with the pilot in force, give essentially zero. On venue P leg A's -0.0316 sits
inside the band and the twin is the band's own maximum, so the two venues' common
drift is not synchronised.

**Four of leg A's six cells sit inside the band.** Against a band of roughly
+/-0.05 on the primary measure, N/G2 (+0.0510), N/G3 (+0.0218), P/G1 (-0.0324)
and P/G2 (+0.0022) are not readings. Two are outside it, N/G1 at -0.0994 and
P/G3 at -0.0502, and both are on the side the exit predicts.

**So the registered six-of-six criterion could not have passed.** It asks every
cell to clear a band that four of the six true effects are smaller than. The
reading this stage supports is not that the prediction failed; it is that on four
cells the instrument resolves nothing, and on the two where it resolves anything
the prediction holds. The pass/fail labels in `b14_gate_exit.json` are superseded
by this band and should not be quoted.

### the same check run on the entry round, which the audit had not touched

The window contamination was found on the exit round and the entry round was not
checked against it. That is an audit that only cuts one way, so it was run. The
entry's post window is November-December 2016 and contains the US election.

Its control delta is +0.1202 on venue N, outside the same eighteen-block band
(-0.0851 to +0.0864) that the exit's +0.2766 was outside. So the entry window is
not quiet either. What separates the two is size: on venue N the entry's gaps run
+0.2792 to +0.4394, three to four times the control's own move, where the exit's
run +0.0012 to +0.0780, a fraction of it.

Across six cells and the four venue conventions, all twenty-four of the entry's
gaps carry the same sign, and no cell crosses zero. The weakest, P/G3 under the
T6 convention at +0.0211, sits inside the placebo band; every other cell on venue
P runs +0.0265 to +0.1058 and every cell on venue N is an order of magnitude
clear. The entry reading stands, and it stands because the effect dwarfs the
drift rather than because the window was clean.

**One sentence elsewhere in this stage's heading needs reading narrowly.** "Under
every weighting convention tried" is true of the entry round, where twenty-four
of twenty-four agree in sign, and it is not true of the exit round, where five of
six cells flip sign with the convention. The claim belongs to the entry.

### the exit round on the entry round's population, and two wrong diagnoses before it

`results/b14_gate_exit_pre804.json`. Population: the 618 symbols in the venue-N
Appendix B file for 201803, the last month before that file's coverage tripled.
The restriction is a coverage fact, it predates both of the round's windows, and
applying it to both venues puts the exit round on a population comparable to the
entry round's. Criterion: sign agreement across the four venue conventions, which
is not a line on an estimate.

| post window | control delta N | control delta P | sign agreement | predicted direction |
|---|---|---|---|---|
| October | -0.0003 | -0.0715 | 5/6 | 5 |
| November-December | +0.0594 | -0.0495 | **6/6** | **6** |

The gaps run -0.0203 to -0.4866. On the full population they ran -0.0012 to
-0.0780, so the effect is an order of magnitude larger here, and the control
delta that was +0.2766 is +0.0594.

**So the fourth quarter of 2018 was never the cause.** The crash showed up as a
0.2766 move in the control group only because the population contained about 1400
names whose venue-N activity is marginal, and thin quotes blow out in a crash. On
the population the entry round ran, the same crash moved the control by 0.0594 and
every cell still reverses.

**Two diagnoses were published in this session before this one and both were
wrong.** The first said the November-December window was contaminated by the crash
and moved the window to October. The second said there was no clean post window at
all, because the post-pilot level series swings 0.62 where the preceding two years
swing 0.24. Both were reading a symptom. The level series carried the answer
already, in the jump from -2.34 to -1.98 across 201804 and 201805, and that jump
was recorded as a coverage change and then not connected to the failures it was
causing.

**What this costs and what still stands.** The restriction was arrived at by
chasing failures, and that is how it was found; its justification is separate and
predates the looking. The October window change stands on its own reason, which is
that the 2018 end had no phase-in. Sign agreement needs no band, but any
statement about size does, and the bands in `b14_placebo_band.json` and
`b14_placebo_band_1m.json` were measured on the full population. The band on these
618 symbols is `b14_placebo_band_pre804.json` and `b14_placebo_band_1m_pre804.json`,
and the post-event check that it transfers is `b14_placebo_post.json`; both are in
the two subsections below.

### the placebo band on the 618, which is the one the restricted readings stand on

`results/b14_placebo_band_pre804.json` and `results/b14_placebo_band_1m_pre804.json`,
from `experiments/b14_placebo_band.py --pop pre804`. The same eighteen five-month
blocks and twenty one-month blocks as before, all of them wholly inside the pilot
where the true gap is zero by construction, with both venues restricted to the 618
symbols in the 201803 venue-N file. The filter goes in between load and deltas,
the same place and the same operation as in `b14_gate_exit_pre804.py`, so the band
and the gap stand on one population.

Rule 19 was read by running rather than by reasoning. `--pop full` reproduces all
eighteen five-month blocks on disk field for field, with one exception that is
itself a finding: the `files` field went from 66 to 72 and every reading held.
`X.load` lists the whole cache and filters by date, so that field counts what was
in the cache when the block ran, not what the block read. Three more months were
built for the October re-read, all of them ending after every block here ends. The
field is a per-run number sitting in a checked file, which the write discipline's
sixth clause forbids; it is left in place, and named here so that the next reader
does not take it for a property of the block.

**The five-month shape, against the November-December post window.**

| cell | observed, four conventions | weakest | band, 18 blocks x 4 | blocks at least as large |
|---|---|---|---|---|
| `N/G1` | -0.3777 -0.4362 -0.3669 -0.3572 | 0.3572 | -0.0660 to +0.0851 | **0 / 72** |
| `N/G2` | -0.1974 -0.2321 -0.1943 -0.1900 | 0.1900 | -0.0600 to +0.0955 | **0 / 72** |
| `N/G3` | -0.3998 -0.4866 -0.3998 -0.3880 | 0.3880 | -0.0831 to +0.0810 | **0 / 72** |
| `P/G1` | -0.1550 -0.1031 -0.1582 -0.1232 | 0.1031 | -0.1299 to +0.0884 | 3 / 72 |
| `P/G2` | -0.0577 -0.0513 -0.0456 -0.0203 | 0.0203 | -0.0735 to +0.1047 | 46 / 72 |
| `P/G3` | -0.2025 -0.0287 -0.1944 -0.1374 | 0.0287 | -0.0891 to +0.1032 | 35 / 72 |

Control delta: observed N +0.0594, and seven of the eighteen in-pilot blocks move
the control at least that far; observed P -0.0495, and nine of eighteen do. The
common move on this population is an ordinary one. On the full population the same
window gave +0.2766, larger than every block in the band, which is what made the
original reading unreadable.

**The one-month shape, against the October post window.**

| cell | observed, four conventions | weakest | band, 20 blocks x 4 | blocks at least as large |
|---|---|---|---|---|
| `N/G1` | -0.3155 -0.3719 -0.3170 -0.3099 | 0.3099 | -0.0812 to +0.0496 | **0 / 80** |
| `N/G2` | -0.2226 -0.2360 -0.2240 -0.2158 | 0.2158 | -0.0749 to +0.0405 | **0 / 80** |
| `N/G3` | -0.3599 -0.4476 -0.3613 -0.3646 | 0.3599 | -0.0654 to +0.0502 | **0 / 80** |
| `P/G1` | -0.1339 -0.1073 -0.1312 -0.1144 | 0.1073 | -0.1193 to +0.0929 | 2 / 80 |
| `P/G2` | -0.1132 +0.0026 -0.0866 -0.0503 | 0.0026 | -0.0727 to +0.0900 | 77 / 80 |
| `P/G3` | -0.2694 -0.1078 -0.2081 -0.1517 | 0.1078 | -0.0903 to +0.0741 | **0 / 80** |

Control delta: observed N -0.0003, quieter than all twenty in-pilot blocks;
observed P -0.0715, with four of twenty at least that large.

**How to read the last column, and how not to.** It is a count over overlapping
windows. The eighteen five-month blocks are eighteen views of one panel and the
largest non-overlapping subset has three members; the twenty one-month blocks give
seven. So the column reports consistency across the in-pilot span and is not a
sample size, and `0 / 72` is not a p-value of 1/72. No line is drawn on it. The
comparison point chosen for each cell is the weakest of the four conventions,
which is the conservative end.

**What the two tables say together.** Four of the six cells, the three venue-N
groups and `P/G1`, sit outside everything the in-pilot span produced, on both post
windows, at the weakest convention. `P/G3` sits outside on October and inside on
November-December. `P/G2` sits inside on both.

`P/G2` is the same cell whose sign disagrees across conventions in the October
reading. Two readings taken for different reasons, sign agreement and magnitude
against noise, single out the same cell. Nothing in the design forced that.

**Restricting widened the band rather than narrowing it.** Venue N was already
about 618 to 686 symbols throughout the in-pilot span, so its band barely moves:
the five-month `N/G2` maximum is 0.0955 on both populations. Venue P falls from
about 2,100 symbols to 618, fewer symbols per cell and therefore noisier, and its
band widens accordingly: five-month `P/G1` goes from 0.0627 to 0.1299, one-month
`P/G1` from 0.0607 to 0.1193. The gaps are read against the wider band.

### the post-event placebo: does the in-pilot band transfer, and does the crash forge gaps

`results/b14_placebo_post.json` and `results/b14_placebo_post_full.json`, from
`experiments/b14_placebo_post.py`. Four one-month-shaped blocks, every window
wholly after the close on 2018-09-28, when the quoting and trading requirements
ended for every test group at one moment and every pilot security opened in the
control condition on October 1. A test-versus-control gap measured entirely after
that date has nothing generating it.

The group labels cannot come from the panel file here. Its `test_group` column is
the live condition and reads `C` for every row from 201810 on, 46,668 then 42,283
then 38,144 rows with no other value, so reading labels from the pre window as both
rounds do would put every security in the control group and return nothing. They
come from the FINRA assignment file through `b14_gate0.load_authoritative`, 2,395
tickers, the same external list `b14_gate0`'s authoritative arm already uses. That
substitution is why this is a separate script and not a flag on the band.

| | blocks | gap readings | largest \|gap\| | median \|gap\| | largest \|control delta\| |
|---|---|---|---|---|---|
| the 618 | 4 | 96 | **0.0593** | 0.0244 | 0.1200 |
| full population | 4 | 96 | **0.0543** | 0.0142 | 0.1846 |

Per block, largest gap anywhere among six cells and four conventions, on the 618:
0.0593 for December, 0.0572 for January, 0.0429 for February, 0.0493 for March.

**This was run to answer an objection raised against the band above, and it clears
it.** That band is measured on blocks wholly inside the pilot and applied to
windows that are not, which is a criterion whose scope does not meet its object's.
The post-pilot regime turns out to be the quieter of the two: 0.0593 here against
0.1299 and 0.1193 in the in-pilot band on the same symbols. The band is therefore
the conservative one to read the exit round against, and reading the exit round
against the tighter post-event numbers would only widen the margin.

**The crash is inside the first block and produces nothing.** That block's post
window is December 2018. Its largest gap anywhere is 0.0593, against the 0.19 to
0.49 the exit round reads on the venue-N cells. Whatever the fourth quarter of 2018
did to quotes, it does not forge a test-versus-control gap on this population.

**The restriction does not manufacture gaps either, which is the check it most
needed.** If cutting to 618 symbols inflated the statistic mechanically, these
blocks would show it, because they run the identical machine on the identical
population with nothing to find. Largest gap 0.0593 restricted against 0.0543 full.
The two are the same number to within the difference between four and four blocks.

**What separates the two populations is not noise in the gap, it is attenuation.**
Post-event, where test and control sit in the same condition, a common move cancels
in the difference and both populations read near zero; the full population's control
does swing further in level, to 0.1846 against 0.1200. Across the event the gaps run
-0.0012 to -0.0780 on the full population and -0.0203 to -0.4866 on the 618, six
times larger, and the roughly 1,400 added symbols are names whose venue-N activity
is marginal. A diluted effect, not an inflated variance.

### the level on the 618, from 201604 to 201903

`results/b14_level_series_pre804.json`, from
`experiments/b14_level_series.py --pop pre804 --write`. Every other reading in this
stage is a difference between two windows, and a difference cannot say whether one
of its windows is unusual. This is the level: the median of log(spread ratio) by
month, for the 618 symbols the restricted readings stand on, with group membership
fixed by the published assignment list so that it cannot change in 201810 when
every pilot security opens in the control condition. No threshold is drawn on it.
`--pop full` reproduces all 288 cells of the series already on disk.

**The coverage break disappears when the population is held fixed, which is the
last thing that diagnosis needed.** Venue N's control level jumps +0.1085 across
201803 to 201804 on the full population, where the symbol count goes 301 to 681. On
the 618 the same step is +0.0021 and the count goes 301 to 299. Nothing happened to
these securities in 201804.

**Test group minus control, three regimes.**

| cell | pre-pilot, 201604-09 | in-pilot, 201611-201809 | after, 201810-201903 | the six months after, in order |
|---|---|---|---|---|
| `N/G1` | -0.07 to -0.00 | +0.14 to +0.32 | -0.25 to -0.06 | -0.06 -0.11 -0.25 -0.15 -0.06 -0.10 |
| `N/G2` | +0.07 to +0.10 | +0.23 to +0.47 | +0.13 to +0.47 | +0.29 +0.32 +0.47 +0.30 +0.30 +0.13 |
| `N/G3` | -0.22 to -0.09 | -0.08 to +0.22 | -0.29 to -0.03 | -0.29 -0.28 -0.09 -0.03 -0.09 -0.11 |
| `P/G1` | -0.13 to -0.03 | +0.02 to +0.34 | -0.21 to -0.08 | -0.21 -0.13 -0.08 -0.10 -0.18 -0.16 |
| `P/G2` | -0.02 to +0.07 | +0.23 to +0.46 | +0.22 to +0.36 | +0.36 +0.31 +0.36 +0.27 +0.28 +0.22 |
| `P/G3` | -0.07 to +0.10 | +0.00 to +0.30 | -0.15 to +0.02 | -0.13 -0.15 -0.11 +0.02 -0.08 -0.15 |

The last column is the six post-pilot months in order rather than a verdict. An
earlier draft of this table carried a two-word summary computed by comparing the
post range against the pre range plus a constant, which is a line drawn on an
estimate and is the shape rule 11 forbids; it labelled `N/G3` as staying up on a
0.01 margin while the two ranges overlap across most of their width. The ranges and
the months are the object; no summary of them is offered.

Written out for venue N: `G1` runs -0.07 to -0.00 across the six months before the
pilot, +0.14 to +0.32 across the twenty-three months of it, and -0.25 to -0.06
after. `G3` runs -0.22 to -0.09 before, -0.08 to +0.22 during, -0.29 to -0.03
after. Both are square waves against their own baselines, and the baselines are not
zero, which is why each group has to be read against its own pre-pilot level rather
than against the control line.

**`G2` steps up and does not come back.** On venue N it runs +0.09 before, +0.25 to
+0.47 during, and +0.13 to +0.47 after; the lowest post-pilot month is March 2019
at +0.13, so it may be reverting on a horizon longer than the six months of data
that exist. On venue P it does not step at all at the switch, +0.353 in 201809
against +0.357 in 201810.

**That is the third reading to single out the same group, from a third direction.**
`P/G2` is the cell whose sign disagrees across weighting conventions in the October
round, and the cell whose gap sits inside the noise band on both post windows. The
level says why: there is no step there to read. Sign agreement, magnitude against
noise, and the level picture were taken for unrelated reasons and land on one
object.

**What this does and does not cost leg A.** The round measures the step at the
switch, and `N/G2` does take one: its gap reads -0.19 to -0.23 against a band whose
widest reading is 0.13. What the level adds is that the step does not carry `G2`
back to where it began. The claim leg A can carry is that the friction half moves
with the friction in both directions; the claim it cannot carry is that the friction
half returns to its pre-treatment relation for every group.

**The pre window is ordinary.** 201808 and 201809 read -2.280 and -2.314 on venue N
against an in-pilot plateau of -2.185 to -2.412. An earlier reading in this stage
proposed that the shared pre window was what both post windows were reacting to.
On this population it is unremarkable, and the population was the cause.

### the level series, and the coverage change nobody had looked at

`results/b14_level_series.json`. Every other reading in this stage is a difference
between two windows, and a difference cannot say whether one of its windows is
unusual. This is the level, month by month, for a population fixed by the
published group list.

**Venue N's reporting scope changes in April 2018.** Distinct symbols in the
Appendix B file: 969 in 201608 before the pilot, 687 from 201610 when it narrows
to the pilot universe, 618 by 201803, then **2110 in 201804**, and from there on
venue N and venue P are identical to a handful. Before that break venue N carried
about thirty per cent of what venue P carried. The names that appear are
Nasdaq-listed and the group proportions are preserved, so this is reporting scope
and not the market.

**The entry round and the exit round are therefore not the same instrument on the
same securities.** The entry reads about 679 venue-N symbols, the exit about 2070,
and roughly two thirds of the exit's population is Nasdaq-listed names whose
venue-N activity is marginal. Thin activity gives noisy spreads, and noisy spreads
are what make an answer turn on the weighting convention, which is exactly the
exit round's symptom. That is a candidate explanation and is recorded as one; it
is not established until the exit round is re-run on the pre-April-2018
population.

**The entry round's own windows straddle the 201610 change and it survives that**,
because a symbol must appear in both windows to contribute, so the population is
the intersection; gate0's 679 venue-N symbols is the narrower scope already.

**After the pilot ends the series stops being stable.** From 201604 to 201803 the
venue-N control level stays between -2.4406 and -2.2021, a range of 0.24 across
two years. From 201810 to 201903 it runs -1.8161, -1.1970, -1.4564, -1.2008,
-1.6455, -1.7590: a swing of 0.62 in six months, with November and January more
extreme than December although December was the worse month for the market. So
the exit round has no clean post window, and the reason is a property of this data
after the pilot ended rather than one quarter's weather. October reads clean
because it is the last month before the swing starts, and it has already moved
from -1.93 to -1.82.

**The pre window is not the anomaly, and an earlier reading in this session
guessed that it was.** The guess was that two post windows a quarter apart giving
the same control delta pointed at the window they share. The level series shows
201808 and 201809 flat against each other and against the months before them, and
the instability entirely after them. The guess was wrong and is recorded as wrong.

### leg A re-read on October, and why the window changed

`results/b14_gate_exit_oct.json`, band in `results/b14_placebo_band_1m.json`.

**Why October was dropped, and why that reason does not transfer.** The 2016
round drops October 2016 because the pilot phased in across it: the test groups
entered in waves between October 3 and October 31, so the month is neither a pre
nor a post observation. Leg A mirrored that drop into 2018. The 2018 end has no
such property. Cboe's expiration notice records that the quoting and trading
requirements ended "at the close of trading on September 28, 2018" and that "as of
October 1, 2018, all securities in Tick Pilot Test Groups will open in the Control
Group": one moment, every group, no waves. The mirror carried the calendar shape
of the drop without carrying its reason.

**How the window was arrived at, stated rather than implied.** This is a redesign
after the fact. The defect was found by reading data: leg A's control delta of
+0.2766 exceeded all eighteen placebo blocks, and enumerating every post window
anchored on 2018-09-28 showed October to be the only one whose control delta sits
inside the band. The justification is separate from the discovery and is
structural, and it was available before any window was run. Both belong in the
record. The original verdict stands unwithdrawn.

**The window is clean.** Control delta +0.0573 on venue N and -0.0298 on venue P,
both inside the matching band (N -0.0674..+0.0640, P -0.0423..+0.0668) measured on
twenty in-pilot blocks of the same shape. Those blocks overlap; the largest
non-overlapping subset has seven members and its spread matches.

**All five conventions, and what they actually say.** The raw gaps, negative
meaning the treated group's spread narrowed relative to control, which is the
direction the exit predicts:

| cell | `bbo_shr` | `bbo_cnt` | `bbo_shr_adv` | `bbo_shr_adv2` | `nbbo_shr` |
|---|---|---|---|---|---|
| N/G1 | -0.0583 | -0.0780 | -0.0456 | -0.0505 | -0.0719 |
| N/G2 | +0.0134 | -0.0015 | +0.0136 | +0.0097 | -0.0367 |
| N/G3 | -0.0012 | +0.0102 | +0.0135 | +0.0112 | -0.0577 |
| P/G1 | -0.0389 | +0.0046 | -0.0160 | +0.0134 | -0.1211 |
| P/G2 | -0.0322 | +0.0262 | -0.0151 | +0.0044 | -0.0844 |
| P/G3 | -0.0433 | +0.0227 | +0.0022 | +0.0115 | -0.1199 |

**One cell is a reading and five are not, and the reason is in the numbers rather
than in any rule.** On N/G1 the four venue conventions agree in sign and in size,
-0.0456 to -0.0780, and the range never crosses zero; the primary puts it outside
the band. On the other five the sign flips with the weighting: P/G3 runs from
-0.0433 to +0.0227 depending only on whether rows are weighted by shares or by
order count and on whether zero-spread rows are admitted. The spread across
conventions, 0.015 to 0.066, is the same size as the effects being read. A
quantity that changes sign when the weighting changes, by as much as the quantity
itself, is not a measurement of anything at this precision.

**The disagreement is itself informative and is recorded as a finding rather than
as a nuisance.** Share weighting and order-count weighting come apart when large
orders behave differently from small ones, and admitting zero-spread rows matters
when locked and crossed quotes are common. That the sign turns on those choices
says the effect lives in a subset of rows the weightings treat differently, and
locating that subset is a question this stage did not ask.

**The consolidated measure is negative on all six, from -0.0367 to -0.1211, and it
is a different object.** The NBBO is not a venue-level quantity, so a venue-level
design cannot score it without putting criterion and object in different scopes.
That it is the one measure with no disagreement is consistent with the mechanism:
the best quote across all venues moves as soon as any single venue improves, while
one venue's own spread also carries that venue's share of everything else.

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

**This stage is B6's zero calibration and that is the whole of its purpose.**
B6 found an edge the law grants, that is posted, and that nobody walks, on 207
of 207 Cuban publication days, and the one thing that reading could not
establish about itself is whether the instrument says as much of any economy
with an official rate and a parallel market beside it. **Bolivia reads 21 of
52** against the same 95%. **The instrument discriminates, so B6-15 is a fact
about Cuba rather than a reflex of the method.**

**What it discriminates on is sharper than the contrast between two countries.**
Measured against Bolivia's own frozen peg the same window reads 100%, against
what the banks were actually selling at 65.4%, and after the peg went and the
official rate began to follow the market, 40.38%. **A posted price nobody
transacts at is what produces the Cuban reading**, and the reading falls when
the official rate becomes one somebody trades at.

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

## B2A — dispersion in financing terms at fixed position and date, against a scalar price field's prediction of zero

20,071,740 loans `min_cell_size=20` `spread_bound=20.0` 160 rows outside the plausibility band

**7/7 live criteria passed**

| | criterion | detail |
|---|---|---|
| PASS | B2A-1  variance decomposition is exact | between 0.095178 + within 0.343669 = 0.438848 |
| PASS | B2A-2  dispersion survives fixing position and date | within share 0.7831 over 1,103,962 cells and 20,071,740 loans. Integrability predicts exactly zero |
| PASS | B2A-3  the median cell has a non-trivial spread | median within-cell IQR 0.5257 points, median p90-p10 1.0774, over 328,902 cells of at least 20 loans |
| PASS | B2A-4  restricting to well-populated cells does not weaken it | all cells 0.7831 over 1,103,962 cells; cells of at least 20 loans 0.8480 over 328,902 cells and 16,177,088 loans. Sparse cells have zero within variance by construction, so the unrestricted figure is the conservative one |
| PASS | B2A-5  it does not vanish within occupancy type | principal residence: 0.8289 over 602,375 cells (0.8502 over the 317,689 of at least 20 loans), second residence: 0.6155 over 259,726 cells (0.8418 over the 10,227 of at least 20 loans), investment: 0.3482 over 241,861 cells (0.5049 over the 986 of at least 20 loans) |
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
| PASS | P2  conventional exceeds FHA | conventional 0.8480 vs FHA 0.4757 = +0.3722. Both accounts predict this sign, so it grades the effect and separates neither; the reading holds, it just does not tell the two apart |
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

## B5 source audit — the friction column, screened out on paper before anything was bought

The verdict is in the heading, which is where it belongs: this is a source audit and not a set of pre-registered criteria, so there is no table under it and there never was one.


## B5 source audit — the P2P control class, screened out on paper before anything was bought

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

## B8 — the modification triangle on Fannie Mae loan performance: a scalar on states requires two routes to one state to carry equal terms, and eight of eight live criteria, on 49,649 modification loops and 35,659 deferral loops over 2,942,295 loans

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

## B9 — the ETF creation triangle: a scalar price on the three positions predicts a loop sum of zero; eleven registered predictions, and the two that were designed so they could lose

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

**One test in this stage was built so that it could lose, and it returned the other branch.** The
gate-speed test predicted the share of zero-change days would rise under stress;
it fell in ten of eleven. That is not a failure to report quietly. **It is the
only reading here that a competing account would have got wrong**, and what it
shows is that this carrier's hole is a contractual membership rather than a
collateral threshold: **a breathing hole moves with prices and a contract does
not**, and the test was aimed at the one that does not move.

**The general lesson the stage states about itself**: a shape is cheap. A
prediction has discriminating power because a competing account gets it wrong,
not because a competing account also gets it right. **A rate is a shape; a sign
is not.** The converse is not a lesson and does not follow: a competing account
also getting it right is overlap, and overlap is what a more general account owes
the account it generalises. **What would count against this one is a reading the
rival gets right and it gets wrong, and no such reading has been produced.**

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

**Two carriers were screened out on paper before this one, before any data was bought.** The
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

## A15 — which of these phenomena are transcribed, and which fall out

`rounds=300` `f2i=30` `150 rows in two batches` `two rulers read off disk`

**10/10 criteria passed. Closed.** Three phenomena that look like three
questions share one discriminant: remove the absorbing wall and see whether the
phenomenon is still there. `SubsistenceSpec.mode` is the instrument, with `exit`
carrying the wall and `drawdown` not, and nothing else differing.

**The stage cost 80 runs.** The main grid needed none: A12's two records are it,
630 rows each at seed 0, carrying the four top-share fields because those were
added to A12 for this stage. Both rulers are disk reads as well, one of A12's
record and one of A11's two.

**A transcribed switch does no work in forty-four cells of forty-five and full
scale in the forty-fifth.** Flipping `reversible` alone moves the closing Gini
by at most 0.000472 everywhere except at `f2i=30, e=0`, where it moves 0.271975.
On that cell the arm with the return enabled lands back on the no-wall arm to
within 0.0005. The amplifier between them is the issuance rule, which is a
stabiliser: a permanent collapse in production-layer inflow makes the authority
issue continuously, and the claim stock ends 22.7 times its opening rather than
1.03 times.

**Whether the return catches is bistable.** Across twenty repetitions the closing
starved count under the returning arm takes one of two values and nothing
between: four cells at 75 to 78 and sixteen at 151 to 164. The money stock
splits the same way, four cells at 1.030 to 1.123 against sixteen at 14.152 to
23.033, an empty band of 12.6 times. Which basin a run lands in is set by the
graph draw. More financial-to-intermediate edges make the catching basin
reachable at all, at 4 of 10 against 0 of 10.

**The cascade is not what the wall creates; permanence is.** On the complete
graph at a floor of 1.00 both exit rules put all two hundred nodes below the
line. Under `drawdown` all two hundred come back and under `exit` none do. On
the stratified graph the two rules leave nearly the same count below the line,
183 to 187 against 179 to 182, and neither returns.

**The wage level scars, and a rescue that catches recovers two thirds of it.**
With the derived-demand elasticity at zero the bill is constant by definition
and forty of forty rows read exactly 1.0000, which is the control reading its
forced value. At 0.5 the closing bill sits 26.2 to 29.5 per cent below its
opening in every one of ten cells and does not return. On the one cell where the
return catches, the loss falls from 0.2913 to 0.0988, which is 66.1 per cent of
it taken back. The bill is still climbing at three hundred rounds, so the
residual is a reading at that horizon and not a limit.

**The three inequality measures diverge on a graph draw, not on a mechanism.**
At the registered floor of 0.20 they never diverge, in 1,260 arm-cells across
two carrier sizes: the Gini rising implies all three rise in 344 of 344 cells
and the top percentile falling implies all three fall in 266 of 266. At a floor
of 0.05 ten of A12's fourteen arms produce the divergence, all fifteen hits land
on one seed, and the arm with no floor at all is among them with zero
departures. The four arms that produce nothing are the three carrying a fiscal
transfer and the one combining the exit floor with the write-off.

| | criterion | detail |
|---|---|---|
| PASS | A15-1 one grid, imported not restated | grid, carrier and arm table taken from A12's module by identity and matched against its record: nine edge counts, five elasticities, fourteen arms |
| PASS | A15-2 ruler one: a transcribed switch that does no work | 45 cells; `reversible` alone gives a closing-Gini gap of max 0.271975, median 0.000000; `cut_payroll` alone max 0.344037, median 0.300944. The expectation of a null reading is what the per-cell print refuted |
| PASS | A15-2b does the one cell survive four more seeds | seed 0 reproduces A12's record on 16 of 16 shared cells. Catch rate 3 of 5 at `f2i=30, e=0`, 1 of 5 at `e=0.5`, 0 of 10 at `f2i=20`. The catches sit in a second cluster with an empty band of 12.6 times |
| PASS | A15-3 ruler two: a cascade nobody wrote | complete graph at 1.00: both rules peak at 200 of 200, `exit` closes at 200 and `drawdown` at 0. Stratified: 183–187 against 179–182, neither returning |
| PASS | A15-4 do the three measures ever go three ways | at floor 0.20, zero in 1,260 arm-cells, and the target's own pair, the top percentile falling with the Gini rising, is zero there too |
| PASS | A15-4b the question at the depth where the shape is | at floor 0.05, 10 of 14 arms produce it, every hit on one seed, and the arm with no floor is among them at zero departures |
| PASS | A15-5 which switches every producing subset shares | nothing produced it at the registered depth, so there was no intersection to take |
| PASS | A15-5b which switches every producing arm shares | the intersection is empty and must be, since an arm with no mechanisms is in the set. The informative set is the suppressors: three of the four carry a fiscal transfer |
| PASS | A15-6 how many nodes each top share averages over | 2 and 20 nodes at 200, 10 and 100 at 1000 |
| PASS | A15-7 does the wage level come back | control reads exactly 1.0000 at forty of forty rows with the elasticity at zero; at 0.5 the closing bill is 26.2–29.5 per cent down in ten of ten cells, and 66.1 per cent of the loss is recovered on the one cell where the return catches |


## A16 — a bilateral obligation on the highest-degree nodes, and where the composition effect lives

`rounds=300` `seeds=5` `f2i=30` `e=0.5` `380 rows + a 160-row floor scan`

**6/6 criteria passed on the grid and 1/1 on the floor scan.** This model has no
liabilities anywhere else: no receivables, no borrowing, claims conserved
through every exit, and it still produces a cascade. So balance-sheet
interconnection, which the interbank literature derives cascades from, and real
input dependence, which the production-network literature derives them from, are
each sufficient for a cascade here and neither is necessary. This stage adds one
liability and asks what it changes.

**The obligation is a stream and not a balance.** The first form was a principal
amortising over a term, and at a principal of 0.9 with a ten-round term the
whole thing was 48 claims against 400,000 of flow, gone by round ten, and every
reading came back equal to the arm with the switch off. A continuing rate is
also what Volume One names: mortgage, rent, tax and interest are claims that
keep arriving.

**The complete graph is out, on two counts each sufficient.** In-degree there
takes exactly one value, so "the highest-degree nodes" is not a defined set and
the selection falls through to index order. And the one reading that moved there
is an identity: the closing starved count is `nodes - hubs` at every hub count,
and the survivors are the hub set, because they collect from everyone else. On
the stratified carrier the survivors are never the hub set, in 0 of 380 runs.

**The cascade does become a function of the debt structure, and the slope is
flat.** Against the control at the same cell, the closing starved count moves by
single digits on a base of 76 to 154: `debtor` monotonically down to -9 at the
highest rate, `creditor` both ways from -4 to +6, `mutual` smallest. The
sentence this supports is that the cascade size is a function of the debt
structure, not that debt changes it appreciably.

**The 1929 shape appears, and the debt is not what produces it.** The three
concentration measures go three ways in 21 of 380 rows, all of them at a floor
of 0.05, and one of the twenty-one is the arm with the obligation off. The two
floor depths differ sharply in what the departing nodes carry: at 0.05 they hold
**0.3 per cent** of the closing stock and at 0.20 they freeze holding **94 per
cent**.

**What that difference is not is the cause, and A15 is where that was settled.**
Every arm on this grid carries the floor, including the one named for having no
obligation, so nothing here can turn the floor off. A15 ran A12's fourteen arms
at the shallow depth, one of which has no floor at all, and **that arm produces
the same shape with zero departures**, to within a digit of the arms that have
one. So the pattern is the baseline drift of a particular graph draw rather than
a composition effect, and what the mechanisms do to it is destroy it: the four
arms that do not produce it are the three carrying a fiscal transfer and the one
combining the exit floor with the write-off, all of which move the closing Gini
far enough to bury it.

**The boundary is between 0.125 and 0.150, and it is a jump.** Across 160 cells
the frozen share takes two values and nothing between: 105 cells at or below
0.0086 and 55 at or above 0.9339, an empty band of 108 times. At 0.150 both
regimes occur at the same depth on different draws. Within the shallow regime
the shape lands on the same four cells in twenty at every depth, so which draw
produces it is a property of the graph and the depth only decides which regime.

**Orientation does not move the boundary.** All four arms cross at the same
place. What it moves is the frequency inside the shallow regime, and that effect
is one to two seeds wide: on independent seeds `debtor` is 3 of 5 and the others
1 of 5, against a grid reading of 13 of 30 against 1 of 30 that came from six
rate settings sharing one set of seeds.

| | criterion | detail |
|---|---|---|
| PASS | A16-1 the control arm is A12's floor arm | 6 of 6 fields identical to `a12_mechanisms.json`: closing Gini, `m_ratio`, support ratio, starved, top 1% and top 10% |
| PASS | A16-2 the hub set, and how much of it is degree | in-degree takes 32 distinct values; the cut is 49 against 47 at two hubs and 33 against 32 at ten, neither a tie. The failing state is one distinct in-degree, which is the complete graph's |
| PASS | A16-6 do the survivors turn out to be the hub set | 0 of 380 runs, and 0 runs where the survivor count matches the hub count without the sets matching |
| PASS | A16-4 does the cascade become a function of the debt | all three orientations move it; ranges against the control at the same cell given above |
| PASS | A16-5 every cell, and the thinnest three | printed per cell rather than averaged, with the three cells where the obligation moved least named |
| PASS | A16-7 does the obligation add a second concentration process | **no.** 21 of 380 rows carry the 1929 shape, all at a floor of 0.05, and the control arm is among them |
| PASS | A16-8 where along the floor the composition effect lives | the boundary sits between 0.125 and 0.150; the frozen share is bimodal with an empty band of 108 times; four hits in twenty at every shallow depth, the same four cells |


## A17 — edges cut out of the graph, rather than a node ceasing to trade

`rounds=300` `seeds=5` `f2i=30` `e=0.5` `floor off on every arm` `315 rows`

**6/6 criteria passed.** Every rule in this model reads the node's own state,
and the exit branch does not touch the adjacency: it flips a membership flag,
the routes that pointed at the node are masked for that round, and the potential
graph is what it was at construction. So a trading relationship ending is not
something the model could express. This stage adds that and asks whether a
phase transition in the graph produces a cascade on its own.

**The floor is off on every arm, and two measurements are why.** With the cut
trigger at the floor the nodes whose edges are cut are exactly the nodes that
have already left, 180 stranded against 180 departed, the same set, and the flow
identical to the control's. Raising the trigger above the floor does not help
either, because at the registered floor the cascade already takes 180 of 200.
So the floor comes off and the cut threshold is the only one in the model.

**Removing edges does not produce a cascade, either at random or aimed at the
hubs.** Cutting seven tenths of the edges at random leaves total flow at 0.99 of
the control's while breaking the graph into 13 to 19 components; aimed at the
hubs it leaves flow at 0.94 and **the graph in one piece**. The literature's
paired result, robust to random link removal and fragile to targeted removal,
does not reproduce, and the reason is the object: that result removes *nodes*,
taking every edge at once, and a hub here has so many edges that a seven-tenths
cut of the hub-incident ones leaves it connected.

**Removing nodes does produce one, and this repository has measured that many
times: it is the subsistence floor.** So the three read together: taking nodes
out cascades, taking edges out at random does not, taking edges out at the hubs
does not. The graph's phase transition is not what does it.

**The targeted arm's stranded set is fixed by the construction, and the
artefact detector caught it.** The same node ids at all five seeds, intersection
full, every one of them with an opening out-degree of 81 against 3 to 18 for the
rest. Those thirty are the wage payers, whose out-degree is set when the graph is
built rather than drawn, so a rule that ranks on degree always reaches them
first. **That arm therefore measures cutting the payroll channel's edges first**,
which is a named intervention its readings hold for, and not the generic
targeting of the literature.

**Who does the cutting is the mechanism, by three orders of magnitude.** At the
same trigger and share, a stressed node cutting its own out-edges leaves flow at
0.0199 of the control's, while its counterparties cutting the edges that point
at it leaves flow at **32.9 times** the control's. Withdrawal by the weak and
withdrawal from the weak are different objects here, not one object named twice.
The second is intelligible: cutting the edges into the weakest redirects flow to
the better-connected, who have more onward edges and a higher propensity, so
circulation speeds up among them until the trigger rises far enough that
everyone counts as weak, at which point the same rule leaves 0.0097.

**A resemblance worth naming, and it is a pointer rather than a result.** Money
leaving weaker institutions and concentrating in stronger ones, with the
aggregate at the core rising while the periphery empties, is the documented
shape of a flight to quality: deposits moved from smaller to larger institutions
in March 2023, and the earlier leg of the same pattern is visible in the deposit
surge at the institutions that later failed. **The mapping is not tested here
and this stage does not claim it.** What is measured is that the sign and the
magnitude of the effect depend on which side does the cutting, which is the part
someone doing the empirical work would need.

**Sixty-two cells run on under a twentieth of the control's flow**, and the
support statistic there is a ratio of two small numbers rather than a reading.
It takes the values 0.0, 0.3706 and 0.4246 on them against the control's 1.0338,
and those numbers are not to be read in either direction.

| | criterion | detail |
|---|---|---|
| PASS | A17-1 the control arm is A12's off arm | 5 of 5 fields identical to `a12_mechanisms.json` |
| PASS | A17-2 one threshold, two responses, two readings | identical on 0 of 5 seeds at both settings. At the mild one the same threshold strands 25 through the edge rule against 195 departing through the floor, and the floor arm's flow is thirty times the edge arm's |
| PASS | A17-4 what the graph does with no trigger anywhere | random and hub-targeted, nine shares each, given above. Neither collapses |
| PASS | A17-5 the two triggered arms against each other | 0.0199 against 32.9 at the same trigger and share |
| PASS | A17-7 is the stranded set the low-degree tail | it is not: the stranded carry a higher mean opening out-degree than the kept, and on the targeted arm they are a construction-fixed set |
| PASS | A17-8 support readings taken on near-zero flow | 62 cells named, and their support numbers refused |

## A18 — what the policy switches do to the time path

`rounds=300` `seeds=5` `two floor depths` `120 rows` `no mechanism added`

**6/6 criteria passed.** Every station before this one reads a closing value: a
closing Gini, a closing count below the line, a mean over the last twenty-five
rounds. None reads a trajectory, and a claim of the form "it looks steady and
then releases something larger" is only falsifiable on one. Four switches are
read here as paths, all four already in the model, and the code already calls
one of them a political condition rather than a mechanism.

**The count below the line is not one object across the two exit rules**, and
that is the gate this stage runs first. Under `exit` it is a running total that
never falls, monotone in 12 of 12 cells; under `drawdown` it is re-read every
round, monotone in 6 of 12. So the readings are taken on the claim-to-resource
ratio and on total flow, which mean the same thing under both.

**Forbearance does not defer the problem here, it prevents it.** At the deeper
floor the arm that lets nodes go ends with a claim stock **17.45 times** its
opening; the arm that keeps everyone in the market ends at **1.0005**. The
predicted shape, quiet for a while and then a larger release, needs both a later
start and a larger jump; the forbearance arm starts twelve rounds later and its
largest single-round jump is **smaller** than the control's, so it has one of the
two. The un-forborne arm's largest jump lands at **round 5 at every seed** and
measures `0.069` to `0.081`. The forbearance arm has **no jump to read**: two of
its five seeds never leave their opening value by more than floating tolerance
at all, and the three that do move by `0.0003` to `0.0005`, three orders below
the control. **This is not an early break against a slow drift, it is a break
against nothing happening.**

**The accumulation is the issuance rule's, not the write-off's.** With the
authority switched off, **all twelve policy combinations end at exactly
1.0000**. With it on, recognising losses cuts the ratio from 17.45 to 4.94, and
refilling what was destroyed barely moves it again, to 5.07. This is the other
half of what A15 found: a permanent collapse in production-layer inflow makes
the stabiliser issue continuously, and keeping nodes in the market is what stops
the collapse that starts it.

**At the shallow floor there is nothing to read**, and that is reported rather
than filled in: recognising losses and not recognising them return identical
numbers, because the write-off never fires there and the claims destroyed in the
closing round are zero on every arm.

**One correspondence was written down before the run and is answered by the B
arm below.** Forbearance is dangerous in the world because the forborne party
keeps receiving new credit. A node here eats its own stock until it has none and
nobody feeds it. The readings above hold for forbearance without resupply;
`A18_B` is the other kind.

**A field in this record was measured and corrected on 2026-08-26.** The round
at which each series makes its largest single-round move was taken as
`argmax` of the absolute differences, with no guard on the size of that move.
Under forbearance `M/R` is flat for all three hundred rounds, its largest change
is one unit in the last place, and eight to eleven rounds tie at exactly that
value, so the field indexed into a set of ties and reproduced nothing. It now
reports no jump when the series never moves. **The reading it supported has been
withdrawn and replaced above**; nothing else in this record changed, and
`docs/MEASUREMENT.md` failure mode 46 carries the shape.

| | criterion | detail |
|---|---|---|
| PASS | A18-1 the control policy is A12's floor arm | `M/R` over its opening 17.56787 against A12's 17.56787, closing count below the line 151 against 151 |
| PASS | A18-2 the count below the line is not one object | monotone in 12 of 12 under `exit` and 6 of 12 under `drawdown`, which is why the main readings are taken elsewhere |
| PASS | A18-6 does not recognising a loss accumulate anything | at the shallow floor the two write-off settings are identical and nothing is destroyed; at the deeper one 17.57 against 4.92 |
| PASS | A18-3 quiet then release, a slow grind, or neither | neither, and better than neither: 1.0005 against 17.45, with a later start and no readable jump at all on two of five seeds |
| PASS | A18-4 the paths, sampled | five sample rounds per series per cell, printed rather than summarised |
| PASS | A18-5 every cell, and the three most extreme | 110 cells against a control at the same floor and seed |


## A18_B — forbearance with somebody paying for it, and where that money comes from

`rounds=300` `seeds=5` `three floor depths` `three funding routes` `435 rows` `150 boundary cells`

**8/8 criteria passed.** The A arm above measured forbearance with nobody
feeding the forborne party and said so before it ran. This arm supplies the
feeder: a node below the subsistence line is topped up by whoever already lends
to it, along the edges that are already there, in the direction they already
point. **No edge is introduced and nothing is created by default**, so the
conservation assertion stays a criterion rather than something to exempt.

**The interesting quantity is not the node being kept alive, it is the ones
paying.** Across the thirty-nine cells where money moved, the lenders hand over
a gross amount and end holding between **0.0016% and 0.44%** of it less than
they would have. **The rescue is a loop**: what they pay, the rescued node
spends, and the graph carries it back. Not one cell has them better off.

**The constraint they are under is real and this record now says so.** The model
computed the shortfall the rescue asked for and recorded only the part it could
fund; both are recorded from this run. The lenders cover **87%** of what is
asked at the shallow floor and **27%** at the deepest floor with the largest
rate. **They cannot fund three quarters of it.** That is what makes the funding
routes below a measurement rather than an identity.

**Three routes, because "where does a rescue's money come from" has three
answers and they are not three settings of one dial.** The lender's own book,
new claims from outside the graph credited to the lenders one round later, or a
levy per head on everyone still trading. The last two give the money back to
exactly the nodes it came from and differ only in where it is found.

| route | holds fewest below the line | claim stock at close |
|---|---|---|
| `creditors` | 4 of 45 cells | **1.000 – 1.022** |
| `issuance` | **23 of 45** | **1.002 – 7.531** |
| `levy` | 0 of 45 | **1.000 – 1.006** |

They agree on the count in the remaining 18. **The route that saves the most
bought them**, and the claim stock is the price; the two conservative routes end
within 2% of where they started.

**What survives when the recapitalised nodes stop passing it on.** The framework
already has the object for this: `SpendRule` states that the retention rate is
`1 − propensity` and reads as the rate of exit from cross-layer circulation, and
the propensities are per node. So a recapitalised node that retains is a node
whose propensity has been scaled. **The rescue itself is untouched**, because it
is served before discretionary spending: a retaining node goes on funding
whatever it is asked for and stops doing everything else.

The count below the line turns on **27 of 45 cells**, first turning at `0.5`,
`0.9` or `1.0` depending on how large the rescue is relative to the need. At the
deeper floor with a rescue that is not marginal, the count is **flat from `0.00`
to `0.95` and moves only at total withdrawal**, while `M/R` climbs from about 5
to about 32 over the same span. **The benefit survives almost any amount of
retention. The price is paid throughout**, at **1.0 to 26.1 times** the claim
stock at no retention.

**At total retention the arm produces the one shape this repository had not
produced before**: claims created that do not circulate. At the shallow floor
with the smallest rate, the claim stock closes at **30.9 times** its opening
while total flow closes at **0.893** of the control's, the count below the line
does not move, and **the only flow that grows is lending to the nodes below the
line**, from 207 to 772. Decomposed against an opening claim stock of 100: the
injection itself is **7.7×** and the authority's own issuance rule, reacting to
the inflow collapse the injection caused, is **22.2×**. **The reaction is 2.89
times the intervention**, and it is A15's amplifier reached from a new direction.

**One cell of 150 sits on a boundary and the record names it.** Perturbing every
opening holding by `1e-10`, a difference of the order that separates one BLAS
build's summation order from another's, moves the count below the line in
exactly one cell: floor `0.50`, rate `1.0`, `creditors`, seed 1, from 153 to
132. A single unit in the last place moves nothing, three of the five seeds hold
to `1e-6`, and **that one cell is the one that disagreed when this record was
re-run on a second machine.** There is no exemption list for it; the scan is
recorded in full and `docs/MEASUREMENT.md` failure mode 48 carries the shape.

**The `exit` arm is printed and carries no criterion**, because a node out of
the market receives and does not spend, so claims sent to it are frozen by
construction. It is worth printing anyway: at the deepest floor the same rescue
raises the count below the line from **157.6 to 174.2**, cuts the effective
support from **29.90 to 20.32**, and leaves the paying nodes **better off by
26.34** rather than worse. **The same money, the same edges, and the sign turns
on whether the recipient is still trading.**

### The resemblance to Japan, stated as a resemblance

**No parameter in this model comes from Japanese data.** The carrier is the
registered one and the switches are the framework's own. What follows was found
after the fact and is offered as a pointer for someone who wants to test the
mapping, which this stage does not.

| | Japan, 2001–06 | this stage, floor 0.20, rate 1.0, full retention |
|---|---|---|
| bank lending | **−10%** | total flow **−10.7%** |
| response over intervention | recapitalisation ¥8.6tn, monetary base +¥37tn, **≈4.3×** | injection 7.7×, issuance rule 22.2×, **2.89×** |
| lending to the weakest | sustained or rising | **+273%** |
| created money entering circulation | base **+70%**, M2 trajectory unchanged | claims **×30.9**, flow **×0.893** |
| the weak | failures suppressed | count below the line barely moves |
| prices | mild deflation | **no price level exists here** |

**The load-bearing part is the mechanism rather than the numbers, and the C arm
below narrows which mechanism.** The standard account of why that episode's
monetary expansion did not reach the money supply is that the purchases were
made from banks rather than from non-banks, so the new claims stopped where they
landed. **Landing them somewhere else is now an arm, and it changes almost
nothing**: over 135 paired cells the count below the line is identical in 105
and differs by one node in 23. What the claims stopping turns on here is
retention, not the landing point. The accounting form of that account, which
rests on reserves and deposits being different aggregates, has no counterpart in
a model with one kind of claim and is not tested either way.

**The landing point is not inert everywhere, and where it is not is
informative.** It matters in one corner of the C arm's grid, at zero wage
elasticity, and its influence falls monotonically as the wage channel
strengthens: the count differs in 14 of 45 pairs at elasticity 0 with a largest
gap of 11 nodes, 10 of 45 and a gap of 2 at 0.5, and 6 of 45 and a gap of 1 at
1.0. **Where the claims land matters only when there is no redistribution
channel to carry them away from where they landed.**

**Two scope statements, and a third that A18_E closed.** The cell was selected
from a scan and needs retention at its maximum; at `0.9` the flow is **1.084**
of the control and the direction is the other way. There is no price level, so
the cause of deflation is reproducible here and deflation is not.

**The third was that retaining and holding something outside the trading system
were one state, because there was no outside.** There is one now. A18_E
separates them, and with it the signature this pointer reaches for by selecting
an extreme retention cell is produced directly and as a continuous dial: the
stock rises **22 times** while the circulating half falls to **0.15** of its
opening. **A reading that needed a corner of the grid is now a reading of a
parameter.**

| | criterion | detail |
|---|---|---|
| PASS | A18_B1 the A arm reproduces its record | 120 recorded rows re-run through the edited code, 0 fields differ |
| PASS | A18_B2 what the rescue does to the count below the line | where money moved the count never rose; by route, 5 of 6 down on each |
| PASS | A18_B3 gross paid against net cost to the payers | net over gross `0.0016%` to `0.44%`, 0 cells with the payers better off |
| PASS | A18_B4 is more rescue always less distress | monotone in some cells and not others; the non-monotone cells are named |
| PASS | A18_B7 where the rescue's money comes from | 45 cells with all three routes, 18 agreeing; claim stock 1.000–1.022, 1.002–7.531, 1.000–1.006 |
| PASS | A18_B8 what survives when the money is retained | the count turns on 27 of 45 cells at levels 0.5, 0.9 or 1.0; price 1.0 to 26.1 times |
| PASS | A18_B6 which readings sit on a boundary | 1 of 150 cells moves under a `1e-10` perturbation, named |
| PASS | A18_B5 under exit, where the rescue money ends up | printed, not judged: the arm reports its own construction |


## A18_C — where the created claims land, and whether that is what decides anything

`rounds=300` `seeds=5` `three floor depths` `three rates` `two landing points` `wage elasticity swept` `360 rows`

**5/5 criteria passed.** The B arm reported that created claims can fail to
circulate and attributed it to retention, having created them in one place only.
**This arm exists to find out whether the place was the operative part.** The
same amount is created for the same reason and arrives either on the nodes that
funded the rescue or spread evenly over every node still trading; nothing else
differs, which is what A18_C1 checks before anything is read.

**Over 135 paired cells the landing point changes the count below the line in
30, and 23 of those by a single node in both directions.** That is the size of
the discrete jitter this carrier already carries, measured in A18_B6. **In 105
pairs there is no difference at all.**

**The five pairs that differ by more than two nodes are one cell of the grid,
at every seed.** Floor `0.50`, rate `4.0`, wage elasticity `0.0`: landing on the
lenders leaves 3, 4, 5, 9 and 11 more nodes below the line than landing on
everyone, in the same direction at all five seeds, with total flow 16 to 17 per
cent lower.

**And the effect is monotone in the wage channel's strength.**

| wage elasticity | pairs whose count differs | largest gap |
|---|---|---|
| 0.0 | 14 of 45 | **11** |
| 0.5 | 10 of 45 | 2 |
| 1.0 | 6 of 45 | **1** |

**So where new claims land matters only when there is nothing to redistribute
them.** With a live wage channel the graph carries them away from wherever they
arrived and the landing point does no work; with the channel dead it is the only
thing moving them and the landing point becomes visible.

**This narrows the B arm's reading rather than confirming it.** "The claims
stopped where they landed" is not what the model says. What it says is that the
claims stopped because whoever received them did not pass them on, and that
where they arrived is second order and appears only when the redistribution
channel is off as well.

**The wage channel's own effect on the count is not monotone**, and that is
reported rather than smoothed: it moves the count in 45 of 90 cells, and it
moves it both ways. At floor `0.20` with rate `1.0` on the lender arm the count
runs `75, 150, 150` across the three elasticities, so raising it doubles the
count; at floor `0.50` with rate `2.0` it runs `103, 75, 75`, so raising it
halves it.

**The full-retention rows are printed and carry no criterion.** Under `uniform`
every node still trading is a recipient, so retention there withdraws the whole
economy rather than the recapitalised set, and the two are not the same
experiment. They are worth printing: at three of five seeds the two landing
points are identical, and at the other two the uniform arm's flow falls to
between 1,013 and 2,249 against roughly 20,200 on the lender arm. **Another
bimodal pair with nothing between**, which is now the fifth on this carrier.

| | criterion | detail |
|---|---|---|
| PASS | A18_C1 the two arms differ in the landing point and nothing else | recipients 1 to 52 under lenders against 200 under uniform; 19 pairs inert because the rescue never fired, named |
| PASS | A18_C2 does the landing point change the count | second state: 30 of 135 pairs, 23 of them by one node in both directions, and the five larger ones are one cell at every seed |
| PASS | A18_C3 the continuous readings across the pair | median relative gap: flow 1.15%, `M/R` 1.75%, support 0.058%, Gini 0.0045%, rescue paid 9.09% |
| PASS | A18_C4 does the wage channel's strength change the count | second state: 45 of 90 cells, and not in one direction |
| PASS | A18_C5 full retention under each landing point | printed, not judged, and why |


## A18_D — the rescue as a loan rather than a gift

`rounds=300` `seeds=5` `three floor depths` `five repayment rates` `330 rows`

**6/6 criteria passed.** Every earlier arm's rescue was a gift: the node below
the line received and never repaid. That made three things unreachable at once
— a debt overhang, a rescue that leaves its recipient worse off, and any
distinction between a bridge and a trap. Here the rescued node owes what it
received, to the nodes that funded it, and **services that debt before it
spends anything of its own**, which is the seniority Volume One gives to
mortgage, rent, tax and interest and the same ordering the hub obligation
already carries.

**The book closes exactly.** Lent, less repaid, less outstanding, is **zero to
the last bit in all 330 rows**. That check is not redundant with the round's
conservation assertion: the assertion watches the holdings total and this
watches the ledger, and a repayment rule can be wrong in the second while the
first is satisfied.

**A repayable rescue does more with the same balance sheet.** The lenders' stock
is finite and the rescue is capped by it, so a rescue that comes back can be
made again: over 180 paired comparisons the amount of rescue delivered exceeds
the gift arm's in **97**, with a median ratio of **1.34** and a maximum of
**3.00**. The count below the line falls in 93 comparisons, holds in 77, and
**rises in 10**.

**The best repayment rate is almost never the largest one.** Of 45 cells it sits
strictly inside the grid in **24**, at zero in 19, and at the largest rate in
**2**. The counts show what that means:

| cell, counts at repayment 0 / 0.05 / 0.20 / 0.50 / 1.00 | |
|---|---|
| floor 0.50, rate 1.0, seed 0 | `139, 111, 115, 118, `**`127`** |
| floor 0.20, rate 1.0, seed 3 | `153, 120, 123, `**`117`**`, 123` |
| floor 0.20, rate 1.0, seed 4 | `152, `**`113`**`, 117, 121, 121` |

**Repaying faster is worse than repaying slowly, past a point that is inside the
grid rather than at its edge.** The first row is the sharpest: five per cent a
round leaves 111 below the line and repaying the whole balance leaves 127, which
is worse by sixteen nodes and still better than never repaying at all.

**Whether the balance clears depends on how deep the floor is.** The share of
everything lent that is still outstanding at close has a median of **4.5%** at
floor 0.20 and **19.0%** at floor 0.50, and the ranges do not overlap at their
middles. **At the deepest floor a fifth of the rescue is structurally
unrepayable**, and it stays that way at every repayment rate on the grid.

**One branch is reported as never firing, and the reason is two different
things.** A debtor that owes while every one of its creditors has left
circulation pays nothing and its arrears stand. That fired in **0 of 90** exit
rows and **0 of 240** drawdown rows. Under `drawdown` it *cannot* fire, because
`_alive` is set false only by the exit rule and every creditor is therefore live
forever; under `exit` it can, and does not, **because the creditors are by
construction the solvent in-neighbours of whoever was below the line and are
therefore the last nodes to leave.** A count of zero here is a statement about
who lends, not about how many rows were run.

**The cell A18_B named as closest to a real episode, now with the rescue
repayable**, printed and not judged: the count below the line falls from
**121.2** to **109.0**, the rescue delivered rises from 4,128 to 5,683, the
outstanding balance falls from 4,128 to 1,333, and `M/R` rises from **42.1** to
**57.6**. **More is rescued and more is created**, because more lending draws
more recapitalisation behind it.

### A second resemblance, and it is a thin one

**No parameter here comes from any episode**, and this pointer is weaker than
the one on A18_B. It is stated with its weakness because the arithmetic that
would have made it strong came out with the wrong sign.

**What matches is one direction.** Repaying faster is worse than repaying slowly
past a point inside the grid, which is the shape of the argument that
front-loaded consolidation costs more than gradual consolidation. The recorded
direction on the other side is that countries expected to improve their
structural balance performed worse than forecast, and that Greece's debt ratio
rose from roughly 130 per cent of output at end-2009 to roughly 180 by 2016
despite the consolidation.

**What does not match is the magnitude, and it does not match in sign.** The
comparable quantity is a multiplier: output per unit of consolidation. Measured
here as the change in total flow per unit repaid, it runs **+0.56 to +1.50**.
**Repaying raises flow in this model.** A consolidation multiplier is negative
in the same units.

**The reason was structural, and A18_E removed it.** This stage's creditors are
inside the graph, so what a debtor repays is received by somebody who lends it
again; the defining feature of the episode is that the payments left the
economy, and there was no outside here for them to leave to. **Two independent
correspondences had named the same missing piece**, this one and the Japan
pointer above, which is a statement about the model rather than about either
episode. A18_E supplies it, and **the sign turns**:

| creditors parking, per round | flow per unit repaid |
|---|---|
| none | **+1.08 to +1.50** |
| 0.20 | **−0.58 to −0.37** |
| 0.50 | +0.24 to +0.49 |

**The `+1.5` above is not wrong; it is the answer for a creditor who lends the
payment out again.** With the payment leaving the trading system the same
measurement is negative, and the estimates the argument is usually conducted
with are of order one. **Same sign, same order, smaller here.** The return to
positive at the highest parking rate is reported rather than smoothed: by then
so little circulates that the repayment flow is itself a large share of what is
left.

| | criterion | detail |
|---|---|---|
| PASS | A18_D1 the ledger closes | largest absolute residual 0 over 330 rows |
| PASS | A18_D2 a loan against a gift | 93 down, 77 level, 10 up; rescue delivered exceeds the gift arm's in 97 of 180, median ratio 1.34 |
| PASS | A18_D3 where the best repayment rate sits | strictly inside in 24 of 45 cells, at zero in 19, at the largest in 2 |
| PASS | A18_D4 does the balance clear | outstanding over lent, median 4.5% at floor 0.20 and 19.0% at floor 0.50 |
| PASS | A18_D5 a debtor whose creditors have left | 0 of 90 exit rows and 0 of 240 drawdown rows, and the two reasons are different |
| PASS | A18_D6 the retained-issuance cell, with the rescue repayable | printed, not judged |


## A18_E — a claim that exists, is owned, and is not in the money that circulates

`rounds=300` `seeds=5` `three floor depths` `four parking rates` `430 rows`

**5/5 criteria passed.** Two separate correspondences on this station ended on
the same limit. The first said that retaining and holding something outside the
trading system are one state here; the second said that a repayment cannot leave
the economy because the creditor is a node in it. **Both are the same missing
piece: the graph had no boundary.** This arm supplies one. A share of a node's
holdings moves out of the accounts the flow can route through, and is not
destroyed.

**The framework had the quantity and not the destination.** `SpendRule` states
that the retention rate reads as the rate of exit from cross-layer circulation
rather than as hoarding in the literal sense. Exit needs somewhere to go, and
until now the only somewhere was staying put.

**It is not retention under another name, and that is the first criterion.**
Under every retention setting the parked stock is zero in **90 of 90** cells,
because a retaining node's claims are still on its account; under parking it is
above zero in **245 of 245**. The difference is what an obligation can reach: a
retaining node still owes and still pays, so retention is pierced, and parked
claims are not there to be taken.

**The stock and the circulating half separate, and in every cell the two
mechanisms move the second in opposite directions.**

| parking rate | stock | circulating | parked | count below | flow |
|---|---|---|---|---|---|
| none | 185.1 | **185.1** | 0 | 86.7 | 36,794 |
| 0.05 | 1,925.9 | **171.3** | 1,754.6 | 104.1 | 34,732 |
| 0.20 | 2,725.0 | **56.9** | 2,668.1 | 112.3 | 14,856 |
| 0.50 | 4,127.0 | **28.2** | 4,098.8 | 135.0 | 9,188 |

**The stock rises twenty-two times while the money that circulates falls to
0.15 of its opening.** That is a continuous dial rather than a corner of a grid,
and it is the shape both pointers above were reaching for.

**The recorded `M` was already the circulating half and this makes that
visible.** `total_claims` is the row sum of `holdings`, so `M` in this
repository has always meant claims in trading accounts. Parking splits the
stock, `M/R` follows the circulating part, and the rest is carried beside it as
`parked`. The conservation assertion counts both, because those claims still
exist; destroying them is what the write-off does and this is not that.

**Output per unit repaid turns sign with the parking rate.** A18_D measured
that quantity at **+0.56 to +1.50** and that number is the answer for a creditor
who lends the payment out again. Here:

| creditors parking, per round | flow per unit repaid |
|---|---|
| none | **+1.08 to +1.50** |
| 0.20 | **−0.58 to −0.37** |
| 0.50 | +0.24 to +0.49 |

**One switch separates a payment that recirculates from a payment that leaves**,
and nothing else in the cell differs. The return to positive at the highest rate
is reported and not smoothed: by then so little circulates that the repayment
flow is itself a large share of what remains.

**Who parks changes the size of the damage**, printed and not judged because the
three sets are different sizes and part of any difference is that:

| who parks | circulating | count below | flow |
|---|---|---|---|
| the recapitalised set | **234.3** | **106.2** | 47,334 |
| the financial layer | 100.6 | 110.6 | 26,665 |
| everyone | **55.5** | **119.8** | 17,539 |

**Rule 19 for this switch was carried to a full sweep of what it can reach.**
Twenty-two of the twenty-six stages import the module that changed, and the
four that cannot were named and excluded rather than assumed. Of the records
re-derived, **twenty came back identical field for field and one differed**, in
380 places that are all the same event: a field that had not existed appearing.
**No recorded value moved.** The one differing record also turned out to have
been older than its own code in the baseline, which the comparison found on its
way past.

| | criterion | detail |
|---|---|---|
| PASS | A18_E1 a stock that does not circulate | retention parks nothing in 90 of 90; parking parks something in 245 of 245 |
| PASS | A18_E2 the two halves under each mechanism | first state: in every cell the two move the circulating half in opposite directions |
| PASS | A18_E3 how far the circulating half moves | stock ×22 against circulating ×0.15 across the parking grid |
| PASS | A18_E5 output per unit repaid, at each parking rate | first state: positive throughout at 0 and 0.50, negative throughout at 0.20 |
| PASS | A18_E4 who parks | printed, not judged |


## A18_F — who carries a forbearance programme

`rounds=300` `seeds=5` `two floor depths` `two funding routes` `six parking rates` `120 rows`

**3/3 criteria passed.** The same forbearance, the same parking behaviour, and
one thing different: whether the lending is funded from the lenders' own book or
from claims an authority creates and hands them. **Nothing else in the pair
differs**, so a difference in any reading belongs to that.

**The grid is three orders below A18_E's, and the measurement that moved it is
worth stating.** That arm's lowest parking rate leaves **ninety-two per cent** of
the stock parked, so every cell in it reports saturation. The parked share
passes a third at about `0.002`. **A grid whose first rung is past the region of
interest can only report that it is past it.**

**The first criterion publishes a translation table and calibrates nothing.**
The parked share rises with the parking rate in all four series and all four
span a third, so an external figure for how much of a banking system's assets
sit outside the trading system has somewhere to land. **Landing it is not done
here**, and no external number sets any parameter in this repository.

**The table is indexed by rate and horizon together, because the share has no
steady state.** Parking is one way, so the parked stock only accumulates and its
share climbs towards one without settling. A table indexed by the rate alone
would invite a reader to match a figure without matching the second index, and
the second index moves it more than any policy switch does.

| parking rate | share at round 50 | 150 | 299 |
|---|---|---|---|
| 0.001 | 0.033 | 0.101 | **0.187** |
| 0.002 | 0.065 | 0.185 | **0.313** |
| 0.005 | 0.150 | 0.356 | **0.529** |
| 0.010 | 0.259 | 0.524 | **0.690** |
| 0.020 | 0.412 | 0.684 | **0.814** |

**What the table is portable across was measured rather than assumed.** Holding
the parking rate at `0.002` and moving everything else one axis at a time, the
share reads `0.3082` on the registered setting and:

| axis moved | share | against the registered setting |
|---|---|---|
| horizon 150 rounds | 0.1821 | **0.59×** |
| horizon 600 rounds | 0.4713 | **1.53×** |
| the parking set is the recapitalised nodes | 0.1028 | **0.33×** |
| the parking set is everyone | 0.3752 | 1.22× |
| the funding route | 0.3062 | 0.99× |
| the floor depth, either direction | 0.312 / 0.335 | 1.01× / 1.09× |
| the rescue rate, either direction | 0.314 / 0.302 | 1.02× / 0.98× |
| the write-off switched on | 0.3082 | **1.00×** |
| retention at a half | 0.2719 | 0.88× |

**Every policy switch moves it by under a tenth and the write-off not at all.
The two that move it are the horizon and which set parks**, and neither is a
policy. **So the table is portable in the sense that matters and conditional in
two places that have to be stated with it**, which is what indexing it by
horizon does for the first; the second is a modelling choice a reader has to
make before the dial means anything to them.

| floor | parking rate | parked share | flow under issuance ÷ flow under creditors |
|---|---|---|---|
| 0.20 | 0.001 | 0.183 | **1.33** |
| 0.20 | 0.002 | 0.309 | **1.30** |
| 0.20 | 0.020 | 0.819 | 1.37 |
| 0.50 | 0.001 | 0.205 | **4.58** |
| 0.50 | 0.002 | 0.336 | **4.86** |
| 0.50 | 0.020 | 0.826 | 5.10 |

**The deeper the distress, the more the funding route decides.** At the
shallower floor an authority creating the claims buys about thirty per cent more
circulation than making the lenders carry it; at the deeper one it buys four to
five times as much. **The count below the line differs in 48 of 60 pairs.**

**The two routes are non-monotone in the parking rate for different reasons, and
that is the reading rather than the count of cells.** Four of ten cells on the
lenders' route are non-monotone and six of ten on the authority's, which on its
own says nothing; the shapes do. On the lenders' route the count **drifts
upward** as parking rises, `113, 122, 127, 128, 126, 129` at one seed and
`117, 129, 129, 131, 131, 130` at another. On the authority's route it **flips
between two values**, `78, 78, 77, 78, 153, 78` at one seed and
`76, 76, 76, 151, 76, 151` at another. **One is a trend with noise on it and the
other is a knife-edge between two basins**, and this carrier has now shown that
second shape six times.

### The two ends of the axis, as directions only

**This arm was opened because two episodes sit at its ends, and it is written
so that neither is landed on the dial.** At one end an authority creates the
claims and hands them to the lenders; at the other the lenders carry the
programme on their own book while moving assets out of the trading system. **The
axis does not depend on either**, which is why the arm asks about the funding
route rather than about a country: a treatment variable whose value is the name
of one episode has one value in the world, and a station built on it cannot be
run.

**What is measured is a direction**: on the same parking dial, the end where the
lenders carry it circulates less, and the gap widens with the depth of the
distress. **What is not measured, and is not attempted, is where any real
banking system sits on that dial.** A18_F1 exists so that someone with the
figure can place it; placing it is their work and not this stage's.

| | criterion | detail |
|---|---|---|
| PASS | A18_F1 the dial is monotone and spans the region | monotone in 4 of 4 series, and 4 of 4 bracket a parked share of one third |
| PASS | A18_F2 does who carries it change the count | second state: 48 of 60 pairs; flow ratio 1.30–1.44 at the shallower floor and 4.42–5.21 at the deeper |
| PASS | A18_F3 is the count monotone in the parking rate | second state: 4 of 10 and 6 of 10 cells by route, and the two shapes are different |


## B18 — the directional remnant: what a position's one-sidedness leaves in the book

`295 spread contracts` `3,895,656 snapshots` `one trading day` `nothing bought`

**Closed on the instrument's resolution.** The measured quantity is the direct
book's one-sided-absence asymmetry, `A_s = P(no bid) − P(no ask)`, taken at
end-of-event snapshots. The direct book rather than the implied one, because an
implied quote's one-sidedness is fixed by its legs and is the matching engine's
definition rather than a finding.

**The precondition passed and it answers a different question.** It asks whether
`A_s` is identically zero. It is not: quantiles run `p10 0.0004` to
`p90 0.0528`, and the largest contract reads `−0.3893`. **Both of this station's
axes read a sign**, and the question a sign needs is whether one contract's sign
can be estimated at all.

**Absence happens in runs, so the independent unit is the run.** One quote away
for three hundred seconds leaves three hundred correlated snapshots; taking the
3,895,656 snapshots as `n` inflates the degrees of freedom. Counting runs
instead, over the same cache in one pass:

| | |
|---|---|
| absence segments per contract, both sides summed | **p10 2, p50 2, p90 13, max 63** |
| `\|A_s\| >= 1 se` | **4 of 295** |
| `\|A_s\| >= 2 se` | **0 of 295** |

`se` treats the two sides as independent, which is the loose direction:
correlated sides give a smaller `se` and more eligible contracts, so a contract
that does not clear here would not clear under a tighter treatment either.

**The largest reading is the least trustworthy one.** `QMU3-QMX3` carries the
biggest `|A_s|` on the day at `0.3893`, built from **one segment on each side**,
against an `se` of `0.5306`.

**What this settles about the design.** The registered power for the leg axis was
computed at `N = 44` and gives 0.997 at a true rate of 0.80. That arithmetic is
right and its premise is not: it assumes each contract contributes a reliable
sign. **`N` was never the constraint here; sign quality was.**

**What stays open, and it is a purchase decision.** Segment counts are a property
of one trading day and add roughly linearly across days, so reaching forty
contracts at two standard errors needs about two orders of magnitude more days
against 6.8 GB of capture per day. That decision goes through the depth gate:
count qualifying cells on what is already on disk before buying more.

**This station makes no claim about the directionality of Theorems 4 and 5.**
The step from those theorems to "a position's one-sidedness travels into every
contract containing it" was the design's own and was never derived, and the
reading side does not stand either, so the station carries neither.

## B21 — the class index on A+H dual listings, and an arm whose target is set by statute

`203 pairs` `4,226 leg-years` `193 companies` `2006 to 2026` `nothing bought`

**The carrier.** One company, two shares, one profit. An A+H dual listing pays
the same declared dividend to both lines and the two lines are held under
different tax law, so the same claim delivers a different amount to different
holders **by an amount the state publishes**. Dividend withholding on the
Connect legs is 0%, 10% or 20% by 财税〔2014〕81号, 财税〔2016〕127号 and the 2023
extension, which makes this the one station in the repository whose target is
known before the measurement rather than estimated from it.

**The reading.** The class index, computed from realised prices and dividends
over one-year holding periods:

| leg | n | p10 | median | p90 | max | min |
|---|---|---|---|---|---|---|
| A | 2,297 | 2.8 | **14.8** | 45.0 | 221.1 | 0.1221 |
| H | 1,929 | 8.6 | **30.5** | 70.1 | 302.1 | 0.2829 |

basis points per year. **Zero is in neither distribution and not one leg-year of
4,226 reaches it.** A single scalar price field on positions requires the terms
not to depend on who holds, and Corollary 1 needs one edge and one pair of
classes to break it.

**The arm, and why it is an arm rather than a tolerance.** The gap between the
closed form and the exact index has a predicted shape: expanding the log in the
yield `y = D / P1` gives `gap ≈ ½ Δτ (2 − τ_a − τ_b) y²`, with the coefficient
fixed by the statutory rates and nothing fitted. What is reported is the observed
gap over that prediction, which must sit at one and fall below it monotonically
as the third-order term turns on.

| leg | second-order coefficient | ratio to prediction, by yield band |
|---|---|---|
| A | 0.0950 | 0.995 · 0.987 · 0.974 · 0.956 · 0.929 · 0.878 |
| H | 0.0850 | 0.995 · 0.988 · 0.976 · 0.957 · 0.933 · 0.890 |

Monotone on both legs, and the ratio reaches 0.9999 and 0.9998 without exceeding
one. **The third-order coefficients 0.9509 and 0.8510 match to three decimals in
the five low yield bands and the fourth-order sign reverses**, all three levels
given by statute and algebra with zero fitted parameters.

**The arm has now been insensitive to two separate defects in its own inputs,
both times for a reason stated before the defect was found.** Its ratio carries
the same yield above and below the line, so a scaled dividend moves a point along
the curve rather than off it. Neither the pre-2014 rebuild nor the adjustment
problem below moved any coefficient.

### What the cross section adds, and what its own placebo took away

Taking the loop sum across pairs on a fixed date removes any term without a pair
index, **identically rather than by controlling for it**. Adding a constant to
every pair on a date moves the dispersion by at most `1.110e-16` over 4,846
dates. That licenses one sentence and no more: **dispersion across pairs on a
fixed day is not the capital-account wedge.**

| | reading |
|---|---|
| panel | 4,846 dates, pairs per date min 28, median 84, max 198 |
| variance between dates | 0.020899 (11.3%) |
| variance within a date | 0.163720 (88.7%) |
| external anchor, 2024-06-28 | ICBC 0.2777, Ping An 0.2275, CM Bank 0.0357 |

**The placebo attached to this decomposition refutes the other half of it, and is
recorded as failing.** A currency event moves the wedge and nothing with a pair
index, so it should move the common term. Across five events the common term's
jump sits at the 14th to 39th percentile of its own history and never above the
median, while the onshore-offshore spread itself jumps at the 99.8th, 95.8th and
90.2nd. **One number says why: the wedge's standard deviation is 0.00423 against
the common term's 0.13512, so it is 3.1% of the thing it was taken for.** The
identity is untouched, because it needs the wedge to be common and not to be all
that is common. **What is withdrawn is the identification of the common term with
anything**, and with it the external cross-check that was to be run against it.

### Attribution beyond that exclusion: registered, with the order of purchase reversed

Separating the position-transfer term from the price term needs the Connect
eligibility list, which is published. **The list is not the binding input.** After
inclusion the loop sum is the transfer cost minus the cash wedge, the cash wedge
has no pair index, and the transfer cost is a published fee schedule set per
trade plus that stock's own bid-ask spread. **So the whole stock-level content is
the spread**, and whether its cross-stock dispersion is large enough to find is
the precondition. It is, and settling it needed no quotes.

**No estimator answers it and the way they fail names what does.** Four were
tried on daily bars. Corwin and Schultz (2012) floors two windows in five on
every leg; Abdi and Ranaldo (2017) comes back non-positive on 52.5% of months;
Amihud (2002) cannot floor but ranks the legs −0.958 against turnover, which is
the same measurement twice; the zero-return share of Lesmond et al (1999) ranks
+0.011 against Amihud, no relationship at all. **They fail together because they
share one assumption**: that a daily range carries information about the spread.
An A-share's range runs two to four hundred basis points against a spread in
single digits.

**What settles it is a published rule and a division.** The mainland tick is a
flat 0.01 yuan on both boards, so a stock at price `P` cannot quote a relative
spread below `0.01 / P`. Exact, stock-level, and free.

| | |
|---|---|
| tick floor `0.01/P` | p10 1.81, median 7.84, p90 23.70 bp |
| extremes | 0.46 bp at 216.72 yuan, 58.82 bp at 1.70 yuan |
| **cross-stock sd** | **0.00099, which is 0.234 of the wedge's 0.00423** |

**A floor is only a floor unless the tick binds, and whether it binds is also
measurable from closes alone.** By Harris's last-digit clustering a stock using
every tick puts 0.200 of its closes on a final digit of 0 or 5. The median leg
reads 0.2219 and 89 of 202 sit within 0.02 of uniform; clustering runs +0.6882
against log price and **−0.5009 against the floor itself**. **The tick binds
where the floor is large and loosens where it is small**, which is the direction
that refuses the objection a floor invites.

**So the stock-level term exists, is bounded below exactly at 0.234 of the common
term, and the two estimators that survive at all put it near 0.41 and 0.46.**

**Reading the eligibility rule then removes the cross-sectional route entirely,
for the third and cheapest time.** The Shanghai exchange lists "SSE-SEHK A+H
shares" as an eligibility category in its own right, so an A share is Northbound
eligible for having an H line at all, whatever its size. All 203 pairs qualify,
none carries a risk-alert marker, and 201 of 203 would clear the index route's
turnover floor regardless. **The treatment takes one value on this unit of
observation.** Two earlier readings had reached the same place more expensively:
the intended control group was a stock index's constituents rather than the
eligibility list, and turnover correlates −0.5613 with the premium across stocks,
running the median from 2.28× in the least liquid quartile to 1.30× in the most.

**On a different unit of observation the treatment does vary, and the dates are
published.** Northbound opened for Shanghai on 2014-11-17 and for Shenzhen on
2016-12-05, 749 days apart, so for those 749 days a Shenzhen A+H pair was out of
reach for a Hong Kong holder without a quota while a Shanghai one was not. Of the
203 pairs, 143 are Shanghai and 60 Shenzhen; 81 and 32 respectively were already
trading before the first launch.

**The two events exchange the roles of the two groups**, which is what carries
the identification: a fixed Shanghai-Shenzhen difference predicts the same sign
at both events and the treatment predicts opposite signs, so the groups do not
have to be argued comparable.

**The design turns out to have nothing to identify, and working out why closes
the question rather than parking it.**

**The premium cancels.** Both classes meet on one order book, so the price
component of a move from an A position to an H position is identical for them and
drops out of the difference:

    w_a(A->H) = [price] - f_a,   w_b(A->H) = [price] - f_b,   so  w_a - w_b = f_b - f_a

**A premium of 30 to 130 per cent therefore contributes nothing whatever to the
index part of the square.** It sits entirely in the friction part, which section
5.1 of `docs/b4_directed_edges.md` shows says nothing about who the agents are.
This is algebra, not a judgement about what the premium deserves to be used for.

**Then the published fee schedule empties `f_b - f_a` as well.** A Northbound
investor pays a handling fee of 0.00341%, a securities management fee of 0.002%
and a transfer fee of 0.001% on both sides, and stamp duty of 0.05% on the sell
side. **A domestic investor pays exactly the same four**: they are levied per
trade by the exchange, the regulator, the clearing house and the tax authority,
and none of them looks at who is trading.

**So the square is enumerable term by term, and the enumeration is short:**

| term | class-dependent | |
|---|---|---|
| price | no | one order book |
| the four statutory charges | no | published schedule, levied per trade |
| currency conversion | yes, but carries no pair index | the common term, measured above |
| **dividend withholding** | **yes, and it carries the index** | **the arm reported above** |
| capital gains | yes, unmeasured | exempt for Northbound under 财税〔2014〕81号, 25% for domestic corporates |

**The separation layer two was to perform is therefore derived rather than
estimated, and its answer is the arm this station already ran.** What the
enumeration adds is two further statutory edges, both read out of the same
notice, both larger than the withholding, and both run on the data already in
hand.

### Two more edges the enumeration found, and an algebra that predicts opposite shapes

Caishui [2014] 81 exempts a Hong Kong investor, enterprise or individual, from
tax on A-share transfer gains, while a mainland enterprise carries them into
taxable income at 25 per cent. **The same notice also sets a threshold rather
than a rate**: a mainland enterprise pays no enterprise income tax on an H-share
dividend once it has held continuously for twelve months, and 25 per cent
otherwise. **A location given by statute and a size given by statute, with
nothing fitted.**

**The two edges are predicted to take opposite shapes and they do.** Both indices
are a difference of two logs, and the third-order term subtracts from a positive
second-order term in the dividend case and adds to a negative one in the gains
case:

**The twelve-month threshold reaches both legs, and by one statute rather than
two.** Article 26 of the Enterprise Income Tax Law with article 83 of its
implementing regulations excludes from exemption any dividend on a listed share
held continuously for under twelve months, and Caishui [2014] 81 carries the same
threshold onto the H line. So the edge runs on all 4,226 leg-years.

**The capital-gains edge then splits itself, and the statute says which way.** A
loss is deductible where a gain is taxable, so the index reverses sign; in the
expansion the second-order term does not care about the sign of the running
variable and the third-order term does, so the loss branch is predicted to mirror
the gain branch.

| edge | statutory gap | 2nd-order coefficient | leg-years | index median | ratio across bands | extreme |
|---|---|---|---|---|---|---|
| dividend withholding, A | 0.10 | 0.0950 | 2,297 | 14.8 bp | 0.995 → 0.878 | max 0.9999 |
| dividend withholding, H | 0.10 | 0.0850 | 1,929 | 30.5 bp | 0.995 → 0.890 | max 0.9998 |
| **twelve-month threshold, both legs** | **0.25** | **0.21875** | **4,226** | **52.7 bp** | 0.996 → 0.886 | **max 0.9999** |
| **capital gains, A, on a gain** | **0.25** | **−0.03125** | 1,176 | **+622.8 bp** | 1.001 → 1.056 | **min 1.0002** |
| **capital gains, A, on a loss** | **0.25** | **−0.03125** | 1,118 | **−528.1 bp** | 0.999 → 0.950 | **max 0.9999** |

**Five readings, three statutory gaps, every shape fixed by the algebra before
the run, and every one of them observed.** The three predicted to sit below one
never exceed it, the one predicted to sit above never falls below, and **all
1,118 loss leg-years carry a negative index without a single exception**.
**A pipeline that is wrong cannot be wrong in two opposite directions at once,
and this one is asked to be right in both on the same edge with the sign of one
variable flipped.**

**The class index on this carrier now spans four orders of magnitude, from 0.12
to 2,425 basis points, and is nowhere zero.**

Three limits travel with the capital-gains edge. It bites on realisation rather
than accrual, so it is computed on the same close-of-period construction the
first arm uses. **Enterprise income tax is an annual entity-level computation
rather than a deduction at source**, so 25 per cent is the rate at the margin for
an entity with taxable income, and that is the class the edge names; this bears
on the class definition and not only on the construction. And the loss branch reads
the same class as the gain branch, an entity with taxable income to deduct
against, so the two are one edge read at two signs rather than two populations.

### The first thing this station measures rather than computes, and it agrees

Every edge above is arithmetic: a statutory rate carried through the algebra of
after-tax returns. **None of them asks whether the market prices the wedge.**

Elton and Gruber (1970) is the instrument. On the ex-dividend day the price gives
up some fraction of the dividend, and the fraction depends on what the marginal
holder pays on a dividend against a capital gain. **The level of a drop-off ratio
has been argued over for fifty years**, because transaction costs, ex-day risk and
price discreteness all move it. **A+H removes the argument**: one company declares
one dividend, the two lines are held by holders the tax code treats differently,
and differencing the two legs cancels everything that belongs to the company.

**The band is declared from statute before the run.** A resident holding an A
share past twelve months pays nothing, so the A leg should surrender the whole
dividend and read 1.00; an H-share dividend is withheld at 10 per cent for a
non-resident and 20 for a mainland individual through Southbound, so the H leg
should read 0.90 to 0.80 and **the difference should fall in [0.10, 0.20]**.

**This is the one criterion shape on this station that gates two and three bind,
so both are run first.** The standard deviation of the per-event ratio is 10.4
times its interquartile range on the A leg and 8.4 on the H, so the centre and its
error are taken robustly. Gate two's first stage, borrowing nothing: `1.645 × se`
of the difference is 0.0380 against a band 0.10 wide, a ratio of **0.380**. The
difference then sits 5.6 standard errors from zero, so power is not the binding
constraint.

| | n | centre | robust se | |
|---|---|---|---|---|
| A leg | 2,608 | **+0.9883** | 0.0194 | an untaxed holder reads 1.00 |
| H leg | 2,242 | **+0.8581** | 0.0126 | implied withholding **14.19%** |
| difference | | **+0.1302** | 0.0231 | statute says [0.10, 0.20] |
| within company | 133 | **+0.1790** | 0.0311 | 96 of 133 companies positive |

**Both the pooled and the within-company reading fall inside the band the statute
declares, and the implied 14.19 per cent sits between the 10 the non-resident pays
and the 20 the Southbound individual pays**, which is where a mixed margin
belongs. Dispersion across companies is wide, p10 −0.268 to p90 +0.798, so no
single company carries anything; only the centre does.

**One prediction was declared with a direction, and the direction had no
statutory source.** Southbound opened on 2014-11-17; the reading is an implied
0.1799 before and 0.1289 after, and differencing within the 82 companies carrying
ex-days on both sides gives −0.0701 with a robust standard error of 0.0366, **so
it is not a change in which companies are in the sample**.

**What the notice actually admits is a mixture.** Caishui [2014] 81 lets mainland
individuals into the H line at 20 per cent **and mainland enterprises at zero once
they have held twelve months**, 25 below it, alongside the non-resident's 10. A
mixture of 0, 10, 20 and 25 fixes endpoints and not a direction. **The rising sign
was the analyst's and not the statute's**, so that criterion is recorded void with
its reading preserved, and what the statute does support is registered in its
place: the implied rate stays inside 0 to 25 per cent on both sides, which it
does. **The reading is unchanged by the correction; only what may be concluded
from it is.**

### A statute that taxes one trade, and a trade that leaves no trace to tax

Caishui [2012] 85, in force 2013-01-01, made an individual's tax on a listed
dividend depend on the holding period: the whole dividend into taxable income
under a month, half from a month to a year, a quarter beyond, all at 20 per cent.
What it replaced taxed every holder at 10 per cent regardless. **So on one dated
day the cost of the dividend-capture trade doubled**, and nothing else about the
trade changed. Caishui [2015] 101 is not the event: it moved the over-one-year
tier to zero and left the under-a-month tier where it was, and the capture trade
sits in that tier.

**The direction and the control were declared before the run.** Volume in the
five days before an A-leg ex-date should thin after 2013-01-01; the H leg of the
same company is outside this statute and should not move.

| | n | median log ratio | robust se |
|---|---|---|---|
| A before | 462 | −0.0396 | 0.0214 |
| A after | 2,104 | −0.0045 | 0.0091 |
| H before | 478 | +0.1074 | 0.0183 |
| H after | 1,730 | +0.0745 | 0.0103 |

**The declared sign is not observed, and is recorded in the middle state rather
than as a refutation.** The A leg moves +0.0351 where minus was declared, the H
control does sit still at −0.0329, and the difference in differences is +0.0680.
At a standard error of 0.0233 the A leg's move is 1.5 standard errors from zero.
**The criterion was first written as `change < 0`, a zero-width strict inequality
on an estimator**, which the repository forbids whichever way such a test comes
out; a reading a standard error and a half from zero is undecidable.

**A defect of this station's own was found mid-way, and printing the profile is
what found it.** The first baseline was one-sided, taken from the sixty to eleven
trading days *before* the ex-date, so it sits earlier in calendar time than the
window it normalises and any trend in volume enters the ratio. A-share volume grew
by orders of magnitude over twenty years and the two eras compared have different
trends. **The one-sided reading sat 12 to 24 per cent below baseline at every lag
from minus ten to plus ten**, and no ex-date effect can be present ten days
before the ex-date. With the baseline taken on both sides, the main effect falls
from +0.1270 at 5.0 standard errors to +0.0351 at 1.5, **so two thirds of it was
the trend**, and the difference in differences falls from 4.5 to 2.2.

**What the corrected profile says matters more than the failed sign.**

```
   day    A before     A after    H before     H after
    -1       0.004       0.068       0.149       0.185
     0      -0.119       0.040       0.136       0.169
     1      -0.099       0.027       0.110       0.055
```

Before 2013 neither leg carries anything resembling a spike. After 2013 a peak at
day minus one appears on **both** legs, and the larger of the two, +0.185, is on
the H leg, **which this statute does not reach**. So the pattern is a market-wide
change rather than a tax effect, and **the trade the statute penalises leaves no
signature on this instrument to be removed**. That reading is recorded in the
third state rather than as a result.

**The +2.2 standard errors may not be read as the tax increasing the trade.**
That reading requires the trade to be visible first, and the profile says it is
not.

### What each criterion would refute if it failed

Twenty-six criteria have been recorded on this station. **Sorting them by what
their failure would cost is worth doing once, because the answer bears on how the
station may be quoted.**

| a failure would mean | criteria | count |
|---|---|---|
| the code is wrong | B21-1, 2A, 2H, 3, 13, 14, 15, 16, 21 | 9 |
| this carrier does not carry the quantity | B21-4, 5, 11, 12, 24 | 5 |
| the estimator does not work on this data | B21-7, 8, 9, 10, 17 | 5 |
| an assumption added on top of the theory is wrong | B21-6, 23 | 2 |
| **the world is other than the statute implies** | **B21-18, 19**, and weakly 25 | 3 |
| **the framework is wrong** | **none** | **0** |

**That last row is a property of the construction and not an oversight.** This
station's core content is computed from tax law: the statute says two classes of
holder receive different amounts from one claim, and a statute is a fact rather
than a hypothesis. **That is exactly what makes the existence result hard to
argue with, and exactly what makes it unfalsifiable by measurement.**

**The two criteria that are two-sided against the world are the drop-off arm.**
Had the market priced no class difference at all, the reading would have been that
the statutory wedge exists on paper and not in prices, which is a meaningful
negative. It reads +0.1302 pooled and +0.1790 within company, both inside the band.

**So the station's shape is: existence given by statute, and whether the market
prices it tested by measurement.** The content that could refute the framework
rather than this station lives in the zero-domain family, where the framework
names where its own quantity must vanish and the measurement is then taken there.

**The two criteria still recorded as failing are in the third and fourth rows.**
The four-instrument disagreement is a fact about Corwin-Schultz, Abdi-Ranaldo,
Amihud and the zero-return share, on which the framework says nothing, and it is
the disagreement that led to the tick floor. The currency placebo refutes the
sentence "the common term is the wedge", which was added on top of the identity;
**the identity itself holds to 1.11e-16 and the placebo returned a number, the
wedge being 3.1 per cent of the common term's dispersion.** Neither is a null
result: both are measurements whose answer was that an assumption was wrong.

### The dividend column, which carried two conventions

Before 2014 the vendor's H-leg dividend is the A-leg figure times a fixed 1.166
whatever the rate did, while the measured rate ran 0.973 to 1.267. The share of
matched pairs sitting on that constant falls from 78.1% in 2013 to 5.6% in 2014.
**Two conventions in one column**, rebuilt from the A-leg amount and the rate on
its ex-date, 308 payments over 74 legs. Effect on the H-leg median: one tenth of
a basis point.

Pairing the two legs is by best agreement rather than by nearest date, and by
declared rather than saved amounts, since the dividend column is adjusted for
later splits and the two legs do not always carry the same ones. **Three
tolerance bands were tried and all three discarded**: sorted, the excess of an
implied ratio beyond the range the rate actually took runs 0.013, 0.015, 0.020,
0.027, 0.035, 0.046, 0.059, 0.082, 0.110, 0.124, 0.187 and on to 9.14 without a
break, and a continuous tail has no place to cut. 1,843 pairs over 164 companies,
69.0% scoring exactly zero, every unpartnered payment reported.

**Which leg is faithful is not what it looks like.** ZTE's declared cash
dividends per ten shares are on the public record as 2.5, 1.5, 2.5, 3, 3, 3, 2
for 2006 to 2012. The computed H column reproduces them to one part in ten
thousand in five of seven years using its own splits and the constant; the native
A column reproduces them in none, needing an extra factor of 1.5, 1.5, 15/14, 1,
1.5, 1, 1. **A column being computed rather than reported says nothing about
whether it is right.** Across all A legs, 180 of 2,608 payments (6.9%) sit off
the declaration grid; splitting the index by that flag moves the median from 14.8
to 14.4 bp and the arm's ratio from 0.9859 to 0.9863.

## C1 — an administratively declared exchange rate, and the exact count of its loops

`105 species` `11 published standards` `b1 = 339` `no market anywhere in it`

**This is the first carrier in the project that is not money.** A global warming
potential is an administrative declaration: under standard `s`, one tonne of
species `a` counts as `GWP_s(a)` tonnes of CO2-equivalent, and compliance
schemes offset against that number, so it is an exchange rate in the operative
sense. There is no trading, no spread, no liquidity and no latency, which is
what makes the carrier worth having: whatever this measures cannot be answered
with friction.

**The cycle count has a closed form and it was checked against the machinery.**
Put every species opposite CO2-equivalent and draw one edge per standard that
quotes it. A species quoted under `S_a` standards contributes `S_a - 1`
independent loops, so `b1 = sum_a (S_a - 1)`, and each basis loop is the same
gas read twice under two standards. One standard alone gives `b1 = 0`: the field
is integrable by construction and there is nothing for it to disagree with. The
count is therefore a direct measure of how much room the institutional
arrangement leaves for disagreement, before any value is read.

**The sharpest reading holds the report fixed as well as the gas and the
horizon.** AR5 published a 100-year value with and without climate-carbon
feedback, both authoritative, and institutions choose between them. Across 86
comparable species the two agree exactly once.

**Both halves have run, and the second one settles what the first could not.**
The reading was fixed before the survey: one basis in force anywhere and this
stage measures a transition; more than one at the same time and an obligation
can be discharged two different ways in the same year. **Four methane values are
in force at once.** The treaty layer did converge on AR5 by the end of 2024, and
the disagreement moved rather than closing: AR6 publishes three methane values
and all three circulate, while the treaty adopts AR5 and excludes the fossil
methane distinction its own source draws, so one tonne of fugitive fossil
methane is 28 under the treaty and 29.8 under the corporate standard in the same
year.

**One jurisdiction priced the choice this year.** New York legislated a
twenty-year horizon in 2019, methane at 84, and replaced it with a hundred-year
basis on 26 May 2026, methane at 27.9. On the same physical record for 1990 to
2023 the reported reduction moves from 14.8 percent to 24 percent, with nothing
emitted or abated to produce those 9.2 points.

| | criterion | detail |
|---|---|---|
| PASS | C1-1 cycle rank of the declaration star, two ways | E=444 edges over V=106 nodes; closed form sum(S_a-1)=339; cycle_rank on the subdivided graph=339; species quoted by exactly one standard=17 contribute no loop |
| PASS | C1-2 holonomy of the vintage loops, GWP-100 only | 88 species decidable, 17 undecidable (one quote only); holonomy exactly 1: 0; median 1.4150, quartiles 1.2568/1.8483, max 60.640 (HFE374pc2) |
| PASS | C1-3 AR5 against AR5 with climate-carbon feedback | one report, one gas, one horizon, two published numbers: 86 species comparable, ratio exactly 1 for 1 of them, median 1.1913, range 1.0000 to 2.0000; CH4 is 28 against 34 |
| PASS | C1-4 do the vintages converge | 54 of 79 species non-monotone in vintage order, including CH4 N2O CFC11 CFC12; median relative revision SAR->TAR 19.68% TAR->AR4 3.68% AR4->AR5 9.05% AR5->AR6 12.63%; steps shrinking: False |

**C1-4 was reachable both ways.** A monotone sequence with shrinking steps would
have said the vintages are converging, that the earlier ones are superseded
rather than concurrent, and that this stage measures a transition. The steps do
not shrink and the most recent revision is the second largest of the four.

## C2 — the control arm: a system of the same kind, asked the same question, that agrees with itself

`115 colleges` `84,018 comparable placements` `six parallel classification schemes` `no market here either`

**C1 has one cheap objection and this stage is built to answer it.** That a
state-scale administrative system carries inconsistent conversion factors could
be a fact about bureaucracies rather than about whether a value scalar exists.
Settling that needs a second system of the same kind: comparable in scale and
age, carrying several parallel classification schemes at once, publishing its
declarations the same way, and equally free of prices, trading and friction.
California's course articulation system is that.

**It agrees with itself.** Across 84,018 placements that two or more published
lists both record, in a vocabulary the lists share, 28 disagree. They
sit in 12 colleges of 115, every one of them falls between the same two
documents of the same system, and the heaviest college contributes ten courses
carrying one identical discrepancy. A further 3174 are containment, where
one list records a finer sub-area than another and neither contradicts the
other. **So the multivaluedness C1 measured does not follow from the size of an
institution.**

**One arm could have read either way and read the other one.** If a scalar with
two thresholds governs transferability, then the stricter system's list is
contained in the looser one's. It is, at 113 colleges of 115, with three
courses in total on the other side. That is what agreement looks like when it
is measured rather than assumed, and it is the reason this stage's null is
worth something.

**Comparing whole area sets across lists returns disagreement for every course,
and that number is manufactured.** Each list annotates with several schemes at
once: the CSU-transferable list carries IGETC, CSU GE-Breadth and CSU
American-Ideals areas together, while the IGETC list carries IGETC areas only.
The comparison is therefore made one scheme at a time, between the lists that
actually carry that scheme. **Which lists annotate with which schemes is a
property of the documents, and reading it as disagreement about a course would
have reported a rate of 100%.**

**Three arms were scoped and did not open, all closed on paper.** Unit counts
telescope to 1 around any loop, because units are a scalar attached to a course.
"Two courses satisfying the same receiving course are equivalent" does not
follow, because articulation declares an inequality. The Ferrers 2x2, which
would show the relation admits no scalar representation at all, is confounded
at college level by curriculum coverage. Their common cause is one measured
fact: `courseIdentifierParentId` is institution-local, with none of 972 sending
identifiers shared between colleges and none of 633 receiving identifiers shared
between universities, so "the same course" is not sayable and every proxy for it
also encodes "these two institutions are different".

| | criterion | detail |
|---|---|---|
| PASS | C2-1 coverage of the sweep | 115 of 116 colleges returned data, 115 of those carry all 6 list types; 1 college(s) returned HTTP 500 for every list type and hold no record here |
| PASS | C2-2 do the lists place a course in the same areas | 84018 comparable placements over 115 colleges; areaType 1 0 comparable 0 conflict, areaType 2 22761 comparable 0 conflict, areaType 3 24706 comparable 0 conflict, areaType 4 35398 comparable 28 conflict, areaType 5 1153 comparable 0 conflict; 3174 nested, where one list records a finer sub-area than another; 28 mutually non-containing |
| PASS | C2-3 where the conflicts sit | 28 conflicts over 12 colleges of 115; the three heaviest hold 17 of them; every one is between CSUGE vs CSUTC; the heaviest college contributes 10 courses carrying one identical discrepancy |
| PASS | C2-4 UC transferability against CSU transferability | nesting holds at 113 of 115 colleges; 2 college(s) list a course as UC transferable and not CSU transferable, 3 course(s) in total. Strict nesting is what a scalar with two thresholds produces, so this arm can read either way and reads one of them |

**One college is absent and is named rather than left as a gap between two
counts.** Compton College returned HTTP 500 for all six list types and holds no
record here. It is the one California community college whose institutional
identity changed inside the record window, having operated for roughly a decade
under another college's accreditation before regaining its own; whether that is
why is a lead and not a finding. **The stage's records carry `diagnostic_only`
until that hole is closed or shown not to matter**, because one witness settles
an existence claim and no number of them settles an absence.


## C3 — fifteen provinces ordering the same universities, and no order they share

`15 provinces` `5,771 institution entries` `2,077,374 determined comparisons` `no number declared anywhere in it`

**9/9 criteria passed.**

**Carrier.** The first-tier parallel-choice filing lines published by each
Chinese province after the 2015 national college entrance examination. Fifteen
provinces in the arts track, fifteen in science, fourteen in both, 5,771
institution entries. Smallest cell 75 entries, largest 304. Full station
document at `docs/c3_admission_reversals.md`.

**What is under test.** Nobody publishes a national difficulty score for
universities, and the apparatus around the examination nonetheless speaks as
though one existed. That way of speaking has a content: if a scalar `v` over
universities existed and each province's line were a reading of it, every
province would place any two universities the same way round. `v` need not be
observable, need not be in shared units, need not be the score. The commitment
is that each province's order is the restriction of one common order.

**The objection is answered by construction.** A point is not worth the same in
two provinces, and nothing here compares a score in one province with a score in
another. Only the order inside a province is used. The objection says the two
provinces' scores are related by an unknown strictly increasing map, and every
such map leaves the reading where it was; C3-2 rebuilds the reversing tuple set
under five per-province recodings and gets the same set as an object.

| | criterion | detail |
|---|---|---|
| PASS | C3-0 panel | 15 provinces arts, 15 science, 14 both, 5771 entries; smallest cell 75, largest 304; 0 names dropped as ambiguous inside a cell |
| PASS | C3-1 whether one order fits every province | arts 105 province pairs, 681773 determined comparisons, 77933 reverse, 22123 tie, 105 of 105 pairs contain a reversal; science 105 pairs, 1395601 determined, 160280 reverse, 42506 tie, 105 of 105 |
| PASS | C3-2 invariance under a per-province recoding | the reversing (institution pair, province pair) set is identical under exponential, logarithmic, cubic, mixed and piecewise-irregular recodings applied province by province, both tracks |
| PASS | C3-3 the pairs whose order is not a property of the pair | arts 7883 institution pairs reverse in at least one province pair of 28935 compared; science 13293 of 45294 |
| PASS | C3-4 replication on the other track | 27708 institution pairs compared in both tracks; 4843 reverse in both, 6864 in exactly one, 16001 in neither |
| PASS | C3-5 whether counting the provinces resolves it | arts 17351 majority edges, 16341 lie on a three-cycle; science 28879 edges, 28256 on a cycle. Raw cycle counts 63905 and 156937 are reported and are not read as independent findings |
| PASS | C3-6 whether the reversal keeps its direction in the other track | 521134 comparisons determined in both tracks; 59672 reverse in arts, 20213 of those also reverse in science, 18240 of those keep the same province on top, 0.9024. Agreeing comparisons keep their direction 0.9611 of the time |
| PASS | C3-7 the same numbers from a publisher with no common upstream | Tsinghua publishes its own filing lines by province and year; 29 cells comparable, 25 agree to the digit, the 4 that differ are named: three by one point in inconsistent directions and one by 19 points in the province whose table is a sub-round |
| PASS | C3-8 how far apart in rank the reversing pairs sit | weaker of the two within-province rank separations; arts reversing deciles 1 2 4 6 8 10 13 16 22 32 max 155 against agreeing 1 8 16 24 32 41 52 65 80 102 max 191; science reversing 1 3 5 7 9 12 16 20 27 39 max 155 against agreeing 1 11 21 32 43 56 70 88 109 140 max 275 |

**C3-6 is the criterion that carries the finding.** C3-1 alone is compatible
with a national scalar read by each province with error, under which a reversal
is a small true gap flipped by noise. That defence predicts something it cannot
escape: the arts and science tracks are disjoint applicant pools sitting
different papers in the same provinces in the same summer, so if a reversal is
cohort error, which province ends up on top is decided afresh and the direction
match sits near one half. It is 0.9024. The remaining escape, that one province
of the pair is simply noisier and is the flipped one both times, would show as a
degenerate lean; over the 91 province pairs measured in both tracks the lean
runs from 0.3208 to 0.7624. Which province is on top depends on which two
universities are being compared.

**One pair, printed rather than summarised.** `东北财经大学` against
`中国海洋大学`, filing line, 2015. Shanghai, Beijing, Shanxi, Jiangxi, Hunan,
Guizhou, Chongqing and Heilongjiang put the first above the second in both
tracks. Shandong, Jiangsu, Zhejiang and Fujian put the second above the first in
both tracks. Guangxi and Shaanxi split between the tracks. The margins are not
rounding: Heilongjiang science is 20 points one way, Jiangsu arts 13 the other
on a 480-point scale.

**C3-8 cuts both ways and is reported that way.** Reversals do concentrate
among schools that sit close together: the median reversing comparison in arts
has them 8 places apart in the province that separates them less, against 41 for
a comparison the provinces agree on, which is what a scalar read with error
predicts. The same table says the tail is neither small nor close. The printed
separation is the weaker of the two provinces' rank distances, so the ninth
decile of 32 in arts and 39 in science means 7,793 arts and 16,028 science
comparisons in which both provinces separate the two schools decisively and
separate them opposite ways. The widest is `中央财经大学` against
`对外经济贸易大学`: Jiangxi ranks them 10 and 173 of 189 at 585 and 528, Hunan
ranks them 163 and 8 of 182 at 544 and 614. Neither province is undecided about
this pair.

**Guangdong is a sub-round and is marked.** Its table is 第一志愿组, the first
of two choice groups inside the first tier, and it is present in one track only,
so it is not among the fourteen provinces C3-6 uses. On the science side it does
enter, removing it leaves 91 province pairs of which 91 contain a reversal.

**Scope.** What is refuted is a scalar over institutions whose restriction gives
every province's order. What is not touched is a scalar over
institution-and-programme pairs, since a university offers a different programme
mix in different provinces and the panel carries institution-level lines. Note
what that rescue costs: it indexes the quantity by the very thing whose
independence was the claim. Fifteen provinces of thirty-one, one year; the
finding is an existence claim, so coverage bounds its generality and not its
validity. First-round filing only, with supplementary rounds excluded by name
and the exclusion printed by the parser.
