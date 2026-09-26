# B64: the two-tier gold market, and the classes that could still walk the conversion

**Status: readings, with the inputs checked first. Registered 2026-09-11. Script
`experiments/b64_gold_two_tier.py`, records `results/b64_checks.json` (B64-1, B64-2) and
`results/b64_gold_two_tier.json` (B64-3 to B64-8), each carrying the configuration it ran
under. Sources and their calibers are listed in `data/SOURCES.md` under B64.**

---

## 0. The question this station answers

Triffin's condition says that a gold-exchange standard cannot last once the dollar claims
held abroad exceed the gold that stands behind them. On the figures below, the condition
held for the claims of all foreigners from the end of 1960 and for the claims of foreign
official holders from the end of 1965. The United States closed its gold window on
15 August 1971. **The argument names no date, and the record has the convertibility
lasting almost six years past the stricter of the two conditions.**

Corollary 8.6 of [`b63_trilemma.md`](b63_trilemma.md) gives the time a pegged conversion
can hold as its capacity divided by the flow of the classes that can still walk it, and
Corollary 8.4 gives the instrument: a rule that takes one direction of the conversion out
of a class's reach. Between 1961 and 1971 the conversion of dollars into gold was
restricted class by class, on dated occasions, and the United States' gold was counted
each month. This station reads the flow across those dates, by class where the classes
are on record.

## 1. Setup

Positions are (dollar, date) and (gold, date). The conversion edge carries the official
price of 35 dollars an ounce for monetary authorities at the US window. The private class
trades gold in London.

| date | occasion | what it did to the conversion |
|---|---|---|
| 1961-11 | Gold Pool founded | the Pool sells in London to hold the price near 35, and the United States supplies its share, so the private class reaches US gold through the Pool |
| 1967-03-30 | letter of the Bundesbank | one official holder undertakes not to convert on a large scale |
| 1968-03-17 | two-tier market | official transactions stay at 35 and the central banks stop supplying the London market: the private class is cut from the conversion |
| 1969-12-30 | South Africa and the IMF | South Africa may sell newly mined gold to the IMF at 35 when the free price is at or below 35: a priced edge under the free price |
| 1971-08-15 | window closed | no class converts |

With two classes and two positions there is one square: the official price against the
free price, with the agent edge between the two classes cut by the split. Under a single
price for gold its sum is zero.

## 2. Data

| file | what | caliber |
|---|---|---|
| `data/b64/lbma_gold_usd_am_pm_19680401_19711231.csv` | London fixing, morning and afternoon, 954 dates | US dollars per troy ounce, as the publisher prints it |
| `data/b64/fred_M1476CUSM144NNBR.csv` | US monetary gold stock, 1947 to 1970 | millions of dollars, monthly averages of daily figures, **the Treasury's own gold** |
| `data/b64/frb_table4_us_reserve_assets.csv` | US reserve assets, year ends 1958 to 1970, month ends September 1969 to September 1971 | millions of dollars; carries **the total gold stock, the Exchange Stabilization Fund's gold included**, beside the Treasury's |
| `data/b64/frb_table6_us_liquid_liabilities.csv` | US liquid liabilities to foreigners, by holder, year ends 1957 to 1969, month ends July 1970 to July 1971 | millions of dollars |
| `data/raw/ICPSR_111725-V1.1.zip` | replication package of Bordo, Monnet and Naef (2019): US gold transactions by customer government, quarterly, 1965 Q1 to 1968 Q4 | millions of dollars; positive is a US purchase of gold |

The two Federal Reserve Bulletin tables are transcribed by hand, row by row with issue and
page, and each row is checked against the table's own sums; they hold on every row that
prints its components. The loader recomputes a digest of every file and refuses one that
is not the file retrieved.

**The flow is read on the total stock.** The Treasury's column in the FRED series stands at
exactly 10,367 from July 1968 to December 1969, while the total, the Exchange Stabilization
Fund's gold included, moves from 10,892 at the end of 1968 to 11,859 at the end of 1969:
after the split, official gold transactions ran through the Fund. The package's quarterly
movement of the gold stock sums to the Bulletin's total within 6 in every complete year
(1965: -1,671 against -1,665; 1967: -1,175 against -1,170; 1968: -1,178 against -1,173),
and in 1968 the Treasury's own stock fell 1,615, so the package is on the total basis too.

## 3. Criteria, and how to read them

The criteria come in kinds. `instrument` and `known_answer` ask about this run's inputs;
`own_reading` asks whether the stage's own reading holds; `bookkeeping` asks whether
something that has to be printed was printed. A failure of the first two kinds stops the
run until the input is repaired; a failure of an own reading withdraws that reading. None
of this stage's criteria is a rival's point prediction.

| criterion | kind | state | verdict |
|---|---|---|---|
| B64-1 the two series load, parse and carry their units | `instrument` | | PASS |
| B64-2 the price file reproduces the published anchors of April 1968 (36.70) and March 1969 (43.82) | `known_answer` | | PASS |
| B64-3 after the split the gold stock falls more slowly than in the year before it | `own_reading` | slower | PASS |
| B64-4 the South African arrangement puts a floor under the free price | `own_reading` | floor with friction | PASS |
| B64-5 the size of the square, month by month | `own_reading` | printed | no verdict |
| B64-6 the forced exit runs toward devaluation of the dollar against gold | `own_reading` | devaluation | PASS |
| B64-7 the capacity side | `bookkeeping` | printed | PASS |
| B64-8 placement | `bookkeeping` | written | PASS |

Each record prints, with every criterion of more than two states, the state and the verdict
each state maps to.

## 4. B64-3: the flow of the classes that could still walk the edge

**On the total stock**, outflow per month, positive being gold leaving the United States:

| segment | from, to | months | change | outflow per month |
|---|---|---|---|---|
| letter to split | end of 1967 Q1 to end of 1968 Q1 | 12 | -2,488 | 207.3 |
| split to arrangement | end of March 1968 to end of 1969 | 21 | +1,158 | -55.1 |
| arrangement to the last month end with the window open | end of 1969 to end of July 1971 | 19 | -1,406 | 74.0 |

Through August 1971 the last segment reads 82.5 a month. Net of the IMF's gold
transactions (-22 and -475, from the liabilities to the IMF arising from gold
transactions), the two segments after the split read -56.2 and 49.0. **Both readings are
slower than the year before the split.** Printed and kept in: France sold 600 of gold to
the United States in 1968 Q2 to Q4; the Bundesbank sold 500 on 1969-12-29; in 1970 the
Treasury sold 550 to the Swiss National Bank and 20 to the Netherlands Bank to clear swap
drawings. The first two are official holders walking the same edge in the other
direction and the third is an official dollar claim turned into gold, so all three are
flow on the edge.

**By class**, from the package, the four quarters before the split against the three
after, per month, negative being a US sale of gold:

| class | before | after |
|---|---|---|
| United Kingdom, the Gold Pool included | -148.5 | +7.2 |
| Pool members other than the United Kingdom and France (Belgium, Germany, Italy, the Netherlands, Switzerland) | -33.2 | -5.9 |
| non-members, the IMF included | -10.3 | -47.3 |
| France | 0.0 | +66.7 |

The United Kingdom's line is the one through which the Pool's sales in London reached US
gold, and it stops in the first quarter after the split. Official non-members bought more
for two quarters, and France turned seller. **The flow fell on the class the split cut.**

**At the other dated restrictions**, printed without a verdict:

- Gold Pool, 1961-11: the Treasury's gold fell 95.1 a month from December 1958 to October
  1961 and 64.9 a month from then to March 1967. This date opened a route for the private
  class.
- Letter of the Bundesbank, 1967-03-30: Germany's own line was -45.3 in the eight reported
  quarters before it and zero in the seven after. The total rose from 64.9 to 167.7 a month
  on the Treasury's column, carried by the United Kingdom's line after sterling's
  devaluation in November 1967: -19, 27, 137.3 and 3 in the four reported quarters from
  1966 Q1 to 1967 Q1 (1966 Q4 is missing), then -34, -77, -771 and -900. The letter did not reach that class.

At both restrictions the step sits on the restricted line, and the total follows it only
at the date that cut the class carrying most of the flow. That is Corollary 8.6 read with
Corollary 8.4: the capacity is spent by the classes that can still walk the edge.

## 5. B64-4: a priced edge under the free price

Before the arrangement, from 1968-04-01 to 1969-12-29, no fixing was below 35 by more than a
cent; the lowest was 35.00, on 1969-12-09. After it, 21 morning and 19 afternoon fixings were
below 35 by more than a cent, on 24 days between 1970-01-08 and 1970-03-10, the lowest 34.75
on 1970-01-16, 0.71 percent under 35. None was below 34.99 after 1970-03-10, and none below
35.00 after 1970-03-12. Fixings at exactly 35.00 sit on the printed cent and are not judged.
**The floor holds with friction**: whether to sell to the IMF rested with South Africa, and
the free price went under 35 by a quarter of a dollar at most, for two months.

## 6. B64-5: the size of the square

The afternoon fixing's monthly mean against 35, as a log ratio, runs from 0.0786 in April
1968 to 0.2166 in May 1969, falls through zero in January 1970 (-0.0016), and climbs back to
0.1995 in August 1971 and 0.2171 in December 1971. With the window open the highest fixing
was 43.94, on 1971-08-09, 25.5 percent above 35. The monthly path is in the record.

## 7. B64-6: the forced exit

| step | decision | law |
|---|---|---|
| to 38 | "Connally also said the administration would approach the Congress for authority to increase the gold price to $38 per ounce" (Foreign Relations of the United States, 1969-1976, Volume III, Document 221, on the meeting of 17 and 18 December 1971) | "The Secretary of the Treasury is hereby authorized and directed to take the steps necessary to establish a new par value of the dollar of $1 equals one thirty-eighth of a fine troy ounce of gold." (Par Value Modification Act, Public Law 92-268, 31 March 1972, 86 Stat. 116, section 2) |
| to 42 2/9 | "a 10 percent devaluation of the dollar" (The American Presidency Project, note to Richard Nixon's remarks of 13 February 1973 on the Secretary of the Treasury's announcement) | "0.828948 Special Drawing Right or, the equivalent in terms of gold, of forty-two and two-ninths dollars per fine troy ounce of gold" (Public Law 93-110, 21 September 1973, 87 Stat. 352) |

35 to 38 to 42.2222 dollars an ounce: the dollar lost 7.89 and then 10.00 percent of its
gold content, the second figure being the "10 percent" of the announcement. **Both
adjustments run toward devaluation**, the direction Corollary 8.6 gives a forced exit when
capacity is bounded against outflow.

## 8. B64-7: the capacity side

The gold stock on the total basis over US liquid liabilities to foreign official
institutions, and over liabilities to all foreigners. Where reporting coverage changed,
the table prints two lines for one date, the first comparable with the preceding date and
the second with the following one, and the ratio is printed on both.

| date | gold | official | ratio | all foreigners | ratio |
|---|---|---|---|---|---|
| end of 1959 | 19,507 | 10,120 | 1.928 | 19,428 | 1.004 |
| end of 1960 | 17,804 | 11,078 / 11,088 | 1.607 / 1.606 | 20,994 / 21,027 | 0.848 / 0.847 |
| end of 1961 | 16,947 | 11,830 | 1.433 | 22,853 / 22,936 | 0.742 / 0.739 |
| end of 1962 | 16,057 | 12,748 / 12,714 | 1.260 / 1.263 | 24,068 | 0.667 |
| end of 1963 | 15,596 | 14,387 / 14,353 | 1.084 / 1.087 | 26,361 / 26,322 | 0.592 / 0.593 |
| end of 1964 | 15,471 | 15,428 / 15,424 | 1.003 | 28,951 / 29,002 | 0.534 / 0.533 |
| end of 1965 | 13,806 | 15,372 | 0.898 | 29,115 | 0.474 |
| end of 1966 | 13,235 | 13,600 / 13,655 | 0.973 / 0.969 | 29,904 / 29,779 | 0.443 / 0.444 |
| end of 1967 | 12,065 | 15,653 / 15,646 | 0.771 | 33,271 / 33,119 | 0.363 / 0.364 |
| end of 1968 | 10,892 | 12,548 / 12,481 | 0.868 / 0.873 | 33,828 / 33,614 | 0.322 / 0.324 |
| end of 1969 | 11,859 | 11,955 / 11,957 | 0.992 | 41,735 / 41,859 | 0.284 / 0.283 |
| end of 1970 | 11,072 | 20,041 / 20,057 | 0.552 | 43,264 / 43,258 | 0.256 |
| end of July 1971 | 10,453 | 32,953 | 0.317 | 53,264 | 0.196 |

The ratio to official claims crossed one between the end of 1964 and the end of 1965, came
back to 0.992 at the end of 1969 while the private class was off the edge, and fell to
0.317 by July 1971. The month ends from July 1970 are in the record.

## 9. Three things the package and the tables say beside their totals

1. **The package's final classification counts Algeria's purchase of 150 twice in 1967
   Q4.** Its non-member cell is entered as `-99-150`, and the -99 already contains Algeria:
   the other classification table computes it as `CG14-(CM14+CO14+CP14-AW14)`. The four
   classes then sum to -1,105 against a quarterly total of -955. I form the classes from
   the country columns, with the membership of the final table, and that quarter reads -85,
   -99, -771 and 0. Both of the package's classification tables are printed in the record
   as delivered.
2. **1966 Q4 is missing from the archive source and the sheet prints it as zeros**, total
   included; the row is highlighted with 1966 Q3, which comes from a Bank of France document
   and carries one decimal (-31.3, 137.3, -277.3). The loader reads 1966 Q4 as missing.
3. **The Treasury's gold rose 1,000 in January 1970 while the total rose 23.** The month
   ends are 10,367, 11,367 and 11,367 for the Treasury and 11,859, 11,882 and 11,906 for
   the total, December 1969 to February 1970: the Exchange Stabilization Fund transferred
   gold to the Treasury. The inflow itself shows in the total in December 1969, from 11,171
   to 11,859, the month of the Bundesbank's sale.

The afternoon fixing in the package, taken from FRED after March 1968, agrees with the LBMA
file on 742 of 949 common dates; 206 differ only because the LBMA file rounds a third
decimal to the cent, and 1968-05-16 reads 42.25 in the package and 41.25 in the LBMA file,
where that day's morning fixing was 40.85 and the next morning's 41.60. The stage reads the
LBMA file.

## 10. Placement

**What this framework reads of the world.** The conversion edge carried the flow of the
classes that could still walk it. When the private class was cut from it on 1968-03-17,
the United Kingdom's line, which had carried the Pool's sales in London, went from -148.5
to +7.2 a month; the total stock took in gold for the 21 months to the South African
arrangement and then lost 74.0 a month to July 1971, against 207.3 a month in the year
before the split, while it stood below the dollar claims of foreign official holders from
the end of 1965. After the window closed the official price moved only up, 35 to 38, then
38 to 42.2222.

**What a single price for gold reads of it.** The free price sits at 35 at all times. With
the window open it reached 43.94, on 1971-08-09, 25.5 percent above 35; after the
arrangement it stood below 35 by more than a cent on 24 days between 1970-01-08 and
1970-03-10, lowest 34.75. Triffin's condition says the system cannot last once dollar
claims exceed the gold stock and names no date; it held for claims of all foreigners from
the end of 1960 and for official claims from the end of 1965, and the window closed on
1971-08-15.

| cell | content |
|---|---|
| **B** | The square against the scalar price field, whose sum it puts at zero. Already counted at earlier stages; not counted again |
| **D2** | Why convertibility lasted after Triffin's condition held. The question sits inside Triffin's argument, which gives no time; Corollary 8.6 gives the time as capacity over the flow of the classes that can still walk the edge, and B64-3 reads that flow falling on the class each restriction cut |
| **A** | The floor under the free price in 1970. The historical accounts give the same answer |
| **C** | Empty |

## 11. Related work

The quarterly US gold transactions by customer are the digitization by Bordo, Monnet and
Naef (2019) of a document in the archives of the Bank for International Settlements, with
1966 Q3 from the Bank of France; their paper reads the Gold Pool's operations, and its share
of the US gold lost in 1967 Q4 reads 0.760 on their own table (the United Kingdom's line,
-771, over the movement of the stock, -1,014). Triffin (1960) states the condition this
station dates. The corollaries read here are proved in [`b63_trilemma.md`](b63_trilemma.md).

- Bordo, M. D., Monnet, E. and Naef, A. (2019). The Gold Pool (1961-1968) and the Fall of
  the Bretton Woods System: Lessons for Central Bank Cooperation. *Journal of Economic
  History* 79(4). Replication package: openICPSR 111725, version V1.1.
- Triffin, R. (1960). *Gold and the Dollar Crisis: The Future of Convertibility.* Yale
  University Press.

## 12. Scope

The by-class reading covers 1965 Q1 to 1968 Q4, the last three years of the Pool and three
quarters after the split. From 1969 the flow is read on the total, with the official
operations that are known printed item by item; a by-customer series for 1969 to 1971 is
printed in the Federal Reserve Bulletin's table of US net monetary gold transactions with
foreign countries, by year, which this station has not transcribed. The dates are read one
by one; with five dated occasions on one currency, nothing here is a statistical claim
across occasions.
