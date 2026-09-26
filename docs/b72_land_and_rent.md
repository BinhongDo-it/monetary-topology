# B72: rent, as a term on an edge into a position no cycle produces

**Status: statement and proof, with one known answer from the literature and three structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B72-5 and
B72-6, are in `experiments/b72_land_and_rent.py`, record `results/b72_land_and_rent.json`, and
are listed in §5.**

---

## 0. The question this station answers

[`b70_joint_production.md`](b70_joint_production.md) registered land as the other half of
Sraffa's Part II, and [`b71_von_neumann.md`](b71_von_neumann.md) read the complementary
slackness conditions as sentences about cycles. **Rent is where those two meet.**

1. **Land is a position that no cycle produces.** It is bought and never sold as an output, so
   under extensive rent it is a pendant vertex and `b₁` counts processes and nothing else
   (§2, Theorem 17(1)). **A rent is a term on an edge into such a position.**
2. **The rent is exactly what makes the cycle sums equal** (§2, Theorem 17(2)): it is the
   amount by which a land's cycle would otherwise carry more than the common value.
3. **"The marginal land pays no rent" is not an assumption.** Requiring every rent to be
   non-negative pins the wage to the lower envelope of the lands' own wage curves, and the land
   attaining that envelope pays nothing (§2, Theorem 17(3)). **This is von Neumann's (7') of
   B71 applied to an input no process produces.**
4. **The order of cultivation therefore varies with distribution** (§2, Theorem 17(4)): the
   wage curves are straight lines in the rate of profit and a reversal is two lines crossing,
   the same shape as the reswitching of B67-6b. **This is Sraffa's section 86.**
5. **Extensive and intensive rent differ by one cycle** (§3, Corollary 17.1). Two methods on
   one land make that land's vertex the meeting point of two purchase edges, so it closes a
   cycle and `b₁` rises by one. **The extra equation intensive rent is known to need is that
   extra cycle.**

## 1. Setup

`n` produced commodities and `k` qualities of land in use. Commodity 1 can be produced on any
land, one method per land; each other commodity has one method. Method `i` on land `i` uses the
input bundle `a_i` of produced commodities, `l_i` labour and one acre of land `i`, and delivers
`q_i` units of commodity 1. Wages and rents are paid out of the product, as in Sraffa. With `p`
the commodity prices, `w` the wage, `ρ_i` the rent on land `i` and `r` the rate of profit,

```
p₁ q_i = (1 + r) p a_i + w l_i + ρ_i          (lands i = 1 … k)
p_j    = (1 + r) p a_j + w l_j                (other commodities j = 2 … n)
```

**Which lands are in use is given from outside**: this file asks what the rents and the order
are, given that they are.

**The corn model** used in §5 is the case `n = 1`: corn is produced from corn and labour on each
land, `α_i` corn and `λ_i` labour per unit of corn, with corn as the unit of account, so the
land equations read `1 = (1 + r) α_i + w λ_i + ρ_i`.

## 2. Theorem 17

**Theorem 17.** With the setup of §1:

1. **(Land lies on no cycle.)** Each land vertex is bought by the bundle of the one method that
   uses it and is produced by nothing, so it is a pendant vertex: the drawn graph's first Betti
   number is `b₁ = k + n − 1`, the number of operated methods, and adding the land vertices
   leaves it there. **A rent is a term on an edge into a position no cycle produces.**
2. **(The rent is the excess on a cycle.)** Setting every production cycle's sum to `log(1 + r)`
   requires

   ```
   ρ_i = p₁ q_i − (1 + r) p a_i − w l_i
   ```

   which is the amount that land `i`'s cycle carries over the common value. A land whose excess
   is zero pays no rent; one whose excess is negative cannot be operated at a non-negative rent.
3. **(The marginal land, and where the zero comes from.)** In the corn model, land `i` alone
   would support the wage `w_i(r) = (1 − (1 + r) α_i)/λ_i`. Then

   ```
   every ρ_i ≥ 0   ⟺   w ≤ min_i w_i(r)
   ```

   and with all `k` lands in use the wage is that minimum, so **the land attaining it pays no
   rent and every other rent is positive**. Take any other land as the marginal one and some
   rent goes negative. **The zero is forced by non-negativity, which is the slackness condition
   of B71 Theorem 16(3) read on an input no process produces.**
4. **(The order varies with distribution.)** Each `w_i` is a straight line in `r`, so the
   argmin of the envelope changes wherever two lines cross. **The order of cultivation is
   therefore not a physical datum**, and a reversal is the same object as a switch point in
   B67-6b.

**Proof.**

**(1)** The graph has, per method, a money vertex, a bundle vertex and an output vertex with
three edges among them, and the money vertices are chained, which gives `b₁ = k + n − 1` as in
B70 §2. Attaching a vertex by a single edge raises `E` and `V` by one each and leaves
`b₁ = E − rank(incidence)` unchanged. Each land is attached by exactly one edge because exactly
one method uses it.

**(2)** is the price equation of §1 solved for `ρ_i`, together with the reading of the cycle's
two legs: the bundle costs `(1 + r)`-free `p a_i` and the sale leg returns
`p₁ q_i − w l_i − ρ_i`, whose ratio is `1 + r` exactly when the displayed equation holds.

**(3)** `ρ_i = 1 − (1 + r) α_i − w λ_i ≥ 0` is `w ≤ w_i(r)` for each `i`, so all of them hold
exactly when `w ≤ min_i w_i(r)`; with every land in use the system has one degree of freedom
left and it is closed by the highest wage compatible with non-negative rents, which is that
minimum. At `w = w_j(r)` for a non-minimising `j`, the minimising land's rent is
`(w_j − w_min)·λ` in the relevant units and is negative.

**(4)** `w_i(r) = (1 − α_i)/λ_i − r α_i/λ_i` is affine in `r` with intercept and slope both
depending on `(α_i, λ_i)`, so two lands' curves cross at
`r* = ((1 − α_i)/λ_i − (1 − α_j)/λ_j) / (α_i/λ_i − α_j/λ_j)` whenever that is positive, and the
argmin changes there. ∎

## 3. Corollary 17.1: extensive and intensive rent differ by one cycle

**Corollary 17.1.** Put two methods on one quality of land, which is intensive rent. That land's
vertex is then bought by two bundles, so it is attached by two edges and closes a cycle:
`b₁` rises to `k + n`. **The extra equation that intensive rent is known to need is that extra
cycle.**

**Proof.** Attaching a vertex by two edges raises `E` by two and `V` by one, so
`b₁ = E − rank(incidence)` rises by one. ∎

**What this says.** Under extensive rent the land contributes a price and no equation, and the
system is closed by a zero. Under intensive rent the same land contributes a price and a cycle,
and the cycle is the equation. **The two cases are not two theories of rent: they are one graph
drawn with a land vertex of degree one or of degree two.**

## 4. Placement

**What this framework reads of the world.** Rent is a term on an edge into a position no cycle
produces; the rent is the excess a cycle carries over the common sum; the zero on the marginal
land is forced by non-negativity and is von Neumann's slackness condition; the order of
cultivation moves with distribution because the wage curves are lines and the envelope's argmin
moves; and extensive and intensive rent differ by one in `b₁`.

**What the classical account reads of it.** Differential rent, the no-rent margin, and Sraffa's
result that the order of cultivation follows costs and therefore distribution.

| cell | content |
|---|---|
| **A** | The no-rent marginal land, differential rent as the cost difference, and the dependence of the order of cultivation on distribution. That account has them, the last by name at PCMC section 86 |
| **D2** | **Empty on this station**, as in B71: nothing here is a question that account asks and cannot answer |
| **D** | Rent as a term on an edge into a position no cycle produces; the zero rent as the slackness condition of B71 rather than a separate postulate; and the difference between extensive and intensive rent as a difference of one in `b₁`. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 5. Related work

The theory is Ricardo's (1817), chapter 2, and Sraffa's (1960) Part II; the statement read back
in §6 is Sraffa's section 86. Bidard's survey for Centro Sraffa renders that section and counts
the operated methods against the unknowns. The results this file rests on are Theorem 15 of
[`b70_joint_production.md`](b70_joint_production.md), Theorem 16 of
[`b71_von_neumann.md`](b71_von_neumann.md), and Theorem 12 of
[`b67_prices_of_production.md`](b67_prices_of_production.md).

- Bidard, C. *The Ricardian Rent Theory: An Overview.* Centro Sraffa Working Papers.
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Ricardo, D. (1817). *On the Principles of Political Economy and Taxation.* John Murray,
  London.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 6. The known answer and the structural checks

`experiments/b72_land_and_rent.py`, record `results/b72_land_and_rent.json`, which carries the
configuration it ran under. Seed 0; a run takes a few seconds and a second run writes the same
bytes. The drawn systems are corn models with 2 to 5 lands, each using between `0.10` and `0.60`
corn and between `0.20` and `1.50` labour per unit of corn. All four pass.

**B72-5, a known answer: Sraffa's section 86.** 400 drawn sets of lands. **The order of
cultivation reverses with the rate of profit on 227 of them**, 260 crossings in all, at rates
between `0.0142` and `1.9854`, median `0.6770`. The wage is the lower envelope of the lands'
own wage curves, each a straight line in the rate, so **a reversal is two lines crossing**, the
same object as a switch point in B67-6b. The companion reading is read back at the same time:
**the land attaining the envelope pays no rent and no other rent is negative**, on 400 of 400
systems at a rate of `0.25`.

**B72-6, the structural checks.**

- **B72-6a, Theorem 17(2).** 400 systems at four rates, 1,600 points where the wage and both
  legs are positive: **with the rent set at each land's excess, every cycle carries
  `log(1 + r)`**, within `1.3e-15`.
- **B72-6b, Theorem 17(3).** **Exactly one land pays no rent and none is negative**, 400 of
  400, the smallest positive rent `0.000072`. **Taking any other land as the marginal one
  drives some rent negative**, 400 of 400, the most negative `−5.21`.
- **B72-6c, the counting and Corollary 17.1.** The operated methods number `k + n − 1` against
  `n + k` unknowns, **one short**, 400 of 400, and the zero rent closes it to full rank. The
  graph is then built as vertices and edges with `b₁` read as `E − rank(incidence)` rather than
  from a formula: **extensive rent leaves `b₁` at the process count**, 400 of 400, and **two
  methods on one land raise it by exactly one**, 400 of 400.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The 227 of 400 is a count on drawn parameter sets and is not a frequency in any agriculture.

## 6a. The demand side, supplied 2026-09-13

**"Which lands are in use is given from outside" is answered at**
[`b87_demand_grip.md`](b87_demand_grip.md), **Theorem 31**, which imports this
station's solver, land generator, graph builder and Betti number rather than
rewriting them. Three things come back here:

- **Demand's whole action on the field is the choice of a cultivated set.** Theorem
  17(3) assumes all `k` lands are cultivated, and that assumption is where demand
  enters. Two demands calling up the same lands give the same wage, the same rents
  and the same prices, so the action is a step function with at most `k` values,
  measured at `0.00e+00` inside a step against at least `2.16e-04` across one.
- **`b1` at the process count is confirmed on a sweep rather than at one point**,
  985 steps over 200 systems, and **the closed form is `|S| + n`**, which is what
  the drawn graph returns.
- **Corollary 17.1's `+1` arrives as a step of the demand sweep.** Once every land
  is in use the next unit of demand puts a second method on the best land, so the
  step adds a process and closes a cycle at once and `b1` rises by two. The
  extensive-to-intensive transition is therefore visible as a `+2` in a single
  running count.

**Theorem 17(3)'s boundary condition is one case of a counting identity**, done on 2026-09-13
at [`b89_degrees_of_freedom.md`](b89_degrees_of_freedom.md): with `j` acres worked by two
methods and `f = 1` when some cultivated land has spare capacity, `equations - unknowns =
j + f - 1`, so this station is the cell `(j, f) = (0, 1)`. **With no spare capacity and no
second method the system is short by one and the wage is not determined by cost**, the missing
direction being `(1, -lambda)`.

**The arithmetic of intensive rent at that step was run on 2026-09-13** at
[`b88_two_margins.md`](b88_two_margins.md), which brings in B73's pair. **The zero rent on the
marginal land does not survive the step**: the mixed system is square without it, so keeping it
over-determines, and the land that was marginal pays a strictly positive rent on 3,917 of 3,917
viable configurations. **Theorem 17(3)'s envelope rule survives in a stronger form**, applied to
closures rather than to lands: the pair is viable exactly when its wage lies on or below the
envelope.

## 7. Scope

The corn model for the checks: one produced commodity on several lands. The theorem is stated
for `n` commodities and the counting is checked at `n` up to three, but the envelope argument of
Theorem 17(3) is written for the corn case, where the wage curves are lines. Which lands are in
use is given from outside; no demand side is modelled, and the choice of how many lands to
cultivate is therefore not derived here. Intensive rent is placed by Corollary 17.1 and its
arithmetic is not run. Absolute rent needs an assumption about ownership that this framework
does not supply and is outside scope.
