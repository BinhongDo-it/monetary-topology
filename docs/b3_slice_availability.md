# B3 availability check: can the slice summand be reached on free data?

**Not a pre-registration. A check, run before deciding whether to open a stage**,
as `PROJECT_PLAN.md` §13.5 requires: "项目到目前为止全部跑在免费政府数据上。FX 会打破
这一点 … 开工前先做可得性核查，不要假设." (*Everything so far has run on free
government data. FX would break that. Run an availability check before opening
the stage; do not assume.*)

Run 2026-08-10.

---

## 1. Why the question is worth asking at all

Theorem 2 splits the obstruction into **slice cycles** — one agent traversing
several positions — and **squares** — two agents on the same pair of positions.
Corollary 2 is the operative fact: **stage B2 reaches squares and nothing else,
no matter how large the sample**, because a mortgage applicant is observed at one
transition. The slice summand has never been measured by this project.

`b1_theorem.md` §9 names covered interest parity deviations as the available
carrier whose loop is traversed by a single agent, and warns that carry returns
are not that — they are compensation for bearing risk, and treating them as an
obstruction is a category error this project made once already on paper.

---

## 2. What was checked, and what each route turned out to be

### 2.1 Raw FX forward points — **not free**

Every study in this literature sources forward points from Bloomberg or
Refinitiv. `Du, Keerati and Schreger (2025)` state the constraint directly: **"By
Bloomberg's licensing agreement, we cannot publish the raw data."** CME publishes
current-day settlements free but historical bulk sits behind DataMine, a
commercial product. FRED carries interest-rate swap rates and spot FX; it does
not carry FX forward points or a cross-currency basis.

### 2.2 Retail broker "swap" rates — **a category error, not a source**

Dukascopy and similar venues publish free historical data, and it was suggested
as a route. It is **rolling spot forex**, a contract for difference, with
**overnight rollover swap rates**. A broker's rollover charge is a financing fee
on a CFD and carries the broker's markup; it is not the interbank forward point.
Using it as one would repeat, in a new place, exactly the error §9 warns about.
**Rejected.**

### 2.3 The Du–Keerati–Schreger CIP dataset — **free, maintained, and it works**

`https://sites.google.com/view/jschreger/CIP`

| | |
|---|---|
| file | `cip_dataset_v4.csv` (also Stata), direct download, no registration |
| version | **V4, October 2025**, with V1–V3 archived back to June 2018 |
| coverage | **2000–2025**, 10 developed and 18 emerging markets |
| maturities | 3M, 1Y, 2Y, 3Y, 5Y, 10Y, 20Y, 30Y |
| published series | `cip_govt` (the deviation, bp), `rho` (**market-implied forward premium**), `diff_y` (government bond yield differential) |
| robustness pair | `rho_ibor` / `rho_sofr` and `cip_govt_ibor` / `cip_govt_sofr`, with the transition date published per tenor-currency pair |
| construction | ticker list and reproduction instructions published as a separate spreadsheet, plus a data appendix |

**`rho` is the leg this project needs and it is published.** The raw forwards are
not, and cannot be, but the forward premium derived from them is.

---

## 3. Is it the right shape?

**Yes, and it is worth being exact about why.** The measured object is

```
x_govt(i, n, t)  =  y_govt(i, n, t)  −  ρ(i, n, t)  −  y_govt(USD, n, t)
```

A dollar investor holds USD, converts at spot into currency `i`, buys the
`i`-government bond, hedges the currency forward, and returns to USD — against
simply holding the Treasury. **One agent, four positions, loop closes.** That is
the slice shape §9 asks for, and it is not a carry return: the currency risk is
hedged, so the sum is not compensation for bearing it.

Two further properties the check did not expect to find:

**The position graph has real structure.** Eight maturities and twenty-eight
countries means `G` is not a tree. One can ask whether the field is exact
**across maturities** at a fixed country, or **across countries** at a fixed
maturity, and those are genuine cycles rather than the single edge B2 works on.

**A graded placebo is already labelled in the data.** The appendix states that
emerging-market deviations are dominated by default risk and capital controls,
while for developed markets with negligible default risk and open capital
accounts they measure convenience yield and frictions. That is the same shape as
`b2_measurement.md` §8.1's conventional/FHA/VA placebo: a grouping rule that is
not the framework's variable, against which the measured quantity should move in
a stated direction.

---

## 4. The three costs, which are for the stage designer and not for this check

**It is a derived series, and that is a step down from B2.** This project
retrieved 20.1 million originations and applied filters fixed in advance, and the
one time that discipline lapsed it cost `0.975` (§11.2). Here the filters have
already been applied by someone else. The ticker list makes the construction
**auditable** but not **re-runnable** without a terminal, which is better than an
opaque series and worse than our own retrieval. Any stage built on this must say
so at the top rather than in a footnote.

**`b1_setup.md` §4's framing objection survives Theorem 2 untouched.** §4's
disposition is that FX "appears, if at all, as a short worked illustration … It
carries no result", and the reason was never mathematical: "a framework about
domestic stratification whose empirical section is about currency markets will be
read as a framework about currency markets." Theorem 2 shows FX is structurally
necessary to reach the second summand. It does not make the framing cost go away.
**Both statements are true and they pull in opposite directions.**

**The economic content is not Volume I's.** Theorem 2 says the two summands
"have different economic content", and this is what that means in practice: B2's
squares are two borrowers at one location and date on different terms — the agent
index, which is the stratification claim. The slice cycle here is one arbitrageur
across positions, and its drivers are default risk, convenience yield and market
segmentation. A result would read "**the price field is also non-exact in the
slice direction**", which completes Volume II's mathematics. It would not read
"and this too is stratification".

---

## 5. What this check withdraws

**An earlier conclusion reached during this check — that the slice summand is
"structurally unreachable on free data" and should be recorded as a permanent
limitation — is withdrawn.** It was reached after finding that raw forwards are
paywalled and before checking whether the derived forward premium is published
separately. It is, maintained, with a documented construction.

The remaining open item is different and is **not** solved by this dataset: the
domestic slice carrier. `b1_setup.md` §5's seven domestic constructions are all
square-shaped — same position, different agents — except the accreditation
threshold, which is a hole. **A domestic slice cycle needs a position graph with
a genuine cycle**, for instance `cash → dwelling → home-equity credit → cash`
walked by one household, and its plausibility as a non-zero loop rests on the
fact that the leg cannot be reversed — one cannot short one's own deposit — so it
is not an arbitrage that competition removes. **That is new design work and is
not specified anywhere in this repository.**

---

## 6. Retrieval, if a stage is opened

Fits the existing pattern exactly and needs no new infrastructure. `.gitignore`
already excludes `data/raw/*`; `data/SOURCES.md` is where retrieval is recorded;
This repository requires every fetch script to be resumable and to detect
truncation
rather than reading a damaged file silently. One CSV of moderate size, versioned
by the publisher, with three archived prior versions — so a manifest recording
the version, the URL and the retrieval date is sufficient and the download is
reproducible in a way the underlying Bloomberg pull is not.

Citation is required by the publisher and is recorded here so it is not
forgotten: Du, Keerati and Schreger (2025); Du, Im and Schreger (2018); Du and
Schreger (2016).

---

## 7. Ruling on the framing cost, and one correction that has to be made first

**The framing objection of `b1_setup.md` §4 is overruled.** Recorded here with
the reasons rather than quietly ignored, because §4 is a registered disposition.

Two reasons, and the second was not available when §4 was written.

**§4 predates Theorem 2.** When it was written FX was a convenient illustration
of pairwise structure, and paying a framing cost for convenience is a bad trade.
Theorem 2 changed that: the slice summand is a **structurally distinct half** of
the obstruction, and no volume of mortgage data reaches it. The trade is now a
framing cost against half the mathematics, which is a different trade.

**The two carriers close different objections, and this one has to be closed in
the venue where it is hardest.** B2 closes "the same position should carry the
same price". What it cannot close is "give the market time and arbitrage grinds
any non-integrability away". That objection is answered only where arbitrage is
sharpest — deepest liquidity, most transparent information, most professional
participants, and eighteen years of time already given. **A domestic carrier is
the weakest possible venue for that objection, not the strongest**, and a critic
can always reply that a domestic anomaly is a feature of that particular
industry's market. That reply is unanswerable by adding more domestic carriers.

### 7.1 The correction: a CIP deviation is not profit, and saying so would be fatal

The reasoning that produced the ruling above contained a phrase that must not
reach a draft: that the deviation is a **non-zero closed-loop net gain**, so
arbitrage has demonstrably failed.

**It is not a net gain.** The post-2008 account, well supported and effectively
standard, is that the deviation is the **shadow price of balance-sheet
capacity**: the arbitrage consumes balance sheet, leverage-ratio constraints make
balance sheet costly, and the deviation persists as compensation for a
constraint rather than as money left on the table. The title of BIS Working Paper
590 states it — *The failure of covered interest parity: FX hedging demand and
costly balance sheets*.

**Why this matters more than a wording quibble.** `PROJECT_PLAN.md` §10.2 records
this project getting the neighbouring case wrong once already: "carry trade 不是
非零环路和（那是风险补偿），只有 CIP 偏离是" (*the carry trade is not a non-zero
loop sum, since that is risk compensation; only the CIP deviation is*). Calling
the CIP deviation a profit re-imports that same category error one level up, and
a referee closes the section with one sentence: *that is the price of a
constraint, not free money*.

### 7.2 And the constraint explanation instantiates the framework rather than defeating it

**This must be registered before anything is run, not offered afterwards.**

If the basis is the shadow price of balance-sheet capacity, then what has been
shown is:

> **The price vector on positions is not a potential, and making it one requires
> a coordinate the price system does not carry.**

That is Volume II §1, verbatim in content: price is a scalar, the projection to
one dimension necessarily discards dimensions, and what matters lives in the
discarded ones. The obstruction is real and it sits exactly in a projected-away
coordinate.

So the stage's claim is **not** "there is unexploited profit in the deepest
market in the world". It is:

> On the position space as the price system states it, no global potential
> exists; the residual is the price of a constraint that the position space does
> not contain.

That is stronger, harder to dismiss, and it is the same shape as the mortgage
result — where the missing coordinate is who the borrower is, and here it is how
much balance sheet the trade consumes.

**Falsification is unaffected and is worth stating in the same breath**: if the
deviation can be made to vanish by adding a *published, position-level* price —
that is, if some scalar already quoted on positions accounts for it — then the
field was integrable on a space the price system does carry, and this stage
fails.
