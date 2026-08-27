# B5 availability check: what the orphan-currency stage would need, and what exists

**Not a pre-registration. A check, run before deciding whether to open a stage**,
as this project requires before a stage is opened. Same discipline as
`b3_slice_availability.md`, and for the same reason: the last time this project
assumed a source was reachable it was wrong in both directions, and both errors
surfaced inside the same check.

Run 2026-08-11. Written **after**
`docs/b4_directed_edges.md`, because B4 changes what has to be retrieved.

---

## 1. What B4 changed about the shopping list

Before B4 the stage would have measured a loop sum on a market with a wide
spread. B4 §5.1 shows that number is `S`, a mixture, and that the two halves must
be reported separately:

```
S + S'  =  2 [ ω̄_a + ω̄_b ]     the two classes' round-trip costs      REPORT BESIDE
S − S'  =  2 [ ŵ_a − ŵ_b ]      twice Theorem 1's square sum           THE HEADLINE
```

Working the definitions through to quoted numbers, with `rate` in local currency
per dollar and `bid < ask`:

```
ŵ(LCY → USD)   =  −log √(bid · ask)      the log geometric mid
ω̄(LCY → USD)   =  ½ log(bid / ask)  ≤ 0   minus half the log spread
```

so, for two classes `a` and `b` facing the **same** conversion,

```
S − S'  =  2 · log( mid_b / mid_a )       twice the log premium between the two rates
S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)
```

**Three consequences for retrieval, and the first is good news.**

**The headline needs only the two mid rates.** The spread cancels out of
`S − S'` by construction, so the index part is computable from the mid quotes
that every source publishes. B4's correction does not make the stage more
expensive; it makes it cheaper and it makes the number defensible.

**The friction column needs two-sided quotes.** `S + S'` is not the headline but
it must be reported beside it, so a source that publishes only a mid is
sufficient for the claim and insufficient for the paper.

**The `H⁰` claim needs a different kind of data entirely.** Theorem 5 is about
reachability, not about a number. It needs the **eligibility rule**: who is
permitted to make the conversion, stated in regulation, not inferred from
prices.

---

## 2. The cross-country parallel-rate panel is not free, and the route is rejected

The obvious design is a panel: parallel and official rates for thirty countries
over forty years. Checked, and it is the same wall B3 hit on raw forward points.

| source | what it has | status |
|---|---|---|
| Pick's *Currency Yearbook* / *World Currency Yearbook* | the canonical historical black-market series | out of print, not free, and ends in the 1990s |
| Cross-National Time-Series (CNTS) | free/black market rate, from Pick's | **subscription** |
| Global Financial Data | black-market rates for ~50 countries | **subscription** |
| Haver `INTDAILY` | some parallel rates | **subscription** |
| Ilzetzki–Reinhart–Rogoff (2019, 2021) | regime classification, anchor, "unified market analysis" capital-control index, monthly 1946–2019 | **free**, `ilzetzki.com/irr-data` |

**The IRR files are free and they are not a substitute.** They publish the
*classification* built from parallel rates, not the rate levels. And using the
IRR capital-control index as this stage's connectivity index `C` would be
**circular in exactly the way this stage's own rule prohibits**: the index is
constructed partly from whether a country has an active parallel market, which
is the thing `C` is supposed to predict. Recorded here so it is not reached for
later as a convenience.

**Route rejected.** A panel is not available on free data and no amount of
assembling gets around it.

---

## 3. Argentina is the carrier, and the reason is structural rather than convenience

Not a fallback from the panel. Argentina has the property the framework needs
and the panel does not: **several exchange rates in force at the same time, on
the same conversion, with eligibility fixed by regulation rather than by price.**

That is the agent index, written into law:

| rate | who is eligible | eligibility rule |
|---|---|---|
| **oficial** (BCRA Com. A 3500) | importers and, since April 2025, individuals | import licence, and formerly a USD 200 monthly cap |
| **MEP / bolsa** | anyone with a brokerage account | securities settlement, formerly a parking period |
| **CCL** (contado con liqui) | those able to settle abroad | offshore securities account |
| **tarjeta / turista** | card holders | **oficial × (1 + tax)**, a construction identity |
| **blue** | anyone, in cash | none |

**This is `b2_measurement.md`'s cell structure in a different market.** One
position pair, `ARS ↔ USD`, several classes of agent, terms differing by who the
agent is and not by what is being bought. The ruling that the orphan currency
measures **squares and not slices** is confirmed by the
shape rather than asserted: every one of these is many agents on one edge.

**And the `H⁰` claim has its own instances here**, kept separate per B4 §5.2:
the export surrender requirement is a directed edge, since an exporter must
convert dollars into pesos at the official rate and cannot convert back; the
former rule that buying MEP barred the official window for ninety days is a
directed edge in the agent factor.

### 3.1 What is free, and what each source is

| what | source | terms |
|---|---|---|
| oficial, daily, official | **BCRA** Comunicación A 3500 | free, the central bank, authoritative |
| blue / MEP / CCL / tarjeta, **bid and ask**, daily | `dolarapi.com`, `argentinadatos.com` (Ámbito Financiero quotes) | free, open source, **community-run** |
| MEP and CCL, reconstructible | BYMA bond prices | free, an exchange, more work |
| capital-account restrictiveness, annual | **IMF AREAER Online**, incl. the new **FARI** index | free, and it is outside price data |
| currency turnover, triennial | **BIS Triennial Survey** | free |
| payment shares | **SWIFT** monthly trackers | free |

**The community APIs are a step down and it has to be said at the top rather
than in a footnote**, the same admission `b3_slice_availability.md` §4 makes
about a derived series. The mitigation is that the oficial leg comes from the
central bank, so at least one side of every premium is authoritative, and that
Ámbito's quotes are cross-checkable against a second house.

---

## 4. The reason to run it at all: the government performed the intervention

This is what makes the stage worth opening, and it was not available when the
stage was first framed.

**On 14 April 2025 Argentina removed the cepo.** The USD 200 monthly cap ended,
individuals were permitted to buy at the official rate for the first time in six
years, and a band replaced the peg. **The eligibility rule was deleted; the
market was not.**

The gaps behaved accordingly. Where oficial, MEP and blue had stood far apart,
they converged to within a few percent, and by mid-2026 all three sit in the same
narrow range.

**So the agent-edge structure was switched off, on a known date, by someone who
was not us.** That is a `do()` on the exact object A3c had to simulate. The
registered differential prediction writes itself:

> **`S − S'` collapses at the intervention. `S + S'` does not.**

The index part is the eligibility rule and the rule was deleted. The friction
part is cash handling, inventory and counterparty risk in the informal market,
and none of that was deleted: the blue market still quotes `compra` and `venta`.

**Why the differential form is what makes this survive the confounding.** April
2025 also brought an IMF programme, a band regime and a devaluation, and any of
them moves the level of everything. But `S − S'` and `S + S'` are computed **on
the same days from the same four quotes**, so a confound that moves the peso
moves both. The framework predicts that **only one moves**. That is
`MEASUREMENT.md` rule 4 satisfied by a comparison rather than by an assumption,
and it is the reason to prefer this design over a level study that no amount of
controls would rescue.

**It can fail, and the failure is informative.** If the blue bid-ask collapses
along with the premium, the separation of §5.1 is not doing work on this carrier
and the stage says so.

---

## 5. The two arms that keep it honest

**Zero calibration.** Two quote sources for the **same** rate — Ámbito's blue
against a second house's blue — are the same agent class reported twice. The
index part must be indistinguishable from zero. Built from independent
re-execution rather than from aliasing, which is the rule `MEASUREMENT.md` fixed
after the `0.975` incident.

**Known-answer arm.** `dólar tarjeta` is `oficial × (1 + tax)` by regulation. Its
index part against `oficial` must equal `2 log(1 + tax)` and nothing else, with
the tax rate read from the regulation rather than fitted. A pipeline that returns
anything else is broken before the headline is read.

---

## 6. What this check does not settle, and hands to the pre-registration

**The scope statement.** One country is one country. The result would read *the
structure of loop A appears in a second, unrelated market and survives the
removal of the mechanism that generates it*, and it would not read *therefore
this holds across emerging markets*. `a3b_initial_construction.md` §9 is the
model for how to write that.

**Whether the `H⁰` claim gets its own arm or waits.** Theorem 5 gives it a
precise statement, but the surrender requirement is a regulation rather than a
series, and turning it into a measurement is design work that this check has not
done.

**The connectivity index.** AREAER's FARI is annual and Argentina-only would give
a handful of points. `C` may not be reachable in a form worth reporting on a
single country, in which case §9.6's requirement is satisfied vacuously and the
`C → D` half of the original orphan-currency concept is dropped rather than
faked.

**Cost.** Two daily series over roughly 2019–2026, a few thousand rows.
`.gitignore` already excludes `data/raw/*`; the fetcher must be resumable and
must detect truncation, which this repository requires of anything that
downloads: retrieved data is treated as non-regenerable.

---

## 7. Endpoint verification, and four corrections to a proposed source list

An external suggestion (Gemini, relayed 2026-08-11) proposed four routes. One is
an improvement and is adopted; three do not deliver what they were invoked for.
Recorded with reasons, because the reasons are design constraints.

### 7.1 Adopted: Ámbito's underlying JSON, which removes a dependency

**The proposed URL was wrong** — `ambito.com/agrupadores/datos-dolar-historico`
is a page, not an interface. The working endpoint is

```
https://mercados.ambito.com/<series>/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>
```

Verified 2026-08-11, returning JSON arrays with a header row, `DD/MM/YYYY` dates
and **comma decimal separators**.

| series path | fields returned | usable for |
|---|---|---|
| `dolar/oficial` | `Fecha, Compra, Venta` | headline **and** friction |
| `dolar/informal` | `Fecha, Compra, Venta` | headline **and** friction |
| `dolarrava/mep` | `Fecha, **Referencia**` | headline only |
| `dolarrava/ccl` | `Fecha, Referencia` (same shape) | headline only |

**This is an upgrade over `dolarapi.com` and is adopted**: the community wrappers
scrape this, so calling it directly removes an intermediary without losing
anything. It does not change the provenance tier — Ámbito is a newspaper, not a
central bank — and §3.1's admission stands unchanged.

### 7.2 **MEP and CCL have no bid and ask, and that is not a gap in the source**

`dolarrava/mep` returns a single `Referencia`. That is correct rather than
deficient: MEP is a **ratio of two bond prices**, `AL30` in pesos against `AL30D`
in dollars, so it has no native two-sided quote. A spread for it would have to be
built from the four legs of the two bonds.

**Consequence for the design, and it is a real narrowing.** The friction column
`S + S'` is computable **only for the oficial–blue pair**. MEP and CCL can enter
the headline `S − S'`, which needs mids only, and cannot enter the column beside
it. The pre-registration states this rather than discovering it at write-up.

### 7.3 Rejected: Investing.com for MEP and CCL bid/ask

Invoked to supply the two-sided quotes §7.2 shows do not exist. Its historical
export is **OHLC, not bid and ask**, so it would not supply them even if they
did. Two failures in series, and the route is dropped.

### 7.4 Demoted, not adopted: Kaggle history dumps **of the Ámbito series**

Proposed as a historical baseline to avoid rate limits. **A Kaggle CSV is a third
party's scrape of the endpoint in §7.1, with no published construction and behind
an account.** That is strictly worse provenance than the thing it copies, and
convenience is the wrong reason to accept a step down when the original is
reachable. `b3_slice_availability.md` §4's rule applies: auditable beats
convenient. Rate limiting is a fetcher problem, and every fetcher in this
repository is already required to be resumable.

**Amended 2026-08-11. The ruling above is conditional and the condition is in
its own text: "when the original is reachable."** It was written about the
Ámbito series, where the original *is* reachable, and it does not extend to
sources where it is not.

**It therefore does not bar a Kaggle dump for the P2P leg**, where Binance
publishes no historical interface at all, only current order-book depth. There
the dump is not a step down from a reachable original; it is the only record
that exists. The general principle stands and is narrower than it first read:
*prefer the original where there is one*, not *refuse third-party collection*.
This project scrapes a newspaper's internal endpoint for four of its series, so
a blanket objection to third-party collection would rule out most of the stage.

**What a third-party dump still owes, and this is definitional rather than a
provenance complaint.** Any P2P series adopted must state, in `data/SOURCES.md`
alongside every other source: which venue, which side of the book, what
aggregation over the day's orders, and at what hour it was sampled. Those are the
same four questions `SOURCES.md` asks of a government release. A series whose
construction cannot be stated cannot enter the headline, whoever collected it,
because `MEASUREMENT.md` §2 needs to know what the denominator is.

**And one condition the same day supplied, at cost.** The amended rule above was
tested within hours of being written. argentinadatos' `mayorista` series was
adopted as one half of the calibration arm on two hand-checked dates, and over
the window it turned out to **freeze**: an unchanged sell quote for up to 71 days,
flat at `365.45` through the 13 December 2023 devaluation while both Ámbito and
the central bank moved to about `800`. See `b5_orphan_prereg.md` §4.4.

**The lesson is not that third-party collection is bad.** The same publisher's
`tarjeta` series tracked that devaluation correctly, so the fault is in one
series rather than in the collector. The lesson is narrower and it is now a
condition on the amendment:

> **A third-party series may be adopted, and must be checked against an
> independent referee over the whole window before it carries anything.** Two
> agreeing dates are not a check. Here the referee was BCRA's A 3500, which the
> stage already retrieves, and the check cost one experiment run.

This is the same discipline `MEASUREMENT.md` rule 7 applies to measurements,
moved one level out to sources.

### 7.5 Corrected: the known-answer arm's tax schedule

The proposal hard-codes "30% PAIS plus a 30%/45% income-tax perception". **That
is the schedule before 23 December 2024.** The PAIS tax ended on that date; the
30% perception on account of income and wealth tax was retained by ARCA
Resolución General 5617/24; residual provisions were formally cleared on 2
January 2026.

The stage's window opens after that, so **the constant is `1.30` throughout**,
which makes the arm cleaner than a piecewise schedule would: the index part of
`tarjeta` against `oficial` must equal `2 log 1.30` on every day in the window,
read from the regulation and never fitted.

### 7.6 An unresolved problem with the friction column, found while verifying

Ámbito's `dolar/oficial` returns e.g. `1071.36 / 1125.54` on 22 April 2025, a
gap near five percent. **A central bank's reference rate does not have a five
percent dealer spread.** This is a range across retail bank counters, so reading
it as `ω̄` would put **dispersion across banks** into a quantity B4 defines as
**one agent's round-trip cost**. That is the agent index leaking into the
friction term, which inverts the whole point of §5.1's separation.

**Ruled: the single named dealer.** The headline mid comes from **BCRA Com. A
3500**; the friction term comes from **Banco de la Nación Argentina**'s own
posted counter rates. BNA is one legal entity quoting both sides of one
conversion, which is what `ω̄` is defined to be, and it keeps the friction column
structurally symmetric with the blue leg, which is also a single-market
two-sided quote. The cheaper alternative — report the friction column for the
blue leg only — is rejected because an asymmetric column invites the reader to
compare two things that were not measured the same way.

### 7.6b The 23 April 2025 row, and why the fetcher must not repair it

`dolar/oficial` reads `1251.44 / 1333.24` on 23 April 2025 between neighbours
near `1100`, a jump of roughly fifteen percent and back. Three candidates: a
composition change in what Ámbito was averaging, a bad row, or a real liquidity
event three weeks into a new float.

**A proposal to resolve it automatically, by fetching news for the day and
substituting BNA's rate when the row looks bad, is rejected.** Two reasons.

**Substitution is repair, and repair is what this project forbids.** Replacing a
value in one series with a value from another silently changes what the series
is, and the change is invisible downstream. **This repository does not repair**,
and the rule applies to values as much as to files: leave it in place, mark it,
and make the code ignore what it should not read.

**A jump filter cannot tell the third candidate from the first two, and in this
window it will fire on real moves.** The stage's whole subject is a period when
the peso genuinely moved in double digits. A threshold that flags those is
measuring volatility, not data quality.

**Ruled**: the fetcher records a `DataAnomaly` for any row whose one-day mid
change exceeds a registered threshold, writes it to the manifest, and **changes
nothing**. The threshold's only job is to populate a list. The headline is then
computed **twice, with and without the flagged rows**, and both numbers are
reported. If they differ materially, that is the finding rather than a problem to
be cleaned away.

### 7.7b P2P is a fourth agent class, not a second reporter

Proposed: use Binance P2P or another crypto `ARS/USDT` rate as source B of the
zero-calibration arm, on the grounds that its collection path is physically
independent of a cueva survey and therefore immune to media aliasing.

**The independence argument is right and the placement is wrong.** The zero arm
requires **one agent class measured twice**. A P2P venue is not the cueva class
observed by other means: it requires an exchange account, platform KYC, and
settlement rails a cash cueva does not use. **Eligibility differs, so by this
framework's own definition it is a different agent class and its index part
against blue is expected to be non-zero.** Putting it in the zero arm means a
non-zero result cannot be read: alias failure and genuine agent-index difference
would look identical, and the arm loses the one thing it exists to do.

**Ruled, and it is a promotion rather than a rejection**: `ARS/USDT` P2P enters
the **headline as a fifth class**, alongside oficial, MEP, CCL and blue. It is
the most interesting one available, because its eligibility rule is a platform
account rather than a state licence, so it is the one class whose access the
April 2025 intervention did **not** change. That makes it a within-design control
the other classes cannot supply.

**And the zero arm gets a construction that actually satisfies it**: **BNA's own
published rate against a third party's report of BNA's rate.** One dealer, one
counter, one conversion, two independent collection paths. The index part must be
exactly zero, and a non-zero result can only be a reporting failure, which is
what a zero calibration is for.

### 7.7 Aliasing risk in the zero-calibration arm

**If two outlets republish the same survey rather than polling their own
sources, the two series are one series and the arm is aliasing, not independent
re-execution.** That is the failure `MEASUREMENT.md` fixed after the `0.975`
incident.

**Adopted, as a pre-flight assertion rather than an assumption**: before either
pair counts as independent, run a co-movement test. Two series that are one
series will show same-day identical changes on nearly every day and identical
trailing digits. **Registered rule: if the two agree to the last quoted digit on
more than a registered share of days, they are one source and the arm does not
run.** The threshold and the share are fixed in the pre-registration, and the
test is run on the pair actually used rather than assumed away.

---

## 8. Verdict

**Open the stage, with the scope narrowed from what was first envisaged.**

Dropped: the cross-country parallel-rate panel, not free.
Dropped: `C → D`, unless a form of `C` survives §6.
Kept and sharpened: **the square structure in a second market**, with the index
part separated from the friction part per B4, and with the April 2025 removal of
the cepo as a differential test that this project did not have to run itself.
