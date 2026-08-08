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
| NY Fed Household Debt and Credit, **split by product and by income quartile / credit score** | A1 calibration. The split is the point: the K-shape lives in the disaggregation, not the totals | `newyorkfed.org/microeconomics/hhdc` |
| Fed Z.1 Financial Accounts, by sector | B2 graph; A3 sector accounts | `federalreserve.gov/releases/z1` |
| BEA Input-Output Use Tables | B2 primary graph; empirical anchor for the A2 adjacency matrix | `bea.gov/industry/input-output-accounts-data` |
| M2, NBER recession dates | timeline alignment | FRED |

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

## Recording convention

Every file added to `data/raw/` gets a row here with: URL, retrieval date, series
identifier, and definitional basis. Figures from different definitional bases are
never placed in the same column. Delinquency data in particular mixes "unpaid" and
"paid late but eventually paid" across providers, and conflating them would
overstate a level.
