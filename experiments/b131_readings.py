"""B131: FISIM, one scalar reference rate cutting a class-value gap into two "services".

Reads what `b131_fetch.py` put in data/raw/b131/ and the MIR overnight rates and ECB key rates
on disk from B128. Nothing is fetched here.

FISIM by user sector is read off the national accounts themselves (ESA 2010 14.11):
  deposits:  D41 received after allocation  - D41G received before allocation
  loans:     D41G paid before allocation    - D41 paid after allocation

Criteria (each has a planted error in --selftest that must make it fail):
  B131-1  instrument    FISIM derived for every cell where both items exist; margins over stocks
                        outside +-10 points are listed by name
  B131-2  known_answer  euro area households, (deposit + loan) FISIM / B6G in 2022 and 2023, against
                        the ECB box (1.7 % and 2.1 %, first halves); read through when both round
                        within one unit of the ECB's printed digit (0.1 point) and the change has
                        the ECB's sign
  B131-3  rival         the rival's premise (ESA 14.01: the gap to the one reference rate is an
                        implicit fee paid) entails FISIM >= 0 in every cell. Scored on the cells
                        where the framework says the opposite: euro-area members, deposit side in
                        years the ECB deposit facility rate averaged below zero, loan side in 2023
                        and later. PASS means the rival is wrong in at least one such cell above the
                        floor (1 million euro, the publication unit)
  B131-4  own_reading   where the negatives fall: every negative above the floor by side, sector and
                        era (DFR below zero / tightening from 2023 / other)
  B131-5  own_reading   the cut point: household deposit FISIM, loan FISIM and their sum, 2021 and
                        2023, per country; change in the sum against the two changes
  B131-6  own_reading   where it goes: household deposit FISIM as a share of P3 and of GDP, and the
                        2021 -> 2023 change of that deposit FISIM as a share of GDP. The change is a
                        size, not the GDP effect: household producers' use is intermediate and
                        imports are netted out. Imports of FISIM (P72F, rest of the world) are
                        printed per country beside the change, and their 2023 level as a share of
                        it. P72F sums both sides and every sector, and a side can be negative
                        (LT and HR print negative totals), so it does not cap the imported part of
                        household deposit FISIM and no floor is drawn from it. The euro area has
                        no published P72F
  B131-8  own_reading   the feasible band for one shared scalar (highest sector deposit rate,
                        lowest sector loan rate; deposit rates weighted over overnight, agreed and
                        notice deposits by BSI month-end stocks), the office's reference rate implied
                        four ways, and where every negative year falls against the band
  B131-7  instrument    with MIR outstanding rates: sign of (DFR - composite deposit rate) and of
                        (loan rate - DFR) against the sign of FISIM, euro-area member years. DFR is
                        a proxy for the internal reference rate (14.09), so this checks the
                        instrument and is not a reading

Run from the repo root:
    python experiments/b131_readings.py
    python experiments/b131_readings.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b131"
B128 = ROOT / "data" / "raw" / "b128"
OUT = ROOT / "results" / "b131_readings.json"
FLOOR = 1.0          # million euro, the publication unit of D41 and D41G
BIG = 100.0          # a second count, far above the floor
ECB_BOX = {2022: 1.7, 2023: 2.1}
ECB_DIGIT = 0.1
# first full calendar year inside the euro area (Eurostat geo codes)
EURO_FROM = {"AT": 1999, "BE": 1999, "DE": 1999, "ES": 1999, "FI": 1999, "FR": 1999, "IE": 1999,
             "IT": 1999, "LU": 1999, "NL": 1999, "PT": 1999, "EL": 2001, "SI": 2007, "CY": 2008,
             "MT": 2008, "SK": 2009, "EE": 2011, "LV": 2014, "LT": 2015, "HR": 2023}
MIR_GEO = {"GR": "EL"}
AGG = {"EA21", "EU27_2020", "EA20", "EA19", "EU28"}
SIDES = [("S14_S15", "dep"), ("S14_S15", "loan"), ("S11", "dep"), ("S11", "loan")]


# ---------- loading ----------

def load_eurostat(name: str) -> dict:
    d = json.loads((RAW / name).read_text(encoding="utf-8"))
    ids, size = d["id"], d["size"]
    inv = {k: {i: v for v, i in d["dimension"][k]["category"]["index"].items()} for k in ids}
    out = {}
    for flat, v in d["value"].items():
        f, pos = int(flat), {}
        for k, s in zip(reversed(ids), reversed(size)):
            pos[k] = inv[k][f % s]
            f //= s
        key = tuple(pos[k] for k in ids if k not in ("freq", "unit", "time")) + (int(pos["time"]),)
        out[key] = float(v)
    return out


def dfr_annual() -> dict[int, float]:
    """Day-weighted annual mean of the ECB deposit facility rate from its dated levels."""
    fm = pd.read_csv(B128 / "fm_keyrates.csv", usecols=["KEY", "TIME_PERIOD", "OBS_VALUE"])
    lev = fm[fm.KEY.str.contains(r"\.DFR\.LEV$")].sort_values("TIME_PERIOD")
    steps = [(date.fromisoformat(t), float(v)) for t, v in zip(lev.TIME_PERIOD, lev.OBS_VALUE)]
    out = {}
    for y in range(1999, 2026):
        tot, days = 0.0, 0
        d0 = date(y, 1, 1)
        for i in range(365 + (y % 4 == 0)):
            d = date.fromordinal(d0.toordinal() + i)
            cur = [v for t, v in steps if t <= d]
            if cur:
                tot += cur[-1]
                days += 1
        if days:
            out[y] = tot / days
    return out


def mir_annual() -> dict:
    """Annual mean of monthly MIR rates: (geo, item, sector) -> {year: rate}. A year counts only
    with twelve distinct months that each carry a number; a row with an empty value is not a month."""
    rows = []
    o = pd.read_csv(RAW / "mir_outstanding.csv",
                    usecols=["REF_AREA", "BS_ITEM", "BS_COUNT_SECTOR", "TIME_PERIOD", "OBS_VALUE"])
    rows.append(o)
    for sec in ("2240", "2250"):
        n = pd.read_csv(B128 / f"mir_B_L21_A_R_A_{sec}_EUR_N.csv",
                        usecols=["REF_AREA", "BS_ITEM", "BS_COUNT_SECTOR", "TIME_PERIOD", "OBS_VALUE"])
        rows.append(n)
    m = pd.concat(rows)
    m["year"] = m.TIME_PERIOD.str[:4].astype(int)
    m["geo"] = m.REF_AREA.map(lambda g: MIR_GEO.get(g, g))
    out = defaultdict(dict)
    for (g, it, s, y), grp in m.groupby(["geo", "BS_ITEM", "BS_COUNT_SECTOR", "year"]):
        if full_year(grp):
            out[(g, it, str(s))][y] = float(grp.OBS_VALUE.mean())
    return out


def full_year(grp) -> bool:
    """Twelve rows, twelve distinct months, every value a finite number."""
    v = pd.to_numeric(grp.OBS_VALUE, errors="coerce")
    return len(grp) == 12 and grp.TIME_PERIOD.nunique() == 12 and bool(np.isfinite(v).all())


def bsi_annual() -> dict:
    """(geo, item, sector, year) -> mean of the twelve month-end stocks, EUR millions."""
    b = pd.read_csv(RAW / "bsi_stocks.csv",
                    usecols=["REF_AREA", "BS_ITEM", "BS_COUNT_SECTOR", "TIME_PERIOD", "OBS_VALUE"]).dropna()
    b["year"] = b.TIME_PERIOD.str[:4].astype(int)
    b["geo"] = b.REF_AREA.map(lambda g: MIR_GEO.get(g, g))
    return {(g, it, str(s), y): float(grp.OBS_VALUE.mean())
            for (g, it, s, y), grp in b.groupby(["geo", "BS_ITEM", "BS_COUNT_SECTOR", "year"])
            if full_year(grp)}


def notice_annual() -> dict:
    """(geo, year) -> annual mean of the household notice-deposit rate."""
    n = pd.read_csv(RAW / "mir_notice.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]).dropna()
    n["year"] = n.TIME_PERIOD.str[:4].astype(int)
    n["geo"] = n.REF_AREA.map(lambda g: MIR_GEO.get(g, g))
    return {(g, y): float(grp.OBS_VALUE.mean()) for (g, y), grp in n.groupby(["geo", "year"])
            if full_year(grp)}


def load_all() -> dict:
    return {"d41": load_eurostat("nasa_10_nf_tr_d41.json"),
            "bs": load_eurostat("nasa_10_f_bs_dep_loans.json"),
            "hh": load_eurostat("nasa_10_nf_tr_b6g_p3.json"),
            "s1": load_eurostat("nasa_10_nf_tr_s1.json"),
            "trade": load_eurostat("nasa_10_nf_tr_fisim_trade.json"),
            "dfr": dfr_annual(), "mir": mir_annual(),
            "bsi": bsi_annual(), "r23": notice_annual()}


# ---------- objects ----------

def fisim(d41: dict) -> dict:
    """(geo, sector, side, year) -> FISIM, million euro; None where an item is missing."""
    out = {}
    cells = {(g, s, y) for (dr, it, s, g, y) in d41}
    for g, s, y in cells:
        a, b = d41.get(("RECV", "D41", s, g, y)), d41.get(("RECV", "D41G", s, g, y))
        out[(g, s, "dep", y)] = None if a is None or b is None else a - b
        a, b = d41.get(("PAID", "D41", s, g, y)), d41.get(("PAID", "D41G", s, g, y))
        out[(g, s, "loan", y)] = None if a is None or b is None else b - a
    return out


def stock(bs: dict, g: str, s: str, side: str, y: int):
    if side == "dep":
        a, b = bs.get(("NCO", s, "ASS", "F22", g, y)), bs.get(("NCO", s, "ASS", "F29", g, y))
        return None if a is None or b is None else a + b
    return bs.get(("NCO", s, "LIAB", "F4", g, y))


def era(y: int, dfr: dict) -> str:
    if dfr.get(y, 1.0) < 0:
        return "DFR below zero"
    if y >= 2023:
        return "tightening from 2023"
    return "other"


def in_rival_cell(g: str, side: str, y: int, dfr: dict) -> bool:
    if g not in EURO_FROM or y < EURO_FROM[g]:
        return False
    if side == "dep":
        return dfr.get(y, 1.0) < 0
    return y >= 2023


# ---------- criteria ----------

def c1(data, F):
    missing = [k for k, v in F.items() if v is None and k[0] not in AGG]
    have = [k for k, v in F.items() if v is not None and k[0] not in AGG]
    out_of_range = []
    for (g, s, side, y) in have:
        st = stock(data["bs"], g, s, side, y)
        if st and st > 0:
            m = 100 * F[(g, s, side, y)] / st
            if abs(m) > 10:
                out_of_range.append(f"{g} {s} {side} {y}: {m:.1f} points")
    finite = all(np.isfinite(F[k]) for k in have)
    passed = bool(have) and finite
    detail = (f"{len(have)} cells derived, {len(missing)} with an item missing (not derived); "
              f"margins over year-end stocks outside +-10 points: {len(out_of_range)}")
    return passed, detail, {"derived": len(have), "missing_items": len(missing),
                            "margin_outliers": sorted(out_of_range)}


def c2(data, F):
    b6 = {y: v for (dr, it, s, g, y), v in data["hh"].items() if g == "EA21" and it == "B6G"}
    got = {}
    for y in ECB_BOX:
        dep, loan = F.get(("EA21", "S14_S15", "dep", y)), F.get(("EA21", "S14_S15", "loan", y))
        got[y] = None if dep is None or loan is None or y not in b6 else 100 * (dep + loan) / b6[y]
    ok = all(v is not None and abs(v - ECB_BOX[y]) <= ECB_DIGIT + 1e-9 for y, v in got.items())
    ys = sorted(ECB_BOX)
    ok = ok and np.sign(got[ys[1]] - got[ys[0]]) == np.sign(ECB_BOX[ys[1]] - ECB_BOX[ys[0]])
    detail = "; ".join(f"{y}: annual {got[y]:.2f} % against the box's {ECB_BOX[y]} % (first half)"
                       for y in ys if got[y] is not None)
    return bool(ok), detail, {str(y): (None if v is None else round(v, 4)) for y, v in got.items()}


def c3(data, F):
    cells, neg, big = defaultdict(int), defaultdict(list), defaultdict(int)
    for (g, s, side, y), v in F.items():
        if v is None or not in_rival_cell(g, side, y, data["dfr"]):
            continue
        cells[(s, side)] += 1
        if v < -FLOOR:
            neg[(s, side)].append(f"{g} {y}: {v:,.0f}")
            if v < -BIG:
                big[(s, side)] += 1
    n_neg = sum(len(v) for v in neg.values())
    n_cells = sum(cells.values())
    passed = n_neg > 0
    per = {f"{s} {side}": {"cells": cells[(s, side)], "negative_above_floor": len(neg[(s, side)]),
                           "below_minus_100m": big[(s, side)], "list": sorted(neg[(s, side)])}
           for s, side in SIDES}
    detail = (f"rival premise: the gap to the single reference rate is an implicit fee paid, so "
              f"FISIM >= 0 in every cell. In the {n_cells} framework cells, {n_neg} are negative "
              f"beyond the 1 million floor. " +
              "; ".join(f"{k}: {v['negative_above_floor']}/{v['cells']}" for k, v in per.items()))
    return passed, detail, {"per_cell": per, "cells": n_cells, "negative": n_neg}


def c4(data, F):
    tab = defaultdict(int)
    tot = defaultdict(int)
    for (g, s, side, y), v in F.items():
        if v is None or g in AGG:
            continue
        e = era(y, data["dfr"])
        tot[(s, side, e)] += 1
        if v < -FLOOR:
            tab[(s, side, e)] += 1
    rows = {f"{s} {side} | {e}": f"{tab[(s, side, e)]}/{tot[(s, side, e)]}"
            for s, side in SIDES for e in ("DFR below zero", "tightening from 2023", "other")}
    passed = sum(tot.values()) > 0 and set(tab) <= set(tot)
    return passed, "negative country-years by era: " + "; ".join(f"{k} {v}" for k, v in rows.items()), rows


def c5(data, F):
    rows = {}
    for g in sorted({k[0] for k in F}):
        vals = {(side, y): F.get((g, "S14_S15", side, y)) for side in ("dep", "loan") for y in (2021, 2023)}
        if any(v is None for v in vals.values()):
            continue
        dd = vals[("dep", 2023)] - vals[("dep", 2021)]
        dl = vals[("loan", 2023)] - vals[("loan", 2021)]
        moved = abs(dd) + abs(dl)
        rows[g] = {"dep_2021": vals[("dep", 2021)], "dep_2023": vals[("dep", 2023)],
                   "loan_2021": vals[("loan", 2021)], "loan_2023": vals[("loan", 2023)],
                   "d_sum": dd + dl, "d_sum_over_moved": None if moved == 0 else round((dd + dl) / moved, 4)}
    passed = "EA21" in rows and len(rows) > 1
    ea = rows.get("EA21", {})
    detail = (f"{len(rows)} areas. Euro area households: deposit FISIM {ea.get('dep_2021', 0):,.0f} -> "
              f"{ea.get('dep_2023', 0):,.0f}, loan FISIM {ea.get('loan_2021', 0):,.0f} -> "
              f"{ea.get('loan_2023', 0):,.0f} million; the sum moved {ea.get('d_sum_over_moved')} of what "
              f"the two parts moved")
    return passed, detail, rows


def c6(data, F):
    gdp = {(g, y): v for (dr, it, s, g, y), v in data["s1"].items() if it == "B1GQ"}
    p3 = {(g, y): v for (dr, it, s, g, y), v in data["hh"].items() if it == "P3"}
    # exports of FISIM sit under S2 paid, imports under S2 received
    exports = {(g, y): v for (dr, it, s, g, y), v in data["trade"].items() if it == "P62F" and dr == "PAID"}
    imports = {(g, y): v for (dr, it, s, g, y), v in data["trade"].items() if it == "P72F" and dr == "RECV"}
    rows = {}
    for g in sorted({k[0] for k in F}):
        r = {}
        for y in (2019, 2021, 2023):
            dep = F.get((g, "S14_S15", "dep", y))
            if dep is None or (g, y) not in gdp or (g, y) not in p3:
                continue
            r[str(y)] = {"dep_over_P3_pct": round(100 * dep / p3[(g, y)], 3),
                         "dep_over_GDP_pct": round(100 * dep / gdp[(g, y)], 3),
                         "fisim_exports": exports.get((g, y)), "fisim_imports": imports.get((g, y))}
        if "2021" in r and "2023" in r:
            d = F[(g, "S14_S15", "dep", 2023)] - F[(g, "S14_S15", "dep", 2021)]
            r["change_2021_2023"] = d
            r["change_2021_2023_over_GDP2023_pct"] = round(100 * d / gdp[(g, 2023)], 3)
            imp = imports.get((g, 2023))
            if imp is not None and d > 0:
                r["imports2023_over_change"] = round(imp / d, 3)
        if r:
            rows[g] = r
    ratios = {g: r["imports2023_over_change"] for g, r in rows.items()
              if "imports2023_over_change" in r and g not in AGG}
    negative = sorted(g for g, r in rows.items() if (r.get("2023", {}).get("fisim_imports") or 0) < 0)
    passed = ("EA21" in rows and "change_2021_2023_over_GDP2023_pct" in rows["EA21"] and bool(ratios)
              and all(np.isfinite(v) for v in ratios.values()))
    ea = rows.get("EA21", {})
    show = "; ".join(f"{g} {ratios[g]}" for g in ("DE", "FR", "NL", "IT") if g in ratios)
    detail = (f"euro area: household deposit FISIM {ea.get('2021', {}).get('dep_over_P3_pct')} % of "
              f"P3 in 2021, {ea.get('2023', {}).get('dep_over_P3_pct')} % in 2023; the change is "
              f"{ea.get('change_2021_2023_over_GDP2023_pct')} % of 2023 GDP in size (no euro-area imports of "
              f"FISIM are published). Whole-economy FISIM imports in 2023 against the change, {len(ratios)} "
              f"countries: {show}, median {np.median(list(ratios.values())) if ratios else float('nan'):.3f}; both sides and every sector "
              f"in one total, negative in {', '.join(negative) or 'none'}, so not a cap on the imported part")
    return passed, detail, rows


def c7(data, F):
    agree, disagree, evaluated, dropped = 0, 0, [], []
    mir, bs, dfr = data["mir"], data["bs"], data["dfr"]
    sec_code = {"S14_S15": "2250", "S11": "2240"}
    for (g, s, side, y), v in F.items():
        if v is None or g not in EURO_FROM or y < EURO_FROM[g] or abs(v) <= FLOOR or y not in dfr:
            continue
        sc = sec_code[s]
        if side == "dep":
            r21, r22 = mir.get((g, "L21", sc), {}).get(y), mir.get((g, "L22", sc), {}).get(y)
            a = bs.get(("NCO", s, "ASS", "F22", g, y))
            b = bs.get(("NCO", s, "ASS", "F29", g, y))
            if not _num(r21, r22, a, b) or a + b <= 0:
                dropped.append(f"{g} {s} {side} {y}")
                continue
            pred = np.sign(dfr[y] - (r21 * a + r22 * b) / (a + b))
        else:
            rl = mir.get((g, "A20", sc), {}).get(y)
            if not _num(rl):
                dropped.append(f"{g} {s} {side} {y}")
                continue
            pred = np.sign(rl - dfr[y])
        evaluated.append((g, s, side, y))
        if pred == np.sign(v):
            agree += 1
        else:
            disagree += 1
    passed = len(evaluated) > 0 and agree + disagree == len(evaluated)
    detail = (f"{len(evaluated)} euro-area member cells with every input: the sign of the DFR-based "
              f"margin agrees with the sign of FISIM in {agree}, not in {disagree}; "
              f"{len(dropped)} cells lack an input")
    return passed, detail, {"agree": agree, "disagree": disagree, "evaluated": len(evaluated),
                            "dropped": len(dropped)}


def _num(*v) -> bool:
    return all(x is not None and np.isfinite(x) for x in v)


def bands(data, F) -> list[dict]:
    """Per euro-area member year with every input: the feasible band for one shared scalar
    (highest sector deposit rate, lowest sector loan rate) and the office's reference rate
    implied four ways (each sector, each side)."""
    mir, S, r23, dfr = data["mir"], data["bsi"], data["r23"], data["dfr"]
    code = {"S14_S15": "2250", "S11": "2240"}
    rows = []
    for g in sorted(EURO_FROM):
        for y in range(2003, 2026):
            if y < EURO_FROM[g]:
                continue
            lo, hi, imp, good = [], [], {}, True
            for s in ("S14_S15", "S11"):
                c = code[s]
                r21, r22 = mir.get((g, "L21", c), {}).get(y), mir.get((g, "L22", c), {}).get(y)
                # households carry their notice rate; corporations have none, so their notice
                # stock takes the lower of their two rates (a lower deposit rate widens the band,
                # which works against a closed band)
                rn = r23.get((g, y)) if s == "S14_S15" else (min(r21, r22) if _num(r21, r22) else None)
                st = [S.get((g, k, c, y)) for k in ("L21", "L22", "L23")]
                rl, L = mir.get((g, "A20", c), {}).get(y), S.get((g, "A20", c, y))
                fd, fl = F.get((g, s, "dep", y)), F.get((g, s, "loan", y))
                if not _num(r21, r22, rn, rl, L, fd, fl, *st) or sum(st) <= 0 or L <= 0:
                    good = False
                    break
                D = sum(st)
                rd = (r21 * st[0] + r22 * st[1] + rn * st[2]) / D
                lo.append(rd)
                hi.append(rl)
                imp[f"{s} dep"] = rd + 100 * fd / D
                imp[f"{s} loan"] = rl - 100 * fl / L
            if good:
                rows.append({"geo": g, "year": y, "band_low": max(lo), "band_high": min(hi),
                             "implied": imp, "dfr": dfr.get(y)})
    return rows


def c8(data, F):
    rows = bands(data, F)
    if not rows:
        return False, "no member year has every input", {"years": 0}
    closed = [r for r in rows if r["band_high"] < r["band_low"]]
    outside = [r for r in rows if any(v < r["band_low"] or v > r["band_high"] for v in r["implied"].values())]
    spread = [max(r["implied"].values()) - min(r["implied"].values()) for r in rows]
    neg_years = [r for r in rows if any((F.get((r["geo"], s, side, r["year"])) or 0) < -FLOOR
                                        for s, side in SIDES)]
    classified = {"band closed": 0, "office scalar outside the band": 0, "office scalar inside the band": 0}
    listing = []
    for r in neg_years:
        if r in closed:
            k = "band closed"
        elif r in outside:
            k = "office scalar outside the band"
        else:
            k = "office scalar inside the band"
        classified[k] += 1
        mid = float(np.mean(list(r["implied"].values())))
        side = "below" if mid < r["band_low"] else ("above" if mid > r["band_high"] else "inside")
        cells = [f"{s} {sd} {F[(r['geo'], s, sd, r['year'])]:,.0f}" for s, sd in SIDES
                 if (F.get((r["geo"], s, sd, r["year"])) or 0) < -FLOOR]
        listing.append(f"{r['geo']} {r['year']}: band [{r['band_low']:.2f}, {r['band_high']:.2f}], "
                       f"office {mid:.2f} ({side}), DFR {r['dfr']:.2f}; " + ", ".join(cells))
    passed = bool(rows) and sum(classified.values()) == len(neg_years)
    detail = (f"{len(rows)} member years with every input; band closed in {len(closed)}; "
              f"the office's four implied rates differ by a median {np.median(spread):.2f} points "
              f"(quartiles {np.percentile(spread, 25):.2f} to {np.percentile(spread, 75):.2f}); "
              f"the office's scalar lies outside the band in {len(outside)}; of the {len(neg_years)} "
              f"years with a negative cell: " + ", ".join(f"{k} {v}" for k, v in classified.items()))
    return passed, detail, {"years": len(rows), "closed": len(closed), "outside": len(outside),
                            "spread_median": round(float(np.median(spread)), 4) if spread else None,
                            "negative_years": classified, "list": listing}


KINDS = {"B131-1": "instrument", "B131-2": "known_answer", "B131-3": "rival", "B131-4": "own_reading",
         "B131-5": "own_reading", "B131-6": "own_reading", "B131-7": "instrument",
         "B131-8": "own_reading"}
FUNCS = {"B131-1": c1, "B131-2": c2, "B131-3": c3, "B131-4": c4, "B131-5": c5, "B131-6": c6,
         "B131-7": c7, "B131-8": c8}


def build(data) -> dict:
    F = fisim(data["d41"])
    return {name: fn(data, F) for name, fn in FUNCS.items()}


def selftest() -> None:
    data = load_all()
    base = build(data)
    assert all(v[0] for v in base.values()), {k: v[1] for k, v in base.items() if not v[0]}

    bad = copy.deepcopy(data)          # B131-1: a derived value that is not a number
    k = next(k for k in bad["d41"] if k[:2] == ("RECV", "D41") and k[3] == "BE")
    bad["d41"][k] = float("nan")
    assert not c1(bad, fisim(bad["d41"]))[0], "B131-1 must catch a NaN"

    bad = copy.deepcopy(data)          # B131-2: the euro area deposit side doubled in 2023
    k = ("RECV", "D41", "S14_S15", "EA21", 2023)
    bad["d41"][k] += 100_000
    assert not c2(bad, fisim(bad["d41"]))[0], "B131-2 must catch a wrong euro-area figure"

    bad = copy.deepcopy(data)          # B131-3: every rival cell made non-negative
    F = fisim(bad["d41"])
    F = {k: (abs(v) if v is not None else None) for k, v in F.items()}
    assert not c3(bad, F)[0], "B131-3 must not read the rival wrong when no cell is negative"

    assert not c4(data, {})[0], "B131-4 must fail on an empty object"
    F = fisim(data["d41"])
    assert not c5(data, {k: v for k, v in F.items() if k[0] != "EA21"})[0], "B131-5 needs the euro area"
    assert not c6(data, {k: v for k, v in F.items() if k[0] != "EA21"})[0], "B131-6 needs the euro area"
    assert not c6(dict(data, trade={}), F)[0], "B131-6 needs the imports it prints beside the change"
    de = c6(data, F)[2]["DE"]
    want = data["trade"][("RECV", "P72F", "S2", "DE", 2023)] / (
        F[("DE", "S14_S15", "dep", 2023)] - F[("DE", "S14_S15", "dep", 2021)])
    assert abs(de["imports2023_over_change"] - want) < 1e-3, "the ratio is 2023 imports (S2 received) over the change"
    swapped = dict(data, trade={(("RECV" if k[0] == "PAID" else "PAID"),) + k[1:]: v for k, v in data["trade"].items()})
    assert c6(swapped, F)[2]["DE"]["2023"]["fisim_imports"] is None, "imports are read under S2 received only"
    bad = copy.deepcopy(data)
    bad["mir"] = {}
    assert not c7(bad, F)[0], "B131-7 must fail with no rates to compare"
    bad = copy.deepcopy(data)
    bad["bsi"] = {}
    assert not c8(bad, F)[0], "B131-8 must fail with no stocks"
    # a band made to close must be counted as closed, not silently as outside
    rows = bands(data, F)
    r0 = rows[0]
    bad = copy.deepcopy(data)
    code = "2250"
    for y in [r0["year"]]:
        bad["mir"][(r0["geo"], "A20", code)][y] = -50.0
    assert bands(bad, F)[0]["band_high"] < bands(bad, F)[0]["band_low"], "a planted closed band must read closed"
    # a year is twelve distinct months with a number each: an empty month, or a month twice, is not one
    months = [f"2020-{m:02d}" for m in range(1, 13)]
    year = pd.DataFrame({"TIME_PERIOD": months, "OBS_VALUE": [1.0] * 12})
    assert full_year(year), "twelve numbered months must count as a year"
    holed = year.copy()
    holed.loc[3, "OBS_VALUE"] = float("nan")
    assert not full_year(holed), "a month without a number must not count"
    twice = year.copy()
    twice.loc[11, "TIME_PERIOD"] = months[0]
    assert not full_year(twice), "a month counted twice must not make a year"
    # B131-7: a rate that is not a number is a missing input, not a disagreement
    before = c7(data, F)[2]
    for key in (("DE", "A20", "2250"), ("DE", "L21", "2250")):      # the loan side, then the deposit side
        bad = copy.deepcopy(data)
        bad["mir"][key] = {y: float("nan") for y in bad["mir"][key]}
        after = c7(bad, F)[2]
        assert after["dropped"] > before["dropped"] and after["disagree"] <= before["disagree"] \
            and after["evaluated"] + after["dropped"] == before["evaluated"] + before["dropped"], \
            f"B131-7 must drop a cell whose rate is not a number ({key[1]})"
    print("selftest ok: all eight flags pass on the data and each fails on its planted error")


def main() -> int:
    data = load_all()
    res = build(data)
    crit = []
    for name, (passed, detail, obj) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
        c = {"name": name, "kind": KINDS[name], "passed": passed, "detail": detail}
        if name == "B131-3":
            c.update({"grid": "B" if passed else "unread",
                      "grid_note": ("cells where FISIM is not negative are unread on the framework "
                                    "side: without the office's reference rate the framework's sign "
                                    "is not computed there"),
                      "rival_shape": "one-sided inequality",
                      "rival_premise": ("ESA 2010 14.01 and 14.09: one reference rate for every user "
                                        "sector, the gap to it is an implicit fee paid for a service"),
                      "rival_entailment": "a fee paid for a service is not negative, so FISIM >= 0 "
                                          "in every sector, side and year",
                      "cite": ("ESA 2010 14.01: 'the rate at which both lender and borrower would be "
                               "happy to strike a deal' ... 'the sum of the two implicit fees paid'"),
                      "rival_holds_share": round(1 - obj["negative"] / obj["cells"], 4) if obj["cells"] else None})
            if not passed:
                c["passed"] = None
        crit.append(c)
    record = {"stage": "B131", "criteria": crit,
              "objects": {name: obj for name, (_, _, obj) in res.items()},
              "dfr_annual_mean": {str(y): round(v, 4) for y, v in data["dfr"].items()},
              "config": {"floor_million_eur": FLOOR, "big_million_eur": BIG, "ecb_box": ECB_BOX,
                         "euro_from": EURO_FROM, "rival_cells": "euro members; deposit side DFR "
                         "annual mean < 0; loan side 2023 and later"}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] is not False for c in crit if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
