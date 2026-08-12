"""Stage A0: retention and allocation. Runs every figure and every criterion.

Usage::

    python experiments/a0_retention.py
    python experiments/a0_retention.py --rounds 600 --seed 12

Writes PNGs to ``figures/`` and a machine-readable record to
``results/a0_retention.json``. The criteria table it prints is the same one
recorded in RESULTS.md, including any criterion that fails: a results file that
only records successes is the same object as a macro statistic designed to look
good.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology import EconomyConfig, History, MonetaryAuthority, run
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)
from monetary_topology.variants import variant

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

TAIL = 50
TOP_PROPENSITIES = (0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0)
DOWNWARD_EDGES = (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.55, 0.7, 0.85)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


# ---------------------------------------------------------------------------
# figure 1: the production layer drains to the payroll floor
# ---------------------------------------------------------------------------


def figure_1(base: EconomyConfig) -> tuple[Path, History]:
    h = run(base)
    rounds = np.arange(base.rounds)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(7.2, 5.6), sharex=True, height_ratios=[1.15, 1]
    )

    ax_top.plot(
        rounds, h.layer2_holdings, color=COLOR_LAYER2, label="Layer 2 (production)"
    )
    ax_top.plot(
        rounds, h.layer1_holdings, color=COLOR_LAYER1, label="Layer 1 (financial)"
    )
    ax_top.set_yscale("log")
    ax_top.set_ylabel("claims held (log)")
    ax_top.set_title("Claims accumulate in one layer and drain from the other")
    ax_top.legend(loc="center right")
    annotate(
        ax_top,
        "Log scale. Layers start at 40 and 60.\n"
        "Issuance is credited to Layer 1 every round.",
        loc="upper left",
    )

    ax_bot.plot(
        rounds, h.active_claims, color=COLOR_LAYER2, label="claims landing in Layer 2"
    )
    floor = base.wages.net_downward()
    ax_bot.axhline(
        floor,
        color=COLOR_INSTRUMENT,
        linestyle="--",
        linewidth=1.2,
        label=f"net downward wage flow = {floor:.2f}",
    )
    ax_bot.set_xlabel("round")
    ax_bot.set_ylabel("claims per round")
    ax_bot.set_ylim(0, float(h.active_claims.max()) * 1.12)
    ax_bot.set_title("Inflow converges to the payroll edge, not to zero")
    ax_bot.legend(loc="upper right")
    annotate(
        ax_bot,
        "The production layer does not collapse. It settles at whatever the\n"
        "one downward edge delivers, plus its own internal circulation.",
        loc="lower left",
    )

    fig.tight_layout()
    return save(fig, FIGURES / "a0_fig1_layer_drain.png"), h


# ---------------------------------------------------------------------------
# figure 2: the two ratios
# ---------------------------------------------------------------------------


def figure_2(base: EconomyConfig) -> tuple[Path, History]:
    cfg = variant(base, authority=MonetaryAuthority(rule="endogenous"))
    h = run(cfg)
    rounds = np.arange(cfg.rounds)

    fig, (ax_ratio, ax_share) = plt.subplots(
        2, 1, figsize=(7.2, 5.6), sharex=True, height_ratios=[1.25, 1]
    )

    # Independent scales. The two series differ by two orders of magnitude by
    # the end of the run, so a shared axis would render the targeted ratio as a
    # flat line pinned to zero and hide the very thing being claimed about it.
    # Both axes start at zero and both ranges are printed on the figure.
    ax_ratio.plot(
        rounds, h.total_ratio, color=COLOR_LAYER1, label="M / R  (nobody targets this)"
    )
    ax_ratio.set_ylabel("M / R", color=COLOR_LAYER1)
    ax_ratio.tick_params(axis="y", labelcolor=COLOR_LAYER1)
    ax_ratio.set_ylim(0, float(h.total_ratio.max()) * 1.08)
    ax_ratio.set_title(
        "The targeted ratio settles; the total ratio rises without bound"
    )

    ax_active = ax_ratio.twinx()
    ax_active.plot(
        rounds,
        h.active_ratio,
        color=COLOR_LAYER2,
        label=r"M$_a$ / R$_a$  (the instrument targets this)",
    )
    ax_active.set_ylabel(r"M$_a$ / R$_a$", color=COLOR_LAYER2)
    ax_active.tick_params(axis="y", labelcolor=COLOR_LAYER2)
    ax_active.set_ylim(0, float(h.active_ratio.max()) * 1.6)
    ax_active.spines["top"].set_visible(False)
    ax_active.grid(False)

    handles = ax_ratio.get_lines() + ax_active.get_lines()
    ax_ratio.legend(handles, [x.get_label() for x in handles], loc="upper left")
    annotate(
        ax_ratio,
        f"M/R rose {h.total_ratio[0]:.2f} to {h.total_ratio[-1]:.2f}. "
        f"M$_a$/R$_a$ held {h.tail_mean('active_ratio', TAIL):.3f} "
        f"+/- {h.tail_std('active_ratio', TAIL):.1e}.\n"
        "Separate axes, both zero-based; ranges stated here because the series "
        "differ by two orders of magnitude.",
        loc="lower right",
    )

    ax_share.plot(
        rounds,
        h.cumulative_issuance,
        color=COLOR_INSTRUMENT,
        label="cumulative issuance",
    )
    ax_share.plot(
        rounds,
        h.cumulative_retention,
        color=COLOR_ACCENT,
        linestyle="--",
        label="cumulative retention",
    )
    ax_share.set_xlabel("round")
    ax_share.set_ylabel("claims")
    ax_share.set_title("Issuance equals retention, to floating-point identity")
    ax_share.legend(loc="upper left")
    residual = float(np.abs(h.issuance[1:] - h.retention[:-1]).max())
    annotate(
        ax_share,
        f"max |issuance$_t$ - retention$_{{t-1}}$| = {residual:.2e}\n"
        "The curves coincide by construction of the issuance rule,\n"
        "which is the content of the claim rather than a fitted result.",
        loc="lower right",
    )

    fig.tight_layout()
    return save(fig, FIGURES / "a0_fig2_two_ratios.png"), h


# ---------------------------------------------------------------------------
# figure 3: quantity versus topology
# ---------------------------------------------------------------------------


def figure_3(base: EconomyConfig) -> tuple[Path, dict[str, list[float]]]:
    spend_inflow, spend_churn = [], []
    for p in TOP_PROPENSITIES:
        h = run(variant(base, spend=base.spend.with_top_propensity(p)))
        spend_inflow.append(h.tail_mean("active_claims", TAIL))
        spend_churn.append(h.tail_mean("layer1_churn", TAIL))

    edge_inflow = []
    for w in DOWNWARD_EDGES:
        h = run(variant(base, adjacency=base.adjacency.with_downward_edge(w)))
        edge_inflow.append(h.tail_mean("active_claims", TAIL))

    baseline = spend_inflow[TOP_PROPENSITIES.index(0.5)]

    fig, (ax_q, ax_t) = plt.subplots(1, 2, figsize=(10.6, 4.4))

    # -- left: quantity
    ax_q.plot(
        TOP_PROPENSITIES,
        spend_inflow,
        color=COLOR_LAYER2,
        marker="o",
        markersize=4.5,
        label="claims landing in Layer 2",
    )
    ax_q.set_xlabel("top stratum spending propensity")
    ax_q.set_ylabel("claims per round, Layer 2 inflow", color=COLOR_LAYER2)
    ax_q.tick_params(axis="y", labelcolor=COLOR_LAYER2)
    ax_q.set_ylim(0, max(spend_inflow) * 1.9)
    ax_q.set_title("Quantity: spend twentyfold more, nothing arrives")

    ax_q2 = ax_q.twinx()
    ax_q2.plot(
        TOP_PROPENSITIES,
        spend_churn,
        color=COLOR_LAYER1,
        marker="s",
        markersize=4,
        linestyle="--",
        label="circulation inside Layer 1",
    )
    ax_q2.set_ylabel("claims per round, Layer 1 churn", color=COLOR_LAYER1)
    ax_q2.tick_params(axis="y", labelcolor=COLOR_LAYER1)
    ax_q2.spines["top"].set_visible(False)
    ax_q2.grid(False)

    handles = ax_q.get_lines() + ax_q2.get_lines()
    ax_q.legend(handles, [h.get_label() for h in handles], loc="upper center")
    annotate(
        ax_q,
        "Blue is flat to floating-point equality above 0.05.\n"
        "Below it the intermediate stratum cannot fund payroll,\n"
        "so the wage edge narrows and inflow falls. More spending\n"
        "never helps beyond that threshold.",
        loc="lower right",
    )

    # -- right: topology
    ax_t.plot(
        DOWNWARD_EDGES,
        edge_inflow,
        color=COLOR_ACCENT,
        marker="o",
        markersize=4.5,
    )
    ax_t.axhline(
        baseline,
        color=COLOR_INSTRUMENT,
        linestyle=":",
        linewidth=1.2,
        label="closed-topology level (left panel)",
    )
    ax_t.set_xlabel("weight of one downward edge into Layer 2")
    ax_t.set_ylabel("claims per round, Layer 2 inflow")
    ax_t.set_ylim(0, max(edge_inflow) * 1.15)
    ax_t.set_title("Topology: open one edge, everything arrives")
    ax_t.legend(loc="upper left")

    # The jump between a closed edge and a barely-open one is the whole point,
    # so it is marked rather than left for the reader to notice.
    jump = edge_inflow[1] / edge_inflow[0]
    rest = edge_inflow[-1] / edge_inflow[1]
    ax_t.annotate(
        f"x{jump:.2f} from opening it at all",
        xy=(DOWNWARD_EDGES[1], edge_inflow[1]),
        xytext=(0.18, 0.40),
        textcoords="axes fraction",
        fontsize=8.5,
        color="#404040",
        arrowprops={"arrowstyle": "->", "color": "#707070", "linewidth": 1.0},
    )
    annotate(
        ax_t,
        "Same spending propensity throughout; only the destination changes.\n"
        f"Opening the edge at all: x{jump:.2f}. Widening it seventeenfold\n"
        f"thereafter: x{rest:.2f}. Existence dominates magnitude, which is\n"
        "what makes the property topological rather than quantitative.",
        loc="lower right",
    )

    fig.suptitle(
        "A quantity of money does not establish access. An adjacency matrix does.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    path = save(fig, FIGURES / "a0_fig3_quantity_vs_topology.png")
    return path, {
        "top_propensity": list(TOP_PROPENSITIES),
        "spend_sweep_inflow": spend_inflow,
        "spend_sweep_churn": spend_churn,
        "downward_edge": list(DOWNWARD_EDGES),
        "edge_sweep_inflow": edge_inflow,
    }


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------


def evaluate(
    base: EconomyConfig, h1: History, h2: History, sweeps: dict[str, list[float]]
) -> list[Criterion]:
    out: list[Criterion] = []

    drift = float(h2.total_ratio[-1] - h2.total_ratio[-TAIL])
    sd = h2.tail_std("active_ratio", TAIL)
    out.append(
        Criterion(
            "A0-1  targeted ratio flat while total ratio rises",
            drift > 0 and sd < 0.05 * drift,
            f"tail sd of M_a/R_a = {sd:.3e}, M/R drift = {drift:.4f}, "
            f"threshold = {0.05 * drift:.3e}",
        )
    )

    monotone = bool(np.all(np.diff(h2.total_ratio) >= -1e-12))
    out.append(
        Criterion(
            "A0-2  M/R monotone under endogenous issuance",
            monotone,
            f"min first difference = {float(np.diff(h2.total_ratio).min()):.3e}",
        )
    )

    residual = float(np.abs(h2.issuance[1:] - h2.retention[:-1]).max())
    out.append(
        Criterion(
            "A0-3  issuance equals lagged retention",
            residual < 1e-9,
            f"max absolute residual = {residual:.3e}",
        )
    )

    inflow = sweeps["spend_sweep_inflow"]
    churn = sweeps["spend_sweep_churn"]
    props = sweeps["top_propensity"]
    keep = [i for i, p in enumerate(props) if p >= 0.05]
    flat = [inflow[i] for i in keep]
    spread = max(flat) - min(flat)
    out.append(
        Criterion(
            "A0-4  Layer 2 inflow flat across the spending sweep (propensity >= 0.05)",
            spread < 1e-9 * max(1.0, float(np.mean(flat))),
            f"spread = {spread:.3e} over propensities "
            f"{[props[i] for i in keep]}, level = {flat[0]:.6f}",
        )
    )

    churn_kept = [churn[i] for i in keep]
    ratio = max(churn_kept) / max(min(churn_kept), 1e-12)
    out.append(
        Criterion(
            "A0-5  the same sweep moves Layer 1 churn by an order of magnitude",
            ratio > 10.0,
            f"churn ranged {min(churn_kept):.2f} to {max(churn_kept):.2f}, "
            f"factor {ratio:.1f}",
        )
    )

    edges = sweeps["edge_sweep_inflow"]
    out.append(
        Criterion(
            "A0-6  opening one downward edge raises Layer 2 inflow",
            edges[-1] > 1.5 * edges[0],
            f"inflow rose from {edges[0]:.4f} at weight 0 to {edges[-1]:.4f} "
            f"at weight {DOWNWARD_EDGES[-1]}, factor {edges[-1] / edges[0]:.2f}",
        )
    )

    edge_monotone = all(b >= a - 1e-9 for a, b in pairwise(edges))
    out.append(
        Criterion(
            "A0-7  edge response monotone",
            edge_monotone,
            f"sequence = {[round(v, 3) for v in edges]}",
        )
    )

    floor = base.wages.net_downward()
    settled = h1.tail_mean("active_claims", TAIL)
    out.append(
        Criterion(
            "A0-8  production layer settles at the payroll edge rather than zero",
            settled > floor,
            f"settled inflow = {settled:.4f} against net downward wage flow "
            f"{floor:.4f}",
        )
    )

    l1_share = h2.tail_mean("layer1_share", TAIL)
    out.append(
        Criterion(
            "A0-9  issuance accumulates in the layer it was issued to",
            l1_share > 0.9,
            f"Layer 1 holds {l1_share:.4f} of all claims at steady state, "
            f"from {h2.layer1_share[0]:.4f} at t=0",
        )
    )

    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    apply_style()
    base = EconomyConfig(rounds=args.rounds, seed=args.seed)

    print("stage A0: retention and allocation")
    print(f"  rounds={base.rounds} seed={base.seed}")
    print(
        f"  retention rates sigma = {[round(s, 3) for s in base.spend.retention_rate]}"
    )
    print(f"  Layer 2 outflow / downward inflow = {base.flow_balance():.3f}")
    print(f"  net downward wage flow = {base.wages.net_downward():.3f}")
    print()

    p1, h1 = figure_1(base)
    p2, h2 = figure_2(base)
    p3, sweeps = figure_3(base)
    for p in (p1, p2, p3):
        print(f"  wrote {p.relative_to(ROOT)}")
    print()

    criteria = evaluate(base, h1, h2, sweeps)
    print("criteria")
    for c in criteria:
        print(c.line())
    print()

    n_pass = sum(c.passed for c in criteria)
    print(f"  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    record = {
        "stage": "A0",
        "rounds": base.rounds,
        "seed": base.seed,
        "parameters": {
            "strata_counts": list(base.strata.counts),
            "wealth_share": list(base.strata.wealth_share),
            "propensity_low": list(base.spend.low),
            "propensity_high": list(base.spend.high),
            "retention_rate": list(base.spend.retention_rate),
            "adjacency": [list(row) for row in base.adjacency.flow],
            "wage_bill": base.wages.bill,
            "wage_source_shares": list(base.wages.source_shares),
            "wage_dest_shares": list(base.wages.dest_shares),
            "issuance_rule": base.authority.rule,
            "issuance_gain": base.authority.gain,
            "initial_claims": base.initial_claims,
            "total_resources": base.total_resources,
        },
        "derived": {
            "flow_balance": base.flow_balance(),
            "net_downward_wage_flow": base.wages.net_downward(),
            "upward_leakage": base.adjacency.upward_leakage(),
        },
        "sweeps": sweeps,
        "criteria": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in criteria
        ],
    }
    out_path = RESULTS / "a0_retention.json"
    out_path.write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"  wrote {out_path.relative_to(ROOT)}")

    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
