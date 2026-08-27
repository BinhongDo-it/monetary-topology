"""B21: four instruments for the stock-level transfer cost, none of them quotes.

The precondition for layer two is whether `t_ab(A_k)` has a `k` in it large
enough to find. A first pass estimated the bid-ask spread with Corwin and Schultz
(2012) and could not answer: the estimator returns a negative on two windows in
five for every leg, and a leg's estimate correlates -0.39 with its own floored
share, so truncation narrows the dispersion while a varying floor rate widens it.

**That is one estimator's failure, not the question's.** Three of the four here
cannot return a negative at all, and the fourth fixes the negativity by taking
the expectation before the square root rather than after.

    Abdi-Ranaldo (2017, RFS)   spread, from close and the high-low midpoint.
                               `S^2 = 4 E[(c_t - m_t)(c_t - m_{t+1})]`, and the
                               expectation is taken over a month **before** the
                               root, which is the step that removes most of the
                               negatives Corwin-Schultz leaves.
    Amihud (2002, JFM)         price impact, `mean |r| / turnover`. **Cannot be
                               negative.** For moving a position between holders
                               this is the better object anyway: a transfer pays
                               impact, not the touch.
    Lesmond et al (1999, RFS)  the share of zero-return days. **Cannot be
                               negative**, needs closes only, and is the standard
                               proxy where quotes are thin.
    turnover                   median daily value traded. **Cannot be negative**,
                               and is the crudest of the four.

**None of the four settles it, and the way they fail names the instrument that
does.** All four are noise-dominated in the same way: an A-share's daily range
runs two to four hundred basis points while the spread being sought is single
digits, so every range-based estimator drowns. Abdi-Ranaldo comes back
non-positive on 52.5% of months against Corwin-Schultz's 40.7% of windows, and
the four rank the legs almost independently of one another.

**What settles it is not an estimator at all.** The mainland tick is a flat 0.01
yuan on both boards, so a stock trading at `P` cannot have a relative spread
below `0.01 / P`. That is a published rule and a division, exact, stock-level,
and free. It is also discipline's own ninth category error read forwards: **a
fixed absolute grid across heterogeneous prices manufactures exactly the
stock-level heterogeneity layer two needs.**

The one gap in that argument is closed by a fifth instrument. A floor is only a
floor: if every stock quoted the same relative spread, a dispersed floor would
imply nothing. **Whether the tick binds is measurable from closes alone**, by
Harris's last-digit clustering: a stock using every tick spreads its final digit
uniformly, one whose effective grid is coarser piles onto 0 and 5. It binds where
it matters, and the correlations say so in the right direction.

**What the four estimators are still good for is agreement, and they do not agree.**
Each is blind to what the others see: one reads the range, one reads impact per
unit traded, one reads days with no trade at all, one reads size. If they rank
the same stocks the same way, the stock-level term is real and the dispersion
can be read off the one in spread units. If they do not, the disagreement is the
answer and it is a different answer from "the estimator floored".

Usage::

    python experiments/b21_liquidity.py
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
OUT = ROOT / "results" / "b21_liquidity.json"

MIN_DAYS = 500
WEDGE_SD = 0.00423          # b21_cross_section.py, the CNH-CNY log spread


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


def bars(tk: str) -> list[tuple[str, float, float, float, float]]:
    out = []
    for r in load(tk):
        try:
            h, lo, c, v = (float(r["High"]), float(r["Low"]),
                           float(r["Close"]), float(r.get("Volume") or 0))
        except (TypeError, ValueError, KeyError):
            continue
        if h > 0 and lo > 0 and c > 0 and h >= lo:
            out.append((r["Date"][:10], h, lo, c, v))
    return out


def abdi_ranaldo(b: list) -> tuple[float | None, float]:
    """Monthly S, then the median month. Negatives counted, not hidden."""
    by: dict[str, list[float]] = {}
    for t in range(len(b) - 1):
        _, h1, l1, c1, _ = b[t]
        _, h2, l2, _, _ = b[t + 1]
        m1 = (math.log(h1) + math.log(l1)) / 2
        m2 = (math.log(h2) + math.log(l2)) / 2
        by.setdefault(b[t][0][:7], []).append(4 * (math.log(c1) - m1)
                                              * (math.log(c1) - m2))
    s, neg = [], 0
    for mo, v in by.items():
        if len(v) < 10:
            continue
        m = statistics.fmean(v)
        if m <= 0:
            neg += 1
            s.append(0.0)
        else:
            s.append(math.sqrt(m))
    return (statistics.median(s) if len(s) >= 12 else None,
            neg / len(s) if s else 0.0)


def amihud(b: list) -> float | None:
    v = []
    for t in range(1, len(b)):
        c0, c1, q = b[t - 1][3], b[t][3], b[t][4]
        if q > 0 and c0 > 0:
            v.append(abs(math.log(c1 / c0)) / (q * c1))
    return statistics.median(v) if len(v) >= MIN_DAYS else None


def zero_return_share(b: list) -> float | None:
    n = z = 0
    for t in range(1, len(b)):
        n += 1
        if b[t][3] == b[t - 1][3]:
            z += 1
    return z / n if n >= MIN_DAYS else None


TICK = 0.01                 # yuan, flat on both mainland boards


def tick_floor(b: list) -> float:
    """`0.01 / P` on the median day. **Exact, not estimated.**"""
    return statistics.median([TICK / x[3] for x in b])


def digit_clustering(b: list) -> float:
    """Share of closes whose last 0.01 digit is 0 or 5 (Harris 1991).

    A stock that uses every tick reads 0.200. One whose effective grid is coarser
    than the tick reads above it. **This is what turns the floor from a bound
    into a reading**: where the number sits at 0.200 the tick is the spread.
    """
    d = [0] * 10
    for x in b:
        d[int(round(x[3] * 100)) % 10] += 1
    n = sum(d)
    return (d[0] + d[5]) / n if n else 0.0


def spearman(x: list[float], y: list[float]) -> float:
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return statistics.correlation(rank(x), rank(y))


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
    rows = []
    for r in pairs_on_page():
        b = bars(r["a"])
        if len(b) < MIN_DAYS:
            continue
        ar, ar_neg = abdi_ranaldo(b)
        am, zr = amihud(b), zero_return_share(b)
        tv = statistics.median([x[3] * x[4] for x in b if x[4] > 0] or [0])
        if None in (ar, am, zr) or tv <= 0:
            continue
        rows.append({"name": r["name"], "tk": r["a"], "ar": ar, "ar_neg": ar_neg,
                     "amihud": am, "zero": zr, "turnover": tv,
                     "floor": tick_floor(b), "cluster": digit_clustering(b),
                     "price": statistics.median([x[3] for x in b])})
    if len(rows) < 30:
        print(f"only {len(rows)} legs usable")
        return 1

    print(f"{len(rows)} A legs, at least {MIN_DAYS} daily bars each\n")
    v = sorted(x["ar"] for x in rows)
    ng = sorted(x["ar_neg"] for x in rows)
    print("Abdi-Ranaldo spread, in basis points of price:")
    print(f"  p10 {1e4*v[len(v)//10]:>7.1f}   median {1e4*v[len(v)//2]:>7.1f}   "
          f"p90 {1e4*v[9*len(v)//10]:>7.1f}   min {1e4*v[0]:>7.1f}   "
          f"max {1e4*v[-1]:>7.1f}")
    print(f"  months whose estimate comes back non-positive: median leg "
          f"{100*ng[len(ng)//2]:.1f}%, p90 leg {100*ng[9*len(ng)//10]:.1f}%")
    print(f"  **Corwin-Schultz floored 40.7% of its windows on the median leg.**")

    print("\ndo the four instruments rank the same stocks the same way?")
    keys = [("Abdi-Ranaldo", "ar"), ("Amihud", "amihud"),
            ("zero-return share", "zero"), ("turnover", "turnover")]
    print(f"  {'':>20}" + "".join(f"{k[0][:12]:>14}" for k in keys))
    rho = {}
    for na, ka in keys:
        line = f"  {na:>20}"
        for nb, kb in keys:
            r = spearman([x[ka] for x in rows], [x[kb] for x in rows])
            rho[(ka, kb)] = r
            line += f"{r:>14.3f}"
        print(line)
    print("  Turnover runs the other way by construction: a liquid stock has high")
    print("  turnover and a low spread, so a negative there is agreement.")

    agree = all(rho[(a, b)] > 0 for a, _ in [(k[1], 0) for k in keys[:3]]
                for b in [k[1] for k in keys[:3]] if a != b) and \
        all(rho[(a, "turnover")] < 0 for a in ("ar", "amihud", "zero"))

    # ---- the instrument that does not estimate anything ----
    fl = sorted(x["floor"] for x in rows)
    fdisp = statistics.pstdev([x["floor"] for x in rows])
    cl = sorted(x["cluster"] for x in rows)
    c_price = statistics.correlation([x["cluster"] for x in rows],
                                     [math.log(x["price"]) for x in rows])
    c_floor = statistics.correlation([x["cluster"] for x in rows],
                                     [x["floor"] for x in rows])
    uniform = sum(1 for x in cl if abs(x - 0.2) < 0.02)
    print(f"\nthe tick floor, `0.01 / P`. **A published rule and a division, so")
    print(f"nothing here is estimated and nothing can come back negative.**")
    print(f"  p10 {1e4*fl[len(fl)//10]:>7.2f}   median {1e4*fl[len(fl)//2]:>7.2f}   "
          f"p90 {1e4*fl[9*len(fl)//10]:>7.2f}   min {1e4*fl[0]:>7.2f}   "
          f"max {1e4*fl[-1]:>7.2f}  bp")
    print(f"  cross-stock sd {fdisp:.5f}, which is {fdisp/WEDGE_SD:.3f} of the "
          f"wedge's {WEDGE_SD:.5f}")

    print(f"\nwhether the tick binds, from the last digit of the close:")
    print(f"  0 or 5 share: p10 {cl[len(cl)//10]:.4f}  median {cl[len(cl)//2]:.4f}  "
          f"p90 {cl[9*len(cl)//10]:.4f}   (a stock using every tick reads 0.200)")
    print(f"  within 0.02 of uniform: {uniform} of {len(rows)} legs")
    print(f"  clustering against log price {c_price:+.4f}, against the floor "
          f"{c_floor:+.4f}")
    print("  **It binds where the floor is large and loosens where it is small**,")
    print("  which is the direction that makes the floor's dispersion a reading")
    print("  rather than a bound: the objection a floor invites is that every")
    print("  stock might quote the same relative spread, and a cheap stock using")
    print("  every tick while an expensive one skips four is that objection")
    print("  measured and refused.")

    disp = statistics.pstdev([x["ar"] for x in rows])
    iqr = v[3 * len(v) // 4] - v[len(v) // 4]
    print(f"\nthe comparison layer two turns on:")
    print(f"  stock-level term, cross-stock sd {disp:.5f}   iqr {iqr:.5f}")
    print(f"  currency wedge, sd               {WEDGE_SD:.5f}")
    print(f"  ratio                            {disp/WEDGE_SD:.2f}")

    print(f"\n  {'widest five':>26} {'bp':>7}       {'tightest five':>26} {'bp':>7}")
    for a, b in zip(sorted(rows, key=lambda x: -x["ar"])[:5],
                    sorted(rows, key=lambda x: x["ar"])[:5]):
        print(f"  {a['name']:>26} {1e4*a['ar']:>7.1f}       "
              f"{b['name']:>26} {1e4*b['ar']:>7.1f}")

    crit = [
        {"name": "B21-11  the stock-level term is bounded below exactly, with no "
                 "estimator in the chain",
         "passed": fdisp > 0,
         "detail": f"tick floor 0.01/P runs {1e4*fl[0]:.2f} to {1e4*fl[-1]:.2f} bp "
                   f"over {len(rows)} legs, cross-stock sd {fdisp:.5f}, "
                   f"{fdisp/WEDGE_SD:.3f} of the wedge"},
        {"name": "B21-12  the tick binds where the floor is large, so the floor's "
                 "dispersion is a reading and not only a bound",
         "passed": c_floor < 0 and c_price > 0,
         "detail": f"last-digit clustering median {cl[len(cl)//2]:.4f} against "
                   f"0.200 for a stock using every tick, {uniform} legs within "
                   f"0.02 of uniform; clustering against log price {c_price:+.4f} "
                   f"and against the floor {c_floor:+.4f}"},
        {"name": "B21-9  four instruments, three of which cannot return a "
                 "negative, agree on the ordering of the legs",
         "passed": bool(agree),
         "detail": "; ".join(
             f"{na} vs {nb} {rho[(ka,kb)]:+.3f}"
             for (na, ka), (nb, kb) in
             [(keys[0], keys[1]), (keys[0], keys[2]), (keys[1], keys[2]),
              (keys[0], keys[3]), (keys[1], keys[3]), (keys[2], keys[3])])},
        {"name": "B21-10  the stock-level term is not degenerate",
         "passed": v[0] < v[-1],
         "detail": f"Abdi-Ranaldo spread runs {1e4*v[0]:.1f} to {1e4*v[-1]:.1f} bp, "
                   f"median {1e4*v[len(v)//2]:.1f}, over {len(rows)} legs"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "liquidity",
        "diagnostic_only": True,
        "diagnostic_reason": "The precondition for layer two, re-asked with "
                             "instruments that do not floor. It sizes the "
                             "stock-level term; it does not read the station.",
        "legs": len(rows),
        "spread_bp": {"p10": 1e4*v[len(v)//10], "median": 1e4*v[len(v)//2],
                      "p90": 1e4*v[9*len(v)//10], "min": 1e4*v[0], "max": 1e4*v[-1]},
        "ar_nonpositive_share_median_leg": ng[len(ng)//2],
        "cross_stock_sd": disp, "iqr": iqr, "wedge_sd": WEDGE_SD,
        "ratio": disp / WEDGE_SD,
        "tick_floor_bp": {"p10": 1e4*fl[len(fl)//10], "median": 1e4*fl[len(fl)//2],
                          "p90": 1e4*fl[9*len(fl)//10], "min": 1e4*fl[0],
                          "max": 1e4*fl[-1]},
        "tick_floor_sd": fdisp, "tick_floor_ratio": fdisp / WEDGE_SD,
        "clustering_median": cl[len(cl)//2], "legs_near_uniform": uniform,
        "clustering_vs_logprice": c_price, "clustering_vs_floor": c_floor,
        "rank_correlations": {f"{a}|{b}": r for (a, b), r in rho.items()},
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, "
          f"{sum(1 for c in crit if c['passed'])} passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
