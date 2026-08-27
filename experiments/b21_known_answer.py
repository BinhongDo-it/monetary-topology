"""B21 known-answer arm: a class index whose true value is set by statute.

**Why this exists.** Every stage in this repository that reads a class index has
had to build its own known-answer arm to show the machinery reads a non-zero
where one provably exists (B13-3 and B6-10 each constructed one). Here it does
not have to be constructed. On an A+H company's dividend, the same share pays a
different net amount to different classes of holder, the rate for each class is
fixed by published tax notices, and the dates on which the schedule changed are
public. **The true value is legislated, so the measurement error on it is zero.**

**What it is not.** Withholding differing by holder class is not a surprising
empirical finding; everyone knows taxes are agent-specific. The obvious defence
is available and should be stated rather than dodged: prices are scalar and tax
is a separable additive wedge applied afterwards, so the scalar field lives on
the pre-tax price. That defence is real. Its cost is that the pre-tax price is
then **unobservable** and every statement about what a holder actually faces is
non-scalar. **This file supplies a calibration point, not a refutation.**

The quantity, and why the gross amount does not cancel out of it. The class index
on a single dividend is `log((1 - t_a) / (1 - t_b))` and the gross does cancel
there. But section 3 of `b1_setup.md` fixes `w` as a **return over a holding
period**, so what enters the field is the differential weighted by how much of
the return the dividend is:

    class index over one year  ~  (t_b - t_a) * (D / P)

which is the statutory gap times the dividend yield. Both factors are on disk:
the rates below, and the `Dividends` and `Close` columns of the price files.

Usage::

    python experiments/b21_known_answer.py
    python experiments/b21_known_answer.py --check 601088.SS   # one name, printed
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"

# Every rate here has a citation. Nothing is a calibrated constant.
#
#   A share, mainland institution, not QFII and not Connect .... 0
#       China Shenhua 2025 distribution announcement, A-share notice
#   A share, Northbound investor ............................... 0.10
#       same announcement
#   A share, QFII / RQFII ...................................... 0.10
#       same announcement
#   H share, non-resident holder ............................... 0.10
#       standard PRC withholding on H-share dividends
#   H share, mainland individual via Southbound ................ 0.20
#       Caishui [2014] 81 for Shanghai Connect, Caishui [2016] 127 for
#       Shenzhen Connect, extended to 2027-12-31 by Announcement 23 of 2023
RATES = {
    "A_mainland_institution": 0.00,
    "A_northbound": 0.10,
    "A_qfii": 0.10,
    "H_nonresident": 0.10,
    "H_southbound_individual": 0.20,
}

# The pairs of classes that meet on one position. Each is one edge of the agent
# graph at a position both of them can hold.
EDGES = [
    ("A share", "A_mainland_institution", "A_northbound"),
    ("H share", "H_nonresident", "H_southbound_individual"),
]

# Effective dates, so the arm calibrates timing as well as level.
SCHEDULE = [
    ("2014-11-17", "Shanghai Connect opens; Caishui [2014] 81 sets the Southbound rate"),
    ("2016-12-05", "Shenzhen Connect opens; Caishui [2016] 127 extends it"),
    ("2023-01-01", "Announcement 23 of 2023 extends the arrangement to 2027-12-31"),
]


def load(tk: str) -> list[dict]:
    for cand in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if cand.exists():
            return list(csv.DictReader(cand.open(encoding="utf-8")))
    return []


def pairs_on_page() -> list[dict]:
    import re
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
    html = PAGE.read_text(encoding="utf-8")
    row = re.compile(r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
                     r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", re.S)
    seen, out = set(), []
    for m in row.finditer(html):
        name, h, _, a, mkt, _ = m.groups()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": name.strip()[:22],
                    "h": (h[1:] if h.startswith("0") else h) + ".HK",
                    "a": f"{a}.{'SS' if mkt == 'SH' else 'SZ'}"})
    return sorted(out, key=lambda r: r["a"])


def yields(rows: list[dict]) -> dict[str, float]:
    """Dividend paid in a year over the mean close that year. Both on disk."""
    div, px = {}, {}
    for r in rows:
        y = r.get("Date", "")[:4]
        try:
            d = float(r.get("Dividends") or 0)
            c = float(r["Close"])
        except (TypeError, ValueError):
            continue
        if d > 0:
            div[y] = div.get(y, 0.0) + d
        if c > 0:
            px.setdefault(y, []).append(c)
    return {y: div[y] / (sum(px[y]) / len(px[y]))
            for y in div if y in px and px[y]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", help="print one ticker's dividends and stop")
    args = ap.parse_args()

    if args.check:
        rows = load(args.check)
        if not rows:
            return 2
        print(f"{args.check}: {len(rows)} rows")
        print(f"{'date':>12} {'close':>10} {'dividend':>10}")
        for r in rows:
            try:
                d = float(r.get("Dividends") or 0)
            except (TypeError, ValueError):
                continue
            if d > 0:
                print(f"{r['Date'][:10]:>12} {float(r['Close']):>10.3f} {d:>10.4f}")
        return 0

    print("the statutory gap on each agent edge, before any data")
    print(f"{'position':>10} {'class a':>26} {'class b':>26} {'gap pp':>8} "
          f"{'log ratio bp':>13}")
    for pos, ca, cb in EDGES:
        ta, tb = RATES[ca], RATES[cb]
        bp = 1e4 * math.log((1 - ta) / (1 - tb))
        print(f"{pos:>10} {ca:>26} {cb:>26} {100 * (tb - ta):>8.1f} {bp:>13.1f}")
    print("\n  The log ratio is the index on the dividend alone and does not depend")
    print("  on the amount. What reaches the field is that gap weighted by the")
    print("  dividend's share of the holding period return, which does.\n")

    ps = pairs_on_page()
    out = []
    for r in ps:
        ya, yh = yields(load(r["a"])), yields(load(r["h"]))
        for y in sorted(set(ya) & set(yh)):
            out.append((r["name"], r["a"], y, ya[y], yh[y]))
    if not out:
        print("no company has dividends on both legs on disk")
        return 1

    print(f"{len(out)} company-years with a dividend on both legs, "
          f"{len({o[1] for o in out})} companies\n")
    for pos, ca, cb in EDGES:
        gap = RATES[cb] - RATES[ca]
        col = 3 if pos == "A share" else 4
        v = sorted(1e4 * gap * o[col] for o in out)
        print(f"{pos}: class index over one holding year, "
              f"gap {100 * gap:.0f} pp times the yield")
        print(f"    p10 {v[len(v)//10]:>7.1f} bp   median {v[len(v)//2]:>7.1f} bp   "
              f"p90 {v[9*len(v)//10]:>7.1f} bp   max {v[-1]:>7.1f} bp")
    print()
    print("  **The floor against this is zero.** A statutory rate is not measured,")
    print("  so a machine that reads a class index has a target here with no error")
    print("  bar on it, and dated steps to calibrate timing against:")
    for d, why in SCHEDULE:
        print(f"    {d}  {why}")
    print()
    print("  **This is a calibration point and not a refutation.** The defence that")
    print("  price is scalar and tax is a separable wedge is available and real; its")
    print("  cost is that the scalar object is then unobservable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
