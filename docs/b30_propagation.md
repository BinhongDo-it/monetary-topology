# B30: how a price propagates, and what arrives

**Status: construction, organisation and vet. Registered 2026-08-30. No arm run.**
Upstream sibling of [`b29_locality_theorem.md`](b29_locality_theorem.md).
**The design file is [`b30_prereg.md`](b30_prereg.md)**, which carries the arms in
their current form, the gate arithmetic, the population and the order of work.
This file carries the construction and the reasoning behind it.

---

## 0. The question

B29 takes a price field as given and asks what local arbitrage can remove from it.
**This asks where the field came from.** The named cases:

1. the first or most authoritative trading pair, and how its signal travels;
2. how a signal is adjusted inside each local loop before being handed to the next;
3. broadcast across a subgraph, a province inside a country;
4. the pricing of a local speciality once it leaves home;
5. the advantage of holding information edges and distribution channel edges, and
   the reading that "the information is in the price" usually means percolated
   information: the previous matrix found it reasonable, and the previous matrix
   may only have been the one before it not objecting.

---

## 1. Two operators, and only one of them makes a field

**Projection.** Arbitrage acts on cycles. It removes the component of the field in
the span of the cycles the agents can walk. It never creates a value. That is all
of B29.

**Transport.** Quotation acts on paths. An edge that has never traded gets its
value copied from a neighbouring edge with an adjustment. This is what creates the
field.

**A graph of relations determines a level field only up to one constant per
connected component.** The relations are differences; differences fix a function
up to an additive constant. So transport needs a boundary condition, and someone
has to supply it.

**That is what the authoritative pair is.** Not a better-informed participant, and
not a participant with more weight in an average. **A supplier of the one constant
the relations cannot fix.** The count is exact:

```
number of independent anchors required = dim H0 = number of components
```

**This closes a loop with an earlier reading.** [`b25`](b25_price_band_availability.md)
located the robustness of price discrimination in `H0` rather than `H1`, as a
degree of disconnection. The same `H0` counts the anchors. A market that separates
into two components needs two anchors and can hold two unrelated levels
indefinitely, and neither is wrong, because nothing relates them.

---

## 2. What propagation produces is a tree, and the defect is born at a datable moment

Transport has a **front**. The anchor is priced, then its neighbours, then theirs.
Each position takes its value from whichever neighbour reached it first, with that
neighbour's adjustment applied.

**The result is a spanning tree of the graph, and a tree has `b1 = 0`.** So while
the front is still expanding the field is exact by construction. **There is no
inconsistency anywhere in a growing market.**

**Inconsistency is created at the meetings of the front with itself.** Each
non-tree edge is one meeting: two propagation paths arrive at the same relation
carrying different accumulated adjustments. The number of independent meetings is
exactly `b1`.

**So the defect is not noise laid on top of a consistent field. It is manufactured
at events, one per independent cycle, and each event has a date.** After the
meetings, B29's projection runs and removes the ones sitting inside short loops.
**What survives is the set of meetings that happened across loops longer than the
arbitrage reach.**

**This is measurable.** If the field were a distance-weighted equilibrium, two
regions equally far from the anchor would hold equal values. If it is a
propagation tree, two regions equally far from the anchor but reached through
different intermediaries hold different values, **and the difference is inherited
from the branch rather than generated locally**, so it should correlate with the
intermediary's own deviation and not with the region's own conditions.

---

## 3. A closed local loop becomes one node at the next scale

A loop that arbitrages to completion presents a single consistent face outward.
**At the next scale up it is a node.** The clusters then form their own graph, that
graph has its own `b1`, and B29's threshold applies again with the reach measured
at that scale.

**Reach shrinks relative to size as the scale coarsens.** There are many agents who
arbitrage across a street and few who arbitrage across a border, while the loop
lengths grow. By B29's threshold the defect therefore lives at the coarse scales
and is absent at the fine ones.

**This matches everything measured so far.** Prices are consistent within a store,
within a chain, within a country. The dispersion appears at 41 countries
([`b25`](b25_price_band_availability.md), price to income range 60.58) and across
program boundaries ([`b27`](b27_results.md), the loyalty loop at spread 2.40).

**It is also a search instruction, and it runs opposite to the usual one.** To find
inconsistency, look at bigger loops rather than at smaller ones more carefully.
Refining measurement at the fine scale searches the region where the theory
predicts exact zero.

---

## 4. Broadcast over a subgraph, and the relation that cannot be checked

A province is dense inside and thin outside. Inside, the diameter is small
relative to the local reach, so the whole subgraph reaches one consistent value
quickly. Outside, it connects through few edges.

**Checkability is a cut, and Menger's theorem counts it.** A relation between two
regions can be tested only by comparing two routes, so

```
independent checks available = (edge-disjoint routes between the regions) - 1
```

**A region joined to the rest by a single intermediary has zero checks.** Not an
unmeasured relation, an unfalsifiable one: there is no second path, so no cycle,
so nothing for Theorem 1 to test. This is the same shape as the project's D29 and
D30 gates, arrived at from the propagation side.

**Prediction.** The dispersion of a relative price between two regions should fall
with the number of independent routes joining them, and a relation carried by one
intermediary should show both the largest dispersion and the slowest correction.
**Sole-distributor arrangements are the extreme cell** and they are common enough
to sample.

---

## 5. The local speciality leaving home

Before export, the good is priced inside its own cluster against its own anchor.
On export it acquires an edge to a foreign shelf. **Two anchors now touch one
object, and the question is which one wins.**

The framework's entry reading answers it: the entrant adopts the destination's
anchor. **So the export price is set by what the good is placed next to, not by
its home price and not by its cost.**

Two predictions follow, and they point in opposite directions, which is what makes
them worth running.

**Where comparables are dense**, the same good exported to two destinations should
sit at different multiples of its home price, and the multiple should track the
destination's own ladder rather than the freight and duty. Dispersion should be
**small within a destination** because the ladder is tight there.

**Where comparables are absent**, there is no anchor to attach to and the price is
underdetermined in the framework's exact sense. **Dispersion should be large, and
inversely related to the density of comparables at the destination.** Goods with
no foreign category to enter are the carriers: a national spirit, a regional tea,
a meat grade with no local equivalent.

**This is a scope condition and not a hedge.** It names where the framework
predicts tight prices and where it predicts wide ones, and it fails if the two
cells come out the same.

---

## 6. Two graphs on the same positions: what trades and what watches

Let `G_T` be the graph of who transacts with whom and `G_I` the graph of who
observes whose price. **They are different, and `G_T` is contained in `G_I`.**

**Transport runs on `G_I`. Falsification runs on cycles of `G_T`.** A price can be
copied along an edge that carries no trade, and no trade can then contradict it.

```
checkable subspace   = span of the cycles of G_T
asserted remainder   = everything else in the field
```

**This is the formal content of the promotion advantage.** Holding many
information edges and many channel edges buys transport reach. It does not buy
checkability, because checkability needs a second trading route and an
advertisement is not one. **A seller with a wide information graph and a narrow
trade graph is in the best position the construction allows: their number
propagates everywhere and can be contradicted nowhere.**

**It also says what the "information priced in" claim can and cannot mean.** The
part of a price supported on trade cycles is disciplined. The part supported on
information edges alone is asserted, and the ratio of the two is a computable
number for any network where both graphs can be drawn.

---

## 7. What an information edge carries when it carries an absence of objection

The content passed along an information edge is often not a fact about the object.
It is the neighbour's state, and the neighbour's state was itself a copy. **The
terminal content is that nobody objected.**

**An absence of objection has no magnitude, so it constrains no factor.** Each hop
applies its own multiplicative adjustment, and none of the adjustments is pinned
by anything the hop can observe. **The composite along a path is therefore
unconstrained, and it is unconstrained precisely because every step was locally
unopposed rather than despite it.** This is the same object as B27's asserted
factor, reached from the propagation side instead of the convention side.

**The discriminating measurement, and it is clean.** Information decays with
distance: each relay discounts what it did not verify, so the amplitude of a shock
at the anchor should fall in the number of hops. **Copying does not decay.** So:

- amplitude falling roughly geometrically in hops → what moved was information
- amplitude flat in hops → what moved was a convention
- amplitude flat **across an edge that carries no trade** → the sharpest cell,
  because no information channel and no arbitrage channel is available to carry it

**One instance is already in the framework.** The entry price of a foreign phone
into a large market was the home price converted at the exchange rate, which is
full amplitude with zero decay across the largest edge available, and the domestic
band then anchored on it. **That is the flat case, and it was not sought as a test
of this, which is why it counts.**

---

## 8. Percolation and phase transitions: three different objects, one of them critical

**8.1 B29's threshold is combinatorial, not critical.** `L*r >= n` on a
deterministic regular graph is a sharp threshold with no critical window, no
diverging correlation length and no exponent: the gap goes 1 to 0 between two
consecutive integers. **Calling it a phase transition invites a search for
exponents that are not there**, and this file records that so a later reading does
not go looking.

**8.2 Randomise the graph and a real percolation problem appears, but not the
usual one.** With long links present at rate `p`, whether the short cycles span
the cycle space becomes a random event with a threshold. **The relevant object is
homological rather than ordinary percolation**: ordinary percolation asks when a
spanning cluster appears, which is `H0`; here the question is when `H1` of the
short-cycle complex vanishes. There is an existing literature on exactly this
(thresholds for homology in random complexes, homological percolation on lattices
and in growing complexes), and B29 chunk two is a question in it.

**8.3 There are two thresholds, and the interesting phase is between them.**

```
p_connect   : the signal reaches everyone            (H0 becomes trivial)
p_homology  : the values everyone holds agree        (H1 becomes trivial)
```

**These are different thresholds and `p_connect` comes first.** Between them lies a
regime in which **a price is universally known and globally inconsistent.** Every
participant has heard the number, every local check passes, and no global level
exists. **That is the regime this project keeps measuring**, and naming it as the
gap between two percolation thresholds is the clearest statement of what the
framework claims the world is in.

**8.4 The adoption side has a genuine critical window, and this project has
already returned a negative on it once.** Granovetter thresholds and the Watts
cascade window are real critical objects and they govern whether a convention
spreads at all. **The A2e gate tested one carrier for a cascade window and found
none**: two disjoint tight unimodal bands, zero within-run crossings, an integer
knob with no intermediate value. So criticality is not available to be assumed
here. It has to be found on a carrier that shows it.

---

## 9. Precedent, and where this differs

**The propagation half of this is a large and mature literature and none of it is
claimed here.**

- **Duffie, Malamud and Manso**, *Information Percolation With Equilibrium Search
  Dynamics*, *Econometrica* 77(5), 2009, doi:10.3982/ECTA8160. Agents meet, share,
  and beliefs converge.
- **Golub and Jackson**, *Naive Learning in Social Networks and the Wisdom of
  Crowds*, *AEJ: Microeconomics* 2(1), 2010, 112-149. DeGroot updating on a
  network; the crowd is wise when the most influential agent's influence vanishes.
- **Banerjee** (1992) and **Bikhchandani, Hirshleifer and Welch** (1992).
  Cascades: agents copy predecessors and aggregation stops.
- **Allen, Morris and Shin**, *Beauty Contests and Iterated Expectations in Asset
  Markets*, *Review of Financial Studies* 19(3), 2006, 719-752.
- **Golub and Morris**, *Expectations, Networks, and Conventions*, working paper,
  December 2017. **This is the closest by a wide margin.** Higher-order average
  expectations over a network of counterparty relations, unified with classical
  beauty contests by Markov methods; the consensus is the eigenvector-centrality
  weighted average of priors; and the **tyranny of the least informed**, in which
  everyone coordinates on the prior of the worst-informed participant despite
  nearly common certainty of the right action. **The reading that the price
  reflects nobody having objected has a formal published version there.**

**Where this differs, stated as a modelling difference and not as priority.**

Every model above propagates a **node** quantity. Each agent holds a belief about a
scalar, the update operator is row stochastic, and a row-stochastic irreducible
matrix has a unique stationary distribution. **Consensus is therefore delivered by
the modelling choice before any economics enters**, and Golub and Morris state the
consequence directly: the limit unconditionally produces a single scalar outcome.

**A price is an edge quantity.** An agent who trades A for B learns the ratio on
their own edge and learns nothing about the ratio to a good they never touch.
**Agreement on every edge does not produce a global level**, and the failure is
exactly `H1`.

**The obstruction needs two things and only two.** That the propagated object lives
on edges, and that each agent observes only their own edges. Hand every agent a
full price vector over all goods and the obstruction vanishes, because a vector of
levels is a node quantity again and the stochastic machinery applies coordinate by
coordinate. **That is the assumption the literature makes, and it is made in the
choice of state space rather than in a stated assumption**, which is why the
question does not come up there.

**Open check.** Whether the edge-valued version has been done is not settled.
Ilinski's lattice gauge treatment of prices, recorded in
[`b29_locality_theorem.md`](b29_locality_theorem.md) §5, is the first place to
look, and until it is read this is an open question rather than a novelty claim.

---

## 10. What this generates

Five measurements, written before any carrier is chosen so that a later prereg
cannot reshape them.

***Superseded by [`b30_prereg.md`](b30_prereg.md) §2**, which carries these five
plus B30-6 through B30-9 and a control arm, with gate arithmetic. **B30-1 below is
the uncorrected form**; the correction is §12.5 and the corrected criterion is in
the prereg. The table is kept as written so the failure mode stays visible.*

| arm | quantity | first branch | second branch |
|---|---|---|---|
| **B30-1 decay** | amplitude of an anchor shock against hop count | flat in hops → convention | geometric decay → information |
| **B30-2 routes** | dispersion of a relative price against the number of edge-disjoint routes | dispersion falls with routes, largest at one route → checkability is the binding constraint | no relation → route count is not the mechanism |
| **B30-3 destination ladder** | export multiple over home price, for one good in two destinations | tracks the destination ladder → the destination anchor wins | tracks freight and duty → cost explains it |
| **B30-4 no comparable** | dispersion of export price against density of comparables at the destination | dispersion rises as comparables thin out | flat → anchoring is not what sets it |
| **B30-5 front** | deviation of a region against its propagation branch and against its own conditions | loads on the branch → the field is a tree | loads on local conditions → the field is an equilibrium |

**B30-1 and B30-5 are the two that can kill the whole construction**, since a
geometric decay in hops and a loading on local conditions would both say the field
is generated by information reaching agents who price against their own
circumstances, which is the reading this file is set against.

---

## 11. Scope

**The construction half is arithmetic.** Transport on a graph with cycles is a
connection; its path dependence is holonomy; a tree carries none; a spanning tree
plus `b1` extra edges carries `b1` independent disagreements. None of that needs
data and none of it carries any weight about the world.

**The claim half is that real price fields are generated this way**, and nothing
above establishes it. Every arm in §10 is unrun.

**Nothing here requires anyone to be irrational, uninformed or foolish.** Every
agent in the construction arbitrages perfectly over everything they can reach and
copies faithfully along every edge they hold. The obstruction is in what they can
reach, not in how well they think.

---

## 12. Vet, 2026-08-30

**Verdict first.** The construction holds. Two of the offered instances are correct
as offered and one of them sharpens the whole file. One is a mixture and points at
a different arm than the one it was offered for. One needs its date corrected and
becomes stronger evidence after the correction. **One arm as written in §10 would
have produced a false positive**, and that is fixed below.

### 12.1 Holds without qualification: the information edge with no trade edge

*"Information arrives, people want to buy, the maker will not sell."* That is
`G_I` without `G_T` on the same pair, and it is a better instance than §6 had,
because **the refusal to sell is an observable deliberate act of edge deletion**
rather than an absence to be inferred.

**It unifies with [`b27`](b27_results.md).** That station found convention systems
holding apparent consistency by deleting edges, with the statutory gift-card
reversal proving the deletion was a choice. Refusing to sell across a market
boundary is the same operator, run by the same kind of party, for the same reason:
**the participant who would lose if the loop closed removes the edge that would
close it.**

**New arm B30-6.** Refusal to sell, region locking, warranty non-portability and
authorised-channel restriction should be **concentrated where the cross-market
price gap is largest**, and should relax where it narrows. A maker with a uniform
world price has no reason to region-lock. First branch: restriction density tracks
the gap. Second branch: it tracks logistics or regulation instead, and the reading
fails.

### 12.2 Holds and sharpens everything: the haircut, and what actually discriminates

***Superseded in part by §12.9.** The case below is right and the variable it
names is wrong. Read §12.9 with it. The section is kept as written because the
wrong variable is the one a reader would reach for first.*

The offered case: haircuts are one price per city; cities cross-reference through
urbanisation but a small city with few links to large ones is its own subgraph;
and quoting a large city's price to a small city's customer gets the quoter
abused rather than paid.

**This is the control cell the file was missing.** Copying succeeds for the phone
and fails for the haircut, and **the variable that separates them is not
tradability.** It is the density of the local trade graph around the buyer.

| | local trade graph | what happens to a copied number |
|---|---|---|
| haircut | dozens of substitutable sellers within walking distance, repeat purchase | a local cycle closes in one step and contradicts it immediately |
| phone | one posted national price, no local alternative at all | no local cycle exists, so nothing contradicts it |

**Restated in the file's own terms: an anchor is required per component, and the
only question is who fills it. A dense local market fills it locally. A sparse one
imports it.** Tradability matters only because it usually correlates with local
density, and the correlation is what makes the tradable and non-tradable split
look like the explanation when it is not.

**This yields the sharpest test in the file, B30-7, because it has a cell that no
one would construct on purpose.**

- **tradable, dense local market** (wet-market vegetables, generic staples) →
  copying should fail and the local price should rule, despite the good moving
  freely
- **non-tradable, sparse local market** (the sole crematorium, the single water
  utility, the only specialist clinic in a small city) → copying should succeed,
  and the price should track the reference city rather than local income

**These two cells separate the framework from the standard account.** If
non-tradables simply track local income, the second cell tracks local income. If
the reading here is right, it tracks the reference city. **The predictions differ
in sign and the data exists**: regulated utility tariffs, funeral service
schedules, private school fees and specialist fee schedules are all published by
city.

**And the abuse is the mechanism, not colour.** Being cursed at is the objection
channel firing. So **the falsifiable form of "nobody objected" is that the price
persists exactly where the objection channel is closed**, which is a statement
about market structure and not about psychology.

### 12.3 A mixture, pointing at a different arm than the one it was offered for

The Big Mac. **The one-price-per-country half is right** and it is the uniform
pricing fact already carried in [`b25`](b25_price_band_availability.md) through
DellaVigna and Gentzkow.

**The cross-country half is the documented income case, not the anchor case.** The
Big Mac's international variation is the standard illustration of the Penn and
Balassa-Samuelson effect, to the point that the index is published in a
GDP-adjusted form for exactly that reason. The burger is tradable inputs plus
heavily non-tradable labour and rent, so it is a mixture by construction.

**So it is the wrong carrier for the percolation claim and a good carrier for the
mixture, with an ordering that is itself the test.** The price-to-income
dispersion of the Big Mac should sit **strictly between** the phone and the
haircut: B25 measured the phone at a price-to-income range of 60.58 across 41
countries, the haircut is the local end, and the burger should land in between and
nearer the local end than the phone. **An ordering across three carriers is a
stronger test than any one of them**, and every input is already published.

### 12.4 Right claim, wrong date, and better after the correction

As offered: the early China price of the foreign phone was inexplicable and plenty
of people bought it anyway. **Two periods have to be separated.**

- **2009-11-02.** The 32GB model launched officially through the carrier at
  **6,999 yuan** with the wireless radio removed. Roughly **1.5 million grey
  handsets were already in the country**, over a third of them running on the
  rival network. About 300 people queued at the flagship store, which trade press
  contrasted with the lines abroad and called a slow start. The carrier cut the
  price in December 2010.
- **From the following generation, 2010 onward.** The same high price relative to
  income sold in volume, and the market became one of the maker's largest.

**The volume claim is correct and belongs to the second period.** The correction
makes the instance stronger rather than weaker, because **2009 is a positive test
of this file rather than an embarrassment to it**: a second route existed, it
carried 1.5 million units, the grey device was the better one on features, the
loop closed, and the copied price lost and had to be cut. **The file predicts that
a copied price stands only where the second route is absent, and 2009 is the cell
where it was present.**

**This is a natural experiment worth its own arm.** Same product, same country,
same posted price level relative to income, and the treatment is the presence of a
competing route. Both outcomes are realised three years apart.

### 12.5 The design flaw: B30-1 as written would have fired on nothing

**"Flat amplitude in hops implies convention" is wrong as stated, because
broadcast produces the identical signature.** If every participant reads the same
source then every participant is one hop from it, flatness is trivially true, and
the arm returns its first branch while measuring nothing.

**Two-step flow is the standard statement of why the graph has both paths at
once**: the source reaches the public directly and also through opinion leaders,
so hop count is not identified without knowing which path a node used.

**Corrected B30-1.** Hops are counted in the quotation graph, and the arm requires
a control for direct access to the source. **The discriminating cell is a node
with no direct access and a long relay path**; flat amplitude there is the
signature, and flat amplitude among nodes with direct access is nothing at all.
The uncorrected version is left in §10 with this correction referenced, so that
the failure mode stays visible.

### 12.6 What communication research says

**Serial distortion.** Bartlett's serial reproduction (1932) and Allport and
Postman, *The Psychology of Rumor* (Henry Holt, 1947): transmission **levels**
(detail drops out), **sharpens** (the few surviving elements are amplified) and
**assimilates** (the residue is fitted to the receiver's expectations).

**This reads at first as a contradiction of the flat-amplitude prediction and it
is the opposite.** What levels off is the **justification**. A price has no detail
to lose, being one scalar, so it is precisely the element that gets sharpened, and
the receiver's local adjustment factor is assimilation. **The classical finding is
therefore that the number survives at full amplitude while the reason for it does
not survive at all**, which is the mechanism this file needs. It is the strongest
external support here and it is seventy-nine years old.

**Two-step flow** (Katz and Lazarsfeld): source to opinion leaders to public, a
tree with hubs, which is §2's front with the branch structure made explicit.

**Gatekeeping** (Lewin 1947; White 1950): a small number of nodes decide what
passes, which is §1's authoritative pair arrived at from the other side.

**Diffusion of innovations** (Rogers; Bass 1969): the imitation coefficient is the
copying term, and the standing lesson that **hearing and adopting are different
curves with different timing** is §8.3's two thresholds in the discipline's own
vocabulary.

**Pluralistic ignorance and the spiral of silence** (Noelle-Neumann, *Journal of
Communication* 24(2), 1974): silence propagates because each participant infers
the majority from the absence of expressed dissent, which then suppresses further
dissent. **That is the published form of "the previous one did not object".**

**Where the discipline does not help, and it is the same gap as in economics.**
Communication research has no consistency condition on a cycle. Its dependent
variable is adoption, belief or salience, all **node** quantities, so it inherits
exactly the limitation §9 identifies: **a node quantity always admits a
consensus.** No diffusion model found here carries an edge-valued object, so none
of them can produce an obstruction even in principle.

### 12.7 The two thresholds are now computed rather than asserted

`experiments/b29b_two_thresholds.py`. `G(n, p)` at `n = 40`, five seeds, gap
`= b1 - rank(span of cycles of length at most L)`.

| p | connected | b1 mean | gap mean, L=3 | gap mean, L=4 |
|---|---|---|---|---|
| 0.08 | 0.0 | 19.6 | 15.2 | 11.4 |
| 0.10 | 0.4 | 33.8 | 25.8 | 14.6 |
| 0.12 | 0.4 | 48.8 | 33.8 | 12.4 |
| **0.15** | **1.0** | **73.8** | **43.4** | **5.6** |
| 0.20 | 1.0 | 117.6 | 41.8 | 0.2 |
| 0.25 | 1.0 | 154.8 | 23.6 | 0.0 |
| 0.30 | 1.0 | 194.2 | 7.6 | 0.0 |
| 0.35 | 1.0 | 228.8 | 1.2 | 0.0 |
| 0.50 | 1.0 | 344.8 | 0.0 | 0.0 |

**`p_connect` lies between 0.12 and 0.15. `p_homology` at horizon 3 lies between
0.35 and 0.50, and at horizon 4 between 0.20 and 0.25.** The gap between the two
thresholds is a factor of roughly three in `p` at horizon 3.

**Inside that window the graph is fully connected and 43.4 of 73.8 independent
cycles are unresolvable, which is 59 per cent.** Everyone has heard the number,
every check anyone can run passes, and a majority of the independent relations
have no consistent value. **That is §8.3's phase, computed.**

**The gap is non-monotone in density and this was not predicted.** It rises from
1.0 at `p = 0.04` to a peak of 43.4 at `p = 0.15` and falls to zero by `p = 0.50`.
A sparse market has few loops and therefore few disagreements; a dense one has
enough short cycles to fill them all; **the most globally inconsistent market is
the moderately connected one.** This is falsifiable and it is the opposite of the
reading that inconsistency is a symptom of thin markets.

**Raising the horizon from 3 to 4 cuts the peak by a factor of three and halves
the vanishing threshold**, which is B29's range result appearing again in the
random setting.

### 12.8 What would kill the whole thing

Unchanged from §10 and now with two additions from this vet.

- **B30-1 corrected**: geometric decay in hops among nodes with no direct access
  to the source.
- **B30-5**: regional deviation loading on local conditions rather than on the
  propagation branch.
- **B30-7 second cell**: a sparse-local-market non-tradable whose price tracks
  local income rather than the reference city. **This is the cleanest single
  observation that would sink the file**, and it is cheap to look for.

> **Pointer, 2026-09-01. The third item has been looked for and the file
> survived it.** Both branches of B30-7 cell B were observed on 2026-08-30 on
> two carriers in the same class of towns, and a third independent source
> reproduced the ordering on fifty-three items at once: Shanghai against Harbin,
> class rule fixed before the table was fetched, LADDER median **1.003** on
> seventeen items against an income ratio of **0.3398**, LOCAL median **0.611**,
> full spread across all items a factor of **fourteen**. Readings in
> ``b30_results.md``, the B30-7 cell B sections and the city-pair section; code
> in ``experiments/b30_7_city_pair.py``.
>
> **So this list now has two live items, not three: B30-1 corrected and B30-5.**
> The text above is left as written.

> **Pointer, 2026-09-03. The list has one live item, not two.** B30-5 ran as a
> cross-section on 2026-09-01 and returned two PASS criteria; its registered text
> names no clock, which is why it could run where B30-1 could not. Registration
> and limit in ``b30_prereg.md``, reading in ``b30_results.md``. **What a
> cross-section does not separate is inheritance down a tree from a common cause
> reaching both regions independently**, and that residue needs the same input
> B30-1 needs, which is dated arrival. **So the two remaining gaps on this side
> are one purchase and not two: a quotation network with a countable hop gradient
> and dated arrivals.**
>
> **B30-1's own gate is worth naming rather than leaving as a carrier failure.**
> The quotation graph returned a maximum hop distance of one. That is gate zero
> (``D18``) on the hop variable, and on electronically published quotations the
> answer will keep coming back one, because publication makes every reader
> adjacent to the source. **That is a property of the family, not of that
> carrier.** Under gate zero's 2026-08-27 clause the next question is whether the
> variable varies on some other observation unit, and three families are recorded
> here as directions rather than as choices: eras where transmission cost was
> non-zero, so that reprint chains are dated by issue and cite their source;
> institutionally tiered release, where a documented subset holds the number
> before the public does; and oral or non-electronic relay. **None of the three
> has been screened.**

### 12.9 Correction to 12.2: density is the wrong variable, substitutability is the right one

**The coffee case breaks the density reading, and it breaks it cleanly.** Local
coffee supply in a large Chinese city is abundant by any measure, and three price
levels sit on the same street at once: a domestic chain at 9.9 yuan, a foreign
chain priced at or above its home price after conversion at the market rate
despite far lower local income, and independent specialty shops higher still.
**Density did not collapse them, so density is not the mechanism.**

**What matters is whether two sellers are parallel edges in the buyer's own
substitution graph.** Two quotes for a thing the buyer treats as one thing are
parallel edges between the same pair of positions, and parallel edges form a
2-cycle, the shortest cycle that exists, so the loop closes at once. Sellers the
buyer does not treat as exchangeable are not parallel edges at all. They sit in
different components, and nothing joins them.

```
within one substitution class : price collapses to one, and the anchor is
                                whatever the densest local reference is
across substitution classes   : no cycle exists, nothing collapses, and each
                                class carries its own anchor, which may be
                                imported from anywhere
```

**This corrects the haircut reading as well, and the correction was inside the
original example.** The same city carries ten-yuan quick cuts and two-hundred-yuan
salons at the same time. The two-hundred quote draws abuse only when it is offered
for the ten-yuan class; walk into the salon and it is paid without complaint. **So
the haircut and the coffee are one case, and §12.2 was wrong about the haircut in
exactly the way it was wrong about the coffee.**

**Product differentiation, restated.** Differentiation is not the making of a
better object. **It is the deletion of the edge that would let a buyer close a
loop.** That is the same operator as [`b27`](b27_results.md)'s deletion and as
§12.1's refusal to sell, applied to a third graph: the buyer's substitution graph
rather than the trade graph or the information graph.

**This closes §6.** The promotion advantage was described there as the holding of
information edges. It is two operations serving one end: **it adds information
edges and it removes substitution edges.** The value of a brand is then exactly the
price gap it can hold, which is the size of the `H0` it manufactures. **Three
prices for one cup on one street is `dim H0 = 3`, and the components are
maintained rather than found.**

**Cheap prediction: the three should not co-move.** The domestic chain's number
should move with local competition, the foreign chain's with its own global ladder
and the exchange rate, the independents with bean cost and rent.
[`b26`](b26_results.md) already holds half of it: the 9.9 did not move while unit
cost rose 36 to 46 per cent and non-focal prices on the same menu did move.

### 12.10 The natural experiment has already happened, it is dated, and it is the whole file in one event

On **2026-08-07** delivery platforms placed the foreign chain into the same list,
under the same coupon mechanics, as the domestic chain. One platform's voucher was
**12.9 yuan, the same number as some of the domestic chain's vouchers**, and paid
prices of **4 and 6 yuan** appeared, against a band that had held for more than a
decade. Reporting on 08-09 is explicit that **the brand did not initiate this**,
and the brand issued a statement on 08-08.

**The price gap was held by the absence of a substitution edge and not by anything
about the object.** A third party who was neither buyer nor seller created the
edge, the loop closed, and the gap went in a day. **The brand's same-day statement
is the deletion operator trying to fire and failing, because the platform owns
that edge and the brand does not.**

**New arm B30-8, and it is the best identified thing in this file.**

| | |
|---|---|
| treatment | creation of a substitution edge by a third party |
| date | exact, 2026-08-07 |
| treated unit | the two chains' paid prices on the platform |
| control | the same brand's in-store price on the same days |
| outcome | the gap between the two chains' paid prices |

- gap collapses on the platform **and persists in store** → the edge held the
  price, and nothing about the object changed
- gap collapses in both → something other than the edge moved and the design is
  not identified
- gap persists on the platform → substitutability is not the mechanism and §12.9
  is wrong

**The in-store leg is what identifies this and it has not been collected.** It is
the next thing to fetch, not a thing to assume, and the arm is recorded here
unrun.

---

## 13. What supply and demand do, and what they do not do

**The standard objection to everything above is that prices are set by supply and
demand. The objection is correct and it is about a different quantity.** Supply and
demand govern the **support** of the graph and the **speed** on an edge. They do
not pin the **value** on the edge, and they say nothing at all about whether the
values are mutually consistent.

**Three statements, and only the first is what the objection asserts.**

1. **Existence, and it is necessary.** If nobody will buy at any price, or the
   object cannot be obtained, the edge is not in the graph and there is nothing to
   price. Supply and demand decide which edges exist. **This file assumes it
   throughout and does not contest it.**
2. **Speed, and this is supply and demand too.** Once an edge connects with demand
   standing behind it, the value on that edge moves fast. §12.10 is exactly this:
   the edge appeared and a decade-old gap closed in a day. A queue of buyers
   waiting for an object that becomes purchasable is the same phenomenon.
3. **Level, and this is not supply and demand.** Which number the edge settles on
   is not determined by 1 and 2. **The existence proof is a digital good with an
   unlimited free substitute**: marginal cost zero, supply unbounded, a free
   alternative of the same functional kind one click away, and the posted price
   positive, clustered on a focal grid, and stable for years.

**So the relation is necessary and not sufficient**, and the framework's own
results say where the remaining freedom lives. Theorem 1 says the levels need not
admit a global potential however each one was set. Theorem 7 says local arbitrage
cannot remove the residue even when every agent is perfect.

**The strongest form of the objection has a computed answer.** *In equilibrium
arbitrage would eliminate any inconsistency.* **That is Theorem 7's own statement,
and Theorem 7 computes the residue: it is zero exactly when `L*r >= n` and one
otherwise, with no window in between.** The objection is right about the mechanism
and wrong about the reach.

---

## 14. The limiting cell: a named individual as an object with no substitute

**A carrier class in which every structural feature of this file sits at its
extreme.** It is stated as a class, because the finding is about the class and no
single member is load bearing.

**Named-individual subscription with an abundant free substitute.** The object is
access to the output of one identified person. Members: paid newsletters, creator
membership tiers, streaming channel subscriptions, fan clubs, and adult
subscription platforms. **Every member has the same four properties.**

1. **Marginal cost zero.** A further copy costs nothing.
2. **An unlimited free substitute of the same functional kind**, in effectively
   infinite supply and of comparable production quality.
3. **No substitute for the object itself.** The object is *that person's* output,
   so there are no parallel edges and `b1 = 0` around it by construction. **A named
   individual is a monopoly on themselves, and this requires no market power, no
   barrier to entry and no strategy.** It is B30-7's sparse cell taken to a single
   provider.
4. **The platform posts the ladder.** Minimum and maximum prices and the focal grid
   are set by the platform rather than by either side of the transaction.

**Prediction, and it is this whole file inside one carrier.** Prices should cluster
on the platform's own focal grid, should be close to uncorrelated with output
volume, audience size or anything about the object, and should differ across
platforms in the way the platforms' posted ladders differ. **Cost cannot explain
it, because cost is zero. Scarcity cannot explain it, because the substitute is
unlimited. The posted ladder is what is left.**

**The competing explanation fails a gradient test on its own variable.** The
standard account is parasocial attachment. **If attachment is what is bought, then
willingness to pay should rise with the bandwidth and the synchrony of the
contact**: one-to-one live contact should command the most and asynchronous
one-to-many the least. **The observed ordering is the reverse.** The asynchronous
one-to-many subscription is the large market and the synchronous one-to-one form
is the small one. **Attachment predicts the wrong sign on the variable it is
named after.**

**The account here gives the right sign.** The monthly subscription form **imports
a mature and extremely dense anchor**, the general digital subscription ladder,
which is among the most heavily posted price grids that exist. **The per-minute
live form has no such anchor**: its reference class is service labour billed by
time, which is thinner, locally variable and not posted. So the subscription form
is priced by copying a ladder that is already there, and the live form has to be
priced from nothing each time. **The relative size of the two markets follows the
availability of an anchor rather than the intimacy of the contact.**

**And the reading that buyers never asked why they are paying is already formal
here.** The free substitute is not in the same substitution class, because the
class is fixed by the named person, so the comparison that would close the loop
never forms. **That is a statement about the substitution graph. It is not a
statement about anyone's intelligence, and no arm in this station reads buyer
competence.**

***Refined by the first reading, 2026-08-30.** The prediction above is right about
the floor and too strong about the whole distribution.
[`b30_results.md`](b30_results.md) §5 finds the floor universal across five domains
and five enforcement regimes, and the **ceiling varying by domain**. The grid pins
the entry point, which is where the anchor is densest, and above it there is
domain variation. Read §14 with that attached.*

**Why the class and not one platform.** The four properties hold across publishing,
streaming, music and adult content alike, and the arm is specified over the class
so that any single member can be removed without touching the result. **A finding
that survives dropping any one member is also a finding that cannot be dismissed
by objecting to that member.**
