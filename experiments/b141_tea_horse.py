"""B141: Ming tea for horses. One horse, two prices, and the price of the edge that was cut.

The tea-horse offices bought horses for tea at a price the state wrote down; private tea bought them
at whatever the private market paid. The state cut the private edge by statute. Where the ban held,
the square between the two channels is non-zero and its size is the price of the cut edge; where it
slipped, sellers moved to the private market, official intake fell, and the state either rewrote its
price or went without horses.

**The square.** Office ``j``, year ``t``, grade ``g``. Official price ``x(j,t,g)``, private price
``y(j,t,g)``, both in jin of tea per horse:

    square = ln y - ln x      only on pairs where place, period, grade and kind of tea all match
    rival  = 0                a horse has one price in tea, whoever buys it

**Units.** One jin is sixteen liang; a bao is 50 jin and two bao make a yin (Hongwu 4). The bi (篦)
changed weight across the dynasty and is taken by year, with every reading the sources give kept as
a variant: early Ming 7 jin (Wang Qi's edition: 10); Zhengde 10 (1515) 1,000 jin to 330 bi, each
6 jin 4 liang gross of which 3 jin tea; Longqing 5 (1571) at most 7 jin; early Qing 10 jin (two feng
of five).

**Grades.** 上, 中, 下. 堪中马 means "a horse fit to be taken", not the middle grade; 驹马 is the
third grade at Yazhou 1389 and maps to 下 with a flag.

**Enforcement dose.** Four dimensions (penalty, patrol officials, merchant tea, gold tallies), each a
list of dated events; the state on a day is the last event on or before it (an event on day d
governs d itself). Gold tallies have three stop dates in primary sources; all are carried.

Block one (``--paper``) checks units, grades, pairing and the dose encoder on synthetic data with
seeded faults. It writes nothing.

    python experiments/b141_tea_horse.py --paper
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import sys

import numpy as np

SEED = 141
TOL = 1e-12
LIANG_PER_JIN = 16

FAULTS = ("bi_as_jin", "bi_one_weight", "kanzhong_as_middle", "pair_across_grade",
          "pair_across_place", "state_from_next_day", "floor_zero", "count_by_record", "ignore_contrary",
          "pair_unknown_as_same", "floor_half_jin", "one_bi_reading", "foal_simplified_only", "quota_as_intake",
          "posted_unchecked")

# --------------------------------------------------------------------------
# units


BI_READINGS = {  # (first year it applies, jin of tea per bi), per variant
    "tea": [(1368, 7.0), (1515, 1000 / 330), (1571, 7.0), (1644, 10.0)],
    "gross": [(1368, 7.0), (1515, 6.25), (1571, 7.0), (1644, 10.0)],
    "wangqi": [(1368, 10.0), (1515, 1000 / 330), (1571, 7.0), (1644, 10.0)],
}
FIXED = {"斤": 1.0, "两": 1 / LIANG_PER_JIN, "包": 50.0, "引": 100.0, "封": 5.0}


def bi_jin(year, variant="tea", fault=None):
    if fault == "bi_as_jin":
        return 1.0
    steps = BI_READINGS["tea" if fault == "bi_one_weight" else variant]
    if fault == "bi_one_weight":
        return steps[0][1]
    w = None
    for start, jin in steps:
        if year >= start:
            w = jin
    return w


def to_jin(value, unit, year, variant="tea", fault=None):
    if unit == "篦":
        return value * bi_jin(year, variant, fault)
    return value * FIXED[unit]


# --------------------------------------------------------------------------
# grades


def grade(label: str, fault=None):
    """(grade, flag) or (None, reason). The foal of Yazhou 1389 is printed 駒馬 in the Veritable Records."""
    s = label.strip()
    if s.startswith("堪中"):
        return ("中", "") if fault == "kanzhong_as_middle" else (None, "堪中马 is a fit horse, no grade")
    if s.startswith("驹") or (s.startswith("駒") and fault != "foal_simplified_only"):
        return "下", "third grade at Yazhou 1389, printed as 駒馬"
    for g in ("上", "中", "下"):
        if s.startswith(g):
            return g, ""
    return None, f"no grade in {s!r}"


# --------------------------------------------------------------------------
# the square

FEATURES = ("place", "period", "grade", "tea")


def pairs(official, private, fault=None):
    """Match official and private records on place, period, grade and kind of tea. A feature a record does not
    state matches nothing: two records silent on the grade are not thereby of one grade. Every unmatched record
    is returned with its reason."""
    out, left = [], []
    strict = fault != "pair_unknown_as_same"
    for p in private:
        silent = [f for f in FEATURES if p.get(f) is None]
        if silent and strict:
            left.append((p, "not stated in the private record: " + ", ".join(silent)))
            continue
        hit = None
        for o in official:
            if strict and any(o.get(f) is None for f in FEATURES):
                continue
            same = [o["place"] == p["place"] or fault == "pair_across_place",
                    o["period"] == p["period"],
                    o["grade"] == p["grade"] or fault == "pair_across_grade",
                    o["tea"] == p["tea"]]
            if all(same):
                hit = o
                break
        if hit is None:
            left.append((p, "no official record with the same place, period, grade and tea"))
        else:
            out.append((hit, p))
    return out, left


def quote(rec, variant="tea", fault=None):
    """A printed quote in jin with the interval its last printed place allows. The last place is in the unit the
    quote is printed in: a count of bao is good to half a bao (25 jin), not to half a jin. A record may carry
    'last_place' in its own unit; the default is one unit."""
    per = to_jin(1.0, rec["unit"], rec["year"], variant, fault)
    v = rec["value"] * per
    half = 0.5 if fault == "floor_half_jin" else 0.5 * rec.get("last_place", 1.0) * per
    return v, v - half, v + half


def square(o, p, variant="tea", fault=None):
    """ln private - ln official for one pair, with the lowest and highest value the two printed quotes allow. The
    pair reads non-zero only when the two printed intervals share no value."""
    x, xlo, xhi = quote(o, variant, fault)
    y, ylo, yhi = quote(p, variant, fault)
    s = math.log(y) - math.log(x)
    if fault == "floor_zero":
        return {"square": s, "lo": s, "hi": s, "nonzero": s != 0.0}
    lo = math.log(ylo / xhi) if ylo > 0 else -math.inf
    hi = math.log(yhi / xlo) if xlo > 0 else math.inf
    return {"square": s, "lo": lo, "hi": hi, "nonzero": lo > 0 or hi < 0}


def square_by_reading(o, p, fault=None):
    """The square under every reading of the bi's weight. A pair is non-zero only if it is so under each reading and
    compatible with zero only if it is so under each; otherwise it turns on the reading and is left unread."""
    readings = ["tea"] if fault == "one_bi_reading" else list(BI_READINGS)
    by = {v: square(o, p, v, fault) for v in readings}
    nz = [r["nonzero"] for r in by.values()]
    status = "non-zero" if all(nz) else "compatible with zero" if not any(nz) else "depends on the bi reading"
    return by, status


# --------------------------------------------------------------------------
# the dose encoder


def state_at(events, day, fault=None):
    """Last event on or before day; events: sorted (date, state)."""
    cur = None
    for d, st in events:
        if d < day or (d == day and fault != "state_from_next_day"):
            cur = st
    return cur


D = dt.date
DOSE = {
    # 刑名: the severest penalty written for carrying tea out; the offences are not all the same one
    "penalty": [(D(1368, 1, 23), "杖一百徒三年（同私鹽法）"), (D(1397, 12, 30), "處斬"),
                (D(1409, 1, 4), "淩遲"), (D(1482, 10, 11), "五百斤以上充軍"),
                (D(1505, 2, 1), "潛往邊境不拘斤數烟瘴永遠充軍")],
    # 巡禁官 (years only where the source gives only a year: first day of that year, flagged)
    "patrol": [(D(1397, 1, 1), "行人每月一巡"), (D(1435, 1, 1), "三月一差"),
               (D(1452, 1, 1), "行人與御史反復更換"), (D(1478, 1, 1), "御史每歲一代"),
               (D(1503, 1, 1), "都御史專理"), (D(1507, 1, 1), "巡茶御史兼管馬政"),
               (D(1603, 1, 1), "巡按兼理")],
    # 開中 and merchant tea
    "merchant": [(D(1435, 1, 1), "開"), (D(1436, 1, 1), "關"), (D(1482, 1, 1), "開"),
                 (D(1490, 1, 1), "開"), (D(1495, 1, 1), "開"), (D(1500, 1, 1), "關"),
                 (D(1502, 1, 1), "關"), (D(1536, 1, 1), "內地開"), (D(1557, 1, 1), "增"),
                 (D(1564, 1, 1), "減"), (D(1585, 1, 1), "腹裏三府開")],
}
# The three readings of when the tallies stopped. The Yongle stops are followed by the Xuande 10
# (1435) reissue, so the Zhengtong 14 (1449) stop can be a second stop after it, not a rival date:
# both Yongle chains carry it. Yang Yiqing's memorial of 1504, "since the tallies were abolished ...
# nearly sixty years", points at the 1440s, which is the 1449 stop.
GOLD_TALLY = {
    "永樂四年 (續通考卷22)": [(D(1393, 3, 20), "on"), (D(1406, 1, 1), "off"),
                           (D(1435, 1, 1), "on"), (D(1449, 1, 1), "off"), (D(1551, 2, 23), "勘合代")],
    "永樂十四年 (萬曆會典卷37)": [(D(1393, 3, 20), "on"), (D(1416, 1, 1), "off"),
                              (D(1435, 1, 1), "on"), (D(1449, 1, 1), "off"), (D(1551, 2, 23), "勘合代")],
    "正統十四年 (正德會典卷122)": [(D(1393, 3, 20), "on"), (D(1449, 1, 1), "off"),
                               (D(1551, 2, 23), "勘合代")],
}


# --------------------------------------------------------------------------
# synthetic checks


def synthetic(rng, n=400, gap=True):
    places, periods, teas = ["河州", "洮州", "西寧", "碉門"], list(range(1380, 1620, 20)), ["官茶", "巴茶"]
    units = ["斤", "篦", "包", "引", "两"]
    official, private, truth = [], [], {}
    for k in range(n):
        key = (places[k % 4], periods[(k // 4) % 12], "上中下"[(k // 48) % 3], teas[(k // 144) % 2])
        if key in truth:
            continue
        year = key[1] + int(rng.integers(0, 20))
        x = float(rng.uniform(20, 150))
        y = x * (float(np.exp(rng.uniform(0.3, 1.5))) if gap else 1.0)
        truth[key] = math.log(y) - math.log(x)
        for rec, jin in ((official, x), (private, y)):
            u = units[int(rng.integers(0, len(units)))]
            per = to_jin(1.0, u, year)
            # a synthetic quote is printed to the jin, in whatever unit it is quoted
            rec.append({"place": key[0], "period": key[1], "grade": key[2], "tea": key[3],
                        "year": year, "unit": u, "value": jin / per, "last_place": 1.0 / per})
    return official, private, truth


def check_units(fault=None):
    worst = 0.0
    rng = np.random.default_rng(SEED)
    for _ in range(2000):
        year = int(rng.integers(1368, 1700))
        jin = float(rng.uniform(1, 500))
        for u in ("斤", "篦", "包", "引", "两"):
            per = FIXED.get(u) or {1368: 7.0, 1515: 1000 / 330, 1571: 7.0, 1644: 10.0}[
                max(s for s in (1368, 1515, 1571, 1644) if year >= s)]
            worst = max(worst, abs(to_jin(jin / per, u, year, fault=fault) - jin) / jin)
    return {"passed": worst < TOL, "worst": worst}


def check_grades(fault=None):
    cases = {"上馬": "上", "中馬": "中", "下馬": "下", "驹马": "下", "駒馬": "下", "堪中馬": None, "善馬": None}
    bad = [k for k, want in cases.items() if grade(k, fault)[0] != want]
    return {"passed": not bad, "wrong": bad}


def check_square(fault=None):
    rng = np.random.default_rng(SEED)
    off, pri, truth = synthetic(rng)
    # shuffle grades on one extra private record so a cross-grade pair is available to go wrong
    extra = dict(pri[0], grade="上" if pri[0]["grade"] != "上" else "中", place="莊浪")
    off2 = [o for o in off if not (o["place"] == pri[0]["place"] and o["grade"] == extra["grade"]
                                   and o["period"] == extra["period"] and o["tea"] == extra["tea"])]
    got, left = pairs(off2, pri + [extra], fault=fault)
    worst = 0.0
    for o, p in got:
        key = (p["place"], p["period"], p["grade"], p["tea"])
        s = square(o, p, fault=fault)["square"]
        worst = max(worst, abs(s - truth[key]) if key in truth else math.inf)
    unmatched_extra = any(p is extra for p, _ in left)
    # a feature both records leave unstated is no match: each of the four in turn
    silent = []
    for f in FEATURES:
        o = {"place": "河州", "period": 1400, "grade": "上", "tea": "官茶", "year": 1400, "unit": "斤", "value": 80}
        p = dict(o, value=160)
        o[f] = p[f] = None
        g, lf = pairs([o], [p], fault=fault)
        silent.append(len(g) == 0 and f in lf[0][1])
    return {"passed": worst < 1e-9 and unmatched_extra and all(silent), "worst": worst, "pairs": len(got),
            "unmatched": len(left), "unstated_feature_left_unpaired": f"{sum(silent)}/{len(silent)}"}


def check_rival_field(fault=None):
    """11f: where private equals official no pair may read non-zero. A quote counted in a coarse unit is good only to
    half that unit, and a pair whose square turns on the bi's weight is left unread."""
    rng = np.random.default_rng(SEED)
    off, pri, _ = synthetic(rng, gap=False)
    got, _ = pairs(off, pri, fault=fault)
    over = sum(square(o, p, fault=fault)["nonzero"] for o, p in got)
    off, pri, _ = synthetic(np.random.default_rng(SEED), gap=True)
    got2, _ = pairs(off, pri, fault=fault)
    over_gap = sum(square(o, p, fault=fault)["nonzero"] for o, p in got2)
    # one true price of 126 jin, printed as 126 jin by the office and as 3 bao (125 to 175 jin) in the market
    same = square({"value": 126, "unit": "斤", "year": 1400}, {"value": 3, "unit": "包", "year": 1400}, fault=fault)
    # 70 jin against 10 bi in 1380: equal at 7 jin a bi, apart at the 10 of Wang Qi's edition
    _, bi = square_by_reading({"value": 70, "unit": "斤", "year": 1380}, {"value": 10, "unit": "篦", "year": 1380}, fault)
    return {"passed": (over == 0 and over_gap == len(got2) and not same["nonzero"]
                       and bi == "depends on the bi reading"),
            "equal_field_nonzero": over, "gap_field_nonzero": f"{over_gap}/{len(got2)}",
            "126 jin against 3 bao": "non-zero" if same["nonzero"] else "compatible with zero",
            "70 jin against 10 bi": bi}


def check_encoder(fault=None):
    ev = [(D(1400, 5, 1), "a"), (D(1400, 5, 3), "b")]
    want = {D(1400, 4, 30): None, D(1400, 5, 1): "a", D(1400, 5, 2): "a", D(1400, 5, 3): "b"}
    bad = [str(d) for d, w in want.items() if state_at(ev, d, fault) != w]
    return {"passed": not bad, "wrong_days": bad}


CHECKS = {"units": check_units, "grades": check_grades, "square": check_square,
          "rival field": check_rival_field, "dose encoder": check_encoder}


# --------------------------------------------------------------------------
# B141-3b. The sign of the square, read from dated statements (2026-09-30). No pair gives the size of the
# gap between the channels; the sources state its direction many times over. Each statement is coded by
# what it reports: with the private channel open, sellers leave the office, the horse grows dear and
# office tea cheap; with it cut, tea grows dear at the border and the horses come. Both are the same sign:
# the private channel pays the seller more than the office does. The rival, one price through either
# channel, leaves the seller indifferent, so such reports carry no common sign.
#
# (block-zero file, index in its record list, year, what the statement reports)
DIRECTION = [
    ("private", 0, 1397, "open: horses dear, tea cheap"),
    ("private", 1, 1397, "open: tea cheap, horses dear"),
    ("private", 2, 1397, "open: private tea goes cheap to the buyers, few horses come in"),
    ("private", 7, 1435, "open: fewer horses got"),
    ("private", 8, 1436, "open: office tea loses value"),
    ("private", 9, 1441, "open: horses dear, tea cheap"),
    ("private", 10, 1442, "open: sellers no longer bring horses for office tea"),
    ("private", 11, 1445, "open: tea price lost, horse numbers short"),
    ("private", 12, 1448, "open: fine tea sold privately, coarse tea to the office, sellers refuse it"),
    ("private", 30, 1471, "open: the office price must be raised to 200 and 100 jin to starve the private market"),
    ("private", 13, 1473, "cut: horses crowd in"),
    ("private", 14, 1502, "open: horses got are not a tenth of early Chenghua's, the ban on private tea not holding"),
    ("private", 34, 1503, "cut: tea dear at Xining"),
    ("private", 31, 1504, "cut: tea price jumps, sellers gather from far and near"),
    ("private", 15, 1523, "open: sellers get tea without bringing horses"),
    ("private", 16, 1530, "open: sellers supplied by traders, not by the office"),
    ("private", 18, 1533, "open: brick tea goes straight to the sellers, the office market stalls"),
    ("private", 19, 1534, "open: merchant tea swells, horses do not come"),
    ("private", 37, 1536, "open: the gain on private dealing is more than threefold"),
    ("private", 40, 1541, "open: sellers collect the gain on tea and bring no tally horses"),
    ("private", 20, 1551, "open: horses do not come even with the gold tally"),
    ("private", 42, 1590, "open: traders carry tea deep into the sellers' country for a thick gain"),
    ("private", 22, 1595, "open: sellers enjoy cheap private tea and will not bring horses"),
    ("private", 23, 1597, "open: sellers enjoy cheap private tea and will not bring horses"),
]
# read and not coded: (file, index, why)
DIRECTION_NOT_CODED = [
    ("private", 6, "1433: an officer cut the price paid to sellers and traded privately; no sign stated"),
    ("private_verify", 3, "Mingshan cang on 1435-36: a later compilation"),
    ("private_verify", 4, "Mingshan cang on 1478: a later compilation"),
    ("private_verify", 5, "Mingshan cang on 1546, 'the ban strict, tea price soaring': a later compilation"),
    ("private", 45, "Ming shi 80, 'the best horses all go to the traders': a later compilation"),
    ("private_verify", 19, "Wanli Shaanxi tongzhi through Tani 1966: read at second hand"),
]
REIGNS = [(1368, 1398, "Hongwu"), (1399, 1402, "Jianwen"), (1403, 1424, "Yongle"), (1425, 1425, "Hongxi"),
          (1426, 1435, "Xuande"), (1436, 1449, "Zhengtong"), (1450, 1456, "Jingtai"), (1457, 1464, "Tianshun"),
          (1465, 1487, "Chenghua"), (1488, 1505, "Hongzhi"), (1506, 1521, "Zhengde"), (1522, 1566, "Jiajing"),
          (1567, 1572, "Longqing"), (1573, 1620, "Wanli")]


def reign_of(year):
    return [n for a, b, n in REIGNS if a <= year <= b][0]


def direction_verdict(statements, fault=None, alpha=0.05):
    """statements: (year, sign) with sign +1 for the framework's direction and -1 against it. The unit is
    the reign, the coarsest one the sources allow: statements of one reign count once, and a reign with any
    contrary statement counts against. Passes when every reign agrees and one half to the power of their
    number is below alpha; fails when half the reigns or more go the other way; otherwise unread."""
    if fault == "count_by_record":
        units = {i: [sg] for i, (_, sg) in enumerate(statements)}
    else:
        units = {}
        for year, sg in statements:
            units.setdefault(reign_of(year), []).append(sg)
    n = len(units)
    against = 0 if fault == "ignore_contrary" else sum(1 for v in units.values() if min(v) < 0)
    if n == 0:
        return {"passed": None, "units": 0, "against": 0, "prob": None}
    if against * 2 >= n:
        return {"passed": False, "units": n, "against": against, "prob": None}
    prob = 0.5 ** n if against == 0 else 1.0
    return {"passed": True if prob < alpha else None, "units": n, "against": against, "prob": prob}


def check_direction(fault=None):
    """Seven reigns agreeing pass; six statements of one reign do not; contrary reigns fail or stay unread."""
    spread = [(y, 1) for y in (1397, 1435, 1441, 1471, 1504, 1530, 1595)]
    one_reign = [(1530 + i, 1) for i in range(6)]
    half_against = [(1397, 1), (1435, -1), (1441, 1), (1471, -1)]
    one_against = spread[:-1] + [(1595, -1)]
    got = {"seven reigns": direction_verdict(spread, fault)["passed"],
           "one reign, six statements": direction_verdict(one_reign, fault)["passed"],
           "half against": direction_verdict(half_against, fault)["passed"],
           "one reign against": direction_verdict(one_against, fault)["passed"]}
    want = {"seven reigns": True, "one reign, six statements": None, "half against": False,
            "one reign against": None}
    return {"passed": got == want, "got": got}


CHECKS["direction"] = check_direction


def dose_table():
    rows = []
    for year in (1400, 1410, 1420, 1440, 1450, 1480, 1500, 1504, 1510, 1540, 1560, 1600):
        day = D(year, 7, 1)
        gold = " / ".join(state_at(ev, day) or "-" for ev in GOLD_TALLY.values())
        rows.append(f"  {year}  penalty {state_at(DOSE['penalty'], day)}; patrol {state_at(DOSE['patrol'], day)}; "
                    f"merchant {state_at(DOSE['merchant'], day)}; gold tallies {gold}")
    return rows


def paper() -> int:
    ok = True
    print("B141-1, block one\n")
    for name, fn in CHECKS.items():
        r = fn()
        ok &= r["passed"]
        print(f"  {name:13s} {'PASS' if r['passed'] else 'FAIL'}  "
              + ", ".join(f"{k} {v}" for k, v in r.items() if k != "passed"))
    print()
    for fault in FAULTS:
        caught = [n for n, fn in CHECKS.items() if not fn(fault=fault)["passed"]]
        ok &= bool(caught)
        print(f"  fault {fault:20s} caught by: {', '.join(caught) or 'NOTHING'}")
    print("\nBi weight by year, every reading (jin of tea per bi)")
    for v, steps in BI_READINGS.items():
        print(f"  {v:7s} " + "; ".join(f"from {s} {w:.4g}" for s, w in steps))
    print("\nDose on 1 July of sample years; gold tallies in the order "
          + " / ".join(GOLD_TALLY))
    for r in dose_table():
        print(r)
    print(f"\nblock one {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# block two: the readings (printed, not written; block three writes the record)
# Every row carries its record in data/raw/b141/_blockzero/{horses,horses_verify}.json by index.

# posted official prices, jin of tea per horse by grade (上, 中, 下):
# (year or None, the date as it is known, place, prices or None, source, block-zero record, record that dates it)
POSTED = [
    (1383, "1383", "永寧 (as 河州)", (40, 30, 20), "太祖實錄 156", 7, None),
    (None, "洪武中 (recalled 1409)", "秦河", (80, 60, 40), "太宗實錄 87", 21, None),
    (1389, "1389", "雅州/碉門, to 長河西 merchants, 'who will not may refuse'", (120, 70, 50), "太祖實錄 196", 13, None),
    (1410, "1410", "河州", (60, 40, None), "太宗實錄 110", 22, None),
    (1435, "1435", "河州: +30 jin per horse, on request", None, "英宗實錄 8", 26, None),
    # Li Dongyang's 西北備邊事宜狀, headed 閣試 in the Jingshi wenbian: an essay set in the Hanlin, dated by its
    # account of 癿加思蘭 holding the Ordos as a present danger; the Mazheng ji quotes it without a date, and
    # block-zero record 74 files that quotation under Hongzhi
    (1471, "c. 1471-72, proposal", "陝西 (李東陽, a cabinet-examination essay: 'if they covet the high price, "
     "private trade cannot run')", (200, None, 100), "皇明經世文編 54; 馬政紀 12", 74, ("private", 30)),
    (1490, "1490", "西寧 河州 洮州", (100, 80, None), "萬曆會典 37", 67, None),
    (1644, "順治初", "陝甘 five offices, 12/9/7 bi of 10 jin", (120, 90, 70), "雍正陝西通志 42", 96, None),
]

# realized official price: tea paid / horses taken, where one record gives both (西北 offices)
REALIZED = [
    (1380, "河州", 58892, 2050, "plus 98 oxen", 4),
    (1392, "河州", 300000, 10340, "tea '30餘萬', horses '10,340餘'", 15),
    (1398, "三衛 (gold tallies)", 500000, 13518, "tea '50餘萬'", 19),
    (1410, "河州", 278460, 7714, "", 22),
    (1435, "西寧 河州 洮州", 1097000, 13000, "horses '13,000餘'", 25),
    (1447, "five 衛", 125430, 2946, "", 28),
    (1508, "三司 under 翟唐", 782000, 9000, "a year, both 'x餘'", 34),
]
# 碉門, Sichuan: the same channel, before the 1389 posting and when the ban slackened
DIAOMEN = [
    (1387, "tea 163,600 jin for camels, horses, mules, foals '170餘'", 163600, 170, 12),
    (1389, "old price per fit horse, before the posting", 1800, 1, 13),
    (1409, "'the tea ban slightly relaxed': tea 83,050 jin, horses 70", 83050, 70, 21),
]

# horses, 西寧 河州 洮州 together unless noted:
# (when, first year, last year, taken or due, scope, horses, per campaign or per year, note, block-zero record)
# A sum due or a quota is what the offices were to receive, not what came in; it is listed and never compared.
INTAKE = [
    ("1393-1449", 1393, 1449, "due", "three offices", 14051, "campaign",
     "gold-tally levy due every three years (7,705 + 3,296 + 3,050), arrears collected the next year", 83),
    ("1398", 1398, 1398, "taken", "three offices", 13518, "campaign", "one campaign (three 衛)", 19),
    ("1432", 1432, 1432, "taken", "part", 6500, "campaign", "河州 alone, of 7,700 due", 24),
    ("1435", 1435, 1435, "taken", "three offices", 13000, "campaign", "three offices, '13,000餘'", 25),
    ("1447", 1447, 1447, "taken", "part", 2946, "campaign", "five 衛 of the 西寧 side", 28),
    ("1497-1502", 1497, 1502, "taken", "three offices", 5043 / 6, "year", "six years 5,043", 75),
    ("1503", 1503, 1503, "taken", "three offices", 2488, "year", "", 76),
    ("1504", 1504, 1504, "taken", "three offices", 6343, "year", "", 77),
    ("1505", 1505, 1505, "taken", "three offices", 4298, "year", "", 78),
    ("1506", 1506, 1506, "taken", "three offices", 5948, "year", "", 79),
    ("1508", 1508, 1508, "taken", "three offices", 9000, "year", "翟唐, a year, '9,000餘'", 34),
    ("1556", 1556, 1556, "due", "later offices", 4800, "year", "quota 洮州 河州", 43),
    ("1571", 1571, 1571, "taken", "later offices", 6370, "year", "four offices", 46),
    ("1601", 1601, 1601, "due", "later offices", 9600, "year", "quota, six offices", 51),
    ("to 1618", 1618, 1618, "due", "later offices", 9724, "year",
     "yearly quota before the Liao war, recalled by 王大年 in 1626", 56),
    ("to 1644", 1644, 1644, "due", "later offices", 11088, "year",
     "old quota of five offices at the end of Chongzhen, 'in arrears every year' (姜圖南's memorial, after 1645)", 93),
]
# Xiaozong shilu 194, 1502-12-30 (private record 14): the fall stated by a censor, not counted
FALL_STATED = ("1502", "in early Chenghua 'ten thousand a year', of late 'not one in ten' (variants: 'not two in "
               "ten'), laid to the ban on private tea not holding and to merchant tea", ("private", 14))

SEGMENTS = [
    ("1393-1449", "gold tallies on (1406-1416 disputed), penalty death, patrol monthly to 1435 and once in three "
                  "months from then"),
    ("1449-1502", "tallies off, patrol once in three months, messengers and censors by turns (1452), a censor a "
                  "year (1478); 'private trade flourishes'"),
    ("1503-1535", "楊一清: a censor-in-chief in charge (1503), 1505 penalty, tea patrol censor (1507)"),
    ("1536-1644", "merchant tea opened inland (1536); quotas"),
]


def intake_reading(rows, fault=None):
    """Horses taken a year by the three offices: under the tallies (a campaign every three years, so a campaign's
    count over three), in the slack span, and after the tightening. Sums due and quotas never enter; the seeded
    fault lets them in."""
    kinds = ("taken", "due") if fault == "quota_as_intake" else ("taken",)
    use = [(r[1], r[2], r[5] / 3 if r[6] == "campaign" else r[5]) for r in rows
           if r[3] in kinds and r[4] == "three offices"]
    early = [n for a, b, n in use if b <= 1449]
    slack = [n for a, b, n in use if a >= 1450 and b <= 1502]
    tight = [n for a, b, n in use if 1503 <= a and b <= 1506]
    ok = bool(early and slack and tight)
    return {"early": early, "slack": slack, "tight": tight,
            "fell": ok and max(slack) < min(early), "returned": ok and max(slack) < min(tight)}


def check_intake(fault=None):
    """A quota is not intake: with no count of horses taken under the tallies, a fall from them cannot be read."""
    rows = [("due", 1393, 1449, "due", "three offices", 14051, "campaign", "", 0),
            ("slack", 1497, 1502, "taken", "three offices", 840, "year", "", 0),
            ("tight", 1504, 1504, "taken", "three offices", 6000, "year", "", 0)]
    got = intake_reading(rows, fault)
    full = intake_reading(rows + [("early", 1398, 1398, "taken", "three offices", 13500, "campaign", "", 0)], fault)
    return {"passed": got["fell"] is False and full["fell"] is True and full["returned"] is True,
            "without an early count": got["fell"], "with one": full["fell"]}


def intake_around(year):
    """The last three-office count before a year, any in it, and the first after it."""
    comp = [r for r in INTAKE if r[3] == "taken" and r[4] == "three offices"]
    before = [r for r in comp if r[2] < year]
    same = [r for r in comp if r[1] <= year <= r[2]]
    after = [r for r in comp if r[1] > year]
    return (before[-1] if before else None), (same[0] if same else None), (after[0] if after else None)


def posted_check(rows, recs, dating=None, fault=None):
    """Each posted row against its block-zero record: the record exists, was opened and names a source; every
    figure of the row stands in it and the row's year in the record that dates it; dated rows run in order between
    1368 and 1700. Returns the problems found."""
    if fault == "posted_unchecked":
        return []
    bad, last = [], None
    for year, when, where, p, src, i, dated_by in rows:
        tag = f"{when} {where[:10]}"
        if not (isinstance(i, int) and 0 <= i < len(recs)):
            bad.append(f"{tag}: no record {i}")
            continue
        r = recs[i]
        if not (r.get("opened") and r.get("source")):
            bad.append(f"{tag}: record {i} not opened or without a source")
        nums = set(re.findall(r"\d+", str(r.get("numbers", "")).replace(",", "")))
        missing = [v for v in (p or ()) if v is not None and str(v) not in nums]
        if missing:
            bad.append(f"{tag}: {missing} not in record {i}")
        if year is not None:
            if not 1368 <= year <= 1700:
                bad.append(f"{tag}: year {year} outside 1368-1700")
            d = r if dated_by is None else (dating or {}).get(dated_by, {})
            if str(year) not in str(d.get("date", "")):
                bad.append(f"{tag}: year {year} not in the record that dates it")
            if last is not None and year < last:
                bad.append(f"{tag}: out of order")
            last = year
    return bad


def check_posted(fault=None):
    """A row with no record behind it, an impossible year and figures no record carries is reported."""
    recs = [{"date": "洪武十六年（1383）", "numbers": "上馬40斤、中馬30斤、下馬20斤", "opened": True, "source": "太祖實錄"}]
    good = [(1383, "1383", "河州", (40, 30, 20), "太祖實錄 156", 0, None)]
    planted = good + [(1300, "1300", "nowhere", (1, 2, 3), "no source", -999, None)]
    wrong_figure = [(1383, "1383", "河州", (45, 30, 20), "太祖實錄 156", 0, None)]
    n = len(posted_check(planted, recs, fault=fault))
    return {"passed": posted_check(good, recs) == [] and n > 0 and len(posted_check(wrong_figure, recs, fault=fault)) > 0,
            "problems_in_the_planted_row": n}


CHECKS["intake"] = check_intake
CHECKS["posted"] = check_posted


def read() -> int:
    print("B141 block two: the readings, printed. Nothing is written.\n")
    print("B141-2  posted official prices (jin per horse, 上/中/下), from the originals")
    for year, when, where, p, src, i, dated_by in POSTED:
        print(f"  {when:24s} {str(p):20s} {where}  [{src}; record {i}]")
    print("  The oft-cited 洪武 120/70/50 is 雅州 1389 alone, and its third grade is 駒馬.")
    print("\nB141-3  private price: no pair matches on place, period, grade and tea -> third state")
    print("  one bound: 李東陽 (c. 1471-72) puts the private price between 80 and 200 jin (the posted 80, the proposed 200)")
    print("  one market estimate, ungraded: 1466 甘州 'a good horse in open trade: tea 100 jin and 15 石 of barley'")
    print("\nB141-4  realized official price, tea paid / horses taken")
    for year, where, tea, horses, note, i in REALIZED:
        print(f"  {year}  {tea / horses:7.1f} jin  {where}  {note}  [record {i}]")
    print("  碉門 (Sichuan), the same channel:")
    for year, what, tea, n, i in DIAOMEN:
        print(f"  {year}  {tea / n:7.1f} jin  {what}  [record {i}]")
    print("\nB141-4  horses by enforcement segment: taken, and what was due (listed, not compared)")
    for seg, what in SEGMENTS:
        lo, hi = (int(x) for x in seg.split("-"))
        rows = [r for r in INTAKE if lo <= r[1] <= hi and (r[1] != lo or seg == SEGMENTS[0][0] or lo != 1449)]
        print(f"  {seg}  {what}")
        for when, a, b, kind, scope, n, per, note, i in rows:
            print(f"      {when:10s} {kind:5s} {n:8.0f} a {per:8s} {scope:13s} {note}  [record {i}]")
    r = intake_reading(INTAKE)
    print("  three offices, horses taken a year (a campaign every three years counted over three):")
    print(f"      under the tallies {', '.join(f'{n:.0f}' for n in r['early'])}; 1497-1502 "
          f"{', '.join(f'{n:.1f}' for n in r['slack'])}; 1503-1506 {', '.join(f'{n:.0f}' for n in r['tight'])}"
          f"  -> fell {r['fell']}, returned {r['returned']}")
    print(f"  stated: {FALL_STATED[0]} {FALL_STATED[1]}")
    print("\nB141-5  the issuer's revisions, with the three-office count before, in and after each")
    for year, when, where, p, src, i, dated_by in POSTED:
        if year is None:
            continue
        b, s, a = intake_around(year)
        print(f"  {when:22s} {str(p):18s} before: " + (f"{b[0]} {b[5]:.0f} a {b[6]}" if b else "none")
              + "; that year: " + (f"{s[5]:.0f} a {s[6]}" if s else "none")
              + "; after: " + (f"{a[0]} {a[5]:.0f} a {a[6]}" if a else "none"))
    print("  1601: 400 yin for 11,900 horses; a yin of 100 jin (洪武四年) gives 3.4 jin a horse, so the")
    print("        1601 yin is not that yin; its weight is still missing")
    return 0


# --------------------------------------------------------------------------
# block three: the record


def build_record() -> dict:
    import json
    from pathlib import Path
    raw = Path(__file__).resolve().parents[1] / "data" / "raw" / "b141" / "_blockzero"
    recs = (json.loads((raw / "horses.json").read_text(encoding="utf-8"))["records"]
            + json.loads((raw / "horses_verify.json").read_text(encoding="utf-8"))["new_records"])
    checks = {n: fn()["passed"] for n, fn in CHECKS.items()}
    faults = {f: any(not fn(fault=f)["passed"] for fn in CHECKS.values()) for f in FAULTS}
    posted_1389 = [p for year, when, where, p, src, i, dated_by in POSTED if year == 1389][0]
    realized = [(y, where, tea / h) for y, where, tea, h, note, i in REALIZED]
    diaomen = [(y, what, tea / n) for y, what, tea, n, i in DIAOMEN]
    taken = intake_reading(INTAKE)
    priv = {"private": json.loads((raw / "private.json").read_text(encoding="utf-8"))["records"],
            "private_verify": json.loads((raw / "private_verify.json").read_text(encoding="utf-8"))["new_records"]}
    dating = {k: priv[k[0]][k[1]] for k in {d for *_, d in POSTED if d}}
    posted_bad = posted_check(POSTED, recs, dating)
    around = [(when, intake_around(year)) for year, when, where, p, src, i, dated_by in POSTED if year is not None]
    comp = [r for r in INTAKE if r[3] == "taken" and r[4] == "three offices"]
    gap = max(((a[2], b[1]) for a, b in zip(comp, comp[1:])), key=lambda g: g[1] - g[0])
    stated = [(y, 1, what, priv[f][i]) for f, i, y, what in DIRECTION]
    sourced = all(r.get("source") and r.get("opened") for *_, r in stated)
    dv = direction_verdict([(y, sg) for y, sg, *_ in stated])
    years = sorted({y for y, *_ in stated})
    reigns = sorted({reign_of(y) for y in years}, key=lambda n: [r[2] for r in REIGNS].index(n))
    crit = [
        {"name": "B141-1  units, grades, pairing and the dose encoder on synthetic data", "kind": "instrument",
         "passed": all(checks.values()) and all(faults.values()),
         "detail": "checks " + ", ".join(f"{k} {v}" for k, v in checks.items()) + "; seeded faults caught: "
                   + ", ".join(f"{k} {v}" for k, v in faults.items())},
        {"name": "B141-2  the oft-cited Hongwu price 120/70/50 against the Veritable Records", "kind": "known_answer",
         "passed": tuple(posted_1389) == (120, 70, 50),
         "detail": f"Taizu shilu 196, 1389: {posted_1389}, at Yazhou/Diaomen for Changhexi merchants, third grade "
                   "'foal', and 'merchants who do not wish may refuse'; the Qin-He price recalled in 1409 is 80/60/40"},
        {"name": "B141-3  official and private price of one horse differ", "kind": "rival", "grid": "unread",
         "rival_shape": "point", "passed": None,
         "rival_premise": "a horse has one price in tea, the same whoever buys it",
         "rival_entailment": "the official price equals the private price at the same place, time, grade and tea: "
                             "the square between the channels is zero",
         "detail": "no pair matches on place, period, grade and tea, so there is no square to read. One bound: "
                   "Li Dongyang (an essay of c. 1471-72) puts the private price between 80 and 200 jin; one ungraded "
                   "market estimate: 1466 Ganzhou, a good horse for 100 jin of tea and 15 shi of barley. The tool, "
                   "when a pair comes: a feature a record does not state matches nothing; a quote is good to half the "
                   "last place of the unit it is printed in; the square is read under each of the three bi weights "
                   "and left unread where they disagree"},
        {"name": "B141-3b  the sign of the gap between the channels, from dated statements", "kind": "rival",
         "grid": {True: "B", None: "unread", False: "C"}[dv["passed"] if sourced else None], "rival_shape": "point",
         "passed": dv["passed"] if sourced else None,
         "rival_premise": "a horse has one price in tea, the same whoever buys it",
         "rival_entailment": "the seller is indifferent between the office and the private trader, so reports of "
                             "which way sellers and tea prices moved when the private channel was open or cut "
                             "carry no common sign: each reign's reports go either way with probability one half",
         "detail": f"{len(stated)} dated statements read in the original (Veritable Records, Yang Yiqing's memorials, "
                   f"Huang Ming jingshi wenbian, Jiubian kao), {len(years)} years, {dv['units']} reigns ("
                   + ", ".join(reigns) + f"); against the framework's direction {dv['against']}; on the rival's "
                   + (f"premise probability {dv['prob']:.4f} by reign" if dv["prob"] is not None else "premise no probability")
                   + f" (by year it would be {0.5 ** len(years):.1e}). The statements: "
                   + "; ".join(f"{y} {what} ({r['source'][:28]})" for y, sg, what, r in stated)
                   + ". Read and not coded: "
                   + "; ".join(why for f, i, why in DIRECTION_NOT_CODED)
                   + ". The sign only: no statement gives the size of the gap, which B141-3 needs"},
        {"name": "B141-4  official intake falls where enforcement slackens and returns where it tightens",
         "kind": "own_reading", "passed": bool(taken["fell"] and taken["returned"]),
         "detail": "horses taken by the three offices, a year (a campaign every three years counted over three): "
                   "under the tallies " + ", ".join(f"{n:.0f}" for n in taken["early"])
                   + " (campaigns of 1398 and 1435); 1497-1502 " + ", ".join(f"{n:.1f}" for n in taken["slack"])
                   + " (5,043 in six years); 1503-1506 " + ", ".join(f"{n:.0f}" for n in taken["tight"])
                   + f" ({sum(taken['tight']):.0f} in four years, {sum(taken['tight']) / len(taken['tight']):.2f} a "
                     f"year, {sum(taken['tight']) / len(taken['tight']) / taken['slack'][0]:.2f} times the six years "
                     "before). Listed and not compared, sums due and parts: "
                   + "; ".join(f"{w} {kind} {n:.0f} a {per} ({note})" for w, a, b, kind, scope, n, per, note, i in INTAKE
                               if not (kind == "taken" and scope == "three offices"))
                   + f". The fall as a censor stated it, {FALL_STATED[0]}: {FALL_STATED[1]}"
                   + ". Realized price, jin per horse: "
                   + "; ".join(f"{y} {v:.1f} ({w})" for y, w, v in realized) + ". Diaomen: "
                   + "; ".join(f"{y} {v:.0f} ({w})" for y, w, v in diaomen)},
        {"name": "B141-5  the issuer's revisions of the posted price", "kind": "own_reading",
         "passed": len(POSTED) > 0 and not posted_bad,
         "detail": "; ".join(f"{when}: {p} {where}" for year, when, where, p, src, i, dated_by in POSTED)
                   + ". Each row against its block-zero record (opened, with a source, its figures and its year in "
                     "it, dated rows in order): " + ("no problem" if not posted_bad else "; ".join(posted_bad))
                   + ". Three-office counts of horses taken, before and after each dated revision: "
                   + "; ".join(f"{when}: before " + (f"{b[0]} {b[5]:.0f} a {b[6]}" if b else "none")
                               + (f", that year {s[5]:.0f} a {s[6]}" if s else "")
                               + ", after " + (f"{a[0]} {a[5]:.0f} a {a[6]}" if a else "none")
                               for when, (b, s, a) in around)
                   + f". No three-office count stands between {gap[0]} and {gap[1]}, so whether the raising of 1490 "
                     "came close upon a fall is not read from counts; the statements are Li Dongyang's essay "
                     "(private trade flourishing since the tallies lapsed, c. 1471-72) and the censor's of 1502. The "
                     "count after the raising of 1490 is the lowest on file; it rose again when Yang Yiqing tightened "
                     "enforcement from 1503. Li Dongyang's stated reason for 200/100: a high posted price starves "
                     "the private market. The raising of 1435 was granted on a request, in a year of high intake"},
        {"name": "B141-6  every horse-count and price record carries its source", "kind": "bookkeeping",
         "passed": len(recs) > 0 and all(r.get("source") or r.get("label") for r in recs),
         "detail": f"{len(recs)} records from block zero, two rounds; private prices found in no Ming period"},
    ]
    config = {"bi_readings": {k: [[s, round(w, 4)] for s, w in v] for k, v in BI_READINGS.items()},
              "gold_tally_chains": list(GOLD_TALLY), "segments": [s for s, _ in SEGMENTS],
              "pairing": "a feature not stated in a record matches nothing",
              "quote_interval": "half the last printed place of the unit the quote is printed in",
              "intake_compared": "horses taken by the three offices; a campaign counted over three years; sums due "
                                 "and quotas listed, not compared"}
    return {"stage": "B141", "config": config, "criteria": crit}


def run() -> int:
    import json
    from pathlib import Path
    rec = build_record()
    path = Path(__file__).resolve().parents[1] / "results" / "b141_tea_horse.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for c in rec["criteria"]:
        print(f"  {({True: 'PASS', False: 'FAIL', None: 'UNREAD'})[c['passed']]}  {c['name']}")
    print(f"\nwrote {path.name}")
    return 0 if all(c["passed"] is not False for c in rec["criteria"]) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.paper:
        sys.exit(paper())
    if a.read:
        sys.exit(read())
    if a.run:
        sys.exit(run())
    ap.print_help()


if __name__ == "__main__":
    main()
