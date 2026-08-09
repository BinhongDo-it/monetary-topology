"""B2 loop A graded placebo: conventional against FHA and VA.

Pre-registered in ``docs/b2_measurement.md`` section 8.1, written and committed
before any FHA or VA row was retrieved. Run the retrievals first::

    python data/fetch_hmda.py --product fha
    python data/fetch_hmda.py --product va

Then::

    python experiments/b2_placebo_products.py
    python experiments/b2_placebo_products.py --splits 5     # quicker null

Writes ``figures/b2_fig12_*.png`` and ``results/b2_placebo_products.json``.

What the placebo is for
-----------------------
Loop A shows that terms disperse at fixed position and date. It does not show
that the dispersion is carried by the agent index rather than by something the
cell keys failed to hold fixed. This tests that by suppressing the agent index
through programme rule while leaving every position key identical.

Conventional lending prices credit explicitly, through the loan-level price
adjustment grid. FHA replaces that with a flat insurance premium schedule; VA
replaces it with a funding fee that moves with down payment and prior use but not
with credit score.

Why VA and not FHA carries the test
-----------------------------------
``within_share(FHA) < within_share(conventional)`` is also predicted by a duller
account: FHA borrowers are a narrower pool, so `a` spans a shorter interval and
`P(a, g)` varies less over the realised sample even if the field is exactly as
non-integrable. Same sign, so FHA discriminates nothing on its own.

VA separates the two. Eligibility is service-based rather than credit-based, so
the pool is wide, while the price grid is flat. The pool-width account predicts VA
near conventional; the agent-index account predicts VA near FHA. Opposite
directions, so this is the comparison that can fail.

Why there is a split-half null
------------------------------
A gap of 0.05 means nothing without knowing what a gap of zero looks like at this
sample size. The conventional sample is split at random and the same difference
computed between halves, where the true value is exactly zero by construction.
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
    make_cell_ids,
    plausible_mask,
    rank_decomposition,
    variance_decomposition,
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
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

#: Directory per programme, matching ``data/fetch_hmda.py``. Separate directories
#: rather than one directory with a column, so that retrieving a new programme
#: cannot reach an already-retrieved one by any path.
PRODUCT_DIRS = {
    "conventional": "hmda",
    "fha": "hmda_fha",
    "va": "hmda_va",
}

#: Same convention as the loop A loader. Files not matching are skipped and
#: reported rather than silently included, and nothing is ever removed.
VALID_NAME = re.compile(r"^hmda_[A-Z]{2}_(20\d\d)\.csv$")
VALID_YEARS = range(2018, 2031)

#: Pre-registered in section 8.1. The gap conventional minus VA must clear this
#: *and* the split-half null.
MIN_GAP = 0.05


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


@dataclass
class Sample:
    """One programme, held in compact arrays.

    The string columns are released as soon as the codes are built. Holding seven
    string columns for three programmes at once is about twenty-nine million rows
    of Python objects and does not fit; holding four numeric arrays is under a
    gigabyte.
    """

    product: str
    spreads: np.ndarray  # float64, raw, no band applied
    cell_ids: np.ndarray  # int64
    pair: np.ndarray  # int64, tract-year code, local to this sample
    pair_values: np.ndarray  # str, one entry per distinct code

    @property
    def n(self) -> int:
        return int(self.spreads.size)


def load_product(product: str) -> Sample:
    """Read one programme's directory into compact arrays."""
    directory = ROOT / "data" / "raw" / PRODUCT_DIRS[product]
    if not directory.exists():
        raise SystemExit(
            f"no data directory at {directory.relative_to(ROOT)}.\n"
            f"Run:  python data/fetch_hmda.py --product {product}"
        )

    files, skipped = [], []
    for path in sorted(directory.glob("*.csv")):
        match = VALID_NAME.match(path.name)
        if match and int(match.group(1)) in VALID_YEARS:
            files.append(path)
        else:
            skipped.append(path.name)
    if skipped:
        print(f"  {product}: skipped {len(skipped)} file(s) off-convention")
    if not files:
        raise SystemExit(f"no usable data in {directory.relative_to(ROOT)}")

    spreads: list[float] = []
    cols: dict[str, list[str]] = {k: [] for k in CELL_KEYS}
    for path in files:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                # The completion marker parses as a short row; see the loop A
                # loader for why this guard exists.
                if row.get("activity_year", "").startswith("#"):
                    continue
                try:
                    spreads.append(float(row["rate_spread"]))
                except (KeyError, TypeError, ValueError):
                    continue
                for key in CELL_KEYS:
                    cols[key].append(row.get(key, ""))

    arrays = {k: np.array(v) for k, v in cols.items()}
    cols.clear()

    cell_ids = make_cell_ids(arrays)

    # Tract-year, kept as a small value table plus per-row codes. There are under
    # a million distinct pairs against tens of millions of rows, which is what
    # makes the cross-programme intersection cheap.
    tract_vals, tract_codes = np.unique(arrays["census_tract"], return_inverse=True)
    year_vals, year_codes = np.unique(arrays["activity_year"], return_inverse=True)
    flat = tract_codes.astype(np.int64) * year_vals.size + year_codes
    pair_vals_flat, pair = np.unique(flat, return_inverse=True)
    pair_values = np.array(
        [
            f"{tract_vals[c // year_vals.size]}|{year_vals[c % year_vals.size]}"
            for c in pair_vals_flat
        ]
    )

    out = Sample(
        product=product,
        spreads=np.asarray(spreads, dtype=np.float64),
        cell_ids=cell_ids.astype(np.int64),
        pair=pair.astype(np.int64),
        pair_values=pair_values,
    )
    print(
        f"  {product:<13} {len(files):>3} files, {out.n:>10,} loans, "
        f"{pair_values.size:>8,} tract-years"
    )
    return out


def shares(
    sample: Sample, *, min_size: int, bound: float, mask=None, ranked: bool = True
) -> dict:
    """Banded and ranked within shares for one sample, optionally sub-masked.

    ``ranked`` is switchable because the split-half null runs this forty times and
    the rank transform is a full sort of ten million rows each time, which the null
    does not need.
    """
    spreads = sample.spreads if mask is None else sample.spreads[mask]
    cells = sample.cell_ids if mask is None else sample.cell_ids[mask]

    keep = plausible_mask(spreads, bound)
    banded = variance_decomposition(spreads[keep], cells[keep], min_size=min_size)
    out = {
        "n_loans": int(spreads.size),
        "n_excluded": int(spreads.size - int(keep.sum())),
        "within_share": banded.within_share,
        "n_cells": banded.n_cells,
        "n_loans_in_cells": banded.n_loans,
    }
    if ranked:
        # Ranked on everything, band included, so the exclusion cannot be what
        # produces any gap between programmes.
        r = rank_decomposition(spreads, cells, min_size=min_size)
        out["within_share_ranked"] = r.within_share
        out["n_cells_ranked"] = r.n_cells
    return out


def common_pair_masks(samples: dict[str, Sample]) -> tuple[dict[str, np.ndarray], int]:
    """Row masks restricting every sample to tract-years present in all of them.

    VA lending concentrates near installations and FHA in lower-income tracts.
    Without this, a difference in where the programmes lend could stand in for a
    difference in how they price, which is the thing being tested.
    """
    common: set[str] | None = None
    for sample in samples.values():
        vals = set(sample.pair_values.tolist())
        common = vals if common is None else (common & vals)
    common_arr = np.array(sorted(common or set()), dtype="U32")

    masks = {}
    for name, sample in samples.items():
        keep_codes = np.flatnonzero(np.isin(sample.pair_values, common_arr))
        masks[name] = np.isin(sample.pair, keep_codes)
    return masks, int(common_arr.size)


def split_half_null(
    sample: Sample, *, splits: int, min_size: int, bound: float, seed: int = 0
) -> dict:
    """The scale of a gap whose true value is exactly zero.

    The sample is halved at random and the same difference computed between the
    halves. Anything the conventional-VA gap does not clear is not a finding.
    """
    rng = np.random.default_rng(seed)
    gaps = []
    for _ in range(splits):
        left = rng.random(sample.n) < 0.5
        kw = {"min_size": min_size, "bound": bound, "ranked": False}
        a = shares(sample, mask=left, **kw)["within_share"]
        b = shares(sample, mask=~left, **kw)["within_share"]
        gaps.append(abs(a - b))
    return {
        "splits": splits,
        "max_abs_gap": float(max(gaps)),
        "median_abs_gap": float(np.median(gaps)),
        "gaps": [float(g) for g in gaps],
    }


#: Cell-size cutoffs the post-hoc robustness sweep runs at.
SWEEP_SIZES: tuple[int, ...] = (5, 10, 20, 50, 100)

#: Below this many surviving cells a programme's share at that cutoff is not read.
MIN_CELLS_FOR_SWEEP = 100


def min_size_sweep(
    samples: dict[str, Sample], *, bound: float, sizes: tuple[int, ...] = SWEEP_SIZES
) -> dict:
    """Post-hoc. Does the cell-size cutoff select a special set of VA tracts?

    **Not pre-registered.** Registered in nothing, run after the criteria were
    read, and reported separately from them for that reason.

    The objection it addresses is the strongest one left. VA clears 24,880 cells
    against conventional's 328,902, and a tract needs twenty VA purchase loans in
    one year to qualify, which in practice means a tract near an installation.
    Borrowers there may be more alike than VA borrowers generally, in pay grade
    and in tenure, so the cutoff could be reintroducing the narrow-pool
    explanation at the level of the cell rather than the programme. The common
    tract-year restriction does not catch this, because it asks whether a tract
    appears at all and not how many loans it holds.

    Lowering the cutoff admits far more tracts and dilutes the installation
    concentration. If VA's share is roughly flat across cutoffs, the selection is
    not what produces it. If VA rises sharply as the cutoff falls, the objection
    stands and belongs in the limitations rather than being argued away.
    """
    out: dict[str, dict] = {}
    for size in sizes:
        row = {
            name: shares(s, min_size=size, bound=bound, ranked=False)
            for name, s in samples.items()
        }
        out[str(size)] = {
            **{
                f"{name}_{k}": v
                for name, r in row.items()
                for k, v in (("share", r["within_share"]), ("cells", r["n_cells"]))
            },
            "gap_conventional_minus_va": (
                row["conventional"]["within_share"] - row["va"]["within_share"]
            ),
            # A cutoff that empties a programme returns a share of zero, and the
            # gap against it would then look large for the least interesting
            # reason. Rows below this are printed and stored but excluded from
            # any statement about the gap.
            "usable": all(r["n_cells"] >= MIN_CELLS_FOR_SWEEP for r in row.values()),
        }
    return out


def two_by_two(overall: dict) -> dict:
    """Post-hoc reading of the three programmes as a design with one cell missing.

    **Not pre-registered.** Section 8.1 registered no direction for FHA against VA
    and said the outcome would be reported and not interpreted. This is the
    interpretation, kept separate and labelled so it cannot be mistaken for a
    tested prediction.

    Conventional has a credit-graded price grid and a wide pool. VA has a flat
    grid and a wide pool. FHA has a flat grid and a narrow pool. The fourth cell,
    a graded grid over a narrow pool, has no programme because programme rules
    bundle who may enter with how they are priced, which is why the reading stays
    a reading.
    """
    conv, fha, va = (overall[k]["within_share"] for k in ("conventional", "fha", "va"))
    return {
        "conventional_graded_grid_wide_pool": conv,
        "va_flat_grid_wide_pool": va,
        "fha_flat_grid_narrow_pool": fha,
        "missing_cell": "graded grid over a narrow pool: no programme has this",
        "pricing_channel_conventional_minus_va": conv - va,
        "pool_width_channel_va_minus_fha": va - fha,
        "note": (
            "the two channels come out close in magnitude and together span the "
            "whole distance from conventional to FHA. Additivity is assumed, not "
            "shown, and cannot be shown without the missing cell"
        ),
    }


def evaluate(overall: dict, restricted: dict, null: dict) -> list[Criterion]:
    conv, fha, va = (overall[k]["within_share"] for k in ("conventional", "fha", "va"))
    conv_r, fha_r, va_r = (
        overall[k]["within_share_ranked"] for k in ("conventional", "fha", "va")
    )
    gap = conv - va
    gap_ranked = conv_r - va_r
    c_conv, c_fha, c_va = (
        restricted[k]["within_share"] for k in ("conventional", "fha", "va")
    )

    return [
        Criterion(
            "P1  conventional exceeds VA by more than the registered margin",
            gap > MIN_GAP and gap_ranked > 0,
            f"conventional {conv:.4f} - VA {va:.4f} = {gap:+.4f} "
            f"(registered > {MIN_GAP}); ranked {conv_r:.4f} - {va_r:.4f} "
            f"= {gap_ranked:+.4f} (registered same sign). VA has a wide pool and a "
            "flat price grid, so the pool-width account predicts VA near "
            "conventional and this is where it fails or survives",
        ),
        Criterion(
            "P2  conventional exceeds FHA",
            conv > fha,
            f"conventional {conv:.4f} vs FHA {fha:.4f} = {conv - fha:+.4f}. "
            "Both accounts predict this sign, so it grades the effect and "
            "discriminates nothing",
        ),
        Criterion(
            "P3  both hold on tract-years common to all three programmes",
            c_conv > c_va + MIN_GAP and c_conv > c_fha,
            f"common tract-years: conventional {c_conv:.4f}, FHA {c_fha:.4f}, "
            f"VA {c_va:.4f}; conventional - VA = {c_conv - c_va:+.4f}. "
            "Removes the geography difference between where the programmes lend",
        ),
        Criterion(
            "P5  the gap clears a gap whose true value is zero",
            gap > null["max_abs_gap"],
            f"conventional - VA = {gap:+.4f} against a split-half null whose "
            f"largest absolute gap over {null['splits']} random halvings of the "
            f"conventional sample is {null['max_abs_gap']:.4f} "
            f"(median {null['median_abs_gap']:.4f})",
        ),
    ]


def figure_12(overall: dict, restricted: dict, null: dict) -> Path:
    fig, (ax_bar, ax_null) = plt.subplots(1, 2, figsize=(11.0, 4.4))

    names = ["conventional", "fha", "va"]
    labels = ["Conventional", "FHA", "VA"]
    x = np.arange(len(names))
    w = 0.38
    ax_bar.bar(
        x - w / 2,
        [overall[n]["within_share"] for n in names],
        w,
        label="all tract-years",
        color=COLOR_LAYER1,
    )
    ax_bar.bar(
        x + w / 2,
        [restricted[n]["within_share"] for n in names],
        w,
        label="tract-years common to all three",
        color=COLOR_LAYER2,
    )
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(labels)
    ax_bar.set_ylim(0, 1)
    ax_bar.set_ylabel("within share of rate-spread variance")
    ax_bar.axhline(0.0, color=COLOR_INSTRUMENT, linewidth=1.2, linestyle="--")
    ax_bar.legend(fontsize=8, loc="lower left")
    ax_bar.set_title("Same position keys, different price grids")
    annotate(
        ax_bar,
        "Conventional prices credit through an explicit grid. FHA and VA replace\n"
        "it with a flat schedule. VA's pool is wide, so a narrow-pool explanation\n"
        "predicts VA near conventional rather than near FHA.",
        loc="upper right",
    )

    ax_null.hist(null["gaps"], bins=12, color=COLOR_LAYER2, edgecolor="none")
    observed = overall["conventional"]["within_share"] - overall["va"]["within_share"]
    ax_null.axvline(observed, color=COLOR_ACCENT, linewidth=1.8)
    ax_null.set_xlabel("absolute gap in within share")
    ax_null.set_ylabel("random halvings")
    ax_null.set_title("What a gap of exactly zero looks like")
    annotate(
        ax_null,
        "Histogram: the conventional sample split at random, where the true gap\n"
        f"is zero by construction. Line: conventional minus VA, {observed:+.4f}.",
        loc="upper left",
    )

    fig.suptitle(
        "Suppress the credit-graded price grid by programme rule, "
        "hold every position key fixed",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, FIGURES / "b2_fig12_graded_placebo.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-cell-size", type=int, default=MIN_CELL_SIZE)
    ap.add_argument("--spread-bound", type=float, default=SPREAD_BOUND)
    ap.add_argument("--splits", type=int, default=20)
    args = ap.parse_args()

    apply_style()
    print("B2 loop A graded placebo: conventional vs FHA vs VA\n")

    samples = {name: load_product(name) for name in PRODUCT_DIRS}

    print("\nwithin share by programme")
    overall = {
        name: shares(s, min_size=args.min_cell_size, bound=args.spread_bound)
        for name, s in samples.items()
    }
    for name, r in overall.items():
        print(
            f"  {name:<13} banded {r['within_share']:.4f}  "
            f"ranked {r['within_share_ranked']:.4f}  "
            f"cells {r['n_cells']:>8,}  excluded {r['n_excluded']:>4}"
        )

    masks, n_common = common_pair_masks(samples)
    print(f"\ntract-years common to all three: {n_common:,}")
    restricted = {
        name: shares(
            s,
            min_size=args.min_cell_size,
            bound=args.spread_bound,
            mask=masks[name],
        )
        for name, s in samples.items()
    }
    for name, r in restricted.items():
        print(
            f"  {name:<13} banded {r['within_share']:.4f}  "
            f"ranked {r['within_share_ranked']:.4f}  "
            f"loans {r['n_loans']:>10,}"
        )

    print(f"\nsplit-half null on the conventional sample, {args.splits} halvings")
    null = split_half_null(
        samples["conventional"],
        splits=args.splits,
        min_size=args.min_cell_size,
        bound=args.spread_bound,
    )
    print(
        f"  largest absolute gap {null['max_abs_gap']:.4f}, "
        f"median {null['median_abs_gap']:.4f}"
    )

    path = figure_12(overall, restricted, null)
    print(f"\n  wrote {path.relative_to(ROOT)}\n")

    criteria = evaluate(overall, restricted, null)
    print("criteria")
    for c in criteria:
        print(c.line())

    fha_va = overall["fha"]["within_share"] - overall["va"]["within_share"]
    print(
        "\nreported and not interpreted (P4: no direction was registered)\n"
        f"  FHA - VA = {fha_va:+.4f}"
    )

    print("\npost-hoc, not pre-registered, reported apart from the criteria")
    sweep = min_size_sweep(samples, bound=args.spread_bound)
    print("  cell-size cutoff sweep: does the cutoff select a special VA tract set?")
    print(
        f"  {'cutoff':>7}  {'conv':>7} {'cells':>8}  {'fha':>7} {'cells':>7}  "
        f"{'va':>7} {'cells':>7}  {'conv-va':>8}"
    )
    for size in SWEEP_SIZES:
        r = sweep[str(size)]
        flag = "" if r["usable"] else f"   (< {MIN_CELLS_FOR_SWEEP} cells, not read)"
        print(
            f"  {size:>7}  {r['conventional_share']:>7.4f} "
            f"{r['conventional_cells']:>8,}  {r['fha_share']:>7.4f} "
            f"{r['fha_cells']:>7,}  {r['va_share']:>7.4f} {r['va_cells']:>7,}  "
            f"{r['gap_conventional_minus_va']:>+8.4f}{flag}"
        )
    gaps = [
        sweep[str(s)]["gap_conventional_minus_va"]
        for s in SWEEP_SIZES
        if sweep[str(s)]["usable"]
    ]
    if gaps:
        print(
            f"  over the {len(gaps)} usable cutoffs: gap range "
            f"{max(gaps) - min(gaps):.4f}, sign held throughout "
            f"{all(g > 0 for g in gaps)}"
        )
    else:
        print("  no cutoff leaves every programme enough cells to read")

    square = two_by_two(overall)
    print("\n  the three programmes as a design with one cell missing")
    print(
        f"    pricing channel  conventional - VA = "
        f"{square['pricing_channel_conventional_minus_va']:+.4f}"
    )
    print(
        f"    pool width       VA - FHA          = "
        f"{square['pool_width_channel_va_minus_fha']:+.4f}"
    )
    print("    the fourth cell, a graded grid over a narrow pool, has no programme")

    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b2_placebo_products.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B2A-placebo",
                "min_cell_size": args.min_cell_size,
                "spread_bound": args.spread_bound,
                "registered_min_gap": MIN_GAP,
                "overall": overall,
                "common_tract_years": n_common,
                "restricted_to_common": restricted,
                "split_half_null": null,
                "fha_minus_va_not_registered": fha_va,
                "post_hoc_not_pre_registered": {
                    "min_size_sweep": sweep,
                    "two_by_two": square,
                },
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
