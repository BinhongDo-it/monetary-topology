# B49 results: 39 of 39 squares non-zero, the smallest at 7.4 times the floor

RUN: 2026-09-06　DESIGN: `b49_prereg.md`

Script `experiments/b49_energy_class_square.py`, record
`results/b49_energy_class_square.json`.

## 1. The panel

Thirteen countries carry all four series in all three years: Algeria, Czechia,
France, Greece, Hungary, Ireland, Netherlands, New Zealand, Poland, Slovak
Republic, Spain, Switzerland, United Kingdom. **39 cells, 156 prices.**

Algeria is in the panel and is not an OECD member, which is how the tax basis was
read off the source rather than assumed.

## 2. The reading

| criterion | reading | |
|---|---|---|
| **B49-1** the locked panel is complete | 13 countries, 39 cells, 156 prices | PASS · `instrument` |
| **B49-2** roster never shorter than the records it names, per product | electricity roster 111, record 111, all three years 38, paired 179; gas roster 69, record 69, all three years 28, paired 102; and so on for the other six | PASS · `bookkeeping` |
| **B49-3** the square does not move with the currency | floor `2.471e-03` from the national-currency quotation, worst cell Netherlands 2000 | PASS · `instrument` |
| **B49-4** every square above the measured floor | 39 of 39; smallest `7.4x`, median `56x`; at or below the floor: none | PASS · `instrument` |
| **B49-5** no cell at the rival's point prediction of exactly zero | **0 of 39** | PASS · `rival` |

`|S|` runs from `0.0183` to `0.853`, median `0.138`.

## 3. Which of the eight products can carry this shape at all

The selection was made from the printed grid rather than by assumption:

| product | sectors quoted | can a square be written |
|---|---|---|
| **electricity** | industry, households | **yes**, and it cannot be resold across the class line |
| **natural gas** | industry, households | **yes**, same |
| steam coal | generation, industry, households | resold across the line |
| kerosene, LPG, light fuel oil, fuel oil | mixed | resold across the line |
| gasoline, automotive diesel | transport only | one sector, no square |

**The one product with depth is the one with a single class.** Transport fuels
carry an annual series back to the 1960s and quote one sector; the two that
carry two classes carry three years.

## 4. The floor was selected the wrong way in the first pass

The first implementation took the floor from whichever alternative quotation had
the **smallest** residual among those covering every cell. **That is the loosest
of the available floors, and the rule should take the largest.** The reading did
not change, because the purchasing-power quotation covered 35 of 39 cells and
was excluded on coverage before the comparison was reached. The rule is stated
in the pre-registration in its corrected form and the residuals for both
quotations are in the record: `2.471e-03` for national currency,
`1.830e-02` for purchasing-power.

**This is recorded because the reading surviving is not the same thing as the
rule being right.**

## 5. One reading from this station is superseded

The first pass also reported that the sign of the square appeared to move in one
direction only across the three years. **B52 read the same square over 33
countries and 38 semesters and found both directions populated in three separate
windows**, including one that stops before the 2021 wholesale move. That shape is
withdrawn; `b52_results.md` section 4 carries the numbers.

The withdrawal reaches the drift only. **B49-5 is untouched**, and B52 read the
same point prediction on 27 times as many cells with the same answer.

## 6. What the station settles

A scalar over positions predicts exactly zero on this loop for any size of
terms. **Thirty-nine cells, none of them there, the smallest standing at 7.4
times the instrument's own floor.** The four prices are compiled from national
official sources and published annually per carrier and per class, so the
quantity is read off published tariffs rather than estimated.
