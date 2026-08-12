"""Stage A2: support-set contraction, and the intermediate layer.

Runs every A2 figure and criterion. Usage::

    python experiments/a2_support_contraction.py
    python experiments/a2_support_contraction.py --rounds 800 --seeds 12

Writes ``figures/a2_fig6..8_*.png`` and ``results/a2_support_contraction.json``.
Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import (
    Network,
    NetworkConfig,
    NetworkSpec,
    run_network,
)
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

TAIL = 25
AUTONOMOUS_EDGES = (0, 1, 2, 3, 5, 8, 12, 20, 30)
ELASTICITIES = (0.0, 0.5, 0.9, 0.99, 1.0)
INTERMEDIATE_SIZE = 30


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def two_layer(seed: int = 0, **kw: object) -> NetworkSpec:
    return NetworkSpec(seed=seed, **kw)  # type: ignore[arg-type]


def three_layer(
    seed: int = 0, size: int = INTERMEDIATE_SIZE, **kw: object
) -> NetworkSpec:
    return NetworkSpec(
        seed=seed,
        intermediate_size=size,
        layer2_size=180 - size,
        **kw,  # type: ignore[arg-type]
    )


def go(
    spec: NetworkSpec,
    *,
    rule: str = "endogenous",
    e: float = 0.0,
    rounds: int,
    seed: int,
):
    return run_network(
        NetworkConfig(
            spec=spec,
            rounds=rounds,
            seed=seed,
            authority=MonetaryAuthority(rule=rule),
            wages=WageChannel(bill=8.0, elasticity=e),
        )
    )


# ---------------------------------------------------------------------------
# figure 6: the injection breaks the sign relationship
# ---------------------------------------------------------------------------


def figure_6(rounds: int, seed: int) -> tuple[Path, dict]:
    off = go(two_layer(seed), rule="none", rounds=rounds, seed=seed)
    on = go(two_layer(seed), rule="endogenous", rounds=rounds, seed=seed)
    t = np.arange(rounds)

    # Shared y-axis: the contrast is the whole figure, and two independent
    # scales would let the left panel's tiny movements look like the right
    # panel's large ones.
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6), sharey=True)
    for ax, h, title in (
        (axes[0], off, "No issuance"),
        (axes[1], on, "Issuance, targeting the active pool"),
    ):
        ax.plot(
            t,
            h.total_volume / h.total_volume[0],
            color=COLOR_LAYER1,
            label="total transaction volume",
        )
        ax.plot(
            t,
            h.effective_support / h.effective_support[0],
            color=COLOR_LAYER2,
            label="effective support  (1 / HHI of inflow)",
        )
        ax.axhline(1.0, color=COLOR_INSTRUMENT, linewidth=0.9, linestyle=":")
        ax.set_yscale("log")
        ax.set_ylim(0.25, 80)
        ax.set_xlabel("round")
        ax.set_title(title)
        ax.legend(loc="upper left")
    axes[0].set_ylabel("indexed to round 0, log scale")

    v_off, s_off = off.divergence
    v_on, s_on = on.divergence
    annotate(
        axes[0],
        f"volume x{v_off:.2f}, support x{s_off:.2f}.\n"
        "Both fall. The aggregate and the topology agree,\n"
        "so a flow statistic still carries information.",
        loc="lower right",
    )
    annotate(
        axes[1],
        f"volume x{v_on:.1f}, support x{s_on:.2f}.\n"
        "Opposite signs. The production layer goes from\n"
        f"{off.layer2_inflow[0] / off.total_volume[0]:.0%} of all circulation to "
        f"{on.layer2_inflow[-1] / on.total_volume[-1]:.1%}.",
        loc="lower left",
    )

    fig.suptitle(
        "The injection is what breaks the sign relation between the aggregate "
        "and the topology.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    path = save(fig, FIGURES / "a2_fig6_injection_breaks_the_sign.png")
    return path, {
        "no_issuance": {"volume": v_off, "support": s_off},
        "issuance": {"volume": v_on, "support": s_on},
        "l2_flow_share_end_no_issuance": float(
            off.layer2_inflow[-1] / off.total_volume[-1]
        ),
        "l2_flow_share_end_issuance": float(on.layer2_inflow[-1] / on.total_volume[-1]),
    }


# ---------------------------------------------------------------------------
# figure 7: the intermediate closes the channel it operates
# ---------------------------------------------------------------------------


def figure_7(rounds: int, seed: int) -> tuple[Path, dict]:
    two = go(two_layer(seed), rounds=rounds, seed=seed)
    three = go(three_layer(seed), rounds=rounds, seed=seed)
    t = np.arange(rounds)

    fig, (ax_fund, ax_h2) = plt.subplots(1, 2, figsize=(10.6, 4.6))

    ax_fund.plot(
        t, two.wage_owed, color=COLOR_INSTRUMENT, linestyle="--", label="bill owed"
    )
    ax_fund.plot(t, two.wage_paid, color=COLOR_LAYER2, label="paid, two-layer")
    ax_fund.plot(t, three.wage_paid, color=COLOR_LAYER1, label="paid, three-layer")
    ax_fund.set_xlim(0, min(120, rounds))
    ax_fund.set_xlabel("round")
    ax_fund.set_ylabel("claims per round")
    ax_fund.set_title("The payroll channel closes itself")
    ax_fund.legend(loc="center right")
    annotate(
        ax_fund,
        "Elasticity is zero in both runs, so the rule never cuts the bill:\n"
        "the dashed line is flat. In the three-layer economy the entity that\n"
        "operates the channel is being drained upward at the same time, and\n"
        "eventually cannot fund what it owes. Nobody decided this.",
        loc="upper right",
    )

    levels = [
        go(two_layer(seed), e=e, rounds=rounds, seed=seed).layer2_inflow[-TAIL:].mean()
        for e in ELASTICITIES
    ]
    three_level = float(three.layer2_inflow[-TAIL:].mean())

    ax_h2.plot(
        ELASTICITIES,
        levels,
        color=COLOR_LAYER2,
        marker="o",
        markersize=5,
        label="two-layer, varying elasticity",
    )
    ax_h2.axhline(
        three_level,
        color=COLOR_LAYER1,
        linestyle="--",
        linewidth=1.4,
        label="three-layer at elasticity = 0",
    )
    ax_h2.set_xlabel("derived-demand elasticity of the two-layer model")
    ax_h2.set_ylabel("household inflow, steady state")
    ax_h2.set_title("Structure puts the system where a parameter would have to")
    ax_h2.legend(loc="upper right")
    annotate(
        ax_h2,
        "The three-layer economy has its elasticity set to zero and lands on\n"
        "the two-layer model's collapse boundary anyway. An intermediary that\n"
        "funds payroll out of revenue paid by the people payroll pays has no\n"
        "autonomous component left to anchor a fixed point.",
        loc="center left",
    )

    fig.tight_layout()
    path = save(fig, FIGURES / "a2_fig7_intermediate_closes_the_channel.png")
    return path, {
        "two_layer_levels_by_elasticity": dict(
            zip([str(e) for e in ELASTICITIES], levels, strict=True)
        ),
        "three_layer_level_at_zero_elasticity": three_level,
        "two_layer_funding_ratio_tail": float(two.wage_funding_ratio[-TAIL:].mean()),
        "three_layer_funding_ratio_tail": float(
            three.wage_funding_ratio[-TAIL:].mean()
        ),
    }


# ---------------------------------------------------------------------------
# figure 8: one customer in the layer above
# ---------------------------------------------------------------------------


def figure_8(rounds: int, seed: int) -> tuple[Path, dict]:
    levels, funding = [], []
    for k in AUTONOMOUS_EDGES:
        h = go(
            three_layer(seed, financial_to_intermediate_edges=k),
            rounds=rounds,
            seed=seed,
        )
        levels.append(float(h.layer2_inflow[-TAIL:].mean()))
        funding.append(float(h.wage_funding_ratio[-TAIL:].mean()))

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.plot(AUTONOMOUS_EDGES, levels, color=COLOR_ACCENT, marker="o", markersize=5)
    ax.set_xlabel("edges from the financial layer into the intermediary")
    ax.set_ylabel("household inflow, steady state")
    ax.set_ylim(0, max(levels) * 1.15)
    ax.set_title("One customer in the layer above is the whole difference")

    jump = levels[1]
    ax.annotate(
        f"one edge:\nfrom exact zero to {jump / max(levels):.0%} of the eventual level",
        xy=(1, jump),
        xytext=(0.30, 0.42),
        textcoords="axes fraction",
        fontsize=8.5,
        color="#404040",
        arrowprops={"arrowstyle": "->", "color": "#707070", "linewidth": 1.0},
    )
    annotate(
        ax,
        f"Zero edges collapses exactly. Widening from one to "
        f"{AUTONOMOUS_EDGES[-1]} adds x{levels[-1] / levels[1]:.2f}.\n"
        "The intermediary's other revenue comes from the households its own\n"
        "payroll pays, so it is not autonomous. This edge is, and it is the\n"
        "only thing standing between the economy and the boundary.",
        loc="lower right",
    )

    fig.tight_layout()
    path = save(fig, FIGURES / "a2_fig8_one_customer_above.png")
    return path, {
        "autonomous_edges": list(AUTONOMOUS_EDGES),
        "household_inflow": levels,
        "wage_funding_ratio": funding,
    }


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------


def evaluate(rounds: int, seeds: int, f6: dict, f7: dict, f8: dict) -> list[Criterion]:
    out: list[Criterion] = []

    on, off = f6["issuance"], f6["no_issuance"]
    out.append(
        Criterion(
            "A2-1  without issuance, volume and support move the same way",
            (off["volume"] - 1) * (off["support"] - 1) > 0,
            f"volume x{off['volume']:.2f}, support x{off['support']:.3f}",
        )
    )
    out.append(
        Criterion(
            "A2-2  with issuance, volume rises while support contracts",
            on["volume"] > 1 and on["support"] < 1,
            f"volume x{on['volume']:.2f}, support x{on['support']:.3f}; "
            f"production layer falls to {f6['l2_flow_share_end_issuance']:.2%} "
            "of all circulation",
        )
    )

    # cross-seed robustness of the sign flip
    flips, sames = [], []
    for gs in range(seeds):
        a = go(two_layer(gs), rule="endogenous", rounds=rounds, seed=gs).divergence
        b = go(two_layer(gs), rule="none", rounds=rounds, seed=gs).divergence
        flips.append(a[0] > 1 and a[1] < 1)
        sames.append((b[0] - 1) * (b[1] - 1) > 0)
    out.append(
        Criterion(
            "A2-3  the sign flip holds across graph seeds",
            all(flips) and all(sames),
            f"{sum(flips)}/{seeds} seeds flip under issuance, "
            f"{sum(sames)}/{seeds} agree without it",
        )
    )

    # MPC control
    severed_final = []
    for gs in range(seeds):
        cfg = NetworkConfig(spec=two_layer(gs), rounds=min(300, rounds), seed=gs)
        node = int(two_layer(gs).household_nodes[0])
        net = Network(cfg)
        net._p_low[node] = net._p_high[node] = 1.0
        net.adjacency[:, node] = 0.0
        net._route[:, node] = 0.0
        rs = net._route.sum(axis=1, keepdims=True)
        net._route = np.divide(
            net._route, rs, out=np.zeros_like(net._route), where=rs > 0
        )
        net._wage_receivers = net._wage_receivers[net._wage_receivers != node]
        severed_final.append(float(net.run().holdings[-1, node]))
    out.append(
        Criterion(
            "A2-4  a maximal propensity with no in-edge still terminates at zero",
            max(severed_final) <= 0.0,
            f"final holdings across {seeds} seeds, maximum {max(severed_final):.3e}. "
            "Propensity is a property of the agent; reachability is a property "
            "of the graph, and only the second one decides",
        )
    )

    out.append(
        Criterion(
            "A2-5  the two-layer payroll channel never narrows",
            f7["two_layer_funding_ratio_tail"] > 0.999,
            f"funding ratio {f7['two_layer_funding_ratio_tail']:.4f}",
        )
    )
    out.append(
        Criterion(
            "A2-6  H1: the three-layer payroll channel closes with the bill unchanged",
            f7["three_layer_funding_ratio_tail"] < 1e-6,
            f"funding ratio {f7['three_layer_funding_ratio_tail']:.3e} while the "
            "bill owed stayed constant and the elasticity was zero",
        )
    )

    three_level = f7["three_layer_level_at_zero_elasticity"]
    two_at_one = f7["two_layer_levels_by_elasticity"]["1.0"]
    two_at_zero = f7["two_layer_levels_by_elasticity"]["0.0"]
    out.append(
        Criterion(
            "A2-7  H2: three-layer at zero elasticity matches two-layer at unity",
            abs(three_level - two_at_one) < 1e-6 and two_at_zero > 1.0,
            f"three-layer {three_level:.4e} against two-layer at e=1 "
            f"{two_at_one:.4e} and at e=0 {two_at_zero:.4f}",
        )
    )

    inflow = f8["household_inflow"]
    out.append(
        Criterion(
            "A2-8  zero autonomous edges collapses; one rescues",
            inflow[0] < 1e-6 and inflow[1] > 0.5 * max(inflow),
            f"0 edges {inflow[0]:.3e}, 1 edge {inflow[1]:.4f} "
            f"({inflow[1] / max(inflow):.0%} of the maximum), "
            f"{AUTONOMOUS_EDGES[-1]} edges {inflow[-1]:.4f}",
        )
    )

    return out


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=600)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    apply_style()
    print("stage A2: support-set contraction")
    print(f"  rounds={args.rounds} seeds={args.seeds}\n")

    p6, f6 = figure_6(args.rounds, args.seed)
    p7, f7 = figure_7(args.rounds, args.seed)
    p8, f8 = figure_8(args.rounds, args.seed)
    for p in (p6, p7, p8):
        print(f"  wrote {p.relative_to(ROOT)}")
    print()

    criteria = evaluate(args.rounds, args.seeds, f6, f7, f8)
    print("criteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a2_support_contraction.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A2",
                "rounds": args.rounds,
                "seed": args.seed,
                "seeds_tested": args.seeds,
                "injection": f6,
                "intermediate": f7,
                "autonomous_edges": f8,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
