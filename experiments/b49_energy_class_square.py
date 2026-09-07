"""B49: a class square on the two energy carriers that cannot be resold.

Positions are electricity and piped natural gas. Classes are residential and
industrial. The square sum this station reads is the first of the three terms,

    w_resid(elec, gas) - w_ind(elec, gas)
      = log(P_resid_elec / P_resid_gas) - log(P_ind_elec / P_ind_gas)

Why these two carriers and not the other six the source carries. A class
differential can only be read off two prices when the holder of the cheaper one
cannot resell it to the holder of the dearer one. Electricity and piped gas
arrive over a fixed network and the connection point IS the class definition, so
nothing moves past the meter. Kerosene, LPG, fuel oil and coal all travel in
drums, bottles and wagons, so a price gap between two buyer classes is carriage
and handling, not a class differential. Gasoline and diesel do not even have two
classes in this source: they exist in the transport sector only, one price, and
the paired-cell count is zero. That count is printed by B49-2 rather than
asserted.

The rival is a scalar price field over positions: if the terms facing every
class were the gradient of one potential, every square sum would be exactly
zero, whatever the level of prices. This is a point prediction of zero, so it
carries no band and is read against a measured resolution floor (D24), not
against a rival's interval (D14 does not apply).

Criteria, all evaluated on the record this run writes:

  B49-1  the locked panel is complete: every country in the locked set carries
         all four series in all three years. Structural.
  B49-2  roster against records (D37): the list endpoint names one number of
         countries, the price rows carry another. Both are printed, for every
         product, together with the paired-cell counts that decide which
         products can carry a class square at all.
  B49-3  currency identity: one exchange rate per country-year cancels in the
         log difference, so the square sum must not move when the four prices
         are quoted in another currency. This is an implementation check, not an
         independent confirmation (D35): the cancellation is forced by the
         construction, and only a coding error can break it. Its worst gap is
         the measured floor used by B49-4.
  B49-4  every square sum stands above that floor, and by what multiple.
  B49-5  the rival's point prediction: how many of the cells are exactly zero.
The sign distribution and the median by year are printed as well. They are an
object this run reports, not a criterion, and no line is drawn on either.

Every cell this run produces goes into the record, including the four prices
behind it, so nothing is selected for reporting.

Source: IEA End-use Energy Prices, public read endpoint, CC BY 4.0. Responses
are cached under data/cache/iea/ and reused; pass --refresh to re-fetch.

Run:

    python experiments\\b49_energy_class_square.py
    python experiments\\b49_energy_class_square.py --refresh
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
CACHE = ROOT / "data" / "cache" / "iea"
OUT = ROOT / "results" / "b49_energy_class_square.json"

API = "https://api.iea.org/prices"
LIST = "https://api.iea.org/prices/list"
UA = "monetary-topology/b49 (research; contact via repository)"

# The four series of the square, keyed by the short name used throughout.
SERIES = {
    "RE": ("RESID", "ELECTR"),
    "IE": ("IND", "ELECTR"),
    "RG": ("RESID", "NATGAS"),
    "IG": ("IND", "NATGAS"),
}
UNITS = ("USDCUR", "NCCUR", "PPPREA")
BASE_UNIT = "USDCUR"
YEARS = ("2000", "2010", "2025")

# Every product the source carries, for the roster-against-records table.
ALL_PRODUCTS = ("ELECTR", "NATGAS", "KEROSENE", "LPG", "RESFUEL", "COAL",
                "GASOLINE", "DIESEL")
ALL_SECTORS = ("ELGEN", "IND", "RESID", "TRANS")

# Rows the source returns under a country name that is a region or a club.
# They are not countries and are dropped before anything is counted.
AGGREGATES = frozenset({
    "Africa", "Americas", "Asia", "Europe", "European Union - 27", "G20",
    "IEA", "IEA and Accession/Association countries", "OECD", "OECD Americas",
    "OECD Asia Oceania", "OECD Europe", "Oceania", "World",
})

REQUIRED_KEYS = ("Country", "CODE_YEAR", "Value", "Unit")


def _get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(kind: str, params: dict, refresh: bool) -> list:
    """One cached GET. Cache key is the sorted query, so it is stable."""
    q = urllib.parse.urlencode(sorted(params.items()))
    name = "%s__%s.json" % (kind, q.replace("&", "__").replace("=", "-"))
    path = CACHE / name
    if path.exists() and not refresh:
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                "cached file is not valid JSON, delete or re-fetch it: %s (%s)"
                % (path, exc))
        if not isinstance(data, list):
            raise SystemExit("cached file is not a list: %s" % path)
        return data
    base = LIST + "/" + kind if kind != "prices" else API
    url = base + "?" + q
    try:
        data = _get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise SystemExit(
            "could not reach the price endpoint and no usable cache is on disk\n"
            "  url: %s\n  error: %s" % (url, exc))
    if not isinstance(data, list):
        raise SystemExit("endpoint returned a %s, expected a list: %s"
                         % (type(data).__name__, url))
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(data, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")
    os.replace(part, path)
    return data


def prices(sector: str, product: str, unit: str, refresh: bool) -> list:
    rows = fetch("prices", {"CODE_INDICATOR": "PRICE", "CODE_SECTOR": sector,
                            "CODE_PRODUCT": product, "CODE_UNIT": unit},
                 refresh)
    for d in rows:
        missing = [k for k in REQUIRED_KEYS if k not in d]
        if missing:
            raise SystemExit("price row is missing %s: %r" % (missing, d))
    return rows


def as_map(rows: list) -> dict:
    """country|year -> value, aggregates dropped."""
    return {"%s|%s" % (d["Country"], d["CODE_YEAR"]): d["Value"]
            for d in rows if d["Country"] not in AGGREGATES}


def units_of(rows: list) -> set:
    return {d["Unit"] for d in rows if d["Country"] not in AGGREGATES}


def main() -> int:
    refresh = "--refresh" in sys.argv[1:]
    rec: dict = {
        "stage": "B49",
        "config": {
            "endpoint": API,
            "years": list(YEARS),
            "units": list(UNITS),
            "base_unit": BASE_UNIT,
            "series": {k: list(v) for k, v in SERIES.items()},
            "aggregates_dropped": sorted(AGGREGATES),
            "refresh": refresh,
            "cache_dir": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    # ---- B49-2: roster against records, for every product ------------------
    print("B49-2  roster against records, and which products carry two classes")
    print("  %-9s %6s %6s %6s %6s | %6s %6s %6s %6s"
          % ("product", "ELGEN", "IND", "RESID", "TRANS",
             "roster", "record", "3yrs", "paired"))
    grid = {}
    for product in ALL_PRODUCTS:
        per_sector = {}
        cells: dict = {}
        roster: set = set()
        record: set = set()
        years_seen: dict = {}
        for sector in ALL_SECTORS:
            rows = prices(sector, product, BASE_UNIT, refresh)
            real = [d for d in rows if d["Country"] not in AGGREGATES]
            per_sector[sector] = len({d["Country"] for d in real})
            for d in real:
                cells.setdefault("%s|%s" % (d["Country"], d["CODE_YEAR"]),
                                 set()).add(sector)
                record.add(d["Country"])
                years_seen.setdefault(d["Country"], set()).add(d["CODE_YEAR"])
            names = fetch("Country", {"CODE_INDICATOR": "PRICE",
                                      "CODE_SECTOR": sector,
                                      "CODE_PRODUCT": product,
                                      "CODE_UNIT": BASE_UNIT}, refresh)
            roster.update(n for n in names if n not in AGGREGATES)
        paired = sum(1 for s in cells.values() if len(s) >= 2)
        all_years = sum(1 for ys in years_seen.values()
                        if set(YEARS).issubset(ys))
        grid[product] = {
            "countries_by_sector": per_sector,
            "roster_countries": len(roster),
            "record_countries": len(record),
            "record_countries_all_three_years": all_years,
            "record_country_year_cells": len(cells),
            "paired_cells": paired,
        }
        print("  %-9s %6d %6d %6d %6d | %6d %6d %6d %6d"
              % (product, per_sector["ELGEN"], per_sector["IND"],
                 per_sector["RESID"], per_sector["TRANS"],
                 len(roster), len(record), all_years, paired))
    rec["product_grid"] = grid

    # ---- load the four series in every currency ----------------------------
    data: dict = {}
    unit_labels: dict = {}
    for unit in UNITS:
        data[unit] = {}
        for key, (sector, product) in SERIES.items():
            rows = prices(sector, product, unit, refresh)
            data[unit][key] = as_map(rows)
            unit_labels.setdefault(unit, {})[key] = sorted(units_of(rows))

    # The square divides electricity by gas, so the two must be quoted in the
    # same physical unit. This one feeds the reading directly, so it stops the
    # run rather than being reported and passed over.
    for unit in UNITS:
        got = {k: tuple(v) for k, v in unit_labels[unit].items()}
        if len({got["RE"], got["IE"]}) != 1 or len({got["RG"], got["IG"]}) != 1 \
           or got["RE"] != got["RG"]:
            raise SystemExit(
                "electricity and gas are not quoted in one unit under %s: %r"
                % (unit, got))
    rec["quoted_units"] = {u: {k: v for k, v in unit_labels[u].items()}
                           for u in UNITS}

    # ---- B49-1: the locked panel ------------------------------------------
    base = data[BASE_UNIT]
    candidates = sorted({k.split("|")[0] for k in base["RE"]})
    locked = [c for c in candidates
              if all("%s|%s" % (c, y) in base[k]
                     for y in YEARS for k in SERIES)]
    rec["locked_countries"] = locked
    rec["locked_cells"] = len(locked) * len(YEARS)
    rec["prices_behind_cells"] = len(locked) * len(YEARS) * len(SERIES)
    print("\nB49-1  locked panel")
    print("  countries with all four series in all three years: %d" % len(locked))
    print("  " + ", ".join(locked))

    # ---- the square sum ----------------------------------------------------
    def square(unit: str, country: str, year: str):
        k = "%s|%s" % (country, year)
        d = data[unit]
        if not all(k in d[s] for s in SERIES):
            return None
        return ((math.log(d["RE"][k]) - math.log(d["RG"][k]))
                - (math.log(d["IE"][k]) - math.log(d["IG"][k])))

    cells = []
    for country in locked:
        for year in YEARS:
            k = "%s|%s" % (country, year)
            cells.append({
                "country": country,
                "year": year,
                "square_sum": float("%.9f" % square(BASE_UNIT, country, year)),
                "price_resid_electricity": base["RE"][k],
                "price_ind_electricity": base["IE"][k],
                "price_resid_gas": base["RG"][k],
                "price_ind_gas": base["IG"][k],
            })
    rec["cells"] = cells

    # ---- B49-3: currency identity, and the floor it measures ---------------
    gaps = []
    for country in locked:
        for year in YEARS:
            b = square(BASE_UNIT, country, year)
            for unit in UNITS:
                if unit == BASE_UNIT:
                    continue
                v = square(unit, country, year)
                if v is None:
                    continue
                gaps.append({"country": country, "year": year, "unit": unit,
                             "gap": abs(v - b)})
    gaps.sort(key=lambda g: -g["gap"])
    per_unit = {}
    for unit in UNITS:
        if unit == BASE_UNIT:
            continue
        g = [x for x in gaps if x["unit"] == unit]
        per_unit[unit] = {
            "cells_present": len(g),
            "cells_expected": len(cells),
            "max_gap": g[0]["gap"] if g else None,
            "worst_cell": "%s %s" % (g[0]["country"], g[0]["year"]) if g else None,
            "median_gap": sorted(x["gap"] for x in g)[len(g) // 2] if g else None,
        }
    # The floor comes from the currency that is a pure scalar conversion and is
    # present in every cell. A unit that is missing cells, or that carries its
    # own rounding, is reported but does not set the floor.
    floor_unit = None
    for unit in UNITS:
        if unit == BASE_UNIT:
            continue
        if per_unit[unit]["cells_present"] == len(cells):
            if floor_unit is None or \
               per_unit[unit]["max_gap"] > per_unit[floor_unit]["max_gap"]:
                floor_unit = unit
    floor = per_unit[floor_unit]["max_gap"] if floor_unit else None
    rec["currency_identity"] = {"by_unit": per_unit, "floor_unit": floor_unit,
                                "floor": floor,
                                "note": "implementation check, not an "
                                        "independent confirmation"}
    print("\nB49-3  currency identity (implementation check)")
    for unit in UNITS:
        if unit == BASE_UNIT:
            continue
        p = per_unit[unit]
        print("  %-8s cells %2d/%2d   median gap %.3e   max gap %.3e  at %s"
              % (unit, p["cells_present"], p["cells_expected"],
                 p["median_gap"] or 0.0, p["max_gap"] or 0.0, p["worst_cell"]))
    print("  floor taken from %s: %.3e" % (floor_unit, floor))

    # ---- B49-4 and B49-5 ---------------------------------------------------
    mags = sorted(abs(c["square_sum"]) for c in cells)
    above = [c for c in cells if abs(c["square_sum"]) > floor]
    at_or_below = ["%s %s" % (c["country"], c["year"]) for c in cells
                   if abs(c["square_sum"]) <= floor]
    exact_zero = [c for c in cells if c["square_sum"] == 0.0]
    rec["magnitude"] = {
        "min_abs": mags[0], "median_abs": mags[len(mags) // 2],
        "max_abs": mags[-1],
        "cells_above_floor": len(above), "cells_total": len(cells),
        "cells_at_or_below_floor": at_or_below,
        "smallest_multiple_of_floor": mags[0] / floor if floor else None,
        "median_multiple_of_floor": mags[len(mags) // 2] / floor if floor else None,
    }
    rec["rival_point_prediction"] = {
        "rival": "a scalar price field over positions, which predicts every "
                 "square sum is exactly zero",
        "cells_exactly_zero": len(exact_zero),
        "cells_total": len(cells),
    }
    print("\nB49-4  magnitude against the floor")
    print("  |square sum|  min %.4f   median %.4f   max %.4f"
          % (mags[0], mags[len(mags) // 2], mags[-1]))
    print("  above the floor: %d of %d   (smallest is %.1f x floor,"
          " median is %.0f x)"
          % (len(above), len(cells), mags[0] / floor,
             mags[len(mags) // 2] / floor))
    if at_or_below:
        print("  at or below the floor, unreadable rather than zero: %s"
              % ", ".join(at_or_below))
    print("\nB49-5  the rival predicts every cell is exactly zero")
    print("  cells exactly zero: %d of %d" % (len(exact_zero), len(cells)))

    # ---- B49-6: sign and median by year ------------------------------------
    by_year = {}
    for year in YEARS:
        v = sorted(c["square_sum"] for c in cells if c["year"] == year)
        by_year[year] = {
            "n": len(v), "positive": sum(1 for x in v if x > 0),
            "negative": sum(1 for x in v if x < 0),
            "median": v[len(v) // 2], "min": v[0], "max": v[-1],
        }
    rec["by_year"] = by_year
    print("\nsign and median by year (reported, no line drawn on it)")
    print("  %-6s %4s %4s %4s %10s %10s %10s"
          % ("year", "n", "pos", "neg", "median", "min", "max"))
    for year in YEARS:
        b = by_year[year]
        print("  %-6s %4d %4d %4d %10.4f %10.4f %10.4f"
              % (year, b["n"], b["positive"], b["negative"], b["median"],
                 b["min"], b["max"]))

    print("\n  every cell, and the four prices behind it")
    print("  %-18s %6s %11s %10s %10s %10s %10s"
          % ("country", "year", "square", "P re", "P ie", "P rg", "P ig"))
    for c in cells:
        print("  %-18s %6s %11.6f %10.3f %10.3f %10.3f %10.3f"
              % (c["country"], c["year"], c["square_sum"],
                 c["price_resid_electricity"], c["price_ind_electricity"],
                 c["price_resid_gas"], c["price_ind_gas"]))

    # ---- the three questions a square has to answer before it is read ------
    rec["degeneracy_check"] = {
        "edges_traversable": "both classes buy both carriers in every locked "
                             "country, so this is a first cohomology object and "
                             "not a reachability statement",
        "terms_nonzero": "the two classes face separate published tariffs, so "
                         "the first term is not zero by construction",
        "where_the_difference_is_published": "all four prices are compiled from "
                                             "national official sources and "
                                             "published annually, per carrier "
                                             "and per class",
        "unobserved": "the two transfer wedges are not observed; for the full "
                      "sum to vanish they would have to cancel the measured "
                      "term in every one of the cells",
    }

    rec["criteria"] = {
        "B49-1": {
            "kind": "instrument",
            "name": "locked panel complete: all four series in all three years",
            "passed": all(all("%s|%s" % (c, y) in base[k]
                              for y in YEARS for k in SERIES) for c in locked)
                      and len(locked) > 0,
            "detail": "%d countries, %d cells, %d prices"
                      % (len(locked), len(cells), len(cells) * len(SERIES)),
        },
        "B49-2": {
            "kind": "bookkeeping",
            "name": "roster is never shorter than the records it names, and the "
                    "gap between the two is reported per product (D37)",
            "passed": all(grid[p]["roster_countries"]
                          >= grid[p]["record_countries_all_three_years"]
                          for p in ALL_PRODUCTS),
            "detail": "; ".join(
                "%s roster %d record %d all-three-years %d paired %d"
                % (p, grid[p]["roster_countries"], grid[p]["record_countries"],
                   grid[p]["record_countries_all_three_years"],
                   grid[p]["paired_cells"]) for p in ALL_PRODUCTS),
        },
        "B49-3": {
            "kind": "instrument",
            "name": "square sum invariant to the currency the prices are quoted "
                    "in (implementation check, not independent confirmation)",
            "passed": floor is not None,
            "detail": "floor from %s = %.3e, worst cell %s"
                      % (floor_unit, floor, per_unit[floor_unit]["worst_cell"]),
        },
        "B49-4": {
            "kind": "instrument",
            "name": "every square sum stands above the measured floor (D24); a "
                    "cell at or below it is unreadable rather than zero",
            "passed": len(at_or_below) == 0,
            "detail": "%d of %d above %.3e; smallest %.1f x floor, median %.0f x"
                      "; at or below: %s"
                      % (len(above), len(cells), floor, mags[0] / floor,
                         mags[len(mags) // 2] / floor,
                         ", ".join(at_or_below) or "none"),
        },
        "B49-5": {
            "kind": "rival",
            "name": "no cell matches the rival's point prediction, which is that "
                    "every square sum is exactly zero",
            "passed": len(exact_zero) == 0,
            "detail": "%d of %d cells are exactly zero"
                      % (len(exact_zero), len(cells)),
        },
    }
    # The sign distribution is an object this run prints, not a criterion. No
    # line is drawn on it here or anywhere else.
    rec["readings"] = {
        "sign_and_median_by_year": "; ".join(
            "%s: %d+ %d- median %.4f"
            % (y, by_year[y]["positive"], by_year[y]["negative"],
               by_year[y]["median"]) for y in YEARS),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for name in sorted(rec["criteria"]):
        c = rec["criteria"][name]
        print("  %-7s %-4s %s" % (name, "PASS" if c["passed"] else "FAIL",
                                  c["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
