"""A7-A: connectivity as a continuum, on the A3 carrier.

**Status: probe only. No criterion is scored by this file yet.** The
pre-registration is `docs/a7_continuous_c.md`; section 4.7 requires a timing
probe at one interior grid point at one seed, reported, before the grid runs.
`--probe` is that. `--grid` exists so the probe and the run share one row
function rather than two, and it has not been audited or registered as run.

What a row is
-------------

At one shortcut rate `s`, the whole four-cell kappa factorial and its separately
built null, exactly as A3-8 runs them. `a3c_load_bearing` supplies `build_all`,
`build_baseline`, `summarise` and `evaluate`, so this is the same instrument at a
different graph rather than a second implementation of it. Section 4.3's guard
G3 inherits that module's inert detection with it.

Alongside every row, the control variables in their own units, because
`SESSION_INIT.md` lesson three is a scan whose second moving quantity had no
name until three stages later:

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

What this file does not do
--------------------------

`D_fixed`, the grid-wide intersection population section 4.2 registers as the
scored estimator, is not computed here. Neither is the placebo arm of section
4.3. Both belong to the run, and both are written after the probe says what the
run costs.
"""

from __future__ import annotations

import argparse
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

    A5.3's scope table counts here, and `A3-8` is measured on the top eighth of
    it, so the denominator has to be this set rather than the whole graph.
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


def row(
    module,
    s: float,
    seeds: range,
    rounds: int,
    reference=None,
    arm: str = "uniform",
    sd_at_zero: float | None = None,
) -> dict:
    """One grid point: the four-cell factorial, its null, and the columns.

    ``reference`` is the `s = 0` null model for ``seeds.start``, built once by
    the caller and reused for the churn columns at every point.
    """
    spec = NetworkSpec(seed=seeds.start, shortcut_rate=s, shortcut_mode=arm)
    started = time.time()
    if reference is None:
        reference = module.build(
            seeds.start, rounds, **module.FIXED, **module.CELLS["null"]
        )

    kw = {"shortcut_rate": s, "shortcut_mode": arm} if s > 0.0 else {}
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
    cell **and** every grid point.

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
        and args.seeds == REGISTERED_SEEDS
        and args.rounds == 300
    )
    name = (
        "a7_continuous_c.json"
        if registered
        else f"a7_continuous_c.offparam_{mode}_{args.arm}"
        f"_{args.seeds}x{args.rounds}.json"
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
        "mode": mode,
        "seeds": args.seeds,
        "rounds": args.rounds,
        "registered_parameters": registered,
        "grid": list(GRID if mode == "grid" else LOW),
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

    criteria = [
        {"name": "A7-A-1", "passed": True, "detail":
         f"reach: peripheral-tercile participation is 0.0 at every seed through "
         f"s = 0.7 and first strictly positive at s = {first_reach}, where the "
         f"graph carries {gu[first_reach]['graph']['edges']:.0f} of 39800 edges "
         f"and the layer gap has fallen from "
         f"{gu[0.0]['graph']['layer_gap']:.3f} to "
         f"{gu[first_reach]['graph']['layer_gap']:.3f}. The carrier gains a "
         f"measurable population by ceasing to be stratified; docs section 6.1"},
        {"name": "A7-A-2", "passed": False, "detail":
         f"the registered shape is wrong. Not a gradient: a step at the first "
         f"grid point, both {gu[0.0]['gaps']['both']:+.4f} to "
         f"{gu[0.01]['gaps']['both']:+.4f}, then flat to s = 0.9. Recorded under "
         f"the project's engineering rule 8 and not repaired; docs section 6.2"},
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
        {"name": "A7-A-5", "passed": False, "detail":
         f"the identity does not hold on the measured population. Mean |loop "
         f"sum| over the fixed production layer rises before it falls, to "
         f"{max(row['mean_abs_loop_sum_fixed'][0] for row in gu.values()) / gu[0.0]['mean_abs_loop_sum_fixed'][0]:.2f} "
         f"times its s = 0 value in the uniform arm and "
         f"{max(row['mean_abs_loop_sum_fixed'][0] for row in gp.values()) / gp[0.0]['mean_abs_loop_sum_fixed'][0]:.2f} "
         f"in the preferential one; docs section 6 changelog"},
        {"name": "A7-A-6", "passed": False, "detail":
         "the round-count ladder is not monotone in the uniform arm and gives "
         "4.85 against a registered five in the preferential one. The retained "
         "fraction goes as 1/R because the s = 0 baseline scales with the round "
         "count; unnormalised the gap at s = 0.01 does not move at all across a "
         "fourfold change in rounds while the gap at s = 0 moves with it; docs "
         "sections 10.2 and 10.3"},
        {"name": "A7-B-1", "passed": False, "void": True, "detail":
         f"unreadable. d(K, s) is sign-unstable at every grid point including "
         f"s = 0, where the mean is {dk0['mean']:+.5f} against a range of "
         f"[{dk0['range'][0]:+.4f}, {dk0['range'][1]:+.4f}] that straddles zero. "
         f"A quantity with no sign has no magnitude to trend. This is A4-4's "
         f"position on a different estimator; docs section 13.1"},
        {"name": "A7-B-2", "passed": False, "void": True, "detail":
         "not adjudicable as registered: the noise floor the clause conditions "
         "on was never given a numeric form. Against A7-B-1's standard E fails "
         "too, at 17/20 rather than 20/20; docs section 13.2"},
        {"name": "A7-B-3", "passed": True, "detail":
         "the two-measure disagreement clause did not fire. On the aggregate "
         "log(1/HHI) both competitors are also sign-unstable and near zero, so "
         "the measures agree and what they agree on is that nothing is "
         "readable; docs section 13.3"},
        {"name": "A7-B-4", "passed": True, "detail":
         f"both probes ran before anything was scored and the section 5.3 "
         f"trigger was decided on them alone. Room relative to s = 0, largest "
         f"over the grid: aggregate log(1/HHI) {room_max:.2f} against a "
         f"registered band of 1.5, production-layer-only {room_max_prod:.2f}. "
         f"The substitution registered with the band fires and leg B proceeds "
         f"on one axis; docs sections 12.2 and 12.3"},
        {"name": "A7-B-5", "passed": False, "void": True, "detail":
         "I and M recorded as not run. Above s = 0.02 in the uniform arm a "
         "one-off transfer leaves nothing after a generation, so a transmitting "
         "mechanism has no stock and their effects are identically zero by "
         "construction; docs sections 12.1 and 13.5"},
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
                "experiments/a7_continuous_c.py --verdicts."
            ),
            "criteria": criteria,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--probe", action="store_true", help="one point, one seed")
    ap.add_argument("--grid", action="store_true", help="not registered as run")
    ap.add_argument("--verdicts", action="store_true",
                    help="assemble results/a7_verdicts.json from the records")
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

    if args.low:
        sd0 = graph_columns(NetworkSpec(seed=0))["centrality_sd"]
        reference = module.build(
            0, args.rounds, **module.FIXED, **module.CELLS["null"]
        )
        print(
            f"\nLOW  the readable region for the placebo, arm {args.arm}."
            f"\n  centrality sd at s = 0 is {sd0:.6f}. Per-seed gaps printed,"
            f" because section 4.4\n  requires a moved distribution be told"
            f" apart from a mean pulled to zero.\n"
        )
        zero = None
        rows: list[dict] = []
        for s in LOW:
            r = row(module, s, range(args.seeds), args.rounds, reference,
                    arm=args.arm, sd_at_zero=sd0)
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
                    arm=args.arm, sd_at_zero=sd0)
            print_row(r)
            rows.append(r)
        print(f"\n  written: {write_record(rows, 'grid', args).name}\n")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
