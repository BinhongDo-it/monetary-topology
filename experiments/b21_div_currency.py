"""B21 input check: is each leg's dividend in that leg's own currency?

**The check only exists because the carrier is a pair.** An A+H company declares
one dividend per share, in renminbi. The A holder receives that number of yuan.
The H holder receives the same number converted to Hong Kong dollars, which is
the same amount divided by the CNY-per-HKD rate, so **about 1.10 times the
numeric value**. The two legs' reported dividends therefore have a predicted
ratio, and it is not one.

    H dividend / A dividend  ~  1 / e     with e = CNY per HKD, near 0.91

- A ratio near **1.10** means each leg carries its own currency and the yields
  computed from them are right.
- A ratio near **1.00** means one leg's figure is in the other's currency, and
  every yield on that leg is off by ten per cent.

**A ten per cent error on the yield is a twenty per cent error on the second
order term** that the known-answer arm reads, so this has to be settled before
the arm's readings are quoted anywhere.

The same comparison also prices the special dividends. `y = D / P1` above forty
per cent on one leg-year looks like a bad row until the other leg shows the same
payout, at which point it is a payout.

Usage::

    python experiments/b21_div_currency.py
    python experiments/b21_div_currency.py --name COSCO
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"

# CNY per HKD over the sample, roughly. Used only to say which of two very
# different predictions the data sits on, never to correct anything.
E_LOW, E_HIGH = 0.80, 0.95


def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def pairs() -> list[dict]:
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


def annual(tk: str) -> dict[str, tuple[float, float]]:
    """year -> (dividends summed, last close)."""
    div, last = {}, {}
    for r in load(tk):
        y = r.get("Date", "")[:4]
        try:
            d, c = float(r.get("Dividends") or 0), float(r["Close"])
        except (TypeError, ValueError, KeyError):
            continue
        if d > 0:
            div[y] = div.get(y, 0.0) + d
        if c > 0:
            last[y] = c
    return {y: (div[y], last[y]) for y in div if y in last}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", help="print one company by name substring")
    args = ap.parse_args()
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")

    ps = pairs()
    if args.name:
        ps = [r for r in ps if args.name.upper() in r["name"].upper()]
        if not ps:
            print("no company matches")
            return 2

    rows = []
    for r in ps:
        a, h = annual(r["a"]), annual(r["h"])
        for y in sorted(set(a) & set(h)):
            da, pa = a[y]
            dh, ph = h[y]
            if da > 0 and dh > 0:
                rows.append({"name": r["name"], "y": y, "a": r["a"], "h": r["h"],
                             "da": da, "dh": dh, "ratio": dh / da,
                             "ya": da / pa, "yh": dh / ph})
    if not rows:
        print("no company-year has a dividend on both legs")
        return 1

    if args.name:
        print(f"{'company':>22} {'year':>6} {'A div':>9} {'H div':>9} {'H/A':>7} "
              f"{'A yield':>9} {'H yield':>9}")
        for x in sorted(rows, key=lambda x: (x["name"], x["y"])):
            print(f"{x['name']:>22} {x['y']:>6} {x['da']:>9.4f} {x['dh']:>9.4f} "
                  f"{x['ratio']:>7.3f} {x['ya']:>9.4f} {x['yh']:>9.4f}")
        return 0

    v = sorted(x["ratio"] for x in rows)
    print(f"{len(rows)} company-years with a dividend on both legs, "
          f"{len({x['name'] for x in rows})} companies\n")
    print("H dividend over A dividend, same company, same year")
    print(f"  p10 {v[len(v)//10]:.3f}   p25 {v[len(v)//4]:.3f}   "
          f"median {v[len(v)//2]:.3f}   p75 {v[3*len(v)//4]:.3f}   "
          f"p90 {v[9*len(v)//10]:.3f}")
    print(f"\n  predicted if each leg is in its own currency : "
          f"{1/E_HIGH:.2f} to {1/E_LOW:.2f}")
    print(f"  predicted if both are in renminbi            : 1.00")
    med = statistics.median(v)
    inband = sum(1 for r in v if 1 / E_HIGH <= r <= 1 / E_LOW)
    near1 = sum(1 for r in v if 0.97 <= r <= 1.03)
    print(f"\n  in the own-currency band : {inband:>6,} of {len(v):,}  "
          f"({inband/len(v):.1%})")
    print(f"  within 3% of one         : {near1:>6,} of {len(v):,}  "
          f"({near1/len(v):.1%})")
    print(f"  median                   : {med:.3f}")
    print()
    if 1 / E_HIGH <= med <= 1 / E_LOW:
        print("  **Own currency on each leg.** The yields the arm reads are in the")
        print("  right units and no correction is called for.")
    elif 0.97 <= med <= 1.03:
        print("  **Both legs in one currency.** Every H-leg yield is out by the")
        print("  exchange rate and the arm's second order term is out by twice that.")
    else:
        print("  **Neither prediction.** Print the object before assuming which.")

    print("\n  the ten company-years with the largest A-leg yield, both legs shown,")
    print("  because a payout that appears on both legs is a payout and not a bad row")
    print(f"{'company':>22} {'year':>6} {'A yield':>9} {'H yield':>9} {'H/A div':>9}")
    for x in sorted(rows, key=lambda x: -x["ya"])[:10]:
        print(f"{x['name']:>22} {x['y']:>6} {x['ya']:>9.4f} {x['yh']:>9.4f} "
              f"{x['ratio']:>9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
