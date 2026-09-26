# B77: what changes when the book of techniques becomes a continuum, and what does not

**Status: statement and proof, with two classical facts read back and four structural checks.
Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B77-5 and B77-6,
are in `experiments/b77_continuum.py`, record `results/b77_continuum.json`, and are listed in
§5.**

---

## 0. The question this station answers

[`b72_land_and_rent.md`](b72_land_and_rent.md) registered a continuum of land qualities and
[`b76_envelope.md`](b76_envelope.md) registered a continuum of techniques, each noting the two
were the same object. **This station makes the index set a continuum and asks what survives.**

1. **The active set does not grow with the book** (§2, Theorem 22(1)). B75's bound on how many
   processes run is the number of goods, and that bound never mentions how many processes there
   are. **A continuum of techniques still runs at most `m` of them at a basic optimum. The
   thickness of the book does not enter.** The qualifier is the programme's: a degenerate
   optimum can spread the same activity over more processes, so this bounds the solution a
   vertex solver returns, which is what §5 reads.
2. **Counting stops being the question and differentiating replaces it** (§2, Theorem 22(2)).
   B76's `λ_s(k)` is true at every `k` and says nothing in the limit, because the switch count
   grows without bound. What is left is a derivative identity: `E'(x) = ∂C_θ/∂x` at the owner.
   **Under one and the same refinement, the count of running techniques stays put while the
   count of switch points diverges. They are not two measures of one thing.**
3. **The label is not the invariant** (§2, Theorem 22(3)). In a continuum the owner's index can
   wander up and down while the coefficient it carries moves monotonically. So **"a technique
   returns", which is well posed with finitely many, is a statement about names, and names are
   dense.** What survives is a statement about the owner's slope.
4. **A continuum of land qualities adds no cycles** (§2, Theorem 22(4)). Qualities are pendant
   vertices at every discretisation, so `b₁` never moves. What the limit does change is that the
   marginal quality becomes a point of measure zero: **it still pins the wage and it contributes
   nothing to total rent, which was already true and is now visible.**

## 1. Setup

An index set `Θ`, finite or the interval `[0,1]`. Technique `θ` has cost `C_θ(x)` with
`x = 1 + r`; the envelope is `E(x) = min_θ C_θ(x)` and the owner is `θ*(x) = argmin`. On the
quantity side, processes are indexed by `Θ` with input and output rows `A_θ`, `B_θ` over `m`
goods, and the von Neumann programme of [`b75_rectangular_programme.md`](b75_rectangular_programme.md)
applies with the process set now of any cardinality.

**The closed-form family used throughout.** `C_θ(x) = θ² + (1−θ)²x` on `θ ∈ [0,1]`. The
first-order condition `2θ − 2(1−θ)x = 0` gives `θ*(x) = x/(1+x)`, and substituting back,

```
E(x) = θ*² + (1−θ*)² x = (x² + x)/(1+x)² = x/(1+x)
```

with `E'(x) = 1/(1+x)²`. **The owner moves continuously across the whole index set as `x` runs
from 0 to infinity**, which is what makes this family the right one to ask the counting question
on.

## 2. Theorem 22

**Theorem 22.** With the setup of §1:

1. **(The active set does not grow with the book.)** At a basic optimal solution of the von
   Neumann programme, the number of processes carrying positive intensity is at most `m`,
   whatever the cardinality of `Θ`. **The proof is about a basic solution and the statement
   follows it**: a degenerate optimum can spread the same activity over more processes, so this
   bounds the solution a vertex solver returns rather than every optimal one. Corrected
   2026-09-13; §5 reads exactly that solution and its counts are unchanged.

   *Proof.* B75's Theorem 20(2): the programme for the intensities has `m` inequality rows and
   one normalisation, so an optimal basic solution has at most `m + 1` basic variables, one of
   which is the value. **That count is of rows, not of columns**, so it is unchanged when
   columns are added, and in the limit it is the statement that an optimal measure on `Θ` is
   supported on at most `m` atoms. ∎

   **What this rules out.** It is not that a continuum is a good approximation to a large finite
   book. **It is that the two give the same answer to the question "how many run", exactly, at
   every size.** §5 refines a continuum from 10 processes to 600 and the count is 4 throughout.

2. **(Counting goes, differentiating stays.)** As `Θ` is refined, the number of switch points on
   the envelope grows without bound, so `λ_s(k)` has no limiting content. Where the owner is
   unique the envelope is differentiable and `E'(x) = ∂C_θ/∂x` evaluated at `θ*(x)`.

   *Proof.* The growth is exhibited in §5. The identity is the envelope theorem: `E(x) =
   C_{θ*(x)}(x)`, and differentiating, the term in `dθ*/dx` carries the factor `∂C_θ/∂θ`, which
   vanishes at an interior minimiser. ∎

   **The two counts move in opposite directions under the same refinement**, which is the whole
   content of this clause: the number that run is a property of the economy, and the number of
   switches is a property of how finely the book was written.

   **A note on where the envelope theorem does and does not apply**, because this repository has
   a station arguing the other way. [`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
   observes that the Hulten aggregation argument has **no object for the envelope theorem to act
   on**, because the allocation it differentiates is not the argmax of anything. **That is
   consistent with this clause and is its other half**: the theorem holds exactly where there is
   a genuine optimisation, and choice of technique is one. The two together are one
   discriminant, applied in the two cases where it comes out differently.

3. **(The label is not the invariant.)** With affine costs the envelope is concave, so the slope
   carried by the owner is non-increasing in `x`. **The owner's index need not be monotone**: if
   `θ ↦ b(θ)` is not monotone, the index can move up and down while the slope it carries only
   falls.

   *Proof.* `E` is a minimum of affine functions of `x`, hence concave, and where differentiable
   `E'(x)` is the slope of the attaining member; a concave function has non-increasing
   derivative. The index claim is exhibited in §5. ∎

   **What a dense index does and does not dissolve.** With `k` techniques, "technique `i`
   leaves the envelope and returns" is well posed and B76 settled when it can happen. **With a
   continuum, neighbouring members are nearly the same profile**, so the minimiser wobbles
   between them and a return read off one such wobble is not stable: §5 takes the largest
   candidate found and halves its margin at each grid refinement. **A feature holds under
   refinement; an artefact halves.**

   **This clause read, until 2026-09-13, that the question itself dissolves. It does not.**
   The stable form is whether the minimiser over the index is monotone in the rate, which is
   well posed at any cardinality, and
   [`b93_continuum_second_pass.md`](b93_continuum_second_pass.md) exhibits a family whose owner
   crosses the whole index and comes back, leading the runner-up by `1e-4` at both spells and
   holding through a 64-fold refinement, against the `1e-8` of the wobbles. **So what §5 watched
   collapse was a wobble and not the question.** The reading in §5 and every count in this file
   are unchanged.

4. **(Land qualities are pendant, at any cardinality.)** A quality bought by one method and
   produced by nothing hangs off the graph by a single edge, adding one vertex and one edge, so
   `b₁` is unchanged. This holds at every discretisation and therefore in the limit. In the
   limit the marginal quality has measure zero, so it contributes nothing to total rent while
   still fixing the wage.

   *Proof.* The `b₁` half is B72's Theorem 17(1) applied once per quality. The rent half is the
   convergence of the Riemann sum, exhibited in §5. ∎

## 3. Placement

**What this framework reads of the world.** How many techniques run is bounded by the number of
positions and not by how many techniques exist; the switch count is a property of the
discretisation rather than of the economy, and the derivative identity is what survives; the
owner's index is a name while the coefficient it carries is the invariant; and a continuum of
land qualities adds no cycles.

**What the classical account reads of it.** The envelope theorem; the concavity of a lower
envelope of affine functions; that a continuum of techniques makes the wage-profit frontier
smooth, which is the surrogate production function reading; and Ricardo's rent as an integral
with a marginal land paying nothing.

| cell | content |
|---|---|
| **A** | The envelope theorem, the concavity of a min of affine functions, the smoothness of the frontier under a continuum, and rent as an integral. That account has all of it. **Recorded as this framework being right, not as a debt** |
| **D2** | Empty. What this station asks about the continuum, that literature does answer where it asks it |
| **D** | That the bound on how many run is a bound on rows and so is blind to the cardinality of the book; that the two counts diverge in opposite directions under one refinement; that the wobble between neighbouring members dissolves when labels are dense while the owner's slope survives, the returning-technique question itself staying well posed as monotonicity of the minimiser (B93); and that the marginal quality's zero share and its wage-pinning role come apart cleanly in the limit. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 4. Related work

The envelope theorem and the concavity of a lower envelope of affine functions are standard and
are used here rather than established. The reading of a continuum of techniques as smoothing the
frontier is Samuelson's surrogate production function and the Cambridge exchange around it,
which B67 and B74 already read; **this station does not reopen whether that smoothness
rehabilitates anything**, which is that exchange's own question.

- Samuelson, P. A. (1962). Parable and realism in capital theory: the surrogate production
  function. *Review of Economic Studies* 29(3), 193-206.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 5. The known answers and the structural checks

`experiments/b77_continuum.py`, record `results/b77_continuum.json`, which carries the
configuration it ran under. Seed 0; a run takes about nine seconds and a second run writes the
same bytes. All five pass.

**B77-5, two classical facts read back on constructed instances.** **(a)** The lower envelope of
a family of affine functions is concave, so the slope carried by the owner never rises: over 400
drawn families **the largest rise is exactly `0.0e+00`**, exact because concavity is not an
approximation. **(b)** The envelope theorem holds within `1.5e-10` on the closed-form family,
whose envelope is exactly `x/(1+x)` with owner `x/(1+x)`; a grid of 20001 values of `θ`
reproduces the envelope within `1.0e-8` and the owner within `2.4e-5`, the latter being half the
grid spacing and therefore the grid's own floor rather than an error.

**B77-6, the structural checks.**

- **B77-6a, the active set.** A continuum of processes on 4 goods, discretised at 10, 50, 200
  and 600. **Four processes run at every one of them**, while the expansion factor converges:
  `2.87458619`, `2.87492658`, `2.87497868`, `2.87499294`. **The programme is written out again
  here rather than imported from B75, so that a change to one station's file cannot reach
  another's, and the copy is pinned against an external number**: on QuantEcon's published
  example it returns the cube root of two within `1e-9`.
- **B77-6b, the other count.** The closed-form family discretised at 5, 20, 80, 320, 1280 gives
  **4, 17, 71, 280 and 741 switch points**. Beside B77-6a: **under the same refinement one count
  stays at 4 and the other diverges.**
- **B77-6c, the label.** In the affine class **the owner's label wanders up and down on 13 of
  400 families while the slope it carries never rises on any**, largest rise exactly `0.0e+00`.
  In the quadratic class a search over 1500 families found a candidate rising slope; taken
  through a grid ladder it reads `0.017023`, `0.008509`, `0.004254`, **halving at each step**.
  **Recorded as not found in this family class, which is not the same as shown not to exist.**
- **B77-6d, land.** On a ring of four processes, `b₁` is 1 with 1, 5, 20 and 50 lands alike.
  Total rent as a left-endpoint Riemann sum reads `0.450000`, `0.495000`, `0.499500`,
  `0.499950`, **climbing to the integral `1/2`**. Left endpoints and not midpoints: the midpoint
  rule is exact for a linear integrand, so a midpoint sum would read `1/2` at every `k` and
  could not fail whatever the limit was.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts are counts on drawn or constructed families, and the negative result in B77-6c is a
negative for one family class searched at one budget.

## The registered slope question, reformulated and answered 2026-09-13

[`b93_continuum_second_pass.md`](b93_continuum_second_pass.md) takes the registration this station
left, and **changes the object before answering it**.

**The registered object is automatic.** Every member of the quadratic family here has a strictly
positive leading coefficient, so every owner curve is convex and the envelope's slope rises inside
any run of one owner by construction. Refining the parameter grid only shortens runs against a
fixed `x` grid, so what the refinement test measures is the `x` grid.

**The well-posed object is capital per worker along the envelope**, which is what a slope reversal
means economically and what B92 measures on discrete families. On that object the answer runs the
other way: **capital reversing on a continuum occurs on about a fifth of drawn families at every
degree from two to five, and 67 of 100 cohort members survive a 64-fold refinement**. The cohort
is taken in draw order rather than by the largest rise, since selecting the maximiser selects on
the statistic and a discretisation artefact is what would win that selection.

**This station's bounded active set is what decides the other reading.** Filling a family in
shrinks B92's two-valued `k` by a median factor of `0.028` where the active set more than doubles,
and leaves it exactly where the active set does not, factor `1.000`.

## 6. Scope

One index set at a time, and the continuum is always reached as a limit of discretisations
rather than handled symbolically: statements about measures on `Θ` are stated but the checks are
finite. The carriers are small, at most 600 processes and 4 goods, because the point is limiting
behaviour and not scale. Whether a continuum's smooth frontier rehabilitates an aggregate
production function is the Cambridge exchange's own question and is not touched. Nothing here
measures a technique, a land quality or an envelope in any economy.
