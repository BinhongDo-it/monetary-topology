# B74: roundaboutness is the degree of a polynomial, and how often the order can reverse is bounded by a sign count

**Status: statement and proof, with one known answer from the literature and three structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B74-5 and
B74-6, are in `experiments/b74_roundaboutness.py`, record
`results/b74_roundaboutness.json`, and are listed in §5.**

---

## 0. The question this station answers

[`b67_prices_of_production.md`](b67_prices_of_production.md) Corollary 12.3 already says that
no quantity read off the field orders techniques independently of the rate, and the average
period of production is such a quantity. **So "order techniques by roundaboutness" is already
settled and this station does not prove it again.** Three things were left, and they are what
is done here.

1. **Roundaboutness is a degree, and the degree is the one thing about a technique that does
   not move with the rate** (§2, Theorem 19(1)). On the dated position graph of B69 Corollary
   14.2 a technique's cycle crosses one date edge per period of lag, each date edge carries
   `log(1 + r)`, and the number of them is the degree of the cost polynomial. **The tradition
   was right that there is a number here. It was wrong about what the number does.**
2. **How often two techniques can change places is bounded by a sign count** (§2, Theorem
   19(2) and (3)). Switch points are the roots of the difference of the two cost polynomials,
   so by Descartes' rule their number is at most the number of sign changes in the coefficients
   of that difference, with the same parity. **That bound mentions no rate of profit and no
   price. It is read off the two labour profiles alone.**
3. **The Austrian intuition has an exact domain, and this is it** (§2, Theorem 19(4)): the two
   dated labour profiles cross once. There one number does order the two techniques and the
   order reverses at most once. Two crossings or more and it does not. **The intuition is not
   false, it is a statement whose domain was never written down.**
4. **The average period does not even track the thing it was introduced to stand for** (§2,
   Theorem 19(5)). That it moves with the rate is known, and that its ordering is opposite on
   the two sides of a pair of switch points is Fratini's (2012) reading of the Hicks-Malinvaud
   measure. **What is added here is the speed and the mismatch**: `APP' = Var(t)/x`, so the
   measure rises exactly as fast as the variance of the date under the discounted weights; and
   its ordering can reverse at a rate that is not a switch point at all, which is a case that
   does not arise when the reversal is read off a pair of switch points to begin with.

## 1. Setup

**Dated labour.** By Theorem 12(2) of B67 the price system with a uniform rate reduces to dated
labour, and by Corollary 14.2 of B69 the dates are positions in the graph. A technique is a
finite list of labour inputs `l_t ≥ 0`, `t = 0 … T`, where `l_t` is applied `t` periods before
one unit of output, with `l_T > 0`. With the wage as the unit of account and `x = 1 + r`, the
cost of the output is

```
C(x) = Σ_t l_t x^t
```

**The average period of production.** Böhm-Bawerk's idea, in the weighted form Hicks (1946)
gave it and Malinvaud developed, which Fratini (2012) writes as
`θ = Σ t u_t (1 + ρ)^t / Σ u_t (1 + ρ)^t`. In the notation here:

```
APP(x) = Σ_t t l_t x^t / Σ_t l_t x^t
```

At `x = 1` this is the labour-weighted mean date; away from it the weights move. Hicks's step
was to weight by shares of cost rather than shares of labour, which is what puts `x` inside.

**Two techniques.** `C₁` and `C₂` for the same unit of output, and their difference
`D(x) = C₁(x) − C₂(x)`. A **switch point** is a rate `r > 0`, that is an `x > 1`, at which the
two are equally costly.

## 2. Theorem 19

**Theorem 19.** With the setup of §1:

1. **(Roundaboutness is a degree.)** In the dated position graph the cycle carrying `l_t`
   crosses `t` date edges, each of weight `log(1 + r)`, so the longest such cycle of a technique
   crosses `T` of them, and `T = deg C`. **`T` is read from the profile with no price in it, so
   it is the one quantity here that does not move with `r`.**

   *Proof.* Each period of lag is one date edge by Corollary 14.2, and each date edge carries
   `log(1 + r)` by Theorem 12(2): this is why the cost of `l_t` is `l_t x^t` and not `l_t` times
   anything else. The largest `t` with `l_t > 0` is both the longest lag and the degree of `C`.
   The profile is a list of labour quantities, so no price enters it. ∎

2. **(Switch points are roots.)** The two techniques are equally costly at `x` exactly when
   `D(x) = 0`, so the switch points are the roots of `D` with `x > 1`, and between consecutive
   roots the sign of `D` is constant, that is one technique is strictly the cheaper over that
   whole interval.

   *Proof.* Equality of `C₁` and `C₂` is `D = 0` by definition; `D` is a polynomial, hence
   continuous, so it keeps its sign on an interval carrying no root. ∎

3. **(Descartes bounds the reversals.)** Let `s` be the number of sign changes in the
   coefficient sequence of `D` with zeros skipped. Then the number of positive roots of `D`,
   counted with multiplicity, is at most `s` and differs from `s` by an even number. **Switch
   points are positive roots, so their number is at most `s` as well.**

   *Proof.* This is Descartes' rule of signs applied to `D`. The only step belonging to this
   station is that the object it is applied to is a difference of two dated labour profiles, so
   `s` is computed from labour quantities alone. Switch points require `x > 1` and positive
   roots require `x > 0`, so the former are a subset of the latter and inherit the bound. ∎

4. **(The domain of the intuition.)** If `s = 1` then `D` has exactly one positive root, so
   there is at most one switch point and the cost ordering reverses at most once over all
   rates: **one number does order these two techniques.** If `s ≥ 2` then two switch points are
   possible, and where they occur the cheaper technique at a low rate is again the cheaper at a
   high one.

   *Proof.* With `s = 1` clause 3 gives at most one positive root and the parity clause gives
   exactly one, so `D` changes sign once on `x > 0` and the ordering reverses at most once on
   `x > 1`. With `s ≥ 2` the bound permits two and §5 exhibits pairs attaining it, Samuelson's
   among them. ∎

5. **(The average period moves, and not where the cost moves.)** `APP` is constant in `x` only
   if the profile carries a single date. Its ordering between two techniques can reverse as `x`
   rises, and **the rate at which it reverses need not be a root of `D`.**

   *Proof.* Write `APP = N/M` with `N = Σ t l_t x^t` and `M = Σ l_t x^t`. Then

   ```
   M² · APP'(x) = (Σ t² l_t x^{t-1})(Σ l_t x^t) − (Σ t l_t x^t)(Σ t l_t x^{t-1})
                = x^{-1} · [ E(t²) − E(t)² ] · M²
   ```

   where `E` is the expectation under the weights `w_t = l_t x^t / M`. **The bracket is the
   variance of the date under those weights**, so `APP' = Var(t)/x ≥ 0`, with equality exactly
   when the weights sit on a single date. So `APP` is non-decreasing in `x` and strictly
   increasing unless the profile is a point, and §5's two non-moving pairs out of 600 are
   exactly that case, both legs on one date. The last clause is independent: `APP₁ − APP₂` and
   `D` are different functions of `x` with no algebraic relation forced between their zeros, and
   §5 exhibits pairs whose `APP` ordering reverses at a rate where `D` has no root at all. ∎

**What the five clauses are together.** The tradition put one number on a technique and asked
it to order techniques. Clause 1 says the number exists and is a degree. Clause 3 says what
that kind of number can buy, namely a bound on how often the order can turn over. Clause 4 says
when it buys an ordering outright. Clause 5 says that the particular number the tradition
chose, the average period, is not even the one that tracks the ordering. **The bound in clause
3 is the part with no counterpart in that literature: it is a statement about two techniques
that mentions the rate of profit nowhere.**

## 3. Placement

**What this framework reads of the world.** A technique's roundaboutness is the number of date
edges its longest cycle crosses, which is the degree of its cost polynomial; two techniques'
switch points are the positive roots of the difference of those polynomials; the number of
those roots is bounded, with matching parity, by the sign changes of that difference; the
ordering by a single number is valid exactly where the profiles cross once; and the average
period rises with the rate at a speed equal to the variance of the date under the discounted
weights.

**What the Austrian and the Cambridge accounts read of it.** That production takes time and
that techniques differ in how much; that the Hicks-Malinvaud average period depends on the rate
of interest and that the ranking it gives at one switch point is opposite to the ranking at the
next, so it does not express a degree of roundaboutness; and Samuelson's pair with two switch
points at 50 and 100 per cent.

| cell | content |
|---|---|
| **A** | That the average period moves with distribution and does not express roundaboutness, and that its ranking is reversed between two switch points. That is Fratini's reading of Hicks-Malinvaud and that side has it; here the first half comes out as `APP' = Var(t)/x`, which says the same thing and says how fast |
| **D2** | **How many switch points a given pair can have.** "How often can the ordering reverse" falls squarely inside a theory of the choice of technique, and that literature answers it with examples rather than with a bound. Descartes on the difference of two profiles gives the bound in one line, and the framework's own dated positions are what put the profiles in a form a sign count applies to |
| **D** | That roundaboutness is a degree in the dated position graph, and that the bound and its parity are read off labour quantities with no price in them; that the exact domain of the Austrian ordering is "the profiles cross once"; that `APP' = Var(t)/x`, so the measure's speed is a variance; and that the average period's ordering can reverse where there is no switch point at all, a case outside a reading that takes the reversal between two switch points. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

**Corollary 12.3 and this station.** That corollary says no quantity read off the field orders
the techniques independently of the rate. Clause 1 here adds that there is a quantity **not**
read off the field, the degree, and clause 3 says what it is good for. **The two do not
conflict: the degree is not a price-built quantity, and it does not order the techniques
either. It bounds how often the order can change.**

## 4. Related work

The reduction to dated labour and the reswitching example are Sraffa's and Samuelson's; the
symposium in which the second appears is the one B67 §9 already reads. The measure clause 5 is
about is Böhm-Bawerk's idea in the cost-weighted form Hicks gave it, which Fratini (2012) calls
the Hicks-Malinvaud average period and reads as not expressing a degree of roundaboutness.
Descartes' rule of signs is of course not new; what is done with it here is to apply it to the
difference of two dated labour profiles, where the sign count is a property of the two
techniques.

- Böhm-Bawerk, E. von (1889). *Positive Theorie des Kapitales.* Wagner.
- Fratini, S. M. (2012). Malinvaud on Wicksell's legacy to capital theory: some critical
  remarks. MPRA Paper 39574.
- Hicks, J. R. (1946). *Value and Capital.* 2nd ed. Oxford University Press.
- Hicks, J. R. (1973). *Capital and Time: A Neo-Austrian Theory.* Oxford University Press.
- Samuelson, P. A. (1966). A Summing Up. *Quarterly Journal of Economics* 80(4), 568-583.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 5. The known answer and the structural checks

`experiments/b74_roundaboutness.py`, record `results/b74_roundaboutness.json`, which carries
the configuration it ran under. Seed 0; a run takes a few seconds and a second run writes the
same bytes. All four pass.

**B74-5, a known answer: Samuelson's two switch points, read back by factoring.** One technique
spends 7 units of labour two periods before the output, the other 2 units three periods before
and 6 units one period before. **The difference of their dated labour profiles is
`−6x + 7x² − 2x³`, which factors as `−x(2x − 3)(x − 2)`**, so the switch points are exactly
`x = 3/2` and `x = 2`, that is **50 and 100 per cent, matched to `0.0e+00`**, with costs 15.75
and 28.00 matched to `0.0e+00` and the two techniques equally costly there to `0.0e+00`.
**Descartes' bound is attained**: the coefficient sequence changes sign twice and there are two
switch points. B67-6b read the same pair by bisection on the cost functions; **here the
polynomial factors and the roots are rational**, which is a different route to the same
published numbers.

**B74-6, the structural checks.** 600 drawn pairs of techniques, each with a longest lag
between 2 and 6 and some dates carrying no labour.

- **B74-6a, Theorem 19(3).** The number of positive roots of the difference **never exceeds the
  number of sign changes** in its coefficients, on all 600, and **the two always have the same
  parity**, on all 600. The bound is attained on 288. The joint distribution of (sign changes,
  switch points at a positive rate) is `(0,0)` on 54, `(1,0)` on 95, `(1,1)` on 70, `(2,0)` on
  172, `(2,1)` on 36, `(2,2)` on 5, `(3,0)` on 80, `(3,1)` on 52, `(4,0)` on 18, `(4,1)` on 9,
  `(4,2)` on 1, `(5,0)` on 5, `(5,1)` on 2, `(5,2)` on 1.
- **B74-6b, Theorem 19(4).** Where the difference changes sign **once** there is at most one
  switch point, on all 169 such pairs, **and the cost ordering reverses at most once** over the
  whole range of rates probed, on all 169. Where it changes sign twice or more, pairs with two
  switch points occur, 7 of the 374 such pairs. **So the domain of the intuition is not empty
  and it is not everything.**
- **B74-6c, Theorem 19(5).** Each pair read at 601 rates from zero up to 3. **The average
  period moves with the rate on 598 of the pairs**, the largest movement 4.6240 periods.
  **Its ordering between two techniques reverses somewhere on 133 of the pairs, and on all 133
  the rate where it reverses is not a switch point.** An instance: the ordering reverses at
  `r = 0.3775` while that pair has no switch point at all.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts are counts on drawn profiles: 288 of 600 attaining the bound is a property of the
drawing, not a frequency among techniques used anywhere. The two pairs among 600 whose average
period does not move were inspected, and both legs of both sit on a single date, which is
clause 5's equality case.


## Capital reversing on this station's own object, 2026-09-13

[`b92_capital_reversing.md`](b92_capital_reversing.md) reads capital per worker on the dated-labour
profiles defined here, `k = (1/L - w)/r` with `w = 1/c(x)`, and takes the Samuelson pair and the
two published switch points from this station's constants. **Capital reverses at the second of
the two and not at the first**, which is the textbook reading; `L_A = 7` against `L_B = 8` is what
decides it, since at a crossing the wage is shared and `k` is ordered the opposite way to `L`.

**The general statement uses this station's `c(1) = L`.** A single crossing above `x = 1` leaves
the cost ordering agreeing with the labour ordering all the way down, so two techniques cannot
reverse without reswitching. Three can.

## 6. Scope

Two techniques, one produced output, labour the only unproduced input, and the wage as the unit
of account: this is the dated-labour reduction, so it inherits its conditions from B67. Three
or more techniques and the lower envelope of their cost curves is a different question, done in
[`b76_envelope.md`](b76_envelope.md), where the bound of clause 3 becomes the order of a
Davenport-Schinzel sequence and the domain of clause 4 becomes the condition for no reswitching
anywhere on the envelope. Nothing here says why a rate of profit is positive: time preference
and the productivity of roundaboutness are behavioural and this framework does not supply them,
as at every station before. Nothing here measures a technique, a switch point or an average
period in any economy.
