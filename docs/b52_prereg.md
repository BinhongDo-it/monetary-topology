# B52 pre-registration: the class square across the European reporting area

B49 read a class square on two carriers that cannot be resold, over three years
and thirteen countries, and found no cell at the rival's point prediction. That
prediction is sharp: if the terms attached to a position are the difference of a
scalar potential over positions, every closed loop sums to exactly zero, however
large the terms themselves are. A square is the smallest such loop, and this one
is built from four posted prices:

```
S = [ log P(household, electricity) - log P(household, gas) ]
  - [ log P(industry,  electricity) - log P(industry,  gas) ]
```

The two commodities arrive through a metered network, so a household cannot
resell to an industrial buyer at the industrial price, and the split between the
two classes is imposed by the tariff rather than chosen by either party. That is
what makes the four prices four distinct positions rather than one price quoted
four times.

This station runs the same square on the widest panel that publishes all four
legs on one basis: Eurostat's bi-annual energy prices, the whole reporting area,
every semester it covers.

## 1. Criteria

| | asks | kind | FAIL |
|---|---|---|---|
| **B52-1** | the panel is complete, printed country by country | `instrument` | a leg is missing without being named |
| **B52-2** | the square does not move with the currency the prices are quoted in | `instrument` | the gap between the two quotations exceeds what a shared scalar can leave behind |
| **B52-3** | no readable cell sits at the rival's point prediction of exactly zero | `rival` | **a readable cell reads exactly zero** |
| **B52-4** | every cell at or below the measured floor is named and carries no verdict | `bookkeeping` | a cell below the floor is scored either way |
| **B52-5** | the sign drift is one-directional, in the shape B49 read it: one of the two directions is empty | `own_reading` | both directions are populated |
| **B52-6** | the same question on one window every country shares for its whole length | `own_reading` | as above |
| **B52-7** | the same question stopped before the 2021 wholesale move, so that the drift has a basis independent of the interventions | `own_reading` | as above |

Three states throughout: readable and scored, readable and at the rival's
prediction, and **below the instrument's floor, which carries no verdict at
all**. The third state is the one that has to exist: a continuous quantity read
at a threshold cannot be reported as a zero merely because the instrument stops
there.

`B52-2` is an implementation check and not an independent confirmation. Where a
country already quotes in euro the conversion is the identity and the comparison
carries nothing; those cells are counted and named as vacuous.

## 2. The four numbers before the run

**No estimator, no band.** The prediction under test is a point, exactly zero,
so the gate that asks whether an instrument can separate an estimate from a
registered band does not apply here, and neither does a power calculation: there
is no sampling distribution for a quantity that is predicted to be identically
zero. What replaces both is a **resolution floor**, measured rather than
declared.

**The floor.** Each of the four prices is published to a fixed number of decimal
places, and the same square computed from prices quoted in a second currency
must return the same number up to what one shared scalar per country and
semester can leave behind. The largest such residual over the panel is the
floor. Only euro is admitted for this: the purchasing-power unit is not a single
scalar per country and semester, so a residual computed against it would carry
structure of its own and would set the floor far too high.

**Independent count.** Four positions, four edges, so `b_1 = 4 - 4 + 1 = 1` per
country. **The independent number is the number of countries, not the number of
cells**: the semesters of one country are repeated readings of one loop.

**Reachability.** Every branch is reachable before the run. A cell can read
above the floor, at exactly zero, or below the floor; the drift arms can find
one direction empty, both populated, or no country turning at all.

## 3. Carrier and basis

Eurostat's bi-annual energy prices, public dissemination endpoint, no key.
`nrg_pc_204` and `nrg_pc_205` for household and non-household electricity,
`nrg_pc_202` and `nrg_pc_203` for household and non-household gas, at the
standard reference bands `KWH2500-4999`, `MWH500-1999`, `GJ20-199` and
`GJ10000-99999`. Seven aggregate codes are dropped by name so that no aggregate
is read as a country. **One tax code on both legs, always**: reading household
prices with all taxes against non-household prices net of recoverable ones would
measure the tax convention rather than the price. All three tax codes are
computed and the differences between them are the part of a class difference
that taxation writes.

A semester price is an average over six months, not a price on a date. That is a
limit on dating, not on precision.

The record `results/b52_europe_class_square.json` carries the criteria wording,
the configuration this run used, and every quantity it produced.
