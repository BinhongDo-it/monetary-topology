"""B7 step 4c-a: the design census. What B7-7 and B7-8 would be reading.

Pre-registered in ``docs/b7_interaction_rank.md`` §6 (B7-7, B7-8) and §3.13,
which splits both into a cheap census and an expensive estimation and says why.

**This file computes no rank and imports no estimator**, the same device as
``b7_design.py``. It exists because of a problem the criteria did not anticipate.

The problem
-----------
B7-7 sweeps the spread band and adds a rank-transformed arm; B7-8 splits the
sample by year parity. **Every one of those is a different design.** A different
band keeps a different set of loans, so a different set of cells clears
``MIN_CELL_SIZE``, so the fill and the co-occurrence counts move. The rank
transform is more extreme still: ``effective_price.rank_decomposition`` is
deliberately computed with **no band at all**, so its sample is the raw one.

`MEASUREMENT.md` failure mode 10 and its rule, written into this repository on
2026-08-15 out of B7's own B7-6, is that **every design a number is read from
needs its own calibration**. Nine arms would mean nine gates and several hours.

So the arms are counted before they are gated
---------------------------------------------
The registered `±20` band excludes **115 rows out of 20,071,900**. If the other
bands move the design by a comparable amount, they are the same design and one
gate covers them; if they move it materially, each needs its own. **That is a
question with an answer in the data, and this file gets the answer for the price
of one read of the files.**

The decisive statistic is not the loan count. It is the **symmetric difference of
the surviving cell sets** against the registered design: how many cells are in one
and not the other. Two designs holding the same cells with the same classes are
the same design whatever their loan counts do at the third decimal.

Usage::

    python experiments/b7_robustness.py

Writes ``results/b7_robustness_census.json``. Reads through ``b7_design.load_cached``,
so the twenty-minute parse is paid once across the whole stage and this run costs
seconds of loading plus the arms themselves.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import design_from_loaded, load_cached  # noqa: E402
from monetary_topology.effective_price import (  # noqa: E402
    BOUND_SWEEP,
    SPREAD_BOUND,
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


def census(loaded, cell_ids) -> dict[str, dict]:
    """One design per registered arm, described but not estimated."""
    arms: dict[str, dict] = {}

    def add(label: str, **kw) -> None:
        _c, _k, _v, years, design = design_from_loaded(loaded, cell_ids=cell_ids, **kw)
        design["years"] = years
        arms[label] = design
        print(
            f"    {label:22s} loans {design['n_after_filters']:>10,}  "
            f"cells {design['n_cells']:>7,}  classes {design['n_classes']:>3}  "
            f"fill {design['fill']:.4f}"
        )

    print("  spread-band sweep (B7-7)")
    for bound in BOUND_SWEEP:
        add(f"band_{bound:g}", bound=bound)

    print("  rank transform, unbanded (B7-7)")
    add("rank_unbanded", bound=None, rank_transform=True)

    print("  year split (B7-8)")
    ref_years = arms[f"band_{SPREAD_BOUND:g}"]["years"]
    arms["odd_years"] = {"parity": "odd"}
    arms["even_years"] = {"parity": "even"}
    for label, want in (("odd_years", 1), ("even_years", 0)):
        mask = (ref_years.astype(np.int64) % 2) == want
        keys = arms[f"band_{SPREAD_BOUND:g}"]["cell_keys"][mask]
        uniq = np.unique(keys)
        arms[label] |= {
            "n_after_filters": int(mask.sum()),
            "n_cells_before_size_filter": int(uniq.size),
            "note": "activity_year is a cell key, so every cell lies wholly in "
            "one parity: the split partitions the cells and halves none of "
            "them. No cell needs re-filtering for size.",
        }
        print(
            f"    {label:22s} loans {int(mask.sum()):>10,}  "
            f"cells {uniq.size:>7,}  (before re-applying MIN_CELL_SIZE)"
        )
    return arms


def main() -> int:
    print("B7 step 4c-a: the design census. No rank is computed in this file.\n")
    loaded, cell_ids = load_cached()
    arms = census(loaded, cell_ids)

    ref_label = f"band_{SPREAD_BOUND:g}"
    ref = set(np.unique(arms[ref_label]["cell_keys"]).tolist())

    rows, identical = [], []
    for label, d in arms.items():
        if "cell_keys" not in d:
            continue
        here = set(np.unique(d["cell_keys"]).tolist())
        only_here, only_ref = len(here - ref), len(ref - here)
        same = only_here == 0 and only_ref == 0 and d["n_classes"] == arms[ref_label]["n_classes"]
        identical.append(same)
        rows.append(
            {
                "arm": label,
                "n_after_filters": d["n_after_filters"],
                "n_cells": d["n_cells"],
                "n_classes": d["n_classes"],
                "fill": d["fill"],
                "cells_only_in_this_arm": only_here,
                "cells_only_in_reference": only_ref,
                "identical_design_to_reference": bool(same),
            }
        )

    print("\n  cell-set symmetric difference against the registered "
          f"{ref_label} design\n")
    for r in rows:
        mark = "SAME" if r["identical_design_to_reference"] else "DIFF"
        print(
            f"    [{mark}] {r['arm']:22s} +{r['cells_only_in_this_arm']:>6,} "
            f"/ -{r['cells_only_in_reference']:>6,} cells   fill {r['fill']:.4f}"
        )

    n_diff = sum(1 for r in rows if not r["identical_design_to_reference"])
    cs = [
        Criterion(
            "B7-7c  the census is complete and self-describing",
            len(rows) == len(BOUND_SWEEP) + 1,
            f"{len(rows)} banded arms described against the {ref_label} "
            "reference; the year split is described separately because it "
            "partitions rather than re-filters",
        ),
        Criterion(
            "B7-7d  reported, not gated: how many arms are new designs",
            True,
            f"**{n_diff} of {len(rows)} arms differ from the registered design "
            f"by at least one cell.** Each of those needs its own gate before "
            "its rank may be read (`MEASUREMENT.md` failure mode 10). Arms marked "
            "SAME are the registered design and are already gated",
        ),
    ]
    print()
    for c in cs:
        print(c.line())

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_robustness_census.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B7",
                "step": "robustness_census",
                "reference": ref_label,
                "arms": rows,
                "year_split": {
                    k: {kk: vv for kk, vv in arms[k].items() if kk != "cell_keys"}
                    for k in ("odd_years", "even_years")
                },
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
    print(f"\n  wrote {out.relative_to(ROOT)}")
    print(
        "\n  Next: §3.13 step b gates only the arms marked DIFF, then estimates.\n"
        "  If every arm is SAME, one gate already covers the sweep and step b is\n"
        "  the estimation alone."
    )
    return 0 if all(c.passed for c in cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
