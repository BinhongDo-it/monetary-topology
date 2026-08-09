# B0: what is being claimed, and what is deliberately not

Read this before the empirical documents. It is short, and it exists because the
first objection every reader raises is one this project is not making.

---

## 1. The claim

> Given a coordination system represented by a price or claim field `ω`, if `ω`
> carries a non-trivial cohomology class — if some cycle sum fails to vanish — then
> `ω` is not globally exact. No global scalar potential exists whose gradient
> reproduces the decentralised local signals. Consequently **no objective,
> whatever its content, can be globally realised by that coordination architecture
> through the price mechanism.**

The last sentence is the whole point and its structure is worth reading twice.

The conclusion does not name an objective. It does not say the outcome is
inefficient, unfair, or worse than some alternative. It says that the mechanism by
which local signals are supposed to aggregate into a global allocation **has no
global object to aggregate into**, and that this holds regardless of what the
global object was supposed to be.

Efficiency, output, longevity, subjective welfare, any weighted combination of
those: the argument does not distinguish between them, because the failure is
upstream of the objective. A gradient ascent needs a function to ascend. If no
function exists whose gradient the local signals are, then following local signals
is not ascent toward anything, and it does not matter what one hoped it was
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

That also makes it narrower, and the narrowness is the price. Establishing that no
global potential exists says nothing about which of the available outcomes is
better. It rules out one specific claim — that the price mechanism aggregates
local information into a global optimum — and rules out nothing else.

---

## 3. What follows, and what does not

**Follows.** Statements of the form "the market will find the efficient
allocation", "prices are sufficient statistics for coordination", and "local
optimisation implements global optimisation" are false on a field with a
non-trivial class. Not approximately true with an error term; false in the sense
that the object they refer to does not exist.

**Follows.** Any policy argument whose load-bearing step is "let the price
mechanism handle it" inherits the failure, whatever the policy's stated goal.

**Does not follow.** That central planning would do better. That is a separate
claim about a different architecture and needs its own argument. Nothing here
supplies one.

**Does not follow.** That anyone behaved badly. Non-integrability is a property of
a field, not an accusation. Every agent in stage B2's twenty million loans may have
acted entirely reasonably.

**Does not follow.** That the outcome is bad. The argument is silent on the
ranking of outcomes because it never introduces a ranking.

**Does not follow.** That markets do not clear. They may clear perfectly. Clearing
is a statement about excess demand; exactness is a statement about whether a
potential exists. A field can clear at every date and still admit no potential.

---

## 4. Where the burden sits after this

Once no global potential exists, the interesting question moves. It is no longer
"is the market efficient", which has become ill-posed. It is:

**Given that local signals do not aggregate, what architecture does the
coordination actually run on, and what does it select for?**

That is a question about mechanism and it is answerable. It is what track A is
for: a simulation in which agents are identical in preferences and abilities, and
the only thing that differs is who is connected to whom. If stratification appears
there, connectivity alone is sufficient to produce it, and the question of what
share it explains in the real economy becomes worth asking rather than assumed
away.

---

## 5. The one place this could be attacked

The argument is a theorem plus a measurement. The theorem is not the weak point:
Theorem 1 in [`b1_theorem.md`](b1_theorem.md) is an equivalence with an elementary
proof and no economic assumptions in it.

The weak point is the identification of the measured object with the field the
claim is about. Stage B2 measures dispersion in mortgage financing terms at fixed
position and date, and Theorem 3 shows that quantity **is** the holonomy of the
four-cycles. The step a critic should press is whether those four-cycles are the
relevant cycles of the actual economy, or an artefact of how the position space was
carved.

That is the right place to push, it is recorded in `b1_theorem.md` §8 as assumption
A1, and it is why the graded placebo in `b2_measurement.md` §8.1 exists: it
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
