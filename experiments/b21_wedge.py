"""B21: the transfer wedge on the onshore cash vertex, and what it licenses.

The square on the position edge `onshore cash - A share`, with the two classes
being mainland and international holders, has the sum

    square = w_a(cash,A) - w_b(cash,A) + t_ab(A) - t_ab(cash)

from `b1_theorem.md` section 8, assumption A1's robustness paragraph. The first
two terms are zero by inspection: Northbound and domestic buyers meet on one
order book, and an A-share position passes between them by trading on that same
book. **So the square is minus the cost of moving an onshore-renminbi position
from a mainland holder to an international one**, which is what the capital
account restricts.

**What this file computes, and what it does not.** It computes that wedge from
the two exchange-rate series, and compares it against the round-trip trading cost
read off the fee schedules. It does **not** attribute the result: section 8 is
explicit that a non-zero square sum proves the field is not exact and leaves the
attribution open, so the reading here supports Corollary 1 and says nothing about
whether the two classes face different prices.

**A caveat that has to travel with the number.** The wedge computed this way is
the onshore-offshore renminbi spread, which is a quantity other people already
publish. **Its value here is not that the number is new.** It is that the number
is what a closed loop on this carrier sums to, and a single scalar price field on
positions predicts that sum to be exactly zero. The novelty is in what it
refutes, not in what it measures.

Usage::

    python experiments/b21_wedge.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"

# Round trip trading cost, read from the exchange fee schedules rather than
# estimated. Northbound: handling 0.00341%, securities management 0.002%,
# transfer 0.001% each side, stamp duty 0.05% on the sell. Southbound: HK stamp
# 0.1%, trading fee 0.00565%, SFC levy 0.0027%, AFRC levy 0.00015%, settlement
# 0.0042% each side. Commission is the only negotiable line.
COST_BP = {"institutional, commission 0.01%": 43.0,
           "retail, commission 0.03%": 51.0}


def series(name: str) -> dict[str, float]:
    """Accept either filename spelling. The fetcher wrote both at different times."""
    for cand in (PX / f"{name.replace('=', '_')}.csv", PX / f"{name}.csv"):
        if cand.exists():
            path = cand
            break
    else:
        raise SystemExit(f"missing {name} under either spelling in {PX}. "
                         f"Run data/fetch_ah_panel.py --fx first.")
    out = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        try:
            c = float(r["Close"])
        except (TypeError, ValueError):
            continue
        if c > 0:
            out[r["Date"][:10]] = c
    return out


def main() -> int:
    on = series("CNY=X")        # USD/CNY onshore
    off = series("CNH=F")       # USD/CNH offshore, a futures series, not spot
    days = sorted(set(on) & set(off))
    if not days:
        raise SystemExit("no overlapping dates between the two rate series")

    print(f"onshore  CNY_X : {len(on):>6} days, {min(on)} to {max(on)}")
    print(f"offshore CNH_F : {len(off):>6} days, {min(off)} to {max(off)}")
    print(f"overlap        : {len(days):>6} days, {days[0]} to {days[-1]}\n")

    # t_ab(cash) in basis points. Positive means offshore renminbi is cheaper
    # per dollar, i.e. the offshore currency is weaker.
    wedge = [(d, 1e4 * math.log(off[d] / on[d])) for d in days]
    vals = sorted(w for _, w in wedge)
    absv = sorted(abs(w) for _, w in wedge)

    def q(v, p):
        return v[min(len(v) - 1, int(p * len(v)))]

    print("t_ab(onshore cash) = 1e4 * log(offshore / onshore), in basis points")
    print(f"  signed    p01 {q(vals,.01):>8.1f}   p25 {q(vals,.25):>8.1f}   "
          f"median {q(vals,.50):>8.1f}   p75 {q(vals,.75):>8.1f}   p99 {q(vals,.99):>8.1f}")
    print(f"  absolute  median {q(absv,.50):>6.1f}   p75 {q(absv,.75):>6.1f}   "
          f"p90 {q(absv,.90):>6.1f}   p99 {q(absv,.99):>6.1f}   max {absv[-1]:>6.1f}")

    print("\n**The gate.** The square is readable on the days its size clears the")
    print("round-trip cost, which is not estimated here but read from the fee tables.")
    print(f"{'cost assumption':>34} {'bp':>6} {'days |wedge| > cost':>22} {'share':>8}")
    for label, c in COST_BP.items():
        n = sum(1 for w in absv if w > c)
        print(f"{label:>34} {c:>6.1f} {n:>22,} {n / len(absv):>8.1%}")

    print("\nby year, so a run of readable days is not mistaken for a readable sample")
    print(f"{'year':>6} {'days':>6} {'median |bp|':>12} {'max |bp|':>10} "
          f"{'share over 43bp':>16}")
    by: dict[str, list[float]] = {}
    for d, w in wedge:
        by.setdefault(d[:4], []).append(abs(w))
    for y in sorted(by):
        v = sorted(by[y])
        print(f"{y:>6} {len(v):>6} {q(v,.50):>12.1f} {v[-1]:>10.1f} "
              f"{sum(1 for x in v if x > 43) / len(v):>16.1%}")

    print("\n**Read this before quoting any of it.**")
    print("  **This is not a square sum and must not be called one.** It is the price")
    print("  gap between two positions, onshore and offshore renminbi. The square on")
    print("  the cash-to-A-share edge equals minus the cost of moving an onshore")
    print("  renminbi position across the class boundary, and **that cost is quoted")
    print("  nowhere**. The number above is the nearest observable proxy for it.")
    print("  CNH_F is a futures series and carries basis, so the level here is not")
    print("  the spot spread. The basis is small against a wedge of this size and it")
    print("  is not zero. A published spot offshore series would replace it.")
    print()
    print("  **On the attribution, scoped to this edge only.** On the currency edge")
    print("  a price difference and a transfer wedge cannot be told apart, because")
    print("  neither is separately quoted. **That is a fact about this edge and not")
    print("  about the carrier.** On the dividend edge they are told apart exactly:")
    print("  the withholding rate applied to each class of holder of the same share")
    print("  is published in the distribution announcement, and a withholding rate")
    print("  is a price term and not a transfer friction. An earlier version of this")
    print("  block said the carrier cannot separate them, full stop. **That was")
    print("  wrong and it was wrong by generalising one edge to the whole graph.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
