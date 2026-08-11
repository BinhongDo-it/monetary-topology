"""A3 P-C: is the holonomy load-bearing, or is the mechanism reachability?

Registered in ``docs/a3_restated.md`` §4. This file evaluates and does not
design; every threshold and every reading it prints is written there.

Usage::

    python experiments/a3c_load_bearing.py
    python experiments/a3c_load_bearing.py --seeds 5 --rounds 300

Writes ``results/a3c_load_bearing.json``.

**Why this arm and not another.** P-A, that the cycle is traversed, is
established and can only fail by switching turnover off. P-B, that the algebra
survives the embedding, is close to guaranteed because the relation is an
identity; its 3.05% measures aggregation, not agreement. P-C is the only one of
the three whose outcome is not fixed by construction, and it is the only one
that can falsify the identification of the settlement ratchet with
non-integrability.

**Why the split was needed.** ``γ`` was doing two jobs, the premium paid and the
admission threshold, so ``terms_spread = 0`` zeroed the loop sum *and* levelled
the gate. One switch, two things: `MEASUREMENT.md` rule 4. ``gate_spread``
separates them.

**The trap this file has to avoid.** Lowering the payment dispersion also lowers
the **mean** acquisition cost, so the flat cell would also be the cheap cell.
``hold_mean_cost`` rescales the base terms to hold the cross-sectional mean at
the registered ``κ``, and the run reports the realised mean cost per cell so a
reader can see the hold worked rather than trust that it did.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    A3Config,
    A3Model,
    AssetSpec,
    DesignDeviation,
)
from monetary_topology.network import (  # noqa: E402
    NetworkConfig,
    NetworkSpec,
)

RESULTS = ROOT / "results"

REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300

#: The registered dispersion, and the reference the mean cost is held at.
KAPPA = 1.0

#: ``a3_restated.md`` §4.3. Payment dispersion crossed with gate dispersion.
CELLS: dict[str, dict] = {
    "both": {"terms_spread": KAPPA, "gate_spread": KAPPA},
    "H1_only": {"terms_spread": KAPPA, "gate_spread": 0.0},
    "H0_only": {"terms_spread": 0.0, "gate_spread": KAPPA},
    "null": {"terms_spread": 0.0, "gate_spread": 0.0},
}

#: Held fixed across every cell. A3b's corrections are in, because a cell
#: comparison run on a construction the repository has established cannot exist
#: would not be worth running.
FIXED = {
    "hold_mean_cost": True,
    "mean_cost_reference": KAPPA,
    "units_per_node": 1.1,
    "residual_owner": True,
    "proceeds": "seller",
}


def build(seed: int, rounds: int, **asset_kw) -> A3Model:
    spec = AssetSpec(**asset_kw)
    model = A3Model(
        A3Config(
            asset=spec,
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )
    model.run()
    return model


def terciles(
    model: A3Model, population: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """``(central third, peripheral third)`` of ``population``.

    Split on **centrality**, a property of the graph: identical across cells at
    a given seed and fixed before any treatment touches anything.

    ``population`` is passed in rather than derived here because it has to be
    the **same node set in every cell**, and no single cell knows that.
    """
    order = population[np.argsort(model.centrality[population])]
    k = max(1, order.size // 3)
    return order[-k:], order[:k]


def gap(
    model: A3Model, baseline: np.ndarray, population: np.ndarray
) -> tuple[float, float, float]:
    """``(gap, central mean, peripheral mean)``, each node against **itself**.

    **Fourth version. The three that failed are kept here because the way they
    failed is the finding.**

    *Version one* took the 90th over the 10th percentile of the production
    layer's growth multiple. The 10th percentile is zero, because the layer is
    stripped, so the ratio was infinite; and the **null cell scored above a
    treated cell**, which a floor cannot do. It was measuring who holds a unit
    and who is drained by rent — dispersion in ownership, not dispersion
    produced by terms.

    *Version two* compared the central third against the peripheral third
    within a single cell, each node over its own opening claims. Every cell came
    out **negative**: central production nodes hold systematically larger
    opening claims, so dividing by them inverts the ranking, and a peripheral
    node with a tiny denominator posts a huge growth multiple. `MEASUREMENT.md`
    rule 2 — the two sides of the comparison did not share a denominator.

    *Version three* paired each node against itself in the null cell, which
    fixed the denominator and gave an exact zero calibration, but measured the
    **production layer at round 300**. A3b established that the production layer
    holds nothing by round 200 under every construction, so that window reads
    the aftermath: terminal net worth downstairs is between `0.000` and `0.143`
    in all four cells and the differences sit in the noise floor of a layer that
    has already been stripped. `MEASUREMENT.md` rule 1 — the claim is about what
    accumulates per round trip, and the window has to contain the round trips.

    *This version* keeps the pairing and changes the population to the agents
    who **actually walk the cycle**, intersected across all four cells so the
    set is identical everywhere. P-C asks whether A3-4's object is load-bearing,
    so it measures on A3-4's population.

    Returns the gap and the two group means of the paired change.
    """
    central, peripheral = terciles(model, population)
    delta = (model.net_worth() - baseline) / np.maximum(model._claims_0, 1e-12)
    hi = float(delta[central].mean())
    lo = float(delta[peripheral].mean())
    return hi - lo, hi, lo


def gap_net_of_stretch(
    model: A3Model, baseline: A3Model, population: np.ndarray
) -> float:
    """The same gap with the stretch write-off deducted from both sides.

    Most of the paired population entered by stretching — 35 to 37 of about 42 —
    and their ``uncounted_cost`` averages around nine tenths of their opening
    claims. The registered document says of that quantity that ``net_worth``
    overstates a stretcher's position **by exactly** it, so deducting it is the
    intended use rather than a correction invented here.

    Reported beside the headline instead of replacing it. If the two disagree
    the finding is about the write-off; if they agree the write-off is not
    carrying it, and either way the reader is told rather than reassured.
    """
    central, peripheral = terciles(model, population)
    c0 = np.maximum(model._claims_0, 1e-12)
    a = model.net_worth() - model.uncounted_cost
    b = baseline.net_worth() - baseline.uncounted_cost
    delta = (a - b) / c0
    return float(delta[central].mean() - delta[peripheral].mean())


def _unused_gap_v2(model: A3Model) -> tuple[float, float, float]:
    """``(gap, central mean, peripheral mean)``. The outcome measure.

    **This replaces the first version, which was wrong, and the way it was wrong
    is worth keeping.** That one took the 90th over the 10th percentile of the
    production layer's growth multiple. Two failures showed up on the first run:
    the 10th percentile is zero, because the production layer is stripped, so
    the ratio was infinite; and the **null cell scored higher than a treated
    cell**, which is impossible for a floor. It was measuring who holds a unit
    and who is being drained by rent — dispersion in ownership, not dispersion
    produced by terms. `MEASUREMENT.md` would call it a population error: the
    quantity was not the one the name claimed.

    The measure now splits on **centrality**, which is a property of the graph,
    identical across cells and fixed before any treatment. Terciles: the most
    central third of the production layer against the least central third. In
    the full cell those are the well-termed and the badly-termed; in the
    ``H0_only`` cell they have identical terms and differ only in the gate.

    Each node's terminal net worth is divided by **its own opening claims** and
    the two group **means** are then subtracted. A difference and not a ratio,
    for the reason recorded in `a3_asset_channel.md` §9.13: a ratio puts a
    treated quantity in a denominator.

    The null cell is **not** expected to be zero. Centrality drives the
    underlying A2 economy through wages and adjacency whatever the asset channel
    does, so the null carries that and only that. The quantity of interest is
    each cell's excess over the null.
    """
    prod = np.flatnonzero(model._is_production)
    c = model.centrality[prod]
    k = max(1, c.size // 3)
    order = prod[np.argsort(c)]
    peripheral, central = order[:k], order[-k:]
    grown = model.net_worth() / np.maximum(model._claims_0, 1e-12)
    hi = float(grown[central].mean())
    lo = float(grown[peripheral].mean())
    return hi - lo, hi, lo


def mean_cost(model: A3Model) -> float:
    """Realised mean acquisition cost, to show the hold in §4.4 worked."""
    p = np.asarray(model.a3.asset.initial_price, dtype=float)
    return float((model.terms * p[None, :]).mean())


def build_all(seeds: range, rounds: int) -> tuple[dict, dict, set[str]]:
    """Every cell at every seed, plus the population they share.

    Two things have to happen before any number is taken and neither can be
    done cell by cell.

    The **null is built twice**, once as the baseline every other cell is
    subtracted from and once as an ordinary row. Aliasing the two would make the
    zero-calibration row a tautology; built separately it is two independent
    executions of one configuration and must return exactly zero.

    The **population is the intersection** of the agents who complete at least
    one round trip in *every* cell. An agent that trades in one cell and not
    another is not a paired observation, and letting the set move with the
    treatment is the population error `MEASUREMENT.md` rule 5 exists for. The
    number dropped to form the intersection is reported.
    """
    models: dict[tuple[str, int], A3Model] = {}
    devs: set[str] = set()
    for seed in seeds:
        for name, kw in CELLS.items():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", DesignDeviation)
                m = build(seed, rounds, **FIXED, **kw)
            devs |= {str(w.message).split(".")[0] for w in caught}
            devs |= set(m.deviations)
            models[(name, seed)] = m
    population: dict[int, np.ndarray] = {}
    dropped = 0
    for seed in seeds:
        shared = np.ones(models[("null", seed)]._n, dtype=bool)
        for name in CELLS:
            shared &= models[(name, seed)].cycles > 0
        any_cell = np.zeros_like(shared)
        for name in CELLS:
            any_cell |= models[(name, seed)].cycles > 0
        dropped += int(any_cell.sum() - shared.sum())
        population[seed] = np.flatnonzero(shared)
    return models, population, devs | {f"__dropped__{dropped}"}


def summarise(
    name: str,
    kw: dict,
    seeds: range,
    models: dict,
    baseline: dict[int, A3Model],
    population: dict[int, np.ndarray],
) -> dict:
    gaps, nets, his, los, costs, stretched, traders = [], [], [], [], [], [], []
    for seed in seeds:
        m = models[(name, seed)]
        g, hi, lo = gap(m, baseline[seed].net_worth(), population[seed])
        nets.append(gap_net_of_stretch(m, baseline[seed], population[seed]))
        gaps.append(g)
        his.append(hi)
        los.append(lo)
        costs.append(mean_cost(m))
        stretched.append(int(m.stretched.sum()))
        traders.append(int((m.cycles > 0).sum()))
    return {
        "name": name,
        "config": kw,
        "gap_mean": float(np.mean(gaps)),
        "gap_net_of_stretch": float(np.mean(nets)),
        "gap_by_seed": [float(x) for x in gaps],
        # A mean with no dispersion beside it is the defect this file's own
        # notes accuse A4-4 of. Sign consistency is the weakest statistic that
        # can refuse an attribution, and it needs no distributional assumption.
        "same_sign_across_seeds": bool(
            all(g > 0 for g in gaps) or all(g < 0 for g in gaps)
        ),
        "gap_range": [float(min(gaps)), float(max(gaps))],
        "central_mean": float(np.mean(his)),
        "peripheral_mean": float(np.mean(los)),
        "mean_cost": float(np.mean(costs)),
        "stretched_nodes": float(np.mean(stretched)),
        "traders": float(np.mean(traders)),
        "paired_population": float(
            np.mean([population[s].size for s in seeds])
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)

    print("A3 P-C: is the holonomy load-bearing?\n")
    print(f"  {args.seeds} seeds, {args.rounds} rounds, mean cost held at "
          f"kappa = {KAPPA}")

    # The null is built first and separately, and every other cell is measured
    # against it node by node. Building it twice rather than aliasing it is
    # deliberate: the null row then reports two independent executions of the
    # same configuration and must come out at exactly zero, which is the zero
    # calibration. Aliasing would make that row a tautology.
    models, population, devset = build_all(seeds, args.rounds)
    dropped = next(
        int(d.split("__")[-1]) for d in devset if d.startswith("__dropped__")
    )
    devset = {d for d in devset if not d.startswith("__dropped__")}
    baseline = {
        s: build(s, args.rounds, **FIXED, **CELLS["null"]) for s in seeds
    }
    cells = {
        n: summarise(n, kw, seeds, models, baseline, population)
        for n, kw in CELLS.items()
    }
    for c in cells.values():
        c["deviations"] = sorted(devset)

    print("\n  cell         k_pay  k_gate       gap  net of stretch   central"
          "  periph  mean cost")
    for n, c in cells.items():
        print(f"  {n:11s}  {c['config']['terms_spread']:5.1f}"
              f"  {c['config']['gate_spread']:6.1f}"
              f"  {c['gap_mean']:8.3f}  {c['gap_net_of_stretch']:14.3f}"
              f"  {c['central_mean']:8.3f}  {c['peripheral_mean']:6.3f}"
              f"  {c['mean_cost']:9.4f}")
    print("\n  gap: every node is paired against itself in the null cell, the "
          "change divided by\n  its own opening claims, then the mean over the "
          "most central third minus the mean\n  over the least central third. "
          "Population is the agents completing a round trip in\n  every cell: "
          f"{cells['both']['paired_population']:.1f} nodes, {dropped} dropped "
          "to form the intersection. The null row\n  is the zero calibration "
          "and must read exactly 0.")

    both = cells["both"]["gap_mean"]
    null = cells["null"]["gap_mean"]
    h1 = cells["H1_only"]["gap_mean"]
    h0 = cells["H0_only"]["gap_mean"]

    # The hold on the mean cost is the precondition for reading anything.
    costs = [c["mean_cost"] for c in cells.values()]
    cost_drift = (max(costs) - min(costs)) / max(min(costs), 1e-12)
    print(f"\n  mean-cost hold: worst relative drift across cells "
          f"{cost_drift:.2e}")

    print("\n  reading, per a3_restated.md §4.3 and §6")
    verdict = []
    if cost_drift > 0.01:
        verdict.append(
            "VOID: the mean acquisition cost is not held across cells, so they "
            "differ in level as well as dispersion and no comparison is valid"
        )
    if abs(null) > 1e-12:
        verdict.append(
            f"VOID: the zero calibration reads {null:.3e} rather than zero, so "
            "the harness is wrong whatever the other cells say"
        )
    if abs(both) < 1e-9:
        verdict.append(
            "VOID: the full cell moves nothing against the null, so there is "
            "no gap for the single-channel cells to decompose"
        )
    if not verdict:
        print(f"    both channels on: gap {both:+.4f}")
        print(f"    loop sum removed: gap {h0:+.4f}  -- what is left is H0")
        print(f"    gate removed:     gap {h1:+.4f}  -- what is left is H1")
        for n in ("both", "H1_only", "H0_only"):
            c = cells[n]
            mark = "same sign" if c["same_sign_across_seeds"] else "SIGN FLIPS"
            print(f"      {n:9s} across seeds: {mark}, range "
                  f"[{c['gap_range'][0]:+.2f}, {c['gap_range'][1]:+.2f}]")
        unstable = [
            n
            for n in ("H1_only", "H0_only")
            if not cells[n]["same_sign_across_seeds"]
        ]
        for n in unstable:
            channel = "loop sum" if n == "H1_only" else "gate"
            verdict.append(
                f"the {channel} channel's gap changes sign across seeds, so "
                f"its contribution is NOT DISTINGUISHABLE FROM ZERO and no "
                f"share may be quoted for it"
            )
        if not unstable:
            share_h1 = (both - h0) / both
            share_h0 = (both - h1) / both
            print(f"    attributable to H1 (loop sum): {share_h1:+.1%};"
                  f"  to H0 (gate): {share_h0:+.1%}")
            verdict.append(
                "shares are of the gap between the full cell and the null, "
                "and they need not sum to one: anything left over is "
                "interaction, which §6 requires be reported as interaction "
                "rather than attributed"
            )
    for v in verdict:
        print(f"    {v}")

    devs = sorted({d for c in cells.values() for d in c["deviations"]})
    if devs:
        print("\n  deviations reported by the model:")
        for d in devs:
            print(f"    {d}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    registered = (
        args.seeds == REGISTERED_SEEDS and args.rounds == REGISTERED_ROUNDS
    )
    out = RESULTS / (
        "a3c_load_bearing.json"
        if registered
        else f"a3c_load_bearing.offparam_{args.seeds}x{args.rounds}.json"
    )
    if not registered:
        print(f"\n  off-parameter run against the registered "
              f"{REGISTERED_SEEDS}x{REGISTERED_ROUNDS}: writing beside the "
              f"registered result, not over it")
    out.write_text(
        json.dumps(
            {
                "stage": "A3 P-C",
                "seeds": args.seeds,
                "rounds": args.rounds,
                "kappa": KAPPA,
                "fixed": FIXED,
                "mean_cost_relative_drift": cost_drift,
                "cells": cells,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
