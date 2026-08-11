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
    Adds a downward edge. Levy on the financial layer, paid out equally per head
    across the production layer. The claims arrive and then leak back upward
    along the existing edges at the rate those edges always had.

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


@dataclass(frozen=True)
class A6Config:
    fiscal: FiscalSpec = field(default_factory=FiscalSpec)
    network: NetworkConfig = field(
        default_factory=lambda: NetworkConfig(
            authority=MonetaryAuthority(rule="none")
        )
    )


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

    def _post_round(self, t: int) -> None:
        spec = self.a6.fiscal
        self.palma_history.append(palma(self.holdings))
        if spec.rate <= 0.0:
            return

        levy = spec.rate * np.maximum(self.holdings[self._l1_idx], 0.0)
        total = float(levy.sum())
        if total <= 0.0:
            return

        # Both arms move claims identically: out of the financial layer, in
        # equal shares to the production layer. Conservation is exact.
        self.holdings[self._l1_idx] -= levy
        self.holdings[self._l2_idx] += total / self._l2_idx.size

        if spec.channel == "infrastructure":
            self.invested += total
            removed = min(
                1.0, spec.leak_response * self.invested / self._opening_claims
            )
            self.leak_factor = 1.0 - removed
            self._rebuild_route()


def run_a6(config: A6Config) -> tuple[A6Model, object]:
    """Run and return the model alongside its history.

    The model is returned because the Palma trajectory and the investment total
    live on it, and a history object cannot carry them.
    """
    model = A6Model(config)
    return model, model.run()


def find_rate(
    config: A6Config,
    *,
    tail: int = 150,
    grid: tuple[float, ...] = (
        0.0, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.12, 0.16,
        0.24, 0.32, 0.48, 0.64, 0.80, 0.95,
    ),
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
    def contracts(rate: float) -> bool:
        cfg = replace(config, fiscal=replace(config.fiscal, rate=rate))
        _, history = run_a6(cfg)
        return contracted(history.effective_support, tail=tail)

    verdicts = [contracts(r) for r in grid]
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
    "A6Config",
    "A6Model",
    "FiscalSpec",
    "contracted",
    "find_rate",
    "palma",
    "pareto_index",
    "run_a6",
    "support_trend",
]
