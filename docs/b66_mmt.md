# B66: the edges a sovereign posts, and where the two mechanisms of modern monetary theory live

**Status: statement and proof, with structural checks and one known-answer check.
Registered 2026-09-11. No empirical arm: this station is paper. Its checks, B66-8 and B66-9,
are in `experiments/b66_mmt_check.py`, record `results/b66_mmt_check.json`, and are listed
in §7.**

---

## 0. The question this station answers

Six claims carry modern monetary theory. Four of them are readings of results already on
the books in this repository. The other two are about edges the sovereign posts, and this
file proves those.

| the claim | where it lands |
|---|---|
| the unit the state names is driven by a tax payable in it | **§3, Theorem 11(2) and (3)** |
| the issuer spends before it taxes | **§3, Theorem 11(1)** |
| the government's deficit is the non-government's surplus | Corollary 10.1 of [`b65_post_keynesian.md`](b65_post_keynesian.md) |
| bonds do not fund the spending | stage A29, both rounds |
| interest paid on balances is a floor, and the rate is a posted price | stage B59 |
| what an issuer can do turns on its monetary sovereignty | [`b63_trilemma.md`](b63_trilemma.md), Corollaries 8.1 to 8.4 |
| a job guarantee anchors the price level | **§4, Corollary 11.1** |

**The result the two proofs share.** Both of the sovereign's own mechanisms are statements
about flows, not about the field. A tax decides which route carries a payment and how large
that payment is; a guarantee decides at what wage hours move. Neither adds a no-arbitrage
constraint on the terms **while the edge it stands on lies on no walkable cycle**, and each
adds one the moment the rest of the graph closes such a cycle through it: an edge out of the
obligation for the tax, an agent edge at the labour position for the guarantee (§4,
Corollary 11.2).

## 1. Setup: the three edges a sovereign posts

Notation follows [`b1_theorem.md`](b1_theorem.md) §2 and §3 and
[`b65_post_keynesian.md`](b65_post_keynesian.md) §1: positions `N`, classes `A`,
`Γ = G □ H` with dates, flows satisfying Kirchhoff's law, the field `ω`, and `ρ(ω)` the
distance of Theorem 5. The sovereign is drawn outside the graph as the party that sets its
edges (stage A29), and it is the outside node `O`.

**The tax edge.** Each liable class `a` owes `τ_a(t) > 0` units of an **obligation position**
`d` at date `t`. One unit of `d` is one unit of tax due. The obligation is discharged by
sending one unit of the sovereign's unit `m` per unit of `d`.

**The penalty edge.** What a class loses by leaving the obligation undischarged: `κ` units of
goods `q` per unit of `d`, which discharges it too, by the other route. `κ` is the
enforcement, whatever form it takes.

**The posted price.** An offer by the sovereign to trade a position at a weight it fixes. A
peg is one of these, and stage B63 reads it. **A job guarantee is one posted on labour hours
and posted one way**: the sovereign buys hours at `W_JG` and sells none (§4).

## 2. The four already on the books

**No new proof here. These rows are pointers, and the readings behind them belong to the
stations named.**

| the claim | what reads it | what it says there |
|---|---|---|
| the deficit is the other side's surplus | Corollary 10.1, [`b65_post_keynesian.md`](b65_post_keynesian.md) §6 | Kirchhoff's law on a quotient by sector: the blocks' net lending sums to zero, and with the government one of the blocks that is the sectoral balance identity |
| bonds do not fund the spending | stage A29, first round | Passing down and issuance are two exits from one gap and they trade one for one: with bonds taking the whole of the parking, the authority's issuance goes to nothing, and the share of the created claims arriving as debt is the bond share |
| what the bonds do instead | stage A29, second round | Bonds bring parked claims back into the graph; a rollover with interest snowballs on the debt ledger while the cash side does not move; a progressive levy bends the stock onto a closed-form plateau |
| interest on balances as a floor | stage B59 | `12 CFR 204.2(y)` is a closed list of four kinds of eligible institution, and a class outside it holds the same balance at the same obligor at zero: the floor is a posted price that reaches the classes on the list |
| monetary sovereignty | [`b63_trilemma.md`](b63_trilemma.md) | Rates are equal across each component of the peg graph, free where no walkable cycle crosses, and inside the friction band where one does: what a sovereign keeps is what its own graph leaves free |

## 3. Theorem 11: the tax edge

**Theorem 11.** Let `m` be issued by `O` and by no class inside the graph, let stocks of `m`
be carried on time edges, and let the obligation, the settlement and the penalty be as in §1.

1. **(The cut identity, and precedence.)** At every date `t` the stock of `m` held inside the
   graph is `S(t) − T(t)`, the sovereign's cumulative spending less its cumulative receipts.
   If no class may hold a negative stock of `m`, then `S(t) ≥ T(t)` at every date: **the unit
   has to be issued before it can be collected.**
2. **(The discharge square.)** The two routes discharging one unit of `d` close a square whose
   sum is `log(κ / p)`, with `p` the goods price of one unit of `m`. Every edge at `d` points
   into it, so no class can walk that square: **(NA) adds no constraint, and the sign of the
   sum decides which route carries the flow.** At `p < κ` every liable class routes through
   `m` and puts a demand of `Σ_a τ_a` per period on the market edge into it; at `p > κ` none
   does. **A tax makes a demand the size of the bill for the unit it is payable in, at any
   price below the enforcement, and none above it.**
3. **(Two acceptable units.)** If the obligation may also be discharged in a unit `m'` at `ψ`
   units per unit of `d`, each class routes through whichever of `p`, `ψ p'` and `κ` is
   cheapest. **A tax drives the cheapest acceptable means of payment**, and it drives nothing
   the sovereign issues when the cheapest is something else.
4. **(What takes it away.)** At `κ = 0` the obligation is discharged for nothing and the
   demand is gone.

*Proof.* (1) Sum Kirchhoff's law over the nodes dated at or before `t`. Every edge with both
ends inside that set cancels, which leaves the edges crossing the cut: what `O` has paid in,
what it has taken out, and the time edges carrying the stocks at `t`. Hence
`H(t) = S(t) − T(t)`, which is Proposition 9.0 read on this cut. Adding `H(t) ≥ 0`, since no
class inside issues `m`, gives `S(t) ≥ T(t)`. (2) Walking `q → m → d` and back along the
penalty edge, the sum is `−log p + 0 + log κ`. No edge leaves `d`, so `d` lies on no directed
cycle and the square is not walkable; a class facing the obligation compares the goods it
gives up on each route, `p` against `κ` per unit, which is the sign of the sum, and the flow
it sends along the route it takes is its own obligation `τ_a`. (3) The same comparison over
three routes. (4) A route that costs nothing is taken. ∎

**The obligation and the collection are two statements, and the cut separates them.** Nothing
stops a sovereign from posting the obligation before it has issued anything: an obligation is
an edge, and an edge can be drawn at any date. What cannot come first is the flow that
discharges it. The two sequencing claims in this literature sit on the two sides of that line.
Mosler writes that tax liabilities precede spending, and also that spending precedes the
collection of taxes; **clause (1) is the second of those, and the first is a statement about
when an edge is drawn, which nothing here forbids.**

**Why this is not an arbitrage, and what follows from that.** Theorem 10's production cycle
can be walked round and round, and (NA) bites when nothing bounds it. Nothing here can be
walked at all: **a tax paid is not undone.** So the tax fixes no terms. What it fixes is a
flow, of the size of the bill, and a ceiling on the price at which that flow exists. Where
the price settles below that ceiling is a question of how much `m` the sovereign has issued
against the bill, **which is the reading Theorem 10(b) already gives for a bounded walker**:
a gap persists while the flow runs at its bound.

**The first clause in one line.** The sovereign's cumulative deficit is the stock of its unit
held by everyone else, and the stock cannot be negative, so the spending comes first. Model
SIM shows both halves at once: its stationary state balances the flows, taxes against
spending, while the stock stays at the deficit already run (§7).

## 4. Corollary 11.1: the job guarantee, an edge posted one way

The sovereign posts, for every class it admits, an edge `(a, L) → (a, m)` at a fixed wage
`W_JG`: it buys hours at that wage and sells none, so the reverse edge is absent.

**Corollary 11.1.**

1. **(Hours that do not pass between classes.)** With no agent edge carrying hours between
   classes, the posted edge lies on no cycle and (NA) adds nothing. The guarantee acts on the
   flow side: a class that can reach it sells no hours below `W_JG`, so **hours reach an
   employer below that wage only from classes the programme does not admit, or beyond what it
   is able to take**.
2. **(Hours that pass.)** With an agent edge carrying hours between classes at a cost `c`, an
   employer's hire composes with an admitted class's sale to the programme, and the square
   closes. It is walkable in one orientation only, since the programme releases no hours, so
   it gives one side of a band: `W ≥ W_JG / (1 + c)` wherever the composition reaches, and no
   upper bound anywhere. This is Corollary 8.3's one-way case with a labour edge in place of a
   conversion, composed by agent edges as in Corollary 8.4.
3. **(A bounded programme.)** If the programme takes at most `H` hours, the class that walks
   the edge is bounded, (NA) does not reach it, and the gap persists on the hours it cannot
   take: Corollary 8.6, which is Theorem 10(b) on this edge.

*Proof.* (1) Every edge of the programme ends at the money node of the class that sold the
hour, and nothing enters the labour node of a class that buys no hours, so no cycle contains
the posted edge; with no cycle, (NA) is silent. What remains is the choice at the labour node
between two edges out of it, and a class that does not sell at a loss takes the higher wage.
(2) The cycle runs: an employer buys an hour at `W`, the hour passes at `1 / (1 + c)`, the
admitted class sells it to the programme at `W_JG`, and the money returns at par. Its sum is
`log(W_JG / (W (1 + c)))`, positive exactly below `W_JG / (1 + c)`; the reverse cycle needs
the programme to sell an hour, which it does not do. (3) Corollary 8.6 with the plaquette
replaced by this cycle. ∎

**Scope of (1).** It reads the graph of this section, where hours enter at the nodes of the
classes that hold them. Draw an endowment edge from the outside node into a labour node, the
hours a class has to give up to work, and cycles through the posted edge exist again; every
one of them is bounded by the hours there are, so (NA) is silent on them by Corollary 8.6, and
(1)'s conclusion stands on that ground instead.

**The reach of an anchor.** A posted price fixes one edge's weight, and it bears on another
edge's terms only through the walkable cycles that contain both, which is Corollary 8.5's
argument on a labour edge. Two things follow. **Where the field is exact, an anchor's reach is
the set of those cycles**, and what it transmits along one of them is what the cycle's other
edges carry (Corollary 11.3). **Where `ρ(ω) > 0` there is no single price vector at all**, so
a claim that one posted price sets the price level is a claim about an object that does not
exist in that generality; `ρ(ω)` measures how far the field is from having one, and it says
nothing by itself about which edges the anchor reaches, **which is a question about the graph**.

**Corollary 11.2 (when an edge the sovereign posts reaches the terms).** An edge bears on the
field only through the walkable cycles that contain it. While the obligation is a sink the
tax's settlement edge lies on none, and while hours do not pass between classes the
guarantee's edge lies on none; in both cases what the edge does is decide flows. Each becomes
a constraint on terms as soon as the rest of the graph closes a walkable cycle through it: an
edge out of the obligation for the first, an agent edge at the labour position for the second.

*Proof.* (NA) is one inequality per walkable cycle, so an edge on none of them enters none of
the inequalities: Corollary 8.5's argument again. The two openings are Theorem 11(2) with a
refund route and Corollary 11.1(2). ∎

**What decides it is the cycle, and not the direction.** A one-way edge still pins terms when
other one-way edges chain with it into a directed cycle, which is Corollary 8.1's one-way
case, and an edge open both ways constrains nothing when it hangs on no cycle at all. §7 runs
both sides of this: hours passing in one direction only give the same switching wage as hours
passing in both.

**Corollary 11.3 (what an anchor transmits to goods).** Let a producing class buy labour and
sell goods, with the production cycle of Theorem 10 and its markup `μ`. If the wage it pays is
floored at `W_JG` by Corollary 11.1, the money price of its output satisfies
`p ≥ (1 + μ)·W_JG·l`, with `l` the hours per unit. **A posted wage reaches goods prices
through the production cycle, and it carries the markup and the labour requirement with it.**
The transmission is one for one in logs while `μ` and `l` hold still; by Theorem 10 `μ` is
pinned at zero only under free entry with no bound on quantity, and under a bound it persists,
so the same posted wage moves goods prices by different amounts in the two regimes.

*Proof.* Theorem 10 gives `log(p / (W l)) = log(1 + μ)` on the producing class's cycle, and
Corollary 11.1 gives `W ≥ W_JG` where it reaches. ∎

## 5. Placement

**What this framework reads of the world.** A tax makes a demand for the unit it is payable
in, of the size of the bill and only at a price below the enforcement; which unit it drives is
whichever acceptable one is cheapest to obtain. The issuer's cumulative deficit is the stock
of its unit held by everyone else, and it cannot be negative. A guarantee posted one way
floors the wage of those it admits on the flow side, pins a one-sided band on the field only
where hours pass between classes, and reaches exactly the cycles that cross it.

**What modern monetary theory reads of it.** A tax liability creates sellers of goods and
services against the state's unit; the issuer spends first and collects afterwards; the deficit
is the other sectors' surplus; and the source of the price level is the prices the government
pays when it spends, the job guarantee being the posted price for the buffer stock.

**What the scalar price field reads of it.** It has no place for the tax edge or for the
class that holds it: the value of the unit is settled elsewhere, and a guarantee is a floor
in one labour market.

| cell | content |
|---|---|
| **A** | Precedence and the sectoral balance: identities on both sides, and on this side consequences of Kirchhoff's law on a cut and on a quotient |
| **B** | The reach of an anchor. The rival states it without a condition: the price level is a function of the prices the government pays. This side gives it one. A posted price bears on other terms only through the walkable cycles that contain it; the transmission to goods carries the markup of Theorem 10 (Corollary 11.3), so it is one for one only where that markup holds still; and where `ρ(ω) > 0` there is no single price level to be set. This station measures no wage, so the cell is registered and left out of the count |
| **D2** | The two bounds on what a tax can do: the bill sizes the demand and the enforcement caps the price at which it exists. The question is modern monetary theory's own central mechanism, and that literature names the enforcement without pricing it, so the pair of bounds is not in it |
| **C** | Empty |

## 6. Related work

The state theory of money is Knapp's (1924); the argument that a tax liability creates the
demand for the unit runs through Lerner (1947), Mosler (1993) and Wray (2012), and Mosler puts
it as tax liabilities creating sellers of goods and services against the state's unit, with the
source of the price level being the prices the government pays when it spends; functional
finance is Lerner's (1943); the textbook statement of the sectoral balances, the spending
sequence and the job guarantee is Mitchell, Wray and Watts (2019), and Kelton (2020) puts the
same case for a general reader; the job guarantee as a buffer stock with a fixed price is
argued in Mitchell's work and in Tcherneva (2020). The programmes a later station would read
are Argentina's Jefes de Hogar (2002) and India's MGNREGA (2005). The results this file rests
on are Theorem 1 and Theorem 5 of [`b1_theorem.md`](b1_theorem.md), Theorem 4 of
[`b4_directed_edges.md`](b4_directed_edges.md), Corollaries 8.3, 8.4 and 8.6 of
[`b63_trilemma.md`](b63_trilemma.md), and Proposition 9.0, Theorem 10 and Corollary 10.1 of
[`b65_post_keynesian.md`](b65_post_keynesian.md).

- Kelton, S. (2020). *The Deficit Myth.* PublicAffairs.
- Knapp, G. F. (1924). *The State Theory of Money.* Macmillan, English edition.
- Lerner, A. P. (1943). Functional Finance and the Federal Debt. *Social Research* 10(1).
- Lerner, A. P. (1947). Money as a Creature of the State. *American Economic Review* 37(2).
- Mitchell, W., Wray, L. R. and Watts, M. (2019). *Macroeconomics.* Red Globe Press.
- Mosler, W. (1993). *Soft Currency Economics.*
- Mosler, W. (2014). There is no right time for the Fed to raise rates. moslereconomics.com,
  13 October, for the price level as a function of the prices the government pays.
- Mosler, W. Collected works, entries of 29 June 2018 and 12 July 2020, for the tax liability
  as what creates sellers against the state's unit, and for a purchase as what defines the
  unit's value.
- Tcherneva, P. R. (2020). *The Case for a Job Guarantee.* Polity.
- Wray, L. R. (2012). *Modern Money Theory: A Primer on Macroeconomics for Sovereign
  Monetary Systems.* Palgrave Macmillan.

## 7. Structural checks and the known answer

`experiments/b66_mmt_check.py`, record `results/b66_mmt_check.json`, which carries the
configuration it ran under. Seed 0; a run takes a fifth of a second, and a second run writes
the same bytes. The statements are proved in §3 and §4, and these checks run the objects the
proofs use.

**B66-8, the known answer: Model SIM read through Theorem 11(1).** Godley and Lavoie chapter
3's parameters, 100 periods from zero stocks, each period solved from the model's own seven
equations. At every date the households' stock of the unit equals the government's cumulative
deficit within `1e-12`, and it never goes negative, so cumulative spending is never behind
cumulative taxes: the first period spends 20 and taxes 7.6923, leaving a stock of 12.3077.
**In the stationary state the flows balance, taxes of 20.0000 against spending of 20, while
the stock stays at the deficit already run, 80.0000, which is the book's value.** A balanced
flow at a positive stock is the cut identity at work.

**B66-9, the structural checks.** All pass.

- **B66-9a, Theorem 11(1) on random economies.** 200 economies of 3 to 7 private holders over
  485 periods in all, with the unit issued only by the outside node and taxes drawn as a share
  of what each holder has. The stock held privately equals cumulative spending less cumulative
  taxes within `1e-12`, no stock goes below zero, and cumulative taxes never run ahead of
  cumulative spending. **The bound binds rather than merely holding**: in 20 of 20 runs that
  tax before anything has been issued, a holder's stock goes negative, which is what the
  nonnegativity rules out.
- **B66-9b, Theorem 11(2) and (3).** 400 draws of a price and a penalty, both uniform on
  `[0.1, 3]`. The square sums to `log(κ / p)` within `1e-12` on every draw. The obligation is a
  sink and no directed cycle is positive at any price, 400 of 400. Open a refund route, the one
  thing that would make the square walkable, and a positive cycle appears exactly below the
  penalty: the switching price found by bisection is the penalty itself within `1e-9`, 100 of
  100. With a second acceptable unit, the route taken is the cheapest of the three, 400 of 400,
  read off the square sums and off the costs alike.
- **B66-9c, Corollary 11.1.** With a labour position that does not pass between classes, no
  directed cycle is positive at any market wage from a tenth of the guarantee's to ten times
  it. With an agent edge at that position the switch found by bisection is the guarantee's wage
  at par, `1.0`, and the guarantee's wage over one plus the cost of passing hours when that
  cost is a quarter, `0.8`, each within `1e-9`, and nothing is positive above. **With hours
  passing in one direction only, from the employer to the admitted class, every edge of that
  cycle is one-way and the switch is the guarantee's wage all the same**, which is why
  Corollary 11.2 turns on the cycle and not on the direction. With the programme's edge
  bounded, nothing is positive again. On the flow side, with 100 workers and
  caps of 0, 25, 50, 100 and 200, the hours that reach an employer below the guarantee's wage
  are what the programme cannot take, in every cell of the grid; the cell where the two wages
  are equal is reported and mapped to no verdict.

## 8. Scope

The sovereign's edges here are three: an obligation, an enforcement and a posted price. The
file says what each does to the flows and to the field, and it measures none of them: the
size of any bill against the stock of any unit, the enforcement behind any tax, and the wage
at which hours actually move in any economy with a programme are left to stations with data.
Nothing here fixes the price level. What sets the terms on the edges the sovereign does not
post is where the rest of this repository works.
