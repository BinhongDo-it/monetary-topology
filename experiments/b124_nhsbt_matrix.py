"""B124: the NHSBT donor-zone by transplant-centre matrix, parsed and checked.

NHS Blood and Transplant answered a freedom of information request
(reference CAS-323843-M1Z2M9, 22 October 2026) with two tables of adult
elective liver transplants, donation zone (rows) by transplant centre
(columns), for four years running 20 March to 19 March, 2016/17 to 2019/20.
The National Liver Offering Scheme started on 20 March 2018 and changed DBD
allocation from zonal to national; DCD stayed zonal.

Cells below five are printed as "<5". They are read here as the interval
[1, 4], since zeros are printed as 0. Every total is therefore an interval.

The tables do not name the donor type. The request asked for DBD first and
DCD second; the known-answer check against Tables 14 and 15 of the 48-month
monitoring report settles which is which.

Run:  python experiments/b124_nhsbt_matrix.py [--selftest]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b124" / "nhsbt"
TABLES_PDF = RAW / "Elective Liver Transplants UK - CAS-323843-M1Z2M9.pdf"
TABLES_SHA = "6a4ae6b83981ec4a392f28899a4d17b752631a6276615c3847e6a7ae0b35538e"
OUT = ROOT / "results" / "b124_nhsbt_matrix.json"

CENTRES = ["Newcastle", "Leeds", "Cambridge", "Royal Free",
           "King’s College", "Birmingham", "Edinburgh"]
ROWS = CENTRES + ["Overseas"]
YEARS = ["2016/17", "2017/18", "2018/19", "2019/20"]
PERIOD = re.compile(r"^20 March (\d{4}) to 19 March (\d{4})$")
SUPPRESSED = "<5"

# Tables 14 and 15 of the NLOS 48-month monitoring report (pages 39 to 41),
# adult elective liver and liver/kidney transplants. The report starts at 2017/18.
PUBLISHED = {
    "DBD": {"2017/18": (635, 468, 167), "2018/19": (622, 134, 488), "2019/20": (607, 121, 486)},
    "DCD": {"2017/18": (186, 121, 65), "2018/19": (181, 107, 74), "2019/20": (170, 105, 65)},
}


def read_tokens(path):
    blob = path.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != TABLES_SHA:
        raise SystemExit(f"{path.name}: SHA-256 {sha} is not the registered file")
    doc = pymupdf.open(path)
    tokens = []
    for page in doc:
        tokens += [t.strip() for t in page.get_text().split("\n") if t.strip()]
    return tokens


def parse(tokens):
    """Return {table: {year: {row: [cell] * 7}}}; a cell is an int or "<5"."""
    tables, table, year, i = {}, None, None, 0
    while i < len(tokens):
        t = tokens[i]
        m = PERIOD.match(t)
        if t.startswith("Table "):
            table = t
            tables[table] = {}
            year = None
        elif m:
            year = f"{m.group(1)}/{m.group(2)[2:]}"
            tables[table][year] = {}
        elif year is not None and t in ROWS:
            cells = []
            for v in tokens[i + 1:i + 8]:
                if v == SUPPRESSED:
                    cells.append(SUPPRESSED)
                elif v.isdigit():
                    cells.append(int(v))
                else:
                    raise SystemExit(f"{table} {year} {t}: unexpected cell {v!r}")
            tables[table][year][t] = cells
            i += 7
        i += 1
    return tables


def bounds(cells):
    lo = sum(1 if c == SUPPRESSED else c for c in cells)
    hi = sum(4 if c == SUPPRESSED else c for c in cells)
    return lo, hi


def summarise(block):
    diag, off, allc = [], [], []
    for r, row in block.items():
        for j, c in enumerate(row):
            allc.append(c)
            (diag if r == CENTRES[j] else off).append(c)
    return {"total": bounds(allc), "zonal": bounds(diag), "non_zonal": bounds(off),
            "suppressed_cells": sum(c == SUPPRESSED for c in allc),
            "printed_below_five": [(r, CENTRES[j], c) for r, row in block.items()
                                   for j, c in enumerate(row)
                                   if isinstance(c, int) and 0 < c < 5]}


def check(summary, published):
    """For each published year, does every published count fall inside its interval."""
    rows = []
    for year, (tot, zon, non) in published.items():
        s = summary[year]
        for name, val in (("total", tot), ("zonal", zon), ("non_zonal", non)):
            lo, hi = s[name]
            rows.append({"year": year, "quantity": name, "published": val,
                         "interval": [lo, hi], "inside": lo <= val <= hi})
    return rows


# Tables 16 and 17 of the report (pages 43 and 44): N transplants per centre and year,
# the same population as Tables 14 and 15. Column order is CENTRES.
PUBLISHED_CENTRE_N = {
    "DBD": {"2017/18": [30, 108, 71, 84, 128, 133, 81],
            "2018/19": [22, 66, 65, 83, 143, 155, 88],
            "2019/20": [26, 79, 60, 91, 145, 154, 52]},
    "DCD": {"2017/18": [5, 26, 32, 13, 46, 52, 12],
            "2018/19": [3, 21, 40, 28, 38, 38, 13],
            "2019/20": [4, 21, 33, 37, 37, 33, 5]},
}


def column_bounds(block):
    return [bounds([row[j] for row in block.values()]) for j in range(len(CENTRES))]


def centre_check(tables):
    """Per centre and year: is the published N inside the matrix column interval,
    and by how much does it fall outside."""
    out = {}
    for t, label in (("Table 1", "DBD"), ("Table 2", "DCD")):
        rows = []
        for year, ns in PUBLISHED_CENTRE_N[label].items():
            for j, (n, (lo, hi)) in enumerate(zip(ns, column_bounds(tables[t][year]))):
                rows.append({"year": year, "centre": CENTRES[j], "published": n,
                             "interval": [lo, hi], "above": max(0, n - hi), "below": max(0, lo - n)})
        out[label] = rows
    return out


# Liver and kidney transplants inside the DBD totals of Table 14 (page 39).
DBD_LIVER_KIDNEY = {"2017/18": 20, "2018/19": 13, "2019/20": 14}


def liver_only_scope(summary):
    """If the FOI table counts liver-only transplants, some split of each year's
    liver and kidney transplants into zonal z and non-zonal k - z must bring all
    three published counts inside the matrix intervals. Print the feasible z."""
    out = {}
    for year, k in DBD_LIVER_KIDNEY.items():
        tot, zon, non = PUBLISHED["DBD"][year]
        s = summary[year]
        ok = [z for z in range(k + 1)
              if s["total"][0] <= tot - k <= s["total"][1]
              and s["zonal"][0] <= zon - z <= s["zonal"][1]
              and s["non_zonal"][0] <= non - (k - z) <= s["non_zonal"][1]]
        out[year] = {"liver_kidney": k, "feasible_zonal_liver_kidney": ok}
    return out


def build(tables):
    shape_ok = (sorted(tables) == ["Table 1", "Table 2"]
                and all(sorted(t) == YEARS for t in tables.values())
                and all(sorted(b) == sorted(ROWS) and all(len(r) == 7 for r in b.values())
                        for t in tables.values() for b in t.values()))
    summ = {t: {y: summarise(b) for y, b in tables[t].items()} for t in tables}
    assign = {"Table 1": "DBD", "Table 2": "DCD"}
    checks = {assign[t]: check(summ[t], PUBLISHED[assign[t]]) for t in tables}
    swapped = {assign[t]: check(summ[t], PUBLISHED["DCD" if assign[t] == "DBD" else "DBD"])
               for t in tables}
    crit = [
        {"name": "B124-N1", "kind": "instrument",
         "statement": "Both tables parse to four years, eight donor-zone rows and seven centre columns",
         "passed": shape_ok},
        {"name": "B124-N2", "kind": "known_answer",
         "statement": "Under the order DBD then DCD, every published total, zonal and non-zonal count "
                      "for 2017/18 to 2019/20 lies inside the interval read from the matrix",
         "passed": all(r["inside"] for v in checks.values() for r in v),
         "detail": {k: [r for r in v if not r["inside"]] for k, v in checks.items()}},
        {"name": "B124-N3", "kind": "known_answer",
         "statement": "The swapped order (DCD then DBD) fails the same check, so the order is identified",
         "passed": not all(r["inside"] for v in swapped.values() for r in v)},
    ]
    cc = centre_check(tables)
    crit.append({"name": "B124-N4", "kind": "known_answer",
                 "statement": "Every published per-centre N of Tables 16 and 17 for 2017/18 to 2019/20 "
                              "lies inside the matrix column interval",
                 "passed": all(r["above"] == 0 and r["below"] == 0 for v in cc.values() for r in v),
                 "detail": {k: [r for r in v if r["above"] or r["below"]] for k, v in cc.items()}})
    return summ, checks, crit


def selftest(tables):
    import copy
    bad = copy.deepcopy(tables)
    bad["Table 1"]["2018/19"]["Leeds"][1] += 40       # inflate one diagonal cell
    assert not build(bad)[2][1]["passed"], "N2 did not flip on a seeded count"
    bad = copy.deepcopy(tables)
    del bad["Table 2"]["2019/20"]["Overseas"]
    assert not build(bad)[2][0]["passed"], "N1 did not flip on a missing row"
    bad = copy.deepcopy(tables)
    bad["Table 2"]["2017/18"]["Leeds"][1] = 60           # a column far above Table 17's N
    assert not build(bad)[2][3]["passed"], "N4 did not flip on a seeded column"
    print("selftest: 3/3 seeds flip their flag")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    tables = parse(read_tokens(TABLES_PDF))
    if a.selftest:
        selftest(tables)
        return 0
    summ, checks, crit = build(tables)
    for t, label in (("Table 1", "DBD"), ("Table 2", "DCD")):
        print(f"== {t} ({label})")
        for y in YEARS:
            s = summ[t][y]
            print(f"  {y}  total {s['total']}  zonal {s['zonal']}  non-zonal {s['non_zonal']}"
                  f"  <5 cells {s['suppressed_cells']}  printed 1-4 {s['printed_below_five']}")
    for k, v in checks.items():
        for r in v:
            print(f"  {k} {r['year']} {r['quantity']:9s} published {r['published']:4d}"
                  f"  interval {r['interval']}  {'inside' if r['inside'] else 'OUTSIDE'}")
    for label, rows in centre_check(tables).items():
        for r in rows:
            flag = "inside" if not (r["above"] or r["below"]) else f"above {r['above']} below {r['below']}"
            print(f"  {label} {r['year']} {r['centre']:15s} N {r['published']:4d}  column {r['interval']}  {flag}")
    scope = liver_only_scope(summ["Table 1"])
    for y, v in scope.items():
        print(f"  liver-only scope {y}: {v['liver_kidney']} liver/kidney, zonal among them could be "
              f"{v['feasible_zonal_liver_kidney'] or 'none'}")
    for c in crit:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['statement']}")
    rec = {"diagnostics": {"dbd_liver_only_scope": scope, "centre_check": centre_check(tables)},"stage": "B124-N", "source": {"file": TABLES_PDF.name, "sha256": TABLES_SHA,
           "foi_reference": "CAS-323843-M1Z2M9", "response_date": "2026-10-22"},
           "config": {"suppressed_interval": [1, 4], "zonal": "row zone equals column centre",
                      "overseas_row": "counted as non-zonal"},
           "cells": tables, "summary": summ, "checks": checks, "criteria": crit}
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
