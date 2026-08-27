# B6 availability check: Cuba as the carrier for `H⁰`, and what the central bank turns out to publish

**Not a pre-registration. A check, run before deciding whether to open a stage**,
as this project requires before a stage is opened, and the third of its kind after
`b3_slice_availability.md` and `b5_orphan_availability.md`. Both of those changed
the design of their stage rather than its budget. This one changes the
identification strategy.

Run 2026-08-12. Written **after** `docs/b4_directed_edges.md` and after B5
completed, because both change what has to be retrieved and what may be claimed.

**No headline quantity is computed here.** Availability, provenance, retrieval
mechanics and the arms are settled; the estimator and its thresholds belong to
the pre-registration.

---

## 1. What B6 is for, and why B5 could not do it

The gap this stage exists to close:

> `H⁰` has never had a positive empirical reading in this project, and this is
> harder than it looks. Theorem 5 gives the orphan currency a precise statement
> and B2's loop B was also ruled `H⁰`, but both are **negative** findings: that
> edge is not in the graph. The object of observation is **a missing quote**, and
> a missing quote is not distinguishable in data from an incomplete dataset. The
> only repair is prohibited by `b4` §5.2.

§14.3.1 accepted that argument and moved the `H⁰` arm out of B5 rather than
faking it, on the ground that the difficulty is structural and does not go away
by changing country. The escape route recorded there was a single one: **the leg
appears or disappears on a known date**, and Cuba was written down as the
candidate because 2025-12-18 supplied such a date.

**This check finds a second escape route, and it is stronger than the dated
switch.** See §4.

## 2. What the framework needs, in retrievable terms

From `b4_directed_edges.md` §5.1, with `rate` in local currency per dollar and
`bid < ask`:

```
S − S'  =  2 · log( mid_b / mid_a )                  the index part, the headline
S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)  ≤ 0  the friction part, reported beside it
```

and from §5.2, the criterion that decides which object is in front of you:

| what is observed | which object | what may be reported |
|---|---|---|
| both directions quoted, spread present | `H¹` with friction | `S − S'`, with `S + S'` beside it |
| one direction only, for some class | `H⁰` | reachability, and Theorem 5's one-sided bound |

So the shopping list is: **two mid quotes on the same conversion on the same day
for two classes of agent**, plus **two-sided quotes** wherever a friction column
is to be reported, plus **the eligibility rule in regulation** for anything that
is to be typed as `H⁰` rather than inferred from a gap in a file.

## 3. What exists, and it is more than the plan assumed

### 3.1 The Banco Central de Cuba publishes the agent index itself

Verified 2026-08-12, both routes, from a Windows build (the sandbox cannot
reach `*.bc.gob.cu`; this is an environment limit and not a property of the
source).

```
https://api.bc.gob.cu/v1/tasas-de-cambio/historico
    ?fechaInicio=YYYY-MM-DD&fechaFin=YYYY-MM-DD&codigoMoneda=USD
```

returns, with no key and no account,

```json
[{"fecha":"2025-12-19","tasaOficial":24,"tasaPublica":120,"tasaEspecial":410}]
```

and `https://www.bc.gob.cu/tasas-de-cambio` offers the same record as an XLSX
download over a chosen date range, with nineteen further columns.

**The three fields are three agent classes on one position edge.** `CUP ↔ USD`,
the same conversion, the same day, one publisher, and eligibility fixed by legal
status and transaction type rather than by price:

| field | segment | who it applies to | USD, 2025-12-18 | USD, 2026-08-12 | distinct values in 238 days |
|---|---|---|---|---|---|
| `tasaOficial` | I | state enterprises and legal persons, on designated operations | **24.0000** | **24.0000** | **1** |
| `tasaPublica` | II | natural persons, on the retained fixed schedule | **120.0000** | **120.0000** | **1** |
| `tasaEspecial` | III | the managed float opened 2025-12-18 | 410.00 | 624.00 | 62 |

**This is `b2_measurement.md`'s cell structure printed by a central bank.** One
position pair, several classes, terms differing by who the agent is and not by
what is being bought. It is the same shape `b5_orphan_availability.md` §3 found
in Argentina, with one difference that removes a confound rather than adding
one: Argentina's five classes came from five publishers, so a difference between
two classes was partly a difference between two reporters. Here every class is a
column of one table.

### 3.2 The nineteen channel columns, and what they are

The XLSX adds, for each segment: `Efectivo en Ventanilla` compra/venta,
`Efectivo en Aeropuertos/Hoteles` compra/venta, `Efectivo Domingos/Feriados`
compra/venta, `Transferencia Externa a Cuenta`, `Transferencia Externa a
Efectivo`, `Compra con Tarjetas Internacionales`, `Servicios de Divisas a CUP`,
`Transferencia de Divisas a CUP`, `Transferencia de CUP a Divisas`, `Retiro de
Efectivo CUP desde Cuenta en Divisas`, `Depósito de Efectivo CUP a Cuenta en
Divisas`, `Depósito de Efectivo en Divisas a Cuenta`, and three `USD Legal`
tiers.

**Every one of them is the segment's base rate times a fixed constant.** Checked
over all 238 days and all six files (USD and EUR, segments I, II and III): the
ratio varies by at most `3.5e-6`, which is the published rounding to four
decimals.

| column | `k` |
|---|---|
| `Efectivo en Ventanilla` compra / venta | 0.980 / 1.020 |
| `Efectivo en Aeropuertos/Hoteles` compra / venta | 0.970 / 1.060 |
| `Efectivo Domingos/Feriados` compra / venta | 0.965 / 1.060 |
| `Transferencia Externa a Cuenta` compra | 0.990 |
| `Transferencia Externa a Efectivo` compra | 0.970 |
| `Compra con Tarjetas Internacionales` compra | 0.980 |
| `Servicios de Divisas a CUP` compra | 0.990 |
| `Transferencia de Divisas a CUP` compra | 1.000 |
| `Transferencia de CUP a Divisas` venta | 1.015 |
| `Retiro de Efectivo CUP desde Cuenta en Divisas` compra | 0.970 |
| `Depósito de Efectivo CUP a Cuenta en Divisas` venta | 1.015 |
| `Depósito de Efectivo en Divisas a Cuenta` compra | 0.980 |
| `USD Legal No Efectivo` compra | 0.990 |
| `USD Legal Efectivo CUP Entrada/Salida` compra | 0.980 |
| `USD Legal Preferencial` compra / venta | 0.990 / 1.010 |

Three consequences, all of them design rulings rather than observations, and the
first is a prohibition.

**Ruled: no headline square may have both legs inside this table.** For two
channels `a` and `b` of the same segment, `S − S' = 2 log(k_b/k_a)`, the same
constant on every date, zero variance, no information. That is
`a3_asset_channel.md`'s construction identity appearing in a data source instead
of in a simulation, and **this project has already had such a quantity written
up as a confirmation once.** **The headline needs one
leg outside the table**, which is the informal market.

**Ruled: the same fact is a known-answer arm, and a stronger one than B5's.**
B5 had a single known answer, `tarjeta ≡ oficial × 1.30`. Here twenty columns
give one hundred and ninety pairs whose index part must equal `2 log(k_b/k_a)`
exactly, on every date, with `k` read from the published markup schedule and
never fitted. A pipeline returning anything else is broken before the headline
is read. The arm costs nothing and it exercises the same machinery the headline
uses.

**Ruled: the friction column on the formal leg is a policy parameter, and must
be labelled as one.** `b4` §5.1 describes `S + S'` as the two agents' round-trip
costs. On the Cuban formal leg the spread is a posted administrative markup, not
a dealer's inventory and counterparty cost. The headline `S − S'` is unaffected,
being invariant to friction common to both classes, but the column beside it
does not mean what the same column means in B2 or B3, and writing it up as if it
did would be the naming failure `MEASUREMENT.md` was written about.

### 3.3 The euro files, which are a free triangulation

USD segments I and II are exactly constant across the window. **The euro
equivalents are not**: EUR segment I moves 28.1424 to 27.7332 and segment II
140.7120 to 138.6660, both with 135 distinct values. The fixed rates are fixed
**against the dollar**, so their CUP value inherits `EUR/USD` from the
international cross. Any implementation that treats a "fixed" segment as a
constant will disagree with the euro file immediately. Recorded here so the
pre-registration can turn it into an assertion rather than a footnote.

### 3.4 The informal leg: elTOQUE's TRMI

| property | value |
|---|---|
| coverage | daily, 2021-01-01 to present |
| construction | median of a 24-hour window of buy and sell intentions, after removal of outliers; collected by NLP over social media and classified-ad sites |
| published methodology | yes, and peer reviewed: Vidal, Muñiz Cuza and Calas Torres, *Applied Economics*, October 2024, `10.1080/00036846.2024.2416091` |
| interface | `https://tasas.eltoque.com/v1/trmi`, verified live 2026-08-12 (returns 401 without a token) |
| access | free in beta; token by application form at `https://tasas-token.eltoque.com/`, two to three days |
| rate limit | one request per second since 2023-12-01, when the earlier two-per-minute and five-thousand-per-month caps were withdrawn |
| terms | attribution required; sublicensing and resale prohibited; local storage not restricted |

**The provenance is a tier above what B5 had on its informal leg.** Ámbito is a
newspaper's internal endpoint with no published construction. elTOQUE publishes
its construction and has had it refereed. `b5_orphan_availability.md` §3.1's
admission still applies in form, and it is a smaller admission here.

**One property remains unverified and it is load-bearing**: whether a requested
date range may lie in the past, or only in the trailing twenty-four hours. The
published FAQ says a custom range is permitted and may not span more than
twenty-four hours, which reads as the former, but one rule applies without
exception: **an endpoint that was inferred does not count as verified.** It can only be settled with a token in hand. If the answer is the
latter, the informal leg has no history, the stage collapses to prospective
collection, and B6 does not open on the window that matters. **This is the one
remaining gate.**

---

## 4. What this check found, and why it changes the identification

B6 was planned as an event study around a single switch on 2025-12-18, and that
plan flagged its own weakest point: the 2021 to 2025 queue was
**rationing rather than prohibition**, and a criterion for when a rationed,
posted-but-unavailable rate counts as an edge would have to be argued **outside
the data**, before looking at it, or the stage would not open.

**The regulatory record makes that worse than flagged, on both sides of the
switch.** Individuals could buy up to USD 100 at CADECA from 2022-08-23 at a
posted rate, rationed to whatever the branch had bought the previous day; the
queue moved to `MiTurno` in October 2024 with waits reported in months; CADECA
withdrew to hotels, ports and airports on 2025-04-18. After the switch the cap
of USD 100 per operation is retained, the appointment gate is retained, and on
2025-12-26 branches were still buying and not selling. Under "a quota is still
an edge" the edge exists on both sides and there is no transition; under "a
quota is no edge" it is absent on both sides and there is again no transition.
**No threshold on rationing intensity separates the two periods without being
chosen for that purpose.**

**The table in §3.1 removes the need for one.** Segments I, II and III are
quoted **on the same days**, so the contrast between an edge that is priced by
arbitrage and an edge that is not is **cross-sectional, not before-and-after**.
A macroeconomic confound that moves the peso moves all three columns; the
framework predicts that only one of them is held by a bound. The date of the
reopening stops being load-bearing, and with it the entire ambiguity above.

**And this is what defeats §12.11's objection, which is the reason the stage is
worth opening at all.** §12.11 says an `H⁰` determination cannot be made because
a missing quote is indistinguishable from an incomplete dataset. **Nothing is
missing from this file.** `tasaOficial` is published every day, to four
decimals, by the central bank. What is absent is the **reverse leg**: a holder
of pesos cannot acquire dollars at 24, and a holder of dollars acquired at 24
cannot resell them there. That absence is stated in regulation, as an
eligibility rule attached to designated operations, and it is therefore not an
absence of data. **The `H⁰` typing rests on the rule, and the rule is a
document.**

Theorem 5's unbounded ray is then directly visible rather than inferred. The log
distance from segment I to segment III runs from `log(410/24) = 2.84` on
2025-12-19 to `log(624/24) = 3.26` on 2026-08-11, rising monotonically over
eight months with no arbitrage relation objecting, because there is no closed
loop through segment I to sum. **Reporting that distance as an overvaluation
percentage is exactly the error `b1_theorem.md` §12.1 records**: an `H⁰` fact
under an `H¹` name. The contribution of this stage is not a better number for
the premium at 24. It is that at 24 the premium is not a defined quantity, and
that the framework says so in advance, from reachability, without reference to
the size of the number.

**What B6 therefore claims, and it should be written this way from the start**:
one country, on one day, supplies one edge on which a premium is a meaningful
`H¹` quantity and two edges on which it is not, and the framework separates them
a priori. The dated closure and reopening (2025-04-18, 2025-12-29) remain in the
write-up as narrative and as a robustness split of the window. They are no
longer the identification.

## 5. The registered prediction this check recommends, and the disclosure it owes

B6's prediction is required to be about **the existence or responsiveness of an
edge** and explicitly not about a premium collapsing,
because a premium is a magnitude and an edge is topology. Theorem 5 supplies a
form that meets this and carries no free parameter.

Theorem 5's forward direction bounds every coordinate difference by the
round-trip sum along the two directed paths. Written in quotes, the log distance
between two classes that can both transact in both directions must lie inside
the band formed by the two legs' own quoted spreads. So:

> **After the edge exists, the formal-to-informal log distance lies inside the
> round-trip friction band computed from the two legs' own quoted spreads. If it
> does not, the quoted reopening did not create an edge in the framework's
> sense, and the binding quota is the named candidate explanation.**

**Nothing in it can be slid after the fact.** The band is computed from the
spreads the two sources publish; it is not a chosen constant, a bandwidth, or a
fraction. It can fail, and it fails informatively in both directions.

**Disclosure, in the manner `b5_orphan_prereg.md` §6B.3 requires.** The
approximate size of the formal-to-informal gap during the post window was
already public when this form was chosen, from press reporting of the official
and informal rates on scattered dates. The defence is the one B5-15 used and the
only one available: the criterion is threshold-free, so prior knowledge of the
magnitude cannot have been used to position a cutoff. It is recorded here rather
than discovered at write-up.

## 6. Retrieval, and one property of the source that would have contaminated the estimator

### 6.1 The two paths agree, and the difference between them is structural

| | days | span |
|---|---|---|
| XLSX export | 238 | 2025-12-18 to 2026-08-12, every calendar day |
| REST API | 206 | 2025-12-19 to 2026-08-11 |

On the 206 shared dates there are **no value disagreements**. Of the 32 dates in
the XLSX only, 31 of the 31 that have a prior published day carry **exactly the
previous published value**. The XLSX is the API's record **forward-filled onto a
complete calendar**.

Range semantics were settled at the same time and there is no off-by-one: both
endpoints are inclusive. `2025-12-18` and `2026-08-12` are genuinely absent from
the API, the first being the announcement day and the second the current day,
which has not yet entered the historical record. A request for
`2025-01-01` to `2025-12-31` returns nine rows, all on or after 2025-12-19,
which confirms that **the series begins at the reform and there is no formal leg
for the pre-window**.

### 6.2 The publication schedule changes inside the window, and the change is correlated with the level

The absent days are not scattered. Sundays and Mondays are absent
systematically from the start of the series through **2026-02-23**; from
**2026-03-10** publication is near daily, with only five isolated gaps
afterwards (2026-05-30, 2026-07-07, 2026-07-08, 2026-07-19, 2026-07-20).

**Left alone this contaminates any daily estimator.** Run on the XLSX's 238
calendar days, roughly two days in seven in the first eleven weeks carry a
stale formal quote against an informal quote that moves every day, and almost
none do afterwards. The first period is also the low part of the rate's path.
The measurement error therefore carries a trend that is correlated with the
quantity being measured, and **nothing in the file reports this**: the forward
fill is silent, and the numbers are internally consistent. It is
`MEASUREMENT.md` failure mode 1 compounded with mode 5, of the coherent-drift
kind the meta-rule at the end of that file says a self-check will not catch.

**Ruled**, and this is a condition on opening the stage:

1. **The estimator is defined on publication days**, the dates the API returns.
2. The forward-filled dates are **recorded in the manifest and skipped by the
   loader**, following the `VALID_NAME` pattern: the code ignores what it should
   not read and the file is not touched.
3. The headline is computed **twice, on publication days and on all calendar
   days**, and both are reported, following `b5_orphan_availability.md` §7.6b. If
   they differ materially that is the finding and not a defect to be cleaned
   away.
4. The fetcher **asserts the reconciliation** rather than assuming it: every
   XLSX-only date must equal the previous published value, and any date on which
   the two paths disagree is an error and not a fill.

### 6.3 Cost, and the shape of the fetchers

**`fetch_bcc.py`.** One request returns the whole window (206 rows, 15.8 kB).
The nineteen channel columns need not be retrieved per day, since each is the
base times a constant; they are **reconstructed** from `tasaEspecial` and the
markup schedule, and the XLSX is retained as the validator of that schedule
rather than as the daily source. Resumable by date range, which is trivial here,
and required to detect truncation per the project's engineering rule 6.

**`fetch_eltoque.py`.** Roughly 2 050 daily requests for 2021-01-01 to the
present at one per second, so under an hour of wall clock, subject to §3.4's
unverified property. Resumable, and it must treat a retrieved day as
non-regenerable. Raw responses are cached under `data/raw/`, which
`.gitignore` already excludes, which is what keeps the terms in §3.4 satisfied:
the repository does not redistribute the series, it records how to obtain it.

**A reproducibility consequence, stated rather than hidden.** A third party
reproducing B6 needs their own elTOQUE token. The BCC leg is unconditionally
open. This is the same shape as B3, whose CIP input is a free but externally
derived series, and it is weaker than B2, whose input is a public bulk file.

## 7. The arms

**Known-answer arm: strong, and free.** §3.2. One hundred and ninety pairs of
channels whose index part is fixed by the published markup schedule, on every
date, in both currencies and all three segments.

**Cross-currency arm: free.** §3.3. The euro files must reproduce the fixed
segments as moving series and the markup vector as identical.

**Zero-calibration arm: available only prospectively, and this is a real
narrowing.** `MEASUREMENT.md` item 7 makes a zero calibration standard equipment
on every new carrier, and B5 built one from BNA's own posted rate against a
third party's report of it: one dealer, one counter, two collection paths. The
Cuban analogue exists, elTOQUE's formal-market page republishes CADECA's and the
banks' buy and sell quotes, **but that page carries current values only and no
history**. So the arm can be run **forward from the day collection starts** and
cannot be run over the window that carries the headline.

**The XLSX-against-API agreement in §6.1 is not a substitute and must not be
written up as one.** Two delivery paths for one record test the retrieval code,
not the collection. Calling it a zero calibration would be the failure
`MEASUREMENT.md` names in its own §7 discussion: a guard that is silent when it
should speak.

**No referee for the informal leg, by construction.**
`b5_orphan_availability.md` §7.4, as amended, requires a third-party series to
be checked against an independent referee over the whole window before it
carries anything. The referee there was BCRA. For an **informal** rate there is
no central bank to referee it, which is what makes it informal, and the same was
true of Ámbito's blue in B5. The mitigations are that elTOQUE's construction is
published and refereed in the literature, that the BCC's own segment III was set
at the reform close to the informal median, and that the failure mode the rule
was written against, a series that silently freezes, is testable within the
series itself. **The pre-registration must state this rather than inherit the
Argentine sentence unchanged.**

## 8. What this check does not settle

**The elTOQUE historical range.** §3.4. The one remaining gate, and it needs a
token.

**Whether the informal leg publishes usable two-sided quotes.** The API is
documented as returning median buy and sell values, which would make `S + S'`
computable on the informal leg; the public web page shows a single figure. Until
a response body is in hand this is unverified, and if only a mid is served the
friction column exists on the formal leg alone, which is the narrowing B5 took
in its §7.2 for MEP and CCL.

**The scope statement.** One country is one country, and the window is 238 days.
The result would read *the framework separates, a priori and by reachability,
one edge on which a premium is defined from two on which it is not, inside one
central bank's own table*, and it would not read *therefore multi-rate regimes
generally*. `a3b_initial_construction.md` §9 is the model.

**The estimator, the windows, and every constant.** To the pre-registration.

**`C → D` does not return.** §14.3.1 dropped the connectivity index because one
country cannot supply a `C` worth reporting and AREAER's FARI is annual. Cuba
adds two more points and the cross-section is still not there. Recorded as a
scope statement, not as a to-do.

## 9. Verdict

**Open the stage, conditional on the single gate in §3.4**, and with the
identification changed from what the stage was first planned as.

Dropped: the event study on 2025-12-18 as the identifying variation, because no
criterion separates a rationed edge before from a rationed edge after without
being chosen to do so.

Kept and strengthened: **the `H⁰` against `H¹` contrast, cross-sectionally,
inside one table on the same days**, with the informal market as the outside leg,
Theorem 5's friction band as a threshold-free registered prediction, and a
known-answer arm an order of magnitude stronger than B5's.

New, and it is the reason to run this rather than something else: **§12.11's
objection does not apply to this carrier.** The `H⁰` typing here rests on a
published eligibility rule, not on the absence of a quote from a file.
