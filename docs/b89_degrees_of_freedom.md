# B89: one identity covers every configuration of the two margins, and it has four cells

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b89_degrees_of_freedom.py`, record `results/b89_degrees_of_freedom.json`, which
carries the configuration it ran under. Paper station: zero data. B72's envelope solver and land
generator and B73's intensive pair are imported rather than rewritten.**

## 0. The question this station answers

[`b88_two_margins.md`](b88_two_margins.md) counted two configurations and found the extensive one
short by a boundary condition and the mixed one square. **Counting all of them at once turns that
into an identity**, and the identity says which configurations exist at all.

## 1. Setup

`c` cultivated lands of unit capacity, corn the unit of account, the rate `r` fixed. Write `j`
for how many of those lands are worked by two methods and `f = 1` when some cultivated land still
has spare capacity, so that a boundary condition applies, and `f = 0` when none has. The unknowns
are the wage and one rent per cultivated land, `c + 1` of them. The equations are one per operated
method, plus the boundary condition when `f = 1`.

**The station builds those rows itself and knows nothing about either imported solver.** The
solvers have to agree with the rows, not the other way round, which is what `B89-1` checks.

## 2. Theorem 33

**(1) The counting identity.**

```
equations - unknowns = j + f - 1
```

**(2) So the system is square exactly when `j + f = 1`, and for no other reason.** The two
solutions of that equation are the two stations already on the board: `(j, f) = (0, 1)` is B72's
extensive rent with a free margin, and `(1, 0)` is B88's mixed system with none.

**(3) Two classical facts are corollaries of the arithmetic rather than assumptions, in general
position.**

```
j >= 1 with f = 1   over-determined: intensive cultivation does not coexist with spare capacity
j >= 2              over-determined: at most one acre is worked by two methods
```

**(3a) And general position is where the corollary lives, not a hedge attached to it.** More
equations than unknowns leaves the extra rows to be satisfied by the rest, which takes an exact
coincidence among the technical coefficients. A random draw misses that with probability one, **so
the sweep in section 3 cannot meet an exception however large it grows**. They are built instead,
and the recipe is one line per cell. For `(2, 0)`, each acre's own pair of methods fixes the wage
at `[q - 1 - (1+r) a_i (c - 1)] / [l_i (d - 1)]`, so putting every acre's on one target by choice
of `l_i` makes four rows in three unknowns agree, with rents that stay non-negative. For `(1, 1)`,
the single choice `d = [q - (1+r) a c] / [1 - (1+r) a]` on the boundary acre puts its two methods
on the same wage and the zero rent costs nothing. **The identity in (1) is untouched**: counting
tells you a solution needs a coincidence, not that none exists.

**(4) The remaining cell is short by one, and the wage is then not determined by cost.** With
every acre full and no second method anywhere, `(j, f) = (0, 0)` leaves a one-dimensional family
of solutions.

**(5) That family has a direction, and the direction is the labour vector.** The null direction
is `(1, -lambda_1, ..., -lambda_c)`: raise the wage by one and every rent falls by that land's
labour input. **The single missing equation is the one that says where on the wage-rent frontier
the economy sits.**

**(6) Hence the demand ladder walks along the square cells and nowhere else.** While spare
capacity remains, `f = 1` and `j = 0`. Once it is gone, `f` drops to zero and `j` must rise to one
or **the wage and the rents are not pinned by cost alone**: `(0, 0)` is consistent and leaves the
one-dimensional family of (4), so what is missing is the condition that picks a point on it and
not a price system altogether. Corrected 2026-09-13. **B87's step of `+2` in the first Betti number is one dimension
for the added process and one for the cycle that replaces the boundary condition**, and (5) is
why those two are the same equation counted twice: the graph gains a cycle exactly where the
price system loses a degree of freedom.

## 3. What the checks read

All criteria pass at `seed 89`, 300 systems, `c` from 2 to 6, 6,276 configurations, and 40
constructed systems in each of the two excluded cells.

| | criterion | reading |
|---|---|---|
| `B89-1` `known_answer` | the two square cells are the two solvers' own answers | `(0, 1)` matches B72's envelope wage to `2.2e-15` over 1,046 cases and `(1, 0)` matches B73's pair to `4.5e-11`. **It caught a real fault**: the first version put the boundary condition on the last land in the list rather than on the marginal one, which disagrees with B72 whenever the list is not sorted by fertility |
| `B89-2` `own_reading` | the identity | holds on all 30 distinct shapes drawn, `c` from 2 to 6, **shapes printed rather than counted** |
| `B89-3` `own_reading` | **three states over the grid** | `(0,0)` a family of solutions on 1,046; `(0,1)` and `(1,0)` one solution on 1,046 each; `(1,1)`, `(2,0)` and `(2,1)` no solution on 1,046 each. **No cell is ever mixed.** These are drawn systems, so they are in general position and **this sweep cannot meet an exception**, which is what `B89-8` is for |
| `B89-4` `own_reading` | **the frontier** | the family is one-dimensional and its direction is `(1, -lambda)` to `1.3e-15` over 1,046 cases |
| `B89-5` `own_reading` | a separate second method per acre | on 234 systems with a viable acre, a mean of `1.72` acres are viable, the acre taken is the most fertile on `38`, and **the two choosing rules part on `61`**. Giving each acre its own technology does not make fertility the rule |
| `B89-6` `instrument` | **the line is measured** | the largest residual among cases with a solution is `4.4e-13`, the smallest among those without is `3.0e-04`, a ratio of `7.0e+08`. A tolerance chosen in advance would be a number this station made up |
| `B89-8` `own_reading` | **the excluded cells, built rather than drawn** | `(1, 1)`: `36 / 36` built are over-determined and consistent, worst residual `5.6e-15`, all with non-negative rents. `(2, 0)`: `35 / 35`, worst `2.2e-15`, `34` with non-negative rents. One instance returns a wage of `0.5693` with rents `[0.5611, 0.5668]` on four rows in three unknowns |
| `B89-7` `bookkeeping` | write-back | B88 and B72 each name this station |

**Clause (3) was published on 2026-09-13 without its general-position qualifier and carries it
the same day.** No measured quantity moved: the sweep reports what it reported, and what changed is
what the sweep is taken to establish, plus a criterion that exhibits the exceptions.

**Every mutation seeded was caught but one, which is an equivalent implementation rather than a
fault.** That one
reads the residual off the solver's own output instead of recomputing it. That output is empty
exactly when the system is square or rank-deficient, where the true residual is zero anyway, and
non-empty exactly in the over-determined full-rank cells, where it is the true residual, so it
returns the same verdict in every cell. **A mutation that changes no verdict is not a miss**, and
saying so is cheaper than adding a probe for a fault that is not there.

**`B89-5` needed two probes and the first version had one.** A fixture built so the closure order
matches the fertility order trips both of the criterion's clauses at once, so it cannot say which
one is load-bearing. Making the most fertile acre unviable as well trips only the clause that
counts where the two rules part, and that is the one that says the closure is choosing.

## 4. Placement

**A.** That intensive cultivation excludes a free margin, and that only one land can be
cultivated by two methods at a time, are Sraffa's and the classical literature's.

**D.** That both are one counting identity rather than two results; that the identity's remaining
cell is an indeterminacy of exactly one dimension whose direction is the labour vector; and
**that the graph gaining a cycle and the price system losing a degree of freedom are the same
event counted on two sides**. The last has nowhere to sit in an account with no graph in it.

**C is empty and this station cannot produce it**: it reads no data.

## 3a. The indeterminate cell reached from another direction, 2026-09-13

Theorem 33(4) says `(j, f) = (0, 0)` is short by one. **That cell is not a corner case**:
[`b90_two_switch_structures.md`](b90_two_switch_structures.md) sweeps the rate and finds a band
on 357 of 362 systems, a median `0.295` wide, in which every land is workable and no acre can
take a second method. **Taking a rate inside the band and building the rows with this station's
own builder returns the indeterminate cell on 357 of 357.** So the cell is where a real economy
sits whenever demand runs past capacity at a rate too high for any intensification to pay, and
the wage there is not determined by cost.

## 5. Scope

Unit capacity per acre, corn the only good produced on the land side, a single rate, at most two
methods per acre and at most two intensified acres in the grid. **The identity is stated for any
`j`**, and the grid tests `j` up to two, which is one past the point where it stops being square.
The cell counts in section 3 are properties of the generator. **Theorem 33(1) to (6) are algebra
and are not.**
