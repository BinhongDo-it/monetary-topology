"""B115: the sorghum deposit of 2018 and its end, read in the weekly flows on the relation it touched.

The source is the Export Sales Reporting and Query System of the USDA Foreign Agricultural Service:
US grain sorghum (commodity 701, marketing year September to August) by destination and week, in
tonnes. A week runs Friday to Thursday and is named by its Thursday, the grid the price branch of
this station already reads on (experiments/b115_sorghum_step.py). Six marketing years are read,
2013/14 to 2018/19.

The steps, counted from three documents. From 2018-04-18 importers of US sorghum paid a 178.6%
deposit (Ministry of Commerce announcement 2018 No. 38); on 2018-05-18 the investigations ended and
the deposits were refunded (No. 44); from 2018-07-06 list one put 25% on the same line (Tariff
Commission announcement [2018] No. 5). The charge in force on e = (US sorghum -> China) is written
by week as omega = ln(1 + rate in force), averaged over the seven days of the week.

Corollary 43.6 on the flows. With only the term of e moved by Delta, the residual on e becomes
r_e + (1 - h_e) Delta: what a deal along e has to pay beyond the gap between its two ends rises
with the deposit and falls with its end. So new business and shipments on e move by at most 0 at
the deposit and by at least 0 at its end, and what used to travel along e lands on the relations
still open, so the other named destinations move by at least 0 at the deposit. The framework fixes
no direction for the move from before the deposit to after its end, for the step of 07-06 (the same
list moved corn and other relations), for the destination reported as unknown (a reporting
category, not a relation), or for the size of anything. Those are printed with their floors and
carry no state.

The query reports eight columns by destination: Gross New Sales, Net Sales, Weekly Exports,
Outstanding Sales, Accumulated Exports, Total Commitment, and for the next marketing year Net Sales
and Outstanding Sales. It has no column of cancellations by destination. R = Gross New Sales - Net
Sales is printed under that name: by the source's definition of Net Sales it nets buy-backs and
cancellations with changes of destination out of and into the row, and it can be negative.

A move is the mean weekly tonnage over one plateau minus the mean over another, in levels (weekly
values are often zero). The plateaus and their four settings are the price branch's; P3 is the four
weeks 07-12 to 08-02. Each move is set against the same move over every window of the same shape on
a Thursday grid that ends on 2018-02-01 and holds none of the seven dated documents. Two grids are
read, from 2016-01-07 and from 2013-09-05. The floor is the larger of the reporting grid and the
median absolute placebo move. A state counts only when all four settings and both floors give it.

    python experiments/b115_sorghum_flows.py --fetch     # fetch what is missing, rebuild the data file
    python experiments/b115_sorghum_flows.py             # print, and write the record
    python experiments/b115_sorghum_flows.py --selftest  # offline, planted faults
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import html as html_lib
import json
import math
import os
import random
import re
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import b115_sorghum_step as S0  # noqa: E402  the plateaus, settings, grid and window machinery of the price branch

DATA = REPO / "data" / "b115_sorghum_esr.json"
CODES = REPO / "data" / "b115_esr_destination_codes.json"
STEPS_FILE = REPO / "data" / "b115_sorghum_fob.json"
RAW = REPO / "data" / "b115" / "raw" / "esr"
MANIFEST = REPO / "data" / "b115" / "raw" / "b115_esr_manifest.json"
OUT = REPO / "results" / "b115_sorghum_flows.json"

BASE = "https://apps.fas.usda.gov/esrqs/ReportsHome.aspx"
FORMAT = "Commodity/WeekEndingDate/ReportingMarketingYearName/Country"
COMMODITY = "GRAIN SORGHUMS - UNMILLED"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research reader, one request per marketing year"
PAUSE_S = 2.0
FIRST_YEARS = (2013, 2014, 2015, 2016, 2017, 2018)
COLUMNS = ("Gross New Sales", "Net Sales", "Weekly Exports", "Outstanding Sales", "Accumulated Exports",
           "Total Commitment", "Net Sales", "Outstanding Sales")
KEYS = ("gross", "net", "exports", "outstanding", "accumulated", "commitment", "next_net", "next_outstanding")
CHINA, UNKNOWN = "5700", "9990"
TOL = 0.15                      # tonnes; the source prints to 0.1
REPORT_STEP = 0.1
P0 = S0.P0
SETTINGS = S0.SETTINGS
DEFAULT = S0.DEFAULT
P3 = ("2018-07-12", 4)
GRIDS = {"from_2016": tuple(S0.GRID), "from_2013": ("2013-09-05", S0.GRID[1])}
TABLE = ("2018-01-04", "2018-08-30")
CHAIN_FROM = "2017-12-28"
MOVES = {"deposit": ("P0", "P1"), "end": ("P1", "P2"), "across": ("P0", "P2"), "list_one": ("P2", "P3")}
DEPOSIT = {"first_day": "2018-04-18", "last_day": "2018-05-17", "rate": 1.786}
LIST_ONE = {"first_day": "2018-07-06", "rate": 0.25}
TWIN_YEARS = (2014, 2015, 2016)
AFTER_YEAR = 2018
SHARE_YEARS = (2014, 2015, 2016, 2017)
SERIES = ("china_exports", "china_gross", "china_net", "china_r", "others_gross", "others_exports", "unknown_net")
LE, GE = "at most 0", "at least 0"
DIRECTIONAL = (
    ("B115-21", "china_exports", "deposit", LE),
    ("B115-22", "china_gross", "deposit", LE),
    ("B115-23", "china_exports", "end", GE),
    ("B115-24", "china_gross", "end", GE),
    ("B115-25", "others_gross", "deposit", GE),
    ("B115-26", "others_exports", "deposit", GE),
)
KNOWN = {"window": ("2018-04-19", "2018-05-31"),
         "destinations": {"5170": "SAUDI ARABIA", "4700": "SPAIN", "5520": "VIETNAM", "5880": "JAPAN"},
         "source": "Hansen, Marchant, Zhang and Grant, Choices 33(2), 2018: cargoes at sea in April were sent on to "
                   "Saudi Arabia, Spain, Vietnam and Japan"}

MATCH, MISS, NOT_READ = "matches", "does not match", "not read"
R_BELOW, R_ABOVE = "below minus its floor", "above its floor"
R_WITHIN, R_NO_FLOOR, R_GAP = "within its floor", "floor not measured", "a plateau with no week"
CELL = (
    (LE, R_BELOW, MATCH), (LE, R_ABOVE, MISS), (GE, R_ABOVE, MATCH), (GE, R_BELOW, MISS),
    ("any", R_WITHIN, NOT_READ), ("any", R_NO_FLOOR, NOT_READ), ("any", R_GAP, NOT_READ),
)
ALL_MATCH, ALL_MISS, ALL_NOT_READ, SPLIT = ("all eight cells match", "all eight cells do not match",
                                            "all eight cells not read", "the eight cells do not give one state")
VERDICT = {ALL_MATCH: True, ALL_MISS: False, ALL_NOT_READ: None, SPLIT: None}
MAPPING = tuple(("cell", f"predicted {p}: {r}" if p != "any" else r, s) for p, r, s in CELL) + tuple(
    ("criterion", k, v) for k, v in VERDICT.items())
assert VERDICT[ALL_NOT_READ] is None and VERDICT[SPLIT] is None
assert all(s == NOT_READ for p, r, s in CELL if p == "any")

day, thursdays, grid_between = S0.day, S0.thursdays, S0.grid_between


# ---------------------------------------------------------------- dates

def first_thursday_of_september(year: int) -> date:
    d = date(year, 9, 1)
    return d + timedelta(days=(3 - d.weekday()) % 7)


def year_span(first_year: int) -> tuple[str, str]:
    lo = first_thursday_of_september(first_year)
    hi = first_thursday_of_september(first_year + 1) - timedelta(days=7)
    return lo.isoformat(), hi.isoformat()


def us_date(iso: str, pad: bool = True) -> str:
    d = day(iso)
    return f"{d.month:02d}/{d.day:02d}/{d.year}" if pad else f"{d.month}/{d.day}/{d.year}"


def shift_to_year(week: str, first_year: int) -> str:
    """The Thursday with the same ordinal in the marketing year that starts in first_year."""
    d = day(week)
    own = d.year if d >= first_thursday_of_september(d.year) else d.year - 1
    k = (d - first_thursday_of_september(own)).days // 7
    return (first_thursday_of_september(first_year) + timedelta(days=7 * k)).isoformat()


def omega(week: str) -> dict:
    days = [day(week) - timedelta(days=k) for k in range(7)]
    dep = sum(1 for d in days if day(DEPOSIT["first_day"]) <= d <= day(DEPOSIT["last_day"]))
    lst = sum(1 for d in days if d >= day(LIST_ONE["first_day"]))
    w = (dep * math.log(1 + DEPOSIT["rate"]) + lst * math.log(1 + LIST_ONE["rate"])) / 7
    return {"deposit_days": dep, "list_one_days": lst, "omega": w}


# ---------------------------------------------------------------- the source: fetch and parse

TOKEN = re.compile(r'<div style="width:[\d.]+mm;min-width: [\d.]+mm;">(.*?)</div>', re.S)
WEEK = re.compile(r"^(\d\d)/(\d\d)/(\d{4})\(wk(\d+)\)$")
MY = re.compile(r"^MY -\s+Sep (\d{4})/Aug (\d{4})$")
NUM = re.compile(r"^-?[\d,]+\.\d$")
DEST = re.compile(r"^(.*?)\s*\((\d{4})\)$")
SPAN_LINE = re.compile(r"^From: (\d+)/(\d+)/(\d{4}) To: (\d+)/(\d+)/(\d{4})$")


def url_for(lo: str, hi: str, codes: list[str]) -> str:
    return (f"{BASE}?RN=ESRQR&weekStartDate={us_date(lo)}&weekEndDate={us_date(hi)}&commodityId=13"
            f"&destinationCode={','.join(codes)}&format={FORMAT}")


def parse_report(text: str) -> dict:
    """One report page -> the header and every row. Raises on anything it does not recognise."""
    tokens = [html_lib.unescape(t).strip() for t in TOKEN.findall(text)]
    pages = [int(x) for x in re.findall(r'"TotalPages":(\d+)', text)]
    out = {"complete": text.rstrip().endswith("</html>"), "total_pages": pages[0] if pages else None,
           "header_from": None, "header_to": None, "commodities": [], "rows": [], "totals": []}
    week = my = None
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        m = SPAN_LINE.match(t)
        if m:
            a = [int(x) for x in m.groups()]
            out["header_from"], out["header_to"] = date(a[2], a[0], a[1]).isoformat(), date(a[5], a[3], a[4]).isoformat()
            i += 1
            continue
        m = WEEK.match(t)
        if m:
            week, my = date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat(), None
            i += 1
            continue
        m = MY.match(t)
        if m:
            if week is None:
                raise ValueError("a marketing year before any week")
            if int(m.group(2)) != int(m.group(1)) + 1:
                raise ValueError(f"marketing year {t!r}")
            my = f"{m.group(1)}/{m.group(2)[2:]}"
            head = tuple(tokens[i + 1:i + 11])
            if head != ("Current Marketing Year", "Next Marketing Year") + COLUMNS:
                raise ValueError(f"columns under {week} {my}: {head}")
            i += 11
            continue
        if t in ("Export Sales Query System", "Export Sales Data by Commodity/Date/Country", ""):
            i += 1
            continue
        nums = tokens[i + 1:i + 9]
        if len(nums) == 8 and all(NUM.match(x) for x in nums):
            if week is None or my is None:
                raise ValueError(f"a row before its week and marketing year: {t!r}")
            vals = [float(x.replace(",", "")) for x in nums]
            if t == "Total":
                out["totals"].append([week, my] + vals)
            else:
                d = DEST.match(t)
                if not d:
                    raise ValueError(f"not a destination: {t!r}")
                out["rows"].append([week, my, d.group(2), d.group(1).strip()] + vals)
            i += 9
            continue
        if week is None and not NUM.match(t):
            out["commodities"].append(t)
            i += 1
            continue
        raise ValueError(f"token {i} not recognised: {t!r}")
    return out


def check_file(p: dict, lo: str, hi: str) -> list[str]:
    bad = []
    if not p["complete"]:
        bad.append("does not end with </html>")
    if p["total_pages"] != 1:
        bad.append(f"TotalPages {p['total_pages']}")
    if (p["header_from"], p["header_to"]) != (lo, hi):
        bad.append(f"header {p['header_from']}..{p['header_to']} against request {lo}..{hi}")
    if p["commodities"] != [COMMODITY]:
        bad.append(f"commodity {p['commodities']}")
    weeks = sorted({r[0] for r in p["totals"]})
    if weeks != grid_between(lo, hi):
        missing = [w for w in grid_between(lo, hi) if w not in weeks]
        bad.append(f"{len(weeks)} weeks with a Total row against {len(grid_between(lo, hi))} Thursdays; missing {missing[:5]}")
    return bad


def file_block(name: str, url: str, raw: bytes, p: dict, lo: str, hi: str) -> dict:
    return {"file": name, "url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "request_from": lo, "request_to": hi, "header_from": p["header_from"], "header_to": p["header_to"],
            "total_pages": p["total_pages"], "complete": p["complete"], "commodities": p["commodities"],
            "weeks": len({r[0] for r in p["totals"]}), "rows": len(p["rows"])}


def fetch() -> int:
    import urllib.request
    codes = json.loads(CODES.read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"files": {}}
    blocks, rows, totals, failed = [], [], [], []
    for y in FIRST_YEARS:
        lo, hi = year_span(y)
        name = f"esr_sorghum_{y}_{(y + 1) % 100:02d}.html"
        path, url = RAW / name, url_for(lo, hi, codes["destination_codes"])
        have = manifest["files"].get(name)
        raw = path.read_bytes() if path.exists() else None
        ok = False
        if raw is not None and have and have.get("sha256") == hashlib.sha256(raw).hexdigest():
            try:
                p = parse_report(raw.decode("utf-8"))
                ok = not check_file(p, lo, hi)
            except ValueError:
                ok = False
        if not ok:
            t0 = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            raw = urllib.request.urlopen(req, timeout=180).read()
            secs = time.time() - t0
            try:
                p = parse_report(raw.decode("utf-8"))
                bad = check_file(p, lo, hi)
            except ValueError as e:
                p, bad = None, [f"parse: {e}"]
            if bad:
                (RAW / (name + ".rejected")).write_bytes(raw)
                print(f"{name}: {len(raw)} bytes in {secs:.1f} s, rejected: {'; '.join(bad)}")
                failed.append(name)
                time.sleep(PAUSE_S)
                continue
            tmp = RAW / (name + ".part")
            tmp.write_bytes(raw)
            os.replace(tmp, path)
            manifest["files"][name] = {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                                       "retrieved": date.today().isoformat()}
            MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(f"{name}: fetched {len(raw)} bytes in {secs:.1f} s")
            time.sleep(PAUSE_S)
        else:
            print(f"{name}: on disk, hash and checks hold")
        blocks.append(file_block(name, url, raw, p, lo, hi))
        rows += p["rows"]
        totals += p["totals"]
    if failed:
        print(f"not rebuilt: {failed}")
        return 1
    write_data(blocks, rows, totals, codes)
    return 0


def data_text(blocks: list[dict], rows: list, totals: list, codes: dict) -> str:
    rows = sorted(rows, key=lambda r: (r[0], r[1], r[2]))
    totals = sorted(totals, key=lambda r: (r[0], r[1]))

    def line(r, k):
        return json.dumps(r[:k], ensure_ascii=False)[:-1] + "".join(f", {v:.1f}" for v in r[k:]) + "]"
    head = {
        "what": "US grain sorghum weekly export sales by destination, FAS Export Sales Reporting and Query System",
        "unit": "tonnes; weeks run Friday to Thursday and are named by the Thursday; marketing year September to August",
        "commodity": {"code": codes["commodity_code"], "id": codes["commodity_id"], "name": COMMODITY},
        "columns": list(KEYS),
        "columns_at_source": list(COLUMNS[:6]) + ["Next Marketing Year " + c for c in COLUMNS[6:]],
        "row": "week, marketing year, destination code, destination, then the eight columns",
        "total_row": "week, marketing year, then the eight columns of the report's Total row",
        "absent_rows": "a destination with no row in a week has no activity and no balance there; read as zeros",
        "destination_codes": {"n": len(codes["destination_codes"]), "file": "data/b115_esr_destination_codes.json"},
        "files": blocks,
    }
    text = json.dumps(head, indent=1, sort_keys=True, ensure_ascii=False)[:-2]
    text += ',\n "rows": [\n  ' + ",\n  ".join(line(r, 4) for r in rows) + "\n ]"
    text += ',\n "totals": [\n  ' + ",\n  ".join(line(r, 2) for r in totals) + "\n ]\n}\n"
    return text


def write_data(blocks: list[dict], rows: list, totals: list, codes: dict) -> None:
    text = data_text(blocks, rows, totals, codes)
    json.loads(text)
    DATA.write_text(text, encoding="utf-8", newline="\n")
    print(f"data {DATA.relative_to(REPO)}: {len(rows)} rows, {len(totals)} Total rows")


# ---------------------------------------------------------------- series

def build(data: dict) -> dict:
    """Weekly series over every Thursday that has a Total row; a destination without a row is zero."""
    weeks = sorted({r[0] for r in data["totals"]})
    wset = set(weeks)
    zero = lambda: collections.defaultdict(float)  # noqa: E731
    s = {k: zero() for k in SERIES + ("china_outstanding", "china_next_net", "china_next_outstanding",
                                      "unknown_outstanding", "total_exports", "total_gross", "named_exports", "named_gross")}
    present = collections.defaultdict(set)
    for r in data["rows"]:
        w, code = r[0], r[2]
        v = dict(zip(KEYS, r[4:]))
        present[code].add(w)
        if code == CHINA:
            s["china_exports"][w] += v["exports"]
            s["china_gross"][w] += v["gross"]
            s["china_net"][w] += v["net"]
            s["china_r"][w] += v["gross"] - v["net"]
            s["china_outstanding"][w] += v["outstanding"]
            s["china_next_net"][w] += v["next_net"]
            s["china_next_outstanding"][w] += v["next_outstanding"]
        elif code == UNKNOWN:
            s["unknown_net"][w] += v["net"]
            s["unknown_outstanding"][w] += v["outstanding"]
        else:
            s["others_gross"][w] += v["gross"]
            s["others_exports"][w] += v["exports"]
        s["named_exports"][w] += v["exports"]
        s["named_gross"][w] += v["gross"]
    for r in data["totals"]:
        v = dict(zip(KEYS, r[2:]))
        s["total_exports"][r[0]] += v["exports"]
        s["total_gross"][r[0]] += v["gross"]
    series = {k: {w: float(d.get(w, 0.0)) for w in weeks} for k, d in s.items()}
    zeros = {code: sum(1 for w in weeks if w not in present[code]) for code in (CHINA, UNKNOWN)}
    return {"weeks": weeks, "weekset": wset, "series": series, "weeks_without_a_row": zeros}


def identities(data: dict) -> dict:
    row_bad, total_bad, chain_bad, chain_other = [], [], [], 0
    sums = collections.defaultdict(lambda: [0.0] * 8)
    by = collections.defaultdict(dict)
    for r in data["rows"]:
        v = dict(zip(KEYS, r[4:]))
        if abs(v["commitment"] - v["outstanding"] - v["accumulated"]) > TOL:
            row_bad.append(f"{r[0]} {r[1]} {r[3]}: {v['commitment']:.1f} against {v['outstanding'] + v['accumulated']:.1f}")
        for k in range(8):
            sums[(r[0], r[1])][k] += r[4 + k]
        by[(r[2], r[1])][r[0]] = v
    tot_keys = set()
    for r in data["totals"]:
        tot_keys.add((r[0], r[1]))
        for k in range(8):
            if abs(r[2 + k] - sums[(r[0], r[1])][k]) > TOL:
                total_bad.append(f"{r[0]} {r[1]} {COLUMNS[k]}: Total {r[2 + k]:.1f} against {sums[(r[0], r[1])][k]:.1f}")
    total_bad += [f"{w} {m}: rows without a Total row" for (w, m) in sorted(set(sums) - tot_keys)]
    checked = 0
    for (code, my), d in sorted(by.items()):
        ws = sorted(d)
        for a, b in zip(ws, ws[1:]):
            if (day(b) - day(a)).days != 7:
                continue
            e1 = d[b]["outstanding"] - (d[a]["outstanding"] + d[b]["net"] - d[b]["exports"])
            e2 = d[b]["accumulated"] - (d[a]["accumulated"] + d[b]["exports"])
            inside = code == CHINA and CHAIN_FROM <= a and b <= TABLE[1]
            checked += inside
            if abs(e1) > TOL or abs(e2) > TOL:
                if inside:
                    chain_bad.append(f"{b} {my}: outstanding off by {e1:+.1f}, accumulated off by {e2:+.1f}")
                else:
                    chain_other += 1
    china_weeks = {w for (code, my), d in by.items() if code == CHINA for w in d}
    need = grid_between(CHAIN_FROM, TABLE[1])
    chain_bad += [f"{w}: China has no row" for w in need if w not in china_weeks]
    return {"rows": len(data["rows"]), "row_identity_breaks": row_bad, "total_row_breaks": total_bad,
            "china_chain_links_checked": checked, "china_chain_breaks": chain_bad,
            "chain_breaks_elsewhere": chain_other, "tolerance": TOL}


# ---------------------------------------------------------------- moves, floors, states

def as_path(series: dict) -> dict:
    return {w: {"tau": v, "segment": 0} for w, v in series.items()}


def plateau_weeks(st: dict) -> dict:
    return {"P0": thursdays(*P0), "P1": thursdays(*st["P1"]), "P2": thursdays(*st["P2"]), "P3": thursdays(*P3)}


def observed(path: dict, pre_w: list[str], post_w: list[str]) -> dict | None:
    a = [path[w]["tau"] for w in pre_w if w in path]
    b = [path[w]["tau"] for w in post_w if w in path]
    if len(a) != len(pre_w) or len(b) != len(post_w):
        return None
    return {"move": statistics.fmean(b) - statistics.fmean(a), "pre_mean": statistics.fmean(a),
            "post_mean": statistics.fmean(b), "pre_n": len(a), "post_n": len(b)}


def read_state(pred: str, obs: dict | None, floor: float | None) -> tuple[str, str]:
    if obs is None:
        return NOT_READ, R_GAP
    if floor is None:
        return NOT_READ, R_NO_FLOOR
    m = obs["move"]
    reason = R_BELOW if m < -floor else R_ABOVE if m > floor else R_WITHIN
    for p, r, s in CELL:
        if r == reason and p in (pred, "any"):
            return s, reason
    raise KeyError((pred, reason))


def criterion_state(cells: dict) -> str:
    kinds = {c[0] for c in cells.values()}
    if kinds == {MATCH}:
        return ALL_MATCH
    if kinds == {MISS}:
        return ALL_MISS
    if kinds == {NOT_READ}:
        return ALL_NOT_READ
    return SPLIT


def run(data: dict, steps: list[str], settings: dict = SETTINGS, grids: dict = GRIDS, drop_spanning: bool = True) -> dict:
    b = build(data)
    series, weeks = b["series"], b["weeks"]
    pred = {(s, mv): (name, p) for name, s, mv, p in DIRECTIONAL}
    moves, spanning, empty = {}, [], []
    for sname in SERIES:
        path = as_path(series[sname])
        moves[sname] = {}
        for mv, (pa, pb) in MOVES.items():
            per = {}
            for k, st in settings.items():
                pw = plateau_weeks(st)
                pre_w, post_w = pw[pa], pw[pb]
                gap = S0.gap_weeks(pre_w, post_w)
                obs = observed(path, pre_w, post_w)
                step = REPORT_STEP / len(pre_w) + REPORT_STEP / len(post_w)
                cell = {"pre": [pre_w[0], pre_w[-1]], "post": [post_w[0], post_w[-1]], "gap_weeks": gap,
                        "observed": obs, "floors": {}}
                for gname, (glo, ghi) in grids.items():
                    grid = [w for w in grid_between(glo, ghi)]
                    rows, stepped, thin = S0.placebo(path, grid, len(pre_w), gap, len(post_w), steps if drop_spanning else [])
                    fl = S0.floor_of(obs and obs["move"], rows, step)
                    fl["spanning_a_date_dropped"], fl["without_a_week"] = stepped, thin
                    kept_spanning = sum(1 for r in rows if any(r["span"][0] <= t <= r["span"][1] for t in steps))
                    fl["kept_spanning_a_date"] = kept_spanning
                    if kept_spanning:
                        spanning.append(f"{sname} {mv} {k} {gname}: {kept_spanning} windows span a dated document")
                    if not rows:
                        empty.append(f"{sname} {mv} {k} {gname}: no placebo window")
                    if (sname, mv) in pred:
                        fl["state"] = list(read_state(pred[(sname, mv)][1], obs, fl.get("floor")))
                    cell["floors"][gname] = fl
                cell["twins"] = {}
                for y in TWIN_YEARS + (AFTER_YEAR,):
                    o2 = observed(path, [shift_to_year(w, y) for w in pre_w], [shift_to_year(w, y) for w in post_w])
                    cell["twins"][f"{y}/{(y + 1) % 100:02d}"] = o2
                per[k] = cell
            moves[sname][mv] = per
    directional = {}
    for name, sname, mv, p in DIRECTIONAL:
        cells = {f"{k}/{g}": tuple(moves[sname][mv][k]["floors"][g]["state"]) for k in settings for g in grids}
        directional[name] = {"series": sname, "move": mv, "predicted": p, "cells": {c: list(v) for c, v in cells.items()},
                             "state": criterion_state(cells)}
    printed = [{"series": s, "move": mv} for s in SERIES for mv in MOVES if (s, mv) not in pred]
    plateau_means = {}
    for k, st in settings.items():
        pw = plateau_weeks(st)
        plateau_means[k] = {pn: {s: (statistics.fmean(series[s][w] for w in ws) if all(w in series[s] for w in ws) else None)
                                 for s in SERIES + ("china_outstanding", "unknown_outstanding")} for pn, ws in pw.items()}
    need = sorted({w for st in settings.values() for ws in plateau_weeks(st).values() for w in ws})
    span = grid_between(year_span(FIRST_YEARS[0])[0], year_span(FIRST_YEARS[-1])[1])
    return {"steps": steps, "grids": {g: list(v) for g, v in grids.items()},
            "files": data.get("files", []),
            "coverage": {"thursdays": len(span), "thursdays_without_a_total_row": [w for w in span if w not in b["weekset"]],
                         "plateau_weeks": need, "plateau_weeks_absent": [w for w in need if w not in b["weekset"]],
                         "weeks_without_a_row": b["weeks_without_a_row"]},
            "identities": identities(data),
            "placebo": {"kept_spanning_a_date": spanning, "without_any_window": empty},
            "moves": moves, "directional": directional, "printed_moves": printed, "plateau_means": plateau_means,
            "table": table(data, b), "known_answer": known_answer(data),
            "beside": beside(data, b, moves, steps if drop_spanning else [], settings, grids)}


def table(data: dict, b: dict) -> dict:
    s = b["series"]
    weeks = [w for w in grid_between(*TABLE)]
    by = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    china = collections.defaultdict(lambda: [0.0] * 8)
    for r in data["rows"]:
        if r[2] == CHINA:
            for k in range(8):
                china[r[0]][k] += r[4 + k]
        elif r[2] != UNKNOWN and TABLE[0] <= r[0] <= TABLE[1] and (r[4] or r[6]):
            by[r[0]][r[3]][0] += r[4]
            by[r[0]][r[3]][1] += r[6]
    rows = []
    for w in weeks:
        if w not in b["weekset"]:
            continue
        te, tg = s["total_exports"][w], s["total_gross"][w]
        rows.append({"week": w, **omega(w), "china": dict(zip(KEYS, china[w])), "china_r": s["china_r"][w],
                     "unknown_net": s["unknown_net"][w], "unknown_outstanding": s["unknown_outstanding"][w],
                     "others_gross": s["others_gross"][w], "others_exports": s["others_exports"][w],
                     "others_by_destination": {n: {"gross": v[0], "exports": v[1]} for n, v in sorted(by[w].items())},
                     "total_gross": tg, "total_exports": te,
                     "china_share_of_exports": s["china_exports"][w] / te if te else None,
                     "china_share_of_gross": s["china_gross"][w] / tg if tg else None})
    same = {}
    for y in (2016, AFTER_YEAR):
        same[f"{y}/{(y + 1) % 100:02d}"] = [{"week": shift_to_year(w, y), "same_ordinal_as": w,
                                            "china": dict(zip(KEYS, china[shift_to_year(w, y)]))}
                                           for w in weeks if shift_to_year(w, y) in b["weekset"]]
    shares = {}
    for y in SHARE_YEARS:
        ws = [w for w in b["weeks"] if w[:4] == str(y)]
        te = sum(s["total_exports"][w] for w in ws)
        shares[str(y)] = {"weeks": len(ws), "china_exports": sum(s["china_exports"][w] for w in ws), "total_exports": te,
                          "share": sum(s["china_exports"][w] for w in ws) / te if te else None}
    path = [{"week": w, "china_outstanding": s["china_outstanding"][w], "china_net": s["china_net"][w],
             "china_exports": s["china_exports"][w], "unknown_outstanding": s["unknown_outstanding"][w]}
            for w in weeks if w in b["weekset"]]
    return {"expected_weeks": len(weeks), "weeks": rows, "same_ordinal": same, "calendar_year_share": shares,
            "outstanding_path": path}


def known_answer(data: dict) -> dict:
    lo, hi = KNOWN["window"]
    out = {}
    for code, name in KNOWN["destinations"].items():
        g = sum(r[4] for r in data["rows"] if r[2] == code and lo <= r[0] <= hi)
        n = sum(r[5] for r in data["rows"] if r[2] == code and lo <= r[0] <= hi)
        e = sum(r[6] for r in data["rows"] if r[2] == code and lo <= r[0] <= hi)
        names = sorted({r[3] for r in data["rows"] if r[2] == code})
        out[name] = {"code": code, "name_at_source": names, "gross": g, "net": n, "exports": e, "positive": g > 0 or e > 0}
    return {"window": [lo, hi], "destinations": out, "missing": [n for n, v in out.items() if not v["positive"]]}


def beside(data: dict, b: dict, moves: dict, steps: list[str], settings: dict, grids: dict) -> dict:
    """Printed beside the readings and carrying no state: the states each cell of a criterion can reach, the same weeks
    of earlier years set against each move, and the tonnage sold and shipped in one row and week."""
    sign = {LE: -1.0, GE: 1.0}

    def ratio(v):
        return v["post_mean"] / v["pre_mean"] if v and v["pre_mean"] else None

    reach, twins = {}, {}
    for name, sname, mv, p in DIRECTIONAL:
        reach[name], twins[name] = {}, {}
        for k, c in moves[sname][mv].items():
            ob = c["observed"]
            tw = {y: v for y, v in c["twins"].items() if v is not None and int(y[:4]) in TWIN_YEARS}
            far = max(sorted(tw), key=lambda y: sign[p] * tw[y]["move"]) if tw else None
            rest = None if ob is None or far is None else ob["move"] - tw[far]["move"]
            twins[name][k] = {"move": ob and ob["move"], "post_over_pre": ratio(ob),
                              "twin_furthest_the_predicted_way": far, "move_less_that_twin": rest,
                              "twins_post_over_pre": {y: ratio(v) for y, v in tw.items()}, "by_grid": {}}
            for g, fl in c["floors"].items():
                f = fl.get("floor")
                # gross new sales and weekly exports are never below zero, so a move is at least minus the mean before it
                can_fall = ob is not None and f is not None and ob["pre_mean"] > f
                if ob is None or f is None:
                    states = [NOT_READ]
                else:
                    states = [NOT_READ, MATCH if p == GE else MISS] + ([MISS if p == GE else MATCH] if can_fall else [])
                reach[name][f"{k}/{g}"] = {"mean_before": ob and ob["pre_mean"], "lowest_possible_move": ob and -ob["pre_mean"],
                                           "floor": f, "a_fall_beyond_the_floor_possible": can_fall,
                                           "states_possible": sorted(states)}
                twins[name][k]["by_grid"][g] = {
                    "floor": f,
                    "twins_beyond_the_floor_the_predicted_way": None if f is None else sorted(
                        y for y, v in tw.items() if sign[p] * v["move"] > f),
                    "move_less_that_twin_over_floor": None if rest is None or not f else sign[p] * rest / f}
    same = {}
    path = as_path(b["series"]["others_exports"])
    for k, st in settings.items():
        pw = plateau_weeks(st)
        ws = set(pw["P1"])
        cell = collections.defaultdict(lambda: [0.0, 0.0])
        for r in data["rows"]:
            if r[0] in ws and r[2] not in (CHINA, UNKNOWN):
                cell[(r[0], r[3])][0] += r[4]
                cell[(r[0], r[3])][1] += r[6]
        rows = [{"week": w, "destination": n, "tonnes": v[0]} for (w, n), v in sorted(cell.items())
                if v[0] > 0 and abs(v[0] - v[1]) <= TOL]
        both = sum(r["tonnes"] for r in rows)
        gross, exports = sum(v[0] for v in cell.values()), sum(v[1] for v in cell.values())
        c = moves["others_exports"]["deposit"][k]
        ob = c["observed"]
        less = None if ob is None else ob["move"] - both / len(pw["P1"])
        by_grid = {}
        for g, (glo, ghi) in grids.items():
            prow, _, _ = S0.placebo(path, list(grid_between(glo, ghi)), len(pw["P0"]), c["gap_weeks"], len(pw["P1"]), steps)
            by_grid[g] = {"windows": len(prow), "floor": c["floors"][g].get("floor"),
                          "placebo_at_least_as_large": None if less is None else sum(1 for r in prow if abs(r["move"]) >= abs(less))}
        same[k] = {"weeks": [pw["P1"][0], pw["P1"][-1]], "rows": rows, "tonnes_in_those_rows": both,
                   "others_gross": gross, "others_exports": exports,
                   "share_of_exports": both / exports if exports else None,
                   "share_of_gross": both / gross if gross else None,
                   "sold_and_shipped_row_by_row": sum(min(v) for v in cell.values()),
                   "others_exports_move_without_those_rows": less, "by_grid": by_grid}
    return {"least_value_in_a_row": {"gross": min((r[4] for r in data["rows"]), default=None),
                                     "exports": min((r[6] for r in data["rows"]), default=None)},
            "states_possible": reach, "twins": twins, "same_row_and_week": same}


# ---------------------------------------------------------------- criteria

def t0(x) -> str:
    return "n/a" if x is None else f"{x:+,.0f}"


def criteria_for(o: dict) -> list[dict]:
    cov, idn = o["coverage"], o["identities"]
    b17 = []
    if len(o["files"]) != len(FIRST_YEARS):
        b17.append(f"{len(o['files'])} files against {len(FIRST_YEARS)}")
    for f in o["files"]:
        if f.get("total_pages") != 1:
            b17.append(f"{f['file']}: TotalPages {f.get('total_pages')}")
        if not f.get("complete"):
            b17.append(f"{f['file']}: cut short")
        if (f.get("header_from"), f.get("header_to")) != (f.get("request_from"), f.get("request_to")):
            b17.append(f"{f['file']}: header {f.get('header_from')}..{f.get('header_to')} against request "
                       f"{f.get('request_from')}..{f.get('request_to')}")
        if f.get("commodities") != [COMMODITY]:
            b17.append(f"{f['file']}: commodity {f.get('commodities')}")
    b17 += [f"no Total row for {w}" for w in cov["thursdays_without_a_total_row"][:8]]
    b17 += [f"plateau week {w} absent" for w in cov["plateau_weeks_absent"]]
    b18 = idn["row_identity_breaks"] + idn["total_row_breaks"] + idn["china_chain_breaks"]
    if not idn["rows"] or not idn["china_chain_links_checked"]:
        b18.append("nothing to check")
    b19 = o["placebo"]["kept_spanning_a_date"] + o["placebo"]["without_any_window"]
    tb = o["table"]
    b20 = []
    if len(tb["weeks"]) != tb["expected_weeks"]:
        b20.append(f"{len(tb['weeks'])} weeks against {tb['expected_weeks']}")
    if not any(r["total_exports"] > 0 for r in tb["weeks"]):
        b20.append("no exports in the table")
    if not all(tb["same_ordinal"].get(k) for k in tb["same_ordinal"]) or not tb["calendar_year_share"]:
        b20.append("a comparison year is empty")
    dflt = o["moves"]["china_exports"]["deposit"][DEFAULT]
    out = [
        {"name": "B115-17", "kind": "instrument", "passed": not b17,
         "statement": "each of the six files is one page, its header dates are the dates asked for and its commodity is "
                      "grain sorghum; every Thursday from 2013-09-05 to 2019-08-29 has a Total row; every plateau week of "
                      "every setting is there",
         "detail": f"{len(o['files'])} files, {cov['thursdays'] - len(cov['thursdays_without_a_total_row'])} of "
                   f"{cov['thursdays']} Thursdays, {len(cov['plateau_weeks'])} plateau weeks"
                   + (": " + "; ".join(b17[:6]) if b17 else "")},
        {"name": "B115-18", "kind": "instrument", "passed": not b18,
         "statement": "in every row Total Commitment is Outstanding Sales plus Accumulated Exports; in every week and "
                      "marketing year the Total row is the sum of the destinations in all eight columns; for China from "
                      "2018-01-04 to 2018-08-30 outstanding and accumulated chain week to week through net sales and "
                      f"exports, all within {TOL} t",
         "detail": f"{idn['rows']} rows, {idn['china_chain_links_checked']} China links; chain breaks elsewhere, printed "
                   f"and not judged: {idn['chain_breaks_elsewhere']}" + (": " + "; ".join(b18[:6]) if b18 else "")},
        {"name": "B115-19", "kind": "instrument", "passed": not b19,
         "statement": "no placebo window kept spans a dated sorghum document, and every series, move, setting and grid "
                      "has placebo windows",
         "detail": "china_exports, deposit, setting A: " + ", ".join(
             f"{g} {fl.get('windows')} kept ({fl.get('independent')} apart)" for g, fl in dflt["floors"].items())
                   + (": " + "; ".join(b19[:6]) if b19 else "")},
        {"name": "B115-20", "kind": "own_reading", "passed": not b20,
         "statement": "printed: the weekly table 2018-01-04 to 2018-08-30 with the charge in force, China's eight "
                      "columns and R, the unknown destination, the other named destinations one by one, the Total row and "
                      "China's shares; China's columns over the same weeks of 2016/17 and 2018/19; China's share of "
                      "exports by calendar year 2014 to 2017",
         "detail": f"{len(tb['weeks'])} weeks; calendar-year share of exports "
                   + ", ".join(f"{y} {v['share']:.3f}" if v["share"] is not None else f"{y} n/a"
                               for y, v in tb["calendar_year_share"].items())
                   + (": " + "; ".join(b20) if b20 else "")},
    ]
    words = {"B115-21": "the deposit: China's weekly exports moved by at most 0",
             "B115-22": "the deposit: China's gross new sales moved by at most 0",
             "B115-23": "the end: China's weekly exports moved by at least 0 (the joint statement of 05-19 falls in the "
                        "same step)",
             "B115-24": "the end: China's gross new sales moved by at least 0 (the joint statement of 05-19 falls in the "
                        "same step)",
             "B115-25": "the deposit: gross new sales to the other named destinations together moved by at least 0",
             "B115-26": "the deposit: weekly exports to the other named destinations together moved by at least 0"}
    for name, sname, mv, p in DIRECTIONAL:
        d = o["directional"][name]
        per = o["moves"][sname][mv]
        out.append({"name": name, "kind": "own_reading", "passed": VERDICT[d["state"]], "statement": words[name],
                    "detail": f"{d['state']}; " + "; ".join(
                        f"{k}: {t0((c['observed'] or {}).get('move'))} t/week, " + ", ".join(
                            f"{g} floor {t0(fl.get('floor'))} ({fl.get('placebo_at_least_as_large')} of "
                            f"{fl.get('windows')} as large) {fl['state'][0]}" for g, fl in c["floors"].items())
                        for k, c in per.items())})
    b27 = []
    named = {(d["series"], d["move"]) for d in o["directional"].values()}
    if not o["printed_moves"]:
        b27.append("no printed moves")
    for pm in o["printed_moves"]:
        if (pm["series"], pm["move"]) in named:
            b27.append(f"{pm['series']} {pm['move']} is a criterion as well")
        if "verdict" in pm or "state" in pm:
            b27.append(f"{pm['series']} {pm['move']} carries a verdict")
        for k, c in o["moves"][pm["series"]][pm["move"]].items():
            for g, fl in c["floors"].items():
                if fl.get("floor") is None:
                    b27.append(f"{pm['series']} {pm['move']} {k} {g}: no floor")
                if "state" in fl:
                    b27.append(f"{pm['series']} {pm['move']} {k} {g} carries a state")
    if not o["table"]["outstanding_path"] or not o["plateau_means"]:
        b27.append("the outstanding path or the plateau means are missing")
    bs = o.get("beside") or {}
    for name, sname, mv, p in DIRECTIONAL:
        cells = (bs.get("states_possible") or {}).get(name) or {}
        want = {f"{k}/{g}" for k, c in o["moves"][sname][mv].items() for g in c["floors"]}
        if set(cells) != want or any(not c.get("states_possible") for c in cells.values()):
            b27.append(f"{name}: the states each cell can reach are not all printed")
        if set((bs.get("twins") or {}).get(name) or {}) != set(o["moves"][sname][mv]):
            b27.append(f"{name}: the same weeks of earlier years are not set against it in every setting")
    if set(bs.get("same_row_and_week") or {}) != set(o["moves"]["others_exports"]["deposit"]):
        b27.append("the tonnage sold and shipped in one row and week is not printed in every setting")
    a = o["moves"]
    out.append({"name": "B115-27", "kind": "own_reading", "passed": not b27,
                "statement": "printed without a state, each with its floors: every series from before the deposit to after "
                             "its end and across list one; net sales, R and the unknown destination across every step; "
                             "R by plateau; China's outstanding sales week by week; beside the criteria, the states "
                             "each cell can reach, the same weeks of earlier years, and the tonnage sold and shipped in "
                             "one row and week",
                "detail": f"{len(o['printed_moves'])} printed moves; setting A, grid from 2016: China exports P0 to P2 "
                          f"{t0((a['china_exports']['across'][DEFAULT]['observed'] or {}).get('move'))} (floor "
                          f"{t0(a['china_exports']['across'][DEFAULT]['floors']['from_2016'].get('floor'))}), P2 to P3 "
                          f"{t0((a['china_exports']['list_one'][DEFAULT]['observed'] or {}).get('move'))} (floor "
                          f"{t0(a['china_exports']['list_one'][DEFAULT]['floors']['from_2016'].get('floor'))}); R at the "
                          f"deposit {t0((a['china_r']['deposit'][DEFAULT]['observed'] or {}).get('move'))}, at the end "
                          f"{t0((a['china_r']['end'][DEFAULT]['observed'] or {}).get('move'))}"
                          + (": " + "; ".join(b27[:6]) if b27 else "")})
    ka = o["known_answer"]
    out.append({"name": "B115-28", "kind": "known_answer", "passed": bool(ka["destinations"]) and not ka["missing"],
                "statement": f"each of Saudi Arabia, Spain, Vietnam and Japan has gross new sales or exports above zero in "
                             f"the weeks ending {ka['window'][0]} to {ka['window'][1]}, the destinations Hansen, Marchant, "
                             "Zhang and Grant (Choices 33(2), 2018) name for the cargoes sent on in April",
                "detail": "; ".join(f"{n}: gross {v['gross']:,.0f}, net {v['net']:,.0f}, exports {v['exports']:,.0f}"
                                    for n, v in ka["destinations"].items())
                          + (f"; without either: {', '.join(ka['missing'])}" if ka["missing"] else "")})
    return out


def bookkeeping(record: dict) -> dict:
    bad = []
    if not record.get("config"):
        bad.append("no config")
    if not record.get("mapping"):
        bad.append("no mapping")
    if any(not c.get("kind") for c in record.get("criteria", [])):
        bad.append("a criterion without a kind")
    files = (record.get("objects") or {}).get("files") or []
    if len(files) != len(FIRST_YEARS) or any(not f.get("sha256") or not f.get("url") for f in files):
        bad.append("the six files do not all carry a hash and a URL")
    return {"name": "B115-29", "kind": "bookkeeping", "passed": not bad,
            "statement": "the record carries its configuration, a kind on every criterion, the mapping from states to "
                         "verdicts, and the hash and URL of each of the six files",
            "detail": f"{len(files)} files, {len(record.get('criteria', []))} criteria before this one"
                      + (": " + "; ".join(bad) if bad else "")}


def make_record(o: dict, config: dict | None) -> dict:
    record = {"stage": "B115", "mapping": MAPPING, "criteria": criteria_for(o), "objects": o}
    if config is not None:
        record["config"] = config
    record["criteria"].append(bookkeeping(record))
    return record


def config_of(steps: list[str]) -> dict:
    return {"data": "data/b115_sorghum_esr.json", "steps_from": "data/b115_sorghum_fob.json", "steps": steps,
            "p0": P0, "p3": P3, "settings": SETTINGS, "default_setting": DEFAULT, "placebo_grids": GRIDS,
            "table": TABLE, "chain_from": CHAIN_FROM, "moves": MOVES, "series": SERIES,
            "china": CHINA, "unknown": UNKNOWN, "tolerance_t": TOL, "report_step_t": REPORT_STEP,
            "deposit": DEPOSIT, "list_one": LIST_ONE, "twin_years": TWIN_YEARS, "after_year": AFTER_YEAR,
            "share_years": SHARE_YEARS, "known_answer": KNOWN,
            "requests": [list(year_span(y)) for y in FIRST_YEARS],
            "directional": [list(d) for d in DIRECTIONAL],
            "floor": "the larger of the reporting grid (0.1 t over each plateau's weeks) and the median absolute move "
                     "over placebo windows of the same shape",
            "state": "a criterion has a verdict only when all four settings and both grids give one state"}


# ---------------------------------------------------------------- output

def public(x):
    if isinstance(x, float):
        return float(f"{x:.9g}") if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): public(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [public(v) for v in x]
    return x


def show(o: dict, criteria: list[dict]) -> None:
    cov = o["coverage"]
    print(f"Thursdays {cov['thursdays']}, without a Total row {len(cov['thursdays_without_a_total_row'])}; weeks with no "
          f"row: China {cov['weeks_without_a_row'][CHINA]}, unknown {cov['weeks_without_a_row'][UNKNOWN]}")
    for f in o["files"]:
        print(f"  {f['file']}: {f['bytes']} bytes, {f['weeks']} weeks, {f['rows']} rows, pages {f['total_pages']}, "
              f"{f['header_from']}..{f['header_to']}")
    print("\nweek        omega   CN gross      net  exports  outstanding        R |  UNK net  UNK outst | oth gross  oth exp |"
          " tot exp  CN share")
    for r in o["table"]["weeks"]:
        c = r["china"]
        sh = "   n/a" if r["china_share_of_exports"] is None else f"{r['china_share_of_exports']:6.3f}"
        print(f"{r['week']}  {r['omega']:.4f} {c['gross']:9,.0f} {c['net']:8,.0f} {c['exports']:8,.0f} "
              f"{c['outstanding']:12,.0f} {r['china_r']:8,.0f} | {r['unknown_net']:8,.0f} {r['unknown_outstanding']:10,.0f} | "
              f"{r['others_gross']:9,.0f} {r['others_exports']:8,.0f} | {r['total_exports']:7,.0f}  {sh}")
        if r["others_by_destination"]:
            print("            " + "; ".join(f"{n} {v['gross']:,.0f}/{v['exports']:,.0f}"
                                           for n, v in r["others_by_destination"].items()))
    for y, rows in o["table"]["same_ordinal"].items():
        print(f"\nChina over the same weeks of {y}: exports " + " ".join(f"{r['china']['exports']:,.0f}" for r in rows))
        print(f"  gross " + " ".join(f"{r['china']['gross']:,.0f}" for r in rows))
    print("\ncalendar-year share of exports: " + ", ".join(
        f"{y} {v['share']:.3f} ({v['china_exports']:,.0f} of {v['total_exports']:,.0f})" if v["share"] is not None else f"{y} n/a"
        for y, v in o["table"]["calendar_year_share"].items()))
    print("\nplateau means, t/week")
    for k, pm in o["plateau_means"].items():
        for pn, v in pm.items():
            print(f"  {k} {pn}: " + "  ".join(f"{s} {t0(x)}" for s, x in v.items()))
    print("\nmoves, t/week: observed (floor; max; windows kept/apart; as large) by grid; twins")
    for sname, mvs in o["moves"].items():
        for mv, per in mvs.items():
            for k, c in per.items():
                ob = c["observed"] or {}
                fls = "  ".join(f"{g}: floor {t0(fl.get('floor'))} max {t0(fl.get('max_abs'))} "
                                f"{fl.get('windows')}/{fl.get('independent')} as large {fl.get('placebo_at_least_as_large')}"
                                + (f" -> {fl['state'][0]}" if "state" in fl else "") for g, fl in c["floors"].items())
                tw = " ".join(f"{y} {t0((v or {}).get('move'))}" for y, v in c["twins"].items())
                print(f"  {sname:15s} {mv:8s} {k} gap {c['gap_weeks']}: {t0(ob.get('move')):>9s} "
                      f"({t0(ob.get('pre_mean'))} -> {t0(ob.get('post_mean'))})  {fls}  | {tw}")
    bs = o["beside"]
    print("\nbeside the criteria: states a cell can reach (mean before against floor)")
    for name, cells in bs["states_possible"].items():
        print(f"  {name}: " + "; ".join(f"{c} {t0(v['mean_before'])} vs {t0(v['floor'])} -> {'/'.join(v['states_possible'])}"
                                         for c, v in cells.items()))
    print("the same weeks of earlier years: move, less the twin furthest the predicted way, over each floor; post/pre")
    for name, per in bs["twins"].items():
        for k, v in per.items():
            r = v["post_over_pre"]
            print(f"  {name} {k}: {t0(v['move'])} less {v['twin_furthest_the_predicted_way']} = {t0(v['move_less_that_twin'])}; "
                  + "; ".join(f"{g} x{x['move_less_that_twin_over_floor']:.2f} beyond: {','.join(x['twins_beyond_the_floor_the_predicted_way']) or 'none'}"
                              if x["move_less_that_twin_over_floor"] is not None else f"{g} n/a" for g, x in v["by_grid"].items())
                  + f"; post/pre {'n/a' if r is None else f'{r:.3f}'} twins "
                  + " ".join("n/a" if x is None else f"{x:.3f}" for x in v["twins_post_over_pre"].values()))
    print("sold and shipped in one row and week, other named destinations over the deposit's plateau")
    for k, v in bs["same_row_and_week"].items():
        print(f"  {k}: {t0(v['tonnes_in_those_rows'])} t in {len(v['rows'])} rows ("
              + ", ".join(f"{r['week']} {r['destination']} {r['tonnes']:,.0f}" for r in v["rows"])
              + f") of exports {t0(v['others_exports'])} and gross {t0(v['others_gross'])}; exports move without them "
              f"{t0(v['others_exports_move_without_those_rows'])}, placebo as large "
              + ", ".join(f"{g} {x['placebo_at_least_as_large']} of {x['windows']}" for g, x in v["by_grid"].items()))
    idn = o["identities"]
    print(f"\nidentities: {idn['rows']} rows, row breaks {len(idn['row_identity_breaks'])}, Total-row breaks "
          f"{len(idn['total_row_breaks'])}, China chain breaks {len(idn['china_chain_breaks'])} over "
          f"{idn['china_chain_links_checked']} links, chain breaks elsewhere {idn['chain_breaks_elsewhere']}")
    print("\nmapping")
    for m in MAPPING:
        print(f"  {m[0]:9s} {m[1]:45s} -> {m[2]}")
    print()
    for c in criteria:
        print(f"{c['name']} [{c['kind']}] {c['passed']}: {c['detail']}")


# ---------------------------------------------------------------- self-test

def fake_html(tokens: list[str], pages: int = 1, cut: bool = False) -> str:
    body = "".join(f'<div style="width:10.00mm;min-width: 10.00mm;">{html_lib.escape(t)}</div>' for t in tokens)
    return f'<html><script>{{"TotalPages":{pages}}}</script>{body}' + ("" if cut else "</html>\n")


def fake_tokens(lo: str, hi: str, weeks: dict, commodity: str = COMMODITY) -> list[str]:
    """weeks: week -> list of (marketing year first year, [(name with code, eight values), ...])."""
    def n(v):
        return f"{v:,.1f}"
    out = ["Export Sales Query System", "Export Sales Data by Commodity/Date/Country",
           f"From: {us_date(lo, False)} To: {us_date(hi, False)}", commodity]
    for w in sorted(weeks):
        out.append(f"{us_date(w)}(wk{1})")
        for y, rows in weeks[w]:
            out += [f" MY -  Sep {y}/Aug {y + 1}", "Current Marketing Year", "Next Marketing Year"] + list(COLUMNS)
            tot = [0.0] * 8
            for name, vals in rows:
                out += [name] + [n(v) for v in vals]
                tot = [a + b for a, b in zip(tot, vals)]
            out += ["Total"] + [n(v) for v in tot]
    return out


def synthetic(cn_exports=(150000.0, 20000.0, 60000.0, 30000.0), cn_gross=(8000.0, 500.0, 6000.0, 2000.0),
              oth_gross=(10000.0, 90000.0, 30000.0, 20000.0), oth_exports=(20000.0, 70000.0, 40000.0, 30000.0),
              noise=1.0, seed=7, china_into_others=False, drop=()) -> dict:
    """A world with exact plateau values in 2018 and a seasonal, noisy path elsewhere; identities hold by construction."""
    rng = random.Random(seed)
    span = grid_between(year_span(FIRST_YEARS[0])[0], year_span(FIRST_YEARS[-1])[1])
    lo_p, hi_p = "2018-04-05", "2018-08-02"

    def level(w, vals):
        if w < "2018-04-05" or w > hi_p:
            return None
        if w <= "2018-04-12":
            return vals[0]
        if w <= "2018-05-17":
            return vals[1]
        if w <= "2018-07-05":
            return vals[2]
        return vals[3]
    dests = {CHINA: "CHINA, PEOPLES REPUBLIC OF", UNKNOWN: "UNKNOWN", "5880": "JAPAN", "4700": "SPAIN",
             "5170": "SAUDI ARABIA", "5520": "VIETNAM", "2010": "MEXICO"}
    named = [c for c in dests if c not in (CHINA, UNKNOWN)]
    rows, totals = [], []
    state = {}
    for w in span:
        d = day(w)
        own = d.year if d >= first_thursday_of_september(d.year) else d.year - 1
        my = f"{own}/{(own + 1) % 100:02d}"
        k = (d - first_thursday_of_september(own)).days // 7
        season = 1 + 0.3 * math.sin(2 * math.pi * k / 52)
        tot = [0.0] * 8
        for code, name in dests.items():
            if (w, code) in drop:
                continue
            if code == CHINA:
                e, g = 40000 * season + noise * rng.uniform(-8000, 8000), 5000 * season + noise * rng.uniform(-1500, 1500)
                e, g = level(w, cn_exports) or e, level(w, cn_gross) or g
                r = 300.0
            elif code == UNKNOWN:
                e, g, r = 0.0, 2000.0 + noise * rng.uniform(-500, 500), 100.0
            else:
                share = 1.0 / len(named)
                e = (30000 * season + noise * rng.uniform(-6000, 6000)) * share
                g = (15000 * season + noise * rng.uniform(-4000, 4000)) * share
                le, lg = level(w, oth_exports), level(w, oth_gross)
                e, g = (le * share if le is not None else e), (lg * share if lg is not None else g)
                if china_into_others and code == named[0]:
                    e += level(w, cn_exports) or 0.0
                    g += level(w, cn_gross) or 0.0
                r = 0.0
            e, g = round(e, 1), round(g, 1)
            net = round(g - r, 1)
            prev = state.get((code, my), (0.0, 0.0))
            o_, a_ = round(prev[0] + net - e, 1), round(prev[1] + e, 1)
            state[(code, my)] = (o_, a_)
            vals = [g, net, e, o_, a_, round(o_ + a_, 1), 0.0, 0.0]
            rows.append([w, my, code, name] + vals)
            tot = [round(x + y, 1) for x, y in zip(tot, vals)]
        totals.append([w, my] + tot)
    files = []
    for y in FIRST_YEARS:
        lo, hi = year_span(y)
        files.append({"file": f"esr_sorghum_{y}_{(y + 1) % 100:02d}.html", "url": "u", "bytes": 1, "sha256": "0" * 64,
                      "request_from": lo, "request_to": hi, "header_from": lo, "header_to": hi, "total_pages": 1,
                      "complete": True, "commodities": [COMMODITY], "weeks": 52, "rows": 1})
    return {"rows": rows, "totals": totals, "files": files}


STEPS_2018 = ["2018-02-04", "2018-04-04", "2018-04-18", "2018-05-18", "2018-05-19", "2018-06-16", "2018-07-06"]


def selftest() -> int:
    fails, count = [], 0

    def check(name: str, cond: bool) -> None:
        nonlocal count
        count += 1
        if not cond:
            fails.append(name)

    def crit(o, config="cfg"):
        return {c["name"]: c for c in make_record(o, None if config is None else config_of(STEPS_2018))["criteria"]}

    # dates
    check("first Thursdays", [first_thursday_of_september(y).isoformat() for y in FIRST_YEARS] ==
          ["2013-09-05", "2014-09-04", "2015-09-03", "2016-09-01", "2017-09-07", "2018-09-06"])
    check("year span", year_span(2017) == ("2017-09-07", "2018-08-30"))
    check("ordinal shift", shift_to_year("2018-04-05", 2016) == "2017-03-30" and shift_to_year("2018-04-05", 2017) == "2018-04-05")
    check("ordinal shift forward", shift_to_year("2018-04-05", 2018) == "2019-04-04")
    om = {w: omega(w) for w in ("2018-04-12", "2018-04-19", "2018-04-26", "2018-05-17", "2018-05-24", "2018-07-05", "2018-07-12")}
    check("omega zero before", om["2018-04-12"]["omega"] == 0 and om["2018-05-24"]["omega"] == 0 and om["2018-07-05"]["omega"] == 0)
    check("omega mixed week", om["2018-04-19"]["deposit_days"] == 2 and abs(om["2018-04-19"]["omega"] - 2 / 7 * math.log(2.786)) < 1e-12)
    check("omega deposit", abs(om["2018-04-26"]["omega"] - math.log(2.786)) < 1e-12 and abs(om["2018-04-26"]["omega"] - 1.0246) < 5e-5 and om["2018-05-17"]["deposit_days"] == 7)
    check("omega list one", abs(om["2018-07-12"]["omega"] - 0.2231) < 5e-5 and om["2018-07-12"]["list_one_days"] == 7)
    check("us date", us_date("2018-04-05") == "04/05/2018" and us_date("2018-04-05", False) == "4/5/2018")
    check("url", "weekStartDate=09/07/2017&weekEndDate=08/30/2018&commodityId=13&destinationCode=5700,9990&format=" in
          url_for("2017-09-07", "2018-08-30", ["5700", "9990"]))

    # the parser
    wk = {"2018-08-30": [(2017, [("CHINA, PEOPLES REPUBLIC OF     (5700)", [1.0, -2.5, 3.0, 4.0, 5.0, 9.0, 0.0, 0.0]),
                                 ("CONGO (BRAZZAVILLE)            (7620)", [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0])]),
                         (2018, [("TRINIDAD & TOBAGO, REP. OF     (2740)", [1234567.5, 0.0, 0.0, 7.0, 0.0, 7.0, 0.0, 0.0])])]}
    p = parse_report(fake_html(fake_tokens("2018-08-30", "2018-08-30", wk)))
    check("parser: two marketing years in one week", [r[1] for r in p["rows"]] == ["2017/18", "2017/18", "2018/19"]
          and [r[1] for r in p["totals"]] == ["2017/18", "2018/19"])
    check("parser: names with commas, ampersands and brackets", [(r[2], r[3]) for r in p["rows"]] ==
          [("5700", "CHINA, PEOPLES REPUBLIC OF"), ("7620", "CONGO (BRAZZAVILLE)"), ("2740", "TRINIDAD & TOBAGO, REP. OF")])
    check("parser: negative and thousands", p["rows"][0][5] == -2.5 and p["rows"][2][4] == 1234567.5)
    check("parser: header", (p["header_from"], p["header_to"], p["commodities"], p["total_pages"], p["complete"]) ==
          ("2018-08-30", "2018-08-30", [COMMODITY], 1, True))
    check("parser: Total row", p["totals"][0][2:] == [1.0, -2.5, 3.0, 4.0, 6.0, 10.0, 0.0, 0.0])
    check("file check passes", check_file(p, "2018-08-30", "2018-08-30") == [])
    check("file check: two pages", any("TotalPages" in b for b in check_file(
        parse_report(fake_html(fake_tokens("2018-08-30", "2018-08-30", wk), pages=2)), "2018-08-30", "2018-08-30")))
    check("file check: cut short", any("</html>" in b for b in check_file(
        parse_report(fake_html(fake_tokens("2018-08-30", "2018-08-30", wk), cut=True)), "2018-08-30", "2018-08-30")))
    check("file check: header a day off", any("header" in b for b in check_file({**p, "header_from": "2018-08-29"}, "2018-08-30", "2018-08-30")))
    check("file check: a week missing", any("weeks with a Total row" in b for b in check_file(p, "2018-08-23", "2018-08-30")))
    check("file check: corn", any("commodity" in b for b in check_file(
        parse_report(fake_html(fake_tokens("2018-08-30", "2018-08-30", wk, commodity="CORN - UNMILLED"))), "2018-08-30", "2018-08-30")))
    toks = fake_tokens("2018-08-30", "2018-08-30", wk)
    swapped = list(toks)
    i_g, i_n = swapped.index("Gross New Sales"), swapped.index("Net Sales")
    swapped[i_g], swapped[i_n] = swapped[i_n], swapped[i_g]
    for label, bad_tokens in (("columns in another order", swapped),
                              ("a row with seven numbers", toks[:toks.index("Total")] + toks[toks.index("Total") + 1:]),
                              ("a destination without a code", [t.replace("     (5700)", "") for t in toks])):
        try:
            parse_report(fake_html(bad_tokens))
            check("parser raises on " + label, False)
        except ValueError:
            check("parser raises on " + label, True)

    fb = file_block("f.html", "u", b"abc", p, "2018-08-30", "2018-08-30")
    check("file block", fb["sha256"] == hashlib.sha256(b"abc").hexdigest() and fb["bytes"] == 3 and fb["weeks"] == 1
          and fb["rows"] == 3 and fb["request_to"] == fb["header_to"] == "2018-08-30")
    back = json.loads(data_text([fb], list(reversed(p["rows"])), list(reversed(p["totals"])),
                                {"commodity_code": 701, "commodity_id": 13, "destination_codes": ["5700"]}))
    check("data file: rows sorted, values kept to 0.1 t", back["rows"] == sorted(p["rows"], key=lambda r: (r[0], r[1], r[2]))
          and back["totals"] == p["totals"] and back["files"] == [fb] and back["columns"] == list(KEYS))

    # the synthetic world, read back
    w0 = synthetic()
    o = run(w0, STEPS_2018)
    c = crit(o)
    check("world: every criterion passes", all(c[n]["passed"] is True for n in c))
    check("world: thirteen criteria, each with a kind", sorted(c) == [f"B115-{k}" for k in range(17, 30)]
          and all(v["kind"] in ("instrument", "own_reading", "known_answer", "bookkeeping") for v in c.values()))
    mv = o["moves"]
    check("deposit move, China exports, A", abs(mv["china_exports"]["deposit"]["A"]["observed"]["move"] - (20000.0 - 150000.0)) < 1e-6)
    check("deposit move, China exports, B", abs(mv["china_exports"]["deposit"]["B"]["observed"]["move"] + 130000.0) < 1e-6
          and mv["china_exports"]["deposit"]["B"]["observed"]["post_n"] == 4)
    check("end move, China exports, A and C", abs(mv["china_exports"]["end"]["A"]["observed"]["move"] - 40000.0) < 1e-6
          and mv["china_exports"]["end"]["C"]["observed"]["post_n"] == 3)
    check("across", abs(mv["china_exports"]["across"]["A"]["observed"]["move"] + 90000.0) < 1e-6)
    check("list one", abs(mv["china_exports"]["list_one"]["A"]["observed"]["move"] + 30000.0) < 1e-6
          and mv["china_exports"]["list_one"]["A"]["gap_weeks"] == 3)
    check("others gross at the deposit", abs(mv["others_gross"]["deposit"]["A"]["observed"]["move"] - 80000.0) < 1e-3)
    check("others exports at the deposit", abs(mv["others_exports"]["deposit"]["A"]["observed"]["move"] - 50000.0) < 1e-3)
    check("R is gross minus net", abs(mv["china_r"]["deposit"]["A"]["observed"]["pre_mean"] - 300.0) < 1e-6)
    check("gaps", [mv["china_exports"][m]["A"]["gap_weeks"] for m in MOVES] == [0, 0, 5, 3]
          and mv["china_exports"]["deposit"]["B"]["gap_weeks"] == 1 and mv["china_exports"]["end"]["C"]["gap_weeks"] == 1)
    fl = mv["china_exports"]["deposit"]["A"]["floors"]
    check("two floors, the longer grid has more windows", fl["from_2013"]["windows"] > fl["from_2016"]["windows"] > 0)
    n16 = len(grid_between(*GRIDS["from_2016"])) - 7 + 1
    check("window count on the short grid", fl["from_2016"]["windows"] == n16)
    check("floor is the median, above the grid", fl["from_2016"]["floor"] == fl["from_2016"]["median_abs"] > fl["from_2016"]["grid"]
          and abs(fl["from_2016"]["grid"] - (0.1 / 2 + 0.1 / 5)) < 1e-12)
    check("max at least the median", fl["from_2016"]["max_abs"] >= fl["from_2016"]["median_abs"])
    check("as-large count", fl["from_2016"]["placebo_at_least_as_large"] == 0)
    check("independent windows", 0 < fl["from_2016"]["independent"] <= fl["from_2016"]["windows"] // 7 + 1)
    check("twins", set(mv["china_exports"]["deposit"]["A"]["twins"]) == {"2014/15", "2015/16", "2016/17", "2018/19"}
          and all(v is not None for v in mv["china_exports"]["deposit"]["A"]["twins"].values()))
    flat = synthetic(noise=0.0)
    of = run(flat, STEPS_2018)
    tw = of["moves"]["china_exports"]["deposit"]["A"]["twins"]["2016/17"]
    k0 = (day("2018-04-05") - first_thursday_of_september(2017)).days // 7
    sea = lambda k: 40000 * (1 + 0.3 * math.sin(2 * math.pi * k / 52))  # noqa: E731
    want = statistics.fmean(sea(k0 + 2 + j) for j in range(5)) - statistics.fmean(sea(k0 + j) for j in range(2))
    check("twin window reads the seasonal move of its own year", abs(tw["move"] - want) < 0.2)
    check("noise-free world: reporting grid is not the floor, seasonal drift is", of["moves"]["china_exports"]["deposit"]["A"]
          ["floors"]["from_2016"]["floor"] > 1.0)
    const = synthetic(noise=0.0)
    for r in const["rows"]:
        if r[2] == CHINA and r[0] <= "2018-02-01":
            r[6] = 1000.0
    oc = run(const, STEPS_2018)
    check("a flat history gives the reporting grid as the floor",
          abs(oc["moves"]["china_exports"]["deposit"]["A"]["floors"]["from_2016"]["floor"] - 0.07) < 1e-9)
    tb = o["table"]
    check("table: 35 weeks", len(tb["weeks"]) == 35 == tb["expected_weeks"])
    r419 = next(r for r in tb["weeks"] if r["week"] == "2018-04-19")
    check("table: China columns", r419["china"]["exports"] == 20000.0 and r419["china"]["gross"] == 500.0 and r419["china_r"] == 300.0)
    check("table: shares", abs(r419["china_share_of_exports"] - 20000.0 / 90000.0) < 1e-9)
    check("table: others one by one", len(r419["others_by_destination"]) == 5 and
          abs(sum(v["gross"] for v in r419["others_by_destination"].values()) - 90000.0) < 1e-6)
    check("table: same ordinals", len(tb["same_ordinal"]["2016/17"]) == 35 and tb["same_ordinal"]["2018/19"][0]["week"] == "2019-01-03")
    check("table: calendar years", list(tb["calendar_year_share"]) == ["2014", "2015", "2016", "2017"]
          and all(0 < v["share"] < 1 and v["weeks"] in (52, 53) for v in tb["calendar_year_share"].values()))
    check("plateau means", abs(o["plateau_means"]["A"]["P3"]["china_exports"] - 30000.0) < 1e-6
          and abs(o["plateau_means"]["D"]["P1"]["china_gross"] - 500.0) < 1e-6)
    check("zero rows counted", o["coverage"]["weeks_without_a_row"] == {CHINA: 0, UNKNOWN: 0})
    od = run(synthetic(drop={("2015-03-05", CHINA)}), STEPS_2018)
    check("an absent row is a counted zero", od["coverage"]["weeks_without_a_row"][CHINA] == 1
          and build(synthetic(drop={("2015-03-05", CHINA)}))["series"]["china_exports"]["2015-03-05"] == 0.0)
    check("others exclude China and unknown", abs(build(w0)["series"]["others_gross"]["2018-04-26"] - 90000.0) < 1e-6
          and abs(build(w0)["series"]["named_gross"]["2018-04-26"] - 90000.0 - 500.0 - build(w0)["series"]["unknown_net"]["2018-04-26"] - 100.0) < 1e-6)

    # the mapping, row by row
    for pred_, reason, state in CELL:
        fl_ = None if reason == R_NO_FLOOR else 10.0
        ob = None if reason == R_GAP else {"move": {R_BELOW: -11.0, R_ABOVE: 11.0}.get(reason, 3.0)}
        for p_ in ((LE, GE) if pred_ == "any" else (pred_,)):
            check(f"mapping {p_} {reason}", read_state(p_, ob, fl_) == (state, reason))
    check("at the floor is within", read_state(LE, {"move": -10.0}, 10.0)[0] == NOT_READ and read_state(GE, {"move": 10.0}, 10.0)[0] == NOT_READ)
    eight = lambda s: {str(k): (s, "") for k in range(8)}  # noqa: E731
    check("criterion states", (criterion_state(eight(MATCH)), criterion_state(eight(MISS)), criterion_state(eight(NOT_READ))) ==
          (ALL_MATCH, ALL_MISS, ALL_NOT_READ))
    mixed = eight(MATCH)
    mixed["3"] = (NOT_READ, "")
    mixed2 = eight(MATCH)
    mixed2["0"] = (MISS, "")
    check("split gives no verdict", VERDICT[criterion_state(mixed)] is None and VERDICT[criterion_state(mixed2)] is None
          and criterion_state(mixed) == SPLIT)
    check("verdicts", VERDICT[ALL_MATCH] is True and VERDICT[ALL_MISS] is False and VERDICT[ALL_NOT_READ] is None)

    # planted faults, criterion by criterion
    def without(world, pred_fn):
        w = copy.deepcopy(world)
        w["rows"] = [r for r in w["rows"] if not pred_fn(r)]
        return w

    w = copy.deepcopy(w0)
    w["rows"] = [r for r in w["rows"] if r[0] != "2018-05-03"]
    w["totals"] = [r for r in w["totals"] if r[0] != "2018-05-03"]
    c1 = crit(run(w, STEPS_2018))
    check("B115-17 fails on a plateau week removed", c1["B115-17"]["passed"] is False)
    check("a plateau without all its weeks is not read", c1["B115-21"]["passed"] is None)
    w = copy.deepcopy(w0)
    w["totals"] = [r for r in w["totals"] if r[0] != "2014-06-05"]
    w["rows"] = [r for r in w["rows"] if r[0] != "2014-06-05"]
    check("B115-17 fails on a Thursday outside the plateaus removed", crit(run(w, STEPS_2018))["B115-17"]["passed"] is False)
    for label, key, val in (("two pages", "total_pages", 2), ("header a day off", "header_from", "2017-09-08"),
                            ("corn", "commodities", ["CORN - UNMILLED"]), ("cut short", "complete", False)):
        w = copy.deepcopy(w0)
        w["files"][4][key] = val
        check("B115-17 fails on " + label, crit(run(w, STEPS_2018))["B115-17"]["passed"] is False)
    w = copy.deepcopy(w0)
    w["files"] = w["files"][:5]
    cf = crit(run(w, STEPS_2018))
    check("B115-17 and B115-29 fail on five files", cf["B115-17"]["passed"] is False and cf["B115-29"]["passed"] is False)

    w = copy.deepcopy(w0)
    i = next(i for i, r in enumerate(w["rows"]) if r[2] == CHINA and r[0] == "2018-05-10")
    w["rows"][i][7] += 1.0
    c2 = crit(run(w, STEPS_2018))
    check("B115-18 fails on one tonne in a China cell", c2["B115-18"]["passed"] is False)
    w = copy.deepcopy(w0)
    w["rows"][i][8] += 1.0
    w["rows"][i][9] += 1.0
    idn = run(w, STEPS_2018)["identities"]
    check("accumulated a tonne off breaks the chain and the Total row, not the row identity",
          len(idn["china_chain_breaks"]) == 2 and len(idn["total_row_breaks"]) == 2 and not idn["row_identity_breaks"])
    w = copy.deepcopy(w0)
    j = next(i for i, r in enumerate(w["rows"]) if r[2] == "5880" and r[0] == "2015-02-05")
    w["rows"][j][7] += 5.0
    w["rows"][j][9] += 5.0
    for t in w["totals"]:
        if t[0] == "2015-02-05":
            t[5] += 5.0
            t[7] += 5.0
    o3 = run(w, STEPS_2018)
    check("a chain break elsewhere is printed and not judged", o3["identities"]["chain_breaks_elsewhere"] == 2
          and crit(o3)["B115-18"]["passed"] is True)
    w = copy.deepcopy(w0)
    w["rows"][j][9] += 2.0
    for t in w["totals"]:
        if t[0] == "2015-02-05":
            t[7] += 2.0
    idn = run(w, STEPS_2018)["identities"]
    check("commitment two tonnes off breaks the row identity alone", len(idn["row_identity_breaks"]) == 1
          and not idn["total_row_breaks"] and not idn["china_chain_breaks"] and idn["chain_breaks_elsewhere"] == 0
          and crit(run(w, STEPS_2018))["B115-18"]["passed"] is False)
    check("B115-18 fails on a destination row removed", crit(run(without(w0, lambda r: r[2] == "2010" and r[0] == "2016-03-03"),
                                                              STEPS_2018))["B115-18"]["passed"] is False)
    w = copy.deepcopy(w0)
    w["totals"][10][4] += 3.0
    check("B115-18 fails on a Total row changed", crit(run(w, STEPS_2018))["B115-18"]["passed"] is False)
    check("B115-18 fails on China without a row in the window",
          crit(run(without(w0, lambda r: r[2] == CHINA and r[0] == "2018-06-07"), STEPS_2018))["B115-18"]["passed"] is False)
    check("B115-18 fails with nothing to check", crit(run({"rows": [], "totals": w0["totals"], "files": w0["files"]},
                                                          STEPS_2018))["B115-18"]["passed"] is False)

    o4 = run(w0, STEPS_2018, grids={"from_2016": ("2016-01-07", "2018-06-28"), "from_2013": GRIDS["from_2013"]}, drop_spanning=False)
    check("B115-19 fails on a window across a dated document", crit(o4)["B115-19"]["passed"] is False)
    o4b = run(w0, STEPS_2018, grids={"from_2016": ("2016-01-07", "2018-06-28"), "from_2013": GRIDS["from_2013"]})
    check("windows across a dated document are dropped", crit(o4b)["B115-19"]["passed"] is True and
          o4b["moves"]["china_exports"]["deposit"]["A"]["floors"]["from_2016"]["spanning_a_date_dropped"] > 0)
    o5 = run(w0, STEPS_2018, grids={"from_2016": ("2018-01-04", "2018-02-01"), "from_2013": GRIDS["from_2013"]})
    c5 = crit(o5)
    check("B115-19 fails on a grid too short for a window", c5["B115-19"]["passed"] is False)
    check("no floor on one grid gives no verdict", c5["B115-21"]["passed"] is None and c5["B115-27"]["passed"] is False)

    o6 = copy.deepcopy(o)
    o6["table"]["weeks"] = []
    check("B115-20 fails on an empty table", crit(o6)["B115-20"]["passed"] is False)
    o6 = copy.deepcopy(o)
    o6["table"]["weeks"] = o6["table"]["weeks"][:-1]
    check("B115-20 fails a week short", crit(o6)["B115-20"]["passed"] is False)
    o6 = copy.deepcopy(o)
    o6["table"]["same_ordinal"]["2018/19"] = []
    check("B115-20 fails on an empty comparison year", crit(o6)["B115-20"]["passed"] is False)
    o6 = copy.deepcopy(o)
    for r in o6["table"]["weeks"]:
        r["total_exports"] = 0.0
    check("B115-20 fails on a table of zeros", crit(o6)["B115-20"]["passed"] is False)

    up = crit(run(synthetic(cn_exports=(150000.0, 260000.0, 60000.0, 30000.0), cn_gross=(8000.0, 30000.0, 6000.0, 2000.0)), STEPS_2018))
    check("B115-21 and B115-22 fail when China rises at the deposit", up["B115-21"]["passed"] is False and up["B115-22"]["passed"] is False)
    check("and the end then falls: B115-23 and B115-24 fail", up["B115-23"]["passed"] is False and up["B115-24"]["passed"] is False)
    near = crit(run(synthetic(cn_exports=(150000.0, 149000.0, 149500.0, 30000.0), cn_gross=(8000.0, 7990.0, 8000.0, 2000.0)), STEPS_2018))
    check("moves inside the floor are not read", all(near[n]["passed"] is None for n in ("B115-21", "B115-22", "B115-23", "B115-24")))
    w = copy.deepcopy(w0)
    for r in w["rows"]:
        if r[2] == CHINA and r[0] == "2018-04-19":
            r[6] = 1500000.0
    one = run(w, STEPS_2018)
    check("one setting the other way gives no verdict", crit(one)["B115-21"]["passed"] is None
          and one["directional"]["B115-21"]["state"] == SPLIT
          and one["directional"]["B115-21"]["cells"]["A/from_2016"][0] == MISS
          and one["directional"]["B115-21"]["cells"]["B/from_2016"][0] == MATCH)
    down = crit(run(synthetic(oth_gross=(90000.0, 10000.0, 30000.0, 20000.0), oth_exports=(70000.0, 20000.0, 40000.0, 30000.0)), STEPS_2018))
    check("B115-25 and B115-26 fail when the others fall", down["B115-25"]["passed"] is False and down["B115-26"]["passed"] is False)
    merged = run(synthetic(china_into_others=True, oth_gross=(10000.0, 12000.0, 30000.0, 20000.0),
                           oth_exports=(20000.0, 70000.0, 40000.0, 30000.0)), STEPS_2018)
    check("China counted among the others turns B115-26 over", crit(merged)["B115-26"]["passed"] is False
          and abs(merged["moves"]["others_exports"]["deposit"]["A"]["observed"]["move"] - (50000.0 - 130000.0)) < 1e-3)
    endfall = crit(run(synthetic(cn_exports=(150000.0, 80000.0, 10000.0, 30000.0), cn_gross=(8000.0, 6000.0, 100.0, 2000.0)), STEPS_2018))
    check("B115-23 and B115-24 fail when China falls after the end", endfall["B115-23"]["passed"] is False and endfall["B115-24"]["passed"] is False)

    o7 = copy.deepcopy(o)
    o7["printed_moves"][0]["verdict"] = True
    check("B115-27 fails on a verdict on a printed move", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    o7["moves"]["china_r"]["end"]["B"]["floors"]["from_2013"]["floor"] = None
    check("B115-27 fails on a floor removed", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    o7["moves"]["unknown_net"]["deposit"]["A"]["floors"]["from_2016"]["state"] = [MATCH, R_BELOW]
    check("B115-27 fails on a state on a printed move", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    o7["printed_moves"].append({"series": "china_exports", "move": "deposit"})
    check("B115-27 fails when a criterion's move is listed as printed", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    o7["printed_moves"] = []
    check("B115-27 fails with nothing printed", crit(o7)["B115-27"]["passed"] is False)
    check("printed moves are the ones with no prediction", len(o["printed_moves"]) == len(SERIES) * len(MOVES) - len(DIRECTIONAL)
          and all("state" not in fl_ for pm in o["printed_moves"] for c_ in o["moves"][pm["series"]][pm["move"]].values()
                  for fl_ in c_["floors"].values()))
    check("directional cells carry a state", all("state" in fl_ for _, s_, m_, _ in DIRECTIONAL for c_ in o["moves"][s_][m_].values()
                                                 for fl_ in c_["floors"].values()))

    # beside the criteria
    bs = o["beside"]
    check("beside: rows are never below zero", bs["least_value_in_a_row"]["gross"] >= 0 and bs["least_value_in_a_row"]["exports"] >= 0)
    r21 = bs["states_possible"]["B115-21"]
    check("beside: a cell that can fall past its floor reaches all three states", len(r21) == len(SETTINGS) * len(GRIDS) and all(
        v["a_fall_beyond_the_floor_possible"] and v["states_possible"] == sorted([MATCH, MISS, NOT_READ])
        and abs(v["mean_before"] - 150000.0) < 1e-6 and abs(v["lowest_possible_move"] + 150000.0) < 1e-6 for v in r21.values()))
    low = run(synthetic(cn_exports=(150000.0, 100.0, 60000.0, 30000.0), cn_gross=(8.0, 500.0, 6000.0, 2000.0)), STEPS_2018)
    lb = low["beside"]["states_possible"]
    check("beside: a level under the floor cannot miss a rise", all(
        not v["a_fall_beyond_the_floor_possible"] and v["states_possible"] == sorted([MATCH, NOT_READ])
        and v["floor"] > v["mean_before"] == 100.0 for v in lb["B115-23"].values()))
    check("beside: a level under the floor cannot match a fall", all(
        not v["a_fall_beyond_the_floor_possible"] and v["states_possible"] == sorted([MISS, NOT_READ])
        for v in lb["B115-22"].values()))
    check("beside: reach follows each cell's own floor", all(
        v["a_fall_beyond_the_floor_possible"] == (v["mean_before"] > v["floor"])
        and v["floor"] == o["moves"][s_][m_][c_.split("/")[0]]["floors"][c_.split("/")[1]]["floor"]
        and v["mean_before"] == o["moves"][s_][m_][c_.split("/")[0]]["observed"]["pre_mean"]
        for n_, s_, m_, _ in DIRECTIONAL for c_, v in bs["states_possible"][n_].items()))
    nofl = copy.deepcopy(o)
    nofl["moves"]["china_exports"]["deposit"]["A"]["floors"]["from_2016"]["floor"] = None
    nb = beside(w0, build(w0), nofl["moves"], STEPS_2018, SETTINGS, GRIDS)
    check("beside: a cell without a floor reaches only not read", nb["states_possible"]["B115-21"]["A/from_2016"]["states_possible"] == [NOT_READ]
          and nb["twins"]["B115-21"]["A"]["by_grid"]["from_2016"]["move_less_that_twin_over_floor"] is None)
    for n_, s_, m_, p_ in DIRECTIONAL:
        for k_ in SETTINGS:
            c_ = o["moves"][s_][m_][k_]
            tm = {y: c_["twins"][y]["move"] for y in ("2014/15", "2015/16", "2016/17")}
            far_ = (min if p_ == LE else max)(tm, key=tm.get)
            t_ = bs["twins"][n_][k_]
            sg = -1.0 if p_ == LE else 1.0
            check(f"beside: twins {n_} {k_}", t_["twin_furthest_the_predicted_way"] == far_
                  and abs(t_["move_less_that_twin"] - (c_["observed"]["move"] - tm[far_])) < 1e-9
                  and set(t_["twins_post_over_pre"]) == set(tm)
                  and abs(t_["post_over_pre"] - c_["observed"]["post_mean"] / c_["observed"]["pre_mean"]) < 1e-12
                  and all(abs(x["move_less_that_twin_over_floor"] - sg * t_["move_less_that_twin"] / c_["floors"][g_]["floor"]) < 1e-12
                          and x["twins_beyond_the_floor_the_predicted_way"] == sorted(y for y, m in tm.items() if sg * m > c_["floors"][g_]["floor"])
                          for g_, x in t_["by_grid"].items()))
    check("beside: twin ratios read each year's own means", abs(
        bs["twins"]["B115-21"]["A"]["twins_post_over_pre"]["2015/16"]
        - o["moves"]["china_exports"]["deposit"]["A"]["twins"]["2015/16"]["post_mean"]
        / o["moves"]["china_exports"]["deposit"]["A"]["twins"]["2015/16"]["pre_mean"]) < 1e-12)
    sr = bs["same_row_and_week"]
    check("beside: no row sold and shipped alike in the plain world", all(
        v["rows"] == [] and v["tonnes_in_those_rows"] == 0
        and abs(v["others_exports_move_without_those_rows"] - o["moves"]["others_exports"]["deposit"][k_]["observed"]["move"]) < 1e-9
        and all(x["placebo_at_least_as_large"] == o["moves"]["others_exports"]["deposit"][k_]["floors"][g_]["placebo_at_least_as_large"]
                and x["windows"] == o["moves"]["others_exports"]["deposit"][k_]["floors"][g_]["windows"] for g_, x in v["by_grid"].items())
        for k_, v in sr.items()))
    check("beside: plateau totals of the others", abs(sr["A"]["others_exports"] - 5 * 70000.0) < 1e-3 and abs(sr["A"]["others_gross"] - 5 * 90000.0) < 1e-3
          and abs(sr["B"]["others_exports"] - 4 * 70000.0) < 1e-3 and abs(sr["A"]["sold_and_shipped_row_by_row"] - 5 * 70000.0) < 1e-3)
    ws = copy.deepcopy(w0)
    for r in ws["rows"]:
        if r[3] == "SPAIN" and r[0] in ("2018-04-19", "2018-05-03"):
            r[4] = r[6]                      # sold and shipped alike, 14,000 t each
        if r[2] == CHINA and r[0] == "2018-05-03":
            r[4] = r[6]                      # China's own row is no part of it
        if r[3] == "SPAIN" and r[0] == "2018-06-07":
            r[4] = r[6]                      # outside the deposit's plateau
    osr = run(ws, STEPS_2018)
    sa, sb = osr["beside"]["same_row_and_week"]["A"], osr["beside"]["same_row_and_week"]["B"]
    mva = osr["moves"]["others_exports"]["deposit"]
    check("beside: rows sold and shipped alike are named", [(r["week"], r["destination"]) for r in sa["rows"]] ==
          [("2018-04-19", "SPAIN"), ("2018-05-03", "SPAIN")] and abs(sa["tonnes_in_those_rows"] - 28000.0) < 1e-6
          and [(r["week"], r["destination"]) for r in sb["rows"]] == [("2018-05-03", "SPAIN")] and abs(sb["tonnes_in_those_rows"] - 14000.0) < 1e-6)
    check("beside: the move without those rows", abs(sa["others_exports_move_without_those_rows"] - (mva["A"]["observed"]["move"] - 28000.0 / 5)) < 1e-6
          and abs(sb["others_exports_move_without_those_rows"] - (mva["B"]["observed"]["move"] - 14000.0 / 4)) < 1e-6
          and abs(sa["share_of_exports"] - 28000.0 / 350000.0) < 1e-9
          and abs(sa["share_of_gross"] - 28000.0 / sa["others_gross"]) < 1e-12 and sa["others_gross"] < 450000.0)
    big = synthetic(oth_exports=(20000.0, 26000.0, 40000.0, 30000.0))
    for r in big["rows"]:
        if r[3] == "SPAIN" and "2018-04-19" <= r[0] <= "2018-05-17":
            r[6] = 5200.0 + 250000.0
            r[4] = r[6]
    ob_ = run(big, STEPS_2018)
    ba = ob_["beside"]["same_row_and_week"]["A"]
    check("beside: placebo windows are counted against the move without those rows", abs(
        ba["others_exports_move_without_those_rows"] - (ob_["moves"]["others_exports"]["deposit"]["A"]["observed"]["move"] - 255200.0)) < 1e-6
          and abs(ba["others_exports_move_without_those_rows"] - 800.0) < 1e-6
          and all(0 < x["placebo_at_least_as_large"] <= x["windows"] for x in ba["by_grid"].values())
          and all(fl_["placebo_at_least_as_large"] == 0 for fl_ in ob_["moves"]["others_exports"]["deposit"]["A"]["floors"].values()))
    small = run(synthetic(oth_exports=(20000.0, 22000.0, 40000.0, 30000.0)), STEPS_2018)
    check("beside: placebo windows are those of the others' exports", all(
        x["placebo_at_least_as_large"] == small["moves"]["others_exports"]["deposit"][k_]["floors"][g_]["placebo_at_least_as_large"] > 0
        and x["placebo_at_least_as_large"] != small["moves"]["others_gross"]["deposit"][k_]["floors"][g_]["placebo_at_least_as_large"]
        for k_, v in small["beside"]["same_row_and_week"].items() for g_, x in v["by_grid"].items()))
    wide = run(w0, STEPS_2018, grids={"across_the_dates": ("2016-01-07", "2018-08-02")})
    check("beside: placebo windows across a dated document are left out as in the floors", all(
        x["windows"] == wide["moves"]["others_exports"]["deposit"][k_]["floors"][g_]["windows"]
        and wide["moves"]["others_exports"]["deposit"][k_]["floors"][g_]["spanning_a_date_dropped"] > 0
        for k_, v in wide["beside"]["same_row_and_week"].items() for g_, x in v["by_grid"].items()))
    o7 = copy.deepcopy(o)
    del o7["beside"]
    check("B115-27 fails without what is printed beside the criteria", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    del o7["beside"]["states_possible"]["B115-23"]["C/from_2013"]
    check("B115-27 fails when a cell's reach is not printed", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    del o7["beside"]["twins"]["B115-21"]["B"]
    check("B115-27 fails when a setting's twins are not printed", crit(o7)["B115-27"]["passed"] is False)
    o7 = copy.deepcopy(o)
    del o7["beside"]["same_row_and_week"]["D"]
    check("B115-27 fails when a setting's shared rows are not printed", crit(o7)["B115-27"]["passed"] is False)
    check("B115-27 holds on the plain world", crit(o)["B115-27"]["passed"] is True)

    ka = crit(run(without(w0, lambda r: r[2] == "4700"), STEPS_2018))["B115-28"]
    check("B115-28 fails without Spain, and names it", ka["passed"] is False and "SPAIN" in ka["detail"].split("without either")[-1])
    saved = KNOWN["window"]
    KNOWN["window"] = ("2018-03-01", "2018-03-29")
    w = copy.deepcopy(w0)
    for r in w["rows"]:
        if r[2] in ("5520", "5170") and r[0] < "2018-04-01":
            r[4] = r[6] = 0.0
    k3 = known_answer(w)
    KNOWN["window"] = saved
    check("B115-28 reads its own window", k3["window"] == ["2018-03-01", "2018-03-29"] and sorted(k3["missing"]) == ["SAUDI ARABIA", "VIETNAM"])
    w = copy.deepcopy(w0)
    for r in w["rows"]:
        if r[2] == "5520":
            r[6] = 0.0
    k4 = known_answer(w)
    check("gross new sales alone count as arriving", k4["destinations"]["VIETNAM"]["positive"]
          and k4["destinations"]["VIETNAM"]["exports"] == 0 and not k4["missing"])
    check("known answer sums the window", abs(o["known_answer"]["destinations"]["SPAIN"]["gross"] - (5 * 18000.0 + 2 * 6000.0)) < 1e-3)

    check("B115-29 fails without config", crit(o, config=None)["B115-29"]["passed"] is False)
    rec = make_record(o, config_of(STEPS_2018))
    rec2 = copy.deepcopy(rec)
    rec2["criteria"][3].pop("kind")
    check("B115-29 fails on a criterion without a kind", bookkeeping({**rec2, "criteria": rec2["criteria"][:-1]})["passed"] is False)
    rec2 = copy.deepcopy(rec)
    rec2["objects"]["files"][2]["sha256"] = ""
    check("B115-29 fails on a file without its hash", bookkeeping({**rec2, "criteria": rec2["criteria"][:-1]})["passed"] is False)
    rec2 = copy.deepcopy(rec)
    rec2.pop("mapping")
    check("B115-29 fails without the mapping", bookkeeping({**rec2, "criteria": rec2["criteria"][:-1]})["passed"] is False)
    text = json.dumps(public(rec), sort_keys=True)
    check("the record serialises, floats rounded", "NaN" not in text and public(1 / 3) == 0.333333333)
    check("config names the six requests", config_of(STEPS_2018)["requests"][4] == ["2017-09-07", "2018-08-30"])

    # fixtures added after a round of planted mutations of this file
    w = without(w0, lambda r: r[2] == CHINA and r[0] == "2018-06-07")
    gone = next(r for r in w0["rows"] if r[2] == CHINA and r[0] == "2018-06-07")
    for t in w["totals"]:
        if t[0] == "2018-06-07":
            t[2:] = [round(x - y, 1) for x, y in zip(t[2:], gone[4:])]
    idn = run(w, STEPS_2018)["identities"]
    check("China without a row is named even when the Total row agrees", not idn["total_row_breaks"]
          and idn["china_chain_breaks"] == ["2018-06-07: China has no row"])
    check("P3 is the four weeks 07-12 to 08-02", plateau_weeks(SETTINGS[DEFAULT])["P3"] ==
          ["2018-07-12", "2018-07-19", "2018-07-26", "2018-08-02"]
          and mv["china_exports"]["list_one"]["A"]["observed"]["post_n"] == 4)
    check("the two grids", GRIDS == {"from_2016": ("2016-01-07", "2018-02-01"), "from_2013": ("2013-09-05", "2018-02-01")}
          and fl["from_2013"]["windows"] == len(grid_between("2013-09-05", "2018-02-01")) - 7 + 1)
    check("B115-17 names the plateau week that is absent", "plateau week 2018-05-03 absent" in c1["B115-17"]["detail"])
    late = {"2018-08-23": wk["2018-08-30"], "2018-08-30": wk["2018-08-30"]}
    toks2 = fake_tokens("2018-08-23", "2018-08-30", late)
    k2 = toks2.index("08/30/2018(wk1)")
    try:
        parse_report(fake_html(toks2[:k2 + 1] + toks2[k2 + 12:]))
        check("parser raises on a week whose rows come before any marketing year", False)
    except ValueError:
        check("parser raises on a week whose rows come before any marketing year", True)
    check("plateau means follow their own setting", abs(one["plateau_means"]["A"]["P1"]["china_exports"] -
                                                         (1500000.0 + 4 * 20000.0) / 5) < 1e-6
          and abs(one["plateau_means"]["B"]["P1"]["china_exports"] - 20000.0) < 1e-6
          and abs(o["plateau_means"]["C"]["P2"]["china_exports"] - 60000.0) < 1e-6)
    check("table: the Total row's gross new sales", abs(r419["total_gross"] - sum(
        r[4] for r in w0["rows"] if r[0] == "2018-04-19")) < 0.5 and r419["total_gross"] != r419["total_exports"]
          and abs(r419["china_share_of_gross"] - 500.0 / r419["total_gross"]) < 1e-12)
    cn607 = next(r for r in w0["rows"] if r[2] == CHINA and r[0] == "2018-06-07")
    p607 = next(r for r in tb["outstanding_path"] if r["week"] == "2018-06-07")
    check("outstanding path reads Outstanding Sales", p607["china_outstanding"] == cn607[7] != cn607[8]
          and p607["china_exports"] == cn607[6] and p607["china_net"] == cn607[5])
    cy = tb["calendar_year_share"]["2015"]
    check("calendar-year share sums the weeks of that calendar year", abs(cy["china_exports"] - sum(
        r[6] for r in w0["rows"] if r[2] == CHINA and r[0][:4] == "2015")) < 0.5
          and cy["weeks"] == len([x for x in grid_between("2015-01-01", "2015-12-31")]))

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {count - len(fails)} of {count} checks hold")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.fetch:
        return fetch()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    steps = sorted(s["date"] for s in json.loads(STEPS_FILE.read_text(encoding="utf-8"))["steps"])
    o = run(data, steps)
    record = make_record(o, config_of(steps))
    show(o, record["criteria"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(public(record), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nrecord {OUT.relative_to(REPO)}")
    return 0 if all(c["passed"] is not False for c in record["criteria"] if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    raise SystemExit(main())
