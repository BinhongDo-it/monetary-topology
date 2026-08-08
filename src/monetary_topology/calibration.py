"""Calibrated parameter presets, with sources.

Two presets are provided and both are reported. The source-faithful one keeps
the original worked example reproducible; the DFA one replaces every invented
number with a published estimate. A finding that holds under both is not an
artefact of either.

Nothing here is fitted. These are published levels substituted directly into the
model, which is the cheapest available answer to the objection that the numbers
were chosen to produce the result.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    Adjacency,
    EconomyConfig,
    MonetaryAuthority,
    SpendRule,
    Strata,
    WageChannel,
)

# ---------------------------------------------------------------------------
# Federal Reserve Distributional Financial Accounts, Q1 2026
# ---------------------------------------------------------------------------
# Share of total net worth by wealth percentile group. Retrieved 2026-08-08 from
# the FRED release table "Shares of Wealth by Wealth Percentile Groups"
# (release 453, Q1 2026). Series identifiers are given so a reader can pull the
# same vintage rather than trusting this file.
#
#   top 1%   (99th-100th)  31.6   WFRBST01134
#   next 9%  (90th-99th)   36.3   WFRBSN09161
#   next 40% (50th-90th)   29.6   WFRBSN40188
#   bottom 50%             2.5    WFRBSB50215
#                          -----
#                          100.0
#
# The four DFA groups map onto the model's four strata without adjustment, which
# is why this preset needs no interpolation: the DFA's own grouping is
# 1 / 9 / 40 / 50, and the source framework's toy strata were already close to
# it. Agent counts follow the percentile widths exactly.

DFA_VINTAGE = "Q1 2026"
DFA_RETRIEVED = "2026-08-08"
DFA_SERIES = {
    "top1": "WFRBST01134",
    "upper9": "WFRBSN09161",
    "middle40": "WFRBSN40188",
    "bottom50": "WFRBSB50215",
}
DFA_NET_WORTH_SHARES = (0.025, 0.296, 0.363, 0.316)
DFA_COUNTS = (50, 40, 9, 1)

# Two further DFA figures are not used at this stage but are recorded because
# they are the calibration targets for the default waterfall at stage A1, and
# because their juxtaposition is itself the K-shape:
#
#   bottom 50% share of consumer credit   51.8   WFRBSB50211
#   bottom 50% share of total liabilities 30.4   WFRBSB50208
#   bottom 50% share of net worth          2.5   WFRBSB50215
#
# The bottom half of the distribution holds over half of all consumer credit
# against two and a half percent of net worth.
DFA_BOTTOM50_CONSUMER_CREDIT = 0.518
DFA_BOTTOM50_LIABILITIES = 0.304

# ---------------------------------------------------------------------------
# Spending propensities
# ---------------------------------------------------------------------------
# The DFA gives stocks, not behaviour, so propensities come from elsewhere.
#
# Fagereng, Holm & Natvik, "MPC Heterogeneity and Household Balance Sheets",
# American Economic Journal: Macroeconomics, October 2021. Norwegian lottery
# wins in administrative panel data. Low-liquidity winners of the smallest
# prizes spend essentially all of the win within the year; high-liquidity
# winners of the largest prizes spend slightly below one half.
#
# Caveat, stated rather than buried: their estimand is the MPC out of a
# transitory income shock, while this model's propensity is a spending rate out
# of holdings. These are not the same quantity, and the mapping is an analogy
# justified by both being a share of an available claim balance spent within a
# period. What the estimates license is the *range and ordering* -- close to one
# at the bottom, slightly under one half at the top -- not the exact values.
#
# The relevant fact for this repository is that the source framework's toy
# figures, reverse-engineered from its worked example as 0.88-1.00 at the bottom
# and 0.50 at the top, already sit inside the measured range. The calibration
# tightens the provenance; it does not move the numbers much.

FHN_CITATION = (
    "Fagereng, Holm & Natvik (2021), MPC Heterogeneity and Household Balance "
    "Sheets, AEJ: Macroeconomics"
)
DFA_PROPENSITY_LOW = (0.95, 0.85, 0.55, 0.48)
DFA_PROPENSITY_HIGH = (1.00, 0.95, 0.55, 0.48)


@dataclass(frozen=True)
class Preset:
    """A named configuration with its provenance."""

    name: str
    config: EconomyConfig
    sources: tuple[str, ...]

    def describe(self) -> str:
        lines = [f"{self.name}:"]
        lines += [f"  - {s}" for s in self.sources]
        return "\n".join(lines)


def source_faithful(**overrides: object) -> EconomyConfig:
    """The original worked example. All library defaults."""
    return EconomyConfig(**overrides)  # type: ignore[arg-type]


def dfa_calibrated(**overrides: object) -> EconomyConfig:
    """Published wealth shares and propensities substituted for toy figures.

    The wage bill is set so that Layer 2's outflow still exceeds its downward
    inflow, because the death-zone condition is the premise of the stage rather
    than something the calibration is asked to deliver. Its value is reported by
    ``EconomyConfig.flow_balance`` and the sensitivity to it is swept in the
    experiment.
    """
    defaults: dict[str, object] = {
        "strata": Strata(counts=DFA_COUNTS, wealth_share=DFA_NET_WORTH_SHARES),
        "spend": SpendRule(low=DFA_PROPENSITY_LOW, high=DFA_PROPENSITY_HIGH),
        "adjacency": Adjacency(),
        "wages": WageChannel(bill=6.0),
        "authority": MonetaryAuthority(rule="endogenous"),
    }
    defaults.update(overrides)
    return EconomyConfig(**defaults)  # type: ignore[arg-type]


def presets() -> tuple[Preset, ...]:
    return (
        Preset(
            name="source-faithful",
            config=source_faithful(),
            sources=(
                "wealth shares and propensities from the framework's 100-agent "
                "worked example; bottom stratum is our explicit completion of "
                "an implicit residual",
            ),
        ),
        Preset(
            name="DFA-calibrated",
            config=dfa_calibrated(),
            sources=(
                f"net worth shares: Fed Distributional Financial Accounts "
                f"{DFA_VINTAGE}, retrieved {DFA_RETRIEVED}, series "
                + ", ".join(sorted(DFA_SERIES.values())),
                f"propensity range and ordering: {FHN_CITATION}",
                "adjacency and wage bill: not calibrated. Assumptions, swept in "
                "the experiment rather than defended",
            ),
        ),
    )
