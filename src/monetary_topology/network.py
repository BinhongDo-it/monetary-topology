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

#: A second fresh stream, so the placebo's choice of targets cannot correlate
#: with which pairs the uniform arm happened to draw.
_PREFERENTIAL_OFFSET = 31_337

#: Where newly issued claims are credited. ``PROJECT_PLAN.md`` §16.2 registers
#: both arms as the two readings of the source's own claim that money is
#: non-neutral because the path and the injection point decide everything. Only
#: the first was ever implemented.
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
        if spec.shortcut_mode == "uniform":
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

        # Injection at the most central financial node, where new money enters in
        # the block model.
        in_degree = self.adjacency.sum(axis=0)
        self.injection_node = int(self._l1[np.argmax(in_degree[self._l1])])

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

        per_payer = bill / self._wage_payers.size
        paid = np.minimum(per_payer, np.maximum(self.holdings[self._wage_payers], 0.0))
        total = float(paid.sum())
        self._last_bill_owed = bill
        self._last_bill_paid = total
        if total <= 0.0:
            return matrix, 0.0

        if self._wage_weights is None:
            share = total / self._wage_receivers.size
            for idx, payer in enumerate(self._wage_payers):
                if paid[idx] <= 0:
                    continue
                portion = paid[idx] / self._wage_receivers.size
                matrix[payer, self._wage_receivers] += portion
            self.holdings[self._wage_payers] -= paid
            self.holdings[self._wage_receivers] += share
        else:
            w = self._wage_weights
            for idx, payer in enumerate(self._wage_payers):
                if paid[idx] <= 0:
                    continue
                matrix[payer, self._wage_receivers] += paid[idx] * w
            self.holdings[self._wage_payers] -= paid
            self.holdings[self._wage_receivers] += total * w
        return matrix, bill

    def _discretionary_flow(self) -> np.ndarray:
        propensity = self.rng.uniform(self._p_low, self._p_high)
        spent = propensity * np.maximum(self.holdings, 0.0) * self._has_out
        matrix = spent[:, None] * self._route
        self.holdings = self.holdings - spent + matrix.sum(axis=0)
        return matrix

    # -- hooks -------------------------------------------------------------
    #
    # Two no-ops, so that stage A4 can add demography and the competing
    # mechanisms without a second copy of the round loop. A second copy would
    # make the bitwise reproduction of A2 a claim about two files staying in
    # step, which is not a claim anyone can check by reading either one.

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
        }

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

            before = float(self.holdings.sum())
            wage_matrix, _ = self._wage_flow()
            spend_matrix = self._discretionary_flow()
            flow = wage_matrix + spend_matrix
            after = float(self.holdings.sum())
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
            out["holdings"][t] = self.holdings

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

            self._post_round(t)

        return NetworkHistory(
            potential_support=potential,
            node_count=n,
            adjacency=self.adjacency,
            snapshots=snapshots,
            epsilon_absolute=float(epsilon_abs or 0.0),
            **out,
        )


def run_network(config: NetworkConfig) -> NetworkHistory:
    return Network(config).run()
