# B145 arm A: what the Carnegie library "shares do not move" result is made of

RUN: 2026-10-29. Script `experiments/b145_carnegie_share.py`, record `results/b145_carnegie_share.json`
(carries the configuration it ran under). Retrieval: `experiments/b145_fetch.py`; the two packages, their
SHA-256 and byte counts are in `data/raw/b145/b145_manifest.json` and listed in `data/SOURCES.md`.

## 1. The question

Berkes and Nencka (Review of Economics and Statistics, 2026) find that a Carnegie library raises
patenting in the city that received it, against cities that applied and were turned down. Their table A5
adds that the share of patents by immigrant inventors and by women inventors does not move: column 3
reads `-0.000 (0.002)` for immigrants and `-0.001 (0.004)` for women. That zero is the only published
reading on whether a large access shock to codified knowledge changes who invents.

The same table reports level effects on the counts: `+0.080 (0.024)` immigrant patents on a mean of
`0.208`, `+0.021 (0.013)` women's patents on `0.094`. Two things decide what the zero carries: how the
share is built, and whether the counts are in levels. Both are read here from the authors' own code and
data, and the share is then read a second way, pooled over cities.

## 2. Carrier

Harvard Dataverse `doi:10.7910/DVN/TYVVY2`, CC0: the data package (491,062,786 bytes) and the code
package (4,588,918 bytes). The code was read as text and ported to Python; nothing from the packages was
executed.

The analysis panel is not in the package (its output folder is empty), so it is rebuilt from the
packaged inputs by porting the sample script (`~Combined/Scripts/02_create_carnegie_sample.do`) and the
first part of the results script (`Scripts/01_carnegie_rejected_results.do`). Two city files that the
sample step merges are built on the NBER server from the restricted full-count census and are not
packaged. They supply the census city population, which the published sample needs in two places: a
city must match the 1900 census uniquely, and a city above 25,000 people counts as large and is dropped.
Three stand-ins are run and all are printed:

| variant | large city | census match | cities | city-years |
|---|---|---|---:|---:|
| `county_only` | county population 1900 above 750,000 | none | 1,553 | 61,977 |
| `city_pop_proxy` | the same, or the packaged city population above 25,000 in 1900 | none | 1,465 | 58,450 |
| `pop_listed` | as `city_pop_proxy` | a positive packaged population in 1900 | 1,363 | 54,382 |

The published sample has 48,698 city-years; at forty years per city that is about 1,220 cities. The
count columns of the same table are the calibration: `city_pop_proxy` reproduces them best, at a summed
distance of 0.42 published standard errors over the three columns, and carries the readings below.

| column 3, same specification | published | `city_pop_proxy` | `pop_listed` | `county_only` |
|---|---|---|---|---|
| total patents (levels) | 0.762 (0.269) | 0.715 (0.263) | 0.849 (0.250) | 2.724 (0.679) |
| immigrant patents (levels) | 0.080 (0.024) | 0.080 (0.022) | 0.092 (0.021) | 0.322 (0.069) |
| women's patents (levels) | 0.021 (0.013) | 0.018 (0.012) | 0.025 (0.012) | 0.098 (0.029) |
| immigrant share | -0.000 (0.002) | 0.000 (0.002) | 0.001 (0.002) | 0.001 (0.002) |
| women's share | -0.001 (0.004) | -0.002 (0.004) | -0.000 (0.004) | -0.002 (0.004) |
| share regression N | 28,882 | 34,077 | 32,441 | 37,542 |

Column 3 absorbs state, year and grant-year effects and clusters by city. The sample means match the
published summary table: patents per city-year 2.54 against 2.51, immigrant 0.211 against 0.208, women
0.095 against 0.094.

## 3. How the share is built

The code builds `share_immigrant = total_immigrant_patents / patent_count` for every city-year, with no
rule for a zero denominator. In Stata `x/0` is missing, so a city-year with no patent leaves the share
regression. It is not recorded as zero. The published N says the same: 28,882 share observations
against 48,698 count observations. The share regression is an unweighted average over the 59% of
city-years that have a patent.

Its denominators are thin. In the rebuilt panel the median city-year in the share regression has 2
patents, the first quartile 1, the ninth decile 9. City-years with at most two patents are 54.4% of the
observations and hold 16.8% of the patents. Each enters with the same weight as a city-year with a
hundred.

The immigrant and women counts are sums of name-based probabilities (`prob_foreignborn_ln`,
`prob_female_fn`), and the denominator is all patents. In the sample the birthplace probabilities cover
94.1% of patents and the gender probabilities 95.2%, so every share is of all patents, with about one
in twenty unclassified.

One line of the results script regresses the women's share in columns 5 and 6 of the table it writes
under the immigrant name. Column 3, the one cited, is not affected.

## 4. The counts are in levels, and they imply a small share move

The count regressions use the counts themselves, not `ihs` and not logs. Read at the sample means, the
three published level effects say: all patents `+0.762` on `2.509` (+30%), immigrant patents `+0.080` on
`0.208` (+38%), women's patents `+0.021` on `0.094` (+22%). The share they imply:

| | before | implied after | move |
|---|---:|---:|---:|
| immigrant | 0.0832 | 0.0883 | +0.0050 |
| women | 0.0373 | 0.0350 | -0.0022 |

The counts and the published share are therefore not far apart. An implied move of +0.0050 against a
reported `-0.000 (0.002)` is two and a half standard errors; the women's row is half of one. Setting the
`ihs` effect on total patents (`+0.120`, i.e. +12.7%) against the level effect on immigrant patents gives
a much larger gap; the two are on different scales and that gap is not in the data.

## 5. The share read pooled

`sum(x) / sum(n)` in treated and control cities, before and after the grant (20 years either side, the
published window), with a city-cluster bootstrap (2,000 draws). The floor is a placebo on the same 1,465
cities: inside the pre-period only, a false grant ten years early.

| | patents | immigrant share | women's share | cities | city-years (with no patent) |
|---|---:|---:|---:|---:|---:|
| treated, before | 45,188 | 0.0742 | 0.0345 | 1,280 | 25,547 (11,798) |
| treated, after | 88,885 | 0.0886 | 0.0382 | 1,280 | 25,528 (9,145) |
| control, before | 5,343 | 0.0725 | 0.0354 | 185 | 3,692 (1,887) |
| control, after | 8,914 | 0.0823 | 0.0433 | 185 | 3,683 (1,543) |

| | difference in differences | 90% interval | placebo (sd) | reading |
|---|---:|---|---:|---|
| immigrant share | +0.0045 | [+0.0006, +0.0083] | -0.0045 (0.0030) | signed, within twice the placebo spread |
| women's share | -0.0042 | [-0.0100, +0.0017] | +0.0019 (0.0054) | interval covers zero |

The same regression as column 3 weighted by the denominator reads `+0.0019 (0.0024)` for immigrants and
`-0.0034 (0.0036)` for women. The other two variants give pooled differences of +0.0050 and +0.0051
(immigrant) and -0.0037 and -0.0028 (women), with the same two readings. Dropping any one of the five
heaviest cities in either group moves the immigrant difference between +0.0039 and +0.0050 and the
women's between -0.0060 and -0.0030. The five heaviest control cities hold 18.1% of control patents, the
five heaviest treated cities 6.5% of treated patents. Every city is in the record with its patents,
shares and zero years before and after.

## 6. What this says

- The published zero is a city-year ratio averaged without weights over the city-years that have a
  patent. Zero-patent years drop out; they do not enter as zeros.
- For immigrants, weighting by the denominator moves the estimate from +0.0004 to +0.0019, and pooling
  moves it to +0.0045, the size the published level counts imply (+0.0050). The pooled move matches,
  with the opposite sign, the placebo move in the decade before the grant (-0.0045), so it does not stand
  above the floor.
- For women, every reading has a point estimate at or below zero, from -0.0000 to -0.0042, with an
  interval that covers zero.
- Read either way, a library moves neither share by more than about one percentage point, and the
  pooled immigrant move cannot be told from the pre-grant movement in the same cities.

A Carnegie library opened both a book edge and a meeting room, so this carrier does not separate the two
edges; the reading bounds the share move, and the separation is left to a carrier that opens only the
book edge.

## 7. Criteria

Criteria come in kinds; only a rival kind can speak against the framework, and this arm hangs none,
because the carrier allows both outcomes.

| | criterion | reading |
|---|---|---|
| PASS | B145-1 `bookkeeping` source and coverage table | 5 rows; 2 named by the code and absent from the package, listed with zero items |
| UNREAD | B145-2 `known_answer` table A5 column 3 shares to the published digits | immigrant share agrees at the printed digits (0.000 against -0.000, 0.002 against 0.002); women's coefficient -0.002 against -0.001 with the standard error equal; the census-match restriction is not in the package, so the exact sample cannot be rebuilt and the criterion is not evaluated; the three count columns reproduce within 0.25 published standard errors each |
| PASS | B145-3 `own_reading` pooled shares, difference in differences, placebo floor, every city printed | immigrant +0.0045 [+0.0006, +0.0083], placebo -0.0045 (0.0030); women -0.0042 [-0.0100, +0.0017], placebo +0.0019 (0.0054) |

Criteria are written in the script that produces the record; the record carries their text, and every
quantity the run produces is reported.
