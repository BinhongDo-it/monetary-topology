# Availability: Bolivia, and why it is B6's control rather than B6 again

**Written 2026-08-19, first pass. Second pass the same day: the regulation was
opened, the parallel-history question was settled, and §4 below was wrong. Third
pass the same day, on the Aduana Nacional comunicado supplied by hand: `RM 245` is confirmed
from an official document, and it brought a fourth priced edge with it (§4.6).**

**This carrier was assigned the number `B15` on 2026-08-19**, and the
pre-registration is `docs/b15_bolivia_prereg.md`. Nothing in `PROJECT_PLAN.md` or
`HANDOFF.md` held `B15` at the time it was assigned, and no `b15_*` or `b16_*`
file existed, so the number is free rather than merely unclaimed.

**This is an availability check. No criterion is registered and no reading is
computed.**

---

## 1. Why this carrier and not a second Cuba

`PROJECT_PLAN.md` §14.5 ruled out Latin American controls for B5 because a
country with one market rate leaves `S - S'` undefined, and §14.7 ruled North
Korea narrative-only for want of a referee. **Neither objection applies here.**
Bolivia has a published official rate with two sides, a published parallel rate
with two sides, and a dated regime change.

**What makes it a control rather than a repetition** is that the two carriers
look like they disagree about the outcome:

| | Cuba | Bolivia |
|---|---|---|
| the event | Segment III opens 2025-12-18 | the peg is abandoned 2026-06-26 |
| the instrument | Res. 127/2025 + Reglamento, BCC | RM 245/2026 (MEFP) **and** RD 88/2026 (BCB) |
| official before | 24 and 120, frozen | 6.86 compra / 6.96 venta, fixed |
| official after | a managed float, 410 rising to 628 | a daily transaction-weighted rate, about 9.7 rising |
| gap before | official II against informal, about 263% | about 42 to 43% |
| gap after | 6%, then 23%, then 5.6%. **Never closed** | **provisionally under 1%, sign not yet established** |
| B6's reading | posted two-way, transacted one-way. `a(t) > 0` on 207 of 207 publication days | to be established |

**A paper with one carrier invites the question whether the framework would say
the same of any controlled economy.** Two carriers, the same criteria, and
opposite verdicts is the answer to it.

**§4.4 below is the reason the last row now says "to be established" instead of
"the gap collapsed".** The regulation turns out to measure only one direction,
which is the same asymmetry B6 found in Cuba, arriving here by a different route.
Whether the verdicts are opposite is now an open empirical question rather than
a premise of the design.

## 2. What Bolivia has that Cuba's informal leg does not

**Two sides.** `b6b_eltoque_prereg.md` §2.1 is built around elTOQUE publishing
one median per instrument, which is why B6-B carries an index part and no
friction part and why **no positive cycle through the informal edge can ever be
certified there**. Bolivia's parallel rate is published as a bid and an ask by at
least two independent aggregators, and one of them serves both sides
historically at 15-minute resolution (§3.2.1).

**So the limit that governs all of B6-B does not govern here.** This carrier can
carry an `H¹` arm with friction on the informal side.

**And a real event study.** §14.4 records that B6 was designed as an event study
around 2025-12-18 and that the availability check killed it, because **there was
no formal leg before the reform**: the BCC's table begins 2025-12-19. Bolivia has
a formal leg throughout, back to 1940 (§3.1), and a parallel leg back to
2024-07-21 (§3.2.1). **The design B6 could not have is available here.**

## 3. The sources, and what is settled about each

**Read this section with §6.** Everything below was established through a
fetching tool that returns a summary of a page rather than the page. That is
enough to settle whether a source exists and what shape it has. **It is not
enough to record a number.** §6 says which of these still has to be opened by
hand before anything rests on it.

### 3.1 Official: Banco Central de Bolivia

**Settled, and it is generous.** `bcb.gob.bo/tiposDeCambioHistorico/?anio=YYYY`
serves a year of daily quotes with **VENTA and COMPRA as separate columns**, and
offers the same year in three formats:

```
https://www.bcb.gob.bo/tiposDeCambioHistorico/xls.php?anio=YYYY
https://www.bcb.gob.bo/tiposDeCambioHistorico/ods.php?anio=YYYY
https://www.bcb.gob.bo/tiposDeCambioHistorico/pdf.php?anio=YYYY
```

The year selector reaches back to **1940**. One request per year, so the whole
formal leg from the start of the peg era is a few dozen requests, against the
2,056 the informal leg of B6-B cost.

**The institutional detail B6 had to learn the hard way is here in a numbered
article.** `RD 88/2026` Art. 5.III: the BCB publishes the rate at 20:00 each
business day **and it takes effect the following day**. This is the exact
analogue of Reglamento Art. 10.1 in Cuba, which B6 established only by reading
the statute. **The date on a Bolivian quote and the day it governs are not the
same date**, and the annual table does not say which of the two its date column
carries. That is the first thing to settle against the source, and §6 records why
it cannot be settled from a summary.

### 3.2 Parallel: four sources, and they do not agree with each other

The load-bearing open question of the first pass was whether **a daily parallel
series spanning 2026-06-26** exists. **It does, from four independent
publishers, and the differences between them matter more than the fact that they
exist.**

#### 3.2.1 dolarbluebolivia.click: the one that carries the friction arm

```
https://api.dolarbluebolivia.click/v1/chart/all.csv
header: datetime,official_buy,official_sell,blue_buy,blue_sell
```

**Both legs and both sides in one file, at 15-minute resolution, from
2024-07-21.** This is the richest instrument found on either carrier. B6-B had
one median per day and no side at all.

Its method is stated as **the first advertisement, the best available offer**, on
Binance P2P. **That is a touch quote, not a central tendency**, which is what an
`H¹` friction arm wants and what `b6c_orderbook_availability.md` had to go to a
scraped order book to get for Havana.

**Two problems, both recorded before use.**

**The side labels run in opposite directions inside the same row.** The first
row of the file reads `6.86,6.96,10.17,10.13`: the official pair has
`sell - buy = +0.10`, the blue pair has `sell - buy = -0.04`. Read as one
convention the informal book is crossed, which no real quote is. **So one of the
two pairs is labelled from the counterparty's side**, and which one cannot be
decided from the header. This is `b4` §5.2 exactly: imputing the direction
imputes the quantity in dispute. **The convention has to be established from the
data**, by the same construction `havana_orders.which_side` uses.

**Bulk history sits in a grey zone in the terms.** The site permits reuse with
the attribution `Powered by dolarbluebolivia.click`, allows commercial use, sets
no visit limit on the public endpoint and asks for no polling faster than 60
seconds, **and says bulk downloads and historical data require registration for
its beta API**. `/v1/chart/all.csv` is served without a key and is therefore
public, but the two statements are in tension. **Register, or use paralelo.bo,
before pulling the whole file.** B6-B's handling of elTOQUE's terms is the
precedent: the terms go in the prereg and the key never leaves `.env`.

#### 3.2.2 paralelo.bo: the one with a licence

```
https://paralelo.bo/api/v1/historical.csv
header: date,median_bob_per_usd
```

Daily, **from 2024-01-01**, no key, no registration, **CC-BY 4.0** with a stated
citation string. It also exposes `/api/v1/rate` with median, compra, venta and
spread, and an MCP server at `https://paralelo.bo/mcp`.

**But the historical file carries the median alone.** Two sides live, one side in
history. **This is elTOQUE's limit again**, and it means paralelo.bo can serve as
the licensed index series and the audit check on the others, and cannot carry the
friction arm by itself.

#### 3.2.3 mauforonda/dolares: the auditable one

`github.com/mauforonda/dolares`, cited by paralelo.bo as the source it
reconstructs its earlier history from. Files include `buy.csv`, `sell.csv`,
`buy_oficial.csv`, `sell_oficial.csv`, `buy_oficial_completo.csv` and
**`buy_oficial_monto.csv`**, collected by `update.py` and `update_oficial.py` on
a scheduled workflow, over **25,627 commits**.

**This is the strongest form of the auditability `b5_orphan_prereg.md` §7.4
demands.** Every observation is fixed by a commit, so the series can be
reconstructed as of any past date and any silent revision is visible in the
history. B6-B had to build a manifest with two sha256 digests per day to get a
weaker version of this property. **Here it comes free.**

`buy_oficial_monto.csv` is the name to look at first: `monto` matches the amount
column of the BCB's own microdata endpoint (§4.4), which would make this repo a
running mirror of it.

#### 3.2.4 tipodecambiobolivia.com and the rest

Derived. It states its own source as Binance P2P plus the Dólar Blue Bolivia
historical CSV, which is §3.2.1 under another name. Its own referential series
begins 2025-12-01. `dolarbolivia.net`, `boliviablue.com` and
`dolarparalelobolivia.net` all resolve to the same underlying P2P book.

**So there is one market and several publishers of it.** The publishers disagree,
which is useful: the disagreement between them measures the publication noise
that `cuba_informal.noise_floor` had to estimate from a variance identity in
B6-B, because there was only one publisher of Cuba's informal rate.

### 3.3 Referee

B6-4 used the ECB's daily euro reference rate as an outside check on the BCC's
implied cross. The analogue here would be a cross the BCB publishes and an
outside source for the same cross. The BCB publishes `Bs / Euro` and `DEG`, so
the same construction is available in principle.

**Open**: whether the BCB's euro is an independent quote or the dollar times a
world cross, which is what B6-5 found for Cuba and what made B6-4 a check on the
pass-through rather than on the rate. **Under Art. 5.I the dollar rate is now a
transaction-weighted average of actual bank purchases**, so if the euro is a
world cross off that dollar, the pass-through check becomes sharper here than it
was in Cuba, where both legs were administered.

## 4. The regulation, corrected

### 4.1 The first pass named the wrong instrument, in the way it predicted

The first pass wrote **"`Resolución 245` of the Banco Central de Bolivia"**, from
a single secondary aggregator page, and flagged the number as unverified on the
strength of what had just happened with `Resolución 128/2025` in Cuba. **The flag
was right and the citation was wrong in exactly the predicted way.**

**There are two instruments, both dated 2026-06-26, and neither is what the first
pass wrote:**

| | issuing body | what it does |
|---|---|---|
| **Resolución Ministerial N° 245** | Ministerio de Economía y Finanzas Públicas | establishes the flexible regime and **delegates the transition to the BCB** |
| **Resolución de Directorio N° 88/2026** | Directorio del Banco Central de Bolivia | approves the **Reglamento de Operaciones Cambiarias** and Anexos I and II, and repeals Reglamento 63/2013 |

**The number 245 belongs to the Ministry, not the central bank.** The BCB's
instrument is 88/2026, and it is the one that contains every operative rule. A
search on "Resolución 245" plus "Banco Central de Bolivia" returns the pair
crossed, which is how the first pass got it.

**Same failure mode, third sighting.** `b8_pitfalls.md` should carry it as a
standing rule rather than a Cuba note: **cite by issuing body, by number, and by
year; a number alone identifies nothing in a jurisdiction with more than one
issuer.**

`RD 88/2026` is published directly by the BCB at
`bcb.gob.bo/webdocs/files_noticias/`. `RM 245` is published by the MEFP at
`economiayfinanzas.gob.bo/node/21723`, which refused the fetch on a certificate
error.

**The identity of `RM 245` is nevertheless settled, from a document on disk.**
`data/raw/bolivia/aduana_comunicado_2026-06_RM245.pdf`, a comunicado of the
**Aduana Nacional** on Presidencia del Estado Plurinacional letterhead, La Paz,
Junio de 2026, opens:

> `En virtud de lo dispuesto mediante la Resolución Ministerial N° 245 de`
> `26/06/2026 que establece un régimen cambiario flexible, la Aduana Nacional`
> `recuerda a los Operadores de Comercio Exterior que ...`

**A Bolivian state body citing the instrument by number, date and ministerial
character.** The number, the date and the issuing level are confirmed; the
resolution's own articles are still unread (§6).

### 4.2 What RD 88/2026 says about the rate

**Art. 5.I.** `El Tipo de Cambio Oficial (TCO) se determinará diariamente como
resultado del promedio ponderado de las operaciones cambiarias de compra
realizadas por los Bancos Múltiples, los Bancos PymE y el Banco Público con sus
clientes.`

**Anexo II** gives the formula and the filter: purchases of USD against
bolivianos, **00:00 to 17:00 of each business day**, inter-institution trades
excluded, weighted by amount.

```
TCO_t = Σ_i (TC_it × M_it) / Σ_i M_it
```

**Art. 5.III.** `Cada día hábil a horas 20:00 el BCB publicará en su página web
el TCO que será vigente al día siguiente.`

**Art. 6.** `Se denomina valor referencial de venta del USD al que resulte de
sumar al TCO 10 centavos de boliviano.`

**No band.** The Reglamento sets no limit on how far the TCO may move in a day.

### 4.3 What that makes measurable

**The official leg is a genuine two-way posted edge with a legally capped
symmetric part.** Art. 6 fixes the ask at `TCO + 0.10` Bs and forbids exceeding
it. In the notation of `b1_theorem.md` Theorem 6 the two-way official edge splits
into `ŵ` and `ω̄ ≤ 0` with

```
ω̄  ≥  - log( 1 + 0.10 / TCO )
```

a bound the statute supplies rather than the data. At a TCO near 9.7 that is a
round-trip cost of about **1.03%**, against Cuba's `K_VENTA = 1.020`, a 2.0%
markup fixed by Res. 127 Art. 8.1 and 8.2. **Two administered spreads, both
priced in the statute, differing by a factor of two.** That is a comparison the
one-carrier version of the paper could not make.

**And the official bid is a transacted price.** Art. 5.I builds the TCO out of
operations that actually happened, weighted by their amounts. B6's entire finding
in Cuba was **posted two-way, transacted one-way**, established indirectly
because the BCC posts an administered number and publishes no transaction record.
Here the posted number **is** the transaction record on one side.

### 4.4 The asymmetry, which is the reason §1's last row changed

**The TCO is built from purchases only.** Art. 5.I says `operaciones cambiarias
de compra`, Anexo II says purchases of USD against bolivianos, and the BCB's own
microdata endpoint follows:

```
https://www.bcb.gob.bo/tco_reporte_detalle_historico.php
```

which serves, **per bank and per rate tier, the rate, the number of operations
and the amount in USD**, with a CSV export and a date selector running from
2026-06-26. **It carries compra only.**

**So the sale side has no published transaction record at all.** The ask is a
derived number, `TCO + 0.10`, and nothing in the Reglamento requires that anyone
ever trade at it, or reports it if they do.

**This is the same shape B6 found in Cuba, reached from the opposite direction.**
In Cuba the ask was posted and the question was whether it was walked, answered
by `a(t) > 0` on 207 of 207 publication days. In Bolivia the ask is not even
posted as an observation, it is computed from the bid, and the transaction record
that would settle whether it is walked is the one thing the regulation does not
collect. **The carrier may therefore agree with Cuba rather than contradict it**,
and the first pass's table was pre-committing to a contradiction it had not
measured.

**What settles it is one arithmetic on numbers this check has not yet read from
source.** With the parallel ask at `p_a` and the official ceiling at
`TCO + 0.10`,

```
a(t)  =  log p_a  -  log ( TCO + 0.10 )
```

is the same statistic `cuba_informal.a_statistic` computes, with the Art. 6
ceiling in place of Cuba's `K_VENTA`. On the provisional figures the first pass
recorded, a parallel ask near 11.57 against a TCO near 11.52 puts the ceiling at
11.62 and makes `a(t)` **negative**: the informal ask sits **inside** the legal
official spread, so the official ask does not bind and there is no cycle to
certify. **That is the sharp opposite of Cuba and it is one subtraction away from
being established.** It is not established here because neither number has been
read from its source (§6).

### 4.5 Still not read

**Whether banks may now sell to individuals, and on what condition.** This was
open question 3 of the first pass and it is still open. Art. 6 caps the price of
a sale without saying who may buy. In Cuba the answer turned on a Circular that
was not in the Gaceta at all, and `b6_cuba_prereg.md` §2.1.1a records that the
return leg was opened for CNAs and MSMEs and left closed for natural persons.
**The Bolivian analogue is exactly the question to put to Anexo I**, which the
summary lists as the Reglamento's own body and which has not been read
article by article.

### 4.6 A fourth priced edge, which arrived with the comunicado

**The Aduana Nacional document supplied by hand is not only a confirmation. It
carries a rule that puts a second formal position on the graph.**

It quotes `Artículo 20 del Reglamento de la Ley General de Aduanas`, approved by
`Decreto Supremo 25870`:

> `los valores expresados en moneda extranjera deberán ser convertidos en moneda`
> `nacional al tipo de cambio oficial del Banco Central de Bolivia, vigente al`
> `último día hábil de la semana anterior de la fecha de aceptación de la`
> `declaración de mercancías por la Administración Aduanera.`

and from 06/07/2026 onward specifies which side:

> `se aplicará el tipo de cambio oficial de venta publicado por el Banco Central`
> `de Bolivia que se encuentre vigente al último día hábil de la semana anterior`

**So the rate at which an importer's tax base is struck is not the rate of the
day. It is the previous week's closing venta, held flat for a week.** Formally,

```
TC_aduana(t)  =  TCO_venta( last business day of the week before t )
```

**This is Cuba's Art. 10.1 forward-fill again, with a week's step instead of a
day's, and applied to a tax base instead of a transaction.** `b6_cuba_prereg.md`
records Reglamento Art. 10.1/10.2 as forward-fill written into law. Bolivia
supplies the same operator at a coarser grain, and unlike Cuba's it is **not** a
price anybody can trade at. It is a position occupied by exactly one agent class,
`Operadores de Comercio Exterior`, at a number no other agent gets.

**Which makes it the cleanest instance of a priced edge this project has found.**
The edge from the spot official position to the customs-valuation position is
deterministic given the published series, it is dated, it is granted by statute
to one class of agent, and during a rising regime it is strictly favourable to
that class. Under Theorem 6 it is a one-way edge with a known weight, and its
holonomy around the cycle **buy dollars at market, import, value at
`TC_aduana`** is computable from two published series and nothing else.

**And the transition week prices it.** The comunicado fixes `6,96 Bs/USD vigente
al 26/06/2026` for every declaration accepted in the week `29/06/2026` to
`05/07/2026`, which is the week the peg was already gone. **A statutory
conversion at the old peg, for one week, while the market had moved.** That is a
single dated observation of the edge at its widest, and it is exactly the kind of
event `b8_pitfalls.md` warns not to reconstruct from press.

**Two flags on this, both about the document rather than the rule.**

**It supersedes a predecessor.** The last line reads `Se deja sin efecto el
comunicado publicado en fecha 27/06/2026`. The Aduana changed its position within
days of the reform, and **the 27/06 text has not been seen**. Whatever it said is
the counterfactual for this rule, so it goes on the get-list (§6).

**Its own date is imprecise.** The sheet is signed `La Paz, Junio de 2026` with
no day, its filename carries `19 JUN`, its PDF `ModDate` is `2026-06-29`, and it
supersedes a comunicado of `27/06/2026`. **A document cannot supersede one
published eight days after it**, so the `19 JUN` in the filename is not this
sheet's date of issue. **Cite it by body, subject and the dates in its text**, and
not by the filename. This is the same rule §4.1 arrived at for resolutions,
reaching a second kind of document.

## 5. What is settled and what is not

**Settled:**

1. the carrier exists, and the event has a date and **two** instruments, both
   now identified by issuing body and number;
2. the official rate is published with **both sides** and history to **1940**,
   with a one-request-per-year export in three formats;
3. a daily parallel series spanning 2026-06-26 exists from **four** publishers,
   one of them **with both sides at 15-minute resolution from 2024-07-21**, one
   of them **CC-BY 4.0**, and one of them **a git repository with 25,627
   commits**;
4. the rule for how the official rate is computed, when it is published and when
   it takes effect, with article numbers;
5. the official spread is **capped by statute** at 0.10 Bs, which bounds `ω̄`
   from the law rather than from the data;
6. **the official transaction record covers purchases only**, so the sale side
   is derived and unobserved;
7. **`RM 245` is confirmed by number, date and ministerial character** from an
   official document on disk, which retires the first pass's misattribution;
8. **a fourth priced edge**, `Art. 20` of `D.S. 25870`, which strikes the customs
   tax base at the previous week's closing venta and is granted to one agent
   class alone (§4.6).

**Not settled, in the order that decides whether the stage opens:**

1. **which side is which in `all.csv`**, since the official and blue pairs run in
   opposite directions and `b4` §5.2 forbids imputing it;
2. **whether the annual table's date column is the publication date or the
   vigencia date**, given Art. 5.III;
3. **what Anexo I says about who may buy dollars from a bank and what rations
   them**, which is the Cuban question in Bolivian form. §7.6 restates it: Cuba's
   individual channel is rationed by a queue governed by no published
   instrument, so the comparable question here is whether Bolivia's rationing is
   on paper at all;
4. the **articles** of RM 245 from the MEFP itself, its identity now being
   settled and only its content outstanding;
5. the superseded **Aduana comunicado of 27/06/2026**, which is the
   counterfactual for §4.6;
6. whether the BCB's euro is an independent quote or a pass-through;
7. the terms position on bulk history at dolarbluebolivia.click.

**The stage opens on 1, 2 and 3.** Items 4 to 6 gate particular arms, not the
carrier. The first pass said the stage does not open until a parallel series and
the regulation were settled; **both are now settled**, and what replaced them are
three questions about how to read sources that are already in hand.

## 6. How each thing above was established, and what that is worth

**B6 is the reason this section exists.** Its `H⁰` typing rested for two months
on a citation nobody had opened, and when the text was finally read the
load-bearing sentence turned out to be false.

**Everything in §3 and §4 came through a fetching tool that returns a language
model's summary of a page.** That is sound evidence that a source exists, what
its endpoints are, and what shape its columns have. It is **not** evidence of any
particular number, and one read in this pass proves the point: the BCB's 2026
annual table was reported as carrying a value for **31 August 2026**, a date that
has not happened. The same read put the peg still in force on 29 June, against
press reporting of Bs 9.73 for that Monday. **Both readings are discarded.** No
number from the BCB annual table is recorded in this document.

**What has to be opened by hand before anything rests on it:**

| item | why |
|---|---|
| `RD 88/2026` PDF | the four articles in §4.2 are quoted from a summary. They are load-bearing and they must be read from the PDF |
| `RM 245` from MEFP | never fetched, the publisher refused on a certificate error. Its identity is settled by §4.1, its articles are not |
| `D.S. 25870` Art. 20 | quoted at second hand by the Aduana. The rule in §4.6 is load-bearing enough to want the decree itself |
| the Aduana comunicado of `27/06/2026` | superseded and unseen |
| `xls.php?anio=2026` and `?anio=2025` | the only way to settle the date-column question, and the only trustworthy source of the values |
| `all.csv` in full | the fetch returned 1,162 lines ending mid-number on 2024-08-01, which is a truncation and not the end of the file |
| `tco_reporte_detalle_historico.php` CSV | the microdata behind Art. 5.I, and the thing that makes §4.4 checkable |

**One item in this document is in the other class, and it is the only one.**
`data/raw/bolivia/aduana_comunicado_2026-06_RM245.pdf` was supplied by hand and
read from disk, text layer and page image both. Every quotation in §4.1 and §4.6
is from that file. **It settled the identity of `RM 245` on the first reading and
produced a rule nobody had gone looking for**, which is the argument for the
pattern rather than a coincidence of it.

**The pattern is the one B6 settled into and it works: the assistant finds the
source and states what it should contain, it is downloaded by hand, and the file is
read from disk.** The Gaceta went that way on 2026-08-19 and immediately falsified a
claim that had stood for two months. The Aduana comunicado went that way the same
day and added a priced edge to the design.

## 7. What B6 hands over, and why each item dies here

**B6 closed on 2026-08-19 with one live to-do of its own.** Everything else that
was still open on it was open for a reason that does not survive the change of
carrier. This section is the transfer, item by item, and it is the argument for
the second carrier stated in a form that can be checked rather than asserted.

### 7.1 Assumption A1

**B6 assumed `bid ≤ m ≤ ask`** because elTOQUE publishes one median per
instrument per day and no side at all. The whole one-sided rule of
`b6b_eltoque_prereg.md` §3.4 rests on it, and with it the fact that **B6-B can
never certify a positive cycle**.

B6-16 measured it on the dollar leg against the Havana order book and it holds on
**95.38%** of 1,321 days, with **61 misses, every one of them above the ask**.
B6-16-S reweighted by volume and it holds on **98.18%**, with **7 above and 17
below**, which turns a one-sided breach into two-sided noise. **So the
one-sidedness was the weighting.**

**Two residues, and both are structural.** A1 stays an assumption on the euro,
MLC and tether legs, because the order book covers the dollar only. And the
measurement runs 2021-07-23 to 2025-03-04, which **ends before B6-A's window
opens on 2025-12-19**, so the span on which A1 is used is the one span on which
it was never checked.

**Here A1 is not assumed and not measured. It is not needed.**
`api.dolarbluebolivia.click/v1/chart/all.csv` publishes both sides directly, so
there is no median to sandwich and no substitution to bound. **The rule that
governs everything B6-B may claim has no analogue on this carrier**, which is
also why this carrier can carry a friction arm and B6-B cannot.

### 7.2 The unobserved offer ratio `r`

B6-13 de-noised its floor by the identity `Var(m_1h - m_full) = (r - 1) ·
Var(m_full)` and reported a **critical `r` of 44%**: the reading flips only if one
hour holds 44% of a day's offers. **`r` was never observed.** elTOQUE gives one
median a day, and the order book's `time_stamp` turned out to be a sequence
counter rather than a clock, so the intraday count is not in the data either.
**B6 closed the item as impossible.**

**Here `r` is not a nuisance parameter.** The series is native at **15 minutes**,
so the intraday distribution of offers is the data rather than something the data
has to be de-noised against. The critical-ratio construction becomes a direct
count.

### 7.3 The round trip that could not be compared to anything

**B6-17 is the stage's one VOID**, and its reason is not a defect: the informal
round trip is measured 2021-07-23 to 2025-03-04 and the critical spread it would
be compared against is measured from 2025-12-19. **The spans do not overlap and
cannot be made to**, because the order book ends before the window opens. The
distribution stands as a reading with nothing to judge it: median 0.0148, p90
0.0392, p99 0.0747, max 0.1214 over 1,321 days.

**Here both legs run to today.** The official series is current and the parallel
series is current, so the round trip and the threshold it is judged against are
measured on the same days. **B6-17 is not repaired here, it is re-run under
conditions that let it return a verdict.**

### 7.4 Whether anybody trades at the posted rate

**The most load-bearing thing B6 does not know is the volume, and as of
2026-08-19 it is known that it cannot be known.** An external search settled it:
`bc.gob.cu/indicadores` and the exchange-rate pages carry the daily rate per
segment and nothing about quantity. No volume, no operation count, no book.
**So the item moves from "not retrieved" to "not published"**, which is a
stronger statement and a worse position: B6-15's `a(t) > 0` on 207 of 207 days is
an inference from prices about whether an edge is walked, and the institution
that posts the edge withholds the one series that would settle it.

**Here the transaction record is published by statute.**
`tco_reporte_detalle_historico.php` gives, per bank and per rate tier, **the
rate, the number of operations and the amount in dollars**, because `RD 88/2026`
Art. 5.I builds the official rate out of exactly those operations.

**And the asymmetry is the finding rather than a gap** (§4.4): the record covers
**purchases only**, so the same question B6 could not answer about Cuba's posted
ask is, here, a question the regulation itself declines to collect evidence on,
while collecting it in full for the other direction. **That is a sharper
statement than B6 could make, and it is made from the statute rather than from
prices.**

### 7.5 The referee that failed

**B6-4 is registered as a failure and is not repaired.** It compared the BCC's
implied euro cross against the ECB daily reference rate and 3 of 147 days fell
outside the band, on days when EUR/USD moved about a percent, because **the BCC
prices off the previous business day**. `HANDOFF` §3.2 item thirteen forbids
swapping in a lagged comparison, since choosing the alignment that makes the
criterion pass is fitting.

**Here the alignment is not a choice.** `RD 88/2026` Art. 5.III states it: the
rate is published at 20:00 and is `vigente al día siguiente`. And `D.S. 25870`
Art. 20 states a second one for a different agent class, at a week's lag (§4.6).
**The lag that sank B6-4 is a numbered article here**, so the referee arm can be
registered with its alignment fixed by statute before any comparison is drawn.

### 7.6 What does not transfer

**The Cuban individual channel.** `b6_cuba_prereg.md` §2.1.1b to §2.1.1d
settled it on 2026-08-19 and the answer is not the one this section was drafted
against. **Natural persons do reach the float**, at the CADECA counter and the
bank cash window, from the day of the reform, capped at **USD 100 per operation**
and rationed by a queue. **No circular opens it; the cap is an administrative
practice inherited from the 2022 cash window**, and its only public statement is
a central bank official's answer to a journalist. The two classes therefore
differ in **what rations them and in what kind of instrument does the rationing**,
not in whether they have the edge.

**That stays with B6 and it changes what the Bolivian analogue is.** The question
to put to Anexo I of `RD 88/2026` is no longer "may natural persons buy" but
**"what rations them, and is the rationing published"**. §5 item 3 above is
restated in those terms. **Cuba's answer is a queue governed by nothing on
paper.** Whether Bolivia's is a published formula, a quantity, or nothing at all
is the single most comparable thing the two carriers can be asked.

**`MARKUP_SCHEDULE`.** B6's only live to-do of its own, and it is Cuban
arithmetic that has no counterpart here: `guard_paths_reconcile` compares the
API against 39 hand-downloaded XLSX exports still at their old snapshot, and it
needs those files re-downloaded over the extended window. **It stays with B6.**
