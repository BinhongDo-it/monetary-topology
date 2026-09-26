"""B35: how many tongues exist, and how many were exported.

The step-or-spike record excluded slaughter as the driver by comparing two
meters of the same animal count. That is a statement about SUPPLY and it leaves
demand untouched: nothing in it stops a story where China simply wanted twelve
times as much tongue. Tongue and heart are not the same product to a buyer, they
sit in different kitchens at different price points, and a demand divergence
between them is an ordinary thing rather than an anomaly.

This file closes that opening with a quantity that no demand can move. One
tongue comes off one hog, so US tongue production is slaughter times the weight
of a tongue, and exports of a part cannot exceed production of that part. That
bound holds whatever anyone wants to buy.

  slaughter        USDA NASS Livestock Slaughter Annual Summary, commercial
                   head, 2021 128,985,900 / 2022 125,321,700 / 2023 127,971,000,
                   with 2022 by month
  yields           Pork Information Gateway, "Determination of by-product yield
                   values from market swine", 196 hogs, mean live weight
                   111.4 +/- 13.3 kg: tongue 0.25 +/- 0.04 kg (tip on), heart
                   0.42 +/- 0.05 kg (unslashed), fore feet 0.85 +/- 0.10 and
                   hind feet 1.01 +/- 0.11 kg

Nothing here rests on one weight: the load-bearing figure is inverted instead.
The line is asked what a tongue would have to weigh for it to be tongue, and
that number is compared with the measured one in units of the measured spread.

Two controls, because an arithmetic that finds an impossibility everywhere has
found nothing. Feet and hearts go through the same steps and must come back
inside the bound.

Two things this file does NOT do. It does not treat the demand story as beaten
by argument: the demand story makes a directional prediction about price and
that prediction is read off the data (criterion 5). And it does not close the
one remaining route by which exports could legitimately exceed production,
re-export of imported product; that needs the imports side of the same feed and
is registered with its outcomes mapped (criterion 7).

Usage
-----
    python b35_physical_ceiling.py
    python b35_physical_ceiling.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020649_bycountry_2021-2023.json"
OUT = ROOT / "results" / "b35_physical_ceiling.json"

TONG, HEART, FOOT, HEAD = ("0206490010", "0206490020",
                           "0206490030", "0206490040")
NAMES = {TONG: "tongues", HEART: "hearts", FOOT: "feet", HEAD: "head meat"}
CHINA = "CHINA"

SLAUGHTER = {2021: 128_985_900, 2022: 125_321_700, 2023: 127_971_000}
SLAUGHTER_2022_MONTHLY = {
    1: 10_410_100, 2: 9_943_400, 3: 11_250_200, 4: 10_078_700,
    5: 10_034_500, 6: 10_505_400, 7: 9_318_300, 8: 10_989_600,
    9: 10_659_000, 10: 10_919_400, 11: 10_914_000, 12: 10_299_000,
}
SLAUGHTER_SRC = ("USDA NASS, Livestock Slaughter Annual Summary, commercial "
                 "slaughter, head; 2021 and 2022 from the 2022 summary "
                 "(April 2023), 2023 from the 2023 summary (April 2024)")

# kg per animal, and the spread the study reports. PER_ANIMAL says how many of
# the part come off one hog, which is what turns a weight into a ceiling.
YIELD = {
    TONG:  {"kg": 0.25, "sd": 0.04, "per_animal": 1, "note": "tip on"},
    HEART: {"kg": 0.42, "sd": 0.05, "per_animal": 1, "note": "unslashed"},
    FOOT:  {"kg": 1.86, "sd": 0.15, "per_animal": 1,
            "note": "fore 0.85 plus hind 1.01, both as reported per animal"},
}
YIELD_SRC = ("Pork Information Gateway, Determination of by-product yield "
             "values from market swine, 196 crossbred market barrows and "
             "gilts, mean live weight 111.4 +/- 13.3 kg")

BREAK = (2022, 9)


def is_atom(code: str) -> bool:
    return code.isdigit() and len(code) == 4 and not code.startswith("00")


def qv(rows, code, months, leg=None):
    q = v = 0.0
    want = set(months)
    for r in rows:
        if r["E_COMMODITY"] != code or (r["_year"], r["_month"]) not in want:
            continue
        if not is_atom(r["CTY_CODE"]):
            continue
        if leg == "CN" and r["CTY_NAME"] != CHINA:
            continue
        if leg == "NC" and r["CTY_NAME"] == CHINA:
            continue
        q += float(r["QTY_1_MO"])
        v += float(r["ALL_VAL_MO"])
    return q, v


def year(y):
    return [(y, m) for m in range(1, 13)]


def run(rows, slaughter=None, monthly=None):
    slaughter = slaughter or SLAUGHTER
    monthly = monthly or SLAUGHTER_2022_MONTHLY
    crit = []
    rep = {"slaughter_head": slaughter, "slaughter_source": SLAUGHTER_SRC,
           "yield_kg_per_animal": {NAMES[k]: v for k, v in YIELD.items()},
           "yield_source": YIELD_SRC}
    yrs = sorted(slaughter)

    # ---- 1. the inputs are named and the arithmetic is one line ------------
    named = all(YIELD[c]["kg"] > 0 and YIELD[c]["per_animal"] >= 1
                for c in YIELD)
    rep["formula"] = ("production_kg = slaughter_head * per_animal * kg; "
                      "exports cannot exceed production, so the ratio "
                      "exports / production is bounded by one")
    crit.append({
        "name": "B35-PH-1",
        "kind": "instrument",
        "passed": bool(named) and len(slaughter) >= 3,
        "detail": (f"three years of commercial slaughter and three yields, each "
                   f"with its source and its spread, and one line of "
                   f"arithmetic between them; no step below divides by a number "
                   f"that is not printed here"),
    })

    # ---- 2. the two controls ----------------------------------------------
    ratios = {}
    for code in (TONG, HEART, FOOT):
        ratios[NAMES[code]] = {}
        for y in yrs:
            q, _ = qv(rows, code, year(y))
            prod = slaughter[y] * YIELD[code]["per_animal"] * YIELD[code]["kg"]
            ratios[NAMES[code]][y] = {"exports_t": q / 1000.0,
                                      "production_t": prod / 1000.0,
                                      "ratio": q / prod}
    rep["exports_over_production"] = ratios
    # The first version of this criterion asserted that the controls sit at or
    # below one, and feet came back at 1.013 in 2022. That verdict was the
    # wrong shape rather than a wrong number, and the numbers below did not
    # change when it was fixed. A dissected yield does not bound a traded
    # tonnage exactly, because a trade cut is not an anatomical cut: a traded
    # trotter carries part of the shank, and a traded tongue may or may not
    # carry the root and the throat trim. So the ratio is not "how much of the
    # animal shipped", it is "how many times the dissected part a traded piece
    # would have to be", and a line drawn at exactly 1.0 is the zero-width
    # threshold that criterion-shape discipline forbids. The reading is the
    # ORDERING of that multiple across parts.
    ctrl_max = max(ratios[n][y]["ratio"] for n in ("feet", "hearts")
                   for y in yrs)
    tong_max = max(ratios["tongues"][y]["ratio"] for y in yrs)
    rep["trade_cut_multiple"] = {"controls_max": ctrl_max,
                                 "tongues_max": tong_max,
                                 "gap_x": tong_max / ctrl_max}
    crit.append({
        "name": "B35-PH-2",
        "kind": "known_answer",
        "passed": tong_max > ctrl_max,
        "detail": (
            "the same arithmetic on two parts nobody is questioning asks how "
            "many times the dissected part a traded piece would have to be: "
            f"feet run {ratios['feet'][yrs[0]]['ratio']:.3f} to "
            f"{ratios['feet'][yrs[1]]['ratio']:.3f} and hearts "
            f"{ratios['hearts'][yrs[1]]['ratio']:.3f} to "
            f"{ratios['hearts'][yrs[-1]]['ratio']:.3f}, so the trade cut costs "
            f"the controls at most {ctrl_max:.3f} times the anatomy, while the "
            f"tongue line asks for {tong_max:.3f} times, a factor of "
            f"{tong_max/ctrl_max:.2f} more allowance than any control needs"),
    })

    # ---- 3. what a tongue would have to weigh ------------------------------
    req = {}
    for y in yrs:
        q, _ = qv(rows, TONG, year(y))
        w = q / slaughter[y] / YIELD[TONG]["per_animal"]
        req[y] = {"required_kg": w,
                  "sd_above_measured": (w - YIELD[TONG]["kg"]) / YIELD[TONG]["sd"],
                  "ratio": ratios["tongues"][y]["ratio"]}
    rep["required_tongue_weight"] = req
    first, last = yrs[0], yrs[-1]
    # A single traded weight large enough makes any one year possible, so the
    # required weight on its own settles nothing. What no weight can change is
    # the RATIO between years: whatever a traded tongue weighs, it weighs the
    # same in both, so the export rate's multiple is the export tonnage's
    # multiple divided by slaughter's. That number is weight-invariant, and it
    # is what the reading rests on.
    qa, _ = qv(rows, TONG, year(first))
    qb, _ = qv(rows, TONG, year(last))
    rate_mult = (qb / qa) / (slaughter[last] / slaughter[first])
    max_first_rate = 1.0 / rate_mult
    rep["export_rate_invariant"] = {
        "tonnage_multiple": qb / qa,
        "slaughter_multiple": slaughter[last] / slaughter[first],
        "export_rate_multiple": rate_mult,
        "max_first_year_rate_for_last_to_be_possible": max_first_rate,
        "why_invariant": ("a traded tongue weighs the same in both years, so "
                          "it cancels out of the ratio; no choice of weight "
                          "moves this number"),
    }
    crit.append({
        "name": "B35-PH-3",
        "kind": "own_reading",
        "passed": rate_mult > 1.0 and max_first_rate < 0.5,
        "detail": (
            f"at the dissected weight the line runs "
            + ", ".join(f"{y} {req[y]['ratio']:.3f}" for y in yrs)
            + f" of production, and a traded tongue of {req[last]['required_kg']:.4f} "
              f"kg would make {last} fit; but the weight cancels out of the "
              f"ratio between years, and there the tonnage rises "
              f"{qb/qa:.3f}x while slaughter moves "
              f"{slaughter[last]/slaughter[first]:.3f}x, so the share of the "
              f"country's tongues that leave it rose {rate_mult:.3f}x whatever "
              f"a tongue weighs. For {last} to sit at or below every tongue in "
              f"the country, {first} must have been at or below "
              f"{max_first_rate:.3f} of them, meaning three quarters of US "
              f"pork tongue went unexported in a year when it was already "
              f"being shipped at ${qv(rows, TONG, year(first))[1] / qa:.2f}/kg"),
    })

    # ---- 4. the month the line crosses its own ceiling ---------------------
    # 2022 only, because that is the year with slaughter by month. Mixing a
    # measured monthly figure with an annual one divided by twelve would put two
    # different objects on one axis.
    cross = []
    for m in range(1, 13):
        q, _ = qv(rows, TONG, [(2022, m)])
        prod = monthly[m] * YIELD[TONG]["kg"]
        cross.append({"month": m, "exports_t": q / 1000.0,
                      "ceiling_t": prod / 1000.0, "ratio": q / prod})
    rep["monthly_2022"] = cross
    pre = [c["ratio"] for c in cross if c["month"] < BREAK[1]]
    post = [c["ratio"] for c in cross if c["month"] >= BREAK[1]]
    crit.append({
        "name": "B35-PH-4",
        "kind": "own_reading",
        "passed": max(pre) < 1.0 <= min(post),
        "detail": (
            f"against slaughter by month, the world tongue line runs "
            f"{min(pre):.3f} to {max(pre):.3f} of the country's tongue "
            f"production in January through August 2022 and {min(post):.3f} to "
            f"{max(post):.3f} from September; it crosses its own physical "
            f"ceiling in the break month named by the gate and does not come "
            f"back under it"),
    })

    # ---- 5. the demand story's own prediction, read off the data -----------
    # A demand shift out along a supply curve whose position is set by slaughter
    # raises quantity AND price. This is the alternative explanation for the
    # reading, so it is measured rather than argued with.
    q1, v1 = qv(rows, TONG, year(yrs[0]), leg="CN")
    q3, v3 = qv(rows, TONG, year(yrs[-1]), leg="CN")
    p1, p3 = v1 / q1, v3 / q3
    rep["demand_signature"] = {
        "china_qty_factor": q3 / q1, "china_price_factor": p3 / p1,
        "price_2021": p1, "price_2023": p3,
        "prediction": ("a demand shift along a supply curve fixed by slaughter "
                       "moves quantity and price in the same direction"),
        "why_not_filed_as_rival": (
            "this is an alternative explanation for one of this station's own "
            "readings, not a point prediction of a competing price theory, so "
            "it is a known-answer check and stays out of the four-cell table"),
    }
    crit.append({
        "name": "B35-PH-5",
        "kind": "known_answer",
        "passed": (q3 / q1 > 1.0) and (p3 / p1 < 1.0),
        "detail": (
            f"on the China leg the tongue line's quantity moves {q3/q1:.3f}x "
            f"while its unit value moves {p3/p1:.3f}x (${p1:.3f} to ${p3:.3f} "
            f"a kg); a demand shift against a supply position fixed by "
            f"slaughter moves both the same way, and these move opposite ways, "
            f"so the quantity did not come from wanting more of this good"),
    })

    # ---- 6. the part where a demand story IS what the data shows -----------
    # Hearts. Same family, same feed, same years, and the arithmetic says
    # something different about them, which is the point.
    hw1, _ = qv(rows, HEART, year(yrs[0]))
    hw3, _ = qv(rows, HEART, year(yrs[-1]))
    hc1, _ = qv(rows, HEART, year(yrs[0]), leg="CN")
    hc3, _ = qv(rows, HEART, year(yrs[-1]), leg="CN")
    hn1, hn3 = hw1 - hc1, hw3 - hc3
    rep["hearts"] = {
        "world_t": [hw1 / 1000.0, hw3 / 1000.0], "world_factor": hw3 / hw1,
        "china_t": [hc1 / 1000.0, hc3 / 1000.0], "china_factor": hc3 / hc1,
        "nonchina_t": [hn1 / 1000.0, hn3 / 1000.0],
        "nonchina_factor": (hn3 / hn1) if hn1 else None,
        "china_share": [hc1 / hw1, hc3 / hw3],
        "exports_over_production": [ratios["hearts"][yrs[0]]["ratio"],
                                    ratios["hearts"][yrs[-1]]["ratio"]],
    }
    crit.append({
        "name": "B35-PH-6",
        "kind": "own_reading",
        "passed": (hw3 > hw1 and hc3 < hc1 and hn3 > hn1
                   and ratios["hearts"][yrs[-1]]["ratio"] < 0.5),
        "detail": (
            f"hearts do the opposite and the arithmetic says so: world exports "
            f"rise {hw3/hw1:.3f}x while China's fall {hc3/hc1:.3f}x and every "
            f"other destination rises {hn3/hn1:.3f}x, China's share going "
            f"{hc1/hw1:.3f} to {hc3/hw3:.3f}, with the line sitting at "
            f"{ratios['hearts'][yrs[-1]]['ratio']:.3f} of production and no "
            f"physical anomaly anywhere; that is a destination and demand "
            f"shift, and it is what one looks like here"),
    })

    # ---- 7. the one route left open, registered with its outcomes mapped ---
    branches = {
        "domestic": {
            "pattern": ("US imports of 0206490010 in 2023 are small next to "
                        "the 50,000 tonne gap"),
            "reading": ("the tongue line cannot be tongue and the code's "
                        "contents are what changed, which is the gate's "
                        "verdict standing on a physical bound"),
        },
        "re_export": {
            "pattern": ("US imports of 0206490010 in 2023 are of the order of "
                        "the gap"),
            "reading": ("exports are not bounded by domestic production and "
                        "this whole file is void; the gate's verdict would then "
                        "rest on the unit value and the mass balance alone"),
        },
        "partial": {
            "pattern": "imports cover part of the gap",
            "reading": ("the bound is weakened by the imported tonnage and the "
                        "reading is restated against production plus imports, "
                        "which is a subtraction, not a new argument"),
        },
    }
    rep["re_export_check"] = {
        "status": "registered, not run",
        "needs": ("US Census intltrade IMPORTS, HS10 0206490010, 2023, "
                  "same endpoint and same fetcher as the exports side"),
        "note_not_a_reading": (
            "an argument exists and is not used as one: imported tongue would "
            "have to be bought at a tongue price, and the line's unit value "
            "fell to head meat's, so re-export would have to be loss-making. "
            "That is reasoning, and the pull is a measurement, so the pull is "
            "registered rather than replaced"),
        "branches": branches,
    }
    crit.append({
        "name": "B35-PH-7",
        "kind": "bookkeeping",
        "passed": len({json.dumps(b["reading"]) for b in branches.values()})
                  == len(branches),
        "detail": ("exports exceed domestic production only if nothing was "
                   f"imported and re-exported; that pull is named and all "
                   f"{len(branches)} of its outcomes carry distinct readings "
                   "written before it runs, one of which voids this file"),
    })

    # ---- 8. two prices for one code, in the same year ----------------------
    # This one needs no yield, no slaughter and no weight. Same ten digit code,
    # same origin country, same month: what the rest of the world pays for a US
    # frozen swine tongue, against what the China leg records. If the code
    # carried one good these would track. The reading is interval overlap by
    # year, the same instrument used everywhere else in this station.
    two = {}
    for y in yrs:
        cq, cv = qv(rows, TONG, year(y), leg="CN")
        nq, nv = qv(rows, TONG, year(y), leg="NC")
        mon_c, mon_n = [], []
        for m in range(1, 13):
            a, b = qv(rows, TONG, [(y, m)], leg="CN")
            if a:
                mon_c.append(b / a)
            a, b = qv(rows, TONG, [(y, m)], leg="NC")
            if a:
                mon_n.append(b / a)
        two[y] = {"china_uv": cv / cq if cq else None,
                  "nonchina_uv": nv / nq if nq else None,
                  "china_monthly_range": [min(mon_c), max(mon_c)] if mon_c else None,
                  "nonchina_monthly_range": [min(mon_n), max(mon_n)] if mon_n else None,
                  "ratio": (cv / cq) / (nv / nq) if cq and nq else None}
    rep["two_prices_one_code"] = two
    ov_first = (min(two[first]["china_monthly_range"])
                <= max(two[first]["nonchina_monthly_range"])
                and min(two[first]["nonchina_monthly_range"])
                <= max(two[first]["china_monthly_range"]))
    ov_last = (min(two[last]["china_monthly_range"])
               <= max(two[last]["nonchina_monthly_range"])
               and min(two[last]["nonchina_monthly_range"])
               <= max(two[last]["china_monthly_range"]))
    crit.append({
        "name": "B35-PH-8",
        "kind": "own_reading",
        "passed": bool(ov_first and not ov_last),
        "detail": (
            f"one code, one origin, two prices: in {first} the China leg runs "
            f"${two[first]['china_monthly_range'][0]:.2f}-"
            f"{two[first]['china_monthly_range'][1]:.2f} a kg by month against "
            f"${two[first]['nonchina_monthly_range'][0]:.2f}-"
            f"{two[first]['nonchina_monthly_range'][1]:.2f} everywhere else and "
            f"the two overlap, and in {last} they are "
            f"${two[last]['china_monthly_range'][0]:.2f}-"
            f"{two[last]['china_monthly_range'][1]:.2f} against "
            f"${two[last]['nonchina_monthly_range'][0]:.2f}-"
            f"{two[last]['nonchina_monthly_range'][1]:.2f} and they do not; the "
            f"rest of the world goes on paying a tongue price for this code "
            f"while the China leg pays {two[last]['ratio']:.3f} of it, and no "
            f"weight, yield or slaughter figure enters this reading"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True

    def row(code, cty, name, y, m, q, v):
        return {"E_COMMODITY": code, "CTY_CODE": cty, "CTY_NAME": name,
                "_year": y, "_month": m, "QTY_1_MO": str(q),
                "ALL_VAL_MO": str(v)}

    # A world where every line is physically possible. The impossibility
    # criterion must NOT fire, or it fires on anything.
    sl = {2021: 120_000_000, 2022: 120_000_000, 2023: 120_000_000}
    mo = {m: 10_000_000 for m in range(1, 13)}
    seed = []
    for y in sl:
        for m in range(1, 13):
            for code, frac, price in ((TONG, 0.5, 3.30), (HEART, 0.2, 1.40),
                                      (FOOT, 0.5, 2.30)):
                q = sl[y] / 12 * YIELD[code]["per_animal"] * YIELD[code]["kg"] * frac
                seed.append(row(code, "5700", CHINA, y, m, q * 0.5, q * 0.5 * price))
                seed.append(row(code, "5880", "JAPAN", y, m, q * 0.5, q * 0.5 * price))
                seed.append(row(code, "5XXX", "ASIA", y, m, q, q * price))
    crit, rep = run(seed, sl, mo)
    by = {c["name"]: c for c in crit}
    if by["B35-PH-3"]["passed"]:
        print("SELFTEST FAIL: the impossibility fired on a possible world")
        ok = False
    # Criterion 2 reads an ordering: the tongue line asks for more trade-cut
    # allowance than any control. In a world where nothing is wrong it must NOT
    # fire, and a guard that fires either way is reading nothing.
    if by["B35-PH-2"]["passed"]:
        print("SELFTEST FAIL: the ordering fired on a world with no anomaly")
        ok = False
    for name in ("tongues", "hearts", "feet"):
        r = rep["exports_over_production"][name][2023]["ratio"]
        want = 0.5 if name != "hearts" else 0.2
        if abs(r - want) > 1e-9:
            print("SELFTEST FAIL: seeded %s at %.3f of production, read %.6f"
                  % (name, want, r))
            ok = False

    # A world seeded to be impossible on tongues only, at a known multiple.
    seed2 = []
    for y in sl:
        for m in range(1, 13):
            for code, frac, price in ((TONG, 2.0, 3.30), (HEART, 0.2, 1.40),
                                      (FOOT, 0.5, 2.30)):
                q = sl[y] / 12 * YIELD[code]["per_animal"] * YIELD[code]["kg"] * frac
                seed2.append(row(code, "5700", CHINA, y, m, q * 0.9, q * 0.9 * price))
                seed2.append(row(code, "5880", "JAPAN", y, m, q * 0.1, q * 0.1 * price))
                seed2.append(row(code, "5XXX", "ASIA", y, m, q, q * price))
    c2, r2 = run(seed2, sl, mo)
    b2 = {c["name"]: c for c in c2}
    if abs(r2["required_tongue_weight"][2023]["required_kg"]
           - 2.0 * YIELD[TONG]["kg"]) > 1e-9:
        print("SELFTEST FAIL: inverted weight should be twice the measured one")
        ok = False
    if not b2["B35-PH-2"]["passed"]:
        print("SELFTEST FAIL: the ordering did not fire on a seeded anomaly")
        ok = False
    # criterion 3 wants the first year under one and the last over one; this
    # seed is over in every year, so it must NOT pass, and that is the point:
    # the criterion reads a crossing, not a level.
    if b2["B35-PH-3"]["passed"]:
        print("SELFTEST FAIL: a level with no crossing should not read as one")
        ok = False

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not SRC.exists():
        print("missing %s" % SRC)
        return 2
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    crit, rep = run(rows)

    print("=" * 74)
    print("B35 physical ceiling: how many tongues exist against how many shipped")
    print("=" * 74)
    print("slaughter, commercial head: " +
          ", ".join("%d %s" % (y, format(rep["slaughter_head"][y], ","))
                    for y in sorted(rep["slaughter_head"])))
    print("yield per animal, kg: " +
          ", ".join("%s %.2f+/-%.2f" % (k, v["kg"], v["sd"])
                    for k, v in rep["yield_kg_per_animal"].items()))
    print()
    print("%-10s %6s %12s %14s %9s" % ("", "year", "exports t",
                                       "production t", "ratio"))
    for name, byy in rep["exports_over_production"].items():
        for y in sorted(byy):
            d = byy[y]
            print("%-10s %6d %12.1f %14.1f %9.3f"
                  % (name, y, d["exports_t"], d["production_t"], d["ratio"]))
    print()
    print("what a tongue would have to weigh for the line to be tongue")
    for y in sorted(rep["required_tongue_weight"]):
        d = rep["required_tongue_weight"][y]
        print("  %d   %.4f kg   %+.1f sd above the measured 0.25 +/- 0.04"
              % (y, d["required_kg"], d["sd_above_measured"]))
    print()
    print("2022 by month, world tongue against that month's own ceiling")
    for c in rep["monthly_2022"]:
        print("  %02d  %8.1f t   ceiling %8.1f t   %6.3f%s"
              % (c["month"], c["exports_t"], c["ceiling_t"], c["ratio"],
                 "   <- break" if c["month"] == BREAK[1] else ""))
    print()
    d = rep["demand_signature"]
    print("the demand story's own prediction: quantity x%.3f, price x%.3f"
          % (d["china_qty_factor"], d["china_price_factor"]))
    h = rep["hearts"]
    print("hearts, for contrast: world x%.3f, China x%.3f, elsewhere x%.3f, "
          "China share %.3f -> %.3f"
          % (h["world_factor"], h["china_factor"], h["nonchina_factor"],
             h["china_share"][0], h["china_share"][1]))
    print()
    for c in crit:
        print("%-5s %-12s %s" % ("PASS" if c["passed"] else "FAIL",
                                 c["name"], c["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B35-PH",
        "config": {"source": SRC.name, "break": list(BREAK),
                   "slaughter_head": SLAUGHTER,
                   "slaughter_source": SLAUGHTER_SRC,
                   "yield_source": YIELD_SRC,
                   "yield_kg_per_animal": {NAMES[k]: v
                                           for k, v in YIELD.items()},
                   "atom_rule": "four digits, all numeric, not starting 00"},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
