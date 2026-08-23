# Volume II speedrun: what each station asked, what it answered, and what the evidence revised

**Part 1 of 3. Stations B0 through B6.** Part 2 covers B7 through B11, which are the three
carriers that produced the headline readings. Part 3 covers B12 through B14, which were built after
the programme knew what it was short of, and two of the three were built to be able to fail.

Every entry has the same four fields, in the same order. The third field is the point of the
document: a station whose own evidence never moved it has not been tested by anything.

Figures are quoted exactly as the record carries them. Where the record superseded itself, the
later reading is given and the earlier one is named as superseded.

---

## B overall

**Asked.** Can the effective terms of exchange in a real financial system be represented by one
globally consistent scalar price field? The test is the closed loop: additive separability of the
terms is equivalent to every closed cycle summing to zero, so a persistent non-zero cycle sum is a
measurement of non-integrability rather than an interpretation of dispersion.

**Answered.** **Four** carriers have produced measured non-zero cycle sums on real transaction data:
mortgage origination terms (B2, B7), **mortgage modification (B8, the strongest of the four)**,
cross-currency funding (B3), and the ETF creation triangle (B9).
Non-integrability is a quantity here, not a metaphor.

> **[2026-08-18 M-43 correction]** This read *"Three carriers"* and omitted B8, while the project
> ledger and the outward-facing note both say four with **B8 the strongest**. Part 1 covers B0–B6,
> so B8 has no station section here; **it is still counted, because this paragraph counts carriers,
> not sections.**

**Superseded.** The premise that any of these carriers is a zero domain (B9 §22.11). The
cross-carrier calibration `π`, which required a richer path space than any carrier supplied.
The claim that the mortgage carrier can never reach a slice cycle, which was scoped down to a
cross-section of originations rather than mortgages in general.

**Scope.** The four carriers do not add. `H⁰` (a hole: a transition that no price can complete)
and `H¹` (a curl: a cycle that does not close) are different objects and the record forbids
summing them. Each carrier is quoted with its own floor.

---

## B0 — what is and is not being claimed

*Theory. Scope-fixing. No measurement.*

**Asked.** If the field is non-integrable, what exactly follows, and what deliberately does not?

**Answered.** If `ω` carries a non-trivial cohomology class, no global scalar potential exists, and
therefore no objective can be globally realised by that coordination architecture through the price
mechanism. The claim needs one inequality on one cycle. It needs no interpersonal comparison, no
utility function, and no welfare criterion.

**What the reading licenses.** It is a statement about the arithmetic of a price field. The four
things it does not imply were written down before the stage ran, and none of them follows: that
central planning is better, that anyone is behaving badly, that the outcome is bad, or that markets
fail to clear.

**Scope.** The theorem is not the weak point, the identification is. The document names its own
single attack surface: whether the four-cycles measured are the relevant cycles of the actual
economy or an artefact of how the position space was carved. That is logged as assumption A1.

---

## B1 — is integrability a theorem of notation?

*Theory. Definition and proof. Self-declared: no data is analysed here.*

**Asked.** Is the field the claim is about a real two-index object, or does the whole question
dissolve into notation?

**Answered.** It dissolves on one index and survives on two. On a single-currency price vector
`log R_ij = log p_j − log p_i` is exactly a gradient, so on a price vector integrability is a
theorem of notation. The relevant field is `P(a, j)`, the effective cost to agent class `a` of
obtaining position `j`. Four results follow.

- **Theorem 1**, a four-way equivalence: a single price vector exists ⟺ `ω` is exact ⟺ holonomy
  vanishes ⟺ each `w_a` is exact *and* `w_a = w_b`.
- **Corollary 1**: one edge, one pair of classes with `w_a(i,j) ≠ w_b(i,j)`, and the single price
  vector is dead.
- **Theorem 2**: the cycle space splits into slice ⊕ square. Agent cycles contribute zero for any
  field.
- **Theorem 3**: `H = 2·Var(x)`. Stage B2's within-cell variance share **is** the square-component
  holonomy, not a proxy for it. Verified per cell and in aggregate to `1e-16` on a graph with
  **28 million vertices**.
- **Theorem 4** restates the square holonomy as `Δ_a Δ_g P`, which is the difference-in-differences
  estimand. A single non-zero interaction term decides the question.

**Superseded.** Four, and one of them is the most useful sentence in the station.

- The standing assertion `R > C` (renting costs more than owning) is withdrawn as **currently
  false**: 2026 data has average rent `$1,669` against average ownership cost `$2,589`, with
  ownership cheaper monthly in 23 of the 50 largest metros and renting cheaper in 27. The sign
  flipping by metro and by year is then re-read as *evidence*, because integrability requires
  **zero**, not positive.
- FX was demoted from headline carrier to pedagogical illustration, then that demotion was itself
  overruled by B3.
- The rule "deleted edge raises `dim H¹` iff the graph stays connected" is falsified by the
  project's own counterexample. Connectivity is necessary and is not sufficient.
- `§0`'s "Theorem 3 is the one that matters" is **superseded**. The standing order is Corollary 1,
  then Corollary 2, then Theorem 3, on the following reasoning: Theorem 3 is an algebraic identity,
  and a reader who wants to dismiss it can say the framework renamed an analysis of variance, and
  at the level of arithmetic be right.

**Scope.** Assumption A1 is where all the economics is: agent edges carry weight zero, meaning the
position trades at one price independent of who holds it. Where A1 fails (a non-assumable mortgage)
the graph disconnects, the square stops being a cycle, and Theorem 1 does not apply. If agent edges
carry `t ≠ 0`, Corollary 1 survives untouched but attribution does not: the sum can no longer be
assigned to price differences rather than transfer wedges.

### B1 §5 — hole taxonomy

*Computational verification on synthetic carriers.*

Deleting one interior edge of a filled 5×6 grid: `b₁` 20 → 19, `rank ∂₂` 20 → 18, `dim H¹`
**0 → 1**. A boundary edge: `dim H¹` 0 → 0. A dumbbell's bridge: components `c` **1 → 2**, which is
`H⁰` and not this station's object. One transition that was never observed is a hole, and missing
cells **raise** `dim H¹` rather than lowering it.

### B1-2 / B1-8 / B1-9 — checking the split instead of asserting it

B1-2 fires the squares and watches the slice cycles stay silent. Its own zeros are an artefact of
the constructors, and the record says so: a summand that is zero because nothing was ever put in it
has not been separated from anything. **B1-8 is the mirror**, and it is the one that closes the
gap: on a field shared across classes but not a gradient, slice cycles reach **15.0** while every
square sum is **exactly 0.0**, structurally rather than to a tolerance. B1-9 adds the two fields
together and recovers each summand **compared as raw bytes**, which is available only because the
fields are integer-valued. A decomposition that only nearly separates is a tolerance argument.

---

## B2 — mortgage origination: does the cost field carry an agent index?

*Empirical. HMDA modified LAR, 2018 onward, all states, 20,071,900 reported spreads.*

**Asked.** At the same quarter, census tract, tier, occupancy, lien and purpose, do two applicants
for materially the same financing receive materially different terms?

**Answered.** Within-cell share of rate-spread variance **0.7831** unrestricted, **0.8480** at
`min_size = 20`. In robust form, untouched by the correction below: median within-cell IQR
**0.5257** percentage points, median `p90 − p10` **1.0774** points, and **98.9%** of cells carry an
IQR above 25 basis points. A gradient field predicts exactly zero everywhere.

**Superseded.** Every variance share in the first run. The reported `0.9750000458` was the fraction
**39/40 exactly**: one row carrying a rate spread of `−9,999,997` sitting in a cell of forty loans,
with the magnitude cancelling out entirely. 160 rows lie outside `±20` and 115 outside `±50`, all
filer placeholders (`1111`, `99.99`, `100.0`, one `−968`), not a parsing fault. Two earlier
specification errors were withdrawn before retrieval: measuring only the vintage loop, and using
price tier as though it indexed the agent.

**Scope.** The estimate is a floor, and the censoring is worst exactly where it matters most:
all-cash buyers are the extreme favourable point of this loop and generate no HMDA record at all,
so dispersion is understated most in the markets with the highest cash share. Attribution to credit
score is impossible here because public HMDA redacts it. The plausibility band and `min_size` were
both added after the first result was read, which is why **0.7831** rather than 0.8480 is the number
to quote when one number is wanted.

### B2 loop B — the vintage wedge, and why the bigger number is the weaker evidence

*Empirical. A rigorous lower bound on binned NMDB data, 53 quarters, 2013 Q1 to 2026 Q1.*

**Asked.** Hold the dwelling fixed and vary the entry date: how large is the dispersion in carrying
cost across vintages?

**Answered.** All four predictions passed. Latest quarter **0.8479**, smallest **0.3018**
(2019 Q4), at or above loop A in **46 of 53** quarters, positive in **51 of 51** states, and
**2.52 times** loop A's within-cell variance. On a synthetic sample of known variance the
five-bucket bound recovers about **27%**, so the true dispersion is plausibly three to four times
what is reported.

**Superseded.** No falsification fired, but the framing was downgraded by B1's theorem, and the
elaborate original design (entry/holding/exit legs, imputed rent, a Hodge decomposition on
`(metro, tier, vintage)`) has no recorded result. It was executed instead as the bucket-variance
bound.

**Scope.** This is not evidence of non-integrability. A 3% mortgage cannot be transferred, so the
agent edge is absent, the graph disconnects in the agent direction, the square is not a cycle, and
the quantity is `H⁰` where loop A's is `H¹`. Stated in the record's own words: **a reader who takes
the 2.52 as the headline has been handed a number about `H⁰` and told a story about `H¹`.**

### B2-8.1 — the graded placebo

*Empirical. Registered before any VA or FHA data was retrieved, with the conventional figure
already fixed.*

Conventional within-share **0.8480** against VA **0.6666**, on a registered threshold of a gap
above 0.05. VA is the load-bearing comparison because its price grid removes the graded component
by programme rule. FHA discriminates nothing: both the pool-width account and the agent-index
account predict the same sign there.

### B2-PW — testing the premise the placebo asserts

*Empirical. 23.6 million loans across 409,181 tract-years common to all three programmes.*

**Asked.** Is the VA borrower pool at a fixed position actually as wide as the conventional pool?
If it is narrower, the conventional-VA gap appears with no agent index anywhere.

**Answered.** Six of nine criteria pass. Ranked income dispersion: conventional `0.05396`, VA
`0.05271`, ratio **0.9769**. Log income: ratio **0.5292** against a registered floor of `0.80`.
Conventional converts a unit of pool width into `6.336` units of rate dispersion against VA's
`5.168`.

**Superseded.** The first national run reported within-cell LTV dispersion of **91,970,479** for
conventional against 11,412 for VA, and an income maximum of `2,302,773`, which in HMDA's units is
an annual income of 2.3 billion dollars. Same failure family as loop A's `−9,999,997`. Two criteria
were restated before any figure existed: one had been written on a within *share*, which cannot
detect a rule-pinned variable at all.

**Scope.** The verdict **holds on the ranked measure and fails on the log measure**, and that split
is stable across every threshold and every plausibility band, so it is a property of the two
measures rather than of the sample. It must be reported as a split. Also: this measures capacity,
not credit, and nothing in it licenses a statement about credit scores.

---

## B3 — cross-currency funding: the first slice cycle

*Empirical. Du–Keerati–Schreger CIP dataset, 1,513,471 rows, 2000 to 2025.*

**Asked.** B1's Corollary 2 says the mortgage cross-section reaches squares and nothing else no
matter how large the sample. Is there a carrier for the *slice* summand, one agent traversing
several positions with the loop closed? And on it: do cross-currency cycles that never touch the US
Treasury vanish, as a single common convenience yield would require?

**Answered.** They do not vanish. All seven registered criteria pass. G10 cycle sums run
**30.9 basis points at 3 months rising to 45.6 at 10 years and 43.6 at 30 years**, against a
data-derived measurement floor of **2.8 to 3.7**. Signal over floor runs **63 to 200** across eight
tenors, against a registered requirement of 4. Nine of nine tenors exceed 25 bp. The degenerate
cycle reads `|z(i,i)| = 0.0e+00`. The sharpest single reading is CNH against CNY, the same currency
onshore and offshore: **66.2 to 169.0 bp** over seven tenors, at ratios of **6.7 to 1198** over the
floor, largest at the short end and decaying with maturity.

**Superseded.** Two, both before results. An earlier conclusion that the slice summand is
"structurally unreachable on free data" was withdrawn: it had been reached after finding raw
forwards paywalled and before checking whether the derived forward premium is published separately.
And a phrase the record flags as one that must not reach a draft: that the deviation is a non-zero
closed-loop **net gain**, so arbitrage has demonstrably failed. It is not a net gain. It is the
shadow price of balance-sheet capacity.

**Scope.** The G10 arm is the headline and the emerging-market arm is explicitly not evidence. Both
accounts predict a large EM number, and the band scan gives an independent second reason: across a
tenfold change in the outlier band G10 moves by one to three basis points while EM more than
doubles, so the EM number lives in the tail. This is also a derived series filtered by someone else,
which is a step down from B2 and has to be said at the top rather than in a footnote.

---

## B4 — one-way conversions, and a theorem that runs against the framework

*Theory. No data, no retrieval, no parameters.*

**Asked.** When a conversion runs one way only, does a non-zero directed loop sum still mean an
obstruction?

**Answered.** No, and the station says so plainly: **directedness helps the null.** A sub-potential
exists iff no directed cycle sums positive, which is strictly weaker than exactness, so "no global
potential" stops being the falsifiable statement. A raw non-zero round trip is not evidence,
because a bid-ask spread produces one with no obstruction anywhere. The station supplies the split
that rescues the measurement: on two-way edges `ω` decomposes uniquely into an index part and a
friction part, the directed square gives `S + S' ≤ 0` (friction) and `S − S'` (twice Theorem 1's
square sum, the index part). Eight of eight code checks pass, including a byte-level separation with
zero mismatches. A position that can be entered and not left is not priced by the system, and that
is `H⁰`.

**Superseded.** Two, both load-bearing. The summary table claimed the sub-potential is "unique up to
a constant"; the theorem does not say that and its proof does not show it. The error was confined to
the summary table, which is the part a reader sees first. And `PROJECT_PLAN.md` §9.5's claim that
the directed existence condition is stronger is **backwards**: one-way edges remove constraints.

**Scope.** **Theorem 2 does not generalise.** Directed cycles form a cone, not a vector space, so
the slice-versus-square accounting is available only on the two-way part of the world. B2's and
B3's results live there and nothing in this station extends them to one-way markets. Imputing a
missing direction is prohibited.

---

## B5 — Argentina: one conversion, several legal prices, and a rule that was deleted

*Empirical. 5,248 rows across three series. The intervention is 14 April 2025, when the cepo was
removed and the USD 200 monthly cap deleted.*

**Asked.** Where eligibility is fixed by regulation rather than inferred, does the agent premium
appear, and does it collapse when the government deletes the eligibility rule that generates it?

**Answered.** The treated pair `oficial–informal` collapses: `rms(S − S')` **0.4996 before,
0.0508 after, ratio 0.102** against a registered band of ≤ 1/3. The three control pairs do not:
**0.712**, **1.050**, **0.999**, against a registered band of ≥ 2/3. The differential prediction
was registered before retrieval: the index part collapses, the friction part does not.

**Revised / void.** **B5-14, the pre-trend check, returns no reading, and it is not a failure.**
The pre-window bucket series turns inside the window, at bucket 3 and bucket 8 of 12, so the fitted
slope is set by where the series turned rather than by where it ended and cannot be extrapolated
past the edge. An estimator that does not describe the object returns no verdict about the object.
The arm prints the series, the slope, and the shares of the collapse those slopes imply, **0.77 to
0.90**, and compares them to nothing.

**Recorded as a failure on 2026-08-11 against a band of 0.25, withdrawn 2026-08-21**, together with
the consequence it carried, that B5-8's collapse is confounded with a pre-existing trend and enters
the headline. Two independent reasons. The band had no theoretical source: it was the factor of four
another arm uses for a detection ratio of a measured magnitude against a measured noise floor, a
different quantity in a different role, and an arbitrary calibration value may not ground a negative
finding, so that consequence was unavailable on the day it was written. And a criterion may not draw
a line across an estimator: the three shares sit inside a span of 0.12, so the verdict was a step
function of where the band was placed and unanimous on either side of it. **B5-8's headline carries
no pre-trend caveat from this arm.**

Three further failures, and these are failures. **B5-5** was superseded whole: Ámbito's `dolar/tarjeta` turns out to be
byte-aliased to `dolar/oficial`, reading a ratio of **1.0000** in a month when the true regulated
multiplier was about 1.6. **B5-9, B5-12 and B5-13** never ran: the only free daily P2P history has a
longest frozen run of **47 days** against a threshold of **21 registered before the candidate was
retrieved**. **B5-11** never ran: three friction-column candidates were audited and all three
failed, the last on a median deviation of `2.90e-2` against a bound of `0.02` and a 106-day frozen
run.

**Scope.** B5-15, the edge-of-window check, passes on strict comparisons (the final pre-window
bucket **0.387** stands **4.8 times** above the treated pair's entire post-window maximum of 0.080),
and the record refuses to let it repair anything: **that B5-15 passes was known before B5-15 was
written.** It does not supply the pre-window reading B5-14 could not produce. Separately, the
control group is contaminated: the
MEP and CCL cross-restriction was removed on the intervention date and reimposed in September 2025,
inside the post-window, so the controls were treated twice.

---

## B6 — Cuba: three official prices for one conversion, and the first `H⁰` carrier

*Empirical, partially run. Banco Central de Cuba API, 238 publication days from 2025-12-18.*

**Asked.** Can `H⁰` get a positive empirical reading? The BCC prices `CUP ↔ USD` three ways on the
same day: a frozen enterprise rate, a frozen retail rate, and a managed float opened 2025-12-18.
The first two admit no return leg, so a position can be entered and not left.

**Answered.** The structure is visible in the published table and needs no estimation.
`tasaOficial` **24.0000 → 24.0000, one distinct value** over 238 days. `tasaPublica` **120.0000 →
120.0000, one distinct value**. `tasaEspecial` **410.00 → 624.00, 62 distinct values**. B4's
unbounded ray is directly readable: `log(410/24) = 2.84` on 2025-12-19 rising to
`log(624/24) = 3.26` on 2026-08-11. The instrument checks out: **B6-8 passes** on 5,174 ladder rungs
across thirteen currencies with a worst relative departure of **0.0018%**, and the publisher
**truncates rather than rounds**, in **27,132 of 27,132** channel values.

**Revised, refuted, or unresolved.** Three, and two of them are the useful ones.

- **B6-8's first result is withdrawn as an artefact.** It had failed on eight yuan rungs. The yuan's
  API record begins twelve days after the segment opened, the XLSX back-fills its first published
  value, and a reconstruction fed **thirteen manufactured rows** into the criterion. Those were the
  failures. Note for anyone citing the pre-registration directly: §5 and §7 still read "It did
  fail... on the yuan alone", and that text is superseded.
- **B6-6's registered form named an undefined quantity.** It called `|2 log(III/I)|` the index part,
  but the index part is a cycle sum and there is no cycle through a frozen segment. The record's own
  comment: this is the error `b1_theorem.md` §12.1 exists to prevent, committed inside a document
  written to prevent it, and caught while writing the experiment rather than by any guard.
- **B6-4, the external referee, failed** on 3 of 147 days, worst **1.134%** against a 1% band. Under
  a one-business-day lag the worst deviation falls to 0.549% and no day is outside the band. The
  ruling is that the criterion stays failed and the alignment is not re-registered: the lag
  diagnosis is a diagnostic and not a pass.

**Scope.** The `H¹` arm has never run, so the station establishes one side of a contrast and does
not contain the contrast. It is blocked on one unresolved gate: the informal-rate API requires a
token, and whether it serves historical ranges at all is unverified. There is also **no zero
calibration over this window**, and the two delivery paths agreeing (XLSX against API) tests the
retrieval code rather than the collection. The record's own summary of how it learned this:
**two currencies are not a sample, and neither is one download.**

---

## What Part 1 adds up to

Six stations **in Part 1** (the carrier count above is four and spans both parts; **B8 is in Part 2**).
Two are pure theory and one of them (B4) proves a result that **weakens** the
framework's own falsifiable claim in the directed setting. Two produced measured non-zero cycle
sums (B2 loop A, B3). One (B5) produced a clean-looking result, could not read its own pre-window,
and withdrew the band it had first used to call that a failure. One (B6) validated its instrument, superseded its
first instrument failure as an artefact, and has not yet run the arm it exists for.

The largest number in Part 1 is B2 loop B's `2.52`, and the record's instruction is not to quote it
as the headline, because it is a statement about `H⁰` wearing the clothes of `H¹`.
