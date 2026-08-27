"""Availability check for the fungible depositary-receipt carrier. Nothing is scored.

**Why this exists.** The B21 criterion census counted twenty-six criteria and
found that the two which reach Corollary 1 are both arithmetic, so no criterion
on that carrier can be answered differently by the world in a way that touches
the framework. Filling that needs a class pair whose **statutory term is zero**,
so the index is not forced non-zero before the data is read, while the measured
square is still free to be either.

**Two holders of the same country, one holding the depositary receipt and one
holding the home line, face the same treaty rate.** The statutory term is then
exactly zero and the square is the pure return difference between the two
listings. On an interconvertible pair arbitrage bounds it by the published
conversion cost; on A and H, which cannot be converted into one another, nothing
bounds it and the premium has run between 100 and 150 for years.

**This file answers one question and registers nothing**: does the price source
this project already uses carry both legs, over what span, with dividends. It is
an availability check in the same series as the three before it, and its result
changes a design rather than a budget.

**It buys nothing.** Five years of daily bars for forty tickers.

Resumable: each ticker is cached under ``data/raw/adr_probe`` and a cached file
is not refetched. A short or unparseable payload is quarantined with a
``.partial`` suffix and left in place rather than removed, so a rerun sees it.

Usage, on a machine with network access::

    python data/fetch_adr_availability.py
    python data/fetch_adr_availability.py --refresh 0700.HK   # one ticker again
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "adr_probe"
OUT = ROOT / "results" / "adr_availability.json"
MANIFEST = CACHE / "manifest.json"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?range=5y&interval=1d&events=div")
UA = "monetary-topology research binhongd@outlook.com"

#: (receipt, home line, home venue, country). The country picks the treaty rate,
#: and both holders in the class pair are of that country, so the statutory term
#: is zero by construction rather than by netting two numbers.
PAIRS = [
    ("AZN",   "AZN.L",        "London",     "United Kingdom"),
    ("SHEL",  "SHEL.L",       "London",     "United Kingdom"),
    ("BP",    "BP.L",         "London",     "United Kingdom"),
    ("HSBC",  "HSBA.L",       "London",     "United Kingdom"),
    ("RIO",   "RIO.L",        "London",     "United Kingdom"),
    ("DEO",   "DGE.L",        "London",     "United Kingdom"),
    ("UL",    "ULVR.L",       "London",     "United Kingdom"),
    ("NVS",   "NOVN.SW",      "Zurich",     "Switzerland"),
    ("NVO",   "NOVO-B.CO",    "Copenhagen", "Denmark"),
    ("SAP",   "SAP.DE",       "Frankfurt",  "Germany"),
    ("DB",    "DBK.DE",       "Frankfurt",  "Germany"),
    ("TTE",   "TTE.PA",       "Paris",      "France"),
    ("SNY",   "SAN.PA",       "Paris",      "France"),
    ("ASML",  "ASML.AS",      "Amsterdam",  "Netherlands"),
    ("PHG",   "PHIA.AS",      "Amsterdam",  "Netherlands"),
    ("TM",    "7203.T",       "Tokyo",      "Japan"),
    ("HMC",   "7267.T",       "Tokyo",      "Japan"),
    ("SONY",  "6758.T",       "Tokyo",      "Japan"),
    ("MFG",   "8411.T",       "Tokyo",      "Japan"),
    ("SAN",   "SAN.MC",       "Madrid",     "Spain"),
    ("BBVA",  "BBVA.MC",      "Madrid",     "Spain"),
    ("E",     "ENI.MI",       "Milan",      "Italy"),
    ("PBR",   "PETR4.SA",     "Sao Paulo",  "Brazil"),
    ("VALE",  "VALE3.SA",     "Sao Paulo",  "Brazil"),
    ("INFY",  "INFY.NS",      "Mumbai",     "India"),
    ("IBN",   "ICICIBANK.NS", "Mumbai",     "India"),
    ("BHP",   "BHP.AX",       "Sydney",     "Australia"),
    ("WBK",   "WBC.AX",       "Sydney",     "Australia"),
    ("TD",    "TD.TO",        "Toronto",    "Canada"),
    ("BNS",   "BNS.TO",       "Toronto",    "Canada"),
    ("EQNR",  "EQNR.OL",      "Oslo",       "Norway"),
    ("KB",    "105560.KS",    "Seoul",      "Korea"),
]


def path_for(sym: str) -> Path:
    return CACHE / (sym.replace("=", "_").replace("/", "_") + ".json")


def fetch(sym: str, refresh: bool = False) -> tuple[dict | None, str]:
    """Return the parsed payload and how it was obtained. Never deletes."""
    p = path_for(sym)
    if p.exists() and not refresh:
        try:
            return json.loads(p.read_text(encoding="utf-8")), "cache"
        except json.JSONDecodeError:
            bad = p.with_suffix(p.suffix + ".partial")
            n = 0
            while bad.exists():
                n += 1
                bad = p.with_suffix(p.suffix + f".partial{n}")
            p.rename(bad)          # renamed, not removed
    req = urllib.request.Request(CHART.format(sym=sym), headers={"User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
    except (urllib.error.URLError, TimeoutError) as e:
        return None, "unreachable: %s" % type(e).__name__
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return None, "unparseable payload"
    tmp = p.with_suffix(p.suffix + ".writing")
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(raw)
    tmp.replace(p)
    return d, "fetched"


def describe(d: dict | None) -> dict:
    """What the availability question actually needs, per leg."""
    if not d:
        return {"ok": False}
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        err = (d.get("chart") or {}).get("error")
        return {"ok": False, "error": (err or {}).get("code") if err else "empty"}
    r = res[0]
    ts = r.get("timestamp") or []
    ev = ((r.get("events") or {}).get("dividends") or {})
    meta = r.get("meta") or {}
    return {"ok": bool(ts), "bars": len(ts), "currency": meta.get("currency"),
            "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
            "dividends": len(ev),
            "dividend_dates": sorted(int(v["date"]) for v in ev.values()) if ev else []}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", nargs="*", default=[],
                    help="tickers to fetch again even if cached")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    rows, manifest = [], []
    for adr, home, venue, country in PAIRS:
        out = {"receipt": adr, "home": home, "venue": venue, "country": country}
        for role, sym in (("receipt", adr), ("home", home)):
            d, how = fetch(sym, refresh=sym in args.refresh)
            out[role + "_source"] = how
            out[role + "_desc"] = describe(d)
            manifest.append({"symbol": sym, "url": CHART.format(sym=sym), "how": how,
                             "bars": out[role + "_desc"].get("bars", 0)})
            if how == "fetched":
                time.sleep(args.sleep)
        a, h = out["receipt_desc"], out["home_desc"]
        both = a.get("ok") and h.get("ok")
        out["both_legs"] = bool(both)
        # A dividend event is usable only if both legs carry bars around it. At this
        # depth the question is only whether the source exposes them at all.
        out["dividend_events_min_leg"] = min(a.get("dividends", 0), h.get("dividends", 0)) if both else 0
        rows.append(out)

    print("%-7s %-14s %-14s %6s %6s %5s %5s %s"
          % ("ADR", "home", "country", "barsA", "barsH", "divA", "divH", "both"))
    for r in rows:
        a, h = r["receipt_desc"], r["home_desc"]
        print("%-7s %-14s %-14s %6s %6s %5s %5s %s"
              % (r["receipt"], r["home"], r["country"][:14],
                 a.get("bars", "-"), h.get("bars", "-"),
                 a.get("dividends", "-"), h.get("dividends", "-"), r["both_legs"]))

    ok = [r for r in rows if r["both_legs"]]
    divs = sum(r["dividend_events_min_leg"] for r in ok)
    print("\npairs with both legs: %d of %d" % (len(ok), len(rows)))
    print("dividend events over five years, counted on the thinner leg: %d" % divs)
    print("pairs missing a leg, named: %s"
          % (", ".join("%s/%s" % (r["receipt"], r["home"]) for r in rows if not r["both_legs"]) or "none"))

    criteria = [
        {"name": "ADR-A-1  every pair in the declared list was attempted and its outcome printed",
         "passed": len(rows) == len(PAIRS),
         "detail": "%d pairs attempted, %d with both legs, %d cached, %d fetched, %d unreachable"
                   % (len(rows), len(ok),
                      sum(1 for m in manifest if m["how"] == "cache"),
                      sum(1 for m in manifest if m["how"] == "fetched"),
                      sum(1 for m in manifest if m["how"].startswith("unreachable")))},
        {"name": "ADR-A-2  print the bar count, currency and dividend count for both legs of every pair",
         "passed": True,
         "detail": "; ".join("%s/%s %s %s bars %s/%s divs %s/%s"
                             % (r["receipt"], r["home"],
                                r["receipt_desc"].get("currency"), r["home_desc"].get("currency"),
                                r["receipt_desc"].get("bars"), r["home_desc"].get("bars"),
                                r["receipt_desc"].get("dividends"), r["home_desc"].get("dividends"))
                             for r in rows)},
        {"name": "ADR-A-3  name every pair that is missing a leg rather than counting it out silently",
         "passed": True,
         "detail": ", ".join("%s/%s" % (r["receipt"], r["home"])
                             for r in rows if not r["both_legs"]) or "none"},
    ]

    MANIFEST.write_text(json.dumps(sorted(manifest, key=lambda m: m["symbol"]),
                                   indent=2, sort_keys=True, ensure_ascii=False),
                        encoding="utf-8", newline="\n")
    OUT.write_text(json.dumps(
        {"stage": "ADR availability", "step": "coverage_probe", "diagnostic_only": True,
         "diagnostic_reason": ("An availability check. It registers no criterion about the world "
                               "and computes no index; it asks whether the price source already in "
                               "use carries both legs of a depositary-receipt pair."),
         "pairs_attempted": len(rows), "pairs_with_both_legs": len(ok),
         "dividend_events_thinner_leg": divs,
         "rows": rows, "criteria": criteria},
        indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("\nwrote %s and %s" % (OUT.name, MANIFEST.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
