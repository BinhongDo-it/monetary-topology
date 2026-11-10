# Where the standard price constructions sit on the agent edge

**Status: positioning note. No theorem is proved here and no data is analysed.**
Every construction below is placed from its own text, quoted. The theorems it leans
on are proved in [b1_theorem.md](b1_theorem.md) and
[b4_directed_edges.md](b4_directed_edges.md).

---

## 1. The axis

[b1_theorem.md](b1_theorem.md) §8 states assumption A1, that agent edges carry
weight zero, and says it requires that *the position trades at a single price
independent of who holds it*. The same section says *It is where all the economics
is*. That edge has three settings:

```
t = 0             changing who holds the position costs nothing    A1 holds; one price per position
0 < t < ∞         it can be changed, at a cost                     the square is a cycle; its sum is measurable
edge absent       it cannot be changed                             Γ is disconnected in the agent direction;
                                                                   the square is not a cycle (H⁰)
```

For `t ≠ 0` the square sum is `w_a(i,j) − w_b(i,j) + t_ab(j) − t_ab(i)`, as given in
the same section.

## 2. The standard constructions, placed

| Construction | Where it sits | The assumption that puts it there, in its own words |
|---|---|---|
| No-arbitrage asset pricing, complete markets | `t = 0` | Free portfolio formation. Cochrane names what it excludes: *It rules out short sales constraints, bid/ask spreads, leverage limitations* |
| General equilibrium with one price per good | `t = 0` | *a full range of perfectly competitive markets* (Shell, *New Palgrave*), with full participation |
| Second-degree price discrimination (screening) | `t = 0`, in the type direction | The incentive constraint `θ ∈ argmax_{θ̂} v(x(θ̂), θ) − T(θ̂)` (MIT 14.271, lecture 3). Writing that argmax concedes that every type can reach the bundle designed for every other type |
| Third-degree price discrimination | edge absent | Stole's third feasibility condition: *arbitrage across differently priced goods is infeasible* |
| First-degree price discrimination | edge absent | One reservation price per buyer, and no resale |
| Search with price dispersion (Burdett and Judd 1983) | `t = 0` | *consumers are identical*; consumers differ only in how many prices they observe. The posted price is the same number for anyone who walks in |
| The assignment game (Shapley and Shubik 1972) | `t = 0`, with the inequality applied to pairs that did not trade | See §4 |
| Sunspot immunity | not even at a vertex | Full participation. Shell: *If a random variable is realized before your birth, you cannot buy securities dependent on its realization* |

Stole's survey (*Handbook of Industrial Organization*, vol. 3, ch. 34) gives the
three general conditions verbatim: *(i) firm(s) have short-run market power, (ii)
consumers can be segmented either directly or indirectly, and (iii) arbitrage across
differently priced goods is infeasible.* It also records that Pigou's "second
degree" was a step-function approximation to the first, while today's usage means
indirect segmentation through nonlinear prices. This note uses today's meaning.

**Second- and third-degree price discrimination sit at the two ends of one axis.**
The second degree needs the incentive constraint to be writable, so it must let each
type pass as another (the edge is open and free) and then make passing unprofitable
through the menu. The third degree needs to post different numbers to two classes,
so it must cut the edge. Calling them two "degrees" of one thing presents the two
endpoints of one axis as two depths of the same practice.

## 3. The two ends each have a law, and they are limits of one quantity

```
t = 0          classes are forced to agree   one distinct value survives          Theorem 1
edge absent    classes need not agree        as many values as the rule writes     the counting law
0 < t < ∞      neither law applies           the loop sum is a measurable number   what the carriers read
```

The counting law ([b43_counting_theorem.md](b43_counting_theorem.md)) is therefore
the reading of this axis at the end where the edge is cut, and Theorem 1 is its
reading at the other end. Neither law covers the interior, and the interior is
where this framework measures.

The standard family also has a third move: set `t` finite and nonzero, that is,
admit frictions, writing observed terms as differences of a scalar potential plus a
symmetric friction. [b4_directed_edges.md](b4_directed_edges.md) Corollary 6.1
states the whole region this occupies: `ρ = |S − S'| / −(S + S')` is zero on every
cycle if and only if the antisymmetric part is exact, that is, if and only if some
scalar price field plus some symmetric friction reproduces every observed term.
`ρ > 0` on one cycle rules out every such pair. `ρ` has been read at a median of
`0.2000` on B13 and `0.2552` on B44 ([RESULTS.md](../RESULTS.md)).

The interior of the axis also has a literature of its own: switching costs
(Klemperer 1987, *Quarterly Journal of Economics*; Farrell and Klemperer, *Handbook of Industrial Organization*, vol. 3,
ch. 31) and behaviour-based price discrimination (Fudenberg and Tirole, 2000,
customer poaching). There `t` varies continuously across consumers and that
literature has its own results. Its `t` is a per-consumer scalar added to a price,
and each consumer still carries a utility function, so the placement in §5 below is
unaffected. UK regulators have measured this interior at the level of firms: the
CMA estimated the loyalty penalty at *around £4 billion in total across the 5
markets* (*Tackling the loyalty penalty*, 19 December 2018), and after the FCA's
rule that a renewal price may not exceed the equivalent new-business price took
effect on 1 January 2022, the home-insurance gap between an existing and a new
customer fell from `£95.38` to `£49.17` (FCA Evaluation Paper 25/2, July 2025).

## 4. The assignment game: the same inequality, a different object

Shapley and Shubik's core condition is `u_i + v_j ≥ a_ij` for every pair, with
equality on the pairs the optimal assignment matches, and their Theorem 2 reads
*the core of an assignment game is precisely the set of solutions of the LP dual of
the corresponding assignment problem*.

Set `φ(i) = −u_i` for buyers and `φ(j) = v_j` for sellers. The core condition becomes
`ω(i, j) ≤ φ(j) − φ(i)` with `ω(i, j) = a_ij`, which is the definition of a
sub-potential in [b4_directed_edges.md](b4_directed_edges.md). Adding a reverse edge
`ω(j, i) = −a_ij` on each matched pair turns the equality on matched pairs into the
two inequalities holding together. A directed cycle then has the form
`i₁ → j₁ → i₂ → … → j_m → i₁`, with reverse edges only on matched pairs, and its sum
is the value of reassigning that subset minus the value of the assignment on it.
**Every directed cycle sum is `≤ 0` exactly when no reassignment of any subset does
better, so Theorem 4 returns the classical nonemptiness condition of the core.** The
translation is the content here; Theorem 4 is the standard shortest-path condition
and the LP duality is older.

The slack means different things on the two sides:

| | `φ(v) − φ(u) − ω(u, v)` is |
|---|---|
| this framework | the friction paid on an edge that was travelled, `ω̄ = ½(ω(u,v) + ω(v,u)) ≤ 0` |
| the assignment game | the shortfall on a pair that never traded |

In the assignment game `ω̄ ≡ 0`: a matched edge is antisymmetric (one side gets `u`,
the other `v`, summing to `a_ij`) and an unmatched pair is one-way. There is no
friction anywhere in the model, so `ρ` is undefined there rather than zero. The
assignment game therefore sits at the same endpoint as complete markets, and uses
the inequality on counterfactual pairs. A friction extension and the assignment
game use one inequality to say two different things.

## 5. Where each degree of price discrimination assumes `D = 0`

`D` is the non-exact part of the term field; `D = 0` exactly when a scalar potential
on positions generates every term. Each degree places that assumption somewhere
different.

| Degree | Where `D = 0` sits | What is assumed |
|---|---|---|
| first | `r_i` is a number | what a buyer will pay is a scalar attached to the person, independent of what else is in view |
| second | quasilinear utility, `v(q, θ) − T` | money enters utility separably and linearly, so everything is priced against one numéraire |
| second | single crossing, `v_qθ > 0` | one scalar index orders all types |
| second | the incentive constraint | one function `v(·, θ)` ranks every item on the menu, whatever order they are compared in |
| second | local incentive compatibility, `U(θ) = U(θ̲) + ∫ v_θ(x(s), s) ds` | a line integral in type space, path independent because types are one-dimensional |
| third | `D_i(p_i)` for each block | within a block a scalar price maps to a scalar quantity, and blocks have no cross terms |
| third | one marginal cost | the seller side is a scalar too |

(Formulas from MIT 14.271, Industrial Organization I, lecture 3; the third-degree
condition `(p_i* − c) / p_i* = − 1 / ε_i(p_i*)` is from the same source and from
Stole.)

The incentive constraint reads `U(θ, menu(θ)) ≥ U(θ, menu(θ'))` for every `θ'`, and
that needs one `U` ranking every option. **When `D ≠ 0` the constraint is not
violated. It cannot be written.**

A small instance, inside one shopper and one trip. Bought alone, fresh food is
compared on cooking effort and nutrition and snacks are compared with other snacks.
Bought together, the snacks can be dropped because they are not nutritious and they
fatten, though nutrition was never the reason to buy them. The same person, the same
day, the same two goods; the budget does not bind, and what is given up is the
cheapest buy-one-get-one tier. On positions `{fresh, snack, money}`, the terms of
snack against money depend on the route: reached directly the reference set is other
snacks, reached through fresh food it is the nutrition axis. **`money → fresh →
snack → money` and `money → snack → money` do not return the same number. The
reference set is a function of the path, not of the good**, and it happens with no
market, no arbitrageur and no institution. The ordering of `{two packs of crisps}`
against `{nothing}` depends on whether fresh food is in the basket, so no single `U`
of the kind the incentive constraint needs exists here.

The last row of the second degree is the one no assumption list shows. Every
1-form on a one-dimensional manifold is closed, so path independence of the local
incentive integral is a consequence of the dimension of the type space rather than
an assumption. The screening literature records that the step fails once types have
more dimensions. Rochet and Choné (1998, *Econometrica* 66(4)): *one does not know
the direction of the (local) incentive compatibility constraints that will be
binding*.

So the second degree sits at `t = 0` for two independent reasons, set in two
different places:

```
the incentive constraint    sets the cost of taking another identity to zero    on the class edge
one-dimensional types       makes integrability hold automatically             on the dimension of the base space
```

## 6. One operator on three base spaces

Three literatures each require a 1-form to be closed and give the condition a
different name.

| | Base space | The 1-form | The closedness condition | Who tests it |
|---|---|---|---|---|
| this framework | positions × classes, a graph | the term on each edge, `ω` | a potential exists iff every cycle sums to zero (Theorem 1) | read on the carriers in [RESULTS.md](../RESULTS.md) |
| consumer side | price space | compensated demand `h(p)` | Slutsky symmetry, `∂h_i/∂p_j = ∂h_j/∂p_i` | untestable on the aggregate data applied work uses |
| screening side | type space | the allocation `x(θ)` | implementability, `Dx(θ)` symmetric | `x(θ)` is not observed |

On the graph the condition is a cycle sum; on the two continuous spaces it is
symmetry of a Jacobian. Both say that the integral of the form around every closed
chain is zero.

The consumer-side untestability has a source. Kono, *Untestability of Average
Slutsky Symmetry* (arXiv:2501.18923): *its identified set always contains a
symmetric matrix*. Gunsilius and Sithole (arXiv:2505.05603) give a testable form at
the level of the individual. On the screening side there is no independent reading
of `θ`, so the symmetry of `Dx(θ)` has nothing to be compared with.

This framework's base space is positions and classes, and both are written down at
the registration point: a class is a block a programme names, a position is a place
a claim can be held. Both indices are printed. So closedness here can be computed
from posted prices. B58-10 found `7` of `53` published residential electricity
tariffs writing time of use or voltage into the argument of `T`, so the
multidimensional case is not a hypothetical corner.

## 7. Inside the endpoint: the orthodox and heterodox families share one summand

§2 places constructions on the axis. This section places the price theories that sit
at the same point relative to one another.

Write the enlarged graph as `Γ = G □ H`, positions by classes. Each family below
carries one price per good (or per good and date), which takes the class graph `H`
to a single point. Then `Γ = G`, there is no square, and `H¹(Γ)` has only the
position summand.

| Station | Family | Class graph | Position side |
|---|---|---|---|
| [B0d](b0d_new_keynesian.md) | New Keynesian | a point | `[ω] = 0` by construction for the members B0d surveys: a scalar price field, every cycle zero |
| [B65](b65_post_keynesian.md) | Post-Keynesian, Kaleckian | a point | nonzero, one term per class of good: a production cycle carries `log(1+μ_j)`, with the `μ_j` allowed to differ |
| [B66](b66_mmt.md) | MMT | a point, the sovereign outside the graph | nonzero; the question is which edges lie on cycles that can be walked |
| [B67](b67_prices_of_production.md) | Sraffa, classical | a point | nonzero and all equal, `log(1+r)`: one more equation than B65 |
| [B68](b68_value_field.md) | Marx | a point | zero on the member of the family with `r = 0`, nonzero on the rest |
| [B69](b69_okishio.md) | Okishio | a point | the same family; once positions carry dates the cycle sum is no longer one number |

MMT distinguishes issuer from user, and that distinction is about positions (who can
create the unit), so `D = 0` holds for it too. The B0d row says that the object New
Keynesian models write, a scalar on positions, has zero cycle sums on the graph they
draw. It does not say that family denies profit: profit enters there by drawing the
return inside the input bundle, the second shape below. B68 Corollary 13.3 reads it
that way.

Every difference among these families is one of three shapes:

```
1  which equation is added                 B65 one μ_j per class  →  B67 all equal
2  whether an edge is drawn inside a cycle  B68 Corollary 13.3: with the normal return inside
                                            the input bundle, every member reads zero on every cycle
3  whether positions carry dates            B69: with the two legs at different dates the cycle
                                            sum takes both p_t and p_{t+1}
```

None of the three produces `D`. Each changes a constraint, a drawing, or an index on
the position side. **The orthodox and heterodox price theories sit at one endpoint
of one axis, their disputes all happen on the position graph inside it, and `ρ > 0`
lies outside the premise they share.** It is a statement about where their common
domain ends, and within that domain each of B65 to B69 derives the family's own
results.

The second shape has a consequence for reading `ρ`. With the return drawn inside the
input bundle every cycle of every member closes, so wherever edge weights are
apportioned by whoever keeps the accounts, `ρ = 0` can be arranged. Where both legs
are printed by a third party it cannot: the two reserve-balance rates in B59 (the
closed list in `12 CFR 204.2(y)`), the per-class withholding rates in B21, the
cancellation fee in B24, the cross-currency loop in B3. **This is why the empirical
arm reads published terms only: there `ρ` cannot be arranged.**

B59 is the cell none of these families can hold. One debtor (a Federal Reserve Bank),
one instrument (a balance there), one position: an eligible institution earns IORB
and a Federal Home Loan Bank earns zero. Every object above has one index, so there
is nowhere to put a class difference. The question lies inside the domain price
theory claims, and this framework answers it.

The same holds for the further families. Joint production and fixed capital
([b70_joint_production.md](b70_joint_production.md) Corollary 15.2): the known
difficulties there (negative labour values, no positive price at some rates, under-
or over-determined price systems) all occur on the position side while every
construction still carries one price per good, or per good and age. Austrian
roundaboutness ([b74_roundaboutness.md](b74_roundaboutness.md)) is the third shape,
and its disagreement is bounded: how often two techniques can swap order is capped
by the sign changes of the difference of their profiles (Descartes), a count that
contains no profit rate. Von Neumann ([b71_von_neumann.md](b71_von_neumann.md))
replaces equalities with inequalities and complementary slackness, a generalisation
of the first shape. Banking and financial intermediation, the insurance separating
equilibrium (whose incentive constraint is `t = 0`, as in second-degree
discrimination), mechanism design, market microstructure, trade with heterogeneous
firms, the general-equilibrium family, optimal taxation and non-price rationing all
take the class graph to a point as well.

Two families sit differently:

1. **Matched employer-employee wage models**, `w_ij = α_i + ψ_j + residual`, write the
   class graph down and assert the field is exact on it, and the literature names and
   measures the residual (match effects). That is a registered `D = 0` point
   prediction rather than an empty summand. Its two legs are apportioned by the
   regression (the connected set, the functional form, the bias correction all move
   `ψ`), so by the argument above `ρ` can be arranged there in either direction.
2. **Revenue management** is a fourth shape: the price stays and the sale is refused.
   A protection level says whether this class can reach this position now, which is a
   statement about reachability. It lives in `H⁰` and produces no `D` and no cycle
   sum. The fare ladder, set by matching competitors, lives in `H¹`; which rung is open
   lives in `H⁰`.

## 8. Market power and psychology do not leave the zero set

The standard construction indexes a field the world writes with two indices
(position, holder class) by one. [b1_theorem.md](b1_theorem.md) Corollary 5.1 gives
the cost of that as exactly quadratic, and Corollary 5.3 fixes its size by the spectra
of the two graphs before any price is chosen.

- **Market power** moves the level of `φ`, a one-index object. However large, it
  keeps `w = dφ` exact and every cycle sum zero. It can raise a price; it cannot
  produce a cycle that fails to close.
- **Psychology**: the scope paragraph of Corollary 5.5 counts the three slots through
  which behavioural extensions enter. None introduces the class index into the field.
- **Irrationality** is not needed either for the second source of bias, reach
  ([b29_locality_theorem.md](b29_locality_theorem.md), Theorem 7): with `L·r < n`,
  arbitrage drives every cycle it can walk to zero and cannot touch the one it cannot
  reach, while every agent arbitrages perfectly within reach.

**A one-index model does not leave the zero set however much friction or psychology
is added, because the slots those additions enter cannot reach the missing index.**

## 9. Further constructions, placed

These are placed by the shape of each construction.

1. **Commodity taxation (Diamond and Mirrlees 1971) is a fourth cell on the axis:
   `t ≠ 0` and exact.** The wedge is real money, differs by good and is printed by a
   third party, and it is a difference of two node fields, so every square is
   identically zero. What decides `ρ` is therefore whether the wedge factors, not
   how large or how public it is: a class that faces a complete price vector over all
   goods gives `ρ ≡ 0` however large the edge. Where the Diamond and Mirrlees premises
   break the wedge stops factoring; the cleanest case is the input-tax deduction ratio
   under exempt and partly exempt supply (B122 in [RESULTS.md](../RESULTS.md)).
2. **Signalling (Spence 1973).** `c(y, θ)` is the cost of being read as a different
   type: finite, class-specific, asymmetric by construction. The price field is still
   `w(y)`, one index. So finite asymmetric `t` is necessary for `D > 0` but not
   sufficient: the party posting the price must also see the class. When it does not,
   the price attaches to an observable proxy, and a proxy is a position.
3. **Mechanism design and auctions.** Revenue equivalence is the statement that the
   payment field is exact in the type direction, proved by that literature itself.
   Rochet's (1987) cyclical monotonicity is the cycle condition of Theorem 4, and, as
   with the assignment game in §4, the slack lives on pairs never traded, so `ω̄ ≡ 0`
   and `ρ` is undefined. The resale literature is the one place this family sweeps
   the price of the agent edge as a parameter (full resale collapses discrimination,
   limited resale sits between), and the edge it travels is one-way on a one-point
   position graph, so `ρ` is still not readable
   ([b4_directed_edges.md](b4_directed_edges.md) §5.2).
4. **Gravity with heterogeneous firms.** Trade-cost asymmetry is acknowledged, and is
   estimated as an exporter fixed effect. A fixed effect on a node is a scalar
   potential on a node, exact by definition, so `S − S' = 0`. Asymmetry written as a
   property of the origin is a potential difference by construction; only asymmetry
   written as a property of the edge pair can fail to be. This family is held at
   `ρ = 0` by the shape of the estimated equation rather than by an assumption of
   symmetry.
5. **General equilibrium.** Full participation does two jobs in the table of §2: where
   it holds it gives `t = 0`, and where it fails (sunspots) it removes the vertex.
   Restricted participation and personalised prices (Lindahl, clubs) sit at the
   edge-absent end, for the same reason as third-degree discrimination. None reaches
   `ρ > 0`: a two-index price list alone is still an exact field, and `ρ > 0` needs an
   independently observed cost of changing class.
6. **Market microstructure supplies the denominator of `ρ`.** `−(S + S')` is the
   symmetric friction, and microstructure theory computes it. **With the denominator
   charged in full by that theory, the numerator is still nonzero, so the nonzero
   cannot come from friction left out of the account.** The French financial
   transactions tax, charged on the buyer with a market-making exemption (*Code
   général des impôts*, art. 235 ter ZD), is a third instance of the B59 shape.
7. **Two-sided markets name the agent edge.** Price coherence and the no-surcharge rule
   are that literature's words for a cut agent edge, and it proves a theorem at each
   end (neutrality where the edge is open at `t = 0`, a price structure that carries
   content where it is cut). The interior has no reading there, and the interchange
   schedules the card networks publish sit in it (B123 in [RESULTS.md](../RESULTS.md)).
8. **Rationing by waiting (Barzel 1974).** With two or more positions the full price
   `p_j + w_i·T_j` carries the cross term `(w_a − w_b)(T_1 − T_2)`, a position property
   times a holder property, and it lives on the square. Full dissipation of waiting
   costs, Barzel's central result, is equivalent in the split to a zero antisymmetric
   part. In a fixed-capacity queue priority is zero-sum, and that zero-sum part is the
   numerator of `ρ` by construction.

## 10. The three degrees as special cases

Stole's second and third conditions (segmentation, blocked arbitrage) are this
framework's registration point and edge deletion, and they are older than this
framework. The degrees differ from it in what each adds.

```
this framework          partition + registration point + edge deletion       ⇒  the number of values
third degree            the above + elasticity as the basis of grouping
                        + optimisation + separable blocks + scalar MC         ⇒  the ratios between values
```

**Price discrimination needs a superset of what this framework needs; the extra
premises buy ratios, where this framework predicts a count.** The whole empirical
content of third degree is the inverse elasticity rule, a first-order condition, so
without optimisation it reduces to "different groups pay different prices".

**First degree.** It needs a scalar reservation price per buyer; single-item trades
with no bundle and nothing else in view; no resale; and a seller who reads the number
from a register rather than inferring it. Under all four, first degree is a limit of
the counting law: as many classes as registrable persons, one value each. A seller who
infers the number from behaviour is running a noisy third degree.

**Second degree.** Quasilinearity asks for one numéraire everything is priced
against; `v(q, θ)` asks that the basket not be an argument (the value of a good does
not depend on what else is bought); single crossing asks that buyers differ along one
dimension on this margin; local incentive compatibility follows from that
dimension. Together: **one product line, one quality or quantity dimension, bought
alone, buyers differing in one thing.** There `D = 0` on that subgraph and both give
the same answer. It fails in the second condition when the basket enters (the
shopping trip in §5), in the third and fourth when buyers differ in two things (time
value and risk), and in the first when the numéraire is not commensurable across two
positions.

**Third degree.** Of its five conditions, a given observable partition and blocked
resale between segments are this framework's; a scalar demand `D_i(p_i)` per segment
with no cross terms, a scalar marginal cost, and profit maximisation are added (the
last is not among Stole's three feasibility conditions). On the carriers read here the
added premises did not hold: B56-5 found the inverse elasticity rule at none of three
operators, and in B58 the target of `19` pairs is bound by a named document and the
seller of `1` pair is a statute ([RESULTS.md](../RESULTS.md)).

```
all conditions hold       their answer = this framework's answer + a refinement about ratios
some hold                 this framework gives a count; they give no ratio
none hold                 this framework gives a count; they have no object
```

**Third-degree price discrimination is a special case of this framework under a set
of conditions that can be written down**, and the three tables above are that
statement in checkable form. They are taken from Stole ch. 34, MIT 14.271 lecture 3
and Rochet and Choné (1998); conditions those texts do not state are not added here.

## 11. A martingale is exactness along time, and the two repairs

After a numéraire and a change of measure, a martingale says that the time axis
carries no residual: **exactness restricted to time**. Weakening it is weakening
exactness.

[b4_directed_edges.md](b4_directed_edges.md) has the weakened object with theorems.
`φ` is a sub-potential of `ω` when `ω(u, v) ≤ φ(v) − φ(u)` on every directed edge, the
supermartingale condition on a graph. Theorem 4: a sub-potential exists iff every
directed cycle sum is `≤ 0`. Theorem 6(2): one with zero slack everywhere exists iff
`ω̄ ≡ 0` and `ŵ` is exact. **No-arbitrage buys the existence of a sub-potential and
nothing about exactness.** Theorem 6(4) bounds one part by the other,
`|S − S'| ≤ −(S + S')`, which is why the registered quantity is `ρ ∈ [0, 1]`.

The same failure admits two repairs:

```
keep the equality, widen the object into a band,
and assert a martingale exists inside it                  →  an existence statement
keep the posted terms, weaken the equality to an
inequality, and measure the slack                         →  a number in [0, 1]
```

The first is the consistent price system of the transaction-cost literature, which
places the imprecision in the width of the object. This framework leaves it on the
equality and measures it.

## 12. Scope

1. The table in §2 covers the constructions whose text was read. It is not a census
   of the family.
2. Each construction is correct at its own endpoint. What is placed here is scope.
3. The two endpoints are two different routes to a single price: at `t = 0` the
   square closes; with the edge absent there is no square. Writing both as one
   phrase, "the standard theory assumes `D = 0`", merges two things this note keeps
   apart.
4. §6 places the same operator on three spaces. It does not claim one theorem, and
   it does not claim that Slutsky symmetry is equivalent to `D = 0`: one is
   exactness of compensated demand in price space, the other a scalar potential on
   positions.
5. §7 does not claim the families are one theory. Their position graphs, constraints
   and quantities of interest differ, and each disagreement in §7 is a substantive
   question with its own readings. What is shared is the treatment of the class
   dimension, and that treatment is a premise.
6. `ρ > 0` refutes none of the families in §7 inside its own domain. It says where
   that domain ends.
7. §10 does not claim the added premises fail in general; it reports the carriers
   read here.
