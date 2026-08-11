"""A4: connectivity against four competing explanations of stratification.

What this stage is for
----------------------
Stages A0 and A2 show that a stratified access structure produces stratified
holdings. That is an existence result and it does not yet answer the question a
reader of the inequality literature will ask first, which is why connectivity
should be treated as anything other than one regressor among several.

``docs/a4_causal_primitive.md`` is the pre-registration and it fixes every
switch, outcome measure and threshold. This module implements it and adds
nothing to it. Where the implementation had to decide something the document did
not specify, the decision is recorded in section 9 of that document rather than
here, so that the registered text stays the single place a reader has to check.

The five switches
-----------------
``C``  connectivity. On is the stratified graph of stages A0 and A2. Off is a
       complete graph on which every node reaches every other on identical
       terms, implemented as ``NetworkSpec.uniform_access``.
``I``  inheritance. Holdings transmitted across generations at a retention
       coefficient. Off is equal division, not destruction.
``E``  education. Persistent heterogeneous multipliers on payroll receipts.
``K``  capital returns. Persistent heterogeneous returns on holdings.
``M``  assortative mating. Pairing by similarity in holdings rather than at
       random.

Each competitor acts exogenously
--------------------------------
This is the load-bearing implementation choice and it runs against the project's
own thesis on purpose.

On this framework's account, return heterogeneity is *downstream* of
connectivity: better-connected agents obtain better terms, which is what stage
B2 measured on real mortgages. Implementing ``K`` that way would build the
conclusion into the mechanism, and the resulting amplification ratio would be a
restatement of the code rather than a finding.

So ``E`` and ``K`` are drawn from fixed distributions that never consult the
graph, and ``M`` matches on holdings alone and never sees which layer an agent
belongs to. Each competitor is handed its strongest exogenous form. If
connectivity still amplifies it, the amplification was not put there by
construction.

Households, and why marriage is an average under lockstep
---------------------------------------------------------
Two paired agents pool their holdings and split them evenly at the end of every
round, and they draw a single spending propensity between them. Both keep their
own slot and both keep their own edges.

The pre-registered text ruled out averaging, on the ground that averaging
"would leave two agents holding the same amount while still choosing
separately, which is a transfer rather than a marriage". The lockstep removes
the separate choosing, so the reason survives while the letter changes; the
change is recorded in section 9 of the pre-registration.

Two artefacts are avoided by not literally merging, and both would have been
fatal rather than untidy:

1. A merge into one slot leaves the other slot holding zero. The Gini is
   computed on that vector, so the mere existence of marriage would push it
   toward one half in every cell where ``I`` or ``M`` is on, with no mechanism
   involved. Under lockstep the vector stays strictly positive.
2. A merge has to discard one partner's adjacency row. Marriage would then be
   mechanically reducing connectivity, which puts a term with the same sign as
   ``C`` inside the ``M`` channel and makes ``A(M)`` uninterpretable. Under
   lockstep no edge is touched.

Conservation
------------
Every operation here is a reshuffle. Inheritance conserves the claim total by
construction, the capital-return channel renormalises after applying returns,
and household pooling is an average. So ``economy.py``'s stock-flow assertion
stays live in all thirty-two cells, and any arm that silently created claims
would fail loudly rather than post a favourable Gini.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .network import Network, NetworkConfig, NetworkHistory

#: Orderings of the within-round channels, for pre-registered prediction A4-5.
#: If the finding flips between them it is a finding about the update order.
CHANNEL_ORDERS: tuple[str, ...] = ("capital_first", "pooling_first")

#: Orderings inside the generational event, the second half of A4-5. Under
#: ``inherit_first`` the estate is settled and the next cohort is matched on
#: post-inheritance holdings; under ``match_first`` the cohort is matched on the
#: parental holdings and the estate is settled afterwards. These are not
#: cosmetic variants: the second is matching on family background and the first
#: is matching on realised endowment.
EVENT_ORDERS: tuple[str, ...] = ("inherit_first", "match_first")

#: How often a household settles its internal budget.
#:
#: ``"round"`` follows the pre-registered wording that a household "acts as a
#: single agent from then on", and is the reading with the strongest claim to
#: the registered text.
#:
#: ``"generation"`` pools only when the estate is settled. The distinction is
#: not a detail and it is not a robustness afterthought. Pooling every round
#: makes a household a zero-cost transfer of unbounded bandwidth between two
#: arbitrary nodes, so a household straddling the thermocline is a permanent
#: conduit across it. Measured on the stratified arm, that conduit accounts for
#: roughly ninety-six percent of everything the ``I`` and ``M`` channels do:
#: forcing pairs to form within a layer cuts their effect on the Gini from
#: ``-0.168`` to ``-0.006``. Neither endpoint is privileged, both are run, and
#: the pre-registration's section 9 records that the choice is load-bearing.
POOLING_RULES: tuple[str, ...] = ("round", "generation")


# ---------------------------------------------------------------------------
# Outcome measures
# ---------------------------------------------------------------------------


def gini(holdings: np.ndarray) -> float:
    """Gini coefficient of a non-negative vector.

    The registered outcome measure, chosen because it is what the competing
    literature reports; the diagnostics table in the pre-registration is only
    possible in this unit.

    Computed from the sorted vector as ``(2 Σ i x_i) / (n Σ x_i) − (n + 1) / n``,
    which is exact rather than a numerical approximation of the Lorenz area. An
    all-zero vector returns zero, since a distribution with nothing in it is not
    unequal.
    """
    x = np.sort(np.asarray(holdings, dtype=float))
    if (x < 0).any():
        raise ValueError("Gini is undefined for negative holdings")
    n = x.size
    total = x.sum()
    if n == 0 or total <= 0.0:
        return 0.0
    index = np.arange(1, n + 1, dtype=float)
    return float((2.0 * (index * x).sum()) / (n * total) - (n + 1.0) / n)


def cross_layer_baseline(n: int, layer1_size: int) -> float:
    """Share of pairs spanning the layer boundary under uniform random matching.

    Closed form rather than simulated, so that prediction A4-6 is compared
    against an exact reference instead of against another draw. In a uniformly
    random perfect matching any particular pair is equally likely, so the share
    is ``2 k (n − k) / (n (n − 1))``.
    """
    if n < 2:
        return 0.0
    k = layer1_size
    return float(2.0 * k * (n - k) / (n * (n - 1.0)))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Switches:
    """One cell of the factorial. ``C`` on with the rest off is the A2 control."""

    connectivity: bool = True
    inheritance: bool = False
    education: bool = False
    capital: bool = False
    mating: bool = False

    @property
    def demography_active(self) -> bool:
        """Whether households and generations exist at all.

        With both ``I`` and ``M`` off the demographic layer does not fire. This
        is pinned in the pre-registration and it is not a convenience: random
        pairing followed by pooling followed by an equal split reshuffles
        holdings even with both channels nominally off, which would break the
        bitwise reproduction of stage A2 in the control cell and make the whole
        factorial incomparable to the stage it generalises.
        """
        return self.inheritance or self.mating

    @property
    def competitors_off(self) -> bool:
        return not (
            self.inheritance or self.education or self.capital or self.mating
        )

    @property
    def label(self) -> str:
        flags = "".join(
            letter if on else "-"
            for letter, on in (
                ("C", self.connectivity),
                ("I", self.inheritance),
                ("E", self.education),
                ("K", self.capital),
                ("M", self.mating),
            )
        )
        return flags


@dataclass(frozen=True)
class MechanismParams:
    """Strengths of the four competing channels.

    None of these is calibrated to a real magnitude and the pre-registration is
    explicit that A4 cannot rank the competitors as a result. They are set so
    that each channel clears the strawman floor of prediction A4-3 on its own,
    which is the only property they are required to have.
    """

    #: Log-scale dispersion of the persistent payroll multiplier. Drawn once per
    #: agent per generation, exponentiated, then normalised so the payroll total
    #: is untouched: education redistributes the wage bill, it does not enlarge
    #: it.
    education_sd: float = 0.60

    #: Standard deviation of the persistent per-round return on holdings, in
    #: proportional terms. Drawn once per agent per generation and held fixed
    #: for that lifetime, which is the form the empirical literature on return
    #: heterogeneity reports.
    capital_sd: float = 0.010

    #: Share of a household's holdings passed to its own offspring at the
    #: generational event. The remainder is pooled across the whole cohort. With
    #: ``I`` off this is forced to zero, which is equal division.
    inheritance_retention: float = 0.90

    #: Weight on the holdings rank in the matching key, against a uniform draw.
    #: One is perfectly assortative, zero is uniformly random. With ``M`` off
    #: this is forced to zero.
    assortativity: float = 0.90

    #: Rounds a generation lasts. No criterion depends on it.
    generation_length: int = 40

    def __post_init__(self) -> None:
        if self.education_sd < 0.0:
            raise ValueError("education_sd must be non-negative")
        if self.capital_sd < 0.0:
            raise ValueError("capital_sd must be non-negative")
        if not 0.0 <= self.inheritance_retention <= 1.0:
            raise ValueError("inheritance_retention must lie in [0, 1]")
        if not 0.0 <= self.assortativity <= 1.0:
            raise ValueError("assortativity must lie in [0, 1]")
        if self.generation_length < 1:
            raise ValueError("generation_length must be at least 1")


@dataclass(frozen=True)
class A4Config:
    """Full parameter set for one cell of the factorial, at one seed."""

    switches: Switches = field(default_factory=Switches)
    params: MechanismParams = field(default_factory=MechanismParams)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    channel_order: str = "capital_first"
    event_order: str = "inherit_first"
    pooling: str = "round"

    def __post_init__(self) -> None:
        for name, allowed in (
            ("channel_order", CHANNEL_ORDERS),
            ("event_order", EVENT_ORDERS),
            ("pooling", POOLING_RULES),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ValueError(
                    f"{name} must be one of {allowed}, got {value!r}"
                )

    def resolved_network(self) -> NetworkConfig:
        """The network config with the ``C`` switch applied to its spec."""
        spec = replace(
            self.network.spec, uniform_access=not self.switches.connectivity
        )
        return replace(self.network, spec=spec)


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


@dataclass
class A4Result:
    """One run. ``history`` is the ordinary A2 record, unchanged."""

    switches: Switches
    seed: int
    channel_order: str
    event_order: str
    pooling: str
    history: NetworkHistory
    gini_final: float
    gini_series: np.ndarray
    effective_holders_final: float
    cross_layer_rate: float
    cross_layer_baseline: float
    generational_events: int


class A4Model(Network):
    """Stage A2's network with a demographic layer and four exogenous channels.

    Subclassed rather than reimplemented. Every switch that is off leaves the
    inherited code path untouched, so the control cell reproduces stage A2
    bitwise as a property of the class hierarchy rather than as a claim about
    two files being kept in step.
    """

    def __init__(self, config: A4Config) -> None:
        super().__init__(config.resolved_network())
        self.a4 = config
        p = config.params
        sw = config.switches

        # A separate stream from the one driving spending propensities, so that
        # turning a channel on does not shift the draws of the channels already
        # running. Without this, comparing two cells would confound the switch
        # with a change of random numbers.
        self._mech_rng = np.random.default_rng(config.network.seed + 811_301)

        self._retention = p.inheritance_retention if sw.inheritance else 0.0
        self._assortativity = p.assortativity if sw.mating else 0.0

        #: ``partner[i]`` is the slot ``i`` is paired with, or ``None`` when the
        #: demographic layer is not firing.
        self._partner: np.ndarray | None = None
        self._returns = np.zeros(self._n)
        self._education = np.ones(self._n)

        #: Layer label by slot index, fixed in both arms. The matching rule
        #: never reads it; only the A4-6 measurement does. Holding it to the
        #: index rather than to the graph is what makes the cross-layer rate
        #: comparable between the ``C`` on and ``C`` off arms at all.
        self._is_layer1 = np.zeros(self._n, dtype=bool)
        self._is_layer1[: config.network.spec.layer1_size] = True

        self._cross_layer_events: list[float] = []
        self._generation_length = p.generation_length

        # With no demographic layer there is one cohort and it lasts the whole
        # run, so the persistent traits are drawn once here. With a demographic
        # layer they are drawn at each generational event instead, and drawing
        # them here as well would consume the stream twice for no purpose.
        if not sw.demography_active:
            self._draw_generation_traits()

    # -- channel draws -----------------------------------------------------

    def _draw_generation_traits(self) -> None:
        """Redraw the persistent per-agent traits for a new cohort.

        Persistent within a lifetime and independent across cohorts. Neither
        draw consults the graph, the layer label or the holdings, which is what
        "exogenous" means here and is the reason the amplification ratio is not
        circular.
        """
        if self.a4.switches.education:
            raw = np.exp(
                self._mech_rng.normal(0.0, self.a4.params.education_sd, self._n)
            )
            self._education = raw / raw.mean()
            w = self._education[self._wage_receivers]
            self._wage_weights = w / w.sum()
        if self.a4.switches.capital:
            self._returns = self._mech_rng.normal(
                0.0, self.a4.params.capital_sd, self._n
            )
            np.maximum(self._returns, -0.99, out=self._returns)

    # -- demography --------------------------------------------------------

    def _inherit(self) -> None:
        """Dissolve households into offspring and settle the estate.

        Under lockstep the two members of a household already hold equal halves
        of it, so dissolution is a matter of who keeps what rather than of
        rearranging slots. Each offspring keeps ``retention`` of its own half
        and the rest is pooled across the whole cohort and divided equally.
        ``retention = 0`` is exactly equal division, which is what ``I`` off
        means, and the total is conserved at either end of the range.
        """
        total = float(self.holdings.sum())
        kept = self.holdings * self._retention
        pooled = total - float(kept.sum())
        self.holdings = kept + pooled / self._n

    def _rematch(self) -> None:
        """Pair every slot into households of two.

        The key mixes the normalised holdings rank with a uniform draw. Weight
        one is perfectly assortative, weight zero is uniformly random, and the
        rule reads holdings and nothing else. It has no access to
        ``self._is_layer1``, so any tendency of households to form within a
        layer is derived rather than imposed, which is the whole content of
        prediction A4-6.
        """
        n = self._n
        # Ties in holdings are broken at random, never by slot index. This is
        # not tidiness. In the ``C = 0`` arm every agent holds the same amount
        # by construction, so a stable sort would rank them in index order, the
        # matching key would become the index, adjacent slots would pair, and
        # the cross-layer rate would fall to roughly one over the financial
        # layer's size. That number would be a property of the sort routine
        # presented as a property of assortative mating, which is the same class
        # of error as the ``0.975`` incident recorded in ``PROJECT_PLAN.md`` section
        # 7.2, and it would corrupt precisely the arm prediction A4-6 uses as
        # its reference.
        tiebreak = self._mech_rng.random(n)
        order = np.lexsort((tiebreak, self.holdings))
        rank = np.empty(n)
        rank[order] = np.arange(n, dtype=float) / max(n - 1, 1)
        noise = self._mech_rng.random(n)
        a = self._assortativity
        key = a * rank + (1.0 - a) * noise
        seating = np.argsort(key, kind="stable")

        partner = np.empty(n, dtype=int)
        left, right = seating[0::2], seating[1::2]
        partner[left] = right
        partner[right] = left
        self._partner = partner

        crossed = self._is_layer1[left] != self._is_layer1[right]
        self._cross_layer_events.append(float(crossed.mean()))

    def _pool_households(self) -> None:
        """Settle the household budget: pool and split evenly.

        Conserves the total exactly. This is the operation that makes the pair a
        single budget constraint rather than two agents who happen to hold the
        same amount.
        """
        if self._partner is None:
            return
        self.holdings = 0.5 * (self.holdings + self.holdings[self._partner])

    def _apply_returns(self) -> None:
        """Apply persistent heterogeneous returns as a pure reshuffle.

        Returns are applied and the vector is then renormalised to the total it
        had before. Claims are therefore redistributed toward high-return agents
        without any being created, so the stock-flow assertion stays live in
        this arm exactly as in every other. A channel that created claims would
        raise the Gini partly by inflating the top rather than by concentrating
        a fixed stock, and the two are not the same finding.
        """
        total = float(self.holdings.sum())
        if total <= 0.0:
            return
        grown = np.maximum(self.holdings, 0.0) * (1.0 + self._returns)
        scale = float(grown.sum())
        if scale <= 0.0:
            return
        self.holdings = grown * (total / scale)

    # -- hooks -------------------------------------------------------------

    def _pre_round(self, t: int) -> None:
        if not self.a4.switches.demography_active:
            return
        if t % self._generation_length:
            return
        if self.a4.event_order == "inherit_first":
            if t:
                self._inherit()
            self._draw_generation_traits()
            self._rematch()
        else:
            # Matching on the parents' holdings, before the estate is settled.
            self._rematch()
            self._draw_generation_traits()
            if t:
                self._inherit()
        # A household always opens its books on the round it is formed,
        # whichever pooling rule is in force.
        self._pool_households()

    def _post_round(self, t: int) -> None:
        sw = self.a4.switches
        capital = sw.capital
        pooling = sw.demography_active and self.a4.pooling == "round"
        if self.a4.channel_order == "capital_first":
            if capital:
                self._apply_returns()
            if pooling:
                self._pool_households()
        else:
            if pooling:
                self._pool_households()
            if capital:
                self._apply_returns()

    # -- flows -------------------------------------------------------------

    def _discretionary_flow(self) -> np.ndarray:
        """As stage A2, except that a household draws one propensity between it.

        The four lines after the draw are copied from the base class rather than
        delegated, because the only thing that changes is the propensity vector
        and delegating would mean drawing it twice. When no households exist the
        base implementation is called, so the control cell does not run this
        code at all.
        """
        if self._partner is None:
            return super()._discretionary_flow()
        propensity = self.rng.uniform(self._p_low, self._p_high)
        leads = self._partner > np.arange(self._n)
        propensity = np.where(leads, propensity, propensity[self._partner])
        spent = propensity * np.maximum(self.holdings, 0.0) * self._has_out
        matrix = spent[:, None] * self._route
        self.holdings = self.holdings - spent + matrix.sum(axis=0)
        return matrix


def run_a4(config: A4Config) -> A4Result:
    """Run one cell at one seed and package the registered measures."""
    model = A4Model(config)
    history = model.run()
    holdings = np.asarray(history.holdings)
    series = np.array([gini(row) for row in holdings])
    final = holdings[-1]
    events = model._cross_layer_events
    return A4Result(
        switches=config.switches,
        seed=config.network.seed,
        channel_order=config.channel_order,
        event_order=config.event_order,
        pooling=config.pooling,
        history=history,
        gini_final=float(series[-1]),
        gini_series=series,
        effective_holders_final=float(
            1.0 / np.square(final / final.sum()).sum() if final.sum() > 0 else 0.0
        ),
        cross_layer_rate=float(np.mean(events)) if events else float("nan"),
        cross_layer_baseline=cross_layer_baseline(
            model._n, config.network.spec.layer1_size
        ),
        generational_events=len(events),
    )


def cell_configs(
    switches: Switches,
    *,
    seeds: range,
    base: NetworkConfig | None = None,
    params: MechanismParams | None = None,
    channel_order: str = "capital_first",
    event_order: str = "inherit_first",
    pooling: str = "round",
) -> list[A4Config]:
    """One config per seed for a given cell of the factorial.

    The graph seed and the run seed move together, so a replication varies the
    graph as well as the draws. Holding the graph fixed would make the reported
    spread a statement about one graph.
    """
    base = base or NetworkConfig()
    params = params or MechanismParams()
    out = []
    for s in seeds:
        net = replace(base, seed=s, spec=replace(base.spec, seed=s))
        out.append(
            A4Config(
                switches=switches,
                params=params,
                network=net,
                channel_order=channel_order,
                event_order=event_order,
                pooling=pooling,
            )
        )
    return out
