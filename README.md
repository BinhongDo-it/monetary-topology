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

**Status. All three tracks have run, and the measurement work stands on carriers
in separate regulatory environments**, each of which returns a non-zero reading
against two different zeros. One is a floor that is measured rather than
asserted, which says the reading can be seen. The other is **a point prediction
of exactly zero, made by the account this repository tests**: if a single scalar
price vector on positions exists, every closed loop sums to zero **however much
the contract changes along the way**. [CARRIERS.md](CARRIERS.md) is the list of
what was read and [RESULTS.md](RESULTS.md) is the record of every reading taken
off it.

**The readings against that prediction come in three shapes, and they are kept
apart because collapsing them into one word makes the strongest of them
uncheckable.**

**One, the loop sum or the square sum itself.** Mortgage modification is the
strongest, at `1.07e+05` to `4.18e+06` times its own floor across six vintages in
the same direction, with a within-cell permutation null of 0 of 999 in every
cohort. Cross-currency funding cycles that never touch one issuer run 30.9 to
45.6 basis points. The ETF creation triangle stands at 1.05 to 5.08 times the
measurement floor, on 11 of 11. China's domestic price against its own border
price clears the printed-precision floor on 106 of 106 squares, at a median of
51.7 times it, with 54 of the 106 independent. European household energy against
industrial clears it on 1,069 of 1,076 cells at a median of 103 times. The two
non-resaleable energy carriers clear it on 39 of 39, the smallest at 7.4 times.
And a declared conversion between physical quantities is multivalued: across the
published standards that quote them, 88 species can be judged, and **the number
whose loop product is exactly 1 is zero**, at a median of 1.4150 and a largest of
60.640.

**Two, the same point prediction read on a different object.** Hold census tract,
year, lien position, loan purpose, occupancy and dwelling type fixed, and the
dispersion that remains inside those cells is `0.7831` where a single price vector
predicts zero. One central bank's own table carries a one-sided bound that its law
grants, that is posted, and that nobody walks, on 207 of 207 publication days.
Fifteen independent orderings of the same universities admit no common refinement
on **any of 105 province pairs**, in either of two disjoint cohorts. The rank of
the obstruction to a scalar price potential, on city prices and again on cash
grain, clears a conservative floor in both.

**Three, the counting law on a published table.** A programme that names classes
and writes a figure against each produces exactly as many distinct prices as it
writes distinct class values, and that is an identity with no resolution limit in
it. A published benefit scheme's five classes produce six clause vectors that
coincide on no dimension. A tax code writes five filing statuses and prints four
cells. A tuition corpus writes three classes in whole dollars. A licence fee
schedule carries 45 distinct figures in 104 cells.

**One carrier returns both a zero and a non-zero from the same apparatus on the
same feed on the same day**, which is the only place in the record where the
framework named which side would be which before anyone looked: implied spread
quotes are never worse than their own two-leg derivation over 81,968 states, exact
on six of nine products, while the directly quoted member of the same family is
non-zero in 65 to 96 per cent of states.

**One track reads a directed cycle rather than an undirected one**, where the
question is not whether a potential exists but whether a *sub*-potential does, and
it arrives with its own zero calibration measured on a second country under the
same register.

**Three further carriers put the same question where friction cannot be the
answer, because nothing on them is traded.** An institution that declares one unit
of `a` to be `R(a,b)` units of `b` asserts the same scalar, and the loop product
must still be 1. A comparable institution of the same scale and age, asked the
same question, agrees with itself, so the multivalued reading above is not about
bureaucracies.

**Three results are about the instruments rather than about the world, and each
bounds what may be claimed anywhere in the record.** One built a counterexample
against its own headline and measured what its carrier can support, which
**bounds every future rank claim on that data**. One measured that its own
pre-window turns inside itself, and **removed a threshold that had no theoretical
source**, so no arbitrary calibration grounds a negative anywhere here. One
answers the sharpest objection in the programme by **measuring the instrument's
own resolution and reporting the number**, which settles what that objection can
and cannot be tested with. See [RESULTS.md](RESULTS.md) for the full record, and
the index by field below for which stations sit in your field.

This repository gives an exact criterion for when a single scalar price vector on
positions exists, proves it with no economic assumptions in it, and measures it on
financial carriers and on carriers where nothing is traded. Which standard
constructs presuppose that object, and what each of their setups states, is in
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
value and whichever way it came out, is in [RESULTS.md](RESULTS.md), under the stage
that produced it, and a stage that ran in more than one round carries more than
one block there. `docs/` holds a prose document for the stages that have one, and the
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

**[CARRIERS.md](CARRIERS.md) is the map by what was read**: one row per object
in the world this programme took a reading off, grouped by what kind of object it
is and by what the readings off it ask, with the stations that stand on each. It
carries two counts and both are computed from the table rather than typed into
it: how many distinct objects, and how many economies, jurisdictions and separate
published schedules sit inside the ones that are themselves cross-sections.

**[INDEX.md](INDEX.md) is the map of the ledger**: one row for every block in it,
sorted by station, each linked to the section it names, with a few routes through
it at the top for a reader who wants one subject rather than all of them. The
table is generated from the ledger's own headings by `scripts/make_index.py`, so
a block cannot be in the ledger and missing from the map. `--check` says whether
the map is current and `--selftest` plants faults in it and checks they are
caught.

### Which stages have a prose document, and which do not

**[INDEX.md](INDEX.md) carries the link for every stage that has one**, in its
third column, generated from what is on disk. This section says only what a link
cannot, which is why the others do not, since that is a convention rather than an
omission.

**The four earliest A-track stages never had one.** A0, A0b, A2 and A2c each
isolate one mechanism in a few dozen lines, and the design is legible in the
experiment file itself. Their readings are in [RESULTS.md](RESULTS.md).

**From B10 onward the criteria are written in the experiment script, the record
each run writes carries them verbatim, and the reading goes into
[RESULTS.md](RESULTS.md).** **What is published is the evidence**:
`experiments/<stage>_*.py` and the committed `results/*.json` beside them, which
is what someone re-running a stage actually needs. The A-track stages built after
A7 are scored the same way.

**A stage gets a file under `docs/` when it holds something a record cannot**: a
proof, a derivation, a carrier specification, or an account of how several arms
fit together. That is why every station from B63 to B96, which is where standard
price theories are recovered as special cases, carries one, and why several
measurement stations whose whole content is a table of criteria do not.

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

**Every C-track stage carries a document**, and one more besides:
[`docs/c_track.md`](docs/c_track.md) is the account of what the three of them
together license, which is a thing no single stage's document can say.

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
own commitments turns out to produce.

**Say exactly where the world enters, because "no empirical input" would be too
strong and an easy thing to catch.** Building the mechanisms used none: the
positions, the rules and the accounting in the earliest stages come from the
framework and from nothing that was measured. Checking them used plenty, because
checking is comparing an output to something observed, and the later stages are
inferences of the form *if this object is put into these mechanisms, what comes
out*, read against what the world shows. **What is absent throughout is fitting.**
No parameter is chosen to move an output toward a target, no series is regressed
on, and the sweeps are declared ranges rather than searched ones. A reading that
lands near an observed magnitude is therefore worth what the chance of missing it
was, and a reading that lands far away is reported as it came out. The credit in reproducing something is
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
absent from A0 and stays absent through most of the track: the authority issues,
and no matching liability is created anywhere. A41's second block is where it
opens, behind a switch of its own, and a line of credit there makes a negative
holding a debt owed to the house. The other four were scope restrictions on A0 rather than on
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

## Two readings from the price-field stations

**How many dimensions the obstruction to a single price level occupies, stage B38.**
Treat price as a field with two indices, one for the item and one for the city.
A single scalar price level per city means `log P(i,c) = a_i + m_c`, which is
rank one in logs and makes every square exactly zero. That is Theorem 1's
premise, and it is what every spatial price index and every purchasing-power
construction assumes without stating. **What this stage measures is the rank of
the departure from it, which no competing account has a reason to compute**,
because only this framework says the rank is what survives.

The counting law and the two-way decomposition turn out to be one object: on the
complete bipartite graph `b1 = E - V + 1 = (I-1)(C-1)`, which is exactly the
number of free parameters the residual keeps after row and column effects are
removed, and both were computed and printed at 66,886. Currency never enters,
because converting a city's prices adds a constant to its column that the city
effect absorbs, so the stage runs on every city at once with no exchange rate in
it. On 53 items across the 1,263 cities carrying all of them, with no imputed
cell, **at least eight directions clear a floor that concedes the entire
residual to measurement error**, and the median square sum is 9.4 times the
noise a square carries. **So a spatial price index cannot be repaired by adding
a few correction factors**: a rank-`k` approximation needs far more of them than
anyone fits. Two accounts that would explain the residual away were put against
their own predictions and did not carry it, and an independently collected
posted price -- a chain's menu price, gathered by people with no contact with
the first source -- sets the bound the reading is stated on.

**The same criterion run once inside each of 64 countries, stage B30-5.**
Items were sorted in advance, from their descriptions alone, into those a single
brand posts nationally and those produced where they are sold, and each
country's cities were regressed separately: countries are never pooled, because
pooling puts currencies, tax regimes and different brand sets on one line.
**The nationally posted class sits below the locally produced one in 53 of the
64 countries that meet the minimum**, on an assignment written for one country
and never re-tuned, and no country's posted class approaches the value that would
close the question the other way. The class assignment carries no country-specific
tuning, so the count has an exact null and needs no threshold on any coefficient.
The registered level for the locally produced class is not what the countries
return, and RESULTS.md reports the ordering and the level apart.

## What the standard account needs in order to have one price

This framework's condition for a single price to exist is one sentence and it is
read off numbers that are already posted: **every loop sums to zero**. Theorem 1
says a potential exists exactly when that holds, so the condition is a property of
the measured object rather than of the model built around it.

The standard account needs the same thing and states it as a conjunction. Its
sources are precise about this and the wording is theirs.

**Completeness buys uniqueness of the discount factor.** In Cochrane's Asset
Pricing: *"If markets are complete, there is nowhere to go orthogonal to the
payoff space X, so m\* is the only possible discount factor."* That settles
uniqueness inside the payoff space, and it settles nothing about whether any
particular participant's valuation equals it.

**What settles that is a separate assumption, and the same text names it and names
what it excludes.** The pricing equation for a given investor is that investor's
first-order condition, reached because *"the consumer buys more or less of the
asset until this first order condition holds"*. The condition for that step is
free portfolio formation, and Cochrane calls it out: *"Free portfolio formation is
in fact an important and restrictive simplifying assumption. It rules out short
sales constraints, bid/ask spreads, leverage limitations and so on."*

**The general-equilibrium form of the same requirement is longer still.** Shell's
own account of the Cass-Shell sunspot immunity theorem, the result that says
variables with no bearing on fundamentals leave equilibrium alone, has it hold
under a full range of perfectly competitive markets together with strictly convex
preferences, convex production, a finite horizon, agents sharing beliefs about the
extrinsic variable, and full participation. It fails under restricted
participation, under incomplete markets, and under an unbounded horizon.

    the standard account   complete ∧ strictly convex preferences ∧ convex
                           production ∧ finite horizon ∧ shared beliefs ∧
                           full participation
    this framework         every loop sums to zero

**Two of the conjuncts have to be supplied by whoever is doing the modelling
rather than read from anything.** Which state space counts decides completeness,
and who counts as a participant decides the rest. Both are choices, and the second
one is the sharper problem: **a person who does not trade because doing nothing is
optimal and a person who does not trade because a rule stops them leave the same
record.** They are not two cases that resemble each other. Where there is a
bid-ask spread there is a band inside which no trade is strictly best and the
marginal condition holds only as a pair of inequalities, so one person is
simultaneously trading voluntarily and unpinned. Watching for longer does not
separate them: a participant who is always constrained and one who is free and
happens to be stationary generate the same series unless something perturbs them
across the band. **So free portfolio formation is not identified from behaviour.**

This framework does not have to identify it, for a reason that is arithmetic. The
number of independent loops on a graph is `b1 = |E| - |V| + c` with `c` the number
of components. An isolated vertex adds one to `|V|` and one to `c`. A vertex
attached by a single edge adds one to `|V|` and one to `|E|`. Either way the count
does not move:

    base graph, two independent loops       b1 = 2    V=4    E=5
    plus 100 isolated onlookers             b1 = 2    V=104  E=5
    plus 100 onlookers on one edge each     b1 = 2    V=104  E=105
    plus 1 participant who opens a
      second route between two positions    b1 = 3    V=5    E=7

**Who counts as a participant is therefore not a question this framework has to
answer.** Nobody has to be excluded from the count, because onlookers do not
change it. What changes it is whether a second route exists between two positions,
and that is something to count rather than to judge.

The same substitution runs through the empirical stations. Where the standard
account infers the constraint set from what people did, the stations here read the
rule that draws it: which credential an operator issues and how many of them,
which article of a statute names which classes, which clause of a filed tariff
prices which case. Stage B57's reading that seventeen pairs of merged classes sit
at sellers issuing a separately applied-for credential per class stands on the
operators' own pages, not on an inference from the merge itself.

Two further notes on where this sits. **The exclusion list quoted above names
bid-ask spreads**, and a bid-ask spread is exactly a two-sided edge whose terms
differ by direction. That case has a theorem here rather than an exclusion.
Theorem 4 says a sub-potential exists, meaning a consistent price vector no
available move beats, exactly when every directed cycle sums to at most zero; and
Theorem 6(2) says that sub-potential has every slack zero, which is the equality
case, **only when the symmetric part of the field vanishes and the antisymmetric
part is exact**. So absence of arbitrage buys the weaker object and buys nothing
about exactness, the two parts are separately non-zero and separately measurable,
and Theorem 6(4) bounds one by the other so that the registered quantity is a
ratio in the unit interval rather than a raw difference. And Shell's account adds
that
imperfect and monopolistic competition are highly prone to sunspot effects, while
market power is the first of the three conditions the price-discrimination account
needs before it applies. **Those two strands speak about the same domain from
opposite directions**, and the readings collected here sit in that domain.

## How to read a result the rival account also gets right

A reading in this repository sits somewhere on two axes: whether this framework gets
it right, and what the rival says about it. The rival is stated above and is the same
one throughout: **a single scalar price vector on positions**, whose gradient generates
every term, and which therefore predicts that every closed loop returns exactly zero.

|  | rival right | rival wrong | rival silent |
|---|---|---|---|
| **framework right** | **A**, shared explanation | **B**, discriminating | **D**, a quantity only this framework has reason to compute |
| **framework wrong** | **C** | both wrong | wrong, and nothing on the other side says so |

**The bottom row is failure. Labelling it and stopping there would be the wrong
report**, because failures differ in kind and in size and the difference is the part
worth having.

- **C.** The framework is wrong where the rival is right. This is the only cell of the
  bottom row that has been in play here, and it is empty. Every falsification
  condition on this track is fixed before the data it applies to, and none has been
  hit: across every committed record, the number of `rival` criteria that did not pass
  is zero. **That is a count and not a claim about what is possible**, and it is read
  off the records by `scripts/fail_census.py` rather than kept in this file, because it
  moves every time a station is added.
- **Both wrong.** Two accounts failing on the same reading are not failing the same
  way. A mechanism that has the order of its steps wrong is a different object from a
  result with no mechanism that produces it, and they cost different amounts to repair.
  A cell entry here has to say which kind and how large, or it says nothing.
- **Rival silent.** The framework is wrong and the other side carries no information
  about it either way. Nothing external corrects this one, which is what makes it the
  expensive cell rather than the empty one.

**A is not a demotion.** A more general account giving the older one's answer where the
older one is right is a requirement on it, not a defect in it. General relativity
returns Newton's number in the Newtonian limit and a different one at Mercury's
perihelion, and there is no cell in which Newton is right and it is wrong. Writing "so
this reading does not count" about an A-cell result is a mistake this repository made
for a while and does not make any more.

**D is where most of this repository's output sits**: support-set size, the integrable
fraction, the loop sums themselves. The rival is not answering those incorrectly. It has
no reason to compute them.

**Reading the cells requires the rival to be fixed first, and that is the step most
easily got wrong.** Explanations of *why* a loop sum is not zero, in terms of spreads,
fees, execution cost or constrained capital, are not the rival here. They concede the
non-zero and then argue about its source, which is a later argument and a different one.
Treating them as the rival moves results out of B and into A, and this repository did
exactly that with seven carriers before correcting it.

## Scope

- **What puts a position on the graph is whether an edge CAN form, not whether
  one currently does, and not distance.** Two positions belong to the same graph
  exactly when the possibility of an edge between them persists: there need be
  no edge at any given moment, but the possibility has to stay. A thing is off
  the graph only when no edge could form between it and anything on the graph,
  which is physical isolation. **So the graph is not a map. It is one
  circulation body that is not physically partitioned**, and two cities inside
  one such body plainly can form edges, so *moving between them does not leave
  the graph*: it is a change of edges inside it.

  This forecloses a reading that otherwise looks like a hole: "the model has no
  geography, so it cannot do migration, so it cannot speak to employment
  separating from population." **Neither step holds.** Position is defined by
  edges, so migration is edge rewiring, which is a native operation here and is
  implemented with its own published anchors. Even the most complete version of
  moving, cutting every edge at once and reconnecting at the destination, is
  an operation inside the graph, and it is all-or-nothing rather than half,
  which is also what the evidence on losing a position shows.

  **What is genuinely out of scope is not migration but "elsewhere."** A closed
  economy has one graph and no elsewhere, so a ratio whose denominator counts
  people who left the region needs two graphs and the flow between them. **That
  is a different carrier, not a missing mechanism**, and treating the carrier's
  boundary as a hole in the theory is the confusion this paragraph exists to
  prevent.
- **The object is structure, not timing.** Almost every quantity here is a property
  of a configuration rather than a forecast. Where a station does reach past the data
  it holds, it is named: B59 registers a hypothesis about a rate change whose data did
  not exist when the hypothesis was written, with the window, the statistic and the
  verdict each cell maps to all fixed in advance.
- **Levels are entered as published, not estimated from a target.** Nothing is
  fitted, so a match to a series is evidence rather than construction. Stage A1 is
  the first place the model is asked to meet one.
- **Whether reproducing a stylised fact is worth anything depends on how many
  knobs this model has on that fact, not on how many papers report it.** The
  credit in reproducing something is exactly the chance it could have failed to.
  A model with a few million parameters reproducing the standard agent-based
  stylised facts earns nothing, because failing would have been the only
  newsworthy outcome; a model whose positions are fixed before the run could
  fail, so the same reproduction is informative. **The rule is therefore to
  write down two numbers before paying for a fit: how many knobs can move, and
  how many targets have to be met**, and to declare which targets are used to
  fit and which are held back. A fit with at least as many knobs as targets is
  not worth running, because only one of its outcomes is reachable. The
  stylised facts sit in an appendix at stage A3 and no criterion rests on them,
  which is a statement about that appendix rather than about the class of
  facts.
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

python experiments/a0_retention.py       # one stage, and this is the way in
python experiments/b52_europe_class_square.py

python -m pytest -q                      # the invariants, and they are assertions
```

**A single stage is the way in.** Each is one file under `experiments/`, takes
`--rounds N` and `--seeds N`, writes its record to `results/`, and exits non-zero
if a live criterion fails. Nothing else has to be working for that to run.

**`scripts/run_all.py` is superseded and is not the way to run anything here.**
It was the middle link of a chain that ran a batch of stages, regenerated
`RESULTS.md` from the records, and had continuous integration compare the two.
All three ends of that chain were retired on 2026-08-21: the generator, the CI
trigger, and the ratchet that had required every record to have a job in it. Its
job table covers a minority of the scripts under `experiments/` and has not
tracked the ones added since, so whether a station appears in it says nothing
about that station. It is left in place rather than removed, and
[RESULTS.md](RESULTS.md) is the index.

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
  make_index.py        writes INDEX.md from the ledger's own headings
  make_carriers.py     writes CARRIERS.md from the carrier table it holds
  check_dead_links.py  every document reference, resolved against the disk
  fail_census.py       every criterion that did not pass, counted by what it asks
  run_all.py           superseded; see the section above
docs/            one file per stage that holds something a record cannot:
                 a proof, a derivation, or a carrier specification
tests/           naming follows the stage, so `test_a4_*.py` are
                 A4's guards and each asserts one claim its docstring states
figures/         committed; they are the artefact
results/         committed; machine-readable run records
speedrun/        README.md is the index by field: which stations sit in
                 which field, what they found in that field's vocabulary,
                 and where to read them
data/            not committed. SOURCES.md records provenance
```

`INDEX.md` and `CARRIERS.md` sit beside `RESULTS.md` at the top level and are
generated. Each takes `--check`, which says whether it is current, and
`--selftest`, which plants faults in the generator and checks they are caught.

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

## The three tracks

Three tracks, run in parallel, answering different kinds of question. They were
built apart, and where a later station needs an object an earlier one already
constructs, it imports it rather than rebuilding it: the classical price stations
draw their productive systems from stage A19's industry generator.

**Where each station is.** [INDEX.md](INDEX.md) lists every block in the ledger,
sorted by station and linked to it, with a few routes through it for a reader who
wants one subject rather than all of them. [CARRIERS.md](CARRIERS.md) lists the
same work by what was read rather than by station number.
[RESULTS.md](RESULTS.md) is the record itself and is the authority on any of it.
This section says what the three tracks are for; it does not carry a station list,
because a list kept here by hand falls behind the ledger and then misleads.

**Track A, distribution dynamics.** Computational claims: whether a support set
contracts is **parameter-dependent rather than structurally guaranteed**, and the
sweep maps where it does and does not. The track starts at A0's construction,
which the section above states in full, and every mechanism added after it sits
behind its own switch, is off by default, and reproduces the earlier results bit
for bit when it is off. Two published figures are its calibration targets, and
they are entered rather than fitted: the bottom half of the distribution holds
51.8% of all consumer credit against 2.5% of net worth.

**The asset channel is where compounding enters, and that is why it is a stage of
its own.** Stages A0 to A2c measure claim circulation and report levels: a layer
drains, a support set contracts, loops stop being traversed. None of them can
produce a widening gap between agents who began level, because none of them has an
asset whose value responds to where claims accumulate. Claims pile up in the
financial layer, that layer bids on assets, holders gain and non-holders are
priced out of entry, and the agents who could not enter at the start cannot enter
later either. [`docs/b1_setup.md`](docs/b1_setup.md) shows why that is
load-bearing rather than decorative: with an asset, a per-period loop sum `δ`
opens a gap of `exp(Tδ)`, and the framework's settlement ratchet turns out to be
its non-integrability read at a different horizon.

**Track B, non-integrability.** Structural claims: the assertion is that a global
object does not exist, which is universal and cannot be established by simulating
instances. The approach is discrete rather than smooth. On a finite graph, curl is
a sum around a cycle, the cycle space has dimension `E − V + C`, and the first
cohomology is a rank computation on the incidence matrix. The discrete Hodge
decomposition splits any flow into gradient, curl and harmonic parts, which is
the three-way split the argument needs, and it is computable on real data.

**Fixing the object is the first task, and it is not a proof.** On a
single-currency price vector, integrability holds by identity: writing
`R_ij = p_j / p_i` makes every loop sum zero as a matter of notation, so a theorem
about that field would be a theorem about the empty set.
[`docs/b1_setup.md`](docs/b1_setup.md) fixes the object instead. The field is the
**two-index** effective cost `P(a, j)`, the terms on which agent class `a` can
obtain `j`, and a single price vector is the special case where terms do not
depend on who is transacting, which is an assumption about an economy rather than
a description of one.

**The first two measurements divide the work, and the division is the design.**
Loop A holds the date fixed: same quarter, same census tract, same lien, same
purpose, same occupancy, and applicants receive different rates while a cash buyer
carries no financing term at all. Position identical, date identical, market
identical, terms different by who is transacting, and there is no finer position
space to retreat to because the position was already held fixed. **It is done and
it passed**, 7/7 with the placebo at 4/4, on 28,137,985 loans across three
programmes. Loop B holds the dwelling fixed and varies the entry date. **It is
done and it passed**, 4/4 over 53 quarters, with a vintage bound of 0.8479 in
2026 Q1 against loop A's 0.3363, above loop A in 46 of the 53. Its registered
prediction most likely to fail was that the wedge predates the 2022 repricing, and
the mean over the 36 quarters before 2022 is 0.4043, so the repricing raised it by
64% rather than creating it.

**The larger number is the weaker evidence**, and
[`docs/b1_theorem.md`](docs/b1_theorem.md) is why: loop A's figure is a holonomy
and loop B's is a component separation, because a below-market mortgage cannot be
transferred and so no cycle closes. Loop B alone would not have carried it, and
the design says so. A critic can answer it by saying the two owners hold different
assets, a dwelling plus a 3% contract against a dwelling plus a 7% one, which is
correct as stated: entry date is a coordinate rather than an attribute of the
holder. Loop B survives through the hole, since the 3% contract cannot be
purchased and integrability on a space you cannot move around in is vacuous. That
argument is second-order, so the paper leads with A.

**The theorem changed what those numbers are.** The question it settled was
whether stage B2 had exercised the framework's machinery at all: loop A's
decomposition runs over a partition rather than a graph, so until Theorem 3 the
honest description was an analysis of variance believed to be related to a
topological claim, and that is worth little, because conditional dispersion in
mortgage pricing is already documented and a framework that re-derives it has
contributed a vocabulary. Theorem 3 shows the within share **is** the `L²` norm of
the square component, halved, and on this carrier the square component is the
whole non-exact part because the harmonic one is identically zero
([`docs/b1_theorem.md`](docs/b1_theorem.md) §12). Same number, different object,
and only the second is something the framework can be judged on. Theorem 2 then
fixes what any one carrier can reach: mortgage data reaches squares only, and no
sample size changes that, so the other summand needs a different carrier
altogether.

**Two corrections are recorded rather than quietly fixed.** The loan-level public
file carries rate spread but redacts credit score, so it establishes that
dispersion exists at fixed position and date without attributing it, and
attribution is a separate and weaker claim made with credit-score-banded
aggregates and labelled as such. And **asset tier is not agent class**: a landlord
buying down-market units to rent and hold is a high-class agent holding a low-tier
asset, and pooling by price tier averages that landlord together with the
household that could reach no higher tier. Occupancy type separates them, and
every cell in the panel is crossed by it.

**Track C, the same claim where no market exists.** A price field that does not
compose can be argued back to friction: thin books, stale quotes, transaction
costs. The argument is weak and it is available, and closing it costs work. **Track
C moves the question to carriers friction does not reach.** Wherever an
institution declares that one unit of `a` counts as `R(a,b)` units of `b`, it
asserts a scalar `v` with `R(a,b) = v(a)/v(b)`, and that assertion has an exact
consequence: around any closed loop of declarations the product is 1. Nothing is
traded to produce these numbers, so friction is not among the things that could
explain a product away from 1. Full account in
[`docs/c_track.md`](docs/c_track.md).

**One station is not part of any of the three tracks, and is marked so it is not
read as one.** E1 counts first-degree places allocated to each province against
the number of candidates there, from a public compilation of enrolment plans.
**The framework says nothing about how a quota should be allocated or to whom**,
and E1 draws no conclusion from its own numbers. It sits in this repository
because it shares C3's carrier, its parser and its measurement discipline, and
because **half of it is a list of nine ways that source misleads a reader who does
not check**. Every one of them produced a number that looked like a finding, and
none of them was caught by a criterion. Anyone using that compilation by any
method will meet the same nine.

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
record keeps both, including the withdrawals and the criteria that were void on
their own registered estimator. Citing a passing criterion without its
attached scope limits is a misreading of the record rather than a shortening of
it; each stage's limits sit in its own document under `docs/`.

**Criteria are of six kinds, and counts are given per kind.** `instrument` asks
whether the run's own machinery is sound, `premise` whether the external fact a
station rests on holds at all, `known_answer` whether a parser reproduces counts
that are already known from another source, `rival` whether the scalar-potential
prediction of an exact zero holds in a cell, `own_reading` whether the station's
own registered reading holds, and `bookkeeping` whether the record names
everything it is required to name. Each means something different when it does
not pass: the instrument ones point at code and say where; the premise ones say
the criteria resting on them have no object to judge; the known-answer ones
return a named and checkable list of anomalies, which is often the most useful
thing a station returns; a station's own reading that does not pass withdraws
that one reading. The rival line is the one that bears on the theory. A count
that pools the six refers to nothing, which is why the totals in this file are
given by kind and by stage.

## License

Code is MIT: `src/`, `experiments/`, `scripts/`, `tests/`, and the retrieval
scripts at `data/*.py`. See [LICENSE](LICENSE).

Documentation and results are CC BY 4.0: `docs/`, `results/`, `figures/`,
`speedrun/`, `RESULTS.md`, `README.md`, and under `data/` the provenance and the
pinned choices: `data/SOURCES.md`, `data/*.json`, `data/*.csv`, and the
per-file manifests. See [LICENSE-CC-BY-4.0.md](LICENSE-CC-BY-4.0.md), which
names the covered paths and the attribution form.

**No retrieved source data is redistributed.** `data/raw/` and the per-stage
`raw/` directories are not in git, and each source keeps its own terms, recorded
in [`data/SOURCES.md`](data/SOURCES.md). What is committed under `data/` is this
project's own: the scripts that fetch, the manifests that record what each fetch
returned, the choices pinned by hand with the measurements that settled them,
and two tables collected and arranged here.
