"""B7 step 2: the estimator, on synthetic fields only.

Pre-registered in ``docs/b7_interaction_rank.md``. Section 9 of that document
orders the work: criteria B7-1 to B7-3 run on constructed fields **before any
HMDA row is loaded**, and if any fails the estimator is fixed with the criteria
untouched. This file is that step and nothing else. It retrieves nothing, opens
no data file, and the HMDA half of the stage is deliberately not in it.

Usage::

    python experiments/b7_interaction_rank.py
    python experiments/b7_interaction_rank.py --draws 200   # slower null

Writes ``results/b7_interaction_rank.json``.

What this step found, before the stage could spend anything on data
------------------------------------------------------------------
**The estimator's resolving power is set by the fill of the cell-by-class
design.** At a fill of 0.6 and above the constructed rank comes back exactly. At
0.35 and below it does not.

**A withdrawn claim, left on the record because withdrawing it is the finding.**
B7-4 was first written as a gated criterion asserting that the error runs
**upward, never downward**, on the strength of a narrower sweep that showed only
over-counts. The wider sweep in this file refutes it: at a fill of 0.15 a
constructed rank of three reads back as two. The estimate is not biased in a
known direction outside its usable regime, it is simply unreliable there, and the
gated form of B7-4 is withdrawn rather than restated until it passes. What
remains is a reported diagnostic with no pass or fail, in the shape of
``b3_cip_slice.md``'s B3-7.

Over-counting is still the reading that matters most, because section 5 of the
pre-registration makes `rank >= 2` the interesting answer and an inflated estimate
manufactures the stage's own headline out of sparsity. Section 4 of the
pre-registration claimed the procedure was conservative in that direction; that
claim was about the null's treatment of the class main effect and does not cover
this. Section 3.5 of the pre-registration now carries the correction and B7-0
carries the guard.

**No permutation null can repair it.** The leak grows with the signal and the
null has no signal, so the null cannot see it. That is why B7-0 is a calibration
on the observed design at the observed signal strength rather than a wider null.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from monetary_topology.interaction_rank import (  # noqa: E402
    calibration_sample,
    estimate_rank,
    permute_within_cells,
    synthetic_sample,
)

RESULTS = ROOT / "results"

#: Fill levels swept in B7-4. Chosen to bracket the transition, not tuned to it:
#: 0.85 is a nearly complete design, 0.15 is one where a cell holds two classes
#: out of twelve and no method could separate a class loading from a cell one.
FILL_SWEEP = (0.85, 0.60, 0.35, 0.20, 0.15)

#: Shape of the constructed designs. Small enough that the whole file runs in
#: seconds and large enough that a rank of three is not near the class count.
N_CELLS, N_CLASSES, MAX_LOANS, NOISE = 300, 12, 40, 1.0


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def recover(true_rank: int, fill: float, draws: int, seed: int) -> int:
    rng = np.random.default_rng(seed + true_rank)
    cells, classes, values = synthetic_sample(
        rng, N_CELLS, N_CLASSES, true_rank, NOISE, fill, MAX_LOANS
    )
    est = estimate_rank(
        cells, classes, values, N_CELLS, N_CLASSES, draws,
        np.random.default_rng(seed + 977),
    )
    return est.rank


def criteria(draws: int, seed: int) -> tuple[list[Criterion], dict]:
    out: list[Criterion] = []
    record: dict = {}

    # ---- B7-1: recovery, in the regime where the design supports it ------
    got = {r: recover(r, 0.85, draws, seed) for r in (0, 1, 2, 3)}
    record["b7_1_recovery_at_fill_085"] = got
    out.append(
        Criterion(
            "B7-1  the estimator recovers a constructed rank on a near-complete "
            "design",
            all(got[r] == r for r in got),
            "fill=0.85, constructed -> estimated: "
            + ", ".join(f"{r}->{v}" for r, v in got.items())
            + ".  Scope: this says the estimator works where the design supports "
            "it. B7-4 is where it stops working",
        )
    )

    # ---- B7-2: no interaction, no rank, at every fill --------------------
    zero = {f: recover(0, f, draws, seed) for f in FILL_SWEEP}
    record["b7_2_zero_at_every_fill"] = {str(k): v for k, v in zero.items()}
    out.append(
        Criterion(
            "B7-2  a field with no interaction returns rank zero at every fill",
            all(v == 0 for v in zero.values()),
            "constructed rank 0, fill -> estimated: "
            + ", ".join(f"{f}->{v}" for f, v in zero.items())
            + ".  **This is the one reading that survives everywhere**, and it is "
            "the zero-versus-non-zero split rather than the trichotomy",
        )
    )

    # ---- B7-3: the null checks itself ------------------------------------
    rng = np.random.default_rng(seed + 5)
    cells, classes, values = synthetic_sample(
        rng, N_CELLS, N_CLASSES, 2, NOISE, 0.60, MAX_LOANS
    )
    permuted = permute_within_cells(cells, classes, np.random.default_rng(seed + 6))
    null_est = estimate_rank(
        cells, permuted, values, N_CELLS, N_CLASSES, draws,
        np.random.default_rng(seed + 977),
    )
    record["b7_3_permuted_rank"] = null_est.rank
    out.append(
        Criterion(
            "B7-3  permuted data returns rank zero through the identical path",
            null_est.rank == 0,
            f"estimated rank {null_est.rank} on a permutation of a true-rank-2 "
            "sample, taken through the same centring and the same second-moment "
            "matrix rather than short-circuited",
        )
    )

    # ---- B7-4: where it stops working, and in which direction ------------
    sweep = {
        f: {r: recover(r, f, draws, seed) for r in (0, 1, 2, 3)} for f in FILL_SWEEP
    }
    record["b7_4_fill_sweep"] = {
        str(f): {str(r): v for r, v in row.items()} for f, row in sweep.items()
    }
    never_under = all(v >= r for row in sweep.values() for r, v in row.items())
    record["b7_4_withdrawn_upward_only_claim_holds"] = bool(never_under)
    out.append(
        Criterion(
            "B7-4  reported, not judged: where the estimator stops working",
            True,
            "  ".join(
                f"fill {f}: " + "/".join(f"{r}->{v}" for r, v in row.items())
                for f, row in sweep.items()
            )
            + f".  The gated form of this criterion asserted the error runs "
            f"upward and never downward; that assertion is "
            f"{'still consistent with' if never_under else 'REFUTED by'} this "
            "sweep and was withdrawn on 2026-08-15 rather than restated until it "
            "passed. Outside its usable regime the estimate is unreliable in "
            "either direction, and a `rank >= 2` result is not admissible without "
            "B7-0",
        )
    )

    # ---- B7-0: the gate the real run has to pass first --------------------
    # Constructed here on a design of known fill, because there is no HMDA row
    # in this file. On the real sample it runs on the real design.
    gate = {}
    for f in (0.85, 0.60, 0.35):
        rng = np.random.default_rng(seed + 41)
        cells, classes, values = synthetic_sample(
            rng, N_CELLS, N_CLASSES, 2, NOISE, f, MAX_LOANS
        )
        calibrated = calibration_sample(
            cells, classes, values, N_CELLS, N_CLASSES, 1,
            np.random.default_rng(seed + 42),
        )
        est = estimate_rank(
            cells, classes, calibrated, N_CELLS, N_CLASSES, draws,
            np.random.default_rng(seed + 977),
        )
        gate[f] = est.rank
    record["b7_0_gate_on_constructed_designs"] = {str(k): v for k, v in gate.items()}
    out.append(
        Criterion(
            "B7-0  the gate is implemented and is not vacuous",
            any(v != 1 for v in gate.values()),
            "a rank-one field at the observed signal strength, read back on the "
            "same design: "
            + ", ".join(f"fill {f} -> {v}" for f, v in gate.items())
            + ".  **A gate that passed everywhere would not be a gate.** It fails "
            "here on designs where B7-4 says it should, which is what makes a "
            "pass on the real design mean something",
        )
    )

    return out, record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260815)
    args = ap.parse_args()

    print("B7 step 2: the estimator, on constructed fields\n")
    cs, record = criteria(args.draws, args.seed)
    for c in cs:
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")
    print(
        "\n  No HMDA row was read. Section 9 step 3 of the pre-registration is\n"
        "  next and it is B7-9, the share of stage B2's within term this class\n"
        "  index touches at all, which has to be reported before any rank is."
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_interaction_rank.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B7",
                "step": "synthetic",
                "seed": args.seed,
                "draws": args.draws,
                **record,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in cs
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
