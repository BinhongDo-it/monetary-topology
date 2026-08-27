# monetary-topology

Mechanism models for a topological framework of claims and resources.

A monetary claim and the resource it points at are two different objects. Most
of what follows from that is uncontroversial and widely conceded in principle.
This repository is about the part that is not: once claim circulation is
stratified, **a quantity of money does not establish access to resources. An
adjacency matrix does.**

The models here are minimal by design. Each isolates one mechanism, exposes fewer
than a dozen parameters, and reports a criterion that can falsify it.
They are built for checkability rather than scale: every structural claim is
packaged so that someone who did not write the code can test it and see what
would have counted as the other answer.

**Status, 2026-08-27.** Both tracks have run. **Seven carriers have produced
measured non-zero readings on real transaction data**, and each stands against two
different zeros. One is a floor that is measured rather than asserted, which says
the reading can be seen. The other is **a point prediction of exactly zero, made by
the account this repository tests**: if a single scalar price vector on positions
exists, every closed loop sums to zero **however much the contract changes along the
way**. **Seven carriers return non-zero against that prediction**, the largest at
`4.18e+06` times its own floor with a within-cell permutation null of 0 of 999 in
every cohort. The carriers are mortgage origination terms; **mortgage
modification, the strongest of them**, on one design and two GSE datasets;
cross-currency funding; the ETF creation triangle; Argentina's legally distinct
conversion tracks; Cuba's central-bank table; and CME calendar spreads. Each is a
separate regulatory environment, which is what makes them separate carriers
rather than one carrier sampled seven times.

**Six of them read an undirected cycle sum. The seventh reads a directed one**,
where the question is not whether a potential exists but whether a *sub*-potential
does, and it arrives with its own zero calibration measured on a second country
under the same register. **One of the seven returns both a zero and a non-zero
from the same apparatus on the same feed on the same day**, which is the only
place in the record where the framework named which side would be which before
anyone looked.

**Three results are about the instruments rather than about the world, and each
bounds what may be claimed anywhere in the record.** One built a counterexample
against its own headline and measured what its carrier can support, which
**bounds every future rank claim on that data**. One measured that its own
pre-window turns inside itself, and **removed a threshold that had no theoretical
source**, so no arbitrary calibration grounds a negative anywhere here. One
answers the sharpest objection in the programme by **measuring the instrument's
own resolution and reporting the number**, which settles what that objection can
and cannot be tested with. See [RESULTS.md](RESULTS.md) for the full
record, and the index by field below for which stations sit in your field.

This repository gives an exact criterion for when a single scalar price
vector on positions exists, proves it with no economic assumptions in it,
and measures it on seven carriers. Which standard constructs presuppose that
object, and what each of their setups says in its own words, is in
[`b0b_aggregation_and_the_potential.md`](docs/b0b_aggregation_and_the_potential.md).

The headline empirical number: hold census tract, year, lien position, loan
purpose, occupancy and dwelling type fixed, and **78 percent of the variance in
financing terms remains inside those cells** (`0.8480` under `min_size = 20`, a
restriction added after the first result was read, which is why `0.7831` is the
number quoted when one number is wanted). A single price vector on
positions predicts zero. A pre-registered placebo, in which government programmes
replace the credit-graded price grid with a flat schedule, moves it in the
predicted direction by 130 times the scale of a gap known to be zero.

---

## Speedrun: the index by field

**[`speedrun/README.md`](speedrun/README.md) is the way in.** It states **what
the programme claims and why that is one claim** rather than a pile of stations.
Then it indexes the whole thing **by economics subfield**: which stations are in
your field, what they found in your field's own vocabulary, what the nearest
existing practice is, how this differs from it, and where to read them. **Read
one section of that, then go to the stations it names.**

The record itself is ordered by station number, which is an internal build order
and tells an outside reader nothing, which is why nobody should start there.

**The scope note attached to each station is part of the entry, not a footnote.**
[RESULTS.md](RESULTS.md) reports every criterion at the same resolution,
whichever way it came out, and it keeps apart three outcomes that get collapsed
elsewhere: **a prediction the data said no to**, **a claim this programme
superseded on its own evidence**, and **a question for which the instrument
returns a measured bound rather than a verdict**. The third is the largest group,
and it is the map of what the available instruments resolve to. Producing that
map is most of what this record is for, because it is what tells the next person
where their effort will and will not buy an answer.

For the machine-readable record, one entry per criterion with the number beside
it, see [RESULTS.md](RESULTS.md). The run records it draws on are in
`results/*.json`.

---

## What this is about, for someone who does not do economics

For readers outside economics. It states the idea without the machinery,
because the machinery is what makes the claim look either obvious or absurd
depending on which half you read first.

**Money is not the same object as the thing money buys.** Almost nobody disputes
that in the abstract. What follows from it is disputed, and the dispute is
usually conducted as if it were about quantities: is there too much money, too
little, is it going to the wrong people.

**This programme is about a different question: who can reach whom.**

Picture the economy as a map of who can pay whom for something real. Not who is
rich, not how much money exists — who is connected to whom. Now notice that this
map is not one connected sheet. There are regions that trade briskly with each
other and touch the rest only through a couple of narrow bridges.

Add money to such a map and it does not spread evenly. It circulates inside
whichever region it landed in. The total goes up, activity in that region goes
up, and a region on the far side of a missing bridge sees none of it — not
because the money "hasn't trickled down yet", but because **there is no path.**
A quantity cannot create a path. Only a change in the map can.

That is the whole idea. Everything else here is designed to falsify it.

**Three things follow, and each of them is checkable:**

1. **The same amount of money can produce completely different outcomes**
   depending on where it enters. So "how much" is the wrong first question and
   "where does it enter, and what is it connected to" is the right one.
2. **A price is not one number attached to a thing.** If it were, then going
   around any closed loop of exchanges — trade A for B, B for C, C back to A —
   would have to come back to where you started. **It does not.** That gap is
   measurable, and measuring it on real transactions is most of the empirical
   work here.
3. **Some economic damage is invisible to the usual instruments** because those
   instruments add everything up first, and adding up is exactly the step that
   destroys the information about who could reach whom.

**Why the loop matters.** If prices really were one consistent set of numbers,
every closed loop would sum to zero, always, as a matter of arithmetic rather
than of economics. So a loop that reliably does not sum to zero is not an
opinion about markets. It is a fact about the data that a single price field
cannot accommodate. That is the quantity this programme measures, on mortgage
originations, on mortgage modifications, on currency conversions, and on the
mechanics of exchange-traded funds.

**What has actually been found, in one paragraph.** Hold constant everything a
lender is supposed to price on — same neighbourhood, same year, same kind of
loan, same position in the queue — and most of the variation in the terms
borrowers get is still there, inside those groups. A single price schedule
predicts none of it. The same non-zero loop shows up in three other places that
share no data and no code with the first. A large part of the register is neither a
pass nor a refutation: the instrument returns a bounded estimate rather than a
verdict, and that bound is recorded with its reason and its number rather than
rounded into one. One station superseded its own headline on a counterexample
this programme built against itself, and the counterexample is the more useful
result, because it bounds what that carrier can support.

**What the finding licenses.** It is a statement about the arithmetic of a price
field and nothing else: these prices do not come from one consistent schedule.
Whether that is good, bad, or anyone's fault is a separate question this
programme does not take up, and
[`docs/b0_claim_scope.md`](docs/b0_claim_scope.md) draws that line explicitly
before anyone reads the rest.

---

## Where the conclusions live

**This README gives the headline results. Every criterion, with its measured
value and whichever way it came out, is in [RESULTS.md](RESULTS.md), one section
per stage. `docs/` holds a prose document for the stages that have one, and the
section below says which those are.** The division is
deliberate: a README that carried every reading would have to be rewritten every
time one moved, and the ones that moved most are the ones worth reading in full.

**What the three places are for.** For a stage that has one, its `docs/` file
holds the pre-registration, the amendment trail and the reading, including the
readings that were withdrawn and why. `RESULTS.md` is the ledger over the
committed JSON records and lists every criterion — **passed, bounded, or
superseded** — with its measured value, for every stage without exception. This
README is an entry point and the record leads it.

**A stage's own record is the authority on that stage, and this README is behind
it by construction.** Where this file disagrees with [RESULTS.md](RESULTS.md), or
with a `docs/` file for a stage that has one, the record is right.

### Which stages have a prose document, and which do not

**The Roadmap tables below carry the link for every stage that has one.** This
section says only what a link cannot, which is why the others do not, since that
is a convention rather than an omission.

**The four earliest A-track stages never had one.** A0, A0b, A2 and A2c each
isolate one mechanism in a few dozen lines, and the design is legible in the
experiment file itself. Their readings are in [RESULTS.md](RESULTS.md).

**From B10 onward the convention changed, and it is the one still in force.** The
criteria are written in the experiment script, the record each run writes carries
them verbatim, and the reading goes into [RESULTS.md](RESULTS.md). The design and
result documents for those stages are held outside this repository. **What is
published is the evidence**: `experiments/<stage>_*.py` and the committed
`results/*.json` beside them, which is what someone re-running a stage actually
needs. The A-track stages built after A7 follow the same convention.

**Two stations answer a requirement stated inside another station's document**,
which is worth knowing before looking for a file that does not exist. B13's
carrier requirement is in [`b9_zero_holonomy.md`](docs/b9_zero_holonomy.md)
section 57, which states it and says in the same breath that meeting it is not
B9's work. B14's is in [`b4_directed_edges.md`](docs/b4_directed_edges.md)
section 9, and **that section now carries three conditions where it carried one,
with Theorem 6(5) new**, which is what that stage produced besides its readings.

**One station has both its register and its readings published here**, and that
is B15, because it is the control carrier for B6 and four of its thresholds are
B6's own values carried over unchanged. Judging two carriers by one ruler means
something only if the ruler is visible.

### Across every stage

[`MEASUREMENT.md`](docs/MEASUREMENT.md) — **a catalogue of the ways a measurement
in this repository can be misaligned with the thing it is measuring, each entry
carrying the instances that produced it**, plus the checks applied before any
number is reported. Every entry was written from a case rather than from
anticipation, which is what makes them transferable: several changed a stage's
headline, and they are the part of this work most directly reusable by someone
measuring something else. **It is the
most useful file here for anyone who wants to know how much to trust the rest.**

---

## What the A-track model assumes

**This section is about the A track only, and the B track rests on none of it.**
The A track is a simulation, so it has to declare a population, a behavioural
rule and a parameter range before it can produce anything, and every one of
those is a place to attack it. The B track measures a closed-loop sum on
administrative data; it needs no strata, no spending propensity, no elasticity
and no calibrated wage bill, and its scope is fixed instead by B0, which states
what a non-zero loop does and does not license. **A reader who came for the
measurement stations can skip to the next section.**

**How to read the list below, and what is different about this particular ABM.**

Loose bricks build whatever you meant to build. Give a model enough of them and
it produces a house, because a house is what you set out to make and nothing in
between constrains you, so "it produced a house" carries no information. That is
the usual criticism of agent-based models, and it is a fair one.

Fix where the columns stand and where the doors and the windows go, and what is
left is a different kind of freedom. Many ways to build the house remain, and
every one of them is a different realisation of the same blueprint. The more the
rules say about the positions, the less the remaining choices can decide.

**This model is a phenomenon simulation and not a fit.** It is derived from the
framework and does not try to reproduce the economy. It asks a narrower
question: which observed phenomena a mechanism set carrying only the framework's
own commitments turns out to produce. The credit in reproducing something is
exactly the chance it could have failed to. A model with a few million
parameters reproducing the stylised facts is worth nothing, because failing to
reproduce them is the only outcome that would have been news. A model whose
positions are fixed before the run can fail, and that is what makes the same
reproduction informative.

Which bricks get used, how thick the walls are, what colour they are: those
decide what the house looks like, not whether it is a house. Suppose, and the
number is invented for the sake of the point, that some outcome here needed a
tax rate of 102%. The right reading is "this brick is a different material in
the real world, and something there is counterbalancing it", not "the framework
predicts a world with a 102% tax rate". The mechanisms and topological paths
enumerated here are the ones that could be enumerated while the experiment was
designed, and the framework permits others compatible with it.

**There is no such reading in this repository.** The invented number is there to
make the principle unmistakable, not to prepare an excuse. Readings are kept
inside realistic ranges, and where a magnitude or a range is load-bearing for
what a stage claims, a reading outside it is not accepted as a pass. The real
case runs the other way and is sharper: A9's levy is a share of financial-layer
holdings taken each round, so it is not on the same scale as any historical
marginal tax rate and is not to be compared with one. Where a parameter has no
real-world counterpart, the honest form names the mismatch rather than reaching
for a number.

What can still fail is the columns against the doors: readings that conflict
with each other, or that come out with the wrong sign or the wrong order of
magnitude against the world. Put a door where a column stands and there is no
house at all, and no choice of bricks recovers one. So the load-bearing claim is
never that a house was built. It is that the positions were fixed in advance,
out of the theory rather than out of the data, that they could have conflicted,
and that they did not. Two things make that checkable rather than asserted:
every mechanism added since the first stage is off by default and reproduces the
earlier results bit for bit when it is off, and every criterion is in the
experiment script that produced the record it scores.

Stated plainly, because the A-track results follow from these and a reader
should be able to attack them directly rather than reverse-engineer them from
code. **These are stage A0's construction**, which is where the track starts.
The stations after it add mechanisms one at a time, each behind its own switch,
each off by default, and each reproducing the earlier results bit for bit when
it is off.

**Load-bearing.** The financial layer has no discretionary edge into the
production layer. Its spending can land only inside itself. The single downward
connection is a wage bill, modelled separately because it is set by hiring
decisions rather than by how much anyone chooses to consume. Collapsing the two
would put the conclusion of the left panel into its premise.

If you think this zero is too strong, do not argue about it. `Adjacency.
with_downward_edge(w)` opens it, and the right panel reports exactly what
happens across the full range. That comparison is the deliverable of this stage.

**Also assumed.**

- Four strata. Under the source-faithful preset: 49 agents holding 10%, 40
  holding 30%, 10 holding 30%, 1 holding 30%. The last three come from the
  framework; the bottom 49 is my explicit completion of a residual it leaves
  implicit, and dropping it would have flattered the result. Under the DFA preset
  the strata are the published percentile groups.
- Spending is a propensity on holdings, not a fixed amount. Retention rate is
  then `1 - propensity`, which is what the source means by a rate of exit from
  cross-layer circulation rather than a hoarding rate.
- The production layer's outflow exceeds its downward inflow, by 2.214x under the
  source preset and 2.368x under the DFA one. **This is a parameter, not a
  result.** The stage traces what follows from a drained layer and does not claim
  to derive the shortfall. The wage bill that sets it is not calibrated under
  either preset; it is swept instead.
- The derived-demand elasticity is a free parameter swept from 0 to 1.2, and the
  sweep extends past unity deliberately. Employment adjusts in lumps, and both
  the framework's account and the standard derived-demand argument imply a fall
  in final demand is amplified rather than damped on the way into payroll. Where
  the boundary falls is the result, not the assumption.
- Claims and resources start one-to-one; resources are fixed with no real
  growth.

**Absent from A0, and where each was taken up afterwards.** Credit creation is
absent throughout the track: the authority issues, and no matching liability is
created anywhere. The other four were scope restrictions on A0 rather than on
the framework, and each has since been opened behind a switch of its own.

| absent from A0 | opened at |
|---|---|
| default | A1b's cascade on a measured population, and A10's write-off chain |
| prices beyond a single index | A3's asset channel: three tiers, each with its own price and a declared elasticity |
| any network finer than stratum-level adjacency | A2 onward, a two-hundred-node graph with per-node degrees |
| cross-layer bidding for a shared resource pool | A3, which is the stage that took it up |

The last row is the one worth stating twice. Asset inflation squeezing the
production layer is a real mechanism and it is in the source framework, and
modelling it needs a price system with cross-layer asset markets. That is why A0
does not have one, and why inventing a deflator there to get the result earlier
would have been using formalisation to endorse a conclusion instead of checking
it. A3 builds the price system and reports what it does.

**A0 therefore reports claims, not real resource allocation.** That is a
deliberate scope restriction on A0, and stage A3 is where the
resource-allocation channel is taken up.

---

## Three readings from the later A stages

**A cascade with no balance sheet and no input dependence, stage A16.** Cascades
are usually derived one of two ways. Financial contagion runs through
liabilities: A owes B, A fails, and B's asset goes with it. Production networks
run through real inputs: A stops, so B cannot produce. **This model carries
neither, and takes a third route.** There are no debts, no receivables and no
input requirements between nodes, and the claim total is conserved through every
departure. What propagates is income: a node whose inflow falls below
subsistence stops spending, the routes that pointed at it are renormalised
across whoever is still trading, its counterparties' inflow falls with it, and
they stop in turn. So **balance-sheet interconnection and real input dependence
are each sufficient for a cascade and neither is necessary.** The route this
model does take is the income-expenditure spiral of Volume One section 12, given
an absorbing threshold and put on a graph rather than on an aggregate.
Stage A16 then adds one liability on purpose, carried by the highest-degree
nodes and pointing three ways in turn, and measures what it buys: the closing
count below the line moves by single digits on a base of 76 to 154. The cascade
is a function of the debt structure, and a flat one.

**A threshold in the subsistence level with nothing on either side of it, stages A15 and A16.**
What a departure costs the rest of the economy depends on what the departing
node was holding. Across 160 runs the share of the closing claim stock held by
nodes that have left takes one of two values: at or below 0.0086 in 105 of them,
at or above 0.9339 in the other 55, an empty band of 108 times, and no run
inside it. The crossing sits between floor multiples of 0.125 and 0.150, and at
0.150 both regimes occur at the same depth on different draws. **Which side of
it a configuration sits on decides what every distribution reading means.** On
the shallow side the leavers hold three tenths of one per cent and the readings
are redistribution among those still trading; on the deep side they freeze
holding ninety-four per cent, and every concentration measure moves with that
accumulation rather than with anything else.

**A control arm that separates a mechanism from the graph, stage A15.** Three inequality
measures moving three ways at once, the top percentile falling while the top
decile and the Gini rise, is a pattern with a standard name and a standard
explanation in terms of who leaves the sample. This model produces it. It also
produces it in the arm with **every mechanism switched off and no node leaving
at all**, within a digit of the arms that carry a floor: closing Gini 0.8812
against 0.8813, top percentile 0.1480 against 0.1480, top decile 0.8171 against
0.8172. The pattern therefore belongs to the particular graph draw rather than
to any mechanism here, and what the mechanisms do to it is remove it. The four
arms of fourteen that do not produce it are the three carrying a fiscal transfer
and the one combining the absorbing floor with the write-off, each of which
moves the closing Gini far enough to bury it. **The reading is available because
the arm exists.** An arm with every switch off is the cheapest configuration in
the design and the only one that can tell a mechanism's effect from the graph's
own drift.

---

## Scope

- **The object is structure, not timing.** Every quantity here is a property of a
  configuration; none of them is a forecast, and nothing is dated forward.
- **Levels are entered as published, not estimated from a target.** Nothing is
  fitted, so a match to a series is evidence rather than construction. Stage A1 is
  the first place the model is asked to meet one.
- **The standard agent-based stylised facts are an entry ticket, reported and not
  scored.** Models with no layered structure reproduce them too, so reproducing
  them carries no differential information about this structure. They are in an
  appendix at stage A3, and no criterion rests on them.
- **Two quantities are swept rather than defended: the adjacency matrix and the
  wage bill.** They are where the model is still assumption, so every conclusion
  is required to hold across the sweep, and obtaining real adjacency data is the
  top item in `data/SOURCES.md`.

---

## Running it

```bash
git clone https://github.com/<user>/monetary-topology
cd monetary-topology
pip install -e ".[dev]"

python scripts/run_all.py            # lint, tests, every stage, one digest
python scripts/run_all.py --quick    # lint and tests only
python scripts/run_all.py --slow     # adds A6's ratchet, about twenty-five minutes
python scripts/run_all.py --b2       # adds the stages needing fetched data
python scripts/run_all.py --skip-done   # read a stage's existing record instead of re-running it
python scripts/run_all.py --only B10 B14   # restrict to the named stages
```

`run_all.py` is the entry point. It prints a dozen pasteable lines: one per
stage, with its pass count, its exit code and its wall time, and a named line for
every criterion that failed. Criteria registered as failing carry the reason
inline, so a reader can tell a known negative from a regression without opening
anything. Individual stages still run on their own, for example
`python experiments/a0_retention.py`, and take `--rounds N` and `--seeds N`.

Every experiment script exits non-zero if a live criterion fails, so a
regression shows up the moment its stage is run. `.github/workflows/ci.yml` is
present but its trigger block is `workflow_dispatch` only, and every step is
left in place with a note on what it checked; three of its four steps re-ran
work that had already run on the machine that produced the commit, and the
fourth compared `RESULTS.md` against a generator that was retired on
2026-08-21. `RESULTS.md` is now kept by hand. The rules recorded here about
wall-clock content, float formatting and machine-dependent values still apply
to anything a criterion writes into its detail string, because two machines
render the same record and a spurious diff buries a real one.

Results are reproducible for a given seed, and every qualitative finding above
was verified to hold across seeds 0-19: the spending-sweep spread is exactly 0.0
in all twenty, the churn factor is 15.0 in all twenty, and the edge-opening jump
ranges from x1.89 to x2.01.

---

## Repository layout

```
src/monetary_topology/   the ones a reader starts from:
  config.py        all parameters, with sources and justifications
  economy.py       the block model (A0)
  network.py       the graph model and the intermediate layer (A2)
  topology.py      incidence operators, Betti number, Hodge split (A2c)
  asset.py         the asset price channel and its gate (A3)
  mechanisms.py    the four competitors and the demographic layer (A4)
  redistribution.py  the levy, the rebate and the frontier ratchet (A6)
  directed.py      one-way edges, friction and index (B4)
  calibration.py   the two presets, with series IDs and citations
  variants.py      config copying, so a sweep cannot re-default a field
experiments/     one script per stage or diagnostic. A stage script
                 writes results/<name>.json; a diagnostic writes nothing and
                 says so in its first line
scripts/
  run_all.py           lints, tests, runs every stage, prints one digest
tests/           naming follows the stage, so `test_a4_*.py` are
                 A4's guards and each asserts one claim its docstring states
figures/         committed; they are the artefact
results/         committed; machine-readable run records
speedrun/        README.md is the index by field: which stations sit in
                 which field, what they found in that field's vocabulary,
                 and where to read them
data/            not committed. SOURCES.md records provenance
```

No notebooks. Every result is produced by a script that runs start to finish
with no hidden state, and every parameter that affects a published figure is
declared in `config.py` where it can be read without reading the simulation
loop.

### Two invariants enforced in code

```python
# economy.py, every round. Raises on violation.
assert abs(claims_after - claims_before) <= 1e-9

# tests/. The identity behind "the rise in M/R equals cumulative retention".
np.testing.assert_allclose(h.issuance[1:], h.retention[:-1], atol=1e-9)
```

Stock-flow consistency is an assertion in the main loop rather than a check
performed afterwards. If it fails, the run stops and no figure is produced.

---

## Roadmap

Two tracks, run in parallel. They share no code because they answer different
kinds of question.

**Track A — distribution dynamics.** Computational claims: whether a support set
contracts is **parameter-dependent rather than structurally guaranteed**, and the
sweep maps where it does and does not.

| stage | subject | status |
|---|---|---|
| A0 | retention and allocation | **complete, 9/9**; no separate document, see [RESULTS.md](RESULTS.md) |
| A0b | derived demand on the downward edge | **complete, 6/6 under both presets**; no separate document |
| A2 | support-set contraction, and the intermediate layer | **complete, 8/8 over 12 graph seeds**; no separate document |
| A2c | cycle structure of the realized graph | **complete, 7/7**; no separate document |
| A3 | **the asset price channel** | closed, **3/4 live, 1 void, 2 diagnostic**, [`docs/a3_asset_channel.md`](docs/a3_asset_channel.md) |
| A3b | the construction the channel opens from | complete, [`docs/a3b_initial_construction.md`](docs/a3b_initial_construction.md) |
| A3c | which parts of A3 are load-bearing | complete, A3-8 **void**, [`docs/a3_restated.md`](docs/a3_restated.md) |
| A5 | reachability against participation | **4 of 5 live criteria pass, 3 void, 1 diagnostic**, [`docs/a5_reachability.md`](docs/a5_reachability.md). The region closes through the denominator rather than the price: freeze the price and the threshold is still crossed in 12 of 12 seeds |
| A6 | the cost of the siphon | complete, [`docs/a6_siphon_cost.md`](docs/a6_siphon_cost.md) |
| A4 | four competitors on the causal primitive | ran, **3/4 live, 2 void**; the discriminant is one of the voids, see below, [`docs/a4_causal_primitive.md`](docs/a4_causal_primitive.md) |
| A7 | continuous connectivity | **ran**, eleven verdicts, [`docs/a7_continuous_c.md`](docs/a7_continuous_c.md). The per-run records are `diagnostic_only` because section 4.2's scored estimator (`D_fixed`) is not what those runs computed; every gap in them is `D_reach`, which the same section registers as reported and never scored. The verdict sheet is the record that reaches [RESULTS.md](RESULTS.md) |
| A1 | default waterfall, calibrated to delinquency cross-sections | A1 superseded by A1b; A1b, A1c and A1d have run, see [RESULTS.md](RESULTS.md). Registers: [`a1_prereg.md`](docs/a1_prereg.md), [`a1b_prereg.md`](docs/a1b_prereg.md), [`a1c_prereg.md`](docs/a1c_prereg.md), [`a1d_prereg.md`](docs/a1d_prereg.md); what was checked before retrieval, [`a1_availability.md`](docs/a1_availability.md) and [`a1_inputs_availability.md`](docs/a1_inputs_availability.md) |
| A2d | what selects the terminal distribution | **complete, 4/4.** Structure moves terminal top1% wealth by 0.156, the savings rate by 0.0066 and where issuance enters by less still |
| A8 | the coverage test | **complete, 4/4.** Four surfaces are in play at once on a grid fixed before the run, and the two ends of the edge-width curve each drop a different one, which is what a conjunction of positive predictions has to do to carry any information |
| A9 | the New Deal switch | **complete, 4/4.** One structure, two parameter settings, and the rate at which both readings hold |
| A10 | the write-off chain | **complete, 4/4 live, 1 void.** One switch, and the aggregate stops showing what the distribution still shows |
| A11 | the subsistence floor | **complete, 4/4.** On a stratified graph position decides who starves; erasing the topology removes the question |
| A12 | the coverage result under the two later mechanisms | **complete, 7/7.** The floor and the write-off are added to A8's carrier and the four surfaces are read again |
| A13 | whether position can be bought and sold | **complete, 9/9.** Every earlier stage ran on a graph fixed at construction; opening that channel moves terminal top1% wealth by 0.0033, half what the savings rate moves it and a forty-seventh of what the structural parameters move it. A promoted node could acquire three things and not one: the core's edges, its spending propensity, and its role in paying wages. They are added one rung at a time so each step's difference has a single owner, and the propensity and the payroll rungs move terminal share in opposite directions |
| A14 | which readings are scale free | **complete, 7/7.** With node count and core share in the grid the structural span is 0.383, two and a half times what A2d reports with both held fixed |
| A15 | which of these phenomena are transcribed, and which fall out | **complete, 10/10.** The main grid needed no runs: A12's two records are it. A switch taken from the manuscript moves the closing Gini by under 0.0005 in forty-four cells of forty-five and by 0.271975 in the forty-fifth, where the amplifier is the issuance rule and the claim stock ends 22.7 times its opening. Whether a return catches is bistable, four cells against sixteen with an empty band of 12.6 times in the money stock. On the complete graph both exit rules put all two hundred below the line and only one lets them back, so the wall makes the cascade permanent rather than making it happen. The wage bill closes 26.2 to 29.5 per cent down and does not return; a return that catches recovers 66.1 per cent of that |
| A16 | a bilateral obligation on the highest-degree nodes | **complete, 6/6 and 1/1 on the floor scan.** The one liability in the flow layer, three orientations, selected by in-degree off the same expression that picks the injection node. It moves the closing count below the line by single digits on a base of 76 to 154. The share of the stock held by departed nodes is bimodal across 160 runs, 105 cells at or under 0.0086 against 55 at or over 0.9339 with nothing between, and the crossing sits between floor multiples of 0.125 and 0.150 |
| A17 | edges cut out of the graph, rather than a node ceasing to trade | **complete, 6/6.** Cutting seven tenths of the edges produces no cascade, at random or aimed at the hubs: flow ends at 0.99 and 0.94 of the control's. Removing nodes does produce one, and that is the subsistence floor, so the graph's phase transition is not what does it. Who does the cutting is the mechanism by three orders of magnitude: a stressed node cutting its own out-edges leaves flow at 0.0199 of the control's, and its counterparties cutting the edges into it leaves it at 32.9 times |
| A18 | what the policy switches do to the time path | **complete, 6/6, and no mechanism added.** The first station here to read a trajectory rather than a closing value. Forbearance does not defer the problem, it prevents it: the arm that lets nodes go ends with a claim stock 17.45 times its opening and the arm that keeps them in the market ends at 1.0005. The accumulation belongs to the issuance rule and not to loss recognition, since with the authority off all twelve policy combinations end at exactly 1.0000 |
| A18_B | who pays for forbearance, and what changes when they stop passing it on | **complete, 8/8.** A node below the line is kept going by whoever already lends to it, along the edges already there. The rescue is a loop: the lenders end holding 0.0016% to 0.44% of what they paid less than they would have. The lenders cover 87% of what the rescue asks at the shallow floor and 27% at the deepest, so where the money comes from is a measurement: over 45 cells, new claims credited to the lenders hold the fewest below the line in 23 and end with a claim stock up to 7.53 times its opening, while the two conservative routes end within 2%. When the recapitalised nodes retain instead of passing it on, the count below the line is flat up to 0.95 retention while the claim stock climbs from about 5 to about 32, and at full retention the stage produces claims created that do not circulate: stock 30.9 times, flow 0.893 of the control's, and the only growing flow is lending to the nodes below the line |
| A18_C | where the created claims land, and whether that is what decides anything | **complete, 5/5.** The control for the arm above: the same claims created for the same reason, arriving either on the lenders or spread over everyone still trading. Over 135 paired cells the count below the line is identical in 105 and differs by a single node in 23, so what decides whether created claims circulate is whether the recipient passes them on and not where they arrived. The landing point is not inert everywhere and where it is not is the informative part: its influence falls monotonically as the wage channel strengthens, from 14 of 45 pairs differing with a largest gap of 11 nodes at zero elasticity to 6 of 45 and a gap of 1 at full elasticity |
| A18_D | the rescue as a loan rather than a gift | **complete, 6/6.** Every earlier arm's rescue was never repaid, which put a debt overhang, a rescue that leaves its recipient worse off, and the difference between a bridge and a trap all out of reach at once. Here the rescued node owes what it received to the nodes that funded it and services that before it spends anything of its own. The book closes to the last bit in all 330 rows. A repayable rescue does more with the same balance sheet: the amount delivered exceeds the gift arm's in 97 of 180 comparisons, median ratio 1.34. And the best repayment rate is almost never the largest one on the grid, sitting strictly inside it in 24 of 45 cells and at the largest in 2, so repaying faster is worse than repaying slowly past a point that is interior. At the deepest floor a fifth of everything lent is still outstanding at close, at every rate |
| A18_E | a claim that exists, is owned, and is not in the money that circulates | **complete, 5/5.** Two separate correspondences on this station had ended on the same limit: the graph had no boundary, so holding claims back and holding something outside the trading system were one state, and a repayment could not leave the economy because the creditor is a node in it. A share of a node's holdings now moves out of the accounts the flow routes through, without being destroyed. It is not the earlier switch renamed: under that one the parked stock is zero in 90 of 90 cells and under this one it is above zero in 245 of 245, and in every cell the two move the circulating half in opposite directions. Across the grid the stock rises 22 times while the money that circulates falls to 0.15 of its opening. And output per unit repaid turns sign with the parking rate, from +1.08 to +1.50 with none of it to −0.58 to −0.37 at a fifth |
| A18_F | who carries a forbearance programme | **complete, 3/3.** The same forbearance and the same parking behaviour, funded either from the lenders' own book or from claims an authority creates and hands them, with nothing else different. The grid sits three orders below the arm above it, because that one's lowest parking rate already leaves ninety-two per cent of the stock parked and can only report saturation. The deeper the distress the more the funding route decides: an authority creating the claims buys about thirty per cent more circulation at the shallower floor and four to five times as much at the deeper one, and the count below the line differs in 48 of 60 pairs. The two routes are non-monotone in the parking rate in different shapes, a drift on one and a flip between two values on the other |

**A3 returned two non-positive outcomes, and they are different states, which is
why both are reported with their reason.** A3-5 comes back **void rather than
negative**, and the reason is itself a finding about the mechanism: opening the
high tier is a bitwise no-op in this calibration, because the tier allocates
fully at the opening and no production-layer node can reach it even at a soft
gate. At that tier the exclusion is a **price wall and not a hole**, so there is
nothing there for a gate criterion to measure. A3-6 is a **negative with a number
on it**: the stock exists, and the holding population is 15.8 nodes of 200 with
none of them in the production layer, which is a measured bound on the domain any
wealth-based account can speak about here.

**A3-6 was also why A4 was blocked, and A4 has since run and answered it a
different way.** A4 sets four competing accounts against each other on wealth,
and A3-6 says the wealth is upstairs: sixteen nodes of two hundred, all in the
financial layer. The plan had been for A4 to inherit that stock. It does not.
[`docs/a4_causal_primitive.md`](docs/a4_causal_primitive.md) §10.4 rules that A4
keeps the plain network and takes its stock from issuance instead, because the
population A3's channel could hand it is that sixteen and no more.

**A4 ran, and its discriminant could not be computed.** Not "failed": three of
four live criteria pass and the two voids are voids on grounds registered before
the run. The amplification ratio `A(X)` compares a competitor's effect with
connectivity on against its effect with connectivity off, and no competitor is
readable in both arms. Inheritance and assortative mating transmit dispersion
without creating any, and the complete graph is an attractor at a Gini of
`0.0071` reached in five rounds from any opening, so on that arm they have
nothing to transmit. Education and capital returns create their own dispersion
and are invisible on the stratified arm, where twenty nodes hold `99.7%` of the
stock and any agent-level mechanism moves about `0.3%` of it. One of the two
terms of every ratio is therefore a reading of the graph draw.

Two repairs were registered in §11 before either was run, and both of the
falsification conditions written down with them fired. Measuring on the
production layer alone relieves the Gini ceiling by a factor of six and a half
and still leaves education inside the noise floor. Measuring a transmitting
mechanism on top of a generating one lifts the complete-graph denominator six to
eight fold and still yields no sign-stable cell once the household pooling rule
is set to settle at generations rather than every round. That last control
matters on its own: at the registered rule, ninety-nine point six percent of what
inheritance and assortative mating do on the stratified arm is a household
straddling the layer boundary and acting as a zero-cost conduit across it, not
the channel being measured.

**What A4 does establish is A4-2 and A4-6.** With every competitor off and every
agent identical, switching on nothing but the access structure takes the Gini
from `0.00711` to `0.93673`. And the matching rule, which reads holdings and is
guarded in code against seeing the layer label at all, pairs across the layer
boundary `16.1%` of the time with connectivity on against `17.8%` with it off,
where uniform random gives `18.1%`, at five of five seeds. Connectivity does not
prevent anyone from marrying anyone. It arranges the holdings so that a rule
which never mentions layers ends up respecting them.

**A7 is where A4's ratio stops being readable.** The two arms of a binary `C` are not two
settings of one economy, they are two economies with different state, and a ratio
between them measures the state difference as much as the mechanism difference. A
continuous `C` replaces that ratio with a slope along a path, which does not need
both endpoints live at once. The availability check is done and the continuum is
constructible: interpolating by edge addition takes the centrality dispersion from
`0.161` to `0.000` monotonically with no cliff, the layer gap closes with it
rather than surviving it, and both endpoints are exact rather than limits. It also
lets `C` move one thing at a time, which the binary switch does not: `uniform_access`
collapses the adjacency, the payroll incidence, the routing, the propensities and
the opening holdings together, and the design notes say so.

**A7 is pre-registered and has run: 3 of 7 live criteria pass and 4 are void, and
what it returns runs against this track's own headline.** A7-A-2 finds the registered
shape wrong, a step at the first grid point rather than a gradient; A7-A-4 finds A3-8'
holding nowhere, including where it was derived. Adding 350 edges to 1,039 removes 98
per cent of the compounding divergence and the placebo falls by the same 98 per cent,
while holonomy rises 4.9 and 7.0 per cent. **The reading is that position rent here is
lock-in and not a spread, and one alternative path ends it.**
[`docs/a7_continuous_c.md`](docs/a7_continuous_c.md)
files one registration with two legs, because the holonomy is not computable on
A4's carrier: the loop sum is defined on the `terms` matrix, which lives on
`A3Model`, while `A4Model` subclasses `Network` and has no edge field. Leg A7-A
runs on the A3 carrier and measures `s -> H1 -> D`, where the content is that
A3-8 already removed the same holonomy once with a parameter (`kappa_pay = 0`,
graph fixed) and this removes it with the topology instead, with every kappa left
alone. Leg A7-B runs on the A4 carrier and replaces `A(X)`'s cross-arm ratio with
a slope, scoring `E` and `K` on `log(1/HHI)` and reporting `I` and `M` without
scoring them: the stock those two transmit runs from `28.06%` to `0.00%` of a
generation along the same axis, in the same direction as the amplification the
leg would be claiming, while `E` and `K` are compressed the other way by the Gini
ceiling that section 11.3 already measured. No criterion reads the whole grid,
because A4-1 measured the complete graph to be an attractor and its zero is
overdetermined. The construction parameter is `s`, it runs against `C`, and the
`s = 1` endpoint is not A4's `C = 0` arm.

**A3 has been redefined and it is no longer a merge.** The original plan made it
an integrated simulator that combined the earlier stages. That is now the wrong
target. Stages A0 through A2c measure claim circulation and report levels: a layer
drains, a support set contracts, loops stop being traversed. None of them can
produce a *widening gap* between agents who began level, because none of them has
an asset whose value responds to where claims accumulate.

That channel is where compounding comes from. Claims pile up in the financial
layer, the financial layer bids on assets, holders gain and non-holders are priced
out of entry, and the agents who could not enter at the start cannot enter later
either. The source framework describes this directly, and
[`docs/b1_setup.md`](docs/b1_setup.md) shows why it is load-bearing rather than
decorative: with an asset, a per-period loop sum `δ` opens a gap of `exp(Tδ)`, and
the framework's settlement ratchet turns out to be its non-integrability read at a
different horizon.

So A3 is one mechanism, not four glued together, and the same discipline applies as
before: with the asset channel switched off it must reproduce A0 through A2c
exactly, and those stages remain the control that the channel is measured against.

A0b changes what A1 needs. With a fixed wage bill the production layer settles,
and a default model bolted onto a settled layer can match a level but not a
dynamic. With derived demand the layer has a genuine downward trajectory whose
speed is governed by one parameter, which is the driver a default cascade
requires. Two DFA figures are already recorded in `calibration.py` as A1's
targets: the bottom half of the distribution holds 51.8% of all consumer credit
(`WFRBSB50211`) against 2.5% of net worth.

A3 is gated deliberately. A model with four layers, exhaust valves, quasi-money
creation and a default cascade has enough freedom to produce nearly any output.
Stages A0 through A2 exist so each mechanism carries two or three parameters and
a reader can verify by hand that a result is not an artefact of tuning.

**Track B — non-integrability.** Structural claims: the assertion is that a
global object does not exist, which is universal and cannot be established by
simulating instances.

| stage | subject | status |
|---|---|---|
| B0 | what the non-integrability claim licenses, and what it does not | **complete**, scope-fixing, no measurement. One inequality on one cycle carries it, with no interpersonal comparison, no utility function and no welfare criterion. The four readings it does not license were written down before the stage ran, and the single attack surface is logged as assumption A1: whether the cycles measured are the relevant cycles of the economy or an artefact of how the position space was carved, [`docs/b0_claim_scope.md`](docs/b0_claim_scope.md) |
| B0b | which standard constructs need the object Theorem 1 characterises | **complete**, and it runs no measurement of its own: every empirical assertion in it is a pointer to a criterion already in [RESULTS.md](RESULTS.md). Domar-weighted aggregation is the load-bearing one, because it needs a frontier whose gradient is the price vector, [`docs/b0b_aggregation_and_the_potential.md`](docs/b0b_aggregation_and_the_potential.md) |
| B1 setup | fixing the field so the claim is not vacuous | **complete**, [`docs/b1_setup.md`](docs/b1_setup.md) |
| B2 design | pre-registration, filters, falsifications | **complete**, [`docs/b2_measurement.md`](docs/b2_measurement.md) |
| B2 loop A | dispersion at fixed position and date, where a single scalar price on positions predicts zero | **complete, 7/7** on 20,071,900 loans |
| B2 placebo | conventional against FHA and VA | **complete, 4/4** on a further 8,066,085 |
| B1 theorem | is the partition result a case of the cohomological claim? | **complete, 7/7**, [`docs/b1_theorem.md`](docs/b1_theorem.md) |
| B2 loop B | same dwelling, different entry vintages | **complete, 4/4**, [`docs/b2_loop_b.md`](docs/b2_loop_b.md) |
| B2 placebo validation | is the VA pool actually wide? | **6/9**, the premise survives, [`docs/b2_placebo_pool_width.md`](docs/b2_placebo_pool_width.md) |
| B3 | CIP deviations: cycles that never touch the US Treasury, which vanish if one common convenience yield explains them | complete, [`docs/b3_cip_slice.md`](docs/b3_cip_slice.md); what was checked before retrieval, [`b3_slice_availability.md`](docs/b3_slice_availability.md) |
| B4 | the directed theorem: what survives one-way edges | **complete, 8/8**, [`docs/b4_directed_edges.md`](docs/b4_directed_edges.md) |
| B5 | Argentina, and what the April 2025 intervention did to the agent index | squares **5/5**, zero calibration **2/2**, pre-window guards **1/1 live, 1 void**; two source audits returned REJECT. **B5-14 is void rather than negative**: its pre-window series turns inside the window so no slope can be extrapolated across the edge, and the band it was first judged against was withdrawn for having no theoretical source, [`docs/b5_orphan_prereg.md`](docs/b5_orphan_prereg.md) §6A; what was checked before retrieval, [`b5_orphan_availability.md`](docs/b5_orphan_availability.md) |
| B6-A | reachability typing inside one central bank's own table (Cuba) | ran, the `H1` arm is not in this half, [`docs/b6_cuba_prereg.md`](docs/b6_cuba_prereg.md); what was checked before retrieval, [`b6_cuba_availability.md`](docs/b6_cuba_availability.md) |
| B7 | matrix rank of the cell-by-class interaction on 16m loans | **the class index carries 0.3036 of stage B2's within-term dispersion** over 16,035,398 loans in 326,872 cells, and **there is no single ladder in it**: the 19-class and 6-class cuts read alike. **The stage then measured what its own carrier can support, and withdrew its rank-2 headline on that measurement.** With two classes at 1.18 and 1.37 loans per entry, a constructed field carrying **no interaction at all** reads back exactly 2 in 20 of 20 repetitions, and the second-moment matrix is near-diagonal (off-diagonal correlations max `0.1417`), so per-class noise lands on the diagonal and there is nothing off it for a rank to count. **That bound governs any future rank claim on this data**, which is why no number is quoted, [`docs/b7_interaction_rank.md`](docs/b7_interaction_rank.md) §11 |
| B8 | the slice summand on a household carrier: two realisable routes to one state, which a scalar on states requires to carry equal terms | **closed, 8/8 live criteria, 1 void (B8-4b)**. The residual sum runs on 49,649 modification loops and 35,659 deferral loops over 2,942,295 loans, and this is the strongest of the seven carriers. B8-4b waits on C9, and section 15.3 puts that outside the stage's scope, [`docs/b8_fannie_slice.md`](docs/b8_fannie_slice.md). Instrument conclusions the published criteria lean on: [`b8_instrument_notes.md`](docs/b8_instrument_notes.md) |
| B9 | the measured zero, and the path share | ran; the ETF creation triangle carries a non-zero holonomy of 1.2 to 1.7 bp and its quantization explanation is falsified. The stage is under re-audit, [`docs/b9_zero_holonomy.md`](docs/b9_zero_holonomy.md) |
| B10 | Freddie as a carrier, and the shape of the state graph | **closed.** The holonomy machinery was rebuilt on a second GSE: 1,362,490 loans, 74,937,616 monthly rows, 28 vintages. The structural reading is the cheap one and it bounds every path design on this data: **of 10,816 possible ordered state pairs only 1,496 ever occur, 13.83 per cent**. The stage also names what its carrier stops recording in mid-2019 |
| B11 | corporate credit as the second domain | **open, and the readings taken before the gate are now in [RESULTS.md](RESULTS.md).** The branch table in B8 section 15.6 sends the second domain here; the domain was not chosen. The ceiling is counted rather than assumed: the distressed-exchange marker appears on **422 rows over 227 issuers**, 2012-06-15 to 2025-07-01, against a gate of 200, so the investment-grade filter has to retain 88 per cent to clear it. **Registered and sequenced: C11-0 is the next run** |
| B12 | grid invariance | **closed, and it binds rather than clears.** Every three-bin threshold cut of the delinquency ladder is enumerated whole, so nothing is ranked and no null is needed. The between-class spread of median holonomy moves **4 to 17 times across cuts**, over the registered line on all six vintages on one arm and on three of six on the other. **Per-loop holonomy is untouched and that half is structural**: coarsening changes which loops are the same loop, not what any one of them sums to. So what this binds is every quantity aggregated over cycle classes, and **the 30/60-day convention is not neutral** |
| B13 | the zero domain | **closed, 7/7 criteria, in a day, on the vendor's free public sample.** The framework names where its own quantity must be zero and then measures it on CME implied quotes: never worse than the two-leg derivation in **81,968 states** over nine products and three channels, exactly equal on six of them, while the directly quoted member of the same family is non-zero in 65 to 96 per cent of states. **The explanation first given for the six-versus-nine split is withdrawn** and B13-2 carries the withdrawal. It also produced the first measurement of both halves of B4 section 5.1's split |
| B14 | a dated, exogenous, symmetric friction change | **the gate passes in both directions.** The SEC tick size pilot is the carrier B4 section 9 asked for. Imposing the 5-cent grid in 2016 widens the treated spread against the control, six inequalities of six, and it holds under every weighting and adversarial convention tried, thirty of thirty. **Lifting it in 2018 narrows them again, six of six**, once both rounds are read on the securities they share: the venue's Appendix B coverage runs 618 distinct symbols in March 2018 and 2,110 in April, between the two rounds. Four of the six cells then sit outside every gap measured on window pairs where nothing happened, taken both inside the pilot and after it. **Closed rather than paused**: the index half was bought and cannot be adjudicated on this carrier, and the reason is structural. `S - S'` is a difference of price levels and a tick-size change works by moving those levels onto a lattice, so projecting the post-release quotes back onto the nickel grid reproduces **88.7 per cent** of the whole move and the residual sits inside a placebo band. What the stage produced instead is a carrier specification |
| B15 | Bolivia, as the control carrier for B6 | **closed, and it is B6's zero calibration.** B6 found an edge the law grants, that is posted, and that nobody walks, on 207 of 207 Cuban publication days, and the one thing that reading could not establish about itself is whether the instrument says as much of any economy with an official rate and a parallel market beside it. **It does not.** The register was sealed before a single Bolivian number was downloaded and four of its thresholds are B6's own values carried over unchanged, so one ruler measures both carriers: Bolivia reads **21 of 52** against the same 95 per cent. **B6-15 is therefore a fact about Cuba rather than a reflex of the method.** What the instrument tracks is sharper than the contrast. Measured against Bolivia's own frozen peg the same window reads 100 per cent, and against what the banks were actually selling at, 65 per cent; after the peg went and the official rate began to follow the market, 40 per cent. **A posted price nobody transacts at is what produces the Cuban reading**, and the reading falls when the official rate becomes one somebody trades at **Register and readings are both published here**: [`b15_bolivia_prereg.md`](docs/b15_bolivia_prereg.md), [`b15_bolivia_results.md`](docs/b15_bolivia_results.md) |
| B16 | a purchased-quote carrier, pre-purchase checks only | **open, nothing judged, nothing bought.** Every check run so far was free. The second gate needs the observed dispersion of the statistic, which needs quotes, so the registered order is to buy the smallest arm first, compute the gate from it, and let that decide whether the other five are bought at all. **The screening rule is frozen; the symbol list is not** |
| B17 | how many independent directions the parallel-rate deviations occupy | **closed**, on Argentina's simultaneously quoted legal conversion tracks, from files already on disk. **Nothing was bought.** Two carriers were screened out on paper before this one, before any data was bought: a GSE monthly panel whose cycle count ran from 1275 to 1 as the state definition changed with no cut having a source, and a depositary-receipt design |
| B18 | the directional remnant in the direct book | **closed on the instrument's resolution, nothing bought.** One trading day, 295 spread contracts, 3,895,656 snapshots. Absence happens in runs, so counting runs rather than snapshots puts every contract's `A_s` inside two standard errors of zero. See [RESULTS.md](RESULTS.md) |
| L2 | what is left of B14's move after the arithmetic is taken out | **opened on B14's carrier and free.** B14 closed with its index half unadjudicated because the lattice projection reproduces 88.7 per cent of the move. L2 asks whether the residue is arithmetic or behaviour, and **imports B14's sample, windows, pure-slack definition and group assignment character for character rather than restating them**. The residue has the wrong sign to be arithmetic |
| square complex | curl against harmonic on `Γ` | **withdrawn**, see B1 §12 |

**Three of those rows are newer than the narrative that follows them**, which was
written when loop B was the next thing. B3 has since reached the slice summand
that Corollary 2 says no volume of mortgage data can touch; B4 removes the
standing prohibition on directed agent edges and replaces it with a narrower one,
that a carrier with a bid-ask spread may report `S − S'` and never a single
orientation; and the square complex is not merely unbuilt but **withdrawn**,
because filling the squares of `Γ` leaves the harmonic component identically zero
on every field this project runs, so the refinement it would deliver is an
identity dressed as a measurement.

**The placebo validation row exists because a premise was doing work unmeasured.**
The graded placebo's load-bearing comparison is conventional against VA, and it
rests on VA's borrower pool being as wide as conventional's. That was argued from
programme rule and never looked at. It now has been, on the borrower-capacity
fields the retrieval kept: at fixed position the VA pool is 97.7% as wide as the
conventional pool on the tail-insensitive measure, and wider than FHA's on every
measure tried. Three criteria fail and none of them touches that comparison.

**The B1 theorem was taken before any further retrieval, and it changed the
ordering that follows it.** The question it settled was whether stage B2 had
exercised the framework's machinery at all: loop A's decomposition runs over a
partition rather than a graph, so until Theorem 3 the honest description of the
result was "an analysis of variance we believe is related to a topological claim."
That description is worth little, because conditional dispersion in mortgage
pricing is already documented and a framework that re-derives it has contributed a
vocabulary rather than a result.

Theorem 3 shows the within share **is** the `L²` norm of the square component,
halved, and on this carrier the square component is the whole non-exact part
because the harmonic one is identically zero
([`docs/b1_theorem.md`](docs/b1_theorem.md) §12). Same number, different object,
and only the second is something the
framework can be judged on. Getting FX data first would have risked measuring the
wrong thing entirely — a mistake this project already made once on paper,
conflating carry returns, which are compensation for bearing risk, with
covered-parity deviations, which are the loop sums that actually fail to close.

Theorem 2 then reorders what remains. Mortgage data reaches squares only, and no
sample size changes that, so **FX stops being a robustness check and becomes the
only available carrier for the other summand**. Loop B goes first regardless: it
needs no retrieval, FHFA publishes the vintage shares as aggregates, and Theorem 1
has just shown its disconnection argument to be a structurally different claim
rather than a weaker version of the same one.

The working approach is discrete rather than smooth. On a finite graph, curl is
a sum around a cycle, the cycle space has dimension `E − V + C`, and the first
cohomology is a rank computation on the incidence matrix. The discrete Hodge
decomposition splits any flow into gradient, curl, and harmonic parts — which is
exactly the three-way split the argument needs, and it is computable on real
input-output data. The headline quantity is one scalar: what fraction of an
observed price field is integrable.

The first task in Track B is not a proof. On a single-currency price vector,
integrability holds **by identity**: writing `R_ij = p_j / p_i` makes every loop
sum zero as a matter of notation, so a theorem about that field would be a theorem
about the empty set. [`docs/b1_setup.md`](docs/b1_setup.md) fixes the object
instead: the field is the *two-index* effective cost `P(a, j)`, the terms on which
agent class `a` can obtain `j`. A single price vector is the special case where
terms do not depend on who is transacting, which is an assumption about an economy
rather than a description of one. That document also records a correction: the
obvious rent-versus-own example is currently false in the direction usually
assumed, and why the dispersion of the loop sum is better evidence than its sign.

What to measure is fixed in
[`docs/b2_measurement.md`](docs/b2_measurement.md), written as a pre-registration
before any data is retrieved. Two loops, and the division between them is the
substance of the design.

**Loop A holds the date fixed.** Same quarter, same census tract, same lien, same
purpose, same occupancy: applicants receive different rates, and a cash buyer
carries no financing term at all. Position identical, date identical, market
identical, terms different by who is transacting. There is no finer position space
to retreat to, because the position was already held fixed. This is the loop that
establishes the field carries an agent index at all.

**Loop A is done and it passed**, 7/7 with the placebo at 4/4, on 28,137,985 loans
across three programmes. The result, and the artifact it had to be corrected for,
are in [`docs/b2_measurement.md`](docs/b2_measurement.md).

**Loop B holds the dwelling fixed and varies the entry date.** This is where the
magnitude is: FHFA's National Mortgage Database reports the share of outstanding
fixed-rate mortgages below 4% peaked at 65.1% in Q1 2022 and stood at 49.9% in
Q1 2026, against new originations at market. Roughly half the holders of the same
position face materially different terms from the other half.

**Loop B is done and it passed**, 4/4 over 53 quarters of FHFA's National
Mortgage Database. The bound on vintage dispersion is 0.8479 in 2026 Q1 against
loop A's 0.3363, and it exceeds loop A in 46 of 53 quarters. The registered
prediction most likely to fail was that the wedge predates the 2022 repricing;
the mean over the 36 quarters before 2022 is 0.4043, so the repricing raised it by
64% rather than creating it. **The larger number is the weaker evidence**, and
[`docs/b1_theorem.md`](docs/b1_theorem.md) is why:
loop A's figure is a holonomy and loop B's is a component separation, because a
below-market mortgage cannot be transferred and so no cycle closes.

Loop B alone would not have been enough, and the document says so. A critic can
answer it by saying the two owners hold different assets, a dwelling plus a 3%
contract against a dwelling plus a 7% one, and that is correct as stated: entry
date is a coordinate rather than an attribute of the holder. Loop B survives, but
only via the hole, since the 3% contract cannot be purchased and integrability on
a space you cannot move around in is vacuous. That argument is worth making and it
is second-order, so the paper leads with A.

The document also records what the public data cannot do. HMDA's loan-level file
carries rate spread but **redacts credit score**, so it establishes that dispersion
exists at fixed position and date without attributing it. Non-integrability needs
a non-zero loop sum; it does not need the loop sum to be explained. Attribution is
a separate and weaker claim, made with FHFA's credit-score-banded aggregates and
labelled as such.

A third correction is recorded rather than quietly fixed: **asset tier is not agent
class.** A landlord buying down-market units to rent and hold is a high-class agent
holding a low-tier asset, and pooling by price tier averages that landlord together
with the household that could reach no higher tier. HMDA's occupancy type separates
them, and every cell in the panel is crossed by it.

Finally the document fixes, in advance, the test separating a structural
per-period wedge from one episode of repricing, and eight observations that would
falsify the claim.

Track B needs no simulation output and does not wait on Track A. Stage A2c is
*not* part of it: measuring cycle structure on the graph built here is description, and
only the same computation on real data would be a finding. A2c can motivate the
theorem's introduction; it cannot support it.

That separation held until B1. It no longer describes the whole repository: by
Theorem 3, stage B2's within share is a cycle-sum norm on a graph built from real
loans, so the cohomology is now exercised on data and not only on a simulation.
The A2c caveat stands as written, because it is about A2c.

---

## Provenance

These models formalise mechanisms from a longer framework document, *A
Topological Framework of Claims and Resources*, which is not part of this
repository. Where the framework and the implementation disagree, the
implementation is annotated: three of its settings were changed during
development because the first version was not faithful to the source, and the
comments in `config.py` say which and why.

The framework's own standard for a good theory is internal consistency,
portability across parameter regimes, explanatory reach, and prediction of
phenomena not used in its construction. This repository is an attempt to make
the first and the last of those testable rather than asserted. Where a criterion
fails, RESULTS.md says so.

## How to cite

Machine-readable metadata is in [CITATION.cff](CITATION.cff). GitHub renders it
as a "Cite this repository" button and it converts to BibTeX and APA from there.

**Cite a specific result by its criterion identifier, not by a section number.**
`B8-3`, `A5-6`, `B7-16` and the rest are stable: they are the names the
pre-registrations gave those criteria before the runs, and they do not move when
a document is reorganised. Section numbers do move. RESULTS.md is indexed by
stage and criterion for this reason.

**A criterion that failed is citable on the same terms as one that passed.** The
record keeps both, including three withdrawals and the criteria that were void
on their own registered estimator. Citing a passing criterion without its
attached scope limits is a misreading of the record rather than a shortening of
it; each stage's limits sit in its own document under `docs/`.

## License

MIT. See [LICENSE](LICENSE).
