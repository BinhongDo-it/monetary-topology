# B29: what local trade can and cannot build

**Status: construction and proof, with numerical verification. Registered
2026-08-30. No empirical arm has been run.**

---

## 0. The question this station answers

Prices are set locally. A position trades with the positions next to it, and
perhaps with the ones one or two steps beyond that, and never with the whole
network at once. Out of that, something appears that everybody treats as a global
price. **The question is what that something is.**

The answer here is exact and it is not a metaphor. **Local trade produces a field
that is locally exact and globally inexact.** Every check an agent can run passes.
A potential can be built on any patch. The object is single-valued over the whole
network only after a seam is cut, and the seam can be cut anywhere. The defect is
one number per independent global loop, and no local observation can see it.

**Where the field comes from is a different question and it has its own file.**
This one takes `w` as given and asks what arbitrage can remove.
[`b30_propagation.md`](b30_propagation.md) asks how `w` gets onto an edge that has
never traded, and the two operators are different: arbitrage acts on cycles and
only removes, transport acts on paths and creates.

This is [`b1_theorem.md`](b1_theorem.md) Theorem 1 read at a second scale.
Theorem 1 asks whether a global potential exists. **This asks what happens when
the agents themselves can only test the question locally**, which is the only way
they ever test it.

---

## 1. Setup

Positions `0 .. n-1` on a ring. Two positions trade iff their ring distance is at
most `r`, the **interaction range**: `r = 1` is nearest neighbour only, `r = 2`
adds one hop across, `r = 3` two hops across. Each edge is oriented in the
direction of increasing index and carries a signed **step** `d in {1..r}`.

A price state is `w` in `R^E`, one log ratio per edge. The cycle space
`Z = ker(boundary)` has dimension `b1 = E - V + 1`.

**Arbitrage is bounded by what an agent can walk.** An agent who closes a loop
must traverse it, so the loops that actually get closed are the short ones. Write
`V(L)` for the span of every cycle of length at most `L`, the **arbitrage
horizon**. Local arbitrage drives `w` into the orthogonal complement of `V(L)`
and leaves everything orthogonal to `V(L)` untouched.

**`L` and `r` are behavioural, not topological.** That is the whole point of the
construction. Ordinary price theory fixes the graph and asks whether a potential
exists. Here the graph is fixed *and* the agents' reach is a parameter, and the
answer depends on both.

---

## 2. Theorem 7

**Displacement functional.** Define `phi` in `(R^E)*` by `phi(e) = d_e`, extended
linearly. A cycle is a closed walk, so its total signed step returns to the start
modulo `n`, hence `phi(c)` is an integer multiple of `n`. Define
`wind(c) = phi(c) / n` in `Z`.

**Lemma.** Every edge has `|d_e| <= r`, so a cycle `c` of length `L` has
`|phi(c)| <= L*r`. If `L*r < n` then `|wind(c)| < 1`, and since it is an integer,
`wind(c) = 0`.

**Theorem 7.** Let `L*r < n`. Then

1. `V(L)` is contained in `ker(wind)`, which has codimension exactly 1 in `Z`.
2. The ring cycle `R` (the sum of all step-1 edges) has `wind(R) = 1`, so
   `R` is not in `V(L)`, and the component of `R` orthogonal to `V(L)` is
   non-zero.
3. Therefore at the arbitrage fixed point `w* = (I - P_V) w`: every cycle of
   length at most `L` sums to exactly zero, **and** `R . w* = ((I - P_V) R) . w`
   is non-zero for generic `w`.

**In words. Arbitrage of any range `r` and any horizon `L` with `L*r < n` closes
every loop the agents can walk and cannot touch the one that they cannot.**

**General form.** Drop the ring. Let `X_L` be the 2-complex whose 1-skeleton is
the trading graph and whose 2-cells are its cycles of length at most `L`. The
surviving inconsistency is `H_1(X_L; R)`, of dimension

```
gap = b1(G) - rank V(L)
```

**This is the quantity the station measures.** For the ring at range `r` it is 1
when `L*r < n` and 0 otherwise. For an `n_x` by `n_y` torus at `r = 1, L = 4` it
is the number of directions whose circumference exceeds 4.

---

## 3. Verification

`experiments/b29_locality.py`. Rank by SVD with a cut, arbitrage by orthogonal
projection off `span V(L)`, cycles enumerated exhaustively up to the horizon.
Cached by `(n, r, L)` since none of these change once computed.

**One correction is recorded rather than quietly fixed.** The first version took
the projection basis from a reduced QR of the cycle matrix. That family is always
rank deficient, and reduced QR of a rank-deficient matrix returns columns
spanning more than the column space, so the projection removed directions no
arbitrage can reach and the surviving defect read as zero. The wrong reading was
"local arbitrage removes everything", which is the answer a careless version of
this construction would want. SVD with a rank cut fixes it.

| n | r | L | E | b1 | cycles ≤ L | rank V | **gap** | max wind of a visible cycle | visible residual | ring sum | ⌈n/r⌉ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | 1 | 8 | 12 | 1 | 0 | 0 | **1** | 0 | 0 | 0.2648 | 12 |
| 12 | 2 | 4 | 24 | 13 | 24 | 12 | **1** | 0 | 1.3e-15 | -0.2378 | 6 |
| 12 | 2 | 5 | 24 | 13 | 36 | 12 | **1** | 0 | 2.9e-15 | -0.2378 | 6 |
| 12 | 2 | 6 | 24 | 13 | 50 | 13 | **0** | 1 | 1.6e-15 | 0.0000 | 6 |
| 12 | 3 | 3 | 36 | 25 | 36 | 24 | **1** | 0 | 3.4e-15 | -0.5467 | 4 |
| 12 | 3 | 4 | 36 | 25 | 123 | 25 | **0** | 1 | 4.9e-15 | 0.0000 | 4 |
| 16 | 2 | 4 | 32 | 17 | 32 | 16 | **1** | 0 | 3.8e-15 | -0.8259 | 8 |
| 16 | 2 | 6 | 32 | 17 | 64 | 16 | **1** | 0 | 4.0e-15 | -0.8259 | 8 |
| 16 | 2 | 8 | 32 | 17 | 98 | 17 | **0** | 1 | 3.6e-15 | 0.0000 | 8 |
| 16 | 3 | 4 | 48 | 33 | 160 | 32 | **1** | 0 | 8.3e-15 | 0.6777 | 6 |
| 16 | 3 | 5 | 48 | 33 | 400 | 32 | **1** | 0 | 8.7e-15 | 0.6777 | 6 |
| 16 | 3 | 6 | 48 | 33 | 952 | 33 | **0** | 1 | 7.3e-15 | 0.0000 | 6 |
| 20 | 2 | 6 | 40 | 21 | 80 | 20 | **1** | 0 | 4.2e-15 | 0.1152 | 10 |
| 20 | 2 | 10 | 40 | 21 | 162 | 21 | **0** | 1 | 3.6e-15 | 0.0000 | 10 |
| 20 | 4 | 4 | 80 | 61 | 560 | 60 | **1** | 0 | 9.9e-15 | 1.2831 | 5 |
| 20 | 4 | 5 | 80 | 61 | 2104 | 61 | **0** | 1 | 1.2e-14 | 0.0000 | 5 |

**Three things this table establishes and the proof did not.**

**The containment is an equality.** `rank V(L) = b1 - 1` in every configuration
with a surviving defect, so `V(L)` is exactly `ker(wind)` rather than merely
contained in it. The surviving space is one dimensional, never more.

**The transition is exactly at `L = ⌈n/r⌉`, with no window.** `(20,2,6)` has a
defect and `(20,2,10)` does not; `(20,4,4)` has one and `(20,4,5)` does not;
`(12,3,3)` has one and `(12,3,4)` does not. The gap goes 1 to 0 at the first
horizon at which a winding cycle fits, and the `max wind` column shows the
mechanism directly: below the threshold no visible cycle winds at all.

**The residual column is the honest part.** Every visible cycle closes to `1e-14`
or better at the fixed point. **The construction is not producing a defect by
failing to arbitrage.** It arbitrages everything it can reach.

### The length spectrum, which is what the empirical arm would measure

After arbitrage with horizon `L`, probe cycles by length and record the largest
sum found at each length.

| n | r | horizon L | ⌈n/r⌉ | len 3 | len 4 | len 5 | len 6 | len 7 | len 8 |
|---|---|---|---|---|---|---|---|---|---|
| 16 | 2 | 6 | 8 | 2e-15 | 3e-15 | 4e-15 | 4e-15 | **5e-15** | **0.8259** |
| 20 | 4 | 4 | 5 | 9e-15 | 1e-14 | **1.2831** | 1.2831 | | |

**The first row carries the sharper statement.** The agents arbitraged only up to
length 6, and cycles of length 7 still close to `5e-15`. **Nobody closed them and
they closed anyway**, because a length-7 cycle at range 2 cannot wind, so it
already lies in the span of what was arbitraged. The first non-zero appears at
length 8, which is `⌈n/r⌉` and not the horizon.

**So the crossover a measurement would find estimates the network's own reach
ratio, not the traders' horizon.** The traders' horizon decides only whether a
defect exists at all. This is a correction to the obvious reading of the arm and
it is written here rather than discovered later.

### The seam

Ring of 20, range 2, horizon 6, so the defect survives. At the fixed point:

```
every visible cycle closes to                             5.93e-15
worst disagreement between two short routes to one node   4.11e-15
discrepancy on closing the ring                          -4.038834
```

**Every local check passes to machine precision and the ring does not close.** A
potential can be integrated from any starting position and is single-valued on
any arc; carry it all the way round and it fails to return by `-4.04`. **The
global price exists as a function only after choosing where to put the seam, and
nothing in the data chooses.**

### The same construction on a torus

Nearest neighbour only, horizon 4, so the visible cycles are the elementary
squares.

| n_x | n_y | V | E | b1 | 4-cycles | rank V | **gap** |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 16 | 32 | 17 | 24 | 17 | **0** |
| 5 | 4 | 20 | 40 | 21 | 25 | 20 | **1** |
| 5 | 5 | 25 | 50 | 26 | 25 | 24 | **2** |
| 6 | 5 | 30 | 60 | 31 | 30 | 29 | **2** |

**The gap counts the global directions the agents cannot walk around.** At `4x4`
both circumferences equal the horizon, so both classes die. At `5x4` one survives.
At `5x5` and `6x5` both do. **The surviving dimension is the first Betti number
of the shape the trading network sits on, not of the network.**

---

## 4. Three consequences

### 4.1 Density does not buy a global price. Range does.

Going from `r = 1` to `r = 4` on a ring of 20 takes the cycle space from
dimension 1 to dimension 61. **The surviving defect stays at exactly 1.** Every
new link adds a local constraint and a local degree of freedom in equal measure,
and the winding class is untouched until `L*r` reaches `n`.

**So a market can be arbitrarily thick, with arbitrarily many bilateral
relations, all of them arbitraged to machine precision, and still carry no global
price.** Thickness and globality are different quantities. This is the sharpest
thing the construction says, and it is the one an ordinary reading of "more trade
means better price discovery" gets backwards.

### 4.2 The apparent global price is a gauge choice

At the fixed point the field is exact on every patch. Fix a position, integrate
outward, and a price function appears. Two agents who compare their functions on
the overlap agree. **They agree because they overlap, not because a global
function exists.** The disagreement is entirely in the transition around the loop,
and it is invisible to every pair.

This is what "looks like a global price" means precisely: **a locally exact
1-form with non-zero holonomy.** Nothing about it is approximate. It is exact
locally and non-existent globally, and both statements hold at machine precision
in the same object.

### 4.3 What this says about the price theory it replaces

Walrasian theory posits a price vector `p` in `R^n`, which is a global potential,
before asking anything. Theorem 1 already showed that the potential's existence is
a cycle condition rather than a modelling convenience. **Theorem 7 locates what
the standard assumption actually buys.** It is not frictionlessness. It is
`L*r >= n`: the assumption that the arbitrage horizon times the interaction range
covers the network.

Complete markets are the corner `r ≈ n/2`, where every pair trades and the
threshold is met at `L = 3`. **So the completeness assumption is a statement about
the trading graph's reach, and the theory is exactly true there and has no
approximation anywhere else.** Between the corner and the ring there is no
gradient of goodness: the defect is 1 at every `r` below threshold and 0 above.
That is the second thing an ordinary reading gets wrong, which is to treat
incompleteness as a small perturbation of completeness.

---

## 5. Precedent

**Arbitrage as curvature or holonomy is not new and is not claimed here.**

- **Ilinski**, *Physics of Finance: Gauge Modelling in Non-Equilibrium Pricing*
  (Wiley, ISBN 9780471877387; earlier as arXiv:hep-th/9710148, 1997), models
  prices as a gauge field on a lattice with arbitrage as the field strength.
- **Farinelli**, *Geometric Arbitrage Theory and Market Dynamics Reloaded*
  (arXiv:0910.1671), identifies arbitrage with the curvature of a principal fibre
  bundle and parameterises arbitrage strategies by its holonomy, and relates
  no-free-lunch-with-vanishing-risk to zero curvature. **Continuous time and
  stochastic, not a finite graph with a bounded reach.**
- **Jiang, Lim, Yao and Ye**, HodgeRank (*Math. Prog. B*, 2010, arXiv:0811.1067),
  already cited in [`b0c_precedent_topological.md`](b0c_precedent_topological.md),
  give the Hodge decomposition of cyclic inconsistency on comparison graphs.
- **Ostroy and Starr**, *Money and the Decentralization of Exchange*
  (*Econometrica* 42(6), 1974, 1093-1113), is the economics precedent for asking
  what decentralised bilateral trade can and cannot achieve without a global
  auctioneer.
- **Armstrong and Sudderth**, *Locally Coherent Rates of Exchange* (University of
  Minnesota technical report 459, 1985, 33pp). **The title collides and the
  content is unread**: the abstract is not served with the record and the report
  itself has not been retrieved. Recorded here as an open check rather than as
  either support or a conflict.

**What is added.** The 2-complex is not chosen for mathematical convenience; it is
**generated by a behavioural parameter**, how far an agent can actually walk a
loop. Once that identification is made the threshold `L*r >= n` and the
density-versus-range corollary follow. **Whether the bounded-reach version already
appears in Ilinski's lattice treatment has not been checked**, and until the book
is read that is an open question rather than a novelty claim.

---

## 6. What this generates, and what it does not yet have

**The construction half is arithmetic and carries no empirical weight.** If the
trading graph has a global loop longer than the agents' reach then the defect
survives. That is a fact about matrices.

**The claim half is that real trading networks sit below their own threshold**,
and it is not established by anything above. It generates one measurement, stated
here so that a later prereg cannot reshape it:

**B29-1, the length spectrum.** In a real network of asserted bilateral rates,
measure the cycle-sum defect as a function of cycle length. The prediction is a
threshold: at or below zero for short cycles and rising above some length, with
the crossover at the reach of the traders rather than at a round number.

- a defect that is flat in cycle length, or present at length 3 → this reading is
  wrong and the inconsistency is local noise
- a defect that rises with length and has a crossover → the reading holds, and by
  the length-spectrum table above the crossover estimates `⌈n/r⌉`, the ratio of
  the network's global loop length to the interaction range, rather than the
  traders' horizon
- no cycles long enough to test → the carrier is unusable, and this has already
  happened once, in B27, where the transfer networks turned out to be built
  acyclic on purpose

**Two carriers are already in hand and point opposite ways**, which is the reason
to run it. Triangular currency arbitrage closes in milliseconds, which is the
`r` near `n` corner and predicts no defect at any length. The loyalty loop read in
[`b27_results.md`](b27_results.md) closes on no local pair and fails around a long
loop, which is the ring corner. **A carrier with a crossover strictly between the
two has not been found yet**, and finding one is the work.

**Scope kept explicit.** Nothing above reads whether any price is correct, fair or
efficient, and nothing above requires anyone to be irrational. Every agent in the
construction arbitrages perfectly, to machine precision, over everything they can
reach.
