"""A6-7 to A6-23: the frontier ratchet, the levy base, the rebate base, the
scaling of ``R*`` with ``λ``, and the curve re-measured on all of it.

Registered in ``docs/a6_siphon_cost.md``, sections 13, 14.7, 15, 18, 19
and 20.

This file evaluates and does not design. Every threshold, grid and scope
decision it compares against is written in that document, before any of this
ran.

Usage::

    python experiments/a6_ratchet.py
    python experiments/a6_ratchet.py --smoke        # tiny, proves nothing
    python experiments/a6_ratchet.py --guard-only   # A6-7 and A6-8, then stop

Writes ``results/a6_ratchet.json``.

**A6-7 is a gate and is enforced as one.** Section 12.6 says a generalisation
that cannot reproduce its special case is not a generalisation, so the reduction
guard runs first and nothing below it runs if it fails. The guard compares
``A6RatchetModel`` under a default ``RatchetSpec`` against the unmodified
``A6Model`` in this same process, bit for bit, which makes it a statement about
two code paths rather than about two machines.

What the stage is for, in one paragraph. Section 9.2 found that the
infrastructure arm has **no steady state**: cumulative investment only ever
increases, so the levy rate sets how fast the arm seals the production layer's
upward leak and not where it stops, the financial layer is starved to nothing at
saturation, and two of five seeds then collapse because the production layer
cannot circulate on its own. The ratchet gives the arm a stop. The absorbed
baseline chases the built stock, the gap settles at ``I/λ``, and because ``I`` is
itself the levy on a financial layer that empties as the leak closes, the loop
has negative feedback where it previously had none. **A6-9 asks whether that
removes the collapse, A6-10 asks whether it turns ``R*`` back into a price.**
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    NetworkConfig,
    NetworkSpec,
)
from monetary_topology.redistribution import (  # noqa: E402
    RATE_GRID,
    A6Config,
    A6Model,
    A6RatchetModel,
    FiscalSpec,
    LevySpec,
    RatchetSpec,
    RebateSpec,
    open_band,
    run_a6,
    scan_rates,
    support_trend,
)

RESULTS = ROOT / "results"

# --------------------------------------------------------------------------
# section 13's registered values, named here so a reader can check them against
# the document rather than hunting through the code
# --------------------------------------------------------------------------

REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300
REGISTERED_LONG = 2000

#: Section 13.2. ``0`` is the reduction point and is included so the curve has
#: today's model as its left endpoint rather than as a separate story.
LAMBDA_GRID: tuple[float, ...] = (
    0.0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
)

#: Section 13.2. ``exp`` is the registered default and ``hill`` the robustness
#: axis; A6-10 and A6-11 are judged on ``exp`` alone and ``hill`` feeds A6-13.
SHAPE_DEFAULT = "exp"
SHAPE_AXIS = "hill"
SHAPES_RUN: tuple[str, ...] = (SHAPE_DEFAULT, SHAPE_AXIS)

#: Section 14.7. The wall, swept across the same lambda grid as a control
#: column. It feeds A6-14 and A6-15 only: it is not in A6-13, which compares the
#: two smooth shapes, and it is not rescanned for ``R*``.
SHAPE_CONTROL = "clip"
CURVE_SHAPES: tuple[str, ...] = (*SHAPES_RUN, SHAPE_CONTROL)

#: Section 14.7, A6-14. Section 9.2's two-thousand-round reading, to the two
#: decimals it printed. The control column at ``λ = 0`` goes through the
#: reduction path A6-7 proved bit-identical to ``A6Model``, at the same rate,
#: seeds and horizon, so this should reproduce exactly rather than closely.
A6_5_RECORDED: tuple[float, ...] = (1.66, 0.07, 1.60, 1.86, 0.15)
A6_14_TOL = 0.005

#: Section 14.7, A6-15. Four pinned cells of the control column. The crossover
#: from closed to open is reported and not predicted, because the financial
#: layer's share is endogenous and moves with how much the wall seals.
A6_15_CLOSED: tuple[float, ...] = (0.0, 1e-4, 1e-1)
A6_15_OPEN: tuple[float, ...] = (1e-2,)
A6_15_CROSSOVER_WINDOW: tuple[float, ...] = (3e-4, 1e-3, 3e-3)

#: Section 13.7. The expensive scan runs at two values of ``λ``, and they
#: bracket ``x* = 1`` at ``R = 0.005`` by the arithmetic in section 13.3.
RESCAN_LAMBDAS: tuple[float, ...] = (1e-3, 1e-2)

#: Section 13.4. A6-9's rate is the three-hundred-round ``R*`` already on
#: record, not a rate chosen for this run.
A6_9_RATE = 0.005

#: Section 13.4. One-sided: ending more open than it began is not a failure,
#: and A6-5's symmetric band could not tell the two apart.
A6_9_FLOOR = 0.9

#: Section 13.4, reusing A6-4's registered threshold unchanged.
A6_11_RATIO = 0.75

#: Section 13.4.
A6_8_TOL = 1e-9
A6_8_LAMBDAS: tuple[float, ...] = (1e-4, 1e-3, 1e-2, 1e-1)
A6_8_INJECTIONS: tuple[float, ...] = (1.0, 0.0034, 250.0)

#: Section 13.4. The guard's registered scope.
GUARD_RATES: tuple[float, ...] = (0.0, 0.005, 0.06, 0.32)

#: A6-16, A6-17 and A6-19, the long-horizon test. A6-5's own warning applied to
#: this stage's conclusion: three hundred rounds was enough to find `R*` and not
#: enough to claim "forever", and two thousand rounds is not enough to claim
#: that a smooth `g` removes the collapse rather than postponing it.
#:
#: **Raised from twelve thousand on 2026-08-12, and that is not a change of
#: criterion.** A6-16 was built three-valued precisely so that "the horizon is
#: too short" would trigger a longer run instead of a wrong answer, and it
#: returned that branch at twelve thousand with `layer/hill`'s `x` still
#: climbing at fifty percent per six thousand rounds. Extending is the response
#: the criterion prescribes. Sixty thousand comes from two independent readings,
#: not from convenience: `layer/hill`'s `x` fits `4.50·ln t − 30.35` across five
#: seeds, putting a surviving leak of `0.05` at about fifty-eight thousand
#: rounds; and `threshold/hill`'s `x` grows close to linearly at `2.45e-3` per
#: round, giving `x ≈ 147` and a leak near `0.0068` at sixty thousand, inside
#: the range where closure has already been observed. Section 15.11.
HORIZON_ROUNDS = 60000

#: Two judged cells and one control. The control has a genuine fixed point in
#: `x` at about `0.87` and a surviving leak of `0.12`, well clear of the
#: boundary, so it should stay open at any horizon. **If the control closes
#: too, long horizons close everything and the two judged cells say nothing
#: about `g`**, so A6-16 returns no verdict rather than a wrong one.
#: **Two criteria share this block and neither reads the other's rows.** A6-16
#: asks whether a smooth `g` removes the collapse or postpones it, on the
#: `layer` base, and it stays there because a criterion is not moved to another
#: arm after returning a verdict, even a null one. **A6-19 asks the same
#: question on the `threshold` base**, with its own control.
#:
#: The two controls differ, and the difference is measured rather than assumed.
#: `clip/λ=1e-3` has a settled fixed point at `x ≈ 0.87` and a surviving leak of
#: `0.12` under the layer base, so it holds at any horizon. Under the threshold
#: base the same cell **closes**, because a base that does not drain keeps `I`
#: three times higher and moves `x*` to `2.74`, above the wall's corner at one.
#: A6-19's control is therefore `clip/λ=1e-2`, whose fixed point is `x* ≈ 0.27`
#: and whose surviving leak is about `0.73`. Section 15.9 and section 15.11.
#: The last column is a **per-cell multiple of the horizon**, and it sets a run
#: length rather than a threshold. Every criterion in this block is unchanged:
#: five seeds, ``end/start >= 0.90``, the same three-valued rule. What the
#: multiple does is give each cell enough rounds for its own ``x`` to reach the
#: range where closure has already been observed, sized from that cell's own
#: measured growth.
#:
#: Only ``layer/hill`` needs more than one. At sixty thousand rounds it sits at
#: ``x = 28`` to ``34`` with seed 1 at ``0.92`` against the floor, and its
#: increments per twelve thousand rounds are ``5.97, 4.68, 3.98, 3.52``,
#: decelerating. Seed 1 closed under ``threshold/hill`` at ``x ≈ 42``, so this
#: cell needs about eleven and a half more, which those increments deliver in
#: four to five more blocks, near a hundred and twenty thousand rounds.
#: **Three times is deliberate margin**: overshooting costs three minutes of
#: compute, undershooting costs another null verdict and another pass over the
#: whole stage.
HORIZON_CELLS: tuple[tuple[str, float, str, str, int], ...] = (
    ("exp", 0.0, "layer", "judged", 1),
    ("hill", 0.0, "layer", "judged", 3),
    ("clip", 1e-3, "layer", "control", 1),
    ("exp", 0.0, "threshold", "levy-judged", 1),
    ("hill", 0.0, "threshold", "levy-judged", 1),
    ("clip", 1e-2, "threshold", "levy-control", 1),
)

#: A6-18. The levy collected in the final round, as a fraction of the opening
#: claim stock, at or above which the base counts as still alive. Set at the
#: scale of numerical noise rather than at a level chosen to taste: the
#: registered claim is that the threshold base **does not die**, so the test is
#: that it is not approximately zero, and the magnitudes are reported beside
#: the verdict rather than being turned into a threshold nobody had seen.
A6_18_FLOOR = 1e-6

#: A6-20's conservation tolerance. Not a measurement tolerance: the levy
#: and the rebate are the same float total added and subtracted, so the
#: only thing between them is accumulated rounding over the horizon. Set
#: well above float noise and far below any transfer the model makes, so a
#: real leak of claims could not hide under it.
A6_20_DRIFT = 1e-6

#: Relative growth of `x` across the second half of the run, at or below which
#: `x` counts as settled. Registered rather than chosen at reading time, and
#: the measured growth is printed beside every verdict so a reading that rests
#: on the threshold can be seen to rest on it.
X_SETTLED = 0.01

#: Measured growth inside this band means the settled/climbing call is decided
#: by the threshold and not by the data. Flagged, and the cell's reading is
#: declared non load-bearing.
X_SETTLED_MARGINAL: tuple[float, float] = (0.005, 0.02)

#: Fractions of the horizon at which `x` is recorded, so that the shape of the
#: approach is visible instead of only its endpoint. No extrapolation is done
#: from these: inventing a crossing round the run did not reach would be
#: inventing a price for a path that was not simulated.
HORIZON_CHECKPOINTS: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.0)

#: Repeated from ``a6_siphon_cost.py`` so that landing on the grid's smallest
#: non-zero point can be recognised. A6-10 is exactly the question of whether
#: this still happens once the arm has a stop.
FIRST_NONZERO = 0.005

#: Section 14.7. Three points below ``0.005``, because A6-10 failed at
#: ``λ = 1e-3`` on resolution rather than on mechanism. **``RATE_GRID`` itself is
#: not touched**: ``a6_siphon_cost.py`` reads it and section 9.2's numbers have
#: to stay reproducible, so the refinement is a constant of this stage alone.
#: It contains the registered grid as a subset, so one scan yields both the
#: registered verdict and the refined reading and they cannot come from
#: different runs.
RATE_GRID_FINE: tuple[float, ...] = (
    0.0, 0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08,
    0.12, 0.16, 0.24, 0.32, 0.48, 0.64, 0.80, 0.95,
)
FIRST_NONZERO_FINE = 0.001

#: Where each registered rate sits in the refined grid. Building this raises if
#: the refinement ever stops being a superset, which is the property the whole
#: arrangement rests on.
REGISTERED_INDEX: tuple[int, ...] = tuple(
    RATE_GRID_FINE.index(rate) for rate in RATE_GRID
)


def config_for(
    seed: int,
    rounds: int,
    access: bool,
    fair: bool,
    channel: str,
    rate: float = 0.0,
    ratchet: RatchetSpec | None = None,
    levy: LevySpec | None = None,
    rebate: RebateSpec | None = None,
) -> A6Config:
    """One cell of section 4's factorial, at one levy rate.

    ``access`` is the stratified graph; its absence is ``uniform_access``.
    Issuance is off in every cell, which is what makes ``R*`` a measurement of
    the economy rather than of the monetary authority.
    """
    return A6Config(
        fiscal=FiscalSpec(channel=channel, fair_retention=fair, rate=rate),
        network=NetworkConfig(
            spec=NetworkSpec(seed=seed, uniform_access=not access),
            seed=seed,
            rounds=rounds,
            authority=MonetaryAuthority(rule="none"),
        ),
        ratchet=ratchet or RatchetSpec(),
        levy=levy or LevySpec(),
        rebate=rebate or RebateSpec(),
    )


def _quiet(fn, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*args, **kwargs)


# --------------------------------------------------------------------------
# A6-7. The gate
# --------------------------------------------------------------------------


def reduction_guard(seeds: range, rounds: int, rates: tuple[float, ...]) -> dict:
    """A6-7. Bit-identical, or the three new parameters do not enter.

    Not ``allclose``. The point of the guard is that the generalisation
    computes the same expression on the same bits, and a tolerance would hide
    exactly the kind of reordering that makes two runs agree to twelve digits
    and disagree about which of them is the special case.
    """
    mismatches: list[dict] = []
    pairs = 0
    for access, fair, channel in itertools.product(
        (True, False), (True, False), ("transfer", "infrastructure")
    ):
        for rate in rates:
            for seed in seeds:
                cfg = config_for(seed, rounds, access, fair, channel, rate)
                base, base_h = _quiet(run_a6, cfg)
                new, new_h = _quiet(run_a6, cfg, model_cls=A6RatchetModel)
                pairs += 1
                differs = [
                    name
                    for name, same in (
                        ("effective_support", np.array_equal(
                            base_h.effective_support,
                            new_h.effective_support)),
                        ("holdings", np.array_equal(
                            base_h.holdings, new_h.holdings)),
                        ("total_volume", np.array_equal(
                            base_h.total_volume, new_h.total_volume)),
                        ("leak_factor", base.leak_factor == new.leak_factor),
                        ("invested", base.invested == new.invested),
                        ("palma_history", np.array_equal(
                            np.asarray(base.palma_history),
                            np.asarray(new.palma_history))),
                    )
                    if not same
                ]
                if differs:
                    mismatches.append({
                        "access": access, "fair": fair, "channel": channel,
                        "rate": rate, "seed": seed, "fields": differs,
                    })
    return {
        "pairs": pairs,
        "rates": list(rates),
        "rounds": rounds,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:10],
        "passed": not mismatches,
    }


# --------------------------------------------------------------------------
# A6-8. The fixed point, on a bench with no economy in it
# --------------------------------------------------------------------------


def bench_gap(absorption: float, injection: float, rounds: int) -> float:
    """The two state equations and nothing else, in the model's own order.

    The baseline absorbs before the new building lands. That order is what puts
    the fixed point at ``I/λ`` rather than at ``I·(1−λ)/λ``, and it is the order
    ``A6RatchetModel`` uses. ``tests/test_a6_ratchet.py`` pins both.
    """
    built = baseline = 0.0
    for _ in range(rounds):
        baseline += absorption * (built - baseline)
        built += injection
    return built - baseline


def fixed_point_bench() -> dict:
    """A6-8. ``K - B -> I/λ``, which is section 12.2's claim on the mechanism.

    Arithmetic rather than economics. It exists because the whole argument for
    the ratchet is that the fixed point falls out of the mechanism instead of
    being bolted on, and if the code settles somewhere else then the mechanism
    in the document is not the mechanism in the model.
    """
    rows = []
    for absorption, injection in itertools.product(
        A6_8_LAMBDAS, A6_8_INJECTIONS
    ):
        rounds = int(20 * 9 / absorption) + 1000
        gap = bench_gap(absorption, injection, rounds)
        want = injection / absorption
        rows.append({
            "absorption": absorption,
            "injection": injection,
            "rounds": rounds,
            "gap": float(gap),
            "expected": float(want),
            "relative_error": float(abs(gap - want) / want),
        })
    return {
        "tolerance": A6_8_TOL,
        "rows": rows,
        "passed": all(r["relative_error"] <= A6_8_TOL for r in rows),
    }


# --------------------------------------------------------------------------
# A6-9. The lambda curve
# --------------------------------------------------------------------------


def lambda_cell(
    seeds: range,
    absorption: float,
    shape: str,
    rounds: int,
    rate: float,
    levy: LevySpec | None = None,
    rebate: RebateSpec | None = None,
) -> dict:
    """One point of the curve: five long runs in ``access / fair / arm I``.

    ``levy`` and ``rebate`` are section 20's re-measurement and default to
    ``None``, which is the registered instrument. A6-9 calls this without them
    and its numbers are unchanged.
    """
    ratios, trends, gaps, xs, leaks = [], [], [], [], []
    for seed in seeds:
        cfg = config_for(
            seed, rounds, access=True, fair=True, channel="infrastructure",
            rate=rate,
            ratchet=RatchetSpec(absorption=absorption, shape=shape),
            levy=levy,
            rebate=rebate,
        )
        model, history = _quiet(run_a6, cfg, model_cls=A6RatchetModel)
        y = np.asarray(history.effective_support, dtype=float)
        ratios.append(float(y[-1] / y[0]) if y[0] else float("nan"))
        trends.append(support_trend(y, last=500))
        gap = model.gap_history[-1] if model.gap_history else 0.0
        gaps.append(gap)
        # ``x``, the dimensionless argument of ``g``. Section 13.3's arithmetic
        # is about this and not about the raw gap; keeping both under names that
        # say which is which is section 14.7's repair of a key that did not.
        xs.append(cfg.fiscal.leak_response * gap / model._opening_claims)
        leaks.append(model.leak_history[-1] if model.leak_history else 1.0)
    return {
        "absorption": absorption,
        "shape": shape,
        "end_over_start": [float(r) for r in ratios],
        "tail_trend": [float(t) for t in trends],
        "final_gap": [float(g) for g in gaps],
        "final_x": [float(x) for x in xs],
        "final_leak_factor": [float(x) for x in leaks],
        # A6-9's own test, one-sided.
        "open_in_every_seed": bool(
            ratios and all(r >= A6_9_FLOOR for r in ratios)
        ),
        # Reported beside it because A6-5's symmetric band scored these two
        # opposite outcomes as one failure, and section 9.2 records that.
        "seeds_below_start": int(sum(r < 1.0 for r in ratios)),
        "seeds_above_start": int(sum(r > 1.0 for r in ratios)),
    }


def lambda_curve(
    seeds: range,
    rounds: int,
    rate: float,
    grid: tuple[float, ...],
    shapes: tuple[str, ...],
    progress: bool,
) -> dict:
    """A6-9. The whole curve, both shapes, no preferred ``λ`` nominated."""
    cells: dict[str, dict] = {}
    for shape, absorption in itertools.product(shapes, grid):
        key = f"{shape}/lambda={absorption:g}"
        started = time.time()
        cells[key] = lambda_cell(seeds, absorption, shape, rounds, rate)
        if progress:
            mark = "open" if cells[key]["open_in_every_seed"] else "closed"
            print(f"      {key:24s} {mark:6s} "
                  f"{time.time() - started:5.1f}s", flush=True)

    bands = {}
    for shape in shapes:
        good = [
            a for a in grid
            if cells[f"{shape}/lambda={a:g}"]["open_in_every_seed"]
        ]
        inside = [
            cells[f"{shape}/lambda={a:g}"]["open_in_every_seed"]
            for a in grid
            if good and good[0] <= a <= good[-1]
        ]
        bands[shape] = {
            "low": (good[0] if good else None),
            "high": (good[-1] if good else None),
            "points": [float(a) for a in good],
            "contiguous": bool(all(inside)),
            "non_empty": bool(good),
        }
    return {
        "rate": rate,
        "rounds": rounds,
        "floor": A6_9_FLOOR,
        "cells": cells,
        "bands": bands,
        "passed": bool(bands[SHAPE_DEFAULT]["non_empty"]),
    }


# --------------------------------------------------------------------------
# A6-10, A6-11, A6-12. The rescan
# --------------------------------------------------------------------------


def summarise(
    grid: tuple[float, ...],
    vectors: list[list[bool]],
    first_nonzero: float,
) -> dict:
    """``R*`` and the band's two ends, per seed, on one grid.

    Called twice per cell on the same runs: once on the registered grid and
    once on the refinement. Both readings therefore come from a single scan and
    cannot disagree because one of them was measured on a different day.
    """
    rates: list[float | None] = []
    highs: list[float | None] = []
    contiguous: list[bool] = []
    for verdicts in vectors:
        low, high, ok = open_band(grid, verdicts)
        rates.append(low)
        highs.append(high)
        contiguous.append(ok)
    found = [r for r in rates if r is not None]
    return {
        "grid_first_nonzero": first_nonzero,
        "rates": rates,
        "band_high": highs,
        "band_contiguous": contiguous,
        "median": float(np.median(found)) if found else None,
        "unsolved_seeds": int(sum(r is None for r in rates)),
        # A6-10's own test. ``True`` here is the failure: it says the scan
        # established ``R* <=`` the grid's first non-zero point and nothing
        # finer, which is section 9.2's reading that the rate does not control
        # this channel.
        "at_grid_floor": bool(found and max(found) <= first_nonzero),
        "monotone_above": bool(
            all(h == grid[-1] for h in highs if h is not None)
            and all(contiguous)
        ),
    }


def scan_cell(
    seeds: range,
    rounds: int,
    channel: str,
    ratchet: RatchetSpec | None,
    progress_label: str,
    progress: bool,
) -> dict:
    """``R*`` per seed from the full verdict vector, plus the band's two ends.

    The vector rather than its first entry, because section 9.1 recorded that
    this arm is not monotone and left the top of the working band unlocated.
    That top is A6-12.
    """
    started = time.time()
    vectors: list[list[bool]] = []
    for seed in seeds:
        cfg = config_for(
            seed, rounds, access=True, fair=True, channel=channel,
            ratchet=ratchet,
        )
        model_cls = A6Model if ratchet is None else A6RatchetModel
        verdicts = _quiet(
            scan_rates, cfg, grid=RATE_GRID_FINE, model_cls=model_cls
        )
        vectors.append([bool(v) for v in verdicts])

    registered_vectors = [
        [v[i] for i in REGISTERED_INDEX] for v in vectors
    ]
    out = {
        "channel": channel,
        "rounds": rounds,
        "grid": list(RATE_GRID_FINE),
        "contracted_by_rate": vectors,
        # The verdict that goes to `criteria`, on the grid section 13 registered
        # and against the floor it registered. Section 14.7: the refinement is a
        # re-measurement and never a repaired criterion.
        "registered": summarise(RATE_GRID, registered_vectors, FIRST_NONZERO),
        "refined": summarise(
            RATE_GRID_FINE, vectors, FIRST_NONZERO_FINE
        ),
    }
    if progress:
        reg, fine = out["registered"], out["refined"]
        print(f"      {progress_label:28s} "
              f"R*(reg)={reg['median']} floor={reg['at_grid_floor']}  "
              f"R*(fine)={fine['median']} floor={fine['at_grid_floor']}  "
              f"unsolved={reg['unsolved_seeds']} "
              f"{time.time() - started:5.1f}s", flush=True)
    return out


def ratio_block(infra: dict, transfer: dict, readout: str) -> dict:
    """``R*(I) / R*(T)`` per seed, on one of the two grid readouts."""
    out = {}
    for key, cell in infra.items():
        per_seed = [
            (a / b) if (a is not None and b) else None
            for a, b in zip(
                cell[readout]["rates"],
                transfer[readout]["rates"],
                strict=True,
            )
        ]
        good = [x for x in per_seed if x is not None]
        out[key] = {
            "per_seed": per_seed,
            "median": float(np.median(good)) if good else None,
            "all_below_threshold": bool(good) and all(
                x < A6_11_RATIO for x in good
            ),
            # A ratio built on a cell sitting at the grid floor is a bound in
            # the direction that favours the framework, which is what section
            # 9.2 withdrew A6-4's reading over.
            "is_upper_bound": cell[readout]["at_grid_floor"],
        }
    return out


def rescan(
    seeds: range,
    rounds: int,
    lambdas: tuple[float, ...],
    shapes: tuple[str, ...],
    progress: bool,
) -> dict:
    """A6-10, A6-11 and A6-12, from one pass over the grid per cell."""
    transfer = scan_cell(
        seeds, rounds, "transfer", None, "transfer (denominator)", progress
    )
    infra: dict[str, dict] = {}
    for shape, absorption in itertools.product(shapes, lambdas):
        key = f"{shape}/lambda={absorption:g}"
        infra[key] = scan_cell(
            seeds, rounds, "infrastructure",
            RatchetSpec(absorption=absorption, shape=shape),
            f"infra {key}", progress,
        )

    ratios = {
        readout: ratio_block(infra, transfer, readout)
        for readout in ("registered", "refined")
    }

    judged = [f"{SHAPE_DEFAULT}/lambda={a:g}" for a in lambdas]

    def verdicts(readout: str) -> tuple[bool, bool]:
        ten = all(
            infra[k][readout]["unsolved_seeds"] == 0
            and not infra[k][readout]["at_grid_floor"]
            for k in judged
        )
        eleven = all(
            ratios[readout][k]["all_below_threshold"]
            and not ratios[readout][k]["is_upper_bound"]
            for k in judged
        )
        return ten, eleven

    a6_10, a6_11 = verdicts("registered")
    fine_10, fine_11 = verdicts("refined")
    return {
        "threshold": A6_11_RATIO,
        "judged_cells": judged,
        "transfer": transfer,
        "infrastructure": infra,
        "ratios": ratios,
        # The registered verdicts. These are what reach `criteria`.
        "A6-10": a6_10,
        "A6-11": a6_11,
        # The re-measurement at higher resolution, reported beside them and
        # never substituted for them. Section 14.7.
        "refined_A6-10": fine_10,
        "refined_A6-11": fine_11,
    }


# --------------------------------------------------------------------------
# A6-13. Does the answer rest on g's tail
# --------------------------------------------------------------------------


def closed_at_round(series: np.ndarray, floor: float) -> int | None:
    """The round after which the support set never came back to the floor.

    Scanned **backwards** from the end. Looking forwards for the first dip
    below would report a transient that recovered, and a run that dips and
    returns has not closed. Returns ``None`` when the run ends at or above the
    floor.
    """
    y = np.asarray(series, dtype=float)
    below = y < y[0] * floor
    if not below[-1]:
        return None
    t = y.size - 1
    while t > 0 and below[t - 1]:
        t -= 1
    return int(t)


def horizon_cell(
    seeds: range,
    shape: str,
    absorption: float,
    levy_base: str,
    rounds: int,
    rate: float,
    role: str,
) -> dict:
    """One cell of the long-horizon test: does ``x`` settle, and where?

    Two things are read and they answer different questions. **Whether ``x``
    settles** decides whether this run is a final answer or a snapshot, because
    "still climbing towards the boundary" and "stopped above the boundary" have
    the same endpoint and opposite meanings. **Where it settles** decides open
    or closed, against the surviving-leak boundary the `λ` curve bracketed.

    The wall is already known to settle: it stops at ``x = 1`` exactly, because
    sealing the leak destroys the levy base that was funding the building. The
    open question is whether a smooth ``g`` self-limits the same way, and if it
    does, on which side of the boundary it stops.
    """
    ratios, leaks, crossings = [], [], []
    traces: list[list[float]] = []
    growth: list[float] = []
    levy_first, levy_final, levy_share = [], [], []
    payers: list[int] = []
    for seed in seeds:
        cfg = config_for(
            seed, rounds, access=True, fair=True, channel="infrastructure",
            rate=rate,
            ratchet=RatchetSpec(absorption=absorption, shape=shape),
            levy=LevySpec(base=levy_base),
        )
        model, history = _quiet(run_a6, cfg, model_cls=A6RatchetModel)
        y = np.asarray(history.effective_support, dtype=float)
        claims = model._opening_claims
        xs = (
            np.asarray(model.gap_history, dtype=float)
            * cfg.fiscal.leak_response
            / claims
        )
        ratios.append(float(y[-1] / y[0]) if y[0] else float("nan"))
        leaks.append(float(model.leak_history[-1]))
        crossings.append(closed_at_round(y, A6_9_FLOOR))
        traces.append([
            float(xs[min(int(f * xs.size), xs.size - 1)])
            for f in HORIZON_CHECKPOINTS
        ])
        mid = float(xs[xs.size // 2])
        end = float(xs[-1])
        growth.append((end - mid) / mid if mid else float("inf"))
        levy_first.append(model.levy_history[0] / claims)
        levy_final.append(model.levy_history[-1] / claims)
        levy_share.append(model.l2_levy_share_history[-1])
        payers.append(model.payer_count_history[-1])

    settled = all(g <= X_SETTLED for g in growth)
    worst = max(growth)
    return {
        "shape": shape,
        "absorption": absorption,
        "levy_base": levy_base,
        "role": role,
        "rounds": rounds,
        # All in units of the opening claim stock, so the numbers are
        # comparable across cells and across any future change of scale.
        "levy_first_round": levy_first,
        "levy_final_round": levy_final,
        "final_payer_count": payers,
        "final_l2_levy_share": levy_share,
        # A6-18's own test: the base is still collecting something.
        "levy_alive": bool(all(v >= A6_18_FLOOR for v in levy_final)),
        "end_over_start": ratios,
        "final_leak_factor": leaks,
        "final_x": [t[-1] for t in traces],
        "x_checkpoints": traces,
        "checkpoint_fractions": list(HORIZON_CHECKPOINTS),
        "x_growth_second_half": growth,
        "x_settled": bool(settled),
        "open_in_every_seed": bool(all(r >= A6_9_FLOOR for r in ratios)),
        "closed_at_round": crossings,
        # True when the settled/climbing call is decided by the threshold
        # rather than by the data, in which case this cell carries nothing.
        "settling_call_is_marginal": bool(
            X_SETTLED_MARGINAL[0] <= worst <= X_SETTLED_MARGINAL[1]
        ),
    }


def three_valued(
    cells: dict, judged_role: str, control_role: str, label: str
) -> dict:
    """One criterion's verdict on one levy base. ``True``, ``False`` or ``None``.

    A6-16 and A6-19 ask the same question of two different bases and share this
    rule, so it lives in one place and neither can drift from the other.

    - both judged cells closed: the registered prediction holds
    - a judged cell open with ``x`` settled: the prediction is wrong there
    - a judged cell open with ``x`` still climbing: **no verdict.** The horizon
      is too short, and A6-5 was scored on a two-thousand-round run while
      section 5 says in as many words that three hundred rounds is "not enough
      to claim forever". Returning a pass here would repeat that
    - the control closed as well: **no verdict.** Long horizons close
      everything on this base and the judged cells are confounded
    """
    judged = [c for c in cells.values() if c["role"] == judged_role]
    control = [c for c in cells.values() if c["role"] == control_role]
    if not judged or not control:
        return {
            "passed": None,
            "control_open": False,
            "reason": f"the {label} base has no judged or no control cell "
                      f"in this run",
        }
    control_open = all(c["open_in_every_seed"] for c in control)
    if not control_open:
        verdict, why = None, (
            f"the {label} control closed as well, so this horizon closes "
            f"everything on this base and the judged cells are confounded"
        )
    elif all(not c["open_in_every_seed"] for c in judged):
        verdict, why = True, (
            f"both judged cells closed on the {label} base, which is what the "
            f"surviving-leak reading predicts: a smooth g postpones the "
            f"collapse rather than removing it"
        )
    elif any(c["open_in_every_seed"] and not c["x_settled"] for c in judged):
        verdict, why = None, (
            f"a judged cell on the {label} base is still open with x still "
            f"climbing, so this horizon cannot decide it. Reported as no "
            f"verdict rather than as a pass, which is A6-5's mistake"
        )
    else:
        verdict, why = False, (
            f"a judged cell on the {label} base is open with x settled, so a "
            f"smooth g removes the collapse on its own there"
        )
    return {
        "passed": verdict,
        "control_open": bool(control_open),
        "reason": why,
    }


#: Section 20.2. The `λ` set the re-measurement walks. `3e-4` and below are
#: excluded on cost, the same budget decision section 19.3 records; `0` is
#: excluded because it has no fixed point to relax to, so no horizon rule can
#: make its reading settled, which section 16.6 already records.
A6_22_LAMBDAS: tuple[float, ...] = (1e-3, 3e-3, 1e-2, 3e-2, 1e-1)

#: Section 20.2's factorial. One change at a time, so that a difference between
#: the corrected instrument and section 13.4's reading can be attributed to the
#: horizon, the levy base or the rebate base rather than to all three at once.
#: ``C`` is the corrected instrument and is the column A6-22 and A6-23 judge.
REBASE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("A", "layer", "layer"),
    ("B", "threshold", "layer"),
    ("C", "threshold", "threshold"),
)

#: Section 19.2. The ratio grid A6-21 scans in place of a rate grid. Geometric
#: with a factor of two, so ``ρ*`` resolves to within a factor of two and that
#: resolution **is** the criterion's tolerance: section 19.2 registers "the same
#: grid point or one step apart" and registers no other band.
RHO_GRID: tuple[float, ...] = (0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)

#: Section 19.2. One decade. ``λ = 3e-4`` and below are excluded on cost, which
#: section 19.3 records as a limit on the span rather than as a finding.
A6_21_LAMBDAS: tuple[float, ...] = (1e-3, 3e-3, 1e-2)

#: Section 19.3. Ten relaxation times, or the stage's registered long horizon,
#: whichever is larger. The ratchet approaches ``I/λ`` at rate ``λ`` per round,
#: so a cell shorter than a few multiples of ``1/λ`` reports a transient and not
#: the fixed point the criterion is about.
A6_21_RELAXATIONS = 10


def a6_21_rounds(absorption: float) -> int:
    """Section 19.3's horizon rule, as one function so it cannot drift."""
    return max(REGISTERED_LONG, math.ceil(A6_21_RELAXATIONS / absorption))


def rho_scaling(seeds: range, progress: bool, smoke: bool = False) -> dict:
    """A6-21. Is ``R*`` a slope in ``λ`` rather than a level?

    Registered in section 19 before this function existed. It scans
    ``R = ρ·λ`` over :data:`RHO_GRID` at each :data:`A6_21_LAMBDAS`, in the arm
    A6-10 is judged in, and asks whether ``ρ*`` is the same grid point
    throughout.

    **A6-10 and A6-11 are untouched by this.** They keep their failures, their
    thresholds and their split. This is a different question about the same
    mechanism, in the relation to them that A6-18 stands in to A6-1.

    ``I(R*)/λ`` and the settledness of ``x`` are measured and **reported, not
    judged**, per section 19.4. The first is the parameter-free form of the same
    hypothesis and the second is what stops "the horizon rule was followed" from
    being mistaken for "the fixed point was reached".
    """
    # A smoke run is off every registered parameter by design and says so.
    # Section 19.3's horizon rule is what makes this criterion expensive, so a
    # smoke run that honoured it would not be a smoke run.
    lambdas = (3e-3, 1e-2) if smoke else A6_21_LAMBDAS
    cells: dict[str, dict] = {}
    for absorption in lambdas:
        rounds = 300 if smoke else a6_21_rounds(absorption)
        rates = tuple(rho * absorption for rho in RHO_GRID)
        started = time.time()
        rho_star: list[float | None] = []
        levy_over_lambda: list[float] = []
        growth: list[float] = []
        for seed in seeds:
            cfg = config_for(
                seed, rounds, access=True, fair=True,
                channel="infrastructure",
                ratchet=RatchetSpec(absorption=absorption, shape=SHAPE_DEFAULT),
            )
            verdicts = _quiet(
                scan_rates, cfg, grid=rates, model_cls=A6RatchetModel
            )
            open_at = [
                rho for rho, bad in zip(RHO_GRID, verdicts, strict=True)
                if not bad
            ]
            if not open_at:
                rho_star.append(None)
                continue
            rho_star.append(open_at[0])
            # One extra run at this seed's own critical rate, to read the levy
            # actually collected there and whether `x` had settled. Reading it
            # at the median instead would attribute one seed's levy to another.
            crit = config_for(
                seed, rounds, access=True, fair=True,
                channel="infrastructure", rate=open_at[0] * absorption,
                ratchet=RatchetSpec(absorption=absorption, shape=SHAPE_DEFAULT),
            )
            model, _ = _quiet(run_a6, crit, model_cls=A6RatchetModel)
            claims = model._opening_claims
            levy_over_lambda.append(
                float(model.levy_history[-1]) / claims / absorption
            )
            xs = (
                np.asarray(model.gap_history, dtype=float)
                * crit.fiscal.leak_response
                / claims
            )
            mid = float(xs[xs.size // 2]) if xs.size else 0.0
            end = float(xs[-1]) if xs.size else 0.0
            growth.append((end - mid) / mid if mid else float("inf"))
        solved = [r for r in rho_star if r is not None]
        median = float(np.median(solved)) if solved else float("nan")
        cells[f"lambda={absorption:g}"] = {
            "absorption": absorption,
            "rounds": rounds,
            "relaxation_times": rounds * absorption,
            "rho_grid": list(RHO_GRID),
            "rate_grid": list(rates),
            "rho_star_per_seed": rho_star,
            "rho_star_median": median,
            "unsolved_seeds": int(sum(r is None for r in rho_star)),
            "at_grid_bottom": bool(solved) and median <= RHO_GRID[0],
            "at_grid_top": bool(solved) and median >= RHO_GRID[-1],
            # Section 19.4, reported and not judged.
            "levy_over_lambda": levy_over_lambda,
            "x_growth_second_half": growth,
            "x_settled": bool(growth) and all(g <= X_SETTLED for g in growth),
        }
        if progress:
            c = cells[f"lambda={absorption:g}"]
            print(f"      lambda={absorption:<8g} {rounds:>6d} rounds  "
                  f"rho* {c['rho_star_per_seed']} median {median:g}  "
                  f"unsolved {c['unsolved_seeds']}  "
                  f"{time.time() - started:6.1f}s", flush=True)

    medians = [
        c["rho_star_median"] for c in cells.values()
        if not math.isnan(c["rho_star_median"])
    ]
    expected = len(lambdas)
    steps = [
        abs(RHO_GRID.index(_nearest_rho(a)) - RHO_GRID.index(_nearest_rho(b)))
        for a, b in itertools.combinations(medians, 2)
    ]
    return {
        "lambdas": list(lambdas),
        "smoke": bool(smoke),
        "cells": cells,
        "worst_step_apart": max(steps) if steps else None,
        "at_a_grid_end": any(
            c["at_grid_bottom"] or c["at_grid_top"] for c in cells.values()
        ),
        "unsolved_total": sum(c["unsolved_seeds"] for c in cells.values()),
        "passed": (
            len(medians) == expected
            and bool(steps)
            and max(steps) <= 1
            and not any(c["at_grid_bottom"] or c["at_grid_top"]
                        for c in cells.values())
            and not any(c["unsolved_seeds"] for c in cells.values())
        ),
    }


def _band_text(rebase: dict, label: str) -> str:
    """One column's band as a phrase, for the digest and the detail string."""
    b = rebase["columns"][label]["band"]
    if not b["non_empty"]:
        return "empty"
    hole = "" if b["contiguous"] else " with a hole"
    return f"{b['low']:g} to {b['high']:g}{hole}"


def _band(cells: dict, grid: tuple[float, ...], key_of) -> dict:
    """The open block of ``λ``, its two ends, and whether it has a hole.

    Lifted out of ``lambda_curve`` unchanged in meaning so that section 20's
    columns are read the same way A6-9's curve is. A band with a hole in it is a
    different object from a band and both criteria are stated on the block.
    """
    good = [a for a in grid if cells[key_of(a)]["open_in_every_seed"]]
    inside = [
        cells[key_of(a)]["open_in_every_seed"]
        for a in grid
        if good and good[0] <= a <= good[-1]
    ]
    return {
        "low": (good[0] if good else None),
        "high": (good[-1] if good else None),
        "points": [float(a) for a in good],
        "contiguous": bool(all(inside)),
        "non_empty": bool(good),
        # Section 20.3's interior test, stated against the scanned set rather
        # than against the whole real line: a band touching either end of what
        # was scanned is a band whose edge was not observed.
        "interior": bool(good) and good[0] > grid[0] and good[-1] < grid[-1],
    }


def rebase_curve(seeds: range, progress: bool, smoke: bool = False) -> dict:
    """A6-22 and A6-23. Section 13.4's curve on the corrected instrument.

    Registered in section 20 before this function existed. Three columns, one
    change at a time, plus the ``clip`` control column A6-23 is stated on and
    the ``ρ = 1`` column section 20.4 reports without judging.

    **A6-9 and A6-15 are untouched.** They keep their bands on the layer base at
    two thousand rounds. This asks the same two questions of a different
    instrument and reports the answers under different names.
    """
    lambdas = (3e-3, 1e-2) if smoke else A6_22_LAMBDAS
    columns: dict[str, dict] = {}

    def walk(label: str, shape: str, levy: str, rebate: str, scaled: bool):
        cells: dict[str, dict] = {}
        for absorption in lambdas:
            rounds = 300 if smoke else a6_21_rounds(absorption)
            # Section 20.4. `scaled` puts the policy at each lambda's own
            # critical strength, which section 19.5 measured at `R* = lambda`.
            rate = absorption if scaled else A6_9_RATE
            started = time.time()
            cells[f"lambda={absorption:g}"] = lambda_cell(
                seeds, absorption, shape, rounds, rate,
                levy=LevySpec(base=levy), rebate=RebateSpec(base=rebate),
            )
            if progress:
                c = cells[f"lambda={absorption:g}"]
                mark = "open" if c["open_in_every_seed"] else "closed"
                print(f"      {label:22s} lambda={absorption:<7g} "
                      f"{rounds:>6d} rounds  R={rate:<8g} {mark:6s} "
                      f"end/start {min(c['end_over_start']):.2f}"
                      f"-{max(c['end_over_start']):.2f}  "
                      f"{time.time() - started:5.1f}s", flush=True)
        band = _band(cells, lambdas, lambda a: f"lambda={a:g}")
        columns[label] = {
            "shape": shape,
            "levy_base": levy,
            "rebate_base": rebate,
            "rate": "lambda" if scaled else A6_9_RATE,
            "cells": cells,
            "band": band,
        }

    for label, levy, rebate in REBASE_COLUMNS:
        walk(f"{label} exp {levy[:4]}/{rebate[:4]}", SHAPE_DEFAULT,
             levy, rebate, False)
    walk("C clip thre/thre", SHAPE_CONTROL, "threshold", "threshold", False)
    walk("C exp rho=1", SHAPE_DEFAULT, "threshold", "threshold", True)

    judged = columns[
        f"C exp {REBASE_COLUMNS[2][1][:4]}/{REBASE_COLUMNS[2][2][:4]}"
    ]
    control = columns["C clip thre/thre"]
    return {
        "lambdas": list(lambdas),
        "rate": A6_9_RATE,
        "floor": A6_9_FLOOR,
        "smoke": bool(smoke),
        "columns": columns,
        "A6-22": bool(judged["band"]["non_empty"]),
        "A6-23": bool(control["band"]["interior"]),
    }


def _nearest_rho(value: float) -> float:
    """The ratio-grid point nearest ``value``.

    A median over an even count can land between two grid points, and "one step
    apart" is a statement about grid indices. Snapping is the only way to say
    it, and it is done here rather than by rounding the median itself so that
    the median printed is the median measured.
    """
    return min(RHO_GRID, key=lambda r: abs(r - value))


#: A6-20's cells. The corrected rebate is only reachable under the threshold
#: levy: under the layer levy the payers are the financial layer and the
#: recipients the production layer, which are already disjoint, so there is
#: nothing for the correction to remove and the cell would pass by not asking.
#: Both levy bases are run anyway, precisely so that the layer row shows the
#: overlap at zero for a reason that has nothing to do with the fix.
A6_20_CELLS: tuple[tuple[str, str], ...] = (
    ("layer", "layer"),
    ("layer", "threshold"),
    ("threshold", "layer"),
    ("threshold", "threshold"),
)
#: A6-20 runs at this horizon. Long enough for the threshold levy to have
#: drained the financial layer and moved downstream, which is the regime where
#: the two sides of the instrument disagree; short enough to sit inside the
#: default run rather than behind ``--slow``.
A6_20_ROUNDS = 20000


def rebate_sides(seeds: range, rounds: int, rate: float) -> dict:
    """A6-20. Both sides of one instrument keyed on the same kind of thing.

    **Structural, not a threshold.** Every quantity here is determined by
    construction rather than chosen, so there is nothing to tune and nothing
    that could have been set after seeing a number. The criterion is two-sided
    and both directions can fail:

    * **Matched pairs put nobody on both sides.** ``layer/layer`` because the
      financial and production layers are disjoint by construction;
      ``threshold/threshold`` because above ``θ`` pays and below ``θ`` receives
      and both are read off one measurement. Either being non-zero means the
      within-round ordering is wrong.
    * **Mismatched pairs put somebody on both sides.** ``threshold/layer`` is
      the defect section 18 records: the payers move with the distribution and
      the recipients do not, so a production-layer node above ``θ`` pays and
      receives. ``layer/threshold`` is the same error mirrored: a
      financial-layer node below ``θ`` receives and is levied anyway because
      the layer levy never looks at ``θ``. **Both are required to be non-zero.**
      A zero there would not be a success, it would mean the distribution never
      put anyone in the overlapping region and the comparison had nothing in it.
    * **Claims are conserved and the empty-recipient fallback did not fire
      silently.** Both checked in every cell.

    **The first draft of this criterion quantified over all four cells and
    demanded zero everywhere.** It failed on the two mismatched cells, which is
    what it should do: those cells are supposed to overlap and the criterion had
    the wrong scope. Recorded here rather than silently corrected because the
    scope changed after a run, and it is only legitimate because **nothing had
    been registered yet**: A6-20 reaches ``docs/a6_siphon_cost.md`` §18 in the
    corrected form, and the first form never left this file. A criterion already
    on the page would have been left failing, as A6-1 is.

    The comparison of *outcomes* between the two rebates is deliberately not
    judged here. No threshold for it is registered, it belongs with the
    re-measurement of A6-9 and A6-15 on the corrected instrument, and inventing
    a bound for it now would be choosing one after seeing the run.
    """
    rows: dict[str, dict] = {}
    for levy_base, rebate_base in A6_20_CELLS:
        key = f"levy={levy_base}/rebate={rebate_base}"
        overlap, drift, fallbacks, payees = [], [], [], []
        for seed in seeds:
            cfg = config_for(
                seed,
                rounds,
                True,
                False,
                "infrastructure",
                rate,
                ratchet=RatchetSpec(absorption=1e-3, shape=SHAPE_DEFAULT),
                levy=LevySpec(base=levy_base),
                rebate=RebateSpec(base=rebate_base),
            )
            model, _ = _quiet(run_a6, cfg, model_cls=A6RatchetModel)
            both = np.asarray(model.both_sides_history)
            pc = np.asarray(model.payee_count_history)
            overlap.append(int(both.max()) if both.size else 0)
            drift.append(
                abs(float(model.holdings.sum()) - model._opening_claims)
            )
            fallbacks.append(int(np.asarray(model.rebate_fallback_history).sum()))
            payees.append((int(pc.min()), int(pc.max())) if pc.size else (0, 0))
        rows[key] = {
            "levy_base": levy_base,
            "rebate_base": rebate_base,
            "worst_both_sides": max(overlap),
            "worst_claim_drift": max(drift),
            "fallback_rounds": max(fallbacks),
            "payee_range": [min(p[0] for p in payees), max(p[1] for p in payees)],
        }
    matched = [
        r for r in rows.values() if r["levy_base"] == r["rebate_base"]
    ]
    mismatched = [
        r for r in rows.values() if r["levy_base"] != r["rebate_base"]
    ]
    return {
        "rounds": rounds,
        "rate": rate,
        "cells": rows,
        "worst_claim_drift": max(r["worst_claim_drift"] for r in rows.values()),
        "worst_fallback_rounds": max(
            r["fallback_rounds"] for r in rows.values()
        ),
        "matched_clean": all(r["worst_both_sides"] == 0 for r in matched),
        "mismatched_overlap": all(
            r["worst_both_sides"] > 0 for r in mismatched
        ),
        "passed": (
            all(r["worst_both_sides"] == 0 for r in matched)
            and all(r["worst_both_sides"] > 0 for r in mismatched)
            and all(r["worst_claim_drift"] < A6_20_DRIFT for r in rows.values())
            and all(r["fallback_rounds"] == 0 for r in rows.values())
        ),
    }


def long_horizon(
    seeds: range, rounds: int, rate: float, progress: bool
) -> dict:
    """A6-16, A6-17, A6-18 and A6-19, from one pass over six cells.

    A6-16 and A6-19 are the same question asked of the two levy bases, each
    with its own control, each three-valued. A6-18 reads the levy actually
    collected. A6-17 is the trajectory of ``x``, reported and not judged.
    """
    cells: dict[str, dict] = {}
    for shape, absorption, levy_base, role, multiple in HORIZON_CELLS:
        key = f"{levy_base}/{shape}/lambda={absorption:g}"
        started = time.time()
        cells[key] = horizon_cell(
            seeds, shape, absorption, levy_base, rounds * multiple, rate, role
        )
        if progress:
            c = cells[key]
            print(f"      {key:30s} {role:13s} "
                  f"{c['rounds']:>7d}r "
                  f"{'open' if c['open_in_every_seed'] else 'closed':6s} "
                  f"x {min(c['final_x']):.2f}-{max(c['final_x']):.2f} "
                  f"{'settled' if c['x_settled'] else 'CLIMBING'} "
                  f"(+{max(c['x_growth_second_half']):.2%}) "
                  f"levy {min(c['levy_final_round']):.2e} "
                  f"{time.time() - started:5.1f}s", flush=True)

    layer = three_valued(cells, "judged", "control", "layer")
    threshold = three_valued(
        cells, "levy-judged", "levy-control", "threshold"
    )
    levy_cells = [
        c for c in cells.values() if c["role"].startswith("levy")
    ]
    return {
        # The base horizon. Cells carry their own ``rounds``, which is this
        # times the per-cell multiple registered in ``HORIZON_CELLS``.
        "rounds": rounds,
        "cell_multiples": {
            f"{base}/{shape}/lambda={a:g}": m
            for shape, a, base, _role, m in HORIZON_CELLS
        },
        "rate": rate,
        "floor": A6_9_FLOOR,
        "x_settled_threshold": X_SETTLED,
        "levy_floor": A6_18_FLOOR,
        "cells": cells,
        # A6-16, on the layer base. Where it has always been judged.
        "control_open": layer["control_open"],
        "passed": layer["passed"],
        "reason": layer["reason"],
        # A6-19, the same question on the threshold base, with its own control.
        "A6-19": threshold["passed"],
        "A6-19 reason": threshold["reason"],
        "A6-19 control_open": threshold["control_open"],
        "marginal_cells": [
            k for k, c in cells.items() if c["settling_call_is_marginal"]
        ],
        # A6-18. Does a base recomputed each round from a measured stock keep
        # collecting, where a fixed set of payers is drained and then collects
        # nothing forever?
        "A6-18": (
            bool(levy_cells) and all(c["levy_alive"] for c in levy_cells)
        ),
        "levy_comparison": {
            k: {
                "levy_base": c["levy_base"],
                "first_round": c["levy_first_round"],
                "final_round": c["levy_final_round"],
                "final_payer_count": c["final_payer_count"],
                "final_l2_levy_share": c["final_l2_levy_share"],
                "alive": c["levy_alive"],
            }
            for k, c in cells.items()
        },
    }


def control_column(curve: dict, grid: tuple[float, ...]) -> dict:
    """A6-14 and A6-15. The wall swept across the same ``λ`` grid.

    A6-14 is a gate on comparability. Section 14.2 reads the smooth column
    against section 9.2's recorded numbers, and that comparison is only worth
    anything if this script reproduces those numbers when it runs the wall.

    A6-15 is the prediction that separates what ``λ`` does from what ``g``
    does. Under the wall the effect saturates completely once ``x >= 1``, and
    ``x`` settles at ``ι·R·s/λ``, so small ``λ`` should seal the leak and close
    the economy, the middle should stay open, and the top should close again
    because the arm buys too little. Section 14.7.
    """
    cells = curve["cells"]

    def is_open(absorption: float) -> bool | None:
        key = f"{SHAPE_CONTROL}/lambda={absorption:g}"
        cell = cells.get(key)
        return None if cell is None else bool(cell["open_in_every_seed"])

    zero = cells.get(f"{SHAPE_CONTROL}/lambda={0.0:g}")
    reproduction: dict | None = None
    if zero is not None and len(zero["end_over_start"]) == len(A6_5_RECORDED):
        measured = [float(x) for x in zero["end_over_start"]]
        deltas = [
            abs(a - b)
            for a, b in zip(measured, A6_5_RECORDED, strict=True)
        ]
        reproduction = {
            "recorded": list(A6_5_RECORDED),
            "measured": measured,
            "abs_deltas": [float(d) for d in deltas],
            "tolerance": A6_14_TOL,
            "passed": all(d <= A6_14_TOL for d in deltas),
        }

    pins = {
        f"{a:g}": is_open(a)
        for a in (*A6_15_CLOSED, *A6_15_OPEN)
    }
    band = curve["bands"].get(SHAPE_CONTROL)
    interior: bool | None = None
    if all(v is not None for v in pins.values()) and band is not None:
        interior = bool(
            all(is_open(a) is False for a in A6_15_CLOSED)
            and all(is_open(a) is True for a in A6_15_OPEN)
            and band["non_empty"]
            and band["contiguous"]
        )
    crossover = None if band is None else band["low"]
    return {
        "A6-14": reproduction,
        "A6-15": {
            "pinned": pins,
            "band": band,
            "crossover": crossover,
            "crossover_window": list(A6_15_CROSSOVER_WINDOW),
            # Reported. The window is where the pins already imply it must sit,
            # so this adds nothing to the verdict and is printed because the
            # location itself is the deliverable.
            "crossover_in_window": (
                None if crossover is None
                else any(
                    abs(crossover - w) < 1e-12
                    for w in A6_15_CROSSOVER_WINDOW
                )
            ),
            "passed": interior,
        },
    }


def shape_agreement(curve: dict, scan: dict | None,
                    lambdas: tuple[float, ...]) -> dict:
    """A6-13. The two shapes must point the same way.

    Section 13.3 says in advance which way each is expected to bend, so this is
    a check and not a tie-breaker. If they disagree the headline is withdrawn
    and what gets reported is the shape dependence.
    """
    band_agrees = (
        curve["bands"][SHAPE_DEFAULT]["non_empty"]
        == curve["bands"][SHAPE_AXIS]["non_empty"]
    )
    scan_agrees = None
    if scan is not None:
        def verdict(shape: str) -> list[bool]:
            return [
                (
                    scan["infrastructure"][f"{shape}/lambda={a:g}"][
                        "registered"]["unsolved_seeds"] == 0
                    and not scan["infrastructure"][
                        f"{shape}/lambda={a:g}"]["registered"]["at_grid_floor"]
                )
                for a in lambdas
            ]
        scan_agrees = verdict(SHAPE_DEFAULT) == verdict(SHAPE_AXIS)
    return {
        "band_non_empty_agrees": bool(band_agrees),
        "scan_verdict_agrees": scan_agrees,
        "passed": bool(band_agrees and (scan_agrees is not False)),
    }


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def _fmt(x: float | None) -> str:
    return "none" if x is None else f"{x:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    ap.add_argument("--long", type=int, default=REGISTERED_LONG)
    ap.add_argument("--horizon", type=int, default=HORIZON_ROUNDS,
                    help="rounds for A6-16's long-horizon test")
    ap.add_argument("--skip-horizon", action="store_true",
                    help="omit A6-16 and A6-17, the slowest block")
    ap.add_argument("--guard-only", action="store_true",
                    help="run A6-7 and A6-8 and stop")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny off-parameter shakeout; establishes nothing")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress per-cell progress lines")
    args = ap.parse_args()

    lambdas, shapes = LAMBDA_GRID, SHAPES_RUN
    curve_shapes = CURVE_SHAPES
    rescan_lambdas = RESCAN_LAMBDAS
    guard_rates = GUARD_RATES
    if args.smoke:
        args.seeds, args.rounds, args.long = 2, 80, 200
        args.horizon = 300
        lambdas = (0.0, 1e-3, 1e-2)
        rescan_lambdas = (1e-3,)
        guard_rates = (0.0, 0.06)
        print("  SMOKE RUN. Off every registered parameter. It shows that the "
              "code runs and it establishes nothing about A6.\n")

    seeds = range(args.seeds)
    progress = not args.quiet
    registered = (
        not args.smoke
        and args.seeds == REGISTERED_SEEDS
        and args.rounds == REGISTERED_ROUNDS
        and args.long == REGISTERED_LONG
        and args.horizon == HORIZON_ROUNDS
        and not args.skip_horizon
    )

    print("A6-7 to A6-19: the frontier ratchet and the levy base\n")
    print(f"  {args.seeds} seeds, {args.rounds} rounds for the guard, "
          f"{args.long} for the long runs, issuance off in every cell")

    print("\n  A6-7  the reduction guard (gate)")
    guard = reduction_guard(seeds, args.rounds, guard_rates)
    print(f"        {'pass' if guard['passed'] else 'FAIL'} -- "
          f"{guard['pairs']} model pairs compared bit for bit, "
          f"{guard['mismatch_count']} mismatches")
    if not guard["passed"]:
        for bad in guard["mismatches"]:
            print(f"        MISMATCH {bad}")
        print("\n  The generalisation does not reproduce its special case, so "
              "the three new parameters do not enter and nothing below this "
              "line was run. Section 12.6.")
        return 1

    print("\n  A6-8  the fixed point")
    bench = fixed_point_bench()
    worst = max(r["relative_error"] for r in bench["rows"])
    print(f"        {'pass' if bench['passed'] else 'FAIL'} -- K-B settles on "
          f"I/lambda, worst relative error {worst:.2e} against {A6_8_TOL:g}")

    if args.guard_only:
        print("\n  --guard-only: stopping before the long runs")
        return 0 if bench["passed"] else 1

    print(f"\n  A6-9  the lambda curve at R = {A6_9_RATE}, "
          f"{args.long} rounds, floor {A6_9_FLOOR}")
    curve = lambda_curve(
        seeds, args.long, A6_9_RATE, lambdas, curve_shapes, progress
    )
    for shape in curve_shapes:
        band = curve["bands"][shape]
        tag = f"{shape} (control)" if shape == SHAPE_CONTROL else shape
        if band["non_empty"]:
            note = "" if band["contiguous"] else "  ** not contiguous"
            print(f"        {tag:15s} band lambda in "
                  f"[{band['low']:g}, {band['high']:g}], "
                  f"{len(band['points'])} of {len(lambdas)} points{note}")
        else:
            print(f"        {tag:15s} no lambda on the grid holds all seeds "
                  f"open")
    print(f"        {'pass' if curve['passed'] else 'FAIL'} -- judged on "
          f"{SHAPE_DEFAULT}. Both endpoints are reported and no lambda is "
          f"nominated, which is section 13.6")

    control = control_column(curve, lambdas)
    rep, interior = control["A6-14"], control["A6-15"]
    if rep is None:
        print("\n  A6-14 skipped: the control column at lambda = 0 is not "
              "comparable to section 9.2 off the registered parameters")
    else:
        print(f"\n  A6-14 {'pass' if rep['passed'] else 'FAIL'} -- the wall at "
              f"lambda = 0 reproduces section 9.2. recorded "
              f"{[f'{x:.2f}' for x in rep['recorded']]}, measured "
              f"{[f'{x:.2f}' for x in rep['measured']]}, worst delta "
              f"{max(rep['abs_deltas']):.4f} against {A6_14_TOL}")
        if not rep["passed"]:
            print("        The two scripts are not measuring the same thing, "
                  "so section 14.2's comparison is void along with everything "
                  "built on it.")
    if interior["passed"] is None:
        print("  A6-15 skipped: the pinned lambda are not all on this grid")
    else:
        print(f"  A6-15 {'pass' if interior['passed'] else 'FAIL'} -- under "
              f"the wall the band is interior. pinned "
              f"{interior['pinned']}, crossover at {interior['crossover']}, "
              f"in the registered window "
              f"{interior['crossover_in_window']}")

    print(f"\n  A6-10 / A6-11 / A6-12  the rescan at {args.long} rounds, "
          f"access/fair, lambda in {[f'{a:g}' for a in rescan_lambdas]}")
    scan = rescan(seeds, args.long, rescan_lambdas, shapes, progress)
    print(f"        A6-10 {'pass' if scan['A6-10'] else 'FAIL'} -- R* has a "
          f"solution in every seed and is off the grid floor, at both judged "
          f"lambda under {SHAPE_DEFAULT}, on the registered grid")
    print(f"        A6-11 {'pass' if scan['A6-11'] else 'FAIL'} -- "
          f"R*(I)/R*(T) against {A6_11_RATIO}, as a value not a bound")
    for readout, floor, key10, key11 in (
        ("registered", FIRST_NONZERO, "A6-10", "A6-11"),
        ("refined", FIRST_NONZERO_FINE, "refined_A6-10", "refined_A6-11"),
    ):
        print(f"          on the {readout} grid (first non-zero {floor:g}): "
              f"A6-10 {scan[key10]}, A6-11 {scan[key11]}")
        for key in scan["judged_cells"]:
            v = scan["ratios"][readout][key]
            flag = "  ** upper bound only" if v["is_upper_bound"] else ""
            stars = [
                _fmt(r)
                for r in scan["infrastructure"][key][readout]["rates"]
            ]
            print(f"            {key:22s} R* {stars}  "
                  f"ratio {_fmt(v['median'])}{flag}")
    print("        the refined reading is a re-measurement at higher "
          "resolution. It does not replace the registered verdict, which is "
          "what reaches RESULTS.md. Section 14.7")
    print("        A6-12 reported, not judged: the top of the working band, "
          "which section 9.1 left unlocated")
    for key, cell in scan["infrastructure"].items():
        fine = cell["refined"]
        print(f"          {key:22s} low {[_fmt(r) for r in fine['rates']]}  "
              f"high {[_fmt(h) for h in fine['band_high']]}  "
              f"contiguous {fine['band_contiguous']}")

    horizon: dict | None = None
    if not args.skip_horizon:
        print(f"\n  A6-16 / A6-17 / A6-19  the long horizon: {args.horizon} "
              f"rounds at R = {A6_9_RATE}, two judged cells and one "
              f"control on each levy base. Cells carrying a registered "
              f"multiple run longer and print their own length")
        horizon = long_horizon(seeds, args.horizon, A6_9_RATE, progress)
        mark = {True: "pass", False: "FAIL", None: "no verdict"}[
            horizon["passed"]
        ]
        print(f"        A6-16 {mark} (layer base) -- {horizon['reason']}")
        shown = {True: "pass", False: "FAIL", None: "no verdict"}[
            horizon["A6-19"]
        ]
        print(f"        A6-19 {shown} (threshold base) -- "
              f"{horizon['A6-19 reason']}")
        for key, cell in horizon["cells"].items():
            shut = [
                "-" if r is None else str(r) for r in cell["closed_at_round"]
            ]
            print(f"          {key:30s} end/start "
                  f"{[f'{r:.2f}' for r in cell['end_over_start']]}")
            print(f"          {'':30s} leak "
                  f"{min(cell['final_leak_factor']):.4f}-"
                  f"{max(cell['final_leak_factor']):.4f}, closed at round "
                  f"{shut}")
            print(f"          {'':30s} x at "
                  f"{[f'{f:.0%}' for f in cell['checkpoint_fractions']]} "
                  f"= {[f'{v:.2f}' for v in cell['x_checkpoints'][0]]} "
                  f"(seed 0)")
            print(f"          {'':30s} levy round 1 "
                  f"{min(cell['levy_first_round']):.3e} -> final "
                  f"{min(cell['levy_final_round']):.3e}, payers "
                  f"{cell['final_payer_count']}, from L2 "
                  f"{[f'{s:.0%}' for s in cell['final_l2_levy_share']]}")
        print(f"        A6-18 {'pass' if horizon['A6-18'] else 'FAIL'} -- the "
              f"threshold base is still collecting at the end of the run, "
              f"every seed, against a floor of {A6_18_FLOOR:g} of the opening "
              f"claim stock. The layer rows are printed beside it as the "
              f"comparison and are not judged by this criterion")
        if horizon["marginal_cells"]:
            print(f"        ** the settled/climbing call rests on the "
                  f"{X_SETTLED:.0%} threshold rather than on the data in "
                  f"{horizon['marginal_cells']}. Those cells carry nothing")
        print("        A6-17 reported, not judged: where x settles and what "
              "leak that leaves, above in the same lines")
    else:
        print("\n  A6-16 / A6-17 / A6-19 skipped")

    sides_rounds = 300 if args.smoke else A6_20_ROUNDS
    print(f"\n  A6-20  the two sides of the instrument, {sides_rounds} rounds "
          f"at R = {A6_9_RATE}, four cells")
    sides = rebate_sides(seeds, sides_rounds, A6_9_RATE)
    for key, row in sides["cells"].items():
        print(f"        {key:38s} both sides {row['worst_both_sides']:>4d}   "
              f"payees {row['payee_range'][0]}-{row['payee_range'][1]}   "
              f"claim drift {row['worst_claim_drift']:.2e}   "
              f"fallbacks {row['fallback_rounds']}")
    print(f"        A6-20 {'pass' if sides['passed'] else 'FAIL'} -- matched "
          f"pairs put nobody on both sides ({sides['matched_clean']}), "
          f"mismatched pairs do ({sides['mismatched_overlap']}), claims are "
          f"conserved and the empty-recipient fallback never fired. "
          f"`levy=threshold/rebate=layer` is the defect section 18 records and "
          f"its count is what the correction removes")

    print(f"\n  A6-21  R* as a slope in lambda: {len(RHO_GRID)} ratios at "
          f"{len(A6_21_LAMBDAS)} values of lambda, each for "
          f"max(2000, {A6_21_RELAXATIONS}/lambda) rounds")
    slope = rho_scaling(seeds, progress, smoke=args.smoke)
    reading = (
        "the same grid point or one step apart"
        if slope["passed"]
        else "NOT stable"
    )
    print(f"        A6-21 {'pass' if slope['passed'] else 'FAIL'} -- rho* is "
          f"{reading} across lambda, worst separation "
          f"{slope['worst_step_apart']} steps. A6-10 and A6-11 keep their "
          f"failures; this asks a different question")
    for key, c in slope["cells"].items():
        iol = c["levy_over_lambda"]
        print(f"          {key:16s} reported, not judged: I(R*)/lambda "
              f"{'-' if not iol else f'{min(iol):.3g} to {max(iol):.3g}'}, "
              f"x {'settled' if c['x_settled'] else 'CLIMBING'}")

    print(f"\n  A6-22 / A6-23  the curve on the corrected instrument: "
          f"{len(REBASE_COLUMNS)} columns plus a control and a scaled column, "
          f"one change at a time")
    rebase = rebase_curve(seeds, progress, smoke=args.smoke)
    for label, col in rebase["columns"].items():
        b = col["band"]
        print(f"        {label:22s} band {_band_text(rebase, label):18s} "
              f"contiguous {str(b['contiguous']):5s} interior "
              f"{str(b['interior']):5s}")
    a22 = (
        "non-empty"
        if rebase["A6-22"]
        else "EMPTY: no absorption rate in the scanned set keeps this economy "
             "open at the registered levy"
    )
    print(f"        A6-22 {'pass' if rebase['A6-22'] else 'FAIL'} -- the exp "
          f"band on the corrected instrument is {a22}")
    a23 = (
        "interior to the scanned set"
        if rebase["A6-23"]
        else "NOT interior: it runs to an end of what was scanned"
    )
    print(f"        A6-23 {'pass' if rebase['A6-23'] else 'FAIL'} -- the clip "
          f"band is {a23}")

    agreement = shape_agreement(curve, scan, rescan_lambdas)
    print(f"\n  A6-13 {'pass' if agreement['passed'] else 'FAIL'} -- "
          f"{SHAPE_DEFAULT} and {SHAPE_AXIS} point the same way "
          f"(band {agreement['band_non_empty_agrees']}, "
          f"scan {agreement['scan_verdict_agrees']}). If they did not, the "
          f"headline would rest on the tail of g rather than on lambda")

    # Every number in a detail string goes through an explicit format spec.
    # RESULTS.md is rendered from this file and diffed byte for byte in CI, so
    # a value printed through ``repr`` would turn that check red on a
    # last-digit difference between two BLAS builds rather than on a change to
    # the model.
    band = curve["bands"][SHAPE_DEFAULT]
    judged = scan["judged_cells"]
    details = {
        "A6-7": (
            f"{guard['pairs']} model pairs compared against A6Model bit for "
            f"bit, over {len(guard['rates'])} rates and {guard['rounds']} "
            f"rounds in each of eight cells; {guard['mismatch_count']} "
            f"mismatches. A gate: nothing below it runs if it fails"
        ),
        "A6-8": (
            f"K-B settles on I/lambda on a bench with no economy in it; "
            f"worst relative error "
            f"{max(r['relative_error'] for r in bench['rows']):.1e} against "
            f"{A6_8_TOL:g}"
        ),
        "A6-9": (
            (
                f"band of lambda holding all five seeds open at R = "
                f"{A6_9_RATE:g} over {args.long} rounds: "
                f"[{band['low']:g}, {band['high']:g}], "
                f"{len(band['points'])} of {len(lambdas)} grid points, "
                f"judged on {SHAPE_DEFAULT}. No lambda is nominated, and the "
                f"low end is an artefact of this horizon"
            )
            if band["non_empty"]
            else "no lambda on the grid holds all seeds open"
        ),
        "A6-10": (
            "on the registered grid at "
            f"{args.long} rounds, R*(I) per judged cell: "
            + "; ".join(
                f"{k} median {_fmt(scan['infrastructure'][k]['registered']['median'])}"
                + (" on the grid floor"
                   if scan["infrastructure"][k]["registered"]["at_grid_floor"]
                   else " off the floor")
                for k in judged
            )
        ),
        "A6-11": (
            f"R*(I)/R*(T) against {A6_11_RATIO:g}, as a value not a bound: "
            + "; ".join(
                f"{k} {_fmt(scan['ratios']['registered'][k]['median'])}"
                + (" (bound only)"
                   if scan["ratios"]["registered"][k]["is_upper_bound"] else "")
                for k in judged
            )
        ),
        "A6-13": (
            f"{SHAPE_DEFAULT} and {SHAPE_AXIS} point the same way: band "
            f"agreement {agreement['band_non_empty_agrees']}, scan verdict "
            f"agreement {agreement['scan_verdict_agrees']}"
        ),
        "A6-14": (
            "not comparable off the registered parameters"
            if rep is None
            else (
                "the wall at lambda = 0 reproduces section 9.2's end over "
                "start: recorded "
                + ", ".join(f"{x:.2f}" for x in rep["recorded"])
                + "; measured "
                + ", ".join(f"{x:.2f}" for x in rep["measured"])
                + f"; worst absolute difference {max(rep['abs_deltas']):.4f} "
                f"against {A6_14_TOL:g}"
            )
        ),
        "A6-15": (
            "the pinned lambda are not all on this grid"
            if interior["passed"] is None
            else (
                "under the wall the band is interior: open at "
                f"{[k for k, v in interior['pinned'].items() if v]}, closed at "
                f"{[k for k, v in interior['pinned'].items() if not v]}, "
                f"crossover at {interior['crossover']}, inside the registered "
                f"window {interior['crossover_in_window']}"
            )
        ),
        "A6-16": "not run" if horizon is None else horizon["reason"],
        "A6-18": (
            "not run"
            if horizon is None
            else (
                "levy collected in the final round, in units of the opening "
                "claim stock: "
                + "; ".join(
                    f"{k} {min(c['levy_final_round']):.2e} from "
                    f"{min(c['levy_first_round']):.2e}"
                    for k, c in horizon["cells"].items()
                )
            )
        ),
        "A6-19": "not run" if horizon is None else horizon["A6-19 reason"],
        "A6-20": (
            "nodes on both sides of the transfer in one round, worst over "
            "seeds: "
            + "; ".join(
                f"{k} {c['worst_both_sides']}" for k, c in sides["cells"].items()
            )
            + f". Worst claim drift {sides['worst_claim_drift']:.2e} against "
            + f"{A6_20_DRIFT:g}; fallback rounds "
            + f"{sides['worst_fallback_rounds']}"
        ),
        "A6-21": (
            "rho* per lambda, median over seeds: "
            + "; ".join(
                f"{k} {c['rho_star_median']:g}" for k, c in slope["cells"].items()
            )
            + f". Worst separation {slope['worst_step_apart']} grid steps "
            + f"against 1; at a grid end {slope['at_a_grid_end']}; "
            + f"unsolved seeds {slope['unsolved_total']}"
        ),
        "A6-22": (
            "band of lambda keeping every seed open, exp, on the corrected "
            "instrument: "
            + _band_text(rebase, "C exp thre/thre")
            + ". The other columns, one change at a time: "
            + "; ".join(
                f"{k} {_band_text(rebase, k)}"
                for k in rebase["columns"]
                if k != "C exp thre/thre"
            )
        ),
        "A6-23": (
            "clip control band on the corrected instrument: "
            + _band_text(rebase, "C clip thre/thre")
            + f", scanned over {rebase['lambdas']}"
        ),
    }
    verdicts = [
        ("A6-7", guard["passed"]),
        ("A6-8", bench["passed"]),
        ("A6-9", curve["passed"]),
        ("A6-10", scan["A6-10"]),
        ("A6-11", scan["A6-11"]),
        ("A6-13", agreement["passed"]),
        ("A6-14", None if rep is None else rep["passed"]),
        ("A6-15", interior["passed"]),
        ("A6-16", None if horizon is None else horizon["passed"]),
        ("A6-18", None if horizon is None else horizon["A6-18"]),
        ("A6-19", None if horizon is None else horizon["A6-19"]),
        ("A6-20", sides["passed"]),
        ("A6-21", slope["passed"]),
        ("A6-22", rebase["A6-22"]),
        ("A6-23", rebase["A6-23"]),
    ]
    skipped = [name for name, v in verdicts if v is None]
    criteria = [
        {"name": name, "passed": bool(v), "detail": details[name]}
        for name, v in verdicts
        if v is not None
    ]
    passed = sum(c["passed"] for c in criteria)
    note = f", {len(skipped)} skipped ({', '.join(skipped)})" if skipped else ""
    print(f"\n  {passed}/{len(criteria)} criteria passed{note}; A6-12 is "
          f"reported and not judged")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / (
        "a6_ratchet.json"
        if registered
        else (
            f"a6_ratchet.offparam_{args.seeds}x{args.rounds}"
            f"x{args.long}x{args.horizon if not args.skip_horizon else 0}.json"
        )
    )
    if not registered:
        print(f"\n  off-parameter run against the registered "
              f"{REGISTERED_SEEDS}x{REGISTERED_ROUNDS}x{REGISTERED_LONG}: "
              f"writing beside the registered result, not over it")
    out.write_text(
        json.dumps(
            {
                "stage": "A6-ratchet",
                "seeds": args.seeds,
                "rounds": args.rounds,
                "long_rounds": args.long,
                "lambda_grid": list(lambdas),
                "shapes": list(shapes),
                "curve_shapes": list(curve_shapes),
                "rescan_lambdas": list(rescan_lambdas),
                "rate_grid_registered": list(RATE_GRID),
                "rate_grid_refined": list(RATE_GRID_FINE),
                "thresholds": {
                    "A6-8 relative": A6_8_TOL,
                    "A6-9 floor": A6_9_FLOOR,
                    "A6-9 rate": A6_9_RATE,
                    "A6-11 ratio": A6_11_RATIO,
                    "A6-14 absolute": A6_14_TOL,
                    "A6-16 x settled": X_SETTLED,
                    "A6-16 rounds": args.horizon,
                    "A6-18 levy floor": A6_18_FLOOR,
                },
                "levy_threshold_multiple": LevySpec().threshold_multiple,
                "reduction_guard": guard,
                "fixed_point": bench,
                "lambda_curve": curve,
                "control_column": control,
                "long_horizon": horizon,
                "rescan": scan,
                "shape_agreement": agreement,
                "criteria": criteria,
                "skipped": skipped,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if passed == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
