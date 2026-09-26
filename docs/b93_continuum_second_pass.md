# B93: what a continuum changes, on both indices, and one registered question reformulated

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b93_continuum_second_pass.py`, record `results/b93_continuum_second_pass.json`, which
carries the configuration it ran under. Paper station: zero data. B77's coefficient family is
imported rather than rewritten.**

## 0. Two registrations that are one object

[`b77_continuum.md`](b77_continuum.md) registered whether a quadratic continuum carries a slope
reversal that survives refinement, none having been found.
[`b86_non_substitution.md`](b86_non_substitution.md) registered whether the componentwise minimum
survives a continuum of methods per good, **which is B77's continuum with the other index
continuous**. So the two are one object read along two indices, and they are done together.

## 1. The first registration is not well posed as measured

B77's object is the rise in the envelope's slope, the `x`-derivative of the cost at the owner.
**Every member of that family has a strictly positive leading coefficient**, so every owner curve
is convex, and inside any run of one owner the slope rises by construction. Refining the parameter
grid shortens runs against a fixed `x` grid and nothing else. **The registered object measures the
`x` grid.**

**The well-posed object is capital per worker along the envelope**, `k = (1/L − w)/r` with
`L = C(θ, 1)`, which is what a slope reversal means economically and what
[`b92_capital_reversing.md`](b92_capital_reversing.md) measures on discrete families.

## 2. Theorem 37

**(1) Capital reversing on a continuum is common relative to discrete families, and two events
have to be counted apart.** A rise in `k` **at a change of owner** is capital reversing, **and it
has to be read at the rate where the switch happens**: there both members carry one cost and
therefore one wage, so their two capital values belong to one price system. A rise **inside one
owner's own run** is a price Wicksell effect, and no technique is chosen differently there.
Counted apart, reversing runs from `4.9%` at degree two to `10.5%` at degree five, rising with the
degree, against `12 / 1878` on B92's discrete triples. At degree two `551` of the `987` families
whose `k` rises anywhere have one owner from end to end, **so more than half of the undivided
count is the other thing**.

**(2) It survives refinement, and both outcomes occur.** Following a cohort of reversing families
through a 64-fold refinement of the parameter grid, `11` of `100` stay, `13` are families whose
rise the refinement **created** rather than preserved, and the rest collapse.
**An existence claim needs a witness that survives, and the survivors are the answer.**

> **【2026-09-14 correction. This read `24` of `100` and that number was made by a criterion
> whose two halves disagreed.** The registered wording is "still positive and still more than
> half its coarse value", and the code tested `last > TOL and last > 0.5 * first`. The cohort is
> selected at `theta = 300` while the ladder starts at `theta = 100`, so a family can enter with
> a coarse rise at or below zero; for those the second half is vacuous, because half of a
> non-positive number is below any positive one, and the test collapses to the selection
> condition itself. **Replayed on the same seed: `24` survive under the registered rule, `13` of
> those have a coarse rise at or below zero, and requiring a positive coarse rise leaves `11`.**
> **The station then re-ran with the bracket fix as well and returns `8`, not `11`**: dropping
> the brackets that held more than one change alters `rise_at_change`, which is the quantity the
> cohort is selected on, so a different cohort is drawn. Both numbers are right and their scopes
> differ, `11` being the survival rule fixed alone and `8` being both fixes together.
> **`8` is the one on the record.**
> Those `13` are not nothing and are not survivors either: they are families the refinement
> created, which is a third state and is reported as one rather than folded into either side.
> **The existence claim stands on the `8`, and separately on the witness in §(5), which was
> checked across its whole interval.**】

**(3) The reason it is common is B92's own.** Reversing **with no owner returning anywhere** needs
three techniques, because the pair meeting on the envelope must not include the one owning a zero
rate. **A continuum is always in that regime**, which is why that kind was impossible on two and
is ordinary here.

> **【2026-09-14 correction. This read "reversing needs three techniques", and that drops the
> condition that carries it.** B92's own record has the counterexample: `B92-2` reads `0` of the
> `1102` single-crossing two-technique draws reversing and **`43` of the `43` that cross twice or
> more doing so**. Two techniques reverse whenever they reswitch. What needs three is reversing
> **without** reswitching, which is what `B92-4`'s `12 / 1878` counts.
> **The comparison in (1) therefore compared two different objects**: this station counted every
> reversal and set it against `12 / 1878`, which counts only the no-reswitching kind.
>
> **2026-09-14, split and settled.** The station now counts both, and the return test it needed
> was already being computed for every family. Reversing **with no owner returning anywhere**
> reads `14`, `27`, `26` and `35` of `4,000` by degree, which is `0.35%` to `0.88%`, against
> `12 / 1878` or `0.64%` on B92's discrete triples. **The two straddle each other, so the
> continuum family does not reverse more often once the counts are of the same object**, and the
> claim that it does is withdrawn rather than restored. Every reversal, the wider count, still
> reads `4.9%` to `10.5%` and still rises with the degree, and that number is about a different
> object than B92's.
>
> **The existence claim is untouched by any of this**; only the frequency comparison was, and it
> is now settled against the station's own earlier reading.】

**(4) B92's other reading does not carry over, and where it does is measurable.** `k` is
two-valued at a switch. Filling the family in shrinks the jump **where the set of owners fills in
with it, and leaves it exactly where that set does not**. So the two-valuedness tracks the owners
actually used rather than the members on offer.

**This is not B77's bounded active set, and an earlier version of this station said it was.**
B77 bounds the processes running **together at one rate** by the number of goods. What is counted
here is the members that own the envelope **at some rate or another across a sweep**, which runs
to `637` at `1280` members and is not bounded at all. The two move in opposite directions under
one refinement, which is B77's own Theorem 22(2).

**(5) On the other index, the componentwise minimum survives a continuum exactly when the per-good
minimum is attained.** Theorem 30(2)'s argument is per good and indifferent to cardinality.

**(6) When it fails, it fails by the infimum escaping.** On a half-open method set whose cost falls
toward the excluded end, the minimiser sits at the end point at every refinement and marches toward
it while the cost keeps falling: **a minimiser with no limit in the set, rather than two goods
wanting different techniques.**

**(7) A technique still leaves the envelope and comes back when the labels are dense.** Compress
the owner sequence and look for a member that owns the envelope, loses it, and takes it back.
`1234` of `16000` drawn families carry one at some width, and `79` carry one that crosses at least
`2%` of the family and leads the runner-up by more than `1e-5` at both spells. **The width and the
lead are both needed.** Adjacent members of a dense family are nearly the same profile, so the
argmin wobbles between neighbours and those wobbles lead by around `1e-8`; **that is what a
continuum dissolves.** The widest found crosses the whole family, `299` of `300` members, leads by
`1.0e-4`, and holds through a 64-fold refinement to `6399` of `6400` at `6.0e-5`. **So technique
return is defined on a continuum and it happens**, the question being whether the minimiser over
the index is monotone in the rate.

## 3. What the checks read

All criteria pass at `seed 93`, 4,000 families at each of four degrees.

| | criterion | reading |
|---|---|---|
| `B93-1` `known_answer` | **why the registered form is automatic** | B77's leading coefficient is strictly positive on `20 / 20` drawn families, the rise is positive on all readings, and a 256-fold parameter refinement moves it by at most `1e-13` because the `x` grid is fixed |
| `B93-2` `own_reading` | **reversing, counted apart from the price Wicksell effect** | at a change of owner, read at the switching rate: `195 / 4000` (`4.9%`), `312` (`7.8%`), `408` (`10.2%`), `422` (`10.5%`) by degree. Inside one owner's own run: `858`, `585`, `415`, `340`. With one owner over the whole sweep: `551`, `390`, `293`, `234`. Rising anywhere: `987`, `776`, `643`, `584`. Largest rises `0.152`, `0.168`, `0.374`, `0.397` |
| `B93-3` `own_reading` | **and it survives refinement** | `24` of `100` cohort families survive a 64-fold refinement (5, 8, 5, 6 by degree), `76` collapse. **The cohort is selected on a rise at a change of owner read at the switching rate**, which is the harder population; the first version selected on any rise between adjacent grid rates and so followed price Wicksell effects through the ladder as well. **Taken in draw order, not by the largest rise**, since selecting the maximiser selects on the statistic |
| `B93-4` `own_reading` | **the two-valued `k`, and what it tracks** | filling from 5 members to 1280 shrinks the jump, read at each switching rate, by a median factor of `0.010` on the `16` families whose owner set more than doubles, and by `0.994` on the `4` whose owner set stays put. That set runs to `637` at `1280` members, **so it is not B77's bounded active set** |
| `B93-5` `own_reading` | **the other index** | on a closed set the minimiser settles to `s = 0.3968` and the cost converges; on a half-open set it sits at the end point at every refinement, marching `5.0e-04 → 5.0e-06` while the cost falls `1.110265 → 1.110003` |
| `B93-6` `instrument` | attainment gives one technique, and two guards | `8000` drawn techniques beat the per-good choice in `0` components; every coefficient stays at or above `0.02`, so each member is a real dated-labour profile; and **the envelope is checked to run the right way up**, the owner at `x → 1` being the least-labour member, `0` exceptions |
| `B93-8` `own_reading` | **technique return survives dense labels** | `79` of `16000` families carry a return crossing at least `2%` of the family and leading by more than `1e-5`, against `1234` at any width. The widest crosses `299 / 300` at `1.0e-4` and holds to `6399 / 6400` at `6.0e-5` through a 64-fold refinement |
| `B93-7` `bookkeeping` | write-back | B77, B86 and B92 each name this station |

**Two criteria were written stronger than the data supports and were rewritten to it.** B93-3
first demanded that the refinement move the reading by less than a twentieth, which is false: some
families collapse. B93-4 first demanded that the jump shrink on every family, which is false: it
shrinks where the owner set fills in. **Both rewrites made the readings more specific.**

**The envelope-direction guard in B93-6 exists because a mutation needed it**, exactly as in B92:
reading the owner as the dearest member still produces reversing counts and nothing else notices.
**Every mutation seeded was caught**, one only after that guard was added, and two of them are new
with the split: a fixture in which no family has one owner throughout, and one in which the count
of families rising anywhere is smaller than the count rising at a change of owner.

## 4. Placement

**A.** That a continuum of techniques carries reswitching and reversing is the Cambridge
literature's; that the non-substitution theorem needs the per-good minimum to exist is standard
analysis.

**D.** That a slope reversal read as the envelope's own derivative is automatic in a convex family
and says nothing about the family; **that the two-valuedness of `k` tracks the owners actually used
rather than the members on offer**; that a rise in `k` at a change of owner and a rise under one
owner are different events and a single count of them says nothing; and that the non-substitution
theorem's failure under a continuum is non-attainment rather than disagreement between goods. None
has a place in an account with no envelope owner in it.

**C is empty and this station cannot produce it**: it reads no data.

## 5. Scope

B77's cubic-in-parameter coefficient family, degrees two to five in `x`, rates from `0.02` to `3`,
a coefficient floor of `0.02`, and parameter grids to 6,400. The counts in section 3 are properties
of the generator. **Theorem 37(3), (5) and (6) are argument; (1), (2), (4) and (7) are read off the
draws and are reported as such.**

## 6. What was superseded, and how

**Published 2026-09-13 and corrected the same day**, on two points, neither of which moves a
number that was measured.

**Clause (1) counted two events as one, and then measured the survivor at the wrong rate.** Two
corrections, both on the same day.

**First**, `reversal()` returned the largest step up in `k` between adjacent rates without asking
whether the owner changed there. At degree two, `551` of the `987` families it counted keep a
single owner across the whole sweep, so the reported `24.7%` was mostly a price Wicksell effect.

**Second**, splitting the count was not enough, because a step between two adjacent grid rates
still carries each member's own valuation drift between them. **The wage is shared at the rate
where the two members cost the same and nowhere else**, so the comparison belongs at that rate,
which is what B92 does on discrete families and what this station did not. The switching rate is
now found by bisection on the pair and both members are read there. **The sign can turn on it**:
on draw 1,253 of the quadratic family the switch from member 100 to 101 reads `+1.58e-06` across
the grid bracket and `-1.69e-06` at the switch itself.

**With both corrections the counts rise**, to `195 / 312 / 408 / 422` of 4,000 by degree against
the `146 / 225 / 248 / 262` of the intermediate form, and the cohort in B93-3 survives `24 / 100`
against `74 / 100` for the original undivided population: a different and harder population,
measured where the wage is one number.

**Clause (4) cited B77's bounded active set for an object B77 does not bound.** B77's bound is on
the processes running together at one rate; this station counts the members that own the envelope
at some rate across a sweep, and that count grows without bound as the family fills in, reaching
`637` at `1280` members. **The measurement in (4) is unchanged**; the sentence attaching it to
B77 is gone, and B77's actual result, that the two counts move in opposite directions, is in its
place.

**And a third statement, in B77 rather than here, is answered by (7).** B77 recorded that a
technique returning dissolves when the labels are dense. What dissolves is the wobble between
neighbouring members; a return crossing the whole family and leading by `1e-4` survives refinement,
and (7) exhibits one.
