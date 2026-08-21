"""B7 step 4a-0: does the constructed field land where it was aimed?

Registered in ``docs/b7_interaction_rank.md`` §3.16 and §3.17. **No null is drawn
in this file and no rank is estimated**, which is what makes it cheap enough to
run before the gate rather than after it.

Why it exists
-------------
§3.15's VOID 3 said the constructed field's spectrum must be **shaped** like the
observed one. §3.16 said shaping is not enough: it also has to be the **size** of
the observed one, and the sample it sits in has to carry the observed class main
effect, or the gate is easier than the reading it licenses. §3.17 said the size
target itself was wrong, because the observed `lambda_i` already contains the
sampling noise that the construction then adds again.

Every one of those is a claim about a construction, and a claim about a
construction is settled by building it and measuring it. That is all this file
does.

What it prints
--------------
For each constructed rank `r`, twice, once at `floor = 0` and once at
`floor = c`:

* the **recovered** top eigenvalues, from one pass of the same estimator the
  reading uses, against the **observed** top eigenvalues it was aimed at;
* the recovered `lambda_2 / lambda_1`, against the observed one;
* the same for the superseded ``calibration_sample``, flat and shaped, so the
  size of the correction is on the record rather than asserted.

What a good result looks like, declared before the run
------------------------------------------------------
**At `floor = c`, the recovered `lambda_1` and `lambda_2` should land within a
couple of percent of the observed ones, and the recovered ratio within a couple
of percent of the observed ratio.** That is §3.17's whole claim and it is the
condition on paying for the gate.

At `floor = 0` they should land **above** observed by about `c` in each
direction, which is §3.16's version and is why §3.17 exists. On the superseded
construction they should land above observed by a multiple, of roughly the trace
over the sum of the top two.

Usage::

    python experiments/b7_calib_check.py
    python experiments/b7_calib_check.py --grid coarse

Writes ``results/b7_calib_check_<grid>.json`` with ``diagnostic_only`` set, so
it reads as what it is and the runner ratchet needs no entry while B7 is open.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import (  # noqa: E402
    build_design,
    coarse_classes,
    complement_classes,
)
from monetary_topology.interaction_rank import (  # noqa: E402
    calibration_basis,
    calibration_sample,
    matched_sample,
    measure_noise_floor,
    solve_floor,
    spectrum,
)

RESULTS = ROOT / "results"

#: Constructed ranks to build. `0` to `2` are the gate's arms. `3` costs one more
#: pass and says whether the design has any room above the reading, which nothing
#: in the stage has asked yet.
CHECK_RANKS = (0, 1, 2, 3)

#: Draws averaged into the noise floor. Not a criterion: the per-draw values are
#: printed and recorded, so a floor whose draws disagree is visible rather than
#: hidden inside a mean.
FLOOR_DRAWS = 3


def top(eig: np.ndarray, k: int = 8) -> list[float]:
    return [float(v) for v in np.asarray(eig)[:k]]


def fmt(eig: np.ndarray, k: int = 6) -> str:
    return "[" + ", ".join(f"{v:.4g}" for v in np.asarray(eig)[:k]) + "]"


def run_arms(basis, cells, classes, n_cells, n_classes, obs, floor, seed):
    """One matched sample per rank at this floor, measured by one estimator pass."""
    out: dict[str, dict] = {}
    for r in CHECK_RANKS:
        try:
            v = matched_sample(basis, cells, classes, r,
                               np.random.default_rng(seed + 1000 * r), floor=floor)
        except ValueError as exc:
            out[str(r)] = {"unavailable": str(exc)}
            print(f"    rank {r}: unavailable, {exc}")
            continue
        eig, _vecs, _c, _co, _t = spectrum(cells, classes, v, n_cells, n_classes)
        ratio = float(eig[1] / eig[0]) if eig[0] > 0 else float("nan")
        out[str(r)] = {
            "recovered": top(eig),
            "recovered_ratio_2_to_1": ratio,
            "lambda1_over_observed": float(eig[0] / obs[0]),
            "lambda2_over_observed": float(eig[1] / obs[1]) if obs[1] > 0 else None,
        }
        print(f"    rank {r}  recovered {fmt(eig)}")
        print(f"             l2/l1 {ratio:.4f}   l1/obs {eig[0] / obs[0]:.4f}   "
              f"l2/obs {eig[1] / obs[1]:.4f}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", choices=("fine", "coarse", "complement"), default="fine")
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--solve", action="store_true",
                    help="also run §3.18's floor solve, which §3.19 voided as "
                         "noise-dominated. Off by default: it costs a dozen "
                         "passes to reproduce a superseded diagnostic")
    args = ap.parse_args()

    print("B7 step 4a-0: the calibration check. No null is drawn in this file.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    if args.grid == "coarse":
        classes = coarse_classes(classes, design["class_levels"])
        n_classes = int(classes.max()) + 1
    elif args.grid == "complement":
        classes = complement_classes(classes, design["class_levels"])
        n_classes = int(classes.max()) + 1

    print(f"  grid {args.grid}: {n_cells:,} cells, {n_classes} classes, "
          f"{values.size:,} loans\n")

    basis = calibration_basis(cells, classes, values, n_cells, n_classes)
    obs = np.asarray(basis.eigenvalues)
    trace = float(obs.sum())
    top2 = float(obs[:2].sum())

    print(f"  observed spectrum  {fmt(obs, 8)}")
    print(f"  observed fill {basis.fill:.4f}   within-entry sd {basis.sd:.4f}")
    print(f"  observed ratio l2/l1 {obs[1] / obs[0]:.4f}")
    print(f"  trace {trace:.4f}   top two {top2:.4f}   "
          f"top two share of trace {top2 / trace:.4f}")
    print(
        "\n  That share is §3.16's second point. The superseded construction "
        f"handed a\n  rank-two field the trace, so its two directions carried "
        f"{trace / top2:.2f}x the energy\n  the observed two do.\n"
    )

    floor, per_draw = measure_noise_floor(
        basis, cells, classes, np.random.default_rng(args.seed + 5), FLOOR_DRAWS
    )
    print(f"  §3.17 noise floor c = {floor:.6f}   "
          f"per draw {[round(v, 6) for v in per_draw]}")
    print(f"  observed lambda net of the floor: "
          f"{fmt(obs[:4] - floor, 4)}\n")

    record: dict = {
        "grid": args.grid,
        "n_cells": n_cells,
        "n_classes": n_classes,
        "n_loans": int(values.size),
        "fill": basis.fill,
        "within_entry_sd": basis.sd,
        "observed_eigenvalues": [float(v) for v in obs],
        "observed_trace": trace,
        "observed_top2_share_of_trace": top2 / trace,
        "noise_floor": floor,
        "noise_floor_per_draw": per_draw,
        "noise_floor_draws": FLOOR_DRAWS,
        "matched_floor_zero": {},
        "matched_floor_c": {},
        "superseded": {},
    }

    print("  matched_sample at floor = 0  (§3.16 as first written)\n")
    record["matched_floor_zero"] = run_arms(
        basis, cells, classes, n_cells, n_classes, obs, 0.0, args.seed
    )

    print(f"\n  matched_sample at floor = c = {floor:.6f}  (§3.17, the live "
          "construction)\n")
    record["matched_floor_c"] = run_arms(
        basis, cells, classes, n_cells, n_classes, obs, floor, args.seed
    )

    record["solved"] = {}
    if args.solve:
        print("\n  solve_floor (§3.18, VOIDED by §3.19, shown on request)\n")
    for r in (1, 2, 3) if args.solve else ():
        try:
            sol = solve_floor(basis, cells, classes, r,
                              np.random.default_rng(args.seed + 900 + r),
                              draws=FLOOR_DRAWS, start=floor, iters=1)
        except ValueError as exc:
            record["solved"][str(r)] = {"unavailable": str(exc)}
            print(f"    rank {r}: unavailable, {exc}")
            continue
        record["solved"][str(r)] = {
            "floor": sol.floor,
            "start": sol.start,
            "steps": sol.steps,
            "achieved": sol.achieved,
            "target": sol.target,
            "worst_relative_miss": sol.worst_relative_miss,
            "miss_before_solve": sol.miss_before_solve,
            "improved": bool(sol.improved),
            "draws": sol.draws,
        }
        print(f"    {sol.line()}")

    print("\n  calibration_sample (superseded, kept for the contrast)\n")
    for label, shape in (("flat", None), ("shaped", obs[:2])):
        v = calibration_sample(cells, classes, values, n_cells, n_classes, 2,
                               np.random.default_rng(args.seed + 77),
                               spectrum_shape=shape)
        eig, _vecs, _c, _co, _t = spectrum(cells, classes, v, n_cells, n_classes)
        ratio = float(eig[1] / eig[0]) if eig[0] > 0 else float("nan")
        record["superseded"][label] = {
            "recovered": top(eig),
            "recovered_ratio_2_to_1": ratio,
            "lambda1_over_observed": float(eig[0] / obs[0]),
            "lambda2_over_observed": float(eig[1] / obs[1]),
        }
        print(f"    rank 2, {label:6s} recovered {fmt(eig)}")
        print(f"                   l2/l1 {ratio:.4f}   "
              f"l1/obs {eig[0] / obs[0]:.4f}   l2/obs {eig[1] / obs[1]:.4f}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"b7_calib_check_{args.grid}.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B7",
                "step": "calibration_check",
                "seed": args.seed,
                "diagnostic_only": True,
                "diagnostic_reason": (
                    "B7 is open. This file draws no null and estimates no rank; "
                    "it measures whether the constructed field registered in "
                    "§3.16 and §3.17 lands at the observed level and shape. It is "
                    "an input to the gate and carries no reading of its own."
                ),
                **record,
            },
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    print(
        "\n  §3.18's one hard condition, declared before this ran: **the solve\n"
        "  reduces the miss.** A step that makes it worse is not doing what it\n"
        "  claims, and the construction falls back to §3.17's floor with the miss\n"
        "  reported. No threshold on the miss itself, for VOID 1's reason: the\n"
        "  miss travels with every rate the arm produces, which is more use than\n"
        "  a cutoff that throws it away."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
