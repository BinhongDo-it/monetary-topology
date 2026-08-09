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

Three results.

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

---

## 5. Theorem 2: the cycle space splits, and each carrier reaches one half

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
other half of the cycle space, and the mortgage carrier cannot reach it for
structural reasons rather than for want of a bigger sample.

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

After Theorem 3 the description is "the `L²` norm of the non-exact part of a
1-cochain on a 28-million-vertex graph, measured against the null that it is
exact." Same number, different object, and only the second one is a claim the
framework can be judged on.

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

---

## 10. What the theorem does not say

**It does not show the field is non-integrable.** It gives an exact criterion and
identifies the measurement that decides. The deciding was done in stage B2, and it
could have gone the other way.

**It says nothing about magnitude.** `b₁(Γ)` is large, but a large cycle space is
room for an obstruction, not an obstruction. How much of the field is non-exact is
the empirical question, and the answer is stage B2's within share, not anything in
this document.

**It carries no welfare content.** That no scalar on positions reproduces the terms
different agents face is a statement about representations. It does not by itself
say anyone behaves badly, that markets fail to clear, or that an alternative
allocation would be better. Every such step is separate and none is taken here.

**The Hodge decomposition in `topology.py` is the wrong complex for `Γ`.** That
implementation builds 2-cells from triangles, which is right for the clique complex
used in stage A2c. The natural 2-cells of a Cartesian product are **squares**, and
the four-cycles of §3 are squares. A curl-versus-harmonic split on `Γ` therefore
needs a square complex, which is not built. Until it is, this document claims a
gradient-versus-non-gradient split and no finer decomposition. Flagged rather than
papered over, because the finer split is the more interesting one and someone will
ask for it.

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

The last row is the same discipline applied throughout the repository: a
generalisation that does not reproduce the special case bitwise is not a
generalisation.
