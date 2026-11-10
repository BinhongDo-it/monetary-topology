# B136: adding a channel, on the price side and on the money side, is one rank-one update

**RUN: 2026-09-27; rerun 2026-10-06 (every reading stored before is unchanged). Statement and proof
below. Checks in `experiments/b136_channel_bridge.py`, record
`results/b136_channel_bridge.json`, which carries the configuration it ran under. Paper station: zero
data. The graph helpers are imported from B103; the money map, its stationary vector and its
derivative from `experiments/a45_duration_levers.py`.**

## 0. The question this station answers

B103 reads what adding one relation does to prices: the potentials move by
`w D / (1 + w R) · L⁺b`, with `R` the effective resistance between the two ends
([`b103_time_reachability.md`](b103_time_reachability.md) section 2). B105 reads cutting
([`b105_cutting_relations.md`](b105_cutting_relations.md)). A45 reads the same kind of carrier from
the money side: where new claims settle is the stationary vector `π` of a one-round map `B`, and its
derivative with respect to a part of the map is `Z (dB) π` (the A45 section of `RESULTS.md`).

**The question is whether the two sides say the same thing about one act, a channel opened or
closed.** They do, and they part in two places. The money map's response to one route is an exact
rank-one update of the same shape as B103's, with the chain's fundamental matrix in the place of the
Laplacian's pseudoinverse and first-passage times in the place of resistance. On a reversible chain the
two are the same numbers. The money side keeps only half of B103's monotonicity, and one route can
never disconnect it.

## 1. Setup

`B` is a real square matrix with `ℓB = ℓ`, `ℓ` the mass functional (one on nodes that hold claims, zero on
any bookkeeping state), eigenvalue one simple, `Bπ = π`, `ℓπ = 1`. Its fundamental matrix is
`Z = (I − B + πℓ)⁻¹`. An action changes `B` to `B' = B + u v'` with `ℓu = 0`: claims change direction and
none are created. On a nonnegative chain, column `x` of `B` is where a unit at `x` goes, `P(x → y) = B[y, x]`,
and `m(x → i)` is the mean first-passage time from `x` to `i`, `m(i → i) = 0`. The statements written in `m`,
(2), (4) and Corollary 44.2, are for an irreducible nonnegative chain: every stationary share is positive and
every `m` is finite.

**A rerouting at `k`** moves `δ` of `k`'s outflow from its current destinations `r` (column `k`) to `j`:
`u = δ (e_j − r)`, `v = e_k`.

**A45's map.** One round is wages, then spending. On the block of trading nodes and one spending
state, `A = [G; s'] M`, where `M = [W | c]` is the wage step with the bill column, `G = I − diag(q) + R'diag(q)`
is spending (`q` the spending rates, `R` the row-normalised routes) and `s` the layer-two spending
rates. Only `G` depends on the routes.

## 2. Theorem 44

**(1) The exact finite step.** If eigenvalue one of `B'` is simple,

```
π'  =  π  +  (v'π) / (1 − v'Zu) · Zu
```

and the first-order term `(v'π) Zu` is `Z (dB) π` with `dB = u v'`.

**(2) The first-passage form.** On an irreducible nonnegative chain, for a rerouting at `k` towards `j`,

```
( Z (e_j − r) )_i  =  π_i ( m(r → i) − m(j → i) ),      m(r → i) = Σ_l r_l m(l → i)
```

so node `i` gains in proportion to its own share and to how much sooner claims reach it from the new
destination than from the old ones.

A reducible nonnegative chain can meet the setup of section 1 and still have a transient node, with
stationary share zero and an infinite passage time; the right side then has no value and the move is read
from (1). With columns as destinations, `B = [[1, ½], [0, ½]]` has `π = (1, 0)`. Sending a quarter of node
0's outflow to node 1 gives `π' = (⅔, ⅓)` with denominator `3/2`: (1) returns it from `Z(e₁ − e₀) = (−2, 2)`,
while `π₁ m(0 → 1)` is zero times infinity.

**(3) The reversible limit.** For the random walk on a weighted undirected graph (`B = W D⁻¹`,
`d` the weighted degrees, `vol = Σ d`), `m(a → b) + m(b → a) = vol · R_ab` and
`m(a → b) = ½ Σ_x d_x (R_ab + R_bx − R_ax)`, with `R_ab = b'L⁺b` exactly B103's resistance. So on a
reversible chain (2) is written term by term in B103's resistances.

**(4) The gate.** On an irreducible nonnegative chain, if `g` is a gate of a set `S` (every path from
outside `S ∪ {g}` into `S` passes `g`) and `j` and the support of `r` lie outside `S`, every node of `S`
moves by the same relative amount, `Δπ_i / π_i`, as `g`.

**(5) The denominator.** `1 − v'Zu = det(I − B' + πℓ) / det(I − B + πℓ)`. When only one column changes on an
irreducible nonnegative chain it never vanishes: every closed class of `B'` holds `k`, so there is exactly
one. A rerouting that closes a set holding `k` sends the whole stationary split into it and leaves exactly
zero outside. The singular case needs a change on both sides, such as a relation between two parts removed
in both directions.

**Proposition 44.1 (A45's map).** Adding or cutting one route of a trading node `k` that keeps at least one
route to a trading node changes the block by exactly `u v'` with

```
u  =  [ q_k ( r'_k − r_k ) ; 0 ],        v  =  M[k, :]'
```

so `v'π` is `k`'s holding after the wage step in the stationary state, the claims it has to spend. The
change is one outer product, so its rank is at most one: one when neither factor is zero, and the change
is the zero matrix when `v = 0`, the case of a payer whose whole holding the wage step takes.

**Corollary 44.2 (who gains).** On an irreducible nonnegative chain, a new route `k → j` never lowers the destination:
`Δπ_j = (π_k / (1 − v'Zu)) δ π_j m(r → j) ≥ 0`. The source moves with the sign of `m(r → k) − m(j → k)`,
up when claims come back to it sooner through `j` than through its old destinations, down otherwise.

**Proof.** (1) `ℓu = 0` gives `ℓB' = ℓ`. `(I − B' + πℓ)π' = π(ℓπ') = π`, and `I − B' + πℓ = Z⁻¹ − uv'`. By
Sherman and Morrison, `(Z⁻¹ − uv')⁻¹ = Z + Zuv'Z / (1 − v'Zu)`. Since `Z⁻¹π = π`, `Zπ = π`, and applying the
inverse to `π` gives the formula. (5)'s first clause is the matrix determinant lemma for the same
matrix. (2) Kemeny and Snell's relation for an irreducible chain, written for columns, is `Z_ix = Z_ii − π_i m(x → i)`; then
`Z_ij − Σ_l r_l Z_il = π_i (Σ_l r_l m(l → i) − m(j → i))` because `Σ r = 1`. (3) The commute-time identity is
Chandra et al.'s, the one-way form Tetali's; `R` in both is the resistance of the graph whose
conductances are the edge weights, which is B103's `b'L⁺b`. (4) A path from `x` outside `S ∪ {g}` to `i ∈ S`
first reaches `g`, so by the strong Markov property `m(x → i) = m(x → g) + m(g → i)`, also for `x = g`. With
`j` and `r` outside `S`, (2) gives `z_i / π_i = m(r → g) − m(j → g)` for every `i ∈ S ∪ {g}`, and (1) scales
every `z_i` by one number. (5) A closed class of `B'` that does not hold `k` has the same columns in `B`
and is closed there, which irreducibility rules out; closed classes are disjoint, so there is one, and
the multiplicity of eigenvalue one of a nonnegative stochastic matrix is its number of closed classes.
With eigenvalue one simple, `(I − B' + πℓ)x = 0` gives `ℓx = 0` on applying `ℓ`, then `(I − B')x = 0`, so `x` is a
multiple of `π'` with zero mass, hence zero. States outside the one closed class are transient and have
stationary mass zero. Two disjoint closed classes with stationary vectors `a` and `b` give
`(I − B'' + πℓ)(a − b) = 0`. Proposition 44.1: `A` depends on the routes only through `G`, and changing
row `k` of `R` changes column `k` of `G` by `q_k (r'_k − r_k)`; `q` is unchanged while `k` keeps a route to a
trading node, so `s` and `M` are unchanged and `ΔA = [ΔG; 0] M = [q_k (r' − r); 0] M[k, :]`. Corollary 44.2:
with `v = e_k`, (1) gives `π'_k = π_k / (1 − v'Zu)`, positive because `k` is in the one closed class, so the
denominator is positive; `(Zu)_j = δ π_j m(r → j)` by (2) with `m(j → j) = 0`, and
`(Zu)_k = δ π_k (m(r → k) − m(j → k))`. ∎

**Against the price side, part by part.**

| Theorem 44 | B103 to B105 |
|---|---|
| (1) `(v'π) / (1 − v'Zu) · Zu` | Theorem 41 (2): `w D / (1 + w R) · L⁺b` |
| (2) first-passage times | the effective resistance |
| (3) on a reversible chain, the same numbers | |
| (4) a gate moves a set as one piece | Theorem 42 (1): a piece hanging from one vertex moves as one piece |
| (5) one route cannot make the denominator vanish | Theorem 43 (4): cutting a bridge makes `det(I − H_F)` zero. A bridge cut removes a relation in both directions |
| Corollary 44.2: the destination always gains, the source either way | Rayleigh's law in Theorem 41 (3): a relation added never raises the share an action rewrites |

## 3. What the checks read

Tolerance `1e-9` everywhere except the rank checks (`1e-12`). The floors measured before the run were
`1.2e-15` for (1), `1.2e-14` for (2) and `1.8e-12` for (3).

| | check | reading |
|---|---|---|
| PASS | B136-1 `instrument` **the exact step** | 200 nonnegative irreducible chains of 5 to 60 nodes, one reroute in five moving the source's whole outflow: largest node gap to the re-solved stationary vector `8.7e-16`. On the reducible two-node chain of (2) the step returns `(⅔, ⅓)` and denominator `3/2`, gap `5.6e-16`. Planted: no denominator, the wrong scalar, a pseudo-inverse for `Z`; the least caught at `7.3e-2` |
| PASS | B136-2 `instrument` **the first-passage form** | Passage times solved target by target on their own: largest gap `9.7e-14`. Planted: the return time on the diagonal, the chain transposed |
| PASS | B136-3 `instrument` **the reversible limit** | 90 of B103's weighted graphs (8, 16 and 32 nodes), resistance from B103's own pseudoinverse: commute identity, Tetali's form and the rerouting's direction in resistances, largest gap `7.7e-14` of the largest passage time. Planted: the volume as the edge sum, the unweighted Laplacian |
| PASS | B136-4 `instrument` **the gate** | 30 gated chains, largest relative spread over the set `6.1e-11`; 30 with one back door into the set, least spread `0.58` |
| PASS | B136-5 `instrument` **the denominator** | Determinant ratio on the 200 chains `2.4e-15`; 40 reroutes that close a set: least denominator `0.196`, largest share left outside `2.3e-15`; the same with the other side's way in removed as well: largest least singular value `1.4e-16` |
| PASS | B136-6 `instrument` **Proposition 44.1 on A45's carriers** | 15 carriers (five seeds, three floors), 1,020 routes, 750 added and 270 cut: change against `u v'` `2.8e-17`. 46 change nothing (34 added, 12 cut, `v = 0` on all of them); on the other 974 the second singular value is `1.0e-15` of the first. Exact step against the rebuilt map re-solved `1.3e-14`; first order against A45's derivative `1.7e-18`. A missing or non-finite gap fails the check wherever it sits in the list. Planted: `v` as a unit vector, routes not renormalised, a non-finite ratio first and last, a zero change read as rank one and the reverse |
| PASS | B136-7 `known_answer` **A45's exact column** | A45's three edge-lever variants on five seeds, 15 rows: one outer-product term for every source whose routes the lever changes, 20 or 150 terms; the change's rank is 20, or 47 to 49 for the 150 terms. Woodbury's step against A45's recorded exact split, largest gap `4.9e-11`. Planted: the first-order term alone, the rank of the new map read for the rank of the change |
| PASS | B136-8 `own_reading` **the channel readings** | 1,020 rows over 18 (source, destination, kind) cells, all finite; the holdings block's distance from reversible read on all 15 carriers under two weights |

## 4. Two things the checks found that the statement did not contain

**One route from a payer who is always short moves nothing.** Of the 750 added routes, 34 leave their
destination where it was. All 34 start at payers whose short share is exactly one: in every round the
wage step takes everything they hold, so their row of the wage step is zero, `v = 0`, and the map does not
change at all. The same holds for 12 of the 270 cuts. So 46 of the 1,020 changes are the zero matrix and
974 have rank one. Every other intermediate source is short in at most `39.2%` of rounds and has
`|v'π| ≥ 6.4e-4`.

**A45's gap between first order and exact is a Woodbury denominator.** For the financial-to-intermediate
edges at a third of their weight, A45 printed a first-order financial share of `0.843` and an exact one of
`0.881` (seed 0). The exact value is the Woodbury step with 20 terms, one per financial node, and the gap is
the inverse of `I − V'ZU`. The number of terms bounds the rank of the change and need not equal it: for the
upward out-degree lever there are 150 terms and the change has rank 47 to 49 across the seeds (`U` has that
rank, `V` has 150). Woodbury's step holds with dependent terms, and the split it returns is the recorded one.

## 5. The channel read as an economy

**On the carriers the destination always gains and the source goes either way.** Of 750 routes added, the
destination node rises on 716 and falls on none; the source's own share rises on 304 and falls on 412. Of
270 cuts, the source rises on 161 and falls on 97. The destination's class fell once, by `2.8e-7`. A route
opened is a claim on the destination's attention and it always gets something. Whether the opener gains
depends on whether its money comes back sooner through the new counterparty than through the old ones.

**By class**, medians: a financial node's new route into the intermediate block lowers the financial
layer's share by `0.0035` and raises the block's by `0.0034`; cutting such a route raises the financial
layer by `0.0057`. Routes added by wage earners move every class by a few hundred-thousandths, because
their money is small and moves fast.

**The carriers are far from reversible.** Read on the holdings block `H` with the holdings part `h` of the
whole map's stationary vector as weights, `72.0%` to `77.8%` of the flow `H diag(h)` has no flow back, and
`95%` to `96%` of the node pairs that carry flow carry it one way. With the bill column `H h + b z = h`, so
`h` is not `H`'s own stationary vector (`|H h − h|` is `1.1e-3` to `2.0e-3`); under `H`'s own stationary
vector the share is `72.0%` to `77.7%`, within `0.29` of a point carrier by carrier. So B103's resistances describe the
money side exactly only in the limit (3), and what the money side lacks against the price side, the source
half of monotonicity and the bridge cut, comes from direction.

## 6. Placement

**A.** The rank-one update is Sherman and Morrison's; the perturbation of a stationary distribution is
Schweitzer's; the fundamental matrix and first-passage times are Kemeny and Snell's; the commute identity is
Chandra et al.'s and the one-way form Tetali's; the denominator is the matrix determinant lemma.

**D.** That adding or cutting one route on the money map is exactly one outer product, of rank at most
one, with `v` the source's row of the wage step; that adding a channel is one update applied to the Green's function of one graph, `L⁺` for
prices and `Z` for money, and that the two are the same numbers on a reversible chain; that on the money
side the destination always gains and the source goes either way; that one route cannot disconnect the
money side, while a bridge cut on the price side does, because the cut removes both directions; and that a
route from an always-short payer carries nothing.

**C is empty and this station cannot produce it**: it reads no data, so no point prediction of any other
account is scored here.

## 7. Scope

One route at a time on the money side (several routes compose as Woodbury's step, as in B136-7), weights
positive, a source that keeps at least one route to a trading node. Parts (2) and (4) and Corollary 44.2
are proved for irreducible nonnegative chains, the corollary with `v = e_k`; on A45's map `v` carries the wage step and the bill column makes some
entries negative, and there the counts in section 5 are readings. Nothing here measures a route, a price
or a flow in any economy.

## References

- Chandra, A. K., Raghavan, P., Ruzzo, W. L., Smolensky, R. and Tiwari, P. (1996). The electrical
  resistance of a graph captures its commute and cover times. *Computational Complexity* 6(4): 312–340.
- Kemeny, J. G. and Snell, J. L. (1960). *Finite Markov Chains*. Van Nostrand.
- Schweitzer, P. J. (1968). Perturbation theory and finite Markov chains. *Journal of Applied
  Probability* 5(2): 401–413.
- Sherman, J. and Morrison, W. J. (1950). Adjustment of an inverse matrix corresponding to a change in
  one element of a given matrix. *Annals of Mathematical Statistics* 21(1): 124–127.
- Tetali, P. (1991). Random walks and the effective resistance of networks. *Journal of Theoretical
  Probability* 4(1): 101–109.
