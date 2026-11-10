"""B144 arm I: the same rows read along time inside one country.

Arms A and F read how far a price follows the wage across places: between countries, and across
the regions of one country. This arm reads the third direction: over decades inside the United
States, where every place's wage moves together and a writer who governs the whole country
rewrites its number year by year. For each consumer price index component the elasticity is

    (log P(end) - log P(start)) / (log W(end) - log W(start))

with W the average hourly earnings of production and nonsupervisory employees and annual
averages of twelve months. Knob grid: start 1991 or 2000, end 2019 or 2024 (the index for October
2025 was not published, so 2025 has no twelve-month average).

  B144-I0  instrument    the series are all there, with twelve months in every year read
  B144-I1  own_reading   along time, goods with global writers fall behind the wage and services
                         sold on the spot keep up with it: the median elasticity of the first is
                         below that of the second at every knob point
  B144-I2  own_reading   prices written by one institution for a country (tuition, hospital,
                         physicians, water) rise faster than the wage: their median elasticity
                         is above one at every knob point
  B144-I3  own_reading   services sold on the spot follow the wage along time more than they
                         follow it across countries (arm A) or across regions of one country
                         (arm F), at every knob point

Run from the repo root:
    python experiments/b144_time_slopes.py
    python experiments/b144_time_slopes.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144" / "bls"
ARM_A = ROOT / "results" / "b144_wage_coordinates.json"
ARM_F = ROOT / "results" / "b144_one_basket.json"
OUT = ROOT / "results" / "b144_time_slopes.json"

WAGE = "CEU0500000008"
CLASSES = {
    "goods with global writers": {"CUUR0000SETA01": "new vehicles", "CUUR0000SAA": "apparel",
                                  "CUUR0000SERA01": "televisions"},
    "food at home": {"CUUR0000SAF11": "food at home"},
    "services sold on the spot": {"CUUR0000SEFV": "food away from home", "CUUR0000SEGD": "personal care services",
                                  "CUUR0000SEEB03": "day care and preschool",
                                  "CUUR0000SETD": "motor vehicle maintenance and repair"},
    "position": {"CUUR0000SEHA": "rent of primary residence", "CUUR0000SEHC": "owners' equivalent rent"},
    "written by one institution": {"CUUR0000SEEB01": "college tuition and fees",
                                   "CUUR0000SEMD": "hospital and related services",
                                   "CUUR0000SEMC01": "physicians' services",
                                   "CUUR0000SEHG": "water and sewer and trash collection"},
}
ALL_ITEMS = "CUUR0000SA0"
STARTS, ENDS = (1991, 2000), (2019, 2024)   # October 2025 was not published, so 2025 has eleven months
KNOBS = [(s, e) for s in STARTS for e in ENDS]


def load() -> dict:
    months = {}
    for f in sorted(RAW.glob("cpi_*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        for s in j["Results"]["series"]:
            for d in s["data"]:
                if d["period"].startswith("M") and d["period"] != "M13" and d["value"] not in ("", "-"):
                    months.setdefault(s["seriesID"], {}).setdefault(int(d["year"]), {})[d["period"]] = float(d["value"])
    return {"months": months}


def annual(data: dict, sid: str, year: int) -> float:
    m = data["months"].get(sid, {}).get(year, {})
    return float(np.mean(list(m.values()))) if len(m) == 12 else math.nan


def elasticity(data: dict, sid: str, start: int, end: int) -> float:
    p0, p1 = annual(data, sid, start), annual(data, sid, end)
    w0, w1 = annual(data, WAGE, start), annual(data, WAGE, end)
    if not all(math.isfinite(x) and x > 0 for x in (p0, p1, w0, w1)) or w1 == w0:
        return math.nan
    return math.log(p1 / p0) / math.log(w1 / w0)


def grid(data: dict) -> list:
    out = []
    for s, e in KNOBS:
        el = {sid: elasticity(data, sid, s, e) for c in CLASSES.values() for sid in c}
        med = {name: float(np.nanmedian([el[sid] for sid in c])) if any(math.isfinite(el[sid]) for sid in c)
               else math.nan for name, c in CLASSES.items()}
        out.append({"start": s, "end": e, "elasticity": el, "class_median": med,
                    "wage_growth": annual(data, WAGE, e) / annual(data, WAGE, s),
                    "all_items": elasticity(data, ALL_ITEMS, s, e)})
    return out


def across(path_a: Path, path_f: Path) -> dict:
    a = json.loads(path_a.read_text(encoding="utf-8"))["objects"]["classes"]["LOCAL"]["between"]
    f = json.loads(path_f.read_text(encoding="utf-8"))["objects"]["group_grid"][0]["services"]
    return {"between countries": float(a), "across regions of one country": float(f)}


def c_i0(data: dict, g: list):
    problems = []
    for sid in [WAGE, ALL_ITEMS] + [s for c in CLASSES.values() for s in c]:
        if sid not in data["months"]:
            problems.append(f"no series {sid}")
    for s, e in KNOBS:
        for sid in (WAGE, ALL_ITEMS):
            if not (math.isfinite(annual(data, sid, s)) and math.isfinite(annual(data, sid, e))):
                problems.append(f"{sid} lacks a full year at {s} or {e}")
    missing = sorted({sid for pt in g for sid, v in pt["elasticity"].items() if not math.isfinite(v)})
    detail = (f"{len(data['months'])} series; wage {annual(data, WAGE, 1991):.2f} in 1991 and "
              f"{annual(data, WAGE, 2024):.2f} in 2024 an hour; series without a full start year at some knob point: "
              f"{missing or 'none'}; " + ("; ".join(problems) if problems else "every class has members at every knob point"))
    return not problems, detail, {"problems": problems, "short": missing}


def c_i1(g: list):
    states = ["global below" if pt["class_median"]["goods with global writers"]
              < pt["class_median"]["services sold on the spot"] else "global above" for pt in g]
    state = states[0] if len(set(states)) == 1 else "unread"
    p0 = g[0]
    names = {sid: n for c in CLASSES.values() for sid, n in c.items()}
    detail = (f"{p0['start']} to {p0['end']}, wage up {p0['wage_growth']:.2f} times: "
              + "; ".join(f"{n} {p0['elasticity'][sid]:+.2f}" for sid, n in names.items()
                          if math.isfinite(p0['elasticity'][sid]))
              + f"; all items {p0['all_items']:+.2f}. Class medians over the knob grid: "
              + "; ".join(f"{c} {min(pt['class_median'][c] for pt in g):+.2f} to "
                          f"{max(pt['class_median'][c] for pt in g):+.2f}" for c in CLASSES) + f" -> {state}")
    passed = True if state == "global below" else (False if state == "global above" else None)
    return passed, detail, {"state": state}


def c_i2(g: list):
    vals = [pt["class_median"]["written by one institution"] for pt in g]
    state = ("faster than the wage" if all(v > 1 for v in vals) else
             "slower than the wage" if all(v < 1 for v in vals) else "unread")
    detail = (f"median elasticity of the four rows one institution writes {min(vals):+.2f} to {max(vals):+.2f} over "
              f"{len(vals)} knob points; position {min(pt['class_median']['position'] for pt in g):+.2f} to "
              f"{max(pt['class_median']['position'] for pt in g):+.2f} -> {state}")
    passed = True if state == "faster than the wage" else (False if state == "slower than the wage" else None)
    return passed, detail, {"state": state}


def c_i3(g: list, ac: dict):
    t = [pt["class_median"]["services sold on the spot"] for pt in g]
    top = max(ac.values())
    state = ("time steeper" if all(x > top for x in t) else
             "place steeper" if all(x < min(ac.values()) for x in t) else "unread")
    detail = (f"services sold on the spot follow the wage by {min(t):+.2f} to {max(t):+.2f} along time; across "
              + "; ".join(f"{k} {v:+.3f}" for k, v in ac.items()) + f" -> {state}")
    passed = True if state == "time steeper" else (False if state == "place steeper" else None)
    return passed, detail, {"state": state, "across": ac}


KINDS = {"B144-I0": "instrument", "B144-I1": "own_reading", "B144-I2": "own_reading", "B144-I3": "own_reading"}
STATEMENTS = {
    "B144-I0": "The series are all there, with twelve months in every year read.",
    "B144-I1": "Along time, goods with global writers fall behind the wage more than services sold on the spot.",
    "B144-I2": "Prices one institution writes for a whole country rise faster than the wage.",
    "B144-I3": "Services sold on the spot follow the wage along time more than they follow it across places.",
}


def r4(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 4)
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data: dict, ac: dict):
    g = grid(data)
    return {"B144-I0": c_i0(data, g), "B144-I1": c_i1(g), "B144-I2": c_i2(g), "B144-I3": c_i3(g, ac)}, g


def toy(rates: dict | None = None, late: dict | None = None) -> dict:
    """Monthly series growing at planted yearly rates; the wage grows 3.5 percent a year."""
    base = {"global": 0.0, "food": 0.025, "spot": 0.035, "position": 0.04, "institution": 0.05}
    base.update(rates or {})
    kind = {"goods with global writers": "global", "food at home": "food", "services sold on the spot": "spot",
            "position": "position", "written by one institution": "institution"}
    months = {}

    def series(sid, g, extra=0.0):
        months[sid] = {y: {f"M{m:02d}": 100 * math.exp(g * (y - 1990 + m / 12) + extra * max(0.0, y - 2019 + m / 12))
                           for m in range(1, 13)} for y in range(1990, 2026)}
    series(WAGE, 0.035)
    series(ALL_ITEMS, 0.025)
    for c, ids in CLASSES.items():
        for sid in ids:
            series(sid, base[kind[c]], (late or {}).get(kind[c], 0.0))
    return {"months": months}


def selftest() -> None:
    ac = {"between countries": 0.4, "across regions of one country": 0.44}
    d = toy()
    assert abs(elasticity(d, "CUUR0000SEFV", 1991, 2025) - 1.0) < 1e-9
    assert abs(elasticity(d, "CUUR0000SEHA", 2000, 2019) - 0.04 / 0.035) < 1e-9
    res, _ = run(d, ac)
    assert all(v[0] for v in res.values()), {k: v[1] for k, v in res.items()}
    assert run(toy({"global": 0.05, "spot": 0.01}), ac)[0]["B144-I1"][0] is False
    assert run(toy({"institution": 0.02}), ac)[0]["B144-I2"][0] is False
    assert run(toy({"spot": 0.01}), ac)[0]["B144-I3"][0] is False
    assert run(toy(late={"global": 0.5}), ac)[0]["B144-I1"][0] is None, "an order that turns at a later end is unread"
    assert run(d, {"between countries": 0.4, "across regions of one country": 1.2})[0]["B144-I3"][0] is None,         "a time slope between the two across-place slopes is unread"
    short = toy()
    del short["months"]["CUUR0000SEFV"][1991]["M05"]
    assert math.isnan(elasticity(short, "CUUR0000SEFV", 1991, 2025)), "a year with a month missing is not read"
    gone = toy()
    del gone["months"][WAGE]
    assert not c_i0(gone, grid(gone))[0]
    print("selftest ok: planted growth comes back as elasticities, and every flag fails on its planted input")


def main() -> int:
    data = load()
    ac = across(ARM_A, ARM_F)
    res, g = run(data, ac)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    record = {
        "stage": "B144", "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d}
                     for n, (p, d, _) in res.items()],
        "objects": {"grid": r4(g), "across_places": r4(ac), "states": {n: o for n, (_, _, o) in res.items()}},
        "config": {"raw": "data/raw/b144/bls", "fetched_by": "experiments/b144_fetch.py --only bls",
                   "wage": WAGE, "classes": CLASSES, "starts": list(STARTS), "ends": list(ENDS),
                   "across_from": ["results/b144_wage_coordinates.json", "results/b144_one_basket.json"]},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-I0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
