# B85: several columns at once, where Okishio's equivalence becomes an implication

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b85_simultaneous.py`, record `results/b85_simultaneous.json`, which
carries the configuration it ran under. Paper station: zero data. B69's system
generator, Perron solver, basket and substitution form are imported rather than
rewritten, so a disagreement between the two stations is a real one.**

## 0. The question this station answers

[`b69_okishio.md`](b69_okishio.md) proved Theorem 14(1): with the real wage basket
held fixed, the sign of the change in the general rate of profit is the sign of the
cost saving at the prices in force, **on the one column that changed**. It is an
equivalence. Its scope section registered the several-column case as "the same
argument with `p M' ≤ λ p` holding on a set of columns".

**Half of that is right, and the half that is wrong is the interesting half.**

## 1. Setup

B69 §1 throughout: technology `(A, l)` productive and irreducible, basket `b ≥ 0`,
augmented matrix `M = A + b l`, `1 + r = 1/λ_PF(M)`, `p` the left Perron vector. A
**simultaneous substitution** on a set `S` of industries replaces each column `k in
S` by a new method, leaving the rest alone. Write `M'`, `λ'`, `r'`.

## 2. Theorem 29

**(1) The forward implication carries over unchanged.** If every column in `S` is no
dearer at the prices in force and at least one is strictly cheaper, then `p M' ≤ λ p`
with strict inequality somewhere, so for irreducible `M'` the Collatz-Wielandt step
gives `λ' < λ` and `r' > r`. **Not a word of B69's argument changes.**

**(2) The converse does not.** A set in which some columns get dearer and others
cheaper can raise the rate. **1,461 of 4,092 drawn several-column substitutions do**,
the largest lifting the rate from `0.257` to `0.623` on four columns of which one got
dearer. So **the equivalence of Theorem 14(1) is not the `|S| = 1` case of a
several-column equivalence. It is a property of `|S| = 1`**, and what makes it one is
that with a single column the prices in force see everything that moved.

**(3) What survives is a bracket over the columns that moved.** Write

```
sigma = min over k in S of (p M')_k / p_k,     rho = max over k in S of (p M')_k / p_k
```

Both are computable at the prices in force, with no re-solving. Then

| | at the prices in force |
|---|---|
| `rho ≤ λ`, one strict | `r' > r` |
| `sigma ≥ λ`, one strict | `r' < r` |
| `sigma < λ < rho` | **not decided** |

**At `|S| = 1` the two ends coincide and the third cell is empty**, which is
Theorem 14(1). As `S` grows the third cell fills.

**(4) The bracket over *every* column is true and useless.** An unchanged column has
`(p M')_j = λ p_j` exactly, so the moment one column is left alone that bracket
contains `λ` and decides nothing. **This is not a technicality: the first version of
the check used it and reported that the prices decide nothing even at one column**,
contradicting Theorem 14(1). The contradiction is what showed the object was wrong.

**(5) Irreducibility comes from the basket, not from the substitution.** With `b > 0`
and `l' > 0` the outer product `b l'` is strictly positive, so `M'` is a positive
matrix whatever the substitution did to `A`. That is B69's own sufficient condition,
and it is why the hypothesis of (1) is free here.

## 3. What the checks read

**Seven criteria, all passing** at `--seed 85 --systems 120`, 5,532 substitutions.

| | criterion | reading |
|---|---|---|
| `B85-1` `known_answer` | it reduces to B69 at one column | the sign of the change is the sign of the saving on `1440 / 1440`, on B69's own systems and baskets with B69's solver |
| `B85-2` `own_reading` | the forward half | `601` draws have every changed column cheaper, and the rate rises on all `601`. **The premise count is in the verdict**: zero counterexamples is free on zero cases |
| `B85-3` `own_reading` | **the converse fails** | `1461` of `4092`, found rather than assumed |
| `B85-4` `own_reading` | the three cells | below `λ`: `1306` draws, rate rises `1306`. Above: `1360`, rises `0`. **Straddling: `2866`, rises `1461` and falls `1405`.** No single-column draw straddles |
| `B85-5` `own_reading` | how often the old prices decide | 1 column `1440/1440`, 2 columns `705/1440`, 3 columns `375/1440`, 4 columns `146/1212` |
| `B85-6` `instrument` | the hypothesis | the basket and the labour vector are strictly positive on `5532/5532`, so `M'` is positive. **The irreducibility computation cannot fail while that holds**, so it is a check on the test and not a third reading (`D35`) |
| `B85-7` `bookkeeping` | B69's registration | discharged and written back the same round |

**Four criteria carry a clause whose job is to be able to fail.** `B85-2` counts the
draws that reached its premise. `B85-3` has to find its case, and would have recorded
"not found" rather than "does not exist". `B85-4` requires both outcomes inside the
undecided cell, or the cell is decorative, and requires the single-column draws not
to straddle, which is the clause that tells the right bracket from the wrong one.
`B85-6` names which of its clauses cannot fail instead of listing three as equals.

## 3a. The same monotonicity with the other thing held fixed

This station holds the basket fixed and reads the rate. **Hold the rate fixed and
read the prices instead and the same Perron monotonicity gives the non-substitution
theorem**, done on 2026-09-13 at [`b86_non_substitution.md`](b86_non_substitution.md),
Theorem 30: the componentwise minimum of the price vectors over techniques is
attained by a single technique, which is what makes "the cheapest technique"
definable without naming a demand vector.

```
B85   basket fixed, rate read      a cheaper column raises r
B86   rate fixed, prices read      a cheaper column lowers every price
```

**Two classical theorems, one monotonicity, two different things held fixed.**

## 4. Placement

**A.** Okishio's theorem, its setting and the Collatz-Wielandt step are B69's and the
literature's.

**D.** That the equivalence is a property of the one-column case rather than a
special case of a general one, that the discriminant available at the prices in force
is a bracket over the moved columns, and **that the share of substitutions those
prices can decide falls from all of them to about a tenth as four columns move at
once**. The last is a counted object with no analogue in an account that has no graph
and no bracket in it.

**C is empty and this station cannot produce it**: it reads no data.

## 4a. Both registrations, answered 2026-09-13

**Done at** [`b91_thin_basket_and_iteration.md`](b91_thin_basket_and_iteration.md), and the two
turn out to be about one thing: how much of the theorem survives when its hypothesis stops being
free.

- **This station's hypothesis was supplied by its generator.** A strictly positive basket against
  a strictly positive labour vector makes `b l'` positive, so `M'` is a positive matrix whatever
  the substitution did. Thin the basket to a bundle that does not contain every intermediate good
  and let the substitution set entries of `A` to zero, and **`M'` is reducible on 466 of 1,200
  draws** where it was irreducible on all 1,200 before.
- **What irreducibility buys is the price vector, not the direction of the rate.** On those 466
  the forward implication holds on 398 of 398 draws whose premise is met, while the left Perron
  vector is strictly positive on 386 of 466 against 734 of 734 irreducible ones. **A comparison
  of Perron roots does not need the goods outside the dominant block, and those price at zero.**
- **One power iteration decides a quarter of the undecided cell**, 173 of 678, two decide half,
  five decide 87%, and all 678 are decided within 46. **The prices in force decide none of it,
  and that is structural**: an unchanged column returns exactly `lambda`, so the bracket contains
  it. The bracket is never wrong at any iteration, which is Collatz-Wielandt, so the iteration is
  a safe early exit rather than an approximation.

## 5. Scope

Single-product industries, circulating capital, no joint production and no fixed
capital, as in B67, B68 and B69. Substitutions are elementwise rescalings of existing
columns, which preserves the zero pattern; a substitution that changed the pattern is
a different family and is not drawn here. The counts in section 3 are properties of
that family and of the generator, not of any economy. **What is not family-specific
is Theorem 29(1) to (4)**, which are algebra.
