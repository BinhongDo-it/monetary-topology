# B148: customer-class lines on one UK bank's posted mortgage rate tables

HSBC UK posts four mortgage rate pages, one per kind of borrower: first-time buyers (F), people
moving home (M), people remortgaging to the bank from another lender (R), and existing customers
switching product (E). Each page prints, for the same LTV bands, fixed periods and products, an
initial interest rate, a booking fee and an incentive. The same position therefore carries up to
four printed prices, one per class of borrower.

A second bank is read the same way: Barclays UK prints its rates in one customer rate sheet (a
PDF, rates effective from 16 October 2026) with separate tables for purchase (P), remortgage to
Barclays (R) and existing Barclays mortgage customers (E). Section 6 gives its readings.

Script: `experiments/b148_mortgage_class_square.py` (transcription of the page snapshots, the
table, the squares, the criteria and the self-test).
Record: `results/b148_uk_mortgage_class_lines.json`, carrying the configuration it ran under.
Sources: `data/SOURCES.md`, section B148.

## 1. The object

A position is `j = (LTV band, fixed period, product)`; the product carries the booking fee
(Fee Saver, no fee; Standard, 999 pounds; Premier Standard, 999 pounds, for Premier customers).
A class is `a` in {F, M, R, E}. `r(a, j)` is the printed initial rate, read as an exact rational
from its two printed decimals. `c(a, j)` is the printed incentive: cashback in pounds on the
first-time-buyer and moving-home pages, a choice of standard legal fees or 300 pounds cashback at
the same rate on the remortgage page, nothing on the existing-customer page.

An incentive-neutral square takes two classes `a, b` and two positions `j, k` with the same fixed
period, where `c(a, j) = c(a, k)` and `c(b, j) = c(b, k)`. Then

    S = r(a, j) - r(b, j) - r(a, k) + r(b, k)

and fees and incentives cancel term by term in the cost of the four loans, so the square is a
square of the rate alone, whatever the loan amount and term. The unit is 0.01 percentage
point, the unit the pages print; a square is read when `|S|` is at least two units.

Premier Standard is read two ways and both are reported: as a product (a position), and as a
separate class line on each page (class `aP` at the Standard position).

## 2. The accounts, each against the table

Three accounts put the class outside the price at a position, or let it enter only as one overall
shift. Each makes a point prediction:

| Account | Premise | Entailment on this table |
|---|---|---|
| scalar price on the position | `r(a, j) = p(j)` | two classes at one position, both with no incentive, print the same rate |
| additive class shift | `r(a, j) = alpha(a) + beta(j)` | every incentive-neutral square is exactly zero |
| multiplicative class factor | `1 + r(a, j) = A(a) B(j)` | every four-term ratio of `1 + r` is exactly one, and the class difference keeps one sign inside an incentive group |

The framework reads the price as a field with two indices, class and position. No page prints a
rule that writes one class's rate as another's plus a constant (each page was searched for a
comparison with other customer types, a discount or a "same as" sentence; none is there), so the
framework expects open squares on this table, with values set by the bank's pricing of each line.

## 3. Readings

All counts below are for the first read (2026-10-14, 09:53 to 10:01 New York time), Premier as a
product. A second read the same day (10:15 to 10:26) gives the same 208 rows with all 1,248 recorded
fields equal. The Premier-as-class-line reading gives the same verdict on every criterion.

**Scalar price.** At the 24 positions where two classes both carry no incentive, all 24 class
differences are nonzero; the largest is 36 units (existing customer 4.74% against moving home
5.10% at 70% LTV, two-year Premier Standard; 4.94% against 5.29% at 60% LTV, two-year Fee Saver).

**Additive shift.** 750 incentive-neutral squares; 624 are nonzero, 542 are at least two units,
82 sit at exactly one unit. The largest is 38 units: existing customer against moving home, 90%
against 95% LTV, two-year Fee Saver (5.53, 5.54, 5.55, 5.94). By class pair:

| Pair | squares | nonzero | largest (units) |
|---|---|---|---|
| E-F | 144 | 126 | 15 |
| E-M | 174 | 150 | 38 |
| E-R | 162 | 147 | 25 |
| F-M | 108 | 70 | 7 |
| F-R | 72 | 58 | 17 |
| M-R | 90 | 73 | 14 |

**Multiplicative factor.** 678 of the 750 four-term ratios differ from one, 542 of them on a
square of at least two units. In three incentive groups the class difference changes sign. The
first-time-buyer against moving-home five-year group (cashback 500 and 350 pounds on both sides)
prints differences of -1, +2, -1, +2, -3, +4 units across 80%, 85% and 90% LTV, Fee Saver and
Standard: the two lines cross each other inside a block where the incentives do not move.

**Count.** At 32 of 44 positions the four classes print four different rates. The two-year
tracker prints one rate for all classes at every band read (F and M equal at 6 of 6). Among 38
fixed-rate rows that both first-time buyers and movers carry, 36 differ; the two equal ones are
the five-year Premier Standard at 80% and 85% LTV.

**LTV boundaries.** At 20 adjacent-band boundaries every class keeps its incentive on both sides.
The jump differs by class: from 85% to 90% LTV on the two-year Fee Saver, F +17, M +10, R +15,
E +22 units; from 90% to 95% on the same product, M +40 and E +2.

**Full cost where incentives differ.** For the 1,194 squares whose incentives differ, the full
cost over the fixed period (interest on a 25-year repayment loan, plus fee, minus cashback) at
100k, 200k, 300k and 500k pounds, capped by each row's maximum loan: 744 are nonzero at every
amount (619 with one sign at every amount), none is zero at every amount, and 450 are mixed or
contain the legal-fees incentive, whose pound value the page does not print.

**Premier as a class line.** On the moving-home page Premier Standard sits exactly 3 units below
Standard at every band and both fixed periods read, so its twelve squares against the moving-home
Standard line are all zero: on that page the Premier line is a single shift. Against the Standard
line of its own page, the Premier line's largest square is 2 units on the first-time-buyer page
and 7 units on the remortgage and existing-customer pages.

## 4. Criteria

Criteria are written in the script; the record carries their text, and every quantity the run
produces is in the record. Criteria come in kinds: `instrument` and `bookkeeping` ask whether this
run's reading is usable, `known_answer` reads back numbers fixed before the run, `own_reading`
prints an object, and `rival` scores another account's point prediction, where PASS means the
prediction failed on the table.

| Criterion | Kind | Status | Reading |
|---|---|---|---|
| B148-1 | instrument | PASS | titles, eligibility and headers verbatim; the rate column is the one the pages call "Initial interest rate"; every row resolves all eight fields; the same-day second read agrees on every field |
| B148-2 | bookkeeping | PASS | snapshot hashes, prompts and time brackets present; each read within one hour; the next-day read (2026-10-18) is in and compared with the first read row by row |
| B148-3 | known_answer | FAIL | the first read gave 5.36, 5.29, 5.09, 5.06; the next-day read gives 5.31, 5.19, 5.04, 4.99 with the fixed end dates 31.01.2029 and 31.01.2032 unchanged. Between the two reads the bank lowered 134 of the 136 fixed-rate rows on the first-time-buyer, moving-home and remortgage pages by 5 to 19 units (the remortgage 90% five-year Fee Saver stays at 5.59) and left the existing-customer page and every tracker row as they were, so the end dates do not mark a repricing. Every other criterion reads the first-read table |
| B148-4 | own_reading | PASS | 750 incentive-neutral squares printed |
| B148-5 | rival | PASS, grid B | largest class difference 36 units at zero incentive |
| B148-6 | rival | PASS, grid B | 542 of 750 squares at two units or more, largest 38 |
| B148-7 | rival | PASS, grid B | 542 ratios off one on squares of two units or more; three sign-crossing groups |
| B148-8 | own_reading | PASS | 20 boundaries with class-specific jumps |
| B148-9 | own_reading | PASS | four distinct rates at 32 of 44 positions; trackers one rate |
| B148-10 | own_reading | PASS | 744 full-cost squares nonzero at every amount, 0 zero |
| B148-1-Barclays | instrument | PASS | the table path and the text path agree on all 169 rate rows; every column header names "Initial Interest Rate" as the rate column, the APRC column apart |
| B148-2-Barclays | bookkeeping | PASS | the PDF on disk matches its manifest in length and SHA-256; the coverage table lists all 11 pages, the page with no rate row included; every row carries its page and row |
| B148-3-Barclays | known_answer | PASS | every tracker rate equals the printed Bank Rate (3.75%) plus its printed margin, and every follow-on line sums (3.75 + 1.99 = 5.74): 211 checks, 0 off |
| B148-4-Barclays | own_reading | PASS | 40 incentive-neutral squares printed, each cell with its page and row |
| B148-5-Barclays | rival | PASS, grid B | 16 positions with no incentive and the same fee on both sides, 9 nonzero, largest 11 units |
| B148-6-Barclays | rival | PASS, grid B | 29 of 40 squares at two units or more, largest 29 |
| B148-7-Barclays | rival | PASS, grid B | 29 ratios off one on squares of two units or more; two sign-crossing groups |
| B148-8-Barclays | own_reading | PASS | 5 boundaries with class-specific jumps |
| B148-9-Barclays | own_reading | PASS | at 37 shared positions: three rates at 4, two at 19, one at 14 |
| B148-10-Barclays | own_reading | PASS | 84 squares where an incentive or a fee moves: 29 nonzero at every amount, 0 zero, 55 carry a package with no printed pound value |

## 5. The carrier and how it was read

The four pages:

    F  https://www.hsbc.co.uk/mortgages/first-time-buyers/rates/
    M  https://www.hsbc.co.uk/mortgages/our-rates/
    R  https://www.hsbc.co.uk/mortgages/move-your-mortgage/rates/
    E  https://www.hsbc.co.uk/mortgages/existing-customers/switch/rates/

Each page is 113,000 to 170,000 characters of text. It was read through a text-extraction tool in
two windows (from character 0 and from character 100,000), one prompt per group of LTV bands, and
every returned text was saved verbatim with its SHA-256, offset, prompt and a time bracket. The
hash identifies the returned text, not the page bytes. The rows are parsed from those snapshots,
each row keeping its source line. A second read of all four pages on the same day, more than
twenty minutes after the first, is compared field by field; a further read at least 24 hours later
checks the version (no page carries a date; the fixed end dates serve as the version mark).

Eligibility as printed: first-time buyers have "never owned a residential property in the UK, or
anywhere else in the world"; the moving-home tables are labelled "Moving home rates"; the
remortgage rates "are available to people looking to remortgage to HSBC"; existing customers have
an HSBC mortgage whose rate "is coming to an end" and can choose a new deal "up to 90 days before".
The early repayment charge text on the moving-home and existing-customer pages is the same
schedule (1% per remaining year above the 10% allowance, at most 5%).

The Barclays rate sheet:

    https://www.barclays.co.uk/content/dam/documents/personal/mortgages/CoreRangeCustomerRateSheet.pdf

fetched 2026-10-29, 584,117 bytes, SHA-256
`ce5cff8a1b093035d02c78d072ac740a458ded00e20a71990c5ab78ea62c73ea`, printed "Rates effective from
16 October 2026". It was read with a PDF library in two independent ways (table geometry and the
plain text stream), which agree row by row; every row in the record names its page and its row in
that page's table.

**Scope.** Two banks, each read as printed on its own date. The claim is existential: on each
bank's table there are incentive-neutral squares well above the print grid. Each bank is reported
on its own; the counts are not added.

## 6. Second designer: the Barclays customer rate sheet

**Classes and positions.** Purchase is one table on this sheet (first-time buyers and home movers
are not split), so the classes are P, R and E. A position is (LTV band, fixed period, kind), where
the kind carries the product line (standard, Premier, Green Home, Springboard), the fee tier (a
product fee or none) and the loan band (loans from 1m pounds). The same fee tier carries 899 pounds
for purchase and 999 pounds for remortgage and existing customers, so the fee is held on the cell,
and a square is incentive-neutral when each class keeps its incentive and the four fees cancel.
(On the HSBC pages every class pays the same fee at a position, so this adds nothing there.)
Remortgage rows carry the bank's remortgage packages: Switch & Save on fee-paying products (a legal
service, no pound value printed) and The Great Escape on the no-fee products (no product fee, free
legal work and valuation, 150 pounds cashback). The main reading places The Great Escape at the
no-fee position as a remortgage incentive; read as a product of its own, every verdict is the same.
At every position two or more classes share, the early repayment charge, the follow-on rate and
the end date are the same; the maximum loan differs at 90% LTV (640,000 pounds for purchase, 2m
for existing customers), which bounds the loan and leaves the rate on a loan within both bounds
unchanged. The sheet was searched for a sentence that writes one class's rate from another's; the
only hits are two lines about call charges.

**Readings.** 96 fixed-rate residential rows, 61 positions, `b1 = 33`. 40 incentive-neutral
squares: 33 nonzero, 29 at two units or more. The largest is existing customer against purchase,
five-year fee-paying product, 75% against 90% LTV (5.42, 5.30, 5.74, 5.33): 29 units, the existing
customer's rate rising 32 units across that step and the purchase rate 3. By class pair (squares,
nonzero, largest): E-P 22, 22, 29; E-R 6, 6, 11; P-R 12, 5, 7. The existing-customer against
purchase difference changes sign inside both of its incentive groups: two-year, from +11 units
(90% no fee) to -3 (70% large loan); five-year, from +41 (90% with fee) to -4 (70% large loan).

**Where the class lines meet.** On the large-loan band (from 2m pounds) purchase and remortgage
print the same rate at all six positions, and the existing-customer line sits 3 to 4 units below
them at 70% LTV. Trackers print one rate for all three classes at most positions; the existing
customer is lower at three (70% large loan 4.20 against 4.30, 75% 4.20 against 4.26, 90% 4.48
against purchase 4.85). On the remortgage page the Premier line sits exactly 3 units below the
standard line at each of the three positions it prints, the same shape as the HSBC moving-home
Premier line; on the purchase page the Premier line differs from the standard line by 3, 3, 5 and
20 units.

**Premier as a class line.** 44 squares, 36 nonzero, 32 at two units or more, largest 29; the same
verdict on all three accounts.

**Buy-to-let tables, printed only.** 17 positions, `b1 = 10`. Four incentive-neutral squares: two
purchase-against-remortgage squares at 6 units, and two zeros where the existing-customer and
remortgage tables print the same four rates at 75% LTV. The 1m to 2m pound rows are printed once
for purchase and remortgage, and the existing-customer table prints the same rate.

**Representative example, printed only.** The sheet's example prints a first monthly payment of
1,164.36 pounds; a level payment on its printed loan (164,622 pounds), term (276 months) and rate
(4.85%) is 990.82 pounds.

## 7. Related work

LTV notches in UK posted mortgage rates are documented in Best, Cloyne, Ilzetzki and Kleven,
"Estimating the Elasticity of Intertemporal Substitution Using Mortgage Notches", Review of
Economic Studies 87(2), 2020, 656-690, which reads the rate along the LTV index; the class-specific
boundary jumps above are the same notches split by borrower type. A trade report (Mortgage
Solutions, 2019-03-04, "Product transfer rates up to 0.35% cheaper than new deals") compares
existing-customer and new-customer rates at three lenders without holding incentives fixed. The
FCA Mortgages Market Study (MS16/2, final report 2019) discusses long-standing customers on
reversion rates.
