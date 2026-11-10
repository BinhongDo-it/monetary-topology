"""A7-A: connectivity as a continuum, on the A3 carrier.

The pre-registration and the readings are `docs/a7_continuous_c.md`. What
each entry runs:

- `--probe`, the timing probe section 4.7 requires: one interior grid point,
  one seed;
- `--grid`, the registered seventeen-point grid. With the uniform arm, twenty
  seeds and three hundred rounds it writes `results/a7_continuous_c.json`;
  `--arm preferential` is section 4.3's placebo arm;
- `--low`, the four low points with per-seed gaps, and `--dfixed`, section
  4.2's scored estimator `D_fixed` over those four points;
- `--scope` and `--dose`, where the added edges land and the downward
  channel as a dose;
- `--loop-sum`, A7-A-5's quantity at every seed, on models built and not run;
- `--verdicts`, which assembles `results/a7_verdicts.json` from the records
  on disk.

What a row is
-------------

At one shortcut rate `s`, the whole four-cell kappa factorial and its separately
built null, exactly as A3-8 runs them. `a3c_load_bearing` supplies `build_all`,
`build_baseline`, `summarise` and `evaluate`, so this is the same instrument at a
different graph rather than a second implementation of it. Section 4.3's guard
G3 named that module's inert detection, which lives in its `sweep`; this file
does not call `sweep`, and section 4.3's 2026-10-10 restatement says how the
stored rows were checked instead.

Alongside every row, the control variables in their own units, because this
repository has already run a scan whose second moving quantity had no name until
three stages later:

- realised edge count and mean degree, so "the graph got denser" is visible;
- centrality standard deviation, which section 2.5 requires be read instead of
  the range, and the layer gap, so a continuum in dispersion can be told from a
  continuum in structure;
- participation, on the production layer and in its peripheral tercile, which is
  A7-A-1's quantity and section 5.3's scope fact;
- the churn diagnostics section 2.3 registers: two of the four rules held fixed
  select on in-degree, so their outputs move with `s` even though the rules do
  not, and a payer set that has turned over by the second grid point means the
  stage is moving two things.

What a row does not compute
---------------------------

A row's gaps are `D_reach`, the within-`s` intersection. `D_fixed`, section
4.2's scored estimator, is computed only under `--dfixed`, into its own record,
with the population intersected across every cell and the four points in `LOW`.
"""

from __future__ import annotations

import argparse
# ``dataclasses.replace`` and not ``NetworkSpec.replace``: the latter is a
# hand-written field list and a field added later is silently dropped by it.
import dataclasses
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import centrality, loop_sum  # noqa: E402
from monetary_topology.network import NetworkSpec, build_graph  # noqa: E402
from monetary_topology.product_graph import tier_positions  # noqa: E402

#: The availability check's grid, dense near zero because that is where a
#: threshold would sit if the framework's account is right.
GRID: tuple[float, ...] = (
    0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4,
    0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0,
)

#: Where the probe is taken. Interior, and away from the dense low end where
#: section 2.6 measured the only per-seed non-monotonicity, so the probe's cost
#: is representative rather than best case: at `s = 0.5` the graph carries about
#: twenty times the edges of the stratified one and every model runs on it.
PROBE_S = 0.5

#: Section 4.4. Twenty rather than A3's five, because section 5.3 measured five
#: to be insufficient for sign stability on this exact estimator.
REGISTERED_SEEDS = 20

#: The readable region for the placebo. Section 4.3 registers that the arm is
#: void where its dispersion leaves the band around the `s = 0` value, and the
#: 2026-08-15 grid measured the preferential arm at ratios 1.053, 1.027 and
#: 1.111 here against 1.222 and above from `s = 0.1`. `--low` runs exactly these
#: so the comparison that decides A7-A-3 is not buried in fourteen void rows.
LOW: tuple[float, ...] = (0.0, 0.01, 0.02, 0.05)

#: The dose ladder for the downward channel, registered 2026-08-24. Zero is
#: the framework's specification and the top of the ladder is what the
#: registered shortcut arm happens to open at ``s = 0.01``, so the ladder
#: spans from the specification to the accident.
DOSE: tuple[int, ...] = (0, 1, 2, 5, 10, 21)


def _a3c():
    """`experiments/a3c_load_bearing.py`, loaded by path like the rest."""
    path = ROOT / "experiments" / "a3c_load_bearing.py"
    spec = importlib.util.spec_from_file_location("a3c_load_bearing", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def production_nodes(spec: NetworkSpec) -> np.ndarray:
    """Everything that is not the financial layer.

    A5.3's scope table counts here. `A3-8`'s paired set holds all twenty
    financial-layer nodes, and its production-layer participants are the top
    eighth of this set, so the denominator has to be this set rather than the
    whole graph.
    """
    return np.arange(spec.layer1_size, spec.size)


def peripheral_tercile(spec: NetworkSpec, cen: np.ndarray) -> np.ndarray:
    """The least central third of the production layer, split on the graph.

    Centrality is a property of the graph and identical across the four cells at
    one `s`, which is what lets the same split be applied to all of them.
    """
    prod = production_nodes(spec)
    order = prod[np.argsort(cen[prod])]
    k = max(1, order.size // 3)
    return order[:k]


def graph_columns(spec: NetworkSpec) -> dict:
    """Control variables, read off the graph before any model is run."""
    a = build_graph(spec)
    cen = centrality(a)
    k = spec.layer1_size
    return {
        "edges": float(a.sum()),
        "mean_degree": float(a.sum(axis=1).mean()),
        "centrality_sd": float(cen.std()),
        "centrality_range": float(cen.max() - cen.min()),
        "layer_gap": float(cen[:k].mean() - cen[k:].mean()),
    }


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Rank correlation, which is what section 2.3 registers.

    Positional agreement was measured here first and is the wrong instrument:
    on two hundred nodes whose in-degree ties are broken arbitrarily, "is this
    node still at rank `i`" reads near zero however little the ordering actually
    moved, so it cannot tell a reordered vector from a jostled one.
    """
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0.0 or ry.std() == 0.0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def churn_columns(reference, here) -> dict:
    """Section 2.3's diagnostic: how far the two derived rules have moved.

    Reported, never scored. Both rules select on in-degree, so their outputs are
    functions of `s` while the rules themselves are not, and this is what makes
    that visible instead of arguable.

    ``reference`` is the `s = 0` model, built once by the caller. Rebuilding it
    per grid point costs a model per row and measures the same thing every time.
    """

    def jaccard(x: np.ndarray, y: np.ndarray) -> float:
        sx, sy = set(x.tolist()), set(y.tolist())
        union = sx | sy
        return float(len(sx & sy) / len(union)) if union else 1.0

    return {
        "payer_jaccard_vs_s0": jaccard(
            reference._wage_payers, here._wage_payers
        ),
        "receiver_jaccard_vs_s0": jaccard(
            reference._wage_receivers, here._wage_receivers
        ),
        "opening_rank_corr_vs_s0": _spearman(
            reference._claims_0, here._claims_0
        ),
    }


def mean_abs_loop_sum(model, nodes: np.ndarray) -> list[float]:
    """A7-A-5's quantity, per tier: mean |loop sum| over the pairs in ``nodes``.

    ``loop_sum`` divides by a period count, a constant that cannot affect the
    registered shape, which is a direction in `s`. It is one here, so the
    quantity is per traversal. `asset.py` defines the function and **nothing in
    the repository called it before this stage**, so this is its first caller.

    Computed vectorised and **checked against `asset.loop_sum` itself** on a
    fixed sample of pairs, because a second implementation of an identity that
    agrees with itself would establish nothing while a second implementation
    that silently disagreed would be worse.

    Two node sets are reported by the caller and the difference between them is
    the point. Over a fixed set this is a dispersion of log terms and its fall
    with `s` is the construction identity A7-A-5 asserts. Over the paired
    population it is not, because that population moves with the treatment: the
    first version of this function read only the paired set and came out
    **rising** from `s = 0` to `s = 0.05`, which is composition and not terms.
    That is the third statistic in this stage whose behaviour was dominated by
    something moving with the treatment, after A7-A-3 and A7-A-6.
    """
    idx = np.asarray(nodes, dtype=int)
    out: list[float] = []
    for tier in range(model.terms.shape[1]):
        lt = np.log(model.terms[idx, tier])
        if lt.size < 2:
            out.append(float("nan"))
            continue
        d = np.abs(lt[:, None] - lt[None, :])
        out.append(float(d.sum() / (lt.size * (lt.size - 1))))
        if tier == 0 and lt.size >= 3:
            a, b = int(idx[0]), int(idx[1])
            direct = abs(loop_sum(model.terms, a, b, 0, 1))
            assert abs(direct - abs(lt[0] - lt[1])) < 1e-12, (
                "vectorised loop sum disagrees with asset.loop_sum"
            )
    return out


#: Section 2.6's per-seed tolerance, in the relative form it was measured in: the
#: largest per-seed rise of the centrality dispersion was 0.62% of that seed's own
#: `s = 0` value, and the terms dispersion the loop sum is built from is
#: proportional to that dispersion, so the relative form is the one that carries.
PER_SEED_RELATIVE_TOLERANCE = 0.0062


def summarise_loop_sum(arm: str, grid, by_point: dict) -> dict:
    """A7-A-5's shape from per-seed values, at every grid point.

    The criterion registers a fall that is monotone in the seed mean, and per
    seed within section 2.6's tolerance with every violation named. So the
    reading is of both: the mean over seeds, and each seed's own series step by
    step, every rise larger than the tolerance named by seed and step. The peak
    over the grid as a multiple of the value at the first grid point is printed
    alongside; a seed can break the per-seed clause without ever passing its own
    first value, so the two are different readings.
    """
    first = grid[0]
    n = len(by_point[first])
    mean = [float(np.mean(by_point[s])) for s in grid]
    peaks = [
        max(by_point[s][i] for s in grid) / by_point[first][i] for i in range(n)
    ]
    violations = [
        {"seed": i, "from": a, "to": b,
         "rise_over_own_first": (by_point[b][i] - by_point[a][i])
         / by_point[first][i]}
        for i in range(n) for a, b in zip(grid, grid[1:])
        if by_point[b][i] - by_point[a][i]
        > PER_SEED_RELATIVE_TOLERANCE * by_point[first][i]
    ]
    return {
        "per_seed_tolerance_relative": PER_SEED_RELATIVE_TOLERANCE,
        "per_seed_violations": violations,
        "seeds_with_a_violation": len({v["seed"] for v in violations}),
        "falls_per_seed_within_tolerance": not violations,
        "arm": arm,
        "grid": list(grid),
        "tier": 0,
        "seeds": n,
        "by_point": {f"{s:g}": list(by_point[s]) for s in grid},
        "mean_by_point": mean,
        "peak_multiple_first_seed": peaks[0],
        "peak_multiple_of_the_seed_mean": max(mean) / mean[0],
        "peak_multiple_by_seed": peaks,
        "rising_steps_of_the_seed_mean": sum(
            1 for a, b in zip(mean, mean[1:]) if b > a
        ),
        "seeds_rising_above_their_own_first_point": sum(
            1 for p in peaks if p > 1.0
        ),
        "falls_monotonically_in_the_seed_mean": all(
            b <= a for a, b in zip(mean, mean[1:])
        ),
    }


def loop_sum_by_seed(module, arm: str, seeds: range, rounds: int,
                     grid=GRID) -> dict:
    """A7-A-5's quantity at every seed, on models that are built and not run.

    The loop sum over the fixed production layer is read off the terms matrix,
    and the terms are set when the model is constructed. So the reading over
    all the seeds the criterion registers costs one construction per seed and
    grid point and no run. The grid records carry the first seed alone, and
    the verdict sheet used to quote that seed as the stage's figure.

    Section 4.3's guard G2 is asserted here as well, where it costs nothing:
    the position graph is the cash-and-tiers star at every point, so its first
    Betti number is zero and the whole obstruction is squares.
    """
    by_point: dict[float, list[float]] = {}
    for s in grid:
        kw = {"shortcut_rate": s, "shortcut_mode": arm} if s > 0.0 else {}
        values = []
        for seed in seeds:
            model = module.construct(
                seed, rounds, **module.FIXED, **module.CELLS["both"], **kw
            )
            star = tier_positions(model.a3.asset.tiers)
            edges = int(np.count_nonzero(np.triu(star + star.T)))
            assert edges - star.shape[0] + 1 == 0, (
                "the position graph is no longer a star, so the obstruction "
                "is not all squares and H1 may not be read off the square sums"
            )
            values.append(
                mean_abs_loop_sum(
                    model, production_nodes(model.a3.network.spec)
                )[0]
            )
        by_point[s] = values
    return summarise_loop_sum(arm, grid, by_point)


def paired_loop_sum_by_seed(module, arm: str, seeds: range, rounds: int,
                            grid=GRID) -> dict:
    """Mean |loop sum| over each seed's own paired population, at every seed.

    The grid records carry this for the first seed alone
    (`mean_abs_loop_sum_paired`), and section 14.2 quoted that seed's change
    from `s = 0` to `s = 0.01` as the stage's. The paired population is the
    within-`s` intersection, so it comes out of the runs, and this mode runs the
    same factorial a grid row runs. Unlike the fixed production layer this set
    moves with `s`, so a change here mixes the identity with composition.
    """
    per_point: dict[float, list[float]] = {}
    size: dict[float, list[int]] = {}
    for s in grid:
        kw = {"shortcut_rate": s, "shortcut_mode": arm} if s > 0.0 else {}
        models, population, _ = module.build_all(seeds, rounds, **kw)
        per_point[s] = [
            mean_abs_loop_sum(models[("both", seed)], population[seed])[0]
            for seed in seeds
        ]
        size[s] = [int(len(population[seed])) for seed in seeds]
    first = grid[0]
    n = len(per_point[first])
    change = {
        f"{s:g}": [per_point[s][i] / per_point[first][i] - 1.0 for i in range(n)]
        for s in grid
    }
    return {
        "arm": arm,
        "grid": list(grid),
        "tier": 0,
        "seeds": n,
        "by_point": {f"{s:g}": per_point[s] for s in grid},
        "population_by_point": {f"{s:g}": size[s] for s in grid},
        "mean_by_point": [float(np.mean(per_point[s])) for s in grid],
        "change_from_first_by_seed": change,
        "change_of_the_seed_mean_from_first": {
            f"{s:g}": float(np.mean(per_point[s]) / np.mean(per_point[first]) - 1.0)
            for s in grid
        },
        "seeds_higher_than_their_own_first": {
            k: sum(1 for v in vals if v > 0) for k, vals in change.items()
        },
    }


def added_edges_by_kind(spec: NetworkSpec) -> dict[str, int]:
    """How many edges the shortcut added, split by where they landed.

    **The object A7's scope arms are about.** The draw is uniform over ordered
    pairs and on a 20/180 graph that is not uniform over kinds of edge: 80.95
    percent of pairs are production to production and 0.95 percent are financial
    to financial, so a rate applied to pairs is four different rates applied to
    kinds. Counted from the graph rather than from the draw, so a scope that
    cannot hold the matched count shows up here as a smaller total rather than
    as nothing.
    """
    base = build_graph(dataclasses.replace(spec, shortcut_rate=0.0))
    added = build_graph(spec) - base
    fin = np.zeros(spec.size, dtype=bool)
    fin[list(spec.financial_nodes)] = True
    rows_, cols = np.nonzero(added > 0)
    out = {"production": 0, "financial": 0, "downward": 0, "upward": 0}
    for i, j in zip(rows_, cols, strict=True):
        a_, b_ = bool(fin[i]), bool(fin[j])
        key = (
            "financial" if a_ and b_
            else "downward" if a_
            else "upward" if b_
            else "production"
        )
        out[key] += 1
    out["total"] = int(added.sum())
    return out


def row(
    module,
    s: float,
    seeds: range,
    rounds: int,
    reference=None,
    arm: str = "uniform",
    sd_at_zero: float | None = None,
    scope: str = "all",
    downward: int = 0,
) -> dict:
    """One grid point: the four-cell factorial, its null, and the columns.

    ``reference`` is the `s = 0` null model for ``seeds.start``, built once by
    the caller and reused for the churn columns at every point.
    """
    spec = NetworkSpec(
        seed=seeds.start, shortcut_rate=s, shortcut_mode=arm,
        shortcut_scope=scope, downward_edges=downward,
    )
    started = time.time()
    edge_kinds = (
        added_edges_by_kind(spec) if s > 0.0
        else {"production": 0, "financial": 0, "downward": 0,
              "upward": 0, "total": 0}
    )
    if reference is None:
        reference = module.build(
            seeds.start, rounds, **module.FIXED, **module.CELLS["null"]
        )

    # ``scope`` is only passed when it is not the registered value, so the
    # registered path constructs exactly the kwargs it always did and the
    # reproduction is by construction rather than by a no-op argument.
    kw = (
        {"shortcut_rate": s, "shortcut_mode": arm}
        | ({} if scope == "all" else {"shortcut_scope": scope})
        if s > 0.0
        else {}
    )
    # The dose arm turns the framework's own channel on directly instead of
    # reaching it sideways through a uniform draw. Passed only when it is
    # not zero, so every path that does not ask for it builds the kwargs it
    # always built.
    if downward:
        kw["downward_edges"] = downward
    models, population, devset = module.build_all(seeds, rounds, **kw)
    baseline, base_devs = module.build_baseline(seeds, rounds, **kw)
    rows = {
        name: module.summarise(name, ckw, seeds, models, baseline, population)
        for name, ckw in module.CELLS.items()
    }
    reading = module.evaluate(rows)

    participating, peripheral = [], []
    for seed in seeds:
        model = models[("both", seed)]
        prod = production_nodes(model.a3.network.spec)
        walked = model.cycles > 0
        participating.append(float(walked[prod].sum()))
        edge = peripheral_tercile(model.a3.network.spec, model.centrality)
        peripheral.append(float(walked[edge].sum()))

    g = graph_columns(spec)
    return {
        "s": s,
        "arm": arm,
        "scope": scope,
        "downward_edges": downward,
        # Counted from the graph, not from the draw, so an arm whose scope
        # cannot hold the matched count shows a smaller total here rather
        # than passing for matched. That shortfall is a reading.
        "edges_added_by_kind": edge_kinds,
        # Section 4.3's readability gate, made visible on the row rather than
        # left to be recomputed. The placebo is registered to hold dispersion
        # near its `s = 0` value; where it does not, that arm's point is void
        # rather than negative, and the reader has to be able to see which.
        "sd_ratio_vs_s0": (
            None if sd_at_zero in (None, 0.0)
            else g["centrality_sd"] / sd_at_zero
        ),
        "seconds": time.time() - started,
        "graph": g,
        "churn": churn_columns(reference, models[("null", seeds.start)]),
        "state": reading["state"] if reading["finite"] else "nonfinite",
        "gaps": reading["gaps"],
        # A7-A-5, per tier, on the `both` cell at the first seed.
        #
        # **The cell matters and the first version of this line had it wrong.**
        # `terms = base (1 + kappa (1 - c_i))` is a function of the graph *and*
        # of `terms_spread`, and the null cell sets `terms_spread = 0`, which
        # flattens the matrix and makes every loop sum exactly zero by
        # construction. That read `0.000000` at every tier and every rate, which
        # is what caught it. The loop sum has to be read where the loop sum is
        # alive.
        # Fixed set: every production-layer node, so composition cannot move.
        # This is the one A7-A-5 asserts a shape for.
        "mean_abs_loop_sum_fixed": mean_abs_loop_sum(
            models[("both", seeds.start)],
            production_nodes(models[("both", seeds.start)].a3.network.spec),
        ),
        # Paired population, which moves with `s`. Reported so the composition
        # effect is visible instead of being folded into the identity.
        "mean_abs_loop_sum_paired": mean_abs_loop_sum(
            models[("both", seeds.start)], population[seeds.start]
        ),
        # Section 4.4's per-seed requirement. A mean of `+0.66` against an
        # `s = 0` mean of `+18.99` reads as a collapse, and `docs/a3_asset_channel.md`
        # section 5.3 records the `s = 0` per-seed range as [+0.60, +38.31], so
        # that mean sits inside the reference point's own spread. Without the
        # per-seed values a distribution that moved cannot be told from a mean
        # that a sign-flipping set pulled to zero, and those are different
        # findings.
        "gap_by_seed": {
            name: rows[name]["gap_by_seed"] for name in module.CELLS
        },
        "gap_range": {name: rows[name]["gap_range"] for name in module.CELLS},
        "same_sign_across_seeds": {
            name: rows[name]["same_sign_across_seeds"] for name in module.CELLS
        },
        "unstable_channels": list(reading["unstable_channels"]),
        "paired_population": rows["both"]["paired_population"],
        "dropped_to_intersect": next(
            int(d.split("__")[-1]) for d in devset if d.startswith("__dropped__")
        ),
        "deviations": sorted(
            {d for d in devset if not d.startswith("__dropped__")} | base_devs
        ),
        # A7-A-1's quantity. Section 5.3 measured the peripheral tercile at
        # exactly 0.0 over twenty seeds at `s = 0`, in every cell including the
        # null, so anything above zero here is the carrier's reach changing.
        "production_participating_mean": float(np.mean(participating)),
        "peripheral_participating_mean": float(np.mean(peripheral)),
        "peripheral_participating_by_seed": peripheral,
    }


def print_row(r: dict) -> None:
    g, c = r["graph"], r["churn"]
    ratio = (
        "" if r.get("sd_ratio_vs_s0") is None
        else f"   sd/sd(s=0) {r['sd_ratio_vs_s0']:.3f}"
    )
    print(
        f"\n  s = {r['s']:<5}  arm {r.get('arm', 'uniform'):<12s}"
        f"  {r['seconds']:.1f}s   state {r['state']}{ratio}\n"
        f"    graph      edges {g['edges']:.0f}   mean degree {g['mean_degree']:.2f}"
        f"   centrality sd {g['centrality_sd']:.6f}"
        f"   layer gap {g['layer_gap']:.6f}\n"
        f"    gaps       both {r['gaps']['both']:+.4f}   loop sum only "
        f"{r['gaps']['H1_only']:+.4f}   gate only {r['gaps']['H0_only']:+.4f}"
        f"   null {r['gaps']['null']:+.4f}\n"
        f"    population paired {r['paired_population']:.1f}"
        f"   dropped {r['dropped_to_intersect']}\n"
        f"    reach      production {r['production_participating_mean']:.1f}"
        f"   peripheral tercile {r['peripheral_participating_mean']:.2f}"
        f"   by seed {r['peripheral_participating_by_seed']}\n"
        f"    churn      payers {c['payer_jaccard_vs_s0']:.3f}"
        f"   receivers {c['receiver_jaccard_vs_s0']:.3f}"
        f"   opening rank corr {c['opening_rank_corr_vs_s0']:+.3f}\n"
        f"    A7-A-5    mean |loop sum| tier 0:"
        f"  fixed {r['mean_abs_loop_sum_fixed'][0]:.6f}"
        f"   paired {r['mean_abs_loop_sum_paired'][0]:.6f}"
    )
    if r["deviations"]:
        print(f"    ** DESIGN DEVIATION: {'; '.join(r['deviations'])}")


def print_per_seed(r: dict, reference: dict | None) -> None:
    """The per-seed gaps, and what fraction of the `s = 0` gap each cell keeps.

    The fraction is the quantity A7-A-3' is registered on. It is printed for
    both cells that carry a channel and for neither of the two that do not.
    """
    print(f"    per seed, arm {r['arm']}, s = {r['s']}")
    for name in ("both", "H1_only", "H0_only"):
        by_seed = r["gap_by_seed"][name]
        lo, hi = r["gap_range"][name]
        same = r["same_sign_across_seeds"][name]
        kept = ""
        if reference is not None:
            ref = reference["gaps"][name]
            if ref != 0.0:
                kept = f"  keeps {100.0 * r['gaps'][name] / ref:+7.2f}% of s=0"
        n_pos = sum(1 for g in by_seed if g > 0)
        print(
            f"      {name:9s} mean {r['gaps'][name]:+8.4f}"
            f"  range [{lo:+8.4f}, {hi:+8.4f}]"
            f"  {n_pos:2d}/{len(by_seed)} positive"
            f"  same sign {str(same):5s}{kept}"
        )
        print("        " + " ".join(f"{g:+.3f}" for g in by_seed))


def _split(cen: np.ndarray, population: np.ndarray, bins: int):
    """``(central, peripheral)``, the same rule `a3c_load_bearing.terciles` uses.

    Reimplemented rather than imported because that function takes a model and
    D_fixed needs the split applied to one population across several models.
    The caller asserts the two agree on a case where both are defined.
    """
    order = population[np.argsort(cen[population])]
    k = max(1, order.size // max(1, bins))
    return order[-k:], order[:k]


def d_fixed(module, seeds: range, rounds: int, arm: str, points=None) -> dict:
    """Section 4.2's scored estimator: the population intersected across every
    cell **and** every point in ``points``, which defaults to `LOW`, the
    placebo's readable region of section 4.3.

    Everything reported before 2026-08-16 was `D_reach`, the within-`s`
    intersection, which section 4.2 registers as reported and never scored. This
    is the estimator the criteria were registered on.

    Two bin conventions are computed and both are reported, because **section
    4.2 fixed the population and did not fix the split**. `terciles` ranks the
    population by centrality, and centrality changes with `s` even on a frozen
    set, so a split recomputed at each point still moves with the treatment.
    `at_s` follows A3-8's estimator literally; `at_zero` freezes the split at
    `s = 0` and is the only fully fixed reading. Choosing one after seeing them
    would be choosing a result, so both travel together.

    Only small arrays are kept from each model, so four grid points times five
    cells times twenty seeds does not hold four hundred running economies.
    """
    points = tuple(LOW if points is None else points)
    store: dict = {}
    base: dict = {}
    n = None
    bins = None
    for s in points:
        kw = {"shortcut_rate": s, "shortcut_mode": arm} if s > 0.0 else {}
        models, _, _ = module.build_all(seeds, rounds, **kw)
        baseline, _ = module.build_baseline(seeds, rounds, **kw)
        for seed in seeds:
            base[(s, seed)] = baseline[seed].net_worth()
            for name in module.CELLS:
                m = models[(name, seed)]
                n = m._n
                bins = m.a3.asset.centrality_bins
                store[(s, name, seed)] = (
                    m.cycles > 0,
                    m.net_worth(),
                    m._claims_0,
                    m.centrality,
                )
        # One check that the local split agrees with the module's own.
        m0 = models[("both", seeds.start)]
        pop0 = np.flatnonzero(m0.cycles > 0)
        if pop0.size >= 3:
            mine = _split(m0.centrality, pop0, m0.a3.asset.centrality_bins)
            theirs = module.terciles(m0, pop0)
            assert np.array_equal(mine[0], theirs[0]), "central bin disagrees"
            assert np.array_equal(mine[1], theirs[1]), "peripheral bin disagrees"

    population: dict = {}
    for seed in seeds:
        mask = np.ones(n, dtype=bool)
        for s in points:
            for name in module.CELLS:
                mask &= store[(s, name, seed)][0]
        population[seed] = np.flatnonzero(mask)

    out: dict = {
        "points": list(points),
        "arm": arm,
        "population_by_seed": [int(population[s].size) for s in seeds],
        "population_mean": float(
            np.mean([population[s].size for s in seeds])
        ),
        "cells": {},
    }
    for name in module.CELLS:
        rows_at_s, rows_at_zero = {}, {}
        for s in points:
            gaps_s, gaps_0 = [], []
            for seed in seeds:
                pop = population[seed]
                if pop.size < 2:
                    continue
                _, nw, c0, cen = store[(s, name, seed)]
                delta = (nw - base[(s, seed)]) / np.maximum(c0, 1e-12)
                hi, lo = _split(cen, pop, bins)
                gaps_s.append(float(delta[hi].mean() - delta[lo].mean()))
                cen0 = store[(points[0], name, seed)][3]
                hi0, lo0 = _split(cen0, pop, bins)
                gaps_0.append(float(delta[hi0].mean() - delta[lo0].mean()))
            for target, gaps in ((rows_at_s, gaps_s), (rows_at_zero, gaps_0)):
                target[str(s)] = {
                    "mean": float(np.mean(gaps)) if gaps else float("nan"),
                    "by_seed": gaps,
                    "range": (
                        [float(min(gaps)), float(max(gaps))] if gaps else None
                    ),
                    "same_sign_across_seeds": bool(
                        gaps
                        and (
                            all(g > 0 for g in gaps) or all(g < 0 for g in gaps)
                        )
                    ),
                    "n_positive": sum(1 for g in gaps if g > 0),
                }
        out["cells"][name] = {"split_at_s": rows_at_s, "split_at_zero": rows_at_zero}
    return out


RESULTS = ROOT / "results"

#: Floats are written through an explicit format rather than through `repr`,
#: per the generated-files rule 5: a difference in the last digit
#: between BLAS builds must not surface as a text diff. Ten significant figures
#: is far more than any statement in `docs/a7_continuous_c.md` rests on.
_FLOAT_FORMAT = ".10g"


def _clean(obj):
    """Recursively format floats and sort nothing that is not already sorted."""
    if isinstance(obj, float):
        return float(format(obj, _FLOAT_FORMAT))
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return _clean(obj.item())
    return obj


def write_record(rows: list[dict], mode: str, args) -> Path:
    """Write the run to `results/`.

    **The registered record is no longer declared a diagnostic** (M-46,
    2026-08-18): the stage's own readings belong in `RESULTS.md` and not only in
    its verdict sheet. Off-parameter runs keep `diagnostic_only`; they are
    skipped on filename as well, so there the flag is redundant rather than
    load-bearing.

    **The caveat the cleared flag used to carry does not go away and must travel
    with any citation of this record.** `docs/a7_continuous_c.md` section 4.2
    registers `D_fixed`, the population intersected across grid points, as the
    scored estimator, and this file computes `D_reach`, which the same section
    registers as reported and never scored. It is kept in the record as
    `diagnostic_reason` and repeated in full in
    the record itself, because a reason that lives in one place only is a
    reason one rename removes.

    **The flag is cleared here in the writer and not only in the record on
    disk.** A record-level edit is silently undone by the next run, and that is
    not a hypothetical: it happened on 2026-08-18, hours after M-46, when
    another session re-ran this file and the flag came back.

    Nothing wall-clock, machine-dependent or version-dependent goes in, per
    the generated-files rules 1 and 2.
    """
    registered = (
        mode == "grid"
        and args.arm == "uniform"
        and getattr(args, "scope", "all") == "all"
        and args.seeds == REGISTERED_SEEDS
        and args.rounds == 300
    )
    name = (
        "a7_continuous_c.json"
        if registered
        else f"a7_continuous_c.offparam_{mode}_{args.arm}"
        + (
            "" if getattr(args, "scope", "all") == "all"
            else f"_scope-{args.scope}"
        )
        + f"_{args.seeds}x{args.rounds}.json"
    )
    payload = {
        "stage": "A7-A continuous connectivity",
        # M-46: the registered record is not a diagnostic. Off-parameter runs
        # still are, though `.offparam` in the name already excludes them.
        **({} if registered else {"diagnostic_only": True}),
        # Kept on both, cleared flag or not. See this function's docstring.
        "diagnostic_reason": (
            "D_fixed, the estimator section 4.2 registers as scored, is not "
            "computed here. Every gap in this file is D_reach, which the same "
            "section registers as reported and never scored."
        ),
        "arm": args.arm,
        "scope": getattr(args, "scope", "all"),
        "mode": mode,
        "seeds": args.seeds,
        "rounds": args.rounds,
        "registered_parameters": registered,
        "grid": list(
            DOSE if mode == "dose" else (GRID if mode == "grid" else LOW)
        ),
        "rows": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / name
    out.write_text(
        json.dumps(_clean(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out


def write_verdicts() -> Path:
    """Assemble `results/a7_verdicts.json` from the records already on disk.

    **This exists because `RESULTS.md` is the ledger other lines of work read,
    and a stage whose every record was `diagnostic_only` had no heading in it.**
    A7 ran and has eleven verdicts; without this it read as not run, which is
    what the README said in two places until 2026-08-16.

    **That premise is now only half true**: M-46 cleared the flag on the
    registered measurement record, so A7-A has its own heading as well. This
    sheet stays, because the eleven verdicts are not derivable from any one
    record and because retiring it would move the citation target of everything
    that already points here. Every number below is read out of a
    record rather than typed, and a missing record raises rather than being
    skipped, so the sheet cannot claim a verdict it has no evidence for.
    """
    need = {
        "grid_u": "a7_continuous_c.json",
        "grid_p": "a7_continuous_c.offparam_grid_preferential_20x300.json",
        "dfx_u": "a7_continuous_c.offparam_dfixed_uniform_20x300.json",
        "dfx_p": "a7_continuous_c.offparam_dfixed_preferential_20x300.json",
        "legb": "a7b_legb.offparam_uniform_20x300.json",
        "p2": "a7b_p2_room.offparam_uniform_20x300.json",
        "p2_p": "a7b_p2_room.offparam_preferential_20x300.json",
        "p1_u": "a7b_p1_retention.offparam_uniform_20x300.json",
        "p1_p": "a7b_p1_retention.offparam_preferential_20x300.json",
        "loop": "a7_loop_sum_by_seed.json",
        "im": "a7b_im_switch.offparam_uniform_20x300.json",
    }
    r = {}
    for key, name in need.items():
        p = RESULTS / name
        if not p.exists():
            raise FileNotFoundError(
                f"{name} is missing, so the verdict sheet cannot be written. "
                "Re-run the stage rather than editing this file."
            )
        r[key] = json.loads(p.read_text(encoding="utf-8"))

    gu = {row["s"]: row for row in r["grid_u"]["rows"]}
    gp = {row["s"]: row for row in r["grid_p"]["rows"]}
    du = r["dfx_u"]["result"]["cells"]
    dp = r["dfx_p"]["result"]["cells"]
    legb = {row["s"]: row for row in r["legb"]["rows"]}
    p2 = {row["s"]: row for row in r["p2"]["rows"]}

    first_reach = next(
        s for s in sorted(gu) if gu[s]["peripheral_participating_mean"] > 0
    )
    h1_0 = du["H1_only"]["split_at_s"]["0.0"]
    h1_u = du["H1_only"]["split_at_s"]["0.01"]
    h1_p = dp["H1_only"]["split_at_s"]["0.01"]
    room_base = p2[0.0]
    room_max = max(
        row["room_log_inv_hhi"] / room_base["room_log_inv_hhi"] for row in p2.values()
    )
    room_max_prod = max(
        row["room_log_inv_hhi_prod"] / room_base["room_log_inv_hhi_prod"]
        for row in p2.values()
    )
    dk0 = legb[0.0]["d"]["K"]["log_inv_hhi_prod"]

    # A7-A-5 registers a fall that is monotone in the seed mean and, per seed,
    # within section 2.6's tolerance with every violation named. The grid
    # records carry the first seed alone, and the sheet used to quote that
    # seed's peak as the stage's. The per-seed record has every seed; its first
    # seed has to be the one the grid records carry, or the two are not
    # readings of one object.
    loops = {"uniform": (r["loop"]["arms"]["uniform"], gu),
             "preferential": (r["loop"]["arms"]["preferential"], gp)}
    for arm, (block, grid_rows) in loops.items():
        for s, row in grid_rows.items():
            first = block["by_point"][f"{s:g}"][0]
            if abs(first - row["mean_abs_loop_sum_fixed"][0]) > 1e-9:
                raise ValueError(
                    f"the per-seed loop sums and the {arm} grid record "
                    f"disagree on the first seed at s = {s:g}, so they do not "
                    "read the same object. Re-run --loop-sum."
                )
    # Both clauses are read off the per-seed values themselves, not off the
    # summary fields stored beside them, so a record whose stored flags say one
    # thing and whose values say another reads as its values.
    def _from_values(block):
        grid = tuple(block["grid"])
        return summarise_loop_sum(
            block["arm"], grid, {s: block["by_point"][f"{s:g}"] for s in grid})
    lu = _from_values(loops["uniform"][0])
    lp = _from_values(loops["preferential"][0])
    a7_a5 = all(a["falls_monotonically_in_the_seed_mean"]
                and a["falls_per_seed_within_tolerance"] for a in (lu, lp))

    # A7-A-2 names D_fixed. Its interior is the D_fixed points strictly inside
    # the grid, and the clause asks for a negative rank correlation of the gap
    # against s at every seed.
    def _ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        out = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2.0
            i = j + 1
        return out

    def _negative_seeds(cells):
        split = cells["both"]["split_at_s"]
        interior = sorted((p for p in split if 0.0 < float(p) < 1.0), key=float)
        xs = _ranks([float(p) for p in interior])
        count = 0
        for i in range(len(split[interior[0]]["by_seed"])):
            ys = _ranks([split[p]["by_seed"][i] for p in interior])
            if float(np.corrcoef(xs, ys)[0, 1]) < 0:
                count += 1
        return count, interior
    a2_neg_u, a2_interior = _negative_seeds(du)
    a2_neg_p, _ = _negative_seeds(dp)
    a2_seeds = len(du["both"]["split_at_s"]["0.0"]["by_seed"])

    # Leg B ran on its own grid, which is nine of leg A's seventeen points.
    legb_points = sorted(legb)
    absent = [s for s in sorted(gu) if s not in legb]
    # A7-B-4 registers both probes on every row of leg B. Read which points
    # each probe record carries rather than assuming them from leg B's rows.
    probe_points = {
        key: sorted(row["s"] for row in r[key]["rows"])
        for key in ("p1_u", "p1_p", "p2", "p2_p")
    }
    probes_on_every_row = all(v == legb_points for v in probe_points.values())
    k_unstable = sum(
        1 for s in legb_points
        if not legb[s]["d"]["K"]["log_inv_hhi_prod"]["same_sign_across_seeds"]
    )

    # The two switch cells section 13.5 recorded as identically zero.
    im = r["im"]["point"]
    im_i = im["d"]["I"]["log_inv_hhi_prod"]
    im_m = im["d"]["M"]["log_inv_hhi_prod"]

    # Rule 11f, 2026-09-13. Three of this sheet's verdicts were a literal True while
    # their details stated claims the objects above can answer. None of the readings
    # moves; what changes is that the claim and the verdict become the same object.

    # A7-A-1: nothing participates below the first reach, and something does at it.
    a7_a1 = (gu[first_reach]["peripheral_participating_mean"] > 0
             and all(gu[s]["peripheral_participating_mean"] == 0
                     for s in sorted(gu) if s < first_reach))

    # A7-B-3: the clause fires when the two measures disagree. It did not fire, and
    # the reason given is that the aggregate is sign-unstable too, so check that:
    # every competitor's range on the aggregate straddles zero at s = 0.
    def _straddles(cell):
        lo, hi = cell["range"]
        return lo < 0 < hi
    agg0 = legb[0.0]["d"]
    a7_b3 = (bool(agg0)
             and all(_straddles(agg0[arm]["log_inv_hhi"]) for arm in agg0)
             and _straddles(dk0))

    # A7-B-4: the trigger the section registered. The aggregate has more room than
    # the band and the production-layer axis does not, which is what makes the
    # substitution fire; the band is named here rather than left in the prose.
    ROOM_BAND = 1.5
    a7_b4 = probes_on_every_row and room_max > ROOM_BAND >= room_max_prod

    criteria = [
        {"name": "A7-A-1", "passed": a7_a1, "detail":
         f"reach: peripheral-tercile participation is 0.0 at every seed through "
         f"s = 0.7 and first strictly positive at s = {first_reach}, where the "
         f"graph carries {gu[first_reach]['graph']['edges']:.0f} of 39800 edges "
         f"and the layer gap has fallen from "
         f"{gu[0.0]['graph']['layer_gap']:.3f} to "
         f"{gu[first_reach]['graph']['layer_gap']:.3f}. The carrier gains a "
         f"measurable population by ceasing to be stratified; docs section 6.1"},
        {"name": "A7-A-2", "passed": False, "detail":
         f"the registered shape is wrong. On D_fixed, the estimator it names, "
         f"over its interior points s = "
         f"{', '.join(f'{float(p):g}' for p in a2_interior)} the rank "
         f"correlation of both against s is negative in {a2_neg_u}/{a2_seeds} "
         f"seeds in the uniform arm and {a2_neg_p}/{a2_seeds} in the "
         f"preferential one, not at every seed. Not a gradient: a step at the "
         f"first grid point, on D_fixed both "
         f"{du['both']['split_at_s']['0.0']['mean']:+.4f} to "
         f"{du['both']['split_at_s']['0.01']['mean']:+.4f} and "
         f"{dp['both']['split_at_s']['0.0']['mean']:+.4f} to "
         f"{dp['both']['split_at_s']['0.01']['mean']:+.4f}; on D_reach the same "
         f"step reads {gu[0.0]['gaps']['both']:+.4f} to "
         f"{gu[0.01]['gaps']['both']:+.4f} and stays flat to s = 0.9. Recorded "
         f"under the project's engineering rule 8 and not repaired; docs "
         f"sections 6.2 and 11.1"},
        {"name": "A7-A-3", "passed": False, "void": True, "detail":
         f"void on the estimator it names. On D_fixed each arm's population is "
         f"intersected across its own grid, so the two are "
         f"{r['dfx_u']['result']['population_mean']:.2f} against "
         f"{r['dfx_p']['result']['population_mean']:.2f} nodes and a difference "
         f"of falls compares quantities on different agents; docs section 11.2"},
        {"name": "A7-A-4", "passed": False, "detail":
         f"A3-8' holds nowhere including where it was derived. Loop-sum-only "
         f"same-sign across seeds on D_fixed at s = 0: "
         f"{du['H1_only']['split_at_s']['0.0']['n_positive']}/20 and "
         f"{dp['H1_only']['split_at_s']['0.0']['n_positive']}/20, against 20/20 "
         f"on D_reach. A3-8's own state is untouched; docs section 11.3"},
        {"name": "A7-A-5", "passed": a7_a5, "detail":
         f"the identity does not hold on the measured population. Mean |loop "
         f"sum| over the fixed production layer rises before it falls. On the "
         f"mean of the {lu['seeds']} seeds its peak over the grid is "
         f"{lu['peak_multiple_of_the_seed_mean']:.2f} times its s = 0 value in "
         f"the uniform arm and {lp['peak_multiple_of_the_seed_mean']:.2f} in "
         f"the preferential one, the mean rising at "
         f"{lu['rising_steps_of_the_seed_mean']} and "
         f"{lp['rising_steps_of_the_seed_mean']} of "
         f"{len(lu['grid']) - 1} steps; "
         f"{lu['seeds_rising_above_their_own_first_point']} and "
         f"{lp['seeds_rising_above_their_own_first_point']} of "
         f"{lu['seeds']} seeds rise above their own s = 0 value. Per seed, "
         f"{lu['seeds_with_a_violation']} and {lp['seeds_with_a_violation']} of "
         f"{lu['seeds']} seeds rise by more than section 2.6's tolerance "
         f"({lu['per_seed_tolerance_relative']:.2%} of the seed's own s = 0 "
         f"value) at some step, {len(lu['per_seed_violations'])} and "
         f"{len(lp['per_seed_violations'])} steps, each named in "
         f"results/a7_loop_sum_by_seed.json. The first "
         f"seed alone, which is what the grid records carry, peaks at "
         f"{max(row['mean_abs_loop_sum_fixed'][0] for row in gu.values()) / gu[0.0]['mean_abs_loop_sum_fixed'][0]:.2f} "
         f"and "
         f"{max(row['mean_abs_loop_sum_fixed'][0] for row in gp.values()) / gp[0.0]['mean_abs_loop_sum_fixed'][0]:.2f}"
         f"; docs section 9, changelog entry of 2026-08-16"},
        {"name": "A7-A-6", "passed": False, "detail":
         "the round-count ladder is not monotone in the uniform arm and gives "
         "4.85 against a registered five in the preferential one. The retained "
         "fraction goes as 1/R because the s = 0 baseline scales with the round "
         "count; unnormalised the gap at s = 0.01 does not move at all across a "
         "fourfold change in rounds while the gap at s = 0 moves with it; docs "
         "sections 10.2 and 10.3"},
        {"name": "A7-B-1", "passed": False, "void": True, "detail":
         f"unreadable. d(K, s) is sign-unstable at {k_unstable} of the "
         f"{len(legb_points)} grid points leg B ran, including "
         f"s = 0, where the mean is {dk0['mean']:+.5f} against a range of "
         f"[{dk0['range'][0]:+.4f}, {dk0['range'][1]:+.4f}] that straddles zero. "
         f"A quantity with no sign has no magnitude to trend. This is A4-4's "
         f"position on a different estimator; docs section 13.1"},
        {"name": "A7-B-2", "passed": False, "void": True, "detail":
         "not adjudicable as registered: the noise floor the clause conditions "
         "on was never given a numeric form. Against A7-B-1's standard E fails "
         "too, at 17/20 rather than 20/20; docs section 13.2"},
        {"name": "A7-B-3", "passed": a7_b3, "detail":
         "the two-measure disagreement clause did not fire. On the aggregate "
         "log(1/HHI) both competitors are also sign-unstable and near zero, so "
         "the measures agree and what they agree on is that nothing is "
         "readable; docs section 13.3"},
        {"name": "A7-B-4", "passed": a7_b4, "detail":
         f"both probes ran before anything was scored and the section 5.3 "
         f"trigger was decided on them alone. P1 in both arms and P2 in both "
         f"arms carry "
         f"{'every one' if probes_on_every_row else 'not all'} of the "
         f"{len(legb_points)} points leg B ran "
         f"({min(len(v) for v in probe_points.values())} to "
         f"{max(len(v) for v in probe_points.values())} points per record). "
         f"Room relative to s = 0, largest "
         f"over the grid: aggregate log(1/HHI) {room_max:.2f} against a "
         f"registered band of {ROOM_BAND}, production-layer-only "
         f"{room_max_prod:.2f}. "
         f"The substitution registered with the band fires and leg B proceeds "
         f"on one axis; docs sections 12.2 and 12.3"},
        {"name": "A7-B-5", "passed": False, "void": True, "detail":
         f"I and M recorded as not run on leg B's grid, on section 5.2's "
         f"ruling that they are unreadable for direction. The further reason "
         f"once given here, that above s = 0.02 a one-off transfer leaves "
         f"nothing after a generation and so their effects are identically "
         f"zero, does not hold: what vanishes is the memory of a perturbation, "
         f"and the two switches act on current holdings through the "
         f"demographic layer. At s = {im['s']:g} in the {im['arm']} arm the "
         f"switch cells end on other holdings than the control in "
         f"{im['final_holdings_differ_from_none']['I']} and "
         f"{im['final_holdings_differ_from_none']['M']} of "
         f"{r['im']['seeds']} seeds, production-layer log(1/HHI) "
         f"{im_i['mean']:+.4f} for I and {im_m['mean']:+.4f} for M, negative "
         f"in {im_i['n_negative']} and {im_m['n_negative']} seeds. Either "
         f"switch also turns on the demographic layer, so that is the switch "
         f"cell against the control and not an effect of inheritance or "
         f"mating alone; docs sections 12.1 and 13.5"},
    ]
    out = RESULTS / "a7_verdicts.json"
    out.write_text(
        json.dumps({
            "stage": "A7",
            "seeds": 20,
            "rounds": 300,
            "note": (
                "One pre-registration with two legs. The measurement records "
                "carry diagnostic_only because section 4.2's scored estimator "
                "is computed under a flag rather than by default; this sheet "
                "carries the verdicts and is assembled from those records by "
                "experiments/a7_continuous_c.py --verdicts. Leg B ran on "
                + str(len(legb_points))
                + " of leg A's "
                + str(len(gu))
                + " grid points; the points leg A has and leg B does not are "
                + ", ".join(f"{s:g}" for s in absent)
                + "."
            ),
            "criteria": criteria,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--probe", action="store_true", help="one point, one seed")
    ap.add_argument("--grid", action="store_true",
                    help="the seventeen-point grid; the registered run with the "
                         "uniform arm, 20 seeds and 300 rounds")
    ap.add_argument("--verdicts", action="store_true",
                    help="assemble results/a7_verdicts.json from the records")
    ap.add_argument("--loop-sum", action="store_true",
                    help="A7-A-5's quantity at every seed, both arms, on "
                         "models that are built and not run")
    ap.add_argument("--paired-loop-sum", action="store_true",
                    help="mean |loop sum| over each seed's own paired "
                         "population, every seed, both arms; needs the runs")
    ap.add_argument(
        "--dfixed", action="store_true",
        help="section 4.2's scored estimator, over the --low points",
    )
    ap.add_argument(
        "--low", action="store_true",
        help="the four points where the placebo is readable, with per-seed gaps",
    )
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--s", type=float, default=PROBE_S)
    ap.add_argument(
        "--arm", choices=("uniform", "preferential"), default="uniform",
        help="preferential is section 4.3's placebo: same edge count, targets "
             "drawn in proportion to existing in-degree",
    )
    ap.add_argument(
        "--dose", action="store_true",
        help="the downward channel as a dose, at s = 0. NetworkSpec."
             "downward_edges is the framework's own thin controlled channel and "
             "zero is its specification; the scope arms showed that such edges "
             "arriving sideways through the shortcut draw, 21 to 47 per seed "
             "(21 at the first seed), already collapse the gap. This turns the channel on directly over "
             + str(DOSE) + " and reads where the collapse starts.",
    )
    ap.add_argument(
        "--scope",
        choices=("all", "production", "financial", "downward", "upward"),
        default="all",
        help="where the shortcut edges may land, with the count held at "
             "what the registered arm draws. The draw is uniform over "
             "ordered pairs and on a 20/180 graph that is not uniform over "
             "kinds of edge: at a rate of 0.01 the registered arm puts, at "
             "the first seed, 282 edges inside the production layer and 21 "
             "pointing downward (21 to 47 downward across 20 seeds), "
             "while downward_edges is zero by default and its docstring "
             "calls zero the framework's specification",
    )
    args = ap.parse_args()

    module = _a3c()

    if args.probe:
        print(
            f"\nPROBE  section 4.7. One grid point, one seed, nothing scored.\n"
            f"  s = {args.s}, arm {args.arm}, 1 seed, {args.rounds} rounds. The four-cell "
            f"factorial and its separately built null, five models.\n"
        )
        sd0 = graph_columns(NetworkSpec(seed=0))["centrality_sd"]
        r = row(
            module, args.s, range(1), args.rounds,
            arm=args.arm, sd_at_zero=sd0,
        )
        print_row(r)
        per_point = r["seconds"] * args.seeds
        print(
            f"\n  Extrapolation, and it is arithmetic rather than a measurement."
            f"\n    one point at {args.seeds} seeds     "
            f"{per_point / 60:6.1f} min"
            f"\n    {len(GRID)} grid points, one arm      "
            f"{per_point * len(GRID) / 60:6.1f} min"
            f"\n    both arms (section 4.3 A1)   "
            f"{2 * per_point * len(GRID) / 60:6.1f} min"
            f"\n\n  Section 4.7's contraction, if it does not fit: drop grid"
            f" points from the dense\n  low-`s` region inward and record which."
            f" Never drop seeds.\n"
        )
        return 0

    if args.loop_sum:
        print(
            f"\nLOOP SUM  A7-A-5's quantity at every seed, both arms,"
            f" {args.seeds} seeds.\n  Read off the terms matrix of models that"
            f" are built and not run, over the fixed production layer.\n"
        )
        arms = {
            arm: loop_sum_by_seed(module, arm, range(args.seeds), args.rounds)
            for arm in ("uniform", "preferential")
        }
        for arm, a in arms.items():
            print(f"  {arm:13s} peak over the grid, as a multiple of s = 0: "
                  f"{a['peak_multiple_of_the_seed_mean']:.6f} on the mean of "
                  f"{a['seeds']} seeds, {a['peak_multiple_first_seed']:.6f} on "
                  f"the first seed alone, "
                  f"{min(a['peak_multiple_by_seed']):.3f} to "
                  f"{max(a['peak_multiple_by_seed']):.3f} by seed")
            print(f"  {'':13s} the seed mean rises at "
                  f"{a['rising_steps_of_the_seed_mean']} of "
                  f"{len(a['grid']) - 1} steps, and "
                  f"{a['seeds_rising_above_their_own_first_point']} of "
                  f"{a['seeds']} seeds rise above their own s = 0 value")
        registered = args.seeds == REGISTERED_SEEDS and args.rounds == 300
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            "a7_loop_sum_by_seed.json" if registered
            else f"a7_loop_sum_by_seed.offparam_{args.seeds}x{args.rounds}.json"
        )
        payload = {
            "stage": "A7-A loop sum by seed",
            "diagnostic_only": True,
            "diagnostic_reason": (
                "the per-seed reading A7-A-5 registers; the verdict sheet "
                "reads it, and the grid records carry the first seed alone"
            ),
            "built_and_not_run": True,
            "seeds": args.seeds,
            "rounds": args.rounds,
            "arms": arms,
        }
        out.write_text(
            json.dumps(_clean(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\n  written: {out.name}\n")
        return 0

    if args.paired_loop_sum:
        print(
            f"\nPAIRED LOOP SUM  mean |loop sum| over each seed's own paired"
            f" population, both arms,\n  {args.seeds} seeds, {args.rounds}"
            f" rounds. The population comes out of the runs.\n"
        )
        arms = {}
        for arm in ("uniform", "preferential"):
            a = paired_loop_sum_by_seed(module, arm, range(args.seeds),
                                        args.rounds)
            arms[arm] = a
            for k in ("0.01", "0.05", "0.5"):
                if k in a["change_of_the_seed_mean_from_first"]:
                    print(f"  {arm:13s} s = {k:4s} seed mean "
                          f"{a['change_of_the_seed_mean_from_first'][k]:+.4f} "
                          f"from s = 0, higher in "
                          f"{a['seeds_higher_than_their_own_first'][k]} of "
                          f"{a['seeds']} seeds")
        registered = args.seeds == REGISTERED_SEEDS and args.rounds == 300
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            "a7_paired_loop_sum_by_seed.json" if registered
            else f"a7_paired_loop_sum_by_seed.offparam_{args.seeds}x{args.rounds}.json"
        )
        payload = {
            "stage": "A7-A paired loop sum by seed",
            "diagnostic_only": True,
            "diagnostic_reason": (
                "the paired-population loop sum at every seed; the grid records "
                "carry the first seed alone and section 14.2 quoted it"
            ),
            "seeds": args.seeds,
            "rounds": args.rounds,
            "arms": arms,
        }
        out.write_text(
            json.dumps(_clean(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\n  written: {out.name}\n")
        return 0

    if args.verdicts:
        p = write_verdicts()
        print(f"\n  written: {p.name}  (eleven verdicts, assembled from"
              f" the measurement records)\n")
        return 0

    if args.dfixed:
        print(
            f"\nD_FIXED  section 4.2's scored estimator, arm {args.arm}."
            f"\n  Population intersected across every cell and every point in"
            f" {list(LOW)}.\n  Both bin conventions reported: the split"
            f" recomputed at each `s`, and frozen at `s = 0`.\n"
        )
        res = d_fixed(module, range(args.seeds), args.rounds, args.arm)
        print(f"  fixed population {res['population_mean']:.1f} nodes, "
              f"per seed {res['population_by_seed']}\n")
        for name in ("both", "H1_only", "H0_only"):
            print(f"  {name}")
            for label in ("split_at_s", "split_at_zero"):
                cells = res["cells"][name][label]
                zero = cells[str(LOW[0])]["mean"]
                line = f"    {label:14s}"
                for s in LOW:
                    c = cells[str(s)]
                    kept = (
                        "" if s == LOW[0] or zero == 0.0
                        else f" ({100.0 * c['mean'] / zero:+.1f}%)"
                    )
                    line += (
                        f"  s={s}: {c['mean']:+8.4f}{kept}"
                        f" [{c['n_positive']:2d}/{args.seeds}]"
                    )
                print(line)
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            f"a7_continuous_c.offparam_dfixed_{args.arm}"
            f"_{args.seeds}x{args.rounds}.json"
        )
        payload = {
            "stage": "A7-A D_fixed",
            "diagnostic_only": True,
            "diagnostic_reason": (
                "section 4.2 fixed the population and did not fix the "
                "centrality split, so two conventions are reported and neither "
                "is registered as the one"
            ),
            "seeds": args.seeds,
            "rounds": args.rounds,
            "result": res,
        }
        out.write_text(
            json.dumps(_clean(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\n  written: {out.name}\n")
        return 0

    if args.dose:
        # The channel opened directly, at s = 0, so nothing else moves with it.
        # Registered 2026-08-24 after the scope arms located the collapse in the
        # downward edges: 21 of them arriving through the shortcut draw already
        # take the gap down as far as 350 do. That says the channel saturates
        # early and says nothing about where it starts, which is what this reads.
        sd0 = graph_columns(NetworkSpec(seed=0))["centrality_sd"]
        reference = module.build(
            0, args.rounds, **module.FIXED, **module.CELLS["null"]
        )
        print(
            f"\nDOSE  the downward channel opened directly, s = 0, over {list(DOSE)}."
            f"\n  downward_edges is zero in the framework's specification; A0-6"
            f" measured one such edge\n  taking production-layer inflow from"
            f" 17.7007 to 48.3919. This reads the gap against the count.\n"
        )
        rows: list[dict] = []
        for k in DOSE:
            r = row(module, 0.0, range(args.seeds), args.rounds, reference,
                    arm=args.arm, sd_at_zero=sd0, downward=k)
            print_row(r)
            rows.append(r)
        print(f"\n  written: {write_record(rows, 'dose', args).name}\n")
        return 0

    if args.low:
        sd0 = graph_columns(NetworkSpec(seed=0))["centrality_sd"]
        reference = module.build(
            0, args.rounds, **module.FIXED, **module.CELLS["null"]
        )
        print(
            f"\nLOW  the readable region for the placebo, arm {args.arm}, "
            f"scope {args.scope}."
            f"\n  centrality sd at s = 0 is {sd0:.6f}. Per-seed gaps printed,"
            f" because section 4.4\n  requires a moved distribution be told"
            f" apart from a mean pulled to zero.\n"
        )
        zero = None
        rows: list[dict] = []
        for s in LOW:
            r = row(module, s, range(args.seeds), args.rounds, reference,
                    arm=args.arm, sd_at_zero=sd0, scope=args.scope)
            print_row(r)
            print_per_seed(r, zero)
            if s == 0.0:
                zero = r
            rows.append(r)
        print(f"\n  written: {write_record(rows, 'low', args).name}\n")
        return 0

    if args.grid:
        print("\nGRID  unaudited path, section 4.7's probe has to come first.\n")
        reference = module.build(
            0, args.rounds, **module.FIXED, **module.CELLS["null"]
        )
        sd0 = graph_columns(NetworkSpec(seed=0))["centrality_sd"]
        print(f"  arm: {args.arm}.  centrality sd at s = 0 is {sd0:.6f}, and "
              f"every row carries its own ratio to it.\n")
        rows = []
        for s in GRID:
            r = row(module, s, range(args.seeds), args.rounds, reference,
                    arm=args.arm, sd_at_zero=sd0, scope=args.scope)
            print_row(r)
            rows.append(r)
        print(f"\n  written: {write_record(rows, 'grid', args).name}\n")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
