"""B126 retail arm: does a unit's retail listing track its own last sale, or its neighbours'?

Reads data/b126/parsed/ and writes results/b126_retail.json. Uses the lot cleaning and event
definitions of experiments/b126_readings.py, so the auction side is the same object as there.

The question. A unit (wine x vintage) that has not traded for a while still carries a retail
listing. Two readings of where that number comes from:
  own      the listing holds the unit's own last sale (a state the holder keeps)
  harmonic the listing is set from the neighbours that did trade: on the chain of one wine's
           vintages, the harmonic function with the recently traded vintages as fixed values,
           which on a path is linear interpolation between the nearest anchored vintage below
           and the nearest above
On a unit that traded recently the two coincide (its own sale is an anchor), so the cells that
tell them apart are the units whose own last sale is old.

Objects:
  listing  median log per-750 ml price of the unit's retail offers in US dollars ('$' only; other
           currencies need exchange rates the pages do not carry, and none are supplied here).
           The per-750 ml figure is the site's own, printed beside every offer.
  anchor   a vintage of the same wine with at least one auction event in the FRESH days before the
           fetch; its value is the median log price of those events.
  interp   linear interpolation in vintage between the nearest anchor below and above the unit,
           the unit itself excluded. Units with an anchor on one side only get no interp.
  own_last the unit's last auction event price, and its age in days.
  markup   median of (listing - own fresh value) over units that are themselves anchors. Retail
           sits above auction by a merchant margin; it is taken off before any comparison.

Readings, by the age of the unit's own last sale (fresh / stale / very stale):
  error_own     |listing - markup - own_last|
  error_interp  |listing - markup - interp|
  hull          whether listing - markup lies between the two anchors (the maximum principle:
                a harmonic value never leaves the range of its boundary values), and, as its
                baseline, whether own_last does

Knobs, scanned (`11f`): SIZES (750 ml and 'Bottle' only, or every size), FRESH (365, 730 days),
CLEAN (0, 3; the auction-side cleaning of b126_readings).

Criteria (`11d`):
  B126-9   own_reading  stale units: interp is closer to the listing than own_last (median error)
  B126-9k  known_answer fresh units: own_last is at least as close as interp (the two readings
                        coincide there, so this is where the instrument can be checked)
  B126-10  own_reading  stale units: the listing lies inside its anchors' hull more often than
                        own_last does
Three states each, mapped in STATE (`11c`).

Run from the repo root:
    python experiments/b126_retail.py
    python experiments/b126_retail.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b126_readings as R  # noqa: E402
from scipy.stats import binomtest  # noqa: E402

OUT = R.ROOT / "results" / "b126_retail.json"
SCAN = {"sizes": ["bottle", "all"], "fresh": [365, 730], "clean": [0.0, 3.0]}
DEFAULT = {"sizes": "bottle", "fresh": 365, "clean": 3.0}
AGE_GROUPS = (("fresh", 0, 365), ("stale", 365, 1095), ("very stale", 1095, 10 ** 6))
BOTTLE = {"Bottle", "750ml"}


def usd(s: str | None) -> float | None:
    if not s or not s.startswith("$"):
        return None
    try:
        return float(s[1:].replace(",", ""))
    except ValueError:
        return None


def listings(retail: list[dict], sizes: str) -> dict:
    by: dict[tuple, list[float]] = {}
    for r in retail:
        if r["slug"] in R.EXCLUDE:
            continue
        if sizes == "bottle" and r["format"] not in BOTTLE:
            continue
        v = usd(r["per_750"])
        if v:
            by.setdefault((r["slug"], r["vintage"]), []).append(math.log(v))
    return {k: st.median(v) for k, v in by.items()}


def auction_side(lots: list[dict], cfg: dict) -> dict:
    """Per unit: events (all sizes' per-750 prices, as in the jump reading's 'all' setting)."""
    by: dict[tuple, list[dict]] = {}
    for l in R.clean_lots(lots, cfg["clean"]):
        if l["slug"] in R.EXCLUDE or l["format_conflict"] or not l.get("own_750_usd"):
            continue
        by.setdefault((l["slug"], l["vintage"]), []).append(l)
    out = {}
    for k, rows in by.items():
        ev, _ = R.events(rows)
        fresh = [e[2] for e in ev if (R.FETCHED - e[0]).days <= cfg["fresh"]]
        last = ev[-1]
        # the unit's own value: the median of its events in a window of FRESH days ending at its
        # last sale, the same length of window an anchor gets. A first version used the last
        # event alone, and the known-answer check (B126-9k) failed at every scan point: one
        # event against a value built from two medians loses on noise alone.
        own = [e[2] for e in ev if (last[0] - e[0]).days <= cfg["fresh"]]
        out[k] = {"fresh": st.median(fresh) if fresh else None, "last": st.median(own),
                  "last_age": (R.FETCHED - last[0]).days}
    return out


def interp(slug: str, vint: int, anchors: dict) -> tuple[float | None, tuple | None]:
    vs = sorted(v for (s, v) in anchors if s == slug and v != vint)
    lo = [v for v in vs if v < vint]
    hi = [v for v in vs if v > vint]
    if not lo or not hi:
        return None, None
    a, b = lo[-1], hi[0]
    pa, pb = anchors[(slug, a)], anchors[(slug, b)]
    return pa + (pb - pa) * (vint - a) / (b - a), (pa, pb)


def read_once(lots, retail, cfg) -> dict:
    L = listings(retail, cfg["sizes"])
    A = auction_side(lots, cfg)
    anchors = {k: v["fresh"] for k, v in A.items() if v["fresh"] is not None}
    marks = [L[k] - anchors[k] for k in L if k in anchors]
    markup = st.median(marks) if marks else 0.0
    rows = []
    for k, lv in L.items():
        if k not in A:
            continue
        ip, hull = interp(k[0], k[1], anchors)
        if ip is None:
            continue
        x = lv - markup
        rows.append({"unit": f"{k[0]}|{k[1]}", "age": A[k]["last_age"], "listing_net": x,
                     "own_last": A[k]["last"], "interp": ip,
                     "err_own": abs(x - A[k]["last"]), "err_interp": abs(x - ip),
                     "in_hull": min(hull) <= x <= max(hull),
                     "own_in_hull": min(hull) <= A[k]["last"] <= max(hull)})
    groups = {}
    for name, lo, hi in AGE_GROUPS:
        g = [r for r in rows if lo <= r["age"] < hi]
        if not g:
            groups[name] = {"units": 0}
            continue
        groups[name] = {"units": len(g),
                        "median_err_own": st.median(r["err_own"] for r in g),
                        "median_err_interp": st.median(r["err_interp"] for r in g),
                        "share_interp_closer": sum(r["err_interp"] < r["err_own"] for r in g) / len(g),
                        "share_listing_in_hull": sum(r["in_hull"] for r in g) / len(g),
                        "share_own_in_hull": sum(r["own_in_hull"] for r in g) / len(g)}
    stale = [r for r in rows if r["age"] >= 365]
    k = sum(r["err_interp"] < r["err_own"] for r in stale)
    pooled = {"units": len(stale), "interp_closer": k,
              "sign_p_one_sided": binomtest(k, len(stale), 0.5, alternative="greater").pvalue if stale else None}
    return {"cfg": cfg, "markup": markup, "markup_units": len(marks), "units": len(rows),
            "groups": groups, "pooled_stale": pooled, "rows": rows}


STATE = {"holds at every scan point": True, "fails at every scan point": False,
         "moves across the scan": None, "no object": None}


def state(vals: list[bool | None]) -> str:
    s = {v for v in vals if v is not None}
    if not s:
        return "no object"
    if s == {True}:
        return "holds at every scan point"
    if s == {False}:
        return "fails at every scan point"
    return "moves across the scan"


def stale_groups(r):
    return [r["groups"][n] for n in ("stale", "very stale") if r["groups"][n].get("units")]


def read(lots, retail) -> dict:
    scan = []
    for sz, fr, cl in itertools.product(SCAN["sizes"], SCAN["fresh"], SCAN["clean"]):
        scan.append(read_once(lots, retail, {"sizes": sz, "fresh": fr, "clean": cl}))

    def c9(r):
        gs = stale_groups(r)
        return None if not gs else all(g["median_err_interp"] < g["median_err_own"] for g in gs)

    def c9k(r):
        g = r["groups"]["fresh"]
        return None if not g.get("units") else g["median_err_own"] <= g["median_err_interp"]

    def c10(r):
        gs = stale_groups(r)
        return None if not gs else all(g["share_listing_in_hull"] > g["share_own_in_hull"] for g in gs)

    def det(r):
        c = r["cfg"]
        parts = []
        for n, g in r["groups"].items():
            if g.get("units"):
                parts.append(f"{n} n={g['units']} own {g['median_err_own']:.3f} interp {g['median_err_interp']:.3f}"
                             f" hull {g['share_listing_in_hull']:.2f}/{g['share_own_in_hull']:.2f}")
        return f"{c['sizes']}/f{c['fresh']}/c{c['clean']:g}: " + "; ".join(parts)

    s9, s9k, s10 = state([c9(r) for r in scan]), state([c9k(r) for r in scan]), state([c10(r) for r in scan])
    crit = [
        {"name": "B126-9", "kind": "own_reading",
         "statement": "stale units: the neighbours' interpolation is closer to the listing than the unit's own last sale",
         "passed": STATE[s9], "state": s9, "state_map": STATE, "detail": " | ".join(det(r) for r in scan)},
        {"name": "B126-9k", "kind": "known_answer",
         "statement": "fresh units, where the two readings coincide: own last sale at least as close as the interpolation",
         "passed": STATE[s9k], "state": s9k, "state_map": STATE,
         "detail": " | ".join(det(r).split(";")[0] for r in scan)},
        {"name": "B126-10", "kind": "own_reading",
         "statement": "stale units: the listing lies inside its anchors' range more often than the own last sale does",
         "passed": STATE[s10], "state": s10, "state_map": STATE, "detail": "see B126-9 detail, hull listing/own"},
    ]
    return {"scan": [{k: v for k, v in r.items() if k != "rows"} for r in scan],
            "rows_default": next(r["rows"] for r in scan if r["cfg"] == DEFAULT), "criteria": crit}


def report(r: dict) -> None:
    print("scan: sizes / fresh days / clean   markup (log) on n units   per age group: units, median error own vs interp, share interp closer, hull listing vs own")
    for s in r["scan"]:
        c = s["cfg"]
        print(f"  {c['sizes']:>6} f{c['fresh']} c{c['clean']:g}  markup {s['markup']:+.3f} (n={s['markup_units']})  units {s['units']}")
        for n, g in s["groups"].items():
            if g.get("units"):
                print(f"      {n:>10}  n {g['units']:>3}  err own {g['median_err_own']:.3f}  interp {g['median_err_interp']:.3f}"
                      f"  interp closer {g['share_interp_closer']:.2f}  in hull {g['share_listing_in_hull']:.2f} vs own {g['share_own_in_hull']:.2f}")
        p = s["pooled_stale"]
        print(f"      pooled stale units {p['units']}: interp closer on {p['interp_closer']}, one-sided sign p {p['sign_p_one_sided']:.3f}")
    print("\ncriteria")
    for c in r["criteria"]:
        print(f"  {c['name']:8} {c['kind']:12} {c['passed']!s:5}  {c['state']}")
    print(f"state map (`11c`): {STATE}")


def run() -> int:
    lots = json.loads((R.PARSED / "lots.json").read_text(encoding="utf-8"))
    retail = json.loads((R.PARSED / "retail.json").read_text(encoding="utf-8"))
    r = read(lots, retail)
    report(r)
    rec = {"stage": "B126", "arm": "retail",
           "config": {"default": DEFAULT, "scan": SCAN, "age_groups": [list(g) for g in AGE_GROUPS],
                      "currency": "USD listings only", "exclude": R.EXCLUDE,
                      "source": "data/b126/parsed/ via experiments/b126_parse.py"},
           **R.rnd(r)}
    OUT.write_text(json.dumps(rec, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")
    return 0


def selftest() -> int:
    """Seeded worlds (`11f`): a harmonic world must read B126-9 True, an own-state world False."""
    def world(rule):
        lots, retail = [], []
        # one wine, vintages 1990..2009; true value rises with age; odd vintages traded long ago,
        # even vintages traded in the last month (anchors). Since the old sales, the market moved
        # up by 0.4 everywhere.
        for v in range(1990, 2010):
            true_now = 5.0 + 0.05 * (2010 - v)
            old = v % 2 == 1
            day = "2020-01-01" if old else "2026-09-01"
            price_at_sale = true_now - (0.4 if old else 0.0)
            for h in ("a", "b"):
                lots.append({"slug": "w", "vintage": v, "date": day, "house": h, "format_ml": 750,
                             "format_conflict": False, "own_750_usd": math.exp(price_at_sale)})
            listing = rule(true_now, price_at_sale) + 0.2   # a 0.2 retail markup
            retail.append({"slug": "w", "vintage": v, "format": "Bottle", "per_750": f"${math.exp(listing):.2f}"})
        return lots, retail

    checks = []
    R._CLEAN_CACHE.clear()
    r = read(*world(lambda now, sold: now))
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("harmonic world: B126-9 True", c["B126-9"]["passed"] is True))
    checks.append(("harmonic world: B126-10 True", c["B126-10"]["passed"] is True))
    R._CLEAN_CACHE.clear()
    r = read(*world(lambda now, sold: sold))
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("own-state world: B126-9 False", c["B126-9"]["passed"] is False))
    checks.append(("own-state world: B126-10 not True", c["B126-10"]["passed"] is not True))
    R._CLEAN_CACHE.clear()
    checks.append(("a non-dollar listing is not read", usd("£120") is None and usd("HK$1,200") is None
                   and usd("$1,200") == 1200.0))
    checks.append(("interpolation is linear between the nearest anchors on each side",
                   interp("w", 2001, {("w", 2000): 1.0, ("w", 2004): 2.0, ("w", 1990): 9.0})[0] == 1.25))
    checks.append(("no anchor on one side: no interpolation", interp("w", 2005, {("w", 2000): 1.0})[0] is None))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    return selftest() if ap.parse_args().selftest else run()


if __name__ == "__main__":
    sys.exit(main())
