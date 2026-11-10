# B99: drug distribution routes, zero calibrations on NADAC

```
CODE:     experiments/b99_drug_routes.py
FETCH:    scripts/fetch_b99.py
RECORD:   results/b99_drug_routes.json
```

## 1. What the station reads

NADAC, the National Average Drug Acquisition Cost that CMS publishes weekly, gives one
acquisition cost per pricing unit for each 11-digit National Drug Code. One number per NDC is
a field with one index: a scalar on positions. That makes NADAC the place to calibrate the
cycle machinery before it is pointed at a two-index field, and it makes the repackaging route a
reading of its own: under 21 CFR 207.53 a repackager reports *"The NDC assigned to each
finished drug received by the registrant for repacking or relabeling"*, so one batch of tablets
can carry two NDCs, each with its own NADAC.

| | `kind` | what it reads |
|---|---|---|
| `B99-0` | `instrument` | the one-index NADAC field, fed to the cycle machinery as two identical class slices on the repackaging pair graph, returns every square exactly `0.0` and every slice cycle inside its floating-point band |
| `B99-1` | `instrument` | the publisher's own arithmetic: `Percent Change` recomputed from `Old` and `New NADAC Per Unit` lands inside the rounding band of the printed digits, and every row outside it is printed and named by its week |
| `B99-2` | `known_answer` | on the same NDC-11, NADAC's `Pricing Unit` and FDA NSDE's `Billing Unit` agree; every disagreement is named |
| `B99-3` | `own_reading` | the repackaging wedge `log(NADAC repack) − log(NADAC source)`, one number per pair, read into three named cells; the cell with too few pairs, or every wedge at or under its floor, carries no verdict |

`B99-3` is a printed distribution and not a test of a scalar price field: whether a repackaged
NDC and its source are one position cannot be decided without a two-index field.

## 2. Sources, as fetched on 2026-10-29

| source | file | bytes | rows |
|---|---|---|---|
| NADAC 2026, data.medicaid.gov | `nadac-national-average-drug-acquisition-cost-10-28-2026.csv` | 112,571,995 | 1,298,476 |
| NADAC 2025, data.medicaid.gov | `nadac-national-average-drug-acquisition-cost-12-31-2025.csv` | 139,475,442 | 1,608,416 |
| NADAC Comparison, data.medicaid.gov (cumulative from 2013, 617 comparison weeks) | `nadac-comparison-10-28-2026.csv` | 370,916,996 | 3,492,313 |
| FDA NSDE (Comprehensive NDC SPL Data Elements File) | zip of 21,849,404 bytes, one CSV of 84,243,735 bytes | | 671,489 |

The fetcher writes to a `.part` file, resumes with a Range request, and accepts a file only at
exactly the length the server announced. A CSV must carry the header the source prints, with
the same field count on every row; the zip must pass its CRC check and is unpacked by base name
into a new, empty directory. Every column the station reads is matched against the name the
source itself uses, and a file whose header lacks one is refused with its header printed. All
three sources matched. The 2025 NADAC file is published without a final newline; its last row
is whole, and the fetcher accepts such a file only when the last field has a shape earlier rows
of that column carry.

## 3. `B99-1`: the publisher's arithmetic reproduces on 3,491,558 of 3,492,295 rows, and the other 737 are printed

The data dictionary defines `Percent Change` as *"The difference between the New NADAC Per Unit
and the Old NADAC Per Unit, divided by the Old NADAC Per Unit"*, without a scale, and the file
does not print one scale throughout. The scale is therefore read per comparison week
(`Start Date`, `End Date`) from three candidates: a fraction, a per cent, and a hundred times
the per cent.

| reading | rows outside the band |
|---|---|
| one scale for the whole file (per cent) | 107,712 |
| the scale read per week | 737 |

Of 617 weeks, 599 print a per cent. Sixteen weeks with end dates from 2017-12-20 to 2018-04-11
print a fraction, and two (2020-10-21 and 2021-04-14) print a hundred times the per cent. In
those eighteen weeks the per cent was rounded to two places before it was rescaled: every row
there that a single rounding band misses fits that double rounding, 6,765 of 6,765 (0.30108 to
0.29429 is −2.2552 per cent, rounded to −2.26 and printed as `-226.00`). Their band carries
both roundings, `0.005 × scale / 100` on top of the printed digits; in a per-cent week the two
grids coincide.

The 737 rows that remain sit in three weeks:

| week ending | rows | shape |
|---|---|---|
| 2017-06-21 | 360 | changes under 0.1 per cent printed as `0.00` (all 486 such rows that week) |
| 2017-07-19 | 372 | the same (423 of the 461 such rows that week) |
| 2014-08-20 | 5 | `Old` `0.00280`, `New` printed `0.00000`, `Percent Change` printed `-67.14`; the printed prices give −100 |

Every one of the 737 rows is printed in the record (`report.B99-1.outside_rows`) with its NDC,
week, prices and both percentages, and the weeks are named with their row counts: 5 of 18,586,
360 of 20,170 and 372 of 20,697. Read this way, the publisher's arithmetic reproduces on every
row not printed, and each printed row is a place where the printed `Percent Change` departs
from its own definition, read by its week. The flag asserts that rows were recomputed and that
every out-of-band row is named by its week; it is `True`. Every NADAC price in the file,
6,984,626 of them, is printed to five decimals, a fixed published format, so the price
resolution is `1e-5`.

## 4. `B99-2`: 35,666 NDC-11, no disagreement

Across the two annual files NADAC lists 36,056 NDCs. 35,666 of them carry a billing unit in
NSDE, and on every one the two units agree; the other 390 have no billing unit in NSDE and are
not judged. No matched NDC carries two units on either side.

NSDE states that the billing unit is the one field it does not generate from SPL, and that the
column holds an NCPDP Billing Unit (`GM`, `ML` or `EA`). Neither publisher states where its unit
comes from, and both follow the same industry standard, so the agreement is read as two
publishers printing the same unit for every shared NDC, not as two independent measurements
meeting. For `B99-3` it means that no repackaging pair on the shared set will be held out for a
unit split.

## 5. `B99-0` and `B99-3`: waiting for the source-NDC map

Both criteria run on the repackaging pair graph, which comes from DailyMed SPL's source NDCs.
The first step there is a count on a sample of how many repackaged NDCs and their sources both
appear in NADAC. NADAC surveys retail community pharmacies, while much repackaged product goes
to institutions, so this is the one branch that can come up empty. If the count is large
enough, the bulk SPL files and a parser to `repack_ndc,source_ndc` follow. The price resolution
the wedge is read against is already measured: `1e-5` per pricing unit.

## 6. The repackaging pairs on a sample of SPL documents

The source NDC sits in each SPL under the product's own code, as
`asEquivalentEntity/definingMaterialKind/code` in the NDC code system, with equivalence code
`C64637`. `scripts/fetch_b99_spl.py` looks products up through the DailyMed web service by the
package NDC in the labeler's own hyphenated form (NSDE's `Item Code`) and fetches each set id's
XML; it refuses any body that declares a DOCTYPE or an entity, and keeps a file only when it is
as long as announced, parses, ends in `</document>` and has the HL7 v3 `document` root.
`scripts/b99_spl_pairs.py` counts the pairs. The sample is 563 documents, 107.9 MB.

| | random draw (300 NADAC products) | five labelers (471 products) | all |
|---|---|---|---|
| documents with a source NDC | 25 | 255 | 280 |
| repackaging pairs | 79 | 538 | 617 |
| both ends in NADAC | 75 | 530 | 605 |
| both ends on a common date with one pricing unit | 75 | 530 | 605 |

Of the 300 products drawn at random, 23 are themselves the repackaged end of such a pair. The
labelers that carry source NDCs and reach NADAC are retail relabelers; the repackagers that
supply institutions do not appear in NADAC at all. On 604 of the 605 pairs the two NADAC values
are equal to the last printed digit, which is what a rule pricing a generic group as one would
produce; that rule is to be read in the NADAC methodology before the full SPL set is fetched.

## 7. The NADAC methodology: one price per drug group, so the repackaging wedge has no object here

The methodology CMS publishes for NADAC (December 2024, 50 pages) was read before any bulk SPL
download. It reports NADAC per NDC and computes it per group:

- p. 6: "The NADAC is calculated at the drug grouping, classification for rate setting, and
  pharmacy type level." A drug grouping "is primarily based on active ingredient(s), strength,
  dosage form, and route of administration."
- p. 7: "Only NDCs with the same drug grouping, classification for rate setting, and pharmacy
  type indicator will share the same NADAC rate."
- pp. 15-16: "one generic drug NADAC rate will apply to all 'G' NDCs within a drug grouping."
- p. 26: "NADAC rates are applied to the entire grouping regardless of whether or not costs were
  collected for a specific NDC within the drug group".

Groups are split further only by rule: package size for `ML` and `GM` products whose package
prices differ, legend against over-the-counter, therapeutic equivalence code, several brand
manufacturers in one group, and biosimilars (pp. 18-19). No clause addresses repackaged or
relabeled NDCs; "repack" appears only where the package-size exception speaks of a pharmacy
repackaging a large package for dispensing.

A repackaged NDC and its source share ingredient, strength, dosage form and route, so they sit in
one group, and with one classification they carry the group's price. The sample shows it pair by
pair (`scripts/b99_nadac_group_check.py`, reading each pair's common effective date package by
package):

| Count | Value |
|---|---|
| Pairs | 605 |
| Classification for Rate Setting at both ends | G and G on all 605 |
| Repackaged package prices all found among the source package prices | 605 of 605 |
| Product medians equal to the last digit | 604 of 605 |
| Pairs whose price is printed by at least three labelers that day | 601 of 605 |

The one pair whose product medians differ:

| NDC-11 | Description | NADAC Per Unit | Unit | Class |
|---|---|---|---|---|
| `60687012201` (repackaged) | PREDNISONE 5 MG TABLET | 0.04351 | EA | G |
| `60687012211` (repackaged) | PREDNISONE 5 MG TABLET | 0.04351 | EA | G |
| `00603533715` (source) | PREDNISONE 5 MG TAB DOSE PACK | 0.30794 | EA | G |
| `00603533721` (source) | PREDNISONE 5 MG TABLET | 0.04351 | EA | G |
| `00603533731` (source) | PREDNISONE 5 MG TAB DOSE PACK | 0.30794 | EA | G |
| `00603533732` (source) | PREDNISONE 5 MG TABLET | 0.04351 | EA | G |

The SPL names the source at product level, `0603-5337`, and that product spans two drug groups.
The product median, (0.30794 + 0.04351) / 2 = 0.175725, averages them. The repackaged tablets
print the source tablets' price, as do 24 NDCs from 11 labelers that day. Pairing on a nine-digit
product therefore needs to descend to the package, or to the source packages with the same
description, wherever a product spans two groups.

So on NADAC the two ends of a repackaging pair carry one price, set by a published rule that
depends only on group membership. A wedge read there would reproduce that rule: the design's
first cell (a wedge that is zero or constant) would be reached by construction and would say
nothing about a repackaging fee. `B99-3` therefore stays without a verdict and is not run on
NADAC prices; `B99-0`, `B99-1` and `B99-2` are unaffected, and the bulk SPL set is no longer
needed for NADAC. A price set per NDC is what the wedge needs. The Part D quarterly formulary,
network and pricing files carry a plan-level average unit cost keyed by NDC; whether that cost is
set per NDC or per generic group by a maximum allowable cost list is to be read in their own
methodology before any of it is fetched (read on 2026-10-29, section 8). Wholesale acquisition cost is set per NDC by each
labeler, repackagers included, and is distributed through licensed drug compendia. The Federal
Upper Limit and state maximum allowable cost lists price a group, the same shape as NADAC.

## 8. The Part D quarterly pricing file: one price per drug product, so the wedge has no object there either

Read on 2026-10-29 before any data was fetched; the documents are under
`data/raw/b99/docs/partd/` with a SHA-256 manifest. The quarterly Prescription Drug Plan
Formulary, Pharmacy Network, and Pricing Information public use file keys its pricing file on
contract, plan, segment, NDC and days supply, and its record layout (2026, p. 15) defines the
NDC as "11-digit proxy NDC associated with the drug product" and `UNIT_COST` as "Average unit
cost (e.g. per pill) for the specified days supply at in-area retail pharmacies." The formulary
file carries the same proxy NDC beside an `RXCUI` (p. 7).

The submission rules CMS gives plans say where the proxy comes from. The CY 2026 Drug Pricing
Submission Guidelines (May 27, 2025) state: "MPF displays one cost for all National Drug Codes
(NDCs) for a given brand name, generic name, dosage form, route of administration, and strength
combination" (p. 13), and "Related NDCs contained on the CY 2026 FRF must be used for the
submission of Part D drug pricing files" (p. 15), with RXCUI 314231, simvastatin 10 mg oral
tablet, priced under its one related NDC `16729000417`. A plan that cannot price that NDC prices
"the most comparable drug product", and "the pricing file must contain the related NDC from the
FRF" (p. 16). CMS's 2006 notes on the reference file describe the proxy as "a unique identifier
for a drug, similar to a randomly assigned code", picked as the NDC at the median average
wholesale price of the drug.

A repackaged NDC and its source share ingredient, strength, dosage form and route, so they are
one drug product with one RXCUI. In a plan's pricing file at most one of the two NDCs appears,
and the other has no row of its own; both ends carry the plan's one price for that product. That
is one price under a published rule (the design's third clause on conversion rules), coarser
than NADAC, which at least prints its group rate on every NDC of the group. `B99-3` therefore has
no object on this source either. No data was fetched. For the record, the latest quarter,
`SPUF_2026_20261007.zip` (July to September 2026), announces 2,485,007,192 bytes.

The station script lists the source in `GROUP_RATED` beside NADAC, with its pages; on it `B99-3`
lands in its third cell with the carrier as the reason, and a seeded run with differing prices
confirms that. With the default source the rerun record matches the earlier one field by field
apart from the list of group-rated sources and the wording of the third cell. The candidate
left is wholesale acquisition cost, which each labeler sets per NDC and which is distributed
through licensed drug compendia.

The pricing file does have two indices, plan and drug product, and that shape is registered for
the two-index half of the design. It does not bear on the repackaging wedge.
