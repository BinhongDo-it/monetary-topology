# B94: both factors on a rectangular economy are eigenvalues, of a block that has to be found

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b94_rectangular_closed_form.py`, record `results/b94_rectangular_closed_form.json`,
which carries the configuration it ran under. Paper station: zero data. B75's game solver and
factors and B82's rectangular generator are imported rather than rewritten.**

## 0. The registration

[`b82_rectangular_parts.md`](b82_rectangular_parts.md) closed B80's two-family registration and
left one of its own: **whether either family has a closed form on a rectangular economy**, since
the Perron route needs principal blocks of one matrix and there are none here, so the factors are
read by a programme rather than by an eigenvalue.

## 1. Theorem 38

**(1) Both factors are generalised eigenvalues.** At the optimum the programme is tight on a square
sub-pair of processes and goods, so the factor is a root of `det(B_{S,G} − γ A_{S,G}) = 0`:

```
alpha = the largest admissible generalised eigenvalue over square sub-pairs
beta  = the smallest
```

**(2) The two factors are the two ends of one finite set.** That is the sharpest form B82's
two-family statement takes here: the families differ in which index set they range over, and the
factors differ only in the direction the extremum is taken.

**(3) The feasibility screen is what makes this a closed form and not a formula.** A sub-pair's
eigenvalue need not be attainable by any non-negative intensity vector on the whole economy.
Without the screen the maximum overshoots badly.

**(4) The block is usually one cell.** So the expansion factor is most often one process's own
output-to-input ratio, **chosen by a search rather than computed by one**.

**(5) This is the chain's own shape read once more.** B87 has demand choosing which lands, B89
which cell of a counting identity, B93 which member owns the envelope, and here which block carries
the factor. **The continuous part is an eigenvalue and the work is combinatorial.**

## 2. What the checks read

**Seven criteria, all passing** at `seed 94`, 60 drawn rectangular economies.

| | criterion | reading |
|---|---|---|
| `B94-1` `known_answer` | B75's published pair | all four values, `alpha` and `beta` on both examples, come back to six places through the closed form rather than the bisection |
| `B94-2` `own_reading` | **alpha is an eigenvalue** | agrees with the bisection on `60 / 60`, worst gap `1.2e-07` |
| `B94-3` `own_reading` | **and beta is the other end** | agrees on `60 / 60`, worst gap `5.2e-08` |
| `B94-4` `own_reading` | **the screen is load-bearing** | dropping it overshoots on `54 / 60` economies by a median factor of `3.565`. **And it does a second job**: complex generalised eigenvalues turn up on `38 / 60` economies, and keeping their real parts moves the answer on `0`, so the imaginary-part filter is redundant here and the screen was rejecting them all along |
| `B94-5` `own_reading` | **which block** | `1x1` on `28`, `2x2` on `15`, `3x3` on `10`, `4x4` on `5`, `5x5` on `2`. More than one size occurs, so the block is found and not fixed by the shape |
| `B94-6` `instrument` | the search is complete | the visit count equals `Σ_k C(n,k)C(m,k)` on `60 / 60`, median `83` and largest `923`. Everything above is an extremum over that set |
| `B94-7` `bookkeeping` | write-back | B82 names this station |

**B94-4's second half was a mutation that turned out not to be a fault.** Removing the
imaginary-part filter changes no answer, and rather than adding a probe for a fault that is not
there, the station measures it: the screen rejects every real part of a complex root that could
have won. **Eight mutations, seven caught and one measured as redundant.**

## 3. Placement

**A.** The von Neumann expansion factor and the interest factor, and their reading as a matrix
game, are the literature's.

**D.** That both are generalised eigenvalues of a square sub-pair on a rectangular economy, so the
Perron route's absence costs a search rather than a formula; that the two are the two ends of one
finite set; and **that the block carrying the factor is usually a single process-good cell**. None
sits in an account that reads the factors only off a programme.

**C is empty and this station cannot produce it**: it reads no data.

## 4. Scope

B82's generator, economies from three to six processes and goods, densities from `0.3` to `0.5`,
and an agreement tolerance of `1e-5` against a bisection whose own floor is coarser than that. The
size distribution in section 2 is a property of the generator. **Theorem 38(1) to (3) are argument;
(4) is read off the draws.** The enumeration is exponential in the size of the economy, which is
what "the work is combinatorial" costs and is why the draws stop at six.
