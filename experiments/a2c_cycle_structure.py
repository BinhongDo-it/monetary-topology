"""Stage A2c: cycle structure of the realized circulation graph.

Measures, on runs stage A2 already produces, the object Volume II's
non-integrability argument is about: cycle structure. Nothing new is simulated
and no price field is invented. See ``topology.py`` for what this can and cannot
license.

Usage::

    python experiments/a2c_cycle_structure.py
    python experiments/a2c_cycle_structure.py --rounds 800 --seeds 6

Writes ``figures/a2c_fig9..10_*.png`` and ``results/a2c_cycle_structure.json``.
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
from monetary_topology.network import NetworkConfig, NetworkSpec, run_network
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)
from monetary_topology.topology import (
    cycle_rank,
    hodge_decomposition,
    incidence_matrix,
    net_flow_vector,
    realized_adjacency,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

SNAPSHOT_EVERY = 50
AUTONOMOUS_EDGES = (0, 1, 2, 5, 12, 30)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def go(spec: NetworkSpec, *, rule="endogenous", rounds: int, seed: int):
    return run_network(
        NetworkConfig(
            spec=spec,
            rounds=rounds,
            seed=seed,
            snapshot_every=SNAPSHOT_EVERY,
            authority=MonetaryAuthority(rule=rule),
            wages=WageChannel(bill=8.0, elasticity=0.0),
        )
    )


def three_layer(seed: int, edges: int = 0) -> NetworkSpec:
    return NetworkSpec(
        seed=seed,
        intermediate_size=30,
        layer2_size=150,
        financial_to_intermediate_edges=edges,
    )


def measure_ranks(history) -> dict[str, list]:
    """Cycle rank only. Exact integer combinatorics, cheap.

    Kept separate from the Hodge measurement because the decomposition costs
    orders of magnitude more and figure 10 does not need it.
    """
    rows: dict[str, list] = {"round": [], "realized_rank": []}
    for t in sorted(history.snapshots):
        realized = realized_adjacency(history.snapshots[t], history.epsilon_absolute)
        rows["round"].append(int(t))
        rows["realized_rank"].append(cycle_rank(realized))
    return rows


def measure(history) -> dict[str, list]:
    """Cycle rank and Hodge magnitudes at every snapshot.

    Magnitudes are recorded alongside shares throughout. A share can fall
    because its own component shrank or because everything else grew, and in
    this model it is usually the second, so reporting shares alone would
    misdescribe what happened.
    """
    rows: dict[str, list] = {
        "round": [],
        "realized_rank": [],
        "gradient_norm": [],
        "curl_norm": [],
        "harmonic_norm": [],
        "flow_norm": [],
        "gradient_share": [],
        "harmonic_share": [],
        "divergence_norm": [],
    }
    for t in sorted(history.snapshots):
        flow = history.snapshots[t]
        realized = realized_adjacency(flow, history.epsilon_absolute)
        split = hodge_decomposition(flow, realized)
        w = net_flow_vector(flow, realized)
        div = incidence_matrix(realized).T @ w
        g, c, h = split.energies()
        gs, _, hs = split.shares()

        rows["round"].append(int(t))
        rows["realized_rank"].append(cycle_rank(realized))
        rows["gradient_norm"].append(float(np.sqrt(g)))
        rows["curl_norm"].append(float(np.sqrt(c)))
        rows["harmonic_norm"].append(float(np.sqrt(h)))
        rows["flow_norm"].append(float(np.linalg.norm(w)))
        rows["gradient_share"].append(float(gs))
        rows["harmonic_share"].append(float(hs))
        rows["divergence_norm"].append(float(np.linalg.norm(div)))
    return rows


# ---------------------------------------------------------------------------
# figure 9: churn grows, net displacement does not
# ---------------------------------------------------------------------------


def figure_9(rounds: int, seed: int) -> tuple[Path, dict]:
    h = go(NetworkSpec(seed=seed), rounds=rounds, seed=seed)
    m = measure(h)
    t = m["round"]

    fig, (ax_n, ax_s) = plt.subplots(1, 2, figsize=(10.6, 4.6))

    ax_n.plot(
        t,
        m["flow_norm"],
        color=COLOR_LAYER1,
        marker="o",
        markersize=3.5,
        label="net flow, all components",
    )
    ax_n.plot(
        t,
        m["gradient_norm"],
        color=COLOR_LAYER2,
        marker="s",
        markersize=3.5,
        label="gradient component",
    )
    ax_n.plot(
        t,
        m["harmonic_norm"],
        color=COLOR_ACCENT,
        marker="^",
        markersize=3.5,
        label="harmonic component",
    )
    ax_n.set_yscale("log")
    ax_n.set_xlabel("round")
    ax_n.set_ylabel("magnitude, log scale")
    ax_n.set_title("Magnitudes: only one of them grows")
    ax_n.legend(loc="center right")
    annotate(
        ax_n,
        "The gradient component is the part of circulation that actually moves\n"
        "claims from one place to another. It is flat. What grows is the part\n"
        "that returns to where it came from.",
        loc="lower left",
    )

    ratio = np.array(m["flow_norm"]) / np.maximum(np.array(m["gradient_norm"]), 1e-30)
    ax_s.plot(t, ratio, color=COLOR_INSTRUMENT, marker="o", markersize=4)
    ax_s.set_yscale("log")
    ax_s.set_xlabel("round")
    ax_s.set_ylabel("circulation / net displacement")
    ax_s.set_title("Book velocity against topological displacement")
    annotate(
        ax_s,
        f"Rises from {ratio[0]:.1f} to {ratio[-1]:.0f} over the run.\n"
        "This is the framework's claim that intra-layer spending has non-zero\n"
        "book velocity and zero topological displacement, stated for the whole\n"
        "economy as one number rather than asserted about one stratum.",
        loc="lower right",
    )

    fig.tight_layout()
    path = save(fig, FIGURES / "a2c_fig9_churn_versus_displacement.png")
    return path, {
        "two_layer": m,
        "ratio_start": float(ratio[0]),
        "ratio_end": float(ratio[-1]),
    }


# ---------------------------------------------------------------------------
# figure 10: cycle rank collapses with nothing deleted
# ---------------------------------------------------------------------------


def figure_10(rounds: int, seed: int) -> tuple[Path, dict]:
    series: dict[int, dict] = {}
    potentials: dict[int, int] = {}
    for k in AUTONOMOUS_EDGES:
        spec = three_layer(seed, k)
        h = go(spec, rounds=rounds, seed=seed)
        potentials[k] = cycle_rank(h.adjacency)
        series[k] = measure_ranks(h)

    fig, (ax_t, ax_k) = plt.subplots(1, 2, figsize=(10.6, 4.6))

    for k, colour in ((0, COLOR_LAYER1), (1, COLOR_ACCENT), (30, COLOR_LAYER2)):
        m = series[k]
        ax_t.plot(
            m["round"],
            np.array(m["realized_rank"]) / potentials[k],
            color=colour,
            marker="o",
            markersize=3.5,
            label=f"{k} autonomous edge" + ("" if k == 1 else "s"),
        )
    ax_t.axhline(1.0, color=COLOR_INSTRUMENT, linestyle=":", linewidth=1.0)
    ax_t.set_xlabel("round")
    ax_t.set_ylabel("realized cycle rank / potential")
    ax_t.set_ylim(0, 1.08)
    ax_t.set_title("Independent loops surviving in circulation")
    ax_t.legend(loc="center right")
    annotate(
        ax_t,
        "The potential graph is unchanged throughout: no edge is deleted, no\n"
        "transaction is forbidden, no price is refused. Loops disappear only\n"
        "because nothing traverses them.",
        loc="lower left",
    )

    finals = [series[k]["realized_rank"][-1] / potentials[k] for k in AUTONOMOUS_EDGES]
    ax_k.plot(AUTONOMOUS_EDGES, finals, color=COLOR_ACCENT, marker="o", markersize=5)
    ax_k.set_xlabel("edges from the financial layer into the intermediary")
    ax_k.set_ylabel("surviving fraction of cycle rank")
    ax_k.set_ylim(0, 1.0)
    ax_k.set_title("The same discontinuity, in topological terms")
    annotate(
        ax_k,
        f"Zero edges leaves {finals[0]:.1%} of the loop structure. One edge leaves\n"
        f"{finals[1]:.0%}. This is the stage A2 result restated: what the economy\n"
        "loses when the intermediary is cut off is not volume, it is the\n"
        "independent paths circulation could take.",
        loc="lower right",
    )

    fig.suptitle(
        "Potential cycle rank "
        f"{potentials[0]}, realized {series[0]['realized_rank'][-1]}, "
        "with nothing deleted.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    path = save(fig, FIGURES / "a2c_fig10_cycle_rank_collapse.png")
    return path, {
        "potential_rank": potentials,
        "final_fraction": dict(
            zip([str(k) for k in AUTONOMOUS_EDGES], finals, strict=True)
        ),
        "series": {str(k): v for k, v in series.items()},
    }


# ---------------------------------------------------------------------------


def evaluate(rounds: int, seeds: int, f9: dict, f10: dict) -> list[Criterion]:
    out: list[Criterion] = []
    m = f9["two_layer"]

    out.append(
        Criterion(
            "A2c-1  net displacement is flat while circulation grows",
            max(m["gradient_norm"]) / min(m["gradient_norm"]) < 3.0
            and m["flow_norm"][-1] / m["flow_norm"][0] > 10.0,
            f"gradient magnitude stays within a factor of "
            f"{max(m['gradient_norm']) / min(m['gradient_norm']):.2f}; total flow "
            f"grows x{m['flow_norm'][-1] / m['flow_norm'][0]:.1f}",
        )
    )
    out.append(
        Criterion(
            "A2c-2  the churn ratio rises by an order of magnitude",
            f9["ratio_end"] / f9["ratio_start"] > 10.0,
            f"circulation over net displacement rises "
            f"{f9['ratio_start']:.1f} -> {f9['ratio_end']:.0f}",
        )
    )
    out.append(
        Criterion(
            "A2c-3  the harmonic component is diluted, not removed",
            max(m["harmonic_norm"]) / min(m["harmonic_norm"]) < 3.0
            and m["harmonic_share"][-1] < 0.1 * m["harmonic_share"][0],
            f"magnitude within a factor of "
            f"{max(m['harmonic_norm']) / min(m['harmonic_norm']):.2f} while its "
            f"share falls {m['harmonic_share'][0]:.2e} -> "
            f"{m['harmonic_share'][-1]:.2e}. Reporting the share alone would have "
            "said it vanished",
        )
    )

    frac = f10["final_fraction"]
    out.append(
        Criterion(
            "A2c-4  cycle rank collapses with no edge deleted",
            frac["0"] < 0.10,
            f"potential rank {f10['potential_rank'][0]}, realized fraction "
            f"{frac['0']:.3f}, and the potential graph is identical throughout",
        )
    )
    out.append(
        Criterion(
            "A2c-5  one autonomous edge restores most of the loop structure",
            frac["1"] > 0.5,
            f"0 edges {frac['0']:.3f}, 1 edge {frac['1']:.3f}, "
            f"30 edges {frac['30']:.3f}",
        )
    )

    # cross-seed
    collapsed, rescued = [], []
    for gs in range(seeds):
        a = go(three_layer(gs, 0), rounds=rounds, seed=gs)
        b = go(three_layer(gs, 1), rounds=rounds, seed=gs)
        collapsed.append(
            cycle_rank(
                realized_adjacency(a.snapshots[max(a.snapshots)], a.epsilon_absolute)
            )
            / cycle_rank(a.adjacency)
        )
        rescued.append(
            cycle_rank(
                realized_adjacency(b.snapshots[max(b.snapshots)], b.epsilon_absolute)
            )
            / cycle_rank(b.adjacency)
        )
    out.append(
        Criterion(
            "A2c-6  the collapse and the rescue hold across graph seeds",
            max(collapsed) < 0.10 and min(rescued) > 0.5,
            f"{seeds} seeds: collapsed {min(collapsed):.3f}-{max(collapsed):.3f}, "
            f"rescued {min(rescued):.3f}-{max(rescued):.3f}",
        )
    )

    # the honest limitation
    two = go(NetworkSpec(seed=0), rounds=rounds, seed=0)
    ranks = [
        cycle_rank(realized_adjacency(two.snapshots[t], two.epsilon_absolute))
        for t in sorted(two.snapshots)
    ]
    out.append(
        Criterion(
            "A2c-7  limitation recorded: cycle rank saturates when nothing dies",
            max(ranks[1:]) - min(ranks[1:]) <= 1,
            f"in the two-layer model the realized rank is flat at {ranks[-1]} after "
            f"the transient, against a potential {cycle_rank(two.adjacency)}. Cycle "
            "rank is a binary count, so it moves only where edges genuinely stop "
            "carrying claims. It is informative in the three-layer economy and "
            "inert in the two-layer one, and this criterion exists to keep that "
            "on the record",
        )
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=600)
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    apply_style()
    print("stage A2c: cycle structure")
    print(f"  rounds={args.rounds} seeds={args.seeds}\n")

    p9, f9 = figure_9(args.rounds, args.seed)
    p10, f10 = figure_10(args.rounds, args.seed)
    for p in (p9, p10):
        print(f"  wrote {p.relative_to(ROOT)}")
    print()

    criteria = evaluate(args.rounds, args.seeds, f9, f10)
    print("criteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a2c_cycle_structure.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A2c",
                "rounds": args.rounds,
                "seed": args.seed,
                "seeds_tested": args.seeds,
                "churn": {k: v for k, v in f9.items() if k != "two_layer"},
                "cycle_rank": {
                    "potential_rank": {
                        str(k): v for k, v in f10["potential_rank"].items()
                    },
                    "final_fraction": f10["final_fraction"],
                },
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
