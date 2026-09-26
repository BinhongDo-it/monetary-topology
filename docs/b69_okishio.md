# B69: Okishio's theorem as the same bound evaluated at a second member of the same family

**Status: statement and proof, with one known answer from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B69-5 and
B69-6, are in `experiments/b69_okishio.py`, record `results/b69_okishio.json`, and are listed
in §7.**

---

## 0. The question this station answers

[`b68_value_field.md`](b68_value_field.md) proved the Fundamental Marxian Theorem by putting
the labour value vector into the Collatz-Wielandt bound on the augmented matrix. **That vector
is one member of the family of Theorem 13.** This file puts a second member into the same
bound.

1. **With the real wage basket held fixed, the sign of the change in the general rate of
   profit is the sign of the cost saving at the prices in force, on the one column that
   changed** (§2, Theorem 14(1)). **It is an equivalence.** Okishio's theorem of 1961 is the
   half that says a cheaper column does not lower the rate.
2. **The cost criterion is a statement about a cycle.** The new method's production cycle, run
   in the field that is in force, carries more than `log(1 + r)` exactly when the new column is
   cheaper, and the theorem says that excess survives the re-solving of the whole field rather
   than turning negative (§2, Theorem 14(2)).
3. **The constant real wage carries the conclusion.** For every cost-reducing substitution
   there is a rise in the wage basket that exactly cancels the gain, and it is a computed
   number, not an assertion (§2, Theorem 14(3)). So the direction the rate moves is fixed by
   two inputs, the technique and the basket, and **this framework supplies no law for how
   either of them moves**: what it supplies is the map from the pair to the rate.
4. **One bound, a family of test vectors** (§3, Corollary 14.1). The price vector is the
   family's member at the current rate, up to the unit of account; the value vector is its
   member at zero. **The Fundamental Marxian Theorem and Okishio's theorem are one inequality
   evaluated at two points of one family.**
5. **What the long dispute about this theorem is about** (§4, Corollary 14.2). Okishio's
   setting puts one price vector on both legs of a production cycle, which is to say the
   positions carry no date. The standing objection is that the two legs sit at different dates
   and therefore at different positions. **In this framework that is not an interpretive
   disagreement: it is a question about which graph is drawn**, and which graph fits a given
   economy is a fact about that economy.

## 1. Setup

The setup of [`b68_value_field.md`](b68_value_field.md) §1, with wages advanced: commodities
`1 … n` with `n ≥ 2`, technology `(A, l)` productive and irreducible, real wage basket `b ≥ 0`
per unit of labour, augmented matrix `M = A + b l`, and

```
1 + r = 1 / λ_PF(M),      p M = λ_PF(M) · p
```

so `p`, the left Perron vector of `M`, is the price vector and `(p M)_j` is what it costs to
produce one unit of `j` at those prices with the wage advanced.

**A substitution** replaces industry `k`'s method `(a_k, l_k)` by `(a'_k, l'_k)`, leaving every
other column alone. Write `A'`, `l'`, `M' = A' + b l'`, `λ' = λ_PF(M')` and `r'` for the
resulting system, **with the same basket `b`**. The new method is **cheaper at the current
prices** when `(p M')_k < (p M)_k`, which written out is `p a'_k + w l'_k < p a_k + w l_k` with
`w = p·b`.

## 2. Theorem 14

**Theorem 14.** With the setup of §1:

1. **(The sign of the change is the sign of the saving.)** With `M'` irreducible,

   ```
   r' > r   ⟺   (p M')_k < (p M)_k
   r' = r   ⟺   (p M')_k = (p M)_k
   r' < r   ⟺   (p M')_k > (p M)_k
   ```

   **The half that reads left to right in the first line is Okishio's theorem.** `M'` is
   irreducible automatically whenever the basket contains every commodity, since then
   `b l' > 0` entrywise.
2. **(The criterion is a cycle sum.)** In the field `(p, w, r)`, industry `k`'s production
   cycle run with the new method carries `log(p_k) − log((p M')_k)`, and the same cycle with
   the old method carries `log(1 + r)`. So the cost criterion is exactly the statement that
   **the new method's cycle shows an excess over the sum every other cycle is carrying.**
3. **(The basket carries the conclusion.)** Let `b(g) = (1 + g) b`. Then `r'(g)` is continuous
   and strictly decreasing with `r'(g) → −1`, so for any cost-reducing substitution there is
   exactly one `g* > 0` with `r'(g*) = r`. **The direction the rate moves after a technical
   change is fixed by the technique and the basket together, and nothing in this framework
   fixes the second.**

**Proof.**

**The bound.** For a non-negative matrix `N` with right Perron vector `q ≥ 0`, `N q = λ_PF q`,
and any positive row vector `u`,

```
min_j (u N)_j / u_j   ≤   λ_PF(N)   ≤   max_j (u N)_j / u_j
```

since `u N q = λ_PF (u·q)` and `u·q > 0`. If the upper inequality `u N ≤ μ u` is strict in a
component `j₀` with `q_{j₀} > 0`, then `λ_PF(N) < μ`, and symmetrically below.

**(1)** `M` and `M'` agree off column `k`, so `(p M')_j = (p M)_j = λ p_j` for every `j ≠ k`,
and `n ≥ 2` guarantees at least one such `j`. If `(p M')_k < λ p_k` then
`max_j (p M')_j / p_j = λ`, so `λ' ≤ λ`; and `M'` irreducible gives `q' > 0`, so the strict
component makes `λ' < λ`, that is `r' > r`. If `(p M')_k > λ p_k` then
`min_j (p M')_j / p_j = λ`, so `λ' ≥ λ` and by the same argument `λ' > λ`, that is `r' < r`.
If `(p M')_k = λ p_k` then `p M' = λ p`, so `p` is a positive left eigenvector of `M'` and
`λ' = λ` exactly. The three cases are exhaustive and the equivalences follow.

**(2)** The bundle for one unit costs `p a'_k + w l'_k = (p M')_k` and the sale returns `p_k`,
so the cycle carries `log(p_k) − log((p M')_k)`. With the old method `(p M)_k = λ p_k`, so that
cycle carries `−log λ = log(1 + r)`. Subtracting, the excess is positive exactly when
`(p M')_k < (p M)_k`.

**(3)** `M'(g) = A' + (1 + g) b l'` is entrywise non-decreasing in `g` and strictly increasing
in every entry where `b l' > 0`, so `λ_PF(M'(g))` is strictly increasing, so `r'(g)` is
strictly decreasing; it is continuous because the Perron root is, and `λ_PF → ∞` as `g → ∞`
gives `r' → −1`. A cost-reducing substitution has `r'(0) > r`, so the intermediate value
theorem gives exactly one crossing. ∎

**What the first clause says in words.** The whole economy's rate of profit answers to one
number, computed on the one column that changed, at the prices that were in force before it
changed. **No other column has to be looked at, and neither do the new prices.** That is why
the theorem is available to a capitalist deciding one at a time, which is the use Okishio put
it to.

## 3. Corollary 14.1: one bound, and the family that supplies its test vectors

**Corollary 14.1.** Write `u(r₀) = l (I − (1 + r₀) A)^{-1}` for the family of Theorem 13 of
B68, positive for `0 ≤ r₀ < R = 1/λ_PF(A) − 1`. Then:

1. `u(0) = v`, the labour value vector.
2. `p = (1 + r)(p·b) · u(r)`: **the price vector is the family's member at the actual rate, up
   to the unit of account.**
3. Every member is a legitimate test vector, so each gives a bound
   `λ_PF(M) ≤ max_j (u(r₀) M)_j / u(r₀)_j` on any augmented matrix.
4. **The bound at `u(0)` is the Fundamental Marxian Theorem and the bound at `u(r)` is Theorem
   14.** The two theorems are one inequality evaluated at two points of one family.

**Proof.** (1) is the definition. (2): the price equation with wages advanced is
`p = (1 + r) p A + (1 + r)(p·b) l`, so `p (I − (1 + r) A) = (1 + r)(p·b) l`, and
`I − (1 + r) A` is invertible for `r < R`. (3) is the bound of §2 with `u = u(r₀) > 0`. (4):
at `u(0) = v`, `v M = v − (1 − v·b) l`, so the bound reads `λ_PF(M) < 1` exactly when
`v·b < 1`, which is B68 Corollary 13.2; at `u(r) ∝ p`, the bound applied to `M'` is the
argument of §2. ∎

**What this buys.** The two theorems have been read for sixty years as separate results about
separate things, one about exploitation and one about technical change. **They are the same
inequality, and what differs is only which member of the price family is put into it.** The
members between them give further bounds, which nothing in the literature has asked for; §7
reports which member happened to give the tightest bound on the drawn systems, and it is
usually neither end.

## 4. Corollary 14.2: what the dispute about this theorem is about

**Corollary 14.2.** In the drawing of §1 the purchase leg and the sale leg of a production
cycle carry the same price vector, which is to say the position graph has one vertex per
commodity. Give the positions a date, as in the product with dates of
[`b63_trilemma.md`](b63_trilemma.md): the purchase sits at `(commodity, t)` and the sale at
`(commodity, t + 1)`, and industry `k`'s cycle carries

```
log p_{t+1, k}  −  log (p_t M')_k
```

Then:

1. If the field is invariant under the date shift, `p_{t+1} = p_t`, this is the cycle sum of
   Theorem 14 and everything above holds unchanged.
2. Otherwise the sum depends on both `p_t` and `p_{t+1}`, and **it is not a function of the
   technique and the basket alone.**

**So there are two computable objects here, living on two different graphs**, and the question
which of them a claim about the rate of profit is about is settled by whether the positions
carry dates. **In a given economy that is a fact rather than a reading**: it asks whether the
inputs were bought at other dates, and at other prices, than the outputs were sold.

**Proof.** Immediate from the construction: with dates in the positions the two legs are
incident to different vertices, so the field takes two values on them, and a cycle sum is a
sum over its edges. The stationary case is the quotient of the dated graph by the date shift.
∎

**What this file does not do.** It does not adjudicate which graph a real economy is on, and it
does not implement either side's valuation rule and score it. Both would need a carrier where
the dates and the prices on both legs can be read, and this station reads no data. **What it
supplies is the statement that the disagreement has that shape**, which is a question with an
answer rather than a matter of which author one follows.

## 5. Placement

**What this framework reads of the world.** The sign of the change in the general rate of
profit is the sign of the cost saving on the changed column at the prevailing prices, in both
directions; that criterion is an excess cycle sum in the field in force; the conclusion is
carried by the fixed basket, and the cancelling rise in the basket is computable; the theorem
is one Collatz-Wielandt bound at a second member of the price family; and the dispute about
the theorem is a question about whether positions carry dates.

**What the Marxian account reads of it.** Okishio's theorem itself, as an implication, and a
long literature disputing what it settles about the tendency of the rate of profit to fall.

| cell | content |
|---|---|
| **A** | Okishio's theorem, derived here from the same bound B68 used for the Fundamental Marxian Theorem. That tradition has it already, by name and by proof |
| **D2** | **What the dispute about the theorem is about.** Each side asserts its own valuation rule and neither supplies a test that would decide between them. Here the two sides compute cycle sums on two different graphs, one with dates in the positions and one without, and which graph fits an economy is a fact about that economy. The question is both sides' own and the discriminant is not in either |
| **D** | The equivalence in both directions rather than the published implication; the reading of the cost criterion as an excess cycle sum; the cancelling rise in the basket as a computed number; and the family of test vectors, of which two members are named theorems and the rest are bounds no account asks for |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

**Where a specialisation and an account's own statement of itself come apart.** As in B68:
drawing an established result out of this framework term for term is what a more general
statement owes a narrower one. Where the two come apart, the place to look first is the
explanation the narrower account gives of its own result, which causal claim carries the
weight, whether a term keeps one sense from premise to conclusion, and whether the instrument
takes the object the claim is about.

## 6. Related work

The theorem is Okishio's (1961); the same author's 1963 note is the Fundamental Marxian Theorem
that B68 reads back, and Morishima (1973) is the standard modern treatment of both. Roemer
(1981) is the analytical restatement. The standing objection from the temporal side is
Freeman's (1998), which names simultaneous valuation as the assumption it attacks; Rigby (1990)
is an empirical challenge. The results this file rests on are Theorem 13 and Corollary 13.2 of
[`b68_value_field.md`](b68_value_field.md), Theorem 12 of
[`b67_prices_of_production.md`](b67_prices_of_production.md), and the product with dates of
[`b63_trilemma.md`](b63_trilemma.md).

- Freeman, A. (1998). A General Refutation of Okishio's Theorem and a Proof of the Falling Rate
  of Profit. In R. Bellofiore (ed.), *Marxian Economics: A Reappraisal*, 139-162. Palgrave
  Macmillan, London.
- Morishima, M. (1973). *Marx's Economics: A Dual Theory of Value and Growth.* Cambridge
  University Press.
- Okishio, N. (1961). Technical Changes and the Rate of Profit. *Kobe University Economic
  Review* 7, 85-99.
- Okishio, N. (1963). A Mathematical Note on Marxian Theorems.
  *Weltwirtschaftliches Archiv* 91(2), 287-299.
- Rigby, D. L. (1990). Technical Change and the Rate of Profit: An Obituary for Okishio's
  Theorem. *Environment and Planning A* 22(8).
- Roemer, J. E. (1981). *Analytical Foundations of Marxian Economic Theory.* Cambridge
  University Press.

## 7. The known answer and the structural checks

`experiments/b69_okishio.py`, record `results/b69_okishio.json`, which carries the
configuration it ran under. Seed 0; a run takes a few seconds and a second run writes the same
bytes. **All five criteria are read off one shared sample of 1,800 draws**, each a system of 3
to 8 industries from stage A19's generator, a wage basket whose labour value is `0.3`, `0.5` or
`0.7`, and a substitution in one industry drawn by scaling that column entrywise in
`[0.6, 1.4]`, which preserves the zero pattern. All five pass.

**B69-5, a known answer: Okishio's theorem.** 915 of the 1,800 substitutions are cheaper at
the current prices, and **every one of them raises the rate of profit**, with the basket held
fixed in kind. Zero counterexamples. The smallest gain seen is `0.000008` in the rate, so the
test is not reading noise at the boundary.

**B69-6, the structural checks.**

- **B69-6a, Theorem 14(2).** The old field's cycle for the changed industry carries
  `log(1 + r)` to `4.3e-15`, and the same cycle run with the new method carries more than that
  **exactly when** the new column is cheaper at the old prices, on all 1,800 draws, cheaper and
  dearer alike. The smallest excess in absolute value is `1.7e-5`, well clear of the tolerance.
- **B69-6b, Theorem 14(1) as an equivalence.** 885 of the 1,800 substitutions are dearer at the
  current prices, and **the rate falls on all 885 of them**, rising on none. The largest fall
  is `0.1994` in the rate. This is the lower Collatz-Wielandt bound doing the work the upper
  one does for Okishio's half.
- **B69-6c, Corollary 14.1.** The price vector equals the family's member at the current rate
  after scaling, to `4.4e-15` on every draw. **Every member of the family bounds the Perron
  root of the new augmented matrix**, 12,600 of 12,600 points, worst slack `1.5e-3`. The
  tightest member is `r₀ = 0.25 R` on 594 draws, `0.5 R` on 552 and `0.1 R` on 254: **usually
  neither of the two ends that carry a named theorem.**
- **B69-6d, Theorem 14(3).** For all 915 cheaper substitutions the rise in the basket that
  exactly cancels the gain is found by bisection inside a window of 20 times the basket. The
  median is `0.0541` of the basket and the range is `0.0000` to `1.6163`. **A technical change
  that raises the rate by a little is cancelled by a wage rise of a few per cent.**

**What these checks are and are not.** They read no data and decide nothing about any economy.
They check that the algebra above holds on systems the generator draws. The one statement that
is anyone else's, the theorem of §2's first clause read left to right, is read back rather than
assumed.

## 8. Scope

Single-product industries, circulating capital, homogeneous labour, no joint production and no
fixed capital, as in B67 and B68. One column changes at a time. **Simultaneous changes in
several industries were registered here as the same argument with `p M' ≤ λ p` holding on a
set of columns, and were done on 2026-09-13 at [`b85_simultaneous.md`](b85_simultaneous.md),
Theorem 29. Half of that registration was right.** The forward implication carries over with
the same Collatz-Wielandt step and not a word changed, but **the equivalence does not**: a set
in which some columns get dearer and others cheaper raises the rate on 1,461 of 4,092 drawn
substitutions. So the equivalence of Theorem 14(1) is not the one-column case of a
several-column equivalence, it is **a property of one column**, namely that the prices in
force see everything that moved. What survives in general is a bracket over the changed
columns, which decides on 1,440 of 1,440 draws at one column, 705 of 1,440 at two, and less
as more move. The basket is held fixed in kind, which is the theorem's hypothesis
and, by Theorem 14(3), the place where its conclusion is carried.

**What is not here.** Which direction techniques actually move is not a statement this
framework supplies, and neither is which direction the wage basket moves. Both are inputs.
A tendency of the rate of profit to fall would need a law for at least one of them, and this
file makes precise what such a law would have to deliver rather than supplying one.
