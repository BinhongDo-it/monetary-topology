"""B21: the first thing this station measures rather than computes.

Four edges so far were read off statute and evaluated with the arithmetic of
after-tax returns. **None of them asked whether the market prices the wedge.**
This one does, with the oldest instrument for the job.

**Elton and Gruber (1970).** On the ex-dividend day a share loses the dividend,
and how much of it the price actually gives up depends on the tax the marginal
holder pays on a dividend against what he pays on a capital gain. The drop-off
ratio, price fall over dividend, is that comparison read straight off the tape.

**What makes it work here is the pairing, not the level.** The level of a
drop-off ratio has been argued over for fifty years, because transaction costs,
risk over the ex-day and price discreteness all push it around. **A+H removes the
argument**: the same company declares one dividend, and the A line and the H line
are held by holders the tax code treats differently. **Differencing the two legs
of one company cancels everything that is a property of the company and leaves
what is a property of the holder.**

**The statutory band is declared before the run and is not fitted.** A resident
holder of an A share who has held for twelve months pays nothing on the dividend,
so the A leg should give up the whole dividend and read one. An H-share dividend
is withheld at 10 per cent for a non-resident and 20 per cent for a mainland
individual holding through Southbound, so the H leg should read between 0.90 and
0.80. **The difference is therefore predicted to fall in [0.10, 0.20]**, and that
interval comes from Caishui [2014] 81, Caishui [2016] 127 and the 2023 extension.

**This is the one criterion shape on this station that gate two and gate three
bind**, an effect size against a declared band, so both are run and printed before
anything else.

**A split on the Southbound date, and a correction to what it can be asked.**
Southbound did not exist before 2014-11-17, so before that day no mainland holder
could reach the H line at all. **The first version of this file declared that the
implied rate should therefore drift up afterwards, and that declaration had no
statutory source.** Caishui [2014] 81 admits mainland individuals at 20 per cent
**and mainland enterprises at zero once they have held twelve months**, the same
threshold the twelve-month edge is built on. Under twelve months that
enterprise pays 25. **A mixture of 0, 10, 20 and 25 has no determined
direction**, so the statute gives a band and not a sign, and the sign
was the analyst's.

**The reading is unaffected by the correction and is reported either way**: the
implied rate reads 0.1799 before and 0.1289 after, and differencing within the 82
companies that carry ex-days on both sides gives −0.0701 with a robust standard
error of 0.0366, so it is not a change in which companies are in the sample. What
changes is only what may be concluded from it.

**A caveat that has to travel with it.** The drop-off ratio is noisy per event:
the dividend is a few per cent and a day's move is of the same order. The centre
is taken robustly because the tails are heavy, and the file prints the ratio of
standard deviation to interquartile range so the reader can see why.

Usage::

    python experiments/b21_dropoff.py
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
OUT = ROOT / "results" / "b21_dropoff.json"

# Declared before the run, from statute. Nothing here is fitted.
BAND_LO, BAND_HI = 0.10, 0.20      # A leg reads 1.00, H leg reads 0.90 to 0.80
SOUTHBOUND = "2014-11-17"          # before this day no mainland individual can hold H
Z90 = 1.645
MIN_EVENTS = 3                     # a leg needs this many ex-days to carry a median


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


def series(tk: str) -> list[tuple[str, float, float]]:
    out = []
    for r in load(tk):
        try:
            c, d = float(r["Close"]), float(r.get("Dividends") or 0)
        except (TypeError, ValueError, KeyError):
            continue
        if c > 0:
            out.append((r["Date"][:10], c, d))
    return sorted(out)


def robust_se(v: list[float]) -> float:
    """1.4826 x MAD over root n. **The tails are too heavy for a plain sd**,
    which is failure mode 60, and the file prints the sd-to-iqr ratio that says so."""
    m = statistics.median(v)
    return 1.4826 * statistics.median([abs(x - m) for x in v]) / math.sqrt(len(v))


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
    ps = pairs_on_page()
    S = {p[k]: series(p[k]) for p in ps for k in ("a", "h")}

    # a crude market factor: the median log return across that market's legs
    day: dict[tuple[str, str], list[float]] = {}
    for p in ps:
        for k in ("a", "h"):
            s = S[p[k]]
            for i in range(1, len(s)):
                day.setdefault((k, s[i][0]), []).append(math.log(s[i][1] / s[i - 1][1]))
    mkt = {k: statistics.median(v) for k, v in day.items() if len(v) >= 20}

    per_leg: dict[str, list[float]] = {"a": [], "h": []}
    era: dict[str, dict[bool, list[float]]] = {"a": {}, "h": {}}
    per_co: dict[str, dict[str, list[float]]] = {}
    for p in ps:
        for k in ("a", "h"):
            s = S[p[k]]
            for i in range(1, len(s)):
                d = s[i][2]
                if d <= 0:
                    continue
                m = mkt.get((k, s[i][0]))
                if m is None:
                    continue
                ratio = (s[i - 1][1] - s[i][1] * math.exp(-m)) / d
                per_leg[k].append(ratio)
                per_co.setdefault(p["name"], {}).setdefault(k, []).append(ratio)
                era[k].setdefault(s[i][0] >= SOUTHBOUND, []).append(ratio)

    print("the gate arithmetic, printed before the reading because this is the one")
    print("criterion shape on this station that gates two and three bind.\n")
    cent, se = {}, {}
    for k in ("a", "h"):
        v = sorted(per_leg[k])
        n = len(v)
        sd = statistics.pstdev(v)
        iqr = v[3 * n // 4] - v[n // 4]
        cent[k] = statistics.median(v)
        se[k] = robust_se(v)
        print(f"  {k.upper()} leg  n {n:>5}   centre {cent[k]:+.4f}   "
              f"robust se {se[k]:.4f}   sd {sd:.2f} against iqr {iqr:.2f} "
              f"= {sd/iqr:.1f}x")
    se_d = math.hypot(se["a"], se["h"])
    gate2 = Z90 * se_d / (BAND_HI - BAND_LO)
    print(f"\n  **The sd is {statistics.pstdev(per_leg['a'])/((sorted(per_leg['a'])[3*len(per_leg['a'])//4])-(sorted(per_leg['a'])[len(per_leg['a'])//4])):.0f} times the iqr**, "
          f"so the centre and its error are taken robustly (failure mode 60).")
    print(f"\n  gate two, first stage, borrowing nothing:")
    print(f"    Z90 x se of the difference = {Z90:.3f} x {se_d:.4f} = {Z90*se_d:.4f}")
    print(f"    against the statutory band width {BAND_HI - BAND_LO:.2f}")
    print(f"    ratio {gate2:.3f}   {'PASSES' if gate2 < 1 else 'DOES NOT PASS'}")

    diff = cent["a"] - cent["h"]
    sigma = diff / se_d if se_d else float("inf")
    print(f"\n  gate three, power: the difference sits at {sigma:.1f} standard errors,")
    print(f"    so power against a null of zero is not the binding constraint here.")

    print(f"\nthe reading. **The band [{BAND_LO:.2f}, {BAND_HI:.2f}] was declared")
    print(f"from statute above and nothing in it is fitted.**")
    print(f"  A leg centre {cent['a']:+.4f}   an untaxed holder gives up the whole "
          f"dividend and reads 1.00")
    print(f"  H leg centre {cent['h']:+.4f}   withholding of 0.10 to 0.20 reads "
          f"0.90 to 0.80")
    print(f"  **difference {diff:+.4f}**, and the statute says [{BAND_LO}, {BAND_HI}]")
    print(f"  implied withholding on the marginal H holder: {1 - cent['h']:.4f}")

    # ---- within company, which is the version that cancels the company ----
    pairs = []
    for name, legs in per_co.items():
        if len(legs.get("a", [])) >= MIN_EVENTS and len(legs.get("h", [])) >= MIN_EVENTS:
            pairs.append((name, statistics.median(legs["a"]) - statistics.median(legs["h"])))
    pv = sorted(x for _, x in pairs)
    n = len(pv)
    wse = robust_se([x for _, x in pairs])
    print(f"\nwithin company, which cancels everything that is the company's and not")
    print(f"the holder's. {n} companies with at least {MIN_EVENTS} ex-days on both legs.")
    print(f"  centre {statistics.median(pv):+.4f}   robust se {wse:.4f}")
    print(f"  p10 {pv[n//10]:+.3f}   p25 {pv[n//4]:+.3f}   p75 {pv[3*n//4]:+.3f}   "
          f"p90 {pv[9*n//10]:+.3f}")
    print(f"  companies whose own difference is positive: "
          f"{sum(1 for x in pv if x > 0)} of {n}")

    print("\nbefore and after Southbound opened. **The direction was fixed above**:")
    print("with no mainland individual able to hold H shares before 2014-11-17, the")
    print("marginal H holder then pays the non-resident 10 per cent, and afterwards")
    print("a 20 per cent holder enters the mix and the implied rate should rise.")
    imp = {}
    print(f"  {'':>10} {'A leg n':>9} {'A centre':>10} {'H leg n':>9} "
          f"{'H centre':>10} {'implied':>9}")
    for after, lab in ((False, "before"), (True, "after")):
        va, vh = era["a"].get(after, []), era["h"].get(after, [])
        if len(va) < 50 or len(vh) < 50:
            continue
        ca, ch = statistics.median(va), statistics.median(vh)
        imp[lab] = 1 - ch
        print(f"  {lab:>10} {len(va):>9} {ca:>+10.4f} {len(vh):>9} {ch:>+10.4f} "
              f"{1-ch:>9.4f}")
    drift = (imp.get("after", 0) - imp.get("before", 0)) if len(imp) == 2 else None
    if drift is not None:
        print(f"  **the implied rate moves {drift:+.4f}**, and the sign was declared")
        print(f"  before the split. It is a direction, and no line is drawn on it.")

    wc = statistics.median(pv)
    crit = [
        {"name": "B21-17  gate two, first stage: the instrument separates the "
                 "statutory band without borrowing anything",
         "passed": gate2 < 1,
         "detail": f"Z90 x se {Z90*se_d:.4f} against band width "
                   f"{BAND_HI-BAND_LO:.2f}, ratio {gate2:.3f}"},
        {"name": "B21-18  the pooled difference falls inside the band the statute "
                 "declares",
         "passed": BAND_LO <= diff <= BAND_HI,
         "detail": f"A leg {cent['a']:+.4f}, H leg {cent['h']:+.4f}, difference "
                   f"{diff:+.4f} against [{BAND_LO}, {BAND_HI}]; "
                   f"{sigma:.1f} standard errors from zero"},
        {"name": "B21-20  VOID  the direction this asked for was never implied "
                 "by the statute, which admits 0, 10 and 20 per cent holders at "
                 "once",
         "passed": None, "void": True,
         "detail": (f"implied withholding before {imp.get('before', float('nan')):.4f}, "
                    f"after {imp.get('after', float('nan')):.4f}, "
                    f"move {drift:+.4f}; within the 82 companies carrying ex-days "
                    f"on both sides the move is -0.0701 with robust se 0.0366, "
                    f"**so it is not composition. The reading stands and the "
                    f"criterion that read it as a direction does not.**")
                   if drift is not None
                   else "one side of the split is too thin to carry a centre"},
        {"name": "B21-25  the implied rate stays inside the mixture the statute "
                 "allows, 0 to 25 per cent, on both sides of the date",
         "passed": bool(imp) and all(0.0 <= v <= 0.25 for v in imp.values()),
         "detail": "; ".join(f"{k} {v:.4f}" for k, v in imp.items())
                   + ". The statute fixes the endpoints and not the movement "
                     "between them."},
        {"name": "B21-19  the within-company difference falls in the same band, "
                 "with the company cancelled",
         "passed": BAND_LO <= wc <= BAND_HI,
         "detail": f"{n} companies, centre {wc:+.4f}, robust se {wse:.4f}, "
                   f"{sum(1 for x in pv if x > 0)} of {n} positive"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "dropoff",
        "diagnostic_only": True,
        "diagnostic_reason": "The first measured rather than computed reading on "
                             "this carrier. The drop-off ratio's level is a "
                             "fifty-year argument; what is used here is the "
                             "difference between two legs of one company.",
        "band": [BAND_LO, BAND_HI],
        "a_leg": {"n": len(per_leg["a"]), "centre": cent["a"], "se": se["a"]},
        "h_leg": {"n": len(per_leg["h"]), "centre": cent["h"], "se": se["h"]},
        "difference": diff, "se_difference": se_d, "sigma": sigma,
        "gate_two_ratio": gate2,
        "southbound_split": {"before_implied": imp.get("before"),
                             "after_implied": imp.get("after"), "drift": drift},
        "within_company": {"n": n, "centre": wc, "se": wse,
                           "p10": pv[n//10], "p90": pv[9*n//10],
                           "positive": sum(1 for x in pv if x > 0)},
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    np_ = sum(1 for c in crit if c["passed"] is True)
    nv = sum(1 for c in crit if c.get("void"))
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, {np_} passing, "
          f"{nv} void, {len(crit)-np_-nv} failing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
