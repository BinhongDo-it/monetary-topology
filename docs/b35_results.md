# B35 results

Design: [`b35_prereg.md`](b35_prereg.md). Every criterion this station
registered appears below, including the ones a later round superseded and the
ones that were never scored.

## 1. What this station established

**A part with no substitute class at origin has a naturally concentrated
destination list.** Chicken paws go 98.7 per cent to one country, second place
0.49. Swine feet 96.74, second place 1.03. Swine head meat 94.55, second place
2.12. Three parts, two species, two independent trade lines. The places that eat
such a part are few, so the export destination list is short. This was a guess
before the pull and it now has three figures behind it.

**The US national price report quotes no price for chicken paws at all.** Two
independent official reports, three independent pulls, most recently over 1,819
machine-readable rows. A market nobody trades in has no quotation, which is the
structural fact arm B35-7 asks for, and it is stronger evidence than a thin
quotation would have been.

**An objection was tested to its end and became the station's own material.**
"Larger volumes are less volatile, so the comparison reads volume rather than
anchoring." The correlation that objection points at is itself a function of
this station's treatment variable, seen one step downstream.

## 2. What this station did not establish, and why

**B35-6, the magnitude ratio, is undecidable and the arm is at its ceiling on
this carrier.** The point estimate is 9.42 in the direction the framework
predicts, replicated across window lengths (7 adjacent steps gave 9.75, 46 gave
9.42). It carries no claim: the denominator coefficient is not distinguishable
from zero, so the ratio is a combination of two estimates where the combination
itself was never estimated.

Gate two does not clear, under four different standard-error conventions:

| convention | se(difference) | `1.645 x se` | band half-width | short by |
|---|---|---|---|---|
| classical, joint | 0.4741 | 0.7799 | 0.4055 | 1.923x |
| classical, independent bound | 0.4605 | 0.7575 | 0.4055 | 1.868x |
| heteroskedasticity-robust | 0.4412 | 0.7258 | 0.4055 | 1.790x |
| **Newey-West, lag 3** | **0.2830** | **0.4655** | 0.4055 | **1.148x** |
| Newey-West, lag 4 | 0.2767 | 0.4552 | 0.4055 | 1.123x |

The residual correlation between the two legs is negative, so the joint standard
error is the larger of the two classical figures, not the smaller. An earlier
note calling the independent bound conservative was wrong and is corrected here.

**Gate six clears.** The reading stands at 3.9 to 5.3 times the measured
resolution floor, where the floor comes from pairs the theory says should not
differ. Gate two and gate six answer different questions and their verdicts do
not conflict: one asks whether the reading can be told from the rival's band,
the other whether it can be seen at all.

**The ceiling is arithmetic, not a shortage of effort.** The window's two ends
are dated institutional events, so 2020-01 to 2023-11 is all of it. Widening it
would need a part-level US quotation covering 2020 onward, and three
independent checks agree that no such series exists. Two facts, neither of which
more months would change.

## 3. The independent count

The gate arithmetic divides by the square root of the step count. Monthly series
are serially correlated, so the count was measured.

Residual autocorrelation on the difference series, orders one to eight:
`-0.1013, -0.0570, -0.0988, +0.2215, +0.0581, -0.0264, -0.0722, +0.1021`. The
low orders are negative and the long-run variance ratio is 0.7417, below one.

**The effective count is larger than the nominal one, not smaller**: 62 by the
direct ratio, 129 and 135 implied by the two HAC standard errors. Monthly log
changes of a mean-reverting level series carry negative first-order
autocorrelation, so dividing by the square root of the raw count is conservative
here rather than optimistic. This is the correction that moves gate two from
short by 1.92x to short by 1.148x, and it does not change the verdict.

Recorded in `results/b35_d22_effective_n.json`, script
`experiments/b35_d22_effective_n.py`.

## 4. Gate zero on the cross-destination arm

The three-way read-out was written before the pull: two or more countries at ten
per cent each and present in all twelve months opens the arm; one country above
ninety per cent closes the family, **and that closure is itself a reading**;
anything else is undecidable.

One call, all destinations, ten-digit codes, 2022. Chicken paws, swine feet and
swine head meat all land in the closing cell, with the figures in section 1.
Cross-destination dispersion cannot be formed on any of the three legs.

**The same pull drops a fourth candidate that fits the opening cell**: swine
tongues, China 37.19 / Japan 31.37 / Mexico 26.48 per cent, all twelve months,
unit values 1.87 / 3.23 / 2.33 dollars per kg, a factor of 1.73 across anchors.
There is no low-cost swap between the three, because access for frozen offal is
granted plant by plant and a consignment cleared for one destination cannot be
rerouted to another. **It is a candidate, not a registered hit.**

It carries a break in September 2022 that has to be settled before the arm
opens. The China leg's unit value halves while its volume rises sixfold. The
other five parts on the same edge do not move or move the other way; the Japan
and Mexico legs do not move; and a table of first-appearance months for swine
skins rules out a reclassification, since skins are present on four legs from
January and on the China leg only from September. What remains is either an
access change or two goods under one code, and prices cannot separate those.
Rule text can.

## 5. Every criterion

| criterion | verdict | reading |
|---|---|---|
| **B35-7 structure** | **PASS** | the national report quotes no paw price at all; confirmed in three independent pulls, most recently on 1,819 machine-readable rows |
| **B35-6 origin-side magnitude ratio** | **undecidable** | ratio 9.42 in the predicted direction across 46 adjacent steps and 9.75 across 7; denominator not distinguishable from zero; gate two short by 1.148x at best |
| **B35-5 destination-side arm** | **undecidable** | the window carrying the control leg is occupied by a larger origin-side move whose direction is already known, so this arm's own treatment is not the dominant variation there |
| **B35-8 cross-destination dispersion** | **closed at gate zero, and the closure is a reading** | paws 98.7 per cent to one destination, feet 96.74, head meat 94.55 |
| **B35-4 self-sufficiency gradient** | **not run** | registered; one change of destination code on the same query would supply it |
| B35-D22-1 autocorrelation printed rather than assumed | **PASS** | eight orders on three series |
| B35-D22-2 gate two verdict survives the serial correction | **PASS** | four conventions, all short of the band |
| B35-D22-3 effective count reported, arm not booked at n = 46 | **PASS** | long-run variance ratio 0.7417, effective count 62 to 135 |
| objection: larger volumes are less volatile | **not sustained** | the correlation is a function of this station's own treatment variable |
| B35-1 destination-side arm, bovine carrier | **superseded** | the offal heading is not bovine on this leg; superseded by B35-5 |
| B35-2 origin-side arm, bovine carrier | **superseded** | the shock is a swine shock; superseded by B35-6 |
| B35-3 substitute class at origin, bovine carrier | **superseded** | superseded by B35-7, which answered it on a stronger source |

## 6. Still open at closing

**Neither of these belongs to any verdict above.**

1. **The swine tongue candidate. Gate answered 2026-09-10, and the arm is
   narrowed rather than closed.** The gate was the rule text for US swine
   product access in the second half of 2022, deciding between an access change
   and two goods under one code. The rule text was chased through five source
   classes and not reached; the arithmetic answered instead, and more sharply.
   **Two goods under one code, in its sharpest form: not a code that always held
   two, but contents moving between codes on the China leg from September.**
   The union of the tongue and head-meat codes is continuous across the break in
   both tonnage and unit value while each member separately is not, which a
   demand episode inside one good cannot produce. A mixture with both endpoints
   measured on the same leg before the break puts **0.662 to 0.907 of the
   post-break tongue line at head meat's price**, with the eight pre-break
   months run through the same arithmetic as a control returning -0.176 to
   +0.079, and the **implied real tongue flow, 386 to 609 tonnes a month, inside
   its own observed pre-break range of 79 to 699**. Sweeping the second endpoint
   over 0.90 to 1.60 dollars a kilo holds the majority reading. **The leg itself
   has no break**: August to September is rank 1 of 11 month-on-month steps in
   the tongue unit value and rank 9 of 11 in the leg's total tonnage. The arm may
   use January through August, and the independent count and the resolution
   floor still come before it opens. `b35_tongue_anatomy.py`,
   `b35_d23_tongue_break.py`.
2. **Step against spike, run 2026-09-10. It is a step, and three years make the
   move larger than one year showed.** All three outcomes carried readings
   written before the pull; the branch that fires is the one requiring 2021 to
   sit on the pre-break side and 2023 on the post-break side. **China-leg tongue
   unit value: 2021 2.305-3.617, 2022 Jan-Aug 3.212-3.764, 2022 Sep-Dec
   1.419-1.950, 2023 1.066-1.582** — 2021 overlaps the first, 2023 the second,
   and the two do not overlap each other. **Head meat to China goes 81,424 to
   26,023 to 713 tonnes a year, monotone, with four months of 2023 at exactly
   zero; 2021's thinnest month is 8.7 times 2023's thickest.** The move is not
   a two-code swap on this horizon: skins to China move x15.277 over the same
   two years while hearts move x0.447. **Slaughter is excluded without any
   weight assumption**: one tongue and four feet come off every hog, so both
   lines meter the same animal count, and the foot line moves x1.058 while the
   tongue line moves x12.765. Over all 36 months the tongue unit value spans
   3.53x while the two codes together span 1.75x. `b35_step_or_spike.py`.
3. **B35-4**, registered and never run.

## 7. Two things worth carrying elsewhere

**A reading stands against two zeros at once**, the rival's band and the
instrument's own floor, and they are different objects. This station measured
both, and they gave different answers on the same reading.

**Monthly log changes carry negative low-order autocorrelation**, so dividing by
the square root of the raw month count understates the information rather than
overstating it. Any arm booking a month count on differenced monthly data is
worth checking for this. It costs one pass over residuals already on disk.
