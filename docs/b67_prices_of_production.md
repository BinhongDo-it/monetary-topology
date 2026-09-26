# B67: prices of production, as the configuration in which every production cycle carries the same sum

**Status: statement and proof, with two known answers from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B67-6 and
B67-7, are in `experiments/b67_prices_of_production.py`, record
`results/b67_prices_of_production.json`, and are listed in §9.**

---

## 0. The question this station answers

[`b65_post_keynesian.md`](b65_post_keynesian.md) put the markup on a cycle: the producing
class buys its bundle of inputs, produces, sells, and the sum of that cycle is
`log(1 + μ)`. Theorem 10 there leaves each class its own `μ`. **The classical theory of
prices adds one equation: all of those sums are equal.** This file works out what follows.

1. **Equal cycle sums are Sraffa's price equations** (§2, Theorem 12(1)), and the solutions
   are a one-parameter family in the rate of profits, ending where the wage vanishes at the
   rate the Perron-Frobenius eigenvalue of the input matrix fixes (Theorem 12(2)).
2. **The whole departure from a single price vector sits on the production edges**, so the
   distance of Theorem 5 is `log(1 + r)` times a number that belongs to the graph
   (Theorem 12(4)).
3. **Kalecki and Sraffa are the same object with and without that one equation** (§3).
4. **No-arbitrage cannot deliver a uniform positive rate of profits.** With the cycles
   walkable and unbounded it forces the rate to zero; with every producer bounded it reaches
   none of them. Equalisation at a positive rate needs a bound and a flow that responds, and
   this framework supplies neither (§4, Corollary 12.2).
5. **The standard commodity is the flow side of the same matrix**: the right eigenvector where
   the prices are the left one, and their pairing is Theorem 9's (§6).

## 1. Setup

Commodities `1 … n`, one class per commodity, each class producing its own. The technology is
`(A, l)`: `a_ij` is the quantity of commodity `i` used to make one unit of commodity `j`, so
**the buyer is the column**, and `l_j` is the labour per unit of `j`. Every class faces the
same commodity prices `p` and the same wage `w`, so the exchange edges carry a single price
vector and all their cycles sum to zero. `A` is productive, and irreducible so that every
commodity is basic.

**Industry `j`'s production cycle**, as in [`b65_post_keynesian.md`](b65_post_keynesian.md) §5:

```
C_j :  (j, money) → (j, the bundle for one unit) → (j, its output) → (j, money)
```

**Two conventions, and the convention is which edges lie on the loop.**

| wages | the bundle the cycle buys | what the sale leg returns |
|---|---|---|
| **paid out of the product**, as in Sraffa | the commodity inputs, `(pA)_j` | the price less the wage bill, `p_j − w l_j` |
| **advanced** | the commodities and the hours, `(pA)_j + w l_j` | the price, `p_j` |

Money passes between classes at par. Nothing else is drawn.

## 2. Theorem 12

**Theorem 12.** With the setup of §1:

1. **(Equal sums are the price equations.)** The condition that `∮ C_j` is the same number `c`
   for every industry is, with wages paid out of the product,
   `p_j = (1 + r)·Σ_i p_i a_ij + w l_j` with `1 + r = e^c`; and with wages advanced,
   `p_j = (1 + r)·(Σ_i p_i a_ij + w l_j)`. **A uniform rate of profits is one equation about
   cycle sums, and what counts as advanced is what the cycle passes through.**
2. **(The family and its end.)** For a numéraire fixed, the solutions form a one-parameter
   family indexed by `r`, with `p` proportional to `l (I − (1 + r)A)^{-1}` and the wage falling
   as `r` rises. The family ends at `R` with `1 + R = 1 / λ_PF(A)`, where the wage is zero and
   `p` is the left Perron-Frobenius eigenvector.
3. **(The standard commodity.)** Let `s` be the right eigenvector, `A s = λ_PF(A)·s`, scaled so
   that `l·s = 1`. With its net product `(I − A)s` as the unit of account, the wage is exactly
   `w = 1 − r / R` at every `r` in `[0, R]`.
4. **(Where the obstruction sits.)** Against the potential the prices themselves give, the
   field departs by `log(1 + r)` on every production edge and by nothing on any other edge.
   Hence `ρ(ω) = c_Γ · log(1 + r)`, with `c_Γ = ‖P_Z 1_P‖` the norm of the projection of the
   production edges' indicator on the cycle space, **a number that belongs to the graph and
   not to the rate**. For the graph of §1, one three-edge cycle per industry and money at par,
   `c_Γ = √(n / 3)`.

*Proof.* (1) With wages out of the product the cycle buys `(pA)_j`, and the money it returns
is `p_j − w l_j`, so `∮ C_j = log((p_j − w l_j) / (pA)_j)`; setting that to `c` for every `j`
and writing `1 + r = e^c` gives the equations, and with wages advanced the same step gives the
other form. (2) The equations say `p(I − (1 + r)A) = w l`, so `p = w l (I − (1 + r)A)^{-1}`,
and the inverse is non-negative exactly while `(1 + r)·λ_PF(A) < 1`; the numéraire fixes `w`,
and at `(1 + R)λ_PF = 1` the matrix is singular with `w = 0` and `p` its left eigenvector.
(3) Multiply `p(I − (1 + r)A) = w l` on the right by `s`: `p·s (1 − (1 + r)λ) = w (l·s)`. With
`1 + R = 1/λ` the first factor is `p·s·(R − r)/(1 + R)`, and the numéraire `p·(I − A)s = 1`
gives `p·s = (1 + R)/R`; with `l·s = 1` this is `w = 1 − r/R`. (4) Take
`ψ(j, money) = 0`, `ψ(j, bundle) = −log(pA)_j`, `ψ(j, output) = −log(p_j − w l_j)`. The buy
leg, the sale leg and the money edges are then exactly `d⁰ψ`, and the production edge, which
carries weight zero, sits at `d⁰ψ = −log(1 + r)`, so the departure is `log(1 + r)` there and
zero elsewhere. The departure is `log(1 + r)·1_P`, and `ρ(ω)` is its projection on the cycle
space, which is linear in it. For the graph of §1 the `n` production cycles are disjoint and
each has three edges, so the projection of `1_P` has norm `√(n/3)`. ∎

**The invariant is the sum on one cycle.** `ρ(ω)` aggregates that sum over the graph, so it
counts how many production cycles were drawn and how long each is. A statement about the size
of `ρ` is a statement about the drawing as much as about the economy, and only the per-cycle
sum is free of that.

## 3. Corollary 12.1: Kalecki and Sraffa, one equation apart

**Corollary 12.1.** Theorem 10 of [`b65_post_keynesian.md`](b65_post_keynesian.md) gives each
class its own cycle sum, `log(1 + μ_j)`, which is its degree of monopoly. **Sraffa's system is
that same object with one equation added: `μ_j` is the same for every `j`.** With wages
advanced the common value is the markup over full unit cost; with wages out of the product it
is the return on the commodities advanced, and Kalecki's markup over prime cost is the same
cycle with the wage bill moved inside the bundle.

*Proof.* Theorem 12(1) with Theorem 10's reading of the cycle sum. ∎

**What that locates.** The disagreement between the two traditions about distribution is not
about which object to look at. It is one equation on that object, and §4 says what it would
take for the equation to hold.

## 4. Corollary 12.2: what (NA) can and cannot give

**Corollary 12.2.** Let two industries' production cycles be walkable.

1. If neither faces a bound on quantity, (NA) with finite flows forces each sum to be at most
   zero, so `r ≤ 0`: **a uniform positive rate of profits is not available under (NA)**.
2. If every producer is bounded, (NA) reaches none of the cycles, and sums that are positive,
   equal or unequal, are all consistent with it.

Hence equalisation at a positive rate requires two things this framework does not supply: a
bound, so that a positive sum can persist (Theorem 10(b)), and a flow that moves toward the
higher sum until the sums level. **The classical postulate that competition equalises the rate
of profits is a statement about how capital moves, and this is the shape of what it has to
do.**

*Proof.* (1) is Theorem 10(a) applied to each cycle: a positive sum on an unbounded walkable
cycle admits an unbounded flow. (2) is Theorem 10(b), which is Corollary 8.6 of
[`b63_trilemma.md`](b63_trilemma.md) with the production cycle in place of the plaquette. ∎

**This is the third time the same shape has come up.** The tax and the job guarantee of
[`b66_mmt.md`](b66_mmt.md) live on the flow side for the same reason, and Corollary 11.2 there
gives the test: an edge bears on the terms only through the walkable cycles that contain it,
and a bound takes (NA) off the cycles that do.


## 4z. Corollary 12.3 measured, 2026-09-13

Corollary 12.3 says the value advanced is read off the field and the field moves with the rate,
so no quantity read off prices orders techniques independently of the rate. **The named case of
that is capital reversing**, and it is measured at
[`b92_capital_reversing.md`](b92_capital_reversing.md), Theorem 36.

- **The sharpest form is that `k` is two-valued at a switch.** Both techniques are in use at one
  wage and one rate, and their capital per worker differs on all 3,399 switches drawn, by a
  median of `0.562` of the smaller value and never by less than `9.8e-04`. **A quantity read off
  the field is not a coordinate on the field**, so asking it for a direction is the category
  error and not the anomaly.
- **With two techniques, reversing requires reswitching**, and that is one line of arithmetic
  rather than a property of any family: `c_i(1) = L_i`, so a single crossing above `x = 1` leaves
  the labour ordering and the cost ordering agreeing. Measured at `0` of 1,102 single-crossing
  pairs against `43` of 43 that reswitch.
- **With three it does not**, because the pair meeting on the envelope need not include the
  technique that owns a zero rate.

## 5. Corollary 12.3: the quantity of capital moves with the field

**Corollary 12.3.** The value advanced per unit of output, `K_j(r) = Σ_i p_i(r) a_ij`, is read
off the field, and the field moves with `r` along the family of Theorem 12(2). In the
reduction to dated labour a technique's cost is a series in `(1 + r)`, so two techniques' costs
can be equal at more than one rate. **No quantity read off the field orders the techniques
independently of the rate**, and reswitching is the case where the order returns to a technique
it had left.

*Proof.* The first half is Theorem 12(2): `p` depends on `r`, so any ratio built from `p` does.
The second is arithmetic on the two series, and §9 runs Samuelson's pair, whose costs are equal
at two rates. ∎

## 6. Corollary 12.4: the standard commodity is the flow side

**Corollary 12.4.** The right eigenvector `s` of `A` is a flow: run industry `j` at scale `s_j`
and the inputs the whole system consumes stand in the same proportions as its gross output, so
the system reproduces itself with a surplus at the rate `R`. The prices at `r = R` are the left
eigenvector of the same matrix. **At the top of the family the field side and the flow side of
this framework are the two eigenvectors of one matrix**, and their pairing is the pairing of
Theorem 9: the value of the standard net product.

**Profits in the aggregate.** Running the economy at any scale `x`, the profits of the whole
system are `r` times the value of what is advanced. That is Corollary 10.2 of
[`b65_post_keynesian.md`](b65_post_keynesian.md) summed over the cycles, with the value sent
around cycle `j` being what industry `j` advances, and §9 reads it back on random scales.

## 7. Placement

**What this framework reads of the world.** Prices of production are the configuration in
which every production cycle carries the same sum, and that sum is `log(1 + r)`; the
configurations form a one-parameter family ending where the wage vanishes; the whole departure
from a single price vector sits on the production edges; a uniform positive rate needs a bound
and a flow that responds; and any ordering of techniques by a quantity read off prices moves
with the rate.

**What the classical account reads of it.** The price equations, the maximum rate, the standard
commodity, the linear frontier in standard units, and reswitching.

**What the scalar price field reads of it.** Every cycle sums to zero, so there is no profit
over full unit cost, and the rate of profits it can carry is zero.

| cell | content |
|---|---|
| **A** | The price equations, the maximum rate at the Perron-Frobenius eigenvalue, the standard commodity and its linear frontier, and reswitching: this side derives them from one equation about cycle sums, and the classical account has them already |
| **D2** | **What makes the rate uniform.** The classical tradition takes competition's equalisation as a postulate; this side gives the conditions it has to meet, a bound on every producer and a flow that moves to the higher sum, and shows that no-arbitrage alone gives only `r = 0`. The question is that tradition's own, and the conditions are not in it |
| **D** | `ρ(ω)` as a function of the rate of profits, `c_Γ·log(1 + r)`, and the reading that the invariant is the per-cycle sum while `ρ` counts the drawing. No account asks for it |
| **C** | Empty |

## 8. Related work

The system, the standard commodity, the maximum rate and the frontier are Sraffa's (1960),
Part I; the reduction to dated labour is his too. The reswitching example read back in §9 is
Samuelson's (1966), from the symposium in which Pasinetti (1966) and Garegnani (1970) set out
the case the example conceded. Kurz and Salvadori (1995) is the standard modern treatment, and
the input-output matrix is Leontief's. The results this file rests on are Theorem 1 and
Theorem 5 of [`b1_theorem.md`](b1_theorem.md), Theorem 4 of
[`b4_directed_edges.md`](b4_directed_edges.md), Corollary 8.6 of
[`b63_trilemma.md`](b63_trilemma.md), and Theorem 9, Theorem 10 and Corollary 10.2 of
[`b65_post_keynesian.md`](b65_post_keynesian.md).

- Garegnani, P. (1970). Heterogeneous Capital, the Production Function and the Theory of
  Distribution. *Review of Economic Studies* 37(3).
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Leontief, W. (1941). *The Structure of American Economy, 1919-1929.* Harvard University Press.
- Pasinetti, L. L. (1966). Changes in the Rate of Profit and Switches of Techniques.
  *Quarterly Journal of Economics* 80(4).
- Samuelson, P. A. (1966). A Summing Up. *Quarterly Journal of Economics* 80(4), 568-583.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 9. The known answers and the structural checks

`experiments/b67_prices_of_production.py`, record `results/b67_prices_of_production.json`,
which carries the configuration it ran under. Seed 0; a run takes about a second, and a second
run writes the same bytes. The random systems come from stage A19's industry generator, which
enforces the Hawkins-Simon condition where the matrix is made; only irreducible draws are kept,
so every commodity is basic.

**B67-6a, a known answer: Sraffa's linear frontier.** 200 systems of 3 to 8 industries, at
seven rates of profits each. With the standard system scaled to one unit of labour and its net
product as the unit of account, **the wage is `1 − r/R` at all 1,400 points**, the worst gap
`7.3e-15`, and `R` is `1/λ_PF(A) − 1`. The eigenvector equation itself holds to `1.5e-15`.

**B67-6b, a known answer: Samuelson's two switch points.** One technique spends 7 units of
labour two periods before the output, the other 2 units three periods before and 6 units one
period before. Their costs are equal at **exactly two rates, 50 and 100 per cent**, found here
by bisection to `1.2e-15` of the published pair, at 15.75 and 28.00 per unit; the second
technique is the cheaper strictly between them and the first outside, at every probe.
**The same technique is chosen at a low rate and at a high one, and the other in between.**

**B67-7, the structural checks.** All pass.

- **B67-7a, Theorem 12(1) and (2).** 200 systems at seven rates: every industry's production
  cycle sums to `log(1 + r)` and all of them are equal, worst gap `2.7e-15` with wages paid out
  of the product and `8.9e-16` with wages advanced; the wage falls in the rate on every system,
  and reaches zero at the Perron-Frobenius rate.
- **B67-7b, Theorem 12(4).** Against the potential the prices give, the departure is
  `log(1 + r)` on every production edge and zero on every other, worst `2.7e-15`; the distance
  of Theorem 5 is `c_Γ·log(1 + r)` at all 1,400 points, worst `1.5e-14`; and for the graph
  drawn here `c_Γ = √(n/3)`, matched to `2.2e-16` on every system.
- **B67-7c, Corollary 12.2.** 60 systems probed at rates from `−0.3` to `+0.9`. With the
  production edges walkable and unbounded, a directed cycle is positive at every positive rate
  and at none below zero, 60 of 60, and the switching rate found by bisection is zero within
  `1e-9`. With every producer bounded, no directed cycle is positive at any rate, 60 of 60.
- **B67-7d, Corollary 10.2 read here.** 200 systems, three rates each, the standard proportions
  and three random scales of the economy: the profits of the whole economy are the rate times
  the value of what is advanced, 2,400 of 2,400, worst relative gap `8.3e-16`.

## 10. Scope

Single-product industries, circulating capital, no joint production and no fixed capital:
Sraffa's Part I. Joint production and fixed capital put the age of a machine into the positions
and the cycles into several dates, which is another station. The input matrix is taken
irreducible, so every commodity is basic; with non-basics the standard commodity is built on
the basic subsystem. Nothing here measures a rate of profits, a technology or a wage in any
economy: the file says what configuration the classical prices are, and what it would take for
the rate to be uniform.
