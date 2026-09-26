# B82: the two families on a rectangular economy, and they are two index sets

**RUN: 2026-09-12. Statement and proof below. Checks in
`experiments/b82_rectangular_parts.py`, record `results/b82_rectangular_parts.json`,
which carries the configuration it ran under. Paper station: zero data. The solver
is B75's and the independence machinery is B80's; both are imported.**

## 0. The question this station answers

B80 proved, for a simple economy with `B = I`, that the expansion factor and the
interest factor are read off two different families of parts, and registered the
general rectangular case: the support argument should still hold, but the parts
are no longer principal blocks of one matrix, so the Perron route is unavailable.

**The support argument does hold, and the general statement is sharper than the
registration expected.** On a simple economy both families are families of goods,
because `B = I` makes a process and a good the same index. In general they are
not: **one family is a family of process sets, the other a family of good sets.**

## 1. Setup

`n` processes, `m` goods, non-negative `A` and `B`, both `n × m`. Write
`produced(T) = { j : B[i,j] > 0 for some i in T }` and
`consumed(T) = { j : A[i,j] > 0 for some i in T }` for a set of processes `T`.

```
TEP   max alpha  subject to  x'B >= alpha x'A,   x semi-positive over processes
EEP   min beta   subject to  Bp <= beta Ap,      p semi-positive over goods
```

## 2. Theorem 27

**(1) The quantity programme confines the support of `x` to a process set that
produces everything it consumes.** Let `T = supp(x)`. For a good `j` outside
`produced(T)` the constraint reads `0 >= alpha (x'A)_j`, so `(x'A)_j = 0` and `T`
consumes nothing it does not produce:

```
consumed(T)  subset  produced(T)
```

**(2) The price programme confines the support of `p` to a good set no process
produces into without consuming from.** Let `S = supp(p)`. A process `i` that
consumes nothing in `S` has `(Ap)_i = 0`, so the constraint reads `(Bp)_i <= 0`
and `i` produces nothing in `S` either:

```
no i with  produces into S  and  consumes nothing from S
```

**(3) So the two factors are two extrema over two families, over two index
sets.**

```
alpha_0 = max over admissible process sets T  of  alpha(T, produced(T))
beta_0  = min over admissible good sets S     of  beta(rows touching S, S)
```

**(4) `B = I` is what collapses the distinction.** With `B = I` a process
produces exactly its own good, so `produced(T) = T` and the first family's image
under `T -> produced(T)` is a family of goods. It is then B80's family of
independent subsets, and both statements can be made over goods. **That
identification is a property of the simple case and not of the model**, which is
why B80's version could not be read off as the general one.

## 3. Placement

**Against the von Neumann literature.** The model, the two programmes and the two
example economies are theirs, and B80 already recorded the reading back. **A.**
What is added here is the general form of the two families and the observation
that they are indexed by different sets, which that literature does not state
because it works either on the square irreducible case, where the question does
not arise, or on the simple case, where `B = I` hides it. **D.**

**C is empty, and this station cannot produce it**: it reads no data, so no point
prediction of any other account is scored here.

## 4. Related work

von Neumann (1945); Kemeny, Morgenstern and Thompson (1956, *Econometrica* 24,
115-135) for the generalisation that admits reducible economies; QuantEcon, *Von
Neumann Growth Model (and a Generalization)*, for the two worked economies. B75
for the programme and its solver, B80 for the simple case.

## 5. The known answers and the structural checks

**Six criteria, all passing** at `--seed 82 --reps 8`.

| | criterion | reading |
|---|---|---|
| `B82-1` `known_answer` | both published economies | `3 × 4`: `alpha = beta = 1.259921050`; `5 × 6`: `alpha = 1.259921050`, `beta = 1.000000000`, both inside `1e-8` of the published pair |
| `B82-2` `instrument` | **it specialises to B80** | on 8 simple economies the image of the process family under `T -> produced(T)` is B80's family of independent good sets, 8 of 8. **A disagreement would mean one of the two stations has the condition wrong** |
| `B82-3` `own_reading` | **the two families** | 9 rectangular economies: `alpha_0` is the max over admissible process sets in 9 of 9, worst departure `1.3e-14`; `beta_0` is the min over admissible good sets in 9 of 9, worst `3.8e-15` |
| `B82-5` `own_reading` | **two index sets** | the image of the process family and the good family are different families in **15 of 16** rectangular economies |
| `B82-6` `own_reading` | the solution's own supports | the intensity support satisfies the process condition and the price support the good condition in 9 of 9. **Neither condition is imposed anywhere in the solver; both are read off what it returns** |
| `B82-7` `bookkeeping` | B80's registration | named, with the way the answer is sharper than it |

**`B82-4` is not a hole left by a withdrawn reading.** The two halves of the
statement are checked in one sweep because they share the economies they are
checked on, and the numbering was left as it stood rather than renumbered after
the merge.


## The closed-form registration, answered 2026-09-13

**Both factors are eigenvalues after all**, done at
[`b94_rectangular_closed_form.md`](b94_rectangular_closed_form.md). At the optimum the programme is
tight on a square sub-pair of processes and goods, and the factor is a generalised eigenvalue of
that pair, a root of `det(B_{S,G} - gamma A_{S,G}) = 0`:

```
alpha = the largest admissible generalised eigenvalue over square sub-pairs
beta  = the smallest
```

Verified against this station's own bisection on 60 drawn economies and against B75's two published
examples. **What makes it a closed form rather than a formula is the feasibility screen**: a
sub-pair's eigenvalue need not be attainable by any non-negative intensity vector on the whole
economy, and dropping the screen overshoots on most economies. **And the block is usually one
cell**, so the expansion factor is most often one process's own output-to-input ratio, chosen by a
search rather than computed by one.

## 6. Scope

Enumeration is over subsets of processes and of goods, so the drawn economies are
capped at six of each: the statement is about which family, not about scale.
Nothing here computes the parts in closed form, and on a rectangular economy no
closed form is claimed: the Perron route B80 used needs principal blocks of one
matrix and there are none here. Nothing in this station measures an economy.
