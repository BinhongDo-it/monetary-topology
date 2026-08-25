# B15: Bolivia, the control carrier. Pre-registration, version 1

**Registered 2026-08-19. Nothing has been downloaded.**

**That sentence is the point of this document and not an apology for it.** Every
constant, threshold, arm and criterion below is fixed while I have seen no
Bolivian number from any source. `docs/bolivia_availability.md` §6 records
that the sources were located through a tool that returns a summary of a page
rather than the page, that one such summary reported a value for a date that has
not happened, and that the reading was discarded. **So the register is closed
before the data exists locally, which is the strongest form of the discipline
this project has been trying to keep and the one B6 could not have**, because B6
was designed after its window had already been read.

Authority for the carrier and its sources is `docs/bolivia_availability.md`.
**Read its §6 before reading §3 here.** Authority for the framework is
`docs/b1_theorem.md` and `docs/b4_directed_edges.md`.

---

## 1. What this stage is for

B6 measured one controlled economy and found the same thing at every criterion:
**an edge that the law grants, that is posted, and that nobody walks.** The
finding is worth exactly as much as the answer to one question, which a reader
will ask immediately: **would this framework say that of any controlled
economy?**

**A second carrier with the same criteria and a different institutional outcome
is the answer.** B15 is that carrier. It is not a replication and it is not a
robustness check. **It is the discriminating case**, and it is chosen because on
2026-06-26 Bolivia did the thing Cuba has not done: it abandoned a fifteen-year
peg and let the official rate be computed from transactions.

**If B15 returns B6's readings, the framework's finding is about controlled
economies in general and the paper must say so.** If B15 returns the opposite
readings on the same criteria, the finding is about the specific institution B6
identified. **Either outcome is publishable and the stage is registered to be
indifferent between them.** `bolivia_availability.md` §4.4 already removed the
first version of §1's outcome table for pre-committing to the second answer.

## 2. The instrument, and what it can and cannot say

### 2.1 Both sides, both legs

**The limit that governs all of B6-B does not govern here.**
`b6b_eltoque_prereg.md` §3.4 registers the one-sided rule: elTOQUE publishes one
median per instrument, so substituting it bounds every directed weight from
above, so a non-positive cycle can be established and **a positive one never
can**. B6-B carries an index part and no friction part for that reason alone.

Bolivia publishes a bid and an ask on both legs:

| leg | bid | ask | source |
|---|---|---|---|
| official | `TCO` | `TCO + 0.10` by statute | BCB, and `official_buy`/`official_sell` |
| parallel | `blue_buy` | `blue_sell` | `api.dolarbluebolivia.click/v1/chart/all.csv` |

**So B15 can carry an `H¹` arm with friction on both legs and can certify a
positive cycle if one is there.** This is the single largest capability
difference between the carriers and §5's arms are organised around it.

### 2.2 One limit that does govern, registered so it cannot be forgotten

**`paralelo.bo` publishes a median and only a median in history.**
`/api/v1/historical.csv` has the header `date,median_bob_per_usd`. Its live
endpoint gives compra, venta and spread; its archive does not.

**So paralelo.bo is subject to exactly the elTOQUE limit**, and mixing it into a
friction computation would reintroduce the one-sided rule silently, on one
series, while the register says the stage is free of it.

**Guard `no_one_sided_in_friction`** (§6.3): a criterion that computes a spread,
a round trip or a cycle weight may read only from a source that publishes both
sides on the day in question. paralelo.bo enters as an index series and as an
independent check on the level, and enters no friction quantity.

### 2.3 What the sale side is, and why it is not an observation

**`RD 88/2026` Art. 5.I builds the official rate out of purchases only**, and the
BCB's microdata endpoint follows: it serves rate, count and amount per bank per
tier, for compra, and for nothing else. Art. 6 then defines the ask as
`TCO + 0.10` and forbids exceeding it.

**So on the official leg the bid is a transacted price and the ask is an
arithmetic consequence of it.** No transaction record for the ask exists,
because the regulation does not collect one.

**This is registered as a property of the instrument, before any reading**,
because it is the thing most likely to be misread later as a result. **A finding
that the official ask does not clear cannot be drawn from the absence of a record
of it clearing.** What can be drawn is B15-7's price statistic, and §7.2 states
what would falsify it.

### 2.4 The instrument set moves

The reform changed what is published. `tco_reporte_detalle_historico.php` begins
**2026-06-26**, because the operations it reports did not exist as a reported
category before. And the `kind` column of that publisher's `oficial.csv`
is reported to carry at least `referencial` and `unificado`.

**A series whose meaning changes at the event is not a series.** §3.5 registers
the break handling and §6.2 registers the guard.

## 3. Measurement

### 3.1 Sources

Exactly as `bolivia_availability.md` §3, with the acquisition order fixed here:

| # | source | what it carries | role |
|---|---|---|---|
| S1 | `bcb.gob.bo/tiposDeCambioHistorico/xls.php?anio=YYYY` | official compra and venta, daily, to 1940 | the formal leg |
| S2 | `bcb.gob.bo/tco_reporte_detalle_historico.php` | per bank, per tier: rate, count, amount. **Compra only** | the microdata, B15-6 |
| S3 | `api.dolarbluebolivia.click/v1/chart/all.csv` | both legs, both sides, 15 minutes, from 2024-07-21 | the friction arms |
| S4 | `paralelo.bo/api/v1/historical.csv` | median only, daily, from 2024-01-01, CC-BY 4.0 | index and cross-check |
| S5 | `github.com/mauforonda/dolares` | buy, sell, official, amount; 25,627 commits | audit and reconstruction |
| S6 | ECB daily euro reference rate | the outside cross | B15-12 |

**S1 and S3 are the two the stage cannot open without.** S2 opens B15-6, S4 and
S5 open B15-11, S6 opens B15-12.

### 3.2 Window

**Registered window: 2024-07-21 to the day of the run.**

The left edge is S3's first observation and it is chosen because it is the first
day on which **both legs and both sides** exist together. S4 reaches back to
2024-01-01 with one side, which is enough to extend the index arm and not enough
to extend anything else, and §6.3's guard is what keeps the two from being mixed.

**The event sits at 2026-06-26**, which puts roughly 23 months before it and
whatever has accumulated since. B6 was designed as an event study around
2025-12-18 and could not be one, because Cuba's formal leg begins the day after
the reform. **This is the design B6 could not have** and the window is registered
to make that concrete rather than to make it flattering.

### 3.3 Time and the day boundary

`America/La_Paz` is **UTC-4 all year and observes no daylight saving**, which
removes the entire class of failure that cost B6-B a day of retrieval and five
shortened windows. **The registered convention is that a day runs 00:00:00 to
23:59:59 local, with no exceptions, and `local_span_seconds` is 86,399 on every
day in the window.** A guard asserts it rather than assuming it (§6.1), because
that assertion is cheap and the equivalent assumption in B6-B was wrong.

**`RD 88/2026` Anexo II uses 00:00 to 17:00 local for the operations that enter
the TCO**, and Art. 5.III publishes at 20:00 for the following day. Those are
properties of the official series, not of the day boundary, and they enter
B15-4 and B15-6.

### 3.4 The two date conventions, which are not the same date

**Art. 5.III: `Cada día hábil a horas 20:00 el BCB publicará en su página web el
TCO que será vigente al día siguiente`.**

So every official observation carries two dates and the annual table's column
does not say which it is. `bolivia_availability.md` §5 item 2 is the blocker;
this section registers how it is settled, **before the table is downloaded**.

**The test is decisive and needs no new source.** S3 samples the official pair
every 15 minutes. Whichever local time of day `official_sell` steps to a new
value across the whole span identifies the convention:

- steps at **20:00** local: the table's date column is the **publication** date;
- steps at **00:00** local: the column is the **vigencia** date;
- steps at neither, or at no consistent time: **B15-4 is void** and every arm
  that needs a dated official value is suspended rather than aligned by guess.

**One outside anchor is already on disk and is registered as the confirming
check.** `data/raw/bolivia/aduana_comunicado_2026-06_RM245.pdf` states
`el tipo de cambio de 6,96 Bs/USD vigente al 26/06/2026`. So the peg was
**vigente** on Friday 2026-06-26, and whichever convention B15-4 selects must
reproduce that.

**No alignment may be chosen because it makes a criterion pass.** This is
`HANDOFF` §3.2 item thirteen, which is why B6-4 is registered as a failure and
not repaired.

### 3.5 The breaks

Three dates, and they are three, which is itself worth registering:

| date | what happens |
|---|---|
| **2026-06-26** | `RM 245` and `RD 88/2026` are issued. The peg is still `vigente` this day |
| **2026-06-29** | the flexible regime takes effect, first business day |
| **2026-07-06** | the customs conversion switches from the frozen 6.96 to the running official venta |

**The registered event date is 2026-06-29**, the first day the new rate governs,
not 2026-06-26, the day the instruments are signed. `bolivia_availability.md`
§4.6 is the reason the third date exists at all and B15-9 is the arm that uses
it.

**No criterion may use a window that straddles a break without saying so.**
Guard `break_disclosure` (§6.2).

### 3.6 Assumptions

**A1 is not assumed.** `b6b_eltoque_prereg.md` §3.3's `bid <= m <= ask` has no
role here, because no median is substituted for a side anywhere in §5.
`bolivia_availability.md` §7.1 records what that cost B6 and how B6-16 partly
retired it.

**A2, registered and load-bearing.** `blue_buy` and `blue_sell` are the best
available offer on each side of one venue's book, per the publisher's stated
method, which makes them touch quotes. **A2 is that the touch is executable at a
size that is not zero.** It cannot be tested from S3 alone. It is testable from
the private per-offer endpoints the publisher documents, and that test is
registered as future work rather than as a criterion, because the endpoints
require registration and the stage is not going to depend on a key.

**A3, registered as a scope limit.** S3's parallel figures come from one venue.
`bolivia_availability.md` §3.2.4 records that every aggregator found resolves to
the same underlying P2P book, so **the parallel leg of this stage is one venue's
book and not "the parallel market"**, and §8 says so again.

## 4. Arms

**Four arms. Each names the sources it may read and the guard that stops it
reading anything else.**

| arm | reads | carries |
|---|---|---|
| **I. Integrity** | S1, S3, S5 | B15-1, B15-2 |
| **II. Typing** | S3 | B15-3, B15-4, B15-5 |
| **III. Structure** | S1, S2, S3 | B15-6, B15-7, B15-8, B15-9 |
| **IV. Calibration and referee** | S1, S3, S4, S5, S6 | B15-10, B15-11, B15-12 |

**Arms II and III are ordered and the order is not negotiable.** B15-3 and B15-4
decide which column is which side and which date is which day. **Every criterion
in arm III is undefined until both return a live verdict**, and if either is void
the arm does not run. `b4` §5.2 is the reason: imputing a direction imputes the
quantity in dispute, and here the direction is literally a column choice.

## 5. Criteria

**Twelve criteria, B15-1 to B15-12. Two of them, B15-3 and B15-4, gate the four
in arm III. Every threshold is fixed here.**

### Arm I

**B15-1. Retrieval integrity.** Every day in the window is present or recorded
absent, never filled in either direction. Two digests per response, of which the
one over the payload survives a refetch. Resume by file existence. A truncated or
corrupt file is detected and re-fetched rather than read.
**Passes if**: zero silent gaps, zero fills, and the manifest's day count equals
the window's.
**This is B6-9 transplanted** and the fetcher is written to the same contract as
`data/fetch_eltoque.py`.

**B15-2. The known-answer arm.** A set of values is written down from the live
endpoints before any criterion is computed, stored in the source module as
constants, and replayed against the archive on every run.
**Passes if**: every recorded answer is reproduced from disk, byte for byte on
the payload digest.
**This is B6-10 transplanted.** It is what catches a source that silently
revises.

### Arm II

**B15-3. The side convention, established from the data.**
`bolivia_availability.md` §3.2.1 records that the two pairs in one row of S3 run
in opposite directions: the official pair has `sell - buy = +0.10`, the blue pair
has `sell - buy < 0`. Read under one convention the informal book is crossed.

The official pair is anchored by statute: Art. 6 fixes `venta = TCO + 0.10`, so
`official_sell` is the ask and `official_buy` is the bid, and this is a check
rather than a choice.

The informal pair is decided by a single registered test: **under exactly one of
the two orientations is the book uncrossed**, meaning `ask >= bid` on a share of
observations at or above the threshold.
**Passes if**: one orientation gives an uncrossed book on **>= 99%** of
observations and the other gives it on **< 50%**.
**Void if**: both orientations clear 99%, or neither does. **Void suspends arm
III**, and no orientation is chosen by which one makes a later criterion pass.

**B15-4. The date column.** As §3.4. **Passes if**: the official value steps at a
single consistent local time across the span, that time is 20:00 or 00:00, and
the resulting convention reproduces `6,96 vigente al 26/06/2026`.
**Void otherwise**, and void suspends arm III.

**B15-5. The statutory spread is administered and constant.** Art. 6 caps the
official ask at `TCO + 0.10`. The peg era's published pair was 6.86 and 6.96,
which is the same 0.10, **so the reform did not change the spread and Art. 6 may
be codifying what was already practice.**
**Passes if**: `official_sell - official_buy` equals **0.10 exactly** on **>=
99%** of days in the window, on both sides of the event.
**This is a Theorem 6 statement.** The symmetric part of the official two-way
edge is `ω̄ = -log(1 + 0.10 / TCO)`, administratively fixed in level and
therefore shrinking in log terms as the TCO rises. **B6's Cuban analogue is
`K_VENTA = 1.020`, fixed as a ratio and therefore constant in log terms.** The
two administered spreads differ in level and in how they behave under a
devaluation, and that comparison is a result of this stage.

### Arm III

**B15-6. The published TCO is the statute's weighted average.** Recompute
`TCO_t = Σ(TC_it × M_it) / Σ M_it` from S2's microdata and compare against S1's
published value.
**Passes if**: the recomputation equals the published value to the published
precision on **>= 99%** of days S2 covers.
**This is the zero calibration of the formal leg** and it is the counterpart of
B6-18, which found 909 of 1,321 days exactly equal on the informal leg. A stage
that only reports differences cannot show that it would report zero when zero is
the truth.
**A failure here is a finding and not a defect.** If the published TCO is not
what Anexo II says it is, that is the most interesting single result this stage
could return, and §7.1 says what would have to be ruled out first.

**B15-7. The posted return leg.** The direct analogue of B6-15, with Art. 6's
ceiling in place of Cuba's `K_VENTA`:

```
a(t) = log p_ask_parallel(t) - log ( TCO(t) + 0.10 )
```

**Passes if**: the share of days with `a(t) > 0` is **>= 0.95** and the critical
spread exceeds **0.02**. **The thresholds are B6-15's, unchanged, because the
comparison is the purpose.**

**This criterion is registered to be informative in both directions and the
register says so before the run.** `a(t) > 0` means the informal ask is above the
legal official ceiling, so the official window does not clear and B6's reading
repeats on a second carrier. `a(t) < 0` means the informal ask sits **inside** the
official spread, so the official ask does not bind and there is no cycle to
certify, which is the opposite reading. **`bolivia_availability.md` §4.4 records
provisional press-level figures pointing at the second**, and those figures are
not used, are not in this document as inputs, and will not be looked at again
before the criterion runs.

**B15-8. Friction, and the cycle B6-B could never certify.** With both sides on
both legs, `edge_weights(bid, ask) = (-log ask, log bid)` is available on every
edge without substitution. Build the two-position cycle official ↔ parallel and
run Bellman-Ford per `b1_theorem.md` Theorem 4.
**Passes if**: the sign of the maximal cycle weight is determined on **>= 99%**
of days, meaning the cycle is certified positive or certified non-positive rather
than left undetermined by a bound.
**The registered claim is capability, not direction.** A positive cycle and a
non-positive cycle are both live outcomes. **What B6-B could not do at all, and
what B6-12 exists to prevent it from claiming, is what this criterion does.**

**B15-9. The customs edge.** As `bolivia_availability.md` §4.6. `Art. 20` of
`D.S. 25870` strikes the customs tax base at

```
TC_aduana(t) = TCO_venta( last business day of the week before t )
```

held flat for a week, and granted to `Operadores de Comercio Exterior` alone.
This is a one-way edge with a deterministic weight given the published series,
and its holonomy around **market purchase, import, valuation at `TC_aduana`** is
computable from S1 and S3.
**Passes if**: the edge weight is reproduced from S1 for **100%** of weeks in the
post-event window, and the holonomy is reported with its sign and its maximum.
**The transition week is the registered single observation**: the comunicado
fixes 6.96 for declarations accepted 2026-06-29 to 2026-07-05, a week in which
the peg was already gone. **That is the edge at its widest and its width is a
number this stage reports.**

### Arm IV

**B15-10. The event.** Structural break at 2026-06-29 in the log gap between the
parallel bid and the official ask, tested against a permutation null over the
window with the break date drawn uniformly, 999 draws, seed 0.
**Passes if**: the observed break statistic exceeds the 99th percentile of the
null.
**The null's degeneracy is checked and reported**, because B6-14's null returned
exactly the same value on all 999 draws and that was reported rather than hidden.

**B15-11. Zero calibration across publishers.** S3, S4 and S5 publish the same
underlying market. Where two of them agree exactly on a day, the instrument has
reported zero when zero was the truth.
**Passes if**: the share of days on which at least two of the three agree to the
published precision is **>= 0.50**.
**And the disagreement is the measurement B6-B could not make.** B6-B had one
publisher of Cuba's informal rate, so `cuba_informal.noise_floor` had to infer
publication noise from a variance identity. **Here it is observed directly**, as
the dispersion across publishers of one market, and that observed floor replaces
the inferred one wherever a later criterion needs a noise band.

**B15-12. The referee.** The BCB's `Bs / Euro` against the ECB daily reference
rate times the BCB's `Bs / Dólar`.
**Passes if**: the two agree within a band that is fixed before the run at the
tick of the published euro series.
**Registered expectation, and it is a prediction rather than a hope**: B6-5 found
the BCC's euro to be the dollar times a world cross, which is what made B6-4 a
test of the pass-through rather than of the rate. **If Bolivia's is the same, this
criterion measures the pass-through and says so**, and the alignment that sank
B6-4 is here fixed by Art. 5.III instead of guessed.

## 6. Constants and guards

### 6.1 Constants, fixed here

```
WINDOW_OPEN_DATE      = 2024-07-21          # S3's first observation
EVENT_DATE            = 2026-06-29          # first day the new regime governs
SIGNING_DATE          = 2026-06-26          # RM 245 and RD 88/2026
CUSTOMS_SWITCH_DATE   = 2026-07-06          # Art. 20 leaves the frozen 6.96
TZ                    = "America/La_Paz"    # UTC-4, no DST
ORDINARY_SPAN         = 86_399              # asserted on every day, not assumed
STATUTORY_SPREAD      = 0.10                # RD 88/2026 Art. 6, bolivianos
SPREAD_SHARE          = 0.99                # B15-5
UNCROSSED_SHARE       = 0.99                # B15-3, the deciding orientation
CROSSED_SHARE_MAX     = 0.50                # B15-3, the rejected orientation
TCO_RECOMPUTE_SHARE   = 0.99                # B15-6
A_SHARE               = 0.95                # B15-7, B6-15's threshold unchanged
CRITICAL_SPREAD       = 0.02                # B15-7, B6-15's threshold unchanged
CYCLE_DETERMINED      = 0.99                # B15-8
AGREEMENT_SHARE       = 0.50                # B15-11
NULL_DRAWS, NULL_SEED = 999, 0              # B15-10, B6-B's values
```

**No threshold in this list was chosen after seeing a Bolivian number, because
no Bolivian number has been seen.** Four of them are B6's own values carried over
unchanged so that the two carriers are compared on identical criteria.

### 6.2 Guards on the data

- **`guard_break_disclosure`**: a criterion whose window straddles 2026-06-29
  reports that it does, in its own record.
- **`guard_kind_column`**: S3's `oficial.csv` `kind` field is read and recorded
  per row. A change in `kind` inside a window is a break and is disclosed.
  **A row whose two sides are equal is recorded as a fill and never as a zero
  spread**, since `bolivia_availability.md` §3.2.1 flags `unificado` rows with
  `compra == venta` and Art. 6 says the true spread is 0.10.
- **`guard_no_fill`**: an absent day is absent. Nothing is forward-filled, in
  either direction, at any resolution.
- **`guard_span`**: every day's span is `ORDINARY_SPAN`. La Paz has no DST and
  the guard asserts it rather than trusting it.
- **`guard_truncation`**: a payload that ends mid-record is a corrupt file and is
  re-fetched. **This one is written because it already happened**: the first
  read of `all.csv` returned 1,162 lines ending mid-number, and a fetcher without
  this guard would have recorded 2024-08-01 as the end of the series.

### 6.3 Guards on the criteria

- **`guard_no_one_sided_in_friction`**: §2.2. paralelo.bo's median-only history
  may not enter a spread, a round trip or a cycle weight.
- **`guard_typing_first`**: arm III does not run unless B15-3 and B15-4 both
  return live verdicts. Implemented as a hard gate, not a warning.
- **`guard_no_alignment_shopping`**: the date convention and the side convention
  are read out of B15-4 and B15-3 and may not be re-derived inside any arm III
  criterion. This is the code form of `HANDOFF` §3.2 item thirteen.
- **`guard_press_free`**: no number that entered this project through press
  coverage or a fetch summary may be an input to any criterion. The list of such
  numbers is in `bolivia_availability.md` §6 and it is checked against the
  constants above, which contain none of them.

## 7. Falsification

### 7.1 B15-6

**If the recomputed TCO does not match the published one**, three things are
ruled out before it is called a finding: S2's tier buckets rounding differently
from the underlying operations; the 17:00 cutoff excluding operations S2 still
lists; and the published value being rounded to a coarser precision than the
recomputation. **Only after all three fail does the statute and the practice
disagree**, and that is reported as such.

### 7.2 B15-7

**`a(t) > 0` does not establish that the official window fails to clear.** It
establishes that the informal ask is above the legal ceiling on the day, which is
consistent with the window clearing at a rationed quantity. **B6 carries the same
limit and states it**; §2.3 is why it is repeated here. What would settle it is
the sale-side transaction record, which §2.3 records does not exist.

### 7.3 B15-8

**A certified positive cycle is a claim about published quotes and not about
executable prices.** A2 (§3.6) is what stands between the two, it is not tested,
and any positive cycle this criterion certifies is reported with A2 named beside
it.

### 7.4 The stage as a whole

**B15 fails as a control if its criteria cannot be run at B6's thresholds.** If
arm III is suspended by a void in B15-3 or B15-4, the stage degrades to arms I,
II and IV, which is a cross-section plus an event study and **not** the
discriminating case §1 asks for. **That outcome is registered as a possible
result and the stage will be reported as degraded rather than rewritten to fit
what it can do.**

## 8. Scope

- **One venue's book.** §3.6 A3. The parallel leg is Binance P2P through one
  publisher's best-offer extraction, and every aggregator found resolves to the
  same source. **This stage does not measure "the Bolivian parallel market".**
- **The dollar only.** The euro appears in B15-12 as a referee and nowhere else.
- **No claim about welfare, policy or the wisdom of the reform.** The stage
  measures edges, weights and cycles.
- **The pre-event span carries one regime.** 2024-07-21 to 2026-06-26 is a peg
  throughout, so the pre-period has no internal variation in the official rate,
  and any criterion whose power comes from official-rate variation has that power
  only after the event. **B15-5 is the exception and it is registered for that
  reason**: a constant is exactly what it is testing.

## 9. What this stage does not contain

- **`RM 245`'s articles.** Its identity is settled from the Aduana comunicado on
  disk. Its text is not read. **No criterion depends on what it says.**
- **`Anexo I` of `RD 88/2026`.** Whether banks may sell to natural persons, and
  on what condition, is the Cuban Circular question in Bolivian form and it is
  open. **No criterion depends on the answer**, and when it is read it will
  interpret B15-7 rather than change it.
- **The superseded Aduana comunicado of 2026-06-27.** It is the counterfactual
  for B15-9 and it has not been seen.
- **Any Bolivian number.** §6.1.

## 10. Retrieval

**Written to `data/fetch_bolivia.py`, to `data/fetch_eltoque.py`'s contract**, and
none of it has been run.

One file per source per period under `data/raw/bolivia/`. Resume by file
existence. Two digests per response, the payload digest being the stable one.
Pacing read from response headers and not assumed, with the elTOQUE lesson
recorded in `b6b_eltoque_prereg.md` §12 applied: **a documented rate limit is a
claim and the measured one is the fact**, and a `Retry-After` that is negative is
not a delay to clamp.

**Politeness, registered:**

- S1 is one request per year. **Roughly 3 requests** for the window, and the
  whole series to 1940 is under 90 if it is ever wanted.
- S3's publisher asks for no polling faster than 60 seconds and the archive is
  one file. **One request**, repeated only to extend.
- S4 is CC-BY 4.0 and is cited as `paralelo.bo (https://paralelo.bo)`.
- S5 is a git clone, which is one operation and is versioned by construction.
- S3's terms permit reuse with the attribution `Powered by
  dolarbluebolivia.click` and say bulk history wants registration.
  **`bolivia_availability.md` §3.2.1 records the tension and the resolution is
  to register or to fall back to S4 plus S5 rather than to pull quietly.**

**Total registered request count for the whole stage is in the low tens**, against
the 2,056 days and nine hours B6-B cost. The difference is that these publishers
serve ranges and elTOQUE serves one day per request.

## 11. Disclosure

**What was seen before this register closed, and by what means.**

| seen | how | used as an input? |
|---|---|---|
| the existence and shape of S1 to S6 | fetch summaries | **no**, only to choose sources |
| `RD 88/2026` Art. 5.I, 5.III, 6, Anexo II | fetch summary of the BCB's own PDF | **yes, for §2.3, §3.4, §6.1's `STATUTORY_SPREAD`**. Flagged in `bolivia_availability.md` §6 as needing the PDF read from disk |
| the Aduana comunicado | **read from disk**, text and image | **yes**, for §3.4's anchor and §5's B15-9 |
| S3's header and first rows | fetch summary | **no**. B15-3 exists because the ordering was noticed, and the criterion is decided from the full archive, not from those rows |
| press figures for the post-event gap | press | **no**, and `guard_press_free` enforces it |
| a BCB annual-table read reporting a value for 2026-08-31 | fetch summary | **no. Discarded as impossible**, `bolivia_availability.md` §6 |

**The one honest exposure is row two.** Four articles of `RD 88/2026` are quoted
from a summary of the PDF rather than from the PDF, and `STATUTORY_SPREAD = 0.10`
is registered on that basis. **If the PDF says otherwise, B15-5 and B15-7 change
and this register is amended in §12 with the old value left visible.**

## 12. Changelog

**v1, 2026-08-19.** First registration. Nothing downloaded, nothing computed.
Carrier and number assigned the same day. Twelve criteria, of which
arm III's four are gated on B15-3 and B15-4 returning live verdicts.

**2026-08-19, both instruments read from source. No registered value moves.**
`RD N° 88/2026` and `Resolución Ministerial N° 245` were supplied by hand and
both were read from disk, text layer and page image. **Readings are in
`docs/b15_bolivia_results.md` §0** and this entry records only what they do to
this register.

- **§11 row two is closed.** Art. 5.I, Art. 6 and Anexo II are confirmed word
  for word against the summary they were quoted from, including the formula.
  **So `STATUTORY_SPREAD = 0.10` is a statute and not a summary of one**, and
  **B15-5 and B15-7 stand exactly as registered.** §11 provided for the old
  value to be left visible here if the PDF disagreed. It does not.
- **Art. 5.III was truncated by that summary and Art. 5.IV was absent from it.**
  The `vigente al día siguiente` rule is written `para las operaciones del
  sector público y del BCB y para los registros contables y de valoración`, and
  Art. 5.IV makes the TCO a `referencia` for everyone else with no stated date
  of effect. **B15-4's test is unchanged**, since it measures when the published
  number steps. **Its reading gains a qualifier**: the vigencia it can identify
  is the one the statute dates, which is the public-sector one, and the
  criterion's record says so.
- **Anexo II §4 fixes the published value at two decimals.** §7.1's third
  exclusion becomes a stated fact rather than a hypothesis, so B15-6's
  comparison is defined at that precision by the statute.
  `TCO_RECOMPUTE_SHARE = 0.99` does not move.
- **Anexo II §4 also writes a weekend and holiday forward-fill into law.** This
  does not touch `guard_no_fill`, which governs this project's code; a weekend
  row carrying Friday's number is the publisher reporting what the statute says
  the rate is.
- **§9's `Anexo I` question is answered and §9 holds.** Anexo I is the
  Reglamento in seven articles and **no article states a quantity, an
  eligibility condition or a cap**; Art. 6 caps the price alone. Per
  `b8_pitfalls.md` entry 52 the finding is that **this instrument** does not
  ration, which is not the same as nothing rationing. §9's sentence that reading
  it "will interpret B15-7 rather than change it" is what happened.
- **§9's `RM 245` entry holds too.** Its three operative points are read and no
  criterion depends on them. What they add is a provenance for §2.3: the
  delegating instrument names `oferta y demanda` and the implementing reglamento
  built the average from purchases alone.

**2026-08-19, the endpoints answered. One retrieval decision is now forced
rather than merely cheap.** Four requests, nothing written, readings in
`docs/b15_bolivia_results.md` §1.

- **`xls.php` serves an OLE2 workbook**, which the standard library cannot read.
  §10's decision to fetch `ods.php` beside it was recorded as machinery that
  would pay either way; **it is now the only parse path for the formal leg**.
  S1 as named in §3.1 is unchanged and remains the source of record.
- **`all.csv` carries `Content-Length: 3,156,156`**, which measures the earlier
  1,162-line read as the truncation `guard_truncation` was written for.
- **`oficial.csv` exists and carries a `kind` column**, so §6.2's
  `guard_kind_column` is exercisable. A `referencial` row inside the peg era
  confirms §2.4's warning before any pull.
- **No response carries a rate-limit header.** There is nothing to measure, so
  §10's floors are the whole of the pacing, which is a weaker footing than B6-B
  ended on.
- **One question is open about the instrument itself**: `all.csv` is rebuilt per
  request, so its 15-minute grid may be anchored to the clock or to the moment
  of generation. **If it is the second, a row is not addressable by its
  timestamp and B15-2 needs a different key on S3.** One extra request separates
  the two and it is registered before it runs.

---

## 13. Closure addendum

**Written at closure, 2026-08-20. §1 to §12 are unchanged.**

A station's design file is fixed before the run and only added to afterwards,
and closing one requires writing back the conclusions that were reached but have
no entry above. **Without this section a later reader takes them as untested and
measures them again.** Every reading named here is in
`docs/b15_bolivia_results.md` with its timestamp; this section is the index, not
the evidence.

### 13.0 Closure revised 2026-08-21: B15-4 is void and arm III is suspended

**Added, not rewritten**, which is the rule this section already runs under:
§1 to §12 do not move and the entries below stand as written on 2026-08-20.

**What changed is one preprocessing step that §5 does not register.** S3's
`datetime` column carries no offset, and the clock it is on was being set by a
two-hour test fed from another run's manifest. Measured against the publisher's
own page and against a second publisher's offset-carrying stamps, the column is
`America/La_Paz` and not UTC. On that clock the official leg steps at 04:00 to
05:00 on 31 of 36 steps, at neither hour §3.4 admits, so **§3.4's third branch
fires: B15-4 is void and §6.3 suspends arm III.**

**§5 B15-4 is not amended and needs no amendment.** It wrote this branch and the
branch fired. The customs anchor reproduces, more cleanly than the entries below
record, and that does not rescue the criterion because §5 B15-4 is a
conjunction.

**The full account is `docs/b15_bolivia_results.md` §9**, with the voided
sections there carrying dated pointers to it.

**B15-12 has since run, 2026-08-21.** §3.3 put the euro on an endpoint that
serves the dollar and takes a year parameter; it is on a per-day quotation
table at the same institution, one request each, and the correction is recorded
in `docs/b15_bolivia_results.md` §10.1. **The criterion returns FAIL and its
registered expectation is falsified**: Bolivia's euro is not, as Cuba's was, the
published dollar times a world cross at any alignment tried, so this stage does
not have B6's pass-through reading available. §11 carries the readings, the
per-day rounding envelope that rules out arithmetic, and the finding that the
registered band of one tick sits below the floor the referee's own four
decimals put under any reconstruction. **Arm IV is now three failures and no
passes**, none of them an instrument breaking.

Entries 13.1 to 13.4 below were
written while arm III counted; where they name an arm III reading as a
conclusion, that reading is now a reading and not a verdict.

### 13.0b Closure revised again 2026-08-21: B15-4 resolves and arm III runs

**Added, not rewritten. §13.0 above stands as written and its account of the
step-hour instrument is correct.** What changed after it is the instrument, not
the account.

**B15-4 reads `vigencia date`, from the publisher's own two columns.**
`bcb_tco_series.csv` carries `Fecha de corte` and `Vigencia` on every row, and
the official column keys on `Vigencia` on 39 of 39 against 1 of 35 under
`Fecha de corte`. **No clock, no aggregator, no third party, and no threshold on
an estimator.** §3.4's instrument reads the convention off the local hour the
series steps and 31 of 36 steps land at 04:00 to 05:00, at neither hour Art.
5.III makes available: it was measuring the aggregator's refresh. **That is D3's
third category, the reason is recorded, and the original VOID is kept in the
record beside the live verdict.**

**B15-3 stays VOID on the registered window and §6.3's gate is asked on the
segment arm III uses.** The registered window straddles §3.5's break; the
post-event segment, which is the only segment arm III runs on and which it
discloses, resolves to orientation A on 99.960% of 4,966 rows.

**So arm III runs and the stage closes with twelve verdicts.** B15-7 reads 21 of
52 against B6's own 95%, where Cuba's B6-15 reads 207 of 207, and the reading
survives every cell of a five-alignment by two-ceiling sweep (26.00% to 66.00%).
**The question §1 opened the stage to answer is answered.**
`docs/b15_bolivia_results.md` §13 carries it and §12 carries the sweep.

### 13.1 Things the register did not know about its own sources

| | what turned out to be true | where |
|---|---|---|
| **S1's month labels** | The 2026 sheet displaces every post-reform month one two-column block to the right of its label, and June is split across two blocks because the reform fell on the 26th. Settled against S2's dated values, not against the labels | results §6.1 |
| **S1's filing convention** | S1 files by **vigencia**, agreeing with S2's own `Vigencia` column | results §6.1 |
| **S2's endpoints** | `tco_reporte_detalle_historico.php?fecha=` for one day's microdata, `tco_tcreferencial_descargar_csv.php?desde=&hasta=` for the whole range in one request. Both read off the page's form | results §5, §5.5 |
| **S2's detail endpoint lies by omission** | `?fecha=` on a day with no operations returns 200 and **another day's grid**. The page states the day it is showing in its date input, and `guard_echoed_date` reads it | results §5.4 |
| **S2's CSV states both dates** | `Fecha de corte` and `Vigencia` are separate columns, and `Vigencia` is sometimes a range where a holiday block is covered | results §5.3 |
| **S3's blue columns reverse at the event** | And S5's do not, on 745 of 745 days, so the reversal is one publisher's labels rather than the market | results §2.3, §4 |
| **S4 opens with a licence banner** | Four `#` lines before the header row | results §3.2 |
| **S6 is not where §3.3 put it** | The BCB's rate index carries `?anio=` and no currency parameter, and its own heading says it is the dollar. B15-12 is `pending on retrieval` | results §7 |

### 13.2 Conclusions with no criterion of their own

**The reform ratified a rate the banks had already reached.** The amount-weighted
bank purchase rate ran from 7.85 on 2025-12-01 to 9.76 on 2026-06-26, the last
day of the peg, while the BCB posted 6.86 and 6.96 throughout. The first TCO of
the flexible regime was 9.73. **A step of about 0.3%.** results §4.3.

**So B15-10's FAIL is not that the reform did nothing.** The log gap has no
single dated break: it steps at the reform and keeps moving for six weeks, and a
uniform-break-date null cannot separate the reform from the adjustment that
followed it. results §3.1.

**And the pre-event segment does not give a Cuba-like reading either.** Measured
against the price the banks were actually selling at rather than against the
frozen posted quote, `a(t) > 0` on 65.4% of 182 pre-event days, against Cuba's
100% and this stage's post-event 40.4%. **The discriminating answer of §1 does
not depend on the segmentation question.** results §4.4.

**`bolivia_availability.md` §4.6 needs one word changed and it is recorded rather
than edited.** That section says the customs edge is "during a rising regime
strictly favourable" to `Operadores de Comercio Exterior`. It is favourable while
the rate rises and adverse while it falls, and both happened inside eight weeks.
The edge is a one-week lag and a lag cuts both ways. results §6.4.

### 13.3 What did not run, and what that costs

**SUPERSEDED by §13.0b: B15-12 ran, and twelve of twelve criteria carry the
stage.** The euro was located on a per-day BCB quotation table rather than the
endpoint §3.1 named, one request each, and the criterion returns FAIL with its
registered expectation falsified. This section is kept as written and the
paragraph below is the state on 2026-08-20.

**B15-12 alone.** Its source is not at the endpoint §3.1 named, which is a
retrieval fact and not a reading. §5 registers its own expectation that it would
measure a pass-through rather than a rate, it sits in arm IV, and it gates
nothing. **Eleven of twelve criteria carry the stage.**

**Arm III ran at B6's thresholds, unchanged, on the post-event segment**, so
§7.4's degraded outcome did not occur in the sense that section feared. B15-3
stands VOID on the registered whole window and the void is explained rather than
repaired.

### 13.4 The three constants §6.1 could not have chosen well

**Not a complaint about the register and not a change to it.** `SPREAD_SHARE`,
`UNCROSSED_SHARE`, `TCO_RECOMPUTE_SHARE` and `CYCLE_DETERMINED` are all 0.99 and
`CROSSED_SHARE_MAX` and `AGREEMENT_SHARE` are both 0.50, and none of the six has
a source. They are a qualitative judgement written as a number, which this
project's own discipline classifies as an arbitrary calibration value that may
not carry a refutation.

**One of them decided something.** `UNCROSSED_SHARE = 0.99` is what makes B15-3
VOID, and B15-3's void is what suspended arm III on the registered window. The
readings underneath it are not close to the line in a way the line resolves:
pre-event 91.24% one way, post-event 99.96% the other, with the convention
reversing at the event. **The line did not detect the problem; printing the two
periods did.**

**Recorded here so that the next station's register does not spend a threshold
where it should spend a print.**
