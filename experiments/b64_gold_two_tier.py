"""B64: the two-tier gold market, and what set the life of dollar convertibility.

A dollar held by a foreign monetary authority could be turned into gold at 35
dollars an ounce. From November 1961 a pool of central banks also held that price
on the London market. On 17 March 1968 the market was split: official
transactions stayed at 35 and everyone else traded at a free price. On
15 August 1971 the window closed.

The stage reads three things against the stated corollaries of B63: the United
States' gold across the dated restrictions on who could walk that conversion,
the free price against 35, and the South African arrangement of 30 December 1969
as a priced edge under the free price.

Parts:

  checks   B64-1 and B64-2, the two criteria that ask about this run's inputs.
           Record: results/b64_checks.json
  main     B64-3 to B64-8, the stage's readings.
           Record: results/b64_gold_two_tier.json

Run:

    python experiments\\b64_gold_two_tier.py --part checks
    python experiments\\b64_gold_two_tier.py --part main
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "b64"
FIXING = DATA / "lbma_gold_usd_am_pm_19680401_19711231.csv"
STOCK = DATA / "fred_M1476CUSM144NNBR.csv"
OUT_CHECKS = ROOT / "results" / "b64_checks.json"

# Recorded at retrieval: a 32-bit rolling hash (h = 31*h + ord(c), mod 2**32)
# of the whole file, computed in the browser on the source text.
FIXING_HASH, FIXING_LEN = 849329907, 21021
STOCK_HASH, STOCK_LEN = 2540559288, 4930

TICK = Decimal("0.01")          # the fixing is printed to the cent in this period

# Published anchors the price file is read back against. The first two are from
# testimony to the Joint Economic Committee in November 1969; the third is from a
# collector's history and may be an intraday price, so it is printed, not judged.
ANCHORS = [
    {"name": "April 1968 low", "month": "1968-04", "side": "min",
     "value": Decimal("36.70"), "judged": True,
     "source": "Joint Economic Committee hearing, November 1969: "
               "'low of $36.70 an ounce, in April 1968'"},
    {"name": "March 1969 high", "month": "1969-03", "side": "max",
     "value": Decimal("43.82"), "judged": True,
     "source": "same hearing: 'high of $43.82 an ounce in March 1969'"},
    {"name": "40 touched on 1968-05-17", "date": "1968-05-17",
     "value": Decimal("40.00"), "judged": False,
     "source": "Coin World, the two-tier system: 'On May 17, 1968, it touched $40 "
               "an ounce on the London market'"},
]

# Discipline 11c: every state of a criterion with more than two states, and the
# verdict it maps to. Printed with the verdict, not only the verdict.
MAPPING_B64_2 = {
    "exact": "PASS: the anchor is one of the fixings",
    "one_tick": "PASS: within one printed cent of a fixing",
    "off": "FAIL (instrument): the source quotes another price; find which before any reading",
    "printed_only": "no verdict: the anchor may be intraday",
}


def rolling_hash(text: str) -> int:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def read_checked(path: Path, want_hash: int, want_len: int) -> str:
    """Read a file and refuse it unless it is the one recorded at retrieval."""
    text = path.read_text(encoding="utf-8")
    got = rolling_hash(text)
    if len(text) != want_len or got != want_hash:
        raise SystemExit(f"{path.name}: length {len(text)} hash {got}, recorded "
                         f"{want_len} {want_hash}. The file is not the one retrieved; "
                         f"it is reported here rather than read.")
    return text


def parse_price(cell: str):
    if cell == "":
        return None
    v = Decimal(cell)
    if v.as_tuple().exponent < -2:
        raise SystemExit(f"a fixing with more than two decimals: {cell}")
    return v


def load_fixing():
    text = read_checked(FIXING, FIXING_HASH, FIXING_LEN)
    lines = text.rstrip("\n").split("\n")
    if lines[0] != "date,usd_am,usd_pm":
        raise SystemExit(f"fixing header: {lines[0]!r}")
    rows = []
    for ln in lines[1:]:
        d, a, p = ln.split(",")
        rows.append((dt.date.fromisoformat(d), parse_price(a), parse_price(p)))
    return rows


def load_stock():
    text = read_checked(STOCK, STOCK_HASH, STOCK_LEN)
    lines = text.rstrip("\n").split("\n")
    if lines[0] != "observation_date,M1476CUSM144NNBR":
        raise SystemExit(f"stock header: {lines[0]!r}")
    rows = []
    for ln in lines[1:]:
        d, v = ln.split(",")
        rows.append((dt.date.fromisoformat(d), int(v)))
    return rows


def check_b64_1(fix, stock):
    dates = [r[0] for r in fix]
    increasing = all(a < b for a, b in zip(dates, dates[1:]))
    weekdays = all(d.weekday() < 5 for d in dates)
    am_only = sum(1 for _, a, p in fix if a is not None and p is None)
    pm_only = sum(1 for _, a, p in fix if a is None and p is not None)
    neither = sum(1 for _, a, p in fix if a is None and p is None)
    zeros = sum(1 for _, a, p in fix for v in (a, p) if v is not None and v == 0)
    ams = [a for _, a, _ in fix if a is not None]
    pms = [p for _, _, p in fix if p is not None]
    months = [d for d, _ in stock]
    consecutive = all((b.year * 12 + b.month) - (a.year * 12 + a.month) == 1
                      for a, b in zip(months, months[1:]))
    firsts = all(d.day == 1 for d in months)
    vals = [v for _, v in stock]
    ok = (increasing and weekdays and neither == 0 and zeros == 0 and consecutive
          and firsts and len(fix) == 954 and len(stock) == 288)
    detail = (f"fixing: {len(fix)} dates {dates[0]} to {dates[-1]}, strictly increasing "
              f"{increasing}, all weekdays {weekdays}; morning only {am_only}, afternoon "
              f"only {pm_only}, neither {neither}; zero values {zeros}; morning "
              f"{min(ams)} to {max(ams)}, afternoon {min(pms)} to {max(pms)}. gold stock: "
              f"{len(stock)} months {months[0]:%Y-%m} to {months[-1]:%Y-%m}, consecutive "
              f"{consecutive}, integer millions {min(vals)} to {max(vals)}. Both files "
              f"match the hashes recorded at retrieval")
    return ok, detail


def check_b64_2(fix):
    by_month = {}
    for d, a, p in fix:
        key = f"{d:%Y-%m}"
        for side, v in (("am", a), ("pm", p)):
            if v is not None:
                by_month.setdefault(key, {}).setdefault(side, []).append((v, d))
    out, verdicts = [], []
    for an in ANCHORS:
        if "date" in an:
            day = dt.date.fromisoformat(an["date"])
            row = next(r for r in fix if r[0] == day)
            first40 = next((r for r in fix
                            if (r[1] is not None and r[1] >= an["value"])
                            or (r[2] is not None and r[2] >= an["value"])), None)
            out.append({"anchor": an["name"], "source": an["source"],
                        "state": "printed_only",
                        "on_the_day": {"am": str(row[1]), "pm": str(row[2])},
                        "first_fixing_at_or_above": {"date": first40[0].isoformat(),
                                                     "am": str(first40[1]),
                                                     "pm": str(first40[2])}})
            continue
        cells = {}
        best = None
        for side in ("am", "pm"):
            vs = by_month[an["month"]][side]
            pick = min(vs) if an["side"] == "min" else max(vs)
            cells[side] = {"value": str(pick[0]), "date": pick[1].isoformat()}
            gap = abs(pick[0] - an["value"])
            if best is None or gap < best:
                best = gap
        state = "exact" if best == 0 else ("one_tick" if best <= TICK else "off")
        verdicts.append(state in ("exact", "one_tick"))
        out.append({"anchor": an["name"], "source": an["source"], "published": str(an["value"]),
                    "month_extreme": cells, "closest_gap": str(best), "state": state,
                    "maps_to": MAPPING_B64_2[state]})
    ok = all(verdicts)
    parts = []
    for o in out:
        if o["state"] == "printed_only":
            parts.append(f"{o['anchor']}: that day am {o['on_the_day']['am']} pm "
                         f"{o['on_the_day']['pm']}; first fixing at or above 40 is "
                         f"{o['first_fixing_at_or_above']['date']} (am "
                         f"{o['first_fixing_at_or_above']['am']}, pm "
                         f"{o['first_fixing_at_or_above']['pm']}); printed, no verdict")
        else:
            parts.append(f"{o['anchor']} published {o['published']}: morning "
                         f"{o['month_extreme']['am']['value']} on {o['month_extreme']['am']['date']}, "
                         f"afternoon {o['month_extreme']['pm']['value']} on "
                         f"{o['month_extreme']['pm']['date']}; state {o['state']}")
    return ok, "; ".join(parts), out


def part_checks():
    fix = load_fixing()
    stock = load_stock()
    ok1, d1 = check_b64_1(fix, stock)
    ok2, d2, anchors = check_b64_2(fix)
    criteria = [
        {"name": "B64-1", "kind": "instrument", "passed": bool(ok1),
         "statement": "both series load, parse and carry the units the stage reads; an "
                      "empty cell is not read as a zero",
         "detail": d1},
        {"name": "B64-2", "kind": "known_answer", "passed": bool(ok2),
         "statement": "the price file reproduces the published anchors for April 1968 and "
                      "March 1969; the May 1968 anchor is printed",
         "detail": d2, "mapping": MAPPING_B64_2},
    ]
    rec = {
        "stage": "B64-checks",
        "config": {
            "fixing_file": FIXING.name, "fixing_hash": FIXING_HASH, "fixing_len": FIXING_LEN,
            "stock_file": STOCK.name, "stock_hash": STOCK_HASH, "stock_len": STOCK_LEN,
            "tick": str(TICK),
        },
        "criteria": criteria,
        "report": {"anchors": anchors},
    }
    OUT_CHECKS.parent.mkdir(parents=True, exist_ok=True)
    OUT_CHECKS.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    print("=" * 78)
    print("B64 checks: the inputs, before any reading")
    print("=" * 78)
    for c in criteria:
        print(f"\n{c['name']} [{c['kind']}]  {'PASS' if c['passed'] else 'FAIL'}\n  "
              f"{c['statement']}\n  {c['detail']}")
    print("\n  mapping for B64-2 (11c):")
    for k, v in MAPPING_B64_2.items():
        print(f"    {k:13s} -> {v}")
    print(f"\n  record: results/{OUT_CHECKS.name}")
    return 0 if all(c["passed"] for c in criteria) else 1


# ---------------------------------------------------------------------------
# Part main: B64-3 to B64-8
# ---------------------------------------------------------------------------

TABLE4 = DATA / "frb_table4_us_reserve_assets.csv"
TABLE6 = DATA / "frb_table6_us_liquid_liabilities.csv"
TABLE4_HASH, TABLE4_LEN = 1998692235, 5274
TABLE6_HASH, TABLE6_LEN = 489931139, 5726
BMN_ZIP = ROOT / "data" / "raw" / "ICPSR_111725-V1.1.zip"
BMN_SHA256 = "e18cf09f898632da83d0b2727d03f0c031dc7ed290ef9e27961a94fa2d90af72"
BMN_MEMBER = ("ICPSR_111725-V1.1/"
              "data-file---The-Gold-Pool-Bordo--Monnet-and-Naef-2019.xlsx")
BMN_SHEET = "Gold Window data"
BMN_FIRST_ROW, BMN_LAST_ROW = 3, 18      # 1965 Q1 to 1968 Q4, the sheet's top table
BMN_COUNTRY = {                          # the sheet's top table, one column per customer
    "belgium": "O", "germany": "R", "italy": "U", "netherlands": "V", "switzerland": "Z",
    "uk_incl_pool": "AB", "france": "Q",
}
GP_MEMBERS = ("belgium", "germany", "italy", "netherlands", "switzerland")
BMN_TOTALS = {"imf": "CF", "foreign_total": "CG", "industry": "CH", "movement": "CI"}
# The authors' two classification tables, printed as delivered and compared with the
# classes formed here from the country columns.
BMN_FINAL = {"gp_members": "CT", "non_members": "CU", "uk_incl_pool": "CV", "france": "CW"}
BMN_OTHER = {"gp_members": "CM", "non_members": "CN", "uk_incl_pool": "CO", "france": "CP"}
CLASSES = ("gp_members", "non_members", "uk_incl_pool", "france")
BMN_MISSING = "1966 Q4"                 # absent from the archive source; the sheet prints zeros
OUT_MAIN = ROOT / "results" / "b64_gold_two_tier.json"

EVENTS = [
    {"date": "1961-11", "name": "Gold Pool founded",
     "restriction": None,
     "what": "the Pool sells in London to hold 35 and the United States supplies its share, "
             "so the private class reaches US gold through the Pool"},
    {"date": "1967-03-30", "name": "letter of the Bundesbank",
     "restriction": "one member: the Bundesbank undertakes not to convert on a large scale",
     "what": "restricts one official holder"},
    {"date": "1968-03-17", "name": "two-tier market",
     "restriction": "the private class: official transactions stay at 35, the rest trade at a free price",
     "what": "cuts the private class from the conversion"},
    {"date": "1969-12-30", "name": "South Africa and the IMF",
     "restriction": None,
     "what": "adds a priced edge under the free price: South Africa may sell new gold to the IMF "
             "at 35 when the free price is at or below 35"},
    {"date": "1971-08-15", "name": "window closed",
     "restriction": "every class", "what": "ends the conversion"},
]
ARRANGEMENT = dt.date(1969, 12, 30)
FLOOR = Decimal("35.00")

# Official operations beside the conversion demand. The second reading of B64-3 nets out
# the IMF's gold transactions (computed from table 6 and the gold-window table), which are
# not the conversion edge at all. The items below are printed and kept in: an official
# holder selling gold to the United States walks the same edge in the other direction, and a
# swap drawing settled in gold is an official holder's dollar claim turned into gold.
ITEMS = [
    {"window": "split to arrangement", "date": "1968 Q2 to Q4", "amount": 600, "netted": False,
     "item": "France sold gold to the United States",
     "source": "the France line of the gold-window table (220, 240 and 140 by quarter)"},
    {"window": "split to arrangement", "date": "1969-12-29", "amount": 500, "netted": False,
     "item": "the Bundesbank sold gold to the United States Treasury",
     "source": "Federal Reserve Bank of New York, Monthly Review, March 1970: 'Germany sold "
               "$500 million of gold to the United States Treasury on December 29'"},
    {"window": "arrangement to close", "date": "1970", "amount": -570, "netted": False,
     "item": "the United States Treasury sold gold to the Swiss National Bank (550) and the "
             "Netherlands Bank (20) to clear swap drawings",
     "source": "Federal Reserve Bank of New York, Monthly Review, September 1970"},
]

# B64-6: the two adjustments of the official price after the window closed, from the texts.
OFFICIAL_PRICE = [
    {"step": "December 1971", "usd_per_oz": "38",
     "decision": {"date": "1971-12-17/18",
                  "quote": "Connally also said the administration would approach the Congress "
                           "for authority to increase the gold price to $38 per ounce",
                  "source": "Foreign Relations of the United States, 1969-1976, Volume III, "
                            "Document 221, Editorial Note"},
     "law": {"date": "1972-03-31",
             "quote": "The Secretary of the Treasury is hereby authorized and directed to take the "
                      "steps necessary to establish a new par value of the dollar of $1 equals one "
                      "thirty-eighth of a fine troy ounce of gold.",
             "source": "Par Value Modification Act, Public Law 92-268, 86 Stat. 116, section 2"}},
    {"step": "February 1973", "usd_per_oz": "42.2222",
     "decision": {"date": "1973-02-12",
                  "quote": "a 10 percent devaluation of the dollar",
                  "source": "The American Presidency Project, Richard Nixon, Remarks Following "
                            "Announcement of a Devaluation of the Dollar, 13 February 1973, note "
                            "on the Secretary of the Treasury's announcement"},
     "law": {"date": "1973-09-21",
             "quote": "0.828948 Special Drawing Right or, the equivalent in terms of gold, of "
                      "forty-two and two-ninths dollars per fine troy ounce of gold",
             "source": "Public Law 93-110, 87 Stat. 352, amending section 2 of the Par Value "
                       "Modification Act"}},
]

MAPPING_B64_3 = {
    "slower": "PASS: after the split the gold stock fell more slowly than in the year before it, "
              "on the total basis, with and without the official operations that are not the "
              "conversion demand",
    "not_slower": "FAIL: the reading is withdrawn",
    "inseparable": "no verdict: the comparison turns on official operations that are not the "
                   "conversion demand; they are printed item by item",
}
MAPPING_B64_4 = {
    "floor": "PASS: no fixing below 35 by more than the printed cent after the arrangement, "
             "and some before",
    "floor_with_friction": "PASS, read with friction: fixings below 35 after the arrangement, "
                           "days and depth printed; whether to sell rested with South Africa",
    "not_identified": "no verdict: no fixing below 35 before or after, the floor is not identified",
}
MAPPING_B64_5 = {"printed": "no verdict: printed only"}
MAPPING_B64_6 = {"devaluation": "PASS: the dollar lost gold content at both adjustments",
                 "revaluation": "FAIL: the reading is withdrawn",
                 "mixed": "no verdict: the two adjustments point in different directions"}
MAPPING_B64_7 = {"printed": "PASS: printed", "missing": "FAIL (bookkeeping): print it"}
MAPPING_B64_8 = {"written": "PASS: written", "missing": "FAIL (bookkeeping): write it"}

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def read_sheet(xbytes: bytes, sheet_name: str) -> dict:
    """The cells of one worksheet, {reference: value}, from the workbook's stored results.

    A spreadsheet file is a zip of XML parts; this reads the parts directly so the
    stage needs no spreadsheet library. Formulas are not evaluated: the value stored
    with each formula when the authors saved the file is read."""
    with zipfile.ZipFile(io.BytesIO(xbytes)) as x:
        wb = ET.fromstring(x.read("xl/workbook.xml"))
        rid = next(s.get(_NS_REL + "id") for s in wb.iter(_NS + "sheet")
                   if s.get("name") == sheet_name)
        rels = ET.fromstring(x.read("xl/_rels/workbook.xml.rels"))
        target = next(r.get("Target") for r in rels if r.get("Id") == rid)
        part = target.lstrip("/") if target.startswith("/") else "xl/" + target
        shared = []
        if "xl/sharedStrings.xml" in x.namelist():
            for si in ET.fromstring(x.read("xl/sharedStrings.xml")).iter(_NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(_NS + "t")))
        cells = {}
        for c in ET.fromstring(x.read(part)).iter(_NS + "c"):
            kind = c.get("t")
            if kind == "inlineStr":
                cells[c.get("r")] = "".join(t.text or "" for t in c.iter(_NS + "t"))
                continue
            v = c.find(_NS + "v")
            if v is None or v.text is None:
                continue
            if kind == "s":
                cells[c.get("r")] = shared[int(v.text)]
            elif kind in ("str", "e", "b"):
                cells[c.get("r")] = v.text
            else:
                cells[c.get("r")] = float(v.text)
    return cells


TENTH = Decimal("0.1")


def amount(v, where: str):
    """Millions of dollars to the tenth, or None for an empty cell.

    The table is in whole millions except the quarter taken from the Bank of France
    document (1966 Q3), which carries one decimal; the stored values carry binary
    rounding residue from the authors' sums (10.300000000000011), so each is read to the
    tenth and a residue larger than that stops the run."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, str):
        raise SystemExit(f"{where}: text {v!r} where a number was expected")
    d = Decimal(repr(v)).quantize(TENTH)
    if abs(Decimal(repr(v)) - d) > Decimal("1e-9"):
        raise SystemExit(f"{where}: {v} is not an amount to the tenth of a million")
    return d.quantize(Decimal(1)) if d == d.to_integral_value() else d


def clean(obj):
    """Amounts for the record: whole ones as integers, the rest as text to the tenth."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else f"{obj:.1f}"
    return obj


def load_bmn():
    """The gold-window table by quarter, with the four classes formed from the country
    columns: Pool members other than the United Kingdom and France (Belgium, Germany,
    Italy, the Netherlands, Switzerland, the membership of the authors' final table), the
    United Kingdom including the Pool, France's own line, and the rest of the total."""
    raw = BMN_ZIP.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != BMN_SHA256:
        raise SystemExit(f"{BMN_ZIP.name}: SHA-256 {got}, recorded {BMN_SHA256}. The file is "
                         f"not the one retrieved; it is reported here rather than read.")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        cells = read_sheet(z.read(BMN_MEMBER), BMN_SHEET)

    def cell(col, r):
        return amount(cells.get(f"{col}{r}"), f"{BMN_SHEET} {col}{r}")

    rows = []
    for r in range(BMN_FIRST_ROW, BMN_LAST_ROW + 1):
        quarter = cells.get(f"A{r}")
        if quarter == BMN_MISSING:
            rows.append({"quarter": quarter, "missing": True})
            continue
        rec = {"quarter": quarter, "missing": False}
        for name, col in {**BMN_COUNTRY, **BMN_TOTALS}.items():
            rec[name] = cell(col, r)
        rec["gp_members"] = sum((rec[m] or 0) for m in GP_MEMBERS)
        rec["uk_incl_pool"] = rec["uk_incl_pool"] or 0
        rec["france"] = rec["france"] or 0
        rec["non_members"] = (rec["foreign_total"] - rec["gp_members"] - rec["uk_incl_pool"]
                              - rec["france"])
        rec["final_as_delivered"] = {k: cell(c, r) for k, c in BMN_FINAL.items()}
        rec["other_as_delivered"] = {k: cell(c, r) for k, c in BMN_OTHER.items()}
        if rec["foreign_total"] + (rec["industry"] or 0) != rec["movement"]:
            raise SystemExit(f"{quarter}: total plus industry is not the movement")
        rows.append(rec)
    want = [f"{y} Q{k}" for y in range(1965, 1969) for k in range(1, 5)]
    if [x["quarter"] for x in rows] != want:
        raise SystemExit(f"{BMN_SHEET}: quarters {[x['quarter'] for x in rows]}")
    return rows


def final_table_differences(bmn):
    """Quarters where the authors' final table departs from the classes formed here, with
    the sum of its four classes against the total."""
    out = []
    for x in bmn:
        if x["missing"]:
            continue
        fin = x["final_as_delivered"]
        diffs = {c: {"final": fin[c], "formed_here": x[c]} for c in CLASSES if fin[c] != x[c]}
        if diffs:
            out.append({"quarter": x["quarter"], "classes": diffs,
                        "final_classes_sum": sum(fin[c] for c in CLASSES),
                        "total": x["foreign_total"]})
    return out


def load_table4():
    rows = list(csv.DictReader(io.StringIO(read_checked(TABLE4, TABLE4_HASH, TABLE4_LEN))))
    year = {r["period"]: int(r["gold_stock_total"]) for r in rows if r["kind"] == "year_end"}
    month = {r["period"]: int(r["gold_stock_total"]) for r in rows if r["kind"] == "month_end"}
    treasury = {r["period"]: int(r["gold_stock_treasury"]) for r in rows}
    return year, month, treasury


def load_table6():
    rows = list(csv.DictReader(io.StringIO(read_checked(TABLE6, TABLE6_HASH, TABLE6_LEN))))
    bad = [(r["period"], r["line"]) for r in rows if r["identity"] not in ("holds", "not_checked")]
    if bad:
        raise SystemExit(f"table 6 rows whose own sums fail: {bad}")
    return {(r["period"], r["line"]): r for r in rows}


def t6_value(t6, period, column, line):
    """A table 6 cell. At a break in coverage the table prints two lines: the first is
    comparable with the preceding date, the second with the following one."""
    r = t6.get((period, line)) or t6.get((period, "single"))
    return int(r[column]) if r[column] != "" else None


def months_between(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb * 12 + mb) - (ya * 12 + ma)


def per_month(change, months) -> str:
    return f"{change / months:.1f}"


def reading_b64_3(bmn, fred, t4_year, t4_month, t4_treasury, t6):
    q = {r["quarter"]: r for r in bmn}

    def seg_t(name, a, b):
        ch = fred[b] - fred[a]
        n = months_between(a, b)
        return {"segment": name, "from": a, "to": b, "months": n, "change": ch,
                "per_month": per_month(ch, n)}

    treasury_basis = [
        seg_t("before the Gold Pool", "1958-12", "1961-10"),
        seg_t("Gold Pool to the letter of the Bundesbank", "1961-10", "1967-03"),
        seg_t("letter to the split", "1967-03", "1968-03"),
        seg_t("split to the arrangement (Treasury column only)", "1968-03", "1969-12"),
        seg_t("arrangement to December 1970 (Treasury column only)", "1969-12", "1970-12"),
    ]
    pre_q = ["1967 Q2", "1967 Q3", "1967 Q4", "1968 Q1"]
    post_q = ["1968 Q2", "1968 Q3", "1968 Q4"]
    early_q = ["1965 Q1", "1965 Q2", "1965 Q3", "1965 Q4", "1966 Q1", "1966 Q2", "1966 Q3",
               "1967 Q1"]
    pre_change = sum(q[x]["movement"] for x in pre_q)
    level_mar68 = t4_year["1967"] + q["1968 Q1"]["movement"]
    s3_change = t4_year["1969"] - level_mar68
    s4_change = t4_month["1971-07"] - t4_year["1969"]
    s4_aug_change = t4_month["1971-08"] - t4_year["1969"]
    imf_s3 = (sum(q[x]["imf"] or 0 for x in post_q)
              + t6_value(t6, "1969", "imf_gold_total", "first")
              - t6_value(t6, "1968", "imf_gold_total", "second"))
    imf_s4 = (t6_value(t6, "1971-07", "imf_gold_total", "single")
              - t6_value(t6, "1969", "imf_gold_total", "second"))
    netted_s3 = sum(i["amount"] for i in ITEMS if i["netted"] and i["window"] == "split to arrangement")
    s3_adj = s3_change - imf_s3 - netted_s3
    s4_adj = s4_change - imf_s4
    total_basis = [
        {"segment": "letter to the split", "from": "end of 1967 Q1", "to": "end of 1968 Q1",
         "months": 12, "change": pre_change, "per_month": per_month(pre_change, 12),
         "basis": "quarterly movement of the total stock, 1967 Q2 to 1968 Q1"},
        {"segment": "split to the arrangement", "from": "end of March 1968", "to": "end of 1969",
         "months": 21, "change": s3_change, "per_month": per_month(s3_change, 21),
         "basis": f"end of 1967 ({t4_year['1967']}) plus the 1968 Q1 movement "
                  f"({q['1968 Q1']['movement']}) to the end of 1969 ({t4_year['1969']})",
         "pieces": {"1968 Q2 to Q4": sum(q[x]["movement"] for x in post_q),
                    "1969": t4_year["1969"] - t4_year["1968"]}},
        {"segment": "arrangement to the last month end with the window open",
         "from": "end of 1969", "to": "end of July 1971", "months": 19, "change": s4_change,
         "per_month": per_month(s4_change, 19),
         "through_august": {"change": s4_aug_change, "months": 20,
                            "per_month": per_month(s4_aug_change, 20)}},
    ]
    netted = [
        {"window": "split to arrangement", "item": "IMF gold transactions: 1968 Q2 to Q4 from "
         "the IMF line of the gold-window table, 1969 from the change in liabilities to the IMF "
         "arising from gold transactions", "amount": imf_s3},
        {"window": "arrangement to close", "item": "IMF gold transactions: change in "
         "liabilities to the IMF arising from gold transactions, end of 1969 to July 1971 "
         "(gold deposits returned and gold investment terminated)", "amount": imf_s4},
    ] + [dict(i) for i in ITEMS]
    pre_rate = pre_change / 12
    rates = {"s3": s3_change / 21, "s4": s4_change / 19,
             "s3_net": s3_adj / 21, "s4_net": s4_adj / 19}
    raw_slower = all(-rates[k] < -pre_rate for k in ("s3", "s4"))
    net_slower = all(-rates[k] < -pre_rate for k in ("s3_net", "s4_net"))
    if raw_slower and net_slower:
        state = "slower"
    elif not raw_slower and not net_slower:
        state = "not_slower"
    else:
        state = "inseparable"
    comparison = {
        "outflow_per_month_before": f"{-pre_rate:.1f}",
        "outflow_per_month_after": {"split to arrangement": f"{-rates['s3']:.1f}",
                                    "arrangement to July 1971": f"{-rates['s4']:.1f}"},
        "outflow_per_month_after_net_of_items": {
            "split to arrangement": f"{-rates['s3_net']:.1f}",
            "arrangement to July 1971": f"{-rates['s4_net']:.1f}"},
        "sign": "positive is an outflow of gold from the United States",
    }

    def class_block(quarters, months):
        out = {}
        for c in CLASSES + ("foreign_total", "movement"):
            s = sum(q[x][c] for x in quarters)
            out[c] = {"sum": s, "per_month": per_month(s, months)}
        return out

    by_class = {
        "1965 Q1 to 1967 Q1 (1966 Q4 missing), 24 months": class_block(early_q, 24),
        "letter to the split, 1967 Q2 to 1968 Q1, 12 months": class_block(pre_q, 12),
        "after the split, 1968 Q2 to Q4, 9 months": class_block(post_q, 9),
    }
    class_steps = {}
    for c in CLASSES:
        before = sum(q[x][c] for x in pre_q) / 12
        after = sum(q[x][c] for x in post_q) / 9
        if -after < -before:
            word = "outflow fell" if after <= 0 else "turned to an inflow"
        else:
            word = "outflow rose"
        class_steps[c] = {"before_per_month": f"{before:.1f}", "after_per_month": f"{after:.1f}",
                          "reading": word}
    quarterly = []
    for r in bmn:
        if r["missing"]:
            quarterly.append({"quarter": r["quarter"], "missing": True})
            continue
        quarterly.append({k: r[k] for k in ("quarter",) + CLASSES + GP_MEMBERS + (
            "imf", "foreign_total", "industry", "movement", "final_as_delivered",
            "other_as_delivered")})
    germany_before = sum(q[x]["germany"] or 0 for x in early_q)
    germany_after = sum(q[x]["germany"] or 0 for x in pre_q + post_q)
    steps = [
        {"date": "1961-11", "event": "Gold Pool founded",
         "treasury_per_month_before": treasury_basis[0]["per_month"],
         "treasury_per_month_after": treasury_basis[1]["per_month"]},
        {"date": "1967-03-30", "event": "letter of the Bundesbank",
         "restricted_line_germany": {"before": germany_before,
                                     "before_quarters": "1965 Q1 to 1967 Q1, eight reported",
                                     "after": germany_after,
                                     "after_quarters": "1967 Q2 to 1968 Q4"},
         "treasury_per_month_before": treasury_basis[1]["per_month"],
         "treasury_per_month_after": treasury_basis[2]["per_month"],
         "uk_incl_pool_before_and_after": {
             "1966 Q1 to 1967 Q1": [q[x]["uk_incl_pool"] for x in ("1966 Q1", "1966 Q2",
                                                                    "1966 Q3", "1967 Q1")],
             "1967 Q2 to 1968 Q1": [q[x]["uk_incl_pool"] for x in pre_q]}},
        {"date": "1968-03-17", "event": "two-tier market", "verdict": state},
    ]
    treasury_transfer = {
        "months": ["1969-12", "1970-01", "1970-02"],
        "treasury_month_end": [t4_treasury["1969-12"], t4_treasury["1970-01"],
                               t4_treasury["1970-02"]],
        "total_month_end": [t4_month["1969-12"], t4_month["1970-01"], t4_month["1970-02"]],
    }
    detail = (
        f"Total basis, outflow per month (positive is gold leaving the United States): "
        f"{-pre_rate:.1f} from the letter to the split (1967 Q2 to 1968 Q1, change "
        f"{pre_change}); {-rates['s3']:.1f} from the split to the arrangement (change "
        f"{s3_change} over 21 months); {-rates['s4']:.1f} from the arrangement to July 1971 "
        f"(change {s4_change} over 19 months; {-s4_aug_change / 20:.1f} through August). Net "
        f"of the IMF's gold transactions ({imf_s3} and {imf_s4}): {-rates['s3_net']:.1f} and "
        f"{-rates['s4_net']:.1f}. By class, before and "
        f"after the split, per month: United Kingdom including the Pool "
        f"{class_steps['uk_incl_pool']['before_per_month']} to "
        f"{class_steps['uk_incl_pool']['after_per_month']}, Pool members other than the United "
        f"Kingdom and France {class_steps['gp_members']['before_per_month']} to "
        f"{class_steps['gp_members']['after_per_month']}, non-members "
        f"{class_steps['non_members']['before_per_month']} to "
        f"{class_steps['non_members']['after_per_month']}, France "
        f"{class_steps['france']['before_per_month']} to "
        f"{class_steps['france']['after_per_month']}; state {state}")
    report = {"final_table_differences": final_table_differences(bmn),
              "treasury_basis": treasury_basis, "total_basis": total_basis,
              "items": netted, "comparison": comparison, "by_class": by_class,
              "class_steps": class_steps, "quarterly_by_class": quarterly,
              "steps_at_the_dated_restrictions": steps,
              "treasury_column_january_1970": treasury_transfer}
    return state, detail, report


def reading_b64_4(fix):
    below_line = FLOOR - TICK

    def stats(rows, idx):
        vals = [(r[0], r[idx]) for r in rows if r[idx] is not None]
        below = [(d, v) for d, v in vals if v < below_line]
        within = [(d, v) for d, v in vals if below_line <= v < FLOOR]
        at = [(d, v) for d, v in vals if v == FLOOR]
        low = min(vals, key=lambda t: (t[1], t[0]))
        return {"fixings": len(vals), "below_35_by_more_than_a_cent": len(below),
                "within_a_cent_below_35": len(within), "at_35_00": len(at),
                "lowest": str(low[1]), "lowest_date": low[0].isoformat(),
                "first_below": below[0][0].isoformat() if below else None,
                "last_below": below[-1][0].isoformat() if below else None}

    before = [r for r in fix if r[0] < ARRANGEMENT]
    after = [r for r in fix if r[0] >= ARRANGEMENT]
    out = {}
    for name, rows in (("before", before), ("after", after)):
        days = [r for r in rows if (r[1] is not None and r[1] < below_line)
                or (r[2] is not None and r[2] < below_line)]
        out[name] = {"window": f"{rows[0][0]} to {rows[-1][0]}", "am": stats(rows, 1),
                     "pm": stats(rows, 2), "days_either_fixing_below": len(days)}
    depth = [{"date": r[0].isoformat(), "am": None if r[1] is None else str(r[1]),
              "pm": None if r[2] is None else str(r[2])}
             for r in after if (r[1] is not None and r[1] < below_line)
             or (r[2] is not None and r[2] < below_line)]
    b = out["before"]["days_either_fixing_below"]
    a = out["after"]["days_either_fixing_below"]
    state = "floor_with_friction" if a > 0 else ("floor" if b > 0 else "not_identified")
    if depth:
        deepest = min(Decimal(x[s]) for x in depth for s in ("am", "pm") if x[s] is not None)
        span = (f"from {depth[0]['date']} to {depth[-1]['date']}, lowest {deepest} "
                f"({(deepest / FLOOR - 1) * 100:.2f} percent)")
    else:
        span = "none"
    detail = (f"days with either fixing below 35 by more than the printed cent: before the "
              f"arrangement {b}, after {a}; after it, morning "
              f"{out['after']['am']['below_35_by_more_than_a_cent']} and afternoon "
              f"{out['after']['pm']['below_35_by_more_than_a_cent']} fixings, {span}; "
              f"lowest fixing before "
              f"the arrangement {out['before']['pm']['lowest']} on {out['before']['pm']['lowest_date']}"
              f"; fixings at exactly 35.00 sit on the resolution floor and are not judged; state {state}")
    return state, detail, {"windows": out, "days_below_after": depth}


def reading_b64_5(fix):
    months = {}
    for d, a, p in fix:
        if p is not None:
            months.setdefault(f"{d:%Y-%m}", []).append(p)
    path = []
    for m in sorted(months):
        vs = months[m]
        mean = sum(vs) / len(vs)
        path.append({"month": m, "pm_fixings": len(vs), "mean": f"{mean:.2f}",
                     "min": str(min(vs)), "max": str(max(vs)),
                     "log_mean_over_35": f"{math.log(float(mean) / 35):.4f}"})
    top = max(path, key=lambda r: Decimal(r["mean"]))
    low = min(path, key=lambda r: Decimal(r["mean"]))
    detail = (f"{len(path)} months, the afternoon fixing's monthly mean against 35: highest "
              f"{top['mean']} in {top['month']} (log {top['log_mean_over_35']}), lowest "
              f"{low['mean']} in {low['month']} (log {low['log_mean_over_35']}); printed only")
    return "printed", detail, {"monthly": path}


def reading_b64_6():
    prices = [Decimal("35")] + [Decimal(s["usd_per_oz"]) for s in OFFICIAL_PRICE]
    steps = []
    for (a, b), s in zip(zip(prices, prices[1:]), OFFICIAL_PRICE):
        steps.append({"step": s["step"], "from": str(a), "to": str(b),
                      "gold_price_change_percent": f"{(b / a - 1) * 100:.2f}",
                      "gold_content_of_the_dollar_change_percent": f"{(a / b - 1) * 100:.2f}"})
    ups = [Decimal(s["to"]) > Decimal(s["from"]) for s in steps]
    state = "devaluation" if all(ups) else ("revaluation" if not any(ups) else "mixed")
    detail = "; ".join(f"{s['step']}: {s['from']} to {s['to']} dollars an ounce, gold content "
                       f"of the dollar {s['gold_content_of_the_dollar_change_percent']} percent"
                       for s in steps) + f"; state {state}"
    return state, detail, {"steps": steps, "texts": OFFICIAL_PRICE}


def reading_b64_7(t4_year, t4_month, t6):
    rows = []
    for y in range(1959, 1970):          # the end of 1970 is the December 1970 month end below
        g = t4_year[str(y)]
        lines = ("first", "second") if (str(y), "first") in t6 else ("single",)
        for ln in lines:
            off = t6_value(t6, str(y), "official_total", ln)
            tot = t6_value(t6, str(y), "total", ln)
            rows.append({"date": f"end of {y}", "line": ln, "gold_total": g,
                         "liabilities_to_foreign_official": off,
                         "gold_over_official": f"{g / off:.3f}",
                         "liabilities_to_all_foreigners": tot,
                         "gold_over_all": f"{g / tot:.3f}"})
    for m in ("1970-07", "1970-08", "1970-09", "1970-10", "1970-11", "1970-12", "1971-01",
              "1971-02", "1971-03", "1971-04", "1971-05", "1971-06", "1971-07"):
        g = t4_month[m]
        lines = ("first", "second") if (m, "first") in t6 else ("single",)
        for ln in lines:
            off = t6_value(t6, m, "official_total", ln)
            tot = t6_value(t6, m, "total", ln)
            rows.append({"date": f"end of {m}", "line": ln, "gold_total": g,
                         "liabilities_to_foreign_official": off,
                         "gold_over_official": f"{g / off:.3f}",
                         "liabilities_to_all_foreigners": tot,
                         "gold_over_all": f"{g / tot:.3f}"})

    def first_below(key):
        for r in rows:
            if r["date"].startswith("end of 19") and len(r["date"]) == 11 and Decimal(r[key]) < 1:
                return r["date"]
        return None

    at = {y: [r for r in rows if r["date"] == f"end of {y}"] for y in ("1961", "1968")}
    detail = (f"gold over liquid liabilities to foreign official institutions, first year end "
              f"below one: {first_below('gold_over_official')}; over liabilities to all "
              f"foreigners: {first_below('gold_over_all')}. End of 1961: "
              + ", ".join(f"{r['gold_over_official']} ({r['line']} line)" for r in at["1961"])
              + "; end of 1968: "
              + ", ".join(f"{r['gold_over_official']} ({r['line']} line)" for r in at["1968"])
              + f"; end of July 1971: {rows[-1]['gold_over_official']}; printed")
    return ("printed" if rows else "missing"), detail, {"ratios": rows}


def placement(r3, r4, r6, r7, fix):
    """B64-8, the two readings written separately (0b), then the cells. Every number in
    the sentences is taken from the readings above."""
    steps = r3["class_steps"]["uk_incl_pool"]
    comp = r3["comparison"]
    after = r4["windows"]["after"]
    below = r4["days_below_after"]
    lowest = min(Decimal(x[s]) for x in below for s in ("am", "pm") if x[s] is not None)
    opened = [(v, d) for d, a, p in fix if d < dt.date(1971, 8, 16) for v in (a, p)
              if v is not None]
    top, top_day = max(opened, key=lambda t: (t[0], t[1]))
    ratios = r7["ratios"]

    def first_year_below(key):
        for r in ratios:
            if len(r["date"]) == 11 and Decimal(r[key]) < 1:
                return r["date"][7:]
        return None

    framework = (
        f"The conversion edge carried the flow of the classes that could still walk it. When "
        f"the private class was cut from it on 1968-03-17, the United Kingdom's line, which "
        f"had carried the Pool's sales in London, went from {steps['before_per_month']} to "
        f"{steps['after_per_month']} a month; the total stock took in gold for the 21 months "
        f"to the South African arrangement and then lost "
        f"{comp['outflow_per_month_after']['arrangement to July 1971']} a month to July 1971, "
        f"against {comp['outflow_per_month_before']} a month in the year before the split, "
        f"while it stood below the dollar claims of foreign official holders from the end of "
        f"{first_year_below('gold_over_official')}. After the window closed the official "
        f"price moved only up: "
        + ", then ".join(f"{s['from']} to {s['to']}" for s in r6["steps"]) + ".")
    rival = (
        f"A single price for gold puts the free price at 35 at all times. With the window "
        f"open it reached {top} on {top_day.isoformat()}, "
        f"{(top / FLOOR - 1) * 100:.1f} percent above 35, and after the arrangement it stood "
        f"below 35 by more than a cent on {after['days_either_fixing_below']} days between "
        f"{below[0]['date']} and {below[-1]['date']}, lowest {lowest}. Triffin's condition says "
        f"the system cannot last once dollar claims exceed the gold stock and names no date; "
        f"it held for claims of all foreigners from the end of "
        f"{first_year_below('gold_over_all')} and for official claims from the end of "
        f"{first_year_below('gold_over_official')}, and the window closed on 1971-08-15.")
    return {
        "framework_against_reality": framework,
        "rival_against_reality": rival,
        "cells": {
            "square against the scalar price field": "B, already counted at earlier stages; "
                                                     "not counted again",
            "why convertibility lasted after Triffin's condition held": (
                "D2: the question sits inside Triffin's argument, which gives no time; the "
                "corollary gives the time as capacity over the flow of the classes that can "
                "still walk the edge"),
            "the floor under the free price in 1970": "A: the historical accounts give the "
                                                      "same answer",
        },
    }


def part_main():
    fix = load_fixing()
    fred = {f"{d:%Y-%m}": v for d, v in load_stock()}
    t4_year, t4_month, t4_treasury = load_table4()
    t6 = load_table6()
    bmn = load_bmn()
    s3, d3, r3 = reading_b64_3(bmn, fred, t4_year, t4_month, t4_treasury, t6)
    s4, d4, r4 = reading_b64_4(fix)
    s5, d5, r5 = reading_b64_5(fix)
    s6, d6, r6 = reading_b64_6()
    s7, d7, r7 = reading_b64_7(t4_year, t4_month, t6)
    place = placement(r3, r4, r6, r7, fix)
    verdict = {"slower": True, "not_slower": False, "inseparable": None,
               "floor": True, "floor_with_friction": True, "not_identified": None,
               "devaluation": True, "revaluation": False, "mixed": None,
               # the two bookkeeping states. This file declared MAPPING_B64_7 and
               # MAPPING_B64_8 and then did not route the two verdicts through
               # them: both were a literal True until 2026-09-13 (rule 11f), so a
               # reading that came back empty would still have been called printed.
               "printed": True, "written": True, "missing": False}
    s8 = "written" if place.get("cells") else "missing"
    for name, state, mapping in (("B64-7", s7, MAPPING_B64_7),
                                 ("B64-8", s8, MAPPING_B64_8)):
        assert state in mapping and state in verdict, \
            f"{name} state {state!r} is outside its own declared mapping"
    criteria = [
        {"name": "B64-3", "kind": "own_reading", "state": s3, "passed": verdict[s3],
         "statement": "after the split of 1968-03-17 the United States' gold stock falls more "
                      "slowly than in the year before it; printed by class where the classes "
                      "are on record",
         "detail": d3, "mapping": MAPPING_B64_3},
        {"name": "B64-4", "kind": "own_reading", "state": s4, "passed": verdict[s4],
         "statement": "the South African arrangement of 1969-12-30 puts a floor under the free "
                      "price at 35",
         "detail": d4, "mapping": MAPPING_B64_4},
        {"name": "B64-5", "kind": "own_reading", "state": s5, "passed": None,
         "statement": "the size of the square: the free price against 35, month by month",
         "detail": d5, "mapping": MAPPING_B64_5},
        {"name": "B64-6", "kind": "own_reading", "state": s6, "passed": verdict[s6],
         "statement": "the forced exit after the window closed runs toward devaluation of the "
                      "dollar against gold",
         "detail": d6, "mapping": MAPPING_B64_6},
        {"name": "B64-7", "kind": "bookkeeping", "state": s7, "passed": verdict[s7],
         "statement": "the capacity side: the gold stock over the dollar claims of foreign "
                      "official holders, year by year, and at the ends of 1961 and 1968",
         "detail": d7, "mapping": MAPPING_B64_7},
        {"name": "B64-8", "kind": "bookkeeping", "state": s8, "passed": verdict[s8],
         "statement": "placement, the two readings written separately",
         "detail": "; ".join(f"{k}: {v}" for k, v in place["cells"].items()),
         "mapping": MAPPING_B64_8},
    ]
    rec = {
        "stage": "B64",
        "config": {
            "fixing_file": FIXING.name, "fixing_hash": FIXING_HASH,
            "stock_file": STOCK.name, "stock_hash": STOCK_HASH,
            "table4_file": TABLE4.name, "table4_hash": TABLE4_HASH,
            "table6_file": TABLE6.name, "table6_hash": TABLE6_HASH,
            "bmn_file": BMN_ZIP.name, "bmn_sha256": BMN_SHA256, "bmn_sheet": BMN_SHEET,
            "bmn_country_columns": BMN_COUNTRY, "bmn_gp_members": list(GP_MEMBERS),
            "bmn_total_columns": BMN_TOTALS, "bmn_final_columns": BMN_FINAL,
            "bmn_other_columns": BMN_OTHER, "bmn_missing_quarter": BMN_MISSING,
            "events": EVENTS, "arrangement": ARRANGEMENT.isoformat(), "floor": str(FLOOR),
            "tick": str(TICK), "items": ITEMS,
        },
        "criteria": criteria,
        "report": {"B64-3": r3, "B64-4": r4, "B64-5": r5, "B64-6": r6, "B64-7": r7,
                   "B64-8": place},
    }
    OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAIN.write_text(json.dumps(clean(rec), indent=1, sort_keys=True, ensure_ascii=False)
                        + "\n", encoding="utf-8", newline="\n")
    print("=" * 78)
    print("B64 main: the readings")
    print("=" * 78)
    for c in criteria:
        tag = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"\n{c['name']} [{c['kind']}]  {tag}  (state {c['state']})\n  {c['statement']}\n"
              f"  {c['detail']}")
        print("  mapping (11c):")
        for k, v in c["mapping"].items():
            print(f"    {k:20s} -> {v}")
    print(f"\n  record: results/{OUT_MAIN.name}")
    return 0 if all(c["passed"] is not False for c in criteria) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["checks", "main"], required=True)
    args = ap.parse_args()
    if args.part == "checks":
        return part_checks()
    return part_main()


if __name__ == "__main__":
    raise SystemExit(main())
