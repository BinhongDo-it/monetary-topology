"""A0: the retention-and-allocation model.

Purpose
-------
Isolate one mechanism: new claims enter at the top of a stratified economy, each
stratum withholds some share from cross-layer circulation, and the monetary
authority calibrates issuance against the active pools only.

Deliberately minimal. No credit creation, no default, no network finer than
stratum-level adjacency, and no cross-layer bidding for a shared resource pool.
Those belong to later stages. Adding them here would make the headline results
impossible to check by hand, which is the only reason this stage exists.

Three claims are put at risk
----------------------------
1. The active ratio stays flat while the total ratio rises monotonically, the
   rise equalling cumulative retention.
2. Retention is not hoarding. Spending inside one's own layer is, for every node
   outside that layer, indistinguishable from spending nothing. Book velocity is
   non-zero, topological displacement is zero.
3. Therefore the top layer's *rate* of spending does not govern what reaches the
   production layer. The adjacency matrix does.

Claim (3) is the one worth attacking, so the experiment sweeps both variables and
lets the reader see which one moves the outcome.

Measurement note
----------------
``active_claims`` counts claims *landing in Layer 2*. Flow that circulates inside
Layer 1, however fast, is excluded. That single choice carries claim (2) and is
the most consequential line in the file. It is stated here rather than buried, so
a reader who rejects it knows exactly what to reject.

A0 reports claims, not real resource allocation. Converting claim inflow into
resource access requires both layers bidding for a shared pool, which is where
asset inflation squeezes the production layer. That mechanism is real and it is
in the source, but it needs a price system with cross-layer asset markets, which
is stage A3. Reporting it here would mean inventing a deflator, and an invented
deflator is exactly the kind of formalisation that backs a conclusion instead of
checking it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import INJECTION_STRATUM, LAYER_1, LAYER_2, EconomyConfig

#: Tolerance for the stock-flow consistency assertion. Claims are conserved
#: exactly up to floating point. Not a fitted slack.
SFC_TOLERANCE = 1e-9


@dataclass
class History:
    """Per-round record. One row per round, arrays aligned by index."""

    holdings: np.ndarray  # (rounds, n_strata) claims held at end of round
    spending: np.ndarray  # (rounds, n_strata) discretionary claims spent
    terminating: np.ndarray  # (rounds, n_strata) claims landing, by stratum
    active_claims: np.ndarray  # (rounds,) M_a: claims landing in Layer 2
    dormant_claims: np.ndarray  # (rounds,) M_d = M - M_a
    total_claims: np.ndarray  # (rounds,) M
    active_resources: np.ndarray  # (rounds,) R_a
    total_resources: np.ndarray  # (rounds,) R
    issuance: np.ndarray  # (rounds,) new claims created this round
    retention: np.ndarray  # (rounds,) active circulation lost vs baseline
    layer1_holdings: np.ndarray  # (rounds,) claims parked in Layer 1
    layer2_holdings: np.ndarray  # (rounds,) claims held in Layer 2
    layer1_churn: np.ndarray  # (rounds,) flow circulating inside Layer 1
    wage_bill: np.ndarray  # (rounds,) the bill owed, after derived demand
    layer2_spending: np.ndarray  # (rounds,) Layer 2 discretionary spending

    @property
    def collapsed(self) -> bool:
        """Whether Layer 2 circulation fell to a negligible fraction of its
        starting level and stayed there.

        The threshold is deliberately coarse. The question this answers is
        qualitative -- does the production layer settle at a floor or spiral to
        nothing -- and a coarse cut is more honest than a tuned one.
        """
        start = float(self.layer2_spending[0])
        if start <= 0.0:
            return True
        tail = float(np.asarray(self.layer2_spending)[-25:].mean())
        return tail < 0.01 * start

    @property
    def active_ratio(self) -> np.ndarray:
        """M_a / R_a. What the authority targets and a price index reads."""
        return self.active_claims / self.active_resources

    @property
    def total_ratio(self) -> np.ndarray:
        """M / R. What nobody targets."""
        return self.total_claims / self.total_resources

    @property
    def cumulative_issuance(self) -> np.ndarray:
        return np.cumsum(self.issuance)

    @property
    def cumulative_retention(self) -> np.ndarray:
        return np.cumsum(self.retention)

    @property
    def layer1_share(self) -> np.ndarray:
        """Share of all claims parked in Layer 1."""
        return self.layer1_holdings / self.total_claims

    def tail_mean(self, metric: str, last: int = 50) -> float:
        series = np.asarray(getattr(self, metric), dtype=float)
        return float(series[-min(last, len(series)) :].mean())

    def tail_std(self, metric: str, last: int = 50) -> float:
        series = np.asarray(getattr(self, metric), dtype=float)
        return float(series[-min(last, len(series)) :].std())


class Economy:
    """Stratified claim-circulation model with an issuance rule.

    Ordering within a round is fixed and load-bearing:

    1. Issuance decided on last round's observation is credited to the injection
       stratum. The authority acts on lagged information; it cannot observe this
       round before financing it.
    2. Wages settle. Contractual, so they clear before discretion.
    3. Discretionary spending is drawn as a propensity on holdings and routed
       through the adjacency matrix.
    4. Measurement, then the issuance decision for next round.
    """

    def __init__(self, config: EconomyConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)

        shares = np.asarray(config.strata.wealth_share, dtype=float)
        self.holdings = shares * config.initial_claims
        self.flow = config.adjacency.as_array()
        self.wage_source = np.asarray(config.wages.source_shares, dtype=float)
        self.wage_dest = np.asarray(config.wages.dest_shares, dtype=float)

        self._n = config.strata.n_strata
        self._l1 = list(LAYER_1)
        self._l2 = list(LAYER_2)
        self._total_claims = float(config.initial_claims)
        self._pending_issuance = 0.0
        self._baseline_active: float | None = None
        #: Layer 2 spending last round, and its t=0 reference. Both seeded from
        #: the initial distribution so that round 0 is not a special case.
        seed_spending = float(
            (
                0.5
                * (np.asarray(config.spend.low) + np.asarray(config.spend.high))
                * shares
                * config.initial_claims
            )[self._l2].sum()
        )
        self._last_l2_spending = seed_spending
        self._baseline_l2_spending = seed_spending

    # -- flows -------------------------------------------------------------

    def _wage_flows(self) -> tuple[np.ndarray, float]:
        """Settle the wage bill; return the (n, n) flow matrix and the bill.

        The bill is set by ``WageChannel.bill_at`` from *last* round's Layer 2
        spending, because wages clear before discretionary spending within a
        round. That one-round lag is what makes the derived-demand version a
        dynamical system rather than a fixed point calculation.

        Payment is then capped by what each financing stratum can actually pay,
        so the channel narrows when the upper strata are illiquid instead of
        driving holdings negative. Two distinct constrictions therefore act on
        the same edge: derived demand cuts the bill that is owed, illiquidity
        cuts the bill that is paid.
        """
        bill = self.config.wages.bill_at(
            self._last_l2_spending, self._baseline_l2_spending
        )
        if bill <= 0.0:
            return np.zeros((self._n, self._n)), 0.0

        demanded = self.wage_source * bill
        paid = np.minimum(demanded, np.maximum(self.holdings, 0.0))
        matrix = np.outer(paid, self.wage_dest)
        self.holdings = self.holdings - paid + matrix.sum(axis=0)
        return matrix, bill

    def _discretionary_flows(self) -> tuple[np.ndarray, np.ndarray]:
        """Draw and route discretionary spending.

        Returns ``(spent_by_stratum, flow_matrix)``.
        """
        propensity = self.config.spend.draw(self.rng)
        spent = propensity * np.maximum(self.holdings, 0.0)
        matrix = spent[:, None] * self.flow
        self.holdings = self.holdings - spent + matrix.sum(axis=0)
        return spent, matrix

    # -- issuance ----------------------------------------------------------

    def _issuance_decision(self, observed_active: float) -> float:
        auth = self.config.authority
        if auth.rule == "none":
            return 0.0
        if auth.rule == "fixed":
            return auth.fixed_amount
        if self._baseline_active is None:
            return 0.0
        return max(0.0, auth.gain * (self._baseline_active - observed_active))

    # -- driver ------------------------------------------------------------

    def run(self) -> History:
        cfg = self.config
        rounds, n = cfg.rounds, self._n

        out: dict[str, np.ndarray] = {
            "holdings": np.zeros((rounds, n)),
            "spending": np.zeros((rounds, n)),
            "terminating": np.zeros((rounds, n)),
            "active_claims": np.zeros(rounds),
            "dormant_claims": np.zeros(rounds),
            "total_claims": np.zeros(rounds),
            "active_resources": np.zeros(rounds),
            "total_resources": np.zeros(rounds),
            "issuance": np.zeros(rounds),
            "retention": np.zeros(rounds),
            "layer1_holdings": np.zeros(rounds),
            "layer2_holdings": np.zeros(rounds),
            "layer1_churn": np.zeros(rounds),
            "wage_bill": np.zeros(rounds),
            "layer2_spending": np.zeros(rounds),
        }

        resources_offered = cfg.total_resources * (1.0 - cfg.resource_withholding)

        for t in range(rounds):
            # 1. lagged issuance, credited at the injection point
            issued = self._pending_issuance
            if issued:
                self.holdings[INJECTION_STRATUM] += issued
                self._total_claims += issued
            self._pending_issuance = 0.0

            claims_before = float(self.holdings.sum())

            # 2-3. flows
            wage_matrix, bill = self._wage_flows()
            spent, spend_matrix = self._discretionary_flows()
            total_matrix = wage_matrix + spend_matrix

            claims_after = float(self.holdings.sum())
            if abs(claims_after - claims_before) > SFC_TOLERANCE:
                raise AssertionError(
                    f"stock-flow inconsistency at round {t}: "
                    f"{claims_before!r} -> {claims_after!r}"
                )

            # 4. measurement. Active claims land in Layer 2; see module docstring.
            terminating = total_matrix.sum(axis=0)
            active = float(total_matrix[:, self._l2].sum())
            churn = float(total_matrix[np.ix_(self._l1, self._l1)].sum())

            if self._baseline_active is None:
                self._baseline_active = active
            retention = max(0.0, self._baseline_active - active)

            out["holdings"][t] = self.holdings
            out["spending"][t] = spent
            out["terminating"][t] = terminating
            out["active_claims"][t] = active
            out["dormant_claims"][t] = self._total_claims - active
            out["total_claims"][t] = self._total_claims
            out["active_resources"][t] = resources_offered
            out["total_resources"][t] = cfg.total_resources
            out["issuance"][t] = issued
            out["retention"][t] = retention
            out["layer1_holdings"][t] = float(self.holdings[self._l1].sum())
            out["layer2_holdings"][t] = float(self.holdings[self._l2].sum())
            out["layer1_churn"][t] = churn
            out["wage_bill"][t] = bill
            out["layer2_spending"][t] = float(spent[self._l2].sum())

            self._last_l2_spending = out["layer2_spending"][t]
            self._pending_issuance = self._issuance_decision(active)

        return History(**out)


def run(config: EconomyConfig) -> History:
    """Convenience entry point."""
    return Economy(config).run()
