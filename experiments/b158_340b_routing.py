"""B158: 340B contract pharmacies. A state law reopens the class line only where its text reaches,
and the crossers route their registrations there.

The 340B ceiling price is open to covered entities; a contract pharmacy dispenses the drug bought at
that price to patients who carry commercial coverage. The contract pharmacy is the organisation that
crosses the line between the 340B price and the commercial price on the covered entity's behalf.
Arkansas Act 1103 of 2021 forbids a manufacturer to deny 340B pricing to an "Arkansas-based community
pharmacy"; its rule (Rule 123) defines that as a pharmacy licensed and located in the state and puts
no condition on where the covered entity sits. The station reads the registry of contract pharmacy
arrangements for what moved after that rule took effect, and against what.

Criteria (kind in brackets):
  B158-1 [instrument]   the cache holds every data row of the registry workbook; the history scope
  B158-2 [own_reading]  quarterly begins and terminations 2019Q1-2022Q4 (manufacturer restrictions
                        start 2020-07): does the closing side show in the registry at all
  B158-3 [own_reading]  out-of-state covered entities' new arrangements at Arkansas pharmacies, eight
                        quarters either side of Rule 123 (2022-09-30), with the top pharmacy each quarter
  B158-4 [own_reading]  the Rogers pharmacy that takes the jump: licensed 2020-03-23, registrations
                        before the rule date; the same entities at the chain's Texas central fill site
  B158-5 [own_reading]  twenty-two state laws by the reach of their text, before and after counts printed
  B158-6 [known_answer] year-end distinct pharmacy addresses against GAO-18-480 (about 1,300 in 2010,
                        nearly 20,000 in 2017)

What is read is registration: an arrangement a covered entity lists. Whether the manufacturer honoured
the 340B price on it is not in the registry.

usage:
  python -B experiments/b158_340b_routing.py              run, write results/b158_340b_routing.json
  python -B experiments/b158_340b_routing.py --selftest   planted errors, each flag must flip
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "org1"
WORKBOOK = RAW / "340B_ContractPharmacy_Daily_20261014_140816.xlsx"
CACHE = RAW / "opais_cp_20261014_slim.csv"
SIDECAR = RAW / "opais_cp_20261014_rowcount.json"
RECORD = ROOT / "results" / "b158_340b_routing.json"
SESSION = "B158"

SNAPSHOT_EXPORTED = "2026-10-14"
WINDOW = 8  # quarters either side of an effective date

KEEP = ["340B ID", "CE ID", "Program Type", "Participating", "CE Add Date", "CE Term Date",
        "Entity State", "Contract Begin Date", "Contract Termination Date", "Pharmacy Name",
        "Pharmacy Address 1", "Pharmacy City", "Pharmacy State", "Pharmacy Zip",
        "Pharmacy Comments", "Contract Comments", "Edit Date"]

# Arkansas. Statute effective by the default rule (91st day after recess); Rule 123 effective date as
# printed in the Arkansas Register. Not enjoined at any point (E.D. Ark. 2022-12-12; 8th Cir. 2024-03-12;
# certiorari denied 2024-12-09).
AR_STATUTE = "2021-07-28"
AR_RULE = "2022-09-30"

# The pharmacy that takes the Arkansas jump, and the chain's central fill site in Texas.
# Licence from the Arkansas State Board of Pharmacy roster, read 2026-10-17:
# "Walmart Pharmacy #10-5169", Retail Pharmacy License AR20927, issued 03/23/2020,
# 2252 North 8th Street, Suite A, Rogers, AR 72756.
ROGERS_KEY = "10-5169"
ROGERS_LICENSED = "2020-03-23"
SPRING_KEY = "10-2670"

# GAO-18-480: contract pharmacies "about 1,300 in 2010" and "nearly 20,000 in 2017".
GAO = {2010: 1300, 2017: 20000}

# State contract pharmacy laws: (state, effective date, reach of the protection, note).
# reach: "pharmacy" = text protects pharmacies by their location or licence, entity location open;
#        "entity"   = text or the controlling court reading confines it to in-state covered entities;
#        "open"     = text names neither.
# Effective dates read from the enacted bills, session laws and court records, 2026-10-15.
STATES = [
    ("AR", "2022-09-30", "pharmacy", "Act 1103; statute 2021-07-28, Rule 123 2022-09-30; never enjoined"),
    ("LA", "2023-08-01", "pharmacy", "Act 358; the pharmacy must serve patients physically in the state"),
    ("MS", "2024-07-01", "open", "HB 728"),
    ("MD", "2024-07-01", "open", "HB 1056"),
    ("WV", "2024-06-06", "open", "SB 325; preliminary injunction 2024-12-17"),
    ("MN", "2024-08-01", "entity", "HF 4757; the state concedes out-of-state pharmacies are not covered; sunset 2027-07-01"),
    ("MO", "2024-08-28", "entity", "SB 751; 8th Cir. 2026-07-01 reads both entity and pharmacy in the state"),
    ("NE", "2025-04-09", "open", "LB 168"),
    ("TN", "2025-05-05", "open", "SB 1414; reaches restrictions added after 2025-06-01"),
    ("UT", "2025-05-07", "entity", "SB 69; D. Utah 2025-11-19 reads entities and pharmacies in Utah"),
    ("VT", "2025-06-11", "pharmacy", "H.266; pharmacy licensed in Vermont"),
    ("HI", "2025-07-01", "open", "HB 712"),
    ("SD", "2025-07-01", "pharmacy", "SB 154; pharmacy licensed by the state board and serving residents"),
    ("ND", "2025-08-01", "open", "HB 1473; struck by D.N.D. 2026-04-27"),
    ("CO", "2025-08-06", "open", "SB25-071"),
    ("ME", "2025-09-24", "open", "P.L. 2025 c. 388 Part P"),
    ("OR", "2025-09-26", "entity", "HB 2385; covered entity in the state"),
    ("RI", "2025-10-01", "open", "S 0114 / H 5634"),
    ("OK", "2025-11-01", "pharmacy", "HB 2048; enjoined for the plaintiffs 2025-10-31"),
    ("NM", "2026-01-01", "open", "HB 78; FQHCs only"),
    ("WA", "2026-06-11", "pharmacy", "SB 5981; pharmacy licensed in Washington"),
    ("IL", "2026-08-07", "entity", "HB 2371; entity in Illinois"),
]
OPEN_LATE = "2024-01-01"  # open-text laws effective from here on: manufacturers' practice already in place

# State-to-verdict mapping for the three-state criteria (rule 11c). The third state carries no verdict.
MAPPING = [
    ("B158-3", "after window holds more out-of-state begins than the before window", True),
    ("B158-3", "it does not", False),
    ("B158-3", "a window reaches past the snapshot", None),
    ("B158-4", "no arrangement at the Rogers pharmacy between its licence and the rule date", True),
    ("B158-4", "one or more", False),
    ("B158-4", "no licence date on the roster", None),
    ("B158-5", "every state row printed with its reach; no row carries a verdict", True),
    ("B158-5", "a row missing", False),
]


# ---------------------------------------------------------------- data

def cell(v) -> str:
    if isinstance(v, dt.datetime):
        return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v).strip()


def build_cache(workbook=WORKBOOK, cache=CACHE, sidecar=SIDECAR) -> None:
    """Read the workbook once, write the slim CSV and the data-row count. Contacts are not carried."""
    import openpyxl
    wb = openpyxl.load_workbook(workbook, read_only=True)
    rows = wb.worksheets[0].iter_rows(values_only=True)
    header = None
    for r in rows:
        if r and r[0] == "340B ID":
            header = list(r)
            break
    idx = [header.index(k) for k in KEEP]
    n = 0
    part = cache.with_suffix(".partial")
    with part.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(KEEP)
        for r in rows:
            if r is None or all(v in (None, "") for v in r):
                continue
            w.writerow([cell(r[i]) for i in idx])
            n += 1
    part.replace(cache)
    sidecar.write_text(json.dumps({"sheet_data_rows": n, "workbook": workbook.name}, sort_keys=True) + "\n",
                       encoding="utf-8", newline="\n")


def count_sheet_rows(workbook=WORKBOOK, sidecar=SIDECAR) -> None:
    """Count the workbook's non-blank data rows without touching an existing cache."""
    import openpyxl
    wb = openpyxl.load_workbook(workbook, read_only=True)
    seen_header, n = False, 0
    for r in wb.worksheets[0].iter_rows(values_only=True):
        if not seen_header:
            seen_header = bool(r) and r[0] == "340B ID"
            continue
        if r is not None and not all(v in (None, "") for v in r):
            n += 1
    sidecar.write_text(json.dumps({"sheet_data_rows": n, "workbook": workbook.name}, sort_keys=True) + "\n",
                       encoding="utf-8", newline="\n")


def load_rows(cache=CACHE) -> list:
    with cache.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sheet_rows(sidecar=SIDECAR) -> int | None:
    if not sidecar.exists():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))["sheet_data_rows"]


# ---------------------------------------------------------------- helpers

def quarter(d: str) -> int:
    return int(d[:4]) * 4 + (int(d[5:7]) - 1) // 3


def qname(q: int) -> str:
    return f"{q // 4}Q{q % 4 + 1}"


def out_of_state(r) -> bool:
    return r["Entity State"] != r["Pharmacy State"]


def window_counts(rows, state, date, window=WINDOW, snapshot=SNAPSHOT_EXPORTED):
    """Out-of-state begins at pharmacies in `state`, per quarter, `window` either side of `date`."""
    q0 = quarter(date)
    tot, out, top = Counter(), Counter(), defaultdict(Counter)
    for r in rows:
        d = r["Contract Begin Date"]
        if not d or r["Pharmacy State"] != state:
            continue
        q = quarter(d)
        if q0 - window <= q < q0 + window:
            tot[q] += 1
            if out_of_state(r):
                out[q] += 1
                top[q][(r["Pharmacy Name"], r["Pharmacy City"])] += 1
    per_q = []
    for q in range(q0 - window, q0 + window):
        best = top[q].most_common(1)
        per_q.append({"quarter": qname(q), "begins": tot[q], "out_of_state": out[q],
                      "top_pharmacy": f"{best[0][0][0]} / {best[0][0][1]}" if best else "",
                      "top_pharmacy_n": best[0][1] if best else 0})
    before = sum(out[q] for q in range(q0 - window, q0))
    after = sum(out[q] for q in range(q0, q0 + window))
    inside = q0 + window - 1 <= quarter(snapshot)
    return {"effective": date, "quarter": qname(q0), "before": before, "after": after,
            "window_inside_snapshot": inside, "per_quarter": per_q}


# ---------------------------------------------------------------- criteria

def b158_1(rows, n_sheet):
    begins = [r["Contract Begin Date"] for r in rows if r["Contract Begin Date"]]
    terms = [r["Contract Termination Date"] for r in rows if r["Contract Termination Date"]]
    quarter_start = sum(1 for d in begins if d[5:7] in ("01", "04", "07", "10"))
    rep = {"cache_rows": len(rows), "sheet_data_rows": n_sheet,
           "earliest_begin": min(begins) if begins else "", "earliest_termination": min(terms) if terms else "",
           "begins": len(begins), "begins_in_quarter_start_months": quarter_start,
           "participating": dict(sorted(Counter(r["Participating"] for r in rows).items()))}
    passed = n_sheet is not None and len(rows) == n_sheet and bool(rep["earliest_termination"])
    return passed, rep


def b158_2(rows, first="2019-01-01", last="2022-12-31"):
    q_first, q_last = quarter(first), quarter(last)
    beg, ter = Counter(), Counter()
    for r in rows:
        b, t = r["Contract Begin Date"], r["Contract Termination Date"]
        if b and q_first <= quarter(b) <= q_last:
            beg[quarter(b)] += 1
        if t and q_first <= quarter(t) <= q_last:
            ter[quarter(t)] += 1
    table = [{"quarter": qname(q), "begins": beg[q], "terminations": ter[q]} for q in range(q_first, q_last + 1)]
    words = Counter()
    for r in rows:
        t = r["Contract Termination Date"]
        if t and q_first <= quarter(t) <= q_last and r["Contract Comments"]:
            words[r["Contract Comments"][:60]] += 1
    rep = {"quarters": table, "termination_comments": [{"comment": k, "n": v} for k, v in words.most_common(10)]}
    passed = len(table) == q_last - q_first + 1 and all(row["begins"] or row["terminations"] for row in table)
    return passed, rep


def b158_3(rows, date=AR_RULE, alt=AR_STATUTE):
    main = window_counts(rows, "AR", date)
    statute = window_counts(rows, "AR", alt)
    if not main["window_inside_snapshot"]:
        passed = None
    else:
        tops = [q["top_pharmacy"] for q in main["per_quarter"][WINDOW:] if q["out_of_state"]]
        passed = main["after"] > main["before"] and bool(tops) and all(tops)
    return passed, {"rule_123": main, "statute": statute}


def b158_4(rows, licensed=ROGERS_LICENSED, rule=AR_RULE):
    rogers = [r for r in rows if ROGERS_KEY in r["Pharmacy Name"]]
    first = min((r["Contract Begin Date"] for r in rogers if r["Contract Begin Date"]), default="")
    between = [r for r in rogers if r["Contract Begin Date"] and licensed and licensed <= r["Contract Begin Date"] < rule] \
        if licensed else None
    rogers_start = {}
    for r in rogers:
        d = r["Contract Begin Date"]
        if d and (r["CE ID"] not in rogers_start or d < rogers_start[r["CE ID"]]):
            rogers_start[r["CE ID"]] = d
    spring = defaultdict(list)
    for r in rows:
        if SPRING_KEY in r["Pharmacy Name"]:
            spring[r["CE ID"]].append(r)
    cells = Counter()
    for ce, d in rogers_start.items():
        if ce not in spring:
            cells["no Spring arrangement"] += 1
            continue
        ends = [x["Contract Termination Date"] for x in spring[ce]]
        if any(not e for e in ends):
            cells["Spring still active"] += 1
        elif max(ends) <= d:
            cells["Spring ended before or on the Rogers begin"] += 1
        else:
            cells["Spring ended after the Rogers begin"] += 1
    names = ["Spring still active", "Spring ended before or on the Rogers begin",
             "Spring ended after the Rogers begin", "no Spring arrangement"]
    rep = {"licensed": licensed, "rule": rule, "arrangements": len(rogers), "entities": len(rogers_start),
           "first_begin": first, "begins_between_licence_and_rule": None if between is None else len(between),
           "spring_cells": {k: cells[k] for k in names},
           "begins_by_quarter": dict(sorted(Counter(qname(quarter(r["Contract Begin Date"]))
                                                    for r in rogers if r["Contract Begin Date"]).items()))}
    if between is None:
        return None, rep
    printed = sum(rep["spring_cells"].values()) == len(rogers_start)
    return len(between) == 0 and printed and len(rogers_start) > 0, rep


def b158_5(rows, states=STATES):
    table = []
    for st, date, reach, note in states:
        w = window_counts(rows, st, date)
        late_open = reach == "open" and date >= OPEN_LATE
        table.append({"state": st, "effective": date, "reach": reach, "note": note,
                      "group": "open text, effective 2024 or later" if late_open else reach,
                      "before": w["before"], "after": w["after"],
                      "window_inside_snapshot": w["window_inside_snapshot"], "verdict": None})
    passed = len(table) == len(states) == 22 and all(t["reach"] in ("pharmacy", "entity", "open") for t in table) \
        and all(t["verdict"] is None for t in table)
    return passed, {"states": table}


def b158_6(rows, gao=GAO):
    def stock(year):
        d = f"{year}-12-31"
        keys = set()
        for r in rows:
            b, t = r["Contract Begin Date"], r["Contract Termination Date"]
            if b and b <= d and (not t or t > d):
                keys.add((r["Pharmacy Address 1"].upper(), r["Pharmacy Zip"][:5]))
        return len(keys)
    s2010, s2017 = stock(2010), stock(2017)
    rep = {"addresses_2010": s2010, "gao_2010": gao[2010], "addresses_2017": s2017, "gao_2017": gao[2017],
           "ratio_2017": f"{s2017 / gao[2017]:.3f}",
           "year_end_addresses": {y: stock(y) for y in (2015, 2016, 2019, 2022, 2023, 2024, 2025)}}
    return s2010 <= gao[2010] and s2017 > 0, rep


# ---------------------------------------------------------------- selftest

def fake(begin, term="", es="TX", ps="AR", name="SOME PHARMACY", ce="1", addr="1 MAIN", zipc="72000", comment=""):
    r = {k: "" for k in KEEP}
    r.update({"Contract Begin Date": begin, "Contract Termination Date": term, "Entity State": es,
              "Pharmacy State": ps, "Pharmacy Name": name, "CE ID": ce, "Pharmacy Address 1": addr,
              "Pharmacy Zip": zipc, "Contract Comments": comment, "Participating": "TRUE"})
    return r


def run_selftest(verbose=False):
    out = []

    def expect(cond, msg):
        out.append({"check": msg, "ok": bool(cond)})
        if verbose:
            print(("ok   " if cond else "FAIL ") + msg)

    base = [fake("2023-04-01", ce=str(i), name=f"WALMART PHARMACY {ROGERS_KEY}") for i in range(5)]
    base += [fake("2021-01-01", ce="9", es="AR"), fake("2016-10-03", "2016-12-01", ce="8")]
    # 1
    p, _ = b158_1(base, len(base))
    expect(p is True, "B158-1 passes when the cache holds every sheet row")
    p, _ = b158_1(base[1:], len(base))
    expect(p is False, "B158-1 fails when a row is missing from the cache")
    p, _ = b158_1(base, None)
    expect(p is False, "B158-1 fails without the sheet row count")
    # 2
    full = [fake(f"{y}-{m:02d}-01") for y in range(2019, 2023) for m in (1, 4, 7, 10)]
    p, _ = b158_2(full)
    expect(p is True, "B158-2 passes with every quarter present")
    p, _ = b158_2([r for r in full if not r["Contract Begin Date"].startswith("2020-07")])
    expect(p is False, "B158-2 fails when a quarter is empty")
    # 3
    jump = [fake("2021-01-01", ce="a")] + [fake("2023-04-01", ce=str(i), name="X") for i in range(4)]
    p, _ = b158_3(jump)
    expect(p is True, "B158-3 passes on a jump after the rule date")
    flat = [fake("2021-01-01", ce=str(i)) for i in range(4)] + [fake("2023-04-01", ce="z")]
    p, _ = b158_3(flat)
    expect(p is False, "B158-3 fails when the before window holds more")
    home = [fake("2021-01-01", ce="a")] + [fake("2023-04-01", ce=str(i), es="AR", name="X") for i in range(4)]
    p, _ = b158_3(home)
    expect(p is False, "B158-3 fails when the jump comes from in-state entities only")
    p, _ = b158_3(jump, date="2026-01-01")
    expect(p is None, "B158-3 carries no verdict when the window reaches past the snapshot")
    # 4
    p, _ = b158_4(base)
    expect(p is True, "B158-4 passes with no Rogers arrangement between licence and rule")
    early = base + [fake("2021-04-01", ce="77", name=f"WALMART PHARMACY {ROGERS_KEY}")]
    p, _ = b158_4(early)
    expect(p is False, "B158-4 fails on a Rogers arrangement before the rule date")
    p, _ = b158_4(base, licensed="")
    expect(p is None, "B158-4 carries no verdict without a licence date")
    p, rep = b158_4(base + [fake("2019-01-01", ce="0", name=f"CENTRAL FILL {SPRING_KEY}", ps="TX")])
    expect(rep["spring_cells"]["Spring still active"] == 1 and rep["spring_cells"]["no Spring arrangement"] == 4,
           "B158-4 places an entity holding both sites in the still-active cell")
    # 5
    p, _ = b158_5(base)
    expect(p is True, "B158-5 passes with all twenty-two states printed")
    p, _ = b158_5(base, STATES[1:])
    expect(p is False, "B158-5 fails when a state is missing")
    # 6
    p, _ = b158_6(base + [fake("2009-01-01", addr=f"{i} ST") for i in range(10)])
    expect(p is True, "B158-6 passes when the 2010 survivors are under the GAO count")
    ended = base + [fake("2009-01-01", addr="ACTIVE ST")] \
        + [fake("2009-01-01", "2009-06-30", addr=f"{i} ST") for i in range(1301)]
    p, _ = b158_6(ended)
    expect(p is True, "B158-6 leaves arrangements ended before the year end out of the stock")
    many = base + [fake("2009-01-01", addr=f"{i} ST") for i in range(1301)]
    p, _ = b158_6(many)
    expect(p is False, "B158-6 fails when 2010 survivors exceed the GAO count")
    # 11c mapping: the third state maps to no verdict
    expect(all(v is None for _c, s, v in MAPPING if "no licence" in s or "past the snapshot" in s),
           "every third state maps to no verdict")
    return out


def selftest() -> int:
    rows = run_selftest(verbose=True)
    bad = [r for r in rows if not r["ok"]]
    print(f"selftest: {len(rows)} checks, {len(bad)} failure(s)")
    return 1 if bad else 0


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    st_rows = run_selftest(verbose=False)
    print(f"selftest: {len(st_rows)} checks, {sum(not r['ok'] for r in st_rows)} failure(s)")
    if not CACHE.exists():
        print("building the cache from the workbook (about five minutes)")
        build_cache()
    elif not SIDECAR.exists():
        print("counting the workbook's data rows (about a minute and a half); the cache is left as it is")
        count_sheet_rows()
    rows = load_rows()
    p1, r1 = b158_1(rows, sheet_rows())
    p2, r2 = b158_2(rows)
    p3, r3 = b158_3(rows)
    p4, r4 = b158_4(rows)
    p5, r5 = b158_5(rows)
    p6, r6 = b158_6(rows)

    print(f"B158-1 cache {r1['cache_rows']} / sheet {r1['sheet_data_rows']}; earliest begin {r1['earliest_begin']}, "
          f"earliest termination {r1['earliest_termination']}; quarter-start begins "
          f"{r1['begins_in_quarter_start_months']} of {r1['begins']}")
    print("B158-2 " + "  ".join(f"{q['quarter']} {q['begins']}/{q['terminations']}" for q in r2["quarters"]))
    m = r3["rule_123"]
    print(f"B158-3 AR, Rule 123: before {m['before']}, after {m['after']}; statute date: before "
          f"{r3['statute']['before']}, after {r3['statute']['after']}")
    for q in m["per_quarter"]:
        print(f"   {q['quarter']} begins {q['begins']:5d} out-of-state {q['out_of_state']:5d}  "
              f"{q['top_pharmacy']} x{q['top_pharmacy_n']}")
    print(f"B158-4 licensed {r4['licensed']}, first begin {r4['first_begin']}, between licence and rule "
          f"{r4['begins_between_licence_and_rule']}; {r4['entities']} entities; {r4['spring_cells']}")
    for t in r5["states"]:
        print(f"B158-5 {t['state']} {t['effective']} {t['group']:38s} before {t['before']:5d} after {t['after']:5d}"
              f"{'' if t['window_inside_snapshot'] else '  (window past snapshot)'}")
    print(f"B158-6 2010 {r6['addresses_2010']} vs GAO {r6['gao_2010']}; 2017 {r6['addresses_2017']} vs GAO "
          f"{r6['gao_2017']} (ratio {r6['ratio_2017']})")

    groups = defaultdict(lambda: [0, 0, 0])
    for t in r5["states"]:
        g = groups[t["group"]]
        g[0] += 1
        g[1] += t["before"]
        g[2] += t["after"]
    crit = [
        {"name": "B158-1", "kind": "instrument", "passed": p1,
         "detail": f"Cache rows {r1['cache_rows']}, workbook data rows {r1['sheet_data_rows']}. Earliest begin "
                   f"{r1['earliest_begin']}, earliest termination {r1['earliest_termination']}: arrangements that "
                   "ended before that date are not in the export, so stocks before 2016 count survivors only. "
                   f"{r1['begins_in_quarter_start_months']} of {r1['begins']} begin dates fall in January, April, "
                   "July or October; the registry moves in quarterly windows."},
        {"name": "B158-2", "kind": "own_reading", "passed": p2,
         "detail": "Begins/terminations by quarter: "
                   + ", ".join(f"{q['quarter']} {q['begins']}/{q['terminations']}" for q in r2["quarters"])
                   + ". Manufacturer restrictions start in 2020-07; terminations show no cluster after it and "
                   "begins stay high. A restriction cuts the price, not the listing, so the registry does not "
                   "record the closing side. No termination reason column exists; the comment field names none."},
        {"name": "B158-3", "kind": "own_reading", "passed": p3,
         "detail": f"Arkansas pharmacies, new arrangements from covered entities in other states: "
                   f"{m['before']} in the eight quarters before Rule 123 (effective {AR_RULE}), {m['after']} in "
                   f"the eight from it. Around the statute date ({AR_STATUTE}): {r3['statute']['before']} and "
                   f"{r3['statute']['after']}. Top pharmacy in the quarters after: "
                   + "; ".join(f"{q['quarter']} {q['top_pharmacy']} x{q['top_pharmacy_n']}"
                               for q in m["per_quarter"][WINDOW:] if q["out_of_state"])
                   + ". These are registrations; whether manufacturers honoured the price on them is not read."},
        {"name": "B158-4", "kind": "own_reading", "passed": p4,
         "detail": f"The Rogers pharmacy ({ROGERS_KEY}) holds Arkansas retail licence AR20927 issued "
                   f"{ROGERS_LICENSED}. Arrangements naming it between that date and {AR_RULE}: "
                   f"{r4['begins_between_licence_and_rule']}; first begin {r4['first_begin']}; "
                   f"{r4['arrangements']} arrangements from {r4['entities']} entities. The same entities at the "
                   f"chain's Texas central fill site ({SPRING_KEY}): "
                   + "; ".join(f"{k} {v}" for k, v in r4["spring_cells"].items())
                   + ". The jump lines up with the rule date, not with the licence."},
        {"name": "B158-5", "kind": "own_reading", "passed": p5,
         "detail": "Twenty-two laws, out-of-state begins eight quarters before and after the effective date, by "
                   "the reach of the text: "
                   + "; ".join(f"{g}: {v[0]} states, {v[1]} before, {v[2]} after" for g, v in sorted(groups.items()))
                   + ". Rows: " + "; ".join(f"{t['state']} {t['before']}->{t['after']}" for t in r5["states"])
                   + ". No row carries a verdict. Open-text laws effective 2024 or later meet a manufacturer "
                   "practice that already required both entity and pharmacy in the state."},
        {"name": "B158-6", "kind": "known_answer", "passed": p6,
         "detail": f"Distinct pharmacy addresses active at year end: 2010 {r6['addresses_2010']} (GAO about "
                   f"{GAO[2010]}; survivors only, so at most that); 2017 {r6['addresses_2017']} (GAO nearly "
                   f"{GAO[2017]}, ratio {r6['ratio_2017']})."},
    ]
    record = {
        "stage": "B158",
        "title": "340B contract pharmacies: a state law reopens the class line where its text reaches",
        "config": {"workbook": WORKBOOK.name, "snapshot_exported": SNAPSHOT_EXPORTED, "window_quarters": WINDOW,
                   "ar_rule_123": AR_RULE, "ar_statute": AR_STATUTE, "rogers_licensed": ROGERS_LICENSED,
                   "open_late_from": OPEN_LATE},
        "criteria": crit,
        "mapping_11c": [{"criterion": c, "state": s, "verdict": v} for c, s, v in MAPPING],
        "selftest": st_rows,
        "B158_1": r1, "B158_2": r2, "B158_3": r3, "B158_4": r4, "B158_5": r5, "B158_6": r6,
    }
    text = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        from safe_write import create, rewrite
        if RECORD.exists():
            rewrite(RECORD, "B158_record", lambda _t: text, session=SESSION)
        else:
            create(RECORD, "B158_record", text, session=SESSION)
        print(f"wrote {RECORD.name}")
    print("criteria:", {c["name"]: c["passed"] for c in crit})
    return 1 if any(c["passed"] is False for c in crit) else 0


if __name__ == "__main__":
    sys.exit(main())
