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

## Stage B13 and B18: the CME capture, and the four addresses every scan needs

`data/raw/b13/dc3-glbx-ab-dedup-20230717T133000.pcap.zst`, 6.8 GB, the A and B
feeds already de-duplicated against each other. Instrument definitions come from
`dc3-glbx-a-20230716T110000.pcap.zst`, 30 MB, captured the previous day.

**Every scan over this capture takes a `--groups` list, and it is four addresses,
not two.** Channels 382 and 386 each publish on an A feed and a B feed:

    224.0.31.130:14382    channel 382, feed A
    224.0.32.130:15382    channel 382, feed B
    224.0.31.134:14386    channel 386, feed A
    224.0.32.134:15386    channel 386, feed B

**The capture is de-duplicated across the two feeds, so each one still carries
packets the other does not.** Passing only the A addresses runs to completion,
resolves every instrument, writes a well-formed file, and silently drops **0.85%**
of the packets: on a floor-2000 run that moves the row count of **259 of 295**
spreads. Nothing in the output says so; it was caught by comparing against an
earlier run field by field.

The port's last three digits are the channel number, which is why the A addresses
can be recovered from a traffic survey of the capture and the B addresses cannot:
a survey lists both, and nothing in it says the two belong together.

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
on disk is either wholly there or absent. Both hashes are still recorded, because a guard that cries on every run is as
useless as one that never cries.

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

## Bolivia

Opened 2026-08-19 as B6's control carrier. **Availability only, nothing measured
yet.** `docs/bolivia_availability.md` carries the check and §6 of it carries the
list of things still to be read from source.

### The regulation

| document | body | date | held |
|---|---|---|---|
| `Resolución Ministerial N° 245` | Ministerio de Economía y Finanzas Públicas | 2026-06-26 | **no**, identity confirmed, articles unread |
| `Resolución de Directorio N° 88/2026` | Banco Central de Bolivia | 2026-06-26 | **no**, four articles quoted from a fetch summary |
| `Decreto Supremo 25870` Art. 20 | Presidencia | pre-existing | **no**, quoted at second hand |
| Aduana Nacional comunicado | Aduana Nacional | `La Paz, Junio de 2026` | **yes** |

`data/raw/bolivia/aduana_comunicado_2026-06_RM245.pdf`, supplied by hand and read
from disk. One page, text layer plus page image. It is the only Bolivian document
this project has actually read, and it does three things: it confirms `RM 245` by
number, date and ministerial character; it fixes `6,96 Bs/USD` as **vigente al
26/06/2026**, which anchors the last day of the peg; and it quotes `Art. 20` of
`D.S. 25870`, under which the customs tax base is struck at the previous week's
closing **venta**, held flat for a week. That last is a priced edge granted to one
agent class and it was not in the design before this file arrived.

**Its own date is not on it.** Signed `La Paz, Junio de 2026` with no day, filename
`19 JUN`, PDF `ModDate` 2026-06-29, and it supersedes a comunicado of 2026-06-27.
It cannot postdate what it supersedes, so `19 JUN` is not its date of issue. Cited
by body and subject, never by filename.

### The series, found and not yet pulled

| source | what it gives | from | terms |
|---|---|---|---|
| `bcb.gob.bo/tiposDeCambioHistorico/xls.php?anio=YYYY` | official, **compra and venta**, one file per year | 1940 | public |
| `bcb.gob.bo/tco_reporte_detalle_historico.php` | the microdata behind the TCO: per bank, per rate tier, count and amount. **Compra only** | 2026-06-26 | public, CSV export |
| `api.dolarbluebolivia.click/v1/chart/all.csv` | both legs, both sides, 15-minute | 2024-07-21 | attribution `Powered by dolarbluebolivia.click`; bulk history nominally wants registration |
| `paralelo.bo/api/v1/historical.csv` | **median only**, daily | 2024-01-01 | **CC-BY 4.0**, cite as `paralelo.bo (https://paralelo.bo)` |
| `github.com/mauforonda/dolares` | buy/sell, official, and an amount file; 25,627 commits | to check | to check |

**Nothing here has been downloaded.** Every line of this table came from a
fetching tool that returns a summary rather than the page, which is sound about
what exists and unsound about numbers: one such read reported a value for
31 August 2026, a date that has not happened. **No Bolivian number is recorded in
this project.**

---

## B21: A+H dual listings

### The pair list

`data/raw/b21/aastocks_ah.html`, fetched by `experiments/b21_probe.py` from
`https://www.aastocks.com/en/stocks/market/ah.aspx`. One page, no pagination.
Download date is the file's own mtime; the page is a live snapshot and carries no
date of its own, which is why the probe prints the prices it read rather than
only the counts.

Columns present: company name, Hong Kong code as `NNNNN.HK`, last in HKD, Hong
Kong percent change, mainland code as `NNNNNN.SH` or `NNNNNN.SZ`, last in CNY,
mainland percent change, and a premium column.

**The premium column is not used and must not be.** It is signed the other way
round from this project's convention -- it reads the Hong Kong price against the
mainland one, so it prints negative where the A share is dearer -- and it applies
an exchange rate this file does not disclose. Two different definitions of the
same word in one column is what discipline 18c forbids. **The premium is
recomputed from the two price columns and an exchange rate named here.**

**Two exchange rates are needed and they are different objects.** The onshore
rate and the offshore rate are what the two agent classes respectively face, and
the whole measurement is the difference between the classes. **They may not
share a column.** The probe uses a single constant for the FX leg only because
that leg contributes under 3 basis points to the resolution floor; **the panel
may not.**

### Ticker suffixes, since the mapping is not the obvious one

The page writes Shanghai as `.SH`. Most price sources write it `.SS`. Shenzhen
is `.SZ` in both. A mapping written from the page's own suffix will silently miss
every Shanghai name, and Shanghai is the larger half.

### The Hong Kong tick, which changed twice and is not in any price file

Read from the exchange rulebook, not from data:

| effective | band | tick before | tick after |
|---|---|---|---|
| 2025-08-04 | HKD 10 to 20 | 0.020 | 0.010 |
| 2025-08-04 | HKD 20 to 50 | 0.050 | 0.020 |
| 2026-08-03 | HKD 0.50 to 10 | 0.010 | 0.005 |

Source: HKEX consultation conclusions of December 2024 and the Reduction of
Minimum Spreads page. **The mainland tick did not change and is a flat 0.01 yuan
at every price.** So both dates are a step in the instrument on one leg only.
**A window that spans either date reads that step, and it looks like a structural
change.**

### Files on disk that are not data

`_synth.html.synthtest` and `_synth_bad.html.partial` are the synthetic pages the
parser was unit-tested on before anything was fetched. They are kept rather than
removed, under the rule that nothing under `data/` is deleted. The loader ignores
them: it reads one named path and nothing else.

### What the price column carries, settled by 373 split events

**The saved `Close` is split-adjusted and dividend-unadjusted.** That is exactly
the treatment this stage needs, and it is what the files carry.

The evidence is `--splits`, which prints the one-day price step beside every
split event on disk. **The step sits at one at every event, while the reported
split factor runs from 0.1 to 5.0:**

| split factor | events | observed step |
|---|---|---|
| 0.100 (a one-for-ten consolidation) | 4 | 1.000 to 1.002 |
| 1.100 to 1.300 | many | around 1.00 |
| 2.000 | several | 0.944 to 1.012 |
| 3.000 | 7 | 0.835 to 1.008 |
| 3.800 | 1 | 1.091 |
| 5.000 | 1 | 0.847 |

A price that does not move on a five-for-one split has already had the split
taken out of it. **373 events, no step at any of them.**

`--adjcheck` gives the other half: on `0168.HK` at the start of 2015,
`auto_adjust=False` returns `Close = 52.4500` against `Adj Close = 39.9224`, and
`auto_adjust=True` returns `39.9224`. The gap between the two is dividends, and
`Close` is on the near side of it.

**So the columns are already right for the two opposite requirements.**

- A **split** is simultaneous on the two legs by charter. It has to be out of the
  price, or the ratio of the two legs jumps by the whole factor on one day. **It
  is out.**
- A **dividend** is not simultaneous: the legs go ex on different dates and are
  taxed differently. Taking it out would **invent** a premium move on each leg's
  own ex-date. **It is still in.**

The `Stock Splits` and `Dividends` columns are kept anyway, and a file saved
without `Stock Splits` is refused and refetched, because without them nothing on
disk can be used to check this again.

### Two statements this file carried for an hour, and what overturned them

Written here rather than left as a strikethrough, because a machine reading this
file cannot see a line through text and would take both versions as live.

**Withdrawn: "the saved `Close` is the raw close".** It is raw of dividends and
not of splits. `--adjcheck` alone cannot tell the two apart, because the ticker
it sampled had a dividend and no split in the window.

**Withdrawn: "with a raw close, splits are not adjusted away, and the ratios just
under the threshold are the size an ordinary bonus issue has".** The run of
`2.89, 2.17, 2.17, 2.02, 2.01, 1.96, 1.94` is not a population of unadjusted
splits. Every split on disk shows a step of one, so those steps are something
else and remain unexplained; they are under the cut and stay in.

**What overturned both was printing the object.** The step scan compared a number
against a threshold and produced a plausible story either way. The split report
put the reported factor and the observed step side by side, and one look settled
it. **The first version of that report also carried a threshold, and it was
broken in a way worth recording**: it tested `|step / factor - 1| < 0.25`, which
at a step of one passes for factors of 1.1, 1.2 and 1.3 and fails for 1.5, 2.0
and 3.0. It reported 122 matches against 251 mismatches where there was a single
population, sorted in two by the size of the split rather than by anything about
the data. That threshold is gone.

### The offshore exchange rate, and why the panel starts in 2013

`data/fetch_ah_panel.py --fx` tried five candidates. **Only one returns a
series:**

| candidate | rows | range |
|---|---|---|
| `CNH=X` | 1 | one day |
| `USDCNH=X` | 1 | one day |
| **`CNH=F`** | **3,293** | **2013-02-11 onward** |
| `CNHUSD=X` | 1 | one day |
| `USDCNH` | - | not found |

Three things about `CNH=F` that have to travel with it.

1. **It is a futures series, not a spot rate.** It carries basis. That is
   immaterial to the resolution floor, where the exchange-rate leg contributes
   under three basis points, and it is **not** immaterial to a premium computed
   from it. It may not be described as spot.
2. **Coverage begins 2013-02-11, and the missing years are not a gap.** The
   offshore market itself dates from 2010, so there is no offshore rate to be
   missing before then. **Every dated event in this stage falls inside the
   coverage**: both Connect launches, 2014-11-17 and 2016-12-05, and both tick
   reductions, 2025-08-04 and 2026-08-03.
3. **The onshore rate may never stand in for it.** The difference between the two
   rates is the difference between the two classes, and that difference is the
   measurement. A run that cannot obtain the offshore leg has not obtained a
   worse version of the panel; it has not obtained the index half at all.

**The panel therefore starts 2013-02-11** for anything that needs the offshore
leg, which is everything with a class index in it. The price files themselves
reach back to 2006 and are kept whole.

### The H-leg dividend column carries two conventions, and where they part

**Before 2014 the vendor's H-leg dividend is the A-leg dividend times a fixed
1.166**, whatever the exchange rate was doing. Over the same span the measured
HKD-per-CNY rate ran from 0.973 to 1.267, so the constant is not a rate. From
2014 it stops: the share of matched pairs sitting on it exactly falls from 78.1%
in 2013 to 5.6% in 2014, and stays in low single figures after.

This is discipline 18c's case exactly, two conventions in one column, and the
column had been read as one. The older convention is rebuilt from the A-leg
amount and the rate on the A-leg ex-date, both already on disk, by
`experiments/b21_div_align.py --write`.

**The residual pins after 2014 are not survivals of the old convention.** They
cluster in the years the true rate crossed 1.166 (2016 at 17.1%, 2022 at 6.3%),
where a real conversion and the stale constant are the same number. Those are
false positives and they cost nothing by construction: the flag can only fire at
1.166, so where the conversion was real the rate was 1.166 and the rebuilt amount
is the amount. Measured, the rebuild moves the amount by 0.4% in 2016 and 0.5% in
2022, against 16.6% in 2006 and 8.7% in 2013. **The error the flag can introduce
is bounded by the same distance that makes it detectable.**

**Effect on the class index: one tenth of a basis point on the H-leg median**
(30.4 to 30.5) and no change to any coefficient of the known-answer arm. That the
arm does not move is not luck. Its ratio carries the same yield above and below
and they cancel to first order, which is why the arm was chosen to sit on a
statutory rate rather than an estimated one.

#### Matching the two legs, and why there is no tolerance band in it

Pairing a payment on one leg with its partner on the other cannot be done by
calendar year. Anhui Expressway pays H holders two to three months before A
holders, and in 2006 the A leg carries two payments to the H leg's one.

Nearest-date is also wrong, and its failure is not a mislabelled row. It hands
the single 2006 H payment to the March A payment at an implied 0.901, and the H
payment's real partner is the July one at exactly 1.166. **The wrong match steals
the payment from the pair that needed rebuilding**, so the cost is a dropped
correction rather than a bad ratio.

Three tolerance bands were tried before the matching rule was looked at: a fixed
0.90 to 1.40, then eight per cent against the measured rate, then a percentile of
the drift the rate itself shows over the gap. **The third one is what settled the
question, by failing usefully.** Sorted, the excess of the implied ratio beyond
the range the rate actually took runs

    0.013  0.015  0.020  0.027  0.035  0.046  0.059  0.082  0.110  0.124  0.187

and on up to 9.14 without a break. A continuous tail has no place to cut, so
every cut would have been the analyst's rather than the data's, which is what
discipline 11 forbids.

What replaced all three is an ordering, not a threshold. Candidates are scored by
how near the implied ratio comes to something a ratio between these legs can be,
either the constant or the range the rate took over the span, and the
best-scoring pair in the company is settled first. Anhui's July pair scores zero
and leaves the pool before the March candidate at 0.901 is considered at all.
**No pair is dropped for its score**; the score is a column in
`data/cache/b21_dividends_paired.csv` and a reading that needs a clean subset
cuts it itself. The one flag that decides anything, the rebuild, is an exact
match on a constant.

Yield: 1,843 pairs over 164 companies, 68.9% scoring exactly zero, 765 A-leg and
399 H-leg payments left unpartnered and reported rather than folded into a year.

#### One direction error inside this, worth its own line

`fx_daily` first returned CNY per HKD and left each caller to invert it. Of the
two callers one did and one did not, so the test compared a HKD-per-CNY ratio
against a CNY-per-HKD rate and rejected 1,515 correct pairs out of 1,840. Both
spellings are defensible and that is the whole problem: nothing in a program can
tell which way a bare float points. **The direction now lives in one function
with a name in it and is inverted nowhere else.** Same shape as discipline 22.

#### The two legs do not carry the same splits, and the dividend column is adjusted for them

The saved dividend is divided by every split that came after it. **The two legs
of a dual listing do not always carry the same splits**, so the ratio of the two
saved amounts is the ratio the company declared times the ratio of the two
adjustment factors, and nothing in either file says so.

18 of 1,843 pairs have legs whose factors differ. Multiplying each amount back by
its own factor, so that the comparison is between declared amounts, moves 17 of
the 18 nearer the constant and one further. **Eight land on 1.166 exactly**, and
an exact landing on a sharp target is not something a wrong correction does by
luck: Shanghai Petrochemical reads 1.749 uncorrected across six years, which is
1.166 times the 1.5 its A leg carries and its H leg does not.

**Within one leg this cancels and cannot matter.** The class index divides a
dividend by a price and the saved price carries the same factor, so it is
invariant by algebra rather than by measurement. The correction is only ever
about comparing the two legs.

**A split on the payment's own day is counted, and this was settled against the
published record rather than assumed.** 307 payments fall on the day of a split,
because a Chinese capitalisation and its cash dividend go ex together, so this is
the ordinary case rather than a boundary one.

The ruler is the declaration itself. A Chinese cash dividend is announced per ten
shares to two or three decimals, so undoing the adjustment correctly lands on
that grid and undoing it wrongly does not. Of the 238 A-leg payments that fall on
a split date, counting the same-day split puts **209 on the grid against 134**.

**An earlier attempt to settle the same question against the 1.166 constant
separated the two conventions by one pair and settled nothing.** A constant that
300 pairs already sit on is not sensitive to a factor of 1.2 in twenty of them;
the declaration grid is, because it is a property of every payment rather than of
a subset. **The weaker test was not wrong, it was blunt**, and the tell was that
it returned 309 against 308 where a real effect was worth eighty.

#### The A-leg dividend column is not always on one adjustment basis

Undoing the adjustment leaves **180 of 2,608 A-leg payments (6.9%) off the
declaration grid, touching 52 of 191 legs**. Those payments are not on a
consistent basis, and the factor required to put them back varies year to year
within one company, so no single missing or spurious split explains them.

**Neither load-bearing reading moves.** Splitting the class index by whether a
leg-year contains an off-grid payment:

| | n | index median | index min | arm ratio median | arm ratio max |
|---|---|---|---|---|---|
| A leg, on the grid | 2,129 | 14.8 bp | 0.1221 | 0.9859 | 0.9999 |
| A leg, off the grid | 168 | 14.4 bp | 0.4081 | 0.9863 | 0.9996 |

**The arm is immune and it is worth saying why**, because the reason was
predicted before the split was run. A wrong factor on the dividend scales the
yield, and the arm reports the observed gap over a prediction that is itself a
function of that same yield. A scaled yield moves a point **along** the curve
rather than off it. This is the second time the arm has been insensitive to a
defect in its own inputs, after the pre-2014 rebuild, and both times the
insensitivity followed from the algebra rather than from luck.

#### ZTE, and what the published record says about which leg is wrong

ZTE's uncorrected ratio reads 2.099 in 2006, 2007 and 2008 alike. Its declared
cash dividends per ten shares are on the public record: **2.5, 1.5, 2.5, 3, 3, 3,
2** for 2006 through 2012, with capitalisations of 4, 3, 5 and 2 per ten shares in
2008, 2009, 2010 and 2011. Testing each leg against those:

| ex-date | declared | factor the A column needs | A leftover | factor the H column needs | H leftover |
|---|---|---|---|---|---|
| 2006-07-14 | 2.50 | 7.0761 | **1.5000** | 3.9315 | 1.0001 |
| 2007-07-27 | 1.50 | 7.0761 | **1.5000** | 3.9316 | 1.0001 |
| 2008-07-10 | 2.50 | 5.0544 | **1.0714** | 2.8083 | 1.0001 |
| 2009-06-05 | 3.00 | 3.3696 | 1.0000 | 2.1602 | 1.0001 |
| 2010-06-24 | 3.00 | 3.8880 | **1.5000** | 1.2623 | **0.8766** |
| 2011-07-07 | 3.00 | 1.4400 | 1.0000 | 1.4047 | 0.9755 |
| 2012-07-18 | 2.00 | 1.2000 | 1.0000 | 1.2001 | 1.0001 |

**The H column reproduces the declarations to one part in ten thousand in five of
the seven years**, using the splits already in its own file and the 1.166
convention. 2011 reads 0.9755 because that is the year the constant gives way to
a real conversion, and 1.166 over the 1.203 the rate stood at is 0.969.

**The A column reproduces them in none of the seven** without an extra factor
that changes from year to year: 1.5, 1.5, 15/14, 1, 1.5, 1, 1. A single missing
split would give one factor in every year before its date and one after. **This
is not that, so the A column for this company is not on one basis.**

**This inverts the assumption the section was written under.** The stale 1.166
column looked like the fabricated one and the native A column like the reliable
one, and the published record says the reverse for this company: the fabricated
column is arithmetically faithful to what was declared, and the native one is
not. **A column being computed rather than reported says nothing about whether it
is right.**

2010 is the one year neither leg reproduces, at 1.5 on the A side and 0.8766 on
the H side, and no product of any split in either file gives either number. It
stays named.

## Stage B9: the Select Sector SPDR creation and redemption transaction fees

**What it is.** The fee schedule the ETF carrier's friction term is built from. It
is not a price series and nothing is fetched; it is two paragraphs of a filed
document, transcribed by hand and quoted verbatim in
`docs/b9_zero_holonomy.md` sections 16.4 and 56.4a.

**Source, and it is one document for both directions.** Select Sector SPDR Trust,
Statement of Additional Information as filed in Post-effective amendment [Rule
485(b)], CIK `0001064641`, accession `0001193125-26-027312`, filed 2026-01-28,
document `d15107d485bpos.htm`. The fees are under `PURCHASE AND REDEMPTION OF
CREATION UNITS`, in the subsections headed `CREATION TRANSACTION FEE` (page 48)
and `REDEMPTION TRANSACTION FEE` (page 49). Read 2026-08-29.

**Two vintages exist and the difference is recorded rather than merged.** Section
16.4 read the creation side from the **supplement dated 2026-06-12**, obtained
through the fund's own document viewer. That supplement is not on EDGAR. Section
56.4a therefore quotes **both** directions from the 2026-01-28 filing above, so
that the two sides being compared come from one vintage. **The creation-side
figures agree exactly across the two vintages**, which is what licenses reading
section 16.4 and section 56.4a together; had they differed, the two sides would
have had to be reported in separate columns under the same rule that separates
Hemlane's delinquency from RentRedi's late-payment rate.

**The figures, both directions.**

| | creation | redemption |
|---|---|---|
| fixed fee per transaction | `$500` | `$500` |
| the one excepted fund (XLC) | `$250` | `$250` |
| additional charge | up to 3x the fixed fee | up to 3x the fixed fee |
| ceiling | `$2,000`, XLC `$1,000` | `$2,000`, XLC `$1,000` |

**What the fee is charged per, which is the trap section 16.4 fell into once.**
Per **transaction**, not per Creation Unit, on both sides. The redemption side
states this in words: *"regardless of the number of Creation Units redeemed in
the transaction."* So a fee expressed as a fraction of one unit's value depends
on how many units were bundled into the order, a quantity nobody publishes. That
is why `f` enters as an interval and not a point.

**Who receives it**, from the `Compensation` paragraph of the same document:
State Street, alongside its unitary custody, sub-administration and transfer
agency fee. Recorded because the third-party-fee objection is about exactly this
recipient.

**A wording asymmetry that does not move a number.** The creation side
parenthesises the additional charge as *"expressed as a percentage of the value
of the Deposit Securities"*; the redemption side carries no such phrase. Both
ceilings are stated as the same dollar amounts, so no reading taken here depends
on it. Recorded for any later stage that reads this schedule for something other
than the ceiling.

## Stage C1: IPCC global warming potentials, every assessment report

`https://raw.githubusercontent.com/openclimatedata/globalwarmingpotentials/d3cb48938de7ec35d2f6a0d8072237e6a0db6ce7/globalwarmingpotentials.csv`,
retrieved 2026-08-27, CC0-1.0, 6,744 bytes, sha256 `9b80412c...2454f36`, 105
species. Pulled by `data/fetch_gwp.py`, which pins the commit rather than
`main` and refuses to write a file that disagrees with the recorded hash. The
manifest is committed at `data/raw/gwp/gwp_manifest.json`; the CSV itself is
not, on the same footing as every other raw file here, and the fetcher rebuilds
it in a second.

Primary sources are named in the CSV's own comment header rather than
paraphrased here: GHG Protocol calculation tools for SAR, AR4 and AR5; IPCC TAR
chapter 6 table 6.7; AR5 chapter 8 supplementary table 8.SM.16 for the
climate-carbon-feedback variant; AR6 chapter 7 supplementary table 7.SM.7.

### What a GWP is, in this stage's terms

A GWP is not a measurement of a gas. It is a **declared conversion**: under
standard `s`, one tonne of species `a` is to be counted as `GWP_s(a)` tonnes of
CO2-equivalent. The declaration is executable, because compliance schemes offset
against it, so it is an exchange rate in the operative sense and not only in the
metaphorical one. That is why this table is a carrier at all.

### Eleven columns are eleven definitional bases, and they never share one

The recording convention above says numbers on different bases must not sit in
one column. This table is the case where that rule is the object under study
rather than a precaution around it, so the bases are enumerated:

| column | horizon | assessment report | what distinguishes it |
|---|---|---|---|
| `SARGWP100` | 100 yr | SAR, 1995 | still the basis under some national inventories |
| `TARGWP100` | 100 yr | TAR, 2001 | |
| `AR4GWP100` | 100 yr | AR4, 2007 | |
| `AR5GWP100` | 100 yr | AR5, 2013 | **without** climate-carbon feedback |
| `AR5CCFGWP100` | 100 yr | AR5, 2013 | **with** climate-carbon feedback |
| `AR6GWP100` | 100 yr | AR6, 2021 | |
| `TARGWP20` | 20 yr | TAR | |
| `AR6GWP20` | 20 yr | AR6 | the basis New York and Maryland legislate on |
| `TARGWP500` | 500 yr | TAR | |
| `AR6GWP500` | 500 yr | AR6 | |
| `AR6GTP100` | 100 yr | AR6 | a **temperature** potential, not a warming one |

The last row is a different quantity and not a variant reading of the same one.
It is kept in the file because it is in the upstream table, and C1 excludes it
from the vintage comparison for that reason.

The first six are the ones that matter for the stage's main reading: same gas,
same 100-year horizon, six published numbers. `AR5GWP100` and `AR5CCFGWP100` are
the sharpest pair, because they are the same report.

### What this file does not supply

Which declarations are mutually redeemable. Registry acceptance lists,
compliance-scheme eligibility, linkage agreements and transfer haircuts decide
whether a loop between two standards can be walked, and they are policy
documents rather than a dataset. C1's second half reads them separately, and
nothing here is evidence about them.

## Stage C3: provincial admission cutoffs

**The stage opened on 2026-08-27 from a third route, and the account below of
the two that did not work stays as written.** What follows immediately is what
was collected and how; the search that preceded it, and the two routes it ruled
out, begin at *The quantity* and are unchanged. The line in the earlier account
that says what is missing is a source and not a method is superseded by this
one, and only by this one: the parser, the criteria and the exclusions it
describes are the ones that ran.

### The route that worked: the tables as published, not as archived

The provincial authorities publish a filing table once and then let it age off.
The aggregate archives begin around 2020. **What sits between the two is the
press**: the education channel of a general news site carried each province's
table at publication time in July 2015 and kept the article, with the numbers as
markup rather than as an image. One hub page per admission batch links a page
per province, and the hub pages are themselves still served.

**Thirty-four pages are on disk**, listed in `data/gaokao_sources.json` with the
province, year, track and a verification of each. They reduce to a panel by
`data/parse_gaokao_provincial.py`, which writes `data/gaokao_provincial.csv`:
6,386 rows over fifteen provinces in the arts track and fifteen in science,
fourteen in both, one year.

| | |
|---|---|
| pages held | 34, of which 24 more are byte-identical duplicates the loader passes over by content hash |
| provinces yielding a table | 16 for 2015, plus Shanxi and Henan for 2014 |
| pages holding no article body | 5 provinces: Anhui, Hebei, Hubei, Liaoning, and Guangdong in one track |
| pages excluded by their own title | 3: Jiangsu and Hainan supplementary rounds |
| cross-source agreement | Shandong is published by two outlets and they agree on all 80 entries they share, in both tracks |

**Supplementary rounds are excluded by name and the exclusion is printed.** A
supplementary round refills the seats the first round left empty, so a school
that filled in round one is absent from it and a school that did not files at or
near the tier control line. Jiangsu's two arts pages disagree on 26 of the 43
schools they share and the supplementary one puts 15 of them at 342, which was
the control line that year. **They are not two readings of one quantity.** The
test is applied to the clause of the headline that carries the score noun rather
than to the whole string, because a main table's headline can end with a line
announcing that supplementary filing opens on the 21st.

**A machine-supplied list of candidate pages was mostly fabricated and is
recorded as such.** Of 79 candidate addresses obtained that way, none verified;
30 were removed as 404 and the rest failed the content check. Two more were
correctly addressed and mislabelled, being supplementary tables presented as
main ones, which the page titles settled. **The working division is that a
language model supplies names and the fetcher verifies them**, and the names
were useful while the addresses were not.

**Four pipeline faults sat between the pages and the panel, every one silent**,
and they are recorded together as failure mode 87 in `docs/MEASUREMENT.md`: the
same fact was written twice on the object and the weaker statement was read.
The duplicate pages, a two-level table header read as one level, a file name
contradicting its own page title, and a keyword tested against a whole headline
instead of its governing clause. **Each produced output in a plausible range**,
and one of them would have made the two-track replication criterion pass at one
hundred percent by construction.

**The per-university route recorded below is kept and is not needed.** Its
output, `data/gaokao_cutoffs.csv`, holds Tsinghua's 181 rows over 31 provinces
for 2014 to 2016 and is an independent reading of the same quantity for one
institution, so it remains available as a cross-check on any province whose
provincial table is later disputed.

---

### The search, and the two routes that did not open it


**The quantity.** One admission cutoff per university per province per year, in
the era when a university had exactly one: subject-divided tracks and separate
undergraduate batches, roughly through 2016 depending on province. **No rank and
no normalisation are needed.** The criterion compares the ordering of two
universities inside one province against their ordering inside another, so any
order-preserving per-province transformation cancels, and that is what makes
"a point costs more effort in one province" cancel with it.

**Why the pre-reform era rather than the recent one.** After the reform a
university does not have one cutoff per province, it has one per subject group.
Representing it by the minimum across its groups is biased in a way that
manufactures the finding: an institution offering twelve groups has more
chances at a low minimum than one offering two, so reversals would appear
between institutions of different sizes for a reason that has nothing to do
with the question. The earlier regime has no such degree of freedom, and it has
every province on one footing in the same year.

**What was found, 2026-08-27.**

| source | reachable | what it carries |
|---|---|---|
| `eol.cn` rank-table channel | yes, 200 to a plain request | 2026 only; tables published as CMS images, no numeric markup |
| `eol.cn` score-line channel | yes | 2020 to 2026; nothing earlier |
| `gaokao.eol.cn` provincial channels | yes | nine links dated before 2018, all editorial prose, no tables and no attachments |
| `gaokao.cn` and its static bucket | no | 403 to a scripted request, which is a bot control and is left alone |
| `gaokao.chsi.com.cn` | no | 412 |
| provincial authorities, five sampled | three of five | Jiangsu and Henan serve cutoff tables as PDF attachments; Hebei resets the connection; Hunan fails the TLS handshake |

**Why this is not opened.** The aggregate archive begins around 2020, which is
after the era the quantity is defined in, so the remaining route is one
authority at a time for material roughly a decade old. **Coverage loss on that
route is quadratic in effect, not linear**: the criterion is a comparison of one
pair of universities across one pair of provinces, so a province that cannot be
retrieved removes every pair involving it rather than one observation. Two of
five authorities already refuse a plain connection on their current pages, and
the gaps would concentrate in those provinces rather than spread.

**A source was then found, by inverting who is asked.** The panel was being
sought from the thirty-one provincial authorities, one table per province per
year. The other holder of the same numbers is each **university**, which
publishes its own cutoffs by province and year on its admissions site and has a
standing reason to keep that archive. That turns thirty-one large sources, two
of five refusing a plain connection, into a hundred small independent ones.

**Verified 2026-08-27, three sampled.** Tsinghua serves it: the index at
`join-tsinghua.edu.cn/xxgk/lnlqfsx.htm` links a page per year back to **2009**,
and the 2016 page carries **31 provinces, science and arts split, batch
identified, as selectable text** (Anhui 682/644, Beijing 680/679, Fujian
668/630, Gansu 671/618, Guangdong 671/631). **Every field the design needs is
there and 2009 to 2016 is entirely inside the window where a university has one
cutoff per province.** Peking University's index at
`bkzs.pku.edu.cn/xxgk/lqfsx/index.htm` returns metadata only, its content being
rendered client-side. Shanghai Jiao Tong serves its archive from a query-string
column view of another shape.

**So the route works and is not uniform: one of three sampled is a plain fetch.**
That is the honest ratio to plan against, and it does not decide the stage,
because the criterion needs enough universities to form pairs rather than a
particular list. Tsinghua alone supplies 31 provinces across 8 pre-reform years,
and a few dozen institutions on the same footing give several hundred university
pairs. **The collection rule is therefore to take the ones that serve text and
stop when the count of reversals stops moving**, not to complete a roster.

**Pilot run on Tsinghua, 2026-08-27, and the pipeline closes end to end.**
The index links eight pre-reform years. Three of them, 2014 to 2016, carry the
figures as text in the page: a bracketed section per admission channel, and
inside the general first-batch one a line per province reading
`province: science NNN; arts NNN`. Parsed, they give **181 rows across 31
provinces and both tracks**, and the 2016 values agree character for character
with an independent reading of the live page. The table ships as
`data/gaokao_cutoffs.csv`.

**Three things the pages do that a parser written from a description would miss,
each found by reading the saved file rather than the site.** The section title
is `一批录取分数线` in 2014 and 2015 and `一批统招录取分数线` in 2016, so it is
matched on two substrings and not on a string. On the 2015 page that title also
appears inside a `meta` description, so the head is dropped before the scan or
the first hit carries no data. And a province line carries other channels
inline, `安徽：理科689分；文科675分；理科定向683分`, so the score pattern requires
the digits to follow the track label immediately, which keeps directed and
military places out.

**The earlier years are a different quantity and are excluded rather than
folded in.** 2009 to 2013 hang their figures off a workbook, and that workbook
is by major, giving highest, lowest and mean per major per province. A minimum
over majors approximates an institution's lowest admitted score, which is not
the cutoff at which files are released. Two quantities, so not one column.

**Extending the roster is where this stops, and the sample says why.** Six
institutions of the same tier were checked, and one of them serves what this
needs.

| institution | outcome |
|---|---|
| Tsinghua | **serves it**: eight pre-reform years indexed, three of them as text in the page |
| Peking | index renders client-side; the fetched document carries metadata only |
| Shanghai Jiao Tong | archive served from a query-string column view of another shape |
| Zhejiang | archive holds three years, 2023 to 2025, all after the reform |
| Science and Technology of China | index redirects to a second application that loads its figures by script |
| Nanjing | archive served from a single-page application path |

**The failures are structural rather than incidental**: a script-rendered
archive and a three-year retention window are both properties of how a site is
built and kept, so sampling further institutions would not be expected to
improve the ratio much. **Tsinghua is the exception here and not the template**,
and the plan of one page per university does not hold at the scale the criterion
needs.

**One institution yields no pairs at all.** The criterion compares the ordering
of two universities inside one province against their ordering inside another,
so a single institution produces a table and no reading. **The stage needs a
second source before it produces anything, and that is the binding constraint,
not the volume of rows.**

**Third-party compilations carry the same panel and one of them was checked.**
A per-school, per-province historical view exists on a consumer site, and
Tsinghua's own three parsed years would have served as a calibration key: a
compilation that reproduces them character for character could then be trusted
for institutions whose own sites do not serve their archives. That check was not
completed, because the page is behind a puzzle verification, and **access
controls of that kind are not worked around here**.

**So the hold is unchanged in kind and better specified.** What opens the stage
is a second and third institution whose own site serves pre-reform per-province
cutoffs as text, or a compilation obtained without circumventing an access
control, which Tsinghua's 181 parsed rows can then verify before anything is
built on it. **The parser, the criteria and the exclusions are written and
tested**, so what is missing is a source and not a method.

**Superseded 2026-08-27 by the route recorded at the head of this section.** The
panel came from the contemporaneous press rather than from a second institution
or a compilation, and no access control was circumvented to get it. The sentence
above about what was missing was right about the method and wrong about where
the source would be found: it was looking at who holds the numbers now, and the
numbers were published once, in public, and kept by whoever reported them.

## Depositary receipts and their home lines: an availability probe, nothing bought

`data/fetch_adr_availability.py`, written 2026-08-27, **not yet run**: the two
machines this session had reach the price source through a tunnel that returns
`403`, so the probe has to run where the rest of the panel was fetched.

**The question it answers is one question.** Does the price source already in use
for the A and H panel carry both legs of a depositary-receipt pair, over what
span, with dividends exposed. Thirty-two pairs are declared in the file, one or
two per treaty country, each an ordinary receipt against its home line at
London, Zurich, Copenhagen, Frankfurt, Paris, Amsterdam, Tokyo, Madrid, Milan,
Sao Paulo, Mumbai, Sydney, Toronto, Oslo and Seoul.

**Why the pair is chosen this way.** Both holders in the class pair are of the
same country, so they face one treaty rate and **the statutory term is exactly
zero by construction rather than by subtracting two numbers**. What is left in
the square is the return difference between two listings of one claim, which
arbitrage bounds by the published conversion cost on an interconvertible pair
and does not bound at all on A against H.

**Resumable and non-destructive.** Each ticker caches under
`data/raw/adr_probe/` and a cached file is not refetched. An unparseable payload
is renamed with a `.partial` suffix and left in place, so a rerun sees it.
Five years of daily bars for sixty-four tickers, and it buys nothing.
