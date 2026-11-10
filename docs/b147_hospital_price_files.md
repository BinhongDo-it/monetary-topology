# B147: the payer-by-item square on a hospital's own published price file

A United States hospital must publish one machine-readable file under 45 CFR 180.50. For each
item it prints the charge negotiated with each payer and plan, and since 2024-07-01 the method
that sets it: a percentage of billed charges, a fee schedule, a case rate, a per diem, or other.
A class difference that used to sit in private bilateral contracts is printed, item by item.

Scripts: `experiments/b147_fetch.py` (retrieval, wholeness checks, manifest),
`experiments/b147_parse.py` (three layouts into one table of cells, with a cache) and
`experiments/b147_payer_item_square.py` (the reading and its self-test).
Record: `results/b147_payer_item_square.json`, carrying the configuration it ran under.
Sources: `data/SOURCES.md`, section B147.

## 1. The object

Row `i` is an item as the file prints it: every code on the line, setting, modifiers, drug unit,
billing class, description. Column `a` is a payer and plan. `P(a, i)` is the printed dollar price.
The square over two columns and two rows is

    S(a, b; i, k) = ln P(a, i) - ln P(a, k) - ln P(b, i) + ln P(b, k).

With `r_i = ln P(a, i) - ln P(b, i)`, `S = r_i - r_k`. Every square of a column pair is zero
exactly when `r` is one constant on the rows the two columns share, that is, when the two columns
are one price list and a factor that depends on the payer alone.

A patient cannot change payer at the desk, so there is no class edge to walk and this is a square
on a published table, the same kind of object as B49, B52, B102 and B123.

## 2. Two accounts, each against the file

The account being scored is the product form used in bargaining models of hospital prices: the
total a payer `m` pays hospital `j` for condition `d` is `w_d * p_mj`, with `w_d` common to all
payers (Gowrisankaran, Nevo and Town, NBER Working Paper 18875, "the base price multiplied by the
disease weight"). In logs the second difference cancels both terms, so it predicts that every
square is exactly zero.

The framework reads the price as a field with two indices. Two columns whose conversion factor
depends on the payer alone are one price and close every square; two columns priced from two
different lists leave squares open, with values set by the two lists.

The file names one closed domain before any price is read. Two cells that are both a percentage
of billed charges, with the same printed pair of percentages on two rows, close the square by
arithmetic.

The method label by itself does not say which list a price is computed from. CMS's guidance on
encoding (Hospital Price Transparency FAQs on encoding algorithms, on cms.gov) describes the value
as the contract arrangement, and has a contract that pays a flat share of gross charges for all
services encoded as computed dollars under `fee schedule`. A column pair labelled with a
percentage on one side and a fee schedule on the other is therefore read as two arrangements, and
whether it is two bases is what the squares show.

Earlier work established the neighbouring facts. The same hospital is paid different prices by
different insurers for the same service, and contracts that pay a share of charges coexist with
prospective contracts inside one hospital (Cooper, Craig, Gaynor and Van Reenen, NBER Working
Paper 21815, on claims). Relative prices across services differ between insurers inside one
hospital: Craig, Ericson and Starc on Massachusetts claims (NBER Working Paper 25190); Wang, Xu
and Anderson on insurer-side files for 1,970 hospitals, ten services and five national insurers,
where the lowest price comes from the same insurer across services in 614 hospitals (JAMA Network
Open 2024;7(12):e2451941); Douven, Burger and Schut on one Dutch hospital (Health Economics,
Policy and Law 2020;15(3):341-354). The failure of the product form's zero is therefore a known
fact, and B147-4 below is that fact read on hospital-side files against a printing-grid floor.
What this station adds is the partition of each hospital's columns into classes joined by compatible
column pairs, with the members of each, and beside it the fewest common price bases those columns
need on the observed cells (section 5.3), the
closed domain named from printed percentages and checked on printed dollars, and a count of how
the method labels are used.

## 3. Files

Six hospital files, each from the hospital's own site at the address its `cms-hpt.txt` names, and
the CMS data dictionary. Sizes in bytes as retrieved on 2026-10-13 (UTC 2026-10-14).

| file | hospital | bytes | layout, template, date |
|---|---|---|---|
| garfield | Garfield County Health Center, Jordan, Montana | 680,743 | CSV wide, 3.0.0, 2026-01-04 |
| mh_tmc | Memorial Hermann - Texas Medical Center, Houston | 36,141,332 | CSV tall, 3.0.0, 2026-04-01 |
| ohsu | Oregon Health & Science University, Portland | 13,498,398 (zip of a 297,896,809-byte CSV) | CSV tall, 3.0.0, 2026-03-23 |
| deaconess | Deaconess Regional Medical Center, Bozeman, Montana | 134,150,342 | JSON, 2.2.0, 2024-11-19 |
| cvmc | Central Vermont Medical Center, Berlin, Vermont | 52,895,861 | CSV tall, 3.0.0, 2026-10-01 |
| cheshire | Cheshire Medical Center, Keene, New Hampshire | 12,956,206 (zip of a 526,379,146-byte CSV) | CSV wide, 3.0.0, 2026-01-01 |

The six were chosen by hand for readable indexes, files on the hospital's own domain and size, so
every share below speaks for these six files. Two files of the University of Iowa Health Care
Medical Center (1,597,353,362 and 1,583,312,047 bytes) were read in a continuation on 2026-10-14,
together with the Medicare Part B drug payment limits; section 7.

## 4. How a cell is read

**Price.** The printed negotiated dollar amount when there is one; otherwise, on a
percentage-of-billed-charges cell, the printed percentage times the row's printed gross charge.
A percentage cell on a row without a gross charge has no price. A price of one cent or less is a
placeholder and is not read. Cells whose method is `other`, or that carry only an algorithm text,
are not read. A (row, column) printed more than once is kept when every printing agrees and
dropped otherwise. Plans of one payer that print identical cells are one column.

**Billing unit.** Percentage of billed charges and fee schedule are charged per item; a case rate
per case; a per diem per day. A row whose two cells are charged in different units is not read:
the product form speaks of the total for an episode and the length of stay is not in the file.
On a column pair the rows therefore fall into PP, PF, FF (per item), CC and DD.

**Floor.** The printing grid. A printed dollar moves by one cent; a computed price by one cent of
gross and one unit of the percentage's last printed decimal. Each row's `r` is then an interval,
and the rows consistent with one constant are those whose intervals share a point. The script
takes the point covered by the most intervals; rows whose interval misses it are the squares
above the floor, each against a row of the modal class. This is the smallest number of non-zero
squares any constant could leave. Squares are counted pair by pair: a column pair sharing `n` rows
gives `n - 1`, and the counts are summed over pairs. Pairs that share a column are not independent
of one another; a file of `m` columns and `n` rows has at most `(m - 1)(n - 1)` independent
squares, and that bound is printed for each file in the record. Shares are ratios of the
pair-by-pair counts.

**Knobs.** Floor multiplied by 1, 2 and 5; the two orders of the price rule. A verdict is read
only when all six settings agree.

## 5. Readings

Criteria come in kinds. `instrument`, `known_answer`, `premise` and `bookkeeping` ask about the
tool, a check with a known result, a fact later criteria depend on, and the record. `own_reading`
is a reading this station registers. `rival` scores the product form's point prediction, and a
criterion of that kind passes when the prediction fails.

| | criterion | reading |
|---|---|---|
| PASS | B147-0 `instrument` **the estimator returns zero on a rank-one table** | 885 squares, none above an exact floor; one cell multiplied by 1 + 1e-9 is reported |
| PASS | B147-1 `known_answer` **the calibration file** | Garfield: all 2,670 cells a percentage of billed charges, one percentage per column (95, 90, 85, 95, 75); 10 column pairs, 5,330 squares, none above the floor; the file's own minimum column equals 0.75 times gross on 527 of 527 rows |
| PASS | B147-2 `premise` **rows where two columns are priced per item by different methods** | 6,557,817 (row, column pair) cells in three files: OHSU 5,887,108, Deaconess 445,276, Central Vermont 225,433; none at Garfield, Memorial Hermann or Cheshire |
| PASS | B147-3 `own_reading` **connected classes per hospital** | k = 1 at Garfield and Memorial Hermann, 4 at Deaconess, 7 at Cheshire, 17 at Central Vermont, 46 at OHSU (29 when 99 in 100 rows suffice); member lists in the record. **Restated 2026-10-27.** k counts connected classes; the fewest common price bases on the observed per-item cells are 1, 2, 4, 18, 16 and 46 (section 5.3) |
| PASS | B147-4 `rival` **the product form on percentage-against-fee-schedule column pairs** | 1,207 column pairs in three files; 1,153 carry a square above the floor and 54 (all at OHSU) have every square within it; 5,768,194 of 6,556,599 squares above the floor; the same 1,153 on all six knob settings |
| PASS | B147-5 `known_answer` **the zero domain named from the method and percentage columns** | Cheshire, on cells that print both the percentage and the dollar amount: 198 column pairs, 10,402,414 squares, none above the floor |
| PASS | B147-6 `own_reading` **two dollar columns of the same method** | share of fee-schedule squares above the floor: Memorial Hermann 0.0093, Deaconess 0.106, OHSU 0.237, Cheshire 0.583, Central Vermont 0.773; Central Vermont's case-rate pairs, 21 of 21 within the floor |
| PASS | B147-7 `bookkeeping` **coverage** | six files read of six in the manifest; cells left out are counted by reason |

The readings above are those of the first six files; with the two Iowa files added they are in section 7, and every number for the first six is unchanged.

### 5.1 The product form, read on the pairs the file labels with two arrangements

| file | column pairs | with a square above the floor | squares | above the floor | share | median multiple of the floor | median absolute log gap |
|---|---|---|---|---|---|---|---|
| OHSU | 942 | 888 | 5,886,156 | 5,113,190 | 0.869 | 10,350 | 1.33 |
| Deaconess | 155 | 155 | 445,121 | 433,813 | 0.975 | 122 | 1.27 |
| Central Vermont | 110 | 110 | 225,322 | 221,191 | 0.982 | 7,861 | 0.557 |

Framework against the file: a square is zero exactly when two columns share a base. 1,153 of
1,207 pairs carry squares above the floor; the other 54, all at OHSU, are one base under two
labels. Product form against the file: it states zero everywhere; it holds on those 54 pairs and
on 0.120 of the squares. The three hospitals are in three states with three sets of
contracts.

One square as printed (Deaconess): Pacificsource pays a percentage of billed charges, 963.90 for
CPT 37238 and 30.8448 for CPT 86003; Blue Cross Blue Shield of Montana Medicare Advantage pays
from a fee schedule, 11,226.02 and 5.59 for the same two rows. The square is -4.16.

### 5.2 The zero domain

Named from the method and percentage columns alone, and checked on printed dollars, the zero
domain holds on every one of 10,402,414 squares at Cheshire. At Garfield (5,330) and
Deaconess (1,157,599) the same domain's prices are themselves the percentage times gross, so a
zero there is arithmetic and is counted apart.

The method label alone does not name the domain. Where both cells are a percentage of billed
charges, whatever the percentages, squares above the floor number 802,670 of
10,402,432 at Cheshire, 233,541 of 2,005,612 at OHSU, 48,590 of 1,157,618 at Deaconess and 18,928
of 295,069 at Central Vermont: the percentage itself varies by row, as the data dictionary allows.

Three of the six files (Garfield, Deaconess, Cheshire) print a flat discount as a percentage
under the percentage label, where the encoding guidance would have computed dollars under
`fee schedule`. The label is used both ways.

Pairs the file does not name and that are zero all the same: fee-schedule pairs with every square
within the floor number 400 of 406 at Memorial Hermann, 66 of 78 at Deaconess, 37 of 513 at
Cheshire, 2 of 811 at OHSU and none of 128 at Central Vermont.

### 5.3 Price bases

Columns are joined into a class when their price ratio is one constant on every per-item row they
share, and the join runs through chains of such pairs, so a class is a connected component. For these six files, requiring 2, 10 or 50 shared rows gives the same count; the two
Iowa files in section 7 are the first where it does not.

| file | columns | k | the classes |
|---|---|---|---|
| Garfield | 5 | 1 | all five, percentages of billed charges |
| Memorial Hermann | 29 | 1 | all 29, fee schedules; 6 column pairs inside the class differ on the rows those two share |
| Deaconess | 24 | 4 | 12 fee-schedule columns (Medicare Advantage and Veterans Affairs plans); 10 percentage columns; two single columns |
| Cheshire | 37 | 7 | 23 commercial and managed Medicaid columns; 8 Medicare Advantage columns; one pair; four single columns |
| Central Vermont | 17 | 17 | every column its own |
| OHSU | 47 | 46 | one pair joined |

k = 1 is the cell in which the product form holds for the whole file. Which method a payer signs
is a choice made contract by contract, so the count is stated per file and not as a rule.

**Restated 2026-10-27.** `k` is the number of connected classes, and the table above prints it as
the number of price bases; the two are different objects. A set of columns shares one price base
when `ln P(a,i) = alpha_a + beta_i` holds on every observed per-item cell of those columns, each
cell within its printing-grid interval. The fewest such sets are in the record, under
`fewest_common_price_bases` in each file's report, each with matching bounds: a lower bound from a
clique of columns that conflict pairwise (each conflict confirmed in exact arithmetic on the two
rows that attain it), so that no two of them fit one base, and an upper bound from a partition each
part of which passes the joint check, with every per-item cell of the part tested against its
interval rounded inward. The record prints the clique, the sets and the columns without a per-item
cell beside the two bounds.

| file | connected classes k (2 shared rows) | fewest common price bases | where they part |
|---|---|---|---|
| Garfield | 1 | 1 | |
| Memorial Hermann | 1 | 2 | a chain joins Aetna Exchange to six columns it conflicts with |
| Deaconess | 4 | 4 | |
| Cheshire | 7 | 18 | the class of 23 has 156 conflicting pairs inside it; 18 columns of the file conflict pairwise |
| Central Vermont | 17 | 16 | two columns share one per-item row, below the two-row join, and fit one base |
| OHSU | 46 | 46 | |
| Iowa main campus | 18 | 27 | chains inside the classes of 24 and 12 columns; 48 of 54 columns carry per-item cells |
| Iowa Downtown | 16 | 25 | the same with 23 and 12; 45 of 51 columns carry per-item cells |

The sentence above that k = 1 is the cell in which the product form holds for the whole file holds
at Garfield only. At Memorial Hermann the one class needs two bases. Aetna Medicare Managed Care
Plan and Aetna Exchange print 111,492.17 and 172,812.86 for HCPCS Q0480 (outpatient) and 399,661.70
and 659,441.80 for MS-DRG 018 (inpatient): log ratios -0.4383 and -0.5008, a gap of 6.45 percent
beyond both cells' printing intervals. The chain that joins them runs through Amerivantage Medicare
Managed Care Plan, which prints 770 rows, all inpatient. With Aetna Exchange apart, the other 28
columns fit one base. At Central Vermont the 17 classes are the right output of the join rule, and
the observed cells need 16 bases: Aetna Medicare Advantage and Cigna Behavioral Health share one
per-item row (CPT 99245, 249.62 and 225.00) and fit one base on every cell either prints; how the
two relate on items neither prints is not in the file. At each Iowa campus six columns (Aetna
Commercial, Cigna Lifesource Transplant, Interlink Medical Excellence Network, LifeTrac Transplant,
Optum Commercial/Medicaid, Wellmark Blue Distinction Transplant) print cells in other billing units
only; each is a class of one with no per-item cell, so its base is not identified, and 27 and 25 come
from the columns that print per-item cells. With rows whose gross charge is one dollar or less left
out, 27 and 25 stay. On the fewest common bases a hospital carries from one to forty-six, as before.

## 6. Scope

The files print the price and the method of each cell; stepped terms and caps appear only as free
text and are not parsed. Which published schedule a fee-schedule column follows is not printed;
for drugs, section 7.3 reads it against the Medicare Part B payment limit, and for laboratory tests
the CMS Clinical Laboratory Fee Schedule is not read (its download sits behind a licence page). The Deaconess
file is an earlier template (2.2.0, dated 2024-11-19). Rows keep the description and every code,
so one procedure code in two departments is two rows.

## 7. Continuation: University of Iowa, and the Medicare Part B drug payment limit

Retrieved 2026-10-14. Two files of one legal entity, the State University of Iowa, one per
campus, from `www.healthcare.uiowa.edu/marcom/uihc/billing/`, the two `mrf-url` addresses in the
hospital's index at `uihc.org/cms-hpt.txt`, both template 3.0.0 dated
2026-03-11. Every one of the 29 header names matches the CMS data dictionary. Nine quarterly
Medicare Part B drug payment limit files from cms.gov (October 2024, the four quarters of 2025 and
the four of 2026) are read beside them as reference tables; each prints the column `Payment
Limit` under the title "Payment Allowance Limits for Medicare Part B Drugs", to three decimals.

| file | campus | bytes | item rows | columns (after merging) | cells | percentage | fee schedule | case rate | per diem |
|---|---|---|---|---|---|---|---|---|---|
| uihc | main campus | 1,597,353,362 | 235,513 | 55 (54) | 7,475,874 | 6,959,534 | 484,448 | 30,422 | 590 |
| uihc_dt | Downtown | 1,583,312,047 | 234,382 | 53 (51) | 7,424,130 | 6,930,767 | 460,547 | 31,442 | 517 |

Percentage cells print dollars; the 133 and 825 cells that print a percentage print no dollar
amount, so no cell prints both. Cells printed
more than once with different prices (464,318 and 463,370) and one-cent placeholders (12,165 and
12,163) are counted and not read. With the two files added, every number for the first six files
is the same as before.

### 7.1 Criteria with eight files

| | criterion | reading |
|---|---|---|
| PASS | B147-2 `premise` | qualifying cells: Iowa main campus 7,263,120 and Downtown 6,673,616, beside OHSU, Deaconess and Central Vermont |
| PASS | B147-3 `own_reading` | k = 18 / 19 / 21 at the main campus and 16 / 17 / 19 at Downtown for 2, 10 and 50 shared rows: the first files where the three settings give different counts. Classes: one of 24 commercial and employer columns, one of 12 Medicare Advantage and related columns, one of three Medicaid plans, and single columns. **Restated 2026-10-27.** These are connected classes; the fewest common price bases are 27 at the main campus and 25 at Downtown (section 5.3) |
| PASS | B147-4 `rival` | 2,788 column pairs in five files, 2,734 with a square above the floor, 54 (all at OHSU) with every square within it; 19,598,163 of 20,491,751 squares above the floor; at Iowa 843 of 843 and 738 of 738 pairs, 0.992 of squares; with rows whose gross charge is one dollar or less left out, 840 of 840 and 736 of 736 pairs, 0.993 and 0.992 of squares; the same on all six knob settings |
| PASS | B147-5 `known_answer` | Cheshire as before; at Iowa no cell prints both a percentage and a dollar amount, so the named domain has nothing to check. Both columns labelled a percentage of billed charges, at Iowa: 191 of 604 and 169 of 536 column pairs entirely within the floor, 0.202 and 0.197 of squares above it |
| PASS | B147-6 `own_reading` | Iowa fee-schedule pairs 485 and 414 (40 and 45 within the floor), 0.787 and 0.776 of squares above; case-rate pairs 137 and 154, 0.712 and 0.696 |
| PASS | B147-7 `bookkeeping` | eight hospital files read of eight; nine payment limit files read as reference tables |
| PASS | B147-8 `own_reading` | each column against the Medicare Part B payment limit on drug rows; table in 7.3 |

### 7.2 Each account against the file

The framework: a square closes exactly when two columns share a base. On the pairs labelled with
two per-item arrangements, 2,734 of 2,788 carry squares above the floor, in four legal entities
(the two Iowa campuses are one). The product form: zero everywhere; it holds on 54 pairs and on
0.0436 of squares counted file by file. The two Iowa files nearly repeat each other (section 7.3,
last paragraph); with one of them kept the share is 0.061 (main campus) or 0.063 (Downtown), and
the pairs with a square above the floor number 1,996 or 1,891. By file: OHSU 0.131, Deaconess
0.025, Central Vermont 0.018, Iowa 0.0076 at each campus. The relative-price differences between
insurers inside one hospital were known before (section 2); these are further hospital-side
readings of that fact.

**Magnitude at Iowa.** About a quarter of the Iowa squares on these pairs sit on rows whose gross
charge is one dollar: there a percentage of billed charges prints cents (CPT 14061, gross 1.00,
0.88 from a payer at 88 percent) while a fee schedule prints a price (1,724.20 on the same row).
A one-dollar gross is a stand-in of the same kind as a one-cent price. With those rows left out
the median absolute log gap is 1.00 at both campuses (2.06 and 2.07 with them), beside 1.33 at
OHSU, 1.27 at Deaconess and 0.557 at Central Vermont, which move by less than 0.01. The record
carries both readings.

### 7.3 Which columns price drugs at the Medicare payment limit (B147-8)

The payment limit is read as one more column on drug rows: rows carrying exactly one HCPCS or CPT
code that the limit file lists, cells charged per item. Each hospital column falls in one cell:
it follows the limit (every shared drug row within the floor of one constant c, in the quarter
that covers the file's date), it does not follow it in any quarter read, it shares fewer than two
drug rows, or it follows another quarter's limit and not the default one (listed with that
quarter). A fifth cell carries no verdict: most of the column's shared drug rows sit on one
constant c, and every row off it is off by the same ratio in a column with a different constant.
Two contracts with different multipliers that depart from the limit by one ratio on one row place
the departure on the row (the limit printed for that code, or the unit the hospital prices it in),
and not on either contract. The floor adds the limit's own printing grid, 0.001.

The limit files on cms.gov carry only the latest revision of each quarter: the January 2026 file
read is the revision of 2026-09-15, the October 2025 file that of 2026-08-20. The hospital files
predate those revisions. Each file's revision date is in the record.

| file | follows | does not follow | fewer than two rows | listed | no verdict |
|---|---|---|---|---|---|
| Garfield | 0 | 5 | 0 | 0 | 0 |
| Memorial Hermann | 0 | 0 | 22 | 7 | 0 |
| OHSU | 0 | 36 | 0 | 0 | 11 |
| Deaconess | 0 | 24 | 0 | 0 | 0 |
| Central Vermont | 0 | 16 | 1 | 0 | 0 |
| Cheshire | 0 | 37 | 0 | 0 | 0 |
| Iowa Downtown | 1 | 37 | 8 | 0 | 5 |
| Iowa main campus | 1 | 39 | 9 | 0 | 5 |

- Follows: Medical Associates Medicare Advantage at both Iowa campuses, c = 1.0, first quarter of
  2026, six rows.
- Listed: seven Memorial Hermann columns, in a file dated 2026-04-01, follow the limit of the
  fourth quarter of 2025 as revised on 2026-08-20, exactly on five rows each, at c = 1.00, 1.1,
  1.15, 1.5, 1.55, 1.6 and 1.9.
- No verdict, on the limit everywhere but rows shared across contracts: at Iowa, five Medicare
  Advantage and related columns at each campus (c from 1.00 to 1.05), 679 of 699 rows on the
  constant (673 of 693 for one), the other 20 being seven codes off by one ratio in all six such
  columns (J1885 0.931, J0666 0.940, J1303 1.006, J9308 0.998, J1299 1.005, J2777 1.001, J9055
  0.997). At OHSU, eleven Medicare Advantage, Medicaid and related columns at c from 0.8 to 2.5,
  1,704 to 1,711 of 1,836 or 1,883 rows on the constant. Five of the codes, J9055, J1299, J1303,
  J2777 and J9308, are off by the same ratios at both hospitals, which places those departures in
  the revised limit file. OHSU's other shared rows are vaccines (ratios 0.88 to 1.32) and drugs
  priced in another unit.
- Printed and not judged, columns whose best quarter puts at least 99 in 100 shared drug rows on
  one constant: Central Vermont's MVP and Aetna Medicare Advantage columns, c = 1.0 in the second
  quarter of 2026 (567 and 536 rows); Cheshire's two Anthem commercial columns, c = 1.4151 in the
  fourth quarter of 2025 (978 rows). The limit is 106 percent of the average sales price, and
  1.4151 times 1.06 is 1.5000, so those two columns pay 150 percent of it.

For these columns the base the file does not name is a published Medicare table, at a constant
the file lets one read column by column. The squares between such a column and a percentage
column are then the relative prices of two published tables, the hospital's gross charges and the
payment limit.

**Two campuses of one entity, printed and not judged.** Keyed by payer, plan and every code on the
row, 721,595 keys print a dollar price at both campuses and 660,125 of them (0.915) are the same to
the cent.
