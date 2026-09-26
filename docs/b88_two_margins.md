# B88: the two margins cannot both be open, because they supply the same missing equation

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b88_two_margins.py`, record `results/b88_two_margins.json`, which carries the
configuration it ran under. Paper station: zero data. B72's envelope solver and land generator
and B73's intensive pair are imported rather than rewritten, so a disagreement between the three
stations is a real one.**

## 0. The registration this station answers

[`b87_demand_grip.md`](b87_demand_grip.md) swept demand over a set of lands and found that the
last step, past full extensive cultivation, puts a second method on one acre and raises the
first Betti number by two rather than one. **It drew the graph at that step and did not solve
it**, because two methods on one acre need the extra equation of
[`b73_two_extensions.md`](b73_two_extensions.md)'s Corollary 17.1, which B87 does not carry.

B73 has it. Joining the two gives a constraint neither station could state alone, and it
corrects B87 on a second point as well.

## 1. Setup

`k` lands of unit capacity, corn the unit of account, the rate `r` fixed. Land `i` worked by its
own method produces one corn per acre from `a_i` corn and `l_i` labour:

```
1 = (1 + r) a_i + w l_i + rho_i
```

A second method on acre `i` uses `c a_i` corn and `d l_i` labour and yields `q > 1`:

```
q = (1 + r) c a_i + w d l_i + rho_i
```

The same `rho_i` in both: one price per position, which is where the content is.

## 2. Theorem 32

**(1) The extensive system is short by one and the mixed system is square.** With every land
cultivated there are `k` equations in the `k + 1` unknowns `(w, rho_1 ... rho_k)`. B72's
Theorem 17(3) closes it with a boundary condition, the zero rent on the marginal land. Add the
second method and there are `k + 1` equations in the same `k + 1` unknowns.

**(2) So the boundary condition is displaced, not dropped by choice.** A system that is square
and also carries the boundary condition is over-determined by exactly one. B73's Theorem 18(4)
said a boundary condition and a cycle closure are what close the two systems; **put both on one
system and they are alternatives, because they supply the same one missing equation.**

**(3) Hence free land disappears at the intensive margin.** The rent the boundary condition
would have set to zero is now whatever the mixed system says it is, and what it says is strictly
positive whenever the configuration is viable at all. **The land that paid nothing starts paying.**

**(4) Viability is B72's envelope rule applied to a closure.** Write `w_int` for the wage the
pair returns, `w_own` for the acre's own wage curve and `w_ext` for the extensive envelope. Then
`w_int <= w_ext` if and only if every rent is non-negative, since a rent falls in the wage and
the marginal one is zero exactly at `w_ext`. **The pair must lie on or below the envelope, the
same rule B72 gave for lands.**

**(5) Three thresholds, four cells, and the third is new.**

```
w_int <= 0            the pair is not a system at all
w_int >  w_own        the second method is not worth operating on its own acre
w_ext <  w_int <= w_own   it pays on its own acre and is infeasible for the system
w_int <= w_ext        viable, and no land is free
```

**The third cell is what a one-land model cannot see.** The second method earns a non-negative
rent where it stands and still drives another land's rent below zero, **because what it moves is
the whole system's wage and not just its own acre's rent**.

**(6) Which acre takes it is decided by the closure and not by fertility.** The two orders are
different orders, so B87's choice of the best land was a fiat.

## 3. What the checks read

**Seven criteria, all passing** at `seed 88`, 3,000 systems, `k` from 2 to 6, 12,009 mixed
configurations.

| | criterion | reading |
|---|---|---|
| `B88-1` `known_answer` | the imported pieces are the imported pieces | the rent written on a land not being intensified reproduces B72's own to `0.00e+00` over 3,000 systems; a pair solved by hand at `q = (1, 1.5)`, `a = (0.2, 0.5)`, `l = (0.4, 0.9)`, `r = 0` gives `w = 0.4`, `rho = 0.64` and the solver agrees to machine precision |
| `B88-2` `own_reading` | **the counting, and the over-determination** | shapes printed rather than counted: extensive `k -> k` by `k+1` at every `k` from 2 to 6, mixed `k -> k+1` by `k+1`. **The rent the boundary condition would zero comes out at least `8.0e-05` from zero over 12,009 configurations, against exactly `1.1e-16` on the extensive control** |
| `B88-3` `own_reading` | four cells, all occupied | not worth operating `2478`, **profitable on its own acre and infeasible for the system `1703`**, viable `3917`, wage non-positive `3911` |
| `B88-4` `instrument` | the equivalence | `w_int <= w_ext` and `every rent >= 0` agree on `8098 / 8098`. **An implementation check and not a reading** (`D35` second clause): the two statements are one statement, and what this can catch is the code not implementing it |
| `B88-5` `own_reading` | **no free land** | the formerly marginal land pays a strictly positive rent on `3917 / 3917` viable configurations, the smallest `1.5e-04`. **Not implied by viability**, which would be satisfied by a rent of exactly zero, and a rent of exactly zero is what a boundary condition surviving the step would look like |
| `B88-6` `own_reading` | **which acre, and B87's fiat** | one intensification technology per system, so the choice is a reading. The acre taken is the most fertile on `558 / 1762` and the marginal one on `406`; the two orders differ on `599 / 1498`; **the two choosing rules, run over the same candidates, part on `305 / 1762`** |
| `B88-7` `bookkeeping` | write-back | B87, B73 and B72 each name this station |

**`B88-2` is the load-bearing one and it is measured against a control.** A solver tolerance
would show as a small number on both runs. The extensive run gives `1.1e-16` on the same
quantity and the mixed run gives at least `8.0e-05`, four thousand times larger at its closest,
so this is two closures disagreeing.

**`B88-6` counts where two rules part rather than where one rule lands.** Reporting only that
the fertile acre is taken 558 times out of 1,762 would not separate "the closure chooses" from
"the closure agrees with fertility and the fertile acre is often not a candidate", since both
rules run over the viable set. Running both and counting the disagreements does.

## 4. Placement

**A.** That intensive rent is determined by two methods used side by side, and that the order of
fertility and the order of rentability need not agree, are Sraffa's and the classical
literature's.

**D.** That a boundary condition and a cycle closure are the same missing equation, so a system
cannot carry both; that free land therefore disappears at the intensive margin as a matter of
counting rather than of bargaining; and **that between the acre's own wage curve and the
extensive envelope there is a cell in which a second method pays on its own acre and is
infeasible for the system**. The last is invisible to a one-land treatment and has no place to
sit in an account with no field over positions.

**C is empty and this station cannot produce it**: it reads no data.

## 4a. The identity these two configurations are cases of, 2026-09-13

**Done at** [`b89_degrees_of_freedom.md`](b89_degrees_of_freedom.md), **Theorem 33**, which
counts every configuration at once rather than these two. Write `c` for the cultivated lands,
`j` for how many are worked by two methods and `f = 1` when some cultivated land still has spare
capacity:

```
equations - unknowns = j + f - 1
```

- **Square exactly when `j + f = 1`, and the two solutions of that are the two stations
  already on the board**: `(0, 1)` is B72 and `(1, 0)` is this one. Verified on 30 distinct
  shapes with `c` from 2 to 6.
- **`(j, f) = (1, 1)` and `(2, 0)` have no solution on every drawn system**, measured: the largest
  residual among the solvable cases is `4.4e-13` and the smallest among the rest is `3.0e-04`. So
  intensive cultivation does not coexist with spare capacity, and at most one acre is worked by two
  methods. **Both are classical and both fall out of the counting, in general position**: an
  over-determined system can still be consistent when the technical coefficients coincide exactly,
  which a random draw misses with probability one. B89-8 builds those exceptions from a recipe.
  Corrected 2026-09-13; the residuals above are unchanged.
- **`(0, 0)` leaves a one-dimensional family**, and its direction is `(1, -lambda)`: raise the
  wage by one and every rent falls by that land's labour input. **The single missing equation is
  the one that says where on the wage-rent frontier the economy sits**, which is why the
  intensive step adds a dimension to the graph and removes one from the price system.

## 4b. What the rate does, 2026-09-13

Everything above is at one rate. **Done at**
[`b90_two_switch_structures.md`](b90_two_switch_structures.md), which sweeps it:

- **The intensive margin closes below the rate at which the extensive one does**, on 357 of 362
  systems where both open at all, by a median of `0.295` in the rate. **In that band every land
  is workable and no acre can take a second method**, so demand above capacity is not met, and
  the configuration there is B89's indeterminate cell, checked with B89's own row builder on
  357 of 357.
- **The viable set of rates need not be an interval**: 28 systems of 500 have two blocks, 5 have
  three, 3 have four. **The margin closes as the rate rises and opens again above it**, which is
  reswitching of the margin rather than of a technique.
- **Which acre takes the second method and which land owns the envelope switch at different
  rates.** Both switch on 100 systems and share a grid interval on 1; the acre switches with no
  envelope switch anywhere on 79.

## 5. Scope

One quality of intensification per system, unit capacity per acre, a single rate, corn as the
only produced good on the land side. The cell counts in section 3 are properties of the
generator, not of any agriculture. **Theorem 32(1) to (6) are algebra and are not.** Which acre
an actual economy intensifies depends on the technologies actually available on each, which this
station draws rather than observes.
