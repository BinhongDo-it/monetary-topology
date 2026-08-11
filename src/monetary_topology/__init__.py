"""Monetary topology: mechanism models for a claims-and-resources framework.

Stage A0 (this release) isolates retention and allocation. Later stages add the
default waterfall (A1), support-set contraction (A2), and the integrated
simulator (A3). See PROJECT_PLAN.md for milestone criteria.
"""

from .asset import (
    CLOSED,
    A3Config,
    A3Model,
    AssetSpec,
    DesignDeviation,
    centrality,
    loop_sum,
    run_a3,
    run_a3_model,
    soft_gate,
    terms_matrix,
)
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
from .mechanisms import (
    A4Config,
    A4Model,
    A4Result,
    MechanismParams,
    Switches,
    cell_configs,
    cross_layer_baseline,
    gini,
    run_a4,
)
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
    "CLOSED",
    "STRATUM_NAMES",
    "A3Config",
    "A3Model",
    "A4Config",
    "A4Model",
    "A4Result",
    "Adjacency",
    "AssetSpec",
    "DesignDeviation",
    "Economy",
    "EconomyConfig",
    "History",
    "HodgeSplit",
    "MechanismParams",
    "MonetaryAuthority",
    "Network",
    "NetworkConfig",
    "NetworkHistory",
    "NetworkSpec",
    "Preset",
    "SpendRule",
    "Strata",
    "Switches",
    "WageChannel",
    "cell_configs",
    "centrality",
    "cross_layer_baseline",
    "cycle_rank",
    "dfa_calibrated",
    "effective_support",
    "gini",
    "hodge_decomposition",
    "loop_sum",
    "presets",
    "realized_adjacency",
    "run",
    "run_a3",
    "run_a3_model",
    "run_a4",
    "run_network",
    "soft_gate",
    "source_faithful",
    "terms_matrix",
]

__version__ = "0.1.0"
