"""B148: customer-class lines on one UK bank's posted mortgage rate tables.

One bank posts four rate pages: first-time buyers (F), moving home (M),
remortgage to the bank (R) and existing customers switching (E). Each page
prints an initial rate at the same positions, a position being
(LTV band, fixed period, product). Three rivals say the class does not enter
the price at a position, or enters it as one overall shift:

    bare scalar field     r(a, j) = p(j)               same price for two classes at one position
    additive separation   r(a, j) = alpha(a) + beta(j) every incentive-neutral square is zero
    multiplicative        1 + r(a, j) = A(a) * B(j)    every four-term ratio is one, and the
                                                       class difference keeps one sign in a group

Each rate page also prints a cashback or fee incentive that moves with the
class. An incentive-neutral square takes two classes a, b and two positions
j, k with the same fixed period, where each class has the same incentive at j
and at k. Fees and incentives then cancel term by term, and the square of the
full cost is the square of the rate, whatever the loan amount and term.

The rows come from verbatim text snapshots of the four pages (one tool call
per snapshot, see data/raw/b148/). ``--transcribe`` parses them into a row
file and a snapshot manifest; the default run reads the row file and writes the
record. All arithmetic on rates and money is exact (``Fraction``); the grid
unit is 0.01 percentage point, the unit the pages print.

Criteria are written in this file, the record carries their text, and every
quantity the run produces is in the record.

    python -B experiments/b148_mortgage_class_square.py --transcribe
    python -B experiments/b148_mortgage_class_square.py
    python -B experiments/b148_mortgage_class_square.py --selftest
    python -B experiments/b148_mortgage_class_square.py --mutation-test
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # safe_write.py sits one level above the repository

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b148"
ROWS = RAW / "b148_rows.json"
MANIFEST = RAW / "b148_snapshots.json"
RECORD = ROOT / "results" / "b148_uk_mortgage_class_lines.json"
SESSION = "B148_1029"

PAGES = {
    "F": "https://www.hsbc.co.uk/mortgages/first-time-buyers/rates/",
    "M": "https://www.hsbc.co.uk/mortgages/our-rates/",
    "R": "https://www.hsbc.co.uk/mortgages/move-your-mortgage/rates/",
    "E": "https://www.hsbc.co.uk/mortgages/existing-customers/switch/rates/",
}
CLASSES = ("F", "M", "R", "E")
FIXED_KINDS = ("FeeSaver", "Standard", "PremierStandard")
LOANS = (100_000, 200_000, 300_000, 500_000)
AMORT_MONTHS = 300
THRESHOLD_UNITS = 2          # a reading must clear the one-unit print grid by one more unit
R_VARIANT = 300              # remortgage: the 300 pound cashback variant (same rate as legal-fees variant)
KNOWN = {                    # B148-3: read at the gate, 2026-10-13/14
    ("F", 60, 2, "FeeSaver"): "5.36",
    ("M", 60, 2, "FeeSaver"): "5.29",
    ("F", 60, 5, "Standard"): "5.09",
    ("M", 60, 5, "Standard"): "5.06",
}
VERSION_MARKS = {2: "31.01.2029", 5: "31.01.2032"}

MUT = os.environ.get("B148_MUT", "")   # mutation switch for --mutation-test only


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def frac_rate(s: str) -> Fraction:
    if MUT == "float":
        return Fraction(float(s))  # wrong on purpose under the mutation
    return Fraction(s)


def units(x: Fraction) -> Fraction:
    """A rate difference in units of 0.01 percentage point."""
    return x * 100


def fmt_units(u) -> str:
    u = Fraction(u)
    return str(u.numerator) if u.denominator == 1 else f"{float(u):.4f}"


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def write_json(path: Path, obj, label: str) -> None:
    import safe_write
    text = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        safe_write.rewrite(path, label, lambda _old: text, session=SESSION)
    else:
        safe_write.create(path, label, text, session=SESSION)


# ----------------------------------------------------------------------------
# Transcription: snapshot text -> rows
# ----------------------------------------------------------------------------

RE_LTV = re.compile(r"^(\d{2,3})%(?: LTV)?$")
RE_RATE = re.compile(r"^(\d\.\d\d)%(?:\s+(?:fixed|variable))?$")
RE_PCT = re.compile(r"(\d+\.\d\d)%")
RE_DATE = re.compile(r"\b(\d\d\.\d\d\.\d{4})\b")
RE_SECTION = re.compile(r"^\*\*(\d{2,3})% LTV")
LABELS = ("Section", "LTV", "Period", "Product", "Initial rate", "Booking fee",
          "Cashback", "Incentive", "Max loan", "Follow-on rate")


def _money(cell: str) -> int:
    return int(re.sub(r"[^\d]", "", cell))


def _kind_period(cell: str, others: list[str]):
    if "BTL" in cell or "buy-to-let" in cell.lower() or "buy to let" in cell.lower():
        return None
    if "Tracker" in cell:
        kind = "TrackerFeeSaver" if "Fee Saver" in cell else "TrackerStandard"
    elif "Premier" in cell:
        kind = "PremierStandard" if "Standard" in cell else None
    elif "Fee Saver" in cell:
        kind = "FeeSaver"
    elif "Standard" in cell:
        kind = "Standard"
    else:
        return None
    if kind is None:
        return None
    m = re.search(r"(\d+)\s*(?:Year|Y\b)", cell)
    period = int(m.group(1)) if m else None
    if period is None:
        for o in others:
            m = re.search(r"(\d+)\s*(?:yrs|Years|years|Year)", o)
            if m:
                period = int(m.group(1))
                break
    return kind, period


def parse_snapshot(text: str, page: str) -> list[dict]:
    """Rows parsed from one snapshot. Each row keeps its source line verbatim."""
    out = []
    sec_ltv = None
    defaults = {}
    end_by_period = {}
    for m in re.finditer(r"(\d\d\.\d\d\.\d{4}) \((\d+)-year\)", text):
        end_by_period[int(m.group(2))] = m.group(1)
    if page == "E" and re.search(r"cashback is £0", text):
        defaults["incentive"] = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        ms = RE_SECTION.match(line)
        if ms:
            sec_ltv = int(ms.group(1))
            defaults.pop("max_loan", None)
            defaults.pop("follow_on", None)
            continue
        mf = re.match(r"^Follow-on variable rate: (\d\.\d\d)%", line)
        if mf:
            defaults["follow_on"] = mf.group(1)
        mm = re.search(r"Max loan is (£[\d,]+) for every product", line)
        if mm:
            defaults["max_loan"] = _money(mm.group(1))
        if "|" not in line:
            continue
        if line.startswith("- "):
            line = line[2:]
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells = [c for c in cells if c and not set(c) <= set("-: ")]
        clean = []
        for c in cells:
            for lab in LABELS:
                if c.startswith(lab + ": "):
                    c = c[len(lab) + 2:]
                    break
            clean.append(c.strip())
        cells = clean
        irate = next((i for i, c in enumerate(cells) if RE_RATE.match(c.split(" (")[0])), None)
        if irate is None:
            continue
        ltv = next((int(RE_LTV.match(c).group(1)) for c in cells[:irate] if RE_LTV.match(c)), sec_ltv)
        pcell = next((c for c in cells[:irate] if ("Fee Saver" in c or "Standard" in c or "Tracker" in c)
                      and "Legal" not in c), None)
        if pcell is None or ltv is None:
            continue
        kp = _kind_period(pcell, cells[:irate])
        if kp is None:
            continue
        kind, period = kp
        rate = RE_RATE.match(cells[irate].split(" (")[0]).group(1)
        fee = None
        incs = []
        max_loan = None
        follow_on = None
        for c in cells[irate + 1:]:
            if "Legal" in c or "ashback" in c or "£" in c:
                parts = [p.strip() for p in c.split("/")] if "/" in c else [c]
                for p in parts:
                    if "Legal" in p:
                        incs.append("LF")
                    elif "ashback" in p:
                        incs.append(_money(p))
                    elif "£" in p:
                        v = _money(p)
                        if v >= 100_000:
                            max_loan = v
                        elif fee is None:
                            fee = v
                        else:
                            incs.append(v)
            elif RE_PCT.search(c) and max_loan is not None:
                follow_on = RE_PCT.search(c).group(1)
        if max_loan is None:
            max_loan = defaults.get("max_loan")
        if follow_on is None:
            follow_on = defaults.get("follow_on")
        if not incs:
            incs = [defaults["incentive"]] if "incentive" in defaults else [None]
        md = RE_DATE.search(line)
        end_date = md.group(1) if md else end_by_period.get(period) if not kind.startswith("Tracker") else None
        for inc in incs:
            out.append({"page": page, "ltv": ltv, "period": period, "kind": kind, "rate": rate,
                        "fee": fee, "incentive": inc, "max_loan": max_loan, "follow_on": follow_on,
                        "end_date": end_date, "line": raw_line.rstrip()})
    return out


FIELDS = ("rate", "fee", "incentive", "max_loan", "follow_on", "end_date")


def row_key(r: dict) -> tuple:
    inc = r["incentive"]
    variant = "LF" if inc == "LF" else "num"
    return (r["page"], r["ltv"], r["period"], r["kind"], variant)


def merge_read(rows: list[dict]) -> tuple[dict, list[dict]]:
    """One row per key inside a read; a key printed twice with different fields is a conflict."""
    by = defaultdict(list)
    for r in rows:
        by[row_key(r)].append(r)
    merged, conflicts = {}, []
    for k, rs in by.items():
        sig = {tuple(str(x[f]) for f in FIELDS) for x in rs}
        # R cashback variant: a duplicate in a combined cell carries the same numbers
        if len(sig) == 1:
            merged[k] = rs[0]
        else:
            # fields that are None in one copy and set in another are filled, not a conflict
            base = dict(rs[0])
            clash = False
            for x in rs[1:]:
                for f in FIELDS:
                    if base[f] is None:
                        base[f] = x[f]
                    elif x[f] is not None and str(x[f]) != str(base[f]):
                        clash = True
            if clash:
                conflicts.append({"key": list(k), "copies": [{f: x[f] for f in FIELDS} | {"file": x["file"]}
                                                              for x in rs]})
            else:
                merged[k] = base
    return merged, conflicts


def transcribe() -> int:
    logs = sorted(RAW.glob("b148_fetchlog_read*.json"))
    snapshots, rows = [], []
    for lp in logs:
        log = json.loads(lp.read_text(encoding="utf-8"))
        for s in log["snapshots"]:
            p = RAW / s["file"]
            text = p.read_text(encoding="utf-8")
            snapshots.append({**s, "read": log["read"], "sha256": sha256_text(text), "chars": len(text)})
            for r in parse_snapshot(text, s["page"]):
                r["file"] = s["file"]
                r["read"] = log["read"]
                rows.append(r)
    write_json(MANIFEST, {"snapshots": snapshots,
                          "second_designer_attempts": [a for lp in logs for a in
                                                       json.loads(lp.read_text(encoding="utf-8")).get(
                                                           "second_designer_attempts", [])],
                          "hash_of": "the text WebFetch returned, saved verbatim; not the page bytes"},
               "B148 snapshot manifest")
    write_json(ROWS, {"rows": rows}, "B148 transcribed rows")
    print(f"snapshots {len(snapshots)}  rows {len(rows)}  -> {ROWS.name}, {MANIFEST.name}")
    return 0


# ----------------------------------------------------------------------------
# Table building
# ----------------------------------------------------------------------------

def consistency(rows: list[dict]) -> dict:
    """Per read merge, then same-day reads compared field by field (B148-1)."""
    reads = sorted({r["read"] for r in rows})
    merged, conflicts = {}, {}
    for rd in reads:
        merged[rd], conflicts[rd] = merge_read([r for r in rows if r["read"] == rd])
    first = reads[0]
    same_day = [rd for rd in reads if rd != first and rd < 10]   # reads 2..9 same day, 10+ next day
    shelved = {}
    for k, r in merged[first].items():
        missing = [f for f in ("ltv", "period", "kind", "rate", "fee", "incentive", "max_loan", "follow_on")
                   if r.get(f) is None]
        if missing:
            shelved[k] = f"missing {','.join(missing)}"
            continue
        for rd in same_day:
            o = merged[rd].get(k)
            if o is None:
                shelved[k] = f"absent in read {rd}"
                break
            diff = [f for f in FIELDS if str(o[f]) != str(r[f]) and not (o[f] is None or r[f] is None)]
            if diff:
                shelved[k] = f"read {rd} differs on {','.join(diff)}: " + "; ".join(
                    f"{f} {r[f]} vs {o[f]}" for f in diff)
                break
    for rd in reads:
        for c in conflicts[rd]:
            shelved[tuple(c["key"])] = f"two copies disagree inside read {rd}"
    return {"reads": reads, "same_day_reads": same_day, "merged": merged, "shelved": shelved,
            "conflicts": conflicts}


def build_table(merged_first: dict, shelved: dict, premier: str) -> dict:
    """cells[(cls, pos)] = {rate, fee, inc, max_loan}; pos = (ltv, period, kind)."""
    cells = {}
    for k, r in merged_first.items():
        if k in shelved:
            continue
        page, ltv, period, kind, variant = k
        if kind not in FIXED_KINDS and not kind.startswith("Tracker"):
            continue
        if page == "R" and variant == "LF" and (page, ltv, period, kind, "num") in merged_first \
                and (page, ltv, period, kind, "num") not in shelved:
            continue          # the 300 pound variant stands for R where it exists
        cls = page
        pos_kind = kind
        if premier == "classline" and kind == "PremierStandard":
            cls, pos_kind = page + "P", "Standard"
        cells[(cls, (ltv, period, pos_kind))] = {
            "rate": frac_rate(r["rate"]), "rate_s": r["rate"], "fee": r["fee"], "inc": r["incentive"],
            "max_loan": r["max_loan"], "follow_on": r["follow_on"]}
    return cells


def fixed_cells(cells: dict) -> dict:
    return {k: v for k, v in cells.items() if not k[1][2].startswith("Tracker")}


def classes_of(cells: dict) -> list[str]:
    return sorted({c for c, _ in cells})


def positions_of(cells: dict) -> list[tuple]:
    return sorted({p for _, p in cells})


def betti1(cells: dict) -> dict:
    cls = classes_of(cells)
    pos = positions_of(cells)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (c, p) in cells:
        a, b = find(("c", c)), find(("p", p))
        if a != b:
            parent[a] = b
    comps = len({find(("c", c)) for c in cls} | {find(("p", p)) for p in pos})
    E, V = len(cells), len(cls) + len(pos)
    return {"edges": E, "vertices": V, "components": comps, "b1": E - V + comps}


# ----------------------------------------------------------------------------
# Squares
# ----------------------------------------------------------------------------

def square(cells, a, b, j, k) -> Fraction:
    s = cells[(a, j)]["rate"] - cells[(b, j)]["rate"] - cells[(a, k)]["rate"] + cells[(b, k)]["rate"]
    return -s if MUT == "sign" else s


def neutral(cells, a, b, j, k) -> bool:
    if j[1] != k[1]:
        return False
    if MUT == "noinc":
        return True
    # The fee square must vanish too. On the HSBC pages every class pays the same fee at a
    # position, so this adds nothing there; on the Barclays sheet the fee tier is the position
    # and the fee amount moves with the class (purchase 899, remortgage and existing 999).
    if MUT != "nofee":
        fees = [cells[(a, j)].get("fee"), cells[(b, j)].get("fee"), cells[(a, k)].get("fee"), cells[(b, k)].get("fee")]
        if any(f is None for f in fees) or fees[0] - fees[1] - fees[2] + fees[3] != 0:
            return False
    return cells[(a, j)]["inc"] == cells[(a, k)]["inc"] and cells[(b, j)]["inc"] == cells[(b, k)]["inc"]


def class_pairs(cells):
    return list(itertools.combinations(classes_of(cells), 2))


def all_squares(cells, neutral_only=True):
    """Every (a, b, j, k) with all four cells present, j < k, same period."""
    out = []
    pos = positions_of(cells)
    for a, b in class_pairs(cells):
        common = [p for p in pos if (a, p) in cells and (b, p) in cells]
        for j, k in itertools.combinations(common, 2):
            if j[1] != k[1]:
                continue
            nt = neutral(cells, a, b, j, k)
            if neutral_only and not nt:
                continue
            if not neutral_only and nt:
                continue
            out.append((a, b, j, k))
    return out


def pos_s(p) -> str:
    return f"{p[0]}%/{p[1]}y/{p[2]}"


def square_object(cells, a, b, j, k) -> dict:
    s = square(cells, a, b, j, k)
    cell = lambda c, p: (f"{c}@{pos_s(p)}={cells[(c, p)]['rate_s']}%(inc {cells[(c, p)]['inc']})"
                         + (f"[{cells[(c, p)]['src']}]" if "src" in cells[(c, p)] else ""))
    obj = {"classes": f"{a}-{b}", "j": pos_s(j), "k": pos_s(k),
           "cells": [cell(a, j), cell(b, j), cell(a, k), cell(b, k)], "units": fmt_units(units(s))}
    if s == 0:
        obj["equal_prices"] = (f"{a}@j-{b}@j = {fmt_units(units(cells[(a, j)]['rate'] - cells[(b, j)]['rate']))}"
                               f" = {a}@k-{b}@k")
    return obj


# ----------------------------------------------------------------------------
# Criteria (each returns a dict; the flag is computed from the object)
# ----------------------------------------------------------------------------

RIVAL_MAPPING = [
    ("some |value| >= 2 units", True, "B"),
    ("every value exactly 0", False, "C"),
    ("nonzero values only at 1 unit (on the print floor), or no object", None, "unread"),
]


def rival_verdict(values: list[Fraction]):
    if not values:
        return None, "unread"
    mx = max(abs(units(v)) for v in values)
    if mx >= THRESHOLD_UNITS:
        return True, "B"
    if mx == 0:
        return False, "C"
    return None, "unread"


def c_bare(cells) -> dict:
    """B148-5: positions where both classes have zero incentive (fees are part of the position)."""
    diffs = []
    for a, b in class_pairs(cells):
        for p in positions_of(cells):
            if (a, p) in cells and (b, p) in cells and not p[2].startswith("Tracker") \
                    and cells[(a, p)]["inc"] == 0 and cells[(b, p)]["inc"] == 0 \
                    and cells[(a, p)]["fee"] == cells[(b, p)]["fee"]:
                d = cells[(a, p)]["rate"] - cells[(b, p)]["rate"]
                diffs.append((a, b, p, d))
    passed, grid = rival_verdict([d for *_, d in diffs])
    top = sorted(diffs, key=lambda x: -abs(x[3]))[:12]
    return {"passed": passed, "grid": grid, "n_positions": len(diffs),
            "n_nonzero": sum(1 for *_, d in diffs if d != 0),
            "max_units": fmt_units(max((abs(units(d)) for *_, d in diffs), default=0)),
            "largest": [f"{a}-{b}@{pos_s(p)}: {cells[(a, p)]['rate_s']} vs {cells[(b, p)]['rate_s']}"
                        f" = {fmt_units(units(d))} units" for a, b, p, d in top]}


def c_additive(cells) -> dict:
    sq = all_squares(cells, neutral_only=True)
    vals = [square(cells, *q) for q in sq]
    passed, grid = rival_verdict(vals)
    per_pair = {}
    for (a, b, j, k), v in zip(sq, vals):
        d = per_pair.setdefault(f"{a}-{b}", {"squares": 0, "nonzero": 0, "zero": 0, "one_unit": 0, "max_units": 0})
        d["squares"] += 1
        u = abs(units(v))
        d["nonzero" if v != 0 else "zero"] += 1
        d["one_unit"] += 1 if u == 1 else 0
        d["max_units"] = max(d["max_units"], int(u) if u.denominator == 1 else float(u))
    return {"passed": passed, "grid": grid, "n_squares": len(sq),
            "n_nonzero": sum(1 for v in vals if v != 0),
            "n_ge2": sum(1 for v in vals if abs(units(v)) >= THRESHOLD_UNITS),
            "n_one_unit": sum(1 for v in vals if abs(units(v)) == 1),
            "max_units": fmt_units(max((abs(units(v)) for v in vals), default=0)),
            "per_pair": per_pair, "squares": sq}


def c_multiplicative(cells) -> dict:
    sq = all_squares(cells, neutral_only=True)
    ratio_hits = []
    n_ratio_not_one = 0
    for (a, b, j, k) in sq:
        ra, rb = cells[(a, j)]["rate"], cells[(b, j)]["rate"]
        rak, rbk = cells[(a, k)]["rate"], cells[(b, k)]["rate"]
        one = Fraction(1)
        if MUT == "float":
            ratio = ((1 + float(ra) / 100) * (1 + float(rbk) / 100)) / ((1 + float(rb) / 100) * (1 + float(rak) / 100))
            not_one = ratio != 1.0
        else:
            ratio = ((one + ra / 100) * (one + rbk / 100)) / ((one + rb / 100) * (one + rak / 100))
            not_one = ratio != 1
        if not_one:
            n_ratio_not_one += 1
            if abs(units(square(cells, a, b, j, k))) >= THRESHOLD_UNITS:
                ratio_hits.append((a, b, j, k))
    # sign crossing inside a group: class pair, period, incentive pattern
    groups = defaultdict(list)
    for a, b in class_pairs(cells):
        for p in positions_of(cells):
            if (a, p) in cells and (b, p) in cells and not p[2].startswith("Tracker"):
                groups[(a, b, p[1], str(cells[(a, p)]["inc"]), str(cells[(b, p)]["inc"]))].append(
                    (p, cells[(a, p)]["rate"] - cells[(b, p)]["rate"]))
    crossing = []
    for g, items in groups.items():
        ds = [d for _, d in items]
        if len(items) >= 2 and max(ds) > 0 and min(ds) < 0:
            crossing.append({"group": f"{g[0]}-{g[1]} {g[2]}y inc({g[3]},{g[4]})",
                             "diffs": [f"{pos_s(p)}:{fmt_units(units(d))}" for p, d in items]})
    if ratio_hits or crossing:
        passed, grid = True, "B"
    elif sq and n_ratio_not_one == 0 and not crossing:
        passed, grid = False, "C"
    else:
        passed, grid = None, "unread"
    return {"passed": passed, "grid": grid, "n_squares": len(sq), "n_ratio_not_one": n_ratio_not_one,
            "n_ratio_not_one_and_ge2": len(ratio_hits), "n_groups": len(groups),
            "n_crossing_groups": len(crossing), "crossing": crossing[:20]}


LTV_ORDER = (60, 70, 75, 80, 85, 90, 95)


def c_boundaries(cells, ltv_order=LTV_ORDER) -> dict:
    """B148-8: adjacent LTV bands, same period and kind; every class keeps its incentive across the boundary."""
    out = []
    cls = classes_of(cells)
    for period in sorted({p[1] for p in positions_of(cells)}):
        for kind in sorted({p[2] for p in positions_of(cells)}):
            for lo, hi in zip(ltv_order, ltv_order[1:]):
                j, k = (lo, period, kind), (hi, period, kind)
                present = [c for c in cls if (c, j) in cells and (c, k) in cells
                           and cells[(c, j)]["inc"] == cells[(c, k)]["inc"]]
                if len(present) < 2:
                    continue
                jumps = {c: cells[(c, k)]["rate"] - cells[(c, j)]["rate"] for c in present}
                if all(v == 0 for v in jumps.values()):
                    continue
                sqs = {f"{a}-{b}": fmt_units(units(jumps[a] - jumps[b])) for a, b in itertools.combinations(present, 2)}
                out.append({"boundary": f"{lo}->{hi} {period}y {kind}",
                            "jumps_units": {c: fmt_units(units(v)) for c, v in jumps.items()},
                            "class_x_boundary_units": sqs})
    return {"passed": bool(out), "n_boundaries": len(out), "boundaries": out}


def c_count(cells, classes=CLASSES) -> dict:
    per_pos = []
    for p in positions_of(cells):
        vals = {c: cells[(c, p)]["rate_s"] for c in classes if (c, p) in cells}
        if len(vals) >= 2:
            per_pos.append({"pos": pos_s(p), "n_classes": len(vals), "n_values": len(set(vals.values())),
                            "values": vals})
    trackers = [{"pos": x["pos"], "F": x["values"].get("F"), "M": x["values"].get("M"),
                 "same": x["values"].get("F") == x["values"].get("M")}
                for x in per_pos if "Tracker" in x["pos"] and "F" in x["values"] and "M" in x["values"]]
    fixed_fm = [x for x in per_pos if "Tracker" not in x["pos"] and "F" in x["values"] and "M" in x["values"]]
    fm_same = [x["pos"] for x in fixed_fm if x["values"]["F"] == x["values"]["M"]]
    return {"passed": bool(per_pos), "positions": per_pos, "tracker_F_vs_M": trackers,
            "fixed_F_M_rows": len(fixed_fm), "fixed_F_M_same": fm_same,
            "histogram_n_values": dict(sorted(
                {str(n): sum(1 for x in per_pos if x["n_values"] == n) for n in
                 {x["n_values"] for x in per_pos}}.items()))}


_COST_CACHE: dict = {}


def fixed_period_interest(rate_s_or_frac, loan: int, months: int) -> Fraction:
    r = Fraction(rate_s_or_frac) if not isinstance(rate_s_or_frac, Fraction) else rate_s_or_frac
    key = (r, loan, months)
    if key in _COST_CACHE:
        return _COST_CACHE[key]
    i = r / 1200
    L = Fraction(loan)
    g = (1 + i) ** AMORT_MONTHS
    pay = L * i * g / (g - 1)
    gn = (1 + i) ** months
    bal = L * gn - pay * (gn - 1) / i
    interest = months * pay - (L - bal)
    _COST_CACHE[key] = interest
    return interest


def full_cost(cell: dict, loan: int, period: int):
    if not isinstance(cell["inc"], int) or cell["fee"] is None:
        return None          # an incentive with no pound value (legal fees, a package) is not read
    cash = 0 if MUT == "nocash" else cell["inc"]
    return fixed_period_interest(cell["rate"], loan, period * 12) + cell["fee"] - cash


def c_fullcost(cells) -> dict:
    sq = all_squares(cells, neutral_only=False)
    tally = {"read": 0, "zero": 0, "unread": 0}
    sign_const = 0
    rows = []
    for (a, b, j, k) in sq:
        four = [cells[(a, j)], cells[(b, j)], cells[(a, k)], cells[(b, k)]]
        cap = min(c["max_loan"] for c in four)
        loans = [L for L in LOANS if L <= cap]
        vals = []
        for L in loans:
            cs = [full_cost(c, L, j[1]) for c in four]
            if any(x is None for x in cs):
                vals = []
                break
            vals.append(cs[0] - cs[1] - cs[2] + cs[3])
        if not vals:
            state = "unread"
        elif all(v != 0 for v in vals):
            state = "read"
        elif all(v == 0 for v in vals):
            state = "zero"
        else:
            state = "unread"
        tally[state] += 1
        signs = {(v > 0) - (v < 0) for v in vals}
        const = len(signs) == 1 and 0 not in signs
        if state == "read" and const:
            sign_const += 1
        rows.append({"sq": f"{a}-{b} {pos_s(j)} / {pos_s(k)}", "state": state,
                     "pounds": [f"{float(v):.2f}" for v in vals], "sign_constant": const})
    return {"passed": bool(sq), "n_squares": len(sq), "tally": tally,
            "read_with_constant_sign": sign_const, "squares": rows}


def c_premier_both(results_by_partition: dict) -> bool:
    return set(results_by_partition) == {"product", "classline"}


def c_known(merged_first: dict, shelved: dict) -> dict:
    found, bad = {}, []
    version_change = []
    for (cls, ltv, period, kind), want in KNOWN.items():
        r = merged_first.get((cls, ltv, period, kind, "num"))
        if r is None:
            bad.append(f"{cls} {ltv}% {period}y {kind}: absent")
            continue
        found[f"{cls} {ltv}% {period}y {kind}"] = r["rate"]
        if r.get("end_date") and r["end_date"] != VERSION_MARKS[period]:
            version_change.append(f"{cls} {period}y end date {r['end_date']} (mark {VERSION_MARKS[period]})")
        elif r["rate"] != want:
            bad.append(f"{cls} {ltv}% {period}y {kind}: read {r['rate']}, known {want}")
    if version_change:
        passed, state = None, "version changed (third state)"
    elif bad:
        passed, state = False, "mismatch"
    else:
        passed, state = True, "all four read back"
    return {"passed": passed, "state": state, "read": found, "mismatches": bad, "version": version_change}


def c_instrument(con: dict, header_ok: dict) -> dict:
    first = con["reads"][0]
    per_page = {}
    for page in CLASSES:
        keys = [k for k in con["merged"][first] if k[0] == page]
        sh = [k for k in keys if k in con["shelved"]]
        per_page[page] = {"rows": len(keys), "shelved": len(sh),
                          "share": f"{(len(sh) / len(keys)) if keys else 1:.4f}",
                          "header_initial_interest_rate": header_ok.get(page, False)}
    over = [p for p, d in per_page.items() if d["rows"] == 0 or d["shelved"] * 10 > d["rows"]
            or not d["header_initial_interest_rate"]]
    if not con["same_day_reads"]:
        passed = None
    else:
        passed = not over
    return {"passed": passed, "per_page": per_page, "pages_over": over,
            "same_day_reads": con["same_day_reads"],
            "shelved_rows": {" ".join(map(str, k)): v for k, v in sorted(con["shelved"].items(), key=str)}}


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def c_bookkeeping(manifest: dict) -> dict:
    snaps = manifest["snapshots"]
    missing = [s.get("file", "?") for s in snaps
               if not all(s.get(f) for f in ("sha256", "fetched_after", "fetched_before", "prompt", "url"))
               or s.get("offset") is None]
    reads = defaultdict(list)
    for s in snaps:
        reads[s["read"]].append(s)
    spans = {}
    over_hour = []
    for rd, ss in reads.items():
        try:
            t0 = min(_ts(s["fetched_after"]) for s in ss)
            t1 = max(_ts(s["fetched_before"]) for s in ss)
        except (KeyError, TypeError, ValueError):
            missing.append(f"read {rd} timestamps")
            continue
        spans[rd] = (t0, t1)
        if t1 - t0 > timedelta(hours=1):
            over_hour.append(rd)
    first = min(spans) if spans else None
    nextday = [rd for rd in spans if first is not None and spans[rd][0] - spans[first][1] >= timedelta(hours=24)]
    if missing or over_hour:
        passed = False
    elif not nextday:
        passed = None
    else:
        passed = True
    return {"passed": passed, "missing": missing, "reads_over_one_hour": over_hour,
            "spans": {str(rd): [a.isoformat(), b.isoformat()] for rd, (a, b) in sorted(spans.items())},
            "next_day_reads": nextday,
            "state": "pending: second read not yet 24 h after the first" if passed is None else None}


# ----------------------------------------------------------------------------
# Second designer: the Barclays core-range customer rate sheet (one PDF)
# ----------------------------------------------------------------------------
#
# The rows come from data/raw/b148/barclays/barclays_rows.json, written by
# experiments/b148_read_barclays.py under ``python -I`` from the fetched PDF. This file never
# opens the PDF. Classes on this sheet: P purchase, R remortgage to Barclays, E existing
# Barclays mortgage customers (EMC Reward, switching or borrowing more). Purchase is not split
# into first-time buyers and home movers on this sheet, so P is its own class, not F or M.
#
# A position is (LTV, fixed period, kind). The kind carries the product line (standard,
# Premier, Green Home, Springboard), the fee tier (a fee or none) and the loan band (loans of
# 1m pounds and up form their own band). The fee amount is a cell attribute, because the same
# tier carries 899 pounds for purchase and 999 for remortgage and existing customers; the
# incentive-neutral test asks the fee square to vanish (see ``neutral``).

BARCLAYS_DIR = RAW / "barclays"
BARCLAYS_ROWS = BARCLAYS_DIR / "barclays_rows.json"
BARCLAYS_MANIFEST = BARCLAYS_DIR / "barclays_manifest.json"
BARCLAYS_URL = "https://www.barclays.co.uk/content/dam/documents/personal/mortgages/CoreRangeCustomerRateSheet.pdf"
BARCLAYS_CLASSES = ("P", "R", "E")
SCOPE_TITLES = (                                     # page title -> (scope, class); first match wins
    ("Reward Rates for Existing Mortgage Customers - Buy to Let", ("btl", "E")),
    ("Reward Rates for Existing Mortgage Customers - Residential", ("res", "E")),
    ("Buy to Let Purchase & Remortgage Rates", ("btl", None)),     # class from the sub-heading
    ("Residential Remortgage Rates", ("res", "R")),
    ("Residential Purchase Rates", ("res", "P")),
)
BTL_SUB = (("Purchase Only", ("P",)), ("Remortgage Only", ("R",)), ("Buy to Let Purchase & Remortgage", ("P", "R")))
RE_LOAN = re.compile(r"£\s*([\d,]+)(m?)\s*-\s*£\s*([\d,]+)(m?)")
RE_MARGIN = re.compile(r"\+(\d\.\d\d)%")


def _pounds(num: str, m: str) -> int:
    v = int(num.replace(",", ""))
    return v * 1_000_000 if m == "m" else v


def page_scopes(cover: list[dict]) -> dict:
    out = {}
    for c in cover:
        heads = " ".join(h.split(": ", 1)[-1] for h in c["headings"])
        out[c["page"]] = next((v for t, v in SCOPE_TITLES if t in heads), None)
    return out


def barclays_cell(row: dict, cls: str) -> dict | None:
    """One table row as a cell for one class. None for a row this reading does not use."""
    c = row["cells"]
    name = c["Product Type"].replace("EMC Reward ", "").replace("™", "")
    m = re.search(r"(\d+)\s*Yr", name)
    period = int(m.group(1)) if m else None
    fee = _money(c["Product Fee"])
    tier = "NoFee" if fee == 0 else "Fee"
    ml = RE_LOAN.search(c["Minimum/Maximum Loan Size"])
    lo, hi = (_pounds(ml.group(1), ml.group(2)), _pounds(ml.group(3), ml.group(4))) if ml else (None, None)
    band = "Large-" if lo is not None and lo >= 1_000_000 else ""
    ltv_s = c["LTV"]
    mo = re.match(r"^(Over\s+)?(\d{2,3})%$", ltv_s)
    ltv = (int(mo.group(2)) + (1 if mo.group(1) else 0)) if mo else None   # "Over 90%" -> 91
    if "Tracker" in name:
        line = "Offset" if "Offset" in name else "Base"
        kind = f"Tracker{line}-{'Premier-' if name.startswith('Premier') else ''}{band}{tier}"
    elif name.startswith("Premier"):
        kind = f"Premier-{band}{tier}"
    elif name.startswith("Green Home"):
        kind = f"GreenHome-{band}{tier}"
    elif name.startswith("Springboard"):
        kind = f"Springboard-{band}{tier}"
    elif name.startswith("The Great Escape"):
        kind = f"GreatEscape-{band}{tier}"
    else:
        kind = f"Std-{band}{tier}"
    if cls == "R":
        if kind.startswith("GreatEscape"):
            inc = "GE"           # no fee, free legals, free valuation and 150 pounds cashback: a package
        elif row.get("scope") == "btl" or not band:
            inc = "S&S"          # Switch & Save remortgage package (legal service), no pound value printed
        else:
            inc = 0              # residential Switch & Save stops at loans up to 2m
    else:
        inc = 0
    return {"ltv": ltv, "period": period, "kind": kind, "rate_s": c["Initial Interest Rate"].rstrip("%"),
            "fee": fee, "inc": inc, "max_loan": hi, "min_loan": lo, "end": c["Product/ ERC end date"],
            "erc": c["Early Repayment Charge"], "follow_on": c["Follow On Rate"],
            "src": f"p{row['page']} r{row['row']}", "product": c["Product Type"]}


def barclays_table(rows: list[dict], scopes: dict, scope: str, premier: str, ge: str) -> tuple[dict, list]:
    """cells[(cls, (ltv, period, kind))]. Returns the cells and the rows that clashed on one key."""
    cells, clashes = {}, []
    for r in rows:
        sc = scopes.get(r["page"])
        if sc is None or sc[0] != scope:
            continue
        classes = (sc[1],) if sc[1] else next((v for t, v in BTL_SUB if t in (r["heading"] or "")), ())
        for cls in classes:
            cell = barclays_cell(dict(r, scope=scope), cls)
            if cell is None or cell["ltv"] is None or cell["period"] is None:
                continue
            kind = cell["kind"]
            if ge == "merged" and kind.startswith("GreatEscape-"):
                kind = "Std-" + kind[len("GreatEscape-"):]
            ccls = cls
            if premier == "classline" and kind.startswith("Premier-"):
                ccls, kind = cls + "P", "Std-" + kind[len("Premier-"):]
            key = (ccls, (cell["ltv"], cell["period"], kind))
            cell = dict(cell, rate=frac_rate(cell["rate_s"]))
            if key in cells:
                clashes.append({"key": f"{key[0]}@{pos_s(key[1])}", "rows": [cells[key]["src"], cell["src"]]})
                continue
            cells[key] = cell
    return cells, clashes


def barclays_features(cells: dict) -> list[dict]:
    """D49: at every position two or more classes share, the features the reading leans on
    besides the rate (ERC, follow-on rate, end date, maximum loan). Printed where they differ."""
    out = []
    for p in positions_of(cells):
        cs = [c for c in classes_of(cells) if (c, p) in cells]
        if len(cs) < 2:
            continue
        for f in ("erc", "follow_on", "end", "max_loan"):
            vals = {c: cells[(c, p)][f] for c in cs}
            if len(set(map(str, vals.values()))) > 1:
                out.append({"pos": pos_s(p), "feature": f, "values": vals})
    return out


def barclays_analyse(rows, scopes, scope, premier, ge) -> dict:
    cells_all, clashes = barclays_table(rows, scopes, scope, premier, ge)
    cells = fixed_cells(cells_all)
    add = c_additive(cells)
    squares_obj = [square_object(cells, *q) for q in add.pop("squares")]
    ltvs = tuple(sorted({p[0] for p in positions_of(cells)}))
    classes = tuple(classes_of(cells_all))
    return {
        "table": {"classes": classes_of(cells), "positions": len(positions_of(cells)),
                  "cells": len(cells), "betti": betti1(cells), "clashes": clashes},
        "B148-4": {"passed": bool(squares_obj), "n": len(squares_obj), "squares": squares_obj},
        "B148-5": c_bare(cells),
        "B148-6": add,
        "B148-7": c_multiplicative(cells),
        "B148-8": c_boundaries(cells, ltvs),
        "B148-9": c_count(cells_all, classes),
        "B148-10": c_fullcost(cells),
        "features_differing": barclays_features(cells),
    }


def c_instrument_barclays(doc: dict, used_pages: set) -> dict:
    """Two extraction paths agree row by row; every used row resolves its fields; the rate
    column is the one the sheet calls 'Initial Interest Rate' and the APRC column is not read (D54)."""
    t = doc["rows"]
    x = doc["text_path_rows"]
    per_page = {}
    disagree = []
    for pg in sorted({r["page"] for r in t} | {r["page"] for r in x}):
        tp = [r for r in t if r["page"] == pg]
        xp = [r for r in x if r["page"] == pg]
        bad = 0
        for i in range(max(len(tp), len(xp))):
            a = tp[i]["cells"] if i < len(tp) else None
            b = xp[i] if i < len(xp) else None
            pair = None if a is None or b is None else [
                (a["Product Type"], b["product"]), (a["Initial Interest Rate"], b["rate"]),
                (a["Product Fee"], b["fee"]), (a["LTV"], b["ltv"]),
                (a["Minimum/Maximum Loan Size"], b["loan"]), (a["Product/ ERC end date"], b["end"])]
            if pair is None or any(re.sub(r"\s+", "", u) != re.sub(r"\s+", "", v) for u, v in pair):
                bad += 1
                disagree.append(f"p{pg} item {i}: table {a and a['Product Type']} {a and a['Initial Interest Rate']} "
                                f"| text {b and b['product']} {b and b['rate']}")
        per_page[pg] = {"table_rows": len(tp), "text_rows": len(xp), "disagree": bad}
    unresolved = []
    for r in t:
        if r["page"] not in used_pages:
            continue
        c = r["cells"]
        if not (RE_LOAN.search(c["Minimum/Maximum Loan Size"]) and re.match(r"^(Over\s+)?\d{2,3}%$", c["LTV"])
                and c["Product Fee"].startswith("£") and re.search(r"\d+\s*Yr", c["Product Type"])
                and c["Early Repayment Charge"] and c["Follow On Rate"]):
            unresolved.append(f"p{r['page']} r{r['row']}")
    headers_ok = bool(doc["column_header_rows"]) and all(
        h.split(": ", 1)[1].split(" | ")[1] == "Initial Interest Rate"
        and h.split(": ", 1)[1].split(" | ")[8] == "Overall Cost for Comparison" for h in doc["column_header_rows"])
    over = [pg for pg, d in per_page.items() if d["disagree"] * 10 > max(d["table_rows"], 1)]
    passed = bool(t) and headers_ok and not over and not unresolved
    return {"passed": passed, "per_page": per_page, "pages_over": over, "disagree": disagree[:30],
            "unresolved": unresolved, "header_rows": len(doc["column_header_rows"]), "headers_ok": headers_ok}


def c_bookkeeping_barclays(doc: dict, manifest: dict, pdf_bytes: bytes | None) -> dict:
    """The file on disk matches its manifest (length and SHA-256); the row file names that file;
    the coverage table lists every page of the PDF, pages with zero rows included; every row
    carries its page and row (rule 25)."""
    v = manifest["versions"][-1] if manifest.get("versions") else {}
    problems = []
    if pdf_bytes is None:
        problems.append("PDF not on disk")
    else:
        if len(pdf_bytes) != v.get("bytes"):
            problems.append(f"length {len(pdf_bytes)} vs manifest {v.get('bytes')}")
        if hashlib.sha256(pdf_bytes).hexdigest() != v.get("sha256"):
            problems.append("sha256 differs from manifest")
    if doc["source"]["sha256"] != v.get("sha256"):
        problems.append("row file read a different file")
    pages = [c["page"] for c in doc["coverage"] if c.get("opened")]
    if pages != list(range(1, doc["source"]["pages"] + 1)):
        problems.append(f"coverage pages {pages} vs {doc['source']['pages']} in the PDF")
    if any(r.get("page") is None or r.get("row") is None for r in doc["rows"]):
        problems.append("a row without page or row")
    return {"passed": not problems, "problems": problems,
            "coverage": [{k: c[k] for k in ("page", "opened", "tables", "rate_rows")} for c in doc["coverage"]]}


def c_known_barclays(doc: dict) -> dict:
    """Known answers the sheet fixes itself: every tracker's initial rate is the printed Bank Rate
    plus the printed margin, and every follow-on line's sum is its two terms."""
    bebr = Fraction(doc["source"]["bebr_printed"]) if doc["source"].get("bebr_printed") else None
    checked, bad = 0, []
    for r in doc["rows"]:
        c = r["cells"]
        if "Tracker" in c["Product Type"] and bebr is not None:
            m = RE_MARGIN.search(c["Product Type"])
            if m:
                checked += 1
                if Fraction(c["Initial Interest Rate"].rstrip("%")) != bebr + Fraction(m.group(1)):
                    bad.append(f"p{r['page']} r{r['row']}: {c['Product Type']} prints {c['Initial Interest Rate']}")
        mf = re.search(r"currently (\d\.\d\d)% \+ (\d\.\d\d)% = (\d\.\d\d)%", c["Follow On Rate"])
        if mf:
            checked += 1
            if Fraction(mf.group(1)) + Fraction(mf.group(2)) != Fraction(mf.group(3)):
                bad.append(f"p{r['page']} r{r['row']}: follow-on {mf.group(0)}")
    if bebr is None or checked == 0:
        passed, state = None, "no object: Bank Rate or tracker rows not read"
    else:
        passed, state = (not bad), ("all read back" if not bad else "mismatch")
    return {"passed": passed, "state": state, "bebr": doc["source"].get("bebr_printed"), "checked": checked, "mismatches": bad,
            "version_mark": doc["source"].get("rates_effective")}


def representative_example(doc: dict) -> dict:
    """Printed only: the sheet's representative example recomputed with level-payment amortisation."""
    t = doc.get("representative_example") or ""
    m = re.search(r"mortgage of £([\d,]+) payable over (\d+) months on a tracker rate of (\d\.\d\d)%.*?"
                  r"(\d+) monthly payments of £([\d,.]+) and (\d+) monthly payments of £([\d,.]+)", t)
    if not m:
        return {"read": False}
    L, n, r = Fraction(m.group(1).replace(",", "")), int(m.group(2)), Fraction(m.group(3))
    i = r / 1200
    g = (1 + i) ** n
    pay = L * i * g / (g - 1)
    return {"read": True, "loan": m.group(1), "months": n, "rate": m.group(3),
            "printed_first_payment": m.group(5), "level_payment_from_printed_terms": f"{float(pay):.2f}",
            "note": "printed, not a criterion"}


def load_barclays():
    if not BARCLAYS_ROWS.exists():
        return None
    doc = json.loads(BARCLAYS_ROWS.read_text(encoding="utf-8"))
    man = json.loads(BARCLAYS_MANIFEST.read_text(encoding="utf-8"))
    pdf = BARCLAYS_DIR / man["versions"][-1]["file"]
    return doc, man, (pdf.read_bytes() if pdf.exists() else None)


def barclays_run(add) -> dict | None:
    """Criteria B148-1-Barclays to B148-10-Barclays, appended after the HSBC ones through ``add``."""
    loaded = load_barclays()
    if loaded is None:
        return None
    doc, man, pdf = loaded
    scopes = page_scopes(doc["coverage"])
    used = {p for p, s in scopes.items() if s and s[0] == "res"}
    parts = {p: barclays_analyse(doc["rows"], scopes, "res", p, "merged") for p in ("product", "classline")}
    if MUT == "onepart":
        parts.pop("classline")
    if not c_premier_both(parts):
        raise SystemExit("Premier: both partitions must be analysed (D43)")
    ge_own = barclays_analyse(doc["rows"], scopes, "res", "product", "own")
    btl = barclays_analyse(doc["rows"], scopes, "btl", "product", "merged")
    main = parts["product"]
    inst = c_instrument_barclays(doc, used)
    book = c_bookkeeping_barclays(doc, man, pdf)
    kn = c_known_barclays(doc)
    sfx = "-Barclays"
    add("B148-1" + sfx, "instrument", inst["passed"],
        f"pages {json.dumps(inst['per_page'], sort_keys=True)}; unresolved {inst['unresolved']}; "
        f"column-header rows {inst['header_rows']}, all 'Initial Interest Rate' and APRC apart: {inst['headers_ok']}",
        statement=BARCLAYS_STATEMENTS["B148-1"])
    add("B148-2" + sfx, "bookkeeping", book["passed"],
        f"problems {book['problems']}; coverage {json.dumps(book['coverage'])}", statement=BARCLAYS_STATEMENTS["B148-2"])
    add("B148-3" + sfx, "known_answer", kn["passed"],
        f"{kn['state']}; Bank Rate printed {kn['bebr']}; {kn['checked']} checks; mismatches {kn['mismatches']}; "
        f"version mark 'Rates effective from {kn['version_mark']}'", statement=BARCLAYS_STATEMENTS["B148-3"])
    add("B148-4" + sfx, "own_reading", main["B148-4"]["passed"],
        f"{main['B148-4']['n']} incentive-neutral squares printed in the record", statement=STATEMENTS["B148-4"])
    for name in ("B148-5", "B148-6", "B148-7"):
        r = main[name]
        det = {k: v for k, v in r.items() if k not in ("passed", "grid", "crossing", "largest", "per_pair")}
        add(name + sfx, "rival", r["passed"],
            f"{json.dumps(det, sort_keys=True)}; Premier as class line: passed {parts.get('classline', {}).get(name, {}).get('passed')}, "
            f"grid {parts.get('classline', {}).get(name, {}).get('grid')}; Great Escape as its own kind: passed "
            f"{ge_own[name]['passed']}, grid {ge_own[name]['grid']}",
            {"grid": r["grid"], **RIVAL_FIELDS[name]}, statement=STATEMENTS[name])
    add("B148-8" + sfx, "own_reading", main["B148-8"]["passed"],
        f"{main['B148-8']['n_boundaries']} boundaries with every class's incentive and fee unchanged",
        statement=STATEMENTS["B148-8"])
    b9 = main["B148-9"]
    add("B148-9" + sfx, "own_reading", b9["passed"],
        f"positions {len(b9['positions'])}; histogram of distinct values {b9['histogram_n_values']}",
        statement=BARCLAYS_STATEMENTS["B148-9"])
    b10 = main["B148-10"]
    add("B148-10" + sfx, "own_reading", b10["passed"],
        f"{b10['n_squares']} squares; {b10['tally']}; read with constant sign {b10['read_with_constant_sign']}",
        statement=STATEMENTS["B148-10"])
    return {"source": doc["source"], "page_scopes": {str(k): v for k, v in scopes.items()},
            "coverage": doc["coverage"], "partitions": parts, "great_escape_own_kind": ge_own, "buy_to_let": btl,
            "instrument": inst, "bookkeeping": book, "known_answer": kn,
            "rule_sentence_candidates": doc["rule_sentence_candidates"],
            "representative_example": representative_example(doc)}


BARCLAYS_STATEMENTS = {
    "B148-1": "Barclays sheet: the table path (pymupdf find_tables) and the text path (get_text line stream) agree row by row on product, rate, fee, LTV, loan size and end date; every used row resolves its fields; every column-header row names 'Initial Interest Rate' as the rate column and 'Overall Cost for Comparison' (APRC) apart, which is not read (D54). More than one in ten rows disagreeing on a page is FAIL.",
    "B148-2": "Barclays sheet: the PDF on disk matches its manifest in length and SHA-256; the row file was read from that file; the coverage table lists every page of the PDF, pages with zero rate rows included; every row carries its page and its row in that page's table.",
    "B148-3": "Barclays sheet, known answers the sheet fixes itself: every tracker's initial rate equals the printed Bank Rate plus the printed margin, and every follow-on line's sum equals its two terms. Version mark: 'Rates effective from'. A mismatch is FAIL and named.",
    "B148-9": "Barclays sheet, count: how many distinct rates the classes (purchase, remortgage, existing customer) write at each position they share.",
}


# ----------------------------------------------------------------------------
# The run
# ----------------------------------------------------------------------------

STATEMENTS = {
    "B148-1": "Page titles, eligibility sentences and column headers are printed verbatim; the rate column is the one the source calls 'Initial interest rate' (D54); every row resolves LTV, period, product, rate, fee, incentive, max loan and follow-on rate, and agrees field by field with a same-day second read. Rows that fail are shelved and named; more than one in ten shelved on a page is FAIL.",
    "B148-2": "Every snapshot carries SHA-256, a fetch time bracket, offset and the prompt; one bank's four pages are read within one hour; a second read at least 24 hours after the first is compared row by row. Missing items FAIL; second read not yet due is pending.",
    "B148-3": "Four rates read at the gate read back: 60% 2y Fee Saver F 5.36, M 5.29; 60% 5y Standard F 5.09, M 5.06. Version mark: fixed end dates 31.01.2029 and 31.01.2032. A changed version is the third state; an unchanged version with a mismatch is FAIL.",
    "B148-4": "Every incentive-neutral square is printed: four cells (class, position, rate, incentive) and the square in units of 0.01 point; zero squares print the two equal differences.",
    "B148-5": "Rival, bare scalar field: two classes at one position pay the same rate. Read where both classes have zero incentive (the fee is part of the position).",
    "B148-6": "Rival, additive separation r(a,j)=alpha(a)+beta(j): every incentive-neutral square is exactly zero (Fraction).",
    "B148-7": "Rival, multiplicative separation 1+r(a,j)=A(a)B(j): every four-term ratio of (1+r) is exactly one, and the class difference keeps one sign inside an incentive group.",
    "B148-8": "Class x LTV boundary: where every class keeps its incentive across an adjacent band boundary, the jump of each class and the class x boundary squares are printed.",
    "B148-9": "Count: how many distinct rates the classes write at each position; tracker rate F vs M; fixed rows where F equals M are named.",
    "B148-10": "Full-cost squares for class pairs whose incentives differ: interest over the fixed period on a 25-year repayment loan, plus booking fee, minus cashback, at 100k, 200k, 300k, 500k pounds capped by each row's maximum loan; read / zero / unread printed with sign constancy.",
}

RIVAL_FIELDS = {
    "B148-5": {"rival_premise": "The price is a scalar on the position: r(a, j) = p(j).",
               "rival_entailment": "Two classes at one position pay the same rate; where both incentives are zero and the fee is the same, r(a, j) - r(b, j) = 0.",
               "rival_shape": "point prediction (exactly zero)"},
    "B148-6": {"rival_premise": "The price is a class potential plus a position potential: r(a, j) = alpha(a) + beta(j).",
               "rival_entailment": "Any incentive-neutral square [alpha(a)+beta(j)] - [alpha(b)+beta(j)] - [alpha(a)+beta(k)] + [alpha(b)+beta(k)] = 0.",
               "rival_shape": "point prediction (exactly zero)"},
    "B148-7": {"rival_premise": "The gross rate is a class factor times a position price: 1 + r(a, j) = A(a) B(j).",
               "rival_entailment": "(1+r(a,j))(1+r(b,k)) / ((1+r(b,j))(1+r(a,k))) = 1, and r(a,j) - r(b,j) = (A(a)-A(b)) B(j) keeps one sign across positions.",
               "rival_shape": "point prediction (exactly one)"},
}


def analyse(con: dict, premier: str) -> dict:
    cells_all = build_table(con["merged"][con["reads"][0]], con["shelved"], premier)
    cells = fixed_cells(cells_all)
    add = c_additive(cells)
    squares_obj = [square_object(cells, *q) for q in add.pop("squares")]
    return {
        "table": {"classes": classes_of(cells), "positions": len(positions_of(cells)),
                  "cells": len(cells), "betti": betti1(cells)},
        "B148-4": {"passed": bool(squares_obj), "n": len(squares_obj), "squares": squares_obj},
        "B148-5": c_bare(cells),
        "B148-6": add,
        "B148-7": c_multiplicative(cells),
        "B148-8": c_boundaries(cells),
        "B148-9": c_count(cells_all),
        "B148-10": c_fullcost(cells),
    }


def header_check(manifest: dict) -> dict:
    ok = {}
    for s in manifest["snapshots"]:
        t = (RAW / s["file"]).read_text(encoding="utf-8")
        if "Initial interest rate" in t:
            ok[s["page"]] = True
    return ok


def run() -> int:
    rows = json.loads(ROWS.read_text(encoding="utf-8"))["rows"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    con = consistency(rows)
    by_part = {p: analyse(con, p) for p in ("product", "classline")}
    if MUT == "onepart":
        by_part.pop("classline")
    if not c_premier_both(by_part):
        raise SystemExit("Premier: both partitions must be analysed (D43)")
    main = by_part["product"]
    pend = c_bookkeeping(manifest)
    crit = []

    def add(name, kind, passed, detail, extra=None, statement=None):
        c = {"name": name, "kind": kind, "passed": passed, "statement": statement or STATEMENTS[name], "detail": detail}
        if extra:
            c.update(extra)
        if pend["passed"] is None and name != "B148-2":
            c["pending_second_read"] = True
        crit.append(c)

    inst = c_instrument(con, header_check(manifest))
    add("B148-1", "instrument", inst["passed"],
        f"pages {json.dumps(inst['per_page'], sort_keys=True)}; shelved {len(inst['shelved_rows'])}; "
        f"same-day reads {inst['same_day_reads']}")
    add("B148-2", "bookkeeping", pend["passed"],
        f"missing {pend['missing']}; reads over one hour {pend['reads_over_one_hour']}; spans {pend['spans']}; "
        f"next-day reads {pend['next_day_reads']}" + (f"; {pend['state']}" if pend["state"] else ""))
    kn = c_known(con["merged"][con["reads"][0]], con["shelved"])
    # Next-day reads (numbered 10 and up): the known answers again, and every row compared with the first read.
    nextday = {}
    for rd in [x for x in con["reads"] if x >= 10]:
        k2 = c_known(con["merged"][rd], {})
        first = con["merged"][con["reads"][0]]
        changed = sorted(" ".join(map(str, k)) for k, r in first.items()
                         if k in con["merged"][rd] and any(str(con["merged"][rd][k][f]) != str(r[f]) for f in FIELDS))
        missing = sorted(" ".join(map(str, k)) for k in first if k not in con["merged"][rd])
        nextday[str(rd)] = {"known": k2, "changed_rows": changed, "absent_rows": missing}
        if k2["passed"] is None:
            kn = dict(kn, passed=None, state=f"read {rd}: {k2['state']}")
        elif k2["passed"] is False and kn["passed"] is not None:
            kn = dict(kn, passed=False, state=f"read {rd}: {k2['state']}", mismatches=kn["mismatches"] + k2["mismatches"])
    kn["next_day"] = nextday
    add("B148-3", "known_answer", kn["passed"], f"{kn['state']}; read {kn['read']}; mismatches {kn['mismatches']}; version {kn['version']}; "
        f"next-day reads {[(rd, len(v['changed_rows']), len(v['absent_rows'])) for rd, v in nextday.items()]}")
    b4 = main["B148-4"]
    add("B148-4", "own_reading", b4["passed"], f"{b4['n']} incentive-neutral squares printed in the record")
    for name in ("B148-5", "B148-6", "B148-7"):
        r = main[name]
        other = by_part.get("classline", {}).get(name, {})
        det = {k: v for k, v in r.items() if k not in ("passed", "grid", "crossing", "largest", "per_pair")}
        add(name, "rival", r["passed"],
            f"{json.dumps(det, sort_keys=True)}; Premier as class line: passed {other.get('passed')}, grid {other.get('grid')}",
            {"grid": r["grid"], **RIVAL_FIELDS[name]})
    b8 = main["B148-8"]
    add("B148-8", "own_reading", b8["passed"], f"{b8['n_boundaries']} boundaries with every class's incentive unchanged")
    b9 = main["B148-9"]
    add("B148-9", "own_reading", b9["passed"],
        f"positions {len(b9['positions'])}; histogram of distinct values {b9['histogram_n_values']}; "
        f"tracker F vs M same at {sum(1 for t in b9['tracker_F_vs_M'] if t['same'])}/{len(b9['tracker_F_vs_M'])}; "
        f"fixed F=M at {b9['fixed_F_M_same']} of {b9['fixed_F_M_rows']}")
    b10 = main["B148-10"]
    add("B148-10", "own_reading", b10["passed"],
        f"{b10['n_squares']} squares; {b10['tally']}; read with constant sign {b10['read_with_constant_sign']}")
    barclays = barclays_run(add)

    record = {
        "stage": "B148",
        "title": "Customer-class lines on one UK bank's posted mortgage rate tables",
        "config": {
            "pages": PAGES, "loans": list(LOANS), "amortisation_months": AMORT_MONTHS,
            "threshold_units": THRESHOLD_UNITS, "unit": "0.01 percentage point",
            "remortgage_variant": f"cashback {R_VARIANT} (same rate as the legal-fees variant)",
            "premier_partitions": sorted(by_part), "snapshots": [
                {k: s[k] for k in ("file", "url", "offset", "fetched_after", "fetched_before", "sha256", "chars", "read")}
                for s in manifest["snapshots"]],
            "second_designer": manifest.get("second_designer_attempts", []),
        },
        "rival_mapping": [{"cell": c, "passed": p, "grid": g} for c, p, g in RIVAL_MAPPING],
        "criteria": crit,
        "partitions": {p: {k: v for k, v in r.items()} for p, r in by_part.items()},
        "instrument": inst,
        "known_answer": kn,
        "bookkeeping": {k: v for k, v in pend.items()},
    }
    if barclays is not None:
        record["config"]["second_designer_barclays"] = {
            "url": BARCLAYS_URL, "file": barclays["source"]["file"], "bytes": barclays["source"]["bytes"],
            "sha256": barclays["source"]["sha256"], "rates_effective": barclays["source"]["rates_effective"],
            "classes": list(BARCLAYS_CLASSES), "premier_partitions": sorted(barclays["partitions"]),
            "great_escape": "merged into the no-fee standard kind as a remortgage incentive (own-kind run printed)",
            "fetcher": "experiments/b148_fetch_barclays.py", "reader": "experiments/b148_read_barclays.py (python -I)"}
        record["barclays"] = barclays
    if pend["passed"] is None:
        record["diagnostic_only"] = True
        record["diagnostic_reason"] = ("Station open: the second read 24 hours after the first is not yet in; "
                                       "B148-2 is pending and the other criteria carry pending_second_read.")
    write_json(RECORD, record, "B148 record")
    for c in crit:
        print(f"{c['name']:8s} {c['kind']:12s} {str(c['passed']):5s} {c.get('grid', ''):7s} {c['detail'][:220]}")
    for p, r in by_part.items():
        print(f"[{p}] table {r['table']}")
    if barclays is not None:
        for p, r in list(barclays["partitions"].items()) + [("ge_own", barclays["great_escape_own_kind"]),
                                                             ("btl", barclays["buy_to_let"])]:
            print(f"[Barclays {p}] table {r['table']}")
    return 0


# ----------------------------------------------------------------------------
# Self-test: fixtures with known answers, and a seeded error for every criterion
# ----------------------------------------------------------------------------

def _mk(rows):
    """rows: (cls, ltv, period, kind, rate_str, fee, inc, max_loan) -> cells."""
    cells = {}
    for cls, ltv, per, kind, rate, fee, inc, ml in rows:
        cells[(cls, (ltv, per, kind))] = {"rate": frac_rate(rate), "rate_s": rate, "fee": fee, "inc": inc,
                                          "max_loan": ml, "follow_on": "6.24"}
    return cells


def _mk_frac(rows):
    cells = {}
    for cls, ltv, per, kind, rate, fee, inc, ml in rows:
        cells[(cls, (ltv, per, kind))] = {"rate": rate, "rate_s": str(rate), "fee": fee, "inc": inc,
                                          "max_loan": ml, "follow_on": "6.24"}
    return cells


def selftest() -> int:
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    ML = 2_000_000
    # A real-shaped fixture: two classes, three positions, one incentive differing.
    base = _mk([
        ("A", 60, 2, "FeeSaver", "5.36", 0, 0, ML), ("B", 60, 2, "FeeSaver", "5.29", 0, 0, ML),
        ("A", 80, 2, "FeeSaver", "5.49", 0, 0, ML), ("B", 80, 2, "FeeSaver", "5.44", 0, 0, ML),
        ("A", 90, 2, "FeeSaver", "5.66", 0, 350, ML), ("B", 90, 2, "FeeSaver", "5.54", 0, 0, ML),
    ])
    # known signed square: A-B @60 minus A-B @80 = 7 - 5 = +2 units
    s = square(base, "A", "B", (60, 2, "FeeSaver"), (80, 2, "FeeSaver"))
    check(units(s) == 2, f"square sign/value: expected +2 units, got {fmt_units(units(s))}")
    check(isinstance(s, Fraction), "square is not exact")
    # the 90% cell carries a different incentive for A, so (60,90) and (80,90) leave the neutral set
    sq = all_squares(base, neutral_only=True)
    check(len(sq) == 1, f"neutral set: expected 1 square, got {len(sq)}")
    check(not neutral(base, "A", "B", (60, 2, "FeeSaver"), (90, 2, "FeeSaver")),
          "incentive change did not take the square out of its neutral group")

    # B148-4: a table with one class has no square
    one = _mk([("A", 60, 2, "FeeSaver", "5.36", 0, 0, ML), ("A", 80, 2, "FeeSaver", "5.49", 0, 0, ML)])
    check(not bool(all_squares(one)), "B148-4 seeded single-class table produced a square")

    # B148-5: zero class differences -> FAIL/C; one-unit only -> unread
    zero = _mk([("A", 60, 2, "FeeSaver", "5.30", 0, 0, ML), ("B", 60, 2, "FeeSaver", "5.30", 0, 0, ML)])
    r = c_bare(zero)
    check(r["passed"] is False and r["grid"] == "C", f"B148-5 zero table: {r['passed']} {r['grid']}")
    onegrid = _mk([("A", 60, 2, "FeeSaver", "5.31", 0, 0, ML), ("B", 60, 2, "FeeSaver", "5.30", 0, 0, ML)])
    r = c_bare(onegrid)
    check(r["passed"] is None and r["grid"] == "unread", f"B148-5 one-unit table: {r['passed']} {r['grid']}")
    r = c_bare(base)
    check(r["passed"] is True and r["grid"] == "B", "B148-5 real-shaped table should read B")

    # B148-6: additive table -> FAIL/C; single one-unit square -> unread
    alpha = {"A": Fraction(10, 100), "B": Fraction(-25, 100), "C": Fraction(3, 100)}
    beta = {(60, 2, "FeeSaver"): Fraction(5), (80, 2, "FeeSaver"): Fraction(527, 100), (90, 2, "Standard"): Fraction(561, 100)}
    addtab = _mk_frac([(c, p[0], p[1], p[2], alpha[c] + beta[p], 0, 0, ML) for c in alpha for p in beta])
    r = c_additive(addtab)
    check(r["passed"] is False and r["grid"] == "C", f"B148-6 additive table: {r['passed']} {r['grid']}")
    oneunit = _mk([
        ("A", 60, 2, "FeeSaver", "5.31", 0, 0, ML), ("B", 60, 2, "FeeSaver", "5.30", 0, 0, ML),
        ("A", 80, 2, "FeeSaver", "5.40", 0, 0, ML), ("B", 80, 2, "FeeSaver", "5.40", 0, 0, ML)])
    r = c_additive(oneunit)
    check(r["passed"] is None and r["grid"] == "unread", f"B148-6 one-unit square: {r['passed']} {r['grid']}")

    # B148-7: exactly multiplicative rational table -> FAIL/C
    A = {"A": Fraction(1001, 1000), "B": Fraction(998, 1000)}
    Bp = {(60, 2, "FeeSaver"): Fraction(105, 100), (80, 2, "FeeSaver"): Fraction(1056, 1000), (90, 2, "FeeSaver"): Fraction(106, 100)}
    multab = _mk_frac([(c, p[0], p[1], p[2], (A[c] * Bp[p] - 1) * 100, 0, 0, ML) for c in A for p in Bp])
    r = c_multiplicative(multab)
    check(r["passed"] is False and r["grid"] == "C", f"B148-7 multiplicative table: {r['passed']} {r['grid']}")
    cross = _mk([
        ("A", 80, 5, "FeeSaver", "5.38", 0, 500, ML), ("B", 80, 5, "FeeSaver", "5.39", 0, 350, ML),
        ("A", 90, 5, "FeeSaver", "5.46", 0, 500, ML), ("B", 90, 5, "FeeSaver", "5.44", 0, 350, ML)])
    r = c_multiplicative(cross)
    check(r["passed"] is True and r["n_crossing_groups"] == 1, "B148-7 crossing group not found")

    # B148-8: no boundary with unchanged incentive -> FAIL (empty)
    nob = _mk([
        ("A", 80, 2, "FeeSaver", "5.49", 0, 350, ML), ("B", 80, 2, "FeeSaver", "5.44", 0, 250, ML),
        ("A", 85, 2, "FeeSaver", "5.59", 0, 500, ML), ("B", 85, 2, "FeeSaver", "5.54", 0, 0, ML)])
    check(c_boundaries(nob)["passed"] is False, "B148-8 seeded empty boundary set passed")
    yesb = _mk([
        ("A", 80, 2, "FeeSaver", "5.49", 0, 350, ML), ("B", 80, 2, "FeeSaver", "5.44", 0, 250, ML),
        ("A", 85, 2, "FeeSaver", "5.59", 0, 350, ML), ("B", 85, 2, "FeeSaver", "5.50", 0, 250, ML)])
    rb = c_boundaries(yesb)
    check(rb["passed"] is True and rb["boundaries"][0]["class_x_boundary_units"]["A-B"] == "4",
          "B148-8 boundary fixture: expected one boundary with a 4-unit class x boundary square")

    # B148-9: same values at a position -> count 1
    same = _mk([("F", 60, 2, "FeeSaver", "5.30", 0, 0, ML), ("M", 60, 2, "FeeSaver", "5.30", 0, 0, ML),
                ("R", 60, 2, "FeeSaver", "5.30", 0, 300, ML), ("E", 60, 2, "FeeSaver", "5.30", 0, 0, ML)])
    r = c_count(same)
    check(r["positions"][0]["n_values"] == 1, "B148-9 seeded single value not counted as 1")

    # B148-10: zero cashback -> full square equals the interest square, computed independently
    fc = _mk([
        ("A", 60, 2, "FeeSaver", "5.36", 0, 0, ML), ("B", 60, 2, "FeeSaver", "5.29", 0, 250, ML),
        ("A", 80, 2, "FeeSaver", "5.49", 0, 0, ML), ("B", 80, 2, "FeeSaver", "5.44", 0, 0, ML)])
    res = c_fullcost(fc)
    check(res["n_squares"] == 1, "B148-10 expected one non-neutral square")
    # independent month-by-month interest
    def interest_loop(rate, L, n):
        i = Fraction(rate) / 1200
        g = (1 + i) ** AMORT_MONTHS
        pay = Fraction(L) * i * g / (g - 1)
        bal, tot = Fraction(L), Fraction(0)
        for _ in range(n):
            it = bal * i
            tot += it
            bal = bal + it - pay
        return tot
    L = 100_000
    want = (interest_loop("5.36", L, 24) - (interest_loop("5.29", L, 24) - 250)
            - interest_loop("5.49", L, 24) + interest_loop("5.44", L, 24))
    if res["squares"] and res["squares"][0]["pounds"]:
        got = Fraction(res["squares"][0]["pounds"][0])
        check(abs(got - want) < Fraction(1, 100), f"B148-10 full square {float(got):.4f} vs loop {float(want):.4f}")
    else:
        check(False, "B148-10 fixture produced no full-cost square")
    # cashback enters with weight exactly one
    c1 = {"rate": Fraction("5.29"), "fee": 0, "inc": 250, "max_loan": ML}
    c0 = {"rate": Fraction("5.29"), "fee": 0, "inc": 0, "max_loan": ML}
    check(full_cost(c0, L, 2) - full_cost(c1, L, 2) == 250, "B148-10 cashback not subtracted")

    # B148-3: seeded mismatch -> FAIL; seeded end-date change -> third state
    def known_rows(f2="5.36", end2="31.01.2029"):
        m = {}
        for (cls, ltv, per, kind), v in KNOWN.items():
            m[(cls, ltv, per, kind, "num")] = {"rate": v, "end_date": VERSION_MARKS[per]}
        m[("F", 60, 2, "FeeSaver", "num")] = {"rate": f2, "end_date": end2}
        return m
    check(c_known(known_rows(), {})["passed"] is True, "B148-3 clean fixture did not pass")
    check(c_known(known_rows(f2="5.37"), {})["passed"] is False, "B148-3 seeded 5.37 did not FAIL")
    check(c_known(known_rows(end2="31.03.2029"), {})["passed"] is None, "B148-3 seeded new end date not third state")

    # B148-1: seeded rate change in read 2 -> shelved; seeded missing incentive -> shelved
    def r_(read, rate="5.36", inc=0):
        return {"page": "F", "ltv": 60, "period": 2, "kind": "FeeSaver", "rate": rate, "fee": 0, "incentive": inc,
                "max_loan": ML, "follow_on": "6.24", "end_date": "31.01.2029", "line": "x", "file": "f", "read": read}
    con = consistency([r_(1), r_(2, rate="5.37")])
    check(len(con["shelved"]) == 1 and "differs" in list(con["shelved"].values())[0], "B148-1 two-read mismatch not shelved")
    con = consistency([r_(1, inc=None), r_(2, inc=None)])
    check(len(con["shelved"]) == 1 and "missing" in list(con["shelved"].values())[0], "B148-1 missing incentive not shelved")
    ci = c_instrument(consistency([r_(1), r_(2, rate="5.37")]), {p: True for p in CLASSES})
    check(ci["passed"] is False, "B148-1 page with all rows shelved did not FAIL")

    # B148-2: seeded missing hash -> FAIL; second read 2 h later -> pending
    def man(sha="x" * 64, second="2026-10-15T10:30:00-04:00"):
        s1 = {"file": "a", "read": 1, "url": "u", "offset": 0, "prompt": "p", "sha256": sha,
              "fetched_after": "2026-10-14T09:53:00-04:00", "fetched_before": "2026-10-14T10:01:00-04:00"}
        s2 = dict(s1, read=10, sha256="y" * 64, fetched_after=second, fetched_before=second)
        return {"snapshots": [s1, s2]}
    check(c_bookkeeping(man())["passed"] is True, "B148-2 clean manifest did not pass")
    check(c_bookkeeping(man(sha=""))["passed"] is False, "B148-2 seeded missing hash did not FAIL")
    check(c_bookkeeping(man(second="2026-10-14T12:00:00-04:00"))["passed"] is None,
          "B148-2 second read 2 h later not pending")

    # Premier: both partitions must be analysed
    parts = {"product": 1, "classline": 1}
    if MUT == "onepart":
        parts.pop("classline")
    check(c_premier_both(parts), "Premier: only one partition analysed")

    # Parser: three row shapes from the snapshots
    t = ("Fixed-rate mortgages | 60% | 2 Years fixed rate until 31.01.2029 | 2 Year Fixed Fee Saver | 5.36% fixed | £0 | £250 | £2,000,000 | 6.24%\n"
         "80% Maximum Loan to Value (LTV) | 80% | 2 Years fixed rate until 31.01.2029 | 2 Year Fixed Standard | 5.50% fixed | £999 | Cashback £300 | £2,000,000 | 6.24%\n"
         "80% | 5 Year Fixed Premier Standard | 4.99% fixed | £999 | £0 | £2,000,000 | 6.24% | 31.01.2032\n")
    t += ("- 60% | 2yr to 31.01.2029 | 2 Year Fixed Fee Saver Buy To Let | 5.06% | £0 | £0 | £2,000,000 | 7.25%\n"
          "80% LTV | 5 Years fixed rate until 31.01.2032 | 5 Year Fixed Standard | 5.39% fixed | £999 | Standard Legal Fees* | £ 2,000,000 | 6.24%\n")
    pr = parse_snapshot(t, "F")
    check(len(pr) == 4, f"parser: expected 4 rows (buy-to-let dropped), got {len(pr)}")
    if len(pr) == 4:
        check(pr[3]["ltv"] == 80 and pr[3]["incentive"] == "LF" and pr[3]["max_loan"] == ML, "parser row 4 fields")
        check(pr[0]["incentive"] == 250 and pr[0]["fee"] == 0 and pr[0]["max_loan"] == ML, "parser row 1 fields")
        check(pr[1]["incentive"] == 300 and pr[1]["fee"] == 999, "parser row 2 fields")
        check(pr[2]["kind"] == "PremierStandard" and pr[2]["period"] == 5 and pr[2]["end_date"] == "31.01.2032",
              "parser row 3 fields")

    # ---- Barclays sheet -------------------------------------------------------------
    def brow(page, row, name, rate, fee, ltv, loan, end="31/12/2028", erc="2% of balance repaid",
             heading="2 Year Fixed Rates", fol="Residential Tracker at BEBR which is variable, currently 3.75% + 1.99% = 5.74% for term"):
        return {"page": page, "row": row, "heading": heading, "table": 0, "cells": {
            "Product Type": name, "Initial Interest Rate": rate, "Product Fee": fee, "LTV": ltv,
            "Minimum/Maximum Loan Size": loan, "Product/ ERC end date": end, "Early Repayment Charge": erc,
            "Follow On Rate": fol, "Overall Cost for Comparison": "5.9% APRC"}}
    # cell classification
    c = barclays_cell(brow(4, 25, "The Great Escape™ 2 Yr Fixed", "5.50%", "£0", "60%", "£50000 - £2m"), "R")
    check(c["kind"] == "GreatEscape-NoFee" and c["inc"] == "GE" and c["max_loan"] == 2_000_000 and c["src"] == "p4 r25",
          f"Barclays cell: Great Escape {c['kind']} {c['inc']}")
    c = barclays_cell(brow(4, 20, "2 Yr Fixed", "5.31%", "£1,999", "60%", "£2m - £10m"), "R")
    check(c["kind"] == "Std-Large-Fee" and c["inc"] == 0, f"Barclays cell: large remortgage {c['kind']} {c['inc']}")
    c = barclays_cell(brow(7, 31, "EMC Reward 2 Yr Fixed", "5.74%", "£0", "Over 90%", "£1000 - £2m"), "E")
    check(c["ltv"] == 91 and c["period"] == 2 and c["kind"] == "Std-NoFee", f"Barclays cell: Over 90% read as {c['ltv']}")
    # fee square: purchase 899 and existing 999 on the fee tier, nothing on the no-fee tier
    fsq = _mk([("P", 60, 2, "Std-Fee", "5.15", 899, 0, ML), ("E", 60, 2, "Std-Fee", "5.21", 999, 0, ML),
               ("P", 60, 2, "Std-NoFee", "5.40", 0, 0, ML), ("E", 60, 2, "Std-NoFee", "5.40", 0, 0, ML),
               ("P", 75, 2, "Std-Fee", "5.30", 899, 0, ML), ("E", 75, 2, "Std-Fee", "5.34", 999, 0, ML)])
    check(not neutral(fsq, "E", "P", (60, 2, "Std-Fee"), (60, 2, "Std-NoFee")),
          "a square across fee tiers with class-specific fees stayed incentive-neutral")
    check(neutral(fsq, "E", "P", (60, 2, "Std-Fee"), (75, 2, "Std-Fee")), "a fee-square-zero pair left the neutral set")
    rb5 = c_bare(fsq)
    check(rb5["n_positions"] == 1, f"B148-5 compared two classes with different fees: {rb5['n_positions']} positions")
    # B148-1-Barclays: the text path disagreeing on a rate must FAIL; a header naming another column must FAIL
    good_rows = [brow(1, 21 + i, "2 Yr Fixed", f"5.{15 + i}%", "£899", "60%", "£5000 - £2m") for i in range(3)]
    text_rows = [{"page": 1, "product": "2 Yr Fixed", "rate": f"5.{15 + i}%", "fee": "£899", "ltv": "60%",
                  "loan": "£5000 - £2m", "end": "31/12/2028"} for i in range(3)]
    hdr = ["p1 r3: Product Type | Initial Interest Rate | Product Fee | LTV | Minimum/Maximum Loan Size | "
           "Product/ ERC end date | Early Repayment Charge | Follow On Rate | Overall Cost for Comparison"]
    bdoc = {"rows": good_rows, "text_path_rows": text_rows, "column_header_rows": hdr}
    check(c_instrument_barclays(bdoc, {1})["passed"] is True, "B148-1-Barclays clean fixture did not pass")
    bad_text = [dict(text_rows[0], rate="5.18%")] + text_rows[1:]
    check(c_instrument_barclays(dict(bdoc, text_path_rows=bad_text), {1})["passed"] is False,
          "B148-1-Barclays seeded rate disagreement between the two paths did not FAIL")
    check(c_instrument_barclays(dict(bdoc, column_header_rows=[hdr[0].replace("Initial Interest Rate", "APRC")]), {1})["passed"]
          is False, "B148-1-Barclays seeded wrong rate column did not FAIL")
    # B148-2-Barclays: a page missing from the coverage table, or a length off by one, must FAIL
    pdf = b"%PDF-1.7 fixture %%EOF"
    sha = hashlib.sha256(pdf).hexdigest()
    man = {"versions": [{"file": "x.pdf", "bytes": len(pdf), "sha256": sha}]}
    cov = [{"page": p, "opened": True, "tables": 1, "rate_rows": 0 if p == 3 else 5} for p in (1, 2, 3)]
    bk = {"source": {"sha256": sha, "pages": 3}, "coverage": cov, "rows": good_rows}
    check(c_bookkeeping_barclays(bk, man, pdf)["passed"] is True, "B148-2-Barclays clean fixture did not pass")
    check(c_bookkeeping_barclays(dict(bk, coverage=cov[:2]), man, pdf)["passed"] is False,
          "B148-2-Barclays seeded missing zero-row page did not FAIL")
    check(c_bookkeeping_barclays(bk, man, pdf + b" ")["passed"] is False, "B148-2-Barclays seeded length change did not FAIL")
    # B148-3-Barclays: a tracker rate one unit off Bank Rate plus margin must FAIL and be named
    trk = [brow(1, 10, "2 Yr Tracker at BEBR +0.42%", "4.17%", "£999", "60%", "£5000 - £2m", end="2 Years", erc="None")]
    kd = {"source": {"bebr_printed": "3.75", "rates_effective": "16 October 2026"}, "rows": trk}
    check(c_known_barclays(kd)["passed"] is True, "B148-3-Barclays clean tracker did not pass")
    trk_bad = [brow(1, 10, "2 Yr Tracker at BEBR +0.42%", "4.18%", "£999", "60%", "£5000 - £2m", end="2 Years", erc="None")]
    kb = c_known_barclays(dict(kd, rows=trk_bad))
    check(kb["passed"] is False and any("p1 r10" in m for m in kb["mismatches"]),
          "B148-3-Barclays seeded tracker rate 4.18 did not FAIL with its source")
    check(c_known_barclays(dict(kd, source={"bebr_printed": None}))["passed"] is None,
          "B148-3-Barclays without Bank Rate did not fall to the third state")

    for f in fails:
        print("SELFTEST FAIL:", f)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


MUTATIONS = ("sign", "noinc", "float", "nocash", "onepart", "nofee")


def mutation_test() -> int:
    caught = {}
    for m in MUTATIONS:
        env = dict(os.environ, B148_MUT=m)
        p = subprocess.run([sys.executable, "-B", __file__, "--selftest"], env=env,
                           capture_output=True, text=True, encoding="utf-8")
        caught[m] = p.returncode != 0
        print(f"mutation {m:8s} caught={caught[m]}  " + (p.stdout.strip().splitlines() or [""])[0][:150])
    missed = [m for m, c in caught.items() if not c]
    print(f"mutation test: {len(MUTATIONS) - len(missed)}/{len(MUTATIONS)} caught; missed {missed}")
    return 1 if missed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mutation-test", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.mutation_test:
        return mutation_test()
    if a.transcribe:
        return transcribe()
    return run()


if __name__ == "__main__":
    sys.exit(main())
