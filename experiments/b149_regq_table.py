"""B149: Regulation Q ceilings as a holder-class by position table, one table per revision.

Reads the hand transcription in data/b149_regq_cells.json (every fixed ceiling read
from the circular's page image, the OCR token kept only as an index), builds for each
revision the table C(a, j) with a in {o, g, k} (ordinary depositor, governmental unit,
IRA/Keogh) and j a member-bank maturity band, and prints:

  the full table; distinct values per row and over the table in two scopes;
  holder clauses; the bipartite class-position graph V, E, b1 under two edge
  conventions; every single-position class gap and every square with its multiple
  of the 0.25-point floor; the zero-domain cells; eight criteria B149-1 .. B149-8.

    python -B experiments/b149_regq_table.py              # run, write the record
    python -B experiments/b149_regq_table.py --selftest   # fixtures, seeds, mutation run

Values are integers in basis points. Floating categories ((f), (g)) are rule tokens
and only enter the zero-domain criterion.
"""
from __future__ import annotations

import copy
import itertools
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, r"E:\better economics")

HERE = Path(__file__).resolve().parent.parent
CELLS = HERE / "data" / "b149_regq_cells.json"
RECORD = HERE / "results" / "b149_regq_class_table.json"
SESSION = "B149_1029"

FLOOR_BP = 25
CLASSES = ("o", "g", "k")
FULL_REVS = ("1975-12-04", "1978-06-01", "1979-07-01", "1979-08-01", "1980-01-01")
# revisions read in the second pass: 1966 (one class), 1974 (the (d) clause appears), 1980-10 (one DIDC position)
NEW_TABLE_REVS = ("1966-09-26", "1974-11-27", "1980-10-30")
# partial tables read in the third pass (T20): rows where a fixed ceiling still binds
T20_TABLE_REVS = ("1981-01-15", "1982-09-01", "1983-10-01", "1984-01-01")
ALL_TABLE_REVS = tuple(sorted(FULL_REVS + NEW_TABLE_REVS + T20_TABLE_REVS))
ZERO_DOMAIN_REVS = ("1978-06-01", "1979-07-01", "1979-08-01", "1980-01-01", "1982-09-01", "1983-01-05", "1983-10-01",
                    "1986-01-01")
WINDOW = ("1966-09-21", "1986-03-31")
DIDC_START = "1980-03-31"
MUTANT = os.environ.get("B149_MUTANT", "")

RIVAL_PREMISE = ("A scalar on positions: at one institution, one maturity band, one kind of insured "
                 "time deposit under $100,000, one price for every depositor.")
RIVAL_ENTAILMENT_5 = "P(a, j) = phi(j) implies C(a, j) - C(o, j) = 0 on every cell."
RIVAL_ENTAILMENT_6 = ("The additive form P(a, j) = phi(j) + psi(a) implies every square "
                      "Delta(a; j) - Delta(a; j') = 0, a constant bank/thrift gap included.")


def fmt(bp):
    return None if bp is None else f"{bp / 100:.2f}"


def load(path=CELLS):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- tables
def table(data, rev, convention=1):
    """C(a, j) for one revision from the non-duplicate cells. Convention 2 gives k an
    edge below three years at the ordinary ceiling (8102 p1: retirement savers may use
    other time deposits, which stay under the existing ceilings)."""
    T = {}
    for c in data["cells"]:
        if c["rev"] != rev or c.get("duplicate"):
            continue
        T[(c["class"], c["position"])] = c["value_bp"]
    if MUTANT == "fill_zero":
        for p in data["positions"]:
            T.setdefault(("k", p), 0)
    if MUTANT == "f_fixed":
        for a in CLASSES:
            T[(a, "mmc26w")] = 0
    if MUTANT == "d_six_months" and rev == "1978-06-01":
        T.pop(("g", "m1"), None)
    if convention == 2 and any(a == "k" for (a, _) in T):
        for p in data["positions"]:
            if ("k", p) not in T and ("o", p) in T:
                T[("k", p)] = T[("o", p)]
    return T


ORDER = ("d7_31_u2500", "d14_89", "m1", "m2", "m3", "t30m_4y", "m4a", "m4b", "t4y_u1000", "t4y_1000", "t4y_6y_u1000",
         "t4y_6y_1000", "t6y_u1000", "t6y_1000", "m5", "m6", "m7",
         "s66_multi_lt90", "s66_multi_90plus", "s66_single")


def positions_of(T):
    return sorted({p for (_, p) in T}, key=lambda p: (ORDER.index(p) if p in ORDER else len(ORDER), p))


def delta(T, a, p):
    if (a, p) not in T or ("o", p) not in T:
        return None
    if MUTANT == "sign_flip":
        return T[("o", p)] - T[(a, p)]
    return T[(a, p)] - T[("o", p)]


def deltas(T, a):
    return {p: delta(T, a, p) for p in positions_of(T) if delta(T, a, p) is not None}


def squares(T, a, b="o"):
    """S(a; j, j') = (C(a,j) - C(b,j)) - (C(a,j') - C(b,j')) on every pair of positions
    where both classes have an edge."""
    ps = [p for p in positions_of(T) if (a, p) in T and (b, p) in T]
    out = []
    for j, jj in itertools.combinations(ps, 2):
        s = (T[(a, j)] - T[(b, j)]) - (T[(a, jj)] - T[(b, jj)])
        out.append({"pair": f"{j}|{jj}", "S_bp": s, "floor_multiple": abs(s) / FLOOR_BP})
    return out


def graph(T):
    """V, E, components, b1 = E - V + components of the bipartite class-position graph."""
    nodes = set()
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, p) in T:
        for n in (("c", a), ("p", p)):
            nodes.add(n)
            parent.setdefault(n, n)
        ra, rp = find(("c", a)), find(("p", p))
        if ra != rp:
            parent[ra] = rp
    comps = len({find(n) for n in nodes})
    V, E = len(nodes), len(T)
    return {"V": V, "E": E, "components": comps, "b1": E - V + comps}


# ----------------------------------------------------------------------------- foreign official holders (f)
# Fourth holder class, added 2026-10-29: 217.3(g) (217.3(a) before 1968-10-15) takes time deposits of foreign
# official holders out of 217.7 up to a maturity limit. The o, g, k computations above and below are untouched;
# f is computed beside them and printed under its own keys.
F_NO_CEILING = "NO_CEILING"


def f_period(data, rev):
    fo = data.get("foreign_official")
    if not fo or MUTANT == "skip_f":
        return None
    day = rev[:10]
    for p in fo["periods"]:
        if p["from"] <= day <= p["to"]:
            return p
    return None


def f_part(data, pos, limit):
    """Where a position lies against the maturity limit: inside, outside, straddling (or all, with no limit)."""
    if limit is None:
        return "inside"
    lo, hi = data["foreign_official"]["position_bounds_months"][pos]
    if hi is not None and hi <= limit:
        return "inside"
    if lo >= limit:
        return "outside"
    return "straddles"


def f_row(data, rev):
    """f on every numeric position of the revision's table (convention 1): the ceiling-free value inside the limit,
    o's number outside it, both on a straddling position."""
    per = f_period(data, rev)
    if per is None:
        return None
    T = table(data, rev)
    out = {}
    for p in positions_of(T):
        if ("o", p) not in T:
            continue
        part = f_part(data, p, per["limit_months"])
        val = {"inside": F_NO_CEILING, "outside": fmt(T[("o", p)]),
               "straddles": f"{F_NO_CEILING} to {per['limit_months']} months, {fmt(T[('o', p)])} above"}[part]
        out[p] = {"part": part, "value": val, "differs_from_o": part != "outside"}
    return out


def f_rule_cells(data, rev):
    """f against o on the rule-written positions of the revision: inside the limit f has no ceiling, outside it f
    follows o's rule. Same value as o -> a zero-domain cell; different -> a class-line cell."""
    per = f_period(data, rev)
    if per is None:
        return []
    out = []
    for r in data["rules"]:
        if r["rev"] != rev or r["class"] != "o":
            continue
        part = f_part(data, r["position"], per["limit_months"])
        if part == "outside" or r["rule"] == F_NO_CEILING:
            tok = r["rule"]
        elif part == "inside":
            tok = F_NO_CEILING
        else:
            tok = f"{F_NO_CEILING}_TO_{per['limit_months']}M_THEN_{r['rule']}"
        out.append({"cell": f"{rev}|f-o|{r['position']}", "part": part, "rules": {"o": r["rule"], "f": tok},
                    "state": "same" if tok == r["rule"] else "differs"})
    return out


def f_block(data, rev):
    row = f_row(data, rev)
    if row is None:
        return None
    T = table(data, rev)
    Tf = dict(T)
    for p in row:
        Tf[("f", p)] = 0  # an edge; the value is not used by graph()
    sq = {"zero": 0, "nonzero_rule": 0, "undefined": 0}
    for j, jj in itertools.combinations(list(row), 2):
        a, b = row[j]["differs_from_o"], row[jj]["differs_from_o"]
        sq["zero" if not (a or b) else ("undefined" if (a and b) else "nonzero_rule")] += 1
    return {"row": row, "cells_differing_from_o": sum(v["differs_from_o"] for v in row.values()),
            "graph_with_f_convention_1": graph(Tf), "squares_f_o": sq,
            "squares_note": ("zero: both positions outside the limit (f carries o's number); nonzero_rule: one inside, "
                             "one outside (a ceiling-free value against o's ceiling); undefined: both inside, the class "
                             "value is not a number and the difference is not filled with zero"),
            "rule_cells": f_rule_cells(data, rev)}


def distinct(data, rev, T):
    rows = {a: sorted({v for (b, _), v in T.items() if b == a}) for a in CLASSES}
    member = sorted(set(T.values()))
    thrift = sorted({t["value_bp"] for t in data["thrift_cells"] if t["rev"] == rev and "value_bp" in t})
    combined = sorted(set(member) | set(thrift))
    o_vals = set(rows["o"])
    class_only = sorted(set(member) - o_vals)
    class_only_combined = sorted(set(combined) - o_vals - set(thrift))
    return {
        "per_row": {a: {"n": len(v), "values": [fmt(x) for x in v]} for a, v in rows.items()},
        "member_bank_table": {"n": len(member), "values": [fmt(x) for x in member],
                              "values_only_on_class_rows": [fmt(x) for x in class_only]},
        "all_insured_combined": {"n": len(combined), "values": [fmt(x) for x in combined],
                                 "values_only_on_class_rows": [fmt(x) for x in class_only_combined],
                                 "thrift_cells_read": [fmt(x) for x in thrift],
                                 "complete": False,
                                 "note": "thrift fixed table not read (Federal Register / FHLBB pending); only the thrift values printed in the opened circulars enter"},
    }


# ----------------------------------------------------------------------------- criteria
def c1_instrument(data):
    cells = data["cells"]
    key = {f'{c["rev"]}|{c["class"]}|{c["position"]}|{c["source"]}|{c["page"]}': c
           for c in cells if not c.get("duplicate")}
    no_image = [f'{c["rev"]}|{c["class"]}|{c["position"]}' for c in cells
                if c["method"] not in ("page_image", "page_image_carried_back", "page_image_carried_forward")
                or c.get("image_reading") is None]
    value_not_image = [f'{c["rev"]}|{c["class"]}|{c["position"]}' for c in cells
                       if c.get("image_reading") is not None and c["image_reading"] != fmt(c["value_bp"])]
    grid_vals = [(f'{c["rev"]}|{c["class"]}|{c["position"]}', c["value_bp"]) for c in cells]
    grid_vals += [(f'savings|{s["rev"]}|{s["institution"]}', s["value_bp"]) for s in data["savings"]]
    off_grid = [k for k, v in grid_vals if MUTANT != "no_grid_check" and v % FLOOR_BP]
    dup_bad = []
    n_dup = 0
    if MUTANT != "dup_skip":
        for c in cells:
            if c.get("duplicate"):
                n_dup += 1
                orig = key.get(c["dup_of"])
                if orig is None or orig["value_bp"] != c["value_bp"]:
                    dup_bad.append(c["dup_of"])
    T = {r: table(data, r) for r in ALL_TABLE_REVS}
    sav = {(s["rev"], s["institution"]): s["value_bp"] for s in data["savings"]}
    narr_bad, narr_registered, narr_ok = [], [], []
    for n in data["narrative_checks"]:
        reg = n.get("registered_discrepancy")
        for i, (rev, a, p, v) in enumerate(n.get("claims", [])):
            got = T.get(rev, {}).get((a, p))
            if got == v:
                narr_ok.append(f'{n["id"]}[{i}]')
            elif reg and reg["claim_index"] == i:
                narr_registered.append({"id": f'{n["id"]}[{i}]', "narrative": fmt(v), "table": fmt(got), "note": reg["note"]})
            else:
                narr_bad.append({"id": f'{n["id"]}[{i}]', "narrative": fmt(v), "table": fmt(got)})
        if "diff" in n:
            d = n["diff"]
            rev, a, p = d["cell"]
            got = sav.get((d["savings_rev"], "member bank"), 0) - T.get(rev, {}).get((a, p), 0)
            (narr_ok if got == d["value_bp"] else narr_bad).append(
                n["id"] if got == d["value_bp"] else {"id": n["id"], "narrative": fmt(d["value_bp"]), "table": fmt(got)})
    # DIDC block: institution-axis cells (8869) and the passbook read-back (9177) obey the same three rules
    didc = data.get("didc", {})
    dcells = (didc.get("institution_axis", []) + didc.get("passbook_readback", [])
              + didc.get("institution_axis_19810801", []))
    for c in dcells:
        tag = f'didc|{c["rev"]}|{c["institution"]}|{c.get("account", "savings")}'
        if c.get("method") != "page_image" or c.get("image_reading") is None:
            no_image.append(tag)
        elif c["image_reading"] != fmt(c["value_bp"]):
            value_not_image.append(tag)
        if MUTANT != "no_grid_check" and c["value_bp"] % FLOOR_BP:
            off_grid.append(tag)
    inst = {(c["institution"], c["account"]): c["value_bp"] for c in didc.get("institution_axis", [])}
    for c in ([] if MUTANT == "skip_passbook" else didc.get("passbook_readback", [])):
        tag = f'9177-passbook|{c["institution"]}'
        if inst.get((c["institution"], "savings")) == c["value_bp"]:
            narr_ok.append(tag)
        else:
            narr_bad.append({"id": tag, "narrative": fmt(c["value_bp"]), "table": fmt(inst.get((c["institution"], "savings")))})
    # k line: the 9196 reaffirmation read back against 9177 (rule) and 9210 (rescission), property by property
    k_rb = [] if MUTANT == "skip_9196" else didc.get("k_readback", [])
    for r in k_rb:
        tag = f'k-readback|{r["a_source"]}-{r["b_source"]}|{r["property"]}'
        if r.get("method") != "page_image":
            no_image.append(tag)
        if r["a_value"] == r["b_value"]:
            narr_ok.append(tag)
        else:
            narr_bad.append({"id": tag, "narrative": r["a_value"], "table": r["b_value"]})
    s_noimg, s_sum, s_memo = ([], [], []) if MUTANT == "skip_survey_checks" else survey_checks(data)
    no_image += s_noimg
    passed = not (no_image or value_not_image or off_grid or dup_bad or narr_bad or s_sum or s_memo)
    return {"name": "B149-1", "kind": "instrument", "passed": passed,
            "detail": (f"{len(cells)} member-bank cells ({n_dup} second printings) and {len(dcells)} DIDC-period cells; "
                       f"k-line read-backs (9196 against 9177 and 9210) {len(k_rb)}; "
                       f"without an image reading {len(no_image)}; "
                       f"value differs from image reading {len(value_not_image)}; off the quarter-point grid {len(off_grid)}; "
                       f"second printing disagreeing {len(dup_bad)}; narrative checks agreeing {len(narr_ok)}, "
                       f"disagreeing unregistered {len(narr_bad)}, source-internal discrepancies registered {len(narr_registered)}"
                       + (f"; survey readings {len(data.get('binding_surveys', []))} and table 1.16 issues "
                          f"{len(data.get('table_1_16', []))}: sums off {len(s_sum)}, memo above its interval {len(s_memo)}"
                          if data.get("binding_surveys") else "")),
            "survey_sums_off": s_sum, "survey_memo_over_interval": s_memo,
            "no_image": no_image, "value_not_image": value_not_image, "off_grid": off_grid,
            "second_printing_disagreeing": dup_bad, "narrative_disagreeing": narr_bad,
            "narrative_registered_discrepancies": narr_registered}


def reading_measure(r, m, cell_bp):
    """One survey reading, one measure (0 banks, 1 dollars), against the cell's ceiling.

    The paying-ceiling memo is a sub-column of one interval (memo_in, default the last); that interval is split into
    the memo and the rest. If the memo counts the cell's own ceiling: bound when the memo share is strictly the largest
    part, below otherwise (every other part pays less than the ceiling). If the memo counts another ceiling: below
    when the largest interval lies wholly under the cell's ceiling, otherwise not decidable."""
    br = r["brackets"]
    k = r.get("memo_in", len(br) - 1)
    memo = r["memo"][m]
    if MUTANT == "banks_only":
        memo = r["memo"][0]
        m = 0
    if r["memo_ceiling_bp"] == cell_bp:
        parts = [(b[0], b[3 + m]) for i, b in enumerate(br) if i != k]
        parts.append((br[k][0] + " below the ceiling", br[k][3 + m] - memo))
        top = max(v for _, v in parts)
        return "bound" if memo > top else "below"
    largest = max(br, key=lambda b: b[3 + m])
    ties = [b for b in br if b[3 + m] == largest[3 + m]]
    if len(ties) == 1 and largest[2] is not None and largest[2] < cell_bp:
        return "below"
    return None


def reading_state(r, cell_bp):
    s = [reading_measure(r, m, cell_bp) for m in (0, 1)]
    if MUTANT == "banks_only":
        return {"banks": s[0], "dollars": s[0], "state": s[0]}
    return {"banks": s[0], "dollars": s[1], "state": s[0] if s[0] == s[1] else None}


def binding_detail(data, rev, a, p):
    """The binding reading behind one cell: seeds first (self-test), then the survey map."""
    for b in data["binding"]:
        if b["rev"] == rev and b["class"] == a and b["position"] == p:
            if b.get("most_common_bp") is None:
                return {"state": None, "via": "seed without a rate"}
            ceil = table(data, rev).get((a, p))
            return {"state": b["most_common_bp"] == ceil, "via": "seed"}
    rd = {r["id"]: r for r in data.get("binding_surveys", [])}
    for e in data.get("binding_map", []):
        if e["rev"] == rev and e["class"] == a and e["position"] == p:
            ceil = table(data, rev).get((a, p))
            per = {i: reading_state(rd[i], ceil) for i in e["readings"]}
            sts = {v["state"] for v in per.values()}
            st = sts.pop() if len(sts) == 1 else None
            return {"state": {"bound": True, "below": False, None: None}[st], "via": "survey", "readings": per}
    return {"state": None, "via": "no source"}


def binding_state(data, rev, a, p):
    return binding_detail(data, rev, a, p)["state"]


def c2_premise(data):
    states, details = {}, {}
    for rev in FULL_REVS:
        for (a, p) in table(data, rev):
            dt = binding_detail(data, rev, a, p)
            states[f"{rev}|{a}|{p}"] = dt["state"]
            details[f"{rev}|{a}|{p}"] = dt
    vals = list(states.values())
    if any(v is False for v in vals):
        passed = False
    elif vals and all(v is True for v in vals):
        passed = True
    else:
        passed = None
    by_class = {}
    for key, v in states.items():
        a = key.split("|")[1]
        c = by_class.setdefault(a, {"bound": 0, "below": 0, "undecided_or_no_source": 0})
        c["bound" if v is True else "below" if v is False else "undecided_or_no_source"] += 1
    surveys = sorted({r["survey_date"] for r in data.get("binding_surveys", [])})
    mapping = {"the ceiling is the most common rate paid (banks and dollars agree)": True,
               "the most common rate paid is below the ceiling (banks and dollars agree)": False,
               "banks and dollars disagree, or the source's ceiling differs and its modal interval reaches the cell's, "
               "or no source": None}
    return {"name": "B149-2", "kind": "premise", "passed": passed,
            "detail": (f"survey readings {len(data.get('binding_surveys', []))} from the surveys of {surveys} "
                       f"(Federal Reserve Bulletin); cells bound {sum(v is True for v in vals)}, below "
                       f"{sum(v is False for v in vals)}, undecided or no source {sum(v is None for v in vals)} of {len(vals)}; "
                       f"by class {by_class}"),
            "state_to_verdict": mapping, "by_class": by_class, "cells_by_state": {
                "bound": sorted(k for k, v in states.items() if v is True),
                "below": sorted(k for k, v in states.items() if v is False),
                "no_source": len([1 for v in vals if v is None]),
                "undecided": sorted(k for k, v in states.items() if v is None and details[k]["via"] == "survey")},
            "cell_readings": {k: v for k, v in details.items() if v["via"] == "survey"}}


def survey_checks(data):
    """B149-1 for the survey readings: every one read from a page image; parts add up to the total (counts within 3 of
    the printed total, percent within 0.3 of 100); the memo is not larger than the interval it sits in."""
    no_image, sum_off, memo_over = [], [], []
    for r in data.get("binding_surveys", []):
        if r.get("method") != "page_image":
            no_image.append(r["id"])
        k = r.get("memo_in", len(r["brackets"]) - 1)
        for m in (0, 1):
            s = sum(b[3 + m] for b in r["brackets"])
            tot, tol = (r["total"][m], 3) if r["unit"] == "count" else (100.0, 0.3)
            if abs(s - tot) > tol:
                sum_off.append(f'{r["id"]}[{m}] {s} vs {tot}')
            if r["memo"][m] > r["brackets"][k][3 + m] + 1e-9:
                memo_over.append(f'{r["id"]}[{m}]')
    for t in data.get("table_1_16", []):
        if t.get("method") != "page_image":
            no_image.append("table_1_16 " + t["in_effect"])
    return no_image, sum_off, memo_over


def c3_known(data):
    T = {r: table(data, r) for r in FULL_REVS}
    sav = {(s["rev"], s["institution"]): s["value_bp"] for s in data["savings"]}
    reads = {}
    rows = []
    for k in data["known_answers"]:
        if "read_bp" in k:
            got = k["read_bp"]
        elif "derived" in k:
            x, y = [s.strip() for s in k["derived"].split("-")]
            got = reads.get(x, None)
            got = None if got is None or reads.get(y) is None else got - reads[y]
        elif "cell" in k:
            rev, a, p = k["cell"]
            got = T.get(rev, {}).get((a, p))
        elif "diff_savings_minus_cell" in k:
            rev, a, p = k["diff_savings_minus_cell"]
            s = sav.get((rev, "member bank"))
            c = T.get(rev, {}).get((a, p))
            got = None if s is None or c is None else s - c
        elif "pair" in k:
            got = [T.get(r, {}).get((a, p)) for r, a, p, _ in k["pair"]]
        reads[k["id"]] = got
        exp = [v for *_, v in k["pair"]] if "pair" in k else k["expected_bp"]
        if got is None or (isinstance(got, list) and None in got):
            st = None
        else:
            st = got == exp
        rows.append({"id": k["id"], "what": k["what"], "read": fmt(got) if not isinstance(got, list) else [fmt(x) for x in got],
                     "expected": fmt(exp) if not isinstance(exp, list) else [fmt(x) for x in exp], "match": st})
    # dates: the expected date of a known step against the effective date of the transcribed event
    evs = all_events(data)
    for k in data.get("known_dates", []):
        hits = [e["effective"] for e in evs
                if e["class"] == k["event"]["class"] and e["source"] == k["event"]["source"]]
        got = hits[0] if len(hits) == 1 else None
        rows.append({"id": k["id"], "what": k["what"], "read": got, "expected": k["expected"],
                     "match": None if got is None else got == k["expected"], "source": k["event"]["source"]})
    bad = [r["id"] for r in rows if r["match"] is False]
    unread = [r["id"] for r in rows if r["match"] is None]
    passed = False if bad else (True if not unread else None)
    return {"name": "B149-3", "kind": "known_answer", "passed": passed,
            "detail": f"{len(rows)} read-backs: matched {sum(r['match'] is True for r in rows)}, mismatched {bad}, unread {unread}",
            "read_backs": rows}


def chain(data, e):
    """The authority chain of an event: its own, or that of the revision whose circular carried it."""
    if e.get("authority"):
        return e["authority"]
    for r in data["revisions"]:
        if e["source"] in [s.strip() for s in r["circular"].split(";")]:
            return r.get("authority")
    return None


def all_events(data):
    return (data.get("class_line_events_block2", []) + data.get("didc", {}).get("class_line_events", [])
            + data.get("class_line_events_t20", []))


def class_line_rules(data):
    """Floating or rule-written positions registered as class lines: the g/k rule must differ from the o rule.
    A registered class line that reads the same is a reading failure of B149-4."""
    rules = [r for r in data["rules"] if r.get("registered") == "class_line"]
    if MUTANT == "skip_class_line_rules":
        rules = []
    out = []
    for rev, pos in sorted({(r["rev"], r["position"]) for r in rules}):
        toks = {r["class"]: r["rule"] for r in rules if r["rev"] == rev and r["position"] == pos}
        for a in ("g", "k"):
            if a in toks and "o" in toks:
                out.append({"cell": f"{rev}|{a}-o|{pos}", "rules": {"o": toks["o"], a: toks[a]},
                            "state": "differs" if toks[a] != toks["o"] else "same"})
    return out


def per_revision(data, rev):
    T1, T2 = table(data, rev, 1), table(data, rev, 2)
    pos = positions_of(T1)
    tab = {p: {a: fmt(T1.get((a, p))) for a in CLASSES} for p in pos}
    tab2_k = {p: fmt(T2.get(("k", p))) for p in pos}
    out = {"table": tab, "k_under_convention_2": tab2_k,
           "distinct": distinct(data, rev, T1),
           "graph": {"convention_1": graph(T1), "convention_2": graph(T2)},
           "deltas": {a: {p: {"delta_bp": d, "floor_multiple": abs(d) / FLOOR_BP} for p, d in deltas(T1, a).items()}
                      for a in ("g", "k")},
           "squares": {f"{a}-o": squares(T1, a) for a in ("g", "k")}}
    out["squares"]["k-g"] = squares(T1, "k", "g")
    fb = f_block(data, rev)
    if fb is not None:
        out["foreign_official"] = fb
    return out


def f_reading(data):
    """B149-4 for the fourth class: per revision the positions where f's value differs from o's, the rule-written
    class-line cells, and the f events (inside the window, each with an authority chain)."""
    fo = data.get("foreign_official")
    if not fo or MUTANT == "skip_f":
        return {"present": False, "passed": None, "hits": [], "events_outside_window": [], "events_without_authority": []}
    hits, rule_hits, per = [], [], {}
    for rev in ALL_TABLE_REVS:
        row = f_row(data, rev) or {}
        h = [f"{rev}|f|{p}" for p, v in row.items() if v["differs_from_o"]]
        rh = [c["cell"] for c in f_rule_cells(data, rev) if c["state"] == "differs"]
        per[rev] = len(h)
        hits += h
        rule_hits += rh
    seen = set(ALL_TABLE_REVS)
    for r in sorted({r["rev"] for r in data["rules"]} - seen):
        rule_hits += [c["cell"] for c in f_rule_cells(data, r) if c["state"] == "differs"]
    ev = fo.get("events", [])
    outside = [f'{e["effective"]} f {e["source"]}' for e in ev if not (WINDOW[0] <= e["effective"] <= WINDOW[1])]
    no_chain = [f'{e["effective"]} f {e["source"]}' for e in ev if not chain(data, e)]
    revs = sorted({h.split("|")[0] for h in hits})
    return {"present": True, "passed": bool(hits) and not outside and not no_chain,
            "hits": hits, "per_revision": per, "rule_cell_hits": rule_hits, "revisions_with_f_line": revs,
            "events": [f'{e["effective"]} {e["paragraph"]}: {e["class_value"]}' for e in ev],
            "events_outside_window": outside, "events_without_authority": no_chain}


def c4_own(data):
    hits = []
    for rev in ALL_TABLE_REVS:
        T = table(data, rev)
        for a in ("g", "k"):
            for p, d in deltas(T, a).items():
                if d != 0:
                    hits.append(f"{rev}|{a}|{p}")
    per_rev = {r: sum(h.startswith(r + "|") for h in hits) for r in ALL_TABLE_REVS}
    holder = {r["rev"]: r["holder_clauses"] for r in data["revisions"]}
    lines = {r["rev"]: r["class_lines"] for r in data["revisions"]}
    events = data.get("didc", {}).get("class_line_events", [])
    block2 = data.get("class_line_events_block2", [])
    t20 = data.get("class_line_events_t20", [])
    allev = block2 + events + t20
    cl = class_line_rules(data)
    cl_same = [c["cell"] for c in cl if c["state"] == "same"]
    ev = [f'{e["effective"]} {e["class"]} {e["paragraph"]}: {e.get("class_value", e.get("square_after", e.get("reading", "")))}'
          for e in allev]
    outside = [f'{e["effective"]} {e["class"]} {e["source"]}' for e in allev
               if not (WINDOW[0] <= e["effective"] <= WINDOW[1])]
    no_chain = [f'{e["effective"]} {e["class"]} {e["source"]}' for e in allev if not chain(data, e)]
    # g line in the DIDC years: found / searched and not found (third state, no verdict on this item)
    g_didc = [e for e in allev if e["class"] == "g" and e["effective"] > DIDC_START and chain(data, e)]
    g_state = {"state": "found", "passed": True, "events": [f'{e["effective"]} {e["source"]}' for e in g_didc]} if g_didc else \
        {"state": "authorization sentence not traced", "passed": None,
         "source_classes_searched": ["NY Fed circulars (FRASER)", "Dallas Fed circulars (FRASER)", "Board press releases (FRASER)",
                                     "FRASER full-text search"]}
    passed = bool(hits) and not outside and not no_chain and not cl_same
    fr = f_reading(data)
    if fr["present"]:
        passed = passed and fr["passed"] is True
    f_detail = ("" if not fr["present"] else
                f"; foreign official holders (f, 217.3): revisions writing f apart from o {fr['revisions_with_f_line']}, "
                f"cells {len(fr['hits'])} (per revision {fr['per_revision']}), rule-written f class-line cells "
                f"{len(fr['rule_cell_hits'])}, f events {len(fr['events'])}, outside the window {len(fr['events_outside_window'])}, "
                f"without an authority chain {len(fr['events_without_authority'])}; with f the revisions writing two class "
                f"values on one position are {sorted({h.split('|')[0] for h in hits + fr['hits']})}")
    return {"name": "B149-4", "kind": "own_reading", "passed": passed, "foreign_official": fr,
            "detail": (f"existential count law: revisions writing two different class values on one position: "
                       f"{sorted({h.split('|')[0] for h in hits})}; class-value cells differing from the ordinary row {len(hits)} "
                       f"(per revision {per_rev}); holder clauses per revision {holder}; class-line events {len(ev)} "
                       f"(1966-1977 {len(block2)}, DIDC block {len(events)}, third pass {len(t20)}); rule-written class-line cells {len(cl)}, "
                       f"reading the same as o {len(cl_same)}; outside {WINDOW[0]}..{WINDOW[1]} {len(outside)}, "
                       f"events without an authority chain {len(no_chain)}; g line in the DIDC years: {g_state['state']} {g_state.get('events', g_state.get('source_classes_searched'))}; "
                       f"events: {ev}" + f_detail),
            "cells_with_two_values": hits, "cells_with_two_values_per_revision": per_rev, "class_lines": lines,
            "class_line_events": events, "class_line_events_block2": block2, "class_line_events_t20": t20,
            "class_line_rule_cells": cl, "class_line_rules_reading_same": cl_same,
            "events_outside_window": outside, "events_without_authority": no_chain, "g_line_didc": g_state,
            "state_to_verdict_g_line_didc": [{"state": "found", "passed": True},
                                             {"state": "authorization sentence not traced", "passed": None}]}


MAP_RIVAL = [
    ("bound, |x| above one floor", True, "B"),
    ("bound, 0 < |x| <= one floor", None, "on the floor: third state, no grid cell"),
    ("bound, every registered-nonzero cell reads zero", False, "C"),
    ("not bound or no binding source", None, "unread"),
]


def _rival(data, name, values_fn, axis_note, entail):
    states = []
    for rev in FULL_REVS:
        for a in ("g", "k"):
            for key, x, cells in values_fn(data, rev, a):
                bound = all(binding_state(data, rev, cls, p) is True for cls, p in cells)
                floor = 0 if MUTANT == "floor_zero" else FLOOR_BP
                if not bound:
                    st = "unread"
                elif abs(x) > floor:
                    st = "B"
                elif x != 0:
                    st = "floor"
                else:
                    st = "zero"
                states.append({"cell": f"{rev}|{a}|{key}", "x_bp": x, "state": st})
    bound = [s for s in states if s["state"] != "unread"]
    nB = sum(s["state"] == "B" for s in states)
    nF = sum(s["state"] == "floor" for s in states)
    if not bound:
        passed, grid = None, "unread"
    elif all(s["state"] == "zero" for s in bound):
        passed, grid = False, "C"
    elif nB:
        passed, grid = True, "B"
    else:
        passed, grid = None, "unread"
    rec = {"name": name, "kind": "rival", "passed": passed, "grid": grid,
           "rival_premise": RIVAL_PREMISE, "rival_entailment": entail, "rival_shape": "point",
           "detail": (f"{len(states)} cells; bound {len(bound)}; above the floor {nB}; on the floor {nF}; "
                      f"unread {len(states) - len(bound)}. {axis_note}"),
           "state_to_verdict": [{"state": s, "passed": p, "grid": g} for s, p, g in MAP_RIVAL],
           "cells": states}
    rec["grid_note"] = ("No cell is occupied: the binding premise (B149-2) has no source yet, so neither side's reading "
                        "of the paid rate exists on any cell. The ceilings themselves are printed under B149-4."
                        if grid == "unread" else f"cells on the floor: {nF}")
    return rec


def _gaps(data, rev, a):
    T = table(data, rev)
    return [(p, d, [(a, p), ("o", p)]) for p, d in deltas(T, a).items()]


def _sqs(data, rev, a):
    T = table(data, rev)
    out = []
    for s in squares(T, a):
        j, jj = s["pair"].split("|")
        out.append((s["pair"], s["S_bp"], [(a, j), ("o", j), (a, jj), ("o", jj)]))
    return out


NEW_CELLS_NOTE = ("Cells of the revisions read in the second pass (1966-09-26, 1974-11-27, 1980-10-30) are counted under "
                  "B149-4 only and are not placed in any grid cell.")


def c5_rival(data):
    r = _rival(data, "B149-5", _gaps, "Single-position class gap Delta(a; j). " + NEW_CELLS_NOTE, RIVAL_ENTAILMENT_5)
    r["second_pass_cells_counted_not_placed"] = sum(1 for c in data["cells"] if c["rev"] in NEW_TABLE_REVS)
    return r


def c6_rival(data):
    t116 = data.get("table_1_16", [])
    note = ("Term axis inside the member-bank table. Institution axis (bank against thrift): thrift fixed table unread; "
            "its 0.25-point squares equal one grid step and read as third state.") if not t116 else (
            "Term axis inside the member-bank table. Institution axis (bank against thrift): thrift fixed rows read from "
            "Bulletin table 1.16 on four dates; squares of at most one grid step read as third state; no binding source "
            "for thrift institutions (the survey covers commercial banks), so no institution-axis cell is placed.")
    r = _rival(data, "B149-6", _sqs, note, RIVAL_ENTAILMENT_6)
    ia = institution_axis(data)
    ia["fixed_time_deposit_table"] = ("unread: thrift fixed time-deposit table not opened (Federal Register pending)"
                                      if not t116 else "read from Bulletin table 1.16, see institution_axis_table_1_16")
    r["institution_axis_table_1_16"] = [table116_axis(x) for x in t116]
    r["institution_axis"] = ia
    r["institution_axis_19810801"] = institution_axis(data, "institution_axis_19810801", "1981-08-01", "Dallas 81-154 p.10")
    r["second_pass_cells_counted_not_placed"] = sum(1 for c in data["cells"] if c["rev"] in NEW_TABLE_REVS)
    r["detail"] += " " + NEW_CELLS_NOTE
    return r


T116_O_ROWS = ["savings", "d90_1y", "y1_2.5", "y2.5_4", "y4_6", "y6_8", "y8plus"]


def table116_axis(t):
    """Bank against thrift on one issue of Bulletin table 1.16: o rows give the institution-axis squares (additive
    rival: zero); the g and k rows are printed beside them as class-by-institution squares (diagnostic, not placed)."""
    rows = t["rows"]
    floor = 0 if MUTANT == "floor_zero" else FLOOR_BP
    accts = [a for a in T116_O_ROWS if rows[a]["commercial bank"] is not None and rows[a]["thrift"] is not None]
    gaps = {a: rows[a]["thrift"] - rows[a]["commercial bank"] for a in accts}
    sq = []
    for a, b in itertools.combinations(accts, 2):
        s = gaps[a] - gaps[b]
        sq.append({"pair": f"{a}|{b}", "S_bp": s, "floor_multiple": abs(s) / FLOOR_BP,
                   "state": "above floor" if abs(s) > floor else ("on the floor" if s else "zero")})
    cls = {}
    for c in ("g", "k"):
        if rows[c]["commercial bank"] is None or rows[c]["thrift"] is None:
            continue
        gc = rows[c]["thrift"] - rows[c]["commercial bank"]
        cls[c] = {"thrift_minus_bank_bp": gc,
                  "squares_against_o_rows_bp": {a: gc - gaps[a] for a in accts}}
    above = [s["pair"] for s in sq if s["state"] == "above floor"]
    return {"in_effect": t["in_effect"], "source": t["source"], "passed": None,
            "thrift_minus_bank_bp": gaps, "squares": sq, "n_squares": len(sq), "n_above_floor": len(above),
            "n_on_floor": sum(s["state"] == "on the floor" for s in sq), "n_zero": sum(s["state"] == "zero" for s in sq),
            "state": ("above floor: a reading, awaiting a thrift binding source" if above else
                      "every square at most one grid step: third state, registered before the run"),
            "class_rows": cls,
            "class_rows_note": ("g and k carry the same number at banks and thrifts while o's rows differ by 25 to 50 "
                                "basis points; the class-by-institution squares are printed, not placed (no thrift "
                                "binding source)")}


def institution_axis(data, key="institution_axis", rev="1980-07-09", src="8869 p.2"):
    """Bank against thrift on the 1980-07 savings and transaction-account ceilings (8869 p.2), and on the
    1981-08-01 fixed time-deposit ceilings (Dallas 81-154 p.10).
    Additive rival: P(inst, account) = phi(account) + psi(inst) gives every square zero. Squares of
    one grid step were registered before the run as third state; anything larger would be a reading."""
    cells = data.get("didc", {}).get(key, [])
    T = {(c["institution"], c["account"]): c["value_bp"] for c in cells}
    order = ["savings", "NOW", "ATS", "TTS", "PNTS", "RSU", "d14_89", "d90_1y", "y1_2.5"]
    accts = [a for a in order if ("commercial bank", a) in T and ("thrift", a) in T]
    gaps = {a: T[("thrift", a)] - T[("commercial bank", a)] for a in accts}
    sq = []
    floor = 0 if MUTANT == "floor_zero" else FLOOR_BP
    for a, b in itertools.combinations(accts, 2):
        s = gaps[a] - gaps[b]
        sq.append({"pair": f"{a}|{b}", "S_bp": s, "floor_multiple": abs(s) / FLOOR_BP,
                   "state": "above floor" if abs(s) > floor else ("on the floor" if s else "zero")})
    above = [s["pair"] for s in sq if s["state"] == "above floor"]
    state = ("no cells" if not sq else
             "above floor: a reading, awaiting B149-2" if above else
             "every square at most one grid step: third state, registered before the run")
    return {"passed": None, "rev": rev, "source": src,
            "accounts_on_both": accts, "thrift_minus_bank_bp": gaps, "squares": sq,
            "n_squares": len(sq), "n_above_floor": len(above), "n_on_floor": sum(s["state"] == "on the floor" for s in sq),
            "n_zero": sum(s["state"] == "zero" for s in sq), "state": state}


def zero_domain(data, rev):
    out = []
    rules = [r for r in data["rules"] if r["rev"] == rev and r.get("registered") != "class_line"]
    for pos in sorted({r["position"] for r in rules}):
        toks = {r["class"]: r["rule"] for r in rules if r["position"] == pos}
        for a in ("g", "k"):
            if a in toks and "o" in toks:
                out.append({"cell": f"{rev}|{a}-o|{pos}", "kind": "same rule text",
                            "S": "0" if toks[a] == toks["o"] else "nonzero",
                            "rules": {"o": toks["o"], a: toks[a]}})
    T = table(data, rev)
    for s in squares(T, "k", "g"):
        out.append({"cell": f"{rev}|k-g|{s['pair']}", "kind": "both flat at one number", "S": "0" if s["S_bp"] == 0 else "nonzero",
                    "S_bp": s["S_bp"]})
    return out


def c7_zero(data, c1_passed):
    zd = [z for rev in ZERO_DOMAIN_REVS for z in zero_domain(data, rev)]
    # f against o on the rule-written positions where the text leaves f under o's rule (outside the limit) or both
    # without a ceiling: same value, so the square is zero; a planted mismatch there must surface.
    zdf = []
    for rev in ZERO_DOMAIN_REVS:
        for c in f_rule_cells(data, rev):
            if c["part"] == "outside" or c["rules"]["o"] == F_NO_CEILING:
                zdf.append({"cell": c["cell"], "kind": "f under o's rule or both ceiling-free",
                            "S": "0" if c["state"] == "same" else "nonzero", "rules": c["rules"]})
    # f-o cells here are equal by construction (f takes o's rule outside the limit), so they cannot fail and do not
    # enter the verdict (11f); they are printed as the f side of the zero domain.
    nonzero = [z["cell"] for z in zd if z["S"] != "0"]
    if not zd:
        passed = None
    elif not nonzero:
        passed = True
    elif c1_passed:
        passed = False
    else:
        passed = None
    return {"name": "B149-7", "kind": "own_reading", "passed": passed,
            "detail": f"zero-domain cells {len(zd)}; nonzero {len(nonzero)}{(' ' + str(nonzero)) if nonzero else ''}",
            "state_to_verdict": [{"state": "all zero", "passed": True},
                                 {"state": "a zero-domain cell nonzero and B149-1 passes", "passed": False},
                                 {"state": "a zero-domain cell nonzero and B149-1 fails", "passed": None},
                                 {"state": "no zero-domain cell", "passed": None}],
            "cells": zd, "cells_foreign_official": zdf,
            "cells_foreign_official_note": "f-o cells equal by construction (f under o's rule outside the two-year limit, "
                                           "or both without a ceiling); printed, not in the verdict"}


def c8_book(data):
    need = ("issue_date", "effective_date", "issuer", "circular", "pages", "authority")
    missing = [f'{r["rev"]}:{k}' for r in data["revisions"] for k in need if not r.get(k)]
    unopened = [f'{c["listed_in"]}: {c["item"]}' for c in data["coverage"] if not c["opened"]]
    passed = not missing and not unopened
    return {"name": "B149-8", "kind": "bookkeeping", "passed": passed,
            "detail": (f"revisions {len(data['revisions'])}, missing fields {len(missing)}; retain-list items "
                       f"{len(data['coverage'])}, opened {sum(c['opened'] for c in data['coverage'])}, unopened {len(unopened)}"),
            "missing_fields": missing, "unopened": unopened}


def criteria(data):
    c1 = c1_instrument(data)
    return [c1, c2_premise(data), c3_known(data), c4_own(data), c5_rival(data), c6_rival(data),
            c7_zero(data, c1["passed"]), c8_book(data)]


# ----------------------------------------------------------------------------- record
def build_record(data):
    crit = criteria(data)
    return {
        "stage": "B149",
        "config": {"cells_file": "data/b149_regq_cells.json", "floor_bp": FLOOR_BP,
                   "revisions_with_tables": list(FULL_REVS), "verdict_edge_convention": 1,
                   "revisions_with_tables_second_pass": list(NEW_TABLE_REVS),
                   "revisions_with_partial_tables_third_pass": list(T20_TABLE_REVS), "zero_domain_revisions": list(ZERO_DOMAIN_REVS),
                   "window": list(WINDOW),
                   "positions": data["positions"], "binding_sources": len(data["binding"]),
                   "binding_survey_readings": len(data.get("binding_surveys", [])),
                   "scopes": ["member_bank_table", "all_insured_combined"],
                   "didc_institution_axis_rev": "1980-07-09", "didc_institution_axis_rev_2": "1981-08-01",
                   "class_line_events": len(all_events(data)),
                   "foreign_official_class": bool(data.get("foreign_official"))},
        "foreign_official": data.get("foreign_official"),
        "revisions": data["revisions"],
        "per_revision": {r: per_revision(data, r) for r in ALL_TABLE_REVS},
        "zero_domain": {r: zero_domain(data, r) for r in ZERO_DOMAIN_REVS},
        "class_line_events_block2": data.get("class_line_events_block2", []),
        "class_line_events_t20": data.get("class_line_events_t20", []),
        "class_line_rule_cells": class_line_rules(data),
        "known_dates": data.get("known_dates", []),
        "savings": [{**s, "value": fmt(s["value_bp"])} for s in data["savings"]],
        "thrift_cells": data["thrift_cells"],
        "coverage": data["coverage"], "pages_read": data["pages_read"], "probes": data["probes"],
        "didc": {**data.get("didc", {}), "institution_axis_reading": institution_axis(data),
                 "institution_axis_19810801_reading": institution_axis(data, "institution_axis_19810801", "1981-08-01",
                                                                      "Dallas 81-154 p.10")},
        "criteria": crit,
        "binding_surveys": data.get("binding_surveys", []), "binding_map_note": data.get("binding_map_note"),
        "table_1_16": data.get("table_1_16", []), "fr_readings": data.get("fr_readings", []),
        "fr_not_located": data.get("fr_not_located", []),
    }


def write_record(rec):
    from safe_write import create, rewrite
    text = json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if RECORD.exists():
        return rewrite(RECORD, "B149 record", lambda old: text, session=SESSION)
    return create(RECORD, "B149 record", text, session=SESSION)


def summary(rec):
    for r in ALL_TABLE_REVS:
        pr = rec["per_revision"][r]
        print(f"== {r}")
        for p, row in pr["table"].items():
            print(f"   {p:16s} o={row['o']} g={row['g']} k={row['k']}  (k conv2 {pr['k_under_convention_2'][p]})")
        g1, g2 = pr["graph"]["convention_1"], pr["graph"]["convention_2"]
        print(f"   graph conv1 V={g1['V']} E={g1['E']} b1={g1['b1']} | conv2 V={g2['V']} E={g2['E']} b1={g2['b1']}")
        print(f"   distinct member={pr['distinct']['member_bank_table']} per row={ {a: v['n'] for a, v in pr['distinct']['per_row'].items()} }")
        mx = max((abs(s['S_bp']) for s in pr['squares']['g-o']), default=0)
        dg = [pr['deltas']['g'][p]['delta_bp'] for p in pr['deltas']['g']]
        print(f"   max |S| g-o {mx} bp over {len(pr['squares']['g-o'])} squares; max delta g {max(dg) if dg else None} bp")
    for key in ("institution_axis_reading", "institution_axis_19810801_reading"):
        ia = rec["didc"][key]
        print(f"== institution axis {ia['rev']}: thrift-bank {ia['thrift_minus_bank_bp']}; squares {ia['n_squares']}, above {ia['n_above_floor']}, on floor {ia['n_on_floor']}, zero {ia['n_zero']}: {ia['state']}")
    for c in rec["criteria"]:
        print(f"{c['name']} [{c['kind']}] passed={c['passed']}" + (f" grid={c['grid']}" if 'grid' in c else ""), "::", c["detail"])


# ----------------------------------------------------------------------------- selftest
def _set(data, rev, a, p, bp, dup=False):
    for c in data["cells"]:
        if c["rev"] == rev and c["class"] == a and c["position"] == p and bool(c.get("duplicate")) == dup:
            c["value_bp"] = bp
            c["image_reading"] = fmt(bp)
            return
    raise KeyError((rev, a, p))


def _bind_all(data):
    data["binding"] = [{"rev": r, "class": a, "position": p, "most_common_bp": v, "source": "seed"}
                       for r in FULL_REVS for (a, p), v in table(data, r).items()]


def selftest():
    base = load()
    # fixtures whose answers can be counted by hand from the printed 1979-08 member-bank table
    pr = per_revision(base, "1979-08-01")
    assert pr["graph"]["convention_1"]["b1"] == 10, pr["graph"]
    assert pr["graph"]["convention_2"]["b1"] == 14, pr["graph"]
    assert max(d["delta_bp"] for d in pr["deltas"]["g"].values()) == 275
    assert max(abs(s["S_bp"]) for s in pr["squares"]["g-o"]) == 250
    assert per_revision(base, "1978-06-01")["graph"]["convention_1"]["b1"] == 10
    assert pr["deltas"]["k"]["m4b"]["delta_bp"] == 150
    crit = {c["name"]: c for c in criteria(base)}
    assert crit["B149-1"]["passed"] is True, crit["B149-1"]["detail"]
    assert crit["B149-3"]["passed"] is True, crit["B149-3"]["detail"]
    # with the Bulletin survey in (2026-10-29) the k gaps bind and read B; without any binding input both rivals are unread
    assert crit["B149-5"]["passed"] is True and crit["B149-5"]["grid"] == "B", crit["B149-5"]["detail"]
    assert crit["B149-6"]["passed"] is True and crit["B149-6"]["grid"] == "B", crit["B149-6"]["detail"]
    nb = copy.deepcopy(base); nb["binding_surveys"], nb["binding_map"] = [], []
    assert c5_rival(nb)["grid"] == "unread" and c6_rival(nb)["grid"] == "unread"
    assert crit["B149-7"]["passed"] is True

    # B149-1 seeds
    d = copy.deepcopy(base); d["cells"][0]["method"] = "ocr_token"
    assert c1_instrument(d)["passed"] is False, "cell without image reading"
    d = copy.deepcopy(base); _set(d, "1979-08-01", "o", "m6", 725, dup=True)
    assert c1_instrument(d)["passed"] is False, "second printing disagreeing"
    d = copy.deepcopy(base); _set(d, "1979-07-01", "o", "m7", 734)  # a cell with no second printing
    assert c1_instrument(d)["passed"] is False, "7.34 read for 7 3/4"
    assert c1_instrument(d)["off_grid"] == ["1979-07-01|o|m7"], "only the quarter-point grid catches this one"
    d = copy.deepcopy(base); d["narrative_checks"][3].pop("registered_discrepancy")
    assert c1_instrument(d)["passed"] is False, "unregistered narrative discrepancy"

    # B149-2 seeds
    d = copy.deepcopy(base); d["binding_surveys"], d["binding_map"] = [], []
    assert c2_premise(d)["passed"] is None
    _bind_all(d); assert c2_premise(d)["passed"] is True
    d["binding"][0]["most_common_bp"] -= 25; assert c2_premise(d)["passed"] is False

    # B149-3 seeds: alter the cell behind yi, then behind ding; the name must come back
    d = copy.deepcopy(base); _set(d, "1978-06-01", "g", "m7", 775)
    r = c3_known(d); assert r["passed"] is False and "yi" in r["detail"]
    d = copy.deepcopy(base); _set(d, "1979-08-01", "o", "m1", 500)
    r = c3_known(d); assert r["passed"] is False and "ding" in r["detail"]

    # B149-4 seeds: g and k rows set to o; a dropped column
    d = copy.deepcopy(base)
    for r_ in ALL_TABLE_REVS:
        T = table(d, r_)
        for (a, p) in list(T):
            if a in ("g", "k"):
                _set(d, r_, a, p, T[("o", p)])
    assert c4_own(d)["passed"] is False
    assert per_revision(d, "1979-08-01")["distinct"]["per_row"]["g"]["n"] > 1  # g row now follows o
    assert distinct(d, "1979-08-01", table(d, "1979-08-01"))["member_bank_table"]["values_only_on_class_rows"] == []
    d = copy.deepcopy(base)
    d["cells"] = [c for c in d["cells"] if not (c["rev"] == "1979-08-01" and c["position"] == "m7")]
    assert per_revision(d, "1979-08-01")["graph"]["convention_1"]["b1"] != 10

    # B149-5 / B149-6 seeds: no binding input forces unread; bound real table gives B; m7 g gap sits on the floor
    d = copy.deepcopy(base); _bind_all(d)
    r5 = c5_rival(d); assert r5["passed"] is True and r5["grid"] == "B"
    floor_cells = [s for s in r5["cells"] if s["state"] == "floor"]
    assert any(s["cell"] == "1979-08-01|g|m7" for s in floor_cells), "m7 g gap is one floor"
    assert c6_rival(d)["passed"] is True
    # additive table: every class row = o + constant -> all squares zero -> C
    d2 = copy.deepcopy(d)
    for r_ in FULL_REVS:
        T = table(d2, r_)
        for (a, p) in list(T):
            if a in ("g", "k"):
                _set(d2, r_, a, p, T[("o", p)] + 100)
    _bind_all(d2)
    assert all(s["S_bp"] == 0 for r_ in FULL_REVS for s in squares(table(d2, r_), "g"))
    r6 = c6_rival(d2); assert r6["passed"] is False and r6["grid"] == "C"
    # g row shifted in step with o: term-axis squares all zero
    d3 = copy.deepcopy(base)
    T = table(d3, "1979-08-01")
    for p in base["positions"]:
        _set(d3, "1979-08-01", "g", p, T[("o", p)] + 250)
    assert all(s["S_bp"] == 0 for s in squares(table(d3, "1979-08-01"), "g"))

    # B149-7 seed: a markup on (g) for one class
    d = copy.deepcopy(base)
    for r_ in d["rules"]:
        if r_["class"] == "g" and r_["position"] == "var4y":
            r_["rule"] = "TSY4Y_AVG_MINUS_100BP"
            break
    assert c7_zero(d, True)["passed"] is False
    assert c7_zero(d, False)["passed"] is None

    # B149-8 seed: one more listed item unopened (the real list already has unopened items)
    d = copy.deepcopy(base)
    for c in d["coverage"]:
        c["opened"] = True
    assert c8_book(d)["passed"] is True
    d["coverage"][1]["opened"] = False
    assert c8_book(d)["passed"] is False

    # DIDC block seeds
    ia = institution_axis(base)
    assert ia["n_squares"] == 10 and ia["n_above_floor"] == 0 and ia["n_on_floor"] == 6, ia
    d = copy.deepcopy(base)
    for c in d["didc"]["institution_axis"]:
        if c["institution"] == "thrift" and c["account"] == "savings":
            c["value_bp"], c["image_reading"] = 575, "5.75"
    assert institution_axis(d)["n_above_floor"] > 0, "a 50 bp institution square must leave the third state"
    assert c1_instrument(d)["passed"] is False, "9177 passbook read-back must disagree with a moved 8869 cell"
    d = copy.deepcopy(base); d["didc"]["institution_axis"][0]["method"] = "ocr_token"
    assert c1_instrument(d)["passed"] is False, "DIDC cell without image reading"
    d = copy.deepcopy(base); d["didc"]["passbook_readback"][1]["value_bp"] = 534; d["didc"]["passbook_readback"][1]["image_reading"] = "5.34"
    assert c1_instrument(d)["passed"] is False, "5.34 for 5.25 off the grid"
    d = copy.deepcopy(base)
    next(r_ for r_ in d["revisions"] if r_["rev"] == "1981-12-01")["authority"] = ""
    assert c8_book(d)["missing_fields"] == ["1981-12-01:authority"]
    assert len(c4_own(base)["class_line_events"]) == 12  # 2 from the first DIDC pass, 10 added in T19

    # 11c: the undecided state maps to no verdict
    assert [p for s, p, g in MAP_RIVAL if s.startswith("not bound")] == [None]

    # ---- second pass (T19): fixtures counted by hand from the printed pages
    pr74 = per_revision(base, "1974-11-27")
    assert pr74["graph"]["convention_1"] == {"V": 8, "E": 12, "components": 1, "b1": 5}, pr74["graph"]
    assert pr74["graph"]["convention_2"]["b1"] == 5, "no k line in 1974: convention 2 adds nothing"
    assert max(d["delta_bp"] for d in pr74["deltas"]["g"].values()) == 250
    assert max(abs(s["S_bp"]) for s in pr74["squares"]["g-o"]) == 225
    pr66 = per_revision(base, "1966-09-26")
    assert pr66["graph"]["convention_1"]["b1"] == 0 and not pr66["deltas"]["g"], "1966: one class, no class line"
    assert per_revision(base, "1980-10-30")["deltas"]["g"]["d14_89"]["delta_bp"] == 275
    c4b = c4_own(base)
    assert c4b["cells_with_two_values_per_revision"]["1974-11-27"] == 6
    assert c4b["g_line_didc"]["state"] == "found" and not c4b["events_outside_window"]
    assert len(base["didc"]["k_readback"]) == 4
    assert institution_axis(base, "institution_axis_19810801", "1981-08-01", "x")["n_on_floor"] == 1

    # B149-1 seeds: 9196 maturity read as two years; a new cell with only an OCR token
    d = copy.deepcopy(base); d["didc"]["k_readback"][0]["a_value"] = "2 years"
    assert c1_instrument(d)["passed"] is False, "9196 against 9177 maturity read-back"
    d = copy.deepcopy(base)
    for c in d["cells"]:
        if c["rev"] == "1974-11-27" and c["class"] == "g" and c["position"] == "m1":
            c["method"] = "ocr_token"
    assert c1_instrument(d)["passed"] is False, "new cell with OCR token only"
    # B149-3 seed: a read-back date one day off
    d = copy.deepcopy(base)
    for e in d["didc"]["class_line_events"]:
        if e["source"] == "9524" and e["class"] == "g":
            e["effective"] = "1983-10-02"
    r = c3_known(d); assert r["passed"] is False and "ji_1983" in r["detail"], r["detail"]
    # B149-4 seeds: g row of a new revision set to o; an event outside the window; no g in the DIDC years
    d = copy.deepcopy(base)
    T = table(d, "1974-11-27")
    for (a, p_) in list(T):
        if a == "g":
            _set(d, "1974-11-27", "g", p_, T[("o", p_)])
    assert c4_own(d)["cells_with_two_values_per_revision"]["1974-11-27"] == 0, "count must drop"
    d = copy.deepcopy(base); d["class_line_events_block2"][1]["effective"] = "1966-09-20"
    r = c4_own(d); assert r["passed"] is False and r["events_outside_window"] == ["1966-09-20 g 7517"], r["events_outside_window"]
    d = copy.deepcopy(base)
    d["didc"]["class_line_events"] = [e for e in d["didc"]["class_line_events"] if e["class"] != "g"]
    d["class_line_events_t20"] = [e for e in d.get("class_line_events_t20", []) if e["class"] != "g" or e["effective"] <= DIDC_START]
    g = c4_own(d)["g_line_didc"]; assert g["state"] == "authorization sentence not traced" and g["passed"] is None
    d = copy.deepcopy(base); d["didc"]["class_line_events"][-1]["authority"] = ""
    for r_ in d["revisions"]:
        if r_["rev"] == "1986-03-31":
            r_["circular"] = "unknown"
    assert c4_own(d)["passed"] is False, "an event with no authority chain"
    # B149-7 seed: g given a markup in the 1983 rule
    d = copy.deepcopy(base)
    for r_ in d["rules"]:
        if r_["rev"] == "1983-10-01" and r_["class"] == "g":
            r_["rule"] = "NO_CEILING_PLUS_25BP"
    assert c7_zero(d, True)["passed"] is False
    # B149-8 seeds: a new revision without authority; one more retain item unopened
    d = copy.deepcopy(base)
    for r_ in d["revisions"]:
        if r_["rev"] == "1983-10-01":
            r_["authority"] = ""
    assert "1983-10-01:authority" in c8_book(d)["missing_fields"]
    d = copy.deepcopy(base)
    for c in d["coverage"]:
        c["opened"] = True
    assert c8_book(d)["passed"] is True
    d["coverage"][-1]["opened"] = False
    assert c8_book(d)["passed"] is False

    # ---- third pass (T20): fixtures counted by hand from the printed pages
    pr75 = per_revision(base, "1975-12-04")
    assert max(x["delta_bp"] for x in pr75["deltas"]["g"].values()) == 275, "1975-12-04: g 7.75 against o 5 at 30-89 days"
    assert {p: x["delta_bp"] for p, x in pr75["deltas"]["k"].items()} == {
        "t4y_6y_u1000": 75, "t4y_6y_1000": 0, "t6y_u1000": 100, "t6y_1000": 0}, pr75["deltas"]["k"]
    pr80 = per_revision(base, "1980-01-01")
    assert pr80["deltas"]["g"]["m2"]["delta_bp"] == 225 and pr80["graph"]["convention_1"]["b1"] == 10
    assert per_revision(base, "1983-10-01")["deltas"]["g"]["d7_31_u2500"]["delta_bp"] == 275
    assert per_revision(base, "1984-01-01")["deltas"]["g"]["d7_31_u2500"]["delta_bp"] == 250
    c4c = c4_own(base)
    assert c4c["cells_with_two_values_per_revision"]["1975-12-04"] == 10, c4c["cells_with_two_values_per_revision"]
    assert c4c["class_line_rule_cells"] and not c4c["class_line_rules_reading_same"]
    # B149-4 seeds: k at 1975-12-04 set to o -> count drops by two; a registered class-line rule read as the o rule -> fails
    d = copy.deepcopy(base)
    T = table(d, "1975-12-04")
    for p_ in ("t4y_6y_u1000", "t6y_u1000"):
        _set(d, "1975-12-04", "k", p_, T[("o", p_)])
    assert c4_own(d)["cells_with_two_values_per_revision"]["1975-12-04"] == 8
    d = copy.deepcopy(base)
    for r_ in d["rules"]:
        if r_.get("registered") == "class_line" and r_["class"] == "g" and r_["rev"] == "1982-09-01" and r_["position"] == "d7_31_20k":
            r_["rule"] = "TB91_MINUS_25BP"
    r = c4_own(d); assert r["passed"] is False and r["class_line_rules_reading_same"] == ["1982-09-01|g-o|d7_31_20k"], r["class_line_rules_reading_same"]
    # B149-7 seed: a registered zero rule given to g alone at 1986-01-01
    d = copy.deepcopy(base)
    for r_ in d["rules"]:
        if r_["rev"] == "1986-01-01" and r_["class"] == "g":
            r_["rule"] = "CEILING_800"
    assert c7_zero(d, True)["passed"] is False
    # B149-1 seeds: the 9225 printing discrepancy unregistered; a carried-forward cell without an image reading
    d = copy.deepcopy(base)
    next(n for n in d["narrative_checks"] if n["id"] == "N12").pop("registered_discrepancy")
    assert c1_instrument(d)["passed"] is False
    d = copy.deepcopy(base)
    for c in d["cells"]:
        if c["method"] == "page_image_carried_forward":
            c["image_reading"] = None
    assert c1_instrument(d)["passed"] is False
    # ---- fourth pass (B149_1029): foreign-official class, Bulletin survey, table 1.16
    # f: fixtures counted by hand from the position labels and the two periods
    fb66 = per_revision(base, "1966-09-26")["foreign_official"]
    assert fb66["cells_differing_from_o"] == 3 and fb66["graph_with_f_convention_1"]["b1"] == 2, fb66
    assert per_revision(base, "1978-06-01")["foreign_official"]["cells_differing_from_o"] == 3
    assert per_revision(base, "1978-06-01")["foreign_official"]["row"]["m3"]["part"] == "straddles"
    fr = c4_own(base)["foreign_official"]
    assert fr["present"] and len(fr["hits"]) == 30 and "1966-09-26" in fr["revisions_with_f_line"], fr["per_revision"]
    # f seeds: m1 put outside the two-year line drops one cell per revision after 1968; a zero limit leaves no f line;
    # an f event outside the window, or without an authority chain, fails B149-4
    d = copy.deepcopy(base); d["foreign_official"]["position_bounds_months"]["m1"] = [30, 36]
    assert per_revision(d, "1978-06-01")["foreign_official"]["cells_differing_from_o"] == 2
    d = copy.deepcopy(base)
    for per_ in d["foreign_official"]["periods"]:
        per_["limit_months"] = 0
    assert c4_own(d)["foreign_official"]["passed"] is False and c4_own(d)["passed"] is False
    d = copy.deepcopy(base); d["foreign_official"]["events"][1]["effective"] = "1986-04-01"
    assert c4_own(d)["passed"] is False
    d = copy.deepcopy(base); d["foreign_official"]["events"][2]["authority"] = ""
    assert c4_own(d)["passed"] is False

    # B149-2 from the survey: three states, each from its own reading
    assert binding_state(base, "1979-08-01", "o", "m1") is None, "banks below, dollars at the ceiling"
    assert binding_state(base, "1979-07-01", "k", "m4b") is True
    assert binding_state(base, "1975-12-04", "g", "m1") is False
    assert binding_state(base, "1980-01-01", "o", "m2") is False, "survey ceiling 5.50 against the rule's 5.75"
    assert binding_state(base, "1979-07-01", "o", "m5") is None, "memo counts the 7.60 variable ceiling"
    d = copy.deepcopy(base)
    next(r_ for r_ in d["binding_surveys"] if r_["id"] == "S79b-o30")["memo"][1] = 20.0
    next(r_ for r_ in d["binding_surveys"] if r_["id"] == "S79b-o30")["brackets"][1][4] = 52.4
    assert binding_state(d, "1979-08-01", "o", "m1") is False, "dollars now below too"
    d = copy.deepcopy(base)
    for r_ in d["binding_surveys"]:
        if r_["id"].endswith("-k"):
            r_["memo"] = [1.0, 1.0]
    assert c5_rival(d)["grid"] == "unread" and c6_rival(d)["grid"] == "unread", "k below: nothing bound on both sides"
    # B149-1 survey seeds: a reading not from an image; a bracket mistyped (sum off); a memo larger than its interval
    d = copy.deepcopy(base); d["binding_surveys"][0]["method"] = "alto"
    assert c1_instrument(d)["passed"] is False
    d = copy.deepcopy(base); d["binding_surveys"][4]["brackets"][0][3] = 2210
    assert c1_instrument(d)["passed"] is False and c1_instrument(d)["survey_sums_off"], "221 read as 2210"
    d = copy.deepcopy(base); d["binding_surveys"][4]["memo"][0] = 5700
    assert c1_instrument(d)["survey_memo_over_interval"]
    d = copy.deepcopy(base); next(n for n in d["narrative_checks"] if n["id"] == "N19").pop("registered_discrepancy")
    assert c1_instrument(d)["passed"] is False, "table 1.16 5 1/2 against the rule's 5 3/4"
    # table 1.16 institution axis: one grid step everywhere; a thrift row moved 50 bp must leave the third state
    ax = [table116_axis(x) for x in base["table_1_16"]]
    assert all(a["n_above_floor"] == 0 for a in ax) and ax[1]["class_rows"]["g"]["thrift_minus_bank_bp"] == 0, ax[1]
    d = copy.deepcopy(base); d["table_1_16"][1]["rows"]["y4_6"]["thrift"] += 50
    assert table116_axis(d["table_1_16"][1])["n_above_floor"] > 0
    return True


MUTANTS = ["fill_zero", "f_fixed", "d_six_months", "floor_zero", "no_grid_check", "sign_flip", "dup_skip", "skip_passbook",
           "skip_9196", "skip_class_line_rules", "skip_f", "banks_only", "skip_survey_checks"]


def mutation_run():
    import subprocess
    caught = {}
    for m in MUTANTS:
        env = dict(os.environ, B149_MUTANT=m)
        r = subprocess.run([sys.executable, "-B", str(Path(__file__)), "--selftest-only"], env=env,
                           capture_output=True, text=True, encoding="utf-8")
        caught[m] = r.returncode != 0
    return caught


def main(argv):
    if "--selftest-only" in argv:
        selftest()
        print("selftest ok")
        return 0
    if "--selftest" in argv:
        selftest()
        print("selftest ok")
        caught = mutation_run()
        for m, c in caught.items():
            print(f"  mutant {m:14s} caught={c}")
        return 0 if all(caught.values()) else 1
    data = load()
    rec = build_record(data)
    summary(rec)
    if "--no-write" not in argv:
        print(write_record(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
