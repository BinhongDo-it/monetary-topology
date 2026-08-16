"""B7-12 step one: is the observed rank class-specific dispersion?

Pre-registered in ``docs/b7_interaction_rank.md`` §3.23, **before this file was
written**. Every reading it can return is declared there and the table cuts both
ways.

**No null is drawn, no field is constructed and no rank is estimated.** One pass
over the sample. That is the point: the question can be answered by description,
and a description is worth having before anything expensive is aimed at it.

The question
------------
B7-11's loading table came back with `v1` a near-pure indicator on `>60%`
(`+0.9917`) and `v2` a near-pure indicator on `50%-60%` (`+0.9920`), every other
level between `-0.019` and `-0.038` on both. Those two buckets hold `1.18` and
`1.37` loans per cell-class entry against `2.16` to `10.00` for every other class.

`S(a,a)` is a mean over cells of `gamma(c,a)^2`, `gamma` is built from cell-class
**means**, and a mean of `n` loans carries noise of order `Var(a) / n`. Noise is
independent across entries, so it inflates `S`'s **diagonal** and not its
off-diagonals, and a symmetric matrix with two inflated diagonal entries has
near-indicator eigenvectors on exactly those two coordinates. **The observed
pattern is what that artefact looks like, in the order the thinness predicts.**

Neither null can see it: both assume loans are exchangeable across classes within
a cell, which is precisely what class-specific dispersion violates. The gate
cannot see it either, because ``matched_sample`` draws homoskedastic noise.

What this computes
------------------
Per class, four things and two bounds:

* ``loans_per_entry``, the thinness;
* ``sd_within_cell``, the dispersion of a class-`a` loan about its **cell** mean.
  This still contains the class effect and `gamma`, so the noise it predicts is an
  **upper** bound;
* ``sd_within_entry``, the dispersion about its own **cell-class** mean, over
  entries holding two or more loans. This is the noise proper and gives a
  **lower** bound, and it is estimable for every class because even `>60%` has
  thousands of such entries;
* ``S_diag``, the observed diagonal of `S`.

The predicted noise contribution to `S(a,a)` is ``Var(a) * mean over cells of
1 / n_ca``, which is the exact expectation for an entry mean of `n_ca` draws, with
the two variances giving the two bounds.

Usage::

    python experiments/b7_hetero.py

Writes ``results/b7_hetero.json``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import build_design  # noqa: E402
from monetary_topology.effective_price import MIN_CELL_SIZE  # noqa: E402
from monetary_topology.interaction_rank import (  # noqa: E402
    alternating_centre,
    cell_class_table,
    estimate_rank,
    pairwise_second_moment,
)

RESULTS = ROOT / "results"

#: Draws and seed for §3.26's seventeen-class null. One estimate, so the cost is
#: one pass plus the draws; the rest of this file draws nothing.
DRAWS_17 = 50
SEED_17 = 20260816

#: §3.24 voided §3.23's table. The branch is still computed and printed, because
#: a voided criterion whose output is hidden cannot be checked, and it is labelled
#: so that no reader takes it for a verdict.
VERDICT_NOTE = (
    "**VOIDED by §3.24 and not a verdict.** Its `clear` branch is an exact "
    "inequality with no width against two defective bounds. Read B7-12b instead."
)


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def main() -> int:
    print("B7-12 step one: class-specific dispersion. No null is drawn here.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = design["class_levels"]
    values = np.asarray(values, dtype=np.float64)

    table = cell_class_table(cells, classes, values, n_cells, n_classes)
    gamma = alternating_centre(table).gamma
    s, _cooccur = pairwise_second_moment(gamma, table.present)
    eig = np.linalg.eigvalsh(s)[::-1]

    # cell means, and the deviation of every loan from its own cell's mean
    cell_n = np.bincount(cells, minlength=n_cells).astype(np.float64)
    cell_sum = np.bincount(cells, weights=values, minlength=n_cells)
    cell_mean = cell_sum / np.maximum(cell_n, 1.0)
    dev_cell = values - cell_mean[cells]

    # deviation from the loan's own cell-class mean, which is the noise proper
    dev_entry = values - table.means[cells, classes]
    n_ca = table.counts[cells, classes]

    rows = []
    for a in range(n_classes):
        m = classes == a
        n_loans = int(m.sum())
        present = table.present[:, a]
        counts_a = table.counts[present, a]
        per_entry = float(n_loans / max(present.sum(), 1))
        # E[1/n] over the cells holding a, which is the exact factor a mean of
        # n_ca draws contributes to E[gamma^2].
        inv_n = float(np.mean(1.0 / counts_a)) if counts_a.size else 0.0

        var_cell = float(np.mean(dev_cell[m] ** 2))
        big = m & (n_ca >= 2)
        dof = float(table.present[:, a].sum() - (counts_a < 2).sum())
        var_entry = (float((dev_entry[big] ** 2).sum() / max(big.sum() - dof, 1.0))
                     if big.sum() > dof else float("nan"))

        rows.append({
            "level": lv[a],
            "loans": n_loans,
            "share": n_loans / float(values.size),
            "cells_holding": int(present.sum()),
            "loans_per_entry": per_entry,
            "mean_inverse_n": inv_n,
            "sd_within_cell": float(np.sqrt(var_cell)),
            "sd_within_entry": float(np.sqrt(var_entry)) if var_entry == var_entry
                               else None,
            "S_diag": float(s[a, a]),
            "predicted_upper": var_cell * inv_n,
            "predicted_lower": (var_entry * inv_n) if var_entry == var_entry else None,
        })

    order = sorted(range(n_classes), key=lambda i: rows[i]["loans_per_entry"])
    print(f"  observed spectrum {', '.join(f'{v:.4g}' for v in eig[:4])}\n")
    print(f"    {'level':<12} {'n/entry':>8} {'sd_cell':>8} {'sd_entry':>9} "
          f"{'S(a,a)':>9} {'lower':>9} {'upper':>9}   verdict")
    for i in order:
        r = rows[i]
        lo = r["predicted_lower"]
        up = r["predicted_upper"]
        if lo is None:
            v = "no estimate"
        elif lo >= r["S_diag"]:
            v = "NOISE ALONE ACCOUNTS FOR IT"
        elif up < r["S_diag"]:
            v = "exceeds any dispersion"
        else:
            v = "straddled"
        se = r["sd_within_entry"]
        print(f"    {r['level']:<12} {r['loans_per_entry']:>8.2f} "
              f"{r['sd_within_cell']:>8.4f} "
              f"{(f'{se:.4f}' if se is not None else '  n/a'):>9} "
              f"{r['S_diag']:>9.4f} "
              f"{(f'{lo:.4f}' if lo is not None else 'n/a'):>9} "
              f"{up:>9.4f}   {v}")

    # ---- B7-12b (§3.24): how much of S is off the diagonal --------------
    # Noise between entries is independent, so it lands on the diagonal and
    # nowhere else. A real interaction direction is classes moving together
    # across cells, which is off-diagonal correlation. **This needs no variance
    # estimate, no bound and no selected subsample**, which is why §3.24 voided
    # the bound comparison and put this in its place.
    dg = np.sqrt(np.clip(np.diag(s), 0.0, None))
    denom = np.outer(dg, dg)
    corr = np.divide(s, denom, out=np.zeros_like(s), where=denom > 0)
    off = ~np.eye(n_classes, dtype=bool)
    diag_mass = float(np.abs(np.diag(s)).sum())
    off_mass = float(np.abs(s[off]).sum())
    corr_off = corr[off]
    thin = sorted(range(n_classes),
                  key=lambda i: rows[i]["loans_per_entry"])[:2]
    keep = np.array([i for i in range(n_classes) if i not in thin])
    sub = corr[np.ix_(keep, keep)]
    sub_off = sub[~np.eye(keep.size, dtype=bool)]

    print(f"\n  B7-12b (§3.24): how much of S is off the diagonal\n")
    print(f"    diagonal mass {diag_mass:.4f}   off-diagonal mass {off_mass:.4f}"
          f"   ratio {off_mass / diag_mass:.4f}")
    print(f"    off-diagonal correlations: max |r| {np.abs(corr_off).max():.4f}, "
          f"mean |r| {np.abs(corr_off).mean():.4f}, "
          f"90th pct {np.percentile(np.abs(corr_off), 90):.4f}")
    print(f"    with the two thinnest classes "
          f"({', '.join(rows[i]['level'] for i in thin)}) dropped: "
          f"max |r| {np.abs(sub_off).max():.4f}, "
          f"mean |r| {np.abs(sub_off).mean():.4f}")

    offdiag = {
        "diagonal_mass": diag_mass,
        "off_diagonal_mass": off_mass,
        "off_over_diag": off_mass / diag_mass,
        "max_abs_corr": float(np.abs(corr_off).max()),
        "mean_abs_corr": float(np.abs(corr_off).mean()),
        "p90_abs_corr": float(np.percentile(np.abs(corr_off), 90)),
        "dropped_thinnest": [rows[i]["level"] for i in thin],
        "max_abs_corr_without_thinnest": float(np.abs(sub_off).max()),
        "mean_abs_corr_without_thinnest": float(np.abs(sub_off).mean()),
        "S": [[float(x) for x in r] for r in s],
        "corr": [[float(x) for x in r] for r in corr],
    }

    # ---- B7-14 (§3.26): the seventeen-class design gets its own null -----
    # §3.25 compared the seventeen-class spectrum against the **nineteen**-class
    # design's `null_max`. Those are different designs and a null belongs to the
    # design it was drawn on. Dropping the two thinnest classes removes the two
    # largest noise sources and shrinks the matrix, so the seventeen-class null is
    # expected **below** the nineteen-class one and the comparison §3.25 made was
    # against a threshold that is too high. **This computes the right one.**
    drop = {rows[i]["level"] for i in
            sorted(range(n_classes), key=lambda i: rows[i]["loans_per_entry"])[:2]}
    keep_class = np.array([lv[a] not in drop for a in range(n_classes)])
    m = keep_class[classes]
    c17 = np.unique(cells[m], return_inverse=True)[1]
    big = np.bincount(c17)[c17] >= MIN_CELL_SIZE
    c17 = np.unique(c17[big], return_inverse=True)[1]
    k17 = np.unique(classes[m][big], return_inverse=True)[1]
    v17 = values[m][big]
    n17c, n17k = int(c17.max()) + 1, int(k17.max()) + 1
    est17 = estimate_rank(c17, k17, v17, n17c, n17k, DRAWS_17,
                          np.random.default_rng(SEED_17),
                          stable_order=np.argsort(c17, kind="stable"))
    print(f"\n  B7-14 (§3.26): the design with {', '.join(sorted(drop))} dropped")
    print(f"    {n17c:,} cells, {n17k} classes, {v17.size:,} loans "
          f"(MIN_CELL_SIZE re-applied)")
    print(f"    spectrum {', '.join(f'{x:.4g}' for x in est17.eigenvalues[:5])}")
    print(f"    its own null_max {est17.null_max:.4g} at {DRAWS_17} draws  ->  "
          f"**rank {est17.rank}**")
    # **Record what the direction IS, not only that there is one.** The first
    # version of this block stored the rank and left `leading_class` at None,
    # which is the same omission already on this stage's outstanding list for the
    # complement grid, committed a second time. A rank with no loading behind it
    # cannot be read.
    lv17 = [lv[a] for a in range(n_classes) if lv[a] not in drop]
    v1 = est17.eigenvectors[:, 0]
    v1 = -v1 if v1[np.argmax(np.abs(v1))] < 0 else v1
    v2 = est17.eigenvectors[:, 1]
    v2 = -v2 if v2[np.argmax(np.abs(v2))] < 0 else v2
    print(f"    leading loading, by level")
    for j, name in enumerate(lv17):
        print(f"      {name:<12} v1 {v1[j]:+.4f}   v2 {v2[j]:+.4f}")
    lead17 = lv17[int(np.argmax(np.abs(v1)))]
    seventeen = {
        "dropped": sorted(drop), "n_cells": n17c, "n_classes": n17k,
        "n_loans": int(v17.size), "draws": DRAWS_17,
        "eigenvalues": [float(x) for x in est17.eigenvalues[:6]],
        "null_max": float(est17.null_max), "rank": int(est17.rank),
        "levels": lv17,
        "v1": [float(x) for x in v1], "v2": [float(x) for x in v2],
        "leading_class": lead17,
        "leading_weight": float(np.abs(v1).max()),
    }
    print(f"    leading direction is **{lead17}** at "
          f"{np.abs(v1).max():.4f}")

    # the two classes the loadings pick out
    top = [r for r in rows if r["level"] in (">60%", "50%-60%")]
    settled_low = [r for r in top
                   if r["predicted_lower"] is not None
                   and r["predicted_lower"] >= r["S_diag"]]
    settled_high = [r for r in top if r["predicted_upper"] < r["S_diag"]]

    cs = [
        Criterion(
            "B7-14  reported, not gated: the seventeen-class design against its "
            "own null",
            True,
            f"dropping {', '.join(sorted(drop))} and re-applying MIN_CELL_SIZE "
            f"gives {n17c:,} cells and {v17.size:,} loans; spectrum "
            f"{', '.join(f'{x:.4g}' for x in est17.eigenvalues[:4])} against its "
            f"**own** `null_max` of {est17.null_max:.4g}, **rank "
            f"{est17.rank}**.  §3.25 compared that spectrum to the nineteen-class "
            "design's null, which is a different design's null and is expected to "
            "be too high because the two dropped classes are the two largest "
            "noise sources.  **§3.26 is the correction and this line is the "
            "number it needed**",
        ),
        Criterion(
            "B7-12b  reported, not gated: how much of S is off the diagonal",
            True,
            f"off-diagonal mass / diagonal mass = **{off_mass / diag_mass:.4f}**; "
            f"off-diagonal correlations max |r| = **{np.abs(corr_off).max():.4f}**, "
            f"mean |r| = {np.abs(corr_off).mean():.4f}.  Dropping the two thinnest "
            f"classes ({', '.join(rows[i]['level'] for i in thin)}): max |r| = "
            f"{np.abs(sub_off).max():.4f}, mean |r| = "
            f"{np.abs(sub_off).mean():.4f}.  **Noise lands on the diagonal and "
            "nowhere else**, so a near-diagonal `S` has no interaction for a rank "
            "to count, whatever its eigenvalues are. §3.24 declares the three "
            "readings",
        ),
        Criterion(
            "B7-12a  VOIDED by §3.24, computed and printed only: does class-"
            "specific noise account for "
            "the two leading diagonals",
            True,
            ("; ".join(
                f"**{r['level']}**: {r['loans_per_entry']:.2f} loans per entry, "
                f"S(a,a) = {r['S_diag']:.4f}, noise predicts "
                f"[{r['predicted_lower']:.4f}, {r['predicted_upper']:.4f}]"
                for r in top if r["predicted_lower"] is not None
            ) or "neither `>60%` nor `50%-60%` is present in this sample")
            + ".  **§3.23's table is voided by §3.24 and this line is not a "
            "verdict.** The upper bound is nearly an algebraic identity for a "
            "class at one loan per entry, the lower bound is estimated on the "
            "entries holding two or more and therefore on a different population "
            "from the one it bounds, and the table compared both to `S(a,a)` with "
            "exact inequalities and no width. B7-12b above replaces it",
        ),
        Criterion(
            "B7-12c  structural: the two leading directions are the two thinnest "
            "classes",
            [rows[i]["level"] for i in order[:2]] == [">60%", "50%-60%"]
            or set(rows[i]["level"] for i in order[:2]) == {">60%", "50%-60%"},
            f"thinnest two by loans per entry: "
            f"{', '.join(rows[i]['level'] for i in order[:2])}.  B7-11's `v1` is a "
            "near-pure indicator on `>60%` and `v2` on `50%-60%`.  **This "
            "criterion is about the coincidence and not about its cause**: a "
            "failure here would mean §3.23's premise is wrong and the whole arm "
            "is misdirected",
        ),
    ]
    print()
    for c in cs:
        print(c.line())

    # An empty ``top`` means this sample has neither of the two buckets the
    # loadings picked out, so §3.23's table does not apply and is not forced to.
    if not top or any(r["predicted_lower"] is None for r in top):
        verdict = "not applicable on this sample"
    elif len(settled_low) == len(top):
        verdict = "withdraw"
    elif len(settled_high) == len(top):
        verdict = "clear"
    else:
        verdict = "straddled"
    print(f"\n  §3.23's branch would have said: {verdict}")
    print("  " + VERDICT_NOTE)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_hetero.json"
    out.write_text(
        json.dumps(
            {"stage": "B7", "step": "hetero", "n_cells": n_cells,
             "n_classes": n_classes, "n_loans": int(values.size),
             "observed_eigenvalues": [float(v) for v in eig],
             "verdict": verdict, "verdict_note": VERDICT_NOTE,
             "classes": rows, "off_diagonal": offdiag,
             "seventeen_class": seventeen,
             "criteria": [{"name": c.name, "passed": bool(c.passed),
                           "detail": c.detail} for c in cs]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if all(c.passed for c in cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
