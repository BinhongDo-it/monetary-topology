# B84: weighting the country-product-dummy method changes the metric and not the topology

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b84_weighted_cpd.py`, record `results/b84_weighted_cpd.json`, which
carries the configuration it ran under. Paper station: zero data. B81's tableau
generator, design matrix, incidence matrix and cycle basis are imported rather than
rewritten, so a disagreement between the two stations is a real one.**

## 0. The question this station answers

`docs/b81_cpd.md` section 6 states, and says plainly that it does not check, that
the weighted country-product-dummy method the International Comparison Program
actually runs is the same projection in a weighted inner product, so the weights
change which coboundary is nearest without changing that it is one.

**That claim is correct, and it has a boundary the sentence did not mention.**

## 1. Setup

B81's bipartite graph `Lambda`: one vertex per product, one per country, one edge
per observed cell, oriented product to country. Put `W = diag(w_e)` with `w_e > 0`
on the observed cells. The weighted fit is

```
psi_w  =  argmin_psi  sum_e  w_e ( y_e − (d⁰psi)_e )²
```

which is B81's problem in the inner product `<a, b>_W = a' W b`.

## 2. Theorem 28

**(1) The weights cannot break transitivity.** The fitted value is `d⁰psi_w` for
whatever `psi_w` the weighted problem returns, so it is a coboundary by
construction and every cycle sums to zero. **This does not depend on the weights at
all**: the design's column space is the exact subspace either way, and only which
element of it is nearest depends on `W`.

**(2) The normal equations are a weighted graph Laplacian.**

```
L_W psi = d⁰' W y,     L_W = d⁰' W d⁰
```

For `w > 0` the null space of `L_W` is the constants on each component, so the rank
deficiency is `c` and identification is exactly B81's Theorem 26(5). **Weights do
not identify anything that connectivity did not, and do not lose anything it did.**

**(3) The discarded dimension is topological.** `b₁(Lambda) = E − V + c` contains no
weight. **The weights change which coboundary is nearest; they do not change how much
is thrown away in dimension.**

**(4) Zero is not a small weight.** As `w_e -> 0` the parities converge to the fit on
the graph with `e` deleted, and the approach is linear in `w_e`. But `b₁` and `c` are
unchanged for every `w_e > 0` and jump only at zero: if `e` lies in a cycle, `b₁`
drops by one; if `e` is a bridge, `c` rises by one and two parities stop being
comparable at any weight. **So the family is continuous in the parities and
discontinuous in the topology, and the discontinuity sits exactly at the endpoint.**

**(5) The unweighted case is inside the family**, at `w = 1`, and the fit is
invariant to `w -> lambda w`.

## 3. What the checks read

**Seven criteria, all passing** at `--seed 84 --reps 10`.

| | criterion | reading |
|---|---|---|
| `B84-1` `known_answer` | unit weights are B81, the scale does nothing, and the gauge is sound | fitted values agree to `0.00e+00` importing B81's own solver; scaling every weight by 7.3 moves the parities by `2.2e-15`; re-gauging to each other base moves no pairwise difference by more than `2.2e-16`, **while the raw coefficients move by at least `0.163` when the weights change** |
| `B84-2` `own_reading` | the weighted fit is a coboundary and the prices are not | 98 cycles tested: at most `2.2e-16` on the fitted values, at least `0.928` on the raw log prices |
| `B84-3` `own_reading` | **metric, not topology** | over six dispersions on ten tableaux, `b₁` and the rank deficiency hold at every dispersion and equal the closed form and the component count, **while the parities move by up to `1.819`** |
| `B84-4` `own_reading` | **zero is an edge leaving** | ten cycle edges converge to the deleted-edge solution, worst `1.1e-12` at the bottom of the ladder, ratio to the weight between `0.85` and `1.00`; ten bridges raise the component count by one and leave `b₁` alone |
| `B84-5` `own_reading` | how far the two get | largest change in any pairwise comparison, by dispersion of log weight: `0.25 -> 0.15`, `0.5 -> 0.36`, `1.0 -> 0.68`, `2.0 -> 0.81`, `4.0 -> 1.60`, medians |
| `B84-6` `instrument` | two ways to solve it | `6.3e-15`. **An implementation check and not a second route**: the normal equations make the two equal by a theorem |
| `B84-7` `bookkeeping` | B81's section 6 | discharged, and that section's wording corrected in the same round |

**Three criteria carry a clause whose job is to be able to fail.** `B84-1` requires
the raw coefficients to move under a change of weights, otherwise its gauge clause
would be reporting that a gauge nobody exercised is harmless. `B84-2` requires the
raw log prices *not* to telescope, and counts the cycles it tested, since a tableau
with no cycle would pass both halves for nothing. `B84-3` requires the parities to
move, since an unchanged topology on its own is also what a weight that never
reached the solve looks like.

## 4. Two things the checks found that the statement did not contain

**The boundary case is unreachable on a dense tableau.** At the density the rest of
this station uses, the bipartite graphs come back two-edge-connected, so no bridge
exists and no vanishing weight can disconnect anything. The bridges of `B84-4` had
to be drawn from sparser tableaux, where pendant edges appear. **A missing cell
threatens identification only where the graph was thin to begin with**, which
sharpens B81's Theorem 26(5) from "connectivity decides" to "connectivity decides,
and on a well-covered round it is not close."

**The approach to the deleted-edge solution is linear in the weight.** Dividing the
weight by a factor divides the distance by the same factor, measured over every step
of every edge. **So a small weight is a small perturbation and not a partial
deletion**: nothing about the topology is happening gradually.

**Sharpened 2026-09-15 by B103** ([`b103_time_reachability.md`](b103_time_reachability.md),
Corollary 41.1). The distance to the deleted-edge solution is exactly `|D| · s · w/(1 + wR)`, with `R` the
effective resistance between the edge's ends in the deleted tableau, so the ratio printed for
`B84-4` is `(1 + w_b R)/(1 + w_a R)`: its low end `0.85` is that curvature on the first step at
`R = 1.8`, the second steps sit within `1.8e-3` of one, and its high end is float noise on the
last step. The linear reading holds as the weight goes to zero.

## 5. Placement

**A.** The weighted estimator, its equation and its use in the ICP are the index
number literature's; Rao (2005) proves the weighted version equivalent to the Rao
system, which is cited and not re-derived here.

**D.** That the weights are a change of inner product on a fixed graph, that the
discarded dimension is therefore a topological invariant of the tableau's coverage
and not a property of the weighting scheme, and that the weight family's only
discontinuity is edge deletion at zero. **The counting side is the part no account of
the estimator supplies, because nothing in that account has a graph in it.**

**C is empty and this station cannot produce it**: it reads no data, so no point
prediction of any other account is scored here.

## 6. Scope

Positive weights throughout. Nothing here says which weights a statistical office
should use, and nothing here measures a price, a parity or a tableau in any economy:
the inputs are one published equation and one published claim about its weighted
form. The tableaux are drawn, and what is checked on them is structure, not
magnitude.
