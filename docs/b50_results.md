# B50 results: the premise did not hold, and the station says why

RUN: 2026-09-06　DESIGN: `b50_prereg.md`

Script `experiments/b50_hungary_class_square.py`, record
`results/b50_hungary_class_square.json`.

## 1. The panel

37 semesters with all four legs, 2007-S2 to 2025-S2, in all three tax bases.

**The aggregate is the sparser series here, not the fuller one.** The per-band
series carries 37 semesters on each leg; the total band carries 10, 10, 6 and 1.
A time dimension listing 38 semesters says the system knows those semesters, not
that this country reported them.

## 2. The reading

| criterion | reading | |
|---|---|---|
| **B50-1** panel complete, four legs, three tax bases | 37 semesters, all three bases, 2007-S2 to 2025-S2 | PASS · `instrument` |
| **B50-2** the per-band series is used, not the total band | band 37 against total 10, 10, 1 and 6 | PASS · `instrument` |
| **B50-3** the square does not move with the currency | floor `7.404e-04` over 37 comparisons in euro, worst 2018-S2; the purchasing-power unit reported separately at `5.190e-02` and excluded | PASS · `instrument` |
| **B50-4** the point prediction over the clean window | change `-0.0483`, `65.3x` the floor, 22nd percentile of the 36 own transitions whose median is `0.0969` | not judged · `own_reading` |
| **B50-5** the premise: the two household carriers moved by the same proportion | household electricity `-0.1025`, household gas `-0.1342`, difference `0.0318` against a floor of `7.404e-04` | **FAIL** · `premise` |
| **B50-6** the cut reached the price, not only the tax | tax-excluded `-0.1060` against tax-included `-0.1025` | PASS · `premise` |

## 3. Why B50-4 carries no verdict

The statute sets a **ceiling**, not an equal cut: it caps the regulated price at
a proportion of the previous one. Read as an equal cut it predicts no movement
in the square; read as a ceiling it predicts nothing in particular, because two
carriers under one ceiling can move by different amounts and here they did, by
`0.0318` against a floor of `0.00074`.

**So the window carries no point prediction to judge, and B50-4 is recorded as
not judged rather than as a failure.** The premise check is the thing that
found it, which is why it is registered separately: without it the `-0.0483`
would have been scored against a prediction that was never actually made.

## 4. The second yardstick, and what it says

`-0.0483` is 65 times the instrument's floor and sits at the **22nd percentile**
of the square's own 36 semester-to-semester steps, whose median is `0.0969`.
**Visible and ordinary at once.** A floor says whether a move can be seen; it
says nothing about whether a move stands out among the series' own movements,
and reporting only the first would have made an unremarkable step look like a
finding.

## 5. What the station did establish, and what it cost

The clean-window decomposition is the useful residue. Over 2012-S2 to 2013-S1
the four legs moved `IE +0.0075`, `IG -0.0726`, `RE -0.1025`, `RG -0.1342`:
**the industrial legs moved more than the household legs the programme was
aimed at.** The condition this design needs is that the untouched leg stays
still while the treated one moves, and **that condition is not something the
design can arrange**. It is a property of the window.

That is the general result this station contributes: **a one-leg programme
change tests the discriminant only when the other leg is quiet at the same
moment**, so the number of usable cases is the number of carriers multiplied by
the number of quiet moments, not the number of carriers.

`B50-6` is worth keeping separately: the household move is the same size with
tax excluded as with tax included, so the intervention reached the price rather
than only the tax line. Where that check fails, a class reading on a regulated
carrier is measuring the tax convention.
