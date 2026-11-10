"""B150: Singapore foreign worker levy tables, read as prices written on (class, position).

Object.  Classes: Work Permit higher-skilled (HS), Work Permit basic-skilled (BS),
construction's unskilled class (U), and S Pass (SP).  Positions: the levy tiers T1/T2/T3
in services and manufacturing (a tier is a slot fixed by the employer's own workforce
mix), the source groups and off-site row in construction, the source groups in process,
and one cell in marine shipyard.  Price: monthly levy per worker, SGD.

Every number below is copied from a page-text snapshot in data/raw/b150/ (the
manifest there carries URL, snapshot time, the page's own "Last updated" date and a
SHA-256 of the stored bytes) or from the Ministry's guide "How to calculate your quota
and levy bill" (Updated 1 July 2026), which was read and not stored.  Each constant
names its source row.

Criteria (kind in brackets):
  L3-1 [instrument]   printed daily levy == ceil_cent(monthly * 12 / 365), every cell
  L3-2 [bookkeeping]  the guide's three worked levy bills recomputed from its own steps,
                      and the guide's rate table compared cell by cell with the pages;
                      flag: every row present and read on both sides (reconciled); the rows
                      that disagree are errors in the guide itself, and their list, computed
                      from the rows, is the check's output (ruled 2026-10-27)
  L3-3 [own_reading]  class values per position, distinct values per table; flag: at every
                      position HS and BS are both written and differ
  L3-4 [own_reading]  every square, in SGD and in log, with its floor and multiple
  L3-5 [own_reading]  services and manufacturing: the set of increments in the monthly
                      bill from hiring one more worker of each class, over a grid of
                      workforce mixes; flag: the S Pass set reaches above 650
  L3-6 [known_answer] the announced 2028 tables, read on the month they take effect
                      (event pending: passed is None)
  L3-7 [bookkeeping]  snapshot coverage table and SHA-256 recomputation; every file in the
                      snapshot folder, any extension, must be listed; each page says how much
                      of its stored text is word for word (full / partial / summary)

Run:  python -B experiments/b150_levy_table.py            (writes results/b150_levy_table.json)
      python -B experiments/b150_levy_table.py --selftest (planted errors, each must flip)
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "data" / "raw" / "b150"
RECORD = ROOT / "results" / "b150_levy_table.json"
SESSION = "T9_LABOR3"

# ---------------------------------------------------------------------------
# Rate tables.  (sector, position, class) -> (monthly SGD or None, printed daily or None, source)
# ---------------------------------------------------------------------------
S, M, C, P, MR = "services", "manufacturing", "construction", "process", "marine"

CELLS = {
    (S, "T1", "HS"): (300, "9.87", "services snapshot, row 'Tier 1 (up to 10%)', Higher-skilled"),
    (S, "T1", "BS"): (450, "14.80", "services snapshot, row 'Tier 1 (up to 10%)', Basic-skilled"),
    (S, "T2", "HS"): (400, "13.16", "services snapshot, row 'Tier 2 (above 10% to 25%)', Higher-skilled"),
    (S, "T2", "BS"): (600, "19.73", "services snapshot, row 'Tier 2 (above 10% to 25%)', Basic-skilled"),
    (S, "T3", "HS"): (600, "19.73", "services snapshot, row 'Tier 3 (above 25% to 35%)', Higher-skilled"),
    (S, "T3", "BS"): (800, "26.31", "services snapshot, row 'Tier 3 (above 25% to 35%)', Basic-skilled"),
    (M, "T1", "HS"): (250, "8.22", "manufacturing snapshot, row 'Basic Tier / Tier 1: up to 25%', Higher-skilled"),
    (M, "T1", "BS"): (370, "12.17", "manufacturing snapshot, row 'Basic Tier / Tier 1: up to 25%', Basic-skilled"),
    (M, "T2", "HS"): (350, "11.51", "manufacturing snapshot, row 'Tier 2: above 25% to 50%', Higher-skilled"),
    (M, "T2", "BS"): (470, "15.46", "manufacturing snapshot, row 'Tier 2: above 25% to 50%', Basic-skilled"),
    (M, "T3", "HS"): (550, "18.09", "manufacturing snapshot, row 'Tier 3: above 50% to 60%', Higher-skilled"),
    (M, "T3", "BS"): (650, "21.37", "manufacturing snapshot, row 'Tier 3: above 50% to 60%', Basic-skilled"),
    (C, "NTS", "HS"): (500, "16.44", "construction snapshot, row 'NTS - Higher-skilled'"),
    (C, "NTS", "BS"): (900, "29.59", "construction snapshot, row 'NTS - Basic-skilled'"),
    (C, "MNP", "HS"): (300, "9.87", "construction snapshot, row 'Malaysia, NAS, PRC - Higher-skilled'"),
    (C, "MNP", "BS"): (700, "23.02", "construction snapshot, row 'Malaysia, NAS, PRC - Basic-skilled'"),
    (C, "OFF", "HS"): (250, "8.22", "construction snapshot, row 'Off-site Construction - Higher-skilled'"),
    (C, "OFF", "BS"): (370, "12.17", "construction snapshot, row 'Off-site Construction - Basic-skilled'"),
    (C, "NTS", "U"): (900, None, "construction snapshot, sentence '$900, regardless of their source country/region'"),
    (C, "MNP", "U"): (900, None, "construction snapshot, sentence '$900, regardless of their source country/region'"),
    (C, "OFF", "U"): (None, None, "construction snapshot: the page does not say whether Unskilled applies off-site"),
    (P, "NTS", "HS"): (300, "9.87", "process snapshot, row 'NTS - Higher-skilled'"),
    (P, "NTS", "BS"): (650, "21.37", "process snapshot, row 'NTS - Basic-skilled'"),
    (P, "MNP", "HS"): (200, "6.58", "process snapshot, row 'Malaysia, NAS, PRC - Higher-skilled'"),
    (P, "MNP", "BS"): (450, "14.80", "process snapshot, row 'Malaysia, NAS, PRC - Basic-skilled'"),
    (MR, "ONE", "HS"): (350, "11.51", "marine snapshot, row 'Higher-skilled'"),
    (MR, "ONE", "BS"): (500, "16.44", "marine snapshot, row 'Basic-skilled'"),
}
POSITIONS = {S: ["T1", "T2", "T3"], M: ["T1", "T2", "T3"], C: ["MNP", "NTS", "OFF"],
             P: ["MNP", "NTS"], MR: ["ONE"]}

SPASS_CURRENT = (650, "21.37", "spass_levy_quota snapshot, 'harmonised to $650 across all sectors and levy tiers'")
SPASS_PREVIOUS = {  # before 2025-09-01; spass_changes snapshot
    "services Tier 1 (up to 10%)": 550,
    "other sectors Tier 1 (up to 10%)": 550,
    "other sectors Tier 2 (above 10% to 15%)": 650,
}

# Guide p.5-6 rate table: (sector, position, class) -> monthly
GUIDE_RATES = {
    (M, "T1", "HS"): 250, (M, "T1", "BS"): 370, (M, "T2", "HS"): 350, (M, "T2", "BS"): 470,
    (M, "T3", "HS"): 550, (M, "T3", "BS"): 650,
    (S, "T1", "HS"): 300, (S, "T1", "BS"): 450, (S, "T2", "HS"): 400, (S, "T2", "BS"): 600,
    (S, "T3", "HS"): 600, (S, "T3", "BS"): 800,
    (C, "MNP", "HS"): 300, (C, "MNP", "BS"): 700, (C, "NTS", "HS"): 500, (C, "NTS", "BS"): 900,
    (C, "OFF", "HS"): 250, (C, "OFF", "BS"): 370,
    (P, "MNP", "HS"): 200, (P, "MNP", "BS"): 450, (P, "NTS", "HS"): 300, (P, "NTS", "BS"): 650,
    (MR, "ONE", "HS"): 300, (MR, "ONE", "BS"): 500,
    (S, "ALL", "SP"): 650, (M, "ALL", "SP"): 650,
}

# Guide Step 1 multipliers (p.6) and Step 3 / Step 5 shares (p.9, p.11), in integer form.
# max MWs = floor(LQS * mult); S Pass <= floor(spq% * W); T1 = floor(a% * W); T2 = floor(b% * W) - T1.
TIER_RULES = {
    S: {"mult_num": 538462, "mult_den": 1000000, "a": 10, "b": 25, "spq": 10},
    M: {"mult_num": 3, "mult_den": 2, "a": 25, "b": 50, "spq": 15},
}
SP_RATE = 650

# Guide worked examples.  hs/bs counts; all Malaysian/PRC, which carry the same tiered rate.
EXAMPLES = [
    {"id": "p12 factory", "sector": M, "lqs": 25, "sp": 6, "hs": 8, "bs": 17,
     "printed_counts": (14, 14, 3), "printed_tier": (5900, 6580, 1950), "printed_total": 14430},
    {"id": "p14 cafe", "sector": S, "lqs": 7, "sp": 0, "hs": 3, "bs": 0,
     "printed_counts": (1, 1, 1), "printed_tier": (300, 400, 600), "printed_total": 1300},
    {"id": "p15 factory", "sector": M, "lqs": 20, "sp": 6, "hs": 5, "bs": 17,
     "printed_counts": (12, 12, 4), "printed_tier": (5520, 5160, 2600), "printed_total": 13280},
]
COMBINED = {"id": "p15 cafe + factory", "parts": ["p14 cafe", "p15 factory"], "printed_total": 14580}

# Announced 2028 changes (page sentences).  Merged tier boundaries are not written on any page.
ANNOUNCED_2028 = {
    S: {("M", "HS"): 400, ("M", "BS"): 600},
    M: {("M", "HS"): 300, ("M", "BS"): 470},
    P: {("MNP", "BS"): 600, ("NTS", "BS"): 800},
    MR: {("ONE", "BS"): 600},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def f4(x: float) -> str:
    return f"{x:+.4f}"


def ceil_cent(monthly: int) -> int:
    """Daily levy in cents: (monthly x 12) / 365 rounded up to the cent, exact integer arithmetic."""
    return -(-monthly * 1200 // 365)


def cents(s: str) -> int:
    whole, _, frac = s.partition(".")
    return int(whole) * 100 + int((frac + "00")[:2])


def table_of(cells, sector):
    """{position: {class: monthly}} for one sector, HS and BS only."""
    out = {}
    for pos in POSITIONS[sector]:
        out[pos] = {cls: cells.get((sector, pos, cls), (None,))[0] for cls in ("HS", "BS")}
    return out


def tables_2028(cells):
    t = {}
    for sector in (S, M):
        cur = table_of(cells, sector)
        new = {"M": {"HS": ANNOUNCED_2028[sector][("M", "HS")], "BS": ANNOUNCED_2028[sector][("M", "BS")]},
               "T3": dict(cur["T3"])}
        t[sector] = new
    pr = table_of(cells, P)
    for (pos, cls), v in ANNOUNCED_2028[P].items():
        pr[pos] = dict(pr[pos]); pr[pos][cls] = v
    t[P] = pr
    mr = table_of(cells, MR)
    mr["ONE"] = dict(mr["ONE"]); mr["ONE"]["BS"] = ANNOUNCED_2028[MR][("ONE", "BS")]
    t[MR] = mr
    return t

# ---------------------------------------------------------------------------
# 11c mapping
# ---------------------------------------------------------------------------
MAPPING = [
    ("L3-1", "printed daily equals ceil_cent", "match"),
    ("L3-1", "printed daily differs", "mismatch, flag False"),
    ("L3-1", "no daily printed (Unskilled) or no monthly", None),
    ("L3-2", "row read on both sides and agrees", "agree count"),
    ("L3-2", "a row read on both sides disagrees", "listed as an error in the guide; the list is the output, flag unaffected"),
    ("L3-2", "a row is missing", "flag False"),
    ("L3-3", "a position writes two distinct class values", "counted"),
    ("L3-3", "a position writes one value, or a class value is missing", "flag False"),
    ("L3-2", "guide lacks the input", None),
    ("L3-4", "composition exactly zero", "zero"),
    ("L3-4", "composition nonzero", "nonzero, multiple of floor"),
    ("L3-4", "both compositions nonzero, same sign", "read sign"),
    ("L3-4", "compositions of opposite sign", None),
    ("L3-4", "one composition zero", None),
    ("L3-4", "both compositions zero", None),
    ("L3-4", "a cell of a square missing, or b1 from the cells differs from the basis", "flag False"),
    ("L3-5", "S Pass max increment > 650 at every knob point", True),
    ("L3-5", "S Pass max increment == 650 at every knob point", False),
    ("L3-5", "knob points disagree", None),
    ("L3-6", "event not yet in effect", None),
    ("L3-6", "in effect, every cell as announced", True),
    ("L3-6", "in effect, some cell differs", False),
    ("L3-6", "2028-12-31 passed and still not in effect ('announcement not carried out')", None),
]
UNDECIDED = {("L3-1", "no daily printed (Unskilled) or no monthly"), ("L3-2", "guide lacks the input"),
             ("L3-4", "compositions of opposite sign"), ("L3-4", "one composition zero"),
             ("L3-4", "both compositions zero"), ("L3-5", "knob points disagree"),
             ("L3-6", "event not yet in effect"),
             ("L3-6", "2028-12-31 passed and still not in effect ('announcement not carried out')")}


def mapping_ok() -> bool:
    return all((m[2] is None) == ((m[0], m[1]) in UNDECIDED) for m in MAPPING) and \
        all(any((m[0], m[1]) == u for m in MAPPING) for u in UNDECIDED)

# ---------------------------------------------------------------------------
# L3-1
# ---------------------------------------------------------------------------

def l3_1(cells, spass=SPASS_CURRENT):
    rows = []
    items = sorted(cells.items()) + [(("spass", "ALL", "SP"), spass)]
    for key, (monthly, daily, _src) in items:
        if monthly is None or daily is None:
            rows.append({"cell": "/".join(key), "monthly": monthly, "printed": daily, "state": "no_input"})
            continue
        calc = ceil_cent(monthly)
        pr = cents(daily)
        rows.append({"cell": "/".join(key), "monthly": monthly, "printed": daily,
                     "computed": f"{calc // 100}.{calc % 100:02d}", "diff_cents": pr - calc,
                     "state": "match" if pr == calc else "mismatch"})
    read = [r for r in rows if r["state"] != "no_input"]
    passed = bool(read) and all(r["state"] == "match" for r in read)
    return passed, rows

# ---------------------------------------------------------------------------
# L3-2
# ---------------------------------------------------------------------------

def allocate(n_sp, n_hs, n_bs, t1, t2, sp_in_tiers=True):
    """Fill tiers in the guide's order (1st S Pass, 2nd HS, 3rd BS).  Returns per-tier counts by class."""
    queue = (["SP"] * n_sp if sp_in_tiers else []) + ["HS"] * n_hs + ["BS"] * n_bs
    caps = [t1, t2]
    tiers = [[], [], []]
    k = 0
    for w in queue:
        while k < 2 and len(tiers[k]) >= max(caps[k], 0):
            k += 1
        tiers[k].append(w)
    extra_sp = 0 if sp_in_tiers else n_sp
    return tiers, extra_sp


def tier_fill(seq, t1, t2):
    """Same fill as allocate(), by counts: seq is [(class, n)] in the guide's order; tiers 1 and 2
    hold at most max(t1, 0) and max(t2, 0) workers, the rest go to tier 3.  Returns three
    {class: count} dicts.  Arithmetic only, so the L3-5 grid can cover the whole quota region."""
    room = [max(t1, 0), max(t2, 0), None]
    out = [{}, {}, {}]
    k = 0
    for cls, n in seq:
        while n > 0:
            while k < 2 and room[k] == 0:
                k += 1
            take = n if room[k] is None else min(n, room[k])
            out[k][cls] = out[k].get(cls, 0) + take
            if room[k] is not None:
                room[k] -= take
            n -= take
    return out


def bill(sector, lqs2, n_sp, n_hs, n_bs, rates, sp_in_tiers=True):
    """lqs2 = 2 x LQS count (integer).  Returns (counts, per-tier levy, total)."""
    r = TIER_RULES[sector]
    w2 = lqs2 + 2 * (n_sp + n_hs + n_bs)
    t1 = (r["a"] * w2) // 200
    t2 = (r["b"] * w2) // 200 - t1
    seq = ([("SP", n_sp)] if sp_in_tiers else []) + [("HS", n_hs), ("BS", n_bs)]
    tiers = tier_fill(seq, t1, t2)
    extra_sp = 0 if sp_in_tiers else n_sp
    tiername = ["T1", "T2", "T3"]
    per = []
    for i, members in enumerate(tiers):
        s = 0
        for w, n in members.items():
            s += n * (SP_RATE if w == "SP" else rates[(sector, tiername[i], w)])
        per.append(s)
    total = sum(per) + extra_sp * SP_RATE
    return tuple(sum(t.values()) for t in tiers), tuple(per), total


def l3_2(guide_rates, page_cells, examples=EXAMPLES, combined=COMBINED, drop=None):
    rows = []
    for key in sorted(guide_rates):
        sector, pos, cls = key
        if cls == "SP":
            page = SPASS_CURRENT[0]
        else:
            page = page_cells.get(key, (None,))[0]
        g = guide_rates[key]
        if g is None or page is None:
            st = "no_input"
        else:
            st = "agree" if g == page else "disagree"
        rows.append({"row": "rate " + "/".join(key), "guide": g, "page": page, "state": st,
                     "diff": None if st == "no_input" else page - g})
    totals = {}
    for ex in examples:
        counts, per, total = bill(ex["sector"], 2 * ex["lqs"], ex["sp"], ex["hs"], ex["bs"], guide_rates)
        totals[ex["id"]] = total
        for i in range(3):
            rows.append({"row": f"{ex['id']} T{i+1} count", "computed": counts[i], "printed": ex["printed_counts"][i],
                         "state": "agree" if counts[i] == ex["printed_counts"][i] else "disagree",
                         "diff": ex["printed_counts"][i] - counts[i]})
            rows.append({"row": f"{ex['id']} T{i+1} levy", "computed": per[i], "printed": ex["printed_tier"][i],
                         "state": "agree" if per[i] == ex["printed_tier"][i] else "disagree",
                         "diff": ex["printed_tier"][i] - per[i]})
        rows.append({"row": f"{ex['id']} total", "computed": total, "printed": ex["printed_total"],
                     "state": "agree" if total == ex["printed_total"] else "disagree",
                     "diff": ex["printed_total"] - total})
    ct = sum(totals.get(p, 0) for p in combined["parts"])
    rows.append({"row": combined["id"] + " total", "computed": ct, "printed": combined["printed_total"],
                 "state": "agree" if ct == combined["printed_total"] else "disagree",
                 "diff": combined["printed_total"] - ct})
    if drop is not None:
        rows = [r for i, r in enumerate(rows) if i != drop]
    expected = len(guide_rates) + 7 * len(examples) + 1
    listed = {r["row"] for r in rows}
    want = {"rate " + "/".join(k) for k in guide_rates} | \
           {f"{e['id']} T{i} {w}" for e in examples for i in (1, 2, 3) for w in ("count", "levy")} | \
           {f"{e['id']} total" for e in examples} | {combined["id"] + " total"}
    mismatches = [r for r in rows if r["state"] == "disagree"]
    # Bookkeeping flag (ruled 2026-10-27): every row present, and every row read on both sides
    # and reconciled.  A row that disagrees is an error in the guide, the source document, and
    # goes on the list, which is this criterion's output; it does not move the flag.  A row
    # missing makes the flag False; a row the guide gives no input for takes no verdict (None).
    if len(rows) != expected or listed != want:
        passed = False
    elif any(r["state"] == "no_input" for r in rows):
        passed = None
    else:
        passed = all(r["state"] in ("agree", "disagree") for r in rows)
    return passed, rows, mismatches

# ---------------------------------------------------------------------------
# L3-3
# ---------------------------------------------------------------------------

def l3_3(cells):
    per_pos = {}
    distinct = {}
    complete = True
    for sector in (S, M, C, P, MR):
        vals = []
        for pos in POSITIONS[sector]:
            row = {}
            for cls in ("HS", "BS", "U"):
                if (sector, pos, cls) in cells:
                    row[cls] = cells[(sector, pos, cls)][0]
            per_pos[f"{sector}/{pos}"] = row
            if row.get("HS") is None or row.get("BS") is None:
                complete = False
            vals += [v for v in row.values() if v is not None]
        distinct[sector] = {"cells": len(vals), "distinct": len(set(vals)), "values": sorted(set(vals))}
    allwp = sorted({v[0] for v in cells.values() if v[0] is not None})
    # Class values written at each position, counted from the table (None excluded).
    classes_at = {p: sum(v is not None for v in row.values()) for p, row in per_pos.items()}
    distinct_at = {p: len({v for v in row.values() if v is not None}) for p, row in per_pos.items()}
    hs_bs_differ = sorted(p for p, row in per_pos.items()
                          if row.get("HS") is not None and row.get("BS") is not None and row["HS"] != row["BS"])
    not_two = sorted(p for p in per_pos if p not in hs_bs_differ)
    # Flag: every position present, and at every position HS and BS are both written and differ.
    passed = complete and len(per_pos) == sum(len(v) for v in POSITIONS.values()) and not not_two
    return passed, {"per_position": per_pos, "per_table": distinct,
                    "classes_written_at_position": classes_at, "distinct_values_at_position": distinct_at,
                    "positions": len(per_pos), "positions_hs_bs_differ": len(hs_bs_differ),
                    "positions_hs_bs_not_two_values": not_two,
                    "all_work_permit_distinct": len(allwp), "all_work_permit_values": allwp,
                    "spass_current": SPASS_CURRENT[0], "spass_previous": SPASS_PREVIOUS,
                    "spass_previous_distinct": len(set(SPASS_PREVIOUS.values()))}

# ---------------------------------------------------------------------------
# L3-4
# ---------------------------------------------------------------------------

def square(name, a, b):
    """a, b: {HS, BS} at two positions.  Sign convention (BS - HS)@a - (BS - HS)@b.

    A square with a missing or non-positive cell is returned in state 'missing'
    (no arithmetic), so the L3-4 flag can read it instead of the run crashing."""
    hs_a, bs_a, hs_b, bs_b = a.get("HS"), a.get("BS"), b.get("HS"), b.get("BS")
    if not all(isinstance(v, int) and v > 0 for v in (hs_a, bs_a, hs_b, bs_b)):
        return {"square": name, "cells": [hs_a, bs_a, hs_b, bs_b], "sgd_state": "missing",
                "log_state": "missing", "sign_state": "missing", "sign": None,
                "rival_additive_holds": None, "rival_multiplicative_holds": None}
    d = (bs_a - hs_a) - (bs_b - hs_b)
    log_zero = bs_a * hs_b == bs_b * hs_a
    lg = 0.0 if log_zero else math.log(bs_a / hs_a) - math.log(bs_b / hs_b)
    x = min(hs_a, bs_a, hs_b, bs_b)
    lfloor = math.log((x + 1) / x)
    sd = 0 if d == 0 else (1 if d > 0 else -1)
    sl = 0 if log_zero else (1 if lg > 0 else -1)
    if sd == 0 and sl == 0:
        sign, state = None, "both compositions zero"
    elif sd == 0 or sl == 0:
        sign, state = None, "one composition zero"
    elif sd != sl:
        sign, state = None, "compositions of opposite sign"
    else:
        sign, state = ("+" if sd > 0 else "-"), "both compositions nonzero, same sign"
    return {"square": name, "sgd": d, "sgd_floor": 1, "sgd_multiple": abs(d),
            "sgd_state": "zero" if d == 0 else "nonzero",
            "log": f4(lg), "log_floor": f"{lfloor:.4f}", "log_multiple": f"{abs(lg) / lfloor:.1f}",
            "log_state": "zero" if log_zero else "nonzero", "sign_state": state, "sign": sign,
            "rival_additive_holds": d == 0, "rival_multiplicative_holds": log_zero}


def enumerate_squares(tables, sets):
    """sets: list of (label, sector, pairs or None for all pairs)."""
    out = []
    for label, sector, pairs in sets:
        t = tables[sector]
        pp = pairs if pairs is not None else list(itertools.combinations(list(t.keys()), 2))
        for i, j in pp:
            out.append(dict(square(f"{sector} {i} vs {j}", t[i], t[j]), set=label))
    return out


SQUARE_TABLES = (S, M, C, P)  # tables with two or more positions; marine has one


def b1_of(table):
    """Independent squares of one table from its own cells: the class x position graph has
    an edge for every printed (position, class) value; b1 = E - V + 1 on that graph."""
    pos = [p for p in table if any(isinstance(v, int) for v in table[p].values())]
    cls = sorted({c for p in table for c, v in table[p].items() if isinstance(v, int)})
    e = sum(1 for p in table for v in table[p].values() if isinstance(v, int))
    v = len(pos) + len(cls)
    return e - v + 1 if v else 0


def l3_4(cells):
    tables = {s: table_of(cells, s) for s in (S, M, C, P, MR)}
    # Every pair of positions within a table.  Construction and process positions are
    # source groups (and the off-site row), as in the design notation; the square between
    # two on-site source groups is a main square, dependent on the two against off-site.
    main = enumerate_squares(tables, [("main", s, None) for s in SQUARE_TABLES])
    # Unskilled: (U - HS) and (U - BS) between the two on-site source groups
    u = []
    for other in ("HS", "BS"):
        a = {"HS": cells.get((C, "MNP", other), (None,))[0], "BS": cells.get((C, "MNP", "U"), (None,))[0]}
        b = {"HS": cells.get((C, "NTS", other), (None,))[0], "BS": cells.get((C, "NTS", "U"), (None,))[0]}
        u.append(dict(square(f"construction U vs {other}, MNP vs NTS", a, b), set="unskilled"))
    # Cross-sector: positions of different tables, printed only
    allpos = [(s, p) for s in (S, M, C, P, MR) for p in POSITIONS[s]]
    cross = []
    for (s1, p1), (s2, p2) in itertools.combinations(allpos, 2):
        if s1 != s2:
            cross.append(dict(square(f"{s1} {p1} vs {s2} {p2}", tables[s1][p1], tables[s2][p2]), set="cross_sector"))
    t28 = tables_2028(cells)
    fut = enumerate_squares(t28, [("2028_announced", S, None), ("2028_announced", M, None),
                                  ("2028_announced", P, [("MNP", "NTS")])])
    # Per table, read from the cells: squares listed, independent squares b1, which squares
    # are dependent (the basis is every square against the table's first position).
    per_table = {}
    for s in SQUARE_TABLES:
        sq = [q for q in main if q["square"].startswith(s + " ")]
        first = POSITIONS[s][0]
        basis = [q["square"] for q in sq if q["square"].startswith(f"{s} {first} vs ")]
        per_table[s] = {"positions": len(POSITIONS[s]), "squares": len(sq), "b1": b1_of(tables[s]),
                        "basis": basis, "dependent": [q["square"] for q in sq if q["square"] not in basis],
                        "additive_holds_on_table": None if any(q["sgd_state"] == "missing" for q in sq)
                        else all(q["sgd_state"] == "zero" for q in sq),
                        "multiplicative_holds_on_table": None if any(q["log_state"] == "missing" for q in sq)
                        else all(q["log_state"] == "zero" for q in sq)}
    bare = {f"{s}/{p}": tables[s][p]["HS"] != tables[s][p]["BS"] for s in tables for p in tables[s]}
    complete = all(q["sgd_state"] in ("zero", "nonzero") and q["log_state"] in ("zero", "nonzero")
                   for q in main + u + fut + cross)
    b1_ok = all(d["b1"] == d["squares"] - math.comb(d["positions"] - 1, 2) == len(d["basis"])
                for d in per_table.values())
    passed = complete and b1_ok
    return passed, {"main": main, "unskilled": u, "cross_sector": cross, "announced_2028": fut,
                    "per_table": per_table, "b1_total": sum(d["b1"] for d in per_table.values()),
                    "complete": complete, "b1_matches_basis": b1_ok,
                    "rival_bare_dies_at_position": bare}

# ---------------------------------------------------------------------------
# L3-5
# ---------------------------------------------------------------------------

def grid_increments(sector, lqs2_values, sp_max=7, w_max=24, rates=None, sp_in_tiers=True):
    """Increment sets per class over all mixes where both before and after are within quota."""
    rates = rates or {k: v[0] for k, v in CELLS.items()}
    r = TIER_RULES[sector]
    out = {"SP": {}, "HS": {}, "BS": {}}
    n_valid = 0
    for lqs2 in lqs2_values:
        maxmw = (lqs2 * r["mult_num"]) // (2 * r["mult_den"])
        cache = {}

        def ok(sp, hs, bs):
            mw = sp + hs + bs
            w2 = lqs2 + 2 * mw
            return mw <= maxmw and 200 * sp <= r["spq"] * w2

        def b(sp, hs, bs):
            k = (sp, hs, bs)
            if k not in cache:
                cache[k] = bill(sector, lqs2, sp, hs, bs, rates, sp_in_tiers)[2]
            return cache[k]

        for sp in range(sp_max + 1):
            for hs in range(w_max + 1):
                for bs in range(w_max + 1):
                    if not ok(sp, hs, bs):
                        continue
                    n_valid += 1
                    base = b(sp, hs, bs)
                    for cls, nxt in (("SP", (sp + 1, hs, bs)), ("HS", (sp, hs + 1, bs)), ("BS", (sp, hs, bs + 1))):
                        if cls == "SP" and nxt[0] > sp_max:
                            continue
                        if cls != "SP" and max(nxt[1], nxt[2]) > w_max:
                            continue
                        if ok(*nxt):
                            d = b(*nxt) - base
                            out[cls][d] = out[cls].get(d, 0) + 1
    return {c: dict(sorted(v.items())) for c, v in out.items()}, n_valid


GRID_SMALL = (7, 24)  # (sp_max, w_max) of the first three knob points
KNOBS = [("L=1..40 step 1", [2 * k for k in range(1, 41)]),
         ("L=1..80 step 1", [2 * k for k in range(1, 81)]),
         ("L=1..80 step 0.5", list(range(2, 161))),
         # The grid bounds are the knob that binds once the quota no longer does (manufacturing,
         # LQS 41 and above, has every small-grid mix within quota).  This point lifts them past
         # the quota region: services LQS 80 allows floor(80 x 0.538462) = 43 migrant workers and
         # at most 12 S Pass holders; manufacturing LQS 40 allows 60 and at most 15.
         ("whole quota region", {S: ([2 * k for k in range(1, 81)], 14, 45),
                                 M: ([2 * k for k in range(1, 41)], 16, 61)})]


def knob_for(spec, sector):
    if isinstance(spec, dict):
        return spec[sector]
    return (spec,) + GRID_SMALL


def l3_5(rates=None, sp_in_tiers=True, knobs=KNOBS):
    res = {}
    flags = []
    for label, spec in knobs:
        res[label] = {}
        for sector in (S, M):
            lqs2s, sp_max, w_max = knob_for(spec, sector)
            inc, nvalid = grid_increments(sector, lqs2s, sp_max=sp_max, w_max=w_max,
                                          rates=rates, sp_in_tiers=sp_in_tiers)
            res[label][sector] = {"increments": {c: {str(k): v for k, v in d.items()} for c, d in inc.items()},
                                  "sets": {c: sorted(d) for c, d in inc.items()}, "mixes_within_quota": nvalid}
            if isinstance(spec, dict):
                res[label][sector]["grid"] = {"lqs_count": f"{lqs2s[0] // 2}..{lqs2s[-1] // 2} step 1",
                                              "s_pass": f"0..{sp_max}", "hs": f"0..{w_max}", "bs": f"0..{w_max}"}
            flags.append(max(inc["SP"]) > SP_RATE)
    if all(flags):
        passed = True
    elif not any(flags):
        passed = False
    else:
        passed = None
    return passed, res

# ---------------------------------------------------------------------------
# L3-6
# ---------------------------------------------------------------------------

def compare_event(event_pages, announced=ANNOUNCED_2028):
    """event_pages: {sector: {(pos, cls): monthly}} read in the month the change takes effect."""
    diffs = []
    for sector, cells in announced.items():
        for key, v in cells.items():
            got = event_pages.get(sector, {}).get(key)
            if got != v:
                diffs.append({"cell": f"{sector}/{key[0]}/{key[1]}", "announced": v, "page": got})
    return (not diffs), diffs


def l3_6(cells, event_pages=None):
    t28 = tables_2028(cells)
    p3 = {s: {"values": sorted({v for pos in t28[s].values() for v in pos.values()}),
              "distinct": len({v for pos in t28[s].values() for v in pos.values()}),
              "cells": sum(len(pos) for pos in t28[s].values())} for s in t28}
    if event_pages is None:
        return None, {"state": "event not yet in effect", "announced": {s: {"/".join(k): v for k, v in c.items()}
                                                                         for s, c in ANNOUNCED_2028.items()},
                      "announced_tables": t28, "recomputed_L3_3_announced": p3,
                      "L3_5_announced": "not computed: the merged tier's boundary is not written on any page"}
    ok, diffs = compare_event(event_pages)
    return ok, {"state": "in effect", "differences": diffs}

# ---------------------------------------------------------------------------
# L3-7
# ---------------------------------------------------------------------------
REQUIRED = ("page", "url", "file", "snapshot_utc", "last_updated", "sha256", "monthly_cells_read", "verbatim")
VERBATIM = ("full", "partial", "summary")  # how much of the stored text the fetch returned word for word


def l3_7(manifest, files):
    """files: {filename: bytes} of the snapshot folder (*.txt, no .expired)."""
    rows = []
    ok = True
    names = set()
    for p in manifest["pages"]:
        missing = [k for k in REQUIRED if k not in p]
        data = files.get(p.get("file"))
        sha = hashlib.sha256(data).hexdigest() if data is not None else None
        good = not missing and sha == p.get("sha256") and p.get("verbatim") in VERBATIM
        ok &= good
        names.add(p.get("file"))
        rows.append({"page": p.get("page"), "url": p.get("url"), "snapshot_utc": p.get("snapshot_utc"),
                     "last_updated": p.get("last_updated"), "sha256": p.get("sha256"),
                     "verbatim": p.get("verbatim"), "verbatim_note": p.get("verbatim_note"),
                     "sha_recomputed_equal": sha == p.get("sha256"), "monthly_cells_read": p.get("monthly_cells_read"),
                     "announced_2028_cells": p.get("announced_2028_cells")})
    extra = sorted(set(files) - names)
    ok = ok and not extra and len(manifest["pages"]) == 7
    return ok, {"pages": rows, "unlisted_files": extra, "guide": manifest.get("guide")}


def snapshot_names(names):
    """Every file in the snapshot folder takes part in the coverage check, whatever its
    extension (a stored PDF or HTML page would be an unlisted file), except the manifest
    itself and .expired copies."""
    return sorted(n for n in names if n != "manifest.json" and ".expired" not in n)


def load_snapshots():
    manifest = json.loads((SNAP / "manifest.json").read_text(encoding="utf-8"))
    keep = set(snapshot_names(f.name for f in SNAP.iterdir() if f.is_file()))
    files = {f.name: f.read_bytes() for f in sorted(SNAP.iterdir()) if f.name in keep}
    return manifest, files

# ---------------------------------------------------------------------------
# Self-test: answer-known fixtures, one planted error per criterion, mapping
# ---------------------------------------------------------------------------

def selftest() -> int:
    results = run_selftest(verbose=True)
    fails = [r for r in results if not r["ok"]]
    print(f"selftest: {len(results)} checks, {len(fails)} failure(s)")
    return 1 if fails else 0


def run_selftest(verbose=False):
    results = []

    def expect(cond, msg):
        cond = bool(cond)
        if verbose:
            print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        results.append({"check": msg, "ok": cond})

    base_rates = {k: v[0] for k, v in CELLS.items()}
    # tier_fill is the count form of allocate(): same tiers on every small case
    same = True
    for t1 in range(0, 5):
        for t2 in range(0, 5):
            for n in itertools.product(range(4), repeat=3):
                for inside in (True, False):
                    lists, _ = allocate(*n, t1, t2, inside)
                    seq = ([("SP", n[0])] if inside else []) + [("HS", n[1]), ("BS", n[2])]
                    counts = tier_fill(seq, t1, t2)
                    same &= all({c: lists[i].count(c) for c in set(lists[i])} == counts[i] for i in range(3))
    expect(same, "tier_fill (counts) equals allocate (lists) on every case with tiers 0..4 and 0..3 of each class")
    # Known answers
    expect(ceil_cent(300) == 987 and ceil_cent(650) == 2137, "ceil_cent known answers 300->9.87, 650->21.37")
    expect(bill(M, 50, 6, 8, 17, GUIDE_RATES)[2] == 14430, "guide p12 bill recomputes to 14,430")
    expect(bill(S, 14, 0, 3, 0, GUIDE_RATES)[2] == 1300, "guide p14 bill recomputes to 1,300")
    expect(bill(S, 16, 1, 1, 0, base_rates)[2] == 1050, "order fixture: S Pass takes the T1 slot (650 + 400)")
    expect(bill(M, 50, 0, 2, 0, base_rates)[2] == 500, "fixture: two HS in manufacturing T1 cost 500")
    # L3-1
    ok, _ = l3_1(CELLS)
    expect(ok, "L3-1 passes on the tables")
    bad = dict(CELLS); k = (S, "T2", "BS"); bad[k] = (bad[k][0] + 1,) + bad[k][1:]
    expect(not l3_1(bad)[0], "L3-1 flips when one monthly levy is moved by one dollar")
    # L3-2
    ok, rows, mm = l3_2(GUIDE_RATES, CELLS)
    expect(len(rows) == 48 and ok is True and sorted(r["row"] for r in mm) ==
           ["p15 cafe + factory total", "p15 factory T2 levy", "p15 factory total", "rate marine/ONE/HS"],
           "L3-2 on the guide: 48 rows all reconciled, the flag is True and the list names exactly the four guide errors")
    # Answer-known fixture where the guide agrees with itself and with the pages: the flag is True
    g_ok = dict(GUIDE_RATES); g_ok[(MR, "ONE", "HS")] = 350
    ex_ok = [dict(e) for e in EXAMPLES]
    for e in ex_ok:
        if e["id"] == "p15 factory":
            e["printed_tier"] = (5520, 5640, 2600); e["printed_total"] = 13760
    comb_ok = dict(COMBINED); comb_ok["printed_total"] = 15060
    ok_fix = l3_2(g_ok, CELLS, ex_ok, comb_ok)
    expect(ok_fix[0] is True and not ok_fix[2], "L3-2 fixture where every known answer agrees: the flag is True")
    expect(not l3_2(g_ok, CELLS, ex_ok, comb_ok, drop=3)[0], "L3-2 flips when a row is deleted")
    g2 = dict(g_ok); g2[(P, "MNP", "HS")] = 201
    r2f = l3_2(g2, CELLS, ex_ok, comb_ok)
    expect(r2f[0] is True and [r["row"] for r in r2f[2]] == ["rate process/MNP/HS"],
           "L3-2 list moves when one guide cell is altered and is that cell (list is computed, not written)")
    g3 = dict(g_ok); g3[(P, "MNP", "HS")] = None
    r2n = l3_2(g3, CELLS, ex_ok, comb_ok)
    expect(r2n[0] is None, "L3-2 takes no verdict when the guide gives no input for one row")
    # L3-3
    expect(l3_3(CELLS)[0], "L3-3 passes on the tables")
    c3 = dict(CELLS); c3[(MR, "ONE", "BS")] = (None, None, "cleared")
    expect(not l3_3(c3)[0], "L3-3 flips when a position is cleared")
    c3b = dict(CELLS); c3b[(S, "T1", "BS")] = (300, "9.87", "fixture: BS equal to HS")
    r3b = l3_3(c3b)
    expect(r3b[0] is False and r3b[1]["positions_hs_bs_not_two_values"] == ["services/T1"]
           and r3b[1]["positions_hs_bs_differ"] == 11,
           "L3-3 flips when one position writes the same value for HS and BS, and names that position")
    # L3-4
    expect(l3_4(CELLS)[0], "L3-4 passes on the tables")
    add = dict(CELLS)
    for pos, c in (("T1", 100), ("T2", 100), ("T3", 100)):
        hs = add[(S, pos, "HS")][0]; add[(S, pos, "BS")] = (hs + c, None, "fixture")
    sq = [q for q in l3_4(add)[1]["main"] if q["square"].startswith("services")]
    expect(all(q["sgd_state"] == "zero" for q in sq) and all(q["log_state"] == "nonzero" for q in sq),
           "L3-4 fixture BS = HS + c: SGD squares all zero, log squares all nonzero")
    mul = dict(CELLS)
    for pos in ("T1", "T2", "T3"):
        hs = mul[(S, pos, "HS")][0]; mul[(S, pos, "BS")] = (hs * 3 // 2, None, "fixture")
    sq = [q for q in l3_4(mul)[1]["main"] if q["square"].startswith("services")]
    expect(all(q["log_state"] == "zero" for q in sq) and all(q["sgd_state"] == "nonzero" for q in sq),
           "L3-4 fixture BS = HS x c: log squares all zero, SGD squares all nonzero")
    four = {s: {"A": {"HS": 1, "BS": 2}, "B": {"HS": 1, "BS": 3}, "C": {"HS": 2, "BS": 3}, "D": {"HS": 5, "BS": 9}}
            for s in ("x",)}
    real = {q["square"]: q for q in l3_4(CELLS)[1]["main"]}
    expect(real["services T1 vs T3"]["sign"] is None and real["services T1 vs T2"]["sign"] is None
           and real["manufacturing T1 vs T3"]["sign"] == "+",
           "L3-4 sign is read only where both compositions are nonzero and agree (paper table, design 3)")
    expect(len(enumerate_squares(four, [("t", "x", None)])) == 6, "L3-4 fixture with four positions gives C(4,2) = 6 squares")
    expect(b1_of(four["x"]) == 3, "L3-4 b1 = E - V + 1 = 8 - 6 + 1 = 3 on the four-position fixture")
    c4 = dict(CELLS); c4[(S, "T2", "HS")] = (None, None, "cleared")
    try:
        p4c = l3_4(c4)[0]
    except Exception as e:  # noqa: BLE001
        p4c = f"crashed {type(e).__name__}"
    expect(p4c is False, f"L3-4 flips to False (no crash) when one cell is cleared: got {p4c}")
    c5 = dict(CELLS); del c5[(MR, "ONE", "BS")]
    try:
        p4d = l3_4(c5)[0]
    except Exception as e:  # noqa: BLE001
        p4d = f"crashed {type(e).__name__}"
    expect(p4d is False, f"L3-4 flips to False (no crash) when one cell is deleted: got {p4d}")
    expect(l3_4(add)[1]["per_table"][S]["additive_holds_on_table"] is True
           and l3_4(CELLS)[1]["per_table"][S]["additive_holds_on_table"] is False,
           "L3-4 per-table additive reading is computed from the squares (fixture holds, tables do not)")
    # L3-5 (small knob for speed)
    small = [("fixture L=1..20", [2 * k for k in range(1, 21)])]
    p5, r5 = l3_5(knobs=small)
    expect(p5 is True, "L3-5 flag is True on a small grid")
    p5b, r5b = l3_5(sp_in_tiers=False, knobs=small)
    spb = r5b["fixture L=1..20"][S]["sets"]["SP"]
    expect(p5b is False and max(spb) == 650,
           f"L3-5 flips when S Pass is taken out of the tier slots (S Pass set {spb}, maximum 650)")
    # L3-6
    event_same = {s: dict(c) for s, c in ANNOUNCED_2028.items()}
    expect(compare_event(event_same)[0] is True, "L3-6 compare passes when pages equal the announcement")
    event_bad = {s: dict(c) for s, c in ANNOUNCED_2028.items()}; event_bad[MR][("ONE", "BS")] = 650
    expect(compare_event(event_bad)[0] is False, "L3-6 compare flips when one announced cell differs")
    expect(l3_6(CELLS)[0] is None, "L3-6 is None while the event is pending")
    # L3-7
    manifest, files = load_snapshots()
    expect(l3_7(manifest, files)[0], "L3-7 passes on the snapshot folder")
    f2 = dict(files); f2["extra_page.txt"] = b"x"
    expect(not l3_7(manifest, f2)[0], "L3-7 flips with one unlisted file")
    f3 = dict(files); first = manifest["pages"][0]["file"]; f3[first] = f3[first][:-1] + b"#"
    expect(not l3_7(manifest, f3)[0], "L3-7 flips when one byte of a snapshot changes")
    expect(snapshot_names(["a.txt", "guide.pdf", "page.html", "manifest.json", "a.txt.expired_x"])
           == ["a.txt", "guide.pdf", "page.html"],
           "L3-7 loader keeps files of any extension (a stored PDF would be unlisted), drops manifest and .expired")
    m4 = json.loads(json.dumps(manifest)); m4["pages"][0].pop("verbatim", None)
    expect(not l3_7(m4, files)[0], "L3-7 flips when a page carries no verbatim field")
    m5 = json.loads(json.dumps(manifest)); m5["pages"][0]["verbatim"] = "unknown"
    expect(not l3_7(m5, files)[0], "L3-7 flips when a page's verbatim field is not full, partial or summary")
    # mapping
    expect(mapping_ok(), "11c mapping: every undecided cell maps to None and only those")
    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    selftest_rows = run_selftest(verbose=False)
    print(f"selftest: {len(selftest_rows)} checks, {sum(not r['ok'] for r in selftest_rows)} failure(s)")
    manifest, files = load_snapshots()
    p1, r1 = l3_1(CELLS)
    print(f"L3-1 daily levy: {sum(r['state']=='match' for r in r1)} match, "
          f"{sum(r['state']=='mismatch' for r in r1)} mismatch, {sum(r['state']=='no_input' for r in r1)} no input")
    p2, r2, mm = l3_2(GUIDE_RATES, CELLS)
    print(f"L3-2 rows {len(r2)}, disagree {len(mm)}:")
    for r in mm:
        print("   ", r)
    p3, r3 = l3_3(CELLS)
    for s, d in r3["per_table"].items():
        print(f"L3-3 {s}: {d['cells']} cells, {d['distinct']} distinct {d['values']}")
    p4, r4 = l3_4(CELLS)
    for q in r4["main"] + r4["unskilled"] + r4["announced_2028"]:
        print(f"L3-4 [{q['set']}] {q['square']}: SGD {q['sgd']:+d} ({q['sgd_state']}), log {q['log']} "
              f"({q['log_state']}, {q['log_multiple']}x floor {q['log_floor']}), {q['sign_state']} {q['sign']}")
    p5, r5 = l3_5()
    for label, d in r5.items():
        for s, v in d.items():
            print(f"L3-5 {label} {s}: mixes {v['mixes_within_quota']}, SP {v['sets']['SP']}, "
                  f"HS {v['sets']['HS']}, BS {v['sets']['BS']}")
    p6, r6 = l3_6(CELLS)
    p7, r7 = l3_7(manifest, files)
    print(f"L3-7 snapshots: {len(r7['pages'])} pages, unlisted {r7['unlisted_files']}, ok {p7}")

    def sets(label, s, c):
        return r5[label][s]["sets"][c]
    sp_s = sets("L=1..80 step 1", S, "SP"); sp_m = sets("L=1..80 step 1", M, "SP")
    knob_flags = [max(r5[label][s]["sets"]["SP"]) > SP_RATE for label in r5 for s in r5[label]]
    knob_points_true = sum(all(max(r5[label][s]["sets"]["SP"]) > SP_RATE for s in r5[label]) for label in r5)
    sets_same = all(r5[label][s]["sets"] == r5["L=1..80 step 1"][s]["sets"] for label in r5 for s in r5[label])
    bare = r4["rival_bare_dies_at_position"]
    pt = r4["per_table"]
    add_fail = [s for s, d in pt.items() if d["additive_holds_on_table"] is False]
    mul_fail = [s for s, d in pt.items() if d["multiplicative_holds_on_table"] is False]
    print(f"L3-4 tables: " + "; ".join(f"{s} squares {d['squares']} b1 {d['b1']} dependent {d['dependent']}"
                                       for s, d in pt.items()))
    print(f"L3-5 flag: {knob_points_true}/{len(r5)} knob points, {sum(knob_flags)}/{len(knob_flags)} sector-knob cells")
    crit = [
        {"name": "L3-1", "kind": "instrument", "passed": p1,
         "detail": f"Daily levy equals ceil_cent(monthly x 12 / 365) on every printed cell: "
                   f"{sum(r['state']=='match' for r in r1)} match, {sum(r['state']=='mismatch' for r in r1)} mismatch; "
                   f"{sum(r['state']=='no_input' for r in r1)} cells carry no daily rate and take no verdict: "
                   + ", ".join(r["cell"] + (" (monthly only)" if r["monthly"] is not None else " (not written)")
                               for r in r1 if r["state"] == "no_input") + "."},
        {"name": "L3-2", "kind": "bookkeeping", "passed": p2,
         "detail": f"The guide's rate table and worked bills, recomputed from its own steps and compared with the "
                   f"sector pages: {len(r2)} rows, {sum(r['state'] in ('agree', 'disagree') for r in r2)} read on both "
                   f"sides and reconciled; {sum(r['state'] == 'agree' for r in r2)} agree, {len(mm)} disagree. "
                   f"The {len(mm)} that disagree are errors in the Ministry's guide 'How to calculate your quota and "
                   "levy bill' (the source document), where the guide contradicts its own steps or the sector page; "
                   "they are not errors in this reading. Listed from the rows: "
                   + "; ".join(f"{r['row']} printed/page {r.get('printed', r.get('page'))} vs "
                               f"computed/guide {r.get('computed', r.get('guide'))}" for r in mm)
                   + ". The flag reads that every row is present and reconciled; the list is this check's output."},
        {"name": "L3-3", "kind": "own_reading", "passed": p3,
         "detail": f"HS and BS are both written and differ at {r3['positions_hs_bs_differ']} of {r3['positions']} positions"
                   + (f" (not at {', '.join(r3['positions_hs_bs_not_two_values'])})"
                      if r3["positions_hs_bs_not_two_values"] else "")
                   + "; positions writing more than two classes (Unskilled added): "
                   + (", ".join(f"{p} {n} classes, {r3['distinct_values_at_position'][p]} distinct values"
                                for p, n in r3["classes_written_at_position"].items() if n > 2) or "none")
                   + ". "
                   + "; ".join(f"{s} {d['cells']} cells {d['distinct']} distinct" for s, d in r3["per_table"].items())
                   + f"; all Work Permit cells {r3['all_work_permit_distinct']} distinct values; "
                   f"S Pass current 1 value (650), before 2025-09-01 {r3['spass_previous_distinct']} values (550, 650)."},
        {"name": "L3-4", "kind": "own_reading", "passed": p4,
         "detail": "Squares (BS-HS)@a-(BS-HS)@b in SGD (floor 1) and log(BS/HS) difference (floor log((x+1)/x)), "
                   f"every pair of positions within a table, {len(r4['main'])} squares, {r4['b1_total']} independent "
                   "(b1 = E - V + 1 per table: "
                   + ", ".join(f"{s} {d['b1']}" for s, d in pt.items())
                   + "; dependent: " + ", ".join(x for d in pt.values() for x in d["dependent"]) + "): "
                   + "; ".join(f"{q['square']} {q['sgd']:+d} / {q['log']} [{q['sign_state']}]" for q in r4["main"])
                   + f". Rival shapes, read on whole tables: bare (one value per position) fails at "
                   f"{sum(bare.values())}/{len(bare)} positions; additive (class term + position term) fails on "
                   f"{len(add_fail)}/{len(pt)} tables ({', '.join(add_fail)}); multiplicative fails on "
                   f"{len(mul_fail)}/{len(pt)} tables ({', '.join(mul_fail)}). Single squares where a rival's zero holds: additive "
                   + ", ".join(q["square"] for q in r4["main"] if q["rival_additive_holds"])
                   + "; multiplicative "
                   + ", ".join(q["square"] for q in r4["main"] if q["rival_multiplicative_holds"]) + "."},
        {"name": "L3-5", "kind": "own_reading", "passed": p5,
         "detail": f"Increment in the monthly bill from one more hire, computed from the guide's steps over mixes within "
                   f"quota, LQS 1..80: services S Pass {sp_s}, manufacturing S Pass {sp_m}; the printed S Pass rate is "
                   f"one number, 650. Sets identical at all knob points: {sets_same}. "
                   f"Flag (S Pass maximum above {SP_RATE}) holds at {knob_points_true}/{len(r5)} knob points "
                   f"({', '.join(r5)})."},
        {"name": "L3-6", "kind": "known_answer", "passed": p6,
         "detail": "Announced 2028 tables (services and manufacturing merge Tier 1 and Tier 2; process and marine raise "
                   "basic-skilled rates; construction announces nothing). Pages say the timeline will be released "
                   "'in due course'. READ: quarterly from 2027-01-15; on 2028-12-31 still pending => 'announcement not carried out'."},
        {"name": "L3-7", "kind": "bookkeeping", "passed": p7,
         "detail": f"{len(r7['pages'])} page snapshots, SHA-256 recomputed equal on "
                   f"{sum(r['sha_recomputed_equal'] for r in r7['pages'])}; unlisted files {len(r7['unlisted_files'])}; "
                   f"guide read pages 1-15, not stored."},
    ]
    record = {
        "stage": "B150",
        "title": "Singapore foreign worker levy: one job, priced by worker class and by the employer's tier",
        "config": {
            "snapshots": {p["page"]: {"last_updated": p["last_updated"], "sha256": p["sha256"], "file": p["file"]}
                          for p in manifest["pages"]},
            "guide_version": "Updated 1 July 2026",
            "L3_5_grid": {"lqs_count": "1..40 step 1; 1..80 step 1; 1..80 step 0.5", "s_pass": "0..7",
                          "hs": "0..24", "bs": "0..24", "within_quota": "before and after the hire",
                          "whole_quota_region": {"services": "LQS 1..80, S Pass 0..14, HS and BS 0..45",
                                                 "manufacturing": "LQS 1..40, S Pass 0..16, HS and BS 0..61"}},
            "tier_rules": TIER_RULES, "s_pass_rate": SP_RATE,
        },
        "criteria": crit,
        "mapping_11c": [{"criterion": m[0], "state": m[1], "verdict": m[2]} for m in MAPPING],
        "selftest": selftest_rows,
        "L3_1_rows": r1, "L3_2_rows": r2, "L3_3": r3, "L3_4": r4, "L3_5": r5, "L3_6": r6, "L3_7": r7,
        "rival_shapes": {
            "bare": "a levy is one number per position (sector) => one value per position",
            "additive": "levy = class term + position term => SGD squares are zero",
            "multiplicative": "levy = class term x position term => log squares are zero",
        },
        "s_pass_printed_rate": {
            "premise": "S Pass page: 'harmonised to $650 across all sectors and levy tiers'; the printed rate is one "
                       "number in every sector and tier",
            "reading": f"holds: L3-3 reads one current S Pass value ({SPASS_CURRENT[0]})",
            "separate_object": "the increase in the monthly bill from one more S Pass holder (L3-5) is a different "
                               "object; the sentence says nothing about it",
        },
    }
    text = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        from safe_write import create, rewrite
        if RECORD.exists():
            rewrite(RECORD, "B150_record", lambda _t: text, session=SESSION)
        else:
            create(RECORD, "B150_record", text, session=SESSION)
        print(f"wrote {RECORD.name}")
    bad = [c["name"] for c in crit if c["passed"] is False]
    print("criteria:", {c["name"]: c["passed"] for c in crit})
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
