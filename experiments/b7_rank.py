"""B7 step 4b: the readings. B7-4, B7-5, B7-6 and B7-10.

Rewritten 2026-08-16 under ``docs/b7_interaction_rank.md`` §3.15 VOID 1, §3.21
and §3.22.

**Two things left this file.**

**The embedded gate.** It ran three repetitions of a constructed field under the
secondary null and **refused to compute B7-4 unless every one returned its
constructed rank**. Both halves are void: the construction was
`calibration_sample`, which §3.16 and §3.17 superseded, and the verdict was a
unanimity rule, which §3.15's VOID 1 struck out. The function is kept below, never
called, because nothing in this repository is deleted and a reader checking that
claim needs the thing itself.

**The hard stop.** VOID 1 replaced the gate's pass/fail with three rates, so there
is no longer a bit to stop on. **This file now always computes its readings and
always quotes them with whatever gate evidence exists for that grid, including
none.** A reading printed beside "no gate record for this grid" is more use than a
reading that was not printed, and it cannot be mistaken for a licensed one.

**What §3.21 changed in the answers, not in the code.** The class levels were
stored alphabetically and read positionally, so every partition this stage built
merged the wrong classes. `b7_design.levels_by_code` fixes it. B7-6's earlier
failure was against an index that put `<20%` in the same class as `49`. On the
corrected partitions the coarse grid reads `2` (§3.22), so **B7-6 is expected to
pass**, and §3.11's three declared readings for the complement grid are void along
with the §3.9 to §3.12 chain they rested on.

**The partition memberships are printed before anything is computed.** That is
§3.21's guard, and it is the one thing that would have caught the bug on the day
it was written.

Usage::

    python experiments/b7_rank.py                 # 50 draws
    python experiments/b7_rank.py --draws 200 --jobs 16

Writes ``results/b7_rank_draws<N>.json``.

What the constructed sweep of §3.5 could not have told us
---------------------------------------------------------
§3.5 swept **fill** and read a boundary off it at `0.60`. The real design's fill
is `0.7222`, above that boundary. But constructed designs at the *same* fill do
**not** recover cleanly: over five seeds at fill `0.72` and three hundred cells, a
constructed rank of two came back as three in two of them.

**Fill is not the sufficient statistic. The co-occurrence counts are.** The real
design carries `326,872` cells with a median of fourteen classes each, so every
entry of `S` is a mean over an enormous number of cells; the constructed designs
carried three hundred. §3.5's table is therefore a **lower bound** on what a real
design of that fill can do. Recorded because the reverse mistake, reading it as an
upper bound and declaring the stage dead, was available and would have been wrong.
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

from b7_design import (  # noqa: E402
    build_design,
    complement_classes,
    describe_partition,
)
from b7_design import coarse_classes as _coarse  # noqa: E402
from b7_gate import GATE_RANKS  # noqa: E402
from monetary_topology.interaction_rank import (  # noqa: E402
    calibration_sample,
    estimate_rank,
    estimate_rank_residual_null,
)

RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def coarse_classes(class_codes: np.ndarray, levels: list[str]) -> np.ndarray:
    """Delegates to :func:`b7_design.coarse_classes`.

    **Moved on 2026-08-15, unchanged.** The mapping is the class index's business
    and ``b7_gate.py`` needs it too, so it lives beside the fine grid it coarsens
    rather than in two places. Kept as a name here so nothing that imported it
    breaks.
    """
    return _coarse(class_codes, levels)


def _voided_residual_null_gate(
    cells, classes, values, n_cells, n_classes, draws, reps, seed, order, jobs
) -> tuple[dict[int, list[int]], bool, bool]:
    """The pre-2026-08-16 embedded gate. **Voided and never called.**

    Two independent reasons, either enough on its own. Its construction is
    ``calibration_sample``, which §3.16 showed carries no class main effect and
    scales a rank-`r` field to the whole trace, and which §3.17 showed aims at an
    observed eigenvalue that already contains the noise it then adds again. And
    its verdict is a unanimity rule over three repetitions, which §3.15's VOID 1
    struck out: three trials cannot estimate a rate, and thresholding an
    unestimated rate at one fails a design whose true recovery rate is `0.9`
    twenty-seven percent of the time.

    Kept because nothing here is deleted and because the claim that it is void
    should be checkable against the code that made it.
    """
    got: dict[int, list[int]] = {}
    for rank in GATE_RANKS:
        run = []
        for r in range(reps):
            synthetic = calibration_sample(
                cells, classes, values, n_cells, n_classes, rank,
                np.random.default_rng(seed + 1000 * rank + r),
            )
            est = estimate_rank_residual_null(
                cells, classes, synthetic, n_cells, n_classes, draws,
                np.random.default_rng(seed + 7717), stable_order=order, jobs=jobs,
            )
            run.append(est.rank)
        got[rank] = run
    return got, all(v == 1 for v in got[1]), all(v == 2 for v in got[2])


def reading(rank: int) -> str:
    return {0: "zero", 1: "one ladder"}.get(rank, "no single ladder")


def gate_evidence(grid: str, draws: int) -> str:
    """Whatever `b7_gate.py` has recorded for this grid, quoted beside the reading.

    VOID 1 turned the gate from a bit into three rates, so there is nothing here
    to stop on and nothing to be licensed by. What there is, is evidence, and the
    reading is quoted with it. **A grid with no gate record says so in the same
    sentence as its number**, which is what the old hard stop was for and is
    strictly more informative than not printing the number at all.
    """
    stem = "b7_gate" if grid == "fine" else f"b7_gate_{grid}"
    hits = sorted(RESULTS.glob(f"{stem}_draws{draws}_reps*.json"))
    if not hits:
        return (f"**no gate record for the {grid} grid at {draws} draws.** "
                "Run `b7_gate.py"
                + ("" if grid == "fine" else f" --grid {grid}")
                + f" --draws {draws}`; until then this number is unquoted")
    d = json.loads(hits[-1].read_text(encoding="utf-8"))
    bits = []
    for name in ("B7-0c", "B7-0a", "B7-0b"):
        a = d.get("arms", {}).get(name)
        if a is None or "unavailable" in a:
            bits.append(f"{name} n/a")
        elif a.get("kind") == "size":
            bits.append(f"{name} {a['failures']}/{a['n']} at nominal "
                        f"{d['nominal_size']:.4f}, "
                        f"p={a['binomial_tail_at_least']:.3f}")
        else:
            lo, hi = a["wilson_95"]
            bits.append(f"{name} power {a['power']:.2f} [{lo:.2f}, {hi:.2f}]")
    cal = d.get("arms", {}).get("B7-0b", {}).get("achieved_level", {})
    if cal:
        bits.append("calibration achieved " + " ".join(
            f"{k} {v['mean']:.3f}+-{v['sd']:.3f}" for k, v in cal.items()))
    return f"gate ({hits[-1].name}): " + "; ".join(bits)


def read_grid(label, cells, ids, values, n_cells, n_groups, draws, seed, order, jobs):
    """Both nulls on one class index, and everything worth storing from each."""
    primary = estimate_rank(cells, ids, values, n_cells, n_groups, draws,
                            np.random.default_rng(seed), stable_order=order,
                            jobs=jobs)
    residual = estimate_rank_residual_null(
        cells, ids, values, n_cells, n_groups, draws,
        np.random.default_rng(seed), stable_order=order, jobs=jobs)
    print(f"    {label:12s} primary {primary.rank}  residual {residual.rank}  "
          f"null_max {primary.null_max:.4g} / {residual.null_max:.4g}  "
          f"spectrum {', '.join(f'{v:.4g}' for v in primary.eigenvalues[:4])}")
    return primary, residual


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260815)
    ap.add_argument(
        "--jobs", type=int, default=None,
        help="threads for the null draws; results are identical at any value",
    )
    args = ap.parse_args()

    print("B7 step 4b: the readings. The gate is quoted beside them, not "
          "stopped on.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = design["class_levels"]
    order = np.argsort(cells, kind="stable")
    print(f"  design: {n_cells:,} cells, {n_classes} classes, {values.size:,} "
          f"loans, fill {design['fill']:.4f}\n")

    coarse = coarse_classes(classes, lv)
    comp = complement_classes(classes, lv)
    n_coarse, n_comp = int(coarse.max()) + 1, int(comp.max()) + 1

    # §3.21's guard. A partition's name is not its membership, and for the whole
    # of this stage before 2026-08-16 the two were different.
    members = {}
    for name, ids in (("coarse", coarse), ("complement", comp)):
        members[name] = describe_partition(classes, ids, lv)
        print(f"  {name} partition membership")
        for g, v in sorted(members[name].items()):
            print(f"    group {g}: {', '.join(v)}")
        print()

    print("  readings, both nulls\n")
    fine_p, fine_r = read_grid("fine", cells, classes, values, n_cells, n_classes,
                               args.draws, args.seed + 31, order, args.jobs)
    coarse_p, coarse_r = read_grid("coarse", cells, coarse, values, n_cells,
                                   n_coarse, args.draws, args.seed + 31, order,
                                   args.jobs)
    comp_p, comp_r = read_grid("complement", cells, comp, values, n_cells, n_comp,
                               args.draws, args.seed + 31, order, args.jobs)

    record: dict = {
        "design": design,
        "partition_membership": {k: {str(g): v for g, v in m.items()}
                                 for k, m in members.items()},
        "b7_4_fine_primary": fine_p.line(),
        "b7_4_fine_primary_rank": fine_p.rank,
        "b7_5_fine_residual_rank": fine_r.rank,
        "b7_6_coarse_primary_rank": coarse_p.rank,
        "b7_6_coarse_residual_rank": coarse_r.rank,
        "b7_10_complement_primary_rank": comp_p.rank,
        "b7_10_complement_residual_rank": comp_r.rank,
        "n_coarse_classes": n_coarse,
        "n_complement_classes": n_comp,
        "eigenvalues_fine": fine_p.eigenvalues[:8].tolist(),
        "eigenvalues_coarse": coarse_p.eigenvalues[:8].tolist(),
        "eigenvalues_complement": comp_p.eigenvalues[:8].tolist(),
        "null_max_primary": fine_p.null_max,
        "null_max_residual": fine_r.null_max,
        "null_max_coarse_primary": coarse_p.null_max,
        "null_max_complement_primary": comp_p.null_max,
    }

    cs = [
        Criterion(
            "B7-4  reported, not gated: the estimate",
            True,
            f"**matrix rank {fine_p.rank}, read as: {reading(fine_p.rank)}**.  "
            f"{fine_p.line()}.  {gate_evidence('fine', args.draws)}",
        ),
        Criterion(
            "B7-5  the answer does not live in the null",
            reading(fine_p.rank) == reading(fine_r.rank),
            f"primary null {fine_p.rank} ({reading(fine_p.rank)}), residual null "
            f"{fine_r.rank} ({reading(fine_r.rank)}); null maxima "
            f"{fine_p.null_max:.4g} and {fine_r.null_max:.4g}.  Agreement is "
            "required on §5's reading and not on the integer",
        ),
        Criterion(
            "B7-6  the answer does not live in the class grid",
            reading(fine_p.rank) == reading(coarse_p.rank)
            and reading(coarse_p.rank) == reading(coarse_r.rank),
            f"fine grid ({n_classes} levels) {fine_p.rank}, coarse grid "
            f"({n_coarse} levels) {coarse_p.rank} under the primary null and "
            f"{coarse_r.rank} under the residual.  **The coarse grid's membership "
            "is printed above and is the regulator's five published buckets with "
            "the fourteen integers `36` to `49` merged.** Before §3.21 it was not, "
            "and this criterion's earlier failure was against a scrambled index.  "
            f"{gate_evidence('coarse', args.draws)}",
        ),
        Criterion(
            "B7-10  reported, not gated: what the integer resolution carries",
            True,
            f"complement grid ({n_comp} levels: the fourteen integers kept apart, "
            f"the five buckets merged) returns {comp_p.rank} under the primary "
            f"null and {comp_r.rank} under the residual, spectrum "
            f"{', '.join(f'{v:.4g}' for v in comp_p.eigenvalues[:4])} against "
            f"`null_max` {comp_p.null_max:.4g}.  **§3.11's three declared readings "
            "are void**, along with the §3.9 to §3.12 chain they rested on, "
            "because all of it assumed the coarse grid expresses a second "
            "direction and does not (§3.22). B7-11 is the arm that reads this one "
            f"now.  {gate_evidence('complement', args.draws)}",
        ),
    ]

    print()
    for c in cs:
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")
    print("\n  Nothing above was licensed by a gate and nothing was blocked by "
          "one.\n  VOID 1 replaced the licence with three rates, quoted inside "
          "each criterion.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"b7_rank_draws{args.draws}.json"
    out.write_text(
        json.dumps(
            {"stage": "B7", "step": "rank", "seed": args.seed,
             "draws": args.draws, "jobs": args.jobs, **record,
             "criteria": [{"name": c.name, "passed": bool(c.passed),
                           "detail": c.detail} for c in cs]},
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
