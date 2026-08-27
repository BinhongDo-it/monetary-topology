"""B21: pair each leg's dividend with the other leg's, and rebuild the stale ones.

Two defects in the calendar-year aggregation this replaces, both found by
printing objects rather than by a threshold.

**One: the ex-dates do not line up, so a calendar year is the wrong bucket.**
Anhui Expressway pays H holders two to three months before A holders. In 2006 the
A leg carries two payments and the H leg one, and summing by year pairs the H
payment with the wrong A payment. 36 of 1,603 company-years came out with an
H-over-A ratio below one for this reason, and none of them is a currency error.
**Matching is by proximity of ex-date, and a payment that finds no partner is
reported rather than silently dropped into a year.**

**Two: before 2014 the H figure is the A figure times a fixed 1.166.** Six to
eight tenths of the company-years up to 2013 sit at exactly that number while the
real CNY-per-HKD rate moved from 0.975 to 1.263 over the same span, so the
constant is not an exchange rate. From 2014 the constant vanishes and the median
tracks the measured rate to within a few per cent. **Two conventions in one
column is what discipline 18c forbids**, and the older one is rebuilt here from
the A-leg amount and the rate on the A-leg ex-date, both of which are on disk.

**What this does not touch.** The known-answer arm's verdict is insensitive to a
yield error, because its ratio uses the same yield in the numerator and the
denominator and they cancel to first order. **What is corrected is the level of
the H-leg class index before 2014, not the arm.**

Usage::

    python experiments/b21_div_align.py                 # report, write nothing
    python experiments/b21_div_align.py --write         # write the rebuilt table
    python experiments/b21_div_align.py --name ANHUI    # one company, every pair
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"
OUT = ROOT / "data" / "cache" / "b21_dividends_paired.csv"

WINDOW = 200          # days either side an H payment may sit from its A payment
PINNED = 1.166        # the stale constant, identified not assumed
PIN_TOL = 0.002       # an exact-match tolerance on a constant, not a judgment
SPAN_BACK = 90        # the conversion rate is fixed before either ex-date

_FX_KEYS: dict[int, list[str]] = {}

# **There is no band here, because the data would not supply one.** The first
# version asked whether an implied ratio was "close enough" to the measured rate
# and tried three answers: a fixed 0.90-1.40, then eight per cent relative, then
# a percentile of the drift the rate itself shows over the gap. All three are
# lines drawn on an estimator, which discipline 11 forbids, and the reason the
# ban is right showed up when the excess over the rate's own range was sorted and
# printed: 0.013 0.015 0.020 0.027 0.035 0.046 0.059 0.082 0.110 0.124 0.187,
# on up to 9.14. **A continuous tail has no place to cut**, so every cut is the
# analyst's and not the data's.
#
# What the band was being asked to do was repair a matching rule, not classify a
# pair. Anhui Expressway pays H holders two months ahead of A holders, and in 2006
# the A leg carries two payments to the H leg's one. Nearest-date hands the single
# H payment to the March A payment at an implied 0.901, and that is not a
# mislabelled row, it is **a theft**: the July payment is the one whose partner
# sits at exactly 1.166 and therefore the one that needed rebuilding, and it goes
# unmatched because its partner was already taken.
#
# So the ordering carries the work. Candidates are scored by how near the implied
# ratio comes to something a ratio can be, either the stale constant or the range
# the rate actually took, and the best-scoring pair anywhere in the company is
# settled first. **Anhui's July pair scores zero and is settled before the March
# candidate is ever considered.** Date proximity breaks ties and decides nothing
# else. No pair is dropped by a threshold; each carries its score into the table
# and the reader cuts where the reading requires.
def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def divs(tk: str) -> list[tuple[str, float]]:
    out = []
    for r in load(tk):
        try:
            v = float(r.get("Dividends") or 0)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out.append((r["Date"][:10], v))
    return sorted(out)


_SPLITS: dict[str, list[tuple[str, float]]] = {}


def splits(tk: str) -> list[tuple[str, float]]:
    if tk in _SPLITS:
        return _SPLITS[tk]
    out = []
    for r in load(tk):
        for k in r:
            if "split" in k.lower():
                try:
                    v = float(r[k] or 0)
                except (TypeError, ValueError):
                    v = 0.0
                if v not in (0.0, 1.0):
                    out.append((r["Date"][:10], v))
    _SPLITS[tk] = out
    return out


def undo_adjust(tk: str, day: str) -> float:
    """What the vendor divided this payment by: every split after it.

    **The dividend column is adjusted for splits that came later**, and the two
    legs of a dual listing do not always carry the same splits. Shanghai
    Petrochemical's A leg carries one its H leg does not, so the ratio of the two
    reported amounts is the ratio the company declared times 1.5, and it reads
    1.749 where the truth is 1.166. Multiplying each amount back by its own
    factor puts the comparison on declared amounts, which is the only basis on
    which a cross-leg ratio means anything.

    **Within one leg this cancels and cannot matter.** The class index divides a
    dividend by a price and both carry the same factor, so it is invariant here
    by algebra rather than by measurement.

    **A split on the payment's own day counts**, which was settled against the
    published declarations rather than assumed. Chinese cash dividends are
    declared per ten shares to two or three decimals, so undoing the adjustment
    correctly puts the result on that grid and undoing it wrongly does not. Of
    the 238 payments that fall on a split date, counting the same-day split puts
    209 on the grid and excluding it puts 134. **An earlier test of the same
    question against the 1.166 constant separated the two conventions by a single
    pair and settled nothing**, because a constant that 300 pairs already sit on
    is not sensitive to a factor of 1.2 in 20 of them.
    """
    return math.prod(v for d, v in splits(tk) if d >= day)


def closes(tk: str) -> dict[str, float]:
    out = {}
    for r in load(tk):
        try:
            c = float(r["Close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c > 0:
            out[r["Date"][:10]] = c
    return out


def fx_daily() -> dict[str, float]:
    """**HKD per CNY**, from the two rate series already on disk.

    The direction is fixed here and inverted nowhere else. The first version
    returned CNY per HKD and left each caller to invert it, and one of the two
    callers did while the other did not, so the test compared a HKD-per-CNY
    ratio against a CNY-per-HKD rate and rejected 1,515 correct pairs out of
    1,840. **The two spellings were both defensible and that is the whole
    problem**, discipline 22's shape: nothing in the program can tell which way
    a bare float points, so the direction belongs in one place with a name.
    """
    cny, hkd = closes("CNY=X"), closes("HKD=X")
    return {d: hkd[d] / cny[d] for d in cny.keys() & hkd.keys() if cny[d] > 0}


def _keys(fx: dict[str, float]) -> list[str]:
    k = _FX_KEYS.get(id(fx))
    if k is None:
        k = _FX_KEYS[id(fx)] = sorted(fx)
    return k


def nearest(fx: dict[str, float], day: str) -> float | None:
    """**HKD per CNY** on or nearest to `day`, within ten days, else None.

    Bisect over a cached sorted key list. The first version scanned the whole
    series on every call and the call sat inside the candidate loop, which is
    thirty candidates times five thousand rate days per A payment. That is the
    same shape as the loop in discipline 13: **the cost was never multiplied out
    before it was written**, and here it is four hundred million comparisons for
    an answer that depends only on the A date.
    """
    keys = _keys(fx)
    if not keys:
        return None
    i = bisect.bisect_left(keys, day)
    best, gap = None, 10**9
    for j in (i - 1, i, i + 1):
        if 0 <= j < len(keys):
            g = abs((dt.date.fromisoformat(keys[j])
                     - dt.date.fromisoformat(day)).days)
            if g < gap:
                best, gap = fx[keys[j]], g
    return best if gap <= 10 else None


def pairs_on_page() -> list[dict]:
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


def span(day_a: str, day_h: str, fx: dict[str, float]) -> tuple[float, float] | None:
    """The range the rate took over the two ex-dates, reaching back before both.

    A company fixes its conversion rate when the board resolves or the meeting
    approves, which is weeks to months ahead of either ex-date, so the range that
    can contain the rate it used starts before the earlier of the two. Reaching
    back ninety days puts 80.8% of unambiguous pairs inside the range outright,
    against 40.4% for the bare interval between the ex-dates.
    """
    keys = _keys(fx)
    if not keys:
        return None
    lo, hi = sorted((day_a, day_h))
    lo = (dt.date.fromisoformat(lo) - dt.timedelta(days=SPAN_BACK)).isoformat()
    i = max(0, bisect.bisect_left(keys, lo) - 3)
    j = min(len(keys), bisect.bisect_right(keys, hi) + 3)
    v = [fx[k] for k in keys[i:j]]
    return (min(v), max(v)) if v else None


def score(av: float, hv: float, rng: tuple[float, float] | None) -> float:
    """How far this ratio is from anything a ratio between these legs can be.

    Zero for the stale constant and zero for any value the rate reached over the
    span. **This is a distance, not a verdict.** Nothing in this file compares it
    with a cutoff, and the one number that does decide something, the rebuild
    flag, is an exact match on the constant rather than a band.
    """
    if av <= 0 or hv <= 0:
        return float("inf")
    r = hv / av
    best = abs(r / PINNED - 1)
    if rng is not None:
        lo, hi = rng
        best = min(best, 0.0 if lo <= r <= hi
                   else (r / hi - 1 if r > hi else lo / r - 1))
    return best


def match(da: list, dh: list, fx: dict[str, float],
          tk_a: str = "", tk_h: str = "") -> tuple[list, list, list]:
    """Settle the best-agreeing pair in the company first, then the next.

    Nearest-date is the wrong order because it lets a payment be taken by a
    partner that agrees with it badly, before the partner that agrees with it
    exactly has been considered. Sorting every candidate in the company by score
    and settling from the top removes that, and it removes it **without a
    threshold**: Anhui's July pair scores zero and is gone from the pool before
    the March candidate at 0.901 comes up at all.
    """
    fa = [undo_adjust(tk_a, d) for d, _ in da]
    fh = [undo_adjust(tk_h, d) for d, _ in dh]
    cand = []
    for i, (ad, av) in enumerate(da):
        a0 = dt.date.fromisoformat(ad)
        for j, (hd, hv) in enumerate(dh):
            g = abs((dt.date.fromisoformat(hd) - a0).days)
            if g <= WINDOW:
                cand.append((score(av * fa[i], hv * fh[j], span(ad, hd, fx)),
                             g, i, j))
    cand.sort()
    ua, uh, got = set(), set(), []
    for sc, g, i, j in cand:
        if i in ua or j in uh:
            continue
        ua.add(i)
        uh.add(j)
        got.append((da[i][0], da[i][1], dh[j][0], dh[j][1], g, sc,
                    fa[i], fh[j]))
    got.sort()
    lone_a = [x for i, x in enumerate(da) if i not in ua]
    lone_h = [x for j, x in enumerate(dh) if j not in uh]
    return got, lone_a, lone_h


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--name")
    args = ap.parse_args()
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")

    fx = fx_daily()
    ps = pairs_on_page()
    if args.name:
        ps = [r for r in ps if args.name.upper() in r["name"].upper()]

    rows, n_lone_a, n_lone_h = [], 0, 0
    for r in ps:
        got, la, lh = match(divs(r["a"]), divs(r["h"]), fx, r["a"], r["h"])
        n_lone_a += len(la)
        n_lone_h += len(lh)
        for ad, av, hd, hv, gap, sc, fa1, fh1 in got:
            rt = nearest(fx, ad)
            imp = (hv * fh1) / (av * fa1)     # declared amounts, not adjusted ones
            pin = abs(imp - PINNED) < PIN_TOL
            rows.append({"name": r["name"], "a": r["a"], "h": r["h"],
                         "a_date": ad, "a_div": av, "h_date": hd, "h_div": hv,
                         "gap_days": gap, "implied": imp, "score": round(sc, 6),
                         "hkd_per_cny": rt if rt else "",
                         "pinned": int(pin),
                         "split_a": fa1, "split_h": fh1,
                         "h_div_rebuilt": (av * fa1 * rt / fh1)
                                          if (pin and rt) else hv})

    if args.name:
        print(f"{'company':>22} {'A date':>11} {'A div':>9} {'H date':>11} "
              f"{'H div':>9} {'days':>5} {'implied':>8} {'rate':>7} {'score':>8} "
              f"{'pin':>4} {'rebuilt':>9}")
        for x in rows:
            rt = f"{x['hkd_per_cny']:.3f}" if x["hkd_per_cny"] != "" else "-"
            print(f"{x['name']:>22} {x['a_date']:>11} {x['a_div']:>9.4f} "
                  f"{x['h_date']:>11} {x['h_div']:>9.4f} {x['gap_days']:>5} "
                  f"{x['implied']:>8.3f} {rt:>7} {x['score']:>8.3f} "
                  f"{x['pinned']:>4} {x['h_div_rebuilt']:>9.4f}")
        return 0

    print(f"{len(rows):,} matched dividend pairs over "
          f"{len({x['a'] for x in rows})} companies")
    print(f"  unmatched on the A leg: {n_lone_a:,}   on the H leg: {n_lone_h:,}")
    print("  Unmatched payments are reported, not folded into a year. **No pair")
    print("  is dropped for its score**, which is carried in the table instead.\n")

    sc = sorted(x["score"] for x in rows)
    n = len(sc)
    print("score, the distance from the nearest thing this ratio could be:")
    print(f"  exactly zero {sum(1 for v in sc if v == 0)/n:>6.1%}   "
          + "   ".join(f"p{q} {sc[int(q/100*n)]:.3f}" for q in (50, 80, 90, 95, 99))
          + f"   max {sc[-1]:.2f}")
    print("  **The tail is continuous, so this file cuts it nowhere.** A reading")
    print("  that needs a clean subset takes the column and cuts it itself.\n")

    worst = sorted(rows, key=lambda x: -x["score"])[:12]
    print("  the twelve furthest, named because the cause is not determined here:")
    print(f"  {'company':>22} {'A date':>11} {'A div':>9} {'H date':>11} "
          f"{'H div':>9} {'days':>5} {'implied':>8} {'score':>8}")
    for x in worst:
        print(f"  {x['name']:>22} {x['a_date']:>11} {x['a_div']:>9.4f} "
              f"{x['h_date']:>11} {x['h_div']:>9.4f} {x['gap_days']:>5} "
              f"{x['implied']:>8.3f} {x['score']:>8.2f}")
    print()

    g = sorted(x["gap_days"] for x in rows)
    print(f"days between the two ex-dates: p10 {g[len(g)//10]}  "
          f"median {g[len(g)//2]}  p90 {g[9*len(g)//10]}  max {g[-1]}")

    pin = [x for x in rows if x["pinned"]]
    print(f"\npairs pinned at exactly {PINNED}: {len(pin):,} of {len(rows):,} "
          f"({len(pin)/len(rows):.1%})")
    print("  **This flag is an exact match on a constant, not a band**, and it is")
    print("  the only thing in this file that decides anything.")
    by = {}
    for x in rows:
        by.setdefault(x["a_date"][:4], []).append(x["pinned"])
    print(f"{'year':>6} {'pairs':>7} {'pinned':>8} {'share':>8}")
    for y in sorted(by):
        v = by[y]
        print(f"{y:>6} {len(v):>7} {sum(v):>8} {sum(v)/len(v):>8.1%}")

    live = [x for x in rows if not x["pinned"] and x["hkd_per_cny"] != ""]
    if live:
        rel = sorted(x["implied"] / x["hkd_per_cny"] for x in live)
        print(f"\nnot pinned, implied rate over the measured rate: "
              f"p10 {rel[len(rel)//10]:.3f}  median {rel[len(rel)//2]:.3f}  "
              f"p90 {rel[9*len(rel)//10]:.3f}")
        print("  **These are the ones that need no rebuilding**, and they sit on")
        print("  the measured rate, which is what says the pinned ones are stale.")

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="\n") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(sorted(rows, key=lambda x: (x["a"], x["a_date"])))
        print(f"\nwrote {OUT} with {len(rows):,} rows, "
              f"{len(pin):,} carrying a rebuilt H amount")
    else:
        print("\n(nothing written. --write to produce the paired table.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
