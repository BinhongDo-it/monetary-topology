# B96: basics are where the vertically integrated subsystems intersect

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b96_basics_and_subsystems.py`, record `results/b96_basics_and_subsystems.json`, which
carries the configuration it ran under. Paper station: zero data. B69's system generator, Perron
solver and labour values are imported rather than rewritten.**

## 0. Two objects the chain had not touched

**Sraffa's basics** (PCMC chapter six): a commodity is basic when it enters, directly or
indirectly, the production of every commodity. The classical results are that the maximum rate of
profit is fixed by the basic part alone and that a tax on a non-basic leaves the rest of the system
where it was.

**Pasinetti's vertically integrated subsystems**: for each good, the sub-economy delivering one net
unit of it with its whole chain of inputs.

## 1. Theorem 40

**(1) The maximum rate of profit is the basic part's alone, while the non-basic block's spectral
radius stays under the core's.** On the graph this is block triangularity: the non-basics use the
core and the core uses none of them, so the whole system's spectral radius is **the larger** of the
two blocks'. **Sraffa's result and an eigenvalue fact are the same statement**, and the condition
comes with it rather than being an extra assumption.

**(1a) And the condition is not decoration.** Sweeping one non-basic's own use across the core's
radius, the two rates agree on every cell below it and part on every cell above, the crossover
sitting within one grid step of the radius on every sweep. **A good no one else uses still caps the
system when it eats enough of itself**, which is Sraffa's Appendix B case. `A = [[0.2, 0.1], [0,
0.8]]` is the smallest instance: good 0 is the only basic, its part gives `R = 4`, and the whole
system gives `R = 0.25`.

**(2) A tax on a non-basic leaves the maximum rate and every basic price exactly where they were.**
The same tax on a basic moves both. **This carries (1)'s condition too, and on a tighter form of
it**: what has to stay under the core's radius is the non-basic block's radius **after** the tax,
so this boundary sits at the core's radius over the tax rather than at the core's radius itself.
**(2a)** Swept, a tax on the non-basic leaves the maximum rate on every cell below that place and
sets the rate on every cell above it, and the last harmless own use sits within one grid step of
it. **A good no one else uses can be made the one that caps the system by taxing it**, which is
Sraffa's Appendix B case reached by taxation rather than by technique.

**(3) The basics are exactly where the vertically integrated subsystems intersect.** A subsystem is
what one net unit of a good calls up; a good is basic when every good calls it up. **So the two
definitions are one reachability relation read along its two arguments**, and Sraffa's chapter six
and Pasinetti's construction meet on the graph rather than in the algebra.

**(4) A subsystem's labour content is the labour value.** `l [I − A]^{-1}` is B68's value field.
**What the subsystem adds is the set rather than the number**: which positions the unit calls up,
and that set is what (3) intersects.

## 2. What the checks read

All criteria pass at `seed 96`, 200 economies with an irreducible basic core and one or two
appended non-basics, and 40 further cores swept across the spectral boundary.

| | criterion | reading |
|---|---|---|
| `B96-1` `known_answer` | two anchors | on `15 / 15` systems from B69's own generator every good is basic, which is what irreducibility means; and a subsystem's labour content agrees with B69's own labour values to `8.9e-16` |
| `B96-2` `own_reading` | **the rate is the core's, under the condition** | the whole economy's maximum rate equals its basic part's on `200 / 200`, worst gap `0.00e+00`. **The condition holds on `200 / 200` by construction**: core radius at least `0.300`, non-basic block at most `0.099`. **So this generator cannot violate it and the count is worth nothing by itself**, which is what `B96-8` is for |
| `B96-3` `own_reading` | **the tax asymmetry, both halves, under the condition** | a tax on a non-basic leaves the rate on `200 / 200` and every basic price on `200 / 200`; **the same tax on a basic moves the rate on `200` and the basic prices on `200`**, the latter by a median of `0.102`. **Both halves counted on the same systems**, and the null half alone would be a check that cannot fail. **The null half is conditional too and on a tighter condition than `B96-2`'s**: it is the block's radius after the tax that has to stay under the core's, which holds on `200 / 200` by construction, core radius at least `0.300` against a taxed block at most `0.150`. **So that count is worth nothing by itself either**, which is what `B96-9` is for |
| `B96-4` `own_reading` | **the intersection** | the intersection of the subsystems equals the basics on `200 / 200`. Subsystem sizes run from `3` to `9` goods, so they are not all the whole economy and the intersection is not trivially everything |
| `B96-5` `own_reading` | the construction is not vacuous | every system carries a non-basic and a basic set strictly smaller than its good set, `200 / 200`, one non-basic on `107` and two on `93`. **Without a non-basic every statement above is vacuous** |
| `B96-6` `instrument` | the closure is a closure | the reachability relation reaches a fixed point on `200 / 200`, checked by running one more step; **and it is the indirect relation**, since on a chain of six goods where each enters only the next the first is reported as entering the last, which one step would not report |
| `B96-8` `own_reading` | **the spectral condition, on both sides** | one non-basic's own use swept from `0.02` to `0.95` over `40` cores, `1600` cells. Below the core's radius the rates agree on `853 / 853`; above it they part on `747 / 747`. The last agreeing value sits within one grid step (`0.024`) of the radius on every sweep, worst `0.018` |
| `B96-9` `own_reading` | **the taxed boundary, on both sides** | the same sweep read for the tax, `1600` cells. Where the taxed block's radius stays under the core's, a tax on the non-basic leaves the maximum rate on `564 / 564`; where the tax carries it over, the taxed non-basic sets the rate on `1036 / 1036`. The last harmless own use sits within one grid step (`0.024`) of the core's radius over the tax, worst `0.017`. **The boundary is at `0.6667` of `B96-8`'s, which is the tax itself, and that factor was written down before the sweep was read** |
| `B96-7` `bookkeeping` | write-back | B80 and B68 each name this station |

**Every mutation seeded was caught.** The ones worth naming: reading the reachability relation
along its other argument turns basics into their opposite and is caught by the chain probe;
keeping only the null half of the tax asymmetry leaves a check that cannot fail; and for `B96-8`,
a sweep that never crosses the boundary in either direction, or one where a cell above it still
agrees, is rejected. **`B96-9` is seeded the same three ways against its own, lower boundary**, and
its fixture is additionally required to hold a cell between the two boundaries, so that the two
arms are separated on it rather than scoring the same cells twice.

**`B96-2` was published without its condition on 2026-09-13 and carries it the same day.** The
measurement did not move: the generator holds the condition on every system it makes, which is
exactly why the arm could not fail and why the sweep now stands beside it.

**`B96-3` was published the same way and carries its own condition from 2026-09-14**, with `B96-9`
added beside it. Two things are worth saying plainly. The tax's boundary is not the same boundary:
it is lower by the tax, and that factor was written down before the sweep was read. **And the sweep
had been computing the taxed rate on every cell since it was written, with no criterion ever
reading that column**, so the arm cost no new sampling at all. The eight criteria that stood before
it reproduce field for field, and only `B96-3`'s wording moved.

## 3. Placement

**A.** Basics and non-basics, the tax result and the maximum rate belong to Sraffa; the vertically
integrated subsystem to Pasinetti.

**D.** That the two are one reachability relation read along its two arguments, so **the basics are
the intersection of the subsystems**; that Sraffa's rate result is block triangularity of the
spectrum, **condition and all**, so the condition is read off the same fact rather than assumed; and that a subsystem's content being the labour value is the number while the subsystem
itself is the set, which is what makes the intersection available at all. **An account with no
graph has the two objects in separate chapters.**

**C is empty and this station cannot produce it**: it reads no data.

## 4. Scope

B69's irreducible generator for the core, one or two non-basics that use the core and a little of
themselves, a tax of half again on one coefficient. **Theorem 40(1), (3) and (4) are argument;
(2) is checked here on a family where the non-basics do not enter the core by construction**, which
is what being non-basic means and is the only case the classical result claims. **(1a) is read off
the sweep**, whose own use runs from `0.02` to `0.95` against core radii from `0.30` up, **and (2a)
off the same sweep read for the tax**. Neither boundary is asserted: each is placed where the
spectra put it, and the second is the first divided by the tax.

[`b95_joint_lives.md`](b95_joint_lives.md) carries the same statement on a chain of machines: a
chain whose product nothing else uses is a non-basic, and its economic life stays out of the wage.
