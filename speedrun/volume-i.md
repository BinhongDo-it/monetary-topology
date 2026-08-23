# Volume I speedrun: the A track, station by station

**Part 3 of 3.** Parts 1 and 2 cover the B track (B0 through B11).

The A track is mostly a **simulation** track. It asks whether position in a payment network, rather
than behaviour, decides who is reached by claims, and whether that position converts into a
compounding advantage. **One stage of ten is attached to real data** (A1, on household survey and
consumer-finance sources); the rest are simulation, and the record's own weakness list says so.
Read every entry below with that on the front.

Same four fields as Parts 1 and 2.

---

## A track overall

**Asked.** If claims keep accumulating at the top of a stratified payment network, does the bottom
get cut off from real resources even while total spending and total transaction volume are flat or
rising? And can one mechanism (network position) produce a family of symptoms that are normally
explained by four separate stories?

**Answered.** **Every registered stage has now run.** Stage verdicts: A0 **9/9**, A0b **12/12**,
A2 **8/8**, A2c **7/7**, A1 **four stations, one criterion clean at 60 cells and eight terminal**
plus A1b 6/8, A1c 2/2, A1d 7/9, A3 **3 pass / 2 diagnostic / 1 void / 1 unstable / 1 fail**,
A4 **3 pass, 2 void**, A5 **4/8**, A6 **3 pass 2 fail** plus a ratchet arm at **13/15**,
A7 **leg A: one pass and five failed or void, with the headline in the failures; leg B: unreadable
at every grid point, and it says so.**

**Superseded.** The argument form "we assume less" is **void and may not appear in any paper**. The
parameter census is **90 to 100 settable fields**, against roughly a dozen for Mark-0 and an
effective count of one for Wright. It is replaced by a weaker and defensible claim: a small tunable
space with nothing fitted, published levels entered as published, and every conclusion required to
hold under both parameterisations. Also retracted: the original A3 target (gluing the earlier stages
into an integration simulator), because gluing produces levels and not compounding.

**Scope.** Two structural weaknesses the record names itself, and both have moved.
**The coverage test is closed rather than outstanding**: Objection 11 ruled it invalid as
self-validation, because it lists what the framework explains and never what it forbids, and in a
space of 90 to 100 settable fields whether one vector hits four surfaces answers a question about
the field count rather than about the mechanism. Its replacement is a **zero domain**, which the B
track has met twice and the A track has not written. The second has partly moved: **A1 has run
against real household data**, so "nothing here has ever been checked against real data" is no
longer true, though nine stages of ten still have no external carrier and the five registered
external fingerprint checks remain unstarted.

**And one result now runs against the track's own headline.** A7 measures that adding **350 edges to
1,039** removes **98%** of the compounding divergence, with disjoint per-seed distributions. The
positional advantage the A track is built to demonstrate is **a lock-in on a sparse graph, not a
property of stratification as such**, and a single alternative route is enough to end it. That is a
finding, and it constrains every claim A3 makes.

---

## A0 — is spending inside your own stratum different from saving?

**Asked.** In a 100-person toy economy with almost no edges from the top holder to the bottom forty,
does raising the top holder's spending rate from 0 to 30 per round deliver any more resources to the
bottom?

**Answered.** Simulation, **9/9**. The load-bearing output is a spending-rate sweep whose registered
criterion is that the slope be **statistically indistinguishable from zero with the adjacency matrix
held fixed**. The slope's measured value is not recorded in the plan file.

**Where the build departs from the manuscript.** Two departures matter to anyone comparing the two:
an edge the manuscript specifies as zero is removed, and wage edges are folded into the adjacency
matrix, because leaving them out makes potential support beat realised support for no reason other
than the missing edge.

**Scope.** A mechanism demonstration, not a fit: no credit creation, no prices, no calibration.
**Its falsification clause is live**: a significant positive slope with a correct implementation
would establish the manuscript's own load-bearing objection and force revision of Volume I §1.

---

## A0b — is there an elasticity above which the production layer cannot survive?

**Asked.** If the wage bill responds to derived demand rather than being a fixed cheque, is there a
threshold?

**Answered.** Simulation, **12/12**. **Unit elasticity is the dividing line**: below it a positive
steady state exists (lowest observed `2.85`); at or above it there is none (highest observed
`3.5e-83`). Above the line, survival is **strictly linear** in the autonomous share. A reduction
guard reproduces the fixed-wage model **bitwise** at elasticity zero.

**Why this stage exists.** It was added rather than planned: under a fixed wage bill the production
layer settles, and a model attached to an already-settled layer can only match levels.

**Scope.** Threshold results are the class where the nearest published competitor is the same kind
of object, so this is **semi-distinctive at best**. The difference claimed is in the trigger
(network structure rather than parameter space) and has to be argued case by case.

---

## A2 — can volume rise while reach shrinks?

**Asked.** Can total transaction volume rise while the set of nodes actually reached by claim
exchange contracts? And does an agent's own propensity to spend matter at all with no incoming
edges?

**Answered.** Simulation, **8/8**, and this is the track's strongest reading. **The sign flip**:
with no issuance, flow and support move together (`×0.87` against `×0.729`); with issuance they move
**opposite**, flow `×44.87` while the support set goes `×0.402` and the production layer falls to
**0.51%** of all circulation. **The flip holds in 12 of 12 seeds.** The cleanest single output:
an agent with propensity maxed out and no in-edges ends holding **`0.000e+00` in 12 of 12 seeds**.
Propensity is a property of the agent, reachability is a property of the graph, and only the second
one decides. With three layers the wage channel closes to `2.571e-139` **while the bill amount is
unchanged and elasticity is zero**. Zero autonomous edges collapses; **one edge recovers 75%**.

**Superseded.** The thresholded support-set measure, mid-design: proportional dynamics have a
positive stationary distribution, so **any cutoff measures the cutoff itself** and the support set
can never contract. Replaced with a threshold-free measure.

**Scope.** Claimed for a class of topologies, not universally. The registered failure clause stands:
if no parameter interval delivers "volume up, support down", the criterion needs extra conditions
and the threshold has to be recorded.

---

## A2c — can the loops disappear without deleting an edge?

**Asked.** When gross flow explodes, does anything real move?

**Answered.** Simulation, **7/7**. Net displacement flat (within `1.62×`) while gross flow rises
**`97.1×`**; the churn ratio goes `4.4 → 268`. The structural component's **magnitude** moves within
`1.65×` while its **share** falls from `2.18e-02` to `8.59e-07`. **Cycle rank collapses to `0.029`
of potential with no edge deleted.**


**Scope.** Self-imposed and kept as a criterion rather than a footnote: in the two-layer
configuration the cycle-rank instrument is **inert** (`1074` against a potential `1190`, motionless
throughout), so cycle-rank results speak only for the three-layer carrier. It was kept as a
criterion precisely so a later refactor could not quietly delete it and make the method look more
general than it is.

---

## A1 — the default waterfall (RUN, and it is the only stage attached to real data)

**Asked.** Does the observed ordering of defaults — card, then car, then rent, then eviction —
**emerge** from ranking each debt by immediate against deferred cost, rather than being hard-coded?

**Answered.** **Run, four stations, four records.** A1 built its population by crossing income
deciles with net-worth groups; **every level from that construction is superseded and none is a
measurement.** A1b replaces it with the survey joint, one model household per weighted respondent;
A1c measures the sequence inside one household; A1d gives net worth a channel and matches the
survey's window. Verdicts: A1 **60 cells exactly `0.000000`** on its first criterion, with eight
criteria left in `not_yet_written` **and that is terminal, not pending**; A1b **6 of 8 live, one
void**; A1c **2 of 2**; A1d **7 of 9**.

**What survives, and the strongest is the third:**

- **The K shape.** A common proportional squeeze raises the bottom's default rate by **`+0.1249`**
  and mortgage holders' by **`+0.0024`**. *The same shock is a rescaling at the top and a change of
  regime at the bottom.*
- **The subprime gradient**, `×2.60` bottom against middle.
- **The order inside one household**, which is the cleanest reading in the A track:
  **`607/2`, `449/2` and `523/9`** in order against inverted, with **all 13 inversions explained by
  the cost rule's own release clause**. And mortgage-before-car, **registered 2026-08-13 before it
  was seen, comes out `768` to `0`.**
- **The representative arm is degenerate in `{0, 1}`.** Aggregation destroys the object being
  studied.
- The delinquency gradient on a matched twelve-month window, on both pairs either side can resolve,
  in all six sweep cells.

**Revised, refuted, or unresolved.** Four, each named for which of those it is.

- **A cross-section of first defaults is not a sequence.** It is the holdings composed with the cost
  rule: **two households in five hold neither of the first two rungs.** *Aggregate delinquency
  composition cannot identify a cascade.*
- One criterion is **void**: its registration named two rankings and they disagree. **The break is
  one cell of 37 renters** whose income is half the group below them.
- One failure is **neither a calibration debt nor a refutation**: the criterion turned on a pair
  separated by **0.14 standard errors**, eleven survey households against five, and on a sixty-month
  window read against a twelve-month question.
- The measured cushion carried the top group thirty months and then lost to a reported income of
  **exactly zero**. **The failing cell is six families and one of them decides it.**

**Also on the record: a registered pre-run gate was breached earlier and never waived.** The plan
states A3's hard prerequisite is that A0, A1 and A2 all pass. A3 was built and run before A1 was
started. A1 has now run; **the gate was breached at the time and the record does not show it being
re-decided.**

**Scope.** The three failures that matter all have the same shape: **a verdict decided by a handful
of households.** One cell of 37, one pair at 0.14 standard errors, one cell of six families with one
household deciding it. Any citation of A1's failures must carry the cell size.

---

## A3 — the asset channel, and the hinge to the B track

**Asked.** Once claims accumulating at the top can bid for a tiered asset whose price rises with the
bidders' holdings, do two agents starting from the same point diverge at a compounding rate, and is
the exponent of that divergence the same object as the loop sum the B track measures?

**Answered.** Simulation. **3 pass, 2 demoted to diagnostics, 1 void, 1 unstable, 1 fail.**

**A3-4 is the hinge and the track's most load-bearing result.** The simulated divergence exponent
reads **`+0.36536`** against a product-graph holonomy of **`+0.37686`**, a relative error of
**3.05%** against a registered 20% tolerance, and it holds in **all 14 robustness cells** with the
loop sum itself moving between `+0.282` and `+0.499`. Price cancellation is **observed** rather than
assumed: an irrelevant price moves the number by `4.44e-16`. The two numbers come from modules that
share no code, enforced by parsing the abstract syntax tree for imports.

**A3-7** passes at the registered point (three non-overlapping windows, sign agreement 100/100/100)
and **fails in four of fourteen grid cells, left unfixed**. The record's own reading: A3-7's
conclusion lives on one parameter value and A3-4's does not, and that is a finding of the grid
rather than a defect to tune away.

**Revised, refuted, or unresolved.** Six, and they are the most instructive part of the station.

- **The service-flow return was deleted.** Imputed rent has no honest accounting representation
  here: you either conjure claims and break conservation, or you invent a conversion rate, and
  **inventing a conversion rate is inventing a deflator, which endorses the conclusion rather than
  checking it.**
- **`γ` was redefined** from a down payment to a terms premium, after which the four-cycle sum
  equals `log(γ_b/γ_a)` and **price cancels entirely**.
- **The pricing rule was retracted as implemented**: evaluating the threshold at the current price
  gives negative feedback rather than compounding, and terminal prices came out with the top tier
  stuck in the zero phase of an oscillation.
- **A3-4 version one read 78.7% error with the mechanism not wrong**, a mapping error, cited
  thereafter as the standard cautionary case.
- **A3-6 failed, and then the diagnostic campaign destroyed the shape it was supposed to predict.**
  See below.
- **A parameter was declared, validated, documented, and read by no line of code.** Two models
  differing only in it were bitwise identical on six outputs. It had been swept twice, reporting
  "no state change" both times: **those two clean rows were fake, because an axis the code cannot
  reach cannot move any verdict, and counting it as robustness claims coverage that does not
  exist.** The registration had named that axis specifically, so the one named axis was the one not
  being tested.

**Scope.** **Every A3 measurement after round 15 is taken on an economy in which the production
layer cannot enter the asset market at any price** (see §6.4d below). That covers A3-4's three
windows, A3-7 and A3-8. The record's phrasing: this is not their defect, it is the carrier's scope.
The asset specification's tier count, unit counts, opening prices, base terms, stretch, turnover and
rent rate are **all self-chosen**, and A3-4 sits in exactly that layer. And the reading rule:
**A3-4 reports that 3.05%, not "they matched"** — what carries information is how much the embedding
perturbed the identity, not that two numbers agreed.

### A3-6 — the prediction that was destroyed by its own diagnostic

This is the entry an outside reader should look at first, because it is the clearest case of the
project's discipline running against its own interest.

**Asked.** The model appeared to predict that the fraction of a one-off cash transfer a household
still holds does not vary smoothly along the income gradient but **jumps** at whether you own an
asset. That is a prediction of a phenomenon not considered when the theory was built, which is the
hardest kind of validation available, and it is checkable against real transfer-retention data.

**Answered.** **Fail**, and then three successive retractions of the shape itself.

1. "The step belongs to layer membership, not to assets" — **retracted**, it is an artefact of the
   rent rate. With rent off, the layer-step to asset-step ratio goes from **26 : 1 to 1.2 : 1**, and
   the mechanism is a floor effect on an instrument's range.
2. "The asset step is transient" — the word is right and **the reason was wrong**: it does not die
   because assets cannot survive downstairs, it decays while still held.
3. "Step versus gradient" — **neither word is right.** In the registered configuration one of five
   seeds has no wealth overlap at all, a third of holders are dropped for lack of a control, and of
   42 matched pairs holders win **57.1% against a noise floor of 60.0%, which is below the floor.**
   With rent off holders win 71.2% against a 50.0% floor, but the paired median still falls inside
   the floor's interquartile width. Concentration separates nothing: the top decile of pairs holds
   75.0% of the positive total **while the floor holds 99.7%**. And the tail **turns over**, with
   top-decile overlap across horizons of only 16.7 to 33.3 percent. Not a few holders persistently
   ahead; a different few each time.

**A registered pre-run gate held, and this is why the entry exists.** The rule was that the internal
check must finish before touching external data, because with only two points you cannot tell a jump
from a steep monotone gradient, and until then the sentence "the model predicts a jump" has no
basis. **The check ran and killed the shape.** The external arm is now suspended for a third and
harder reason: the surviving effect has **no reading on a central measure**, while every candidate
external dataset reports means and medians.

### §6.4d — the shape the B track keeps citing

**Asked.** When production-layer holders disappear from the asset market, is it because they
**cannot clear the price threshold** (a wall, a hole in the domain) or because they clear it and
lose the auction (a price effect)? The two have different fingerprints.

**Answered.** **It is the wall, in all five seeds.** The hard gate first closes at rounds
`2 / 2 / 3 / 3 / 4` and the soft gate at `6 / 6 / 8 / 9 / 15`, while the units are not exhausted
until rounds **55 to 110**, a median gap of **93 rounds**. The count of nodes that can buy is 5.80
at round 1, **0.20 at round 10, 0.00 at round 20**, while the unit count does not bottom out until
round 80. With rent switched off it is identical, so **rent does not build this wall**; the pricing
rule itself does.

> **That is the "shape" the B track cites: the extensive margin goes to zero four to five times
> faster than the intensive margin.** B9 registered a test with the opposite sign against it, ran
> it, and lost — see Part 2.

**Superseded.** An earlier characterisation ("the hole is at the low-tier margin, 23 nodes stuck
between the two gates") is corrected to **a reading of the opening instant only**. That hole closes
between rounds 6 and 15. The gate is a hole for ten rounds and a wall for the remaining two hundred
ninety, **and nothing in the registered report says when it flips.**

---

## A4 — is connectivity upstream of the four standard explanations?

**Asked.** The four standard explanations for wealth divergence are inheritance, education returns,
heterogeneous capital returns, and assortative mating. Is network connectivity a fifth item on that
list, or the variable that sets the space the other four operate in?

**Answered.** Simulation, **3 live passes and 2 void**. Identical agents on a complete graph do not
stratify (Gini `0.00711` against a `0.02` cap). **Connectivity alone produces Gini `0.93673`**
against that `0.00711`, which the record calls the single most unified-theory-looking criterion in
the project. And the measured negative result: each opponent acting alone raises Gini by
**`+0.00007`** (inheritance), **`+0.00932`** (education), **`+0.00080`** (capital returns) and
**`−0.00006`** (assortative mating), **all below the `0.02` floor**; after one conduit was removed,
no opponent moved more than **1.60%** of the stock in any cell of the entire design.

**Revised, refuted, or unresolved.** Two criteria are **void**, and both are among the claims the project most
wants.

**Scope.** The headline Gini comparison **stands on a domain the project itself measured to be
sixteen financial-layer nodes**, and that is on its own weakness list. More generally: **four
undecidables cluster on exactly the claims the project most wants**, and the record's own rule is
that undecidable cannot be used as a defence and four undecidables must not be read as four to-do
items.

---

## A5 — the reachability threshold, and the record that could not be reproduced

**Asked.** Is there a critical point in reachability below which the production layer cannot be
reached at all?

**Answered.** Simulation, **4 of 8**. Four criteria fail and are **not fixed**; all four were
entered into an expected-failure list with registered reasons. At A3's registered parameters the
production layer's effective reachability is `ρ = 5.88` against the financial layer's `0.25`:
**the two layers are 23.5× apart.**

> **[2026-08-18 correction, M-51]** This previously read `ρ = 1.96`. That number is **A3's** `ρ_eff`
> (A3 arrived at its soft gate from the gate side and landed near 2 by accident), not A5's production layer.
> The station file `docs/a5_reachability.md` §2 reads `0.25` / `5.88`, a factor of `23.5`.
> **The ratio was right; the numerator was not.**

**Revised, refuted, or unresolved.** **The headline here is the record, not the verdict.** The stage's stored
results file **cannot be produced by the code committed alongside it**, and the inconsistency
survived five subsequent commits. The cause was a mechanism added as default-on to a machine A5 runs
entirely on, without re-running A5. With that mechanism set back to zero the five stored numbers
reproduce bit for bit.

**Why it hid, and both halves were necessary.** The commit preserved the opening construction, so
**every construction-time quantity in the file still reproduced exactly**, including the numbers
used to score two of the criteria, and only quantities that had run through rounds shifted. **A file
half of whose numbers reproduce exactly does not look like a wrong file.** The other half: A5 was in
neither the run-all list nor continuous integration, **so record and code had never once been
compared.** It was caught by re-running the stage, not by a guard and not by anyone spotting a wrong
number.

**Scope.** The simple-case result does not transfer. **What transfers is the shape**: there exists
a critical point, and the benign side is out of reach in practice. One criterion's denominator spans
`[×0.036, ×2.652]` across 12 seeds with 7 below 1, **sign unstable, so no point value is given** —
and the record notes that raising seed counts does more than narrow intervals, it makes "this
quantity has no location parameter at all" visible.

---

## A6 — what redistribution rate does the siphon cost?

**Asked.** Under already-fair retention with nowhere to issue, what redistribution rate does the
stratified graph need in order to match the flat graph?

**Answered.** Simulation, **3 pass 2 fail**, plus a ratchet arm at **13 of 15**. The headline:
the stratified graph needs **`R* = 0.060`** and the flat graph needs **`0.000`**. **Six tax points,
and that difference is the siphon, in units of tax.** The ratchet mechanism holds to a relative
error of **`5e-11`** with two control cells moving 0.01% over sixty thousand rounds. In one cell,
**61 nodes stand on both sides of the transfer within a single round**. A reduction guard compares
160 model pairs bitwise with **0 mismatches**, against the unmodified model itself rather than a
stored fixture.

**Revised, refuted, or unresolved.** Four, and the first is a pre-run gate that rejected an external suggestion
**with numbers rather than with an opinion**: the suggestion to widen the tax-rate sweep was refused
because the grid was already swept to `0.95`, because raising the levy **makes the two problem seeds
worse**, and because one arm is monotonically non-decreasing and therefore **has no fixed point
structurally**. Also: depreciation was rejected as the wrong mechanism (the asset does not wear out,
**the world walks past it**); a mid-course correction was itself retracted after a long run showed
the proposed fix only postpones the collapse; and the levy was found to land on **twenty node
indices fixed at construction time** rather than on whoever currently holds a lot.

**Scope.** The asymmetry, to be carried verbatim: **up and down are not the same curve.** Up is
diminishing returns; down is falling off a cliff, because the economy was built to a level and
dropping below it loses the whole of that level rather than the near-zero marginal segment. **A6
does not simulate the cliff, it only registers it**, on the grounds that simulating a path that does
not occur amounts to inventing a price for it. Same discipline as the refusal to invent a deflator.
And the scope limit: this is a closed economy with no outside, so one parameter may be read only as
"endogenous absorption speed" and **never as the rate of progress of the era**.

---

## A7 — continuous connectivity (RUN, both legs, and it partly undercuts A3)

**Asked.** Make connectivity a continuous parameter rather than a switch, and ask what the switch
could not: does adding a few edges to a sparse access structure remove the compounding advantage,
and does connectivity amplify the four competing explanations?

**Answered.** **Both legs run.** Leg A is the finding; leg B reads nothing and says so.

**Leg A, and it does not need a test.** At the first grid point — **350 edges added to 1,039** —
**the divergence loses 98% of itself.** The two per-seed distributions are **disjoint**: the
smallest value with no edges added is **3.9× the largest** with them added, twenty seeds against
twenty. Every confound the pre-registration named is held or moves the wrong way: the payer set is
identical, the opening rank correlation is `+0.972`, and the paired population and the participation
both **rise**.

**The placebo settles the mechanism.** Aiming the same number of edges at already-central targets
raises the centrality dispersion by 5% and the layer gap by 7% **and loses the same 98%**. And read
directly off the terms matrix, **the holonomy itself is `+4.9%` and `+7.0%` higher in the two arms
while the divergence is down 98% in both.**

> **What one or two extra counterparties destroy is the repetition of the margin against the same
> counterparty, not the margin itself. Positional rent on this carrier is a lock-in rather than a
> spread, and a single alternative route is enough.**

Unnormalised against the round count, the gap with edges added **does not move across a fourfold
change in rounds** while the gap without them moves with it. **The added edges do not slow the
accumulation, they end it.**

**Leg B reads nothing, at every grid point including the origin.** Its primary quantity is
sign-unstable everywhere, with a mean of `−0.00039` against a range of `[−0.0020, +0.0010]` that
straddles zero and is five times the mean. A quantity with no sign has no magnitude to trend. **This
is not a negative result about connectivity; it is A4's void criterion reappearing on a different
estimator.** Two further criteria are not adjudicable and one is recorded as not run, because above
a threshold a transmitting mechanism has **no stock**, so running it would produce zeros whose cause
is the carrier.

**Revised, refuted, or unresolved.** Five of six leg-A criteria failed or were voided, and the station keeps
them.

- **One criterion's registered shape is wrong.** There is no gradient. There is a **step at the
  first grid point**, `+18.9854` to `−0.1157`, then a flat band. Recorded and **not repaired**.
- **One is void on the estimator it names**, because the two arms end up with different node sets
  and an unnormalised difference of falls compares quantities defined on different agents. Its
  letter-pass on the other estimator is demoted to a diagnostic.
- **One holds nowhere**, including at the point the quantity it defends was derived from.
- **One failed twice before it was right.** Its first implementation read a cell where the terms
  matrix is flattened and **every loop sum is exactly zero by construction**; its second read a
  population that moves with the treatment.
- **Three statistics failed the same way**: the quantity's behaviour was set by something moving
  with the treatment rather than by the thing under test. Registered as a discipline candidate:
  **before registering any ratio or difference, report how the denominator behaves under the
  treatment, and register the unnormalised quantity alongside it.**
- **The station's own compounding explanation is withdrawn** under its falsification clause and left
  in place struck through, **because the way it failed is the finding.**
- **A number quoted in three markdown files had no producer**: it appeared in no code and in no
  stored record. When an instrument was finally built for it, seed zero reproduces it to four
  decimal places and **twenty seeds do not — the table was a single seed and did not say so.**

**What it costs A3, and this is the part that must travel.**

> **A3-8's reading is a reading at mean out-degree `5.20`, and it is gone at `6.95`. A3's registered
> sweep never varied graph density, so this sensitivity was neither measured nor excluded before
> now.**

**Scope.** Every A7 record carries `diagnostic_only` and **no A7 heading enters the results file**,
because the scored estimator is not yet the default output. The station also files its own defence
against the obvious objection, with the concession first: **the policy implication is not new and
may not be presented as a discovery.** What answers "this is just supply and demand" is that supply
and demand predicts the margin **falls**, and the margin **rose by 5 to 7 percent while the outcome
fell by 98**.

---

## The X family — the external checks (REGISTERED, ZERO STARTED)

**Asked.** Which A-track predictions are checkable against real data?

**Answered.** **Five candidates, registered, unscheduled, none started.** They check, in order of
readiness: a structural component's magnitude staying flat while its share collapses (**first
candidate, because the input data is already on disk**); a fork in transfer retention by whether an
upward counterparty exists; stratified rather than continuous retention curves; the collapse of the
four standard explanations once access structure is controlled; and highly non-linear recovery from
adding one downward channel.

**Retracted / blocked.** **Two are blocked by measured obstacles before any run.** One is blocked
because the dataset that would test it **is already an input to this project's own calibration**, so
using it would violate the rule that two constructions sharing an anchor are not independent
validation. Another is gated because it collides with an existing literature, and the estimand has
to be written out as a different quantity first or it reads as a failed replication.

**Scope.** Three disciplines, violating any of which makes the whole family worthless. Every bet
must first be assigned to one of six layers, and **four of those layers have already lost four times
in a row**, so a new station landing on one has to explain why this time is different. Before
opening any station: **if this fingerprint does not hold in reality, which A-track criterion is
overturned? A station that cannot answer is not opened.** And the shape and criteria must be pinned
**before** the data is pulled.

---

## The A track's two open items, and what closed the criterion they replace

**The A track has no zero domain.** The unified-mechanism claim was once to be tested by a coverage
test, one parameter vector producing all four surfaces at once. **That criterion is closed, and it
is closed on the merits rather than by failing.** Objection 11 ruled it invalid as self-validation:
it lists what the framework explains and never what it forbids. It is also undecidable in this
parameter space, because with 90 to 100 settable fields the existence of a four-surface vector is
fixed by the field count rather than by the mechanism, so a hit would carry no information and a
miss is already implied by the parameter census.

The repair adopted in its place is a **zero domain**: name where the framework's own quantity must
be zero, where it could have been non-zero, and where the same family reads non-zero, then measure
there. **The B track has met it twice**, on B6's derived channel columns and on B13's implied
exchange book. **The A track's has not been written**, and writing it is the open item.

**A1 is the only stage attached to real household data**; every other A-track stage is closed-world.
The B track has four external empirical carriers.

> **[2026-08-18 M-42 correction]** This section previously read *"Seven or eight stages"* and
> *"Nothing has been checked against real data"*, both written before A1 landed and never updated,
> while the opening section already said ten stages and named A1's real-data attachment.
> **Two contradictory sentences on one page read as a document nobody had read end to end.**
> **Stage counts are no longer written anywhere in this file** — an audit of A1 may still change
> what counts as a stage, and a number in prose has to be maintained by hand while the roster moves.

---

## How the two tracks connect

**A shared formalism plus one shared number. No shared prediction, no shared dataset, no shared
code.**

The formalism is load-bearing and A3-4 is the hinge: a divergence exponent produced by a full
simulated economy, compared against a loop sum produced by a module given nothing but a terms matrix
and two price vectors, agreeing to 3.05%, with the no-shared-code guarantee enforced mechanically so
that the agreement cannot be an identity.

The shared number was **designed** to be the calibration constraint: the B track's per-period loop
sum should pin the A track's divergence rate, nailing both tracks to one number. **The record states
that the two sides are still not the same object in code, calls it the project's largest unjoined
seam, and never records the seam as closed.** No numerical comparison of the two magnitudes appears
anywhere.

One prohibition travels with any joint citation: **A3's threshold channel and the B track's `H⁰` are
two different objects and may not be cited for one another.** An external suggestion has already
made exactly that mistake and it is on the record.
