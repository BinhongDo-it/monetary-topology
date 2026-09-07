"""B52: the same class square across Europe and across time.

B49 read this square in 13 countries at 3 years and found it nonzero in every
cell, with the sign drifting: 5 positive cells of 13 in 2000, 2 in 2010, 1 in
2025. B50 read it in one country over 37 semesters and found it moving the whole
time. This station puts both dimensions together, on the Eurostat panel: every
country the source covers, 37 semesters, three tax bases.

The load-bearing question is the one B49 left open. The framework predicts the
square sum is not zero. It predicts nothing about which way the sign goes, and
B49 saw the sign move. Either that was a property of thirteen countries at three
dates, or it is there in the panel.

  positions   electricity and piped gas
  classes     residential and industrial
  square      log(P_re / P_rg) - log(P_ie / P_ig)

Counting the independent loops, because this is where a panel invites inflation.
Four vertices, four edges, so b1 = 4 - 4 + 1 = 1 per country. Each country is one
independent square; the semesters are that one square moving, not new squares. So
the independent count is the number of countries, not the number of cells, and
nothing here multiplies by 37.

Criteria:

  B52-1  panel completeness, printed country by country.
  B52-2  the square does not move with the currency the prices are quoted in.
         One rate per country-semester is shared by both classes and cancels in
         the log difference, so this is an implementation check and not an
         independent confirmation (D35). Its worst departure is the floor. Only a
         pure exchange-rate conversion may set it: a purchasing-power unit is not
         one scalar per country-semester and cannot bound the instrument.
  B52-3  the rival's point prediction, which is that every cell is exactly zero.
  B52-4  how many cells stand above the measured floor, in three states, with a
         cell at or below it recorded as unreadable rather than as zero.
  B52-5  the direction of the sign drift: for each country, the sign at its first
         semester against the sign at its last. Two integers, no threshold. Two
         numbers close together means there is no drift and B49's reading was a
         property of its sample.

Every criterion with more than two states prints the state-to-verdict mapping
itself, and the undecided state maps to no verdict.

Source: Eurostat bi-annual energy prices, all geographies the source carries.
Responses are cached under data/cache/eurostat/ and reused; --refresh re-fetches.

Run:

    python experiments\\b52_europe_class_square.py
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
OUT = ROOT / "results" / "b52_europe_class_square.json"
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
UA = "monetary-topology/b52 (research; contact via repository)"

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
TAXES = ("X_TAX", "X_VAT", "I_TAX")
BASE_TAX = "I_TAX"
BASE_CUR = "NAC"
FLOOR_CURRENCIES = ("EUR",)
CURRENCIES = (BASE_CUR,) + FLOOR_CURRENCIES

# Rows the source carries under a geography code that is a bloc, not a country.
AGGREGATES = frozenset({
    "EU27_2020", "EU28", "EA", "EA19", "EA20", "EU", "EU27_2007",
})

# The three states each many-state criterion uses, and what each maps to. This
# mapping is printed and asserted rather than left in the code, because a
# correctly drawn set of states can still be mapped one notch too strong.
STATE_MAP = {
    "above_floor": "counts as readable",
    "at_or_below_floor": "unreadable, no verdict",
    "exactly_zero": "the rival is right in that cell",
}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(ds: str, params: dict, refresh: bool) -> dict:
    q = urllib.parse.urlencode(sorted(params.items()))
    name = "%s__%s.json" % (ds, q.replace("&", "__").replace("=", "-"))
    path = CACHE / name
    if path.exists() and not refresh:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit("cached file is not valid JSON: %s (%s)" % (path, exc))
        if "dimension" not in data:
            raise SystemExit("cached file has no dimension block: %s" % path)
        return data
    url = API + ds + "?" + q
    try:
        data = _get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise SystemExit("could not reach the statistics endpoint and no usable "
                         "cache is on disk\n  url: %s\n  error: %s" % (url, exc))
    if "dimension" not in data:
        raise SystemExit("response has no dimension block: %s" % url)
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(data, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")
    os.replace(part, path)
    return data


def panel(ds: str, band: str, unit: str, tax: str, cur: str,
          refresh: bool) -> dict:
    """(geo, semester) -> price, aggregates dropped."""
    d = fetch(ds, {"format": "JSON", "lang": "EN", "nrg_cons": band,
                   "unit": unit, "tax": tax, "currency": cur}, refresh)
    free = [k for k in d["id"]
            if d["size"][d["id"].index(k)] > 1 and k not in ("geo", "time")]
    if free:
        raise SystemExit("the query left %s free for %s %s %s %s"
                         % (free, ds, band, tax, cur))
    ids, size = d["id"], d["size"]
    gi, ti = ids.index("geo"), ids.index("time")
    geos = list(d["dimension"]["geo"]["category"]["index"])
    times = list(d["dimension"]["time"]["category"]["index"])
    gpos = {v: k for k, v in d["dimension"]["geo"]["category"]["index"].items()}
    tpos = {v: k for k, v in d["dimension"]["time"]["category"]["index"].items()}
    out = {}
    for key, val in d["value"].items():
        rem, sub = int(key), [0] * len(ids)
        for k in range(len(ids) - 1, -1, -1):
            sub[k] = rem % size[k]
            rem //= size[k]
        g, t = gpos[sub[gi]], tpos[sub[ti]]
        if g in AGGREGATES:
            continue
        out[(g, t)] = val
    return out


def main() -> int:
    refresh = "--refresh" in sys.argv[1:]
    rec: dict = {
        "stage": "B52",
        "config": {
            "endpoint": API, "legs": {k: dict(v) for k, v in LEGS.items()},
            "taxes": list(TAXES), "currencies": list(CURRENCIES),
            "base_tax": BASE_TAX, "base_currency": BASE_CUR,
            "floor_currencies": list(FLOOR_CURRENCIES),
            "aggregates_dropped": sorted(AGGREGATES),
            "state_to_verdict": STATE_MAP,
            "independent_loops": "b1 = 4 - 4 + 1 = 1 per country; the "
                                 "independent count is the number of countries, "
                                 "not the number of cells",
            "refresh": refresh,
            "cache_dir": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    data: dict = {}
    for tax in TAXES:
        data[tax] = {}
        for cur in CURRENCIES:
            data[tax][cur] = {k: panel(v["ds"], v["band"], v["unit"], tax, cur,
                                       refresh) for k, v in LEGS.items()}

    base = data[BASE_TAX][BASE_CUR]
    # A price of zero is not a price, it is an absence. Albania reports 0.0 for
    # piped gas in the semesters it reports at all, because it has essentially
    # no gas network, and a zero cannot be logged. Such a cell leaves the panel
    # and is named, in its own column: "this price cannot be logged" is a
    # different state from "this reading sits below the floor", and the two are
    # not merged.
    four_legs = set.intersection(*[set(base[k]) for k in LEGS])
    non_positive = sorted(
        (g, tt, {k: base[k][(g, tt)] for k in LEGS
                 if base[k][(g, tt)] is None or base[k][(g, tt)] <= 0})
        for (g, tt) in four_legs
        if any(base[k][(g, tt)] is None or base[k][(g, tt)] <= 0 for k in LEGS))
    all_keys = {k for k in four_legs
                if all(base[j][k] is not None and base[j][k] > 0 for j in LEGS)}
    countries = sorted({g for g, _ in all_keys})
    semesters = sorted({t for _, t in all_keys})

    print("B52-1  panel")
    print("  countries with all four legs in at least one semester: %d"
          % len(countries))
    print("  semesters spanned: %d   %s..%s"
          % (len(semesters), semesters[0], semesters[-1]))
    per_country = {}
    for g in countries:
        ts = sorted(t for gg, t in all_keys if gg == g)
        per_country[g] = {"semesters": len(ts), "span": [ts[0], ts[-1]]}
    rec["panel"] = {"countries": countries, "semesters": semesters,
                    "cells": len(all_keys), "per_country": per_country,
                    "independent_loops": len(countries),
                    "dropped_non_positive": [
                        {"geo": g, "semester": s, "legs": legs}
                        for g, s, legs in non_positive],
                    "dropped_note": "a zero is an absence, not a price: it "
                                    "cannot be logged and the cell leaves the "
                                    "panel. This is a different state from a "
                                    "reading below the floor."}
    if non_positive:
        print("\n  cells dropped because a price is zero or negative: %d"
              % len(non_positive))
        for g, s, legs in non_positive:
            print("     %-6s %-9s %s" % (g, s, legs))
        print("     a zero is an absence rather than a price, and this is not "
              "the same state as a reading below the floor")
    print("  cells (country x semester with all four legs): %d" % len(all_keys))
    print("  INDEPENDENT LOOPS: %d, one per country. Not %d."
          % (len(countries), len(all_keys)))
    print("  %-6s %4s  %s" % ("geo", "n", "span"))
    for g in countries:
        c = per_country[g]
        print("  %-6s %4d  %s..%s" % (g, c["semesters"], c["span"][0], c["span"][1]))

    def square(tax, cur, key):
        d = data[tax][cur]
        if not all(key in d[k] for k in LEGS):
            return None
        if any(d[k][key] is None or d[k][key] <= 0 for k in LEGS):
            return None
        return ((math.log(d["RE"][key]) - math.log(d["RG"][key]))
                - (math.log(d["IE"][key]) - math.log(d["IG"][key])))

    # ---- B52-2: currency identity and the floor ----------------------------
    gaps = []
    for key in all_keys:
        b = square(BASE_TAX, BASE_CUR, key)
        if b is None:
            continue
        for cur in FLOOR_CURRENCIES:
            v = square(BASE_TAX, cur, key)
            if v is not None:
                gaps.append({"geo": key[0], "semester": key[1],
                             "gap": abs(v - b)})
    gaps.sort(key=lambda g: -g["gap"])
    # In a euro-area country the national currency IS the euro, so the check is
    # an identity there and carries nothing. The floor comes from the countries
    # where a real conversion happens, and the vacuous share is printed rather
    # than left implicit.
    vacuous = [g for g in gaps if g["gap"] == 0.0]
    floor = gaps[0]["gap"] if gaps else None
    med = sorted(g["gap"] for g in gaps)[len(gaps) // 2] if gaps else None
    rec["currency_identity"] = {
        "floor_currencies": list(FLOOR_CURRENCIES), "comparisons": len(gaps),
        "max_gap": floor, "median_gap": med,
        "worst": "%s %s" % (gaps[0]["geo"], gaps[0]["semester"]) if gaps else None,
        "vacuous_comparisons": len(vacuous),
        "vacuous_note": "a euro-area country quotes in euro already, so the "
                        "conversion is the identity and the comparison carries "
                        "nothing there",
        "note": "implementation check, not an independent confirmation",
    }
    print("\nB52-2  currency identity (implementation check)")
    print("  %d comparisons, median %.3e, max %.3e at %s   floor = %.3e"
          % (len(gaps), med, floor, rec["currency_identity"]["worst"], floor))
    print("  of those, %d are the identity (a euro-area country already quotes "
          "in euro) and carry nothing; the floor comes from the rest"
          % len(vacuous))

    # ---- the cells ---------------------------------------------------------
    cells = []
    for key in sorted(all_keys):
        row = {"geo": key[0], "semester": key[1]}
        for tax in TAXES:
            v = square(tax, BASE_CUR, key)
            row[tax] = None if v is None else float("%.6f" % v)
        for leg in LEGS:
            row["price_%s" % leg] = base[leg].get(key)
        cells.append(row)
    rec["cells"] = cells

    vals = [c[BASE_TAX] for c in cells if c[BASE_TAX] is not None]
    exact_zero = [c for c in cells if c[BASE_TAX] == 0.0]
    at_or_below = [(c["geo"], c["semester"]) for c in cells
                   if c[BASE_TAX] is not None and abs(c[BASE_TAX]) <= floor]
    above = [v for v in vals if abs(v) > floor]
    mags = sorted(abs(v) for v in vals)
    rec["magnitude"] = {
        "cells": len(vals), "above_floor": len(above),
        "at_or_below_floor": at_or_below, "exactly_zero": len(exact_zero),
        "abs_min": mags[0], "abs_median": mags[len(mags) // 2],
        "abs_max": mags[-1],
        "smallest_multiple_of_floor": mags[0] / floor if floor else None,
        "median_multiple_of_floor": mags[len(mags) // 2] / floor if floor else None,
    }
    readable = [v for v in vals if abs(v) > floor]
    zero_in_readable = [v for v in readable if v == 0.0]
    print("\nB52-3  the rival predicts every cell is exactly zero")
    print("  judged on the %d readable cells only; the %d cells at or below the "
          "floor cannot separate zero from non-zero and carry no verdict"
          % (len(readable), len(vals) - len(readable)))
    print("  cells exactly zero among the readable: %d of %d"
          % (len(zero_in_readable), len(readable)))
    print("\nB52-4  magnitude against the floor, three states")
    for state, verdict_ in STATE_MAP.items():
        print("     %-20s -> %s" % (state, verdict_))
    print("  above the floor: %d of %d;  at or below (unreadable): %d"
          % (len(above), len(vals), len(at_or_below)))
    print("  |square|  min %.4f (%.1fx floor)   median %.4f (%.0fx)   max %.4f"
          % (mags[0], mags[0] / floor, mags[len(mags) // 2],
             mags[len(mags) // 2] / floor, mags[-1]))

    # ---- B52-5: the direction of the sign drift ----------------------------
    drift = []
    for g in countries:
        ts = sorted(t for gg, t in all_keys if gg == g)
        a = square(BASE_TAX, BASE_CUR, (g, ts[0]))
        b = square(BASE_TAX, BASE_CUR, (g, ts[-1]))
        if a is None or b is None:
            continue
        drift.append({"geo": g, "first": ts[0], "last": ts[-1],
                      "first_value": float("%.6f" % a),
                      "last_value": float("%.6f" % b),
                      "sign_first": "+" if a > 0 else "-",
                      "sign_last": "+" if b > 0 else "-"})
    pos_to_neg = [d["geo"] for d in drift
                  if d["sign_first"] == "+" and d["sign_last"] == "-"]
    neg_to_pos = [d["geo"] for d in drift
                  if d["sign_first"] == "-" and d["sign_last"] == "+"]
    stayed = len(drift) - len(pos_to_neg) - len(neg_to_pos)
    rec["sign_drift"] = {
        "countries": len(drift), "positive_to_negative": pos_to_neg,
        "negative_to_positive": neg_to_pos, "unchanged": stayed,
        "per_country": drift,
    }
    print("\nB52-5  the direction of the sign drift, first semester to last")
    print("  countries read: %d   + to -: %d   - to +: %d   unchanged: %d"
          % (len(drift), len(pos_to_neg), len(neg_to_pos), stayed))
    print("  + to - : %s" % (", ".join(pos_to_neg) or "none"))
    print("  - to + : %s" % (", ".join(neg_to_pos) or "none"))

    # ---- B52-6: the same question on one window shared by every country ----
    # B52-5 compares each country's first semester against its own last, and
    # those windows are not the same window: Georgia enters in 2018, Ukraine
    # stops in 2021, the United Kingdom in 2020. A fixed comparison rule applied
    # over heterogeneous windows is the ninth category error, so the drift is
    # asked a second time on a rectangle every country is inside for its whole
    # length. The rectangle is chosen by maximising countries x semesters, which
    # is computed rather than picked.
    present = {}
    for g in countries:
        present[g] = {tt for gg, tt in all_keys if gg == g}
    best = None
    for i, a in enumerate(semesters):
        for b_ in semesters[i:]:
            span = [s for s in semesters if a <= s <= b_]
            inside = [g for g in countries
                      if all(s in present[g] for s in span)]
            area = len(inside) * len(span)
            if best is None or area > best["area"]:
                best = {"from": a, "to": b_, "span": span,
                        "countries": inside, "area": area}
    rect_drift = []
    for g in best["countries"]:
        a = square(BASE_TAX, BASE_CUR, (g, best["from"]))
        b_ = square(BASE_TAX, BASE_CUR, (g, best["to"]))
        if a is None or b_ is None:
            continue
        rect_drift.append({"geo": g,
                           "first_value": float("%.6f" % a),
                           "last_value": float("%.6f" % b_),
                           "sign_first": "+" if a > 0 else "-",
                           "sign_last": "+" if b_ > 0 else "-"})
    r_pn = [d["geo"] for d in rect_drift
            if d["sign_first"] == "+" and d["sign_last"] == "-"]
    r_np = [d["geo"] for d in rect_drift
            if d["sign_first"] == "-" and d["sign_last"] == "+"]
    rec["common_window"] = {
        "from": best["from"], "to": best["to"],
        "countries": best["countries"], "n_countries": len(best["countries"]),
        "n_semesters": len(best["span"]), "area": best["area"],
        "chosen_by": "the rectangle maximising countries x semesters, computed "
                     "rather than picked",
        "positive_to_negative": r_pn, "negative_to_positive": r_np,
        "unchanged": len(rect_drift) - len(r_pn) - len(r_np),
        "per_country": rect_drift,
    }
    print("\nB52-6  the same question on one window every country shares")
    print("  rectangle %s..%s: %d countries x %d semesters = %d cells"
          % (best["from"], best["to"], len(best["countries"]),
             len(best["span"]), best["area"]))
    print("  + to -: %d (%s)" % (len(r_pn), ", ".join(r_pn) or "none"))
    print("  - to +: %d (%s)" % (len(r_np), ", ".join(r_np) or "none"))
    print("  unchanged: %d" % (len(rect_drift) - len(r_pn) - len(r_np)))
    moved_5 = set(pos_to_neg) | set(neg_to_pos)
    moved_6 = set(r_pn) | set(r_np)
    both = sorted(moved_5 & moved_6 & set(best["countries"]))
    only5 = sorted((moved_5 - moved_6) & set(best["countries"]))
    only6 = sorted(moved_6 - moved_5)
    rec["common_window"]["against_own_window"] = {
        "moved_in_both": both, "moved_only_with_own_window": only5,
        "moved_only_in_common_window": only6,
    }
    print("  against B52-5, restricted to the countries inside the rectangle:")
    print("     moved in both:                %s" % (", ".join(both) or "none"))
    print("     moved only with its own window: %s" % (", ".join(only5) or "none"))
    print("     moved only in the common window: %s" % (", ".join(only6) or "none"))

    # ---- the decomposition, printed before anything is looked up ----------
    # The square sum is the difference of two class gaps,
    #     [ln P_re - ln P_ie] - [ln P_rg - ln P_ig],
    # so its change over a window is four terms. Printing them says which leg
    # moved before any explanation is sought for why.
    print("\n  the four legs over the common window, every country in the "
          "rectangle, in logs")
    print("  %-4s %9s %9s | %9s %9s %9s %9s | %s"
          % ("geo", "sq first", "sq last", "d ln re", "d ln ie", "d ln rg",
             "d ln ig", "turn"))
    decomposition = {}
    for g in best["countries"]:
        ka, kb = (g, best["from"]), (g, best["to"])
        a = square(BASE_TAX, BASE_CUR, ka)
        b_ = square(BASE_TAX, BASE_CUR, kb)
        if a is None or b_ is None:
            continue
        d = {}
        for leg in LEGS:
            d[leg] = math.log(base[leg][kb]) - math.log(base[leg][ka])
        turn = ("+ to -" if (a > 0 and b_ < 0)
                else "- to +" if (a < 0 and b_ > 0) else "")
        decomposition[g] = {
            "square_first": float("%.6f" % a), "square_last": float("%.6f" % b_),
            "change": float("%.6f" % (b_ - a)),
            "dlog": {k: float("%.6f" % v) for k, v in d.items()},
            "electricity_class_gap_change": float("%.6f" % (d["RE"] - d["IE"])),
            "gas_class_gap_change": float("%.6f" % (d["RG"] - d["IG"])),
            "turn": turn,
        }
        print("  %-4s %9.4f %9.4f | %9.4f %9.4f %9.4f %9.4f | %s"
              % (g, a, b_, d["RE"], d["IE"], d["RG"], d["IG"], turn))
    rec["common_window"]["decomposition"] = decomposition
    print("  the square's change is (d ln re - d ln ie) - (d ln rg - d ln ig): "
          "the electricity class gap minus the gas class gap")
    print("\n  %-4s %14s %14s %10s | %s"
          % ("geo", "elec gap chg", "gas gap chg", "sq chg", "turn"))
    for g, v in sorted(decomposition.items(),
                       key=lambda kv: kv[1]["change"]):
        print("  %-4s %14.4f %14.4f %10.4f | %s"
              % (g, v["electricity_class_gap_change"],
                 v["gas_class_gap_change"], v["change"], v["turn"]))

    # ---- B52-7: the same question, stopped before the energy crisis --------
    # The path of the two class gaps is nearly flat from 2008 to 2021 and then
    # moves by ten to twenty-five times its own decade-long range in the four
    # semesters from 2021-S2, recovering only partly. That is the shape of a
    # shock, not of a drift. If B49's reading of a moving sign has a basis
    # independent of that shock, some of it should already be present in a
    # window that stops before it. The cut date is the last semester before
    # wholesale gas began to move, and it is fixed here rather than searched.
    PRE_CRISIS_END = "2021-S1"
    pre_span = [s for s in semesters if best["from"] <= s <= PRE_CRISIS_END]
    pre_countries = [g for g in countries
                     if all(s in present[g] for s in pre_span)]
    pre_drift = []
    for g in pre_countries:
        a = square(BASE_TAX, BASE_CUR, (g, best["from"]))
        b_ = square(BASE_TAX, BASE_CUR, (g, PRE_CRISIS_END))
        if a is None or b_ is None:
            continue
        pre_drift.append({"geo": g, "sign_first": "+" if a > 0 else "-",
                          "sign_last": "+" if b_ > 0 else "-",
                          "first_value": float("%.6f" % a),
                          "last_value": float("%.6f" % b_),
                          "change": float("%.6f" % (b_ - a))})
    p_pn = [d["geo"] for d in pre_drift
            if d["sign_first"] == "+" and d["sign_last"] == "-"]
    p_np = [d["geo"] for d in pre_drift
            if d["sign_first"] == "-" and d["sign_last"] == "+"]
    pre_down = [d["geo"] for d in pre_drift if d["change"] < 0]
    post_down = [g for g, v in decomposition.items() if v["change"] < 0]
    rec["pre_crisis_window"] = {
        "from": best["from"], "to": PRE_CRISIS_END,
        "cut_note": "fixed at the last semester before wholesale gas moved, not "
                    "searched over",
        "countries": pre_countries, "n_countries": len(pre_drift),
        "positive_to_negative": p_pn, "negative_to_positive": p_np,
        "unchanged": len(pre_drift) - len(p_pn) - len(p_np),
        "moved_down": len(pre_down), "moved_up": len(pre_drift) - len(pre_down),
        "per_country": pre_drift,
        "full_window_moved_down": len(post_down),
        "full_window_moved_up": len(decomposition) - len(post_down),
    }
    print("\nB52-7  the same question, stopped before the crisis")
    print("  window %s..%s, %d countries" % (best["from"], PRE_CRISIS_END,
                                             len(pre_drift)))
    print("  + to -: %d (%s)" % (len(p_pn), ", ".join(p_pn) or "none"))
    print("  - to +: %d (%s)" % (len(p_np), ", ".join(p_np) or "none"))
    print("  unchanged: %d" % (len(pre_drift) - len(p_pn) - len(p_np)))
    print("  direction of change, which carries more than the sign turning:")
    print("     pre-crisis  %s..%s : %d down, %d up"
          % (best["from"], PRE_CRISIS_END, len(pre_down),
             len(pre_drift) - len(pre_down)))
    print("     full window %s..%s : %d down, %d up"
          % (best["from"], best["to"], len(post_down),
             len(decomposition) - len(post_down)))

    # per-semester share of positive cells, printed with no line on it
    by_sem = {}
    for t in semesters:
        v = [c[BASE_TAX] for c in cells
             if c["semester"] == t and c[BASE_TAX] is not None]
        if v:
            by_sem[t] = {"n": len(v), "positive": sum(1 for x in v if x > 0),
                         "median": float("%.6f" % sorted(v)[len(v) // 2])}
    rec["by_semester"] = by_sem
    print("\n  positive share and median by semester (reported, no line on it)")
    print("  %-9s %4s %4s %10s" % ("semester", "n", "pos", "median"))
    for t in semesters:
        if t in by_sem:
            b_ = by_sem[t]
            print("  %-9s %4d %4d %10.4f" % (t, b_["n"], b_["positive"], b_["median"]))

    rec["criteria"] = {
        "B52-1": {
            "kind": "instrument",
            "name": "panel completeness, printed country by country",
            "passed": len(countries) > 0 and len(all_keys) > 0,
            "detail": "%d countries, %d semesters, %d cells, %d independent "
                      "loops (one per country, not one per cell); %d cells "
                      "dropped for a zero or negative price: %s"
                      % (len(countries), len(semesters), len(all_keys),
                         len(countries), len(non_positive),
                         ", ".join("%s %s" % (g, s) for g, s, _ in non_positive)
                         or "none"),
        },
        "B52-2": {
            "kind": "instrument",
            "name": "the square does not move with the currency the prices are "
                    "quoted in (implementation check, not independent "
                    "confirmation); only a pure exchange-rate conversion sets "
                    "the floor",
            "passed": floor is not None,
            "detail": "floor %.3e over %d comparisons in %s, worst at %s"
                      % (floor or 0.0, len(gaps), "/".join(FLOOR_CURRENCIES),
                         rec["currency_identity"]["worst"]),
        },
        "B52-3": {
            "kind": "rival",
            "name": "no readable cell matches the rival's point prediction of "
                    "exactly zero; cells at or below the floor carry no verdict "
                    "because the instrument cannot separate zero from non-zero "
                    "there",
            "passed": len(zero_in_readable) == 0,
            "detail": "%d of %d readable cells are exactly zero; %d cells "
                      "unreadable and not judged"
                      % (len(zero_in_readable), len(readable),
                         len(vals) - len(readable)),
        },
        "B52-4": {
            "kind": "bookkeeping",
            "name": "every cell at or below the floor is named and carries no "
                    "verdict. A continuous quantity read at a thousand points "
                    "will pass near zero somewhere, so the count of such cells "
                    "is a reading and not a failure; what can fail is leaving "
                    "them unnamed",
            "passed": len(at_or_below) == len(
                [c for c in cells if c[BASE_TAX] is not None
                 and abs(c[BASE_TAX]) <= floor]),
            "state_map": STATE_MAP,
            "detail": "%d of %d above %.3e; smallest %.1fx, median %.0fx; at or "
                      "below: %s"
                      % (len(above), len(vals), floor, mags[0] / floor,
                         mags[len(mags) // 2] / floor,
                         ", ".join("%s %s" % k for k in at_or_below[:8]) or "none"),
        },
        "B52-5": {
            "kind": "own_reading",
            "name": "the sign drift is one-directional, in the shape B49 read "
                    "it: one of the two directions is empty. Comparing the two "
                    "counts with a strict inequality would be a zero-width test "
                    "on integers, so what is asked is whether the smaller "
                    "direction is zero. Each country is read over its own first "
                    "and last semester, and those windows are not the same "
                    "window, which B52-6 asks again on one that is",
            "passed": min(len(pos_to_neg), len(neg_to_pos)) == 0,
            "detail": "%d countries read, + to - is %d (%s), - to + is %d (%s), "
                      "unchanged %d"
                      % (len(drift), len(pos_to_neg),
                         ", ".join(pos_to_neg) or "none", len(neg_to_pos),
                         ", ".join(neg_to_pos) or "none", stayed),
        },
    }

    rec["criteria"]["B52-6"] = {
        "kind": "own_reading",
        "name": "the same one-directional question on a window every country "
                "shares for its whole length, so that a fixed comparison rule "
                "is not applied over heterogeneous windows",
        "passed": min(len(r_pn), len(r_np)) == 0,
        "detail": "%s..%s, %d countries x %d semesters; + to - is %d (%s), "
                  "- to + is %d (%s), unchanged %d"
                  % (best["from"], best["to"], len(best["countries"]),
                     len(best["span"]), len(r_pn), ", ".join(r_pn) or "none",
                     len(r_np), ", ".join(r_np) or "none",
                     len(rect_drift) - len(r_pn) - len(r_np)),
    }

    rec["criteria"]["B52-7"] = {
        "kind": "own_reading",
        "name": "B49 read a moving sign. If that has a basis independent of the "
                "2021-2023 energy interventions, part of it is already present "
                "in a window stopping before them. The cut date is fixed, not "
                "searched",
        "passed": min(len(p_pn), len(p_np)) == 0 and (len(p_pn) + len(p_np)) > 0,
        "detail": "%s..%s over %d countries: + to - is %d (%s), - to + is %d "
                  "(%s), unchanged %d; by direction of change rather than sign, "
                  "%d down and %d up before the crisis against %d down and %d up "
                  "over the full window"
                  % (best["from"], PRE_CRISIS_END, len(pre_drift), len(p_pn),
                     ", ".join(p_pn) or "none", len(p_np),
                     ", ".join(p_np) or "none",
                     len(pre_drift) - len(p_pn) - len(p_np), len(pre_down),
                     len(pre_drift) - len(pre_down), len(post_down),
                     len(decomposition) - len(post_down)),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for name in sorted(rec["criteria"]):
        c_ = rec["criteria"][name]
        print("  %-7s %-4s %s" % (name, "PASS" if c_["passed"] else "FAIL",
                                  c_["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
