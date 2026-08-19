"""B7-17: does a thin class's `gamma` persist into the next year's same tract?

Registered in the project's document set as B7's results file, section 3.4, with all
three readings written down there **before this file existed**. This file adds no
criterion of its own.

**Not run in this repository.** It is here so that the arm is reproducible rather
than only described, and because the reason it was never run turned out to be
wrong: `docs/b7_interaction_rank.md` section 10.9 records that `build_design` does
not return `activity_year`, and since the 2026-08-16 extraction
`design_from_loaded` returns both the years and the surviving cell keys. The real
cost is stated in "What this costs" below, and it is a parse, not a blocker.

The question
------------
Section 11 leaves one reading with no candidate explanation attached: part of the
leading direction is neither the class main effect nor its slope and is still
ordered in DTI. Separately, section 11.6's `Stilde(a,a)` says how much
cell-varying signal a class has, but not whether that signal is **the same signal
from one year to the next**.

`gamma(c,a)` for a thin class is, in many cells, one loan's residual. **If it is
noise, the same tract's next year is independent of it. If it is a real, locally
persistent condition, the two are correlated**, because a tract persists and a
mortgage market persists.

    r(a) = corr( gamma(c,a), gamma(c',a) )  over cells c, c' that share every
           cell key except `activity_year`, with c' one year later

**No cross-fold is needed here and that is worth saying.** `c` and `c'` hold
disjoint loans by construction, so their sampling noise is already independent and
cannot inflate this correlation the way it inflated `S`'s diagonal. The thing that
made section 11 necessary does not arise.

The three readings, from the registration, not restated as thresholds
--------------------------------------------------------------------
* the two thin classes' `r` indistinguishable from zero while the thick classes'
  are clearly positive: **the diagonal was noise**, the withdrawal is complete;
* the two thin classes' `r` clearly positive: **the diagonal holds a real,
  cell-varying component** that `S` could not separate. This restores no rank,
  since rank counts shared directions, and it is a new per-class positive reading
  that needs its own station;
* every class's `r` indistinguishable from zero: this design has no cross-cell
  persistence at all, which is itself information about stage B2's within-share
  reading, and is reported.

What this costs
---------------
**A full parse, about twenty minutes.** `data/processed/b7_parse_cache.npz` stores
`cell_codes` and `years` and **not** the seven key columns, so the geography alone
cannot be recovered from it: `make_cell_ids` folds the columns into one integer
code and the fold is not invertible. Rather than bump the cache version and force
a re-parse on every other script in the stage, this reads the sample itself and
touches nothing that already works.

Usage::

    python experiments/b7_persistence.py

Writes ``results/b7_persistence.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import design_from_loaded, describe_partition, load_with_class  # noqa: E402
from monetary_topology.effective_price import CELL_KEYS, make_cell_ids  # noqa: E402
from monetary_topology.interaction_rank import (  # noqa: E402
    alternating_centre,
    cell_class_table,
)

RESULTS = ROOT / "results"


def geography_codes(cols) -> np.ndarray:
    """The cell key with the year taken out, as codes.

    `CELL_KEYS[0]` is `activity_year`; the rest are the tract and the loan's
    fixed characteristics. Two cells sharing this and differing by one year are
    the same position observed twice, which is the pairing the arm needs.
    """
    return make_cell_ids({k: cols[k] for k in CELL_KEYS[1:]})


def pairwise_persistence(gamma, present, cell_geo, cell_year, lag=1):
    """Per class, the correlation of `gamma` with the same geography `lag` later."""
    order = np.lexsort((cell_year, cell_geo))
    geo, yr = cell_geo[order], cell_year[order]
    same = (geo[1:] == geo[:-1]) & (yr[1:] == yr[:-1] + lag)
    left, right = order[:-1][same], order[1:][same]
    out = []
    for a in range(gamma.shape[1]):
        ok = present[left, a] & present[right, a]
        x, y = gamma[left[ok], a], gamma[right[ok], a]
        n = int(ok.sum())
        if n < 3:
            out.append({"class_code": a, "pairs": n, "r": None, "se": None})
            continue
        x = x - x.mean()
        y = y - y.mean()
        den = float(np.sqrt((x * x).sum() * (y * y).sum()))
        r = float((x * y).sum() / den) if den > 0 else float("nan")
        # Fisher's standard error, reported so the correlation is read against
        # its own precision rather than against a line drawn here.
        out.append({"class_code": a, "pairs": n, "r": r,
                    "se": float(1.0 / np.sqrt(n - 3)) if n > 3 else None})
    return out, int(same.sum())


def main() -> int:
    print("B7-17: cross-cell persistence. One pass, no null is drawn.\n")
    spreads, cols, class_codes, meta = load_with_class()
    geo_all = geography_codes(cols)
    keys = make_cell_ids(cols)
    cells, classes, values, years, design = design_from_loaded(
        (spreads, cols, class_codes, meta), cell_ids=keys
    )
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = design["class_levels"]
    print("  class codes and their level names (section 3.21 guard):")
    for code, names in sorted(describe_partition(classes, classes, lv).items()):
        print(f"    {code:>3}  {names}")

    # `design_from_loaded` drops rows (the plausibility bound, then MIN_CELL_SIZE),
    # so the unfiltered geography array does not line up with `cells`. **Do not
    # re-apply the filters here**: a second copy of a filter is the drift this
    # repository has paid for before. Use what the design already carries.
    # `design["cell_keys"]` is the **original** key code of each surviving loan,
    # so a key-code to geography-code table built on the unfiltered arrays maps
    # straight onto it. Geography is constant within a key, so writing the table
    # by assignment is well defined whichever loan lands last.
    geo_of_key = np.zeros(int(keys.max()) + 1, dtype=np.int64)
    geo_of_key[keys] = geo_all
    geo_kept = geo_of_key[np.asarray(design["cell_keys"])]
    if geo_kept.size != cells.size:
        raise SystemExit(
            f"geography has {geo_kept.size} rows and the design has {cells.size}. "
            "design['cell_keys'] is supposed to be per surviving loan; if that "
            "changed, this arm must be rebuilt rather than patched."
        )

    # A cell's geography and year are constant within it by construction. The
    # first loan of each cell carries both, and both invariants are checked
    # rather than assumed, because a cell that straddles two years would make
    # every pairing below meaningless without changing any array's shape.
    first = np.zeros(n_cells, dtype=np.int64)
    first[cells[::-1]] = np.arange(cells.size)[::-1]
    cell_geo, cell_year = geo_kept[first], years[first]
    if not (np.all(cell_geo[cells] == geo_kept) and np.all(cell_year[cells] == years)):
        raise SystemExit(
            "a cell holds more than one geography or more than one year, so the "
            "cell key is not what this arm assumes. Nothing below is readable."
        )

    table = cell_class_table(cells, classes, np.asarray(values, dtype=np.float64),
                             n_cells, n_classes)
    gamma = alternating_centre(table).gamma
    rows, n_pairs = pairwise_persistence(gamma, table.present, cell_geo, cell_year)

    depth = table.counts.sum(axis=0) / np.maximum(table.present.sum(axis=0), 1)
    for r in rows:
        r["level"] = lv[r["class_code"]]
        r["loans_per_entry"] = float(depth[r["class_code"]])
    rows.sort(key=lambda r: r["loans_per_entry"])

    print(f"\n  {n_pairs:,} adjacent-year cell pairs sharing every other key\n")
    print(f"    {'level':<12} {'n/entry':>8} {'pairs':>9} {'r':>9} {'se':>8}")
    for r in rows:
        rr = "  n/a" if r["r"] is None else f"{r['r']:+.4f}"
        se = "  n/a" if r["se"] is None else f"{r['se']:.4f}"
        print(f"    {r['level']:<12} {r['loans_per_entry']:>8.2f} "
              f"{r['pairs']:>9,} {rr:>9} {se:>8}")
    print("\n  Readings are the three in the registration. **No threshold is "
          "applied here**;\n  the correlation and its standard error are printed "
          "and read there.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_persistence.json"
    out.write_text(json.dumps(
        {"stage": "B7", "step": "persistence", "n_cells": n_cells,
         "n_classes": n_classes, "n_loans": int(np.asarray(values).size),
         "adjacent_year_cell_pairs": n_pairs, "lag": 1,
         "classes": rows}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
