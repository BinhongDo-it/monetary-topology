# B73: two registered extensions, one costing nothing in the graph and one costing a cycle

**Status: statement and proof, with one known answer from the literature and two structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B73-5 and
B73-6, are in `experiments/b73_two_extensions.py`, record
`results/b73_two_extensions.json`, and are listed in §5.**

---

## 0. The question this station answers

Two things were registered and not scheduled: a machine whose efficiency declines with age,
left open by [`b70_joint_production.md`](b70_joint_production.md), and the arithmetic of
intensive rent, left open by [`b72_land_and_rent.md`](b72_land_and_rent.md). **They are done
here together because their costs in the graph are opposite, and that is the point.**

1. **Declining efficiency costs nothing in the graph** (§2, Theorem 18(1)). A profile of output
   coefficients changes weights and no edge, so `b₁` is unchanged. What it does change is the
   depreciation schedule: **straight-line at a zero rate needs constant efficiency as well**,
   and B70's Corollary 15.1(3) named only the rate.
2. **Intensive rent costs a cycle, and the cycle is the equation** (§2, Theorem 18(2)). A land
   with two users is a vertex of degree two, so `b₁` rises by one; that cycle closes exactly
   when both users pay the same rate for the acre; and with it the two price equations are
   square in the wage and the rent, **with no zero-rent condition anywhere**.
3. **The rent is the unit-cost gap, and Sraffa's condition is an identity** (§2, Theorem
   18(3)): `ρ (1/q₁ − 1/q₂) = C₂/q₂ − C₁/q₁`, so the rent is positive exactly when the method
   with more product per acre carries the higher cost per unit of product. **That is PCMC
   section 87, and here it is two lines of algebra.**
4. **One price per position is vacuous at a vertex of degree one and an equation at a vertex of
   degree two** (§2, Theorem 18(4)). Extensive rent has the first case and closes its system
   with a boundary condition; intensive rent has the second and closes it with the cycle.
   **The same assumption does different amounts of work in the two.**

## 1. Setup

**The machine.** The fixed-capital system of B70 Corollary 15.1, with one change: the output of
a machine of age `j − 1` is `q_j` rather than a constant `q`. Commodity `0` is the good and
commodity `k + 1` a machine used `k` times; process `0` builds a machine from `c` of the good
and `l₀` labour; process `j` uses a machine of age `j − 1` with `a` of the good and `l₁` labour
and delivers `q_j` of the good and, when `j < T`, the machine of age `j`.

**Intensive rent.** One quality of land, two methods used side by side on it. Method `i` uses
`a_i` corn and `l_i` labour on one acre and delivers `q_i` corn. Corn is the unit of account,
the rate of profit is `r`, the wage `w` and the rent `ρ` per acre, both paid out of the product:

```
q_i = (1 + r) a_i + w l_i + ρ                (i = 1, 2)
```

## 2. Theorem 18

**Theorem 18.** With the setup of §1:

1. **(A profile costs nothing in the graph.)** Changing `q_j` changes the weight on one edge of
   each cycle and adds or removes none, so `b₁` is what it was. At `r = 0` the price of the
   machine falls by

   ```
   p_{j−1} − p_j = q_j − a − w l₁
   ```

   each period, so **the schedule is straight-line exactly when the profile is constant**, and
   B70's Corollary 15.1(3) needs constant efficiency as well as a zero rate. **The sign of the
   fall is the sign of `q_j − a − w l₁`**, so a period whose output falls short of that
   period's own non-machine cost makes the machine's price rise with age. A rising profile is
   not by itself enough: what is needed is a period below that line.
2. **(A second user costs a cycle, and the cycle is the equation.)** With two methods on one
   land, the land vertex is bought by two bundles, so it has degree two, `b₁` rises by one, and
   deleting the vertex lowers it again: **the land lies on a cycle rather than hanging off
   one**. Charge the two users `ρ₁` and `ρ₂` for the same acre and that cycle carries
   `log(ρ₂/ρ₁)`, so **it closes exactly when the two rates agree**. With one rent the two price
   equations of §1 are square in `(w, ρ)` and determine both; **no zero-rent condition is used**.
3. **(The rent is the unit-cost gap.)** Writing `C_i = (1 + r) a_i + w l_i` for the cost per
   acre and `C_i/q_i` for the cost per unit of product,

   ```
   ρ (1/q₁ − 1/q₂)  =  C₂/q₂ − C₁/q₁
   ```

   so with `q₂ > q₁`, **the rent is positive exactly when the method that yields more per acre
   carries the higher cost per unit of product.** That is Sraffa's section 87.
4. **(What one price per position costs.)** At a position with one user the assumption that
   everyone pays the same rate for it is vacuous, and the system is closed by a boundary
   condition, which under extensive rent is the zero rent on the marginal land. At a position
   with two users it is the closure of a cycle, and that closure is an equation. **Extensive
   and intensive rent are the two sides of that line.**

**Proof.**

**(1)** The system's matrices have the same zero pattern for every profile, so the drawn graph
is the same and `b₁ = E − rank(incidence)` is unchanged. At `r = 0` process `j`'s equation is
`q_j p_g + p_j = p_{j−1} + a p_g + w l₁`, which rearranges to the display. Linearity in `j` is
constancy of the fall, hence of `q_j`. The last clause is the sign of the same expression.

**(2)** Attaching a vertex by two edges raises `E` by two and `V` by one, so `b₁` rises by one,
and deleting it reverses that. The added cycle runs from one bundle to the land and back to the
other bundle through the money chain, and the two land edges carry `−log ρ₁` and `+log ρ₂`
while the rest of the path is the same one that closes in the system without land, so the sum
is `log(ρ₂/ρ₁)`. Squareness is the two equations of §1 in the two unknowns `w` and `ρ`, whose
matrix has determinant `l₁ − l₂` up to sign.

**(3)** Both equations give the same `ρ`, so `ρ = q_i − C_i` for `i = 1, 2`. Then

```
C₂/q₂ − C₁/q₁ = (q₂ − ρ)/q₂ − (q₁ − ρ)/q₁ = ρ (1/q₁ − 1/q₂)
```

and `1/q₁ − 1/q₂ > 0` when `q₂ > q₁`.

**(4)** is (1) and (2) read together with B72 Theorem 17(3). ∎

**A note on Sraffa's condition.** Written as in (3) it is an identity, not a restriction to be
imposed: **the rent and the unit-cost gap are the same number up to a positive factor**. What
the condition does is tell one which configurations are viable, and Bidard's survey adds that
it is not the same as the condition for the incoming method to be the more productive one. §5
constructs an instance where the two diverge.

## 3. Placement

**What this framework reads of the world.** A profile of efficiencies costs nothing in the
graph and changes only the schedule; a second user of one position costs a cycle and that cycle
is the missing equation; the rent equals the unit-cost gap up to a positive factor; and one
price per position is vacuous at degree one and an equation at degree two.

**What the classical account reads of it.** Depreciation under varying efficiency, the
determination of intensive rent by two methods used side by side, and the condition of section
87 for that rent to be non-negative, together with Bidard's correction to it.

| cell | content |
|---|---|
| **A** | Sraffa's section 87 and Bidard's correction, and the determination of intensive rent by the two methods without a zero-rent condition. That account has them |
| **D2** | **What one price per position costs.** That tradition writes one rent per acre in a line and moves on, and the distinction between a position where the assumption is vacuous and one where it is an equation is not in it. The question of what the assumption is doing is that tradition's own |
| **D** | That a profile costs nothing in the graph while a second user costs a cycle; that the added cycle carries `log(ρ₂/ρ₁)` so its closure is the single rent; and that straight-line depreciation needs constant efficiency as well as a zero rate. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 3a. The pair inside a system that also has an extensive margin, 2026-09-13

Theorem 18(4) says one price per position is vacuous at a vertex of degree one and an equation
at a vertex of degree two, and that extensive and intensive rent are the two sides of that line.
[`b88_two_margins.md`](b88_two_margins.md) puts both on one system, `k` lands with a second
method on one acre, and the line turns into a constraint:

- **The two closures are alternatives and not additions.** A boundary condition and a cycle
  closure supply the same one missing equation, so a system with both is over-determined by
  exactly one. Measured rather than argued: the rent the boundary condition would set to zero
  comes out at least `8.0e-05` from zero over 12,009 configurations, against exactly zero on the
  extensive control.
- **The pair is viable in the system exactly when its wage lies on or below the extensive
  envelope**, which is B72's envelope rule applied to a closure rather than to a land. Between
  the acre's own wage curve and that envelope lies a third cell that neither this station nor
  B72 could state: **the second method pays a non-negative rent on its own acre and still drives
  another land's rent below zero**, on 1,703 of 12,009 configurations. A one-land model cannot
  see it, because what the second method moves is the whole system's wage.

## 4. Related work

The fixed-capital treatment and the intensive-rent equations are Sraffa's (1960), Parts II and
III, the non-negativity condition at section 87. Bidard's survey for Centro Sraffa gives the
rent-free relation by subtraction and the correction read back in §5. The results this file
rests on are Corollary 15.1 of [`b70_joint_production.md`](b70_joint_production.md) and
Theorem 17 with Corollary 17.1 of [`b72_land_and_rent.md`](b72_land_and_rent.md).

- Bidard, C. *The Ricardian Rent Theory: An Overview.* Centro Sraffa Working Papers.
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.

## 5. The known answer and the structural checks

`experiments/b73_two_extensions.py`, record `results/b73_two_extensions.json`, which carries
the configuration it ran under. Seed 0; a run takes a few seconds and a second run writes the
same bytes. All three pass.

**B73-5, a known answer: Sraffa's section 87 and Bidard's correction.** 210 drawn pairs of
methods on one acre, kept where the wage comes out positive. **The rent is positive exactly
when the method yielding more per acre carries the higher cost per unit of product**, on all
210, and the identity `ρ(1/q₁ − 1/q₂) = C₂/q₂ − C₁/q₁` holds within `2.7e-15`. The rent is
positive on 128 of them. **Bidard's correction is read back as well**: the condition for a
non-negative rent is not the condition for the incoming method to be the more productive one,
and the two diverge on 98 of the draws.

**B73-6, the structural checks.**

- **B73-6a, Theorem 18(1).** A machine lasting five periods under four profiles. **`b₁ = 6`
  under every one of them**: a profile changes weights and no edge. The fall in the price each
  period is `q_j − a − w l₁` within `7.8e-16` under every profile, and **the schedule is
  straight-line only for the constant one**: deviation `2.5e-16` there against `0.1655` for the
  declining and the mildly rising profiles. **A rising profile is not by itself enough to make
  the price rise with age**, and the mildly rising one here does not; the fourth profile, with
  the same total output and a first period below that period's own non-machine cost, gives the
  schedule `1.8125, 2.15, 1.7875, 1.325, 0.7625`, **rising after the first period**.
- **B73-6b, Theorem 18(2).** 400 drawn graphs of 2 to 5 processes. **A second user of the land
  raises `b₁` by exactly one**, 400 of 400, with `b₁` read from the incidence matrix, and
  **deleting the land vertex lowers it again**, 400 of 400, so the land lies on a cycle. The
  two price equations are square and non-singular on 400 draws. **Charging the two users `ρ₁`
  and `ρ₂` for the same acre makes the added cycle carry exactly `log(ρ₂/ρ₁)`**, within
  `1e-10`, so it closes exactly when the rates agree; the smallest non-zero opening produced
  here is `0.0488`.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The 98 of 210 is a count on drawn parameter pairs and is not a frequency in any agriculture.

## 6. Scope

The machine has a single efficiency profile fixed in advance and no choice of scrapping date;
endogenous scrapping is a different problem. The intensive-rent case is two methods on one
quality of land, with corn as the only produced commodity in the checks; the theorem is stated
for the two equations as such. Which methods and which lands are in use is given from outside,
as in B72. Nothing here measures a technique, a rent or a depreciation schedule in any economy.
