# -*- coding: utf-8 -*-
"""B2c. Is the within-cell dispersion accounted for by loan characteristics
that are themselves positions?

**Why this stage exists.** `docs/b2_measurement.md` §8 registered this as a
falsification condition for B2 and it was never computed. Its wording:

    delta_A dispersion is entirely accounted for by loan characteristics that
    are themselves positions ... The cell definition must be tightened and the
    measurement rerun before anything is claimed.

`LoopAResult.falsifications()` evaluates five conditions and this is not one of
them. The columns needed for it were retained deliberately at fetch time
(`data/fetch_hmda.py`, "Diagnostics, for the pre-registered falsification"),
and `loan_term`, `discount_points` and `total_loan_costs` appear nowhere else
in the repository. This file computes it.

**The objection being answered, in its strongest form.** A scalar price field
on positions may depend on any observable attribute of the position. Term, LTV
and amortisation are properties of the loan, not of the borrower, and B2's own
cell keys exclude all of them. So a scalar field that reads term and LTV could
reproduce within-cell rate-spread dispersion with no agent index anywhere. If
it does, B2's cell is drawn too coarsely and its reading is about the cell.

**The design is a refinement, not a regression.** The arms below add keys to the
existing cell and re-run the same estimator, so no functional form is assumed
and no new estimator is introduced (discipline D7). What changes between arms is
the partition and nothing else.

**The trap, and the control for it.** Refining a partition lowers within-cell
dispersion whether or not the added key explains anything, because the cells get
smaller and the degrees of freedom go with them. On a six-state smoke sample the
effect is larger than the signal: a label drawn at random with the same number of
bins took the within-share from `0.84` to `0.18`, while the real term-and-LTV
refinement took it to `0.42`. **A placebo drawn at random is therefore not the
control**, because it also changes the cell-size distribution.

The placebo used here permutes the added labels **inside each baseline cell**.
The number of refined cells, their sizes, and the marginal distribution of the
added key are then identical to the real arm by construction, and the single
thing destroyed is the association between the label and the rate spread. **A
real explanation is what A1 and A2 do beyond their permuted twin, and nothing
about what they do beyond the baseline is evidence of anything.**

**Positions and agents are different, and the split matters.** Term and LTV are
contract terms, so a scalar account is entitled to them. Debt-to-income is a
property of the borrower, so a scalar account on positions is not entitled to
it, and an arm that adds it is measuring the opposite thing: how much of the
residual lives on the agent index. The two are reported side by side and never
summed.

**The borrower arm needs its own twin, and the first full run is why.** On the
full sample the borrower arm moved the within-share further than the position
arm did, and on the raw numbers that reads as the borrower attribute explaining
more. It cannot be read that way without its own permuted twin, because the
two keys cut the sample into different numbers of cells. **Every arm here is
paired with a twin of its own**, and only the paired differences are compared
with each other.

**Each twin is permuted five times.** A single permutation is one draw, and the
difference being read is a few hundredths. Five draws give the spread of that
draw, so a difference smaller than the spread is not a reading. The count
follows the repetition discipline: five, and no more unless the spread turns out
to be near the difference.

**Readings, fixed before the run.** Three states, and the third exists.

- **The falsification fires** if the position arms A1 and A2 bring the
  within-share and the median within-cell IQR down to where the placebo arms do
  not, and far enough that what remains is at the reporting quantum of
  `rate_spread`. Then B2's cell must be redrawn and rerun.
- **The falsification does not fire** if A1 and A2 move the reading no further
  than their placebos do, and the agent arm G1 moves it further than either.
  Then the residual dispersion is not a position attribute.
- **Undecidable** if the position arms cannot be evaluated on enough of the
  sample, which is what the coverage table below is for. LTV is absent on
  roughly a third of rows in the file inspected, and a cell that loses its rows
  to a missing key has not been tested.

No threshold is placed on any of these quantities. The arms are printed and the
reading is stated above.

Usage::

    python experiments/b2c_position_attributes.py
    python experiments/b2c_position_attributes.py --rebuild-cache

Writes ``results/b2c_position_attributes.json`` and a reusable column cache at
``results/CACHE/b2c_columns.npz``. The cache is keyed on the file list, so a
later fetch invalidates it rather than being silently ignored.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.effective_price import (  # noqa: E402
    CELL_KEYS,
    MIN_CELL_SIZE,
    SPREAD_BOUND,
    as_codes,
    cell_dispersion,
    variance_decomposition,
)

RAW = ROOT / "data" / "raw" / "hmda"
CACHE = ROOT / "results" / "CACHE" / "b2c_columns.npz"
OUT = ROOT / "results" / "b2c_position_attributes.json"

VALID_NAME = re.compile(r"^hmda_[A-Z]{2}_(20\d\d)\.csv$")
VALID_YEARS = range(2018, 2031)

#: LTV cut points. These are the LLPA grid's own steps, so the bin edges are not
#: chosen against this data.
LTV_EDGES = (60.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 97.0)

#: HMDA publishes debt-to-income both as a number and as its own bracket
#: strings. Both are mapped onto the published brackets so one loan does not
#: land in two different bins depending on which filer reported it.
DTI_EDGES = (20.0, 30.0, 36.0, 41.0, 46.0, 50.0, 60.0)
DTI_STRINGS = {
    "<20%": 0,
    "20%-<30%": 1,
    "30%-<36%": 2,
    "36%-<41%": 3,
    "41%-<46%": 4,
    "46%-<50%": 5,
    "50%-60%": 6,
    ">60%": 7,
}

#: Loan term in months. Everything else lands in "other", which is a bin.
TERM_BINS = ("360", "180", "240", "120", "300", "480", "60")

MISSING = -1


def _show(path: Path) -> str:
    """Path for display. Falls back to the absolute form off the repo tree."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _bin_numeric(text: str, edges: tuple[float, ...]) -> int:
    try:
        v = float(text)
    except (TypeError, ValueError):
        return MISSING
    if not np.isfinite(v) or v < 0 or v > 1000:
        return MISSING
    return int(np.searchsorted(np.asarray(edges), v, side="right"))


def _bin_dti(text: str) -> int:
    if text in DTI_STRINGS:
        return DTI_STRINGS[text]
    return _bin_numeric(text, DTI_EDGES)


def _bin_term(text: str) -> int:
    if text in TERM_BINS:
        return TERM_BINS.index(text)
    try:
        float(text)
    except (TypeError, ValueError):
        return MISSING
    return len(TERM_BINS)


def _files() -> list[Path]:
    if not RAW.exists():
        raise SystemExit(
            f"no data directory at {_show(RAW)}.\n"
            "Run:  python data/fetch_hmda.py"
        )
    out = []
    for path in sorted(RAW.glob("*.csv")):
        m = VALID_NAME.match(path.name)
        if m and int(m.group(1)) in VALID_YEARS:
            out.append(path)
    if not out:
        raise SystemExit(f"no usable data in {_show(RAW)}")
    return out


def build_cache(files: list[Path]) -> dict[str, np.ndarray]:
    """One pass over the CSVs, storing only the columns this stage reads.

    Categorical columns are stored as integer codes with their tables, so the
    cache is a few hundred megabytes rather than a few gigabytes and reloads in
    seconds. Nothing is filtered here beyond what the main stage filters.
    """
    spreads: list[float] = []
    cell_raw: list[list[str]] = [[] for _ in CELL_KEYS]
    term: list[int] = []
    ltv: list[int] = []
    dti: list[int] = []

    for path in files:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            idx = {name: i for i, name in enumerate(header)}
            need = list(CELL_KEYS) + [
                "rate_spread",
                "loan_term",
                "loan_to_value_ratio",
                "debt_to_income_ratio",
            ]
            missing = [c for c in need if c not in idx]
            if missing:
                raise SystemExit(f"{path.name} lacks columns: {missing}")
            i_spread = idx["rate_spread"]
            i_cells = [idx[k] for k in CELL_KEYS]
            i_term = idx["loan_term"]
            i_ltv = idx["loan_to_value_ratio"]
            i_dti = idx["debt_to_income_ratio"]
            width = len(header)
            for row in reader:
                if len(row) != width:
                    continue
                if row[0].startswith("#"):
                    continue
                try:
                    s = float(row[i_spread])
                except (TypeError, ValueError):
                    continue
                spreads.append(s)
                for slot, i in enumerate(i_cells):
                    cell_raw[slot].append(row[i])
                term.append(_bin_term(row[i_term]))
                ltv.append(_bin_numeric(row[i_ltv], LTV_EDGES))
                dti.append(_bin_dti(row[i_dti]))
        print(f"    {path.name}: {len(spreads):,} cumulative", flush=True)

    store: dict[str, np.ndarray] = {
        "spread": np.asarray(spreads, dtype=np.float64),
        "term_bin": np.asarray(term, dtype=np.int16),
        "ltv_bin": np.asarray(ltv, dtype=np.int16),
        "dti_bin": np.asarray(dti, dtype=np.int16),
        "files": np.asarray(sorted(p.name for p in files)),
    }
    for slot, key in enumerate(CELL_KEYS):
        codes, _ = as_codes(np.asarray(cell_raw[slot]))
        store[f"cell_{key}"] = codes.astype(np.int32)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **store)
    print(f"  cache written: {_show(CACHE)}")
    return store


def load(rebuild: bool) -> dict[str, np.ndarray]:
    files = _files()
    names = np.asarray(sorted(p.name for p in files))
    if not rebuild and CACHE.exists():
        store = dict(np.load(CACHE, allow_pickle=False))
        if store["files"].shape == names.shape and bool((store["files"] == names).all()):
            print(f"  cache hit: {len(names)} files, {store['spread'].size:,} loans")
            return store
        print("  cache is stale against the file list; rebuilding")
    print(f"  reading {len(files)} files")
    return build_cache(files)


def permute_within(base_ids: np.ndarray, labels: np.ndarray,
                   rng: np.random.Generator) -> np.ndarray:
    """Shuffle ``labels`` inside each cell of ``base_ids``.

    The refined partition this produces has, cell for cell, the same sizes and
    the same label marginals as the real one. Only the association between the
    label and the value being measured is gone, which is the one thing the arm
    is asking about.
    """
    keys = rng.random(base_ids.size)
    shuffled = np.lexsort((keys, base_ids))
    in_place = np.lexsort((np.arange(base_ids.size), base_ids))
    out = np.empty_like(labels)
    out[in_place] = labels[shuffled]
    return out


def compose(parts: list[np.ndarray]) -> np.ndarray:
    """Cell identifiers from several code columns, as one integer per row."""
    out = parts[0].astype(np.int64)
    for p in parts[1:]:
        span = int(p.max()) + 2
        out = out * span + (p.astype(np.int64) + 1)
    codes, _ = as_codes(out)
    return codes


def arm(name: str, note: str, values: np.ndarray, parts: list[np.ndarray]) -> dict:
    ids = compose(parts)
    split = variance_decomposition(values, ids, min_size=0)
    disp = cell_dispersion(values, ids, min_size=MIN_CELL_SIZE)
    covered = int(disp.n.sum())
    return {
        "arm": name,
        "note": note,
        "n_keys": len(parts),
        "n_cells_total": int(np.unique(ids).size),
        "n_cells_at_or_above_min": int(disp.n.size),
        "loans_in_those_cells": covered,
        "loans_total": int(values.size),
        "coverage": float(covered / values.size) if values.size else 0.0,
        "within_share": float(split.within_share),
        "median_within_cell_iqr": float(np.median(disp.iqr)) if disp.n.size else None,
        "share_of_cells_iqr_above_25bp": (
            float((disp.iqr > 0.25).mean()) if disp.n.size else None
        ),
        "smallest_three_cells": sorted(int(x) for x in np.sort(disp.n)[:3]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--seed", type=int, default=20260829)
    ap.add_argument("--draws", type=int, default=5,
                    help="permutation draws per twin; five is the repetition "
                         "discipline's reference value")
    args = ap.parse_args()

    print("B2c  position attributes against the within-cell dispersion")
    store = load(args.rebuild_cache)

    spread = store["spread"]
    keep = np.abs(spread) <= SPREAD_BOUND
    spread = spread[keep]
    base = [store[f"cell_{k}"][keep] for k in CELL_KEYS]
    term = store["term_bin"][keep]
    ltv = store["ltv_bin"][keep]
    dti = store["dti_bin"][keep]

    n_term = int(term.max()) + 2
    n_ltv = int(ltv.max()) + 2
    n_dti = int(dti.max()) + 2
    base_ids = compose(base)

    # One seed stream per label per draw, so adding an arm later does not move
    # the arms already recorded.
    streams = np.random.SeedSequence(args.seed).spawn(3 * args.draws)
    draws = {}
    for slot, (name, labels) in enumerate((("term", term), ("ltv", ltv), ("dti", dti))):
        draws[name] = [
            permute_within(base_ids, labels,
                           np.random.default_rng(streams[slot * args.draws + d]))
            for d in range(args.draws)
        ]
        print(f"  permuted {name} inside baseline cells, {args.draws} draws")

    missing = {
        "loan_term": float((term == MISSING).mean()),
        "loan_to_value_ratio": float((ltv == MISSING).mean()),
        "debt_to_income_ratio": float((dti == MISSING).mean()),
    }

    real_specs = [
        ("A1 +term", "adds loan term, a contract attribute", [term], ["term"]),
        ("A2 +term+ltv", "adds loan term and LTV, both contract attributes",
         [term, ltv], ["term", "ltv"]),
        ("G1 +dti", "adds debt-to-income, a BORROWER attribute; a scalar account "
         "on positions is not entitled to it", [dti], ["dti"]),
        ("G2 +term+ltv+dti", "position attributes together with the borrower one",
         [term, ltv, dti], ["term", "ltv", "dti"]),
    ]

    arms = [arm("A0 baseline", "the seven registered cell keys", spread, base)]
    twins: dict[str, dict] = {}
    for name, note, labels, tags in real_specs:
        arms.append(arm(name, note, spread, base + labels))
        shares, cells = [], []
        for d in range(args.draws):
            a = arm("twin", "", spread, base + [draws[tag][d] for tag in tags])
            shares.append(a["within_share"])
            cells.append(a["n_cells_at_or_above_min"])
        twins[name] = {
            "twin_of": name,
            "note": f"{' and '.join(tags)} shuffled inside each baseline cell, "
                    f"{args.draws} draws; same cell sizes as the real arm by "
                    f"construction",
            "draws": args.draws,
            "within_share_median": float(np.median(shares)),
            "within_share_min": float(min(shares)),
            "within_share_max": float(max(shares)),
            "within_share_spread": float(max(shares) - min(shares)),
            "n_cells_at_or_above_min_median": int(np.median(cells)),
        }

    print()
    print(f"  {'arm':24s} {'within':>8s} {'medIQR':>8s} {'>25bp':>7s} "
          f"{'cells>=20':>10s} {'coverage':>9s}")
    for a in arms:
        print(f"  {a['arm']:24s} {a['within_share']:8.4f} "
              f"{(a['median_within_cell_iqr'] or 0.0):8.4f} "
              f"{(a['share_of_cells_iqr_above_25bp'] or 0.0):7.4f} "
              f"{a['n_cells_at_or_above_min']:10,d} {a['coverage']:9.4f}")
    by_name = {a["arm"]: a for a in arms}
    contrasts = []
    for name, *_ in real_specs:
        r, w = by_name[name], twins[name]
        diff = r["within_share"] - w["within_share_median"]
        contrasts.append({
            "arm": name,
            "kind": "position" if name.startswith("A") else "borrower",
            "within_share_real": r["within_share"],
            "twin_within_share_median": w["within_share_median"],
            "twin_within_share_spread": w["within_share_spread"],
            "real_minus_twin": diff,
            "diff_over_twin_spread": (
                abs(diff) / w["within_share_spread"]
                if w["within_share_spread"] > 0 else None
            ),
            "cells_real": r["n_cells_at_or_above_min"],
            "cells_twin_median": w["n_cells_at_or_above_min_median"],
        })
    print()
    print("  the comparison that carries the reading, each arm against its own twin:")
    print(f"    {'arm':20s} {'kind':10s} {'real':>8s} {'twin':>8s} "
          f"{'real-twin':>10s} {'twin sprd':>10s} {'ratio':>7s}")
    for c in contrasts:
        ratio = c["diff_over_twin_spread"]
        print(f"    {c['arm']:20s} {c['kind']:10s} {c['within_share_real']:8.4f} "
              f"{c['twin_within_share_median']:8.4f} {c['real_minus_twin']:+10.4f} "
              f"{c['twin_within_share_spread']:10.5f} "
              f"{('%.1f' % ratio) if ratio else '   n/a':>7s}")
    print("    A key that explains the dispersion drives its arm BELOW its twin.")
    print("    Compare the position arms' differences with the borrower arm's;")
    print("    a difference smaller than the twin spread is not a reading.")
    print()
    print("  missing rates on the added keys:")
    for k, v in sorted(missing.items()):
        print(f"    {k:24s} {v:.4f}")
    print()
    print("  Read each real arm against its permuted twin, never against A0. A")
    print("  refinement lowers within-cell dispersion whether or not it explains")
    print("  anything, and on a smoke sample that effect was larger than the signal.")
    print("  G1 and G2 point the other way and are never summed with the rest.")

    record = {
        "stage": "B2c",
        "step": "position_attributes",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "This stage answers the falsification registered in "
            "docs/b2_measurement.md section 8, which had not been computed. Until "
            "its reading is written into the B2 station file, the numbers here are "
            "not a licensed reading of that station."
        ),
        "seed": args.seed,
        "spread_bound": SPREAD_BOUND,
        "min_cell_size": MIN_CELL_SIZE,
        "ltv_edges": list(LTV_EDGES),
        "dti_edges": list(DTI_EDGES),
        "term_bins": list(TERM_BINS),
        "missing_rate": missing,
        "arms": arms,
        "twins": [twins[name] for name, *_ in real_specs],
        "draws": args.draws,
        "contrasts": contrasts,
        "reading": (
            "Each real arm is read against its own permuted twin, which holds the "
            "cell sizes and the label marginals fixed. The falsification fires if "
            "a position arm drives the within-share below its twin and reaches the "
            "reporting quantum of rate_spread; then B2's cell is drawn too coarsely "
            "and must be redrawn. It does not fire if the position arms track their "
            "twins while the borrower arm G1 moves further than either. It is "
            "undecidable where coverage on a position arm is too low to evaluate, "
            "which the coverage column reports rather than hides."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {_show(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
