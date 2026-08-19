# Data sources

Raw data is not redistributed. This file records where each file came from, when
it was retrieved, and on what definitional basis, so that a number can be traced
to a release rather than to this repository.

Stage A0 uses no *fitted* data, but it does use published levels, substituted
directly and not estimated from any target. Those are listed first. The tiers
below are what later stages need.

## In use now (stage A0, DFA-calibrated preset)

| figure | value | series | retrieved |
|---|---|---|---|
| top 1% share of net worth | 31.6% | `WFRBST01134` | 2026-08-08 |
| 90th-99th percentile share | 36.3% | `WFRBSN09161` | 2026-08-08 |
| 50th-90th percentile share | 29.6% | `WFRBSN40188` | 2026-08-08 |
| bottom 50% share | 2.5% | `WFRBSB50215` | 2026-08-08 |

Vintage Q1 2026, FRED release 453, table "Shares of Wealth by Wealth Percentile
Groups". Definitional basis: share of **total net worth**, not total assets. The
total-assets series give a materially different top-1% figure (28.8%,
`WFRBST01108`) and the two must not be mixed.

Spending propensities: Fagereng, Holm & Natvik, "MPC Heterogeneity and Household
Balance Sheets", AEJ: Macroeconomics, October 2021. Norwegian lottery wins in
administrative panel data. Their estimand is the MPC out of a transitory income
shock; the model's parameter is a spending rate out of holdings. These are not
the same quantity, so what is taken from the paper is the range and the ordering,
not the values. Recorded as a caveat in `calibration.py` as well as here.

Recorded for stage A1, not yet used:

| figure | value | series |
|---|---|---|
| bottom 50% share of consumer credit | 51.8% | `WFRBSB50211` |
| bottom 50% share of total liabilities | 30.4% | `WFRBSB50208` |

## Tier 1 — required for A1, A2 and B2

| dataset | use | source |
|---|---|---|
| Fed Distributional Financial Accounts, quarterly wealth shares | proxy for the dormant claim pool | `federalreserve.gov/releases/z1/dataviz/dfa` |
| NY Fed Household Debt and Credit, quarterly underlying-data workbook | A1 calibration. **The split this row originally asked for does not exist in public form; corrected below** | `newyorkfed.org/microeconomics/hhdc` |
| Fed Z.1 Financial Accounts, by sector | B2 graph; A3 sector accounts | `federalreserve.gov/releases/z1` |
| BEA Input-Output Use Tables | B2 primary graph; empirical anchor for the A2 adjacency matrix | `bea.gov/industry/input-output-accounts-data` |
| M2, NBER recession dates | timeline alignment | FRED |

### NY Fed HHDC, corrected 2026-08-13

The row above originally read:

> NY Fed Household Debt and Credit, **split by product and by income quartile /
> credit score** | A1 calibration. The split is the point: the K-shape lives in
> the disaggregation, not the totals

The first half of that is retrievable and the second half is not.
[`../docs/a1_availability.md`](../docs/a1_availability.md) section 4 inventories
the workbook: thirty-six data sheets, on which delinquency is crossed with
**age** (four products, flow measure only, bands 18-29 through 70+), with
**state**, and with nothing else. Credit score appears only at origination and is
never crossed with delinquency. **Income quartile appears nowhere.** The
Philadelphia Fed's Consumer Credit Explorer does cross delinquency with age,
credit score and neighbourhood income on the same underlying panel, and states
that vendor restrictions prevent it from supplying any series in spreadsheet
form. The panel itself, the New York Fed Consumer Credit Panel, is limited by
contract to Federal Reserve System researchers and their coauthors, so there is
no second public route to the same disaggregation.

What stands in for the missing split: the holdings side is already stratified and
already recorded above (bottom 50% holding 51.8% of consumer credit against 2.5%
of net worth), and the K-shape criterion is a contrast **across products**, which
Page 12 supports with no stratification at all. One frozen reading by credit tier
exists for the subprime rung and is recorded in the availability check.

| vintage | what A1 scores against | value |
|---|---|---|
| 2026Q1, Page 12 | credit card, share of balance 90+ days late | 13.12% |
| 2026Q1, Page 12 | auto, share of balance 90+ days late | 5.60% |

**Both are stock figures, and the workbook also publishes a flow.** For the same
quarter the flow table, Page 14, reads 7.10% and 2.97%. The pre-registration
declares which quantity the model emits before either column is quoted; the
factor between them is close to two.

### Retrieval

`data/fetch_hhdc.py` retrieves one vintage to
`data/raw/hhd_c_report_<vintage>.xlsx`, validates it **before** it takes that
name, and merges an entry into `data/raw/hhdc_manifest.json` without dropping any
other vintage. `--check` classifies the cache and fetches nothing. A file that
fails validation is renamed with an `.expired` suffix and kept.

The vintage is pinned in `src/monetary_topology/hhdc.py`, because A1's targets
were written against 2026Q1 and the 2026Q2 workbook was released 2026-08-11. The
URL pattern resolves for past quarters, so a pinned vintage stays re-fetchable
rather than merely archived.

Three properties of this source cost a reader its correctness if ignored, and
each has a case in `tests/test_hhdc.py`:

- **Sheet names are page numbers in the PDF report and move between quarters.**
  The sheet is located by a substring of its own title row.
- **The contents page and the sheets disagree on titles.** The contents page
  calls the flow table `Flow into Serious Delinquency (90+) by Loan Type`; that
  sheet's own title row reads `New Seriously Delinquent* Balances by Loan Type`.
- **The two tables do not share a column order.** Page 12 runs mortgage, HELOC,
  auto, card, student, other, all; Page 14 runs auto, card, mortgage, HELOC,
  student, other, all. Columns are keyed by header string, never by position.

The reader also keeps a dated row whose cells are partly blank rather than
dropping it: the flow table carries no student loan figure for its earliest
quarters, and discarding those rows would shorten the series by coverage that is
real.

## Not data, parameters

Price-change frequency estimates (Nakamura & Steinsson; Bils & Klenow) are used
as **inputs** at stage A3, not re-measured. This removes an entire sub-project.

## Tier 1.5 — adjacency sources

The framework's own methodological conclusion is that a quantity does not
establish a death zone: one must specify who can trade with whom. Aggregate time
series cannot supply that. Without one of the following, the A2 and A3 adjacency
matrices are assumption at the load-bearing point.

| dataset | supplies | difficulty |
|---|---|---|
| BEA IO Use Tables | sector-to-sector flows | low |
| Compustat major-customer disclosures (SFAS 131, customers above 10% of revenue) | firm-level customer-supplier edges | medium, subscription |
| FR Y-15 systemic exposure | the graph inside the financial layer | low, public |
| FFIEC / CRA lending by geography and income band | **direct measurement of the coupling edges between layers** | medium |

CRA data deserves particular attention: it records bank lending by geography and
income level, which is the most direct available observation of how sparse the
downward edges are and where they terminate. The framework's two-layer structure
has so far been argued qualitatively.

## Tier 2 — discriminating tests, stage A3

| dataset | tests what | note |
|---|---|---|
| 13F plus Z.1 sector acquisition timing | who buys inside the lag window | this is what separates the mechanism from `r > g`, which makes no timing prediction |
| cross-country wage indexation (Brazil, Israel, high-inflation periods) | economies with high indexation should gain less concentration from monetary expansion | the only cross-country discriminator available |
| Consumer Expenditure Survey by income decile | the consuming-power basket | |
| Census Business Dynamics Statistics | firm size distribution (entry ticket) | |

## Tier B2 — the effective-price loops

Pre-registered in [`../docs/b2_measurement.md`](../docs/b2_measurement.md). Nothing
here is retrieved until that document is final, and the sample is fixed before any
loop sum is computed.

| dataset | supplies | note |
|---|---|---|
| **HMDA modified LAR** | `rate_spread` (APR minus APOR at rate-set date), census tract, lien status, loan purpose, **occupancy type**, action taken. Loan level, ~4,800 filers | **Loop A, the logical anchor.** Note what is absent: credit score is redacted, along with 26 other fields, and DTI, loan amount and property value are modified. So this file gives the *dispersion* of terms at fixed position and date and cannot attribute it to credit score |
| **NMDB Outstanding Residential Mortgage Statistics** | distribution of interest rates on outstanding fixed-rate mortgages, quarterly | **The load-bearing series.** Share of outstanding loans below 4% peaked at 65.1% in Q1 2022 and stood at 49.9% in Q1 2026. Roughly half the holders of the same position face materially different terms from the other half, divided by entry date |
| NMDB New Residential Mortgage Statistics | LTV and credit score at origination, by vintage | |
| Freddie Mac PMMS | 30-year fixed contract rate by week, averaged to quarter | the rate available at each vintage |
| FHFA HPI, metro, all-transactions and purchase-only | house price by metro and quarter | purchase-only preferred where both exist |
| Zillow ZORI, ZHVI | imputed rent and price tiers by metro | tier definition where FHFA does not publish tiers |
| ACS 5-year | effective property tax rate by metro | |
| NAIC homeowners premium | insurance by state | |
| state assessment caps | hand-coded, dated, statute cited per row | committed as a table; the only hand-coded input |

Two definitional traps recorded in advance.

**The contract rate on an outstanding loan is not the current market rate**, and
loop B turns entirely on that difference. Any step that substitutes one for the
other destroys the measurement silently.

**Asset tier is not agent class.** An individual landlord buying down-market units
to rent and hold is a high-class agent holding a low-tier asset. Pooling by price
tier averages that landlord together with the household that could reach no higher
tier, which cancels the very distinction being measured. Occupancy type separates
them and every cell is crossed by it.

### Retrieval

`data/fetch_hmda.py` pulls the pre-registered sample from the FFIEC Data Browser
CSV endpoint, one file per metro-year, resumable, writing a manifest that records
every URL, row count and exclusion count. It must be run before
`experiments/b2_loop_a.py`.

Two constraints discovered while probing the API and recorded here rather than in
a comment:

**Send two filters, not five.** Each documented filter works alone; five together
return HTTP 400. Rather than guess which pair the server dislikes, only
`loan_purposes` and `loan_products` are sent, purely to cut the download, and every
other exclusion is applied locally where it is visible and testable.

**`action_taken == 1` is load-bearing, not hygiene.** Purchased loans, action taken
6, report `rate_spread` as NA. The first sample retrieved was almost entirely those
and carried no observable field at all.

**The column is `derived_msa-md`, with a hyphen.** An underscore silently produces
no column rather than an error.

**Query by state, not by metro.** HMDA reports Metropolitan Division codes for
divided CBSAs, so querying New York as 35620 returns zero rows. State codes are
unambiguous, and metro is not a cell key in any case.

**The aggregation endpoint cannot serve this.** Its filter list has no
`occupancy_type` and no `rate_spread`, so the raw CSV endpoint is required and the
statistics are computed locally.

**Loop A's window is 2018 onward, not 2000.** The API serves 2018-2025, and more
importantly HMDA carried rate spread only for higher-priced loans before 2018.
Using earlier years would select precisely the tail this measurement is about. The
longer vintage range in `docs/b2_measurement.md` applies to loop B only.

## Recording convention

Every file added to `data/raw/` gets a row here with: URL, retrieval date, series
identifier, and definitional basis. Figures from different definitional bases are
never placed in the same column. Delinquency data in particular mixes "unpaid" and
"paid late but eventually paid" across providers, and conflating them would
overstate a level.

---

## Stage B3: covered interest parity deviations between government bonds

**This one is different from every other source here and the difference is the
first thing to say: it is a derived series and we did not build it.** Every other
row in this file is a government release we retrieved and filtered ourselves.
This is a research dataset constructed from Bloomberg and Datastream by its
authors, who state that licensing forbids republishing the raw inputs. What is
published is the output plus the ticker list needed to audit it.

| | |
|---|---|
| page | `https://sites.google.com/view/jschreger/CIP` |
| file | `cip_dataset_v4.csv` |
| version | V4, October 2025; V1–V3 archived by the publisher |
| retrieved by | `data/fetch_cip.py`, manifest at `data/raw/cip_manifest.json` |
| coverage | 2000–2025, 10 developed and 18 emerging markets |
| maturities | 3M, 1Y, 2Y, 3Y, 5Y, 10Y, 20Y, 30Y |
| companions retrieved | ticker spreadsheet and data appendix, alongside the data |

**Definitional basis.** `cip_govt` is `y_govt(i,n,t) − ρ(i,n,t) − y_govt(USD,n,t)`
in basis points: the local-currency government bond yield, less the market-implied
forward premium for hedging that currency against the dollar, less the US Treasury
yield at the same maturity. `rho` is that forward premium in percentage points and
`diff_y` the raw yield differential.

**Two definitional bases are published and must never be mixed in one column.**
`cip_govt_ibor` and `cip_govt_sofr` are the same object computed under the IBOR
and the post-reform benchmarks; the publisher fixes a break date per
tenor-currency pair, published in `cip_govt_break_date`. Stage B3 uses `cip_govt`
as the series and the ibor/sofr pair **only** as a noise floor, which is
`b3_cip_slice.md` §4.

**Why a content hash is recorded here and nowhere else in this file.** The other
sources are versioned government endpoints. This one is hosted by a researcher
and V4 replaced V3; a silent republication under an unchanged filename would
parse, carry the completion marker, and be different data. The manifest records
the SHA-256 so that case is visible instead of invisible.

**Citation is required by the publisher**: Du, Keerati and Schreger (2025); Du,
Im and Schreger (2018); Du and Schreger (2016).

---

## Stage B5: Argentina's simultaneous peso-dollar quotes

**The provenance here is the lowest in this file and that is the first thing to
say: four of the seven series are a newspaper's quotes.** Every stage before this
one rested on a government release or, in B3, on a research dataset with a
published construction. Ámbito Financiero is a daily paper. `b5_orphan_prereg.md`
§9.4 puts this admission at the top of the write-up rather than in a footnote,
and the mitigation is that the oficial leg's headline comes from the central
bank, so at least one side of every premium is authoritative.

| | |
|---|---|
| endpoint | `https://mercados.ambito.com/<series>/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>` |
| verified | 2026-08-11 |
| retrieved by | `data/fetch_ambito.py`, manifest at `data/raw/ambito_manifest.json` |
| files | `ambito_<series>_<year>.json`, per-year chunks, resumable |
| window | 2019-09-01 to 2026-06-30, registered in `b5_orphan_prereg.md` §7 |

| series | endpoint path | fields | usable for |
|---|---|---|---|
| oficial | `dolar/oficial` | `Fecha, Compra, Venta` | **cross-check only**, see below |
| blue | `dolar/informal` | `Fecha, Compra, Venta` | headline mid **and** friction |
| MEP | `dolarrava/mep` | `Fecha, Referencia` | headline mid only |
| CCL | **`dolarrava/cl`** | `Fecha, Referencia` | headline mid only |

**The CCL path is `cl` and not `ccl`.** `b5_orphan_availability.md` §7.1 listed
`dolarrava/ccl` with the parenthetical "(same shape)", reasoned from the MEP path
rather than requested. It 404s on every range. Corrected 2026-08-11 after the
first retrieval, and recorded because the parenthetical was the tell: **an
endpoint that was inferred is not a verified endpoint.**

**This endpoint returns intraday snapshots, not a daily series.** A date can
carry between two and nine rows with different values and no timestamps; 385 of
the first run's 5,248 rows were repeat dates. Registered collapse rule
(`b5_orphan_prereg.md` §3.5): **each date is represented by the single row whose
mid is that date's median mid**, lower median on ties, selecting a whole row so
that bid and ask stay paired from one published quote. Median rather than mean
because 21 August 2024 returns `954.12 / 300.76 / 953.17` for one date; median
rather than closing because there are no timestamps to identify a close. **The
raw files keep every snapshot**; the collapse happens on load, and the per-date
row count and log range go into the manifest.

**Definitional basis.** Every value is pesos per dollar. The mid is
**geometric**, `sqrt(Compra · Venta)`, because the claim is stated in logs
(`b5_orphan_prereg.md` §3.4). Dates are `DD/MM/YYYY` and **the decimal separator
is a comma** with periods grouping thousands; the retriever asserts the token
format on every row rather than checking a plausibility band, because a
hundredfold misreading at the 2019 end of the window lands inside any band loose
enough to admit the 2026 end.

**Ámbito's `dolar/oficial` is not the oficial leg, and this is a definitional
distinction not a preference.** It returns e.g. `1071.36 / 1125.54` for 22 April
2025, a gap near five percent, which is a **range across retail bank counters**
and not one dealer's spread. Using it as the friction term would put dispersion
across banks — an agent index — into a quantity defined as one agent's
round-trip cost. Registered split, `b5_orphan_prereg.md` §3.2:

- headline mid for oficial → **BCRA Comunicación A 3500**
- friction term for oficial → **Banco de la Nación Argentina** posted counter rates

**Three series this stage needs are not retrieved yet**: BCRA A 3500, BNA counter
rates, and an `ARS/USDT` P2P mid. Their endpoints were **not verified** by
`b5_orphan_availability.md`, and a retriever written against an unverified
endpoint is first tested on the day the data is needed.

**MEP and CCL have no bid and ask, and that is not a gap in the source.** MEP is
a ratio of two bond prices (`AL30` against `AL30D`), so it has no native
two-sided quote. Consequence: the friction column exists **only** for the
oficial–blue pair. **Constructing a synthetic spread for MEP or CCL from another
series, a lagged quote, or an OHLC range is prohibited** — it fills the gap with
exactly the quantity in dispute (`b4_directed_edges.md` §5.2). Investing.com was
proposed for this and rejected on these grounds.

**Anomalies are recorded and never repaired.** A row whose one-day change in the
log mid exceeds `0.10` is written to the manifest as a `DataAnomaly` and **its
value is not changed and the row is not dropped**. The known instance is
`dolar/oficial` on 23 April 2025, reading `1251.44 / 1333.24` between neighbours
near `1100`. A jump filter cannot separate a composition change from a bad row
from a real liquidity event three weeks into a float, and in this window it fires
on genuine moves, so the threshold's only job is to populate the list that
criterion B5-10 computes the headline with and without.

**No completion marker, unlike `fetch_cip.py`.** A truncated CSV still parses as
a CSV, which is why that script appends a sentinel. A truncated JSON array does
not parse, and the write goes through a temporary file and a rename, so a chunk
on disk is either wholly there or absent. Both hashes are still recorded, for the
reason `PROJECT_PLAN.md` §11.11 gives.

### Background only, and the line between the two categories

**Nothing in this subsection is retrieved, parsed or measured.** These are
citations for the prose that describes the market around the intervention, and
the distinction is the one every research paper makes between its data and its
literature. A criterion may not read them, and no number in `results/` comes from
them. `b5_orphan_prereg.md` §8.3 is where they are used and where the line is
restated at the point of use.

The rule that a third-party series needs an independent referee across the whole
window before it carries anything (`b5_orphan_availability.md` §7.4) governs
**series that enter a measurement**. It does not govern a citation in a
discussion section, and reading it that way would forbid citing the literature at
all.

| publication | what it carries | period | form |
|---|---|---|---|
| BCRA, *Informe de la Evolución del Mercado de Cambios y Balance Cambiario* | monthly report on purchases and sales through the exchange market | to 2026-04 | PDF |
| BCRA, *Anexo estadístico del informe de balance cambiario* | the report's statistical annex | 2003-01 onward, monthly | PDF |
| BCRA, *Estadísticas estandarizadas sobre la Evolución del Mercado de Cambios* | standardised monthly series, disaggregated by sector and by concept | 2003 onward | spreadsheet |

**Cite the central bank, not a newspaper's transcription of it.** Household
dollar purchases circulate in the press as a headline figure; in BCRA's own
terms the line is **Formación de Activos Externos del Sector Privado No
Financiero**, and it is published in the annex above. Taking it from the annex
rather than from a report of the annex costs one lookup and removes an
intermediary.

**There is a second reason to prefer BCRA here specifically.** This stage's
headline already takes the oficial leg from BCRA's A 3500 reference
(`b5_orphan_prereg.md` §3.1). Sourcing the background from the same central bank
means a reviewer does not find authoritative data under the criteria and press
reports under the discussion.

---

## Stage B6-A: the Banco Central de Cuba's own segment table

**The provenance here is the highest in this file and that is the first thing to
say: every agent class comes from the central bank.** B5's difficulty was the
opposite, four of seven series from a newspaper. The cost of that strength is
recorded in `b6_cuba_prereg.md` §4.3: with one publisher there is **no zero
calibration** over the window, because a zero calibration needs one class
collected twice by independent paths and there is only one path.

| | |
|---|---|
| endpoint | `https://api.bc.gob.cu/v1/tasas-de-cambio/historico?fechaInicio=&fechaFin=&codigoMoneda=` |
| verified | 2026-08-12 |
| terms | free, no key, no registration, both ends of the range inclusive |
| retrieved by | `data/fetch_bcc.py`, manifest at `data/raw/bcc_manifest.json` |
| files | `bcc_<currency>.json`, one per currency, whole window in one request |
| window | 2025-12-19 to retrieval, registered in `b6_cuba_prereg.md` §6 |

The response carries three rates per date and nothing else:

| field | segment | who may transact | return leg |
|---|---|---|---|
| `tasaOficial` | I | state enterprises and legal persons, on designated operations | **none** |
| `tasaPublica` | II | natural persons, on the retained fixed schedule | **none** |
| `tasaEspecial` | III | the managed float opened 2025-12-18 | both directions |

### The four questions this file asks of every source

**Which venue.** The central bank's own reference, and for the channel columns
the counters of the banks and CADECA that the bank sets rates for. Not a market.

**Which side of the book.** The API carries a mid only. The nineteen channel
columns in the XLSX export carry a buy, a sell, or one of the two, and **the
spread is an administrative markup rather than a dealer's cost**: it is the base
rate times a fixed constant, published in the bank's own schedule. `b4` §5.1's
sentence about `S + S'` being an agent's round-trip cost does not carry over, and
`b6_cuba_prereg.md` §2.2 says so.

**What aggregation over the day.** None. One value per date, no intraday
snapshots, unlike Ámbito in B5.

**At what hour.** Not published. The one thing known about the timing is
indirect: the euro leg's implied cross tracks the previous European business
day's fixing more closely than the same day's, which is why B6-4 failed on three
of 147 days (§below).

### Five properties of this source that cost something to learn

**The nineteen channel columns are not retrieved.** Each is the base rate times a
constant from the bank's published markup schedule, held as
`cuba_segments.MARKUP_SCHEDULE` and validated against the exports by guard 1:
176 358 exact equalities over 39 files, no departures.

**The publisher truncates and does not round.** Every channel is
`floor(base * k * 1e4) / 1e4`. The base itself is **not** truncated, and the
channel whose multiplier is exactly `1.000` differs from the base in the last
place on 59 of 1 428 rows, which is what says the truncation is the publisher's.

**The export is a complete calendar and the API is not.** The XLSX carries every
day; the API carries only publication days. Extra export rows are forward fills.
**Rows before a currency's first publication are back fills** and are a different
object: they manufacture a value for a day the bank published nothing. The yuan
joined the table on **2025-12-31**, twelve days after everything else, so its
export carries thirteen back-filled rows. Reading them as forward fills produced
a criterion failure that was the reader's, `b6_cuba_prereg.md` §11.

**The export's last row is provisional.** Taken before the day's rate is
published it is a forward fill; taken after, it is the real value. Which one
depends on the minute of the download. Rows at or after the export's own date are
never compared.

**The yen is published `de manera indirecta`**, yen per peso, while the other
twelve are `de forma directa`, pesos per unit. The bank's page carries that
footnote. Registered in `cuba_segments.QUOTATION` and asserted by guard 6 through
the segment ladder, which runs `1/5` for the yen where a direct currency runs
`5`.

### The XLSX export, which is not fetched

The historical export is behind a form rather than a URL, so the 39 files, 13
currencies against 3 segments, are downloaded by hand into
`data/raw/bcc_xlsx/`. Names look like
`tasas-historicas-USD-Segmento-III-2026-08-12.xlsx`; the loader accepts only
names matching `cuba_segments.VALID_XLSX` and **reports what it skipped**, since
"the directory is empty" and "the loader accepts none of these six files" are
different facts.

The export is a **validator, not a daily source**: it checks the markup schedule
and reconciles against the API. Every number the criteria read comes from the
API.

---

## Stage B6-A: the ECB daily euro reference rate

The external referee, and **the only source in stage B6-A that is not the Banco
Central de Cuba**.

| | |
|---|---|
| endpoint | `https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=&endPeriod=&format=csvdata` |
| verified | 2026-08-12 |
| terms | free, no key, no registration |
| retrieved by | `data/fetch_ecb.py`, manifest at `data/raw/ecb_manifest.json` |
| series | US dollar against the euro, fixed at 14:15 CET, business days only |

**The address and the series identifier are two different strings.** SDMX
addresses a series as `/service/data/{flow}/{key}`, so the path carries `EXR`
once and then `D.USD.EUR.SP00.A`; the response's `KEY` column carries the two
joined as `EXR.D.USD.EUR.SP00.A`. Putting the joined form into the path is well
formed, looks right, and returns HTTP 400. Both spellings are held separately in
`cuba_segments` and a test pins the built URL against the verified one.

**What it validates and what it does not.** The source, not the pipeline. It
cannot substitute for the zero calibration this stage does not have. And it is
not a claim that the BCC copies the ECB: the two agree to within a few tenths of
a percent but track no fixed lag, and **B6-4 fails on three of 147 compared
days**, each of them a day the reference itself moved about a percent with the
sign reversed. A one-business-day lag removes all three, which is a diagnostic
and is not the registered comparison.


---

## Stage B6-B: elTOQUE's representative informal exchange rate (Cuba)

| dataset | use | source |
|---|---|---|
| elTOQUE **Tasa Representativa del Mercado Informal**, daily, 2021-01-01 onward | the informal leg of B6-13, B6-14 and B6-15. One median per instrument per requested window | `tasas.eltoque.com/v1/trmi`, bearer JWT |
| CryptoDataDownload **Binance spot daily**, BTCUSDT / TRXUSDT / BNBUSDT | **one reading only**: it fixes the units of elTOQUE's crypto columns. Enters no criterion | `cryptodatadownload.com/cdd/Binance_<PAIR>_d.csv` |

**Attribution is a condition of use, not a courtesy.** elTOQUE's terms require
that it be named as the source of anything obtained through the API, forbid
resale and redistribution, and forbid passing the key to a third party. The
series is therefore **not committed**: `data/raw/` is excluded and only
`data/raw/eltoque_manifest.json` is tracked. The key lives in `.env`, which the
same file excludes.

### What the instrument is, and the four things it will not do

`docs/b6b_eltoque_prereg.md` §2 is the full account. In brief:

1. **One number per instrument, formed from buy and sell offers pooled by the
   publisher.** There is no bid and no ask, so the informal edge carries an index
   part and no friction part, and no criterion certifies a positive cycle through
   it.
2. **One request buys one day.** A window longer than 24 hours is refused with
   `El intervalo de tiempo debe ser menor a 24 horas`.
3. **The response carries no echo of the day it answers for.** Its `date`, `hour`,
   `minutes` and `seconds` are the server clock at the moment of the request, so
   the same day refetched hashes differently and the row key comes from the
   request.
4. **The timestamps are read in Havana time**, which no document states and which
   was established by a refusal: the main pass ran 310 days and then returned
   HTTP 400 on 2021-11-07, a window that is under the cap everywhere except a
   zone whose clocks go back that night.

**The rate limit is not the documented one.** The specification states 60 per
minute with a 10 per second burst cap and adds that a key may carry a different
quota; this key carries **ten requests per 156-second window**, measured, which
is a ten-hour main pass rather than a thirty-five minute one.
`X-RateLimit-Remaining` reported `10` on all fifteen requests of the rate probe
including the three that came back 429, so it is recorded and disbelieved.

### The construction has been through peer review

Pavel Vidal, Carlos Enrique Muñiz Cuza and Abraham Calas Torres, *Using AI in the
Informal Currency Market: Evidence from Cuba*, **Applied Economics**, October
2024, doi:`10.1080/00036846.2024.2416091`. The methodology page states that the
dollar, the euro and MLC use a median with a two-standard-deviation outlier
filter, and that thin currencies use an exponential moving average instead.
**`USDT_TRC20` is named on neither list**; the variance ratios in
`results/b6b_informal.json` come in below one and falling, which is measurement
noise rather than smoothing, so it is read as median-based.

### Retrieval

`data/fetch_eltoque.py`. Resumable by file existence, one file per day under
`data/raw/eltoque/`, two digests per response of which only the one over the
`tasas` object survives a refetch, an empty `tasas` recorded as an empty day and
never filled in either direction, and pacing read from the headers rather than
assumed. 2,056 days plus twelve one-hour sensitivity windows plus twelve replays
of the probe answers written down before any criterion existed.
`data/raw/eltoque_manifest.json` carries every response, the served-instrument
set per day, the five shortened windows and the six short-span days.

### The world crypto prices, and why they are here at all

Downloaded by hand on 2026-08-19, so there is no fetcher and these digests are
the only thing between a swapped file and a silent wrong answer:

| file | rows | span | sha256 |
|---|---|---|---|
| `Binance_BTCUSDT_d.csv` | 3,262 | 2017-08-17 → 2026-08-18 | `49839f18be0d820950ef4dff798123cc799682787274eeceede652b5e2d07150` |
| `Binance_TRXUSDT_d.csv` | 2,964 | 2018-06-11 → 2026-08-18 | `0a314da9663bf3b71c8cfcf90abe4cc6bf380b318d2cde6daf7c1cff5c467dab` |
| `Binance_BNBUSDT_d.csv` | 3,181 | 2017-11-06 → 2026-08-18 | `efb8cfa4af31225580af74be4a6de12555feb5dff2048aebfcae2f72a3710f55` |

Twenty-seven days are missing from all three inside the window, on the same
dates, which is the collector's gap rather than the market's, since these
instruments trade every day. They are left absent.

**They answer one question and then stop.** elTOQUE's `BTC` column sat at 737.75
on 2026-08-18 while a bitcoin was worth 64,725 dollars, so it cannot be pesos per
bitcoin. The median of `BTC / USD` is **0.9930** over 2,027 overlapping days and
the correlation between the daily change in `BTC` and the daily change in the
world bitcoin price is **-0.021**. The column is pesos per dollar of bitcoin, and
the three control instruments are three more claims on a dollar rather than a
placebo against an outside market. Having established that, the price series
enters nothing else.
