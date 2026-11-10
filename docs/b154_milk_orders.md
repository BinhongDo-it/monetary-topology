# B154: federal milk marketing orders, one tank of milk, four class prices, a county term on Class I only

Script `experiments/b154_milk_orders.py`, record `results/b154_milk_orders.json`, which carries the
configuration it ran under (versions, floors, base counties, sign rules, list formats). The inputs are not
redistributed; where each file came from, when it was retrieved and how it is checked is in `data/SOURCES.md`.

## 1. What is read

The federal milk marketing orders classify the same producer milk by use (7 CFR 1000.40) and price each
class separately (7 CFR 1000.50). Per hundredweight at 3.5 percent butterfat, on the handler side,

```
P(k, c, t) = B_k(t) + 1[k = I] * d_v(c)        k in {I, II, III, IV}, c the county of the receiving plant
S(I, k; c1, c2) = [P(I,c1) - P(k,c1)] - [P(I,c2) - P(k,c2)] = d_v(c1) - d_v(c2)
```

`d_v(c)` is the county's "Class I differential adjusted for location" in 7 CFR 1000.52, version `v`. The
base terms `B_k(t)` vary by month only and cancel in the square.

**Rival.** A scalar price field on positions: one price for one milk at one place, whatever it is used for.
Premise: on the handler side, in a given county and month, raw milk of a given component basis has one class
price `phi(c, t)`, whatever its use. Entailment: `P(k, c, t) = phi(c, t)` for every `k`, so every square
`S(I, k; c1, c2)` is exactly zero. This framework's opposite point prediction is `d_v(c1) - d_v(c2)`, a number
the rule prints. On the producer side the orders pay one location term for milk of every class (each
order's section .75, pooled in .61), so there both accounts give the same zero.

**Versions of the county table.**

| Version | In force | Read from | Rows | Values | Range | Grid |
|---|---|---|---|---|---|---|
| v2000 | 2000-01 to 2025-05 | CFR 2024 print (equal to the 2000 print county by county, plus Broomfield, CO) | 3,111 | 37 | 1.60 to 4.30 | 0.05 |
| v2025 | 2025-06 to 2026-08 | CFR 2026 print, Shannon County, SD row removed | 3,108 | 42 | 1.70 to 7.40 | 0.10 |
| v2026 | from 2026-09-18 | eCFR current text, which carries 91 FR 59047 | 3,108 | 42 | 1.70 to 7.40 | 0.10 |

Month 2026-09 is read under v2026; the two rows the correction changes carry no Central plant, so the month
reads the same under either version.

Two print details are read as follows, and both are in the record's `config`. The 2000 and 2024 prints give
Pierce County, WA the four-digit code `5303`; the name and state identify it, and the 2026 print carries it as
`53053`. The 2026 print keeps a Shannon County, SD row at `0.00`; 91 FR 59047 explains it as a placeholder
left by the county's renaming to Oglala Lakota (46102) and deletes it. Kept in, it would read as a maximum
square of 7.40; the real maximum is 5.70.

Besides the county table, three southeastern orders (Appalachian, Florida, Southeast) carried an extra Class I
adjustment under their own section .51(b) from May 2008. The all-order overview prints it in a footnote,
+0.30, +1.40 and +0.70 at the three base points, and leaves it out of the Class I price column. The section
text of those .51(b) paragraphs is not on disk, so whether the adjustment varied by county is not read here.
The text has since been read: it varies by county, and the footnoted values are the base counties' entries
(section 11.3).

**Floor.** The county table and the announcements print to the cent on a fixed two-decimal format, so the
floor is 0.01. Every count is repeated at 0.05, 0.10 and 0.50, and a verdict needs all four to agree. All
values in v2000 are multiples of 0.05 and in v2025 and v2026 multiples of 0.10.

## 2. Criteria

Criteria fall into kinds: `instrument` and `bookkeeping` check this run's reading and its inputs, a
`known_answer` reads back objects whose answer the rule fixes, `own_reading` is a reading this station
registers, and `rival` scores the rival's point prediction, where PASS means the rival's prediction does not
hold.

| Criterion | Kind | Status | Reading |
|---|---|---|---|
| B154-0 | instrument | PASS | three versions read row by row on the printed format; the current text equals the 2026 print plus the two changes of 91 FR 59047 (Morgan County, OH 3.90 to 3.80; the Shannon row deleted) |
| B154-0b | instrument | PASS | 3,294 order-month cells of the all-order overview, 2000-01 to 2026-08: Class I price minus the base county's differential is one base price per month across orders; 3,287 cells within 0.01 of it, 7 cells print another order's Class I price for that month while the rest of their row is their own (named below, no verdict); the 51 Western-order cells, whose base county is not on disk, are outside the 3,294 |
| B154-1 | known_answer | PASS | in 1000.50 only paragraphs (b) and (c), Class I skim and butterfat, cite 1000.52; squares among Classes II, III and IV are zero for every county pair, and so is the square of Class I against the Class I ESL price, since paragraph (r) does not cite 1000.52; the eleven order .51 sections name no class but I; on the producer side the eleven .75 sections adjust payment for all producer milk by plant location, naming no class, and the .61 sections pool it |
| B154-2 | rival | PASS, grid mixed (A and B) | every version, on the county table and on the Central order's printed plant lists, has squares above all four floors; county pairs sharing a value read zero, as both accounts predict; the plant lists of the eleven orders pooled read the same way (section 11.5) |
| B154-3 | own_reading | PASS | Central order: 247 months with both location lines read, 74 with the producer line only (the handler line sits on a scanned page), no parse failure; the rival's `T = 0` holds in none of the 247 |
| B154-4 | known_answer | PASS | 12,918 printed plant rows over 320 months agree with the county table; 0 rows off; 1 row named with no verdict |
| B154-5 | bookkeeping | PASS | four classes named in all 321 months; four distinct class prices printed in 47 months and five (with the Class I ESL price) in 16; the version-to-version maps cover every FIPS |
| B154-4b | known_answer | FAIL (62 rows named) | plant lists of the ten other orders: 30,943 rows with a county agree with the county table, 847 of them as the table plus the section .51(b) entry for the county; 62 Upper Midwest rows of 2000 to 2005 print a value off the table (section 11.4); after the second round of county resolution, 31,115 agree, 1,010 of them with a .51(b) entry, 62 off (section 11.7) |
| B154-3b | own_reading | PASS | location dollars of the ten other orders, each line assigned by its printed words; `T` read in 1,057 months of four orders, none zero (section 11.6) |

## 3. Squares (B154-2)

The county-table layer counts all county pairs by closed form, `C(N, 2) - sum_v C(n_v, 2)` non-zero pairs.
The plant-list layer takes the location adjustment each Central announcement prints for each plant, relative
to Jackson County, MO; one county printed with two values in one version would be listed (none is).

| Layer | Locations | Pairs | Zero (A) | Non-zero (B) | Above 0.01 / 0.05 / 0.10 / 0.50 | Independent | Largest | Zero share |
|---|---|---|---|---|---|---|---|---|
| v2000 county table | 3,111 | 4,837,605 | 266,661 | 4,570,944 | 4,570,944 / 4,432,848 / 4,148,741 / 2,675,915 | 36 | 2.70 (Fresno, CA to Broward, FL) | 5.51% |
| v2025 county table | 3,108 | 4,828,278 | 178,221 | 4,650,057 | 4,650,057 / 4,650,057 / 4,458,730 / 3,611,369 | 41 | 5.70 (Ada, ID to Broward, FL) | 3.69% |
| v2026 county table | 3,108 | 4,828,278 | 178,215 | 4,650,063 | 4,650,063 / 4,650,063 / 4,458,859 / 3,611,217 | 41 | 5.70 (Ada, ID to Broward, FL) | 3.69% |
| v2000 Central lists | 70 | 2,415 | 299 | 2,116 | 2,116 / 1,806 / 1,666 / 741 | 12 | 1.00 | 12.38% |
| v2025 Central lists | 31 | 465 | 51 | 414 | 414 / 414 / 367 / 170 | 8 | 1.10 | 10.97% |
| v2026 Central lists | 27 | 351 | 35 | 316 | 316 / 316 / 277 / 125 | 8 | 1.10 | 9.97% |

A square is exactly zero when two counties share a value. There this framework's `d_v(c1) - d_v(c2)` is zero
too, so both accounts give the same answer and the reading agrees with both (cell A); on every other pair the
reading agrees with this framework and not with the rival (cell B). On the current county table (v2026) at
the 0.01 floor: A 178,215, B 4,650,063; summed over the three versions and both layers, A 623,482,
B 13,873,910. On the plant lists no pair has the printed square inside the floor where the
table gives a non-zero one, or the reverse. The verdict needs every layer above all four floors; a layer with
nothing to read carries no verdict and is named. Only Class I carries `d_v`, so the three class pairs (I, II), (I, III), (I, IV) give the same square and
count once. The 2000 print on its own (3,110 counties, without Broomfield) gives 4,567,850 non-zero squares of
4,834,495, largest 2.70.

## 4. Version-to-version map

From v2000 to v2025, 3,104 counties changed value, 2 kept it, 2 codes were added (12086 Miami-Dade, FL and
46102 Oglala Lakota, SD) and 5 removed (12025 Dade, FL; 30113 Yellowstone National Park, MT; 46113 Shannon, SD;
51515 Bedford city, VA; 51560 Clifton Forge city, VA). Every change is an increase, from 0.05 to 3.10; the
modal increases are 1.60 (201 counties), 1.50 (188) and 1.80 (187). From v2025 to v2026 one county changed
(Morgan, OH, -0.10) and the Shannon row went.

The base counties of the eleven orders, each read from its section .51(a): Suffolk, MA 3.25 then 5.10;
Mecklenburg, NC 3.10 then 5.60; Hillsborough, FL 4.00 then 6.80; Fulton, GA 3.10 then 5.80; Cook, IL 1.80
then 3.20; Jackson, MO 2.00 then 3.20; Cuyahoga, OH 2.00 then 3.80; Los Angeles, CA 2.10 then 2.80; King, WA
1.90 then 2.70; Dallas, TX 3.00 then 3.70; Maricopa, AZ 2.35 then 2.60. Every overview header differential
agrees with these.

## 5. Central order location dollars (B154-3)

The pool computation prints two location lines. `A` is the Class I location adjustment to handlers as the pool
computation carries it; `Bp` is minus the producer location adjustment that the pool adds back. Check month:
June 2026, `A = -813,809.91`, `Bp = -5,801,163.19`, `T = Bp - A = -4,987,353.28`.

| Version | Months with both lines | T < 0 | T / Bp, median (range) | T per pooled cwt, median (range) |
|---|---|---|---|---|
| v2000 | 231 | 44 | 0.710 (0.091 to 2.036) | +0.085 (-0.156 to +0.188) |
| v2025 | 15 | 15 | 0.848 (0.729 to 0.877) | -0.366 (-0.410 to -0.266) |
| v2026 | 1 | 1 | 0.861 | -0.377 |

Under v2000 the 44 negative months are 2000-01 to 2003-06, 2004-10 and 2005-01; from 2007 to
2025-05 every month read is positive. Under v2025 every month is negative, with `A` negative too: the 2025
table raised Jackson County by 1.20 while most counties holding Central plants and producers rose by less.
`T` is the producer-side location money the handler side does not offset, which falls on milk outside Class I.

Coverage, 321 months: both lines in 247; producer line only in 74, all between 2003-08 and 2010-08 (11 months in
that span have both lines), where the page carrying the handler line is a scanned image with no text layer; parse failures 0. A month with all non-Class-I milk at
the base county gives `T = 0` in the synthetic check.

The rival's point prediction here is `T = 0`: with one position price for every class, the handler-side
location money would fall on all pooled milk, as the producer-side money does. In none of the 247 months with
both lines is `T` zero; the smallest `|T|` is 64,328.42 (October 2011). The sign of `T` is set by which
counties hold the plants and the producers, and this framework does not predict it, so the reading is
printed and no separate rival criterion is scored.

## 6. Plant lists (B154-4)

Three list formats: county name and the differential at the plant (2000-01 to 2021-06, 257 months), city and
differential without county (2021-07 to 2024-03, 33 months; the county is the one the same listing printed
for that city in another month), and county with FIPS code (2024-04 on, 30 months). 2010-02 has no text list.
Each row's printed adjustment equals `d_v(plant county) - d_v(Jackson, MO)` under the version of its month,
and where the differential is printed it equals `d_v(plant county)`. The 30 FIPS-format footers give Jackson's
own differential, 2.00 then 3.20, and all agree.

The 2004-10 row for Land O'Lakes, Sioux Falls, SD prints the county as "Minnehaah", which matches no county;
the same listing prints Sioux Falls with Minnehaha County only, so the row reads as 46099, and its 1.70 and
-0.30 agree with the table. One row carries no verdict: 2016-02, Independent Dairy Producers, Cimarron, OK,
differential printed 1.40 beside an adjustment of +0.40 on a list whose Jackson line is 2.00, while the table
gives 2.40 and +0.40. Such a row is read as a print slip only while it is the only one in its month; two or
more in one month would mean the differential column is misread, and the criterion fails.

## 7. Overview cells named (B154-0b)

The overview prints Southwest's Class I price for July to December 2002 as the same number it prints for
Pacific Northwest and Western, and Arizona's for December 2008 as Pacific Northwest's. Southwest's and
Arizona's own differentials give the common base in every other month, and in these seven cells the rest of
the row (uniform price, producer price differential, receipts, utilization) is the order's own. These seven
cells are named and carry no verdict. A cell whose whole row equals another order's row that month would
mean the row was read from the wrong order, and the criterion fails. The 2003-10 Central announcement prints Class II pounds as `129.003,209`, read as 129,003,209.

## 8. Classes and depooling, printed only

Every Central announcement names Classes I to IV. The four class prices are printed from 2021-07; from 2025-06
the Class I ESL price (the Class I price plus the ESL adjustment) adds a fifth. No month prints two class
prices at the same number.

Depooling, from the overview, per order and month: producer receipts, the four utilization shares and the
monthly change in receipts, with the months in which the Class III or Class IV price stands above the order's
uniform price. The Class III price is the one Central's announcement prints (from 2021-07), before that
Central's uniform price minus its producer price differential on the announcement, and for the seven months
where the announcement does not read, the same identity on the overview's Central row; every month reads.
The Class IV price is the printed one, 62 months from 2021-07. A month where a price does not read would
carry null.

| Order | Months | Class III above uniform | Class IV above uniform (of 62) |
|---|---|---|---|
| Northeast | 320 | 18 | 12 |
| Appalachian | 320 | 8 | 0 |
| Florida | 320 | 5 | 0 |
| Southeast | 320 | 7 | 0 |
| Upper Midwest | 320 | 53 | 45 |
| Central | 320 | 78 | 36 |
| Mid-East | 320 | 56 | 31 |
| California | 94 | 27 | 36 |
| Pacific Northwest | 320 | 93 | 37 |
| Southwest | 320 | 32 | 25 |
| Arizona | 320 | 57 | 22 |
| Western | 51 | 6 | (terminated 2004) |

Whether to pool is a choice of the handler; the pattern is described in the dairy economics literature, and
the record keeps the rows.

## 9. Not read

The statistical uniform price announcements of the other ten orders (their plant lists and location lines),
and the text of sections 1005.51(b), 1006.51(b) and 1007.51(b) between 2008 and 2025. Both have since been
read (section 11).

## 10. Run

```
python experiments/b154_fetch.py --verify
python experiments/b154_fetch_orders.py --verify
python experiments/b154_fetch_orders.py --extra-verify
python experiments/b154_milk_orders.py --selftest
python experiments/b154_milk_orders.py --mutation
python experiments/b154_milk_orders.py --run
```

The self-test plants a fault for every criterion and checks that its flag turns (a row dropped, Morgan back to
3.90, a three-decimal value, a swapped base county, 0.10 added to one order-month, one order's whole row copied
from another, a county term given to Class III or to the ESL term, the citation moved into Class II, a
producer adjustment tied to Class III, a constant table, one plant-list layer emptied, the Shannon
placeholder put back, a month taken out of the coverage, a plant moved to another county, a list matched to
the wrong version, two misread differentials in one month, a FIPS taken out of the map), and that the named
lists and the depooling denominators move when a single cell is planted. The mutation run plants four faults
in the inputs and each moves a flag. For the ten other orders (section 11) the self-test also plants a swapped
plant county, a list matched to the wrong version, a row 0.30 or 0.10 off its allowed value, a file left out of
the coverage, a place file that puts a city in another county or in two, the section .51(b) text taken away, a
pool line printed twice with two values or with no amount, and another order's page disagreeing with that
order's own file; the mutation run adds three faults (California's adjustment read without its base, Upper
Midwest counties shifted, the Appalachian and Southeast .51(b) tables swapped), each caught.

## 11. The other ten orders

### 11.1 What their announcements print

The statistical uniform price announcements of the ten other orders, 2000-01 to 2026-09, are read in full:
1,879 files (sources and checks in `data/SOURCES.md`). Every file is in the coverage table of the record
(`orders.coverage`), with its pages, image-only pages, the layouts read and the rows taken, zero included.
Each column is read only under the label the page prints for it.

| Order | Files | Plant list with differentials | Rows | Layout |
|---|---|---|---|---|
| Northeast | 321 months | none | 0 | reference zone tables |
| Appalachian | 321 months | 82 (2019-12 to 2026-09) | 1,416 | plant, city, state, `CLASS 1 DIFFERENTIAL` |
| Florida | 9 months, 2 years | none | 0 | pool computation only |
| Southeast | 9 months, 2 years | none | 0 | pool computation only |
| Upper Midwest | 320 months | 316 (2000-02 to 2026-09) | 27,665 | `State County Rate` |
| Mideast | 57 months, 22 years | none | 0 | reference zone tables |
| California | 95 months (from 2018-11) | 95 | 2,169 | county and FIPS, `Loc. Adj.` from Los Angeles County |
| Pacific Northwest | 57 months, 22 years | 9 (2026-01 to 09) | 137 | city, `Class I Differential`, adjustment from King County |
| Southwest | 321 months | none | 0 | handler list without differentials |
| Arizona | 321 months | 5 (2026-01 to 05) | 35 | as Pacific Northwest, base Maricopa County |

### 11.2 Where a row's county comes from

A printed FIPS code, or a printed county name matched within the printed state. A row that prints only a
city takes the county another row printed for the same city and state, in its own order's lists first and
then in any of the eleven, when that county is unique. A row still without a county takes the county of the
Census 2020 place of the printed name in the printed state, when that place lies in one county. A place
that lies in several counties, or a city with no Census place of that name, leaves the row without a county;
those rows are named with their candidates and stay out of the county layers.

Of the 1,588 city-only rows of Appalachian, Pacific Northwest and Arizona, 1,192 take their county from the
place file (Appalachian 1,063, Pacific Northwest 99, Arizona 30). The 396 left: places in several counties,
Charleston, SC (23 rows), High Point, NC (164), North Charleston, SC (8), Portland, OR (18); no Census place of
the printed name, Julian, NC (76), Wirtz, VA (82), Clackamas, OR (11), Boise, ID (9; the Census name is
Boise City), Laveen, AZ (5). With 21 Upper Midwest rows whose printed county matches no county, 417 rows stay
out of the county layers; 181 of them print a value the county table carries somewhere in their state.
A second round for these rows is in section 11.7.

### 11.3 Section .51(b) of the three southeastern orders

From May 2008 to May 2025 the Appalachian, Florida and Southeast orders added a Class I price adjustment by
county. The text is read in four places: the 2009, 2020 and 2024 annual CFR prints and the eCFR text in force
on 2025-02-01. All three orders print the same lead sentence:

> (b) Adjustment to Class I prices. Class I prices shall be established pursuant to § 1000.50(a), (b) and (c) using the following adjustments:

followed by a table headed `State County/parish FIPS Class I price adjustment` (the Southeast print reads
`Country/parish`). The four texts give one table per order on state, FIPS and adjustment: 338 counties for
Appalachian (nine values, 0.10 to 1.00), 63 for Florida (eight values, 0.60 to 1.80), 572 for Southeast
(fourteen values, 0.00 to 1.15). No county is in two tables. Each print carries one source note, the
March 17, 2008 Federal Register document of its order. The entry at each order's base county equals the
adjustment the all-order overview footnotes: Mecklenburg, NC 0.30, Hillsborough, FL 1.40, Fulton, GA 0.70.

A plant row in these months is read against this text: the list of an Appalachian, Florida or Southeast
order prices a county at the table plus its own entry for that county; another order's list prices it at
the table, or at the table plus the entry of the order whose table lists the county. Two rows of the Upper
Midwest lists show the second case:

> 7 CFR 1007.51(b): KY CALLOWAY 21035 0.30
> 7 CFR 1005.51(b): VA ROCKINGHAM 51165 0.10

Murray, KY (Calloway County) prints 2.70 from 2020-08 to 2025-03, the table's 2.40 plus 0.30 (55 rows), and
Mt. Crawford, VA (Rockingham County) prints 2.90 over the same months, the table's 2.80 plus 0.10 (52 rows).
Before 2020-08 the same lists print these two plants at the table value alone, which the Upper Midwest order,
with no section .51(b), also allows. Every Appalachian row from 2019-12 to 2025-05 equals the table plus
Appalachian's own entry for its county (the two counties its table does not list read at the table value),
and from 2025-06, when section .51(b) is reserved, every row equals the table.

### 11.4 B154-4b: plant lists of the ten orders against the county table (known_answer)

| | Rows |
|---|---|
| Rows read | 31,422 |
| With a county, agreeing | 30,943 |
| of which agreeing as the table plus a .51(b) entry | 847 |
| Printing a value off the table | 62 |
| Without a county | 417 |

The 62 rows are a list the check names, all on the Upper Midwest lists: Berkeley Farms (Alameda, CA, a
partially regulated plant) prints 1.75 against the table's 1.80 from 2000-05 to 2005-01 (56 rows), while the
California order's own lists from 2018 print Alameda at 1.80; and in 2004-04 and 2004-05 three Fond du Lac, WI
plants print 1.80 where the same lists print other plants of that county at the table's 1.75 (6 rows). The
criterion's status is FAIL on these rows, which concern the lists and not the framework. Where Pacific
Northwest, Arizona and California (2018 to 2019) print both the differential and the adjustment from the
base, their difference equals the table at the base county on all 244 rows. The counts after the second round
of county resolution are in section 11.7.

### 11.5 B154-2 on the pooled plant lists

The plant lists of the eleven orders are pooled per version: one value per county, the framework's value
being the one the rule allows (the table, or the table plus a .51(b) entry). A county where some row prints a
value the rule does not allow, or whose rows carry two allowed values in one version (Calloway and
Rockingham above), has no settled value; its pairs leave the cell count. Each order's own list is printed
with its own cell and does not gate the verdict: the county table is one table written by the common rule,
and the differential at a county does not depend on which order prints it.

| Layer | Locations | Pairs | Non-zero | Above 0.01 / 0.05 / 0.10 / 0.50 | Independent | Largest |
|---|---|---|---|---|---|---|
| v2000, eleven orders | 192 | 18,336 | 16,025 | 16,025 / 12,652 / 10,686 / 6,080 | 24 | 2.70 (Fresno, CA to Colleton, SC) |
| v2025, eleven orders | 128 | 8,128 | 7,345 | 7,345 / 7,345 / 6,433 / 3,732 | 22 | 3.90 (Cassia, ID to Spartanburg, SC) |
| v2026, eleven orders | 119 | 7,021 | 6,304 | 6,304 / 6,304 / 5,459 / 3,113 | 22 | 3.90 (Cassia, ID to Spartanburg, SC) |

Summed over the three versions at the 0.01 floor, cell A 3,743 and cell B 28,797; no pair falls in C. In
v2000, five counties and 945 pairs are out of the count as above. Colleton County, SC reads 4.30 there, the
table's 3.30 plus Appalachian's entry of 1.00. Printed beside, single-order layers: Upper Midwest and
Appalachian are B in every version; California is B in v2025 and v2026; California v2000, Pacific Northwest
v2025 and v2026 and Arizona v2025 change answer across the four floors (largest square 0.50 or less) and
carry no cell. The verdict of B154-2 stays PASS, grid mixed, and `grid_split` (the current county table)
stays A 178,215, B 4,650,063. The layers after the second round of county resolution are in section 11.7.

### 11.6 B154-3b: location dollars of the ten orders (own_reading)

Each order's section .61 adds to the pool "an amount equal to the minus location adjustments" and subtracts
the plus ones computed under its section .75: that is the producer line, and `Bp` is minus the amount the pool
adds, as for Central. Florida's September 2026 page adds up with it: 45,552,465.08 - 7,644.61 - 243,979.03 +
83,985.23 - 11,665,471.77 = 33,719,354.90, the total the page prints. The handler line is of three kinds, set
by the words each order prints:

| Order | Handler line | Producer line | Handler line is | `T` |
|---|---|---|---|---|
| Northeast; Mideast from 2022; California | Less: Location Adjustment to Handlers | Add: Location Adjustment to Producers | the adjustment from the base county, as Central's `A` | read |
| Mideast to 2021 | Class I Location Differential | Net Producer Location Adjustments | the same | read |
| Appalachian | Location Adjustment (under Class I, whose skim price carries the base differential) | Location Adjustments | the same | read |
| Florida, Southeast, Pacific Northwest, Arizona | Class I Differential at Location (Class I skim priced without a differential) | Location Adjustments | the whole differential at the plants' locations | printed only |
| Southwest | Add: Class I Differential | Add: Location Differential Adjustments 61(c) | not stated on the page | printed only |
| Upper Midwest | not printed | Add: Location Adjustment -- Producer and Unregulated Supply Plant Milk | | `Bp` only |

| Order | Months with `T` | `T < 0` | `T / Bp`, median (range) | June 2026: `A` / `Bp` / `T` |
|---|---|---|---|---|
| Northeast | 321 | 321 | 0.760 (0.642 to 0.811) | -4,658,418.96 / -21,003,509.18 / -16,345,090.22 |
| Appalachian | 320 | 320 | 0.533 (0.224 to 0.750) | -1,603,422.30 / -2,760,537.91 / -1,157,115.61 |
| Mideast | 321 | 320 | 0.738 (-0.372 to 0.864) | -1,208,256.12 / -4,777,686.20 / -3,569,430.08 |
| California | 95 | 95 | 0.889 (0.860 to 0.941) | -1,122,260.44 / -9,378,518.47 / -8,256,258.03 |

The rival's `T = 0` holds in none of the 1,057 months; the smallest `|T|` is 28,255.86 (Mideast). Mideast's
one positive month is September 2006. The whole-differential line would turn into `A` only with the
hundredweight it is charged on, which the page does not define; two readings differ by about 2 percent, and
one of them puts Arizona's average Class I differential for September 2026 at 2.649, above every Arizona plant
the list prints (2.60 and 2.50), so it is not formed. Coverage by order and month is in the record
(`orders_pool.coverage`): no parse failure, no month with two values for one line. One Arizona announcement
(2024-12) carries the Pacific Northwest pool page; the page names its order, is read as Pacific Northwest's,
and both its lines equal Pacific Northwest's own announcement.

### 11.7 A second round for the rows left without a county

RUN 2026-10-29T17:25Z. Two rules are applied to the 396 city-only rows of 11.2 that the place file did not
settle; the record carries both in `config.other_orders`.

(a) A place that lies in several counties. The place file lists every county the place lies in. When, for the
row's order and month, the rule gives every one of those counties the same value (the county table, plus the
order's own section .51(b) entry for Appalachian, Florida and Southeast lists from 2008-05 to 2025-05), the row
takes that value and is marked as spanning counties at one price. No one county is picked: the location is
written as the counties joined by `+` (for example `45015+45019`), and the table is looked up at the first of
them, which gives the same answer at any of them. When the values differ, the row stays without a county and
each county's value is printed (`orders.census_cross_county_same_price`, `orders.census_not_resolved`).

| City | Order | Counties in the place file | Months | Rows | Value at each county | Outcome |
|---|---|---|---|---|---|---|
| Charleston, SC | Appalachian | 45015 Berkeley, 45019 Charleston | 2020-07 to 2022-05 (v2000) | 23 | 4.30, 4.30 | 4.30 |
| North Charleston, SC | Appalachian | 45015, 45019, 45035 Dorchester | 2019-12 to 2020-06 (v2000) | 8 | 4.30 at all three | 4.30 |
| High Point, NC | Appalachian | 37057 Davidson, 37067 Forsyth, 37081 Guilford, 37151 Randolph | 2019-12 to 2025-05 (v2000) | 132 | 3.40 at all four | 3.40 |
| High Point, NC | Appalachian | the same four | 2025-06 to 2026-09 | 32 | 5.60, 5.40, 5.40, 5.60 | no county |
| Portland, OR | Pacific Northwest | 41005 Clackamas, 41051 Multnomah, 41067 Washington | 2026-01 to 2026-09 | 18 | 2.70, 2.70, 2.20 | no county |

(b) A city with no place of that name in its state. A place of the same state whose name is the printed
name's words followed by more words is taken when it is the only one, and then (a) or the one-county rule
applies to it; the place file line is recorded (`orders.census_name_variant`). None, or more than one, leaves
the row without a county.

| City | Order | Rows | Place file | Outcome |
|---|---|---|---|---|
| Boise, ID | Pacific Northwest | 9 | one match, `Boise City city`, line 6428: `ID\|16\|001\|Ada County\|08830\|02409876\|Boise City city\|INCORPORATED PLACE\|C1\|A` | Ada County, 16001 |
| Julian, NC | Appalachian | 76 | no place in North Carolina whose name begins with Julian | no county |
| Wirtz, VA | Appalachian | 82 | no place of that name anywhere in the file | no county |
| Clackamas, OR | Pacific Northwest | 11 | no place in Oregon whose name begins with Clackamas (the name is the county's, which this rule does not read) | no county |
| Laveen, AZ | Arizona | 5 | no place whose name begins with Laveen | no county |

Of the 396 rows, 172 take a value (163 under (a), 9 under (b)) and all 172 agree with the rule; 224 stay
without a county (50 in places whose counties differ, 174 with no matching place). With the 21 Upper Midwest
rows, 245 rows stay out of the county layers; 172 of them print a value the county table carries in their state.

B154-4b: 31,115 rows agree (1,010 of them as the table plus a section .51(b) entry; the 163 rows of (a) are
among these), 62 off as before, 245 without a county; the status stays FAIL on the same 62 rows.

B154-2, pooled lists:

| Layer | Locations | Pairs | Non-zero | Above 0.01 / 0.05 / 0.10 / 0.50 | Independent | Largest |
|---|---|---|---|---|---|---|
| v2000, eleven orders | 195 | 18,915 | 16,598 | 16,598 / 13,224 / 11,258 / 6,640 | 24 | 2.70 |
| v2025, eleven orders | 129 | 8,256 | 7,472 | 7,472 / 7,472 / 6,560 / 3,845 | 22 | 3.90 |
| v2026, eleven orders | 120 | 7,140 | 6,422 | 6,422 / 6,422 / 5,577 / 3,218 | 22 | 3.90 |

Summed over the three versions at the 0.01 floor, cell A 3,751 and cell B 29,600; no pair falls in C; in
v2000, five counties and 960 pairs are out of the count. The verdict stays PASS, grid mixed, and `grid_split`
stays A 178,215, B 4,650,063. Single-order layers, printed and not gating: Appalachian v2000 reads 121 of 136
pairs non-zero; Pacific Northwest gains Ada County (1.70) and now has squares above all four floors in v2025
and v2026 (largest 1.00, Ada, ID to Clark, WA); California v2000 and Arizona v2025 still change answer across
the floors. That single-order layers are printed and do not gate the verdict is now a ruling (2026-10-29),
recorded in `config.single_order_layer_ruling`.

All other readings reproduce bit for bit. Self-test 73 checks; among the new ones, a place seeded across two
counties at different values is not resolved, and a second place whose name begins with Boise makes the name
match not unique and leaves the Boise rows without a county. Mutation eight faults, all caught (the new one
takes the first county of a place without the value check). Two runs are byte-identical (2,206,597 bytes).
