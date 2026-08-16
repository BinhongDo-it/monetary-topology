"""B7-13: does a field with **no interaction** and realistic noise read back two?

Pre-registered in ``docs/b7_interaction_rank.md`` §3.25, before this file was
written. It confirms the mechanism behind B7-4's withdrawal. **It does not license
the withdrawal**, which fired on §3.24's declared table when B7-12b returned.

The question
------------
Every gate this stage ran drew its constructed noise **homoskedastically**, one
standard deviation for every loan (`matched_sample` at ``noise_sd=None``). §3.16
named that approximation and left it in place. §3.25 showed it was the
approximation that decided the stage: `S` is a diagonal matrix of class noise
levels, its two eigenvalues above the null are the diagonal entries of the two
classes holding `1.18` and `1.37` loans per cell-class entry, and its largest
off-diagonal correlation over all `171` pairs is `0.1417`.

So the rank-zero arm is run again with **class-specific** noise: each constructed
loan drawn at its own class's dispersion. If a field with no interaction at all
reproduces `1.4674` and `0.7544` with indicator loadings on those two classes,
the observed spectrum is that and nothing else.

Two dispersions, and why both
-----------------------------
``class_dispersions`` returns the within-entry figure, which is the noise proper
but is estimated on the entries holding two or more loans of that class and so on
a **selected** minority of cells for a thin class; and the within-cell figure,
which has no selection but still contains the class main effect and `gamma`. They
bracket the truth.

**§3.24 voided comparing those two to `S(a,a)` algebraically**, because for a class
at one loan per entry the upper one is nearly an identity with it. Here they are
not compared to anything: **they are the noise level of a constructed field, and
what they bracket is an outcome the full estimator and its null produce.**

Usage::

    python experiments/b7_class_noise.py --jobs 16
    python experiments/b7_class_noise.py --draws 5 --reps 2 --smoke

Writes ``results/b7_class_noise_draws<N>_reps<M>.json``. Checkpointed per
repetition under ``data/processed/``.
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

from b7_design import build_design  # noqa: E402
from b7_gate import FLOOR_DRAWS, ckpt_path, load_ckpt  # noqa: E402
from monetary_topology.effective_price import MIN_CELL_SIZE  # noqa: E402
from monetary_topology.interaction_rank import (  # noqa: E402
    calibration_basis,
    cell_class_table,
    class_dispersions,
    estimate_rank,
    matched_sample,
    measure_noise_floor,
    wilson_interval,
)

RESULTS = ROOT / "results"

#: The two dispersions §3.25 registers, and which bracket each is.
ARMS = (("within_entry", "lower"), ("within_cell", "upper"))


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--drop-thinnest", type=int, default=0, dest="drop_thinnest",
                    help="drop the N classes with the fewest loans per cell-class "
                         "entry, renumber and re-apply MIN_CELL_SIZE, then run the "
                         "arm on what is left. §3.27's B7-15 is this at N=2, on "
                         "the design B7-14 reads a residual rank 1 from")
    args = ap.parse_args()

    print("B7-13: a field with no interaction, at each class's own noise level.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = list(design["class_levels"])

    if args.drop_thinnest > 0:
        # Loans per cell-class entry, and drop the thinnest N classes. The design
        # is rebuilt rather than sliced: cells are renumbered and MIN_CELL_SIZE is
        # re-applied, so what comes out is a design and not a submatrix.
        t0 = cell_class_table(cells, classes, values, n_cells, n_classes)
        per = np.array([np.bincount(classes, minlength=n_classes)[a]
                        / max(t0.present[:, a].sum(), 1)
                        for a in range(n_classes)])
        drop = {lv[a] for a in np.argsort(per)[:args.drop_thinnest]}
        print(f"  dropping the {args.drop_thinnest} thinnest classes: "
              f"{', '.join(sorted(drop))}")
        m = np.array([lv[a] not in drop for a in range(n_classes)])[classes]
        cc = np.unique(cells[m], return_inverse=True)[1]
        big = np.bincount(cc)[cc] >= MIN_CELL_SIZE
        cells = np.unique(cc[big], return_inverse=True)[1]
        classes = np.unique(classes[m][big], return_inverse=True)[1]
        values = values[m][big]
        lv = [x for x in lv if x not in drop]
        n_cells, n_classes = int(cells.max()) + 1, int(classes.max()) + 1
        print(f"  rebuilt: {n_cells:,} cells, {n_classes} classes, "
              f"{values.size:,} loans\n")

    order = np.argsort(cells, kind="stable")

    basis = calibration_basis(cells, classes, values, n_cells, n_classes)
    obs = np.asarray(basis.eigenvalues)
    floor, _per = measure_noise_floor(
        basis, cells, classes, np.random.default_rng(args.seed + 5), FLOOR_DRAWS)
    entry_sd, cell_sd = class_dispersions(cells, classes, values, n_cells, n_classes)

    print(f"  design: {n_cells:,} cells, {n_classes} classes, {values.size:,} loans")
    print(f"  observed spectrum {', '.join(f'{v:.4g}' for v in obs[:4])}")
    print(f"  pooled within-entry sd {basis.sd:.4f}, §3.17 floor {floor:.6f}\n")
    print(f"    {'level':<12} {'within_entry':>13} {'within_cell':>12}")
    for a in range(n_classes):
        print(f"    {lv[a]:<12} {entry_sd[a]:>13.4f} {cell_sd[a]:>12.4f}")
    print()

    record: dict = {"arms": {}}
    cs: list[Criterion] = []
    started = time.monotonic()

    for name, bracket in ARMS:
        sd = entry_sd if name == "within_entry" else cell_sd
        tag = (f"classnoise_{name}" if not args.drop_thinnest
               else f"classnoise_{name}_drop{args.drop_thinnest}")
        ckpt_file = ckpt_path(tag, args.draws, args.seed)
        out = {} if args.fresh else load_ckpt(ckpt_file)
        print(f"  {name} ({bracket} bracket), constructed rank 0, "
              f"{args.reps} repetitions at {args.draws} draws")
        if out:
            print(f"    resuming: {len(out)} done")
        for rep in range(args.reps):
            key = str(rep)
            if key in out:
                continue
            base = args.seed + 7_000_000 + 1_000 * rep + (0 if bracket == "lower"
                                                          else 500)
            v = matched_sample(basis, cells, classes, 0,
                               np.random.default_rng(base), noise_sd=sd)
            est = estimate_rank(cells, classes, v, n_cells, n_classes, args.draws,
                                np.random.default_rng(base + 999_999),
                                stable_order=order, jobs=args.jobs)
            lead = int(np.argmax(np.abs(est.eigenvectors[:, 0])))
            second = int(np.argmax(np.abs(est.eigenvectors[:, 1])))
            out[key] = {
                "rank": int(est.rank),
                "null_max": float(est.null_max),
                "eigenvalues": [float(x) for x in est.eigenvalues[:4]],
                "leading_class": lv[lead],
                "leading_weight": float(abs(est.eigenvectors[lead, 0])),
                "second_class": lv[second],
                "second_weight": float(abs(est.eigenvectors[second, 1])),
            }
            ckpt_file.write_text(json.dumps(out), encoding="utf-8", newline="\n")
            per = (time.monotonic() - started)
            print(f"    rep {rep + 1:>3}/{args.reps}  read {est.rank}  "
                  f"lambda {', '.join(f'{x:.4g}' for x in est.eigenvalues[:2])}  "
                  f"null {est.null_max:.4g}  lead {lv[lead]} "
                  f"({abs(est.eigenvectors[lead, 0]):.3f})  [{per / 60:.0f} min]")

        got = [out[str(r)] for r in range(args.reps) if str(r) in out]
        ranks = [g["rank"] for g in got]
        lam = np.array([g["eigenvalues"][:2] for g in got], dtype=np.float64)
        n_ge1 = sum(1 for r in ranks if r >= 1)
        n_eq2 = sum(1 for r in ranks if r == 2)
        leads = [g["leading_class"] for g in got]
        seconds = [g["second_class"] for g in got]
        record["arms"][name] = {
            "bracket": bracket, "n": len(got), "reads": ranks,
            "reads_at_least_one": n_ge1, "reads_exactly_two": n_eq2,
            "lambda1_mean": float(lam[:, 0].mean()),
            "lambda1_sd": float(lam[:, 0].std(ddof=1)) if len(got) > 1 else 0.0,
            "lambda2_mean": float(lam[:, 1].mean()),
            "lambda2_sd": float(lam[:, 1].std(ddof=1)) if len(got) > 1 else 0.0,
            "lambda1_over_observed": float(lam[:, 0].mean() / obs[0]),
            "lambda2_over_observed": float(lam[:, 1].mean() / obs[1]),
            "leading_classes": leads, "second_classes": seconds,
            "class_sd": [float(x) for x in sd],
            "repetitions": out,
        }
        lo, hi = wilson_interval(n_ge1, len(got))
        top_lead = max(set(leads), key=leads.count) if leads else "n/a"
        print(f"    -> reads >= 1 in {n_ge1}/{len(got)}, Wilson [{lo:.2f},{hi:.2f}]; "
              f"exactly 2 in {n_eq2}/{len(got)}")
        print(f"    -> lambda1 {lam[:, 0].mean():.4f} +- {lam[:, 0].std(ddof=1):.4f} "
              f"against observed {obs[0]:.4f} "
              f"({lam[:, 0].mean() / obs[0]:.3f}x); "
              f"lambda2 {lam[:, 1].mean():.4f} against {obs[1]:.4f} "
              f"({lam[:, 1].mean() / obs[1]:.3f}x)")
        print(f"    -> leading direction is {top_lead} in "
              f"{leads.count(top_lead)}/{len(leads)} repetitions\n")

        cs.append(Criterion(
            f"B7-13 {name}  reported, not gated: no interaction, "
            f"{bracket} bracket",
            True,
            f"a field with **zero interaction** at each class's {name} dispersion "
            f"reads back `>= 1` in **{n_ge1}/{len(got)}** repetitions and exactly "
            f"`2` in **{n_eq2}/{len(got)}**.  Recovered `lambda_1` = "
            f"{lam[:, 0].mean():.4f} +- {lam[:, 0].std(ddof=1):.4f} against the "
            f"observed {obs[0]:.4f}, `lambda_2` = {lam[:, 1].mean():.4f} against "
            f"{obs[1]:.4f}.  Leading direction is **{top_lead}** in "
            f"{leads.count(top_lead)}/{len(leads)}.  §3.25: reading back `2` here "
            "confirms the mechanism behind B7-4's withdrawal; reading back `0` "
            "leaves the withdrawal standing on §3.24's table and the explanation "
            "unknown",
        ))

    for c in cs:
        print(c.line())
    print("\n  B7-4 is withdrawn either way. This arm explains; it does not "
          "license.")

    where = (RESULTS / "subset") if args.smoke else RESULTS
    where.mkdir(parents=True, exist_ok=True)
    suffix = "" if not args.drop_thinnest else f"_drop{args.drop_thinnest}"
    out_path = (where /
                f"b7_class_noise{suffix}_draws{args.draws}_reps{args.reps}.json")
    out_path.write_text(
        json.dumps(
            {"stage": "B7", "step": "class_noise", "seed": args.seed,
             "draws": args.draws, "reps": args.reps, "jobs": args.jobs,
             "diagnostic_only": bool(args.smoke),
             "class_levels": list(lv), "drop_thinnest": args.drop_thinnest,
             "observed_eigenvalues": [float(v) for v in obs],
             "pooled_within_entry_sd": basis.sd,
             "within_entry_sd": [float(x) for x in entry_sd],
             "within_cell_sd": [float(x) for x in cell_sd],
             **record,
             "criteria": [{"name": c.name, "passed": bool(c.passed),
                           "detail": c.detail} for c in cs]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
