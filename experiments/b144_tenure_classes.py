"""B144 arm H: the same country, four classes of household by how they hold their home.

Eurostat's survey of income and living conditions reports, for each country and year, the share
of people living in a household whose housing costs exceed 40 percent of its disposable income
(the housing cost overburden rate), in four tenure classes: owners with a mortgage or loan, owners
without one, tenants at the market price, and tenants at a reduced price or free. The last class
is one a sovereign writes: social, public or employer housing below the market price. Beside it,
median equivalised income of owners and of tenants, so that a reader sees how far the classes
also differ in income.

  B144-H0  instrument    the two tables say what the reading takes them to say
  B144-H1  own_reading   inside one country the tenure class moves the overburden rate more than
                         the country moves it: the median spread across the four classes is
                         larger than the spread of the total rate across countries, every year
  B144-H2  own_reading   tenants at a reduced price are overburdened less than tenants at the
                         market price: the median difference across countries is positive every
                         year, with cells of low reliability in and out

Run from the repo root:
    python experiments/b144_tenure_classes.py
    python experiments/b144_tenure_classes.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144" / "eurostat"
OUT = ROOT / "results" / "b144_tenure_classes.json"

CLASSES = ("OWN_NL", "OWN_L", "RENT_MKT", "RENT_FR")
NAMES = {"OWN_NL": "owners without a mortgage", "OWN_L": "owners with a mortgage",
         "RENT_MKT": "tenants at the market price", "RENT_FR": "tenants at a reduced price or free"}
AGGREGATES = ("EU27_2020", "EA20", "EA21")
YEARS = ("2023", "2024", "2025")
RELIABILITY = ("every cell", "without cells flagged of low reliability")
MIN_COUNTRIES = 25


def read_rates(path: Path) -> dict:
    out, units, flags = {}, set(), {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            units.add(r["unit"])
            if r["OBS_VALUE"] == "":
                continue
            out.setdefault(r["geo"], {}).setdefault(r["TIME_PERIOD"], {})[r["tenure"]] = float(r["OBS_VALUE"])
            flags.setdefault(r["geo"], {}).setdefault(r["TIME_PERIOD"], {})[r["tenure"]] = r["OBS_FLAG"]
    return {"rates": out, "flags": flags, "units": sorted(units)}


def read_income(path: Path) -> dict:
    """geo -> year -> tenure -> median equivalised income in purchasing power standards."""
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if (r["statinfo"], r["unit"], r["sex"], r["age"]) == ("MED_EI", "PPS", "T", "TOTAL") and r["OBS_VALUE"]:
                out.setdefault(r["geo"], {}).setdefault(r["TIME_PERIOD"], {})[r["tenure"]] = float(r["OBS_VALUE"])
    return out


def load() -> dict:
    d = read_rates(RAW / "ilc_lvho07c.csv")
    d["income"] = read_income(RAW / "ilc_di09.csv")
    return d


def cells(data: dict, year: str, reliability: str) -> dict:
    """country -> class -> rate, for countries with all four classes and the total in that year."""
    out = {}
    for geo, by in data["rates"].items():
        if geo in AGGREGATES or year not in by:
            continue
        row = by[year]
        fl = data["flags"].get(geo, {}).get(year, {})
        if all(c in row for c in CLASSES + ("TOTAL",)):
            if reliability == RELIABILITY[1] and any("u" in fl.get(c, "") for c in CLASSES + ("TOTAL",)):
                continue
            out[geo] = row
    return out


def spreads(data: dict) -> list:
    rows = []
    for y in YEARS:
        for rel in RELIABILITY:
            c = cells(data, y, rel)
            totals = [r["TOTAL"] for r in c.values()]
            inside = [float(np.std([r[k] for k in CLASSES])) for r in c.values()]
            gaps = [r["RENT_MKT"] - r["RENT_FR"] for r in c.values()]
            rows.append({"year": y, "reliability": rel, "countries": len(c),
                         "between": float(np.std(totals)) if totals else math.nan,
                         "within_median": float(np.median(inside)) if inside else math.nan,
                         "reduced_gap_median": float(np.median(gaps)) if gaps else math.nan,
                         "reduced_lower_in": int(sum(g > 0 for g in gaps)),
                         "class_medians": {k: float(np.median([r[k] for r in c.values()])) if c else math.nan
                                           for k in CLASSES + ("TOTAL",)}})
    return rows


def c_h0(data: dict):
    problems = []
    if data["units"] != ["PC"]:
        problems.append(f"the unit is {data['units']}, not a percentage")
    for y in YEARS:
        n = len(cells(data, y, RELIABILITY[0]))
        if n < MIN_COUNTRIES:
            problems.append(f"only {n} countries carry every class in {y}")
    bad = [(g, y, k, v) for g, by in data["rates"].items() for y, row in by.items() for k, v in row.items()
           if not 0 <= v <= 100]
    if bad:
        problems.append(f"{len(bad)} rates outside 0 to 100, the first {bad[0]}")
    if not data["income"]:
        problems.append("no median income by tenure")
    low = sum("u" in f for by in data["flags"].values() for row in by.values() for f in row.values())
    detail = (f"{len([g for g in data['rates'] if g not in AGGREGATES])} countries; with every class: "
              + ", ".join(f"{y} {len(cells(data, y, RELIABILITY[0]))}" for y in YEARS)
              + f"; {low} cells flagged of low reliability; "
              + ("; ".join(problems) if problems else "unit and classes as expected"))
    return not problems, detail, {"problems": problems}


def c_h1(data: dict, rows: list):
    ok = [r for r in rows if math.isfinite(r["between"]) and math.isfinite(r["within_median"])]
    if len(ok) != len(rows) or not rows:
        state = "unread"
    elif all(r["within_median"] > r["between"] for r in rows):
        state = "class larger"
    elif all(r["within_median"] < r["between"] for r in rows):
        state = "country larger"
    else:
        state = "unread"
    r0 = next(r for r in rows if r["year"] == YEARS[-1] and r["reliability"] == RELIABILITY[0])
    eu = data["rates"].get("EU27_2020", {}).get(YEARS[-1], {})
    inc = data["income"].get("EU27_2020", {}).get(YEARS[-1], {})
    detail = (f"{YEARS[-1]}, {r0['countries']} countries: median rate by class "
              + ", ".join(f"{NAMES[k]} {r0['class_medians'][k]:.1f}%" for k in CLASSES)
              + f"; Union as a whole " + ", ".join(f"{NAMES[k]} {eu.get(k, math.nan):.1f}%" for k in CLASSES)
              + f". Spread across the four classes inside a country {r0['within_median']:.1f} points at the "
              f"median, spread of the total rate across countries {r0['between']:.1f}; over the years and both "
              f"reliability settings {min(r['within_median'] for r in rows):.1f} to "
              f"{max(r['within_median'] for r in rows):.1f} against {min(r['between'] for r in rows):.1f} to "
              f"{max(r['between'] for r in rows):.1f}. Median equivalised income in the Union, owners "
              f"{inc.get('OWN', math.nan):,.0f} and tenants {inc.get('RENT', math.nan):,.0f} in purchasing power "
              f"standards -> {state}")
    passed = True if state == "class larger" else (False if state == "country larger" else None)
    return passed, detail, {"state": state}


def c_h2(rows: list):
    gaps = [r["reduced_gap_median"] for r in rows]
    if any(not math.isfinite(g) for g in gaps) or not gaps:
        state = "unread"
    elif all(g > 0 for g in gaps):
        state = "reduced lower"
    elif all(g < 0 for g in gaps):
        state = "reduced higher"
    else:
        state = "unread"
    r0 = next(r for r in rows if r["year"] == YEARS[-1] and r["reliability"] == RELIABILITY[0])
    detail = (f"tenants at the market price less tenants at a reduced price, median over countries "
              f"{r0['reduced_gap_median']:+.1f} points in {YEARS[-1]} (lower in {r0['reduced_lower_in']} of "
              f"{r0['countries']} countries); over the years and both reliability settings "
              f"{min(gaps):+.1f} to {max(gaps):+.1f} -> {state}")
    passed = True if state == "reduced lower" else (False if state == "reduced higher" else None)
    return passed, detail, {"state": state}


KINDS = {"B144-H0": "instrument", "B144-H1": "own_reading", "B144-H2": "own_reading"}
STATEMENTS = {
    "B144-H0": "The two tables say what the reading takes them to say.",
    "B144-H1": "Inside one country the tenure class moves the housing cost overburden rate more than the country "
               "moves it.",
    "B144-H2": "Tenants at a reduced price are overburdened less than tenants at the market price.",
}


def r4(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 4)
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data: dict):
    rows = spreads(data)
    return {"B144-H0": c_h0(data), "B144-H1": c_h1(data, rows), "B144-H2": c_h2(rows)}, rows


def toy(class_gap=20.0, country_gap=4.0, reduced=-8.0, n=30) -> dict:
    rates, flags = {}, {}
    for i in range(n):
        geo = f"C{i:02d}"
        base = 5.0 + country_gap * (i / (n - 1) - 0.5) * 2
        for y in YEARS:
            row = {"OWN_NL": base, "OWN_L": base + class_gap * 0.3, "RENT_MKT": base + class_gap,
                   "RENT_FR": base + class_gap + reduced}
            row = {k: min(max(v, 0.0), 100.0) for k, v in row.items()}
            row["TOTAL"] = float(np.mean(list(row.values())))
            rates.setdefault(geo, {})[y] = row
            flags.setdefault(geo, {})[y] = {k: "" for k in row}
    rates["EU27_2020"] = {y: dict(rates["C00"][y]) for y in YEARS}
    return {"rates": rates, "flags": flags, "units": ["PC"],
            "income": {"EU27_2020": {YEARS[-1]: {"OWN": 25000.0, "RENT": 19000.0}}}}


def selftest() -> None:
    res, rows = run(toy())
    assert res["B144-H0"][0], res["B144-H0"][1]
    assert res["B144-H1"][0] is True and res["B144-H2"][0] is True
    assert all(r["countries"] == 30 for r in rows), "the aggregate is not a country"
    assert run(toy(class_gap=1.0, country_gap=40.0))[0]["B144-H1"][0] is False
    assert run(toy(reduced=+5.0))[0]["B144-H2"][0] is False
    mixed = toy()
    for geo in mixed["rates"]:
        mixed["rates"][geo]["2024"]["RENT_FR"] = mixed["rates"][geo]["2024"]["RENT_MKT"] + 3.0
    assert run(mixed)[0]["B144-H2"][0] is None, "a sign that changes with the year is unread"
    flagged = toy()
    for geo in list(flagged["flags"])[:10]:
        flagged["flags"][geo]["2023"]["RENT_FR"] = "u"
    assert len(cells(flagged, "2023", RELIABILITY[1])) == 20 and len(cells(flagged, "2023", RELIABILITY[0])) == 30
    for change in ("unit", "few", "range", "income"):
        b = toy()
        if change == "unit":
            b["units"] = ["PC", "THS_PER"]
        elif change == "few":
            b["rates"] = {k: v for k, v in list(b["rates"].items())[:10]}
        elif change == "range":
            b["rates"]["C03"]["2025"]["OWN_L"] = 140.0
        else:
            b["income"] = {}
        assert not c_h0(b)[0], f"H0 must fail on {change}"
    print("selftest ok: every flag fails on its planted input, and a sign that changes with the year is unread")


def main() -> int:
    data = load()
    res, rows = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    last = {g: by.get(YEARS[-1]) for g, by in data["rates"].items() if by.get(YEARS[-1])}
    income = {g: by.get(YEARS[-1]) for g, by in data["income"].items() if by.get(YEARS[-1])}
    record = {
        "stage": "B144", "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d}
                     for n, (p, d, _) in res.items()],
        "objects": {"spreads": r4(rows), "rates_last_year": r4(last), "median_income_pps_last_year": r4(income),
                    "states": {n: o for n, (_, _, o) in res.items()}},
        "config": {"raw": "data/raw/b144/eurostat", "fetched_by": "experiments/b144_fetch.py --only eurostat",
                   "classes": NAMES, "years": list(YEARS), "aggregates_left_out": list(AGGREGATES),
                   "reliability": list(RELIABILITY), "min_countries": MIN_COUNTRIES},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-H0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
