# B105: what cutting a relation rewrites, read before the cut

**RUN: 2026-09-15; Corollary 43.5 and `B105-3` 2026-09-16; Corollary 43.6, `B105-4` and `B105-5` 2026-09-16. Statement and proof below. Checks in
`experiments/b105_cutting_relations.py`, record `results/b105_cutting_relations.json`, which
carries the configuration it ran under. Paper station: zero data. The projection and the graph
helpers are imported from B103.**

## 0. The question this station answers

[`b103_time_reachability.md`](b103_time_reachability.md) section 2 reads an action that adds a
relation, from the world before it: the action rewrites the share `θ = w_e R / (1 + w_e R)` of
the discrepancy `D` its term brings, with `R` the effective resistance between the positions it
joins. [`b104_action_footprint.md`](b104_action_footprint.md) section 2 reads which prices that
rewrite reaches. This station reads the action that removes a relation, such as a trade link
closed, a parity given up, or a set of measures that shuts several routes at once, **and reads it
from the world that still holds the relation**, so that what a cut will rewrite is priced before
the cut.

**What a cut rewrites is set by a number the fit already carries for every relation, its
leverage.** Draw a spanning tree of the graph with probability proportional to the product of its
weights. A relation's leverage `h_e` is the probability that the tree contains it. It lies in
`(0, 1]`, it equals one exactly when the relation is a bridge, and:

- a relation in place shows only the share `1 − h_e` of the disagreement between its own term
  and what the rest of the graph says, so cutting it moves its pair's relative price by
  `h_e / (1 − h_e)` times the residual visible on it before the cut: more than that residual when
  `h_e > 1/2`, and without bound as `h_e → 1`;
- a bridge shows no residual, and cutting it moves no price on either side of it and removes every
  comparison across it;
- a set of relations cut together disconnects the graph exactly when no spanning tree avoids all of
  them, which can happen when each of them alone has a route around it. Otherwise the set releases
  its residuals through `(I − H_F)^{−1}`, where `H_F` holds the members' leverages and their
  interactions, and each member's own residual is multiplied at least as much as when it is cut
  alone;
- a relation weakened in place, to `(1 − κ)` of its weight, moves its pair by `κ h_e / (1 − κ h_e)`
  times the residual it shows, which stays below `κ / (1 − κ)` times that residual whatever the
  leverage, so only closing a relation removes the bound;
- a relation whose term moves by `Δ`, with every weight and every other term where it was, passes
  `h_e Δ` to its pair's relative price and keeps `(1 − h_e) Δ` as residual, and no other pair moves
  further, so a published change of a term reads the leverage before anything is cut.

The third premise of the source manuscript's preamble says that pricing an action presupposes the
world state its price system belongs to. **Read before the action, an addition rewrites less than
the discrepancy it can see, and a cut rewrites a multiple of the residual it can see, with no bound
on the multiple.** **And when the action may not happen at all, no single price is right in both worlds: with `π` the
probability of the action, the least any single price can miss by, on average and squared, is
`π (1 − π)` times the square of the rewrite.**

## 1. Setup

**Notation** is that of [`b103_time_reachability.md`](b103_time_reachability.md) section 1: a
graph `G` of `n` positions whose relations `e = (i → j)` carry weights `w_e > 0` and terms `ω_e`,
`W = diag(w_e)`, the weighted Laplacian `L`, and the nearest potentials `φ*`. Write `B` for the
incidence matrix `d⁰`, so that `(Bφ)_e = φ(j) − φ(i)` and `L = B'WB`, and `r = ω − Bφ*` for the
residuals the fit leaves, which satisfy `B'Wr = 0` and give `ρ² = r'Wr`. Take `G` connected: a
graph with several components is one problem per component, and a set of relations spread over
several components splits the same way.

**Leverage.** For a relation `e = (i → j)` put `b = e_j − e_i`, `u = L⁺b` and `R = b'u`, as in
B103 and B104: `u` is the potential of a unit current fed in at `j` and drawn out at `i`, and `R`
is the effective resistance between them. The leverage of `e`, a name section 6 explains, is

```
h_e  =  w_e R
```

and `r_e = ω_e − (φ*(j) − φ*(i))` is the residual the fit leaves on it. The matrix
`H = W^{1/2} B L⁺ B' W^{1/2}`, one row and one column per relation, has the leverages on its
diagonal. For a set `F` of `k` relations, a **package**, write `B_F` for the rows of `B` on `F`,
`W_F`, `w_F` and `r_F` likewise, and `H_F` for the `k × k` block of `H` on `F`. An off-diagonal
entry of `H_F` is `√(w_f w_g) b_f' L⁺ b_g`, and it is zero exactly when `g` carries no current
under a unit current between the ends of `f`.

**Spanning trees.** `τ(G)` is the sum, over the spanning trees of `G`, of the product of their
weights, and the **random spanning tree** is drawn with probability proportional to that product.
A spanning tree is a backbone: it connects every position, and removing any one of its relations
disconnects it.

**Time enters in one place**, as in B103: the projection on `G` against the projection on
`G − F`. Every quantity in the statements below is computed on `G`, the graph before the cut.

## 2. Theorem 43

Let `G` be connected.

**(1) Leverage is the share of backbones through a relation.** For every relation `0 < h_e ≤ 1`,
and `h_e = 1` exactly when `e` is a bridge. The leverages add to `n − 1`, and `h_e` is the
probability that the random spanning tree contains `e`.

**(2) Cutting one relation that is not a bridge.** The graph stays connected, and

```
the relative level of i and j becomes     ω_e − r_e / (1 − h_e)
every potential moves by                  −( w_e r_e / (1 − h_e) ) · u,   up to a constant
ρ²  falls by                              w_e r_e² / (1 − h_e)
```

while `b₁` falls by one and `c` holds.

**(3) Cutting a bridge.** Let `S` and `T` be the two sides of `e`, holding `i` and `j`. The
residual `r_e` is zero. Cutting `e` moves no relative level between two positions of one side, and
leaves `ρ²` and `b₁` where they were while `c` rises by one. Each of the `|S| · |T|` relative
levels across it, fixed before the cut, takes every real value after it.

**(4) A package disconnects exactly when no backbone avoids it.**

```
det( I − H_F )  =  τ(G − F) / τ(G)  =  P( the random spanning tree contains no member of F )
```

so `I − H_F` is singular exactly when cutting `F` disconnects `G`.

**(5) A package that leaves the graph connected.** Let `φ⁻` be the nearest potentials of `G − F`,
and `g_F = ω_F − B_F φ⁻` the gaps the package leaves: the terms of its members less the relative
levels their ends take after the cut. With `s = W_F^{1/2} r_F`,

```
g_F                        =  W_F^{−1/2} ( I − H_F )^{−1} W_F^{1/2} r_F
every potential moves by      −L⁺ B_F' W_F g_F,   up to a constant
ρ²  falls by                  r_F' W_F g_F  =  s' ( I − H_F )^{−1} s
```

while `b₁` falls by `k` and `c` holds. The fall in `ρ²` is never less than `s's = Σ w_f r_f²`,
what the members carried before the cut. (2) is the case `k = 1`.

**Proof.** (4) first, then (1) and (5), which use it.

(4) Remove one vertex `v₀`. `L₀`, the Laplacian without the row and column of `v₀`, is invertible
because `G` is connected, and by the matrix-tree theorem `det L₀ = τ(G)` (Kirchhoff 1847). Write
`B_{F,0}` for `B_F` without the column of `v₀`. The same reduced Laplacian for `G − F` is
`L₀ − UU'` with `U = B_{F,0}' W_F^{1/2}`, and its determinant is `τ(G − F)`, which is zero exactly
when `G − F` is disconnected. By Sylvester's identity `det(I − XY) = det(I − YX)`,

```
det( L₀ − UU' )  =  det L₀ · det( I − U' L₀^{−1} U )
```

and `U' L₀^{−1} U = H_F`. For `y` in `ℝ^k` the vector `x = B_F' W_F^{1/2} y` sums to zero, and the
solution of `L₀ φ₀ = x₀`, extended by `φ(v₀) = 0`, solves `Lφ = x`, because the rows of `L` sum to
zero and the equation at `v₀` is therefore minus the sum of the others. That solution is `L⁺x` plus
a constant, which `B_F` does not see. So `det(I − H_F) = τ(G − F) / τ(G)`, and a spanning tree of
`G` avoids `F` exactly when it is a spanning tree of `G − F`.

(1) With `A = W^{1/2} B`, `H = A (A'A)⁺ A'` is the orthogonal projector onto the range of `A`, and
its diagonal entry at `e` is `w_e b'L⁺b = h_e`. So `h_e = ‖H 1_e‖² ≤ 1`, with equality exactly when
`1_e` lies in the range of `A`, that is, when some potential has a non-zero difference across `e`
and a zero difference across every other relation. Such a potential is constant on each connected
piece of `G − e` and differs between the pieces holding `i` and `j`, so `e` is a bridge; and for a
bridge, the potential that is zero on `S` and `w_e^{−1/2}` on `T` is one. `h_e > 0` because `b` is
non-zero and lies in the range of `L`. The trace of a projector is its rank, which here is `n − 1`
(Foster 1949), and (4) with `F = {e}` gives the probability that the tree contains `e` as
`1 − (1 − h_e) = h_e`.

(5) The normal equations on `G` and on `G − F` are `Lφ* = B'Wω` and
`(L − B_F'W_F B_F) φ⁻ = B'Wω − B_F'W_F ω_F`. Subtracting, `δ = φ⁻ − φ*` satisfies
`(L − B_F'W_F B_F) δ = −B_F'W_F r_F`, which is `Lδ = −B_F'W_F (r_F − B_F δ) = −B_F'W_F g_F`,
since `g_F = r_F − B_F δ`. The right side sums to zero, so `δ = −L⁺B_F'W_F g_F` up to a constant.
Multiplying by `W_F^{1/2} B_F` gives `W_F^{1/2} g_F = s + H_F W_F^{1/2} g_F`, and `I − H_F` is
invertible by (4) because `G − F` is connected, which gives `g_F`. After the cut the relations
outside `F` carry the residuals `r − Bδ`, so

```
ρ⁻²  =  ( ρ*² − s's )  −  2 Σ_{e ∉ F} w_e r_e (Bδ)_e  +  δ' (L − B_F'W_F B_F) δ
```

The sum is `r'WBδ − r_F'W_F B_F δ = −r_F'W_F B_F δ`, because `B'Wr = 0`, and the last term is
`−r_F'W_F B_F δ` by the equation for `δ`. So `ρ*² − ρ⁻² = s's − r_F'W_F B_F δ = r_F'W_F g_F`.
`H_F` is a block of the projector `H`, so its eigenvalues lie in `[0, 1]`, and below one when
`I − H_F` is invertible. Then `(I − H_F)^{−1} − I = H_F (I − H_F)^{−1}` has no negative eigenvalue,
and the fall is at least `s's`. `E` falls by `k` and `c` holds.

(2) is (5) with `F = {e}`: `H_F = h_e`, `g = r_e / (1 − h_e)`, `B_F' = b`, and the level of `i` and
`j` after the cut is `ω_e − g`.

(3) is Theorem 41 (1) read from the graph that holds the bridge. `e` is the only relation between
`S` and `T`, so adding a constant to every potential on `T` changes only the residual on `e`. The
minimum therefore puts that residual at zero, and it is reached exactly when the potentials on `S`
and on `T` are nearest potentials of the relations inside `S` and inside `T`, which are the nearest
potentials after the cut. So no level within a side moves, `ρ²` loses the zero that `e` carried,
`E` falls by one and `c` rises by one, and the constant on `T` is free after the cut. ∎

### Corollary 43.1: an addition rewrites less than it can see, and a cut rewrites a multiple of what it can see, without bound

Let `e` be a relation that is not a bridge, `φ⁻` the nearest potentials of `G − e`, and
`D_e = ω_e − (φ⁻(j) − φ⁻(i))` the discrepancy of the term from the level the graph without `e`
assigns, which is Theorem 41's `D` for adding `e` to `G − e`. Then

```
r_e                                        =  (1 − h_e) D_e
the cut moves the level of i and j by      −h_e D_e  =  −( h_e / (1 − h_e) ) r_e
```

and `h_e` is the share `θ` that Theorem 41 (2) gives for adding `e` to `G − e`.

**Adding `e` to `G − e` and cutting it from `G` join the same two world states, read from opposite
ends.** From the state without the relation, the addition sees the whole discrepancy `D_e` and
rewrites the share `h_e < 1` of it, toward the term (Corollary 41.2). From the state with the
relation, the cut sees the residual `(1 − h_e) D_e` and rewrites `h_e / (1 − h_e)` times what it
sees: more than it sees when `h_e > 1/2`, without bound as `h_e → 1`, and at `h_e = 1` the
comparison itself goes, by (3). The level moves away from the term, on the side where it already
stood: the gap between term and level grows from `r_e` to `r_e / (1 − h_e)`. **A relation in place
hides the share `h_e` of the disagreement it holds down, and the relations the graph leans on most
hide the largest share.**

*Proof.* By (2) the level after the cut is `ω_e − r_e / (1 − h_e)`, and by definition it is
`ω_e − D_e`, so `D_e = r_e / (1 − h_e)` and the level moves by `r_e − D_e = −h_e D_e`. For the
share, Theorem 41 (3) with the added relation `(i, j)` itself gives the resistance of `G` from the
resistance `R⁻` between `i` and `j` in `G − e` as `R = R⁻ − w_e R⁻² / (1 + w_e R⁻) = R⁻ / (1 + w_e R⁻)`,
which is the parallel law `1/R = 1/R⁻ + w_e`, so `h_e = w_e R⁻ / (1 + w_e R⁻) = θ`. ∎

### Corollary 43.2: a member's own residual weighs in a package as in the last cut of a sequence

Let `G − F` be connected, `f` a member of `F`, `F'` the other members, and `h'_f` the leverage of
`f` in `G − F'`. Then

```
( (I − H_F)^{−1} )_ff   =   1 / (1 − h'_f)   ≥   1 / (1 − h_f)
```

with equality exactly when no other member carries current under a unit current between the ends
of `f`. **The weight a member's own residual carries in its gap is the amplification that member
would have if it were cut last, after the rest of the package, and cutting the rest first can only
have raised it.**

*Proof.* Write `c` for the column of `H_F` at `f` without its entry at `f`. By the Schur complement,
`((I − H_F)^{−1})_ff = 1 / (1 − h_f − c' (I − H_{F'})^{−1} c)`, and `I − H_{F'}` is invertible by
(4). The argument of (5), run with `b_f` as the right side, gives the unit current between the ends
of `f` in `G − F'` as `L⁺ b_f + L⁺ B_{F'}' W_{F'}^{1/2} y` with
`(I − H_{F'}) y = W_{F'}^{1/2} B_{F'} L⁺ b_f`, so `h'_f = h_f + c' (I − H_{F'})^{−1} c`, the Woodbury
identity (Woodbury 1950). `(I − H_{F'})^{−1}` is positive definite, so `h'_f ≥ h_f`, with equality
exactly when `c = 0`; that inequality is Rayleigh's law in this form (Doyle and Snell 1984). ∎

### Corollary 43.3: a cut reaches only the blocks that hold it

Let `G − F` be connected. For a member `f`, the path between its two ends in the block-cut tree of
`G` is the one block `B(f)` that holds it, so Lemma 42.0 of
[`b104_action_footprint.md`](b104_action_footprint.md) gives every position a gateway `att_f(p)`
into `B(f)`. A relative level `(p, q)` moves under the cut only if `att_f(p) ≠ att_f(q)` for some
member `f`. In particular, no level between two positions of one connected part of `G`, less the
positions of the blocks that hold the members, moves. For one cut with `r_e ≠ 0`, no level moves
further than the cut pair's own `h_e |D_e|`, and a level moves that far exactly when one of its
ends reaches `B(e)` through `i` and the other through `j`.

*Proof.* By (5) the move is the sum over members of `−w_f g_f L⁺ b_f`, and `L⁺ b_f` is the potential
of a unit current between the ends of `f` in `G`. By Theorem 42 (1) it takes the same value at a
position and at that position's gateway into `B(f)`, so every term vanishes on a pair with
`att_f(p) = att_f(q)` for every member. A connected part of `G` less the union of those blocks lies,
for each member, inside one part of `G` less the positions of `B(f)`, on which `att_f` is constant.
For one cut the move is `−w_e D_e u`, by (2) and Corollary 43.1, and Theorem 42 (3) bounds
`|u(q) − u(p)|` by `R`, with equality exactly when `{att_e(p), att_e(q)} = {i, j}`, so every level
moves by at most `w_e |D_e| R = h_e |D_e|`. ∎

### Corollary 43.4: before an action that may not happen, no single price is right in both worlds

Let an action, an addition inside a component as in Theorem 41 (2) or a cut that leaves the graph
connected as in (2) and (5), happen with probability `π` strictly between zero and one, decided after
a price is quoted. For a pair of positions `(a, b)`, write `ℓ⁰` and `ℓ¹` for its relative level in the
world without the action and in the world with it, and `m = ℓ¹ − ℓ⁰` for the rewrite. A single quoted
level `x` misses on average by

```
π (ℓ¹ − x)² + (1 − π) (ℓ⁰ − x)²   =   π (1 − π) m²  +  ( x − π ℓ¹ − (1 − π) ℓ⁰ )²
```

so no single level misses by less than `π (1 − π) m²` on average, and exactly one level reaches that:
the probability-weighted middle `π ℓ¹ + (1 − π) ℓ⁰`, which is a level of neither world unless `m = 0`.
For the joined pair of an addition `m = θ D`, and for the two ends of a single cut
`m = −h_e D_e = −(h_e / (1 − h_e)) r_e`, so, read before the action,

```
an addition:   least expected squared miss   =   π (1 − π) θ² D²                        ≤   π (1 − π) D²
a cut:         least expected squared miss   =   π (1 − π) ( h_e / (1 − h_e) )² r_e²
```

For an addition or a single cut, no pair's rewrite exceeds that pair's (Theorem 42 (3), Corollary
43.3), so that pair carries the largest unavoidable miss, and a pair whose ends hang from one gateway
carries none. If the action joins two components or cuts a bridge, one of the two worlds gives the pair
no relative level at all (Theorem 41 (1), part (3)), and no finite miss can be named.

**The third premise says that no single price system is available before an action that may change
the world state. Corollary 43.4 gives the size of that absence**: the best any single price can do is
a middle value that belongs to neither world, and it still misses by `π (1 − π)` times the square of
the rewrite. For a cut, that is `π (1 − π) (h_e / (1 − h_e))²` times the square of the residual the
pricer can see.

*Proof.* A level that equals `ℓ¹` with probability `π` and `ℓ⁰` otherwise has mean
`π ℓ¹ + (1 − π) ℓ⁰` and variance `π (1 − π) m²`, and the expected squared miss of `x` is that
variance plus the squared distance from `x` to the mean. The two rewrites are Theorem 41 (2) and
Corollary 43.1. ∎

### Corollary 43.5: a relation weakened in place

Let `e = (i → j)` be a relation, `0 < κ < 1`, and `φ^κ` the nearest potentials of the graph in
which the weight of `e` is `(1 − κ) w_e` and every other weight and every term is where it was. The
graph keeps all its relations, so it stays connected, and

```
the relative level of i and j becomes     ω_e − r_e / (1 − κ h_e)
every potential moves by                  −( κ w_e r_e / (1 − κ h_e) ) · u,   up to a constant
ρ²  falls by                              κ w_e r_e² / (1 − κ h_e)
```

where `ρ²` after the change is weighed with the new weight. As `κ → 1` the three lines become those
of (2), and a bridge, which carries no residual, moves nothing at any `κ`.

**A relation weakened in place rewrites through the same leverage as a cut, with `κ h_e` in place of
`h_e`, and its rewrite is bounded.** Its pair moves by `κ h_e |r_e| / (1 − κ h_e)`, which rises with
the leverage and with `κ`, and `κ h_e / (1 − κ h_e) < κ / (1 − κ)` for every `h_e < 1`. Whatever the
leverage, a measure that makes a relation dearer without removing it rewrites less than
`κ / (1 − κ)` times the residual the relation shows, and only removing the relation, `κ = 1`, lifts
the bound.

*Proof.* The normal equations of the weakened graph are `(L − κ w_e b b') φ^κ = B'Wω − κ w_e ω_e b`.
Subtracting `L φ* = B'Wω`, `δ = φ^κ − φ*` satisfies `L δ = −κ w_e g b`, with `g = ω_e − b'φ^κ` the
residual left on `e`. The right side sums to zero, so `δ = −κ w_e g u` up to a constant, and
`b'δ = −κ h_e g`. Since `g = r_e − b'δ = r_e + κ h_e g`, `g = r_e / (1 − κ h_e)`, which gives the
first two lines. Because `B'Wr = 0`, the new potentials leave the residual sum `ρ*² + δ'Lδ` under the
old weights, and `δ'Lδ = κ² w_e² g² R`; lowering the weight of `e` takes away `κ w_e g²`, so the
weakened fit is left with `ρ*² − κ w_e g² (1 − κ h_e) = ρ*² − κ w_e r_e² / (1 − κ h_e)`. The bound
follows from `h_e ≤ 1`, since `κ h / (1 − κ h)` increases in `h`. ∎

### Corollary 43.6: a term moved in place passes on its leverage

Let `e = (i → j)` be a relation, `Δ` a real number, and `φ^Δ` the nearest potentials of the graph in
which the term of `e` is `ω_e + Δ` and every weight and every other term is where it was. Then

```
the relative level of i and j moves by     h_e Δ
the residual on e becomes                  r_e + (1 − h_e) Δ
every potential moves by                   w_e Δ · u,   up to a constant
ρ²  changes by                             w_e Δ ( 2 r_e + (1 − h_e) Δ )
```

and no relative level moves by more than `h_e |Δ|`. For a package `F` whose terms move by `Δ_F`, the
members' relative levels move by `W_F^{−1/2} H_F W_F^{1/2} Δ_F`. For a relation that is not a bridge,
the share `h_e` read from a move of its term and the move `m` of a cut of it, both read from the same
world state, give back the residual it holds, `r_e = −m (1 − h_e) / h_e`. After `e` is weakened to
`(1 − κ) w_e` as in Corollary 43.5, its share is `(1 − κ) h_e / (1 − κ h_e)`.

**A published change of a relation's term reads its leverage without cutting anything.** The pair's
relative price takes up the share `h_e` of the change and the relation's residual takes up the rest,
so the ratio of the price move to the change is the number that sets, by (2) and Corollary 43.1, what
a cut of the relation would rewrite. A bridge passes on the whole change and keeps none of it; a
relation with strong routes around it passes on little. With the share read from one change of the
term, a cut of the same relation from the same state returns the residual it had been holding down.
A relation already weakened passes on less of a later change, since `(1 − κ) h / (1 − κ h) < h`
whenever `h < 1`.

*Proof.* With the moved term the normal equations are `L φ^Δ = B'Wω + w_e Δ b`, so `δ = φ^Δ − φ*`
satisfies `L δ = w_e Δ b`. The right side sums to zero, so `δ = w_e Δ u` up to a constant, and
`b'δ = w_e Δ R = h_e Δ`. The residual on `e` is `(ω_e + Δ) − b'φ^Δ = r_e + (1 − h_e) Δ`. The new
residuals are `r + Δ 1_e − Bδ`, and `r'WBδ = 0` because `B'Wr = 0`, so

```
ρ^Δ²  −  ρ*²  =  2 w_e r_e Δ  +  w_e Δ²  −  2 w_e Δ b'δ  +  δ'Lδ
```

with `δ'Lδ = w_e² Δ² R = h_e w_e Δ²`, which is the fourth line. `u` is the potential of a unit
current between `i` and `j`, so Theorem 42 (3) gives `|u(q) − u(p)| ≤ R` for every pair, and
`|δ(q) − δ(p)| ≤ h_e |Δ|`. For a package the same subtraction gives `L δ = B_F' W_F Δ_F`, so
`B_F δ = B_F L⁺ B_F' W_F Δ_F`, and `B_F L⁺ B_F' = W_F^{−1/2} H_F W_F^{−1/2}`. The residual follows from
Corollary 43.1, which gives the move of the cut as `m = −(h_e / (1 − h_e)) r_e`. For the weakened
share, the parallel law in the proof of Corollary 43.1 gives `w_e R⁻ = h_e / (1 − h_e)` for the
resistance `R⁻` between `i` and `j` in `G − e`, and in the weakened graph the same law gives the share
`(1 − κ) w_e R⁻ / (1 + (1 − κ) w_e R⁻) = (1 − κ) h_e / (1 − κ h_e)`. A bridge has `R⁻` infinite and
share one at every `κ`. ∎

Corollaries 43.1 to 43.4 are algebra on Theorem 43 and on Theorems 41 and 42, and carry no check of
their own: `B105-1` and `B105-2` read every leverage, residual, gap and move they are built from.
Corollary 43.5 changes a weight where the theorem removes a relation, and `B105-3` reads it.
Corollary 43.6 changes a term, and `B105-4` and `B105-5` read it.

## 3. What the checks read

**Every criterion passes** at `--seed 105`. They run on every connected labelled graph on 2 to
6 vertices with random weights, terms and orientations, and on 200 sparse random connected graphs
of each of 16, 32 and 64 vertices; `B105-3` weakens every relation of the enumerated graphs and of
the random graphs of 16 and 32 vertices, at `κ = 0.3` and at `κ = 0.8`. Each closed form is
compared with a second fit on the graph after the cut or the weakening. The float error of that
comparison grows with the factor that multiplies the residual, `1/(1 − h_e)` for one cut,
`1/(1 − κ h_e)` for a weakening and the norm of `(I − H_F)^{−1}` for a package, so the
error is read divided by that factor, against a tolerance of `1e-9`. A relation is called a bridge
when its leverage is within `1e-9` of one, and a package disconnecting when its determinant is
within `1e-9` of zero, and each call is compared with a count of components after the cut. The
floor is measured on cuts whose terms are set to the levels the rest of the graph gives, which
move nothing.

`B105-4` moves the term of every relation that `B105-1` cuts by `0.7`, and `B105-5` moves the
terms of every package that `B105-2` cuts by `0.7` with alternating signs and reads the share of
every relation that `B105-3` weakens. A term that moves changes no weight, so these closed forms are
compared with the tolerance itself, except the residual recovered from a share and a cut, which
divides by the share and by `1 − h_e` and is read divided by the larger of `1/h_e` and `1/(1 − h_e)`.
Their floor moves every term along a potential difference, which moves every potential by exactly
that potential.

| | criterion | reading |
|---|---|---|
| `B105-1` `own_reading` | one cut | every relation of every graph cut once: `218,494` cuts in the enumeration, `28,907` of them bridges, and `37,354` on the random graphs, `2,863` of them bridges. The leverage calls the bridges and no other relation, with no mismatch. On the other `189,587` and `34,491` cuts the new level, the potential shift and the fall in `ρ²` match the second fit to `1.30e-13` and `7.02e-14` after dividing by the amplification (`7.15e-12` and `2.78e-12` before), against a floor of `3.69e-14` and `3.81e-14`. The amplification has median `2.41` and `2.27` and reaches `661` and `459`, so the relations that come closest to bridges without being bridges sit `1.5e-3` and `2.2e-3` below leverage one, six orders of magnitude clear of the tolerance |
| `B105-2` `own_reading` | a package | every pair of relations in the enumeration, `798,279`, every triple on 2 to 5 vertices, `14,657`, and `3,000` packages on the random graphs, `1,021` of two relations, `981` of three and `998` of four. The determinant calls the disconnecting packages and no others, with no mismatch: `208,517` and `785` disconnect. On the `604,419` and `2,215` that leave the graph connected, the gaps, the potential shift and the fall in `ρ²` match the second fit to `1.59e-13` and `4.36e-14` after dividing by the norm of `(I − H_F)^{−1}` (`3.67e-12` and `7.33e-13` before), against a floor of `2.75e-14` and `3.13e-14`. Among them the smallest determinant is `3.1e-5` and `4.4e-5`, four orders of magnitude clear of the tolerance, and the norm reaches `821` and `153` |
| `B105-3` `own_reading` | a weakening | every relation of every enumerated graph at `κ = 0.3` and at `κ = 0.8`, `436,988` weakenings, `57,814` of them of bridges, and `30,938` on the random graphs of 16 and 32 vertices, `2,664` of them of bridges. The new level, the potential shift and the fall in `ρ²` match the second fit to `1.04e-13` and `4.74e-14` after dividing by `1/(1 − κ h_e)` (`2.05e-13` and `1.62e-13` before), against a floor of `2.69e-14` and `2.44e-14`. `113,979` and `7,358` weakenings have `κ h_e` above one half. Off the bridges the amplification reaches `4.97` and `4.85`, below `1/(1 − κ) = 5` at `κ = 0.8`, which only the bridges reach, where it multiplies a residual of zero |
| `B105-4` `own_reading` | a term moved | every relation of every graph, its term moved by `0.7`: `218,494` moves in the enumeration, `28,907` of them of bridges, and `37,354` on the random graphs, `2,863` of them of bridges. The level, the residual, the potentials and `ρ²` match the second fit to `2.07e-13` and `3.50e-13`, and no pair of positions moves further than `h_e \|Δ\|`, against a floor of `1.74e-14` and `2.52e-14`. `3,681` and `662` moves have a share below `0.1`, and `14,883` and `2,023` relations that are not bridges a share above `0.9`. On the `189,587` and `34,491` relations that are not bridges, the share read from the two fits and the level `B105-1`'s cut leaves return the residual to `2.94e-14` and `2.19e-14` after dividing by the larger of `1/h_e` and `1/(1 − h_e)` |
| `B105-5` `own_reading` | package terms and a weakened share | every package `B105-2` cuts, its terms moved by `0.7` with alternating signs: `812,936` packages in the enumeration and `3,000` on the random graphs. The members' levels match the second fit to `8.18e-14` and `1.32e-14`, and `666,004` and `2,793` of the packages have members that interact through the off-diagonal of `H_F`. Every relation `B105-3` weakens, `436,988` and `30,938` of them, has the share `(1 − κ) h_e / (1 − κ h_e)` on the weakened graph to `9.19e-14` and `3.93e-14` |

**Each criterion has seeded failures in `--selftest`, and the self-test asserts that each seed
landed.** Two known answers come first, on random graphs of 4 and 5 vertices: the determinant
against the weighted count of the spanning trees that avoid the package, enumerated tree by tree,
for every package of one to three relations, and the leverages against `n − 1`, both to `1e-12`.
`B105-1` fails with the residual released at its own size, with the release off by one part in a
million, with `R` taken for the leverage, and with every leverage above `0.99` called a bridge. A
triangle with one relation of weight `1e7` and two of weight one gives the heavy relation leverage
`1 − 5e-8`, and the self-test requires it read as a non-bridge whose closed forms match. `B105-2`
fails with the single cuts' gaps added up, with the gaps off by one part in a million, with
disconnection read off the largest single leverage, and with `H_F` built without the weights. A
package that leaves its two sides joined only by a route of weight `1e-7` must read as connected,
with a determinant between zero and `1e-6`; the two relations of a path must read as a package of
bridges, and two opposite relations of a square as a disconnecting package whose members each have
a route around them. `B105-3` fails with `1 − h_e` where `1 − κ h_e` belongs, with `κ` dropped
from the potential shift and the fall in `ρ²`, and with the residual left on the relation off by one
part in a million; weakening all the way, `κ = 1`, must reproduce the cut of `B105-1`. `B105-4`
fails with `R` taken for the share, with the residual moved by the whole of `Δ`, with the quadratic
term of the change in `ρ²` dropped, with the share off by one part in a million, with the pairs
bounded by half the share, and with the residual recovered as `−m h_e / (1 − h_e)`; a triangle of
equal weights must pass on two thirds of a moved term and return its residual with the error read
divided by `3`, a triangle whose one relation is `1e2` times stronger than the route around it
supplies a share of `1e2 / (1e2 + 0.5)`, and a bridge must pass on the whole of a moved term.
`B105-5` fails with the off-diagonal of `H_F` dropped, with `W_F` dropped, with the package moves off
by one part in a million, with `(1 − κ) h_e` for the weakened share, and with the share left where it
was. No criterion accepts a run that did not exercise what it reads: a run with no bridge, or with
no leverage above one half, for `B105-1`; a run with no disconnecting package of replaceable members,
no package whose members interact, or no package of three relations, for `B105-2`; a run with no
bridge weakened, no `κ h_e` above one half, or one of the two fractions missing, for `B105-3`; a run
with no bridge, no share below `0.1`, no share above `0.9` or no residual recovered, for `B105-4`; a
run with no interacting package, no package of three relations, or one of the two fractions missing,
for `B105-5`. The floor is checked to move when a term is set off the level the rest of the graph
gives, for cuts and for weakenings, and when a term is moved off a potential difference, for term
moves.

## 4. Two things the checks found that the statement did not contain

**Most relations hide more than they show.** `115,148` of the `189,587` relations that are not
bridges in the enumeration (`60.7%`), and `19,971` of `34,491` on the random graphs (`57.9%`), have
leverage above one half, where a cut moves the pair's price by more than the residual the relation
showed. The reason is in (1): the leverages add to `n − 1`, so their average is `(n − 1) / E`,
above one half whenever a graph has fewer than `2(n − 1)` relations. Both families of test graphs
are that sparse on average: the enumeration, `27,475` graphs, averages `7.95` relations on `5.97`
positions, and the random graphs `62.3` relations on `37.3` positions. **In an economy with fewer
than `2(n − 1)` relations among `n` positions the relations have leverage above one half on
average, and a relation with leverage above one half shows less than half of the disagreement it
holds down.**

**A package is rarely the sum of its members.** In `590,780` of the `604,419` packages that leave
the enumerated graphs connected, and in `2,209` of the `2,215` on the random graphs, some member
carries current under a unit current between the ends of another (an off-diagonal entry of `H_F`
above `1e-6`), so the package's gaps are in general not its members' single-cut gaps. And `72,428`
of the `208,517` disconnecting packages in the enumeration (`34.7%`), and `82` of the `785` on the
random graphs (`10.4%`), are made only of relations that each have a route around them. **Asking of
each member whether it is a bridge misses a third of the packages that disconnect the enumerated
graphs, and a tenth of those that disconnect the random graphs.**

## 5. What a relation in place hides, read as an economy

**A relation's leverage is how much of the economy's connectedness runs through it.** A backbone
connects every position with no relation to spare, and by (1) a relation's leverage is the share of
backbones, each weighted by the strength of its relations, that use it. A relation with strong
routes around it has leverage near zero, and a relation that every backbone uses is a bridge.

**By Corollary 43.1, a relation in place shows only the share `1 − h_e` of the disagreement between
its own term and what the rest of the economy implies, so, for the same disagreement, the relations
an economy leans on most are the ones whose prices look most consistent.** An authority that stands ready to trade at a
fixed parity puts a large weight on one relation. Its leverage is `w_e R⁻ / (1 + w_e R⁻)`, with
`R⁻` the resistance of the routes around the parity, and it goes to one as the weight grows,
whatever those routes are. The deviation seen while the parity is defended shrinks as the defence
strengthens, and the discrepancy `D_e` between the parity and the routes around it stays where it
is. When the parity is given up, the pair moves by `h_e |D_e|`, which is `h_e / (1 − h_e)` times the
deviation seen before. Both numbers that size the move, the deviation and the leverage, are read on
the world state before the break.

**A set of measures that each leave a route open can close every route together.** By (4) a
package disconnects exactly when no backbone avoids all of its members, and `det(I − H_F)` is the
share of backbones that do. Before that share reaches zero the package already releases its
members' residuals through `(I − H_F)^{−1}`, whose norm lies between `det(I − H_F)^{−1/k}` and
`1 / det(I − H_F)`: the smallest eigenvalue of `I − H_F` is at most the geometric mean of its `k`
eigenvalues, and at least their product, since none exceeds one. So a package that leaves few
backbones can move the relative prices across it by a large multiple of the residuals they showed
before the cut. By Corollary 43.2,
measures taken one after another compound: no cut lowers the leverage of a relation still in place,
which is Rayleigh's law, and a member's own residual weighs in the package as it would in the last
cut of the sequence.

Export controls on Russia follow this shape. On other countries' exports to Russia, the average
effect of listing a good on its unit price was 0.21 log points in 2022, 0.30 in 2023 and 0.71 in
2024, and the coefficients of the first months are not significant (Korhonen and Simola 2025).
The largest step came in the year that measures aimed at the routes around the listed goods took
effect: a US order of 22 December 2023 authorising sanctions on foreign financial institutions that
facilitate transactions involving Russia's military-industrial base (Executive Order 14114), and an
EU requirement, from 20 March 2024 for new contracts, that exporters bar re-export to Russia
(Article 12g of Council Regulation (EU) No 833/2014).

**By Corollary 43.5, a measure that makes a relation dearer without removing it rewrites through
the same leverage, and by less than `κ / (1 − κ)` times the residual the relation shows.** A sanction
on the banks that settle payments along a route, or a licence that lengthens a trade, lowers the
weight of a relation and leaves the relation in place. However much the economy leans on that
relation, such a measure moves prices by a bounded multiple of what was visible before it; a closure
has no bound.

The routes around Russia's listed imports ran through countries that were never sanctioned as
states. After March 2022, EU exports of sanctioned goods to Armenia, Kazakhstan and the Kyrgyz
Republic rose by an extra 30 per cent relative to other goods (Chupilkin, Javorcik and Plekhanov
2023). The measures that followed weakened those routes before closing any of them: the order of
22 December 2023 above; the designation of a bank in the Kyrgyz Republic by the United States in
January 2025 (OCCRP 2025) and of another by the United Kingdom in August 2025 (24.kg 2025); and an
EU transaction ban on banks and traders in Tajikistan, the Kyrgyz Republic, the United Arab Emirates
and Hong Kong, and on banks in Belarus and Kazakhstan (Council of the European Union 2025). The first
closure of a route by name came on 23 April 2026, when the EU prohibited exports of machining centres
for working metal (HS 8457 10) and of data transmission equipment including switching and routing
apparatus (HS 8517 62) to the Kyrgyz Republic (Council Regulation (EU) 2026/506, under Article 12f
of Regulation 833/2014). The relation it closed was thin. EU exports of HS 8517 62 to the Kyrgyz
Republic fell from EUR 485 thousand a month in 2025 to EUR 45 thousand a month in May to July 2026,
and in 2025 they had been 0.22 per cent of EU exports of that code to Russia, Belarus, Armenia,
Azerbaijan, Georgia, Kazakhstan, the Kyrgyz Republic, Mongolia, Tajikistan, Uzbekistan, China, Hong
Kong, Türkiye and the United Arab Emirates together; EU exports of HS 8457 10 to the Kyrgyz Republic
had stopped before the prohibition (Eurostat 2026).

**A bridge sits at the other end of the scale.** Russian gas reached the Transnistrian region of
Moldova only through Ukraine, and none arrived after transit through Ukraine ended on 1 January 2025;
on 27 January the EU put up the money for gas bought in Bulgaria and Romania and carried in by
another route, a new relation (European Commission 2025). For the region the relation was a bridge,
and its cut left no price to compare. For the rest of Moldova, which had bought about 70 per cent of
its electricity from the region's power plant until 31 December 2024 and imported nearly half from
Romania from 1 January, the regulated electricity tariffs rose by 75 and 65 per cent on 3 January
(Interfax-Ukraine 2025).

**In July and August 2026 each side of the war closed the other's grain routes by sea, and the
rewrite fell at the ends of the closed relations.** On 23 July Ukrainian officials reported no
traffic on the Black Sea corridor for the first time since 2023, after strikes on 28 commercial
vessels in a month, with the ports open (Maritime Executive 2026). Food wheat at the ports of Odesa
fell from USD 221 a tonne on 2 June to USD 198 in the last week of July. In the week to 20 July corn
at those ports fell USD 4 to USD 208 while corn at the western border crossing of Chop rose USD 7 to
USD 234, and the land routes carried 1 to 1.2 million tonnes a month against the 5 to 6 million the
sector needs (Spike Brokers 2026). On Russia's side, loading at the shallow-water Black Sea ports was
restricted from 10 July (Reuters 2026a), navigation in the Sea of Azov was suspended in July, the
grain terminal at Taman stopped in late July, and the grain terminals of Novorossiysk stopped in the
second week of August, taking more than 90 per cent of the basin's grain export capacity offline
(The Moscow Times 2026). Third-class wheat in European Russia fell from RUB 13,125 a tonne in the
week to 20 July to RUB 8,850 in the week to 24 August, RUB 2,600 of that in the last week; on
24 August wheat for loading in late September was quoted at USD 210 a tonne in the Black Sea and
about USD 248 in the Baltic, and one of the consultancies reporting the prices called its Black Sea
quotes largely notional for lack of vessels (Reuters 2026a, 2026b). The positions at the two ends of
each closed relation moved apart, and the routes still open were repriced against the closed ones:
the western border above Odesa, the Baltic above the Black Sea. The Russian closures came in three
steps, which by Corollary 43.2 can only have raised the weight of the last. The same weeks also
carried the harvest and other shocks, so these prices locate the rewrite and leave its size open.

**By Corollary 43.3 the rewrite stays inside the blocks that hold the cut relations.** No price
moves inside a part of the economy that lies outside those blocks, a region behind its one market
town or a supplier behind its one buyer, and under a single cut such a part moves against the rest
exactly as the position through which it reaches the block does.

[`b103_time_reachability.md`](b103_time_reachability.md) read the third premise from before an
action that adds a relation. **Read from before an action in both directions, an addition's rewrite
is bounded by the discrepancy the pricer can see, and a cut's rewrite is a multiple of the residual
the pricer can see.** The multiple is set by the leverage, it is largest where the economy depends
on the relation most, and at a bridge the comparison itself goes.

**Corollary 43.4 prices the absence of a single price system when the action itself is uncertain.** A
pricer who must quote one number before a reform, a sanction or the end of a parity, which happens with
probability `π`, is off on average by at least `π (1 − π)` times the square of the rewrite, most at even
odds. The number that does best is the probability-weighted middle of the two worlds' levels, and it is
a level of neither.

**Corollary 43.6 reads the leverage before anything is cut.** A tariff raised, a fee added or a
parity moved in a step is a term moved in place: the pair's relative price takes up the share `h_e`
of the step and the relation's residual takes up the rest. The ratio of the price move to a
published step is therefore the number that, by Corollary 43.1, sizes what closing the relation
would rewrite, and after a closure the move it makes, read with that ratio, returns the disagreement
the relation had been holding down. A relation already weakened passes on less of a later step. On China's 2018 tariff on US soybeans the share read this way is 0.54 to 0.75 across four window settings, with Paranaguá rising against the Gulf in all four ([`b115_soy_tariff.md`](b115_soy_tariff.md)). On China's 2018 deposit on US sorghum, sorghum fell against Gulf corn at the deposit and rose back at its end, at both US export quotes and in all four settings ([`b115_sorghum_deposit.md`](b115_sorghum_deposit.md)).

## 6. Placement

**A.** The projection is a weighted least-squares regression of the terms on potential differences,
with each relation an observation. The leverage, the deleted residual `r_e / (1 − h_e)`, the change
in the fit and in the residual sum of squares when one observation is deleted, and their versions
for a group through `(I − H_F)^{−1}`, are regression diagnostics (Cook 1977; Belsley, Kuh and
Welsch 1980; Cook and Weisberg 1982). That an edge's leverage is the probability that a weighted
random spanning tree contains it, and the matrix-tree theorem, are Kirchhoff's (1847); that the
leverages of a connected graph add to `n − 1` is Foster's theorem (Foster 1949); and that
`det(I − H_F)` is the probability that the tree avoids `F` is the avoidance case of the transfer
current theorem (Burton and Pemantle 1993). The low-rank updates are those of Sherman and Morrison
(1950) and Woodbury (1950), and Rayleigh's law and the blocks are used as in
[`b103_time_reachability.md`](b103_time_reachability.md) and
[`b104_action_footprint.md`](b104_action_footprint.md) (Doyle and Snell 1984). Applied to power
flows with the injections held fixed, the same single and group corrections are the line outage
distribution factors of transmission contingency analysis: with susceptances as the weights, a
line's self power transfer distribution factor is its leverage; the share of an outaged line's flow
that moves onto another line is the other line's transfer factor for a transfer between the
outaged line's ends, divided by one minus the outaged line's self factor; and simultaneous outages
are read through the inverse of `I − PTDF` on the outaged set, which is singular when the outages
split the network into islands, the zero case of (4) (Guler, Gross and Liu 2007). Changing an
observation's weight instead of deleting it is a case-weight perturbation (Cook 1986), and a finite
change of weight is again a rank-one update. Moving an observation's value moves every fitted value
through the hat matrix, its own by its leverage, which is the reading of the hat matrix as the
influence of each observed value on each fitted value (Hoaglin and Welsch 1978); with weights the
matrix that takes terms to levels is `W^{−1/2} H W^{1/2}`, whose diagonal is still the leverage.

**D.** That in a price graph a relation's leverage is the share of weighted backbones through it,
equal to one exactly at a bridge, whose cut removes the comparison itself; that a relation in place
shows only the share `1 − h_e` of the discrepancy between its term and the rest of the graph, so
that, read before the action, a cut rewrites `h_e / (1 − h_e)` times what it can see while an
addition rewrites less than what it can see; that a package of relations disconnects exactly when no
weighted backbone avoids it, including packages whose every member has a route around it, and
otherwise releases its residuals through `(I − H_F)^{−1}`, each member's own residual weighted as in
the last cut of a sequence and never below its weight when cut alone; that a relation weakened in place rewrites through the same
leverage, by less than `κ / (1 − κ)` times the residual it shows, so that only closing a relation
removes the bound; that a change of a relation's term passes to its pair's price in the share `h_e`, so
that a published change reads the leverage before anything is cut and a later cut returns the residual
the relation held down; that before an action that may not happen, no single price beats an expected squared miss of
`π (1 − π)` times the square of the rewrite, and the only price that reaches it is a middle value that
belongs to neither world; and that the rewrite stays
inside the blocks that hold the cut relations. **What a cut will rewrite is priced on the world
state before it, from two numbers the fit already carries for every relation: its residual and its
leverage.**

**C is empty and this station cannot produce it**: it reads no data, so no point prediction of any
other account is scored here.

## 7. Scope

Positive weights, relations cut from a connected graph, weakened in place or with their terms moved
in place, and the terms on every other relation held where they were. A graph with several components is read one component at a time. Parts (1) to (5)
hold for every choice of weights and terms. Several packages compose one at a time, each read on
the graph as it stands at that step. The checks use simple graphs; the statement holds with
parallel relations. Nothing here measures a price, a relation or a world state in any economy; the prices and volumes
in section 5 are cited from their sources.

## References

- 24.kg (2025). UK imposes sanctions on Kyrgyzstan's Capital Bank and crypto exchanges. News
  agency 24.kg, August 2025.
- Belsley, D. A., Kuh, E. and Welsch, R. E. (1980). *Regression Diagnostics: Identifying
  Influential Data and Sources of Collinearity*. Wiley.
- Burton, R. and Pemantle, R. (1993). Local characteristics, entropy and limit theorems for
  spanning trees and domino tilings via transfer-impedances. *Annals of Probability* 21:
  1329–1371.
- Chupilkin, M., Javorcik, B. and Plekhanov, A. (2023). The Eurasian roundabout: Trade flows into
  Russia through the Caucasus and Central Asia. *EBRD Working Paper* 276. European Bank for
  Reconstruction and Development.
- Cook, R. D. (1977). Detection of influential observation in linear regression. *Technometrics*
  19(1): 15–18.
- Cook, R. D. (1986). Assessment of local influence. *Journal of the Royal Statistical Society,
  Series B* 48(2): 133–169.
- Cook, R. D. and Weisberg, S. (1982). *Residuals and Influence in Regression*. Chapman and Hall.
- Council of the European Union (2025). 19th package of sanctions against Russia: EU targets
  Russian energy, third-country banks and crypto providers. Press release, 23 October 2025.
- Council of the European Union (2026). Council Regulation (EU) 2026/506 of 23 April 2026 amending
  Regulation (EU) No 833/2014 concerning restrictive measures in view of Russia's actions
  destabilising the situation in Ukraine.
- Doyle, P. G. and Snell, J. L. (1984). *Random Walks and Electric Networks*. Carus Mathematical
  Monographs 22. Mathematical Association of America.
- European Commission (2025). The EU offers emergency support to tackle the energy crisis in
  Moldova. News item, 27 January 2025.
- Eurostat (2026). EU trade since 1988 by HS2-4-6 and CN8, dataset DS-045409 (Comext): exports of
  the EU27 by partner, monthly, value in euros. Updated 15 September 2026, read 16 September 2026.
- Foster, R. M. (1949). The average impedance of an electrical network. In *Contributions to
  Applied Mechanics (Reissner Anniversary Volume)*, 333–340. Edwards Brothers.
- Guler, T., Gross, G. and Liu, M. (2007). Generalized line outage distribution factors. *IEEE
  Transactions on Power Systems* 22(2): 879–881.
- Hoaglin, D. C. and Welsch, R. E. (1978). The hat matrix in regression and ANOVA. *The American
  Statistician* 32(1): 17–22.
- Interfax-Ukraine (2025). Moldova raises electricity, heating tariffs. 3 January 2025.
- Kirchhoff, G. (1847). Ueber die Auflösung der Gleichungen, auf welche man bei der Untersuchung
  der linearen Vertheilung galvanischer Ströme geführt wird. *Annalen der Physik und Chemie*
  148(12): 497–508.
- Korhonen, I. and Simola, H. (2025). From sanctions to price surges: The dynamics of Russia's
  import prices. *BOFIT Discussion Papers* 8/2025. Bank of Finland Institute for Emerging
  Economies.
- Maritime Executive (2026). Shipping suspended on Ukraine's Black Sea corridor due to increased
  attacks. 23 July 2026.
- OCCRP (2025). U.S. sanctions Kyrgyz bank over alleged Russian sanctions violations. January 2025.
- Reuters (2026a). Russian wheat export prices soar amidst escalating hostilities. 20 July 2026, as
  carried by MarineLink.
- Reuters (2026b). Russian wheat prices drop, shipments to reach 16-year low. 24 August 2026, as
  carried by Maritime Professional.
- Sherman, J. and Morrison, W. J. (1950). Adjustment of an inverse matrix corresponding to a
  change in one element of a given matrix. *Annals of Mathematical Statistics* 21(1): 124–127.
- Spike Brokers (2026). Weekly notes on Ukrainian port and border grain prices, 2 June, 20 July and
  27 July 2026, as published by Ukrainian Shipping Magazine.
- The Moscow Times (2026). Ukrainian strikes halt most Russian grain exports in the Black Sea.
  17 August 2026.
- Woodbury, M. A. (1950). *Inverting Modified Matrices*. Memorandum Report 42, Statistical
  Research Group, Princeton University.
