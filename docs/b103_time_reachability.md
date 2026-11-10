# B103: what an action that changes the world state rewrites in the prices set before it

**RUN: 2026-09-15. Statement and proof below. Checks in
`experiments/b103_time_reachability.py`, record `results/b103_time_reachability.json`, which
carries the configuration it ran under. Paper station: zero data. B84's record is read as it
stands, and its tableaux are redrawn from B81's generator with the seed B84 recorded, so the
fourth check reads the edges B84 wrote down.**

## 0. The question this station answers

The source manuscript reaches the conclusion that current prices cannot direct long-run
allocation by two independent routes. The spatial route is non-integrability at one world
state, carried by Theorems 1 and 5 ([`b1_theorem.md`](b1_theorem.md) sections 4 and 14): loops
need not sum to zero, and the distance from the field to the nearest single index has a closed
form. The temporal route is the third premise of the manuscript's preamble: pricing an action
presupposes the world state its price system belongs to, and when the point of the action is
that it may change that state, no single price system is available.

**The temporal route is a statement about reachability.** A holder carries a position forward
through an action and never back, and no transaction joins the world in which an action was
taken to the world in which it was not. World states therefore sit on a tree rooted at the
present. A tree has no cycle, so no loop runs through two world states, and a loop sum that
does not exist is neither zero nor non-zero. What remains is the question `H⁰` asks: which
comparisons a graph can make, and what an action does to them.

**This station answers that question in closed form.** An action that joins two positions
either creates a comparison the graph did not have, or rewrites one it had, and the share it
rewrites is set by one number of the graph before the action: the effective resistance
between the two positions. The manuscript's own instance of the premise is a road built into
a region, after which the prices computed before the road no longer apply. Theorem 41 says how
much of them no longer applies.

## 1. Setup

**The graph.** `G` has `n` vertices, the positions, and directed edges `e = (i → j)` carrying
weights `w_e > 0` and terms `ω_e`. The inner product is B84's weighted one,
`<a, b>_W = a'Wb` with `W = diag(w_e)`. The nearest potentials and the distance are

```
φ*  ∈  argmin_φ  Σ_e  w_e ( ω_e − (d⁰φ)_e )²,        ρ²  =  the minimum
```

and they solve `L φ = d⁰'Wω`, with `L = d⁰'Wd⁰` the weighted Laplacian. Every nearest
potential is one of them plus a constant on each component. **So two positions `i` and `j`
have a well-defined relative level `φ(j) − φ(i)` exactly when they share a component**, which
is the statement that `b = e_j − e_i` lies in the range of `L`. Across components the relative
level is the difference of two independent anchors.

**The action** adds one edge `e = (i → j)` with weight `w_e` and term `ω_e`. Two numbers of
`G` govern what it does:

```
D  =  ω_e − ( φ*(j) − φ*(i) )      the new term minus the relative level G assigns
R  =  b' L⁺ b                      the effective resistance between i and j, each edge conducting w
```

`D` is defined when `i` and `j` share a component, and `R` is then finite. `R` is infinite when
they do not.

**Where time enters.** Inside one world state, claims move across dates in both directions:
[`b63_trilemma.md`](b63_trilemma.md) section 1 carries lend and borrow edges between `(k, t)`
and `(k, t+1)`, loops through dated positions close, and their sums are loop sums of the
ordinary kind. That is spatial, and this station leaves it where it is. What this station
treats as time is the step from one contract graph to the next: the projection on `G` against
the projection on `G + e`.

## 2. Theorem 41

**(1) An action that joins two components creates a comparison and rewrites nothing.** If `i`
and `j` lie in different components of `G`, then before the action `φ(j) − φ(i)` takes every
real value across the nearest potentials, and after it every nearest potential gives exactly
`ω_e`. Every other residual is unchanged, so `ρ²` is unchanged. `b₁ = E − V + c` holds and `c`
falls by one.

**(2) An action inside a component rewrites a fixed share of the old comparison.** If `i` and
`j` share a component, put `θ = w_e R / (1 + w_e R)`. Then

```
ρ²  rises by                              w_e D² / (1 + w_e R)
every potential moves by                  ψ  =  ( w_e D / (1 + w_e R) ) · L⁺ b,  up to a constant per component
the relative level of i and j moves by    θ D
the new edge keeps the residual           (1 − θ) D  =  D / (1 + w_e R)
```

and `b₁` rises by one while `c` holds.

**(3) The two cases are one formula.** As `R → ∞`, `θ → 1`, and the rise in `ρ²` and the new
edge's residual go to zero: that is (1). A bridge of conductance `ε` between the part holding
`i` and the part holding `j` realises the limit. It gives `R = R_A + 1/ε + R_B`, with `R_A` the
resistance from `i` to the bridge's end on its side and `R_B` likewise for `j`; it leaves `D`
the same for every `ε > 0`; and at `ε = 0` the case is (1). As `R → 0`, `θ → 0`: the graph ties
`i` to `j` so tightly that the action moves nothing, and the whole of `D` stays on the new edge.
**`R` never rises when a conductance rises or an edge is added**, which is Rayleigh's
monotonicity law. Adding a relation `(x, y)` of conductance `c` inside the component lowers it
by exactly `c Δ² / (1 + c R_xy)`, where `Δ` is the difference in potential between `x` and `y`
under a unit current from `j` to `i` and `R_xy` is their own resistance. **So no relation
already tying `i` to `j` raises the share that an action joining them rewrites, and every
relation that carries current between them lowers it.**

**Proof.** (1) `b` sums to `−1` on the component of `i` and to `+1` on that of `j`, so it lies
outside the range of `L`, and adding a constant `t` on the component of `j` moves
`φ(j) − φ(i)` by `t` while changing no residual. After the action `e` is the only edge between
the two components. Adding `t` on the component of `j` then changes the residual on `e` alone,
so the minimum puts that residual at zero and leaves the rest of the fit where it was. `E`
rises by one and `c` falls by one.

(2) `b` lies in the range of `L`, so `L L⁺ b = b`. The normal equations after the action are
`(L + w_e b b') φ = d⁰'Wω + w_e ω_e b`. With `φ = φ* + κ L⁺b` the left side is
`d⁰'Wω + b · ( w_e (φ*(j) − φ*(i)) + κ (1 + w_e R) )`, which equals the right side at
`κ = w_e D / (1 + w_e R)`. So `b'ψ = κR = θD`, and the new edge keeps `D − θD`. For `ρ²`, the
old edges carry the residual `r* − d⁰ψ` with `r* = ω − d⁰φ*`. Since `d⁰'W r* = 0`, they
contribute `ρ*² + ψ'Lψ = ρ*² + κ²R`; the new edge contributes `w_e D² / (1 + w_e R)²`; and the
total exceeds `ρ*²` by `w_e D² / (1 + w_e R)`.

(3) The limits are read off (2). Every path from `i` to `j` crosses the bridge, so the
resistances add in series. By the argument of (1) the bridge's residual is zero in every
nearest potential whatever its weight, so `φ*(j) − φ*(i)`, and `D` with it, do not depend on
`ε`. For the relation `(x, y)`: adding it changes `L` by `c b_xy b_xy'`, with `b_xy` in the
range of `L`, so the rank-one algebra of (2) lowers `b'L⁺b` by `c (b_xy' L⁺ b)² / (1 + c R_xy)`,
and `b_xy' L⁺ b` is the potential difference `Δ` under the unit current. That fall is never
negative, which is Rayleigh's law. ∎

**The same statement as a circuit.** Read `1/w_e` as the new edge's resistance and `D` as a
source in series with it. The source drives the current `D / (R + 1/w_e)` around the loop the
new edge closes, which is `κ`. The potentials move as a current `κ` injected at `j` and drawn
at `i`, which is `ψ`. The drop across the old graph is the share `R / (R + 1/w_e) = θ` of `D`,
and `ρ²` rises by the power the source delivers, `D² / (R + 1/w_e)`. **So the graph before an
action holds its comparisons the way a network holds a voltage: where it ties a pair loosely,
the old relative level gives way to most of a new discrepancy, and where it ties a pair
tightly, the old level barely moves and the discrepancy stays on the new edge.** The share
depends on `w_e` and `R` only through their product, so a weak action on a loosely tied pair
and a strong action on a tightly tied pair rewrite the same share.

### Corollary 41.1: B84-4's ladder is (2) with the weight walked down

B84-4 took a cycle edge of a tableau, set its weight to `w` with every other weight one, and
recorded the largest change in any country parity against the fit with that edge deleted, at
`w = 1e-1, 1e-3, 1e-6, 1e-9, 1e-12`. That is (2), with the deleted tableau as the graph before
the action and the edge as the action. The parities are the potentials on the country
vertices measured from the first country, so the recorded distance is

```
d(w)  =  |D| · s · w / (1 + wR),        s  =  max over countries | (L⁺b)_country − (L⁺b)_first |
```

and the ratio B84 printed between successive rungs, `(d_a / d_b) / (w_a / w_b)`, is

```
(1 + w_b R) / (1 + w_a R)
```

**The distance is linear in `w` as `w → 0`, which is B84's reading, and above that it bends by
the factor `1/(1 + wR)`.** On B84's ladder the first step, from `1e-1` to `1e-3`, carries almost
all of the bend, and the edge with the largest `R` bends furthest.

### Corollary 41.2: an action moves a level toward its own term and never past it

After an action inside a component, the relative level of `i` and `j` is

```
(1 − θ) · ( φ*(j) − φ*(i) )  +  θ · ω_e
```

a weighted average of the level before the action and the new edge's own term, with the
weight `θ` on the term. So the level moves toward the new term and stops short of it, and the
direction of the old level reverses only when the new term points the other way and `θ` exceeds
`|φ*(j) − φ*(i)| / (|φ*(j) − φ*(i)| + |ω_e|)`. **An edge whose own term runs with the old
gradient changes the gradient's size and cannot change its direction.** The manuscript says two
things about a road built into a region that a gradient already drains: that the road makes the
prices computed before it inapplicable, and that the road revives the region only once the
gradient has first been changed by something else. Corollary 41.2 is the statement that these
are one fact. The road rewrites the level by `θ D`, and the reversal needs the road's own term to
point inward already.

### Corollary 41.3: the two routes are independent, and inside a component one number drives both

Take a field that is exact before the action, `ρ² = 0`, so that current prices are fully
integrable.

- **Across components the routes do not meet.** A bridge action leaves `ρ² = 0`, and the
  comparison it creates had no value before it: by (1), every real number was some nearest
  potential's answer. Pricing a position in a world state the pricer is not in is this case,
  which is why valuations that borrow a price from a counterfactual world can disagree without
  bound, with nothing in the prices to pick between them.
- **With no action they do not meet either.** A non-exact field on a fixed graph has `ρ² > 0`,
  and no world state changes.
- **Inside a component they meet at `D`.** Every cycle through the new edge closes with the sum
  `D`, because the field was exact; the field after the action sits at
  `ρ² = w_e D² / (1 + w_e R)` from exact; and the old prices are rewritten by `θ D`. **An action
  that rewrites a relative price inside a connected economy creates, in the world state it
  produces, a loop whose sum is `D`, the discrepancy of which the old price absorbs the share
  `θ`.**

Corollaries 41.2 and 41.3 are algebra on (1) and (2) and carry no check of their own: `B103-1`
and `B103-2` read every quantity they are built from.

## 3. What the checks read

**Four criteria, all passing** at `--seed 103`.

| | criterion | reading |
|---|---|---|
| `B103-1` `own_reading` | joining two components | every labelled simple graph on 2 to 5 vertices with random weights and terms, every missing edge added once: `1,606` additions join two components and `3,719` do not. On every one of the first kind the relative level is fixed by no nearest potential before the action and by all of them after it, at the new term to `1.0e-14`; `ρ²` moves by at most `3.6e-15`; `b₁` holds and `c` falls by one. On every one of the second kind the level was already fixed, `b₁` rises by one and `c` holds |
| `B103-2` `own_reading` | the closed forms | `600` random weighted connected graphs on 8, 16 and 32 vertices, one missing edge with random weight and term added to each: the rise in `ρ²`, the potential shift, the level's move and the new edge's residual all match the numerical projection, worst `4.1e-14`, against a floor of `2.8e-14` measured as the same action with `D` set to zero. Across these graphs `R` runs from `0.16` to `12.7` and the share rewritten from `0.018` to `0.958`, with medians `0.35` to `0.41` by size |
| `B103-3` `own_reading` | one formula | a bridge walked from conductance `1` to `1e-4`: `R` from `2.703` to `10001.7`, the share measured from the two fits from `0.7299` to `0.999900`, the rise in `ρ²` from `0.55` to `2.0e-4`, the new edge's residual from `0.39` to `1.4e-4`, and `D` constant to `4.7e-12`. With the bridge removed the level is pinned to `1.2e-15` and `ρ²` does not move. A complete graph on eight vertices less the joined pair, weights walked from `1` to `1e4`: `R` from `1/3` to `3.3e-5`, the measured share from `0.25` to `3.3e-5`. On every rung of both walks the measured share equals `w_e R / (1 + w_e R)` to `1.8e-15` |
| `B103-4` `known_answer` | B84-4's ladder | the ten tableaux come back with the same ten edges, with `R` from `0.603` to `1.800` computed from each tableau, and the closed form matches all fifty recorded distances to `5.3e-15`. The first two ratios of every edge match `(1 + w_b R)/(1 + w_a R)`: first steps `0.8490` to `0.9437`, second steps `0.9982` to `0.9994`. On the last two ratios the closed form bends by at most `1.8e-6`, below the float noise of the distances they divide. **B84's printed low end, `0.8490`, is the first step of the edge with `R = 1.800`, and its high end, `1.0025`, is a last step** |

Figures below `1e-11` in this table are what the run printed on the build that first wrote the
record; the record carries the tolerances only, because those digits belong to the BLAS build.
A Windows build writes the same record byte for byte and prints `9.8e-15` and `3.6e-15` for
`B103-1`, `3.2e-14` against the same floor `2.8e-14` for `B103-2`, and for `B103-3` `D` constant
to `2.0e-12`, the level pinned to `2.6e-15` and the share matching to `1.9e-15`. `B103-4` prints
`5.3e-15` on both.

**Each criterion has a seeded failure in `--selftest`.** Where a seed could land on nothing, a
fixture without a reachable pair or new edges all of weight one, the self-test asserts that it
landed. A reachable pair read as unreachable, and a broken component count, fail `B103-1`.
The new edge's weight dropped from the closed forms, and the residual written as the moved
share, fail `B103-2`. The residual's share read as the level's fails `B103-3`. The full tableau
taken as the graph before the action, and the ratio inverted, fail `B103-4`.

## 4. Two things the checks found that the statement did not contain

**B84's printed spread is curvature at one end and float noise at the other.** B84 read its
ladder as linear and printed the ratio's range as `0.85` to `1.00`. Corollary 41.1 splits that
range exactly. The low end is `(1 + w_b R)/(1 + w_a R)` on the first step at the largest
resistance among B84's edges, `R = 1.800`. The second step's ratios sit within `1.8e-3` of one, as linearity says. The high
end is the last step of an edge whose distances there are `1.6e-10` and `1.6e-13`, where one
digit of float noise moves the ratio by parts in a thousand. **What is left of the range once
the floor is set aside is one number per edge, `R`.**

**The potentials are solved on the incidence matrix.** `B103-1` to `B103-3` solve each projection by a
singular value decomposition of the weighted incidence matrix `W^{1/2} d⁰`, whose condition
number the Laplacian squares. With a bridge of conductance `1e-4` the two condition numbers are
about `9e2` and `7e5`, and `D` reads constant across the walk to `5e-12` on the incidence matrix
and to `4e-11` through the Laplacian (`2.0e-12` and `1.5e-10` on the Windows build). **Reading (3) near its limit is a question about a
nearly disconnected graph, and on such a graph the normal equations spend digits the question
needs.**

## 5. Two ways a measure fitted on one world state stops describing the next

Theorem 41 separates them. **The terms on existing edges can move**, by misreport or by a true
change in what they record, which moves the fit through `L⁺ d⁰'W` with the graph fixed. **Or the
graph can change while every term on the old edges stays where it was**, which moves the fit by
(2). The second needs nobody to game anything and nothing already measured to change. It needs an action that joins two positions, its size is `θ D`, and by
(3) the share it rewrites is largest where the old graph was thinnest, while where the old graph
was disconnected the whole comparison is new.
A target set on the projection before the action is off by `θ D` after it, whether or not
anyone games it.

The performance-measurement literature draws its line at manipulation. On the side without it,
it names performance improving under an unchanged indicator: "indicators lose their sensitivity
in detecting bad performance. In fact, everybody has become so good at what they do that the
indicator becomes obsolete" (van Thiel and Leeuw 2002, p. 270). It calls that positive learning,
against the perverse learning of those who learn what is measured and manipulate their
assessments. **Theorem 41 adds a second mechanism on the side without manipulation, a change of
graph with every old term where it was, and gives it its size, `θ D`.**

## 6. Placement

**A.** The effective resistance, Rayleigh's law and the rank-one solution of the normal
equations are circuit theory and linear algebra, used here where they are needed: resistance
as `b'L⁺b` (Klein and Randić 1993), monotonicity (Doyle and Snell 1984), and the rank-one update
(Sherman and Morrison 1950). That a measure can decline with nobody manipulating it is the
framework's reading and the performance-paradox literature's (van Thiel and Leeuw 2002; Meyer
2003).

**D.** That the temporal route, the manuscript's third premise, is an `H⁰` statement; that an
action joining two positions rewrites exactly the share `w_e R / (1 + w_e R)` of the discrepancy,
with `R` the effective resistance of the graph before it; that joining two components is that
formula's endpoint; that the low end of B84-4's printed spread is that formula's curvature and its
high end float noise; that an action moves a level toward its own term and reverses it only when
that term already points the other way; and that inside a component one number, `D`, sets both
the loop an action creates and the rewrite of old prices, `θ D`. **The
size of the drift is the part no account of a measure's decline supplies, because nothing in
those accounts has a graph in it.**

**C is empty and this station cannot produce it**: it reads no data, so no point prediction of
any other account is scored here.

## 7. Scope

Positive weights, one edge added at a time, and the terms on every other edge held where they
were. Several actions compose one update at a time, each with the resistance of the graph as
it stands at that step. The tree of world states is the premise of section 0, taken as given;
claims moved across dates inside one world state belong to the spatial side. Nothing here
measures a price, an action or a world state in any economy.

## References

- Doyle, P. G. and Snell, J. L. (1984). *Random Walks and Electric Networks*. Carus
  Mathematical Monographs 22. Mathematical Association of America.
- Klein, D. J. and Randić, M. (1993). Resistance distance. *Journal of Mathematical Chemistry*
  12: 81–95.
- Meyer, M. W. (2003). *Rethinking Performance Measurement: Beyond the Balanced Scorecard*.
  Cambridge University Press.
- Sherman, J. and Morrison, W. J. (1950). Adjustment of an inverse matrix corresponding to a
  change in one element of a given matrix. *Annals of Mathematical Statistics* 21(1): 124–127.
- van Thiel, S. and Leeuw, F. L. (2002). The performance paradox in the public sector. *Public
  Performance & Management Review* 25(3): 267–281.
