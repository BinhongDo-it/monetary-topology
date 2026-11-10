"""B144 arm A: prices in units of the local salary, between countries and inside them.

The table is the third-party archive already on disk for B30-5 and B38
(data/raw/cost-of-living_v2.csv: 4,956 cities, 55 rows per city, one currency,
December 2022). It carries a salary row, four rent rows and two purchase rows.
Nothing is fetched. The row names come from pages displayed in imperial units and
the archive is metric; every reading here is a slope or a ratio and does not see
the unit.

What is measured. For each row, the slope of log price on log salary at two scales:
between countries (one point per country, the median over its cities) and inside
countries (cities of one country, country means removed, pooled). A slope is divided
by the same-scale slope of a reference, the rows that are produced where they are
sold. Noise in the salary row scales every slope at one scale by one common factor,
so it cancels in that quotient. R is the quotient inside countries over the quotient
between them.

  cost-share account   a price is a traded part at one world price and a local part
                       at the local wage, with shares that belong to the good. The
                       slope on the wage is then the share at either scale, so R = 1
                       for every class of row.
  this framework       position rows (rent, purchase): R > 1. People of one class can
                       move between cities of one country and not between countries,
                       so inside a country a wage gap is taken up by the price of the
                       position. Rows whose number one writer sets for a whole country,
                       a government or a national seller: R < 1.

Criteria (each has a planted input in --selftest that must make it fail):
  B144-A0  instrument    the table reads back: 55 item columns, the salary row, every
                         class list equal, item by item, to experiments/b30_7_city_pair.py
  B144-A1  known_answer  two synthetic worlds through the same code: one built on the
                         cost-share premise with the measured salary noise must place no
                         class; one with position rows steeper inside countries and
                         written rows flatter must place those four
  B144-A2  rival         R against 1 for the classes this framework gives a direction
                         to. A class is placed when log R stands outside the largest
                         value the cost-share world returned (the floor) and its side of
                         1 is the same at every knob point. Passing means the rival's
                         point prediction does not hold on a placed class
  B144-A3  own_reading   what one month of salary buys, five coordinates per country;
                         for every pair of countries the spread of the five ratios, which
                         one conversion factor puts at 1. Two floors, both printed
  B144-A4  own_reading   the sandwich, purchase rows. If rows produced where they are sold
                         respond to the wage inside a country as they do between countries,
                         the implied response of a position row inside a country is its
                         inside quotient times that between-country slope. Read: local rows
                         below 1, purchase rows above 1, at every knob point
  B144-A5  own_reading   the same for rent rows

Run from the repo root:
    python experiments/b144_wage_coordinates.py
    python experiments/b144_wage_coordinates.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "raw" / "cost-of-living_v2.csv"
NAMES = ROOT / "data" / "b30_5" / "column_map.json"
OUT = ROOT / "results" / "b144_wage_coordinates.json"

# class of each column; the pairing with the names used in b30_7_city_pair.py is checked by A0
CLASS_OF = {
    "STATE": {"x33": "gasoline, 1L", "x27": "cigarettes, Marlboro 20", "x28": "transit, one way",
              "x29": "transit, monthly pass", "x30": "taxi, start fare", "x31": "taxi, per mile",
              "x32": "taxi, hourly waiting", "x36": "utilities, basic monthly"},
    "LADDER": {"x34": "VW Golf 1.5", "x35": "Toyota Corolla 1.6", "x3": "McDonald's combo meal",
               "x9": "milk, 1L", "x10": "white bread, 1lb", "x11": "rice, 1lb",
               "x26": "imported beer, market", "x23": "bottled water, 50oz",
               "x24": "wine, mid-range bottle", "x25": "domestic beer, market",
               "x46": "Nike running shoes", "x45": "summer dress, chain", "x44": "Levi's 501 jeans",
               "x47": "men's leather shoes", "x6": "cappuccino (*)", "x38": "broadband (*)"},
    "FRESH": {"x12": "eggs, 12", "x13": "local cheese, 1lb", "x14": "chicken fillets, 1lb",
              "x15": "beef round, 1lb", "x16": "apples, 1lb", "x17": "bananas, 1lb",
              "x18": "oranges, 1lb", "x19": "tomatoes, 1lb", "x20": "potatoes, 1lb",
              "x21": "onions, 1lb", "x22": "lettuce, 1 head"},
    "LOCAL": {"x1": "inexpensive restaurant meal", "x2": "mid-range meal for two",
              "x4": "draft beer, restaurant", "x5": "imported beer, restaurant",
              "x7": "soft drink, restaurant", "x8": "bottled water, restaurant",
              "x41": "cinema ticket", "x39": "fitness membership, monthly",
              "x40": "tennis court, 1 hour", "x42": "preschool, monthly",
              "x43": "international primary, year"},
    "RENT": {"x48": "rent 1BR centre", "x49": "rent 1BR outside", "x50": "rent 3BR centre",
             "x51": "rent 3BR outside"},
    "BUY": {"x52": "apartment/sqft, centre", "x53": "apartment/sqft, outside"},
}
# a word the archive's own name for the column must contain, so a slipped column is caught
KEYWORD = {"x33": "Gasoline", "x27": "Cigarettes", "x28": "One-Way", "x29": "Monthly Public",
           "x30": "Taxi Start", "x31": "Taxi 1 mile", "x32": "Taxi 1 Hour", "x36": "Basic Utilities",
           "x34": "Volkswagen", "x35": "Toyota", "x3": "McDonald", "x9": "Milk", "x10": "Bread",
           "x11": "Rice", "x26": "Markets :: Imported Beer", "x23": "Markets :: Bottled Water", "x24": "Wine",
           "x25": "Domestic Beer", "x46": "Nike", "x45": "Summer Dress", "x44": "Jeans",
           "x47": "Leather", "x6": "Cappuccino", "x38": "Broadband", "x12": "Eggs", "x13": "Cheese",
           "x14": "Chicken", "x15": "Beef", "x16": "Apples", "x17": "Bananas", "x18": "Oranges",
           "x19": "Tomatoes", "x20": "Potatoes", "x21": "Onions", "x22": "Lettuce",
           "x1": "Inexpensive", "x2": "Mid-Range", "x4": "Draft", "x5": "Restaurants :: Imported Beer",
           "x7": "Soft Drink", "x8": "Restaurants :: Bottled Water", "x41": "Cinema", "x39": "Fitness",
           "x40": "Tennis", "x42": "Preschool", "x43": "International Primary",
           "x48": "1 Bedroom Apartment in City Centre", "x49": "1 Bedroom Apartment Outside",
           "x50": "3 Bedroom Apartment in City Centre", "x51": "3 Bedroom Apartment Outside",
           "x52": "City Centre", "x53": "Outside of Centre"}
SAL = "x54"
SALARY_WORD = "Average Monthly Net Salary"
DROPPED = {"x37": "redefined between the archive's two vintages", "x55": "an interest rate, not a price"}
ORDER = ["LADDER", "STATE", "FRESH", "LOCAL", "RENT", "BUY"]
COORDS = ["LADDER", "FRESH", "LOCAL", "RENT", "BUY"]         # A3; STATE is each sovereign's own writing
DIRECTION = {"RENT": +1, "BUY": +1, "STATE": -1, "LADDER": -1}   # this framework's side of R = 1
SPEC_TIGHT = ["x34", "x35", "x27", "x44", "x3", "x7"]        # named brand or model: a control

# knobs. The first value of each is the default; A2 and A4 are read at every combination
MIN_WITHIN = (8, 5, 15)          # salary-carrying cities a country needs to enter the inside slope
REFERENCE = ("LOCAL", "MEAL", "LOCAL+FRESH")
QUALITY = ("all", "flagged")     # the archive's own data_quality flag
MIN_ITEM = 5                     # cities with the item a country needs, per item
MIN_PAIR = 8                     # salary-carrying cities a country needs to enter A3
N_BOOT = 1000                    # country-block resamples
N_WORLD = 200                    # synthetic worlds per seed for the floor
N_KNOWN = 6                      # synthetic worlds of each kind read by A1
SEEDS = (20261012, 20261013)
FLOOR_INDEPENDENT = 0.2752       # log error of the archive against an independent posted price (B39)
FLOOR_SAME_SOURCE = 0.0373       # the archive's two vintages against each other (B38c)
NAMED = ["Singapore", "China", "United States", "South Korea", "Japan", "Germany", "Switzerland",
         "Hong Kong", "Taiwan", "India", "Vietnam", "Egypt", "Turkey", "Spain", "Australia"]

ITEMS = [x for k in ORDER for x in CLASS_OF[k]]
IDX = {x: j for j, x in enumerate(ITEMS)}
COLS = {k: np.array([IDX[x] for x in CLASS_OF[k]]) for k in ORDER}


# ----------------------------------------------------------------------------- loading
def load() -> dict:
    with TABLE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        raw = list(reader)

    def num(v):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return math.nan
        return math.log(x) if x > 0 else math.nan

    names = json.loads(NAMES.read_text(encoding="utf-8"))
    logw = np.array([num(r.get(SAL)) for r in raw])
    keep = ~np.isnan(logw)
    countries = sorted({r["country"] for r, k in zip(raw, keep) if k})
    gid = {c: i for i, c in enumerate(countries)}
    rows = [r for r, k in zip(raw, keep) if k]
    return {
        "header": header, "names": {k: v["item"] for k, v in names["mapping"].items()},
        "unresolved": [u["column"] for u in names.get("unresolved", [])],
        "n_cities": len(raw), "countries": countries,
        "g": np.array([gid[r["country"]] for r in rows]),
        "w": logw[keep],
        "p": np.array([[num(r.get(x)) for x in ITEMS] for r in rows]),
        "flag": np.array([str(r.get("data_quality", "")).strip() == "1" for r in rows]),
        "class_of": {k: dict(v) for k, v in CLASS_OF.items()},
    }


# ----------------------------------------------------------------------------- the estimator
def quiet_nanmedian(a, axis=None):
    """nanmedian; a column with no value returns nan without a warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(a, axis=axis)


def stats(g, w, p, n_g, min_within):
    """Per country and item, everything both slopes need. One pass, no loops over cities."""
    G = n_g
    present = ~np.isnan(p)
    cities = np.bincount(g, minlength=G).astype(float)
    wsum = np.bincount(g, weights=w, minlength=G)
    wbar = wsum / np.maximum(cities, 1)
    med = np.full((G, p.shape[1]), np.nan)
    order = np.argsort(g, kind="stable")
    bounds = np.searchsorted(g[order], np.arange(G + 1))
    for c in range(G):
        block = p[order[bounds[c]:bounds[c + 1]]]
        if block.size:
            med[c] = quiet_nanmedian(block, axis=0)
    wmed = np.array([np.median(w[order[bounds[c]:bounds[c + 1]]]) if bounds[c + 1] > bounds[c]
                     else np.nan for c in range(G)])
    sxy = np.zeros((G, p.shape[1]))
    sxx = np.zeros((G, p.shape[1]))
    big = cities >= min_within
    for j in range(p.shape[1]):
        m = present[:, j]
        n = np.bincount(g[m], minlength=G).astype(float)
        sw = np.bincount(g[m], weights=w[m], minlength=G)
        sp = np.bincount(g[m], weights=p[m, j], minlength=G)
        swp = np.bincount(g[m], weights=w[m] * p[m, j], minlength=G)
        sww = np.bincount(g[m], weights=w[m] * w[m], minlength=G)
        ok = big & (n >= MIN_ITEM)
        nn = np.where(ok, n, 1.0)
        sxy[:, j] = np.where(ok, swp - sw * sp / nn, 0.0)
        sxx[:, j] = np.where(ok, sww - sw * sw / nn, 0.0)
    return {"med": med, "wmed": wmed, "sxy": sxy, "sxx": sxx, "cities": cities, "wbar": wbar}


def slopes(st, mult=None):
    """Between and inside slopes for every item. mult: how many times each country is drawn."""
    med, wmed = st["med"], st["wmed"]
    G = med.shape[0]
    m = np.ones(G) if mult is None else mult
    has = ~np.isnan(med) & ~np.isnan(wmed)[:, None]
    wt = np.where(has, m[:, None], 0.0)
    n = wt.sum(axis=0)
    x = np.where(has, wmed[:, None], 0.0)
    y = np.where(has, med, 0.0)
    mx = (wt * x).sum(axis=0) / np.maximum(n, 1e-12)
    my = (wt * y).sum(axis=0) / np.maximum(n, 1e-12)
    sxx = (wt * (x - mx) ** 2).sum(axis=0)
    sxy = (wt * (x - mx) * (y - my)).sum(axis=0)
    with np.errstate(all="ignore"):
        between = np.where(sxx > 0, sxy / sxx, np.nan)
        within = (m[:, None] * st["sxy"]).sum(axis=0) / (m[:, None] * st["sxx"]).sum(axis=0)
    return between, within


def ref_slope(b, reference):
    if reference == "MEAL":
        return b[IDX["x1"]]
    if reference == "LOCAL":
        return quiet_nanmedian(b[COLS["LOCAL"]])
    if reference == "LOCAL+FRESH":
        return quiet_nanmedian(b[np.concatenate([COLS["LOCAL"], COLS["FRESH"]])])
    raise ValueError(reference)


def profile(st, reference, mult=None):
    """Class medians of the slopes, the two quotients, R, and log R (nan when a sign makes it undefined)."""
    between, within = slopes(st, mult)
    rb, rw = ref_slope(between, reference), ref_slope(within, reference)
    out = {"ref_between": rb, "ref_within": rw, "between": between, "within": within}
    for k in ORDER:
        b, w = quiet_nanmedian(between[COLS[k]]), quiet_nanmedian(within[COLS[k]])
        with np.errstate(all="ignore"):
            rel_b, rel_w = b / rb, w / rw
            r = rel_w / rel_b
        out[k] = {"between": b, "within": w, "rel_between": rel_b, "rel_within": rel_w, "R": r,
                  "logR": math.log(r) if (r > 0 and np.isfinite(r)) else math.nan}
    return out


def subset(data, quality):
    if quality == "all":
        return data
    keep = data["flag"]
    return {**data, "g": data["g"][keep], "w": data["w"][keep], "p": data["p"][keep], "flag": data["flag"][keep]}


def stats_of(data, min_within=MIN_WITHIN[0], quality=QUALITY[0]):
    d = subset(data, quality)
    return stats(d["g"], d["w"], d["p"], len(data["countries"]), min_within)


# ----------------------------------------------------------------------------- synthetic worlds
def world_inputs(data):
    """What the cost-share world is built from, all read off the real table."""
    st = stats_of(data)
    between, within = slopes(st)
    lam = float(np.clip(ref_slope(within, "LOCAL") / ref_slope(between, "LOCAL"), 0.05, 1.0))
    g, w, p = data["g"], data["w"], data["p"]
    G = len(data["countries"])
    wbar = st["wbar"]
    dev = w - wbar[g]
    var_g = np.bincount(g, weights=dev * dev, minlength=G) / np.maximum(st["cities"], 1)
    icpt = np.nanmean(p - between[None, :] * w[:, None], axis=0)
    # residuals of the cost-share law itself, split into a country part and a city part
    res = p - (icpt[None, :] + between[None, :] * w[:, None])
    cres = np.full((G, p.shape[1]), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for c in range(G):
            blk = res[g == c]
            if blk.size:
                cres[c] = np.nanmean(blk, axis=0)
        sd_country = np.nanstd(cres, axis=0)
        sd_city = np.nanstd(res - cres[g], axis=0)
    return {"lam": lam, "share": between, "icpt": icpt, "wbar": wbar, "dev": dev, "var_g": var_g,
            "sd_country": sd_country, "sd_city": sd_city}


SPLIT = 3.0        # planted: position rows respond this many times their share inside a country


def make_world(data, wi, rng, kind="cost_share", noise="empirical", split=SPLIT):
    """A table with the real shape, salaries and gaps, and prices from a stated law.

    cost_share   log p = intercept + share * true log wage, one share per row at both scales
    scale_split  the same, except that inside a country position rows respond `split` times
                 their share and rows with one writer per country 0.4 times
    scalar       log p = intercept + one level per city, every row with the same slope
    The observed salary is the true wage plus noise sized so that inside-country slopes are
    attenuated by the factor the real reference rows show.
    """
    g, lam = data["g"], wi["lam"]
    G, I = len(data["countries"]), len(ITEMS)
    true_dev = math.sqrt(lam) * wi["dev"]
    noise_w = rng.normal(size=g.size) * np.sqrt((1 - lam) * wi["var_g"][g])
    w_obs = wi["wbar"][g] + true_dev + noise_w
    share_between = np.array(wi["share"], dtype=float)
    if kind == "scalar":
        share_between = np.full(I, float(quiet_nanmedian(wi["share"][COLS["LOCAL"]])))
    share_within = share_between.copy()
    if kind == "scale_split":
        for k, f in (("RENT", split), ("BUY", split), ("STATE", 0.4), ("LADDER", 0.4)):
            share_within[COLS[k]] = f * share_between[COLS[k]]
    if noise == "empirical":
        eta = (rng.normal(size=(G, I)) * wi["sd_country"][None, :])[g] \
            + rng.normal(size=(g.size, I)) * wi["sd_city"][None, :]
    else:
        eta = rng.normal(size=(g.size, I)) * float(noise)
    p = wi["icpt"][None, :] + share_between[None, :] * wi["wbar"][g][:, None] \
        + share_within[None, :] * true_dev[:, None] + eta
    p = np.where(np.isnan(data["p"]), np.nan, p)
    return {**data, "w": w_obs, "p": p}


def floor_logR(data, wi, noise, seeds=SEEDS, n_world=N_WORLD, reference=REFERENCE[0]):
    """Largest |log R| per class over worlds in which the cost-share premise holds exactly."""
    per_seed = []
    for s in seeds:
        rng = np.random.default_rng(s)
        mx = {k: 0.0 for k in ORDER}
        undefined = 0
        for _ in range(n_world):
            pr = profile(stats_of(make_world(data, wi, rng, "cost_share", noise)), reference)
            for k in ORDER:
                v = pr[k]["logR"]
                if math.isnan(v):
                    undefined += 1
                else:
                    mx[k] = max(mx[k], abs(v))
        per_seed.append({"null_max": mx, "undefined": undefined})
    return {"per_seed": per_seed,
            "floor": {k: max(ps["null_max"][k] for ps in per_seed) for k in ORDER}}


# ----------------------------------------------------------------------------- readings
def bootstrap(st, reference, seeds=SEEDS, n_boot=N_BOOT):
    G = st["med"].shape[0]
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        draws = {k: [] for k in ORDER}
        for _ in range(n_boot):
            mult = np.bincount(rng.integers(0, G, size=G), minlength=G).astype(float)
            pr = profile(st, reference, mult)
            for k in ORDER:
                draws[k].append(pr[k]["logR"])
        res = {}
        for k in ORDER:
            a = np.array(draws[k])
            ok = a[~np.isnan(a)]
            res[k] = {"defined": int(ok.size), "above_zero": int((ok > 0).sum()),
                      "below_zero": int((ok < 0).sum()),
                      "p025": float(np.quantile(ok, 0.025)), "p975": float(np.quantile(ok, 0.975)),
                      "sd": float(ok.std())}
        out.append(res)
    return out


def knob_grid(data):
    grid = []
    for mw, ref, q in itertools.product(MIN_WITHIN, REFERENCE, QUALITY):
        pr = profile(stats_of(data, mw, q), ref)
        grid.append({"min_within": mw, "reference": ref, "quality": q,
                     "logR": {k: pr[k]["logR"] for k in ORDER},
                     "implied": {k: pr[k]["rel_within"] * pr["ref_between"] for k in ("RENT", "BUY")},
                     "ref_between": pr["ref_between"], "ref_within": pr["ref_within"]})
    return grid


STATES_A2 = {"ours": "the side this framework names, outside the floor, at every knob point",
             "opposite": "the other side, outside the floor, at every knob point",
             "unread": "inside the floor, or the side changes somewhere on the knob grid"}
MAPPING_A2 = {"ours": "B", "opposite": "both_unmet", "unread": "not placed"}


def place(logr, floor, grid_values, direction):
    """One class against the floor and the knob grid. Returns one of STATES_A2."""
    if math.isnan(logr) or any(math.isnan(v) for v in grid_values):
        return "unread"                                   # an undefined knob point is not a reading
    signs = {1 if v > 0 else -1 for v in grid_values}
    if abs(logr) <= floor or len(signs) != 1:
        return "unread"
    return "ours" if (1 if logr > 0 else -1) == direction else "opposite"


def reading_a2(data, wi, floors=None, n_boot=N_BOOT):
    st = stats_of(data)
    pr = profile(st, REFERENCE[0])
    grid = knob_grid(data)
    floors = floors or {"independent": floor_logR(data, wi, FLOOR_INDEPENDENT),
                        "empirical": floor_logR(data, wi, "empirical")}
    floor = {k: max(floors["independent"]["floor"][k], floors["empirical"]["floor"][k]) for k in ORDER}
    states = {k: place(pr[k]["logR"], floor[k], [pt["logR"][k] for pt in grid], DIRECTION[k])
              for k in DIRECTION}
    return {"profile": pr, "grid": grid, "floors": floors, "floor": floor, "states": states,
            "boot": bootstrap(st, REFERENCE[0], n_boot=n_boot), "lam": wi["lam"]}


def verdict_a2(states):
    """Rival polarity: passing means its point prediction fails on a placed class."""
    cells = {}
    for k, s in states.items():
        cell = MAPPING_A2[s]
        if cell != "not placed":
            cells[cell] = cells.get(cell, 0) + 1
    if not cells:
        return None, "unread", None
    if len(cells) == 1:
        return True, next(iter(cells)), None
    return True, "mixed", cells


def coords(st):
    """Log of how many median items of each class one month of salary buys, per country."""
    med, wmed = st["med"], st["wmed"]
    return np.column_stack([quiet_nanmedian(wmed[:, None] - med[:, COLS[k]], axis=1) for k in COORDS])


def spreads(u):
    """For every pair of countries, max minus min over the coordinates of the log ratio."""
    d = u[:, None, :] - u[None, :, :]
    s = d.max(axis=2) - d.min(axis=2)
    return s[np.triu_indices(u.shape[0], 1)]


def reading_a3(data, seeds=SEEDS, n_world=40):
    st = stats_of(data)
    keep = (st["cities"] >= MIN_PAIR)
    cols = np.concatenate([COLS[k] for k in COORDS])
    x = st["wmed"][:, None] - st["med"][:, cols]              # log units bought, country by item
    full = keep & ~np.isnan(x).any(axis=1)
    x = x[full]
    lab = np.concatenate([np.full(len(COLS[k]), i) for i, k in enumerate(COORDS)])

    def class_medians(m):
        return np.column_stack([np.median(m[:, lab == i], axis=1) for i in range(len(COORDS))])

    obs = spreads(class_medians(x))
    who = [c for c, f in zip(data["countries"], full) if f]
    ia, ib = np.triu_indices(len(who), 1)
    fit = x.mean(axis=1, keepdims=True) + x.mean(axis=0, keepdims=True) - x.mean()
    resid = x - fit
    floors = {}
    for name in ("independent", "own_residuals_shuffled"):
        mx, med = [], []
        for s in seeds:
            rng = np.random.default_rng(s)
            for _ in range(n_world):
                if name == "independent":
                    e = rng.normal(size=x.shape) * FLOOR_INDEPENDENT
                else:
                    e = rng.permutation(resid.ravel()).reshape(resid.shape)
                sp = spreads(class_medians(fit + e))
                mx.append(float(sp.max()))
                med.append(float(np.median(sp)))
        floors[name] = {"null_max": max(mx), "null_median": float(np.median(med))}
    named = {}
    u_all = coords(st)
    us = data["countries"].index("United States") if "United States" in data["countries"] else None
    for c in NAMED:
        if c in data["countries"] and us is not None:
            i = data["countries"].index(c)
            d = u_all[i] - u_all[us]
            if not np.isnan(d).any():
                named[c] = {"cities": int(st["cities"][i]),
                            "ratios_to_united_states": {k: float(math.exp(v)) for k, v in zip(COORDS, d)},
                            "max_over_min": float(math.exp(d.max() - d.min()))}
    top = [{"pair": [who[ia[i]], who[ib[i]]], "spread_log": float(obs[i])}
           for i in np.argsort(-obs)[:30] if obs[i] > floors["own_residuals_shuffled"]["null_max"]]
    return {"countries": int(full.sum()), "pairs": int(obs.size), "obs": obs, "floors": floors, "named": named,
            "above": {n: int((obs > f["null_max"]).sum()) for n, f in floors.items()}, "top": top}


def reading_a4(a2):
    pr, grid = a2["profile"], a2["grid"]
    implied = {k: pr[k]["rel_within"] * pr["ref_between"] for k in ("RENT", "BUY")}
    on_grid = {k: [pt["implied"][k] for pt in grid] for k in ("RENT", "BUY")}
    ref_grid = [pt["ref_between"] for pt in grid]
    return {"ref_between": pr["ref_between"], "implied": implied, "on_grid": on_grid, "ref_grid": ref_grid}


STATES_A4 = {"sandwich": "local rows below 1 and this position row above 1 at every knob point",
             "not there": "this position row at or below 1 at every knob point, or local rows at or above 1 "
                          "at every knob point",
             "unread": "the side of 1 changes somewhere on the knob grid"}
MAPPING_A4 = {"sandwich": True, "not there": False, "unread": None}


def state_a4(a4, k):
    pos = [v > 1 for v in a4["on_grid"][k]]
    loc = [v < 1 for v in a4["ref_grid"]]
    if all(pos) and all(loc):
        return "sandwich"
    if not any(pos) or not any(loc):
        return "not there"
    return "unread"


# ----------------------------------------------------------------------------- criteria
def c_a0(data):
    from b30_7_city_pair import FRESH, LADDER, LOCAL, STATE
    theirs = {"STATE": [r[0] for r in STATE], "LADDER": [r[0] for r in LADDER],
              "FRESH": [r[0] for r in FRESH], "LOCAL": [r[0] for r in LOCAL]}
    mine = {k: sorted(v.values()) for k, v in data["class_of"].items()}
    mine_local = sorted(mine["LOCAL"] + mine["RENT"] + mine["BUY"])
    problems = []
    for k in ("STATE", "FRESH"):
        if sorted(theirs[k]) != mine[k]:
            problems.append(f"{k} differs")
    if sorted(n for n in theirs["LADDER"] if n != "mobile plan (*)") != mine["LADDER"]:
        problems.append("LADDER differs")
    if sorted(theirs["LOCAL"]) != mine_local:
        problems.append("LOCAL with the housing rows differs")
    xs = [h for h in data["header"] if h.startswith("x")]
    if len(xs) != 55:
        problems.append(f"{len(xs)} item columns, not 55")
    if SALARY_WORD not in data["names"].get(SAL, ""):
        problems.append("the salary column is not the salary row")
    used = [x for v in data["class_of"].values() for x in v]
    if sorted(used + list(DROPPED), key=lambda s: int(s[1:])) != [f"x{i}" for i in range(1, 56) if f"x{i}" != SAL]:
        problems.append("the classes and the dropped rows do not cover the item columns exactly once")
    slipped = [x for x in used if KEYWORD[x] not in data["names"].get(x, "")]
    if slipped:
        problems.append(f"columns whose archive name lacks the expected word: {slipped}")
    if [x for x in used if x in data["unresolved"]]:
        problems.append("a used column is one the column map left unresolved")
    detail = (f"{len(xs)} item columns; {len(used)} used in six classes, {len(DROPPED)} dropped by name; "
              f"{int(data['w'].size)} of {data['n_cities']} cities carry the salary row, in "
              f"{len(data['countries'])} countries; " + ("; ".join(problems) if problems else
                                                         "class lists equal those of b30_7_city_pair.py item by item"))
    return not problems, detail, {"problems": problems, "dropped": DROPPED}


def c_a1(data, wi, floor, n_worlds=N_KNOWN, built=("cost_share", "scale_split")):
    """A2's placing rule, with the floor A2 uses, on worlds whose answer is known.

    built: the law each of the two worlds is generated from. The selftest hands the wrong
    law to each slot in turn, and the flag has to fail both times.
    """
    out = {}
    for (kind, want), law in zip((("cost_share", {}), ("scale_split", {k: "ours" for k in DIRECTION})), built):
        placed, sandwich = [], []
        for i in range(n_worlds):
            world = make_world(data, wi, np.random.default_rng(1000 + i), law)
            pr = profile(stats_of(world), REFERENCE[0])
            grid = knob_grid(world)
            states = {k: place(pr[k]["logR"], floor[k], [pt["logR"][k] for pt in grid], DIRECTION[k])
                      for k in DIRECTION}
            placed.append({k: s for k, s in states.items() if s != "unread"})
            a4w = {"on_grid": {k: [pt["implied"][k] for pt in grid] for k in ("RENT", "BUY")},
                   "ref_grid": [pt["ref_between"] for pt in grid]}
            sandwich.append({k: state_a4(a4w, k) for k in ("BUY", "RENT")})
        out[kind] = {"worlds": n_worlds, "placed": placed, "as_wanted": sum(p == want for p in placed),
                     "sandwich_states": sandwich,
                     "sandwich_read": {k: sum(s[k] == "sandwich" for s in sandwich) for k in ("BUY", "RENT")}}
    ok = (out["cost_share"]["as_wanted"] == n_worlds and out["scale_split"]["as_wanted"] == n_worlds)
    detail = (f"cost-share world: {out['cost_share']['as_wanted']} of {n_worlds} place no class; "
              f"world with position rows steeper and written rows flatter inside countries: "
              f"{out['scale_split']['as_wanted']} of {n_worlds} place RENT, BUY, STATE and LADDER on this "
              f"framework's side")
    out["planted_implied"] = {k: float(SPLIT * quiet_nanmedian(wi["share"][COLS[k]])) for k in ("BUY", "RENT")}
    return ok, detail, out


def c_a2(a2):
    pr, st = a2["profile"], a2["states"]
    passed, grid, split = verdict_a2(st)
    parts = []
    for k in DIRECTION:
        b = a2["boot"][0][k]
        side = "above_zero" if DIRECTION[k] > 0 else "below_zero"
        vals = [pt["logR"][k] for pt in a2["grid"]]
        knob = sum((v > 0) == (DIRECTION[k] > 0) for v in vals)
        parts.append(f"{k}: R {pr[k]['R']:.2f} (log {pr[k]['logR']:+.3f}), floor {a2['floor'][k]:.3f}, "
                     f"{abs(pr[k]['logR']) / a2['floor'][k]:.1f} floors, {knob} of {len(vals)} knob points on "
                     f"this framework's side (log R {min(vals):+.2f} to {max(vals):+.2f}), {b[side]} of "
                     f"{b['defined']} country resamples there -> {st[k]}")
    others = "; ".join(f"{k} R {pr[k]['R']:.2f}, floor {a2['floor'][k]:.3f}" for k in ORDER
                       if k not in DIRECTION and k != "LOCAL")
    detail = "; ".join(parts) + f". No side stated, printed: {others}. LOCAL is the reference"
    obj = {"grid": grid, "grid_split": split, "states": st}
    return passed, detail, obj


def c_a3(a3):
    obs = a3["obs"]
    ind, own = a3["floors"]["independent"], a3["floors"]["own_residuals_shuffled"]
    passed = a3["above"]["own_residuals_shuffled"] > 0
    detail = (f"{a3['countries']} countries with every row and {MIN_PAIR} or more cities, {a3['pairs']} pairs; "
              f"spread of the five ratios, median {math.exp(float(np.median(obs))):.2f} times, largest "
              f"{math.exp(float(obs.max())):.1f} times. Floor from an independent source (log error "
              f"{FLOOR_INDEPENDENT}): median {math.exp(ind['null_median']):.2f}, largest {math.exp(ind['null_max']):.2f}, "
              f"{a3['above']['independent']} pairs above it. Floor with the table's own residuals shuffled over "
              f"cells: median {math.exp(own['null_median']):.2f}, largest {math.exp(own['null_max']):.2f}, "
              f"{a3['above']['own_residuals_shuffled']} pairs above it")
    return passed, detail, None


def c_a4(a4, k, known=None):
    state = state_a4(a4, k)
    passed = MAPPING_A4[state]
    vals = a4["on_grid"][k]
    detail = (f"between countries the local rows move {a4['ref_between']:.3f} per unit of log salary "
              f"({min(a4['ref_grid']):.3f} to {max(a4['ref_grid']):.3f} over the knob grid); implied inside a "
              f"country for {k}: {a4['implied'][k]:.2f} ({min(vals):.2f} to {max(vals):.2f}, above 1 at "
              f"{sum(v > 1 for v in vals)} of {len(vals)} knob points) -> {state}. Conditional on local rows "
              f"responding to the wage inside a country as they do between countries")
    if known:
        w = known["scale_split"]
        detail += (f". The rule on synthetic worlds: with a planted response of {known['planted_implied'][k]:.2f} "
                   f"it read a sandwich in {w['sandwich_read'][k]} of {w['worlds']}; where every row keeps its "
                   f"share, in {known['cost_share']['sandwich_read'][k]} of {known['cost_share']['worlds']}")
    return passed, detail, {"state": state}


def r4(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), 4)


def run(data, verbose=True):
    wi = world_inputs(data)
    a0 = c_a0(data)
    a2 = reading_a2(data, wi)
    a1 = c_a1(data, wi, a2["floor"])
    a3 = reading_a3(data)
    a4 = reading_a4(a2)
    res = {"B144-A0": a0, "B144-A1": a1, "B144-A2": c_a2(a2), "B144-A3": c_a3(a3),
           "B144-A4": c_a4(a4, "BUY", a1[2]), "B144-A5": c_a4(a4, "RENT", a1[2])}
    return res, {"a2": a2, "a3": a3, "a4": a4, "wi": wi, "known": a1[2]}


KINDS = {"B144-A0": "instrument", "B144-A1": "known_answer", "B144-A2": "rival",
         "B144-A3": "own_reading", "B144-A4": "own_reading", "B144-A5": "own_reading"}
STATEMENTS = {
    "B144-A0": "The table reads back and the classes are the ones of the city-pair station, item by item.",
    "B144-A1": "The reading returns the known answer on two synthetic worlds: no class placed where the "
               "cost-share premise holds, four placed where position rows are steeper and written rows "
               "flatter inside countries.",
    "B144-A2": "The rival's point prediction R = 1 does not hold on a class this framework gives a side to. "
               "Passing means the rival is wrong on a placed class (`11e`).",
    "B144-A3": "The five ratios between two countries are not one number: pairs stand above the floor that "
               "gives the table's whole residual to unstructured noise.",
    "B144-A4": "Inside a country the wage sits between what labour sells and the purchase price of a position: "
               "local rows respond less than one for one, purchase rows more.",
    "B144-A5": "The same for the rent of a position.",
}
RIVAL = {
    "rival_shape": "point prediction",
    "rival_premise": "A price is a traded part at one world price and a local part at the local wage, "
                     "p_i = (e p*)^(1 - s_i) w^(s_i), and the share s_i belongs to the good.",
    "rival_entailment": "Then d log p_i / d log w = s_i whether wages differ between countries or between "
                        "cities of one country, so the slope of any row over the slope of a reference row is "
                        "the same number at both scales: R = 1 for every class of row.",
}


def record_of(data, res, objs):
    a2, a3, a4, known = objs["a2"], objs["a3"], objs["a4"], objs["known"]
    pr = a2["profile"]
    crit = []
    for name, (passed, detail, obj) in res.items():
        c = {"name": name, "kind": KINDS[name], "passed": passed, "statement": STATEMENTS[name], "detail": detail}
        if name == "B144-A2":
            c.update(RIVAL)
            c["grid"] = obj["grid"]
            if obj["grid_split"]:
                c["grid_split"] = obj["grid_split"]
            c["grid_note"] = {k: f"{s}: {STATES_A2[s]}" for k, s in obj["states"].items()}
        crit.append(c)
    items = {x: {"class": k, "name": data["names"][x].split(" :: ")[-1],
                 "between": r4(pr["between"][IDX[x]]), "within": r4(pr["within"][IDX[x]])}
             for k in ORDER for x in CLASS_OF[k]}
    classes = {k: {kk: r4(v) for kk, v in pr[k].items()} for k in ORDER}
    for k in ORDER:
        classes[k]["floor_independent"] = r4(a2["floors"]["independent"]["floor"][k])
        classes[k]["floor_empirical"] = r4(a2["floors"]["empirical"]["floor"][k])
        classes[k]["floor"] = r4(a2["floor"][k])
        classes[k]["bootstrap"] = [{kk: (r4(v) if isinstance(v, float) else v) for kk, v in b[k].items()}
                                   for b in a2["boot"]]
    obs = a3["obs"]
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": crit,
        "mapping": {"B144-A2": {"states": STATES_A2, "state_to_cell": MAPPING_A2,
                                "verdict": "passed is true when a class is placed, null when none is"},
                    "B144-A4": {"states": STATES_A4, "state_to_verdict": MAPPING_A4},
                    "B144-A5": {"states": STATES_A4, "state_to_verdict": MAPPING_A4}},
        "objects": {
            "items": items, "classes": classes,
            "reference": {"between": r4(pr["ref_between"]), "within": r4(pr["ref_within"]),
                          "attenuation_used_in_worlds": r4(a2["lam"])},
            "spec_tight_rows": {x: {"name": data["names"][x].split(" :: ")[-1],
                                    "R": r4((pr["within"][IDX[x]] / pr["ref_within"])
                                            / (pr["between"][IDX[x]] / pr["ref_between"]))} for x in SPEC_TIGHT},
            "knob_grid": [{"min_within": pt["min_within"], "reference": pt["reference"], "quality": pt["quality"],
                           "logR": {k: r4(v) for k, v in pt["logR"].items()},
                           "implied": {k: r4(v) for k, v in pt["implied"].items()},
                           "ref_between": r4(pt["ref_between"]), "ref_within": r4(pt["ref_within"])}
                          for pt in a2["grid"]],
            "floor_worlds": {n: [{"null_max": {k: r4(v) for k, v in ps["null_max"].items()},
                                  "undefined": ps["undefined"]} for ps in f["per_seed"]]
                             for n, f in a2["floors"].items()},
            "pairs": {"countries": a3["countries"], "pairs": a3["pairs"],
                      "spread_log": {"median": r4(float(np.median(obs))), "p25": r4(float(np.quantile(obs, 0.25))),
                                     "p75": r4(float(np.quantile(obs, 0.75))), "max": r4(float(obs.max()))},
                      "floors": {n: {k: r4(v) for k, v in f.items()} for n, f in a3["floors"].items()},
                      "pairs_above_floor": a3["above"],
                      "pairs_above_shuffled_floor": [{"pair": tp["pair"], "spread_log": r4(tp["spread_log"])}
                                                     for tp in a3["top"]]},
            "named_countries": {c: {"cities": v["cities"], "max_over_min": r4(v["max_over_min"]),
                                    "ratios_to_united_states": {k: r4(x) for k, x in
                                                                v["ratios_to_united_states"].items()}}
                                for c, v in a3["named"].items()},
            "known_worlds": {"planted_implied": {k: r4(v) for k, v in known["planted_implied"].items()},
                             **{kind: {"worlds": known[kind]["worlds"], "placed": known[kind]["placed"],
                                       "sandwich_states": known[kind]["sandwich_states"]}
                                for kind in ("cost_share", "scale_split")}},
            "sandwich": {"local_rows_between": r4(a4["ref_between"]),
                         "implied_inside": {k: r4(v) for k, v in a4["implied"].items()},
                         "implied_on_grid": {k: [r4(v) for v in vs] for k, vs in a4["on_grid"].items()}},
        },
        "config": {"table": "data/raw/cost-of-living_v2.csv", "column_names": "data/b30_5/column_map.json",
                   "classes_from": "experiments/b30_7_city_pair.py", "dropped": DROPPED,
                   "knobs": {"min_within": list(MIN_WITHIN), "reference": list(REFERENCE), "quality": list(QUALITY)},
                   "min_item": MIN_ITEM, "min_pair": MIN_PAIR, "n_boot": N_BOOT, "n_world": N_WORLD,
                   "n_known": N_KNOWN, "planted_split": SPLIT,
                   "seeds": list(SEEDS), "floor_independent": FLOOR_INDEPENDENT,
                   "floor_same_source": FLOOR_SAME_SOURCE, "direction": DIRECTION, "coordinates": COORDS},
    }


# ----------------------------------------------------------------------------- selftest
def selftest() -> None:
    data = load()
    wi = world_inputs(data)
    st = stats_of(data)

    # A0: a row in the wrong class, a salary column that is something else, a slipped column
    assert c_a0(data)[0], c_a0(data)[1]
    bad = {**data, "class_of": {k: dict(v) for k, v in data["class_of"].items()}}
    bad["class_of"]["LADDER"]["x33"] = bad["class_of"]["STATE"].pop("x33")
    assert not c_a0(bad)[0], "A0 must catch a row moved to another class"
    bad = {**data, "names": {**data["names"], SAL: "something else"}}
    assert not c_a0(bad)[0], "A0 must catch a salary column that is not the salary row"
    bad = {**data, "names": {**data["names"], "x48": data["names"]["x52"]}}
    assert not c_a0(bad)[0], "A0 must catch a slipped column"
    bad = {**data, "names": {**data["names"], "x5": data["names"]["x26"]}}
    assert not c_a0(bad)[0], "A0 must tell the restaurant beer from the market beer"

    # the estimator at the knob point the first look used returns the first look's numbers
    meal = profile(st, "MEAL")
    seen = {k: (round(float(meal[k]["rel_between"]), 2), round(float(meal[k]["rel_within"]), 2)) for k in ORDER}
    assert seen == {"LADDER": (0.46, 0.41), "STATE": (1.02, 0.47), "FRESH": (0.58, 0.62),
                    "LOCAL": (0.84, 1.0), "RENT": (1.12, 2.78), "BUY": (1.07, 3.55)}, seen

    # on a table with no gaps and no noise, a row with share s returns s at both scales and R = 1
    full = {**data, "p": np.zeros_like(data["p"])}
    exact = make_world(full, {**wi, "lam": 1.0}, np.random.default_rng(1), "cost_share", noise=0.0)
    b, w = slopes(stats_of(exact))
    assert np.max(np.abs(b - wi["share"])) < 1e-9, "between slope must return the share"
    assert np.max(np.abs(w - wi["share"])) < 1e-9, "inside slope must return the share"
    assert all(abs(profile(stats_of(exact), r)[k]["R"] - 1) < 1e-9 for r in REFERENCE for k in ORDER)
    # salary noise attenuates every inside slope by one factor, and R does not move
    noisy = make_world(full, {**wi, "lam": 0.3}, np.random.default_rng(2), "cost_share", noise=0.0)
    prn = profile(stats_of(noisy), "LOCAL")
    assert 0.2 < prn["ref_within"] / prn["ref_between"] < 0.4, "the planted salary noise must attenuate"
    assert all(abs(prn[k]["R"] - 1) < 1e-9 for k in ORDER), "attenuation must cancel in R exactly"
    # and a planted split shows up at its planted size. Not to the last digit: a country's median
    # price carries its median inside deviation times the inside share, which leaks a little of the
    # split into the between slope. The untouched classes stay exact.
    split = make_world(full, {**wi, "lam": 0.3}, np.random.default_rng(2), "scale_split", noise=0.0)
    prs = profile(stats_of(split), "LOCAL")
    for k, planted in (("RENT", 3.0), ("BUY", 3.0), ("STATE", 0.4), ("LADDER", 0.4)):
        assert abs(math.log(prs[k]["R"] / planted)) < 0.01, f"planted R must come back for {k}: {prs[k]['R']}"
    assert abs(prs["FRESH"]["R"] - 1) < 1e-9 and abs(prs["LOCAL"]["R"] - 1) < 1e-9
    # one draw of every country is the plain estimate; two draws of every country as well
    ones = np.ones(len(data["countries"]))
    for mult in (ones, 2 * ones):
        for x, y in zip(slopes(st), slopes(st, mult)):
            assert np.allclose(x, y, equal_nan=True)
    # a multiplicity that leaves out half the countries is the estimate on the other half alone
    half = (np.arange(len(data["countries"])) % 2 == 0).astype(float)
    keep = half[data["g"]] > 0
    sub = {**data, "g": data["g"][keep], "w": data["w"][keep], "p": data["p"][keep], "flag": data["flag"][keep]}
    for x, y in zip(slopes(st, half), slopes(stats_of(sub))):
        assert np.allclose(x, y, equal_nan=True), "a resample must weigh countries, not ignore the weights"
    # the three references are three different numbers, each the one its name says
    vec = np.arange(len(ITEMS), dtype=float)
    assert ref_slope(vec, "MEAL") == vec[IDX["x1"]]
    assert ref_slope(vec, "LOCAL") == np.median(vec[COLS["LOCAL"]])
    assert ref_slope(vec, "LOCAL+FRESH") == np.median(vec[np.concatenate([COLS["LOCAL"], COLS["FRESH"]])])
    assert len({float(ref_slope(vec, r)) for r in REFERENCE}) == 3
    # the quality knob keeps the flagged cities and only those; the grid has every combination once
    flagged = stats_of(data, quality="flagged")
    assert flagged["cities"].sum() == data["flag"].sum() < data["w"].size
    grid = knob_grid(data)
    assert len({(pt["min_within"], pt["reference"], pt["quality"]) for pt in grid}) \
        == len(MIN_WITHIN) * len(REFERENCE) * len(QUALITY) == len(grid)
    assert len({round(pt["logR"]["RENT"], 6) for pt in grid}) == len(grid), "every knob point is its own reading"
    # salaries shuffled inside countries leave no inside slope
    rng = np.random.default_rng(3)
    sh = data["w"].copy()
    for c in range(len(data["countries"])):
        m = np.where(data["g"] == c)[0]
        sh[m] = rng.permutation(sh[m])
    wsh = slopes(stats_of({**data, "w": sh}))[1]
    assert abs(np.nanmedian(wsh[COLS["BUY"]])) < 0.1 * abs(np.nanmedian(slopes(st)[1][COLS["BUY"]]))

    # the placing rule, every state, and the mapping from states to cells
    assert place(0.5, 0.2, [0.5, 0.4], +1) == "ours" and place(0.5, 0.2, [0.5, -0.1], +1) == "unread"
    assert place(0.1, 0.2, [0.1, 0.1], +1) == "unread" and place(-0.5, 0.2, [-0.5, -0.4], +1) == "opposite"
    assert place(-0.5, 0.2, [-0.5, -0.4], -1) == "ours" and place(math.nan, 0.2, [0.1], +1) == "unread"
    assert place(0.5, 0.2, [0.5, math.nan], +1) == "unread"
    assert verdict_a2({"RENT": "unread", "BUY": "unread"}) == (None, "unread", None)
    assert verdict_a2({"RENT": "ours", "BUY": "ours", "STATE": "unread"}) == (True, "B", None)
    assert verdict_a2({"RENT": "ours", "BUY": "opposite", "STATE": "unread"}) == (True, "mixed", {"B": 1, "both_unmet": 1})
    assert verdict_a2({"RENT": "opposite", "STATE": "unread"})[:2] == (True, "both_unmet")
    assert set(MAPPING_A2) == set(STATES_A2) and MAPPING_A2["unread"] == "not placed"

    # A1 and A2 on worlds with known answers, with a floor from fewer worlds than the full run
    fl = floor_logR(data, wi, "empirical", seeds=(5,), n_world=150)
    floors = {"independent": fl, "empirical": fl}
    # the floor is a maximum over worlds: positive under noise, never lowered by more worlds, zero without noise
    fl50 = floor_logR(data, wi, "empirical", seeds=(5,), n_world=50)
    assert all(fl["floor"][k] >= fl50["floor"][k] > 0 for k in DIRECTION), "more worlds cannot lower a maximum"
    still = floor_logR(full, {**wi, "lam": 1.0}, 0.0, seeds=(5,), n_world=3)
    assert all(v < 1e-9 for v in still["floor"].values()), "no noise, no floor"
    ok, detail, _ = c_a1(data, wi, fl["floor"], n_worlds=3)
    assert ok, detail
    assert not c_a1(data, wi, fl["floor"], n_worlds=3, built=("scale_split", "scale_split"))[0],         "A1 must fail when the world that should place nothing carries a split"
    assert not c_a1(data, wi, fl["floor"], n_worlds=3, built=("cost_share", "cost_share"))[0],         "A1 must fail when the world that should place four carries none"
    assert not c_a1(data, wi, {k: 10.0 for k in ORDER}, n_worlds=3)[0],         "A1 must fail when the floor is out of reach"
    world = make_world(data, wi, np.random.default_rng(11), "cost_share")
    a2n = reading_a2(world, wi, floors, n_boot=20)
    assert verdict_a2(a2n["states"]) == (None, "unread", None), a2n["states"]
    assert c_a2(a2n)[0] is None, "A2 must not pass where the cost-share premise holds"
    world = make_world(data, wi, np.random.default_rng(12), "scale_split")
    a2s = reading_a2(world, wi, floors, n_boot=20)
    assert verdict_a2(a2s["states"])[:2] == (True, "B"), a2s["states"]
    assert c_a2(a2s)[0] is True

    # A3: a table that is one level per city plus noise puts no pair above its floor
    scalar = make_world(data, wi, np.random.default_rng(13), "scalar", noise=FLOOR_INDEPENDENT)
    assert not c_a3(reading_a3(scalar))[0], "A3 must fail on a table that is one level per city plus noise"
    assert c_a3(reading_a3(data))[0]
    u = np.array([[0.0, 0.0], [1.0, 3.0], [2.0, 2.0]])
    assert np.allclose(spreads(u), [2.0, 0.0, 2.0]), spreads(u)

    # A4 and A5: the three states, and worlds where the position rows are and are not steeper
    g = {"on_grid": {"RENT": [1.2, 0.9], "BUY": [1.5, 1.4]}, "ref_grid": [0.4, 0.5]}
    assert state_a4(g, "BUY") == "sandwich" and state_a4(g, "RENT") == "unread"
    assert state_a4({"on_grid": {"BUY": [0.8, 0.9]}, "ref_grid": [0.4, 0.5]}, "BUY") == "not there"
    assert state_a4({"on_grid": {"BUY": [1.5, 1.4]}, "ref_grid": [1.1, 1.2]}, "BUY") == "not there"
    assert set(MAPPING_A4) == set(STATES_A4) and MAPPING_A4["unread"] is None
    assert c_a4(reading_a4(a2n), "BUY")[0] is not True, "A4 must not read a sandwich where every row has its share"
    steep = make_world(data, wi, np.random.default_rng(14), "scale_split", split=8.0)
    a2t = reading_a2(steep, wi, floors, n_boot=20)
    assert c_a4(reading_a4(a2t), "BUY")[0] is True and c_a4(reading_a4(a2t), "RENT")[0] is True
    print("selftest ok: the estimator returns planted shares, attenuation cancels in R, and every flag "
          "fails on its planted input")


def main() -> int:
    data = load()
    res, objs = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    record = record_of(data, res, objs)
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(v[0] for n, v in res.items() if KINDS[n] in ("instrument", "known_answer")) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
