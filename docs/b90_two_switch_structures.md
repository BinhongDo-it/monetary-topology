# B90: the rate moves two orders on one system, and they switch at different rates

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b90_two_switch_structures.py`, record
`results/b90_two_switch_structures.json`, which carries the configuration it ran under. Paper
station: zero data. B72's envelope solver and land generator, B73's intensive pair and B89's row
builder are imported rather than rewritten.**

## 0. The question this station answers

[`b88_two_margins.md`](b88_two_margins.md) and [`b89_degrees_of_freedom.md`](b89_degrees_of_freedom.md)
both run at one rate, and B88 registered a second rate as the interface to reswitching. Sweeping
it turns up three things, and only the third is the one the registration expected.

## 1. Setup

`k` lands of unit capacity with their own methods, one intensification technology, corn the unit
of account. At each rate on a grid of 601 points to `3.0`, read three things: whether every land
can be worked at a positive wage, which land owns the extensive envelope, and which acre if any
could take a second method whose closure lies on or below that envelope. **Every switch reported
is bisected from the grid interval it was spotted in**, so the grid finds candidates and does not
decide them.

## 2. Theorem 34

**(1) The intensive margin closes below the extensive one.** Every land is workable up to the
rate at which the worst land's own wage curve reaches zero. The intensive closure stops lying
under the envelope strictly below that, on almost every system.

**(2) So there is a band of rates in which demand above capacity cannot be met at all.** Every
land is workable there and no acre can take a second method, so by Theorem 33 the configuration
is `(j, f) = (0, 0)`: **the rows are consistent, the extra output is not produced, and the wage
is not determined by cost.** B89 named that cell from the counting; this reaches it from the
rate.

**(3) The viable set of rates need not be an interval.** On some systems the margin closes as
the rate rises and opens again above it. **That is reswitching, of the margin rather than of a
technique**, and it is not the same phenomenon as a change in which acre is taken.

**(4) There are two orders on one system and they are not the same order.** Which land owns the
extensive envelope and which acre takes the second method both switch in the rate, and they
almost never switch at the same rate. **Neither is a reparametrisation of the other.**

## 3. What the checks read

**Seven criteria, all passing** at `seed 90`, 500 systems, `k` from 3 to 5, a rate grid of 601
points to `3.0` and 50 bisection steps.

| | criterion | reading |
|---|---|---|
| `B90-1` `known_answer` | the state function is B72's answer at B88's rate | at `r = 0.05` the envelope wage and the marginal land agree with B72's own solver on `500 / 500`, worst gap `0.00e+00` |
| `B90-2` `own_reading` | **the band** | the intensive margin closes strictly below the extensive one on `357 / 362` systems where both open, by a median of `0.295` in the rate, and within one grid step on `5`. **The band is checked rate by rate and not inferred from two endpoints**: `0` of the 357 contain a rate at which some acre is viable after all |
| `B90-3` `own_reading` | **the viable set need not be an interval** | `326` systems with one block, `28` with two, `5` with three, `3` with four, `138` with none. **Printed as intervals**: `[[0.0, 0.365], [0.4, 0.535]]`, `[[0.0, 0.135], [0.31, 0.64], [0.875, 0.905]]`, `[[0.0, 0.175], [0.625, 0.705]]` |
| `B90-4` `own_reading` | **two switch structures** | both orders switch on `100` systems and **share a grid interval on `1`**; only the envelope owner on `164`, **only the intensified acre on `79`**, neither on `157` |
| `B90-5` `instrument` | **the switches are located, not read off the grid** | `557` switches bisected, widest remaining bracket `4.4e-16` against a grid step of `0.005`, a factor of `1.1e+13` |
| `B90-6` `own_reading` | the band is B89's cell | at a rate inside the band, B89's own row builder returns its indeterminate cell on `357 / 357` |
| `B90-7` `bookkeeping` | write-back | B88 and B89 each name this station |

**`B90-4`'s load-bearing count is the 79 and not the 1.** A shared interval count of one out of a
hundred could be read as the two orders switching together and this station missing it; the 79
systems on which the acre switches while the envelope never does cannot be that, because there is
no envelope switch there to be seen through another variable. **A mutation that shadowed every
acre switch with an envelope switch one interval along passed the first version of this criterion
and is caught by this one.**

**`B90-2` is checked rate by rate for the same reason.** Subtracting the two upper endpoints gives
a band even when the viable set has holes in it, so a system whose margin reopens would report a
band that contains viable rates. Walking the band and reading the state at each point is what
rules that out, and it costs nothing since the states are already computed.

**Eight mutations, all eight caught.** Two of them needed the criteria strengthened first: the
band measured from the first viable block instead of the last, and B90-4 with its 79-count clause
removed.

## 4. Placement

**A.** That the order of fertility can switch with the rate is B72's and the classical
literature's.

**D.** That the intensive margin has a switch structure of its own, essentially disjoint from the
extensive one; that the viable set of rates for the intensive margin need not be connected, which
is reswitching of a margin rather than of a technique; and **that between the two closing rates
lies a band in which the price system is consistent, one-dimensionally indeterminate, and unable
to meet the demand that put the system there**. None of the three has a place in an account that
carries one margin at a time.

**C is empty and this station cannot produce it**: it reads no data.

## 5. Scope

One intensification technology per system, unit capacity per acre, corn the only good on the land
side, `k` from 3 to 5, and a rate grid to `3.0`. Whether the four-block systems have more blocks
above `3.0` is not read here. The counts in section 3 are properties of the generator.
**Theorem 34(1) to (4) are statements about drawn families and the mechanism behind each is
stated, but only (2) is algebra**: (1), (3) and (4) are read off the draws and are reported as
such.
