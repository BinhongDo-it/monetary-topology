# B76: the envelope of k techniques, whose switch count grows linearly in k while the pairs grow quadratically

**Status: statement and proof, with one known answer checked by exhaustive search and four
structural checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks,
B76-5 and B76-6, are in `experiments/b76_envelope.py`, record `results/b76_envelope.json`, and
are listed in §5.**

---

## 0. The question this station answers

Two registrations asked for the same object. [`b74_roundaboutness.md`](b74_roundaboutness.md)
bounded how often **two** techniques can change places and left the envelope of three or more
open; [`b75_rectangular_programme.md`](b75_rectangular_programme.md) read the expansion factor
as an upper envelope and left its relation to B74's cost envelope open. **They are one curve.**

1. **The cost lower envelope and the wage upper envelope are one line in two coordinates** (§2,
   Theorem 21(1)). Choosing the cheapest technique and choosing the technique that pays the
   highest wage are **one instruction, not two that happen to agree.**
2. **The switch count is linear in `k`, though the number of pairs is quadratic** (§2, Theorem
   21(2)). The sequence of techniques owning successive stretches of the envelope is a
   Davenport-Schinzel sequence, so its length is bounded by `λ_s(k)`, with `s` the pairwise
   crossing count that B74's Theorem 19(3) supplies. **`λ_1(k) = k` and `λ_2(k) = 2k − 1`,
   against `k(k−1)/2` pairs.** Adding a technique adds a bounded number of switches, not a
   number growing with how many techniques are already there.
3. **Reswitching happens on the envelope exactly when some pair crosses more than once** (§2,
   Theorem 21(3)). At `s = 1` the owner sequence admits no repeated symbol, so **no technique
   can leave and return, with any number of techniques.** B74's domain condition, stated there
   for one pair, is here the condition for no reswitching anywhere.
4. **B75's expansion factor is this envelope's right-hand endpoint** (§2, Theorem 21(4)).
   `max_i R_i` is where the envelope reaches zero, the technique owning the right end is the one
   attaining it, and the technique owning the left end is a different one. **So the growth
   factor and the cost envelope are not two constructions to be related. They are one curve and
   two of its points.**

## 1. Setup

`k` techniques. Two carriers, and the theorem is stated on whichever makes each clause visible.

**Dated labour**, as in B74: technique `i` has cost `C_i(x) = Σ_t l^i_t x^t` with `x = 1 + r`.
The **lower envelope** is `C(x) = min_i C_i(x)`.

**Square systems**, as in B67: technique `i` is `(A_i, l_i)` on `m` goods, and with numeraire
basket `d` its wage curve is

```
w_i(r) = 1 / ( l_i [I − (1 + r) A_i]^{-1} d )
```

which vanishes at `R_i = 1/λ_PF(A_i) − 1`. The **upper envelope** is `w(r) = max_i w_i(r)`.

**The owner sequence.** Read the envelope from low `r` to high and write down which technique
attains it on each maximal stretch. That sequence, not the curve, is what the counting is about.

## 2. Theorem 21

**Theorem 21.** With the setup of §1:

1. **(One line, two coordinates.)** The cost of one unit of the numeraire under technique `i` is
   `1 / w_i(r)`. Since `t ↦ 1/t` is strictly decreasing on the positives, `argmin_i` of the cost
   and `argmax_i` of the wage are the same technique at every rate, and the lower envelope of
   costs is the reciprocal of the upper envelope of wages.

   *Proof.* Immediate from the definitions and the monotonicity of the reciprocal. ∎

2. **(Davenport-Schinzel bounds the switches.)** If every pair of curves meets at most `s`
   times, the owner sequence contains no alternating subsequence `a … b … a … b …` of length
   `s + 2`. It is therefore a Davenport-Schinzel sequence of order `s` over `k` symbols, so it
   has at most `λ_s(k)` terms and the envelope has at most `λ_s(k) − 1` switch points.

   *Proof.* Suppose the owner sequence contained an alternation of length `s + 2`. Between two
   consecutive terms of it the owner passes from `a` to `b` or from `b` to `a`, and both curves
   are defined throughout, so curve `a` and curve `b` must meet somewhere in between. An
   alternation of length `s + 2` has `s + 1` such gaps, giving `s + 1` meetings and
   contradicting the hypothesis. The rest is the definition of a Davenport-Schinzel sequence. ∎

   **Where `s` comes from.** B74's Theorem 19(3): on dated labour, two techniques meet at the
   positive roots of the difference of their cost polynomials, and that count is at most the
   number of sign changes in the difference's coefficients. **So the bound on the whole
   envelope is read off the same labour profiles, with no rate of profit in it.**

   **What the bound says, and it is not tightness.** `λ_1(k) = k` and `λ_2(k) = 2k − 1`, both
   linear, while the number of pairs is `k(k−1)/2`. **The naive count, that every pair can
   contribute its own crossings, is quadratic and wrong**: most pairwise crossings are not on
   the envelope, because one of the two curves is above some third curve there.

3. **(No pair crossing twice is enough for no reswitching, and is not necessary.)** At `s = 1`
   the owner sequence admits no alternation of length three, which for a sequence with no two
   equal terms in a row means no symbol occurs twice. **So no technique leaves the envelope and
   returns.** At `s ≥ 2` it can, and §5 exhibits it, **but it need not**: a pair crossing twice
   contributes nothing to the envelope where a third curve is below both of them, which is the
   mechanism §2 clause 2 already names for why the pairwise count overstates. **So `s = 1` is
   sufficient and not necessary**, and the clause title said "exactly when" until 2026-09-13.
   The bound and every count in §3 are unchanged; what was too strong was the converse.

   *Proof.* An order-one sequence forbids `a … b … a`; with no two equal terms adjacent, a
   symbol occurring twice would produce exactly that pattern. ∎

   **This is B74's clause 4 read on the whole envelope.** There, one crossing per pair meant one
   number orders *that pair*. Here it means reswitching cannot happen at all, however many
   techniques are in the book.

4. **(B75's factor is the right-hand endpoint.)** `w_i(r) > 0` exactly for `r < R_i`, so the
   envelope is positive exactly for `r < max_i R_i` and vanishes there. Near that rate only a
   technique attaining `max_i R_i` has a positive wage, so it owns the right end; the technique
   owning the left end is `argmax_i w_i(0)`; and the two are in general different.

   *Proof.* The first two statements are the definition of the envelope and of `R_i`. The last
   is exhibited in §5, where the two ends have different owners. ∎

   **What this settles.** B75's Theorem 20(3) read `α` as the upper envelope of sub-economies'
   own factors, and its sweep had a kink where the owner changed. **That kink is a switch point
   of this envelope, at its right-hand end.** The two envelopes were never two objects.

## 3. Placement

**What this framework reads of the world.** The cost and wage envelopes are one curve; its
owner sequence is a Davenport-Schinzel sequence whose order is the pairwise crossing count, so
the switch total is linear in the number of techniques; reswitching anywhere on the envelope is
equivalent to some pair crossing twice; and the expansion factor of the growth problem is this
curve's right-hand endpoint.

**What the classical account reads of it.** Wage curves and their envelope as the
cost-minimising choice of technique; reswitching, with examples; the order of cultivation and
of technique changing with distribution. Davenport-Schinzel sequences and their lower-envelope
reading are the combinatorialists'.

| cell | content |
|---|---|
| **A** | Wage curves, the envelope as the cost-minimising choice, reswitching itself, and the order changing with distribution. B67 and B72 have each recorded a share of this already. **Recorded as this framework being right, not as a debt** |
| **D2** | **How many switch points an envelope of `k` techniques can carry.** That falls inside a theory of the choice of technique, and that literature answers it with examples rather than with a bound, as B74 already recorded for the two-technique case. The bound here is linear where the obvious count is quadratic, and the tool that gives it is borrowed and credited |
| **D** | That the owner sequence is a Davenport-Schinzel sequence and its order is B74's sign-change count; that no reswitching anywhere is equivalent to no pair crossing twice; and that B75's expansion factor is this same envelope's right-hand endpoint rather than a second construction. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 4. Related work

The wage curve, the envelope and reswitching are Sraffa's and the Cambridge literature's, and
B67 and B74 read their examples back. The sequences, and the observation that the intervals of
a lower envelope labelled by the function attaining it form one, are Davenport and Schinzel's;
the sharp asymptotics for higher orders are a large later literature that this station does not
need, because its carriers have `s ≤ 2`.

- Davenport, H. and Schinzel, A. (1965). A combinatorial problem connected with differential
  equations. *American Journal of Mathematics* 87(3), 684-694.
- Samuelson, P. A. (1966). A Summing Up. *Quarterly Journal of Economics* 80(4), 568-583.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 5. The known answer and the structural checks

`experiments/b76_envelope.py`, record `results/b76_envelope.json`, which carries the
configuration it ran under. Seed 0; a run takes about four seconds and a second run writes the
same bytes. All five pass.

**B76-5, a known answer: the two Davenport-Schinzel numbers, by exhaustive search.** A sequence
over `k` symbols with no two equal terms in a row and no alternation of length `s + 2` is one of
order `s`. **Searching all of them for `k` up to 5 returns `λ_1(k) = k` and `λ_2(k) = 2k − 1` on
every `k`**: 1 and 1, 2 and 3, 3 and 5, 4 and 7, 5 and 9. **No table is quoted**; the two
formulas Theorem 21(2) uses are established here by enumeration.

**B76-6, the structural checks.**

- **B76-6a, the bound, and the grid as the floor.** Families of degree-two cost polynomials
  drawn 200 per size, so every pair crosses at most twice, which the sign-change count confirms
  at 2. **The switch count never exceeds `2k − 2`**, and the gap is wide: `k = 3` reaches 2
  against 4, `k = 6` reaches 4 against 10, `k = 10` reaches 3 against 18, with 90 ordered pairs.
  **The drawn maxima do not grow with `k` at all**, which is the linearity showing through.
  **The grid is this instrument's floor**, since two curves crossing twice inside one interval
  read as crossing zero times, so the owner sequence was read again on a grid four times denser:
  **the same sequence on 400 of 400 families**.
- **B76-6b, the reswitching dichotomy.** 1200 families of degree-one costs, **0 with a
  return**; 1200 of degree-two, **16 with a return**. A search also finds owner sequences that
  are not admissible at order one, **and both ways of failing occur**: at `k = 3` the sequence
  `[2, 0, 2, 1]` is both too long and has a repeated symbol; at `k = 4` the sequence
  `[3, 0, 1, 0]` has a repeated symbol at a length order one would still allow. **Either breaks
  order one**, which is what shows the order must come from the pairwise crossing count.
- **B76-6c, the two ends.** A carrier of five square systems, one per degree of mechanisation:
  the input matrix scaled up and the labour vector down, **so the wage curves cross by
  construction rather than one technique dominating, which is what drawing at random produces**.
  The envelope changes owner four times, sequence `[4, 3, 2, 1, 0]`. **The right end is owned by
  the technique with the largest maximum rate** and `max_i R_i` is the envelope's right-hand
  zero within `1e-12`; **the left end is owned by the technique with the highest wage at a zero
  rate, and it is a different technique**.
- **B76-6d, one instruction not two.** The same carrier read at 3000 rates: **the cheapest
  technique and the highest-paying technique are the same technique at every one of them**,
  3000 of 3000.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts are counts on drawn or constructed families; that 16 of 1200 drawn degree-two
families reswitch is a property of the drawing, not a frequency among techniques used anywhere.

## 6. Scope

A finite set of techniques, indexed discretely: a continuum of techniques, and equally the
continuum of land qualities registered by B72, is a different object and is done in
[`b77_continuum.md`](b77_continuum.md), where the bound of Theorem 21(2) is shown true at every
`k` and empty in the limit. The carriers have `s ≤ 2`, so the higher-order Davenport-Schinzel bounds, which are not
linear, are never needed and are not checked. Which techniques are in the book at all is given
from outside, as at every station in this family. Nothing here says which technique ought to be
chosen, and nothing here measures a technique, a wage curve or a switch point in any economy.
