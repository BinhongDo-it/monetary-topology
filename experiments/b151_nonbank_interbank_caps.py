"""B151: one self-regulatory initiative, two positions at the same bank, and the values it writes by class of depositor.

China's market interest-rate pricing self-regulatory mechanism adopted, on 28 November 2024, an initiative on the
rates banks pay on deposits placed by non-bank financial institutions. In force from 1 December 2024, with one
month's grace, and part of the macroprudential assessment from the first quarter of 2025. It writes:

    position A, demand deposits placed at a bank by
        financial market infrastructure institutions   refer to the rate on excess reserves
        every other non-bank institution                refer to the 7-day reverse repo rate
    position B, early withdrawal of a time deposit placed by any non-bank institution
                                                        in principle not above the rate on excess reserves

So one writer names two classes at position A and gives them two different values, and names one class at
position B and gives it one value. Each cell is written by reference to a published policy rate (a reference rate
at A, a ceiling at B), so the value of every cell is read off a central bank notice. Two regimes: the 7-day rate was 1.50 from 27 September 2024 and 1.40 from 8 May 2025; the
rate on excess reserves has been 0.35 since 7 April 2020.

Nothing is estimated. The script reads the saved page snapshots, checks that every quoted sentence is on the page
it is attributed to and that every policy rate is the one the notice prints, then counts written values per
position and computes the 2 x 2 square in two compositions (percentage points and logs) against the publication
grid of the rates. Each cell's value is the rate its own sentence names, and the script checks that name in the
sentence. The initiative itself is not public; its sentences are read from three outlets that carry them word for
word the same, and its existence and name from the central bank's own release. The square is computed on the
written values: a reference rate at A and a ceiling at B, not rates actually paid.

    python experiments/b151_nonbank_interbank_caps.py              # print, write the record
    python experiments/b151_nonbank_interbank_caps.py --selftest   # seeded faults, each must be caught
"""

import argparse
import copy
import hashlib
import html
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "data" / "raw" / "b151"
RECORD = ROOT / "results" / "b151_nonbank_interbank_caps.json"
READ_DATE = "2026-10-14"
LAPSE_DATE = "2027-03-31"   # no text for the announced second step by then: "announced, not landed"
GRID = 0.01                 # both policy rates are published to two decimals

CLASSES = {
    "fmi": "financial market infrastructure institutions",
    "other": "non-bank financial institutions other than financial market infrastructure (incl. unincorporated products)",
}
POSITIONS = {
    "A": "demand deposit placed at a bank",
    "B": "early withdrawal of a time deposit placed at the same bank",
}
# Depositors that place interbank deposits of the same kind at the same bank and that this initiative does not write
# for.
UNWRITTEN = {
    "A": ["banks (interbank demand deposits between banks)"],
    "B": ["banks (interbank time deposits between banks)"],
}
# Corporate and household deposits are general deposits, not interbank deposits, so they are not at either position.
NOT_AT_THESE_POSITIONS = ("corporate and household deposits: general deposits, not interbank deposits; this initiative "
                          "does not cover them and their rates are written under other rules, not read here")

# Segments: from the start date to the end date, both inclusive.
SEGMENTS = [
    {"id": "one", "start": "2024-12-01", "end": "2025-05-07"},
    {"id": "two", "start": "2025-05-08", "end": READ_DATE},
]

# Policy-rate notices. `value` and `effective` are recorded by hand; `pattern` reads both off the snapshot, and the
# two must agree. Whitespace is removed from page text before matching.
RATES = [
    {"rate": "ioer", "value": 0.35, "effective": "2020-04-07", "file": "pbc_ioer_20200403.html",
     "pattern": r"自(\d+)月(\d+)日起将金融机构在央行超额存款准备金利率从[\d.]+%下调至([\d.]+)%", "year": 2020},
    {"rate": "rr7", "value": 1.50, "effective": "2024-09-27", "file": "pbc_omo_notice_2024_5.html",
     "pattern": r"从(\d+)月(\d+)日起，公开市场7天期逆回购操作利率由此前的[\d.]+%调整为([\d.]+)%", "year": 2024},
    {"rate": "rr7", "value": 1.40, "effective": "2025-05-08", "file": "pbc_omo_notice_2025_1.html",
     "pattern": r"从2025年(\d+)月(\d+)日起，公开市场7天期逆回购操作利率由此前的[\d.]+%调整为([\d.]+)%", "year": 2025},
]
# Latest statement of each level in the last segment: the operation printed on the reading date, the central bank's
# 2026Q1 report, and a 2026-05-07 press statement (the only later statement of the excess-reserve rate found).
LATEST_STATEMENTS = [
    {"rate": "rr7", "file": "pbc_omo_trade_2026_198.html", "pattern": r"逆回购操作情况.*?7天([\d.]+)%",
     "level": "official"},
    {"rate": "rr7", "file": "pbc_mpr_2026q1.pdf", "pattern": r"公开市场7天期逆回购利率维持于([\d.]+)%",
     "level": "official"},
    {"rate": "ioer", "file": "sina_20260507.html", "pattern": r"超额存款准备金利率合理确定利率水平（目前为([\d.]+)%）",
     "level": "other"},
]
# How each policy rate is named inside the initiative's sentences. A cell's value is taken from the rate its
# sentence names, and B151-2 checks that the sentence names its anchor and no other rate.
RATE_NAMES = {"ioer": "超额存款准备金利率", "rr7": "7天期逆回购操作利率"}

QUOTES = {
    "A_fmi": "金融基础设施机构的同业活期存款主要体现支付结算属性，应参考超额存款准备金利率合理确定利率水平",
    "A_other": "除金融基础设施机构外的其他非银同业活期存款应参考公开市场7天期逆回购操作利率合理确定利率水平，充分体现政策利率传导",
    "B_all": "若银行与非银金融机构（含非法人产品）约定同业定期存款可提前支取，提前支取利率原则上不应高于超额存款准备金利率",
}
TRANSCRIPTIONS = ["thepaper_20241204.html", "sina_21cbh_20241129.html", "cnfin_xinhua_bank_bulletin_20241209.pdf"]
EXISTENCE = {"file": "pbc_meeting_20241129.html", "needle": "审议通过了《关于优化非银同业存款利率自律管理的自律倡议》"}

# One cell per (position, class). `entry` names the sentence that writes it: two cells sharing an entry were written
# once for both classes. `anchor` is the policy rate the sentence refers to; `modal` is the operative wording.
LEVEL = "other (three outlets carry the sentence word for word the same)"
CELLS = {
    ("A", "fmi"): {"entry": "A_fmi", "anchor": "ioer", "modal": ["参考", "合理确定"], "sources": TRANSCRIPTIONS,
                   "level": LEVEL},
    ("A", "other"): {"entry": "A_other", "anchor": "rr7", "modal": ["参考", "合理确定"], "sources": TRANSCRIPTIONS,
                     "level": LEVEL},
    ("B", "fmi"): {"entry": "B_all", "anchor": "ioer", "modal": ["原则上不应高于"], "sources": TRANSCRIPTIONS,
                   "level": LEVEL},
    ("B", "other"): {"entry": "B_all", "anchor": "ioer", "modal": ["原则上不应高于"], "sources": TRANSCRIPTIONS,
                     "level": LEVEL},
}

# Second step (interbank time deposits brought under the self-regulation). None until a text is public.
SECOND_STEP = None
SECOND_STEP_CHECKS = [
    {"date": "2026-10-14", "looked_at": "central bank monetary policy reports 2026Q1 and 2026Q2 (full text), the "
     "report list page (2026Q3 not yet listed), press search", "found": "reports only; 2026-05 press says 'expected "
     "in the third quarter', cap 'same-tenor Shibor + 10 bp'; no text of the step itself"},
]

MAPPINGS = {
    "B151-1": {"every segment has both rates, each read off a notice and equal to the table": "PASS",
               "a rate missing, unread, or not equal to the table": "FAIL"},
    "B151-2": {"every cell has its sentence on a verified snapshot, a modal word inside the sentence, a level, and "
               "the sentence names its anchor rate and no other": "PASS",
               "a cell without a verified snapshot, without its modal word, without a level, or whose sentence does "
               "not name its anchor rate alone": "FAIL"},
    "B151-3": {"in every segment, distinct values at position A equal the classes named (2)": "PASS",
               "in some segment distinct values differ from the classes named (fewer or more)": "FAIL",
               "a cell at position A without a value or without a verified sentence": "None (no verdict)"},
    "B151-4": {"in every segment both compositions clear their floor with the same sign": "PASS",
               "both clear their floor with opposite signs in some segment": "None (no verdict)",
               "either composition at or under its floor in some segment": "None (no verdict)",
               "a cell of the square without a value or without a verified sentence": "None (no verdict)"},
    "B151-5": {"at every position distinct values equal separately written classes": "PASS",
               "at some position they differ": "FAIL",
               "a position with no classes": "None (no verdict)",
               "a cell without a value or without a verified sentence": "None (no verdict)"},
    "B151-6": {"second-step text read, its cells pass the sentence checks, positions recomputed":
               "verdict of the recomputed B151-5",
               "second-step text read and a cell fails the sentence checks": "None (no verdict)",
               "no text, reading date on or before the lapse date": "None (waiting for the event)",
               "no text after the lapse date": "None (announced, not landed)"},
}


def fmt(x, n=4):
    return None if x is None else f"{x:.{n}f}"


def page_text(path):
    """Text of a snapshot with all whitespace removed; page markers of the form 5/33 removed from PDFs."""
    raw = path.read_bytes()
    if path.suffix == ".pdf":
        import pymupdf
        doc = pymupdf.open(stream=raw, filetype="pdf")
        t = "".join(p.get_text() for p in doc)
        t = re.sub(r"\s+", "", t)
        return re.sub(r"\d{1,3}/\d{1,3}", "", t)
    for enc in ("utf-8", "gbk"):
        try:
            t = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", "", t)


def load_snapshots(snap_dir):
    """Snapshots whose bytes match the manifest; others are listed as unverified and carry nothing."""
    man = json.loads((snap_dir / "b151_manifest.json").read_text(encoding="utf-8"))
    ok, bad = {}, []
    for row in man["snapshots"]:
        p = snap_dir / row["file"]
        if not p.exists():
            bad.append(f"{row['file']}: missing")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != row["sha256"]:
            bad.append(f"{row['file']}: hash differs from the manifest")
            continue
        ok[row["file"]] = {"text": page_text(p), "meta": row}
    return ok, bad


def read_rates(rates, snaps):
    out = []
    for r in rates:
        got = {"rate": r["rate"], "table_value": fmt(r["value"], 2), "table_effective": r["effective"],
               "file": r["file"], "read_value": None, "read_effective": None, "agrees": False}
        s = snaps.get(r["file"])
        m = re.search(r["pattern"], s["text"]) if s else None
        if m:
            mo, dy, v = m.groups()
            got["read_value"] = f"{float(v):.2f}"
            got["read_effective"] = f"{r['year']:04d}-{int(mo):02d}-{int(dy):02d}"
            got["agrees"] = (got["read_value"] == got["table_value"] and got["read_effective"] == r["effective"])
        out.append(got)
    return out


def rates_by_segment(rates, read):
    """Rate in force at each segment start, and whether any change falls inside the segment."""
    seg = {}
    for s in SEGMENTS:
        row = {}
        for name in ("ioer", "rr7"):
            ins = [(r, g) for r, g in zip(rates, read) if r["rate"] == name]
            before = [(r, g) for r, g in ins if r["effective"] <= s["start"]]
            inside = [r["effective"] for r, g in ins if s["start"] < r["effective"] <= s["end"]]
            if not before:
                row[name] = {"value": None, "source": None, "agrees": False, "changes_inside": inside}
                continue
            r, g = max(before, key=lambda x: x[0]["effective"])
            row[name] = {"value": r["value"], "source": r["file"], "agrees": g["agrees"], "changes_inside": inside}
        seg[s["id"]] = row
    return seg


def check_latest_statement(snaps, seg, latest_statement=LATEST_STATEMENTS):
    """The latest statement of each level found in the last segment must equal the table's value there. The date
    printed is the page's own publication date; it is a statement of the level on that date."""
    last = seg[SEGMENTS[-1]["id"]]
    out = []
    for c in latest_statement:
        s = snaps.get(c["file"])
        m = re.search(c["pattern"], s["text"]) if s else None
        v = f"{float(m.group(1)):.2f}" if m else None
        want = last[c["rate"]]["value"]
        out.append({"rate": c["rate"], "file": c["file"], "level": c["level"], "read": v,
                    "published": s["meta"].get("published") if s else None,
                    "agrees": want is not None and v == f"{want:.2f}"})
    return out


def verify_cells(cells, snaps):
    """For each cell: which listed snapshots carry its sentence, and whether the modal words sit inside it."""
    out = {}
    for key, c in cells.items():
        q = QUOTES.get(c.get("entry"), "")
        found = [f for f in c.get("sources", []) if f in snaps and q and q in snaps[f]["text"]]
        modal = c.get("modal") or []
        named = sorted(r for r, n in RATE_NAMES.items() if q and n in q)
        out[key] = {"entry": c.get("entry"), "sentence": q, "anchor": c.get("anchor"), "found_in": found,
                    "listed": list(c.get("sources", [])), "modal": modal,
                    "modal_in_sentence": bool(modal) and all(w in q for w in modal), "level": c.get("level"),
                    "rates_named": named, "anchor_named": named == [c.get("anchor")]}
    return out


def cell_values(cells, seg_rates, overrides=None):
    """Value of each cell in each segment: the anchor rate, or an explicit override (used only by seeds)."""
    overrides = overrides or {}
    vals = {}
    for sid, row in seg_rates.items():
        for key, c in cells.items():
            v = overrides.get((sid,) + key)
            if v is None:
                a = c.get("anchor")
                v = row[a]["value"] if a in row else None
            vals[(sid,) + key] = v
    return vals


def count_position(cells, vals, ver, sid, pos):
    keys = [k for k in cells if k[0] == pos]
    members = {k[1]: vals[(sid,) + k] for k in keys}
    entries = sorted({cells[k]["entry"] for k in keys})
    distinct = sorted({v for v in members.values() if v is not None})
    missing = [k[1] for k in keys if vals[(sid,) + k] is None or not ver[k]["found_in"]]
    return {"classes_present": sorted(members), "members": {c: fmt(v, 2) for c, v in members.items()},
            "separately_written": len(entries), "entries": entries,
            "distinct_values": [fmt(v, 2) for v in distinct], "n_values": len(distinct), "missing": missing}


def square(vals, sid):
    g = {(p, c): vals.get((sid, p, c)) for p in POSITIONS for c in CLASSES}
    if any(v is None for v in g.values()):
        return None
    pp = (g[("A", "other")] - g[("A", "fmi")]) - (g[("B", "other")] - g[("B", "fmi")])
    if min(g.values()) <= 0:
        return {"cells": {f"{p}_{c}": fmt(v, 4) for (p, c), v in g.items()}, "pp": pp, "log": None}
    lg = math.log(g[("A", "other")] / g[("A", "fmi")]) - math.log(g[("B", "other")] / g[("B", "fmi")])
    x = min(g.values())
    lfloor = math.log((x + GRID) / x)
    return {"cells": {f"{p}_{c}": fmt(v, 4) for (p, c), v in g.items()}, "pp": pp, "pp_floor": GRID,
            "log": lg, "log_floor": lfloor, "pp_multiple": abs(pp) / GRID, "log_multiple": abs(lg) / lfloor}


def verdict_square(sq):
    if sq is None or sq.get("log") is None:
        return None, "a cell has no value"
    clears = abs(sq["pp"]) > sq["pp_floor"] and abs(sq["log"]) > sq["log_floor"]
    if not clears:
        return None, "a composition is at or under its floor"
    if (sq["pp"] > 0) != (sq["log"] > 0):
        return None, "both clear their floor with opposite signs"
    return True, "both clear their floor, same sign"


def evaluate(cells=None, rates=None, snaps=None, overrides=None, second_step=None, today=READ_DATE,
             latest_statement=LATEST_STATEMENTS):
    cells = CELLS if cells is None else cells
    rates = RATES if rates is None else rates
    read = read_rates(rates, snaps)
    seg = rates_by_segment(rates, read)
    infl = check_latest_statement(snaps, seg, latest_statement)
    ver = verify_cells(cells, snaps)
    vals = cell_values(cells, seg, overrides)
    crit = []

    # B151-1
    probs = []
    for sid, row in seg.items():
        for name in ("ioer", "rr7"):
            r = row[name]
            if r["value"] is None:
                probs.append(f"segment {sid}: no notice for {name}")
            elif not r["agrees"]:
                probs.append(f"segment {sid}: {name} {r['value']:.2f} not what {r['source']} prints")
            if r["changes_inside"]:
                probs.append(f"segment {sid}: {name} changes inside on {r['changes_inside']}")
    probs += [f"latest statement: {c['rate']} read {c['read']} from {c['file']}" for c in infl if not c["agrees"]]
    det = "; ".join(f"segment {sid}: ioer {fmt(row['ioer']['value'], 2)} ({row['ioer']['source']}), rr7 "
                    f"{fmt(row['rr7']['value'], 2)} ({row['rr7']['source']})" for sid, row in seg.items())
    if not any(row[n]["changes_inside"] for row in seg.values() for n in ("ioer", "rr7")):
        det += "; no notice in the table changes either rate inside a segment"
    det += ("; latest statement of each level: "
            + ", ".join(f"{c['rate']} {c['read']} ({c['file']}, published {c['published']}, {c['level']})"
                        for c in infl))
    crit.append({"name": "B151-1", "kind": "instrument", "passed": not probs,
                 "statement": "each segment's two policy rates are read off an opened central bank notice and agree "
                              "with the table; segment cuts sit on the notices' effective dates",
                 "detail": det + ("" if not probs else " | problems: " + "; ".join(probs))})

    # B151-2
    probs = []
    for key, v in ver.items():
        tag = f"{key[0]}/{key[1]}"
        if not v["found_in"]:
            probs.append(f"{tag}: sentence on no verified snapshot")
        if not v["modal_in_sentence"]:
            probs.append(f"{tag}: modal wording missing or not in the sentence")
        if not v["level"]:
            probs.append(f"{tag}: no source level")
        if not v["anchor_named"]:
            probs.append(f"{tag}: value taken from {v['anchor']} but the sentence names {v['rates_named']}")
    det = "; ".join(f"{k[0]}/{k[1]}: sentence names {'+'.join(v['rates_named']) or '-'}, value from {v['anchor']}, "
                    f"modal {'+'.join(v['modal']) or '-'}, on {len(v['found_in'])} of "
                    f"{len(v['listed'])} snapshots, level {v['level']}" for k, v in ver.items())
    ex = snaps.get(EXISTENCE["file"])
    exists = bool(ex) and EXISTENCE["needle"] in ex["text"]
    det += f"; existence and name on the central bank's own release: {'yes' if exists else 'no'}"
    if not exists:
        probs.append("central bank release not verified")
    crit.append({"name": "B151-2", "kind": "bookkeeping", "passed": not probs,
                 "statement": "every cell carries its sentence on a verified snapshot, its operative wording and the "
                              "level of its source, and its value is taken from the one policy rate its sentence names",
                 "detail": det + ("" if not probs else " | problems: " + "; ".join(probs))})

    # B151-3
    per = {}
    state = True
    for s in SEGMENTS:
        c = count_position(cells, vals, ver, s["id"], "A")
        per[s["id"]] = c
        if c["missing"] or not c["classes_present"]:
            state = None
        elif state is not None and c["n_values"] != c["separately_written"]:
            state = False
    det = "; ".join(f"segment {sid}: {c['n_values']} values {c['distinct_values']} for "
                    f"{c['separately_written']} classes named, members {c['members']}"
                    + (f", missing {c['missing']}" if c["missing"] else "") for sid, c in per.items())
    crit.append({"name": "B151-3", "kind": "own_reading", "grid": "D2", "passed": state,
                 "grid_note": "at the demand-deposit position no single number is read by both classes: the written "
                              "value splits by class and each half is pinned by a different published policy rate; an "
                              "object with one index per position has nowhere to write this",
                 "statement": "distinct values the initiative writes at the demand-deposit position, by segment",
                 "detail": det, "count_by_segment": per})

    # B151-4
    sqs, states = {}, []
    unverified = sorted(f"{p}/{c}" for (p, c) in cells if (p, c) in ver and not ver[(p, c)]["found_in"]
                        and p in POSITIONS and c in CLASSES)
    for s in SEGMENTS:
        sq = square(vals, s["id"])
        st, why = verdict_square(sq)
        if unverified and st is not None:
            st, why = None, f"a cell without a verified sentence: {unverified}"
        sqs[s["id"]] = {"square": None if sq is None else {k: (fmt(v) if isinstance(v, float) else v)
                                                         for k, v in sq.items()},
                        "verdict": st, "why": why}
        states.append(st)
    sq_state = True if all(x is True for x in states) else None
    shapes = []
    a_counts = [count_position(cells, vals, ver, s["id"], "A")["n_values"] for s in SEGMENTS]
    shapes.append("bare (one value per position): " + (
        "has no place for the two values position A carries in every segment (B151-3, grid D2)"
        if min(a_counts) > 1 else "has a place for the values written"))
    raw = {sid: square(vals, sid) for sid in sqs}
    add_zero = [sid for sid, q in raw.items() if q is not None and abs(q["pp"]) <= GRID]
    mul_zero = [sid for sid, q in raw.items() if q is not None and q.get("log") is not None
                and abs(q["log"]) <= q["log_floor"]]
    shapes.append("additive (class term + position term, pp square zero): "
                  + ("refuted as a shape of the written schedule in every segment; rates actually paid are not read at "
                     "either position" if not add_zero else f"holds in {add_zero}"))
    shapes.append("multiplicative (class term x position term, log square zero): "
                  + ("refuted as a shape of the written schedule in every segment; rates actually paid are not read at "
                     "either position" if not mul_zero else f"holds in {mul_zero}"))
    b_one = all(vals.get((s["id"], "B", "fmi")) == vals.get((s["id"], "B", "other")) for s in SEGMENTS)
    sign_note = (" | position B carries one value, so the two compositions reduce to (A gap) and log(A ratio) and "
                 "their agreeing in sign is forced: here the sign check is a code check" if b_one else "")
    det = "; ".join(f"segment {sid}: pp {q['square']['pp'] if q['square'] else None} "
                    f"({q['square'].get('pp_multiple') if q['square'] else None} x floor), log "
                    f"{q['square'].get('log') if q['square'] else None} "
                    f"({q['square'].get('log_multiple') if q['square'] else None} x floor), {q['why']}"
                    for sid, q in sqs.items())
    det += sign_note + " | rival shapes: " + "; ".join(shapes)
    crit.append({"name": "B151-4", "kind": "own_reading", "passed": sq_state,
                 "statement": "the 2 x 2 square (class x position) of the written values (a reference rate at A, a "
                              "ceiling at B), in percentage points and in logs, against the publication grid of the "
                              "rates",
                 "detail": det, "squares": sqs, "rival_shapes": shapes})

    # B151-5
    pos_rows, st = {}, True
    present = sorted({k[0] for k in cells})
    for p in POSITIONS:
        if p not in present:
            st = None
            pos_rows[f"all/{p}"] = {"classes_present": [], "note": "no classes written at this position"}
    for s in SEGMENTS:
        for p in present:
            c = count_position(cells, vals, ver, s["id"], p)
            c["unwritten_classes"] = UNWRITTEN.get(p, [])
            pos_rows[f"{s['id']}/{p}"] = c
            if c["missing"] or not c["classes_present"]:
                st = None
            elif st is not None and c["n_values"] != c["separately_written"]:
                st = False
    det = "; ".join(f"{k}: {c['n_values']} values for {c['separately_written']} separately written classes "
                    f"{c['entries']}, not written for {c['unwritten_classes']}"
                    + (f", missing {c['missing']}" if c["missing"] else "") if "n_values" in c
                    else f"{k}: {c['note']}" for k, c in pos_rows.items())
    crit.append({"name": "B151-5", "kind": "own_reading", "passed": st,
                 "statement": "at each position the number of distinct values equals the number of classes written "
                              "separately",
                 "grid_note": "position B (early withdrawal): one class named, one value written; a scalar field also "
                              "answers one value there, both answers agree and the counting law predicts exactly one",
                 "detail": det, "by_position": pos_rows})

    # B151-6
    if second_step:
        ext = copy.deepcopy(cells)
        ext.update(second_step["cells"])
        sub = evaluate(cells=ext, rates=rates, snaps=snaps, overrides=overrides, second_step=None, today=today,
                       latest_statement=latest_statement)
        r5 = next(c for c in sub["criteria"] if c["name"] == "B151-5")
        r2 = next(c for c in sub["criteria"] if c["name"] == "B151-2")
        n_pos = len({k[0] for k in ext})
        # The second step's cells pass the same sentence checks as the first step's before their count is read.
        crit.append({"name": "B151-6", "kind": "own_reading", "passed": r5["passed"] if r2["passed"] else None,
                     "statement": "when the second-step text is out, read it and recompute positions and counts",
                     "detail": (f"recomputed with {n_pos} positions: {r5['detail']}" if r2["passed"] else
                                f"second-step cells fail the sentence checks, count not read: {r2['detail']}"),
                     "positions": n_pos, "recomputed": True})
    else:
        lapsed = today > LAPSE_DATE
        crit.append({"name": "B151-6", "kind": "own_reading", "passed": None,
                     "statement": "when the second-step text is out, read it and recompute positions and counts",
                     "detail": ("announced, not landed" if lapsed else "waiting for the event")
                               + f": no text as of {today}; checks " + json.dumps(SECOND_STEP_CHECKS, ensure_ascii=False),
                     "positions": len({k[0] for k in cells}), "recomputed": False})
    for c in crit:
        c["mapping"] = MAPPINGS[c["name"]]
    return {"criteria": crit, "rates_read": read, "latest_statement": infl, "segments": seg, "cells": ver,
            "values": {"/".join(k): fmt(v, 4) for k, v in vals.items()}}


def by(res, name):
    return next(c for c in res["criteria"] if c["name"] == name)


def seeded_faults(snaps):
    out = {}
    base = evaluate(snaps=snaps)
    out["baseline: one to five pass, six waits"] = (
        all(by(base, f"B151-{i}")["passed"] is True for i in range(1, 6)) and by(base, "B151-6")["passed"] is None)

    # B151-1
    r = [x for x in copy.deepcopy(RATES) if not (x["rate"] == "rr7" and x["effective"] == "2025-05-08")]
    out["1: a notice removed fails one"] = by(evaluate(rates=r, snaps=snaps), "B151-1")["passed"] is False
    r = copy.deepcopy(RATES)
    r[2]["value"] = 1.50
    out["1: 1.40 written as 1.50 fails one"] = by(evaluate(rates=r, snaps=snaps), "B151-1")["passed"] is False
    r = copy.deepcopy(RATES)
    r[2]["effective"] = "2025-06-01"
    out["1: a cut date that the notice does not print fails one"] = by(evaluate(rates=r, snaps=snaps),
                                                                      "B151-1")["passed"] is False
    r = copy.deepcopy(RATES)
    r[1]["value"] = 1.70
    out["1: segment one's 1.50 written as 1.70 fails one"] = by(evaluate(rates=r, snaps=snaps),
                                                                "B151-1")["passed"] is False
    global SEGMENTS
    kept = SEGMENTS
    try:
        SEGMENTS = [{"id": "one", "start": "2024-12-01", "end": "2025-06-30"},
                    {"id": "two", "start": "2025-07-01", "end": READ_DATE}]
        out["1: a segment cut that is not the notice's date fails one"] = by(evaluate(snaps=snaps), "B151-1")["passed"] is False
    finally:
        SEGMENTS = kept
    s2 = copy.deepcopy(snaps)
    f = LATEST_STATEMENTS[0]["file"]
    s2[f]["text"] = s2[f]["text"].replace("7天1.40%", "7天1.50%")
    out["1: a reading-date operation at another rate fails one"] = by(evaluate(snaps=s2), "B151-1")["passed"] is False

    # B151-2
    c = copy.deepcopy(CELLS)
    c[("A", "fmi")]["modal"] = []
    out["2: a cell without modal wording fails two"] = by(evaluate(cells=c, snaps=snaps), "B151-2")["passed"] is False
    c = copy.deepcopy(CELLS)
    c[("B", "other")]["modal"] = ["参考"]
    out["2: modal wording not in the sentence fails two"] = by(evaluate(cells=c, snaps=snaps),
                                                               "B151-2")["passed"] is False
    c = copy.deepcopy(CELLS)
    c[("A", "other")]["sources"] = ["no_such_snapshot.html"]
    out["2: a snapshot path not on disk fails two"] = by(evaluate(cells=c, snaps=snaps), "B151-2")["passed"] is False
    s2 = dict(snaps)
    s2.pop(EXISTENCE["file"])
    out["2: central bank release missing fails two"] = by(evaluate(snaps=s2), "B151-2")["passed"] is False
    c = copy.deepcopy(CELLS)
    c[("A", "fmi")]["anchor"], c[("A", "other")]["anchor"] = "rr7", "ioer"
    out["2: the two anchors at position A swapped fails two"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-2")["passed"] is False)
    c = copy.deepcopy(CELLS)
    c[("B", "fmi")]["anchor"] = c[("B", "other")]["anchor"] = "rr7"
    out["2: both early-withdrawal cells taken from the 7-day rate fails two"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-2")["passed"] is False)

    # B151-3
    c = copy.deepcopy(CELLS)
    c[("A", "fmi")]["anchor"] = "rr7"
    out["3: infrastructure cell pointed at the 7-day rate fails three"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-3")["passed"] is False)
    c = copy.deepcopy(CELLS)
    c[("A", "other")]["anchor"] = None
    out["3: a cell without a value leaves three without a verdict"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-3")["passed"] is None)
    c = copy.deepcopy(CELLS)
    c[("A", "other")]["entry"] = "no_such_sentence"
    out["3: a cell whose sentence is on no page leaves three without a verdict"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-3")["passed"] is None)
    c = copy.deepcopy(CELLS)
    c[("A", "other")]["entry"] = "A_fmi"
    out["3: two values under one named class at position A fails three"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-3")["passed"] is False)

    # B151-4
    c = copy.deepcopy(CELLS)
    c[("B", "other")]["anchor"] = "rr7"
    res = evaluate(cells=c, snaps=snaps)
    sq = res["criteria"][3]["squares"]["two"]["square"]
    out["4: other non-bank at B on the 7-day rate: both squares zero, no verdict"] = (
        by(res, "B151-4")["passed"] is None and float(sq["pp"]) == 0.0 and abs(float(sq["log"])) < 1e-12)
    res = evaluate(snaps=snaps, overrides={("two", "B", "fmi"): 0.35 * 0.35 / 1.40})
    sq = by(res, "B151-4")["squares"]["two"]["square"]
    out["4: infrastructure at B = 0.0875: log square zero, pp not, no verdict"] = (
        by(res, "B151-4")["passed"] is None and abs(float(sq["log"])) < 1e-9 and abs(float(sq["pp"])) > GRID)
    res = evaluate(snaps=snaps, overrides={("two", "B", "fmi"): 0.0876})
    sq = by(res, "B151-4")["squares"]["two"]["square"]
    out["4: log square inside its floor while pp clears, same sign: no verdict"] = (
        by(res, "B151-4")["passed"] is None and 0 < float(sq["log"]) < float(sq["log_floor"]))
    res = evaluate(snaps=snaps, overrides={("one", "A", "other"): 0.35 + 0.004})
    out["4: a square inside the floor leaves four without a verdict"] = by(res, "B151-4")["passed"] is None

    # B151-5
    c = {k: v for k, v in copy.deepcopy(CELLS).items() if k[0] != "B"}
    out["5: position B with no classes leaves five without a verdict"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-5")["passed"] is None)
    c = copy.deepcopy(CELLS)
    c[("B", "other")]["anchor"] = "rr7"
    out["5: other non-bank at B moved to 1.40 under one entry fails five"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-5")["passed"] is False)
    c = copy.deepcopy(CELLS)
    c[("B", "other")]["anchor"] = None
    res = evaluate(cells=c, snaps=snaps)
    out["5: a cell at B without a value leaves five and four without a verdict"] = (
        by(res, "B151-5")["passed"] is None and by(res, "B151-4")["passed"] is None)
    c = copy.deepcopy(CELLS)
    c[("B", "other")]["entry"] = "no_such_sentence"
    out["5: a cell at B whose sentence is on no page leaves five without a verdict"] = (
        by(evaluate(cells=c, snaps=snaps), "B151-5")["passed"] is None)
    s2 = copy.deepcopy(snaps)
    for f in TRANSCRIPTIONS:
        s2[f]["text"] = s2[f]["text"].replace("原则上不应高于超额存款准备金利率", "")
    res = evaluate(snaps=s2)
    out["4/5: the early-withdrawal sentence gone from every page leaves four and five without a verdict"] = (
        by(res, "B151-4")["passed"] is None and by(res, "B151-5")["passed"] is None)

    # B151-6
    fake = {"cells": {("T", "fmi"): {"entry": "A_fmi", "anchor": "ioer", "modal": ["参考"], "sources": TRANSCRIPTIONS,
                                      "level": "seed"},
                      ("T", "other"): {"entry": "A_other", "anchor": "rr7", "modal": ["参考"], "sources": TRANSCRIPTIONS,
                                        "level": "seed"}}}
    res = evaluate(snaps=snaps, second_step=fake)
    six = by(res, "B151-6")
    out["6: a second-step table is read and the count recomputed with one more position"] = (
        six["recomputed"] is True and six["positions"] == 3 and six["passed"] is not None)
    # Two verified sentences that write the same value for two classes: one value for two entries.
    bad = {"cells": {("T", "fmi"): {"entry": "B_all", "anchor": "ioer", "modal": ["原则上不应高于"],
                                     "sources": TRANSCRIPTIONS, "level": "seed"},
                     ("T", "other"): {"entry": "A_fmi", "anchor": "ioer", "modal": ["参考"],
                                       "sources": TRANSCRIPTIONS, "level": "seed"}}}
    out["6: a second step whose recount fails is a FAIL"] = (
        by(evaluate(snaps=snaps, second_step=bad), "B151-6")["passed"] is False)
    nowhere = {"cells": {("T", "fmi"): {"entry": "no_such_sentence", "anchor": "ioer", "modal": ["参考"],
                                         "sources": TRANSCRIPTIONS, "level": "seed"},
                         ("T", "other"): {"entry": "no_such_sentence", "anchor": "rr7", "modal": ["参考"],
                                           "sources": TRANSCRIPTIONS, "level": "seed"}}}
    out["6: a second step whose sentences are on no page leaves six without a verdict"] = (
        by(evaluate(snaps=snaps, second_step=nowhere), "B151-6")["passed"] is None)
    unread_b = {"cells": {("T", "fmi"): {"entry": "A_fmi", "anchor": "ioer", "modal": ["参考"],
                                          "sources": TRANSCRIPTIONS, "level": "seed"},
                          ("T", "other"): {"entry": "A_other", "anchor": "rr7", "modal": ["参考"],
                                            "sources": TRANSCRIPTIONS, "level": ""}}}
    out["6: a second-step cell without a source level leaves six without a verdict"] = (
        by(evaluate(snaps=snaps, second_step=unread_b), "B151-6")["passed"] is None)
    out["6: empty text leaves six without a verdict"] = by(evaluate(snaps=snaps, second_step={}),
                                                         "B151-6")["passed"] is None
    after = by(evaluate(snaps=snaps, today="2027-04-01"), "B151-6")
    out["6: past the lapse date reads 'announced, not landed'"] = (
        after["passed"] is None and after["detail"].startswith("announced, not landed"))

    # snapshots: a copy with one byte changed is refused and carries nothing
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copyfile(SNAP / "b151_manifest.json", tmp / "b151_manifest.json")
        f = EXISTENCE["file"]
        b = bytearray((SNAP / f).read_bytes())
        b[-2] = (b[-2] + 1) % 256
        (tmp / f).write_bytes(bytes(b))
        ok, refused = load_snapshots(tmp)
    out["snapshots: a changed byte is refused"] = f not in ok and any(r.startswith(f) for r in refused)
    s2 = copy.deepcopy(snaps)
    for f in TRANSCRIPTIONS:
        s2[f]["text"] = s2[f]["text"].replace("合理确定", "")
    out["snapshots: sentences gone from every page leave three without a verdict"] = (
        by(evaluate(snaps=s2), "B151-3")["passed"] is None)
    return out


def build_record(snaps, bad, checks, seconds):
    res = evaluate(snaps=snaps)
    man = json.loads((SNAP / "b151_manifest.json").read_text(encoding="utf-8"))
    config = {
        "segments": SEGMENTS, "read_date": READ_DATE, "lapse_date": LAPSE_DATE,
        "floor": {"pp": "0.01, the two-decimal publication grid of both policy rates",
                  "log": "log((x + 0.01) / x), x the smallest of the four square cells"},
        "compositions": {"pp": "(other - fmi)@A - (other - fmi)@B",
                         "log": "log(other / fmi)@A - log(other / fmi)@B"},
        "unit_of_count": "one initiative; values are the policy rates the sentences refer to, in the segment",
        "values_are": "written values: a reference rate at A, a ceiling at B; no rate actually paid is read",
        "classes": CLASSES, "positions": POSITIONS, "not_at_these_positions": NOT_AT_THESE_POSITIONS,
    }
    return {"stage": "B151", "config": config, "criteria": res["criteria"], "rates_read": res["rates_read"],
            "latest_statement": res["latest_statement"], "cells": {"/".join(k): v for k, v in res["cells"].items()},
            "values": res["values"], "quotes": QUOTES,
            "snapshots": [{k: r[k] for k in ("file", "url", "publisher", "published", "read_on", "d47_level",
                                              "sha256")} for r in man["snapshots"]],
            "snapshots_unverified": bad, "selftest": {k: bool(v) for k, v in checks.items()},
            "second_step": {"text": SECOND_STEP, "checks": SECOND_STEP_CHECKS}}


def show(rec):
    print("rates read off the notices:")
    for r in rec["rates_read"]:
        print(f"    {r['rate']:5s} table {r['table_value']} from {r['table_effective']}  read {r['read_value']} "
              f"from {r['read_effective']}  {'agrees' if r['agrees'] else 'DISAGREES'}  ({r['file']})")
    for r in rec["latest_statement"]:
        print(f"    {r['rate']:5s} latest statement: {r['read']} ({r['file']}, published {r['published']}, "
              f"{r['level']})")
    print("cells:")
    for k, v in rec["cells"].items():
        print(f"    {k:8s} anchor {v['anchor']}, modal {'+'.join(v['modal'])}, on {len(v['found_in'])}/"
              f"{len(v['listed'])} snapshots: {v['sentence']}")
    print("values by segment/position/class:")
    for k, v in sorted(rec["values"].items()):
        print(f"    {k:14s} {v}")
    print()
    for c in rec["criteria"]:
        print(f"  {({True: 'PASS', False: 'FAIL', None: 'UNREAD'})[c['passed']]:6s} {c['name']} [{c['kind']}"
              + (f", grid {c['grid']}" if c.get("grid") else "") + "]")
        for cell, v in c["mapping"].items():
            print(f"         map: {cell} -> {v}")
        print(f"         {c['detail']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.perf_counter()
    snaps, bad = load_snapshots(SNAP)
    checks = seeded_faults(snaps)
    if a.selftest:
        for name, ok in sorted(checks.items()):
            print(f"  {'caught' if ok else 'MISSED':7s} {name}")
        print(f"snapshots unverified: {bad}")
        return 0 if all(checks.values()) and not bad else 1
    rec = build_record(snaps, bad, checks, time.perf_counter() - t0)
    show(rec)
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    # Use the shared compare-and-swap writer when it sits next to the repository; otherwise a plain write.
    sys.path.insert(0, str(ROOT.parent))
    try:
        from safe_write import create, rewrite
    except ImportError:
        create = rewrite = None
    if rewrite is None:
        RECORD.write_text(text, encoding="utf-8", newline="\n")
    elif RECORD.exists():
        rewrite(RECORD, "B151 record", lambda _old: text, session="B151")
    else:
        create(RECORD, "B151 record", text, session="B151")
    print(f"\nwrote {RECORD.name}; {time.perf_counter() - t0:.1f} s (not in the record)")
    return 0 if all(checks.values()) and all(c["passed"] is not False for c in rec["criteria"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
