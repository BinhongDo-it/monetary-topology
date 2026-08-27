"""A2: support-set contraction on a directed graph.

What this stage adds
--------------------
A0 works on four strata, which is the block aggregation of a graph. A2 runs the
same claim dynamics on the graph itself, so that a question A0 cannot pose
becomes available: not how much is circulating, but **how many nodes the
circulation still reaches**.

The distinction the stage rests on
----------------------------------
Two supports, and they come apart.

``potential_support``
    Nodes reachable from the injection point in the graph itself, ignoring how
    much flows. Constant for the whole run. Nothing is ever forbidden, no edge is
    ever deleted, no price is ever refused.

``realized_support``
    Nodes reachable from the injection point along edges that actually carried
    claims this round. This is the source framework's central functional,
    circulation reachability, made computable.

The edges in the second set are a subset of the first not because anything
blocked them but because nothing traversed them. That gap is exactly the
framework's distinction between a hole and a high price: a hole is not a state
the price system can express, and an edge with no flow is invisible to any
statistic built from flows.

Why the headline measure has no threshold
-----------------------------------------
Proportional claim dynamics on a fixed graph have a positive stationary
distribution. Nothing ever reaches exactly zero, so any measure of the form
"count the nodes above a cutoff" is reporting the cutoff as much as the economy.
Adding a minimum operating scale so that nodes exit would fix that, but it would
also import the mechanism stage A1 exists to study, and it would invite the fair
objection that a threshold was inserted in order to make nodes disappear.

So the headline measure is threshold-free: the **effective support**, the
reciprocal Herfindahl index of the inflow distribution,

.. math::

    N_{\\mathrm{eff}} = 1 / \\sum_i p_i^2, \\qquad p_i = \\text{inflow}_i / \\sum_j
    \\text{inflow}_j

which is the effective number of firms from industrial organisation, applied to
circulation rather than to market share. It equals the node count under a
perfectly even spread, falls as flow concentrates, needs no cutoff, and moves
continuously.

The cutoff-based reachability measure is retained as a secondary series and its
cutoff is swept, so a reader can check that the qualitative result does not live
in the choice of epsilon.

The differential claim
----------------------
There exist parameter regimes in which total transaction volume **rises** while
effective support **contracts**. If so, no aggregate flow statistic can detect
the contraction, because every such statistic is a sum over the very edges that
are still busy.

The source framework is explicit that "total circulation fell" is the wrong
description, since the missing flow can be recirculating faster elsewhere and the
total can even rise. This module is that objection taken seriously and turned
into a measurement.

The intermediate layer, and what it is for
------------------------------------------
Set ``intermediate_size > 0`` and a third block appears between the two. It
collects household spending as revenue, pays rent and financing costs upward, and
**operates the payroll channel downward**. So it is simultaneously the entity that
funds wages and an entity being drained, which is a position no node can occupy in
a two-layer graph: there, the payer is rich and the recipient is the victim, and
nobody is both.

Three statements were written down before the code was run, so that whichever way
it came out could be reported.

**H1.** The wage channel narrows on its own. Not because the elasticity changed
and not because anyone decided to cut hiring, but because the entity operating the
channel runs short of claims to pay with.

**H2, the stronger one.** With an intermediary funding payroll out of its own
revenue, and that revenue coming from the very layer payroll pays, the autonomous
component of the downward flow is gone by construction. Stage A0b found that a
positive steady state survives only in proportion to that autonomous component and
vanishes at unit elasticity. So the prediction is that a three-layer economy sits
on the A0b collapse boundary **with its elasticity parameter set to zero**, having
been placed there by structure rather than by choice.

The falsifiable form: a three-layer run at ``elasticity = 0`` should resemble a
two-layer run at ``elasticity ≈ 1``, not a two-layer run at zero.

**H0, the null.** The intermediary changes nothing material. Volume and support
diverge as before, the wage channel behaves as before, and the third block is
decoration. Stage A2 has already returned two results of this shape -- degree
heterogeneity and the initial holdings distribution both turned out not to be
load-bearing -- and this one is reported the same way if it holds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as _dc_replace

import dataclasses

import numpy as np

from .config import LAYER_1, LAYER_2, MonetaryAuthority, SpendRule, WageChannel

#: A realized edge is one carrying flow above this fraction of the mean edge
#: flow in round zero. Relative rather than absolute so the threshold does not
#: silently depend on the scale of the initial claim stock. Swept for robustness
#: in the experiment; the qualitative result must not depend on its value.
DEFAULT_EPSILON = 1e-4

#: How the opening holdings are set in the arm where ``uniform_access`` is on.
#:
#: ``flat`` is an equal split and is what every result before 2026-08-13 was
#: produced under, so it remains the default and reproduces those bitwise.
#:
#: ``same_marginal`` gives that arm the **same multiset of opening holdings**
#: the stratified arm would produce, assigned at random rather than by layer and
#: in-degree. `docs/a4_causal_primitive.md` section 9.3 is the defect this
#: exists for and section 9.3a is why it is a switch rather than a repair.
#:
#: The distinction matters because the two things ``uniform_access`` collapses
#: are not equally licensed. A complete graph genuinely has no layers to define
#: an adjacency, a payroll incidence or a spending propensity by, so collapsing
#: those follows from the switch. **Holdings do not follow.** They can be drawn
#: from the same marginal without reference to any layer, and flattening them
#: makes the null arm start perfectly equal, which pins the denominator of every
#: transmitting mechanism near zero by construction rather than by anything
#: about the mechanism. Inheritance and assortative mating transmit and sort
#: dispersion without creating any, so on a perfectly equal opening they have
#: nothing to act on whatever the routing does.
#:
#: Under ``uniform_access = False`` this field reaches no code at all, which is
#: asserted rather than argued in ``tests/test_a4_uniform_opening.py``.
OPENING_HOLDINGS: tuple[str, ...] = ("flat", "same_marginal")

#: Offset for the permutation that assigns the stratified marginal at random.
#: A fresh constant, so the assignment cannot correlate with the payroll
#: receiver order, which draws on ``seed + 4241``.
_OPENING_PERMUTATION_OFFSET = 9301

#: Offset for the stream that draws A7's added edges. A fresh constant, so the
#: shortcuts cannot correlate with the stratified graph's own draw (``seed``),
#: the payroll receiver order (``seed + 4241``) or the opening permutation
#: (``seed + 9301``). The value is the one
#: ``experiments/a7a_continuous_c.py`` measured the continuum with, and
#: ``tests/test_a7_shortcut_rate.py`` asserts the two agree elementwise.
_SHORTCUT_OFFSET = 20_749

#: How A7's added edges pick their targets.
#:
#: ``uniform`` is the availability check's interpolation: every remaining
#: ordered pair independently at the rate. It raises mean degree and lowers
#: centrality dispersion together, and `docs/a7_continuous_c.md` section 4.3
#: records that this is exactly the confound the placebo exists to break.
#:
#: ``preferential`` adds **the same number of edges the uniform arm added at
#: that rate and seed**, chosen with probability proportional to the target's
#: existing in-degree. Density therefore tracks the uniform arm edge for edge
#: while the dispersion does not. Section 4.3 registers that the realised
#: dispersion is reported for both arms on every row, and that an arm whose
#: dispersion leaves the registered band is void rather than negative.
SHORTCUT_MODES: tuple[str, ...] = ("uniform", "preferential")

#: Where A7's shortcuts are allowed to land. ``"all"`` is the registered
#: behaviour and every A7 reading was taken under it.
#:
#: **Why the others exist.** The shortcut draw is uniform over ordered pairs,
#: and on a 20/180 graph that is not uniform over kinds of edge. Pure
#: combinatorics, no run needed: 80.95 percent of ordered pairs are
#: production to production, 9.05 percent are financial to production, and
#: **0.95 percent are financial to financial**. So a rate of 0.01 adds about
#: 322 edges inside the production layer and about **36 pointing downward**,
#: while ``NetworkSpec.downward_edges`` is zero by default and its own
#: docstring says zero is the framework's specification. A0-6 measured what
#: one downward edge does: production-layer inflow 17.7007 to 48.3919, a
#: factor of 2.73. **Every arm with a positive rate therefore moves two
#: things at once, and A7 read the result as density.**
#:
#: These scopes hold the count and move only where the edges land, which is
#: the same discipline ``shortcut_mode`` already applies to targets.
#:
#: ``"all"``          anywhere, the registered behaviour
#: ``"production"``   both endpoints outside the financial layer
#: ``"financial"``    both endpoints inside it
#: ``"downward"``     financial to production
#: ``"upward"``       production to financial
#:
#: **A scope can be too small to hold the matched count and the caller has to
#: check.** The financial layer offers 380 ordered pairs against a matched
#: count of about 398 at a rate of 0.01, so that arm saturates. Nothing here
#: raises: the graph is returned with what fits, and an arm that wanted more
#: is visible by counting the edges it actually gained.
SHORTCUT_SCOPES: tuple[str, ...] = (
    "all", "production", "financial", "downward", "upward",
)

#: A third fresh stream, so a scoped placement cannot correlate with either
#: the uniform draw or the preferential targets.
_SCOPE_OFFSET = 60_013

#: A second fresh stream, so the placebo's choice of targets cannot correlate
#: with which pairs the uniform arm happened to draw.
_PREFERENTIAL_OFFSET = 31_337

#: Offset for the stream that drives endogenous rewiring. A fresh constant, so
#: the rewire draws cannot correlate with the stratified graph's own draw
#: (``seed``), the payroll receiver order (``seed + 4241``), the opening
#: permutation (``seed + 9301``), A7's shortcuts (``seed + 20749``) or the
#: placebo's targets (``seed + 31337``).
_REWIRE_OFFSET = 51_413

#: A stream of its own for edge cutting, for the reason the rewire stream has
#: one: a switch that consumes another switch's draws changes results it has
#: nothing to do with, and the bitwise reproduction would then be a claim about
#: draw order rather than about the mechanism.
_EDGE_CUT_OFFSET = 90_311

#: Where newly issued claims are credited. Both arms are registered as the two
#: readings of the source's own claim that money is non-neutral because the path
#: and the injection point decide everything. Only the first was ever implemented.
#:
#: ``"top_node"``
#:     The financial-layer node of highest in-degree, which is what
#:     ``self.injection_node`` has always been and what every number in this
#:     repository was produced under. This is the default and it reproduces
#:     bitwise.
#:
#: ``"uniform"``
#:     An equal per-head credit to every node. Helicopter money, and the arm
#:     §16.2 named and nobody wrote.
#:
#: **Why this is a switch and not a robustness afterthought.**
#: ``experiments/a4a_domain_probe.py --probe injection`` measures what the
#: existing arm delivers downstairs, and the answer is **bitwise zero**. Over
#: three hundred rounds the endogenous rule issues about ``3213`` against an
#: opening stock of ``100``, a thirty-three-fold expansion, and the production
#: layer's entire holdings history is `array_equal` to the same run with
#: issuance off, at every seed, with derived demand on or off. The financial
#: block differs, so the comparison is live rather than unwired.
#:
#: The reason is structural rather than incidental. The credit lands on one
#: node inside layer 1, and the only downward edge is ``WageChannel.bill``, an
#: **absolute** per-round flow whose elasticity feeds back on the production
#: layer's *own* spending rather than on the financial layer's stock. No edge in
#: the model connects how much money sits upstairs to how much arrives
#: downstairs. So the production layer's share falls from ``10.4%`` to ``0.3%``
#: while its absolute holdings do not move at all.
#:
#: That kills §16.2's registered deliverable as it was written. "At what
#: injection amount does ``A(X)`` cross one" presupposes that the amount reaches
#: someone; on this arm no amount does, and the presupposition fails bitwise
#: rather than by being small. The contrast §16.2 wanted survives in a sharper
#: form: the two arms are zero and non-zero rather than two points on a dosage
#: curve.
INJECTION_TARGETS: tuple[str, ...] = ("top_node", "uniform")


@dataclass(frozen=True)
class NetworkSpec:
    """Structure of the two-layer graph.

    A financial core that is small, dense and internally recirculating, and a
    production periphery that is large, sparse, and connected upward far more
    than downward. Attachment is preferential within each layer, so degree is
    heavy-tailed and the core has genuine hubs rather than uniform connectivity.
    That matters: the framework's disagreement with the production-network
    literature is over what centrality *means*, not over whether it exists, so a
    graph without hubs would not be engaging the same object.
    """

    layer1_size: int = 20
    layer2_size: int = 180

    #: Out-degree within the financial layer. Fixed: the core is dense and its
    #: members are of comparable size.
    layer1_out_degree: int = 6

    #: *Mean* out-degree within the production layer, drawn per node from a
    #: geometric distribution rather than assigned uniformly.
    #:
    #: This is the stage's one substantive structural assumption and it is worth
    #: stating plainly. A node's internal trading partners scale with its size,
    #: while its upward obligations -- rent, financing costs, tax -- behave more
    #: like a fixed overhead per node. The consequence is that the *ratio* of
    #: upward leakage to internal circulation is heavy at the periphery and light
    #: at the centre, which is the standard observation that fixed costs fall
    #: hardest on the smallest firms.
    #:
    #: With a uniform out-degree instead, every production node has an identical
    #: leakage ratio, the whole layer drains in proportion, and the support set
    #: cannot contract because nothing dies before anything else. That version is
    #: available via ``uniform_degree`` and is run as the control.
    layer2_out_degree: int = 3

    #: Edges from the production layer up into the financial layer, per node.
    #: Fixed, for the reason above.
    upward_out_degree: int = 2

    #: Assign every production node the mean out-degree instead of drawing it.
    #: The homogeneous control.
    uniform_degree: bool = False

    # -- the intermediate layer ------------------------------------------
    #: Nodes in the intermediate block. Zero disables it and recovers the
    #: two-layer graph bitwise, which is the backward-compatibility control.
    intermediate_size: int = 0
    #: Out-degree within the intermediate block. Business to business.
    intermediate_out_degree: int = 4
    #: Edges from the intermediate block up into the financial layer. Rent,
    #: interest, financing costs. Fixed per node, like the household case and
    #: for the same reason.
    intermediate_upward_degree: int = 2

    #: Edges from the financial layer down into the intermediate block: business
    #: sold to the layer above rather than to households. This is the
    #: intermediary's *autonomous* revenue, the part that does not depend on the
    #: households its own payroll pays. Stage A0b predicts survival should be
    #: linear in it, so it is swept rather than set.
    financial_to_intermediate_edges: int = 0

    #: Total edges from the financial layer down into the production layer.
    #: The thin controlled channel. Zero is the framework's own specification
    #: and is the default; the experiment opens it and reports what happens.
    downward_edges: int = 0

    preferential: bool = True
    seed: int = 0

    #: Stage A4's ``C = 0`` arm: a complete graph on which every node reaches
    #: every other on identical terms.
    #:
    #: Switching this on removes *differentiation of access*, not access. The
    #: wage edge survives, aggregate spending propensity survives, and the claim
    #: stock survives; what goes is the fact that any of the three is
    #: distributed unequally across nodes. Concretely it sets four things at
    #: once, and they are one object rather than four:
    #:
    #: 1. the adjacency becomes complete,
    #: 2. every node both funds and receives payroll,
    #: 3. every node draws the same spending propensity, the node-count-weighted
    #:    mean of the two layers' values, so aggregate propensity is unchanged,
    #: 4. initial holdings are uniform, since the in-degree weighting that sets
    #:    them has nothing left to weight by.
    #:
    #: Points 3 and 4 are consequences rather than extra assumptions: both are
    #: defined in the A2 model *by layer*, and with a complete graph there are
    #: no layers for them to be defined by. Recorded in
    #: ``docs/a4_causal_primitive.md`` section 9.
    #:
    #: ``False`` is the default and no code path above changes under it, which
    #: is what makes the bitwise reproduction of A2 checkable.
    uniform_access: bool = False

    #: See ``OPENING_HOLDINGS``. Only read when ``uniform_access`` is on.
    uniform_opening: str = "flat"

    #: A7's continuum. The stratified adjacency with every remaining ordered
    #: pair added independently at this rate, so ``0.0`` returns the stratified
    #: graph bit for bit and ``1.0`` returns the complete graph, both exactly
    #: rather than in a limit. ``docs/a7_continuous_c.md`` section 2.
    #:
    #: **The documentation calls this ``s`` and it runs against ``C``.**
    #: ``s = 0`` is A4's ``C = 1`` arm. ``s = 1`` is a complete graph and **is
    #: not** A4's ``C = 0`` arm: only the adjacency moves with ``s``, while the
    #: payroll incidence, the discretionary routing, the propensities and the
    #: opening holdings keep their stratified rules, so five of the six things
    #: ``uniform_access`` collapses are still stratified at ``s = 1``. Section
    #: 2.4 of that file forbids comparing any ``s = 1`` number to a published
    #: ``C = 0`` one, and section 2.1 is why the letter had to change: the two
    #: coordinates run opposite ways and "connectivity rises" means two
    #: different things under them.
    #:
    #: Two of the four rules held fixed still have outputs that move with
    #: ``s``, because the payroll payers are selected on in-degree and the
    #: opening holdings are weighted by it. Section 2.3 rules that the rules
    #: run rather than that the index sets are frozen, and registers the churn
    #: diagnostic that goes with it.
    #:
    #: ``0.0`` is the default and no code path changes under it, which is what
    #: makes the bitwise reproduction of A2 and A3 checkable.
    shortcut_rate: float = 0.0

    #: See ``SHORTCUT_MODES``. Only read when ``shortcut_rate`` is strictly
    #: between zero and one: at either endpoint both modes return the same
    #: object, the stratified graph and the complete graph respectively.
    shortcut_mode: str = "uniform"

    #: See ``SHORTCUT_SCOPES``. Only read when ``shortcut_rate`` is strictly
    #: between zero and one, for the same reason ``shortcut_mode`` is.
    shortcut_scope: str = "all"

    @property
    def size(self) -> int:
        return self.layer1_size + self.intermediate_size + self.layer2_size

    @property
    def has_intermediate(self) -> bool:
        return self.intermediate_size > 0

    @property
    def financial_nodes(self) -> np.ndarray:
        return np.arange(self.layer1_size)

    @property
    def intermediate_nodes(self) -> np.ndarray:
        return np.arange(self.layer1_size, self.layer1_size + self.intermediate_size)

    @property
    def household_nodes(self) -> np.ndarray:
        return np.arange(self.layer1_size + self.intermediate_size, self.size)

    @property
    def layer1(self) -> slice:
        return slice(0, self.layer1_size)

    @property
    def layer2(self) -> slice:
        """The production side: intermediate plus households.

        Kept as one slice so every Layer 2 metric defined before the
        intermediate existed keeps meaning the same thing. The intermediate is a
        block *within* the production side, not a fourth category.
        """
        return slice(self.layer1_size, self.size)

    def __post_init__(self) -> None:
        if self.uniform_opening not in OPENING_HOLDINGS:
            raise ValueError(
                f"uniform_opening must be one of {OPENING_HOLDINGS}, "
                f"got {self.uniform_opening!r}"
            )
        if not 0.0 <= self.shortcut_rate <= 1.0:
            raise ValueError("shortcut_rate must lie in [0, 1]")
        if self.shortcut_scope not in SHORTCUT_SCOPES:
            raise ValueError(
                f"shortcut_scope must be one of {SHORTCUT_SCOPES}, "
                f"got {self.shortcut_scope!r}"
            )
        if self.shortcut_mode not in SHORTCUT_MODES:
            raise ValueError(
                f"shortcut_mode must be one of {SHORTCUT_MODES}, "
                f"got {self.shortcut_mode!r}"
            )
        if self.uniform_access and self.shortcut_rate > 0.0:
            raise ValueError(
                "uniform_access and shortcut_rate are different objects and A7 "
                "never switches uniform_access on; see docs/a7_continuous_c.md "
                "section 2.4"
            )
        if self.layer1_size < 2 or self.layer2_size < 2:
            raise ValueError("each layer needs at least two nodes")
        if self.downward_edges < 0:
            raise ValueError("downward_edges must be non-negative")
        if self.intermediate_size < 0:
            raise ValueError("intermediate_size must be non-negative")
        if self.financial_to_intermediate_edges < 0:
            raise ValueError("financial_to_intermediate_edges must be non-negative")
        if 0 < self.intermediate_size < 2:
            raise ValueError("an intermediate layer needs at least two nodes")
        for name in (
            "layer1_out_degree",
            "layer2_out_degree",
            "upward_out_degree",
            "intermediate_out_degree",
            "intermediate_upward_degree",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")

    def replace(self, **changes: object) -> NetworkSpec:
        fields = {
            "layer1_size": self.layer1_size,
            "layer2_size": self.layer2_size,
            "layer1_out_degree": self.layer1_out_degree,
            "layer2_out_degree": self.layer2_out_degree,
            "upward_out_degree": self.upward_out_degree,
            "uniform_degree": self.uniform_degree,
            "intermediate_size": self.intermediate_size,
            "intermediate_out_degree": self.intermediate_out_degree,
            "intermediate_upward_degree": self.intermediate_upward_degree,
            "financial_to_intermediate_edges": self.financial_to_intermediate_edges,
            "downward_edges": self.downward_edges,
            "preferential": self.preferential,
            "seed": self.seed,
            "uniform_access": self.uniform_access,
            "shortcut_rate": self.shortcut_rate,
            "shortcut_mode": self.shortcut_mode,
            "shortcut_scope": self.shortcut_scope,
            "uniform_opening": self.uniform_opening,
        }
        fields.update(changes)
        return NetworkSpec(**fields)  # type: ignore[arg-type]

    def with_intermediate(self, size: int) -> NetworkSpec:
        return self.replace(intermediate_size=size)

    def with_downward_edges(self, count: int) -> NetworkSpec:
        return self.replace(downward_edges=count)


def _attach_one(
    rng: np.random.Generator,
    src: int,
    targets: np.ndarray,
    out_degree: int,
    weights: np.ndarray | None,
    adjacency: np.ndarray,
) -> None:
    """Wire ``src`` to ``out_degree`` members of ``targets``.

    ``weights`` gives preferential attachment probabilities over ``targets``;
    ``None`` means uniform. Self-loops are skipped and a target is never used
    twice for the same source.
    """
    pool = targets[targets != src]
    if pool.size == 0:
        return
    k = min(out_degree, pool.size)
    if weights is None:
        chosen = rng.choice(pool, size=k, replace=False)
    else:
        p = weights[pool].astype(float)
        total = p.sum()
        p = p / total if total > 0 else None
        chosen = rng.choice(pool, size=k, replace=False, p=p)
    adjacency[src, chosen] = 1.0


def production_out_degrees(spec: NetworkSpec) -> np.ndarray:
    """Per-node internal out-degree for the production layer.

    Geometric with the configured mean, so the resulting upward-leakage ratio
    ``up / (up + k)`` is heavy at the periphery and light at the centre. Under
    ``uniform_degree`` every node gets the mean instead, which is the control.
    """
    rng = np.random.default_rng(spec.seed + 9973)
    if spec.uniform_degree:
        return np.full(spec.layer2_size, spec.layer2_out_degree, dtype=int)
    p = 1.0 / max(spec.layer2_out_degree, 1)
    return rng.geometric(p, size=spec.layer2_size)


def build_graph(spec: NetworkSpec, wage_edges: np.ndarray | None = None) -> np.ndarray:
    """Return the binary adjacency matrix. ``a[i, j] == 1`` means i can pay j.

    ``wage_edges`` is an optional (n, n) mask folded in at the end. The payroll
    channel has to be part of the potential graph, otherwise realized flow can
    traverse edges the potential graph does not contain and the two supports stop
    being comparable.
    """
    n = spec.size

    if spec.uniform_access:
        # Complete graph, no self-loops. Nothing is drawn, so no seed enters:
        # under uniform access the graph is not a sample from anything and two
        # seeds must give the same structure. Folding ``wage_edges`` is a no-op
        # here and is skipped rather than special-cased.
        return 1.0 - np.eye(n)

    rng = np.random.default_rng(spec.seed)
    a = np.zeros((n, n))

    fin = spec.financial_nodes
    mid = spec.intermediate_nodes
    hh = spec.household_nodes
    k_out = production_out_degrees(spec)

    def weights() -> np.ndarray:
        return 1.0 + a.sum(axis=0)

    # Financial core: dense, internally recirculating.
    w = np.ones(n)
    for src in rng.permutation(fin):
        _attach_one(
            rng,
            int(src),
            fin,
            spec.layer1_out_degree,
            w if spec.preferential else None,
            a,
        )
        if spec.preferential:
            w = weights()

    # Intermediate block, when present: business to business.
    for src in rng.permutation(mid):
        _attach_one(
            rng,
            int(src),
            mid,
            spec.intermediate_out_degree,
            w if spec.preferential else None,
            a,
        )
        if spec.preferential:
            w = weights()

    # Household discretionary spending. Without an intermediate it circulates
    # among households, which is the two-layer graph. With one, it is revenue
    # for the intermediate, which is the whole point of adding the block: the
    # entity that funds payroll is funded by the layer payroll pays.
    consumption_targets = mid if spec.has_intermediate else hh
    for src in rng.permutation(hh):
        _attach_one(
            rng,
            int(src),
            consumption_targets,
            int(k_out[src - spec.layer1_size - spec.intermediate_size]),
            w if spec.preferential else None,
            a,
        )
        if spec.preferential:
            w = weights()

    # Upward: rent, financing costs, tax. Fixed degree per node, which is what
    # makes the leakage *ratio* heavy at the periphery.
    up_w = np.zeros(n)
    up_w[fin] = 1.0 + a[np.ix_(fin, fin)].sum(axis=0)
    for src in hh:
        _attach_one(rng, int(src), fin, spec.upward_out_degree, up_w, a)
    for src in mid:
        _attach_one(rng, int(src), fin, spec.intermediate_upward_degree, up_w, a)

    # Autonomous revenue for the intermediary: sales to the layer above. Wired
    # from the most central financial nodes, which are the ones with claims.
    if spec.has_intermediate and spec.financial_to_intermediate_edges > 0:
        payers = fin[np.argsort(-a.sum(axis=0)[fin])]
        buyers = rng.permutation(mid)
        for i in range(spec.financial_to_intermediate_edges):
            a[payers[i % payers.size], buyers[i % buyers.size]] = 1.0

    # Downward discretionary channel from the financial core. Zero by default,
    # per the framework's specification; opened by the experiment.
    if spec.downward_edges > 0:
        payers = fin[np.argsort(-a.sum(axis=0)[fin])]
        receivers = rng.permutation(hh)
        for i in range(spec.downward_edges):
            a[payers[i % payers.size], receivers[i % receivers.size]] = 1.0

    # A7's continuum, applied after the stratified graph is finished and
    # before the payroll fold, which is the order
    # ``experiments/a7a_continuous_c.py`` measured it in. One draw is
    # thresholded, so the added edges are nested as the rate rises rather than
    # redrawn, and the sweep is a path rather than seventeen unrelated graphs.
    if spec.shortcut_rate > 0.0:
        if spec.shortcut_rate >= 1.0:
            # Exact rather than a limit, and the payroll fold is skipped for
            # the reason ``uniform_access`` skips it: on a complete graph it
            # adds nothing, and returning here keeps this endpoint bitwise
            # equal to the object the availability check compared against.
            return 1.0 - np.eye(n)
        shortcut_rng = np.random.default_rng(spec.seed + _SHORTCUT_OFFSET)
        drawn = shortcut_rng.random((n, n)) < spec.shortcut_rate
        np.fill_diagonal(drawn, False)
        if spec.shortcut_scope != "all":
            # The count comes from the same draw as every other arm, so the
            # scoped arms and the registered one are matched edge for edge at
            # every rate and seed. Only where the edges may land moves.
            #
            # **Placed rather than masked.** Masking the draw by the scope would
            # give the small scopes proportionally fewer edges, which is the
            # confound this exists to remove: it would make an arm both scoped
            # and sparser and no reading could tell the two apart.
            free = a == 0.0
            np.fill_diagonal(free, False)
            m = int((drawn & free).sum())
            is_fin = np.zeros(n, dtype=bool)
            is_fin[fin] = True
            row_fin = np.repeat(is_fin[:, None], n, axis=1)
            col_fin = np.repeat(is_fin[None, :], n, axis=0)
            allowed = {
                "production": ~row_fin & ~col_fin,
                "financial": row_fin & col_fin,
                "downward": row_fin & ~col_fin,
                "upward": ~row_fin & col_fin,
            }[spec.shortcut_scope]
            candidates = np.flatnonzero((free & allowed).ravel())
            # A scope smaller than the matched count saturates. Returning what
            # fits keeps the arm runnable and leaves the shortfall visible to
            # anyone who counts the edges the graph actually gained, which is
            # the reading rather than a flag: the financial layer offers 380
            # ordered pairs against about 398 wanted at a rate of 0.01.
            take = min(m, candidates.size)
            if take > 0:
                scope_rng = np.random.default_rng(spec.seed + _SCOPE_OFFSET)
                chosen = scope_rng.choice(candidates, size=take, replace=False)
                flat = a.ravel()
                flat[chosen] = 1.0
                a = flat.reshape(n, n)
        elif spec.shortcut_mode == "uniform":
            a = np.clip(a + drawn.astype(float), 0.0, 1.0)
        else:
            # The same count, different targets. ``drawn`` is read only for how
            # many edges it would have added that are not already there, so the
            # two arms are matched edge for edge at every rate and seed and the
            # comparison is not confounded by density.
            free = (a == 0.0)
            np.fill_diagonal(free, False)
            m = int((drawn & free).sum())
            if m > 0:
                idx = np.flatnonzero(free.ravel())
                # Weight by the target's existing in-degree. The plus one keeps
                # a node with no incoming edge reachable rather than excluded,
                # which would be a second intervention riding on this one.
                weight = 1.0 + a.sum(axis=0)
                w = np.repeat(weight[None, :], n, axis=0).ravel()[idx]
                # Gumbel top-k, which is weighted sampling without replacement
                # (Efraimidis and Spirakis) and is linear in the candidate set
                # rather than quadratic the way repeated choice would be. At the
                # rates where `m` approaches the whole candidate set this still
                # terminates, because it is a sort rather than a rejection loop.
                pick_rng = np.random.default_rng(
                    spec.seed + _PREFERENTIAL_OFFSET
                )
                u = pick_rng.random(idx.size)
                keys = np.log(w) - np.log(-np.log(u))
                chosen = idx[np.argpartition(-keys, m - 1)[:m]]
                flat = a.ravel()
                flat[chosen] = 1.0
                a = flat.reshape(n, n)

    if wage_edges is not None:
        a = np.maximum(a, (wage_edges > 0).astype(float))

    return a


@dataclass(frozen=True)
class SubsistenceSpec:
    """An absolute floor under a node's inflow, below which it leaves circulation.

    Derived rather than transcribed, so the derivation is here. Three things
    about the framework fix the shape and none of them is a choice made in this
    file.

    **It is a level on the real side, not a ratio on the claim side.** A claim
    is nominal and the framework's whole content is that the two come apart, so
    a floor that scaled with the claim stock would move with the thing it is
    supposed to be independent of. The floor is therefore in resource units,
    and claims and resources open one to one in this model, which is what makes
    the comparison meaningful at all.

    **It is a floor on inflow, not on holdings.** Volume One's own statement is
    that an agent with a high marginal propensity and no in-edge starves anyway:
    a claim about edges rather than about behaviour or about stock. A stock
    floor would let a node coast on what it accumulated, and the proposition
    being modelled is about the flow reaching it.

    **Leaving is absorbing.** The general preamble's mechanism is path
    dependence with absorbing walls, and the manuscript distinguishes a sector
    that was cut from one that was drained precisely because an edge into a
    drained region does not revive it. A node that leaves therefore does not
    come back when flow returns.

    **What leaving does not do is destroy claims.** Destruction is the write-off
    of section 14 and it has its own switch. A node that drops out freezes: it
    stops spending, stops receiving, and its holdings stay where they are. The
    claim total is untouched, so this mechanism and the conservation identity do
    not interact.

    Off by default, and off runs the original code path rather than a masked
    version of it, so the bit-for-bit reproduction is by construction.
    """

    #: Minimum inflow per round, in the units claims and resources share at the
    #: opening. Zero is off. The natural scale is the resource pool over the
    #: node count, and the value is swept rather than set: nothing in the
    #: framework fixes where subsistence sits, only that there is one.
    need: float = 0.0
    #: Consecutive rounds below the floor before the node leaves. One means it
    #: leaves the first time it is short.
    grace: int = 1

    #: Whether payroll is cut too. **False is the original behaviour** and is
    #: what every record taken before 2026-08-23 was produced under: a node that
    #: dropped out stopped trading but kept receiving wages.
    #:
    #: Two independent things, kept independent rather than bundled into one
    #: label, because they are two different questions. This one asks whether
    #: every channel closes or only the market.
    cut_payroll: bool = False

    #: Whether inflow returning above the floor brings the node back. **False is
    #: the original behaviour**, an absorbing wall.
    reversible: bool = False

    #: What being below the floor does. ``"exit"`` is the original behaviour
    #: and the default, so a run that does not name a mode is bit-for-bit
    #: what it was.
    #:
    #: ``"exit"`` --- the node stops trading. With ``cut_payroll`` false it
    #: goes on receiving wages, and it spends nothing, ever.
    #:
    #: **That combination describes nobody.** A household that has fallen
    #: below subsistence has no savings; one that has lost its job goes on
    #: consuming and consumes less. This one draws a wage every round,
    #: consumes zero, and never returns. Measured on A12's carrier: a
    #: hundred and sixty five nodes leave by round five, and the claims they
    #: hold then grow linearly by four per round for the rest of the run, to
    #: **85.6 percent of every claim outstanding at the close**. Receiving
    #: and not passing on is retention, and retention is this framework's
    #: mechanism for the **top** layer. The exit mode applies it to the
    #: bottom, which is why the distribution it produces is upside down.
    #: **Kept as a construction control, not as a regime.**
    #:
    #: ``"drawdown"`` --- the node stays in the graph and its spending is
    #: taken off subsistence rather than off propensity: it spends
    #: ``min(need, holdings)``, which does not consult inflow. So it goes on
    #: consuming, consumes less, and eats its savings. **There is no
    #: absorbing wall in this mode and none is needed**: the stock runs out
    #: on its own and a node with nothing spends nothing. ``cut_payroll``
    #: and ``reversible`` do not apply here and are ignored.
    mode: str = "exit"

    def __post_init__(self) -> None:
        if self.need < 0.0:
            raise ValueError("subsistence need must be non-negative")
        if self.grace < 1:
            raise ValueError("subsistence grace must be at least one round")
        if self.mode not in {"exit", "drawdown"}:
            raise ValueError(f"unknown subsistence mode: {self.mode}")

    @classmethod
    def payroll_severed(cls, need: float, grace: int = 1) -> SubsistenceSpec:
        """Every channel closes and nothing comes back.

        **A corner of the exit mode, not a regime.** Added 2026-08-24: the
        exit mode has another corner that leaves payroll on, and a node there
        draws a wage every round while spending nothing, which describes
        nobody. This corner closes that leak by closing the wage edge too, so
        its numbers are usable. It still holds the stock still and still
        never lets the node back. **The state with a household in it is the
        drawdown mode**, which keeps the node in the graph and lets it eat
        its savings. Read that one for anything about subsistence and read
        this one only as the exit mode with its leak closed.

        Renamed from ``starving`` on 2026-08-23. The old name asserted a social
        phenomenon the mechanism does not model: nothing here dies, a node stops
        transacting. Volume One section 18 motivates the setting, and section 18
        is where the motivation belongs; the constructor names the edge
        operation, which is what this actually does.

        **Which of the two booleans carries the difference is measured, not
        assumed.** On A12's carrier ``cut_payroll`` moves closing gini by 0.32
        and ``reversible`` moves it by 0.0005, so the separation between this
        and ``payroll_kept_reversible`` is carried by the payroll switch alone.
        The two remaining corners of the pair have not been run.
        """
        return cls(need=need, grace=grace, cut_payroll=True, reversible=False)

    @classmethod
    def payroll_kept_reversible(cls, need: float, grace: int = 1) -> SubsistenceSpec:
        """The market closes, the wage edge does not, and the exit is undone
        when inflow returns.

        **This is the corner with the leak in it**, and 2026-08-24 measured
        what the leak does: the node goes on drawing a wage and spends
        nothing, so a hundred and sixty five of them end A12's run holding
        85.6 percent of every claim outstanding and the stage reads monetary
        expansion as favouring the middle. **Receiving and not passing on is
        retention, which this framework assigns to the top layer.** Keep this
        as a construction control and do not read a regime off it. The
        household state is the drawdown mode.

        Renamed from ``bankrupting`` on 2026-08-23, for the reason in
        ``payroll_severed``. Section 18's present regime motivates it: output
        ample, access intermediated by debt, and the same relative position
        invisible because nobody is visibly destitute.

        **Read the caveat in ``payroll_severed`` before using this as a regime.**
        Its ``reversible`` boolean is the one measured to move nothing, so on the
        carrier tested this differs from a plain ``SubsistenceSpec(need=...)`` by
        0.0005 in closing gini. It is a named corner of a two-boolean square, not
        an established second regime.
        """
        return cls(need=need, grace=grace, cut_payroll=False, reversible=True)

    @property
    def active(self) -> bool:
        return self.need > 0.0


@dataclass(frozen=True)
class RewireSpec:
    """Whether position is bought and sold, or fixed at construction.

    Every stage before 2026-08-23 ran on a graph that never changes: the
    adjacency built at construction is bitwise identical after three hundred
    rounds. That is the framework's thesis stated as a construction, and the
    thesis is what the stages were meant to test, so this switch exists to stop
    assuming the conclusion in the one place it matters most.

    The measured motivation. At ``t = 0`` the two layers overlap in holdings,
    the richest production node at ``1.0477`` against the poorest financial node
    at ``0.7929``. By round three hundred the poorest financial node holds forty
    times the richest production node and the overlap is empty. **The total
    separation is produced during the run, on a graph that cannot respond to
    it.**

    Three parts, and the two rates are read off published work rather than
    chosen here.

    **Acquisition is graded and it fires twice.** Chetty et al. (Nature 2022)
    decompose cross-class connection into exposure, the share of high-status
    members in the group, and friending bias, the rate of actually connecting
    conditional on exposure. Exposure explains about 54 percent of the gap and
    friending bias about 46, and their own statement of the residual is that
    perfect integration by status would leave nearly half the gap standing. So
    qualifying is one draw and the cluster firing is a second, and the second
    does not fire for everyone. Their friending bias is also higher in larger
    groups, so ``cluster_rate`` is swept rather than pinned.

    **Loss is bimodal, not graded.** Eckbo, Thorburn and Wang (JFE 2015) follow
    the CEOs of 322 large public Chapter 11 filings from 1996 to 2007: one third
    keep full-time executive employment and their median compensation change is
    statistically indistinguishable from zero, and two thirds leave the
    executive labour market outright. Nobody keeps half a network. So a demoted
    node keeps all of its core edges or none of them, at a rate near one third.

    **Demotion redirects rather than deletes.** A node that leaves the core is
    not a sink; it trades with the production layer instead. Out-degree is
    conserved on that side so the change is in targets rather than in density,
    which matters because density moves the terminal distribution far more than
    anything behavioural does. ``conserve_degree`` extends the same discipline
    to acquisition, and False is available precisely so the density confound can
    be measured rather than assumed away.

    Off by default. Off leaves ``_rewire`` unreachable rather than running a
    no-op version of it, so the bit-for-bit reproduction is by construction.
    """

    #: Holdings at or above this level qualify a production-layer node for an
    #: edge into the financial core. Zero is off. Same units as claims, and the
    #: natural scale is ``initial_claims / n`` as it is for the subsistence
    #: floor. Nothing in the framework fixes the level, only that wealth buys
    #: access, so it is swept.
    acquire_level: float = 0.0

    #: How many non-core nodes join per rewire round, taken from the top of the
    #: non-core holdings order. Zero is off.
    #:
    #: This is the scale-free half of the pair, and it exists because the level
    #: form is not reachable on this model's own trajectory. Measured before
    #: writing it: the richest production node peaks at ``1.0477`` in **round
    #: zero** and falls monotonically to ``0.4518``, while the whole claim stock
    #: grows from ``100`` to ``3412``. So a level in claim units is crossed in
    #: 300 of 300 rounds at ``0.25``, in 7 at ``0.50``, in 1 at ``1.00`` and in
    #: none at ``2.00``: below the band everyone always qualifies and above it
    #: nobody ever does, and the same level loosens for the core and tightens
    #: for the periphery as the stock grows. **A rank always has somebody in
    #: it.**
    acquire_top_k: int = 0

    #: The second condition, applied together with the rank: a node must hold at
    #: least this share of the total claim stock. Zero is off, and with
    #: ``acquire_top_k`` set it is the difference between "the top k" and "the
    #: top k that are actually large".
    #:
    #: Two conditions rather than one because a core is a count **and** a share.
    #: The published cores are stated that way: Fedwire's tightly connected core
    #: is 25 nodes carrying 75% of value; the US top one percent held 38% of
    #: wealth in 2018. Neither number alone names the object.
    min_claim_share: float = 0.0

    #: Share form of ``demote_level``, on the same scale-free footing. A core
    #: node holding less than this share of the stock is demoted. Zero is off.
    demote_claim_share: float = 0.0

    #: Probability that qualifying pulls in the whole core rather than a single
    #: node. Zero means one edge per qualification and no cluster at all.
    cluster_rate: float = 0.0

    #: Financial-layer nodes whose holdings fall below this level are demoted.
    #: Zero is off, and it is separate from ``acquire_level`` because the two
    #: directions are not measured to be symmetric.
    demote_level: float = 0.0

    #: Probability a demoted node keeps its core edges regardless. The published
    #: figure is near one third; swept, because the figure is for large public
    #: company CEOs and this model's core is not that population.
    retain_rate: float = 0.0

    #: Whether demotion also removes the core's edges **into** this node. False
    #: is the original behaviour and it redirects outbound edges only.
    #:
    #: Added 2026-08-24 after reading what the outbound-only form implements.
    #: Grindaker, Kostol and Roszbach identify the effect of bankruptcy on a
    #: CEO's career off the random assignment of petitions to judges of varying
    #: strictness, in Norwegian small and medium firms, and find two halves that
    #: come apart: **no enduring effect on labour income after five years**, and
    #: a **permanent fall in capital income** of about five percent of gross
    #: income a year, worth 60 percent of a pre-bankruptcy year over the rest of
    #: the career. Displaced executives relocate quickly and take lower-ranked
    #: positions.
    #:
    #: Mapped onto this graph, the recovering half is trading with the
    #: production layer again, which outbound redirection already delivers and
    #: delivers for free: a demoted node keeps its payroll position, because the
    #: wage mask is never rewired, and keeps trading, because its out-edges are
    #: replaced rather than deleted. **The permanent half has no carrier at all
    #: without this switch**, because what falls permanently is what the core
    #: sends down, and demotion did not touch a single edge pointing in.
    #:
    #: So this is not a horizon. A horizon would restore something that was
    #: never taken. The asymmetry the published estimates describe is between
    #: two channels, not between two dates.
    demote_cuts_inbound: bool = False

    #: Whether acquisition redirects an existing edge (True, out-degree fixed)
    #: or adds a new one (False, out-degree rises and density moves with it).
    conserve_degree: bool = True

    #: Rounds between rewires. One is every round.
    interval: int = 1

    #: Whether promotion also hands over the core's spending propensity, and
    #: demotion hands it back. Off by default, and off is the arm every reading
    #: before 2026-08-24 was taken on: promotion buys edges and nothing else,
    #: so what those readings measure is what buying access does.
    #:
    #: **A no-op under ``uniform_access``**, where both layers already share one
    #: flat propensity by construction and there is nothing to transfer.
    transfer_propensity: bool = False

    #: Whether promotion also hands over the payroll role, and demotion hands it
    #: back. A node added here becomes a wage payer in the same round and gains
    #: the edges to the wage receivers that the construction gives every other
    #: payer, so the graph means the same thing for it as for them.
    #:
    #: **This one moves out-degree** on top of what ``conserve_degree`` holds,
    #: which is why it is a switch of its own rather than part of the one above:
    #: run both at once and a change cannot be attributed to either. The two are
    #: meant to be climbed one rung at a time.
    #:
    #: The payer set is never allowed to empty, because the payroll bill is
    #: divided by its size.
    transfer_payroll: bool = False

    def __post_init__(self) -> None:
        for name in ("acquire_level", "demote_level"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be non-negative")
        for name in ("cluster_rate", "retain_rate", "min_claim_share",
                     "demote_claim_share"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.acquire_top_k < 0:
            raise ValueError("acquire_top_k must be non-negative")
        if self.interval < 1:
            raise ValueError("rewire interval must be at least one round")

    @property
    def active(self) -> bool:
        return (
            self.acquire_level > 0.0
            or self.acquire_top_k > 0
            or self.demote_level > 0.0
            or self.demote_claim_share > 0.0
        )


#: Which way the obligation points between the hub set and everyone else.
#: Each has an object in the manuscript and the framework does not settle which
#: one produces what, which is why the stage runs all three rather than picking.
#:
#: ``creditor``  the hubs collect. Volume One's upward leakage is named as
#:               mortgage, rent, tax and interest, and the collector is
#:               upstream, so this is the framework's own default direction.
#: ``debtor``    the hubs owe, and everyone else holds the claim on them. That
#:               is the deposit shape, and section 13's fiat-Q construction is
#:               a hub issuing a claim other people hold as an asset.
#:
#:               **This is not A6's fiscal transfer with a different payer**,
#:               and the difference is four things rather than a label. A6's
#:               levy (``redistribution.py``, ``_apply_levy``) pays out of
#:               ``_l1_idx``, which is **layer membership fixed at
#:               construction**, in **equal shares to every node of
#:               ``_l2_idx``**, with **no edge test and no liveness test**: a
#:               production-layer node is paid whether or not the payer can
#:               reach it and whether or not it is still in the market.
#:
#:               Here the payer set is **the top of the in-degree
#:               distribution**, so it is chosen by the graph rather than by a
#:               layer label and it moves when the graph does; the payment is
#:               **routed along the payer's own out-edges** and is therefore
#:               unequal, with a node the payer cannot reach receiving nothing;
#:               and the recipient set is **masked by ``_alive``**, so a
#:               departed creditor drops out and the rest renormalise. A payer
#:               with no live reachable creditor pays **nothing at all** that
#:               round, which is a state A6's channel does not have.
#:
#:               The two therefore answer different questions. A6 asks what a
#:               policy that moves claims downward does. This asks what an
#:               obligation whose counterparties are picked by position and can
#:               disappear does, which is the only one of the two that can carry
#:               a contagion.
#: ``mutual``    the hubs owe each other. Volume One's "investing in each
#:               other's projects", and the one orientation where a hub's
#:               failure removes an asset from another hub's book.
HUB_DEBT_ORIENTATIONS: tuple[str, ...] = ("creditor", "debtor", "mutual")


#: How an edge comes to be cut. Each has a shape in the world and none of them
#: is what this model already does, because every rule here reads the node's own
#: state and the exit branch does not touch the adjacency at all: it flips a
#: membership flag and lets the routing renormalise.
#:
#: ``shock``     a share of the edges is cut once, at a named round, with the
#:               subsistence floor off. **No propagation rule at all.** This arm
#:               asks whether the graph on its own carries a cascade, and it can
#:               produce a discrete event without a floor because a node whose
#:               out-edges are all gone has ``_has_out`` false and spends
#:               nothing, which is an exit arrived at through the graph.
#: ``self_cut``  a node whose inflow falls below a threshold cuts its own
#:               out-edges. Withdrawing from the market rather than being unable
#:               to afford it. **This is the arm closest to the existing exit
#:               rule**, which is why the stage gates it: if the two read the
#:               same numbers then it is the exit rule under another name.
#: ``run``       nodes cut the edges pointing **at** a node whose inflow has
#:               fallen below the threshold. The trigger is read on one node and
#:               the action taken on another, and **no rule in this model does
#:               that today**. It is the shape a run has: a counterparty that
#:               looks weak stops being sent to, which makes it weaker.
EDGE_CUT_MODES: tuple[str, ...] = ("shock", "self_cut", "run")

#: How the shock arm picks its edges. See ``EdgeCutSpec.targeting``.
EDGE_CUT_TARGETING: tuple[str, ...] = ("random", "degree")


#: Where the money for a resupply comes from. See ``ResupplySpec.funding``.
#:
#: ``"creditors"``
#:               The node's existing in-neighbours pay, out of their own
#:               holdings. Nothing is created and nothing is levied, so the
#:               whole cost falls on whoever already lent. **This is a
#:               relationship-lending system with nobody standing behind the
#:               lender**, and it is the only value the switch had when it was
#:               added.
#: ``"issuance"``
#:               New claims are created and credited to the nodes that paid,
#:               one round later, through the same issuance step the authority
#:               already uses. The lenders are made whole and the claim stock
#:               rises. **The lag is not a convenience**: an authority
#:               recapitalises against losses it has seen, so the money arrives
#:               after the lending, never in the same instant.
#: ``"levy"``
#:               The cost is taken per head from every node still trading and
#:               handed to the nodes that paid. Conservative, and the burden is
#:               spread over everyone rather than falling on the existing
#:               creditors.
#:
#: **The three are the three answers to one question**, which is where a
#: rescue's money comes from: the lender's own book, outside the graph, or
#: everybody. They are not three degrees of one thing and no ordering is
#: implied between them.
RESUPPLY_FUNDING: tuple[str, ...] = ("creditors", "issuance", "levy")

#: Where new claims land under ``funding="issuance"``. See
#: ``ResupplySpec.recap_target``.
#:
#: ``"lenders"``
#:               On the nodes that funded the rescue. This is the only
#:               behaviour the switch had when it was added, and it is the one
#:               that says an injection reaches the economy through whoever
#:               already holds the claims on it.
#: ``"uniform"``
#:               Spread evenly over every node still trading. The same claims
#:               created, arriving in a different place.
#:
#: **This exists as a control and not as a second scenario.** A reading of the
#: form "the claims stopped where they landed" is a description of one arm
#: until an arm exists that lands them elsewhere. Whether the landing point
#: changes anything is the question; that it might not is a real branch.
RECAP_TARGETS: tuple[str, ...] = ("lenders", "uniform")


@dataclass(frozen=True)
class ResupplySpec:
    """A node held below the floor is kept going by whoever already lends to it.

    **This closes a gap A18 wrote down before it ran.** Forbearance is dangerous
    in the world because the forborne party keeps receiving new credit, and a
    node here eats its own stock until it has none with nobody feeding it. So
    the readings that stage took hold for forbearance without resupply, and this
    switch is the other kind.

    **The resuppliers are the node's existing in-neighbours**, and that choice
    is the whole design. Nothing is created: what the node below the floor
    receives, the nodes that already send to it lose. So the conservation
    assertion stays a criterion, and the interesting quantity is not what
    happens to the node being kept alive, it is what happens to the ones paying
    for it. A relationship-lending system is exactly a graph where the existing
    creditors are the ones who cannot walk away.

    **No edge is introduced.** The resupply travels the edges that are already
    there, in the direction they already point, which is why the potential
    support set is untouched and why a node with no in-edges is simply not
    resupplied.

    Off by default, and off reproduces a run without it to the last bit.
    """

    #: Share of the subsistence need topped up each round for a node that is
    #: below the floor. Zero is off. One means the node is held exactly at
    #: subsistence and never runs down; above one it is refloated.
    rate: float = 0.0

    #: Who ends up out of pocket. See ``RESUPPLY_FUNDING``. The default is the
    #: only behaviour this switch had when it was added, so a run that does not
    #: name it is the run it was before this field existed.
    funding: str = "creditors"

    #: What a recapitalised node withdraws from circulation, as a share of its
    #: spending propensity. Only reachable under ``funding="issuance"``, since
    #: it is the recapitalised set that retains and the other two routes create
    #: no such set.
    #:
    #: **This is the framework's own object and not a new one.** ``SpendRule``
    #: already says that the retention rate is ``1 - propensity`` and that it
    #: reads as the rate of exit from cross-layer circulation rather than as
    #: hoarding in the literal sense. So a recapitalised node that retains is a
    #: node whose propensity has been scaled, which is the same operation the
    #: top layer already carries. Nothing is earmarked: a particular tranche of
    #: claims being frozen is not an object this framework has.
    #:
    #: **The rescue itself is untouched by it.** The resupply is served before
    #: discretionary spending, so a retaining node goes on funding whatever it
    #: is asked for and simply stops doing anything else. That ordering is what
    #: makes this arm a decomposition rather than an on/off switch: it turns
    #: off the circulation channel and leaves the balance-sheet channel on.
    retain: float = 0.0

    #: Where the created claims land. See ``RECAP_TARGETS``. Reachable only
    #: under ``funding="issuance"``, and the default is the behaviour the
    #: switch had before this field existed.
    recap_target: str = "lenders"

    #: Share of the outstanding balance a rescued node repays each round.
    #: Zero, the default, is the behaviour this switch had until now: **the
    #: rescue is a gift and is never repaid.**
    #:
    #: **This is the half every real case has and this model did not.** A
    #: rescue that is never repaid cannot show a debt overhang, cannot show a
    #: rescue that makes its recipient worse off, and cannot distinguish a
    #: bridge from a trap. With it, the rescued node owes what it received to
    #: the nodes that funded it, and services that debt **before** it spends
    #: anything of its own.
    #:
    #: **The seniority is the mechanism and it is Volume One's.** Mortgage,
    #: rent, tax and interest are named there as the senior claim on income
    #: rather than what is left after shopping, which is the same ordering
    #: ``_hub_debt_flow`` already carries. So repayment is served first, and a
    #: node that repays itself back below the subsistence line and is topped up
    #: again is not an artefact of the ordering: **it is the ordering's
    #: content.**
    #:
    #: Unpaid amounts stay on the ledger rather than being forgiven, so the
    #: balance is readable and arrears are visible.
    repay: float = 0.0

    def __post_init__(self) -> None:
        if self.rate < 0.0:
            raise ValueError("rate must be non-negative")
        if self.funding not in RESUPPLY_FUNDING:
            raise ValueError(
                f"funding must be one of {RESUPPLY_FUNDING}, "
                f"got {self.funding!r}"
            )
        if not 0.0 <= self.retain <= 1.0:
            raise ValueError("retain must lie in [0, 1]")
        if self.recap_target not in RECAP_TARGETS:
            raise ValueError(
                f"recap_target must be one of {RECAP_TARGETS}, "
                f"got {self.recap_target!r}"
            )
        if not 0.0 <= self.repay <= 1.0:
            raise ValueError("repay must lie in [0, 1]")

    @property
    def active(self) -> bool:
        return self.rate > 0.0


#: Who moves claims out of reach. See ``ParkSpec.target``.
PARK_TARGETS: tuple[str, ...] = ("financial", "all", "recapitalised")


@dataclass(frozen=True)
class ParkSpec:
    """Claims moved out of circulation and out of reach, and not destroyed.

    **This is the piece two separate correspondences named as missing.** A node
    that retains holds its claims and does not spend them, but they are still
    on its account, so an obligation senior to spending can still take them and
    the retention is pierced. A node that has bought something outside the graph
    has done a different thing: the claims are gone from the trading system and
    no obligation reaches them, and yet they have not been destroyed.

    **The framework already has the quantity and not the destination.**
    ``SpendRule`` states that the retention rate reads as the rate of exit from
    cross-layer circulation rather than as hoarding. Exit needs somewhere to go,
    and until now the only somewhere was staying put.

    **Nothing is created or destroyed, so the conservation assertion stays a
    criterion** -- it counts the parked stock, because those claims still exist.
    Destroying them is what ``WriteOffSpec`` does and this is not that.

    **But the recorded ``M`` does not count them, and that is the point rather
    than an oversight.** ``NetworkHistory.total_claims`` is the row sum of
    ``holdings``, so ``M`` here has always meant claims in trading accounts.
    Parking therefore splits the stock in two and the recorded ``M/R`` follows
    the circulating half, with the other half carried beside it as ``parked``.
    **That split is exactly what could not be expressed before**: a stock of
    claims that exists, is owned, and is not in the money that circulates.

    **One way.** A parked claim does not come back. That is the limiting case
    and it is deliberately the first one: an instrument that matures is a second
    mechanism and would make this one impossible to read on its own.

    Off by default, and off reproduces a run without it to the last bit.
    """

    #: Share of what a node holds that is moved out of reach each round, after
    #: obligations are served and before discretionary spending. Zero is off.
    #:
    #: **The placement is the content.** Parking before obligations would let a
    #: node dodge them, which is a different claim about the world and one this
    #: framework does not make: Volume One's senior claims are senior.
    rate: float = 0.0

    #: Which nodes do it. See ``PARK_TARGETS``. The default is the financial
    #: layer, because that is the set every episode this was built for points
    #: at, and because a rule applied to every node is a rule about the economy
    #: rather than about a position in it.
    target: str = "financial"

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("rate must lie in [0, 1]")
        if self.target not in PARK_TARGETS:
            raise ValueError(
                f"target must be one of {PARK_TARGETS}, got {self.target!r}")

    @property
    def active(self) -> bool:
        return self.rate > 0.0


@dataclass(frozen=True)
class EdgeCutSpec:
    """Edges removed from the graph itself, rather than a node ceasing to trade.

    **The distinction this switch exists for.** When a node crosses the
    subsistence floor the adjacency is untouched: ``_alive`` flips, the routes
    that pointed at it are masked out for that round and the rest renormalised,
    and the potential graph is exactly what it was at construction. So the model
    has no way for a trading relationship to end. That is a real gap, because
    the relationship ending is the mechanism in a run: the depositor cuts the
    edge to the bank before the bank has failed anything.

    **Cutting creates and destroys no claims.** It changes who can pay whom, and
    the round's flow renormalises over whatever edges remain, so the
    conservation assertion stays a criterion rather than something to exempt.

    Off by default, and off reproduces a run without it to the last bit.
    """

    #: What triggers a cut and who does the cutting. See ``EDGE_CUT_MODES``.
    mode: str = "shock"

    #: Share of edges cut. Zero is off. **What the share is taken over depends
    #: on the mode**, and that is not a defect: under ``shock`` it is a share of
    #: every edge in the graph, cut once, and under the two triggered modes it
    #: is a share of the edges the event concerns. One number with a scope named
    #: by the mode beats two numbers where only one is ever live.
    share: float = 0.0

    #: ``shock`` only: the round the cut happens. Zero means the opening round.
    at_round: int = 0

    #: ``shock`` only: how the edges to cut are chosen. ``random`` is uniform
    #: over every edge present and is the default, so a run that does not ask
    #: for targeting takes the path this arm always took.
    #:
    #: ``degree`` cuts the edges whose **target** has the highest in-degree
    #: first. In-degree rather than out-degree, and the target rather than the
    #: source, because that is already this file's definition of a hub: it is
    #: the vector ``injection_node`` is chosen off and the one ``HubDebtSpec``
    #: selects with. **A second definition of "the well-connected node" would be
    #: the thing to avoid here**, since two of them in one file is how a word
    #: comes to mean two objects.
    #:
    #: The pair exists because the network literature's result is a pair: graphs
    #: of this kind are robust to random link removal and fragile to targeted
    #: removal at the hubs. An arm that only cuts at random measures one half of
    #: a known result and reports it as if it were the whole.
    targeting: str = "random"

    #: The two triggered modes only: the inflow below which a node counts as
    #: stressed, in the units inflow is measured in. Zero with a triggered mode
    #: means nothing ever fires, which is a coherent configuration and is left
    #: to the caller rather than raised on.
    trigger: float = 0.0

    def __post_init__(self) -> None:
        if self.mode not in EDGE_CUT_MODES:
            raise ValueError(
                f"mode must be one of {EDGE_CUT_MODES}, got {self.mode!r}"
            )
        if not 0.0 <= self.share <= 1.0:
            raise ValueError("share must lie in [0, 1]")
        if self.at_round < 0:
            raise ValueError("at_round must be non-negative")
        if self.targeting not in EDGE_CUT_TARGETING:
            raise ValueError(
                f"targeting must be one of {EDGE_CUT_TARGETING}, "
                f"got {self.targeting!r}"
            )
        if self.trigger < 0.0:
            raise ValueError("trigger must be non-negative")

    @property
    def active(self) -> bool:
        return self.share > 0.0


@dataclass(frozen=True)
class HubDebtSpec:
    """A bilateral obligation carried by the highest-degree nodes. Off by default.

    **This is the only liability in the flow layer**, and it is deliberately
    one: the model has no balance sheets anywhere else, claims are conserved
    through every exit, and it still produces an all-or-nothing cascade. The
    point of this switch is to find out what a liability adds to that, not to
    make the cascade possible.

    **The debt does not create claims.** It is a claim on future flow, and the
    instalment is routed through the payer's own adjacency row, which is the
    same shape ``asset.py`` gives ``stretch_debt``. Section 14's other reading,
    that credit creation mints money as debt, is a different switch and the
    destruction side of it already exists as ``WriteOffSpec``.

    **The instalment is a flow and not a holdings adjustment.** That choice is
    the one ``_fiscal_flow``'s docstring names: a transfer routed through the
    flow is an edge and counts as inflow wherever inflow is read, and one
    applied to holdings directly is money that arrives without one. The
    obligation has to be the first kind, because the question this switch
    exists for is whether it changes who falls below the subsistence floor, and
    the floor reads inflow.

    Off by default, and off reproduces a run without it to the last bit.
    """

    #: How many of the highest in-degree nodes are the hub set. Zero is off.
    #: Selected by ``adjacency.sum(axis=0)``, the same expression that picks
    #: ``injection_node``, so "the node with the most edges" cannot come to mean
    #: two different nodes in two places.
    hubs: int = 0

    #: Which way the obligation points. See ``HUB_DEBT_ORIENTATIONS``.
    orientation: str = "creditor"

    #: Share of the debtor's holdings owed to the creditor set each round.
    #: Zero is off.
    #:
    #: **A recurring rate rather than a principal with a term**, and the first
    #: version was the other one. A stock that amortises is a transient: at a
    #: principal of 0.9 and a ten-round term the whole obligation was 48 claims
    #: against 400,000 of total flow over the run, it was gone by round ten, and
    #: every reading came back equal to the arm with the switch off, the starved
    #: count included. **The mechanism has to be alive for the whole run for a
    #: departure to cost anybody anything**, and Volume One's upward leakage is
    #: named as mortgage, rent, tax and interest, which are continuing claims
    #: and not one-off balances. So the object is a stream, and what a creditor
    #: loses when a debtor goes is that stream.
    rate: float = 0.0

    def __post_init__(self) -> None:
        if self.hubs < 0:
            raise ValueError("hubs must be non-negative")
        if self.orientation not in HUB_DEBT_ORIENTATIONS:
            raise ValueError(
                f"orientation must be one of {HUB_DEBT_ORIENTATIONS}, "
                f"got {self.orientation!r}"
            )
        if not 0.0 <= self.rate < 1.0:
            raise ValueError("rate must lie in [0, 1)")

    @property
    def active(self) -> bool:
        return self.hubs > 0 and self.rate > 0.0


@dataclass(frozen=True)
class WriteOffSpec:
    """Volume One section 14: the accounting chain of a write-off.

    The chain the manuscript states is: credit creation mints money as debt,
    default sends the paper out at a discount, part is recovered, owners'
    equity carries the difference, and **money is destroyed at write-off**. So
    the claim stock falls, which is the one thing in this model that breaks
    conservation, and it breaks it in a stated direction rather than as slack.

    Two decisions come from the same section and neither is invented here.
    **The loss is borne by dilution and nobody can name what they paid**
    (section 14, closing paragraph), so the destruction is proportional across
    every holder rather than aimed at anyone. And **whether the head grows back
    is a political condition rather than a mechanism** (the hydra clause): the
    United States had TARP and Iceland did not, same mechanism, opposite
    outcome. That is ``refill``, and it is a switch precisely because the
    manuscript says it is not endogenous.

    Off by default, and off reproduces a run without it to the last bit.
    """

    #: Share of the outstanding claim stock destroyed in a round where the
    #: trigger is met. Zero is off.
    rate: float = 0.0
    #: The claims-per-unit-resource ratio above which claims start being judged
    #: to have no backing. Zero is off. Swept rather than set: the manuscript
    #: states that the referent of a quasi-money claim is empty in some states,
    #: not at which ratio that begins.
    trigger: float = 0.0
    #: Whether issuance refills what was destroyed, on the round after. The
    #: hydra clause: the equity that absorbs the loss is conserved, and what
    #: grows back is funded from the layer that is not.
    refill: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate < 1.0:
            raise ValueError("write-off rate must lie in [0, 1)")
        if self.trigger < 0.0:
            raise ValueError("write-off trigger must be non-negative")

    @property
    def active(self) -> bool:
        return self.rate > 0.0 and self.trigger > 0.0


@dataclass(frozen=True)
class NetworkConfig:
    """Parameters for one A2 run."""

    spec: NetworkSpec = field(default_factory=NetworkSpec)
    spend: SpendRule = field(default_factory=SpendRule)
    wages: WageChannel = field(default_factory=WageChannel)
    authority: MonetaryAuthority = field(
        default_factory=lambda: MonetaryAuthority(rule="endogenous")
    )

    #: Total claims at t=0, split so that the layer shares match the block model.
    initial_claims: float = 100.0
    layer1_initial_share: float = 0.679

    #: Total real resources. Closed economy, no real growth by default. Same
    #: name, same default and same meaning as ``EconomyConfig``, so ``M/R`` read
    #: off either model is on one scale. Constant by construction: this graph
    #: moves claims, it does not produce the pool those claims are claims on.
    total_resources: float = 100.0
    #: Share of resources withheld from market each round, the dormant resource
    #: pool. Zero here so the stage isolates the claim side, as in A0.
    resource_withholding: float = 0.0

    #: Volume One section 14's write-off chain. Off by default.
    writeoff: WriteOffSpec = field(default_factory=WriteOffSpec)

    #: The subsistence floor. Off by default.
    subsistence: SubsistenceSpec = field(default_factory=SubsistenceSpec)

    #: Endogenous rewiring. Off by default.
    rewire: RewireSpec = field(default_factory=RewireSpec)

    #: A bilateral obligation on the highest-degree nodes. Off by default.
    hub_debt: HubDebtSpec = field(default_factory=HubDebtSpec)

    #: Edges removed from the graph itself. Off by default.
    edge_cut: EdgeCutSpec = field(default_factory=EdgeCutSpec)

    #: Whoever already lends to a node below the floor keeps it going. Off by
    #: default.
    resupply: ResupplySpec = field(default_factory=ResupplySpec)

    #: Claims moved out of circulation without being destroyed. Off by default.
    park: ParkSpec = field(default_factory=ParkSpec)

    epsilon: float = DEFAULT_EPSILON
    rounds: int = 300
    seed: int = 0

    #: Where new claims land. See ``INJECTION_TARGETS``. It sits here rather
    #: than on ``MonetaryAuthority`` because ``economy.py``'s block model shares
    #: that dataclass and credits ``INJECTION_STRATUM`` instead of a node, so a
    #: field there would be read by one model and silently ignored by the other,
    #: which is the shape ``centrality_bins`` failed in.
    injection_target: str = "top_node"

    #: Keep the full flow matrix every ``snapshot_every`` rounds, for stage A2c
    #: to compute cycle structure on. Zero keeps nothing, which is the default:
    #: the matrices are large and no earlier stage needs them.
    snapshot_every: int = 0

    def __post_init__(self) -> None:
        if not 0.0 < self.layer1_initial_share < 1.0:
            raise ValueError("layer1_initial_share must lie in (0, 1)")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon must be positive")
        if not 0.0 <= self.resource_withholding < 1.0:
            raise ValueError("resource_withholding must lie in [0, 1)")
        if self.rounds < 1:
            raise ValueError("rounds must be >= 1")
        if self.snapshot_every < 0:
            raise ValueError("snapshot_every must be non-negative")
        if self.injection_target not in INJECTION_TARGETS:
            raise ValueError(
                f"injection_target must be one of {INJECTION_TARGETS}, "
                f"got {self.injection_target!r}"
            )


def effective_support(inflow: np.ndarray) -> float:
    """Reciprocal Herfindahl index of an inflow distribution.

    The effective number of nodes the circulation reaches. Equals the node count
    when flow is spread evenly and falls toward one as it concentrates. No
    cutoff, no exit rule, no free parameter.
    """
    total = float(inflow.sum())
    if total <= 0.0:
        return 0.0
    p = inflow / total
    return float(1.0 / np.square(p).sum())


@dataclass
class NetworkHistory:
    """Per-round record."""

    total_volume: np.ndarray  # (rounds,) sum of all realized flow
    effective_support: np.ndarray  # (rounds,) 1 / HHI of inflow. Headline.
    effective_support_l2: np.ndarray  # (rounds,) the same, production layer only
    realized_support: np.ndarray  # (rounds,) cutoff-based reachability
    active_nodes: np.ndarray  # (rounds,) nodes with inflow above the cutoff
    layer2_reached: np.ndarray  # (rounds,) of the reachable set, in Layer 2
    layer1_volume: np.ndarray  # (rounds,) flow circulating inside Layer 1
    layer2_inflow: np.ndarray  # (rounds,) claims landing in Layer 2
    wage_owed: np.ndarray  # (rounds,) the bill the rule calls for
    wage_paid: np.ndarray  # (rounds,) what the payers could actually fund
    intermediate_holdings: np.ndarray  # (rounds,) claims held by the middle block
    holdings: np.ndarray  # (rounds, n) claims held
    issuance: np.ndarray  # (rounds,) new claims
    active_resources: np.ndarray  # (rounds,) R_a
    total_resources: np.ndarray  # (rounds,) R
    written_off: np.ndarray  # (rounds,) claims destroyed this round
    starved: np.ndarray  # (rounds,) nodes that have left circulation, cumulative
    promoted: np.ndarray  # (rounds,) nodes that bought into the core this round
    demoted: np.ndarray  # (rounds,) nodes that lost the core this round
    frozen_holdings: np.ndarray  # (rounds,) claims held by nodes that have left
    parked: np.ndarray  # (rounds,) claims out of circulation and not destroyed
    potential_support: int  # constant: nodes reachable in the potential graph
    node_count: int  # constant: nodes in the graph
    adjacency: np.ndarray  # the potential graph, fixed for the whole run
    snapshots: dict[int, np.ndarray]  # round -> flow matrix, if requested
    epsilon_absolute: float  # the cutoff actually used, in claim units

    def tail_mean(self, metric: str, last: int = 50) -> float:
        series = np.asarray(getattr(self, metric), dtype=float)
        return float(series[-min(last, len(series)) :].mean())

    @property
    def support_fraction(self) -> np.ndarray:
        return self.realized_support / self.potential_support

    @property
    def wage_funding_ratio(self) -> np.ndarray:
        """Fraction of the wage bill the payers could actually fund.

        Below one means the channel narrowed because whoever operates it ran
        short of claims, with no change to the wage rule and no decision by
        anyone. This is the series hypothesis H1 is about.
        """
        return np.divide(
            self.wage_paid,
            self.wage_owed,
            out=np.ones_like(self.wage_paid),
            where=self.wage_owed > 0,
        )

    @property
    def total_claims(self) -> np.ndarray:
        """M: claims outstanding at the end of each round.

        Read off the row sums of ``holdings`` rather than tracked alongside
        them. This model carries no stock-flow assertion in its loop, unlike
        ``economy.py``, so the row sum is the only statement of M here.
        """
        return np.asarray(self.holdings, dtype=float).sum(axis=1)

    @property
    def active_ratio(self) -> np.ndarray:
        """M_a / R_a. What the authority targets and a price index reads.

        ``layer2_inflow`` carries the same definition as ``economy.py``'s
        ``active_claims``, claims landing in Layer 2, so this ratio is the one
        A0 reports, computed on the graph instead of on the block model.
        """
        return np.asarray(self.layer2_inflow, dtype=float) / np.asarray(
            self.active_resources, dtype=float
        )

    @property
    def total_ratio(self) -> np.ndarray:
        """M / R. What nobody targets."""
        return self.total_claims / np.asarray(self.total_resources, dtype=float)

    @property
    def divergence(self) -> tuple[float, float]:
        """Ratio by which volume grew and effective support shrank.

        The pair that carries the differential claim: if the first is above one
        and the second below one, no sum over flows can report what happened.
        """
        vol = float(self.total_volume[-1] / self.total_volume[0])
        sup = float(self.effective_support[-1] / self.effective_support[0])
        return vol, sup


def reachable_from(flow: np.ndarray, source: int, epsilon: float) -> np.ndarray:
    """Nodes reachable from ``source`` along edges carrying flow above epsilon.

    Breadth-first over the *realized* graph. The potential graph is not
    consulted, which is the whole point: an edge that exists and carries nothing
    does not transmit.
    """
    live = flow > epsilon
    n = live.shape[0]
    seen = np.zeros(n, dtype=bool)
    seen[source] = True
    frontier = np.zeros(n, dtype=bool)
    frontier[source] = True
    while frontier.any():
        nxt = live[frontier].any(axis=0) & ~seen
        seen |= nxt
        frontier = nxt
    return seen


class Network:
    """Claim circulation on a directed graph.

    The per-round sequence matches A0 exactly, so that block-aggregating this
    model returns the A0 dynamics rather than something merely similar.
    """

    def __init__(self, config: NetworkConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)

        spec = config.spec
        n = spec.size
        self._n = n
        self._l1 = spec.financial_nodes
        self._l2 = np.arange(spec.layer1_size, n)
        self._mid = spec.intermediate_nodes
        self._hh = spec.household_nodes

        # The payroll channel is chosen first so it can be folded into the
        # potential graph.
        #
        # Who operates it is the one structural difference the intermediate
        # makes. Without an intermediate, the payers are the most central
        # financial nodes, which are never short of claims. With one, the payers
        # are the intermediate itself, which is being drained upward at the same
        # time. Nothing else about the wage rule changes.
        scaffold_in = build_graph(spec).sum(axis=0)
        if spec.uniform_access:
            # Everyone funds payroll and everyone receives it. The bill is a
            # total that is split across payers, so its size is untouched; only
            # the concentration of who pays and who is paid is removed.
            self._wage_payers = np.arange(n)
            self._wage_receivers = np.arange(n)
        elif spec.has_intermediate:
            self._wage_payers = self._mid
            self._wage_receivers = np.random.default_rng(spec.seed + 4241).permutation(
                self._hh
            )[: max(1, spec.layer2_size // 2)]
        else:
            self._wage_payers = self._l1[np.argsort(-scaffold_in[self._l1])][
                : max(1, spec.layer1_size // 4)
            ]
            self._wage_receivers = np.random.default_rng(spec.seed + 4241).permutation(
                self._hh
            )[: max(1, spec.layer2_size // 2)]

        wage_mask = np.zeros((n, n))
        wage_mask[np.ix_(self._wage_payers, self._wage_receivers)] = 1.0
        self.adjacency = build_graph(config.spec, wage_edges=wage_mask)
        self.wage_mask = wage_mask

        # Discretionary routing follows the graph minus the payroll edges: wages
        # are settled separately, so counting them twice would let the top's
        # consumption ride down the employment channel.
        # Under uniform access the subtraction is skipped. Its purpose is to
        # stop the financial layer's consumption riding down the employment
        # channel, and with a complete graph there is no financial layer and no
        # downward channel: every edge is already both. Subtracting anyway would
        # not be conservative, it would be fatal -- everyone pays and receives
        # payroll in that arm, so the mask is the full matrix and the
        # discretionary graph would be emptied. The null arm would then consist
        # of a payroll transfer that is a wash for every node, holdings would
        # never move, and every competing mechanism would have an exactly
        # uniform distribution to work on and would report zero. The reference
        # arm of the entire factorial would be a dead economy reporting clean
        # numbers.
        if spec.uniform_access:
            discretionary = self.adjacency.copy()
        else:
            discretionary = np.clip(self.adjacency - wage_mask, 0.0, 1.0)
        row_sums = discretionary.sum(axis=1, keepdims=True)
        self._route = np.divide(
            discretionary,
            row_sums,
            out=np.zeros_like(discretionary),
            where=row_sums > 0,
        )
        self._has_out = row_sums.ravel() > 0

        # Rewiring's own stream, built once so the sweep is a path rather than a
        # fresh draw per round. Never touched when the switch is off.
        self._rewire_rng = np.random.default_rng(config.seed + _REWIRE_OFFSET)
        #: Which layer each node currently belongs to. Only rewiring moves an
        #: entry, and with rewiring off this is the construction's own split for
        #: the whole run.
        self._in_core = np.zeros(n, dtype=bool)
        self._in_core[self._l1] = True

        # Injection at the most central financial node, where new money enters in
        # the block model.
        in_degree = self.adjacency.sum(axis=0)
        self.injection_node = int(self._l1[np.argmax(in_degree[self._l1])])

        # The hub set, off the same in-degree vector. Sorted so the set is an
        # ordered object rather than whatever order the sort happened to give,
        # which is the shape the B7 partition failed in.
        hd = config.hub_debt
        if hd.active:
            order = np.argsort(in_degree, kind="stable")[::-1]
            self._hub_nodes = np.sort(order[: hd.hubs]).astype(int)
        else:
            self._hub_nodes = np.zeros(0, dtype=int)
        #: Edge cutting: its own stream, so that turning it on does not shift
        #: any other draw, and two counters. ``_shock_fired`` makes the one-shot
        #: arm one-shot even if the round is revisited.
        self._cut_rng = np.random.default_rng(config.seed + _EDGE_CUT_OFFSET)
        self._shock_fired = False
        self._edges_cut = 0
        #: Cumulative claims the existing creditors have sent to keep
        #: nodes below the floor going. A diagnostic: no criterion reads
        #: it, and a switch that turns out to have moved nothing should
        #: say so rather than being inferred from an unchanged reading.
        self._resupplied = 0.0
        #: What each node paid out as a resupplier this round, and what the
        #: authority still owes them under ``funding="issuance"``. Two arrays
        #: rather than one because the first is cleared every round and the
        #: second is carried one round forward on purpose.
        self._resupply_owed = np.zeros(n)
        self._pending_recap = np.zeros(n)
        self._recapitalised = 0.0
        self._levied = 0.0
        #: What the rescue was asked for, against what it could fund. Recorded
        #: because the model computes the shortfall either way and reporting
        #: only the paid half hides the quantity the whole arm turns on: at the
        #: deepest floor and the largest rate the lenders fund a quarter of
        #: what is asked.
        self._resupply_asked = 0.0
        #: Nodes that have received a recapitalisation, ever. Membership is
        #: monotone: an injection is not undone by a later round.
        self._recap_recipients = np.zeros(n, dtype=bool)
        #: Who owes what to whom from the rescue. ``[i, j]`` is what ``j`` owes
        #: ``i``. Bilateral rather than a per-node total because the money has
        #: to go back to the nodes it came from, and those are not
        #: interchangeable: the whole point of a relationship-lending graph is
        #: that the creditor is a particular node.
        self._resupply_ledger = np.zeros((n, n))
        #: Claims that have left circulation without being destroyed. Held as a
        #: per-node figure so that who parked can be read, and added back into
        #: the conservation check, because they still exist.
        self._parked = np.zeros(n)
        self._repaid = 0.0
        self._repay_blocked = 0

        #: Cumulative claims moved by the obligation, and the number of rounds
        #: in which no payment could be made because no live creditor was
        #: reachable. Diagnostics: neither feeds a criterion, and both are here
        #: because a switch that turns out to have moved nothing should say so
        #: rather than being inferred from a reading that did not change.
        self._hub_debt_paid = 0.0
        self._hub_debt_blocked = 0

        # Propensities: the block model's per-stratum values, assigned by layer.
        # The intermediate takes the production side's propensity, since it is a
        # block within that side rather than a separate behavioural type. Giving
        # it its own propensity would add a free parameter and make any result
        # attributable to that parameter instead of to its position.
        lo = np.asarray(config.spend.low, dtype=float)
        hi = np.asarray(config.spend.high, dtype=float)
        self._p_low = np.empty(n)
        self._p_high = np.empty(n)
        self._p_low[self._l1] = lo[list(LAYER_1)].mean()
        self._p_high[self._l1] = hi[list(LAYER_1)].mean()
        self._p_low[self._l2] = lo[list(LAYER_2)].mean()
        self._p_high[self._l2] = hi[list(LAYER_2)].mean()
        # Kept as scalars so ``RewireSpec.transfer_propensity`` has the two
        # layer values to move a node between. Read only; the arrays above are
        # the state, and under ``uniform_access`` they are overwritten below,
        # which is what makes that switch a no-op for this one.
        self._p_core = (float(self._p_low[self._l1][0]),
                        float(self._p_high[self._l1][0]))
        self._p_outside = (float(self._p_low[self._l2][0]),
                           float(self._p_high[self._l2][0]))
        if spec.uniform_access:
            # The two values above are defined *by layer*, and a complete graph
            # has no layers to define them by. Both are replaced by a single
            # figure, weighted by each layer's share of the initial claim stock
            # rather than by its share of the nodes.
            #
            # The weighting is not a detail. Claim-weighting holds the
            # economy's aggregate spending flow at t=0 equal to the stratified
            # arm's, which is the invariant the whole ``C`` switch is built on:
            # aggregates survive, their dispersion does not. Node-weighting
            # would instead hold the mean propensity *per node* fixed, and since
            # ninety percent of nodes sit in the production layer the result is
            # a null arm that turns its entire claim stock over roughly twice as
            # fast as the arm it is the reference for. Any mechanism acting on a
            # stock would then be washed out in the null arm by a difference in
            # turnover that the switch was never supposed to introduce, and the
            # comparison would be measuring the weighting.
            w1 = float(config.layer1_initial_share)
            w2 = 1.0 - w1
            flat_low = float(w1 * self._p_low[0] + w2 * self._p_low[-1])
            flat_high = float(w1 * self._p_high[0] + w2 * self._p_high[-1])
            self._p_low[:] = flat_low
            self._p_high[:] = flat_high

        # Initial holdings, spread within each layer in proportion to in-degree
        # so that the graph's own centrality sets the distribution. Verified in
        # stage A2 not to affect any reported result.
        self.holdings = np.zeros(n)
        if spec.uniform_access:
            # ``layer1_initial_share`` splits the stock between two layers that
            # no longer exist, and the in-degree weighting within each has a
            # constant to weight by. Both collapse to an equal split. The total
            # is unchanged, so the null arm starts with the same claim stock as
            # every other arm and differs only in its concentration.
            #
            # `uniform_opening` decides whether that last sentence is the
            # intended design or a defect. See `OPENING_HOLDINGS` and
            # `docs/a4_causal_primitive.md` section 9.3.
            if spec.uniform_opening == "flat":
                self.holdings[:] = config.initial_claims / n
            else:
                # The stratified arm's own opening vector, then permuted.
                #
                # **Built by constructing that arm rather than by recomputing
                # its formula here.** The first attempt weighted by
                # ``build_graph(spec).sum(axis=0)`` and was wrong, because the
                # stratified arm weights by ``self.adjacency``, which is
                # ``build_graph(config.spec, wage_edges=wage_mask)`` and folds
                # the payroll incidence in. Two lines that look like the same
                # in-degree are not, and a copy of the formula here would go
                # stale the first time the other one changes. The twin cannot
                # recurse: it has ``uniform_access`` off, so it takes the branch
                # below and never reaches this one.
                twin = Network(
                    _dc_replace(config, spec=spec.replace(uniform_access=False))
                )
                order = np.random.default_rng(
                    spec.seed + _OPENING_PERMUTATION_OFFSET
                ).permutation(n)
                self.holdings[:] = np.asarray(twin.holdings, dtype=float)[order]
        else:
            for nodes, share in (
                (self._l1, config.layer1_initial_share),
                (self._l2, 1.0 - config.layer1_initial_share),
            ):
                w = in_degree[nodes] + 1.0
                self.holdings[nodes] = config.initial_claims * share * w / w.sum()

        #: Relative shares in which payroll is distributed across
        #: ``_wage_receivers``. ``None`` means an equal split and is the only
        #: value any stage before A4 uses. It is a separate branch rather than a
        #: vector of ``1/k`` because ``total / k`` and ``total * (1.0 / k)`` are
        #: not the same float, and stage A4's bitwise reproduction of A2 would
        #: fail on the difference.
        self._wage_weights: np.ndarray | None = None

        #: Who is still in circulation. All of them until a floor is set and
        #: somebody falls under it; never set back to True, per the absorbing
        #: wall in the spec's docstring.
        self._alive = np.ones(n, dtype=bool)
        #: Who is below the floor, in ``drawdown`` mode. Distinct from
        #: ``_alive``, which is membership: these nodes are still in the
        #: graph and still trading, only on a different spending rule.
        self._below = np.zeros(n, dtype=bool)
        self._short_for = np.zeros(n, dtype=int)

        self._total_claims = float(config.initial_claims)
        self._pending_issuance = 0.0
        self._baseline_active: float | None = None
        self._baseline_l2_spending: float | None = None
        self._last_l2_spending = 0.0
        self._last_bill_owed = 0.0
        self._last_bill_paid = 0.0

        # Potential reachability: what the graph permits, before any dynamics.
        # Constant for the whole run and the correct comparison for the realized
        # set, since both are then reachability from the same source.
        self._potential_reached = reachable_from(
            self.adjacency, self.injection_node, 0.0
        )

    # -- flows -------------------------------------------------------------

    def _wage_flow(self) -> tuple[np.ndarray, float]:
        cfg = self.config
        baseline = self._baseline_l2_spending
        bill = (
            cfg.wages.bill
            if baseline is None
            else cfg.wages.bill_at(self._last_l2_spending, baseline)
        )
        matrix = np.zeros((self._n, self._n))
        if bill <= 0.0:
            return matrix, 0.0

        payers, receivers = self._wage_payers, self._wage_receivers
        if self.config.subsistence.cut_payroll and not self._alive.all():
            # Starving cuts every channel. Bankruptcy does not: payroll is how a
            # node that lost the market can still be reached, and the difference
            # between the two exits is exactly this line.
            payers = payers[self._alive[payers]]
            receivers = receivers[self._alive[receivers]]
            if payers.size == 0 or receivers.size == 0:
                self._last_bill_owed = bill
                self._last_bill_paid = 0.0
                return matrix, bill

        per_payer = bill / payers.size
        paid = np.minimum(per_payer, np.maximum(self.holdings[payers], 0.0))
        total = float(paid.sum())
        self._last_bill_owed = bill
        self._last_bill_paid = total
        if total <= 0.0:
            return matrix, 0.0

        if self._wage_weights is None:
            share = total / receivers.size
            for idx, payer in enumerate(payers):
                if paid[idx] <= 0:
                    continue
                portion = paid[idx] / receivers.size
                matrix[payer, receivers] += portion
            self.holdings[payers] -= paid
            self.holdings[receivers] += share
        else:
            w = self._wage_weights
            for idx, payer in enumerate(payers):
                if paid[idx] <= 0:
                    continue
                matrix[payer, receivers] += paid[idx] * w
            self.holdings[payers] -= paid
            self.holdings[receivers] += total * w
        return matrix, bill

    def _discretionary_flow(self) -> np.ndarray:
        propensity = self.rng.uniform(self._p_low, self._p_high)
        rsp = self.config.resupply
        if rsp.retain > 0.0 and self._recap_recipients.any():
            # The recapitalised set retains. Guarded so that a run without the
            # switch never reaches this line and the draw above is the only
            # thing that touched the propensity, which is what makes the
            # default reproduce to the bit.
            propensity = np.where(self._recap_recipients,
                                  propensity * (1.0 - rsp.retain), propensity)
        spent = propensity * np.maximum(self.holdings, 0.0) * self._has_out
        if self._below.any():
            # ``drawdown``: below the floor, spending comes off subsistence
            # rather than off propensity, and it does not consult inflow.
            # The node goes on consuming, consumes less, and eats its stock.
            #
            # ``min`` with holdings is the whole of the exit condition. A
            # node whose stock is gone spends zero and receives whatever
            # still points at it, so it leaves circulation by running out
            # rather than by a flag, and it comes back if an edge does.
            # **No absorbing wall, and none is needed.**
            need = self.config.subsistence.need
            floor_spend = np.minimum(
                need, np.maximum(self.holdings, 0.0)
            ) * self._has_out
            spent = np.where(self._below, floor_spend, spent)
        route = self._route
        if not self._alive.all():
            # A node that has left is not a counterparty either way. Its own
            # spending stops, and the routes into it are removed and the rest
            # renormalised, so what would have gone there goes to whoever is
            # still trading rather than vanishing. The branch is guarded so that
            # a run with no floor never touches this arithmetic.
            spent = spent * self._alive
            route = self._route * self._alive[None, :]
            sums = route.sum(axis=1, keepdims=True)
            route = np.divide(route, sums, out=np.zeros_like(route), where=sums > 0)
            # A node whose every out-edge points at a node that has left has
            # nowhere to spend. Without this line it still spends and nobody
            # receives, so the claim total falls by that amount and the identity
            # breaks. The in-loop assertion caught this on the infrastructure
            # channel, which reweights the routes and so reaches the case first.
            spent = spent * (sums.ravel() > 0)
        matrix = spent[:, None] * route
        self.holdings = self.holdings - spent + matrix.sum(axis=0)
        return matrix

    # -- hooks -------------------------------------------------------------
    #
    # Two no-ops, so that stage A4 can add demography and the competing
    # mechanisms without a second copy of the round loop. A second copy would
    # make the bitwise reproduction of A2 a claim about two files staying in
    # step, which is not a claim anyone can check by reading either one.

    def _rebuild_route(self) -> None:
        """Recompute the discretionary routing from the current adjacency.

        Same two lines as the constructor, factored out rather than duplicated
        so a rewired graph and a freshly built one cannot route differently.
        The payroll mask is not rebuilt: wages are a separate channel and moving
        them here would be a second intervention riding on this one.
        """
        if self.config.spec.uniform_access:
            discretionary = self.adjacency.copy()
        else:
            discretionary = np.clip(self.adjacency - self.wage_mask, 0.0, 1.0)
        row_sums = discretionary.sum(axis=1, keepdims=True)
        self._route = np.divide(
            discretionary,
            row_sums,
            out=np.zeros_like(discretionary),
            where=row_sums > 0,
        )
        self._has_out = row_sums.ravel() > 0

    def _add_wage_payer(self, i: int) -> None:
        """Give node ``i`` the payroll role, edges included.

        The construction gives every wage payer an edge to every wage receiver
        before the graph is built, so a node handed the role mid-run gets the
        same edges. Without them the node would pay wages along a channel the
        adjacency does not show, and every topological reading of the payroll
        would be reading a different graph from the one paying.
        """
        if i in self._wage_payers:
            return
        self._wage_payers = np.append(self._wage_payers, i)
        self.adjacency[i, self._wage_receivers] = 1.0

    def _drop_wage_payer(self, i: int) -> None:
        """Take the payroll role back, and the edges with it.

        **Never empties the set.** The bill is divided by the number of payers,
        so an empty set is a division by zero rather than an economy with no
        wages. A demotion that would empty it leaves the role where it is and
        the node loses its core edges only, which is the same thing the switch
        does when it is off.
        """
        if self._wage_payers.size <= 1 or i not in self._wage_payers:
            return
        self._wage_payers = self._wage_payers[self._wage_payers != i]
        self.adjacency[i, self._wage_receivers] = 0.0

    def _rewire(self, t: int) -> tuple[int, int]:
        """Move nodes between layers on holdings, and move their edges with them.

        Returns the number promoted and the number demoted this round, so a run
        that never fires says so in the record rather than passing every reading
        by never having run.
        """
        spec = self.config.rewire
        rng = self._rewire_rng
        core = np.flatnonzero(self._in_core)
        outside = np.flatnonzero(~self._in_core)
        changed = False
        promoted = demoted = 0

        # Demotion first, so a node cannot be promoted and demoted in one round
        # on two different holdings readings of the same vector.
        stock = float(self.holdings.sum())
        share = self.holdings / stock if stock > 0 else np.zeros_like(self.holdings)
        if (spec.demote_level > 0.0 or spec.demote_claim_share > 0.0) and core.size:
            below = np.zeros(core.size, dtype=bool)
            if spec.demote_level > 0.0:
                below |= self.holdings[core] < spec.demote_level
            if spec.demote_claim_share > 0.0:
                below |= share[core] < spec.demote_claim_share
            falling = core[below]
            for i in falling:
                if rng.random() < spec.retain_rate:
                    continue
                # Redirect this node's core edges at the production layer. Out-
                # degree is conserved, so what changes is targets and not
                # density.
                targets = np.flatnonzero(self.adjacency[i] > 0) if outside.size else np.array([], int)
                targets = targets[self._in_core[targets]]
                if not targets.size:
                    continue
                self.adjacency[i, targets] = 0.0
                pick = rng.choice(outside, size=targets.size, replace=targets.size > outside.size)
                self.adjacency[i, np.atleast_1d(pick)] = 1.0
                if spec.demote_cuts_inbound:
                    # What the core sends this node, which is the channel the
                    # published estimates find permanently reduced. Deleted
                    # rather than redirected: the core does not acquire a new
                    # counterparty because one of its own left, and adding one
                    # would change the core's out-degree for a reason nothing
                    # in the account calls for.
                    senders = np.flatnonzero(self.adjacency[:, i] > 0)
                    senders = senders[self._in_core[senders]]
                    self.adjacency[senders, i] = 0.0
                self._in_core[i] = False
                if spec.transfer_propensity:
                    self._p_low[i], self._p_high[i] = self._p_outside
                if spec.transfer_payroll:
                    self._drop_wage_payer(int(i))
                changed = True
                demoted += 1

        if spec.acquire_level > 0.0 or spec.acquire_top_k > 0:
            outside = np.flatnonzero(~self._in_core)
            core = np.flatnonzero(self._in_core)
            if outside.size and core.size:
                # Both conditions, applied together. A core is a count and a
                # share, and either alone names a different object.
                eligible = outside
                if spec.min_claim_share > 0.0:
                    eligible = eligible[share[eligible] >= spec.min_claim_share]
                if spec.acquire_level > 0.0:
                    eligible = eligible[self.holdings[eligible] >= spec.acquire_level]
                if spec.acquire_top_k > 0 and eligible.size:
                    order = eligible[np.argsort(-self.holdings[eligible], kind="stable")]
                    eligible = order[: spec.acquire_top_k]
                qualifying = eligible
                for i in qualifying:
                    # Stage one, getting into the room: one edge, aimed the way
                    # the construction aims every other edge, by in-degree.
                    weight = self.adjacency.sum(axis=0)[core] + 1.0
                    first = int(rng.choice(core, p=weight / weight.sum()))
                    new_targets = [first]
                    # Stage two, the cluster firing. It does not fire for
                    # everyone, which is the whole content of the second draw.
                    if rng.random() < spec.cluster_rate:
                        new_targets = list(core)
                    held = np.flatnonzero(self.adjacency[i] > 0)
                    if spec.conserve_degree and held.size:
                        drop = rng.choice(held, size=min(len(new_targets), held.size),
                                          replace=False)
                        self.adjacency[i, np.atleast_1d(drop)] = 0.0
                    self.adjacency[i, new_targets] = 1.0
                    self._in_core[i] = True
                    if spec.transfer_propensity:
                        self._p_low[i], self._p_high[i] = self._p_core
                    if spec.transfer_payroll:
                        self._add_wage_payer(int(i))
                    changed = True
                    promoted += 1

        if changed:
            np.fill_diagonal(self.adjacency, 0.0)
            self._rebuild_route()
        return promoted, demoted

    def _resupply_flow(self, t: int) -> np.ndarray | None:
        """What the existing creditors send to keep a node below the floor going.

        ``None`` when the switch is off, which is the default, so a run without
        it never reaches this arithmetic.

        The shortfall is topped up to ``rate`` times the need, out of the
        holdings of whoever already has an edge into the node, split evenly over
        those of them still trading. A resupplier that cannot fund its share
        sends what it has, which is the same rule the wage channel uses when its
        payers are illiquid rather than driving holdings negative.
        """
        spec = self.config.resupply
        if not spec.active:
            return None
        below = self._below if self.config.subsistence.mode == "drawdown" \
            else ~self._alive
        if not below.any():
            return None

        need = self.config.subsistence.need
        target = spec.rate * need
        shortfall = np.maximum(target - np.maximum(self.holdings, 0.0), 0.0)
        shortfall = np.where(below, shortfall, 0.0)
        if not shortfall.any():
            return None

        matrix = np.zeros((self._n, self._n))
        self._resupply_owed[:] = 0.0
        for j in np.flatnonzero(shortfall > 0.0):
            senders = np.flatnonzero((self.adjacency[:, j] > 0) & self._alive)
            senders = senders[senders != j]
            if senders.size == 0:
                continue
            # Asked for, and only where there is somebody to ask. A shortfall
            # at a node with no live creditor is not an unmet request, it is a
            # node outside this mechanism's reach.
            self._resupply_asked += float(shortfall[j])
            per = shortfall[j] / senders.size
            paid = np.minimum(per, np.maximum(self.holdings[senders], 0.0))
            if not paid.any():
                continue
            matrix[senders, j] += paid
            self.holdings[senders] -= paid
            self.holdings[j] += float(paid.sum())
            self._resupplied += float(paid.sum())
            # Who paid, kept per node, because the two funding routes both need
            # to give it back to exactly the nodes it came from.
            self._resupply_owed[senders] += paid
            # And what is now owed, kept bilaterally. A no-op when `repay` is
            # zero: the ledger is written either way and read only by
            # `_repay_flow`, so a run without that switch carries an array it
            # never consults, which costs one addition per rescued node and
            # keeps the two paths from diverging.
            self._resupply_ledger[senders, j] += paid
        return matrix if matrix.any() else None

    def _repay_flow(self) -> np.ndarray | None:
        """What a rescued node hands back, before it spends anything of its own.

        ``None`` when ``repay`` is zero, which is the default and the behaviour
        this model had until now: **the rescue is a gift.**

        **Senior to discretionary spending, and that ordering is the content.**
        Volume One names mortgage, rent, tax and interest as the senior claim on
        income rather than what is left after shopping, and ``_hub_debt_flow``
        already carries the same ordering. So a node repays, and if repaying
        puts it back under the subsistence line it is topped up again and owes
        more. **That is a debt trap and it is a result rather than an artefact**:
        the other ordering is a different model.

        **A debtor with no live creditor pays nothing and the balance stands.**
        Paying a node that has left circulation would freeze the claims rather
        than return them, and the arrears that build instead are the reading.

        Conservative: the ledger moves, the claim total does not.
        """
        spec = self.config.resupply
        if spec.repay <= 0.0:
            return None
        ledger = self._resupply_ledger
        owed_by = ledger.sum(axis=0)
        if not owed_by.any():
            return None

        due = spec.repay * owed_by
        cash = np.maximum(self.holdings, 0.0)
        pay = np.minimum(due, cash)
        pay = np.where(self._alive, pay, 0.0)
        matrix = np.zeros((self._n, self._n))
        for j in np.flatnonzero(pay > 0.0):
            claims = ledger[:, j] * self._alive
            total = float(claims.sum())
            if total <= 0.0:
                # Owes something, but to nobody still trading.
                self._repay_blocked += 1
                continue
            amounts = pay[j] * (claims / total)
            matrix[j, :] += amounts
            ledger[:, j] -= amounts
            self.holdings[j] -= pay[j]
            self.holdings += amounts
            self._repaid += float(pay[j])
        np.clip(ledger, 0.0, None, out=ledger)
        return matrix if matrix.any() else None

    def _park_claims(self) -> None:
        """Move a share of what a node holds out of the trading system.

        A no-op when the switch is off, which is the default.

        **After the obligations and before the spending**, so a node cannot use
        this to dodge what it owes. Volume One's senior claims are senior, and
        a rule that let a node park ahead of them would be asserting the
        opposite.

        **The claim total is untouched.** ``_total_claims`` counts parked claims
        and so does ``M``; what changes is that they are in no account the flow
        can route through, so they are outside ``M`` as a circulating quantity
        while remaining inside it as a stock. **That gap is the object this
        switch exists to create**, and it is the one thing retention could not
        produce: a retaining node's claims are still on its account and an
        obligation still reaches them.
        """
        spec = self.config.park
        if not spec.active:
            return
        if spec.target == "all":
            who = np.ones(self._n, dtype=bool)
        elif spec.target == "recapitalised":
            who = self._recap_recipients.copy()
        else:
            who = np.zeros(self._n, dtype=bool)
            who[self._l1] = True
        who &= self._alive
        if not who.any():
            return
        amount = spec.rate * np.maximum(self.holdings, 0.0) * who
        if not amount.any():
            return
        self.holdings -= amount
        self._parked += amount

    def _settle_levy(self) -> None:
        """``funding="levy"``: everybody still trading refunds the lenders.

        **Conservative and deliberately not routed through the flow.** A levy
        is not a trade, so putting it in the flow matrix would credit it as
        inflow and let a tax raise the measured support. ``_fiscal_flow``
        already draws that line for A6's transfer channel and this follows it:
        money applied outside the matrix is money that arrives without an edge.

        A node that cannot fund its share pays what it has, and the refund is
        pro rata to what was actually collected, so the claim stock is
        unchanged to the last bit and the conservation assertion stays a
        criterion rather than something to exempt.
        """
        owed = self._resupply_owed
        total = float(owed.sum())
        if total <= 0.0:
            return
        payers = self._alive.copy()
        n_live = int(payers.sum())
        if n_live == 0:
            return
        share = total / n_live
        take = np.where(payers,
                        np.minimum(share, np.maximum(self.holdings, 0.0)), 0.0)
        collected = float(take.sum())
        if collected <= 0.0:
            return
        self.holdings -= take
        self.holdings += owed * (collected / total)
        self._levied += collected

    def _recapitalise(self) -> float:
        """``funding="issuance"``: new claims make last round's lenders whole.

        **One round late, and that is the mechanism rather than a convenience.**
        An authority recapitalises against losses it has already seen, so the
        money cannot arrive in the same instant as the lending it is answering.

        It is credited to the nodes that paid, not to the nodes that were
        rescued, because those are two different interventions: this one puts
        the claims on the lender's book and leaves it to the lender to keep
        lending. Sending them straight to the node below the floor would be a
        different model and this switch does not offer it.

        Called from the round loop beside the authority's own issuance and
        therefore outside the conservation guard, which is where claims are
        allowed to be created.
        """
        amount = float(self._pending_recap.sum())
        if amount <= 0.0:
            self._pending_recap[:] = 0.0
            return 0.0
        if self.config.resupply.recap_target == "uniform":
            # The same claims, created for the same reason and in the same
            # amount, arriving somewhere else. **Only the landing point
            # differs**, which is what makes this a control rather than a
            # second scenario: any difference in the readings is attributable
            # to where the money went and to nothing else.
            live = self._alive
            n_live = int(live.sum())
            if n_live == 0:
                self._pending_recap[:] = 0.0
                return 0.0
            self.holdings += np.where(live, amount / n_live, 0.0)
            self._recap_recipients |= live
        else:
            self._recap_recipients |= self._pending_recap > 0.0
            self.holdings += self._pending_recap
        self._total_claims += amount
        self._recapitalised += amount
        self._pending_recap[:] = 0.0
        return amount

    def _cut_edges(self, t: int, inflow: np.ndarray | None) -> None:
        """Remove edges from the graph. A no-op when the switch is off.

        ``inflow`` is this round's per-node inflow where a floor is active and
        ``None`` where it is not, because the ``shock`` arm runs with the floor
        off and does not need it while the two triggered arms do.

        **Stage one carries the plumbing and not the mechanism.** The guard is
        here so the bitwise reproduction can be checked before any arithmetic
        exists to break it.
        """
        ec = self.config.edge_cut
        if not ec.active:
            return

        cut = np.zeros_like(self.adjacency, dtype=bool)

        if ec.mode == "shock":
            # One cut, at one round, over every edge in the graph. Nothing
            # triggers it and nothing propagates it: this arm asks what the
            # graph does on its own, so a rule that made the cut depend on any
            # node's state would be answering a different question.
            if t != ec.at_round or self._shock_fired:
                return
            self._shock_fired = True
            present = np.flatnonzero(self.adjacency.ravel() > 0)
            if present.size == 0:
                return
            k = int(round(ec.share * present.size))
            if k <= 0:
                return
            if ec.targeting == "random":
                pick = self._cut_rng.choice(present, size=k, replace=False)
            else:
                # Targeted at the hubs. **An edge counts as hub-incident if
                # either end is one**, and the first version ranked on the
                # target's in-degree alone. That measured something else and
                # said so: it takes in-edges away from nodes that have many, so
                # nobody is stranded, because being stranded means losing every
                # out-edge, and the reading saturated at a share of 0.20 and
                # then did not move again up to 0.70.
                #
                # The literature's result is about removing nodes, so the
                # faithful analogue removes edges on both of a hub's sides. The
                # two degree vectors are the file's own: ``sum(axis=0)`` is the
                # one ``injection_node`` and ``HubDebtSpec`` use.
                in_degree = self.adjacency.sum(axis=0)
                out_degree = self.adjacency.sum(axis=1)
                rows, cols = present // self._n, present % self._n
                weight = np.maximum(out_degree[rows], in_degree[cols])
                order = np.argsort(-weight, kind="stable")
                pick = present[order[:k]]
            cut.ravel()[pick] = True

        else:
            if inflow is None:
                return
            stressed = inflow < ec.trigger
            if not stressed.any():
                return
            if ec.mode == "self_cut":
                # The stressed node withdraws: a share of its own out-edges
                # goes. Rows, because a row is who this node can pay.
                rows = np.flatnonzero(stressed)
                for i in rows:
                    out = np.flatnonzero(self.adjacency[i] > 0)
                    k = int(round(ec.share * out.size))
                    if k <= 0:
                        continue
                    cut[i, self._cut_rng.choice(out, size=k, replace=False)] = True
            else:
                # ``run``: the edges pointing **at** the stressed node go, and
                # the decision is taken by whoever holds them. Columns, because
                # a column is who can pay this node. **The trigger is read on
                # one node and the action taken on another**, which is the one
                # thing no other rule in this model does.
                cols = np.flatnonzero(stressed)
                for j in cols:
                    senders = np.flatnonzero(self.adjacency[:, j] > 0)
                    k = int(round(ec.share * senders.size))
                    if k <= 0:
                        continue
                    cut[self._cut_rng.choice(senders, size=k, replace=False), j] = True

        if not cut.any():
            return
        self.adjacency[cut] = 0.0
        self._edges_cut += int(cut.sum())
        # The routing has to be rebuilt or the next round pays along edges that
        # are gone. ``_rebuild_route`` also refreshes ``_has_out``, which is
        # what turns a node whose out-edges are all cut into one that spends
        # nothing, and that is how this arm produces a discrete event with no
        # floor anywhere.
        self._rebuild_route()

    def _hub_sides(self) -> tuple[np.ndarray, np.ndarray]:
        """Who owes and who is owed, as two masks, by orientation.

        ``mutual`` returns the same mask twice on purpose: the hubs owe each
        other, and a node never routes to itself because the adjacency has no
        self-loops.
        """
        is_hub = np.zeros(self._n, dtype=bool)
        is_hub[self._hub_nodes] = True
        orientation = self.config.hub_debt.orientation
        if orientation == "creditor":
            return ~is_hub, is_hub
        if orientation == "debtor":
            return is_hub, ~is_hub
        return is_hub, is_hub

    def _hub_debt_flow(self, t: int) -> np.ndarray | None:
        """One round's instalment on the hub obligation, as a flow matrix.

        ``None`` when the switch is off, which is the default, so a run without
        it never reaches any of this arithmetic and the reproduction is by
        construction rather than by a no-op path.

        **The creditor is named, and that is the whole point of the switch.**
        ``asset.py``'s ``stretch_debt`` routes its instalment through the
        payer's own row precisely so that the destination stays out of the
        assumptions, which is right for that mechanism and wrong for this one:
        if nobody holds the matching asset then nobody's book loses anything
        when a payer stops paying, and there is no contagion to measure. So the
        instalment goes to the creditor set, **restricted to the creditors the
        payer already has an edge to**, which names a counterparty without
        introducing an edge. A payer with no edge to any live creditor does not
        pay, and the balance stays outstanding, in the same spirit as the wage
        channel narrowing when its payers are illiquid.

        **A creditor that has left is not a counterparty.** That line is the
        mechanism this stage exists to measure: the instalment pointed at a
        departed creditor does not arrive, and whoever was counting on that
        inflow finds out this round.

        Claims are conserved: the routing rows sum to one over the live
        creditors a payer can reach, and a payer with none is excluded rather
        than left to spend into nothing.
        """
        hd = self.config.hub_debt
        if not hd.active:
            return None

        debtors, creditors = self._hub_sides()
        live_creditors = creditors & self._alive
        if not live_creditors.any():
            self._hub_debt_blocked += 1
            return None

        reach = ((self.adjacency > 0) & live_creditors[None, :]).astype(float)
        np.fill_diagonal(reach, 0.0)
        sums = reach.sum(axis=1)

        due = hd.rate * np.maximum(self.holdings, 0.0)
        due = np.where(debtors & self._alive & (sums > 0.0), due, 0.0)
        if not due.any():
            self._hub_debt_blocked += 1
            return None

        route = np.divide(reach, sums[:, None],
                          out=np.zeros_like(reach), where=sums[:, None] > 0.0)
        matrix = due[:, None] * route
        self.holdings = self.holdings - due + matrix.sum(axis=0)
        self._hub_debt_paid += float(due.sum())
        return matrix

    def _fiscal_flow(self, t: int) -> np.ndarray | None:
        """Claims moved by a fiscal channel, as a flow matrix. ``None`` here.

        A subclass that moves claims between nodes has two places to do it: this
        hook, whose matrix joins the round's flow and therefore counts as inflow
        wherever inflow is read, or ``_post_round``, which moves holdings
        directly and does not appear in the flow at all. The two are different
        objects and the choice matters: a transfer routed through here is an
        edge, and a transfer applied in ``_post_round`` is money that arrives
        without one.

        Whichever it does, it must conserve the claim total, since the
        assertion above compares the holdings before and after this whole
        stage.
        """
        return None

    def _pre_round(self, t: int) -> None:
        """Called before issuance is credited. Base class does nothing."""

    def _post_round(self, t: int) -> None:
        """Called after measurement. Base class does nothing.

        Anything an override does here must conserve the claim total, since the
        stock-flow assertion in the next round compares against the holdings
        this one left behind.
        """

    # -- driver ------------------------------------------------------------

    def run(self) -> NetworkHistory:
        cfg = self.config
        rounds, n = cfg.rounds, self._n

        potential = int(self._potential_reached.sum())
        out: dict[str, np.ndarray] = {
            "total_volume": np.zeros(rounds),
            "effective_support": np.zeros(rounds),
            "effective_support_l2": np.zeros(rounds),
            "realized_support": np.zeros(rounds),
            "active_nodes": np.zeros(rounds),
            "layer2_reached": np.zeros(rounds),
            "layer1_volume": np.zeros(rounds),
            "layer2_inflow": np.zeros(rounds),
            "issuance": np.zeros(rounds),
            "wage_owed": np.zeros(rounds),
            "wage_paid": np.zeros(rounds),
            "intermediate_holdings": np.zeros(rounds),
            "holdings": np.zeros((rounds, n)),
            "active_resources": np.zeros(rounds),
            "total_resources": np.zeros(rounds),
            "written_off": np.zeros(rounds),
            "starved": np.zeros(rounds),
            "promoted": np.zeros(rounds),
            "demoted": np.zeros(rounds),
            "frozen_holdings": np.zeros(rounds),
            "parked": np.zeros(rounds),
        }

        # The real side. Constant every round, exactly as in ``economy.py``:
        # nothing in this stage produces or consumes resources, so R and R_a
        # are levels the claim side is measured against, not state.
        resources_offered = cfg.total_resources * (1.0 - cfg.resource_withholding)

        epsilon_abs: float | None = None
        snapshots: dict[int, np.ndarray] = {}
        every = cfg.snapshot_every

        for t in range(rounds):
            self._pre_round(t)
            issued = self._pending_issuance
            if issued:
                # `top_node` is the line this branch replaced, unchanged, so the
                # default path is the previous behaviour and not a
                # reimplementation of it. See `INJECTION_TARGETS`.
                if cfg.injection_target == "top_node":
                    self.holdings[self.injection_node] += issued
                else:
                    self.holdings += issued / n
                self._total_claims += issued
            self._pending_issuance = 0.0

            # Beside the authority's own issuance, and for the same reason it
            # sits here: this is the one place in the round where claims are
            # allowed to come into existence, so it is outside the guard below.
            # A no-op unless `resupply.funding` is "issuance".
            self._recapitalise()

            # The conservation check counts parked claims, because parking
            # moves them out of the trading accounts and not out of existence.
            # With the switch off this is the same expression it always was.
            before = float(self.holdings.sum()) + float(self._parked.sum())
            wage_matrix, _ = self._wage_flow()
            # Income arrives, then the rescue tops up whoever was seen to be in
            # trouble, then obligations are served, then what is left is spent.
            # The below-the-floor set this reads was written at the end of last
            # round, which is the right causal order: a node is rescued after it
            # has been seen to be in trouble, not in the same instant.
            # Income arrives, then last round's debt is served, then whoever
            # is still short is topped up. Repaying first is what lets a rescue
            # push its own recipient back under the line, which is the state
            # this switch exists to make reachable.
            repay_matrix = self._repay_flow()
            resupply_matrix = self._resupply_flow(t)
            # Who carries the cost of that rescue. Both routes give it back to
            # exactly the nodes it came from and differ only in where the money
            # to do that comes from: "levy" takes it from everybody still
            # trading, here and now and conservatively; "issuance" creates it
            # and lands it next round, through the block above. "creditors",
            # the default, does neither, and the lenders simply carry it.
            if self.config.resupply.funding == "levy":
                self._settle_levy()
            elif self.config.resupply.funding == "issuance":
                self._pending_recap += self._resupply_owed
            # The obligation is served before discretionary spending, so it is
            # senior to consumption. That ordering is not neutral and it is not
            # arbitrary: Volume One names the upward leakage as mortgage, rent,
            # tax and interest, and those are the senior claim on a household's
            # income rather than what is left after it has shopped. The other
            # ordering is a different model and this switch does not offer it.
            debt_matrix = self._hub_debt_flow(t)
            # Out of reach before the discretionary spending is computed, so
            # what is parked is out of the spending base as well as out of the
            # obligations that were already served above.
            self._park_claims()
            spend_matrix = self._discretionary_flow()
            fiscal_matrix = self._fiscal_flow(t)
            flow = wage_matrix + spend_matrix
            if fiscal_matrix is not None:
                flow = flow + fiscal_matrix
            if debt_matrix is not None:
                flow = flow + debt_matrix
            if resupply_matrix is not None:
                flow = flow + resupply_matrix
            if repay_matrix is not None:
                flow = flow + repay_matrix
            after = float(self.holdings.sum()) + float(self._parked.sum())
            if abs(after - before) > 1e-8:
                raise AssertionError(
                    f"stock-flow inconsistency at round {t}: {before!r} -> {after!r}"
                )

            if epsilon_abs is None:
                live = flow[self.adjacency > 0]
                scale = float(live.mean()) if live.size else 1.0
                epsilon_abs = cfg.epsilon * max(scale, 1e-12)

            reached = reachable_from(flow, self.injection_node, epsilon_abs)
            inflow = flow.sum(axis=0)
            l2_inflow = float(flow[:, self._l2].sum())

            out["total_volume"][t] = float(flow.sum())
            out["effective_support"][t] = effective_support(inflow)
            out["effective_support_l2"][t] = effective_support(inflow[self._l2])
            out["realized_support"][t] = int(reached.sum())
            out["active_nodes"][t] = int((flow.sum(axis=0) > epsilon_abs).sum())
            out["layer2_reached"][t] = int(reached[self._l2].sum())
            out["layer1_volume"][t] = float(flow[np.ix_(self._l1, self._l1)].sum())
            out["layer2_inflow"][t] = l2_inflow
            out["issuance"][t] = issued
            out["wage_owed"][t] = self._last_bill_owed
            out["wage_paid"][t] = self._last_bill_paid
            out["intermediate_holdings"][t] = (
                float(self.holdings[self._mid].sum()) if self._mid.size else 0.0
            )
            # Section 14's chain, before the round's holdings are recorded: the
            # write-off is an end-of-round event, so the stock this round leaves
            # behind is the stock after it. Recording first and destroying after
            # would put the destruction in one round and its effect in the next,
            # and the conservation identity would not close. Zero rate leaves
            # every line here inert.
            #
            # The refill is deliberately **not** here. The issuance rule below
            # assigns ``_pending_issuance`` rather than adding to it, so adding
            # the refill at this point would be overwritten a few lines later
            # and the switch would do nothing while every other reading looked
            # normal. The refill is applied after that assignment.
            write_spec = cfg.writeoff
            destroyed_this_round = 0.0
            if write_spec.active:
                ratio = self._total_claims / max(resources_offered, 1e-12)
                if ratio > write_spec.trigger:
                    destroyed_this_round = write_spec.rate * self._total_claims
                    self.holdings *= 1.0 - write_spec.rate
                    self._total_claims -= destroyed_this_round
                    out["written_off"][t] = destroyed_this_round

            # The subsistence floor, read on this round's inflow. Guarded, so a
            # run without a floor never evaluates it.
            sub = cfg.subsistence
            if sub.active and sub.mode == "drawdown":
                # No membership flag moves here. Below the floor is a
                # spending rule and it is re-read every round, so a node
                # whose inflow returns is simply not below it any more.
                inflow_by_node = flow.sum(axis=0)
                short = inflow_by_node < sub.need
                self._short_for[short] += 1
                self._short_for[~short] = 0
                self._below = self._short_for >= sub.grace
            elif sub.active:
                inflow_by_node = flow.sum(axis=0)
                short = (inflow_by_node < sub.need) & self._alive
                self._short_for[short] += 1
                self._short_for[~short] = 0
                leaving = self._alive & (self._short_for >= sub.grace)
                if leaving.any():
                    self._alive[leaving] = False
                if sub.reversible:
                    # An in-edge that returns brings the node back. Under
                    # ``starve`` there is no such line, which is what makes that
                    # exit an absorbing wall and this one not.
                    back = (~self._alive) & (inflow_by_node >= sub.need)
                    if back.any():
                        self._alive[back] = True
                        self._short_for[back] = 0
            # Endogenous rewiring, read on this round's closing holdings so the
            # next round trades on the new graph. Guarded, so a run without it
            # never reaches ``_rewire`` and the reproduction is by construction
            # rather than by a no-op path.
            # Skipped under ``uniform_access`` for the reason the payroll-mask
            # subtraction is skipped: that arm is a complete graph with no
            # layers, so there is no core to buy into and every node already
            # reaches every other. Rewiring there does not model mobility, it
            # manufactures the structure the arm exists to remove. Measured:
            # with this guard absent the ``C = 0`` null read a closing Gini of
            # 0.13065 against A4-1's registered ceiling of 0.02, an eighteenfold
            # rise over the 0.00711 that arm is supposed to produce.
            # Edges cut out of the graph, before rewiring, so that a stage
            # running both sees the cut graph rather than a rewired copy of the
            # old one. Guarded, so a run without it never reaches the
            # arithmetic.
            # ``inflow`` unconditionally, and that is the fix for a bug this
            # line had on its first version: it passed the floor's own inflow
            # vector, which only exists when the floor is active, so with the
            # floor off the two triggered arms never fired and cut zero edges
            # at every setting. **The arms exist precisely to run without the
            # floor**, so their trigger cannot borrow the floor's state.
            self._cut_edges(t, inflow)

            rw = cfg.rewire
            if rw.active and not cfg.spec.uniform_access and t % rw.interval == 0:
                got, lost = self._rewire(t)
                out["promoted"][t] = got
                out["demoted"][t] = lost

            # Two modes, two objects, one pair of columns. In ``exit`` these
            # count nodes that have left and the claims they took with them;
            # in ``drawdown`` nobody leaves, so they count nodes below the
            # floor and the claims those still hold. **Read them against the
            # record's mode**, which is why the mode is written out.
            out_of_market = self._below if cfg.subsistence.mode == "drawdown" else ~self._alive
            out["starved"][t] = int(out_of_market.sum())
            out["frozen_holdings"][t] = float(self.holdings[out_of_market].sum())
            out["parked"][t] = float(self._parked.sum())

            out["holdings"][t] = self.holdings
            out["active_resources"][t] = resources_offered
            out["total_resources"][t] = cfg.total_resources

            l2_spending = float(spend_matrix[self._l2, :].sum())
            if self._baseline_l2_spending is None:
                self._baseline_l2_spending = l2_spending
            if every and (t % every == 0 or t == rounds - 1):
                snapshots[t] = flow.copy()

            self._last_l2_spending = l2_spending

            if self._baseline_active is None:
                self._baseline_active = l2_inflow
            auth = cfg.authority
            if auth.rule == "none":
                self._pending_issuance = 0.0
            elif auth.rule == "fixed":
                self._pending_issuance = auth.fixed_amount
            else:
                self._pending_issuance = max(
                    0.0, auth.gain * (self._baseline_active - l2_inflow)
                )

            # The hydra clause, after the issuance rule has had its say: what was
            # destroyed is funded again from the layer that is not conserved.
            # Section 14 puts this step last and makes it conditional, which is
            # why it is a switch and sits outside the rule above.
            if destroyed_this_round and cfg.writeoff.refill:
                self._pending_issuance += destroyed_this_round

            self._post_round(t)

        return NetworkHistory(
            potential_support=potential,
            node_count=n,
            adjacency=self.adjacency,
            snapshots=snapshots,
            epsilon_absolute=float(epsilon_abs or 0.0),
            **out,
        )


#: Memo for ``autonomous_share``. The quantity is a property of the
#: construction and the construction is deterministic in these five fields, so
#: a repeat is a lookup. It matters because ``scaled_carrier`` solves nine
#: targets by bisection and each step is a graph build: at a thousand nodes one
#: build is about half a second, nine targets at nine steps is about forty five,
#: and that is paid once per process rather than once per grid point.
_AUTONOMOUS_SHARE_MEMO: dict[tuple[int, int, int, int, int], float] = {}


def autonomous_share(config: NetworkConfig) -> float:
    """What share of the intermediate block's opening inflow comes from above.

    ``financial_to_intermediate_edges`` is an edge count, and stage A0b's
    registered prediction is about a **share**: survival is linear in the
    autonomous share, the part of the intermediary's revenue that does not come
    from the households its own payroll pays. The two are the same parameter
    only at one graph size. At 200 nodes with a core of 20 and a block of 30,
    thirty edges buy a share of ``0.3111``; at 1000 nodes with a core of 100 and
    a block of 150 the same thirty edges buy ``0.1600``. Neither the node ratio
    nor the possible-edge ratio converts one into the other, because the share
    is not linear in the count.

    So a grid written in edges means a different thing at every size, and the
    way to carry it across is to hold the share and solve for the count. This
    function is the forward direction and ``f2i_for_share`` is the inverse.

    Read on the opening round, which is where the quantity is defined: it is a
    property of the construction rather than of the trajectory, and taking it
    later would fold in the drain the stage is measuring.
    """
    if config.spec.intermediate_size <= 0:
        raise ValueError("autonomous share needs an intermediate block")

    key = (
        config.spec.seed,
        config.spec.layer1_size,
        config.spec.layer2_size,
        config.spec.intermediate_size,
        config.spec.financial_to_intermediate_edges,
    )
    if key in _AUTONOMOUS_SHARE_MEMO:
        return _AUTONOMOUS_SHARE_MEMO[key]

    captured: list[np.ndarray] = []

    class _Probe(Network):
        def _discretionary_flow(self) -> np.ndarray:
            m = super()._discretionary_flow()
            if not captured:
                captured.append((self._first_wage + m).copy())
            return m

        def _wage_flow(self):
            m, x = super()._wage_flow()
            self._first_wage = m
            return m, x

    net = _Probe(dataclasses.replace(config, rounds=1))
    net.run()
    flow = captured[0]
    block_in = float(flow[:, net._mid].sum())
    if block_in <= 0.0:
        _AUTONOMOUS_SHARE_MEMO[key] = 0.0
        return 0.0
    from_core = float(flow[np.ix_(net._l1, net._mid)].sum())
    out = from_core / block_in
    _AUTONOMOUS_SHARE_MEMO[key] = out
    return out


def scaled_carrier(
    nodes: int,
    *,
    base_nodes: int = 200,
    base_layer1: int = 20,
    base_intermediate: int = 30,
    base_edges: tuple[int, ...] = (),
    seed: int = 0,
) -> tuple[dict[str, int], tuple[int, ...]]:
    """The block sizes and the autonomous-edge grid for a carrier at ``nodes``.

    Sizes scale by the node ratio, which is a choice and a plain one: the three
    blocks keep their shares of the population. The **edge grid does not scale
    that way and cannot**, because ``financial_to_intermediate_edges`` is a
    count while stage A0b's registered prediction is about the autonomous
    share, and the share is not linear in the count. Solved instead, one
    bisection per grid point, so each returned count reproduces its original
    share at the new size.

    Measured, 200 to 1000 nodes: the registered grid
    ``(0, 1, 2, 3, 5, 8, 12, 20, 30)`` becomes ``(0, 2, 5, 8, 15, 28, 45, 72,
    128)`` and every share lands within a thousandth of its original. Neither
    the node ratio of 5 nor the possible-edge ratio of 25 produces that
    sequence; the implied multiplier runs from 2 at the bottom to 4.3 at the
    top.

    ``nodes == base_nodes`` returns the originals untouched, so a station that
    calls this at its default size is bit-identical to one that never did.
    """
    if nodes == base_nodes:
        return (
            {
                "layer1_size": base_layer1,
                "intermediate_size": base_intermediate,
                "layer2_size": base_nodes - base_layer1 - base_intermediate,
            },
            tuple(base_edges),
        )

    ratio = nodes / base_nodes
    layer1 = max(2, round(base_layer1 * ratio))
    intermediate = max(2, round(base_intermediate * ratio))
    sizes = {
        "layer1_size": layer1,
        "intermediate_size": intermediate,
        "layer2_size": nodes - layer1 - intermediate,
    }

    def cfg(l1: int, mid: int, l2: int, k: int) -> NetworkConfig:
        return NetworkConfig(
            spec=NetworkSpec(
                seed=seed, layer1_size=l1, intermediate_size=mid,
                layer2_size=l2, financial_to_intermediate_edges=k,
            ),
            seed=seed, rounds=1,
        )

    base_l2 = base_nodes - base_layer1 - base_intermediate
    grid = []
    for k in base_edges:
        target = autonomous_share(cfg(base_layer1, base_intermediate, base_l2, k))
        grid.append(
            f2i_for_share(
                target,
                cfg(layer1, intermediate, sizes["layer2_size"], 0),
            )
        )
    return sizes, tuple(grid)


def f2i_for_share(target: float, config: NetworkConfig, cap: int = 100_000) -> int:
    """The edge count whose autonomous share is nearest ``target``, at this size.

    Bisection, because the share is monotone in the count. The first draft
    scanned coarsely and then linearly around the winner, which at a thousand
    nodes meant a coarse step of 468 and a fine pass of nearly a thousand graph
    builds; it did not finish. Monotone plus integer is exactly the shape
    bisection wants, and it costs about fourteen builds instead.

    ``cap`` bounds the search at the number of edges the two blocks admit.
    A target above what this size can reach returns that bound rather than
    running away, so **callers should read the share they actually got** rather
    than assuming the target was met. The registered grid's top does not
    transfer: 0.3111 at 200 nodes needs more than 130 edges at 1000.
    """
    hi = min(cap, config.spec.layer1_size * config.spec.intermediate_size)

    def share_at(k: int) -> float:
        return autonomous_share(
            dataclasses.replace(
                config,
                spec=config.spec.replace(financial_to_intermediate_edges=int(k)),
            )
        )

    if target <= share_at(0):
        return 0
    if target >= share_at(hi):
        return hi
    lo = 0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if share_at(mid) < target:
            lo = mid
        else:
            hi = mid
    return lo if abs(share_at(lo) - target) <= abs(share_at(hi) - target) else hi


def run_network(config: NetworkConfig) -> NetworkHistory:
    return Network(config).run()
