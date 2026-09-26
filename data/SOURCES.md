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

**All three files here are this project's own, and that is why all three are
committed.** The quantity underneath is a set of filing scores, and a score is a
fact rather than anyone's text. What sits in these files is the collection and the
arrangement: which pages carry the table, which were fetched, which were thrown out
and on what test, and how the rows were read off two-level headers. **That work is
recorded in this section rather than asserted**, and it is what the files are.

`data/gaokao_sources.json` is the retrieval list: one row per page with its url, the
province, year, track and quantity, and the byte count, row count, headline and
keyword checks each page was verified against.

`data/gaokao_provincial.csv` is the provincial panel, 6,386 rows over sixteen
provinces. The pages were found by working through a news site's education channel
for the July 2015 publication window, one hub page per admission batch, over an
afternoon. **Twenty-four further pages were dropped as byte-identical duplicates by
content hash, five carried no article body, three were excluded by their own
headline as supplementary rounds, and Shandong's two independent outlets agree on
all 80 entries they share in both tracks.** Four silent pipeline faults sat between
the pages and this file, and each is recorded above.

`data/gaokao_cutoffs.csv` is the per-institution reading, 181 rows over 31 provinces
and three years, assembled by working through the examination-board and admissions
pages until the figures were found as text. The three parsing quirks it had to
survive are recorded above. **The individual addresses that run fetched were not
written into the file**; the route was what was recorded.

**Rebuilding the panel from scratch is possible and the way is above**: fetch the 34
urls in the list, keep the files under the `on_disk` names it gives, and run
`data/parse_gaokao_provincial.py`. The checks in the list are what a rebuild should
be compared against, and the exclusions the parser applies are printed in its
output.

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
## B30-5 cross-sectional city panel, and the two sources it stands between

**What is on disk.** `data/b30_5/pages/*.html`, one page per city, fetched
2026-09-01 from the crowdsourced cost-of-living database at numbeo.com, one
request per city with the page cached so a re-run resumes rather than refetches.
`data/b30_5/panel.json` is the parse of those pages. Twelve cities so far, of a
registered thirty-one: the four municipalities and every provincial and
autonomous-region capital, an administrative list fixed by the state rather than
by income or by data volume.

**Why only twelve.** The host began answering HTTP 429 with `Retry-After` set to
a date one calendar month out rather than a delay in seconds. That is a quota
resetting on a calendar, not a rate to back off from, so the run stops instead
of retrying and the nineteen remaining cities are not yet fetched.

**Coverage, recorded and never used as a filter.** Each page states its own
volume in one of two sentences, and which one it uses is itself a reading: a
city with traffic gets an entry count and a twelve-month window, a thin one gets
a contributor count over an *eighteen*-month window, no entry count, and a flag
saying some values are estimated. Both forms are parsed, the window is recorded
as a number of months, and the estimated flag is recorded per city. Contributor
counts on the twelve range from 3 (Hohhot) to 162 (Shanghai); two cities carry
the estimated flag.

**Unit, and it is exact rather than nominal.** The housing rows are labelled per
square foot, and the underlying contributions are per square metre: converting
back by 10.7639 returns round numbers in the thin cities -- Harbin 9,000,
Shenyang 8,750, Taiyuan 8,250, Hohhot 7,500, Changchun 6,667 yuan per square
metre. Round figures survive the conversion, so 10.7639 is the exact factor the
site used and not an approximation to it.

**Stability, measured twice.** Harbin's page re-read on 2026-09-01 against
fifty-three values transcribed by hand from the same source on 2026-07-15: 51 of
53 agree to the cent, the two that differ by about a quarter of one per cent,
which is the source recomputing its own averages as entries age. Separately,
thirteen values across six cities were read through a browser before the parser
was written, and the eleven whose cities are in the panel match the parser to the
cent.

**The official counterpart, and why it is only a counterpart.** The statistics
bureau's average residential selling price is an absolute quantity published per
region, which the bureau itself describes as suitable for comparison across
regions against local income. `data/b30_5/nbs/` holds that series once fetched,
and `experiments/b30_5_carrier_check.py` regresses the panel on it to put a
number on the panel's error. **Two other official series were checked and do not
serve**: the fifty-city food price release publishes the average *across* the
fifty cities rather than a figure per city, so the cross-city dimension is gone
at the source; and the seventy-city housing release is a change index, whose base
is each city's own past, so its numbers are not comparable across cities in
levels.

**No official source can carry the other side of this design, and that is
structural rather than a gap.** The contrast the station reads needs the price of
one branded item in many cities, and official price statistics average over
brands by collection method everywhere, not only here. For that side the
authoritative source is the posted price itself -- a manufacturer's list price, a
chain's menu by city -- which is the number rather than an average of reports
about it.


**The item-major route was tried and does not serve this design, 2026-09-02.**
The source publishes a ranking page per item that returns every city it covers
in one request, which looked like the way past a per-address monthly page quota:
ten requests instead of thirty-one. Measured on one item, it returns **505
cities worldwide and 13 in China**, against 104 Chinese cities in the bulk
archive. The thirteen are the source's index-admitted cities, and admission is
decided by contributor count -- **the same gate this station's registered text
rejects, because contributors concentrate in high-income cities and using the
gate is a selection on income.** So the ranking route buys breadth across
countries and not depth inside one, and the archive remains the carrier for the
Chinese cross-section. `data/b30_5/item_panel.json` holds the one item fetched;
the cross-route ratio check against the twelve pages passed before it was
written.


**USDA AMS grain bids and published freight, registered 2026-09-02 and not yet
fetched.** The door was read on paper. Four of the five items required before any
bulk pull are answered and the fifth is not, so no pull is authorised. Report
index at https://www.ams.usda.gov/market-news/state-grain-reports, weekly report
and dataset index at
https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets, API base
at https://marsapi.ams.usda.gov/services/v1.1/reports. The key is free on
registration through eAuthentication; the row cap per request is 5,000
unregistered and 100,000 registered, with no cap on the number of requests, and
browser calls are not supported. Derived tables are also posted as Excel on
data.gov under CC-BY 4.0.

**There are four carriers behind one name, and they do different work.** State
daily grain bids, thirty daily reports and four weekly ones, give a cash bid and
a basis per reporting zone per commodity, in dollars per bushel with the basis in
cents. The weekly Grain Transportation Report gives interior-origin to
export-position price spreads in dollars per bushel; posted rail tariffs by
commodity and origin-destination pair, monthly, in dollars per car, per metric
ton and per bushel; and southbound barge rates for seven river segments, weekly,
as a percent of a 1976 tariff benchmark together with a dollars-per-ton figure,
plus Columbia-Snake rates for twenty locations, monthly, in dollars per ton.

**The price-spread table carries one commodity per origin-destination pair, so no
two-commodity contrast can be formed on it.** Both the 2022-10-27 and the
2026-06-11 issue list the same five rows: Illinois to Gulf corn, Nebraska to Gulf
corn, Iowa to Gulf soybeans, Kansas to Gulf hard red winter wheat, North Dakota
to Portland hard red spring wheat. On the location-by-commodity incidence graph
that is five edges over six vertices, so the first Betti number is zero and there
is no independent cycle to read. The multi-commodity structure lives in the state
bids instead, where the same zone carries corn, soybeans and wheat.

**Posted rail tariff is per car and is shared across commodities on the one
origin-destination pair that carries two of them.** In the 2026-05-14 issue,
Gibson City, IL to Reserve, LA is quoted at $2,894.34 and $3,274.34 per car for
both corn and soybeans. The per-bushel figures printed alongside, $0.73 and $0.83
for corn against $0.78 and $0.88 for soybeans, are reproduced to the printed cent
by dividing the per-car figure by the statutory bushels per car. The report's own
footnote gives the conversion: a C-114 covered hopper carries 111 short tons
(100.7 metric tons), corn is 56 pounds per bushel and wheat and soybeans 60,
and the Goodland, KS to Kansas City, MO route uses a C-113 at 100 short tons.
Only that one city pair carries two commodities in the issue transcribed row by
row; the historical Excel files were not enumerated, so this is what one issue
shows rather than what the series contains.

**Freight is therefore common per car and not common per bushel, and bids are
quoted per bushel.** A corn-against-soybean contrast built on per-bushel bids
carries a mechanical term of 1.8018e-05 times the per-car freight difference
between the two links. Across the per-car range in the 2026-05-14 issue,
$1,425.30 to $7,005.09, that term reaches $0.1005 per bushel, the same order as
the basis itself and ten times the resolution floor below. Pairing two
commodities of equal statutory test weight, soybeans and wheat at 60 pounds, sets
the term to exactly zero whatever the per-car rate is.

**Resolution floor, measured rather than asserted.** State bids show a smallest
increment of $0.0025 per bushel, with most quotes on $0.01 or $0.005; the
per-bushel column of the tariff tables is printed to $0.01. The larger of the two
governs, so the floor is $0.01 per bushel.

**Barge rates are not commodity-specific, and that makes the barge side the
cleaner one.** Seven segments are published southbound (Twin Cities,
Mid-Mississippi, Lower Illinois River, St. Louis, Cincinnati, Lower Ohio,
Cairo-Memphis) and they line up by river segment with the barge elevator zones of
the Illinois daily report (Mississippi River, North Illinois River, South
Illinois River). Rail does not line up: the tariff tables name specific origin
stations while the state reports aggregate to zones, so using rail as a reference
requires a station-to-zone map that carries its own error.

**Two caveats on the freight tables.** The dollars-per-ton column of the barge
table is derived rather than observed, as percent of tariff times that segment's
1976 benchmark rate per ton divided by 100, and the benchmark differs by segment
(St. Louis is 3.99), so the benchmark must be stored alongside the percentage or
the dollars cannot be recovered. And the rail tables are posted tariffs, not
transacted rates: much grain moves on private contract rates that are not
published, so these serve as a published physical-cost benchmark and not as
freight actually paid.

**The item still open is the start of history.** The AMS announcement says the
series run "over a decade" without naming a start year, and the report pages do
not print one. One dated query per report settles it once a key is in hand, and
until then no bulk pull is authorised. Two further things are unmeasured and are
named here so they are not assumed: the actual fill rate per zone and commodity,
which should be reported as the three thinnest cells rather than a mean, and
whether any origin-destination pair beyond Gibson City carries two commodities.


**The state bids carry four keys and not two, read off the reports on 2026-09-02.**
A quote is identified by reporting zone, commodity, delivery period and futures
contract month, and the last two are printed. Delivery period appears as its own
column with values such as Current, Oct - Nov and Jun - Jul, and the contract
month rides alongside the basis figure as a letter, X for November, Z for
December, U for September, N for July. **Within one commodity on one day the
letter can differ across zones.** In the Ohio report of that date the soft red
winter wheat quotes carry Z at the two Toledo terminals and U at the country
elevators and the Ohio River barge houses, so those two groups sit at different
futures levels and cannot enter the same cycle: differencing across them would
import a calendar spread that has nothing to do with space. Some cells are worse
than that and have to be dropped whole, because the printed range itself straddles
two months: the Nebraska report of the same date quotes southwest soybeans at
-125.00U to -70.00X and southwest wheat at -88.00Z to -45.00U, so the two ends of
one range are not on the same measuring stick.

**Quotes are ranges rather than points, and a zone is a group of elevators rather
than one.** Any figure derived from them should be reported as a midpoint together
with the envelope over the range endpoints, so that the width of the interval stays
visible instead of being averaged away.

**Same-city position pairs exist and are the cheapest contrast available.** The
Ohio report quotes Toledo On River and Toledo Off River separately, both carrying
soybeans and soft red winter wheat at the same contract months. A contrast built
across two positions in one city needs no freight figure at all, since whatever
per-bushel handling cost attaches to a position is common to both commodities and
cancels. Enumerating the family costs nothing: it is a scan of the current reports
for city names that carry more than one position label.


## Registered deliverable grain, and why this one series can only be built forward

**Source.** Two workbooks published by the exchange at
`https://www.cmegroup.com/delivery_reports/`, free and with no login:
`deliverable-commodities-under-registration.xls`, daily, and
`stocks-of-grain-updated-tuesday.xlsx`, weekly. First captured 2026-09-02.

**Both are published as the current issue only.** There is no archive behind
either link and no query parameter that reaches an earlier day. The history sits
in a paid data product. That single fact decides how this source has to be
treated: **the series is not reproducible by re-running a fetcher**, so a day that
is not captured on that day is a permanent hole, and the cache is the asset rather
than a convenience. It is the opposite of the state grain reports on the same
shelf, where six and a half years can be pulled in an afternoon whenever the
question comes up.

**What the daily file measures.** Certificates in store at a named regular
facility for a named commodity: how much grain at that location is registered as
deliverable against the futures contract right now. The unit is certificates, not
bushels, and one certificate stands for a contract quantity fixed in the rulebook;
that conversion is a rulebook lookup and not an assumption. The weekly file
measures stocks held at the same facilities, which is a different quantity: what
is stored, rather than what is registered as deliverable.

**Why the pair is worth a daily job.** It carries a commodity index on a position.
Whether a location can deliver a given commodity is otherwise a yes or no fixed by
the regulars list; here it is a quantity that moves day by day, published by a
third party, and independent of any price series. A model in which position
carries a single scalar has no place to put it.

**Capture discipline, as implemented.** Raw bytes only, no parsing at fetch time,
because a capture that parses is a capture that can lose the day it was trying to
keep and the format belongs to the publisher. The day key is the UTC date, so this
series and the other daily capture in this project share one calendar. A day
already on disk is a no-op, so firing twice is safe and a missed fire is caught by
the next run on the same day. A payload shorter than two kilobytes, or one whose
magic bytes are not a workbook, is written under a name that says so and counted,
rather than dropped: what the source served on a given day is itself the evidence
about that day.

**The known gap between this source and the state basis reports.** The regular
facilities sit in named towns, while the state reports quote zones. The Ohio
report, for one, does not split by city, so several regular houses inside one
delivery district collapse into a single quoted zone. Any contrast that needs a
facility and a quote to be the same place has to check that the two sides name the
same place first, and the check belongs before the fetch rather than after it.

---

## Sound Toll Registers, re-engineered tables (STRO 2.0)

| | |
|---|---|
| source | STRO 2.0, re-engineered data from Sound Toll Registers Online |
| archive | figshare article `27176202`, `https://doi.org/10.6084/m9.figshare.27176202` |
| licence | **CC BY 4.0** |
| published | 2024-10-17 |
| retrieved | see `data/raw/stro_manifest.json`, per file |
| fetched by | `python data/fetch_stro.py` |
| coverage | passages of the Sound, 1497 to 1857, near complete from 1574, about 1.8 million passages |
| size | five port tables about 202 MB; all eighteen tables about 1.63 GB |

**Definitional basis, and what is standardised.** A row is one passage of the
Sound, dated, with the port the ship departed from and the port it was bound for.
The port fields are standardised and each carries three levels, the port itself
and two region levels above it. **The commodity field is not standardised**: it is
free text, about three hundred and fifty thousand distinct strings, and the source
says so.

**Which tables are fetched, and why it is not five out of eighteen for economy.**
The stage that uses this carrier reads the *pair* dimension, which port to which
port, per year. That needs `departure.csv`, `destination.csv`, `customs_entries.csv`
for the dates, and the two small key tables. It does not need the cargo, tax, image,
master or ship tables, which are the bulk. A different stage reading the commodity
dimension needs the opposite half and would pay the standardisation cost the ports
do not have.

**Two limits that are properties of the source and belong before any reading.**
The destination port field begins only in the middle 1660s, while the departure
port runs from 1497, so a reading that needs an ordered pair covers about 190 years
and one that needs only the origin covers the whole span. And the register is a
chokepoint rather than a census: it records passage of one strait, so absence in it
is absence from that route and not absence from trade.

**Verification.** The archive publishes a size and an MD5 for every file and the
fetch script carries both, resumes an interrupted transfer from the byte it reached,
and sets a file aside under a name that says so rather than keeping or removing one
whose digest does not match. A truncated CSV does not raise when it is read, it
just ends early, and every count taken from it is quietly low.


### The published mapping from written cargo names to plant taxa

| | |
|---|---|
| source | De Groot, Van Andel, Kool, Hazenberg, Kjesrud and Teixidor-Toneu, *Economic Botany* 76(3), 2022, 285-299 |
| doi | `10.1007/s12231-022-09550-x` |
| licence | **CC BY 4.0**, the article is open access and the supplement travels under the same licence |
| the file | `12231_2022_9550_MOESM1_ESM.xlsx`, reached from the article page under Supplementary Information, served from `media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs12231-022-09550-x/MediaObjects/` |
| what it holds | 264 plant products against 140 botanical taxa, and for each product the written Danish forms, the verified botanical name, family, the part traded, a use category, climate zone, continent of origin, **the search terms used**, the number of passages, and literature references |

**Why it is on this shelf rather than in a footnote.** The commodity field in the
registers is free text and the scan of it here counts 273,943 distinct written
forms. A count of how many distinct things moved is meaningless on a field like
that, because the number of spellings tracks the number of clerks and the volume of
traffic rather than the trade. This table is the only published instrument that
maps those written forms onto a grid fixed outside the source: botanical
nomenclature does not move when a port grows or a scribe is replaced. The column
that does the work is the list of search terms, which is a rule rather than an
estimate.

**What it does not cover.** Plants only. Iron, copper, salt, herring and
manufactures are outside it, so a support set counted on this grid is a restricted
one. The restriction is defined by botany rather than by anything under study, which
is what makes the restriction admissible; it still has to be stated beside every
reading rather than in a note. The grid is also coarse at 264 classes, and which
classes were merged matters more than how many, so the merge pattern is worth
printing once before any count is taken.

**One figure in the paper that is not settled.** It reports 2,130,930 passages as
documenting plant-based commodities. The register holds 2,152,670 passages in total,
which makes that figure 99.0 per cent of them. Read as a count of passages carrying
at least one plant product it is plausible for a trade dominated by grain, timber,
flax and hemp; read as a sum over products it should exceed the total rather than
fall just under it. The distinction is computable from the search terms and the
cargo scan, and it should be computed rather than assumed.

**A second document, from the same paper's citations.** The transcription project
publishes its own list of the commodities that occur as cargoes. The paper cites it
at `soundtoll.nl/images/files/List%20of%20products.pdf`; the current site serves what
appears to be the same document at `data/pdf/products.pdf`, 199,690 bytes. The label
the project puts on that link opens with the word incomplete, in its own
parentheses. The study took 207 plant entries from that list and then had to scan
the raw spellings to reach 264, which is the measure of how far the list goes.

### The same registers in a second packaging, `data/raw/stro/classic/`

The archive publishes the registers twice. The re-engineered tables above are one
normalisation; `www.soundtoll.nl` serves the older one, ten tables rather than
eighteen, and the two differ in where the ports live. In the older packaging a row
of `ladingen` is one parcel of a cargo and carries the commodity together with the
port that parcel came from and the port it was bound for, so a commodity and a pair
of positions sit in one table. In the re-engineered tables the ports are normalised
out into files of their own. A stage reading the pair alone is cheaper on the newer
set, a stage reading a commodity against a position is cheaper on the older one, and
that is why both are on the shelf rather than one being a leftover.

The fields that matter for reading the older set. In `ladingen` the port of
departure, the port of destination, the commodity, the unit of measure and the
number of units all come from the manuscript, while the passage key and the parcel
line number are supplied by the transcription project, which marks the distinction
in its own documentation. `places_standard` carries the standard toponym, two levels
of region above it, coordinates, a modern name, and a flag saying whether the place
lies west of Helsingør, which is the sailing direction without having to infer it
from geography. `maten` maps a written unit of measure onto a standard one.

The older packaging is served from one directory and the links on the page are
click handlers rather than anchors, so the addresses are recorded here: the tables
sit under `https://www.soundtoll.nl/data/db_downloads/` as `ladingen.csv.zip`,
`doorvaarten.csv.zip`, `places_source.csv.zip`, `places_standard.csv.zip`,
`maten.csv.zip` and `secties_totaal.csv.zip`. What the server reports for each, in
bytes, is 77,470,292 / 69,755,586 / 26,885,052 / 83,797 / 71,382 / 74,180, and those are the numbers a
finished transfer has to match. The sizes printed beside the links on the page are
not all current: the page says twelve kilobytes for the units table where the server
sends seventy-one, and it says seven hundred and seventy-one kilobytes for the
source toponyms where the server sends twenty-seven megabytes, so the length the
server reports is the one to check against.

The two toponym tables are what makes this packaging worth keeping for a reading
that needs positions rather than pairs. The written toponym in a cargo or passage
row is free text; `places_source` carries that written form beside a code, and
`places_standard` carries the code beside a standard name, two levels of region,
coordinates, a modern name, and the side of Helsingor the place lies on. The
re-engineered set has no table of either kind, so the written forms there stand
unresolved. Two cautions travel with the mapping: it is the transcription
project's own judgement rather than anything in the manuscript, and it resolves
how a written name is spelled, not whether a name is a port at all, which leaves
entries naming a whole sea exactly where they were.

The same directory tree carries the project's own list of the commodities that occur
as cargoes, at `https://www.soundtoll.nl/data/pdf/products.pdf`. The label the
project puts on that link begins with the word incomplete, in its own parentheses,
which settles how much weight the list can carry: it is a working list compiled by
transcribers, not a closed vocabulary, and a published study that used it took its
plant entries from the list and then had to scan the raw spellings to find the rest.

The table documentation the site serves describes an older shape than the files do.
It lists four fields for the source toponyms where the shipped table carries thirteen,
the extra ones being the standard name itself, the full set of variant spellings for
each standard name, a letter index on both the written and the standard form, flags
for whether the name occurs as a home, departure or destination port, and two levels
of region. The documentation is worth reading for what each field means and is not
worth trusting for what a file contains; open the header.

Integrity rests on a different footing here. The figshare set publishes a size and
an MD5 per file. This one ships each table inside a zip, and a zip stores a checksum
for every member, so a transfer that was cut short fails to extract rather than
reading short and quietly returning a low count. Extraction succeeding is the check.
The publisher also warns that the files are UTF-8 and are to be imported rather than
opened, which is the same trap as every other place on this shelf where an encoding
is left to the platform to guess.

One caution belongs with the data rather than with any single reading. The
transcription splits at 1633 and 1634 into two databases, because the registrations
in the earlier half are more complex and were digitised by a different method. That
is a boundary in the recording and not in the trade, and a count of how many
distinct things moved is exactly the kind of statistic such a boundary moves. A
reading either stays on one side of it, or measures first what the boundary itself
is worth.

## Stage B30-3: import duty on passenger cars

**File**: `data/raw/wits_tariff_hs870323.csv`, 190 reporters, four columns
(`iso3`, `wits_name`, `mfn_2020`, `mfn_2022`).

**Source**: UNCTAD TRAINS, served by the World Bank's WITS API.
`https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/all/partner/000/product/870323/year/{YEAR}/datatype/reported`,
with reporter names from
`https://wits.worldbank.org/API/V1/wits/datasource/trn/country/ALL`.
**Retrieved 2026-09-03.** Response is SDMX 2.1 StructureSpecificData; the values
taken are the single annual observation per reporter series.

**Definition**: HS 870323, motor cars with spark-ignition engine of 1500 to 3000 cc,
**MFN applied rate as reported**, partner `000` (world), annual.

**Two things about this file, both of which bear on how it may be used.**

**One: the year.** `mfn_2020` has 180 reporters and `mfn_2022` has 154. The price
vintage it is joined to is late 2022. **The reading in `docs/b30_results.md` uses
the 2020 column for coverage, and the 2022 column is carried in the same file so a
re-run can check the choice.** Passenger-car MFN rates move slowly, and the two
columns agree exactly on most reporters that have both.

**Two: how it was fetched, because the route matters for reproducing it.** The
WITS host refused both the cloud sandbox and the local shell at the proxy (HTTP
403 on CONNECT). **The file was retrieved through an ordinary browser session
instead**, by fetching the two endpoints above from a page on the same host. A
re-run from a machine with direct access to `wits.worldbank.org` reproduces it from
the URLs as written.

**Not in this file**: preferential and bound rates, non-tariff measures,
registration tax, excise, and dealer margin. **Only the MFN applied duty.**


---

## `falling_short_layout.txt`, the residential annex of a global electricity tariff survey

**File**: `data/raw/falling_short_layout.txt`, 138 KB, 47 pages separated by form
feeds. It is the output of `pdftotext -layout` on the published pdf, kept as text so
the reading reproduces without the pdf and without `pdftotext` installed.

**Source**: *Falling Short: A Global Survey of Electricity Tariff Design*, World Bank
Policy Research Working Paper, Foster and Witte. The pdf is served at
`https://documents1.worldbank.org/curated/en/568181583337584393/pdf/Falling-Short-A-Global-Survey-of-Electricity-Tariff-Design.pdf`
and the landing page at
`https://documents.worldbank.org/en/publication/documents-reports/documentdetail/568181583337584393`.
**Retrieved 2026-09-03.** The underlying tariff schedules were collected under a
World Bank and ESMAP project and are also served at `http://rise.esmap.org`.

**Definition**: Annex 1A is the residential annex. Per country it prints the tariff
schedule organising variable, the structure type, the number of blocks, the block
sizes in kWh, **the charge on each block in USD rounded to two decimals**, average
monthly consumption in kWh, an operating and limited capital cost recovery
benchmark, an average unit tariff, and a monthly bill. **Charges are in USD at two
decimals, and that rounding is the binding limit on what can be read off this file.**

**The vintage is 2015 to 2016 and it is a cross-section.** No country appears twice.

**Which fields are used and which are not.** `experiments/tariff_blocks_count.py`
reads `country`, `type`, `n_blocks`, `block_sizes`, `block_charges` and
`consumption`. The last three columns of the annex run together under the
layout parse in some rows and **are not used by any reading**.

**Not in this file**: the other four annexes, which carry demand and time-of-use
charges and have no block structure; and the underlying national schedules at their
own precision, **which is a separate collection and has not been made**.

## Agmarknet daily arrivals and prices (India, APMC mandis)

| | |
|---|---|
| Producer | Directorate of Marketing and Inspection, Ministry of Agriculture and Farmers Welfare |
| Endpoint | `https://api.agmarknet.gov.in/v1/prices-and-arrivals/date-wise/specific-commodity`, query `year, month, stateId, commodityId`. The ASP.NET page `SearchCmmMkt.aspx` that this collection first targeted no longer answers; the portal was rebuilt on this JSON API and the first fetcher is kept as `data/fetch_agmarknet.py.expired_..._旧门已不存在` |
| Fetcher | `data/fetch_agmarknet_api.py`, phases `probe / map / states / pull`, one commodity-month-state per request, resumable, refuses to run without `--confirm` |
| Access | the endpoint answers 403 to requests from outside India, on three separate networks tested. It was reached through a browser carrying an Indian exit |
| Rate | serial with a delay, never concurrent. Ten concurrent requests returned 19 answers out of 200 and then blocked serial requests as well for a period. Retry backoff `[3, 9]` seconds |
| Landing | `data/agmark/api/<commodity>/<YYYY-MM>.json` (not committed) |
| Downloaded | 2026-09-03 onward |
| Unit | one row per market per day: State, District, Market, Commodity, Variety, Grade, Min/Max/Modal price, Arrivals. The response carries `markets` directly, so the support-set count needs no derivation |
| Arrivals unit | tonnes |
| Commodity ids | `data/agmark/api/commodity_map.json` and the same as `.txt`, 592 ids probed one by one, ids 1..600 with eight blank slots (86, 123, 238, 453, 536, 547, 548, 549) that answer HTTP 500. 600 is where the scan stopped, not where the master ends |
| Ids are not stable | an older third-party id list read off the retired dropdown disagrees with the live master on at least one entry (id 311 is `Gladiolus Bulb` on the live master and `Sponge` on the old list). Everything downstream resolves commodities BY NAME through `commodity_map.json`, never by a stored id |

**Second copy of the same series, third-party, used only to measure the instrument before buying anything:**

| | |
|---|---|
| Source | `github.com/iancovert/Agmarknet`, a scrape of the same portal |
| Coverage | 12 commodities, 2008 to June 2017, about 4 million rows |
| Landing | `data/agmark/<commodity>/<year>.csv` (not committed) |
| Downloaded | 2026-09-03, three commodities only: White Peas, Cowpea (Lobia-Karamani), Lentil (Masur) |
| Why only three | they span the thickness range the design has to live on; the measurement they were bought for is in `experiments/agmark_support_floor.py` |
| Columns | state, district, market, variety, group, arrivals, min, max, modal, date. **This copy carries the three administrative levels; the JSON API rows above do not**, which is failure mode 153 |
| Also read by | `experiments/b60_anchor_regeneration.py` and `experiments/b61_branch_loading.py`. B61 reads the `variety` column as a stratifier and uses only the `Other` stratum, since a price gap between varieties is not a price gap between markets |

**Four readings that belong with the data, not in a footnote:**

1. **Arrivals are reported per market per day, and a market reports only on days it trades.**
   A month with no row for a market is not a zero, it is a market that did not report.
   The support-set statistic counts markets with a positive arrival, so it inherits this.
2. **The two copies are not interchangeable.** The third-party one stops in 2017 and covers
   12 commodities; the portal fetch is the one every reading after 2017 must come from.
3. **A market-month with no row is a market that did not report, and not reporting is free.**
   Uploading is described as a responsibility of the market committee, and no penalty for
   failing to upload appears in any of the official descriptions of the network. A 2025-08-18
   letter from the producer to one state marketing board records that, apart from two market
   committees, markets in that state had submitted no price data at all for June and July 2025.
   About 1,800 markets are connected with work in progress on another 700. So the missingness
   is administrative, it clusters by state and month, and any reading whose outcome counts
   reporting markets has to absorb a state-by-month shock.
4. **A filed row is not always a fresh row.** Across three commodities, 8.6 to 18.8 percent of
   filings repeat the previous filing's price triple byte for byte, and about two thirds of
   those repeats sit inside runs of five or more consecutive identical filings, which a
   geometric benchmark with the same mean undershoots by a factor of 11 to 14. The longest
   single run is 279 consecutive identical filings. The behaviour is concentrated: 5 to 14
   percent of markets hold every run of ten or more. Arrivals do not show it; their repeat
   rate rises with the reporting gap, which is a selection on small values and goes away when
   both endpoints are held above 10 t. Measured in `experiments/agmark_repeat.py`,
   `agmark_repeat_within.py`, `agmark_repeat_runs.py`; the trap is failure mode 147.



---

## B34: LFS microdata, and the statutory rates it is read against

### The four quarters

| SN | Internal file name | Quarter | Renamed to | Bytes (.dta) |
|---|---|---|---|---|
| 8826 | `lfsp_aj21_eul_pwt24` | 2021 Apr-Jun | `lfs_ry2021_q1_aj21.dta` | 101,650,113 |
| 8872 | `lfsp_js21_eul_pwt24` | 2021 Jul-Sep | `lfs_ry2021_q2_js21.dta` | 98,078,281 |
| 8915 | `lfsp_od21_eul_pwt24` | 2021 Oct-Dec | `lfs_ry2021_q3_od21.dta` | 94,247,791 |
| 8957 | `lfsp_jm22_eul_pwt24` | 2022 Jan-Mar | `lfs_ry2021_q4_jm22.dta` | 87,186,821 |

| | |
|---|---|
| Source | UK Data Service, Quarterly Labour Force Survey, End User Licence |
| Retrieved | 2026-09-04, Stata format |
| Redistribution | not permitted under the licence, and none of it is in this repository |
| Location | `data/raw/UK Data Service/`, docs unpacked to `doc/`, cache in `data/b34/cache/` |

**`ry2021` in the new names is the *rate year*, 1 April 2021 to 31 March 2022, not the
calendar year.** All four quarters fall inside one rate year, which is what makes a single
common threshold well defined for the whole window. The rename is load bearing for a second
reason: the loader takes the year from a four-digit run in the file name, and the original
names (`lfsp_aj21`) contain none, so an unrenamed file is silently dropped by the grouping.

**Only the four calendar quarters are taken.** The catalogue also carries rolling quarters,
one per month with a three-month window. Mixing them in would inflate the count in a cell
by up to a factor of three, and that count is the only thing the resolution floor reads.

**Redistribution, and why this directory has its own ignore rule.** The extracted
per-person cache under `data/b34/` is a row level export of licensed microdata. The raw
`.dta` files sit under `data/raw/`, which is excluded, but the cache does not fall under
that rule, so `data/b34/` is excluded in its own right. Untracked is not the same as
excluded; it only means not yet added.

**Two vintages in one column, recorded here under the rule that forbids it.** `hiqual` is
`HIQUAL15` for the first three quarters and `HIQUAL22` for the fourth: the coding frame
changed at the end of 2021, and the label on `QUAL21_14` records it. No criterion on this
station uses that column; the extraction script carries the matched source name through and
names it at the end so that the two are never read as one series.

### The statutory rates the pay variable is read against

The threshold is a published rule, not an estimate, so it is recorded here with its
instrument rather than derived. Rate year 2021-22, in force 1 April 2021:

| Band | Rate | Where it is set |
|---|---|---|
| National living wage, aged 23 or over | 8.91 | SI 2021/329 reg 2(2), amending SI 2015/621 reg 4 |
| Aged 21 but under 23 | 8.36 | SI 2021/329 reg 2(3)(a), amending reg 4A(1)(a) |
| Aged 18 but under 21 | 6.56 | reg 2(3)(c), amending reg 4A(1)(b) |
| Under 18 | 4.62 | reg 2(3)(d), amending reg 4A(1)(c) |
| Apprentice | 4.30 | reg 2(3)(e), amending reg 4A(1)(d) |
| Accommodation offset, per day | 8.36 | reg 2(4), amending reg 16(1) |

Rate year 2022-23, in force 1 April 2022, from SI 2022/382: 9.50 / 9.18 / 6.83 / 4.81 /
4.81, offset 8.70. The band boundaries are unchanged between the two years.

Rate year 2019-20, in force 1 April 2019, from SI 2019/603 (reg 2(2) for the living wage,
reg 2(3) for reg 4A(1)(a)-(d), reg 2(4) for the offset): 8.21 for aged 25 or over, 7.70 for
21 but under 25, 6.15 for 18 but under 21, 4.35 for under 18, 3.90 apprentice, offset 7.55.
Checked against the GOV.UK historical table and the House of Commons Library briefing; the
fifteen cells agree across all three. **The band boundaries differ from the later years**:
{18, 21, 25} here against {18, 21, 23} from April 2021, because the living wage age was
lowered from 25 to 23 on 1 April 2021. That move is the treatment one arm of this station
reads, so the two rate years are not interchangeable and the boundary set travels with the
year.

**One instrument break sits inside this rate year, and it is the survey's own.** ONS records
that in March 2020 the LFS changed initial contact from face-to-face to telephone because of
the pandemic, and that housing tenure weights were introduced for periods from January to
March 2020 onward. Both fall in the fourth quarter of the 2019-20 rate year. Any comparison
of *levels* across these two rate years carries that break; a comparison of *positions*,
which is what a kink location is, does not. The two are reported separately.

| Source | URL |
|---|---|
| Statute, 2021 | https://www.legislation.gov.uk/uksi/2021/329/note/made |
| Statute, 2022 | https://www.legislation.gov.uk/uksi/2022/382/made |
| Apprentice condition, and the base regulations | https://www.legislation.gov.uk/uksi/2015/621/regulation/5/made |
| Who qualifies at all | https://www.legislation.gov.uk/ukpga/1998/39/section/1 |
| Historical table | https://www.gov.uk/national-minimum-wage-rates |
| House of Commons Library CBP-7735 | https://researchbriefings.files.parliament.uk/documents/CBP-7735/CBP-7735.pdf |
| Low Pay Commission Report 2021 | https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1039488/LPC_Report_2021_web_version.pdf |

Four sources were checked against each other cell by cell. Three agree everywhere. The
fourth disagreed in one cell, the 21-22 rate for 2021, where the figure read out of it is
the apprentice figure from the row above; the statute settles it. Recorded rather than
averaged away.

**Three definitional gaps between this pay variable and statutory compliance, all of them
real and none of them cancelling:**

1. **The accommodation offset is invisible here.** An employer providing living
   accommodation may offset up to 8.36 per day, so a fully compliant worker can show a
   gross hourly figure below 8.91. Direction: raises the share below a low threshold, and
   it concentrates in agriculture, hospitality and care.
2. **The apprentice rate is not an age band.** Under reg 5(1) it applies to an apprentice
   in the first twelve months of employment **or** under nineteen, and the disjunction means
   a twenty-five year old first-year apprentice is lawfully paid 4.30. Losing it at nineteen
   is a boundary the minimum wage age bands do not have.
   `APPRCURR` (currently an apprentice) and `APPSAM` (the apprenticeship is part of the main
   job) are extracted so this can be held out of the profile and measured rather than argued
   about. Only half of the statutory condition is observable: `APPST12` splits before and
   after the year 2000 and nothing in the survey dates an apprenticeship to the month, so the
   "first twelve months of employment" half has no counterpart here. A first-year apprentice
   aged nineteen or over is therefore counted as a non-apprentice, which leaves some lawful
   low pay in the comparison group and makes any difference measured this way a lower bound.
3. **Average hourly pay is not the compliance base.** It is derived from gross weekly pay in
   the main job and hours (LFS User Guide volume 4), and it therefore carries overtime
   premium in the numerator, which compliance excludes. Direction: lowers the share below a
   threshold for anyone working paid overtime.

The three directions are not the same, so they do not compose into a correction that could
be applied in advance. Each is carried as its own qualification.


## B46: German population by single year of age, used as a difference of two series

`data/raw/GESIS histat.zip`, retrieved 2026-09-05. GESIS study **ZA8617**, Gabriele
Franzmann (2015), histat-Datenkompilation, *Bevölkerung nach Alter in Jahren und nach
Geschlecht für das Deutsche Reich, die frühere Bundesrepublik und Deutschland,
1871–2010*, Köln, GESIS. Registration is required to download it; the archive holds 70
`.xls` tables and one index in `.docx`.

**The definition matters more than usual here, because the series wanted is not in the
archive and is obtained by subtraction.** Three territories are covered, and each states
its own scope in the file:

- **A tables**, `früheres Bundesgebiet (alte Länder)`, 1871 to 1989. Its note reads
  `Ab 1946: Stand zum 31. 12. des jeweiligen Jahres. Ab 1957 einschl. Saarland, ohne
  Berlin. Ab 1962 Bundesgebiet einschl. Berlin West.`
- **B tables**, `Deutschland in den Grenzen nach Oktober 1990`, 1950 to 2013. Its note
  reads `Früheres Bundesgebiet sowie Neue Länder und Berlin-Ost.` Its source line reads
  `Statistisches Bundesamt (Hrsg.): Zusendung der Daten auf Anfrage für die Zeit von 1950
  bis 1989.`
- **C tables**, the German Reich.

**A and B overlap over 1950 to 1989 at the same reference date, in the same unit, from the
same office, by single year of age, so B minus A is the territory of the German Democratic
Republic.** For 1989 the difference is **16,433.796 thousand**, which matches to the person
a figure this repository already held from an unrelated route, across 86 single-year cells
none of which is negative. That agreement is the check on the subtraction and is recorded
with the reading rather than assumed.

**Unit is thousands of persons; reference date 31 December.** Two shapes in the archive
have to be handled and are noted so a rebuild does not trip on them: tables `A-01-11`
through `A-01-17` carry no `Gebiet` row, so their `Geschlecht` and `Alter in Jahren` rows
sit one row higher than in the other tables; and one column label in `A-01-11` is printed
`52 unter 53` without the hyphen the rest of the file uses.

**Not redistributed**, under the rule at the top of `.gitignore` that raw data stays out of
the repository. What the repository keeps is the three band totals and the reading derived
from them.

## B30-16, B30-17, B30-18: three quote carriers, retrieved 2026-08-30

These three were used and their readings published before anything was written
here. The entries are late, and the lateness is the disclosure.

### B30-16, airline fares, two backends

| | |
|---|---|
| Backend one | DOT Consumer Airfare Report Table 6, Socrata, `https://data.transportation.gov/resource/yj5y-b2ir.csv`, 1996Q1 onward |
| Backend two | Origin and Destination Survey DB1B market table, `https://transtats.bts.gov/PREZIP/` prefetched as `T_DB1B_MARKET_<year>.zip`, selected through `DL_SelectFields.asp?gnoyr_VQ=FHK` |
| Retrieved | 2026-08-30 |
| Caliber, backend one | exactly two carriers per city pair per quarter, the largest carrier and the lowest-fare carrier, each with its own fare. Sparse by construction, and the sparsity is a property of the publication and not of the market |
| Caliber, backend two | a 10 per cent sample of tickets, quarterly. Collection ended July 2025, so the series is closed, not merely stale |
| **Not interchangeable** | the two backends select different carriers per route by different rules. Their fares do not belong in one column |

### B30-17, Treasury constant maturity curve

| | |
|---|---|
| Source | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/`, daily par yield curve, one CSV per year |
| Retrieved | 2026-08-30, years 2010 to 2024 |
| Caliber | rates print to two decimals in per cent, so the publication grid is one basis point. Levels and changes therefore have different resolution floors, `1/sqrt(12) = 0.2887` bp and `sqrt(2)/sqrt(12) = 0.4082` bp, and the two must not be swapped |

### B30-18, overnight rates

| | |
|---|---|
| Source | FRED, `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR` and `id=EFFR` |
| Retrieved | 2026-08-30 |
| Origin | both series are administered and published by the Federal Reserve Bank of New York; FRED redistributes them |
| Caliber | SOFR begins 2018-04-03, EFFR reaches back to 2000. **The two do not span the same period**, and the arm reads their difference, so the usable window starts where the shorter one does |
| Gaps | EFFR carries empty cells on non-business days, and an empty cell is not a zero |

**Attribution, required by the source's terms rather than by convention.** The
New York Fed permits copying, distributing and creating derived works from its
content, on three conditions: carry its copyright notice and source identifier,
do not state or imply that it endorses the use or anything created from it, and
do not impose more restrictive terms on the content. So, for the readings in
this repository that are derived from SOFR and EFFR:

> Contains content from the Federal Reserve Bank of New York, © Federal Reserve
> Bank of New York, subject to the Terms of Use at newyorkfed.org. The readings
> derived from it here are this repository's own and are not endorsed by, and
> carry no representation from, the Federal Reserve Bank of New York.

The other two carriers need no such notice. The Consumer Airfare Report, DB1B
and the Treasury curve are output of United States federal agencies, which is
not subject to copyright in the United States, and neither agency attaches a
reuse condition to them.

**What is in the repository and what is not.** The raw quarters, the per-year
Treasury CSVs and the two FRED series are excluded, by the rule at the top of
`.gitignore` that raw data is not redistributed and because the DB1B quarters
alone are 315 MB that a documented fetch rebuilds. The derived cell matrices and
curve matrices are excluded too, as a cache keyed by a configuration hash. What
stays is the readings, the `stage*.json` files, and the small `*_diag.json`
files that record the shape of each cell matrix, since those are the only
provenance a reader gets for a matrix that is not shipped.


## DPRK 2009 currency reform, the deposit side and its 2010 redemption

Supplied by hand, 2026-09-05. Contemporaneous reporting; used as literature and not as measurement.

- **Daily NK, Japanese edition, 2010-07-29**, "貨幣改革で預金した50万ウォンを返還".
  https://dailynk.jp/archives/10052
  The Central Bank announcement of a two-week redemption from 1 August 2010 at 100:1 capped at
  500,000 old won; the source's own arithmetic that five thousand new won buys five kilogrammes of
  rice at a thousand won a kilogramme; and the statement that many residents had not deposited
  because their deposits were confiscated in the fourth currency reform of 1992.
- **Daily NK, Chinese edition, 2010-08-01**, same report, published a few days after the Japanese
  and Korean editions, which appeared the same day. The Korean edition was not obtained; the
  Japanese and Chinese texts agree.
  https://www.dailynk.com/chinese/8%E6%9C%88%E5%BC%80%E5%A7%8B%E8%BF%94%E8%BF%98%E8%B4%A7%E5%B8%81%E6%94%B9%E9%9D%A9%E5%BD%93%E6%97%B6%E7%9A%8450%E4%B8%87%E5%85%83%E5%AD%98/
  Also the statement that all prices had returned to their level before the reform.
- **NK Chosun, 2010-07-29**, "북, 화폐개혁시 예금 50만원 8월부터 교환".
  https://m.nk.chosun.com/news/articleView.html?idxno=126899
- **Yonhap, Chinese service, 2009-12-02**, the initial ceiling of 100,000 old won per household with
  the excess to be deposited. https://m-cn.yna.co.kr/view/ACK20091202002200881
- **ReliefWeb, North Korea Today No. 308, 2009-12-02**, "each household is allowed to exchange up to
  100,000 won and the exchange rate is 100 to 1".
  https://reliefweb.int/report/democratic-peoples-republic-korea/north-korea-today-no-308-dec-2009
- **Chosun Ilbo English, 2009-12-15**, the raise on 6 December from 100,000 per person to 500,000,
  still at 100:1, and the unrest.
  https://www.chosun.com/english/north-korea-en/2009/12/15/PNJEVEV3PGXQP45BCYA7FZHSDA/
- **Oriental Daily, 2009-12-16**, the 6 December raise described as a first-step measure, the promise
  that old notes deposited in banks could all be converted, and no inquiry into the origin of sums
  below one million old won. https://orientaldaily.on.cc/cnt/china_world/20091216/00180_015.html
- **Asahi Shimbun, 2009-12-04**. http://www.asahi.com/special/08001/TKY200912040457.html
- **Kyunghyang Shinmun, 2009-12-06**. https://www.khan.co.kr/article/200912061818185
- **JoongAng, Japanese and Chinese editions**. https://japanese.joins.com/JArticle/124404 and
  https://chinese.joins.com/news/articleView.html?idxno=17852
- **Time, "Economic 'Reform' in North Korea: Nuking the Won"**, limits raised to 150,000 in cash and
  500,000 in bank notes. https://time.com/archive/6948798/economic-reform-in-north-korea-nuking-the-won/

Two cautions travel with this material. The redemption cap of 500,000 old won equals the per-person
cash exchange ceiling settled on 6 December, so deposits above it return nothing. And the report's
own two figures, five thousand new won returned and rice at a thousand new won a kilogramme together
with prices having returned to their pre-reform level, are what carry the reading that the written
rate was honoured while that rate had become the loss.

## Bearer deposits and the Czechoslovak separation of 1993 (retrieved 2026-09-05)

Used for the scope change from a cash-against-deposit cut to a cut on whether a holder's identity is
attached to the money, and for the occupancy of the above-limit band.

- **Czech National Bank, its own history pages, currency separation of 1993.** Carries the cash
  exchange maxima verbatim, four thousand crowns for persons over fifteen and one thousand for those
  under, and the sentence on the above-limit instruments: postal orders, central-bank vouchers and
  the deposit instruments of Česká spořitelna and Poštovní banka were designated, and were used
  minimally because most citizens had already put their surplus cash in banks. One word came back
  with a dropped letter in retrieval and is completed from context; the rest is verbatim. Official,
  first tier for this arm.
  https://www.historie.cnb.cz/cs/menova_politika/6_menova_politika_na_ceste_ke_standardu_vyspelych_zemi/3_menova_odluka_cr_a_sr/
- **Aktuálně.cz, 30 December 2016**, on the end of the withdrawal period for anonymous passbooks.
  Carries the two figures used: a volume of 120 billion crowns on the bank's books at the end of 2002
  when validity lapsed, and 1,785 million crowns still uncollected at the end of 2016; and that
  validity ended under the banking act. Second tier, quoting the bank.
  https://zpravy.aktualne.cz/finance/konci-posledni-termin-pro-vyplatu-anonymnich-vkladnich-knize/r~0794b9cccea411e6aa860025900fea04/
- **Měšec.cz**, that bearer passbooks lapsed definitively on 31 December 2002 under the new banking
  act, that interest stopped from 1 January 2003 with a ten-year withdrawal period, that they were
  anonymous deposits, and that one institution ran them. Second tier.
  https://www.mesec.cz/clanky/anonymni-vkladni-knizky-konci/
- **Sovcombank's own explainer**, that the bearer deposit is a product that appeared in Soviet times,
  and that issuing bearer securities was prohibited in Russia from 1 June 2018. **Third tier, a
  bank's popular article, marked as such and not load-bearing**; no primary instrument retrieved.
  https://journal.sovcombank.ru/sberezheniya/predyavit-za-vklad-kto-i-dlya-chego-mozhet-otkrit-vklad-na-predyavitelya

One caution travels with the first item. Its sentence on the above-limit instruments cannot be read as
a route walked after the announcement, because the same corpus records that all payment traffic was
halted between the announcement on 3 February and the changeover on 8 February. The phrase reads as
"long before", so it describes a starting position and not a response.

## Kazakhstan, November 1993 (retrieved 2026-09-05)

Used to close the alternative-route cell for this carrier and to correct its price count.

- **Vlast.kz, an analytical journal, on the introduction of the tenge.** Carries verbatim the note
  issues withdrawn, treasury and bank notes of the USSR State Bank and the Bank of Russia of the
  1961 to 1992 issue, denominations of 1,000, 5,000 and 10,000 from 15 November and 1 to 500 from
  18 November; the per-person limit of 100,000 roubles; and the treatment above it, credited at one
  tenge to 500 roubles to a special personal account with no right of use for six months while a
  special commission examined the source and legality. It also states that the Russian reform caused
  an uncontrolled dumping of old-issue money into Kazakhstan. Second tier.
  https://vlast.kz/modern_history/53658-1993-god-kak-vvodili-tenge.html
- **Kazinform, the state news agency, chronicle entry for 1993.** Carries the within-limit rate and
  ceiling in one sentence: every citizen had the right to exchange old roubles for tenge at 500
  roubles to one tenge, and no more than 100,000 roubles. Second tier, state agency.
  https://www.inform.kz/ru/letopis-nezavisimosti-1993-v-kazahstane-poyavilas-nacional-naya-valyuta_a2960287
- **National Bank of Kazakhstan, currency history page.** Retrieved and carries only the decree date
  of 12 November and the circulation date of 15 November; **no rate, no note issues, no ceiling.**
  Recorded as checked and empty rather than not checked, first tier.
  https://nationalbank.kz/ru/page/currency-history

The two second-tier sources agree on the rate from opposite sides: one gives it for the within-limit
exchange and the other for the sums above the limit, and they give the same 500 to one. That
agreement is what carries the reading that the tiers differ in access and not in price.

## Burma's demonetisations and Indonesia 1959 (retrieved 2026-09-05)

### Burma

Used to test whether the 1987 row had been written from an account of 1985, and to establish the
within-country comparison on the registration point.

- **Historical Dictionary of Burma, entry on demonetization.** States that the first two
  demonetizations offered limited compensation to persons who surrendered old banknotes and that
  the 1987 order did not; gives 25, 35 and 75 kyat replaced by 45 and 90, and a share of as much as
  80 per cent of the country's savings. Reference work, second tier.
  https://hist_burma.en-academic.com/186/Demonetization
- **The Irrawaddy, anniversary piece.** Gives 5 September 1987, the three denominations, that it
  offered no compensation at all, and around 80 per cent of the money in circulation. Burmese
  outlet, second tier and closest to the event.
  https://www.irrawaddy.com/specials/on-this-day/day-three-myanmar-banknotes-suddenly-became-worthless.html
- **Facts and Details, economic history of Myanmar.** Gives 3 November 1985 demonetised without
  warning though the public was allowed to exchange limited amounts of the old notes for new ones,
  and all other denominations then in circulation remained legal tender; and 1987 without warning or
  compensation, some 75 per cent of the country's currency, with 45 and 90 issued on 22 September.
  Compilation, second tier. https://factsanddetails.com/southeast-asia/Myanmar/sub5_5g/entry-3126.html
- **Central Bank of Myanmar, history of banknotes.** Attempted and refused by the site's robots
  rules; **recorded as not retrieved rather than absent.** https://www.cbm.gov.mm/content/history-bank-notes

Two cautions. The share of currency affected is given three ways and the denominators differ, so it
is carried as a range of 75 to 80 per cent with the denominator disputed. And the sources disagree on
which denominations 1985 voided; that disagreement is recorded and not resolved, because nothing
here depends on it.

### Indonesia 1959

- **Indonesian official regulation register.** Gives the instrument's full title, `Peraturan
  Pemerintah Pengganti Undang-Undang Nomor 3 Tahun 1959 tentang "Pembekuan Sebagian Dari Simpanan
  Pada Bank-Bank"`, enacted and promulgated 24 August 1959, in force 25 August 1959. **The page
  carries metadata only; the text is a PDF that has not been retrieved.** First tier for title and
  dates. https://peraturan.bpk.go.id/Details/53808/perpu-no-3-tahun-1959
- **A numismatic weblog.** Supplies the two instruments side by side: `Perpu No.2 Tahun 1959` cutting
  the 500 and 1,000 notes to 50 and 100 with an exchange deadline of 1 January 1960, and `Perpu No.3
  Tahun 1959` freezing ninety per cent of bank deposits, current accounts and time deposits, above a
  threshold of 25,000 rupiah, the frozen portion converted into long-term government savings.
  **Third tier, and the threshold and the proportion rest on it alone.**
  http://uangkuno-magelang.blogspot.com/2011/07/15-senering-tahun-1959-dan-1965.html

The official title alone settles the device type, a freeze rather than a write-down, which is what
the classification turns on; the threshold and the percentage are the parts still resting on a third
tier, and one retrieval of the PDF would raise them.

### Burma 1964 (retrieved 2026-09-05)

Retrieved while looking for the 1985 per-person ceiling, which is still not in hand.

- **Mostly Economics, on Burma's three demonetisations.** Carries the terms verbatim: reimbursement
  if notes were surrendered within a week, spot reimbursement for small amounts, timely
  reimbursement for amounts between 500 and 4,200 kyats, further scrutiny and the escalating tax
  above 4,200 kyats, and 78 per cent of notes returned. **Second tier, and it does not name the work
  it is transcribing**, which is recorded rather than glossed over.
  https://mostlyeconomics.wordpress.com/2017/10/30/history-of-burmas-3-demonetisations-1964-1985-and-1987/
- **The Irrawaddy, on the first demonetisation of the socialist era.** Gives 17 May 1964, the 100 and
  50 kyat notes voided, exchange for valid notes up to a total value of 500 kyats, and that exchanges
  were stopped after a few days. Second tier, and closest to the event.
  https://www.irrawaddy.com/specials/on-this-day/day-myanmar-experienced-socialist-eras-first-demonetization.html

The two fit together and the figure 500 appears in both, one as the ceiling on what could be
exchanged on the spot and the other as the point above which payment was promised but deferred. That
agreement is what carries the three-band reading; neither source alone states three bands.

### Central Bank of Myanmar, history of banknotes (retrieved 2026-09-05, by hand)

The site's robots rules refuse automated retrieval, so the page was opened by hand and the text
supplied. **First tier: the issuer's own record.**
https://www.cbm.gov.mm/content/history-bank-notes

It carries the issue date of every denomination and the three demonetisations verbatim, and on those
it is decisive: 3 November 1985 voided the 20 kyat note issued in 1958 and 1964 and the 100 issued in
1976 and the 50; 25, 35 and 75 were withdrawn on 5 September 1987; 45 and 90 were issued on 22
September 1987; the 25 was issued on 30 September 1972, the 75 on 11 November 1985 and the 35 on 1
August 1986.

Two cautions travel with it. **The page is silent on exchange or compensation terms for all three
demonetisations**, which is recorded as a property of this class of source rather than as an
omission. And it is internally inconsistent about the 50, giving 30 April 1979 as its issue date in
one sentence and describing it as issued in 1975 in another; nothing here depends on that.

### PERPU 3/1959, full primary text (retrieved 2026-09-05, by hand)

`Peraturan Pemerintah Pengganti Undang-undang No. 3 Tahun 1959 tentang Pembekuan Sebagian Dari
Simpanan Pada Bank-Bank`. Enacted and promulgated at Bogor, 24 August 1959, in force 25 August 1959
at six in the morning Java time. `LEMBARAN NEGARA TAHUN 1959 NOMOR 90`;
`TAMBAHAN LEMBARAN NEGARA NOMOR 1838`. Ten articles plus an official memorandum. **First tier, full
text.** Downloaded by hand from the official register.
https://peraturan.bpk.go.id/Download/43209/perpu%20003%201959.pdf

A note on how it was obtained, because it cost a wasted retrieval first. **On this register the id in
the Details path and the id in the Download path are different numbers**, 53808 and 43209 here, and
substituting the first for the second returns a real and valid but entirely unrelated instrument
rather than an error. **The download link is taken from the page; it is not constructed from the id.**

The two figures the third-tier source had given, 25,000 rupiah and ninety per cent, are confirmed
verbatim. **Everything else in the record derived from this instrument comes from lines no summary
carried**, above all the sentence in the memorandum stating that the available figures on the
composition of bank deposits were not complete enough for a more careful calculation.


## Two third-party repositories cloned under data/raw, and neither is redistributed

Both were cloned rather than fetched by a script in this repository, so neither has a
manifest. Git records a clone sitting inside another repository as a gitlink, which is
a directory-shaped entry, and the exclusion that re-admits directories so the manifest
exceptions can run had therefore been letting them through. Both are now named in
`.gitignore`. **Neither is committed here and neither should be: one is 1.5 GB and the
other 348 MB, and each has an upstream that serves it.**

### Gaokao-Compass-11M

`https://huggingface.co/datasets/choucsan/Gaokao-Compass-11M`, cloned to
`data/raw/gaokao/Gaokao-Compass-11M`, upstream commit `545f9f6` dated 2026-08-06,
1.5 GB on disk. A published dataset of Chinese college admission records.

**Nothing in this repository reads it.** The provincial admission panel used here comes
from the route recorded above under the heading on the tables as published: 34 pages
held, listed with province, year and track in `data/gaokao_sources.json`, reduced by
`data/parse_gaokao_provincial.py` to `data/gaokao_provincial.csv`. The clone was taken
while looking for a second source and is kept because re-cloning it costs 1.5 GB of
transfer, not because any reading depends on it. **If a reading later does depend on it,
the commit above is the one to pin.**

### Looking into Informal Currency Markets as Limit Order Books

`https://github.com/lolfig/Looking-into-Informal-Currency-Markets-as-Limit-Order-Books.git`,
cloned to `data/raw/havana_lob`, upstream commit `196c279` dated 2025-03-05, 348 MB on
disk. Third-party code and collected messages that model the Cuban informal currency
market as a limit order book: scraping, message parsing, order-book simulation.

It sits beside the Cuban stages in this repository and is **a neighbouring construction
by other people, not an input to any criterion scored here**. The readings on that
carrier are taken from the instrument described above under what the instrument is,
whose four limits are recorded there. **Any use of this clone would be a separate
carrier with its own availability work, and none has been done.**

### IEA End-use Energy Prices

`https://api.iea.org/prices`, the public read endpoint behind the End-Use Prices Data
Explorer, no key and no login, licensed CC BY 4.0. Responses are cached verbatim under
`data/cache/iea/`, one file per query with the query sorted into the file name, first
fetched 2026-09-06. `experiments/b49_energy_class_square.py` reads the cache and goes to
the network only when a file is missing or `--refresh` is passed. The dimensions are
country, sector (`ELGEN`, `IND`, `RESID`, `TRANS`), product (electricity, natural gas,
light fuel oil, LPG, fuel oil, steam coal, gasoline, automotive diesel), unit (national
currency, USD, USD at constant 2020 prices and PPP) and year, each enumerable from a
list endpoint under the same host.

**Basis: prices include VAT, in every sector.** The database documentation states that
the World Energy Prices series includes VAT for the industry and electricity-generation
sectors as well, so that countries stay comparable, and that it is the OECD-only
quarterly series which reports those two sectors VAT exempt. This endpoint returns the
former, which is read off the country coverage rather than assumed: Algeria is in it and
is not an OECD member. **The distinction is load-bearing.** Were residential prices
quoted with tax and industrial prices without, a residential-against-industrial reading
would be measuring the tax convention rather than the price.

**Depth differs by product and is the binding limit here.** Electricity and natural gas
by sector carry three years only, 2000, 2010 and 2025; transport fuels carry a full
annual series back to the 1960s. The one product with depth is the one with a single
class, so depth and shape run opposite in this source. Units are `USD/MWh` for
electricity and gas, checked in the script rather than assumed, since the square divides
one by the other.

The cached files stay on the machine that fetched them, as everything under `data/`
does. They are small and the endpoint serves them, so re-fetching costs one run.

### Eurostat bi-annual energy prices

`https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/`, the public
dissemination endpoint, no key and no login. Four datasets are used: `nrg_pc_204`
household electricity, `nrg_pc_205` non-household electricity, `nrg_pc_202` household
gas, `nrg_pc_203` non-household gas, first fetched 2026-09-06 and cached verbatim under
`data/cache/eurostat/`, one file per query with the query sorted into the file name.
`experiments/b50_hungary_class_square.py` pulls `geo=HU` alone;
`experiments/b52_europe_class_square.py` pulls the reporting area whole, which returns
**33 countries over 38 semesters, 2007-S1 to 2025-S2**, after the seven aggregate codes
(`EU`, `EU27_2007`, `EU27_2020`, `EU28`, `EA`, `EA19`, `EA20`) are dropped by name so
that no aggregate is read as a country. Both read the cache and go to the network only
when a file is missing or `--refresh` is passed.

**Bands: the per-band series, never the total band.** The total band carries 10, 10, 1
and 6 semesters across the four datasets while every consumption band carries 37, from
2007-S2 to 2025-S2. A time dimension listing 38 semesters says the system knows those
semesters, not that this country reported them, and the aggregate row is the sparser
one here rather than the fuller one. The bands taken are the standard reference bands
Eurostat itself publishes against: `KWH2500-4999` and `MWH500-1999` for electricity,
`GJ20-199` and `GJ10000-99999` for gas.

**Basis: one tax code on both legs, always.** Eurostat publishes three, `X_TAX` with no
taxes, `X_VAT` with other taxes but not VAT, and `I_TAX` with everything. Its own
presentation shows household prices with all taxes and non-household prices net of
recoverable ones, so **comparing the two as presented would measure the tax convention
rather than the price.** All three are computed here, and the differences between them
are the part of a class difference that taxation writes.

**A semester price is an average over six months, not a price on a date.** Any rule
taking effect inside a semester is diluted in proportion to the months it covers, which
is a resolution limit on dating and not on precision.

**One conversion is scalar and one is not.** Quoting the four prices in euro applies one
exchange rate per country and semester, shared by both classes, which cancels in the
difference of log ratios; the residual over the panel bounds what the instrument can
resolve. The purchasing-power unit is not a single scalar per semester and carries
structure of its own, so it is reported and excluded from that bound.

The cached files stay on the machine that fetched them, as everything under `data/`
does. They are small and the endpoint serves them, so re-fetching costs one run.

### IPEDS published tuition, through the Education Data API

`https://educationdata.urban.org/api/v1/college-university/ipeds/`, the Urban
Institute's public read endpoint over the federal IPEDS collection, no key and no login.
Two endpoints are used: `academic-year-tuition` for the published rates and
`directory` for the control code. Responses are cached verbatim under
`data/cache/ipeds/`, one file per state and endpoint, 112 files, first fetched
2026-09-06. `experiments/b53_tuition_class_values.py` reads the cache and goes to the
network only when a file is missing or `--refresh` is passed. Requests go out state by
state so an interrupted pull resumes where it stopped.

**Basis: the published schedule, not a paid amount.** The field is `tuition_fees_ft`,
full-time tuition and required fees as the institution published them for the academic
year, before any aid. That is what a reading of the counting law wants, because the
object is what the schedule writes rather than what any student ends up paying.

**Three class codes and what they are.** `2` in-district, `3` in-state, `4`
out-of-state, read per institution and per level (`1` undergraduate, `2` graduate). A
schedule is one institution at one level, and the reading is how many distinct dollar
amounts those three codes carry. 2020, the one year pulled: 56 states and territories
requested, 56 returned, 5,605 schedules over 3,861 institutions.

**Control comes from a different endpoint and is not derived here.** All 3,861
institutions matched a control code, none unmatched; the field is `inst_control` on the
directory endpoint, and joining on it is what makes the private-against-public split a
check rather than a restatement of the tuition figures themselves.

**Negative values are absence codes, and are dropped rather than read.** 124 rows
carried one in 2020. Reading a negative code as a fee would put a fourth distinct value
into a schedule that has three.

**Every published figure is a whole dollar amount, checked and not assumed.** Zero
non-integer figures over 5,605 schedules, which is why the collisions counted on this
carrier are exact rather than bounded above by a rounding step.

The cached files stay on the machine that fetched them, as everything under `data/`
does. They total about 23 MB and the endpoint serves them, so re-fetching costs one run.

## B45 广州小客车指标，两条腿（2026-09-10）

**取数手段**：手工，在一个浏览器里打开页面读出来。**两个取数器都拿不到这份内容**，而两者的病因不同，
**分清楚它们有操作后果**：

```
jtzl.jtj.gz.gov.cn   403，而它是地理封锁不是机器人封锁：
                     页面自己印着 Node information: PS-MIA-04d6m172（迈阿密边缘节点）
                     与 IP: 132.147.46.121。换出口地址才有用，换 UA 没用
jt.gz.bendibao.com   证书主机名不匹配，取数器读不到 robots.txt，于是不取
```

**级别（`D32`）：两份都是聚合站，属「其他」一级，不是官方。**
**任何判据在它们上面打分之前要与官方逐期通告对过。**

| 文件 | 内容 | 口径 |
|---|---|---|
| `data/b45/gz_auction_rows_raw.txt` | **竞价腿**，`169` 行，2012-08 到 2026-08 | 竞价时间 ｜ 个人最低成交价 ｜ 个人平均成交价 ｜ 单位最低成交价 ｜ 单位平均成交价。单位：元／个指标 |
| `data/b45/gz_lottery_individual_rows_raw.txt` | **摇号腿，个人普通车**，`160` 行，2013-05 到 2026-08 | 摇号时间 ｜ 摇号基数 ｜ 指标数量 ｜ 中签比例 ｜ 中签率 |
| `data/b45/gz_auction_bendibao_raw.txt` | 两次抓取的抬头、出处、级别、已知缺陷 | — |

**两条腿的重叠是 2013-05 到 2026-08**：竞价腿 2012-08 就开始，
**而摇号腿在 2013-04 之前逐行写着「暂无」**，即那几期没有摇号。**这是源头自己的缺，不是抄漏。**

**已知缺陷，逐条留在原文里不改（第 25 条：抄录带来源，缺陷原样留）：**

```
竞价腿   "2205年7月25日"   2025 年的笔误
         "2025月1月26日"   年月分隔符写成「月」
         2020 年 1 月整期缺，而 2020 年 2 月有两行（2月3日 与 2月25日）
摇号腿   "2026年4月7日"    其余各期都落在 26 日或之后，竞价腿同期写 4月27日
         2020 年 2 月同样两行（2月3日 与 2月26日），与竞价腿对得上
```

**抄录自检（已知答案，跑过）**：拿 `指标数量 / 摇号基数` 自己算中签率，
对上源头印出来的那一列，**160 行里只有 4 行差过 2%，四行全部是 `0.2%` 附近两位小数的舍入**
（`0.206 → 0.20`、`0.209 → 0.20`、`0.214 → 0.21`、`0.216 → 0.21`）。**抄录过关。**

**第二个独立编纂源已对过一次，13 期逐位相同（2026-09-10）：**

`yaochepai.cn/guangzhou` 的个人竞价表，窗口只有 `2025-08` 到 `2026-08` 十三期，
**而那十三期的最低价与平均价与上面那份逐位相同，零处不同。**
它另有一列上面那份没有的：**竞价参与人数**（其页脚自述「已剔除资格审核不通过的人员，
但部分人可能弃权不报价」），同样只覆盖那十三期。

**两个长跨度的商业库查了，都取不到**：迈博汇金 EDB 的「客车总量调控数据」分类下确有
「广州市中小客车增量指标(月)」共 184 条序列，**而表体由异步加载，页面停在「数据加载中」**，
导出多半要账号。前瞻同族，未逐条试。

**官方那一级的处置，写下来免得下一个人再花一次：**

> **本站的判据是两条序列一百六十期的关系，不是某一个数扛全部重量。**
> **所以要杀的是编纂错误，而杀它的是第二个独立编纂源，不是官方身份。**
> **`D32` 明文允许「没有官方口径时其他也用，但要在件里标明是哪一级」。**

**官方逐期通告留到读数出来之后再取，而且只取读数真正依赖的那一段。**
那时是几条公告，不是一百六十九条。**这是第 13 条第 4 步（先算成本）与 `D34`
（取不到给主张封顶）合起来的做法：不为全序列预先买对账，为承重的那一段买。**

**官方入口的实况，一并记下**：`jtzl.jtj.gz.gov.cn/index/gbl/index.html` 是逐期公告的归档页
（自称共 28 页 557 条，翻页 `index_N.html`），**而它对境外地址一律 403，病因是地理不是机器人**。
逐期公告的标题格式是
`关于{年}年{月}月份广州市普通车增量指标竞价的通告` 与
`关于{年}年{月}月份广州市普通车增量指标配置数量的通告`，
省级搜索 `search.gd.gov.cn/search/all?keyword=...&siteCode=440100` 可按标题检索。
**这三样都还没有被本项目实际打开过，属登记不属已验。**

**还没做的**：长跨度的第二源对账、官方逐期抽样对账、天津杭州深圳三个同族城市、
闸六的分辨率底、闸二闸三。**设计件仍未写。**


## B33 observed side: basic table by size of adjusted gross income and marital status

**Files** `data/b33/{23,22,21}in12ms.xls`, tax years 2023, 2022 and 2021.
**Source** the revenue service's Statistics of Income basic tables, Table 1.2,
`All Returns: Adjusted Gross Income, Exemptions, Deductions, and Tax Items`,
classified by size of adjusted gross income and marital status.
**URL pattern** `https://www.irs.gov/pub/irs-soi/{yy}in12ms.xls`.
**Level** official.
**Downloaded** by hand on the machine that runs the project, because the gateway
in front of both sandboxes denies this host by policy; the denial is recorded as a
connect rejection at the gateway rather than a transient failure, and no attempt
was made to route around it.
**Fetcher** `experiments/b33_step0_fetch_soi.py`: resumes a partial file, refuses
to re-download a complete one, and checks the first bytes are an OLE2 compound
file or a zip so that an error page or a truncation is reported rather than
parsed.

**What it is for.** Arm one of this station read a tax code against itself and
found two filing statuses sharing every printed number. This table is the observed
side of that: whether the two also pay the same at the same income. The reading
registered before the file was obtained is an ordering, not a line: the pair that
shares every printed number should show a far smaller gap in effective rate than
pairs that differ on printed numbers.

**Known limitation, stated before parsing, and resolved the same day.** The stub
had not been read when the file was obtained, so whether it reports surviving
spouses as a category of its own was unknown, and the registered reading said that
if it folded them the comparison would be recorded as the published aggregate
being unable to reach it rather than as the quantity being absent. **It folds
them.** All three years carry five column blocks of twelve columns each, headed
`All returns`, `Returns of married persons filing jointly and returns of surviving
spouses`, `Returns of married persons filing separately`, `Returns of heads of
households`, `Returns of single persons`. So this source gives four statuses in
four blocks, the merged one being the pair, and the within-pair comparison is
recorded as out of reach.

**Layout, for anyone parsing it next.** One sheet, `TBL12`, 49 rows by 63 columns
in each of the three years. Block headings on row 2, first columns at 1, 13, 25,
37 and 49. Inside a block the offsets are 0 number of returns, 1 adjusted gross
income less deficit, then number-and-amount pairs for total itemized deductions,
standard deduction, taxable income, income tax after credits and total income tax,
the last amount at offset 11. Rows 10 to 27 are the income bands of the
all-returns panel; row 8 is its total, row 28 begins a taxable-returns panel and
row 44 a nontaxable one.

## B64 two-tier gold market: the London fixing and the US monetary gold stock

**Files**
`data/b64/lbma_gold_usd_am_pm_19680401_19711231.csv`: 954 London trading dates from
1968-04-01 to 1971-12-31, US dollars per troy ounce, morning and afternoon fixing,
columns `date,usd_am,usd_pm`. An empty cell is a fixing that did not take place that
day (four dates carry only the morning price and one only the afternoon), never a zero.
`data/b64/fred_M1476CUSM144NNBR.csv`: monetary gold stock of the United States,
millions of dollars, monthly averages of daily figures, 1947-01 to 1970-12, 288 months,
as published.
**Source** the London fixing from its publisher's price files,
`https://prices.lbma.org.uk/json/gold_am.json` and `gold_pm.json`, each entry a date
and the fixing in US dollars, sterling and euros, of which the dollar element is kept.
The gold stock from FRED series `M1476CUSM144NNBR` (NBER Macrohistory, Federal Reserve
Board figures), `https://fred.stlouisfed.org/graph/fredgraph.csv?id=M1476CUSM144NNBR`.
**Level** official, both.
**Retrieved** 2026-09-11 in a browser on the machine that runs the project, because
the gateway in front of both sandboxes denies both hosts by policy. The files were
carried to disk in chunks. A 32-bit rolling hash of every chunk and of the whole
reconstructed file was computed in the browser on the source text and matched on
disk: 849329907 over 21,021 bytes for the fixing, 2540559288 over 4,930 bytes for the
gold stock. The fixing file keeps the source's own numbers in the source's own decimal
rendering; nothing was rounded.
**Loader** `experiments/b64_gold_two_tier.py` recomputes both hashes and refuses a
file that does not match, so a truncated or edited copy is reported rather than read.
**Not in these files** the gold stock for January to August 1971; the FRED series ends
in December 1970, and the months before the window closed are taken from the Federal
Reserve Bulletin before the stage's main reading.

**Added the same day: `data/b64/frb_table4_us_reserve_assets.csv`.** US reserve assets,
millions of dollars: total, gold stock in total (which includes the Exchange
Stabilization Fund's gold), the Treasury's gold stock, convertible currencies, the IMF
reserve position and SDRs. Year ends 1958 to 1970 and month ends September 1969 to
September 1971, 38 rows. **Source** Federal Reserve Bulletin, Table 4 "U.S. Reserve
Assets": the October 1971 issue, page A77, and the October 1970 issue, page A75, read
from the full text FRASER extracts from each issue's scan
(`https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/october-1971-21441/fulltext`
and `.../october-1970-21430/fulltext`). **Level** official. **Transcribed by hand** from
that text, which prints the table column by column, so every row carries its issue and
page, and each row is checked against the table's own sum: total equals gold plus
currencies plus reserve position plus SDRs. The sum holds on all 30 rows that print every
component. The eight month ends January to August 1970 have no SDR figure in the extracted
text, so their sum is not checked and the implied SDR figure is printed instead. The
overlapping month in the two issues, September 1970, agrees in every column, and the
December month ends agree with the year ends. **Why this file is needed**: the FRED gold
stock is the Treasury's alone and stands at exactly 10,367 from July 1968 to December 1969,
while gold in total, the Exchange Stabilization Fund included, moves from 10,892 at the
end of 1968 to 11,859 at the end of 1969. Flows through the conversion are read on the total.

**Added the same day: `data/raw/ICPSR_111725-V1.1.zip`.** The replication package of
Bordo, Monnet and Naef (2019), "The Gold Pool (1961-1968) and the Fall of the Bretton
Woods System: Lessons for Central Bank Cooperation", *Journal of Economic History* 79(4),
openICPSR project 111725, version V1.1
(`https://www.icpsr.umich.edu/sites/icpsr/view/studies/111725`). 751,327 bytes, SHA-256
`e18cf09f898632da83d0b2727d03f0c031dc7ed290ef9e27961a94fa2d90af72`. It holds the workbook
`data-file---The-Gold-Pool-Bordo--Monnet-and-Naef-2019.xlsx` and a zip of EViews programs,
which are not used. **Retrieved by hand** 2026-09-11, since the repository asks for a
login, and kept as downloaded: the zip is not unpacked, and the loader reads the workbook
from inside it after checking the digest. **Level** research data. The gold-window sheet
is the authors' digitization of a document in the archives of the Bank for International
Settlements (reference BISA 7.18(12)), with 1966 Q3 taken from a Bank of France document.

What is read, sheet by sheet:

- `Gold Window data`: US monetary gold transactions by customer government, quarterly,
  1965 Q1 to 1968 Q4, millions of dollars; positive is a US purchase of gold against
  dollars, negative a US sale. During the Gold Pool the United Kingdom's line is the
  Pool's. The authors' final classification (Gold Pool members other than the United
  Kingdom and France; non-members, the IMF included; the United Kingdom including the
  Pool; France) is followed for membership, and the four classes are formed from the
  country columns: in 1967 Q4 the final table enters Algeria's purchase of 150 in the
  non-member class twice, so its four classes sum to -1,105 against a quarterly total of
  -955. Formed from the country columns, that quarter reads -85, -99, -771 and 0.
  **1966 Q4 is missing and printed as zeros** in every
  column, the total included, and the row is highlighted together with 1966 Q3; the
  loader reads that row as missing. 1966 Q3 has no figure for net sales to industry.
- `Daily data set`: the London fixing and the Bank of England's gold intervention, on
  the Pool's behalf from 1961, daily from 1960-01-04 to 1968-03-14. The workbook does not
  state the unit of the intervention column, so that column is not read until a document
  states it.
- `Daily gold 1961-2016`: the afternoon fixing, from the Bank of England dealers' reports
  before March 1968 and from FRED `GOLDPMGBD228NLBM` after; `#N/A` marks days with no
  fixing. Used as a check only.
- `Monthly data set`: not read; its US gold stock is the FRED series already in
  `data/b64/`.

**Checked against files already on disk.** The quarterly movement of the gold stock sums
to the change in the Federal Reserve Bulletin's total gold stock, the Exchange
Stabilization Fund's gold included, within 6 in every complete year: 1965 -1,671 against
-1,665, 1967 -1,175 against -1,170, 1968 -1,178 against -1,173. In 1968 the Treasury's own
stock fell 1,615, so the movement column is on the total basis. On the 949 dates it shares
with the LBMA afternoon file, the afternoon fixing agrees on 742; 206 differ only because
the LBMA file rounds a third decimal half up to the cent (40.025 against 40.03); one differs
by exactly a dollar, 1968-05-16, 42.25 here and 41.25 in the LBMA file, and the LBMA figure
sits between that day's morning fixing, 40.85, and the next morning's, 41.60. Inside the
workbook the two daily fixing columns agree on 1,702 of 1,703 common days; 1962-12-31 reads
35.075 in one and 35.675 in the other.

**Not in this file**: transactions by customer after 1968 Q4.

**Added the same day: `data/b64/frb_table6_us_liquid_liabilities.csv`.** US liquid
liabilities to foreigners, millions of dollars, by holder: the IMF's gold transactions
(total, gold deposit, gold investment); foreign official institutions (total, short-term
liabilities reported by banks in the United States, marketable and nonmarketable Treasury
bonds and notes); banks and other foreigners; and nonmonetary international and regional
organizations. Year ends 1957 to 1969 and month ends July 1970 to July 1971, 36 rows. Where
reporting coverage changed, the table prints two lines for one date, the first comparable
with the preceding date and the second with the following one; both are kept, with a
`line` column. **Source** Federal Reserve Bulletin, October 1971, Table 6 "U.S. Liquid
Liabilities to Foreigners", page A78, read from the full text FRASER extracts from the
issue's scan
(`https://fraser.stlouisfed.org/title/federal-reserve-bulletin-62/october-1971-21441/fulltext`).
**Level** official. **Transcribed by hand** 2026-09-11 from that text, which prints the
table column by column; each row is checked against the table's own sums: the total equals
its four holders, and each holder's total equals its components. The sums hold on all 34
rows that print every component. The rows for 1957 and 1958 print no total for three of
the holders, because foreign holdings of bonds and notes were not broken down by holder
before 1959 (the table's footnote 7), so they are not checked. **Why this file is needed**:
the capacity side of the conversion is the gold stock against the dollar claims of the
official holders who could present them.

## B98 arm E: California net metering, the two vintages

`PGE-EEC-Price-Sheets.zip`, 717,253 bytes, fetched 2026-09-15 from
`https://www.pge.com/energyexportcredit`, which is the URL Schedule NBT names for
the values themselves ("The Export Compensation Rate values are posted at ...").
That URL is the file, not a page pointing at one. It holds one price sheet per
interconnection application year, 2023 through 2026, and a How-To.

Caliber: each sheet is 48 rows by 12 months by two components. The 48 rows are 24
hours of weekday values then 24 hours of weekend values. The two components are
`Energy Produced` and `Energy Delivered`, and the published How-To's own worked
example adds them: $0.33 + $0.05 = $0.38 total credit. So the export price is
their sum, read from the publisher rather than assumed.

`Res_Inclu_TOU_Current.xlsx`, 40,469 bytes, fetched 2026-09-15 from
`https://www.pge.com/assets/rates/tariffs/Res_Inclu_TOU_Current.xlsx`, effective
2024-09-01 to present. One workbook carrying both the rates and the period
definitions, which is why it was taken whole rather than one schedule at a time.

Caliber: `E-TOU-C` is sheet `Res Inclu TOU_240901-Present` rows 11-14, two periods
by two seasons. `EV2` is sheet `ElecVehicle&Tech_240901-Present` rows 14-19, three
periods by two seasons. Period definitions are in the sheets named `..._TOU
Periods`. The `Total Usage` column is used; `E-TOU-C` also publishes a baseline
credit of -0.09837 that applies only to baseline quantities, so it makes the unit
price depend on cumulative consumption rather than on the hour, and it is not
part of a price indexed by time of use. `EV2` publishes no such credit.

Not deducted: non-bypassable charges. Schedule NEM2 sheet 13 says they "may not
be reduced by any credits for exports to the grid" and "shall be assessed only on
the kilowatt hours consumed". Sheet 11 values exports at "the same price per kWh
at the same TOU period". So the NEM-2 export price is the retail price of that
period, unadjusted.


## B102 — Chinese residential electricity tariffs

Nothing was downloaded for this station. Every number is a constant read off a
published document and entered in `experiments/b102_cn_power_tariff.py`, where
each schedule carries its own `source` string. This section is the caliber note
for those strings, and it names the documents that read zero as well as the ones
that read non-zero.

**National.** `关于居民生活用电试行阶梯电价的指导意见` (NDRC, 发改价格〔2011〕2617号).
Sets the second tier's increment at "not less than five fen per kilowatt hour"
and the third at "about 0.3 yuan", then hands two structural questions to the
provinces in two separate sentences: household-size differences are for each
locality to work out, and time-of-day pricing may be set locally with enrolment
left to the household. So the increments in every provincial row below are the
national numbers and the block structure is not.

**Beijing, arm B.** Three documents from the municipal DRC: the notice on
multi-person households, its policy explainer, and the retail price schedule
(`W020240625381732703691.pdf`, table 1). Ordinary blocks `1-240`, `241-400`,
`400+` at `0.4883`, `0.5383`, `0.7883` yuan below 1 kV; registered blocks
`1-340`, `341-500`, `500+` at the same three prices; threshold six people.

Caliber, recorded rather than flattened: the explainer says the added kilowatt
hours go on the first tier, and the block table moves both finite edges by 100.
Both sentences are official and they do not say the same thing. The block table
is the one used, because it is the one that can be put straight into the price
schedule. The implementing rules are delegated to the Beijing electric power
company and have not been read.

**Guangdong, arm B.** 粤发改价格函〔2021〕826号 for the policy ("households of five
or more may apply to add 100 kilowatt hours to the first, second and third tier
bases respectively"; seven or more may instead elect the pooled-meter rate) and
粤发改价格函〔2023〕553号 for the resulting blocks (summer `0-360`, `361-700`,
`701+`; non-summer `0-300`, `301-500`, `501+`). Ordinary blocks and the `+0.05`
and `+0.30` increments are from the Guangzhou DRC price explainer: summer `0-260`,
`261-600`, `601+`; non-summer `0-200`, `201-400`, `401+`.

Caliber: increments published without a base price, which is enough, because the
class difference depends on the increments and the shift and not on the base.
The two seasons are one notice and one shift and therefore one reading, not two.

**Shenzhen, arm A.** Shenzhen DRC residential price schedule, PDF, in fen per
kilowatt hour including tax: tier one peak `111.21`, flat `65.42`, valley `24.86`;
tier two and three at `+5.00` and `+30.00` in every period. Registered as an
additive schedule and read back at zero.

**Shandong, arm A.** Provincial notice as reprinted by Tai'an municipality, PDF.
Tier one peak `0.5769` valley `0.3769`; tier two `0.6269` / `0.4269`; tier three
`0.8769` / `0.6769`. Registered as additive, read back at zero.

**Zhejiang, arm A.** Provincial compilation. Level: other. The provincial original
has not been checked. Tier one peak `0.5680` valley `0.2880`; tier two `0.6180` /
`0.3380`; tier three `0.8680` / `0.5880`. Registered as additive, read back at zero.

**Shanghai, arm A.** Municipal DRC tiered-tariff implementation notice, read in
the browser and checked twice against the original sentences. Second tier: `0.05`
per kilowatt hour undifferentiated, `0.06` peak, `0.03` valley. Third tier: `0.30`
undifferentiated, `0.36` peak, `0.18` valley. Printed to fen, so the tick is
`0.01` yuan.

**Read and found to carry no two-dimensional table.** Beijing's table 1 has no
residential time-of-day column at all, only a voltage column whose spread is
`0.0100` on all three tiers. Jiangsu publishes the two dimensions separately,
peak `0.5583`, valley `0.3583`, undifferentiated `0.5283`. Guangdong publishes a
peak/flat/valley ratio of `1.7 : 1 : 0.38` and states that the time-of-day split
is applied before the tier, so the tier increment adds on top and the square is
zero by construction. Jilin's notice says the amounts are to be worked out
separately. These rows are part of the coverage table and not omissions.

**Hunan, arm B and arm C.** `湘发改价调规〔2024〕14号`, full text, republished by
Huarong county government with the document number. Blocks are monthly and
seasonal: first tier to `200` in both seasons, second to `350` in March, April,
May, September, October and November and to `450` in January, February, June,
July, August and December. Increments `+0.05` and `+0.30`, printed to fen, so the
tick is `0.01` yuan. Five people and up raise "the first tier's monthly base by
100 kilowatt hours", the first edge alone. The same notice gives households on
minimum living support and rural or urban extreme-poverty support ten free
kilowatt hours a month.

Caliber: the notice carries no time-of-day clause at all, so Hunan contributes a
row to the arm-A coverage table and no arm-A reading. Whether the free quota is
taken off the metered quantity before the blocks are applied is not stated, which
is why arm C scores nothing.

**Sichuan, arms A and B.** `川发改价格〔2024〕668号` for the policy: a household
of five or more may add `100` kilowatt hours a month to the block base, rising
`30` per person per month above five, with the implementing rules delegated to
the grid companies. The blocks and the increments come from the implementing
guide issued by Xuzhou district, Yibin, republished with the provincial notice
attached. Ordinary blocks `0-180`, `181-280`, `281+`; a five-person household
`0-280`, `281-380`, `381+`; a six-person household `0-310`, `311-410`, `411+`,
worked out in the guide as `280 + (6-5) * 30`.

Caliber: Sichuan's second-tier increment is `0.10`, not `0.05`. The guide states
it in words and again in a worked example where the first tier's `0.5224` becomes
`0.6224` on the second and `0.8224` on the third. The national guidance sets five
fen as a floor, not as the number, so this is within it, and it means the earlier
reading that every province took the national figures was wrong — four did, this
one did not.

The same worked example is the source for Sichuan's arm-A row. A month of `400`
kilowatt hours split `100` peak, `150` flat and `150` valley is charged the tier
surcharge on quantity alone — ten yuan for a hundred kilowatt hours on the second
tier and thirty-six for a hundred and twenty on the third, with no reference to
which period they fell in. So the increment is period-independent and the arm-A
square is zero. That is read off the example's arithmetic rather than from a
printed two-dimensional table, and the record says so.

**Sichuan, the 2026 seasonal adjustment.** From 2026-07-01 the summer months,
July to September, take blocks of `260` and `460` while the other months keep
`180` and `280`. The prices are unchanged at `0.5224`, `0.6224` and `0.8224`,
which confirms the `0.10` increment from a second and later source. The
multi-person bases adjust in step, 阶梯电量基数同步调整.

Caliber: the registered summer blocks, `360` and `560`, are derived and the
record flags them as such. They follow from the implementing guide moving both
edges by a hundred plus that sentence, and no text found states them outright. A
second news restatement of the same adjustment garbles it — it reports the first
block as unchanged at `0-260` while also giving the old `181-280` — and is not
used.

**Guangdong, arm D.** `粤价〔2012〕146号`, quoted in full by the provincial DRC's
own price desk: the pooled-meter residential rate is the residential rate "raised
uniformly by `0.037` yuan per kilowatt hour", with no blocks. `粤发改价格函〔2021〕
826号` adds that a household of seven or more may elect it. Printed to three
decimals, so the tick is `0.001`.

**Shanghai, arms B and D.** `沪发改价管〔2012〕020号`, the tiered-tariff scheme, PDF
on the municipal DRC site. Annual blocks `0-3120`, `3120-4800`, above `4800`.
Undifferentiated increments `0.05` and `0.30`; time-differentiated ones `0.06`
peak against `0.03` valley on the second tier and `0.36` against `0.18` on the
third. Five people and up add `100` kilowatt hours a month to the block base, and
the clause names no tier, which is why arm B keeps Shanghai in the third cell
while recording the numbers a settled structure would need. Seven and up may
elect `0.024` yuan on every kilowatt hour instead, which is arm D.

Which edges move is not in either notice. The resulting blocks come from Xinmin
Evening News on 2020-09-02, the day after the policy took effect: first block
`0-4320` (`360 × 12`), second `4320-6000`, against the ordinary `0-3120`
(`260 × 12`) and `3120-4800`. Its worked example bills a six-thousand kilowatt
hour year as `4320 × 0.617` plus `(6000 - 4320) × (0.617 + 0.05)`, which fixes
both the edges and the first two levels. Level: a newspaper, not the price
authority, and it is a restatement rather than the rule itself. The station uses
it because the rule delegates and the delegated text has not been found; if the
implementing rule turns up and says otherwise, this row changes. The 2020 notice
on water, electricity and gas carries the same policy and calls that option
`居民阶梯平均价格`; an earlier note here described it as an undifferentiated
average rate, which the 2012 text corrects — it is a flat surcharge on every
kilowatt hour, not a price. Corrected 2026-09-15. Households on
minimum living support get `15` free kilowatt hours a month, deducted peak
quantity first and then valley, capped at actual use.

Caliber: the flat surcharge is printed to three decimals and the block increments
to two, so arm D's tick is `0.001` and arm A's is `0.01`. The free allowance is
stated as a deduction of quantity rather than of bill, which narrows arm C's open
question without closing it: what is still unstated is whether the deducted
quantity is also taken out of the block count.

**Anhui, arm B, nothing read.** The province runs the policy. No notice, no
blocks, no threshold has been taken. It is carried as a row so the coverage table
names it rather than omitting it, and it carries no threshold so that nothing in
it reads as a finding. The national increments sit in its row as a placeholder,
which after Sichuan is a distinction worth keeping visible: the national figures
are a floor, not a fact about any province.

**Jiangsu, arms A and C.** Yixing municipal government's explainer of the
provincial tiered tariff, 2014. Blocks `230` and `400` a month, increments `+0.05`
and `+0.30`; peak `0.5583`, valley `0.3583`, undifferentiated `0.5283`. The
low-income clause reads 对城乡「低保户」和农村「五保户」家庭每户每月给予15度免费
用电基数, and the mechanism 由供电企业从其抄表月份第一档电量中扣除对应的免费电量后
计算当月应收电费.

Caliber: the increments and the two period prices are printed in the same document
and neither is ever qualified by the other, which is the same shape as Guangdong
and Shandong and is why Jiangsu's arm-A square is registered at zero. The quota
comes out of the first block's quantity, so the edges do not move — that is arm C's
mechanism and it is a third case, not either of the two the arm was written to
choose between. Level: a municipal explainer of a provincial rule.

**Hunan, the provincial original.** `湘发改价调规〔2024〕14号` on the Hunan DRC site,
read in full in the browser. It carries three things the county reprint did not.
The first-tier base price below 1 kV is `0.588` yuan, which fixes Hunan's levels
against its increments. The low-income clause states the mechanism outright:
对全省「最低生活保障户」和「城乡特困人员救助户」家庭每户每月免费10千瓦时 …
免费用电量纳入第一档分档电量 — the free quantity is counted into the first block,
which is Jiangsu's mechanism in a wholly independent wording. And it prints two
flat rates with no blocks: `+0.016` for pooled-meter dwellings and `+0.046` for
non-residential users on the residential rate.

Caliber: those two flat rates are kept out of arm D and the reason is in the record.
The pooled rate is for dwellings with no household meter rather than an option a
metered household may elect, and without a household meter the position index is
not defined on that side, so the two classes are not at the same position. The
elective pooled rates in Shanghai, Guangdong and Anhui are a different object:
those households keep their own meter.

**Anhui, arm B.** The provincial DRC's multi-person notice, republished in full with
the issuing body named. Five people and up add `100` kilowatt hours a month, and the
notice prints the result: 第一档电量为0-280千瓦时，第二档电量为281-450千瓦时，
第三档电量为451千瓦时及以上. The ordinary edges, `180` and `350`, are that arithmetic
run backwards and are recorded as derived rather than quoted. Seven and up may also
elect the pooled rate at `0.5853`, which against a first tier of `0.5653` is a
flat `0.02` and is Anhui's arm-D row.

**Jiangsu, arms B, C and D.** The provincial DRC's own reply to proposal 1164 of
the 2021 provincial congress restates `苏发改价格发〔2021〕106号` and settles three
things at once. The blocks are monthly: 第一档在230度以内的，执行基本电价（每度电
0.5283元）；第二档在231至400度之间的，每度加价0.05元（每度电0.5783元）；第三档高于
400度的部分，每度加价0.3元（每度电0.8283元）. The multi-person amount is 人数满5人
及以上的，可申请每户每月增加100度阶梯电量基数, with no tier named, so arm B keeps
Jiangsu in the third cell with its numbers ready. And 人数满7人及以上的，也可选择
申请执行居民合表电价（高于居民生活用电基本电价每度电2分钱），不执行阶梯式电价, which
is an arm-D row at a flat `0.02`.

Correction: an earlier note here said Jiangsu had moved to annual blocks in 2021
and that the Yixing explainer's `230` and `400` were stale, so they must not be
carried into a current reading. That warning had no source. It was inferred from
a headline that was never opened, and this provincial text, dated after the 2021
notice it describes, gives the blocks as monthly and unchanged. The warning is
withdrawn. The `0.5283` in arm C is the same figure in the 2014 explainer and in
this 2021 reply.

**Anhui, the levels, the pooled rate and the voltage rows.** The provincial
residential price table as published by Lu'an DRC, and Xuancheng's explainer,
which print the same numbers. Below 1 kV: tiers `0.5653`, `0.6153`, `0.8653` and
a pooled rate of `0.5853`; at 1–10 kV: `0.5503`, `0.6003`, `0.8503` and `0.5703`.
Blocks `180` and `350` a month, increments `+0.05` and `+0.30`, which the
explainer states in words as well. Low-income households get ten free kilowatt
hours a month and the explainer says 具体办法另行规定, so Anhui contributes no
arm-C row.

Caliber: the pooled rate is the first tier plus `0.02`, stated as 每度提高2分钱但
不执行阶梯分档, and the multi-person notice says a household of seven or more may
elect it, which is what makes it an arm-D row rather than a category. The voltage
gap is `0.0150` on all four rows including the pooled one, which is what makes
Anhui the cleanest instance of the additive control: one table, two class
dimensions, one of them a level shift and one of them not.

**Beijing, the voltage rows.** Table 1 of the municipal schedule, already cited
above for arm B. The gap is `0.0100` on all three tiers.

**Anhui, arm C.** The provincial implementing rules as reported in 2012 give the
mechanism: 采取先征后返方式，由民政部门统一将退电费款发放到低保户、五保户的存折上.
That is Jilin's mechanism in different words and through the same department, so
Anhui is the second transfer rather than the fourth price. Xuancheng's explainer
grants the ten kilowatt hours and says 具体办法另行规定, which is why this row sat
in the third cell until the 2012 rules turned up.

**Arm C elsewhere.** Jilin ten kilowatt hours a month, and its mechanism is
published and is the other one: 先收后返, the household pays the ordinary bill and
the provincial finance department pays the money to civil affairs, which hands it
back with the 低保 payment. Nothing leaves any block, so the marginal price is
untouched and this is a transfer rather than a price. Source: Jilin City's
published answers on current water, heat, gas and electricity policy, which also
give its blocks — `2040` and `3120` a year, `170` and `260` a month — at `0.525`,
`0.575` and `0.825`, and a pooled rate of `0.5424`. Shanghai fifteen, deducted peak quantity
first and then valley, capped at actual use — the same shape as Jiangsu's and
Hunan's on a different axis, a time of day rather than a place in the month's
running total. Lianyungang's municipal Q&A restates the Jiangsu mechanism in the
same words as Yixing and adds that the free quantity is settled annually.

## B111: Black Sea two-sided cut, Ukrainian side

Nothing was downloaded. Every cell in `data/b111_black_sea_prices.json` was read
by hand from a public web page and carries its own `source` URL and `date`.

**Port, border and futures, 2026.** The broker Spike Brokers publishes a weekly
grain report (part II of its weekly market review, dated in the post text) and,
until 2026-07-14, a daily index, on its public channel `t.me/s/spike_brokers`.
Series read: corn, food wheat 11.5% protein and feed wheat at CPT Odesa (USD/t);
corn at FCA Chop (USD/t, first published 2026-07-17); new-crop corn forwards at
FCA Chop (EUR/t) and toward the ports (USD/t) with the delivery period as
written; wheat at FCA Chop (EUR/t, one week); milling wheat on Euronext (EUR/t),
with the contract month recorded per cell because the report rolls from
September to December after expiry. The 2026-06-05 Euronext cell is written as
a zone in the report and is flagged `zone`.

Caliber, recorded rather than flattened: where the report itself calls a port
price nominal, the cell carries `nominal: true` (corn 2026-07-17, 2026-07-24,
2026-07-31; wheat 2026-07-24 and 2026-08-07). New-crop quotes described as
nominal are flagged the same way. Every value was re-read against the page text
after transcription, post by post, with no mismatch. Four weeks were also
compared with independent republications of the same report (Interfax-Ukraine,
USM, Ukraine Open for Business, Latifundist) and agree.

**Interior.** UkrAgroConsult, "Prices for agri commodities, Ukraine, EXW, UAH/t",
retrieved 2026-09-16. The page shows only its latest eight dates, which leaves
July 2026 empty.

**Minimum allowable export prices.** Exports are prohibited when the contract
price is below the approved minimum (Cabinet of Ministers, 2024-08-21). Monthly
values for May to September 2026 per delivery term, each with the report that
printed it; the August values carry the 0.714 coefficient. September corn is
printed at CPT 195 above FOB 187 and is kept as printed.

**2025 reference.** The same channel, weekly reports from 2025-06-06 to
2025-08-29 quoting DAP Odesa ranges (USD/t) and FCA border ranges (EUR/t), and
the daily index from 2025-09-02. DAP ranges and the 2026 CPT index are different
bases and sit in different series.

**Exchange purchase prices, 2025 and 2026.** GrainTrade, the Ukrainian
electronic grain exchange, publishes one page a day titled "Purchase prices for
grains in Ukraine on <date>", with the weighted average purchase price of the day
per delivery term. The Friday page of every week from 2026-05-29 to 2026-09-11
and from 2025-05-30 to 2025-09-12 was opened in the browser on 2026-09-16, 32
pages. Rows read: corn and wheat grades II, III and IV. Columns read by their
headers: EXW elevators (UAH/t), CPT terminal (UAH/t), CPT terminal (USD/t) and
DAF (USD/t). A column the page leaves empty for a row gives no cell, so a page
yields 10 to 13 cells, and each page's count is on its coverage row. The page
calls no value nominal, and no cell carries a flag. After transcription every
page was opened again and each cell compared on the page by a script: 32 of 32
pages equal. The column alignment was checked once more on the 2025-09-05 page by
printing the four rows cell by cell with their headers.

**Futures, 2025.** Investing.com, Milling Wheat N2 Futures historical data: the
daily table for 2025-05-26 to 2025-09-19, set in the page's date control and read
on 2026-09-16, Friday closes kept. The series is continuous. It holds the
September 2025 contract until that contract's expiry on 2025-09-10 and the
December contract after it; the roll shows in the table as 170.50 on 2025-09-10
and 189.50 on 2025-09-11, and each cell records its contract. Two days were
checked against the Euronext closes printed by La Dépêche-Le Petit Meunier (14
July, September 197.25; 8 August 2025, September 196.50), and the table was read
again after transcription, 16 of 16 Fridays equal.

## B111: Black Sea two-sided cut, Russian side

Nothing was downloaded. The Russian cells sit in `data/b111_black_sea_prices.json`
with `side: "RU"`; each carries its `source` URL, the price `date`, and the
article date as `published`.

**Port and interior, 2026.** The Reuters Russian-service weekly grain report,
reposted on ru.themoscowtimes.com each Monday. It quotes IKAR for new-crop wheat
with 12.5% protein FOB Novorossiysk, with the delivery period; SovEcon for the
same class FOB deep water, a range in most weeks; SovEcon's average third- and
fourth-class wheat EXW for European Russia (RUB/t) with the weekly change; and
the Ministry of Agriculture's wheat export duty for the coming week (RUB/t).
Prices are dated to the Friday the report calls the end of last week, which
puts the Russian and Ukrainian weekly dates on the same days. From 2026-08-24
the report also quotes IKAR's Baltic FOB (Vysotsk, Ust-Luga).

Weeks without a repost: 2026-06-08 (Business Recorder), 2026-06-29 (CropGPT) and
2026-07-27 (Investing.com) are English rewrites of the same report, fetched twice
with a verbatim-quote prompt and marked `via: "fetch"`. For 2026-06-15,
2026-07-13 and 2026-09-07 no report was found; those Fridays carry the next
report's level less its stated change (`kind: "implied"`) or the next report's
stated previous value (`kind: "stated_prev"`). The coverage list names every
page opened and the number of cells read from it, including weeks with none.

Rusagrotrans' weekly note via Interfax (2026-08-19) gives FOB Novorossiysk and
FOB Baltic for the same delivery on the same day, fourth-class wheat delivered
by truck to deep-water ports, and regional EXW ranges.

Caliber, recorded rather than flattened: on 2026-08-24 the report calls the
week's decline rather notional and SovEcon calls its own prices mostly notional;
on 2026-08-31 IKAR's Novorossiysk price is given as nominal. Those cells carry
`nominal: true` with the quote. The 2026-06-22 repost has a dateline reading
8 June; its duty period, its export figure for 1-15 June and its sugar index
date place it in the week of 22 June. IKAR's new-crop quote reads "about 242,
unchanged" on 2026-06-01 and "down 2 to 242" on 2026-06-08; both are kept as
printed.

**2025 reference.** The same weekly report from 2025-06-02 to 2025-09-01. No
repost was found for 2025-08-04; that Friday's levels are implied from
2025-08-11. The fourth-class level of 2025-08-25 misses the reports on either
side by 25 roubles and is kept as printed, with a note.

**Checks.** After transcription each article read in the browser was re-read by
a script that pulls the IKAR, SovEcon, Baltic, domestic-price and duty sentences
from the page and lists their numbers; every transcribed value matched. The
Interfax note was checked phrase by phrase. The six articles of 2025-06-02 to 2025-07-07, added
later, were re-read the same way, every value equal. Two of them date IKAR's
price to Friday 20 June, a date carried over from an earlier week; the change
and the duty period place them on 27 June and 4 July, and the cells say so.

**The open route before the cut.** No quote of Russian wheat FOB Baltic dated
before 2026-08-11 was found. Searched on 2026-09-16: Rusagrotrans with FOB Baltic
in June and July 2026 and in 2025, FOB Baltic and Ust-Luga wheat prices in July
2025, and Russian wheat FOB Baltic in June 2026 in English. Every hit was an
August 2026 article: Interfax of 2026-08-19 and its reposts, Vedomosti of the
same day, and the Moscow Times reposts of 2026-08-24 and 2026-08-31. A second
round the same day went by kind of source. Price agencies: IKAR and SovEcon in
the weekly report, Rusagrotrans via Interfax, and the Sizov Report blog of
2026-09-02, which gives volumes and no prices. Exchange indices: the NAMEX
over-the-counter grain indices quote wheat FOB at the Black Sea ports only
(Novorossiysk, Tuapse, Taman, Kavkaz), and barley and corn add the Caspian; no
Baltic basis. Aggregators: zerno.ru shows its port purchase prices for the
latest day only, and zol.ru could not be fetched and was not retrieved another
way. Trade media in English: UkrAgroConsult of 2026-08-28, Fastmarkets of
2026-08-19 and the Reuters story reposted by Euronext on 2026-08-31 give no
price; Agbull of 2026-08-31 puts Russian 12.5% protein wheat from the Baltic at
about 262 dollars, after the cut and without a date or source. No Baltic quote
dated before the cut, or in the same weeks of 2025, was found.

## B59: the rates the size arm reads against, the primary credit rate, and the Call Report archives

### B59, overnight rate and interest on reserves

| | |
|---|---|
| Files | `data/b59/EFFR.csv`, `data/b59/IOER.csv`, `data/b59/IORB.csv` |
| Source | FRED, `https://fred.stlouisfed.org/graph/fredgraph.csv?id=EFFR`, `id=IOER` and `id=IORB` |
| Retrieved | 2026-09-08 |
| Origin | EFFR is administered and published by the Federal Reserve Bank of New York, and the attribution given under B30-18 applies to it here as well; the interest rates on excess reserves and on reserve balances are set by the Board of Governors; FRED redistributes all three |
| Caliber | daily, percent a year. IOER runs 2008-10-09 to 2021-07-28 and IORB from 2021-07-29, so a spread against interest on reserves joins the two at that date |
| Gaps | EFFR carries empty cells on non-business days, and an empty cell is not a zero |

### B59, the primary credit rate

| | |
|---|---|
| Files | `data/b59/DPCREDIT.csv`, `data/b59/primarysecondary.xlsx` |
| Source | FRED, `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DPCREDIT`; the Federal Reserve's Discount Window site, `https://www.frbdiscountwindow.org/-/media/documents/primarysecondary.xlsx`, linked from its Discount Rates page |
| Retrieved | 2026-09-16, both supplied by hand |
| Origin | each Reserve Bank sets the rate subject to review by the Board of Governors; the workbook is the Discount Window site's own table of changes; FRED redistributes the daily series |
| Caliber | DPCREDIT: business days, percent a year, 2003-01-09 to 2026-09-14, no empty cells. The workbook: one row per change, newest first, the primary and secondary rates as fractions (0.0375 is 3.75 percent) and each of the twelve Reserve Banks' effective date; on 30 of its 62 rows the twelve dates differ by a day or two, and the New York date is the one matched here. The change of 17 August 2007 appears as a footnote and not as a row |
| Check | every one of the 62 workbook rates is in DPCREDIT from its New York effective date on. After its first day DPCREDIT changes on 62 business days: 61 are workbook dates, and the other is 17 August 2007, the footnoted change |

### B59, Call Report bulk archives

| | |
|---|---|
| Files | `data/raw/CallReport/` |
| Source | FFIEC Central Data Repository, Public Data Distribution, Bulk Data Download: `Call Reports -- Single Period` in the tab-delimited format, and `Subset of Schedules` for 2009 |
| Retrieved | placed on disk 2026-09-16; `data/raw/CallReport/MANIFEST.json` records each archive's digest and the period its name claims, and an archive whose digest moves is reported |
| Caliber | one archive per quarter from 2010Q1 to 2026Q2, one archive holding the four quarters of 2009, which carries no Schedule RC-K, and a few earlier quarters outside the window read. Every column is read from the schedule its code belongs to and only under the archive's own description of it |

## B112: where euro area reserves sit, where they come in, and how much of each banking system's payments cross a border

Everything under `data/b112/raw/` was fetched on 2026-09-16 from the ECB Data Portal
API, `https://data-api.ecb.europa.eu/service/data/<flow>/<key>`, by
`experiments/b112_fetch.py`: 77 requests, each saved as a data file
(`detail=dataonly`) and a metadata file (`detail=nodata`, which carries `TITLE`,
`UNIT` and `UNIT_MULT`). `manifest.json` records, per request, the key, the start
period, the series count, the first and last period and the SHA-256 of the data and
metadata files. Every key was chosen from the series keys the flow returned the same
day, and every request came back with the series count that enumeration found.

**TGB.** TARGET balance of each national central bank, monthly, end of period (`E`)
and period average (`A`), 23 reference areas including the ECB (`4F`); most areas
from 2008-05. Million euro.

**ILM.** Balance sheet of each national central bank, monthly, end of month, 55 items
(54 for the ECB), from 2016-06; Croatia from 2023-01 and Bulgaria from 2025-12.
Reserves in this station are `L020000`, liabilities to euro area credit institutions
related to monetary policy operations. Refinancing is `A050200` (longer-term
refinancing operations), purchases are `A070100` (securities held for monetary
policy purposes). For the euro area as a whole: the weekly consolidated statement in
four groups by counterpart area and currency from 2008, the daily liquidity series
from 2008, and maintenance period averages from 1999-03.

**BSI.** MFI balance sheet items by country, monthly outstanding amounts: loans
(`A20`) and deposit liabilities (`L20`) against MFIs (`1000`), the central bank
(`1100`) and other MFIs (`1200`), each against counterparts in the euro area (`U2`),
in other euro area countries (`U5`) and at home (`U6`); and total assets (`T00`).
Start dates follow each country's reporting, 1997-09 for the earliest.

**PSS.** TARGET payments (`P101`), annual, 2000 to 2021, value (`VT`) and number
(`NT`). Counterpart sector `31` is payments to participants in the same national
component, `32` to participants in another component. The series end in 2021.

**FM.** Key ECB rates (`DFR`, `MLFR`, `MRR_FR`, `MRR_MBR`, `MRR_RT`), daily levels
from 2007-01-01.

Caliber: TGB and ILM are end of month, so a refinancing dose that settles late in a
month is seen a few days after it lands, and everything that moves within a month is
netted. Month-to-month noise in reserves is printed per country by block 6 of
`experiments/b112_object.py`.

### B113, discount window loans

| | |
|---|---|
| Files | `data/b59/dw/dw_data_<year>_q<quarter>.xls` for 2010Q3 to 2017Q4 and `.xlsx` for 2018Q1 to 2024Q2, 56 workbooks, with `data/b59/dw/MANIFEST.json` |
| Source | Board of Governors of the Federal Reserve System, discount window lending data, `https://www.federalreserve.gov/regreform/discount-window.htm`; the 2010 workbooks under `/newsevents/files/`, the rest under `/regreform/files/` |
| Retrieved | 2026-09-16 by `scripts/fetch_dw_lending.py`, run on a machine that reaches the site; the manifest records each workbook's URL, bytes and digest |
| Origin | published by the Board with a lag of about two years, one workbook per quarter, loans made from 22 July 2010 |
| Caliber | one row per loan, or per group of loans of the same type, term and rate made to one borrower on one day, which the workbook marks with a trailing `*` on the type of credit and reports as their total; loan amount and collateral in dollars, the rate in percent on the loan date; the borrower's ABA number as nine-character text with its leading zeros. The loan sheet is named `discount window loan data`, except in 2012Q3 where it is `discount window borrowing data`; its header is on the fourth row in every workbook, and the first twelve columns (loan date through loan amount) carry the same names throughout, while the outstanding-credit and collateral columns are named four ways over the years. Dates are Excel serial numbers in the `.xls` workbooks and date cells in the `.xlsx` ones. A separate `interest rates` sheet gives the primary, secondary and seasonal rate for every calendar day of the quarter |
| Coverage | borrowers include credit unions, which file no Call Report, so a loan whose ABA number is not in the Call Report panel of reporters is not an error of the join |

## B114: Sarafu, a community currency in Kenya, every transfer from 2020-01-25 to 2021-06-15

| | |
|---|---|
| Files | `data/b114/raw/Sarafu2021_UKdb_submission_complete_d.zip`, 39,745,209 bytes, read in place without unpacking; `data/b114/raw/manifest.json` beside it records its SHA-256, and `experiments/b114_sarafu.py` refuses an archive that differs from it |
| Source | UK Data Service ReShare, record 855142: Mattsson, Criscione and Ruddick, Sarafu Community Inclusion Currency, 2020-2021. The data descriptor is Scientific Data 9, 426 (2022) |
| Retrieved | 2026-09-16, downloaded by hand after registration. The archive is safeguarded data under the UK Data Service End User Licence, which prohibits research that aims to de-anonymize or re-identify Sarafu users; everything this station prints is a sum over areas, months or wallet classes |
| Origin | exported by Grassroots Economics from the xDAI chain the currency ran on; the archive carries the transaction table, the users table, a README, the descriptor's preprocessing notebook and documentation pages |
| Caliber | `sarafu_xDAI/sarafu_txns_20200125-20210615.csv` (173,316,885 bytes): one row per transfer, 930,161 rows; `source` and `target` are wallet addresses, which the users table carries as `xDAI_blockchain_address`; `weight` is in Sarafu; `transfer_subtype` is in capitals (`STANDARD`, `DISBURSEMENT`, `RECLAMATION`, `AGENT_OUT`) although the descriptor writes the codes in lower case. One row is in Kenyan Shilling (a disbursement of 1,000 on 2020-04-30) and is left out of every sum. `sarafu_xDAI/sarafu_users_20210615.csv` (9,477,705 bytes): one row per account with its area, area type, business type, held role and final balance; its `id` is a database index, not the key transfers use. Two staff wallets carry 3 and 20 staff rows, three accounts created in error share the address `None`, and one row repeats another exactly. Disbursements before 2020-01-28 convert the precursor community tokens one to one and are not new money |
| Checks | the descriptor's totals recomputed from the transfers: demurrage reclaimed 2021-02-01 to 2021-02-03, 352,834.00 against 352,834; `agent_out`, 6,172,074.95 against 6,172,075; the balance of all accounts except admin accounts, 19,414,222.25 from the flows against 19,419,736, and 19,416,434.84 from the users table's final balances. Balances rebuilt from the flows match `final_bal` to 0.01 for 54,883 wallets and differ for 83, by at most 1,000 |

## B110: A-share placements from 2017-02-15, their unlock batches and holders, and the stocks' daily bars

| | |
|---|---|
| Files | `data/raw/b110/rpt_seo_detail/count_5884_ps500/` (12 pages) and `data/raw/b110/rpt_lift_stage/count_31520_ps500/`: one table snapshot per directory, named by the server's row count when that run began, one JSON file per page of 500 rows; the stage table's earlier snapshots `count_31514_ps500` and `count_31515_ps500` sit beside it. `data/raw/b110/rpt_lift_gd/`: one JSON file per unlock batch with its holder rows, named by stock and unlock date. `data/raw/b110/daily_baostock/stock/`: one JSON file per stock with its rows and the date ranges asked for; `stock_basic_2026-09-15.json` beside it is the security list the windows are cut to. `data/raw/b110/fetch_manifest.json`: scope, table snapshots, counts and every named gap. `request_log.tsv` and `bars_log.tsv`: one line per request with its seconds and bytes. `data/cache/b110_bars.npz` is built from the stock files and rebuilt when any of them changes. The ranges B120's plans need are added to the same store by `experiments/b120_bars.py` with this script's fetch function and checks; after that run the store holds 2,225 stocks |
| Source | Eastmoney data center, `https://datacenter-web.eastmoney.com/api/data/v1/get` with `reportName` `RPT_SEO_DETAIL` (one row per offering), `RPT_LIFT_STAGE` (one row per unlock batch) and `RPT_LIFT_GD` (one row per holder in a batch). Daily bars from baostock: `query_history_k_data_plus` in the Python package `baostock` 0.9.30, `adjustflag` 3 (unadjusted) |
| Retrieved | 2026-09-16, two runs of `experiments/b110_fetch.py` |
| Caliber | `RPT_SEO_DETAIL`: `ISSUE_DATE` is the bid day T, the offering period opening two trading days earlier; `ISSUE_PRICE` in yuan; `ISSUE_NUM` and `ISSUE_SHARE_BEFORE` in shares; `ISSUE_WAY` `网下询价配售` is an offering priced by bids and `网下定价发行` one priced in advance, issues to buy assets included; `TOTAL_RAISE_FUNDS` and `NET_RAISE_FUNDS` are gross and net proceeds in yuan, net below gross in 1,769 of the 1,771 bid offerings and equal to gross in 565 of the 587 offerings priced in advance whose pricing text reads as an issue paying for assets; `PRICE_PRINCIPLE` and `LOCKIN_PERIOD` are free text, and the table carries no bids and no allocation by investor. `RPT_LIFT_GD`: `LOCK_MONTH` is the lock the rules gave the holder's class, and `ADD_LISTING_SHARES` the shares freed, counted on the unlock day. Bars: `volume` in shares and `amount` in yuan; prices printed to four decimals, with a tick of 0.01 yuan; a suspended day comes back as a row with `tradestatus` 0; `preclose` is the exchange's reference price after a split or dividend. Shanghai and Shenzhen only, so the 7 offerings on the Beijing Stock Exchange (codes starting 920) have no bars |
| Checks | 2,925 offerings of `SEO_TYPE` 1 with T on or after 2017-02-15. 6,195 unlock batches of placement shares from 2017-02-15, 308 of them unlocking after the fetch: holder rows for 6,194, and for one (300114, unlock 2017-12-12, 10 holders in the batch table) the holder table answers empty. Bars for 1,959 stocks over 1,780 date ranges, each answer checked before it is written (no row outside the range asked for, no answer ending more than 15 days short of either end for a stock listed through the range), 0 row conflicts. Against a calendar of every date on which any stock has a row, 1,750,658 stock-days are due and 0 are missing, 39,334 of them suspended. For one offering (301321, T 2017-07-12) the window falls before the stock's listing in the security list. The stage table grew from 31,514 to 31,520 rows during the day with the batches in scope unchanged |

## B115: 2018 US–China soybeans, the US basis, the Dalian futures, the Paranaguá indicator and the yuan

| | |
|---|---|
| Files | `data/b115/raw/`: `agtransport/grain_basis_soybeans_2016_2020_p000.json` (one page of rows); `dce/<year>_<product>.<zip or xlsx>` for corn, No. 1 soybeans, No. 2 soybeans and soybean meal, 2016 to 2020, twenty files; `fred/DEXCHUS.csv`; `cepea/soja_paranagua_series.xls`. `data/b115/raw/b115_soy_manifest.json` records per file the URL, bytes, SHA-256, retrieval time and the check the file passed, and `experiments/b115_soy_describe.py` refuses a file that differs from it. Fetched by `experiments/b115_soy_fetch.py` |
| Sources | USDA Agricultural Marketing Service, "Grain Basis" on the AgTransport open data platform, dataset `v85y-3hep` (`https://agtransport.usda.gov/resource/v85y-3hep.json`), the rows with `commodity='Soybeans'` and a week ending date in 2016-01-01 to 2020-12-31. Dalian Commodity Exchange, historical data page (`http://www.dce.com.cn/dalianshangpin/xqsj/lssj/index.html`), one file per product and year as linked there. Federal Reserve Board H.10 through FRED, series DEXCHUS (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS`). CEPEA/ESALQ, soybean indicator page (`https://cepea.org.br/br/indicador/soja.aspx`), series file `https://cepea.org.br/br/indicador/series/soja.aspx?id=92` |
| Retrieved | 2026-09-16, by script on a Windows build; the three 2017 Dalian workbooks served under `.csv` links in a second run the same day |
| Caliber, AgTransport | one row per market and week ending date. The platform's column descriptions, read from its metadata on 2026-09-16: `date` is the week ending date, `bid` the price in dollars per bushel, `futures_price` the CBOT price for soybeans in the contract month named in `contract_month`, `basis` the difference between bid and futures price, and `market_type` "Elevator Bid" for origins and "30-Day to Arrive" for destinations. Basis equals bid minus futures price on every row to `1.7e-15`. 1,619 rows over 15 markets. Destinations: Gulf - Louisiana 255 weeks across the five years, Great Lakes - Toledo 247, Atlantic Coast 48 from 2019-10-25, Portland (the Pacific Northwest) 14 weeks from 2020-08-21 to 2020-11-20. Origins: Illinois and Iowa 257 weeks each across the five years; nine others 54 to 61 weeks from 2019-10-25. The source is named per row: AMS Market News report JO_GR850 for Toledo and the Atlantic Coast, and with U.S. Wheat Associates price reports for the Gulf; JO_GR110 with U.S. Wheat Associates for Portland; SF_GR110 for South Dakota; a GeoGrain subscription for the other ten origins, Illinois and Iowa among them |
| Caliber, Dalian | one row per contract and trading day: contract, date (YYYYMMDD), previous close, previous settlement, open, high, low, close, settlement, two changes, volume, turnover and open interest; prices in yuan per tonne, the contracts' quotation unit. Four layouts: 2016 files are zip archives of a gb18030 csv with `ROWNUM` and `成交金额`; 2017 files are workbooks (corn inside a zip under a `.csv` name, the other three served under `.csv` links); 2018 and 2019 workbooks carry an empty first column and `成交额`, and the 2018 sheets run on for about 26,000 empty rows; the 2020 soybean and meal workbooks drop `ROWNUM`. Every file's contract prefix (c, a, b, m) matches its product and its dates its year. No. 2 soybeans traded on 165, 205 and 197 trading days in 2016, 2017 and 2018, and its 2018 file ends on 2018-12-14; it traded on every trading day of 2019 and 2020. The other three products traded on every trading day |
| Caliber, FRED | yuan per US dollar, noon buying rates in New York for cable transfers, business days from 1981-01-02; `.` where no rate was set, 515 of 11,921 rows, 57 of 1,305 in 2016 to 2020 |
| Caliber, CEPEA | the Paranaguá soybean indicator, daily from 2006-03-13 to 2026-09-16, 5,115 rows in strictly increasing order: `Data` (dd/mm/yyyy), `À vista R$` and `À vista US$`, in reais and in US dollars per 60 kg bag. 1,246 days in 2016 to 2020. The workbook's compound file shares sectors between the root storage and the workbook stream; xlrd calls that corruption and reads the whole sheet when told to ignore it. The file is the length the server announced |
| Checks | the AgTransport rows equal the platform's count for the same query, 1,619; every Dalian file's contract prefixes and dates match its product and year; the CEPEA file's last two days match the indicator page on 2026-09-16, 160.59 and 31.16 on 15/09 and 161.88 and 31.37 on 16/09 |

## B115: 2018 US sorghum and corn FOB prices, the US Grains Council's weekly tables

| | |
|---|---|
| File | `data/b115_sorghum_fob.json`: 1,270 cells from 123 weekly issues, each cell with its issue date, table (corn or sorghum), port, delivery month, basis as printed and as read, futures month and flat price; each issue with the URL of its PDF, the PDF's page count and the pages of the two tables, and for 2018-02-22 to 08-02 also the issue's page 5 and the two table images; the dated documents with their URLs; a coverage block |
| Source | US Grains Council, Market Perspectives, the Yellow Corn FOB and Sorghum FOB tables. PDFs of the issues from 2016-01-07 to 2018-08-02 under `https://grains.org/lta/wp-content/uploads/sites/6/`, named `MP-MMDDYYYY.pdf`, a few with `_0` before the extension; images of the 2018-02-22 to 08-02 tables under `https://grains.org/wp-content/uploads/` |
| Retrieved | 2026-09-17, read in a browser: the text layer of each PDF, and the 2018 images at magnification. The page text was carried over in blocks, each checked by hash against the browser's copy |
| Caliber | flat prices in US$/t FOB vessel, #2 YC for corn (Gulf and PNW) and #2 YGS for sorghum (NOLA and Texas); basis in US$/bu over the CBOT corn futures month named by its letter (H March, K May, N July, U September, Z December); corn and sorghum bushels both 56 lb, so a flat price is the futures price plus the basis, times 39.37. Delivery months as printed, FH and LH marking the halves of a month, and a few 2016 and 2017 labels carry a day (March 5, March 25, February 25). Three Gulf corn bases of 2017-08-24 are printed without a decimal point (`50+U`, `52+Z`, `61+Z`) and are read as 0.50, 0.52 and 0.61. Lines printed under a table to say another table is left out that week are not price rows and are not transcribed |
| Coverage | 47 issues in 2016, 46 in 2017, 30 in 2018 to 08-02. No PDF found for 2016-02-18, 06-09, 07-21 and 11-10, or for 2017-01-05, 03-16, 05-18 and 09-21; no issue on 2016-11-24, 2017-11-23, 2017-12-28 and 2018-01-25. The images linked from the 2017 issue pages no longer open |
| Checks | each PDF's Week Ending date equals its issue date, 123 of 123; the 231 cells of 2018-02-22 to 08-02 read from the images equal those read from the text layer in every cell; `experiments/b115_sorghum_step.py` flags 19 cells whose flat price and basis put the futures price more than a cent a bushel from the median over their issue and futures month, and 3 cells hung on a futures month that ends before their delivery month |

## B30-4, the itch.io tag directory

| | |
|---|---|
| Source | `https://itch.io/tags`, sixteen pages, retrieved 2026-09-16 |
| Cache | `data/raw/itch_tags/page_NN.html`, one file per page, fetched once and not refetched |
| Fetcher | `data/fetch_b30_4_itch_tags.py`; record `results/b30_4_itch_tag_census.json` |
| What a row is | one directory cell: a display name, a slug, a scope, a kind (`tag`, `genre` or `feature`) and a count of projects |
| **Definitional basis of the count** | **every project type at once.** `tag-horror` reads `114k` here while `/games/tag-horror` reads `92,386`, and `genre-sports` reads `14.5k` here while `/games/genre-sports` reads `13,769`. **A count from this file must not be placed in the same column as a count read off a single-scope browse page** |
| Resolution | printed to three significant figures with a `k` or `m` suffix above ten thousand, exactly below it. `500` of `616` rows are exact, and they are the small ones |
| Coverage | `616` cells, none skipped: `605` tags, `10` genres, `1` feature |
| Checks | ten counts read directly off the directory before the fetcher existed are reproduced exactly, `no-ai` `505k`, `2d` `430k`, `horror` `114k`, `pixel-art` `243k`, `singleplayer` `321k`, `3d` `177k`, `retro` `102k`, `dating-sim` `7,246`, and the genres `adventure` `213k` and `visual-novel` `65k`. An earlier parse failed eight of those ten while every aggregate on the run looked correct |
| Prices | **none retrieved.** This file carries no price field by design; the split of the vocabulary is applied to the names alone and recorded before any price band is pulled |

## B120: A-share placement announcements on cninfo from 2020-02-14, their titles, and the PDFs of subscription agreements, review notices, adjustments and plan documents

| | |
|---|---|
| Files | `data/raw/b120/cninfo/<keyword>/<setting>/`: one JSON file per answer page, named by month window and page. `szse_all_any` holds the census keywords asked with no category (终止, 认购协议, 定价基准日 from 2020-02-14, 调整 from 2026-05-01 to 2026-08-31, and 失效, 撤回, 不予, 否决 from 2020-02-14), `szse_all_zf` the placement category (预案, and the probe's other keywords), `sse_*` the probe's second setting. `data/raw/b120/pdf/<announcementId>.pdf`. `data/raw/b120/request_log.tsv`: one line per request with its seconds and bytes. `data/raw/b120/printout_<time>.txt` and `plans_printout_<time>.txt`: what each run of `b120_fetch.py` and `b120_plans.py` printed. `data/raw/b120/plan_documents_wanted.txt`: the plan documents `b120_plans.py` still needs read, rewritten on every run, which `b120_fetch.py --plan-pdfs` fetches. `data/raw/b120/bars_manifest.json`: what `b120_bars.py` asked of baostock for the plans' windows, what came back and what is still missing; `bars_printout_<time>.txt` its printout. The bars themselves go into the B110 store, `data/raw/b110/daily_baostock/stock/`. `data/raw/b120/readings_printout_<time>.txt`: what `experiments/b120_readings.py` printed; `data/cache/b120_bars.npz` is the compact copy of the bars the plans need, rebuilt when one of those store files changes. `data/cache/b120_pdf_text.jsonl.gz`: the text of each PDF, read again for a PDF whose size or modification time changed |
| Source | cninfo announcement search, `http://www.cninfo.com.cn/new/hisAnnouncement/query` (POST: `column` szse, `tabName` fulltext, `plate` empty, `searchkey` one keyword, `seDate` one month, `category` empty or `category_zf_szsh`, 30 rows a page). PDFs from `http://static.cninfo.com.cn/` followed by the row's `adjunctUrl` |
| Retrieved | 2026-09-16 and 2026-09-17, `experiments/b120_probe.py` and `experiments/b120_fetch.py` |
| Caliber | `announcementTime` is milliseconds, read as a day in China time (UTC+8); `adjunctSize` is kilobytes. Titles carry `<em>` search marks, stripped before reading. A keyword matches words, not strings: `认购协议` returns titles with 认购 and 协议 apart. The probe's two settings, `szse` and `sse` columns, return the same rows. The placement category holds the plans and few of the announcements that end them, so the census is asked with no category and the titles are sorted locally. A month that ended within seven days of a run is asked again, and a page that fails its check is kept under an `.expired` name. A PDF is kept only with its header and end mark |
| Checks | Census from the first run, the four keywords of 2026-09-16: 23,659 announcements over 244 month windows, none missing; 2,255 PDFs, one (announcement 1214636830) not retrieved after three tries. The placement category: 10,879 rows, 2,532 first versions of a plan document. Two answers known before the run are printed against the census: the companies the press named among the plans moved to first-day pricing in June and July 2026, and the completed placements priced in advance in the B110 offering table, each linked to its plan or named. Second run, 2026-09-17: the keywords 失效, 撤回, 不予 and 否决 over 80 month windows (446, 909, 203 and 6 rows, each under the cap of 9,000, every page fetched), 24,717 census announcements; 1,603 more PDFs with announcement 1214636830 among them, 3,858 on disk, the 1,461 plan documents to read included (the 1,401 with no agreement announcement near them and a spread of 60 with one); 5 failed attempts, each retrieved on a retry. Third run, 2026-09-17: the 56 plan documents on the wanted list, all 58 on it read. Daily bars for the windows of 949 plans over 752 stocks, from 60 days before a plan's first date to 10 days after its end: 595 ranges asked, 594 fetched with 0 row conflicts, one (002011, 2021-09-18, a Saturday) answered with no rows; 7 codes on the Beijing Stock Exchange have no bars. Fourth run, 2026-09-17, the readings and the criteria: `results/b120_readings.json`, 647,476 bytes, sha256 5f597ed3, carrying the configuration it ran under and a coverage row for each of the 949 plans with the source of every field. Two of its seven criteria fail and both ask the instrument: 34 plans whose locked price cannot be sourced, named, and one completed placement (600029) whose plan is not found |

## B30-4, the itch.io price enumeration and the pages behind it

**Source.** `https://itch.io/games/store/tag-<slug>` and its pagination, plus
`https://itch.io/games/<four price filters>/tag-<slug>` for the counts, plus a sample
of project pages at `https://<seller>.itch.io/<project>`.

**Retrieved** 2026-09-16 and 2026-09-17, from a US locale with no account signed in.

**Records.** `results/b30_4_itch_tag_census.json` (the tag vocabulary and its counts),
`results/b30_4_itch_counts.json` (five published counts per market tag),
`results/b30_4_itch_prices.json` (`26,353` projects with their posted price),
`results/b30_4_price_spotcheck.json` (the listing against the project's own page).

**Definitional basis, and it is the site's own wording.** Each price is the project's
**posted minimum**, which the site prints in the title attribute beside it as
`Pay $X or more for this game`. **It is not a transaction price**: a buyer may pay
above it, and a project on sale is recorded at its sale price with the discount
percentage kept alongside. `1,144` projects were on sale and `293` of those were
discounted to nothing, which leaves them with no recoverable posted price.

**Currency is the seller's, not a display conversion**, and that was checked rather
than assumed: `83%` of the euro prices land on a round euro point, `81%` of the
pound prices on a round pound point, against a `90%` baseline in dollars, and a
search over every exchange rate between `0.70` and `1.10` finds none that explains
them better than one. `USD 24,423`, `EUR 1,177`, `GBP 507`, `BRL 81`, and twelve
projects priced in `¥`, **which is left unconverted because the symbol is shared by
two currencies about twenty times apart in value**.

**Counts on the same tag are not all equally sound.** The `paid` count matched a full
walk of the pages on every one of the `151` market tags, to zero on the nine tags
where `free + paid` does not equal `total`. **So the fault on those nine sits in
`free` or in `total`**, and the treatment variable is drawn from `total`, which is
recorded as located rather than resolved.

**What is not in the repository and why.** The fetched HTML stays on the machine that
fetched it, `222 MB` of it, excluded by the `data/**` rule. **It carries project
descriptions, which are text their sellers wrote.** The records carry titles, prices,
currencies, genres, sale states and seller handles, **which are facts about a public
listing rather than anyone's writing.**

**Why the snapshot is published at all.** The listings change daily, so a later run
reads a different column. **Without the snapshot the reading taken from it could not
be checked by anyone**, including by a later session of this project.

## B121: 2007-09 US crisis facilities, the rates around them, and the banks that borrowed

| | |
|---|---|
| Files | `data/raw/114040-V1.zip`: replication package of Taylor and Williams, *A Black Swan in the Money Market* (openICPSR 114040), placed by hand; its workbook `TaylorWilliamsData.xls` carries daily 3-month LIBOR (`US0003M`), 3-month OIS (`USSOC`), TAF balances and the authors' own TAF event dummies, 1995-11-16 to 2008-08-08, with a Notes sheet naming every column. `data/raw/b121/*.csv` and `*.done`: FRED series (`TEDRATE`, `DTB3`, `DFF`, `DFEDTAR`, `DFEDTARU`, `DED3`, `SWPT`, `TERMAUC`, `WTERAUC`, `WABCMMF`, `H0RESPPALDDNWW`, `WLCFLPCL`, `TERAUC1690`, `WCPFF`, `COMPOUT`, `ABCOMP`, `DCPF3M`, `DCPN3M`, and the probes that answered), each with a completion marker holding its size, sha256 and date range; `manifest.json`, `timings.json`. `data/raw/b121/taf.csv`, `amlf.csv`, `cpff.csv`, `cbls.csv` and their `_definitions.csv`: the Board's transaction-level disclosures. `data/raw/b121/press/*.html`: Board press releases listed on the Board's TAF and swap-line pages (five first saved as 369-byte redirect stubs, kept under `.expired_redirect_stub`). `data/raw/b121/nyfed_Crisis_Timeline.pdf` and `nyfed_IRCTimelinePublic.pdf`, with `pdftotext` copies. `data/raw/b121/callreport/`: nine single-period Call Report bulk archives (2007Q2 to 2007Q4, 2008Q2, 2008Q3, 2009Q1 to 2009Q4) and the 2007 and 2008 annual subset archives. `data/cache/b121_call_report.json`: the panel 2007Q1 to 2010Q2 built from those and from the archives in `data/raw/CallReport/` |
| Source | FRED `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>`. Board `https://www.federalreserve.gov/newsevents/files/<facility>.csv`, linked from `/newsevents/reform_<facility>.htm`. Press releases `https://www.federalreserve.gov/newsevents/press/monetary/<date><letter>.htm` (redirecting to `/newsevents/pressreleases/monetary<date><letter>.htm`). New York Fed `https://www.newyorkfed.org/research/global_economy/policyresponses.html`. FFIEC CDR Bulk Data Download, products Call Reports -- Single Period and Call Reports -- Balance Sheet, Income Statement, Past Due -- Four Periods, Tab Delimited |
| Retrieved | 2026-09-17 to 2026-09-22; FRED and the Board by `scripts/fetch_b121.py`, the FFIEC archives through the browser on 2026-09-22, the replication package by hand |
| Caliber | FRED rates in percent. `TEDRATE + DTB3` returns the workbook's `US0003M` within 0.50 bp on 397 overlapping days; `DED3` does not (largest gap 38.8 bp). Board facility files: amounts in millions of dollars, one row per loan or swap transaction; every winner of one TAF auction borrows on the same day at the same rate. Call Report archives read with `experiments/b59_call_report.py`'s reader. The single-period archives for 2007Q2 to 2008Q3 and for 2009 in `data/raw/CallReport/` are zero bytes; the ones here were fetched again and are whole. They are kept apart from `data/raw/CallReport/` so that folder never holds two archives for one quarter |
| Checks | Every FRED and Board file parses whole and ends in a newline; a body that does not is kept under `.bad_<n>` with a note. Each FFIEC archive passes `zipfile.testzip`. The panel reads all 14 quarters 2007Q1 to 2010Q2, each carrying the RC-K average (3353) |

## B123: two networks' US interchange schedules, the Board's average fees under Regulation II, and Visa's Australian domestic page before the October 2026 caps

| | |
|---|---|
| Files | United States, read by the station: `data/raw/b123/visa/visa-usa-interchange-reimbursement-fees_2026-04-18.pdf` (877,295 bytes, 28 pages); `data/raw/b123/mastercard/merchant-rates-2026-2027-april2026.pdf` (285,560 bytes, 11 pages) and `merchant-rates-2025-2026.pdf` (240,198 bytes, 11 pages) beside it; `data/raw/b123/fed/Avg_IF_by_PCN.csv` (42,576 bytes). Australia, saved on 2026-09-22 and not yet read by any station: `data/raw/b123/visa_au/visa-au-domestic-interchange_2026-09-22.html` (605,210 bytes), `visa-ap-intra-regional-interchange_2026-09-22.html` (47,459 bytes) and `visa-inter-regional-interchange_2026-09-22.html` (45,296 bytes); `data/raw/b123/mastercard_au/` with the credit (73,810 bytes, 3 pages), debit (85,796 bytes, 3 pages) and prepaid (49,613 bytes, 2 pages) schedules, each effective 2026-04-17; `data/raw/b123/eftpos/auspayplus-eftpos-interchange-fees_2026-09-22.html` (244,503 bytes); `data/raw/b123/rba/rba-conclusions-paper_2026-03-31_upd-2026-06-19.pdf` (3,253,222 bytes, 202 pages). `data/raw/b123/b123_manifest.json`: URL, bytes, SHA-256, the check passed and the retrieval time for all twelve |
| Source | Every URL is in `experiments/b123_fetch.py`'s plan. Visa `https://usa.visa.com/dam/VCOM/download/merchants/visa-usa-interchange-reimbursement-fees.pdf`. Mastercard `https://www.mastercard.com/content/dam/mccom/us/business/documents/merchant-rates-2026-2027-april2026.pdf` and `https://www.mastercard.us/content/dam/public/mastercardcom/na/us/en/smb/documents/merchant-rates-2025-2026.pdf`. Board `https://www.federalreserve.gov/paymentsystems/files/Avg_IF_by_PCN.csv`. Visa Australia `https://www.visa.com.au/about-visa/interchange.html`, `/ap-intra-regional-interchange.html` and `/inter-regional-interchange.html`. Mastercard Australia three PDFs under `https://www.mastercard.com/content/dam/mccom/aus/data-source/merchant-interchange-rates/`, linked from `https://www.mastercard.com/au/en/business/support/merchant-interchange-rates.html`. Australian Payments Plus `https://www.auspayplus.com.au/solutions/eftpos-interchange-fees`. Reserve Bank of Australia `https://www.rba.gov.au/payments-and-infrastructure/review-of-retail-payments-regulation/2026-03/conclusions-paper/pdf/conclusions-paper.pdf` |
| Retrieved | 2026-09-22. Visa's US schedule and the Board's table by `experiments/b123_fetch.py`; everything else saved from a browser and brought in with `--import`, which applies the same check as a fetch and records the file as a browser-saved copy of its URL. Mastercard's servers refuse a scripted request; the Australian pages were saved by hand in the same sitting |
| Caliber | Interchange as each network prints it: a percentage of the sale plus a fixed amount in dollars, with any printed cap or minimum. Visa stars the regulated cap for the fraud-prevention cent; Mastercard prints the fraud adjustment as a separate row and calls exempt issuers "Unregulated". The Board's table: average interchange fee per transaction and average transaction amount, by network, for covered and exempt issuers, by year. The Australian files are the schedules in force before the caps of 2026-10-01, and every one of those URLs is undated, so each is served over on the day the new rates take effect. Visa Australia domestic: credit effective 2026-06-01, debit for multi-network cards effective 2025-07-12 and for single-network cards effective 2025-12-01, prepaid effective 2023-06-01, account funding effective 2026-03-01, each exclusive and inclusive of GST; the two foreign-card pages print one table each, three fee programs by four card tiers. Mastercard Australia: all three effective 2026-04-17, exclusive and inclusive of GST. eftpos: cents or a percentage per transaction, by card type, interchange category and channel, with a Legacy tab beside the current one. The conclusions paper carries the varied standards as its Appendix D |
| Checks | Each PDF starts with `%PDF-`, has `%%EOF` in its last 2,048 bytes and opens in pymupdf with text on its first pages; the CSV parses whole and ends in a newline. `b123_fetch.py --verify` compares every file with its manifest hash, and the station's bookkeeping criterion repeats that on every run. Each saved page decodes as UTF-8, closes its html element and carries its rate tables, and each measured the same byte count the live URL reported the same evening. The conclusions paper opens at 202 pages and its metadata carries the 2026-06-19 update. `b123_fetch.py --verify` reports all twelve OK |

## B124: US liver transplants, donors, waitlist candidates and organ dispositions from SRTR, as released under FOIA to The Markup

| | |
|---|---|
| Files | `data/raw/investigation-organs-main.zip` (135,935,682 bytes, SHA-256 `389787bc1311cebfb4b060777f5b01e846c45657f39fa7a721de2307a2dfa164`): the repository `the-markup/investigation-organs` as a zip of its main branch (last pushed 2024-02-08, BSD 3-Clause licence), placed by hand. Under `01_data/raw/` inside it: liver transplants `04_transplant/TX_LI_22F218Records(2of2)-redacted.csv.gz` (192,982 rows, 309 columns), donors `03_donor/22F123_Records_Redacted.csv.gz` (250,941 rows, 257 columns), waitlist candidates `02_candidate/Updated_CAN_LIIN_22F218Records(1of2)-redacted.csv.gz` (341,208 rows, 173 columns), organ dispositions `06_don_disp/DONDISPOSITION_22F167Records-redacted.csv.gz` (1,048,575 rows, 18 columns), the institution table `01_hospitals/22F138_Institution.csv` (712 rows) and the donor-hospital crosswalk with facility coordinates. `data/raw/b124/nhsbt/nlos-48-month-monitoring-report.pdf` (1,194,241 bytes, 61 pages, SHA-256 `0544aa3fecfba36455498c9717925f68dbcf4e55727fde108d81162e065cd3ff`): NHS Blood and Transplant's 48-month monitoring report on the National Liver Offering Scheme introduced 2018-03-20, placed by hand |
| Source | `https://github.com/the-markup/investigation-organs`. The records are SRTR's, released by HRSA under FOIA to The Markup and The Washington Post in 2023. NHSBT `https://nhsbtdbe.blob.core.windows.net/umbraco-assets-corp/28577/3-national-liver-offering-scheme-48-month-monitoring-report.pdf` |
| Retrieved | 2026-09-22, the zip of the main branch saved from a browser |
| Caliber | One row per transplant, donor, candidate or organ disposition. The transplant file carries the donor's OPO (`DON_OPO_CTR_ID`), the recipient's centre (`REC_CTR_ID`), the recipient's permanent state and the share type (`REC_PB_SHARE_TY`); the institution table maps each centre to its state and OPTN region. The disposition file writes dates as month/day/two-digit year |
| Checks | `zipfile.testzip` passes on all 197 members, and no member is a Git LFS pointer. Each `.gz` decompresses whole with its gzip CRC and length intact. The transplant, donor, candidate and institution row counts match the counts in The Markup's methodology. The disposition file holds 1,048,575 data rows plus a header, which is Excel's row limit of 1,048,576, and its dates cover 1987-10 to 1997-05 and 2013-01 to 2022-03 with nothing in between, so it was most likely cut at that limit before release; its 2013 to 2022 rows are to be checked against the transplant file's yearly liver counts before any use |

## B125: GSA City Pair Program contract fares, fiscal years 2026 and 2027

| | |
|---|---|
| Files | `data/raw/b125/gsa/awards_2026.csv` (2,658,635 bytes, 16,270 non-blank rows, 23 columns) and `data/raw/b125/gsa/awards_2027.csv` (2,880,153 bytes, 17,386 non-blank rows, 24 columns). `data/raw/b125/b125_manifest.json`: URL, bytes, SHA-256, the check passed and the retrieval time |
| Source | `https://www.gsa.gov/system/files/awards_2026.csv` and `awards_2027.csv` beside it, linked from GSA's City Pair Program page |
| Retrieved | Fiscal 2026 on 2026-09-22 by `experiments/b125_fetch.py`; fiscal 2027 on 2026-09-23 saved from a browser and brought in with `experiments/b125_fetch.py --import`, which applies the same check as a fetch |
| Caliber | One row per city pair and awarded carrier: `YCA_FARE` (the unrestricted government fare), `_CA_FARE` (the capacity-controlled one), `BUSINESS_FARE` and `_CP_FARE`, in dollars, `0` where no such fare is awarded, with `PAX_COUNT` and the award's `EFFECTIVE_DATE` and `EXPIRATION_DATE`: 2025-10-01 to 2026-09-30 for fiscal 2026, 2026-10-01 to 2027-09-30 for fiscal 2027. The fiscal 2027 file carries one more fare column, `_CN_FARE`; the other 23 columns are the same |
| Checks | Each file parses whole with every row at the header's width and ends in a newline; fiscal 2026 also matches the server's Content-Length |

- `data/raw/b125/aena/guia-tarifas-aena_2026-08.pdf`: Aena, Guía de Tarifas, August 2026 edition, 128 pages, 1,714,506 bytes, SHA-256 in `data/raw/b125/b125_manifest.json`. Taken 2026-09-23 with `curl.exe` from https://www.aena.es/doc/detalleprensa/260801-guia-tarifas-aena-agosto-2026.pdf and entered with `experiments/b125_fetch.py --import` (the Satellite link on Aena's prices page serves a cookie page to a script). Caliber: public charges per departing passenger in euros; section 2.2 gives the passenger, PMR and security charges by airport group, separately for EEE and international flights (2.2.1), flights between the Canary and Balearic Islands, Ceuta or Melilla and the Peninsula (2.2.2), and inter-island flights (2.2.3); page 18 also prints the 40% reduction for connecting passengers and the 20% November-to-March reduction at Palma, Menorca, Ibiza and Son Bonet.

- `data/raw/b121/tafres/`: Board of Governors TAF yearly archive pages (`taf_2007.htm`, `taf_2008.htm`,
  `taf_2009.htm`), every auction announcement and results release linked from them, the four 2010 pages, and the
  TAF terms and conditions (`tafterms.htm`). Fetched 2026-09-23 from https://www.federalreserve.gov/monetarypolicy/.
  Results releases print offering, total bids, accepted bids, bid/cover, bidders and stop-out; announcements print
  the per-institution maximum award and the minimum bid rate. One release (2008-08-25) prints the accepted amount
  without its unit and one (2008-09-22) with a space after the dollar sign; both are read as billions.

- `data/raw/b121/lit/ssrn-1923696.pdf`: Filipovic, D. and Trolle, A. B., "The term structure of interbank risk",
  SSRN 1923696 (published in Journal of Financial Economics 109(3), 2013, 707-733), 98 pages, downloaded
  2026-09-23 from https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1923696 without a login. Figure 4 Panel A
  (page 56) is read from its vector drawing paths; see `experiments/b121_ft_default.py`. Used as literature for the
  default component of the three-month spread, not as a measurement of this station.

## B128: euro area bank rates by country, key rates, Eurosystem borrowing by country

Fetched 2026-09-23 by `scripts/fetch_b128.py` from the ECB Data Portal SDMX API
(https://data-api.ecb.europa.eu/service/data), start period 2003-01, into `data/raw/b128/`; checksums and per-series
first and last periods are in `data/raw/b128/manifest.json`, request times in `timings.json`.

- `mir_B_*.csv`: MFI interest rate statistics (MIR), new business, monthly, every reference area in one request per
  shape. Ten shapes, all variable or fixed for up to one year: loans to corporations up to EUR 0.25M, EUR 0.25M to
  1M and over EUR 1M; loans to households for house purchase, for consumption and for other purposes (no Irish
  key); deposits with agreed maturity up to one year from households and from corporations; overnight deposits
  from households and from corporations. Unit: percent per annum. All 53,407 values are whole multiples of 0.01.
  The two small corporate-loan buckets start in 2010-06.
- `bsi_eurosystem_borrowing.csv`: BSI, deposit liabilities of MFIs excluding the ESCB vis-a-vis the euro area
  central bank sector (S.121), end of period stocks, EUR millions, from 1999 per the source (fetched from 2003).
- `ilm_ltro.csv`, `ilm_mro.csv`: internal liquidity management, longer-term and main refinancing operations by
  national central bank, EUR millions, from 2016-06.
- `fm_keyrates.csv`: ECB key interest rates (FM dataset), dates of change and levels; the dates are effective dates.
- `mir_keys.csv`, `ilm_keys.csv`, `mir_u2_titles.csv`: the key lists and euro area series titles read before choosing.

## B129: the Berlin rent cap law, its statute text, the Berlin rent index and the 2019 Mietspiegel

Fetched 2026-09-23 by `experiments/b129_fetch.py` into `data/b129/raw/`; URLs, sizes and SHA-256 are in
`data/b129/raw/manifest.json`. Every file is a published document at a fixed address.

- `gvbl_2020_nr6_mietenwog.pdf`: Gesetz- und Verordnungsblatt fuer Berlin 76. Jg. Nr. 6, 22.02.2020, S. 49-56,
  from berlin.de. Article 1 is the MietenWoG Bln; the §6 table is read from it (B129-1). The first three requests
  were answered 429 and the file was fetched later in the same session with an ordinary request.
- `abgh_d18_2347.pdf`, `abgh_d18_2437.pdf`: Abgeordnetenhaus Berlin, Drucksache 18/2347 (the Senate's bill,
  28.11.2019) and 18/2437 (the committee's recommendation, 23.01.2020), from parlament-berlin.de. 18/2437 amends
  §6 only in Abs. 4 and 5, so the table in 18/2347 is the enacted table; both are kept as a second route to it.
- `vpi_berlin_2020m12.xlsx`, `vpi_berlin_2022m09.xlsx`, `vpi_berlin_2022m09.pdf`: Amt fuer Statistik
  Berlin-Brandenburg, Statistischer Bericht M I 2 - m, "Verbraucherpreisindex im Land Berlin", December 2020 and
  September 2022 issues, from statistischebibliothek.de. Sheet 4, "Preisindex fuer Wohnungsmieten Land Berlin
  (2015 = 100)": Nettokaltmieten overall and split into "Wohnung, gebaut bis 1948" and "gebaut ab 1949 und
  Einfamilienhaus", monthly, printed to one decimal. The two workbooks agree on every month they share
  (2019-01 to 2020-12), which the reader asserts.
- `mietspiegeltabelle2019.pdf`: Berliner Mietspiegeltabelle 2019 (Stichtag 01.09.2018), from berlin.de. Net cold
  rent in EUR per m2 per month, median and 3/4 range per cell; 12 rows (size x location) by 8 age bands. Empty
  cells mean fewer than 10 rents. Cells are assigned to row and column by their position on the page.
- `mietspiegel2019_ergebnisbericht.pdf`: the 2019 Mietspiegel's methods and results report. Not read yet.
- `bgb_556f.html`: BGB §556f from gesetze-im-internet.de (the Mietpreisbremse's exemption for dwellings first used
  and let after 1 October 2014).
- `hahn_2023_rent_freeze.pdf`: Hahn, A. M., Kholodilin, K. A., Waltl, S. R. and Fongoni, M., "Forward to the Past:
  Short-Term Effects of the Rent Freeze in Berlin", Management Science, 2023, doi:10.1287/mnsc.2023.4775, CC BY-NC
  4.0, open copy from the University of Cambridge repository. Tables 1, 5 and 6 are transcribed into
  `experiments/b129_readings.py`. Used as literature (a published difference-in-differences on commercial ad data),
  not as a measurement of this station.

- `eba_pgs_volumes.csv`: EBA Risk Dashboard statistical annex, "Newly originated loans and advances subject to public
  guarantee schemes, volumes bn EUR", parsed from the text tables of the Q2 2021 dashboard (page 40, 2020-09 to
  2021-06) and the Q4 2021 dashboard (page 49, 2021-03 to 2021-12), both saved in `data/raw/b128/lit/`; each row
  keeps its file and page. Where the two vintages overlap the earlier one is used; they differ in three cells
  (DE 2021-06, DK 2021-03, HU 2021-06). The sample is about 160 large banks, not the whole banking system.
- `lit/`: ECB speech of 2016-07-28, ECB Decision 2014/34, the ECB TLTRO page, ECB Occasional Paper 257 (guarantee
  envelopes, tables A.3 and A.4), the EBA thematic note on moratoria and public guarantees (2020), and the two EBA
  dashboards, all fetched 2026-09-23 from the issuers' own sites.

## B131: interest before and after FISIM allocation by sector, deposit and loan stocks, ESA 2010 chapter 14

Fetched 2026-09-24 by `experiments/b131_fetch.py` into `data/raw/b131/`; URLs, sizes and SHA-256 are in
`data/raw/b131/manifest.json`.

- `nasa_10_nf_tr_d41.json`: Eurostat non-financial sector accounts, annual, items D41 (interest, after FISIM
  allocation) and D41G (total interest before FISIM allocation), sectors S14_S15 and S11, paid and received,
  current prices, million euro, every country and year published. FISIM on deposits is D41 received less D41G
  received; FISIM on loans is D41G paid less D41 paid (ESA 2010 14.11; the ECB box below uses the same
  definitions). These are derived by the statistical offices; the reference rate each office uses is not in the file.
- `nasa_10_f_bs_dep_loans.json`: Eurostat financial balance sheets, annual, items F22 (transferable deposits),
  F29 (other deposits) and F4 (loans), sectors S14_S15 and S11, assets and liabilities, non-consolidated,
  million euro. Stocks at end of year; ESA 14.07 averages stocks over four quarters, so a ratio of FISIM to these
  stocks is not the margin the office used.
- `nasa_10_nf_tr_b6g_p3.json`: household disposable income (B6G) and final consumption expenditure (P3),
  S14_S15, current prices, million euro.
- `esa2010_ch14.html`: ESA 2010 chapter 14 as Eurostat publishes it (Regulation (EU) No 549/2013, Annex A).
- `ecb_eb_2023_8_box5.html`: ECB Economic Bulletin 8/2023, box "A primer on measuring household income",
  read as literature, not as a measurement.

## B130: Singapore resident households by tenancy and dwelling type, income by dwelling type, HDB key statistics and rules

Fetched 2026-09-24 by `experiments/b130_fetch.py` into `data/b130/raw/`; URLs, sizes and SHA-256 are in
`data/b130/raw/manifest.json`. Every file is a published table, report or rule page at a fixed address.

- `singstat_m810401.json`: Singapore Department of Statistics, table M810401 "Resident Households By Tenancy,
  Annual", from the SingStat Table Builder API. Counts of resident households, owner-occupied and rented, and the
  owner-occupied share (per cent, printed to 0.1) by type of dwelling: HDB total and by flat size, condominiums and
  other apartments, landed properties, other. 1980, 1990, 1995 and every year 2000-2025. Resident households are
  those whose reference person is a citizen or permanent resident; the total also counts households occupying a
  dwelling free of charge, so owner-occupied and rented do not sum to it.
- `dgs_households_by_dwelling.json`: Resident households by type of dwelling, annual (counts), from data.gov.sg
  (resource `d_edf8bb4773c25dd16b8b6875fd0b52da`, adapted from SingStat).
- `dgs_income_per_member_by_dwelling.json`: Average monthly household employment income per household member,
  excluding employer CPF contributions, among resident employed households, by type of dwelling, 2000-2023, in
  dollars, from data.gov.sg (resource `d_c49b6cc84ccab3a0523ad15a907e57be`).
- `hdb_key_statistics_2024_2025.pdf`: Housing & Development Board, Annual Report 2024/2025, Key Statistics
  (27 pages). Read: p. 7 share of the resident population living in HDB flats; p. 10 active cases for renting out
  of flat as at 31 March 2025; p. 15 dwelling units under management, sold and rental, by flat type.
- `hdb_renting_out_flat_eligibility.html`: HDB, "Eligibility for Renting Out a Flat" (owner must be a citizen and
  have met the minimum occupation period; non-citizen quota for whole-flat rental, 8 % by neighbourhood and 11 %
  by block).
- `hdb_buying_couples_and_families.html`: HDB, "Couples and Families" (flat purchase by citizen or permanent
  resident households).

Added 2026-09-25 for a side question (what the resale price of a bound flat follows), same fetcher and manifest:

- `dgs_hdb_resale_price_index.json`: HDB Resale Price Index (1Q2009 = 100), quarterly, 1990-Q1 to 2026-Q2, from data.gov.sg
  (resource `d_14f63e595975691e7c24a27ae4c07c79`). Stratification method to 3Q2014, stratified hedonic regression from 4Q2014.
- `dgs_ura_private_price_index.json`: URA Private Residential Property Price Index (2009-Q1 = 100), quarterly, 1975-Q1 to
  2026-Q2, by property type (All Residential, Landed, Non-Landed), from data.gov.sg (resource `d_97f8a2e995022d311c6c68cfda6d034c`).
- `dgs_median_income_fulltime.json`: MOM, median gross monthly income from employment of full-time employed residents,
  including and excluding employer CPF, annual (June), 2001-2025 with 2005 absent, from data.gov.sg
  (resource `d_9cd9c40f22a4e45cac8f8b9d895fd5ce`).

- `dgs_resale_monthly_totals.json`: resale transactions registered per month, 2018-01 to 2022-09, each the `total` of one
  filtered query (`filters={"month": ...}`) on data.gov.sg "Resale flat prices based on registration date from Jan-2017
  onwards" (resource `d_8b84c4ee58e3cfc0ece0d773c8ca6abc`), written by `experiments/b130_side_buyers.py`. First-timer
  families who bought resale flats are transcribed in that script from MND's written answer to PQ 2568, 9 Jan 2023, Table 1A.

- `dgs_cpf_contributions_annual.json`, `dgs_cpf_housing_withdrawn_annual.json`: CPF Board, contributions received per
  calendar year (includes government grants, dividends from Special Discounted Shares and interest paid; data.gov.sg
  `d_bb9b7f963ef295b750c9925e9e026524`) and net amount withdrawn under the housing schemes, public and private, per
  calendar year (net of money returned on sale; `d_7cce20f5d2d8ae2582da809e66a1cdd7`), 2006-2025. Added 2026-09-25 for
  a side question to A50, read by `experiments/a50_side_cpf_housing.py`.

Tried and not kept: HDB's general conditions for purchase (the address answered with a body that is not a PDF);
the Ministry of Social and Family Development's lower-income households trends reports for 2024 and 2025 (404).

## B132: household consumption by purpose and the HICP

Fetched 2026-09-24 by `experiments/b132_fetch.py` into `data/raw/b132/`; URLs, sizes and SHA-256 are in
`data/raw/b132/manifest.json`.

- `nama_10_cp18.json`: Eurostat household final consumption expenditure by purpose, COICOP 2018, annual: total,
  actual rentals (CP041), imputed rentals (CP042), financial services (CP122, household FISIM included), current
  prices and previous-year prices, million euro. Current over previous-year price gives each year's deflator
  change, and the item differences add up exactly to the total's.
- `nama_10_co3_p3.json`: the same account by COICOP 1999 (CP041, CP042, CP126), current prices and chain-linked
  volumes (2020); most countries stop in 2022. Kept as a cross-check of the 2018 version on the overlapping years.
- `prc_hicp_aind.json`: HICP annual average index, 2015 = 100, all items (CP00), actual rentals (CP041), financial
  services n.e.c. (CP126). The HICP has no imputed rentals, and its CP126 holds explicitly charged fees only.
- `prc_hicp_inw.json`: HICP item weights, per mille, same items.
- `insee_premiere_2002.html`: INSEE Première no 2002, "La consommation des ménages en 2023", read as literature:
  it prints the French 2023 consumption deflator with and without FISIM (7.1 % and 4.8 %) and the financial
  services price change (+193.5 %).

## B133: the BEA NIPA annual flat file, and one EPI table

Fetched 2026-09-25 by `experiments/b133_fetch.py` into `data/raw/b133/`; URLs, sizes and SHA-256 are in
`data/raw/b133/manifest.json`. No key or registration is needed for these files.

- `NipaDataA.txt`: every published annual NIPA series (SeriesCode, Period, Value). Series read: DPCERG and DPCERV
  (PCE price index and its percent change), CE001228 and CE001209 (contributions to the PCE price change of imputed
  rental of owner-occupied nonfarm housing and of financial services furnished without payment, Table 2.4.8),
  DOWNRG, DIMPRG, DOWNRC, DIMPRC, DPCERC (those two items' price indexes and current-dollar values, and PCE's),
  B358RG, B195RG, A191RG (price indexes for gross value added of the nonfarm business sector, the business sector,
  and GDP, Table 1.3.4 and 1.1.4).
- `SeriesRegister.txt`, `TablesRegister.txt`: BEA's registers of series and tables.
- `epi_2015_table1.txt`: Table 1 of Bivens and Mishel (2015), EPI Briefing Paper #406, copied 2026-09-25 from the page
  text in a browser because the site answers scripted requests with HTTP 403. Read as literature; the column used is
  1973-2014 and the rows are "Average hourly compensation-consumer" and "-producer" and "Divergence of consumer and
  output prices".

## B134: PIP PPPs by release and round, the PIP handbook page on urban and rural PPPs, Chen and Ravallion (2008)

Fetched 2026-09-25 by `experiments/b134_fetch.py` into `data/raw/b134/`; URLs, sizes and SHA-256 are in
`data/raw/b134/manifest.json`.

- `pip_ppp_<release>_<round>_<...>_PROD.csv`: World Bank Poverty and Inequality Platform auxiliary PPP table
  (`aux?table=ppp&version=...`), one file per release and PPP round (2011, 2017, 2021; releases 2022-09-09 to
  2026-09-22). Columns: country code, data level (national, rural, urban), round year, PPP in local currency per
  international dollar. The same round in two releases is the same reading published twice.
- `pip_versions.csv`: PIP's list of releases.
- `pip_handbook_convert.html`: PIP Methodology Handbook, "Converting to PPP dollars"; it states that separate rural and
  urban PPPs are computed for China, India and Indonesia from the national PPP, the ratio of urban to rural poverty
  lines and the urban share of ICP price collection.
- `chen_ravallion_wps4703.pdf`: Chen, S. and Ravallion, M. (2008), "The Developing World is Poorer than We Thought, But
  No Less Successful in the Fight against Poverty", World Bank Policy Research Working Paper 4703; read as
  literature for the 2005 round (China's ICP prices collected in 11 cities, treated as an urban PPP).
