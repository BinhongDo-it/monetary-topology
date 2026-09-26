# B70: joint production, where the cycles and the commodities stop being the same index set

**Status: statement and proof, with one known answer from the literature and five structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B70-5 and
B70-6, are in `experiments/b70_joint_production.py`, record
`results/b70_joint_production.json`, and are listed in §7.**

---

## 0. The question this station answers

[`b67_prices_of_production.md`](b67_prices_of_production.md) drew one production cycle per
industry, and under single production that is also one cycle per commodity.
**Joint production separates those two index sets**, and this file works out what follows.

1. **The characterisation survives untouched.** With the sale leg carrying the whole output
   bundle, the condition that every production cycle sums to the same number is still the
   price system, and nothing in the proof of Theorem 12 used single production (§2, Theorem
   15(1)).
2. **What single production supplied was a coordinate system.** The drawn graph has `b₁ = n`,
   one independent cycle per process, and that number never mentions the commodity count `m`.
   **The classical square assumption is `b₁ = m`**; below it the price vector is undetermined
   on a subspace, above it the price equations have no solution and the inequality methods
   take over (§2, Theorem 15(2)).
3. **A negative labour value is a statement about the cone of feasible net outputs.** The
   value of commodity `i` is the labour in the activity that delivers one net unit of `i` and
   nothing else, and when that value is negative the activity has a negative component, so no
   such unit can be produced at all. **The number is the labour of an activity nobody can run**
   (§2, Theorem 15(3)).
4. **Fixed capital is this, with the machine's age as a position.** The value of a part-worn
   machine is then a coordinate of the price field, and the depreciation schedule falls out of
   the price equations: **straight-line exactly at a zero rate of profit, and at no other**
   (§3, Corollary 15.1).
5. **None of this touches the class index.** Every construction here keeps the class graph a
   single point, so the square summand stays empty and all of joint production's difficulties
   are on the position side (§4, Corollary 15.2).

## 1. Setup

`n` processes and `m` commodities. `A` and `B` are `m × n` and non-negative: `a_ij` is the
quantity of commodity `i` that process `j` consumes and `b_ij` the quantity it produces, so
**a process is a column and a commodity is a row**. `l > 0` is the labour per unit level of
each process and `p` is a row vector of commodity prices. The system is **productive** when
some non-negative activity vector leaves a positive net output of every commodity.

**Process `j`'s cycle** is drawn as in B67 §1, with one change:

```
C_j :  (j, money) → (j, the input bundle) → (j, the output bundle) → (j, money)
```

**The output vertex is a bundle, not a commodity.** With wages paid out of the product the
bundle costs `(p A)_j` and the sale leg returns `(p B)_j − w l_j`. Money passes between
processes at par. Single production is the special case `n = m` and `B = I`, where the output
bundle of process `j` is one unit of commodity `j` and nothing else.

## 2. Theorem 15

**Theorem 15.** With the setup of §1:

1. **(Equal cycle sums are the price equations, with no single production used.)** The `n`
   cycle sums are all equal to one number `c` if and only if

   ```
   p B = (1 + r) p A + w l,      1 + r = e^c
   ```

   The identity `(p B)_j − w l_j = (1 + r)(p A)_j` is algebraic and holds whatever the signs
   are. **The cycle sum is a logarithm only where both legs are positive**, and under joint
   production a price can come out negative, so that is a restriction with content.
2. **(One independent cycle per process.)** The drawn graph has `V = 3n` vertices and
   `E = 3n + (n − 1)` edges, so `b₁ = E − V + 1 = n`. The price equations are `n` equations in
   the `m` unknowns of `p` once `w` is fixed, so

   | | |
   |---|---|
   | `n = m` | generically one `p` per rate. **This is the square assumption, and here it reads `b₁ = m`** |
   | `n < m` | `p` is pinned only up to a subspace of dimension `m − rank ≥ m − n` |
   | `n > m` | generically no exact solution, and inequalities replace the equations |

   **Under single production the two index sets coincide, and each commodity has a cycle of
   its own. In general the per-commodity price is a coordinate obtained from the cycle data,
   not a primitive of the graph.**
3. **(A negative labour value is a statement about the feasible cone.)** Let `n = m` with
   `B − A` invertible, and let `v` solve `v(B − A) = l`. Write `x_i = (B − A)^{-1} e_i` for the
   activity vector whose net output is one unit of commodity `i` and nothing else. Then
   `v_i = l · x_i`, and

   ```
   v_i < 0   ⟹   x_i has a negative component
   (B − A)^{-1} ≥ 0   ⟹   v > 0
   ```

   **So a negative value says that one unit of that commodity on its own is not a feasible net
   output, and the number called its value is the labour of an activity that cannot be run.**

**Proof.**

**(1)** The cycle sum is `log((p B)_j − w l_j) − log((p A)_j)`. It equals `c` for every `j` iff
`(p B)_j − w l_j = e^c (p A)_j` for every `j`, which is the price system written column by
column with `1 + r = e^c`. Nothing in this used the shape of `B`. The logarithms exist iff both
legs are positive; the equation between the legs does not need them.

**(2)** The counts are immediate. The rank statements are the rank-nullity theorem applied to
`p ↦ p(B − (1 + r)A)`, a map from `ℝ^m` to `ℝ^n`.

**(3)** `v(B − A) = l` gives `v = l (B − A)^{-1}`, so
`v_i = l (B − A)^{-1} e_i = l · x_i`. If every component of `x_i` were non-negative then
`l > 0` would force `v_i ≥ 0`; contrapositively `v_i < 0` puts a negative component in `x_i`,
and `(B − A) x_i = e_i` says `x_i` is the only activity vector with that net output. If
`(B − A)^{-1} ≥ 0` then every `x_i ≥ 0` and `x_i ≠ 0`, so `v_i = l · x_i > 0`. ∎

**What the third clause settles and what it leaves.** It settles the direction of the reading:
the sign of a labour value under joint production is a fact about which net outputs the
technique can deliver, and not about labour, about exploitation, or about the definition of
value. It leaves open what number, if any, should be assigned to a commodity that has no
separate production; §5 records that the question is the tradition's own and that this file
does not answer it.

## 3. Corollary 15.1: fixed capital, and the depreciation schedule as a coordinate

**Corollary 15.1.** A machine of constant efficiency lasting `T` periods is the joint
production system: commodity `0` is the good and commodity `k + 1` is a machine that has been
used `k` times; process `0` builds a new machine from `c` of the good and `l₀` labour, and
process `j` for `1 ≤ j ≤ T` uses a machine of age `j − 1` together with `a` of the good and
`l₁` labour, delivering `q` of the good and, when `j < T`, the machine of age `j`. Then:

1. **The machine's age is a position coordinate**, exactly as the date is in Corollary 14.2 of
   [`b69_okishio.md`](b69_okishio.md). The framework absorbs fixed capital by enlarging the
   position graph, not by adding a construction.
2. **The value of a part-worn machine is a coordinate of the price field**, fixed by the price
   equations along with every other price, so a depreciation schedule is not a convention that
   the accountant chooses.
3. **At `r = 0` that schedule is exactly straight-line, and at every `r > 0` it is not.**

**Proof.** (1) and (2) are the construction. For (3), write `p_k` for the price of the machine
of age `k`, with `p_T = 0` since the machine is scrapped, and `p_g` for the good. Process `j`
gives

```
q p_g + p_j = (1 + r)(p_{j−1} + a p_g) + w l₁
```

At `r = 0` this is `p_{j−1} − p_j = (q − a) p_g − w l₁`, the same number for every `j`, so the
price falls by a constant each period and is linear in the remaining life. At `r > 0` the
recursion `p_j = (1 + r) p_{j−1} + K` with `K = (1 + r) a p_g + w l₁ − q p_g` has the solution
`p_j = C(1 + r)^j − K/r`, which is linear in `j` only if `C = 0`, and `C = 0` makes the
schedule constant. A constant schedule contradicts `p_T = 0` with `p_0 > 0`. ∎

**So straight-line depreciation is the zero-rate member of a family**, in the same way that the
labour values are the zero-rate member in
[`b68_value_field.md`](b68_value_field.md). Two different accounting conventions, one family
each, and the same parameter.

## 4. Corollary 15.2: none of this touches the class index

**Corollary 15.2.** Every construction in this file writes one number per commodity, or per
commodity and machine age, so the class graph is a single vertex, `Γ = G`, and the square
summand of `H¹(Γ)` is empty. **Corollary 13.4 of [`b68_value_field.md`](b68_value_field.md)
therefore stands unchanged for joint production and fixed capital.**

**What that buys.** Negative values, several rates or none, undetermined or inconsistent price
systems: every difficulty this literature has found is a difficulty of the position side, and
it arrives while the class index is still absent. **So the terms this framework reads are not
in competition with any of them.** They are in the summand none of these constructions has.

**Proof.** The class graph has one vertex, so a square needs two distinct classes and there are
none; Theorem 2 then leaves `H¹(Γ) = H¹(G)`. ∎

## 5. Placement

**What this framework reads of the world.** The equal-cycle-sum characterisation of the price
system needs no single production; the drawn graph carries one independent cycle per process,
so the classical square system is the coincidence of two index sets and the per-commodity price
is a derived coordinate; a negative labour value is a statement about which net outputs the
technique can deliver; and fixed capital is the position graph carrying an age, with
straight-line depreciation as the zero-rate member of a family.

**What the classical account reads of it.** The price equations under joint production, the
possibility of negative labour values and their connection to inferior processes and to
separability, the possibility that no positive price system exists at any rate, the inequality
formulation, and the depreciation schedule as an annuity rather than a straight line.

| cell | content |
|---|---|
| **A** | Steedman's example and every number in it; negative values as a statement about what can be produced separately, which that literature reaches through separability and the cone of feasible net products; the existence of systems with no positive price system; and the non-linear depreciation schedule, which is Sraffa's Part III. This side derives them from one equation about cycle sums; that account has them already |
| **D2** | **What kind of object a per-commodity number is.** The debate asks which redefinition of labour value is the right one for joint production, and each proposal answers with a new definition. Here the primitive is the field on edges, the per-commodity number is a coordinate that exists when the index sets coincide, and the redefinitions are attempts to restore a coordinate the technique does not supply. The question is that tradition's own and the typing is not in it |
| **D** | That the characterisation survives joint production untouched; `b₁ = n` against `m`, with the square assumption read as `b₁ = m`; and the observation that where a price turns negative the logarithmic field is undefined on that edge while the identity between the legs still holds. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

**Where a specialisation and an account's own statement of itself come apart.** As in B68 and
B69: the place to look first is the explanation the narrower account gives of its own result,
which causal claim carries the weight, whether a term keeps one sense from premise to
conclusion, and whether the instrument takes the object the claim is about.

## 6. Related work

The joint production system, the fixed-capital treatment and the depreciation annuity are
Sraffa's (1960), Parts II and III. The example read back in §7 is Steedman's (1975), and the
exchange it started runs through Morishima (1976), Wolfstetter (1976) and Steedman's two
replies (1976a, 1976b); Steedman (1977) is the book-length statement. The conditions under
which labour values stay positive are Schefold's all-productive systems (1978, 1989), with the
two-commodity case in Wolfstetter (1976) and the general case in Hosoda (1993); Filippini and
Filippini (1982) is the companion. Morishima (1976) answers with true values, defined by a
minimisation; Kurz (1979), Krause (1980) and Flaschel (1983) redefine the value vector in other
ways. The inequality formulation is von Neumann's (1945). Kurz and Salvadori (1995) is the
standard modern treatment. The results this file rests on are Theorem 1 and Theorem 2 of
[`b1_theorem.md`](b1_theorem.md), Theorem 12 of
[`b67_prices_of_production.md`](b67_prices_of_production.md), Theorem 13 and Corollary 13.4 of
[`b68_value_field.md`](b68_value_field.md), and Corollary 14.2 of
[`b69_okishio.md`](b69_okishio.md).

- Filippini, C. and Filippini, F. (1982). Two Theorems on Joint Production.
  *The Economic Journal* 92(366), 386-390.
- Flaschel, P. (1983). Actual Labour Values in a General Model of Production.
  *Econometrica* 51(2).
- Hosoda, E. (1993). Negative Surplus Value and Inferior Processes.
  *Metroeconomica* 44, 29-42.
- Krause, U. (1980). Abstract Labour in General Joint Systems. *Metroeconomica* 32, 115-135.
- Kurz, H. D. (1979). Sraffa after Marx. *Australian Economic Papers* 18, 52-70.
- Kurz, H. D. and Salvadori, N. (1995). *Theory of Production.* Cambridge University Press.
- Morishima, M. (1976). Positive Profits with Negative Surplus Value: A Comment.
  *The Economic Journal* 86(343), 599-603.
- von Neumann, J. (1945). A Model of General Economic Equilibrium.
  *The Review of Economic Studies* 13(1), 1-9.
- Schefold, B. (1978). Multiple Product Techniques with Single Product Properties.
  *Zeitschrift für Nationalökonomie* 38, 29-53.
- Schefold, B. (1989). *Mr Sraffa on Joint Production and Other Essays.* Unwin Hyman, London.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press.
- Steedman, I. (1975). Positive Profits with Negative Surplus Value.
  *The Economic Journal* 85(337), 114-123.
- Steedman, I. (1976a). Positive Profits with Negative Surplus Value: A Reply.
  *The Economic Journal* 86(343), 604-608.
- Steedman, I. (1976b). Positive Profits with Negative Surplus Value: A Reply to Wolfstetter.
  *The Economic Journal* 86(344), 873-876.
- Steedman, I. (1977). *Marx after Sraffa.* New Left Books, London.
- Wolfstetter, E. (1976). Positive Profits with Negative Surplus Value: A Comment.
  *The Economic Journal* 86(344), 864-872.

## 7. The known answer and the structural checks

`experiments/b70_joint_production.py`, record `results/b70_joint_production.json`, which
carries the configuration it ran under. Seed 0; a run takes a few seconds and a second run
writes the same bytes. The random systems are square, 2 to 6 processes, each process with a
main product and a drawn amount of joint output, kept only when productive. All six pass.

**B70-5, a known answer: Steedman's example.** Two processes: `5` of commodity 1 and one unit
of labour give `6` of commodity 1 and `1` of commodity 2; `10` of commodity 2 and one unit of
labour give `3` of commodity 1 and `12` of commodity 2. **Ten published numbers are read back
with a worst gap of exactly zero**, the arithmetic being integer: the labour values `(−1, 2)`;
the activity levels `(5, 1)` that deliver the net product `(8, 7)`; total labour `6`; the
workers' bundle `(3, 5)`, which would need activity `(9, −2)` and so carries a variable capital
of `7`; the capitalists' bundle `(5, 2)`, which would need activity `(−4, 3)` and so carries a
surplus value of `−1`; and the same `−1` again as `L − V`. **The rate of profit comes out at
exactly `0.20` with prices `(1, 3)` and a wage of `3`**, so the system has positive profits and
a negative aggregate surplus value at once. The wage basket `(0.5, 5/6)` times the six units of
labour is the workers' bundle exactly; the paper prints the second entry rounded to `0.83`.

**B70-6, the structural checks.**

- **B70-6a, Theorem 15(1).** 400 systems at five rates, 2,000 solvable points. The sale leg
  equals `(1 + r)` times the cost of the input bundle within `4.7e-16` at every point.
  **Where both legs are positive the cycle sums are all `log(1 + r)`**, within `7.1e-14`, at
  1,969 of 1,969. The other 31 points have a non-positive leg: **joint production can push a
  price below zero, and there the logarithmic field is undefined on that edge while the
  identity between the legs still holds.**
- **B70-6b, Theorem 15(2).** `b₁ = n` on all 400 systems, and `B − A` has full rank on all 400.
  **Drop a process and the price vector is undetermined on a subspace of dimension exactly
  one**, on 326 of the systems large enough to test; **add a process and there is no exact
  solution**, on 326 of 326, the smallest least-squares residual `2.4`.
- **B70-6c, Theorem 15(3).** 153 of the 400 systems have a negative labour value, and **on
  every one of them the activity that would deliver one net unit of that commodity alone has a
  negative component**, 153 of 153. In the other direction, 37 systems have a non-negative
  inverse and **all of their labour values are strictly positive**, 37 of 37. The most negative
  value seen is `−2.98`.
- **B70-6d, how many rates carry a positive price vector.** Each system is read twice, once
  with its own output matrix and once with the identity in its place. **Under single production
  every system has exactly one stretch of such rates and it begins at zero**, 400 of 400.
  **Under joint production 52 of the 400 have no such rate at all** and the other 348 have one.
  So on these draws joint production does not multiply the rate, it removes it: a system can be
  productive and still admit no rate of profit whatever at which the wage and every price are
  positive. **Several disjoint stretches are possible and did not occur in this sample; that is
  reported rather than claimed either way.**
- **B70-6e, Corollary 15.1.** A machine lasting five periods. At `r = 0` the schedule is
  `1.8125, 1.45, 1.0875, 0.725, 0.3625`, **straight-line to `1e-10`**. At positive rates the
  departure from straight-line grows monotonically: `0.0119` at `r = 0.02`, `0.0295` at `0.05`,
  `0.0578` at `0.10`, `0.1109` at `0.20`, as a fraction of the new machine's price.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts above are counts on drawn systems: they show that a shape occurs and that the
statements hold where they are claimed to, and they are not frequencies in any economy.

## 8. Scope

Square systems throughout the drawn checks: `n = m`. The rectangular cases are handled by
counting ranks, not by solving them; the inequality formulation that belongs to `n > m` is done
in [`b71_von_neumann.md`](b71_von_neumann.md) for the square case and in
[`b75_rectangular_programme.md`](b75_rectangular_programme.md) for the rectangular one, not
here. Constant returns to scale, circulating capital apart from the
machine of §3, and homogeneous labour, as in B67, B68 and B69. The machine in §3 has constant
efficiency; declining efficiency is the same construction with the output coefficients varying
by age, and it is not run here.

**What this file does not do.** It does not implement or score any of the redefinitions of
labour value for joint production, Morishima's true values among them. It says when a
per-commodity number exists and what it is when it does not, and it leaves to that tradition
the question of which substitute to prefer. It measures no technique, no rate of profit and no
depreciation schedule in any economy.
