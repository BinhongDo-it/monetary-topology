# B52 results: 1,069 readable cells, none of them at the rival's prediction

RUN: 2026-09-06　DESIGN: `b52_prereg.md`

Script `experiments/b52_europe_class_square.py`, record
`results/b52_europe_class_square.json`.

## 1. The panel

33 countries, 38 semesters from 2007-S1 to 2025-S2, **1,076 cells**. Two cells
were dropped and named rather than silently skipped: Albania 2021-S2 and
2022-S1, where the published piped-gas price is `0.0`. That is not a price, it
is the absence of a network, and a logarithm of it would have taken the whole
run down.

**33 independent loops, one per country**, not 1,076. Four positions and four
edges give `b_1 = 4 - 4 + 1 = 1`, and the semesters of one country are repeated
readings of that one loop.

## 2. The reading

| criterion | reading | |
|---|---|---|
| **B52-1** panel completeness, printed country by country | 33 countries, 38 semesters, 1,076 cells, 33 independent loops; 2 cells dropped for a non-positive price, both named | PASS · `instrument` |
| **B52-2** the square does not move with the currency | floor `1.579e-03` over 1,076 comparisons in euro, worst at GE 2019-S2; 546 comparisons vacuous because the country already quotes in euro | PASS · `instrument` |
| **B52-3** no readable cell sits at exactly zero | **0 of 1,069**; 7 cells below the floor carry no verdict | PASS · `rival` |
| **B52-4** every cell at or below the floor named, and unscored | 1,069 of 1,076 above `1.579e-03`; smallest `0.1x`, median `103x`; below: AT 2009-S2, AT 2016-S1, DE 2025-S1, DK 2019-S1, HU 2023-S2, LV 2008-S2, SK 2012-S1 | PASS · `bookkeeping` |
| **B52-5** the sign drift is one-directional, own window | `+ to -` 6 (BA, DE, FR, HR, LT, TR), `- to +` 5 (BE, CZ, ES, LI, PL), unchanged 22 | **FAIL** · `own_reading` |
| **B52-6** the same question on one shared window | 2008-S1 to 2025-S2, 22 countries x 36 semesters; `+ to -` 5, `- to +` 2, unchanged 15 | **FAIL** · `own_reading` |
| **B52-7** the same question stopped before the crisis | 2008-S1 to 2021-S1 over 23 countries; `+ to -` 3, `- to +` 2, unchanged 18; by direction of change, 14 down and 9 up before the crisis against 15 down and 7 up over the full window | **FAIL** · `own_reading` |

`|S|` runs from `1.69e-04` to `2.18`, median `0.163`.

## 3. What the first four lines settle

**The rival here is a specific and old claim**: that the terms attached to a
position are the difference of a scalar over positions. It predicts exactly zero
on every closed loop, for any size of terms, and it has no free parameter with
which to accommodate a non-zero one. **1,069 readable cells, none of them at that
prediction, and the median cell stands 103 times the instrument's own floor.**

B49 read the same square on 39 cells. This is the same reading at 27 times the
width, on an independent panel with its own basis and its own floor, and it
strengthens rather than repeats it: the smallest multiple of the floor here is
`0.1`, which is why seven cells are named and left unscored instead of being
reported as zeros.

## 4. What the last three lines withdraw

B49 also read something the framework does not predict: the sign of the square
appeared to move in one direction only. **On the wide panel that shape does not
hold, in any of three windows.** Both directions are populated in each, and the
result is not sensitive to the window: the crisis-free window shows the same
mixture as the full one. What survives is a weak negative lean, present before
and after the interventions, and never one-directional.

**The three lines are the station's own reading, not the rival's.** Their
failure withdraws a candidate regularity that B49 had put forward. It does not
touch B52-3, and the two readings sit in different places: the framework says
this quantity is not identically zero, and it says nothing about which way it
should drift. That gap is now a measured gap rather than an assumed one.

## 5. Two limits found while running, both carried forward

**The reference band cannot see a carve-out narrower than itself.** Eurostat's
industrial reference band is 0.5 to 2 GWh, while the German relief for
energy-intensive industry requires more than 1 GWh, a listed sector, and an
electricity cost intensity of 14 or 20 per cent. A class difference that lives
inside such a carve-out is invisible to this instrument even where the carrier
otherwise qualifies. **The instrument's bandwidth is a fifth question that the
carrier screen does not ask.**

**Whether a commodity has two posted prices is a property of the commodity and
the place, not of the commodity alone.** Electricity is everywhere; piped gas is
not. Albania is the demonstration, and the screen in `b51` was asking the
question one commodity at a time.
