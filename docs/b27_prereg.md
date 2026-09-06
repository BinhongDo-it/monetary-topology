# B27 preregistration: does a graph of asserted price references close around a cycle?

**The hypothesis is out of sample.** It was written into the project's framework
before any of the readings in B25 or B26 were taken, and this station tests the
half of it that those two do not touch.

## 0. What this station is for

**It is not a test of whether price theory works.** Theorem 1 settles that on its
own terms and Corollary 5.4 names the locus: the single-price account is the zero
set, all classes agreeing and the common field exact. **This station does not
revisit that.**

**It is part of what comes after.** Once the price field admits no potential, the
questions that remain are constructive: **what produces a price, what kind of
object a price is, and what special case the older account turns out to be a
case of.** A theory that removes an object owes an account of what stands where
it stood.

**And it answers the rejoinder that account invites.** If no potential exists,
why does the world look so much like a world where one does? **Corollary 5.4 says
the zero set has measure zero in the field space, so sitting on it is not an
accident.** This station's answer is that the zero set is where interested parties
keep the system, and it names the mechanisms by which they keep it there.

**So the finding is not that some conventional system fails to close.** It is
that **apparent consistency is maintained rather than natural**, which is a
statement about why the older account survives its own failure, and it is the
kind of statement that theory needs when it retires an object.

---

**What B25 and B26 do not carry.** They establish that posted prices track a
reference rather than cost or local income, and that a posted focal number is
rigid while other fields absorb the adjustment. **Both are premises**, and both
are independently established in the literature on other carriers by tighter
designs, which is recorded in their own files. **Neither touches the claim that
reference propagation around a cycle admits no global potential.** That claim is
this station's entire subject.

**Why the earlier carriers could not carry it, restated so it is not retried.**
Sellers refer upward to one leader, which is a star; a star is a tree; its first
Betti number is zero; and with no independent cycle there is nothing for a
holonomy to be non-zero around. **This station's first obligation is therefore to
find a carrier whose reference graph has cycles, and to show it has them before
anything else is read.**

**The instrument is not this project's.** Reading cyclic inconsistency off a graph
of comparisons is HodgeRank, cited in
[`b0c_precedent_topological.md`](b0c_precedent_topological.md) §2a. This station
uses it and says so. **What is this project's is the choice of object it is
applied to.**

---

## 1. The object, and the trap that must be avoided first

A reference relation is an **asserted** factor: a statement that X should stand
at some ratio to Y, made independently of any statement about Z.

**The trap.** If every ratio is computed from one common price vector, then
`a(A,B) x a(B,C) x a(C,A) = 1` identically. That is arithmetic, not a reading,
and a station built on it would have one reachable outcome. **A candidate carrier
is admissible only if its factors are asserted separately**, by different
statements, and this must be demonstrated per edge rather than assumed.

**Admissibility test, applied before any cycle is computed.** For each edge,
name the document that asserts that factor and show that it does not derive the
factor from a scalar shared with the other edges of the cycle. **An edge that
fails is deleted from the graph, not adjusted.**

---

## 2. Criteria

**B27-0  the graph has cycles.** Compute the first Betti number of the admissible
reference graph after §1's deletions.

- `b1 >= 3` → proceed
- `b1 = 0` → **the carrier is a tree and this station closes on it**, as the
  earlier ones did, and that is reported rather than worked around
- `b1` of 1 or 2 → too few independent cycles to separate signal from a single
  idiosyncratic assertion; report and do not proceed

**B27-1  do the cycles close.** On the admissible graph, take logs of the
asserted factors, treat them as an edge flow, and apply the Hodge decomposition.
Report the gradient, curl and harmonic energies and their shares, **and the
magnitudes alongside the shares**, since a share can fall because its own
component shrank or because the rest grew.

- harmonic plus curl energy is a fraction of total that exceeds `0.10` → the
  asserted factors do not come from any global scalar
- below `0.02` → they are consistent with one, and the hypothesis fails here
- between → undecided, reported as undecided

**B27-2  is the non-closure larger than the assertions' own imprecision.**
Assertions are stated to finite precision. Bound the non-closure attributable to
rounding by recomputing with each factor perturbed to the edges of its stated
precision, worst case.

- measured non-closure exceeds that bound → it is not a rounding artefact
- within the bound → **the station reads nothing**, whatever B27-1 says

**B27-3  the null that must be reachable.** Construct the same graph from factors
that are known to derive from a common scalar, and run B27-1 on it.

- that control returns harmonic plus curl below `0.02` → the instrument does not
  manufacture non-closure
- the control returns non-closure too → **the instrument or the construction is
  producing it and the station is void**

---

## 3. Gate arithmetic

**Type of criterion: energy shares against pre-declared thresholds, with a
bound-check arm and a null control.** There is no estimator and no sampling
inference, so the zero-multiple gate and the power floor do not apply. **The
bound in B27-2 replaces them and is the arm that can void the station.**

| gate | number |
|---|---|
| independent cycles | **B27-0 computes it and it gates everything after** |
| square degeneracy | if the complex is built with two-cells, check whether the squares are degenerate before reading curl separately from harmonic. On the bare graph every one-cochain is closed and only the two-way split is available |
| resolution floor | **the stated precision of the assertions**, propagated in B27-2. This is the floor that matters and it is not instrument noise |
| private bilateral contract | to be checked per carrier. An assertion that lives only in a private mandate fails and its edge is deleted |

---

## 4. Reachability

**Both outcomes of B27-1 are available and this is what makes the station worth
running.** A body of asserted factors that happens to derive from consensus
scalars returns near zero, and that is a real possible world: it is what a market
with a single agreed valuation model would produce. Non-closure is equally
available. **Neither is forced by the construction, provided §1's admissibility
test is applied honestly, and §1 exists because without it only one outcome is
reachable.**

**What is excluded.** No claim about prices, only about asserted factors. If the
factors fail to close while the prices they refer to do close, that is a fact
about the assertions and this station may not upgrade it into a fact about the
market.

---

## 4a. Population, and an honest note on how the first carriers were found

**The first nine carriers were nominated, not sampled.** They were thought of, one
at a time, and screened as they arose. **That is a real objection to reading a
count off them and it is answered by defining a population and re-running the
screen over it rather than by arguing that the objection does not matter.**

**Disclosure, under the project's own rule.** Criterion timing is not disclosed,
because criterion shape is not a degree of freedom here. **Selection of what gets
screened is a different matter and is disclosed**: the carriers below were chosen
before a population existed, so the population is defined here and the screen is
re-run over it in full.

**The population.** Publicly documented systems in which **two or more parties
each publish a factor converting between units of account**, such that a chain of
two or more conversions is operationally available to some party. Six domains are
named in advance and enumerated exhaustively within each, with inclusion decided
by the structural test rather than by the answer:

1. loyalty and rewards currencies, across airline, hotel, card issuer and retail
2. stored value instruments, including gift cards, platform currency, transit and
   campus cards
3. credential and qualification equivalence between institutions
4. professional licensing reciprocity between jurisdictions
5. administered exchange rates published by customs, tax and multilateral bodies
6. assessment and valuation adjustment factors

**Reported for the population**: how many members exist, how many admit a cycle,
and for those that do not, which of the two maintenance mechanisms accounts for
it. **A member that cannot be classified is reported as unclassified rather than
dropped.**

---

## 5. Carrier, and a rule for choosing one that is derived rather than guessed

**Not fixed here.** The admissibility test in §1 and the cycle count in B27-0 are
the selection criteria, and a carrier is chosen by passing them rather than by
being nominated first. **Candidates are screened before any data is purchased**,
since the §1 trap is what would make the whole station circular and it is cheap
to check on a handful of documents.

### 5a. First screening round, every carrier failing on B27-0, and why the last one is informative

| carrier | §1 admissibility | B27-0 cycles | why |
|---|---|---|---|
| consumer electronics price bands | passes | **`b1 = 0`** | sellers refer upward to one leader: a star |
| prepared beverage price points | passes | **`b1 = 0`** | same shape |
| loyalty point transfer ratios | **passes cleanly** | **`b1 = 0`** | **unidirectional by policy.** The trade statement is flat: transferring out is a one-way street and the points cannot come back. No lateral edges between programmes either |
| retail gift card balances | passes | **`b1 = 0` in general** | cash buys the card at a published rate; the card does not buy cash |
| platform virtual currency | passes | **`b1 = 0`** | money buys the currency at a published rate, and the reverse edge is deleted in the terms of use |

**The last three failures are not like the first two and the difference is the
finding.** In the first two the acyclicity is incidental: reference is
hierarchical because sellers look up at a leader. **In the last three it is
enforced**, and in two of them the deletion is written down in a document the
issuer publishes. One platform's currency terms state it twice over: the currency
"[has] no cash value and [is] not redeemable for any sum of money or monetary
value", and it "may not be sold, transferred, assigned, redeemed or exchanged for
cash."

**The reason is not obscure.** If such a cycle closed and its product were not
one, it would be a pump against whoever sits on the losing edge, and that party
writes the terms.

**The gift card case is not a fourth example. It is a test of the claim, and it
passes.** If the reverse edge is absent because the loss-bearer removes it, then
compelling the loss-bearer should make the edge reappear, and it does: **ten US
states require cash refunds of small gift card balances, at thresholds set by
statute rather than by any economic quantity**: `0.99` dollars in two states,
`4.99` in six, `9.99` in California, since raised. Elsewhere there is no such law
and no such edge.

**So the edge is not impossible, it is removed**, and it returns exactly where a
regulator puts it back and only up to the amount the regulator names. **That is
the distinction between a hole and a high price, demonstrated by an instrument
that toggles the hole.**

**So a proposition, and it should be tested rather than assumed.** Where a
reference cycle could close and fail to close, someone bears the loss, and that
someone deletes an edge. **Observed reference graphs are then systematically
acyclic, and their acyclicity is endogenous rather than evidence that the
conventions are consistent.** This is the project's own distinction between a
hole and a high price, appearing from the other side: **the missing edge is what
keeps the field looking integrable.**

### 5a-2. A further round, each carrier failing on a different condition

Screening continued under §5b's first rule, on carriers where the asserter does
not trade. **All three fail, and none fails the way the first five did**, which
is what turns one selection condition into three.

| carrier | asserter is not the loss-bearer | cycles | fails on |
|---|---|---|---|
| airline partner mileage earning rates | **yes.** Each programme publishes its own percentage per partner and fare class | **yes.** Alliances are cliques and the programmes credit each other's flights | **composability.** A flight credits to exactly one programme. The edges are independent mappings, not operations that chain, so a product around the cycle has no operational meaning |
| inter-institution course credit articulation | **yes.** The receiving institution asserts the equivalence and the student bears the loss | **yes**, in principle, since roles rotate across agreements | **the factor is not multiplicative.** Acceptance is closer to an edge existing or not than to a number on an edge |
| official exchange rates published by customs and tax authorities | **yes** | **yes.** Different authorities publish the same pairs | **§1.** The rates derive from a common market scalar at different lags, so non-closure is a timing artefact rather than an asserted convention |

### 5a-3. The case where the edge could not be deleted, and what happened instead

**A merger forces a composable edge into existence**: balances in the absorbed
programme must convert into the surviving one at some stated ratio, and no party
can decline to publish it. That is the situation §5a's mechanism cannot handle by
deletion, so it is the sharpest available test of the proposition.

One large hotel merger supplies it, and all three factors are public.

```
absorbed programme -> airline           20,000  ->  25,000
absorbed programme -> surviving         1 : 3, so 20,000 -> 60,000
surviving programme -> airline          60,000  ->  25,000
```

**The diagram commutes exactly.** Twenty thousand points reach twenty five
thousand miles by either route, and the trade account states the identity in one
line: the absorbed programme's units equal three times as many of the surviving
programme's units equal the same airline miles.

**The conversion factor was chosen so that it would commute.** Three is not a
number the merger discovered; it is the number that makes the two paths agree
given the two pre-existing charts.

**So the proposition needs a second mechanism, and this matters more than another
example would.** Where the edge can be removed, the party bearing the loss removes
it. **Where it cannot be removed, that party sets the factor so the loop closes.**
Two mechanisms, one outcome: **observed reference graphs are consistent, not
because convention is consistent, but because whoever controls the factors makes
them so.**

---

### 5b. The selection rule as it now stands

**One. The factor-asserters must not be the loss-bearers.** Where the party stating
the conventional factor also transacts on it, that party can and will remove the
edge that would close a cycle, and B27-0 fails by construction rather than by
accident.

**So the carrier must be one where the assertions are made by third parties who
do not trade on them.** Assessors, raters and analysts state factors as
judgments; they neither gain nor lose from a cycle failing to close, and they
have no instrument for deleting an edge.

**Two. The edges must be composable.** A holonomy is the value of traversing a
loop, so the edges have to be operations that chain. A family of independent
mappings from one object into several currencies has cycles in its diagram and
nothing to traverse.

**Three. The factors must be asserted rather than derived**, which is §1
restated, and it is the condition the exchange rate carrier fails despite passing
the other two.

**Four, and on the evidence this is the load-bearing one. No single party may
control enough of the cycle to make it commute.** Every one of the nine carriers
screened so far had one party positioned over the whole loop, and that party
either deleted an edge or set a factor to close it. **The edges of the cycle have
to be set by different parties who do not coordinate**, or the diagram will
commute by someone's decision rather than by any property of convention.

**And a tension between the first two, which is the reason this is hard.**
Composable edges create pump risk; pump risk makes the loss-bearer delete an edge,
which is §5a; and parties who bear no loss generally do not control composable
edges either. **So third-party assertion and composability rarely coexist.**

**The exception is the case to look for, and it is specific: the composing is done
by someone who is neither the asserter nor able to delete an edge.** A student
chains transfer credits, a taxpayer chains published rates, a market participant
chains one appraiser's adjustments against another's. **The asserter states a
factor and walks away, and no single party is positioned to remove the edge that
would close the loop.**

**The open lead.** Property appraisal adjustment grids satisfy all three
conditions: the adjustments are asserted line by line, they are multiplicative or
additive in a stated currency, they chain across independently produced reports,
and the appraiser bears none of the consequence. **The obstacle is access rather
than structure**, since appraisals are delivered privately, **and the identified route
is assessment appeal filings, which are public record in many jurisdictions but
appear to require case-by-case retrieval rather than bulk access. That is the
next thing to check and it has not been checked.

**Candidates meeting all four, to be screened next and not yet checked.**
Independently produced property appraisals, which remains the standing lead;
notching of the same issuer pairs by different rating agencies; and reciprocity
rules between professional licensing jurisdictions, where each board publishes
what it will accept from each other board, the rules chain, and no board
coordinates with the others.

**This rule is derived from nine screenings and not from a preference for any
particular carrier**, which is why it is recorded here rather than in a note.
**It also predicts its own failure mode**: if a carrier meeting all three
conditions turns out to be acyclic as well, then §5a's proposition is wrong in its
general form and must be narrowed rather than restated.

**A note on what the difficulty does and does not mean.** Eight carriers have
failed, and that is evidence that observable reference cycles are rare. **It is
not evidence that the hypothesis is false.** Rarity of a carrier and falsity of a
claim are different findings, and §5a gives a mechanism for the rarity that is
independent of whether the claim holds: the loops that would be measurable are
the loops someone has an interest in breaking.
