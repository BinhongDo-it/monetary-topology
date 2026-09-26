# B111: the 2026 Black Sea cuts on both sides, printed week by week against Theorem 43

**RUN: 2026-09-16. Script `experiments/b111_black_sea_cut.py`, record
`results/b111_black_sea_cut.json`, which carries the configuration it ran under. Data
`data/b111_black_sea_prices.json`, transcribed by hand with one source URL per cell; sources and
caliber notes in `data/SOURCES.md`. Theorem 43 and its corollaries are in
[`b105_cutting_relations.md`](b105_cutting_relations.md).**

## 0. What the station reads

In July and August 2026 Ukraine lost its Black Sea grain corridor and Russia lost first its Azov
loadings and then most of its Novorossiysk loadings. Each side then had three positions on one
loop with the world wheat price `W` (Euronext milling wheat, September 2026 contract):

| Side | Interior | Port whose sea route was cut | Route that stayed open |
|---|---|---|---|
| Ukraine | `U0` EXW, UAH/t | `U1` CPT port, USD/t | `U2` western border, USD/t |
| Russia | `R0` class 3 wheat EXW European Russia, RUB/t | `R1` 12.5% protein wheat FOB Novorossiysk, USD/t | `R2` FOB Baltic, USD/t |

The station prints the prices at those positions week by week, aligns them to the dated steps of
each cut, and reads four objects against Theorem 43. It is a descriptive station: each reading is
one of three states, **matches**, **does not match** or **not read**, and the full paths are in the
record. A fifth object, whether each position carries a quote each week, is printed next to the
steps without a reading.

Two Ukrainian sources quote the same positions, and each is printed as its own family with its own
floor:

| Family | `U0` | `U1` | `U2` | Same weeks of 2025 |
|---|---|---|---|---|
| broker weekly report | none | 11.5% protein wheat and corn, CPT Odesa | corn, FCA Chop, from 2026-07-17 | DAP Odesa ranges, another column |
| exchange purchase price page | wheat grade II, EXW elevators | wheat grade II and corn, CPT terminal | corn, DAF | every Friday, same columns |
| interior price page | wheat, EXW | | | none |

The exchange page is the daily weighted average purchase price of the Ukrainian electronic grain
exchange, read on the Friday of each week. Its wheat grade is the grade whose CPT dollar price sits
closest to the broker's 11.5% protein index over the four June 2026 Fridays: a mean gap of 1.75
dollars for grade II, 8.25 for grade III and 10.5 for grade IV. Russia has one family per position.

## 1. The dated steps

The step dates come from reports of physical events (strikes, closures, terminals that stopped
loading), never from turning points in the prices. The steps that the readings use:

| Side | Date | Event | Dose |
|---|---|---|---|
| Ukraine | 2026-07-22 | no vessel entered the corridor ports | cut |
| Ukraine | 2026-08-01 to 08-12 | exports back to about three tenths of need | partial reopening |
| Russia | 2026-07-10 | shallow-water Azov ports restricted, Don-Azov channel halted | cut |
| Russia | 2026-07-27 to 07-31 | two Taman terminals damaged | cut |
| Russia | 2026-08-10 to 08-14 | two Novorossiysk terminals stopped, a third stopped intake and loading | cut |

The step week is the first Friday after a step starts. Ukraine's July strikes were reported as a
monthly count without days, and sit in the step table without a window.

## 2. The objects

| | What is printed | Theorem 43 | Reading |
|---|---|---|---|
| `a` | port against `W`: each leg's move against its own June mean, in percent, and their difference in percentage points, every Friday. Two readings: one- and two-week windows starting the Friday before each step week, and long windows from the last June Friday (06-26) to every later Friday | Corollary 43.1: a cut moves the pair away from its term, on the side where it already stood | cut: down past the floor matches, up past the floor does not; a partial reopening reads with the opposite sign (Corollary 43.5). A long window with no dated step inside is not read; one that holds a cut reads as a cut, the Ukrainian reopening included, since exports came back to about three tenths of need |
| `b` | premium of the open route over the cut port, same week, same grade, same source, over one and two weeks from the Friday before each step week | the same rewrite on the relation that stayed open | cut: a premium that widens past the floor matches, one that narrows past it does not; a partial reopening reads with the opposite sign |
| `c` | Ukraine: port against `W` at the end of the weakening segment (2026-07-17) against each week of the full cut | Corollary 43.5: the rewrite grows with the weakening | down past the floor matches, up past the floor does not |
| `d` | the interior's weekly change in the step week and the week after, in its own currency, next to the same weeks of 2025 and to `W`'s change | Theorem 43 (2): a cut lowers the interior | down past the floor matches at a cut, up past it at a reopening; not read when the 2025 week is missing |
| `e` | whether each position carries a quote each Friday, family by family, in 2026 and in the same weeks of 2025 | Theorem 43 (3) and (4): a position whose relations all lose their weight is cut off, and no price fixes its level against the rest | printed without a reading: a source can also stop quoting a line for its own reasons, and there is no floor to read a count against |

A reading is **not read** when an end cell is missing, when its source calls it nominal,
approximate or a zone, when the Ukrainian port price sits at or below that month's minimum
allowable export price (exports below it are prohibited), or when the move stays within the floor.
The record also prints, for every quote, how many Fridays in a row before it the same value was
printed.

For `e` each week of each family takes one state, from its cell and from the coverage row of that
week's issue, and each state falls in one of three kinds. **A price:** quoted, quoted as a range,
implied from the next issue, approximate, or a zone. **No price:** nominal, at or below the minimum
export price, or absent from an issue that was read. **Not read:** the week's report was read only
in an English rewrite that does not carry the line, no report was found, the page did not show that
week, the issue was not opened, or the week's quote is of another futures contract. Each family is
counted before, and from, the first step week of its side at a cut: 07-24 in Ukraine, 07-17 in
Russia.

## 3. Floors

The floor is the larger of two numbers. The quote grid counts only quotes with a fixed format:
Euronext trades in quarters of a euro, the broker's CPT and FCA index and the exchange page are in
whole dollars and whole hryvnias, and the weekly domestic average in European Russia moves in steps
of 25 roubles. The second number is the median absolute move of the same quantity over windows of
the same length whose ends both lie in June 2026, or both in the same weeks of 2025 (2025-05-30 to
2025-09-12), in one column, both ends readable. The 2025 windows of `a` take `W` from the September
2025 contract only, so no window crosses its expiry on 2025-09-10. No minimum export price for 2025
is on disk, so a 2025 end is readable when it is present and not flagged. With no window at all the
floor is not measured.

| Object | Family | One week | Two weeks | Windows in June 2026 and in 2025 |
|---|---|---|---|---|
| `a` Ukraine | broker weekly report | 1.65 pp | 3.31 pp | 2 and 1 in June; none in 2025; grid 0.59 pp |
| `a` Ukraine | exchange purchase price page | 0.87 pp | 2.90 pp | 2 and 1 in June; 14 and 13 in 2025 |
| `a` Russia | weekly grain report | 0.81 pp | 1.81 pp | 2 and 1 in June; 13 and 12 in 2025 |
| `b` Ukraine | exchange purchase price page | 3 dollars | 4 dollars | 3 and 2 in June; 15 and 14 in 2025; grid 2 |
| `b` Ukraine | broker weekly report | not measured | not measured | the FCA Chop dollar index starts 2026-07-17 |
| `b` Russia | both | not measured | not measured | no Baltic quote before 2026-08-11 or in 2025 in these sources |
| `c` | both Ukrainian families | as `a` | as `a` | |
| `d` Ukraine | exchange purchase price page | 65.5 UAH | | 3 in June, all three zero; 15 in 2025 |
| `d` Ukraine | interior price page | not measured | | one June quote, no 2025 quotes |
| `d` Russia | weekly grain report | 175 roubles | | 2 in June; 13 in 2025; grid 25 |

The long windows of `a` that carry a reading are three to nine weeks long, and only 2025 holds
windows longer than two weeks.
Russia: 3.87, 4.50, 5.87, 6.07, 6.71, 9.39 and 9.23 pp for three to nine weeks. Ukraine, exchange
page: 3.33, 4.70, 5.80, 8.86, 8.90, 8.95 and 8.66 pp. The broker family has no 2025 column, so its
floors stop at two weeks.

## 4. Readings

**`a`, port against `W`, around each step:**

| Side | Family | Step | Window | Move | State |
|---|---|---|---|---|---|
| Russia | weekly grain report | 07-10 | 07-10 to 07-17 | −5.80 pp | matches |
| Russia | weekly grain report | 07-10 | 07-10 to 07-24 | −5.18 pp | matches |
| Russia | weekly grain report | Taman | 07-24 to 07-31 | +1.09 pp | does not match (floor 0.81) |
| Russia | weekly grain report | Taman | 07-24 to 08-07 | −1.61 pp | not read, within the floor |
| Russia | weekly grain report | Novorossiysk | 08-07 to 08-14 | −4.63 pp | matches |
| Russia | weekly grain report | Novorossiysk | 08-07 to 08-21 | −4.55 pp | not read, 08-21 quoted as nominal |
| Ukraine | broker weekly report | 07-22 | 07-17 to 07-24 | −2.16 pp | not read, 07-24 quoted as nominal |
| Ukraine | broker weekly report | 07-22 | 07-17 to 07-31 | +1.41 pp | not read, within the floor |
| Ukraine | broker weekly report | reopening | 07-31 to 08-07 | −0.12 pp | not read, 08-07 quoted as nominal |
| Ukraine | broker weekly report | reopening | 07-31 to 08-14 | −2.60 pp | not read, within the floor |
| Ukraine | exchange purchase price page | 07-22 | 07-17 to 07-24 | +0.62 pp | not read, within the floor |
| Ukraine | exchange purchase price page | 07-22 | 07-17 to 07-31 | +5.58 pp | does not match (floor 2.90) |
| Ukraine | exchange purchase price page | reopening | 07-31 to 08-07, to 08-14 | | not read, no grade II CPT dollar quote from 08-07 |

In the Russian Taman week IKAR's Novorossiysk price fell from 235 to 226 dollars and `W` from
232.75 to 222.75 euros, and IKAR's delivery period moved from the second half of August to early
September. The exchange page prints grade II wheat at CPT terminal at 205 dollars on 07-17, 07-24
and 07-31, the same value three Fridays running, while `W` fell 11.25 euros; the broker's 11.5%
protein index on the same Fridays reads 204, 198 (nominal) and 195.

**`a`, long windows from 06-26:**

| Side | Family | To | Weeks | Move | Floor | State |
|---|---|---|---|---|---|---|
| Russia | weekly grain report | 07-17 | 3 | −13.78 pp | 3.87 | matches |
| Russia | weekly grain report | 07-24 | 4 | −13.16 pp | 4.50 | matches |
| Russia | weekly grain report | 07-31 | 5 | −12.07 pp | 5.87 | matches |
| Russia | weekly grain report | 08-07 | 6 | −14.77 pp | 6.07 | matches |
| Russia | weekly grain report | 08-14 | 7 | −19.40 pp | 6.71 | matches |
| Russia | weekly grain report | 08-21, 08-28 | 8, 9 | −19.32, −27.26 pp | | not read, nominal |
| Ukraine | exchange purchase price page | 07-24 | 4 | −20.85 pp | 4.70 | matches |
| Ukraine | exchange purchase price page | 07-31 | 5 | −15.88 pp | 5.80 | matches |
| Ukraine | exchange purchase price page | 08-07 to 09-11 | 6 to 11 | | | not read, no grade II CPT dollar quote |
| Ukraine | broker weekly report | 07-24 to 08-28 | 4 to 9 | −21.83 to −31.19 pp | | not read: no floor beyond two weeks, and 07-24 and 08-07 nominal |

Windows ending 07-03 and 07-10 on both sides, and 07-17 in Ukraine, hold no dated step and are not
read. `W`'s September 2026 contract has no quote on 09-04 and 09-11, so no long window reaches
September.

**`b`, premium of the open route:**

| Side | Family | Step | Window | Change | State |
|---|---|---|---|---|---|
| Ukraine | exchange purchase price page | 07-22 | 07-17 to 07-24 | −1 | not read, within the floor |
| Ukraine | exchange purchase price page | 07-22 | 07-17 to 07-31 | +12 | matches |
| Ukraine | exchange purchase price page | reopening | 07-31 to 08-07 | −4 | matches |
| Ukraine | exchange purchase price page | reopening | 07-31 to 08-14 | −1 | not read, within the floor |

The exchange page's corn at DAF over corn at CPT terminal, in dollars: −10 on 05-29, −9, −6, −3
and −2 through June, +4 on 07-03, 07-10 and 07-17, +3 on 07-24, +16 on 07-31, then +12, +15 and
+10 to 08-21; after 08-21 the page carries no corn CPT dollar quote. The CPT side holds 185 from
07-31 to 08-21. In the same weeks of 2025 the same premium ran from −18 at the end of May and −17 to −15 in June
to +13 on 2025-07-11, and between 0 and +12 after.

The broker family reads nothing: every Ukrainian window has a nominal end (07-17 to 07-31) and
there is no floor. Its premium of corn at FCA Chop over CPT Odesa runs 26, 28 and 23 on the
nominal weeks, then 25, 30, 30 and 40, and 40 and 41 on 09-04 and 09-11, when the port sits below
September's minimum export price of 195. Russia reads nothing: Rusagrotrans' two quotes are dated
Tuesday 08-11 and 08-18 and IKAR's Baltic line starts on 08-21, so no window has its ends, and
neither family has a floor. Rusagrotrans' premium rose from 19 to 40 across the week that holds the
Novorossiysk step.

**`c`, weakening against the full cut:** broker weekly report, 07-17 to 07-24 not read (07-24
nominal) and 07-17 to 07-31 +1.41 pp within 3.31; exchange purchase price page, 07-17 to 07-24
+0.62 pp within 0.87 and 07-17 to 07-31 +5.58 pp, does not match. These are the same windows as the
first Ukrainian step in `a`.

**`d`, the interior's weekly change:**

| Side | Family | Step | Week | Change | Same week of 2025 | `W` that week (EUR) | State |
|---|---|---|---|---|---|---|---|
| Russia | weekly grain report | 07-10 | 07-17 | −675 | −700 | +17.75 | matches |
| Russia | weekly grain report | 07-10 | 07-24 | −175 | +225 | −1.25 | not read, within the floor |
| Russia | weekly grain report | Taman | 07-31 | −825 | +225 | −10.00 | matches |
| Russia | weekly grain report | Taman | 08-07 | −350 | +200 | +0.25 | matches |
| Russia | weekly grain report | Novorossiysk | 08-14 | −325 | −100 | +5.00 | matches |
| Russia | weekly grain report | Novorossiysk | 08-21 | −2,600 | −225 | −4.50 | matches |
| Ukraine | exchange purchase price page | 07-22 | 07-24 | −59 | +188 | −1.25 | not read, within the floor |
| Ukraine | exchange purchase price page | 07-22 | 07-31 | +2 | +69 | −10.00 | not read, within the floor |
| Ukraine | exchange purchase price page | reopening | 08-07 | −81 | +166 | +0.25 | does not match |
| Ukraine | exchange purchase price page | reopening | 08-14 | 0 | +58 | +5.00 | not read, within the floor |
| Ukraine | interior price page | both | 07-24 to 08-14 | −250 and −500 UAH on 08-07 and 08-14 | not on disk | | not read |

The exchange page's grade II wheat at elevators holds 9,410 UAH through all four June Fridays, which
is why the three June windows are zero; it then reads 9,240 on 07-03 and 07-10, 8,830 on 07-17,
8,771 on 07-24, 8,773 on 07-31, 8,692 on 08-07 and 08-14, and 6,970 on 08-21.

**`e`, whether each position carries a quote each Friday.** Codes, by kind. A price: `Q` quoted,
`R` quoted as a range, `I` implied from the next issue, `A` approximate, `Z` zone. No price: `N`
nominal, `F` at or below the minimum export price, `-` absent from an issue that was read. Not read:
`W` read only in a rewrite without the line, `0` no report found, `P` not on the page, `.` issue not
opened, `C` a quote of another contract.

2026:

```
                                            05    06          07             08          09
                                            22 29 05 12 19 26 03 10 17 24 31 07 14 21 28 04 11
UA port       wheat 11.5%, CPT Odesa, USD      Q  Q  Q  Q  Q  Q  Q  Q  N  Q  N  Q  Q  Q  Q  Q
UA port       corn, CPT Odesa, USD             Q  Q  Q  Q  Q  Q  Q  N  N  N  Q  Q  Q  Q  F  F
UA open route corn, FCA Chop, USD              -  -  -  -  -  -  -  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA port       wheat II, CPT terminal, USD      Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  -  -  -  -  -  -
UA port       corn, CPT terminal, USD          Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  -  -  -
UA open route corn, DAF, USD                   Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA interior   wheat II, EXW elevators, UAH     Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA interior   wheat, EXW, UAH                  P  P  P  P  Q  P  P  P  P  Q  Q  Q  Q  Q  Q  Q
RU port       IKAR 12.5%, FOB Novorossiysk  Q  A  Q  I  Q  Q  Q  I  Q  Q  Q  Q  Q  N  N  0  -
RU open route IKAR 12.5%, FOB Baltic        -  -  W  0  -  W  -  0  -  W  -  -  -  A  Q  I  Q
RU interior   SovEcon class 3, EXW          Q  Q  W  I  Q  Q  Q  I  Q  I  Q  Q  Q  Q  Q  I  Q
RU port       12.5%, FOB Novorossiysk       .  .  .  .  .  .  .  .  .  .  .  I  Q  .  .  .  .
RU open route 12.5%, FOB Baltic             .  .  .  .  .  .  .  .  .  .  .  I  Q  .  .  .  .
   world      Euronext, September contract     Q  Z  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  C  C
```

The same weeks of 2025, for the columns with a 2025 twin (the Russian report runs to 2025-08-29):

```
                                            05 06          07          08             09
                                            30 06 13 20 27 04 11 18 25 01 08 15 22 29 05 12
UA port       wheat II, CPT terminal, USD   Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA port       corn, CPT terminal, USD       Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA open route corn, DAF, USD                Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
UA interior   wheat II, EXW elevators, UAH  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q
RU port       IKAR 12.5%, FOB Novorossiysk  Q  Q  Q  Q  Q  Q  Q  Q  Q  I  Q  Q  Q  Q
RU interior   SovEcon class 3, EXW          Q  Q  Q  Q  Q  Q  Q  Q  Q  I  Q  Q  Q  Q
   world      Euronext, September contract  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  Q  C
```

| Side | Position | Family | Column | First cut step week | Before it: price, no price, not read | From it: price, no price, not read | First week without a price from it |
|---|---|---|---|---|---|---|---|
| Ukraine | port | broker weekly report | wheat 11.5%, CPT Odesa, USD | 07-24 | 8, 0, 0 | 6, 2, 0 | 07-24 |
| Ukraine | port | broker weekly report | corn, CPT Odesa, USD | 07-24 | 7, 1, 0 | 4, 4, 0 | 07-24 |
| Ukraine | open route | broker weekly report | corn, FCA Chop, USD | 07-24 | 1, 7, 0 | 8, 0, 0 | none |
| Ukraine | port | exchange purchase price page | wheat II, CPT terminal, USD | 07-24 | 8, 0, 0 | 2, 6, 0 | 08-07 |
| Ukraine | port | exchange purchase price page | corn, CPT terminal, USD | 07-24 | 8, 0, 0 | 5, 3, 0 | 08-28 |
| Ukraine | open route | exchange purchase price page | corn, DAF, USD | 07-24 | 8, 0, 0 | 8, 0, 0 | none |
| Ukraine | interior | exchange purchase price page | wheat II, EXW elevators, UAH | 07-24 | 8, 0, 0 | 8, 0, 0 | none |
| Ukraine | interior | interior price page | wheat, EXW, UAH | 07-24 | 1, 0, 7 | 7, 0, 1 | none |
| Russia | port | weekly grain report | IKAR 12.5%, FOB Novorossiysk | 07-17 | 8, 0, 0 | 5, 3, 1 | 08-21 |
| Russia | open route | weekly grain report | IKAR 12.5%, FOB Baltic | 07-17 | 0, 4, 4 | 4, 4, 1 | 07-17 |
| Russia | interior | weekly grain report | SovEcon class 3, EXW | 07-17 | 7, 0, 1 | 9, 0, 0 | none |
| Russia | port | Rusagrotrans note | 12.5%, FOB Novorossiysk | 07-17 | 0, 0, 8 | 2, 0, 7 | none |
| Russia | open route | Rusagrotrans note | 12.5%, FOB Baltic | 07-17 | 0, 0, 8 | 2, 0, 7 | none |

In Ukraine the broker calls its wheat index at CPT Odesa nominal on 07-24 and 08-07 and its corn
index nominal from 07-17 to 07-31, and puts corn at or below September's minimum export price on
09-04 and 09-11; its dollar index for corn at FCA Chop is first published on 07-17. The exchange
page prints no grade II wheat at CPT terminal in dollars from 08-07 and no corn there from 08-28,
while its corn at DAF and its grade II wheat at elevators carry a price every Friday. The interior
price page shows eight dates, 06-27 and seven from 08-03, so its other weeks are not on it. In
Russia IKAR's Novorossiysk price is nominal on 08-21 and 08-28, no report was found for 09-04, and
the report for 09-11 carries no Novorossiysk quote; IKAR's Baltic line is absent from every report
read in full before 08-21 and carries a price in every week from it. Rusagrotrans' note of 08-19 gives the
weeks of 08-07 and 08-14, and no other note was opened. SovEcon's interior price carries a price in
every week from 07-17. `W`'s September 2026 contract carries a price to 08-28, and the broker quotes
December from 09-04. In the same weeks of 2025 every twin column carries a price every Friday, `W`
up to the expiry of its September contract.

**States:**

| Object | Family | Matches | Does not match | Not read |
|---|---|---|---|---|
| `a` around steps | Russia, weekly grain report | 3 | 1 | 2 |
| `a` around steps | Ukraine, broker weekly report | 0 | 0 | 4 |
| `a` around steps | Ukraine, exchange purchase price page | 0 | 1 | 3 |
| `a` long windows | Russia, weekly grain report | 5 | 0 | 6 |
| `a` long windows | Ukraine, broker weekly report | 0 | 0 | 11 |
| `a` long windows | Ukraine, exchange purchase price page | 2 | 0 | 9 |
| `b` | Ukraine, exchange purchase price page | 2 | 0 | 2 |
| `b` | Ukraine, broker weekly report | 0 | 0 | 4 |
| `b` | Russia, both families | 0 | 0 | 12 |
| `c` | Ukraine, broker weekly report | 0 | 0 | 2 |
| `c` | Ukraine, exchange purchase price page | 0 | 1 | 1 |
| `d` | Russia, weekly grain report | 5 | 0 | 1 |
| `d` | Ukraine, exchange purchase price page | 0 | 1 | 3 |
| `d` | Ukraine, interior price page | 0 | 0 | 4 |

The long windows overlap, so their counts are counts of weeks on one path, and `c` repeats the
first Ukrainian step of `a`.

**Context printed with the readings:** Russia's weekly wheat export duty, a published term between
`R0` and `R1`, turned non-zero for the first time since April on 07-08 (370.1 roubles a tonne) and
then ran 0, 0, 5.7, 326.6, 721.1, 1,012.1, 787.5, 1,179.3 and 1,146.3. Ukraine's minimum allowable
export prices by month and delivery term are in the record.

## 5. Structural checks

| | Kind | What it checks | Run |
|---|---|---|---|
| PASS `B111-1` | `bookkeeping` | every cell carries a source URL, a price date, a published date, a basis and a grade | 909 cells, none incomplete |
| PASS `B111-2` | `instrument` | one column holds one unit, one basis and one grade, and `W` one futures contract | 49 declared columns, no cell off its column |
| PASS `B111-3` | `instrument` | every difference is taken within one week across columns, or within one column across weeks | 794 differences, none off |
| PASS `B111-4` | `bookkeeping` | every week in each source's window has a coverage row, weeks that read zero included, and a row that counts its cells counts the cells on disk from that page | eight source families, every week present; 64 page rows, each count equal to the cells on disk |

The selftest plants a failure under each check (a missing source, an FCA quote filed in a CPT
column, a 2025 cell of another grade in a twin column, a premium taken across two weeks, a dropped
zero week, a dropped 2025 page, a page row counting one cell too many) and each check reports it. It
also checks every verdict row of the state mapping, the count of 2025 windows in each floor, a
nominal end, a port at the minimum export price, a flagged interior end, a long window with no step,
a premium that narrows at a cut, a missing 2025 week and a missing step. For `e` it plants one case
of each state (a nominal cell, a port at the minimum export price, a page read without the cell, a
week off the page, a contract roll, an implied cell, a week with no report found, a line missing
from a rewrite, a page never opened) and checks that a nominal week and a week at the minimum export
price are counted as weeks without a price. Thirty deliberate faults in the implementation were each
caught by the selftest.

## 6. What more data would read

1. **A quote of the Russian Baltic route before 2026-08-11, or in the same weeks of 2025,** would
   give Russia's `b` a floor; a Friday-dated one would also give it windows.
2. **A Ukrainian port quote in dollars that runs past 2026-08-07 and has a 2025 column** would read
   the reopening in `a` and the long windows after 07-31. The broker's 2025 reports quote DAP
   ranges, and the exchange page stops quoting grade II wheat at CPT in dollars from 08-07.
3. **An archive of the interior price page for June and July 2026 and for 2025** would read that
   family of `d` next to the exchange page.
