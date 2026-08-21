# A1 inputs: availability check for the four quantities the model refuses to invent

**Addendum to [`a1_availability.md`](a1_availability.md).** That check covered the
stage's *targets*. This one covers its *inputs*, which appeared only once the
model existed: `src/monetary_topology/cascade.py` leaves four values with no
default, because each one decides part of the answer.

Run 2026-08-13. No result exists for this stage. Items that could not be verified
from a retrieved page are marked **unverified** in place.

| input | what it decides | verdict |
|---|---|---|
| the mortgage/consumer-credit split by wealth group | how far the mortgage stock concentrates upward, which feeds the K shape | **available, and better than the model's current route** (§1) |
| `homeownership_by_stratum` | who is exposed to the rent rung at all | **available only by computing it from SCF microdata** (§2) |
| `income_by_stratum` | who absorbs a shortfall | **available, income-ranked only** (§3) |
| `necessities_by_stratum` | the basket that claims income before any obligation | **available, income-ranked only** (§3) |

**The finding that governs the other three is §4: the model's population is ranked
by wealth, and two of its four inputs are published only by income rank.** No
source publishes a consumption basket by net worth percentile.

---

## 1. The debt split: stop computing a residual, read the series

The model currently takes `liabilities_to_consumer_credit` and sets each
stratum's mortgage stock to the residual of total liabilities minus consumer
credit. **That residual is wrong by construction**, and the size of the error is
now measured.

From Z.1, 2026Q1, NSA, households and nonprofit organizations:

| line | series | 2026Q1, $bn | share of total liabilities |
|---|---|---|---|
| Liabilities | `FL154190005` | 21,560.0 | 100% |
| One-to-four-family residential mortgages | `FL153165105` | 13,821.0 | 64.1% |
| Consumer credit | `FL153166000` | 5,073.0 | 23.5% |
| **neither** | | **2,666.0** | **12.4%** |

The remaining 12.4% is municipal debt securities, depository loans not elsewhere
classified, commercial mortgages, other loans and advances, trade payables and
deferred life insurance premiums. A two-way split of total liabilities forces all
of it into whichever leg takes the residual, which in the model is the mortgage
leg, which is the leg the K shape rests on.

**The repair removes the input rather than correcting it.** The DFA publishes
**Home Mortgages** and **Consumer Credit** by the same wealth groups the model
already uses, so both legs can be read directly and no residual, no aggregate
ratio, and no "split the upper strata in proportion to net worth" assumption is
needed. `calibration.py` already carries one of these series,
`WFRBSB50211`. **Unverified**: the parallel series identifiers for the other
three groups and for home mortgages. The fetcher verifies them at retrieval, and
the model must refuse to run on a group whose identifier did not resolve.

Retrieval, all keyless:

- DFA bundle: `federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip`,
  release 2026-06-18, 381 series in FRED release `rid=453`.
- Z.1 dated archives: `federalreserve.gov/releases/z1/YYYYMMDD/z1_csv_files.zip`.
  Verified for `20260319`.
- FRED CSV without a key: `fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`.
  The FRED **API** requires a key; the graph CSV route does not.

**Three traps recorded before anything is retrieved.**

1. **Z.1 was restructured on 2026-06-11.** `B.101` and `L.101` no longer exist;
   the tables are now `S1M.b` and `S1M.s`. `current/html/b101.htm` returns 404.
   Any fetcher written against the old names is already broken. Mapping file:
   `releases/z1/current/z1_table_mapping.csv`.
2. **The seasonally adjusted twins will corrupt the ratio silently.**
   `HHMSDODNS` (13,852,982) and `HCCSDODNS` (5,132,355) carry the same titles as
   the NSA series `HMLBSHNO` (13,820,984) and `CCLBSHNO` (5,073,031) at 2026Q1.
   Use NSA, matching the Z.1 table.
3. **The households-only boundary exists but is annual.** `S14.b`, total
   liabilities `FL194190005` = 19,963.4 bn for 2025. Quarterly data exists only
   for households **and nonprofit organizations**. Whichever is used, the
   boundary is stated with the number.

Also recorded because it was checked and is a non-issue: **G.19 consumer credit
and Z.1 consumer credit are the same number.** `TOTALNS` for March 2026 is
5,073,031.12 thousand and `CCLBSHNO` for 2026Q1 is 5,073,031. There is no sector
mismatch between them; the traps there are seasonal adjustment and monthly
against quarter-end.

## 2. Homeownership by wealth group is not published anywhere

Checked and refuted, one by one:

- **SCF publications.** The 2022 Bulletin's Table 2 does group by percentile of
  net worth (`<25`, `25-49.9`, `50-74.9`, `75-89.9`, `90-100`), and reports net
  worth rather than homeownership. Primary-residence holding appears in Table 3
  for **all families** (66.1% in 2022) and, where grouped, is grouped by **usual
  income**. No table in the Bulletin reports homeownership by net worth
  percentile. The groups on offer also lack a top 1%.
- **DFA.** Its groups match the model's exactly, and its units are dollars.
  Bottom-50% real estate is `WFRBLB50083` = 4,826,745 million at 2026Q1. **A
  share of aggregate real estate value is not a homeownership rate**: the same
  share is consistent with a few large holdings or many small ones, and the DFA
  has no household count to divide by.
- **Census HVS.** Table 8 and historical Table 17
  (`census.gov/housing/hvs/data/histtab17.xlsx`, xlsx, quarterly, revised
  2026-07-28) split at the **median family income** only: 77.9% above, 52.1%
  below, 2026Q2. Two groups, income-ranked.
- **ACS.** `B25118`, tenure by household income, eleven income brackets, API
  available (metadata keyless, data needs a key), 2024 vintage released
  2025-09-11. Income-ranked.

**The only route to a wealth-ranked rate is computing it.** The SCF summary
extract is public and small: `scfp2022excel.zip` (CSV, ~2 MB), with `NETWORTH`,
`HOUSECL` and the weight `X42001/5` present in the Bulletin macro's keep list.
Weight by `X42001/5`, rank by `NETWORTH`, cut at the 50th, 90th and 99th
percentiles, take the weighted mean of the ownership indicator in each group.

Three costs, all disclosed rather than avoided:

1. **Vintage.** The latest completed wave is **2022**. The 2025 wave was fielded
   March to December 2025 and the Fed says summary results arrive "late 2026", so
   it is not available now. Every other input in this stage is a 2024 to 2026
   vintage.
2. **Unverified**: the coding of `HOUSECL` (which value means owning). It is read
   from the codebook at implementation, not guessed.
3. The five implicates and the replicate weights have to be handled, which the
   summary extract documents.

## 3. Income and the necessities basket come from one table, and it is income-ranked

**BLS Consumer Expenditure Survey, Table 1101 (quintiles) and Table 1110
(deciles).** Both carry `Income before taxes` in the same table as expenditure,
so the two quantities the model needs share a denominator and a unit of
observation. Categories verified present: `Food at home`, `Shelter`,
`Utilities, fuels, and public services`, `Healthcare`,
`Gasoline, other fuels, and motor oil`, `Public and other transportation`.

- Latest reference year **2024**, released **2025-12-19**. Reference year 2025 is
  scheduled for 2026-10-29.
- Format: **xlsx from reference year 2023 onward**; the PDF route stops at 2022
  (verified: the 2023 and 2024 PDFs return 404). URL pattern carries the year, so
  past vintages are re-fetchable.
- Verified level, 2024: average income before taxes $104,207; average annual
  expenditure $78,535; by quintile, lowest $35,046 and highest $150,342.
  Cross-checked against FRED `CXUTOTALEXPLB0102M` = 35,046 for the lowest
  quintile.

**One caveat that must travel with any 2025 comparison**: CEX data could not be
collected in October and November 2025 because of the federal shutdown. The Diary
survey doubles the September and December 2025 weights to stand in. A 2025
reference year is therefore not comparable to earlier years without a footnote.

## 4. The ranking mismatch, which is the real finding

**The model's population is ranked by net worth. Income and the necessities
basket are published only by income rank. The two rankings are not the same
households.**

This was checked rather than assumed:

- CEX publishes nothing by wealth, and the BLS FAQ points users to the SCF for
  wealth while stating that its own asset and liability data "are not as reliable
  as the expenditure data".
- The SCF has `NETWORTH` and collects **food at home** and **rent**, and does not
  collect utilities, healthcare or commuting spending. It cannot supply the
  basket.
- The **PSID** is the only public micro source carrying both wealth and all four
  necessity components (food, housing including utilities, healthcare,
  transport). It is biennial, and its expenditure module covers about 72% of the
  CE definition of outlays.
- Re-ranking CEX microdata by wealth is possible on paper and should not be done:
  the asset variables are collected only in the fourth interview, there is no
  stock variable for non-financial assets, and BLS's own research paper states
  the imputation of assets and liabilities is "currently under investigation"
  while income and expenditure imputation is settled.

**How large is the mismatch.** The only rank correlation this check could verify
is Kennickell (1999) on the 1995 SCF: Spearman correlation between income and net
worth **0.76**, Pearson rank correlations 0.71 to 0.85 depending on the income
measure, with Kennickell's own conclusion that "the relationship is not strong".
That is a thirty-year-old vintage and is cited as such.

A current and sharper reading comes from the SCF 2022 Bulletin Table 2, net worth
by **usual income** percentile, thousands of 2022 dollars:

| income percentile | median net worth | mean net worth |
|---|---|---|
| `<20` | 14.0 | 129.7 |
| `20-39.9` | 71.0 | 218.7 |
| `40-59.9` | 159.3 | 385.4 |
| `60-79.9` | 307.2 | 636.8 |
| `80-89.9` | 747.0 | 1,264.7 |
| `90-100` | 2,556.2 | 6,629.6 |

**The lowest income group's mean net worth, 129.7, exceeds the second group's
median, 71.0.** The bottom of the income ranking contains a substantial
population of high-net-worth households, retired or temporarily low-earning. The
mismatch is therefore worst at the tails, and the tails are exactly where this
stage lives: the bottom 50% carries the consumer credit and the top 1% is a
single household in the model.

### What to do about it

Three routes, and the choice belongs to the pre-registration rather than to this
check.

**(A) Assign income-ranked inputs to wealth-ranked strata, disclose, and register
the mismatch as an arm.** The main arm assigns CEX quintile *k* to the wealth
stratum of matching rank. A second arm permutes the assignment consistently with
a rank correlation of 0.76 and re-runs every gated criterion. Whether any verdict
flips is then a measured quantity rather than an assumption. This is the cheapest
route and it converts an unavoidable mismatch into a sensitivity.

**(B) Rank the model population by income throughout.** The mismatch does not
disappear, it moves: the obligation shares from the DFA are wealth-ranked, and
they are the input the K shape depends on most.

**(C) Build the population from PSID**, which carries wealth and all four
necessity components for the same households. It costs the DFA link, a biennial
frequency, and about 28% of the CE outlay definition.

**None of the three is free, and there is no fourth.** No published source pairs
a consumption basket with a net worth ranking.

## 5. What this check changes in the model

1. **`liabilities_to_consumer_credit` should be removed as an input**, replaced by
   the DFA's own consumer credit and home mortgage shares per wealth group. The
   residual it currently computes carries a 12.4% aggregate that belongs to
   neither leg.
2. **`homeownership_by_stratum` requires a computation**, not a lookup, and it
   arrives at a 2022 vintage while the rest of the stage is 2024 to 2026.
3. **`income_by_stratum` and `necessities_by_stratum` come from one CEX table
   each**, which keeps their denominators consistent with each other, and both
   carry the ranking mismatch of §4.
4. **The fetcher must refuse an unresolved series identifier** rather than
   silently dropping a group, since three of the four DFA group identifiers are
   unverified at the time of writing.

## 6. Verdict

**Proceed, with the debt split read from the DFA rather than computed as a
residual, and with the ranking mismatch registered as an arm rather than
absorbed.**

Two of the four inputs are clean once the right series are read. One requires a
small computation from public microdata at an older vintage. One is unavailable
in the form the model wants and is available only under a different ranking,
which is a property of what statistical agencies publish rather than a defect in
the design: wealth is measured by one survey and consumption by another, and
nobody publishes the cross.
