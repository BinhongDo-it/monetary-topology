# B1 theorem: where the obstruction lives, and what B2 actually measured

Companion to [`b1_setup.md`](b1_setup.md), which fixed the field, and
[`b2_measurement.md`](b2_measurement.md), which pre-registered the measurement.
This document is the part between them: it says what object the measurement is a
measurement *of*.

**Status.** Theorems 1 to 3 are proved here and checked in code. Nothing in this
document is empirical; the numbers it refers to were produced before it was
written and are not adjusted by it.

---

## 0. Summary

The results.

**Theorem 1** gives an exact criterion for when a single scalar price vector on
positions exists, on a graph built from positions *and* agent classes together. It
is an equivalence, not an approximation, and it uses no assumption about
equilibrium, smoothness, rationality or market structure.

**Theorem 2** splits the cycle space of that graph into two summands with distinct
economic readings, and shows that the two available empirical carriers reach one
each. They are complements, not substitutes, which was not obvious before.

**Theorem 3** is the one that matters for the repository as it stands. The
within-cell variance reported by stage B2 equals, up to a factor of two, the mean
squared holonomy around the graph's four-cycles. **B2 loop A did not measure a
proxy for a cohomological quantity. It measured the quantity.**

That closes the open question recorded in the README: whether the partition
result was a special case of the cohomological claim or a weaker relative. It is
a special case, and under the assumptions of §8 it carries almost the whole
obstruction.

**Theorem 5**, added 2026-08-27, turns Theorem 1's equivalence into a
measurement. It computes the distance from the field to the nearest single scalar
potential in closed form from the two graphs' spectra, and splits it, with no
cross term, into the common field's own non-integrability plus a quadratic form
in the disagreement between agent classes. **Standard price theory is the zero
set of that second summand rather than a refuted rival**, and the deviation from
it is exactly quadratic rather than order two in a limit. §14.

**Added 2026-08-15.** §13 restates Theorem 1 as the vanishing of a two-way
interaction term. It proves nothing new about the field. What it fixes is which
part of this document standard econometric practice already reaches, and which
part it cannot reach under any specification.

**Load-bearing order, fixed 2026-08-15.** The sentence above calling Theorem 3
"the one that matters for the repository as it stands" is true about *what stage
B2 measured* and is **superseded as a statement of what carries the argument**. It
is left standing because the reasoning that replaced it is worth having beside it.

The order is **Corollary 1, then Corollary 2, then Theorem 3**, and the test that
produces it is what survives a hostile relabeling.

- **Corollary 1** is an existence claim decided by a single inequality, on a
  single edge, for a single pair of classes. Nothing in it can be dissolved by
  renaming, and no quantity of "the deviations are small" reaches it.
- **Corollary 2** is a prediction about **data design**: which body of evidence
  can reach which summand, and which cannot at any sample size. It is falsifiable
  by construction rather than by estimation. §5's scoping block is the evidence
  that it is sharp enough to be worth scoping rather than vague enough to be safe.
- **Theorem 3** is an algebraic identity. Its number equals stage B2's within-cell
  variance to `1e-16`, so a reader who wants to dismiss it can say the framework
  renamed an analysis of variance, and at the level of arithmetic be right.

§13.4 supplies a second reason for the same order, reached from a different
direction and after this one: the summand Theorem 3 quantifies **is** the
interaction term of a saturated two-way model, which standard practice already
estimates. Theorem 3 says *which* quantity stage B2 holds. It does not put a new
one in anyone's hands, and Corollary 2 is what says where a new one would have to
come from.

---

## 1. The problem this document exists to solve

`b1_setup.md` established that on a one-index price vector integrability is a
theorem of notation, and that the field the claim is about must therefore be the
two-index effective cost `P(a, g)`. That fixed the object. It did not say where
the topology enters.

The gap was visible in the code. Stage B2 computes a variance decomposition over a
**partition** of loans into cells. There is no graph in it, no cycle space, no
Hodge decomposition, no Betti number. The pairwise difference between two
borrowers in the same cell was being called a loop sum, but a "loop" of length two
in a set with no edges is not a loop, and calling it one is exactly the kind of
borrowed authority this project is supposed to be arguing against.

So one of two things had to be true, and it mattered which.

Either the partition result is a shadow of a cohomological statement, in which
case the topological language is decoration and should be dropped from the
empirical claim; or it is a genuine instance, in which case it should be possible
to say precisely which cycles, on which graph, with which weights.

It is the second. The construction is in §3 and it is not elaborate.

---

## 2. Notation

`N` is a finite set of **positions**: assets, goods, or states of holding. The
position graph `G = (N, E)` has an edge for each transition an agent might make,
and is assumed connected.

`A` is a finite set of **agent classes**, `|A| = m`, `|N| = n`.

For each `a ∈ A`, the field is an antisymmetric function on edges,

```
w_a(i, j)  =  log of the rate at which class a can convert position i into j
w_a(j, i)  =  −w_a(i, j)
```

`b1_setup.md` §3 fixes this as a return over a holding period, with `T = 1`
recovering the cost formulation exactly. Nothing below depends on which reading is
taken, only on antisymmetry.

A **1-cochain** assigns a number to each oriented edge. The coboundary of a
function `ψ` on nodes is the 1-cochain `d⁰ψ(u, v) = ψ(v) − ψ(u)`. A cochain is
**exact** if it equals `d⁰ψ` for some `ψ`. The content of `d¹ ∘ d⁰ = 0` on a graph
is elementary: a coboundary telescopes, so it sums to zero around every cycle.

The **one-index null** is the assertion that a single `φ: N → ℝ` exists with
`w_a(i, j) = φ(j) − φ(i)` for every agent class and every edge. This is the claim
that terms do not depend on who is transacting.

---

## 3. The enlarged graph

Positions alone are the wrong space. On positions alone, the field is not one
cochain but a family of them indexed by `a`, and "the family disagrees with itself"
is not a statement about any single cochain's exactness.

Put the agent index into the space instead.

**Definition.** `Γ` has vertex set `V(Γ) = A × N` and two kinds of edge.

**Position edges.** `(a, i) → (a, j)` whenever `(i, j) ∈ E`, carrying weight

```
ω((a, i), (a, j))  =  w_a(i, j)
```

Agent `a` moves between positions, at agent `a`'s terms.

**Agent edges.** `(a, g) → (b, g)` for `a ≠ b`, carrying weight

```
ω((a, g), (b, g))  =  0
```

The same position, held by someone else. The weight is zero because the position
has not changed: `g` is `g` regardless of who holds it. §8 is about when that is
true and what happens when it is not.

The graph is a Cartesian product `Γ = G □ H`, where `H` is the agent graph, taken
complete unless stated otherwise. `Γ` is connected whenever `G` and `H` are.

**The four-cycle.** For any edge `(i, j) ∈ E` and any two classes `a, b`:

```
(a, i) ──w_a(i,j)──► (a, j)
  ▲                    │
  │ 0                  │ 0
  │                    ▼
(b, i) ◄──w_b(j,i)── (b, j)

sum  =  w_a(i, j) + 0 − w_b(i, j) + 0  =  w_a(i, j) − w_b(i, j)
```

This is a cycle in a graph and its sum is a holonomy. It is non-zero exactly when
two agent classes face different terms on the same transition. Nothing about it is
metaphorical.

---

## 4. Theorem 1

**Theorem 1.** Let `G` be connected, let every position be transferable, and let
the agent graph `H` be connected. The following are equivalent.

1. **(single price vector)** There exists `φ: N → ℝ` with `w_a(i, j) = φ(j) − φ(i)`
   for every `a ∈ A` and every `(i, j) ∈ E`.
2. **(exactness)** `ω` is exact on `Γ`.
3. **(vanishing holonomy)** Every cycle in `Γ` sums to zero.
4. **(two conditions)** Every `w_a` is exact on `G`, **and** `w_a = w_b` for all
   `a, b ∈ A`.

### Proof

**(2) ⟺ (3).** Standard on a connected graph. If `ω = d⁰ψ` then any cycle
telescopes to zero. Conversely, fix a basepoint `v₀` and set `ψ(v)` to be the sum
of `ω` along any path from `v₀` to `v`. Two paths differ by a cycle, so vanishing
cycle sums make `ψ` well defined, and `ω = d⁰ψ` by construction.

**(3) ⟹ (4).** Two families of cycles.

*Within a slice.* Any cycle `γ` of `G` lifts to the slice `{a} × N`, where its sum
is `Σ_γ w_a`. By (3) this vanishes, for every cycle of `G`, so `w_a` has vanishing
cycle sums on the connected graph `G` and is therefore exact.

*Across slices.* Take the four-cycle of §3 for `(i, j)` and adjacent classes
`a, b`. Its sum is `w_a(i, j) − w_b(i, j)`, which by (3) is zero. For classes not
adjacent in `H`, chain the equality along a path in `H`, which exists because `H`
is connected. Hence `w_a = w_b` for all pairs.

**(4) ⟹ (1).** By (4) all the `w_a` coincide; call the common value `w`. It is
exact, so `w = d⁰φ` for some `φ: N → ℝ`, which is (1).

**(1) ⟹ (2).** Define `ψ(a, g) := φ(g)`. On a position edge,
`d⁰ψ = φ(j) − φ(i) = w_a(i, j) = ω`. On an agent edge,
`d⁰ψ = φ(g) − φ(g) = 0 = ω`. So `ω = d⁰ψ`. ∎

### Corollary 1

**If `w_a(i, j) ≠ w_b(i, j)` for a single edge and a single pair of classes, then
no single price vector on positions exists.**

The proof used no equilibrium concept, no continuity, no rationality assumption
and no claim about market structure. It is a statement about whether a function
with a given property can be written down, and the answer is decided by one
inequality.

This is what makes the claim falsifiable in the direction that matters. A defender
of the one-index representation cannot retreat to "the deviations are small" or
"they wash out in equilibrium" without conceding that `φ` does not exist and that
what remains is an approximation whose error is the thing being measured.

### Condition (4) read as a reduction

Condition (4) is two conditions, and they do not cost the same.

The first, that each `w_a` is exact on `G`, says that within one class the terms
have a potential. The second, that all the `w_a` coincide, says that the potential
does not depend on who is transacting. **Standard price theory assumes both, and
assumes the second one silently**: writing down one price vector for a market is
already the assertion that no index for the transacting party is needed. A
Walrasian price vector, a state price, a stochastic discount factor and a table of
relative prices differ in what they are indexed by and agree in this, so the
condition is not one school's commitment but the shared representational one.

**So (4) is not a rival hypothesis that Theorem 1 refutes. It is the locus on
which the enlarged object coincides with the older one**, and the implication
(4) ⟹ (1) says the coincidence is an identity: where (4) holds the framework does
not merely agree with the single price vector, it returns that vector. That
direction of the proof is one line and was there from the start.

What Theorem 1 does not supply is what happens just off that locus, which is why
§10 records the gap as "it says nothing about magnitude." §14 closes it. In short:
the distance to the nearest single potential splits, with no cross term, into the
common field's own non-integrability plus a quadratic form in the disagreement
between classes, and the second summand vanishes exactly when the disagreement
does rather than merely becoming small. **Condition (4) is that quantity's zero
set, and the quantity is a modulus for it.**

This is worth stating as containment rather than as refutation, and the choice is
not cosmetic. **A containment claim is the stronger of the two**, because it
obliges the enlarged account to be right everywhere the older one is right, by
identity and not by coincidence. It also carries a cost the refutation framing
does not: it can be broken by a single case in which the single price vector is
right and the framework is not. Corollary 5.4 is what rules that case out, and it
rules it out as algebra rather than as luck.

---

## 5. Theorem 2: the cycle space decomposes into slice and square components

**"Half" is not a dimension count.** The two summands below are not of equal
rank and nothing here claims they are. The statement is about *which* component
a given body of data can reach, so the two empirical carriers are complementary
in the sense of Corollary 2 and not in the sense of splitting `b₁(Γ)` evenly.
The section title said "one half" until 2026-08-11; it was replaced because the
shorter phrase invites the dimensional reading.

**Theorem 2.** With `Γ = G □ H` as above, the cycle space of `Γ` is generated by

- **slice cycles**: lifts of cycles of `G` into a single slice `{a} × N`;
- **agent cycles**: lifts of cycles of `H` at a single position `A × {g}`;
- **squares**: the four-cycles `(a,i), (a,j), (b,j), (b,i)` for `(i,j) ∈ E(G)` and
  `(a,b) ∈ E(H)`.

This is the standard generating set for the cycle space of a Cartesian product of
graphs. Because `ω` vanishes identically on every agent edge, the agent cycles
contribute zero regardless of the field. So

```
the obstruction  =  slice part  ⊕  square part
```

and the two summands have different economic content.

| summand | what a non-zero sum means | who could observe it |
|---|---|---|
| **slice cycles** | a *single* agent faces a non-zero loop: arbitrage inside that agent's own opportunity set | requires one agent traversing several positions |
| **squares** | *two* agents face different terms on the same pair of positions | requires many agents observed on one transition |

### Corollary 2: the two carriers are complements

Stage B2 loop A observes many borrowers making the same transition — from not
holding a dwelling in tract `T` in year `Y` to holding it. Many agents, one edge.
**It reaches squares and nothing else.** No amount of mortgage data will produce a
slice cycle, because a mortgage applicant is observed at one transition.

Covered interest parity deviations are the opposite shape. One dealer traverses
spot into a foreign currency, a forward contract back, and the funding leg —
several positions, one agent. **That is a slice cycle**, and it is the only
carrier considered in this project that reaches the first summand.

So the FX measurement is not a second opinion on the mortgage result. It is the
other summand of the cycle space, and the mortgage carrier cannot reach it for
structural reasons rather than for want of a bigger sample.

**Scoped 2026-08-15.** The sentence "No amount of mortgage data will produce a
slice cycle" is true of the carrier stage B2 uses, and the reason given for it is
a property of that carrier's design rather than a property of mortgages. The two
are easy to run together, so they are separated here.

The structural reason is sharper than "an applicant is observed at one
transition". **A cell is one edge (§8, A3), so a cell's position graph has two
vertices and `b₁(G) = 0`, and a graph with no cycles has no slice cycles to
lift.** §13.2 states the same fact from the other side, where it is what makes the
two-way dictionary free on this carrier.

That reason does not extend to every body of mortgage data. A borrower-linked
panel, observing one borrower across purchase, refinance, sale and repurchase, is
one agent walking several positions, which is the shape this table asks for.
**Whether such a walk closes is a separate question and the answer is not
automatic.** On a two-position graph `{rent, own}` an out-and-back walk sums to
zero by antisymmetry and is not a cycle at all. A slice cycle needs `b₁(G) ≥ 1`,
so it needs at least three positions with two distinct routes between some pair:
`rent → own at tier q → own at tier q' → rent`, or a route through two loan
products. `b1_setup.md` §3's tier index is exactly what supplies the extra
positions, and `b1_setup.md` §5 already lists NMDB, which is longitudinal at loan
level, among the sources for the vintage row. **Whether NMDB links a borrower
across successive loans is an availability question and is not settled here.**

The accurate form of the claim is therefore:

> No cross-section of originations reaches the slice summand, because its
> position graph per cell is a single edge. A borrower-linked panel over three or
> more positions is not excluded by this argument.

**Nothing downstream changes.** §9's ordering stands, and covered-parity
deviations remain the one carrier this project holds that is already retrieved and
whose loop provably closes. What the scoping adds is a second candidate for the
slice summand, not a correction to any figure.

The first Betti number of the enlarged graph, for the record:

```
b₁(Γ)  =  |E(Γ)| − |V(Γ)| + 1  =  m·e_G  +  n·e_H  −  m·n  +  1
```

with `e_G = |E(G)|`, `e_H = |E(H)|`. With `H` complete this is
`m·e_G + n·m(m−1)/2 − mn + 1`, dominated by the `n·m²/2` term: the cycle space
grows quadratically in the number of agent classes, and essentially all of that
growth is in squares. Setting `m = 1` returns `e_G − n + 1 = b₁(G)`, the one-index
case, in which every square degenerates and the obstruction is empty. The
one-index world is recovered exactly, which is the check that the construction is
a generalisation rather than a substitution.

---

## 6. Theorem 3: what stage B2 measured

**Theorem 3.** Fix a cell: one edge `(i, j)`, observed for `k` agents with values
`x₁, …, x_k`, where `x_p = w_{a_p}(i, j)`. Define the cell's **mean squared
holonomy** as the average over ordered pairs of the squared square-sum,

```
H  :=  (1/k²) · Σ_{p,q} (x_p − x_q)²
```

Then `H = 2·Var(x)`, with `Var` the population variance.

**Proof.**
`Σ_{p,q} (x_p − x_q)² = Σ_{p,q}(x_p² − 2 x_p x_q + x_q²) = 2k·Σ_p x_p² − 2(Σ_p x_p)²`.
Divide by `k²`:
`2·(Σx²/k) − 2·(Σx/k)² = 2(E[x²] − E[x]²) = 2·Var(x)`. ∎

**Corollary 3.** Aggregating over cells with the weights the decomposition already
uses,

```
within term  =  Σ_c (n_c/n) · Var_c  =  ½ · Σ_c (n_c/n) · H_c
```

so the reported **within share is the fraction of observed variation that is
holonomy rather than potential**, in the `L²` norm, up to the factor of two that
cancels out of a ratio.

**Which component of the non-exact part, stated precisely.** Theorem 3 is about
squares and nothing else: `x_p − x_q` is the sum around the four-cycle of §3, so
what the identity delivers is the squared magnitude of the **square** component.
On a general graph that is weaker than the non-exact part, because the non-exact
part is curl plus harmonic and the two are not the same object. **Here they
coincide, and the reason is proved rather than assumed:** §12 shows that filling
the squares of `Γ` leaves `H¹(Γ) ≅ H¹(G) ⊕ H¹(H)`, that agent cycles vanish for
every field by Theorem 2, and that slice cycles vanish in every field this
project runs. The harmonic component is therefore identically zero and non-exact
reduces to square. A reader who has not yet reached §12 should treat the phrase
"non-exact part" below as shorthand licensed there, and a reader building a
carrier where slice cycles do **not** vanish must drop the shorthand, because the
identity will then be measuring one summand of two. §11.1 is the algebraic check
that the two summands separate when slice is genuinely non-zero.

Stage B2's headline figures — `0.7831` over all cells, `0.8480` over cells of at
least twenty loans, `0.7654` and `0.8181` in the rank-transformed version that
excludes nothing — are therefore cohomological quantities and not proxies for
them. The identity is checked numerically per cell and in aggregate; it holds to
`1e-16`, which is what an algebraic identity should do.

### Why this was worth proving rather than assuming

Before Theorem 3, the honest description of stage B2 was "an analysis of variance
on mortgage rates, which we believe is related to a topological claim." That
description is worth very little: conditional dispersion in mortgage pricing is
already documented, and a framework that merely re-derives it has added a
vocabulary rather than a result.

After Theorem 3 the description is "the `L²` norm of the square component of a
1-cochain on a 28-million-vertex graph, measured against the null that the
cochain is exact", which by the paragraph above and §12 is the whole non-exact
part on this carrier. Same number, different object, and only the second one is
a claim the framework can be judged on.

The direction of the inference matters too. The theorem was not fitted to the
result. The measurement was pre-registered and executed first, the identity is
algebraic and could not have come out otherwise, and had the within share been
zero the same identity would have said the field was exact on the squares.

---

## 7. The two questions, separated

Theorem 2 makes precise a distinction that ordinary price theory does not draw,
and the separation is worth stating on its own because the two are usually run
together under "prices differ."

**Per-agent integrability.** Does a *single* agent face a consistent price system?
If `w_a` is exact for each `a`, then each agent has a private potential `φ_a`, and
that agent faces no arbitrage. This is presumably close to true: an agent who
faced a non-zero loop in their own opportunity set would trade it until it closed.

**Global integrability.** Is there *one* `φ` for everyone? This is the one-index
null, and it is what fails.

A field can be a family of gradients without being a gradient. Every `w_a` exact,
`φ_a ≠ φ_b`: no agent sees an inconsistency, every agent's own accounts balance,
and yet no scalar on positions reproduces the economy. The obstruction is not
visible from inside any single agent's position and is only visible in the
comparison across agents, which is exactly the square.

That is the framework's claim stated in its sharpest available form, and it is
also why the claim is easy to miss. Anyone checking integrability one agent at a
time will find none.

---

## 8. Assumptions, and the two places they fail

The theorem is exact. Its application is not, and the load is carried by one
assumption.

### A1. Agent edges carry weight zero

This requires the position to trade at a single price independent of who holds
it. It is where all the economics is.

**Where it holds: the dwelling.** A house sells at one market price. Two buyers in
the same tract in the same year are bidding on the same object; what differs is
the terms on which each can finance the purchase, and financing sits on the
position edge, not on the agent edge. This is the case stage B2 measures, and A1 is
defensible there.

**Where it fails: the mortgage contract.** A 3% mortgage originated in 2021 cannot
be transferred to another borrower — conventional loans are not assumable. The
agent edge does not exist. `Γ` disconnects in the agent direction, the square is
not a cycle, and Theorem 1 does not apply.

This is not a gap in the theory; it is the same fact `b1_setup.md` recorded from
the other side. Loop B, the vintage loop, argues from the **hole** rather than from
the holonomy: integrability on a space one cannot move around in is vacuous, and
the disconnection is itself the finding. Theorem 1 explains why loop B needs a
different argument, which the setup document asserted but could not derive.

**Robustness when A1 is merely approximate.** If agent edges carry weight `t ≠ 0`
— transaction costs, transfer frictions — the square sum becomes

```
w_a(i,j) − w_b(i,j)  +  t_{ab}(j) − t_{ab}(i)
```

A non-zero measured sum still proves `ω` is not exact, so **Corollary 1 survives
untouched**. What does not survive is attribution: the sum can no longer be
assigned to price differences rather than to transfer wedges without a separate
argument. The existence claim is robust; the interpretation is not.

### A2. Connectivity

`G` connected and `H` connected. If `H` is disconnected, `w_a = w_b` follows only
within a component, and Theorem 1 gives a price vector per component rather than
one globally — which is a weaker and still informative conclusion.

### A3. A cell is one edge

`x₁, …, x_k` must be values of the *same* `w_a(i, j)` for different `a`. If the
cell pools distinct edges, `H_c` inflates for a reason that has nothing to do with
the agent index. This is what the cell keys are for, and it is already the subject
of a pre-registered falsification in `b2_measurement.md` §8: if the dispersion is
accounted for by loan characteristics that are themselves positions, the position
space was not held fixed and the cell definition must be tightened.

---

## 9. What this decides about the next carrier

Before Theorem 3 it was an open question whether stage B2 had exercised the
framework's actual machinery at all, and a second carrier looked mandatory on
those grounds. It is not.

**FX is not required to make the empirical claim cohomological.** The mortgage
result already is, by Theorem 3.

**FX is required to reach the other summand.** By Corollary 2, mortgage data
cannot produce a slice cycle no matter how large the sample, and CIP deviations
are the available carrier that can. Whether the slice part is non-zero is a
separate empirical question from whether the square part is, and answering the
second does not answer the first.

This also disciplines what an FX measurement would have to be. It must be a loop
traversed by **one** agent through several positions. Carry returns are not that:
they are compensation for bearing risk, not a closed loop with a non-zero sum, and
treating them as an obstruction is a category error the project made once already
on paper. Covered parity deviations are the right object because the loop closes.

**Ordering.** Loop B costs no new retrieval — FHFA's published vintage shares are
aggregates — and it completes the disconnection side of the argument, which
Theorem 1 has just shown to be a structurally different claim rather than a weaker
version of the same one. It should go before FX for that reason and not merely
because it is cheaper.

### 9.1 A square that was not arbitraged, observed where arbitrage is sharpest

**Added 2026-08-28.** Corollary 2's claim that squares are not arbitrage is a
derivation from A1: a square needs two agents, and no single agent traverses it.
This subsection records an observation that bears on it. It was found while
checking documents for an unrelated candidate carrier, and it cost three lookups.

Irish-domiciled UCITS funds receive US dividends at `15%` under the US-Ireland
treaty. Luxembourg-domiciled funds do not qualify and receive them at the `30%`
statutory rate. Two wrappers, one underlying basket, terms differing by fifteen
percentage points of the dividend yield, about `30` basis points a year on the
S&P 500 at a `2%` yield. **That is a square: two holders of one position, on
different terms, at one transition.**

The venue is the one `b3_slice_availability.md` §7 names as the only place where
the objection *give the market time and arbitrage grinds any non-integrability
away* can be answered at all: deepest liquidity, most transparent information,
most professional participants, and decades already given.

**The differential was not priced away. The disadvantaged wrapper was withdrawn.**
On US indices the Luxembourg products are swap-replicating, which takes the rate
to zero under the section `871(m)` qualified-index exception, and a 2026 survey of
S&P 500 UCITS ETFs lists Irish vehicles only.

**The reason is structural, which is what makes this more than an anecdote.** A
fund's market price is pinned to its net asset value by the creation and
redemption mechanism. A wrapper carrying worse terms therefore cannot trade at a
persistent discount that would compensate its buyer: the pin forces the buyer to
pay net asset value for a worse stream. The only margin left is quantity, on both
sides, which is not to buy it and not to offer it.

> **The mechanism that arbitrages the slice direction flat is the same mechanism
> that keeps the square from being priced at all.**

**This pairs with B9 on the same wrapper mechanism, and the pair is the point.**
B9 measured the premium, which is the slice-direction object on an exchange-traded
fund, and found it arbitraged to the width of its own cost floor. The domicile
differential is the square on the same kind of wrapper, and it was not arbitraged
at all. **One wrapper family, both summands, opposite answers**, which is what
Theorem 2 says should happen and is not something either summand could have shown
on its own.

**The route a reader will propose first, and why it is not a counterexample.**
The differential can be reached by holding one wrapper long and the other short.
**That is not a cycle, it is a carry held open**, and §9 above already rules that
carry returns are compensation for bearing a constraint rather than a closed loop
with a non-zero sum. The round trip that **is** a cycle, sell one wrapper and buy
the other and then reverse, costs two spreads and captures nothing, because the
differential accrues over time and does not sit in the switch. Both directions of
that edge exist, so by `b4_directed_edges.md` §5.2 this is `H¹` with friction and
not an `H⁰` reachability statement.

**The carry's own friction is unobservable, and that is the sharper point.**
`b4_directed_edges.md` §5 gives the reportable pair as `S − S'` beside `S + S'`,
and Theorem 6(4) there bounds the first by the second, so the quantity a stage
should register is `rho = |S − S'| / −(S + S')`. **On this carrier the numerator
is known exactly and without estimation**: fifteen percentage points of the
dividend yield, fixed by treaty, no sampling and no model. **The denominator is
not available at all.** The friction on the short leg is the borrow fee, whose
class structure is set in a private bilateral contract; `FINRA Rule 6540(d)`
withholds the counterparty identifiers that would label it and disseminates only
an unlabelled rate distribution.

> **This carrier exhibits a square whose index part is exactly known and whose
> friction part is unobservable by construction. `rho` cannot be formed on it.**

**That is a boundary condition on the empirical programme rather than a defect of
this example**, and it splits cleanly across the two pre-retrieval questions:
`D30` asks whether the class differential lands on two prices that no single agent
can move between cheaply, and it decides whether **`S − S'`** is observable;
`D29` asks whether the differential is written in a document anyone can obtain,
and it decides whether **`S + S'`** is observable. **`rho` needs both, and this
carrier passes the first and fails the second.**

**What this is and is not.** It is evidence that no arbitrage channel exists on
this square, and the evidence is carried by the absence of a product rather than
by a price. **It is not a measurement of the square**, no figure from it enters
any criterion, and nothing downstream cites it as one. The rate is statutory and
the withdrawal is a fact about a product catalogue; neither is estimated here.

**Two neighbouring class differentials found in the same check, both statutory and
exactly known, neither reaching any price at all**: substitute dividend payments
in a securities loan, sourced as the underlying dividend under
`Treas. Reg. §1.861-3(a)(6)` and withheld at the lender's treaty rate; and the
initial margin a position occupies under `Regulation T` against `FINRA Rule
4210(g)` portfolio margin. In both, the two classes hold one instrument at one
price, so the differential lives entirely outside the price system. **These are
concrete instances of the coordinate that §1 says the price vector does not
carry**, and they require no estimation to exhibit.

---

## 10. What the theorem does not say

**It does not show the field is non-integrable.** It gives an exact criterion and
identifies the measurement that decides. The deciding was done in stage B2, and it
could have gone the other way.

**It says nothing about magnitude.** `b₁(Γ)` is large, but a large cycle space is
room for an obstruction, not an obstruction. How much of the field is non-exact is
the empirical question, and the answer is stage B2's within share, not anything in
this document. **Superseded in part on 2026-08-27**: §14 computes the distance
from the field to the nearest single potential in closed form. It still says
nothing about how large that distance is on any actual market, which remains
stage B2's answer to give, but the sentence above no longer means the framework
has no quantity here.

**It carries no welfare content.** That no scalar on positions reproduces the terms
different agents face is a statement about representations. It does not by itself
say anyone behaves badly, that markets fail to clear, or that an alternative
allocation would be better. Every such step is separate and none is taken here.

**The Hodge decomposition in `topology.py` is the wrong complex for `Γ`.** That
implementation builds 2-cells from triangles, which is right for the clique complex
used in stage A2c. The natural 2-cells of a Cartesian product are **squares**, and
the four-cycles of §3 are squares. Building the square complex on `Γ` would not
deliver a finer split, and §12 gives two independent reasons: the harmonic
component is identically zero on every field this project runs, and Theorem 3's
quantity lives on the 1-skeleton, so it is invariant under every choice of `C₂`.
The squares are load-bearing in exactly one place: the hole taxonomy of
`b1_setup.md` §5, which separates a puncture from a disconnection, and
`experiments/b1_holes.py` is what gives that claim its source.

---

## 11. What is checked in code

Theorems are not evidence about their own implementations. The following are
executable, in `experiments/b1_theorem.py` and the tests beside it.

| claim | check |
|---|---|
| Theorem 1, (1) ⟹ (3) | build `Γ` from a random exact field; every cycle sum is zero to `1e-12` |
| Theorem 1, (3) ⟹ (1) | perturb one `w_a` on one edge; recover `φ` iff no square is non-zero |
| Theorem 1, (2) ⟺ (3) | reconstruct `ψ` by path integral and confirm `d⁰ψ = ω` |
| Theorem 2, generating set | rank of the square-and-slice cycle matrix equals `b₁(Γ)` |
| Theorem 2, `b₁` formula | `m·e_G + n·e_H − mn + 1` against `E − V + C` computed directly |
| Theorem 3, identity | per cell and aggregate, on the real HMDA sample, against stage B2's own within term |
| strict generalisation | `m = 1` collapses `Γ` to `G`, every square degenerates, and `b₁(Γ) = b₁(G)` exactly |
| Theorem 2, slice summand | a shared but non-exact field: slice sums fire, every square sum is exactly zero |
| Theorem 2, separation | on a mixture of the two, each summand's cycle sums come back byte-identical |

The strict-generalisation row is the same discipline applied throughout the
repository: a generalisation that does not reproduce the special case bitwise is
not a generalisation. The last two rows are the subject of §11.1.

### 11.1 The slice summand, on a field where it is not zero

**Added 2026-08-11, after a review asked for a numerical verification of the
decomposition.** The check it asked for had already been run and is in §12; what
that run could not do is the point of this section.

**The gap.** Every field this repository constructs makes the slice summand
vanish *by construction*. `exact_field` and `per_agent_exact_field` both make
each `w_a` exact on `G`, so every slice cycle sums to zero as an identity, and
stage A3's carrier is a star, where there are no slice cycles at all. §12
measures slice sums at `2.22e-16` and reports it, but that number confirms the
constructor, not the theorem: a summand that is zero because nothing was ever put
in it has not been separated from anything. **So Theorem 2's split was checked on
its square half and asserted on its slice half**, and B1-2 is the check on the
square half alone: it fires the squares and watches the slice cycles stay silent.

**What was added.** `product_graph.shared_field` gives every class the *same*
field without requiring that field to be a gradient on `G`. It is the exact
complement of `per_agent_exact_field`: there the classes each have a potential
and the potentials differ, here the classes agree and there is no potential.
`product_graph.slice_cycles` lifts a fundamental cycle basis of `G` into each
slice, in the same closed-walk form `squares` already returns.

**B1-8, the mirror of B1-2.** On a shared non-exact field the slice cycles reach
`15.0` while **every square sum is exactly `0.0`**, across the five shapes with
more than one class and a non-trivial cycle basis. Exactly zero rather than
small: a square sum is `w_a(i, j) − w_b(i, j)` and the two legs are now the same
number, so this is subtraction and not cancellation.

**B1-9, the separation itself.** Add a pure-slice field to a pure-square one and
sum around both families again. Cycle sums are linear in the field and each part
is silent on the other's cycles, so each summand must come back out of the
mixture unchanged. It does, **compared as raw bytes**, which is claimable because
the fields are integer-valued and the sums are therefore exact in float64. This
is the same device as `b4`'s B4-6 and it is used for the same reason: a
decomposition that only nearly separates is a tolerance argument, and the
arithmetic here does not need one.

**What this does and does not license.** It closes a gap in the *checking* of
Theorem 2 and changes no empirical figure. Corollary 2 still says the mortgage
carrier reaches squares and nothing else, §12 still says the harmonic component
is identically zero on every field this project runs, and the slice summand is
still empirically untouched until a carrier reaches it. What it removes is the
answer "the split has never been exercised on a case where both parts are
present", which was true until now and is the first thing a reader should have
asked.

---

## 12. Correction to §10: the square complex would not unlock anything

**Added 2026-08-10, after a review that was about to build it.**

§10 records that `topology.py` builds 2-cells from triangles and that the natural
2-cells of a Cartesian product are squares. It is tempting to conclude that a
curl-versus-harmonic split on `Γ` therefore awaits a square complex, and that
building one would deliver the finer split. **It would not.**
The answer is fixed before the code runs, for two independent reasons that are
already in this document.

Filling the squares leaves `H¹(Γ) ≅ H¹(G) ⊕ H¹(H)`, so the harmonic component is
the cochain's projection onto the slice and agent cycles of §5. Both vanish:

- **Agent cycles: identically zero.** Theorem 2 states it — `ω` vanishes on
  every agent edge, so agent cycles contribute nothing *regardless of the
  field*. `cochain_from_field` writes the zeros.
- **Slice cycles: zero in every field this project runs.** `exact_field` and
  `per_agent_exact_field` both make each `w_a` exact on `G` by construction, so
  every slice cycle sums to zero. And on stage A3's carrier the question does not
  arise at all: `tier_positions` is a **star**, a tree, `b₁(G) = 0`, so there are
  no slice cycles to sum over.

Measured, rather than argued: on the A3 star with four agent classes, squares
reach `2.668` while slice sums do not exist and agent sums are exactly `0`. On a
four-node `G` with `b₁(G) = 2` and three agent classes, squares reach `2.760`,
slice sums are `2.22e-16` and agent sums are exactly `0`.

**Those slice sums are zero because the constructor made them zero, and §11.1 is
the case where they are not.** The paragraph above is about the fields this
project runs, and on those fields the harmonic component really is identically
zero, which is what withdraws the square complex. It is not a statement that the
slice summand is always empty, and B1-8 fires it deliberately so that the
distinction is on the record rather than resting on which fields happened to be
constructed.

**So a curl-versus-harmonic decomposition on `Γ` would report curl `100%`,
harmonic `0%`, always.** It is an identity dressed as a measurement — the same
error this project caught in stage A3's criterion A3-3 — and it is not worth
building. A queued proposal to build the cube complex on `Γ` in order to unlock a
curl-versus-harmonic refinement is withdrawn on those grounds.

**The substantive decomposition is not curl against harmonic. It is §5's slice
against square**, and that split is not a refinement waiting on a complex: it is
already stated, already proved, and already tells you which carrier reaches
which half. Corollary 2 is the operative statement, and it says the mortgage data
reaches squares and nothing else, no matter how large the sample.

### 12.1 And a wrong turn worth recording

The same review proposed, before doing this check, that the holes of Volume II §2
"live in the agent edges", and that the directed-agent-edge theorem should
therefore be promoted ahead of everything else. **That is wrong and the error is
worth naming**, because it is the one `b2_loop_b.md` §10 warns about in its last
line.

Where the agent edge fails — the non-assumable mortgage — the edge **does not
exist**. `Γ` disconnects in the agent direction, the square is not a cycle, and
Theorem 1 does not apply. That is `H⁰`, and loop B is the argument for it. It is
not a harmonic `H¹` class and calling it one would be handing a reader a number
about `H⁰` while telling a story about `H¹`.

**The genuinely untouched summand is the slice part**, and by Corollary 2 no
volume of mortgage data can reach it. §9's ordering already says what comes next
and why, and it is better than the reordering this review proposed: loop B first
because it completes the disconnection side, then covered-parity deviations
because they are the one available carrier whose loop is traversed by a single
agent through several positions.

### 12.2 A shorter reason, which does not depend on which fields were run

**Added 2026-08-15.** §12's argument is that filling the squares would report
curl `100%` and harmonic `0%`, so the split is an identity dressed as a
measurement. That argument is correct and it is **scoped**: it holds for the
fields this project has constructed, and §11.1 and `b1_setup.md` §6 both had to
add that scope explicitly. A second argument reaches the same withdrawal for
stage B2's figure and carries no scope condition at all.

**Theorem 3's quantity contains no 2-cells.** `x_p − x_q` is the sum of `ω`
around a closed walk in the **1-skeleton** of `Γ`, and the within share is a
function of `(Γ's 1-skeleton, ω)` alone. **It is invariant under every choice of
`C₂`.** So the question "should the squares be filled" cannot move the number it
would be reporting about, whichever way it is answered.

What the choice does move is the **classification** of that number, and both
readings are available:

| choice of `C₂` | what a non-zero square sum says about `ω` |
|---|---|
| `C₂ = 0` | there is no `d¹`, so `Z¹ = C¹` and every 1-cochain is closed. A non-zero square sum puts `[ω] ≠ 0` in `H¹(Γ)`, and `dim H¹ = b₁(Γ)` |
| squares filled | `d¹ω(Q) = ⟨ω, ∂₂Q⟩` is the square sum, so `ω` is **not closed**. It has a curl and defines no `H¹` class at all |

**Corollary 1 is untouched by either**, because it uses only that a cycle of the
1-skeleton has a non-zero sum, and the 1-skeleton is the same object under both
choices. A reader who wants to fill and a reader who does not will report the same
`0.7831`.

Two things follow.

**The withdrawal in §12 gains a second and stronger reason.** The first is that
the split would be an identity, which is scoped to the fields run. The second is
that the split cannot change the quantity it would be splitting, which is scoped
to nothing.

**Where `C₂` does matter is the hole taxonomy, and that is the only place.**
`b1_setup.md` §5's distinction between a **puncture** (`dim H¹` rises because
`rank ∂₂` falls faster than `b₁`) and a **disconnection** (`c` rises, `b₁` fixed)
is a statement about the filled complex, and it has no counterpart on the bare
graph, where deleting an edge only lowers `dim H¹ = b₁`. So the squares are
load-bearing in exactly one place in this repository, that claim depends on them,
and `experiments/b1_holes.py` is what has to exist for it to have a source.

---

## 13. The same statement in two-way form

**Added 2026-08-15.** Nothing in this section changes a number, a criterion or a
claim. It gives the results above a second name, and the second name is the one a
reader trained in econometrics already has.

### 13.1 The dictionary

Suppose `w_a` is exact on `G`, so that a potential `P(a, ·)` exists with

```
w_a(i, j)  =  P(a, j) − P(a, i)
```

`P(a, g)` is the two-index effective cost that `b1_setup.md` §2 fixes as the
object. Substituting into the square sum of §3,

```
h_ab^ij  =  w_a(i,j) − w_b(i,j)  =  P(a,j) − P(a,i) − P(b,j) + P(b,i)
         =  Δ_a Δ_g P
```

**The square holonomy is a discrete mixed second difference.** It is the estimand
of a difference-in-differences comparison, with the agent index in place of
treatment and the position index in place of time.

### 13.2 The precondition, and where it is free

The substitution needs `P(a, ·)` to exist, which is exactly "`w_a` is exact on
`G`", which is §7's per-agent integrability and the first half of Theorem 1
condition (4). **It is not free in general and the dictionary must not be used
without checking it.**

**It is free on stage B2's carrier.** A cell is one edge (§8, A3); the position
graph of a cell has two vertices and one edge, `b₁ = 0`, and every 1-cochain on a
tree is exact. So `P(a, ·)` exists cell by cell for structural reasons, and the
dictionary applies to stage B2 unconditionally rather than as an assumption.

**It is not free on stage B3's carrier**, where `b₁(G) = C ≥ 1` by construction
([`b3_cip_slice.md`](b3_cip_slice.md) §2). §13.5 reports what happened when it
was measured there.

### 13.3 Theorem 4

**Theorem 4.** Let `G` be connected and let every `w_a` be exact on `G`, with
potential `P(a, ·)`. The following are equivalent.

1. **Theorem 1 condition (4).**
2. **(additive separability)** `P(a, g) = A(a) + φ(g)` for some `A: A → ℝ` and
   `φ: N → ℝ`.
3. **(no interaction)** `Δ_a Δ_g P = 0` for every pair of classes and every edge.

### Proof

**(2) ⟹ (1).** `w_a(i,j) = φ(j) − φ(i)`, which is independent of `a` and is
exact with potential `φ`.

**(1) ⟹ (3).** Condition (4) gives `w_a = w_b`, so the square sum
`w_a(i,j) − w_b(i,j)` vanishes on every edge and every pair.

**(3) ⟹ (2).** (3) says `P(a,j) − P(b,j) = P(a,i) − P(b,i)` on every edge, so
`D_ab(g) := P(a,g) − P(b,g)` takes the same value at both ends of every edge and
is therefore constant on `G`, which is connected. Fix a class `a₀`, put
`φ(g) := P(a₀, g)` and `A(a) := D_{a a₀}`. Then `P(a,g) = A(a) + φ(g)`. ∎

### Corollary 4

**A single non-zero interaction term is enough.** Write the field saturated,

```
P(a, g)  =  A(a)  +  φ(g)  +  γ_ag
```

If `γ` is non-zero anywhere then no single price vector on positions exists.

Corollary 1 and Corollary 4 are the same statement. Corollary 1 is the form that
says what cannot be written down; Corollary 4 is the form that says which
coefficient decides it.

### 13.4 What this says about Theorem 2's two summands

The dictionary gives §5's split a second reading, and it is the sharper of the
two, because it names what standard practice can and cannot reach.

| summand | in two-way form | reachable by a two-way model |
|---|---|---|
| **square** | the interaction term `γ_ag` | **yes.** A saturated specification estimates it |
| **slice** | `P(a, ·)` does not exist: the agent's own field has no potential | **no**, under any specification, because the dependent variable is undefined |

Two consequences. Neither changes a figure.

**Stage B2 measured an interaction term.** By §13.2 the dictionary holds
unconditionally on that carrier, so the within share is the `L²` norm of `γ`. A
saturated two-way model on the same cells reaches the same object. What Theorem 3
adds there is not a quantity out of reach; it is the account of which quantity it
is and which cycles it sums over. **That is worth saying plainly rather than
leaving a reader to find it**, and it is why Corollary 2's structural statement
carries as much weight here as Theorem 3's identity.

**The non-substitutable content is in the other summand and in `H⁰`.** A field
with no potential per agent has no slot in a two-way model of any order, because
writing `P(a, g)` at all presumes the potential. A missing agent edge (§8 A1,
§12.1) is likewise not a coefficient of any sign; it is the absence of the
comparison a coefficient would be about. These are the two places where the
framework reaches something a specification search cannot arrive at, and §9's
ordering already puts them first.

### 13.5 The precondition is no longer a conjecture

§7 records per-agent integrability as presumably close to true, on the reasoning
that an agent facing a non-zero loop in its own opportunity set would trade until
it closed. **Stage B3 is the measurement of that sentence.**

Cross-currency cycles in G10, which never touch the Treasury and are traversed by
one dealer through several positions, run at `30.9` to `45.6` basis points against
a measurement floor of `2.8` to `3.7`, on nine of nine tenors across eighteen
years ([`b3_cip_slice.md`](b3_cip_slice.md) §11.1). The loop does not close.

§7 stands as written. It says *presumably*, and a measurement is what a
*presumably* is for. What follows here is only that the second row of §13.4's
table is occupied rather than hypothetical: on the one carrier where the question
has been put, `P(a, ·)` does not exist.

### 13.6 Precedent

The entries on this document's review list are mathematical. These two are the
economic ones, and they are the reason this section exists.

| object here | the standing name |
|---|---|
| Theorem 1 condition (4); Theorem 4 (2) | additive separability of a two-index field, and the no-interaction restriction. Tested in the flexible-functional-form literature, Christensen–Jorgenson–Lau (1973) and after |
| the square sum `Δ_a Δ_g P` | the discrete mixed second difference; the difference-in-differences estimand |

### 13.7 What this section does not do

**It does not weaken Theorem 3.** The identity is unchanged and so are stage B2's
figures. A translation cannot move a number.

**It does not license the dictionary outside §13.2's condition.** Where `w_a` is
not exact, `P(a, ·)` does not exist, the four-term expression is not available,
and the square sum survives only as what §3 already defines it to be: the sum of
`ω` around a four-cycle of `Γ`.

**It does not decide whether the interaction has structure.** `γ ≠ 0` is Corollary
4 and is settled. Whether `γ` is one-dimensional, so that a single scalar per
agent class reproduces it, is a separate question with a separate answer set, and
it is registered in [`b7_interaction_rank.md`](b7_interaction_rank.md) rather than
here.

---

## 14. Theorem 5: the reduction, and its error term in closed form

**Added 2026-08-27.** §10 records that Theorem 1 "says nothing about magnitude."
This section says the magnitude.

### 14.1 The gap this closes

Corollary 1 decides existence with one inequality on one edge. A reader can grant
it entirely and still answer: `φ` does not exist, the deviations are small, the
one-index picture is a good approximation, and the enlarged graph is a footnote to
it. Theorem 1 has nothing to say back. It is an equivalence, and equivalences do
not carry rates.

The relation to establish instead is **containment**: the older account is
recovered exactly on a locus of the parameter space, and the deviation off that
locus is a quantity the enlarged object computes rather than an unmodelled
residual. That is the sense in which Newtonian mechanics sits inside relativity,
and it is a stronger claim than refutation, because it obliges the enlarged
account to be right everywhere the older one is right, by identity and not by
coincidence.

Everything below is on the 1-skeleton of `Γ` and uses no 2-cells, so §10's
objection about which complex `topology.py` builds, and §12's correction to it,
leave this section alone.

### 14.2 Statement

Write `ρ(ω)² := dist(ω, im d⁰)² = min_ψ ‖ω − d⁰ψ‖²`, the squared distance from
the field to the nearest single scalar potential on `Γ`. Theorem 1 says
`ρ(ω) = 0` iff condition (4) holds. This section computes `ρ(ω)²` when it does
not.

Let `L_G`, `L_H` be the graph Laplacians, with spectra
`0 = λ_0 < λ_1 ≤ … ≤ λ_{n−1}` and `0 = μ_0 < μ_1 ≤ … ≤ μ_{m−1}` (both zeros
simple, since both graphs are connected by §8's A2). Let `v_λ` be an orthonormal
eigenbasis for `L_G` and `χ_k` one for `L_H`, with `χ_0 = m^{−1/2}·1`. Define the
**mode transform** of the family `{w_a}`,

```
ŵ_k  :=  Σ_a χ_k(a) · w_a        ∈ C¹(G),        so  ŵ_0 = √m · w̄
```

where `w̄` is the mean field. Write `δ_G` for the adjoint of `d⁰` on `G`.

**Theorem 5.**

```
ρ(ω)²  =  Σ_a ‖w_a‖²  −  Σ_{k=0}^{m−1}  Σ_{λ>0}  ⟨v_λ, δ_G ŵ_k⟩² / (λ + μ_k)
```

**Proof.** Three facts, none of them deep, and the whole content is that they
combine in one basis.

*The divergence never sees an agent edge.* `ω` is zero on agent edges by A1, so
the divergence of `ω` at `(a, i)` is the position-divergence of `w_a` at `i`
alone. Transforming in the `χ` basis, `(δ_Γ ω)_k = δ_G ŵ_k`.

*The normal operator factors.* `Γ = G □ H` is a Cartesian product, so
`L_Γ = L_G ⊗ I_m + I_n ⊗ L_H`. Its eigenvectors are `v_λ ⊗ χ_k` with eigenvalues
`λ + μ_k`.

*Least squares.* `ρ(ω)² = ‖ω‖² − ⟨δ_Γ ω, L_Γ⁺ δ_Γ ω⟩`. Expand both arguments in
the product basis. `‖ω‖² = Σ_a ‖w_a‖²` because the agent edges contribute nothing.
The terms with `λ = 0` are dropped without loss: their numerator is
`⟨1_n, δ_G ŵ_k⟩ = 0`, since the image of a divergence is orthogonal to constants.
∎

### Corollary 5.1: the split has no cross term

For `k ≠ 0`, `Σ_a χ_k(a) = 0`, so `ŵ_k = Σ_a χ_k(a) · u_a` with `u_a := w_a − w̄`.
The `k = 0` term involves `w̄` and nothing else. Hence

```
ρ(ω)²  =  m · dist(w̄, im d_G)²  +  R,        R := Σ_{k≠0} term_k
```

where the first summand is a function of the common field alone and `R` is a
positive semidefinite quadratic form in the deviations alone.

**So the reduction is not asymptotic.** There is no first-order term to bound and
no limit to take. Homogeneity is a locus, not a limit point, and the error
incurred on leaving it is *exactly* quadratic in the heterogeneity rather than
order two in some `ε → 0`.

### Corollary 5.2: what damps each mode

Splitting `ŵ_k` on `G` into its exact and co-closed parts,

```
term_k  =  ‖ŵ_k^⊥‖²  +  Σ_{λ>0} c_λ(k) · μ_k / (λ + μ_k),
c_λ(k)  :=  ⟨v_λ, δ_G ŵ_k⟩² / λ
```

Read the fraction. The exact part of every non-constant agent mode is absorbed
into a potential only up to `λ / (λ + μ_k)`; the remainder stands in the residual.
The two ends are the two economies:

- **`μ_k → 0`** — the agent graph falls apart, classes cannot be compared. Every
  mode is absorbed as freely as the common one and `ρ² → Σ_a dist(w_a, im d_G)²`:
  `m` independent one-index theories, one per class, with nothing between them to
  violate. This is the correct answer, and it is a check on the formula rather
  than an assumption fed into it.
- **`μ_k → ∞`** — classes are perfectly comparable. Nothing is absorbed and
  `R → D² := Σ_a ‖u_a‖²`. The whole disagreement stands.

**The damping parameter is the agent graph's spectrum and the damped quantity is
the price theory's own potential.** That is the sentence this section exists to
produce.

### Corollary 5.3: both ends of `R` are spectral

```
ρ_H · D²  ≤  R  ≤  D²,        ρ_H := μ_1 / (λ_max(L_G) + μ_1)
```

Neither bound involves a price. The two graphs fix the exchange rate between
measured non-integrability and class heterogeneity before any field is chosen.

### Corollary 5.4: standard price theory is the zero set, and nothing hides in it

`H` connected gives `μ_1 > 0`, hence `ρ_H > 0`, hence `R = 0` iff `D = 0`. There
is no configuration in which the classes disagree and the residual fails to see
it. With Corollary 5.1,

```
ρ(ω)² = 0   ⟺   all w_a equal, and that common field exact   ( = Theorem 1 (4) )
```

so `ρ` is a modulus for Theorem 1's condition (4): it vanishes exactly there, and
off it, it is bounded away from zero by two graph spectra.

**This is the containment statement.** The single-price account is the locus
`D = 0` with the common field's `H¹(G)` component zero. On that locus the enlarged
object does not merely agree with it, it *is* it, by (4) ⟹ (1) of Theorem 1. Off
it, the enlarged object returns a number and the single-price account returns
zero, and Corollary 5.3 says how far apart those are.

### 14.3 What this licenses, and what it does not

**Licensed.**

1. The containment claim itself, in the reduction sense: wherever a single scalar
   price vector is the right description, the framework's own prediction is that
   vector. It is not a rival account that happens to agree there.
2. A measured residual is a **lower bound on class heterogeneity**:
   `D² ≥ R = ρ(ω)² − m · dist(w̄, im d_G)²`, and both terms on the right are
   computable from the same data a carrier already supplies. No competing account
   produces this quantity, because none of them has an object for it to be a norm
   on.
3. "The deviations are small" now has a scale attached. Small compared to what,
   and the answer is `D²` weighed against `ρ_H`, which the two graphs decide.
4. **The zero set is not hypothetical and has been measured.** Stage B13, recorded
   in `RESULTS.md`, reads this quantity on live exchange quotes for eight position
   edges of one instrument family on one day. After removing the states where the
   tick lattice makes zero arithmetically unavailable, one edge returns exactly
   zero in **716 states of 716**, while two others return zero in **4.5 and 8.2
   per cent** of their states with residuals that are **97.5 and 98.9 per cent
   one-signed**. Corollary 5.4 is what entitles the framework to the exactness:
   `R = 0` iff `D = 0`, with no tolerance band anywhere in the statement. An
   account in which prices are scalar up to small frictions predicts a small
   number and cannot produce 716 of 716 bit for bit; an account in which the gap
   is queueing noise cannot produce a residual that is one-signed 98.9 per cent
   of the time.

**Not licensed.**

- Nothing here says `D` is large in any actual market. That is measurement.
- Nothing here converts `ρ²` into an economic magnitude. Its units are squared log
  rates, and the translation into anything else is a separate question.
- Nothing here needs a 2-complex, so nothing here inherits §12's problem, and
  equally nothing here resolves it.
- `H`'s connectivity is load-bearing twice, not decorative: it makes `μ_1 > 0` in
  Corollary 5.4 and makes `χ_0` the only kernel direction in Corollary 5.1. With
  `H` disconnected the theorem survives with `L_H⁺`, but "the mean" becomes the
  per-component mean and the split is by component.
- **B13 describes the zero set rather than predicting it, and the distinction is
  worth keeping.** In §5.1's construction "the two classes face the same
  antisymmetric term" and "`S − S' = 0`" are the same sentence, so a per-edge
  classification read off the measured gap is definitional and not an independent
  assignment. What B13 establishes is that the zero set is non-empty, that it is
  reached exactly rather than approximately, and that it is not everything. What
  would make it a prediction is a class assignment fixed before the reading, and
  Corollary 5.2 names the observable that would supply one: `μ`, the ease with
  which a position moves between the two classes, which is measurable without
  reference to any price. On B13's carrier `μ` is fixed by construction and does
  not vary across edges, which is exactly why it cannot do that work there.

### 14.4 What is checked in code

`experiments/b1_reduction.py`. As in §11, this checks the implementation and not
the mathematics: a proof is not evidence about the code that claims to implement
it. Eleven criteria at `--seed 20260827 --trials 10`.

**Four routes to the same number, sharing as little code as could be arranged.**
Brute force solves least squares against the incidence operator of `Γ` and uses no
result from this section. The mode-by-mode route solves one Tikhonov problem per
agent mode on `G` alone. The closed form evaluates the double sum. The projector
route builds `L_Γ` from the product graph, inverts it on its own eigenbasis, and
touches neither the mode transform nor the Kronecker structure nor `lstsq`. If the
product structure were being assumed rather than used, the fourth route is the one
that would disagree.

| | what it checks | reading |
| --- | --- | --- |
| **R-1** | all four routes, ten shapes | agree to `1.42e-14` worst case |
| **R-2** | scaling the deviations by `t` with `w̄` held fixed | `R/t² = 17.11315731` unchanged for `t = 1, 0.5, 0.25, 0.1, 0.01`; the common summand does not move. Corollary 5.1, four decades of it |
| **R-3** | the sandwich of Corollary 5.3 | inside the band ten out of ten |
| **R-4** | the two degenerate ends | all classes equal reproduces `m · dist(w, im d_G)²` to `1e-9`; equal and exact returns `2.13e-14` |
| **R-5** | one `G` and one field, four choices of `H` | `R/D²` rises with `μ_1`: path `0.581` at `μ_1 = 0.5858`, star `0.597` at `1.0`, cycle `0.655` at `2.0`, complete `0.751` at `4.0`, with `λ_max(L_G) = 4.618034` |
| **R-6** | `L_Γ = L_G ⊗ I + I ⊗ L_H` against the Laplacian of `box_product` | difference `0.00e+00`, exactly, on five shapes |
| **R-7** | both ends of Corollary 5.2, reached by weighting agent edges by `t` | `t = 1e−6` gives `15.72801745` against the target `15.72799829`; `t = 1e6` gives `33.11672785` against `33.11674803`; monotone in `t` at all seven values, brute force and closed form agreeing throughout |
| **R-8** | parallelogram law, `ρ²(w̄+u) + ρ²(w̄−u) − 2ρ²(w̄) = 2R(u)` | five trials, worst gap `5.68e-14`. Confirms Corollary 5.1 by a route independent of R-2 |
| **R-9** | fields whose answer is known without the formula | each class exact and all different: `common = 0.00e+00`, everything in `R`. All equal and co-closed: `ρ² = m‖w‖²` to `1e-9`. One class carrying the whole field: matches brute force |
| **R-10** | `m = 1` | collapses to `dist(w, im d_G)²` to `1e-9`, the one-index problem on `G` alone |
| **R-11** | 300 random shapes up to `n = 12`, `m = 8`, all four routes | worst relative spread `5.11e-15`; Corollary 5.3's bounds held on all 300 |

R-6 and R-7 are the two that would catch a wrong theorem rather than a wrong
implementation. R-6 is the only step of the proof that is not one line of linear
algebra, and R-7 exercises the formula at the two limits where its interpretation
is claimed, six orders of magnitude apart in each direction, against targets
computed without it.

### 14.5 Precedent, and what is actually new here

The derivation is a resolvent of a Cartesian-product Laplacian, which is to say
each agent mode solves a Tikhonov problem whose regularisation parameter is that
mode's eigenvalue. None of that is new mathematics and it should not be presented
as such.

What is new is the identification. The regularisation parameter is the agent
graph's spectrum, the object being damped is the price theory's own potential, and
the residual left over is the quantity §13.4 shows standard practice already
estimates under another name. Standard practice never writes this down because it
never puts positions and agent classes into one graph, and without that there is
no product Laplacian to diagonalise.

**The nearest published result, and it has to be named here.** Farinelli and
Takada, *Can You Hear the Shape of a Market? Geometric Arbitrage and Spectral
Theory* (arXiv:1509.03264; Axioms 10(4) 242, 2021), prove that a market satisfies
NFLVR **if and only if zero lies in the discrete spectrum of the connection
Laplacian** on the cash-flow bundle, by way of Atiyah-Singer and
Bochner-Weitzenbock. That is the same family of statement as Theorem 5: a
Laplacian's spectrum decides whether the obstruction vanishes. **Four differences,
each checkable against their text rather than asserted:**

| | there | here |
|---|---|---|
| setting | continuous: stochastic differential geometry, principal fibre bundles, connection and curvature | discrete: the Cartesian-product graph Laplacian `L_G ⊗ I + I ⊗ L_H` |
| agent index | their §2.1 Definition 8 introduces `K` investors with beliefs and utilities, and **the theorems do not carry that index**; the state space runs over assets and a cash account | the agent index is in the graph, and Theorem 5's damping parameter **is** the agent graph's spectrum |
| what is returned | qualitative: whether `0` is in the spectrum | quantitative: `ρ(ω)²` in closed form, a distance to the nearest single potential |
| frictions | assumed away in text: *"there are no transaction costs and short sales are allowed"* | `ω̄ ≢ 0` is the working case, and Theorem 6(4) needs it |

**The second row is the one that matters and it should not be read as a
criticism.** Introducing agents and then proving theorems that do not carry the
index is the standard move, and it is standard because a single-index price field
is what the classical statement is about. This document's construction is the same
move refused: the index stays in the object, which is what leaves a product
Laplacian to diagonalise and what makes the third row possible.

**Whether the identification survives that comparison is the open question**, and
it is one this project cannot settle from the inside.
