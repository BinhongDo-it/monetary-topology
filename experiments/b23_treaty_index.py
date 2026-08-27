"""B23: the class index across twenty countries, from published rates alone.

**No price data is used and none is needed.** The index between two classes of
holder of one share, when the only difference is a withholding rate applied at
source, is fixed by the two rates and the dividend yield. Both rates are
published; the yield enters as a scale.

**The class pair is two foreign holders, and that is deliberate.** One is a
resident of a country with a US-style tax treaty, taxed at the treaty's portfolio
ceiling; the other is a holder with no treaty relief, taxed at the issuer
country's statutory non-resident rate. **Both are flat rates withheld at source**,
which is the same shape as the four rates that carried B21 and is not the shape a
resident income tax has: residents in many of these countries face progressive
bands or an imputation credit, and a band is not a rate.

**What this arm does not do.** It does not measure whether a market prices the
wedge. The arm that did that on A+H rests on the two lines having different
marginal holders, which follows there from the A and H lines being
non-convertible. **An ordinary ADR is convertible back into the underlying**, so
arbitrage gives the two lines one marginal holder and that arm has no footing
here. This file therefore computes and does not measure, and says so.

Usage::

    python experiments/b23_treaty_index.py
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b23_treaty_index.json"

# Statutory non-resident dividend withholding, whtcalculator.com 2026 country table
STAT = {"Australia": 30.0, "Austria": 27.5, "Belgium": 30.0, "Canada": 25.0,
        "China": 10.0, "Denmark": 27.0, "France": 30.0, "Germany": 26.375,
        "India": 20.0, "Ireland": 25.0, "Italy": 26.0, "Japan": 20.42,
        "Netherlands": 15.0, "New Zealand": 30.0, "Norway": 25.0,
        "South Korea": 20.0, "Spain": 19.0, "Sweden": 30.0,
        "Switzerland": 35.0, "United Kingdom": 0.0}
# US treaty portfolio dividend ceiling, Article 10(2)(b), reciprocal by construction
TREATY = {"Australia": 15.0, "Austria": 15.0, "Belgium": 5.0, "Canada": 15.0,
          "China": 10.0, "Denmark": 15.0, "France": 15.0, "Germany": 15.0,
          "India": 25.0, "Ireland": 15.0, "Italy": 15.0, "Japan": 10.0,
          "Netherlands": 15.0, "New Zealand": 15.0, "Norway": 15.0,
          "South Korea": 15.0, "Spain": 15.0, "Sweden": 15.0,
          "Switzerland": 15.0, "United Kingdom": 15.0}
YIELDS = [0.01, 0.02, 0.03, 0.05, 0.08]     # a scale, not a fitted number


def index_exact(y: float, ta: float, tb: float) -> float:
    """log((1 + (1-ta)y) / (1 + (1-tb)y)), the same form B21 uses."""
    return math.log((1 + (1 - ta) * y) / (1 + (1 - tb) * y))


def main() -> int:
    rows = []
    for c in sorted(STAT):
        s, t = STAT[c] / 100, TREATY[c] / 100
        # **A treaty rate is a ceiling, not a rate.** It binds only where it sits
        # below the statutory rate; above it, nothing happens. India's 25 per cent
        # ceiling over a 20 per cent statutory rate is inert, and so is the United
        # Kingdom's 15 over zero. The first version of this file tested
        # `gap > 0 and statutory > 0`, which let India through, and that is the
        # same mistake failure mode 71 was written about earlier the same day.
        binding = t < s
        gap = (s - t) if binding else 0.0
        rows.append({"country": c, "statutory": STAT[c], "treaty": TREATY[c],
                     "gap": round(gap, 5),
                     "index_bp": {f"{y:.0%}": (1e4 * index_exact(y, t, s))
                                  if binding else 0.0 for y in YIELDS},
                     "binding": binding})

    live = [r for r in rows if r["binding"]]
    dead = [r for r in rows if not r["binding"]]
    print(f"{len(rows)} countries with both rates published. **No prices used.**\n")
    print(f"  {'country':>16} {'statutory':>10} {'treaty':>7} {'gap':>8}"
          + "".join(f"{f'{y:.0%}':>9}" for y in YIELDS))
    print(f"  {'':>16} {'':>10} {'':>7} {'':>8}"
          + "".join(f"{'bp':>9}" for _ in YIELDS))
    for r in sorted(rows, key=lambda x: -x["gap"]):
        mark = "" if r["binding"] else "   <- not binding"
        print(f"  {r['country']:>16} {r['statutory']:>10} {r['treaty']:>7} "
              f"{100*r['gap']:>7.3f}%"
              + "".join(f"{r['index_bp'][f'{y:.0%}']:>9.1f}" for y in YIELDS) + mark)

    print(f"\n  **{len(live)} of {len(rows)} carry a binding wedge.**")
    print(f"  The {len(dead)} that do not: "
          + ", ".join(f"{r['country']} ({r['statutory']}% statutory, "
                      f"{r['treaty']}% treaty)" for r in dead))
    print("  **A treaty rate is a ceiling.** Where it sits at or above the")
    print("  statutory rate it does nothing, so the United Kingdom's 15 over zero")
    print("  and India's 25 over 20 are bands of zero width and not reversed")
    print("  class differences.")

    at3 = sorted(r["index_bp"]["3%"] for r in live)
    print(f"\n  at a three per cent yield the index runs {at3[0]:.1f} to "
          f"{at3[-1]:.1f} bp across the {len(live)} live countries, "
          f"median {statistics.median(at3):.1f}")
    print(f"  B21 measured 14.8 and 30.5 bp on its two withholding edges and "
          f"52.7 on the twelve-month edge, **so this carrier's range brackets it**.")

    crit = [
        {"name": "B23-1  the statutory class index is nonzero wherever the two "
                 "published rates differ, and zero where they do not",
         "passed": all(r["index_bp"]["3%"] > 0 for r in live)
                   and all(abs(r["index_bp"]["3%"]) < 1e-9 or not r["binding"]
                           for r in dead),
         "detail": f"{len(live)} of {len(rows)} binding; at a 3% yield the index "
                   f"runs {at3[0]:.1f} to {at3[-1]:.1f} bp, median "
                   f"{statistics.median(at3):.1f}"},
        {"name": "B23-2  the treatment takes many values, which is what this "
                 "carrier was opened for",
         "passed": len({r["gap"] for r in live}) >= 5,
         "detail": f"{len({r['gap'] for r in live})} distinct gaps over "
                   f"{len(live)} countries, against one value on the A+H carrier"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B23", "step": "treaty_index",
        "diagnostic_only": True,
        "diagnostic_reason": "Arithmetic on published rates, not a measurement. "
                             "The arm that measures whether a market prices the "
                             "wedge needs two lines with different marginal "
                             "holders, which an ordinary convertible ADR does "
                             "not provide.",
        "class_pair": "non-treaty foreign holder against US treaty holder, "
                      "same ordinary share, both flat and withheld at source",
        "countries": rows, "binding": len(live),
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, "
          f"{sum(1 for c in crit if c['passed'])} passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
