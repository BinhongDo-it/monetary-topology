# B4: the directed theorem

**Pure theory. No data, no retrieval, no parameters.** Everything here is proved
or it is not in the document.

Registered as the prerequisite for the orphan-currency stage by
`PROJECT_PLAN.md` §9.5 and §9.8, which state that the existing theorems do not
cover a market where a conversion runs one way, and that using
`product_graph.py` on any such scenario is prohibited until this document
exists.

Written 2026-08-11.

---

## 0. Summary

Theorem 1 assumes every edge is two-way: the field is antisymmetric, and the
proof chains equalities along paths in the agent graph. Real convertibility is
often one-way. This document generalises to directed edges, and the result is
**not** the one `PROJECT_PLAN.md` §9.5 predicted.

| | undirected (Theorem 1) | directed (here) |
|---|---|---|
| the right null object | a potential `φ` with `ω = d⁰φ` | a **sub-potential** `φ` with `ω ≤ d⁰φ` |
| exists iff | every cycle sums to zero | **no directed cycle sums positive** (Thm 4) |
| how hard to satisfy | hard | **easy**; one-sided constraints are weaker |
| pinned down? | unique up to a constant per component | **bounded modulo constants iff strongly connected** (Thm 5) |
| a non-zero loop means | the obstruction | **either friction or the obstruction**, and the two separate (Thm 6) |

**"Bounded" and not "unique", and the difference is not pedantic.** An earlier
version of this table said *unique up to a constant*, which Theorem 5 does not
say and its proof does not show. Strong connectivity bounds every coordinate
difference; it does not collapse the sub-potential polytope to a point. The
polytope is a single point only when the field is exact, `ω = d⁰φ`, which in the
directed setting is the special case rather than the rule. A canonical potential
therefore has to be **chosen** by an extra rule, such as the pointwise largest
or smallest admissible one, and cannot be deduced from connectivity. Corrected
2026-08-11; the theorem statement in §4 and the proof were right throughout, and
the error was confined to this summary table, which is the part a reader sees
first.

Three consequences that change what the next stage may claim.

**One, existence gets cheaper, so the claim has to move.** Dropping the reverse
edge removes a constraint. A sub-potential nearly always exists, so "no global
potential" stops being the falsifiable statement in the directed setting. §7
records the correction to §9.5, which expected the opposite.

**Two, a non-zero round trip is no longer evidence.** On a two-way edge the
round-trip sum `ω(u,v) + ω(v,u)` is forced to be `≤ 0` by no-arbitrage alone and
is exactly zero only in the antisymmetric case. **A bid-ask spread produces a
non-zero loop sum with no obstruction anywhere.** Reporting a raw loop sum as
non-integrability would be a category error of the same family as the carry-trade
one this project already made once on paper.

**Three, the fix is a canonical split, and Theorem 1 survives on half of it.**
Every two-way edge weight decomposes uniquely into an antisymmetric part `ŵ` and
a symmetric part `ω̄ ≤ 0`. Theorem 1, Theorem 2 and Theorem 3 apply **verbatim**
to `ŵ`; `ω̄` is the friction and carries no agent-index content. The directed
square splits along the same line: its two orientations sum to the friction and
differ by twice the Theorem 1 square sum.

And the case where the split is unavailable — an edge that exists in one
direction only — is `H⁰`, not `H¹`. §5.2 states the criterion for telling which
one is in front of you, because `b1_theorem.md` §12.1 records this project
conflating the two once already.

---

## 1. Where Theorem 1's proof actually breaks

Worth locating precisely rather than saying "the proof used undirectedness".

Theorem 1's step **(3) ⟹ (4)**, across slices, takes the four-cycle for
`(i, j)` and adjacent classes `a, b`, reads its sum as `w_a(i,j) − w_b(i,j)`, and
then says: *for classes not adjacent in `H`, chain the equality along a path in
`H`, which exists because `H` is connected.*

Two uses of two-wayness, and they fail differently.

**Inside the four-cycle.** The return leg `(b,j) → (b,i)` is read as
`−w_b(i,j)`. That step **is** antisymmetry. If `b` faces a different rate going
back than coming out, the leg is `ω_b(j,i)`, an independent number, and the
four-cycle sum is `ω_a(i,j) + ω_b(j,i)`, which is not a difference of terms on a
single transition.

**Along the agent graph.** Chaining `w_a = w_b = w_c` requires the equality to
propagate in both directions along a path in `H`. With directed agent edges,
`H` connected is the wrong hypothesis; **strong** connectivity is what the
chaining needs, and the two differ exactly when the interesting cases arise.

So the theorem does not fail for a subtle reason. It fails at two named lines,
and each line names its own repair.

---

## 2. The directed setting

`Γ⃗ = (V, A)` is a directed graph. `ω : A → ℝ` assigns a number to each directed
edge. **No antisymmetry is assumed** and the reverse of an edge need not be
present.

Reading, fixed here so it is not renegotiated later: `ω(u, v)` is the log of the
rate at which the move `u → v` can actually be made, so a **directed** cycle
with a positive sum is a round trip that ends with more than it started, which is
an arbitrage. `b1_setup.md` §3's holding-period reading is unchanged.

**Definition (sub-potential).** `φ : V → ℝ` is a *sub-potential* for `ω` if

```
ω(u, v)  ≤  φ(v) − φ(u)        for every directed edge (u, v) ∈ A
```

Write `P(ω)` for the set of sub-potentials.

**Why the inequality is the right null and the equality is not.** With one-way
edges the equality `ω(u,v) = φ(v) − φ(u)` asserts that a one-way rate is a ratio
of two prices, which is the very thing a one-way market denies. The inequality
says something an economist would actually assert: **there is a consistent price
vector, and no available move beats it.** §5 shows the equality is recovered
exactly when every edge is two-way, so nothing is lost in the case Theorem 1
covers.

**Definition (slack).** For `φ ∈ P(ω)`, `s_φ(u, v) := φ(v) − φ(u) − ω(u, v) ≥ 0`.

---

## 3. Theorem 4: when a sub-potential exists

**Theorem 4.** `P(ω) ≠ ∅` if and only if every directed cycle of `Γ⃗` has
`ω`-sum `≤ 0`.

**Proof.** (⟹) Let `φ ∈ P(ω)` and let `C = (v₀, v₁, …, v_k = v₀)` be a directed
cycle. Summing the defining inequality along `C`,

```
Σ_C ω  ≤  Σ_t [φ(v_{t+1}) − φ(v_t)]  =  0
```

because the right side telescopes around a closed walk.

(⟸) Adjoin a vertex `s` with a directed edge `s → v` of weight `0` for every
`v ∈ V`; this creates no new directed cycle, since `s` has no incoming edge.
Define

```
φ(v)  :=  max { ω-sum of a directed walk from s to v }
```

The max is over a finite set: no directed cycle has positive sum, so inserting a
cycle into a walk never increases its sum, and the supremum over walks is
attained on simple paths, of which there are finitely many. `φ(v) ≥ 0` since the
single edge `s → v` is a walk. For any `(u, v) ∈ A`, appending that edge to a
maximising walk into `u` gives a walk into `v`, so `φ(v) ≥ φ(u) + ω(u, v)`. ∎

This is the Bellman–Ford potential, and the identification is worth stating
plainly: **the null hypothesis of a single price vector on positions, in the
one-way world, is a shortest-path problem.** No new mathematics is being
invented here, which is a point in its favour.

### 3.1 What Theorem 4 costs the framework

Compare the two existence conditions on the *same* graph with every edge
two-way. Theorem 1 needs every cycle sum to be **zero**. Theorem 4 needs every
directed cycle sum to be **≤ 0** — and each undirected cycle appears twice, once
in each orientation, with sums `σ` and `σ'`. So Theorem 4's condition is
`σ ≤ 0` and `σ' ≤ 0`, and when `σ' = −σ` this forces `σ = 0`. The conditions
coincide, as §5 spells out.

Now delete one direction of one edge. That cycle now has only one orientation,
so only `σ ≤ 0` is required, and `σ` may be strictly negative with no
consequence. **Every deletion strictly weakens the null.**

The framework wants to reject the null. **Directedness helps the null.** That is
the honest accounting.

---

## 4. Theorem 5: what directedness does make harder

Existence gets easier. **Uniqueness gets much harder, and that is where the
content moved.**

`P(ω)` is a polyhedron, non-empty by Theorem 4, and it is closed under two
operations. Adding a constant: obvious. Pointwise maximum: given
`φ₁, φ₂ ∈ P(ω)` and an edge `(u,v)`, pick `i` attaining
`max(φ₁, φ₂)(u) = φ_i(u)`; then
`max(φ₁,φ₂)(v) ≥ φ_i(v) ≥ φ_i(u) + ω(u,v) = max(φ₁,φ₂)(u) + ω(u,v)`.

**Theorem 5.** Assume `P(ω) ≠ ∅` and that the underlying undirected graph is
connected. Then `P(ω)` is bounded modulo the constants **if and only if** `Γ⃗` is
strongly connected.

**Proof.** (⟸) Let `Γ⃗` be strongly connected and fix `u, v`. There is a
directed path `u ⇝ v`; summing the inequality along it gives
`φ(v) − φ(u) ≥ Σ ω`, a finite lower bound independent of `φ`. There is also a
directed path `v ⇝ u`, giving `φ(u) − φ(v) ≥ Σ' ω`, hence
`φ(v) − φ(u) ≤ −Σ' ω`. So every coordinate difference lies in a fixed bounded
interval.

(⟹) Suppose `Γ⃗` is not strongly connected. Its condensation is a directed
acyclic graph with at least two vertices, so it has a sink component `S ⊊ V`
with no directed edge leaving `S`. For `t ≥ 0` set `φ_t := φ + t·1_S`. Edges
inside `S` and edges inside `V∖S` are unaffected. An edge `(u, v)` with `u ∉ S`,
`v ∈ S` has its right-hand side increased by `t ≥ 0`, so the inequality still
holds. There are no edges with `u ∈ S`, `v ∉ S`. Hence `φ_t ∈ P(ω)` for all
`t ≥ 0`: an unbounded ray. ∎

### 4.1 What the unbounded ray is, in words

`φ` is a log value: `b1_setup.md`'s convention makes `w(i,j) = φ(j) − φ(i)` with
`w` the log of the number of units received, so **`φ` moves against price**. A
sink component whose potential can be raised without bound is a set of positions
whose **price can fall without bound and no arbitrage relation objects**.

That is what an orphan currency is, stated as a theorem rather than as a
metaphor: **a position that can be entered and not left is not priced by the
system; it is only bounded on one side.** Not "priced badly", not "priced with a
large deviation". Not priced.

And it is `H⁰`. The failure is that the directed graph does not connect back, so
there is no closed loop to sum, so there is no holonomy to report. Anyone who
reports a number here and calls it a curl has reported an `H⁰` fact under an
`H¹` name, which is precisely the error `b1_theorem.md` §12.1 records.

---

## 5. Theorem 6: the canonical split, and Theorem 1 survives on half of it

Call an edge **two-way** if both `(u,v)` and `(v,u)` are in `A`. On the two-way
part of the graph define

```
ŵ(u, v)  :=  ½ [ ω(u, v) − ω(v, u) ]        antisymmetric
ω̄(u, v)  :=  ½ [ ω(u, v) + ω(v, u) ]        symmetric
```

so `ω = ŵ + ω̄`, uniquely, and `ŵ(v,u) = −ŵ(u,v)`, `ω̄(v,u) = ω̄(u,v)`.

**Theorem 6.** Let every edge of `Γ⃗` be two-way and let `P(ω) ≠ ∅`. Then

1. `ω̄(u, v) ≤ 0` for every edge, and `Σ_C ω = Σ_C ŵ + Σ_C ω̄` for every cycle;
2. `P(ω) = { φ : ŵ(u,v) ≤ φ(v) − φ(u) − ω̄(u,v) ∀(u,v) }`, and `P(ω)` contains a
   `φ` with all slacks zero **if and only if** `ω̄ ≡ 0` and `ŵ` is exact;
3. with `ω̄ ≡ 0`, `P(ω)` collapses to the exact potentials of Theorem 1 and
   Theorems 1, 2 and 3 hold verbatim for `ŵ = ω`.

**Proof.** (1) The two-cycle `u → v → u` is a directed cycle with sum
`ω(u,v) + ω(v,u) = 2 ω̄(u,v)`, which Theorem 4 forces to be `≤ 0`. The
decomposition of a cycle sum is linearity.

(2) The rewriting is substitution. If some `φ` has all slacks zero then
`ω(u,v) = φ(v) − φ(u)` and `ω(v,u) = φ(u) − φ(v)`, so `ω̄ ≡ 0` and `ω = ŵ` is
exact. Conversely if `ω̄ ≡ 0` and `ŵ = d⁰φ` then that `φ` has all slacks zero.

(3) With `ω̄ ≡ 0` the pair of inequalities `ω(u,v) ≤ φ(v) − φ(u)` and
`ω(v,u) = −ω(u,v) ≤ φ(u) − φ(v)` is the single equality
`ω(u,v) = φ(v) − φ(u)`. The hypotheses of Theorem 1 are then met on the
undirected graph and its statement applies unchanged. ∎

**This is the reduction check the repository demands**: a generalisation that
does not reproduce the special case is not a generalisation. Setting `ω̄ ≡ 0`
returns Theorem 1 exactly, in the same way that setting `m = 1` in `b₁(Γ)`
returns `b₁(G)`.

### 5.1 The directed square, and which half of it is the finding

Take a position edge `(i, j)`, two agent classes `a, b`, agent edges of weight
zero in both directions, and all four position legs present. The four-cycle of
`b1_theorem.md` §3 now has two orientations with **different** sums:

```
S   =  ω_a(i, j)  +  ω_b(j, i)
S'  =  ω_b(i, j)  +  ω_a(j, i)
```

and

```
S + S'  =  2 [ ω̄_a(i, j) + ω̄_b(i, j) ]     ≤ 0     the friction part
S − S'  =  2 [ ŵ_a(i, j) − ŵ_b(i, j) ]              the index part
```

**Read the two rows.**

`S + S'` is the two agents' round-trip costs added together. It is
sign-constrained, it is non-zero whenever either agent pays a spread, and **it
says nothing whatever about who the agents are**: give both classes an identical
bid-ask and it is unchanged. A design that reports `S` alone reports a mixture of
this with the next row.

`S − S'` is twice Theorem 1's square sum. It is unconstrained in sign, it is
**invariant to adding any friction common to both classes**, and it is zero
exactly when the two classes face the same antisymmetric terms on that
transition. This is the quantity Theorem 3 turns into a variance and stage B2
measured.

**Registered consequence.** Any stage built on a market with spreads reports
`S − S'` and reports `S + S'` beside it as the friction it removed. Reporting
`S` alone is prohibited. This is `MEASUREMENT.md` rule 4 — one switch, one thing
— appearing in the algebra rather than in the experiment design.

**In quoted terms.** With `rate` in local currency per dollar and `bid < ask`,
`ŵ(LCY → USD) = −log √(bid·ask)` and `ω̄(LCY → USD) = ½ log(bid/ask)`, so

```
S − S'  =  2 · log( mid_b / mid_a )
S + S'  =  log(bid_a/ask_a)  +  log(bid_b/ask_b)
```

The headline needs only the two mid quotes; the spread cancels out of it by
construction. The friction column is what needs two-sided quotes.

### 5.2 One-way edges make the split unavailable, and that is the criterion

`ŵ` and `ω̄` are defined only where both directions exist. A one-way edge is the
limit `ω(v,u) → −∞`, under which `ŵ → +∞` and `ω̄ → −∞` while their sum stays
finite. **The split degenerates rather than giving a large number.**

So the criterion for which failure is in front of you is mechanical:

| what is observed | which object | what may be reported |
|---|---|---|
| both directions quoted, spread present | `H¹` with friction | `S − S'`, with `S + S'` beside it |
| one direction only, for some class | `H⁰` | reachability, and the one-sided bound of Theorem 5 |

A number computed from a one-way edge by *imputing* the missing direction — from
another class's quote, from a lagged quote, from a model — has imputed exactly
the quantity in dispute. Prohibited.

---

## 6. What this does and does not say about the agent graph

`PROJECT_PLAN.md` §9.5 frames the orphan currency as a **directed agent edge**:
a peso position passes from a local to a foreigner and not back. That framing is
available and Theorem 5 covers it. But the same fact admits a second reading and
the two are not interchangeable.

**Reading one, directed agent edge.** `(a, g) → (b, g)` exists, `(b, g) → (a, g)`
does not. The position changes hands one way. This breaks the product structure
of `Γ` in the agent factor.

**Reading two, slice-dependent position edge.** The conversion `PESO → USD`
exists in the local's slice and not in the foreigner's. This breaks the product
structure in the position factor: `Γ` is no longer `G □ H` for any single `G`,
because the slices are not isomorphic.

**Both are `H⁰` statements and Theorem 5 applies to either**, since Theorem 5
assumes only a directed graph. What neither supports is Theorem 2's splitting:
the directed cycles of a graph form a **cone**, not a vector space, and a cone
does not decompose as a direct sum. So **Theorem 2 does not generalise**, and the
slice-versus-square accounting is available only after the split of §5 has been
taken and only on the two-way part.

This is a real limitation and it is stated here rather than discovered later:
`b3_cip_slice.md`'s slice result and `b2_measurement.md`'s square result live on
the two-way part of the world, where FX and mortgage markets both quote both
sides. **Nothing in this document extends them to one-way markets, and nothing
in them extends to one-way markets either.**

---

## 7. Correction to `PROJECT_PLAN.md` §9.5

§9.5 states: *"有向图上'存在全局势'的条件更强，单向可达会同时产生 `H⁰` 分离与非零
`H¹`"* — that the directed existence condition is *stronger*, and that one-way
reachability produces both an `H⁰` separation and a non-zero `H¹`.

**The first clause is backwards.** §3.1: one-way edges remove constraints, so the
existence condition is strictly **weaker**. A sub-potential is easier to find in
the directed world, not harder.

**The second clause is half right.** One-way reachability produces `H⁰`
separation, and Theorem 5 makes that precise and gives it a one-sided price
bound. It does **not** by itself produce a non-zero `H¹`. What it produces that
looks like one is the friction term `ω̄`, which is sign-constrained by
no-arbitrage and is fully compatible with a sub-potential existing. §5.1
separates the two and §5.2 gives the criterion.

**Why this correction is load-bearing rather than pedantic.** The orphan-currency
stage as §9.5 envisages it would measure a loop sum on a market with a wide
spread, find it large and non-zero, and report it as the obstruction. Under
Theorem 6 that number is `S`, a mixture, and its largest component in a thin
market is `S + S'`, the spread. **A referee removes the stage with one sentence.**
The correction turns the stage's outcome measure from `S` into `S − S'` before
any data is retrieved, which is the only time it is free to do so.

`PROJECT_PLAN.md` §9.4's ruling is untouched and is confirmed by §5.1: the
orphan currency measures **squares, not slices**, because the official and
parallel rates are two operators on one conversion. §9.6's requirement that the
connectivity index come from outside price data is untouched and is strengthened
by Theorem 5, since the object it now indexes is reachability rather than
dispersion.

---

## 8. What is checked in code

`experiments/b4_directed_edges.py`, against `src/monetary_topology/directed.py`.

| claim | function | check |
|---|---|---|
| Theorem 4, both directions | `sub_potential` vs `worst_directed_cycle` | Bellman-Ford, which never sees a cycle, against brute-force enumeration of every simple directed cycle, which never builds a potential |
| Theorem 4, validity | `violation` | every edge satisfies the inequality |
| Theorem 5, unbounded | `sink_component`, `ray_is_valid` | `φ + t·1_S ∈ P(ω)` over a grid of `t`, by direct verification |
| Theorem 5, bounded | `potential_interval`, `shift_breaks` | strongly connected: every coordinate interval finite, non-empty, and containing the returned potential; and every proper subset shift breaks |
| Theorem 6 (1) | `split` | `ω̄ ≤ 0` on every two-way edge whenever a sub-potential exists |
| Theorem 6 (3), **the reduction** | `from_antisymmetric` vs `potential_from_cochain` | on an antisymmetric field the directed machinery reproduces Theorem 1's potential **bitwise** |
| §5.1 | `directed_square` | `S ± S'` as directed cycle sums, against `ŵ` and `ω̄` computed separately |
| §5.1 invariance | `directed_square` | a spread common to both classes moves `S + S'` and leaves `S − S'` unchanged |
| §5.2 | `DirectedField.one_way`, `split` | the split declines to produce a value where the reverse leg is absent |

The reduction row is the one that matters. Everything else can be right while
the generalisation quietly fails to contain the case it generalises. Integer
potentials are used there precisely so that "bitwise" is a claim that can be made
rather than a tolerance in disguise.

Two design points in the harness, both of which a later reader would otherwise
have to rediscover.

**Criteria fail when either side of a comparison never occurs.** B4-1 reports the
split between graphs admitting a sub-potential and graphs carrying a positive
cycle, and fails if one side is empty. B4-4 carries the same guard, and it is
what showed that the bounded case needed its own generator: a random directed
field that is both strongly connected and arbitrage-free is rare, because strong
connectivity puts every loop in the sample twice and Theorem 4 requires both
orientations non-positive. `strongly_connected_field` forces strong connectivity
with a Hamiltonian cycle and sets weights so a sub-potential exists by
construction, adding extra edges **one way only** so the sample is not the
antisymmetric case under a new name.

**`DirectedField.value` does not invent the reverse edge.**
`product_graph.Cochain.value` returns `−value(v, u)` when only one orientation is
stored, which is correct there and would silently convert every one-way market
into a two-way one here. The two modules therefore do not share a field
representation.

### 8.1 Results

`python experiments/b4_directed_edges.py`, seed `0`. **Eight of eight pass.**

| criterion | number |
|---|---|
| B4-1 Theorem 4 both ways | 24 graphs, 0 disagreements; 5 admit a sub-potential, 19 carry a positive cycle |
| B4-2 the potential is valid | worst breach `0.000e+00` |
| B4-3 the unbounded ray | 31 graphs with a proper sink; worst violation `1.18e-11` at shifts up to `1e6` |
| B4-4 strong connectivity bounds | 24 graphs; every proper subset breaks; every coordinate interval finite, non-empty, containing the returned potential; widest `2.055` |
| B4-5 `ω̄ ≤ 0` | worst `−4.28e-04` over 24 fields |
| B4-6 **the reduction** | 12 fields, **0 byte-level mismatches** |
| B4-7 the square splits | worst residual `1.11e-15` over 226 squares |
| B4-8 the index ignores a common spread | index unchanged to `8.88e-16`; friction moved by at least `0.222` |

`tests/test_b4_directed.py` carries 23 unit tests on hand-built graphs, where the
answer can be read off by eye rather than trusted from a draw.

---

## 9. What this document does not do

**It does not measure anything.** No stage is opened by it and no number in it
comes from the world.

**It does not license the orphan-currency stage.** It removes the blocker
`PROJECT_PLAN.md` §9.5 records, and it replaces it with a narrower one: the
stage's outcome measure must be `S − S'`, its connectivity index must come from
outside price data, and its `H⁰` claim and its `H¹` claim must be reported as two
results rather than one.

**It does not extend Theorem 2.** §6 states why, and the slice-versus-square
accounting remains a two-way-market statement.

**It carries no welfare content.** That a currency's price is bounded on one side
only is a statement about what the price system determines. It does not say the
arrangement is bad, that anyone is being cheated, or that an alternative would be
better. Every such step is separate and none is taken here.
