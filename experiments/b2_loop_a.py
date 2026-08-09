"""B2 loop A: does dispersion in financing terms survive fixing position and date?

Pre-registered in ``docs/b2_measurement.md``. Run ``data/fetch_hmda.py`` first.

Usage::

    python experiments/b2_loop_a.py
    python experiments/b2_loop_a.py --min-cell-size 30

Writes ``figures/b2_fig11_*.png`` and ``results/b2_loop_a.json``. Exits non-zero
if a criterion fails, and separately reports which pre-registered falsification
conditions fired.

The null is integrability. If the effective-cost field were the gradient of a
scalar on positions, then within a cell -- same tract, same quarter, same lien,
same purpose, same occupancy, same product, same dwelling category -- every
borrower would face identical terms and the within-cell variance would be zero.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology.effective_price import (
    CELL_KEYS,
    MIN_CELL_SIZE,
    SPREAD_BOUND,
    run_loop_a,
)
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "hmda"
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

OCCUPANCY_LABEL = {
    "1": "principal residence",
    "2": "second residence",
    "3": "investment",
}


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


#: Filenames the loader will accept: ``hmda_<two-letter state>_<year>.csv``.
#:
#: This exists because an earlier session left a synthetic fixture in the data
#: directory and the advice given for removing it was a recursive delete of the
#: whole directory, which destroyed a completed download. A loader that recognises
#: what belongs to the sample needs no manual deletion at all, so the dangerous
#: instruction never has to be given again.
VALID_NAME = re.compile(r"^hmda_[A-Z]{2}_(20\d\d)\.csv$")
VALID_YEARS = range(2018, 2031)


def load() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Read every retrieved CSV into one sample.

    Files whose names do not match the retrieval convention are skipped and
    reported rather than silently included, so a stray file cannot enter the
    sample and no manual cleanup is required to keep it out.

    Nothing else is filtered here. All exclusions happened in the fetch step and
    are recorded in its manifest, so the sample cannot be narrowed after results
    are visible.
    """
    if not RAW.exists():
        raise SystemExit(
            f"no data directory at {RAW.relative_to(ROOT)}.\n"
            "Run:  python data/fetch_hmda.py\n"
            "It needs network access and is resumable, so an interrupted run can "
            "be continued rather than restarted."
        )

    files, skipped = [], []
    for path in sorted(RAW.glob("*.csv")):
        match = VALID_NAME.match(path.name)
        if match and int(match.group(1)) in VALID_YEARS:
            files.append(path)
        else:
            skipped.append(path.name)

    if skipped:
        print(
            f"  skipped {len(skipped)} file(s) not matching the retrieval "
            f"convention: {', '.join(skipped[:5])}"
            + (" ..." if len(skipped) > 5 else "")
        )
    if not files:
        raise SystemExit(
            f"no usable data in {RAW.relative_to(ROOT)}.\n"
            "Run:  python data/fetch_hmda.py"
        )

    spreads: list[float] = []
    cols: dict[str, list[str]] = {k: [] for k in CELL_KEYS}
    for path in files:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                # Retrieved files end with a ``# complete`` marker line. It parses
                # as a short row, so ``rate_spread`` comes back as None rather than
                # raising, and float(None) is a TypeError that the original except
                # clause did not name. Skipped explicitly here and the exception
                # widened, because a marker whose only effect is to crash the
                # loader is worse than no marker.
                if row.get("activity_year", "").startswith("#"):
                    continue
                try:
                    spreads.append(float(row["rate_spread"]))
                except (KeyError, TypeError, ValueError):
                    continue
                for key in CELL_KEYS:
                    cols[key].append(row.get(key, ""))

    print(f"  loaded {len(files)} files, {len(spreads):,} loans")
    return np.array(spreads), {k: np.array(v) for k, v in cols.items()}


def figure_11(result, tag: str = "") -> Path:
    disp = result.dispersion
    fig, (ax_hist, ax_bar) = plt.subplots(1, 2, figsize=(10.6, 4.4))

    ax_hist.hist(disp.iqr, bins=60, color=COLOR_LAYER2, edgecolor="none")
    ax_hist.axvline(0.0, color=COLOR_LAYER1, linewidth=1.6, linestyle="--")
    ax_hist.set_xlabel("within-cell interquartile range of rate spread, points")
    ax_hist.set_ylabel("cells")
    ax_hist.set_title("What integrability predicts is the dashed line")
    annotate(
        ax_hist,
        "Each cell holds tract, quarter, lien, purpose, occupancy, product and\n"
        "dwelling category fixed. A scalar on positions predicts every cell at\n"
        f"zero. Median observed: {np.median(disp.iqr):.3f} points.",
        loc="upper right",
    )

    shares = {"all": result.split.within_share}
    shares.update(
        {
            OCCUPANCY_LABEL.get(k, k): v.within_share
            for k, v in sorted(result.by_occupancy.items())
        }
    )
    names = list(shares)
    vals = [shares[n] for n in names]
    colours = [COLOR_LAYER1] + [COLOR_ACCENT] * (len(names) - 1)
    ax_bar.barh(names, vals, color=colours)
    ax_bar.set_xlim(0, 1)
    ax_bar.axvline(0.0, color=COLOR_INSTRUMENT, linewidth=1.2, linestyle="--")
    ax_bar.set_xlabel("share of rate-spread variance surviving the cell fixed effect")
    ax_bar.set_title("The part no scalar on positions can account for")
    for i, v in enumerate(vals):
        ax_bar.text(v + 0.015, i, f"{v:.3f}", va="center", fontsize=9)
    annotate(
        ax_bar,
        "Computed separately by occupancy type, because asset tier is not agent\n"
        "class: a landlord holding a low-tier unit is not a low-tier agent.",
        loc="lower right",
    )

    fig.suptitle(
        "Position and date held fixed. What is left varies by who is transacting.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, FIGURES / f"b2_fig11_within_cell_dispersion{tag}.png")


def evaluate(result, min_size: int) -> list[Criterion]:
    split = result.split
    disp = result.dispersion
    out = [
        Criterion(
            "B2A-1  variance decomposition is exact",
            abs(split.total - (split.between + split.within)) < 1e-12,
            f"between {split.between:.6f} + within {split.within:.6f} "
            f"= {split.total:.6f}",
        ),
        Criterion(
            "B2A-2  dispersion survives fixing position and date",
            split.within_share > 0.01,
            f"within share {split.within_share:.4f} over {split.n_cells:,} cells "
            f"and {split.n_loans:,} loans. Integrability predicts exactly zero",
        ),
        Criterion(
            "B2A-3  the median cell has a non-trivial spread",
            float(np.median(disp.iqr)) > 0.05,
            f"median within-cell IQR {np.median(disp.iqr):.4f} points, "
            f"median p90-p10 {np.median(disp.p90_p10):.4f}, "
            f"over {disp.cell_id.size:,} cells of at least {min_size} loans",
        ),
        Criterion(
            "B2A-4  restricting to well-populated cells does not weaken it",
            result.restricted is not None
            and result.restricted.within_share >= split.within_share,
            f"all cells {split.within_share:.4f} over {split.n_cells:,} cells; "
            f"cells of at least {min_size} loans "
            f"{result.restricted.within_share:.4f} over "
            f"{result.restricted.n_cells:,} cells and "
            f"{result.restricted.n_loans:,} loans. Sparse cells have zero within "
            "variance by construction, so the unrestricted figure is the "
            "conservative one",
        ),
        Criterion(
            "B2A-5  it does not vanish within occupancy type",
            bool(result.by_occupancy)
            and min(v.within_share for v in result.by_occupancy.values()) > 0.01,
            ", ".join(
                f"{OCCUPANCY_LABEL.get(k, k)}: {v.within_share:.4f}"
                + (
                    f" ({result.by_occupancy_restricted[k].within_share:.4f} "
                    f"restricted)"
                    if k in result.by_occupancy_restricted
                    else ""
                )
                for k, v in sorted(result.by_occupancy.items())
            )
            or "no occupancy breakdown available",
        ),
        Criterion(
            "B2A-6  the exclusion band is not doing the work",
            bool(result.bound_sweep) and result.bound_spread() <= 0.05,
            "within share across bands "
            + ", ".join(
                f"{r['bound']:.0f}:{r['within_share']:.4f}" for r in result.bound_sweep
            )
            + f"; range {result.bound_spread():.2e}. "
            f"{result.excluded_implausible:,} of "
            f"{result.excluded_implausible + split.n_loans:,} rows lie outside "
            f"+-{result.spread_bound:.0f} and are not interest-rate differences",
        ),
        Criterion(
            "B2A-7  it survives with nothing excluded at all",
            result.rank_split is not None and result.rank_split.within_share > 0.01,
            (
                f"ranked within share {result.rank_split.within_share:.4f} over "
                f"{result.rank_split.n_loans:,} loans including every implausible "
                f"row; {result.rank_split_restricted.within_share:.4f} restricted. "
                "A rank is bounded by the sample size, so no placeholder value can "
                "dominate it, and the integrable null still predicts exactly zero"
                if result.rank_split is not None
                and result.rank_split_restricted is not None
                else "no ranked decomposition available"
            ),
        ),
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-cell-size", type=int, default=MIN_CELL_SIZE)
    ap.add_argument(
        "--spread-bound",
        type=float,
        default=SPREAD_BOUND,
        help=(
            "exclude reported spreads outside +-BOUND as not being interest-rate "
            "differences; pass inf to reproduce the pre-fix behaviour exactly"
        ),
    )
    args = ap.parse_args()

    apply_style()
    print("B2 loop A: dispersion at fixed position and date\n")
    spreads, cols = load()

    result = run_loop_a(
        spreads,
        cols,
        min_size=args.min_cell_size,
        spread_bound=args.spread_bound,
    )
    if result.excluded_implausible:
        print(
            f"  excluded {result.excluded_implausible:,} rows outside "
            f"+-{result.spread_bound:.0f} points (filer placeholders, see "
            "SPREAD_BOUND)"
        )
    path = figure_11(result)
    print(f"  wrote {path.relative_to(ROOT)}\n")

    criteria = evaluate(result, args.min_cell_size)
    print("criteria")
    for c in criteria:
        print(c.line())

    fired = {k: v for k, v in result.falsifications().items() if v}
    print("\npre-registered falsifications")
    if fired:
        for k in fired:
            print(f"  FIRED: {k}")
        print("  See docs/b2_measurement.md section 8 for the consequence.")
    else:
        print("  none fired")

    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b2_loop_a.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B2A",
                "min_cell_size": args.min_cell_size,
                "spread_bound": result.spread_bound,
                "excluded_implausible": result.excluded_implausible,
                "bound_sweep": result.bound_sweep,
                "bound_sweep_range": result.bound_spread(),
                "rank_decomposition": (
                    {
                        "within_share": result.rank_split.within_share,
                        "n_cells": result.rank_split.n_cells,
                        "n_loans": result.rank_split.n_loans,
                        "within_share_restricted": (
                            result.rank_split_restricted.within_share
                            if result.rank_split_restricted
                            else None
                        ),
                        "note": (
                            "computed on the raw sample before any exclusion, "
                            "including every implausible row"
                        ),
                    }
                    if result.rank_split
                    else None
                ),
                "variance": {
                    "between": result.split.between,
                    "within": result.split.within,
                    "within_share": result.split.within_share,
                    "n_cells": result.split.n_cells,
                    "n_loans": result.split.n_loans,
                },
                "variance_restricted": (
                    {
                        "min_cell_size": args.min_cell_size,
                        "between": result.restricted.between,
                        "within": result.restricted.within,
                        "within_share": result.restricted.within_share,
                        "n_cells": result.restricted.n_cells,
                        "n_loans": result.restricted.n_loans,
                    }
                    if result.restricted
                    else None
                ),
                "dispersion": result.dispersion.summary(),
                "by_occupancy": {
                    OCCUPANCY_LABEL.get(k, k): {
                        "within_share": v.within_share,
                        "n_cells": v.n_cells,
                        "n_loans": v.n_loans,
                        "within_share_restricted": (
                            result.by_occupancy_restricted[k].within_share
                            if k in result.by_occupancy_restricted
                            else None
                        ),
                        "n_cells_restricted": (
                            result.by_occupancy_restricted[k].n_cells
                            if k in result.by_occupancy_restricted
                            else None
                        ),
                    }
                    for k, v in sorted(result.by_occupancy.items())
                },
                "falsifications_fired": fired,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
