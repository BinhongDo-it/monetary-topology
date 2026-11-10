# B124: levels set by an allocation, and what a new route or a new term does to them

**RUN: 2026-10-26. Statement and proof below. Checks in `experiments/b124_transport_dual.py`,
record `results/b124_transport_dual.json`, which carries the configuration it ran under.
Paper station: the checks run on generated transport problems, and no data enters.**

## 0. The question this answers

Theorem 41 ([`b103_time_reachability.md`](b103_time_reachability.md) section 2) prices an action
on a graph whose levels are a weighted least-squares fit to its edge terms. A new edge inside a
component then rewrites the share `θ = w_e R / (1 + w_e R)` of the old comparison, which lies
strictly between zero and one.

Organ allocation sets its levels differently. Each organ goes to the patient the rule ranks
first, so the levels are the shadow values of a transport problem, and a transport problem's
levels obey complementary slackness, not normal equations. This document states what that
changes. **On every route that carries flow the level difference equals the route's term
exactly, the routes that carry flow form a forest, and an action rewrites a comparison either
not at all or in full.**

## 1. Setup

**The graph.** `G` is bipartite. One side is the donor zones `z`, the other the transplant
centres `j`, and an edge `e = (z, j)` is a route an organ from `z` may take to a patient at `j`,
with term `c_e`: the cost the rule attaches to that route. Zone `z` supplies `s_z > 0` organs and
centre `j` takes `d_j > 0`, with `Σ s = Σ d` on each component of `G`.

**The allocation** is the transport problem

```
minimise   Σ_e c_e x_e    subject to   Σ_j x_zj = s_z,   Σ_z x_zj = d_j,   x ≥ 0
```

and its dual is

```
maximise   Σ_j d_j φ(j) − Σ_z s_z φ(z)    subject to   φ(j) − φ(z) ≤ c_zj  on every edge
```

with complementary slackness `x_e > 0 ⇒ φ(j) − φ(z) = c_e`. Read `φ(j) − φ(z)` as the
relative level of a centre and a zone, and `φ(j) − φ(k)` as the relative level of two centres.

**Where the dual sits in the framework.** Put the reversed edge `j → z` with
`ω(j, z) = −c_zj`. The dual constraint is then `ω(j, z) ≤ φ(z) − φ(j)`, which is the
sub-potential inequality of [`b4_directed_edges.md`](b4_directed_edges.md) section 2. So the
dual feasible set is the polyhedron `P(ω)` of Theorem 4, non-empty exactly when no directed
cycle has positive `ω`-sum, and the allocation picks one vertex of it: the one its flows pin.

**Non-degeneracy.** Every basic feasible solution of every problem considered puts positive
flow on each of its basic edges. Supplies and demands in general position satisfy it.

## 2. Theorem 46

Let `G` be connected, so that a basis has `|Z| + |J| − 1` edges.

**(1) Flow pins the level, and the routes that carry flow form a tree.** At the optimum the
edges with `x_e > 0` form a spanning tree `T` of `G`, every one of them satisfies
`φ(j) − φ(z) = c_e`, and `φ` is unique up to one constant. The relative level of any two
vertices is the signed sum of the terms along their path in `T`. So `b₁(T) = 0`: no cycle of
the routes in use carries a loop sum, and every inequality the problem meets is held by an
edge without flow, as the slack `c_e − (φ(j) − φ(z)) ≥ 0`.

**(2) A new route rewrites its comparison not at all or in full.** Add an edge `e = (z, j)`
with term `c_e` and put `D = c_e − (φ(j) − φ(z))`, the reduced cost of the new route under the
old levels.

```
D ≥ 0    the old allocation and every level stay as they were              (θ = 0)
D < 0    the new route carries flow, and the relative level of z and j
         becomes c_e: it moves by the whole of D                           (θ = 1)
```

Lowering the term of an edge that carries no flow is the same action with `D` its new slack.

**(3) A new term on a route in use moves exactly the comparisons that route separates.**
Change `c_e` by `Δ` on an edge of `T`, by little enough that `T` stays optimal. Removing `e`
splits `T` into a part holding `z` and a part holding `j`. The relative level of two vertices
moves by `Δ` if `e` separates them and by zero if it does not.

**(4) Against Theorem 41.** A weighted least-squares fit on `T` alone reproduces `φ` exactly,
since `T` has no cycle. Theorem 41's interior share needs a cycle in the fitted graph, and a
transport optimum never keeps one in use: a route that would close one either stays idle
(`D ≥ 0`) or enters and pushes another route out of `T` (`D < 0`). **Where levels are set by
averaging over routes, an action rewrites a share between zero and one; where they are set by
an allocation, the share is zero or one, and which one is decided by the sign of `D`.**

**Proof.** (1) A basic solution of the transport problem on a connected graph has
`|Z| + |J| − 1` basic edges forming a spanning tree, and under non-degeneracy the basic edges
are exactly those with positive flow. Complementary slackness gives equality on them. The
equalities on a spanning tree fix `φ` once one vertex is fixed, and summing them along the
tree path gives the relative level. A vertex of the dual polyhedron where the equalities of a
tree hold is the unique dual solution, since the shift `φ + t` is the only freedom the tree
leaves.

(2) If `D ≥ 0`, the old `φ` is feasible for the enlarged dual and the old `x`, with `x_e = 0`,
is feasible for the enlarged primal. They satisfy complementary slackness, so both are optimal,
and by (1) the dual is unique: nothing moves. If `D < 0`, the old `φ` violates the new
constraint, so the old `x` is not optimal for the enlarged problem. Suppose an optimum `x'` of
the enlarged problem had `x'_e = 0`. Then `x'` is feasible for the old problem, so its cost is
at least the old optimum. The old optimum is feasible for the new problem, and pivoting `e` into
its basis is a step of positive length under non-degeneracy and lowers the cost by `−D` per
unit, so the new optimum costs strictly less than the old one. That contradicts the first
inequality. So `x'_e > 0`, and complementary slackness puts `φ'(j) − φ'(z) = c_e`, a move of
`D` from the old `φ(j) − φ(z)`.

(3) `T` stays optimal, so by (1) the new `φ` solves the tree equalities with the one changed
term. Fix the constant on the part holding `z`. The equalities on that part are unchanged, so
its levels are unchanged; the equality on `e` moves `φ(j)` by `Δ`, and the equalities on the
part holding `j` carry that shift to every vertex of it. A pair inside one part moves by zero,
a pair across moves by `Δ`.

(4) A least-squares fit on a tree attains zero residual on every edge, because a tree has no
cycle on which the terms could disagree. Its solution therefore satisfies the tree equalities
and equals `φ`. The rest restates (2). ∎

## 3. What it says about the carrier

On the 2018 reform of UK liver allocation, the matrix released under freedom of information
gives the flows `x` for each year, and with them the routes in use. Theorem 46 then states what
an allocation-set level does in each case, and two of its consequences can be read against the
matrix and the waiting times in Tables 16 and 17 of the monitoring report.

- **A rule without a geographic term pins centres to one another.** If every route from a zone
  carries the same term, two centres that both draw from one zone have equal levels, and so do
  all centres joined by such shared zones. The scheme offers DBD livers by a national patient
  ranking, so its terms do not depend on the route; under zonal priority the routes out of a
  zone cost more than the route into its own centre.
- **The share is zero or one.** Comparisons the reform reaches move in full or not at all; no
  pair moves part of the way.

**Reading the waiting time as the level `φ(j)` is the step this document does not take.** The
theorem is about the allocation's shadow values. It applies to a centre's waiting time to the
extent that the waiting time is that shadow value, which is what the next step checks against
the matrix.

## 4. Scope

The theorem assumes balance on each component and non-degeneracy. Without balance the problem
needs an outside option (discard, or a waiting pool) as one more vertex, and the statements
hold on the enlarged graph. With degeneracy a pivot can have length zero, in which case `x`
does not move while `φ` may, and (2) holds for the optimum reached after the degenerate pivots
are resolved.

## 5. Against the carrier

`experiments/b124_level_check.py`, record `results/b124_level_check.json`, 2026-10-26.

**Structure.** In every year from 2016/17 to 2019/20, for DBD and DCD alike, the routes in use
join all seven centres in one component. Before the reform DBD uses 50 to 51 routes on 15
vertices, so `b₁` is 36 to 37; DCD uses 28 to 34 with `b₁` 15 to 21. A single transport problem
with distinct route terms keeps a tree in use (Theorem 46 (1)), so these cycles say the
allocation is several transport problems at once. Blood group is the evident split: 99% of
transplants are blood-group identical, which makes the four groups four separate problems, and
four trees on 15 vertices hold up to 56 routes, enough for every year observed. Under the
scheme's route-independent terms every cycle sum is zero, so cycles in use are what Theorem 46
allows there.

**Levels.** Each centre's median waiting time on the log scale, with the floor of its sampling
error from the published N and interquartile range, and the statistic `Q` of the deviations
from the pooled mean on 6 degrees of freedom:

| year | DBD Q/df | DBD p | DCD Q/df | DCD p |
|---|---|---|---|---|
| 2017/18 | 4.20 | 3.1e-04 | 4.12 | 3.8e-04 |
| 2018/19 | 0.84 | 0.54 | 1.11 | 0.35 |
| 2019/20 | 3.07 | 5.2e-03 | 1.72 | 0.11 |
| 2020/21 | 1.43 | 0.20 | 0.75 | 0.61 |
| 2021/22 | 1.17 | 0.32 | 1.71 | 0.11 |

After the reform the DBD centres are equal within the floor in 2018/19, 2020/21 and 2021/22,
and apart in 2019/20. The DCD centres, whose rule did not change, compress over the same years
by as much, so on these medians the compression does not separate the DBD rule from what both
donor types shared. The pooled medians mix the four blood groups, whose levels Theorem 46 sets
separately, and the report gives the split by blood group only for the country as a whole.

## 6. Against the US carrier

`experiments/b124_srtr_levels.py`, record `results/b124_srtr_levels.json`, 2026-10-27.
SRTR transplant records, adult recipients of deceased-donor livers, in four 12-month windows
aligned to the acuity-circle policy of 4 February 2020, two before and two after.

**Structure, within one blood group.** Routes in use from donor OPO to transplant centre, DBD:
for blood group O, 532 routes on 180 vertices before the reform (`b₁` 354) and 916 to 984 after
(`b₁` 740 to 809); A, B and AB have the same shape. So within a single blood group and a single
year the routes in use carry hundreds of independent cycles. Blood group does not explain them.
What does is time: the allocation solves one problem per organ, offer by offer, and a year's
flows are the sum of thousands of those problems, each with its own tree. Theorem 46 is a
statement about one allocation; an annual flow matrix is a sum over allocations, and its
cycles carry no loop sum only if the terms are route-independent.

**Levels, within one blood group.** The spread across centres (N ≥ 10) of median laboratory MELD
at transplant, mean of the two windows after minus the two before: DBD O `−0.19`, A `−0.51`,
B `+0.27`; DCD O `−0.30`, A `+0.07`. The spread of log median waits: DBD O `+0.10`, A `+0.17`,
B `−0.01`. Centres stay apart well beyond their sampling floor (`Q/df` 2 to 9). The acuity
circles still make the route term depend on distance, so the theorem does not predict equal
levels here; it predicts levels that differ by the terms, and the annual medians do not show
the spread falling.

## References

Dantzig, G. B. (1963). *Linear Programming and Extensions*. Princeton University Press.
Chapter 15 sets out the transportation problem, its spanning-tree bases and the dual it solves.
