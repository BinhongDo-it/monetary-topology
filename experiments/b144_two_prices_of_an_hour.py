"""B144 arm D: one hour of work read from both sides, inside one country.

The customer's side is the set of price quotes the Office for National Statistics collects
for its consumer price indices: eight of its items are an hour of somebody's work, posted
by whoever sells it. The provider's side is the hourly pay, excluding overtime, of employees
in the occupation that does that hour, from the Annual Survey of Hours and Earnings (pay
period of April 2025). Both are official, both are in pounds, no exchange rate enters.

    wedge = what the customer pays for the hour / what an employee doing it is paid for it

Three numbers follow from a wedge and the published rates:
    wedge / ((1 + VAT) (1 + employer contribution))    what is left after everything statute
                                                       can put between pay and price
    wedge / kept                                       hours of the provider's own work that
                                                       buy one such hour, kept = 1 - basic
                                                       rate - employee contribution
    kept * kept / wedge                                of each pound a customer earns to pay
                                                       for the hour, what the worker takes home

  B144-D0  instrument    the files parse; each quote file holds the month asked for; the
                         glossary says what PRICE, VALIDITY and REGION are; every item and
                         every occupation carries the words expected of it; every rate used
                         is on its cached government page
  B144-D1  own_reading   an hour one customer buys alone is posted above the pay of the
                         occupation that does it
  B144-D2  own_reading   an hour several customers share is posted below that pay to each of
                         them, and the pay is covered within the number the rule allows
  B144-D3  own_reading   the wedge is not one number across occupations: the spread stays
                         above the largest spread of one-wedge worlds with any one
                         occupation left out
  B144-D4  own_reading   across regions the posted price follows the region's pay more
                         closely than the pay of the occupation does
  B144-D5  rival         one pay level per region: log pay(occupation, region) = a(occupation)
                         + m(region), so every occupation follows the region's pay alike.
                         Against it: the wage floor is one number written for the whole
                         country, and pay that sits near it cannot follow a region. Read
                         over every four-digit occupation the survey discloses by region:
                         the slope of an occupation's pay on the region's pay, against how
                         far its national pay stands above the floor

A state is read only where it is the same at every point of the knob grid (the month of the
quotes, median or mean on either side; for D4 also London in or out and the fewest quotes
a regional cell may hold; for D5 median or mean, London in or out, and how many regions an
occupation may be missing from). D5 is placed the way the first rival criterion of this
station is: outside the relabelling range at the reference point, and on the same side of
zero at every knob point; how many knob points clear their own relabelling range is printed
beside it. The mapping from states to verdicts is printed in the record.

Run from the repo root:
    python experiments/b144_two_prices_of_an_hour.py
    python experiments/b144_two_prices_of_an_hour.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144" / "uk"
RULES = ROOT / "data" / "raw" / "b144" / "uk_rules"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "results" / "b144_two_prices_of_an_hour.json"

MONTHS = {"2025-04": ("quotes_2025_04", 202504),      # the pay period of the earnings survey
          "2026-08": ("quotes_2026_08", 202608)}      # the latest month; pay has risen since the survey
PRICE_STAT = ("median", "mean")
PAY_STAT = ("median", "mean")
LONDON = ("with London", "without London")
MIN_CELL = (3, 5)                  # fewest valid quotes a regional cell may hold
MIN_QUOTES = 30                    # fewest valid quotes an item must have in a month to be read at all
MISSING = (3, 0)                   # regions an occupation's pay may be undisclosed in and still be read
N_PERM = 1000                      # relabellings per seed
N_BOOT = 1000
N_WORLDS = 200                     # one-wedge worlds per seed
SEEDS = (20261012, 20261013)

# what is sold, in the collector's words; the occupation that does it, code and the survey's words
ITEMS = {
    "plumber": ("PLUMBER-DAYTIME HOURLY RATE", "5315",
                "Plumbers & heating and ventilating installers and repairers", "hour, one customer"),
    "electrician": ("ELECTRICIAN-DAYTIME RATE/HOUR", "5241", "Electricians and electrical fitters",
                    "hour, one customer"),
    "carpenter": ("CARPENTER HOURLY RATE", "5316", "Carpenters and joiners", "hour, one customer"),
    "domestic cleaner": ("DOMESTIC CLEANER HOURLY RATE", "9223", "Cleaners and domestics", "hour, one customer"),
    "home care assistant": ("HOME CARE ASSISTANT HRLY RATE", "6135", "Care workers and home carers",
                            "hour, one customer"),
    "driving lesson": ("DRIVING LESSON 1 HOUR", "8215", "Driving instructors", "hour, one customer"),
    "solicitor": ("HOURLY RATE FOR SOLICITOR", "2412", "Solicitors and lawyers", "hour, one customer"),
    "childminder": ("CHILD MINDER - HOURLY RATE", "6114", "Childminders", "hour, shared"),
    "decorator": ("DECORATOR-DAILY RATE;SPEC HRS", "5323", "Painters and decorators", "job"),
    "man's haircut": ("MAN'S HAIRCUT", "6221", "Hairdressers and barbers", "job"),
}
ALONE = [k for k, v in ITEMS.items() if v[3] == "hour, one customer"]
SHARED = [k for k, v in ITEMS.items() if v[3] == "hour, shared"]

# the collector's region codes, as its glossary numbers them, against the survey's region names
REGIONS = {2: ("London", "London"), 3: ("SE", "South East"), 4: ("SW", "South West"), 5: ("East Anglia", "East"),
           6: ("East Midlands", "East Midlands"), 7: ("West Midlands", "West Midlands"),
           8: ("Yorks & Humber", "Yorkshire and The Humber"), 9: ("NW", "North West"), 10: ("North", "North East"),
           11: ("Wales", "Wales"), 12: ("Scotland", "Scotland"), 13: ("Northern Ireland", "Northern Ireland")}
GLOSSARY = ("Observed price on date of collection (in £GBP).",
            "TRUE = Quote included in the current months index.",
            "Approximation to Government Office Regions (GOR):")
PAY_TITLE = "Hourly pay - Excluding overtime (£) - For all employee jobs"

# every rate used: the cached page, the passage on it, the token in the passage, the value
RATES = {
    "vat": ("vat.html", "Standard rate 20%", "20%", 0.20),
    "employer": ("employers_2025_26.html", "A 15% 15% 15% 15%", "15%", 0.15),
    "employee": ("employers_2025_26.html", "A 0% 8% 2%", "8%", 0.08),
    "basic": ("income_tax.html", "Basic rate £12,571 to £50,270 20%", "20%", 0.20),
    "floor 2025-04": ("minimum_wage.html", "April 2025 to March 2026 £12.21", "£12.21", 12.21),
    "floor 2026-08": ("minimum_wage.html", "April 2026 £12.71", "£12.71", 12.71),
    "share cap": ("eyfs_childminders.pdf", "may care for a maximum of six children under the age of eight", "six", 6),
    "young cap": ("eyfs_childminders.pdf", "A maximum of three may be young children", "three", 3),
}
STATUTE = (1 + RATES["vat"][3]) * (1 + RATES["employer"][3])
KEPT = 1 - RATES["basic"][3] - RATES["employee"][3]
SHARE_CAP = RATES["share cap"][3]

STATES = {"above one": "above one at every knob point", "below one": "below one at every knob point",
          "unread": "the side changes somewhere on the knob grid, or a number is missing"}
STATES_SHARED = {"shared and covered": "each customer pays less than the pay at every knob point and the pay "
                                       "is covered within the number the rule allows",
                 "not shared": "each customer pays more than the pay at every knob point, or the pay cannot be "
                               "covered within the number the rule allows at any knob point",
                 "unread": "anything else"}
STATES_SPREAD = {"more than one wedge": "with any one occupation left out the spread is above the floor",
                 "one wedge": "the spread over all occupations is within the floor",
                 "unread": "above the floor only while one particular occupation is in"}
STATES_FLOOR = {"ours": "above the largest any relabelling returns at the reference point, and positive at "
                        "every knob point",
                "opposite": "below the smallest any relabelling returns at the reference point, and negative at "
                            "every knob point",
                "unread": "inside the relabelling range at the reference point, or the sign changes somewhere on "
                          "the knob grid, or too few occupations"}
MAPPING_FLOOR = {"ours": "B", "opposite": "both_unmet", "unread": "not placed"}
BANDS = ((0.10, "within 10% of the floor"), (0.50, "10% to 50% above"), (1.00, "50% to 100% above"),
         (math.inf, "more than double"))
STATES_GAP = {"price steeper": "the posted price follows the region's pay more than the occupation's pay does, "
                               "at every knob point",
              "pay steeper": "the occupation's pay follows the region's pay more, at every knob point",
              "unread": "the order changes somewhere on the knob grid, or a slope is undefined"}


# ----------------------------------------------------------------------------- reading the files
def one_file(folder: Path) -> Path:
    return sorted(p for p in folder.iterdir() if p.is_file() and ".partial" not in p.name
                  and not p.name.endswith(".writing"))[0]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def raw_records(src: Path):
    """(header, rows) of a quote file, whichever container it came in."""
    if src.suffix == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(src, read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        return [str(c) for c in next(it)], it
    f = open(src, encoding="utf-8-sig", errors="replace", newline="")
    it = csv.reader(f)
    return next(it), it


def quote_extract(month: str) -> dict:
    """The rows of the listed items in one month; cached, keyed on the source file's hash."""
    folder, _ = MONTHS[month]
    src = one_file(RAW / folder)
    key = {"source": src.name, "sha256": sha256(src), "items": sorted(v[0] for v in ITEMS.values())}
    cache = CACHE / f"b144_uk_quotes_{folder}.json"
    if cache.exists():
        j = json.loads(cache.read_text(encoding="utf-8"))
        if j.get("key") == key:
            return j
    header, rows = raw_records(src)
    col = {name: header.index(name) for name in ("QUOTE_DATE", "VALIDITY", "PRICE", "REGION", "SHOP_TYPE")}
    descs = [header.index(c) for c in ("ITEM_DESC", "CS_DESC") if c in header]
    words = set(key["items"])
    kept, dates, n = [], {}, 0
    for r in rows:
        n += 1
        d = str(r[col["QUOTE_DATE"]])
        dates[d] = dates.get(d, 0) + 1
        w = next((str(r[i]).strip() for i in descs if str(r[i]).strip() in words), None)
        if w is not None:
            kept.append([w, float(r[col["PRICE"]] or 0), str(r[col["VALIDITY"]]).strip().lower() == "true",
                         int(float(r[col["REGION"]] or 0)), int(float(r[col["SHOP_TYPE"]] or 0))])
    out = {"key": key, "rows_in_file": n, "quote_dates": dates, "rows": kept,
           "description_columns": [header[i] for i in descs]}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out


def sheet(zip_path: Path, marker: str, name: str = "All") -> list:
    import openpyxl
    z = zipfile.ZipFile(zip_path)
    member = sorted(n for n in z.namelist() if marker in n)[0]
    wb = openpyxl.load_workbook(io.BytesIO(z.read(member)), read_only=True, data_only=True)
    return [list(r) for r in wb[name].iter_rows(values_only=True)]


def num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def national(rows: list) -> dict:
    """code -> words, jobs, median, mean; the all-employees line under the key 'all'."""
    out = {}
    for r in rows[5:]:
        if r[0] is None:
            continue
        code = str(r[1] or "").strip()
        out[code or ("all" if str(r[0]).strip() == "All employees" else str(r[0]).strip())] = {
            "words": str(r[0]).strip(), "jobs": num(r[2]), "median": num(r[3]), "mean": num(r[5])}
    return out


def by_region(rows: list) -> dict:
    """(region, code) -> median, mean, from lines that read 'Region, Occupation'."""
    out = {}
    for r in rows[5:]:
        d, code = str(r[0] or "").strip(), str(r[1] or "").strip()
        if "," in d and code:
            out[(d.split(",", 1)[0].strip(), code)] = {"median": num(r[3]), "mean": num(r[5])}
    return out


def region_lines(rows: list) -> dict:
    """region -> median, mean, from the lines whose code is a geography code."""
    return {str(r[0]).strip(): {"median": num(r[3]), "mean": num(r[5])} for r in rows[5:]
            if r[0] is not None and re.fullmatch(r"[A-Z]\d{8}", str(r[1] or "").strip())}


def page_text(p: Path) -> str:
    if p.suffix == ".pdf":
        import pymupdf
        t = " ".join(pg.get_text() for pg in pymupdf.open(p))
    else:
        t = p.read_text(encoding="utf-8", errors="replace")
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def glossary() -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(one_file(RAW / "glossary"), read_only=True, data_only=True)
    cells = [str(c).strip() for r in wb.worksheets[0].iter_rows(values_only=True) for c in r if c is not None]
    regions = {}
    for c in cells:
        m = re.fullmatch(r"(\d+)\s*=\s*(.+?)\.", c)
        if m and int(m.group(1)) in REGIONS and m.group(2) in {v[0] for v in REGIONS.values()}:
            regions[int(m.group(1))] = m.group(2)
    return {"cells": cells, "regions": regions}


def valid(rows: list, words: str) -> list:
    """Quotes of one item that entered the month's index and carry a price."""
    return [r for r in rows if r[0] == words and r[2] and r[1] > 0]


def load() -> dict:
    quotes, files = {}, {}
    for month in MONTHS:
        ex = quote_extract(month)
        files[month] = {k: ex[k] for k in ("rows_in_file", "quote_dates", "description_columns")}
        files[month]["source"] = ex["key"]["source"]
        quotes[month] = {}
        for item, (words, *_rest) in ITEMS.items():
            rows = valid(ex["rows"], words)
            quotes[month][item] = {"price": np.array([r[1] for r in rows], float),
                                   "region": np.array([r[3] for r in rows], int),
                                   "listed": sum(r[0] == words for r in ex["rows"])}
    a14 = one_file(RAW / "ashe14")
    values, cvs = sheet(a14, "Table 14.6a"), sheet(a14, "Table 14.6b")
    pay = national(values)
    cv = {code: {"median": v["median"], "mean": v["mean"]} for code, v in national(cvs).items()}
    r15 = sheet(one_file(RAW / "ashe15"), "(4).6a")
    r3 = sheet(one_file(RAW / "ashe3"), "Table 3.6a")
    pages = {name: page_text(RULES / name) for name in sorted({v[0] for v in RATES.values()})}
    return {"quotes": quotes, "quote_files": files, "pay": pay, "cv": cv,
            "titles": {"national": str(values[0][0]), "cv": str(cvs[0][0]), "regional occupation": str(r15[0][0]),
                       "regional": str(r3[0][0])},
            "pay_region": region_lines(r3), "pay_region_occ": by_region(r15), "glossary": glossary(),
            "rates_found": {k: (v[1] in pages[v[0]]) for k, v in RATES.items()}}


# ----------------------------------------------------------------------------- estimators
def stat(values, how: str) -> float:
    if len(values) == 0:
        return math.nan
    return float(np.median(values)) if how == "median" else float(np.mean(values))


def wedge(data: dict, item: str, month: str, price_how: str, pay_how: str) -> float:
    p = data["quotes"][month][item]["price"]
    w = data["pay"].get(ITEMS[item][1], {}).get(pay_how)
    if len(p) < MIN_QUOTES or not w:
        return math.nan
    return stat(p, price_how) / w


KNOBS = [(m, ph, wh) for m in MONTHS for ph in PRICE_STAT for wh in PAY_STAT]
KNOBS_FLOOR = [(wh, lo, ms) for wh in PAY_STAT for lo in LONDON for ms in MISSING]
KNOBS_REGIONAL = [(m, ph, wh, lo, mc) for m in MONTHS for ph in PRICE_STAT for wh in PAY_STAT for lo in LONDON
                  for mc in MIN_CELL]


def grid(data: dict) -> list:
    return [{"month": m, "price": ph, "pay": wh,
             "wedge": {item: wedge(data, item, m, ph, wh) for item in ALONE + SHARED}} for m, ph, wh in KNOBS]


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
    """True when every state is the wanted one; False when none is and none is unread; None otherwise."""
    s = list(states)
    if s and all(x == want for x in s):
        return True
    if s and all(x != want and x != "unread" for x in s):
        return False
    return None


def draws(data: dict, item: str, knob, rng, n: int, scale: float = 1.0) -> np.ndarray:
    """Wedges of one item under resampled quotes and a pay drawn with the survey's own coefficient of variation."""
    m, ph, wh = knob
    p = data["quotes"][m][item]["price"]
    code = ITEMS[item][1]
    w = data["pay"][code][wh]
    cv = (data["cv"].get(code, {}).get(wh) or 0.0) / 100.0
    idx = rng.integers(0, len(p), size=(n, len(p)))
    top = np.median(p[idx], axis=1) if ph == "median" else np.mean(p[idx], axis=1)
    return scale * top / (w * np.exp(rng.normal(0.0, cv, size=n)))


def resamples(data: dict, items) -> dict:
    out = {}
    for item in items:
        if not math.isfinite(wedge(data, item, *KNOBS[0])):
            continue
        both = [draws(data, item, KNOBS[0], np.random.default_rng(s), N_BOOT) for s in SEEDS]
        out[item] = {"interval": [float(np.quantile(both[0], q)) for q in (0.025, 0.975)],
                     "second_seed": [float(np.quantile(both[1], q)) for q in (0.025, 0.975)]}
    return out


def spread(values) -> float:
    v = [math.log(x) for x in values]
    return max(v) - min(v)


def left_out(wedges: dict) -> float:
    """The smallest spread that remains when any one occupation is taken away."""
    names = list(wedges)
    return min(spread([wedges[k] for k in names if k != drop]) for drop in names)


def one_wedge_floor(data: dict, knob, items) -> float:
    """The largest spread reached by worlds in which every occupation stands at one multiple of its pay."""
    top = 0.0
    for s in SEEDS:
        rng = np.random.default_rng(s)
        cols = []
        for item in items:
            here = wedge(data, item, *knob)
            cols.append(np.log(draws(data, item, knob, rng, N_WORLDS, scale=1.0 / here)))
        m = np.vstack(cols)
        top = max(top, float((m.max(axis=0) - m.min(axis=0)).max()))
    return top


def cells(data: dict, knob) -> list:
    """(item, region, log price, log pay of the occupation or nan, log pay of the region) at one knob point."""
    m, ph, wh, london, min_cell = knob
    out = []
    for item, (_words, code, *_rest) in ITEMS.items():
        q = data["quotes"][m][item]
        for rc, (_theirs, name) in REGIONS.items():
            if name == "London" and london == "without London":
                continue
            sel = q["price"][q["region"] == rc]
            level = data["pay_region"].get(name, {}).get(wh)
            if len(sel) < min_cell or not level:
                continue
            occ = data["pay_region_occ"].get((name, code), {}).get(wh)
            out.append((item, name, math.log(stat(sel, ph)), math.log(occ) if occ else math.nan, math.log(level)))
    return out


def within(rows, ycol: int) -> float:
    """Slope of column ycol on the region's pay, items demeaned."""
    sxy = sxx = 0.0
    for item in sorted({r[0] for r in rows}):
        sub = [r for r in rows if r[0] == item]
        if len(sub) < 2:
            continue
        mx, my = np.mean([r[4] for r in sub]), np.mean([r[ycol] for r in sub])
        sxy += sum((r[4] - mx) * (r[ycol] - my) for r in sub)
        sxx += sum((r[4] - mx) ** 2 for r in sub)
    return sxy / sxx if sxx > 0 else math.nan


def matched(rows: list) -> list:
    """Cells of the items whose occupation pay is disclosed in more than half of their regions."""
    keep = []
    for item in sorted({r[0] for r in rows}):
        sub = [r for r in rows if r[0] == item]
        if sum(math.isfinite(r[3]) for r in sub) * 2 > len(sub):
            keep += [r for r in sub if math.isfinite(r[3])]
    return keep


def regional(data: dict, knob) -> dict:
    rows = matched(cells(data, knob))
    bp, bw = within(rows, 2), within(rows, 3)
    return {"month": knob[0], "price_stat": knob[1], "pay_stat": knob[2], "london": knob[3], "min_cell": knob[4],
            "price": bp, "pay": bw, "gap": bp - bw, "cells": len(rows), "items": sorted({r[0] for r in rows}),
            "regions": len({r[1] for r in rows})}


def regional_items(data: dict, knob) -> dict:
    rows = matched(cells(data, knob))
    out = {}
    for item in sorted({r[0] for r in rows}):
        sub = [r for r in rows if r[0] == item]
        out[item] = {"price": within(sub, 2), "pay": within(sub, 3), "regions": len(sub)}
    return out


def regional_resamples(data: dict, knob) -> dict:
    rows = matched(cells(data, knob))
    names = sorted({r[1] for r in rows})
    out = []
    for s in SEEDS:
        rng = np.random.default_rng(s)
        gaps = []
        for _ in range(N_BOOT):
            pick = rng.integers(0, len(names), size=len(names))
            again = [(r[0], f"{r[1]}#{j}", r[2], r[3], r[4]) for j, i in enumerate(pick) for r in rows
                     if r[1] == names[i]]
            gaps.append(within(again, 2) - within(again, 3))
        out.append([float(np.nanquantile(gaps, q)) for q in (0.025, 0.975)])
    return {"gap": out[0], "second_seed": out[1]}


def line(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx = x - x.mean()
    return float((dx * (y - y.mean())).sum() / (dx * dx).sum()) if (dx * dx).sum() > 0 else math.nan


def occupation_slopes(data: dict, knob) -> list:
    """(code, log of national pay over the floor, slope of its pay on the region's pay, regions) per occupation."""
    wh, london, missing = knob
    names = [name for _rc, (_t, name) in REGIONS.items() if data["pay_region"].get(name, {}).get(wh)
             and not (name == "London" and london == "without London")]
    by_code = {}
    for (region, code), v in data["pay_region_occ"].items():
        if len(code) == 4 and region in names and v.get(wh):
            by_code.setdefault(code, {})[region] = v[wh]
    floor = RATES["floor 2025-04"][3]
    present = max((len(v) for v in by_code.values()), default=0)     # the survey's regional table leaves one out
    out = []
    for code in sorted(by_code):
        national_pay = data["pay"].get(code, {}).get(wh)
        got = by_code[code]
        if not national_pay or len(got) < max(present - missing, 3):
            continue
        b = line([math.log(data["pay_region"][r][wh]) for r in sorted(got)], [math.log(got[r]) for r in sorted(got)])
        if math.isfinite(b):
            out.append((code, math.log(national_pay / floor), b, len(got)))
    return out


def floor_relation(data: dict, knob) -> dict:
    """How the regional slope of an occupation's pay moves with its distance from the floor, and relabellings."""
    rows = occupation_slopes(data, knob)
    x, b = np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
    if len(rows) < 10:
        return {"pay_stat": knob[0], "london": knob[1], "missing": knob[2], "occupations": len(rows),
                "relation": math.nan, "null_max": math.nan, "null_min": math.nan, "bands": []}
    c = line(x, b)
    null = []
    for s in SEEDS:
        rng = np.random.default_rng(s)
        for _ in range(N_PERM):
            null.append(line(rng.permutation(x), b))
    bands, lo = [], -math.inf
    for top, label in BANDS:
        sel = (np.exp(x) - 1 > lo) & (np.exp(x) - 1 <= top)
        bands.append({"band": label, "occupations": int(sel.sum()),
                      "mean_slope": float(b[sel].mean()) if sel.any() else math.nan,
                      "median_slope": float(np.median(b[sel])) if sel.any() else math.nan})
        lo = top
    return {"pay_stat": knob[0], "london": knob[1], "missing": knob[2], "occupations": len(rows), "relation": c,
            "null_max": float(max(null)), "null_min": float(min(null)), "mean_slope": float(b.mean()), "bands": bands}


def state_floor(fg: list) -> str:
    if not fg or any(not math.isfinite(g["relation"]) for g in fg):
        return "unread"
    ref = fg[0]
    if ref["relation"] > ref["null_max"] and all(g["relation"] > 0 for g in fg):
        return "ours"
    if ref["relation"] < ref["null_min"] and all(g["relation"] < 0 for g in fg):
        return "opposite"
    return "unread"


# ----------------------------------------------------------------------------- criteria
def c_d0(data: dict):
    problems = []
    for month, (_folder, stamp) in MONTHS.items():
        f = data["quote_files"][month]
        if set(f["quote_dates"]) != {str(stamp)}:
            problems.append(f"the {month} file holds quote dates {sorted(f['quote_dates'])}")
        for item, (words, *_rest) in ITEMS.items():
            if len(data["quotes"][month][item]["price"]) < MIN_QUOTES:
                problems.append(f"'{words}' has fewer than {MIN_QUOTES} valid quotes in {month}")
    cells_ = data["glossary"]["cells"]
    for sentence in GLOSSARY:
        if sentence not in cells_:
            problems.append(f"the glossary does not say '{sentence}'")
    for rc, (theirs, _ours) in REGIONS.items():
        if data["glossary"]["regions"].get(rc) != theirs:
            problems.append(f"the glossary does not number region {rc} as {theirs}")
    for key in ("national", "regional occupation", "regional"):
        if PAY_TITLE not in data["titles"][key] or "2025" not in data["titles"][key]:
            problems.append(f"the {key} pay table is titled '{data['titles'][key][:60]}'")
    if "Coefficients of variation" not in data["titles"]["cv"]:
        problems.append("the table read for coefficients of variation is not one")
    for item, (_words, code, occupation, _unit) in ITEMS.items():
        got = data["pay"].get(code, {})
        if got.get("words") != occupation:
            problems.append(f"occupation {code} is called '{got.get('words')}', not '{occupation}'")
        elif not got.get("median"):
            problems.append(f"occupation {code} has no median")
    if not data["pay"].get("all", {}).get("median"):
        problems.append("no line for all employees")
    for _rc, (_theirs, name) in REGIONS.items():
        if not data["pay_region"].get(name, {}).get("median"):
            problems.append(f"no pay line for the region {name}")
    for name, (page, passage, token, _value) in RATES.items():
        if token not in passage or not data["rates_found"].get(name):
            problems.append(f"the rate '{name}' is not on {page} as '{passage}'")
    counts = {m: {item: int(len(data["quotes"][m][item]["price"])) for item in ITEMS} for m in MONTHS}
    files = "; ".join(f"{m}: {data['quote_files'][m]['rows_in_file']:,} rows, item named in "
                      f"{'/'.join(data['quote_files'][m]['description_columns'])}" for m in MONTHS)
    detail = (f"{files}; {len(ITEMS)} items, valid quotes per item {min(min(c.values()) for c in counts.values())} "
              f"to {max(max(c.values()) for c in counts.values())}; {len(REGIONS)} region codes as the glossary "
              f"numbers them; {len(RATES)} rates on {len({v[0] for v in RATES.values()})} cached pages; "
              + ("; ".join(problems) if problems else "every item and occupation carries the words expected"))
    return not problems, detail, {"problems": problems, "valid_quotes": counts}


def c_d1(data: dict, g: list, boot: dict):
    states, parts, obj = {}, [], {}
    ref = g[0]["wedge"]
    for item in ALONE:
        vals = [pt["wedge"][item] for pt in g]
        states[item] = side(vals)
        code = ITEMS[item][1]
        p = stat(data["quotes"][KNOBS[0][0]][item]["price"], "median")
        w = data["pay"].get(code, {}).get("median") or math.nan
        lo, hi = boot.get(item, {}).get("interval", [math.nan, math.nan])
        obj[item] = {"posted": p, "paid": w, "wedge": ref[item], "over_statute": ref[item] / STATUTE,
                     "own_hours": ref[item] / KEPT, "taken_home_per_pound_earned": KEPT * KEPT / ref[item],
                     "pay_over_floor": w / RATES["floor 2025-04"][3]}
        parts.append(f"{item} posted {p:.2f} paid {w:.2f}, wedge {ref[item]:.2f} ({np.nanmin(vals):.2f} to "
                     f"{np.nanmax(vals):.2f} over {len(vals)} knob points; resamples {lo:.2f} to {hi:.2f}), "
                     f"{ref[item] / STATUTE:.2f} after statute, {ref[item] / KEPT:.1f} own hours, "
                     f"{100 * KEPT * KEPT / ref[item]:.0f}p taken home per pound earned")
    n = sum(s == "above one" for s in states.values())
    over = sum(all(pt["wedge"][item] > STATUTE for pt in g) for item in ALONE)
    detail = ("; ".join(parts) + f". Above one at every knob point: {n} of {len(states)}; above everything statute "
              f"can add ({STATUTE:.2f}) at every knob point: {over} of {len(states)}")
    return verdict(states.values(), "above one"), detail, {"states": states, "reference": obj}


def c_d2(data: dict, g: list, boot: dict):
    states, parts, obj = {}, [], {}
    for item in SHARED:
        vals = [pt["wedge"][item] for pt in g]
        s = side(vals)
        need = [1.0 / v if math.isfinite(v) and v > 0 else math.nan for v in vals]
        if s == "below one" and all(x <= SHARE_CAP for x in need):
            states[item] = "shared and covered"
        elif s == "above one" or (s == "below one" and all(x > SHARE_CAP for x in need)):
            states[item] = "not shared"
        else:
            states[item] = "unread"
        code = ITEMS[item][1]
        p = stat(data["quotes"][KNOBS[0][0]][item]["price"], "median")
        w = data["pay"].get(code, {}).get("median") or math.nan
        lo, hi = boot.get(item, {}).get("interval", [math.nan, math.nan])
        obj[item] = {"posted_per_customer": p, "paid": w, "wedge": vals[0], "customers_to_cover_the_pay": need[0]}
        parts.append(f"{item} posted {p:.2f} to each customer, paid {w:.2f}, wedge {vals[0]:.2f} "
                     f"({np.nanmin(vals):.2f} to {np.nanmax(vals):.2f} over {len(vals)} knob points; resamples "
                     f"{lo:.2f} to {hi:.2f}); {need[0]:.1f} customers cover the pay ({np.nanmin(need):.1f} to "
                     f"{np.nanmax(need):.1f}), the rule allows {SHARE_CAP}, of whom {RATES['young cap'][3]} young")
    detail = "; ".join(parts) + f" -> {', '.join(states.values())}"
    return verdict(states.values(), "shared and covered"), detail, {"states": states, "reference": obj}


def c_d3(data: dict, g: list):
    states, floors, rows = [], [], []
    for knob, pt in zip(KNOBS, g):
        w = {item: pt["wedge"][item] for item in ALONE}
        if any(not math.isfinite(x) for x in w.values()):
            states.append("unread")
            floors.append(math.nan)
            rows.append({"spread": math.nan, "left_out": math.nan, "floor": math.nan})
            continue
        floor = one_wedge_floor(data, knob, ALONE)
        full, loo = spread(w.values()), left_out(w)
        states.append("more than one wedge" if loo > floor else ("one wedge" if full <= floor else "unread"))
        floors.append(floor)
        rows.append({"spread": full, "left_out": loo, "floor": floor,
                     "largest": max(w, key=w.get), "smallest": min(w, key=w.get)})
    r0 = rows[0]
    order = sorted(ALONE, key=lambda k: g[0]["wedge"][k])
    detail = ("wedges in order: " + ", ".join(f"{k} {g[0]['wedge'][k]:.2f}" for k in order)
              + f". Largest over smallest {math.exp(r0['spread']):.1f} times (log {r0['spread']:.3f}); with any one "
              f"occupation left out at least {math.exp(r0['left_out']):.1f} times (log {r0['left_out']:.3f}); the "
              f"largest spread of {N_WORLDS * len(SEEDS)} one-wedge worlds, log {r0['floor']:.3f}. Over "
              f"{len(rows)} knob points the left-out spread is {np.nanmin([r['left_out'] for r in rows]):.3f} to "
              f"{np.nanmax([r['left_out'] for r in rows]):.3f} against floors up to {np.nanmax(floors):.3f}; "
              f"more than one wedge at {sum(s == 'more than one wedge' for s in states)} of {len(states)}")
    return verdict(states, "more than one wedge"), detail, {"states": states, "knob_points": rows}


def c_d4(data: dict, rg: list, boot: dict, per_item: dict):
    gaps = [pt["gap"] for pt in rg]
    if any(not math.isfinite(x) for x in gaps):
        state = "unread"
    elif all(x > 0 for x in gaps):
        state = "price steeper"
    elif all(x < 0 for x in gaps):
        state = "pay steeper"
    else:
        state = "unread"
    r0 = rg[0]
    out = [pt for pt in rg if pt["london"] == "without London"]
    floor = RATES["floor 2025-04"][3]
    items = "; ".join(f"{k} price {v['price']:+.2f} pay {v['pay']:+.2f} (pay over the floor "
                      f"{(data['pay'][ITEMS[k][1]]['median'] or math.nan) / floor:.2f})" for k, v in per_item.items())
    detail = (f"{r0['cells']} cells, {len(r0['items'])} items in {r0['regions']} regions: the posted price against "
              f"the region's pay {r0['price']:+.3f}, the occupation's pay against it {r0['pay']:+.3f}, gap "
              f"{r0['gap']:+.3f} ({min(gaps):+.3f} to {max(gaps):+.3f} over {len(gaps)} knob points; region "
              f"resamples {boot['gap'][0]:+.3f} to {boot['gap'][1]:+.3f}). Without London: price "
              f"{min(p['price'] for p in out):+.3f} to {max(p['price'] for p in out):+.3f}, pay "
              f"{min(p['pay'] for p in out):+.3f} to {max(p['pay'] for p in out):+.3f}. By item: {items} -> {state}")
    return verdict([state], "price steeper"), detail, {"state": state}


def c_d5(fg: list):
    state = state_floor(fg)
    cell = MAPPING_FLOOR[state]
    passed = None if cell == "not placed" else True
    g0 = fg[0]
    bands = "; ".join(f"{b['band']} {b['mean_slope']:+.2f} ({b['occupations']} occupations)" for b in g0["bands"])
    rel = [g["relation"] for g in fg]
    detail = (f"{g0['occupations']} occupations: the slope of an occupation's pay on the region's pay rises by "
              f"{g0['relation']:+.3f} per log point of its national pay over the floor; relabelled occupations "
              f"return {g0['null_min']:+.3f} to {g0['null_max']:+.3f} in {N_PERM * len(SEEDS)} relabellings; over "
              f"{len(fg)} knob points the relation is {np.nanmin(rel):+.3f} to {np.nanmax(rel):+.3f} against a "
              f"largest relabelled {np.nanmax([g['null_max'] for g in fg]):+.3f}; above its own largest "
              f"relabelling at {sum(g['relation'] > g['null_max'] for g in fg)} of {len(fg)} knob points"
              + "".join(f" (inside it at {g['pay_stat']}, {g['london']}, {g['missing']} regions missing: "
                        f"{g['relation']:+.3f} against {g['null_max']:+.3f})" for g in fg
                        if math.isfinite(g["relation"]) and not g["relation"] > g["null_max"])
              + f". Mean slope by distance from the floor: {bands} -> {state}")
    return passed, detail, {"grid": "unread" if cell == "not placed" else cell, "state": state}


RIVALS = {
    "B144-D5": {"rival_shape": "point prediction",
                "rival_premise": "A region has one pay level: the pay of an occupation in a region is the "
                                 "occupation's own level times the region's, log w(occupation, region) = "
                                 "a(occupation) + m(region).",
                "rival_entailment": "Then every occupation's pay follows the region's level by the same amount, "
                                    "and the slope of an occupation's pay on the region's pay is unrelated to how "
                                    "far its national pay stands above the wage floor: what a relabelling of "
                                    "occupations gives."},
}
KINDS = {"B144-D0": "instrument", "B144-D1": "own_reading", "B144-D2": "own_reading", "B144-D3": "own_reading",
         "B144-D4": "own_reading", "B144-D5": "rival"}
STATEMENTS = {
    "B144-D0": "The quote files, the pay tables, the glossary and the government pages say what the reading "
               "takes them to say.",
    "B144-D1": "An hour that one customer buys alone is posted above the hourly pay of the occupation that "
               "does it.",
    "B144-D2": "An hour that several customers share is posted to each below that pay, and the pay is covered "
               "within the number the rule allows.",
    "B144-D3": "The wedge between the posted hour and the paid hour is not one number across occupations.",
    "B144-D4": "Across regions the posted price follows the region's pay more closely than the pay of the "
               "occupation does.",
    "B144-D5": "Pay follows the region's pay the less, the nearer the occupation's national pay sits to the "
               "wage floor written for the whole country. Passing means the rival is wrong here (`11e`).",
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
    g = grid(data)
    boot = resamples(data, ALONE + SHARED)
    rg = [regional(data, k) for k in KNOBS_REGIONAL]
    rboot = regional_resamples(data, KNOBS_REGIONAL[0])
    per_item = regional_items(data, KNOBS_REGIONAL[0])
    fg = [floor_relation(data, k) for k in KNOBS_FLOOR]
    res = {"B144-D0": c_d0(data), "B144-D1": c_d1(data, g, boot), "B144-D2": c_d2(data, g, boot),
           "B144-D3": c_d3(data, g), "B144-D4": c_d4(data, rg, rboot, per_item), "B144-D5": c_d5(fg)}
    return res, {"knob_grid": g, "resamples": boot, "regional_grid": rg, "regional_resamples": rboot,
                 "regional_by_item": per_item, "floor_grid": fg,
                 "occupations_at_the_reference": [[c, x, b, n] for c, x, b, n in
                                                  occupation_slopes(data, KNOBS_FLOOR[0])]}


def record_of(data: dict, res: dict, objs: dict) -> dict:
    region_pay = {name: data["pay_region"].get(name) for _rc, (_t, name) in REGIONS.items()}
    occ_pay = {item: {name: (data["pay_region_occ"].get((name, ITEMS[item][1])) or {}).get("median")
                      for _rc, (_t, name) in REGIONS.items()} for item in ITEMS}
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d,
                      **({**RIVALS[n], "grid": o["grid"]} if n in RIVALS else {})}
                     for n, (p, d, o) in res.items()],
        "mapping": {"states": STATES, "states_of_the_shared_hour": STATES_SHARED,
                    "states_of_the_floor": STATES_FLOOR, "floor_states_to_cells": MAPPING_FLOOR,
                    "states_of_the_spread": STATES_SPREAD, "states_of_the_gap": STATES_GAP,
                    "verdict": "true when every state is the stated one, false when none is and none is unread, "
                               "null otherwise"},
        "objects": {**r4(objs), "states": {n: r4(o) for n, (_, _, o) in res.items()},
                    "pay": r4({item: data["pay"].get(ITEMS[item][1]) for item in ITEMS}),
                    "pay_all_employees": r4(data["pay"].get("all")),
                    "coefficient_of_variation_percent": r4({item: data["cv"].get(ITEMS[item][1]) for item in ITEMS}),
                    "region_pay": r4(region_pay), "occupation_pay_by_region_median": r4(occ_pay),
                    "statute": round(STATUTE, 4), "kept": round(KEPT, 4)},
        "config": {"raw": "data/raw/b144/uk", "rule_pages": "data/raw/b144/uk_rules",
                   "fetched_by": "experiments/b144_fetch.py --only uk",
                   "quote_files": {m: data["quote_files"][m]["source"] for m in MONTHS},
                   "items": {k: {"sold_as": v[0], "occupation": v[1], "occupation_words": v[2], "unit": v[3]}
                             for k, v in ITEMS.items()},
                   "regions": {str(k): {"collector": v[0], "survey": v[1]} for k, v in REGIONS.items()},
                   "rates": {k: {"page": v[0], "passage": v[1], "value": v[3]} for k, v in RATES.items()},
                   "knobs": {"month": list(MONTHS), "price": list(PRICE_STAT), "pay": list(PAY_STAT),
                             "london": list(LONDON), "min_cell": list(MIN_CELL), "missing_regions": list(MISSING)},
                   "relabellings_per_seed": N_PERM,
                   "min_quotes": MIN_QUOTES, "n_boot": N_BOOT, "worlds_per_seed": N_WORLDS, "seeds": list(SEEDS)},
    }


# ----------------------------------------------------------------------------- selftest
def toy(wedges=None, bp=1.2, bw=0.4, noise=0.05, seed=1, per_region=14, rise=0.6, rise_mean=None) -> dict:
    """A country whose posted hours stand at planted multiples of pay and follow regions by planted slopes.

    wedges, bp and bw may be dicts by month, so that a reading can be made to change across the knob grid.
    """
    rng = np.random.default_rng(seed)
    base = {"plumber": 3.0, "electrician": 2.2, "carpenter": 1.6, "domestic cleaner": 1.4,
            "home care assistant": 2.3, "driving lesson": 2.0, "solicitor": 9.0, "childminder": 0.45,
            "decorator": 9.0, "man's haircut": 1.5}
    level = {name: 17.0 * math.exp(0.3 if name == "London" else 0.02 * ((rc % 5) - 2))
             for rc, (_t, name) in REGIONS.items()}

    def at(x, month, item=None):
        if isinstance(x, dict) and month in x:
            x = x[month]
        if isinstance(x, dict):
            return x.get(item, base[item]) if item else x
        return x

    quotes, pay, cv, occ = {m: {} for m in MONTHS}, {}, {}, {}
    for k, (item, (words, code, occupation, _unit)) in enumerate(ITEMS.items()):
        w = 12.0 + 1.5 * k
        pay[code] = {"words": occupation, "jobs": 50.0, "median": w, "mean": w}
        cv[code] = {"median": 1.0 if noise else 0.0, "mean": 1.0 if noise else 0.0}
        for name, lv in level.items():
            if name != "Northern Ireland":
                v = w * (lv / 17.0) ** at(bw, "2025-04") * math.exp(rng.normal(0, 0.01 if noise else 0.0))
                occ[(name, code)] = {"median": v, "mean": v}
        for m in MONTHS:
            mult = at(wedges if wedges is not None else base, m, item)
            mult = base[item] if mult is None else mult
            prices, regs = [], []
            for rc, (_t, name) in REGIONS.items():
                for _ in range(per_region):
                    prices.append(mult * w * (level[name] / 17.0) ** at(bp, m) * math.exp(rng.normal(0, noise)))
                    regs.append(rc)
            quotes[m][item] = {"price": np.array(prices), "region": np.array(regs), "listed": len(prices)}
    floor = RATES["floor 2025-04"][3]
    for k in range(60):                      # occupations beside the listed ones: slope 0.1 + rise * distance
        code, w = f"7{k:03d}", floor * math.exp(0.02 + 0.02 * k)
        pay[code] = {"words": f"occupation {k}", "jobs": 20.0, "median": w, "mean": w}
        for name, lv in level.items():
            if name != "Northern Ireland":
                v = w * (lv / 17.0) ** (0.1 + rise * math.log(w / floor)) * math.exp(
                    rng.normal(0, 0.01 if noise else 0.0))
                u = v if rise_mean is None else w * (lv / 17.0) ** (0.1 + rise_mean * math.log(w / floor))
                occ[(name, code)] = {"median": v, "mean": u}
    pay["all"] = {"words": "All employees", "jobs": 28000.0, "median": 17.0, "mean": 22.0}
    return {"quotes": quotes,
            "quote_files": {m: {"rows_in_file": 90000, "quote_dates": {str(MONTHS[m][1]): 90000},
                                "description_columns": ["CS_DESC"], "source": "toy"} for m in MONTHS},
            "pay": pay, "cv": cv,
            "titles": {"national": f"Table 14.6a   {PAY_TITLE}a: United Kingdom, 2025",
                       "cv": "Table 14.6b   Coefficients of variation for Hourly pay",
                       "regional occupation": f"Table 15 (4).6a   {PAY_TITLE}a: United Kingdom, 2025",
                       "regional": f"Table 3.6a   {PAY_TITLE}a: United Kingdom, 2025"},
            "pay_region": {name: {"median": lv, "mean": lv} for name, lv in level.items()},
            "pay_region_occ": occ,
            "glossary": {"cells": list(GLOSSARY), "regions": {rc: t for rc, (t, _n) in REGIONS.items()}},
            "rates_found": {k: True for k in RATES}}


def selftest() -> None:
    assert side([1.2, 1.1]) == "above one" and side([0.8, 0.9]) == "below one"
    assert side([1.2, 0.9]) == "unread" and side([math.nan]) == "unread" and side([]) == "unread"
    assert verdict(["a", "a"], "a") is True and verdict(["b", "b"], "a") is False
    assert verdict(["a", "unread"], "a") is None and verdict(["a", "b"], "a") is None and verdict([], "a") is None
    assert abs(spread([1.0, math.e]) - 1.0) < 1e-12
    assert abs(left_out({"a": 1.0, "b": 1.0, "c": math.e}) - 0.0) < 1e-12, "a spread that hangs on one name is zero"
    assert abs(STATUTE - 1.38) < 1e-9 and abs(KEPT - 0.72) < 1e-9 and SHARE_CAP == 6

    # the estimators return what was planted when nothing is noisy
    exact = toy(bp=0.0, bw=0.0, noise=0.0)
    for item, want in (("plumber", 3.0), ("domestic cleaner", 1.4), ("childminder", 0.45)):
        for knob in KNOBS:
            assert abs(wedge(exact, item, *knob) - want) < 1e-9, (item, knob)
    sloped = toy(bp=1.2, bw=0.4, noise=0.0)
    for knob in KNOBS_REGIONAL:
        r = regional(sloped, knob)
        assert abs(r["price"] - 1.2) < 1e-9 and abs(r["pay"] - 0.4) < 1e-9, (knob, r)
    assert "driving lesson" in regional(sloped, KNOBS_REGIONAL[0])["items"]
    thin = toy(bp=1.2, bw=0.4, noise=0.0)
    thin["pay_region_occ"] = {k: v for k, v in thin["pay_region_occ"].items()
                              if not (k[1] == "8215" and k[0] not in ("London", "Wales", "Scotland"))}
    assert "driving lesson" not in regional(thin, KNOBS_REGIONAL[0])["items"], \
        "an occupation disclosed in a minority of regions stays out of the regional reading"

    # the readers of rows: validity, the national table, the regional tables
    q = [["A", 10.0, True, 2, 1], ["A", 0.0, True, 2, 1], ["A", 12.0, False, 3, 1], ["B", 9.0, True, 2, 1]]
    assert valid(q, "A") == [q[0]], "a quote outside the index, or without a price, is not read"
    head = [[None] * 6] * 5
    nat = national(head + [["All employees", "", 100, 17.9, 5, 23.1], ["   Plumbers", "5315", 62, 18.0, 2.2, 18.3],
                           ["   Thin", "9999", "x", "x", None, 14.0]])
    assert nat["all"]["median"] == 17.9 and nat["5315"] == {"words": "Plumbers", "jobs": 62.0, "median": 18.0,
                                                            "mean": 18.3}
    assert nat["9999"]["median"] is None and nat["9999"]["mean"] == 14.0, "a suppressed cell is not a number"
    reg = by_region(head + [["    North East, Plumbers, fitters", "5315", 3, 17.0, 1, 17.5]])
    assert reg == {("North East", "5315"): {"median": 17.0, "mean": 17.5}}
    lines = region_lines(head + [["Wales", "W92000004", 1288, 16.58, 4.9, 20.25], ["Managers", "1", 3, 27.4, 6, 35.5],
                                 ["West Midlands", "E12000005 ", 2348, 16.96, 6.7, 21.27]])
    assert set(lines) == {"Wales", "West Midlands"} and lines["Wales"]["mean"] == 20.25
    assert stat([1.0, 1.0, 10.0], "median") == 1.0 and stat([1.0, 1.0, 10.0], "mean") == 4.0
    assert math.isnan(stat([], "median"))

    # the knobs of the regional reading do what they say
    k_with, k_out = KNOBS_REGIONAL[0], next(k for k in KNOBS_REGIONAL if k[3] == "without London" and k[4] == 3)
    assert regional(sloped, k_with)["regions"] - regional(sloped, k_out)["regions"] == 1
    sparse = toy(bp=1.2, bw=0.4, noise=0.0)
    for m in MONTHS:                         # one cell of four quotes: in at three, out at five
        qq = sparse["quotes"][m]["plumber"]
        keep = np.ones(len(qq["price"]), bool)
        keep[np.where(qq["region"] == 11)[0][4:]] = False
        qq["price"], qq["region"] = qq["price"][keep], qq["region"][keep]
    k5 = next(k for k in KNOBS_REGIONAL if k[3] == "with London" and k[4] == 5)
    assert regional(sparse, k_with)["cells"] - regional(sparse, k5)["cells"] == 1
    lopsided = toy(bp=1.2, bw=0.4, noise=0.0)
    for m in MONTHS:                         # the dearest item loses its low-pay regions
        qq = lopsided["quotes"][m]["solicitor"]
        keep = np.isin(qq["region"], (2, 3, 12))
        qq["price"], qq["region"] = qq["price"][keep], qq["region"][keep]
    r = regional(lopsided, k_with)
    assert abs(r["price"] - 1.2) < 1e-9 and abs(r["pay"] - 0.4) < 1e-9, "items are demeaned before the slope"
    loud = toy()
    quiet_floor = one_wedge_floor(loud, KNOBS[0], ALONE)
    loud["cv"]["5315"] = {"median": 60.0, "mean": 60.0}
    assert one_wedge_floor(loud, KNOBS[0], ALONE) > 2 * quiet_floor, "the survey's own uncertainty enters the floor"
    gap = toy(noise=0.0)
    for name in ("Wales", "Scotland"):
        del gap["pay_region_occ"][(name, "7005")]
    loose, tight = (next(k for k in KNOBS_FLOOR if k[1] == "with London" and k[2] == ms) for ms in (3, 0))
    assert "7005" in {r[0] for r in occupation_slopes(gap, loose)}
    assert "7005" not in {r[0] for r in occupation_slopes(gap, tight)}

    # the world as it is expected to be read
    res, _ = run(toy())
    assert res["B144-D0"][0], res["B144-D0"][1]
    assert res["B144-D1"][0] is True and res["B144-D2"][0] is True
    assert res["B144-D3"][0] is True and res["B144-D4"][0] is True
    assert res["B144-D5"][0] is True and res["B144-D5"][2]["grid"] == "B", res["B144-D5"][1]

    # D5: slopes of the planted block come back; no relation is not placed; the opposite relation is not ours
    assert abs(line([0, 1, 2, 3], [1, 3, 5, 7]) - 2.0) < 1e-12 and math.isnan(line([1, 1], [0, 1]))
    planted = {r[0]: r for r in occupation_slopes(toy(noise=0.0, rise=0.6), KNOBS_FLOOR[0])}
    for k in (0, 30, 59):
        code, x = f"7{k:03d}", 0.02 + 0.02 * k
        assert abs(planted[code][1] - x) < 1e-9 and abs(planted[code][2] - (0.1 + 0.6 * x)) < 1e-9, planted[code]
    flat = run(toy(rise=0.0))[0]["B144-D5"]
    assert flat[0] is None and flat[2]["grid"] == "unread", "a slope unrelated to the floor is not placed"
    back = run(toy(rise=-0.6))[0]["B144-D5"]
    assert back[2]["state"] == "opposite" and back[2]["grid"] == "both_unmet", back[1]
    turn = run(toy(rise=0.6, rise_mean=-0.6))[0]["B144-D5"]
    assert turn[0] is None and turn[2]["grid"] == "unread", "a sign that changes with the pay statistic is unread"
    few = toy()
    few["pay_region_occ"] = {k: v for k, v in few["pay_region_occ"].items() if not k[1].startswith("7")}
    assert c_d5([floor_relation(few, k) for k in KNOBS_FLOOR])[0] is None, "ten occupations are not a reading"
    assert set(MAPPING_FLOOR) == set(STATES_FLOOR) and MAPPING_FLOOR["unread"] == "not placed"

    # D1: posted below pay; and a side that changes with the month
    low = run(toy(wedges={k: 0.8 for k in ALONE}))[0]
    assert low["B144-D1"][0] is False, "D1 must fail where the hour is posted below the pay"
    mixed = run(toy(wedges={"2026-08": {"carpenter": 0.8}}))[0]
    assert mixed["B144-D1"][0] is None, "a side that changes with the month is unread"

    # D2: a shared hour posted above the pay; a pay that the allowed number cannot cover
    assert run(toy(wedges={"childminder": 1.3}))[0]["B144-D2"][0] is False
    assert run(toy(wedges={"childminder": 0.1}))[0]["B144-D2"][0] is False, "ten customers are more than the rule allows"
    assert run(toy(wedges={"2026-08": {"childminder": 1.3}}))[0]["B144-D2"][0] is None

    # D3: one wedge everywhere; a spread that hangs on one occupation
    same = run(toy(wedges={k: 2.0 for k in ALONE}))[0]
    assert same["B144-D3"][0] is False, "D3 must fail where every occupation stands at one multiple of its pay"
    hang = run(toy(wedges={**{k: 2.0 for k in ALONE}, "solicitor": 9.0}))[0]
    assert hang["B144-D3"][0] is None, "a spread that one occupation carries is unread"

    # D4: pay follows the region more than the posted price does; an order that changes with the month
    assert run(toy(bp=0.3, bw=0.9))[0]["B144-D4"][0] is False
    assert run(toy(bp={"2025-04": 1.2, "2026-08": 0.1}, bw=0.5))[0]["B144-D4"][0] is None

    # D0: each thing it reads, broken once
    def broken(change):
        d = toy()
        if change == "month":
            d["quote_files"]["2025-04"]["quote_dates"] = {"202503": 90000}
        elif change == "item":
            d["quotes"]["2026-08"]["plumber"]["price"] = d["quotes"]["2026-08"]["plumber"]["price"][:5]
        elif change == "glossary":
            d["glossary"]["cells"] = d["glossary"]["cells"][1:]
        elif change == "region":
            d["glossary"]["regions"][5] = "Wales"
        elif change == "title":
            d["titles"]["national"] = "Table 14.5a   Hourly pay - Gross"
        elif change == "cv":
            d["titles"]["cv"] = d["titles"]["national"]
        elif change == "occupation":
            d["pay"]["5315"]["words"] = "Plasterers"
        elif change == "region pay":
            del d["pay_region"]["Wales"]
        elif change == "rate":
            d["rates_found"]["employer"] = False
        return d
    for change in ("month", "item", "glossary", "region", "title", "cv", "occupation", "region pay", "rate"):
        assert not c_d0(broken(change))[0], f"D0 must fail on {change}"
    print("selftest ok: planted wedges and slopes come back, every flag fails on its planted input, and a "
          "reading that changes across the knob grid is unread")


def main() -> int:
    data = load()
    res, objs = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    OUT.write_text(json.dumps(record_of(data, res, objs), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-D0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
