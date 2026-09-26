# B87: demand's grip on the field is combinatorial, and it is one dimension per land

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b87_demand_grip.py`, record `results/b87_demand_grip.json`, which
carries the configuration it ran under. Paper station: zero data. B72's envelope
solver, land generator, graph builder and Betti number are imported rather than
rewritten, so a disagreement between the two stations is a real one.**

## 0. The registration this station answers

[`b86_non_substitution.md`](b86_non_substitution.md) proved that with one primary
factor, single-product methods and constant returns, demand moves nothing on the
price side at all: not a price, not a square, not `rho`, not `b1`. It then registered
the obvious next question and, with it, a guess:

> a second primary factor is a second potential, so the field stops being one function

**The guess is wrong, and [`b72_land_and_rent.md`](b72_land_and_rent.md) already had
the right shape.** Two of its results settle it before any measurement:

```
Theorem 17(1)   land is a position no cycle produces, a pendant vertex under
                extensive rent, and b1 counts operated methods only
Theorem 17(3)   non-negative rents pin the wage to the lower envelope of the
                lands' own wage curves
```

So the second factor's price is not a free dimension. It is pinned, and the field is
still one function. **What is not pinned is which lands are in use, and that is the
thing demand fixes.** Theorem 17(3) assumes all `k` lands are cultivated, and that
assumption is exactly where demand enters.

## 1. Setup

`k` lands, each with a corn method `(alpha_i, lambda_i)` and unit capacity, plus
`n` other produced goods with one method each. Rate `r` fixed. Order the lands by
their own wage curves `w_i(r)`, best first. A demand `d` for corn calls up the best
`ceil(d)` lands; call that set `S`, the **cultivated set**. On `S`, B72's solver
returns the wage, the marginal land and the rents.

## 2. Theorem 31

**(1) Demand acts on the field only through `S`.** The solve takes `S` and `r` and
nothing else, so any two demands calling up the same lands give the same wage, the
same rents and the same prices.

**(2) That action is a step function with at most `k` values.** `S` is nested and
increasing in `d`, so the field is constant between thresholds and jumps at them.
**The object demand moves is combinatorial, and a combinatorial object has a
countable set of values and locatable jump points.**

**(3) The graph's dimension is the number of operated methods**, `b1 = |S| + n`. A
land is bought by exactly one bundle under extensive rent, so attaching it raises the
vertex and the edge count together and leaves `b1` where it was. What moves `b1` is
the process that works the land.

**(4) Hence each extensive step costs one dimension**, and this is Theorem 30(4)
turned over. With one primary factor demand can neither create nor destroy an
obstruction. With a scarce second factor it moves the dimension of the obstruction
space, one at a time, by calling up one more method.

**(5) The intensive margin costs two.** Once every land is in use, further demand is
met by a second method on the best land. That land is then bought by two bundles, it
stops being pendant, and by B72's Corollary 17.1 the second edge closes a cycle. So
the step adds a process and a cycle at once: `b1` rises by two. **Intensive rent
arrives in this framework as a step of the demand sweep, not as a separate model.**

**(6) What is claimed is the dimension.** Whether any particular cycle sum is
non-zero is a reading and a different question. Theorem 31 says how many independent
cycles there are and where the count changes.

## 3. What the checks read

**Seven criteria, all passing** at `seed 87`, 200 systems, `k` from 2 to 6, 985 steps.

| | criterion | reading |
|---|---|---|
| `B87-1` `known_answer` | full cultivation is B72's Theorem 17(3) | on `200 / 200` systems the last extensive step returns B72's wage and B72's marginal land, worst wage gap `0.00e+00` |
| `B87-2` `own_reading` | the cultivated set is nested and takes at most `k` values | nested at every step on `200 / 200`, with exactly `k` distinct values, `k` running 2 to 6. **Counted, not argued from the way the sweep is built** |
| `B87-3` `own_reading` | `b1 = \|S\| + n`, from the drawn graph | agrees on `985 / 985` steps, computed from B72's incidence matrix. **Its control is one land worked by two processes**, where the builder returns `4` against `3` for the extensive case, so the measurement is live |
| `B87-4` `own_reading` | the field is still inside a step and moves across one | `1570` demand pairs inside a step move the wage by at most `0.00e+00`; `585` adjacent pairs across a step move it by at least `2.16e-04`. **Both halves required** |
| `B87-5` `own_reading` | the ladder, printed rather than counted | `[3,4,5,6,7,9]`, `[3,4,5,6,8]`, `[3,4,5,7]`, `[3,4,6]` and 196 more. **`+1` at every extensive step and `+2` at the intensive one, on `200 / 200`** |
| `B87-6` `instrument` | the thresholds are where they are computed to be | each of `585` is probed at `±1e-06` in demand and the cultivated set has `m` lands below and one more above, on `585 / 585` |
| `B87-7` `bookkeeping` | write-back | B86's file names this station against the registration it opened, including why its guess was the wrong shape |

**`B87-4` is two clauses on purpose.** A field that never moved is also what a demand
that never reached the solve would look like, so the constant half alone is a check
that cannot fail. The second half is what says the steps are steps.

**`B87-3` is measured against a closed form the run does not trust.** The formula
handed back to itself would pass on any graph the builder drew, so the check computes
`b1` from B72's incidence matrix and compares. The `-1` that the design carried was
wrong by one and the measurement is what said so, which is the point of drawing the
graph.

## 4. Placement

**A.** That land rent is intensive past the extensive margin, and that the wage sits
on the lower envelope, are Ricardo's and Sraffa's.

**D.** That demand's whole action on a price field is the choice of a cultivated set,
so it is a step function with a countable value set and locatable jumps; that the
dimension of the obstruction space is the count of operated methods, so each
extensive step costs exactly one; and **that the extensive-to-intensive transition is
visible as a step of size two in a single running count**. None of the three has an
analogue in an account with no field in it: an account without `b1` has nothing for
the step size to be a size of.

**C is empty and this station cannot produce it**: it reads no data.

## 4a. The field at the intensive step, supplied 2026-09-13

**Done at** [`b88_two_margins.md`](b88_two_margins.md), **Theorem 32**, which imports B73's
intensive pair alongside this station's machinery. Two things come back here, and the second
corrects this station:

- **The cycle does not just add a dimension, it replaces the boundary condition.** With `k`
  lands cultivated there are `k` price equations in `k + 1` unknowns, and B72's zero rent on the
  marginal land supplies the missing one. The mixed system has `k + 1` equations in the same
  `k + 1` unknowns, **so it closes itself and the boundary condition has nowhere to go**.
  Keeping it would over-determine the system, and on 12,009 drawn configurations the rent it
  would set to zero comes out at least `8.0e-05` away from zero. **So the land that was
  marginal starts paying rent: free land disappears at the intensive margin**, strictly, on
  3,917 of 3,917 viable configurations.
- **Putting the second method on the best land was a fiat and it is wrong.** With one
  intensification technology per system, the acre that takes it is the most fertile one on only
  558 of 1,762 systems and the marginal one on 406, and the order of fertility differs from the
  order by intensive closure on 599 of 1,498. **This station's graph reading survives, because
  any acre with two users closes a cycle whichever acre it is**, and its field reading would
  not have.

## 5. Scope

**At the intensive step this station claims the graph and not the field.** Two
methods on one land need the extra equation of B72's Corollary 17.1, which this
station does not carry, so `B87-4` and `B87-6` are restricted to extensive steps and
say so in their own detail lines. `B87-3` and `B87-5` cover the intensive step
because the graph is drawn there and the Betti number is read off it.

Unit capacity per land, one corn method per land, `n = 2` other produced goods with
one method each, a single rate. The counts in section 3 are properties of the
generator, not of any economy. **Theorem 31(1) to (6) are algebra and are not.**
