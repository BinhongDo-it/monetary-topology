"""B24: the same square formula on a convertible pair and on one that is not.

**What this is for.** The B21 criterion census counted twenty-six criteria and
found the two that reach Corollary 1 are both arithmetic, while the nine that
measure the world reach only the instrument. **A criterion in both sets needs a
class pair whose statutory term is zero**, so the index is not forced non-zero
before the data is read, and a carrier where the framework says the square must
vanish.

**The class pair.** In a country whose treaty rate equals its statutory rate, a
treaty-country holder and a holder with no treaty relief face the same
withholding, so `t_ab` is **exactly zero** rather than a difference of two
numbers. What is left in the square is the return difference between two
listings of one claim.

**The two carriers, and the prediction that separates them.**

    convertible      a sponsored receipt can be cancelled into the home line, so
                     a path between the two positions exists, the loop closes,
                     and the framework's square must vanish up to the published
                     conversion cost.
    not convertible  A and H shares cannot be exchanged for one another at any
                     price. The restriction is a hole rather than a term, and the
                     quantity measured there is not a holonomy.

**The statistic is translation invariant on purpose.** The level of the log
parity deviation is identified only up to the receipt ratio, which is a constant
per pair and is not in any price file. **Its spread and its range are free of
that constant**, so nothing here needs a ratio, and none is looked up.

**Both sides are printed and neither is a line.** Section 3 of the design records
that "A and H land inside the cost band" is unreachable, so the A and H side is a
ruler and not a criterion.

Usage, on a machine with network access the first time::

    python experiments/b24_fungibility.py

Rerunning is offline: every series is cached under ``data/raw/adr_probe``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "adr_probe"
B21PX = ROOT / "data" / "raw" / "b21" / "px"
OUT = ROOT / "results" / "b24_fungibility.json"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?range=5y&interval=1d&events=div")
UA = "monetary-topology research binhongd@outlook.com"

#: The receipt, the home line, the venue, the country, and whether that country's
#: treaty rate equals its statutory rate. **Only the last column decides whether a
#: pair carries an exactly zero statutory term**, and it comes from the treaty
#: table computed on this project's own carrier, not from anything fitted here.
PAIRS = [
    ("AZN",  "AZN.L",        "London",     "United Kingdom", "GBP", True),
    ("SHEL", "SHEL.L",       "London",     "United Kingdom", "GBP", True),
    ("BP",   "BP.L",         "London",     "United Kingdom", "GBP", True),
    ("HSBC", "HSBA.L",       "London",     "United Kingdom", "GBP", True),
    ("RIO",  "RIO.L",        "London",     "United Kingdom", "GBP", True),
    ("DEO",  "DGE.L",        "London",     "United Kingdom", "GBP", True),
    ("UL",   "ULVR.L",       "London",     "United Kingdom", "GBP", True),
    ("ASML", "ASML.AS",      "Amsterdam",  "Netherlands",    "EUR", True),
    ("PHG",  "PHIA.AS",      "Amsterdam",  "Netherlands",    "EUR", True),
    ("INFY", "INFY.NS",      "Mumbai",     "India",          "INR", True),
    ("IBN",  "ICICIBANK.NS", "Mumbai",     "India",          "INR", True),
    ("NVS",  "NOVN.SW",      "Zurich",     "Switzerland",    "CHF", False),
    ("NVO",  "NOVO-B.CO",    "Copenhagen", "Denmark",        "DKK", False),
    ("SAP",  "SAP.DE",       "Frankfurt",  "Germany",        "EUR", False),
    ("DB",   "DBK.DE",       "Frankfurt",  "Germany",        "EUR", False),
    ("TTE",  "TTE.PA",       "Paris",      "France",         "EUR", False),
    ("SNY",  "SAN.PA",       "Paris",      "France",         "EUR", False),
    ("TM",   "7203.T",       "Tokyo",      "Japan",          "JPY", False),
    ("HMC",  "7267.T",       "Tokyo",      "Japan",          "JPY", False),
    ("SONY", "6758.T",       "Tokyo",      "Japan",          "JPY", False),
    ("MFG",  "8411.T",       "Tokyo",      "Japan",          "JPY", False),
    ("SAN",  "SAN.MC",       "Madrid",     "Spain",          "EUR", False),
    ("BBVA", "BBVA.MC",      "Madrid",     "Spain",          "EUR", False),
    ("E",    "ENI.MI",       "Milan",      "Italy",          "EUR", False),
    ("PBR",  "PETR3.SA",     "Sao Paulo",  "Brazil",         "BRL", False),
    # PBR is the receipt on the ordinary share. Pairing it with PETR4, the
    # preferred, was an error in the first version of this list: two different
    # claims with two different prices. The wrong pair is kept and printed
    # rather than removed, because its reading is what the error looks like.
    ("PBR",  "PETR4.SA",     "Sao Paulo",  "Brazil",         "BRL", False),
    ("VALE", "VALE3.SA",     "Sao Paulo",  "Brazil",         "BRL", False),
    ("BHP",  "BHP.AX",       "Sydney",     "Australia",      "AUD", False),
    # ---- the same-bell block -------------------------------------------------
    # Toronto keeps New York's hours and moves its clocks on New York's dates, so
    # every pair below has a clock gap of zero all year. **These are interlisted
    # common shares and not receipts**: one register, two places to trade, no
    # depositary and no fee. Their bound is exchange-transfer friction, which is
    # smaller than a depositary fee and is not published as one number.
    #
    # The statutory column is False because Canada's treaty rate and its statutory
    # rate differ. **It does not reach the statistic**: every figure reported here
    # is translation invariant, and a withholding difference shifts the level of
    # the deviation rather than its spread.
    ("TD",   "TD.TO",        "Toronto",    "Canada",         "CAD", False),
    ("BNS",  "BNS.TO",       "Toronto",    "Canada",         "CAD", False),
    ("RY",   "RY.TO",        "Toronto",    "Canada",         "CAD", False),
    ("BMO",  "BMO.TO",       "Toronto",    "Canada",         "CAD", False),
    ("CM",   "CM.TO",        "Toronto",    "Canada",         "CAD", False),
    ("MFC",  "MFC.TO",       "Toronto",    "Canada",         "CAD", False),
    ("SLF",  "SLF.TO",       "Toronto",    "Canada",         "CAD", False),
    ("ENB",  "ENB.TO",       "Toronto",    "Canada",         "CAD", False),
    ("TRP",  "TRP.TO",       "Toronto",    "Canada",         "CAD", False),
    ("SU",   "SU.TO",        "Toronto",    "Canada",         "CAD", False),
    ("CNQ",  "CNQ.TO",       "Toronto",    "Canada",         "CAD", False),
    ("PBA",  "PPL.TO",       "Toronto",    "Canada",         "CAD", False),
    ("CVE",  "CVE.TO",       "Toronto",    "Canada",         "CAD", False),
    ("IMO",  "IMO.TO",       "Toronto",    "Canada",         "CAD", False),
    ("CP",   "CP.TO",        "Toronto",    "Canada",         "CAD", False),
    ("CNI",  "CNR.TO",       "Toronto",    "Canada",         "CAD", False),
    ("BCE",  "BCE.TO",       "Toronto",    "Canada",         "CAD", False),
    ("TU",   "T.TO",         "Toronto",    "Canada",         "CAD", False),
    ("AEM",  "AEM.TO",       "Toronto",    "Canada",         "CAD", False),
    ("WPM",  "WPM.TO",       "Toronto",    "Canada",         "CAD", False),
    ("FNV",  "FNV.TO",       "Toronto",    "Canada",         "CAD", False),
    ("TECK", "TECK-B.TO",    "Toronto",    "Canada",         "CAD", False),
    ("KGC",  "K.TO",         "Toronto",    "Canada",         "CAD", False),
    ("WCN",  "WCN.TO",       "Toronto",    "Canada",         "CAD", False),
    ("QSR",  "QSR.TO",       "Toronto",    "Canada",         "CAD", False),
    ("NTR",  "NTR.TO",       "Toronto",    "Canada",         "CAD", False),
    ("GIB",  "GIB-A.TO",     "Toronto",    "Canada",         "CAD", False),
    ("TRI",  "TRI.TO",       "Toronto",    "Canada",         "CAD", False),
    ("MGA",  "MG.TO",        "Toronto",    "Canada",         "CAD", False),
    ("FTS",  "FTS.TO",       "Toronto",    "Canada",         "CAD", False),
    ("AQN",  "AQN.TO",       "Toronto",    "Canada",         "CAD", False),
    ("BN",   "BN.TO",        "Toronto",    "Canada",         "CAD", False),
    ("EQNR", "EQNR.OL",      "Oslo",       "Norway",         "NOK", False),
    ("KB",   "105560.KS",    "Seoul",      "Korea",          "KRW", False),
]

#: Hours the venue's close is away from the New York close. Published trading
#: hours, nothing estimated. Toronto is the zero, which is what makes it the
#: control for the non-synchronous-close term rather than an extra observation.
CLOCK_GAP = {"Toronto": 0.0,      # 16:00 ET, the same bell
             # Sao Paulo closes 17:00 BRT and Brazil has kept no summer time since
             # 2019, so the gap against the New York bell is 0 h from March to
             # November and 1 h for the rest of the year. **Toronto is the only
             # venue here that keeps the same bell all year**, because it moves its
             # clocks on the same dates as New York.
             "Sao Paulo": 0.5,
             "London": 4.5,       # 16:30 local
             "Amsterdam": 4.5, "Paris": 4.5, "Frankfurt": 4.5,   # 17:30 CET
             "Zurich": 4.5, "Milan": 4.5, "Madrid": 4.5,
             "Copenhagen": 5.0,   # 17:00 CET
             "Oslo": 5.3,         # 16:20 CET
             "Mumbai": 10.0,      # 15:30 IST
             "Tokyo": 15.0,       # 15:00 JST
             "Seoul": 14.5,       # 15:30 KST
             "Sydney": 14.0}      # 16:00 AEST

#: Local units per USD is what the arithmetic wants. The first spelling that
#: returns data is used and which one it was is recorded, the same way this
#: repository already handles a rate with several spellings.
FX_ALTERNATES = {c: ["USD%s=X" % c, "%sUSD=X" % c] for c in
                 ("GBP", "EUR", "INR", "CHF", "DKK", "JPY", "BRL", "AUD", "CAD", "NOK", "KRW")}



def fixed(o, nd: int = 8):
    """Every float written to disk goes through here.

    **The derived-file rule this repository already carries**: write floats
    through an explicit format rather than through ``repr``, so a last-digit
    difference between two builds does not surface as a text diff. It was not
    hypothetical here — the same code over the same cached bytes produced
    last-digit differences between a Windows run and a Linux one, and the record
    stopped reproducing byte for byte. Eight decimals is far below anything this
    file reports, which is one decimal of a basis point.
    """
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: fixed(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [fixed(v, nd) for v in o]
    return o

def path_for(sym: str) -> Path:
    return CACHE / (sym.replace("=", "_").replace("/", "_") + ".json")


def fetch(sym: str) -> tuple[dict | None, str]:
    p = path_for(sym)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")), "cache"
        except json.JSONDecodeError:
            bad, n = p.with_suffix(p.suffix + ".partial"), 0
            while bad.exists():
                n += 1
                bad = p.with_suffix(p.suffix + f".partial{n}")
            p.rename(bad)                      # renamed, never removed
    req = urllib.request.Request(CHART.format(sym=sym), headers={"User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
    except (urllib.error.URLError, TimeoutError) as e:
        return None, "unreachable: %s" % type(e).__name__
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return None, "unparseable"
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".writing")
    tmp.write_bytes(raw)
    tmp.replace(p)
    time.sleep(0.4)
    return d, "fetched"


def closes(d: dict | None) -> dict[str, float]:
    """date -> close, dropping any bar the source left null."""
    if not d:
        return {}
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        return {}
    r = res[0]
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    cl = q.get("close") or []
    out = {}
    for t, c in zip(ts, cl):
        if c is None or c <= 0:
            continue
        out[time.strftime("%Y-%m-%d", time.gmtime(t))] = float(c)
    return out


def csv_closes(p: Path) -> dict[str, float]:
    if not p.exists():
        return {}
    out = {}
    for row in csv.DictReader(p.open(encoding="utf-8")):
        try:
            c = float(row["Close"])
        except (KeyError, ValueError, TypeError):
            continue
        if c > 0:
            out[row["Date"][:10]] = c
    return out


def deviation(a: dict, h: dict, fx: dict, invert_fx: bool) -> tuple[list[str], list[float]]:
    """log P_receipt - log P_home + log(local units per USD), on common dates.

    The receipt ratio is a constant per pair and drops out of every statistic
    reported below, so it is never looked up.
    """
    days = sorted(set(a) & set(h) & set(fx))
    dev = []
    for d in days:
        rate = fx[d]
        if invert_fx:
            rate = 1.0 / rate
        dev.append(math.log(a[d]) - math.log(h[d]) + math.log(rate))
    return days, dev


def stats(dev: list[float]) -> dict:
    """Everything here is translation invariant, so no ratio is needed."""
    if len(dev) < 30:
        return {"n": len(dev), "readable": False}
    s = sorted(dev)
    d1 = [1e4 * (b - a) for a, b in zip(dev, dev[1:])]
    return {"n": len(dev), "readable": True,
            "spread_p10_p90_bp": 1e4 * (s[9 * len(s) // 10] - s[len(s) // 10]),
            "range_bp": 1e4 * (s[-1] - s[0]),
            "iqr_bp": 1e4 * (s[3 * len(s) // 4] - s[len(s) // 4]),
            "daily_change_sd_bp": statistics.pstdev(d1) if len(d1) > 1 else float("nan")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="use only what is cached; report anything missing")
    args = ap.parse_args()

    # ---- the exchange rates, one spelling per currency, recorded ------------
    # **Every attempt is recorded with its own outcome.** The first version of
    # this block wrote one word, ``unavailable``, for a currency that was
    # skipped offline and for one whose fetch failed, and the two are opposite
    # instructions to whoever reads the record next. A field that reads the same
    # for "checked and absent" and "never checked" has nothing guarding it.
    fx, fx_used = {}, {}
    for ccy, alts in sorted(FX_ALTERNATES.items()):
        tried = []
        for sym in alts:
            if args.offline and not path_for(sym).exists():
                tried.append({"symbol": sym, "outcome": "skipped, offline and not cached"})
                continue
            d, how = fetch(sym)
            c = closes(d)
            tried.append({"symbol": sym, "outcome": how, "bars": len(c)})
            if len(c) > 100:
                fx[ccy] = (c, sym.startswith(ccy))   # "<CCY>USD=X" is USD per unit, invert
                fx_used[ccy] = {"symbol": sym, "how": how, "bars": len(c),
                                "inverted": sym.startswith(ccy), "attempts": tried}
                break
        else:
            why = ("skipped, offline" if all(a["outcome"].startswith("skipped") for a in tried)
                   else "every spelling failed")
            fx_used[ccy] = {"symbol": None, "how": why, "bars": 0, "attempts": tried}

    net = [a for u in fx_used.values() for a in u["attempts"]]
    reached = sum(1 for a in net if a["outcome"] in ("fetched", "cache"))
    failed = sum(1 for a in net if a["outcome"].startswith("unreachable"))
    skipped = sum(1 for a in net if a["outcome"].startswith("skipped"))
    print("mode: %s. exchange-rate attempts: %d reached, %d unreachable, %d skipped."
          % ("offline" if args.offline else "online", reached, failed, skipped))
    if failed and not reached:
        print("  **the price source was attempted and did not answer.** "
              "This is not the same as having run offline, and the record says which.")
    print("exchange rates, one spelling per currency:")
    for c, u in sorted(fx_used.items()):
        print("  %-4s %-12s %-32s %5s bars  inverted %s"
              % (c, u["symbol"], u["how"], u["bars"], u.get("inverted")))
        if u["symbol"] is None:
            for a in u["attempts"]:
                print("       tried %-12s %s" % (a["symbol"], a["outcome"]))

    # ---- the convertible carrier -------------------------------------------
    rows, dev_by_pair, ccy_series = [], {}, True
    for adr, home, venue, country, ccy, zero_term in PAIRS:
        r = {"receipt": adr, "home": home, "venue": venue, "country": country,
             "currency": ccy, "statutory_term_zero": zero_term,
             "clock_gap_hours": CLOCK_GAP[venue]}
        if ccy not in fx:
            r.update(readable=False, why="no exchange rate for %s" % ccy)
            rows.append(r)
            continue
        a = closes(fetch(adr)[0] if not args.offline or path_for(adr).exists() else None)
        h = closes(fetch(home)[0] if not args.offline or path_for(home).exists() else None)
        if not a or not h:
            r.update(readable=False, why="a leg is missing from the cache")
            rows.append(r)
            continue
        rate, inv = fx[ccy]
        days, dev = deviation(a, h, rate, inv)
        # **Keyed by both legs.** Keeping a known-wrong row in the list, which is
        # what this repository's no-deletion rule asks for, put two rows under one
        # receipt. A key of the receipt alone then made the second row overwrite
        # the first, and the same series appeared twice under two names.
        dev_by_pair[(adr, home)] = dict(zip(days, dev))
        st = stats(dev)
        r.update(st)
        r["readable"] = st.get("readable", False)
        if days:
            r["first"], r["last"] = days[0], days[-1]
        rows.append(r)

    good = [r for r in rows if r.get("readable")]
    zero = [r for r in good if r["statutory_term_zero"]]

    print("\nthe convertible carrier. **Every pair is printed, none is selected.**")
    print("  %-6s %-13s %-11s %5s %10s %10s %10s %6s"
          % ("ADR", "home", "venue", "n", "p10-p90", "range", "d/day sd", "clock"))
    for r in sorted(rows, key=lambda r: (not r["statutory_term_zero"], r["receipt"])):
        if not r.get("readable"):
            print("  %-6s %-13s %-11s  unreadable: %s"
                  % (r["receipt"], r["home"], r["venue"], r.get("why", "too few days")))
            continue
        print("  %-6s %-13s %-11s %5d %10.1f %10.1f %10.2f %6.1f"
              % (r["receipt"], r["home"], r["venue"], r["n"],
                 r["spread_p10_p90_bp"], r["range_bp"], r["daily_change_sd_bp"],
                 r["clock_gap_hours"]))

    # ---- the carrier that is not convertible, as a ruler --------------------
    # **On the same window.** The receipt cache is five years and the A and H
    # panel is twenty, so reading the second over its whole span would compare a
    # spread taken over four times the history. The window is taken from the
    # receipt side and the full-span figure is printed beside it rather than
    # dropped.
    span = sorted(r["first"] for r in good if r.get("first")) or [""]
    span_hi = sorted(r["last"] for r in good if r.get("last")) or [""]
    win_lo, win_hi = (span[0], span_hi[-1]) if good else ("", "9999")
    cny, hkd = csv_closes(B21PX / "CNY=X.csv"), csv_closes(B21PX / "HKD=X.csv")
    ah_rows, ah_full = [], []
    if cny and hkd:
        import re as _re
        page = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"
        pat = _re.compile(r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
                          r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", _re.S)
        seen = set()
        pairs = []
        if page.exists():
            for m in pat.finditer(page.read_text(encoding="utf-8")):
                name, hh, _, aa, mkt, _ = m.groups()
                if hh in seen:
                    continue
                seen.add(hh)
                pairs.append((name.strip()[:22],
                              (hh[1:] if hh.startswith("0") else hh) + ".HK",
                              f"{aa}.{'SS' if mkt == 'SH' else 'SZ'}"))
        for name, htk, atk in pairs:
            A = csv_closes(B21PX / (atk + ".csv"))
            H = csv_closes(B21PX / (htk + ".csv"))
            if not A or not H:
                continue
            common = sorted(set(A) & set(H) & set(cny) & set(hkd))
            for days, sink in ((common, ah_full),
                               ([d for d in common if win_lo <= d <= win_hi], ah_rows)):
                if not days:
                    continue
                dev = [math.log(A[d]) - math.log(cny[d]) - math.log(H[d]) + math.log(hkd[d])
                       for d in days]
                st = stats(dev)
                if st.get("readable"):
                    sink.append({"name": name, "a": atk, "h": htk, **st,
                                 "first": days[0], "last": days[-1]})

    def med(rs, k):
        v = sorted(r[k] for r in rs)
        return v[len(v) // 2] if v else float("nan")

    print("\nthe carrier that cannot be converted, read by the same function.")
    print("  window taken from the receipt side: %s to %s" % (win_lo or "?", win_hi or "?"))
    if ah_rows:
        print("  on that window: %d pairs, median p10-p90 %.0f bp, median range %.0f bp"
              % (len(ah_rows), med(ah_rows, "spread_p10_p90_bp"), med(ah_rows, "range_bp")))
    else:
        print("  on that window: nothing readable")
    if ah_full:
        print("  over the whole panel, printed and not compared: %d pairs, "
              "median p10-p90 %.0f bp" % (len(ah_full), med(ah_full, "spread_p10_p90_bp")))

    print("\nthe two carriers side by side, medians in basis points:")
    print("  %-34s %10s %10s %10s" % ("", "p10-p90", "range", "d/day sd"))
    for lab, rs in (("convertible, statutory term zero", zero),
                    ("convertible, all readable pairs", good),
                    ("A and H, statutory term zero", ah_rows)):
        if rs:
            print("  %-34s %10.0f %10.0f %10.2f"
                  % (lab, med(rs, "spread_p10_p90_bp"), med(rs, "range_bp"),
                     med(rs, "daily_change_sd_bp")))

    by_venue = {}
    for r in good:
        by_venue.setdefault(r["venue"], []).append(r)

    # ---- the exchange rate cancelled exactly, where a venue has two pairs ----
    # **One series in this construction is not a price of either leg.** The daily
    # exchange rate is cut at its own hour, and neither closing bell is that hour,
    # so a part of every deviation above is the rate moving between three clocks.
    # Two pairs at the same venue share that series exactly, so the difference of
    # their deviations carries no exchange rate at all. Nothing is estimated here
    # and no rate is modelled; one term is removed by subtraction.
    pair_diffs, same_receipt = [], []
    for venue, rs in sorted(by_venue.items()):
        if len(rs) < 2 or ccy_series is None:
            continue
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if a["receipt"] == b["receipt"]:
                    # One receipt against two home lines is a different question and
                    # its difference is not a two-claim dispersion. Named, not run.
                    same_receipt.append("%s: %s and %s" % (a["receipt"], a["home"], b["home"]))
                    continue
                da = dev_by_pair.get((a["receipt"], a["home"]))
                db = dev_by_pair.get((b["receipt"], b["home"]))
                if not da or not db:
                    continue
                days = sorted(set(da) & set(db))
                if len(days) < 30:
                    continue
                st = stats([da[d] - db[d] for d in days])
                if st.get("readable"):
                    pair_diffs.append({"venue": venue, "gap_hours": CLOCK_GAP[venue],
                                       "a": a["receipt"], "b": b["receipt"],
                                       "a_home": a["home"], "b_home": b["home"],
                                       "label": "%s/%s - %s/%s" % (a["receipt"], a["home"],
                                                                   b["receipt"], b["home"]),
                                       **st})

    print("\nthe exchange rate cancelled by subtracting two pairs at one venue.")
    by_v = {}
    for r in pair_diffs:
        by_v.setdefault(r["venue"], []).append(r)
    print("  %-11s %5s %8s %8s %8s %8s" % ("venue", "pairs", "min", "p25", "median", "max"))
    for v in sorted(by_v, key=lambda v: CLOCK_GAP[v]):
        s = sorted(r["spread_p10_p90_bp"] for r in by_v[v])
        print("  %-11s %5d %8.1f %8.1f %8.1f %8.1f"
              % (v, len(s), s[0], s[len(s) // 4], s[len(s) // 2], s[-1]))
    print("  every pairing is in the record. The rows below are the three smallest")
    print("  and the three largest per venue, and the count of what sits between.")
    print("  %-11s %-29s %5s %10s %10s" % ("venue", "pairing", "n", "p10-p90", "d/day sd"))
    for v in sorted(by_v, key=lambda v: CLOCK_GAP[v]):
        rs = sorted(by_v[v], key=lambda r: r["spread_p10_p90_bp"])
        show = rs if len(rs) <= 6 else rs[:3] + rs[-3:]
        for r in show:
            print("  %-11s %-29s %5d %10.1f %10.2f"
                  % (r["venue"], r["label"], r["n"],
                     r["spread_p10_p90_bp"], r["daily_change_sd_bp"]))
        if len(rs) > 6:
            print("  %-11s %-29s %5s  %d more between them, all in the record"
                  % ("", "", "", len(rs) - 6))
    if same_receipt:
        print("  not run, one receipt against two home lines: %s" % "; ".join(same_receipt))
    if pair_diffs:
        print("  median with the rate removed: %.0f bp, against %.0f bp with it in"
              % (med(pair_diffs, "spread_p10_p90_bp"), med(good, "spread_p10_p90_bp")))
    print("\nthe clock, printed and not scored. Toronto is the zero-gap point:")
    for v in sorted(by_venue, key=lambda v: CLOCK_GAP[v]):
        print("  %-11s gap %4.1f h  n %d  median p10-p90 %8.0f bp"
              % (v, CLOCK_GAP[v], len(by_venue[v]), med(by_venue[v], "spread_p10_p90_bp")))

    crit = [
      {"name": "B24-0  the record says whether the price source was attempted, and "
               "distinguishes a skipped run from a failed one",
       "passed": True,
       "detail": "mode %s; %d attempts reached, %d unreachable, %d skipped"
                 % ("offline" if args.offline else "online", reached, failed, skipped)},
      {"name": "B24-1  every declared pair is aligned and its outcome printed, "
               "unreadable pairs named rather than dropped",
       "passed": len(rows) == len(PAIRS),
       "detail": "%d pairs declared, %d readable, unreadable: %s; exchange rates: %s"
                 % (len(PAIRS), len(good),
                    ", ".join("%s (%s)" % (r["receipt"], r.get("why", "few days"))
                              for r in rows if not r.get("readable")) or "none",
                    ", ".join("%s %s" % (c, u["symbol"]) for c, u in sorted(fx_used.items())))},
      {"name": "B24-2  print the deviation's spread and range for every pair, "
               "with the published conversion cost beside it",
       "passed": True,
       "detail": ("published cost is 0.01 to 0.05 USD per ADS, which on a 50 USD receipt "
                  "is 2 to 10 bp one way; "
                  + "; ".join("%s %.0f" % (r["receipt"], r["spread_p10_p90_bp"]) for r in good))},
      {"name": "B24-3  the same function on both carriers, both printed, no line on either",
       "passed": bool(zero) and bool(ah_rows),
       "detail": "convertible with a zero statutory term: median p10-p90 %.0f bp over %d pairs; "
                 "A and H: median p10-p90 %.0f bp over %d pairs"
                 % (med(zero, "spread_p10_p90_bp"), len(zero),
                    med(ah_rows, "spread_p10_p90_bp"), len(ah_rows))},
      {"name": "B24-5  the exchange rate removed by subtracting two pairs at one venue, "
               "printed beside the figure that still carries it",
       "passed": True,
       "detail": ("median with the rate removed %.0f bp against %.0f bp with it in, over %d "
                  "same-venue pairings" % (med(pair_diffs, "spread_p10_p90_bp"),
                                           med(good, "spread_p10_p90_bp"), len(pair_diffs))
                  + ("; not run, one receipt against two home lines: "
                     + "; ".join(same_receipt) if same_receipt else ""))
                 if pair_diffs else "no venue carried two readable pairs"},
      {"name": "B24-4  the clock gap is printed per venue and not scored",
       "passed": True,
       "detail": "; ".join("%s %.1fh %.0f bp" % (v, CLOCK_GAP[v], med(by_venue[v], "spread_p10_p90_bp"))
                           for v in sorted(by_venue, key=lambda v: CLOCK_GAP[v]))},
    ]

    OUT.write_text(json.dumps(fixed(
        {"stage": "B24", "step": "fungibility", "diagnostic_only": True,
         "diagnostic_reason": ("The station is not closed until both carriers have been read and "
                               "the clock term has been separated from the rest."),
         "mode": "offline" if args.offline else "online",
         "network": {"reached": reached, "unreachable": failed, "skipped": skipped},
         "window": {"from": win_lo, "to": win_hi},
         "exchange_rates": fx_used, "convertible": rows,
         "a_and_h_on_window": ah_rows, "a_and_h_full_panel": ah_full,
         "rate_cancelled_pairings": pair_diffs,
         "pairings_not_run_same_receipt": same_receipt,
         "criteria": crit}),
        indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("\nwrote %s: %d criteria, %d passing"
          % (OUT.name, len(crit), sum(1 for c in crit if c["passed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
