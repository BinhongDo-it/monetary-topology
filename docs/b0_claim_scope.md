# B0: what is being claimed, and what is deliberately not

Read this before the empirical documents. Sections 1 to 6 are short, and they exist
because the first objection every reader raises is one this project is not making.
Section 7 answers the objections that come after it.

---

## 1. The claim

> Given a coordination system represented by a price or claim field `ω`, if `ω`
> carries a non-trivial cohomology class — if some cycle sum fails to vanish — then
> `ω` is not globally exact. No global scalar potential exists whose gradient
> reproduces the decentralised local signals. Consequently **no objective,
> whatever its content, can be globally realised by that coordination architecture
> through the price mechanism**, in which the local signals serve as the gradient of
> the objective.

The last sentence is the whole point and its structure is worth reading twice.

The conclusion does not name an objective. It does not say the outcome is
unfair or worse than some chosen alternative. It says that the mechanism by
which local signals are supposed to aggregate into a global allocation **has no
global object to aggregate into**, and that this holds regardless of what the
global object was supposed to be. That the outcome is also not Pareto optimal
follows from the same inequality under conditions stated in
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
section 8.2a, and needs no chosen criterion either.

Efficiency, output, longevity, subjective welfare, any weighted combination of
those: the argument does not distinguish between them, because the failure is
upstream of the objective. A gradient ascent needs a function to ascend. If no
function exists whose gradient the local signals are, then following local signals
is not gradient ascent on anything, and it does not matter what one hoped it was
ascending toward.

---

## 2. What this buys, and why it is stronger than the usual argument

The standard critique of decentralised allocation has to specify a welfare
criterion, argue that the observed outcome scores badly on it, and then defend the
criterion. Every step is contestable and the last is where the argument usually
dies, because welfare criteria are exactly where reasonable people disagree.

**This argument never enters that terrain.** It requires no interpersonal
comparison, no utility function, no social welfare function, no assumption about
preferences at all. It requires one inequality on one cycle.

Establishing that no global potential exists does not, by itself, rank the
available outcomes. With the inequality alone it rules out one specific claim:
that the price mechanism aggregates local information into a global optimum.
**Where the terms are the classes' effective marginal terms, the same inequality
rules out a second: that the allocation reached is Pareto optimal.** The Pareto
criterion is the one the First Welfare Theorem itself is stated in, so a defence of
decentralised allocation cannot set it aside. It adds each class's own ordering of
bundles and nothing more, with no interpersonal
comparison and no social welfare function, so this verdict stays outside the
contested terrain too. The conditions, and the swap between two
classes that shows it, are in
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
section 8.2a.

---

## 3. What follows, and what does not

**Follows.** Statements of the form "the market will find the efficient
allocation", "prices are sufficient statistics for coordination", and "local
optimisation implements global optimisation" are false on a field with a
non-trivial class. Not approximately true with an error term; false in the sense
that the object they rest on, one common price system whose gradient the local
signals are, does not exist.

**Follows.** Any policy argument whose load-bearing step is "let the price
mechanism handle it" inherits the failure, whatever the policy's stated goal.

**Does not follow.** That central planning would do better. That is a separate
claim about a different architecture and needs its own argument. Nothing here
supplies one.

**Does not follow.** That anyone behaved badly. Non-integrability is a property of
a field, not an accusation. Every agent in stage B2's twenty million loans may have
acted entirely reasonably.

**Does not follow.** That the outcome is bad by a criterion someone has to
choose. The argument introduces no such criterion. The one ranking that needs no
chosen criterion, Pareto dominance, is reached under stated conditions in
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
section 8.2a: where two classes face different terms on one transition, a swap
between them at terms strictly between theirs leaves both better off.

**Does not follow.** That markets do not clear. They may clear perfectly. Clearing
is a statement about excess demand; exactness is a statement about whether a
potential exists. A field can clear at every date and still admit no potential.

**How the result transfers.** Write `P` for the existence of one potential whose
gradient the local signals are, which is condition (1) of Theorem 1 in
[`b1_theorem.md`](b1_theorem.md). A claim that requires `P` is excluded wherever
Corollary 1's inequality holds, and no further proof is needed. Every Follows entry
above is of this kind, since each reaches its outcome through the common price
system that `P` asserts. A theorem that uses `P` as a premise loses that derivation
there. For the First Welfare Theorem,
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
section 8 goes further: on carriers meeting the conditions of its section 8.2a the
theorem's conclusion is itself false, so the first Follows statement, "the market
will find the efficient allocation", is false there in the direct sense too: the
allocation the market found is not Pareto optimal.

**Once a carrier's measured terms are identified with the field `ω` declared here,
which is the empirical step of section 5, every consequence of Theorem 1 and its
corollaries applies to that carrier without a new proof.**

---

## 4. Where the burden sits after this

Once no global potential exists, the interesting question moves. It is no longer
"is the market efficient", which the welfare theorems no longer answer on this
field and which [B0b section 8.2a](b0b_aggregation_and_the_potential.md) answers
in the negative wherever its conditions hold. It is:

**Given that local signals do not aggregate, what architecture does the
coordination actually run on, and what does it select for?**

That is a question about mechanism and it is answerable. It is what track A is
for: a simulation in which agents are identical in preferences and abilities, and
the only thing that differs is who is connected to whom. **Stratification appears
there.** In stage A4, two hundred identical agents run for three hundred rounds over
five seeds. On a complete graph with uniform access, and with inheritance,
education, return heterogeneity and assortative mating all switched off, the Gini
ends at 0.00711 (A4-1). Switching on nothing but the stratified access structure
takes the same economy to 0.93673, the sign holding at five seeds of five (A4-2,
[RESULTS.md](../RESULTS.md)). No agent is more able than any other and none
inherits anything, **so connectivity alone is sufficient to produce
stratification**, and the share it explains in the real economy is a question
worth asking.

---

## 5. Where the argument meets the data

The argument is a theorem plus a measurement. The theorem carries no economic
assumption: Theorem 1 in [`b1_theorem.md`](b1_theorem.md) is an equivalence with
an elementary proof.

The empirical step is the identification of the measured object with the field
the claim is about. Stage B2 measures dispersion in mortgage financing terms at fixed
position and date, and the record keeps two readings of that quantity side by side,
for the reader to choose between.

- **As a square.** Take the dwelling as the position and each borrower as a class.
  A house sells at one price whoever holds it, so A1 of `b1_theorem.md` §8 holds and
  financing sits on the position edge. Theorem 3 then makes the within-cell variance,
  up to a factor of two, the mean squared holonomy of the four-cycles, an identity
  that holds to `1e-16`.
- **As a dispersion at a position.** Take the cell as the position and the borrowers
  as unlabelled. Each borrower is seen at one transition only, so no class can be
  followed to a second position, and the reading is an `H⁰` statement: two loans in
  one cell on different terms.

**Both readings face the same point prediction.** One price per position predicts
zero dispersion inside the cell, and the reading is `0.7831`. Under the square
reading the question at the empirical step is whether those four-cycles are the
relevant cycles of the actual economy, or an artefact of how the position space was
carved.

That question is recorded in `b1_theorem.md` §8 as assumption A1, and it is why the graded placebo in `b2_measurement.md` §8.1 exists: it
suppresses the agent index by programme rule and shows the measured quantity moves
with it. A measurement that responds to a mechanical intervention on the mechanism
is harder to dismiss as an artefact of the carving.

---

## 6. A note on tone, since it affects how this is read

Nothing above is an argument about politics and it should not be read as one. The
claim is that a particular mathematical object does not exist, and that a family of
arguments which presuppose its existence therefore do not go through. People who
disagree sharply about what should be done can agree about that, and the project is
written on the assumption that they might.

---

## 7. Objections, and the answers

Each entry states an objection in its strongest form, answers it, and says where the full
argument lives. Theorem, corollary and section numbers refer to the files linked.

**Two classes convert `i` into `j` at log-terms `w_a(i, j) = 1` and `w_b(i, j) = 2`. Both
take the positive move, and `F(i) = 0`, `F(j) = 1` rises along every move taken. The field
is not exact, yet decentralised improvement reaches the maximum of a common function, so
section 1 is false.**

Section 1 is about gradient ascent: the local signals as the gradient of the objective. In
the example `F(j) − F(i) = 1 = w_a(i, j)` while `w_b(i, j) = 2`, so `F` is the potential of
class `a`'s terms alone, and by Corollary 1 no function is the potential of both. What the
example exhibits is an ordinal potential, a function that rises along every move taken.
Monderer and Shapley (1996, *Games and Economic Behavior*) separate exact potentials, which
exist exactly when closed paths sum to zero, from ordinal ones, which read only the signs of
moves, and a non-exact field can carry an ordinal one. **Those signs depend on the unit of
account; cycle sums do not.** Counting `j` in another unit adds one constant to every
class's `w(i, j)` and leaves the square sum `w_a − w_b = −1` unchanged. With the constant at
`−1.5` the terms become `−0.5` and `+0.5`: class `a` improves by moving `j` to `i`, class `b`
by moving `i` to `j`, and no ordinal potential exists, since one would have to stay level
across the costless transfer between the classes and rise along both moves. In general two
classes' improving directions on an edge agree in every unit system if and only if
`w_a(i, j) = w_b(i, j)`; for `w_a < w_b`, any constant strictly between `−w_b` and `−w_a`
separates them. On a non-zero simple cycle within one class, a choice of units makes every
step improve, and improvement can then run round it for ever. Where improvement terminates from
every start on a finite set, Monderer and Shapley show that some ordinal potential
rationalises it, so "reaches the maximum of some `F`" carries coordination content only when
`F` is fixed before the dynamics run. The state the example reaches is also dominated:
routing class `a`'s unit of `i` through class `b`'s channel yields `e²` units of `j` against
`e`, a gain of `e² − e ≈ 4.67`, whenever `i` passes between the classes at weight zero.
Full argument: §1 above; [`b1_theorem.md`](b1_theorem.md) Corollary 1 and §8, A1.

**An optimal allocation still exists under any continuous objective on a compact feasible
set. The welfare function does not disappear, so nothing has been shown about
optimality.**

Section 1 never says otherwise. What it removes is the route: the claim that the market
reaches that optimum through one price system whose gradient the local signals are (§3,
first entry). Section 1 uses no preferences and so ranks nothing. Add four hypotheses and
the same inequality says more: the square's terms are each class's effective marginal
terms; preferences are locally non-satiated and choices interior, so each class's marginal
rate of substitution equals its own terms; the position passes between the two classes at
weight zero ([`b1_theorem.md`](b1_theorem.md) §8, A1); and the four legs are the same two
positions. Then a swap between `a` and `b` at any rate strictly between `e^{w_a(i, j)}` and
`e^{w_b(i, j)}` leaves both strictly better off to first order, and the observed allocation
is not Pareto optimal. This uses ordinal preferences and no interpersonal comparison: it is
the equal-marginal-rates condition for an interior Pareto optimum (Mas-Colell, Whinston and
Green 1995, chapter 16). If the swap is unavailable, the position cannot pass between the
classes, which is a hole on a named edge and the object this framework locates. So a
non-zero square leaves two branches, a Pareto improvement the market left untaken or a
located barrier. Where the terms are printed in a statute or a published schedule they are
the effective marginal terms by construction, and transferability is the only hypothesis
left to check. Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §8.2a, the
welfare fork.

**Prices are sufficient statistics for each agent's own decision. That is what the price
mechanism does: dispersed knowledge is used without anyone holding the whole.**

A price can be sufficient for one agent on one edge: the agent needs its own terms
`w_a(i, j)` on the edges it faces, and the quote supplies them. The coordination claim is
the next step, that these local sufficiencies add up to a global allocation, and the object
they would add up to is the common potential `φ` whose differences every agent's signals
are. On a non-exact field that object does not exist (Theorem 1), so the step has no
target. The information that decides the matter belongs to cycles and to absent edges. A
square sum is a difference between two classes' terms on one edge, and no single agent
traverses a square ([`b1_theorem.md`](b1_theorem.md) §9.1); a hole is an edge that carries
no price at all. Where the loops and holes are is recorded in no node's price. Full
argument: §1 and §3 above; [`b1_theorem.md`](b1_theorem.md) Theorem 1 and Corollary 1.

**The measured sums are a few basis points. The single price vector is an excellent
approximation, and no model claims more than that.**

Section 1 asks whether a potential exists, and Corollary 1 decides it with one inequality
on one edge. Corollary 5.4 has no tolerance band: the distance `ρ(ω)` to the nearest single
potential is zero exactly on condition (4), and off it
`ρ(ω)² ≥ m · dist(w̄, im d_G)² + ρ_H · D²`, with `ρ_H` fixed by two graph spectra
(Corollaries 5.1 and 5.3). Calling the single price vector an
approximation concedes that `φ` does not exist and that what remains is an approximation
whose error is the quantity measured here (Corollary 1). The named rival family predicts
that quantity to be exactly zero, at every parameter value, as an arithmetic consequence of
its own index sets (Corollary 5.5). A reading is decided against its own measurement floor,
whatever unit it is printed in: the cross-currency cycles of
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §3.3 run at
30.9 to 45.6 basis points against a floor of 2.8 to 3.7, on nine of nine tenors across
eighteen years. How far the field sits from the nearest single potential has its own
closed form (B1 §14); what that distance costs is a separate question the claim does not
need. Full argument: [`b1_theorem.md`](b1_theorem.md) Corollaries 1, 5.3 and 5.4, §10
and §14; the paragraph on 1.7 basis points in the [speedrun](../speedrun/README.md).

**The rival is richer than a posted price. Its models carry funding, execution, tax and
access terms, so a posted scalar price does not establish the zero prediction, and each
model's complete rule has to be reconstructed first.**

Reconstruction sorts every friction into one of two cases, and both are settled. A friction
written as one schedule for every agent, whatever it depends on in the model's own state
space (position, direction, the holder's own holdings), gives two agents in the same state
the same terms on the same transition: `w_a = w_b` edge by edge, so every square has a
zero index part (`D = 0`). Kaplan, Moll and Violante's borrowing wedge is of this kind: households
borrow at `r^{b−} = r^b + κ`, "where κ > 0 is a wedge between borrowing and lending rates",
and `r^b(b)` "summarizes the interest rate schedule faced by households" (quoted from NBER
working paper 21897). Its borrow-and-lend cycle sums to
`log(1 + r^b) − log(1 + r^b + κ) < 0`, all of it in the friction part. Under its hypotheses,
[`b4_directed_edges.md`](b4_directed_edges.md) Corollary 6.1 shows that the scalar account
together with every such friction that is the same on both legs of each edge is exactly
the locus on which one ratio per cycle vanishes, and the index part `S − S′` of every
square is invariant to any friction common to both classes in the sense of Theorem 6(5)
there. A friction written with a class index and paid in one
direction of a shared transition is the other case. In Chen, Cúrdia and Ferrero (2012) unrestricted households
"pay a transaction cost ζt per-unit of long-term bond purchased" and restricted households
"pay no transaction costs", so that model's own field has `w_a ≠ w_b` and `D ≠ 0`; Gertler
and Karadi (2011) write a cost of the same kind on central-bank credit. An access
restriction by class removes an edge for one class, which is a hole and again an index on
the transacting party ([`b1_theorem.md`](b1_theorem.md) §8, A1;
[`b4_directed_edges.md`](b4_directed_edges.md) §6). Either way the single-price zero is not
recovered: the first case keeps the rival's exact zero on every square, which the carriers
read against, and the second concedes the non-zero square. Full argument:
[`b1_theorem.md`](b1_theorem.md) §4 ("Condition (4) read as a reduction") and Corollary 5.5
with its sibling; [`b4_directed_edges.md`](b4_directed_edges.md) Theorem 6 and
Corollary 6.1; [`b0d_new_keynesian.md`](b0d_new_keynesian.md) §1.1 and §4.2.

**New Keynesian models already carry dispersion: Calvo pricing disperses prices, and
heterogeneous-agent models give households different returns.**

Neither puts the index on the transacting class. Calvo dispersion runs across sellers: firm
`i` and firm `i′` post different prices, and every buyer of firm `i` pays `p_i(t)`. However
large it is, `p_i` stays a scalar on positions, `w = dφ` stays exact and every cycle sum
stays zero; nominal rigidity changes the dynamics of `φ`. Heterogeneous returns
`r_a = Σ_k θ_ak r_k` sit in the portfolio weights, a quantity index, and every household
still faces the same `r_k`; in the sequence-space formulation a mutual fund "collects all
household savings" and pays every household the same ex-post return. A square opens when
two classes face different terms on the same transition, and the carriers measure
dispersion across buyers at a fixed position, which is where that index sits. Full
argument: [`b0d_new_keynesian.md`](b0d_new_keynesian.md) §1.2, §2.2 and §4.2;
[`b1_theorem.md`](b1_theorem.md) Corollary 5.5.

**Baqaee and Farhi's wedges `τ_ij` make input costs purchaser-specific, so their model
already carries the index this framework says it lacks.**

In their setup "N producers indexed by i" face "τij ... the input-specific tax wedge on good
j", and "producer i sets a price pi" common to every purchaser of good `i`. The purchaser in
`τ_ij` is producer `i`, which is node `i`: the wedge sits on the edge from `j` to `i`, and
only producer `i` traverses it. An edge wedge can make the common field non-exact on the
production graph (the first summand of [`b1_theorem.md`](b1_theorem.md) Corollary 5.1) and
creates no square, so `D = 0`. Read as classes of purchasers sharing one purchase of `j`,
the wedge gives two sub-cases. If `j` cannot be resold between purchasers, the edge between
them is absent, which is a hole (B1 §8, A1). If it can, the model has written a class index
on a shared transition, its field lives on `Γ` and is non-exact whenever `τ_ij ≠ τ_kj`, which
is the second branch of B0b §2.3 and turns one weight per node into one weight per node and
class. The first branch is answered by measurement: with census tract, year, lien position,
loan purpose, occupancy and dwelling type fixed, 78 per cent of the variance in financing
terms is inside those cells (`0.7831`; `0.8480` under `min_size = 20`), where one price per
good predicts zero. Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §2.3.

**Hulten's frontier and its first-order shift are defined by technology, whatever the
claims field, so the Domar result cannot fail for the reason given.**

The frontier and its shift exist. B0b §2 concerns the identity between that shift and the
Domar weights. Hulten defines the prices as the normalised gradient of the frontier,
`P_i = (∂F/∂Y_i) / (∂F/∂Y_1)`, one vector common to every agent, and the envelope step that
cancels the reallocation terms uses exactly that vector. Where two classes face different
terms on one transition no common `P` exists (Corollary 1), and the identity has no
derivation on those terms. Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §2.1 and
§2.2.

**The representative household's utility and its Taylor expansion exist inside the model,
so the New Keynesian loss function is well defined.**

Inside the model it is. The question is whether it applies to a carrier. The loss is a
second-order expansion of a representative household's utility, and a representative
household is constructed over one price vector faced by every household: aggregate demand
has to be a function of that one vector (Mas-Colell, Whinston and Green 1995, chapter 4).
Where two classes face different terms on the same transition, aggregate demand depends on
several price vectors, and the construction has no common vector to be built over
(Corollary 1).
Every field a model of that family can generate has `w_a = w_b` on every edge, at every parameter
value, so no steady state of the model, efficient or distorted, has the carrier's terms, and
the size of the gap has a closed form ([`b1_theorem.md`](b1_theorem.md) Corollaries 5.1 to
5.4). Expanding around a distorted steady state (Benigno and Woodford 2005) leaves this in
place, since the distortions there are written into one representative household's problem.
The loss has no application to that carrier. Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §8.4;
[`b0d_new_keynesian.md`](b0d_new_keynesian.md) §5.3.

**Enlarge the commodity space so that each good carries its buyer. One price vector exists
again, and the welfare theorem applies.**

Do the enlargement and keep the goods transferable. The class-goods `(a, g)` and `(b, g)`
become vertices of `Γ`, and the fact that the same object passes between the two classes at
weight zero is `Γ`'s agent edge. Theorem 1 condition (2) then asks for one price vector on
`Γ`, and the same non-zero square rules it out: free resale forces `p(a, g) = p(b, g)`, and
equal class-good prices on every position return the single price vector that Corollary 1
excludes. The enlargement has renamed the vertices and kept the cycle. A price vector comes back once the
agent edges are deleted, that is, once `a`'s good can no longer become `b`'s good. That
deletion is the hole this framework locates, and the enlarged economy is then one in which
no two classes trade the same commodity, while the literature applies the theorem to the
unenlarged economy where a common good exists. The statistic's dimension also grows with the
number of classes, the cost recorded under the second branch of B0b §2.3. Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §8.3;
[`b1_theorem.md`](b1_theorem.md) Theorem 1 and §8, A1.

**A non-zero cycle is an arbitrage opportunity, so it will be traded away; or what is
measured is transaction costs.**

A square needs two classes on one edge, and no single trader traverses it
([`b1_theorem.md`](b1_theorem.md) §9.1). If the position passes between the classes at
weight zero and each can trade both directions of the edge at its quoted marginal terms,
then with `σ = w_a(i, j) − w_b(i, j)`, one unit taken round the square in the direction of
`σ`'s sign returns `e^{|σ|}` units: a riskless joint gain. A square that persists is
therefore a joint gain the two classes leave untaken or a failure of one of those
conditions on a named leg, which is a located barrier or friction;
[`b1_theorem.md`](b1_theorem.md) §9.1 records one of the second kind at the most liquid
venue there is. Directed no-arbitrage buys a sub-potential and nothing about exactness: a
potential with all slacks zero exists if and only if the friction part vanishes and the
antisymmetric part is exact ([`b4_directed_edges.md`](b4_directed_edges.md) Theorem 6(2)).
The index part `S − S′` is invariant to any friction common to both classes and bounded by
it, `|S − S′| ≤ −(S + S′)`; on B13's carrier the bound held with zero violations in 49,116
states, ratio median `0.2000`. A transfer cost on the agent edge affects attribution only: a
non-zero sum still proves the field is not exact (B1 §8, A1). Full argument:
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) §3.1 and
§3.2; [`b4_directed_edges.md`](b4_directed_edges.md) §5.

**The within-cell dispersion in mortgage terms is borrower risk, a characteristic the cells
failed to hold fixed.**

Risk-based pricing says that the terms on the same dwelling depend on who borrows, which is
the index `a`. Moving the borrower's risk into the position splits nodes by agent, the
second branch of B0b §2.3, and the resulting object is `Γ`. The cell-pooling form of the
objection is assumption A3 of [`b1_theorem.md`](b1_theorem.md) §8, recorded in
`b2_measurement.md` §8. The graded placebo reads the programme-rule
version directly: the VA funding fee does not vary with credit
score, and the within-cell share is `0.8480` for conventional loans against `0.6666` for VA,
a gap of `+0.1814` against a registered margin of `0.05`, on the tail-insensitive caliber. A
price schedule over a household's state is answered the same way: the placebo reads which
price function a household faces at all, selected by an eligibility edge that state does
not contain. Full argument: §5 above; [`b0d_new_keynesian.md`](b0d_new_keynesian.md)
§2.2.1; `b2_measurement.md` §8.1.

**The A-track model takes the stratified graph as an input, so the stratification it
reports is assumed.**

A0 takes the graph as input and measures what flows over it: inflow to the layer below the
top is unchanged across a twentyfold change in the top's spending propensity (spread `0.000e+00`, A0-4) and
rises from `17.7007` to `48.3919` when one downward edge opens and is widened to weight 0.85 (A0-6). The claim in §4 is the
track's, and the track has a stage built for it. A4 runs two hundred identical agents for
three hundred rounds, with inheritance, education, return heterogeneity and assortative
mating all switched off. On a complete graph with uniform access they end at a Gini of
`0.00711` (A4-1). Turning on nothing but the access structure takes the same economy to
`0.93673`, a gap of `+0.92962` against a floor of `0.05`, with the sign holding at 5 of 5
seeds; the production layer reads `0.59490` against `0.00714` (A4-2). No agent in that run is
more able than another and none inherits anything. A4-6 adds that a matching rule reading
holdings and never the layer label ends up respecting the layers: cross-layer pairing
`0.1610` with connectivity on and `0.1780` with it off, against a uniform-random `0.1809`,
lower at 5 of 5 seeds. Full record: [RESULTS.md](../RESULTS.md), stage A4;
[`a4_causal_primitive.md`](a4_causal_primitive.md) §12.
