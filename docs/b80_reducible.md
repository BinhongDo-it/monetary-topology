# B80: a reducible economy, and why its two factors are read off two different parts

**RUN: 2026-09-12. Statement and proof below. Checks in
`experiments/b80_reducible.py`, record `results/b80_reducible.json`, which carries
the configuration it ran under. Paper station: zero data. The solver is B75's and
is imported rather than rewritten.**

## 0. The question this station answers

Three registrations asked for the same object. B75 left open which component `α`
and which `β` are read off in a reducible system, noting that the two come apart
there and that the counting identity fails with them. B71 left the
Kemeny-Morgenstern-Thompson generalisation registered, which is what relaxes von
Neumann's positivity and so admits reducible economies at all. B77 left the
joining of the continuum's active set to that decomposition.

**All three turn on one question: which part of a disconnected economy does a
factor live on.** The answer is that the two factors do not live on the same
family of parts, and that the difference between the two families is exactly the
direction of the edges.

## 1. Setup

`n` processes, `m` goods, non-negative `A` and `B`, both `n × m`. Von Neumann's
two programmes:

```
TEP   max alpha  subject to  x'B >= alpha x'A,   x semi-positive
EEP   min beta   subject to  Bp <= beta Ap,      p semi-positive
```

A set `S` of goods is **independent** when some set `T` of processes consumes
nothing outside `S` and together produces every good in `S`. The economy is
**irreducible** when it has no proper independent subset. This is the
Kemeny-Morgenstern-Thompson relation, and on the graph it is a statement about
closure under consumption, not about the size of any coefficient.

A **simple economy** is one with `B = I`: process `j` is "produce good `j`", so
the economy is the single matrix `A` and the digraph `i -> j` when `A[i, j] > 0`
is the consumption relation.

## 2. Theorem 25

**(1) Independence is closure, and it is not strong connectivity.** On a simple
economy `S` is independent exactly when no row of `A` indexed in `S` has a
non-zero entry outside `S`, that is, when `S` is closed under out-edges. A
strongly connected component need not be closed: it may consume from outside and
still be strongly connected. **The two families differ, and both appear in every
economy that is not one piece.**

**(2) The two factors are read off the two families, one each.** For a simple
economy with Perron roots `lambda_S` on the principal blocks,

```
alpha_0 = max over S closed under consumption of  1 / lambda_S
beta_0  = 1 / lambda_PF(A) = min over all strongly connected components of 1 / lambda_S
```

*Proof.* Let `x` be feasible for TEP with support `S`. For a good `j` outside `S`
the constraint reads `0 >= alpha (x'A)_j`, so `(x'A)_j = 0`, so no row indexed in
`S` touches `j`: **the support of `x` must be closed under consumption.** On `S`
the constraint is `x_S >= alpha x_S A[S,S]`, which is feasible exactly for
`alpha <= 1/lambda_S`. Taking the best such `S` gives the first line. Now let `p`
be feasible for EEP with support `S`. For a good `j` outside `S` the constraint
reads `p_j <= beta (Ap)_j`, and `p_j = 0` satisfies it whatever `A` does:
**the support of `p` is under no closure constraint at all.** So the minimum runs
over every non-empty `S` and is attained at the largest Perron root, which is the
whole matrix's. ∎

**The asymmetry is the direction of the edges.** A quantity programme cannot
expand on inputs drawn from a part that is not expanding with it; a price
programme can put a zero on any good and be done.

**(3) Irreducible collapses the two families into one, which is Theorem II.**
If the only independent subset is everything, the max in the first line runs over
one term, the whole matrix, and both lines return `1/lambda_PF(A)`. So
`alpha_0 = beta_0` follows from connectivity and from nothing else. **The gap
`alpha_0 - beta_0` is an `H⁰` quantity: it measures that the economy is in
several pieces, in the directed sense of `b4_directed_edges.md`.**

**(4) Which part the active set lives on.** The support of the intensity vector
is closed under consumption and lies inside the part attaining `alpha_0`. This is
what B75 registered as "which component" and what B77 registered as joining the
active set to the decomposition: the constraint is on the **support**, not on the
count, so it survives whatever the cardinality of the process set.

**(5) The gap and the spread of the cycle sums are two different objects.**
Write the field on processes as `log((B_j p)/(A_j p))`, the sum around process
`j`'s cycle. Two off-diagonal cells exist, so neither quantity determines the
other:

| | cycle sums all equal | cycle sums not all equal |
|---|---|---|
| **one piece** | an irreducible simple economy | **an irreducible economy with more processes than goods** |
| **several pieces** | **a reducible economy, read part by part** | the general case |

The upper right cell needs more processes than goods. On a simple economy with
`A` irreducible the Perron vector is strictly positive, so every process runs and
every cycle sum is the same number: that cell is structurally empty there, and it
opens exactly where B75's bound on the active set bites.

## 3. Placement

**Against the von Neumann literature.** Theorem I, Theorem II, the two example
economies and their factors are theirs, and this station reads them back. **A,
and recorded as this framework being right rather than as a debt.** The published
one-line summary for a reducible simple economy, `alpha_0 = max_i alpha_i` and
`beta_0 = min_i beta_i` over the irreducible parts, is correct on each half under
a different reading of "part", and **no single reading carries both**: reading
`beta_0` off the closed family is wrong on 7 of 10 drawn economies, and reading
`alpha_0` off the all-components family is wrong on 3 of 10. Separating the two
families, saying which is which, and giving the reason as a direction on the
graph is **D**: that literature states the line and does not split it.

**The scalar price field.** Nothing is scored against it here. **B** is an old
reading and is not counted again.

**C is empty, and this station cannot produce it**: it reads no data, so no point
prediction of any other account is scored here.

## 4. Related work

von Neumann (1945) for the model and the equality. Kemeny, Morgenstern and
Thompson (1956, *Econometrica* 24, 115-135) for the generalisation that relaxes
positivity and for the independence relation used here. QuantEcon, *Von Neumann
Growth Model (and a Generalization)*, for the two worked economies, the statement
of the two theorems and the summary line examined in §3. Kurz and Salvadori treat
the same material on the classical side, which B71 records.

## 5. The known answers and the structural checks

**Seven criteria, all passing** at `--seed 80 --reps 10`.

| | criterion | reading |
|---|---|---|
| `B80-1` `known_answer` | both published economies | example 1 irreducible with `alpha = beta = 1.259921050`, which is `2^(1/3)`; example 2 reducible with `alpha = 1.259921050` and `beta = 1.000000000`. Both inside `1e-8` of the published pair |
| `B80-2` `instrument` | the independence relation, two enumerations | 17 economies, one enumeration over subsets of goods and one over subsets of processes, **17 agree**; 14 reducible and 3 irreducible, so both branches occur. **The first version of the second route failed here**: it recorded only `produced(T)` where the definition admits every `S` between `consumed(T)` and `produced(T)`, and the criterion caught it at 6 of 17 |
| `B80-3` `own_reading` | **the two families** | `alpha_0` is the max over the closed parts in 10 of 10; `beta_0` is `1/lambda_PF` of the whole matrix in 10 of 10. **Both cross readings fail**: `beta_0` off the closed family wrong in 7 of 10, `alpha_0` off the all-components family wrong in 3 of 10 |
| `B80-4` `own_reading` | where the active set lives | the intensity support is closed under consumption and inside the part attaining `alpha_0` in 10 of 10; the price support is outside that part in 3 of 10, which is the asymmetry stated as a count |
| `B80-5` `own_reading` | the gap is connectivity | 11 irreducible economies, every one with `\|alpha - beta\|` below `1e-6`, zero exceptions; 11 reducible, of which 5 carry a gap above `1e-4`, largest `1.511786`. **Stated one way**: reducible permits a gap and does not force one |
| `B80-6` `own_reading` | `H⁰` against `H¹` | both off-diagonal cells exhibited. Irreducible with a spread: gap `1.3e-14` and cycle sums spanning `0.0427` over 5 processes on 4 goods, one idle. On 20 irreducible simple economies the worst spread was `3.9e-14`, so that cell is empty there for the Perron reason. Reducible with no spread inside a part: gap `0.259921` while each of the two parts carries one common sum |
| `B80-7` `bookkeeping` | the three registrations | B75, B71 and B77, each named with the criterion that answers it |


## Basics as a case of this decomposition, 2026-09-13

[`b96_basics_and_subsystems.md`](b96_basics_and_subsystems.md) names Sraffa's basics on the same
graph. A commodity is basic when it enters, directly or indirectly, the production of every
commodity, **which is this station's reachability relation read along its other argument**, and the
basic part is the part every process depends on.

Two classical results come back as block facts: **the maximum rate of profit is the basic part's
alone**, on 200 of 200 drawn systems, because the non-basics use the core and the core uses none of
them so the spectrum splits; and **a tax on a non-basic leaves the rate and every basic price
exactly where they were** while the same tax on a basic moves both, also 200 of 200.

## 6. Scope

The two-family statement of Theorem 25(2) is proved and checked for a simple
economy, `B = I`. For a general rectangular `B` the same proof gives the same
constraint on the two supports, but the parts are no longer indexed by principal
blocks of one matrix and the Perron route is not available, so the factors are
read by the programme rather than by an eigenvalue and the closed-form max and
min are not claimed here. Nothing in this station measures an economy: the
numerical inputs are two published example matrices and two published factors.
Nothing here says which of the several equilibria of a reducible economy should
be selected, which is a question about an objective this framework does not
supply.
