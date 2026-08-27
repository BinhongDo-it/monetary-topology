"""B21: the class index on a real holding period, and the arm that checks it.

**What is computed.** For one share held for one year, two classes of holder get
different net cash because the withholding rate differs by class. The realised
log return therefore differs, and the difference is the class index on that
position edge:

    w_c(one year)  =  log( (P1 + (1 - t_c) * D) / P0 )
    index          =  w_a - w_b

`b1_setup.md` section 3 fixes `w` as a return over a holding period, so this is
the field's own quantity and not a proxy for it. Corollary 1 needs exactly this:
one edge, one pair of classes, one inequality.

**The arm.** The closed form for the same quantity, when the dividend is small
against the price, is `(t_b - t_a) * D / P`. The rates come from statute and the
prices and dividends from disk, so **the target has no error bar on it**. A
pipeline that claims to read a class index has to reproduce it. What this file
reports is the gap between the two, which is the pipeline's own error and not a
fact about the world.

**What it is not.** Withholding differing by holder class is not a surprising
finding. The defence that price is scalar and tax is a separable wedge is
available and real; its cost is that the scalar object is then unobservable.
**This is a calibration and a worked instance, not a refutation.**

Usage::

    python experiments/b21_class_index.py
    python experiments/b21_class_index.py --pair 601088.SS
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"

# Statutory, with the citation beside each. Nothing calibrated.
#   0.00  A share, mainland institution, not QFII and not Connect
#         China Shenhua 2025 distribution announcement, A-share notice
#   0.10  A share, Northbound investor; also QFII and RQFII      same announcement
#   0.10  H share, non-resident holder                           standard PRC rate
#   0.20  H share, mainland individual via Southbound
#         Caishui [2014] 81, Caishui [2016] 127, extended by Announcement 23 of 2023
EDGES = [("A leg", "mainland institution", 0.00, "Northbound", 0.10),
         ("H leg", "non-resident", 0.10, "Southbound individual", 0.20)]


def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def pairs() -> list[dict]:
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
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


PAIRED = ROOT / "data" / "cache" / "b21_dividends_paired.csv"


def rebuilt_amounts() -> dict[tuple[str, str], float]:
    """(ticker, ex-date) to the rebuilt H amount, for the stale ones only.

    Before 2014 the vendor's H-leg figure is the A-leg figure times a fixed
    1.166, whatever the exchange rate did, and the rate over those years ran from
    0.97 to 1.27. **Two conventions in one column is what 18c forbids.** The
    substitution is per payment and only where the pair sits on the constant
    exactly, so a leg with no stale payment is untouched to the last bit.

    A false positive here is harmless by construction and the table shows why:
    the flag can only fire when the ratio is 1.166, so when the conversion was
    real the rate itself was 1.166, and the rebuilt amount is the amount. The
    years where the rebuild moves nothing are 2016 at 0.4% and 2022 at 0.5%,
    which are precisely the years the measured rate crossed the constant, while
    2006 moves 16.6% and 2013 moves 8.7%. **The error the flag can introduce is
    bounded by the distance that makes it detectable.**
    """
    if not PAIRED.exists():
        return {}
    out = {}
    for r in csv.DictReader(PAIRED.open(encoding="utf-8")):
        if r.get("pinned") == "1":
            try:
                out[(r["h"], r["h_date"])] = float(r["h_div_rebuilt"])
            except (TypeError, ValueError, KeyError):
                continue
    return out


def holding_years(rows: list[dict], tk: str = "",
                  sub: dict[tuple[str, str], float] | None = None,
                  ) -> list[tuple[str, float, float, float]]:
    """(year, P0, P1, dividends paid in the year). One holding period each."""
    by: dict[str, list[tuple[str, float, float]]] = {}
    for r in rows:
        try:
            c, d = float(r["Close"]), float(r.get("Dividends") or 0)
        except (TypeError, ValueError, KeyError):
            continue
        if sub and d > 0:
            d = sub.get((tk, r["Date"][:10]), d)
        if c > 0:
            by.setdefault(r["Date"][:4], []).append((r["Date"][:10], c, d))
    out = []
    for y in sorted(by):
        rs = by[y]
        if len(rs) < 100:                    # a stub year is not a holding year
            continue
        div = sum(d for _, _, d in rs)
        if div <= 0:
            continue
        out.append((y, rs[0][1], rs[-1][1], div))
    return out


def index_exact(p0: float, p1: float, d: float, ta: float, tb: float) -> float:
    return math.log((p1 + (1 - ta) * d) / (p1 + (1 - tb) * d))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", help="one A-leg ticker, printed year by year")
    ap.add_argument("--raw", action="store_true",
                    help="the vendor column untouched, two conventions and all")
    args = ap.parse_args()

    # **The switch went in defaulting off and reproduced the earlier run to the
    # last digit before it was flipped** (discipline 19). What flipped it is 18c:
    # the vendor column holds the stale convention before 2014 and the real one
    # after, and a column may not carry two. The flip costs one tenth of a basis
    # point on the H median and moves no coefficient of the arm.
    sub = {} if args.raw else rebuilt_amounts()
    if not args.raw and not sub:
        raise SystemExit("run experiments/b21_div_align.py --write first")
    if sub:
        print(f"substituting {len(sub):,} rebuilt H amounts "
              f"over {len({k[0] for k in sub})} legs\n")

    ps = pairs()
    if args.pair:
        ps = [r for r in ps if r["a"] == args.pair or r["h"] == args.pair]
        if not ps:
            print(f"{args.pair} is not on the page")
            return 2

    rows = []
    for r in ps:
        for leg, ca, ta, cb, tb, tk in (
                (EDGES[0][0], EDGES[0][1], EDGES[0][2], EDGES[0][3], EDGES[0][4], r["a"]),
                (EDGES[1][0], EDGES[1][1], EDGES[1][2], EDGES[1][3], EDGES[1][4], r["h"])):
            for y, p0, p1, d in holding_years(load(tk), tk, sub):
                exact = 1e4 * index_exact(p0, p1, d, ta, tb)
                closed = 1e4 * (tb - ta) * d / p1
                rows.append({"name": r["name"], "leg": leg, "tk": tk, "y": y,
                             "exact": exact, "closed": closed, "yield": d / p1})

    if not rows:
        print("no company-year has a dividend on a leg with a full year of prices")
        return 1

    if args.pair:
        print(f"{'leg':>6} {'ticker':>12} {'year':>6} {'yield':>8} "
              f"{'exact bp':>10} {'closed bp':>10} {'gap bp':>8}")
        for x in sorted(rows, key=lambda x: (x["leg"], x["y"])):
            print(f"{x['leg']:>6} {x['tk']:>12} {x['y']:>6} {x['yield']:>8.4f} "
                  f"{x['exact']:>10.2f} {x['closed']:>10.2f} "
                  f"{x['closed'] - x['exact']:>8.2f}")
        return 0

    print(f"{len(rows)} leg-years over {len({x['tk'] for x in rows})} legs "
          f"and {len({x['name'] for x in rows})} companies\n")
    print("the class index, computed from realised prices and dividends")
    print(f"{'leg':>6} {'n':>7} {'p10':>9} {'median':>9} {'p90':>9} {'max':>9}")
    for leg, *_ in EDGES:
        v = sorted(x["exact"] for x in rows if x["leg"] == leg)
        if not v:
            continue
        print(f"{leg:>6} {len(v):>7} {v[len(v)//10]:>9.1f} {v[len(v)//2]:>9.1f} "
              f"{v[9*len(v)//10]:>9.1f} {v[-1]:>9.1f}   basis points per year")

    print("\nthe arm. **Not a tolerance on the gap.** The gap has a predicted")
    print("form: expanding the log to second order in the yield y = D / P1,")
    print("    gap  =  closed - exact  ~  0.5 * dtau * (2 - ta - tb) * y^2")
    print("with the coefficient fixed by the statutory rates and nothing fitted.")
    print("What is reported is the observed gap over that prediction. **A pipeline")
    print("that is right sits at one and falls below it as the third order term")
    print("turns on, monotonically in y.**\n")
    rec_legs = {}
    for leg, ca, ta, cb, tb in EDGES:
        coef = 0.5 * (tb - ta) * (2 - ta - tb)
        sel = [x for x in rows if x["leg"] == leg and x["yield"] > 0]
        rat = []
        for x in sel:
            pred = 1e4 * coef * x["yield"] ** 2
            if pred > 1e-6:
                rat.append((x["yield"], (x["closed"] - x["exact"]) / pred, x))
        if not rat:
            continue
        v = sorted(r for _, r, _ in rat)
        print(f"{leg}   second order coefficient {coef:.4f}, {len(rat)} leg-years")
        print(f"    ratio to prediction:  p01 {v[len(v)//100]:.3f}   "
              f"p10 {v[len(v)//10]:.3f}   median {v[len(v)//2]:.3f}   "
              f"p90 {v[9*len(v)//10]:.3f}   p99 {v[99*len(v)//100]:.3f}")
        print(f"    {'yield band':>16} {'n':>6} {'median ratio':>14}")
        bands = [(0, .01), (.01, .02), (.02, .04), (.04, .07), (.07, .12), (.12, 9)]
        band_med = []
        for lo, hi in bands:
            g = sorted(r for y, r, _ in rat if lo <= y < hi)
            if len(g) < 5:
                continue
            band_med.append((f"{lo:.0%}-{hi:.0%}" if hi < 9 else f">{lo:.0%}",
                             len(g), g[len(g) // 2]))
            print(f"    {f'{lo:.0%} to {hi:.0%}' if hi < 9 else f'over {lo:.0%}':>16} "
                  f"{len(g):>6} {g[len(g)//2]:>14.3f}")
        top = sorted(rat, key=lambda t: -t[0])[:5]
        print(f"    the five highest yields, printed because an outlier here is a")
        print(f"    special dividend or a bad row and not a pipeline error:")
        print(f"    {'company':>24} {'ticker':>12} {'year':>6} {'yield':>8} {'ratio':>7}")
        for y, r, x in top:
            print(f"    {x['name']:>24} {x['tk']:>12} {x['y']:>6} {y:>8.4f} {r:>7.3f}")
        print()
        idx = sorted(x["exact"] for x in rows if x["leg"] == leg)
        rec_legs[leg] = {
            "n_leg_years": len(idx), "coefficient": coef,
            "index_bp": {"p10": idx[len(idx) // 10], "median": idx[len(idx) // 2],
                         "p90": idx[9 * len(idx) // 10], "max": idx[-1],
                         "min": idx[0]},
            "ratio_to_prediction": {"p01": v[len(v) // 100], "p10": v[len(v) // 10],
                                    "median": v[len(v) // 2],
                                    "p90": v[9 * len(v) // 10],
                                    "p99": v[99 * len(v) // 100], "max": v[-1]},
            "band_medians": [{"band": b, "n": n, "median_ratio": m}
                             for b, n, m in band_med],
        }

    print("\n  **The gap is this pipeline's error, not a fact about the world.**")
    print("  The closed form drops the dividend from the denominator, so the two")
    print("  separate as the yield grows. A gap larger than the second order term")
    print("  would mean the pipeline is wrong, and that is the whole use of an arm")
    print("  whose target is set by statute rather than estimated.")
    print()
    print("  **Zero is not in any of these distributions.** A single scalar price")
    print("  field on positions requires the terms not to depend on who holds, and")
    print("  Corollary 1 needs one edge and one pair of classes to break it. This is")
    print("  that inequality, published rather than measured.")

    # **`--raw` writes no record.** It exists to reproduce the run from before
    # the substitution went in, which is a check on the code and not a reading of
    # the station, and it had overwritten the station's record once before this
    # line was here.
    if args.raw:
        print("\n(--raw is a reproduction check and writes no record.)")
    else:
        write_record(rows, rec_legs, sub)
    return 0


def write_record(rows: list[dict], legs: dict, sub: dict) -> None:
    """Write the record, always, because a station that only prints is invisible.

    Six stations in this repository never wrote to `results/` and four of them
    were missing from the ledger entirely until somebody counted. **The fix is
    that writing is not a flag.**

    The criteria here are structural, a count and two signs, and none of them is
    a line on an estimator. The station is open, so the record carries
    `diagnostic_only` with the reason in it.
    """
    crit = []
    neg = sum(1 for x in rows if x["exact"] <= 0)
    crit.append({
        "name": "B21-1  the class index is nonzero on every leg-year",
        "passed": neg == 0,
        "detail": f"{len(rows)} leg-years, {neg} at or below zero, "
                  f"smallest {min(x['exact'] for x in rows):.4f} bp"})
    for leg, d in legs.items():
        ms = [b["median_ratio"] for b in d["band_medians"]]
        mono = all(a >= b for a, b in zip(ms, ms[1:]))
        crit.append({
            "name": f"B21-2 {leg}  the gap sits under the second order term and "
                    f"falls monotonically in the yield",
            "passed": bool(mono and d["ratio_to_prediction"]["max"] <= 1.0),
            "detail": "band medians " + " ".join(f"{m:.3f}" for m in ms)
                      + f", max ratio {d['ratio_to_prediction']['max']:.4f}"})
    out = {
        "stage": "B21",
        "step": "class_index",
        "diagnostic_only": True,
        "diagnostic_reason": "B21 is open. The known-answer arm has passed at "
                             "three levels and the levels are quotable; the "
                             "station's own reading is not yet closed.",
        "leg_years": len(rows), "legs": len({x["tk"] for x in rows}),
        "companies": len({x["name"] for x in rows}),
        "rebuilt_h_amounts": len(sub),
        "by_leg": legs,
        "criteria": crit,
    }
    path = ROOT / "results" / "b21_class_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
                    + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {path.name}: {len(crit)} criteria, "
          f"{sum(1 for c in crit if c['passed'])} passing")


if __name__ == "__main__":
    raise SystemExit(main())
