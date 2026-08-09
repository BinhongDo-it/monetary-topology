"""Monetary topology: mechanism models for a claims-and-resources framework.

Stage A0 (this release) isolates retention and allocation. Later stages add the
default waterfall (A1), support-set contraction (A2), and the integrated
simulator (A3). See PROJECT_PLAN.md for milestone criteria.
"""

from .calibration import Preset, dfa_calibrated, presets, source_faithful
from .config import (
    STRATUM_NAMES,
    Adjacency,
    EconomyConfig,
    MonetaryAuthority,
    SpendRule,
    Strata,
    WageChannel,
)
from .economy import Economy, History, run
from .network import (
    Network,
    NetworkConfig,
    NetworkHistory,
    NetworkSpec,
    effective_support,
    run_network,
)
from .topology import (
    HodgeSplit,
    cycle_rank,
    hodge_decomposition,
    realized_adjacency,
)

__all__ = [
    "STRATUM_NAMES",
    "Adjacency",
    "Economy",
    "EconomyConfig",
    "History",
    "HodgeSplit",
    "MonetaryAuthority",
    "Network",
    "NetworkConfig",
    "NetworkHistory",
    "NetworkSpec",
    "Preset",
    "SpendRule",
    "Strata",
    "WageChannel",
    "cycle_rank",
    "dfa_calibrated",
    "effective_support",
    "hodge_decomposition",
    "presets",
    "realized_adjacency",
    "run",
    "run_network",
    "source_faithful",
]

__version__ = "0.1.0"
