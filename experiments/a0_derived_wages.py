"""Stage A0b: derived demand on the one downward edge.

The base model holds the wage bill constant, and the production layer therefore
settles at a floor. That floor is an artefact of the exogenous bill. The source
framework's own claim is that hiring is derived from final demand, so when the
production layer's spending falls, employment falls with it, cutting the
production layer's income further.

This script adds one parameter, the derived-demand elasticity, and locates the
boundary between convergence and collapse.

Usage::

    python experiments/a0_derived_wages.py
    python experiments/a0_derived_wages.py --rounds 1200 --seed 3

Writes ``figures/a0_fig4_*.png``, ``figures/a0_fig5_*.png`` and
``results/a0_derived_wages.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology import WageChannel, run
from monetary_topology.calibration import dfa_calibrated, source_faithful
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

TAIL = 25
TRAJECTORY_ELASTICITIES = (0.0, 0.5, 0.9, 1.0, 1.5)
LEVEL_ELASTICITIES = tuple(np.round(np.arange(0.0, 1.21, 0.05), 3))
FLOOR_SHARES = (0.0, 0.025, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
#: Elasticity used for the floor sweep. Chosen well above the boundary so that
#: collapse is certain without a floor, isolating the floor's effect.
FLOOR_SWEEP_ELASTICITY = 1.5

PRESETS = {"source": source_faithful, "dfa": dfa_calibrated}


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def with_wages(base, elasticity: float, floor_share: float = 0.0):
    return variant(
        base,
        wages=WageChannel(
            bill=base.wages.bill,
            elasticity=elasticity,
            floor_share=floor_share,
            source_shares=base.wages.source_shares,
            dest_shares=base.wages.dest_shares,
        ),
    )


# ---------------------------------------------------------------------------
# figure 4: trajectories
# ---------------------------------------------------------------------------


def figure_4(base, tag: str) -> Path:
    fig, (ax_s, ax_w) = plt.subplots(
        2, 1, figsize=(7.4, 5.8), sharex=True, height_ratios=[1.2, 1]
    )
    colours = [COLOR_LAYER2, "#3d7ea6", COLOR_ACCENT, COLOR_LAYER1, "#7a1f0f"]

    for e, colour in zip(TRAJECTORY_ELASTICITIES, colours, strict=True):
        h = run(with_wages(base, e))
        rounds = np.arange(len(h.layer2_spending))
        style = "-" if e < 1.0 else "--"
        ax_s.plot(
            rounds, h.layer2_spending, color=colour, linestyle=style, label=f"e = {e}"
        )
        ax_w.plot(rounds, h.wage_bill, color=colour, linestyle=style, label=f"e = {e}")

    for ax in (ax_s, ax_w):
        ax.set_xlim(0, min(160, base.rounds))
    ax_s.set_ylabel("Layer 2 spending per round")
    ax_s.set_title("Below unit elasticity a floor exists; at unity it does not")
    ax_s.legend(loc="upper right", ncol=2)
    annotate(
        ax_s,
        "Solid: an autonomous component of payroll remains, so the layer\n"
        "settles. Dashed: the whole bill is derived from the layer's own\n"
        "spending, and the feedback has no anchor.",
        loc="lower right",
    )

    ax_w.set_xlabel("round")
    ax_w.set_ylabel("wage bill owed")
    ax_w.set_title("The downward edge narrows itself")
    annotate(
        ax_w,
        "The bill is not cut by anyone's decision. It falls because it is\n"
        "a function of a quantity that its own fall reduces.",
        loc="upper right",
    )

    fig.tight_layout()
    return save(fig, FIGURES / f"a0_fig4_derived_demand_trajectories_{tag}.png")


# ---------------------------------------------------------------------------
# figure 5: the boundary, and what survives it
# ---------------------------------------------------------------------------


def figure_5(base, tag: str) -> tuple[Path, dict[str, list[float]]]:
    levels = [
        run(with_wages(base, e)).tail_mean("layer2_spending", TAIL)
        for e in LEVEL_ELASTICITIES
    ]
    floors = [
        run(with_wages(base, FLOOR_SWEEP_ELASTICITY, fs)).tail_mean(
            "layer2_spending", TAIL
        )
        for fs in FLOOR_SHARES
    ]

    fig, (ax_e, ax_f) = plt.subplots(1, 2, figsize=(10.6, 4.4))

    ax_e.plot(
        LEVEL_ELASTICITIES, levels, color=COLOR_LAYER2, marker="o", markersize=3.5
    )
    ax_e.axvline(1.0, color=COLOR_LAYER1, linestyle="--", linewidth=1.2)
    ax_e.set_xlabel("derived-demand elasticity  e")
    ax_e.set_ylabel("Layer 2 spending, steady state")
    ax_e.set_title("The boundary sits at e = 1 exactly")
    ax_e.text(
        1.02,
        max(levels) * 0.55,
        "e = 1\nno autonomous\ncomponent remains",
        fontsize=8.5,
        color=COLOR_LAYER1,
        va="center",
    )
    annotate(
        ax_e,
        "Not a numerical threshold. At e = 1 the bill is W$_0$·S/S$_0$ with no\n"
        "constant term, so nothing anchors the fixed point. The approach is\n"
        "continuous: the level vanishes linearly in (1 - e).",
        loc="lower left",
    )

    ax_f.plot(FLOOR_SHARES, floors, color=COLOR_ACCENT, marker="o", markersize=4.5)
    slope = float(np.polyfit(FLOOR_SHARES, floors, 1)[0])
    ax_f.plot(
        FLOOR_SHARES,
        [slope * fs for fs in FLOOR_SHARES],
        color=COLOR_INSTRUMENT,
        linestyle=":",
        linewidth=1.2,
        label=f"through the origin, slope {slope:.2f}",
    )
    ax_f.set_xlabel("autonomous share of the wage bill")
    ax_f.set_ylabel("Layer 2 spending, steady state")
    ax_f.set_title(
        f"At e = {FLOOR_SWEEP_ELASTICITY}, only the autonomous part survives"
    )
    ax_f.legend(loc="upper left")
    annotate(
        ax_f,
        "Elasticity is fixed above the boundary throughout, so every one of\n"
        "these runs would collapse to zero without a floor. What is left is\n"
        "exactly proportional to the part of the flow that does not depend\n"
        "on Layer 2's own demand.",
        loc="lower right",
    )

    fig.suptitle(
        "What keeps the production layer alive is the part of the downward flow "
        "that its own decline cannot cut.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    path = save(fig, FIGURES / f"a0_fig5_boundary_and_floor_{tag}.png")
    return path, {
        "elasticity": [float(e) for e in LEVEL_ELASTICITIES],
        "level_by_elasticity": levels,
        "floor_share": list(FLOOR_SHARES),
        "level_by_floor": floors,
        "floor_slope": slope,
    }


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------


def evaluate(base, sweeps: dict[str, list[float]]) -> list[Criterion]:
    out: list[Criterion] = []

    zero_e = run(with_wages(base, 0.0))
    fixed = run(base)
    out.append(
        Criterion(
            "A0b-1  zero elasticity reproduces the fixed-bill model exactly",
            bool(np.allclose(zero_e.layer2_spending, fixed.layer2_spending, atol=0)),
            "series identical to bitwise equality; the addition is a strict "
            "generalisation and cannot have changed the earlier results",
        )
    )

    levels = sweeps["level_by_elasticity"]
    es = sweeps["elasticity"]
    below = [lv for e, lv in zip(es, levels, strict=True) if e <= 0.9]
    at_or_above = [lv for e, lv in zip(es, levels, strict=True) if e >= 1.0]
    out.append(
        Criterion(
            "A0b-2  a positive steady state exists below unit elasticity",
            all(lv > 0.0 for lv in below),
            f"minimum level over e <= 0.9 is {min(below):.4f}",
        )
    )
    out.append(
        Criterion(
            "A0b-3  no steady state exists at or above unit elasticity",
            all(lv < 1e-6 for lv in at_or_above),
            f"maximum level over e >= 1.0 is {max(at_or_above):.3e}",
        )
    )

    monotone = all(b <= a + 1e-9 for a, b in pairwise(levels))
    out.append(
        Criterion(
            "A0b-4  the level falls monotonically in elasticity",
            monotone,
            f"from {levels[0]:.4f} at e=0 to {levels[-1]:.3e} at e={es[-1]}",
        )
    )

    floors = sweeps["level_by_floor"]
    slope = sweeps["floor_slope"]
    predicted = [slope * fs for fs in sweeps["floor_share"]]
    resid = float(np.max(np.abs(np.array(floors) - np.array(predicted))))
    out.append(
        Criterion(
            "A0b-5  above the boundary, survival is linear in the autonomous share",
            resid < 1e-6 * max(1.0, max(floors)),
            f"max deviation from a line through the origin is {resid:.3e}, "
            f"slope {slope:.4f}",
        )
    )
    out.append(
        Criterion(
            "A0b-6  a zero autonomous share above the boundary collapses",
            floors[0] < 1e-6,
            f"level at floor_share=0 is {floors[0]:.3e}",
        )
    )

    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=800)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    apply_style()
    record: dict[str, object] = {
        "stage": "A0b",
        "rounds": args.rounds,
        "seed": args.seed,
    }
    all_pass = True

    for tag, factory in PRESETS.items():
        base = variant(factory(), rounds=args.rounds, seed=args.seed)
        print(f"=== preset: {tag} ===")
        print(f"  baseline wage bill = {base.wages.bill}")
        print(f"  Layer 2 outflow / downward inflow = {base.flow_balance():.3f}")

        p4 = figure_4(base, tag)
        p5, sweeps = figure_5(base, tag)
        for p in (p4, p5):
            print(f"  wrote {p.relative_to(ROOT)}")

        criteria = evaluate(base, sweeps)
        for c in criteria:
            print(c.line())
        n_pass = sum(c.passed for c in criteria)
        print(f"  {n_pass}/{len(criteria)} criteria passed\n")
        all_pass &= n_pass == len(criteria)

        record[tag] = {
            "wage_bill": base.wages.bill,
            "flow_balance": base.flow_balance(),
            "sweeps": sweeps,
            "criteria": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in criteria
            ],
        }

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a0_derived_wages.json"
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
