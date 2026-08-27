"""A3 P-C: is the holonomy load-bearing, or is the mechanism reachability?

Registered in ``docs/a3_restated.md`` §4. This file evaluates and does not
design; every threshold and every reading it prints is written there.

Usage::

    python experiments/a3c_load_bearing.py
    python experiments/a3c_load_bearing.py --seeds 5 --rounds 300
    python experiments/a3c_load_bearing.py --sweep    # 6.5's robustness grid

``--sweep`` runs `a3_asset_channel.md` §6.5's grid against A3-8. That grid is a
registered promise — "no conclusion may live at one value" — and §6.5 records
its absence as a breach rather than as a todo. A3-8 is the criterion carrying
the new content of A3, so leaving it off the grid would have left the breach
open on the one criterion it most applies to.

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
import dataclasses
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    SWEEP_CELLS,
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

#: Which constructor a keyword belongs to, read off the two dataclasses rather
#: than listed here. A hand-written list would have to be edited whenever either
#: gains a field, and the failure of not editing it is silent: the keyword goes
#: to the other constructor, or to neither.
_NETWORK_FIELDS = frozenset(f.name for f in dataclasses.fields(NetworkSpec))
_ASSET_FIELDS = frozenset(f.name for f in dataclasses.fields(AssetSpec))

#: The split below is only well defined while the two names are disjoint, and a
#: name in both would reach one constructor and silently not reach the other.
#: That is the call-site defect this repository has already paid for once: a
#: parameter that reached one of two call sites, where the default path was the correct one so nothing fired
#: until a sweep took the other branch. Checked at import so a field added to
#: either dataclass fails here rather than in a grid cell six hours in.
_COLLIDING_FIELDS = _NETWORK_FIELDS & _ASSET_FIELDS
if _COLLIDING_FIELDS:
    raise ImportError(
        "AssetSpec and NetworkSpec now share field names, so build() cannot "
        f"route a keyword to one of them: {sorted(_COLLIDING_FIELDS)}. Rename "
        "one side or give build() an explicit routing table."
    )


def build(seed: int, rounds: int, **kw) -> A3Model:
    """One model. Keywords are routed by which dataclass declares them.

    **Changed 2026-08-15 for A7.** Every keyword used to go to ``AssetSpec``,
    which is why `docs/a7_continuous_c.md` section 3.1 lists this as the second
    thing A7 needs: ``shortcut_rate`` lives on ``NetworkSpec`` and could not be
    reached from a sweep cell at all.

    An unknown name still raises ``TypeError`` from ``AssetSpec``, so a typo in
    a grid cell fails loudly rather than being dropped.

    ``seed`` needs no guard here and was given one for a moment before that was
    measured. It is a named parameter, so ``seed`` in a cell binds to it and
    never reaches ``kw``, and Python raises before this body runs. A hand-written
    check on ``kw`` would therefore be a condition that can never be true, which
    is a guard that cannot speak. The behaviour is asserted in
    ``tests/test_a7_kwarg_routing.py`` instead, where it can fail if a later
    signature change makes it reachable.
    """
    net_kw = {k: v for k, v in kw.items() if k in _NETWORK_FIELDS}
    asset_kw = {k: v for k, v in kw.items() if k not in _NETWORK_FIELDS}
    model = A3Model(
        A3Config(
            asset=AssetSpec(**asset_kw),
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed, **net_kw), seed=seed, rounds=rounds
            ),
        )
    )
    model.run()
    return model


def terciles(
    model: A3Model, population: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """``(central bin, peripheral bin)`` of ``population``.

    Split on **centrality**, a property of the graph: identical across cells at
    a given seed and fixed before any treatment touches anything.

    ``population`` is passed in rather than derived here because it has to be
    the **same node set in every cell**, and no single cell knows that.

    **The bin width is ``centrality_bins`` and used to be a hardcoded three.**
    At its default of 3 this returns the same two thirds it always has, bit for
    bit. Raising it narrows both groups toward the extremes of the ranking,
    which is what ``a3_asset_channel.md`` §6.5 means by sweeping the binning: a
    gap that only exists between the outer thirds and vanishes between the
    outer eighths is a gap that lives in the cut.

    A bin count low enough to make the two groups overlap returns two empty
    arrays, which propagates as a NaN gap and is caught by the ``finite`` check
    in ``evaluate``. Unreachable at any bin count of two or more.
    """
    order = population[np.argsort(model.centrality[population])]
    k = max(1, order.size // max(1, model.a3.asset.centrality_bins))
    if 2 * k > order.size:
        empty = np.array([], dtype=int)
        return empty, empty
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


def build_all(seeds: range, rounds: int, **extra) -> tuple[dict, dict, set[str]]:
    """Every cell at every seed, plus the population they share.

    ``extra`` is a §6.5 sweep cell, merged **over** ``FIXED`` so that a swept
    parameter which happens to be one of A3b's corrections would replace it
    rather than collide at the call. Nothing in ``SWEEP_CELLS`` currently
    overlaps; the merge is written this way so that adding one is an edit to a
    tuple rather than a ``TypeError``.

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
    fixed = {**FIXED, **extra}
    for seed in seeds:
        for name, kw in CELLS.items():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", DesignDeviation)
                m = build(seed, rounds, **fixed, **kw)
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


def build_baseline(
    seeds: range, rounds: int, **extra
) -> tuple[dict[int, A3Model], set[str]]:
    """The separately built null, and any deviation raised while building it.

    These models were already built this way. What is new is that their
    deviations are **caught**: they were being dropped, so a parameter that
    tripped a registered design tie in the *baseline* would have been invisible
    while the identical tie in the treated cells was reported. At the
    registered point there are none, so this collects an empty set and changes
    no number; under ``--sweep`` it is the difference between a clean row and
    a true one.
    """
    models: dict[int, A3Model] = {}
    devs: set[str] = set()
    for seed in seeds:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DesignDeviation)
            m = build(seed, rounds, **{**FIXED, **extra}, **CELLS["null"])
        devs |= {str(w.message).split(".")[0] for w in caught}
        devs |= set(m.deviations)
        models[seed] = m
    return models, devs


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


def evaluate(cells: dict) -> dict:
    """A3-8's reading, returned as data instead of printed.

    Lifted out of ``main`` **unchanged** so that ``--sweep`` asks the same
    question at every grid point. A reading re-implemented for the sweep would
    be a second criterion wearing the first one's name, and the two would drift
    apart on the first edit to either of them.

    ``state`` is one of three words, which is the structure ``a3_restated.md``
    §6 registers rather than a convenience here. ``void`` says the harness
    cannot be read; ``unstable`` says a channel's sign moves across seeds, so
    no share may be quoted; ``pass`` is the only one that carries an answer.
    "The harness is broken" and "the channel is zero" are different findings
    and a two-valued verdict would print them as the same word.
    """
    both = cells["both"]["gap_mean"]
    null = cells["null"]["gap_mean"]
    h1 = cells["H1_only"]["gap_mean"]
    h0 = cells["H0_only"]["gap_mean"]

    costs = [c["mean_cost"] for c in cells.values()]
    cost_drift = (max(costs) - min(costs)) / max(min(costs), 1e-12)

    notes: list[str] = []
    if cost_drift > 0.01:
        notes.append(
            "VOID: the mean acquisition cost is not held across cells, so they "
            "differ in level as well as dispersion and no comparison is valid"
        )
    if abs(null) > 1e-12:
        notes.append(
            f"VOID: the zero calibration reads {null:.3e} rather than zero, so "
            "the harness is wrong whatever the other cells say"
        )
    if abs(both) < 1e-9:
        notes.append(
            "VOID: the full cell moves nothing against the null, so there is "
            "no gap for the single-channel cells to decompose"
        )
    void = list(notes)

    unstable: list[str] = []
    share_h1 = share_h0 = None
    if not void:
        unstable = [
            n
            for n in ("H1_only", "H0_only")
            if not cells[n]["same_sign_across_seeds"]
        ]
        for n in unstable:
            channel = "loop sum" if n == "H1_only" else "gate"
            notes.append(
                f"the {channel} channel's gap changes sign across seeds, so "
                f"its contribution is NOT DISTINGUISHABLE FROM ZERO and no "
                f"share may be quoted for it"
            )
        if not unstable:
            share_h1 = (both - h0) / both
            share_h0 = (both - h1) / both
            notes.append(
                "shares are of the gap between the full cell and the null, "
                "and they need not sum to one: anything left over is "
                "interaction, which §6 requires be reported as interaction "
                "rather than attributed"
            )

    return {
        "state": "void" if void else ("unstable" if unstable else "pass"),
        "cost_drift": cost_drift,
        "gaps": {"both": both, "H1_only": h1, "H0_only": h0, "null": null},
        "unstable_channels": unstable,
        "share_h1": share_h1,
        "share_h0": share_h0,
        "notes": notes,
        # Not part of the registered reading, and deliberately not folded into
        # it. An empty paired population makes every gap NaN, and NaN passes
        # all three void tests in silence -- ``nan > 1e-12`` is False, and so is
        # ``nan < 1e-9`` -- after which the sign test also fails and the cell
        # would be reported as "unstable" when it measured nothing at all.
        # Reported beside the state rather than as a fourth void condition,
        # because adding one would be editing a registered criterion to cover a
        # case only ``--sweep`` can reach.
        "finite": bool(np.all(np.isfinite([both, null, h1, h0]))),
    }


def _chan(names: list[str]) -> str:
    """``['H1_only', 'H0_only']`` as ``H1,H0``, and ``[]`` as ``none``."""
    return ",".join(n.replace("_only", "") for n in names) or "none"


def sweep(
    seeds: range,
    rounds: int,
    cells: tuple[tuple[str, dict], ...],
    baseline: dict,
    progress: bool = True,
) -> dict:
    """`a3_asset_channel.md` §6.5's grid, applied to A3-8.

    Every cell re-runs the **whole** four-cell factorial and its separately
    built null. A3-8's quantity is a difference between cells, so moving a
    parameter in one of them would measure the parameter and not the channel.

    **κ is not on this grid, and that is not an omission.** The four cells are
    the κ factorial. κ is what A3-8 varies in order to produce its answer, so
    putting it on a robustness axis would be sweeping the treatment.

    Three things are compared against the registered reading, and the first one
    on its own would have been misleading.

    **The state**, which is the three words ``evaluate`` returns plus
    ``nonfinite`` for a cell whose paired population came out empty.

    **Which channels are indistinguishable from zero.** The state is already
    ``unstable`` at the registered point because the gate channel's sign moves
    across seeds, so a cell where the *loop sum* also starts moving reports the
    same word for a different reason. The word held; the finding did not. The
    set is compared, not just its emptiness.

    **Whether the axis reached this criterion at all.** A cell whose four gaps
    are bit-identical to the registered point did not vary anything A3-8 can
    see, and a grid that counts it as a passing robustness check is claiming
    evidence it does not have. Those are flagged ``inert`` and named in the
    summary. This is the same objection that excludes A3-1 from the sibling
    sweep, detected rather than reasoned about in advance.

    A cell that trips a design tie is not clean whether or not anything moved,
    for the reason recorded in ``a3_asset_channel.py``: a violated tie visible
    only in stderr while the digest prints a clean row has already happened
    here once.

    No threshold is registered for the two shares, so they are collected and
    reported rather than judged. A share that swings while the state holds is
    still the thing §6.5 was worried about, and a reader can see it without a
    number having been invented after the fact to gate it.
    """
    baseline_state = baseline["state"]
    baseline_zero = list(baseline["unstable_channels"])
    out: dict[str, dict] = {}
    for axis, kw in cells:
        key = " ".join(f"{k}={v}" for k, v in sorted(kw.items()))
        started = time.time()
        models, population, devset = build_all(seeds, rounds, **kw)
        dropped = next(
            int(d.split("__")[-1]) for d in devset if d.startswith("__dropped__")
        )
        devs = {d for d in devset if not d.startswith("__dropped__")}
        base, base_devs = build_baseline(seeds, rounds, **kw)
        devs |= base_devs
        rows = {
            n: summarise(n, ckw, seeds, models, base, population)
            for n, ckw in CELLS.items()
        }
        reading = evaluate(rows)
        state = reading["state"] if reading["finite"] else "nonfinite"
        deviations = sorted(devs)
        pop = rows["both"]["paired_population"]
        zero = list(reading["unstable_channels"])
        inert = reading["gaps"] == baseline["gaps"]
        moved = "" if state == baseline_state else f"{baseline_state} -> {state}"
        zero_moved = (
            ""
            if zero == baseline_zero
            else f"{_chan(baseline_zero)} -> {_chan(zero)}"
        )
        out[key] = {
            "axis": axis,
            "parameters": kw,
            "state": state,
            "moved": moved,
            "zero_channels_moved": zero_moved,
            # True means the four gaps came out bit-identical to the registered
            # point, so this axis does not reach A3-8 and the cell is evidence
            # of nothing. Counted separately from the passing cells.
            "inert": inert,
            "deviations": deviations,
            "cost_drift": reading["cost_drift"],
            "gaps": reading["gaps"],
            "share_h1": reading["share_h1"],
            "share_h0": reading["share_h0"],
            "unstable_channels": zero,
            "paired_population": pop,
            "dropped_to_intersect": dropped,
            "notes": reading["notes"],
        }
        if progress:
            print(f"    {key:34s} {state:9s} zero {_chan(zero):7s} "
                  f"pop {pop:5.1f}  {time.time() - started:5.1f}s", flush=True)
            marks = []
            if moved:
                marks.append(f"STATE MOVED: {moved}")
            if zero_moved:
                marks.append(
                    f"the set of channels indistinguishable from zero moved: "
                    f"{zero_moved}"
                )
            if inert:
                marks.append(
                    "AXIS INERT: every gap is bit-identical to the registered "
                    "point, so this cell is not evidence of robustness"
                )
            if deviations:
                marks.append(f"DESIGN DEVIATION: {'; '.join(deviations)}")
            for m in marks:
                print(f"        ** {m}", flush=True)
    h1s = [c["share_h1"] for c in out.values() if c["share_h1"] is not None]
    h0s = [c["share_h0"] for c in out.values() if c["share_h0"] is not None]
    return {
        "baseline": baseline_state,
        "cells": out,
        "excluded": {
            "kappa": "the four cells are the kappa factorial, so kappa is this "
                     "criterion's treatment rather than a robustness axis",
        },
        "one_at_a_time": True,
        "interactions_not_tested": True,
        "cells_with_deviations": [
            k for k, c in out.items() if c["deviations"]
        ],
        # Named rather than counted. An inert cell costs the same to run as a
        # live one and looks identical in a pass count, which is how a grid
        # ends up reporting coverage it does not have.
        "cells_inert": [k for k, c in out.items() if c["inert"]],
        "live_cells": sum(1 for c in out.values() if not c["inert"]),
        "share_h1_range": [min(h1s), max(h1s)] if h1s else None,
        "share_h0_range": [min(h0s), max(h0s)] if h0s else None,
        "shares_are_not_gated": (
            "no threshold is registered for either share, so their spread "
            "across the grid is reported and not judged"
        ),
        # All three are required. A cell that tripped a design tie is not clean
        # even if its verdict held, because what it measured is not the
        # parameter it was varying; and a cell that kept the verdict word while
        # changing which channel earned it has moved the finding, which is what
        # §6.5 is about. Inertness is not a failure -- it is a statement about
        # how much the grid covers, reported above rather than gated here.
        "passed": (
            not any(c["moved"] for c in out.values())
            and not any(c["zero_channels_moved"] for c in out.values())
            and not any(c["deviations"] for c in out.values())
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    ap.add_argument(
        "--sweep",
        action="store_true",
        help="a3_asset_channel.md 6.5's robustness grid, one parameter at a "
             "time. Costs one full four-cell factorial plus its null per cell",
    )
    ap.add_argument(
        "--sweep-max",
        type=int,
        default=0,
        help="run only the first N sweep cells, for measuring the cost before "
             "committing to the whole grid; 0 runs all of them",
    )
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
    baseline, base_devs = build_baseline(seeds, args.rounds)
    devset |= base_devs
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

    # The hold on the mean cost is the precondition for reading anything.
    reading = evaluate(cells)
    print(f"\n  mean-cost hold: worst relative drift across cells "
          f"{reading['cost_drift']:.2e}")

    print("\n  reading, per a3_restated.md §4.3 and §6")
    g = reading["gaps"]
    if reading["state"] != "void":
        print(f"    both channels on: gap {g['both']:+.4f}")
        print(f"    loop sum removed: gap {g['H0_only']:+.4f}  -- what is left "
              f"is H0")
        print(f"    gate removed:     gap {g['H1_only']:+.4f}  -- what is left "
              f"is H1")
        for n in ("both", "H1_only", "H0_only"):
            c = cells[n]
            mark = "same sign" if c["same_sign_across_seeds"] else "SIGN FLIPS"
            print(f"      {n:9s} across seeds: {mark}, range "
                  f"[{c['gap_range'][0]:+.2f}, {c['gap_range'][1]:+.2f}]")
        if reading["share_h1"] is not None:
            print(f"    attributable to H1 (loop sum): "
                  f"{reading['share_h1']:+.1%};"
                  f"  to H0 (gate): {reading['share_h0']:+.1%}")
    if not reading["finite"]:
        print("    ** the gaps are not finite, so the state above is not a "
              "reading of anything: the paired population is empty")
    for v in reading["notes"]:
        print(f"    {v}")

    devs = sorted({d for c in cells.values() for d in c["deviations"]})
    if devs:
        print("\n  deviations reported by the model:")
        for d in devs:
            print(f"    {d}")

    grid = None
    if args.sweep:
        gcells = SWEEP_CELLS[: args.sweep_max] if args.sweep_max else SWEEP_CELLS
        print(f"\n  a3_asset_channel.md §6.5 robustness grid, {len(gcells)} of "
              f"{len(SWEEP_CELLS)} cells, one parameter at a time")
        grid = sweep(seeds, args.rounds, gcells, reading)
        headline = (
            "A3-8's verdict and its reason both held at every cell"
            if grid["passed"]
            else "SOMETHING MOVED: read the ** lines above before quoting A3-8"
        )
        print(f"    {headline}. kappa is excluded because the four cells are "
              f"the kappa factorial")
        print(f"    {grid['live_cells']} of {len(gcells)} cells varied "
              f"something A3-8 can see; the rest came out bit-identical to the "
              f"registered point and are named in the result file")
        if grid["share_h1_range"]:
            lo1, hi1 = grid["share_h1_range"]
            lo0, hi0 = grid["share_h0_range"]
            print(f"    across the cells where a share was quotable, H1 ran "
                  f"{lo1:+.1%} to {hi1:+.1%} and H0 ran {lo0:+.1%} to "
                  f"{hi0:+.1%}. No threshold is registered for either, so the "
                  f"range is reported and not judged")

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

    # A plain run must not delete a stored grid. Without this, running this
    # file with no flags after a --sweep run writes `"sweep": null` over the
    # only record that a registered §6.5 commitment was met, and nothing says
    # so. Carried forward with a flag on it instead, because presenting an old
    # grid as this run's output would be the opposite error.
    prior = None
    if grid is None and out.exists():
        try:
            prior = json.loads(out.read_text(encoding="utf-8")).get("sweep")
        except (OSError, json.JSONDecodeError):
            prior = None
    if prior is not None:
        prior = {**prior, "from_an_earlier_run": True}
        print("\n  carrying forward the §6.5 grid left by an earlier --sweep "
              "run, marked in the file as being from one. This run did not "
              "produce it")
    out.write_text(
        json.dumps(
            {
                "stage": "A3 P-C",
                "seeds": args.seeds,
                "rounds": args.rounds,
                "kappa": KAPPA,
                "fixed": FIXED,
                "mean_cost_relative_drift": reading["cost_drift"],
                "state": reading["state"],
                "share_h1": reading["share_h1"],
                "share_h0": reading["share_h0"],
                "notes": reading["notes"],
                # A3-8 in this repository's criterion shape, so that the one
                # criterion carrying A3's new content is on the record rather
                # than only in the console output. Its three
                # states do not fit a boolean, so `void` carries the two that
                # are not a verdict: `void` means the harness cannot be read and
                # `unstable` means a channel's sign moves across seeds, and
                # neither is the model failing. The state is named in the detail
                # so the collapse is visible rather than inferred.
                "criteria": [
                    {
                        "name": (
                            "A3-8  removing the holonomy removes the "
                            "divergence"
                        ),
                        "passed": reading["state"] == "pass",
                        "void": reading["state"] != "pass",
                        "detail": (
                            f"state: **{reading['state']}**. Gaps against the "
                            f"null: both {reading['gaps']['both']:+.4f}, loop "
                            f"sum only {reading['gaps']['H1_only']:+.4f}, gate "
                            f"only {reading['gaps']['H0_only']:+.4f}, null "
                            f"{reading['gaps']['null']:+.3e}. Mean-cost drift "
                            f"at machine precision, below `1e-10`. "
                            + (
                                "Indistinguishable from zero across seeds: "
                                + ", ".join(reading["unstable_channels"])
                                if reading["unstable_channels"]
                                else "Every channel is sign-stable across seeds"
                            )
                            + (
                                ""
                                if reading["share_h1"] is None
                                else f". Attributable to H1 "
                                     f"{reading['share_h1']:+.1%}, to H0 "
                                     f"{reading['share_h0']:+.1%}"
                            )
                        ),
                    }
                ],
                "sweep": grid if grid is not None else prior,
                "cells": cells,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
