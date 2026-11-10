"""B144 arm F: one whole basket inside one country, by who writes the number.

The basket is the United Kingdom's consumer price index including owner occupiers' housing
costs, April 2025: the weights of its 684 consumption segments and the price quotes the Office
for National Statistics collects in shops across twelve regions. Three things are read.

How the office itself prices the basket: a segment either has quotes collected in the regions,
or it is priced centrally (rents, energy, cars, tuition, telecoms and the like).

Who posts the price: the office marks each quote of a stratified item as coming from a multiple
(ten or more outlets) or an independent. Inside one item the two are compared twice: how far
the regional price follows the region's pay, and how often two quotes carry exactly the same
price.

What is sold: items are grouped by the first two digits of their number, which follow the
groups of the retail prices index. Groups that sell a service on the spot (catering, household
services, leisure services) are set against groups of packaged goods (food, alcohol, tobacco).

  B144-F0  instrument    the quote file, the weights file, the glossary and the pay table say
                         what the reading takes them to say
  B144-F1  own_reading   the basket by how the office prices it: weight with regional quotes,
                         weight priced centrally, weight that is rent
  B144-F2  rival         one price level per region: log p(item, shop, region) = a(item, kind
                         of shop) + m(region), so multiples and independents follow the region
                         alike. Against it: a seller with many outlets writes one number across
                         the regions it covers. Read inside items that have both kinds of shop
  B144-F3  own_reading   inside one item, two quotes from multiples carry the same price more
                         often than two quotes from independents
  B144-F4  own_reading   services sold on the spot follow the region's pay more than packaged
                         goods do

F2 is placed as the first rival criterion of this station is: outside the relabelling range at
the reference point and on one side of zero at every knob point. The other states are read
only where they are the same at every point of their knob grids.

Run from the repo root:
    python experiments/b144_one_basket.py
    python experiments/b144_one_basket.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from b144_two_prices_of_an_hour import RAW, REGIONS, one_file, raw_records, region_lines, sha256, sheet

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "results" / "b144_one_basket.json"

MONTH = ("quotes_2025_04", "202504", "segments_2025_04")
STAT = ("median", "mean")
MIN_CELL = (3, 5)                    # fewest valid quotes a regional cell may hold
LONDON = ("with London", "without London")
WEIGHTING = ("by weight", "each item once")
MIN_MATCHED = 6                      # regions in which an item must have both kinds of shop
MIN_TYPE_QUOTES = (20, 40)           # quotes of each kind an item needs for the count of equal prices
N_PERM = 500                         # relabellings per seed
N_BOOT = 1000
SEEDS = (20261013, 20261014)
MULTIPLE, INDEPENDENT = 1, 2
SHOP_LINES = ("1 = Multiple (10 or more outlets).", "2 = Independents (less than 10 outlets).",
              "3 = Item not stratified by retailer.")
GROUPS = {"21": "food", "22": "catering", "31": "alcoholic drink", "32": "tobacco", "41": "housing",
          "42": "fuel and light", "43": "household goods", "44": "household services",
          "51": "clothing and footwear", "52": "personal goods and services", "61": "motoring",
          "62": "fares and other travel", "63": "leisure goods", "64": "leisure services"}
SERVICE = ("22", "44", "64")
PACKAGED = ("21", "31", "32")

KNOBS_SHOP = [(how, mc, lo) for how in STAT for mc in MIN_CELL for lo in LONDON]
KNOBS_GROUP = [(how, mc, lo, wt) for how in STAT for mc in MIN_CELL for lo in LONDON for wt in WEIGHTING]
STATES_SHOP = {"ours": "at the reference point the independents' slope exceeds the multiples' by more than any "
                       "relabelling of shops returns, and it is the larger one at every knob point",
               "opposite": "the multiples' slope is the larger one, beyond every relabelling at the reference "
                           "point and at every knob point",
               "unread": "inside the relabelling range at the reference point, or the order changes somewhere "
                         "on the knob grid, or too few items"}
MAPPING_SHOP = {"ours": "B", "opposite": "both_unmet", "unread": "not placed"}
STATES_SAME = {"multiples repeat": "two quotes from multiples carry one price more often, beyond every "
                                   "relabelling, at every knob point",
               "independents repeat": "two quotes from independents do, beyond every relabelling, at every knob "
                                      "point",
               "unread": "inside the relabelling range somewhere on the knob grid"}
STATES_GROUP = {"services steeper": "services sold on the spot follow the region's pay more than packaged goods, "
                                    "at every knob point",
                "goods steeper": "packaged goods follow it more, at every knob point",
                "unread": "the order changes somewhere on the knob grid, or a slope is undefined"}


# ----------------------------------------------------------------------------- reading the files
def quotes_all() -> dict:
    """Every valid priced quote of the month; cached, keyed on the source file's hash."""
    src = one_file(RAW / MONTH[0])
    key = {"source": src.name, "sha256": sha256(src)}
    cache = CACHE / "b144_uk_basket_202504.json"
    if cache.exists():
        j = json.loads(cache.read_text(encoding="utf-8"))
        if j.get("key") == key:
            return j
    header, rows = raw_records(src)
    c = {n: header.index(n) for n in ("QUOTE_DATE", "CS_ID", "ITEM_ID", "ITEM_DESC", "VALIDITY", "PRICE", "REGION",
                                      "SHOP_TYPE")}
    kept, dates, n, names = [], Counter(), 0, {}
    for r in rows:
        n += 1
        dates[str(r[c["QUOTE_DATE"]])] += 1
        price = float(r[c["PRICE"]] or 0)
        if str(r[c["VALIDITY"]]).strip().lower() == "true" and price > 0:
            item = str(r[c["ITEM_ID"]])
            names[item] = [str(r[c["CS_ID"]]), str(r[c["ITEM_DESC"]]).strip()]
            kept.append([item, price, int(float(r[c["REGION"]] or 0)), int(float(r[c["SHOP_TYPE"]] or 0))])
    out = {"key": key, "rows_in_file": n, "quote_dates": dict(dates), "names": names, "rows": kept}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out


def load() -> dict:
    q = quotes_all()
    items = {}
    for item, price, region, shop in q["rows"]:
        it = items.setdefault(item, {"price": [], "region": [], "shop": []})
        it["price"].append(price)
        it["region"].append(region)
        it["shop"].append(shop)
    for item, it in items.items():
        it.update(price=np.array(it["price"], float), region=np.array(it["region"], int),
                  shop=np.array(it["shop"], int), cs=q["names"][item][0], desc=q["names"][item][1])
    with open(one_file(RAW / MONTH[2]), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    weights = {r["CS_ID"]: {"desc": r["CS_DESC"].strip(), "cpih": float(r["CPIH_WEIGHT"] or 0)} for r in rows}
    pay = region_lines(sheet(one_file(RAW / "ashe3"), "Table 3.6a"))
    level = {rc: {how: math.log(pay[name][how]) for how in STAT} for rc, (_t, name) in REGIONS.items()
             if pay.get(name, {}).get("median") and pay.get(name, {}).get("mean")}
    import openpyxl
    wb = openpyxl.load_workbook(one_file(RAW / "glossary_2025"), read_only=True, data_only=True)
    cells_ = [str(x).strip() for r in wb.worksheets[0].iter_rows(values_only=True) for x in r if x is not None]
    return {"items": items, "weights": weights, "level": level,
            "files": {"quote_dates": q["quote_dates"], "rows_in_file": q["rows_in_file"],
                      "index_dates": sorted({r["INDEX_DATE"] for r in rows}), "glossary": cells_}}


# ----------------------------------------------------------------------------- estimators
def cells(it: dict, how: str, min_cell: int, london: str, shop=None) -> dict:
    """region -> log of the median or mean price of the quotes there, where there are enough."""
    memo = it.setdefault("_cells", {})
    key = (how, min_cell, london, shop)
    if key in memo:
        return memo[key]
    out = {}
    for rc in REGIONS:
        if rc == 2 and london == "without London":
            continue
        sel = it["region"] == rc
        if shop is not None:
            sel = sel & (it["shop"] == shop)
        if int(sel.sum()) >= min_cell:
            p = it["price"][sel]
            out[rc] = math.log(float(np.median(p)) if how == "median" else float(p.mean()))
    memo[key] = out
    return out


def pooled(units: list, level: dict, how: str, mult=None) -> float:
    """Slope of the regional log price on the region's log pay, each unit demeaned; units carry weights."""
    sxy = sxx = 0.0
    for cl, w in units:
        rcs = [rc for rc in cl if rc in level and (mult is None or mult.get(rc, 0) > 0)]
        if len(rcs) < 2:
            continue
        m = np.array([1.0 if mult is None else float(mult[rc]) for rc in rcs])
        x = np.array([level[rc][how] for rc in rcs])
        y = np.array([cl[rc] for rc in rcs])
        dx, dy = x - (m * x).sum() / m.sum(), y - (m * y).sum() / m.sum()
        sxy += w * float((m * dx * dy).sum())
        sxx += w * float((m * dx * dx).sum())
    return sxy / sxx if sxx > 0 else math.nan


def group_of(item: str) -> str:
    return item[:2]


def item_weight(data: dict, item: str) -> float:
    cs = data["items"][item]["cs"]
    share = sum(1 for it in data["items"].values() if it["cs"] == cs)
    return data["weights"].get(cs, {}).get("cpih", 0.0) / max(share, 1)


def group_units(data: dict, knob, groups) -> list:
    how, min_cell, london, weighting = knob
    out = []
    for item, it in data["items"].items():
        if group_of(item) in groups:
            w = data["_w"][item] if weighting == "by weight" else 1.0
            if w > 0:
                out.append((cells(it, how, min_cell, london), w))
    return out


def group_reading(data: dict, knob) -> dict:
    how = knob[0]
    by = {g: pooled(group_units(data, knob, (g,)), data["level"], how) for g in GROUPS}
    s = pooled(group_units(data, knob, SERVICE), data["level"], how)
    p = pooled(group_units(data, knob, PACKAGED), data["level"], how)
    every = pooled(group_units(data, knob, tuple(GROUPS)), data["level"], how)
    return {"stat": how, "min_cell": knob[1], "london": knob[2], "weighting": knob[3], "groups": by, "services": s,
            "packaged": p, "gap": s - p, "all_items": every}


def group_resamples(data: dict, knob) -> dict:
    how = knob[0]
    us, up = group_units(data, knob, SERVICE), group_units(data, knob, PACKAGED)
    codes = sorted(data["level"])
    out = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        gaps = []
        for _ in range(N_BOOT):
            mult = Counter(int(codes[i]) for i in rng.integers(0, len(codes), size=len(codes)))
            gaps.append(pooled(us, data["level"], how, mult) - pooled(up, data["level"], how, mult))
        out.append([float(np.nanquantile(gaps, q)) for q in (0.025, 0.975)])
    return {"gap": out[0], "second_seed": out[1]}


def shop_units(data: dict, knob) -> list:
    """(item, cells of multiples, cells of independents) on the regions where the item has both."""
    how, min_cell, london = knob
    out = []
    for item in sorted(data["items"]):
        it = data["items"][item]
        if not ((it["shop"] == MULTIPLE).any() and (it["shop"] == INDEPENDENT).any()):
            continue
        a, b = cells(it, how, min_cell, london, MULTIPLE), cells(it, how, min_cell, london, INDEPENDENT)
        both = sorted(set(a) & set(b) & set(data["level"]))
        if len(both) >= MIN_MATCHED:
            out.append((item, {rc: a[rc] for rc in both}, {rc: b[rc] for rc in both}))
    return out


def shop_reading(data: dict, knob) -> dict:
    how = knob[0]
    units = shop_units(data, knob)
    bm = pooled([(u[1], 1.0) for u in units], data["level"], how)
    bi = pooled([(u[2], 1.0) for u in units], data["level"], how)
    return {"stat": how, "min_cell": knob[1], "london": knob[2], "items": len(units),
            "cells": sum(len(u[1]) for u in units), "multiples": bm, "independents": bi, "gap": bi - bm}


def shop_relabelled(data: dict, knob) -> dict:
    """The gap when the kind of shop is relabelled inside every item and region, keeping the counts."""
    how, _min_cell, _london = knob
    units = shop_units(data, knob)
    if not units:
        return {"null_min": math.nan, "null_max": math.nan}
    null = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        num, den = np.zeros(N_PERM), 0.0
        for item, a, _b in units:
            it = data["items"][item]
            rcs = sorted(a)
            x = np.array([data["level"][rc][how] for rc in rcs])
            dx = x - x.mean()
            den += float((dx * dx).sum())
            for k, rc in enumerate(rcs):
                sel = it["region"] == rc
                p1, p2 = it["price"][sel & (it["shop"] == MULTIPLE)], it["price"][sel & (it["shop"] == INDEPENDENT)]
                mixed = rng.permuted(np.tile(np.concatenate([p1, p2]), (N_PERM, 1)), axis=1)
                f = np.median if how == "median" else np.mean
                y1, y2 = np.log(f(mixed[:, :len(p1)], axis=1)), np.log(f(mixed[:, len(p1):], axis=1))
                num += dx[k] * (y2 - y1)
        null += list(num / den)
    return {"null_min": float(min(null)), "null_max": float(max(null))}


def state_shop(grid: list, null: dict) -> str:
    if not grid or any(not math.isfinite(g["gap"]) for g in grid) or not math.isfinite(null.get("null_max", math.nan)):
        return "unread"
    ref = grid[0]["gap"]
    if ref > null["null_max"] and all(g["gap"] > 0 for g in grid):
        return "ours"
    if ref < null["null_min"] and all(g["gap"] < 0 for g in grid):
        return "opposite"
    return "unread"


def same_price(prices) -> float:
    """Chance that two quotes drawn without replacement carry exactly the same price, to the penny."""
    n = len(prices)
    if n < 2:
        return math.nan
    return sum(k * (k - 1) for k in Counter(np.round(prices, 2)).values()) / (n * (n - 1))


def same_reading(data: dict, min_quotes: int) -> dict:
    diffs, m, i, null = [], [], [], np.zeros(N_PERM * len(SEEDS))
    used = 0
    for item in sorted(data["items"]):
        it = data["items"][item]
        p1, p2 = it["price"][it["shop"] == MULTIPLE], it["price"][it["shop"] == INDEPENDENT]
        if len(p1) < min_quotes or len(p2) < min_quotes:
            continue
        used += 1
        a, b = same_price(p1), same_price(p2)
        m.append(a)
        i.append(b)
        diffs.append(a - b)
        both = np.concatenate([p1, p2])
        k = 0
        for seed in SEEDS:
            rng = np.random.default_rng(seed + used)
            for _ in range(N_PERM):
                s = rng.permutation(both)
                null[k] += same_price(s[:len(p1)]) - same_price(s[len(p1):])
                k += 1
    if not used:
        return {"min_quotes": min_quotes, "items": 0, "gap": math.nan, "null_min": math.nan, "null_max": math.nan}
    null /= used
    return {"min_quotes": min_quotes, "items": used, "multiples": float(np.mean(m)), "independents": float(np.mean(i)),
            "gap": float(np.mean(diffs)), "null_min": float(null.min()), "null_max": float(null.max())}


def composition(data: dict) -> dict:
    local = {it["cs"] for it in data["items"].values() if (it["region"] != 1).any()}
    w = data["weights"]
    total = sum(v["cpih"] for v in w.values())
    with_quotes = sum(v["cpih"] for k, v in w.items() if k in local)
    rest = {k: v for k, v in w.items() if k not in local}
    rent = sum(v["cpih"] for v in rest.values() if "RENT" in v["desc"].upper())
    top = sorted(rest.items(), key=lambda kv: -kv[1]["cpih"])[:14]
    groups = {}
    for item in data["items"]:
        groups[group_of(item)] = groups.get(group_of(item), 0.0) + data["_w"][item]
    return {"segments": len(w), "weight_in_file": total, "with_regional_quotes": with_quotes,
            "priced_centrally": total - with_quotes, "of_which_rent": rent,
            "segments_with_regional_quotes": len(local & set(w)), "largest_priced_centrally":
                [[v["desc"], v["cpih"]] for _k, v in top], "weight_of_quoted_groups": groups}


# ----------------------------------------------------------------------------- criteria
def c_f0(data: dict):
    problems = []
    f = data["files"]
    if set(f["quote_dates"]) != {MONTH[1]}:
        problems.append(f"the quote file holds dates {sorted(f['quote_dates'])}")
    if f["index_dates"] != [MONTH[1]]:
        problems.append(f"the weights file holds dates {f['index_dates']}")
    for ln in SHOP_LINES:
        if ln not in f["glossary"]:
            problems.append(f"the glossary does not say '{ln}'")
    if len(data["weights"]) < 600:
        problems.append(f"only {len(data['weights'])} segments carry a weight")
    orphans = sorted({it["cs"] for it in data["items"].values()} - set(data["weights"]))
    if orphans:
        problems.append(f"{len(orphans)} quoted segments have no weight, the first {orphans[0]}")
    missing = [name for rc, (_t, name) in REGIONS.items() if rc not in data["level"]]
    if missing:
        problems.append(f"no pay line for {missing}")
    strange = sorted({int(s) for it in data["items"].values() for s in set(it["shop"].tolist())} - {1, 2, 3})
    if strange:
        problems.append(f"shop kinds outside the glossary: {strange}")
    total = sum(v["cpih"] for v in data["weights"].values())
    if not 900 <= total <= 1000.5:
        problems.append(f"the weights add to {total:.1f} parts in a thousand")
    n = sum(len(it["price"]) for it in data["items"].values())
    detail = (f"{f['rows_in_file']:,} rows, {n:,} valid quotes of {len(data['items'])} items in "
              f"{len({it['cs'] for it in data['items'].values()})} segments; {len(data['weights'])} segments carry "
              f"a weight, adding to {total:.1f} parts in a thousand of the index; {len(data['level'])} regions with "
              f"a pay line; "
              + ("; ".join(problems) if problems else "dates, shop kinds and joins as expected"))
    return not problems, detail, {"problems": problems}


def c_f1(data: dict):
    c = composition(data)
    t = c["weight_in_file"]
    ok = t > 0 and c["with_regional_quotes"] > 0 and c["priced_centrally"] > 0
    top = "; ".join(f"{d.lower()} {w:.1f}" for d, w in c["largest_priced_centrally"][:10])
    detail = (f"of {t:.1f} parts in the file, {c['with_regional_quotes']:.1f} "
              f"({100 * c['with_regional_quotes'] / t if t else math.nan:.1f}%) are in segments with quotes collected "
              f"in the regions and {c['priced_centrally']:.1f} ({100 * c['priced_centrally'] / t if t else math.nan:.1f}"
              f"%) in segments priced centrally, of which rent, actual and imputed, {c['of_which_rent']:.1f} "
              f"({100 * c['of_which_rent'] / t if t else math.nan:.1f}%). Largest priced centrally: {top}")
    return ok, detail, c


def c_f2(grid: list, null: dict):
    state = state_shop(grid, null)
    cell = MAPPING_SHOP[state]
    passed = None if cell == "not placed" else True
    g0 = grid[0] if grid else {"items": 0, "cells": 0, "multiples": math.nan, "independents": math.nan,
                               "gap": math.nan}
    gaps = [g["gap"] for g in grid if math.isfinite(g["gap"])] or [0.0]
    detail = (f"{g0['items']} items with both kinds of shop in {MIN_MATCHED} or more regions, {g0['cells']} regional "
              f"cells: prices of multiples follow the region's pay by {g0['multiples']:+.3f}, of independents by "
              f"{g0['independents']:+.3f}, gap {g0['gap']:+.3f}; relabelling the kind of shop inside every item and "
              f"region returns {null.get('null_min', math.nan):+.3f} to {null.get('null_max', math.nan):+.3f} in "
              f"{N_PERM * len(SEEDS)} relabellings; over {len(grid)} knob points the gap is {np.nanmin(gaps):+.3f} to "
              f"{np.nanmax(gaps):+.3f}, positive at {sum(g["gap"] > 0 for g in grid)} -> {state}")
    return passed, detail, {"grid": "unread" if cell == "not placed" else cell, "state": state}


def c_f3(same: list):
    def one(s):
        if not math.isfinite(s["gap"]):
            return "unread"
        return "multiples repeat" if s["gap"] > s["null_max"] else (
            "independents repeat" if s["gap"] < s["null_min"] else "unread")
    states = [one(s) for s in same]
    state = states[0] if len(set(states)) == 1 else "unread"
    s0 = same[0]
    detail = (f"{s0['items']} items with {s0['min_quotes']} or more quotes of each kind: two quotes from multiples "
              f"carry the same price with chance {s0.get('multiples', math.nan):.3f}, two from independents "
              f"{s0.get('independents', math.nan):.3f}, gap {s0['gap']:+.3f}; relabelling the kind of shop inside "
              f"each item returns {s0['null_min']:+.3f} to {s0['null_max']:+.3f}; with "
              + "; ".join(f"{s['min_quotes']} quotes, {s['items']} items, gap {s['gap']:+.3f} against "
                          f"{s['null_max']:+.3f}" for s in same[1:]) + f" -> {state}")
    passed = True if state == "multiples repeat" else (False if state == "independents repeat" else None)
    return passed, detail, {"state": state}


def c_f4(grid: list, boot: dict):
    gaps = [g["gap"] for g in grid]
    if any(not math.isfinite(x) for x in gaps):
        state = "unread"
    elif all(x > 0 for x in gaps):
        state = "services steeper"
    elif all(x < 0 for x in gaps):
        state = "goods steeper"
    else:
        state = "unread"
    g0 = grid[0]
    by = "; ".join(f"{GROUPS[g]} {g0['groups'][g]:+.2f}" for g in sorted(GROUPS, key=lambda k: g0["groups"][k]
                                                                         if math.isfinite(g0["groups"][k]) else 9)
                   if math.isfinite(g0["groups"][g]))
    detail = (f"services sold on the spot {g0['services']:+.3f}, packaged goods {g0['packaged']:+.3f}, gap "
              f"{g0['gap']:+.3f} ({min(gaps):+.3f} to {max(gaps):+.3f} over {len(gaps)} knob points; region "
              f"resamples {boot['gap'][0]:+.3f} to {boot['gap'][1]:+.3f}); every quoted item together "
              f"{g0['all_items']:+.3f}. By group: {by} -> {state}")
    passed = True if state == "services steeper" else (False if state == "goods steeper" else None)
    return passed, detail, {"state": state}


RIVALS = {
    "B144-F2": {"rival_shape": "point prediction",
                "rival_premise": "A region has one price level: the price of an item in a shop is the item's own "
                                 "level in that kind of shop times the region's, log p(item, shop, region) = "
                                 "a(item, kind of shop) + m(region).",
                "rival_entailment": "Then inside one item the prices of multiples and of independents follow the "
                                    "region by the same amount, and the difference of their slopes is what a "
                                    "relabelling of the kind of shop inside every item and region gives."},
}
KINDS = {"B144-F0": "instrument", "B144-F1": "own_reading", "B144-F2": "rival", "B144-F3": "own_reading",
         "B144-F4": "own_reading"}
STATEMENTS = {
    "B144-F0": "The quote file, the weights file, the glossary and the pay table say what the reading takes "
               "them to say.",
    "B144-F1": "The basket splits into a part with quotes collected in the regions and a part priced centrally, "
               "and the two are weighed.",
    "B144-F2": "Inside one item the prices of independents follow the region's pay more than the prices of "
               "multiples. Passing means the rival is wrong here (`11e`).",
    "B144-F3": "Inside one item, two quotes from multiples carry exactly the same price more often than two "
               "quotes from independents.",
    "B144-F4": "Services sold on the spot follow the region's pay more than packaged goods do.",
}


def r4(x):
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else round(float(x), 4)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data: dict):
    data["_w"] = {item: item_weight(data, item) for item in data["items"]}
    sg = [shop_reading(data, k) for k in KNOBS_SHOP]
    null = shop_relabelled(data, KNOBS_SHOP[0])
    same = [same_reading(data, mq) for mq in MIN_TYPE_QUOTES]
    gg = [group_reading(data, k) for k in KNOBS_GROUP]
    gboot = group_resamples(data, KNOBS_GROUP[0])
    res = {"B144-F0": c_f0(data), "B144-F1": c_f1(data), "B144-F2": c_f2(sg, null), "B144-F3": c_f3(same),
           "B144-F4": c_f4(gg, gboot)}
    return res, {"shop_grid": sg, "shop_relabelled": null, "same_price": same, "group_grid": gg,
                 "group_resamples": gboot}


def record_of(data: dict, res: dict, objs: dict) -> dict:
    examples = {}
    for item in sorted(data["items"]):
        examples.setdefault(group_of(item), [])
        if len(examples[group_of(item)]) < 4:
            examples[group_of(item)].append(data["items"][item]["desc"])
    both = [data["items"][u[0]]["desc"] for u in shop_units(data, KNOBS_SHOP[0])]
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d,
                      **({**RIVALS[n], "grid": o["grid"]} if n in RIVALS else {})}
                     for n, (p, d, o) in res.items()],
        "mapping": {"states_of_the_shops": STATES_SHOP, "shop_states_to_cells": MAPPING_SHOP,
                    "states_of_equal_prices": STATES_SAME, "states_of_the_groups": STATES_GROUP},
        "objects": {**r4(objs), "states": {n: r4(o) for n, (_, _, o) in res.items()},
                    "items_in_each_group": {g: sum(group_of(i) == g for i in data["items"]) for g in GROUPS},
                    "first_items_of_each_group": examples, "items_with_both_kinds_of_shop": both},
        "config": {"raw": "data/raw/b144/uk", "fetched_by": "experiments/b144_fetch.py --only uk",
                   "month": MONTH[1], "groups": GROUPS, "service_groups": list(SERVICE),
                   "packaged_groups": list(PACKAGED),
                   "knobs": {"stat": list(STAT), "min_cell": list(MIN_CELL), "london": list(LONDON),
                             "weighting": list(WEIGHTING), "quotes_of_each_kind": list(MIN_TYPE_QUOTES)},
                   "min_matched_regions": MIN_MATCHED, "relabellings_per_seed": N_PERM, "n_boot": N_BOOT,
                   "seeds": list(SEEDS)},
    }


# ----------------------------------------------------------------------------- selftest
def toy(service=0.8, packaged=0.0, mult=0.1, indep=0.7, noise=0.03, grid_mult=0.5, grid_indep=0.0, seed=3,
        per_cell=7) -> dict:
    """A country with planted regional slopes by group and by kind of shop, and planted price points."""
    rng = np.random.default_rng(seed)
    level = {rc: {how: math.log(17.0) + (0.3 if rc == 2 else 0.03 * ((rc % 5) - 2)) for how in STAT}
             for rc in REGIONS}
    mid = float(np.mean([v["median"] for v in level.values()]))
    items, weights = {}, {}

    def quotes(base, slope, shop, step):
        p, r, s = [], [], []
        for rc in REGIONS:
            for _ in range(per_cell):
                v = base * math.exp(slope * (level[rc]["median"] - mid) + rng.normal(0, noise))
                p.append(round(v / step) * step if step else v)
                r.append(rc)
                s.append(shop)
        return p, r, s

    k = 0
    for g in GROUPS:
        slope = service if g in SERVICE else (packaged if g in PACKAGED else 0.3)
        for j in range(6):
            item = f"{g}{j:04d}"
            base = 5.0 + 3.0 * k
            k += 1
            if g == "43":
                a, b = quotes(base, mult, MULTIPLE, grid_mult), quotes(base * 1.1, indep, INDEPENDENT, grid_indep)
                p, r, s = a[0] + b[0], a[1] + b[1], a[2] + b[2]
            else:
                p, r, s = quotes(base, slope, 3, 0.0)
            items[item] = {"price": np.array(p, float), "region": np.array(r, int), "shop": np.array(s, int),
                           "cs": item, "desc": f"item {item}"}
            weights[item] = {"desc": f"item {item}", "cpih": 1.0}
    for name, w in (("IMPUTED RENTS", 150.0), ("ELECTRICITY", 13.0)):
        weights[name] = {"desc": name, "cpih": w}
    for n in range(600):                                   # the rest of a basket, priced centrally
        weights[f"X{n:03d}"] = {"desc": "a segment priced centrally", "cpih": 1.2}
    return {"items": items, "weights": weights, "level": level,
            "files": {"quote_dates": {MONTH[1]: 1}, "rows_in_file": 1, "index_dates": [MONTH[1]],
                      "glossary": list(SHOP_LINES)}}


def selftest() -> None:
    assert SHOP_LINES[MULTIPLE - 1].startswith(f"{MULTIPLE} = Multiple"), "the code of a multiple is the glossary's"
    assert SHOP_LINES[INDEPENDENT - 1].startswith(f"{INDEPENDENT} = Independents")
    assert abs(same_price([1.0, 1.0, 2.0, 2.0]) - 4 / 12) < 1e-12 and same_price([1.0, 2.0, 3.0]) == 0.0
    assert same_price([5.0, 5.0]) == 1.0 and math.isnan(same_price([5.0]))
    assert abs(same_price([1.004, 1.001]) - 1.0) < 1e-12, "prices are compared to the penny"
    one = {"price": np.array([1.0, 2.0, 4.0, 8.0, 8.0, 8.0]), "region": np.array([2, 2, 2, 3, 3, 3]),
           "shop": np.array([1, 1, 2, 2, 2, 2])}
    assert cells(one, "median", 3, "with London") == {2: math.log(2.0), 3: math.log(8.0)}
    assert cells(one, "mean", 3, "without London") == {3: math.log(8.0)}
    assert cells(one, "median", 3, "with London", shop=2) == {3: math.log(8.0)}
    assert cells(one, "median", 4, "with London") == {}

    # planted slopes come back exactly when nothing is noisy and no price is rounded
    exact = toy(noise=0.0, grid_mult=0.0)
    exact["_w"] = {i: item_weight(exact, i) for i in exact["items"]}
    for knob in KNOBS_GROUP:
        g = group_reading(exact, knob)
        assert abs(g["services"] - 0.8) < 1e-9 and abs(g["packaged"] - 0.0) < 1e-9, (knob, g)
        assert abs(g["groups"]["52"] - 0.3) < 1e-9
    for knob in KNOBS_SHOP:
        s = shop_reading(exact, knob)
        assert abs(s["multiples"] - 0.1) < 1e-9 and abs(s["independents"] - 0.7) < 1e-9 and s["items"] == 6, s
    lop = toy(noise=0.0, grid_mult=0.0)
    lop["_w"] = {i: 1.0 for i in lop["items"]}
    big = lop["items"]["220005"]                     # the dearest service item loses its low-pay regions
    keep = np.isin(big["region"], (2, 3, 12))
    for key in ("price", "region", "shop"):
        big[key] = big[key][keep]
    assert abs(group_reading(lop, KNOBS_GROUP[0])["services"] - 0.8) < 1e-9, "items are demeaned before the slope"
    heavy = toy(noise=0.0, grid_mult=0.0)
    heavy["weights"]["220000"]["cpih"] = 50.0
    for key in ("price",):
        it = heavy["items"]["220000"]
        it[key] = it[key] * np.exp(1.0 * (np.array([heavy["level"][rc]["median"] for rc in it["region"]])
                                          - np.mean([v["median"] for v in heavy["level"].values()])))
    heavy["_w"] = {i: item_weight(heavy, i) for i in heavy["items"]}
    by_w = group_reading(heavy, ("median", 3, "with London", "by weight"))["groups"]["22"]
    once = group_reading(heavy, ("median", 3, "with London", "each item once"))["groups"]["22"]
    assert by_w > once + 0.3, "the weight of an item enters the weighted slope and not the other"
    assert abs(item_weight(heavy, "220000") - 50.0) < 1e-12

    # the country as it is expected to be read
    res, _ = run(toy())
    assert res["B144-F0"][0], res["B144-F0"][1]
    assert res["B144-F1"][0] and abs(res["B144-F1"][2]["of_which_rent"] - 150.0) < 1e-9
    assert abs(res["B144-F1"][2]["with_regional_quotes"] - 84.0) < 1e-9
    assert res["B144-F2"][0] is True and res["B144-F2"][2]["grid"] == "B", res["B144-F2"][1]
    assert res["B144-F3"][0] is True, res["B144-F3"][1]
    assert res["B144-F4"][0] is True

    # F2: shops that follow the region alike are not placed; the opposite order is not ours
    alike = run(toy(mult=0.4, indep=0.4))[0]["B144-F2"]
    assert alike[0] is None and alike[2]["grid"] == "unread", alike[1]
    back = run(toy(mult=0.7, indep=0.1))[0]["B144-F2"]
    assert back[2]["state"] == "opposite" and back[2]["grid"] == "both_unmet", back[1]
    assert state_shop([{"gap": 0.5}, {"gap": -0.1}], {"null_min": -0.2, "null_max": 0.2}) == "unread"
    assert state_shop([{"gap": 0.1}, {"gap": 0.3}], {"null_min": -0.2, "null_max": 0.2}) == "unread"
    assert state_shop([], {"null_min": -0.2, "null_max": 0.2}) == "unread"
    none = toy()
    for it in none["items"].values():
        it["shop"] = np.full(len(it["shop"]), 3)
    assert run(none)[0]["B144-F2"][0] is None, "no item with both kinds of shop is not a reading"

    # F3: the other kind repeats; neither repeats; both repeat alike
    assert run(toy(grid_mult=0.0, grid_indep=0.5))[0]["B144-F3"][0] is False
    assert run(toy(grid_mult=0.0, grid_indep=0.0))[0]["B144-F3"][0] is None
    assert run(toy(mult=0.4, indep=0.4, grid_mult=0.5, grid_indep=0.5))[0]["B144-F3"][0] is None, \
        "two kinds of shop on the same price points are not told apart"

    # F1: a segment quoted only from a head office is not one with quotes collected in the regions
    desk = toy()
    for key, value in (("region", 1),):
        desk["items"]["630000"][key] = np.full(len(desk["items"]["630000"][key]), value)
    desk["_w"] = {i: item_weight(desk, i) for i in desk["items"]}
    assert abs(composition(desk)["with_regional_quotes"] - 83.0) < 1e-9

    # F4: goods follow the region more; neither does
    assert run(toy(service=0.0, packaged=0.8))[0]["B144-F4"][0] is False
    assert run(toy(service=0.3, packaged=0.3, noise=0.0, grid_mult=0.0))[0]["B144-F4"][0] is None

    # F0: each thing it reads, broken once
    def broken(change):
        d = toy()
        if change == "month":
            d["files"]["quote_dates"] = {"202503": 1}
        elif change == "weights month":
            d["files"]["index_dates"] = ["202504", "202505"]
        elif change == "glossary":
            d["files"]["glossary"] = list(SHOP_LINES[:2])
        elif change == "few":
            d["weights"] = dict(list(d["weights"].items())[:20])
        elif change == "region":
            del d["level"][11]
        elif change == "shop":
            d["items"]["210000"]["shop"][0] = 7
        elif change == "sum":
            d["weights"]["IMPUTED RENTS"]["cpih"] = 5000.0
        elif change == "orphan":
            del d["weights"]["210003"]
        return d
    for change in ("month", "weights month", "glossary", "few", "region", "shop", "sum", "orphan"):
        assert not c_f0(broken(change))[0], f"F0 must fail on {change}"
    print("selftest ok: planted slopes and repeats come back, every flag fails on its planted input, and what "
          "does not differ is not placed")


def main() -> int:
    data = load()
    res, objs = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    OUT.write_text(json.dumps(record_of(data, res, objs), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-F0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
