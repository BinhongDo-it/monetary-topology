"""B7 step 4a: the gate. B7-0, on the real design.

Rewritten 2026-08-16 under ``docs/b7_interaction_rank.md`` §3.15 VOID 1,
§3.16, §3.17 and §3.19. **Every gate this stage ran before that date is
superseded**; §3.16's closing paragraph says why and it is not a matter of which
arms passed.

**This file never estimates the rank of the observed field.** It estimates the
rank of *constructed* fields laid on the observed design. It does read the
observed **spectrum**, because §3.17 sets the constructed field's level from it,
and a spectrum is not a rank: the rank needs the null, and no null in this file
is ever drawn against the observed values.

What changed, and why each is not a loosening
---------------------------------------------
**VOID 1: the unanimity rule is gone.** Three repetitions thresholded at "all
three" estimates a rate with three trials and then demands perfection of it. The
arms now report a **rate over twenty repetitions**, against the estimator's own
nominal size

    P(observed exceeds all d draws) = 1 / (d + 1)

which comes from exchangeability and from nothing anyone chose. The two size arms
get the exact binomial tail against that nominal; the power arm has no nominal,
so it gets a Wilson interval. **All three are reported and none is gated.**

**VOID 1, second half: the nominal is an upper bound here, and the test is
one-sided.** The primary null redistributes the class main effect, which inflates
it, so the true size sits **below** `1/(d+1)`. A rate significantly above it says
the estimator's size is broken on this design. A rate below it is expected and
says nothing. §3.16 keeps that inflation deliberately, because the reading is
taken under the same null.

**§3.16 and §3.17: the constructed field is matched to the observed one.** It
carries the observed additive fit, so the null it faces is the null the reading
faces. Its interaction is set to the observed top-`r` eigenvalues in level and in
shape, net of the measured noise floor, rather than to the observed Frobenius
norm with a random shape. The old construction was out by `2.63x` on the second
eigenvalue of the fine grid, which is the eigenvalue the whole stage turns on.

**§3.19: the achieved level is reported and costs nothing.** Every repetition
constructs a fresh field and the estimator returns its spectrum, so an arm's
twenty repetitions are twenty measurements of what the construction achieved. The
mean and standard deviation of `recovered lambda_i / observed lambda_i` are
printed and stored beside every rate.

Usage::

    python experiments/b7_gate.py --draws 5 --reps 2 --smoke  # smoke, ~2 min
    python experiments/b7_gate.py                             # 50 draws, 20 reps
    python experiments/b7_gate.py --grid coarse --jobs 16

Writes ``results/b7_gate<_grid>_draws<N>_reps<M>.json``, and checkpoints every
repetition to ``data/processed/`` so an interrupted run resumes where it stopped.
The checkpoint is keyed by grid, draws and seed and **not** by the repetition
count, so the smoke run above is not wasted: its two repetitions are the first
two of the full run, bit for bit, because every repetition's two seeds come from
the grid, the seed and its own index and nothing else.

Memory. The design arrays, the calibration basis and one constructed sample are
about `0.8 GB` together at sixteen million loans, and each null worker allocates
roughly `0.4 GB` transiently. ``--jobs 16`` therefore wants about `8 GB` free.
The default is half the logical cores capped at eight.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
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
    binomial_tail_at_least,
    calibration_basis,
    estimate_rank,
    matched_sample,
    measure_noise_floor,
    wilson_interval,
)

RESULTS = ROOT / "results"
CKPT_DIR = ROOT / "data" / "processed"

#: Constructed ranks laid on the observed design, and what each one measures.
#: `0` and `1` are size arms and have a nominal. `2` is power and has none.
GATE_RANKS = (0, 1, 2)

#: Draws averaged into §3.17's noise floor. Not a criterion: the per-draw values
#: are stored, so a floor whose draws disagree is visible.
FLOOR_DRAWS = 3

#: What each arm counts as a failure, given the constructed rank.
#: A size arm fails by reading **above** what it was given; the power arm fails by
#: reading anything other than what it was given.
ARM = {
    0: ("B7-0c", "size", "reads >= 1"),
    1: ("B7-0a", "size", "reads >= 2"),
    2: ("B7-0b", "power", "reads != 2"),
}


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def arm_seeds(seed: int, rank: int, rep: int) -> tuple[int, int]:
    """The two seeds a repetition uses: one for the field, one for the null.

    **Each repetition gets its own null seed.** The superseded version reused one
    null seed across every repetition of an arm, which made the repetitions share
    their null randomness and correlated them. A rate estimated from correlated
    trials has a smaller spread than it should and the binomial line beside it
    would then be wrong. Independent seeds cost nothing.
    """
    base = seed + 1_000_000 * (rank + 1) + 1_000 * rep
    return base, base + 500_000_000


def ckpt_path(grid: str, draws: int, seed: int) -> Path:
    """Keyed by grid, draw count and seed. **Not by the repetition count.**

    A repetition's two seeds come from ``arm_seeds(seed, rank, rep)`` and its
    result depends on the draw count, so repetition `k` of a twenty-repetition
    run is the identical object as repetition `k` of a two-repetition run at the
    same grid, draws and seed. Keying on ``reps`` would throw that away and make
    a smoke run at ``--reps 2`` worthless to the full one.
    """
    return CKPT_DIR / f"b7_gate_ckpt_{grid}_d{draws}_s{seed}.json"


def load_ckpt(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        print(f"  checkpoint at {path.name} is unreadable, starting fresh")
        return {}


def run_arms(
    cells, classes, values, n_cells, n_classes, basis, floor,
    draws, reps, seed, jobs, ckpt, ckpt_file,
):
    """One record per (constructed rank, repetition). Checkpointed after each."""
    order = np.argsort(cells, kind="stable")
    obs = np.asarray(basis.eigenvalues)
    out: dict[str, dict] = dict(ckpt)
    started = time.monotonic()
    done = 0

    for rank in GATE_RANKS:
        label, kind, fails_when = ARM[rank]
        try:
            if rank > 0:
                basis.shape(rank, floor)  # raises before any work is spent
        except ValueError as exc:
            out[f"{rank}:unavailable"] = {"reason": str(exc)}
            print(f"    {label} rank {rank}: UNAVAILABLE, {exc}")
            continue

        print(f"    {label}  constructed rank {rank}  ({kind}, fails when it "
              f"{fails_when})")
        for rep in range(reps):
            key = f"{rank}:{rep}"
            if key in out:
                continue
            field_seed, null_seed = arm_seeds(seed, rank, rep)
            v = matched_sample(basis, cells, classes, rank,
                               np.random.default_rng(field_seed), floor=floor)
            est = estimate_rank(
                cells, classes, v, n_cells, n_classes, draws,
                np.random.default_rng(null_seed), stable_order=order, jobs=jobs,
            )
            top_r = max(rank, 1)
            out[key] = {
                "rank": int(est.rank),
                "null_max": float(est.null_max),
                "eigenvalues": [float(x) for x in est.eigenvalues[:4]],
                "achieved_ratio": [
                    float(est.eigenvalues[i] / obs[i]) for i in range(top_r)
                ],
            }
            done += 1
            ckpt_file.write_text(json.dumps(out), encoding="utf-8", newline="\n")
            per = (time.monotonic() - started) / done
            todo = sum(
                1 for rk in GATE_RANKS for rp in range(reps)
                if f"{rk}:{rp}" not in out and f"{rk}:unavailable" not in out
            )
            print(f"      rep {rep + 1:>3}/{reps}  read {est.rank}  "
                  f"null_max {est.null_max:.4g}  "
                  f"lambda {', '.join(f'{x:.4g}' for x in est.eigenvalues[:3])}"
                  f"   [{per:.0f}s/rep, ~{per * todo / 60:.0f} min left]")
    return out


def summarise(out: dict, reps: int, draws: int, obs: np.ndarray) -> tuple[list, dict]:
    nominal = 1.0 / (draws + 1)
    cs: list[Criterion] = []
    arms: dict[str, dict] = {}

    for rank in GATE_RANKS:
        label, kind, fails_when = ARM[rank]
        if f"{rank}:unavailable" in out:
            arms[label] = {"constructed_rank": rank, "kind": kind,
                           "unavailable": out[f"{rank}:unavailable"]["reason"]}
            cs.append(Criterion(
                f"{label}  arm unavailable on this design",
                True,
                f"**{out[f'{rank}:unavailable']['reason']}**.  §3.17: a design "
                "whose observed eigenvalue does not clear its own noise floor has "
                "no observed level for a rank-"
                f"{rank} construction to be set to. Reported, and nothing is "
                "substituted for it",
            ))
            continue

        got = [out[f"{rank}:{r}"] for r in range(reps) if f"{rank}:{r}" in out]
        n = len(got)
        read = [g["rank"] for g in got]
        fail = sum(1 for x in read if (x >= rank + 1 if rank < 2 else x != 2))
        rate = fail / n if n else float("nan")

        ratios = np.array([g["achieved_ratio"] for g in got], dtype=np.float64)
        achieved = {
            f"lambda{i + 1}": {"mean": float(ratios[:, i].mean()),
                               "sd": float(ratios[:, i].std(ddof=1)) if n > 1 else 0.0}
            for i in range(ratios.shape[1])
        }
        cal = "  ".join(
            f"l{i + 1}/obs {v['mean']:.4f} sd {v['sd']:.4f}"
            for i, v in enumerate(achieved.values())
        )

        entry = {
            "constructed_rank": rank, "kind": kind, "n": n,
            "reads": read, "failures": fail, "rate": rate,
            "achieved_level": achieved,
            "null_max_mean": float(np.mean([g["null_max"] for g in got])),
        }

        if kind == "size":
            p = binomial_tail_at_least(fail, n, nominal)
            entry |= {"nominal": nominal, "binomial_tail_at_least": p}
            detail = (
                f"**{fail}/{n} = {rate:.3f}** against a nominal of "
                f"1/(d+1) = {nominal:.4f}.  P(at least {fail} | {n}, {nominal:.4f}) "
                f"= **{p:.4f}**, one-sided: the primary null is inflated by the "
                "class main effect it redistributes, so the nominal is an upper "
                "bound and only a rate **above** it is informative.  "
                f"calibration achieved on this arm: {cal}"
            )
        else:
            lo, hi = wilson_interval(n - fail, n)
            entry |= {"power": (n - fail) / n if n else float("nan"),
                      "wilson_95": [lo, hi]}
            detail = (
                f"**{n - fail}/{n} = {(n - fail) / n:.3f}** of repetitions "
                f"returned the constructed rank, Wilson 95% "
                f"[{lo:.3f}, {hi:.3f}].  No nominal exists for a power arm, so "
                "there is an interval here and no line.  "
                f"calibration achieved on this arm: {cal}"
            )

        arms[label] = entry
        cs.append(Criterion(
            f"{label}  reported, not gated: {kind}, constructed rank {rank}",
            True, detail,
        ))

    n_ran = sum(1 for rank in GATE_RANKS
                if any(f"{rank}:{r}" in out for r in range(reps)))
    n_avail = sum(1 for rank in GATE_RANKS if f"{rank}:unavailable" not in out)
    cs.insert(0, Criterion(
        "B7-0  structural: every available arm completed every repetition",
        all(
            sum(1 for r in range(reps) if f"{rank}:{r}" in out) == reps
            for rank in GATE_RANKS if f"{rank}:unavailable" not in out
        ),
        f"{n_ran} of {n_avail} available arms ran, {reps} repetitions each.  "
        "**This is the only gated criterion in the file.** It is about the code "
        "having finished and not about what it found; VOID 1 removed every "
        "threshold on a result",
    ))
    return cs, arms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--grid", choices=("fine", "coarse", "complement"),
                    default="fine")
    ap.add_argument("--jobs", type=int, default=None,
                    help="threads for the null draws; results are identical at "
                         "any value")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore any checkpoint and recompute every repetition")
    ap.add_argument("--smoke", action="store_true",
                    help="a reduced run: writes to results/subset/ with "
                         "diagnostic_only set, so it cannot displace a full "
                         "record. The renderer's glob is not recursive")
    args = ap.parse_args()

    print("B7 step 4a: the gate. This file does not read the observed field's "
          "rank.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    if args.grid == "coarse":
        classes = coarse_classes(classes, design["class_levels"])
        n_classes = int(classes.max()) + 1
    elif args.grid == "complement":
        classes = complement_classes(classes, design["class_levels"])
        n_classes = int(classes.max()) + 1

    print(f"  grid {args.grid}: {n_cells:,} cells, {n_classes} classes, "
          f"{values.size:,} loans, fill {design['fill']:.4f}")

    basis = calibration_basis(cells, classes, values, n_cells, n_classes)
    obs = np.asarray(basis.eigenvalues)
    floor, per_draw = measure_noise_floor(
        basis, cells, classes, np.random.default_rng(args.seed + 5), FLOOR_DRAWS
    )
    print(f"  observed spectrum {', '.join(f'{v:.4g}' for v in obs[:5])}")
    print(f"  §3.17 noise floor {floor:.6f}  per draw "
          f"{[round(v, 6) for v in per_draw]}")
    print(f"  {len(GATE_RANKS)} arms x {args.reps} repetitions x {args.draws} "
          f"draws, nominal size 1/(d+1) = {1 / (args.draws + 1):.4f}\n")

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_file = ckpt_path(args.grid, args.draws, args.seed)
    ckpt = {} if args.fresh else load_ckpt(ckpt_file)
    if ckpt:
        print(f"  resuming from {ckpt_file.name}: "
              f"{sum(1 for k in ckpt if ':unavailable' not in k)} repetitions "
              "already done\n")

    out = run_arms(cells, classes, values, n_cells, n_classes, basis, floor,
                   args.draws, args.reps, args.seed, args.jobs, ckpt, ckpt_file)

    cs, arms = summarise(out, args.reps, args.draws, obs)
    print()
    for c in cs:
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")
    print(
        "\n  Nothing above is a licence or a refusal. VOID 1 replaced the "
        "gate's\n  pass/fail with three rates, and §3.19 attaches each arm's "
        "achieved\n  calibration to its rate. A reading taken from this design "
        "is quoted\n  with both."
    )

    where = (RESULTS / "subset") if args.smoke else RESULTS
    where.mkdir(parents=True, exist_ok=True)
    out_path = (where / f"b7_gate{'' if args.grid == 'fine' else '_' + args.grid}"
                f"_draws{args.draws}_reps{args.reps}.json")
    out_path.write_text(
        json.dumps(
            {
                "stage": "B7",
                "step": "gate",
                "seed": args.seed,
                "diagnostic_only": bool(args.smoke),
                "draws": args.draws,
                "reps": args.reps,
                "grid": args.grid,
                "jobs": args.jobs,
                "nominal_size": 1.0 / (args.draws + 1),
                "design": design,
                "observed_eigenvalues": [float(v) for v in obs],
                "noise_floor": floor,
                "noise_floor_per_draw": per_draw,
                "arms": arms,
                "repetitions": out,
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
    print(f"  wrote {out_path.relative_to(ROOT)}")
    return 0 if n_pass == len(cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
