# B6-B: the informal leg, and what a one-sided quote can and cannot establish (Cuba)

**Written 2026-08-18, before any B6-B reading was computed and before the series
was fetched.** Thirteen windows had been queried as instrument probes by the time
this was written; §11 lists every one of them and every number they returned.

**Authority.** `PROJECT_PLAN.md` §14.4 for the stage, `b6_cuba_prereg.md` for
B6-A, whose §9 deferred every criterion touching the informal leg to this
document and made that deferral a registered commitment. Criteria continue
B6-A's numbering at **B6-9** rather than opening a second namespace inside one
stage.

**The limit that governs everything below, stated first because it is the kind
of thing a reader should not have to reach §5 to discover.** elTOQUE publishes
one number per currency per window. There is no bid and no ask. Under the
assumption of §3.3 that the published median sits inside the unobserved
bid-ask interval, substituting it into the field gives an **upper bound** on
every directed weight through the informal edge, and therefore on every cycle
weight. So a cycle that is non-positive under substitution is non-positive in
truth, and a cycle that is positive under substitution is **not established**.
**B6-B can never certify a positive cycle through the informal edge.** B6-A's
positive cycle of `3.2181` runs inside the BCC table and does not touch this
edge, so it is untouched by this limit.

---

## 1. What this half of the stage is for

B6-A established the typing inside one central bank's own table: three segments,
nineteen channel columns that are one number times a constant, segments I and II
one-way with sinks at exactly `{(USD, I)}` and `{(USD, II)}`, and a potential gap
`D_I >= 2.7932` that grew from `2.7981` to `3.2181` across the window. Every leg
inside that table is a fixed multiple of one number, so every square with both
legs inside one segment is a construction identity. **The contrast needs a leg
from outside, and the informal market is the only one there is.**

B6-A also left one quantity bracketed rather than located: where the truth sits
between the maximal model, in which `P(omega)` is empty, and the directed model,
in which a sub-potential exists with three components. What separates them is how
much of a return leg the informal market supplies in practice. **B6-B does not
close that bracket**, for the reason in the header. What it does instead is
measure three things the bracket cannot see:

1. whether the two markets price the euro against the dollar the same way, and
   whether the disagreement is stable (**B6-13**);
2. whether three claims denominated in the same unit carry three different
   prices in the same market on the same day (**B6-14**);
3. whether the return leg the BCC posts is a leg anyone transacts on
   (**B6-15**).

---

## 2. The instrument

### 2.1 One endpoint, two parameters, and no side

The published OpenAPI document at `https://tasas.eltoque.com/static/swagger.json`
(reachable through the Swagger UI at `https://tasas.eltoque.com/docs/`, whose
page source names that path) declares exactly one path, `GET /v1/trmi`, with
exactly two query parameters, `date_from` and `date_to`, both optional, both in
the format `YYYY-MM-DD HH:MM:SS`. There is no currency parameter and there is no
side parameter. Authentication is a bearer JWT.

The endpoint summary reads `Retorna las medianas de las ofertas de compra y
venta de las divisas en el mercado informal`. Buy offers and sell offers are both
inputs; **the output is one number**. The two sides are collapsed by the
publisher before anything reaches this project. `b6_cuba_prereg.md` §9 wrote the
friction column on this leg conditionally, `if two-sided quotes are served`.
**The condition resolves to the negative branch**, and that resolution is
recorded here rather than treated as a surprise.

### 2.2 The published number is a median over the requested window

The endpoint description states that the rates `se forman a partir de las
medianas de las ofertas de compra y venta en las ultimas 24 horas`, and that a
request without dates returns the trailing twenty-four hours from the moment of
the request. elTOQUE's methodology page states the same for the central
statistic: `Para determinar el valor central del USD, el euro y la MLC en el
mercado informal, elTOQUE utiliza la mediana en lugar de la media`, with a
plus-or-minus two standard deviation filter on outliers.
<https://eltoque.com/es/metodologia-de-la-tasa-representativa-del-mercado-informal-de-eltoque>

**The window is therefore the estimator's window, and choosing it is a
measurement decision, not a formatting one.** Measured on 2026-01-15, a one-hour
window at 09:00 against the full day moves the answer by nothing at all on two
instruments and by 3.71% on a third:

| instrument | full day | 09:00 to 09:59 | difference |
|---|---|---|---|
| USD | 480.0 | 480.0 | 0 |
| BNB | 561.11 | 561.11 | 0 |
| BTC | 468.94 | 467.26 | -0.36% |
| ECU | 520.0 | 511.98 | -1.54% |
| TRX | 156.92 | 155.32 | -1.02% |
| USDT_TRC20 | 545.0 | 535.09 | -1.82% |
| MLC | 400.0 | 385.16 | **-3.71%** |

The thick leg is window-invariant on that day and the thin ones are not.
`MEASUREMENT.md` failure mode 1 is the window error, and this is its instance.
§3.2 registers the window and §4.3 turns this measurement into the noise floor
rather than leaving it as an anecdote.

**A second consequence, which the API confirms rather than the methodology page.**
Ranges longer than twenty-four hours are refused with HTTP 400 and the body `El
intervalo de tiempo debe ser menor a 24 horas`. One request buys one day. The
span of §2.4 is therefore 2055 requests and there is no bulk form.

### 2.3 The response carries no echo of the date it answers for

Every response body reports `date`, `hour`, `minutes` and `seconds`, and **all
four are the server clock at the moment of the request**, not the day the answer
describes. Three probes for 2025-06-01, 2026-01-15 and 2026-08-18, issued two
seconds apart, all returned `"date":"2026-08-18"` with seconds `56`, `02` and
`05`. The rates differed, correctly and by a wide margin.

**This is a live hazard rather than a curiosity.** A fetcher that keyed rows on
the response's own `date` field would collapse all 2055 rows onto one day and
overwrite them in silence. `MEASUREMENT.md` failure mode 7 is the guard error
and this is its shape. Guard 1 of §6 forbids it and a test pins the row key to
the request.

**It also means a silent fallback would be invisible from the payload.** The
domain probes of §2.4 exist for that reason and are load-bearing rather than
decorative.

### 2.4 The domain is 2021-01-01 onward, measured and not claimed

elTOQUE's public chart page states that it runs from `1 de enero de 2021 hasta
la actualidad`.
<https://eltoque.com/tasas-de-cambio-cuba/mercado-informal>
**That claim is not what this document registers.** The boundary was measured
from the instrument itself, on both sides and at both ends:

| requested window | returned |
|---|---|
| 2018-01-01 | `"tasas":{}` |
| 2020-12-31 | `"tasas":{}` |
| **2021-01-01** | `{"ECU":46.0,"USD":40.0,"USDT_TRC20":34.17}` |
| 2021-01-02 | `{"ECU":46.25,"USD":40.0,"USDT_TRC20":67.08}` |
| 2027-06-01 | `"tasas":{}` |

**An empty `tasas` object is the instrument's own statement that it has no data
for that window**, and it is distinguishable from a populated one without any
inference. Two things follow. First, the API does not fall back to the latest
value when asked for a date it cannot serve, which is what makes §2.3's missing
echo survivable. Second, `b6_cuba_prereg.md` §10 rule 1 required the fetcher to
`assert that the returned span covers the requested span`, which is
unimplementable against a response that carries no span; **the empty object
replaces it with something that can actually be checked**. §12 records the
correction.

`TRMI_START = 2021-01-01` and the fetch runs to the last complete day before the
run, which on the day this was written is 2026-08-17, giving **2055 days**.

### 2.5 The instrument set moves, and the movement is a reading

The set of instruments served is not fixed:

| date | instruments |
|---|---|
| 2021-01-01 | `ECU`, `USD`, `USDT_TRC20` |
| 2025-06-01 | those three plus `BNB`, `BTC`, `MLC`, `TRX` |
| 2026-01-15 | the same seven |
| 2026-08-18 | `BTC`, `ECU`, `MLC`, `USD`, `USDT_TRC20` |

The fetcher may not assume a fixed key set, and a panel built from this source is
unbalanced by construction. **A currency present on one day and absent the next
is recorded as absent and never interpolated**, because the absence is itself a
measurement of how thin that leg is. Guard 4 of §6 enforces it.

### 2.6 What elTOQUE's own methodology says, and where it stops

Named in the methodology page as median-based: **USD, the euro, and MLC**. Named
as receiving an exponential moving average instead, because the offer count is
too low for a daily median: **CAD, GBP, MXN and others of that kind**, computed
as the current day's median blended into the previous day's EMA.

**`USDT_TRC20` is on neither list.** Its estimator is therefore unknown, and an
EMA carries serial dependence by construction, which would contaminate any
criterion about persistence. B6-14(b) is written with that caveat attached and
§4.2 registers a diagnostic that looks for the EMA signature rather than assuming
its absence.

The page does **not** state whether buy and sell offers are pooled into one
median or whether the published figure is a midpoint of two medians. §3.3 turns
that gap into a named assumption instead of leaving it implicit.

The construction has been through double-blind peer review: Pavel Vidal, Carlos
Enrique Muniz Cuza and Abraham Calas Torres, *Using AI in the Informal Currency
Market: Evidence from Cuba*, **Applied Economics**, October 2024,
doi:10.1080/00036846.2024.2416091.
<https://www.tandfonline.com/doi/full/10.1080/00036846.2024.2416091>
**That paper is also the place where §3.3's assumption can be settled**, and it
had not been read when this document was written.

---

## 3. The measurement

### 3.1 Which source supplies what

| leg | source | what it gives |
|---|---|---|
| official, three segments | BCC, already retrieved for B6-A | `tasaOficial`, `tasaPublica`, `tasaEspecial`, plus the nineteen channel columns as `base * k` |
| informal | elTOQUE `GET /v1/trmi` | one median per instrument per day |
| external referee | ECB `EXR.D.USD.EUR.SP00.A`, already retrieved for B6-A | the world euro cross |

The BCC publishes **one reference number per currency**, not a two-sided quote.
The two-sidedness in `MARKUP_SCHEDULE` belongs to the intermediaries' authorised
margins, which is what B6-A registered and what the retail ladder confirms: on
2026-08-18 BPA quoted 602.70 / 627.30 and CADECA's offices 585.00 / 608.40,
the latter being exactly compra times 1.04.
<https://eltoque.com/tasas-de-cambio-cuba/dolar>
The registered channel stays `efectivo_ventanilla`, compra `0.980` and venta
`1.020`, a round trip of `0.040005`. It is not swapped for a wider-band channel
at any point in this stage, and B6-A's `SEGMENT_CHANNEL` is the single place it
is written.

### 3.2 The registered window, and why it is not an arbitrary choice

`TRMI_WINDOW = ("00:00:00", "23:59:59")`, the full calendar day, requested as
literal strings in the API's own format.

**The justification is a measurement, not a preference.** The full-day window is
the one that reproduces the figures elTOQUE publishes to the public. Two
independent checks, both made before this document was written:

- **2025-09-30**: the full-day window returns `ECU = 500.0`. elTOQUE's own
  article of that date reports that the euro reached 500 CUP for the first time
  that day.
  <https://eltoque.com/es/el-euro-rompe-la-barrera-de-los-500-cup-en-el-mercado-informal>
- **2026-08-11**: the full-day window returns `USD = 670.0`, which is the value
  already on the project's record from outside the API.

A one-hour window on 2026-01-15 returns `MLC = 385.16` where the full day returns
`400.0`. **The window is doing real work**, and the one registered here is the
one that reconstructs the published series.

### 3.2.1 The window is in Havana time, which was learned from a refusal

`date_from` and `date_to` are read as Havana wall-clock times. **No document
says so.** The main pass ran 310 days and then returned HTTP 400 with `El
intervalo de tiempo debe ser menor a 24 horas` on 2021-11-07, for a window of
`00:00:00` to `23:59:59` that is 23 hours 59 minutes 59 seconds on any ordinary
reading and 25 hours less a second in `America/Havana`, because the clocks go
back that night.

**Five fall-back days are refused outright**, and on each the window closes at
`22:59:59` instead. That covers 86,399 seconds, the same elapsed time as an
ordinary day, so the estimator's exposure is unchanged even though the endpoints
are not; neither endpoint lands in the repeated hour, so neither is ambiguous.

| kind | dates | window | elapsed |
|---|---|---|---|
| fall back | 2021-11-07, 2022-11-06, 2023-11-05, 2024-11-03, 2025-11-02 | shortened to `22:59:59` | 86,399 s |
| spring forward | 2021-03-14, 2022-03-13, 2023-03-12, 2024-03-10, 2025-03-09, **2026-03-08** | registered window, unchanged | **82,799 s** |
| every other day | | registered window | 86,399 s |

**The spring-forward days are the ones that matter and they do not error.** The
registered window on those spans 23 hours rather than 24, so the median is taken
over an hour less of offers and the response says nothing about it. There is no
window inside one local calendar day that repairs this. `local_span_seconds` is
recorded per day in the manifest instead, so the inhomogeneity is visible to
anything downstream rather than waiting to be rediscovered.

**No fall-back day falls inside B6-A's window. One spring-forward day does:
2026-03-08.** It is the only inhomogeneous day any criterion sees, and it is
named here rather than found later.

### 3.3 Assumption A1, and the direction it fixes

> **A1.** The published median `m` satisfies `bid <= m <= ask`, where `bid` and
> `ask` are the unobserved prices at which the informal market buys and sells the
> instrument on that day.

**Basis.** The API summary and the methodology page both state that buy offers
and sell offers are the inputs. A statistic computed from both sides lies between
the two sides' central values whenever buyers bid below sellers' asks, which is
the ordinary condition of a market with intermediaries.

**Not proved.** The methodology page does not say whether the sides are pooled
into one median or averaged as two. The Applied Economics paper of §2.6 is where
it can be settled, and it had not been read.

**What A1 buys, and what it costs.** In the field of `orphan_squares`,
`omega(CUP -> USD) = -log(ask)` and `omega(USD -> CUP) = log(bid)`. Under A1,
`-log(ask) <= -log(m)` and `log(bid) <= log(m)`, so **substituting the median
gives an upper bound on both directed weights**, hence on any path sum and any
cycle sum through this edge.

**A1 is not a load-bearing input to any criterion below.** B6-15 replaces it with
a sensitivity statement: it reports the critical spread the conclusion survives,
so a reader who rejects A1 substitutes their own spread and reads off the answer.
A1 is stated here because §3.4's rule needs a direction, and because an
assumption that governs a sign belongs in the open rather than inside a function.

### 3.4 The one-sided rule

> Substituting `m` into the informal edge yields an upper bound. A cycle that is
> **non-positive** under substitution is non-positive in truth and may be
> reported. A cycle that is **positive** under substitution is **not
> established** and may not be reported as a finding.

This is the informal-leg analogue of `b4` §5.2, which forbids imputing the
missing direction on a one-way edge. Here the missing quantity is the width
rather than the direction, and the prohibition has the same root: **a number
produced by supplying it has supplied exactly the quantity in dispute.** B6-12
enforces the rule in code so that an attempt raises instead of returning a
plausible float.

### 3.5 Two structural breaks inside the window, both registered in advance

1. **2025-12-18.** Segmento III opens. This is B6-A's `WINDOW_START` less one
   day and it is the reason the stage exists.
2. **2026-06-18.** A second package: private exchange houses, an FX auction
   system, private banking, crypto regulation, and foreign-currency accounts for
   natural persons without prior administrative authorisation. No effective date
   was given, and as of 2026-08-18 no evidence was found that the first private
   exchange house had opened, six weeks after the prime minister said it would
   open `in the coming days`.
   <https://oncubanews.com/cuba/economia/cuba-aprueba-banca-privada-criptomonedas-y-remesas-por-canales-privados-la-mayor-reforma-financiera-en-decadas/>
   <https://www.periodicocubano.com/manuel-marrero-confirma-la-apertura-de-la-primera-casa-de-cambio-privada-en-cuba/>

**The second break is registered here because it lands inside B6-13's second
block.** The registered criterion is computed on the whole window with the break
marked; a diagnostic repeats it with the post-break days excluded. Both are
reported. **A break found after the fact and a break declared before the fetch
are different objects**, and this document exists partly to make that difference
checkable.

### 3.6 Segmento III steps, it does not float

The official rate is described by observers as moving in `extended administrative
pauses followed by discrete jumps` rather than continuously, and counters at
airports and hotels have been reported quoting 20 to 30 pesos away from the
published figure.
<https://en.cibercuba.com/noticias/2026-02-07-u1-e207888-s27061-nid320279-banco-central-cuba-acelera-tasa-flotante-sigue-zaga>
B6-A's `publication_days` already confines the estimator to days the table
actually moved. The consequence for B6-B is narrower and is registered in
B6-15(b): **a stepped series makes the mean of a gap uninformative**, so the
criterion is written on a percentile.

---

## 4. The arms

### 4.1 Known-answer arm: three externally published values

| date | quantity | expected | source |
|---|---|---|---|
| 2025-09-30 | `ECU` | `500.0` | elTOQUE's article of that date, reporting the euro at 500 CUP for the first time |
| 2026-08-11 | `USD` | `670.0` | already on the project's record from outside the API |
| 2021-01-01 | non-empty, and 2020-12-31 empty | the domain boundary | measured in §2.4 |

**The 2025-09-30 hit is what pins `ECU` to the euro.** elTOQUE's public site
lists the informal instruments as USD, EUR, MLC, CAD, MXN, ZELLE and CLA and does
not use the string `ECU` anywhere, so the identification rests on the value and
the date agreeing, not on the code. Guard 6 of §6 makes the rename happen in one
place and pins it to this test.

### 4.2 The control arm, which is fetched and carries no criterion

`BTC`, `TRX` and `BNB` are retrieved with everything else, at no marginal cost,
because the request is keyed on the date and not on the instrument. **They enter
no criterion.** Two diagnostics are registered for them:

1. **The placebo.** Their CUP prices divided by their world prices should track
   the informal dollar. If they do, the moving part is the CUP leg rather than
   the instrument, which is a check on the informal dollar itself.
2. **The thinness reading.** `BNB` and `TRX` are present on 2026-01-15 and absent
   on 2026-08-18. When an instrument enters and leaves the served set is a
   measurement of depth that the level series cannot give.

A third diagnostic covers `USDT_TRC20`, whose estimator §2.6 leaves unknown: test
the series for the signature of an exponential moving average. **A positive
finding does not invalidate B6-14; it qualifies part (b) of it**, and the
qualification is registered here rather than added afterwards.

### 4.3 The noise floor is measured twice and the larger is used

B6-13 divides by a noise floor, so the floor may not be a number of this
project's choosing. Two independent measurements, both procedures registered
before the fetch:

1. **Quantisation.** The empirical distribution of the last significant place
   across the fetched series, per instrument. Informal quotes are posted on a
   coarse grid, and on the observed evidence one tick of the euro is roughly
   0.65% to 0.75% of the euro-dollar cross.
2. **Window sensitivity.** On twelve registered dates, the fifteenth of each
   month for twelve consecutive months ending at the last complete month, fetch
   both the full day and `12:00:00` to `12:59:59`. The floor is the ninetieth
   percentile of `|log(m_1h / m_full)|` for the cross.

**The second measurement is of the wrong estimator and is converted.** The
hour-against-day dispersion describes a one-hour median, which no criterion
uses. A one-hour window holds about `1/r` of the day's offers, so if they are
exchangeable within the day it carries `r` times the full-day median's variance
and the full-day median is nested inside it, giving
`Var(m_1h - m_full) = (r - 1) Var(m_full)`. The dispersion divides by
`sqrt(r - 1)`.

**`r` is not observed.** elTOQUE publishes no offer counts, so the registered
value is the window-length ratio, `r = 24`, and nothing stronger. B6-13
therefore reports the **critical `r`** at which its verdict would flip, in the
same form as B6-15's critical spread, so a reader substitutes their own belief
about how concentrated the trading day is and reads off the answer rather than
having to accept a constant.

`noise_floor = max(quantisation, denoise(window_sensitivity))`, per pair. Cost:
twelve extra requests.

---

## 5. Pre-registered criteria

Seven criteria, numbered on from B6-A. Every constant they use is in §6 and
every one was fixed before the series was fetched.

### B6-9. Retrieval integrity

Every day from `TRMI_START` to the last complete day appears exactly once. Days
the instrument answers empty are **stored as empty and counted**, never skipped
and never filled from a neighbour in either direction. Each response is stored
verbatim with the sha256 of what arrived and the sha256 of what was written,
recorded separately. **Eleven of the twelve probe windows of §11 that
returned a `tasas` object** are re-read during the fetch and must reproduce
their probe bodies exactly on that object, the clock fields excepted.

**The twelfth, 2026-08-18, is not compared, and the reason is arithmetic rather
than editorial.** That probe was taken at 18:05 Havana time on 2026-08-18, six
hours before the day closed, so it and the main pass's row for the same date are
medians over different amounts of the same day. `fetch_eltoque.py` stops the main
pass at the last complete day for exactly this reason: today's answer is a
different statistic from every other row. Asking the two for equality would
compare two different statistics. The per-instrument difference is kept and
reported as a second window-sensitivity reading for §4.3.

**FAILS** on a missing day, a hash disagreement, a filled empty day, or one of
the eleven comparable probe windows that does not reproduce.

**Why the probe replay is in the criterion rather than in a guard.** §2.3 leaves
the payload unable to say which day it describes. Re-reading windows whose
answers were written down before any criterion existed is the only check
available that the fetch asked for the days it thinks it asked for.

### B6-10. The known-answer arm

The fetched series carries `ECU = 500.0` on 2025-09-30, `USD = 670.0` on
2026-08-11, a non-empty first day at 2021-01-01, and an empty answer at
2020-12-31.

**FAILS** on any disagreement. **A failure here is a failure of the instrument
and not of the hypothesis**, and under `A6-1` it stays failed rather than being
repaired into a pass.

### B6-11. The informal edge carries an index part and no friction part

Registered as a typing statement with a guard behind it: no reported quantity may
use a bid or an ask on the informal edge, because neither exists. The guard has
the shape of B6-A's `guard_no_imputation` and raises with the reason attached
rather than returning a plausible float.

**FAILS** if the guard fires anywhere on a reporting path.

### B6-12. The one-sided rule is enforced and not merely stated

§3.4's rule is implemented: any cycle weight computed with the median substituted
into the informal edge is carried with its direction, and a positive value is
returned as **not established** rather than as a finding. A source-reading test
asserts that no reporting function emits a positive-cycle claim that depends on a
substituted median.

**FAILS** if any such claim reaches a result record.

### B6-13. The two markets price the euro against the dollar differently, and the disagreement decays

For each day on which both sides serve the dollar and the euro,

```
h(t) = log(BCC_EUR(t) / BCC_USD(t)) - log(ECU(t) / USD(t))
```

both terms taken on the registered channel and the registered window.

- **(a)** the median of `|h|` over the **first 90 publication days** of the B6-A
  window exceeds `SIGNAL_OVER_NOISE * noise_floor`, that is `4.0` times §4.3's
  floor;
- **(b)** the median of `|h|` over the **last 90 publication days** is **smaller**
  than the median over the first 90.

**FAILS** if (a) is inside the band, or if (b) does not shrink.

**(a) is reported with its critical offer ratio**, the share of a day's offers a
single hour would have to hold for the first block to stop clearing the band.
The floor's conversion in §4.3 needs a ratio that is not observed, and a
criterion resting on an unobserved constant should say what the constant would
have to be to change the answer.

**Why a two-block contrast and not a fraction of days.** B6-A's B6-7 is the
precedent: it reported `D_I` moving from `2.7981` to `3.2181` rather than a count
of days above a line. The same shape is right here because the published record
shows a quantity that is decaying rather than switching. Externally published
same-day pairs, with the world cross from daily and monthly references:

| date | informal EUR/USD | world | `h` | source |
|---|---|---|---|---|
| 2025-12-24 | 480/440 = 1.0909 | ~1.179 | **+0.0777** | Directorio Cubano, that day |
| 2026-01-10 | 500/458 = 1.0917 | 1.1731 | **+0.0719** | CiberCuba, that day |
| 2026-03-07 | 575/510 = 1.1275 | 1.1571 | +0.0260 | CiberCuba |
| 2026-04-20 | 600/525 = 1.1429 | 1.1686 | +0.0222 | Directorio Cubano |
| 2026-05-29 | 640/572 = 1.1189 | 1.1681 | +0.0430 | Directorio Cubano |
| 2026-06-21 | 800/695 = 1.1511 | 1.1510 | **-0.0001** | CiberCuba |
| 2026-07-21 | 775/668 = 1.1602 | 1.1419 | -0.0159 | CiberCuba |
| 2026-08-17 | 760/663 = 1.1463 | 1.1580 | +0.0102 | CiberCuba |

**`h` is signed as the criterion defines it**, so a positive value means the informal market prices the euro lower against the dollar than the official market does, which is a discount on the Havana euro. The world cross stands in for the official leg in this table only, on the strength of the three-decimal agreement recorded below.

<https://www.directoriocubano.info/cuba/increible-tasa-de-cambio-del-euro-es-mas-alto-en-el-mercado-formal-que-en-el-informal/>
<https://en.cibercuba.com/noticias/2026-01-10-u1-e207888-s27061-nid318209-dolar-vuela-peso-hunde-regimen-cubano-pierde-batalla>
<https://www.cibercuba.com/noticias/2026-06-21-u1-e207888-s27061-nid332949-brecha-cambiaria-alcanza-niveles-criticos-mercado>
<https://www.cibercuba.com/noticias/2026-08-18-u1-e208933-s27061-nid338085-dolar-retrocede-euro-resiste-asi-cierra-mercado>

**A criterion written as `|h|` above the band on 80% of days would have failed on
this record**, since roughly 40% of the reported days clear `4 * 0.7%`. It would
have failed for a reason unrelated to the phenomenon: the quantity is large early
and small late, and a fraction-of-days test discards exactly that.

**Why the BCC side is the right official leg.** Its implied cross tracks the world
cross to three decimals: `544.85/471 = 1.1568` against `1.1571` on 2026-03-07,
`676/592 = 1.1419` against `1.1419` on 2026-07-21, `727/628 = 1.1576` against
`1.1580` on 2026-08-17. So the BCC is a pass-through of the world cross and `h`
is, to that accuracy, the informal market's own deviation. **B6-A's B6-4 failed
on 3 of 147 days**, which measures where the pass-through is imperfect; the two
readings are consistent and that failure is not repaired here.

### B6-14. Three claims on the dollar, three prices

`USD` cash, `MLC`, and `USDT_TRC20` are all denominated in dollars and all quoted
in pesos in the same market on the same day.

- **(a)** the sign of `log(USD / MLC)` is persistent beyond what a memoryless
  series with the same marginal produces: the series is cut into regimes at a
  minimum run of 30 days, and the share of days agreeing with their own regime
  must exceed the 99th percentile of the same statistic under 999 seeded
  permutations of the signs;
- **(b)** the same for the sign of `log(USDT_TRC20 / USD)`;
- **(c)** the median of `|log(USD / MLC)|` over the B6-A window exceeds
  `widest_friction_band()`, which is `efectivo_domingos_feriados` at
  `0.093896`.

**FAILS** on any of the three.

**Why a permutation null and not a share.** A share of days is a property of a
mixture. "The dollar sits above MLC on three days in four" is produced equally
by two clean eras either side of one switch and by a coin flipped every morning,
and only the first is a claim about stratification. Cutting into regimes and
measuring agreement **inside** them separates the two, and the threshold then
has to come from somewhere other than taste: a memoryless sign that is positive
three days in four runs thirty days one way with probability 0.00018, so the null
almost never splits at all and its agreement is its own marginal. **The
permutation has no constant to choose.** The regime count is reported at five
run lengths beside the agreement, because agreement alone rises to one as the
run length falls and says nothing on its own.

**(b) carries the estimator caveat of §2.6 and §4.2** and is reported with the
EMA diagnostic beside it. If `USDT_TRC20` is EMA-smoothed, a constant sign is
partly a property of the estimator, and the criterion is then read as bounding
the smoothed series rather than the market.

**(c) is the one place `widest_friction_band` belongs.** The comparison is
against the widest round trip the official table offers anywhere, and the claim
is that two dollar-denominated instruments in one market differ by more than the
most expensive official conversion. On the four days already seen the gap is
`log(665/445.17) = 0.4016` and `log(670/460) = 0.3760`, four times the band, so
this part is expected to pass by a wide margin and is registered mainly so that a
collapse would be recorded.

### B6-15. The posted return leg does not clear the informal market

Let `k_venta` be the registered channel's sell multiplier, `1.020`, and

```
a(t) = log(m_USD(t)) - log(tasaEspecial(t) * k_venta)
```

on publication days inside the B6-A window.

- **(a)** `a(t) > 0` on at least **95%** of publication days;
- **(b)** the **critical spread** `s* = 10th percentile of a(t)` satisfies
  `s* > 0.02`;
- **(c)** reported as a diagnostic only: `a(t)` against `widest_friction_band()`.

**FAILS** on (a) or (b).

**What (b) is and why it replaces an assumption.** The arbitrage of buying at the
official sell price and selling into the informal market earns `a(t)` minus the
informal round trip, which §2.1 leaves unobserved. Rather than assume a value,
the criterion reports the **largest informal spread the conclusion survives**. A
reader with their own estimate substitutes it. `0.02` is registered because
elTOQUE's own microstructure study of the informal market puts market-maker
spreads at 1.1 CUP, about 0.93%, in normal conditions in July 2022, widening to
1.8% under stress.
<https://omfi.eltoque.com/micoestructura-del-mercado-informal-de-divisas-en-cuba/>
**Two percent sits above that publisher's own stressed figure**, and the 2022
vintage of the estimate is the reason the threshold is registered above it rather
than at it.

**Why 95% and not more.** Every externally published pair found for the window
has the informal dollar above the official one, and the implied `a(t)` runs from
`0.0344` to `0.1873`:

| date | official III | informal | `a(t)` | source |
|---|---|---|---|---|
| 2025-12-18 | 410 | 435 | 0.0394 | Periódico Cubano / OnCuba, launch day |
| 2026-01-10 | 413 | 458 | 0.0836 | CiberCuba |
| 2026-03-07 | 471 | 510 | 0.0598 | CiberCuba |
| 2026-04-18 | 488 | 525 | 0.0533 | CiberCuba |
| 2026-05-29 | 514 | 572 | 0.0871 | Directorio Cubano |
| **2026-06-21** | 565 | 695 | **0.1873** | CiberCuba, widest since Segmento III opened |
| 2026-07-21 | 592 | 668 | 0.1010 | CiberCuba |
| 2026-08-13 | 624 | 665 | 0.0438 | CiberCuba |
| **2026-08-17** | 628 | 663 | **0.0344** | CiberCuba, narrowest of the period |

The smallest margin on the record is `0.0344`, five times the quantisation of
§4.3. Five percent of days is the allowance for the step schedule of §3.6, on
which the official rate can jump and briefly overshoot a falling informal quote.
**The criterion is passable and it is not trivially passable**: the August
compression, continued, would break it.

**What (b) tests that (a) does not.** (a) is about a sign and (b) is about a
magnitude that has to clear a real trading cost. The gap has been open for the
whole life of Segmento III at between 5.6% and 23%, closing only because the
official rate moved 410 to 628 across eight months, roughly +53.2%, against the
informal 435 to 663, roughly +52.9%.
<https://www.cibercuba.com/noticias/2026-08-07-u1-e197721-s27061-nid337245-100-dolares-alcanzan-cada-vez-menos-cuba-crisis>
**The convergence is one-sided.** The registered prediction is that the posted
return leg is a price and not a transaction, and B6-15 is the measurement of it.

---

### B6-16. Assumption A1, measured on the dollar leg

`docs/b6c_orderbook_availability.md` is the availability check. The Havana order
book carries both sides of the market that elTOQUE pools, for 1,321 days from
2021-07-23 to 2025-03-04, with at least five orders on each side on every one of
them.

Per day, from `daily_info.pickle`:

```
bid(t) = median of that day's best-bid series
ask(t) = median of that day's best-ask series
```

**The median and not the mean, and the choice is registered rather than
inherited.** Both fields are event-level lists appended as the book processes
orders, and the order count runs from 6 to 1,486 across days, so a mean weights a
busy day's intraday drift into a quantity meant to describe the day. The
repository's own helper takes a mean; both are reported and the median is what
the criterion reads.

- **(a)** `bid(t) <= m_USD(t) <= ask(t)` on at least **95%** of the days both
  sources serve;
- **(b)** the days where it fails are reported **with the side it failed on**,
  because a median above the ask and a median below the bid reverse §3.4's bound
  in opposite directions.

**FAILS** if (a) is not met.

**Result, 2026-08-19: 95.38% of 1,321 days, against a threshold of 95%.**
Passes by 0.38 of a percentage point, which is thin and is stated as thin.

**The 61 misses are all on one side: above the ask, none below the bid.** That
is not the shape of noise, which would miss in both directions, and it matters
because §3.4's bound is directional. On a day where `m > ask`,
`omega(CUP -> USD) = -log(ask) > -log(m)`, so **substituting the median gives a
lower bound on that leg** while the other leg's upper bound survives. The bound
collapses by half on 4.6% of days and always the same half.

The misses look like one peso on a level near seventy: `bid 67 / ask 68 /
published 69`, `bid 75 / ask 75 / published 76`. The sell side is **thicker** on
miss days, 333 orders against 285 across all days, which is consistent with a
plain median of sell prices being dragged down by small offers where elTOQUE's
estimator is not a plain median. By year: 1, 13, 13, **32**, 2.

**What a pass buys and what it does not.** A1 stops being an assumption on the
dollar leg and becomes a measurement. **It stays an assumption on the euro, MLC
and tether legs**, because the repository ships the dollar run only: its code
takes `CURRENCY` in `{"USD", "EUR"}` and no euro artefact is published, so the
euro would need their scraper re-run against live sources. §3.3 keeps its
wording for those three and cites this criterion for the dollar.

**What a failure would mean.** §3.4's rule reverses and every reading that rests
on the bound changes sign. B6-15 survives either way, because it reports a
critical spread rather than asserting one. B6-13 does not and would be re-derived.

### B6-17. The informal round trip, measured against B6-15's critical spread

Per day, `spread(t) = median of that day's bid-ask-spread series`, in logs, same
aggregation and same reason as B6-16.

- **(a)** the **99th percentile** of `spread(t)` over the 1,321 days is below
  B6-15's critical spread;
- **(b)** the distribution is reported in full: median, 90th, 99th, maximum, and
  the count of days above B6-15's threshold of `0.02`.

**VOID, ruled 2026-08-19 after the run.** Part (a) was written as a comparison
between two quantities that describe different periods. The round trip is
measured 2021-07-23 to 2025-03-04 and the critical spread it is set against is
measured over B6-A's window from 2025-12-19. **There is no day on which both
exist and no arrangement of this dataset produces one**, because the order book
ends nine months before the window opens.

**A verdict here reports which period each side came from.** The evidence that
this is the defect rather than an inconvenience is in the readings: the
ninety-ninth percentile is `0.0747` on the whole span and `0.0324` on the last
180 days, and **48 of the 56 exceeding days fall in 2022**. Whether (a) is met
depends entirely on which years are in the sample, which is what a comparison
across non-overlapping periods measures.

§5's own text already recorded that this arm ends before the window and that
what carries across is a property of the instrument. **What it did not do was
carry that through to the comparison**, and a criterion that compares an
instrument property against a window statistic is not an instrument-level
criterion.

**Part (b) stands and is reported.** The distribution is a valid reading of the
informal round trip over 1,321 days and it is not voided by the failure of the
comparison it was written beside:

| | median | p90 | p99 | max | days at or above `0.0507` |
|---|---|---|---|---|---|
| whole span | 0.0148 | 0.0392 | **0.0747** | 0.1214 | 56 of 1,321 |
| 2022 | 0.0269 | 0.0519 | 0.0840 | 0.0953 | **48** |
| last 180 days | 0.0061 | 0.0151 | **0.0324** | 0.0339 | **0** |

**The by-year and terminal rows were computed after (a) came out short and are
disclosed as such.** They are not a re-registration; they are the evidence for
the void ruling, and they would read the same way had (a) come out long.

**One corroboration worth keeping.** The whole-span median round trip is
**1.48%** against elTOQUE's own published market-maker spread of 0.93% normal
and 1.8% stressed, measured independently from the orders. An outside
recomputation landing inside the publisher's own stated range is evidence about
the instrument that no criterion here was designed to collect.

**This is the upgrade B6-15(b) was written to accept.** That criterion reports
the largest informal round trip the standing arbitrage survives and cites
elTOQUE's own 2022 microstructure note, 0.93% normal and 1.8% stressed, as
context rather than as an input. B6-17 replaces the published figure with a
measured distribution over 1,321 days. **It does not change B6-15's verdict**,
which is already a sensitivity statement; it says how much room that statement
has.

**Both criteria are instrument-level and neither is a statistic of the window.**
The order book ends 2025-03-04 and B6-A's window opens 2025-12-19. What carries
across is a property of how elTOQUE forms its number, not a reading about Cuban
prices in 2026, and it carries only so far as the instrument is unchanged.
elTOQUE dates its own methodology revisions, so that is checkable and §11's
disclosure records which revisions fall between the two spans.

**A fifth of the orders carry no side.** 19.7% have an empty `sign` and about
1.8% carry a token that is neither verb, so the side classification covers 78.5%.
**The unsigned fifth is not missing at random** and nothing inside the dataset
corrects for it, so both criteria are read as statements about the classified
78.5% and say so.

---

### B6-18. The zero calibration this stage did not have

`b6_cuba_prereg.md` §4.3 records that **B6-A has no zero calibration on this
window**: one publisher supplies all three segments, and the XLSX agreeing with
the API value for value measures the retrieval code rather than the collection.
B5 had one and B6 has not.

**The order book supplies one for the informal leg**: two independent paths to
the same daily number. elTOQUE publishes it; the orders it is computed from are
published separately, so it can be recomputed and the two compared.

Per day, following the method elTOQUE states for the dollar, the euro and MLC:
pool the day's classified prices, drop those outside two standard deviations of
the mean, take the median of what survives. Compare against the published USD
value in logs.

- **(a)** the median of `|log(recomputed / published)|` is below the median daily
  round trip measured in B6-17;
- **(b)** the full distribution is reported, with the count of days beyond one
  round trip and beyond two.

**FAILS** if (a) is not met.

**Result, 2026-08-19: passes, and the agreement is closer than the criterion
asked for.** Over 1,321 days the recomputation reproduces the published value
**exactly on 909 of them, 68.8%**. The median absolute log gap is `0.0000`
against a median round trip of `0.0148`; p90 is `0.0136`, p99 `0.0328`, the worst
day `0.0896`, with 112 days beyond one round trip and 18 beyond two.

**Two separately published artefacts agreeing to the cent on two days in three**,
with the recomputation blind to the published series, is a check on the
methodology statement and on this project's retrieval at once, and it is the
first zero calibration anywhere in B6.

**Not a grid artefact.** Prices sit on a coarse ladder, half a peso for the
dollar in recent years and whole pesos earlier, so exact agreement is easier here
than for a continuous quantity. The days that disagree settle the question: they
differ by three to seven percent, which is several rungs, so the ladder is not
forcing the agreement. Examples: 2022-01-19 recomputed `85.50` against published
`90.00`; 2024-06-04 recomputed `280.00` against `300.00`.

**Why the round trip is the yardstick and not a chosen tolerance.** The two paths
cannot agree exactly and it would be suspicious if they did: this recomputation
sees the classified 78.5% and not elTOQUE's full set, and it cannot replicate
their per-user deduplication or their blacklist. What a zero calibration asks is
whether the disagreement is small **against the scale of the thing being
measured**, and on this carrier that scale is the width of the market. Agreeing
to within one typical bid-ask is the statement worth making; agreeing to a
tolerance picked for the purpose is not.

**What a failure would mean.** Either the published series is not what its
methodology page says it is, or the order extraction misses a part of the market
that moves the median. **The two are not distinguished by this criterion** and
the write-up says so; what it would establish is that one of them holds, which
is more than the stage can say now.

### B6-16-S. Specification check: the sell side, weighted by volume

**Registered after B6-16 ran and disclosed as such.** B6-16 passes at 95.38% with
all 61 misses above the ask, on days whose sell side is thicker than average, 333
orders against 285. That pattern is what a plain median of sell prices dragged
down by small offers would produce against an estimator that is not a plain
median.

The orders carry `volume`. The check recomputes both sides as **volume-weighted**
medians and reports A1 under both definitions.

**This decides nothing and changes no verdict.** B6-16's reading stands as
registered. What the check separates is whether the 61 misses are a property of
the market or of the definition, and either answer is worth having: **the first
would mean the published median sits outside the book on 4.6% of days, the second
would mean it sits inside a book this project was weighting the wrong way.**

**Result, 2026-08-19: it was the weighting.**

| sell side | inside | above the ask | below the bid |
|---|---|---|---|
| unweighted median | 95.38% | **61** | **0** |
| volume-weighted median | **98.18%** | 7 | 17 |

**The one-sidedness disappears.** Sixty-one and nought becomes seven and
seventeen, split across both sides, which is the shape of noise rather than of
bias, and the share inside rises by 2.8 points.

**What this changes is not B6-16's verdict but what a reader should take from
it.** §3.4's bound is directional, and B6-16's misses being all above the ask
meant the bound collapsed on one leg on 4.6% of days. Under the weighting the
market itself uses, that concern is 1.8% of days and it points both ways.
**A1 holds on the dollar leg better than the registered criterion could see.**

**Why the unweighted definition is still the registered one.** It was fixed
before the data was opened and it is the more conservative of the two: a plain
median of prices makes no assumption about whether the volume an order names is
the volume it would trade, and on a market of posted classified advertisements
that assumption is not free. The weighted figure is reported beside it, not in
place of it.

---

## 6. Filters, guards and registered constants

### 6.1 Constants

| name | value | where it comes from |
|---|---|---|
| `TRMI_START` | `2021-01-01` | measured at both ends, §2.4 |
| `TRMI_END` | last complete day before the run | 2026-08-17 as written, 2055 days |
| `TRMI_WINDOW` | `("00:00:00", "23:59:59")` | reproduces the published series, §3.2 |
| `REGISTERED` | `USD`, `EUR`, `MLC`, `USDT_TRC20` | §5. `EUR` is the API's `ECU`, renamed once |
| `CONTROL` | `BTC`, `TRX`, `BNB` | fetched, no criterion, §4.2 |
| `TRMI_ULP` | `0.01` | every value seen carries at most two decimals |
| `SIGNAL_OVER_NOISE` | `4.0` | B6-A's constant, itself from B3-3 and B5-6 |
| `OFFER_RATIO` | `24.0` | the window-length ratio, §4.3. **Not observed**; B6-13 reports the critical value |
| `REGIME_MIN_RUN` | `30` | a month, the shortest span a Havana pricing order could be called a regime over |
| `REGIME_NULL_DRAWS` / `REGIME_NULL_SEED` | `999` / `0` | seeded, so the record reproduces to the byte |
| `REGIME_SWEEP` | `7, 14, 30, 60, 90` | regime count and agreement reported together at each |
| `SEGMENT_CHANNEL` | `efectivo_ventanilla` | B6-A's, unchanged, §3.1 |
| `K_VENTA` | `1.020` | that channel's sell multiplier |
| `CRITICAL_SPREAD` | `0.02` | above the publisher's own stressed 1.8%, §5 B6-15 |
| `BLOCK_DAYS` | `90` | §5 B6-13, two disjoint blocks inside a window of about 245 days |
| `BREAKS` | `2025-12-18`, `2026-06-18` | §3.5, declared before the fetch |
| `RATE_WINDOW_SECONDS` / `RATE_LIMIT` | `156.0` / `10` | **measured on this key**, §12. The documented rate is 24 times faster |
| pacing | **one request every 17.3s** | `156 / 9`, one request of headroom per window. The main pass is 10 hours |

### 6.2 Guards

1. **The clock is not the key.** `date`, `hour`, `minutes` and `seconds` from the
   response are stored as `fetched_at` and may never index a row. The row key is
   the requested date. A test pins it.
2. **An empty day is empty.** No forward fill and no back fill. B6-A's guard 2
   admitted a back-fill as a forward-fill once and the fix is the precedent here.
3. **No bid or ask on the informal edge.** B6-11's guard, shaped after
   `guard_no_imputation`.
4. **Instrument membership is recorded, not interpolated.** A currency that
   appears or disappears produces a membership record and never a value.
5. **Pacing reads the headers, and does not trust their sign.**
   `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` are on
   every response. A `429` is answered from `Retry-After` when that is positive,
   from `X-RateLimit-Reset` when that is, and otherwise from a backoff of this
   project's own that doubles from thirty seconds. The fetcher gives up after
   four consecutive `429`s and reports rather than sleeps when the wait asked
   for exceeds five minutes, because the run resumes from disk and a long silent
   sleep is indistinguishable from a hang. **Neither `Retry-After` nor
   `X-RateLimit-Reset` is trusted without a sign check**: both have been observed
   pointing into the past, and a clamp on a negative wait is an immediate retry
   wearing a delay's clothes.
6. **`ECU` becomes `EUR` in exactly one place**, pinned by the 2025-09-30
   known-answer test of §4.1.

## 7. Falsification

| criterion | falsified by |
|---|---|
| B6-13 | the first block's median inside the band, or the last block's median not smaller |
| B6-14(a) | the dollar-against-MLC sign's regime agreement failing to clear the permutation null's 99th percentile, that is, the ordering being no more persistent than a coin with the same bias |
| B6-14(b) | the same for the tether premium |
| B6-14(c) | two dollar-denominated instruments differing by less than the widest official round trip |
| B6-15(a) | the informal dollar at or below the official sell price on 5% or more of days |
| B6-15(b) | the critical spread falling to or below 2%, that is, the standing gap no longer clearing a plausible informal round trip |
| B6-16 | the published median sitting outside the book's own bid-ask interval on more than 5% of days, which reverses §3.4's bound |
| ~~B6-17~~ | **void, not falsifiable as written.** The two sides describe periods that do not overlap and cannot be made to, so the verdict is a statement about the sample's years. See §5 |

**A failed criterion stays failed.** `A6-1` and `HANDOFF.md` §3.2 item 9. B6-A's
B6-4 is the live example: it failed on 3 of 147 days, the withdrawal of its
envelope clause did not save it, and it is still recorded as failed.

**What would falsify the stage rather than a criterion.** If A1 is false in the
direction that makes the median lie outside the bid-ask interval, §3.4's rule
reverses and every conclusion that rests on the bound changes sign. B6-15 is
written to survive that, since it reports a critical spread rather than asserting
one. B6-13 is not, and would have to be re-derived.

## 8. Scope

**What this stage measures.** Prices, and what prices imply about which edges
exist. It does not measure quantities. B6-A recorded that limitation and it is
unchanged here: the framework has no capacity coordinate, and the informal
market's depth enters only through the membership record of §4.2 and the width
of the disagreement.

**Individual access to the official sell side is rationed, and the record of it
is documentary rather than statistical.** Eight months after Segmento III opened,
no first-hand account was found of an ordinary individual buying dollars at a
bank or CADECA at the floating rate. Selling to a bank worked from the first
week. Bank staff in Havana in the reform's first week said they had received no
instruction to sell: `Hasta el momento no tengo noticias de que se este vendiendo
dolares`, and `ahora todos los bancos lo que estan haciendo es la recogida`.
<https://www.14ymedio.com/cuba/empleados-bancarios-siguen-espera-orientaciones_1_1122000.html>
The individual channel carries a 100 USD per operation cap behind a booked queue
whose reported waits run from months to about eighteen months, conditional on the
branch holding cash.
<https://eltoque.com/es/asi-se-consiguen-divisas-en-cuba-en-2025>
The channel that demonstrably functions is restricted to registered non-state
businesses: 39 of them in the whole province of Villa Clara had bought currency
between January and 2026-03-11.
<https://oncubanews.com/cuba/economia/banco-metropolitano-habilita-la-venta-de-divisas-a-actores-no-estatales/>
<https://en.cibercuba.com/noticias/2026-03-11-u1-e135253-s27061-nid322768-gobierno-vende-divisas-mipymes-villa-clara-39>

**This material is context and not evidence.** B6-15 is the measurement; the
paragraph above is why the measurement is worth making. **Nothing in §5 depends
on any of these reports being right.**

**A mechanism for B6-13 that the criterion does not test.** Formal remittance
channels do not deliver euros as euros: CADECA and FINCIMEX pay out dollars at
the day's rate for euros sent, and at least one platform converts before
delivery.
<https://eltoque.com/como-funcionaran-las-remesas-en-dolares-por-cadeca-esto-es-lo-que-se-sabe>
So physical euros arrive by hand-carriage, and a euro is harder to place in Cuba
than a dollar. That is a candidate explanation for a euro discount against the
world cross, and for its decay as the account regime loosened. **It is written
here so that it cannot later be presented as a prediction.**

## 9. What B6-B does not contain

**The friction column on the informal edge**, for the reason in §2.1. There is no
`omega_bar` on that edge and none is supplied.

**A located answer to B6-A's bracket.** The header says why. The maximal and
directed models stay bracketed and B6-B narrows neither, because narrowing them
requires certifying a positive cycle through the edge that §3.4 forbids
certifying.

**The prospective zero calibration** deferred by `b6_cuba_prereg.md` §9. It needs
a period in which the two markets agree, and the record shows the gap has never
closed.

~~**Any use of the Havana order-book dataset**~~ **Brought in 2026-08-19 as
B6-16 and B6-17**, on the dollar leg only. Availability check in
`docs/b6c_orderbook_availability.md`. It remains outside the window and remains
the same population elTOQUE scrapes, so it is **not** the independent referee
`b5_orphan_prereg.md` §7.4 asks for and is not used as one.

**Still not contained**: the euro, MLC and tether legs of §3.3, for which A1
stays an assumption; the offer-arrival ratio `r` of §4.3, which the order
timestamps could measure on the dollar leg and which B6-13 would then carry
across instruments on a new assumption; and the recomputation of the TRMI from
raw orders that §14.6 registered this source for.

**Quantities, capacity, and volume.** §8.

## 10. Retrieval, and the rules the fetcher must satisfy

`data/fetch_eltoque.py`, following `data/fetch_bcc.py`.

1. **Resumable.** One request per day, 2055 of them, and an interrupted run
   continues from the last day written rather than starting over. The manifest
   is the resume point.
2. **Truncation is detected rather than read.** §2.4 gives the detector the
   earlier rule lacked: an empty `tasas` object is the instrument's own statement
   of absence, and it is distinguished from a short read, a parse failure and a
   `429` by construction rather than by guessing.
3. **Bytes are stored verbatim**, with the sha256 of what arrived and of what was
   written, both in the manifest, recorded separately for the `fetch_cip` reason.
4. **Nothing is deleted.** A file that fails to parse is renamed with an
   `.expired` suffix and left in place.
5. **The manifest records the served-instrument set per day**, so §2.5's
   membership reading comes from data and not from a hard-coded list.
6. **Raw responses live under `data/raw/`**, which `.gitignore` excludes.
   elTOQUE's terms forbid resale and redistribution and forbid sharing the key,
   so the series is not committed and the key lives in `.env`, which the same
   file excludes.
   <https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso>
7. **elTOQUE is cited as the source of the informal series** wherever it is
   reported, which their terms require and which this project would do anyway.

---

## 11. Disclosure: what had been seen before this document was written

The project's engineering rule 8 permits registering after data has been seen and
requires saying so. **Thirteen distinct windows were queried in fourteen requests
across three probe rounds on 2026-08-18, before any criterion above was written.**
Every one is listed with what it returned. Four of them fall inside B6-A's
window and are marked.

| # | window | returned |
|---|---|---|
| 1 | 2025-06-01 full day | `BNB 395.0, BTC 393.22, ECU 395.0, MLC 265.0, TRX 108.98, USD 370.0, USDT_TRC20 405.0` |
| 2 | 2025-06-01 to 2025-06-07 | HTTP 400, `El intervalo de tiempo debe ser menor a 24 horas` |
| 3 | **2026-01-15 full day** | `BNB 561.11, BTC 468.94, ECU 520.0, MLC 400.0, TRX 156.92, USD 480.0, USDT_TRC20 545.0` |
| 4 | **2026-08-18 full day** | `BTC 737.75, ECU 770.0, MLC 445.17, USD 665.0, USDT_TRC20 688.24` |
| 5 | 2025-06-01 full day, repeated | identical to 1 on the `tasas` object |
| 6 | 2018-01-01 full day | `"tasas":{}` |
| 7 | 2027-06-01 full day | `"tasas":{}` |
| 8 | **2026-01-16 full day** | `BNB 560.0, BTC 468.48, ECU 520.0, MLC 407.5, TRX 158.21, USD 485.0, USDT_TRC20 550.0` |
| 9 | **2026-08-11 full day** | `BTC 735.08, ECU 780.0, MLC 460.0, USD 670.0, USDT_TRC20 688.34` |
| 10 | 2026-01-15, 09:00:00 to 09:59:59 | `BNB 561.11, BTC 467.26, ECU 511.98, MLC 385.16, TRX 155.32, USD 480.0, USDT_TRC20 535.09` |
| 11 | 2025-09-30 full day | `BNB 360.0, BTC 452.91, ECU 500.0, MLC 210.0, TRX 164.52, USD 440.0, USDT_TRC20 488.0` |
| 12 | 2020-12-31 full day | `"tasas":{}` |
| 13 | 2021-01-01 full day | `ECU 46.0, USD 40.0, USDT_TRC20 34.17` |
| 14 | 2021-01-02 full day | `ECU 46.25, USD 40.0, USDT_TRC20 67.08` |

**What each round was for, so that the sequence can be audited rather than
taken on trust.** Round 1 asked whether past dates are served at all. Round 2
asked whether the answer is a function of the requested date, which §2.3 made a
live question: rows 5 through 10 are determinism, both domain boundaries,
resolution and window sensitivity. Round 3 asked what quota the key carries,
where the series begins, and whether `ECU` is the euro.

**Also seen before writing.** The external record used to calibrate B6-13 and
B6-15, which is published journalism and not this project's data. Every figure
that entered a threshold is in the tables of §5 with its source. **The two
thresholds that a reader should scrutinise hardest are the ones those tables
produced**: 95% in B6-15(a) and `0.02` in B6-15(b).

**Two thresholds that were drafted and discarded before the fetch**, recorded so
that the discarded versions cannot be mistaken for the registered ones:

- B6-13 was first drafted as `|h|` above the band on **80% of days**. The
  published record clears `4 * 0.7%` on roughly 40% of reported days, so the
  criterion would have failed, and it would have failed on a quantity that is
  large early and small late. Replaced by the two-block contrast.
- B6-15 was first drafted as the post-reform gap being at least **half** the
  pre-reform gap. **Segmento III did not exist before 2025-12-18**, so the
  denominator does not exist, and substituting Segmento II would substitute a
  different edge, one B6-A typed as a one-way sink. Replaced by the sign test and
  the critical spread.

## 12. Changelog

### 2026-08-18, written

**Corrections to `b6_cuba_prereg.md` carried here for the record**, and entered
in that document's own §11 as well:

1. **§10 rule 1 is falsified as written.** It required the fetcher to assert that
   the returned span covers the requested span. The API caps a window at
   twenty-four hours and the response carries no span at all, so neither half is
   available. §2.4's empty-object test replaces it.
2. **§10's pacing constant survives and its justification does not.** The
   registered 1 request per second came from elTOQUE's announcement of
   2023-12-01, which replaced an earlier 2 per minute and 5,000 per month.
   <https://eltoque.com/es/eltoque-anuncia-la-eliminacion-de-restricciones-de-la-api-tasas>
   The API's own specification states 60 per minute with a 10 per second burst
   cap, per key, and the observed headers on this key report a limit of 10 that
   refills within two seconds. **60 per minute is 1 per second**, so the number
   does not move; what moves is that the fetcher now reads
   `X-RateLimit-Remaining` instead of trusting a figure from a news article.
3. **The request count is confirmed rather than estimated.** `about 2050` was
   written before the domain was known. 2021-01-01 to 2026-08-17 inclusive is
   **2055 days**.

### 2026-08-19, how a 429 is answered

**A 429 can carry a negative `Retry-After`.** The first request of the first run
came back with `Retry-After: -11`. Nothing was written and nothing was deleted.

**A clamp on a negative wait is an immediate retry wearing a delay's clothes**,
which is why guard 5 falls back through `Retry-After`, then
`X-RateLimit-Reset`, then a backoff of this project's own that doubles from
thirty seconds, taking each only when it is positive. It gives up after four
consecutive refusals and reports rather than sleeps when the wait asked for
exceeds five minutes.

### 2026-08-19, the limiter measured: ten requests per 156 seconds

**`POLITE_DELAY_SECONDS` is 17.3, measured.** The published specification states
60 requests per minute with a 10-per-second burst cap and adds, in the same
paragraph, that a key may carry a different quota. **This key carries ten
requests per 156-second window**, a twenty-fourth of the documented rate, which
is a ten-hour main pass rather than a thirty-five minute one.

**Two probes, and the second exists because the first could not finish the job.**
A rate probe at one request per second returned nine 200s and then three 429s
with `X-RateLimit-Reset` unmoved throughout: that fixed the count at ten and put
a floor of 155 seconds under the window, but could not separate a whole window
from the tail of one started by the earlier aborted run's refusals, since a
refused request still counts against the quota. So a second probe waited 420
seconds, longer than any candidate window, and made a single request. **That
request is necessarily the first of its own window**, so its
`X-RateLimit-Reset` minus the moment it was sent is the window and nothing else.
It read 156.

**A third header is simply wrong and is no longer read.**
`X-RateLimit-Remaining` reported `10` on all fifteen requests of the rate probe,
including the three that came back 429. **It does not decrement**, so a pacer
that slows down as that count approaches zero never slows down at all. Two of
the three headers are honoured and the third is recorded and disbelieved.

**The pace carries one request of headroom on purpose.** `156 / 10` is 15.6
seconds and puts exactly ten requests in every window, on the boundary, where one
slow response carries an eleventh into a window it does not belong to. `156 / 9`
is 17.3 and costs 9% of the run.

**The span is unchanged.** Ten hours is longer than the criteria need, since
B6-13, B6-14 and B6-15 all run on B6-A's window and that is about 245 days, or
1.1 hours. Fetching 2021 onward anyway was ruled on 2026-08-19:
the retrieval is resumable, the background span is what the closure-and-reopening
reading rests on, and a partial series would have to be refetched later at the
same rate.

### 2026-08-19, the API reads its timestamps in Havana time

**310 days were fetched and are on disk. Nothing was lost and nothing deleted.**
The 311th, 2021-11-07, returned HTTP 400 with the range refusal, for a window
this project had been sending unchanged for 310 days.

**The API reads the timestamps as Havana wall-clock times.** That is not
documented anywhere and was not inferred from the `hour` field, which only ever
suggested an offset near UTC-4. It is established by the refusal itself: a
`00:00:00` to `23:59:59` window is under the 24-hour cap in every timezone
except one where the clocks go back that night, and refusing it is a statement
about which zone is being used. §3.2.1 records the consequence for both
directions of the transition.

**The list of transition dates is written out rather than computed.**
`zoneinfo` needs `tzdata` installed on Windows and this project's constants
should not depend on a host package. A test recomputes both lists from
`zoneinfo` and fails if the zone's history has moved, skipping with a note when
`tzdata` is absent.

**What this cost, and what it says about the earlier probes.** Thirteen probe
windows were queried before any of this was written and **none of them landed on
a transition day**, so nothing in the disclosure of §11 is affected, and a test
now asserts that. Had one, its recorded answer would have been for a window this
file no longer sends, and B6-9's replay would have failed for a reason that is
not a finding.

### 2026-08-19, the fetch completed

**2,056 days, none of them empty**, plus twelve sensitivity windows and twelve
replays. Nine hours and six minutes at 17.3 seconds a request, with no `429` at
any point. **The series has no gap anywhere between 2021-01-01 and 2026-08-18**,
which nothing in the design assumed and which B6-9's absence handling was built
to survive either way.

**The 2026-08-18 replay differs, and the difference is a reading.** That probe
was taken with six hours of the day still to run; the main pass fetched the same
window after it closed. B6-9 excludes the pair from its equality test for the
reason given in §5, and the difference is recorded here because it carries the
same signature as the hour-against-day probe of §2.2, eight months later:

| | probe, 18 hours in | full day | log difference |
|---|---|---|---|
| USD | 665.0 | 665.0 | **0** |
| ECU | 770.0 | 770.0 | **0** |
| BTC | 737.75 | 735.63 | -0.0029 |
| MLC | 445.17 | 450.17 | **+0.0112** |
| USDT_TRC20 | 688.24 | 675.74 | **-0.0183** |

The thick legs do not move at all and the thin ones move by one to two percent.
**§4.3's floor now has two independent observations behind it rather than one**,
taken eight months apart, and they agree about which instruments the window
touches.

**`PROBE_TAKEN_LIVE` names the excluded window**, `probe_is_comparable` is what
excludes it, and the manifest records both the exclusion and the deltas. A test
asserts that no other probe window was taken live, and that the live one is the
latest day any window covers, which is the only day a probe could have sampled
while it was running.

### 2026-08-19, the criteria ran. Two denominators replaced

**All seven pass.** The four gates and B6-13, B6-14 and B6-15.

**B6-13's floor was measuring the wrong estimator.** §4.3 registered the raw
hour-against-day dispersion as the floor and noted that it overstates. It does,
by a factor that is derivable rather than a matter of taste: the hour-against-day
difference has `(r - 1)` times the full-day median's variance, so the floor is
that dispersion over `sqrt(r - 1)`. The raw figure is `0.01571` and the converted
one `0.00328`, against a quantisation floor of `0.00178`.

**`r` is not observed and is not treated as known.** The registered value is the
window-length ratio of 24, and the criterion reports the value at which its
verdict would flip: **the first block stops clearing the band only if a single
hour holds 44% of a whole day's offers.** That is the same shape as B6-15's
critical spread, and for the same reason: a conclusion resting on an unobserved
constant should say what the constant would have to be to overturn it.

**B6-14's shares were statistics about a mixture.** The registered thresholds
were 95% and 90% of all days, and the series returned 75.2% and 62.4%, because
2021 to 2026 contains two orderings and not one. **MLC traded above cash dollars
for 225 days from 2021-06-10 and again for 194 days from 2022-02-09**, in the
period when the MLC stores were the only place to buy imported goods, and has
been below since 2022-12-11.

Cutting into regimes at a thirty-day minimum run gives three regimes for
`USD/MLC` and four for the tether, with 94.3% and 85.9% of days agreeing with
their own. **The threshold is then a permutation null rather than a number**:
999 seeded shuffles of the same signs, which preserve the marginal and destroy
the order. The null is degenerate. A memoryless sign that is positive three days
in four runs thirty days one way with probability 0.00018, so **every one of the
999 draws produced a single regime and an agreement equal to its own marginal**,
75.2% and 62.4% exactly, with zero variance. The observed values sit 19 and 24
points above the null's maximum.

**The sweep is reported because agreement alone is not falsifiable.** At a
one-day minimum run every run is its own regime and the agreement is one by
construction. `USD/MLC` holds at **three regimes from a 30-day minimum through
90**, which is what a blocky series looks like; the tether goes from two regimes
to sixteen as the run length falls from 90 to 7, which is what a less blocky one
looks like.

### 2026-08-19, B6-16 and B6-17 ran. One passes thinly, one is void

**B6-16 passes at 95.38% against 95%**, and the margin is a third of a
percentage point. §5 carries the reading, including the finding that all 61
misses fall on the same side of the book. **A1 is now measured on the dollar leg
and the measurement is weaker than the assumption it replaces**: not "the
published median lies between the two sides" but "it does on 95.4% of days, and
when it does not it is always above the ask". §3.3 keeps the assumption for the
euro, MLC and tether legs, for which no data exists.

**B6-17 is void.** Part (a) compares a round trip measured 2021-07 to 2025-03
against a critical spread measured 2025-12 to 2026-08, and the spans do not
overlap. §5 carries the ruling and the evidence: the answer depends on which
years are in the sample, 48 of the 56 exceeding days being in 2022 alone.

**This is a defect in how the criterion was written, and it was written after
its own arm's limitation had already been stated.** §5's B6-16/B6-17 preamble
says the order book ends before the window and that what carries across is a
property of the instrument. A round trip is such a property. **B6-15's critical
spread is not**: it is a statistic of the window. Setting one against the other
crosses exactly the line the preamble drew.

**What would make it a criterion.** Either an informal spread measured inside
B6-A's window, which no available source supplies, or a comparison of the round
trip against something else instrument-level. Neither is done here.

**Not observed, and genuinely open at the time of writing:**

- Every quantity in B6-13, B6-14 and B6-15 on the window as a whole. Nine to
  twenty externally published pairs per criterion have been seen and are in §5;
  the series has 2055 days and four of them have been seen from the instrument.
- Whether `USDT_TRC20` is median-based or EMA-smoothed. §2.6.
- Whether elTOQUE pools the two sides into one median. §3.3, and the Applied
  Economics paper is where it can be settled.
- The noise floor, both measurements. The procedure is registered and the value
  is not.
- Whether the fetch reproduces the thirteen probe windows. B6-9 exists to ask.
