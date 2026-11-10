"""B144 arm B: one digital item, many account regions, and who wrote each number.

Reads what `b144_fetch.py` put in data/raw/b144/. Nothing is fetched here.

A title on a store has no local input: the same file is delivered everywhere. Its list
price is posted per account region, in that region's currency, by whoever publishes it;
the store suggests a conversion and the publisher may ignore it. The quotient

    f(title, zone) = list price in the zone / list price in the United States

is in units of local currency per dollar of United States list price. If a region had
one price level, f would be one number per zone.

Sources
  steam    1,000 paid titles (the catalogue pages of steamspy.com, which name each
           publisher) in every price zone of the store. A zone is a set of country codes
           that return the same currency and the same prices for eight reference titles.
  icloud   Apple's one page of iCloud+ prices: one writer, five tiers, every country
  gamepass Microsoft's catalogue: one writer, three subscription tiers, every market
  fx       open.er-api.com, and the ECB reference rates as a second source
  salary   the country medians of the city table read by `b144_wage_coordinates.py`

Criteria (each has a planted input in --selftest that must make it fail):
  B144-B0  instrument    every zone's files are on disk and parse; the store's United States
                         list price is the catalogue's for the median title (the unit is
                         cents); every cell of a zone carries the zone's currency
  B144-B1  rival         one conversion factor per zone. A cell is off the zone's level when
                         its price is more than one price point of that zone's own ladder
                         away from level times United States price. Passing means the
                         rival's point prediction fails on such cells at every knob point
  B144-B2  rival         who posts does not enter. Share of the variance of f, inside one
                         zone and one United States list price, that lies between
                         publishers, against the largest share any relabelling of
                         publishers returns
  B144-B3  own_reading   how many local prices one zone writes for one United States list
                         price, and how much of it sits on the most common one
  B144-B4  own_reading   the zone's level at the market exchange rate against the local
                         salary: where a posted digital title sits between a car and a
                         restaurant meal, on the same countries
  B144-B5  own_reading   zones billed in dollars that are not the United States: a class
                         value with no currency in it
  B144-B6  own_reading   three writers on the same countries: the level each writes for a
                         country at the market rate, and its slope on the local salary
  B144-B7  own_reading   one writer: the spread of Apple's five tiers across countries
                         against the spread of titles inside a Steam zone

A second store selling the same titles was probed and is not read: where the publisher,
or a parity term of the larger store, keeps a title at one price on both, the two numbers
are one number and comparing them reads that rule.

Run from the repo root:
    python experiments/b144_posted_regions.py
    python experiments/b144_posted_regions.py --selftest
"""
from __future__ import annotations

import argparse
import html
import itertools
import json
import math
import re
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144"
OUT = ROOT / "results" / "b144_posted_regions.json"

# knobs; the first value of each is the default
PRICE = ("list", "final")            # the price before a discount, or the price charged today
STEPS = (1, 2)                       # price points of slack before a cell counts as off the level
MIN_PUB = (5, 3, 8)                  # titles a publisher needs to be a writer in B2
BASE = ("tier", "zone")              # what f is measured against in B2: its zone and US list price, or its zone
MIN_TIER = 10                        # titles a zone and US list price need to be counted in B3
N_PERM = 200                         # relabellings per seed
SEEDS = (20261012, 20261013)
SUP = str.maketrans("", "", "¹²³⁴⁵⁶\U0001d112,")  # footnote marks of the Apple page

ISO_NAME = dict(x.split("=") for x in (
    "AF=Afghanistan;AL=Albania;DZ=Algeria;AD=Andorra;AO=Angola;AI=Anguilla;AG=Antigua And Barbuda;AR=Argentina;"
    "AM=Armenia;AW=Aruba;AU=Australia;AT=Austria;AZ=Azerbaijan;BS=Bahamas;BH=Bahrain;BD=Bangladesh;BB=Barbados;"
    "BY=Belarus;BE=Belgium;BZ=Belize;BJ=Benin;BM=Bermuda;BT=Bhutan;BO=Bolivia;BA=Bosnia And Herzegovina;"
    "BW=Botswana;BR=Brazil;VG=British Virgin Islands;BN=Brunei;BG=Bulgaria;BF=Burkina Faso;BI=Burundi;KH=Cambodia;"
    "CM=Cameroon;CA=Canada;CV=Cape Verde;TD=Chad;CL=Chile;CN=China;CO=Colombia;KM=Comoros;CG=Congo;CR=Costa Rica;"
    "HR=Croatia;CU=Cuba;CW=Curacao;CY=Cyprus;CZ=Czech Republic;DK=Denmark;DJ=Djibouti;DM=Dominica;"
    "DO=Dominican Republic;EC=Ecuador;EG=Egypt;SV=El Salvador;GQ=Equatorial Guinea;ER=Eritrea;EE=Estonia;"
    "ET=Ethiopia;FJ=Fiji;FI=Finland;FR=France;GA=Gabon;GM=Gambia;GE=Georgia;DE=Germany;GH=Ghana;GI=Gibraltar;"
    "GR=Greece;GL=Greenland;GT=Guatemala;GN=Guinea;GY=Guyana;HT=Haiti;HN=Honduras;HK=Hong Kong;HU=Hungary;"
    "IS=Iceland;IN=India;ID=Indonesia;IR=Iran;IQ=Iraq;IE=Ireland;IL=Israel;IT=Italy;CI=Ivory Coast;JM=Jamaica;"
    "JP=Japan;JO=Jordan;KZ=Kazakhstan;KE=Kenya;KW=Kuwait;KG=Kyrgyzstan;LA=Laos;LV=Latvia;LB=Lebanon;LS=Lesotho;"
    "LR=Liberia;LY=Libya;LI=Liechtenstein;LT=Lithuania;LU=Luxembourg;MG=Madagascar;MW=Malawi;MY=Malaysia;"
    "MV=Maldives;ML=Mali;MT=Malta;MR=Mauritania;MU=Mauritius;MX=Mexico;MD=Moldova;MC=Monaco;MN=Mongolia;"
    "ME=Montenegro;MA=Morocco;MZ=Mozambique;MM=Myanmar;NA=Namibia;NP=Nepal;NL=Netherlands;NZ=New Zealand;"
    "NI=Nicaragua;NE=Niger;NG=Nigeria;MK=North Macedonia;NO=Norway;OM=Oman;PK=Pakistan;PA=Panama;"
    "PG=Papua New Guinea;PY=Paraguay;PE=Peru;PH=Philippines;PL=Poland;PT=Portugal;PR=Puerto Rico;QA=Qatar;"
    "RO=Romania;RU=Russia;RW=Rwanda;SA=Saudi Arabia;SN=Senegal;RS=Serbia;SC=Seychelles;SL=Sierra Leone;"
    "SG=Singapore;SK=Slovakia;SI=Slovenia;SO=Somalia;ZA=South Africa;KR=South Korea;ES=Spain;LK=Sri Lanka;"
    "SD=Sudan;SR=Suriname;SZ=Swaziland;SE=Sweden;CH=Switzerland;SY=Syria;TW=Taiwan;TJ=Tajikistan;TZ=Tanzania;"
    "TH=Thailand;TG=Togo;TT=Trinidad And Tobago;TN=Tunisia;TR=Turkey;TM=Turkmenistan;UG=Uganda;UA=Ukraine;"
    "AE=United Arab Emirates;GB=United Kingdom;US=United States;UY=Uruguay;UZ=Uzbekistan;VE=Venezuela;"
    "VN=Vietnam;YE=Yemen;ZM=Zambia;ZW=Zimbabwe").split(";"))
EURO_ROW = ["Austria", "Belgium", "Cyprus", "Estonia", "Finland", "France", "Germany", "Greece", "Ireland",
            "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Portugal", "Slovakia",
            "Slovenia", "Spain"]      # the page gives the euro area one row, named Euro
APPLE_NAME = {"Republic of Korea": "South Korea", "Türkiye": "Turkey", "China mainland": "China",
              "Czechia": "Czech Republic", "Côte d'Ivoire": "Ivory Coast", "Eswatini": "Swaziland",
              "Cabo Verde": "Cape Verde", "Bosnia and Herzegovina": "Bosnia And Herzegovina",
              "Antigua and Barbuda": "Antigua And Barbuda", "Trinidad and Tobago": "Trinidad And Tobago",
              "Republic of the Congo": "Congo", "Kosovo": "Kosovo (Disputed Territory)",
              "Hong Kong": "Hong Kong", "Macedonia": "North Macedonia", "Laos": "Laos",
              "St. Kitts and Nevis": "Saint Kitts And Nevis", "St. Lucia": "Saint Lucia",
              "St. Vincent and the Grenadines": "Saint Vincent And The Grenadines",
              "Turks and Caicos": "Turks And Caicos Islands", "Sao Tome and Principe": "Sao Tome And Principe",
              "São Tomé and Príncipe": "Sao Tome And Principe",
              "Brunei Darussalam": "Brunei", "Cote D'Ivoire": "Ivory Coast", "Republic of Congo": "Congo",
              "St. Vincent and The Grenadines": "Saint Vincent And The Grenadines",
              "Virgin Islands British": "British Virgin Islands"}


def quiet(fn, a, axis=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return fn(a, axis=axis)


# ----------------------------------------------------------------------------- loading
def load_steam() -> dict:
    import b144_fetch as F
    titles, zones = F.steam_titles(), F.steam_zones()
    if titles is None or zones is None:
        raise SystemExit("steam: catalogue pages or zone probes missing; run experiments/b144_fetch.py")
    groups, no_price = [], []
    for sig, members in zones.items():
        cells = [json.loads(s) for s in sig]
        curs = Counter(c[0] for c in cells if isinstance(c, list))
        if not curs:
            no_price += members
            continue
        groups.append({"rep": F.representative(members), "members": sorted(members),
                       "currency": curs.most_common(1)[0][0]})
    groups.sort(key=lambda g: (g["rep"] != "US", g["rep"]))
    ids = [t["appid"] for t in titles]
    row = {i: k for k, i in enumerate(ids)}
    chunks = [ids[i:i + F.STEAM_CHUNK] for i in range(0, len(ids), F.STEAM_CHUNK)]
    lst = np.full((len(ids), len(groups)), np.nan)
    fin = np.full((len(ids), len(groups)), np.nan)
    missing, wrong_currency = [], 0
    for z, g in enumerate(groups):
        for k, ch in enumerate(chunks):
            p = RAW / "steam_price" / f"{g['rep']}_{k:03d}.json"
            if not p.exists():
                missing.append(p.name)
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            for i in ch:
                v = d.get(str(i))
                if isinstance(v, dict) and v.get("success") and isinstance(v.get("data"), dict) \
                        and "price_overview" in v["data"]:
                    po = v["data"]["price_overview"]
                    if po["currency"] != g["currency"]:
                        wrong_currency += 1
                        continue
                    if po["initial"] > 0:
                        lst[row[i], z] = po["initial"] / 100.0
                        fin[row[i], z] = po["final"] / 100.0
    groups, lst, fin = merge_zones(groups, lst, fin)
    return {"titles": titles, "zones": groups, "list": lst, "final": fin, "missing": missing,
            "wrong_currency": wrong_currency, "codes_without_price": sorted(no_price),
            "spy_us": np.array([t["us_list_cents"] / 100.0 for t in titles]),
            "publisher": [t["publisher"] for t in titles]}


def merge_zones(groups, lst, fin, least: int = 50):
    """Two zones with one currency and one price for every title both sell are one zone.

    The probes tell zones apart on eight titles, and a title that is not sold in a country
    makes that country look like a zone of its own.
    """
    keep = list(range(len(groups)))
    home = {}
    for j in range(len(groups)):
        for i in keep:
            if i >= j or i in home:
                continue
            if groups[i]["currency"] != groups[j]["currency"]:
                continue
            both = ~np.isnan(lst[:, i]) & ~np.isnan(lst[:, j])
            if both.sum() >= least and np.array_equal(lst[both, i], lst[both, j]):
                home[j] = i
                break
    out_g, cols = [], []
    for i in range(len(groups)):
        if i in home:
            continue
        mine = [i] + [j for j, h in home.items() if h == i]
        g = dict(groups[i])
        g["members"] = sorted(c for k in mine for c in groups[k]["members"])
        out_g.append(g)
        cols.append(mine)
    def fold(m):
        out = np.full((m.shape[0], len(cols)), np.nan)
        for k, mine in enumerate(cols):
            for j in mine:
                out[:, k] = np.where(np.isnan(out[:, k]), m[:, j], out[:, k])
        return out
    return out_g, fold(lst), fold(fin)


def load_gamepass() -> dict:
    """Per market: currency and the price the source calls MSRP, for the three tiers."""
    out = {}
    for p in sorted((RAW / "gamepass").glob("*.json")):
        prods = {}
        for pr in json.loads(p.read_text(encoding="utf-8")).get("Products", []):
            for sku in pr.get("DisplaySkuAvailabilities", []):
                price = next((a["OrderManagementData"]["Price"] for a in sku.get("Availabilities", [])
                              if a.get("OrderManagementData", {}).get("Price", {}).get("MSRP")), None)
                if price:
                    prods[pr["ProductId"]] = (float(price["MSRP"]), price["CurrencyCode"])
                    break
        if prods:
            out[p.stem] = prods
    return out


def money(s: str) -> float:
    """The number in a posted price: '$0.99', '9 kr', 'E£49.99', '₫25000', '1.100', '5,90'."""
    m = re.search(r"\d[\d.,  ']*", s)
    if not m:
        return math.nan
    t = re.sub(r"[  ']", "", m.group(0)).rstrip(".,")
    dec = re.search(r"[.,](\d{1,2})$", t)
    if dec:
        whole = re.sub(r"[.,]", "", t[:dec.start()])
        return float(f"{whole}.{dec.group(1)}")
    return float(re.sub(r"[.,]", "", t))


def load_icloud() -> dict:
    p = RAW / "icloud_108047.html"
    t = p.read_text(encoding="utf-8", errors="replace")

    def clean(s):
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    rows, header, unparsed = [], None, []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
        if len(cells) != 6:
            continue
        m = re.match(r"^(.*?)\s*\(([A-Z]{3}|Euro)\)\s*\d*$", cells[0])
        if not m:
            if header is None:
                header = cells
            else:
                unparsed.append(cells[0])
            continue
        raw_name = m.group(1)
        name = re.sub(r"\s*\d+$", "", raw_name.translate(SUP).strip())     # a footnote number after the name
        rows.append({"country": name, "currency": "EUR" if m.group(2) == "Euro" else m.group(2),
                     "tax_included": "³" in raw_name,
                     "tax_may_be_added": "²" in raw_name, "prices": [money(c) for c in cells[1:]]})
    text = clean(t)
    return {"rows": rows, "header": header, "unparsed": [u for u in unparsed if u != (header or [""])[0]],
            "footnote_tax_added": "may be slightly higher due to the Value Added Tax" in text,
            "footnote_tax_included": "Taxes are included in all prices" in text,
            "footnote_vintage": "Existing iCloud plans as of August 21, 2024 continue to be billed at the "
                                "subscription price at the time of initial purchase" in text}


def load_fx() -> dict:
    main = json.loads((RAW / "fx_open_er_api.json").read_text(encoding="utf-8"))
    ecb_txt = (RAW / "fx_ecb.xml").read_text(encoding="utf-8", errors="replace")
    per_eur = {m.group(1): float(m.group(2)) for m in re.finditer(r"currency='([A-Z]{3})' rate='([0-9.]+)'", ecb_txt)}
    ecb = {}
    if "USD" in per_eur:
        ecb = {c: v / per_eur["USD"] for c, v in per_eur.items()}
        ecb["EUR"] = 1.0 / per_eur["USD"]
        ecb["USD"] = 1.0
    return {"main": {**main["rates"], "USD": 1.0}, "ecb": ecb, "main_date": main.get("time_last_update_utc"),
            "ecb_date": (re.search(r"time='([0-9-]+)'", ecb_txt) or [None, None])[1]}


def load_salary() -> dict:
    import b144_wage_coordinates as A
    data = A.load()
    st = A.stats_of(data)
    return {"index": {c: i for i, c in enumerate(data["countries"])}, "logw": st["wmed"], "med": st["med"],
            "idx": A.IDX, "cols": A.COLS}


def load() -> dict:
    return {"steam": load_steam(), "gamepass": load_gamepass(), "icloud": load_icloud(), "fx": load_fx(),
            "salary": load_salary()}


# ----------------------------------------------------------------------------- pieces
def factors(prices: np.ndarray) -> np.ndarray:
    """f(title, zone); column 0 is the United States zone."""
    with np.errstate(all="ignore"):
        return prices / prices[:, [0]]


def off_level(prices: np.ndarray, steps: int):
    """Cells more than `steps` price points of their zone's own ladder away from level times US price."""
    f = factors(prices)
    off = np.zeros(prices.shape, dtype=bool)
    read = np.zeros(prices.shape, dtype=bool)
    level = quiet(np.nanmedian, f, axis=0)
    for z in range(1, prices.shape[1]):
        col = prices[:, z]
        ok = ~np.isnan(col) & ~np.isnan(prices[:, 0])
        ladder = np.unique(col[~np.isnan(col)])
        if ladder.size < 2 or not np.isfinite(level[z]):
            continue
        ref = level[z] * prices[ok, 0]
        near = np.abs(ladder[None, :] - ref[:, None]).argmin(axis=1)
        here = np.searchsorted(ladder, col[ok])
        off[ok, z] = np.abs(here - near) > steps
        read[ok, z] = True
    return off, read, level


def tier_base(logf: np.ndarray, us: np.ndarray, base: str, least: int = 3) -> np.ndarray:
    """log f minus the median of its zone and US list price (or of its zone)."""
    out = np.full(logf.shape, np.nan)
    if base == "zone":
        return logf - quiet(np.nanmedian, logf, axis=0)[None, :]
    for tier in np.unique(us[~np.isnan(us)]):
        rows = np.where(us == tier)[0]
        if rows.size < least:
            continue
        out[rows] = logf[rows] - quiet(np.nanmedian, logf[rows], axis=0)[None, :]
    return out


def eta2(resid: np.ndarray, labels: np.ndarray) -> float:
    """Share of the variance of resid, zone by zone, that lies between the labelled groups."""
    ssb = sst = 0.0
    for z in range(1, resid.shape[1]):
        e = resid[:, z]
        ok = ~np.isnan(e) & (labels >= 0)
        if ok.sum() < 3:
            continue
        ee, ll = e[ok], labels[ok]
        mu = ee.mean()
        sst += float(((ee - mu) ** 2).sum())
        n = np.bincount(ll)
        s = np.bincount(ll, weights=ee)
        keep = n > 0
        ssb += float((n[keep] * (s[keep] / n[keep] - mu) ** 2).sum())
    return ssb / sst if sst > 0 else math.nan


def writer_labels(publisher, min_pub: int) -> np.ndarray:
    count = Counter(publisher)
    names = sorted(p for p, n in count.items() if n >= min_pub)
    code = {p: i for i, p in enumerate(names)}
    return np.array([code.get(p, -1) for p in publisher]), names


def reading_b2(steam, n_perm=N_PERM, seeds=SEEDS):
    us = steam["list"][:, 0]
    grid = []
    for price, min_pub, base in itertools.product(PRICE, MIN_PUB, BASE):
        with np.errstate(all="ignore"):
            logf = np.log(factors(steam[price]))
        resid = tier_base(logf, us, base)
        labels, names = writer_labels(steam["publisher"], min_pub)
        obs = eta2(resid, labels)
        null = []
        for s in seeds:
            rng = np.random.default_rng(s)
            pool = np.where(labels >= 0)[0]
            for _ in range(n_perm):
                lab = labels.copy()
                lab[pool] = labels[rng.permutation(pool)]
                null.append(eta2(resid, lab))
        grid.append({"price": price, "min_pub": min_pub, "base": base, "writers": len(names),
                     "titles": int((labels >= 0).sum()), "eta2": obs, "null_max": max(null),
                     "null_min": min(null), "null_median": float(np.median(null))})
    return grid


def writers_table(steam):
    """Per publisher: how far its titles sit from the common local price of their zone and US list price."""
    with np.errstate(all="ignore"):
        resid = tier_base(np.log(factors(steam["list"])), steam["list"][:, 0], "tier")[:, 1:]
    labels, names = writer_labels(steam["publisher"], MIN_PUB[0])
    rows = []
    for k, name in enumerate(names):
        v = resid[labels == k]
        v = v[np.isfinite(v)]
        if v.size:
            rows.append({"publisher": name, "titles": int((labels == k).sum()), "cells": int(v.size),
                         "median": float(np.median(v)), "p25": float(np.quantile(v, 0.25)),
                         "p75": float(np.quantile(v, 0.75)), "on_the_common_price": float((np.abs(v) < 1e-9).mean())})
    return sorted(rows, key=lambda r: r["median"])


STATES_B2 = {"ours": "above the largest share any relabelling returns, at every knob point",
             "opposite": "below the smallest share any relabelling returns, at every knob point",
             "unread": "inside the relabelling range somewhere on the knob grid"}
MAPPING_B2 = {"ours": "B", "opposite": "both_unmet", "unread": "not placed"}


def state_b2(grid) -> str:
    if grid and all(g["eta2"] > g["null_max"] for g in grid):
        return "ours"
    if grid and all(g["eta2"] < g["null_min"] for g in grid):
        return "opposite"
    return "unread"


def counting(prices: np.ndarray, least: int = MIN_TIER):
    """Per zone and US list price: how many local prices are written, and the share of the commonest."""
    cells = []
    us = prices[:, 0]
    for z in range(1, prices.shape[1]):
        for tier in np.unique(us[~np.isnan(us)]):
            v = prices[(us == tier) & ~np.isnan(prices[:, z]), z]
            if v.size < least:
                continue
            c = Counter(v.tolist())
            cells.append({"zone": z, "tier": float(tier), "titles": int(v.size), "distinct": len(c),
                          "modal_share": c.most_common(1)[0][1] / v.size})
    return cells


def zone_salary(zone, sal):
    v = [sal["logw"][sal["index"][ISO_NAME[c]]] for c in zone["members"]
         if ISO_NAME.get(c) in sal["index"] and np.isfinite(sal["logw"][sal["index"][ISO_NAME[c]]])]
    return float(np.median(v)) if v else math.nan


def zone_item(zone, sal, col):
    v = [sal["med"][sal["index"][ISO_NAME[c]], col] for c in zone["members"] if ISO_NAME.get(c) in sal["index"]]
    v = [x for x in v if np.isfinite(x)]
    return float(np.median(v)) if v else math.nan


def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3 or np.ptp(x[ok]) == 0:
        return math.nan, int(ok.sum())
    xx, yy = x[ok] - x[ok].mean(), y[ok] - y[ok].mean()
    return float((xx * yy).sum() / (xx * xx).sum()), int(ok.sum())


COMPARE = {"car, Corolla": "x35", "car, Golf": "x34", "fast-food combo": "x3", "restaurant meal": "x1"}


SCOPES = ("all zones", "one country", "with the codes billed at the United States price")


def reading_b4(data):
    """Slope of the zone's level, at a market rate, on the local salary; the same for four table rows.

    The United States zone also holds every code the store wrote no regional price for. In the third
    scope those codes enter as one more zone, at a level of one and at their own median salary.
    """
    steam, fx, sal = data["steam"], data["fx"], data["salary"]
    zs = list(steam["zones"])
    rest = dict(zs[0], members=[c for c in zs[0]["members"] if c != "US"])
    wage = np.array([zone_salary(z, sal) for z in zs])
    out = []
    for price, source, scope in itertools.product(PRICE, ("main", "ecb"), SCOPES):
        rate = np.array([fx[source].get(z["currency"], math.nan) for z in zs])
        with np.errstate(all="ignore"):
            level = quiet(np.nanmedian, np.log(factors(steam[price])), axis=0) - np.log(rate)
        use = np.arange(len(zs)) > 0
        if scope == "one country":
            use &= np.array([len(z["members"]) == 1 for z in zs])
        zones = [z for z, u in zip(zs, use) if u]
        x, y = list(wage[use]), list(level[use])
        if scope == SCOPES[2] and rest["members"]:
            zones, x, y = zones + [rest], x + [zone_salary(rest, sal)], y + [0.0]
        seen = [k for k in range(len(zones)) if np.isfinite(x[k]) and np.isfinite(y[k])]
        zones, x, y = [zones[k] for k in seen], [x[k] for k in seen], [y[k] for k in seen]
        b, n = ols(x, y)                                   # the table rows are read on the same zones
        rows = {name: ols(x, [zone_item(z, sal, sal["idx"][col]) for z in zones])[0]
                for name, col in COMPARE.items()}
        out.append({"price": price, "fx": source, "scope": scope, "zones": n, "steam": b, **rows})
    level0 = quiet(np.nanmedian, np.log(factors(steam["list"])), axis=0) - np.log(
        np.array([fx["main"].get(z["currency"], math.nan) for z in zs]))
    return out, wage, level0, {"codes": len(rest["members"]), "log_salary": zone_salary(rest, sal)}


STATES_B4 = {"between": "above both cars and below the restaurant meal at every knob point",
             "outside": "below a car or above the restaurant meal at every knob point",
             "unread": "its place among the rows changes somewhere on the knob grid, or a slope is undefined"}
MAPPING_B4 = {"between": True, "outside": False, "unread": None}


def state_b4(grid) -> str:
    def inside(g):
        v = [g["steam"], g["car, Corolla"], g["car, Golf"], g["restaurant meal"]]
        if not all(np.isfinite(v)):
            return None
        return max(g["car, Corolla"], g["car, Golf"]) < g["steam"] < g["restaurant meal"]
    r = [inside(g) for g in grid]
    if not r or any(x is None for x in r):
        return "unread"
    if all(r):
        return "between"
    if not any(r):
        return "outside"
    return "unread"


def icloud_matrix(ic):
    rows = [r for r in ic["rows"] if all(np.isfinite(r["prices"])) and min(r["prices"]) > 0]
    return rows, np.log(np.array([r["prices"] for r in rows]))


def two_way_sd(m: np.ndarray) -> float:
    fit = m.mean(axis=1, keepdims=True) + m.mean(axis=0, keepdims=True) - m.mean()
    return float((m - fit).std())


# ----------------------------------------------------------------------------- criteria
def c_b0(data):
    s = data["steam"]
    us = s["list"][:, 0]
    both = ~np.isnan(us) & (s["spy_us"] > 0)
    ratio = us[both] / s["spy_us"][both]
    unit = float(np.median(ratio)) if both.any() else math.nan
    same = int((np.abs(ratio - 1) < 1e-9).sum())
    cover = int((~np.isnan(s["list"])).sum())
    passed = (not s["missing"]) and unit == 1.0 and s["wrong_currency"] == 0 and len(s["zones"]) > 1
    detail = (f"{len(s['titles'])} titles in {len(s['zones'])} zones over "
              f"{sum(len(z['members']) for z in s['zones'])} country codes, "
              f"{len({z['currency'] for z in s['zones']})} currencies; {cover} cells carry a list price; "
              f"files missing: {len(s['missing'])}; cells in another currency than their zone's: "
              f"{s['wrong_currency']}; store over catalogue United States list price, median {unit:g}, "
              f"equal for {same} of {int(both.sum())}; codes that return no price: {len(s['codes_without_price'])}")
    return passed, detail, {"codes_without_price": s["codes_without_price"]}


def c_b1(data):
    s = data["steam"]
    grid = []
    for price, steps in itertools.product(PRICE, STEPS):
        off, read, level = off_level(s[price], steps)
        grid.append({"price": price, "steps": steps, "read": int(read.sum()), "off": int(off.sum())})
    off, read, level = off_level(s["list"], STEPS[0])
    with np.errstate(all="ignore"):
        dev = np.abs(np.log(factors(s["list"])) - np.log(level)[None, :])[:, 1:]
    dev = dev[np.isfinite(dev)]
    if not dev.size:
        return None, "no cell carries both a local and a United States list price", {"grid": "unread", "knobs": grid,
                                                                                    "by_zone": []}
    by_zone = sorted(((off[:, z].sum() / max(read[:, z].sum(), 1), s["zones"][z]["rep"])
                      for z in range(1, len(s["zones"])) if read[:, z].sum()), reverse=True)
    if all(g["off"] > 0 for g in grid):
        passed, cell = True, "B"
    elif all(g["off"] == 0 for g in grid):
        passed, cell = False, "A"
    else:
        passed, cell = None, "unread"
    d0 = grid[0]
    detail = (f"{d0['off']} of {d0['read']} cells are more than one price point of their zone's ladder away "
              f"from the zone's level times the United States price ({100 * d0['off'] / max(d0['read'], 1):.1f}%); "
              f"over the knob grid {min(g['off'] / max(g['read'], 1) for g in grid) * 100:.1f}% to "
              f"{max(g['off'] / max(g['read'], 1) for g in grid) * 100:.1f}%. Distance from the level in logs: "
              f"median {float(np.median(dev)):.3f}, ninth decile {float(np.quantile(dev, 0.9)):.3f}. "
              f"Most off: {', '.join(f'{r} {100 * v:.0f}%' for v, r in by_zone[:3])}; least: "
              f"{', '.join(f'{r} {100 * v:.0f}%' for v, r in by_zone[-3:])}")
    return passed, detail, {"grid": cell, "knobs": grid,
                            "by_zone": [{"zone": r, "share_off": round(float(v), 4)} for v, r in by_zone]}


def c_b2(grid):
    state = state_b2(grid)
    cell = MAPPING_B2[state]
    passed = None if cell == "not placed" else True
    d0 = grid[0]
    detail = (f"share of variance between publishers {d0['eta2']:.3f} ({d0['writers']} publishers with "
              f"{MIN_PUB[0]} or more titles, {d0['titles']} titles); relabelled publishers return at most "
              f"{d0['null_max']:.3f} (median {d0['null_median']:.3f}) in {N_PERM * len(SEEDS)} relabellings; "
              f"over {len(grid)} knob points the share is {min(g['eta2'] for g in grid):.3f} to "
              f"{max(g['eta2'] for g in grid):.3f} against a largest relabelled share of "
              f"{max(g['null_max'] for g in grid):.3f} -> {state}")
    return passed, detail, {"grid": "unread" if cell == "not placed" else cell, "state": state}


def c_b3(data):
    s = data["steam"]
    cells = counting(s["list"])
    more = sum(c["distinct"] > 1 for c in cells)
    passed = more > 0
    if not cells:
        return False, "no zone and United States list price with enough titles", {"cells": []}
    by_zone = defaultdict(list)
    for c in cells:
        by_zone[s["zones"][c["zone"]]["rep"]].append(c["modal_share"])
    rank = sorted((float(np.median(v)), z) for z, v in by_zone.items())
    detail = (f"{len(cells)} cells of one zone and one United States list price with {MIN_TIER} or more titles; "
              f"local prices written per cell: median {int(np.median([c['distinct'] for c in cells]))}, largest "
              f"{max(c['distinct'] for c in cells)}; {more} cells carry more than one; share on the commonest "
              f"price: median {np.median([c['modal_share'] for c in cells]):.2f}. Zones by that share: lowest "
              f"{', '.join(f'{z} {v:.2f}' for v, z in rank[:3])}; highest "
              f"{', '.join(f'{z} {v:.2f}' for v, z in rank[-3:])}")
    return passed, detail, {"zones": [{"zone": z, "median_modal_share": round(v, 4)} for v, z in rank]}


def c_b4(data):
    grid, wage, level, rest = reading_b4(data)
    state = state_b4(grid)
    g0 = grid[0]
    detail = (f"{g0['zones']} zones with a salary and a market rate; slope of the zone's level on log salary "
              f"{g0['steam']:.3f} ({min(g['steam'] for g in grid):.3f} to {max(g['steam'] for g in grid):.3f} over "
              f"{len(grid)} knob points). Same zones, rows of the city table: "
              + "; ".join(f"{k} {g0[k]:.3f}" for k in COMPARE) + f" -> {state}. {rest['codes']} more codes "
              f"are billed at the United States price in dollars; as one more zone they enter the third scope")
    return MAPPING_B4[state], detail, {"state": state, "knobs": grid, "wage": wage, "level": level, "rest": rest}


def c_b5(data):
    s = data["steam"]
    f = factors(s["list"])
    rows = []
    for z, zone in enumerate(s["zones"]):
        if z == 0 or zone["currency"] != "USD":
            continue
        v = f[:, z][np.isfinite(f[:, z])]
        if not v.size:
            continue
        rows.append({"zone": zone["rep"], "codes": len(zone["members"]), "titles": int(v.size),
                     "median_f": float(np.median(v)), "p25": float(np.quantile(v, 0.25)),
                     "p75": float(np.quantile(v, 0.75)), "at_us_price": int((np.abs(v - 1) < 1e-9).sum()),
                     "distinct_f": int(np.unique(np.round(v, 4)).size)})
    passed = any(abs(r["median_f"] - 1) > 1e-9 for r in rows)
    detail = (f"{len(rows)} zones are billed in dollars and are not the United States: "
              + "; ".join(f"{r['zone']} ({r['codes']} codes) median {r['median_f']:.2f} of the United States "
                          f"price, {r['at_us_price']} of {r['titles']} titles at it" for r in rows)) \
        if rows else "no zone billed in dollars besides the United States"
    return passed, detail, {"zones": rows}


def writer_levels(data):
    """Country by writer: log of what the country is charged over the United States, at the market rate."""
    s, fx, sal = data["steam"], data["fx"]["main"], data["salary"]
    with np.errstate(all="ignore"):
        zone_level = quiet(np.nanmedian, np.log(factors(s["list"])), axis=0)
    steam = {}
    for k, z in enumerate(s["zones"]):
        if z["currency"] not in fx or not np.isfinite(zone_level[k]):
            continue
        for c in z["members"]:
            if c in ISO_NAME:
                steam[ISO_NAME[c]] = float(zone_level[k] - math.log(fx[z["currency"]]))
    apple = {}
    rows, m = icloud_matrix(data["icloud"])
    us = next((i for i, r in enumerate(rows) if r["country"] == "United States"), None)
    if us is not None:
        for i, r in enumerate(rows):
            if r["currency"] not in fx:
                continue
            level = float(np.median(m[i] - m[us]) - math.log(fx[r["currency"]]))
            for name in (EURO_ROW if r["country"] == "Euro" else [APPLE_NAME.get(r["country"], r["country"])]):
                apple[name] = level
    micro = {}
    gp = data["gamepass"]
    if "US" in gp:
        for c, prods in gp.items():
            v = [math.log(pr[0] / gp["US"][k][0]) - math.log(fx[pr[1]]) for k, pr in prods.items()
                 if k in gp["US"] and pr[1] in fx]
            if v and c in ISO_NAME:
                micro[ISO_NAME[c]] = float(np.median(v))
    return {"store titles": steam, "storage tiers": apple, "game subscription": micro}


def c_b6(data):
    lv, sal = writer_levels(data), data["salary"]
    names = list(lv)
    common = sorted(c for c in set.intersection(*(set(v) for v in lv.values()))
                    if c in sal["index"] and np.isfinite(sal["logw"][sal["index"][c]]) and c != "United States")
    if len(common) < 3:
        return False, f"{len(common)} countries carry all three writers and a salary", {"countries": []}
    m = np.array([[lv[w][c] for w in names] for c in common])
    wage = np.array([sal["logw"][sal["index"][c]] for c in common])
    slopes = {w: ols(wage, m[:, k])[0] for k, w in enumerate(names)}
    rows = {name: ols(wage, [sal["med"][sal["index"][c], sal["idx"][x]] for c in common])[0]
            for name, x in COMPARE.items()}
    gaps = {f"{names[a]} minus {names[b]}": float((m[:, a] - m[:, b]).std())
            for a, b in itertools.combinations(range(len(names)), 2)}
    resid = m - m.mean(axis=1, keepdims=True) - m.mean(axis=0, keepdims=True) + m.mean()
    passed = float(resid.std()) > 1e-9
    detail = (f"{len(common)} countries carry all three writers and a salary. Slope of the written level on log "
              f"salary: " + "; ".join(f"{w} {v:.3f}" for w, v in slopes.items())
              + ". Same countries, rows of the city table: " + "; ".join(f"{k} {v:.3f}" for k, v in rows.items())
              + ". Spread across countries of the gap between two writers, in logs: "
              + "; ".join(f"{k} {v:.3f}" for k, v in gaps.items())
              + f". Left after a level per country and a level per writer: sd {float(resid.std()):.3f}")
    return passed, detail, {"countries": common, "writers": names, "levels": m, "slopes": slopes,
                            "table_rows": rows, "gap_sd": gaps, "residual_sd": float(resid.std())}


def c_b7(data):
    ic, s = data["icloud"], data["steam"]
    rows, m = icloud_matrix(ic)
    if len(rows) < 3:
        return False, "the one-writer table did not parse", {}
    sd_one = two_way_sd(m)
    with np.errstate(all="ignore"):
        logf = np.log(factors(s["list"]))[:, 1:]
    sd_many = float(quiet(np.nanstd, logf - quiet(np.nanmedian, logf, axis=0)[None, :]))
    usd = [r for r in rows if r["currency"] == "USD"]
    tuples = Counter(tuple(r["prices"]) for r in usd)
    us_row = next((r for r in rows if r["country"] == "United States"), None)
    at_us = tuples.get(tuple(us_row["prices"]), 0) if us_row else 0
    passed = sd_one < sd_many
    detail = (f"{len(rows)} countries by 5 tiers, {len({r['currency'] for r in rows})} currencies, "
              f"{sum(r['tax_included'] for r in rows)} rows with tax included; residual of country plus tier in "
              f"logs, sd {sd_one:.4f}; titles inside a zone of the many-writer store, sd {sd_many:.4f}. "
              f"{len(usd)} countries are billed in dollars and carry {len(tuples)} different sets of five prices, "
              f"{at_us} of them the United States set. The page keeps earlier subscribers in one country on the "
              f"price of their purchase date: {'stated' if ic['footnote_vintage'] else 'not found'}")
    return passed, detail, {"sd_one_writer": sd_one, "sd_many_writers": sd_many,
                            "usd_price_sets": [{"prices": list(k), "countries": v} for k, v in tuples.most_common()]}


KINDS = {"B144-B0": "instrument", "B144-B1": "rival", "B144-B2": "rival", "B144-B3": "own_reading",
         "B144-B4": "own_reading", "B144-B5": "own_reading", "B144-B6": "own_reading", "B144-B7": "own_reading"}
STATEMENTS = {
    "B144-B0": "The cache is complete and reads in the units it is taken to be in.",
    "B144-B1": "One conversion factor per zone does not hold: cells stand more than a price point away from "
               "the zone's level. Passing means the rival is wrong here (`11e`).",
    "B144-B2": "Who posts a title enters its regional factor: publishers explain more of it than any "
               "relabelling of publishers. Passing means the rival is wrong here (`11e`).",
    "B144-B3": "One zone and one United States list price carry more than one local price.",
    "B144-B4": "Against the local salary a posted digital title is steeper than a car and flatter than a "
               "restaurant meal.",
    "B144-B5": "Zones billed in dollars carry a price that is not the United States price.",
    "B144-B6": "Three writers do not write one level per country: what a country is charged against the "
               "United States differs by who writes the number.",
    "B144-B7": "One writer's five tiers vary across countries less than many writers' titles vary inside a zone.",
}
RIVALS = {
    "B144-B1": {"rival_shape": "point prediction",
                "rival_premise": "An account region has one price level against the United States, and a title "
                                 "with no local input sells there at its United States list price times that level.",
                "rival_entailment": "Then local list price over United States list price is one number per region "
                                    "for every title, up to the spacing of the price points in use there."},
    "B144-B2": {"rival_shape": "point prediction",
                "rival_premise": "The local price of a title is set by the region: its level against the United "
                                 "States is what buyers there can pay, and who posts the title does not enter.",
                "rival_entailment": "Then inside one region and one United States list price the deviations of "
                                    "titles from the common level are unrelated to the publisher, and the share of "
                                    "their variance between publishers is what a relabelling of publishers gives."},
}


def run(data):
    b2 = reading_b2(data["steam"])
    res = {"B144-B0": c_b0(data), "B144-B1": c_b1(data), "B144-B2": c_b2(b2), "B144-B3": c_b3(data),
           "B144-B4": c_b4(data), "B144-B5": c_b5(data), "B144-B6": c_b6(data), "B144-B7": c_b7(data)}
    res = {k: (None if v[0] is None else bool(v[0]), v[1], v[2]) for k, v in res.items()}
    return res, {"b2": b2, "writers": writers_table(data["steam"])}


def r4(x):
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else round(float(x), 4)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, dict):
        return {k: r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    if isinstance(x, np.ndarray):
        return [r4(v) for v in x.tolist()]
    return x


def record_of(data, res, objs):
    s = data["steam"]
    crit = []
    for name, (passed, detail, obj) in res.items():
        c = {"name": name, "kind": KINDS[name], "passed": passed, "statement": STATEMENTS[name], "detail": detail}
        if name in RIVALS:
            c.update(RIVALS[name])
            c["grid"] = obj["grid"]
        crit.append(c)
    b4 = res["B144-B4"][2]
    zones = [{"zone": z["rep"], "currency": z["currency"], "codes": z["members"],
              "titles_priced": int((~np.isnan(s["list"][:, k])).sum()),
              "log_salary": r4(b4["wage"][k]), "level_at_market_rate": r4(b4["level"][k])}
             for k, z in enumerate(s["zones"])]
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": crit,
        "mapping": {"B144-B1": {"B": "cells off the level at every knob point", "A": "no cell off the level at "
                                "any knob point", "unread": "off at some knob points and not at others"},
                    "B144-B2": {"states": STATES_B2, "state_to_cell": MAPPING_B2},
                    "B144-B4": {"states": STATES_B4, "state_to_verdict": MAPPING_B4}},
        "objects": {"zones": zones,
                    "B144-B0": r4(res["B144-B0"][2]), "B144-B1": r4(res["B144-B1"][2]),
                    "B144-B2": r4(objs["b2"]), "publishers": r4(objs["writers"]),
                    "B144-B3": r4(res["B144-B3"][2]),
                    "B144-B4": r4(b4["knobs"]), "billed_at_us_price": r4(b4["rest"]),
                    "B144-B5": r4(res["B144-B5"][2]),
                    "B144-B6": r4(res["B144-B6"][2]), "B144-B7": r4(res["B144-B7"][2])},
        "config": {"raw": "data/raw/b144", "fetched_by": "experiments/b144_fetch.py",
                   "knobs": {"price": list(PRICE), "steps": list(STEPS), "min_pub": list(MIN_PUB),
                             "base": list(BASE)},
                   "min_tier": MIN_TIER, "n_perm": N_PERM, "seeds": list(SEEDS),
                   "fx_dates": {"main": data["fx"]["main_date"], "ecb": data["fx"]["ecb_date"]},
                   "salary_from": "experiments/b144_wage_coordinates.py, country medians"},
    }


# ----------------------------------------------------------------------------- selftest
def toy(kind: str, seed: int = 1, n_titles: int = 240, n_zones: int = 6):
    """A small store whose answer is known.

    scalar   every title sells at its US price times one factor per zone, on a ladder of .99 points
    writers  each of twelve publishers applies its own factor per zone to all its titles
    noise    each title has its own factor per zone, unrelated to its publisher
    """
    rng = np.random.default_rng(seed)
    tiers = np.array([4.99, 9.99, 14.99, 19.99, 29.99, 39.99, 59.99])
    us = rng.choice(tiers, size=n_titles)
    pub = [f"P{i % 12}" for i in range(n_titles)]
    level = np.concatenate([[1.0], rng.uniform(0.4, 150.0, size=n_zones - 1)])
    f = np.tile(level, (n_titles, 1))
    if kind == "writers":
        house = np.exp(rng.normal(0, 0.25, size=(12, n_zones)))
        house[:, 0] = 1.0
        f = f * house[[i % 12 for i in range(n_titles)]]
    if kind == "noise":
        own = np.exp(rng.normal(0, 0.25, size=(n_titles, n_zones)))
        own[:, 0] = 1.0
        f = f * own
    raw = us[:, None] * f
    step = 10.0 ** np.floor(np.log10(raw)) / 10.0          # the ladder: two significant digits, ending in .99
    prices = np.where(raw >= 1, np.floor(raw / step) * step + step - 0.01, np.round(raw, 2))
    prices[:, 0] = us
    zones = [{"rep": "US", "members": ["US"], "currency": "USD"}] + \
            [{"rep": f"Z{k}", "members": [f"Z{k}"], "currency": f"C{k}"} for k in range(1, n_zones)]
    return {"titles": [{"appid": i, "name": f"t{i}", "publisher": pub[i]} for i in range(n_titles)],
            "zones": zones, "list": prices, "final": prices.copy(), "missing": [], "wrong_currency": 0,
            "codes_without_price": [], "spy_us": us.copy(), "publisher": pub}


def selftest() -> None:
    # parsing
    assert money("$0.99") == 0.99 and money("9 kr") == 9.0 and money("E£49.99") == 49.99
    assert money("₫25000") == 25000.0 and money("1.99 лв") == 1.99 and money("R$ 5,90") == 5.9
    assert money("1.100") == 1100.0 and money("₩1,100") == 1100.0 and math.isnan(money("free"))

    # B0: a missing file, a unit that is off by a hundred, a cell in a foreign currency
    base = {"steam": toy("writers")}
    assert c_b0(base)[0], c_b0(base)[1]
    for change in ({"missing": ["x.json"]}, {"spy_us": base["steam"]["spy_us"] * 100}, {"wrong_currency": 3}):
        assert not c_b0({"steam": {**base["steam"], **change}})[0], f"B0 must fail on {list(change)}"

    # B1: a store with one factor per zone has no cell off its level; one with house factors has
    passed, detail, obj = c_b1({"steam": toy("scalar")})
    assert passed is False and obj["grid"] == "A", detail
    passed, detail, obj = c_b1({"steam": toy("writers")})
    assert passed is True and obj["grid"] == "B", detail
    off, read, level = off_level(toy("scalar")["list"], 1)
    assert read[:, 1:].all() and not read[:, 0].any() and not off.any()

    # B2: publishers explain the factor where they write it, and do not where each title has its own
    g_w = reading_b2(toy("writers"), n_perm=40, seeds=(3,))
    g_n = reading_b2(toy("noise"), n_perm=40, seeds=(3,))
    assert state_b2(g_w) == "ours" and c_b2(g_w)[0] is True, g_w[0]
    assert state_b2(g_n) == "unread" and c_b2(g_n)[0] is None, g_n[0]
    assert state_b2([{"eta2": 0.01, "null_max": 0.2, "null_min": 0.05}]) == "opposite"
    assert set(MAPPING_B2) == set(STATES_B2) and MAPPING_B2["unread"] == "not placed"
    lab = np.array([0, 0, 1, 1, -1])
    r = np.array([[0, 1.0], [0, 1.0], [0, 3.0], [0, 3.0], [0, 9.0]])
    assert abs(eta2(r, lab) - 1.0) < 1e-12, "all variance between two groups"
    r2 = np.array([[0, 1.0], [0, 3.0], [0, 1.0], [0, 3.0], [0, 9.0]])
    assert abs(eta2(r2, lab)) < 1e-12, "no variance between two groups"
    assert np.allclose(tier_base(np.array([[0, 1.0], [0, 2.0], [0, 6.0]]), np.array([5.0, 5.0, 5.0]), "tier")[:, 1],
                       [-1.0, 0.0, 4.0])

    # B3: a zone that follows one table writes one price per tier
    assert not c_b3({"steam": toy("scalar")})[0], "B3 must fail where every tier has one local price"
    assert c_b3({"steam": toy("writers")})[0]

    # B4: the three states
    row = {"car, Corolla": 0.05, "car, Golf": 0.1, "restaurant meal": 0.5}
    assert state_b4([{**row, "steam": 0.3}, {**row, "steam": 0.2}]) == "between"
    assert state_b4([{**row, "steam": 0.3}, {**row, "steam": 0.6}]) == "unread"
    assert state_b4([{**row, "steam": 0.01}, {**row, "steam": 0.7}]) == "outside"
    assert state_b4([{**row, "steam": math.nan}]) == "unread"
    assert set(MAPPING_B4) == set(STATES_B4) and MAPPING_B4["unread"] is None
    assert abs(ols([0, 1, 2, 3], [1, 3, 5, 7])[0] - 2.0) < 1e-12

    # B5: dollar zones at the United States price carry no class value
    t = toy("scalar")
    t["zones"][1]["currency"] = "USD"
    t["list"][:, 1] = t["list"][:, 0]
    assert not c_b5({"steam": t})[0], "B5 must fail when the dollar zone is at the United States price"
    t["list"][:, 1] = np.round(t["list"][:, 0] * 0.6, 2)
    assert c_b5({"steam": t})[0]

    # B6: three writers that write one level per country leave nothing; one that goes its own way does
    sal = {"index": {"United States": 0, "A": 1, "B": 2, "C": 3, "D": 4}, "logw": np.array([8.0, 6.0, 7.0, 7.5, 6.5]),
           "med": np.zeros((5, 60)), "idx": {x: k for k, x in enumerate(("x35", "x34", "x3", "x1"))}}
    same = {"A": -0.5, "B": -0.2, "C": 0.1, "D": -0.4, "United States": 0.0}
    import unittest.mock as mock
    with mock.patch(__name__ + ".writer_levels" if __name__ != "__main__" else "__main__.writer_levels",
                    lambda d: {"one": dict(same), "two": {k: v + 0.3 for k, v in same.items()},
                               "three": {k: v - 0.1 for k, v in same.items()}}):
        assert not c_b6({"salary": sal})[0], "B6 must fail when every writer writes the same level per country"
    own = dict(same, A=0.4)
    with mock.patch(__name__ + ".writer_levels" if __name__ != "__main__" else "__main__.writer_levels",
                    lambda d: {"one": dict(same), "two": own, "three": dict(same)}):
        assert c_b6({"salary": sal})[0]
    gp = {"US": {"a": (10.0, "USD")}, "JP": {"a": (1000.0, "JPY")}}
    lv = writer_levels({"steam": toy("scalar"), "fx": {"main": {"USD": 1.0, "JPY": 100.0}}, "salary": sal,
                        "icloud": {"rows": []}, "gamepass": gp})
    assert abs(lv["game subscription"]["Japan"]) < 1e-12, "a price at the market rate is a level of zero"

    # B7: a one-writer table that is exactly country times tier, against a noisy store and a clean one
    tiers = np.array([0.99, 2.99, 9.99, 29.99, 59.99])
    ic = {"rows": [{"country": c, "currency": "USD" if k < 3 else f"C{k}", "tax_included": False,
                    "tax_may_be_added": False, "prices": list(tiers * (1 + k))}
                   for k, c in enumerate(["United States", "A", "B", "C", "D"])], "footnote_vintage": True}
    assert c_b7({"icloud": ic, "steam": toy("noise")})[0], "an exact one-writer table is tighter than a noisy store"
    rough = {"rows": [dict(r, prices=[p * (1 + 0.9 * ((k + j) % 2)) for j, p in enumerate(r["prices"])])
                      for k, r in enumerate(ic["rows"])], "footnote_vintage": True}
    assert not c_b7({"icloud": rough, "steam": toy("scalar")})[0], \
        "B7 must fail when the one-writer table is rougher than the store"
    merged = merge_zones([{"rep": "US", "members": ["US"], "currency": "USD"},
                          {"rep": "A", "members": ["A"], "currency": "USD"},
                          {"rep": "B", "members": ["B"], "currency": "USD"}],
                         np.column_stack([np.ones(60), np.full(60, 2.0), np.where(np.arange(60) < 5, np.nan, 2.0)]),
                         np.ones((60, 3)), least=50)
    assert [g["members"] for g in merged[0]] == [["US"], ["A", "B"]], "zones that differ only in what is sold merge"
    assert abs(two_way_sd(np.log(np.outer([1, 2, 3], [1, 5, 9.0])))) < 1e-12
    print("selftest ok: parsers, the grid test, the variance share and every flag on its planted input")


def main() -> int:
    data = load()
    res, objs = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    OUT.write_text(json.dumps(record_of(data, res, objs), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-B0"][0] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
