# B104: how far an action's rewrite of relative prices reaches

**RUN: 2026-09-15. Statement and proof below. Checks in
`experiments/b104_action_footprint.py`, record `results/b104_action_footprint.json`, which
carries the configuration it ran under. Paper station: zero data. The projection and the graph
helpers are imported from B103.**

## 0. The question this station answers

[`b103_time_reachability.md`](b103_time_reachability.md) section 2 reads the pair an action
joins. An action that adds a relation `e = (i → j)` between two positions of one component
rewrites their relative level by `θ D`, where `D` is the new term's discrepancy from the level
the graph assigned and `θ = w_e R / (1 + w_e R)` is set by the effective resistance `R` between
them. The same theorem gives the move of every potential. This station reads what that move
does to every other pair of positions.

**Which prices an action can reach is a statement about the blocks of the graph, readable
before any weight or term is known.** A block is a maximal piece of the graph that no single
position can disconnect. The blocks on the way from `i` to `j` fuse with the new relation into
one block of the graph after the action, and:

- every relative price moves as the price between the two positions of that block from which
  its ends hang: a part of the economy that reaches the block through a single position shifts
  with that position as one piece, so no price inside such a part moves;
- inside it, the joined pair's rewrite `θ D` is shared along the chain of blocks between `i`
  and `j`, each block taking the share of its own resistance between the two positions through
  which the chain passes it, and every price across a link of the chain moves the same way as
  the joined pair's;
- no price moves further than the joined pair's, and the prices that move exactly as far are
  those between the part that reaches the block through `i` and the part that reaches it
  through `j`.

The third premise of the source manuscript's preamble says that pricing an action presupposes
the world state its price system belongs to. Theorem 41 says how much of an old comparison an
action rewrites. **Theorem 42 says which comparisons it reaches**: for a given action, the
internal prices of every part hanging off the block it creates are a frame the action leaves
where it was, and a different action, with a different path, leaves a different frame.

## 1. Setup

**Notation** is that of [`b103_time_reachability.md`](b103_time_reachability.md) section 1: a
graph `G` of positions whose edges carry weights `w_e > 0` and terms `ω_e`, the weighted
Laplacian `L`, the nearest potentials `φ*`, and for the action `e = (i → j)` the numbers `D`,
`R` and `θ`. Take `i` and `j` in one component and restrict `G` to it: nothing outside that
component moves, and a pair across components has no relative level (Theorem 41 (1)).

**The unit current.** `u = L⁺ (e_j − e_i)` is the potential of a unit current fed in at `j`
and drawn out at `i`, each edge conducting its weight, and `u(j) − u(i) = R`. By Theorem 41 (2)
every potential moves by `κ u` up to a constant, with `κ = w_e D / (1 + w_e R)`, so the
relative level of a pair `(p, q)` moves by

```
m(p, q)  =  κ ( u(q) − u(p) ),        m(i, j)  =  κ R  =  θ D
```

**Blocks.** A cut vertex is a vertex whose removal disconnects the graph. A block is a maximal
connected subgraph without a cut vertex of its own; a bridge, an edge whose removal disconnects
the graph, is a block of two vertices. Four standard facts are used: every edge lies in exactly
one block; two blocks share at most one vertex; every cycle lies inside one block; and the
graph whose nodes are the blocks and the cut vertices, each cut vertex joined to the blocks
containing it, is a tree, the block-cut tree (Harary and Prins 1966). Joining every other
vertex as a leaf to its one block keeps it a tree.

**The path and its gateways.** In that tree the path from `i` to `j` alternates vertices and
blocks,

```
i = g_0,   B_1,   g_1,   B_2,   …,   g_{m−1},   B_m,   g_m = j
```

so `B_k` contains `g_{k−1}` and `g_k`, its two **gateways**, and for `0 < k < m` the gateway
`g_k` is the cut vertex that `B_k` and `B_{k+1}` share. A vertex in two blocks of the path is
joined to both in the tree, which on a path happens only for the gateway they share; so a vertex
of `B_k` other than its gateways lies in no other block of the path, and is an **inner vertex**
of `B_k`. Write `P` for the vertices of `B_1, …, B_m`, and `R_k` for the effective resistance
between `g_{k−1}` and `g_k` in `B_k` on its own edges.

**Lemma 42.0.** Every connected part `X` of `G − P` is joined to `P` through exactly one vertex,
its gateway, written `att(X)`. For a vertex `v` of `X` write `att(v) = att(X)`, and for `v` in
`P` write `att(v) = v`.

*Proof.* `G` is connected, so `X` is joined to `P`. Suppose it is joined to two vertices
`x ≠ y` of `P`. A path from `x` to `y` through `X`, closed by a path from `y` back to `x` along
edges of `B_1, …, B_m`, is a cycle, and it contains an edge of some `B_k`. A cycle lies inside
one block and every edge in exactly one, so the cycle lies inside `B_k`, and `B_k` then contains
a vertex of `X`, which is outside `P`. ∎

## 2. Theorem 42

Let `i` and `j` lie in one component of `G`, and let the action add `e = (i → j)` with weight
`w_e > 0` and term `ω_e`.

**(1) The block the action creates carries every move, and a part hanging from one of its
positions moves as one piece.** The block of `G + e` that holds `e` has exactly the vertices
`P`. Every vertex moves with its gateway, `m(v, att(v)) = 0`, so

```
m(p, q)  =  m( att(p), att(q) )        for every pair
```

and a pair whose two ends reach `P` through the same vertex does not move.

**(2) Along the path the rewrite is shared by resistance.**

```
R  =  R_1 + R_2 + … + R_m,        m(g_{k−1}, g_k)  =  θ D · R_k / R
```

and every inner vertex `v` of `B_k` satisfies `u(g_{k−1}) < u(v) < u(g_k)`.

**(3) No pair moves further than the joined pair, and a pair split by a gateway moves the same
way.** For every pair, `|m(p, q)| ≤ θ |D|`. Let `D ≠ 0`. Equality holds exactly when one of
`att(p)` and `att(q)` is `i` and the other is `j`. And if `att(p)` lies in
`B_1 ∪ … ∪ B_k` and `att(q)` in `B_{k+1} ∪ … ∪ B_m`, not both at `g_k`, then `m(p, q)` is not
zero and has the sign of `m(i, j)`.

**(4) Every other pair moves, for all weights outside a set of measure zero.** Let `D ≠ 0`. For
the weights of `G` outside a set of Lebesgue measure zero, every pair whose ends reach `P`
through different vertices moves. The exceptions exist: on a square `i, a, j, b` with equal
weights, `u(a) = u(b)`, and the pair `(a, b)` does not move.

**Proof.** At every vertex other than `i` and `j` the unit current is conserved, so `u` is
harmonic there: `u(v)` is the average of the potentials of its neighbours, weighted by the
edges. An edge from `x` to `y` carries the current `w (u(x) − u(y))`.

(1) Take a part `X` of `G − P` with gateway `g`. Every neighbour of a vertex of `X` lies in
`X ∪ {g}`, which is connected, and `u` is harmonic at every vertex of `X`. If the largest value
of `u` on `X ∪ {g}` is taken at a vertex of `X`, every neighbour of that vertex takes it too, and
it spreads through `X` to `g`. So the largest value is `u(g)`, the smallest likewise, and `u` is
constant on `X ∪ {g}`: `m(v, g) = κ (u(g) − u(v)) = 0`. For the block: `e` closes
`B_1, …, B_m` into a ring, and removing any one vertex of `P` leaves the ring connected, since
each `B_k` less one vertex is connected, and the ring less one link is a chain. So `P` with `e`
has no cut vertex and lies inside the block of `G + e` that holds `e`. That block contains no
vertex outside `P`: such a vertex would lie in a part `X`, every path from it to `i` or to `j`
would pass through `att(X)`, and `att(X)` would be a cut vertex of the block.

(2) By (1), no edge inside a part, or between a part and its gateway, carries current. Every
other edge has both ends in `P` and lies in a block of the path, since a block off the path
holding two vertices of `P` would, with the path, close a cycle in the block-cut tree. So at an
inner vertex of `B_k`, which is neither `i` nor `j`, the current on the edges of `B_k` is
conserved: the vertex's other edges run into parts hanging from it and carry nothing. The current
in `B_k` therefore leaves through one gateway what it takes in through the other, say `F_k` in
through `g_k`. At a gateway `g_k` with `0 < k < m`, what comes in from `B_{k+1}` goes out into
`B_k`, so `F_k = F_{k+1}`, and at `j` the whole unit goes into `B_m`, so `F_k = 1` for every `k`.
On `B_k`, then, `u` is the potential of a unit current into `g_k` and out of `g_{k−1}` through
the edges of `B_k` alone, and `u(g_k) − u(g_{k−1}) = R_k`. Summing over `k` gives
`R = R_1 + … + R_m`, and `m(g_{k−1}, g_k) = κ R_k = θ D R_k / R`.

For the inner vertices, take `B_k` with at least one; it has no cut vertex, so removing either
gateway leaves it connected. Let `M` be the largest value of `u` on `B_k`. If an inner vertex took
`M`, so would each of its neighbours in `B_k`, and following a path in `B_k` from that vertex to
`g_{k−1}` that avoids `g_k`, every vertex of which before `g_{k−1}` is inner, so would `g_{k−1}`.
But `u(g_{k−1}) = u(g_k) − R_k < M`. So every inner vertex lies strictly below `M = u(g_k)`, and by
the same argument with the gateways exchanged, strictly above `u(g_{k−1})`.

(3) By (1), `m(p, q) = κ ( u(att(q)) − u(att(p)) )` with both gateways in `P`. By (2) the
potentials of the gateways rise strictly along the path, `u(g_0) < u(g_1) < … < u(g_m)`, and each
vertex of `B_k` lies between the potentials of `g_{k−1}` and `g_k`, strictly unless it is one of
them. So every vertex of `P` has a potential in `[u(i), u(j)]`, equal to `u(i)` only at `i` and to
`u(j)` only at `j`, which gives `|m(p, q)| ≤ |κ| R = θ |D|`, with equality exactly when
`{att(p), att(q)} = {i, j}`. If `att(p)` lies in `B_l` with `l ≤ k` and `att(q)` in `B_{l'}`
with `l' ≥ k + 1`, then

```
u(att(p))  ≤  u(g_l)  ≤  u(g_k)  ≤  u(g_{l'−1})  ≤  u(att(q))
```

and equality throughout would put both at `g_k`. Otherwise `u(att(q)) − u(att(p)) > 0`, and
`m(p, q)` has the sign of `κ`, which is the sign of `D` and of `m(i, j)`.

(4) By (2) and (3), two distinct vertices of `P` share a potential only if both are inner
vertices of one block `B_k`. For two such vertices `v ≠ v'`, `u(v) − u(v')` is a rational
function of the weights of `G` whose denominator, by Kirchhoff's matrix-tree theorem, is a sum
over spanning trees of products of weights, and is positive (Kirchhoff 1847). So it vanishes
either for all weights or only on a set of measure zero, and it is enough to find a limit of
positive weights, keeping `G` connected, at which it does not vanish. `B_k` has no cut vertex,
so by Menger's theorem two paths run from `v` to `g_{k−1}` and to `g_k` meeting only at `v`
(Menger 1927), and together they form a path `Q` from `g_{k−1}` to `g_k` through `v`. If `v'` is
not on `Q`, `B_k − v` is connected, and a shortest path `S` in it from `v'` to `Q − v` meets `Q`
only at its end, which is not `v`. Extend `Q ∪ S`, or `Q` alone if `v'` lies on it, to a spanning
tree `T` of `B_k`, and let the weights of the other edges of `B_k` go to zero. `G` stays connected,
so `u` depends continuously on the weights, and by the argument of (2) its limit on `B_k` is the
potential of a unit current from `g_k` to `g_{k−1}` through `T`. That current runs along `Q`, the
potential rises strictly along `Q`, and by the argument of (1) every vertex of `T` off `Q` takes
the potential of the vertex through which it reaches `Q`. So in the limit `u(v)` and `u(v')` are
the potentials of two different vertices of `Q`, and they differ. ∎

### Corollary 42.1: relations added before an action widen what it can reach and do not raise the share it rewrites

Let `G'` be `G` with more edges, with `P'` and `att'` its block and gateways for the same action.
Then `P ⊆ P'`; every pair whose ends hang from different vertices of `P` hangs from different
vertices of `P'`; and `R' ≤ R`, so `θ' ≤ θ`. **In a denser economy an action can reach every
price it could reach before, and rewrites no larger a share of its own pair's discrepancy.**

*Proof.* The block of `G + e` that holds `e` is a subgraph of `G' + e` without a cut vertex, so it
lies inside the block of `G' + e` that holds `e`, and `P ⊆ P'`. Let `att(p) = a ≠ b = att(q)`,
and suppose `p` and `q` reached `P'` through one vertex `g`. In `G` a path from `p` to `a` has
every vertex but `a` outside `P`, and its first vertex in `P'` is the vertex through which `p`
reaches `P'`, which is `g`; likewise a path from `q` to `b` passes `g` before any other vertex of
`P'`. Each path meets `P` only at its end, so `g` is neither `a` nor `b` and lies outside `P`, and
the two paths from `g` join `a` to `b` through vertices outside `P`, against Lemma 42.0. `R' ≤ R`
is Rayleigh's law, Theorem 41 (3), with equality when no added relation carries current between
`i` and `j`, as a relation joining a part to its own gateway does not. ∎ It carries no check of
its own.

## 3. What the checks read

**Three criteria, all passing** at `--seed 104`. They run on every connected labelled graph on 2
to 6 vertices with random weights and terms, every missing edge added once (`189,587` actions,
`2,827,313` pairs of vertices), and on `3,000` actions on sparse random connected graphs of 16,
32 and 64 vertices (`2,632,000` pairs). The moves are read from the two fits, before and after
the action. Which pairs attain the bound, how the rewrite is shared along the path, and how close
two potentials come are read on `u`, which does not scale with `D`.

| | criterion | reading |
|---|---|---|
| `B104-1` `own_reading` | the bound and the pairs that attain it | the largest move of any pair exceeds the joined pair's by at most `3.6e-14`. The pairs at potential difference `R` are exactly those with one end reaching the created block through `i` and the other through `j`, with no mismatch on any action; `42,804` and `680` actions have a part hanging off `i` or `j`, where that set is larger than the joined pair. Outside it the closest pair stays below the bound by `7.25e-6` of `R` in the enumeration and `2.14e-4` on the random graphs |
| `B104-2` `own_reading` | the block the action creates, and what hangs off it | on every action the block of the graph after the action that holds the new edge has exactly the vertices of the blocks on the path. `126,156` and `14,144` vertices lie outside it; every part outside meets it in one vertex, and every vertex outside moves with that vertex to `4.7e-14`. So `162,876` pairs of the enumeration (`5.76%`) and `19,583` of the random graphs (`0.74%`) cannot move under the action they face |
| `B104-3` `own_reading` | the rewrite shared along the path | the path crosses two blocks or more on `96,315` and `849` actions, at most five, and `134,418` of `310,934` and `1,025` of `4,034` blocks on the paths are a single edge. On every block the potential rises from its gateway toward `i` to its gateway toward `j` by the block's own resistance, computed on its edges alone, to `2.0e-14` of `R`, and no vertex of a block lies outside its gateways. Inside a block the closest vertex stays clear of both gateways by `7.25e-6` of `R` in the enumeration and `1.24e-4` on the random graphs. With `B104-2`, this carries the direction in (3) |

Figures below `1e-11` in this table are what the run printed on the build that first wrote the
record; the record carries the tolerance only. A Windows build writes the same record byte for
byte and prints `3.5e-14`, `3.9e-14` and `1.9e-14` for the three.

**Part (4) is printed and not judged**, because a tolerance cannot tell a set of measure zero
from a small gap. Distinct vertices of the block an action creates come no closer in potential
than `9.85e-8` of `R` in the enumeration and `1.8e-8` on the random graphs.

**Each criterion has seeded failures in `--selftest`, and wherever a seed could land on
nothing the self-test asserts that it landed.** The block machinery is checked on hand fixtures: a path with a pendant chain, a bowtie
split at its cut vertex, the block path with its gateways, and a part meeting a wrong path in two
vertices. `B104-1` fails with the attaining pairs taken as the joined pair alone, with the joined
pair's move read at half its size, and with the action left out of the fit after it; a pair one
millionth of `R` below the bound is a fixture it must not count as attaining. `B104-2` fails with
every vertex outside attached to `i`, with a part meeting the block in two vertices, with the
action left out of the fit, and with the created block looked for in the graph before the action.
`B104-3` fails with every edge of a block conducting one, with the last block of a path alone read
that way, with each block's rise read against the next block's resistance, with every block held
between the first block's gateways, and with the inner vertices read one `R` above where they are.

## 4. Two things the checks found that the statement did not contain

**The frame an action leaves untouched is common and made of small pieces.** On the random graphs
`2,786` of `3,000` actions leave some positions outside the block they create, `12.6%` of all the
positions across the `3,000`, and yet only `0.74%` of pairs cannot move. The positions outside hang from
many different gateways and shift against one another; the rigid pieces are the parts that hang
from one gateway each. In the enumeration `82,416` of `189,587` actions leave positions outside,
`11.1%` of all the positions, and `5.76%` of pairs cannot move.

**A count of the pairs that move depends on `D`, and the potential gaps do not.** Counting the
pairs whose move, read from the two fits, exceeds `1e-9` gives exactly the pairs that hang from
different vertices of the created block in the enumeration. On the random graphs it gives two
fewer: two pairs that hang apart move by less than `1e-9`, and the move their potential gaps
predict is at most `4.25e-10`, so the fits read them correctly and the tolerance on the move is
what drops them. **The attaining set and the gaps of (4) are read on `u` for that reason.**

## 5. The footprint read as an economy

A position that trades with the rest of an economy only through one other position, a village
through its market town or a supplier through its one buyer, forms with everything behind it a
part that hangs off the rest by a gateway. **By (1), an action elsewhere moves such a part's
prices relative to the outside by exactly what it moves its gateway's, and changes no price
inside it.** Which parts are left that way depends on the action: a road that joins two places
already connected by a longer route rewrites prices around the ring of places it closes, and the
places that reach that ring through one town shift with that town.

Inside the ring, by (2), the joined pair's rewrite is split along the chain of sub-economies
between the two places in proportion to how loosely each ties the two points through which the
chain passes it. A tightly integrated sub-economy keeps the price between its two gateways nearly
where it was, and the rewrite lands on the loose links. **By (3), every price between a place on
one side of a gateway and a place on the other moves the way the joined pair's price moves, and
none moves further.**

[`b103_time_reachability.md`](b103_time_reachability.md) Corollary 41.3 put two things on one
number, `D`: the loop an action creates and its rewrite of the old prices. **Theorem 42 puts both
in one place.** Every loop through the new relation lies inside the block the action creates,
because a cycle lies inside one block, and every price the action rewrites moves as a pair of
positions of that block, carried unchanged to what hangs from them. By Corollary 42.1, relations
added before an action enlarge that block, leave every price it could reach within reach, and
never raise the share of its pair's discrepancy that it rewrites.

## 6. Placement

**A.** Harmonic potentials and the maximum principle, the series law of effective resistance,
the matrix-tree theorem, Menger's theorem and the block-cut tree are circuit and graph theory,
used here where they are needed (Kirchhoff 1847; Menger 1927; Harary and Prins 1966; Doyle and
Snell 1984), and the blocks are found by depth-first search (Tarjan 1972).

**D.** That every price an action rewrites moves as a pair of positions of the block it creates,
with every part hanging off that block shifted with its gateway as one piece; that the rewrite is shared along the
chain of blocks between the joined positions in proportion to each block's own resistance, with
every price split by a gateway moving the way the joined pair's does; that no price moves further
than the joined pair's, and exactly which prices move as far; that every other pair moves for all
weights outside a set of measure zero; and that relations added before an action widen what it
can reach without raising the share it rewrites. **Which prices an action can rewrite is fixed by the
blocks of the graph before it, before any weight or term is known.**

**C is empty and this station cannot produce it**: it reads no data, so no point prediction of
any other account is scored here.

## 7. Scope

Positive weights, one relation added inside a component, and the terms on every other edge held
where they were. Parts (1) to (3) hold for every choice of weights, and (4) for all weights
outside a set of measure zero. Several actions compose one at a time, each with the blocks of the
graph as it stands at that step, and an action merges the blocks on its path into one, so blocks
only merge as actions accumulate. The checks use simple graphs; the statement holds with parallel
edges, which lie in one block. Nothing here measures a price, an action or a world state in any
economy.

## References

- Doyle, P. G. and Snell, J. L. (1984). *Random Walks and Electric Networks*. Carus
  Mathematical Monographs 22. Mathematical Association of America.
- Harary, F. and Prins, G. (1966). The block-cutpoint-tree of a graph. *Publicationes
  Mathematicae Debrecen* 13: 103–107.
- Kirchhoff, G. (1847). Ueber die Auflösung der Gleichungen, auf welche man bei der Untersuchung
  der linearen Vertheilung galvanischer Ströme geführt wird. *Annalen der Physik und Chemie*
  148(12): 497–508.
- Menger, K. (1927). Zur allgemeinen Kurventheorie. *Fundamenta Mathematicae* 10: 96–115.
- Tarjan, R. (1972). Depth-first search and linear graph algorithms. *SIAM Journal on Computing*
  1(2): 146–160.
