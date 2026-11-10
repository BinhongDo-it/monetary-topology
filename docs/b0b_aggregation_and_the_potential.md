# B0b: three standard constructs, and the object each one needs to exist

Companion to [`b0_claim_scope.md`](b0_claim_scope.md). **This document runs no
measurement of its own.** It is a reading of results already in the record, and
everything it asserts empirically is a pointer to a criterion in
[RESULTS.md](../RESULTS.md).

Theorem 1 in [`b1_theorem.md`](b1_theorem.md) gives an exact criterion for when a
single scalar price vector on positions exists. The criterion is an equivalence
with an elementary proof and no economic assumptions in it. This document asks a
narrow question about it:

> **Which standard constructs presuppose that the object Theorem 1 characterises
> exists, and what happens to them when it does not?**

The constructs treated below are not equally exposed, and the document says which
carry weight.

| construct | the object it needs | status here |
|---|---|---|
| **Domar-weighted aggregation** (Hulten 1978, and the misallocation literature after it) | a frontier `F` whose gradient is the price vector | **load-bearing** |
| **a single pricing functional common to all agents** | `∮ω = 0` on the enlarged graph | **load-bearing** |
| **the `P` in the quantity identity** | a scalar that generates the local exchange terms | **not load-bearing.** Kept as the shortest example of what the assumption looks like |
| **the equilibrium the welfare theorems quantify over** (added 2026-08-29, section 8) | one price system `p` entering every agent's problem | **load-bearing** |

---

## 1. Two projections, and only the first one is at issue

Getting from the primitive object to an aggregate price index takes two steps,
and they fail for different reasons. Keeping them apart is the whole of this
section.

The primitive is a field on edges. For an agent class `a` and a transition from
position `i` to position `j`,

```
w_a(i, j)  =  log of the rate at which class a can convert i into j
```

**Step one, `w → φ`.** Does a function on positions exist whose differences are
those edge values, for every class at once? Theorem 1 says this holds if and only
if every cycle in `Γ = G □ H` sums to zero, and Corollary 1 says a single edge
with `w_a(i,j) ≠ w_b(i,j)` decides it in the negative.

**Step two, `φ → P`.** Given that `φ` exists, compress it to one scalar index.
This is the index-number problem: base dependence, weight choice, the
superlative-index literature and everything downstream of it.

**Step two is old, known, and defended.** Sixty years of index-number theory exist
because everyone involved knows step two is lossy, and there are standard answers
about when the loss is second order.

**The claim here is entirely about step one, and it is prior.** Solving step two
completely changes nothing, because step two takes `φ` as given and `φ` is what
step one supplies. An argument that stops at "aggregation loses information" is a
restatement of the index-number problem and will be answered as one. The argument
that does not reduce to it is that **there is nothing to compress**: no `φ` exists
to be indexed, at any resolution, under any weighting.

That distinction is the reason this document exists.

---

## 2. Construct one: Domar-weighted aggregation

### 2.1 What Hulten's setup actually says

Hulten (1978), *Growth Accounting with Intermediate Inputs*, Review of Economic
Studies 45(3), 511-518. The social production possibility frontier is defined
implicitly,

```
F(Y, J, t)  =  0
```

with `Y` final demand and `J` primary factor supply. The setup then states, at
p. 512:

> "We assume also that the economy is in competitive equilibrium"

and the marginal conditions that follow it identify the normalised prices with
partial derivatives of `F`:

> `P_i = (∂F/∂Y_i) / (∂F/∂Y_1)` and `W_k = (∂F/∂J_k) / (∂F/∂Y_1)`

The aggregation result is then

```
T  =  Σ_i  [ P_i Q_i / Σ_i P_i Y_i ] · (Ḟ_i / F_i)
```

which the paper describes, at p. 514, as

> "essentially the aggregation rule proposed by Domar (1961). The equality in (14)
> indicates that Domar's procedure is equivalent to the rate of change of the
> social production possibility frontier holding primary input constant."

**Read the second display again.** The price vector is not merely consistent with
a frontier. It is *defined as* the normalised gradient of one. `P = ∇F / (∂F/∂Y_1)`
is step one of §1, written out, with `log P` in the role of `φ`: `F`, together
with the competitive equilibrium the setup assumes, is what makes that `P` one vector
common to every agent.

### 2.2 Why the theorem needs it and not just likes it

The load-bearing step in the result is an envelope argument: the first-order
effect of a sectoral productivity shock on aggregate TFP equals that sector's
Domar weight, because the reallocation terms cancel when the allocation is a
stationary point of a function whose gradient the prices are.

**An envelope step needs a function to envelope.** If the local terms are not the
gradient of any function, the allocation reached by following them is not a
stationary point of any function whose gradient generates those terms, and there
is no object for the envelope step to act on. What fails is the
derivation: the identity Domar weight equals the frontier's first-order shift has no
derivation on those terms, whatever number the formula returns.

So the statement available is:

> **Domar-weighted aggregation may hold on a production graph**, where flows
> conserve and weights are shares given by an accounting identity. **It does not
> hold on a claims graph whose field is not exact.** A macro model that runs a claims graph through the
> production-graph machinery inherits that.

### 2.3 The obvious reply, and the shorter answer to it

The reply is that the misallocation literature dropped efficiency long ago.
Baqaee and Farhi price wedges and markups explicitly, so prices there are not
marginal products and the frontier reading no longer applies.

**Handling wedges is a different thing from handling non-integrability.** An
economy with wedges still has a well defined allocation and a well defined
comparative static. The claim here is stronger: the field admits no potential, so
"the allocation reached" is not the optimum of any objective whose supporting
prices are common to all agents, wedged or not.

That is an argument rather than evidence, and the shorter route does not need it.

**Look at the index sets, not at the generality of the wedges.** In
*Productivity and Misallocation in General Equilibrium*, the setup is

> "The model has N producers indexed by i and F inelastic factors indexed by f
> with supply Lf"

with wedges introduced as

> "where Ai is a Hicks-neutral productivity shifter, yi is total output, τij is
> the input-specific tax wedge on good j, and τfig is a factor-specific tax wedge
> on factor g"

and pricing as

> "producer i sets a price pi = µiCi/Ai equal to an exogenous markup µi over
> marginal cost"

**One price per producer, common to every purchaser of that good.** That sentence
is the second half of Theorem 1 condition (4), `w_a = w_b`, stated in the setup
rather than derived. The wedges are indexed `τ_ij`, on a pair of goods, which is
an **edge** index: the first index is the purchasing producer, which is node `i`.
Edge wedges can break the first half of (4), exactness on `G`, and cannot break
the second. Read instead as a class of purchasers on a shared purchase, `τ` is the
second branch of the table below. Generality on the edge index does not produce an **agent**
index, and the field measured on this repository's carriers is `w_a(i, j)`,
carrying both.

The rest is a two-branch argument, and both branches are already answered:

| branch | consequence | what answers it |
|---|---|---|
| **keep one producer per node** | the field has no slot for `a`. `w_a(i,j)` lies outside the representable class, whatever `τ` is allowed to be | stage B2's measurement: fix census tract, year, lien position, loan purpose, occupancy and dwelling type, and 78 percent of the variance in financing terms is still **inside** those cells (`0.7831`, `0.8480` under `min_size = 20`). A single price vector on positions predicts zero |
| **split nodes by agent** | the object becomes the position-by-agent product graph | that is exactly `Γ = G □ H`. Theorem 1 applies to it verbatim, with no economic assumptions, and Corollary 1 is decided by one inequality. Theorem 2 splits its cycle space; Theorem 3 identifies what B2 measured as the square component, on the square reading of `b0_claim_scope.md` §5 |

**The second branch costs the thing the framework was for.** A sufficient
statistic whose dimension grows with the number of agent classes is not a
compression of the network into weights, which is what Domar aggregation is sold
as being.

### 2.4 What §13.4 of the theorem file adds, and what it takes away

[`b1_theorem.md`](b1_theorem.md) §13.4 states, in two-way form, that **the square
summand is reachable** by a saturated two-way specification: it is the interaction
term `γ_ag`, and a difference-in-differences style estimand reaches it. What
Theorem 3 supplies on that summand is the account of *which* quantity it is and
which cycles it sums over, and not a quantity out of reach.

The part that no specification reaches is the other summand: a field with no
potential per agent has no slot in a two-way model of any order, because writing
`P(a, g)` at all presumes the potential exists. That is where §3 goes.

---

## 3. Construct two: one pricing functional for everyone

### 3.1 The assumption nobody defends, because nobody states it

Complete markets, or a single stochastic discount factor, or a linear pricing
functional applying to all traders, all deliver the same structural fact: any two
agents face the same terms on the same transition, so every square sums to zero
and every cycle closes.

**Integrability there is a corollary rather than an axiom.** Nobody writes it down
as an assumption, so nobody has ever had to defend it separately. It arrives
inside "no arbitrage" and is carried by that phrase.

The framework's version is that **executability is stratified**. When a leg of a
loop cannot be traversed by a given class at all, the loop is not an arbitrage
that someone declined to take. It is a path that does not exist for that agent,
and `∮ω ≠ 0` can coexist with no-arbitrage at every observed instant.

### 3.2 Why that coexistence is a theorem here and not a hope

[`b4_directed_edges.md`](b4_directed_edges.md) §5 makes the two-way version
precise. Write `P(ω)` for the set of sub-potentials, `ω̄` for the symmetric
(friction) part and `ŵ` for the antisymmetric part. Under `P(ω) ≠ ∅`, which is the
directed no-arbitrage condition, **Theorem 6(2)**:

> `P(ω)` contains a `φ` with all slacks zero **if and only if** `ω̄ ≡ 0` and `ŵ` is
> exact

So no-arbitrage buys the existence of a sub-potential and buys nothing about
exactness. The two parts are separately non-zero and separately measurable, and
**Theorem 6(4)** bounds one by the other,

```
|S − S'|  ≤  −(S + S')
```

so `ρ := |S − S'| / −(S + S')` lives in `[0, 1]` and is the registered quantity
rather than `S − S'`, because a common friction moves the ceiling.

**Measured, on B13's carrier**: the split is available in 49,116 of 50,055 states
(`0.981`); zero violations of the bound in those 49,116; `ρ` median `0.2000`, and
no state at `ρ = 1`. The index part is non-zero and strictly inside a ceiling that
the no-arbitrage condition itself supplies.

### 3.3 The other summand is occupied too

Theorem 2 splits the cycle space into squares, reachable by many agents on one
edge, and slice cycles, reachable by one agent across several positions. §2.4
above concedes that a saturated specification reaches the squares. **The slice
summand is the one that does not have a coefficient**, because the dependent
variable that a coefficient would be about is undefined when `P(a, ·)` fails to
exist.

[`b1_theorem.md`](b1_theorem.md) §7 recorded per-agent integrability as
*presumably* close to true, on the reasoning that an agent facing a non-zero loop
inside its own opportunity set would trade until it closed. §13.5 reports what
happened when that sentence was measured. Cross-currency cycles in G10, traversed
by one dealer through several positions and never touching the Treasury, run at
**30.9 to 45.6 basis points against a measurement floor of 2.8 to 3.7**, on nine of
nine tenors across eighteen years.

The loop does not close. That row of the table is occupied rather than
hypothetical.

---

## 4. Construct three: the `P` in the quantity identity

**This section is not load-bearing and is written so that it cannot be read as
load-bearing.** It is here because it is the shortest place to see the shape of
the assumption, and for no other reason.

### 4.1 The identity is fine

With `M` a monetary stock and `V` defined as `PY/M`, the relation `MV = PY` holds
by construction. It is an accounting statement about four aggregates and nothing
in this repository disputes it. **The projection is where the content is**: map a
network state to `(M, V, P, Y)`, and the identity holds on the image.

What does not follow is that the `P` obtained that way generates the local
exchange terms. `P_agg = MV/Y` is a number that closes an accounting identity. If
`∮ω ≠ 0`, then by Theorem 1 no scalar on positions generates those terms, so
`P_agg` cannot be lifted back to them at any resolution. The identity remains
true and stops being a description of a price field.

### 4.2 The residual, and why nothing is bet on it

`V ≡ PY/M` is a definition and empty as such. Empirical content enters only when
`V` is given behaviour independent of `M`: stable, or moving predictably with
rates. **That assumption is where anything projected out has to reappear**, since
`V` is the only free slot in the identity.

**No wager is placed on this here.** A station testing it was screened out on
paper: the treatment variable would be institutional or eligibility events, whose
count in the world is a small number, and `M` sits in the denominator of `V` while
the same events move `M`, which is the shared-denominator failure mode catalogued
in [`MEASUREMENT.md`](MEASUREMENT.md). Both are screening arguments, made before
any data was bought.

### 4.3 One illustration, from the A track, labelled as such

**This is a mechanism model and not a measurement of any economy.** It shows what
a projection artefact looks like when both the aggregate and the underlying object
are visible at once, which is a thing a simulation can do and data cannot.

In stage A2c, over 600 rounds:

- the harmonic component's **magnitude** stays within a factor of `1.65` while its
  **share** falls from `2.18e-02` to `8.59e-07`. The criterion's own note reads:
  *reporting the share alone would have said it vanished*;
- circulation over net displacement rises from `4.4` to `268`, while net
  displacement itself stays flat within a factor of `1.62`;
- realised cycle rank collapses to `0.029` of the potential rank **with no edge
  deleted**, and one autonomous edge restores it to `0.783`. The realised graph
  is the edges whose flow exceeds a fixed cutoff, and every cutoff across `145`
  decades reads the same graph.

And in stage A2, under issuance, transaction volume rises `x44.87` while the
effective support of inflow (its inverse Herfindahl) contracts to `x0.402`,
with every node still reached in that realised graph and the production layer
falling to `0.51` percent of all circulation.

A ratio of two aggregates went by orders of magnitude in each case while the
object underneath moved by well under a factor of two, or did not move at all.
That is the shape of the thing, exhibited on a graph where both quantities can be
read off directly.

---

## 5. What this does not claim

Following the pattern of [`b0_claim_scope.md`](b0_claim_scope.md) §3, since the
same misreadings are available here.

**Does not claim** that `MV = PY` is false. It holds by construction and §4.1 says
so.

**Does not claim** that the index-number problem is solved, or that it is the
problem. §1 separates the two projections precisely so that this document is not
read as a contribution to the second one.

**Does not claim** that Hulten's theorem is wrong on the object it is about. On a
production graph with the stated equilibrium conditions, the frontier exists by
assumption and the result follows from it. The claim is about what happens when
the same machinery is applied to a claims graph.

**Does not claim** that any author assumed something they did not. §2.3 quotes the
setups because the argument is about what the setups say, and the index sets are
visible without reading a single proof.

**Does not claim** that a saturated specification cannot reach the square
component. §2.4 says it can, and says which summand is left.

**Does not claim** that anyone behaved badly, that markets fail to clear, or that
some other architecture would do better. Those are `b0_claim_scope.md` §3's
entries and they carry over unchanged.

---

## 6. The setup questions

Theorem 1 is an equivalence with an elementary proof and no economic assumptions
in it. The empirical step of the programme, whether the measured object is the
field the claim is about, is set out in `b0_claim_scope.md` §5.

§2.3's index argument rests on reading the setups. A formulation in that
literature whose sufficient statistic carries an agent index on a shared
transition, with a dimension that does not grow with the number of agent classes,
would answer the cost stated under the second branch of §2.3's table. It would do
so by writing the agent index on a shared transition, which is the product graph
`Γ` and concedes the non-zero square the carriers measure.

Four questions put the index argument in executable form, and they are the shape
any extension of this section should take:

1. In the theorem being cited, does one industry node correspond to one producer
   or to a family of heterogeneous producers? Quote the setup.
2. What index set does the wedge carry: `(i, j)`, `(i)`, or something with an
   agent dimension? Quote it.
3. In the heterogeneous-firm variants, do firms inside one node face the same
   input price? If they do, the first branch holds inside the node.
4. In the aggregation statement, what is the dimension of the sufficient
   statistic, and does it grow with the number of agents?

**A row that cannot be answered by quotation should be deleted rather than
softened.** "That literature broadly assumes ..." is the failure mode this section
is arranged to prevent, and a paraphrase of an opponent is worth less than nothing
because it is the thing they will answer instead of the argument.

---

## 7. Citation status

The quotations in §2.1 and §2.3 were taken from the following documents, and the
page numbers given are the ones those documents carry:

- Hulten, C. R. (1978), *Growth Accounting with Intermediate Inputs*, Review of
  Economic Studies 45(3), 511-518, pp. 512 and 514.
- Baqaee, D. R. and Farhi, E., *Productivity and Misallocation in General
  Equilibrium*, model setup, and the companion note *A Short Note on Aggregating
  Productivity*.

Section 8 carries its own sources in section 8.6.

**Before any of these are quoted in a manuscript, check each against the published
version of record and attach equation numbers.** Working-paper and published
setups differ, and §6's standard applies to this document as much as to anything
it argues with.


---

## 8. Construct four: the object the welfare theorems quantify over

Added 2026-08-29. Same question as sections 2 to 4, put to the construct that does the
most work outside this literature and is least often written down as needing anything.

### 8.1 What the setup says

**Two features of the standard setup carry this section, and neither is in dispute in any
presentation of it.** They are stated here rather than quoted, because what the argument
uses is the form of the definition and the form of the theorem, and both are the same in
every source.

**First, a competitive equilibrium is a price system together with an allocation.** In a
private ownership economy each household maximises its utility over a budget set priced by
`p`, each firm maximises profit over its production set at the same `p`, and markets
clear. **One `p` enters every household's budget set and every firm's profit problem.**
That is not an incidental feature of one presentation. It is what makes the object a price
*system* rather than a list of bilateral terms.

**Second, the First Welfare Theorem is stated over that object.** Its hypothesis is that
`(p*, x*, y*)` is an equilibrium of such an economy, with preferences locally non-satiated;
its conclusion is that the allocation is Pareto optimal. **The hypothesis names an
equilibrium, and an equilibrium contains a `p*`.**

### 8.2 Why the theorem needs it and not just likes it

Sections 2 and 3 turn on an envelope step and on a common pricing functional. This one
turns on something more elementary and therefore harder to repair.

If no single scalar on positions generates the observed terms, then there is no `p*` for
the triple `(p*, x*, y*)` to contain. **The hypothesis is not false. It is unsatisfiable.**
A theorem whose hypothesis cannot be met on a carrier says nothing about that carrier: its
domain is empty there. That is as far as the hypothesis goes. **Section 8.2a continues to
the conclusion, and on a carrier that meets its conditions the conclusion is false.**

Theorem 1 in [`b1_theorem.md`](b1_theorem.md) gives the criterion, Corollary 1 decides it
with a single edge, and the carriers in [RESULTS.md](../RESULTS.md) are where it was
measured.

**This is the sharpest form of the general point, and it uses the inequality alone.** It
makes no comparison of anybody's welfare and does not assert that any market fails to
clear. [`b0_claim_scope.md`](b0_claim_scope.md) fixes this record's position at issuing no
welfare criterion that someone has to choose, and this section is consistent with that: it
removes a theorem's applicability. Section 8.2a adds the one verdict that needs no chosen
criterion, Pareto dominance, under conditions it states.

### 8.2a The fork, and the Pareto verdict it carries

Added 2026-09-29. Section 8.2 stops at the hypothesis. This section continues to the
conclusion, and on a carrier that meets the conditions below the conclusion is false.

Take one transition `(i, j)`, two classes `a` and `b` adjacent in `H`, and the square of
[`b1_theorem.md`](b1_theorem.md) §3. Its sum is `σ = w_a(i, j) − w_b(i, j)`, and Corollary 1's
premise is `σ ≠ 0`.

**The fork.** Suppose

- **C1.** the positions `i` and `j` each pass between the two classes at weight zero, which
  is A1 of `b1_theorem.md` §8;
- **C2.** `w_a(i, j)` and `w_b(i, j)` are marginal executable rates for a positive quantity,
  so neither is an average over a schedule and neither is rationed at the margin;
- **C3.** the reverse leg is available at the inverse rate, which is Theorem 1's
  antisymmetric setting;
- **C4.** the four legs are the same two positions, which is A3.

Let class `a` hold one unit of `i`, and let `σ > 0`. Class `a` converts it into
`e^{w_a(i,j)}` units of `j` and passes them to class `b`; class `b` converts them back at
`e^{−w_b(i,j)}` and passes the result to `a`. The unit returns as `e^{σ}` units of `i`. For
`σ < 0` the square runs the other way. **Each unit cycled comes back as `e^{|σ|}` units of
`i`, a gain of `e^{|σ|} − 1` at no risk**, and a side payment in `i` leaves both classes
strictly better off, provided each prefers more `i` to less. No single class can take the
gain: a square needs two agents, and no single agent traverses it (`b1_theorem.md`
§9.1). The two classes together can.

> **So a non-zero square is one of two things: a riskless joint gain of `e^{|σ|} − 1` per
> unit cycled, or a failure of C1, C2 or C3 on a named leg of that square, which is a
> located barrier or friction.**

Both branches are findings about the carrier. The second contains the hole of
`b1_theorem.md` §8, where the agent edge "does not exist" and "the square is not a cycle".
On a field with spreads C3 fails on every leg that carries one, and the fork reads on the
directed square of [`b4_directed_edges.md`](b4_directed_edges.md) §5.1. A positive directed
sum `S` is a round trip that ends with `e^{S}` for each unit, and by Theorem 4 there no
sub-potential exists. Where both orientations are non-positive, the spread on the named legs
is the located friction, and Theorem 6(4) bounds the index part `S − S'` by it.

**The Pareto form.** The joint gain assumes only that more `i` is preferred to less. The
standard wedge argument uses first-order conditions and delivers the verdict the First
Welfare Theorem is about. Suppose

- **P1.** `w_a` and `w_b` are the effective marginal terms that enter each class's
  first-order conditions, with taxes, fees and financing included, and risk-adjusted
  where the terms are risky;
- **P2.** each class is at an interior optimum of a differentiable problem, a household with
  locally non-satiated preferences or a firm minimising cost over a differentiable
  technology, so that its marginal rate of substitution between `i` and `j` (of technical
  substitution, for a firm) equals `e^{w_a(i,j)}`, and likewise for `b`;
- **P3.** quantities at the two positions can be reassigned between the two classes, by
  resale or at the point of supply, leaving every other agent's bundle unchanged;
- **P4.** A1 and A3 hold.

Class `a` then values a marginal unit of `i` at `e^{w_a(i,j)}` units of `j`, and class `b`
at `e^{w_b(i,j)}`. With `σ > 0` let `b` pass a small quantity `ε` of `i` to `a` and receive
`qε` of `j`, for any `q` strictly between `e^{w_b(i,j)}` and `e^{w_a(i,j)}`. At first order
`a` gains `ε (e^{w_a(i,j)} − q)` and `b` gains `ε (q − e^{w_b(i,j)})`, both in units of `j`,
and no other bundle moves. **For small enough `ε` both classes are strictly better off, so
the observed allocation is not Pareto optimal.** Where the two classes are firms the same
reassignment raises both outputs, which is production inefficiency, and locally
non-satiated households take the gain from there.

**This uses each class's own ordering of bundles and nothing more.** There is no
interpersonal comparison, no cardinal utility and no social welfare function. The verdict
concerns the allocation, relative to the economy's resources and technology, so it does not
depend on which instruments are available to reach the dominating allocation. **On a
carrier that meets P1 to P4, the conclusion the First Welfare Theorem is cited for, that the
allocation the market reached is Pareto optimal, is false, and one inequality shows it.**
The theorem's proof is untouched: its hypothesis fails there (section 8.2), and its
conclusion fails with it.

The result is the standard one. At an interior Pareto optimum every pair of consumers has
the same marginal rate of substitution between two goods, and every pair of producers the
same marginal rate of transformation; this is in every text that proves the welfare
theorems, including those section 8.6 names. Diamond and Mirrlees (1971) show that, under
their conditions, an optimal commodity tax system keeps production efficient, with every
producer facing the same prices. Varian (1985) decomposes the welfare effect of
third-degree price discrimination and isolates the misallocation that arises because
consumers facing different prices end at different marginal rates of substitution. **What
Corollary 1 adds is that the wedge is decided by one edge and one pair of classes, with no
tolerance band.**

**Where the conditions hold by construction.** P1 holds wherever the terms are printed as
rates by statute, treaty or fee schedule, since the printed rate is then the term at the
margin. Carriers of this kind in [RESULTS.md](../RESULTS.md) include:

- **stage B21**, A+H dual listings, where the Connect legs are withheld at 0%, 10% or 20%
  under the statutes that section names;
- **stage B23**, the same wedge priced by treaty, the two classes "both withheld at source
  and both flat";
- **stage B122**, value added tax, where the rate is printed per input and the deductible
  share per class of buyer. Goods against services, full deduction against the simplified
  method, reads `106/113`, `−0.0639` in log, in exact rational arithmetic. The Pareto form
  there is production inefficiency in Diamond and Mirrlees's sense: two classes of firm
  face different relative costs of the same two inputs.

On these carriers P2 is the local non-satiation the First Welfare Theorem already assumes,
with differentiability at an interior point added, and P3 and P4 are read carrier by
carrier.

**The currency reforms decide the fork in their own text.** `b1_theorem.md` §8 records that
A1 is "denied in the text of a law" there: the statute prints each class's terms. The
programmes also rule on whether notes may pass between classes. Russia's 1993 exchange,
read in stage B47, later "added proof that the money was held before 26 July". Where the
text cuts the agent edge the carrier sits on the second branch, with the barrier printed.

**Where the conditions need work.** On stage B2's mortgages the quoted rate includes
compensation for default, so the effective marginal term of P1 is the risk-adjusted one, and
the Pareto form on that carrier needs the risk-adjusted field. The existence result does
not: Corollary 1 reads the quoted terms.

### 8.3 The escape, and its price

The escape is the same one section 2.3's second branch already priced: **enlarge the
commodity index so that it carries the transacting party.** A loan to class `a` and the
same loan to class `b` become two commodities, one price vector exists again, and the
theorem applies.

Two things follow, and they are the price.

**First**, the sufficient statistic's dimension grows with the number of agent classes,
which is what section 2.3 records as costing the thing the compression was for.

**Second, and specific to this construct**, on the enlarged commodity space each
class-good has exactly one buyer class. The theorem still holds, and it now holds of an
object in which no two classes trade the same commodity. **What the literature applies the
theorem to is the unenlarged economy**, where a common good exists and its allocation
across agents is the thing being called efficient. The enlarged version is a different
object with the same theorem attached to it, and saying so is not a refutation of anyone.
It is a statement about which of the two objects a given carrier is.

**Section 8.2a prices the same escape from the other side.** In the enlarged space the
position held by `a` and the position held by `b` are two commodities. If the position could
still pass from one class to the other at no cost, the two commodities would be perfect
substitutes and their prices would be forced together, so the enlargement carries two
prices only where the agent edge is cut or costly. **The enlargement therefore sits on the
fork's second branch by construction**, and the Pareto optimality the theorem then delivers
is optimality relative to a technology in which the position cannot pass between the
classes at no cost.

### 8.4 The same step, one level down: the quadratic loss function

The New Keynesian loss function in inflation and the output gap is obtained as a
second-order expansion of a representative household's utility around an efficient steady
state. **It rests on the same object as section 2.2's envelope step**: one price vector
faced by every household. A representative household is constructed over one price vector
faced by every household, and Corollary 1 excludes that wherever two classes face different
terms on the same transition. The loss function therefore has no application to such a
carrier.

[`b0d_new_keynesian.md`](b0d_new_keynesian.md) section 5.3 records the consequence for that
literature: the normative closure it has over this framework is not an advantage this
framework lacks, it is an artefact of the assumption this document is about.

### 8.5 What this section does not claim

Following section 5's pattern, since the same misreadings are available.

**Does not claim** that the welfare theorems are wrong. On an economy with a price system
they hold, and section 8.1 quotes the hypothesis rather than disputing the proof.

**Does not claim** that any market fails to clear, or that anyone behaved badly. Those are
`b0_claim_scope.md` section 3's entries and they carry over unchanged. On efficiency the
claim is the one section 8.2a makes: under its conditions the allocation reached is not
Pareto optimal.

**Does not claim** that the enlargement in section 8.3 is illegitimate. It is legitimate
and it is priced, which is a different objection.

**Does not claim** a welfare judgement that depends on a chosen criterion. Section 8.2
removes a theorem's applicability using the inequality alone, and section 8.2a supplies the
one judgement that needs no chosen criterion, Pareto dominance, under its stated conditions.
`b0_claim_scope.md` section 2 records the same division.

### 8.6 Citation status for this section

**Section 8.1 carried two quotations and no longer does.** They had been taken from
teaching material rather than from a text of record, and rather than leave an unsourced
quotation standing they were removed and the two statements written out directly. Section
6's rule is to delete a row that cannot be answered by quotation rather than soften it, and
this is that rule applied to this section.

**Why the statements survive the removal, when section 6 bans paraphrasing an opponent.**
That ban is aimed at claims about what a body of work assumes, where formulations differ and
a paraphrase can quietly pick the convenient one. Section 6's own four questions are all of
that kind. These two are not: the definition of competitive equilibrium and the form of the
First Welfare Theorem do not vary across sources, so there is nothing to pick. **The
operative difference is that if the statements in 8.1 were wrong they would be wrong in
every textbook at once**, which a reader checks against their own copy rather than against a
source this document chose.

**What the argument needs from them is narrow and is visible in the statements themselves**:
that the definition quantifies over one price system, and that the welfare theorem's
hypothesis names an equilibrium. Neither needs surrounding text and neither is contested.

**If either is ever quoted in a manuscript it is transcribed from the book at that point**,
either Debreu's *Theory of Value* (1959) or Mas-Colell, Whinston and Green (1995), and from
the book rather than from a description of it. **Section numbers are deliberately not given
here.** An attempt to fix them from online copies returned a table of contents from a single
mirror with no second source that could corroborate it, and a number carried in on one
unverified mirror would be the same defect as the quotation it replaced.

**Section 8.2a cites on the same footing.** The equal-marginal-rate conditions at an interior
Pareto optimum do not vary across sources any more than the definition of equilibrium does,
so they are stated and not quoted. The applications named there are Diamond, P. A. and
Mirrlees, J. A. (1971), "Optimal Taxation and Public Production I: Production Efficiency",
*American Economic Review* 61(1), and Varian, H. R. (1985), "Price Discrimination and Social
Welfare", *American Economic Review* 75(4). For the reason above, no section, lemma or
proposition number is given for either.
