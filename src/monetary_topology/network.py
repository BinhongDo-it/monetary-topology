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
    Nodes reachable from the injection point along edges whose flow this round
    exceeds the cutoff ``epsilon``. This is the source framework's central
    functional, circulation reachability, made computable.

The edges in the second set are a subset of the first not because anything
blocked them but because nothing above the cutoff traversed them. That gap is
exactly the framework's distinction between a hole and a high price: a hole is
not a state the price system can express, and an edge with no flow is invisible
to any statistic built from flows.

Why the headline measure has no threshold
-----------------------------------------
Proportional claim dynamics on a fixed graph have a positive stationary
distribution on the set reachable from the injection point. Nothing there ever
reaches exactly zero (nodes outside it receive nothing and spend down; in the
two-layer runs of A2's seed 0 they are all at exactly zero from round 254), so any
measure of the form "count the nodes above a cutoff" is reporting the cutoff as
much as the economy.
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

The cutoff-based reachability measure is retained as a secondary series. The
cutoff feeds only that series and its two companions (``realized_support``,
``active_nodes``, ``layer2_reached``); total volume and effective support do
not read it, so the volume-against-support result does not depend on epsilon.

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
component of the downward flow is gone by construction. In stage A0b that
component is a term of the two-layer wage rule ``W_t = W0 [(1 - e) + e S_{t-1} /
S0]``: ``W0 (1 - e)`` is the part of payroll that does not move with the
production layer's spending, and above unit elasticity a contractual floor,
``floor_share * W0``, is the only such part. Stage A0b found that a positive
steady state needs it. Above the boundary the steady-state level is exactly
proportional to the floor (criterion A0b-5: a line through the origin whose slope
is the ``e = 0`` level), and with no floor there is none. Below the boundary, with
no binding floor and each spending propensity held at the midpoint of its
declared range, the level is the fixed point ``K W0 (1 - e) / (1 - r e)``, where
``K`` is the steady-state multiplier of the wage bill on Layer 2 spending, ``S0``
the opening spending and ``r = K W0 / S0`` below one under both presets. It falls
monotonically and reaches zero linearly as ``e`` approaches one, and it is not
proportional to ``(1 - e)``.

The three-layer graph has no wage elasticity and no floor. Its counterpart of that
component is the share of the intermediate block's opening inflow that comes from
the financial layer above (``autonomous_share``), the intermediary's autonomous
revenue. The two correspond because each is the part of the payer's funding that
does not depend on the households its payroll pays. So the prediction is that a
three-layer economy sits on the A0b collapse boundary **with its elasticity
parameter set to zero**, having been placed there by structure rather than by
choice.

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

from .industry import (
    IndustrySpec,
    assign_industries,
    build_io_matrix,
    check_feasible,
    route_weights,
    friction_vector,
    coefficient_perturbation,
    perturbation_is_off,
    industry_layers,
)
from .config import LAYER_1, LAYER_2, MonetaryAuthority, SpendRule, WageChannel

#: A realized edge is one carrying flow above this fraction of the mean edge
#: flow in round zero. Relative rather than absolute so the threshold does not
#: silently depend on the scale of the initial claim stock. It feeds the
#: reachability readouts only and no flow; total volume and effective support
#: do not read it.
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

#: And one more for who is willing to cut at all, because that draw is taken
#: once at construction while the cut stream is consumed round by round. Making
#: them share would move every later cut by one draw the moment the willingness
#: knob leaves its default, and the reading would then be about draw order.
_CUTTER_OFFSET = 61_949

#: A stream of its own for channel formation (``IndustrySpec.channel_rate``),
#: for the same reason as the rewire and edge-cut streams: turning it on must
#: not shift any other draw.
_CHANNEL_OFFSET = 40_127

#: A stream of its own for the rank-and-fill control arm, same reason again. It
#: is drawn from once, at build time, and only when that arm is on, so a run
#: without it reaches none of this.
_GREEDY_OFFSET = 70_207

#: What the rank-and-fill queue may be ordered on. See ``GreedySpec.rank_by``.
GREEDY_RANKS: tuple[str, ...] = ("inflow", "degree", "bilateral", "terms")

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
    #: leakage ratio. That version is available via ``uniform_degree`` and is run
    #: as the control, and effective support contracts there as well, by about as
    #: much (``test_degree_heterogeneity_is_not_load_bearing``): what carries the
    #: contraction is the layer structure together with the injection point, and
    #: the heterogeneity of degree is not.
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
    #: households its own payroll pays. It is this model's counterpart of stage
    #: A0b's object, the part of payroll that does not move with the production
    #: layer's spending: ``W0 (1 - e)`` in A0b's wage rule below unit elasticity,
    #: a contractual floor above it. A0b found a positive steady state only while
    #: that part is non-zero, so this is swept rather than set. The count stands
    #: in for a share; ``autonomous_share`` reads the share and says why it
    #: corresponds.
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
    #: 3. every node draws the same spending propensity, the mean of the two
    #:    layers' values weighted by each layer's share of the opening claim
    #:    stock, so the aggregate spending flow at the opening is unchanged,
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
        assumed.** On A12's carrier ``cut_payroll`` moves the median closing
        gini by 0.32 and ``reversible`` moves it by 0.0005, so the separation
        between this and ``payroll_kept_reversible`` is carried by the payroll
        switch alone. **The 0.0005 is a median.** Cell by cell ``reversible``
        brings nodes back: 375 returns over that grid, 4 of 45 cells closing
        with a different number of nodes in the graph, and a closing-gini gap
        of 0.27 at f2i 30, elasticity 0 (49 nodes in the graph against 125).
        The edge sets carrying A8's four surfaces do not move. A12's record
        carries the cell-by-cell reading as ``reversible_switch``.
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
        Its ``reversible`` boolean leaves A8's edge sets where they were and the
        median closing gini within 0.0005 of a plain ``SubsistenceSpec(need=...)``
        on the carrier tested, while it brings nodes back cell by cell (the
        caveat in ``payroll_severed`` has the counts). It is a named corner of a
        two-boolean square, not an established second regime.
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
    not a sink; it trades with the production layer instead. As many
    replacement targets are drawn as core edges are cut, so the change is in
    targets, and the edge count stays where it was unless a replacement lands
    on a node this one already points at, which leaves it one edge short. That
    matters because density moves the terminal distribution far more than
    anything behavioural does.

    **With ``conserve_degree`` every exchange of edges is exact.** A promoted
    node gives up exactly as many edges as it gains: its stage-one target if
    that is new, and when the cluster fires as many further core members as it
    has edges outside the targets to give up, never more. A demoted node's
    replacements are drawn without replacement from outside nodes it does not
    already point at. So in an arm that only exchanges edges no node's
    out-degree moves in any round; the payroll hand-over and the inbound cut
    still move it, and are meant to. False gives up nothing on acquisition and
    keeps the original demotion draw, which is the arm A24 reads.

    Exact since 2026-10-14. Before that the conserving path gave up
    ``min(targets, edges held)`` edges and then pointed the node at every
    target, so a fired cluster took a node from 5 out-edges to the whole core
    of 20, and a demotion replacement could land on a node already pointed at.
    A13's grid read position and density together until it was rerun on this
    rule; its record prints the edge count of every run at open and close.

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

    #: Whether every exchange of edges holds out-degree exactly (True) or
    #: acquisition gives up nothing (False, out-degree rises and density moves
    #: with it). True: a promoted node gives up one edge outside its targets for
    #: each new target, and a fired cluster reaches as many core members as the
    #: node has such edges, its stage-one target first and the rest drawn
    #: uniformly; demotion replacements avoid nodes already pointed at. Exact
    #: since 2026-10-14; the class docstring says what it did before.
    conserve_degree: bool = True

    #: Rounds between rewires. One is every round.
    interval: int = 1

    #: The first round the rule may fire. Zero is the opening round and
    #: reproduces every earlier stage. It exists because an arm that runs this
    #: rule from round zero is not the same world as one that does not: the
    #: control's own path moves with it, and a comparison between the two is
    #: then two worlds rather than one world with one switch moved. A24-4 was
    #: undecidable for exactly that reason.
    from_round: int = 0

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

    **One way by default.** A parked claim does not come back unless
    ``return_rate`` is set. The one-way case is deliberately the default and was
    built first: an instrument that matures is a second mechanism and having
    both at once would have made the first impossible to read on its own.

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

    #: Share of the shortfall in circulation that comes back out of the parked
    #: stock each round. Zero is off, and off is the default, so a run that does
    #: not set it reproduces the one-way case exactly.
    #:
    #: **This is the half of the manuscript's latent pool that was missing.**
    #: Volume One, section one, states the pool both ways: claims outside the
    #: system may come back to the market to buy resources. Parking implemented
    #: only the outward half, deliberately, because an instrument that matures
    #: is a second mechanism and having both at once would have made the first
    #: unreadable.
    #:
    #: **The trigger is the shortfall, not a rate on the stock.** The manuscript
    #: has the claims come back *to buy resources*, so what pulls them is the
    #: home graph running short of circulating claims, not a clock. A decay
    #: constant on the parked stock would be a number with no source behind it;
    #: keying it to the shortfall sources the trigger and leaves one
    #: coefficient, which gets swept rather than chosen.
    #:
    #: **What this produces that the outward half cannot, measured rather than
    #: predicted.** Both halves settle on positive floors, because parking bites
    #: on one layer and the rest of the graph keeps trading, so the floor's
    #: level is not what separates them: a one-way rate can be found that
    #: reproduces any two-way floor to seven decimal places. What separates them
    #: is where the run sits in the plane whose axes are what circulates and
    #: what does not. A one-parameter family of leaks traces a curve there, and
    #: at a matched circulating level the returning arm holds between 7% and
    #: 132% less parked stock, at 32 to 216 times the dispersion across seeds.
    #: Matching one axis costs the other.
    #:
    #: **That separation needs the trigger to fire.** Where the circulating
    #: stock rises above its opening the shortfall is negative, nothing returns,
    #: and the two arms coincide because there they are one arm.
    #:
    #: **A trigger on M/R would be this same trigger.** The manuscript has the
    #: claims come back to buy resources, which reads as a price, but ``R`` and
    #: ``R_a`` are both run constants here, computed once outside the loop, so
    #: ``M/R`` is ``M`` over a constant and a target level stated in prices
    #: collapses to a target level stated in claims.
    return_rate: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("rate must lie in [0, 1]")
        if not 0.0 <= self.return_rate <= 1.0:
            raise ValueError("return_rate must lie in [0, 1]")
        if self.target not in PARK_TARGETS:
            raise ValueError(
                f"target must be one of {PARK_TARGETS}, got {self.target!r}")

    @property
    def active(self) -> bool:
        return self.rate > 0.0

    @property
    def returns(self) -> bool:
        return self.return_rate > 0.0


#: Where claims the sovereign passes down land. See ``SovereignSpec.landing``.
SOVEREIGN_LANDINGS: tuple[str, ...] = ("parkers", "production", "uniform")

#: Who a levy that serves the sovereign's debt falls on. See
#: ``SovereignSpec.levy_base``.
SOVEREIGN_LEVY_BASES: tuple[str, ...] = ("equal", "threshold")

#: The history fields the debt service writes, when it runs.
DEBT_FIELDS: tuple[str, ...] = ("debt_due", "debt_levied", "debt_levied_l2",
                                "debt_created", "debt_capitalized",
                                "debt_extinguished")

#: Whose accounts an authority that also takes back takes from. See
#: ``WithdrawSpec``. ``none`` is off.
WITHDRAW_POSITIONS: tuple[str, ...] = ("none", "financial", "proportional",
                                       "production")
#: How the amount is split among the accounts inside the position.
WITHDRAW_BASES: tuple[str, ...] = ("holdings", "equal", "threshold")
#: The columns that switch adds to the history, ``None`` when it is off.
WITHDRAW_FIELDS: tuple[str, ...] = ("withdrawn", "withdrawn_unmet",
                                    "withdrawn_l2")

#: The write-off's counters. Allocated only when ``trace_writeoff`` is on.
#: **A per-head levy is capped at each account, and the cap is where the two
#: shapes come apart.** ``uncollected`` is what the cap left behind and is not
#: carried forward; ``payers`` is how many accounts the levy could draw on at
#: all; ``drained`` is how many this round emptied, which is how the paying
#: set shrinks; ``share`` is the amount aimed at each payer, which rises as
#: that set shrinks and so makes the cap bite harder. Pro rata cannot leave a
#: shortfall, because what it aims at each account is a fraction of what that
#: account holds, so ``uncollected`` is structurally zero there and reading a
#: non-zero would mean this comment is wrong about the code.
WRITEOFF_TRACE_FIELDS: tuple[str, ...] = ("writeoff_uncollected",
                                          "writeoff_payers",
                                          "writeoff_drained",
                                          "writeoff_share")


@dataclass(frozen=True)
class SovereignSpec:
    """A sovereign drawn outside the graph, whose bonds are bought with parked claims.

    **Why outside.** The sovereign sets the edge set: which edges may exist,
    their direction and size, and the rules that draw on every agent. The
    party that draws the graph is not one of its nodes. Ruled 2026-09-11.

    **Buying a bond is parking.** A financial-layer node that buys a sovereign
    or local-government bond takes claims out of every account the flow can
    route through, and the claims still exist: they are the buyer's, held as a
    bond. That is ``ParkSpec`` as it stands, so this switch adds nothing on the
    buying side and needs ``park.rate > 0`` to have anything to act on.

    **The other side of the purchase leaves the graph.** The proceeds go into a
    pool outside it. What the pool passes down enters the graph at the
    receiving nodes as an in-edge from outside, so the subsistence floor counts
    it as their inflow. It is kept out of the flow matrix, which holds edges
    between nodes, so every support and cycle measure still reads trades
    between nodes only.

    **Two knobs, one job each.** With ``P(t)`` the claims parked in round ``t``
    and ``G(t)`` the pool when round ``t`` opens,

        G(t+1) = (1 - pass_rate) * G(t) + bond_share * P(t)

    so in steady state each round passes down ``bond_share * P`` whatever
    ``pass_rate`` is, and ``pass_rate`` sets only the mean lag, ``1 / pass_rate``
    rounds. ``bond_share`` decides how much of the parked money can come back,
    ``pass_rate`` how fast.

    **Debt is served only when asked.** With ``maturity_rate`` and
    ``coupon_rate`` at zero the stock rolls over for ever and nobody is repaid.
    Set either and a share of the bonds falls due each round, interest accrues
    on what is outstanding, and ``funding`` names who pays: the holders by
    rolling it over, the nodes still trading through a levy, or new claims.
    What a holder is paid enters the graph as an in-edge from outside, as the
    pass-down does, and the floor counts it; a levy leaves the graph and is
    nobody's inflow.

    **Off by default, and then bit for bit.** With ``pass_rate = 0`` the round
    loop never calls the pass-down, the pool is never touched, and the history
    fields this adds stay ``None``. With ``pass_rate > 0`` and both debt rates
    at zero the loop never calls the debt service either, and the run is the
    one it was before the debt service existed.
    """

    #: Share of the pool passed down each round. Zero is off, and the default.
    pass_rate: float = 0.0
    #: Share of each round's parking that buys bonds, whose proceeds go into
    #: the pool. The rest is parked as before and nothing comes back for it:
    #: reserves, cash, assets held abroad.
    bond_share: float = 1.0
    #: Who receives what is passed down. ``parkers``: the nodes that parked, in
    #: proportion to what each holds parked. ``production``: every live node
    #: outside the financial layer, the intermediate block included, in equal
    #: shares. ``uniform``: every live node, in equal shares.
    landing: str = "production"
    #: Share of the bonds outstanding that falls due each round: a geometric
    #: maturity, mean term ``1 / maturity_rate`` rounds. Zero is a perpetual
    #: bond, and the default.
    maturity_rate: float = 0.0
    #: Interest per round on the bonds outstanding, owed to their holders.
    #: Zero is the default.
    coupon_rate: float = 0.0
    #: Who pays what falls due, one of ``RESUPPLY_FUNDING``. ``creditors``: the
    #: holders carry it, principal rolls into new bonds and the coupon is added
    #: to their holding. ``levy``: the nodes still trading pay, and what cannot
    #: be collected is paid pro rata, unpaid principal rolling and unpaid
    #: coupon added to the holding. ``issuance``: claims are created and paid
    #: to the holders in the same round.
    funding: str = "creditors"
    #: Who a levy falls on. ``equal``: ``_settle_levy``'s rule, the same share
    #: for every node still trading, a node that cannot fund its share paying
    #: what it has. ``threshold``: A6's progressive base, in proportion to the
    #: part of a node's account above the mean account of the nodes still
    #: trading. Parked claims are not assessed.
    levy_base: str = "equal"

    def __post_init__(self) -> None:
        if not 0.0 <= self.pass_rate <= 1.0:
            raise ValueError("pass_rate must lie in [0, 1]")
        if not 0.0 <= self.bond_share <= 1.0:
            raise ValueError("bond_share must lie in [0, 1]")
        if self.landing not in SOVEREIGN_LANDINGS:
            raise ValueError(
                f"landing must be one of {SOVEREIGN_LANDINGS}, got {self.landing!r}")
        if not 0.0 <= self.maturity_rate <= 1.0:
            raise ValueError("maturity_rate must lie in [0, 1]")
        if not 0.0 <= self.coupon_rate <= 1.0:
            raise ValueError("coupon_rate must lie in [0, 1]")
        if self.funding not in RESUPPLY_FUNDING:
            raise ValueError(
                f"funding must be one of {RESUPPLY_FUNDING}, got {self.funding!r}")
        if self.levy_base not in SOVEREIGN_LEVY_BASES:
            raise ValueError(
                f"levy_base must be one of {SOVEREIGN_LEVY_BASES}, "
                f"got {self.levy_base!r}")
        if self.serves_debt and not self.active:
            raise ValueError(
                "maturity_rate or coupon_rate > 0 needs pass_rate > 0: with "
                "nothing passed down no bond is bought, so there is no debt to "
                "serve")

    @property
    def active(self) -> bool:
        return self.pass_rate > 0.0

    @property
    def serves_debt(self) -> bool:
        return self.maturity_rate > 0.0 or self.coupon_rate > 0.0


@dataclass(frozen=True)
class WithdrawSpec:
    """The issuance rule's other side: claims taken back when the inflow runs
    above the level that rule aims at.

    **What it changes.** ``MonetaryAuthority(rule="endogenous")`` issues
    ``gain * (target - inflow)`` while the Layer 2 inflow is short of the
    opening round's, and nothing while it is above. The rule therefore moves in
    one direction, and what it issues into a dip stays in the graph once the
    dip is over. This adds the other direction. Off by default, and off is the
    run it always was.

    **Where it takes from is the reading, not a detail.** The rule pins one
    aggregate, the Layer 2 inflow, while the subsistence floor is read per
    node. So the same pinned aggregate can leave a different set of nodes below
    the floor depending on whose account the claims come out of. ``position``
    names that set and nothing else.

    **It sits on ``NetworkConfig`` rather than on ``MonetaryAuthority``** for
    the reason ``injection_target`` does: ``economy.py``'s block model shares
    that dataclass and reads neither field, so a switch put there would be live
    in one model and silently inert in the other.

    **Claims taken back stop existing.** They are not parked and not paid to
    anyone: the account falls, the claim total falls with it, and the round's
    conservation check sees both. Parked claims are not assessed, as a levy
    does not assess them. No account is taken below zero, and what the cap
    leaves uncollected is recorded and not carried: the next round reads the
    gap again.
    """

    #: Whose accounts the claims come out of. ``none`` is off, and the default.
    #: ``financial``: the financial layer, in proportion to what each node
    #: holds, which is the layer the issuance lands in. ``proportional``: every
    #: live node, in proportion to what it holds. ``production``: every live
    #: node outside the financial layer, the intermediate block included, in
    #: proportion to what it holds, which is the set the sovereign's
    #: ``production`` landing pays into.
    position: str = "none"
    #: Share of the overshoot taken back each round, the mirror of the
    #: authority's own gain.
    gain: float = 1.0
    #: How the amount is split among the accounts inside the position, which
    #: is the shape of the collection as against the set it falls on.
    #: ``holdings``: in proportion to what each node holds, the default and the
    #: run it always was. ``equal``: the same amount from every node inside the
    #: position that holds something, which is ``_settle_levy``'s rule with the
    #: denominator named below. ``threshold``: A6's progressive base, in
    #: proportion to the part of a node's account above the mean account of the
    #: nodes inside the position, and never more than that part, the mean taken
    #: over every live node inside it so that empty accounts count in the
    #: denominator. Each is capped at the account, nothing spills outside the
    #: position, and what the cap leaves uncollected is recorded and not
    #: carried, as for ``holdings``.
    #:
    #: **Why ``equal`` is divided by the nodes holding something rather than by
    #: every live node.** Measured on this carrier before the switch was
    #: written: dividing by every live node collects 0.167 to 0.614 of what the
    #: rule asks for, because most accounts are empty (one cell has 50 positive
    #: accounts among 200 live nodes and a median account of zero). A rule that
    #: collects a quarter of what it asks for changes the aggregate, and the
    #: aggregate is the channel a comparison of shapes has to hold still.
    base: str = "holdings"
    #: Two or more positions collected in one round, each with its own shape
    #: and its own share of the amount: ``((position, base, share), ...)``.
    #: Empty is off, and off is the single-position rule above, untouched.
    #:
    #: **Why it is a field and not two switches.** ``position`` and ``base``
    #: already span "which set" and "which shape", and what this adds is
    #: neither: it is the ratio in which two sets are drawn on at once. The
    #: first round sampled that ratio at three points, 0, about 0.75 and 1 of
    #: the take falling on the financial layer, and read the same count below
    #: the floor at all three. This fills the ratio in and lets the two sets
    #: carry different shapes while it does.
    #:
    #: Shares are shares of the amount, must be positive and sum to one, and
    #: the positions must be distinct. When it is set, ``position`` and
    #: ``base`` above are not read.
    mix: tuple[tuple[str, str, float], ...] = ()

    def __post_init__(self) -> None:
        if self.position not in WITHDRAW_POSITIONS:
            raise ValueError(
                f"position must be one of {WITHDRAW_POSITIONS}, got "
                f"{self.position!r}")
        if not 0.0 < self.gain <= 1.0:
            raise ValueError("gain must lie in (0, 1]")
        if self.base not in WITHDRAW_BASES:
            raise ValueError(
                f"base must be one of {WITHDRAW_BASES}, got {self.base!r}")
        if self.mix:
            if len(self.mix) < 2:
                raise ValueError(
                    "mix needs two or more entries: one entry is the single "
                    "position rule, which position and base already say")
            seen = set()
            total = 0.0
            for entry in self.mix:
                if len(entry) != 3:
                    raise ValueError(
                        f"a mix entry is (position, base, share), got {entry!r}")
                where, how, share = entry
                if where == "none" or where not in WITHDRAW_POSITIONS:
                    raise ValueError(
                        f"a mix position must be one of "
                        f"{WITHDRAW_POSITIONS[1:]}, got {where!r}")
                if how not in WITHDRAW_BASES:
                    raise ValueError(
                        f"a mix base must be one of {WITHDRAW_BASES}, got "
                        f"{how!r}")
                if not 0.0 < float(share) <= 1.0:
                    raise ValueError("a mix share must lie in (0, 1]")
                if where in seen:
                    raise ValueError(
                        f"mix names {where!r} twice: one entry per position")
                seen.add(where)
                total += float(share)
            if abs(total - 1.0) > 1e-12:
                raise ValueError(
                    f"mix shares must sum to one, they sum to {total!r}")

    @property
    def active(self) -> bool:
        return self.position != "none" or bool(self.mix)


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

    #: ``self_cut`` only: of the nodes the trigger catches, the share that
    #: actually withdraw. One is every one of them, and is the default.
    #:
    #: **``share`` is a share of edges and this is a share of nodes**, which is
    #: the whole distinction it exists for: ``share`` is how deep a withdrawal
    #: goes and this is how wide it spreads. Without it the width is endogenous
    #: and saturates, so a run cannot ask what happens at a width the feedback
    #: does not produce on its own.
    #:
    #: **Drawn once, as a disposition of a node, not a coin flipped each
    #: round.** A per-round draw would let the set of withdrawers accumulate to
    #: everyone, which is the thing this knob is for preventing, and it is also
    #: the wrong model: withdrawing is something a node is, not something that
    #: happens to it again every round.
    #:
    #: **At one nothing is drawn at all**, so a run at the default consumes the
    #: same stream it consumed before this field existed and reproduces it to
    #: the last bit.
    #:
    #: Not named ``participation``: that word already means taking part in the
    #: economy in this repository, and one word for two objects is how a reader
    #: ends up unable to tell which is meant.
    cutter_share: float = 1.0

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
        if not 0.0 <= self.cutter_share <= 1.0:
            raise ValueError("cutter_share must lie in [0, 1]")
        if self.cutter_share < 1.0 and self.mode != "self_cut":
            # Rejected rather than ignored. A knob that silently does nothing
            # under some modes is a field with nothing guarding it, and the
            # reader finds out on the day the reading is already written down.
            raise ValueError(
                "cutter_share below one is defined for mode 'self_cut' only, "
                f"got mode {self.mode!r}"
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
    #: How the destroyed claims are taken off the accounts still trading, from
    #: ``WITHDRAW_BASES``. ``holdings`` is pro rata to what each node holds,
    #: the default and the rule this switch has always had, written into the
    #: module as one multiplication. ``equal`` takes the same amount off every
    #: account holding something and ``threshold`` takes from the part above
    #: the mean, both capped at the account, with what the cap leaves
    #: uncollected recorded and not carried.
    #:
    #: **The parked side is pro rata whatever this says.** The dial asks who
    #: among the nodes still trading carries a write-off; claims already out of
    #: circulation are not trading, and the trigger counts them, so they fall
    #: in proportion. The amount aimed at the held side is the rate times what
    #: is held, which leaves the total destroyed equal to the rate times the
    #: claim total whenever no cap binds.
    base: str = "holdings"

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate < 1.0:
            raise ValueError("write-off rate must lie in [0, 1)")
        if self.trigger < 0.0:
            raise ValueError("write-off trigger must be non-negative")
        if self.base not in WITHDRAW_BASES:
            raise ValueError(
                f"write-off base must be one of {WITHDRAW_BASES}, got "
                f"{self.base!r}")

    @property
    def active(self) -> bool:
        return self.rate > 0.0 and self.trigger > 0.0


#: What a public signal is attached to. **Three, not two, and the third one was
#: found by measurement rather than by thinking about it.**
#:
#: A3's terms are ``gamma[i,q] = gbar[q] * (1 + kappa (1 - c_i))``, so
#: ``log gamma`` is a position term plus an agent term, and **both halves are
#: potentials**. Measured on the registered configuration: a position-only
#: signal leaves a residual that is **62 to 80 percent** of the variance, and
#: position plus agent is **exact to 6.66e-16**. So the terms field carries no
#: holonomy at all; the non-zero square A22 reads sits on the agent edges and
#: the transfer wedge instead (D25's three-term decomposition).
#:
#: ``"position"``  one number per position. A published price: "X costs Y".
#:                 **Cannot say that two people pay differently at the same
#:                 position**, and on this carrier that is most of it. The
#:                 remainder is not a missing half: the counterparty had to
#:                 observe this agent to quote it these terms.
#: ``"agent"``     one number per agent. A credit rating. Cannot say that one
#:                 agent faces different terms at different positions.
#: ``"edge"``      one number per edge, which **can** express a profitable
#:                 cycle. Not implemented, and the reason is a gate rather than
#:                 an omission: see ``BroadcastSpec.terms_respond``.
#:
#: **This module's ``phi`` is always indexed by node**, because this graph's
#: vertices are agents. A caller announcing a position-level signal maps it onto
#: nodes itself, and which of the three it is describing is what ``locus``
#: records.
BROADCAST_LOCI: tuple[str, ...] = ("position", "agent", "edge")


@dataclass(frozen=True)
class BroadcastSpec:
    """A public signal every node can see, laid over the graph, not sent along it.

    **The distinction this switch exists for.** The only rule in this model that
    reads anybody else's state is ``EdgeCutSpec(mode="run")``, and it reads it
    along trade edges: who can see node j is exactly j's in-neighbours. So
    information here percolates, and the information graph is a subgraph of the
    transaction graph. A broadcast is the other way information travels: it does
    not percolate, everybody has it at once, and having it is not evidence of
    already trading with anybody.

    **What it does to the routing.** Without it, flow splits over a node's
    surviving edges in proportion, and nothing anywhere compares two
    counterparties. With it, the split is tilted by the announced difference
    between where the flow would land and where it starts.

    Off by default, and off returns the routing array untouched, which is what
    makes ``weight = 0`` reproduce every earlier stage to the bit.
    """

    #: See ``BROADCAST_LOCI``. Records what the caller means ``phi`` to be; it
    #: does not change the arithmetic, which is the same gradient either way.
    locus: str = "position"

    #: How hard the routing bends toward the signal. Zero is off.
    weight: float = 0.0

    #: The announced value at each position, one entry per node. Supplied by the
    #: caller rather than derived here, because what a broadcast says is the
    #: experiment's object and not the model's: a station can announce the best
    #: scalar fit to the true terms field, or a rank, or a constant.
    phi: tuple[float, ...] = ()

    #: The first round the signal is acted on. Zero reproduces a run without it
    #: when the weight is zero anyway, and when the weight is not zero the gap
    #: between this and the round a shock lands is the lead time between an
    #: announcement and the event it is about. That gap is what the currency
    #: changeovers on the empirical side actually differ in: six weeks in one
    #: case and six days in the other, with the second one collapsing.
    from_round: int = 0

    #: The first round the signal is **no longer** acted on, so the signal is
    #: live for ``from_round <= t < until_round``. ``None`` is never off and
    #: reproduces every earlier stage to the bit, because the check below is
    #: skipped entirely when it is ``None``.
    #:
    #: **Why this exists as a separate field rather than a duration.** The two
    #: ends are not the same experiment. Switching on is a signal graph being
    #: built where there was none; switching off is one being destroyed after
    #: the flow has already reorganised around it. A duration would make the
    #: second a function of the first and hide the asymmetry, and the asymmetry
    #: is the object: category error thirteen is exactly a check that assumes
    #: the imposition and the release of a constraint are mirror images.
    until_round: int | None = None

    #: Whether terms respond to the flow that arrives. **Required for
    #: ``locus="edge"`` and the reason is discipline 12, not caution.** A3's
    #: terms are a function of position and not of flow, so piling onto a
    #: profitable edge never reduces its profit, the arbitrage never closes, and
    #: the concentration that comes out is forced by the construction rather
    #: than measured. ``locus="position"`` does not need it, because its
    #: load-bearing prediction is that the signal can never point at the loop at
    #: all, and that one **is** what the construction says.
    terms_respond: bool = False

    def __post_init__(self) -> None:
        if self.locus not in BROADCAST_LOCI:
            raise ValueError(f"locus must be one of {BROADCAST_LOCI}")
        if self.locus == "edge" and not self.terms_respond:
            raise NotImplementedError(
                "locus='edge' with terms that do not respond to flow: the "
                "arbitrage never closes and the concentration is forced by the "
                "construction, so the arm would not be an arm (discipline 12)"
            )


@dataclass(frozen=True)
class GreedySpec:
    """Each node fills its best edge first, then the next best, and so on.

    **The assumption this switch exists to grant.** Every other rule here splits
    a node's spending over its surviving edges in proportion, so nothing
    anywhere ranks two counterparties. This one does: a node sends to the
    counterparty that did the most business last round until that counterparty
    is full, then to the next, and so on down its own out-edges. It is the agent
    standard economics is most willing to grant, and it is granted here on
    purpose: **it is the strongest assumption for the opposing account and the
    weakest for this one.** No rationality beyond what a node can see, no
    forecasting, no aversion holding it back from moving on.

    **Zero parameters beyond the flag**, and that is a requirement rather than a
    convenience:

    * *what "best" means* is last round's inflow, which is the quantity
      ``EdgeCutSpec(mode="run")`` already reads. The two rules read one number
      and act on it with opposite signs: ``run`` sees a low one and cuts, this
      sees a high one and fills. That is what makes the pair of them a clean
      crossing rather than two unrelated interventions.
    * *what "full" means* is that same number. This model has no capacity
      anywhere: a node receives whatever points at it, so "fill" had to be
      given an object, and the only one already on the machine that is a flow
      rather than a stock is what the counterparty took in last round.
    * *who chooses first* does not arise. The ranking is a property of the
      counterparty and not of the pair, so every node sees the same order and
      no tie-break between choosers is needed. **The version of this rule that
      needed one would have grown a knob here.**

    **Two consequences fixed here rather than left to the caller.** Before any
    inflow has been observed the rule is inert and the proportional split
    stands, exactly as the triggered edge-cut arms are inert on their first
    round. And when the ranked capacities do not absorb a node's whole budget,
    the remainder is spread proportionally over the same edges rather than left
    unspent: leaving it unspent would put a second mechanism on the claim
    identity, riding on this one.

    **What it may not do.** It may reorder and it may starve, but it may not
    delete: the adjacency is untouched, so an edge that receives nothing this
    round is eligible again next round. That is the line between this and
    ``run``, which removes the edge for good, and keeping the two apart is the
    only way the crossing of them can be read.

    Off by default, and off leaves the routing untouched, which is what makes
    every earlier stage reproduce to the bit.
    """

    #: Whether the ranking is used at all. False leaves the proportional split.
    enabled: bool = False

    #: What the queue is ordered on. **The order and the capacity are two
    #: different roles and this field separates them**: capacity stays what a
    #: counterparty took in last round, and only the ordering changes.
    #:
    #: ``"inflow"``
    #:     Last round's inflow, which is also the capacity. The original
    #:     behaviour, and the default, so a run that does not set this is the
    #:     run that was made before the field existed.
    #: ``"degree"``
    #:     The counterparty's in-degree, how many nodes can pay it. **Static**:
    #:     it moves only when the adjacency does, so a queue ordered on it
    #:     carries no feedback from the flow to the order.
    #: ``"terms"``
    #:     The terms the payer would get from that counterparty, which on the
    #:     asset stage's construction is ``γ̄(1 + κ(1 − c))`` and so is a
    #:     monotone function of the counterparty's centrality. **Ranking on the
    #:     price collapses to ranking on centrality**, and centrality is
    #:     computed from the adjacency, so this arm needs no price object and
    #:     introduces no parameter. It is static for the same reason the degree
    #:     is: nothing in the flow moves it.
    #:
    #:     **This is a stand-in and it is one on purpose.** A payer ranking
    #:     counterparties by price wants a price on the edge, and no stage here
    #:     has one: the asset stage's terms are indexed by node and asset class,
    #:     not by payer and counterparty. What can be run without inventing an
    #:     object is the ordering that a per-edge price would induce if terms
    #:     followed that construction, and that ordering is this one.
    #: ``"bilateral"``
    #:     What this payer has itself sent to that counterparty so far.
    #:     **The only one of the three that is a quantity on the edge rather
    #:     than on the node**, so every payer holds a different order and the
    #:     order is not a field anyone announces. Ties, which is what a payer
    #:     with no history to go on has, fall back to the inflow: a
    #:     counterparty never dealt with is judged by what everyone can see.
    #:
    #: The pair exists to test a claim this rule's readings already make, that
    #: the ordering is driven by its own result. Under ``"degree"`` it cannot
    #: be. Both are one number per node, so both are exact one-forms in the
    #: sense the broadcast switch documents, and neither can point at a cycle.
    rank_by: str = "inflow"

    #: The control arm. The same capacities in a random order, so the queue is
    #: still filled one counterparty at a time and money still concentrates,
    #: while which counterparty gets filled no longer has anything to do with
    #: the graph. **This is what the signal arm has to be read against**, not
    #: against the switch being off: turning it off removes the concentration
    #: too, so the difference would be the mechanism and the information at
    #: once. The permutation is drawn once, at build time, and held for the run,
    #: because a fresh draw each round would be a different intervention: it
    #: would average the ranking away rather than misdirect it.
    shuffled: bool = False

    #: How much the terms a counterparty offers worsen with the business it is
    #: already carrying. Zero is off and reproduces every earlier run to the
    #: bit, which is what makes this a switch rather than a rewrite.
    #:
    #: **This is the condition the edge locus of the broadcast switch is locked
    #: on, in the form this stage needs it.** With terms fixed by position, more
    #: flow onto a profitable counterparty never reduces what it offers, the
    #: arbitrage never closes, and any concentration that comes out is given by
    #: the construction rather than measured (discipline 12). It is also the
    #: assumption most favourable to the opposing account, which holds that
    #: arbitrage removes persistent differences: switching it on hands that
    #: mechanism over rather than keeping an advantage the construction gave.
    #:
    #: The form is ``gamma_j = gbar (1 + kappa (1 - c_j)) (1 + eta * share_j)``
    #: where ``share_j`` is the counterparty's share of last round's total
    #: inflow. The share is dimensionless, so this is too, and it is one global
    #: number of the same kind as ``kappa`` rather than one per agent. Being a
    #: knob it has to be swept and the direction reported across the sweep.
    #:
    #: Only ``rank_by="terms"`` reads it. Under the other orderings the field is
    #: never consulted and a run reaches none of this arithmetic.
    congestion: float = 0.0

    def __post_init__(self) -> None:
        # Negative values are admitted from 2026-09-03 and they are not a
        # relaxation of a check, they are a second account. A positive value is
        # congestion, terms worsening as a counterparty fills. A negative one is
        # scale, terms improving as it fills, which is what the carrier this
        # stage corresponds to actually looks like: a correspondent bank does
        # not price you worse because other banks also clear through it.
        #
        # The domain is what has to hold rather than the sign. The share is in
        # [0, 1], so ``1 + eta * share`` stays positive for every realised share
        # exactly when ``eta > -1``, and that bound needs no reading of the run.
        if self.congestion <= -1.0:
            raise ValueError("congestion must exceed -1 so that the terms "
                             "factor stays positive at every share")
        if self.rank_by not in GREEDY_RANKS:
            raise ValueError(f"rank_by must be one of {GREEDY_RANKS}, "
                             f"got {self.rank_by!r}")


@dataclass(frozen=True)
class NetworkConfig:
    """Parameters for one A2 run."""

    spec: NetworkSpec = field(default_factory=NetworkSpec)
    spend: SpendRule = field(default_factory=SpendRule)
    wages: WageChannel = field(default_factory=WageChannel)
    #: Record the write-off's four counters on the history. Off by default and
    #: off is the run as it was. **It is not a mechanism and it changes
    #: nothing**: the switch exists so the arrays are not allocated on the
    #: hundreds of runs that have no use for them, and so that turning it on
    #: is a statement that can be checked rather than assumed.
    trace_writeoff: bool = False

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

    #: A sovereign outside the graph whose bonds are bought with parked claims.
    #: Off by default; needs ``park`` on when it is on.
    sovereign: SovereignSpec = field(default_factory=SovereignSpec)

    #: The issuance rule's other side: claims taken back while the inflow runs
    #: above the level that rule aims at. Off by default; needs the endogenous
    #: rule when it is on.
    withdraw: WithdrawSpec = field(default_factory=WithdrawSpec)

    #: Industries as clusters of agents, with a Leontief matrix between them.
    #: ``count = 0`` is off and no line of ``industry.py`` is reached.
    industry: IndustrySpec = field(default_factory=IndustrySpec)
    broadcast: BroadcastSpec = field(default_factory=BroadcastSpec)

    #: The spread of terms across position, ``kappa`` in the asset stage's
    #: terms function. Carried here so the rank-and-fill rule can price a
    #: counterparty without importing that stage's config object. **The default
    #: is that stage's own registered value and is checked against it at use
    #: rather than copied and trusted**, because a constant duplicated in two
    #: files is a constant that will drift. Nothing new is chosen here. Only
    #: ``GreedySpec(rank_by="terms", congestion>0)`` reads it.
    asset_terms_spread: float = 1.0

    #: Rank-and-fill routing instead of the proportional split. Off by default,
    #: and independent of ``edge_cut`` on purpose: the two are the same signal
    #: read with opposite signs and a stage has to be able to run either alone.
    greedy: GreedySpec = field(default_factory=GreedySpec)

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
        if self.sovereign.active:
            if not self.park.active:
                raise ValueError(
                    "sovereign.pass_rate > 0 needs park.rate > 0: the bonds are "
                    "bought with parked claims, so with nothing parked there is "
                    "nothing to pass down")
            if self.park.returns:
                raise ValueError(
                    "sovereign and park.return_rate cannot both be on: both bring "
                    "the same parked stock back, so running the two would bring "
                    "it back twice")
        if self.withdraw.active and self.authority.rule != "endogenous":
            raise ValueError(
                "withdraw.position needs authority.rule == 'endogenous': what "
                "is taken back is the overshoot of that rule's own target, and "
                "the other rules have no target to overshoot")


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
    returned: np.ndarray  # (rounds,) claims that came back out of the parked stock
    potential_support: int  # constant: nodes reachable in the potential graph
    node_count: int  # constant: nodes in the graph
    adjacency: np.ndarray  # the potential graph, fixed for the whole run
    snapshots: dict[int, np.ndarray]  # round -> flow matrix, if requested
    epsilon_absolute: float  # the cutoff actually used, in claim units
    #: The sovereign's four columns. ``None`` unless ``sovereign`` is on.
    sovereign_pool: np.ndarray | None = None  # (rounds,) proceeds outside the graph, end of round
    passed_down: np.ndarray | None = None  # (rounds,) passed into the graph this round
    passed_down_l2: np.ndarray | None = None  # (rounds,) the part landing outside Layer 1
    bond_stock: np.ndarray | None = None  # (rounds,) bonds outstanding
    #: The debt service's six columns. ``None`` unless the sovereign serves its
    #: debt, that is unless ``maturity_rate`` or ``coupon_rate`` is above zero.
    debt_due: np.ndarray | None = None  # (rounds,) coupon plus principal falling due
    debt_levied: np.ndarray | None = None  # (rounds,) collected by a levy
    debt_levied_l2: np.ndarray | None = None  # (rounds,) the part of it paid outside Layer 1
    debt_created: np.ndarray | None = None  # (rounds,) new claims paid to holders
    debt_capitalized: np.ndarray | None = None  # (rounds,) coupon added to holdings of bonds
    debt_extinguished: np.ndarray | None = None  # (rounds,) principal repaid, bonds retired
    #: The withdrawal's three columns. ``None`` unless ``withdraw`` is on.
    withdrawn: np.ndarray | None = None  # (rounds,) claims taken back this round
    withdrawn_unmet: np.ndarray | None = None  # (rounds,) what no account in the position could fund
    withdrawn_l2: np.ndarray | None = None  # (rounds,) the part taken outside Layer 1
    #: The write-off's four counters. ``None`` unless ``trace_writeoff`` is on.
    #: **These record and do not act.** Nothing in the loop reads them, so a
    #: run with the switch on has to come back bit for bit against a run with
    #: it off, and that is the check A35-2 makes rather than the weaker one of
    #: comparing the switch off against the module before the fields existed.
    writeoff_uncollected: np.ndarray | None = None  # (rounds,) aimed at minus taken
    writeoff_payers: np.ndarray | None = None  # (rounds,) accounts the levy could draw on
    writeoff_drained: np.ndarray | None = None  # (rounds,) accounts this round emptied
    writeoff_share: np.ndarray | None = None  # (rounds,) the per-head share aimed at each payer
    cut_out: np.ndarray | None = None  # (rounds, n) out-edges cut from this node this round
    #: ``None`` unless the sovereign serves its debt with a levy.
    levy_out: np.ndarray | None = None  # (rounds, n) taken from this node by the levy

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
        #: The round being computed. Read by ``_apply_broadcast`` so a signal
        #: can switch on partway through, and set before the first route build.
        self._t = 0
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

        # Industries. Built here so the routing below can consult them, and
        # guarded so that ``count = 0`` leaves ``_io_weights`` at None and every
        # line downstream takes the pre-industry path.
        ind = config.industry
        self._industry_of = assign_industries(
            ind, spec.financial_nodes, np.concatenate([spec.intermediate_nodes, spec.household_nodes]).astype(int)
        )
        if ind.enabled:
            self._io = build_io_matrix(ind)
            check_feasible(self._io)
            self._io_weights = route_weights(self._io, self._industry_of)
        else:
            self._io = None
            self._io_weights = None
        #: Last round's inflow vector, read by industry switching. None on the
        #: first round, when there is nothing to have observed yet.
        self._last_inflow: np.ndarray | None = None
        #: Rank-and-fill diagnostics. Allocated whether or not the switch is on,
        #: because they are read by the stage rather than by the model and an
        #: attribute that exists only on one path is the shape a reader trips
        #: over. Nothing in the round touches them when the switch is off.
        self._greedy_filled: np.ndarray = np.zeros(n, dtype=int)
        self._greedy_ever_used: np.ndarray = np.zeros((n, n), dtype=bool)
        #: The control arm's permutation, drawn once and held. ``None`` on the
        #: signal arm and when the switch is off, and the branch that reads it
        #: is guarded on that, so neither reaches the draw.
        #: Cumulative amount sent from each payer to each counterparty. The
        #: bilateral order's key, and a quantity on the edge rather than on the
        #: node, which is the whole reason that order is a different object
        #: from the other two.
        self._greedy_history: np.ndarray = np.zeros((n, n), dtype=float)
        self._greedy_perm: np.ndarray | None = None
        if config.greedy.enabled and config.greedy.shuffled:
            self._greedy_perm = np.random.default_rng(
                config.seed + _GREEDY_OFFSET
            ).permutation(n)
        #: Cumulative industry switches. A diagnostic, printed rather than
        #: judged: a treatment that moves nothing is inert, and the way to find
        #: that out is to count what it moved, not to argue about it.
        self._switch_count = 0
        #: Rounds each industry has been below the sustainable level, -1 for
        #: healthy. Updated every round the industry machinery is on, whether
        #: or not anyone is switching, so the state is readable even in arms
        #: that hold switching at zero.
        #: Members per industry at t=0, the denominator the delivery ratio is
        #: measured against. Frozen: an industry that has shrunk is compared
        #: with what it was, not with what it has become.
        self._initial_agents = (
            np.bincount(
                self._industry_of[self._industry_of >= 0],
                minlength=config.industry.count,
            ).astype(float)
            if config.industry.enabled
            else np.zeros(0)
        )
        self._damaged_for = (
            np.full(config.industry.count, -1, dtype=int)
            if config.industry.enabled
            else np.zeros(0, dtype=int)
        )
        #: Per-industry recovery friction. Flat and equal to the scalar while
        #: ``friction_spread`` is zero, so every run that predates the spread
        #: reproduces bit for bit. Volume Two section 3 is what asks for it:
        #: it orders four bases by formation lag and the ordering is the claim.
        self._friction_of = friction_vector(config.industry)
        #: Each node's tenure in its current industry, in [0, 1]. Everyone
        #: starts at one: the economy a run starts from is an established one,
        #: and that is the reference the supply switch measures a shortfall
        #: against. A switch of industry resets the mover to zero. Allocated
        #: whether or not the switch is on, like the diagnostics above; nothing
        #: reads it while ``supply_skill`` is zero.
        self._tenure = np.ones(n)
        #: Who a membership transfer moved: those moved out, those moved in,
        #: and where the latter came from, kept so a return moves exactly them
        #: back. None until a transfer has happened. The count is a diagnostic.
        self._transfer_moved: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        self._transfer_count = 0
        #: Channel formation: its own stream, which payer has ever had a live
        #: contact in which industry (None until the rule first runs), and how
        #: many channels it has formed, a diagnostic.
        self._channel_rng = np.random.default_rng(config.seed + _CHANNEL_OFFSET)
        self._had_contact: np.ndarray | None = None
        self._channel_count = 0
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
        discretionary = self._apply_industry(discretionary)
        discretionary = self._apply_broadcast(discretionary)
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
        #: Who is willing to withdraw at all, fixed for the run. ``None`` at
        #: the default, and then nothing is drawn and nothing is filtered, so
        #: the arm is the arm it was before this existed.
        self._will_cut = self._draw_cutters()
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
        #: The sovereign's side, outside the graph: proceeds not yet passed down
        #: and bonds outstanding, neither of them a claim any node can spend,
        #: plus what has been passed down so far, in total and per receiving
        #: node. Read only when ``sovereign`` is on.
        self._sovereign_pool = 0.0
        self._bond_stock = 0.0
        self._passed_total = 0.0
        self._passed_by_node = np.zeros(n)
        self._passed_this_round = 0.0
        self._passed_l2_this_round = 0.0
        #: The debt service's side: bonds held per node, a part of ``_parked``
        #: kept only when the debt is served; every bond ever bought, which is
        #: the pool's own book because ``_bond_stock`` is net of retirements
        #: once bonds mature; what has been retired and capitalized so far; and
        #: this round's six figures.
        self._bonds_held = np.zeros(n)
        self._bonds_bought = 0.0
        self._debt_retired_total = 0.0
        self._debt_capitalized_total = 0.0
        self._debt_round = dict.fromkeys(DEBT_FIELDS, 0.0)
        #: The withdrawal's side: what the rule asked for at the end of last
        #: round, and what this round took, could not take, and took outside
        #: the financial layer. Read only when ``withdraw`` is on.
        self._pending_withdrawal = 0.0
        self._withdrawn_this_round = 0.0
        self._withdrawn_unmet_this_round = 0.0
        self._withdrawn_l2_this_round = 0.0
        #: Circulating claims before the first round, the reference the return
        #: shortfall is measured against. Set on the first round rather than
        #: here, because ``holdings`` does not exist yet at this point, and
        #: taken once and never updated, because a moving reference would make
        #: the trigger chase itself.
        self._circulating_baseline: float | None = None
        # Set when ``_run_steps`` finishes. A partially drained generator
        # leaves it None, and that is the honest state rather than a stale
        # history from an earlier call.
        self._history: NetworkHistory | None = None
        #: How much came back this round, kept so the two halves can be read
        #: apart rather than only as a net change in the parked stock.
        self._returned_this_round = 0.0
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
        route = self._greedy_reroute(route, spent)
        matrix = spent[:, None] * route
        rationed = self._ration_supply(matrix)
        if rationed is None:
            self.holdings = self.holdings - spent + matrix.sum(axis=0)
            return matrix
        # What was not delivered was not paid for, so it is subtracted from the
        # payer's outgoings rather than from the seller's receipts. Recomputing
        # the row sums instead of reusing ``spent`` is deliberate: they are no
        # longer the same number, and reusing it would leak claims.
        self.holdings = self.holdings - rationed.sum(axis=1) + rationed.sum(axis=0)
        return rationed

    # -- hooks -------------------------------------------------------------
    #
    # Two no-ops, so that stage A4 can add demography and the competing
    # mechanisms without a second copy of the round loop. A second copy would
    # make the bitwise reproduction of A2 a claim about two files staying in
    # step, which is not a claim anyone can check by reading either one.

    def _switch_industries(self) -> np.ndarray | None:
        """Move the worst-off nodes into their layer's best-paid industry.

        Who moves is read off last round's inflow, which is the only signal a
        node in this model has about how it is doing. Where they move is the
        industry with the highest mean inflow *within the same layer*: a
        household does not become a bank by filing a form, and letting it would
        make the two-layer structure a costume rather than a constraint.

        The cost is a transfer, not a deletion. It leaves the mover and lands on
        the financial layer weighted by in-degree, the same weighting that picks
        the injection node, so the round's conservation assertion covers it and
        it shows up in total volume like any other payment.

        Returns the transfer matrix, or None when nothing moved.
        """
        ind = self.config.industry
        if not ind.enabled:
            return None
        self._update_damage()
        self._grow_tenure()
        if ind.demand_skill > 0.0 and ind.skill_rate > 0.0:
            # Buyers split an industry's share by tenure, and tenure moves every
            # round, so this arm rebuilds the routing every round. With the
            # demand switch at zero the routing is rebuilt only when something
            # changes, as before.
            self._rebuild_route()
        if ind.switch_rate <= 0.0 or self._last_inflow is None:
            return None
        inflow = self._last_inflow
        movers: list[tuple[int, int, float]] = []
        lower = np.concatenate([self._mid, self._l2]).astype(int)
        for nodes in (self._l1, lower):
            # A node that has left circulation is not looking for work. Without
            # this line the switchers are exactly the nodes with the lowest
            # inflow, which after the subsistence floor is on means the ones
            # that are already dead: 6869 switches ran, and the live industry
            # membership came out identical to the arm where switching was
            # blocked entirely. Every reading of the entry friction up to this
            # point was measuring moves between graveyards.
            nodes = nodes[self._alive[nodes]]
            if nodes.size == 0:
                continue
            gs = self._industry_of[nodes]
            keep = gs >= 0
            nodes_v, gs_v = nodes[keep], gs[keep]
            uniq = np.unique(gs_v)
            if nodes_v.size == 0 or uniq.size < 2:
                continue
            means = np.array([inflow[nodes_v[gs_v == g]].mean() for g in uniq])
            best = int(uniq[int(np.argmax(means))])
            k = int(round(ind.switch_rate * nodes_v.size))
            if k <= 0:
                continue
            order = np.argsort(inflow[nodes_v], kind="stable")
            cand = nodes_v[order[:k]]
            if ind.switch_destination == "proportional":
                movers.extend(self._proportional_moves(cand, uniq, means))
                continue
            cand = cand[self._industry_of[cand] != best]
            own = means[np.searchsorted(uniq, self._industry_of[cand])] if cand.size else np.zeros(0)
            fees = np.zeros(cand.size)
            if cand.size and self._entry_threshold(best, ind.switch_cost) == float("inf"):
                # Irreversible: the best industry is damaged and closed. Nobody
                # moves into it and nobody is redirected elsewhere, because the
                # rule is "go to the best one" and the best one is shut.
                cand, own, fees = cand[:0], own[:0], fees[:0]
            elif cand.size and ind.switch_cost > 0.0:
                # Two dimensions, kept apart on purpose.
                #
                # The *decision* is dimensionless: a node moves when the
                # relative gain, the best industry's mean inflow over its own,
                # clears the threshold. Two earlier versions failed here. The
                # first deducted the fee after the move was settled, so it was a
                # tax on movers rather than a price of moving and the line read
                # flat. The second put the fee in the decision but scaled it off
                # the holdings *stock* while the gain was a *flow*: the movers
                # are by construction the lowest-inflow nodes, their stock is
                # small, the fee never bound, and sweeping 0 to 1 moved 2990
                # switches to 2693. What a move is worth is measured in inflow,
                # so what it costs has to be measured there too.
                #
                # The *payment* still comes out of the stock, because that is
                # the only place a node has anything to pay with, and it is
                # capped at what the node holds.
                thr = self._entry_threshold(best, ind.switch_cost)
                keep = (float(means.max()) - own) > thr * np.maximum(own, 1e-12)
                cand, own = cand[keep], own[keep]
                fees = np.minimum(
                    ind.switch_cost * np.maximum(own, 0.0),
                    np.maximum(self.holdings[cand], 0.0),
                )
            movers.extend(
                (int(i), best, float(f)) for i, f in zip(cand, fees, strict=True)
            )
        if not movers:
            return None

        matrix = np.zeros((self._n, self._n))
        if ind.switch_cost > 0.0:
            w = self.adjacency.sum(axis=0)[self._l1]
            w = w / w.sum() if w.sum() > 0 else np.full(self._l1.size, 1.0 / self._l1.size)
            for i, _, fee in movers:
                if fee <= 0.0:
                    continue
                matrix[i, self._l1] += fee * w
                self.holdings[i] -= fee
                self.holdings[self._l1] += fee * w
        for i, g, _ in movers:
            self._industry_of[i] = g
            # What a member knew how to do stays behind in the industry it
            # left. Reset whether or not the supply switch is on; nothing reads
            # the value while it is off.
            self._tenure[i] = 0.0
        self._switch_count += len(movers)
        self._io_weights = route_weights(self._io, self._industry_of)
        self._rebuild_route()
        return matrix if matrix.any() else None

    def _proportional_moves(
        self, cand: np.ndarray, uniq: np.ndarray, means: np.ndarray
    ) -> list[tuple[int, int, float]]:
        """Destinations when every better-paid industry of the layer is open.

        A candidate may move into any industry of its layer whose mean inflow
        beats its own industry's by that destination's entry threshold: the
        test the default rule applies to the best-paid industry alone, applied
        to each. Candidates of one industry share an own mean and so share the
        eligible set, and they are split across it in proportion to each
        destination's gain above its threshold, by largest remainder, ties to
        the lower industry index, the most attractive destination taking the
        lowest-inflow candidates first. No draw is made, so the run stays
        deterministic.

        The weight is the gain *above* the threshold, so a destination that just
        clears it takes almost nobody and one that just misses takes nobody:
        the split is continuous at the threshold. With ``switch_cost`` zero the
        threshold is zero and any strictly better-paid industry is open, which
        matches the default rule's behaviour at zero cost.

        Who is a candidate, the fee (the same share of the mover's own
        industry's mean inflow, capped at what it holds, charged only with a
        positive cost) and everything after the move are the default rule's.
        """
        ind = self.config.industry
        out: list[tuple[int, int, float]] = []
        if cand.size == 0:
            return out
        base = float(ind.switch_cost)
        thr = np.array([self._entry_threshold(int(g), base) for g in uniq])
        g_cand = self._industry_of[cand]
        pos = {int(g): i for i, g in enumerate(uniq)}
        idx_all = np.arange(uniq.size)
        for g_own in np.unique(g_cand):
            group = cand[g_cand == g_own]
            own = float(means[pos[int(g_own)]])
            scale = max(own, 1e-12)
            ok = (uniq != g_own) & np.isfinite(thr)
            gain = np.where(ok, means - own - np.where(ok, thr, 0.0) * scale, 0.0)
            ok = ok & (gain > 0.0)
            if not ok.any():
                continue
            w = np.where(ok, gain, 0.0)
            quota = group.size * w / w.sum()
            n = np.floor(quota).astype(int)
            rest = group.size - int(n.sum())
            if rest > 0:
                frac = np.where(ok, quota - n, -1.0)
                for j in np.lexsort((idx_all, -frac))[:rest]:
                    n[j] += 1
            fee_each = base * max(own, 0.0) if base > 0.0 else 0.0
            at = 0
            for j in np.lexsort((idx_all, -w)):
                if n[j] <= 0:
                    continue
                for i in group[at:at + n[j]]:
                    fee = min(fee_each, max(float(self.holdings[i]), 0.0)) if base > 0.0 else 0.0
                    out.append((int(i), int(uniq[j]), float(fee)))
                at += int(n[j])
        return out

    def _form_channels(self) -> None:
        """Form lost channels again at a finite rate. A no-op when off.

        Each round, every live payer that has had a live contact in an industry
        and now has none forms one new discretionary edge into that industry
        with probability ``channel_rate``. Every industry counts: a payer buys
        from an industry through its intermediate requirement where ``A`` has a
        coefficient, and through final demand, which ``_apply_industry`` spreads
        over every industry, always. The new counterparty is a live member of the industry
        drawn by in-degree plus one, the way the construction aims every other
        edge, leaving out anyone the payer already reaches through the payroll
        mask. Only channels the payer has had are formed again: the market
        structure the construction drew is not extended.

        Runs after the round's switching and any transfer event and before
        anything is spent, so a channel formed this round routes this round.
        """
        ind = self.config.industry
        if not ind.enabled or ind.channel_rate <= 0.0:
            return
        g = self._industry_of
        n = self._n
        count = int(ind.count)
        uniform = bool(self.config.spec.uniform_access)
        disc = (self.adjacency > 0) if uniform else ((self.adjacency - self.wage_mask) > 0)
        live_member = self._alive & (g >= 0)
        onehot = np.zeros((n, count))
        onehot[np.flatnonzero(live_member), g[live_member]] = 1.0
        contact = (disc.astype(float) @ onehot) > 0
        if self._had_contact is None:
            self._had_contact = contact.copy()
        self._had_contact |= contact
        buyers = np.flatnonzero(live_member)
        if buyers.size == 0:
            return
        has_members = onehot.any(axis=0)
        cand = self._had_contact[buyers] & ~contact[buyers] & has_members[None, :]
        pairs = np.argwhere(cand)
        if pairs.size == 0:
            return
        rng = self._channel_rng
        draws = rng.random(len(pairs))
        indeg = self.adjacency.sum(axis=0)
        changed = False
        for (bi, k), u in zip(pairs, draws):
            if u >= ind.channel_rate:
                continue
            i = int(buyers[bi])
            members = np.flatnonzero(onehot[:, k] > 0)
            if not uniform:
                members = members[self.wage_mask[i, members] == 0]
            members = members[members != i]
            if members.size == 0:
                continue
            w = indeg[members] + 1.0
            j = int(rng.choice(members, p=w / w.sum()))
            if ind.channel_conserve_degree:
                held = np.flatnonzero(disc[i])
                held = held[held != j]
                if held.size:
                    drop = int(rng.choice(held))
                    self.adjacency[i, drop] = 0.0
                    disc[i, drop] = False
            self.adjacency[i, j] = 1.0
            disc[i, j] = True
            self._channel_count += 1
            changed = True
        if changed:
            np.fill_diagonal(self.adjacency, 0.0)
            self._rebuild_route()

    def _greedy_reroute(self, route: np.ndarray, spent: np.ndarray) -> np.ndarray:
        """Rank the counterparties and fill them in order. A no-op when off.

        Returns ``route`` itself when the switch is off or before any inflow has
        been seen, so the caller then takes the pre-existing path unchanged and
        the default reproduces bit for bit.

        **Why this is here and not in ``_rebuild_route``.** Capacity is an
        amount and the routing array is a set of fractions, so the rank-and-fill
        cannot be done until a node's budget is known, and the budget is
        ``spent``. Doing it there would have meant estimating the budget, which
        is a knob wearing a different hat.

        **The ranking is the same for every payer.** ``inflow[j]`` is a property
        of the counterparty, so one ``argsort`` serves all rows and the whole
        rule is two array expressions rather than a loop over nodes. That is not
        only speed: it is why no rule about who chooses first was needed.

        The arithmetic, per payer ``i`` and its eligible edges in rank order:
        each counterparty takes ``min(what is left of i's budget, its
        capacity)``. What the capacities do not absorb is spread back over the
        same edges in the proportions the caller passed in, so the row still
        sums to one and nothing is left unspent.
        """
        if not self.config.greedy.enabled or self._last_inflow is None:
            return route
        cap = np.maximum(np.asarray(self._last_inflow, dtype=float), 0.0)
        # The order and the capacity are separate roles. Capacity is always
        # what the counterparty took in; the key the queue sorts on is either
        # that same number or the counterparty's in-degree, which does not move
        # with the flow. Ordering on the degree is how the claim that the
        # ranking drives its own input gets tested rather than asserted.
        rank_by = self.config.greedy.rank_by
        key = cap
        if rank_by == "degree":
            key = (np.asarray(self.adjacency, dtype=float) > 0).sum(axis=0)
        elif rank_by == "terms":
            # Best terms first. Terms fall as centrality rises on the asset
            # stage's construction, so with no congestion the best counterparty
            # is the most central one and the key is the centrality itself.
            # Imported from the stage that defines it rather than recomputed
            # here, so the two cannot drift apart.
            from .asset import centrality as _centrality
            cen = np.asarray(_centrality(self.adjacency), dtype=float)
            eta = float(self.config.greedy.congestion)
            if eta <= 0.0:
                key = cen
            else:
                # What the payer would pay, up to the class constant: the
                # position term times the congestion term. Ranking is on the
                # negative of it, because the queue takes the largest key first
                # and the best counterparty is the cheapest one.
                from .asset import AssetSpec as _AssetSpec
                spread = float(self.config.asset_terms_spread)
                registered = float(_AssetSpec().terms_spread)
                if spread != registered and spread == 1.0:
                    # The field was left at its default while the stage that
                    # owns the constant moved. Raise rather than run on a stale
                    # copy: this is the drift the field's note names.
                    raise ValueError(
                        "asset_terms_spread defaults to the asset stage's "
                        f"registered {registered!r} and that value has moved; "
                        "set it explicitly or update the default")
                total = float(cap.sum())
                share = cap / total if total > 0 else np.zeros_like(cap)
                gamma = (1.0 + spread * (1.0 - cen)) * (1.0 + eta * share)
                key = -gamma
        if self._greedy_perm is not None:
            # The control arm. Same numbers, reassigned to counterparties, so
            # the queue and its concentration survive and the correspondence to
            # the graph does not.
            cap = cap[self._greedy_perm]
            key = key[self._greedy_perm]
        mask = route > 0.0
        # Descending inflow, ties by index so two runs of the same graph rank
        # them the same way. ``kind="stable"`` is what makes that true.
        budget = np.maximum(spent, 0.0)[:, None]
        if rank_by == "bilateral":
            # One order per payer, because the key is a quantity on the edge.
            # Ties break on the public number, which is what a payer with no
            # history of its own has to go on. ``lexsort`` takes the last key
            # as primary, so the history is passed last.
            order2 = np.lexsort(
                (-np.broadcast_to(cap, route.shape), -self._greedy_history),
                axis=1)
            cap_o = cap[order2]
            mask_o = np.take_along_axis(mask, order2, axis=1)
            avail = mask_o * cap_o
            ahead = np.cumsum(avail, axis=1) - avail
            alloc_o = np.clip(budget - ahead, 0.0, avail)
            alloc = np.zeros_like(route)
            np.put_along_axis(alloc, order2, alloc_o, axis=1)
        else:
            order = np.argsort(-key, kind="stable")
            cap_o = cap[order]
            mask_o = mask[:, order]
            # Capacity ahead of each counterparty in the queue, counting only
            # the ones this payer can actually reach.
            avail = mask_o * cap_o[None, :]
            ahead = np.cumsum(avail, axis=1) - avail
            alloc_o = np.clip(budget - ahead, 0.0, avail)
            alloc = np.zeros_like(route)
            alloc[:, order] = alloc_o
        # Whatever the queue could not take goes back over the same edges in the
        # caller's proportions. Not spending it would be a second mechanism.
        left = np.maximum(budget.ravel() - alloc.sum(axis=1), 0.0)
        alloc = alloc + left[:, None] * route
        # What each payer has sent to each counterparty, accumulated. Only the
        # bilateral order reads it; the other two never touch it, so a run on
        # them reaches this line and nothing else.
        self._greedy_history = self._greedy_history + alloc
        total = alloc.sum(axis=1, keepdims=True)
        out = np.divide(alloc, total, out=np.zeros_like(alloc), where=total > 0)
        # A payer whose queue and remainder both came to nothing keeps the
        # proportional row, so the row sums stay at one wherever they were.
        dead = (total.ravel() <= 0.0) & self._has_out
        if dead.any():
            out[dead] = route[dead]
        # Diagnostics, not criteria, and the two are not the same kind of
        # thing. **``_greedy_filled`` is this round only**: it is overwritten
        # every time this runs, so at the end of a run it describes the last
        # round and nothing else. ``_greedy_ever_used`` accumulates, so the
        # per-payer count taken from it is the run-level quantity.
        #
        # The distinction is written here because reading the first as though
        # it were the second gave a clean separation of twenty seeds into two
        # groups that the second does not reproduce: two of the seventeen sit
        # with the three. A per-round snapshot reported as a property of a run
        # is a different quantity wearing the same name.
        used = out > 0.0
        self._greedy_filled = used.sum(axis=1)
        self._greedy_ever_used |= used
        return out

    def _ration_supply(self, matrix: np.ndarray) -> np.ndarray | None:
        """Cut each payment to what the seller's industry can actually deliver.

        An industry that has lost members has lost capacity. The Leontief
        production function is a min, so the buyer who cannot get the input does
        not spend the money elsewhere: the transaction does not happen and the
        claim stays where it was. That is the difference between an industry
        layer that redirects money and one that can destroy a trade, and it is
        the only path by which anything in this layer reaches total volume.

        Returns None when off, and the caller then takes the pre-existing code
        path unchanged, which is what keeps the zero setting bit-for-bit.
        """
        ind = self.config.industry
        if not ind.enabled or ind.supply_elasticity <= 0.0:
            return None
        g = self._industry_of
        live = (g >= 0) & self._alive
        if ind.supply_skill > 0.0:
            # Capacity weighted by tenure. With every member at one the weights
            # are exact ones, so the sum is the headcount to the last bit and a
            # run in which nobody changes industry reproduces the one without.
            w = self._skill_weights()
            current = np.bincount(g[live], weights=w[live], minlength=ind.count)
        else:
            current = np.bincount(g[live], minlength=ind.count).astype(float)
        reference = self._capacity_reference()
        ratio = np.divide(
            current,
            reference,
            out=np.ones(ind.count),
            where=reference > 0,
        )
        deliverable = 1.0 - ind.supply_elasticity * (1.0 - np.minimum(ratio, 1.0))
        return matrix * deliverable[g][None, :]

    def _demand_weights(self) -> np.ndarray:
        """Each node's weight as a seller when a buyer splits what it spends on
        the node's industry: ``1 - demand_skill * (1 - s)``. One method, so a
        stage reading the premium form overrides this alone."""
        return 1.0 - self.config.industry.demand_skill * (1.0 - self._tenure)

    def _skill_weights(self) -> np.ndarray:
        """Each node's contribution to its industry's deliverable capacity.

        ``1 - supply_skill * (1 - s)``: a fully established member counts one,
        a newcomer counts ``1 - supply_skill``. One method, so a stage that
        wants to read the premium form of the same quantity overrides this and
        ``_capacity_reference`` together and touches nothing else.
        """
        return 1.0 - self.config.industry.supply_skill * (1.0 - self._tenure)

    def _capacity_reference(self) -> np.ndarray:
        """What each industry's capacity is measured against: its t=0 headcount.

        With tenure starting at one this is also its t=0 capacity. Frozen, like
        the headcount it replaces: an industry that has lost its skill is
        compared with what it was.
        """
        return self._initial_agents

    def _grow_tenure(self) -> None:
        """Advance every live member's tenure by one round.

        ``s <- s + skill_rate * (1 - s)``. Returns at once while both tenure
        switches are off, so a run without them reaches none of this arithmetic.
        A member at one stays at exactly one, because ``skill_rate * (1 - 1)``
        is an exact zero.
        """
        ind = self.config.industry
        if (ind.supply_skill <= 0.0 and ind.demand_skill <= 0.0) or ind.skill_rate <= 0.0:
            return
        live = (self._industry_of >= 0) & self._alive
        s = self._tenure[live]
        self._tenure[live] = s + ind.skill_rate * (1.0 - s)

    def _transfer(self, t: int) -> None:
        """Change who belongs to one industry, once, and optionally change it back.

        Returns at once while ``transfer_share`` is zero, so a run without the
        event reaches none of this and reproduces the run before it bit for bit.
        """
        ind = self.config.industry
        if not ind.enabled or ind.transfer_share <= 0.0:
            return
        if t == ind.transfer_round:
            self._transfer_out()
        elif t == ind.transfer_back_round and self._transfer_moved is not None:
            self._transfer_back()

    def _transfer_out(self) -> None:
        """Move a share of the industry's live members out, and restaff it.

        Members are taken in index order and sent round robin to the other
        industries of the same layer; replacements are the first live nodes of
        those industries in index order. Deterministic on purpose, and not read
        off inflow: choosing who moves by how they are doing would put a
        selection on top of the event.
        """
        ind = self.config.industry
        k = int(ind.transfer_industry)
        g = self._industry_of
        layers = industry_layers(ind)
        same = (g >= 0) & (layers[np.maximum(g, 0)] == layers[k]) & self._alive
        members = np.flatnonzero(same & (g == k))
        m = int(round(ind.transfer_share * members.size))
        others = np.array([j for j in range(ind.count)
                           if layers[j] == layers[k] and j != k], dtype=int)
        empty = np.zeros(0, dtype=int)
        if m == 0 or others.size == 0:
            self._transfer_moved = (empty, empty, empty)
            return
        out_nodes = members[:m]
        dest = others[np.arange(m) % others.size]
        in_nodes = np.flatnonzero(same & (g != k))[:m] if ind.transfer_replace else empty
        in_origin = g[in_nodes].copy()
        g[out_nodes] = dest
        g[in_nodes] = k
        self._tenure[out_nodes] = 0.0
        self._tenure[in_nodes] = 0.0
        self._transfer_moved = (out_nodes, in_nodes, in_origin)
        self._transfer_count += int(out_nodes.size + in_nodes.size)
        self._io_weights = route_weights(self._io, self._industry_of)
        self._rebuild_route()

    def _transfer_back(self) -> None:
        """Move the same people back, and reset their tenure a second time."""
        ind = self.config.industry
        out_nodes, in_nodes, in_origin = self._transfer_moved
        g = self._industry_of
        g[out_nodes] = int(ind.transfer_industry)
        g[in_nodes] = in_origin
        self._tenure[out_nodes] = 0.0
        self._tenure[in_nodes] = 0.0
        self._transfer_count += int(out_nodes.size + in_nodes.size)
        self._transfer_moved = None
        self._io_weights = route_weights(self._io, self._industry_of)
        self._rebuild_route()

    def _perturb_coefficients(self) -> None:
        """Advance ``A`` one period: ``A' = diag(r) A diag(s)``.

        The RAS form, one row multiplier and one column multiplier, because the
        two mean different things: rows are substitution, one seller's product
        used less per unit of everyone's output; columns are fabrication, one
        buyer's intermediate input intensity. Technical progress is a directed
        trend on the rows; outsourcing is a directed trend on the columns, and
        it runs the other way.

        Every drift at zero returns immediately, so a run without perturbation
        reaches none of this and reproduces the earlier build bit for bit.
        Hawkins-Simon is rechecked every period rather than once at build time,
        because a positive column drift raises the column sums and a matrix that
        was feasible at t=0 need not stay feasible.
        """
        ind = self.config.industry
        if not ind.enabled or self._io is None or perturbation_is_off(ind):
            return
        r, c = coefficient_perturbation(ind)
        self._io = r[:, None] * self._io * c[None, :]
        check_feasible(self._io)
        self._io_weights = route_weights(self._io, self._industry_of)

    def _update_damage(self) -> None:
        """Count how long each industry has been below the sustainable level.

        The level is a share of the mean industry size **within the layer**, so
        a financial industry is measured against financial industries. An
        industry that comes back above the line resets to healthy rather than
        keeping a scar: the friction is on re-entry while it is down, which is
        the mechanism being modelled, and a permanent mark would be a second
        one riding on it.
        """
        ind = self.config.industry
        if ind.min_share <= 0.0 or self._damaged_for.size == 0:
            return
        g = self._industry_of
        lower = np.concatenate([self._mid, self._l2]).astype(int)
        for nodes in (self._l1, lower):
            # Same reason as in the switch: an industry's size is how many of
            # its members are still trading, not how many were assigned to it
            # at t=0.
            nodes = nodes[self._alive[nodes]]
            if nodes.size == 0:
                continue
            gs = g[nodes]
            gs = gs[gs >= 0]
            if gs.size == 0:
                continue
            present = np.unique(gs)
            counts = np.bincount(gs, minlength=self._damaged_for.size)
            bar = ind.min_share * counts[present].mean()
            for gi in present:
                if counts[gi] < bar:
                    self._damaged_for[gi] = max(self._damaged_for[gi], 0) + 1
                else:
                    self._damaged_for[gi] = -1

    def _entry_threshold(self, industry: int, base: float) -> float:
        """Relative-gain threshold for moving *into* ``industry``.

        Healthy industries charge ``base``. A damaged one charges more, in
        proportion to how long it has been down, and infinite friction never
        clears at all, which is the absorbing wall: the industry is not
        expensive to rejoin, it cannot be rejoined.
        """
        ind = self.config.industry
        if self._damaged_for.size == 0 or self._damaged_for[industry] < 0:
            return base
        f = (float(self._friction_of[industry])
             if self._friction_of.size else float(ind.recovery_friction))
        if np.isinf(f):
            return float("inf")
        return base * (1.0 + f * float(self._damaged_for[industry]))

    def _apply_broadcast(self, discretionary: np.ndarray) -> np.ndarray:
        """Tilt the routing toward a public signal, or return the argument.

        Returns the argument untouched when the weight is zero, which is what
        makes the default reproduce every earlier stage to the bit: the array
        that reaches ``row_sums`` is then the same object as before. Same shape
        as ``_apply_industry`` directly below, and for the same reason.
        """
        spec = self.config.broadcast
        if spec.weight == 0.0 or not spec.phi:
            return discretionary
        if self._t < spec.from_round:
            return discretionary
        if spec.until_round is not None and self._t >= spec.until_round:
            return discretionary
        phi = np.asarray(spec.phi, dtype=float)
        if phi.shape[0] != discretionary.shape[0]:
            raise ValueError(
                f"broadcast phi has {phi.shape[0]} entries for "
                f"{discretionary.shape[0]} nodes"
            )
        # One number per vertex, so what the signal says about the edge i -> j is
        # phi[j] - phi[i], a difference of two potentials, and every loop it can
        # express sums to zero. What such a signal cannot say is whatever varies
        # along the other index of the field: see BROADCAST_LOCI for the measured
        # split on A3's terms.
        gain = np.exp(spec.weight * (phi[None, :] - phi[:, None]))
        return discretionary * gain

    def _apply_industry(self, discretionary: np.ndarray) -> np.ndarray:
        """Scale each route by the buyer industry's requirement for the seller's.

        Returns the argument untouched when industries are off, which is what
        makes ``count = 0`` reproduce every earlier stage to the bit: the array
        that reaches ``row_sums`` is then the same object as before.
        """
        if self._io_weights is None:
            return discretionary
        if self.config.industry.demand_skill > 0.0:
            # Regular customers: each seller counts at its demand weight inside
            # the split below, which normalises within each industry, so only
            # the ratio between members of one industry reaches the routing.
            discretionary = discretionary * self._demand_weights()[None, :]
        # Only the intermediate-input part of a node's spending is what the
        # Leontief matrix describes. The rest is final demand -- payroll,
        # consumption, rent -- and no coefficient in ``A`` constrains where it
        # goes. Routing *all* of it through ``A`` was the first version, and it
        # stranded 38.5% of nodes with no outlet at all and collapsed total
        # volume by a factor of 34: a node whose few out-edges all point at
        # mismatched industries stopped spending entirely and became a sink,
        # which is an accidental hoarding mechanism rather than a modelled one.
        #
        # The split ratio is the intermediate input share of gross output, and
        # that share IS the column sum of ``A``. While the matrix is fixed it
        # equals ``column_sum`` for every industry, so the scalar below is the
        # whole story and is kept as its own branch: with technical change off
        # this reproduces the earlier build to the bit without depending on the
        # normaliser landing on ``column_sum`` to the last float.
        #
        # Once ``Theta`` moves the matrix, the two stop being the same thing,
        # and using the parameter instead of the live column sum was the fifth
        # modelling error of this family. The paper's whole claim about
        # technical progress is that it lowers the units of input needed per
        # unit of output, which IS the column sum falling; holding the split at
        # ``column_sum`` while the matrix drifts keeps the intermediate half at
        # a constant size and lets ``Theta`` only reshuffle who inside it gets
        # paid. Measured: driving the production rows down by a factor of ten
        # moved total volume by 0.02%.
        ind_cfg = self.config.industry
        g = self._industry_of
        if perturbation_is_off(ind_cfg):
            share = float(ind_cfg.column_sum)
        else:
            col = self._io.sum(axis=0)
            share = np.where(g >= 0, col[g], ind_cfg.column_sum)[:, None]

        # Two levels of allocation, and collapsing them was the third modelling
        # error of this stage.
        #
        # Leontief says industry ``g(i)`` needs ``A[k, g(i)]`` of industry ``k``
        # per unit of its own output. That requirement is a property of the
        # **industry**, not of how many firms happen to staff it. Weighting the
        # payment graph by ``A`` alone makes an industry's share proportional to
        # ``node count x coefficient``, so an industry that loses half its
        # members loses half its inflow and the survivors are no better off than
        # before. There is then no reason for anyone to move back into a
        # shrinking industry, the entry friction of stage three has nothing to
        # bite on, and sweeping it from zero to infinity changes nothing --
        # which is exactly what it did.
        #
        # So: the industry share is ``A[k, g(i)]`` regardless of headcount, and
        # that share is then split among whichever members of ``k`` the buyer
        # actually has an edge to. Fewer members, more each. That is what makes
        # a thinned industry attractive again, and it is the pressure the
        # recovery lag exists to hold back.
        k = ind_cfg.count
        onehot = np.zeros((self._n, k))
        seen = g >= 0
        onehot[np.arange(self._n)[seen], g[seen]] = 1.0
        per_industry = discretionary @ onehot
        denom = per_industry[:, g]
        inter = np.divide(
            discretionary * self._io_weights,
            denom,
            out=np.zeros_like(discretionary),
            where=denom > 0,
        )

        def _norm(m: np.ndarray) -> np.ndarray:
            s = m.sum(axis=1, keepdims=True)
            return np.divide(m, s, out=np.zeros_like(m), where=s > 0)

        # Final demand has an industry structure too, and leaving it out was the
        # fourth error of this stage. ``x = Ax + f``: the ``Ax`` half is the
        # matrix, the ``f`` half is the consumption basket, and **both** are
        # allocated by industry. Routing ``f`` down the raw payment graph makes
        # a household indifferent between industries, which is not a
        # simplification of Leontief, it is the negation of the thing that binds
        # a node's income to the cluster it sits in: an industry that loses half
        # its members would lose half its final demand too, and the survivors
        # would be no better off. Half the spending was then unbound, which is
        # why the entry friction kept failing to reach any aggregate.
        #
        # ``f`` is uniform across industries here. Uniform is not the same as
        # absent: uniform means each industry draws an equal share regardless of
        # headcount, whereas the raw graph gives an industry a share
        # proportional to how many nodes it has. This is the same correction
        # made above for ``A``, applied on the other half.
        f_share = np.full(k, 1.0 / k)
        final = np.divide(
            discretionary * f_share[g][None, :],
            denom,
            out=np.zeros_like(discretionary),
            where=denom > 0,
        )
        # Final demand is held at its ORIGINAL absolute share, not at
        # ``1 - share``. That was the sixth modelling error of this family and
        # it inverted the reading: letting final demand absorb whatever the
        # intermediate half gives up means technical progress makes the
        # allocation MORE even, because final demand is spread uniformly across
        # industries, and the downstream sellers get back through ``f`` exactly
        # what they lost through ``A``.
        #
        # The paper says the opposite and says it precisely: internal demand
        # shrinks for goods that are decreasingly needed in the overall
        # production pattern, "even when the external demand remains the same".
        # External demand staying the same is an absolute quantity, not a
        # share. So the two shares are set independently and their sum falls
        # below one as the matrix drifts down; the difference is spending that
        # does not happen, which is the same treatment the supply constraint
        # gives to an input that cannot be delivered.
        #
        # With technical change off, ``share`` is ``column_sum`` and the two
        # sum to exactly one, so this reproduces the earlier build to the bit.
        final_share = 1.0 - float(ind_cfg.column_sum)
        return share * _norm(inter) + final_share * _norm(final)

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
        discretionary = self._apply_industry(discretionary)
        discretionary = self._apply_broadcast(discretionary)
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
                # Redirect this node's core edges at the production layer.
                targets = np.flatnonzero(self.adjacency[i] > 0) if outside.size else np.array([], int)
                targets = targets[self._in_core[targets]]
                if not targets.size:
                    continue
                self.adjacency[i, targets] = 0.0
                if spec.conserve_degree:
                    # Replacements come from outside nodes this one does not
                    # already point at, so as many land as were cut.
                    free = outside[(self.adjacency[i, outside] == 0) & (outside != i)]
                    k = min(targets.size, free.size)
                    if k:
                        pick = rng.choice(free, size=k, replace=False)
                        self.adjacency[i, np.atleast_1d(pick)] = 1.0
                else:
                    # The original draw, kept for the arm that does not
                    # conserve degree: one that lands on a node already
                    # pointed at leaves it an edge short.
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
                    if spec.conserve_degree:
                        # As many edges given up as gained. A target already
                        # pointed at needs no edge; each new one takes the
                        # place of a held edge outside the targets. A cluster
                        # wider than that is cut to it, the stage-one target
                        # first when it is new.
                        tg = np.asarray(new_targets, dtype=int)
                        tg = tg[tg != i]
                        held = np.flatnonzero(self.adjacency[i] > 0)
                        new = tg[self.adjacency[i, tg] == 0]
                        give = held[~np.isin(held, tg)]
                        k = min(new.size, give.size)
                        if k:
                            if new.size == k:
                                add = new
                            else:
                                rest = new[new != first]
                                if first in new:
                                    more = (rng.choice(rest, size=k - 1, replace=False)
                                            if k > 1 else np.array([], int))
                                    add = np.concatenate([[first], more]).astype(int)
                                else:
                                    add = rng.choice(new, size=k, replace=False)
                            drop = rng.choice(give, size=k, replace=False)
                            self.adjacency[i, np.atleast_1d(drop)] = 0.0
                            self.adjacency[i, np.atleast_1d(add)] = 1.0
                    else:
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

    def _return_claims(self) -> None:
        """Bring parked claims back when circulation has fallen short.

        A no-op when the switch is off, which is the default, so a run that does
        not set ``return_rate`` is bit-for-bit the one-way case.

        **Before this round's parking**, so what comes back is inside the
        spending base the same round draws on. The ordering is the content: the
        manuscript has these claims return to the market to buy resources, which
        they cannot do if they arrive after the spending.

        **Keyed to the shortfall.** The pull is the home graph running short
        against the resources on offer, not the age of the parked stock.

        **Shared out in proportion to who parked**, because the parked figure is
        per node so that who parked can be read, and a return that redistributed
        it would be a second claim about the world.

        Conservation is untouched: the stock moves between two columns the
        round's assertion already sums together.
        """
        spec = self.config.park
        if not spec.returns or self._circulating_baseline is None:
            return
        parked_total = float(self._parked.sum())
        if parked_total <= 0.0:
            return
        shortfall = self._circulating_baseline - float(self.holdings.sum())
        if shortfall <= 0.0:
            return
        amount = min(parked_total, spec.return_rate * shortfall)
        if amount <= 0.0:
            return
        back = amount * (self._parked / parked_total)
        self._parked -= back
        self.holdings += back
        self._returned_this_round = float(amount)

    def _pass_down(self) -> np.ndarray | None:
        """The sovereign passes a share of its pool into the graph.

        Called only when ``sovereign`` is on, so the default path does not
        reach this method.

        **Where claims enter the graph**, beside the authority's issuance and
        the recapitalisation and before the round's conservation baseline, for
        the reason those two sit there: seen from inside the graph these are
        claims arriving from outside it, and the guard is about what the
        round's trades do to the claims already in.

        **An in-edge from outside.** The amount lands on the receivers'
        holdings and comes back per node, so the round loop can add it to the
        inflow the subsistence floor reads. It stays out of the flow matrix.

        Returns the per-node amount, or ``None`` when nothing moved.
        """
        spec = self.config.sovereign
        self._passed_this_round = 0.0
        self._passed_l2_this_round = 0.0
        pool = self._sovereign_pool
        if pool <= 0.0:
            return None
        amount = spec.pass_rate * pool
        if amount <= 0.0:
            return None
        alive = self._alive.astype(float)
        if spec.landing == "parkers":
            weights = np.maximum(self._parked, 0.0) * alive
        elif spec.landing == "production":
            weights = np.zeros(self._n)
            weights[self._l2] = 1.0
            weights *= alive
        else:
            weights = alive
        total = float(weights.sum())
        if total <= 0.0:
            return None
        share = amount * (weights / total)
        self._sovereign_pool = pool - amount
        self.holdings += share
        self._total_claims += amount
        self._passed_by_node += share
        self._passed_this_round = float(amount)
        self._passed_l2_this_round = float(share[self._l2].sum())
        return share

    def _serve_debt(self) -> np.ndarray | None:
        """What falls due on the sovereign's bonds this round, and who pays it.

        Called only when the sovereign serves its debt, so a run with both debt
        rates at zero does not reach this method.

        **On the bonds held when the round opens**, before this round's buying:
        holder ``i`` is owed coupon ``coupon_rate * b_i`` and principal
        ``maturity_rate * b_i``. **In the zone where claims enter and leave the
        graph**, after the pass-down and before the conservation baseline, for
        the reason the pass-down sits there.

        ``creditors``: the holders carry it. Principal rolls into new bonds,
        which changes nothing, and the coupon is added to what they hold.
        ``levy``: the nodes still trading pay, on the base ``levy_base`` names,
        and each holder receives what was collected in proportion to what it is
        owed; unpaid principal rolls and unpaid coupon is added to the holding.
        ``issuance``: claims are created and paid in full.

        Returns what the holders received, per node, an in-edge from outside
        the graph and so part of the inflow the floor reads, or ``None`` when
        nothing was paid.
        """
        spec = self.config.sovereign
        rec = self._debt_round
        for key in rec:
            rec[key] = 0.0
        # Cleared unconditionally and before the guard below, so the vector a
        # round reads is this round's and never the previous one's. The scalar
        # beside it, ``debt_levied``, is cleared by the loop above; this is the
        # same clearing for the per-node form, and keeping the two in one place
        # is what stops them drifting apart.
        self._levy_out_this_round = np.zeros(self._n)
        held = self._bonds_held
        coupon = spec.coupon_rate * held
        principal = spec.maturity_rate * held
        due = float(coupon.sum()) + float(principal.sum())
        rec["debt_due"] = due
        if due <= 0.0:
            return None
        if spec.funding == "creditors":
            self._bonds_held += coupon
            self._parked += coupon
            added = float(coupon.sum())
            self._bond_stock += added
            self._total_claims += added
            rec["debt_capitalized"] = added
            return None
        owed = coupon + principal
        if spec.funding == "issuance":
            share = 1.0
            rec["debt_created"] = due
        else:
            take = self._levy_for_debt(due)
            collected = float(take.sum())
            self.holdings -= take
            self._levy_out_this_round = take
            share = collected / due
            rec["debt_levied"] = collected
            rec["debt_levied_l2"] = float(take[self._l2].sum())
        paid = share * owed
        retired = share * principal
        unpaid = (1.0 - share) * coupon
        self.holdings += paid
        self._bonds_held += unpaid - retired
        self._parked += unpaid - retired
        retired_total = float(retired.sum())
        unpaid_total = float(unpaid.sum())
        self._bond_stock += unpaid_total - retired_total
        self._total_claims += rec["debt_created"] + unpaid_total - retired_total
        rec["debt_extinguished"] = retired_total
        rec["debt_capitalized"] = unpaid_total
        return paid if share > 0.0 else None

    def _levy_for_debt(self, due: float) -> np.ndarray:
        """What a levy of ``due`` collects from each node, on ``levy_base``.

        ``equal`` is ``_settle_levy``'s rule: the same share for every node
        still trading, and a node that cannot fund its share pays what it has.
        ``threshold`` is A6's progressive base: in proportion to the part of a
        node's account above the mean account of the nodes still trading, and
        never more than that part. Parked claims are not assessed.
        """
        alive = self._alive
        n_live = int(alive.sum())
        if n_live == 0:
            return np.zeros(self._n)
        cash = np.maximum(self.holdings, 0.0)
        if self.config.sovereign.levy_base == "equal":
            return np.where(alive, np.minimum(due / n_live, cash), 0.0)
        mean = float(cash[alive].sum()) / n_live
        excess = np.where(alive, np.maximum(cash - mean, 0.0), 0.0)
        base = float(excess.sum())
        if base <= 0.0:
            return np.zeros(self._n)
        return excess * min(1.0, due / base)

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
        sov = self.config.sovereign
        if sov.active:
            # The other side of the purchase. The buyer's parked stock is the
            # bond; the proceeds leave the graph for the sovereign's pool.
            raised = sov.bond_share * float(amount.sum())
            self._sovereign_pool += raised
            self._bond_stock += raised
            self._bonds_bought += raised
            if sov.serves_debt:
                self._bonds_held += sov.bond_share * amount

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

    def _take_from(self, position: str, base: str, amount: float) -> np.ndarray:
        """What one position hands over, in one shape, for ``amount``.

        Zeros when there is nothing inside the position to take, which the
        caller records as uncollected. Capped at each account, so the single
        position path needs no further cap.
        """
        holdings = np.maximum(self.holdings, 0.0) * self._alive
        inside = self._alive.copy()
        if position in ("financial", "production"):
            keep = np.zeros(self._n, dtype=bool)
            keep[self._l1 if position == "financial" else self._l2] = True
            inside &= keep
        pool = np.where(inside, holdings, 0.0)
        total = float(pool.sum())
        if total <= 0.0:
            return np.zeros(self._n)
        if base == "equal":
            payers = pool > 0.0
            return np.where(payers,
                            np.minimum(amount / int(payers.sum()), pool), 0.0)
        if base == "threshold":
            mean = total / int(inside.sum())
            excess = np.where(inside, np.maximum(pool - mean, 0.0), 0.0)
            span = float(excess.sum())
            if span <= 0.0:
                return np.zeros(self._n)
            return excess * min(1.0, amount / span)
        return np.minimum(amount * (pool / total), pool)

    def _withdraw_claims(self) -> None:
        """Take back what the issuance rule asked for at the end of last round.

        Called only when ``withdraw`` is on, so the default path does not reach
        this method. It runs where the issuance lands, before the round's
        conservation snapshot, because it is the other half of that step: the
        one place in a round where the claim total moves without a trade.

        **Inside the position, capped at each account, and no spilling outside
        it.** What the cap leaves uncollected is recorded. Pushing it onto the
        accounts that could fund it would quietly change who paid, and who paid
        is what this switch exists to read.

        **``position`` names the set and ``base`` the shape.** The two are
        orthogonal and the reading needs both: the same pinned aggregate taken
        from the same set can still leave a different set of nodes below the
        floor depending on how it is split among them.
        """
        spec = self.config.withdraw
        self._withdrawn_this_round = 0.0
        self._withdrawn_unmet_this_round = 0.0
        self._withdrawn_l2_this_round = 0.0
        amount = self._pending_withdrawal
        self._pending_withdrawal = 0.0
        if amount <= 0.0:
            return
        if spec.mix:
            # Each entry draws its own share of the amount, in its own shape,
            # off the accounts as they stood when this step opened, so the
            # entries do not see each other's take and the order they are
            # listed in does not change the result. Distinct positions can
            # still overlap: ``proportional`` contains both layers. The sum is
            # therefore capped at the account once more, which binds only on an
            # overlap and is reported when it does.
            take = np.zeros(self._n)
            for where, how, share in spec.mix:
                take = take + self._take_from(where, how,
                                              float(amount) * float(share))
            take = np.minimum(take,
                              np.maximum(self.holdings, 0.0) * self._alive)
        else:
            take = self._take_from(spec.position, spec.base, amount)
        taken = float(take.sum())
        if taken <= 0.0:
            self._withdrawn_unmet_this_round = float(amount)
            return
        self.holdings -= take
        self._total_claims -= taken
        self._withdrawn_this_round = taken
        self._withdrawn_unmet_this_round = float(amount) - taken
        self._withdrawn_l2_this_round = float(take[self._l2].sum())

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

    def _draw_cutters(self) -> np.ndarray | None:
        """Who is willing to withdraw, drawn once for the run.

        ``None`` when the knob is at its default, and the caller then filters
        nothing: no draw is made, no stream is advanced, and the arm is bitwise
        the arm it was before this method existed.

        **Drawn over every node, not over the stressed set.** The stressed set
        changes from round to round, so drawing over it would make willingness
        a property of the round rather than of the node, and the set of
        withdrawers would accumulate to everyone whatever the share said. That
        is the failure this knob exists to remove, so it must not be rebuilt
        inside it.

        Its own generator, seeded off the cut stream's offset, so that turning
        this on does not shift any draw the cut itself makes.
        """
        ec = self.config.edge_cut
        if ec.cutter_share >= 1.0:
            return None
        k = int(round(ec.cutter_share * self._n))
        mask = np.zeros(self._n, dtype=bool)
        if k > 0:
            rng = np.random.default_rng(self.config.seed + _CUTTER_OFFSET)
            mask[rng.choice(self._n, size=k, replace=False)] = True
        return mask

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
        # Cleared unconditionally and before the guard, so the vector a round
        # reads is this round's and never the previous one's. Rows, because a
        # row is who this node can pay: the quantity is the row sum of the cut
        # matrix and it means the same thing under all three modes, which is
        # what keeps one field from carrying two semantics.
        self._cut_out_this_round = np.zeros(self._n)
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
            if self._will_cut is not None:
                # Willingness is fixed for the run, so a node the trigger
                # catches every round either withdraws every round or never
                # does. The trigger still has to fire: this narrows who acts on
                # it and does not make anyone act without it.
                stressed = stressed & self._will_cut
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
        self._cut_out_this_round = cut.sum(axis=1).astype(float)
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
        """Run every round and return the history. **Unchanged behaviour.**

        The body moved to ``_run_steps``, which is the same code with one
        ``yield`` at the end of each round. Nothing inside the round changed,
        and a run through this wrapper is bit-for-bit what it was: the loop is
        drained here and the history it built is handed back.

        **Why a generator underneath.** Two graphs that trade with each other
        have to advance in lockstep, and a driver can only interleave them at a
        point the round itself names. ``_run_steps`` names one, after
        ``_post_round``, where the round's books are closed and the next round
        has not opened. A caller that wants one graph still calls ``run`` and
        sees none of this.
        """
        for _ in self._run_steps():
            pass
        assert self._history is not None
        return self._history

    def _run_steps(self):
        """The round loop, yielding the round index after each round closes."""
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
            "returned": np.zeros(rounds),
        }
        cut_on = cfg.edge_cut.active
        if cut_on:
            out["cut_out"] = np.zeros((rounds, n))
        # The sovereign's four columns exist only when it is on, so with it off
        # the history is built from the same keys as before.
        sov_on = cfg.sovereign.active
        if sov_on:
            for key in ("sovereign_pool", "passed_down", "passed_down_l2",
                        "bond_stock"):
                out[key] = np.zeros(rounds)
        # The debt service's six, likewise only when it runs.
        debt_on = sov_on and cfg.sovereign.serves_debt
        if debt_on:
            for key in DEBT_FIELDS:
                out[key] = np.zeros(rounds)
        # Per node, and only under the one funding route that takes anything
        # from a node. Under the other two nothing is taken and a field of
        # zeros would say something different from nothing being recorded.
        levy_on = debt_on and cfg.sovereign.funding == "levy"
        if levy_on:
            out["levy_out"] = np.zeros((rounds, n))
        # The withdrawal's three, likewise only when it runs.
        withdraw_on = cfg.withdraw.active
        if withdraw_on:
            for key in WITHDRAW_FIELDS:
                out[key] = np.zeros(rounds)
        # The write-off's four counters, only when asked for. They record and
        # do not act, so this allocation is the whole of what the switch does.
        trace_writeoff = bool(cfg.trace_writeoff)
        if trace_writeoff:
            for key in WRITEOFF_TRACE_FIELDS:
                out[key] = np.zeros(rounds)

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

            # The other side of the same rule, in the same zone: what it asked
            # to take back at the end of last round. Its own ledger closes
            # here, because this is the only step in the round that moves the
            # claim total without a trade. A no-op unless ``withdraw`` is on.
            if withdraw_on:
                stock_before = (float(self.holdings.sum())
                                + float(self._parked.sum()))
                low_before = float(self.holdings.min())
                self._withdraw_claims()
                moved = (stock_before - float(self.holdings.sum())
                         - float(self._parked.sum()))
                tol = 1e-9 * max(1.0, stock_before / cfg.initial_claims)
                if (abs(moved - self._withdrawn_this_round) > tol
                        or self._withdrawn_unmet_this_round < -tol
                        or float(self.holdings.min()) < min(0.0, low_before) - tol):
                    raise AssertionError(
                        f"withdrawal ledger does not close at round {t}: moved "
                        f"{moved!r} against taken "
                        f"{self._withdrawn_this_round!r}, uncollected "
                        f"{self._withdrawn_unmet_this_round!r}, least account "
                        f"{float(self.holdings.min())!r} against "
                        f"{low_before!r} before it")

            # Beside the authority's own issuance, and for the same reason it
            # sits here: this is the one place in the round where claims are
            # allowed to come into existence, so it is outside the guard below.
            # A no-op unless `resupply.funding` is "issuance".
            self._recapitalise()
            # The sovereign's pass-down, in the same zone and for the same
            # reason: claims arriving from outside the graph. Its two books are
            # checked here in the loop, because they are this mechanism's
            # conservation: what landed equals what was passed, and the pool
            # equals bonds bought less everything passed so far.
            boundary_in = None
            if sov_on:
                entering = float(self.holdings.sum()) + float(self._parked.sum())
                boundary_in = self._pass_down()
                landed = (float(self.holdings.sum()) + float(self._parked.sum())
                          - entering)
                self._passed_total += self._passed_this_round
                tol = 1e-9 * max(1.0, entering / cfg.initial_claims,
                                 self._bonds_bought / cfg.initial_claims)
                if (abs(landed - self._passed_this_round) > tol
                        or abs(self._bonds_bought - self._passed_total
                               - self._sovereign_pool) > tol
                        or self._sovereign_pool < -tol):
                    raise AssertionError(
                        f"sovereign ledger does not close at round {t}: landed "
                        f"{landed!r} against passed {self._passed_this_round!r}, "
                        f"pool {self._sovereign_pool!r} against bonds bought "
                        f"less passed {self._bonds_bought - self._passed_total!r}")
            if debt_on:
                # The debt service, in the same zone: what holders are paid
                # arrives from outside the graph and a levy leaves it. Its own
                # books close here: what moved in the graph is what was created
                # and capitalized less what was retired, the bond stock is every
                # bond bought less retirements plus capitalized coupon, and the
                # holdings of bonds add up to that stock.
                entering = float(self.holdings.sum()) + float(self._parked.sum())
                paid_in = self._serve_debt()
                rec = self._debt_round
                moved = (float(self.holdings.sum()) + float(self._parked.sum())
                         - entering)
                expect = (rec["debt_created"] + rec["debt_capitalized"]
                          - rec["debt_extinguished"])
                self._debt_retired_total += rec["debt_extinguished"]
                self._debt_capitalized_total += rec["debt_capitalized"]
                net = (self._bonds_bought - self._debt_retired_total
                       + self._debt_capitalized_total)
                tol = 1e-9 * max(1.0, entering / cfg.initial_claims,
                                 self._bonds_bought / cfg.initial_claims,
                                 self._debt_capitalized_total
                                 / cfg.initial_claims)
                if (abs(moved - expect) > tol
                        or abs(net - self._bond_stock) > tol
                        or abs(float(self._bonds_held.sum())
                               - self._bond_stock) > tol
                        or rec["debt_levied"] > rec["debt_due"] + tol):
                    raise AssertionError(
                        f"debt ledger does not close at round {t}: moved "
                        f"{moved!r} against {expect!r}, bonds "
                        f"{self._bond_stock!r} against {net!r} and held "
                        f"{float(self._bonds_held.sum())!r}")
                if paid_in is not None:
                    boundary_in = (paid_in if boundary_in is None
                                   else boundary_in + paid_in)

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
            # The coefficients move before anyone decides where to go, so a
            # switch this round is made against the new matrix.
            self._perturb_coefficients()
            switch_matrix = self._switch_industries()
            self._transfer(t)
            self._form_channels()
            if self._circulating_baseline is None:
                self._circulating_baseline = float(self.holdings.sum())
            self._returned_this_round = 0.0
            self._return_claims()
            self._park_claims()
            spend_matrix = self._discretionary_flow()
            fiscal_matrix = self._fiscal_flow(t)
            flow = wage_matrix + spend_matrix
            if switch_matrix is not None:
                flow = flow + switch_matrix
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
            self._last_inflow = inflow
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
                    # Read before the levy, because ``drained`` is a
                    # transition and the set it is counted against is the one
                    # that existed when the levy was aimed.
                    if trace_writeoff:
                        held_before = np.maximum(self.holdings, 0.0) * self._alive
                        payers_before = held_before > 0.0
                        n_payers = int(payers_before.sum())
                        out["writeoff_payers"][t] = n_payers
                        out["writeoff_share"][t] = (
                            write_spec.rate * float(self.holdings.sum())
                            / n_payers if n_payers else 0.0)
                    if write_spec.base == "holdings":
                        # Untouched, so the default path is the run it always
                        # was rather than a reimplementation of it.
                        destroyed_this_round = (write_spec.rate
                                                * self._total_claims)
                        self.holdings *= 1.0 - write_spec.rate
                    else:
                        # The same amount, aimed at the held side in a
                        # different shape. ``_take_from`` is the withdrawal's
                        # splitter, already capped at each account, and
                        # ``proportional`` there means every live node, which
                        # is the set a write-off falls on.
                        aimed = write_spec.rate * float(self.holdings.sum())
                        taken = self._take_from("proportional",
                                                write_spec.base, aimed)
                        self.holdings -= taken
                        destroyed_this_round = (
                            float(taken.sum())
                            + write_spec.rate * float(self._parked.sum()))
                        # What the cap left is not recorded in a field of its
                        # own: ``written_off`` already carries what was
                        # actually destroyed, so a shape that cannot reach the
                        # amount it aimed at shows up as a smaller total, and
                        # the reading compares those totals across bases.
                    # **Parked claims are written off in the same proportion**,
                    # and without this line the identity does not close as soon
                    # as anything is parked: the amount destroyed is taken on
                    # the claim total, which counts parked claims, while only
                    # the held side was being reduced. Measured before the fix,
                    # over 80 rounds with a parking rate of 0.02, the gap
                    # between the claim total and held plus parked reached 167
                    # on an opening stock of 100, against 1e-12 with either
                    # switch on alone. No record on disk carries both, so
                    # nothing already read is touched, and with nothing parked
                    # this line scales a zero array and cannot move a bit.
                    #
                    # **It is also what the trigger already says.** The write
                    # off fires on the claim total over the resources offered,
                    # and that ratio counts parked claims among the claims with
                    # no backing; writing off everything except them would be a
                    # different rule from the one the trigger describes.
                    self._parked *= 1.0 - write_spec.rate
                    self._bonds_held *= 1.0 - write_spec.rate
                    self._bond_stock *= 1.0 - write_spec.rate
                    self._total_claims -= destroyed_this_round
                    out["written_off"][t] = destroyed_this_round
                    if trace_writeoff:
                        # ``aimed`` is the held side only, which is the side a
                        # base can shape. The parked share is scaled straight
                        # and no cap applies to it, so it is outside this
                        # measurement by construction rather than by choice.
                        #
                        # **What was taken is measured off the accounts, not
                        # read back from the branch that took it.** The first
                        # version of these lines set the taken amount equal to
                        # the aimed amount on the pro rata path, which made
                        # "pro rata leaves nothing uncollected" true by
                        # construction rather than by measurement, and a
                        # criterion resting on it could not have failed. One
                        # subtraction over the same array serves all three
                        # shapes and none of them gets a branch of its own.
                        held_after = np.maximum(self.holdings, 0.0) * self._alive
                        aimed_held = write_spec.rate * float(held_before.sum())
                        took_held = float(held_before.sum() - held_after.sum())
                        out["writeoff_uncollected"][t] = max(
                            0.0, aimed_held - took_held)
                        out["writeoff_drained"][t] = int(
                            (payers_before & (held_after <= 0.0)).sum())

            # The subsistence floor, read on this round's inflow. Guarded, so a
            # run without a floor never evaluates it.
            sub = cfg.subsistence
            if sub.active and sub.mode == "drawdown":
                # No membership flag moves here. Below the floor is a
                # spending rule and it is re-read every round, so a node
                # whose inflow returns is simply not below it any more.
                inflow_by_node = flow.sum(axis=0)
                if boundary_in is not None:
                    # The pass-down is an in-edge from outside the graph.
                    inflow_by_node = inflow_by_node + boundary_in
                short = inflow_by_node < sub.need
                self._short_for[short] += 1
                self._short_for[~short] = 0
                self._below = self._short_for >= sub.grace
            elif sub.active:
                inflow_by_node = flow.sum(axis=0)
                if boundary_in is not None:
                    inflow_by_node = inflow_by_node + boundary_in
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

            self._t = t
            if cfg.broadcast.from_round and t == cfg.broadcast.from_round:
                # Routing is rebuilt on graph events, so a signal that switches
                # on partway needs one here or it would not be seen until the
                # next cut or rewire.
                self._rebuild_route()
            if (cfg.broadcast.until_round is not None
                    and t == cfg.broadcast.until_round):
                # Same reason on the way out. Without this the routing keeps the
                # tilt after the signal is gone until some other graph event
                # happens to clear it, which would make the tear-down arm read a
                # lag that the model does not contain.
                self._rebuild_route()

            rw = cfg.rewire
            if (rw.active and not cfg.spec.uniform_access
                    and t >= rw.from_round and t % rw.interval == 0):
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
            out["returned"][t] = self._returned_this_round
            if sov_on:
                out["sovereign_pool"][t] = self._sovereign_pool
                out["passed_down"][t] = self._passed_this_round
                out["passed_down_l2"][t] = self._passed_l2_this_round
                out["bond_stock"][t] = self._bond_stock
            if debt_on:
                for key, value in self._debt_round.items():
                    out[key][t] = value
            if levy_on:
                out["levy_out"][t] = self._levy_out_this_round
            if withdraw_on:
                out["withdrawn"][t] = self._withdrawn_this_round
                out["withdrawn_unmet"][t] = self._withdrawn_unmet_this_round
                out["withdrawn_l2"][t] = self._withdrawn_l2_this_round

            if cut_on:
                out["cut_out"][t] = self._cut_out_this_round

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
            # The negative half of the same gap. The line above takes the
            # positive half and drops the rest, which is what makes the rule
            # one-directional; this takes what it dropped, and only when the
            # switch is on, so with it off the line above is the whole rule
            # exactly as it was.
            if withdraw_on:
                self._pending_withdrawal = cfg.withdraw.gain * max(
                    0.0, l2_inflow - self._baseline_active)

            # The hydra clause, after the issuance rule has had its say: what was
            # destroyed is funded again from the layer that is not conserved.
            # Section 14 puts this step last and makes it conditional, which is
            # why it is a switch and sits outside the rule above.
            if destroyed_this_round and cfg.writeoff.refill:
                self._pending_issuance += destroyed_this_round

            self._post_round(t)
            # **The only line added inside the round.** The books for round ``t``
            # are closed and round ``t+1`` has not opened, so a driver that
            # moves claims between two graphs here moves them between two
            # settled states rather than into the middle of one.
            yield t

        self._history = NetworkHistory(
            potential_support=potential,
            node_count=n,
            adjacency=self.adjacency,
            snapshots=snapshots,
            epsilon_absolute=float(epsilon_abs or 0.0),
            **out,
        )
        return


#: Memo for ``autonomous_share``. The quantity is a property of the
#: construction and the construction is deterministic in these five fields, so
#: a repeat is a lookup. It matters because ``scaled_carrier`` solves nine
#: targets by bisection and each step is a graph build: at a thousand nodes one
#: build is about half a second, nine targets at nine steps is about forty five,
#: and that is paid once per process rather than once per grid point.
_AUTONOMOUS_SHARE_MEMO: dict[tuple[int, int, int, int, int], float] = {}


def autonomous_share(config: NetworkConfig) -> float:
    """What share of the intermediate block's opening inflow comes from above.

    ``financial_to_intermediate_edges`` is an edge count, and the quantity it
    stands in for is a **share**. Stage A0b's object was a term of the two-layer
    wage rule: ``W0 (1 - e)``, the part of payroll that does not move with the
    production layer's spending, and above unit elasticity the contractual floor
    that plays the same role, to which the steady-state level is exactly
    proportional. The three-layer graph has no such term, and it carries the
    object over as this share: the part of the intermediary's revenue that comes
    from the financial layer above rather than from the households its own
    payroll pays. It corresponds because it is the part of the payer's funding
    that does not depend on those households, which is what ``W0 (1 - e)`` is in
    A0b. The count and the share are the same parameter only at one graph
    size. At 200 nodes with a core of 20 and a block of 30,
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
    count while the quantity it stands for is the intermediary's opening-inflow
    share from above, this model's counterpart of stage A0b's autonomous wage
    component (``autonomous_share`` says why), and the share is not linear in
    the count. Solved instead, one
    bisection per grid point, so each returned count reproduces its original
    share at the new size.

    Measured, 200 to 1000 nodes: the registered grid
    ``(0, 1, 2, 3, 5, 8, 12, 20, 30)`` becomes ``(0, 2, 5, 8, 15, 28, 45, 72,
    128)``. Each count is the integer whose share is nearest the original, and
    the nearest integer is not always within a thousandth: the first three
    non-zero points land 0.0011, 0.0013 and 0.0012 away, the other five within
    0.0006. Neither
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
    than assuming the target was met. The registered grid's top is within
    reach: 0.3111 at 200 nodes lands on 128 edges at 1000, at 0.3105.
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
