# B1 setup: what field is the theorem about?

**Status: setup only.** No theorem is proved here and no data is analysed. This
document fixes the object, because the proof is worthless if the object is empty.

The field is defined over a holding period `T` and includes revaluation. Setting
`T = 1` with no revaluation recovers the per-period cost formulation exactly, so
the static case is a special case rather than a separate construction, and any
result established at `T = 1` stands without relying on the revaluation term. That
nesting is deliberate: the revaluation term is the part most open to empirical
dispute, and the argument should not rest on it alone.

Empirical figures cited in section 3 are from 2026 rent-versus-own comparisons
across the 50 largest US metros and are used only to correct an assertion that
would otherwise have been made carelessly. They are not a result. Anything used in
B2 gets pulled from primary sources with series identifiers, as in
`data/SOURCES.md`.

---

## 1. The problem this document exists to solve

Volume II of the source framework argues that the price field on an economy is
non-integrable: no global potential exists whose gradient it is, so local price
signals cannot be aggregated into a global allocation instruction.

There is an objection that kills this outright if it is not answered first.

Suppose every good has a price in one currency, so good `i` costs `p_i` dollars.
Then the rate at which `i` exchanges for `j` is

```
R_ij = p_j / p_i
```

and in logs, `log R_ij = log p_j − log p_i`. That is **exactly a gradient**: it is
the difference of a scalar defined on nodes. Any closed loop returns

```
log R_12 + log R_23 + log R_31 = 0
```

identically. So there is no curl, no arbitrage, and a global potential exists,
namely the price vector itself.

This is not an empirical result about market efficiency. It is a consequence of
having written prices as a one-index object. **On a single-currency price vector,
integrability is a theorem of notation.**

## The common-environment reading, and its ceiling

**The first thing anyone says on being shown a non-zero loop is that the parties
share an environment.** They buy the same fuel, they face the same cycle, they
sit under the same regulator. The claim of this section is that the reading
already answers that, by construction, and that no amount of credit given to the
environment moves the answer.

**Give it every advantage.** Let there be any number of environmental variables
`c_1(t) ... c_m(t)`, `m` as large as you like, named or not. Let every position
`i` load on each of them by its own coefficient, so the loading is as
heterogeneous as you please. Position `i` then carries

```
f(i) + sum_k beta_k(i) * c_k(t)
```

Sum the edge differences around a closed loop taken at one time:

```
sum_edges [ f(j) - f(i) ]  +  sum_edges sum_k [ beta_k(j) - beta_k(i) ] * c_k(t)
```

**Both sums telescope to zero.** At fixed `t`, `beta_k(i) * c_k(t)` is a function
of position alone, so it is a potential, and a potential has no curl. The number
of environmental variables does not matter. The heterogeneity of the loading does
not matter. **The contribution to the loop is not small. It is zero.**

**So what would an environment have to be to produce a non-zero loop?** It would
have to be a quantity carried on **ordered pairs** of positions that is **not**
a difference of node values. A quantity on ordered pairs that is not a node
difference is precisely the object this framework claims exists. **Pushed to its
maximum the environmental reading either accounts for none of the loop, or it
stops being an environment and becomes the claim. There is no interior.**

### The reading has one dial and no setting escapes

**Turn the scope of "environment" down** until it means a property of positions,
which is what fuel, the cycle and a regulatory regime are. **Then it predicts a
zero loop and it is falsified**, on seven carriers, the largest at 4.18e+06 times
the measured floor.

**Turn it up** until it means whatever shapes what all the parties can do. **Then
one of two things has happened.** Either it names no object, no count and no
forbidden outcome, in which case it is not a hypothesis and adds exactly what
attributing an unexplained result to heterogeneity adds. **Or it does name the
structure everyone is embedded in, and then it is the topology**, and it stops
contradicting anything here, because the claim of this project is a measurement
of how much signal stands on top of that structure.

**The middle setting does not escape either, it relocates.** Set it to a
property of ordered pairs, freight and duty and spread and borrow fee, and it is
both falsifiable and unfalsified. **But it has conceded that the loop is
non-zero**, so it is no longer a rival to the existence claim; it is a dispute
about what the non-zero is made of, and that dispute is downstream.

### Three things get called the same name, and only one of them is a rival

| | what it is | ceiling on the loop |
|---|---|---|
| **a** | environment as a property of **positions**: fuel, the cycle, a regime, any number of them | **exactly zero** |
| **b** | environment as a property of **ordered pairs**: freight, duty, spread, transaction cost, borrow fee | can be non-zero. **It does not deny that the loop is non-zero**, it disputes where the non-zero comes from |
| **c** | environment as an account of **co-movement and low-dimensional structure** | **all of it** |

**(a) is the rival and it is dead on arrival.** It is the same object as the
scalar potential above, arrived at from the other side.

**(b) is not a rival at all.** It concedes the existence claim and argues about
the source, which is a second-order dispute and is graded as such.

**(c) is not a hypothesis.** A common structure that every party is embedded in
and that shapes what each of them can do **is the topology**. Naming it without
naming an object, a count or a forbidden outcome adds nothing that can fail, in
the way that attributing an unexplained result to heterogeneity adds nothing.
**It is also already netted out**: every anchored reading in this project takes
its floor from a construction that keeps the common structure and destroys only
the thing being claimed, so what is reported is what stands above the
environment. **A quantity that is already subtracted cannot also be the
explanation.**

### Where this argument applies, audited 2026-09-03

**The requirement is weaker than a loop taken at one instant, and stating it
correctly matters, because the weaker version is the one the carriers have to
meet.** Write the term at position `i` and time `t` as `f(i) + beta_i * c(t)`
and take edge `k` at time `t_k`:

```
edge 1->2 at t1:  (f2 - f1) + (beta_2 - beta_1) * c(t1)
edge 2->3 at t2:  (f3 - f2) + (beta_3 - beta_2) * c(t2)
edge 3->1 at t3:  (f1 - f3) + (beta_1 - beta_3) * c(t3)
```

**With homogeneous loading the common term cancels inside each edge**, before any
telescoping across edges, because an edge subtracts two positions observed at the
same moment as each other. **The dates of different edges are then irrelevant and
a loop may be taken across years.** What is actually required is that **each
edge's two endpoints are simultaneous with one another**, which is a far weaker
condition than a simultaneous loop.

**With heterogeneous loading the remainder is
`(beta_2 - beta_1) c(t1) + (beta_3 - beta_2) c(t2) + (beta_1 - beta_3) c(t3)`,
which does not vanish** unless the `c` values agree or the `beta` values do. That
case, and only that case, is what forces one of the two routes below.

**Route one, the loop is taken at one time.** Then `c_k(t)` is a single number
across every edge and the remainder collapses regardless of the loading.

**Route two, the terms are constants of the object being traversed rather than
quantities marked to the world at each step.** Then the calendar is irrelevant:
a loop may span years and still admit nothing, because the environment never
enters the arithmetic that produces the terms. **An accounting identity on a
closed object is the clean case.** A balance that advances by
`b -> b(1+i) - P`, with `i` the instrument's own contractual rate and `P` its
own contractual payment, closes by arithmetic. Nothing leaves the object
unaccounted for, so no common drift can be hiding in the residual. **Route two
fails only where the contract is itself indexed to the environment**, which is a
named and checkable subset rather than a doubt.

| carrier | how the loop is formed | how it is covered |
|---|---|---|
| B2 | within one cell; the cell key carries the period | route one |
| B3 | the difference matrix inside a single (date, tenor) key | route one |
| B6 | `CUP -> USD -> EUR -> CUP` per date | route one |
| B9 | `log(price) - log(nav) - log1p(fee)` from one snapshot | route one |
| **squares** (B21, B24, B41, B42) | four cells on the same day, **and a double difference** | **route one twice over**, and immune even across dates: a common term cancels once inside each of the two differences |
| **B8** | one loan's own path, current to delinquent to modified to current, spanning months | **route two.** Its loop residual is built from the loan's **own note rate and own contract payment**, and the balance advances by `b -> b(1+i) - P`. **Every input is a constant of the contract and not one market quantity appears**; the code says as much beside it, the contract is a property of the period and not of the row. **The traversal takes months and admits nothing, because the balance has to reconcile: the object is closed and nothing leaves it unaccounted for** |
| B13 | one **state**, a book snapshot in which all four legs are quoted natively; 50,055 states, the split available in 49,116 | route one |

**The one place route two can fail on this carrier is an instrument whose own
rate is indexed**, where the environment is written into the contract. **That
subset was named and then counted, 2026-09-03.** The cache carries no product
field, so the label route is unavailable and the object is measured instead: a
note rate that moves at a row which is not a modification onset is the signature
of an indexed contract. Carrying the contract field across blanks first, so a
missing month does not read as a rate that changed and changed back:

| archive | rows | loans | rate changes | at or beside a modification | **away from any** | **loans carrying one** |
|---|---|---|---|---|---|---|
| 2002Q1 | 42,679,752 | 968,761 | 6,633 | 6,259 (0.9436) | **374** | **248, 2.6 per ten thousand** |
| **2007Q1** | 16,782,203 | 253,279 | 33,937 | 33,897 (**0.9988**) | **40** | **31, 1.2 per hundred thousand** |
| 2019Q1 | 11,774,637 | 341,865 | 2,718 | 2,713 (0.9982) | **5** | **4, 1.2 per million** |

**On the vintage with the most modifications, 99.88 per cent of every note-rate
change in sixteen million rows sits at a modification onset. The population is
fixed rate: a rate change here is a re-contracting.** The residue is at most two
and a half loans in ten thousand and falls by two orders of magnitude in the
newest archive, **and it is not shown to be indexed either**: a step-rate
modification whose onset flag was missed, a servicer correction and a payment
step-up all land in the same residue.

**Route two's named failure mode is therefore bounded rather than merely named.**
Three archives, agreeing, and no fourth was run.

### Time enters these algorithms for a second reason, and it is not this one

Several of the constructions do insist on a date, and **what they are protecting
is the identity of the object, not the cancellation above.** The square builder
drops a cell pair when the futures month differs across the two positions, so
that the two legs are the same contract rather than two contracts a month apart.
The loan reader carries a contract field across a gap because the contract is a
property of the period and not of the row, so that a blank month does not read
as a rate that changed and changed back.

**Those are object-identity requirements. Conflating them with the environment
argument would put a criterion's scope and the measured object's scope on
different footings**, which is the category error this project files sixth. **A
carrier can need a precise date for the first reason and need none at all for the
second.**

### B13 does not need this argument. It bounds it

**B13 is the carrier where the framework predicts exactly zero, and it returns
exactly zero 716 times out of 716** on one class, with the parity control in
place. A common environmental factor leaking into that index would show up as a
non-zero, because a leak has no reason to be identically zero. **716 exact zeros
is therefore a direct empirical bound on the leak on that carrier**, obtained
without assuming any of the algebra above.

**This is the useful direction of a predicted-zero reading and it is easy to
miss.** A carrier that returns non-zero needs the argument, to say the non-zero
is not the environment. **A carrier that returns zero where zero was predicted
supplies the argument instead of consuming it.**


If that is the field Volume II is about, Volume II is a claim about the empty set.
Anyone competent will ask this in the first five minutes.

---

## 2. The answer, and why it strengthens rather than rescues the framework

The field the framework is about was never the one-index object.

The relevant quantity is not "the price of `j`". It is **the terms on which agent
`a` can obtain `j`**, which depends on `a`. Write it

```
P(a, j) = the effective cost to a of obtaining j
```

and the exchange field between agents and goods is genuinely two-index. A single
price vector is the special case `P(a, j) = p_j` for all `a`, that is, the
assumption that terms of trade do not depend on who is transacting.

So the burden reverses. The one-index representation is not a description of an
economy, it is **an assumption about one**: that access is uniform. The
neoclassical no-arbitrage conclusion does not discover that the economy is
frictionless; it inherits it from the notation. To defend the one-index object a
critic has to assert that the terms on which you can obtain a thing do not depend
on who you are.

That assertion is false about rent, credit, insurance, bulk purchase, deposits,
minimum balances, and accreditation thresholds, which is to say about most of the
economy the framework is concerned with.

**This is not a repair.** Volume II already says the relevant object is access
rather than nominal price. What was missing was the explicit step showing that the
field is two-index and therefore that integrability is a question rather than a
tautology. This document supplies that step.

---

## 3. The field, stated precisely

Let `A` be a set of agent classes, `G` a set of positions an agent can hold, and
`Q` a set of quality tiers within a position.

Positions: cash, a rented dwelling, an owned dwelling, a financed vehicle, an
owned vehicle, a deposit, a credit balance. Tiers: the same position differs in
grade, and which grade is reachable is itself gated.

Nodes are triples `(a, g, q)`: agent class `a` holding position `g` at tier `q`.

An edge `(a, g, q) → (a, h, r)` exists when agent class `a` can actually execute
that transition. Its weight is

```
w = log( total value at exit / total value at entry )   over a holding period T
```

inclusive of every term: price, fees, deposit, financing rate, insurance loading,
required minimum, the cost of any prerequisite, service flow received, and any
change in the value of the position over the period.

### Why the weight is a return and not a cost

The obvious version of this construction makes the weight a per-period cost. That
version is a special case of this one and it loses the part of the argument that
matters most.

A cost formulation asks what a position charges to hold for one period. A return
formulation asks what a position is worth at the end of `T` periods relative to
what entering it took. The difference is the change in the value of the position
itself, and for the assets access is gated on, that term dominates everything else
over any horizon longer than a year or two.

Three consequences, and the second is the important one.

**T = 1 with no revaluation recovers the cost formulation exactly.** So nothing is
lost by generalising. The static case is not a parallel fallback to be maintained;
it is what this reduces to, and any result proved here at `T = 1` is a result about
the static field. That matters for defence: the revaluation term is the part most
open to empirical dispute, and at `T = 1` there is no revaluation term to dispute.

**The holonomy compounds.** If a loop returns `δ` per period, then over `T` periods
the accumulated gap is `exp(Tδ)`, and under leverage the exponent is multiplied
again. In a cost formulation non-zero curl is a small persistent leak. In a return
formulation it is an exponentially widening wedge between agents who started level.
Nothing about the mathematics changes; the magnitude of what non-integrability
buys does.

**The framework's ratchet and its non-integrability are the same object.** The
source framework states the settlement ratchet and the non-integrability of the
price field as two separate claims in two separate volumes. Under the return
formulation they are one statement read at two horizons: the ratchet is the
per-period loop sum, and non-integrability is the assertion that the loop sum is
not zero. One reports the mechanism, the other reports its structural consequence.

### Two features that carry the argument

**The field is genuinely pairwise.** `w(a, ·)` is not derived from any scalar on
positions alone, because the same transition carries different terms, and reaches
different tiers, for different `a`. Nothing forces the loop sums to vanish.

**Some edges do not exist.** An agent class below a credit threshold, an asset
minimum, or an accreditation bar has no edge for that transition at any price.
This is the framework's distinction between a hole and a high price, and here it is
a structural feature of the graph rather than a metaphor.

Tier is what makes the second feature bite. A critic will say the excluded agent
could have bought a cheaper instance of the same position. Sometimes true, and
beside the point: `q` is gated separately from `g`, entry to the tier that
revalued required capital and bargaining position at entry, and the return
distribution differs by tier. The exclusion is on the tier, not on the choice
between renting and owning.

### The canonical loop: one dwelling, two vintages

Hold the market, the street, the building and the unit fixed. Vary only when the
owner entered.

| | owner who entered early | owner entering now |
|---|---|---|
| basis | historic price | current price |
| financing | rate locked at entry | current rate |
| carrying cost | low | high |
| `owned → cash → owned` | **edge effectively absent**: repurchasing forfeits the locked rate | available |

The same position costs different amounts to hold depending on who holds it, with
nothing else varying. That is the two-index structure in its purest available
form, and the sign is not in dispute: a holder locked well below market has the
lower carrying cost, and no one argues otherwise.

It also supplies a hole in the same object. An owner holding a rate far below
market cannot sell and repurchase without forfeiting it, so for them the
`owned → cash → owned` edge is effectively absent. They are held in place by a
missing edge rather than by a price, and the standard response to a price, that it
can be paid, does not apply.

This example is canonical here because it needs no revaluation term, so it survives
every objection aimed at the appreciation argument, and because it is measurable
directly from origination vintage and rate.

### The secondary loop: rent against ownership

| leg | agent with access | agent without |
|---|---|---|
| cash → owned, tier `q` | purchase at `P`, financed at the rate available to them | **edge absent**: fails deposit and credit screen |
| owned → housing services | carrying cost `C`, plus revaluation over `T` | — |
| cash → housing services | — | rent `R` |

Traverse cash → owned → housing services → cash over `T` periods. The loop sum is
`R − C` plus revaluation, and if it is non-zero the field has non-zero holonomy.

**A correction worth making loudly, because the obvious version of this example is
currently false.** It is tempting to assert `R > C` as a standing fact. It is not
one. On 2026 data, renting a starter home is cheaper than buying in all 50 major
US metros on a monthly basis, average rent $1,669 against average ownership cost
$2,589, and ownership is cheaper monthly in 23 of the 50 largest metros while
renting is cheaper in 27.

Two things follow, and both help.

The static comparison that produced those figures **cannot see the revaluation
term at all**, since it compares monthly outlays. It is not measuring this loop.
It measures the `T = 1` no-revaluation special case, which is a different and
weaker object.

And the sign of `R − C` varying by market and by year is itself evidence.
Integrability requires the loop sum to be **zero**, not positive. A gradient field
returns zero on every loop, in every metro, in every year, by identity. A quantity
positive in Pittsburgh and negative in San Jose that flips as rates move is not the
difference of any scalar on positions. **The dispersion is the evidence, and a
critic pointing at the sign has conceded the magnitude.**

What the argument needs is only that the loop sum is non-zero and that the closing
leg is unavailable to the party on the wrong side of it. It does not need the gain
to be large, positive, uniform, or anyone's fault.

---

## 4. Why FX is not the case to lead with

Cross exchange rates are the textbook instance: each pair is quoted in a separate
market, so the field is pairwise beyond dispute, and triangular arbitrage is
literally a non-zero loop sum. Non-convertible currencies and capital controls are
literal holes.

It is a clean illustration and a bad headline, for two reasons.

**It invites the wrong objection.** A framework about domestic stratification whose
empirical section is about currency markets will be read as a framework about
currency markets. The reply "we only used FX to demonstrate the mathematics" is a
defensive posture that concedes FX is the main case.

**It is not needed.** The domestic effective-price field is equally pairwise and
equally measurable, as section 5 shows. FX was reached for because its pairwise
structure is undeniable, not because the domestic case is unclear. That convenience
is not worth the framing cost.

**Disposition.** FX appears, if at all, as a short worked illustration for readers
who want an uncontroversial example of non-zero holonomy before seeing the
domestic construction. It carries no result.

---

## 5. Measurable domestic constructions

Each row is the same underlying thing obtained on different terms by different
agent classes, with terms set bilaterally rather than read off a public vector.

| edge | field value | source |
|---|---|---|
| **owned → owned, by vintage** | **carrying cost of the identical dwelling by year of purchase and locked rate. The canonical loop, and the one to measure first** | FHFA, Freddie Mac PMMS history, NMDB |
| cash → housing services, rent vs own | rent against imputed carrying cost including revaluation, by metro **and tier** | Zillow ZORI and ZHVI, ACS, FHFA |
| cash → credit | APR for an identical product by credit-score band | Fed G.19, CFPB consumer credit card agreements database, HMDA rate spreads |
| cash → goods, unit price | price per unit at small pack versus bulk, by store format | retail scanner data; the poverty-premium literature |
| cash → deposit services | maintenance and overdraft fees by balance tier | FDIC bank fee surveys, Reg DD schedules |
| cash → insurance | premium for identical coverage by ZIP and credit score | state rate filings |
| cash → equity position | minimum investment and accreditation thresholds | SEC Reg D |

The last row is a pure hole: below the accreditation threshold the edge is absent
at any price, so it contributes to `H¹` rather than to the curl.

**Sharpened 2026-08-13.** "Contributes to `H¹`" is only defined once a complex is
fixed, and this sentence predates the one [`b1_theorem.md`](b1_theorem.md) §12
settles on. On the square complex of `Γ`, deleting an edge has two possible
effects and they are different claims:

- **Puncture.** The graph stays connected, but every square that contained the
  deleted edge dies with it, so `rank ∂₂` falls further than `b₁` does and
  `dim H¹` **rises**. Measured on a filled 5×6 grid, deleting one interior edge
  moves `b₁` 20 → 19, `rank ∂₂` 20 → 18, `c` unchanged, `dim H¹` 0 → 1.
- **Disconnection.** The graph falls into components: `c` rises and `b₁` is
  unchanged. That is `H⁰`. Measured on a dumbbell, deleting the bridge moves
  `c` 1 → 2 with `b₁` fixed at 2.

**The test is whether `Γ` is still connected after the deletion.** The
accreditation row is a puncture: a class that cannot reach the equity position
still reaches everything else, and other classes still reach equity, so nothing
disconnects and the sentence above stands. The non-assumable mortgage of
[`b1_theorem.md`](b1_theorem.md) §8 is a disconnection, which is why §12.1 rejects
filing *it* under `H¹` and hands it to loop B. The two holes are different objects
and carry different arguments; only the second one is `H⁰`.

On the bare graph, with no 2-cells, neither statement is available: every
1-cochain is closed there, `dim H¹ = b₁`, and deleting edges only lowers it. So
any claim of this shape has to name its complex first.

**Sufficient condition added 2026-08-15, when the block above finally got a
committed source.** `experiments/b1_holes.py` reproduces every number quoted
above and, in the course of doing so, produces a counterexample to the sentence
in bold. **The connectivity test is necessary and is not sufficient.** It
separates a disconnection from everything else. It does not separate a puncture
from a no-event.

The counterexample is on this section's own demonstration carrier. On the same
filled 5×6 grid:

| deleted edge | `c` | `b₁` | `rank ∂₂` | `dim H¹` | verdict |
|---|---|---|---|---|---|
| interior | 1 → 1 | 20 → 19 | 20 → **18** | 0 → **1** | puncture |
| **boundary** | 1 → 1 | 20 → 19 | 20 → **19** | 0 → **0** | **neither** |

A boundary edge lies in one 2-cell rather than two, so `rank ∂₂` falls exactly as
fast as `b₁` does and nothing happens. Both deletions leave the graph connected.

**The sufficient condition is that the deleted edge lie in at least two 2-cells
that are independent given the survivors**, which `hole_kind` computes directly
rather than assuming. Whether it holds turns out to depend on `b₁(G)`:

| `G` | barring `k` classes from one position | `dim H¹` |
|---|---|---|
| **star**, `m = 8` | `k = 1` | 21 → **27** |
| **star**, `m = 8` | `k = 2` | 21 → **32** |
| a `G` carrying one cycle, `m = 3, 5, 8` | `k = 1, 2` | **unchanged in every cell** |

On a `G` with a cycle the 2-cells that die are dependent on the ones that
survive, so the identical operation moves nothing.

**The accreditation row's verdict stands, and the reason given for it is not the
reason it stands.** Six of the seven rows in this section's table have cash on one
side, which is a **star** centred on cash, and a star is what
`product_graph.tier_positions` builds. The verdict holds because the position
graph is a tree. "Nothing disconnects" holds in both columns of the table above
and therefore cannot be what decides it.

**What this does not touch.** No figure moves. Everything stage B2 reports is a
1-skeleton quantity and is invariant under the choice of `C₂`, which
[`b1_theorem.md`](b1_theorem.md) §12.2 proves. This section is the one place in
the repository where the choice is load-bearing, which is why the condition had to
be right.

The first row is the one to do first. It holds the position, the market, the
quality and the unit fixed and varies only the holder, so it isolates the two-index
structure with nothing else moving, and it needs no revaluation term, which is the
component most open to dispute.

Every row must be measured **by tier**, not pooled. Pooling across tiers averages
over exactly the gating the argument is about, in the same way that a national
average would cancel the cross-market dispersion.

**Measurement design is the real work, and it is not done here.** A loop needs its
legs measured on a common basis: same period, same unit, same quality, same
inclusive definition of terms. Housing is the most tractable because both legs are
published and the quality match can be held by unit. Credit is the cleanest for
the pairwise structure because the identical contract is priced by band. Whichever
is used first, the construction of each leg has to be written down before anything
is computed, or the result will be a measurement artefact.

---

## 6. What the theorem will and will not say

**Will.** On a field of this construction, non-zero holonomy around a realisable
loop implies no global potential exists, so no scalar price level reproduces the
terms every agent faces. On the return formulation, a per-period loop sum `δ` that
persists opens a gap of `exp(Tδ)` between agents who began level, which is the
source framework's ratchet stated as a consequence of non-integrability rather than
as a separate mechanism. Separately, on a domain with `H¹ ≠ 0` no global potential
exists even where the curl vanishes everywhere. Machinery exists and can be
borrowed: Ilinski's gauge theory of arbitrage, Farinelli's geometric arbitrage
theory.

**Located 2026-08-13.** That second sentence was written as a separate
speculative channel. It now has an address, and it is not separate.

On `Γ` with its squares filled, [`b1_theorem.md`](b1_theorem.md) §12 gives
`H¹(Γ) ≅ H¹(G) ⊕ H¹(H)`. So whenever `G` carries a cycle, a field that is zero on
every square and non-zero on a slice cycle is closed and not exact: the curl
vanishes everywhere and no potential exists. **That is exactly the slice summand
of Theorem 2.** §11.1's B1-8 exhibits one deliberately, and an independent check
on a four-position `G` with `b₁(G) = 2` and three classes reproduces it: every
square sum exactly `0.000e+00`, slice sums `2.14`, residual against exactness
`3.43`.

Two consequences. The sentence is not a second speculative route to
non-integrability, it is the summand the mortgage carrier provably cannot reach
(Corollary 2) and covered-parity deviations can, which is why §9 orders FX after
loop B rather than dropping it. And §12's "the harmonic component is identically
zero" is scoped to the fields this project has run so far, not to `Γ` in general;
§12 and §11.1 both say so, and this paragraph is the reason that scoping matters.

**Will not.** It will not say the gain is large, that anyone is behaving badly,
that markets fail to clear, or that a planner would do better. It will say a single
price vector is not a faithful representation of the object, which is a statement
about representations.

**Relation to the simulations.** Stage A2c measures cycle structure on the model's
own graph. That is description, and its own module says so. It can motivate an
introduction; it cannot support a universal non-existence claim. Only the same
computation on measured domestic terms would be a finding.

---

## 7. Anticipated objections

**"Your ten-fold return is one-time repricing, not a structural wedge."** The
strongest objection to the return formulation, and it is not answered by asserting
otherwise. Realised returns over a single decade cannot distinguish a per-period
structural gap from one large revaluation that happened to favour holders, because
both look identical after the fact.

Three replies, in decreasing strength.

First, the canonical loop does not depend on revaluation at all. Two vintages of
the same dwelling differ in carrying cost through the locked rate, and that gap is
per-period, contractual, and observable without any appreciation term. An objection
to the revaluation argument leaves it untouched.

Second, the discriminating test is stated in advance: examine **multiple
non-overlapping windows**. A structural wedge shows the same sign in each; a
repricing event shows up in one. If it shows up in one, that is the honest finding
and it gets reported as one.

Third, integrability fails on a non-zero loop sum whatever its cause. A one-time
revaluation that some agents could capture and others could not is still a
non-zero loop sum, and it is still non-capturable because of a missing edge. It
would make the wedge episodic rather than compounding, which changes the magnitude
of the claim and not its structure.

**"The excluded agent could have bought a cheaper house."** Addressed by the tier
index in section 3. The exclusion is from a tier, not from the choice between
renting and owning, and tiers do not share a return distribution. Restating the
objection at the level of tiers is welcome, because at that level it is an
empirical claim about whether tier access is gated, which it demonstrably is.

**"But renting is currently cheaper than buying, so your loop runs the other
way."** Correct, in most metros, at present. Integrability needs the loop sum to
be zero, and a quantity whose sign flips across metros and across years is not the
difference of any scalar. See section 3: the dispersion is the evidence, and a
critic pointing at the sign has conceded the magnitude.

**"Arbitrage is competed away."** Only along edges that exist. The construction's
whole content is that the closing leg is missing for the party paying the gain. The
objection assumes the conclusion it is meant to test.

**"These are transaction costs and risk premia, not arbitrage."** Some of the gap
is compensation for genuine cost and risk, and no part of the argument requires
otherwise. Decomposing the gap is a separate empirical question. Integrability
fails as soon as the loop sum is non-zero, whatever the gap is compensation for. A
critic who wants to save integrability has to argue the loop sum is zero, not that
it is deserved.

**"Then just define the price as the risk-adjusted effective price and it is
integrable again."** This requires a scalar on positions alone that reproduces every
agent's terms. If one exists, the field was a gradient and the framework is wrong
about this economy, which is exactly the empirical question. It cannot be assumed
into existence, and asserting it is a restatement of the one-index assumption
section 2 already put on the critic's side of the ledger.

**"You are talking about FX."** No FX data appears. See section 4.

**"This is just price discrimination, which is well studied."** Price discrimination
is the observation that sellers charge different buyers differently. The claim here
is about what follows for the *representation*: once terms are two-index, a scalar
price level is not a faithful summary and the aggregation step that the standard
argument for decentralised allocation depends on is unavailable. The phenomenon is
familiar; the consequence for integrability is what is being claimed.

---

## 8. Order of work

1. **This document.** Fix the object. Done.
2. **Measurement design.** Write down the loop, its legs, and the inclusive
   definition of each edge, before touching data. The vintage loop first, because
   it carries no revaluation term and its sign is not in dispute.
3. **B2.** Compute holonomy and the Hodge split on measured domestic terms. Report
   the integrable fraction, and report the dispersion of loop sums across markets
   and vintages rather than a single national number, since a national average
   would cancel exactly the variation that carries the argument.
4. **B1 proper.** State and prove the two results, citing step 3 as motivation and
   nothing more.
5. **FX illustration.** Optional, short, explicitly pedagogical.

Steps 2 and 3 come before the proof deliberately. A theorem about a field nobody has
constructed is a theorem about a definition.
