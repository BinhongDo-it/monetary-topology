#!/usr/bin/env python3
"""Diagnostics for the B2 loop A result. Prints about forty lines.

Written because three different subsamples returned a within share agreeing to
six decimal places, at a suspiciously round 0.975. A round number repeating
across subsamples is the signature of a bug, not of a finding, and this checks
the mundane explanations before anything is built on top of it.

Usage::

    python scripts/diagnose_b2.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b2_loop_a import load  # noqa: E402

from monetary_topology.effective_price import (  # noqa: E402
    CELL_KEYS,
    as_codes,
    make_cell_ids,
    variance_decomposition,
)


def main() -> int:
    spreads, cols = load()

    print("\n1. the value being decomposed")
    print(f"   n                {spreads.size:,}")
    print(f"   distinct values  {len(np.unique(spreads)):,}")
    print(f"   min / max        {spreads.min():.4f} / {spreads.max():.4f}")
    print(f"   mean / sd        {spreads.mean():.4f} / {spreads.std():.4f}")
    for q in (1, 5, 25, 50, 75, 95, 99):
        print(f"   p{q:<3}             {np.percentile(spreads, q):.4f}")
    top = Counter(spreads.tolist()).most_common(8)
    print("   most common values (value, count, share):")
    for v, c in top:
        print(f"     {v:>9.4f}  {c:>10,}  {c / spreads.size:.4%}")

    print("\n2. cell structure")
    cell_ids = make_cell_ids(cols)
    codes, n_cells = as_codes(cell_ids)
    counts = np.bincount(codes)
    print(f"   cells            {n_cells:,}")
    print(f"   size 1           {(counts == 1).sum():,}  ({(counts == 1).mean():.2%})")
    print(f"   size < 20        {(counts < 20).sum():,}  ({(counts < 20).mean():.2%})")
    print(f"   median size      {np.median(counts):.0f}")
    print(f"   max size         {counts.max():,}")
    print(f"   loans in cells >= 20: {counts[counts >= 20].sum():,}")

    print("\n3. the decomposition at several cutoffs")
    print("   cutoff    cells       loans        between        within    share")
    for m in (0, 2, 5, 10, 20, 30, 50, 100, 200):
        v = variance_decomposition(spreads, cell_ids, min_size=m)
        print(
            f"   {m:>6}  {v.n_cells:>9,}  {v.n_loans:>11,}  "
            f"{v.between:>12,.1f}  {v.within:>12,.1f}  {v.within_share:.6f}"
        )

    print("\n4. is the cutoff series smooth, or does it pin to one value?")
    shares = [
        variance_decomposition(spreads, cell_ids, min_size=m).within_share
        for m in range(15, 41, 5)
    ]
    print("   min_size 15,20,25,30,35,40 ->", ", ".join(f"{s:.6f}" for s in shares))
    print(
        "   spread across those cutoffs:",
        f"{max(shares) - min(shares):.2e}",
        "(a flat series would suggest the value is structural, not estimated)",
    )

    print("\n5. one cell held to the same year but split by month is not available")
    print("   activity_year is the only time key HMDA exposes. Rate spread is APR")
    print("   minus APOR at the rate-set date, so the benchmark already moves with")
    print("   the market, but any residual within-year drift lands in the within")
    print("   term. Checking the size of that by year:")
    years = np.asarray(cols["activity_year"])
    print("   year     n         sd(spread)   within share (min_size 20)")
    for y in sorted(np.unique(years)):
        mask = years == y
        if mask.sum() < 1000:
            continue
        v = variance_decomposition(spreads[mask], cell_ids[mask], min_size=20)
        print(
            f"   {y}  {mask.sum():>9,}  {spreads[mask].std():>10.4f}   "
            f"{v.within_share:.6f}"
        )

    print("\n6. cell keys actually varying in the sample")
    for key in CELL_KEYS:
        vals = np.unique(np.asarray(cols[key]))
        shown = ", ".join(map(str, vals[:6])) + (" ..." if vals.size > 6 else "")
        print(f"   {key:<28} {vals.size:>8,} distinct   {shown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
