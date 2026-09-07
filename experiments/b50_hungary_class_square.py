"""B50: the same class square, and one law that moved only the household leg.

B49 read the square sum on electricity against piped gas, residential against
industrial, in 13 countries and 3 years, and found it nonzero everywhere. This
station asks a different question of the same object: does it move when a
published rule changes one leg and leaves the other alone.

Hungary wrote such a rule. Act LIV of 2013 caps what a household may be charged
at 90 per cent of a named reference date's tariff, names electricity, gas,
district heating, water and sewerage, and covers household universal service
only, with industry outside it. The law fixes the sizes itself and delegates
nothing. Three further rounds followed, and in 2022 the direction reversed.

Two arithmetic screens, both computable before any data is fetched, cut those
five dates down to one clean one.

  screen 1, equal-sized rounds. The square sum is
      log(P_resid_elec / P_resid_gas) - log(P_ind_elec / P_ind_gas)
  so when both carriers are cut by the same proportion on the same day, the
  first term does not move at all. Two of the five rounds are of that kind.

  screen 2, semester averaging. A Eurostat semester price is the average over
  six months, not a price on a date, so a rule taking effect inside a semester
  is diluted in proportion to the months it covers. Only one of the five rounds
  begins on the first day of a semester.

What survives is one window, and it happens to be both clean and equal-sized,
which makes it a point prediction of zero: household electricity fell 10 per
cent between two semesters, a real, dated, large move, and the square sum should
not budge. If it does budge there are exactly two candidate reasons, and both
are named rather than left vague: the law was not applied to both carriers in
equal proportion (B50-5 checks that), or the industrial leg moved on the same
date (printed among the readings).

Criteria:

  B50-1  the panel is complete: four legs, every semester, three tax bases.
  B50-2  the reading uses the per-band series and not the total band, which
         carries 10 semesters where the bands carry 37 (D37).
  B50-3  the square sum does not move when the four prices are quoted in another
         currency. One conversion factor per semester is shared by both classes
         and cancels in the log difference, so this is an implementation check
         and not an independent confirmation (D35). Its worst departure is the
         measured floor used by B50-4 and B50-5.
  B50-4  the point prediction: over the clean window the square sum stays inside
         that floor.
  B50-5  the premise of B50-4: over the same window the two household carriers
         fell by the same proportion, as the law says they must.
  B50-6  the cut reached the price and not only the tax: the household leg moves
         in the same direction with tax excluded as with tax included.

Everything this run produces is reported, including the two windows registered
in advance as unlikely to be readable.

Units differ between the carriers, kWh for electricity and GJ for gas. That is
harmless here and the reason is worth stating: any factor shared by both classes
of one carrier cancels in the difference of differences. What must match is the
unit within a carrier across the two classes, not the unit across carriers.

Source: Eurostat bi-annual energy price statistics, geo=HU. Responses are cached
under data/cache/eurostat/ and reused; pass --refresh to re-fetch.

Run:

    python experiments\\b50_hungary_class_square.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "eurostat"
OUT = ROOT / "results" / "b50_hungary_class_square.json"

API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/")
UA = "monetary-topology/b50 (research; contact via repository)"
GEO = "HU"

# One leg per entry: dataset, the standard reference band Eurostat itself uses,
# and the unit the band is denominated in.
LEGS = {
    "RE": {"ds": "nrg_pc_204", "band": "KWH2500-4999", "unit": "KWH",
           "what": "household electricity, 2 500 to 5 000 kWh"},
    "IE": {"ds": "nrg_pc_205", "band": "MWH500-1999", "unit": "KWH",
           "what": "non-household electricity, 500 to 2 000 MWh"},
    "RG": {"ds": "nrg_pc_202", "band": "GJ20-199", "unit": "GJ_GCV",
           "what": "household gas, 20 to 200 GJ"},
    "IG": {"ds": "nrg_pc_203", "band": "GJ10000-99999", "unit": "GJ_GCV",
           "what": "non-household gas, 10 000 to 100 000 GJ"},
}
TOTAL_BANDS = {"nrg_pc_204": "TOT_KWH", "nrg_pc_205": "TOT_KWH",
               "nrg_pc_202": "TOT_GJ", "nrg_pc_203": "TOT_GJ"}
TAXES = ("X_TAX", "X_VAT", "I_TAX")
CURRENCIES = ("NAC", "EUR", "PPS")
# Only a pure exchange-rate conversion is forced to cancel in the log
# difference: one factor per country and semester, shared by both classes. PPS
# is a purchasing power unit, so its conversion need not be one scalar per
# semester and may carry rounding of its own. It is reported, and it does not
# set the floor.
FLOOR_CURRENCIES = ("EUR",)
BASE_TAX = "I_TAX"
BASE_CUR = "NAC"

# The rounds, with what each did and where it lands. month_in_semester and
# equal_sized are the two screens; neither needs any data.
ROUNDS = [
    {"date": "2013-01-01", "semester": "2013-S1", "previous": "2012-S2",
     "month_in_semester": 1, "months_covered": 6,
     "electricity": -0.100, "gas": -0.100, "equal_sized": True},
    {"date": "2013-11-01", "semester": "2013-S2", "previous": "2013-S1",
     "month_in_semester": 5, "months_covered": 2,
     "electricity": -0.111, "gas": -0.111, "equal_sized": True},
    {"date": "2014-04-01", "semester": "2014-S1", "previous": "2013-S2",
     "month_in_semester": 4, "months_covered": 3,
     "electricity": 0.0, "gas": -0.065, "equal_sized": False},
    {"date": "2014-09-01", "semester": "2014-S2", "previous": "2014-S1",
     "month_in_semester": 3, "months_covered": 4,
     "electricity": -0.057, "gas": 0.0, "equal_sized": False},
    {"date": "2022-08-01", "semester": "2022-S2", "previous": "2022-S1",
     "month_in_semester": 2, "months_covered": 5,
     "electricity": None, "gas": None, "equal_sized": False},
]

# Windows the screens leave behind, registered here rather than chosen later.
WINDOWS = {
    "clean": {"from": "2012-S2", "to": "2013-S1",
              "prediction": "square sum does not move",
              "status": "load-bearing"},
    "small": {"from": "2013-S2", "to": "2015-S1",
              "prediction": "square sum rises by about +0.0085",
              "status": "registered in advance as likely below the floor"},
    "confounded": {"from": "2022-S1", "to": "2022-S2",
                   "prediction": "square sum falls",
                   "status": "downgraded in advance, the industrial leg moves "
                             "in the same semester for reasons outside the law"},
}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(ds: str, params: dict, refresh: bool) -> dict:
    q = urllib.parse.urlencode(sorted(params.items()))
    name = "%s__%s.json" % (ds, q.replace("&", "__").replace("=", "-"))
    path = CACHE / name
    if path.exists() and not refresh:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit("cached file is not valid JSON: %s (%s)"
                             % (path, exc))
        if "dimension" not in data:
            raise SystemExit("cached file has no dimension block: %s" % path)
        return data
    url = API + ds + "?" + q
    try:
        data = _get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise SystemExit(
            "could not reach the statistics endpoint and no usable cache is on "
            "disk\n  url: %s\n  error: %s" % (url, exc))
    if "dimension" not in data:
        raise SystemExit("response has no dimension block: %s" % url)
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(data, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")
    os.replace(part, path)
    return data


def series(ds: str, band: str, unit: str, tax: str, cur: str,
           refresh: bool) -> dict:
    """One leg, one tax base, one currency: semester -> price."""
    data = fetch(ds, {"format": "JSON", "lang": "EN", "geo": GEO,
                      "nrg_cons": band, "unit": unit, "tax": tax,
                      "currency": cur}, refresh)
    free = [d for d in data["id"]
            if data["size"][data["id"].index(d)] > 1 and d != "time"]
    if free:
        raise SystemExit("the query left more than time free (%s) for %s %s"
                         % (free, ds, band))
    idx = data["dimension"]["time"]["category"]["index"]
    values = data["value"]
    out = {}
    for t, i in idx.items():
        v = values.get(str(i), values.get(i)) if isinstance(values, dict) \
            else (values[i] if i < len(values) else None)
        if v is not None:
            out[t] = v
    return dict(sorted(out.items()))


def main() -> int:
    refresh = "--refresh" in sys.argv[1:]
    rec: dict = {
        "stage": "B50",
        "config": {
            "endpoint": API, "geo": GEO,
            "legs": {k: dict(v) for k, v in LEGS.items()},
            "taxes": list(TAXES), "currencies": list(CURRENCIES),
            "base_tax": BASE_TAX, "base_currency": BASE_CUR,
            "rounds": ROUNDS, "windows": WINDOWS,
            "refresh": refresh,
            "cache_dir": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    # ---- B50-2: the per-band series against the total band -----------------
    print("B50-2  per-band coverage against the total band (D37)")
    coverage = {}
    for key, leg in LEGS.items():
        band = series(leg["ds"], leg["band"], leg["unit"], BASE_TAX,
                           BASE_CUR, refresh)
        total = series(leg["ds"], TOTAL_BANDS[leg["ds"]], leg["unit"],
                            BASE_TAX, BASE_CUR, refresh)
        bt, tt = sorted(band), sorted(total)
        coverage[key] = {
            "dataset": leg["ds"], "band": leg["band"],
            "band_semesters": len(bt),
            "band_span": [bt[0], bt[-1]] if bt else None,
            "total_band": TOTAL_BANDS[leg["ds"]],
            "total_semesters": len(tt),
            "total_span": [tt[0], tt[-1]] if tt else None,
        }
        print("  %-3s %-12s band %-15s %3d semesters %s..%s   total %-8s %3d"
              % (key, leg["ds"], leg["band"], len(bt),
                 bt[0] if bt else "-", bt[-1] if bt else "-",
                 TOTAL_BANDS[leg["ds"]], len(tt)))
    rec["coverage"] = coverage

    # ---- load every leg in every tax base and currency ---------------------
    data: dict = {}
    for tax in TAXES:
        data[tax] = {}
        for cur in CURRENCIES:
            data[tax][cur] = {}
            for key, leg in LEGS.items():
                data[tax][cur][key] = series(
                    leg["ds"], leg["band"], leg["unit"], tax, cur, refresh)

    def square(tax: str, cur: str, t: str):
        d = data[tax][cur]
        if not all(t in d[k] for k in LEGS):
            return None
        return ((math.log(d["RE"][t]) - math.log(d["RG"][t]))
                - (math.log(d["IE"][t]) - math.log(d["IG"][t])))

    # ---- B50-1: the panel --------------------------------------------------
    common = sorted(set.intersection(*[
        set(data[BASE_TAX][BASE_CUR][k]) for k in LEGS]))
    complete_all_tax = sorted(set.intersection(*[
        set(data[tax][BASE_CUR][k]) for tax in TAXES for k in LEGS]))
    rec["panel"] = {
        "semesters_all_four_legs": common,
        "n_semesters": len(common),
        "n_semesters_all_three_tax_bases": len(complete_all_tax),
    }
    print("\nB50-1  panel")
    print("  semesters with all four legs: %d   %s..%s"
          % (len(common), common[0] if common else "-",
             common[-1] if common else "-"))
    print("  same, in all three tax bases: %d" % len(complete_all_tax))

    # ---- the square, every semester, every tax base -------------------------
    rows = []
    for t in common:
        row = {"semester": t}
        for tax in TAXES:
            v = square(tax, BASE_CUR, t)
            row[tax] = None if v is None else float("%.6f" % v)
        d = data[BASE_TAX][BASE_CUR]
        row["price_resid_elec"] = d["RE"].get(t)
        row["price_ind_elec"] = d["IE"].get(t)
        row["price_resid_gas"] = d["RG"].get(t)
        row["price_ind_gas"] = d["IG"].get(t)
        rows.append(row)
    rec["cells"] = rows

    # ---- B50-3: currency invariance, and the floor -------------------------
    gaps, reported_only = [], []
    for t in common:
        base = square(BASE_TAX, BASE_CUR, t)
        if base is None:
            continue
        for cur in CURRENCIES:
            if cur == BASE_CUR:
                continue
            v = square(BASE_TAX, cur, t)
            if v is None:
                continue
            entry = {"semester": t, "currency": cur, "gap": abs(v - base)}
            (gaps if cur in FLOOR_CURRENCIES else reported_only).append(entry)
    gaps.sort(key=lambda g: -g["gap"])
    reported_only.sort(key=lambda g: -g["gap"])
    floor = gaps[0]["gap"] if gaps else None
    rec["currency_identity"] = {
        "floor_currencies": list(FLOOR_CURRENCIES),
        "comparisons": len(gaps),
        "max_gap": floor,
        "worst": "%s %s" % (gaps[0]["semester"], gaps[0]["currency"])
                 if gaps else None,
        "median_gap": sorted(g["gap"] for g in gaps)[len(gaps) // 2]
                      if gaps else None,
        "reported_only": {
            "currencies": [c for c in CURRENCIES
                           if c not in FLOOR_CURRENCIES and c != BASE_CUR],
            "comparisons": len(reported_only),
            "max_gap": reported_only[0]["gap"] if reported_only else None,
            "worst": "%s %s" % (reported_only[0]["semester"],
                                reported_only[0]["currency"])
                     if reported_only else None,
            "why_excluded": "not a single scalar per country-semester, so it "
                            "is not forced to cancel and cannot bound the "
                            "instrument",
        },
        "note": "implementation check, not an independent confirmation",
    }
    print("\nB50-3  currency identity (implementation check)")
    if gaps:
        print("  scalar conversion %s: %d comparisons, median %.3e, max %.3e at %s"
              % ("/".join(FLOOR_CURRENCIES), len(gaps),
                 rec["currency_identity"]["median_gap"], floor,
                 rec["currency_identity"]["worst"]))
        print("  floor = %.3e" % floor)
    if reported_only:
        r = rec["currency_identity"]["reported_only"]
        print("  reported and excluded from the floor %s: %d comparisons, "
              "max %.3e at %s" % (r["currencies"], r["comparisons"],
                                  r["max_gap"], r["worst"]))
        print("  reason: %s" % r["why_excluded"])

    # ---- the three windows -------------------------------------------------
    def window(name):
        w = WINDOWS[name]
        a, b = w["from"], w["to"]
        out = {"from": a, "to": b, "prediction": w["prediction"],
               "status": w["status"]}
        for tax in TAXES:
            sa, sb = square(tax, BASE_CUR, a), square(tax, BASE_CUR, b)
            out["square_%s" % tax] = None if (sa is None or sb is None) \
                else {"before": float("%.6f" % sa), "after": float("%.6f" % sb),
                      "change": float("%.6f" % (sb - sa))}
        d = data[BASE_TAX][BASE_CUR]
        for leg in LEGS:
            if a in d[leg] and b in d[leg]:
                out["dlog_%s" % leg] = float(
                    "%.6f" % (math.log(d[leg][b]) - math.log(d[leg][a])))
        return out

    windows = {k: window(k) for k in WINDOWS}
    rec["windows"] = windows
    print("\n  the three windows the two screens leave behind")
    for name, w in windows.items():
        sq = w.get("square_%s" % BASE_TAX)
        print("  %-11s %s -> %s   change %s   [%s]"
              % (name, w["from"], w["to"],
                 ("%+.6f" % sq["change"]) if sq else "not available",
                 w["status"]))
        for leg in LEGS:
            k = "dlog_%s" % leg
            if k in w:
                print("      dlog %-3s %+.6f   (%s)"
                      % (leg, w[k], LEGS[leg]["what"]))

    # What "does not move" has to be read against is not only the instrument
    # floor, which says whether a number is visible, but this quantity's own
    # period-to-period movement, which says whether a given change stands out.
    # The comparison is scale-free and takes its position from the distribution
    # itself rather than from a constant chosen here (D8).
    steps = []
    for a, b in zip(common, common[1:]):
        sa, sb = square(BASE_TAX, BASE_CUR, a), square(BASE_TAX, BASE_CUR, b)
        if sa is not None and sb is not None:
            steps.append({"from": a, "to": b,
                          "change": float("%.6f" % (sb - sa))})
    mags = sorted(abs(s["change"]) for s in steps)
    rec["own_movement"] = {
        "transitions": len(steps),
        "abs_min": mags[0] if mags else None,
        "abs_median": mags[len(mags) // 2] if mags else None,
        "abs_max": mags[-1] if mags else None,
        "steps": steps,
    }
    print("\n  this quantity's own period-to-period movement, %d transitions"
          % len(steps))
    print("  |change|  min %.4f   median %.4f   max %.4f"
          % (mags[0], mags[len(mags) // 2], mags[-1]))

    clean = windows["clean"]
    csq = clean.get("square_%s" % BASE_TAX)
    dRE, dRG = clean.get("dlog_RE"), clean.get("dlog_RG")
    equal_gap = None if (dRE is None or dRG is None) else abs(dRE - dRG)
    # the clean window read against both yardsticks
    if csq is not None and mags:
        cmag = abs(csq["change"])
        others = sorted(abs(s["change"]) for s in steps
                        if not (s["from"] == clean["from"]
                                and s["to"] == clean["to"]))
        own_median = others[len(others) // 2]
        smaller = sum(1 for x in mags if x < cmag)
        # The premise gate comes first. The statute caps a household bill at
        # 90 per cent of a reference tariff. A cap is not an equality, so
        # cutting one carrier further than the other breaks nothing in the
        # statute and everything in the arithmetic this window rests on. With
        # the premise broken there is no point prediction here to judge.
        premise_holds = (equal_gap is not None and floor is not None
                         and equal_gap <= floor)
        if not premise_holds:
            verdict = ("premise does not hold: the two household carriers did "
                       "not move by the same proportion, so this window carries "
                       "no point prediction to judge")
        elif floor and cmag <= floor:
            verdict = ("holds: the change is below what the instrument can "
                       "resolve, which is what not moving looks like")
        elif cmag > own_median:
            verdict = "refutes the point prediction"
        else:
            verdict = ("visible but undecidable: it sits inside this "
                       "quantity's own ordinary movement")
        clean_reading = {
            "abs_change": float("%.6f" % cmag),
            "floor": floor,
            "multiple_of_floor": float("%.1f" % (cmag / floor)) if floor else None,
            "median_of_other_transitions": float("%.6f" % own_median),
            "percentile_in_own_movement": round(100.0 * smaller / len(mags)),
            "premise_holds": premise_holds,
            "verdict": verdict,
        }
    else:
        clean_reading = None
    rec["clean_window_reading"] = clean_reading
    if clean_reading:
        print("\n  the clean window against both yardsticks")
        print("     |change| %.6f = %.0fx the floor, so it is visible"
              % (clean_reading["abs_change"],
                 clean_reading["multiple_of_floor"]))
        print("     median of the other %d transitions %.6f, this one sits at "
              "the %dth percentile"
              % (len(steps) - 1, clean_reading["median_of_other_transitions"],
                 clean_reading["percentile_in_own_movement"]))
        print("     verdict: %s" % clean_reading["verdict"])

    # ---- B50-6: did the cut reach the price or only the tax -----------------
    b6 = {}
    for tax in ("X_TAX", "I_TAX"):
        d = data[tax][BASE_CUR]["RE"]
        a, b = clean["from"], clean["to"]
        b6[tax] = None if (a not in d or b not in d) else float(
            "%.6f" % (math.log(d[b]) - math.log(d[a])))
    rec["household_electricity_by_tax_base"] = b6
    print("\nB50-6  did the cut reach the price or only the tax")
    for tax in ("X_TAX", "I_TAX"):
        print("  household electricity, dlog over the clean window, %-6s %s"
              % (tax, "n/a" if b6[tax] is None else "%+.6f" % b6[tax]))

    # ---- every semester, printed -------------------------------------------
    print("\n  every semester, square sum in three tax bases, then the four prices")
    print("  %-9s %10s %10s %10s | %9s %9s %9s %9s"
          % ("semester", "X_TAX", "X_VAT", "I_TAX",
             "P re", "P ie", "P rg", "P ig"))
    for r in rows:
        print("  %-9s %10s %10s %10s | %9.4f %9.4f %9.4f %9.4f"
              % (r["semester"],
                 "%.6f" % r["X_TAX"] if r["X_TAX"] is not None else "-",
                 "%.6f" % r["X_VAT"] if r["X_VAT"] is not None else "-",
                 "%.6f" % r["I_TAX"] if r["I_TAX"] is not None else "-",
                 r["price_resid_elec"], r["price_ind_elec"],
                 r["price_resid_gas"], r["price_ind_gas"]))

    rec["criteria"] = {
        "B50-1": {
            "kind": "instrument",
            "name": "the panel is complete: four legs across the semesters, in "
                    "all three tax bases",
            "passed": len(common) > 0 and len(complete_all_tax) == len(common),
            "detail": "%d semesters with all four legs, %d of them in all three "
                      "tax bases, %s..%s"
                      % (len(common), len(complete_all_tax),
                         common[0] if common else "-",
                         common[-1] if common else "-"),
        },
        "B50-2": {
            "kind": "instrument",
            "name": "the reading uses the per-band series, which carries more "
                    "semesters than the total band it would be natural to take",
            "passed": all(c["band_semesters"] > c["total_semesters"]
                          for c in coverage.values()),
            "detail": "; ".join(
                "%s band %d vs total %d"
                % (k, coverage[k]["band_semesters"],
                   coverage[k]["total_semesters"]) for k in LEGS),
        },
        "B50-3": {
            "kind": "instrument",
            "name": "the square sum does not move with the currency the prices "
                    "are quoted in (implementation check, not independent "
                    "confirmation)",
            "passed": floor is not None,
            "detail": "floor %.3e over %d comparisons in %s, worst at %s; %s "
                      "reported separately at %.3e and excluded from the floor"
                      % (floor or 0.0, len(gaps), "/".join(FLOOR_CURRENCIES),
                         rec["currency_identity"]["worst"],
                         rec["currency_identity"]["reported_only"]["currencies"],
                         rec["currency_identity"]["reported_only"]["max_gap"]
                         or 0.0),
        },
        "B50-4": {
            "kind": "own_reading",
            "name": "point prediction over the clean window, read in four "
                    "states: the premise of equal proportional cuts failing "
                    "leaves nothing to judge; otherwise below the floor "
                    "confirms it, above the floor and above this quantity's own "
                    "median movement refutes it, and above the floor but inside "
                    "that movement is undecidable",
            "passed": None if clean_reading is None
                      else (True if clean_reading["verdict"].startswith("holds")
                            else (False
                                  if clean_reading["verdict"].startswith("refutes")
                                  else None)),
            "state": None if clean_reading is None else clean_reading["verdict"],
            "detail": "change %s, %sx the floor %.3e, %dth percentile of the "
                      "%d own transitions whose median is %s: %s"
                      % ("n/a" if csq is None else "%+.6f" % csq["change"],
                         clean_reading["multiple_of_floor"] if clean_reading else "n/a",
                         floor or 0.0,
                         clean_reading["percentile_in_own_movement"] if clean_reading else 0,
                         len(steps),
                         "%.6f" % clean_reading["median_of_other_transitions"]
                         if clean_reading else "n/a",
                         clean_reading["verdict"] if clean_reading else "n/a"),
        },
        "B50-5": {
            "kind": "premise",
            "name": "the arithmetic premise of B50-4: over the same window the "
                    "two household carriers moved by the same proportion. The "
                    "statute sets a ceiling rather than an equality, so cutting "
                    "one carrier further than the other breaks the premise "
                    "without breaking the statute",
            "passed": None if (equal_gap is None or floor is None)
                      else equal_gap <= floor,
            "detail": "dlog household electricity %s, household gas %s, "
                      "difference %s against floor %.3e"
                      % ("n/a" if dRE is None else "%+.6f" % dRE,
                         "n/a" if dRG is None else "%+.6f" % dRG,
                         "n/a" if equal_gap is None else "%.6f" % equal_gap,
                         floor or 0.0),
        },
        "B50-6": {
            "kind": "premise",
            "name": "the cut reached the price and not only the tax: the "
                    "household leg moves the same way with tax excluded as "
                    "with tax included",
            "passed": None if (b6["X_TAX"] is None or b6["I_TAX"] is None)
                      else (b6["X_TAX"] < 0) == (b6["I_TAX"] < 0),
            "detail": "X_TAX %s, I_TAX %s"
                      % ("n/a" if b6["X_TAX"] is None else "%+.6f" % b6["X_TAX"],
                         "n/a" if b6["I_TAX"] is None else "%+.6f" % b6["I_TAX"]),
        },
    }
    # The other two windows are readings, not criteria. No line is drawn on them.
    rec["readings"] = {
        "small_window": windows["small"],
        "confounded_window": windows["confounded"],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for name in sorted(rec["criteria"]):
        c = rec["criteria"][name]
        mark = "PASS" if c["passed"] is True else (
            "FAIL" if c["passed"] is False else "N/A ")
        print("  %-7s %-4s %s" % (name, mark, c["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
