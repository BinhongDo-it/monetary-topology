# B63: the impossible trinity, as Theorem 1 read on the currency × date product

**Status: statement and proof, with structural checks. Registered 2026-09-11. No
empirical arm: this station is paper. Its structural checks, B63-8, are listed in §11
and all four pass.**

---

## 0. The question this station answers

A currency pegged to another, with capital free to move between the two, cannot
set its own short rate. The textbook derivation is one line of uncovered parity,
and its weight sits on what that line assumes: uncovered parity with a zero or
exogenous premium, assets in the two currencies as perfect substitutes, and one
instrument in the authority's hands.

**This file reaches the same corner from closed loops alone.** Write positions as
(currency, date), put the short rate on the edge from one date to the next and the
exchange rate on the edge from one currency to the other, and the trinity is a
statement about one four-cycle: **the peg closes it, openness makes it walkable,
and no-arbitrage on walkable cycles sets its sum to zero.** The algebra is the
across-slices step of Theorem 1 ([`b1_theorem.md`](b1_theorem.md) §4) with the peg
in the place of the zero-weight agent edge. The operator is the one Theorem 7
([`b29_locality_theorem.md`](b29_locality_theorem.md) §1) puts on the cycles an
agent can walk.

**The three corners of the trinity are the three cases of b1_theorem §8**: the edge
present with its weight fixed, the edge absent, and the edge present with its
weight moving. The corollaries then give the number of independent rates a system
of pegs leaves (§3), the effect of frictions and one-way convertibility (§4), the
effect of access split by holder class (§5), what a peg pins and what it leaves
free (§6), and the point where the statement hands over to a capacity (§7).

---

## 1. Setup

**Positions.** `C` is a finite set of currencies. Position `(k, t)` is one unit of
currency `k`'s short claim at date `t`, taken to be the issuing authority's own
short liability, so that holding it from `t` to `t+1` carries no default term.

**The date-`t` contract graph `G_t`.** Its vertices are `(k, t)` and `(k, t+1)` for
every `k` in `C`. Its edges are the conversions whose terms are fixed at `t`.
Weights are logs of conversion rates, as in b1_theorem §2, and edges are directed,
as in [`b4_directed_edges.md`](b4_directed_edges.md), because a conversion and its
reverse need not carry opposite weights.

```
lend     (k,t)   -> (k,t+1)    r_k                  r_k = log(1 + i_k), the short rate
borrow   (k,t+1) -> (k,t)      -(r_k + beta_k)      beta_k >= 0, the borrowing spread
spot     (k,t)   -> (l,t)      e_kl - sigma/2       e_kl = log of units of l per unit of k
         (l,t)   -> (k,t)      -e_kl - sigma/2
locked   (k,t+1) -> (l,t+1)    lam_kl - sigma'/2    present only if the date-(t+1)
         (l,t+1) -> (k,t+1)    -lam_kl - sigma'/2   conversion can be fixed at t
```

**The locked edge is the whole content of a peg.** It can exist in two ways. A
forward market supplies it at the forward rate. A credible peg supplies it at the
parity: a published rule fixes the conversion of `k` into `l` at `e_bar` at every
date and the issuing authority stands on that conversion, so at `t` anyone who
holds the edge can fix the date-`(t+1)` conversion at `e_bar`. Under a float with
no forward market the locked edge is absent.

**Classes and agent edges.** Each edge is open to some set of agent classes.
`Gamma_t = G_t □ H` is the enlarged graph of b1_theorem §3. An agent edge
`(a, v) -> (b, v)` joins one position held by two classes, and walking it is a trade
of that position between them. It carries weight zero where the position passes at
par (b1_theorem §8, A1), a weight `t_ab(v)` where the passage has a price or a cost,
and it is absent where a rule bars the passage.

**Walkable.** A directed cycle of `Gamma_t` is walkable if every edge on it exists,
each position edge on it is open to the class in whose slice it lies, every term
on it is fixed at `t`, and no quantity bound applies to any of its edges. A walkable
cycle through agent edges is executed as a chain of trades between classes.

**The premise (NA).** At a steady state with finite flows, every walkable directed
cycle has a non-positive sum.

A walkable cycle with a positive sum pays without limit to the parties that walk
it, so the flow on it is unbounded and there is no steady state. (NA) is the
condition of b4_directed_edges Theorem 4, restricted to the cycles that can be
executed. With two-way frictionless edges the two orientations of a cycle have sums
of opposite sign, so (NA) sets the sum to zero, which is the fixed point of
Theorem 7's operator on the cycles within reach.

**The plaquette.** For two currencies `k` and `l`, the positions `(k,t)`,
`(k,t+1)`, `(l,t+1)`, `(l,t)` carry two oriented loops:

```
Q+   (k,t) -lend k-> (k,t+1) -locked k->l-> (l,t+1) -borrow l-> (l,t) -spot l->k-> (k,t)
Q-   (k,t) -spot k->l-> (l,t) -lend l-> (l,t+1) -locked l->k-> (k,t+1) -borrow k-> (k,t)

S(Q+) =   (r_k - r_l + lam_kl - e_kl) - beta_l - sigma_bar
S(Q-) = - (r_k - r_l + lam_kl - e_kl) - beta_k - sigma_bar        sigma_bar = (sigma + sigma')/2
```

**Without the locked edge, `Q+` and `Q-` are not cycles of `G_t`**: their third leg
is a conversion at a rate unknown at `t`. Such a walk is a position held open over
the period, a carry, and b1_theorem §9 excludes carry returns from cycle sums.
Only closed loops enter anything below.

---

## 2. Theorem 8

> **Theorem 8.** Let `k` and `l` be joined by a credible peg with no conversion
> spreads, let lending and borrowing carry no spreads in either currency, and let
> both orientations of the plaquette be walkable. Under (NA), `r_k = r_l`.

**Proof.** The peg sets `lam_kl = e_kl = e_bar`, so `S(Q+) = r_k - r_l` and
`S(Q-) = r_l - r_k`. (NA) makes both non-positive. `[]`

**The peg closes the loop, openness makes it walkable, and the rate is what is left
to adjust.** Under a float the locked edge is absent and nothing is pinned. With a
forward market the loop closes at the forward rate, and (NA) gives
`lam_kl - e_kl = r_l - r_k`: the rate difference is carried by the forward premium,
which is the covered-parity object of [`b3_cip_slice.md`](b3_cip_slice.md).

### 2.1 Theorem 8 is Theorem 1 on a second product

Change units at each `l` position by the parity of `l` against `k`. Loop sums do
not change, since a change of unit at a position adds a number on the way in and
subtracts it on the way out, and afterwards every pegged conversion has weight
zero (for a bloc of several pegs this needs the parities to be consistent, which
§3 shows (NA) requires). **The pegged part of `G_t` then has the shape of
b1_theorem §3's `Gamma = G □ H`**: currencies stand where classes stood, the date
step stands where the position graph stood, pegged conversions are the zero-weight
edges between slices, and the plaquette is the four-cycle, with sum
`w_k - w_l = r_k - r_l`. Theorem 1's across-slices step is Theorem 8, and its §8 A2,
one price vector per component, is the count of §3.

---

## 3. Corollary 8.1: how many rates a system of pegs leaves

Let `P_t` be the graph on `C` whose edges are the pairs joined by a credible,
frictionless peg with both orientations of the plaquette walkable.

> **Corollary 8.1.** Under (NA), `r_k = r_l` whenever `k` and `l` lie in one
> component of `P_t`. If every pegged conversion is open in both directions at both
> dates or not at all, pairs outside `P_t` add no further equality, and the number of
> rates left free is `b_0(P_t)`, the number of components.

**Proof.** Along an edge of `P_t` equality is Theorem 8, and along a path it
chains, as Theorem 1's proof chains `w_a = w_b` along a path in `H`. A pair outside
`P_t` has no locked edge, in which case no cycle of `G_t` runs through its
plaquette; or a forward, whose weight `lam = e + r_l - r_k` closes the plaquette at
sum zero and constrains no rate; or walkers who all face a quantity bound, which
(NA) does not reach; or spreads, which give the band of Corollary 8.3 and no
equality. The remaining cycles of `G_t` are spot triangles at a single date, which
contain no rate. `[]`

**One-way pegs chain too, around a directed cycle.** Let the pegged conversions
`k_0 -> k_1 -> ... -> k_n = k_0` each be open to a walking class, in that direction
only, at both dates. For any two currencies `k_i`, `k_j` on the cycle, lend `k_i`
from `t` to `t+1`, convert forward along the cycle to `k_j` at `t+1`, borrow `k_j`
back to `t`, and convert forward along the cycle to `k_i` at `t`. After the change
of units of §2.1 the loop sums to `r_{k_i} - r_{k_j}`, and (NA) makes it
non-positive for every ordered pair, so all the rates on the cycle are equal.
**When every open pegged conversion is open at both dates, rates are forced equal
within each strongly connected component of the directed graph of open pegged
conversions**, and with every conversion two-way this is the component count above.
Between two different strongly connected components no walkable cycle crosses at
all, since a crossing would need a conversion back, so their rates are unrelated:
the shape b4_directed_edges Theorem 5 gives for sub-potentials. A conversion open at
one date only gives the one-sided bound of Corollary 8.3.

**The pegs must satisfy one condition among themselves.** Around a triangle of
pegged pairs the parities must sum to zero, or the spot triangle is a walkable
cycle with a positive sum and (NA) fails at `t`. **A consistent system of pegs is
a potential on the peg graph.** A star of pegs to one anchor meets this trivially,
since a tree has no cycle. This is the commutation that
[`b27_results.md`](b27_results.md) §1 records on the merger of two point programmes,
where the factor was chosen so that two routes agree.

**The count on this product.** For a connected currency graph with `m` currencies
and a date path of `T` steps, the product's first Betti number is
`b_1(C)·(T+1) + (m-1)·T`. The first term counts spot triangles at each date and the
second counts independent plaquettes, `m - 1` per step. A single bloc covering all
`m` currencies uses all `m - 1` and leaves one rate per step, which is
Corollary 8.1 with one component.

---

## 4. Corollaries 8.2 and 8.3: the three corners, the band, and one-way convertibility

> **Corollary 8.2.** The three corners of the trinity are the three cases of
> b1_theorem §8.
>
> - **A1 holds.** The pegged conversion is open to a walking class with its weight
>   fixed across the two dates. Theorem 8 applies and the two rates are one.
> - **A1 fails by absence.** No class that could walk the plaquette holds the
>   conversion. The plaquette is not a cycle, Theorem 1 does not apply to it, and
>   the two currencies lie in different components of `P_t`. **A peg that keeps its
>   own rate is a peg with the conversion edge removed.**
> - **A1 holds only approximately, with the weight moving between the two dates.**
>   §8 writes the square sum as `w_a - w_b + t_ab(j) - t_ab(i)`; here it is
>   `r_k - r_l + (lam_kl - e_kl)`. Under a float the locked edge is absent; with a
>   forward, the rate difference is absorbed by the forward premium.

> **Corollary 8.3.** For a pair with no route between them through a third
> currency, with conversion spreads `sigma`, `sigma'`, borrowing spreads `beta_k`,
> `beta_l`, a credible peg, and both orientations walkable:
>
> ```
> -(sigma_bar + beta_k)  <=  r_k - r_l  <=  sigma_bar + beta_l
> ```
>
> If the conversion `k -> l` is closed at `t+1` only, the lower bound survives and
> the upper one does not. If it is closed at every date, no cycle crosses between
> the two currencies and neither bound survives.

**Proof.** The two inequalities are `S(Q+) <= 0` and `S(Q-) <= 0` at
`lam = e = e_bar`. `Q+` uses `k -> l` at `t+1`, so closing that edge removes the
upper bound and leaves `S(Q-) <= 0`. A closed walk that leaves the `k` side must
return to it, so with one direction closed at every date no closed walk crosses at
all: the one-way case of b4_directed_edges §5.2, an `H^0` statement, which leaves
the two rates unrelated. `[]`

**The band is b4_directed_edges Theorem 6 read on the plaquette.** The two
orientations sum to the friction,
`S(Q+) + S(Q-) = -(2·sigma_bar + beta_k + beta_l)`, and differ by twice the
antisymmetric sum. **A peg with frictions pins the rate difference to within the
round-trip cost of walking the loop.**

**The one-sided case, in words.** With `k -> l` closed at `t+1`, money brought into
`k` cannot leave at the parity, so nothing arbitrages a rate in `k` above the
anchor's. Residents can still leave at `t` and return at `t+1`, so a rate in `k`
below the anchor's is arbitraged to within the friction.

---

## 5. Corollary 8.4: access split by class, and the edge that carries a control

> **Corollary 8.4.** For a pair with no route between them through a third currency,
> under a credible peg, let class `a` hold the conversion `k -> l` and class `b` hold
> `l -> k`, each in one direction only, at both dates.
>
> 1. If agent edges between `a` and `b` exist at par at the positions the loops pass
>    through, the two one-way conversions compose into both orientations of the
>    plaquette and the band of Corollary 8.3 holds.
> 2. If those agent edges carry a price or a cost `t_ab`, the bounds move by it.
>    Where a market sets that price, it absorbs the rate difference.
> 3. If a rule removes those agent edges, no walkable cycle crosses between the two
>    currencies and the rates are unrelated.

**Proof.** `Q+` needs `k -> l` at `t+1` and `l -> k` at `t`. Class `a` walks the
lend leg and the locked leg and passes the `l` claim to `b` at `(l, t+1)`; `b`
walks the borrow leg and the spot leg and passes the `k` claim back to `a` at
`(k, t)`. The two agent edges add their weights to `S(Q+)`: zero at par, `t_ab`
otherwise. `Q-` composes the same way through the other two positions. With the
agent edges removed, each class alone holds one direction, and the closing
argument of Corollary 8.3 applies. `[]`

**What bears the load in a control regime is whatever keeps both directions out of
reach of any one class, alone or through a chain of trades.** The published record
has both instruments.

- **Closing the reverse edge for the class that holds the forward one.** A report
  on Argentina's Comunicación A 8336 of September 2025 states that the central bank
  *"prohibió que los ahorristas que compren dólares oficiales puedan operar en los
  siguientes 90 días en el mercado de los dólares financieros"* (it barred savers
  who buy dollars at the official rate from operating in the financial-dollar
  market for the following 90 days). The operation it closes is called the *rulo*,
  the round trip. The same report puts the gap between the official rate and the
  financial ones at 6.7 per cent on the MEP rate and 8.9 per cent on the CCL rate
  after the measure, the widest since the exit from the exchange controls.
  Source: Chequeado, 26 September 2025,
  <https://chequeado.com/el-explicador/el-banco-central-prohibio-el-rulo-entre-el-dolar-oficial-y-los-financieros-la-brecha-cambiaria-es-la-mas-alta-desde-la-salida-del-cepo/>.
- **Voiding the trade between classes.** Germany's 1990 conversion assigned 1:1,
  2:1 or 3:1 by holder, with per-person allowances at 1:1 set by date of birth.
  Annex I Article 6 of the treaty adds *"Umgehungsgeschäfte sind nichtig"*
  (circumvention transactions are void), which removes the agent edges through
  which balances would move to the holders with the better rate; households had
  been moving balances into children's accounts in the weeks before. The table,
  the clause and their sources are in [`b30_results.md`](b30_results.md), B30-22
  chunk one.

**With the loop cut this way, the regime carries a square**: two classes facing two
terms on one conversion, which is where an official rate and a financial one sit.
Where a market prices access across the cut, that price is the agent-edge term of
case 2. Argentina's legal conversion tracks read as squares in five of five over
1,457 dates (stages B5 and B17, [`b0d_new_keynesian.md`](b0d_new_keynesian.md) §6.3).

---

## 6. Corollary 8.5: what a peg pins, and what it leaves free

> **Corollary 8.5.** A peg adds constraints only on walkable cycles that cross
> between the two currencies. It pins the rate differences across the edges of
> `P_t`, to zero or into the band of Corollary 8.3, at the horizon over which the
> locked edge exists. An edge weight that lies on no such cycle is left free by the
> peg, and every cycle inside one currency's positions, including every square
> between two domestic classes on a domestic edge, is constrained by (NA) exactly as
> it would be without the peg.

**Proof.** The peg enters (NA) only through the spot and locked conversions between
`k` and `l`. A cycle that uses neither is the same inequality with or without the
peg, and an edge on no walkable cross-border cycle appears in none of the
inequalities the peg adds. `[]`

**Two readings follow.** First, **a peg releases the rest of the monetary field**:
terms set by class on domestic edges, admission to positions that foreign classes
cannot reach, and the spread between domestic classes on one edge all lie outside
what it pins. Second, **the plaquette constrains only the difference `r_k - r_l`**:
whether `r_k` moves to `r_l` or `r_l` to `r_k` is decided by which authority stands
on the conversion and in which direction its capacity runs (§7), and a cycle sum
says nothing about it.

**The horizon.** A peg credible over one period pins the one-period difference. A
long rate is pinned where the locked conversion exists at that horizon; where the
forward for that horizon trades away from the parity, the long difference is
carried by that premium, by the third case of Corollary 8.2 at the longer step.

---

## 7. Corollary 8.6: capacity, and the handover to the flow side

> **Corollary 8.6.** If every class that can walk the plaquette faces a quantity
> bound, (NA) does not reach it, and a non-zero sum can persist while the flow runs
> at the bound. For the authority holding the peg:
>
> - with `r_k < r_l` the flow leaves `k`, and holding the parity spends reserves of
>   `l`, bounded by their stock;
> - with `r_k > r_l` the flow enters `k`; the authority issues `k` to hold the parity
>   and, to hold `r_k` as well, borrows back what it issued at `r_k` while holding
>   `l` at `r_l`, paying `r_k - r_l` per unit per period on the stock it carries.
>
> In both cases the sum persists while the bound holds, and the time it can hold is
> the capacity divided by the flow.

**Proof.** The first statement is the definition of walkable. The two cases are the
balance sheet of the two operations: with all four edge weights held fixed and a
sum `S` different from zero, the parties walking the loop receive `|S|` per unit per
period and the authority pays it, until the bound binds. `[]`

**Sterilization is capacity with a running cost.** It leaves the flow as it is and
absorbs it on the authority's balance sheet, at a cost per period equal to the loop
sum times the stock absorbed. **The capacity is directed**, in the sense of
b4_directed_edges: bounded by reserves against outflow, and against inflow only by
the cost the authority accepts to carry. A forced exit from a peg therefore runs
toward depreciation.

**The flow side belongs to the A track.** Stage A25 builds two graphs joined by a
clearing boundary: a signed balance with a ceiling set as a share of the other
side's deliveries ([`../experiments/a25_boundary.py`](../experiments/a25_boundary.py),
and [`RESULTS.md`](../RESULTS.md), stage A25). The round in which the ceiling first
binds is the event this corollary hands over.

---

## 8. Merger, split, and the readings in this repository that sit under the corollaries

**Monetary union is the pegged edge contracted permanently.** After it the
conversion is an identity and the two currencies are one position per date. **The
contraction happens at a conversion set by class**: Germany's 1990 table in §5
assigns three values to one mark by holder, so the merger is a square on the
conversion edge at one date, and the edge becomes an identity after it. **A split
is the reverse**: the conversion edge is removed or left to float, and the count of
Corollary 8.1 rises by one. Czechoslovakia 1993 is the split case registered in
[`b30_results.md`](b30_results.md).

**Maintenance.** In the classification of [`b27_results.md`](b27_results.md) §1,
consistency between units is kept by deletion, the reverse edge removed, or by
commutation, the factor chosen so that the loop closes. **A control regime is
maintained by deletion, and an open peg bloc by commutation**: under Theorem 8 the
authority's rate is the number that makes the plaquette close.

**Path against hole, on equity lines.** Stage B24 reads the class square on two
listings of one company. Where a sponsored receipt can be cancelled into its home
line, the square reads 16.4 basis points median over 465 pairings of thirty-one
companies; where the two lines cannot be exchanged, it is 196 times that
([`b0d_new_keynesian.md`](b0d_new_keynesian.md) §6.3, [`RESULTS.md`](../RESULTS.md),
stage B24). **That is Corollary 8.3 and the absent-edge case of Corollary 8.2, read
on equity lines.**

**One currency on two graphs.** Stage B3 registered one test on a single currency: the
covered loop between the offshore and onshore renminbi codes, one sovereign, one bond
market and one default risk under two capital-account regimes, so the loop carries no
default term by construction. It runs from 66.2 to 169.0 basis points across seven
tenors, largest at three months ([`b3_cip_slice.md`](b3_cip_slice.md) §11.6). **That is
Corollary 8.4 on one currency**: the conversion between the two codes is open to some
holder classes and closed to others, and the difference sits on the loop.

**A reference carried across currencies.**
[`b25_price_band_availability.md`](b25_price_band_availability.md) reads posted
prices set by a reference converted at the exchange rate. A float releases the
plaquette of Corollary 8.5 and leaves such reference edges in place, which is one
channel through which a floating currency still imports prices.

---

## 9. Placement

**Against the scalar price field.** That account puts one potential on positions
and predicts every closed loop at zero. **On the pegged, open plaquette it predicts
`r_k = r_l`, and so does Theorem 8**: this corner is the locus where the enlarged
object is the single-price account, Corollary 5.4 of
[`b1_theorem.md`](b1_theorem.md) §14, and the agreement there is an identity.
**Open-economy New Keynesian models with complete markets** (Galí and Monacelli
2005) hold covered parity identically, so their covered plaquettes are exact and
they sit in Corollary 5.5's zero set ([`b0d_new_keynesian.md`](b0d_new_keynesian.md)
§5); their pegged corner is `r_k = r_l`. **On the covered loop under a float the same
account predicts zero, and stage B3 reads 30.9 to 45.6 basis points against a
measurement floor of 2.8 to 3.7, on nine of nine tenors over eighteen years.**

**Against a country-level openness measure.** The trilemma literature measures
openness as one number per country, built from the IMF's annual report on exchange
arrangements, and that report's categories include the presence of multiple
exchange rates. **Corollary 8.4 places openness on the holder class**: which class
holds which direction of the conversion, and whether trades between classes are
allowed. A country scalar has no slot for either, and the covered loop already
carries the class index. For one covered loop, Rime, Schrimpf and Syrstad report,
for top-rated banks, *"These arbitrage profits are as high as 18.8 basis points on
average, if the funds are placed at the deposit facility of the Bank of Japan"*,
and for A-2/P-2 banks *"some arbitrage profits have been available even for A-2/P-2
banks in the Swiss Franc and the Japanese yen. These are fairly small in economic
terms, though, at 0.5 to 4 basis points on average over the post-crisis sample
period."*

---

## 10. Related work

- **Mundell (1963) and Fleming (1962)** state the trilemma on one parity condition
  and one instrument. Theorem 8 reaches the same corner from closed loops, and
  Corollaries 8.1 to 8.6 add the count over a system of pegs, the friction band,
  the one-way case, class-split access, the pinned set and the capacity boundary.
- **Obstfeld, Shambaugh and Taylor (2005)** find that pegged economies with open
  capital accounts track the base country's rate far more closely than the rest:
  the empirical face of Theorem 8's corner.
- **Aizenman, Chinn and Ito (2013)** measure monetary independence, exchange-rate
  stability and financial openness on three indexes whose weighted sum is close to
  constant; the openness index is that of **Chinn and Ito (2006)**. Corollary 8.4
  states what an openness indexed by holder class carries.
- **Krugman (1979) and Flood and Garber (1984)** model the collapse of a peg as
  reserves run out: the outflow side of Corollary 8.6.
- **Gabaix and Maggiori (2015)** give intermediaries a limited capacity to bear
  currency risk, and **Du, Tepper and Verdelhan (2018)** document covered-parity
  deviations since 2008 and trace them to balance-sheet costs. Here both are
  capacity bounds on walkable loops, and **Rime, Schrimpf and Syrstad (2022)** place
  part of the bound on the holder class.
- **Rey (2013)** finds that floating does not insulate an economy from the global
  financial cycle. Corollary 8.5 states what a float releases: the plaquette's
  rate difference, and no other cross-border edge.
- **Jordà, Schularick and Taylor (2020)** build an instrument from the trilemma:
  pegged, open economies import the base country's rate changes. Corollary 8.1 is
  the statement that instrument's first stage rests on.
- **Ilinski (1997)** writes prices as a gauge field on an asset × time lattice, with
  arbitrage as the field strength. The currency × date product here has that base
  space, and the agent-class factor on top of it is what gives Corollaries 8.3, 8.4
  and 8.6 their objects.

References:

- Aizenman, J., M. D. Chinn and H. Ito (2013), "The 'impossible trinity' hypothesis in an era of global imbalances: measurement and testing", *Review of International Economics* 21(3).
- Chinn, M. D. and H. Ito (2006), "What matters for financial development? Capital controls, institutions, and interactions", *Journal of Development Economics* 81(1).
- Du, W., A. Tepper and A. Verdelhan (2018), "Deviations from covered interest rate parity", *Journal of Finance* 73(3).
- Fleming, J. M. (1962), "Domestic financial policies under fixed and under floating exchange rates", *IMF Staff Papers* 9(3).
- Flood, R. P. and P. M. Garber (1984), "Collapsing exchange-rate regimes: some linear examples", *Journal of International Economics* 17(1-2).
- Gabaix, X. and M. Maggiori (2015), "International liquidity and exchange rate dynamics", *Quarterly Journal of Economics* 130(3).
- Galí, J. and T. Monacelli (2005), "Monetary policy and exchange rate volatility in a small open economy", *Review of Economic Studies* 72(3).
- Ilinski, K. (1997), *Physics of Finance: Gauge Modelling in Non-Equilibrium Pricing*, arXiv:hep-th/9710148.
- Jordà, Ò., M. Schularick and A. M. Taylor (2020), "The effects of quasi-random monetary experiments", *Journal of Monetary Economics* 112.
- Krugman, P. (1979), "A model of balance-of-payments crises", *Journal of Money, Credit and Banking* 11(3).
- Mundell, R. A. (1963), "Capital mobility and stabilization policy under fixed and flexible exchange rates", *Canadian Journal of Economics and Political Science* 29(4).
- Obstfeld, M., J. C. Shambaugh and A. M. Taylor (2005), "The trilemma in history: tradeoffs among exchange rates, monetary policies, and capital mobility", *Review of Economics and Statistics* 87(3).
- Rey, H. (2013), "Dilemma not trilemma: the global financial cycle and monetary policy independence", Jackson Hole Economic Policy Symposium.
- Rime, D., A. Schrimpf and O. Syrstad (2022), "Covered interest parity arbitrage", *Review of Financial Studies* 35(11); earlier as BIS Working Paper 651.

---

## 11. Structural checks, B63-8

These are structural: they check the algebra and its implementation. They are run
by [`../experiments/b63_trilemma_check.py`](../experiments/b63_trilemma_check.py),
and the record, with the configuration it ran under, is
[`../results/b63_trilemma_check.json`](../results/b63_trilemma_check.json).
**All four pass.**

1. The plaquette sum is unchanged by any change of units at its four positions,
   and equals the closed form of §1, to within `1e-12` over 1,000 draws.
2. On random currency graphs, the dimension of the set of rate vectors that satisfy
   Corollary 8.1's equalities equals `b_0(P_t)`. Over 400 graphs of 3 to 10
   currencies: rates constant on components admit no positive cycle in 400 of 400;
   moving one rate by `0.001`, with every forward re-priced, creates a positive
   cycle in 327 of the 327 graphs where that currency shares a component and in
   none of the 73 where it is alone. For one-way pegs, a directed 3-cycle forces
   equal rates, and two strongly connected components joined one way leave their
   rates unrelated in either direction.
3. With a credible peg and both orientations open, the set of feasible `r_k - r_l`
   is exactly the band of Corollary 8.3: over 20 spread draws, the first with no
   spreads, the endpoints found by bisection lie within `1e-9` of
   `-(sigma_bar + beta_k)` and `sigma_bar + beta_l`.
4. The shape of that set in five configurations: one direction closed at every date
   (unbounded both ways); closed at `t+1` only (lower bound only); class-split
   one-way conversions with agent edges at par (the band); the same with the agent
   edges removed (unbounded); a float with a forward whose weight is free (every
   difference feasible). All five come back in the registered shape.

---

## 12. Scope

- **Only closed loops enter.** A position held open over a date, with its return leg
  at a rate unknown at entry, is a carry and enters no cycle sum, so nothing here
  depends on uncovered parity or on any premium.
- **The statements say which differences are pinned.** How an authority sets its
  rate, and which side moves once a difference is pinned, lie outside the cycle
  sums (§6).
- **Quantities belong to the flow side.** How long a peg holds against a non-zero
  sum is capacity over flow (§7), read on the A track.
