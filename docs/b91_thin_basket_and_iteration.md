# B91: what the irreducibility hypothesis buys, and how much more than the old prices decides

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b91_thin_basket_and_iteration.py`, record
`results/b91_thin_basket_and_iteration.json`, which carries the configuration it ran under. Paper
station: zero data. B69's generator, Perron solver, basket and augmented matrix and B85's cell
discriminant are imported rather than rewritten.**

## 0. The two registrations

[`b85_simultaneous.md`](b85_simultaneous.md) left two: substitutions that change the zero pattern,
where `M'` can be genuinely reducible and the hypothesis has to be checked rather than supplied;
and whether the undecided cell yields to slightly more than the prices in force. **They turn out
to be about one thing**: how much of Theorem 14 survives when its hypothesis stops being free.

## 1. Setup

`M = A + b l` with `A` the input matrix, `l` the labour vector and `b` the subsistence basket.
B85's substitutions scale columns elementwise, so they preserve the zero pattern, and its basket
is strictly positive, so `b l'` is a positive matrix and `M'` is positive whatever the
substitution did. **This station removes both**: a bundle that does not contain every intermediate
good, and a substitution allowed to set entries of `A` to zero.

**Prices are the left Perron vector of `M`.** The right one is what a Perron routine returns by
default, and the two are not interchangeable; `B91-1` checks the one this station actually used.

## 2. Theorem 35

**(1) The hypothesis is not free once the basket has zeros.** With a thin bundle and a
zero-pattern-changing substitution, `M'` is reducible on a large minority of drawn systems, where
it was irreducible on all of them before.

**(2) What irreducibility buys is the price vector, not the direction of the rate.** On the
reducible systems the forward implication of Theorem 14(1) holds without exception, while the
left Perron vector loses strict positivity on a minority of them. **A comparison of Perron roots
does not need the vector**, which is why the rate reading survives and the price reading does not.
**Where a zero appears depends on which block dominates**: a block the dominant one feeds still
prices off it, so reducibility permits a zero rather than producing one, and most of the reducible
draws here still carry a strictly positive vector.

**(3) The prices in force decide none of the undecided cell, and that is structural.** An
unchanged column returns exactly `lambda`, so the Collatz-Wielandt bracket over all columns
contains `lambda`; where every column changed, the full bracket is the changed one, which
straddles by the cell's own definition.

**(4) Iteration decides it, and the curve is the answer.** Each power iteration moves the
unchanged columns off `lambda` and tightens the bracket.

**(5) The bracket is never wrong at any iteration.** `min_j (pM')_j/p_j <= lambda' <=
max_j (pM')_j/p_j` at every strictly positive `p`, so a bracket entirely below `lambda` puts
`lambda'` below it. **The iteration is a safe early exit rather than an approximation**: stopping
early costs a verdict, never a wrong one.

**(6) What sets the number of iterations is the two things the mechanism names**: how far the
bracket has to travel, and how fast it travels.

## 3. What the checks read

**Seven criteria, all passing** at `seed 91`, 1,200 thin-basket draws and 1,368 iteration draws.

| | criterion | reading |
|---|---|---|
| `B91-1` `known_answer` | the imported pieces, and the vector used as prices | the vector this station used as prices is a left eigenvector of `M` to `<1e-9` relative; B85's own generator gives a strictly positive basket, an unchanged zero pattern and an irreducible `M'` on every draw, all three cells occupied |
| `B91-2` `own_reading` | **the hypothesis stops being free** | `M'` reducible on `466 / 1200` draws, irreducible on `1200 / 1200` before the substitution, a median of `2` entries of `A` newly zero |
| `B91-3` `own_reading` | **the rate survives and the prices do not** | on the 466 reducible draws the premise is met on `398` and the root falls on `398 / 398`; the left Perron vector is strictly positive on `386 / 466` reducible against `734 / 734` irreducible. **Both halves counted on the same draws** |
| `B91-4` `own_reading` | **the curve** | of `678` straddling draws, one iteration decides `173` (`25.5%`), two `333` (`49.1%`), three `457`, five `588` (`86.7%`), ten `661`, and all `678` within `46`. **No threshold is placed on the curve, which is the reading itself** |
| `B91-5` `instrument` | never wrong, and never decided at zero | verdicts agree with the recomputed root on `1368 / 1368`, and `0` of `678` straddling draws are decided at zero iterations. **Both implementation checks** per D35's second clause |
| `B91-6` `own_reading` | what sets the count | iterations fall with the size of the move in the root, Spearman `-0.566`, and rise with the ratio of the second modulus to the first, Spearman `+0.421`, median `3`, **on average ranks**: `661` of `678` values share a count, so a double `argsort` would order ties by position in the array. **Rank correlations rather than a fit**, since neither relation is claimed to be linear |
| `B91-7` `bookkeeping` | write-back | B85's file names this station against both registrations |

**`B91-3` caught a real fault in this station before it caught anything about the theorem.** The
first version took the Perron routine's vector as prices, and that is the right eigenvector. The
forward clause then failed on one irreducible draw in about five hundred, which is what a
violation of Theorem 14(1) would look like and is not one. **The fixture is too small for a
one-in-five-hundred fault**, so the check was moved onto the residual of the vector each draw
actually used, which catches the swap on the first draw.

**`B91-4` carries no threshold, and the first version did.** It asserted that one iteration
decides less than a fifth, a line drawn against numbers the swapped vector had produced. **A line
drawn on an estimate is the shape rule 11 forbids**, and moving it to fit the corrected numbers
would have been worse than removing it. What is asserted now is that the cell is exhausted and
that the curve has somewhere to go; how much each iteration buys is printed.

**Eight mutations, all eight caught**, two of them only after the criteria were strengthened.

## 4. Placement

**A.** That Okishio's theorem is stated for an irreducible system is its own literature's.

**D.** That the hypothesis is doing a different job than its position suggests, buying the strict
positivity of prices and not the direction of the rate; that the prices in force cannot decide a
several-column substitution for a structural reason rather than a numerical one; and **that the
Collatz-Wielandt bracket turns the undecided cell into a cost in iterations rather than a gap in
the theorem**. None of the three is in an account that reads the sign off a full re-solve.

**C is empty and this station cannot produce it**: it reads no data.

## 5. Scope

B69's generator throughout, a bundle thinned to a third of the goods, a knockout probability of
`0.6` on substituted columns, and at most 60 iterations. The counts in section 3 are properties of
the generator. **Theorem 35(3) and (5) are algebra; (1), (2), (4) and (6) are read off the draws
and are reported as such.**

## 6. Two corrections, 2026-09-13

**The zero-price gloss was wider than this station's own number.** It read that the goods outside
the dominant block price at zero; the reading is that `386` of `466` reducible draws carry a
strictly positive vector, so reducibility permits a zero and does not produce one. Which goods can
take it depends on which block dominates. **The counts did not move**, and the rate readings never
depended on the vector.

**The rank correlations were computed with a double `argsort`**, which gives tied values distinct
ranks in array order. `661` of the `678` iteration counts are tied, so this mattered: on average
ranks the two coefficients are `-0.566` and `+0.421` against `-0.545` and `+0.429`. **Both signs
and the verdict are unchanged.**
