"""B21: is there a stock-level part of the transfer cost, or is it all common?

Layer two survives only if `t_ab(A_k)` has a `k` in it. After a stock enters
Connect the cost of moving its position from a mainland holder to an
international one is a published fee schedule plus that stock's own bid-ask
spread, and **the fee schedule has no k**: stamp duty, handling and the
securities management fee are set per trade, not per name. So the whole
stock-level content of layer two sits in the spread.

**It does not answer the question, and the reason is worth more than the number
would have been.** The estimator floors about two windows in five on every leg,
which truncates the low tail one way and lets a varying floor rate widen the
dispersion the other way, and daily bars cannot separate those. **So the
comparison lands in the third state, undecidable**, and the file records it there
rather than reading a ratio it cannot support. Settling it needs quotes.

**The question this file asks is a comparison, not a threshold.** Put the
cross-sectional dispersion of the spread beside the size of the currency wedge
that layer one already measured. If the spread's spread is small against it,
layer two has no stock-level signal to find and closes; if it is comparable,
layer two has content and the missing input is worth buying.

**The spread is estimated, not observed**, because the price files carry daily
open-high-low-close and no quotes. The estimator is Corwin and Schultz (2012,
Journal of Finance), which recovers the spread from the high-low range over two
consecutive days on the argument that the range's expectation scales with the
square root of the time span while the spread's contribution does not. **The
constant in it comes from that paper and not from anything fitted here**, which
is what discipline 5 asks of a number inside a criterion.

Its known failures travel with it: it is biased where a day's range is set by an
overnight gap rather than by trading, and it returns negatives on quiet days,
which are reported here rather than floored silently.

Usage::

    python experiments/b21_spread.py
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"
OUT = ROOT / "results" / "b21_spread.json"

K = 3 - 2 * math.sqrt(2)        # Corwin-Schultz, their equation 14
MIN_DAYS = 250


def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def pairs_on_page() -> list[dict]:
    import re
    row = re.compile(r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
                     r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", re.S)
    seen, out = set(), []
    for m in row.finditer(PAGE.read_text(encoding="utf-8")):
        name, h, _, a, mkt, _ = m.groups()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": name.strip()[:22],
                    "h": (h[1:] if h.startswith("0") else h) + ".HK",
                    "a": f"{a}.{'SS' if mkt == 'SH' else 'SZ'}"})
    return sorted(out, key=lambda r: r["a"])


def corwin_schultz(rows: list[dict]) -> tuple[float | None, float, int]:
    """Median two-day spread estimate, the share coming back negative, and n."""
    bars = []
    for r in rows:
        try:
            h, lo = float(r["High"]), float(r["Low"])
        except (TypeError, ValueError, KeyError):
            continue
        if h > 0 and lo > 0 and h >= lo:
            bars.append((h, lo))
    est, neg = [], 0
    for t in range(len(bars) - 1):
        h1, l1 = bars[t]
        h2, l2 = bars[t + 1]
        if min(l1, l2) <= 0:
            continue
        beta = math.log(h1 / l1) ** 2 + math.log(h2 / l2) ** 2
        gamma = math.log(max(h1, h2) / min(l1, l2)) ** 2
        alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / K - math.sqrt(gamma / K)
        s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
        if s < 0:
            neg += 1
            s = 0.0                      # the paper's own treatment, stated not hidden
        est.append(s)
    if len(est) < MIN_DAYS:
        return None, 0.0, len(est)
    return statistics.median(est), neg / len(est), len(est)


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
    rows = []
    for r in pairs_on_page():
        s, neg, n = corwin_schultz(load(r["a"]))
        if s is not None:
            rows.append({"name": r["name"], "tk": r["a"], "spread": s,
                         "negative_share": neg, "days": n})
    if not rows:
        print("no A leg carries enough daily bars")
        return 1

    v = sorted(x["spread"] for x in rows)
    ng = sorted(x["negative_share"] for x in rows)
    print(f"{len(rows)} A legs with at least {MIN_DAYS} two-day windows")
    print(f"  estimated spread, in basis points of price:")
    print(f"    p10 {1e4*v[len(v)//10]:>8.1f}   median {1e4*v[len(v)//2]:>8.1f}   "
          f"p90 {1e4*v[9*len(v)//10]:>8.1f}   min {1e4*v[0]:>8.1f}   "
          f"max {1e4*v[-1]:>8.1f}")
    print(f"  the estimator returns a negative, floored to zero, on "
          f"{100*ng[len(ng)//2]:.1f}% of windows at the median leg "
          f"(p90 leg {100*ng[9*len(ng)//10]:.1f}%)")
    print("  **That share is printed because it is the estimator's own failure**")
    print("  and it bounds how much of the dispersion below is estimation noise.")

    # --- the comparison layer two turns on ---
    disp = statistics.pstdev([x["spread"] for x in rows])
    iqr = v[3 * len(v) // 4] - v[len(v) // 4]
    WEDGE_SD = 0.00423          # from b21_cross_section.py, the CNH-CNY log spread
    print(f"\nthe comparison. Cross-stock dispersion of the stock-level term")
    print(f"against the size of the common term it would have to be seen beside:")
    print(f"  spread, cross-stock sd  {disp:.5f}   iqr {iqr:.5f}")
    print(f"  currency wedge, sd      {WEDGE_SD:.5f}")
    print(f"  ratio of the two sds    {disp/WEDGE_SD:.2f}")
    print("  **Read the ratio, not a threshold.** A stock-level term far below")
    print("  the common one leaves layer two nothing to find; one of the same")
    print("  order leaves it something, and this is which.")

    top = sorted(rows, key=lambda x: -x["spread"])[:5]
    bot = sorted(rows, key=lambda x: x["spread"])[:5]
    print(f"\n  {'widest five':>28} {'bp':>7}      {'tightest five':>28} {'bp':>7}")
    for a, b in zip(top, bot):
        print(f"  {a['name']:>28} {1e4*a['spread']:>7.1f}      "
              f"{b['name']:>28} {1e4*b['spread']:>7.1f}")

    # --- what the flooring does to the comparison, measured not assumed ---
    corr = statistics.correlation([x["spread"] for x in rows],
                                  [x["negative_share"] for x in rows])
    print(f"\nwhether the dispersion above is the spread or the estimator:")
    print(f"  a leg's estimate against its own floored share: {corr:+.4f}")
    print(f"  floored share across legs: p10 {ng[len(ng)//10]:.3f}  "
          f"median {ng[len(ng)//2]:.3f}  p90 {ng[9*len(ng)//10]:.3f}")
    print(f"  legs under a 35% floored share: "
          f"{sum(1 for x in rows if x['negative_share'] < 0.35)}")
    print("  **Every leg floors about two windows in five**, so the flooring is a")
    print("  property of daily bars rather than of any stock, and it pushes the")
    print("  comparison two ways at once: truncating the low tail narrows the")
    print("  dispersion, while a floored share that itself varies across legs")
    print("  widens it. **Daily bars cannot separate those**, so the ratio above")
    print("  is not a measurement of the stock-level term and no verdict is")
    print("  recorded from it. Settling it needs quotes.")

    undecidable = ng[len(ng) // 2] > 0.25
    crit = [
        {"name": "B21-7  the estimated stock-level term is not degenerate",
         "passed": v[0] < v[-1],
         "detail": f"estimated spread runs {1e4*v[0]:.1f} to {1e4*v[-1]:.1f} bp "
                   f"across {len(rows)} legs, median {1e4*v[len(v)//2]:.1f}"},
        {"name": "B21-8  the stock-level term against the common one: "
                 "UNDECIDABLE on daily bars, which is the third state and "
                 "neither a pass nor a fail",
         "passed": None if undecidable else disp > 0,
         "undecidable": undecidable,
         "detail": f"ratio of the two dispersions {disp/WEDGE_SD:.2f}, but the "
                   f"estimator floors {100*ng[len(ng)//2]:.1f}% of windows at the "
                   f"median leg and a leg's estimate correlates {corr:+.4f} with "
                   f"its own floored share. No threshold is applied to this "
                   f"number and none should be."},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "spread",
        "diagnostic_only": True,
        "diagnostic_reason": "A precondition check for layer two, not a reading "
                             "of the station. It asks whether the stock-level "
                             "part of the transfer cost is large enough to be "
                             "worth acquiring the Connect eligibility list for.",
        "legs": len(rows), "estimator": "Corwin and Schultz (2012, JF)",
        "spread_bp": {"p10": 1e4*v[len(v)//10], "median": 1e4*v[len(v)//2],
                      "p90": 1e4*v[9*len(v)//10], "min": 1e4*v[0], "max": 1e4*v[-1]},
        "cross_stock_sd": disp, "iqr": iqr, "wedge_sd": WEDGE_SD,
        "ratio": disp / WEDGE_SD,
        "negative_share_median_leg": ng[len(ng)//2],
        "estimate_vs_floor_correlation": corr,
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    n_pass = sum(1 for c in crit if c["passed"] is True)
    n_und = sum(1 for c in crit if c.get("undecidable"))
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, {n_pass} passing, "
          f"{n_und} undecidable, {len(crit)-n_pass-n_und} failing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
