"""B144 arm L: predicting the prices of cities the model has not seen.

The arms before this one read slopes. This one uses them: the price of every item in a city is
predicted from information that is not the city's own prices, and the predictions are scored on
cities of countries left out of the fit (five folds, countries kept whole). Four ways to convert:

  law of one price       log p = a(item)                                    one dollar price everywhere
  one price level        log p = a(item) + log PLI(country)                 the scalar conversion in use:
                                                                            the World Bank's private
                                                                            consumption PPP over the
                                                                            official exchange rate, 2022
  one wage slope         log p = a(item) + b log w(city)                    richer places dearer, alike
  who writes the price   log p = a(item) + b(class of item) log w(city)     six classes of arm A, each
                                                                            with its own slope
  and per item           log p = a(item) + b(item) log w(city)              55 slopes, for reference

Every parameter is fitted on the training countries only. The scores are the root mean square
error of the log price over every held-out city and item, and the median absolute error. Knob
grid: two assignments of countries to folds, the city's own salary or its country's median salary,
and the two scores.

  B144-L0  known_answer  the official price level predicts dollar prices better than one dollar
                         price everywhere: the scalar conversion does what it is used for
  B144-L1  rival         one price level per country, log p = a(item) + log PLI(country). Against
                         it: the price of an item follows the wage by an amount its writer sets.
                         The class model's error is below the price level's at every knob point,
                         and the country-block resamples of the ratio stay below one
  B144-L2  own_reading   six class slopes predict better than one common wage slope at every knob
                         point; the share of the per-item improvement the classes capture is printed
  B144-L4  own_reading   the official price level, corrected by each class's own response to the
                         wage, predicts better than the price level alone: the tool in use, mended
  B144-L3  own_reading   inside countries, a model with one slope across countries and another
                         inside them predicts held-out cities better than one slope for both

Run from the repo root:
    python experiments/b144_held_out.py
    python experiments/b144_held_out.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

import b144_wage_coordinates as arm_a

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "data" / "raw" / "b144" / "worldbank"
OUT = ROOT / "results" / "b144_held_out.json"

ALIASES = {"Bahamas": "Bahamas, The", "Bosnia And Herzegovina": "Bosnia and Herzegovina", "Brunei": "Brunei Darussalam",
           "Cape Verde": "Cabo Verde", "Congo": "Congo, Rep.", "Czech Republic": "Czechia", "Egypt": "Egypt, Arab Rep.",
           "Gambia": "Gambia, The", "Hong Kong": "Hong Kong SAR, China", "Iran": "Iran, Islamic Rep.",
           "Ivory Coast": "Cote d'Ivoire", "Kosovo (Disputed Territory)": "Kosovo", "Kyrgyzstan": "Kyrgyz Republic",
           "Laos": "Lao PDR", "Russia": "Russian Federation", "Saint Lucia": "St. Lucia", "Slovakia": "Slovak Republic",
           "South Korea": "Korea, Rep.", "Turkey": "Turkiye", "Vietnam": "Viet Nam",
           "Trinidad And Tobago": "Trinidad and Tobago", "Saint Vincent And The Grenadines": "St. Vincent and the Grenadines",
           "Sao Tome And Principe": "Sao Tome and Principe", "Swaziland": "Eswatini", "Syria": "Syrian Arab Republic",
           "Venezuela": "Venezuela, RB", "Yemen": "Yemen, Rep."}
FOLDS = 5
FOLD_SEEDS = ("a", "b")
WAGE_INPUT = ("the city's salary", "the country's median salary")
SCORES = ("root mean square", "median absolute")
N_BOOT = 1000
SEED = 20261014
MIN_CITIES_INSIDE = 8


def read_pli() -> dict:
    def get(ind):
        j = json.loads((WB / f"{ind}_2022.json").read_text(encoding="utf-8"))
        return {r["country"]["value"]: r["value"] for r in j[1] if r["value"] is not None}
    ppp, fx = get("PA.NUS.PRVT.PP"), get("PA.NUS.FCRF")
    return {k: ppp[k] / fx[k] for k in ppp if k in fx and fx[k] > 0}


def load() -> dict:
    d = arm_a.load()
    pli = read_pli()
    logpli = np.array([math.log(pli[ALIASES.get(c, c)]) if ALIASES.get(c, c) in pli else math.nan
                       for c in d["countries"]])
    cls = np.empty(len(arm_a.ITEMS), dtype=object)
    for k, cols in arm_a.COLS.items():
        cls[cols] = k
    return {"g": d["g"], "w": d["w"], "p": d["p"], "countries": d["countries"], "logpli": logpli,
            "cls": cls, "items": arm_a.ITEMS}


def fold_of(countries: list, seed: str) -> np.ndarray:
    return np.array([int(hashlib.sha256((seed + c).encode()).hexdigest(), 16) % FOLDS for c in countries])


def country_median_wage(g: np.ndarray, w: np.ndarray) -> np.ndarray:
    med = {k: float(np.median(w[g == k])) for k in np.unique(g)}
    return np.array([med[k] for k in g])


def fit_predict(data: dict, train: np.ndarray, test: np.ndarray, x: np.ndarray) -> dict:
    """Predicted log prices of the test cities under the five models, every parameter from the train cities."""
    p, cls, items = data["p"], data["cls"], data["items"]
    lp = data["logpli"][data["g"]]
    out = {k: np.full((test.sum(), len(items)), math.nan) for k in
           ("law of one price", "one price level", "one wage slope", "who writes the price", "per item",
            "price level corrected by class")}
    xt, xs = x[train], x[test]
    pooled_num = pooled_den = 0.0
    a_slope, b_item = {}, {}
    for j in range(len(items)):
        y = p[train, j]
        ok = ~np.isnan(y)
        if ok.sum() < 10:
            continue
        out["law of one price"][:, j] = np.mean(y[ok])
        okl = ok & ~np.isnan(lp[train])
        out["one price level"][:, j] = np.mean(y[okl] - lp[train][okl]) + lp[test]
        dx, dy = xt[ok] - xt[ok].mean(), y[ok] - y[ok].mean()
        b = float((dx * dy).sum() / (dx * dx).sum())
        b_item[j] = (y[ok].mean(), xt[ok].mean(), b, float((dx * dy).sum()), float((dx * dx).sum()))
        pooled_num += b_item[j][3]
        pooled_den += b_item[j][4]
        out["per item"][:, j] = y[ok].mean() + b * (xs - xt[ok].mean())
    common = pooled_num / pooled_den
    for c in set(cls):
        js = [j for j in b_item if cls[j] == c]
        bc = sum(b_item[j][3] for j in js) / sum(b_item[j][4] for j in js)
        for j in js:
            out["who writes the price"][:, j] = b_item[j][0] + bc * (xs - b_item[j][1])
    for j in b_item:
        out["one wage slope"][:, j] = b_item[j][0] + common * (xs - b_item[j][1])
    # the official level, with each class's own response to the wage left over after it
    res_item = {}
    for j in b_item:
        y = p[train, j] - lp[train]
        ok = ~np.isnan(y)
        dx, dy = xt[ok] - xt[ok].mean(), y[ok] - y[ok].mean()
        res_item[j] = (y[ok].mean(), xt[ok].mean(), float((dx * dy).sum()), float((dx * dx).sum()))
    for c in set(cls):
        js = [j for j in res_item if cls[j] == c]
        dc = sum(res_item[j][2] for j in js) / sum(res_item[j][3] for j in js)
        for j in js:
            out["price level corrected by class"][:, j] = res_item[j][0] + lp[test] + dc * (xs - res_item[j][1])
    return out


def score(err: np.ndarray, how: str) -> float:
    e = err[~np.isnan(err)]
    return float(np.sqrt(np.mean(e ** 2))) if how == SCORES[0] else float(np.median(np.abs(e)))


def cross_validate(data: dict, seed: str, wage_input: str) -> dict:
    """Errors of every model on every held-out city, the cells being those every model can predict."""
    x = data["w"] if wage_input == WAGE_INPUT[0] else country_median_wage(data["g"], data["w"])
    fold = fold_of(data["countries"], seed)[data["g"]]
    has_pli = ~np.isnan(data["logpli"][data["g"]])
    errs, groups = {}, []
    for f in range(FOLDS):
        test = (fold == f) & has_pli
        train = fold != f
        if test.sum() == 0:
            continue
        pred = fit_predict(data, train, test, x)
        truth = data["p"][test]
        mask = ~np.isnan(truth)
        for v in pred.values():
            mask &= ~np.isnan(v)
        for k, v in pred.items():
            e = np.where(mask, truth - v, math.nan)
            errs.setdefault(k, []).append(e)
        groups.append(data["g"][test])
    return {"errors": {k: np.vstack(v) for k, v in errs.items()}, "g": np.concatenate(groups)}


def ratio_resamples(cv: dict, a: str, b: str, how: str) -> list:
    """Country-block resamples of score(a) / score(b)."""
    rng = np.random.default_rng(SEED)
    ids = np.unique(cv["g"])
    rows = {k: [cv["errors"][m][cv["g"] == k] for m in (a, b)] for k in ids}
    out = []
    for _ in range(N_BOOT):
        pick = rng.choice(ids, size=len(ids))
        ea = np.vstack([rows[k][0] for k in pick])
        eb = np.vstack([rows[k][1] for k in pick])
        out.append(score(ea, how) / score(eb, how))
    return [float(np.quantile(out, q)) for q in (0.025, 0.975)]


def grid(data: dict) -> list:
    out = []
    for seed in FOLD_SEEDS:
        for wi in WAGE_INPUT:
            cv = cross_validate(data, seed, wi)
            for how in SCORES:
                s = {k: score(e, how) for k, e in cv["errors"].items()}
                out.append({"fold_seed": seed, "wage": wi, "score": how, "scores": s,
                            "cells": int((~np.isnan(cv["errors"]["per item"])).sum()),
                            "countries": int(len(np.unique(cv["g"]))),
                            "resample_writer_over_level": ratio_resamples(cv, "who writes the price",
                                                                          "one price level", how),
                            "resample_corrected_over_level": ratio_resamples(cv, "price level corrected by class",
                                                                             "one price level", how)})
    return out


def inside(data: dict) -> list:
    """Held-out cities inside countries already seen: one slope for both scales against two slopes."""
    out = []
    g, w, p, cls = data["g"], data["w"], data["p"], data["cls"]
    big = [k for k in np.unique(g) if (g == k).sum() >= MIN_CITIES_INSIDE]
    for seed in FOLD_SEEDS:
        city = np.arange(len(g))
        fold = np.array([int(hashlib.sha256(f"{seed}{i}".encode()).hexdigest(), 16) % FOLDS for i in city])
        e1, e2 = [], []
        for f in range(FOLDS):
            test = (fold == f) & np.isin(g, big)
            train = ~test
            cm = {k: float(np.mean(w[train & (g == k)])) for k in np.unique(g[train])}
            xb = np.array([cm.get(k, math.nan) for k in g])
            xw = w - xb
            for j in range(p.shape[1]):
                y = p[:, j]
                ok = train & ~np.isnan(y) & ~np.isnan(xb)
                if ok.sum() < 30:
                    continue
                X1 = np.column_stack([np.ones(ok.sum()), w[ok]])
                X2 = np.column_stack([np.ones(ok.sum()), xb[ok], xw[ok]])
                c1 = np.linalg.lstsq(X1, y[ok], rcond=None)[0]
                c2 = np.linalg.lstsq(X2, y[ok], rcond=None)[0]
                t = test & ~np.isnan(y) & ~np.isnan(xb)
                e1.append(y[t] - (c1[0] + c1[1] * w[t]))
                e2.append(y[t] - (c2[0] + c2[1] * xb[t] + c2[2] * xw[t]))
        a, b = np.concatenate(e1), np.concatenate(e2)
        for how in SCORES:
            out.append({"fold_seed": seed, "score": how, "one slope": score(a, how), "two slopes": score(b, how),
                        "cells": int(len(a))})
    return out


def c_l0(g: list):
    ok = all(pt["scores"]["one price level"] < pt["scores"]["law of one price"] for pt in g)
    pt = g[0]
    detail = (f"{pt['countries']} held-out countries with a price level, {pt['cells']:,} city-item cells: law of one "
              f"price {pt['scores']['law of one price']:.3f}, one price level {pt['scores']['one price level']:.3f} "
              f"({pt['score']} error of the log price); lower at {sum(q['scores']['one price level'] < q['scores']['law of one price'] for q in g)} of {len(g)} knob points")
    return ok, detail, {}


def c_l1(g: list):
    better = [pt["scores"]["who writes the price"] < pt["scores"]["one price level"] for pt in g]
    hi = [pt["resample_writer_over_level"][1] for pt in g]
    worse = [pt["scores"]["who writes the price"] > pt["scores"]["one price level"] for pt in g]
    lo = [pt["resample_writer_over_level"][0] for pt in g]
    if all(better) and all(h < 1 for h in hi):
        state, cell = "ours", "B"
    elif all(worse) and all(x > 1 for x in lo):
        state, cell = "rival's", "C"
    else:
        state, cell = "unread", "unread"
    pt = g[0]
    detail = ("; ".join(f"{q['fold_seed']}, {q['wage']}, {q['score']}: who writes the price "
                        f"{q['scores']['who writes the price']:.3f} against one price level "
                        f"{q['scores']['one price level']:.3f}, ratio resamples {q['resample_writer_over_level'][0]:.3f} "
                        f"to {q['resample_writer_over_level'][1]:.3f}" for q in g) + f" -> {state}")
    passed = True if state == "ours" else (False if state == "rival's" else None)
    return passed, detail, {"state": state, "grid": cell}


def c_l2(g: list):
    better = all(pt["scores"]["who writes the price"] < pt["scores"]["one wage slope"] for pt in g)
    worse = all(pt["scores"]["who writes the price"] > pt["scores"]["one wage slope"] for pt in g)
    shares = []
    for pt in g:
        s = pt["scores"]
        gain = s["one wage slope"] - s["per item"]
        shares.append((s["one wage slope"] - s["who writes the price"]) / gain if gain > 0 else math.nan)
    pt = g[0]["scores"]
    detail = (f"one wage slope {pt['one wage slope']:.3f}, six class slopes {pt['who writes the price']:.3f}, "
              f"55 item slopes {pt['per item']:.3f}; the classes capture {min(shares):.2f} to {max(shares):.2f} of "
              f"the improvement the item slopes make over one slope; lower than one slope at "
              f"{sum(q['scores']['who writes the price'] < q['scores']['one wage slope'] for q in g)} of {len(g)} knob points")
    return (True if better else (False if worse else None)), detail, {"shares": shares}


def c_l3(rows: list):
    better = all(r["two slopes"] < r["one slope"] for r in rows)
    worse = all(r["two slopes"] > r["one slope"] for r in rows)
    detail = "; ".join(f"{r['fold_seed']}, {r['score']}: one slope {r['one slope']:.4f}, two slopes "
                       f"{r['two slopes']:.4f} ({r['cells']:,} cells)" for r in rows)
    return (True if better else (False if worse else None)), detail, {}


def c_l4(g: list):
    better = all(pt["scores"]["price level corrected by class"] < pt["scores"]["one price level"]
                 and pt["resample_corrected_over_level"][1] < 1 for pt in g)
    worse = all(pt["scores"]["price level corrected by class"] > pt["scores"]["one price level"] for pt in g)
    detail = "; ".join(f"{q['fold_seed']}, {q['wage']}, {q['score']}: corrected "
                       f"{q['scores']['price level corrected by class']:.3f} against {q['scores']['one price level']:.3f}, "
                       f"ratio resamples {q['resample_corrected_over_level'][0]:.3f} to "
                       f"{q['resample_corrected_over_level'][1]:.3f}" for q in g)
    return (True if better else (False if worse else None)), detail, {}


RIVALS = {"B144-L1": {"rival_shape": "point prediction",
                      "rival_premise": "A country has one price level: an item's price there is its dollar price "
                                       "times the country's price level, log p = a(item) + log PLI(country).",
                      "rival_entailment": "Then, given the official price level, a model in which items respond to "
                                          "the wage by different amounts predicts held-out prices no better than "
                                          "the price level does."}}
KINDS = {"B144-L0": "known_answer", "B144-L1": "rival", "B144-L2": "own_reading", "B144-L3": "own_reading",
         "B144-L4": "own_reading"}
STATEMENTS = {"B144-L0": "The official price level predicts dollar prices better than one dollar price everywhere.",
              "B144-L1": "Item prices of unseen countries are predicted better by class slopes on the wage than by "
                         "the official price level. Passing means the rival is wrong here (`11e`).",
              "B144-L2": "Six class slopes predict better than one common wage slope.",
              "B144-L3": "Inside countries, separate slopes across and within countries predict held-out cities better.",
              "B144-L4": "The official price level corrected by each class's response to the wage predicts better than "
                         "the price level alone."}


def r4(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 5)
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data: dict):
    g, ins = grid(data), inside(data)
    return {"B144-L0": c_l0(g), "B144-L1": c_l1(g), "B144-L2": c_l2(g), "B144-L3": c_l3(ins),
            "B144-L4": c_l4(g)}, g, ins


def toy(class_slopes: dict, level_noise=0.02, n_countries=40, cities=6, seed=1) -> dict:
    """Countries whose item prices follow the wage by class slopes; the price level is the true average."""
    rng = np.random.default_rng(seed)
    items = list(range(12))
    cls = np.array(["A", "A", "A", "B", "B", "B", "C", "C", "C", "D", "D", "D"], dtype=object)
    g, w, rows = [], [], []
    countries = [f"K{k:02d}" for k in range(n_countries)]
    logpli = np.zeros(n_countries)
    for k in range(n_countries):
        wc = rng.normal(7.0, 0.8)
        logpli[k] = float(np.mean([class_slopes[c] for c in cls])) * (wc - 7.0) + rng.normal(0, level_noise)
        for _ in range(cities):
            wi = wc + rng.normal(0, 0.1)
            g.append(k)
            w.append(wi)
            rows.append([1.0 + 0.2 * j + class_slopes[cls[j]] * (wi - 7.0) + rng.normal(0, 0.05) for j in items])
    return {"g": np.array(g), "w": np.array(w), "p": np.array(rows), "countries": countries, "logpli": logpli,
            "cls": cls, "items": items}


def selftest() -> None:
    global N_BOOT, MIN_CITIES_INSIDE
    N_BOOT, MIN_CITIES_INSIDE = 200, 5
    apart = toy({"A": 0.1, "B": 0.3, "C": 0.6, "D": 1.0})
    res, g, _ = run(apart)
    assert res["B144-L0"][0] and res["B144-L1"][0] is True and res["B144-L2"][0] is True, \
        {k: v[1][:200] for k, v in res.items()}
    alike = toy({"A": 0.5, "B": 0.5, "C": 0.5, "D": 0.5}, level_noise=0.0)
    r2 = run(alike)[0]
    assert r2["B144-L1"][0] is not True, "where every item follows the wage alike and the level is exact, the level is not beaten"
    assert r2["B144-L2"][0] is not True and r2["B144-L4"][0] is not True
    assert res["B144-L4"][0] is True
    assert fold_of(["x", "y"], "a").tolist() == fold_of(["x", "y"], "a").tolist()
    e = np.array([[1.0, -1.0], [math.nan, 3.0]])
    assert abs(score(e, SCORES[0]) - math.sqrt(11 / 3)) < 1e-12 and score(e, SCORES[1]) == 1.0
    print("selftest ok: planted class slopes beat the level, a world of one slope does not, and the scores are exact")


def main() -> int:
    data = load()
    res, g, ins = run(data)
    for n, (p, d, _) in res.items():
        word = "PASS" if p else ("UNREAD" if p is None else "FAIL")
        print(f"{word} {n} [{KINDS[n]}]: {d[:900]}")
    matched = int(np.sum(~np.isnan(data["logpli"])))
    rec = {"stage": "B144", "diagnostic_only": True,
           "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
           "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d,
                         **({**RIVALS[n], "grid": o["grid"]} if n in RIVALS else {})} for n, (p, d, o) in res.items()],
           "objects": {"grid": r4(g), "inside": r4(ins), "countries_with_price_level": matched,
                       "countries": len(data["countries"])},
           "config": {"table": "data/raw/cost-of-living_v2.csv", "price_level": "World Bank PA.NUS.PRVT.PP / PA.NUS.FCRF, 2022",
                      "fetched_by": "experiments/b144_fetch.py --only worldbank", "folds": FOLDS,
                      "fold_seeds": list(FOLD_SEEDS), "wage_input": list(WAGE_INPUT), "scores": list(SCORES),
                      "n_boot": N_BOOT, "seed": SEED, "aliases": ALIASES, "classes": "arm A's six classes"}}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}; {matched} of {len(data['countries'])} countries carry a price level")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
    else:
        sys.exit(main())
