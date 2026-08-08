"""Configuration objects for the A0 retention-and-allocation model.

Every parameter that affects a published figure is declared here, so a reader
can audit the full parameter set without reading the simulation loop.

Design rule (PROJECT_PLAN.md 6.1): parameters are explicit and immutable. No
default may silently propagate between experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Stratification
# ---------------------------------------------------------------------------
# The source specifies three strata holding 30% each: 40 agents at the 50th-90th
# percentile (0.75 each), 10 agents (3.0 each), and 1 agent (30.0). Those three
# sum to 90% of wealth and 51 of 100 agents. The residual -- 49 agents holding
# 10% -- is left implicit. We make it explicit rather than dropping it: a bottom
# stratum with near-zero holdings is where the death-zone criterion bites
# hardest, and omitting it would flatter the result.
#
# Per-capita initial holdings under this completion:
#   bottom49 : 10 / 49 = 0.204
#   middle40 : 30 / 40 = 0.750  <- matches source
#   upper10  : 30 / 10 = 3.000  <- matches source
#   top1     : 30 / 1  = 30.00  <- matches source

STRATUM_NAMES: tuple[str, ...] = ("bottom49", "middle40", "upper10", "top1")

# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------
# The thermocline runs between strata, not around each stratum. The source's
# two-layer structure is a financial layer with fast, self-referential internal
# circulation, and a production layer that generates real output. Distinguishing
# these from the four strata matters for measurement: a transfer from top1 to
# upper10 crosses a stratum boundary but stays inside Layer 1, and for every
# node in Layer 2 it is indistinguishable from no transfer at all.

#: Financial layer.
LAYER_1: tuple[int, ...] = (2, 3)
#: Production layer. Wages, mortgages, basic consumption.
LAYER_2: tuple[int, ...] = (0, 1)

#: Stratum receiving new money. The source injects at the top, and that agent
#: decides how much to retain and how much to pass down.
INJECTION_STRATUM = 3


@dataclass(frozen=True)
class Strata:
    """Population structure and initial claim distribution."""

    counts: tuple[int, ...] = (49, 40, 10, 1)
    wealth_share: tuple[float, ...] = (0.10, 0.30, 0.30, 0.30)

    def __post_init__(self) -> None:
        if len(self.counts) != len(self.wealth_share):
            raise ValueError("counts and wealth_share must have equal length")
        if sum(self.counts) != 100:
            raise ValueError(f"counts must sum to 100 agents, got {sum(self.counts)}")
        if not np.isclose(sum(self.wealth_share), 1.0):
            raise ValueError(
                f"wealth_share must sum to 1.0, got {sum(self.wealth_share)}"
            )

    @property
    def n_strata(self) -> int:
        return len(self.counts)


@dataclass(frozen=True)
class SpendRule:
    """Per-round spending as a propensity: the share of holdings put back out.

    Propensities rather than absolute amounts. The source states absolute
    figures, but those figures encode propensities: the middle stratum spends
    0.65-0.75 out of holdings of 0.75, which is the source's "spends nearly
    everything, keeping a minimal emergency reserve". Stated absolutely, a
    stratum whose income exceeds its fixed spending cap accumulates without
    bound, which is an artefact of the parameterisation rather than a mechanism.

    Propensities also make the retention rate directly readable. The source is
    explicit that the retention rate should not be read as a hoarding rate but
    as the rate of exit from cross-layer circulation, and here that is exactly
    ``1 - propensity``.

    Defaults, recovered from the source's absolute figures at t=0:

    ======== ============ ================= ==========
    stratum  holdings     spend             propensity
    ======== ============ ================= ==========
    bottom49 10.0         8.82-10.00        0.88-1.00
    middle40 30.0         26.0-30.0         0.87-1.00
    upper10  30.0         15.0              0.50
    top1     30.0         15.0              0.50
    ======== ============ ================= ==========

    Implied retention rates are (0.06, 0.13, 0.50, 0.50). The source's ordering
    (top >= middle >= bottom) holds, with a tie between the top two strata: the
    source's own worked example gives both a propensity of exactly one half. We
    keep the tie rather than breaking it to preserve a strict inequality.
    """

    low: tuple[float, ...] = (0.88, 0.87, 0.50, 0.50)
    high: tuple[float, ...] = (1.00, 1.00, 0.50, 0.50)

    def __post_init__(self) -> None:
        if len(self.low) != len(self.high):
            raise ValueError("low and high must have equal length")
        if any(a > b for a, b in zip(self.low, self.high, strict=True)):
            raise ValueError("each low must be <= corresponding high")
        if any(x < 0.0 for x in self.low) or any(x > 1.0 for x in self.high):
            raise ValueError("propensities must lie in [0, 1]")

    @property
    def retention_rate(self) -> tuple[float, ...]:
        """The rate of exit from cross-layer circulation, per stratum."""
        return tuple(
            1.0 - 0.5 * (a + b) for a, b in zip(self.low, self.high, strict=True)
        )

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        low = np.asarray(self.low, dtype=float)
        high = np.asarray(self.high, dtype=float)
        return rng.uniform(low, high)

    def with_top_propensity(self, value: float) -> SpendRule:
        """Copy with the top stratum's propensity fixed at ``value``.

        Used by the discretionary-spending sweep.
        """
        low, high = list(self.low), list(self.high)
        low[-1] = high[-1] = value
        return SpendRule(low=tuple(low), high=tuple(high))


@dataclass(frozen=True)
class Adjacency:
    """Who can transact with whom.

    ``flow[i, j]`` is the share of stratum ``i``'s discretionary spending that
    arrives as income in stratum ``j``. Rows sum to 1.

    This object is the load-bearing assumption of the model. The source's
    methodological conclusion is that a quantity of money does not establish a
    death zone: one must specify who can trade with whom. So this matrix is
    stated separately from the spending rule and swept independently.

    The default encodes two asymmetries:

    1. **Upward leakage.** Layer 2 routes a large share of spending upward as
       rent, mortgage interest, tax and financing costs.
    2. **No downward discretionary edge.** Layer 1's discretionary spending
       cannot land in Layer 2 at all. This is the source's specification, stated
       flatly: between the bottom stratum and the top there is no edge except a
       single controlled channel, employment. Employment is modelled separately
       (see ``WageChannel``) precisely because it is set by hiring decisions
       rather than by how much the top chooses to consume. Collapsing the two
       would smuggle the conclusion of the spending sweep into its premise.

    A reader who thinks the zero entries are too strong should not argue about
    it: ``with_downward_edge`` opens them, and the experiment reports what
    happens. That comparison is the point of the stage.
    """

    flow: tuple[tuple[float, ...], ...] = (
        # ->bottom49  middle40  upper10  top1
        (0.35, 0.25, 0.10, 0.30),  # bottom49 spends
        (0.20, 0.35, 0.15, 0.30),  # middle40 spends
        (0.00, 0.00, 0.45, 0.55),  # upper10  spends: stays in Layer 1
        (0.00, 0.00, 0.10, 0.90),  # top1     spends: stays in Layer 1
    )

    def __post_init__(self) -> None:
        m = self.as_array()
        if m.shape[0] != m.shape[1]:
            raise ValueError("flow matrix must be square")
        if (m < 0).any():
            raise ValueError("flow matrix must be non-negative")
        row_sums = m.sum(axis=1)
        if not np.allclose(row_sums, 1.0):
            raise ValueError(f"flow matrix rows must sum to 1.0, got {row_sums}")

    def as_array(self) -> np.ndarray:
        return np.asarray(self.flow, dtype=float)

    def upward_leakage(self) -> float:
        """Share of Layer 2 spending that terminates in Layer 1.

        Averaged over Layer 2 strata. Together with the net downward wage flow
        this gives the model's version of the death-zone criterion: a layer
        whose inflow falls short of its outflow is drained round by round.
        """
        m = self.as_array()
        return float(m[np.ix_(LAYER_2, LAYER_1)].sum(axis=1).mean())

    def with_downward_edge(self, weight: float) -> Adjacency:
        """Copy where the top stratum routes ``weight`` of its discretionary
        spending into Layer 2, taken out of its intra-layer share.

        This is the topology sweep, the counterpart to
        ``SpendRule.with_top_propensity``: one varies how much the top spends,
        the other varies where that spending is allowed to land.
        """
        m = self.as_array()
        top = m.shape[0] - 1
        intra = m[top, top]
        if not 0.0 <= weight <= intra:
            raise ValueError(
                f"weight must lie in [0, {intra}] (available intra-layer share)"
            )
        m[top, top] = intra - weight
        sizes = np.array([49.0, 40.0])
        for idx, share in zip(LAYER_2, sizes / sizes.sum(), strict=True):
            m[top, idx] += weight * share
        return Adjacency(flow=tuple(tuple(row) for row in m))


@dataclass(frozen=True)
class WageChannel:
    """The thin, controlled connection running downward.

    The source describes the layers as joined by very few edges, nearly all
    owned by the upper layer, with employment the only one that moves claims
    down. It is modelled separately from discretionary spending because it is
    set by hiring rather than by consumption.

    ``bill`` is the per-round flow at t=0, ``source_shares`` how it is financed,
    ``dest_shares`` where it lands.

    Derived demand
    --------------
    ``elasticity`` is the load-bearing addition at this stage. The source's own
    claim is that investment demand is ultimately derived from consumption in
    the production layer, so employment cannot be exogenous: when the production
    layer's spending falls, hiring falls with it, which cuts the production
    layer's income further. The rule is

    .. math::

        W_t = W_0 \\left[(1 - e) + e \\cdot S_{t-1} / S_0 \\right]

    with :math:`S_t` the production layer's spending and :math:`e` the
    elasticity, floored at ``floor_share`` of the baseline to represent whatever
    part of payroll is contractually rigid within a period.

    ``e = 0`` recovers a constant bill exactly, which is the stage's original
    specification and its no-feedback control.

    ``e > 1`` is admissible and not merely a robustness range. Employment adjusts
    in lumps: firms cut headcount and hours together, and both the source's
    account and the standard derived-demand argument imply that a fall in final
    demand is amplified rather than damped on the way into the labour bill. The
    sweep therefore extends past unity, and where the boundary falls is the
    result rather than an assumption.

    The default bill leaves the net downward flow short of Layer 2's upward
    leakage. That shortfall is the death-zone criterion, and it is a parameter
    rather than a result: the stage traces what follows from it and does not
    claim to derive it. ``EconomyConfig.flow_balance`` reports the ratio.
    """

    bill: float = 8.0
    elasticity: float = 0.0
    floor_share: float = 0.0
    source_shares: tuple[float, ...] = (0.00, 0.10, 0.30, 0.60)
    dest_shares: tuple[float, ...] = (0.45, 0.55, 0.00, 0.00)

    def __post_init__(self) -> None:
        for name, shares in (
            ("source_shares", self.source_shares),
            ("dest_shares", self.dest_shares),
        ):
            if not np.isclose(sum(shares), 1.0):
                raise ValueError(f"{name} must sum to 1.0, got {sum(shares)}")
            if any(x < 0.0 for x in shares):
                raise ValueError(f"{name} must be non-negative")
        if self.bill < 0:
            raise ValueError("wage bill must be non-negative")
        if self.elasticity < 0:
            raise ValueError("elasticity must be non-negative")
        if not 0.0 <= self.floor_share <= 1.0:
            raise ValueError("floor_share must lie in [0, 1]")

    def bill_at(self, demand: float, baseline_demand: float) -> float:
        """The wage bill given last round's Layer 2 spending.

        ``demand`` is last round's spending, ``baseline_demand`` the reference
        level at t=0. With ``elasticity == 0`` the baseline is never consulted,
        so the constant-bill case is exact rather than approximate.
        """
        if self.elasticity == 0.0:
            return self.bill
        if baseline_demand <= 0.0:
            return self.bill
        ratio = demand / baseline_demand
        scaled = self.bill * ((1.0 - self.elasticity) + self.elasticity * ratio)
        return float(max(self.bill * self.floor_share, scaled))

    def with_elasticity(self, value: float) -> WageChannel:
        """Copy with a different derived-demand elasticity."""
        return WageChannel(
            bill=self.bill,
            elasticity=value,
            floor_share=self.floor_share,
            source_shares=self.source_shares,
            dest_shares=self.dest_shares,
        )

    def net_downward(self, bill: float | None = None) -> float:
        """Wage flow crossing from Layer 1 into Layer 2.

        Uses the baseline bill unless one is supplied.
        """
        src = np.asarray(self.source_shares)
        dst = np.asarray(self.dest_shares)
        level = self.bill if bill is None else bill
        return float(level * src[list(LAYER_1)].sum() * dst[list(LAYER_2)].sum())


@dataclass(frozen=True)
class MonetaryAuthority:
    """Issuance rule.

    ``"endogenous"``
        The authority observes the active-claim-to-active-resource ratio and
        issues enough to restore it to baseline. This is the source's
        mechanism: the target is pinned to the active pools, so claims that have
        left cross-layer circulation lie outside the instrument's field of view.

    ``"fixed"``
        Constant issuance per round, reproducing the source's worked example.

    ``"none"``
        No issuance. Baseline for isolating retention alone.
    """

    rule: str = "endogenous"
    fixed_amount: float = 10.0
    gain: float = 1.0

    def __post_init__(self) -> None:
        if self.rule not in {"endogenous", "fixed", "none"}:
            raise ValueError(f"unknown issuance rule: {self.rule}")
        if not 0.0 < self.gain <= 1.0:
            raise ValueError("gain must lie in (0, 1]")


@dataclass(frozen=True)
class EconomyConfig:
    """Full parameter set for one run."""

    strata: Strata = field(default_factory=Strata)
    spend: SpendRule = field(default_factory=SpendRule)
    adjacency: Adjacency = field(default_factory=Adjacency)
    wages: WageChannel = field(default_factory=WageChannel)
    authority: MonetaryAuthority = field(default_factory=MonetaryAuthority)

    #: Total claims at t=0. Claims and resources start one to one.
    initial_claims: float = 100.0
    #: Total real resources. Closed economy, no real growth by default.
    total_resources: float = 100.0
    #: Share of resources withheld from market each round (the dormant resource
    #: pool). Zero here so A0 isolates the claim side.
    resource_withholding: float = 0.0

    rounds: int = 300
    seed: int = 0

    def __post_init__(self) -> None:
        n = self.strata.n_strata
        if self.adjacency.as_array().shape[0] != n:
            raise ValueError("adjacency matrix does not match number of strata")
        if len(self.spend.low) != n:
            raise ValueError("spend rule does not match number of strata")
        if len(self.wages.source_shares) != n:
            raise ValueError("wage channel does not match number of strata")
        if not 0.0 <= self.resource_withholding < 1.0:
            raise ValueError("resource_withholding must lie in [0, 1)")
        if self.rounds < 1:
            raise ValueError("rounds must be >= 1")

    def flow_balance(self) -> float:
        """Layer 2 outflow rate divided by its downward inflow, at t=0.

        Above 1 means Layer 2 is drained round by round. This is the death-zone
        criterion expressed in the model's own parameters.
        """
        shares = np.asarray(self.strata.wealth_share)
        layer2_claims = float(shares[list(LAYER_2)].sum() * self.initial_claims)
        propensity = float(
            np.mean([0.5 * (self.spend.low[i] + self.spend.high[i]) for i in LAYER_2])
        )
        outflow = layer2_claims * propensity * self.adjacency.upward_leakage()
        inflow = self.wages.net_downward()
        return float("inf") if inflow == 0 else outflow / inflow
