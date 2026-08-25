# B15: Bolivia, the control carrier. Results

**Design file: `docs/b15_bolivia_prereg.md`. It is sealed and nothing here edits
it.** Every section below carries `RUN` and the `DESIGN` section it answers, and
a reading that is later overturned is recorded in a `Voided` block in its own
section rather than by changing the design.

**State as of 2026-08-21T13:10:00Z. Twelve criteria, twelve verdicts, stage
closed. The verdict table is §13.4 and it is the section to read first if you
are reading one.**

**This file is written forward and the later sections govern.** §8 was the
verdict table when eleven criteria had run, §9.5 when the clock was corrected,
and §13.4 now. Every section a later one overturns carries a dated pointer at
its head and keeps its numbers; none is rewritten.

**The order of the argument, and where it turns twice.** §0 and §1 are the two
statutes read from source and the endpoint probe, both before any criterion. §2
is arms I and II, §3 arm IV, §4 arm III on the post-event segment, §5 B15-6, §6
B15-9, §7 the euro leg's absence, §8 the first verdict table.

**§9 is the first turn**: S3's timestamp clock was being set by a two-hour test
fed from another run's manifest, and correcting it made B15-4 void and suspended
arm III. §10 closes the get-list, §11 runs B15-12, §12 shows the comparison
survives the suspension.

**§13 is the second turn**: B15-4 is re-decided on the publisher's own two date
columns, an instrument that never touches the clock §9 corrected, and arm III
runs. **§9's account of why the registered instrument failed is not withdrawn.
It is the reason for the re-decision.**

---

## 0. The regulation, read from the PDFs

```
RUN:    2026-08-19T22:30:00Z
DESIGN: §11 row two, §9, §2.3, §3.4
```

**Both instruments were supplied by hand and read from disk**, text layer and
page image, the pattern `bolivia_availability.md` §6 records as the only one
that has ever settled anything on this carrier or on B6.

- `RD N° 88/2026`, Directorio del Banco Central de Bolivia, La Paz,
  26 de junio de 2026. Seven pages: four of resolution, `Anexo I` the
  Reglamento de Operaciones Cambiarias in seven articles, `Anexo II` the
  methodology.
- `Resolución Ministerial N° 245`, Ministerio de Economía y Finanzas Públicas,
  La Paz, 26 JUN 2026, signed José Gabriel Espinoza Yáñez. Four pages, three
  operative points.

**§11's one honest exposure is closed and no registered value moves.**

### 0.1 What the summary had right

| | summary | PDF | verdict |
|---|---|---|---|
| Art. 5.I | TCO is the amount-weighted average of **purchase** operations by Bancos Múltiples, Bancos PyME and the Banco Público with their clients | word for word | **confirmed** |
| Art. 6 | `valor referencial de venta` = TCO + **10 centavos de boliviano** | word for word, and the sentence that follows forbids financial entities selling above it | **confirmed** |
| Anexo II | purchases of USD against bolivianos, **00:00 to 17:00** of each business day, inter-EIF trades excluded, weighted by amount | word for word | **confirmed** |
| Anexo II formula | `TCO_t = Σ(TC_it × M_it) / Σ M_it` | rendered as an equation and identical | **confirmed** |

**So `STATUTORY_SPREAD = 0.10` is a statute and not a summary of one, and
B15-5 and B15-7 stand exactly as registered.** §11 said that if the PDF
disagreed, those two criteria would change and the old value would be left
visible in §12. It does not disagree.

### 0.2 What the summary truncated, and what it changes

**Art. 5.III, in full, with the clause the summary dropped in bold:**

> `Cada día hábil a horas 20:00 el BCB publicará en su página web el TCO que`
> `será vigente al día siguiente` **`para las operaciones del sector público y`**
> **`del BCB y para los registros contables y de valoración.`**

**And Art. 5.IV, which the summary did not carry at all:**

> `El TCO será la referencia para las operaciones cambiarias que realicen los`
> `agentes económicos y el público en general.`

**There are two vigencia regimes in one article and they are split by agent
class.** The public sector, the BCB, and accounting and valuation get a dated
rule: the number published at 20:00 on day `t` governs day `t+1`. Everyone else
gets a *reference*, and the statute gives it no date of effect at all.

**What this does to B15-4**: the test is unchanged, because it measures when the
published number steps and that is one observable. What changes is the **reading
of a pass**. The convention B15-4 can identify is the one the statute dates, and
the statute dates only the public-sector one. A `20:00` step and a `00:00` step
still separate publication from vigencia; the vigencia so identified is
`sector público` vigencia, and the criterion's record must say so.

**What this does to B15-9**: it composes cleanly. A customs valuation is a
public-sector valuation, so `D.S. 25870` Art. 20's weekly forward-fill sits on
top of a `t+1` rule rather than beside an undated one.

**And it is the same shape B15-9 measures, found a second time.** One published
number, different agent classes, different dates of effect. B15-9 was registered
because the customs edge has that structure. Art. 5.III and 5.IV say the statute
has it twice.

### 0.3 What the summary did not carry at all

**Anexo II §4, publication.** Two sentences, both load-bearing, neither in the
summary:

> `El valor será redondeado al segundo decimal para su publicación y será`
> `válido para el siguiente día hábil.`
>
> `En el caso de los días sábados, domingos y feriados, el TCO será el`
> `correspondiente al día hábil anterior.`

**The rounding is a statute.** §7.1 registered three things to rule out before a
B15-6 disagreement could be called a finding, and the third was "the published
value being rounded to a coarser precision than the recomputation". It is now a
stated fact rather than a hypothesis: **the comparison is defined at two
decimals by Anexo II.** `TCO_RECOMPUTE_SHARE = 0.99` does not move; what is
fixed is the precision the recomputation is compared at, which was previously an
implementation choice.

**The weekend rule is a third statutory forward-fill.** Saturdays, Sundays and
holidays carry the previous business day's TCO by law.

**This does not touch `guard_no_fill`,** and the distinction is worth writing
down because it is easy to collapse. `guard_no_fill` governs **my own** code: I do
not synthesise a value for a date the source did not serve. A weekend row in the
BCB's own table carrying Friday's number is **the publisher reporting what the
statute says the rate is on that day**. It is a published value with a named
provenance, not a fill. It is recorded as a property of the series.

**Three forward-fill operators are now on the table, at three grains, across two
carriers:**

| carrier | instrument | grain | applies to |
|---|---|---|---|
| Cuba | Reglamento Art. 10.1 / 10.2 | one day | a transaction price |
| Bolivia | `RD 88/2026` Anexo II §4 | weekend and holiday | the TCO itself |
| Bolivia | `D.S. 25870` Art. 20 | one week | a customs tax base |

**Art. 5.II**, also absent from the summary: the 17:00 cutoff is an **ASFI
reporting deadline carrying sanctions for non-compliance**, not a data-vintage
convention.

**Art. 7**, absent from the summary and directly on B15-6's falsification:

> `El suministro de información falsa o la omisión selectiva de operaciones`
> `será sancionado como infracción bajo normativa vigente.`

**The statute names selective omission as the thing it polices**, which is
precisely the mechanism by which a recomputation from S2 could disagree with the
published value. §7.1's list of things to rule out gains a fourth entry that is
not a defect but a named, sanctioned category in the instrument itself.

**Art. 2 (Alcance)**: the Reglamento is applied by public-sector entities, by
ASFI-authorised financial entities, **and by private natural and legal persons
carrying out exchange operations**.

### 0.4 Anexo I, which is the question §4.5 and §9 left open

`bolivia_availability.md` §4.5 and `b15_bolivia_prereg.md` §9 both recorded that
whether banks may sell to natural persons, and on what condition, was "exactly
the question to put to Anexo I", which had not been read article by article.

**It has now been read. `Anexo I` is the Reglamento de Operaciones Cambiarias
and it is seven articles**: Objeto, Alcance, Política Cambiaria, Moneda de
Referencia del Tipo de Cambio, Tipo de Cambio Oficial, Valor Referencial de
Venta, Supervisión y Cumplimiento.

**There is no article about who may buy. No quantity, no eligibility condition,
no cap, no rationing of any kind.** Art. 6 caps the **price** and says nothing
about quantity and nothing about to whom.

**`b8_pitfalls.md` entry 52 governs how that is written down**, and it was
written the day before this reading, off a case where a primary source's silence
was allowed to overwrite something the repository already knew. So:

> **The Reglamento de Operaciones Cambiarias creates no quantity limit and no
> eligibility condition on the sale of USD. It caps the price and nothing else.
> It does not follow that nothing rations.** What follows is that **this
> instrument** does not, and that on the sale side the only thing it publishes
> is a ceiling.

**The comparison §7.6 asked for can now be made from two statutes rather than
from one statute and a queue.** §7.6 restated the question as "what rations
them, and is the rationing published".

| | Cuba | Bolivia |
|---|---|---|
| the entitlement | granted, Reglamento Art. 36 and Res 127 Art. 21 | not addressed; Art. 2 brings natural persons into scope and no article restricts them |
| the quantity, on paper | **deferred**: Art. 37 and Art. 43 move every limit into `Circular`, a document class that is not published | **not created**: no article of the Reglamento states a quantity |
| what is published on the sale side | a fifteen-channel markup schedule | a price ceiling, `TCO + 0.10` |
| the individual limit | USD 100 per operation, in no instrument, inherited from 2022, stated on the record by an official | no counterpart in this instrument |

**The two are not the same shape and the difference is the finding.** Cuba's
limits exist and are hidden, because the drafting moves them into the one
document class the public does not see. Bolivia's Reglamento has nothing to hide
on this axis because it defers nothing: it does not create a quantity at all.

**What stays open, and it is a different question from the one that closed**:
whether anything else rations, in ASFI regulation, in bank practice, or nowhere.
Nothing in §5 depends on the answer, and §9's sentence that reading Anexo I
"will interpret B15-7 rather than change it" holds.

### 0.5 RM 245, and the one-sidedness has a provenance

**Three operative points, read in full:**

> **`PRIMERO.-`** `Establecer un régimen cambiario flexible, a efectos de`
> `fortalecer la estabilidad macroeconómica, preservar la competitividad`
> `externa y contribuir al equilibrio de la balanza de pagos.`
>
> **`SEGUNDO.-`** `El tránsito al nuevo régimen cambiario será ejecutado por el`
> `Banco Central de Bolivia, en el ejercicio de las atribuciones y competencias`
> `conferidas por la Ley N° 1670 de 31 de octubre de 1995, teniendo como base`
> `el reconocimiento de la oferta y demanda diaria de divisas en el sistema`
> `financiero.`
>
> **`TERCERO.-`** `Disponer la publicación de la presente Resolución en medios`
> `de prensa de circulación nacional y en el sitio Web.`

**And this recital, from the same document:**

> `Por ello, el precio promedio de las operaciones de compra y venta de moneda`
> `extranjera registradas por las entidades financieras constituye una`
> `referencia adecuada para la determinación del tipo de cambio oficial en un`
> `régimen cambiario flexible.`

**The delegating instrument names both sides. The implementing instrument built
one.** `SEGUNDO` gives the basis as `oferta y demanda`; the recital gives it as
the average of purchase **and sale** operations. `RD 88/2026` Art. 5.I and
Anexo II §1 and §2 both say `únicamente` operations of **purchase**, and the
BCB's microdata endpoint carries compra and nothing else.

**So the asymmetry `bolivia_availability.md` §4.4 found in the published record
is not an artefact of what the BCB happens to serve. It was introduced between
the ministerial delegation and the central bank's reglamento, and the two
instruments carry the same date.**

**Three limits on how hard that may be read, and they are not decoration.**

1. **A considerando is a recital.** `SEGUNDO`'s `oferta y demanda` describes the
   basis for the transition and is not a formula. Nothing here establishes that
   the BCB acted outside its delegation, and this document does not claim it.
2. **What is established is narrower and is enough**: the two-sided reading was
   available, was written down by the delegating authority on the same day, and
   the implementing rule is one-sided. That is a fact about two instruments.
3. **It does not move B15-7.** §2.3 registered the derived ask as a property of
   the instrument before any reading, and §7.2 registered that `a(t) > 0` does
   not establish that the official window fails to clear. Both stand. What this
   adds is a provenance for the asymmetry, one step above where §2.3 found it.

**One further recital, which is a scope note.** The ministry dates the parallel
rate itself:

> `esta baja disponibilidad de RIN líquidas y disponibles desde inicios de 2023`
> `determinó la aparición de un tipo de cambio paralelo, caracterizado por ser`
> `variable y superior al tipo de cambio oficial del BCB.`

**The registered window opens 2024-07-21**, which is S3's first observation, so
the parallel leg was already running for about eighteen months when the window
opens. §8 already records that the pre-event span carries one regime on the
**official** leg. This says the parallel leg has no comparable quiet period
inside the window, and the state says so itself.

---

## 1. The endpoints, one request each

```
RUN:    2026-08-19T22:14:04Z .. 22:14:21Z
DESIGN: §3.1, §10
```

**Four sources, four requests, nothing written.** This is the step that stops a
documented rate limit being believed, and on this carrier it also settles what
`xls.php` serves, which no summary could.

| source | HTTP | content-type | bytes | sniffed | `Content-Length` |
|---|---|---|---|---|---|
| S1 `xls.php?anio=2026` | 200 | `application/vnd.ms-excel` | 29,184 | **`ole2`** | absent, chunked |
| S1 `ods.php?anio=2026` | 200 | `application/vnd.oasis.opendocument.spreadsheet` | 14,470 | `zip` | absent, chunked |
| S3 `all.csv` | 200 | `text/csv; charset=utf-8` | 3,156,156 | `csv` | **present** |
| S3 `oficial.csv` | 200 | `text/csv; charset=utf-8` | 6,774 | `csv` | **present** |

### 1.1 `xls.php` serves a real workbook, so the ODS is load-bearing

**It is an OLE2 compound file, `cotizacion.xls`, and the standard library does
not read BIFF.** This project's dependencies are `numpy` and `matplotlib`.

The §10 decision to fetch `ods.php` beside `xls.php` was recorded as retrieval
machinery that would earn its three requests either way. **It is now the only
parse path for the formal leg**, and `xls.php` remains the source of record and
the thing `guard_truncation` checks by sector alignment. 29,184 is 57 × 512, so
that check has something to bite on despite the chunked transfer.

### 1.2 The 1,162-line read was a truncation, and the size is now measured

`bolivia_availability.md` §6 recorded that the first read of `all.csv` returned
1,162 lines ending in the middle of a number on 2024-08-01 and called it a
truncation rather than the end of the file. **`Content-Length` is 3,156,156.**

The header is the registered five. **The file uses CRLF**, which is recorded
because it broke this stage's own probe print: the escape covered `\n` and not
`\r`, so the terminal's cursor returned and the header was overwritten by the
row after it. `guard_truncation`'s CSV branch reads through `splitlines` and is
unaffected. The print is fixed.

### 1.3 A press-level number was contradicted by the source, exactly as §6 said

`bolivia_availability.md` §3.2.1 recorded the first row of `all.csv`, from a
fetch summary, as:

```
6.86,6.96,10.17,10.13
```

**The endpoint's own first row reads** `2024-07-21 19:14:15,6.86,6.96,10.17,`
**`10.14`**.

**The summary's last digit was wrong.** §3.2.1's observation survives in the
part that matters: the official pair still runs `sell - buy = +0.10` and the
blue pair still runs the other way, at `-0.03` rather than `-0.04`. **B15-3 was
registered to decide the orientation from the full archive and not from that
row**, and `guard_press_free` keeps the row out of every criterion, so nothing
rests on either digit.

**This is the second discarded summary number on this carrier**, after the BCB
annual table reported as carrying a value for 2026-08-31. It is the argument for
§6 stated as a measurement.

#### Voided 2026-08-19T23:40:00Z. §1.3 above is wrong and the register was right

**The file's first row is `2024-07-21 17:36:42,6.86,6.96,10.17,10.13`.**
`bolivia_availability.md` §3.2.1 recorded `10.13` from a summary and `10.13` is
what the endpoint serves. **Nothing was wrong with the register.**

The `10.14` compared against it above is the **eighth** row of the file, not the
first. The probe printed the first 400 bytes with `\n` escaped and `\r` left
raw; the file is CRLF, so each row's carriage return returned the cursor and the
next row overwrote it, and what survived on the terminal was the last complete
record in the window plus the tail of the header behind it.

**A display bug manufactured a disagreement, and §1.3 then used it to overwrite
something the register already had correct.** That is `b8_pitfalls.md` entry 52
with the roles reversed: not a primary source's silence overwriting a correct
record, but a corrupted rendering of a primary source doing it. The entry's
treatment holds either way and was not applied here: **diff a fresh read against
what the register already claims and treat a disagreement as a question.** One
`head -c 400 | cat -A` would have closed it before a word was written.

**What survives from §1.3**: the sign of the blue pair's ordering, which is what
§3.2.1 was actually recording and what B15-3 was registered to decide from the
full archive. **What is withdrawn**: the claim that a summary digit was wrong,
and with it the sentence above calling this the second discarded summary number.
**There is one, not two.**

### 1.4 `oficial.csv` exists, so `guard_kind_column` is exercisable

The URL was a guess written into `bolivia.py` and marked as one. **It answers**,
as `dolar-oficial-gobierno-bolivia-historico.csv`, 6,774 bytes, with `kind` as
its last column and a row reading:

```
2025-12-15,8.87,8.77,referencial
```

**Two things follow and neither is a criterion.**

**§2.4's warning is confirmed before the pull.** 2025-12-15 sits inside the peg
era, when the official pair was 6.86 and 6.96. A `referencial` row at 8.87 and
8.77 on that date is **a different series from the TCO**, so this file carries at
least two meanings under one filename and `guard_kind_column` has something to
do. "A series whose meaning changes at the event is not a series" was registered
against a file nobody had seen; the file exists and it does.

**And the column order of this file is a B15-3-shaped question on a second
file.** The first numeric field is larger than the second. If the columns run
compra then venta, that is a crossed official book, which Art. 6 forbids after
the event and which did not exist before it. **It is recorded and not resolved**;
`guard_no_alignment_shopping` covers arm III and the same reasoning applies here.

### 1.5 There is no rate-limit header anywhere, and that is a weaker position

**None of the four responses carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset` or `Retry-After`.** The BCB is behind CloudFront, the
publisher behind Cloudflare, and neither exposes a quota.

The elTOQUE lesson was that **a documented limit is a claim and the measured one
is the fact**. Here there is nothing to measure, so the registered floors are all
there is: five seconds for the BCB and sixty for the publisher's own stated
request. That is a weaker footing than B6-B ended on and is stated as one rather
than reported as an absence of problems.

### 1.6 The open question the probe raised, and the one request that settles it

`all.csv` came back with **`last-modified` equal to `Date` to the second**, so
the origin builds the file when it is asked. And the archive's first row reads
`2024-07-21 19:14:15`, whose second-of-minute equals the request's.

**Either the 15-minute grid is anchored to the clock or it is anchored to the
moment of generation**, and those are different instruments:

- **clock-anchored**: a row is addressable by its timestamp, `digest_prefix` is
  an equality test across fetches, and B15-2 works on this source as designed;
- **generation-anchored**: the grid is re-derived per request, a row is not
  addressable, and **B15-2 needs a different key on S3.**

**One extra request separates them and nothing else does.**
`fetch_bolivia.py --replay` fetches to a second file, compares the timestamps of
the closed past first and the values second, and reports the two failures apart,
because they mean different things. It writes a new file, overwrites nothing and
deletes nothing.

**This is registered here before it runs.** A grid that moves is a property of
the instrument and would be reported as one; it is not a reason to reach for
another publisher, and S4 and S5 remain what §2.2 and §6.3 say they are.

**Answered 2026-08-19T23:05:00Z: the grid is clock-anchored.** `--replay`
reproduced the closed past exactly, timestamps first and values second, so a row
is addressable by its timestamp and `digest_prefix` is a valid equality test on
this source. `last-modified` equalling `Date` describes the response being
rebuilt per request and says nothing about the rows. **B15-2 works on S3 as
designed.** §2.2 below.

---

## 2. Arm I and arm II

```
RUN:    2026-08-19T23:20:00Z
DESIGN: §5 B15-1, B15-2, B15-3, B15-4; §6.2, §6.3
SCRIPT: experiments/b15_typing.py -> results/b15_typing.json
```

**Two bugs in this stage's own retrieval layer were found and fixed before any
of this ran**, and both are recorded because each is a shape that will recur.

**`guard_truncation` asserted a schema and called it a wholeness check.** It
required every field after the first to be a number, which is true of `all.csv`
and false of `oficial.csv`, whose last column is `kind` and whose last record
ends in the entirely complete word `unificado`. It fired on a file that gates
nothing and **took the run's manifest with it**, so seven correctly retrieved
payloads lost their provenance record to a failure in the eighth. Column types
are now read from the data: a column is checked as numeric only where the
preceding records are numeric, and a categorical column is checked against its
own observed vocabulary, which is a **stronger** test than the one it replaced
(`unif` is not in `{referencial, unificado}`). And **the manifest is now written
on every path**, because downloaded data is irreproducible and a later error
must not be able to discard the account of an earlier success.

**`parse_ods` stripped trailing empty cells and destroyed column identity.** The
BCB's annual table is a matrix, 25 columns wide, days down and month blocks of
`VENTA`/`COMPRA` across, so a cell's meaning **is** its column index. Popping
empty cells off the end shortened every row that ran out of data early, and a
caller indexing by column then read a different month depending on how late in
the year the row stopped. `covered-table-cell` was also skipped, which moved
every merged month header. **Every count on the sheet stayed correct and every
identity moved**, which is the twelfth entry of this project's range-error
family arriving in a parser.

### 2.1 B15-1, retrieval integrity: `pending`, then PASS

**760 days in the window, 760 dates served, zero absent, zero fills.** The
substance is clean. The criterion was marked `pending` rather than FAIL on the
first pass because the manifest did not exist, and it did not exist because of
the bug above. **A defect in this stage's instrument is not a reading about
Bolivia**, and the registered treatment is the one for a load-bearing self-check
that has not been run yet: mark it `pending`, and flip the mark when it runs. Rerunning the fetcher flips it.

### 2.2 B15-2, the known-answer arm: PASS

| | recorded | on disk |
|---|---|---|
| S3 records before 2026-06-29 | 69,657 | 69,657 |
| S3 prefix digest | `39dd158ef40bb8ed…` | `39dd158ef40bb8ed…` |
| S3 first record | `2024-07-21 17:36:42` | `2024-07-21 17:36:42` |

**And the anchor that does not come from a rate publisher.** The Aduana
comunicado on disk states `6,96 Bs/USD vigente al 26/06/2026`. Day 26 of the
`JUNIO` block of the 2026 sheet reads `venta 6.96, compra 6.86`. **Reproduced.**

The live `--replay` run had already established the other half: a second fetch
of `all.csv` reproduced the closed past exactly, timestamps first and values
second. **So §1.6's open question is closed: the 15-minute grid is anchored to
the clock and not to the moment of generation**, a row is addressable by its
timestamp, and `digest_prefix` is a valid equality test on this source.

### 2.3 B15-3, the side convention: VOID

**The official pair is a check and it passes.** Excluding rows where the two
sides are equal, `official_sell - official_buy` is **exactly 0.10 on 100.000%**
of 69,467 observations. Art. 6's ten centavos is not merely the post-reform
rule; it was the peg's spread too, which is what §5 B15-5 anticipated when it
said Art. 6 may be codifying what was already practice.

The 5,156 rows where the two sides are equal are all post-event and are recorded
as **fills** and never as zero spreads, per `guard_kind_column`.

**The informal pair does not resolve.**

| orientation | uncrossed |
|---|---|
| A, as published: `blue_sell` is the ask | **15.05%** |
| B, swapped: `blue_buy` is the ask | **85.17%** |

Registered: one must clear 99% and the other fall under 50%. **Neither clears
99%. VOID.**

**And the object under the verdict says why.**

```
pre-event    n = 69,657     A uncrossed  9.001%     B uncrossed 91.236%
post-event   n =  4,966     A uncrossed 99.960%     B uncrossed  0.060%
```

**The orientation flips at the event.** Each side is nearly clean and they run
opposite ways. §2.4 registered this possibility in general terms before any
data: *the instrument set moves, and a series whose meaning changes at the event
is not a series.* It moved.

**The size of the crossings settles what kind of failure this is.** The typical
`|blue_sell - blue_buy|` is 0.02 to 0.09 Bs on a rate of 10 to 12, which is an
ordinary bid-ask spread and not a quantisation tick. So the minority readings
are not rounding noise; on the majority convention they are moments when a P2P
board with no matching engine genuinely crossed, which is a thing that board can
do because its two sides are different advertisements. **9% genuine crossing on
an unmatched board is a fact about the venue, and 99% is a bar written for an
instrument with a matching engine.**

**Split at the registered break, the pre-event side still does not clear 99%**
(91.24%), so the void does not turn on the whole-window pooling either.

### 2.4 B15-4, the date column: live, `vigencia date`
**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** This section's verdict is live again, on a different instrument. §9's account of why the step-hour instrument fails stands; its suspension does not.
**VOIDED 2026-08-21T09:35:00Z, see §9.** B15-4 is VOID. The clock this section reads the step times on was set by a two-hour line fed from another run's manifest; measured, the column is `America/La_Paz` and the steps land at 04:00 to 05:00.


**36 steps of `official_sell`. Under `America/La_Paz` they fall in two bands and
both bands are named in Art. 5.III.**

```
20:00-23:59, publication      5/36 = 13.89%
00:00-02:59, vigencia        31/36 = 86.11%
together                     36/36 = 100.00%
```

**The external anchor decides, and it decides without the histogram.** The first
step is 2026-06-26 20:35:56 local, `6.96 -> 9.73`. Under the publication
reading, 6.96 stops being the rate at 20:35 that Friday, which contradicts a
Bolivian state body's own written statement that 6,96 was `vigente al
26/06/2026`. Under the vigencia reading, 6.96 governs all of the 26th and 9.73
governs the next business day. **One instrument rules out one reading, and the
histogram then agrees with the survivor.** §3.4 registered exactly this check.

**B15-4 = the column carries the day the rate governs.**

**The two bands are a finding rather than a defect.** The publisher is a scraper:
sometimes it catches the 20:00 publication and more often it catches the value
already in force after midnight. **The 86/14 split is the empirical fingerprint
of the two clocks Art. 5.III writes into one sentence**, and it is visible only
because the statute was read first.

### 2.5 S1's month labels part company with its data, and it is reported open

Cross-identifying four dated values from S3 against the 2026 sheet:

| date | value | cell | the sheet's label there |
|---|---|---|---|
| 2026-06-26 | 6.86 / 6.96 | day 26, col 11 | `JUNIO` |
| 2026-06-29 | 9.73 | day 29, col 13 | **`JULIO`** |
| 2026-07-01 | 9.76 | day 1, col 15 | **`AGOSTO`** |
| 2026-08-19 | 11.52 | day 19, col 17 | **`SEPTIEMBRE`** |

After the reform the sheet carries one value per day with the `COMPRA` half
empty, while the month headers still span two columns, so the post-reform data
sits one month-block to the right of its label. **Every count on the sheet is
right and every identity after June is wrong.**

**Reported and not resolved, and it stayed that way.** The only cell arm I or
arm II needs from S1 is the one `ADUANA_ANCHOR` names, whose month is stated by
a Bolivian state body rather than inferred, and B15-9 later read the eight
weekly cells it needs off the same sheet by the same route. Resolving the labels
themselves would need the anchor plus the statute's own weekend rule, not a look
at the labels, and nothing in the stage came to need it.

**The clause this paragraph carried on 2026-08-20, that arm III is suspended, is
superseded by §13**: arm III runs. The displacement above is unaffected either
way, because no criterion reads S1 by its month label.

### 2.6 The gate
**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** The gate is open. B15-4 resolves and B15-3's gate is asked on the segment arm III uses.
**VOIDED 2026-08-21T09:35:00Z, see §9.** The gate closes. B15-4 is void, so §6.3 suspends arm III.


**B15-3 VOID, B15-4 live.** `guard_typing_first` suspends arm III on either, so
**B15-6, B15-7, B15-8 and B15-9 do not run.**

§7.4 registered this outcome before the data existed: *the stage degrades to
arms I, II and IV, which is a cross-section plus an event study and not the
discriminating case §1 asks for, and it will be reported as degraded rather than
rewritten to fit what it can do.*

**Both voids are properties of one publisher's serialisation and not of the
Bolivian exchange system.** That distinction is what the degraded report has to
carry, because a reader will otherwise take a suspended arm as a statement about
Bolivia.

---

## 3. Arm IV

```
RUN:    2026-08-19T23:50:00Z
DESIGN: §5 B15-10, B15-11, B15-12
SCRIPT: experiments/b15_calibration.py -> results/b15_calibration.json
```

**Arm IV is not gated.** `guard_typing_first` names arm III and nothing else.

**But B15-10's statistic names a side, and B15-3 could not supply one.** Rather
than derive an orientation inside the criterion, which
`guard_no_alignment_shopping` forbids, the statistic is run under **both**
orientations of the parallel pair and **both** readings of the official ask
(the published number as served, and the published number plus Art. 6's ten
centavos, since which of the two the BCB publishes after the reform is not
settled by any source in hand). **Four combinations, all reported, none chosen.**

### 3.1 B15-10, the event: FAIL, and the reason is a finding

All four combinations agree, so the unresolved typing does not touch the
verdict.

| | value |
|---|---|
| observed break statistic at 2026-06-29 | 0.4933 |
| null p99, 999 draws, seed 0 | 0.4949 |
| null draws at or above observed | 16 of 999 |
| distinct null values | **551 of 999, not degenerate** |

**The null is not degenerate**, which is the check B6-14 forced into the
register after its own null returned one value on all 999 draws.

**The dates that match or beat the registered break are the object worth
printing:**

```
2026-06-27, 2026-06-28, 2026-06-29,
2026-07-25, 2026-07-26, 2026-07-27, 2026-07-30,
2026-08-02, 2026-08-04, 2026-08-05, 2026-08-06
```

The first three are the same split under three labels: the 27th and 28th are the
weekend immediately before the event and the series is flat across it. **The
rest are a second cluster five to six weeks later**, and removing the event's own
seven-day neighbourhood does not rescue the criterion: 13 of the remaining 982
draws still match or beat it.

**So the reading is not that the reform did nothing.** It is that **the log gap
does not have a single dated break.** It steps at the reform and then keeps
moving, and a uniform-break-date null on a series with a step plus a continuing
adjustment gives cuts in the middle of that adjustment about as much separating
power as the reform date itself. The level path says the same thing without a
test: 9.73 at the end of June, 12.15 by the end of July, 11.52 on 19 August.

**B15-10 FAIL, and what fails is the claim that 2026-06-29 is the break rather
than a break.** The extended adjustment is the substantive result.

### 3.2 B15-11: pending, S4 and S5 not yet retrieved

The retrieval layer now carries them: S4 is `paralelo.bo/api/v1/historical.csv`,
one file, CC-BY 4.0, cited as `paralelo.bo (https://paralelo.bo)`. S5 is six raw
files from `github.com/mauforonda/dolares`, taken by raw URL rather than by
clone, because a clone would drop a nested `.git` inside `data/raw/` and B15-11
needs the current snapshot; **the 25,627 commits remain the argument for that
source's auditability and are cited rather than downloaded.** The branch is
discovered rather than guessed, because a raw URL on the wrong branch returns a
404 that reads exactly like a deleted file.

**B15-11 is where the question B15-3's void raises actually lives.** §5
registers it as the measurement `cuba_informal.noise_floor` had to infer from a
variance identity because Cuba had one publisher of its informal rate. Here the
dispersion across publishers of one market is counted, and it is also the
natural place to see whether the convention flip at the event is the market or
the publisher.

### 3.3 B15-12: not run
**SUPERSEDED 2026-08-21T12:05:00Z, see §11.** B15-12 ran. The euro is on a per-day BCB quotation table, not on the endpoint §3.3 named, and the criterion returns FAIL with a finding.


The BCB's `Bs / Euro` endpoint has not been probed. `data/fetch_ecb.py` already
carries the ECB side from B6-4.

---


---

## 4. Arm III, on the segment where the typing exists
**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** Arm III runs. This section's readings are verdicts.
**VOIDED 2026-08-21T09:35:00Z, see §9.** Arm III is suspended by B15-4's void. Everything below is a reading and not a verdict, and `results/b15_structure.json` carries `diagnostic_only` again. The numbers themselves are not withdrawn.


```
RUN:    2026-08-20T00:20:00Z
DESIGN: §5 B15-7, B15-8; §3.5, §6.2 guard_break_disclosure; §8
SCRIPT: experiments/b15_structure.py -> results/b15_structure.json
```

**Why it runs.** B15-4 is live. B15-3 is VOID on the registered whole window and
**live on the post-event segment**, where `blue_sell` is the ask on 99.960% of
4,966 observations against 0.060% for the other orientation. That clears
`UNCROSSED_SHARE` and `CROSSED_SHARE_MAX` as registered, **with no threshold
moved**. §3.5 requires a criterion whose window straddles a break to say so;
this window does not straddle 2026-06-29, it begins there. The pre-event segment
is not typed and arm III does not touch it.

**And the reversal is a label, not a market.** `github.com/mauforonda/dolares`
publishes the same board and its `buy` median exceeds its `sell` median on
**100.000% of 693 pre-event days and 100.000% of 52 post-event days**. It does
not reverse. `dolarbluebolivia` does. A market whose bid and ask genuinely
swapped would swap in both. B15-11 established this and arm III inherits it
rather than re-deriving it, which is what `guard_no_alignment_shopping` asks.

### 4.1 B15-7, the posted return leg: FAIL, and it is B6-15's opposite

52 post-event days, thresholds B6-15's and unchanged.

| ceiling reading | `a(t) > 0` | median `a(t)` | critical spread |
|---|---|---|---|
| published number is the `TCO`, ceiling `+0.10` | **40.38%** | −0.0048 | −0.0683 |
| published number is already the venta | **53.85%** | +0.0048 | −0.0599 |

Threshold is 95% and a critical spread above 0.02. **Both readings FAIL and both
agree**, so the one typing this criterion does not have does not touch its
verdict.

**The informal ask sits on the official ceiling, not above it.** B6-15 found the
informal ask above the official ceiling on **207 of 207** Cuban publication days.
Here the median `a(t)` is within half a percent of zero.

**This is what §1 registered the stage to find out.** The framework does not say
the same thing about any controlled economy. `bolivia_availability.md` §4.4 put
both directions on the record as live before a number had been read, and struck
out the first draft's table for pre-committing to a contradiction it had not
measured. **The measured answer is the contradiction, and it was not assumed.**

§7.2 holds in both directions: `a(t) > 0` would establish that the informal ask
is above the legal ceiling on the day and never that the official window fails
to clear, and the sale-side transaction record that would settle it does not
exist.

### 4.2 B15-8, the cycle B6-B could never certify: PASS

| ceiling reading | sign determined | median max-cycle weight | certified positive |
|---|---|---|---|
| `TCO`, ceiling `+0.10` | **100.0000%** | +0.00833 | 42 of 52 |
| already the venta | **100.0000%** | +0.01576 | 50 of 52 |

**Determined on every day, because there is no one-sided bound anywhere.** Both
sides on both legs is the whole difference from B6-B, where elTOQUE's single
median bounds every directed weight from above and B6-12 exists to stop a
positive cycle being claimed.

The binding direction splits about evenly, 25 to 27 days each way, so neither
leg is uniformly the cheap side.

**A2 is named beside the positive cycle and is not tested.** §3.6 and §7.3: a
certified positive cycle is a claim about published quotes and not about
executable prices, and the touch quotes' executability at a size that is not
zero is an assumption.

**A shape error in this stage's own code, recorded because it is the shape
this project's criterion-shape discipline names.** The first version tested
`best != 0.0` for "the sign
is determined", which is a **zero-width strict inequality on a float**. It
counted a weight of exactly zero as undetermined, failed the criterion on two
days, and the failure was about nothing. A weight of zero is **certified
non-positive**, which is a determination; what would be undetermined is a
one-sided bound, and this carrier has none.

### 4.3 The reform ratified a rate the banks had already reached

**Not a criterion.** S5 publishes per-bank daily purchase rates
(`buy_oficial_completo.csv`) and per-bank daily amounts
(`buy_oficial_monto.csv`), so Anexo II's formula can be applied to them
directly:

```
117 overlapping days, 2026-01-05 .. 2026-06-26
109 reproduce the published aggregate to two decimals = 93.16%
|recomputed - published|: median 0.0000, max 0.0100
```

**And the series starts six months before the reform.** While the BCB posted
6.86 / 6.96, the amount-weighted bank purchase rate ran **7.85 on 2025-12-01 to
9.76 on 2026-06-26**, the last day of the peg. The first TCO of the flexible
regime, 2026-06-29, was **9.73**.

**So 2026-06-29 is not the day the rate started moving. It is the day the BCB
began publishing the one the banks had been using.** A step of about 0.3%.

**This is the reading B15-10's FAIL was pointing at.** That criterion measured
the gap against `all.csv`'s official pair, which is the frozen posted quote
before the event, so what it tested was whether the *posted quote* changed on
2026-06-29. It did. The rate did not, and a null drawn uniformly over break
dates cannot tell those two apart on this series.

**One limit, and it is what keeps this from being B15-6.** The `value` column
may be the aggregator's own computation rather than the BCB's published TCO.
What is established is that **given per-bank rates and per-bank amounts, Anexo
II's formula reproduces that column**, and that a bank-transacted rate distinct
from the posted quote existed and was observable six months before the statute
that defines it was written. B15-6 proper needs S2's microdata against the BCB's
own published TCO and has not run.

### 4.4 The pre-event segment, and a claim of mine that is withdrawn

**Withdrawn.** The previous turn's report said that unsuspending the pre-event
segment would give a Cuba-like reading there and "upgrade the finding by an
order of magnitude". **That was over-claimed and the arithmetic is against it.**

`a(t)` on the pre-event span, under two readings of what the official leg is:

| official leg, pre-event | `a(t) > 0` | median | critical spread |
|---|---|---|---|
| the BCB's frozen quote, `6.96 + 0.10` | **100.00%** of 240 days | +0.3177 | +0.2593 |
| the banks' actual venta, S5 `sell_oficial` | **65.38%** of 182 days | +0.0227 | −0.0458 |

**The Cuba-like reading is entirely an artefact of measuring against a quote
nobody transacted at.** Against the price the banks were actually selling at,
the pre-event reading already fails, at 65.4% against a 95% threshold.

**And this project has a name for this shape.** A baseline whose premise I do
not believe is a trial run and not a measurement, and what may be archived from
one is a sentence about the instrument and never a sentence about the world. The sentence here is: **`a(t)` measured
against a frozen quote is a measure of how frozen the quote is, and is by
construction blind to whether the official window clears.**

**What this does to the stage is make it stronger, not weaker.** The
discriminating answer does not depend on which segment is read:

| | Cuba, B6-15 | Bolivia, pre-event | Bolivia, post-event |
|---|---|---|---|
| official leg | Segment III float, live | bank venta, live | `TCO` (+0.10), live |
| informal ask above it | **207 of 207 days** | 65.4% of 182 days | 40.4% to 53.8% of 52 days |

**Once the official leg is a price someone actually transacts at, Bolivia never
looked like Cuba.** The gap was already mostly closed before the reform and the
reform closed the rest. **So the finding does not rest on the segmentation
question at all**, and the case for reopening the pre-event segment is weaker
than the previous turn claimed rather than stronger.

**Recorded as a diagnostic and not as B15-7.** Substituting S5's bank series for
the official leg is a construction the register does not contain, because the
register did not know the banks were transacting away from the peg. §3.1 assigns
S5 to audit and reconstruction and the substitution is named here rather than
folded into a criterion.

---

## 5. B15-6, and an endpoint that answers a question it was not asked
**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** Arm III runs. B15-6 is a verdict.
**VOIDED 2026-08-21T09:35:00Z, see §9.** Arm III is suspended by B15-4's void. B15-6's reading stands as a reading; `results/b15_zero.json` carries `diagnostic_only` again.


```
RUN:    2026-08-20T01:10:00Z
DESIGN: §5 B15-6, §7.1; §2.3, §3.4
SCRIPT: experiments/b15_zero.py -> results/b15_zero.json
```

### 5.1 The result

**35 cutoff dates, 2026-06-26 to 2026-08-18. The recomputation matches the
published value at two decimals on 35 of 35, and on 484 of 484 bank-days.**

```
TCO_t = sum(TC_it x M_it) / sum(M_it)     RD 88/2026 Anexo II section 2
aggregate   35 / 35   = 100.0000%      threshold 99%
per bank   484 / 484  = 100.0000%
worst |recomputed - published| = 0.0049 Bs, under the half-centavo that
Anexo II section 4's two-decimal rounding accounts for
```

**The published TCO is the statute's own formula applied to the statute's own
microdata.** This is the formal leg's zero calibration and the counterpart of
B6-18, which found 909 of 1,321 days exactly equal on Cuba's informal leg. A
stage that only reports differences cannot show that it would report zero when
zero is the truth; this one now can, on the leg where it matters most.

**Fifteen comparisons a day rather than one.** The BCB prints each bank's own
weighted average beside the aggregate, so a uniform mismatch and a single bank's
mismatch would be different failures. Neither occurred.

### 5.2 What this settles that arm III had to carry twice

**The BCB's single published number after the reform is the `TCO`.** The page
and the CSV both label the aggregate column `TCO`, and that number is what the
aggregators serve. So B15-7's ceiling is the published number **plus** Art. 6's
ten centavos, and the second reading both B15-7 and B15-8 were run under is
retired. **The surviving readings are the tighter ones:**

| | reading now settled | the retired reading |
|---|---|---|
| B15-7 `a(t) > 0` | **40.38%** of 52 days | 53.85% |
| B15-8 median max-cycle weight | **+0.00833** | +0.01576 |

B15-7's FAIL against its 95% threshold is therefore **further** from passing
than the two-reading report showed, and B6-15's opposite is sharper.

### 5.3 B15-4 confirmed a third time, from a column header
**THE VOID ON THIS SECTION WAS AN ERROR, corrected 2026-08-21T13:10:00Z.** This section's argument reads the BCB's own two date columns and never touches the clock that §9 corrected, so voiding it along with everything the clock touched was over-broad. **It is the instrument B15-4 is now decided on**, see §13.1.


The CSV's own header block reads:

```
"Rango de fecha de corte";2026-06-26;2026-08-18
"Rango de vigencia";2026-06-29;2026-08-19
```

and every data row carries both: `Fecha de corte` is the day the operations
happened, `Vigencia` is the day the resulting TCO governs. **Operations of
Friday 2026-06-26 are `vigente` on Monday 2026-06-29**, which is Art. 5.III and
Anexo II section 4's weekend rule in a single row.

**This is the third independent confirmation of B15-4's `vigencia date` verdict
and the only one that comes from a column header rather than from an
inference.** The first was the step-time histogram, the second was the Aduana
anchor, and this is the BCB stating the mapping itself.

**And it dates the first flexible TCO to the last day of the peg.** 9.73,
`vigente` 2026-06-29, was computed from bank operations on 2026-06-26, the day
`RD 88/2026` was signed and the day the Aduana comunicado says 6,96 was still
`vigente`. §4.3's reading is the same fact from the other side: the reform
ratified a rate the banks had already reached.

### 5.4 Voided: the first B15-6 run, which read 55 days and had 35

**Withdrawn 2026-08-20T01:10:00Z.** The first run reported **55 of 55 days and
764 of 764 bank-days at 100%**. That number counted one page twenty times.

`tco_reporte_detalle_historico.php?fecha=` on a day with no operations returns
**HTTP 200 and a complete, well-formed grid, and the grid is another day's**.
Twenty of the fifty-five requested days came back byte-identical to the
endpoint's default. The retrieval layer's check was `has_grid`, it saw a grid on
every one of them, and it passed them all.

**The page does say which day it is showing.** Its date input carries
`value="YYYY-MM-DD"`, and asking for 2026-06-27 returns a page whose input reads
`value="2026-08-18"`. `guard_echoed_date` reads it. **The body carried the
answer and it was not read**, which is B6-9's replay problem inverted: there the
response carried no date and a probe record had to be kept against an
off-by-one; here the response carried the date all along.

**Three things this cost and one it did not.** It cost a wrong 55, a wrong 764,
and a paragraph of celebration. It did not cost the verdict: the corrected run
is 35 of 35 and 484 of 484, still 100%, still PASS. **The number was wrong and
the finding was not**, which is the good case and is recorded because the
mechanism will recur on any endpoint with a default.

**And the fallback list is itself a reading.** Twenty of the fifty-five
requested days fall back, and they split three ways.

| | days | what the absence is |
|---|---|---|
| weekends | 16 | Anexo II §4: Saturdays, Sundays and holidays carry the previous business day's TCO |
| weekdays inside the source's range | **3**: 2026-07-16, 2026-08-06, 2026-08-07 | the BCB computed no TCO. **Holidays, read out of the endpoint** |
| weekdays past the source's last cutoff | **1**: 2026-08-19 | not a holiday at all |

**The third row is a distinction the first version of this reading missed.** It
called all four weekdays holidays. The CSV's own header states its range,
`Rango de fecha de corte;2026-06-26;2026-08-18`, and the detail page's date
input carries `max="2026-08-18"`. **2026-08-19 is past that, so its absence is
Art. 5.III's twenty-hundred publication not having happened yet when the fetch
ran, not a day the BCB took off.** Absence there is the clock and the other
three are the calendar, and counting them together would have invented a
holiday.

**So the holiday calendar is read out of the endpoint rather than invented**,
which is what the retrieval layer claimed to be doing and now actually does, and
the source's own stated range is what keeps that reading from over-reaching.

### 5.5 A retrieval note

**The 55 daily HTML requests were not necessary.** `tco_tcreferencial_descargar_csv.php?desde=&hasta=`
returns the entire range in one request, 1,504 rows, with both date columns and
the same per-bank grid. B15-6 now reads that file. **The 55 pages stay on disk**
because nothing here is deleted, and they are what established §5.4's finding, so they
earned their five minutes.

---

## 6. B15-9, the customs edge
**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** Arm III runs. B15-9 is a verdict.
**VOIDED 2026-08-21T09:35:00Z, see §9.** Arm III is suspended by B15-4's void. `results/b15_customs.json` carries `diagnostic_only` again.


```
RUN:    2026-08-20T02:00:00Z
DESIGN: §5 B15-9; bolivia_availability.md §4.6
SCRIPT: experiments/b15_customs.py -> results/b15_customs.json
```

### 6.1 S1's alignment, settled

**Settled against S2's dated values rather than against the sheet's labels**,
which §2.5 left open. Each dated TCO is looked up at its own day-of-month across
every column, and a month is settled only when one column carries strictly more
of its values than any other.

| month | column that holds it | the sheet's label on that column |
|---|---|---|
| June, post-reform | 13 | `JULIO` |
| July | 15 | `AGOSTO` |
| August | 17 | `SEPTIEMBRE` |

**A uniform displacement of one block, beginning at the reform.** The sheet
opened a fresh two-column block for post-reform June and the twelve month
headers never moved.

**And June is split across two blocks**, days 1 to 26 in the pegged `JUNIO`
block carrying a `VENTA`/`COMPRA` pair and days 27 to 30 in the next block
carrying a single value, because the reform fell on the 26th. The first version
of the resolver gave each month one column, **lost 2026-06-26, and therefore
lost the Aduana anchor**, which is the one dated observation §5 registers for
this criterion. A month now reads from its settled column and from its label's
column, and takes a value only where the sheet has one.

**S1 and S2 then agree on all 39 days they share, with zero disagreements.**
Two BCB products, a spreadsheet grid with mislabelled columns and a CSV with
explicit dates, parsed by different code paths, reconciling exactly. **And S1
files by vigencia**, which is B15-4's verdict arriving from a fourth source.

### 6.2 The check that is not a choice

The comunicado on disk fixes `6,96 Bs/USD vigente al 26/06/2026` for
declarations accepted 2026-06-29 to 2026-07-05. Under Art. 20 that week's rate
is the official venta in force on the last business day of the preceding week.

```
Art. 20 points at         2026-06-26, the Friday
S1's venta on that day    6.96
the comunicado states     6.96          reproduced
```

**The implementation reproduces the Aduana's own number before it is applied to
any week the Aduana did not state.** The business-day calendar it uses to find
that Friday is read out of S2's `Fecha de corte` values, not out of a holiday
calendar this project would have had to invent.

### 6.3 The weekly edge, 8 of 8 weeks from S1

| week | `TC_aduana` | from |
|---|---|---|
| 2026-06-29 to 07-05 | **6.96** | the comunicado, the frozen peg |
| 07-06 to 07-12 | 9.90 | venta vigente 2026-07-03 |
| 07-13 to 07-19 | 10.34 | venta vigente 2026-07-10 |
| 07-20 to 07-26 | 10.85 | venta vigente 2026-07-17 |
| 07-27 to 08-02 | 11.31 | venta vigente 2026-07-24 |
| 08-03 to 08-09 | 12.25 | venta vigente 2026-07-31 |
| 08-10 to 08-16 | 12.12 | venta vigente 2026-08-05 |
| 08-17 to 08-23 | 11.72 | venta vigente 2026-08-14 |

**100% of weeks reproduced from S1**, which is the threshold §5 set.

### 6.4 The holonomy, with its sign and its maximum

`h(t) = log TC_aduana(t) - log p_ask_parallel(t)`, over 52 post-event days.

```
negative on 35 of 52 days = 67.31%
min -0.3644   median -0.0365   max +0.0977
widest -0.3644 on 2026-07-01, which is 43.97% below the market rate
against the same-day official venta: min -0.3554, median -0.0248, max +0.0370
```

**The widest reading is the transition week and §5 registered it as this edge's
single dated observation before any number was read.** Customs valued imports at
6.96 while the market asked about 10.9, so the tax base was struck **44% below**
what the importer paid for the dollars. That is the edge at its widest and its
width is now a number.

**A correction to `bolivia_availability.md` §4.6.** That section says the edge is
"during a rising regime strictly favourable to that class". **It is favourable
while the rate rises and adverse while it falls, and Bolivia had both inside
eight weeks**: the customs rate peaked at 12.25 for the week of 08-03 and fell
to 11.72 by 08-17, and on 17 of 52 days the stale rate sat *above* the market,
which runs the edge against the importer. **The edge is a one-week lag, and a
lag is favourable in one direction and adverse in the other.** The registered
claim that it is deterministic, dated, and granted to one agent class alone is
untouched.

### 6.5 What it is

**The cleanest priced edge this project has found.** Deterministic given two
published series, dated, granted by statute to `Operadores de Comercio Exterior`
and to no other agent class, and unlike Cuba's Reglamento Art. 10.1 forward-fill
**it is not a price anybody can trade at**. It is a position occupied by exactly
one class of agent at a number no other agent gets, which is what makes its
holonomy a statement about the graph rather than about a market.

---

## 7. B15-12, and a source the register placed where it is not
**SUPERSEDED 2026-08-21T12:05:00Z, see §11.** The source was located and B15-12 has since run. This section's reading of the endpoint it probed is unchanged and correct; what it concluded about the criterion's status is superseded by §10.1 and §11.


```
RUN:    2026-08-20T02:40:00Z
DESIGN: §5 B15-12, §3.1 S6; bolivia_availability.md §3.3, §6
SCRIPT: data/fetch_bolivia.py --probe-euro
```

**The BCB's rate index is the dollar and only the dollar, and it says so in its
own heading.** One request, page stored, and the page carries:

```
COTIZACIONES OFICIALES DEL BOLIVIANO CON RELACION AL DOLAR ESTADOUNIDENSE
3 links: pdf.php?anio=  xls.php?anio=  ods.php?anio=
1 select: menu1, 87 options, every one of them a year
0 links matching euro, deg, moneda, divisa or cotizacion
0 mentions of EURO, DEG, Derechos Especiales, UFV, Yen or Libra
```

**There is no currency parameter.** `?anio=` selects a year and nothing selects
an instrument.

### 7.1 What that does to the register

`bolivia_availability.md` §3.3 records that "the BCB publishes `Bs / Euro` and
`DEG`", and §5 B15-12 is built on it. **§3.3 came through a fetch summary**, and
§6 says exactly what that is worth: sound evidence that a source exists, not
evidence of what it contains.

**`b8_pitfalls.md` entry 52 bounds the finding.** What is established is that
**this endpoint carries the dollar alone**. It is not established that the BCB
publishes no euro series anywhere, and the silence of one page is not a
refutation of the institution.

**So this is the second discarded summary claim on this carrier**, after the
2026 annual table reported as carrying a value for a date that had not happened.
The first §1.3 candidate was withdrawn in §1's own Voided block because the
register had been right and a display bug had manufactured the disagreement.

### 7.2 B15-12 is `pending on retrieval`, not FAIL
**SUPERSEDED 2026-08-21T12:05:00Z, see §11.** No longer pending. The endpoint was found and verified, §10.1, and the criterion ran, §11.


The criterion cannot run until the euro series is located, and **the source
being absent from the endpoint the register named is not a reading about
Bolivia.** The treatment is the one for a load-bearing self-check that has not
been run yet: mark it `pending`, and flip the mark when it runs.

**And the criterion's registered value was modest before any of this.** §5 B15-12
states its own expectation: B6-5 found the BCC's euro to be the dollar times a
world cross, which is what made B6-4 a test of the pass-through rather than of
the rate, and **if Bolivia's is the same, B15-12 measures the pass-through and
says so.** It is arm IV, it gates nothing, and §1's question does not touch it.

**So the next move is not more probing.** A human finds a page on a government
site in seconds and an agent guessing URLs spends requests to learn that a guess
was a guess, which is the shape `--probe-s2` and `--probe-euro` were written to
avoid rather than to industrialise. **The euro page goes on the get-list beside
the superseded Aduana comunicado and `D.S. 25870` itself.**

### 7.3 A defect in the probe, fixed

`describe_form` had a flat output cap and the year selector's **87 options** ate
it, truncating everything after the select. The first run of `--probe-euro`
printed seventy-odd year options and stopped.

**A probe whose job is to show what a page offers must not be silenceable by the
longest thing on the page.** Options are now capped per select, the cap says how
many it hid, and an overall truncation announces itself. The finding above
survived only because the three export links happened to be emitted before the
select.

---

## 8. Where the stage stands
**SUPERSEDED, and twice. See §13.4 for the current table.** This section's table was the state when eleven criteria had run; §9.5 replaced it when the clock was corrected and B15-4 went void, and §13.4 replaced that when B15-4 was re-decided on the publisher's own columns and arm III ran. **Twelve criteria, twelve verdicts.** The numbers in this section are not withdrawn and it is not rewritten.


**Eleven of twelve criteria have run.** The twelfth is `pending on retrieval`
and gates nothing.

| | verdict |
|---|---|
| B15-1 retrieval integrity | PASS |
| B15-2 known-answer arm | PASS |
| B15-3 side convention | **VOID** on the registered whole window, live on the post-event segment |
| B15-4 date column | **live: `vigencia date`**, confirmed from four sources |
| B15-5 statutory spread | PASS, 0.10 exactly on 100.000% of non-degenerate rows |
| B15-6 TCO recomputation | PASS, 35/35 days and 484/484 bank-days |
| B15-7 posted return leg | **FAIL**, `a(t) > 0` on 40.38%, and that is the stage's answer |
| B15-8 the cycle | PASS, sign determined 52/52, positive cycle certified |
| B15-9 customs edge | PASS, 8/8 weeks, widest holonomy 44% below market |
| B15-10 the event | FAIL, and the reading is that there is no single break date |
| B15-11 publisher calibration | FAIL, 18.26% against 50%, noise floor measured at 0.165 Bs |
| B15-12 referee | superseded, see §11: **FAIL** |

### What §1 asked, and the answer

B6 found the same thing at every criterion in Cuba: an edge the law grants, that
is posted, and that nobody walks. §1 registered the stage to find out **whether
the framework would say that of any controlled economy.**

**It would not.**

| | Cuba, B6-15 | Bolivia, B15-7 |
|---|---|---|
| official leg | Segment III float, live | `TCO` + Art. 6's ten centavos, live |
| informal ask above the official ceiling | **207 of 207 days** | **21 of 52 days, 40.38%** |
| median `a(t)` | above the ceiling throughout | **−0.0048**, within half a percent of zero |

**And the answer does not depend on the segment.** Read before the reform
against the price the banks were actually selling at, Bolivia gives 65.4%, not
Cuba's 100% (§4.4). **Once the official leg is a price someone actually
transacts at, Bolivia never looked like Cuba.**

### What the second carrier bought that the first could not

- **A certified positive cycle.** B15-8 determines the sign on 52 of 52 days
  because both sides exist on both legs. B6-B has a one-sided bound on every
  directed weight and B6-12 exists to stop it claiming one.
- **A zero calibration on the formal leg.** B15-6 recomputes the published TCO
  from the statute's own microdata and matches on 35 of 35 days.
- **An observed publication noise floor**, 0.165 Bs median across three
  publishers, where `cuba_informal.noise_floor` had to infer it from a variance
  identity because Cuba has one publisher.
- **A priced edge granted to one agent class by statute**, deterministic, dated,
  and measured at its widest: 44% below the market rate in the transition week.

### Still open

| | what it needs |
|---|---|
| **B15-12** | the BCB's euro series, which is not at the endpoint §3.3 named. §7 |
| the superseded Aduana comunicado of 2026-06-27 | B15-9's counterfactual, unseen |
| `D.S. 25870` Art. 20 itself | quoted at second hand by the Aduana in a document on disk |
| S3's pre-event typing | B15-3 is VOID there and §4.4 shows the stage does not need it |

**The stage is not degraded in the sense §7.4 feared.** That section registered
"degraded" as the outcome if arm III could not run at B6's thresholds. **Arm III
ran at B6's thresholds, unchanged, on the segment its criteria are about**, and
what is missing is one referee whose own registered expectation was that it would
measure a pass-through rather than a rate.

---

## 9. Voided: the column's clock, and everything downstream of it

```
RUN:    2026-08-21T09:35:00Z
DESIGN: §5 B15-4, §3.4; §6.3 guard_typing_first
SCRIPT: experiments/b15_typing.py -> results/b15_typing.json
```

**SUPERSEDED 2026-08-21T13:10:00Z, see §13.** B15-4 is re-decided on the publisher's own two date columns and arm III runs. **What this section establishes about the registered instrument stands and is the reason for that re-decision.**

**B15-4 is VOID, and §6.3's gate suspends arm III.** §4, §5 and §6 above are
readings and not verdicts, their records carry `diagnostic_only` again, and the
comparison §1 registered the stage to make **was not made**. §8's summary table
and its headline are void with it.

### 9.1 The defect

S3's `datetime` column carries no offset and the publisher's page did not state
one, so the first implementation measured it: compare the last row to the
moment the file was fetched, and call the column UTC if the two are within two
hours.

**Two things were wrong with that and only one of them was the two-hour line.**

The fetch time it read was `generated_utc` out of `data/raw/bolivia_manifest.json`,
and that file holds one run at a time. The copy on disk carries **56 responses,
every one of them S2**, and was written by the S2 pass at `2026-08-20 00:12:22`
UTC. `dolarblue_all.csv` landed at `2026-08-19 22:38:43` UTC, an hour and a half
earlier, in a different run whose manifest that one replaced. **The comparison
put a stamp from one run against a file from another**, and the 2.04 hours it
produced is not a lag between anything.

And the quantity cannot answer the question even when it is computed correctly.
This endpoint re-derives its grid per request: the same URL returned a first row
of `17:36:42` on one fetch and `19:14:15` on another, the 15-minute phase drifts
across the file (14.25 minutes in the first two thousand rows, 8.10 in the last
two thousand), and the last fifteen rows of the saved copy carry labels ahead of
the moment that copy was written, with real variation in them rather than a
carried-forward value. **A lag against a file's own write time is not a clock on
this carrier.**

### 9.2 What settled it

Two instruments, neither of them a threshold.

**The publisher states its own clock.** `dolarbluebolivia.click` reads
`Lectura verificada: 21-ago, 05:23 a. m.` at a moment when Bolivia was at 05:24
and UTC at 09:24. The site publishes in Bolivian local time.

**A second publisher of the same book states its offset in every stamp.**
`mauforonda/dolares` writes `2024-08-05T20:41-04:00`. Correlating hourly first
differences of the two series and scanning the shift puts **one peak at zero,
`r = +0.4250`, with every other shift in `[-6, +6]` inside `|r| < 0.09`**. The
peak survives removing each hour's own mean, so it is event alignment and not
two publishers sharing a working day. It reproduces on the sell leg.

**So the column is already `America/La_Paz` and the offset applied to it is
zero.** The scan now runs on every execution rather than living in a comment,
and its whole profile is printed and stored, because a scan that reports only
its argmax cannot say "no peak".

### 9.3 What that does to B15-4

With the clock measured, `official_sell` steps at **04:00 to 05:00 local on 31
of its 36 steps**. The register admits 20:00, the publication hour of Art. 5.III,
and 00:00, the vigencia flip. **The two bands together cover 13.89%.**

§3.4's third branch is written for exactly this: *steps at neither, or at no
consistent time: B15-4 is void and every arm that needs a dated official value
is suspended rather than aligned by guess.* **The branch fired as written.**

**04:00 to 05:00 is not one of the statute's hours and is not claimed to be
anything.** What can be said is that it is not 20:00 and not 00:00. Whether it
is the aggregator's own refresh is a further question this stage does not
answer, and three of the 36 steps are a same-day flip and revert
(`2026-07-09`, 9.96 to 10.1 to 9.96 to 10.1), so the step count is not a count
of rate changes either.

### 9.4 The anchor reproduces, and its old test did not ask that

§2.4 and §5.3 recorded the customs comunicado as confirming `vigencia date`.
**The comunicado does reproduce**, and more cleanly than before: every one of
the **96 rows the column dates to 2026-06-26 reads `6.96`**, and the first step
away from it is `2026-06-27 00:35:56`. `6,96 Bs/USD vigente al 26/06/2026`
holds on this column with no exceptions.

**The implementation was asking a different question.** It tested whether the
first step *landed on* 26/06, which is the shape the comunicado takes only under
a clock this column is not on, and it therefore reported `NOT CONFIRMED` for a
statement the data satisfies exactly. It now reads the register's own sentence
off the rows. **This is a code fix and both readings are on the record.**

It does not rescue the criterion. §5 B15-4 is a conjunction and the step-hour
conjunct fails.

### 9.5 What stands and what falls

| | before | now |
|---|---|---|
| B15-1 retrieval integrity | PASS | PASS |
| B15-2 known-answer arm | PASS | PASS |
| B15-3 side convention | VOID on the whole window | VOID, unchanged |
| B15-4 date column | live, `vigencia date` | **VOID** |
| B15-5 statutory spread | PASS | PASS |
| B15-6 TCO recomputation | PASS | reading only, arm III suspended |
| B15-7 posted return leg | FAIL, the stage's answer | reading only, arm III suspended |
| B15-8 the cycle | PASS | reading only, arm III suspended |
| B15-9 customs edge | PASS | reading only, arm III suspended |
| B15-10 the event | FAIL | FAIL |
| B15-11 publisher calibration | FAIL | FAIL |
| B15-12 euro leg | pending on retrieval | **FAIL**, and the registered expectation is falsified. §11 |

**The row above for B15-4 and every `arm III suspended` row in this table is superseded by §13**: B15-4 is re-decided on the publisher's own columns, the gate is open, and arm III's four criteria are verdicts. §9's account of the clock stands and is the reason for the re-decision.

**The 40.38% against Cuba's 207 of 207 is not withdrawn as a number and is not
available as a finding.** It sits in `results/b15_structure.json` with
`diagnostic_only` and a reason naming the criterion that suspended it. If B15-4
ever resolves, `arm_iii_runs` flips those records without anyone editing them,
which is why the gate is read out of arm II's record rather than restated in
each arm III script.

### 9.6 The shape of it

**Three criteria in this stage were decided by a preprocessing step nobody
registered.** §5 registers what B15-4 tests and what makes it void; it does not
register how the column's clock is established, because §3.4 assumed the answer
was readable off the step times themselves. The clock then got settled by an
unregistered two-hour line fed from the wrong file, and the criterion inherited
whatever that line said.

**The band histogram was never the instrument.** It was the only one available
while the clock was unknown, and it stopped being needed the moment the
publisher's own page was read. One request to a public page carried more than
36 step times did.

### 9.7 What the void costs, priced

```
RUN:    2026-08-21T10:45:00Z
DESIGN: §5 B15-7 (diagnostic beside it, not a criterion)
SCRIPT: experiments/b15_structure.py -> results/b15_structure.json,
        key `alignment_sensitivity`
```

**A diagnostic. It does not lift the suspension and no alignment below is
adopted.** §3.4 forbids choosing an alignment, and this section chooses none;
it reads the criterion off every alignment in a range so that the cost of not
knowing is a number rather than a sentence.

The two readings B15-4 was deciding between differ by one business day in which
official value is in force on a given date. Shifting the official leg against
the parallel leg by `k` days and reading `a(t) > 0` off each shift:

| `k` | days | `a(t) > 0` | median `a(t)` | |
|---|---|---|---|---|
| −2 | 50 | 56.00% | +0.0085 | |
| **−1** | 51 | **49.02%** | −0.0008 | **the publication reading** |
| **0** | 52 | **40.38%** | −0.0026 | **the vigencia reading, what B15-7 reports** |
| +1 | 51 | 35.29% | −0.0078 | |
| +2 | 50 | 26.00% | −0.0149 | |

**The registered threshold is 0.95 and Cuba's B6-15 reads 207 of 207.**

**So the void makes the number soft and leaves the verdict alone.** The two
candidate readings give 40.38% and 49.02%, a swing of nine points on a quantity
that would have to reach ninety-five, and every alignment within two days in
either direction lands between 26% and 56%. **What B15-4 could not settle is
what the number is, not which side of the threshold it falls on.**

**This does not make the comparison with Cuba available.** A criterion whose
arm is suspended has no standing whatever its sensitivity looks like, and the
register's gate is not conditional on the answer turning out robust; §3.4 says
suspended rather than aligned by guess, and a table showing that the guess
would not have mattered is still a guess. What this section establishes is
narrower and is worth having on its own: **if B15-4 is ever settled, the number
that comes out is bounded, and no settlement of it produces a Cuban reading.**

---

## 10. The get-list, closed

```
RUN:    2026-08-21T11:20:00Z
DESIGN: §5 B15-12; §7.2's get-list; §6 B15-9
```

Section 7.2 put three items on a get-list and said why an agent guessing URLs is
the wrong instrument for them: **a page on a government site is something a
person finds in seconds, and a guess that fails teaches only that it was a
guess.** All three are now closed, two by retrieval and one by identification.

### 10.1 The euro leg exists, at a different endpoint, and B15-12 can run

**Verified by one request.** The BCB serves a full `Tabla de Cotizaciones` at

```
librerias/indicadores/otras/otras_imprimir2.php?qdd=<day>&qmm=<month>&qaa=<year>
```

For `19/08/2026` it returns the page's own heading
`TABLA DE COTIZACIONES DEL 19 DE AGOSTO DE 2026`, the official USD at **11.52**,
**EUR at 13.33555** Bs per euro, `DEG` at 1.36743 USD per unit, `UFV` at
3.33255, twenty other currencies, gold, silver and SOFR.

**The USD figure cross-checks**: S3's official pair for 2026-08-19 is 11.52 /
11.52, from a different publisher.

**Section 7's finding is narrowed, not withdrawn.** `?anio=` selects a year and
nothing on that endpoint selects an instrument; that remains true and is what
was measured. What was not established, and what section 7.1 said explicitly
under `b8_pitfalls` entry 52, is that the BCB publishes no euro series
anywhere. **It does, one day per request**, which is the same shape as the S2
detail pages and costs one request per date.

**So B15-12's treatment changes from `pending on retrieval` to available.** It
is arm IV, it gates nothing, and running it needs the Bs/EUR and Bs/USD legs
over the window plus a world cross. **Not run here**, because retrieval on that
scale is a decision and not a step.

### 10.2 `D.S. 25870` Article 20, from the decree rather than from a citation of it

Section 6 read Article 20 through the Aduana comunicado's quotation of it. The
decree's own text now sits beside it:

> Para efectos aduaneros y cálculo de la base imponible, los valores expresados
> en moneda extranjera deberán ser convertidos en moneda nacional al tipo de
> cambio oficial de venta en el Banco Central de Bolivia, vigente al último día
> hábil de la semana anterior de la fecha de aceptación de la declaración de
> mercancías por la Administración Aduanera.

`Decreto Supremo N° 25870`, 11 August 2000, the Reglamento to the Ley General
de Aduanas. **The two texts are word for word identical**, so the citation in
section 6 was faithful and nothing there moves. The upgrade is in standing: a
quotation of a decree is now a quotation and a decree.

### 10.3 The superseded comunicado is dated, and the operative one is confirmed

The comunicado on disk closes with `Se deja sin efecto el comunicado publicado
en fecha 27/06/2026`, **so the superseded one is dated 27 June 2026** and the
comunicado being used is its replacement.

**The operative text was re-read against B15-9's constants, character by
character.** It states the peg applies `en la semana del 29/06/2026 al
05/07/2026` and that the floating rate applies to declarations accepted
`a partir del día lunes 06/07/2026`. `COMUNICADO_WEEK` is
`("2026-06-29", "2026-07-05")` and `CUSTOMS_SWITCH_DATE` is `2026-07-06`.
**They match exactly, and the week runs Monday to Sunday.**

**The superseded version put the switch two days earlier**, at Saturday 4 July,
reported rather than retrieved. That is consistent with a Saturday-to-Friday
week convention against the Monday-to-Sunday one the operative comunicado
states, but **the superseded document was not obtained and no reading is taken
from it.** B15-9's registered counterfactual still wants that document.

### 10.4 What did not come back, and what that does not license

**No documentation of the aggregator's refresh schedule was found**: no API
document, no FAQ, no developer statement on any public channel. The proposal
offered instead was that steps concentrated at 04:00 to 05:00 fit a once-daily
batch, **which is the same inference section 9.3 already declined to rely on**,
arriving from the same direction with no new evidence behind it.

**Absence of documentation is not evidence of the mechanism**, `b8_pitfalls`
entry 52 in its plainest form. B15-4's void stands and 04:00 to 05:00 remains
unattributed.

**No longer-coverage BCB series with an explicit `Vigencia` column was found
either.** That was reported rather than verified, so it closes the branch as a
lead and not as a fact: what the stage has is the 35 days S2's own export
carries, and that is still the only place the publication date and the date in
force appear as two columns of one file.

---

## 11. B15-12, the referee, and what it does not settle

```
RUN:    2026-08-21T12:05:00Z
DESIGN: §5 B15-12, §3 S6
SCRIPT: experiments/b15_calibration.py -> results/b15_calibration.json
```

**FAIL, and the failure carries a finding.** The register wrote that if
Bolivia's euro were Cuba's, a mechanical restatement of its dollar times a
world cross, this criterion would measure the pass-through. **It is not that.**

```
   lag  days  in band  nearest on   mean dev  ref ticks  outside rounding  dev/env med
     0    39    2.6%       21 d     0.00151       15.1       30/39              2.52
     1    39    2.6%       11 d     0.00208       20.8       32/39              2.84   Art. 5.III
     2    39    0.0%        6 d     0.00303       30.3       35/39              3.62
     3    39    0.0%        1 d     0.00395       39.5       35/39              5.45
```

The published `Bs/EUR` tracks the ECB reference cross and does not reproduce it.

**Rounding was computed rather than dismissed**, and the larger of the two
precisions feeding the implied cross is not the referee's. The TCO carries two
decimals, so half its last digit is `0.005` Bs, and at a TCO near 11.5 that
arrives in the cross as `5.0e-4`; the referee's own half-digit is `5e-5`, an
order of magnitude smaller. The envelope is computed per day from both.

**At the nearest alignment, 30 of 39 days fall outside that envelope**, by a
median of 2.52 times it and at most 8.59 times. Nine days sit inside it and
rounding accounts for those. **The other thirty it does not.**

**The size of the miss is worth reading as carefully as its existence.** A
median of two and a half times the envelope is a small number: the euro leg is
close to the cross, close enough that a different fixing moment or a
neighbouring commercial source would produce it, and nowhere near what an
independently administered rate would look like. **So the euro leg carries
something the dollar leg does not, and what it carries is small.** That is the
opposite of B6-5's Cuban reading, where the euro was the dollar restated, and
it is a difference between the two carriers in its own right.

### 11.1 The registered band cannot be met, and that is a defect in the band

§5 B15-12 fixes the band at **one tick of the published euro series**. The euro
is published to five decimals, so the band is `1e-5` Bs. The referee publishes
four decimals, so half its last digit at the largest TCO in the window is
**sixty-one ticks of the euro series**.

**The band sits below the floor that the referee's own publication puts under
any reconstruction**, so the first column above cannot pass on any alignment,
and its failing says nothing about Bolivia. It is reported rather than widened:
widening a registered band after seeing the numbers is the move this stage
exists to avoid, and the arithmetic that makes it unmeetable was available
before the run from two published precisions and a multiplication.

**This belongs beside the criterion-shape rule and not beside the result.** The
band is a line on an estimator whose noise floor was never computed, which is
the same family as a zero-width strict inequality: the failure mode is not that
the line is in the wrong place, it is that nobody multiplied two numbers before
drawing it.

### 11.2 It does not settle B15-4, and the scan is sharp enough to say so

**The hope, stated when the euro leg was retrieved, was that this would be an
external instrument for B15-4**: the world cross is published by somebody else,
the lag is measured rather than assumed, and none of it touches the aggregator
whose refresh schedule made B15-4 void. **It is not that instrument.**

Lag 0 is nearest on 21 of 39 days and lag 1 on 11, and lag 0 is nearer than lag
1 on **26 of 39 days paired on the same dates**. The deviation itself, at
fifteen referee ticks and two and a half times the rounding envelope, is
several times larger than the difference between the two lags. **A margin smaller than the noise it sits in does not discriminate**,
and the direction it leans is not the one Art. 5.III would predict anyway.

**The scan is not blunt in general, which is what makes this a null rather than
a shrug.** Run against a fixture built with a clean one-day alignment, the same
code puts 37 of 38 days on lag 1 with a mean deviation of zero. **It finds an
alignment when there is one.** Here there is none to find.

**So B15-4's void stands**, on this evidence as on the last.

### 11.3 Two things the run cleared up on its own

**The `TIPO CAMBIO EN M.E.` column is an internal identity.** On all 39 days
`1/ME` equals `EUR/TCO` to within `1e-4`. It is the published pair rearranged
and carries no information beyond it, so a comparison against it is not a
second reading of anything.

**An assertion I made without computing it is now computed.** The
first draft of this section said the deviation was "far outside what rounding
can account for" and did not carry the arithmetic that would show it. The
envelope is now built per day inside the criterion, from the two published
precisions and nothing else, and the count of days outside it is a printed
object rather than a claim.

**A threshold I invented after the run was removed before it could
be reported.** The first version of this criterion scored a column against a
`5e-4` band on the cross. That band appears in no register, it was chosen after
the deviations were on screen, and it landed in the middle of the distribution
it was scoring, so the share it produced was a property of the line. **It is
replaced by the distribution itself**: mean, median and maximum deviation per
lag, in units of the referee's own last digit, with no line on any of them.

### 11.4 Arm IV, closed

| | verdict |
|---|---|
| B15-10 the event | **FAIL**, and no single dated break is the reading |
| B15-11 zero calibration across publishers | **FAIL**, 18.26% against a registered 50% |
| B15-12 the referee | **FAIL**, and the euro is not the dollar times this cross |

**Three failures, and none of them is the instrument breaking.** B15-10 fails
because the reform ratified a rate the banks had already reached, B15-11
because two publishers of one book disagree by more than the calibration
allows, and B15-12 because the euro leg is not derived from the dollar leg.
**Each is a fact about the carrier.**

---

## 12. The question §1 opened the stage to answer, and a correction to §9

```
RUN:    2026-08-21T12:40:00Z
DESIGN: §5 B15-7; §3.4, §6.3 (diagnostic beside them, not a criterion)
SCRIPT: experiments/b15_structure.py -> results/b15_structure.json,
        key `alignment_sensitivity`
```

**Section 9 said the comparison was not made. That conflated two things and
one of them is false.**

**SUPERSEDED IN PART 2026-08-21T13:10:00Z, see §13.** B15-7 is adjudicable and is adjudicated: **FAIL**, 21 of 52. **This section is not withdrawn and changes role**: what it establishes is that the answer holds in every cell of the uncertainty, which is now a robustness statement beside a scored criterion rather than a substitute for one.

B15-7 is not adjudicable as registered: §6.3 suspends arm III on B15-4's void,
and a criterion cannot be scored on a date column whose meaning is open. **That
is a statement about the criterion.** Whether Bolivia reads as Cuba does is a
statement about the world, and it is answered.

### 12.1 The envelope, both axes at once

The suspension left two things open, and one of them is not the alignment.
B15-4 was deciding between readings that differ by one business day in which
official value is in force; B15-7 separately carries two readings of which
published number the ceiling is. **B15-6 settles the second on 35 of 35 days**
and it is swept anyway, so that nothing below rests on B15-6 either.

```
    k   days     published is the TCO  published is the venta
   -2     50                  56.00%                 66.00%
   -1     51                  49.02%                 62.75%
    0     52                  40.38%                 53.85%
    1     51                  35.29%                 50.98%
    2     50                  26.00%                 40.00%
```

**Ten cells, 26.00% to 66.00%. Cuba's B6-15 reads 207 of 207. The registered
threshold is 95%.**

**Take the most favourable cell**, which means taking the helpful end of both
axes at once and is therefore the worst case for the reading below: 66.00%, 33
of 50. If the true share were the registered threshold, seeing that or less has
probability `1.5e-10`. At the reading B15-6 settles and the alignment the
register expected, `3.2e-27`.

**No cell reaches. The answer does not depend on anything the suspension left
open.**

### 12.2 What actually failed, stated precisely

**Not an assumption about Bolivia's monetary arrangements.** §3.4 assumed that
*the local time of day at which the official series steps identifies the date
convention*, on the reading that a step marks either the 20:00 publication or
the midnight flip into force. **That assumption is about the instrument**, and
it is the one that broke: 31 of 36 steps land at 04:00 to 05:00 local, which is
neither hour, and most plausibly records the aggregator's own refresh rather
than the statute's clock.

The register's response to that is written into it: void, and suspend anything
needing a dated official value *rather than aligning by guess*. **That is a
rule about how criteria may be scored.** It protects B15-7 from being
adjudicated on a guessed alignment; it does not assert that the readings are
wrong, and §12.1 is the measurement of what the guess would have been worth.

### 12.3 How hard the answer is, by what could still move it

**Settled and swept**: the alignment, five cells; which published number is the
ceiling, two readings; sample size, the binomial above; the side convention,
which is void on the registered whole window but **live on the post-event
segment**, which is the only segment arm III runs on.

**One genuine limitation, and it cuts the safe way.** The two carriers are
different instruments: Cuba's informal leg is elTOQUE's series, Bolivia's is
the best available offer on one venue's Binance P2P book, and §3.6's A2 — that
the touch is executable at a size that is not zero — is registered as untested
here. **A thin quote nobody can hit would sit further from the ceiling, not
nearer**, so an unexecutable touch inflates `a(t)` and makes Bolivia look more
Cuban, not less. The limitation therefore weakens the direction this stage did
not find and leaves the direction it did find alone.

**The logical form is why one carrier is enough.** §1 asked whether the
framework would say of *any* controlled economy what it said of Cuba. That is
a universal, and a universal is settled by one counterexample. It would take
many carriers to say what the framework says of controlled economies in
general; it takes one to say it does not say the same thing of all of them.

### 12.4 What is therefore available and what is not

**Available**: Bolivia's informal ask is not systematically above the statutory
ceiling, on every reading of every open question, and B6's Cuban finding is
therefore specific to Cuba rather than a property the framework confers on any
controlled economy. **The pre-event segment sharpens it rather than softening
it**: measured against the frozen peg the same window gives 100%, and against
what the banks were actually selling at, 65.4% (§4.4). **A quote nobody
transacts at is what produces a Cuban reading**, which is a statement about
what B6-15 measures.

**Not available**: B15-7 as a scored criterion, with its `A_SHARE` and its
critical spread, and everything else arm III would have carried as a verdict.
**Section 9.5's table stands** and none of those rows moves.

**Not claimed**: any number as *the* number. 40.38% is the reading at the
settled ceiling and the register's alignment, and it is worth ±13 points across
the alignment axis alone. The finding is the envelope, not a point in it.

---

## 13. B15-4 re-decided, and arm III runs

```
RUN:    2026-08-21T13:10:00Z
DESIGN: §5 B15-4, §3.4; §6.3 guard_typing_first
SCRIPT: experiments/b15_typing.py -> results/b15_typing.json
```

**B15-4 reads `vigencia date`. `guard_typing_first` opens. Arm III's four
criteria are verdicts and their records carry no `diagnostic_only`.** §9's
suspension is superseded and §9's account of why the registered instrument
failed is not: that account is the reason this re-decision was made.

### 13.1 The instrument, which is the publisher's own two columns

`bcb_tco_series.csv` carries **`Fecha de corte`**, the day the bank operations
happened, and **`Vigencia`**, the day the resulting TCO governs, on every row.
Taking the system TCO off that file and asking which of the two dates the
official column is keyed on is B15-4's question, answered by the BCB.

```
   official column keyed on Vigencia        39 / 39
   official column keyed on Fecha de corte   1 / 35
```

**Both the BCB's own quotation tables and the aggregator's official column key
on `Vigencia`.** The one match under `Fecha de corte` is the coincidence of a
day whose two dates land on the same value.

**No clock, no aggregator's refresh, no third party, and no threshold on an
estimator.** It is two columns of one file matched against a third, and it is
the same instrument §5.3 already used before I voided that section
along with everything else the clock touched. **§5.3's argument never touched
the clock and voiding it was an error**; the pointer there is corrected.

### 13.2 Why replacing the instrument is the right move and not a repair

**D3's third category, and the reason is recorded rather than implied.** The
registered instrument reads the date convention off the local hour at which the
official series steps. Thirty-one of thirty-six steps land at 04:00 to 05:00,
at neither the 20:00 publication nor the midnight flip, so **it was measuring
the aggregator's refresh schedule and not the statute's clock.** An instrument
that answers a question about the wrong object does not become right by being
registered first.

**The original verdict is kept, not withdrawn.** `results/b15_typing.json`
carries `registered_verdict: VOID` and `registered_instrument` beside the live
one, and §9 stands as the account of what that instrument did.

**Nothing was chosen because it opened the gate.** The publisher's columns were
read before the gate was looked at, they answer a question that has one answer,
and §12 had already established that the comparison arm III carries does not
depend on which answer it is.

### 13.3 B15-3's gate is asked on the segment arm III uses

B15-3 is **VOID over the registered window and that stands**: the window
straddles §3.5's break, and 15.05% against 85.17% is one orientation read on
each side of it rather than one orientation failing.

**Arm III does not use that window.** It runs on the post-event segment alone
and discloses that it does. On that segment:

```
   pre-event    n = 69,657   A  9.001%   B 91.236%   does not resolve
   post-event   n =  4,966   A 99.960%   B  0.060%   resolves to A
```

**The gate now asks the segment.** Scoring a gate on a window the arm never
touches answers a question nobody asked, and the segment reading is a printed
field in the record rather than an inference at the gate.

### 13.4 The stage, closed

| | verdict |
|---|---|
| B15-1 retrieval integrity | **PASS** 760/760 days, 74,623 observations, 0 fills |
| B15-2 the known-answer arm | **PASS** prefix digest and an external anchor from a state body |
| B15-3 the side convention | **VOID** on the registered window, resolves to A on the segment arm III uses |
| B15-4 the date column | **`vigencia date`**, from the publisher's own two columns |
| B15-5 the statutory spread | **PASS** 0.10 exactly, 100.000% of non-degenerate rows |
| B15-6 TCO recomputation | **PASS** 35/35 days, 484/484 bank-days |
| B15-7 the posted return leg | **FAIL** 21 of 52 days, 40.38%, median −0.0048 |
| B15-8 the cycle | **PASS** determined on 52/52 under both ceiling readings |
| B15-9 the customs edge | **PASS** 8/8 weeks, the comunicado's anchor reproduces |
| B15-10 the event | **FAIL** no single dated break |
| B15-11 publisher calibration | **FAIL** 18.26% against 50% |
| B15-12 the referee | **FAIL** the euro is not the dollar times this cross |

**Twelve criteria, twelve verdicts, and B15-7 is one of them.**

**The question §1 opened the stage to answer is answered, and now by a scored
criterion rather than only by §12's envelope.**

**This stage is B6's zero calibration and that is the whole of its purpose.**
B6 found an edge the law grants, that is posted, and that nobody walks, on 207
of 207 Cuban publication days, and the one thing that reading could not
establish about itself is whether the instrument says as much of any economy
with an official rate and a parallel market beside it. Bolivia reads **21 of
52** against the same 95%, on four thresholds carried over unchanged. **The
instrument discriminates, so B6-15 is a fact about Cuba rather than a reflex of
the method.**

**What it discriminates on is sharper than the contrast between two countries.**
Measured against Bolivia's own frozen peg the same window reads 100%, against
what the banks were actually selling at 65.4%, and after the peg went and the
official rate began to follow the market, 40.38%. **A posted price nobody
transacts at is what produces the Cuban reading.** Bolivia had one until
2026-06-26 and stopped having one after, and the reading moves with that and
not with the country.

§12's envelope is not withdrawn and is now a robustness statement rather than
the finding: across five alignments and both ceiling readings the share runs
26.00% to 66.00%, and the answer holds in every cell.
