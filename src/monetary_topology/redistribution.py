"""A6: pricing the siphon in redistribution, and asking which edges are cheaper.

Registered in ``docs/a6_siphon_cost.md``.

What this adds to stage A2 is a fiscal channel and nothing else. No asset, no
price, no tiers: A6 does not depend on stages A3 or A5 and does not use their
machinery.

The two arms, and why both are topological
------------------------------------------
Redistribution is an **edge**. It runs from the top of the graph to the bottom
and it was not there before, so both arms are interventions on the graph and
neither is "quantity against topology". The question is *which* edges.

``transfer``
    Adds a downward edge. The levy is paid out equally per head across the
    production layer. The claims arrive and then leak back upward along the
    existing edges at the rate those edges always had.

``infrastructure``
    Attenuates the upward edges. The levy is paid to the production layer as
    payment for building, so claims move exactly as in the transfer arm and
    conservation is identical, but the building **permanently reduces the share
    of production-layer spending that terminates in the financial layer**.

Infrastructure is not anybody's wealth and is not added to any holdings. What it
does is make ordinary households need to spend less, and it does so for ordinary
households rather than for the very rich, which is what licenses treating it as
common property in the accounts rather than as somebody's asset.

So the transfer arm has to keep paying and the infrastructure arm does not. If
the second holds the support set open at a lower rate, the framework's thesis
has a form a finance ministry could act on: **where you put the edge matters
more than how much you push through it.**

Who pays, and why that is a switch rather than a fact
-----------------------------------------------------
Two different things were riding on one word in section 3's phrase "on the
financial layer only", and only one of them belongs to the framework.

**Layer as position** is which edges a node has. It is assigned at construction,
it fixes the graph, the propensities, the payroll payers, the injection point
and the opening allocation, and it does not move: a household does not become a
bank by getting rich. That is the framework's own object and :class:`LevySpec`
does not touch it.

**The levy base** is a policy instrument, and a real tax is assessed on a
measured quantity rather than on a category. Every net wealth tax in force,
Norwegian, Swiss, Spanish, and the French ISF before 2018, recomputes liability
from an annual stock, so the set of payers changes as the distribution does, and
their bases grow rather than drain. :data:`LEVY_BASES` makes that a switch:

``layer``
    The twenty node indices assigned to the financial layer at construction,
    whatever they hold. **The default**, so every result recorded before this
    existed is reproduced exactly, and criterion A6-7 checks that bit for bit.
    Its distinguishing property is that it can be **drained to zero**, after
    which the levy collects nothing forever.

``threshold``
    The excess above ``θ``, for every node, recomputed each round. Since
    ``Σ(h − mean) = 0``, a threshold at one mean makes the base
    ``(n/2) ×`` the mean absolute deviation of holdings, so it is exactly zero
    on a flat distribution and **grows as the economy concentrates**. It cannot
    die by concentration, because concentration is what feeds it.

The two agree at the open and separate as soon as the distribution moves, and in
two of the five registered seeds they already disagree at round zero: opening
claims are spread within each layer in proportion to in-degree, so a badly
connected financial node opens poorer than a well connected production one.
Section 15 records what the difference measures.

What is measured, and what is deliberately not
----------------------------------------------
``R*`` is the smallest levy rate at which the **support set stops contracting**.
That is stage A2's threshold-free ``1 / HHI`` and it is the only stationarity
condition.

The **Palma ratio** is reported and is not a criterion. A closed economy
guarantees that no new money is needed; it does not guarantee where the money
sits. Palma is used rather than the Gini because on two hundred nodes split
twenty to one hundred and eighty the top decile *is* the financial layer, so the
statistic reads off the model's own structure instead of being imported over it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np

from .config import MonetaryAuthority
from .network import Network, NetworkConfig

#: Where the levy goes and what it does when it gets there.
CHANNELS: tuple[str, ...] = ("transfer", "infrastructure")


@dataclass(frozen=True)
class FiscalSpec:
    """The fiscal channel. Values are those registered in section 8."""

    #: ``R``. Share of financial-layer holdings levied each round. Zero is the
    #: control and leaves the inherited dynamics untouched.
    rate: float = 0.0

    #: Which arm.
    channel: str = "transfer"

    #: Whether the transfer travels as an edge in the round's flow matrix, or
    #: as a direct adjustment to holdings.
    #:
    #: **False is the original behaviour** and is what every record before
    #: 2026-08-23 was produced under. Under it the levy and the payout never
    #: appear in the flow, so anything read off the flow does not see them:
    #: ``effective_support`` does not, and neither does a subsistence floor that
    #: watches inflow. Claims still move and conservation still holds; what is
    #: missing is the edge.
    #:
    #: The module's own opening line calls the transfer arm "a downward edge",
    #: so False is a gap between that description and the arithmetic. True
    #: closes it. It is a switch rather than a correction because closing it
    #: changes every flow-derived reading, and the records taken under False are
    #: not wrong about what they measured.
    as_edge: bool = False

    #: ``ι``. Upward leakage removed per unit of cumulative investment, in units
    #: of the opening claim stock. At one, a cumulative investment equal to the
    #: opening stock removes the whole of the production layer's upward leakage.
    leak_response: float = 1.0

    #: One propensity for every node, at the claim-weighted mean of the two
    #: layers'. The same construction stage A4 uses when it flattens access, but
    #: as a switch of its own, so that retention and access move independently.
    #: Stage A4 could not separate them because there they were deliberately one
    #: object.
    fair_retention: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate < 1.0:
            raise ValueError("rate must lie in [0, 1)")
        if self.channel not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        if self.leak_response < 0.0:
            raise ValueError("leak_response must be non-negative")


def _g_clip(x: float) -> float:
    """Today's wall: constant marginal effect into a ceiling, then flat.

    Not a diminishing return. It is what section 12.5 records the code as
    having, and it is the shape the reduction guard runs under.
    """
    return min(1.0, x)


def _g_exp(x: float) -> float:
    """``1 - e**-x``. Concave, bounded by one, slope one at the origin."""
    return -math.expm1(-x)


def _g_hill(x: float) -> float:
    """``x / (1 + x)``. Same bound and slope at the origin, heavier tail."""
    return x / (1.0 + x)


#: The registered shapes of ``g``. ``clip`` reproduces the wall and exists so
#: that the reduction guard has something to reduce to; ``exp`` is the
#: registered default and ``hill`` the robustness axis. Both smooth shapes have
#: ``g'(0) = 1``, which is the wall's slope, so the first tax point buys the
#: same thing under all three and they separate only near saturation.
SHAPES: dict[str, Callable[[float], float]] = {
    "clip": _g_clip,
    "exp": _g_exp,
    "hill": _g_hill,
}


#: Who the levy is assessed on. ``layer`` is a fixed set of node indices fixed
#: at construction; ``threshold`` is every node holding more than a threshold,
#: recomputed each round.
LEVY_BASES: tuple[str, ...] = ("layer", "threshold")


@dataclass(frozen=True)
class LevySpec:
    """Who pays. Registered in section 15.

    ``layer`` is what stage A6 has always done: the levy falls on the twenty
    node indices assigned to the financial layer at construction, and it falls
    on them whatever they hold and whoever else has become rich. **No real net
    wealth tax works that way.** Norway, Switzerland, Spain and France all
    assess liability on a measured stock recomputed every year, so the set of
    payers changes as the distribution does.

    ``threshold`` is that shape: the levy falls on **the excess above** a
    threshold, for every node, recomputed each round. Norway taxes what is
    above NOK 1.9m, not the whole holding of everyone above it, and this
    follows that.

    The default is ``layer``, so nothing that ran before this existed moves,
    and criterion A6-7 keeps reducing the ratchet to the object that produced
    section 9.2.
    """

    base: str = "layer"

    #: ``θ``, as a multiple of the mean holding, which is the claim stock over
    #: the node count. Registered at ``1.0``: it catches twenty-one to
    #: twenty-five of two hundred nodes at the open, which is ten and a half to
    #: twelve and a half percent, against the roughly twelve percent of the
    #: population Norway's threshold catches.
    #:
    #: Written as a multiple rather than as an absolute number so that it is
    #: scale-free and would index itself if issuance were ever turned on. In
    #: stage A6 issuance is off in every cell, so the claim stock is conserved
    #: and this is a constant.
    threshold_multiple: float = 1.0

    def __post_init__(self) -> None:
        if self.base not in LEVY_BASES:
            raise ValueError(f"base must be one of {LEVY_BASES}")
        if self.threshold_multiple < 0.0:
            raise ValueError("threshold_multiple must be non-negative")

    @property
    def is_reduction(self) -> bool:
        """Is this the base ``A6Model`` already implements?"""
        return self.base == "layer"


#: Who the rebate is paid to. ``layer`` is the set of node indices assigned to
#: the production layer at construction; ``threshold`` is every node holding
#: **less** than the same threshold the levy is assessed above, recomputed each
#: round.
REBATE_BASES: tuple[str, ...] = ("layer", "threshold")


@dataclass(frozen=True)
class RebateSpec:
    """Who receives. Registered in section 18.

    **:class:`LevySpec` corrected one side of a two-sided instrument.** The
    other side sat three lines further down in ``_post_round`` and was not
    looked at, so under the threshold base the payers are recomputed from
    measured holdings every round while the recipients stay the hundred and
    eighty node indices assigned to the production layer at construction. Over
    twenty thousand rounds at the registered infrastructure cell that leaves
    **fifty-six of the hundred and eighty recipients also paying**, and **four
    financial-layer nodes below the threshold paying nothing and receiving
    nothing**. Section 15's own argument, that liability belongs on a measured
    stock, says the same thing about eligibility.

    ``threshold`` applies it: pay the nodes **below** the same ``θ`` the levy is
    assessed above, in equal shares.

    **Equal shares rather than in proportion to the shortfall, deliberately.**
    The existing rebate is an equal split. Changing the membership and the
    split rule in one step would move two things at once, which
    ``MEASUREMENT.md``'s stratification rule forbids, and the resulting arm
    could not say which of the two did the work. A shortfall-weighted rebate is
    a separate arm and is not written here.

    **``θ`` is the levy's, not a second number.** One instrument, one
    threshold: taxed above it, paid below it. A rebate threshold free to differ
    from the levy's would be a second free parameter and the first thing anyone
    would tune.

    The default is ``layer``, so nothing that ran before this existed moves and
    criterion A6-7 keeps reducing the ratchet to the object that produced
    section 9.2.
    """

    base: str = "layer"

    def __post_init__(self) -> None:
        if self.base not in REBATE_BASES:
            raise ValueError(f"base must be one of {REBATE_BASES}")

    @property
    def is_reduction(self) -> bool:
        """Is this the destination ``A6Model`` already implements?"""
        return self.base == "layer"


@dataclass(frozen=True)
class RatchetSpec:
    """The frontier ratchet. Registered in section 13.2.

    The defaults are the reduction point: an ``A6RatchetModel`` built with a
    default spec must be bit-identical to ``A6Model``, which is criterion A6-7.
    """

    #: ``λ``. Rate at which the absorbed baseline chases the built stock. Zero
    #: freezes the baseline at zero and is the reduction point.
    absorption: float = 0.0

    #: ``δ``. Proportional decay on the built stock. Registered default zero:
    #: physical stock does wear out, but most of the loss is relative, so this
    #: is a robustness axis and never a headline.
    decay: float = 0.0

    #: ``g``. One of :data:`SHAPES`.
    shape: str = "clip"

    def __post_init__(self) -> None:
        if not 0.0 <= self.absorption <= 1.0:
            raise ValueError("absorption must lie in [0, 1]")
        if not 0.0 <= self.decay < 1.0:
            raise ValueError("decay must lie in [0, 1)")
        if self.shape not in SHAPES:
            raise ValueError(f"shape must be one of {tuple(SHAPES)}")

    @property
    def is_reduction(self) -> bool:
        """Is this the special case ``A6Model`` already implements?"""
        return (
            self.absorption == 0.0
            and self.decay == 0.0
            and self.shape == "clip"
        )


@dataclass(frozen=True)
class A6Config:
    fiscal: FiscalSpec = field(default_factory=FiscalSpec)
    network: NetworkConfig = field(
        default_factory=lambda: NetworkConfig(
            authority=MonetaryAuthority(rule="none")
        )
    )
    #: Read by :class:`A6RatchetModel` and ignored by :class:`A6Model`. It sits
    #: here rather than on ``FiscalSpec`` so that ``find_rate``'s
    #: ``replace(config.fiscal, rate=...)`` carries it through untouched and
    #: ``FiscalSpec`` itself does not change at all.
    ratchet: RatchetSpec = field(default_factory=RatchetSpec)

    #: Who the levy falls on. Same placement and the same reason as
    #: ``ratchet``: read by :class:`A6RatchetModel`, ignored by
    #: :class:`A6Model`, and carried untouched through ``find_rate``'s
    #: ``replace(config.fiscal, rate=...)``.
    levy: LevySpec = field(default_factory=LevySpec)

    #: Who the rebate is paid to. Same placement and the same reason again.
    #: Kept as its own field rather than folded into ``levy`` because the two
    #: sides of the instrument are separately settable and the whole finding
    #: behind section 18 is that they were not separately *looked at*.
    rebate: RebateSpec = field(default_factory=RebateSpec)


# ---------------------------------------------------------------------------
# measures
# ---------------------------------------------------------------------------


def palma(holdings: np.ndarray) -> float:
    """Top decile's share of holdings over the bottom four deciles'.

    Reported rather than registered. On this model's two hundred nodes the top
    decile is exactly the financial layer, so the statistic is the model's own
    structure and not one imported over it.

    Returns infinity when the bottom four deciles hold nothing, which is a real
    state of this economy and not a numerical accident: it is what a fully
    drained production layer looks like.
    """
    x = np.sort(np.asarray(holdings, dtype=float))
    n = x.size
    if n < 10:
        raise ValueError("Palma needs at least ten observations")
    bottom = x[: int(0.4 * n)].sum()
    top = x[int(0.9 * n) :].sum()
    return float("inf") if bottom <= 0 else float(top / bottom)


def pareto_index(holdings: np.ndarray, tail: float = 0.1) -> float:
    """Hill estimator of the tail exponent, on the top ``tail`` of the sample.

    A conditional secondary, never a criterion. On twenty financial-layer nodes
    the estimator is too thin to carry a claim, and reporting it as though it
    were would be inventing precision the sample does not have. Returns ``nan``
    when the tail has fewer than five usable observations.
    """
    x = np.sort(np.asarray(holdings, dtype=float))
    x = x[x > 0]
    k = int(tail * x.size)
    if k < 5:
        return float("nan")
    top = x[-k:]
    return float(1.0 / np.mean(np.log(top / top[0])[1:]))


#: Relative slack on "did not contract". A support set that ends within a
#: percent of where it started has not contracted in any sense this stage is
#: about, and demanding equality to machine precision destroyed the very result
#: A6-3 predicts: the uniform-access arm holds `1/HHI` at exactly two hundred and
#: was being failed on the last bit of a float.
CONTRACTION_SLACK = 0.01


def contracted(series: np.ndarray, tail: int = 150) -> bool:
    """Did the support set contract over the run?

    **Net contraction, not a tail slope.** The first version asked whether the
    slope over the last hundred and fifty rounds was negative, and at a zero levy
    that slope is `+1.1e-05`: the support set falls from `35.7` to `26.0` in the
    first part of the run and then sits there. A tail slope answers "is it still
    contracting" and the question is "did it contract".

    So the test is the level: the support set at the end must be at least what it
    was at the start. The tail slope is reported beside it, because an economy
    that ends level but is still sliding has not settled and saying so is worth
    a line.
    """
    y = np.asarray(series, dtype=float)
    fell = y[-1] < y[0] * (1.0 - CONTRACTION_SLACK)
    sliding = support_trend(y, last=tail) < -abs(y[0]) * 1e-4
    return bool(fell or sliding)


def support_trend(series: np.ndarray, last: int | None = None) -> float:
    """Slope of the effective support against time, per round.

    Negative is a contracting support set. Fitted on the tail of the run when
    ``last`` is given, so that the transient at the start does not decide a
    question about the steady state.
    """
    y = np.asarray(series, dtype=float)
    if last is not None:
        y = y[-last:]
    t = np.arange(y.size, dtype=float)
    return float(np.polyfit(t, y, 1)[0])


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------


class A6Model(Network):
    """Stage A2's network with a levy and one of two redistribution channels."""

    def __init__(self, config: A6Config) -> None:
        super().__init__(config.network)
        self.a6 = config
        spec = config.fiscal

        self._l1_idx = np.asarray(self._l1, dtype=int)
        self._l2_idx = np.asarray(self._l2, dtype=int)
        self._opening_claims = float(self.holdings.sum())
        self.invested = 0.0

        #: Share of production-layer spending still routed upward, relative to
        #: the opening graph. Falls in the infrastructure arm and is the only
        #: thing that arm changes.
        self.leak_factor = 1.0
        self._route_0 = self._route.copy()
        self._upward = np.zeros_like(self._route, dtype=bool)
        self._upward[np.ix_(self._l2_idx, self._l1_idx)] = True

        if spec.fair_retention:
            # One propensity for everyone, claim-weighted so that the economy's
            # aggregate spending flow at t=0 is unchanged and only its
            # dispersion across nodes is removed.
            w1 = float(config.network.layer1_initial_share)
            flat_low = w1 * self._p_low[0] + (1.0 - w1) * self._p_low[-1]
            flat_high = w1 * self._p_high[0] + (1.0 - w1) * self._p_high[-1]
            self._p_low[:] = flat_low
            self._p_high[:] = flat_high

        self.palma_history: list[float] = []

    # -- the fiscal channel ------------------------------------------------

    def _rebuild_route(self) -> None:
        """Attenuate the production layer's upward edges and renormalise.

        The weight taken off the upward edges is put back on that node's own
        remaining edges rather than deleted, so every row still sums to one and
        no claim is destroyed by the intervention. A node whose only edges run
        upward keeps them: infrastructure cannot reroute spending that has
        nowhere else to go, and pretending otherwise would let the arm succeed
        by removing the very constraint the stage is about.
        """
        route = self._route_0.copy()
        route[self._upward] *= self.leak_factor
        rows = route.sum(axis=1, keepdims=True)
        stuck = rows.ravel() <= 0
        if stuck.any():
            route[stuck] = self._route_0[stuck]
            rows = route.sum(axis=1, keepdims=True)
        self._route = np.divide(
            route, rows, out=np.zeros_like(route), where=rows > 0
        )

    def _apply_levy(self) -> tuple[float, np.ndarray | None]:
        """Move the levy, and return the total plus a flow matrix if asked.

        Both arms move claims identically: out of the financial layer, in equal
        shares to the production layer. Conservation is exact either way; the
        matrix is what decides whether the movement is visible to anything that
        reads the flow.
        """
        spec = self.a6.fiscal
        levy = spec.rate * np.maximum(self.holdings[self._l1_idx], 0.0)
        total = float(levy.sum())
        if total <= 0.0:
            return 0.0, None

        share = total / self._l2_idx.size
        self.holdings[self._l1_idx] -= levy
        self.holdings[self._l2_idx] += share

        matrix = None
        if spec.as_edge:
            matrix = np.zeros((self._n, self._n))
            # Each payer's own contribution, spread over the recipients, so the
            # matrix reproduces the movement rather than approximating it.
            matrix[np.ix_(self._l1_idx, self._l2_idx)] = (
                levy[:, None] / self._l2_idx.size
            )
        return total, matrix

    def _fiscal_flow(self, t: int) -> np.ndarray | None:
        spec = self.a6.fiscal
        if spec.rate <= 0.0 or not spec.as_edge:
            return None
        total, matrix = self._apply_levy()
        if total > 0.0 and spec.channel == "infrastructure":
            self.invested += total
            removed = min(
                1.0, spec.leak_response * self.invested / self._opening_claims
            )
            self.leak_factor = 1.0 - removed
            self._rebuild_route()
        return matrix

    def _post_round(self, t: int) -> None:
        spec = self.a6.fiscal
        self.palma_history.append(palma(self.holdings))
        if spec.rate <= 0.0 or spec.as_edge:
            return

        total, _ = self._apply_levy()
        if total <= 0.0:
            return

        if spec.channel == "infrastructure":
            self.invested += total
            removed = min(
                1.0, spec.leak_response * self.invested / self._opening_claims
            )
            self.leak_factor = 1.0 - removed
            self._rebuild_route()


class A6RatchetModel(A6Model):
    """A6 with the frontier ratchet. Registered in sections 12 and 13.

    Overrides ``_post_round``, adds ``_assess`` beside it, and touches nothing
    else. ``A6Model`` is left exactly as it was when it produced section 9.2,
    so criterion A6-7 reduces this class to an object that is still in the file
    and can be read beside it rather than to a stored fixture.

    Two switches live here and they are orthogonal. :class:`RatchetSpec` sets
    what building buys, :class:`LevySpec` sets who pays for it, and their
    defaults are both the reduction point, so a default-constructed instance of
    this class is ``A6Model``.

    The state, with ``I`` the levy collected this round::

        B ← B + λ·(K − B)          the baseline absorbs what already stood
        K ← (1 − δ)·K + I          then this round's building lands
        x  = ι · max(0, K − B) / claims₀
        leak_factor = 1 − g(x)

    **The baseline absorbs before the new building lands, and the order is not
    a detail.** What was built this instant cannot already be taken for
    granted, so absorption this round operates on the stock as it stood at the
    start of it. That order is also the one whose fixed point is section 12.2's
    ``K − B → I/λ``; absorbing after the build instead gives ``I·(1−λ)/λ``,
    which agrees to first order and is ten percent lower at the top of the
    registered grid. Criterion A6-8 checks the implemented recursion against
    ``I/λ``, so the two are not interchangeable here.

    ``max(0, ·)`` exists for the ``δ > 0`` axis alone. Section 12.3 registers
    the cliff and refuses to simulate it: if decay ever drives ``K`` under
    ``B`` the effect floors at zero rather than walking back down the marginal
    curve.
    """

    def __init__(self, config: A6Config) -> None:
        super().__init__(config)
        #: ``K``. What has been built, after decay. Equal to ``invested`` bit
        #: for bit whenever ``δ = 0``, which every headline cell has.
        self.K = 0.0
        #: ``B``. What has been absorbed into what is taken for granted.
        self.B = 0.0
        self.gap_history: list[float] = []
        self.leak_history: list[float] = []
        #: Levy collected each round. The measurement A6-18 turns on: under a
        #: fixed set of payers this goes to zero once they are drained, and a
        #: threshold base is supposed not to.
        self.levy_history: list[float] = []
        self.payer_count_history: list[int] = []
        #: Share of each round's levy coming from production-layer nodes. Zero
        #: by construction under the layer base, and the whole point of the
        #: threshold base: does the tax follow the money downstream?
        self.l2_levy_share_history: list[float] = []
        #: How many nodes the rebate was split across. Constant at the
        #: production layer's size under the layer base; under the threshold
        #: base it moves with the distribution and is the measurement A6-20
        #: turns on.
        self.payee_count_history: list[int] = []
        #: Rounds in which the threshold rebate named nobody and the claims
        #: were split across every node instead. Recorded per round so that a
        #: fallback can never be a silent change of policy.
        self.rebate_fallback_history: list[bool] = []
        #: How many nodes both paid and received in the same round. Zero under
        #: the threshold rebate by construction, since both sides are read off
        #: one measurement, and it is recorded anyway: a non-zero entry would
        #: mean the within-round ordering had been changed.
        self.both_sides_history: list[int] = []

    def _assess(self) -> tuple[np.ndarray | None, np.ndarray]:
        """Who pays this round and how much. ``(payer indices, amounts)``.

        ``None`` for the indices means every node, which keeps the caller from
        having to build and index an ``arange`` over the whole graph in the one
        case where it would change the arithmetic.

        The ``layer`` branch is the expression stage A6 has always had, written
        out character for character, because criterion A6-7 compares the result
        against ``A6Model`` bit for bit and any rearrangement of it, however
        algebraically equal, is a risk with no upside.
        """
        spec = self.a6.fiscal
        if self.a6.levy.base == "layer":
            return (
                self._l1_idx,
                spec.rate * np.maximum(self.holdings[self._l1_idx], 0.0),
            )
        threshold = (
            self.a6.levy.threshold_multiple * self._total_claims / self._n
        )
        return None, spec.rate * np.maximum(self.holdings - threshold, 0.0)

    def _payees(self) -> tuple[np.ndarray | None, bool]:
        """Who receives this round. ``(recipient indices, fell back)``.

        ``None`` for the indices means the layer branch, which ``_disburse``
        writes out separately for the same reason ``_assess`` does: A6-7
        compares this class against ``A6Model`` bit for bit and an
        algebraically equal rearrangement is a risk with no upside.

        **Read off the holdings before the levy is deducted, and that ordering
        is load-bearing.** A real instrument assesses both sides on one
        measurement date. Taking the recipients off the post-levy holdings
        would let a node pay and then immediately qualify to receive, which is
        the overlap :class:`RebateSpec` exists to remove, reintroduced by
        ordering rather than by membership. Assessed here, above ``θ`` pays,
        below it receives, and no node does both. ``both_sides_history`` checks
        that rather than trusting it.
        """
        if self.a6.rebate.base == "layer":
            return None, False
        threshold = (
            self.a6.levy.threshold_multiple * self._total_claims / self._n
        )
        below = np.flatnonzero(self.holdings < threshold)
        if below.size == 0:
            # Nobody is below the threshold, so the rule names no recipient.
            # The claims still have to land somewhere: conservation is not
            # negotiable, and holding them outside the ledger would turn the
            # levy into a destruction of claims rather than a transfer. Split
            # across every node and record the round.
            return np.arange(self._n), True
        return below, False

    def _disburse(self, payees: np.ndarray | None, total: float) -> None:
        """Pay ``total`` out. The mirror of ``_assess``, and its inverse."""
        if payees is None:
            self.holdings[self._l2_idx] += total / self._l2_idx.size
            self.payee_count_history.append(int(self._l2_idx.size))
            return
        self.holdings[payees] += total / payees.size
        self.payee_count_history.append(int(payees.size))

    def _post_round(self, t: int) -> None:
        spec = self.a6.fiscal
        ratchet = self.a6.ratchet
        self.palma_history.append(palma(self.holdings))
        if spec.rate <= 0.0:
            return

        payers, levy = self._assess()
        # Both sides are read off the same holdings, before either moves.
        payees, fell_back = self._payees()
        total = float(levy.sum())
        self.levy_history.append(total)
        self.payer_count_history.append(int((levy > 0.0).sum()))
        self.l2_levy_share_history.append(
            0.0 if (payers is not None or total <= 0.0)
            else float(levy[self._l2_idx].sum()) / total
        )
        self.rebate_fallback_history.append(bool(fell_back))
        paid = (
            np.flatnonzero(levy > 0.0) if payers is None
            else np.asarray(payers)[levy > 0.0]
        )
        got = self._l2_idx if payees is None else payees
        self.both_sides_history.append(
            int(np.intersect1d(paid, got, assume_unique=False).size)
        )
        if total > 0.0:
            if payers is None:
                self.holdings -= levy
            else:
                self.holdings[payers] -= levy
            self._disburse(payees, total)
        else:
            self.payee_count_history.append(
                int(self._l2_idx.size if payees is None else payees.size)
            )

        if spec.channel != "infrastructure":
            return

        # A drained financial layer collects no levy, and the arm still has to
        # run: the baseline keeps absorbing whether or not anything was built
        # this round, so the gap decays, the leak reopens and the layer refills.
        # That is the feedback the ratchet exists to create, and returning early
        # here would break it and make A6-9 fail for a reason in the code rather
        # than in the mechanism.
        before = self.leak_factor
        self.invested += total
        if ratchet.absorption:
            self.B += ratchet.absorption * (self.K - self.B)
        if ratchet.decay:
            self.K *= 1.0 - ratchet.decay
        self.K += total

        gap = self.K - self.B
        if gap < 0.0:
            gap = 0.0
        removed = SHAPES[ratchet.shape](
            spec.leak_response * gap / self._opening_claims
        )
        self.leak_factor = 1.0 - removed
        self.gap_history.append(gap)
        self.leak_history.append(self.leak_factor)

        # ``_rebuild_route`` is a pure function of ``leak_factor``, so skipping
        # it when nothing moved leaves ``_route`` on exactly the same bits. The
        # skip is what keeps this class byte-compatible with ``A6Model`` in the
        # rounds where that model returned early.
        if total > 0.0 or self.leak_factor != before:
            self._rebuild_route()


def run_a6(
    config: A6Config, *, model_cls: type[A6Model] = A6Model
) -> tuple[A6Model, object]:
    """Run and return the model alongside its history.

    The model is returned because the Palma trajectory and the investment total
    live on it, and a history object cannot carry them.

    ``model_cls`` selects the arm. The default is the class that produced
    section 9.2, and no existing caller passes anything else.
    """
    model = model_cls(config)
    return model, model.run()


#: The scan grid. Hoisted out of ``find_rate``'s signature so that the two
#: functions that walk it cannot drift apart. The values are unchanged from the
#: tuple that was written inline there.
RATE_GRID: tuple[float, ...] = (
    0.0, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.12, 0.16,
    0.24, 0.32, 0.48, 0.64, 0.80, 0.95,
)


def scan_rates(
    config: A6Config,
    *,
    tail: int = 150,
    grid: tuple[float, ...] = RATE_GRID,
    model_cls: type[A6Model] = A6Model,
) -> list[bool]:
    """``contracted`` at every point of the grid, in grid order.

    A6-12 needs the whole vector and not just its first ``False``. Section 9.1
    recorded that the infrastructure arm is not monotone at any seed, so the
    rates that hold the economy open form a band, and where that band ends was
    never located. ``find_rate`` reads this same vector for its first entry.
    """
    out: list[bool] = []
    for rate in grid:
        cfg = replace(config, fiscal=replace(config.fiscal, rate=rate))
        _, history = run_a6(cfg, model_cls=model_cls)
        out.append(contracted(history.effective_support, tail=tail))
    return out


def open_band(
    grid: tuple[float, ...], verdicts: list[bool]
) -> tuple[float | None, float | None, bool]:
    """Lowest and highest grid rate that hold the support set open.

    Returns ``(low, high, contiguous)``. ``contiguous`` reports whether every
    grid point between the two is open as well, which is the part section 9.1
    left open when it observed that this arm is not monotone. A band with a
    hole in it is a different object from a band, and averaging over the
    difference is how a non-monotone relation gets quoted as a threshold.
    """
    open_at = [r for r, bad in zip(grid, verdicts, strict=True) if not bad]
    if not open_at:
        return None, None, True
    low, high = open_at[0], open_at[-1]
    inside = [
        bad for r, bad in zip(grid, verdicts, strict=True) if low <= r <= high
    ]
    return low, high, not any(inside)


def find_rate(
    config: A6Config,
    *,
    tail: int = 150,
    grid: tuple[float, ...] = RATE_GRID,
    model_cls: type[A6Model] = A6Model,
) -> tuple[float | None, bool]:
    """``R*``, and whether the relation is monotone above it.

    Returns ``(rate, monotone)``. ``rate`` is ``None`` when no point on the grid
    holds the support set open, which is criterion A6-2's failure and is reported
    as such rather than as a large number.

    **A grid scan, not bisection.** The first version bisected, which presumes
    that a higher levy never hurts. It does: at a rate near one the levy strips
    the financial layer every round and the support set contracts for that
    reason instead of the original one, so the relation is not monotone and
    bisection on it can land anywhere. The scan finds the smallest rate that
    works and then reports whether every larger rate also works, which is a fact
    worth knowing rather than an assumption worth making.
    """
    verdicts = scan_rates(config, tail=tail, grid=grid, model_cls=model_cls)
    open_at = [r for r, bad in zip(grid, verdicts, strict=True) if not bad]
    if not open_at:
        return None, True
    first = open_at[0]
    after = [
        bad for r, bad in zip(grid, verdicts, strict=True) if r >= first
    ]
    return first, not any(after)


__all__ = [
    "CHANNELS",
    "LEVY_BASES",
    "RATE_GRID",
    "SHAPES",
    "A6Config",
    "A6Model",
    "A6RatchetModel",
    "FiscalSpec",
    "LevySpec",
    "RatchetSpec",
    "contracted",
    "find_rate",
    "open_band",
    "palma",
    "pareto_index",
    "run_a6",
    "scan_rates",
    "support_trend",
]
