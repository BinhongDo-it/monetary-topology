"""B144, one country from inside with official numbers: rent and the wage of those who serve.

Arm A read a crowdsourced table and found position rows steeper against the local salary
inside countries than between them, relative to rows produced where they are sold. That
quotient does not say which side moved: the position taking up the wage gap, or the wage of
those who supply local services being held flat across a country. Here both are measured
directly, in one country, on official series.

Sources, fetched by `b144_fetch.py --only us` into data/raw/b144/us/
  BEA   regional price parities by metropolitan area, MARPP. Line 3 is called
        "RPPs: Services: Housing"; its definition says "Housing price levels are only
        estimated for tenant-occupied housing", so it is a level of rents.
  BLS   quarterly census of employment and wages, annual averages. `annual_avg_wkly_wage`
        by metropolitan area: every employer (own_code 0), private employers (own_code 5),
        and private employers of nine industries that supply local services.

Each reading is a slope in logs across metropolitan areas.

Criteria (each has a planted input in --selftest that must make it fail):
  B144-A6  instrument    the two sources parse and join; the United States row of the
                         all-items parity is 100; the definition file says what line 3 is;
                         weekly wage times 52 is annual pay in the wage file
  B144-A7  own_reading   rent against the area's average wage: more than one for one, at
                         every knob point
  B144-A8  own_reading   the wage in each industry that supplies local services against the
                         area's average wage: less than one for one, at every knob point
  B144-A9  own_reading   rent responds to the area's average wage more than the wage of each
                         such industry does, on the areas where that industry is disclosed

Knobs: the average wage of every employer or of private employers; 2024 or 2023; areas
counted once each or by employment.

Run from the repo root:
    python experiments/b144_inside_one_country.py
    python experiments/b144_inside_one_country.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144" / "us"
OUT = ROOT / "results" / "b144_inside_one_country.json"

INDUSTRIES = {"8121": "personal care services", "7225": "restaurants and other eating places",
              "5617": "services to buildings and dwellings", "2382": "building equipment contractors",
              "8111": "automotive repair and maintenance", "6244": "child day care services",
              "8123": "drycleaning and laundry services", "2361": "residential building construction",
              "4451": "grocery stores"}
LINES = {"1": "all items", "2": "goods", "3": "housing", "4": "utilities", "5": "other services"}
SENTENCE = "Housing price levels are only estimated for tenant-occupied housing"
BASE = ("every employer", "private employers")       # knobs; the first of each is the default
YEARS = (2024, 2023)
WEIGHT = ("each area once", "by employment")
N_BOOT = 1000
SEEDS = (20261012, 20261013)


# ----------------------------------------------------------------------------- loading
def load_parities():
    z = zipfile.ZipFile(RAW / "MARPP.zip")
    name = next(n for n in z.namelist() if n.startswith("MARPP_MSA") and n.endswith(".csv"))
    rows = list(csv.reader(io.TextIOWrapper(z.open(name), encoding="latin-1")))
    head = rows[0]
    out = {y: {ln: {} for ln in LINES} for y in YEARS}
    us = {}
    for r in rows[1:]:
        if len(r) < len(head) or r[4].strip() not in LINES:
            continue
        code = r[0].replace('"', "").strip()
        for y in YEARS:
            try:
                v = float(r[head.index(str(y))])
            except ValueError:
                continue
            if code == "00000":
                us[(y, r[4].strip())] = v
            elif not code.startswith("00"):
                out[y][r[4].strip()][code] = v
    definition = z.read(next(n for n in z.namelist() if n.startswith("MARPP__definition"))).decode("latin-1")
    return {"values": out, "us": us, "definition": " ".join(definition.split())}


def load_wages():
    out = {}
    identity = []
    for y in YEARS:
        for code in ["10"] + list(INDUSTRIES):
            with (RAW / f"qcew_{y}_{code}.csv").open(encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    a = r["area_fips"]
                    if not a.startswith("C") or r["disclosure_code"].strip():
                        continue
                    if code == "10":
                        key = {("0", "40"): "every employer", ("5", "41"): "private employers"}.get(
                            (r["own_code"], r["agglvl_code"]))
                    else:
                        key = code if r["own_code"] == "5" else None
                    wage, emp = float(r["annual_avg_wkly_wage"]), float(r["annual_avg_emplvl"])
                    if key is None or wage <= 0 or emp <= 0:
                        continue
                    out[(y, key, a)] = (wage, emp)
                    if code == "10" and key == "every employer":
                        identity.append(float(r["avg_annual_pay"]) / (52.0 * wage))
    return {"cells": out, "identity": identity}


def load() -> dict:
    return {"parities": load_parities(), "wages": load_wages()}


# ----------------------------------------------------------------------------- pieces
def slope(x, y, w=None) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    if x.size < 3:
        return math.nan
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    sxx = float((w * (x - mx) ** 2).sum())
    return float((w * (x - mx) * (y - my)).sum() / sxx) if sxx > 0 else math.nan


def table(data, year, base):
    """Per area: log average wage, employment, log price parities, log industry wages."""
    par, cells = data["parities"]["values"][year], data["wages"]["cells"]
    rows = []
    for code in sorted(par["3"]):
        key = "C" + code[:4]
        wage = cells.get((year, base, key))
        if wage is None or not all(code in par[ln] for ln in LINES):
            continue
        rows.append({"area": code, "wage": math.log(wage[0]), "emp": wage[1],
                     **{LINES[ln]: math.log(par[ln][code]) for ln in LINES},
                     **{ind: (math.log(cells[(year, ind, key)][0]) if (year, ind, key) in cells else None)
                        for ind in INDUSTRIES}})
    return rows


def readings(rows, weight):
    w = [r["emp"] for r in rows] if weight == "by employment" else None
    x = [r["wage"] for r in rows]
    out = {"areas": len(rows), "parities": {name: slope(x, [r[name] for r in rows], w) for name in LINES.values()},
           "industry": {}, "rent_same_areas": {}, "industry_areas": {}}
    for ind in INDUSTRIES:
        sub = [r for r in rows if r[ind] is not None]
        ws = [r["emp"] for r in sub] if weight == "by employment" else None
        xs = [r["wage"] for r in sub]
        out["industry"][ind] = slope(xs, [r[ind] for r in sub], ws)
        out["rent_same_areas"][ind] = slope(xs, [r["housing"] for r in sub], ws)
        out["industry_areas"][ind] = len(sub)
    return out


def grid(data):
    out = []
    for base, year, weight in itertools.product(BASE, YEARS, WEIGHT):
        out.append({"base": base, "year": year, "weight": weight, **readings(table(data, year, base), weight)})
    return out


def bootstrap(rows, seeds=SEEDS, n_boot=N_BOOT):
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        rent, inds, gaps = [], {ind: [] for ind in INDUSTRIES}, {ind: [] for ind in INDUSTRIES}
        for _ in range(n_boot):
            pick = [rows[i] for i in rng.integers(0, len(rows), size=len(rows))]
            r = readings(pick, WEIGHT[0])
            rent.append(r["parities"]["housing"])
            for ind in INDUSTRIES:
                inds[ind].append(r["industry"][ind])
                gaps[ind].append(r["rent_same_areas"][ind] - r["industry"][ind])
        out.append({"rent": [float(np.quantile(rent, q)) for q in (0.025, 0.975)],
                    "industry": {ind: [float(np.nanquantile(v, q)) for q in (0.025, 0.975)]
                                 for ind, v in inds.items()},
                    "gap": {ind: [float(np.nanquantile(v, q)) for q in (0.025, 0.975)]
                            for ind, v in gaps.items()}})
    return out


STATES = {"above one": "more than one for one at every knob point",
          "below one": "less than one for one at every knob point",
          "unread": "the side of one changes somewhere on the knob grid, or a slope is undefined"}


def side(values) -> str:
    v = list(values)
    if not v or any(not math.isfinite(x) for x in v):
        return "unread"
    if all(x > 1 for x in v):
        return "above one"
    if all(x < 1 for x in v):
        return "below one"
    return "unread"


def verdict(states, want: str):
    """All on the wanted side: true. None on it and none unread: false. Anything else: unread."""
    s = list(states)
    if s and all(x == want for x in s):
        return True
    if s and all(x != want and x != "unread" for x in s):
        return False
    return None


# ----------------------------------------------------------------------------- criteria
def c_a6(data):
    par, wages = data["parities"], data["wages"]
    rows = table(data, YEARS[0], BASE[0])
    problems = []
    for y in YEARS:
        if abs(par["us"].get((y, "1"), math.nan) - 100.0) > 1e-9:
            problems.append(f"United States row of the all-items parity in {y} is not 100")
    if SENTENCE not in par["definition"]:
        problems.append("the definition file does not say what line 3 is")
    ident = wages["identity"]
    if not ident or abs(float(np.median(ident)) - 1.0) > 0.01:
        problems.append("weekly wage times 52 is not annual pay")
    if len(rows) < 300:
        problems.append(f"only {len(rows)} areas join")
    detail = (f"{len(par['values'][YEARS[0]]['3'])} areas carry a housing parity in {YEARS[0]}, {len(rows)} join the "
              f"wage file with all five lines; annual pay over 52 weekly wages, median "
              f"{float(np.median(ident)) if ident else math.nan:.4f}; industries with a disclosed wage in "
              f"{min(sum(r[i] is not None for r in rows) for i in INDUSTRIES)} to "
              f"{max(sum(r[i] is not None for r in rows) for i in INDUSTRIES)} areas; "
              + ("; ".join(problems) if problems else "the definition file calls line 3 a level of tenant rents")
              + ". United States row of the other lines in " + str(YEARS[0]) + ": "
              + ", ".join(f"{LINES[ln]} {par['us'].get((YEARS[0], ln), math.nan):.1f}" for ln in LINES if ln != "1"))
    return not problems, detail, {"problems": problems,
                                  "united_states_rows": {LINES[ln]: par["us"].get((YEARS[0], ln)) for ln in LINES}}


def c_a7(g, boot):
    v = [pt["parities"]["housing"] for pt in g]
    state = side(v)
    detail = (f"rent against the area's average wage: {v[0]:.3f} ({min(v):.3f} to {max(v):.3f} over {len(v)} knob "
              f"points; area resamples {boot[0]['rent'][0]:.3f} to {boot[0]['rent'][1]:.3f}), {g[0]['areas']} areas "
              f"-> {state}. Same areas: goods {g[0]['parities']['goods']:.3f}, other services "
              f"{g[0]['parities']['other services']:.3f}, utilities {g[0]['parities']['utilities']:.3f}, all items "
              f"{g[0]['parities']['all items']:.3f}")
    return verdict([state], "above one"), detail, {"state": state}


def c_a8(g, boot):
    states = {ind: side(pt["industry"][ind] for pt in g) for ind in INDUSTRIES}
    parts = [f"{INDUSTRIES[ind]} {g[0]['industry'][ind]:.3f} ({min(pt['industry'][ind] for pt in g):.3f} to "
             f"{max(pt['industry'][ind] for pt in g):.3f}, {g[0]['industry_areas'][ind]} areas)" for ind in INDUSTRIES]
    n = sum(s == "below one" for s in states.values())
    detail = (f"wage of the industry against the area's average wage: " + "; ".join(parts)
              + f". Below one at every knob point: {n} of {len(states)}")
    return verdict(states.values(), "below one"), detail, {"states": states}


STATES_GAP = {"rent steeper": "rent responds more than the industry's wage at every knob point",
              "wage steeper": "the industry's wage responds more than rent at every knob point",
              "unread": "the order changes somewhere on the knob grid, or a slope is undefined"}


def c_a9(g, boot):
    states, parts = {}, []
    for ind in INDUSTRIES:
        d = [pt["rent_same_areas"][ind] - pt["industry"][ind] for pt in g]
        if any(not math.isfinite(x) for x in d):
            states[ind] = "unread"
        elif all(x > 0 for x in d):
            states[ind] = "rent steeper"
        elif all(x < 0 for x in d):
            states[ind] = "wage steeper"
        else:
            states[ind] = "unread"
        lo, hi = boot[0]["gap"][ind]
        parts.append(f"{INDUSTRIES[ind]} rent {g[0]['rent_same_areas'][ind]:.3f} against wage "
                     f"{g[0]['industry'][ind]:.3f}, gap {d[0]:+.3f} ({min(d):+.3f} to {max(d):+.3f}; area resamples "
                     f"{lo:+.3f} to {hi:+.3f})")
    n = sum(s == "rent steeper" for s in states.values())
    detail = "; ".join(parts) + f". Rent steeper at every knob point: {n} of {len(states)}"
    return verdict(states.values(), "rent steeper"), detail, {"states": states}


KINDS = {"B144-A6": "instrument", "B144-A7": "own_reading", "B144-A8": "own_reading", "B144-A9": "own_reading"}
STATEMENTS = {
    "B144-A6": "The two official sources parse, join, and say what their columns are.",
    "B144-A7": "Inside one country the rent of a position responds to the area's average wage more than one "
               "for one.",
    "B144-A8": "The wage in industries that supply local services responds to the area's average wage less "
               "than one for one.",
    "B144-A9": "Rent responds to the area's average wage more than the wage of those who supply local "
               "services does.",
}


def r4(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 4)
    if isinstance(x, dict):
        return {k: r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data):
    g = grid(data)
    boot = bootstrap(table(data, YEARS[0], BASE[0]))
    res = {"B144-A6": c_a6(data), "B144-A7": c_a7(g, boot), "B144-A8": c_a8(g, boot), "B144-A9": c_a9(g, boot)}
    return res, g, boot


def record_of(res, g, boot):
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d}
                     for n, (p, d, _) in res.items()],
        "mapping": {"states": STATES, "states_of_the_gap": STATES_GAP,
                    "verdict": "true when every state is on the stated side, false when none is and none is "
                               "unread, null otherwise"},
        "objects": {"knob_grid": r4(g), "area_resamples": r4(boot),
                    "states": {n: o for n, (_, _, o) in res.items() if n != "B144-A6"},
                    "industries": INDUSTRIES},
        "config": {"raw": "data/raw/b144/us", "fetched_by": "experiments/b144_fetch.py --only us",
                   "knobs": {"base": list(BASE), "year": list(YEARS), "weight": list(WEIGHT)},
                   "n_boot": N_BOOT, "seeds": list(SEEDS), "lines": LINES},
    }


# ----------------------------------------------------------------------------- selftest
def toy(rent_e: float, serve_e: float, n: int = 320, seed: int = 1) -> dict:
    """Areas whose rent and service wages respond to the average wage by planted amounts."""
    rng = np.random.default_rng(seed)
    w = rng.normal(7.0, 0.2, size=n)
    par = {y: {ln: {} for ln in LINES} for y in YEARS}
    cells, us = {}, {}
    for y in YEARS:
        for ln in LINES:
            us[(y, ln)] = 100.0
        for i in range(n):
            code = f"{10000 + 10 * i:05d}"
            key = "C" + code[:4]
            e = math.exp(w[i])
            emp = float(rng.integers(20_000, 2_000_000))
            cells[(y, "every employer", key)] = (e, emp)
            cells[(y, "private employers", key)] = (e * 0.99, emp * 0.85)
            for ln in LINES:
                resp = rent_e if ln == "3" else 0.2
                par[y][ln][code] = 100.0 * math.exp(resp * (w[i] - 7.0) + rng.normal(0, 0.03))
            for ind in INDUSTRIES:
                cells[(y, ind, key)] = (math.exp(6.0 + serve_e * (w[i] - 7.0) + rng.normal(0, 0.03)), emp / 100)
    return {"parities": {"values": par, "us": us, "definition": f"... {SENTENCE}. ..."},
            "wages": {"cells": cells, "identity": [1.0] * n}}


def selftest() -> None:
    assert abs(slope([0, 1, 2, 3], [1, 3, 5, 7]) - 2.0) < 1e-12
    assert abs(slope([0, 1, 2], [0, 1, 5], [1, 1, 0]) - 1.0) < 1e-12, "a weight of zero takes the point out"
    assert side([1.2, 1.1]) == "above one" and side([0.8, 0.9]) == "below one"
    assert side([1.2, 0.9]) == "unread" and side([math.nan]) == "unread" and side([]) == "unread"
    assert verdict(["above one", "above one"], "above one") is True
    assert verdict(["below one", "below one"], "above one") is False
    assert verdict(["above one", "unread"], "above one") is None
    assert verdict(["above one", "below one"], "above one") is None
    assert set(STATES) == {"above one", "below one", "unread"}

    d = toy(1.3, 0.6)
    res, g, boot = run(d)
    assert res["B144-A6"][0], res["B144-A6"][1]
    assert abs(g[0]["parities"]["housing"] - 1.3) < 0.05 and abs(g[0]["industry"]["8121"] - 0.6) < 0.05
    assert res["B144-A7"][0] is True and res["B144-A8"][0] is True and res["B144-A9"][0] is True
    flat = run(toy(0.7, 1.2))[0]
    assert flat["B144-A7"][0] is False, "A7 must fail where rent responds less than one for one"
    assert flat["B144-A8"][0] is False, "A8 must fail where service wages respond more than one for one"
    assert flat["B144-A9"][0] is False, "A9 must fail where rent trails the service wage"
    assert verdict(["rent steeper", "unread"], "rent steeper") is None
    straddle = [{"parities": {"housing": v, "goods": 0.1, "other services": 0.1, "utilities": 0.1, "all items": 0.1},
                 "areas": 3} for v in (1.02, 0.98)]
    assert c_a7(straddle, [{"rent": [0.9, 1.1]}])[0] is None, "a slope on both sides of one is unread, not a pass"

    # A6: the United States row, the definition sentence, the wage identity, the join
    for change in ("us", "definition", "identity", "join"):
        bad = toy(1.3, 0.6)
        if change == "us":
            bad["parities"]["us"][(YEARS[0], "1")] = 97.0
        elif change == "definition":
            bad["parities"]["definition"] = "nothing about tenants"
        elif change == "identity":
            bad["wages"]["identity"] = [1.2] * 10
        else:
            bad["wages"]["cells"] = {k: v for k, v in bad["wages"]["cells"].items() if k[1] != BASE[0]}
        assert not c_a6(bad)[0], f"A6 must fail on {change}"
    print("selftest ok: planted responses come back, every flag fails on its planted input, a response of "
          "one is unread")


def main() -> int:
    data = load()
    res, g, boot = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    OUT.write_text(json.dumps(record_of(res, g, boot), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-A6"][0] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
