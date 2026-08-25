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

Three are treated below. They are not equally exposed and the document says which
carries weight.

| construct | the object it needs | status here |
|---|---|---|
| **Domar-weighted aggregation** (Hulten 1978, and the misallocation literature after it) | a frontier `F` whose gradient is the price vector | **load-bearing** |
| **a single pricing functional common to all agents** | `∮ω = 0` on the enlarged graph | **load-bearing** |
| **the `P` in the quantity identity** | a scalar that generates the local exchange terms | **not load-bearing.** Kept as the shortest example of what the assumption looks like |

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
is step one of §1, written out, with `F` in the role of `φ`.

### 2.2 Why the theorem needs it and not just likes it

The load-bearing step in the result is an envelope argument: the first-order
effect of a sectoral productivity shock on aggregate TFP equals that sector's
Domar weight, because the reallocation terms cancel when the allocation is a
stationary point of something.

**An envelope step needs a function to envelope.** If the local terms are not the
gradient of any function, the allocation reached by following them is not the
argmax of anything, and there is no object for the envelope theorem to act on.
The conclusion is not that the theorem gives the wrong number. It is that the
quantity the theorem is about is not defined.

So the statement available is:

> **Domar-weighted aggregation may hold on a production graph**, where flows
> conserve and weights are shares given by an accounting identity. **It does not
> hold on a claims graph.** A macro model that runs a claims graph through the
> production-graph machinery inherits that.

### 2.3 The obvious reply, and the shorter answer to it

The reply is that the misallocation literature dropped efficiency long ago.
Baqaee and Farhi price wedges and markups explicitly, so prices there are not
marginal products and the frontier reading no longer applies.

**Handling wedges is a different thing from handling non-integrability.** An
economy with wedges still has a well defined allocation and a well defined
comparative static. The claim here is stronger: the field admits no potential, so
"the allocation reached" is not the optimum of any objective, wedged or not.

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
is Theorem 1 condition (1) restricted to the position graph, stated in the setup
rather than derived. The wedges are indexed `τ_ij`, on a pair of goods, which is
an **edge** index. Generality on the edge index does not produce an **agent**
index, and the field measured on this repository's carriers is `w_a(i, j)`,
carrying both.

The rest is a two-branch argument, and both branches are already answered:

| branch | consequence | what answers it |
|---|---|---|
| **keep one producer per node** | the field has no slot for `a`. `w_a(i,j)` lies outside the representable class, whatever `τ` is allowed to be | stage B2's measurement: fix census tract, year, lien position, loan purpose, occupancy and dwelling type, and 78 percent of the variance in financing terms is still **inside** those cells (`0.7831`, `0.8480` under `min_size = 20`). A single price vector on positions predicts zero |
| **split nodes by agent** | the object becomes the position-by-agent product graph | that is exactly `Γ = G □ H`. Theorem 1 applies to it verbatim, with no economic assumptions, and Corollary 1 is decided by one inequality. Theorem 2 splits its cycle space; Theorem 3 identifies what B2 measured as the square component |

**The second branch costs the thing the framework was for.** A sufficient
statistic whose dimension grows with the number of agent classes is not a
compression of the network into weights, which is what Domar aggregation is sold
as being.

### 2.4 What §13.4 of the theorem file adds, and what it takes away

Being exact about this matters more than winning the paragraph.
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
  deleted**, and one autonomous edge restores it to `0.783`.

And in stage A2, under issuance, transaction volume rises `x44.87` while the
support set contracts to `x0.402`, with the production layer falling to `0.51`
percent of all circulation.

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

## 6. Where a critic should push

**Not at Theorem 1.** It is an equivalence with an elementary proof and no
economic assumptions in it, and `b0_claim_scope.md` §5 already names the weak
point of the programme: whether the measured object is the field the claim is
about.

**The push specific to this document** is at §2.3's index argument. It rests on
reading the setups rather than the proofs, so the way to break it is to produce a
formulation in that literature whose sufficient statistic carries an agent index
and whose dimension does not grow with the number of agent classes. If that
exists, the second branch of §2.3's table is answered and the row weakens.

Four questions put that push in executable form, and they are the shape any
extension of this section should take:

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

**Before any of these are quoted in a manuscript, check each against the published
version of record and attach equation numbers.** Working-paper and published
setups differ, and §6's standard applies to this document as much as to anything
it argues with.
