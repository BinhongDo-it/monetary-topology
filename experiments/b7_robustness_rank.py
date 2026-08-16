"""B7 step 4c-b: B7-7 and B7-8, with every arm gated.

Rewritten 2026-08-16 under ``docs/b7_interaction_rank.md`` §3.15 VOID 1 and
VOID 2, §3.16, §3.17 and §3.19.

**VOID 2 removed the design-identity rule, so ``GATE_CARRIES`` is gone.** The old
version skipped a gate when an arm's surviving cell set matched the registered
design's exactly. That is an exact-match test on `326,872` elements with the
threshold at zero: informative at the "same" end, useless at the "different" end,
and aimed at the wrong quantity, since what a gate depends on is the
co-occurrence counts and three cells move those by about `1e-5`. It existed to
save time. **Every arm is now gated.** The co-occurrence comparison stays in
``b7_robustness.py`` as description of how similar two designs are, and it
licenses nothing.

The one identity that is not a tolerance
----------------------------------------
`band_20` is not "close to" the registered design. It **is** the registered
design: ``build_design`` calls ``design_from_loaded(loaded, cell_ids=cell_ids)``
with `bound` at its default of ``SPREAD_BOUND = 20``, which is the same call this
file makes for that arm. So its gate is expected to reproduce
``b7_gate.py --grid fine`` digit for digit at the same seed and draw count, and
this file checks that it does. **That is an integration check between two
scripts and not a licence to skip anything**, which is why the arm is gated here
rather than carried.

Usage::

    python experiments/b7_robustness_rank.py --draws 5 --reps 2 --smoke
    python experiments/b7_robustness_rank.py --jobs 16               # full
    python experiments/b7_robustness_rank.py --only band_10,band_15  # in sessions

Writes ``results/b7_robustness_rank_draws<N>_reps<M>.json``. Every repetition of
every arm is checkpointed under ``data/processed/`` and an interrupted run
resumes where it stopped, so the union of several ``--only`` runs is the same
object as one run.

What can and cannot come out of this
------------------------------------
**The headline is already withdrawn** and §7 is not in question. §10.6 names the
stage's terminal state as a standoff between "the fine grid's `2` is real" and
"it is fragile". These arms are the only registered ones that can move it. A `2`
that dies under a band change, a rank transform or a split by year resolves the
standoff toward fragile. A `2` that survives all three pins the disagreement to
class resolution and nothing else.

B7-8 is not a rank comparison. It estimates the **leading class loading** on the
odd years and checks its **signs** on the even years, which is `b3_cip_slice.md`
B3-6's discipline: the axis a thing is selected on must not be the axis it is
tested on. Because `activity_year` is one of the cell keys, the two halves share
no cell at all, which is as disjoint as this sample gets.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import design_from_loaded, load_cached  # noqa: E402
from b7_gate import (  # noqa: E402
    FLOOR_DRAWS,
    GATE_RANKS,
    ckpt_path,
    load_ckpt,
    run_arms,
    summarise,
)
from monetary_topology.effective_price import (  # noqa: E402
    BOUND_SWEEP,
    SPREAD_BOUND,
)
from monetary_topology.interaction_rank import (  # noqa: E402
    calibration_basis,
    estimate_rank,
    measure_noise_floor,
)

RESULTS = ROOT / "results"

#: The arm whose design is the registered one by construction, not by tolerance.
REFERENCE_ARM = f"band_{SPREAD_BOUND:g}"


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def reading(rank: int) -> str:
    return {0: "zero", 1: "one ladder"}.get(rank, "no single ladder")


def build_arms(loaded, cell_ids):
    """Every registered arm, as integer arrays. The strings are freed by the caller."""
    arms: dict[str, tuple] = {}
    for bound in BOUND_SWEEP:
        c, k, v, _y, d = design_from_loaded(loaded, bound=bound, cell_ids=cell_ids)
        arms[f"band_{bound:g}"] = (c, k, v, d["n_cells"], d["n_classes"])
    c, k, v, _y, d = design_from_loaded(
        loaded, bound=None, rank_transform=True, cell_ids=cell_ids
    )
    arms["rank_unbanded"] = (c, k, v, d["n_cells"], d["n_classes"])

    ref_cells, ref_classes, ref_values, ref_years, ref_design = design_from_loaded(
        loaded, cell_ids=cell_ids
    )
    parity = ref_years.astype(np.int64) % 2
    for label, want in (("odd_years", 1), ("even_years", 0)):
        m = parity == want
        cc = np.unique(ref_cells[m], return_inverse=True)[1]
        arms[label] = (cc, ref_classes[m], ref_values[m],
                       int(cc.max()) + 1, ref_design["n_classes"])
    return arms


def gate_one(label, c, k, v, nc, nk, args):
    """§3.16 basis, §3.17 floor, VOID 1 rates. Checkpointed per repetition."""
    basis = calibration_basis(c, k, v, nc, nk)
    floor, per_draw = measure_noise_floor(
        basis, c, k, np.random.default_rng(args.seed + 5), FLOOR_DRAWS
    )
    obs = np.asarray(basis.eigenvalues)
    print(f"\n  {label}: {nc:,} cells, {nk} classes, {v.size:,} loans")
    print(f"    observed spectrum {', '.join(f'{x:.4g}' for x in obs[:4])}")
    print(f"    noise floor {floor:.6f}")

    ckpt_file = ckpt_path(f"arm_{label}", args.draws, args.seed)
    ckpt = {} if args.fresh else load_ckpt(ckpt_file)
    if ckpt:
        print(f"    resuming: {sum(1 for x in ckpt if ':unavailable' not in x)} "
              "repetitions already done")
    raw = run_arms(c, k, v, nc, nk, basis, floor, args.draws, args.reps,
                   args.seed, args.jobs, ckpt, ckpt_file)
    cs, summary = summarise(raw, args.reps, args.draws, obs)
    return {
        "n_cells": nc, "n_classes": nk, "n_loans": int(v.size),
        "observed_eigenvalues": [float(x) for x in obs],
        "noise_floor": floor, "noise_floor_per_draw": per_draw,
        "arms": summary,
        "criteria": [{"name": x.name, "passed": bool(x.passed), "detail": x.detail}
                     for x in cs],
        "repetitions": raw,
    }


def rate_line(gate: dict) -> str:
    """One arm's three rates and its calibration, compressed onto one line."""
    bits = []
    for name in ("B7-0c", "B7-0a", "B7-0b"):
        a = gate["arms"].get(name)
        if a is None or "unavailable" in a:
            bits.append(f"{name} n/a")
        elif a["kind"] == "size":
            bits.append(f"{name} {a['failures']}/{a['n']} "
                        f"p={a['binomial_tail_at_least']:.3f}")
        else:
            bits.append(f"{name} power {a['power']:.2f}")
    cal = gate["arms"].get("B7-0b", {}).get("achieved_level", {})
    if cal:
        bits.append("cal " + " ".join(
            f"{key} {val['mean']:.3f}+-{val['sd']:.3f}" for key, val in cal.items()
        ))
    return "; ".join(bits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="a reduced run: writes to results/subset/ with "
                         "diagnostic_only set, so it cannot displace a full record")
    ap.add_argument("--only", default=None,
                    help="comma separated arm labels, for running the sweep in "
                         "sessions; the checkpoint makes the union of several "
                         "runs identical to one run")
    args = ap.parse_args()

    print("B7 step 4c-b: B7-7 and B7-8. Every arm is gated (VOID 2).\n")
    loaded, cell_ids = load_cached()
    arms = build_arms(loaded, cell_ids)

    # Every arm now holds its own integer arrays, so the strings can go.
    # ``load_with_class`` returns seven fixed-width unicode columns over twenty
    # million rows and ``make_cell_ids`` returns their join, which together are
    # several times the size of everything this script needs from here on.
    # Freeing them before the gates start is what makes a high ``--jobs`` safe.
    del loaded, cell_ids
    gc.collect()

    want = set(args.only.split(",")) if args.only else set(arms)
    unknown = want - set(arms)
    if unknown:
        raise SystemExit(f"unknown arm(s): {sorted(unknown)}\n"
                         f"available: {sorted(arms)}")

    record: dict = {"gates": {}, "estimates": {}}
    started = time.monotonic()

    for label, (c, k, v, nc, nk) in arms.items():
        if label not in want:
            continue
        record["gates"][label] = gate_one(label, c, k, v, nc, nk, args)
        print(f"    {label}: {rate_line(record['gates'][label])}")
    print(f"\n  gates done in {(time.monotonic() - started) / 60:.0f} min\n")

    print("  estimates on the observed field\n")
    for index, (label, (c, k, v, nc, nk)) in enumerate(arms.items()):
        if label not in want:
            continue
        order = np.argsort(c, kind="stable")
        est = estimate_rank(c, k, v, nc, nk, args.draws,
                            np.random.default_rng(args.seed + 31 + index),
                            stable_order=order, jobs=args.jobs)
        record["estimates"][label] = {
            "rank": est.rank, "null_max": est.null_max, "fill": est.fill,
            "eigenvalues": est.eigenvalues[:6].tolist(),
            "leading_loading": est.eigenvectors[:, 0].tolist(),
        }
        print(f"    {label:16s} rank {est.rank}  null_max {est.null_max:.4g}"
              f"  lambda1 {est.eigenvalues[0]:.4g}")

    cs: list[Criterion] = []

    # ---- the integration check, which is not a licence ----------------
    fine = RESULTS / f"b7_gate_draws{args.draws}_reps{args.reps}.json"
    if REFERENCE_ARM in record["gates"] and fine.exists():
        got = record["gates"][REFERENCE_ARM]["repetitions"]
        theirs = json.loads(fine.read_text(encoding="utf-8"))["repetitions"]
        shared = sorted(set(got) & set(theirs))
        same = [x for x in shared if got[x] == theirs[x]]
        cs.append(Criterion(
            f"B7-7z  {REFERENCE_ARM} reproduces b7_gate.py --grid fine exactly",
            len(same) == len(shared) and len(shared) > 0,
            f"**{len(same)} of {len(shared)} shared repetitions are identical.** "
            "The two scripts build that design by the same call with the same "
            "arguments, so agreement is expected digit for digit and a "
            "disagreement is a plumbing fault in one of them. This is an "
            "integration check between two files and it licenses nothing",
        ))

    # ---- B7-7 ---------------------------------------------------------
    band_arms = [f"band_{b:g}" for b in BOUND_SWEEP] + ["rank_unbanded"]
    present = [a for a in band_arms if a in record["estimates"]]
    readings = {a: record["estimates"][a]["rank"] for a in present}
    ref = readings.get(REFERENCE_ARM)
    cs.append(Criterion(
        "B7-7  reported, not gated: does the answer live in the spread band",
        True,
        "; ".join(f"{a}: {readings[a]} ({reading(readings[a])})" for a in present)
        + (f".  **All agree with {REFERENCE_ARM}'s {ref}.**"
           if ref is not None and all(r == ref for r in readings.values())
           else ".  **They do not all agree.**")
        + "  The rank-transformed arm carries no band at all, which is what "
        "`rank_decomposition` does and what makes it the arm a band artefact "
        "could not survive.  Each reading is to be quoted with its own arm's "
        "three rates and its calibration's achieved level, both under `gates` in "
        "the result record. VOID 1 replaced the gated/ungated bit with those "
        "numbers and this criterion does not put it back",
    ))

    # ---- B7-8 ---------------------------------------------------------
    if "odd_years" in record["estimates"] and "even_years" in record["estimates"]:
        odd = record["estimates"]["odd_years"]
        even = record["estimates"]["even_years"]
        lo, le = np.array(odd["leading_loading"]), np.array(even["leading_loading"])
        # A leading eigenvector is defined up to sign; orient by the larger overlap.
        flip = -1.0 if float(lo @ le) < 0 else 1.0
        agree = int((np.sign(lo) == np.sign(le * flip)).sum())
        record["b7_8"] = {
            "classes": int(lo.size), "sign_agreement": agree,
            "orientation_flip": flip, "cosine": float(abs(lo @ le)),
            "odd_rank": odd["rank"], "even_rank": even["rank"],
        }
        cs.append(Criterion(
            "B7-8  selection axis disjoint from test axis",
            agree * 2 > lo.size,
            f"leading class loading estimated on odd years, signs checked on "
            f"even: **{agree} of {lo.size} classes agree**, |cos| = "
            f"{abs(float(lo @ le)):.4f}.  Ranks {odd['rank']} and {even['rank']}.  "
            "`activity_year` is a cell key, so the two halves share no cell; the "
            "eigenvector's sign is arbitrary and is oriented by the larger "
            "overlap before counting, which is a convention and not a result.  "
            "**This one is gated**, because it is a claim about a direction being "
            "stable and not a rate against a nominal",
        ))

    for x in cs:
        print()
        print(x.line())
    n_pass = sum(x.passed for x in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")
    print("\n  §7 is not in question and the headline stays withdrawn whatever "
          "these say.\n  What they move is §10.6's standoff.")

    where = (RESULTS / "subset") if args.smoke else RESULTS
    where.mkdir(parents=True, exist_ok=True)
    out = where / f"b7_robustness_rank_draws{args.draws}_reps{args.reps}.json"
    out.write_text(
        json.dumps(
            {"stage": "B7", "step": "robustness_rank", "seed": args.seed,
             "diagnostic_only": bool(args.smoke),
             "draws": args.draws, "reps": args.reps, "jobs": args.jobs,
             "nominal_size": 1.0 / (args.draws + 1),
             "only": sorted(want), "reference_arm": REFERENCE_ARM,
             "gate_ranks": list(GATE_RANKS), **record,
             "criteria": [{"name": x.name, "passed": bool(x.passed),
                           "detail": x.detail} for x in cs]},
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
