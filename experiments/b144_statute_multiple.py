"""B144 arm E: what statute alone puts between two people who buy an hour from each other.

Two people on the same pay each hire the other for an hour through the books. The buyer pays
out of pay that has been taxed at the margin; the seller's hour is invoiced with value added
tax on top of a labour cost that carries the employer's contributions. With nothing but statute
between them, each works

    multiple = (1 + VAT) / (1 - marginal tax wedge)

hours for the other's one. The marginal tax wedge is the OECD's: income tax plus both sides'
social contributions on one more unit of labour cost, single person without children, at 67,
100 and 167 percent of the average wage. The VAT rate is the standard rate of the OECD's table,
whose last year is 2023; later years hold that rate. The United States has no row in that table
and is read with no tax on the invoice.

Beside the table, provisions that sovereigns have written for services bought by households:
credits to the buyer, an exemption below an amount, reduced rates allowed, separate classes of
provider. Each row rests on verbatim passages found on its cached page.

  B144-E0  instrument    the two OECD files say what the reading takes them to say, and the
                         United Kingdom's row at two thirds of the average wage returns the
                         multiple arm D computed from the government's own rate pages
  B144-E1  own_reading   the multiple differs between sovereigns by more than it moves with
                         the level of pay inside one
  B144-E2  bookkeeping   every passage is on its cached page and every page carries a row
  B144-E3  own_reading   every credit read lowers the multiple of the sovereign that wrote it

Run from the repo root:
    python experiments/b144_statute_multiple.py
    python experiments/b144_statute_multiple.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from b144_class_lines import page_text, squeeze
from b144_two_prices_of_an_hour import KEPT, STATUTE

ROOT = Path(__file__).resolve().parents[1]
OECD = ROOT / "data" / "raw" / "b144" / "oecd"
LAW = ROOT / "data" / "raw" / "b144" / "law_labour"
OUT = ROOT / "results" / "b144_statute_multiple.json"

LEVELS = ("AW100", "AW67", "AW167")        # the first is the reference
YEARS = ("2023", "2024", "2025")           # the first is the year the VAT table ends in
HOUSEHOLD = "S_C0"
MEASURE, UNIT = "MR_TW_PE", "PT_COS_LB"
MEASURE_WORDS = "Marginal tax wedge of the principal earner"
ALIASES = {"Czech Republic": "Czechia"}
NO_VAT = ("USA",)
NAMED = ("USA", "GBR", "JPN", "KOR", "DEU", "FRA", "SWE", "BEL")
ROW_KINDS = ("credit to the buyer", "exemption below an amount", "reduced rate allowed",
             "a separate class of provider")
LEVELS_OF_SOURCE = ("official text", "official description")

ROWS = [
    {"id": "DE-1", "where": "Germany", "code": "DEU", "page": "de_estg_35a.html", "level": "official text",
     "what": "Income Tax Act section 35a: household services and tradesmen's work in the taxpayer's household",
     "kind": "credit to the buyer", "cut": 0.20,
     "words": ["um 20 Prozent, höchstens 4 000 Euro, der Aufwendungen des Steuerpflichtigen",
               "um 20 Prozent der Aufwendungen des Steuerpflichtigen, höchstens jedoch um 1 200 Euro"]},
    {"id": "FR-1", "where": "France", "code": "FRA", "page": "fr_f12.html", "level": "official description",
     "what": "tax credit for employing someone at home", "kind": "credit to the buyer", "cut": 0.50,
     "words": ["s'élève à 50 % des dépenses supportées dans l'année"]},
    {"id": "SE-1", "where": "Sweden", "code": "SWE", "page": "se_inkomstskattelag.html", "level": "official text",
     "what": "Income Tax Act chapter 67 section 19: reduction for household work", "kind": "credit to the buyer",
     "cut": 0.50,
     "words": ["50 procent av underlaget enligt 18 § första stycket 2 till den del det avser sådant "
               "hushållsarbete som anges i 13 § och 30 procent av underlaget till den del det avser annat "
               "hushållsarbete",
               "Den sammanlagda skattereduktionen får uppgå till högst 75 000 kronor för ett beskattningsår"]},
    {"id": "UK-1", "where": "United Kingdom", "code": "GBR", "page": "uk_tax_free_childcare.html",
     "level": "official description", "what": "Tax-Free Childcare, for childcare only",
     "kind": "credit to the buyer", "cut": 0.20,
     "words": ["For every £8 you pay into the account, the government will top it up by £2"]},
    {"id": "US-1", "where": "United States", "code": "USA", "page": "us_tc756.html",
     "level": "official description", "what": "employment taxes for household employees",
     "kind": "exemption below an amount",
     "words": ["If you pay cash wages of $3,000 or more for 2026 (this threshold can change from year to year) "
               "to any one household employee, you generally must withhold 6.2% for Social Security tax"]},
    {"id": "EU-1", "where": "European Union", "page": "eu_vat_annex3.html", "level": "official text",
     "what": "VAT Directive 2006/112/EC, Annex III: supplies to which reduced rates may be applied",
     "kind": "reduced rate allowed",
     "words": ["window-cleaning and cleaning in private households",
               "domestic care services such as home help and care of young, elderly, sick or disabled",
               "hairdressing"]},
    {"id": "SG-1", "where": "Singapore", "page": "sg_fdw_levy.html", "level": "official description",
     "what": "monthly levy on a foreign domestic worker", "kind": "a separate class of provider",
     "words": ["Normal (1 st helper) $300 $9.87", "Concessionary $60 $1.98",
               "The concessionary rate applies to families with a young child, elderly member or person with "
               "disability"]},
    {"id": "HK-1", "where": "Hong Kong", "page": "hk_smw.html", "level": "official description",
     "what": "statutory minimum wage, an hourly floor", "kind": "a separate class of provider",
     "floor_per_hour": 43.1,
     "words": ["The SMW rate is raised to $43.1 per hour with effect from 1 May 2026"]},
    {"id": "HK-2", "where": "Hong Kong", "page": "hk_smw_guideline.pdf", "level": "official description",
     "what": "whom the hourly floor does not cover: live-in domestic workers",
     "kind": "a separate class of provider",
     "words": ["who dwell free of charge in their employing household, irrespective of their sex, race or "
               "nationality"]},
    {"id": "HK-3", "where": "Hong Kong", "page": "hk_maw_2025.html", "level": "official text",
     "what": "minimum allowable wage of foreign domestic helpers, a monthly floor",
     "kind": "a separate class of provider", "floor_per_month": 5100.0,
     "words": ["from $4,990 to $5,100 per month"]},
]

STATES = {"between larger": "the spread between sovereigns is the larger one in every year",
          "within larger": "the spread across levels of pay inside a sovereign is the larger one in every year",
          "unread": "the order changes with the year, or a spread is undefined"}


# ----------------------------------------------------------------------------- reading the files
def read_wedges(path: Path) -> dict:
    """code -> name and (year, level) -> marginal tax wedge in percent of labour cost."""
    out, units, words = {}, Counter(), Counter()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["MEASURE"] != MEASURE or r["HOUSEHOLD_TYPE"] != HOUSEHOLD or len(r["REF_AREA"]) != 3:
                continue
            units[r["UNIT_MEASURE"]] += 1
            words[r["Measure"]] += 1
            c = out.setdefault(r["REF_AREA"], {"name": r["Reference area"], "wedge": {}})
            c["wedge"][(r["TIME_PERIOD"], r["INCOME_PRINCIPAL"])] = float(r["OBS_VALUE"])
    return {"countries": out, "units": dict(units), "words": dict(words)}


def read_vat(path: Path) -> dict:
    """name -> standard rate in the table's last year."""
    import openpyxl
    rows = [list(r) for r in openpyxl.load_workbook(path, data_only=True).worksheets[0].iter_rows(values_only=True)]
    head = next(i for i, r in enumerate(rows) if sum(str(c).isdigit() and len(str(c)) == 4 for c in r) > 5)
    years = [(j, str(c)) for j, c in enumerate(rows[head]) if str(c).isdigit() and len(str(c)) == 4]
    col, year = years[-1]
    rates = {}
    for r in rows[head + 1:]:
        name = str(r[0] or "").replace("*", "").strip()
        try:
            rate = float(str(r[col]).strip("() "))
        except ValueError:
            continue
        if name and "average" not in name.lower():
            rates[ALIASES.get(name, name)] = rate
    return {"year": year, "rates": rates, "title": str(rows[head - 1][0] if head else "")}


def load() -> dict:
    tw = read_wedges(OECD / "tw_comp.csv")
    vat = read_vat(OECD / "vat_rates.xlsx")
    pages = {p.name: page_text(p) for p in sorted(LAW.iterdir())
             if p.is_file() and ".partial" not in p.name and not p.name.endswith(".writing")}
    return {"tw": tw, "vat": vat, "pages": pages, "rows": copy.deepcopy(ROWS)}


# ----------------------------------------------------------------------------- the table
def vat_of(data: dict, code: str):
    if code in NO_VAT:
        return 0.0
    name = data["tw"]["countries"][code]["name"]
    rate = data["vat"]["rates"].get(name)
    return None if rate is None else rate / 100.0


def multiple(data: dict, code: str, year: str, level: str) -> float:
    m = data["tw"]["countries"].get(code, {}).get("wedge", {}).get((year, level))
    v = vat_of(data, code) if code in data["tw"]["countries"] else None
    if m is None or v is None or m >= 100:
        return math.nan
    return (1.0 + v) / (1.0 - m / 100.0)


def table(data: dict) -> dict:
    """code -> year -> level -> multiple, for the countries that have every cell."""
    out = {}
    for code in sorted(data["tw"]["countries"]):
        cells = {y: {lv: multiple(data, code, y, lv) for lv in LEVELS} for y in YEARS}
        if all(math.isfinite(x) for y in cells.values() for x in y.values()):
            out[code] = cells
    return out


def spreads(tab: dict) -> list:
    rows = []
    for y in YEARS:
        ref = [math.log(tab[c][y][LEVELS[0]]) for c in tab]
        inside = [float(np.std([math.log(tab[c][y][lv]) for lv in LEVELS])) for c in tab]
        rows.append({"year": y, "between": float(np.std(ref)) if ref else math.nan,
                     "within_median": float(np.median(inside)) if inside else math.nan,
                     "within_max": float(max(inside)) if inside else math.nan})
    return rows


def state_of(rows: list) -> str:
    if not rows or any(not math.isfinite(r["between"]) or not math.isfinite(r["within_median"]) for r in rows):
        return "unread"
    if all(r["between"] > r["within_median"] for r in rows):
        return "between larger"
    if all(r["between"] < r["within_median"] for r in rows):
        return "within larger"
    return "unread"


def faults(data: dict) -> list:
    """Everything wrong with the provision rows, as sentences. Empty when the rows hold."""
    out, seen = [], Counter(r["id"] for r in data["rows"])
    for r in data["rows"]:
        if seen[r["id"]] > 1:
            out.append(f"{r['id']}: the id is used {seen[r['id']]} times")
        if r["kind"] not in ROW_KINDS:
            out.append(f"{r['id']}: unknown kind {r['kind']!r}")
        if r["level"] not in LEVELS_OF_SOURCE:
            out.append(f"{r['id']}: unknown level {r['level']!r}")
        if (r["kind"] == "credit to the buyer") != ("cut" in r):
            out.append(f"{r['id']}: a credit carries a share and nothing else does")
        text = data["pages"].get(r["page"])
        if text is None:
            out.append(f"{r['id']}: page {r['page']} is not cached")
            continue
        if not r["words"]:
            out.append(f"{r['id']}: no words")
        for w in r["words"]:
            if squeeze(w) not in text:
                out.append(f"{r['id']}: words not on the page: {w[:40]}")
    used = {r["page"] for r in data["rows"]}
    for name in data["pages"]:
        if name not in used:
            out.append(f"page {name} is cached and no row rests on it")
    return out


# ----------------------------------------------------------------------------- criteria
def c_e0(data: dict, tab: dict):
    problems = []
    tw = data["tw"]
    if set(tw["units"]) != {UNIT}:
        problems.append(f"the marginal wedge is in {sorted(tw['units'])}, not in percent of labour cost")
    if set(tw["words"]) != {MEASURE_WORDS}:
        problems.append(f"the measure is called {sorted(tw['words'])}")
    if len(tab) < 30:
        problems.append(f"only {len(tab)} countries carry every year and level")
    for code, c in tw["countries"].items():
        if code not in NO_VAT and data["vat"]["rates"].get(c["name"]) is None:
            problems.append(f"no VAT rate for {c['name']}")
    if data["vat"]["year"] != YEARS[0]:
        problems.append(f"the VAT table ends in {data['vat']['year']}, the reference year is {YEARS[0]}")
    uk = multiple(data, "GBR", YEARS[-1], "AW67")
    want = STATUTE / KEPT
    if not math.isfinite(uk) or abs(uk - want) > 0.005:
        problems.append(f"the United Kingdom at two thirds of the average wage in {YEARS[-1]} gives {uk:.4f}, "
                        f"the rate pages give {want:.4f}")
    detail = (f"{len(tw['countries'])} countries in the labour-tax table, {len(tab)} with every year and level; "
              f"VAT table '{data['vat']['title'][:40]}' with {len(data['vat']['rates'])} rows, last year "
              f"{data['vat']['year']}; the United Kingdom at two thirds of the average wage in {YEARS[-1]}: "
              f"{uk:.4f} against {want:.4f} from the government's rate pages; "
              + ("; ".join(problems) if problems else "units and names as expected"))
    return not problems, detail, {"problems": problems, "uk": uk, "from_rate_pages": want}


def c_e1(data: dict, tab: dict):
    rows = spreads(tab)
    state = state_of(rows)
    ref = {c: tab[c][YEARS[0]][LEVELS[0]] for c in tab}
    order = sorted(ref, key=ref.get)
    name = lambda c: data["tw"]["countries"][c]["name"]                    # noqa: E731
    named = ", ".join(f"{name(c)} {ref[c]:.2f}" for c in NAMED if c in ref)
    r0 = rows[0]
    detail = ((f"{len(ref)} countries at the average wage in {YEARS[0]}: lowest {name(order[0])} "
               f"{ref[order[0]]:.2f}, median {float(np.median(list(ref.values()))):.2f}, highest "
               f"{name(order[-1])} {ref[order[-1]]:.2f}; {named}. " if ref else "no country; ")
              + f"Spread of the log multiple between countries {r0['between']:.3f}, across the three levels of "
              f"pay inside a country {r0['within_median']:.3f} at the median and {r0['within_max']:.3f} at most; "
              f"over the years between {min(r['between'] for r in rows):.3f} to "
              f"{max(r['between'] for r in rows):.3f}, within {min(r['within_median'] for r in rows):.3f} to "
              f"{max(r['within_median'] for r in rows):.3f} -> {state}")
    passed = True if state == "between larger" else (False if state == "within larger" else None)
    return passed, detail, {"state": state, "spreads": rows, "order": order}


def c_e2(data: dict):
    f = faults(data)
    n = sum(len(r["words"]) for r in data["rows"])
    detail = (f"{len(data['rows'])} rows, {n} passages, {len(data['pages'])} cached pages; "
              + ("; ".join(f[:6]) if f else "every passage is on its page and every page carries a row")
              + ". Kinds: " + ", ".join(f"{k} {v}" for k, v in Counter(r["kind"] for r in data["rows"]).items()))
    return not f, detail, {"faults": f}


def c_e3(data: dict, tab: dict):
    ref = {c: tab[c][YEARS[0]][LEVELS[0]] for c in tab}
    order = sorted(ref, key=ref.get, reverse=True)
    credits = [r for r in data["rows"] if r["kind"] == "credit to the buyer"]
    out, bad = [], []
    for r in credits:
        before = ref.get(r.get("code"), math.nan)
        cut = r.get("cut", math.nan)
        after = before * (1.0 - cut) if math.isfinite(before) and isinstance(cut, float) else math.nan
        ok = math.isfinite(after) and 0.0 < cut < 1.0 and after < before
        if not ok:
            bad.append(r["id"])
        out.append({"id": r["id"], "where": r["where"], "cut": cut, "before": before, "after": after,
                    "rank": order.index(r["code"]) + 1 if r.get("code") in order else None})
    hk_hour = next((r["floor_per_hour"] for r in data["rows"] if "floor_per_hour" in r), math.nan)
    hk_month = next((r["floor_per_month"] for r in data["rows"] if "floor_per_month" in r), math.nan)
    hours = hk_month / hk_hour if hk_hour else math.nan
    detail = ("; ".join(f"{o['where']} writes back {100 * o['cut']:.0f}% to the buyer: {o['before']:.2f} to "
                        f"{o['after']:.2f} (rank {o['rank']} of {len(order)} before)" for o in out)
              + f". Lowered by every credit read: {len(out) - len(bad)} of {len(out)}"
              + (f"; not lowered or not joined: {bad}" if bad else "")
              + f". Hong Kong writes two floors for work in a household: {hk_hour:g} an hour, and "
              f"{hk_month:g} a month for a helper who lives in; the monthly floor equals the hourly one at "
              f"{hours:.0f} hours a month")
    passed = bool(out) and not bad
    return passed, detail, {"credits": out, "hong_kong_hours_at_which_the_floors_meet": hours}


KINDS = {"B144-E0": "instrument", "B144-E1": "own_reading", "B144-E2": "bookkeeping", "B144-E3": "own_reading"}
STATEMENTS = {
    "B144-E0": "The OECD's two files say what the reading takes them to say, and the United Kingdom's row "
               "returns the multiple computed from the government's own rate pages.",
    "B144-E1": "The statute-only multiple differs between sovereigns by more than it moves with the level of "
               "pay inside one.",
    "B144-E2": "Every row has its words on a cached page and every cached page carries a row.",
    "B144-E3": "Every credit to the buyer that was read lowers the multiple of the sovereign that wrote it.",
}


def r4(x):
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else round(float(x), 4)
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return x


def run(data: dict):
    tab = table(data)
    return {"B144-E0": c_e0(data, tab), "B144-E1": c_e1(data, tab), "B144-E2": c_e2(data),
            "B144-E3": c_e3(data, tab)}, tab


def record_of(data: dict, res: dict, tab: dict) -> dict:
    names = {c: data["tw"]["countries"][c]["name"] for c in tab}
    return {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": p, "statement": STATEMENTS[n], "detail": d}
                     for n, (p, d, _) in res.items()],
        "mapping": {"states": STATES, "verdict": "true for 'between larger', false for 'within larger', null "
                                                 "for 'unread'"},
        "objects": {"multiple": r4({names[c]: tab[c] for c in tab}),
                    "marginal_wedge_percent": r4({names[c]: {y: {lv: data["tw"]["countries"][c]["wedge"][(y, lv)]
                                                              for lv in LEVELS} for y in YEARS} for c in tab}),
                    "vat_percent": r4({names[c]: (0.0 if c in NO_VAT else data["vat"]["rates"][names[c]])
                                       for c in tab}),
                    "states": {n: r4(o) for n, (_, _, o) in res.items()}},
        "rows": data["rows"],
        "config": {"raw": "data/raw/b144/oecd", "pages": "data/raw/b144/law_labour",
                   "fetched_by": "experiments/b144_fetch.py --only oecd, --only cuts",
                   "household": HOUSEHOLD, "measure": MEASURE, "levels": list(LEVELS), "years": list(YEARS),
                   "vat_year": data["vat"]["year"], "no_vat_row": list(NO_VAT), "aliases": ALIASES,
                   "row_kinds": list(ROW_KINDS)},
    }


# ----------------------------------------------------------------------------- selftest
def toy(spread_between=0.3, spread_within=0.05, n=34) -> dict:
    """Countries whose marginal wedges differ by one amount between them and by another across levels."""
    countries, rates = {}, {}
    for i in range(n):
        code = f"C{i:02d}" if i else "GBR"
        name = "United Kingdom" if code == "GBR" else f"Country {i}"
        base = 0.30 + spread_between * (i / (n - 1) - 0.5)
        wedge = {}
        for y in YEARS:
            for k, lv in enumerate(LEVELS):
                wedge[(y, lv)] = 100.0 * (base + spread_within * (k - 1))
        countries[code] = {"name": name, "wedge": wedge}
        rates[name] = 20.0
    countries["GBR"]["wedge"][(YEARS[-1], "AW67")] = 100.0 * (1.0 - KEPT * 1.2 / STATUTE)
    countries["USA"] = {"name": "United States", "wedge": dict(countries["C01"]["wedge"])}
    rows = [{"id": "X-1", "where": "United Kingdom", "code": "GBR", "page": "a.html", "level": "official text",
             "what": "a credit", "kind": "credit to the buyer", "cut": 0.5, "words": ["half of the cost"]},
            {"id": "X-2", "where": "Hong Kong", "page": "b.html", "level": "official description",
             "what": "two floors", "kind": "a separate class of provider", "floor_per_hour": 40.0,
             "floor_per_month": 5000.0, "words": ["an hourly floor"]}]
    return {"tw": {"countries": countries, "units": {UNIT: 1}, "words": {MEASURE_WORDS: 1}},
            "vat": {"year": YEARS[0], "rates": rates, "title": "toy"},
            "pages": {"a.html": "the buyer gets half of the cost back", "b.html": "there is an hourly floor"},
            "rows": rows}


def selftest() -> None:
    d = toy()
    assert abs(multiple(d, "C05", YEARS[0], "AW100") - 1.2 / (1 - d["tw"]["countries"]["C05"]["wedge"][
        (YEARS[0], "AW100")] / 100)) < 1e-12
    assert abs(multiple(d, "USA", YEARS[0], "AW100") * 1.2 - multiple(d, "C01", YEARS[0], "AW100")) < 1e-12, \
        "a country without a row in the VAT table is read with no tax on the invoice"
    assert math.isnan(multiple(d, "ZZZ", YEARS[0], "AW100"))
    res, tab = run(d)
    assert res["B144-E0"][0], res["B144-E0"][1]
    assert res["B144-E1"][0] is True and res["B144-E2"][0] and res["B144-E3"][0]
    assert abs(res["B144-E3"][2]["credits"][0]["after"] / res["B144-E3"][2]["credits"][0]["before"] - 0.5) < 1e-12
    assert abs(res["B144-E3"][2]["hong_kong_hours_at_which_the_floors_meet"] - 125.0) < 1e-9

    # E1: sovereigns alike, levels of pay apart; and an order that changes with the year
    assert run(toy(spread_between=0.01, spread_within=0.10))[0]["B144-E1"][0] is False
    mixed = toy(spread_between=0.02, spread_within=0.02)
    for c in mixed["tw"]["countries"].values():
        for lv in LEVELS:
            c["wedge"][(YEARS[1], lv)] = c["wedge"][(YEARS[1], "AW100")]
    assert state_of(spreads(table(mixed))) in ("unread", "between larger")
    assert state_of([{"between": 0.2, "within_median": 0.1}, {"between": 0.1, "within_median": 0.2}]) == "unread"
    assert state_of([]) == "unread" and state_of([{"between": math.nan, "within_median": 0.1}]) == "unread"

    # E0: each thing it reads, broken once
    def broken(change):
        b = toy()
        if change == "unit":
            b["tw"]["units"] = {"PT_WG_EARN_G": 1}
        elif change == "measure":
            b["tw"]["words"] = {"Average tax wedge": 1}
        elif change == "few":
            b["tw"]["countries"] = {k: v for k, v in list(b["tw"]["countries"].items())[:10]}
        elif change == "vat":
            del b["vat"]["rates"]["Country 7"]
        elif change == "vat year":
            b["vat"]["year"] = "2019"
        elif change == "uk":
            b["tw"]["countries"]["GBR"]["wedge"][(YEARS[-1], "AW67")] += 2.0
        return b
    for change in ("unit", "measure", "few", "vat", "vat year", "uk"):
        bb = broken(change)
        assert not c_e0(bb, table(bb))[0], f"E0 must fail on {change}"

    # E2 and E3: the rows, broken once each
    def rows_broken(change):
        b = toy()
        if change == "letter":
            b["rows"][0]["words"][0] = "half of the cast"
        elif change == "page":
            del b["pages"]["a.html"]
        elif change == "idle page":
            b["pages"]["c.html"] = "nothing rests here"
        elif change == "kind":
            b["rows"][1]["kind"] = "a rebate"
        elif change == "twice":
            b["rows"].append(copy.deepcopy(b["rows"][0]))
        elif change == "no share":
            del b["rows"][0]["cut"]
        elif change == "no words":
            b["rows"][1]["words"] = []
        return b
    for change in ("letter", "page", "idle page", "kind", "twice", "no share", "no words"):
        assert not c_e2(rows_broken(change))[0], f"E2 must fail on {change}"
    for change in ("zero", "whole", "elsewhere"):
        b = toy()
        if change == "zero":
            b["rows"][0]["cut"] = 0.0
        elif change == "whole":
            b["rows"][0]["cut"] = 1.0
        else:
            b["rows"][0]["code"] = "ZZZ"
        assert not c_e3(b, table(b))[0], f"E3 must fail on {change}"
    none = toy()
    none["rows"] = [none["rows"][1]]
    assert not c_e3(none, table(none))[0], "no credit read is not a pass"
    # the two readers of files, on files written for the purpose
    import tempfile

    import openpyxl
    with tempfile.TemporaryDirectory() as tmp:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Annex Table. VAT rates"])
        ws.append([None, "2005", "2007", "2008", "2009", "2010", "2011", "Temporary", "2023", "Reduced rates"])
        ws.append(["Austria*", "20", "20", "20", "20", "20", "20", None, "21", "10.0"])
        ws.append(["Czech Republic", "19", "19", "19", "19", "20", "20", "(0.0)", "(22)", "15"])
        ws.append(["Unweighted average", "19", "19", "19", "19", "19", "19", None, "19.5", None])
        wb.save(Path(tmp) / "v.xlsx")
        v = read_vat(Path(tmp) / "v.xlsx")
        assert v["year"] == "2023" and v["rates"] == {"Austria": 21.0, "Czechia": 22.0}, v
        head = ("REF_AREA,Reference area,MEASURE,Measure,UNIT_MEASURE,HOUSEHOLD_TYPE,INCOME_PRINCIPAL,"
                "TIME_PERIOD,OBS_VALUE\n")
        body = ("AUT,Austria,MR_TW_PE,Marginal tax wedge of the principal earner,PT_COS_LB,S_C0,AW100,2023,59.5\n"
                "AUT,Austria,MR_TW_PE,Marginal tax wedge of the principal earner,PT_COS_LB,C_C2,AW100,2023,10\n"
                "AUT,Austria,AV_TW,Average tax wedge,PT_COS_LB,S_C0,AW100,2023,47\n"
                "OECD_REP,OECD,MR_TW_PE,Marginal tax wedge of the principal earner,PT_COS_LB,S_C0,AW100,2023,40\n")
        (Path(tmp) / "w.csv").write_text(head + body, encoding="utf-8")
        w = read_wedges(Path(tmp) / "w.csv")
        assert list(w["countries"]) == ["AUT"] and w["countries"]["AUT"]["wedge"] == {("2023", "AW100"): 59.5}, w
    part = toy()
    del part["tw"]["countries"]["C03"]["wedge"][(YEARS[1], "AW67")]
    assert "C03" not in table(part), "a country with a cell missing is not in the table"
    print("selftest ok: planted wedges come back as multiples, and every flag fails on its planted input")


def main() -> int:
    data = load()
    res, tab = run(data)
    for name, (passed, detail, _) in res.items():
        word = "PASS" if passed else ("UNREAD" if passed is None else "FAIL")
        print(f"{word} {name} [{KINDS[name]}]: {detail}")
    OUT.write_text(json.dumps(record_of(data, res, tab), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-E0"][0] and res["B144-E2"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
