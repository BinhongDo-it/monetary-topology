# B149: Regulation Q ceilings as a holder-by-position table

**What this station reads.** Regulation Q set maximum rates that member banks could pay on time
deposits under $100,000. The same regulation also wrote separate ceilings for two kinds of
depositor: governmental units (section 217.7(d), from 1974-11-27) and Individual Retirement Account
and Keogh plan deposits (a footnote of the Supplement from 1975-12-04, section 217.7(e) from
1977-07-06). For each revision this station reads one table C(a, j): a is the
depositor class (o ordinary, g governmental unit, k IRA/Keogh), j is the member-bank maturity band.
From the run of 2026-10-29 a fourth class is counted beside them: f, foreign official holders
(foreign national governments and their agencies, international entities of which the United States
is a member, and entities the Board designates). Section 217.3(g) takes their time deposits of two
years or less out of the ceiling section altogether; before 1968-10-15 section 217.3(a) did the same
for all their time deposits. The o, g and k readings are computed exactly as before; f is printed
under its own keys.
Every fixed ceiling is read from the page image of the New York Fed circular that transmitted the
revision. The text layer of these scans misreads fractions (the same token stands for 5 1/4 and
5 1/2 on one page, and one row's value is missing from the text layer altogether), so it is kept
only as an index.

Script: `experiments/b149_regq_table.py`. Record: `results/b149_regq_class_table.json`.
Criteria are written in the script; the record carries their text and every quantity the run produces.

## Sources

| Circular | Issued | Effective | What it carries |
|---|---|---|---|
| [8102](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1977_08102.pdf) | 1977-04-27 | 1977-07-06 | new 217.7(e): IRA/Keogh ceiling at the highest permissible rate at any federally insured institution, "presently 7.75 per cent" |
| [8347](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1978_08347.pdf) | 1978-05-18 | 1978-06-01 | 217.7(b)(4) eight years and over at 7 3/4; (d) and (e) as a maximum over all insured institutions, "currently 8.00" |
| [8583](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1979_08583.pdf) | 1979-05-31 | 1979-07-01 | joint announcement: savings ceilings 5 1/4 (banks) and 5 1/2 (thrifts) |
| [8585](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1979_08585.pdf) | 1979-06-13 | 1979-07-01 | full Supplement; (d) and (e) flat at 8; (f) and (g) "may offer this category of time deposit to all depositors" |
| [8616](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1979_08616.pdf) | 1979-08-07 | 1979-08-01 | full Supplement, printed twice; 30 to 89 days from 5 to 5 1/4 |
| [8869](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1980_08869.pdf) | 1980-07-09 | 1980-07-02 | Depository Institutions Deregulation Committee: bank and thrift ceilings on savings and transaction accounts; 12 CFR 1204.107 on IRA/Keogh early withdrawal |
| [9177](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1981_09177.pdf) | 1981-10-30 | 1981-12-01 | Depository Institutions Deregulation Committee: 12 CFR 1204.118, IRA/Keogh deposits of 1 1/2 years and over at any agreed rate |
| [Board press release](https://fraser.stlouisfed.org/files/docs/historical/frsbog/pr/frsbog_pr_19660921.pdf) | 1966-09-21 | 1966-09-26 | Supplement 217.6 under the act signed that day: 5 per cent on time deposits under $100,000, 4 on savings and on short multiple-maturity deposits |
| [7517](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1974_07517.pdf) | 1974-12-04 | 1974-11-27 | new 217.7(d): governmental-unit time deposits under $100,000, "regardless of maturity or denomination", at the highest permissible rate at any insured institution, "currently 7.5"; full Supplement; savings eligibility for governmental units |
| [8940](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1980_08940.pdf) | 1980-10-23 | 1980-10-30 | Deregulation Committee: 14-day minimum maturity, 1204.112 at 5 1/4 for member banks; governmental units at 8 under 217.7(d) |
| [Dallas 81-154](https://fraser.stlouisfed.org/files/docs/historical/frbdal/circulars/frbdallas_circ_19810729_no81-154.pdf) | 1981-07-29 | 1981-08-01 | Deregulation Committee phase-out schedule, 1204.115; table "except for MMCs, governmental units and IRA/Keogh Plans"; 1204.115(b)(2) for governmental units and IRA/Keogh |
| [9196](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1981_09196.pdf) | 1981-11-25 | 1981-11-20 | Deregulation Committee reaffirms the new IRA/Keogh category: five properties |
| [9210](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1981_09210.pdf) | 1981-12-10 | 1981-11-20 | Deregulation Committee removes 1204.118(b), the penalty-free transfer into the new IRA/Keogh category |
| [9424](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1982_09424.pdf) | 1982-12-17 | 1982-10-15 | Board: governmental units eligible for NOW accounts (217.1(e)(3), 217.157) |
| [9524](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1983_09524.pdf) | 1983-07-11 | 1983-10-01 | Deregulation Committee: remaining time-deposit ceilings removed; only passbook savings and regular NOW keep fixed ceilings |
| [Board press release](https://fraser.stlouisfed.org/files/docs/historical/frsbog/pr/frsbog_pr_19860319.pdf), [Dallas 86-034](https://fraser.stlouisfed.org/files/docs/historical/frbdal/circulars/frbdallas_circ_19860415_no86-034.pdf) | 1986-03-19 | 1986-04-01 | ceiling authority expires 1986-03-31; 217.7 removed |
| [7614](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1975_07614.pdf) | 1975-04-21 | 1975-05-16 | governmental units may no longer open NOW accounts (New Hampshire, Massachusetts); existing ones kept through 1975-12-31 |
| [7769](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1975_07769.pdf) | 1975-12-10 | 1975-12-04 | Supplement: IRA deposits exempt from the $1,000 minimum at four and six years; 217.7(d) "currently 7.75" |
| [7847a](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1976_07847a.pdf) | 1976-03-24 | 1975-12-04 | reprint of Regulation Q as amended effective 1975-12-04 |
| [7990](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1976_07990.pdf) | 1976-11-12 | 1976-11-08 | the IRA terms extended to Keogh plan deposits |
| [8709](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1979_08709.pdf) | 1979-12-19 | 1980-01-01 | 90 days to 1 year from 5 1/2 to 5 3/4; new 2 1/2-year certificate; governmental units and IRA/Keogh get the thrift ceiling on it and on the 26-week certificate; full Supplement |
| [8767](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1980_08767.pdf) | 1980-03-05 | 1980-02-27 | Supplement reprinted (second printing of the fixed table); 11 3/4 cap on the 2 1/2-year certificate |
| [9022](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1981_09022.pdf) | 1981-02-24 | 1981-01-15 | pamphlet and Supplement incorporating the Deregulation Committee's rules; 217.7(d) at 8 |
| [9225](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1981_09225.pdf) | 1981-12-31 | 1981-12-16 | technical amendments: 217.7(e)(2) IRA/Keogh at any rate from 1 1/2 years; 217.7(b) reprinted |
| [9360](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1982_09360.pdf) | 1982-09-09 | 1982-09-01 | 217.7(d) rewritten, still 8; new (j) 91-day, (k) 3 1/2 years and over, (l) 7 to 31 days with the bill rate for governmental units and IRA/Keogh |
| [9437](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1983_09437.pdf) | 1983-01-14 | 1983-01-05 | 7 to 31 days of $2,500 or more at any rate for every depositor |
| [9563](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1983_09563.pdf) | 1983-10-11 | 1983-10-01 | 217.7 after the removal of time-deposit ceilings: 7 to 31 days under $2,500 at 5 1/4, governmental units at 8 |
| [9611](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/nycirc_1984_09611.pdf) | 1984-01-12 | 1984-01-01 | 7 to 31 days under $2,500 at 5 1/2; no minimum on three accounts for IRA/Keogh; from 1986-01-01 any rate for every depositor |
| [5248](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1962_05248.pdf) | 1962-10-30 | 1962-10-15 | 217.3(a): the ceilings do not apply to time deposits of foreign governments, their monetary and financial authorities, and international financial institutions with United States membership, for three years (Public Law 87-827) |
| [5690](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1965_05690.pdf) | 1965-08-17 | 1965-08-05 | the same sentence extended to 1968-10-15 (Public Law 89-79), no maturity limit |
| [6227](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1968_6227.pdf) | 1968-10-14 | 1968-10-15 | new 217.3(g): time deposits of foreign monetary authorities with a maturity of not more than two years (Public Law 90-505) |
| [6436](https://fraser.stlouisfed.org/files/docs/historical/ny%20circulars/1969_6436.pdf) | 1969-11-12 | 1969-11-05 | 217.3(g) rewritten: two years or less; foreign governments and their agencies, international entities, entities designated by the Board |
| Federal Reserve Bulletin, [September 1977](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/september-1977-20434), [November 1978](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/november-1978-20447), [November 1979](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/november-1979-20459), [March 1980](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/march-1980-20463), [June 1980](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/june-1980-20466) | | | survey of time and savings deposits at insured commercial banks, surveys of 1977-04-27, 1978-07-26, 1979-07-25, 1979-10-31 and 1980-01-30: distribution of issuing banks and of deposits by the most common rate paid on new deposits, by holder group and maturity, with the share paying the ceiling |
| Federal Reserve Bulletin table 1.16, [September 1978](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/september-1978-20445), [September 1979](https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/september-1979-20458) (and the September 1977 and March 1980 issues above) | | | maximum rates payable at commercial banks and at savings and loan associations and mutual savings banks, side by side |
| Federal Register [1974-12-17](https://www.govinfo.gov/content/pkg/FR-1974-12-17/pdf/FR-1974-12-17.pdf), [1978-05-18](https://www.govinfo.gov/content/pkg/FR-1978-05-18/pdf/FR-1978-05-18.pdf), [1979-06-06](https://www.govinfo.gov/content/pkg/FR-1979-06-06/pdf/FR-1979-06-06.pdf), [1979-08-07](https://www.govinfo.gov/content/pkg/FR-1979-08-07/pdf/FR-1979-08-07.pdf) | | | 39 FR 43618 (Board, effective 1974-12-23), 43 FR 21438 (FDIC 329.7 and FHLBB 526.5, effective 1978-06-01), 44 FR 32356 (FDIC 329.7, mutual savings banks), 44 FR 46266 (FDIC 329.6 and 329.7) |

The circulars, Bulletin pages and Federal Register issues opened for the 2026-10-29 run are kept with
a SHA-256 manifest in `data/raw/b149/` (fetched by `experiments/b149_fetch.py`, page by page through
FRASER's IIIF image and text services; the Federal Register only as whole daily issues).

## The tables (percent, member banks, fixed ceilings under $100,000)

| Band | o 1978-06 | o 1979-07 | o 1979-08 | g, all three | k, all three |
|---|---|---|---|---|---|
| 30 to 89 days | 5.00 | 5.00 | 5.25 | 8.00 | no edge |
| 90 days to 1 year | 5.50 | 5.50 | 5.50 | 8.00 | no edge |
| 1 year to 30 months | 6.00 | 6.00 | 6.00 | 8.00 | no edge |
| 30 months to 3 years | 6.50 | 6.50 | 6.50 | 8.00 | no edge |
| 3 to 4 years | 6.50 | 6.50 | 6.50 | 8.00 | 8.00 |
| 4 to 6 years | 7.25 | 7.25 | 7.25 | 8.00 | 8.00 |
| 6 to 8 years | 7.50 | 7.50 | 7.50 | 8.00 | 8.00 |
| 8 years and over | 7.75 | 7.75 | 7.75 | 8.00 | 8.00 |

In the 1978-06 column only the last row is reprinted in that revision's own circular; the other
seven are read from the 1979-07 Supplement, whose preamble states that the existing fixed ceilings
were not affected by that action.

**Readings.**

- The class-by-position graph has V = 11. With IRA/Keogh edges only from three years up, E = 20 and
  b1 = 10; giving IRA/Keogh the ordinary ceiling below three years (the 1977 circular says such
  deposits stay under the existing ceilings) gives E = 24 and b1 = 14. The four extra squares are zero.
- Single-position class gaps for governmental units run from 300 basis points at 30 to 89 days down
  to 25 at eight years and over (1978-06 and 1979-07); 275 down to 25 in 1979-08. Seven of eight
  cells stand above the 25-basis-point grid of the printed ceilings; the eight-year cell sits on it.
- Term-axis squares, governmental unit against ordinary: 28 per revision, the largest 275 basis
  points (11 grid steps) in 1978-06 and 1979-07 and 250 in 1979-08.
- The member-bank table carries eight distinct ceilings, and 8.00 appears only on the class rows.
- Zero domain: the floating categories (f) and (g) carry one rule for every depositor, and the g and
  k rows share the flat 8 from three years up; all 28 such squares read zero.
- One source-internal discrepancy: the Federal Register preamble in circular 8585 prints 8 for the
  eight-year fixed category, while the rule table in the same circular, and the tables in 8347 and
  8616, print 7 3/4. The rule table is used.

## Before 1977: one row, then the governmental-unit row

**1966-09-26 (Board press release of 1966-09-21, Supplement 217.6).** The schedule has one class.
Single-maturity time deposits under $100,000 and multiple-maturity deposits payable after 90 days or
more: 5.00; multiple-maturity deposits payable in less than 90 days: 4.00; savings: 4.00. No section
names a depositor among o, g and k: with those three the class-by-position graph has one class node,
so b1 = 0 and there is no square. Section 217.3(a) names one, see the foreign official holders below:
with f the 1966 table has two classes on all three positions, V = 5, E = 6, b1 = 2.

**1974-11-27 (circular 7517, Supplement 217.7).** Public Law 93-495 extended deposit insurance to
$100,000 for governmental units, and the Board added section 217.7(d) the same day.

| Band | o | g |
|---|---|---|
| 30 to 89 days | 5.00 | 7.50 |
| 90 days to 1 year | 5.50 | 7.50 |
| 1 year to 30 months | 6.00 | 7.50 |
| 30 months to 4 years | 6.50 | 7.50 |
| 4 years and over, under $1,000 | 6.50 | 7.50 |
| 4 years and over, $1,000 and over | 7.25 | 7.50 |

- The governmental-unit ceiling is "the highest of any of the permissible rates that can be paid on
  time deposits under $100,000 by any Federally insured commercial bank, mutual savings bank or
  savings and loan institution", footnoted "currently 7.5 per cent per annum", and the Board's
  statement adds "regardless of maturity or denomination". 7.50 is not a member-bank ceiling: it
  appears only on the class row.
- V = 8, E = 12, b1 = 5. Class gaps: 250, 200, 150, 100, 100 and 25 basis points; the last is one grid
  step. Of the 15 term-axis squares, 14 stand above the grid (largest 225, 9 steps) and one is zero:
  the two 6.50 cells split only by the $1,000 denomination.
- The same amendment let governmental units hold savings deposits at member banks at the ordinary
  savings ceiling: an edge appears at the ordinary value, a zero square.

## Under the Deregulation Committee (1980-1981)

**Bank against thrift, 1980-07 (circular 8869, page 2, current ceilings, percent).**

| Account | Commercial banks | Savings and loans, mutual savings banks |
|---|---|---|
| Savings | 5.25 | 5.50 |
| NOW (New England, New York, New Jersey) | 5.00 | 5.00 |
| ATS | 5.25 | 5.25 |
| TTS | 5.25 | 5.50 |
| PNTS | 5.25 | 5.50 |
| RSU | none | 5.50 |

On the five accounts both sides offer, the thrift-minus-bank gap is 25, 0, 0, 25, 25 basis points, so
all ten bank-against-thrift squares are at most one grid step: six at 25, four at zero. The 1981-10
circular restates the savings pair (5.50 and 5.25), and it agrees with this table.

**The IRA/Keogh line changes twice.**

- 1980-07-02, 12 CFR 1204.107. The early-withdrawal penalty on an IRA/Keogh time deposit after age
  59 1/2 or disability could be waived for any withdrawal at banks, and at savings and loans only for a
  taxable distribution; from this date it can be waived for any withdrawal everywhere. Ordinary
  depositors stay under the penalty at every institution. The class difference stays; the
  difference between institutions in that class difference goes to zero.
- 1981-12-01, 12 CFR 1204.118(a). Institutions "may pay interest at any rate as agreed to by the
  depositor" on IRA/Keogh time deposits of one and one-half years or more. On the same positions
  ordinary depositors still face ceilings, so the IRA/Keogh row carries a value the ordinary row
  cannot: no ceiling.

## Governmental units under the Deregulation Committee (1980-1986)

The Deregulation Committee took over ceiling authority in 1980, while Regulation Q itself, including
217.7(d), stayed in force until 1986. The governmental-unit line is found in both places.

| Effective | Where | What is written |
|---|---|---|
| 1980-10-30 | 8940 p.3 | new 14 to 89 day position: 5 1/4 for ordinary depositors (1204.112); for governmental units "the current ceiling of 8 percent ... will apply to new 14 to 90 day accounts (see 12 CFR 217.7(d))". Class gap 275 basis points |
| 1981-08-01 | Dallas 81-154 p.10 | the phase-out table is printed "except for MMCs, governmental units and IRA/Keogh Plans" |
| 1982-08-01 (scheduled) | Dallas 81-154 p.13 | 1204.115(b)(2), commercial banks, 2 to under 3 years: the 2-year Treasury average less 1/4 point, and the full average "for governmental units and IRA/Keogh depositors", the rate thrifts pay every depositor |
| 1982-10-15 | 9424 pp.9-10 | governmental units become eligible for NOW accounts at member banks: an edge at the ordinary value |
| 1983-10-01 | 9524 p.1 | all remaining time-deposit ceilings removed: governmental units and ordinary depositors under one rule (no ceiling), a zero-domain cell. The Board's text of the same date (9563) narrows the freed range to 32 days and over and to 7 to 31 days of $2,500 or more; below $2,500 governmental units keep 8 until 1986-01-01 (next section) |
| 1986-03-31 | Board press release 1986-03-19 p.1 | "all interest rate ceiling authority expires March 31, 1986"; 217.7 removed from 1986-04-01 |

The 1982 row is the step written in the Committee's order of 1981-07-07; later changes to that
schedule are not part of this run.

**Bank against thrift, 1981-08-01 (Dallas 81-154 page 10).** 90 days to 1 year: 5.75 against 6.00;
1 to 2 1/2 years: 6.00 against 6.50. The one square is 25 basis points, one grid step, the third
state registered before the run.

**The IRA/Keogh line, 1981-11-20.** Circular 9196 reports the Committee's vote of that day: the new
category keeps "(1) a maturity of 1-1/2 years or more, (2) no interest rate restrictions, (3) no
federally required minimum denomination, (4) the normal early withdrawal penalty of six months
interest", and (5) optional additions. Circular 9210 prints the order removing 1204.118(b), the
penalty-free transfer of existing IRA/Keogh deposits into the new category, effective the same day.
The maturity and the absence of a ceiling read back against the 1204.118 text in 9177; the additions
and the transfer rule read back against 9210. All four agree.


## The IRA line from 1975, and the floating positions from 1980

**1975-12-04 (circular 7769, Supplement page 4).** Footnote 2: "The $1,000 minimum denomination
requirement does not apply to time deposits representing funds contributed to an Individual
Retirement Account." The IRA line starts here, before section 217.7(e) existed.

| Band | o | g | k |
|---|---|---|---|
| 30 to 89 days | 5.00 | 7.75 | |
| 90 days to 1 year | 5.50 | 7.75 | |
| 1 year to 30 months | 6.00 | 7.75 | |
| 30 months to 4 years | 6.50 | 7.75 | |
| 4 to 6 years, under $1,000 | 6.50 | 7.75 | 7.25 |
| 4 to 6 years, $1,000 and over | 7.25 | 7.75 | 7.25 |
| 6 years and over, under $1,000 | 6.50 | 7.75 | 7.50 |
| 6 years and over, $1,000 and over | 7.50 | 7.75 | 7.50 |

Ten class cells differ from the ordinary row: eight for governmental units and two for IRA deposits
under $1,000 (75 and 100 basis points). The terms were extended to Keogh plans on 1976-11-08.

**1980-01-01 (circular 8709, Supplement page 5; reprinted in 8767).** The fixed table is the 1979-08
table with 90 days to 1 year at 5.75. On the 26-week money market certificate and the new 2 1/2-year
certificate, member banks "may pay interest ... at a rate not to exceed the ceiling rate payable on the
same category of deposit by any Federally insured savings and loan association or mutual savings
bank" when the deposit belongs to a governmental unit or an IRA/Keogh plan; ordinary depositors get
the bank ceiling. Those two positions carry a class line written as a rule, and it runs through the
bank-against-thrift difference.

**Earlier years.** The text of eighteen Regulation Q circulars from 1970 to 1973 and two reprints of
the regulation contains no clause for governmental units or retirement accounts in sections 217.6 and
217.7. Section 217.3(g) of the same regulation (1972 reprint, page 5) exempts from 217.7 the time
deposits of two years or less owned by foreign national governments and international organizations;
that holder class sits outside the three classes read here.

## The governmental-unit and IRA/Keogh lines in the Board's 217.7, 1981-1986

| Effective | Circular | What is written |
|---|---|---|
| 1981-01-15 | 9022 p.5 | 14 to 89 days 5.25, 90 days to 1 year 5.75, 1 year to 2 1/2 years 6.00; governmental units 8 at each. From 2 1/2 years the floating paragraph (g) pays at least 9.25, above every fixed row |
| 1982-09-01 | 9360 pp.11-16 | 217.7(d) rewritten: 8 per cent "notwithstanding paragraph (b)", except where (f), (g), (j), (k) or (l) apply; the same three fixed rows; 7 to 31 days of $20,000 or more at the 91-day bill rate for governmental units and IRA/Keogh, the bill rate less 25 basis points for others; the 91-day and 3 1/2-year-and-over paragraphs carry one rule for everyone |
| 1983-01-05 | 9437 p.3 | 7 to 31 days of $2,500 or more at any rate for everyone: that class line ends |
| 1983-10-01 | 9563 p.58 | after the removal of time-deposit ceilings, 7 to 31 days under $2,500: ordinary 5 1/4, governmental units 8 under 217.7(d) |
| 1983-12-01 | 9563, 9611 | no minimum balance for IRA/Keogh on money market deposit accounts, Super NOW accounts and 7 to 31 day accounts; others below $2,500 stay under the 5 1/4 (from 1984, 5 1/2) or NOW ceiling |
| 1984-01-01 | 9611 p.2 | 7 to 31 days under $2,500: ordinary 5 1/2; 217.7(d) unchanged at 8 |
| 1986-01-01 | 9611 p.3 | 217.7(b) reserved; 7 to 31 days at any rate "notwithstanding paragraph (d)"; minimums removed: both class lines end |

The Board reprinted 217.7(b) in 9225 with 6 3/4 on the 1 to 2 1/2 year row. The 1981-01 Supplement,
the Committee's 1981-08 table and the 1982-09 order all print 6, and 9225 states that the paragraph
was revised only to add an exception; the table keeps 6 and the discrepancy is listed under B149-1.

## Foreign official holders (sections 217.3(a) and 217.3(g), 1962-1986)

From 1962-10-15 the last sentence of 217.3(a) said the ceilings "shall not apply to the rate of
interest which may be paid by member banks on time deposits of foreign governments, monetary and
financial authorities of foreign governments when acting as such, or international financial
institutions of which the United States is a member" (circular 5248; extended to 1968-10-15 by
circular 5690, page image read). From 1968-10-15 section 217.3(g) limits the exemption to time
deposits "having a maturity of not more than two years" (circular 6227, page image); the rewrite of
1969-11-05 keeps "two years or less" and widens the holders to agencies and to entities the Board
designates (circular 6436). The same paragraph is printed in the 1972 and 1975 reprints and in the
1981 pamphlet that folds in the Deregulation Committee's rules (circular 9022, page 7); Regulation D
of 1983 still refers to deposits exempt "under section 217.3(g)" (circular 9563). The Bulletin's
ceiling table points to it on every issue read ("For exceptions with respect to certain foreign time
deposits see ...").

The class value of f is the absence of a ceiling up to the maturity limit, and o's ceiling above it.
On the tables of this station:

| Revision | positions where f differs from o |
|---|---|
| 1966-09-26 | all three (no maturity limit before 1968-10-15) |
| 1974-11-27, 1975-12-04, 1978-06-01, 1979-07-01, 1979-08-01, 1980-01-01 | 30 to 89 days, 90 days to 1 year, and 1 year to 30 months (the last split by the two-year line) |
| 1981-01-15, 1982-09-01 | 14 to 89 days, 90 days to 1 year, 1 year to 30 months |
| 1980-10-30, 1983-10-01, 1984-01-01 | the one position read (14 to 89 days; 7 to 31 days under $2,500) |

- 30 numeric class cells over twelve revisions; with f, every table revision read writes two class
  values on one position, the 1966-09-26 schedule included.
- On the rule-written positions f has no ceiling where o has a rule: the 26-week certificate on six
  revisions, and on 1982-09-01 the 91-day and the 7 to 31 day $20,000 paragraphs, 1984-01-01 the 7 to
  31 day position under $2,500: 9 class-line cells. Above two years f falls under o's rule (the
  floating four-year and 2 1/2-year categories, the 3 1/2-year paragraph), and where every depositor
  is free of ceilings f and o coincide (1983-01-05, 1983-10-01, 1986-01-01): 8 cells, equal by
  construction, printed beside the zero domain.
- The graph with f: on 1978-06-01 V = 12, E = 28, b1 = 17 (10 without f). Of the 28 f-against-o
  squares 10 are zero (both positions beyond two years), 15 set a ceiling-free value against o's
  ceiling, and 3 have both sides ceiling-free, where the difference is not a number and is left
  undefined rather than filled with zero.
- Events: present on 1966-09-21; two-year cut 1968-10-15; holders widened 1969-11-05; reprinted
  1981-01-15; ends with 217.7 on 1986-03-31. Each inside the window, each with its authority.

## Rates paid: the Bulletin survey of time and savings deposits

The Board and the FDIC surveyed insured commercial banks each quarter and the Bulletin printed, for
each deposit category, the distribution of issuing banks and of deposits by the most common rate
paid on new deposits ("the stated rate per annum ... that banks paid on the largest dollar volume of
deposit inflows during the 2-week period immediately preceding the survey date"), with a column for
banks paying the ceiling. From 1977 governmental units are a separate group with their own maturity
categories; from 1978 IRA and Keogh deposits of three years or more are one category. One survey is
read for each full table: 1977-04-27 (Bulletin September 1977, appendix tables A5 to A15, counts),
1978-07-26 (November 1978, table 2), 1979-07-25 (November 1979, table 4.11), 1979-10-31 (March 1980)
and 1980-01-30 (June 1980), percent of banks and of deposits. 63 category readings, each from the
page image; the parts add to the printed total in every one.

A cell is read as bound when the paying-ceiling share is strictly the largest part of the
distribution, both by banks and by deposits; below when a lower rate is the largest part on both;
undecided when the two measures disagree, or when the survey's ceiling column counts another ceiling
and the largest interval reaches the cell's. Survey categories map to the table's bands (30 up to 90
days to the first band, 90 up to 180 and 180 days up to 1 year jointly to the second, and so on;
governmental units' "1 year and over" to every g cell from one year, where g is one number).

| Class | bound | below | undecided or no source |
|---|---|---|---|
| o | 32 | 1 | 7 |
| g | 0 | 37 | 3 |
| k | 12 | 0 | 8 |

- Ordinary depositors: the ceiling is the most common rate on nearly every band in every survey,
  between 77 and 99 percent of issuing banks. Undecided: the 1975 under-$1,000 positions (the
  category does not isolate them); four to eight years in July and October 1979, where the ceiling
  column counts the four-year variable ceiling of 7.60; and 30 to 89 days in October 1979, two months
  after the step to 5 1/4, where 73.7 percent of banks most commonly paid 5.00 or less while 52.4
  percent of deposits were at 5.25. Below: 90 days to 1 year in January 1980, see the discrepancy
  under bank against thrift.
- Governmental units: the class ceiling (7.75 in 1977, 8.00 from 1978-06-01) is not where they are
  paid. On 1977-04-27, of 4,349 banks issuing 30 to 89 day deposits to governmental units none paid
  7.75 and 3,552 most commonly paid 5.00 or less; from 1978 the share at the ceiling is 0.2 to 30.6
  percent of banks. Undecided where deposits and banks part (30 to 89 days in October 1979 and January
  1980, 90 to 180 days in January 1980: the plurality of deposits at 8.00, the plurality of banks
  below).
- IRA/Keogh: bound in July 1979, October 1979 and January 1980 (53.9, 57.4 and 62.8 percent of banks,
  73.6, 76.0 and 81.3 percent of deposits at 8.00); in July 1978 the survey's top interval stops at
  7.75 while the regulation writes 8, banks and deposits part, undecided; 1975-12-04 has no IRA
  category in the 1977 survey.

**Restated 2026-11-08.** The survey has one IRA/Keogh category, deposits of three years or more
(readings S79a-k, S79b-k and S80-k), and the binding map gives that one reading to each of the four
bands from three years: 3 to 4, 4 to 6, 6 to 8, and 8 years and over. That is a proxy. It reads the
rate most commonly paid on IRA/Keogh deposits of three years or more taken together and does not
separate the bands. What holds without it: on 1979-07-01, 1979-08-01 and 1980-01-01 the ordinary
ceilings at those four bands are 6.50, 7.25, 7.50 and 7.75 (circulars 8585 p.3, 8616 p.3, 8709 p.5),
all below the IRA/Keogh 8.00, and 73.6, 76.0 and 81.3 percent of the category's deposits (July 1979,
October 1979, January 1980) sit in the paying-ceiling column at 8.00. No ordinary depositor may be
paid 8.00 at any band from three years, so on at least one band from three years the two classes are
paid rates at least 25 basis points apart, wherever those deposits fall. That bound is one grid
step, which B149-5 reads as the third state: the gap is exactly 25 if all of those deposits are at
eight years and over. The B149-5 cells above the floor (150, 75 and 50 basis points) and their count
of 5 rest on the proxy, and so do the B149-6 squares, which need the IRA/Keogh rate band by band,
and their count of 6. Both verdicts stand as recorded (PASS, grid B), carried by this proxy; the
coverage is partial. Where the text reads IRA/Keogh as paid 8.00 at 3 to 4 years, read: IRA/Keogh
deposits of three years or more were most commonly paid 8.00.

## Bank against thrift: Bulletin table 1.16

Bulletin table 1.16 prints the ceilings of commercial banks beside those of savings and loan
associations and mutual savings banks. Read on 1977-08-31, 1978-08-31, 1979-08-31 and 1980-02-29:
thrifts are 25 basis points above banks on savings and on every fixed maturity row except 1 to 2 1/2
years, where they are 50 above. The institution-axis squares are therefore 0 or 25 basis points, at
most one grid step on every date (15 or 21 squares a date; 5 or 6 at one step, the rest zero). The
governmental-unit and IRA/Keogh rows carry the same number at both kinds of institution (7.75 in
1977, 8 from 1978), so against o's rows their class-by-institution squares are 25 and 50 basis
points. The survey covers commercial banks only, so no thrift cell has a binding reading and none is
placed.

- The Federal Register issues read confirm the thrift side where they reach: eight years and over at
  8 percent for mutual savings banks and savings and loan associations, and the 26-week certificate
  at the bill rate plus 1/4 (43 FR 21438, effective 1978-06-01); the four-year variable deposit at mutual
  savings banks at one point below the four-year Treasury yield against 1 1/4 at member banks (44 FR
  32356); nonmember banks' schedule 5 1/4, 5 1/2, 6, 6 1/2, equal to the member-bank table of
  1979-08-01, and public units at nonmember banks and mutual savings banks at a flat 8 percent (44 FR
  46266).
- One registered discrepancy: table 1.16 of March 1980 prints 5 1/2 for banks, 90 days to 1 year,
  effective 7/1/73, and the January 1980 survey counts that row's ceiling as 5.50; the rule text of
  circular 8709 (effective 1980-01-01) and its reprint in 8767 print 5 3/4. The rule text is kept;
  the bank-paid rate on that row reads below 5 3/4 either way. Table 1.16 of September 1979 dates the
  30 to 89 day step to 5 1/4 on 9/1/79, circular 8616 on 1979-08-01 (same value).

## Criteria

Criteria come in kinds. Instrument, premise, known-answer and bookkeeping criteria ask about this
run and its inputs; the own-reading criteria are this station's readings; the rival criteria score
the point prediction of a scalar price on positions, which says the class gap and every square are
exactly zero.

| Criterion | Kind | Status | Reading |
|---|---|---|---|
| B149-1 | instrument | PASS | 150 member-bank cells (17 of them second printings) and 18 cells from 1980-81, all read from page images and on the quarter-point grid; the twice-printed 1979-08 and 1980-01 tables agree cell by cell; 81 narrative checks agree with the tables (table 1.16 on four dates and three Federal Register schedules among them); three source-internal discrepancies listed above (8585 preamble, 9225 reprint, table 1.16 of March 1980); 63 survey readings from page images, every one adding to its printed total |
| B149-2 | premise | FAIL | of the 100 cells on the five full tables, 44 bound, 38 below, 18 undecided or without a source; the failing part is the governmental-unit row (0 bound, 37 below): its ceiling is not the rate governmental units are paid. Ordinary rows bound on 32 cells, IRA/Keogh on 12 |
| B149-3 | known_answer | PASS | nine read-backs match: 7.75 (1977), the quarter-point thrift premium, 7.50 for banks, 8.00 (1978), the 25-basis-point gap below savings, 5 to 5 1/4, 7 3/4 at eight years, time-deposit ceilings removed 1983-10-01, and ceiling authority ending 1986-03-31 |
| B149-4 | own_reading | PASS | with f, twelve revisions write two class values on one position (1966-09-26 added): 30 f cells, 9 rule-written f cells, 5 f events in the window with their authority. Without f: eleven revisions write two class values on one position (1974-11-27, 1975-12-04, 1978-06-01, 1979-07-01, 1979-08-01, 1980-01-01, 1980-10-30, 1981-01-15, 1982-09-01, 1983-10-01, 1984-01-01); 73 class cells differ from the ordinary row; 15 rule-written class cells (floating positions) all differ from the ordinary rule; the 1966 schedule has one of the three classes; 26 class-line events between 1966-09-26 and 1986-03-31, each with its authority; the governmental-unit line under the Deregulation Committee is carried by the Board's 217.7(d) to 1986-01-01 |
| B149-5 | rival | PASS (grid: B) | 60 cells; 8 have both sides bound: IRA/Keogh against ordinary at 3 to 4 years, 150 basis points (6 grid steps) on 1979-07-01, 1979-08-01 and 1980-01-01, and on 1980-01-01 also 75 at 4 to 6 years and 50 at 6 to 8; at eight years and over 25 (one step, third state) three times. The 52 others unread (governmental-unit cells below their ceiling, the rest undecided or without a source). The scalar price says zero on every cell; on the bound cells it is wrong. f cells have no binding source and are not placed |
| B149-6 | rival | PASS (grid: B) | 170 term-axis squares; 8 with all four cells bound, all IRA/Keogh against ordinary: 125 basis points (3 to 4 years against eight years) on 1979-07-01, 1979-08-01 and 1980-01-01, and on 1980-01-01 also 75, 100 and 50; two at one grid step. Bank against thrift (table 1.16, four dates, and the 1980-07 and 1981-08 tables): every square at most one grid step, the third state registered before the run, with no thrift binding source |
| B149-7 | own_reading | PASS | all 44 zero-domain cells read zero, including the 1982-09 91-day and 3 1/2-year paragraphs, the 1983-01 and 1986-01 7 to 31 day paragraphs and the 1983-10-01 time-deposit rule |
| B149-8 | bookkeeping | PASS | dates, issuer, circular, pages and authority recorded for all 22 revisions; all 29 items named in the circulars' "retain" lists opened. The last two are the amendment effective 1978-07-06 (circular 8341, 217.1(f)(1): a member bank's note held for the United States is not a deposit) and the one effective 1978-11-01 (circular 8338, 217.5(c): automatic transfers from savings deposits held only by individuals); neither changes a ceiling or writes a class value |

**Restated 2026-11-08.** The B149-5 and B149-6 readings on IRA/Keogh cells rest on one survey
reading, deposits of three years or more, given to four bands; see the restatement at the end of the
survey section.

## Scope of this run

Full tables: 1966-09-26 (one class), 1974-11-27, 1975-12-04, 1978-06-01, 1979-07-01, 1979-08-01 and
1980-01-01; the binding fixed rows of 1981-01-15 and 1982-09-01; single positions on 1980-10-30,
1983-10-01 and 1984-01-01. The window 1966-09-21 to 1986-03-31 is covered at both ends and at each
step of the governmental-unit and IRA/Keogh lines found here. The 1970-1973 single-class tables are
searched for holder clauses but not read cell by cell. Rates paid are read from one Bulletin survey
per full table; thrift ceilings from Bulletin table 1.16 and four Federal Register issues (the
Federal Home Loan Bank Board's 1979-1980 amendments and the Deregulation Committee's Register
notices were not located by issue; their content is read from table 1.16 and from the circulars'
reprints).
