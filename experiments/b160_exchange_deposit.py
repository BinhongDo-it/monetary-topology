"""B160: India, November 2016. One withdrawn note, two paths: over-the-counter exchange for cash
(capped per person, the cap moved in steps and then the path was shut at bank counters) and deposit
into an account (no cap). The Reserve Bank printed both flows separately in two releases.

The cap on the exchange path is a narrowed edge, not a deleted one, until 2016-11-24; the price on
both paths is the same (face value). The station reads what the flow does when the edge narrows,
with the steps of the cap laid out as a dose table, not as one step.

Criteria (kind in brackets):
  B160-1 [instrument]   each release's exchange and deposits add to its stated total within the
                        crore format (each figure rounded to a crore, so the residue is at most 1)
  B160-2 [instrument]   the two words of the release map to the two rows of the banks' daily report
                        (circular DCM 1264, Annex 6: "Exchanged in Cash", "Deposits into Account")
  B160-3 [premise]      how many releases in the scanned range carry the split; two or more give
                        two segments, one gives none, zero means no object
  B160-4 [own_reading]  dose table by segment: days under each cap, ink, closure; daily exchange
                        and deposits; the second segment's daily exchange against the first's
  B160-5 [own_reading]  bound: the flow ratio against the largest ratio the per-event cap can carry
                        (4,500 over the smallest note, 500); the counter events fell at least by the rest
  B160-6 [own_reading]  the exchange share of notes tendered, by segment; deposits' own daily flow
                        and the shortfall against a proportional fall printed beside it

No rival criterion: a scalar price field puts the same price on both paths (face value) and says
nothing about how flow splits between them; the framework gives no opposite point prediction here.

usage:
  python -B experiments/b160_exchange_deposit.py              run, write results/b160_exchange_deposit.json
  python -B experiments/b160_exchange_deposit.py --selftest   planted errors, each flag must flip
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b160"
SNAPSHOT = RAW / "b160_text_snapshot.json"
INDEX = RAW / "b160_scan_index.json"
RECORD = ROOT / "results" / "b160_exchange_deposit.json"
SESSION = "B156_1029"

SPLIT_RELEASES = ("pr38643", "pr38727")
START = "2016-11-10"           # exchange and deposit open (circular DCM 1226, notice 2016-11-08)
SMALLEST_NOTE = 500            # the smaller of the two withdrawn denominations
CRORE_FLOOR = 1                # three figures each rounded to a crore: |residue| <= 1

# Dated steps on the exchange path, each with the source that fixes it.
# cap: rupees per person per exchange; None = no exchange at bank counters.
STEPS = [
    ("2016-11-10", "cap", 4000, "c10684", "exchange up to 4,000 per person with proof of identity"),
    ("2016-11-13", "cap", 4500, "c10706", "limit raised to 4,500, immediate effect; separate queues"),
    ("2016-11-15", "ink", None, "c10713", "indelible ink on the right index finger, metro cities first"),
    ("2016-11-18", "cap", 2000, "c10719", "limit 2,000, once per person"),
    ("2016-11-25", "cap", None, "c10740", "no exchange at bank counters after midnight of 2016-11-24"),
]
RBI_COUNTERS_AFTER_CLOSE = 2000   # pr38695: Reserve Bank counters keep exchanging "upto the current limits"

# 11c: every state each criterion can land in, and the verdict it maps to.
MAPPING = [
    ("B160-1", "every residue within the crore floor", True),
    ("B160-1", "a residue beyond the crore floor", False),
    ("B160-2", "all four phrases found", True),
    ("B160-2", "a phrase missing", False),
    ("B160-3", "two or more releases carry the split", True),
    ("B160-3", "one release carries the split: no segment to compare", None),
    ("B160-3", "no release carries the split: no object", False),
    ("B160-4", "second segment's daily exchange below the first's", True),
    ("B160-4", "not below", False),
    ("B160-4", "fewer than two segments", None),
    ("B160-5", "flow ratio above the largest per-event amount ratio", True),
    ("B160-5", "flow ratio at or below it", False),
    ("B160-5", "fewer than two segments", None),
    ("B160-6", "exchange share lower in the second segment", True),
    ("B160-6", "not lower", False),
    ("B160-6", "fewer than two segments", None),
]

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], start=1)}
SPLIT_RE = re.compile(
    r"from (\w+ \d+, \d{4}) upto (\w+ \d+, \d{4}) amounted to ₹\s*([\d,]+) crore\s*"
    r"\(exchange amounted to ₹\s*([\d,]+) crore and deposits amounted to ₹\s*([\d,]+) crore\)")
WITHDRAW_RE = re.compile(r"withdrawn, during this period, ₹\s*([\d,]+) crore")


def num(s: str) -> int:
    return int(s.replace(",", ""))


def day(s: str) -> dt.date:
    if "," in s:
        m, d, y = re.match(r"(\w+) (\d+), (\d{4})", s).groups()
        return dt.date(int(y), MONTHS[m], int(d))
    return dt.date.fromisoformat(s)


def load_snapshot(path=SNAPSHOT) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {s["key"]: s for s in d["sources"]}


def parse_release(text: str) -> dict | None:
    m = SPLIT_RE.search(text)
    if not m:
        return None
    w = WITHDRAW_RE.search(text)
    return {"from": day(m.group(1)).isoformat(), "upto": day(m.group(2)).isoformat(),
            "total": num(m.group(3)), "exchange": num(m.group(4)), "deposits": num(m.group(5)),
            "withdrawn": num(w.group(1)) if w else None}


def releases(snap: dict) -> list:
    out = []
    for k in SPLIT_RELEASES:
        r = parse_release(snap[k]["text"]) if k in snap else None
        if r:
            r["key"] = k
            out.append(r)
    return sorted(out, key=lambda r: r["upto"])


def regime_on(d: dt.date, steps=STEPS) -> dict:
    cap, ink = None, False
    for date, kind, val, _src, _note in steps:
        if day(date) <= d:
            if kind == "cap":
                cap = val
            elif kind == "ink":
                ink = True
    if cap is None and d >= day("2016-11-25"):
        where = "Reserve Bank counters only"
        cap = RBI_COUNTERS_AFTER_CLOSE
    else:
        where = "bank and Reserve Bank counters"
    return {"cap": cap, "ink": ink, "where": where}


def segments(rels: list, steps=STEPS) -> list:
    """Increments between consecutive cumulative releases, the first from START."""
    segs, prev = [], None
    for r in rels:
        lo = day(START) if prev is None else day(prev["upto"]) + dt.timedelta(days=1)
        hi = day(r["upto"])
        n = (hi - lo).days + 1
        e = r["exchange"] - (prev["exchange"] if prev else 0)
        p = r["deposits"] - (prev["deposits"] if prev else 0)
        t = r["total"] - (prev["total"] if prev else 0)
        w = (r["withdrawn"] - (prev["withdrawn"] if prev else 0)) if r["withdrawn"] is not None else None
        regimes = {}
        caps = []
        for i in range(n):
            g = regime_on(lo + dt.timedelta(days=i), steps)
            key = f"cap {g['cap']}, {'ink' if g['ink'] else 'no ink'}, {g['where']}"
            regimes[key] = regimes.get(key, 0) + 1
            caps.append(g["cap"])
        segs.append({"from": lo.isoformat(), "upto": hi.isoformat(), "days": n, "exchange": e, "deposits": p,
                     "total": t, "withdrawn": w, "regime_days": regimes, "max_cap": max(caps),
                     "day_weighted_cap": f"{sum(caps) / n:.1f}",
                     "exchange_per_day": f"{e / n:.1f}", "deposits_per_day": f"{p / n:.1f}",
                     "exchange_share": f"{e / (e + p):.6f}"})
        prev = r
    return segs


# ---------------------------------------------------------------- criteria

def b160_1(rels):
    rows = [{"release": r["key"], "upto": r["upto"], "total": r["total"],
             "exchange_plus_deposits": r["exchange"] + r["deposits"],
             "residue": r["total"] - r["exchange"] - r["deposits"]} for r in rels]
    if not rows:
        return False, {"rows": rows}
    return all(abs(x["residue"]) <= CRORE_FLOOR for x in rows), {"rows": rows}


PHRASES = [
    ("c10698", "Exchanged in Cash"),
    ("c10698", "Deposits into Account"),
    ("pr38643", "exchange amounted to"),
    ("pr38727", "deposits amounted to"),
]
COUNTERS = "counters of the Reserve Bank and commercial banks"


def b160_2(snap, phrases=PHRASES):
    found = [{"source": k, "phrase": p, "found": k in snap and p.lower() in snap[k]["text"].lower()}
             for k, p in phrases]
    both_counters = all(k in snap and COUNTERS.lower() in snap[k]["text"].lower() for k in SPLIT_RELEASES)
    return all(f["found"] for f in found) and both_counters, {"phrases": found,
                                                              "releases_name_both_counters": both_counters}


def b160_3(index_rows):
    split = [r["id"] for r in index_rows if r.get("split_phrase")]
    sbn = [r for r in index_rows if r.get("sbn_related")]
    rep = {"pages_read": len(index_rows),
           "press_releases_read": sum(r["kind"] == "press_release" for r in index_rows),
           "circulars_read": sum(r["kind"] == "circular" for r in index_rows),
           "sbn_related": len(sbn), "carry_split": split}
    if len(split) >= 2:
        return True, rep
    if len(split) == 1:
        return None, rep
    return False, rep


def b160_4(segs):
    if len(segs) < 2:
        return None, {"segments": segs}
    a, b = segs[0], segs[1]
    return (b["exchange"] / b["days"]) < (a["exchange"] / a["days"]), {"segments": segs}


def b160_5(segs, smallest=SMALLEST_NOTE):
    if len(segs) < 2:
        return None, {}
    a, b = segs[0], segs[1]
    ratio = (a["exchange"] / a["days"]) / (b["exchange"] / b["days"]) if b["exchange"] else float("inf")
    amount_max = a["max_cap"] / smallest
    # at the cap: everyone exchanges the cap in force; first segment 4,000 or 4,500, second 2,000
    at_cap_hi = 4500 / b["max_cap"]
    at_cap_lo = 4000 / b["max_cap"]
    rep = {"flow_ratio": f"{ratio:.4f}",
           "flow_ratio_floor_range": [f"{(a['exchange'] - 0.5) / (b['exchange'] + 0.5):.4f}",
                                      f"{(a['exchange'] + 0.5) / (b['exchange'] - 0.5):.4f}"],
           "largest_amount_ratio": f"{amount_max:.4f}",
           "events_ratio_at_least": f"{ratio / amount_max:.4f}",
           "events_ratio_if_at_cap": [f"{ratio / at_cap_hi:.4f}", f"{ratio / at_cap_lo:.4f}"],
           "events_first_segment_at_least_crore": f"{a['exchange'] / a['max_cap']:.4f}",
           "events_second_segment_at_least_crore": f"{b['exchange'] / b['max_cap']:.4f}",
           "events_first_segment_at_most_crore": f"{a['exchange'] / smallest:.4f}",
           "events_second_segment_at_most_crore": f"{b['exchange'] / smallest:.4f}"}
    return ratio > amount_max, rep


def b160_6(segs):
    if len(segs) < 2:
        return None, {}
    a, b = segs[0], segs[1]
    sa = a["exchange"] / (a["exchange"] + a["deposits"])
    sb = b["exchange"] / (b["exchange"] + b["deposits"])
    dep_ratio = (b["deposits"] / b["days"]) / (a["deposits"] / a["days"])
    cf = a["exchange"] * dep_ratio * b["days"] / a["days"]
    short = cf - b["exchange"]
    rep = {"share_first": f"{sa:.6f}", "share_second": f"{sb:.6f}",
           "deposits_daily_ratio_second_over_first": f"{dep_ratio:.4f}",
           "exchange_if_it_fell_like_deposits": f"{cf:.1f}", "shortfall": f"{short:.1f}",
           "shortfall_over_second_deposits": f"{short / b['deposits']:.6f}",
           "withdrawn_first": a["withdrawn"], "withdrawn_second": b["withdrawn"]}
    return sb < sa, rep


# ---------------------------------------------------------------- selftest

def fake_text(frm, upto, total, ex, dep, wd=1000):
    return (f"Consequent to ... at the counters of the Reserve Bank and commercial banks, Regional Rural banks. "
            f"Banks have since reported that such exchange/deposits effected from {frm} upto {upto} amounted to "
            f"₹ {total:,} crore (exchange amounted to ₹ {ex:,} crore and deposits amounted to ₹ {dep:,} crore). "
            f"They have also reported that the public have withdrawn, during this period, ₹ {wd:,} crore.")


def fake_snap(r1=(5000, 300, 4700), r2=(8000, 330, 7670)):
    return {
        "pr38643": {"text": fake_text("November 10, 2016", "November 18, 2016", *r1)},
        "pr38727": {"text": fake_text("November 10, 2016", "November 27, 2016", *r2, wd=3000)},
        "c10698": {"text": "Particulars Exchanged in Cash Deposits into Account Total"},
    }


def run_selftest(verbose=False):
    out = []

    def expect(cond, msg):
        out.append({"check": msg, "ok": bool(cond)})
        if verbose:
            print(("ok   " if cond else "FAIL ") + msg)

    snap = fake_snap()
    rels = releases(snap)
    expect(len(rels) == 2 and rels[0]["exchange"] == 300 and rels[1]["deposits"] == 7670,
           "parser reads both releases and their figures")
    # 1
    p, _ = b160_1(rels)
    expect(p is True, "B160-1 passes when the parts add to the total")
    bad = releases(fake_snap(r1=(5003, 300, 4700)))
    p, _ = b160_1(bad)
    expect(p is False, "B160-1 fails on a residue of three crore")
    p, _ = b160_1([])
    expect(p is False, "B160-1 fails when no release parses")
    # 2
    p, _ = b160_2(snap)
    expect(p is True, "B160-2 passes with all phrases present")
    s2 = dict(snap)
    s2["c10698"] = {"text": "Particulars Exchanged Deposits Total"}
    p, _ = b160_2(s2)
    expect(p is False, "B160-2 fails when the report row names are missing")
    s3 = dict(snap)
    s3["pr38643"] = {"text": snap["pr38643"]["text"].replace("Reserve Bank and commercial", "commercial")}
    p, _ = b160_2(s3)
    expect(p is False, "B160-2 fails when a release does not name both kinds of counter")
    # 3
    idx = [{"kind": "press_release", "id": i, "split_phrase": i in (1, 2), "sbn_related": True} for i in range(5)]
    p, _ = b160_3(idx)
    expect(p is True, "B160-3 passes with two releases carrying the split")
    p, _ = b160_3([dict(r, split_phrase=r["id"] == 1) for r in idx])
    expect(p is None, "B160-3 carries no verdict with one release")
    p, _ = b160_3([dict(r, split_phrase=False) for r in idx])
    expect(p is False, "B160-3 fails with none")
    # 4
    segs = segments(rels)
    expect(segs[0]["days"] == 9 and segs[1]["days"] == 9, "segments are nine days each")
    expect(segs[0]["regime_days"].get("cap 4500, no ink, bank and Reserve Bank counters") == 2
           and segs[0]["regime_days"].get("cap 4500, ink, bank and Reserve Bank counters") == 3,
           "the 4,500 days split at the ink date")
    expect(segs[1]["regime_days"].get("cap 2000, ink, Reserve Bank counters only") == 3,
           "the last three days are Reserve Bank counters only")
    p, _ = b160_4(segs)
    expect(p is True, "B160-4 passes when daily exchange falls")
    up = segments(releases(fake_snap(r2=(8400, 700, 7700))))
    p, _ = b160_4(up)
    expect(p is False, "B160-4 fails when daily exchange rises")
    p, _ = b160_4(segs[:1])
    expect(p is None, "B160-4 carries no verdict with one segment")
    # 5
    p, rep = b160_5(segs)
    expect(p is True and rep["flow_ratio"] == "10.0000", "B160-5 passes at a flow ratio of 10 against 9")
    nine = segments(releases(fake_snap(r1=(5000, 270, 4730), r2=(8000, 300, 7700))))
    p, _ = b160_5(nine)
    expect(p is False, "B160-5 fails at a flow ratio of 9")
    p, _ = b160_5(segs[:1])
    expect(p is None, "B160-5 carries no verdict with one segment")
    # 6
    p, _ = b160_6(segs)
    expect(p is True, "B160-6 passes when the exchange share falls")
    same = segments(releases(fake_snap(r1=(1000, 100, 900), r2=(2000, 200, 1800))))
    p, _ = b160_6(same)
    expect(p is False, "B160-6 fails when the exchange share holds")
    # regime table against the sources
    expect(regime_on(day("2016-11-12"))["cap"] == 4000 and regime_on(day("2016-11-13"))["cap"] == 4500
           and regime_on(day("2016-11-18"))["cap"] == 2000 and not regime_on(day("2016-11-14"))["ink"]
           and regime_on(day("2016-11-15"))["ink"], "regime dates follow the circulars")
    # 11c: the third states map to no verdict
    expect(all(v is None for _c, s, v in MAPPING if "fewer than two" in s or "one release" in s),
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
    snap = load_snapshot()
    index_rows = json.loads(INDEX.read_text(encoding="utf-8"))["rows"]
    rels = releases(snap)
    segs = segments(rels)
    p1, r1 = b160_1(rels)
    p2, r2 = b160_2(snap)
    p3, r3 = b160_3(index_rows)
    p4, r4 = b160_4(segs)
    p5, r5 = b160_5(segs)
    p6, r6 = b160_6(segs)

    for x in r1["rows"]:
        print(f"B160-1 {x['release']} upto {x['upto']}: total {x['total']}, parts {x['exchange_plus_deposits']}, "
              f"residue {x['residue']}")
    print(f"B160-2 {r2}")
    print(f"B160-3 pages {r3['pages_read']} (press {r3['press_releases_read']}, circulars {r3['circulars_read']}), "
          f"SBN-related {r3['sbn_related']}, carry the split {r3['carry_split']}")
    for s in segs:
        print(f"B160-4 {s['from']}..{s['upto']} ({s['days']} d): exchange {s['exchange']} ({s['exchange_per_day']}/d), "
              f"deposits {s['deposits']} ({s['deposits_per_day']}/d), share {s['exchange_share']}, "
              f"withdrawn {s['withdrawn']}")
        for k, v in s["regime_days"].items():
            print(f"         {v} d  {k}")
    print(f"B160-5 {r5}")
    print(f"B160-6 {r6}")

    s1, s2 = segs[0], segs[1]
    later = [(k, snap[k]["note"]) for k in ("pr38839", "pr38886", "pr38980", "pr39163") if k in snap]
    crit = [
        {"name": "B160-1", "kind": "instrument", "passed": p1,
         "detail": "Stated total against exchange plus deposits: "
                   + "; ".join(f"up to {x['upto']} total {x['total']}, parts {x['exchange_plus_deposits']}, residue "
                               f"{x['residue']}" for x in r1["rows"])
                   + " (crore). Each figure is rounded to a crore, so a residue of one is the format."},
        {"name": "B160-2", "kind": "instrument", "passed": p2,
         "detail": "The banks' daily report (circular DCM 1264, 2016-11-11, Annex 6 and 6A) has the rows "
                   "'Exchanged in Cash' and 'Deposits into Account'; the two releases print 'exchange amounted to' "
                   "and 'deposits amounted to' and name the counters of the Reserve Bank and the banks. The release "
                   "words are the report rows. Phrases: "
                   + ", ".join(f"{f['source']} '{f['phrase']}' {f['found']}" for f in r2["phrases"]) + "."},
        {"name": "B160-3", "kind": "premise", "passed": p3,
         "detail": f"Pages read: {r3['press_releases_read']} press releases (prid 38520-39259, 2016-11-08 to "
                   f"2017-01) and {r3['circulars_read']} circulars (Id 10670-10779); {r3['sbn_related']} concern the "
                   f"withdrawn notes; those that print exchange and deposits apart: {r3['carry_split']}. Later "
                   "releases print other objects: " + "; ".join(f"{k} {n}" for k, n in later)
                   + ". The banks reported daily (Annex 6A); only two cumulative points were published, so the "
                   "daily shape is not readable and the reading is two segments."},
        {"name": "B160-4", "kind": "own_reading", "passed": p4,
         "detail": " | ".join(
             f"{s['from']} to {s['upto']} ({s['days']} days): exchange {s['exchange']} crore "
             f"({s['exchange_per_day']} a day), deposits {s['deposits']} crore ({s['deposits_per_day']} a day); "
             "days by regime: " + ", ".join(f"{v} under {k}" for k, v in s["regime_days"].items())
             for s in segs)
             + ". The cap moved in four steps and the ink came in between; both segments hold more than one "
               "regime, so the fall belongs to the steps together and is not split among them."},
        {"name": "B160-5", "kind": "own_reading", "passed": p5,
         "detail": f"Daily exchange fell by a factor {r5['flow_ratio']} (crore rounding moves it within "
                   f"{r5['flow_ratio_floor_range'][0]} to {r5['flow_ratio_floor_range'][1]}). The amount per counter "
                   f"event can fall at most from the first segment's top cap ({s1['max_cap']}) to one {SMALLEST_NOTE} "
                   f"note, a factor {r5['largest_amount_ratio']}; so the number of counter events fell at least "
                   f"{r5['events_ratio_at_least']}-fold. If everyone exchanged the cap in force and the first segment's "
                   "flow came on its 4,000 and 4,500 days, events fell "
                   f"{r5['events_ratio_if_at_cap'][0]} to {r5['events_ratio_if_at_cap'][1]}-fold. Events: first "
                   f"segment {r5['events_first_segment_at_least_crore']} to {r5['events_first_segment_at_most_crore']} "
                   f"crore, second {r5['events_second_segment_at_least_crore']} to "
                   f"{r5['events_second_segment_at_most_crore']} crore. The narrowing worked mainly on who got "
                   "through, not on how much each one carried."},
        {"name": "B160-6", "kind": "own_reading", "passed": p6,
         "detail": f"Exchange share of notes tendered: {r6['share_first']} then {r6['share_second']}. Deposits' "
                   f"own daily flow fell too (second over first {r6['deposits_daily_ratio_second_over_first']}): "
                   "cumulative deposits rose, the flow did not. Had exchange fallen like deposits it would have been "
                   f"{r6['exchange_if_it_fell_like_deposits']} crore; the shortfall {r6['shortfall']} crore is "
                   f"{r6['shortfall_over_second_deposits']} of second-segment deposits. Whether that shortfall went "
                   "into deposits cannot be separated from the general slowing of tenders. Withdrawals: "
                   f"{r6['withdrawn_first']} then {r6['withdrawn_second']} crore."},
    ]
    record = {
        "stage": "B160",
        "title": "India 2016: exchange and deposit paths for withdrawn notes, the exchange cap in steps",
        "config": {"snapshot": SNAPSHOT.name, "index": INDEX.name, "split_releases": list(SPLIT_RELEASES),
                   "start": START, "smallest_note": SMALLEST_NOTE, "crore_floor": CRORE_FLOOR,
                   "rbi_counters_after_close": RBI_COUNTERS_AFTER_CLOSE,
                   "steps": [{"date": d, "kind": k, "value": v, "source": s, "note": n} for d, k, v, s, n in STEPS]},
        "criteria": crit,
        "mapping_11c": [{"criterion": c, "state": s, "verdict": v} for c, s, v in MAPPING],
        "selftest": st_rows,
        "releases": rels,
        "segments": segs,
        "B160_1": r1, "B160_2": r2, "B160_3": r3, "B160_5": r5, "B160_6": r6,
    }
    text = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        from safe_write import create, rewrite
        if RECORD.exists():
            rewrite(RECORD, "B160 record", lambda _t: text, session=SESSION)
        else:
            create(RECORD, "B160 record", text, session=SESSION)
        print(f"wrote {RECORD.name}")
    print("criteria:", {c["name"]: c["passed"] for c in crit})
    return 1 if any(c["passed"] is False for c in crit) else 0


if __name__ == "__main__":
    sys.exit(main())
