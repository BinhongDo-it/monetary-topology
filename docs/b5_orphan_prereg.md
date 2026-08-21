# B5: the square structure on Argentina's simultaneous exchange rates

Pre-registration. **Written before any data was retrieved.** Every filter,
threshold, window and criterion below is fixed here.

Availability, sourcing, and the ruling that this stage may be opened at all are
in [`b5_orphan_availability.md`](b5_orphan_availability.md). That document also
carries the two things a reader should see before this one: the blue, MEP, CCL
and P2P legs come from **a newspaper and community APIs, not a central bank**,
and the `H⁰` half of the original orphan-currency concept **is not in this
stage** (§9.1 below, and `PROJECT_PLAN.md` §14.3.1).

The directed theorems in [`b4_directed_edges.md`](b4_directed_edges.md) are
load-bearing here in a way they are not in B2 or B3. §2.3 states what they
removed from the design; §3.2 states the prohibition they impose on what may be
reported.

---

## 1. What this stage is for, in one sentence

Theorem 2 splits the obstruction on `Γ` into **squares** — two agents, one edge —
and **slice cycles** — one agent, several edges, loop closed. Stage B2 measured
squares on 20.1 million mortgages; stage B3 measured slices on cross-currency
basis. **This stage measures squares again, on a market that has nothing to do
with mortgages, and watches what happens when a government deletes the
eligibility rule that generates them.**

It is a **replication with an intervention**, and it must be presented as
exactly that. The replication half is worth little on its own: a second
non-zero number is a second non-zero number. The intervention half is the
reason the stage exists.

**`PROJECT_PLAN.md` §9.4 ruled that the orphan currency measures squares and not
slices.** §2.2 confirms that ruling from the shape of the data rather than
asserting it. **Do not run any slice-against-square decomposition on this
carrier**: Theorem 2 does not extend to directed graphs, directed cycles form a
cone and cones have no direct-sum decomposition (`PROJECT_PLAN.md` §12.10,
`b4` §6).

---

## 2. The graph, and where the squares are

Fix a date `t`. There is **one position pair**: `ARS` and `USD`. There is no
second position, no maturity axis and no path through an intermediate asset.
Everything in this stage lives on a single edge of the position graph `G`.

What varies is the **agent factor** `H`. Argentina prices one conversion five
different ways on the same day, and which price applies to you is fixed by
regulation.

### 2.1 The five agent classes, and the rule that admits each one

| class | who may transact | eligibility rule, as regulation |
|---|---|---|
| **oficial** | importers; individuals since April 2025 | import licence; formerly a USD 200 monthly cap |
| **MEP** / bolsa | anyone with a domestic brokerage account | securities settlement, formerly a parking period |
| **CCL** contado con liqui | anyone able to settle offshore | offshore securities account |
| **blue** | anyone, in cash | none |
| **P2P** `ARS/USDT` | anyone with a platform account and KYC | exchange account, not a state licence |

**Every row is an eligibility rule and not a price.** That is the whole point:
the differences below are not differences in what is bought — the conversion is
identical — but in **who is permitted to buy it**. This is `b2_measurement.md`'s
cell structure appearing in a market with no mortgages in it.

`dólar tarjeta` is a sixth rate and is deliberately **not** in this table. It is
`oficial × (1 + tax)` by construction, so it is not an independent agent class;
it is the known-answer arm and lives in §5.

### 2.2 Why these are squares, confirmed by shape rather than asserted

A square in `Γ = G × H` is two agents traversing **the same** position edge. A
slice cycle is one agent traversing **several** position edges and closing a
loop.

There is exactly one position edge here. **A slice cycle cannot be formed**, not
because the sample is small but because the graph has no second edge to walk to.
Corollary 2's shape argument runs in the opposite direction from B3's: B3's
carrier could not reach squares, this carrier cannot reach slices.

So every number this stage produces is a square sum, and `PROJECT_PLAN.md`
§9.4's ruling is confirmed by construction.

### 2.3 What B4 removed from the design, and it made the stage cheaper

Before `b4_directed_edges.md`, this stage would have reported a loop sum on a
market with a wide bid-ask spread. B4 §5.1 shows that number is `S`, a mixture
of two quantities that answer different questions, and that the two must be
separated:

```
S + S'  =  2 [ ω̄_a + ω̄_b ]     the two classes' round-trip frictions
S − S'  =  2 [ ŵ_a − ŵ_b ]      twice Theorem 1's square sum
```

Written in quoted numbers, with `rate` in pesos per dollar and `bid < ask`:

```
ŵ(ARS → USD)  =  −log √(bid · ask)          the log geometric mid
ω̄(ARS → USD)  =  ½ log(bid / ask)   ≤ 0      minus half the log spread
```

so for two classes `a`, `b` facing the same conversion,

```
S − S'  =  2 · log( mid_b / mid_a )
S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)
```

**The headline needs only the two mid quotes.** The spread cancels out of
`S − S'` by construction. B4 did not make this stage more expensive; it made the
headline computable from data every source publishes, and it made the number
defensible against the objection that it is a bid-ask artefact.

---

## 3. The measurement

### 3.1 Which source supplies which leg, and why they are not the same source

| quantity | class | source | why this one |
|---|---|---|---|
| headline mid | oficial | **BCRA Comunicación A 3500** | the central bank; authoritative; one legal reference rate |
| headline mid | blue | Ámbito `dolar/informal`, geometric mid of `Compra`/`Venta` | the standard published informal quote |
| headline mid | MEP, CCL | Ámbito `dolarrava/mep`, `dolarrava/ccl`, field `Referencia` | native single quote, see §3.3 |
| headline mid | P2P | `ARS/USDT` venue mid | the one class April 2025 did not touch |
| friction `ω̄` | oficial | **Banco de la Nación Argentina** posted counter rates | see §3.2 |
| friction `ω̄` | blue | Ámbito `dolar/informal`, `Compra` and `Venta` | one market, two-sided |

Endpoint, verified 2026-08-11:

```
https://mercados.ambito.com/<series>/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>
```

Dates are `DD/MM/YYYY` and **the decimal separator is a comma**. A parser that
assumes a period will silently produce numbers a hundred times too large, and
the fetcher asserts against this on every row.

### 3.2 The friction term does not use Ámbito's `dolar/oficial`, and this is load-bearing

Ámbito's `dolar/oficial` returns e.g. `1071.36 / 1125.54` on 22 April 2025, a gap
near five percent. **A central bank's reference rate does not have a five percent
dealer spread.** That series is a range across retail bank counters.

Reading it as `ω̄` would put **dispersion across banks** — which is an agent
index — into a quantity B4 defines as **one agent's round-trip cost**. That
inverts the entire separation of §2.3: the thing being removed as friction would
contain the thing being reported as signal.

**Ruled**: the friction term for the oficial leg comes from **BNA**, one legal
entity quoting both sides of one conversion, which is what `ω̄` is defined to be.
This keeps the friction column structurally symmetric with the blue leg, which is
also a single market quoting two sides.

The cheaper alternative — report the friction column for the blue leg only — is
rejected. An asymmetric column invites the reader to compare two things that were
not measured the same way.

### 3.2a The friction column has no source, and B5-8 is rewritten rather than deferred

**Ruled 2026-08-11 after three candidates failed.** `experiments/b5_friction.py`
holds the audit.

| candidate | why it is not the oficial friction leg |
|---|---|
| Ámbito `dolar/oficial` | a range across retail bank counters, §3.2 |
| **argentinadatos `oficial`** | **audited and rejected**: modal spread `6.00` ARS on only **29.1%** of dates against Ámbito's `6.00` on **28.9%** — the same fingerprint as the source §3.2 already refused. Median deviation from BCRA `2.90e-2` against the `0.02` bound, and a longest frozen run of **106 days**, worse than the `mayorista` series that was disqualified at 71 |
| Banco de la Nación direct | its historical page does not answer a plain request |

**A hand-check on two dates said the opposite, and was wrong for the second
time.** Both dates happened to sit on the same spread plateau, so the spread
looked round and constant; over the window it is neither. §7.4 of the
availability check now carries the general form of this: two agreeing dates are
not a check.

**So `S + S'` has no source for any pair**, and the second half of B5-8 — the
half that separates a collapse in the eligibility premium from the whole market
going quiet — cannot be computed. **This is not a deferral. It is a permanent
property of what is free**, and B5-8 is rewritten to use a control that the data
already contains.

### 3.2b The replacement control: pairs whose eligibility rule was not touched

The original B5-8 needed the friction column because it needed *something that
should not move*. That something is available without it.

**On 14 April 2025 the deleted rule was oficial's**: the USD 200 monthly cap on
individuals. **MEP's and CCL's eligibility was a brokerage account before and a
brokerage account after.** So the six pairs split into two groups by whether the
pair contains the treated class:

- **treated pairs**: `oficial–blue`, `oficial–MEP`, `oficial–CCL`
- **control pairs**: `blue–MEP`, `blue–CCL`, `MEP–CCL`

Both groups live in the same market, on the same dates, through the same
devaluation, the same IMF programme and the same band regime. **Only the treated
group contains a class whose eligibility rule was deleted.**

**This is stronger than the friction column it replaces, and the reason is
worth stating.** The friction version needed an extra assumption — that
round-trip costs do not respond to a change in eligibility rules — which is
plausible and unargued. The control-pair version needs no such assumption: it
compares premia to premia, in the same units, from the same quotes.

**And it is weaker in one respect**, which the write-up states: MEP and CCL are
not untouched by everything. §14.5 of `PROJECT_PLAN.md` records that the
cross-restriction between the official and financial markets was removed on the
intervention date and **reimposed in September 2025**, inside the post-window. So
the control group is clean with respect to the *deleted cap* and not with respect
to every rule. `blue` is the only class whose access was never rule-bound at all,
which is why `oficial–blue` remains the headline pair.

**Registered before the estimate**: the treated group's ratio of post to pre must
be **below** `1/3` and the control group's **above** `2/3`, the same two bands §7
already carries for B5-8's two halves, now applied across pairs rather than
across columns.

### 3.3 MEP and CCL have no bid and ask, and that is not a gap in the source

`dolarrava/mep` returns a single `Referencia`. MEP is a **ratio of two bond
prices**, `AL30` in pesos against `AL30D` in dollars, so it has no native
two-sided quote; a spread for it would have to be built from four bond legs.

**Consequence, and it is a real narrowing of the design.** The friction column
`S + S'` is computable **only for the oficial–blue pair**. MEP, CCL and P2P enter
the headline `S − S'`, which needs mids only, and cannot enter the column beside
it. This is registered here rather than discovered at write-up.

**Prohibited**: constructing a synthetic MEP spread from another class's quotes,
from a lagged quote, or from an OHLC range. `b4` §5.2 — filling a missing leg
with a different agent's price fills it with exactly the quantity in dispute.
Investing.com was invoked for this purpose during the availability check and
rejected on these grounds (`b5_orphan_availability.md` §7.3).

### 3.4 The aggregation is geometric, because the claim is stated in logs

Mids are **geometric**: `mid = √(bid · ask)`. Daily series are aggregated across
a window by **root mean square of the log quantity**, never by arithmetic mean of
the levels. `MEASUREMENT.md` §3 records what happens when a claim stated in logs
is aggregated arithmetically: 31% of an error, unrelated to any mechanism.

Both sides of every comparison use the same weighting: one day, one observation.
No volume weighting, because volume is not published for four of the five
classes and weighting one arm and not the other is `MEASUREMENT.md` §3's failure
in its second form.

---

### 3.5 The endpoint returns intraday snapshots, and each date is collapsed to one row

**Registered 2026-08-11, after retrieval and before any headline was computed.**
See §11. The availability check did not report this and the first retrieval
found it: 385 of 5,248 rows carried a date that another row also carried, between
two and nine rows per date, with different values and **no timestamps**.

| series | dates carrying more than one row | within-day log range, median | p90 | max |
|---|---|---|---|---|
| oficial | 90 | 0.00097 | 0.0049 | **1.1545** |
| blue | 108 | 0.00503 | 0.0165 | 0.0445 |

**This is load-bearing rather than housekeeping.** Against the cepo-era gap,
which is of order `0.7` in logs, a within-day ambiguity of `0.0165` is nothing.
Against the few-percent gap that remains after April 2025 — which is the window
criterion B5-8 reads — it is **about a third of the signal**. A rule chosen after
seeing the post-window number would be a rule chosen to produce it.

**Registered rule: each date is represented by the single row whose mid is that
date's median mid, taking the lower median on ties and even counts.**

**A whole row is selected, not a statistic computed per field.** The friction
term is `log(bid/ask)` from one quote. A median bid paired with a median ask is a
quote nobody published, and the spread of a manufactured quote is not a market's
spread.

**Median rather than mean.** On 21 August 2024 `dolar/oficial` returns
`954.12 / 300.76 / 953.17` for one date; the middle value is a level the peso
last saw in mid-2023. The mean is `736` and belongs to no market. This project's
standing lesson on non-robust statistics under contamination is
`PROJECT_PLAN.md` §11.2, and it cost a headline number.

**Median rather than first-or-last.** "The closing quote" is the conventional
choice and it is **not identifiable here**: the endpoint publishes no timestamps,
so first-or-last would rest on an inference about array order that the source
does not document.

**Nothing is dropped.** The raw files keep every snapshot verbatim; the collapse
happens on load. The per-date row count and log range are written to the manifest
for every affected date, so a reader who prefers a different rule can see exactly
what the choice was worth on each day.

> **⚠ Outcome of B5-3b, 2026-08-11. This rule lost its one external check.**
> Against BCRA's A 3500 fix on 115 multi-row dates, the closest snapshot was
> `last` 60.9% of the time, `first` 51.3%, and **the registered `median` 34.8%**.
> The rule does not move — changing it on that evidence would be choosing after
> seeing which one agreed — but **every number downstream of this section carries
> the fact**. Details, and why `last` is still not safe on its own, in §4.4a.

### 3.6 A gap in the series is not a one-day change

**Registered 2026-08-11, same occasion.** A "one-day change" is only that if the
two observations are adjacent. Long weekends and Argentine holiday clusters reach
five or six days; beyond `MAX_GAP_DAYS = 7` the neighbours are not neighbours,
and the anomaly scan records a **gap** and resets its comparison chain rather
than reporting a jump.

Without this, a chunk that failed to download turns the two dates either side of
the hole into a spurious jump — which is exactly what the first run produced for
MEP, a "one-day change" dated 2026-01-01 against a previous date in December
2024. The threshold is loose on purpose: a gap rule tight enough to skip a
Friday-to-Monday break would silence the 14 August 2023 devaluation, which is a
genuine move of that shape.

---

## 4. The zero calibration, and an unresolved problem with it

`MEASUREMENT.md` rule 7 makes a zero-calibration arm mandatory for every new
carrier, not optional. It is the only one of the eleven measurement failures in
this project's history that was caught by an automatic guard rather than by a
human noticing a strange number.

**The requirement is one agent class observed twice by independent collection
paths.** The index part between the two observations must be zero, and a non-zero
result can only be a reporting failure.

### 4.1 Primary construction: BNA's own posting against a third party's report of it

**BNA's published counter rate against an aggregator's "Banco Nación" quote.**
One dealer, one counter, one conversion, two collection paths. The index part
must be zero to within the quoted increment.

### 4.2 Why this arm may be vacuous, and the guard that must decide it

`b5_orphan_availability.md` §7.7 registered aliasing as a pre-flight assertion:
if two outlets republish one survey rather than polling their own sources, the
two series are one series and the arm tests a copy-and-paste rather than a
pipeline.

**That risk is unusually high for this particular construction**, because an
aggregator reporting "Banco Nación" plausibly does so by reading BNA's own page.
If it does, the two series will be byte-identical and the arm will pass
trivially.

**A trivially passing arm is a failure, not a pass.** `PROJECT_PLAN.md` §11.11
rule 1: a criterion whose comparison has an empty or degenerate side must fail
and print `vacuous`. This is registered as **B5-4** and it runs **before** B5-3
is read.

### 4.3 The fallback was wrong, and the reason is worth more than the fallback

**Withdrawn 2026-08-11, before any zero-arm number was computed.** The first
version of this section proposed **two constructions of MEP** — the
`AL30 / AL30D` bond pair against `GD30 / GD30D` — on the grounds that both are
the same agent class making the same conversion through two different
instruments.

**That is not a zero calibration and it cannot become one.** `AL30` is governed
by Argentine law and `GD30` by New York law; they carry different default risk
and different liquidity, and their spread is an actively traded quantity. So the
true index part between them is **not zero**, and a non-zero reading could be
either a pipeline failure — the thing the arm exists to detect — or the genuine
legal-jurisdiction spread. The two are indistinguishable, which is exactly the
objection `b5_orphan_availability.md` §7.7b raised when it kept P2P out of this
arm: *putting it in the zero arm means alias failure and a genuine difference
would look identical.*

**The general form of the mistake, because it will be offered again.** An
external suggestion argued for this pair *precisely because* the two bonds are
driven by different risks, and concluded that this makes the arm **non-vacuous**.
Non-vacuous and valid are two requirements, not one. Buying non-vacuity by
destroying the known zero leaves an arm that always has something to say and
never says anything.

### 4.4 What a zero arm actually needs here: independence of format, not of source

The tension looks unresolvable. A true zero requires both series to measure the
**same underlying number**, which is exactly what makes them liable to be
identical, which §4.2 then calls aliasing.

It resolves once the arm's object is named correctly. **The zero calibration
tests this project's pipeline, not the publishers.** So the independence that
carries the test is not independence of source. It is:

> **One underlying number, two different formats, two different parsers, and the
> result must be exactly zero.**

That is available and it is not trivial. BCRA serves JSON with **period decimals
and ISO dates**; Ámbito serves strings with **comma decimals, thousands
separators and `DD/MM/YYYY`**. A single quantity carried through both parsers
and still agreeing to the quoted increment exercises every step this stage's
headline depends on: the decimal convention, the date convention, the field
selection and the alignment.

**The pair first registered here was wrong, and the arm is what found it.**

The wholesale rate (`mayorista`) is published by Ámbito and by argentinadatos.
Two dates checked by hand agreed to the cent, and the arm was registered on that.
**Run over the window it fails, and with BCRA's A 3500 as an independent referee
the reason is not this project's pipeline:**

| deviation from BCRA A 3500 | median | p90 | max |
|---|---|---|---|
| Ámbito `mayorista` | `2.6e-3` | `8.0e-3` | `1.07e-1` |
| argentinadatos `mayorista` | `2.6e-3` | `1.55e-2` | **`1.60`** |

On 13 December 2023 Ámbito and BCRA both move from about `365` to about `800`,
the Milei devaluation, and **argentinadatos sits at `365.45` for weeks**. Its
longest run of an unchanged sell quote is **71 days**, against 13 for its own
`tarjeta`. The premise that the two are one number is false.

**The fault is in that series, not in the publisher**, and the evidence is the
contrast with `tarjeta`, which tracked the same devaluation correctly. So §5.2's
dating instrument survives.

**This is the arm paying for itself.** It found no error in this project's
pipeline because there was none — BCRA confirms the Ámbito side through a
completely separate parser — and instead found that its own premise was wrong.
That is the only return a calibration arm can give when the pipeline is sound,
and a stage that had used the frozen series anywhere substantive would have
carried a flat line through the largest devaluation in its window.

### 4.4b What runs instead: bounded agreement, with the bound derived not observed

**Ámbito `mayorista` against BCRA Comunicación A 3500.** Two parsers with nothing
in common: comma decimals, thousands separators and `DD/MM/YYYY` on one side;
JSON numbers and ISO dates on the other. Two publishers, one of them the central
bank.

**They are not the same quantity.** A 3500 is the central bank's reference and
`mayorista` is the interbank market, so the answer is not exactly zero and the
criterion is not equality. What the arm must catch is a **parse error**, and both
bounds come from that rather than from the data:

- **A systematic error moves every row.** The smallest parse error worth naming
  is a factor of ten, which is `2·log(10) = 4.61` in these units. The registered
  bound on the **median** is **`0.02`**, two hundred and thirty times tighter
  than the smallest thing it must catch.
- **A partial error touches only some rows.** A thousands-separator bug reaches
  only quotes above a thousand, which here is only the later years, and could
  leave a median untouched. The registered bound is that **no single date exceeds
  `0.5`**. Any parse error is on a log scale and clears that; two readings of one
  market do not.

**The tail between the two bounds is reported and not judged.** Two different
objects genuinely diverge on volatile days, and a criterion on the maximum would
be measuring Argentine volatility rather than this repository's parsers.

**What the arm cannot do, stated so nobody claims otherwise.** It tests *this
project's pipeline*. It is not a source audit; that is B5-5's job (§5) and the
provenance admission is §9.4's.

**The wholesale rate is used for this arm and for nothing else.** Not an agent
class, not in the headline, not the oficial leg. It lives in
`parallel_rates.INSTRUMENTS` rather than `SERIES` so it cannot drift into a pair.

**Still open, and not on the critical path**: BCRA publishes A 3500 a second time
as `com3500.xls`, reachable and free, which would be one number in two formats
from one authority and therefore an **exact**-zero arm. Its file format is
unverified and a real binary workbook would cost a dependency this repository
does not have. Registered as an improvement to pursue, not as a blocker.

**If B5-4 fails, or B5-3 breaches either bound, this stage has no calibration and
does not report a headline.** Registered here so it cannot be renegotiated later,
with a headline number already sitting on the screen.

### 4.4a The multi-row dates give the collapse rule its first external check

§3.5 registered the median-of-the-day collapse on internal grounds: the mean is
destroyed by the 21 August 2024 contamination, and first-or-last needs a
within-day ordering the endpoint does not document. **Defensible, and until now
unverifiable.**

Ámbito's `mayorista` carries the same intraday snapshots as its other series
(`2025-06-04` appears twice), while argentinadatos publishes one value per date.
So on exactly those dates the two sources disagree about *which* snapshot the day
is, and that disagreement is readable.

**Registered as B5-3b**, and it is a diagnostic rather than a gate: on dates where
Ámbito carries more than one row, report which of the **median**, the **first**
and the **last** of that day's rows sits **closest to BCRA's A 3500 fix** for the
same date. A relative comparison rather than a tolerance, because the two are
different objects and no tolerance between them would mean anything. Ties count
for every rule achieving the minimum, so the shares may sum above one.

**Registered before looking**: if the median wins, §3.5 gains outside support it
did not have. If first-or-last wins, §3.5 is recorded as **unsupported by the one
external check available**, and every headline computed under it carries that
sentence. Whichever way it goes the registered rule stays the median for this
stage, because changing it here would be choosing a rule after seeing which one
agreed. A future stage may register the winner up front.

#### Result, 2026-08-11: the median lost, and §3.5 now carries the sentence

On 115 multi-row dates: **`last` 60.9%, `first` 51.3%, `median` 34.8%.**

So the collapse rule this stage runs under is **not** the one closest to the
central bank's fix, and that is now a known property of every number downstream
of it rather than an open question. The reading is unsurprising in hindsight —
A 3500 is struck by a survey late in the day, and the last snapshot is the one
nearest that moment — which is exactly why it could not be allowed to decide the
rule after the fact.

**What does not change.** The median was chosen because the mean is destroyed by
the 21 August 2024 contamination (`954.12 / 300.76 / 953.17` on one date) and
because `last` depends on an array ordering the endpoint does not document. That
reasoning stands; this result says the undocumented ordering appears to be
chronological, not that the median is unsafe. **`last` would have taken `300.76`
had it fallen at the end of that day's rows**, and nothing in the payload says it
could not.

**Registered for whoever opens the next stage on this carrier**: `last` is the
candidate to register up front, *paired with* an outlier guard, and not on its
own.

### 4.5 The aliasing rule, corrected

§4.2's rule as first written would kill the good case along with the bad one.
Refined, and the distinction is the whole point:

- **Byte-identical payloads are fatal.** That is one file read twice, and the
  arm would be testing a copy rather than a pipeline.
- **Identical values arriving in different formats is exactly what is wanted.**
  Agreement to the last digit is then the result, not the disqualification.

So B5-4 tests the **bytes**, not the values: if the two payloads are identical
after normalising whitespace, the arm is `vacuous` and fails. If they differ as
bytes and agree as numbers, the arm has done its work.

---

## 5. The known-answer arm does not exist on free data, and what replaces it

**Rewritten 2026-08-11, before any headline was computed.** The section below
first registered `dólar tarjeta` as a known-answer arm: an independently
published series that must equal a regulated constant times `oficial`, used to
catch a broken pipeline before the headline is read. **Retrieval showed there is
no such series.**

**Every free `tarjeta` series is computed by its publisher from that publisher's
own `oficial`.** Verified on two of them:

| source | date | oficial | tarjeta | ratio |
|---|---|---|---|---|
| Ámbito `dolar/tarjeta` | 2024-06-03 | `878.72 / 937.66` | `878.72 / 937.66` | **1.0000, identical to the cent** |
| Ámbito `dolar/tarjeta` | 2025-06-05 | `1163.97 / 1206.55` | `1163.97 / 1206.55` | **1.0000** |
| argentinadatos | 2026-06-29 | `1445 / 1495` | `1878.5 / 1943.5` | **1.30000 on both legs** |
| argentinadatos | 2021-08-02 | `96 / 102` | `96.12 / 168.50` | `1.00125` and `1.65196` |

Ámbito's endpoint is **aliased to `dolar/oficial`**: byte-identical, in a month
when the PAIS tax and the perception were both in force and the true multiplier
was about `1.6`. argentinadatos publishes a genuine multiplier, but it is *their*
multiplier applied to *their* `oficial`, and the construction changed between
2021 and 2026.

**So the arm as registered would be a tautology.** `tarjeta / oficial` from one
publisher is exactly the constant by construction and cannot fail. Taking
`tarjeta` from argentinadatos against `oficial` from BCRA does not rescue it
either: that measures argentinadatos' `oficial` against the central bank's, which
is not a known constant.

### 5.1 Two of the three failures the arm was advertised to catch, it never could

The first version claimed the arm catches *a comma-versus-period parse, a date
misalignment, and a mid computed arithmetically instead of geometrically*.
**The first and the third cancel in a ratio of two series read by one parser**,
and a scale error of a hundred cancels exactly. Only the date misalignment
survives, together with reading the wrong field or the wrong series.

Recorded rather than quietly narrowed, because an arm believed to cover three
failure modes and covering one is worse than an arm known to cover one: the
other two stop being watched.

### 5.2 What the series is good for instead: dating the regime, from the data

`tarjeta / oficial` within one publisher is a **construction identity**, and a
construction identity run across the window is a **dating instrument**. The
multiplier steps, and the steps are the tax regime landing in the data:
`≈1.65`, then `1.60`, then `1.30`.

**The dates are read off the series and are not hard-coded.** An external
suggestion proposed asserting `≈1.60` before 2024-12-23 and exactly `1.30`
after. That reintroduces a check that cannot fail for the right reason, and it
throws away the one thing the series is now useful for. It also assumes the
publisher changed its formula on the day the regulation took effect, which the
same suggestion elsewhere concedes is usually off by a day or two.

**Registered instead**: the experiment reports the multiplier per day, the dates
on which it steps, and the value on each plateau. `b5_orphan_availability.md`
§7.5's regulatory account (PAIS repealed 2024-12-23, the 30% perception retained
under ARCA RG 5617/24) is the **prior**, and a disagreement between the
regulation's date and the data's date is a finding about the publisher rather
than an error to be corrected away.

**And the constant is no longer registered at `1.30` for the whole window.**
That was written when the window was believed to open after the repeal; the
window opens 2019-09-01, so it spans all three plateaux. §7's row is corrected
accordingly.

### 5.3 The consequence for the stage, stated plainly

**All of the pipeline-checking load now sits on the zero calibration**, §4.4,
and on B5-1, B5-2 and the parser assertions in §10. That is a real reduction in
defence, and it is the reason §4.4's arms are on the critical path rather than
in reserve.

---

## 5A. Superseded text, kept for the record

`dólar tarjeta` is `oficial × (1 + tax)` **by regulation**. Its index part
against `oficial` must equal `2 log(1 + tax)` and nothing else, with the tax rate
read from the regulation and never fitted.

**The constant is `1.30` throughout this stage's window, and the arithmetic
behind that is not the schedule most sources still quote.** The 30% PAIS tax
ended 23 December 2024. The 30% perception on account of income and wealth tax
was retained by ARCA Resolución General 5617/24. Residual provisions were
formally cleared 2 January 2026. This stage's post-intervention window opens
after the PAIS repeal, so the arm is a flat constant rather than a piecewise
schedule, which makes it cleaner than it would have been a year earlier.

```
index part of tarjeta against oficial  ≡  2 · log(1.30)  =  0.5247…
```

A pipeline returning anything else is broken **before the headline is read**, and
the headline is not read. This is the arm that catches a comma-versus-period
parse, a date misalignment, and a mid computed arithmetically instead of
geometrically, all of which have analogues in this project's error log.

---

## 6. Pre-registered predictions

Ten criteria. **Four of them are guards that run before anything is read**
(B5-1, B5-2, B5-4, B5-5), one is a pre-flight on the load-bearing criterion
(B5-11), and one is the reason the stage exists (B5-8).

**B5-1 — the pipeline agrees with its own closed form.** The square sum obtained
by decomposing each quote into `ŵ` and `ω̄` through `directed.py` and then
traversing the four edges of the square through `product_graph.py`'s cochain
machinery must equal the closed forms of §2.3 elementwise:

```
S − S'  =  2 · log(mid_b / mid_a)
S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)
```

Threshold: worst relative error below `1e-14`. The matrix of `S − S'` must be
antisymmetric and the matrix of `S + S'` symmetric, to the same tolerance.

**The two representations are deliberately not shared.** `directed.py` does not
reuse `product_graph.py`'s field representation, because the latter's
`Cochain.value` returns `−value(v,u)` when only one orientation is stored, which
would silently convert a one-way market into a two-way one. This criterion is
the check that the hand-off between them is correct.

**B5-2 — the trivial square is exactly zero.** `z(a,a) = 0`, **taken off the
diagonal of the same difference matrix every other number comes from**, not
short-circuited on `a == b`. A short circuit tests the `if` statement.

**B5-3 — the two parsers agree within bounds set by what they must catch.**
Ámbito `mayorista` through the comma parser against BCRA A 3500 through the JSON
parser (§4.4b). **Median** deviation `≤ 0.02`, and **no single date** above
`0.5`. Not equality: the two are different objects. Both bounds are derived from
the smallest parse error worth naming, `2·log(10) = 4.61`, and neither from the
observed distribution. The tail between them is reported and not judged.

**B5-3b — the collapse rule against an outside opinion.** On dates where Ámbito
carries **more than one row**, report which of the **median**, **first** and
**last** sits closest to BCRA's fix (§4.4a). **Diagnostic, not a gate, and the
registered rule does not change on this evidence.** It did not: the median lost,
and §4.4a records the consequence that every headline now carries.

**B5-4 — the arm is not one file read twice, and this runs before B5-3.**
Two checks. The payloads must not be identical after normalising whitespace; and
**each parser must refuse the other's payload**, which is what proves the two
collection paths exercise different code. A pair passing the first and failing
the second would be two formats read by one lenient reader, and the arm would be
testing that reader against itself. Failure prints `vacuous` and **fails**
(`PROJECT_PLAN.md` §11.11 rule 1).

**Corrected 2026-08-11.** The first version tested agreement of *values* and
failed the arm when they agreed on more than `0.80` of days. That rule would
have killed the arm §4.4 is built on, whose whole point is that the values agree
exactly while the formats do not. Identical values in different formats is the
result; identical bytes is the disqualification.

**B5-5 — the multiplier is piecewise constant and its steps are reported, not
asserted.** Within one publisher, `tarjeta / oficial` is a construction identity
(§5). The experiment reports the multiplier per day, the dates on which it
steps, and the plateau values. **Registered expectation, which can fail**: the
series is piecewise constant with **at most four plateaux** over the window, and
each plateau sits within the quoted increment of a value expressible as
`1 + PAIS + perception` at rates the regulations name.

**What failure means here is different from the other criteria.** A multiplier
that drifts rather than steps, or plateaux that match no regulated combination,
says the publisher is not doing what it appears to do, and every use of that
publisher's series is then in question — including `blue`, `mep` and `ccl`,
which come from Ámbito. So this is a **source audit** rather than a pipeline
test, and it is the only one the stage has.

**It replaces a criterion that could not fail.** The withdrawn version asserted
`2 log 1.30` against an independently published `tarjeta`, and no such series
exists on free data (§5).

**B5-6 — the signal is above the noise floor, on matched days.** With `Z` the
mean square index part across class pairs and `N` the same quantity computed on
the zero-calibration arm,

```
Z / N  >  4
```

the same factor B3-3 used. **`Z` and `N` are computed on the same set of dates
and with the same aggregation.** A6's noise floor was once computed on
2012–2025 while its signal was computed on 2000–2025; `PROJECT_PLAN.md` §11.11
rule 3 exists because of it.

**B5-7 — the squares do not vanish before the intervention.** On the pre-window
(§7), the oficial–blue index part clears the same factor of four over the noise
floor. If it does not, this carrier has no measurable agent index and nothing
downstream may be read.

**B5-8 — the load-bearing criterion: the treated premia collapse and the
untouched ones do not.** **Rewritten 2026-08-11**; the version that used the
friction column is in §3.2a, together with why no source for it exists. Across
the event windows of §7,

```
treated  rms(S − S')  post  ≤  (1/3) · pre     oficial–blue, oficial–MEP, oficial–CCL
control  rms(S − S')  post  ≥  (2/3) · pre     blue–MEP, blue–CCL, MEP–CCL
```

Both groups computed **on the same days from the same quotes**, and the split is
by whether the pair contains the class whose eligibility rule was deleted
(§3.2b). This is what makes
the design survive the confounding: April 2025 also brought an IMF programme, a
band regime and a devaluation, and every one of them moves the level of
everything. A confound that moves the peso moves **both** quantities. The
framework predicts that **only one moves**. That is `MEASUREMENT.md` rule 4
satisfied by a comparison rather than by an assumption.

**Both halves must hold.** A collapse in `S − S'` alone is compatible with the
whole market having become quiet, and would not distinguish the framework's
prediction from a general narrowing.

**B5-9 — the control class does not collapse.** The index part of `P2P` against
`blue`, across the same event windows, satisfies

```
rms  post  ≥  (2/3) · rms  pre
```

P2P's eligibility rule is a platform account rather than a state licence, so it
is **the one class whose access the April 2025 intervention did not change**. If
its index part collapses too, the collapse in B5-8 is not attributable to the
deletion of the eligibility rule, and B5-8's causal reading fails even if its
arithmetic passes. This is a within-design control that no other class can
supply.

**B5-10 — the anomalous rows are reported both ways.** The headline is computed
twice, with and without the rows flagged by §7's jump threshold, and **both
numbers are reported**. There is no pass threshold. If they differ materially,
that is the finding rather than a problem to be cleaned away.

**B5-12 — the difference in differences, and the control group is inside
Argentina.** B5-8 and B5-9 are the two arms of one estimand, and stating it as
one is clearer than stating it as two thresholds:

```
DiD = [ rms(S−S')_{oficial–blue, post} − rms(S−S')_{oficial–blue, pre} ]
    − [ rms(S−S')_{P2P–blue,     post} − rms(S−S')_{P2P–blue,     pre} ]
```

**The control unit is a class pair, not another country**, and the reason is
that the outcome variable does not exist elsewhere. `S − S'` is the premium
between two *eligibility classes* facing one conversion. Chile and Brazil have a
single market rate for the dollar, so there is no second class to difference
against and the quantity is **undefined** there rather than small or stable. A
design that used them would have a control group whose outcome cannot move, the
estimate would collapse to the treated group's before-after difference, which is
B5-8 on its own, and the standard error would advertise a control that did no
work. Forcing it by taking two *quote sources* for the same Chilean rate would
measure reporting differences, which is this stage's zero calibration (§4) and
not an agent index.

`P2P` against `blue` holds the country, the currency, the macro shock and the
dates fixed and varies only whether the eligibility rule was deleted, which is
the one thing the framework says should matter.

**B5-13 — parallel trends, and it can refuse the design.** On the eight quarters
before the intervention, the two pairs' `rms(S−S')` series are regressed on a
linear trend within each pair. If the difference in slopes is distinguishable
from zero at the registered band, **the pairs were already diverging and the DiD
is not identified**; B5-12 is then reported as uninterpretable and the stage
falls back to B5-8 and B5-9 as separate before-after statements, with that
weakening stated in the headline rather than in a footnote.

**Registered robustness ladder, fixed here and not after seeing the estimate**:
B5-12 is computed at event windows of **±365 days (primary), ±180 and ±90**, and
**all three are reported** whatever they show. Choosing among them afterwards is
the degree of freedom this ladder exists to remove.

**B5-11 — pre-flight on B5-8: the two columns must not already move together.**
On the pre-window, the correlation of daily changes

```
| ρ( Δ(S − S') ,  Δ(S + S') ) |  ≤  0.5
```

If the index part and the friction part already track each other before the
intervention, then B4 §5.1's separation is not doing work on this carrier, and a
divergence after the intervention cannot be attributed to the separation. **B5-8
is then reported as uninterpretable rather than as a finding.** This criterion
was added while drafting the pre-registration and its threshold is registered
here with the rest.

---

## 6A. B5-14, registered after retrieval, and what was known when it was written

**This section is separated from §6 because its timing is different and a reader
must be able to see that at a glance.** Everything in §6 was fixed before any
Argentine series was on disk. B5-14 was written after retrieval, after the P2P
audit returned `reject`, and after B5-8 had run. That is permitted, and the
condition attached to it is that the result is reported whatever it shows. The
constants below are fixed in this section and not after seeing a slope.

**What was known when this was registered**: B5-8's six pair ratios (treated
`0.102`, `0.110`, `0.177`; control `0.712`, `1.050`, `0.999`), B5-7's pre-window
`rms = 0.4996` on the headline pair, and the calibration arm's `0.00260`.
**What was not known**: any monthly bucket series and any slope. None had been
computed, and the code that computes them did not exist.

### 6A.1 The hole this fills

`B5-11` was `B5-8`'s pre-flight and it does not run: it needs the friction
column, which has no source (§3.2a, §8.2). **So B5-8 currently has no pre-flight
at all**, and the specific failure it is unguarded against is that the treated
and control groups were already diverging before 14 April 2025, which would make
B5-8's collapse ratio a pre-existing trend wearing an event's clothes.

`B5-13` was written to catch exactly that and it does not run either, because its
control unit was `P2P` and the P2P candidate was rejected (longest frozen run 47
days against the registered 21, `experiments/b5_p2p.py`).

**B5-14 is B5-13's question asked of the control pairs that do exist.**

### 6A.2 Why these pairs are admissible here and not in B5-12

§8.1 refuses MEP and CCL as B5-12's control unit because their cross-restriction
was removed on the intervention date and reimposed in September 2025, **both
inside the post-window**, so they were treated twice.

**That objection is entirely about the post-window.** Parallel trends is a
pre-window test, and through the pre-window MEP's and CCL's rule regime is
stable: the cross-restriction is in force for the whole of it and does not move
until the intervention date itself. So the same pairs are admissible for a
pre-window trend comparison and inadmissible as B5-12's control unit, and the two
statements do not collide.

### 6A.3 The criterion

For each pair, `rms(S − S')` is bucketed by calendar month, the bucket values are
regressed on `1 … N` within the pair, and the slope is taken. The comparison is
the slope difference between a treated pair and a control pair.

**Window, primary rung: the registered `PRE_WINDOW`**, 2024-04-14 to 2025-04-13,
twelve monthly buckets. **Not** B5-13's eight quarters, and the reason is
specific: eight quarters reaches back to 2023-04-14 and encloses the **13
December 2023 devaluation**, across which a linear trend is not a description of
anything. `MEASUREMENT.md` rule 1 supplies the second reason: B5-8's ratios are
computed on `PRE_WINDOW`, and a trend fitted on a different window is a trend in
a population B5-8 does not use.

**Second rung: the eight quarters B5-13 named**, 2023-04-14 to 2025-04-13,
twenty-four monthly buckets, with the devaluation date marked in the output.
**Both rungs are reported whatever they show.** They are fixed here so that
choosing between them afterwards is not available.

**Three comparisons, not a group mean.** `oficial–informal`, the headline treated
pair, against each of `informal–mep`, `informal–ccl` and `mep–ccl`. Collapsing
the two groups to their means is the aggregation failure `MEASUREMENT.md` §3
exists for, and it would hide heterogeneity across the three controls.

**The shared leg is a registered feature of the comparison, not an oversight.**
The first two controls share the `informal` leg with the treated pair, so the two
series are mechanically correlated and their trends are pushed **towards each
other**, which makes this criterion **easier** to pass. That is the direction
unfavourable to the claim. `mep–ccl` shares no leg with the treated pair and is
the cleanest of the three; it is also the flattest in B5-8, at `0.999`.

### 6A.4 The band

```
        | slope_treated − slope_control | × H
       ───────────────────────────────────────────  ≤  1/4
        rms_pre(treated) − rms_post(treated)
```

`H` is the post-window length in the slope's own time unit, twelve months. The
reading is direct: **a linear trend already present before the intervention may
account for at most a quarter of the change the intervention is credited with.**

The `1/4` is the factor of four this stage already uses for signal over noise in
B5-3 and B5-6, and that B3-3 used before it. Its value carries no independent
meaning; what it carries is that one discipline is applied in every place a
magnitude has to clear something.

The band is anchored to the effect being explained rather than to the calibration
floor or to machine precision, per `MEASUREMENT.md` rule 6. The denominator is
the quantity under test, which is what makes the ratio the object of interest;
the threshold is the fixed number.

### 6A.5 Direction is separated, and both directions are fixed now

- **Damaging direction**, the treated pair already converging faster than the
  control before the intervention: the band above applies.
- **Conservative direction**, the treated pair diverging before the intervention:
  reported with its magnitude and sign, **no band**, because a trend running away
  from the result cannot manufacture the result. It can only make it harder to
  produce.

Both readings are fixed here so that neither becomes available as an
interpretation chosen after the sign is known.

### 6A.6 The gate, and what a failure does

**B5-14 refuses to start if B5-8 did not pass.** The denominator is B5-8's
collapse, and a criterion whose comparison side is empty must fail and print
`vacuous` rather than return a number (`PROJECT_PLAN.md` §11.11 rule 1). This is
expressed as a read of `results/b5_squares.json`, the same way `b5_squares.py`
reads the calibration arm rather than recomputing it.

**If B5-14 fails**, B5-8's collapse ratio is reported as **confounded with a
pre-existing trend**, in the headline and not in a footnote. It is not repaired.

### 6A.7 What B5-14 does and does not settle

It bears on **B5-8**: it removes, or fails to remove, one named alternative
reading of B5-8's collapse.

**It does not by itself repair B5-12.** B5-12 is unevaluated for two reasons that
live in the post-window and in retrieval: MEP's and CCL's second treatment in
September 2025 (§8.1), and the absence of the P2P class (§8.2). A pre-window
trend result speaks to neither, so passing B5-14 does not convert B5-12 from
unevaluated to identified. If a control whose eligibility is untouched across the
whole post-window is later retrieved, B5-12 becomes reachable again, and B5-14's
result would then be one of its inputs rather than a substitute for it.

---

## 6B. B5-15, written after B5-14 failed, and the disclosure that goes with it

**B5-14 failed.** On the primary rung all three comparisons are in the damaging
direction and the linear pre-trend, extrapolated across the post-window, accounts
for 0.77 to 0.90 of the collapse against a band of 0.25. The second rung fails
harder. `results/b5_parallel_trends.json` carries the numbers.

**And the registered output says why.** §6A.3 required the bucket series to be
written into the record, and it is not trend-stationary:

```
bucket   1      3      8     11     12          (treated, oficial–informal)
       0.314  0.814  0.168  0.274  0.387
```

The series rises to a peak in the bucket covering 13 June to 13 July 2024, falls
to a trough in the bucket covering 12 November to 12 December 2024, and **rises
again to 0.387 in the final bucket before the intervention**. A straight line
through that has a negative slope because the peak sits in the first half, and
extrapolating that line is not a description of anything. So B5-14 conflated two
questions, *were the pairs already converging* and *does a linear trend describe
this pre-window*, and what it detected is the second.

**B5-14's verdict stands and is not revised.** Reading which of the two failed is
reading the output; it is not a repair, and §8's row for B5-14 is unchanged.

### 6B.1 What B5-15 asks, and why it needs no threshold

The question B5-14 could not answer survives: **on the eve of the intervention,
was the treated pair's premium still outside the range it occupied afterwards, in
a way the control pairs were not?** That can be asked of the final pre-window
bucket directly, which requires no extrapolation and so is untouched by the hump.

Two legs, and **neither contains a threshold**:

```
(a)  last_pre(treated)   >   max( post buckets, treated )

(b)  ratio(treated)  >  ratio(c)   for every control pair c,
     where  ratio(p) = last_pre(p) / mean(post buckets, p)
```

Post buckets are the twelve equal-width buckets of `POST_WINDOW`, the same width
as the primary rung's. **Both legs must hold.**

There is no number in either leg that could be moved. That matters here more than
usual, and §6B.3 says why.

### 6B.2 Leg (a) is load-bearing and leg (b) corroborates

**Leg (a) lives entirely inside the treated pair.** It compares one date range
against another date range of the same series, so no cross-pair contamination can
reach it.

**Leg (b) carries a disclosed bias in the unfavourable direction.** §8.1 records
that MEP's and CCL's cross-restriction was reimposed in September 2025, inside
the post-window, which widens premia containing them. A wider control post-window
makes `ratio(c)` smaller and therefore makes leg (b) **easier** to satisfy. How
much of leg (b)'s margin comes from that cannot be separated with what is
retrieved, which is the same limit §8.1 states for B5-8. So leg (b) is reported
as corroboration and the claim rests on leg (a).

### 6B.3 The disclosure. What was known, and what could not have been tuned

**This section was written after B5-14 failed, and I had already seen the
quantities it tests.** The final pre-window bucket, `0.387`; the treated pair's
post-window maximum, `0.080`; and all four ratios, `8.21` for the treated pair
against `0.84`, `0.52` and `0.22` for the controls. **That B5-15 passes was known
before B5-15 was written.** Stating this at criterion level rather than in a
footnote is the point of the section.

What follows from that, and what does not:

- **Not tunable.** Both legs are strict comparisons. There is no band, no
  fraction and no cutoff, so there exists no parameter that could have been slid
  to convert a failure into a pass. The margins are reported, not tested against.
- **A choice was made**, and it is the estimator: the final pre-window bucket
  rather than the pre-window average. That choice is not free-floating; it is
  forced by B5-14's own result, which established that the pre-window average is
  contaminated by a mid-window peak. A reader who thinks a result reached this
  way is worth less than one reached before the data arrived is right, and the
  ordering is recorded here so that judgement is available to them.
- **B5-15 does not inherit B5-8's status.** It is a separate statement about the
  edge of the window and it does not convert B5-14 from failed to passed, does
  not remove §8's consequence for B5-8, and does not repair B5-12.

### 6B.4 Vacuity and failure

**Vacuous** if the final pre-window bucket did not survive §6A.3's date filter, or
if fewer than `MIN_BUCKET_SHARE` of the post buckets did, for any pair the
comparison needs. `PROJECT_PLAN.md` §11.11 rule 1: it then fails and prints
`vacuous` rather than returning a number.

**If leg (a) fails**, the premium was already inside its post-intervention range
before the intervention, and B5-8's collapse is a window artefact. That would be
the strongest single result against this stage and it is reported as such.

**If leg (b) fails while leg (a) holds**, the treated pair's edge behaviour is not
distinguishable from a control's, and B5-15 is reported as passing neither, with
the split stated.

---

## 7. Filters and registered constants, fixed here

Nothing in this table may be changed after retrieval. Changes are recorded in
§11 with the reason and **in bold**, per `b2_measurement.md` §10's convention.

| constant | value | why this one |
|---|---|---|
| **window** | `2019-09-01` to `2026-06-30` | starts the day exchange controls were reimposed after the 2019 PASO crash, so the eligibility regime begins with the window rather than inside it |
| **intervention date** | `2025-04-14` | the cepo removal; the USD 200 monthly cap ended and individuals could buy at the official rate for the first time in six years |
| **pre-window** | `2024-04-14` – `2025-04-13` | 365 days, symmetric |
| **post-window** | `2025-04-15` – `2026-04-14` | 365 days, symmetric. The intervention date itself is in neither |
| **collapse band, index** | post ≤ `1/3` · pre | B5-8 |
| **persistence band, friction** | post ≥ `2/3` · pre | B5-8, registered separately because it is a separate claim |
| **control band** | post ≥ `2/3` · pre | B5-9 |
| **signal / noise** | `> 4` | B5-6, the same factor as B3-3 |
| ~~**aliasing** last-digit agreement on `> 0.80` of days ⇒ `vacuous`~~ | **corrected**: the test is on **bytes**, not values | B5-4. The old rule would have killed the arm §4.4 is built on |
| ~~**zero arm** Ámbito against argentinadatos `mayorista`~~ | **withdrawn**: argentinadatos' `mayorista` freezes, 71-day runs, flat through the December 2023 devaluation | §4.4 |
| **calibration arm** | Ámbito `dolar/mayorista` against **BCRA A 3500** | §4.4b |
| **systematic bound** | median deviation `≤ 0.02` | §4.4b, derived from `2·log(10) = 4.61` |
| **partial bound** | no single date `> 0.5` | §4.4b, same derivation |
| **jump threshold** | one-day `\|Δ log mid\| > 0.10` | B5-10. Its **only** job is to populate a list |
| **within-day collapse** | the row whose mid is the date's **median** mid, lower median on ties | §3.5, registered after retrieval and before any headline |
| **maximum gap** | `7` days; beyond it, a gap is recorded and the chain resets | §3.6, same occasion |
| **pre-flight correlation** | `\|ρ\| ≤ 0.5` | B5-11 |
| **DiD control pair** | `P2P` against `blue` | B5-12. A class pair, not another country; see B5-12 for why the outcome is undefined abroad |
| **robustness ladder** | `±365` primary, `±180`, `±90`, all three reported | B5-12, fixed before any estimate exists |
| **parallel-trends band** | slope difference indistinguishable from zero over the eight pre-quarters | B5-13; failing it makes B5-12 uninterpretable |
| **pre-trend share** | `|Δslope| · H / (rms_pre − rms_post)_treated ≤ 1/4`, damaging direction only | B5-14, §6A.4. Registered after retrieval, before any slope was computed |
| **pre-trend buckets** | calendar month; primary rung `PRE_WINDOW` (12 buckets), second rung the eight pre-quarters (24 buckets), **both reported** | B5-14, §6A.3. The eight-quarter rung encloses the December 2023 devaluation and is the second rung for that reason |
| **pre-trend comparisons** | `oficial–informal` against each of `informal–mep`, `informal–ccl`, `mep–ccl`; no group mean | B5-14, §6A.3 |
| **edge-of-window legs** | **no threshold in either leg.** (a) `last_pre(treated) > max(post buckets, treated)`; (b) `ratio(treated) > ratio(c)` for all three controls | B5-15, §6B.1. Written after B5-14 failed and after I had seen the quantities; §6B.3 is the disclosure |
| **post buckets** | twelve equal-width buckets of `POST_WINDOW`, the primary rung's width | B5-15, §6B.1 |
| **quoted increment** | `0.01` ARS for two-decimal series, `1` ARS for whole-peso series, converted to logs at the prevailing level | the tolerance for B5-3 and B5-5 |
| ~~**known-answer constant** `1.30` throughout~~ | **withdrawn**, see §5 | the window opens 2019-09-01 and spans three plateaux; the multiplier is **reported per day and its step dates read off the data**, not asserted |
| **zero-arm independence** | different **formats**, not different sources; byte-identical payloads fail | §4.4, §4.5 |

**Row filters.** A date enters the analysis only if **every** class required by
the criterion under evaluation has a quote on that date. Missingness is reported
per arm and per class, never imputed, never forward-filled. Forward-filling a
quote across a gap manufactures a day on which two classes agreed, which is the
quantity in dispute.

**Weekends and holidays** are excluded by the requirement above rather than by a
calendar: the official leg simply has no quote. The blue and P2P markets do
quote on some non-business days, and those days drop out of any pair that
includes an official leg while remaining available to pairs that do not. **The
resulting date sets differ across pairs, and every reported number states which
date set it was computed on.**

---

## 8. Falsification

| if | then |
|---|---|
| **B5-1 or B5-2 fails** | the machinery is wrong; nothing else may be read |
| **B5-5 fails**: the multiplier drifts, or a plateau matches no regulated combination | **a source audit failure, not a pipeline failure.** The publisher is not doing what it appears to do, and every series taken from it is in question, which for Ámbito means `blue`, `mep` and `ccl`. Reported at the top of `RESULTS.md` |
| **B5-4 finds the two zero-arm payloads byte-identical** | the arm is one file read twice. `vacuous`, fails, and the next arm in §4.4's order is tried. If none survives, **no headline is reported** |
| **B5-4 declares the primary zero arm vacuous and §4.3's fallback is unavailable** | the stage has no zero calibration and **reports no headline**. Registered here so it cannot be renegotiated with a number already on the screen |
| **B5-7 fails** | this carrier has no measurable agent index. The replication half of the stage is negative and is reported as such |
| **B5-8's first half fails**: the index part does not collapse | the intervention did not remove the thing the framework says generates the squares. **This is the cleanest way this stage can be wrong**, and it is reported at the top of `RESULTS.md`, not in a footnote |
| **B5-8's second half fails**: the friction collapses too | the separation of `b4` §5.1 is not doing work on this carrier. The stage says so and the differential prediction is withdrawn |
| **B5-9 fails**: the control class collapses too | something moved every rate at once. B5-8's arithmetic may still pass, but its causal reading does not, and the causal reading is the point |
| **B5-11 fails** | B5-8 is uninterpretable on this carrier, whatever it returns |
| **B5-13 fails**: the two pairs were already diverging before the intervention | B5-12 is not identified and is reported as uninterpretable. The stage falls back to B5-8 and B5-9 as separate before-after statements and says so in the headline |
| **B5-14 fails**: the treated pair was already converging faster than a control before the intervention | B5-8's collapse ratio is reported as **confounded with a pre-existing trend**, in the headline and not in a footnote, and it is not repaired. §6A.6. **This is what happened**; §6B opens with the numbers |
| **B5-15 leg (a) fails**: the premium was already inside its post-intervention range before the intervention | B5-8's collapse is a window artefact. The strongest single result against this stage, reported as such. §6B.4 |
| **B5-15 leg (b) fails** while leg (a) holds | the treated pair's edge behaviour is not distinguishable from a control's; B5-15 passes neither leg's claim and the split is stated. §6B.4 |
| **the P2P leg is never retrieved** | **B5-12 does not run**, and MEP and CCL may not stand in for it. See §8.1 for why they may serve B5-8 and not B5-12, which is a distinction this document had to make after B5-8 was rewritten |
| **B5-10's two headlines differ materially** | reported as a finding about the series, not repaired |

**The failure mode this stage is most exposed to** is that the convergence of
April 2025 was a level convergence produced by the devaluation rather than an
index collapse produced by the deleted rule. B5-9 is the criterion that
separates them, and it is the reason P2P is in the design at all.

### 8.1 Why MEP and CCL are controls for B5-8 and not for B5-12

**These two statements looked contradictory and are not, but the reason has to be
written down.** B5-8's rewrite (§3.2b) uses MEP and CCL in the control group;
this section's table refuses them as B5-12's control unit.

The two criteria ask for different things.

- **B5-8 asks whether the group the deleted rule did not apply to moved.** The
  rule deleted on 14 April 2025 was oficial's USD 200 cap. It did not apply to
  the pairs that contain no oficial leg, so those pairs are untreated **by that
  rule**, which is what the comparison needs.
- **B5-12 is a difference in differences, and it attributes the gap between the
  two groups to the intervention.** That requires a control whose eligibility was
  untouched **by the whole intervention**, not only by the one clause. MEP's and
  CCL's cross-restriction was removed on the intervention date and reimposed in
  September 2025, inside the post-window, so they were treated twice.

**And one bias must be stated rather than left for a reader to find.** The
September re-imposition would tend to *re-widen* premia involving MEP and CCL.
In B5-8 that pushes the control group **towards** the outcome the criterion wants
to see, which is the unfavourable direction for the claim. How much of
`MEP–CCL`'s `0.999` and `blue–CCL`'s `1.050` comes from that cannot be separated
with what is retrieved.

`informal` is the only class whose access was never rule-bound at all, which is
why `oficial–informal` remains the headline pair — but `informal` cannot form a
control pair on its own, since every pair containing it and not oficial also
contains MEP or CCL.

### 8.2 The four criteria that do not run, and why each is a conclusion

**B5-9, B5-11, B5-12 and B5-13 are not deferred. Their sources were looked for,
audited, and found not to exist.** Recorded here at criterion level so that a
later reader does not spend a week rediscovering it.

| criterion | needs | outcome |
|---|---|---|
| **B5-11** | the **friction column** | no source, §3.2a. Three candidates audited, all three failed. Nothing to do with P2P |
| **B5-9** | the **P2P class** | the only free daily history is argentinadatos' `cripto`, audited in `experiments/b5_p2p.py` and **rejected**: longest frozen run **47 days** against the registered `21` |
| **B5-12** | the P2P class | same |
| **B5-13** | the P2P class | same |

**On the 47 days, and why the threshold did not move.** It sits between the 13
days a sound series showed (`tarjeta`) and the 71 a broken one did (`mayorista`),
so it is a grey reading rather than an obvious one. The threshold was registered
at `21` **before** the candidate was retrieved, from those two anchors, and
`tests/test_b5_squares.py` pins it for exactly this moment: *a threshold chosen
after seeing the candidate would be choosing to admit it.*

**And the grey is precisely what a referee would settle**, which is the second
half of the answer: `cripto` is the one series in this stage that **cannot have
one** (§9.4). No central bank for a crypto market, and CriptoYa publishes bid and
ask across thirty-six venues for the current moment only. A borderline series with
no way to arbitrate it is not a control.

**What is lost, stated plainly.** B5-12's difference in differences and B5-13's
parallel-trends test are the strongest causal form this stage could have taken.
Without them the stage rests on B5-8's treated-versus-control comparison across
pairs, which shares the same logic and carries §8.1's caveat that MEP and CCL
were touched by a different clause of the same intervention.

**Part of B5-13's function is recovered and part is not, and the split matters.**
`B5-14` (§6A) asks B5-13's question of the control pairs that do exist, and §6A.2
gives the reason those pairs are admissible for a pre-window trend test when
§8.1 refuses them as B5-12's control unit: §8.1's objection is entirely about the
post-window. So the pre-trend check is recovered. **B5-12 itself is not**, and
B5-14 does not make it so (§6A.7). A reader arriving here from the table above
should follow that pointer rather than conclude the parallel-trends question went
unasked.

**MEP and CCL may not be promoted into the P2P slot** to make B5-12 run. §8.1
gives the reason: B5-12 attributes its estimate to the intervention, and a
control touched twice by that intervention cannot carry the attribution.

### 8.3 "The market simply got more liquid", and what actually bears on it

**The objection put to this stage most often is that the premium collapsed
because the market became more liquid rather than because an eligibility rule was
deleted.** It arrives in two forms and they are not equally serious. Separating
them is most of the answer.

**The first form is answered by algebra and needs no data.** B4 §5.1 splits a
two-way edge into

```
S − S'  =  2 · log( mid_b / mid_a )              the headline
S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)   the friction
```

so the bid and ask **cancel out of the headline by construction**. What collapsed
is the ratio of two *eligibility classes'* mid quotes; a bid-ask spread is a cost
*within* one class. Those are different objects, and a market-wide narrowing of
spreads cannot move the first. This is also why §3.2a's missing friction column,
which is a real and disclosed loss, is not the loss this particular objection
needs it to be: `S + S'` was never the quantity that ruled out a liquidity story.

**The second form does reach the headline, and §8 already names it as the failure
mode this stage is most exposed to.** If the blue rate carried a premium for its
own thinness, or if the April 2025 convergence was a level convergence produced
by the devaluation, then something other than eligibility moved the gap. Nothing
in the algebra excludes that.

**What bears on it is the control group, computed on the same quotes in the same
units.** A force acting on the whole market compresses every premium, not only
the one containing the treated class. Over the same two windows:

| pair | rms pre | rms post | post / pre |
|---|---|---|---|
| `oficial–informal`, treated | 0.4996 | 0.0508 | **0.102** |
| `informal–mep` | 0.0651 | 0.0463 | 0.712 |
| `informal–ccl` | 0.0663 | 0.0696 | 1.050 |
| `mep–ccl` | 0.0424 | 0.0423 | **0.999** |

`mep–ccl` moved by one part in a thousand across a year containing the
intervention. B5-15's leg (a) is the second thing that bears on it, from the
opposite direction and entirely inside the treated pair: on the eve of the
intervention the premium stood 4.8 times above the highest level it reached in
the whole following year, so whatever was closing the gap had not closed it.

**Background citations exist and they are background.** BCRA publishes the
balance cambiario and its statistical annex monthly back to 2003, and they
describe what the market did around the intervention: volumes, the behaviour of
household dollar purchases, the range the peso traded in. `data/SOURCES.md`
lists them under a heading that says what they are for. They may be cited in a
discussion of the market and they may not be read by a criterion, and the reason
to keep that line sharp is that the strongest evidence against the liquidity
story is already in the table above, in this stage's own measurements. A
paragraph of context does not need to carry weight it would carry badly.

### 9.1 The `H⁰` half is not here, and the reason is not fixable by a bigger sample

Theorem 5 gives the orphan currency a precise statement: where the graph is not
strongly connected, the sub-potential polytope is unbounded in the sink
component, so the position is **not priced** rather than badly priced, and it is
`H⁰`.

**This stage does not measure that, and no single cross-section can.** The
observable for `H⁰` is **the absence of a quote**, and absence is
indistinguishable in data from an incomplete dataset. The only way to fill it is
prohibited by `b4` §5.2: another class's quote, a lagged quote, or a nominal
official rate at which no transaction is possible fills the gap with exactly the
quantity in dispute.

**Changing the carrier does not help**, because the limitation is structural
rather than a property of Argentina. The only form in which the claim becomes
testable is a directed edge that **appears or disappears on a known date**;
Argentina's export surrender requirement is a standing regulation with no such
event inside this window. The disposition and the candidate carrier are in
`PROJECT_PLAN.md` §14.3.1 and §14.4.

**Consequence for how this stage is written up**: every reading it produces lives
in the **bidirectional** half of the world, and the paper says so rather than
implying coverage it does not have (`PROJECT_PLAN.md` §12.11).

### 9.2 The connectivity index `C` is dropped rather than faked

The original orphan-currency concept had a `C → D` half, with `C` a connectivity
index that `PROJECT_PLAN.md` §9.6 requires to come from **outside price data**.

On one country there is no `C` worth reporting. AREAER's FARI is annual, which
gives a handful of points, and the obvious alternative — Ilzetzki–Reinhart–Rogoff's
capital-control index — **is disqualified rather than merely thin**: its
construction includes whether a country has an active parallel market, which is
the thing `C` is supposed to predict. That is §9.6's circularity exactly.

So §9.6 is satisfied **vacuously**, and `C → D` is dropped from this stage
rather than constructed from something that would not survive review.

### 9.3 One country is one country

The result reads: *the square structure of loop A appears in a second, unrelated
market, and it collapses when the eligibility rule that generates it is deleted.*

It does not read: *therefore this holds across emerging markets.*
`a3b_initial_construction.md` §9 is the model for how to write that boundary.

### 9.4 Four smaller limits, stated so they are not discovered later

**Provenance is mixed and one leg is a newspaper.** The oficial leg comes from
the central bank; blue, MEP, CCL and P2P come from Ámbito and community APIs.
This is a step down from every prior stage in this project, and it belongs at
the top of the write-up rather than in a footnote — the same admission
`b3_slice_availability.md` §4 makes about a derived series.

**The friction column exists for one pair only.** MEP, CCL and P2P have no native
two-sided quote (§3.3), so `S + S'` is computable only for oficial–blue. B5-8's
second half therefore rests on a single pair.

**No volume, so no volume weighting.** Four of the five classes publish no
turnover. Every number is one day, one observation.

**Attribution is out of scope.** As with B2, this stage can show that terms
differ by who the agent is, and cannot say which attribute of the agent carries
it. Non-integrability requires a non-zero cycle sum; it does not require the
cycle sum to be explained.

---

## 10. Retrieval, and the rules the fetcher must satisfy

**Retrieved data is treated as non-regenerable in this repository.** The
fetcher is bound by the following, each of which traces to a specific incident.

**Resumable, and truncation must be detected rather than silently read.** The
fetcher writes a sentinel and a manifest, and a file missing the sentinel is
classified `legacy` rather than `bad`: a missing marker is the script's own
fault and is not evidence about the file. `fetch_hmda.py` once classified every
already-downloaded file as truncated because it checked a sentinel it never
wrote, which would have renamed 408 files and re-downloaded for hours
(`PROJECT_PLAN.md` §11.3).

**Two hashes, not one.** The manifest records **both** the hash of the source
bytes and the hash of the written file, because the written file carries a
sentinel line the source does not. `fetch_cip.py`'s first version compared the
source hash against the written file and therefore warned on every run
(`PROJECT_PLAN.md` §11.11) — a guard that cries every time is exactly as useless
as one that never cries, because the reader's response to both is to stop
looking.

**Parse assertions on every row.** Dates are `DD/MM/YYYY` and **the decimal
separator is a comma**. The parser asserts the separator convention and asserts
that parsed levels fall in a registered plausibility band, and it fails loudly
rather than producing numbers a hundred times too large.

**Anomalies are recorded and never repaired.** A row whose one-day mid change
exceeds §7's threshold gets a `DataAnomaly` entry in the manifest and **its value
is not changed**. Substituting a value from another series silently changes what
the series is, and the change is invisible downstream; **this repository does
not repair**, and the rule applies to values as much as to files. The known instance is `dolar/oficial` on
23 April 2025, reading `1251.44 / 1333.24` between neighbours near `1100`, which
may be a composition change, a bad row, or a real liquidity event three weeks
into a new float. **A jump filter cannot tell those apart, and in this window it
will fire on real moves**, so the threshold's only job is to populate the list
that B5-10 computes both ways.

**No deletion, ever.** Superseded files are renamed with an `.expired` suffix and
left in place. When the loader must ignore something, the loader is changed, not
the filesystem — the pattern `b2_loop_a.py`'s `VALID_NAME` established after the
incident recorded in `PROJECT_PLAN.md` §11.1.

---

## 11. Changelog

Any change to §7 after retrieval is recorded here, in bold, with the date and the
reason.

### 2026-08-11, after B5-8 ran. One addition: B5-14

**A criterion was added, not changed.** §7 gained three rows, all of them
`B5-14`'s, and nothing already in §7 was touched. The addition is disclosed here
because its timing differs from every other criterion in the document: §6 was
fixed before any Argentine series existed on disk, and this one was written after
retrieval, after the P2P audit returned `reject`, and after B5-8 had run.

**Why it was added rather than left out.** B5-8's pre-flight, `B5-11`, does not
run: it needs the friction column, which has no source. `B5-13` asked the
question `B5-11` no longer could, and it does not run either, because its control
unit was the rejected P2P class. That left B5-8 with **no pre-flight at all**,
and the alternative reading it was unguarded against is specific and nameable:
that the treated and control pairs were already diverging before 14 April 2025.
B5-14 asks B5-13's question of the control pairs that do exist. §6A.2 gives the
reason those pairs are admissible for a pre-window trend test and not as B5-12's
control unit.

**What was known when it was written** is recorded at the head of §6A, together
with what was not: no monthly bucket series and no slope had been computed, and
the code that computes them did not exist. The condition attached to a criterion
registered at this point is that its result is reported whatever it shows, and
both directions and both window rungs are fixed in §6A before the run.

**What it does not do**, stated here as well as in §6A.7 because this is the
misreading most available to a later reader: B5-14 bears on B5-8 and **does not
by itself repair B5-12**, whose two obstacles both live in the post-window and in
retrieval.

### 2026-08-11, after B5-14 failed. One addition: B5-15

**B5-14 failed and B5-15 was written in response.** The ordering is the whole
disclosure and it is recorded in three places: here, at §6B's head with the
failing numbers, and at §6B.3 at criterion level.

**What was already visible when B5-15 was written**: the treated pair's final
pre-window bucket `0.387`, its post-window maximum `0.080`, and all four
`last_pre / post_mean` ratios. **That B5-15 passes was known before it was
written.**

**What that does and does not license.** Both of B5-15's legs are strict
comparisons containing no band, fraction or cutoff, so no parameter existed that
could have been slid to turn a failure into a pass. The choice that was made is
the estimator, the final pre-window bucket in place of the pre-window average,
and it is forced by B5-14's own finding that the average is contaminated by a
mid-window peak. §6B.3 states both halves so that a reader can discount the
result by however much that ordering is worth to them.

**B5-14's verdict is not revised**, §8's consequence for B5-8 stands, and B5-15
does not reach B5-12.

### 2026-08-11, first retrieval. Four entries, and no headline has been computed

The first run of `data/fetch_ambito.py` retrieved 5,248 rows across three of the
four series. **No cycle sum, no premium and no criterion has been evaluated on
any of it.** The entries below are therefore registrations made before results
exist, not revisions made after seeing one — which is the distinction that
matters, and the reason the retrieval was run before the criteria code was
written rather than after.

**1. The CCL endpoint path was wrong, and the way it was wrong is the lesson.**
`b5_orphan_availability.md` §7.1 listed `dolarrava/ccl` with the parenthetical
"(same shape)". It 404s on every half-year. The working path is
**`dolarrava/cl`**, verified 2026-08-11 against a ten-day range. The
parenthetical was the tell: that row was reasoned from `dolarrava/mep` rather
than requested. §13.5 of `PROJECT_PLAN.md` requires an availability check before
opening a stage; this is the narrower version of the same rule — **an endpoint
that was inferred is not a verified endpoint**, and the availability document's
table should have said so.

**2. §3.5 added: the endpoint returns intraday snapshots, not a daily series.**
Not reported anywhere before the data arrived. Material to B5-8's post-window
reading, so the collapse rule is registered here before any headline exists.

**3. §3.6 added: a gap in the series is not a one-day change.** Found because a
failed chunk produced one.

**4. Chunking changed from calendar years to half-years, then to half-years with
adaptive bisection.** A full year of `dolarrava/mep` returned HTTP 500 while each
half of that year returned normally, so half-years became the unit. The second
run then failed on `2025H2` for **both** `dolarrava` series, deterministically,
three retries each. Bisected:

| range | result |
|---|---|
| `2025-08-01` – `2025-08-07` | fine |
| `2025-08-12` – `2025-08-13` | fine |
| `2025-08-14` – `2025-08-15` | fine |
| **`2025-08-13` – `2025-08-14`** | **500** |
| any range containing that pair | **500** |

`dolarrava/mep` fails identically; both are the same Rava backend. **This is a
deterministic server-side fault on a date boundary, not throttling**: throttling
answers 429, does not reproduce on exactly the same range, and would not let the
two halves through while refusing their union.

**So no fixed chunk size is safe** — any window wider than a day can straddle a
poisoned boundary. The fetcher now bisects on a persistent 5xx down to single
days, storing each successful sub-range as its own file, still one verbatim
response per file. **A single day that still fails is recorded as
`unretrievable` and left absent**; there is no substitute for it that would not
be an invention, and this repository's prohibition on repair covers values as
well as files.

Server errors are retried with backoff and **client errors are not**, since a 404
is the server answering rather than failing. The whole-year files from the first
run are kept in place and reported by `--check` as superseded, since this
repository does not delete.

**What this costs the stage, stated rather than discovered later**: any day the
endpoint will not serve is a day missing from MEP and CCL. Those two enter the
headline only, not the friction column, and §7's row filter already requires
every class a criterion needs to have a quote on a date. So the effect is a
smaller date set for pairs involving MEP or CCL, reported per arm under §7, and
**not** a gap filled from somewhere else.

**Two guard bugs were fixed at the same time, and both are the same bug.** The
anomaly scan ran on uncollapsed rows and reported "one-day changes" whose
previous date equalled their own date; it also compared across a year-long hole
and called that a one-day change. Both are `PROJECT_PLAN.md` §11.11 rule 2 — a
guard must compare the quantity that is actually reported — and both were
invisible until real data arrived. Recorded here rather than only in the code,
because a guard that was wrong once is a fact about this stage.


---

## 12. How many of B5's squares are independent, measured 2026-08-16

This section exists because the script that produced these numbers has been
retired. It was a one-off measurement, it has already done its work, and a
measurement whose conclusion has been absorbed into a rule should not stay on
disk pretending to be a stage. Everything it found is below, so that an auditor
of B5 does not need it.

### 12.1 What was asked

An outside proposal argued that an event-study design over payment topology
would beat the project's existing cross-country panel, on the grounds that
"20 events x 500,000 transactions" is more power than "30 countries". The power
arithmetic behind that claim multiplies events by pairs, taking 50 pairs per
event.

Two things were unmeasured in it. The first is how many of those pairs are
independent. The second is how correlated the ones that are left turn out to be.
B5 is the only stage in this project that already has both an event and a set of
squares over the same positions, so both were measured here, on records already
in this repository, with no new retrieval.

### 12.2 The structural bound, which is arithmetic rather than an estimate

B5 has **four** classes: `ccl`, `informal`, `mep`, `oficial`. A complete graph on
four positions carries **six** pairwise squares, and the number of independent
cycles is

    b1 = E - V + 1 = 6 - 4 + 1 = 3

So at most **three** of those six squares are independent. **The count of
independent comparisons is set by the number of positions, not by the number of
squares that can be written down.** Writing more squares over the same four
positions adds no independent content, and any power calculation that multiplies
by the square count rather than by `b1` is inflated by construction.

This is not a fact about the proposal. It is a fact about B5, and it bounds what
this stage's own criteria can carry: **the six pairs in section 2 rest on three
independent cycles.** Section 3.2's prohibition on what may be reported is the
same constraint arriving from the directed-theorem side.

The project already has the machinery for this bound: B1H-5 computes
`dim H1(G x H) = b1(G) + b1(H)` and verifies it on six shapes against exact
integer agreement.

### 12.3 The correlation, measured, as a cross-check on the bound

Measured on the **control pairs only** (`informal-ccl`, `informal-mep`,
`mep-ccl`), because those are untreated and therefore pure co-movement with no
treatment effect in them. Input was the bucket-level `rms_per_bucket` series
from `results/b5_parallel_trends.json`, one pass per registered window. Pairwise
correlations were averaged by Fisher-z transform, and turned into an effective
count by the standard intra-cluster deflation `N_eff = N / (1 + (N-1) * rho)`.

| window | pair | pair | corr | buckets |
|---|---|---|---|---|
| `primary_rung` (2024-04-14 to 2025-04-13) | `informal-ccl` | `informal-mep` | +0.5985 | 12 |
| `primary_rung` | `informal-ccl` | `mep-ccl` | +0.3087 | 12 |
| `primary_rung` | `informal-mep` | `mep-ccl` | -0.1986 | 12 |
| `second_rung` (2023-04-14 to 2025-04-13) | `informal-ccl` | `informal-mep` | +0.3653 | 24 |
| `second_rung` | `informal-ccl` | `mep-ccl` | +0.2793 | 24 |
| `second_rung` | `informal-mep` | `mep-ccl` | +0.7241 | 24 |

| window | `rho` (Fisher-z mean) | `N_eff` out of 3 nominal control pairs |
|---|---|---|
| `primary_rung` | **+0.2632** | **1.965** |
| `second_rung` | **+0.4844** | **1.524** |

**The measured 1.5 to 2.0 sits under the structural bound of 3, and the two
agree.** `b1` is what the construction permits; `rho` is what the data actually
delivers. The second never exceeded the first, which is the check that the bound
binds rather than merely being available.

Reported alongside, descriptive only, the within-group spread of the collapse
ratio `rms_post / rms_pre`:

| group | ratios | mean | sd |
|---|---|---|---|
| treated | 0.1017, 0.1096, 0.1770 | 0.1294 | 0.0414 |
| control | 0.7118, 0.9992, 1.0499 | 0.9203 | 0.1823 |

### 12.4 What this settled

Substituting the measured `rho` back into the proposal's own formula gives
roughly **73** effective units at `rho = 0.26` and roughly **41** at
`rho = 0.48`. The existing cross-country panel carries **121** independent units
at `h <= 5`. **The event design loses on N rather than winning on it**, so power
is not available as a reason to reorder the queue.

What the event design may still win on is identification, and that is a separate
argument: the panel's treatment variable is endogenous, so its 121 units are
dirty while the event design's 41 to 73 are clean. Many dirty against few clean
is a trade, and it has to be argued on identification. This section does not
argue it.

### 12.5 Three limits on the correlation half, which do not touch the bound

1. **One event cannot give a between-event variance.** What was measured is
   within-event correlation. Treating it as a general `rho` for event designs is
   an extrapolation.
2. **The three control pairs share legs** (`informal-ccl` and `informal-mep`
   share `informal`, and so on), so part of the correlation is mechanical. This
   is not a defect of B5. It is a property of any square set built over one set
   of positions, and it is the same reason `b1` bounds the count at all.
3. **The bucket series is a proxy for the per-day squares**, which are not in the
   JSON records. If the per-day series were available, `rho` would move.
   **The `b1` bound would not**, because it is arithmetic on the graph.

### 12.6 Reproduction

Both inputs, `results/b5_parallel_trends.json` and `results/b5_squares.json`, are
committed, so every number above can be recomputed from this repository with no
retrieval. The script that produced them is retired under this repository's
`.expired` convention rather than deleted, and the rule it fed now lives with the
project's other pre-run gates, where it is applied to new designs instead of
sitting beside one finished measurement.
