# B81: the country-product-dummy method is the same projection on a second graph

**RUN: 2026-09-12. Statement and proof below. Checks in `experiments/b81_cpd.py`,
record `results/b81_cpd.json`, which carries the configuration it ran under.
Paper station: zero data.**

## 0. The question this station answers

B79 showed that GEKS, the standard transitive index, is the least squares
projection of the log bilateral index onto the exact subspace of the graph of
pairwise comparisons. It registered the other standard multilateral method, the
country-product-dummy estimator, as "a regression rather than a projection and
therefore a different loss".

**Half of that registration is wrong, and the half that is wrong is the
interesting half.** A regression onto dummies *is* a projection, and the loss is
the same sum of squares. **What differs is the graph.**

## 1. Setup

A price tableau: `p[j, r]` is the price of product `j` in country `r`, observed
on some subset of the `M × R` cells. The CPD equation is

```
log p[j, r] = z_j + beta_r + e[j, r]
```

estimated by least squares (Coondoo, Majumder and Ray 2004, eq. 1). The parities
are read off `beta`, and that paper states they are invariant to the choice of
numeraire region and therefore satisfy circularity.

Draw the **bipartite graph** `Lambda`: one vertex per product, one per country,
one edge per observed cell, oriented product to country.

## 2. Theorem 26

**(1) The fitted value is a coboundary, and that is why the parities are
transitive.** Put `psi(product j) = −z_j` and `psi(country r) = beta_r`. Then

```
psi(r) − psi(j)  =  beta_r + z_j  =  the fitted value on edge (j, r)
```

so the fitted value is `d⁰psi` on `Lambda`, and a coboundary telescopes: every
cycle sums to zero. **Transitivity is not a property of dummy variable
regressions. It is that a least squares fit onto a design whose columns are
vertex indicators lands in the exact subspace, and the exact subspace is closed
under going round.** This is B79's Theorem 24(1) on a second graph.

**(2) What CPD discards, and how much of it there is.** The residual
`log p − d⁰psi` is the non-exact part, and its dimension is `b₁(Lambda)`. On a
complete tableau

```
b1(Lambda) = MR − (M + R) + 1 = (M − 1)(R − 1)
```

which is the same closed form as the square part of B79's Theorem 24(5), for the
same reason: both graphs are products.

**(3) The two methods are one operation on two graphs.**

| | graph | vertices | edge data | `b₁` on the complete case |
|---|---|---|---|---|
| **GEKS** | complete | countries | log bilateral index | `(R−1)(R−2)/2` |
| **CPD** | bipartite | products and countries | log individual price | `(M−1)(R−1)` |

**Neither is a different loss and neither is a different estimator. They are the
orthogonal projection onto the exact subspace, on two different graphs, and the
count of what each throws away is not the same number.**

**(4) On a complete equal-weight tableau they return the same parities.** Checked
by two routes sharing no code, worst gap `2.0e-15`. **Where they part is the
incomplete tableau.** A bilateral index needs two countries to price something in
common, so GEKS needs that for every pair; CPD needs only that `Lambda` is
connected, which is weaker. **That is a statement about `H⁰` and it decides
whether the parities exist at all, not how well they are estimated.**

**(5) Identification is connectivity.** With `c` components in `Lambda`, the
design matrix's rank deficiency is `c`: one free constant per component, and
`b₁ = E − V + c`. Two components are two parities that cannot be compared at any
sample size. **A missing cell is a missing edge, and the question is whether the
graph stays in one piece, not how many cells are missing.**

## 3. Placement

**This is not an academic comparison of two methods.** The International
Comparison Program runs both, at the same level of the same round: its 2021
methodology computes basic-heading parities by the Jevons index made transitive
by GEKS **and** by the country-product-dummy method, with weighted versions of
each, and then aggregates with GEKS again. **So the two graphs of Theorem 26(3)
are two graphs the same round draws over the same prices.**

**Against the index number literature.** The equation, the estimator, the
transitivity and the base-region invariance are theirs, and this station reads
them back. **A, and recorded as this framework being right rather than as a
debt.** What is added is on the mechanism and the counting side: that paper
attributes circularity to "the properties of the dummy variables regression
model", which names no mechanism; here it is that the fitted value is a
difference of a potential, and the same sentence covers Fisher's circular test
at B79. Naming the two graphs, counting what each discards, and reading
identification as connectivity rather than as missing data is **D**.

**C is empty, and this station cannot produce it**: it reads no data, so no point
prediction of any other account is scored here.

## 4. Related work

Summers (1973) introduces the country-product-dummy method. Coondoo, Majumder and
Ray (2004) give the equation used here together with the invariance and
circularity statement. Rao (2005) proves the weighted CPD equivalent to the Rao
system. Éltető and Köves (1964), Szulc (1964) and Gini (1931) are the GEKS side,
carried by B79. The discrete Hodge decomposition behind both is cited at
`b1_theorem.md` §6.

## 5. The known answers and the structural checks

**Seven criteria, all passing** at `--seed 81 --reps 10`.

| | criterion | reading |
|---|---|---|
| `B81-1` `known_answer` | transitivity and base invariance | worst triple sum `2.2e-16`, worst shift on changing the base country `2.2e-16`, worst residual-design inner product `2.1e-15` |
| `B81-2` `own_reading` | **why they hold** | every cycle of the bipartite graph sums to `2.2e-16` on the fitted values and to **`2.207` or more on the raw log prices**. The cycle basis is built from the incidence pattern and never sees the regression. The cycle count matches both the closed form and the incidence rank |
| `B81-3` `own_reading` | **two graphs** | `(M−1)(R−1)` against its incidence rank in 10 of 10, running 8 to 36; the country graph's `(R−1)(R−2)/2` running 3 to 15 |
| `B81-4` `own_reading` | do they agree | worst gap `2.0e-15` on complete equal-weight tableaux, by two routes sharing no code |
| `B81-5` `own_reading` | **identification is connectivity** | 40 sparse tableaux, **13 disconnected**; rank deficiency equals the component count in 40 of 40, and `b₁ = E − V + c` matches the incidence rank throughout |
| `B81-6` `instrument` | the gauge | dropping each dummy in turn moves the fitted values by at most `2.4e-15` and the coefficients by up to `1.139`. **Both halves are required**: unchanged coefficients would mean the gauge was never exercised |
| `B81-7` `bookkeeping` | B79's registration | named, with the correction to its wording |

**Two criteria carry a clause that had to be able to fail.** `B81-2` requires the
raw log prices *not* to be transitive, otherwise it would be reading an identity;
`B81-6` requires the coefficients to move, otherwise the gauge was not exercised.

## 6. Scope

Unweighted throughout: the weighted CPD, which is what the International
Comparison Program runs, is the same projection in a weighted inner product, and
the weights change which coboundary is nearest without changing that it is a
coboundary. **That was stated and not checked here, and was checked on 2026-09-13
at `docs/b84_weighted_cpd.md`, Theorem 28.** It holds, and it has a boundary this
sentence did not carry: the weights leave `b₁` and the rank deficiency alone for
every positive weight and jump only at zero, where a weight is an edge deletion.
The same station sharpens Theorem 26(5) below: on a tableau at the density used
here the bipartite graph comes back two-edge-connected, so no single missing cell
can disconnect it. Nothing in this station measures
a price, a parity or a tableau in any economy: the inputs are one published
equation and one published pair of claims about it. Nothing here says which
multilateral method a statistical office should use.
