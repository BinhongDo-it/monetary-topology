# B68: the labour values as the member of that family at a zero rate, and the transformation as the move along it

**Status: statement and proof, with one known answer from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B68-6 and
B68-7, are in `experiments/b68_value_field.py`, record `results/b68_value_field.json`, and are
listed in §9.**

---

## 0. The question this station answers

[`b67_prices_of_production.md`](b67_prices_of_production.md) put the classical price system on
the cycles: prices of production are the configuration in which every production cycle carries
the same sum `log(1 + r)`, and the solutions form a one-parameter family. This file names two
members of that family and asks what survives the move between them.

1. **The labour value equations `v = v A + l` are that family's member at `r = 0`**, with
   labour as the unit of account (§2, Theorem 13(1)). On that member every production cycle
   sums to zero, so the field is exact and `ρ(ω) = 0`: **the value scheme is the one member
   with no obstruction at all** (Theorem 13(3)).
2. **The transformation is the move along the family, and the map is explicit** (Theorem
   13(2)). Whether a map from values to prices exists is settled by a formula; what is at
   issue is which magnitudes hold still along it.
3. **An aggregate is a pairing of the field with a flow**, in the sense of Theorem 9 of
   [`b65_post_keynesian.md`](b65_post_keynesian.md), so which aggregates survive is fixed by
   which flow is paired. The total price of the net product equals its total value by a choice
   of unit; the total profits equal the total surplus value exactly when the wage basket costs
   what it is worth, which a basket in the net product's proportions does (§3, Corollary 13.1).
4. **The Fundamental Marxian Theorem is the monotonicity of the family's parameter in the wage
   basket**: `1 + r = 1/λ_PF(A + b l)`, and `r > 0` exactly when `v·b < 1` (§4, Corollary
   13.2). Read on the cycles it says: **every production cycle carries a positive sum exactly
   when the wage basket is worth less than the labour that buys it.**
5. **Whether the normal return on capital is a cost or a profit is a choice of where to draw
   the edge.** Buy the return along with the inputs and every member reads as "every cycle
   sums to zero", at any rate whatever. The rate `r` is what does not move when that choice is
   made; `ρ` does move. **So `ρ` is not a measure of the gap between values and prices: the
   gap is the family's parameter itself** (§5, Corollary 13.3).
6. **All three accounts carry one price per commodity**, so each of them is a field on the
   position graph alone and every square closes. Their whole dispute lives in one summand of
   `H¹(Γ)`, and **the terms this framework reads, what two classes pay at the same position,
   live in the other one** (§6, Corollary 13.4).

## 1. Setup

The setup of [`b67_prices_of_production.md`](b67_prices_of_production.md) §1: commodities
`1 … n`, one class per commodity, technology `(A, l)` with `a_ij` the quantity of commodity `i`
used to make one unit of `j` and `l_j > 0` the labour per unit of `j`. `A` is productive and
irreducible. Industry `j`'s production cycle is

```
C_j :  (j, money) → (j, the bundle for one unit) → (j, its output) → (j, money)
```

and money passes between industries at par, so the drawn graph has one independent cycle per
industry and nothing else.

**Three objects are added here.**

| | |
|---|---|
| **the labour values** | `v = v A + l`, so `v = l (I − A)^{-1}`, positive because `A` is productive |
| **the real wage** | a basket `b ≥ 0` per unit of labour, so the wage bill in kind is `L b` for `L` hours |
| **the net product** | `y > 0`, with the gross output that leaves it `x = (I − A)^{-1} y` and the labour employed `L = l·x` |

**Two conventions for the wage, as in B67 §1**: paid out of the product, where the cycle's
bundle is the commodity advance `(pA)_j` and the sale leg returns `p_j − w l_j`; or advanced,
where the bundle is `(pA)_j + w l_j` and the sale leg returns `p_j`. B67-7a checked that both
give `log(1 + r)` on every cycle. §2, §3 and §5 use the first; §4 uses the second, which is the
convention the Fundamental Marxian Theorem is stated in.

## 2. Theorem 13

**Theorem 13.** With the setup of §1:

1. **(The values are the member at a zero rate.)** The price equations
   `p = (1 + r) p A + w l` at `r = 0` and `w = 1` are the value equations `v = v A + l`, term
   for term. So in the unit of account that makes the wage one unit of labour, `p(0) = v`.
2. **(The transformation is the family's parameter.)** For `0 ≤ r < R = 1/λ_PF(A) − 1` the
   price system has the unique positive solution, up to the unit of account,

   ```
   p(r) = w(r) · l (I − (1 + r) A)^{-1}
   ```

   with `w(r)` fixed by the unit. The map from the value vector to the price vector at a rate
   is this formula: explicit, single valued, and defined at every rate the system admits.
3. **(The value scheme is the only exact member.)** On the member at `r = 0` every production
   cycle sums to zero, so by Theorem 1 the field is exact and by Theorem 5 `ρ(ω) = 0`. At any
   `r > 0` every production cycle sums to `log(1 + r) > 0`, so the field is not exact and
   `ρ(ω) > 0`. **The value scheme is the member with a potential, and no other member has one.**

**Proof.**

**(1)** Setting `r = 0` and `w = 1` in `p = (1 + r) p A + w l` gives `p = p A + l`, which is
the definition of `v`. `I − A` is invertible with a non-negative inverse because `A` is
productive, and the inverse is positive because `A` is irreducible, so the solution is unique
and positive and equals `l (I − A)^{-1}`. The unit of account that makes `w = 1` exists: take
any basket `e` with `v·e = 1`.

**(2)** `(I − (1 + r) A)^{-1} = Σ_k (1 + r)^k A^k` converges exactly when
`(1 + r) λ_PF(A) < 1`, that is `r < R`, and the sum is positive by irreducibility. Positivity
of `l` then makes `p(r)` positive. Uniqueness up to scale is the invertibility of
`I − (1 + r) A`.

**(3)** On the value member the cycle's bundle costs `(v A)_j` and the sale leg returns
`v_j − l_j`, which is `(v A)_j` by the value equation, so

```
∮ C_j = − log (v A)_j + 0 + log (v A)_j = 0
```

for every `j`, and `(v A)_j > 0` because `A` is irreducible with a positive column. The
exchange edges carry a single price vector, so their cycles sum to zero as well. The `n`
production cycles are independent and `b₁ = E − V + 1 = n` for the drawn graph, so they span
the cycle space and every cycle sums to zero. Theorem 1 gives exactness, Theorem 5 gives
`ρ = 0`. At `r > 0`, B67 Theorem 12(1) gives `∮ C_j = log(1 + r)` on every production cycle,
which is not zero, so Theorem 1 fails and Theorem 5 gives `ρ > 0`. ∎

**What the third clause says in words.** The value scheme is not one reading of prices among
others in this framework. It is the one configuration in the family where a single number per
commodity reproduces every exchange in the economy with nothing left over, which is what
`ρ = 0` means. Every other member of the family leaves a residue, the same residue on every
production cycle, and that residue is the rate of profits.

## 3. Corollary 13.1: which aggregates survive, and the flow that decides

**Corollary 13.1.** With the setup of §1, let the unit of account be chosen so that
`p·y = v·y`. Write `Π = p·y − L (p·b)` for the total profits and `S = v·y − v·(L b)` for the
total surplus value. Then:

1. `v·y = L`: **the total value of the net product is the labour employed**, at every
   technique and every activity level.
2. The choice `p·y = v·y` is available at every rate and fixes the unit of account and nothing
   else. **The first aggregate equality is a choice of unit.**
3. `Π − S = L (v·b − p·b)`. **The second aggregate equality holds exactly when the wage basket
   costs what it is worth**, and not otherwise.
4. If `b` is proportional to the net product `y`, then `p·b = v·b` at every rate, so both
   equalities hold at once. When the economy is the standard system of B67 Corollary 12.4,
   that basket is the standard commodity's.
5. `p(r)` is proportional to `v` at some `r > 0` if and only if `v` is proportional to `l`,
   which is equal composition across industries, and then it is proportional at every rate.

**Proof.**

**(1)** `v (I − A) = l` by the value equation, so `v·y = v (I − A) x = l·x = L`.

**(2)** `p(r)` is determined up to a positive scalar, and `p·y > 0`, so exactly one scalar
gives `p·y = L = v·y`. Nothing else is asserted by making it.

**(3)** With the unit of (2), `p·y = L`, so `Π = L − L (p·b) = L (1 − p·b)`. And
`S = v·y − L (v·b) = L (1 − v·b)` by (1). Subtracting gives `Π − S = L (v·b − p·b)`.

**(4)** For `b = s y`, `p·b = s (p·y) = s L = s (v·y) = v·b`, at every rate, and (3) gives
`Π = S`.

**(5)** Suppose `p = c v` with `c > 0` at a rate `r > 0`. Substituting in
`p = (1 + r) p A + w l` and using `v A = v − l`,

```
c v = (1 + r) c (v − l) + w l   ⟹   − r c v = (w − (1 + r) c) l
```

and `r c > 0` forces `v` to be a multiple of `l`. Conversely if `v = κ l` then
`l A = ((κ − 1)/κ) l`, so `l` is a left eigenvector of `A` and
`l (I − (1 + r) A)^{-1} = l / (1 − (1 + r)(κ − 1)/κ)`, a multiple of `l` and so of `v`, at
every rate below `R`. ∎

**What this settles and what it does not.** The two aggregate equalities are objects of
different types. The first is a normalisation, available at every rate, and it asserts nothing
about the economy. The second is a statement about one number, the price of the wage basket
against its value, and it is true for some baskets and false for others. **Asking which of the
two is the true invariant is asking about the flow each is paired with**, not about the
prices: in the pairing `⟨ω, x⟩` of Theorem 9, the first pairs the field with the net product
and the second with the wage basket. Fix the flows and the answer is an identity; leave them
unfixed and there is nothing to decide.

## 4. Corollary 13.2: the Fundamental Marxian Theorem is that parameter's monotonicity

**Corollary 13.2.** With the wage advanced and the real wage basket `b`, the price system is
`p = (1 + r) p (A + b l)`, so `1 + r = 1 / λ_PF(A + b l)` and `p` is the left Perron vector of
`A + b l`. Then

```
r > 0   ⟺   v·b < 1
```

that is, the rate of profits is positive exactly when the rate of exploitation
`e = (1 − v·b) / (v·b)` is. On the cycles: **every production cycle carries a positive sum
exactly when the wage basket is worth less than the labour that buys it.**

**Proof.** Write `M = A + b l`. Then

```
v M = v A + (v·b) l = (v − l) + (v·b) l = v − (1 − v·b) l
```

**so the augmented matrix moves the value vector down by the surplus and by nothing else.**
`v > 0` and `l > 0`. If `v·b < 1` then `v M < v` componentwise, and the Collatz-Wielandt bound
for the positive vector `v` gives `λ_PF(M) ≤ max_j (v M)_j / v_j < 1`, hence `r > 0`. If
`v·b > 1` then `v M > v` and the same bound read from below gives `λ_PF(M) > 1`, hence `r < 0`.
If `v·b = 1` then `v M = v`, so `v` is a left Perron vector with eigenvalue `1` and `r = 0`.
The three cases are exhaustive. ∎

**Whose result this is, and what is added here.** The theorem is Okishio's (1963) and
Morishima's (1973), who named it the Fundamental Marxian Theorem; the proof above is the
standard one. What this file adds is where it sits: the rate of profits is this framework's
family parameter and the common value of every production cycle's sum, so the theorem reads as
a statement about cycles. The exploitation condition is not an extra hypothesis about the
economy, it is the condition for the family to be at a member other than the exact one.

## 5. Corollary 13.3: cost or profit is where the edge is drawn, and the rate is what does not move

**Corollary 13.3.** Fix a member of the family: prices `p`, wage `w`, rate `r`. Draw industry
`j`'s production cycle in either of two ways.

| drawing | what the bundle costs | what the sale leg returns | `∮ C_j` |
|---|---|---|---|
| **the return left outside** | the commodity advance `(pA)_j` | `p_j − w l_j` | `log(1 + r)` |
| **the return bought inside** | `(1 + r)(pA)_j + w l_j` | `p_j` | `0` |

Both are drawings of the same member. In the second, every cycle sums to zero at every rate,
so the field is exact and `ρ(ω) = 0`. The prices, the wage and the rate are the same numbers in
both. Hence:

1. **"There is no profit over full cost" and "every production cycle carries `log(1 + r)`" are
   two drawings of one configuration.** Neither fixes the rate, and no reading of the cycles
   alone tells them apart.
2. **`ρ` is not a measure of how far prices stand from values.** It moves when the drawing
   moves and the configuration does not. What separates the members, under a drawing held
   fixed, is the common cycle sum, and that is the rate of profits.

**Proof.** The price equation at the member is `p_j = (1 + r)(pA)_j + w l_j`, so the second
drawing's bundle costs exactly `p_j`, which is what the sale leg returns, and the cycle sums to
`log p_j − log p_j = 0`. In the first drawing the sale leg returns
`p_j − w l_j = (1 + r)(pA)_j`, so the cycle sums to `log(1 + r)`. Exchange cycles sum to zero
in both, and the production cycles span, so in the second drawing the whole field is exact and
Theorem 5 gives `ρ = 0`. Nothing in the two drawings changed `p`, `w` or `r`: the second
drawing moved `log(1 + r)` from the sale leg to the purchase leg of the same cycle. ∎

**The scope of the freedom, which is narrow and is the reason the empirical arm reads posted
terms.** Moving the normal return into the bundle is a redescription of an accounting
identity, and it is available exactly where the weight on an edge is imputed by whoever is
doing the accounting. **It is not available where both legs are posted.** The interest paid on
one balance at a central bank and not on another, in `results/b59_reserve_class_rate.json`;
the withholding rates on the two share classes of one company, in `results/b21_tax_edges.json`;
the cancellation fee on a depositary receipt, in `results/b24_fungibility.json`; and the
cross-currency loop of [`b3_slice_availability.md`](b3_slice_availability.md) are numbers
published on named edges by parties who are not doing this framework's accounting, and no
redescription moves them. **A closed cycle that follows from a choice of bookkeeping and a
closed cycle that has been read off posted terms are different objects**, and this corollary
is about the first.

## 6. Corollary 13.4: all three accounts carry one price per commodity

**Corollary 13.4.** Marx's value scheme, Sraffa's price scheme and the long-run competitive
scheme each carry one number per commodity, or per commodity and date. In the notation of
[`b1_setup.md`](b1_setup.md), each of them takes the class graph `H` to a single vertex, so
`Γ = G □ H` is `G`, there are no squares, and everything the three disagree about lies in
`H¹(G)`. In particular:

| | `D`, the square part | `H¹(G)`, the loop part |
|---|---|---|
| the value scheme | no squares to have | **zero**: the field is exact (Theorem 13(3)) |
| prices of production at `r > 0` | no squares to have | **non-zero**: `log(1 + r)` on every production cycle |
| the long-run competitive scheme | no squares to have | zero or not, depending on the drawing (§5) |

**So the terms this framework reads, what two classes pay at the same position, are in the
summand none of the three has.** That is not a gap in their coverage that this file is pointing
at: it is the premise each of them starts from, which is that a position carries one number.
Whether that premise holds is measured elsewhere and not here.

**Proof.** With `H` a single vertex, `Γ = G □ H` is isomorphic to `G` and the square subgroup
of `H¹(Γ)` is trivial, since a square needs two distinct classes. Theorem 2 then leaves
`H¹(Γ) = H¹(G)`. The three rows are Theorem 13(3), B67 Theorem 12(1), and Corollary 13.3. ∎

## 7. Placement

**What this framework reads of the world.** The labour values are the member of the classical
family at a zero rate and the only exact one; the transformation is the move along a family
with one parameter; an aggregate is a pairing of the field with a flow, so which aggregates
hold still is fixed by which flow is paired; and whether the normal return is a cost or a
profit is a choice of drawing, under which the rate is invariant and the distance is not.

**What the Marxian account reads of it.** The value equations, the two aggregate equalities,
the claim that profit is unpaid labour, and the Fundamental Marxian Theorem in its modern
form.

**What the Sraffian account reads of it.** The price equations, the family, the standard
commodity, and the demonstration that the two aggregate equalities do not hold together in
general.

| cell | content |
|---|---|
| **A** | The value equations, the explicit map from values to prices at a rate, the Fundamental Marxian Theorem, the identity `Π − S = L (v·b − p·b)`, the closing of both aggregate equalities under a basket in the net product's proportions, and the equal-composition condition. This side derives each from one equation about cycle sums; the classical accounts have them already, the theorem of §4 by name |
| **D2** | **What type of statement each aggregate equality is.** The dispute asks which of the two is the true invariant and treats that as a question about the price transformation. Here the first is a choice of unit, available at every rate and asserting nothing, and the second is a statement about one number, the price of the wage basket against its value. An aggregate is a pairing of the field with a flow, so its invariance is a property of the flow that is paired. The question is the tradition's own, and the flow side is not in it |
| **D** | The distance `ρ` as a function of the rate, the reading that the value scheme is the unique exact member, and the reading that the cost-or-profit question is answered by a drawing rather than by the economy. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

**Where a specialisation and an account's own statement of itself come apart.** Drawing an
established account out of this framework term for term is what a more general statement owes a
narrower one, and each such derivation is recorded above as a common answer. Where the two come
apart, the question is which side is at fault, and the place to look first is the explanation
the narrower account gives of its own result: which causal claim carries the weight, whether a
term keeps one sense from the premise to the conclusion, and whether the instrument applied
takes the object the claim is about. **The phenomena those accounts report are carried by large
literatures; their explanations of them are written by each account separately and contradict
each other, so it is on that side that a discrepancy is first checked.**

## 8. Related work

The value scheme and the transformation are Marx's (1894), volume III, chapters 9 and 10.
Bortkiewicz (1907) is the first worked numerical treatment and the source of the observation
that the two aggregate equalities do not hold together in general; Seton (1957) and the
literature after it set out the normalisation question. The Fundamental Marxian Theorem read
back in §9 is Okishio's (1963) and Morishima's (1973), and the name is Morishima's. Steedman
(1977) is the Sraffian reading of the same material, and Kurz and Salvadori (1995) is the
standard modern treatment of the price system. The results this file rests on are Theorem 1 and
Theorem 5 of [`b1_theorem.md`](b1_theorem.md), Theorem 9 of
[`b65_post_keynesian.md`](b65_post_keynesian.md), and Theorem 12 of
[`b67_prices_of_production.md`](b67_prices_of_production.md).

- Bortkiewicz, L. von (1907). Wertrechnung und Preisrechnung im Marxschen System.
  *Archiv für Sozialwissenschaft und Sozialpolitik* 23 and 25.
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Marx, K. (1894). *Das Kapital*, volume III, edited by F. Engels. Meissner, Hamburg.
- Morishima, M. (1973). *Marx's Economics: A Dual Theory of Value and Growth.* Cambridge
  University Press. The Fundamental Marxian Theorem is stated at p. 53.
- Okishio, N. (1963). A Mathematical Note on Marxian Theorems.
  *Weltwirtschaftliches Archiv* 91(2), 287-299.
- Seton, F. (1957). The "Transformation Problem". *Review of Economic Studies* 24(3), 149-160.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.
- Steedman, I. (1977). *Marx after Sraffa.* New Left Books, London.

## 9. The known answer and the structural checks

`experiments/b68_value_field.py`, record `results/b68_value_field.json`, which carries the
configuration it ran under. Seed 0; a run takes a few seconds, and a second run writes the same
bytes. The random systems come from stage A19's industry generator, which enforces the
Hawkins-Simon condition where the matrix is made; only irreducible draws are kept, so every
commodity is basic. All five pass.

**B68-6, a known answer: the Fundamental Marxian Theorem.** 200 systems of 3 to 8 industries,
six wage baskets each, drawn so that the labour value of the basket is `0.2, 0.5, 0.8, 1.0,
1.2, 1.5`. **The rate of profits is positive at all 1,200 points exactly where the basket is
worth less than one unit of labour**, zero where it is worth one, negative where it is worth
more. The step the proof turns on, `v (A + b l) = v − (1 − v·b) l`, holds to `2.7e-15`. The
left Perron vector of the augmented matrix is positive and solves the price equation to
`4.4e-15` relative, and the eigenvalue read from the transpose matches to `4.9e-15`. The
smallest positive rate seen is `0.0599`, so the sign test is not reading noise.

**B68-7, the structural checks.**

- **B68-7a, Theorem 13.** With labour as the unit of account, `p(0) = v` to `8.9e-16` on every
  system. On the value field every production cycle sums to zero to `1.9e-15` and the distance
  of Theorem 5 is zero to `5.3e-15`, on all 200 systems: **the value scheme is exact.** At the
  six positive rates the same drawing gives `log(1 + r)` on every cycle to `1.6e-15` and a
  distance of `√(n/3)·log(1 + r)` to `6.7e-16`, at all 1,200 points, which is B67's constant
  for this graph.
- **B68-7b, Corollary 13.1.** 200 systems, four net products each, three wage shares, two
  baskets per share. The total value of the net product is the labour employed to `4.2e-16`.
  The identity `Π − S = L (v·b − p·b)` holds to `4.8e-16` at all 4,800 points. **A basket in
  the net product's proportions closes both aggregate equalities at once**, worst `5.0e-16` at
  all 2,400 points; **a basket drawn without that proportion leaves them apart** at all 2,400
  points, the smallest gap `2.6e-6` of the labour employed.
- **B68-7c, Corollary 13.3.** 200 systems at six positive rates, each drawn twice. With the
  return outside, every cycle sums to `log(1 + r)` to `1.4e-15` and the smallest distance seen
  is `0.0420`. **With the return bought inside the bundle, every cycle sums to zero to
  `8.9e-16` and the distance is `1.3e-14`**, at all 1,200 points, on the same prices, wage and
  rate. The two drawings differ by exactly `log(1 + r)` on every cycle, to `1.1e-15`.
- **B68-7d, Corollary 13.1(5).** With the labour vector drawn at random, prices are not
  proportional to values at any positive rate, at all 1,200 points, the smallest spread of
  `p/v` across industries `0.0067`. With the labour vector taken to be the left Perron vector
  of `A`, so that `v` is a multiple of `l`, **they are proportional at every rate**, worst
  spread `7.3e-15` at all 1,200 points.

**What these checks are and are not.** They read no data and decide nothing about any economy.
They check that the algebra written above holds on systems the generator draws, which is what
catches a wrong step in a proof or a wrong line in the code. The one statement here that is
anyone else's, the theorem of §4, is read back rather than assumed.


## The labour value as a subsystem's content, 2026-09-13

[`b96_basics_and_subsystems.md`](b96_basics_and_subsystems.md) reads Pasinetti's vertically
integrated subsystem, what one net unit of a good calls up, and its labour content `l [I - A]^{-1}`
agrees with this station's labour values to `1e-15`. **What the subsystem adds is the set rather
than the number**: which positions the unit calls up, and **the intersection of those sets over all
goods is exactly Sraffa's basics**, on 200 of 200 systems.

## 10. Scope

Single-product industries, circulating capital, homogeneous labour, no joint production and no
fixed capital: the same restriction as B67 Part I. Joint production is where negative values
are possible and where Steedman's case against the value magnitudes is made, and it needs the
joint production station that B67 has already registered. Reduction of skilled to simple labour
is not treated: `l` is one number per industry here.

**What this file does not enter.** The philosophy of value, which is to say whether labour is
the source of value or the measure of it, is not treated and is not needed for anything above.
Two systems of equations and the map between them is the whole object. Nothing here measures a
rate of profits, a technique, a wage or a rate of exploitation in any economy.

**The falling rate of profits is outside this file for a stated reason.** It is a movement of
`(A, l)` over time, which is the family itself moving, so it needs a mechanism for the
direction of technical change, and this framework supplies none. Okishio's theorem on that
question is the monotonicity of `λ_PF(A + b l)` under a cost-reducing change of technique, and
it is algebra of the same kind as §4; it is registered and not scheduled.
