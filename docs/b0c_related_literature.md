# B0c: related literature, and how this framework differs from every entry

> ## This framework is original throughout. It was built from first-hand observation of economic news and the construction that grew out of it, and not from any work named below.
>
> ## **That someone else has mentioned a similar-sounding concept is not a precondition on this work.** The entries here are surveyed so that a reader who knows one of them can see how the two relate. In every case the object is different, and the difference is given as a checkable fact rather than as an impression.
>
> ## Where a specific concept of someone else's is actually used, the credit is given at the station that uses it, in context. That is done for clarity, so that the relation between this framework and the others is legible to a reader, rather than putting it in a much more general place with a group of unrelated concepts.

**Status: literature survey.** No theorem is proved here and no data is analysed.

---

## 1. What this file is for

It is not intellectual debt. Nothing in
[`b1_theorem.md`](b1_theorem.md) takes an input from any work named below, and
whether those works are correct does not bear on any result in this repository.

It is a **map of the neighbourhood**. Several constructions in the literature
apply the same standard mathematics, the Helmholtz-Hodge splitting of a field
into an exact part and a remainder, and a reader who knows one of them will want
to know how this framework relates to it. **The answer is the same every time and
it is structural: their object carries no agent index, so on their object the
residual this framework measures is identically zero.** That is a statement about
the objects, provable from Corollary 5.4.

Three entries earn a full treatment. The rest are a lineage mention, which is
cheap and buys legibility, or they are dropped and the reason is given.

---

## 2. Kemp-Benedict (2012): a neighbouring construction on a different object

Kemp-Benedict, E. (2012), *General Equilibrium as a Topological Field Theory*,
SEI working paper, arXiv:1209.1705 [q-fin.GN]. No journal version, so arXiv is
the version of record.

He writes Walrasian tatonnement as a Langevin equation, applies Faddeev-Popov,
and obtains an action that is a pure BRST gauge-fixing term, `S = {Q, Psi}` at
his (16), so the theory is topological. His (2) splits the drift by
Helmholtz-Hodge,

```
dp/dt  =  - grad V(p)  +  A_bar(p)
```

and his §3.1 fixes the degenerate case: "The Q-symmetry is never broken if the
excess demand function can be written purely as the gradient of a potential, so
that A_bar(p)" is zero. There the theory localises on critical points and, in his
words, "perturbatively ... the field theory behaves as general equilibrium
posits."

**The Helmholtz-Hodge splitting of a field into an exact part and a remainder is
nineteenth-century mathematics and belongs to nobody. A sentence of the form
"theory X is the degenerate case of a larger object obtained by that splitting"
is an instance of standard mathematics applied to whatever object the writer had.
It carries a claim only together with the object, and the objects here are
different.

**The objects are different, and this file proves it rather than arguing it.**
His state is the price vector `p`, one component per good, common to every agent;
no agent index appears in his paper. On that object `D = 0` identically, so by
Corollary 5.4 `R = 0` identically. His construction occupies the first summand of
Corollary 5.1, `m * dist(w_bar, im d_G)^2`, and the whole content of Theorem 5 is
the second summand, which Corollary 5.1 shows carries no cross term with the
first. **Two summands with no cross term are orthogonal contributions, and that
is the accurate description of the relation.** Anyone can check it by reading his
§2 against that corollary.

**The relation, stated once: two orthogonal summands.** §5 gives the paragraph
in the form a manuscript should use.


**The mechanism is not his, and this is provable from Corollary 5.1 rather than
argued.** His state is the price vector `p`, one component per good, common to
every agent; no agent index appears in his paper. On that object `D = 0`
identically, so by Corollary 5.4 `R = 0` identically. His construction therefore
occupies the first summand of Corollary 5.1, `m * dist(w_bar, im d_G)^2`, and the
entire content of Theorem 5 is the second summand, which Corollary 5.1 shows
carries no cross term with the first. Anyone can check this by reading his §2
against that corollary.

**He has one thing this framework does not**, and the placement should say so:
his instanton sector gives endogenous transitions between critical points with no
exogenous shock. Whether this carrier has anything of that shape was put to the
A-track and answered no; see [`a2e_gate.md`](a2e_gate.md). A manuscript should
not gesture at future dynamical work here.

**A third generator, labelled as what it is.** The framework advances, **as a
hypothesis and not as a result**, a further source of the same non-exactness,
arrived at independently of his: pricing convention propagated around a cycle of
reference relations, where the product of the conventional factors around the
cycle need not equal one. The construction is arithmetic and trivially available;
what is hypothetical is that observed price formation works this way, and that
hypothesis carries its own observables and is registered on its own. **Nothing in
§14 depends on it**, and it is named here only so that a reader who notices the
closeness of the containment claim knows the generator question has more than one
answer on offer.

**His open problems are not answered here.** His §4: "current economic theory
cannot say what economic conditions produce stable critical points." His §2.1:
after a policy change "the standard method gives no way to choose between them."
Both are equilibrium selection, which this framework does not do.

---

## 2a. HodgeRank: the same decomposition, on a single-index object

Jiang, X., Lim, L.-H., Yao, Y. and Ye, Y., *Statistical ranking and combinatorial
Hodge theory*, Mathematical Programming B (2010), arXiv:0811.1067.

**This is the nearest construction to Theorem 1 in the literature, and it is
listed for that reason rather than for its subject.** Pairwise comparison
data is treated as an **edge flow on a graph**, an antisymmetric function
`X(i,j) = -X(j,i)`, and decomposed by Hodge into three orthogonal parts: a
**gradient** flow `X_ij = s_j - s_i` induced by a potential, which is a global
ranking; a **curl** flow carrying local inconsistency around triangles; and a
**harmonic** flow carrying global cyclic inconsistency. Their reading of the
third: "if the residual is large, then the underlying data is plagued with cyclic
inconsistencies."

**That is the same standard decomposition Theorem 1 uses, on a different
object.** A global potential exists exactly when the cycles close; where they do
not, the obstruction is what remains after projecting onto gradients. **The Hodge
decomposition is standard mathematics and belongs to nobody; what differs between
the two constructions is the object it is applied to.**

**The differentiator is the same one, for the third independent time.** They do
handle multiple comparators: a pairwise ranking matrix `Y^α` is defined per voter
`α`, and the voters are then **aggregated through a weight function `w_ij^α`**.
The index enters the construction and is integrated out before the results. That
is §14.5's second row exactly, and it is the standard move, for the standard
reason.

**Three neighbouring constructions, one differentiator, and it holds in all three.**
Farinelli and Takada introduce investors and prove theorems without the index.
Kemp-Benedict has no index at all. HodgeRank admits raters and aggregates them
away. **In each case the object that survives to the theorem is single-index, and
in each case the construction here refuses that step**, which is what leaves a
Cartesian-product Laplacian to diagonalise and what makes Theorem 5's damping
parameter the agent graph's own spectrum.

**Practical consequence, and it is favourable.** Any station of this project that
needs to read cyclic inconsistency off a graph of asserted comparisons should use
their machinery and cite it. **The instrument is off the shelf; the contribution
is the object it is pointed at.**

**Citation status.** Abstract and section structure read from the arXiv HTML.
**Full text not read**, and the journal volume and pages must be attached before
use.

---

## 3. The lineage, in one sentence

Debreu, G. (1970), *Economies with a Finite Set of Equilibria*, Econometrica
38(3), 387-392, with its Addendum at 38(5), 790, introduces regular economies as
the regular values of the natural projection, and Balasko assembles that
machinery into the equilibrium manifold. **In all of it the price is a single
vector on goods, common to every agent**, so the agent index sits in the
parameters and never in the field. That is the same structural point §2 makes
about Kemp-Benedict and the same one
[`b1_theorem.md`](b1_theorem.md) §14.5 makes about Farinelli and Takada, and one
sentence naming Debreu and Balasko places the lineage, and the construction here
sits outside it for the same structural reason as the other two entries.

**Nothing stronger is claimed.** An earlier draft used Balasko's contractibility
result to argue that the degenerate locus carries no `H^1` and that this
project's cohomology is therefore transverse to it. That argument is withdrawn:
the version that could be verified is about the fixed-resource manifold `E(r)`,
the unrestricted case was not checked, and a defence resting on an unread theorem
is worth less than no defence.

---

## 4. Dropped, and why

**Chichilnisky, and topological social choice.** The obstruction there is to the
existence of an aggregation rule on a space of preferences, and nothing technical
transfers in either direction. Its only function was to show that a topological
obstruction to aggregation is an admissible form of argument in economics, which
is nice to have and load-bearing for nothing. It also proved expensive: a first
draft put the 1980 paper in the wrong journal and attributed to it a theorem that
is in fact Chichilnisky and Heal (1983). If it is ever wanted, one citation
carries the whole branch: Lauwers, L. (2000), *Topological social choice*,
Mathematical Social Sciences 40(1), 1-39.

**Smale.** Was never more than a name in a list. Dropped rather than filled in.

**The three-column comparison table.** It compared this framework against four
literatures on eight rows. Two of those literatures are now dropped and the
remaining comparison is §2, which is shorter and makes the same point with a
corollary instead of a table.

---

## 5. The paragraph a manuscript should use

> A topological reading of general equilibrium has a lineage: Debreu (1970) and
> Balasko establish the equilibrium manifold and its natural projection, and
> Kemp-Benedict (2012) recovers general equilibrium as the perturbative sector of
> a topological field theory, degenerate precisely when the divergence-free part
> of excess demand vanishes. In each of these the price is a single vector on
> goods, common to all agents; where agents appear they appear in the parameters
> and not in the field. The construction here retains the agent index in the
> object, and Corollary 5.1 shows that the distance to the nearest single
> potential splits, with no cross term, into a common-field term, which is where
> that literature lives, and a residual `R` in the disagreement between classes,
> which is identically zero on every object it studies.

Checkable line by line, claims no unification, and states the delta as an
orthogonal summand rather than as a ranking.

---

## 6. Citation status

| source | status |
|---|---|
| Kemp-Benedict, arXiv:1209.1705 | **full text read and verified 2026-08-28.** Equations (2), (14), (15), (16), (17) and the §2.1, §3.1 and §4 quotes are transcribed from it. arXiv is the version of record |
| Debreu (1970), Econometrica 38(3), 387-392 | **record verified 2026-08-28** (JSTOR 1909545), text not read. The **Addendum** at 38(5), 790 (JSTOR 1912219) is also unread; cite both or say why not |
| Balasko, Y. (1988), *Foundations of the Theory of General Equilibrium*, Academic Press | **not read.** Used for a lineage mention only, which needs no theorem number. §3 withdraws the one claim that did |

`b0b` §6's standard applies: a row that cannot be answered by quotation should be
deleted rather than softened.
