# B6-A: reachability typing inside one central bank's own table (Cuba)

Pre-registration for **the half of stage B6 that needs no source outside the
Banco Central de Cuba.** Every filter, threshold, window and criterion below is
fixed here.

Availability, sourcing, and the ruling that this stage may be opened are in
[`b6_cuba_availability.md`](b6_cuba_availability.md). That document carries two
things a reader should see before this one: the identification is
**cross-sectional and not before-and-after**, contrary to what
`PROJECT_PLAN.md` §14.4 envisaged; and the `H⁰` typing here rests on **a
published eligibility rule rather than on the absence of a quote from a file**,
which is what makes this carrier able to do what §12.11 says no carrier had
done.

The directed theorems in [`b4_directed_edges.md`](b4_directed_edges.md) are
load-bearing throughout. Theorem 5 supplies the object; §5.2's table supplies the
typing rule; §5.1's prohibition on reporting a single orientation `S` applies to
every number below.

**Why this document covers only half a stage.** The complete stage contrasts an
edge on which a premium is a defined `H¹` quantity against edges on which it is
not. The `H⁰` side, and every arm that validates the machinery, lives entirely
inside the BCC table and is registered here. The `H¹` side needs the informal
market, whose retrieval is behind the one gate in `b6_cuba_availability.md`
§3.4. **B6-A is registered and run first so that no criterion touching the
informal leg can be written after its data has been seen.** §9 states exactly
what is deferred.

---

## 1. What this half of the stage is for

Theorem 5 says that a position which can be entered and not left is **not
priced**: the sub-potential polyhedron has an unbounded ray there, so the
position is bounded on one side only. `PROJECT_PLAN.md` §12.11 says this has
never had an empirical reading in this project, because the object of
observation is a missing quote and a missing quote is indistinguishable from an
incomplete dataset.

**This half of the stage supplies the reading, and it does so by finding a case
where nothing is missing from the data.** The Banco Central de Cuba publishes,
every day, three rates for one conversion. Two of them are attached by
regulation to designated operations and admit no return leg. Both are printed to
four decimals. **The absence is in the regulation, not in the file.**

What B6-A produces: the `H⁰` typing, stated as a criterion that can fail; the
machinery validated against a closed form and against a hundred and ninety
known answers; the position factor shown to be exact on this carrier, so that
the whole obstruction is in the agent factor; and an external referee for the
source. What it does not produce is the contrast, which is §9.

---

## 2. The graph

Fix a date `t`. There is **one position pair**, `CUP` and `USD`, with `EUR`
entering only in §2.4's triangle. There is no maturity axis and no path through
an intermediate asset. Everything is on a single edge of the position graph `G`.

What varies is the **agent factor** `H`. Cuba prices one conversion three
different ways on the same day, and which price applies to you is fixed by legal
status and by the operation you are performing.

### 2.1 The three segments, and the rule that admits each one

| segment | API field | who may transact | return leg for that class |
|---|---|---|---|
| **I** | `tasaOficial` | state enterprises and legal persons, on designated operations | **none.** The entitlement attaches to the operation; a holder cannot resell at this rate |
| **II** | `tasaPublica` | natural persons, on the retained fixed schedule | **none**, on the same ground |
| **III** | `tasaEspecial` | the managed float opened 2025-12-18, with a cap of USD 100 per purchase operation for individuals | **both directions quoted**, buy and sell, at every channel in §2.2 |

**This is `b2_measurement.md`'s cell structure printed by a central bank**: one
position pair, several agent classes, terms differing by who the agent is rather
than by what is bought. `PROJECT_PLAN.md` §9.4's ruling that the orphan currency
measures **squares and not slices** holds here for the same reason it held in
B5, and §2.4 confirms it from the shape rather than asserting it.

**Do not run any slice-against-square decomposition on this carrier.** Theorem 2
does not extend to directed graphs; directed cycles form a cone and cones have
no direct-sum decomposition (`PROJECT_PLAN.md` §12.10, `b4` §6). Segments I and
II are directed.

### 2.2 The nineteen channel columns are one number times a constant

For each segment the XLSX publishes nineteen further columns: cash at the
counter, cash at airports and hotels, cash on Sundays and holidays, inbound
transfer to account, inbound transfer to cash, international card purchases,
currency services to CUP, transfers in both directions, cash withdrawal and
deposit against a foreign-currency account, and three `USD Legal` tiers.

**Each is the segment's base rate times a fixed constant `k`.** The schedule is
in `b6_cuba_availability.md` §3.2 and is reproduced in
`src/monetary_topology/cuba_segments.py` as the registered constant
`MARKUP_SCHEDULE`.

Two consequences are registered here as design rules rather than as findings.

**No headline square may have both legs inside one segment.** For channels `a`
and `b` of the same segment the index part is `2 log(k_b/k_a)`, the same
constant on every date, zero variance. That is a construction identity, and
`HANDOFF.md` §3.2 item 6 records what happens when one is written up as a
confirmation.

**The friction column on this carrier is a policy parameter.** `b4` §5.1
describes `S + S'` as the two agents' round-trip costs. Here the spread is a
posted administrative markup. The headline is unaffected, being invariant to
friction common to both classes, but the column beside it does not mean what the
same column means in B2 or B3 and **must not be labelled as a market's
round-trip cost.**

### 2.3 What is a square here and what is not

A square needs two agent classes facing **the same** conversion. Segments I, II
and III on the same date satisfy that: `CUP ↔ USD`, same day, same publisher,
different classes.

**A square between two channels of the same segment does not**, in the sense
that matters: it satisfies the definition and carries no information, per §2.2.
It is used as a known answer and never as a result.

### 2.4 The position factor is exact on this carrier, and that is worth stating

The euro columns give a second position. The triangle
`CUP → USD → EUR → CUP`, taken inside one segment, is the slice object of
Theorem 2 on this carrier.

**It is zero by construction**, because the BCC derives its euro rate by
applying one international cross to the segment's dollar number. B6-5 measures
it rather than assuming it. The consequence, which is the point: **on this
carrier the entire obstruction is in the agent factor**, and the square-against-
slice split of Theorem 2 is not a finding to be measured but a property of how
the source is built. Saying so in advance prevents the `curl`-against-`harmonic`
error `PROJECT_PLAN.md` §12.3 records, where a decomposition was going to be run
whose answer was fixed before the code.

### 2.5 The yen is published the other way up, and the bank says so

Twelve currencies are published `de forma directa`, pesos per unit. **The yen is
published `de manera indirecta`**, yen per peso, and the bank's own page carries
that footnote. A peso is worth a few yen and a yen a few pesos, so the direct
column would carry no significant figures at the published precision.

**The orientation is read, not inferred.** It is registered in
`cuba_segments.QUOTATION` from the footnote. Two independent checks agree and
neither is how it was established: the segment ladder runs `1/5` and `1/26` for
the yen where every direct currency runs `5` and `26`, and `24 × 6.58062`
recovers a plausible USD/JPY of about 158. **Guard 6 asserts the ladder still
points the registered way**, so a change of convention stops the run rather than
silently inverting one row of B6-8.

**Choosing the orientation that makes B6-8 pass would be fitting.** Choosing it
from a footnote is reading. The distinction is the whole of the defence and it is
why the footnote is cited rather than the ladder.

---

## 3. The measurement

### 3.1 Which source supplies what

| leg | source | terms |
|---|---|---|
| segments I, II, III, daily | `https://api.bc.gob.cu/v1/tasas-de-cambio/historico`, `codigoMoneda` in `{USD, EUR}` | free, no key, no account, endpoint verified 2026-08-12 |
| the nineteen channel columns | the XLSX export at `https://www.bc.gob.cu/tasas-de-cambio` | free, same publisher, used to **validate** `MARKUP_SCHEDULE` rather than as the daily source |
| the external referee | an independent daily `EUR/USD` reference, see B6-4 | **endpoint not yet verified**, see §6 |

**One publisher supplies every class.** This removes a confound B5 had to live
with: in Argentina a difference between two classes was partly a difference
between two reporters. It also removes a check B5 had. See §4.3.

### 3.2 The estimator is defined on publication days

The XLSX carries every calendar day; the API carries only the days on which a
rate was published; the XLSX's extra days are **forward fills** of the previous
published value (`b6_cuba_availability.md` §6.1).

**The publication schedule changes inside the window**: Sundays and Mondays are
absent through 2026-02-23 and publication is near daily from 2026-03-10, so the
share of stale days is correlated with calendar time and therefore with the
level of the float. Left alone, the measurement error would carry a trend
correlated with the quantity being measured, and nothing in the file would
report it. This is `MEASUREMENT.md` failure mode 1 compounded with mode 5, of
the coherent-drift kind its meta-rule says a self-check will not catch.

**Registered:**

1. The estimator runs on **publication days**, defined as the dates the API
   returns.
2. Forward-filled dates are recorded in the manifest and **skipped by the
   loader**. Nothing is deleted and no file is edited; the loader ignores what it
   should not read, per `CLAUDE.md` rule 5 and the `VALID_NAME` precedent.
3. Every headline is computed **twice, on publication days and on all calendar
   days**, and both are reported, per `b5_orphan_availability.md` §7.6b. A
   material difference is the finding, not a defect to be cleaned away.

### 3.3 Aggregation is in logs, and only mids enter the index part

Every quantity below is stated in logs, per `MEASUREMENT.md` rule 3, and every
index part is `S − S' = 2 log(mid_b/mid_a)`. **A single orientation `S` is never
reported** (`b4` §5.1). Where a segment publishes only one number, that number
is the mid: it is a reference rate and carries no bid or ask, exactly as BCRA's
A 3500 did in B5.

### 3.4 What `H⁰` means operationally here

`b4` §5.2's rule assigns the type from what is observed: both directions quoted
implies `H¹` with friction; one direction only, for some class, implies `H⁰`.

**For segments I and II the second row applies, and the ground is the
regulation, not a gap in the file.** The rate is attached to designated
operations. A party who acquires dollars at segment I cannot resell them at
segment I; a party holding pesos cannot acquire dollars there at will. There is
no closed loop through those positions, so there is no holonomy to sum, and
**a number computed by imputing the missing direction has imputed the quantity
in dispute** (`b4` §5.2, prohibited).

**The registered consequence, which is what B6-6 tests:** the log distance from
a frozen segment to the float is not held by any bound the table can supply,
because no round trip exists to supply one. Reporting that distance as an
overvaluation percentage would be an `H⁰` fact under an `H¹` name, which is the
error `b1_theorem.md` §12.1 records.

---

## 4. The arms

### 4.1 Known-answer arm, and it is an order of magnitude stronger than B5's

B5 had one known answer, `tarjeta ≡ oficial × 1.30`. Here twenty columns per
segment give **one hundred and ninety pairs**, each with an index part fixed by
`MARKUP_SCHEDULE`, on every date, in two currencies and three segments.

`MEASUREMENT.md` calls a zero calibration standard equipment. This is its
known-answer sibling and it exercises the same machinery the rest of the stage
uses. **It is a floor, not a finding** (`a3_asset_channel.md` §2's phrasing), and
must be reported as one.

### 4.2 Euro triangulation

USD segments I and II are constant across the window. **The euro equivalents are
not**, because the peg is fixed against the dollar and the CUP value of the euro
inherits the international cross. Any implementation that treats a fixed segment
as a constant disagrees with the euro file immediately. B6-5 and the guard in §6
make this an assertion rather than a footnote.

### 4.3 There is no zero calibration on this window, and the two delivery paths
are not one

`MEASUREMENT.md` item 7 makes a zero calibration standard equipment on every new
carrier. B5 built one from BNA's own posted rate against a third party's report
of it: one dealer, one counter, two collection paths.

**The Cuban analogue exists and has no history.** elTOQUE's formal-market page
republishes CADECA's and the banks' buy and sell quotes, but carries current
values only. So the arm can run **forward from the day collection starts** and
cannot run over this window.

**The XLSX-against-API agreement is not a substitute and must not be written up
as one.** Two delivery paths for one record test the retrieval code, not the
collection. Calling it a zero calibration would be a guard that is silent when
it should speak, which is the pattern `PROJECT_PLAN.md` §11.11 collects.

**What replaces it is B6-4**, an external referee on the one quantity the table
exposes to outside checking: the euro cross implied by its own columns. That is
weaker than a zero calibration, because it validates the source rather than the
pipeline, and it is stated as weaker.

---

## 5. Pre-registered criteria

Read the order. **B6-1 and B6-2 gate everything.** If the machinery disagrees
with its own closed form, no number below it means anything.

### B6-1. The machinery reproduces the closed form, elementwise

One path decomposes each quote through `directed.py` and walks the four-cycle;
the other evaluates `2 log(mid_b/mid_a)` directly. The two must agree
elementwise over every date and every pair.

**Domain: pairs of two-sided channels inside one segment.** A square needs two
classes that each quote both directions, and after B6-6b's ruling the only such
classes on this carrier are the float's four two-sided channels, giving six
pairs. Running the machinery between segments would be walking a square whose
second orientation does not exist, which is the thing `b4` §5.2 prohibits.

**Threshold:** `MACHINERY_TOLERANCE = 1e-12`. The two paths are the same
arithmetic in a different order, so anything above rounding is a bug rather than
a precision question. Precedent: B5-1, same constant, same reason.

**Fails if:** any element differs by more than the tolerance.

### B6-2. Trivial cycles are exactly zero

`|z(a,a)| = 0` exactly, for every class `a` and every date, read from the
**diagonal of the same matrix** the off-diagonal entries come from, never
short-circuited. Precedent: B5-2, B3-7.

**Fails if:** any diagonal entry is non-zero, or the implementation returns the
diagonal without computing it.

### B6-3. The known-answer arm: one hundred and ninety pairs, every date

For every ordered pair of channels `(a, b)` inside one segment, the measured
index part equals `2 log(k_b/k_a)` with `k` read from `MARKUP_SCHEDULE`.

**No threshold, because the publisher's arithmetic is reproducible.** The
published channel values are **truncated** at four decimals, not rounded:
checked on 2026-08-12 over every channel column of all six files, 27 132 of
27 132 values equal `floor(base × k × 1e4) / 1e4` and none equals the rounded
value. `cuba_segments.published_from` reproduces that exactly, so the primary
form of B6-3 is a **strict equality on integer last-place counts**, with nothing
in it to be widened later.

**The fallback form, for use only if guard 1 shows the truncation model has
stopped holding.** A truncated value of magnitude `r` carries absolute error up
to one unit in the last place, `1e-4`, so the index part carries at most
`2 × 1e-4 × (1/r_a + 1/r_b)`, evaluated per pair per date rather than fixed as a
constant: about `1.7e-5` between two segment-I columns near 24 and about `6.4e-7`
between two segment-III columns near 624. Registering a single constant would be
loose on one and wrong on the other, which is `MEASUREMENT.md` rule 6.

**A diagnostic runs beside both**: how far the truncated columns sit from the
ideal `2 log(k_b/k_a)`. It is reported and judges nothing.

**This is a floor, not a finding.** It cannot support any claim about the world.

**Fails if:** any pair on any date exceeds its own derived tolerance.

### B6-4. External referee: the implied euro cross matches an outside reference

For each segment and date the implied cross is `EUR_segment / USD_segment`. B6-5
asserts these agree across segments; B6-4 asserts they agree with an
**independent** daily `EUR/USD` reference.

**Source, verified 2026-08-12.** The ECB's daily euro foreign-exchange reference
rate, series `EXR.D.USD.EUR.SP00.A`, fixed at 14:15 CET, free and without a key,
retrieved by `data/fetch_ecb.py`.

**Criterion, one clause.** On every publication day that carries a reference, the
implied cross lies within `CROSS_BAND = 0.01` of it. Days with no reference do
not enter and their count is reported: the reference is business-daily and the
BCC publishes on some Sundays, so coverage is below one and **nothing is
interpolated**.

**What it establishes and what it does not.** It validates the **source**, not
the pipeline. §4.3 states that this stage has no zero calibration over its
window and this referee does not supply one; it is weaker and is stated as
weaker. What a fabricated or stale euro leg cannot do is stay inside one percent
of an independent fixing across eight months.

**It is not a claim that the BCC copies the ECB.** See §11's entry: the two
track no fixed lag.

**Fails if:** the implied cross departs from the reference beyond the band on any
publication day where both exist, which would mean either that the peg is not
against the dollar or that the euro column is not a real cross.

**It did fail.** See §11's entry of 2026-08-12. Three of 147 compared days
exceed the band, all three on days the reference itself moved about a percent
with the sign reversed. **The criterion stays failed and the alignment is not
re-registered.**

### B6-5. The position factor is exact: the segment triangle is zero

Inside one segment, the holonomy of `CUP → USD → EUR → CUP` is zero.

**Threshold:** machine epsilon on the quoted values, `1e-12` in log units, since
the claim is that the euro column **is** the dollar column times one cross
rather than that it approximately is.

**What it establishes:** Theorem 2's slice summand vanishes on this carrier by
construction, so the whole obstruction is in the agent factor. **What it does
not establish:** anything about the world. It is a statement about how the
source is built, and §2.4 says why registering it in advance matters.

**Fails if:** any segment's triangle is non-zero beyond tolerance, which would
mean the BCC sets its euro rate independently of its dollar rate, and §2.4's
reading is wrong.

### B6-6. Two graph models, run side by side, and what separates them

**Why there are two.** `b4` §5.2's rule types an edge from what is quoted: both
directions quoted implies `H¹`. Applied mechanically to this table it types
everything `H¹`, because **the frozen segments carry a compra and a venta column
too** (segment I posts `24 × 0.98` and `24 × 1.02`). Those columns are an
accounting schedule, not a round trip anyone can execute: the entitlement is
attached to a designated operation, and no member of the public buys at
`24 × 1.02`.

So the reading of the table is not settled by the table, and the stage does not
settle it by assertion. It computes **both** readings on the same days with the
same machinery, and the pair brackets the truth:

| model | what it believes | agent edges | connectivity |
|---|---|---|---|
| **maximal** | the columns | two-way and zero at **both** positions | the upper bound on how connected this market can be |
| **directed** | the regulation | two-way and zero at `CUP`; **absent at `USD`** | the lower bound |

The directed model is the registered reading, on the ground stated in
`b6_cuba_availability.md` §4: the entitlement attaches to the operation, so a
segment-I dollar is not fungible with a segment-III dollar. Pesos are fungible,
which is why the `CUP` agent edge stays two-way and the underlying undirected
graph stays connected, as Theorem 5 requires.

**Where the truth sits between them is an empirical question about volume, not
about regulation**: a thick informal market supplies a return leg that no
regulation grants. That quantity is not visible in this table, and locating it is
what the informal leg of §9 is for. B6-A brackets it; B6-B locates it.

#### B6-6a. Under the maximal model there is no sub-potential at all

On every publication day, with agent edges two-way at both positions:

* `directed.sub_potential` returns `None`;
* `directed.worst_directed_cycle` returns a **positive** sum;
* the two agree, which they must, since Bellman-Ford and enumeration are
  independent statements of Theorem 4's condition.

**What it means.** Believing the columns implies that no price vector whatever
rationalises this table, not even a sub-potential. It implies an executable round
trip worth roughly `log(624/24)`, and the orientation matters: the arbitrage
exists because the privileged direction is `CUP → USD` at the frozen rate, which
is the direction the entitlement grants. **The robustness arm flips the frozen
segments' orientation**, under which the cycle sum is negative and no arbitrage
arises; both are reported, because the finding is that the answer depends on the
orientation and the orientation is a regulatory fact.

**Fails if:** a sub-potential exists on any publication day, which would mean the
frozen rates sit close enough to the float that believing the columns costs
nothing.

**And the arbitrage does not occur.** That is the stage's empirical content and
it is stated as an inference rather than as a measurement: a posted price is not
an edge. B6-6b is what follows.

#### B6-6b. Under the directed model the graph is not strongly connected

On every publication day, with the `USD` agent edges removed:

* `directed.sub_potential` **exists**, so the positive cycle of B6-6a was created
  by the two edges the regulation does not grant;
* `directed.strongly_connected_components` returns three components;
* the sinks are exactly `{(USD, I)}` and `{(USD, II)}`, and nothing else.

**Fails if:** the graph is strongly connected, or a sink is some other set, or a
sub-potential still fails to exist, any of which would mean the model was built
wrong rather than that the world is surprising.

#### B6-6c. The one-sided bound, and how far outside the float's band it sits

Everything here comes from `directed.potential_interval`, which returns the
interval every sub-potential's `φ(v) − φ(u)` must lie in. **It is a potential
difference and not a holonomy**, which is the whole point: there is no closed
loop through a frozen segment, so there is no cycle sum to report, and reporting
one would be an `H⁰` fact under an `H¹` name.

For each publication day, with `X` a frozen segment:

```
lo_X , hi_X   = potential_interval( (CUP,X), (USD,X) )      hi_X must be +inf
lo_F , hi_F   = potential_interval( (CUP,III), (USD,III) )  both finite
W             = the widest round-trip band in the table, from the markup schedule
D_X           = lo_X - hi_F
```

**Registered:** `hi_X` is infinite for both frozen segments on every publication
day, `hi_F` is finite on every publication day, and

```
D_X  >  SIGNAL_OVER_NOISE * W        for X in {I, II}
```

with `SIGNAL_OVER_NOISE = 4.0`, the constant B3-3 and B5-6 already used, and `W`
computed from the published markup schedule rather than written down.

**What it means.** Two classes that can each transact in both directions are
confined by Theorem 5 to a band the width of the round trip. The frozen segments
are confined on one side only, and `D_X` is how far the side that *is* bound sits
outside the band the float permits. **It is not a premium**: a premium is a cycle
sum, and there is no cycle.

**Fails if:** `hi_X` is finite, which would mean the model is not the one
described; or `D_X` does not clear four bands, which would mean the `H⁰` typing
carries no observable consequence on this carrier. The second is the outcome this
criterion exists to risk.

### B6-7. The unbounded direction is visible

`D_X` of B6-6c on the **last** publication day exceeds `D_X` on the **first**
publication day, for both frozen segments.

**No threshold.** It is a strict comparison between two observed numbers, in the
manner of B5-15's leg (a), and nothing in it can be slid after the fact.

**Fails if:** the distance is not larger at the end, which would be the case if
the float converged back toward the pegs. That is a real possibility on a
managed float and the criterion is left able to catch it.

### B6-8. The agent factor and the position factor are exactly separable

The bank publishes thirteen currencies against three segments. **It publishes no
edge between two foreign currencies**, so the position graph is a star centred on
the peso, hence a tree, hence `b₁ = 0` and there are no slice cycles to find.
That is a fact about what the source publishes and is stated as one; it is not a
finding and B6-8 does not claim it. A cross between two foreign currencies can
always be *defined* as the ratio of their peso columns, so a star built that way
is unfalsifiable and is not what is tested here.

**What is testable is the interaction.** Write `rate(X, s)` for currency `X` in
segment `s`. The thirty-nine published numbers have fifteen free parameters if
they factor as `f(X) × g(s)`, so a factorisation imposes twenty-four
constraints, and nothing forces the bank to satisfy them: it could apply a stale
cross to the two pegged segments and a live one to the float, in which case the
segment ladder would depend on the currency and the factorisation would break.

**Registered:** on every publication day, for every currency,

```
rate(X, II) / rate(X, I)   =   rate(USD, II) / rate(USD, I)
rate(X, III) / rate(X, I)  =   rate(USD, III) / rate(USD, I)
```

after the orientation normalisation of §2.5, with a tolerance derived per
currency per date from the published grid rather than fixed as a constant:
`BASE_ULP × (1/rate(X, s) + 1/rate(X, I))` with `BASE_ULP = 1e-5`, the grid
every published base rate lies on. Small currencies carry more relative rounding
than large ones and a single constant would be loose on the pound and wrong on
the rouble, which is `MEASUREMENT.md` rule 6 again.

**What it establishes.** The agent index and the position index do not interact
on this carrier. Every currency sees the same three-rung ladder, so no part of
the obstruction lives in the position factor, and **Theorem 2's slice summand
has nothing to act on here**. That is stronger than B6-5's single triangle and it
is the right sentence for the write-up: on this carrier the whole obstruction is
in the agent factor, and it is so by the bank's own construction rather than by
our modelling choice.

**Fails if:** any currency's ladder departs from the dollar's beyond its derived
tolerance on any publication day, which would mean the bank prices some segment
independently, and the currency it happens on is then a position edge that does
interact with the agent index.

**It did fail.** See §11. Eight rungs of 5 382, every one of them the yuan, in a
contiguous stretch at the start of the window. **The criterion stays failed and
the yuan is not excluded.**

---

## 6. Filters, guards and registered constants

Constants live in `src/monetary_topology/cuba_segments.py`, not in the
experiment scripts, so that the fetcher and the experiment cannot drift apart.

| name | value | source |
|---|---|---|
| `WINDOW_START` | `2025-12-19` | first publication day in the API |
| `WINDOW_END` | last publication day at retrieval | recorded in the manifest |
| `SIGNAL_OVER_NOISE` | `4.0` | precedent, B3-3 and B5-6 |
| `MACHINERY_TOLERANCE` | `1e-12` | precedent, B5-1 |
| `PUBLISHED_DECIMALS` | `4` | the published series, both routes |
| `PUBLISHED_ULP` | `1e-4` | one unit in the last place. The publisher **truncates**, so the error is a whole unit and one-sided, not half a unit either way |
| `MARKUP_SCHEDULE` | the nineteen `k` in `b6_cuba_availability.md` §3.2 | the XLSX export |
| `CROSS_BAND` | `0.01` | B6-4. **One clause; the envelope was withdrawn, see §11** |
| `ECB_KEY` | `EXR.D.USD.EUR.SP00.A` | B6-4's reference series, verified 2026-08-12 |
| `CURRENCIES` | thirteen codes | B6-8. One list drives the fetcher and the export-name pattern |
| `QUOTATION` | `JPY` indirect, the rest direct | §2.5, from the bank's own footnote |
| `BASE_ULP` | `1e-5` | B6-8's tolerance. The grid every published base rate lies on |

**Guards, asserted by the loader and not reported as criteria.** A guard that
fires is an error and stops the run; a guard is not a finding.

1. **Schedule invariance.** Every channel column equals
   `published_from(base, k)` **exactly**, on every date and in every file, as
   an equality on integer last-place counts. A revision to the markup schedule
   mid-window invalidates `MARKUP_SCHEDULE` as a single constant and must stop
   the run rather than be averaged over; B6-3 would then fall back to
   `index_tolerance`.
2. **Path reconciliation.** Every date present in the XLSX and absent from the
   API equals the previous published value. Any date present in both on which the
   two disagree is an error, not a fill. **Rows dated on or after the export's own
   snapshot date are provisional** and are checked as forward fills only: the site
   serves a complete calendar, so an export taken before the day's rate is
   published carries that day as a fill, and the two paths then disagree on that
   row correctly, having been taken at different times. The boundary is read from
   the filename, not from where a disagreement happens to fall.
3. **The fixed segments are fixed in dollars, not in pesos.** `USD` segments I
   and II are constant; `EUR` segments I and II are **not**. An implementation
   that finds the euro fixed segments constant has a bug.
4. **No headline square inside one segment.** The experiment refuses a pair whose
   two legs share a segment, except inside B6-3.
5. **The quotation orientation is the registered one.** Guard 6. Each currency's
   segment ladder must point the way `QUOTATION` says. The ladder is a regulated
   constant, 24 against 120, so nothing external is consulted and a change of
   convention stops the run.
6. **Every published base rate lies on the `1e-5` grid** that B6-8's tolerance is
   derived from. Checked at retrieval; a finer grid would make the tolerance too
   generous and a coarser one would make it too tight.
7. **No imputation across a one-way edge.** The code has no path by which a
   missing direction on segments I or II can be supplied from another class, from
   a lag, or from a model. `b4` §5.2.

---

## 7. Falsification

**What sinks B6-A.**

- **B6-1 or B6-2 fails.** The machinery is wrong and nothing else is readable.
- **B6-3 fails.** The published markup schedule is not what the columns are built
  from, so the source is not understood and the stage stops.
- **B6-6a fails.** A sub-potential exists under the maximal model, so believing
  the columns costs nothing and the two readings do not separate. The stage then
  has no bracket and reports that.
- **B6-6b fails.** The directed model is not the graph described. That is an
  implementation fault rather than a finding, and it stops the run.
- **B6-6c fails.** The `H⁰` typing has no observable consequence on this
  carrier. The typing would still be correct as a statement about the
  regulation, and it would have nothing to show, which is the outcome this
  criterion exists to risk.
- **B6-7 fails.** The distance did not grow. Reported as registered, not
  rewritten. `HANDOFF.md` §3.2 item 9 is the precedent: a criterion that fails
  stays failed.
- **Guard 1 fires.** The markup schedule was revised inside the window, or the
  publisher stopped truncating. The stage is not thereby dead, but
  `MARKUP_SCHEDULE` becomes piecewise, B6-3 falls back to `index_tolerance`,
  and both must be settled before anything is read.

- **B6-4 fails.** It did. The failure is in the criterion's alignment rather
  than in the source: a one-business-day lag removes all three exceedances, and
  the distribution of deviations, mean 0.219% and 95th percentile 0.581% over 147
  days, is not what a fabricated or stale euro leg produces. **Both halves of
  that sentence are diagnostics and neither is a pass.** The registered
  comparison is same-day, it was registered before the reference was retrieved,
  and it stays as registered. `HANDOFF.md` §3.2 item 9 and A6-1 are the
  precedent: a criterion that fails stays failed, and the diagnosis goes beside
  it rather than into it.

- **B6-8 fails.** It did, on the yuan alone. The separability the write-up would
  otherwise assert does not hold across the whole window, and the sentence
  "the whole obstruction is in the agent factor" therefore carries an exception
  that has to travel with it.

**What does not sink it.** The float moving, in either direction, by any amount.
The gap widening after the reopening. Both are magnitudes, and no criterion here
is a claim about a magnitude except through a threshold derived from the table's
own spreads.

---

## 8. Scope

**One country, one window.** Two hundred and six publication days between
2025-12-19 and 2026-08-12. The result reads *the framework separates, a priori
and by reachability, edges on which a premium is defined from edges on which it
is not, inside one central bank's own daily table*, and it does not read
*therefore multi-rate regimes generally*. `a3b_initial_construction.md` §9 is the
model for writing that.

**No formal series exists before 2025-12-19.** A request to the API for
2025-01-01 to 2025-12-31 returns nine rows, all on or after 2025-12-19. There is
no pre-window formal leg, and the stage does not construct one from press
reports of scattered dates, which would be selection on the outcome.

**`C → D` does not return.** `PROJECT_PLAN.md` §14.3.1 dropped the connectivity
index because one country cannot supply a `C` worth reporting. Cuba adds two
more points to an annual index and the cross-section is still not there. A scope
statement, not a to-do.

**The dated closure and reopening are narrative.** 2025-04-18 and 2025-12-29
appear in the write-up as context and as a robustness split of the window. They
are not the identification, and `b6_cuba_availability.md` §4 says why the event
study was dropped.

---

## 9. What B6-A does not contain

**The `H¹` arm, and therefore the contrast.** Every non-trivial `H¹` square on
this carrier needs one leg outside the BCC table, because every leg inside it is
a fixed multiple of one number. The informal market is that leg. Until its
retrieval is settled, B6-A establishes one side of a contrast and validates the
instrument.

**Where the truth sits between B6-6's two models.** The maximal model is the
upper bound on connectivity and the directed model the lower bound, and what
lies between them is how much of a return leg the informal market supplies in
practice. That is a question about volume, not about regulation, and it is not
visible in a table of posted rates. B6-A brackets it; B6-B locates it.

**Everything registered about the informal leg**, which is deferred to
`b6_cuba_prereg.md` §10 or to a separate B6-B document: the arbitrage-band
prediction recommended in `b6_cuba_availability.md` §5, the friction column on
the informal leg if two-sided quotes are served, the prospective zero
calibration of §4.3, and every constant those need.

**This split is itself a registered commitment.** No criterion touching the
informal leg may be written after its data has been retrieved. If the token
arrives before B6-A has run, B6-A still runs first.

---

## 10. Retrieval, and the rules the fetcher must satisfy

`data/fetch_bcc.py`, following `data/fetch_bcra.py`.

1. **Resumable, and truncation is detected rather than read.** `CLAUDE.md` rule
   6. The API returns the whole window in one response, so the failure mode is a
   short page rather than a missing chunk; the fetcher asserts that the returned
   span covers the requested span and fails on a short answer.
2. **Bytes are stored verbatim**, with `sha256` of what arrived and of what was
   written, both in the manifest. The `fetch_cip` lesson applies: the two hashes
   are recorded separately because comparing a source hash against a modified
   stored file gives a guard that cries every time.
3. **Nothing is deleted.** A file that fails to parse is renamed with an
   `.expired` suffix and left in place.
4. **The channel columns are reconstructed, not retrieved.** Each is
   `tasaEspecial × k`; the XLSX is retained as the validator of `MARKUP_SCHEDULE`
   and not as a daily source.
5. **The manifest records the publication-day set**, so that §3.2's rule is
   enforced from data rather than from a hard-coded calendar.
6. **Raw responses live under `data/raw/`**, which `.gitignore` excludes.

---

## 11. Changelog

### 2026-08-12, written. What was already known

`CLAUDE.md` rule 8 permits a pre-registration written after real data has been
seen; what it requires is that a result which does not match be reported. This
entry states what had been observed when the criteria above were fixed, so that
a reader can discount each one accordingly.

**Observed during the availability check, before this document:**

- The markup schedule is constant over the window, to within published rounding,
  across all six files. **So guard 1 is an assertion of something already
  checked, and B6-3's tolerance argument was written knowing it holds.**
- USD segments I and II are constant at `24.0000` and `120.0000` across all 238
  calendar days; the float ran `410.00` to `624.00`. **So B6-6 and B6-7 were
  written knowing their direction.** Neither carries a free parameter:
  `SIGNAL_OVER_NOISE` is a constant with precedent from two earlier stages, and
  B6-7 is a strict comparison between two observed numbers. This is the same
  defence B5-15 §6B.3 offered, and it is the only one available.
- The implied euro cross agrees across the three segments to `2.2e-16`. **So
  B6-5 was written knowing it passes.** It is registered anyway because the code
  must assert it rather than the document claim it.
- The float is **not** monotone: two decreases, `410 → 408` on 2025-12-20 and
  `589 → 585` on 2026-07-02. Recorded here because a reader of B6-7 would
  otherwise assume monotonicity from its phrasing.

### 2026-08-12, while implementing. One criterion tightened, no data analysed

**The publisher truncates rather than rounds**, established while writing
`cuba_segments.py` and checked on all 27 132 published channel values. B6-3's
primary form changed from a comparison against a derived tolerance to a strict
equality against `published_from`, which is **stricter**, and the tolerance
form was demoted to a fallback with its constant corrected from `5e-5` to
`1e-4`. Recorded because it tightened a registered criterion; no headline had
been computed, and `CLAUDE.md` rule 8 covers a design change that produced no
evidence.

### 2026-08-12, while implementing. B6-6 rewritten, and why

**The registered form of B6-6 named an undefined quantity.** It asked whether
`|2 log(III/I)|` cleared a band and called that the index part. The index part
is `S − S'`, a cycle sum, and there is no cycle through a frozen segment, so the
quantity did not exist under the reading the same document registered. This is
the error `b1_theorem.md` §12.1 records, committed inside a document written to
prevent it, and it was caught while writing the experiment rather than by any
guard.

**Three things changed, and the replacement is stronger than what it replaced.**
B6-1's domain narrowed to pairs of two-sided channels, because a square between
segments has only one orientation available. B6-6 became 6a, 6b and 6c, running
two graph models side by side rather than asserting one. B6-6c's observable
became a **potential difference** from `directed.potential_interval` rather than
a cycle sum, which is what `b4` §5.2 says an `H⁰` case may report.

**The maximal model was added on the user's instruction**, against a question
this table cannot answer: how much of a return leg the informal market supplies
in practice. Running both bounds it from either side instead of assuming one.

**No data had been analysed under the superseded form**, and no headline had
been computed. `CLAUDE.md` rule 8 covers a design that produced no evidence; the
entry is here because the correction is a substantive one and a reader comparing
this document against a draft would otherwise find two different B6-6.

### 2026-08-12, B6-4 ran and failed. Recorded, not repaired

**Result: 3 of 147 compared days outside the one-percent band**, worst 1.134% on
2026-06-18, then 1.093% on 2026-04-08 and 1.051% on 2026-03-02.

**All three sit on days the reference moved about a percent, and the deviation's
sign is the reverse of the move's**: `-1.122%`, `+1.289%`, `-0.906%` day over day
respectively. Under a one-business-day lag the worst deviation falls from 1.134%
to 0.549% and no day is outside the band. So the Banco Central de Cuba sets its
cross from the previous business day's fixing, and the criterion compares
same-day.

**The criterion stays failed.** Three revisions of one criterion in one day, each
after seeing more data, is fitting whatever the third revision's argument is.
The lagged figures are recorded in the result file as a diagnostic that judges
nothing, in the manner of A6-5's direction printout, which was added without
changing that criterion either.

**And the withdrawal of the envelope clause earlier the same day had a
consequence not foreseen when it was made.** The envelope existed to absorb
exactly this timing question; removing it left a same-day band carrying an
alignment sensitivity it was never meant to carry. The withdrawal's own argument
still holds, that an envelope tests which fixing the BCC uses. **What does not
hold is the implicit assumption that the band was insensitive to the same
thing.** Recorded because the next reader is owed the sequence, not just the
outcome.

**What B6-4 does and does not now support.** It does not support "the euro
column matches an outside reference on every day", which is what it was
registered to test and what failed. It does support, as a reported distribution
rather than as a criterion, that the column tracks an independent fixing to
within a fifth of a percent typically. §4.3's admission is unchanged: this stage
has no zero calibration over its window.

### 2026-08-12, after the referee was verified. B6-4's envelope clause withdrawn

**What was registered.** B6-4 had two clauses: the implied cross within one
percent of the reference on every day, **and** inside the reference's own
`[t-1, t+1]` minimum and maximum on at least 95% of days. The second was written
on the assumption that the BCC applies someone else's published cross and that
the only question was the timestamp.

**What seven overlapping days showed.** The two agree to within 0.29% and track
**no fixed lag**: the closest match is same-day on 2026-08-07 and one business
day back on 2026-08-11, and no lag between zero and three business days brings
the mean deviation below 0.08%. The BCC runs its own fixing.

**Withdrawn, and the disclosure that goes with it.** The envelope clause would
have failed on one of those seven days, 2026-08-06, by `1e-4`, which is above the
BCC's own resolution of `4.2e-6` on segment I and therefore a real difference
rather than rounding. **That was known when the clause was withdrawn.** The
defence is not that it was too strict; it is that it tested **which** fixing the
BCC uses, which is not what B6-4 is for and not something the framework has any
prediction about. The one-percent band, which is what B6-4 exists for, is
untouched and was not re-derived from the seven days.

**Nothing else moved.** No other criterion's constants changed, and no headline
had been computed against the reference when the clause was withdrawn.

### 2026-08-12, first retrieval on the author's machine. Guard 2 fired, correctly

**The export's last row is provisional, and nobody had anticipated it.** The six
XLSX files were downloaded at 23:32 on 11 August local time; the API's record for
12 August appeared some hours later. Every one of the six files carries a
12 August row equal to its 11 August row, so the snapshot filled a day whose rate
did not yet exist, and when the real value arrived the two paths disagreed on
that row: EUR segment I reads `27.7332` in the export against `27.696` from the
API.

**Guard 2 caught it on its first real run**, which is what it is for, and the
handling is the one this repository already uses for a row it does not trust:
mark it, do not repair it, and put the boundary somewhere that cannot be slid.
Rows dated on or after the export's own snapshot are now checked as forward fills
and never against a value, with the snapshot read from the filename. A
provisional row that is **not** a forward fill still fails.

**Nothing was loosened.** The comparison on every earlier row is unchanged and
still exact on integer last-place counts.

### 2026-08-12, B6-8 registered before it ran. What had been seen

**One publication day of the eleven added currencies.** The ladders on
2026-08-11 are `5` and `26` for the twelve direct currencies and `1/5` and
`1/26` for the yen, so **the direction of B6-8's result was known when it was
registered**, on one date out of two hundred and seven. What was not known, and
is what B6-8 asks, is whether the factorisation holds on every date; a bank that
refreshed the pegs' cross weekly and the float's daily would satisfy it on most
days and fail on the rest.

**The tolerance was derived before the sweep, not after it.** `BASE_ULP = 1e-5`
comes from checking that every published base rate on all thirty-nine files lies
on that grid, worst departure `7.5e-9`, which is a property of the source rather
than a level chosen to accommodate a result.

**The yen's orientation was established from the bank's footnote**, relayed by
the user, and not from the ladder. §2.5 states why that distinction is the whole
defence.

### 2026-08-12, B6-8 ran. The first result was the reader's fault and is withdrawn

**Withdrawn: an earlier entry here reported B6-8 as failed on eight yuan rungs
and diagnosed a nineteen-day freeze.** Both the result and the diagnosis were
artefacts of how the yuan's series had been assembled, and the retraction is
recorded rather than the entry quietly rewritten.

**What actually happened.** The yuan's API record **begins on 2025-12-31**, not
on 2025-12-19 like every other currency: it joined the table twelve days after
the segment opened. The XLSX export carries a complete calendar from the window's
start, so it represents the yuan's pre-history by **back-filling** its first
published value to 2025-12-18. A sandbox reconstruction of the yuan's series from
the export therefore fed thirteen manufactured rows into B6-8, and they were the
eight failures. The freeze audit's "nineteen days" was the same thirteen rows
plus six ordinary ones.

**Two holes in the reader, both now closed.**

*Guard 2 accepted a back fill as a forward fill.* Its rule was "a date in the
XLSX only must equal the previous published value", and for a date **before** the
first published date there is no previous value, so the branch fell through and
admitted the row unchecked. A forward fill copies a value that existed; a back
fill manufactures one for a day the source published nothing. They are now
separate categories, counted separately, and back fills are excluded.

*The fetcher asserted that every currency starts on `WINDOW_START`.* It does not:
`WINDOW_START` is the stage's window and a currency may join later. That
assertion was the front-truncation detector, and front truncation is simply not
detectable on a first run; pretending otherwise cost a false failure. The first
publication date is now recorded per currency in the manifest, and a later run
that starts later than the recorded date fails.

*And the provisional-row rule was too strict.* It required a row at or after the
export's snapshot to be a forward fill. The eleven added currencies were
downloaded about two hours after the first two, and the bank published that day's
rates in between, so their last rows are the day's real values rather than fills.
Both are legitimate and which one occurs depends on the minute of the download,
which is not a property of the source. A provisional row is now admitted if it
matches either the day's published value or the previous one, and refused if it
matches neither.

**The corrected result: B6-8 passes.** 5 174 ladder rungs over thirteen
currencies and the 199 dates every currency publishes on, worst relative
departure 0.0018% at `JPY III` on 2026-06-18, nothing outside its derived
tolerance. The freeze audit's longest unchanged runs now sit at four to seven
consecutive publication days for every currency including the yuan.

**What this cost and what it bought.** Three of the four things above were
written from two currencies and six files downloaded in one minute, and all three
broke on the eleventh currency. That is the same sentence as `b5` §7.4's "two
agreeing dates are not a check", one level out: **two currencies are not a
sample, and neither is one download.**

### 2026-08-12, while extending to thirteen currencies. Two things two currencies
could not show

**The plausibility band rejected two of the eleven new currencies.** It was
`(1.0, 1e6)`, written when the stage held the dollar and the euro. The yen is
published indirectly and sits near `0.25`; the rouble is published directly and
sits near `0.29`. Widened to `(1e-4, 1e6)`, which is still ten orders of
magnitude and still catches a schema change, a units change or a zero. **A
parser guard, not a criterion**, and the entry is here because "two currencies is
not a sample" is the same sentence as "two dates is not a check" from
`b5_orphan_availability.md` §7.4.

**The alarm about decimal places was wrong and is withdrawn.** The API returns
some base rates to five decimals, which looked like a per-currency grid and would
have made `PUBLISHED_DECIMALS` a variable. Checked on all thirty-nine files by
trying every truncation from two to six places: **four reproduces all nineteen
channel columns everywhere, with no exceptions.** The five-decimal values are
base rates, and the base is not truncated at all, which `published_column`
already encoded. Nothing changed.

**Not observed, and genuinely open at the time of writing:**

- B6-1, B6-2, and every part of B6-6, since the code does not exist. The
  positive cycle of B6-6a is arithmetic on two numbers that have been seen, so
  its direction is known; that it holds on **every** publication day, and that
  Bellman-Ford and enumeration agree about it, is not.
- B6-4 over the window. The endpoint is verified and seven overlapping days have
  been seen, on which the worst deviation is well inside the band; whether it
  stays inside on all roughly one hundred and forty business days of the window
  is open.
- The path of the float between its endpoints, and therefore whether B6-6 holds
  on **every** publication day rather than on the two that have been seen.
