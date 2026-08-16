"""B7-11: what a coarsening can carry, and the interaction it manufactures.

Pre-registered in ``docs/b7_interaction_rank.md`` §3.20, **before this file
existed**. Every reading it can return is declared there.

**No field is constructed and no rank is gated here.** The only randomness is the
two null runs at the end, which exist so the carried eigenvalues have something to
be compared against. Everything else is a deterministic function of the observed
sample.

The question
------------
B7-6 is the arm that put §10.6 in a standoff: the fine grid reads `2` and the
coarse grid reads `1`. Deciding between "the `2` is real and the coarse index
cannot see it" and "the `2` is fragile" was handed to a gate. §3.16 voided that
gate, and repairing it under §3.17 makes the arm vacuous, because the constructed
level would come from the coarse grid's own observed spectrum and that spectrum
already fails to show a second direction. **The arm's answer would be forced by
its construction.**

So the question is asked directly instead. The coarse cell-class mean is the
loan-count-weighted average of the fine ones inside the cell::

    m_coarse(c, b) = sum over a in b of  n_ca * m_fine(c, a) / n_cb

which means a fine class loading arrives at the coarse index as its count-weighted
**bucket means**. A direction whose loading averages to nothing inside every
bucket is destroyed however strong it is. That is a fact about the partition and
the class mix, not about the estimator, and this file measures it.

What it prints
--------------
Per partition (`coarse`, `complement`) and per fine direction `i`:

* `lambda_i`, the fine grid's own eigenvalue;
* `lambda_i -> partition`, the top eigenvalue the coarse index recovers when the
  loans carry **only** that direction, with no additive part and no noise;
* the carry fraction between them;
* whether the carried value clears that partition's own `null_max`.

Plus one row that is not a direction: the fine **class main effect** alone,
coarsened. §3.20 argues it manufactures a coarse interaction wherever the class
mix varies from cell to cell, because its bucket average depends on the cell's
composition. Nothing in this stage had named that.

Usage::

    python experiments/b7_carry.py
    python experiments/b7_carry.py --draws 200 --jobs 16

Writes ``results/b7_carry.json``.
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
    coarse_classes,
    complement_classes,
    describe_partition,
)
from monetary_topology.interaction_rank import (  # noqa: E402
    alternating_centre,
    cell_class_table,
    estimate_rank,
    spectrum,
)

RESULTS = ROOT / "results"

#: Fine directions carried across. §3.21's control compares how many of them
#: clear a partition's null against that partition's own observed rank.
CARRY_DIRECTIONS = (0, 1, 2, 3)


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def component_values(gamma, vec, cells, classes, present):
    """Loan-level values carrying **only** the part of `gamma` that loads on `vec`.

    `gamma_i = (Gamma v_i) v_i^T`, which is the projection of the field onto one
    class direction. Masked by the observed presence pattern, so it lives on the
    same design.

    No additive part and no noise. `gamma`'s directions are orthogonal to the fine
    additive part by construction, so the question is about this piece alone, and
    a noiseless input is what makes the carried eigenvalue a property of the
    partition rather than of a draw.
    """
    score = gamma @ vec
    comp = np.outer(score, vec) * present
    return comp[cells, classes]


def main_effect_values(table, cells, classes):
    """Loan-level values carrying **only** the fine class main effect `A(a)`.

    `A(a)` is a function of the class alone, so on the fine index it is removed
    exactly by the centring. Its coarse image is not, because the bucket average
    `sum over a in b of (n_ca / n_cb) A(a)` depends on the cell through that
    cell's class composition. §3.20 registers this as a confound in every
    comparison between the two grids, and this is the row that measures it.

    Taken count-weighted from the observed cell-class means with the cell effect
    removed, which is the same object the alternating centring subtracts.
    """
    w = table.counts * table.present
    col_w = w.sum(axis=0)
    row_w = w.sum(axis=1)
    m = table.means * table.present
    row_mean = np.divide((w * m).sum(axis=1), row_w,
                         out=np.zeros_like(row_w), where=row_w > 0)
    dev = (m - row_mean[:, None]) * table.present
    a_eff = np.divide((w * dev).sum(axis=0), col_w,
                      out=np.zeros_like(col_w), where=col_w > 0)
    return a_eff[classes], a_eff


def carried(values, cells, coarse_ids, n_cells, n_coarse):
    """Top eigenvalue the coarse index recovers from a loan-level field."""
    eig, _vecs, _cen, _co, _t = spectrum(
        cells, coarse_ids, values, n_cells, n_coarse
    )
    return np.asarray(eig)


def orient(vec: np.ndarray) -> np.ndarray:
    """Sign-fix an eigenvector so its largest component is positive.

    An eigenvector is defined up to sign and nothing here depends on which one is
    chosen. **This is a printing convention and not a result**, stated because a
    loading table that flips sign between runs is unreadable and a reader has no
    way to know the flip was free.
    """
    v = np.asarray(vec, dtype=np.float64)
    return -v if v[np.argmax(np.abs(v))] < 0 else v


def loading_table(vecs, k, labels, title):
    """The top-`k` class loadings against the names of the levels they load on.

    **Description, not identification.** §3.9's fence stands: naming a mechanism
    from the shape of a loading is post-hoc and needs its own forward-registered
    arm with its own criterion. What this prints is what the numbers are, so that
    a reader is not asked to take a rank on trust while the directions it counts
    stay invisible.
    """
    cols = [orient(vecs[:, i]) for i in range(k)]
    print(f"    {title}")
    head = "  ".join(f"v{i + 1:<8}" for i in range(k))
    print(f"      {'level':<26} {head}")
    for j, name in enumerate(labels):
        row = "  ".join(f"{c[j]:+.4f}   " for c in cols)
        print(f"      {name:<26} {row}")
    return {f"v{i + 1}": [float(x) for x in c] for i, c in enumerate(cols)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--jobs", type=int, default=None)
    args = ap.parse_args()

    print("B7-11: what a coarsening can carry. No field is constructed here.\n")
    cells, classes, values, design = build_design()
    n_cells, n_fine = design["n_cells"], design["n_classes"]
    print(f"  fine grid: {n_cells:,} cells, {n_fine} classes, "
          f"{values.size:,} loans\n")

    table = cell_class_table(cells, classes, values, n_cells, n_fine)
    centred = alternating_centre(table)
    fine_eig, fine_vecs, _c, _co, _t = spectrum(
        cells, classes, values, n_cells, n_fine
    )
    fine_eig = np.asarray(fine_eig)
    print(f"  fine spectrum {', '.join(f'{v:.4g}' for v in fine_eig[:5])}")

    a_loans, a_eff = main_effect_values(table, cells, classes)

    print(f"  fine class main effect A(a), range "
          f"[{a_eff.min():.4g}, {a_eff.max():.4g}], sd {a_eff.std():.4g}\n")

    lv = design["class_levels"]
    partitions = {
        "coarse": coarse_classes(classes, lv),
        "complement": complement_classes(classes, lv),
    }

    # **Print what each grouping actually contains.** A partition's name is not
    # its membership, and on 2026-08-16 this stage discovered that the two had
    # been different for every partition it ever built: `class_levels` was stored
    # alphabetically and read positionally, so the "regulator's bucket scheme"
    # grid had `<20%` in the same group as `49`. Nothing about the fill, the
    # group count or any criterion could see it. A printed membership can.
    record_members: dict[str, dict] = {}
    for name, ids in partitions.items():
        groups = describe_partition(classes, ids, lv)
        record_members[name] = {str(g): v for g, v in sorted(groups.items())}
        print(f"  {name} partition membership")
        for g, v in sorted(groups.items()):
            print(f"    group {g}: {', '.join(v)}")
        print()

    record: dict = {
        "n_cells": n_cells,
        "n_fine_classes": n_fine,
        "n_loans": int(values.size),
        "fine_eigenvalues": [float(v) for v in fine_eig],
        "fine_main_effect": [float(v) for v in a_eff],
        "class_levels_in_code_order": list(design["class_levels"]),
        "partition_membership": {},
        "partitions": {},
    }
    cs: list[Criterion] = []

    record["partition_membership"] = record_members
    print("  fine grid class loadings, top two, by level\n")
    record["fine_loadings"] = loading_table(fine_vecs, 2, lv, f"{n_fine} levels")
    print()

    for name, ids in partitions.items():
        n_group = int(ids.max()) + 1
        order = np.argsort(cells, kind="stable")

        obs = estimate_rank(cells, ids, values, n_cells, n_group, args.draws,
                            np.random.default_rng(args.seed + 101),
                            stable_order=order, jobs=args.jobs)
        print(f"  {name} partition: {n_group} groups.  observed rank "
              f"{obs.rank}, null_max {obs.null_max:.4g}, "
              f"spectrum {', '.join(f'{v:.4g}' for v in obs.eigenvalues[:4])}\n")

        labels = [", ".join(record_members[name][str(g)])[:24]
                  for g in range(n_group)]
        print(f"    {name} grid class loadings, top two, by group\n")
        record.setdefault("loadings", {})[name] = loading_table(
            obs.eigenvectors, 2, labels, f"{n_group} groups")
        print()

        rows = []
        for i in CARRY_DIRECTIONS:
            v = component_values(centred.gamma, fine_vecs[:, i], cells, classes,
                                 table.present)
            got = carried(v, cells, ids, n_cells, n_group)
            frac = float(got[0] / fine_eig[i]) if fine_eig[i] > 0 else float("nan")
            clears = bool(got[0] > obs.null_max)
            rows.append({
                "direction": i + 1,
                "fine_lambda": float(fine_eig[i]),
                "carried_lambda": float(got[0]),
                "carried_spectrum": [float(x) for x in got[:3]],
                "carry_fraction": frac,
                "clears_partition_null": clears,
            })
            print(f"    direction {i + 1}: fine {fine_eig[i]:.4g}  ->  carried "
                  f"{got[0]:.4g}   fraction {frac:.4f}   "
                  f"{'clears' if clears else 'BELOW'} null_max "
                  f"{obs.null_max:.4g}")

        got_a = carried(a_loans, cells, ids, n_cells, n_group)
        manufactured = bool(got_a[0] > obs.null_max)
        print(f"    main effect A(a) alone  ->  carried {got_a[0]:.4g}   "
              f"{'ABOVE' if manufactured else 'below'} null_max "
              f"{obs.null_max:.4g}\n")

        record["partitions"][name] = {
            "n_groups": n_group,
            "observed_rank": obs.rank,
            "observed_null_max": obs.null_max,
            "observed_eigenvalues": obs.eigenvalues[:6].tolist(),
            "directions": rows,
            "main_effect_carried": [float(x) for x in got_a[:3]],
            "main_effect_manufactures_interaction": manufactured,
        }

        d1, d2 = rows[0], rows[1]
        n_clear = sum(1 for r in rows if r["clears_partition_null"])
        lead = max(rows, key=lambda r: r["carried_lambda"])
        lead_ratio = float(lead["carried_lambda"] / obs.eigenvalues[0])
        cs.append(Criterion(
            f"B7-11ctrl  {name}: the carry reproduces this partition's own reading",
            n_clear == obs.rank,
            f"**{n_clear} fine directions clear this partition's `null_max` of "
            f"{obs.null_max:.4g}, and the partition's own observed rank is "
            f"{obs.rank}.** The largest carried value is direction "
            f"{lead['direction']} at {lead['carried_lambda']:.4g} against this "
            f"partition's observed `lambda_1` of {obs.eigenvalues[0]:.4g}, a "
            f"ratio of {lead_ratio:.4f}.  §3.21 replaced §3.20's control with "
            "this one: the old one required **direction 1** to carry, on the "
            "ground that both partitions read at least rank one. That is a "
            "quantifier error. Reading rank one means **some** direction carries "
            "and says nothing about which. This control asks the question the "
            "old one meant to ask and has power the old one did not",
        ))
        cs.append(Criterion(
            f"B7-11  reported, not gated: {name} carries direction 2",
            True,
            f"fine `lambda_2` = {d2['fine_lambda']:.4g} arrives as "
            f"**{d2['carried_lambda']:.4g}**, fraction "
            f"**{d2['carry_fraction']:.4f}**, against this partition's own "
            f"`null_max` of {obs.null_max:.4g}: "
            + ("**it clears**, so this index could have shown the fine grid's "
               "second direction" if d2["clears_partition_null"] else
               "**it does not clear**, so this index cannot carry the fine "
               "grid's second direction even if that direction is real")
            + f".  The observed rank on this partition is {obs.rank}.  §3.20's "
            "table says what each combination does to §10.6",
        ))
        cs.append(Criterion(
            f"B7-11m  reported, not gated: {name} manufactures an interaction",
            True,
            f"the fine class main effect alone, coarsened, arrives as "
            f"**{got_a[0]:.4g}** against `null_max` {obs.null_max:.4g}.  "
            + ("**Above it.** A pure fine main effect has no cell dependence, but "
               "its bucket average depends on each cell's class composition, so "
               "this partition's `gamma` carries a component the fine grid's does "
               "not and that no coarsening can avoid. Every comparison between "
               "the two grids in §10.5 has this confound"
               if manufactured else
               "**Below it.** The coarsening manufactures nothing this index can "
               "see, and §10.5's comparison is clean on this point"),
        ))

    for c in cs:
        print()
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_carry.json"
    out.write_text(
        json.dumps(
            {"stage": "B7", "step": "carry", "seed": args.seed,
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
