# B65: the post-Keynesian core, as a special case of the enlarged graph

**Status: statement and proof, with structural checks and one known-answer check.
Registered 2026-09-11. No empirical arm: this station is paper. Its checks, B65-6 and
B65-7, are in `experiments/b65_pk_flow_side.py`, record `results/b65_pk_flow_side.json`,
and are listed in §9.**

---

## 0. The question this station answers

Three objects carry the post-Keynesian account of demand and distribution.
**Stock-flow consistency**: every flow comes from somewhere and goes somewhere, and every
financial asset is someone's liability (Godley and Lavoie 2007). **Kalecki's profit
equation**: the profits of the capitalist class equal their own spending plus the deficits
of the other sectors, less the saving of workers (Kalecki 1954). **Markup pricing**: the
price of a good is a markup over unit prime cost, set by a degree of monopoly that
barriers to entry limit (Kalecki 1954; Bain 1956; Sylos Labini 1962).

This file places the three inside the objects this repository already uses.

1. **Stock-flow consistency is Kirchhoff's current law** for a flow on the enlarged graph
   `Γ = G □ H` of [`b1_theorem.md`](b1_theorem.md), with the sectors as the classes and
   the instruments as the positions (§2). **Theorem 1 is its dual.** A field is exact if
   and only if it pairs to zero with every circulation, so under a single price vector a
   stock-flow-consistent circuit creates no net value, and what any circuit creates is
   bounded by the distance `ρ(ω)` of Theorem 5 (§3, Theorem 9).
2. **A sectoral model is the quotient of `Γ` by the partition into sectors.** The
   quotient keeps the conservation law for any partition, and with connected blocks it loses
   exactly the cycles inside them, a number that can be counted (§4, Lemma 9.1).
3. **The markup is the sum of the production cycle**, a slice cycle of the producing
   class. Free entry with no bound on quantity puts it at zero, the neoclassical case; a
   bound on quantity, effective demand, lets it persist; a cost of entry caps it, the
   limit price (§5, Theorem 10). **Kalecki's equation is Kirchhoff's law summed over four
   blocks, and the profits it names are the value the production cycle creates on the
   wage bill** (§6).

## 1. Setup

Notation follows [`b1_theorem.md`](b1_theorem.md) §2 and §3. The positions `N` are
instruments: money, deposits, loans, bills, labour hours, goods. The classes `A` are
sectors: workers, capitalists, firms, banks, government, the rest of the world.
`w_a(i, j)` is the log of the number of units of `j` that class `a` receives for one unit
of `i`, and agent edges carry weight zero (assumption A1 of that file).

**Dates.** As in [`b63_trilemma.md`](b63_trilemma.md) §1, each (class, position) is dated,
and the time edge `(a, i, t) → (a, i, t+1)` carries the log gross return on holding `i`
for one period. A stock is the flow on a time edge.

**The outside node.** The sovereign is drawn outside the graph, as the party that sets its
edges (stage A29). Issuance and taxes enter and leave through one node `O`, as do the
stocks at the first and the last date and, where hours and goods are drawn, the hours
households supply and the goods used up. Edges at `O` carry weight zero: money is issued at
par.

**Flows.** A flow `x` is an antisymmetric function on oriented edges, measured in value at
a numéraire. It is **stock-flow consistent** when it satisfies Kirchhoff's current law at
every node, `O` included:

```
Σ_u x(v, u)  =  0        for every node v
```

The set of such flows is the cycle space `Z`, the kernel of the boundary map `∂`. With the
standard inner product on edges, the edge space splits orthogonally into `im d⁰`, the
fields with a potential, and `Z` (Biggs 1993; Bollobás 1998), and the distance `ρ(ω)` of
Theorem 5 ([`b1_theorem.md`](b1_theorem.md) §14) is the length of the component of `ω` in
`Z`.

**Value along an edge.** A flow of value `x` along an edge whose terms differ from the
valuation by `ε = ω − d⁰ψ`, with `ψ` the valuation's potential, delivers `x·e^ε` at the far
end. **The statements below are exact for a single cycle traversed once, and first order
in `ε` for a general circulation, where the text says so.**

## 2. The dictionary, and the redundant equation

| stock-flow object | on `Γ` |
|---|---|
| sector | a class `a ∈ A`, a node of the agent graph `H` |
| instrument | a position `i ∈ N` |
| balance-sheet entry | the stock at `(a, i, t)`, the flow on the time edge that leaves it |
| payment between sectors | a flow on an agent edge at the money position |
| portfolio shift inside a sector | a flow on a position edge between two financial positions |
| purchase of goods | a money flow one way on an agent edge and a goods flow the other way, valued at the price paid |
| production | a flow on the producing class's position edge from labour hours to goods (§5) |
| a row of the transactions-flow matrix sums to zero | every edge flow leaves one node and enters another |
| a column of the transactions-flow matrix sums to zero | Kirchhoff's law summed over the nodes of one sector at one date |
| a row of the balance sheet sums to zero | for a financial instrument, the holders' stocks equal what its issuer owes. An issuer inside the graph holds the liability as a negative stock on its own time edge, and `Σ_a S(a, i, t) = 0` is conserved by Kirchhoff's law on agent edges from a start at zero, since issuance creates the asset and the liability together. When the issuer is the outside node, what it owes is the net flow that has left it, and the row is the equation at `O` on the graph cut at `t` |

**Proposition 9.0 (the redundant equation).** On a graph with `c` connected components the
incidence matrix has rank `V − c`, so the Kirchhoff equations at all nodes but one per
component imply the rest. **The redundant equation of Godley and Lavoie, which their models
leave out of the solution and check afterwards, is the equation at the last node, and
there is one per component.** In their Model SIM, with the government as the outside node,
the graph up to any date `t`, with the households' money at `t` sent to `O`, is one
component, and the equation left over, the one at `O`, reads `H_h(t) = H_s(t)`, with
`H_s(t)` what the government has spent less what it has taxed: the money row of the balance
sheet sums to zero.

*Proof.* Each edge flow enters the Kirchhoff sums of exactly two nodes, with opposite
signs, so the sum over the nodes of one component vanishes identically; the incidence
matrix of a connected graph has rank `V − 1`, so that is the only relation. ∎

## 3. Theorem 9: the flow side of Theorem 1

**Theorem 9.** Let `x ∈ Z` be a stock-flow-consistent flow on `Γ`, with its dates and the
outside node.

1. For every potential `ψ`, `⟨d⁰ψ, x⟩ = 0`. Hence `⟨ω, x⟩ = ⟨ω − d⁰ψ, x⟩` for every `ψ`:
   **to first order, the net value a stock-flow-consistent circuit creates does not depend
   on the valuation**, and it equals `⟨ω, x⟩`.
2. `ω` is exact if and only if `⟨ω, x⟩ = 0` for every `x ∈ Z`.
3. `|⟨ω, x⟩| ≤ ρ(ω)·‖x‖`, with equality when `x` is parallel to the component of `ω` in
   `Z`.
4. Exactly, a unit of value sent once around a cycle `γ` returns `e^{∮_γ ω}` units.

*Proof.* (1) `⟨d⁰ψ, x⟩ = ⟨ψ, ∂x⟩ = 0` because `∂x = 0`; the first-order excess delivered
along the edges is `Σ_e x_e ε_e = ⟨ω, x⟩ − ⟨d⁰ψ, x⟩`. (2) The indicator circulations of
the cycles span `Z`, and `⟨ω, 1_γ⟩ = ∮_γ ω`, so (2) is condition (3) of Theorem 1.
(3) By (1), taking for `ψ` the least-squares potential, `⟨ω, x⟩ = ⟨P_Z ω, x⟩`; apply
Cauchy–Schwarz, with `‖P_Z ω‖ = ρ(ω)` by the orthogonal split of §1. (4) The log of the
units received is additive along a path. ∎

**Read in the language of stock-flow consistency.** Under a single price vector
`ρ(ω) = 0`, and every stock-flow-consistent circuit is value-neutral in total. **A circuit
that leaves the economy with more value than it started with, at any valuation,
certifies `ρ(ω) > 0`, with `ρ(ω) ≥ |⟨ω, x⟩| / ‖x‖` from that one circuit.** The accounting
that stock-flow consistency enforces and the obstruction that Theorem 1 detects are the two
sides of one inner product.

## 4. Lemma 9.1: sectors as a quotient

Let `π` partition the nodes of a connected `Γ` into blocks `B_1, …, B_k`, and let `c_r` be
the number of components of the subgraph `Γ[B_r]` that block `r` induces. The quotient
`Γ/π` has one node per block and keeps every edge between two blocks, parallel edges
included; it is connected because `Γ` is.

**Lemma 9.1.**

1. The projection `π_*`, which keeps the flows on edges between blocks, maps `Z(Γ)` into
   `Z(Γ/π)`, for any partition.
2. Its kernel is the circulations supported inside the blocks, `⊕_r Z(Γ[B_r])`.
3. Its image has codimension `Σ_r (c_r − 1)` in `Z(Γ/π)`. **With every block connected,
   `π_*` is onto and the first Betti number splits: `b₁(Γ) = b₁(Γ/π) + Σ_r b₁(Γ[B_r])`.**

*Proof.* (1) Summing Kirchhoff's law over the nodes of a block cancels every edge inside it,
which leaves the law at the block's node in the quotient; nothing about the block is used.
(2) A circulation that vanishes on every edge between blocks satisfies Kirchhoff's law
inside each block separately. (3) With `E_out` the edges between blocks and `E_r`, `V_r`
those inside block `r`, (2) gives the image the dimension
`(E − V + 1) − Σ_r (E_r − V_r + c_r) = E_out + 1 − Σ_r c_r`, while
`b₁(Γ/π) = E_out − k + 1`. The difference is `Σ_r c_r − k`. ∎

A block in pieces makes the quotient show `Σ_r (c_r − 1)` independent loops that no
circulation of `Γ` produces. Kalecki's equation in §6 uses only part (1), so it holds for
blocks drawn by institutional sector, which need not be connected.

**What a sectoral model cannot see is the kernel, `Σ_r b₁(Γ[B_r])` independent
circulations.** Every circulation inside a sector projects to zero, so a sectoral model
records none of the value it creates. **Take as the blocks the manuscript's layers instead
of the institutional sectors, and spending by the financial layer on the financial layer is
a circulation inside one block: at the level of layers it is indistinguishable from not
spending at all.** That is the precise form of Volume One's opening statement that spending
within a layer is functionally equivalent to saving. Taken by institutional sector instead,
the same money is merged into the entries between households and firms with the money that
reaches the production layer, and the two cannot be told apart.

## 5. Theorem 10: the markup as the sum of the production cycle

Take money `M`, labour hours `L` and goods `Q`. The market edges carry the wage `W` and the
price `p` for every class. The producing class `F` also holds a **production edge**
`L → Q` at the technical rate of `1/l` units of output per hour; the other classes do not
hold it, and production does not run backward, so the edge is directed
([`b4_directed_edges.md`](b4_directed_edges.md)). The cycle

```
C_F :  (F, M) → (F, L) → (F, Q) → (F, M)
∮ C_F  =  −log W  −  log l  +  log p  =  log( p / (W l) )
```

is a slice cycle of `F` in the sense of Theorem 2. Under markup pricing,
`p = (1 + μ)·W·l`, and **`∮ C_F = log(1 + μ)`**. With several prime inputs, take for `L`
the bundle of inputs that makes one unit of output, bought at its unit prime cost `u`; the
cycle runs through the bundle and sums to `log(p / u)`. **Capital.** A class that rents
capital on the cycle at its normal return has the rental in the bundle, and `μ` is then the
markup over full unit cost. Kalecki measures the degree of monopoly over prime cost, which
leaves capital out; the two are related by `1 + μ_prime = (1 + μ)·u / u_prime`.

**Theorem 10.** Assume no-arbitrage on walkable cycles and finite flows at a steady state,
as in [`b63_trilemma.md`](b63_trilemma.md) §1.

- **(a) Free entry, no bound on quantity.** If every class that could produce holds the
  production edge and none faces a bound on quantity, then `μ ≤ 0`; and where output is
  positive and no class produces at a loss, `μ = 0`. This is the neoclassical zero-profit
  locus: zero economic profit, with capital at its normal return inside `u`, and the cycle
  in the zero set of Corollary 5.4.
- **(b) A bound on quantity.** If every class that holds the production edge sells at most
  a quantity `D` at the posted price, no-arbitrage does not reach the cycle, and `μ > 0`
  can persist while output runs at `D`.
- **(c) A cost of entry.** If an outside class can acquire the production edge at a cost of
  `c` per unit of output and then walk the cycle without a bound, `p ≤ W l + c`, that is
  `log(1 + μ) ≤ log(1 + c/(W l))`: the limit price.

*Proof.* (a) A positive sum on a walkable cycle with no bound admits an unbounded flow
along it, which a steady state with finite flows excludes, so `∮ C_F ≤ 0`. Positive output
means some class walks the cycle, and a class that does not produce at a loss walks it only
if `∮ C_F ≥ 0`. On the directed graph the first half is Theorem 4 of the directed-edge file:
a sub-potential exists exactly when no directed cycle is positive. (b) is Corollary 8.6 of
the trilemma file with the plaquette replaced by the production cycle; its proof uses only
that every class able to walk the cycle is bounded, and the sum persists as long as the
bound does. (c) With the cost of entry among its prime costs, the entrant's cycle has sum
`log(p / (W l + c))`, and (a) applied to that cycle gives `p ≤ W l + c`; with a bundle,
`W l` is `u`. ∎

**Reading.** The neoclassical and the post-Keynesian positions on the markup are cases of
one statement about one cycle. The markup is the cycle's sum, and Kalecki's degree of
monopoly is that sum read over prime cost; effective demand is the bound under which it
persists; the barriers of Bain and Sylos Labini are the cost that caps it. Sylos Labini's
own limit-price formula adds the conditions of market size and scale that decide whether an
entrant can walk the cycle at all, which is case (b) applied to the entrant.

**Scope against Corollary 5.5.** Corollary 5.5 of [`b1_theorem.md`](b1_theorem.md) places
the New Keynesian family in the zero set. Its hypothesis is a field of exchange terms
generated by prices, and production edges are not among its edges. With the production
edge in the producing class's slice, a monopolistically competitive gross markup
`ε/(ε − 1)` makes `∮ C_F = log(ε/(ε − 1)) > 0` as well, and the models with endogenous
entry against a sunk cost (Bilbiie, Ghironi and Melitz 2012) are case (c) with the cap
binding. **The two statements concern different edges.**

## 6. Kalecki's equation, and the profits it names

Take four blocks: workers, capitalists with their firms, the government with the outside
node, and the rest of the world. A block's net lending over a period is the change in its
financial stocks, its net acquisition of financial assets.

**Corollary 10.1 (Kalecki's profit equation).**

```
P  =  C_k  +  I  +  (G − T)  +  (X − M)  −  S_w
```

with `P` profits after tax, `C_k` the capitalists' consumption, `I` investment, `G − T`
the government's deficit, `X − M` the trade surplus and `S_w` the workers' saving. Profits
after tax are the firms' sales less the wage bill `W_b`, their imports and the taxes `T_k`
that capitalists and their firms pay; firms buy all imports, so each sector's spending
includes its imported content. With no government, no trade and no saving by workers it is
`P = C_k + I`.

*Proof.* Date the blocks and take the quotient by block and date. At a block other than the
government's, Kirchhoff's law on the quotient, Lemma 9.1(1), says that the change in its
stocks over the period, its net lending, is its surplus on the flows that cross into it. For
workers that surplus is `W_b − C_w − T_w = S_w`, with `C_w` their consumption and `T_w` their
taxes; for the rest of the world it is `M − X`; for capitalists with their firms it is
`(C_w + G + X) − (W_b + M + T_k)`, since the capitalists' consumption, investment and
dividends are flows inside the block, and that is `P − C_k − I`. Each flow between blocks is
paid by one and received by another, the rows of the transactions-flow matrix, so these
three surpluses and the government's, `T − G`, sum to zero. ∎

The government's net lending read from its balance sheet, the change in what it owes with
the sign reversed, equals `T − G` by the equation at `O` on the graph cut at the end of the
period: the redundant equation of Proposition 9.0 again.

**Corollary 10.2 (profits are the value the production cycle creates).** In the one-good
economy of §5, with labour the only prime input, profits before tax are
`P = p Q − W L = μ·W L`: exactly `(e^{∮ C_F} − 1)` times the value sent around the cycle,
the wage bill. To first order in the sum this is `⟨ω, x⟩` of Theorem 9 with `x` the wage
bill sent once around `C_F`. With several producers, each buying its bundle at its own cost,
profits are `Σ_γ c_γ (e^{∮_γ ω} − 1)`, with `c_γ` the cost bill sent around production cycle
`γ`. **Kalecki's two determinations of profit are one cycle read twice.** The flow through
the production cycle is set by spending, output at `D`, the bound of Theorem 10(b); the value
created on each unit of that flow is set by the markup, the sum of the cycle.

## 7. Placement

**What this framework reads of the world.** Stock-flow consistency is Kirchhoff's law on
the enlarged graph, and the value any consistent circuit creates is the pairing of the field
with it, zero exactly when the field has a single price vector. A sectoral model sees every
flow between sectors and none of the cycles inside them. The markup is the sum of the
production cycle, persistent under a bound on quantity and capped by the cost of entry.

**What the scalar price field reads of it.** Every cycle sums to zero, the production cycle
included, so profits over full unit cost are zero.

**What the post-Keynesian account reads of it.** The accounting identities, the profit
equation, and markup pricing with the degree of monopoly limited by the barriers to entry,
with sectors as the units of account.

| cell | content |
|---|---|
| **A** | The three balances, Kalecki's equation and the redundant equation: identities on both sides, and on this side consequences of Kirchhoff's law on a quotient. The limit price: Theorem 10(c) gives the same cap as Bain and Sylos Labini |
| **B** | The production cycle against the scalar price field, which sets every cycle to zero and so leaves no profit over full unit cost. This station measures no markup, so the cell is registered and left out of the count |
| **D** | Two quantities no account asks for: the number of cycles a sectoral model loses, `Σ_r b₁(Γ[B_r])` by Lemma 9.1, and the lower bound on `ρ(ω)` that one consistent circuit gives, `\|⟨ω, x⟩\| / ‖x‖` by Theorem 9 |
| **C** | Empty |

## 8. Related work

Kirchhoff (1847) states the current law; the orthogonal split of the edge space into cycle
and cut spaces is standard (Biggs 1993; Bollobás 1998). Stock-flow consistency and Model
SIM are from Godley and Lavoie (2007); the program that generates their chapter 3 tables is
Zezza's, and the `sfcr` package reproduces the model's long-run values. The profit equation
and the degree of monopoly are Kalecki's (1954); the limit price is Bain's (1956) and Sylos
Labini's (1962); the endogenous-entry model is Bilbiie, Ghironi and Melitz (2012). The
theorems this file rests on are Theorems 1, 2 and 5 of [`b1_theorem.md`](b1_theorem.md),
Theorem 4 of [`b4_directed_edges.md`](b4_directed_edges.md) and Corollary 8.6 of
[`b63_trilemma.md`](b63_trilemma.md).

- Bain, J. S. (1956). *Barriers to New Competition.* Harvard University Press.
- Biggs, N. (1993). *Algebraic Graph Theory*, 2nd edition. Cambridge University Press.
- Bilbiie, F. O., Ghironi, F. and Melitz, M. J. (2012). Endogenous Entry, Product Variety,
  and Business Cycles. *Journal of Political Economy* 120(2).
- Bollobás, B. (1998). *Modern Graph Theory.* Springer.
- Godley, W. and Lavoie, M. (2007). *Monetary Economics: An Integrated Approach to Credit,
  Money, Income, Production and Wealth.* Palgrave Macmillan.
- Kalecki, M. (1954). *Theory of Economic Dynamics.* George Allen and Unwin.
- Kirchhoff, G. (1847). Über die Auflösung der Gleichungen, auf welche man bei der
  Untersuchung der linearen Vertheilung galvanischer Ströme geführt wird. *Annalen der
  Physik und Chemie* 72.
- Sylos Labini, P. (1962). *Oligopoly and Technical Progress.* Harvard University Press.

## 9. Structural checks and the known answer

`experiments/b65_pk_flow_side.py`, record `results/b65_pk_flow_side.json`, which carries
the configuration it ran under. Seed 0; a run takes about a second, and a second run writes
the same bytes. The statements are proved in §§2 to 6, and these checks run the objects the
proofs use.

**B65-6, the known answer: Model SIM as a flow.** Parameters and starting stocks as in
Godley and Lavoie (2007, chapter 3): `α₁ = 0.6`, `α₂ = 0.4`, `θ = 0.2`, `W = 1`, `G = 20`,
no money at the start. Each period is solved from the model's seven equations, and the
solution is then written as a flow on households and firms over money, hours and goods, with
the government as the outside node.

- Kirchhoff's law holds within `1e-12` at every node of every one of 100 periods.
- **The equation at the outside node is used by no step of the solution.** On the run cut at
  each of the 100 dates it holds within `1e-12`, and `H_h(t) − H_s(t)`, the two stocks carried
  separately by the households' and the government's budget constraints, stays within
  `1e-12`.
- The graph is connected and its incidence matrix has rank one short of its node count at
  every horizon checked, from 8 nodes and rank 7 at one period to 602 nodes and rank 601 at a
  hundred: one redundant equation, as Proposition 9.0 says.
- The stationary equations have rank 6 in 7, one of them implied by the rest, and solve to
  `Y* = G/θ = 100`, `YD* = 80`, `H* = 80`, the book's values; the hundredth period lies within
  `1e-4` of them, and the gap to `H*` shrinks by `1 − α₂θ / (1 − α₁(1 − θ)) = 0.846` a period.
- **The firms' production cycle sums to zero**, since output per hour is `W` and the price
  of output is one. Model SIM sits on the zero-profit locus of Theorem 10(a), and its
  Kalecki equation reads `0 = (G − T) − S_w`: the government's deficit is the households'
  saving, which is the redundant equation differenced.

| period | `Y` | `T` | `YD` | `C` | `ΔH` | `H` |
|---|---|---|---|---|---|---|
| 1 | 38.4615 | 7.6923 | 30.7692 | 18.4615 | 12.3077 | 12.3077 |
| 2 | 47.9290 | 9.5858 | 38.3432 | 27.9290 | 10.4142 | 22.7219 |
| 3 | 55.9399 | 11.1880 | 44.7519 | 35.9399 | 8.8120 | 31.5339 |
| 50 | 99.9829 | 19.9966 | 79.9863 | 79.9829 | 0.0034 | 79.9811 |
| 100 | 100.0000 | 20.0000 | 80.0000 | 80.0000 | 0.0000 | 80.0000 |

**B65-7, the structural checks.** All pass.

- **B65-7a, Proposition 9.0 and Theorem 9.** 300 random graphs of 4 to 30 nodes, 87 of them
  in two or three pieces: the incidence matrix has rank `V − c` in 300 of 300. On the 275 with
  a cycle and 1,375 random circulations, a potential pairs to zero with every circulation;
  `|⟨ω, x⟩| ≤ ρ(ω)‖x‖` throughout, attained at the cycle component of `ω`; an exact field has
  every fundamental cycle sum at zero and `ρ = 0`, and adding a circulation `z` moves `ρ` to
  `‖z‖`; a generic field leaves some cycle sum and `ρ` above `1e-6` on every graph; one unit
  sent around each fundamental cycle, rate by rate, returns `e^{∮ω}`. Identities within
  `1e-12`.
- **B65-7b, Lemma 9.1.** 300 random connected graphs, each partitioned twice into 2 to 6
  blocks. The projection sends every circulation into the quotient's cycle space in all 600.
  With blocks grown connected it is onto, its kernel has the dimension of the circulations
  inside the blocks, and `b₁` splits, in 300 of 300. With blocks drawn under no condition,
  231 of them with a block in pieces, the image misses onto by exactly `Σ_r (c_r − 1)` in 300
  of 300.
- **B65-7c, Theorem 10 and Corollary 10.2.** 400 production draws, half with labour hours as
  the input and half with a bundle at its unit prime cost, the first at `μ = 0` exactly. The
  cycle sums to `log(1 + μ)`. With every producer unbounded a directed cycle is positive
  exactly when `μ > 0`, 400 of 400; with every producer bounded none is, 400 of 400; bounded
  producers and one unbounded entrant, positive exactly when `μ > 0`, 400 of 400. An entrant
  paying `c` per unit caps the price at unit cost plus `c` within `1e-9`, 100 of 100. The
  profits of 2 to 8 producers with their own costs and markups equal
  `Σ_γ c_γ (e^{∮_γ ω} − 1)` on every draw.
- **B65-7d, Corollary 10.1.** 200 random economies of workers, capitalists, firms and the
  rest of the world holding money and bills, 20 of them closed, 493 periods in all. The
  equation at the outside node holds without being imposed; the quotient by block and date
  carries a circulation; each block's net lending read from its stocks equals its surplus on
  the flows that cross into it; the four sum to zero; Kalecki's equation holds in every
  period, and `P = C_k + I` in the closed economies. All within `1e-12`.

## 10. Scope

The statements are exact for a single cycle and first order for circulations in general;
the first-order form is the one stock-flow accounting uses, since it books values at the
prices of the period. Revaluations of stocks at changing prices are flows on time edges and
are included by construction. The file measures nothing: the level of any markup, and the
size of any sectoral model's blind spot in any economy, are left to stations with data.

The behavioural half stays where it was found. What sets consumption out of income and
wealth, what sets investment, how large the bound `D` of Theorem 10(b) is, and how a
portfolio is divided between instruments are functions the modeller supplies, here as in any
other account. This file says where those flows live, what a circuit made of them can
create, and what an aggregation of them keeps and loses.
