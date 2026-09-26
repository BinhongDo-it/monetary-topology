# B71: von Neumann's equality as the field side and the flow side of one pencil

**Status: statement and proof, with one known answer from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B71-5 and
B71-6, are in `experiments/b71_von_neumann.py`, record `results/b71_von_neumann.json`, and are
listed in §6.**

---

## 0. The question this station answers

[`b70_joint_production.md`](b70_joint_production.md) ended with the price equations
overdetermined whenever the processes outnumber the commodities, and registered the inequality
formulation as the thing one does instead. **That formulation is von Neumann's**, and it comes
with a theorem: the rate at which the economy can expand and the rate of interest are the same
number. This file reads that theorem.

1. **The two numbers are one root of one pencil** (§2, Theorem 16(1)). The intensity vector is
   the right Perron vector and the price vector the left one, so **von Neumann's equality is
   Theorem 9's pairing of the field side with the flow side**, read at the pencil `(B, A)`.
2. **Read on the cycles, the interest factor is the common cycle sum** (§2, Theorem 16(2)). So
   the equality says: **the number the field puts on every production cycle is the logarithm of
   the number the flow grows by.**
3. **The two complementary slackness conditions are two sentences about cycles** (§2, Theorem
   16(3)). A process is operated only if its cycle carries the common sum; a commodity is
   priced only if it is not in excess. **A cycle whose sum falls short is idle**, the converse
   needing non-degeneracy.
4. **Sraffa's standard commodity is the von Neumann ray of that economy** (§3, Corollary 16.1).
   With one product per process and no wage the pencil degenerates to the eigenproblem of `A`,
   and Corollary 12.4 of B67 and von Neumann's duality are one statement said twice.
5. **Fold the wage basket in and the same root is the rate of profit of B68 and B69** (§3,
   Corollary 16.2): an economy reinvesting every profit grows at the profit factor.

## 1. Setup

`A` and `B` are `m × n` and non-negative, **rows are commodities and columns are processes**,
as in [`b70_joint_production.md`](b70_joint_production.md) §1. **von Neumann writes them
transposed**, with `a_ij` the input of good `j` by process `i`; his intensity vector `X` and
price vector `Y` are our `x` and `p`, his `α` the coefficient of expansion and his `β` the
interest factor. His four conditions, in his numbering, are

```
(7)   α Σ_i a_ij x_i ≤ Σ_i b_ij x_i          (8)   β Σ_j a_ij y_j ≥ Σ_j b_ij y_j
(7')  where (7) is strict,  y_j = 0          (8')  where (8) is strict,  x_i = 0
```

which in the convention here read `α A x ≤ B x` and `β p A ≥ p B` with the same two slackness
clauses. The square case with equality throughout is the one this file proves; §4 says what is
left out.

**Process `j`'s cycle** is drawn as in B70: money buys the input bundle for `(p A)_j`, the
process runs, and the output bundle sells for `(p B)_j`. There is no wage here: von Neumann
folds subsistence into `A`, which is what Corollary 16.2 uses.

## 2. Theorem 16

**Theorem 16.** Let `A`, `B` be square and non-negative with `B` invertible, and write
`C = B^{-1}A`, the input matrix per unit of output bundle. Suppose `C ≥ 0` and irreducible.
Then:

1. **(One root, read from either side.)** With `λ = λ_PF(C)`,

   ```
   α = β = 1/λ
   ```

   the intensity vector `x` is the right Perron vector of `C` and is strictly positive, and the
   price vector is `p = u B^{-1}` with `u` the left Perron vector. **The coefficient of
   expansion is read off the flow side and the interest factor off the field side, and they
   agree because they are one eigenvalue of one matrix.**
2. **(The interest factor is the common cycle sum.)** `p B = β p A` written column by column is
   `(p B)_j = β (p A)_j` for every process, which is the statement that **every production
   cycle carries `log β`**. So Theorem 16(1) says the common cycle sum is the logarithm of the
   economy's expansion factor.
3. **(Slackness, read on cycles.)** Condition (8) says no cycle carries more than `log β`, and
   (8') that a process whose cycle carries strictly less is not operated. Condition (7) says no
   commodity is in deficit, and (7') that one in strict excess is priced at zero. **So a cycle whose sum falls
   short is idle, and free disposal is the statement that a commodity off the binding
   constraint carries no term.** **The converse is not in the conditions**: a cycle can reach
   the common value and still carry no intensity, which is a degenerate vertex, and B75 reads
   exactly that case. Published as "idle exactly when" and corrected 2026-09-13.
4. **(Positivity of prices is not part of the equality system.)** `p = u B^{-1}` and `B^{-1}`
   need not be non-negative, so `p` can fail to be positive even with `u > 0`. **This is what
   the inequalities and free disposal are for**, and B70-6d is the other side of it: among
   productive joint systems drawn without the condition `C ≥ 0`, 52 of 400 admitted no rate at
   all carrying a positive price vector.

**Proof.**

**(1)** `B x = α A x` is `x = α B^{-1} A x = α C x`, so `C x = x/λ` with `λ = 1/α`; a
non-negative irreducible matrix has a positive eigenvector for its Perron root and for no other
eigenvalue, so `x > 0` forces `1/α = λ_PF(C)`. On the other side, put `u = p B`; then
`p B = β p A` is `u = β u C`, so `u C = u/β`, and the same Perron-Frobenius statement applied
to `Cᵀ` forces `1/β = λ_PF(C)`. Hence `α = β = 1/λ_PF(C)`, and `p = u B^{-1}` by construction.

**(2)** is the column-by-column reading of the same equation, with the cycle's two legs
`(p A)_j` and `(p B)_j`.

**(3)** is the reading of (7), (8), (7') and (8') under the identification in (2).

**(4)** is the observation that `B^{-1} ≥ 0` was never assumed and does not follow from
`C = B^{-1}A ≥ 0`. ∎

**What the first clause buys.** von Neumann's theorem is usually proved by a minimax argument
and read as a fixed-point result. **Here it is a statement about one matrix**: the same root
carries the intensities on one side and the prices on the other, which is the pairing of
Theorem 9 of [`b65_post_keynesian.md`](b65_post_keynesian.md) evaluated at the extremum. The
proof above needs the condition `C ≥ 0`; von Neumann's own proof needs none of it and buys
generality with inequalities. **The trade is visible: assume the pencil into Perron-Frobenius's
reach and the equality is an eigenvalue fact; do not, and it is a fixed point.**

## 3. Two corollaries, and what they identify

**Corollary 16.1 (the standard commodity is the von Neumann ray).** With one product per
process and no wage, `B = I`, so `C = A` and

```
α = β = 1/λ_PF(A) = 1 + R
```

the intensity vector is the right Perron vector of `A`, which is Sraffa's standard proportions,
and the price vector is the left one, which is his price vector at the rate where the wage
vanishes. **So Corollary 12.4 of [`b67_prices_of_production.md`](b67_prices_of_production.md)
and von Neumann's duality are one statement.** Both vectors are positive by
Perron-Frobenius, which is why single production never needs the inequalities.

**Corollary 16.2 (reinvest every profit and the growth factor is the profit factor).** Fold the
real wage basket into the input matrix, `M = A + b l`, and take `B = I`. Then

```
α = β = 1/λ_PF(M) = 1 + r
```

with `r` the rate of profit of Corollary 13.2 of [`b68_value_field.md`](b68_value_field.md) and
of Theorem 14 of [`b69_okishio.md`](b69_okishio.md). **The maximal balanced growth factor of an
economy that reinvests every profit is the profit factor itself**, and the Fundamental Marxian
Theorem and Okishio's theorem are statements about that root read from the field side.

**Proofs.** Substitute `B = I` and, for the second, `A → M`, into Theorem 16(1). ∎

## 4. Placement

**What this framework reads of the world.** The coefficient of expansion and the interest
factor are one root of one pencil, the intensity vector and the price vector being its two
Perron vectors; the interest factor is the common production cycle sum; the two slackness
conditions say that a process runs only if its cycle carries that sum and a commodity is priced
only if it is not in excess; and the same root, read on two degenerate pencils, is Sraffa's
maximum rate and the rate of profit of the Marxian theorems.

**What the classical account reads of it.** The equality itself, its uniqueness, the four
conditions, and the connection between the von Neumann ray and Sraffa's standard system, which
is worked out at length in that literature.

| cell | content |
|---|---|
| **A** | `α = β`, its uniqueness, the four conditions, and the identification of the standard system with the von Neumann ray. This side derives them from one Perron root; that account has them already, the equality by name and the Sraffa connection in its own textbooks |
| **D2** | **Empty on this station.** Nothing here is a question that account asks and cannot answer; the reading below is an addition to results it already has |
| **D** | That the two factors are the two Perron vectors of one pencil, which makes the equality an instance of Theorem 9's pairing rather than a fixed point; that the interest factor is the common cycle sum, so the equality reads as the field's number on every cycle being the logarithm of the flow's growth; and the two slackness conditions read as sentences about cycles. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

**A note on what was not claimed.** The Sraffa-von Neumann connection is standard in that
literature, so §3's first corollary is recorded as a common answer and not as a distinction.
What is not standard is the route: **it arrives here as the degeneration of a pencil, and the
same degeneration gives the Marxian rate in the next line.**

## 5. Related work

The model, the four conditions and the equality are von Neumann's (1945). Kemeny, Morgenstern
and Thompson (1956) generalise it by relaxing the positivity assumption. Kurz and Salvadori
(1995) treat the Sraffa connection at length. The results this file rests on are Theorem 9 of
[`b65_post_keynesian.md`](b65_post_keynesian.md), Theorem 12 and Corollary 12.4 of
[`b67_prices_of_production.md`](b67_prices_of_production.md), Corollary 13.2 of
[`b68_value_field.md`](b68_value_field.md), Theorem 14 of [`b69_okishio.md`](b69_okishio.md),
and Theorem 15 of [`b70_joint_production.md`](b70_joint_production.md).

- Kemeny, J. G., Morgenstern, O. and Thompson, G. L. (1956). A Generalization of the von
  Neumann Model of an Expanding Economy. *Econometrica* 24(2), 115-135.
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.
- von Neumann, J. (1945). A Model of General Economic Equilibrium.
  *The Review of Economic Studies* 13(1), 1-9.

## 6. The known answer and the structural checks

`experiments/b71_von_neumann.py`, record `results/b71_von_neumann.json`, which carries the
configuration it ran under. Seed 0; a run takes a few seconds and a second run writes the same
bytes. The drawn systems are square, 2 to 6 processes, kept only when `C = B^{-1}A` is
non-negative and irreducible, which is the condition of Theorem 16. All five pass.

**B71-5, a known answer: von Neumann's theorem.** 400 systems. Both sides hold with equality
within `1.3e-15`, and **the two factors agree within `6.7e-15` on every system**. **Uniqueness
is read back too**: exactly one eigenvalue carries a positive intensity vector, on 400 of 400,
and exactly one carries a positive left vector, on 400 of 400. The price vector comes out
positive on 400 of 400, which is what the filter buys; B70 read the other side, where 52 of 400
productive joint systems admitted no positive price vector at any rate.

**B71-6, the structural checks.**

- **B71-6a, Theorem 16(1) and (2).** The root is the same read from either side of the pencil,
  within `1.1e-15`. **At the solution every process's cycle carries `log α`**, within `2.9e-15`
  on all 400 systems, every leg positive.
- **B71-6c, Theorem 16(3).** Both slackness conditions are built rather than solved for, on the
  399 systems with a positive price vector. **A process using 1.2 times the inputs and
  delivering 0.9 times the outputs of an existing one has a cycle sum below the common one on
  every construction**, smallest shortfall `0.357` in the factor, so (8') idles it. **A
  commodity that no process uses and one process makes is in strict excess, and pricing it at
  zero leaves every other condition unchanged**, within `1e-10`, on all 399.
- **B71-6d, Corollary 16.1.** 400 single production systems. The expansion factor agrees with
  the rate at which the wage vanishes, found by **scanning `det(I − (1+r)A)` for a sign change
  and bisecting, a route sharing no code with the eigen-decomposition**, within `9.8e-15`. The
  intensity vector satisfies `x = α A x` and the price vector `p = α p A` as residuals, both
  within `4.1e-15` relative, both strictly positive.
- **B71-6e, Corollary 16.2.** 400 systems, three wage baskets each. The expansion factor of the
  augmented economy equals `1 + r`, read by the same determinant route, within `5.6e-15` at all
  1,200 points.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The identifications in §3 are algebraic and no run establishes them; what the runs establish is
that the objects solve the equations claimed for them, by a route that does not restate the
computation being checked.

## 7. Scope

Square systems with `C = B^{-1}A` non-negative and irreducible, which is what puts the pencil
inside Perron-Frobenius's reach and is strictly stronger than von Neumann's own assumption.
**The general rectangular case is not solved here**: it needs a linear programme, and the two
slackness conditions are verified on constructed instances instead. It is solved in
[`b75_rectangular_programme.md`](b75_rectangular_programme.md), where the solution turns out to
sit on a square block on which this station's theorem is what holds. Consumption beyond
subsistence is not modelled, as in von Neumann; Corollary 16.2 is the version where the wage
basket is folded into the input matrix. Nothing here measures a technique, a growth rate or a
rate of interest in any economy.
