"""A6-7 to A6-13: the frontier ratchet. Registered in ``docs/a6_siphon_cost.md``.

This file evaluates and does not design. Every threshold, grid and scope
decision it compares against is written in section 13 of that document, before
any of this ran.

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
    RatchetSpec,
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

#: A6-16 and A6-17, the long-horizon test. A6-5's own warning applied to this
#: stage's conclusion: three hundred rounds was enough to find `R*` and not
#: enough to claim "forever", and two thousand rounds is not enough to claim
#: that a smooth `g` removes the collapse rather than postponing it.
HORIZON_ROUNDS = 12000

#: Two judged cells and one control. The control has a genuine fixed point in
#: `x` at about `0.87` and a surviving leak of `0.12`, well clear of the
#: boundary, so it should stay open at any horizon. **If the control closes
#: too, long horizons close everything and the two judged cells say nothing
#: about `g`**, so A6-16 returns no verdict rather than a wrong one.
HORIZON_CELLS: tuple[tuple[str, float, str], ...] = (
    ("exp", 0.0, "judged"),
    ("hill", 0.0, "judged"),
    ("clip", 1e-3, "control"),
)

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
    seeds: range, absorption: float, shape: str, rounds: int, rate: float
) -> dict:
    """One point of the curve: five long runs in ``access / fair / arm I``."""
    ratios, trends, gaps, xs, leaks = [], [], [], [], []
    for seed in seeds:
        cfg = config_for(
            seed, rounds, access=True, fair=True, channel="infrastructure",
            rate=rate,
            ratchet=RatchetSpec(absorption=absorption, shape=shape),
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
    for seed in seeds:
        cfg = config_for(
            seed, rounds, access=True, fair=True, channel="infrastructure",
            rate=rate,
            ratchet=RatchetSpec(absorption=absorption, shape=shape),
        )
        model, history = _quiet(run_a6, cfg, model_cls=A6RatchetModel)
        y = np.asarray(history.effective_support, dtype=float)
        xs = (
            np.asarray(model.gap_history, dtype=float)
            * cfg.fiscal.leak_response
            / model._opening_claims
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

    settled = all(g <= X_SETTLED for g in growth)
    worst = max(growth)
    return {
        "shape": shape,
        "absorption": absorption,
        "role": role,
        "rounds": rounds,
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


def long_horizon(
    seeds: range, rounds: int, rate: float, progress: bool
) -> dict:
    """A6-16 and A6-17. Three-valued on purpose.

    A6-5's failure was scored on a two-thousand-round run and section 5 of this
    document says in as many words that three hundred rounds is "not enough to
    claim forever". The same objection applies to section 14.2's reading, so
    this test refuses to return a verdict when the run cannot support one.

    - both judged cells closed: the registered prediction holds
    - a judged cell open with ``x`` settled: the prediction is wrong there
    - a judged cell open with ``x`` still climbing: **no verdict.** The horizon
      is too short and saying anything else would repeat A6-5's mistake
    - the control closed as well: **no verdict.** Long horizons close
      everything here and the judged cells are confounded
    """
    cells: dict[str, dict] = {}
    for shape, absorption, role in HORIZON_CELLS:
        key = f"{shape}/lambda={absorption:g}"
        started = time.time()
        cells[key] = horizon_cell(seeds, shape, absorption, rounds, rate, role)
        if progress:
            c = cells[key]
            print(f"      {key:22s} {role:7s} "
                  f"{'open' if c['open_in_every_seed'] else 'closed':6s} "
                  f"x {min(c['final_x']):.2f}-{max(c['final_x']):.2f} "
                  f"{'settled' if c['x_settled'] else 'CLIMBING'} "
                  f"(+{max(c['x_growth_second_half']):.2%}) "
                  f"{time.time() - started:5.1f}s", flush=True)

    judged = [c for c in cells.values() if c["role"] == "judged"]
    control = [c for c in cells.values() if c["role"] == "control"]
    control_open = all(c["open_in_every_seed"] for c in control)

    if not control_open:
        passed, reason = None, (
            "the control cell closed too, so the horizon closes everything "
            "here and the judged cells are confounded"
        )
    elif all(not c["open_in_every_seed"] for c in judged):
        passed, reason = True, (
            "both judged cells closed, which is what the surviving-leak "
            "reading predicts: a smooth g postpones the collapse rather than "
            "removing it"
        )
    elif any(
        c["open_in_every_seed"] and not c["x_settled"] for c in judged
    ):
        passed, reason = None, (
            "a judged cell is still open with x still climbing, so this "
            "horizon cannot decide it. Reported as no verdict rather than as "
            "a pass, which is A6-5's mistake"
        )
    else:
        passed, reason = False, (
            "a judged cell is open with x settled, so a smooth g removes the "
            "collapse on its own and section 14.2 stands as written"
        )
    return {
        "rounds": rounds,
        "rate": rate,
        "floor": A6_9_FLOOR,
        "x_settled_threshold": X_SETTLED,
        "cells": cells,
        "control_open": bool(control_open),
        "passed": passed,
        "reason": reason,
        "marginal_cells": [
            k for k, c in cells.items() if c["settling_call_is_marginal"]
        ],
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

    print("A6-7 to A6-13: the frontier ratchet\n")
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
        print(f"\n  A6-16 / A6-17  the long horizon: {args.horizon} rounds at "
              f"R = {A6_9_RATE}, two judged cells and one control")
        horizon = long_horizon(seeds, args.horizon, A6_9_RATE, progress)
        mark = {True: "pass", False: "FAIL", None: "no verdict"}[
            horizon["passed"]
        ]
        print(f"        A6-16 {mark} -- {horizon['reason']}")
        for key, cell in horizon["cells"].items():
            shut = [
                "-" if r is None else str(r) for r in cell["closed_at_round"]
            ]
            print(f"          {key:22s} end/start "
                  f"{[f'{r:.2f}' for r in cell['end_over_start']]}")
            print(f"          {'':22s} leak "
                  f"{min(cell['final_leak_factor']):.4f}-"
                  f"{max(cell['final_leak_factor']):.4f}, closed at round "
                  f"{shut}")
            print(f"          {'':22s} x at "
                  f"{[f'{f:.0%}' for f in cell['checkpoint_fractions']]} "
                  f"= {[f'{v:.2f}' for v in cell['x_checkpoints'][0]]} "
                  f"(seed 0)")
        if horizon["marginal_cells"]:
            print(f"        ** the settled/climbing call rests on the "
                  f"{X_SETTLED:.0%} threshold rather than on the data in "
                  f"{horizon['marginal_cells']}. Those cells carry nothing")
        print("        A6-17 reported, not judged: where x settles and what "
              "leak that leaves, above in the same lines")
    else:
        print("\n  A6-16 / A6-17 skipped")

    agreement = shape_agreement(curve, scan, rescan_lambdas)
    print(f"\n  A6-13 {'pass' if agreement['passed'] else 'FAIL'} -- "
          f"{SHAPE_DEFAULT} and {SHAPE_AXIS} point the same way "
          f"(band {agreement['band_non_empty_agrees']}, "
          f"scan {agreement['scan_verdict_agrees']}). If they did not, the "
          f"headline would rest on the tail of g rather than on lambda")

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
    ]
    skipped = [name for name, v in verdicts if v is None]
    criteria = [
        {"name": name, "passed": bool(v)}
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
                },
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
