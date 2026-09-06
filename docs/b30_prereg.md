# B30 preregistration: what a price copies from, and what can contradict it

**Registered 2026-08-30. No arm has been run.** Design file for
[`b30_propagation.md`](b30_propagation.md), which carries the construction and the
vet. Sibling of [`b29_locality_theorem.md`](b29_locality_theorem.md), which handles
what arbitrage can remove once a field exists.

---

## 0. What this station is for, and a full timing disclosure

B29 asks what local arbitrage removes from a field. **This asks how a number gets
onto an edge that has never traded, and what could ever contradict it.**

**The construction half is arithmetic** and carries no weight: transport on a graph
with cycles is a connection, a spanning tree carries no holonomy, a tree plus `b1`
extra edges carries `b1` independent disagreements, and a graph of relations fixes
a level only up to one constant per component. **The claim half is that real price
fields are generated this way**, and nothing yet establishes it.

### Timing, in four layers, because the layers carry different weight

**Rule 8a requires the hypothesis timing and the criterion timing to be stated
separately, and requires disclosure only where a reading chose what gets scored.**

1. **The anchoring hypothesis predates every reading in this repository.** It was
   written into the framework from the phenomenon alone, before B25 through B28
   were designed and before any of their data existed. **That is the layer that
   carries out-of-sample weight, and it is unaffected by anything below.**
2. **The B30 construction was written on 2026-08-30 from the question alone**, with
   no carrier chosen and no data pulled. The two-graph split, the propagation
   front, and the anchor-as-boundary-condition reading all date from that writing.
3. **B30-8's event was found on the same day by a targeted search**, that is, by
   looking for it because the construction predicted it. **So the platform episode
   is confirmatory and is not out-of-sample for the finding.** Only its in-store
   leg is unseen, and this file fixes that arm's criterion before that leg is
   collected, which is the only reason the arm is worth running.
4. **The substitution-class variable in `b30_propagation.md` §12.9 was chosen after
   seeing a counterexample** that broke the earlier density reading. **B30-7 and
   B30-9 are therefore built on a variable selected post hoc, and they carry
   nothing except through cells that have not been looked at.** This is stated
   plainly rather than left for a reader to work out.

---

## 1. The object, and the trap that must be avoided first

The object is a **substitution class**: a set of sellers whose offers a buyer
treats as quotes for one thing. Two such offers are parallel edges between the
same pair of positions, and parallel edges form a 2-cycle, the shortest cycle
there is.

**The trap is circular definition.** If a substitution class is identified by
whether its prices collapsed, then "prices collapse within a class" is a tautology
and this station says nothing. **The class must be fixed by something independent
of price.**

**Rule for this station: the substitution class must be asserted by a party who is
neither the analyst nor the seller, and the assertion must be datable and
published.** Acceptable assertions, in the project's trust order:

| tier | assertion |
|---|---|
| strongest | a platform's own category assignment, or its placement of two offers in one list under one coupon |
| strong | a regulator's or trade body's product classification |
| usable | a directory's category (a review platform's own taxonomy) |
| **not acceptable** | the analyst's judgement that two things are alike, and any grouping induced by observed prices |

**A seller's own claim that it has no substitutes is evidence about the seller, not
about the class**, and is recorded as such rather than used.

---

## 2. Criteria

Written before carriers are chosen. **The criterion shape is not a degree of
freedom** (research rule 5, 2a), so these branch conditions stand as written even
where a carrier turns out to be awkward.

**B30-0  the control that must be reachable.** One substitution class, asserted by
a third party, with many independent sellers in one city and no imported
reference: a staple sold under one identical SKU across many shops.

- dispersion within the class is small relative to the gap between classes → the
  instrument separates structure from noise and the station may proceed
- dispersion within the class is comparable to the gap between classes → **the
  station is void**, because what looks like class structure is measurement noise

**B30-1  decay against hops.** *(Corrected 2026-08-30, see
`b30_propagation.md` §12.5. The original form fired on broadcast and is retained
there with this pointer.)* Amplitude of a price move at the reference against hop
count **in the quotation graph**, with a control for direct access to the source.
Read on nodes with **no direct access and a long relay path**.

- amplitude flat in hops on no-direct-access nodes → what moved was a convention
- amplitude falling roughly geometrically → what moved was information, and the
  file's central reading fails
- flat only among nodes with direct access → nothing measured, arm void

**B30-2  routes against dispersion.** Dispersion of a relative price between two
regions against the number of edge-disjoint trade routes joining them.

- dispersion falls with route count, largest at one route → checkability binds
- no relation → route count is not the mechanism

**B30-3  destination ladder against freight.** For one exported good in two
destinations, the multiple over its home price.

- tracks the destination's own price ladder → the destination anchor wins
- tracks freight and duty → cost explains it and anchoring is not needed

**B30-4  comparables against dispersion.** Dispersion of a good's export price
against the density of asserted comparables at the destination.

- dispersion rises as comparables thin out → no anchor to attach to
- flat → anchoring is not what sets the entry price

**B30-5  the front.** Regional deviation regressed on the propagation branch and on
the region's own conditions.

- loads on the branch → the field is a tree and the deviation is inherited
- loads on local conditions → the field is an equilibrium and this file is wrong

### B30-5 cross-sectional, registered 2026-09-01. What it answers, and what it does not

**Why this exists.** B30-5 has been blocked since 2026-08-30 on a requirement it
does not carry. The carrier note for B30-1 and B30-5 states that both arms need
published adjacency **and dated propagation**, and dated propagation is what the
public ATPCO record cannot supply. **B30-1 needs it: its statistic is amplitude
against hop count.** B30-5's registered text above asks for regional deviation
regressed on the propagation branch and on the region's own conditions, and
**names no clock**. So the cross-section can run.

**The limit, stated first rather than discovered later.** A cross-section
separates the two branches the criterion names. It does **not** separate
*inherited down a tree* from *a common cause reaching both regions
independently*. Two cities carrying one number may be inheriting it from one
brand, or may both be facing one national cost. **Only the timing separates
those, and the timing is exactly the half that is not obtainable.** So this run
answers the registered dichotomy and leaves that second question open, and any
reading of it has to say so.

**The statistic.** For item `i` over cities `c`, with `Y(c)` the city's average
monthly net salary taken from the same table as the prices:

```
log P(i,c) = a_i + b_i * log Y(c) + e(i,c)
```

**The class of each item is already fixed** by the rule in `b30_propagation.md`
section 12.9, assigned from each item's description and never from its numbers,
and applied before any table was fetched.

| class | what the class means | registered reading of `b_i` |
|---|---|---|
| **LADDER** | one brand posts a single number nationally | **near 0.** The branch pins it and local income is ignored |
| **LOCAL** | no national number, produced where sold | **near 1.** It tracks local conditions |
| FRESH | locally produced food, no national number | between, reported and not predicted |
| STATE | a government sets the number | reported apart, per B30-9 |

**The kill branch is B30-5's own, unchanged**: if LADDER items also come back
near 1, regional deviation loads on local conditions and this file is wrong.

**The reading is the separation between two distributions, not a line on `b`.**
Print every item's `b_i` beside its name so any row can be re-argued, print the
two class distributions, and read whether they overlap. Where they separate with
an empty gap, say so and give the gap; where they overlap, say that instead. **No
threshold is registered on `b`, because a threshold on an estimator is the shape
this project has repeatedly found worthless.**

**Gate six, and it is arithmetic done before any fetch.** To tell `b = 0` from
`b = 1` the standard error has to be well under a half:

```
se(b)  ~=  sigma / ( sqrt(N) * sd(log Y) )
```

With crowdsourced item noise `sigma` around 0.20 in logs and a Chinese city
sample spanning roughly `sd(log Y) = 0.3`, `se ~= 0.67 / sqrt(N)`. So **N = 12
gives 0.19 and N = 20 gives 0.15**, and anything under about ten cities cannot
separate the two branches at all. **The registered minimum is twelve cities**,
and the measured `sigma` replaces the assumed one as soon as the first table is
in, with the gate re-read on the measured value.

**Gates two and three do not apply**: the criterion compares two distributions
of `b` and declares no band on an estimator. Gate zero: the treatment variable
is whether an item has a national ladder, two values, and the observation unit
is item by city rather than country.

**City selection, fixed here so it is not a free parameter, and revised once on
2026-09-01 before any city beyond the original pair was fetched.**

**The first version said: take every city the source covers, and if that has to
be trimmed, trim by a stated mechanical reason. The obvious mechanical reason
was the source's own data-sufficiency gate, the set of cities it admits to its
published index. That was checked and it is not admissible here.**

**The source lists 147 Chinese cities but admits only eleven to its index, and
those eleven are Shanghai, Beijing, Shenzhen, Guangzhou, Suzhou, Hangzhou,
Changsha, Nanjing, Wuhan, Chengdu and Chongqing.** Harbin, which supplies the
low end of the pair already read, is not among them, and its page nonetheless
carries all fifty-three items.

> **The source's gate counts contributors, and contributors concentrate in
> high-income cities. So using that gate is a selection on income**, which this
> criterion forbids, **and it would collapse the income spread that gate six
> needs.**

**What runs instead: the four municipalities and every provincial capital.**
That is an administrative status, fixed by the state and not by income, data
volume or anything this arm measures, and it spans the income range by
construction, from Lhasa, Urumqi, Lanzhou and Guiyang to Beijing, Shanghai,
Hangzhou and Guangzhou. Roughly thirty-one cities.

**Nothing is dropped on income or on thinness.** Each city's page reports its own
contributor count and entry count, and **those two numbers are recorded beside
every city and reported with the result** rather than used as a filter. A city
enters if its page carries the item table and the net salary figure; a city whose
page lacks either is named, with what it lacks.

**Retrieval, and it was validated against a known answer before any new city was
read.** The source is the crowdsourced cost-of-living database already used for
the Shanghai and Harbin pair, read one city page at a time. One page equals one
row of the panel and carries the salary figure, so no two retrievals have to be
reconciled.

**The known-answer check, 2026-09-01.** Harbin's page was read afresh and
compared against the fifty-three values transcribed by hand from the same source
on 2026-07-15 and held in `experiments/b30_7_city_pair.py`. **Fifty-one of the
fifty-three agree to the cent.** The two that differ are the monthly transport
pass, 73.88 against 73.69, and the three-bedroom central rent, 9063.62 against
9041.42, both about a quarter of one per cent. **That is the source recomputing
its own averages as entries age out, not a transcription fault**: a transcription
fault shows up as an order of magnitude or a shifted row, not as two parts in a
thousand.

**So the reading channel is validated**, and the criterion for every later city
is the same one: item labels must match the registered list, and any value more
than a factor of two from the same item's value in an already-read city is named
and checked by hand before it enters.

**Thin cities, settled 2026-09-01 on the first city read and before any other.**
The page states its own recency: Lhasa reports **zero entries in the past twelve
months by zero contributors, last updated 3 March 2025**, and its figures are
visibly odd — a net salary of 14,000 against Beijing's 11,245, and a Volkswagen
Golf at 200,000 where every other city carries 129,900.

**Lhasa enters.** The rule above admits a city if its page carries the table and
the salary, and nothing is dropped for thinness. **Dropping it would be choosing
data**: that Golf is a LADDER item that is *not* pinned, which is evidence
against this arm's own prediction, and an arm that discards its own
counter-evidence for being inconvenient has stopped being an arm.

**A recency filter is not available as a repair, and the reason is the one
already recorded above.** Recent entries come from contributors, contributors
concentrate in high-income cities, **so filtering on recency is filtering on
income by another route.**

**What is reported instead, and it is a print rather than a filter.** Every
city's entry count, contributor count and last-update date are recorded beside
it. The result is computed on **all** cities, which is the criterion, and the
same computation on the subset with at least one entry in the past twelve months
is printed beside it **with no verdict attached**. The pair shows how much the
thin cities move the answer. **The all-cities figure is the one that is read**,
and the subset may not be preferred to it, because the subset is the
income-filtered one.

**B30-6  restriction against gap.** Region locking, warranty non-portability,
authorised-channel restriction and refusal to ship, against the cross-market price
gap for the same maker.

- restriction density tracks the gap, and relaxes where the gap narrows → the
  restriction is edge deletion in the service of the gap
- tracks logistics or regulation instead → the reading fails

**B30-7  the two cells, and this is the arm with the cleanest kill.** Cross the two
variables that §12.9 says are separate.

| | dense local substitution class | sparse local substitution class |
|---|---|---|
| **tradable** | cell A | |
| **non-tradable** | | **cell B** |

- **cell A**: copying should fail and the local price should rule, despite the good
  moving freely
- **cell B**: copying should succeed, and the price should track the **reference
  city** rather than **local income**
- **cell B tracking local income instead → §12.9 is wrong**, and with it the
  substitution reading of the whole file

**Cell B is the worst cell and it is measured first** (research rule 13).

**B30-8  the created edge.** A third party who is neither buyer nor seller places
two previously separate classes into one list under one coupon.

| | |
|---|---|
| treatment | creation of a substitution edge by a third party |
| treated | the two brands' paid prices on that platform |
| control | the same brands' in-store prices on the same dates |
| outcome | the gap between the two brands' paid prices |

- gap collapses on the platform **and persists in store** → the edge held the
  price and nothing about the object changed
- gap collapses in both → something other than the edge moved, **arm not
  identified and reported as such**
- gap persists on the platform → substitutability is not the mechanism

**B30-10  the limiting cell: a named individual with an abundant free substitute.**
Construction in [`b30_propagation.md`](b30_propagation.md) §14. Over the class of
**named-individual subscriptions**, all four of: marginal cost zero, an unlimited
free substitute of the same functional kind, no substitute for the object itself,
and a platform-posted price ladder.

- posted prices cluster on the platform's focal grid, are close to uncorrelated
  with output volume and audience size, and shift across platforms with the
  platforms' posted ladders → the ladder sets the level and neither cost nor
  scarcity is available to
- prices scale with output volume or audience → an ordinary quantity story works
  and this cell is not what §14 says it is
- **the parasocial gradient sub-test**: willingness to pay against the bandwidth
  and synchrony of contact. Rising with synchrony supports attachment; falling with
  synchrony supports the anchor-availability reading. **Both directions are
  available and the arm is specified so that either is a result.**

**Class construction, not carrier selection.** The four properties are checked
before any price is read, the arm is run over every member the class admits in
publishing, streaming, music and elsewhere, and **the reading must survive dropping
any single member.** No member is named as the headline and none is load bearing.

*B30-10 was read on 2026-08-30 and is reported in
[`b30_results.md`](b30_results.md). It is **partially read**: the level-setting
half returns its first branch, the clustering statistic is not in hand, and two
source classes remain untried. The criterion above was not edited after the
reading.*

**B30-9  the regulator as a third anchor.** Recorded as an **exclusion and a
prediction, not a test**. Where a regulator sets a price, the anchor is supplied by
the regulator and neither the local market nor the reference city is expected to
explain it. **Regulated monopolies are therefore excluded from cell B**, and if a
regulated tariff is found tracking a reference city rather than its own regulatory
formula, that is a finding for a different station.

---

## 3. Gate arithmetic

**Which invariant each arm reads, stated per arm, because B27 got this wrong once
before it was fixed.**

| arm | independent cycles | invariant read |
|---|---|---|
| B30-0 | many parallel edges within the class | dispersion inside a `b1 >= 1` class |
| B30-2 | `routes - 1` per region pair | `b1` directly |
| B30-7 cell A | parallel edges present | `H1` on a closed class |
| **B30-7 cell B** | **`b1 = 0` by construction: a sparse class has no parallel edges** | **`H0`. The question is which component supplies the anchor, not whether a loop closes** |
| B30-8 | `b1` moves from 0 to 1 at the treatment date | the creation of a cycle |

**Getting cell B's invariant right is the point of the arm.** It is not a failure
of a cycle to close. **There is no cycle.** It is a question about which component
a lone position draws its constant from, and the two candidate suppliers are local
income and the reference city.

**Resolution floor (D24).** Posted retail prices in the relevant range cluster on a
focal grid, so **a difference smaller than one focal step is not resolvable** and
is reported as zero. In the Chinese beverage and service range that step is a few
yuan, and the exact grid is measured from the carrier's own menu before any
comparison is made rather than assumed.

**Two prices (D30).** Every arm compares at least two posted numbers for one
object. **Private bilateral contract (D29).** All posted publicly; no arm rests on
a negotiated price. **Both outcomes reachable (rule 12).** A county specialty shop
charging 15 yuan and one charging 38 are both entirely ordinary things for such a
shop to do, and neither is forced by anything in the construction.

---

## 4. Reachability, and what is excluded

**Nothing here reads whether any price is correct, fair, or efficient**, and
nothing requires any participant to be irrational, uninformed or foolish. Every
agent in the construction arbitrages perfectly over everything they can reach and
copies faithfully along every edge they hold. **The obstruction is in reach, not in
judgement**, and any reading that slides into a claim about buyer competence is out
of scope and should be struck.

---

## 5. Population, and how carriers will be chosen

**Built rather than nominated** (the B27 lesson: fix a population objection by
constructing a population, not by arguing about one).

**Cell B population.** Services meeting all four conditions:

1. non-tradable: the service cannot be delivered across the city boundary;
2. sparse: below a stated count of independent providers per unit population in
   that locality, with the count taken from a directory rather than estimated;
3. **unregulated**: no authority sets or caps the price, per B30-9;
4. a reference city exists, meaning the same third-party directory carries the
   same category in a larger city.

**One candidate is named and it is the cheapest to run**: independent specialty
coffee in a county-level town, against the same directory's category in a
first-tier city, and against that town's own income. It satisfies all four
conditions, its prices are posted publicly on a third-party directory that also
supplies the category assertion required by §1, and it sits in the same product
family the vet already used.

**Cell A population.** One identical SKU sold by many independent sellers in one
city, category asserted by the same directory or by a platform.

**B30-10 population.** Every platform that posts a price floor, a ceiling, or a
default tier for subscriptions to an individual, across at least three unrelated
content domains so that no domain carries the arm alone. The platform's posted
ladder is the treatment variable and it is published by the platform itself, which
satisfies §1 without a judgement call.

**Naming order is disclosed.** The coffee family was in view before this file was
written, because it is the family the vet's counterexample came from. **The county
carrier itself has not been looked at**, and no price from it has been seen. That
is the difference between the family being familiar and the reading being
contaminated, and it is recorded here so a later reader does not have to guess.

---

## 5a. Data path, checked before the arms are run

**Rule D32: enumerate the source classes before declaring anything unobtainable.**

**For B30-8's in-store leg**, six classes to try in order: the brand's own posted
menu; the brand's financial disclosure and earnings call; the platform's own
release; a third-party directory's stored menu; trade press with figures; and
first-hand posts carrying dated screenshots. **The platform coupon leg is
ephemeral by nature** and the risk that it is unrecoverable retroactively is
recorded now, before the attempt, so that a failure is a recorded negative rather
than a quiet abandonment.

**For cell B**, the directory supplies both the price and the category, so a single
source covers two requirements. **That is a dependency and it is disclosed**: if
the directory's category assignment turns out to be derived from price bands, §1's
independence requirement fails and the carrier must be replaced.

---

## 6. Order of work

**Two arms run first, because each can sink a different half of the file.**

1. **B30-7 cell B.** A sparse-market unregulated non-tradable tracking local income
   rather than the reference city kills §12.9 and the substitution reading.
2. **B30-8's in-store control leg.** An in-store gap that collapsed on the same
   dates leaves the platform episode unidentified, and the file loses its only
   dated event.

**B30-0 runs alongside as the instrument check** and can void the station on its
own.

**The rest wait.** B30-1 and B30-5 need graphs that have not been built, B30-2
needs a route census, and B30-3, B30-4 and B30-6 are ordinary and can follow.

> **UPDATED 2026-09-03. Every clause above has moved. The original stays as
> written; the readings are in [`b30_results.md`](b30_results.md).**
>
> - **B30-1**: the quotation graph was built. **The arm cannot run on it** because
>   the maximum hop distance is one, and that negative is recorded. On ATPCO the
>   registered criterion failed as written, and that negative is recorded too.
>   **What the record supplied instead is a court-ordered, dated, staggered
>   deletion of edges lying in `G_I` alone**, with `G_T` untouched, and it is
>   carried into B30-16.
> - **B30-5**: **ran as a cross-section 2026-09-01**, two criteria PASS. Its
>   registered text names no clock, which is why it could run where B30-1 could
>   not.
> - **B30-2**: census still unbuilt, **and the carrier condition is now settled**:
>   on a dense network the Menger count degenerates into degree and the arm would
>   read economic size, so the census needs a sparse network whose edges are
>   physical.
> - **B30-3**: **run 2026-09-03, returns its first branch.** Freight ruled out by
>   an origin control the carrier already contained; duty pulled from TRAINS,
>   corrected in duty's own favour, swept across the uncertain rate, and entered
>   with squares and an interaction. It enters and does not carry the co-movement.
> - **B30-4**: **carrier settled on paper**, one candidate closed without
>   collecting anything, availability gate registered and unrun.
> - **B30-6**: run, three chunks, **first branch fails on a six-product panel.**

---

## 7. Scope

**One thing this station does not claim.** That anchoring is the only thing setting
any price. Cost convergence along a supply chain is real, regulation is real, and
local competition is real. **The claim is that these do not exhaust it, and every
arm above is a place where they and the construction predict different numbers.**

**And one thing it must not become.** A finding that some price is "wrong". Every
price in every cell here is a number a seller posted and a buyer paid. The station
reads whether a global scalar exists behind them, which is a different question,
and a negative answer is not a complaint about anyone's conduct.

---

## B30-23  a dated transfer of control, and whether the procedure travels with it

**Registered 2026-09-03.** The propagation claim of this chain is that one party's
procedure reached another. **B30-1 asks it through decay against hop count and
needs a published adjacency with dated propagation.** This arm asks the same claim
through a different channel and needs neither: **an ownership or control event
hands the authority to set B's tariff to A, on a public date, while B's customers,
assets, market, regulator and costs continue unchanged.** Imposition rather than
imitation, and imposition is the easier of the two to observe because it arrives
with a direction and a date already attached.

**Why this channel and not another comparison.** A co-movement reading is
symmetric and cannot say which party moved first. This one names A, names B and
names the day. And the confound this channel does carry, that the acquisition
changes B's cost of funds and scale, **moves every value in B's tariff and does
not change how many distinct values it has**, so the criterion below is immune to
exactly the disturbance the carrier introduces.

### 1  Criterion

**B30-23** Count the distinct class values in B's filed tariff in the last filing
before the transfer and the first filing after it, and the same for A's own
filing on both dates. Three outcomes, all reachable:

- B's count moves to A's → **the procedure travelled with the control**
- B's count stays at its own → **it did not; the tariff survived the change of
  owner**
- neither, a third count appears → **a new procedure was written at the transfer**.
  Report the three counts; this is not scored as either of the first two

**Counted on the document, not estimated.** The unit is a distinct class value
written in the filed rating plan, which is a property of the filing and not of the
market. Ties are counted once: two cells carrying the same value are one value.

### 2  Gate arithmetic

- **The zero-multiple gate and the power floor do not apply**, and this is not a
  failure to clear them. There is no estimator and no band. The reading is an
  integer read off a document, so there is no line drawn on an estimate whose
  readability could be in question.
- **The resolution floor is zero** for the same reason: a count off a filed
  document has no measurement error to clear.
- **Treatment values**: the treatment is the transfer, one per case. The count of
  cases available is the binding number and it is what the availability pass has
  to return first.

### 3  Reachability

**One pre-check decides whether a case can be used at all: A and B must have
different counts before the transfer.** Where they already agree the test is
degenerate and returns the same answer under every hypothesis, so such cases are
excluded on paper before anything is pulled. **That check is free and it runs on
the two filings.**

**Two more pre-checks, both added 2026-09-03 after a score was written on this
carrier and withdrawn. Both are free and both run before any parsing.**

### 3a  One program has to have absorbed the other, and which way is not the question

**Simplified 2026-09-03, and the simplification removes a condition rather than
adding one.**

**Direction is not part of the claim.** The claim is that a procedure propagated
from one party to another. **Which party's procedure survived is settled by
shareholder politics, by negotiation and by who holds sovereignty in the merged
entity**, and none of that is this project's object. The canonical case runs
against ownership: an acquirer buys a target and the target's management and its
cost-first procedure end up running the acquirer. **That is a fact about the
merger, not about whether procedures travel.** **The named case is Boeing and McDonnell Douglas, 1997**: the buyer acquired the target and the target's executives and its cost-first procedure ended up running the buyer. **Which procedure survives a merger is a question of politics, of the negotiation and of sovereignty afterwards, and it sits outside anything a count can reach.**

**So the arm does not ask who imposed on whom.** It asks whether two procedures
became one, on a date, with the underlying business unchanged.

**That collapses three indicators into one observable.** The earlier form of this
check listed a filing organisation changing, an entity being renamed, and a filing
attempting a migration. **The first two are compatible with nothing happening at
all** — a carrier was closed on exactly that, where the acquirer renamed four
entities and stated in writing that nothing else changed — **and the third was
misread on that same carrier**, because a rename filing carries a name that reads
like a migration.

> **The single observable: does one of the two programs stop being filed?**

**And a rule that runs before even that one, added 2026-09-03 after two negatives
on this channel.**

**A filed rating plan is observable because it is lodged with a regulator, per
entity, and that is exactly why it survives a change of owner.** Moving a book to
another entity's plan costs notice, rewrites and fresh approval; keeping the plan
and changing the name on it costs almost nothing.

> **Observability and mobility trade against each other. The most visible
> procedures are the least likely to travel.**

**So choose channels where keeping the incumbent procedure is not an option**: the
entity is gone and the procedure has no host; a published condition instructs that
it be changed and keeping it forfeits the funding; or the destination's law does
not permit it. **An ordinary acquisition is the weakest of the four, because there
the incumbent can stay and staying is the cheapest thing available.**

**The same rule points at a different kind of procedure: published, and not bolted
to an entity.** Platform terms are that, and one such was replaced wholesale on a
date.

**A program that is still being revised is still in force.** A program whose
filings cease has been replaced, and the book it priced is now priced by
something else. **This reads off a result list**, with no memoranda, no downloads
and no counts, and it runs before a case is chosen.

**It also enlarges the pool.** Restricting to cases where the acquirer imposes on
the target discards every case that runs the other way, and those are not rare.

### 3a-old  The authority over the tariff has to have actually moved

**An acquisition delivers this operator only if the power to set the acquired
party's tariff changed hands.** A purchase that leaves the charter, the management
and the pricing function where they were is not this treatment, and neither is a
purchase between parties already running a coordinated procedure. **In both, a
null result is what the design predicts and it carries nothing.**

Section 3's count test does not cover this. It catches identical plans and not
coordinated ones, and it says nothing about control. **Three indicators, all read
off the filings rather than off the corporate press:**

| indicator | what it shows |
|---|---|
| the filing organisation changes for the same entity | the acquirer now submits on the acquired entity's behalf |
| the entity is renamed | legal control asserted |
| **a filing exists that attempts to move the book onto the acquirer's own manuals** | **control exercised over the pricing function in particular** |

**The third is the load-bearing one**, and the first two can hold without it.

### 3b  The post-transfer filing has to replace the program, not revise it

**This is the one that was bought.** A filing under the acquirer's prefix, on the
acquired entity, after the closing, accepted, on the right line and in the right
state, **can still be an ordinary rate revision to the acquired party's own
program.** Two consecutive revisions of one program have the same partition by
construction, so such a pair returns "the partition did not move" under every
hypothesis. **It looks like a clean negative and it is empty.**

**The check costs one sentence.** These filings carry a short introduction that
states which program the filing revises **and cites that program's own original
approval number**. **If the cited program is the acquired party's own, the filing
is a revision and the pair is not a before and after.** Read that sentence in both
filings before parsing either.

> **A filing prefix says who submitted a document. It does not say whose procedure
> is inside it.**

### 4  Carrier and definitions

**The two conditions are that the procedure is a retrievable public document and
that the event holds the target's world fixed.** Their intersection:

| candidate channel | holds the world fixed | procedure retrievable |
|---|---|---|
| **cross-border acquisition** | **strongest**: the target keeps its country, customers, regulator and competitors, and what arrives is a foreign parent's procedure, observably unlike the local one | depends on the industry |
| **purchase of a bankrupt firm's equity** | **very strong**: assets, workers and customers continue through the sale or the plan; the owner and the procedures are what change, and the court docket dates every step | depends |
| ordinary merger | strong, but scale and cost of funds do move | best where tariffs are filed |
| conditional recapitalisation | strongest on leaving ownership alone, but the conditions usually govern capital and not pricing. **The exception is programme conditionality**, where the condition is itself an instruction to change a procedure and is published in a dated letter | published, when it exists |

**The named carrier**: **United States insurance, where the filed rating plan is a
per-company public document**, on an acquisition that is cross-border or driven by
insolvency. Both parties' plans are retrievable before and after, and the state
filing systems are open.

**Nothing has been pulled and no case has been named.** The first step is the
availability pass: how many acquisitions satisfy the pre-check of section 3.


### 3c  The channel changes, and the screen becomes a census

**Added 2026-09-03 after two negatives on ordinary acquisition and the structural
reason for them.** The selection rule in the results file ranks four channels by
whether the incumbent procedure can survive at all, and puts ordinary acquisition
last. **This section takes the channel the rule ranks first, in an industry where it
applies.**

**The carrier: the fee schedule of a US securities exchange.** It is published, it is
tiered, every amendment to it is filed under Rule 19b-4 and printed in the Federal
Register with a date, **and when an exchange stops operating its fee schedule stops
being filed and its members are priced by another exchange's.** That is the first
channel: the entity is gone and the procedure has no host. The results file asked for
an industry where the operating entity itself is sold and continues, and this is one.

**Why the fee schedule and not the rate filing that failed twice.** A filed rating
plan is bolted to an insurance entity, which is why it survives a change of owner. An
exchange fee schedule is bolted to an exchange licence, **and licences are
surrendered, merged and retired on public dates**.

**① Criterion.** The criterion of section 1 is unchanged: count the distinct class
values in the fee schedule before and after, three outcomes, all reachable. **This
section registers the screen that runs before it**, and the screen is the census the
results file asked for rather than a hunt for one case:

> **For every exchange appearing in the index, the first and last date on which a fee
> filing of its own was published.** An exchange still filing is still in force. One
> whose filings stop has been replaced.

**Printed, not scored.** The output is a table of exchanges with two dates and a
count each. No threshold is placed on any of them.

**② Gate arithmetic.** No estimator and no band, so the zero-multiple gate and the
power floor do not apply, as in section 2. **The resolution floor is zero**: a
publication date is exact. **The binding number is the count of exchanges, and it is
not guessed** — it is what the census returns, which is why the census runs before a
case is named rather than after.

**③ Reachability, three branches and all three are live.**

- **some exchange's fee filings stop on a date** → a pair exists, and section 3b's
  read of what the successor filing says it is decides whether it is a replacement
- **none stop** → **`0/N` is the reading**, not a failure to find a carrier: it says
  procedures persist with the licence in this industry too, and it is the second
  industry saying so
- **filings stop but the successor filing says it is a rename** → the third outcome,
  reported as itself, which is exactly the trap that cost the previous carrier

**④ Carrier and definition.** The Federal Register index of notices issued by the
Securities and Exchange Commission, title and date only. The self-regulatory notices
carry a title of a regular shape naming the exchange and, where the filing touches
fees, saying so, **so the exchange and the subject are readable off the index without
retrieving a document**. Collected by `data/fetch_sro_filings.py`, one file per month
under `data/raw/fr_sec/`, resumable, with a stored count that has to match the row
count before a month is read rather than refetched.

**Titles vary across "Fee Schedule", "Fees Schedule", "Price List" and "Transaction
Fees", so the index is taken whole and every screen runs on disk.** Filtering
server-side on one spelling loses the others silently.


### 1a  The criterion compares which values, not how many (registered and refuted the same day; see the results file, chunk twenty)

**Corrected 2026-09-05 after the control was measured.** Section 1 registered a
comparison of counts. **Seven whole schedules on disk show that count is not stable
enough to carry it**: one exchange, one owner, no transfer, 2018 against 2026, goes
from 10 cells and 7 distinct values to 25 and 19. **A programme's own drift over a few
years exceeds anything a transfer needs to produce.**

**A procedure that travelled leaves its own values in the other party's schedule.**
That is a statement about which values:

> Take the set of distinct per-share values in B's schedule before the transfer, in
> B's schedule after it, and in A's own schedule. **Report the overlap of B-after
> with A, against the overlap of B-after with B-before.**

**The three outcomes of section 1 map on unchanged**: B's set moves to A's, B keeps
its own, or a third set appears. **Set overlap is immune to the drift that kills the
count**, because a schedule can add tiers for years and still carry its own historical
values, and it is the values themselves a transferred procedure replaces.

**Scope**: per-share rates, identified by dimension — three to six decimals of a
dollar. Section headings differ between exchanges and between two vintages of the same
exchange, so a heading-based scope is not comparable across schedules.

**This is a criterion shape correction and it costs nothing.** The count reading it
replaces is printed in the results file rather than removed, and the retrieval it
needs is the same three schedules as before.
