"""B59: the class line on reserve balances, and what the excluded class recovers.

The gross gap is read off a rule and needs no data. 12 CFR 204.2(y) lists four
kinds of eligible institution and a Federal Home Loan Bank is not among them, so
an FHLB's balance at a Federal Reserve Bank earns nothing while an eligible
institution's earns IORB. Same obligor, same instrument, same continuous
availability, no collateral either way, no maturity either way. Only the holder
differs, and the weight differs by the whole policy rate.

What needs data is the second half. The excluded class does not exit; it routes,
lending federal funds at EFFR. So

    gross      IORB                 from the rule
    net        IORB - EFFR          measured here
    recovered  EFFR                 measured here

What the net gap adjudicates is NOT the scalar-price-field rival. A Fed balance
and a fed funds loan are different positions with different obligors, so a scalar
field on positions does not require them to pay the same. It adjudicates a
narrower and named expectation, stated by the Board itself: that interest on
reserves would floor money market rates. The Board's own words are that the
ineligible participants are "willing to make loans below the IOR rate, eroding
the lower bound on money market rates that interest on reserves was expected to
create." The floor holds on a day when EFFR >= the administered rate.

Everything is integer basis points. Both series are published to two decimal
places in percent, so the grid is 1 bp and that is the resolution floor
(discipline 24). A reading whose magnitude is at or below the floor is not
readable as a sign, and it maps to no verdict (discipline 11c).

IOER and IORB are different definitional bases and never share a column (18c).

No standard errors and no test: an administered spread is heavily autocorrelated,
so the independent count is far below the day count (D22). This file prints
objects, it does not estimate.

Usage:  python experiments/b59_reserve_class_rate.py
"""
from __future__ import annotations
import csv, io, json, os, sys, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "b59")
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RAW, exist_ok=True)
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
SERIES = ["IORB", "IOER", "EFFR"]
BREAK = "2021-07-29"          # IOER's last day is 2021-07-28
FLOOR_BP = 1                  # both series publish on a 1 bp grid

# Read in a browser on 2026-09-08 before this script could reach the endpoint.
# The run must reproduce them. A mismatch is this file's own known-answer
# failure, not a finding about the world.
EXPECTED = {
    "IORB": {"n": 1281, "above": 1171, "below": 0, "within": 110},
    "IOER": {"n": 3217, "above": 2714, "below": 152, "within": 351},
    "break": {"IOER_last_bp": 15, "IORB_first_bp": 15},
}


def fetch(sid: str) -> str | None:
    """Cached, and it classifies rather than trusting the file it finds."""
    p = os.path.join(RAW, f"{sid}.csv")
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read()
        if _complete(txt, sid):
            return txt
        os.rename(p, f"{p}.expired.{date.today():%Y%m%d}")
        print(f"  {sid}: cached file failed classification, renamed, refetching")
    req = urllib.request.Request(FRED.format(sid=sid),
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode("utf-8")
    except Exception as e:                                   # noqa: BLE001
        print(f"  {sid}: FAILED {e}")
        print(f"      save the CSV by hand as {p}")
        print(f"      {FRED.format(sid=sid)}")
        return None
    if not _complete(txt, sid):
        print(f"  {sid}: fetched file fails classification, not written")
        return None
    open(p, "w", encoding="utf-8", newline="\n").write(txt)
    return txt


def _complete(txt: str, sid: str) -> bool:
    lines = [l for l in txt.splitlines() if l.strip()]
    if len(lines) < 101:
        return False
    head = lines[0].lower()
    return ("date" in head) and sid.lower() in head


def parse_bp(txt: str) -> tuple[dict[str, int], int]:
    """Percent to integer basis points. A blank is not a zero."""
    out, blanks = {}, 0
    rd = csv.reader(io.StringIO(txt))
    next(rd)
    for row in rd:
        if len(row) < 2:
            continue
        d, v = row[0].strip(), row[1].strip()
        if v in ("", "."):
            blanks += 1
            continue
        try:
            out[d] = int(round(float(v) * 100))
        except ValueError:
            blanks += 1
    return out, blanks


def q(a: list[int], p: float) -> int:
    return a[min(len(a) - 1, int(p * (len(a) - 1)))]


def arm(admin: dict[str, int], effr: dict[str, int],
        lo: str | None, hi: str | None) -> dict:
    gaps, per_year, within_year = [], {}, {}
    above = below = within = 0
    for d, v in admin.items():
        if lo and d < lo:
            continue
        if hi and d > hi:
            continue
        if d not in effr:
            continue
        x = v - effr[d]
        gaps.append(x)
        y = d[:4]
        o = per_year.setdefault(y, {"n": 0, "min": 10**9, "max": -10**9})
        o["n"] += 1
        o["min"] = min(o["min"], x)
        o["max"] = max(o["max"], x)
        if abs(x) <= FLOOR_BP:
            within += 1
            within_year[y] = within_year.get(y, 0) + 1
        elif x > FLOOR_BP:
            above += 1
        else:
            below += 1
    gaps.sort()
    return {"n": len(gaps), "min": gaps[0], "q1": q(gaps, .25), "median": q(gaps, .5),
            "q3": q(gaps, .75), "max": gaps[-1], "distinct": len(set(gaps)),
            "above_floor": above, "below_floor": below, "within_floor": within,
            "within_floor_by_year": within_year, "by_year": per_year}


def main() -> int:
    print("B59: the class line on reserve balances\n")
    raw = {}
    for sid in SERIES:
        txt = fetch(sid)
        if txt is None:
            print("\nstops: a series is missing. Nothing written.")
            return 1
        raw[sid] = txt

    series, blanks = {}, {}
    for sid, txt in raw.items():
        series[sid], blanks[sid] = parse_bp(txt)
        ks = sorted(series[sid])
        print(f"  {sid:5s} {len(ks):5d} values  {ks[0]} to {ks[-1]}  "
              f"blank rows skipped {blanks[sid]}")

    iorb = arm(series["IORB"], series["EFFR"], BREAK, None)
    ioer = arm(series["IOER"], series["EFFR"], "2008-10-09", "2021-07-28")

    crit: dict[str, dict] = {}

    # B59-2. The station's strongest reading, and it comes from rules rather
    # than from these series, so it is stated here rather than computed. It sat
    # only in prose until 2026-09-08; a record that omits the finding is an
    # arrears whatever else it carries (18a).
    #
    # Grid D2 (7.5, ruled 2026-09-08): the rival is not wrong here, it has
    # nowhere to put the question. "What terms does the same asset carry for a
    # different holder" falls inside the domain any price theory claims for
    # itself, and a one-index object has no slot for it. That is a win and is
    # not to be recorded as undecidable.
    crit["B59-2"] = {
        "kind": "own_reading", "passed": True, "grid": "D2",
        "name": "on one position, a balance at a Federal Reserve Bank, two "
                "holder classes carry two weights, and the rule says which",
        "detail": "eligible institution IORB, Federal Home Loan Bank zero. "
                  "12 CFR 204.2(y) is a closed list of four and an FHLB is not "
                  "on it; 204.2(m)(1)(iv) names FHLB members, not the Banks. "
                  "The Board names the ineligible: 'money market funds (MMFs) "
                  "and government-sponsored enterprises (GSEs)'. The New York "
                  "Fed states the consequence: funds left 'unremunerated in "
                  "their Federal Reserve accounts'. Same obligor, same "
                  "instrument, same continuous availability, no collateral "
                  "either way, no maturity either way",
        "sources": ["12 CFR 204.2(y) and (m)(1)",
                    "FEDS Notes 2018-03-01",
                    "Liberty Street Economics 2013-12"]}

    crit["B59-1"] = {
        "kind": "instrument", "passed": bool(iorb["n"] and ioer["n"]),
        "name": "both administered series parse, align to EFFR by date, and a "
                "blank cell is skipped rather than read as a zero",
        "detail": f"IORB era {iorb['n']} paired days, IOER era {ioer['n']}; "
                  f"blanks skipped IORB {blanks['IORB']}, IOER {blanks['IOER']}, "
                  f"EFFR {blanks['EFFR']}"}

    ioer_last = series["IOER"]["2021-07-28"]
    iorb_first = series["IORB"][BREAK]
    crit["B59-5"] = {
        "kind": "known_answer", "passed": ioer_last == iorb_first,
        "name": "the 2021 redefinition was a rename and not a rate change, so "
                "the two bases meet at one value across the break",
        "detail": f"IOER 2021-07-28 = {ioer_last} bp, IORB {BREAK} = "
                  f"{iorb_first} bp"}

    got = {"IORB": {"n": iorb["n"], "above": iorb["above_floor"],
                    "below": iorb["below_floor"], "within": iorb["within_floor"]},
           "IOER": {"n": ioer["n"], "above": ioer["above_floor"],
                    "below": ioer["below_floor"], "within": ioer["within_floor"]},
           "break": {"IOER_last_bp": ioer_last, "IORB_first_bp": iorb_first}}
    ok = got == EXPECTED
    crit["B59-6"] = {
        "kind": "known_answer", "passed": ok,
        "name": "the run reproduces the counts read in a browser on 2026-09-08, "
                "before this script could reach the endpoint",
        "detail": ("reproduced" if ok else f"MISMATCH got {got} expected {EXPECTED}")}

    # B59-4. Three states, and the mapping is printed rather than implied (11c).
    def verdict(a: dict) -> tuple[str, str]:
        if a["below_floor"] > 0 and a["above_floor"] == 0:
            return "floor_holds", "the administered rate is at or below EFFR throughout"
        if a["above_floor"] > 0 and a["below_floor"] == 0:
            return "floor_broken", "EFFR is below the administered rate on every readable day"
        if a["above_floor"] > 0 and a["below_floor"] > 0:
            return "both_signs", "the floor is broken on some readable days and holds on others"
        return "undetermined", "every day sits inside the resolution floor"

    # Four cells, and the mapping from cell to verdict is written out rather
    # than implied. Two of the four adjudicate. "both_signs" is a determinate
    # description and not a verdict, and "undetermined" is the resolution floor
    # swallowing the whole arm; neither may buy a pass or a fail (11c). Sending
    # both_signs to FAILED is what this file did on its first run, which is the
    # same shape 11c was written for two days earlier.
    CELL_TO_VERDICT = {"floor_broken": True, "floor_holds": False,
                       "both_signs": None, "undetermined": None}
    for nm, a in (("IORB", iorb), ("IOER", ioer)):
        v, why = verdict(a)
        readable = a["above_floor"] + a["below_floor"]
        held = a["below_floor"]
        crit[f"B59-4-{nm}"] = {
            "kind": "rival", "passed": CELL_TO_VERDICT[v], "verdict_cell": v,
            "cell_to_verdict": CELL_TO_VERDICT,
            # 11e. A rival hit is worth what the shape of its prediction makes
            # it worth. This one is a one-sided inequality, so the quantity has
            # to fall on one side or the other and a hit is cheap; a crossing is
            # dear. The number to report is therefore the proportion, not the
            # name of the cell.
            "grid": "B", "rival_premise": "interest on excess reserve balances puts a lower bound under the federal funds rate. Two original wordings, reported separately because they are not the same commitment (D31). The 2008 announcement hedges: 'Paying interest on excess balances should help to establish a lower bound on the federal funds rate.' The 2018 retrospective is firmer, calling it 'the lower bound on money market rates that interest on reserves was expected to create'. The only qualification attached in 2008 is that 'the formula for the interest rate on excess balances may be adjusted subsequently in light of experience and evolving market conditions'", "rival_entailment": "read against the firmer wording: if interest on reserves creates a lower bound then EFFR sits at or above the administered rate, so a day with EFFR below it is a day the bound is not there. Read against the 2008 wording this is stricter than what was staked: 'should help to establish' does not commit to the bound holding on any given day, so the per-day count below describes the data and does not refute that sentence. Both readings are printed and neither is folded into the other", "cite": "Board of Governors, FEDS Notes 2018-03-01: the ineligible participants are willing to make loans below the IOR rate, eroding the lower bound on money market rates that interest on reserves was expected to create", 
            "grid_note": "the rival predicts a floor, this framework predicts a "
                         "positive gap while the barrier binds, so the two "
                         "differ and one of them is wrong on each readable day. "
                         "Against the hedged 2008 wording the cell is weaker "
                         "than B, because that sentence stakes less than a "
                         "per-day inequality",
            "rival_shape": "one_sided_inequality",
            "rival_hit_is_worth": "little: the gap has to fall on one side of "
                                  "zero, so holding is not an achievement. A "
                                  "crossing is what carries weight",
            "rival_held_days": held, "readable_days": readable,
            "rival_held_share": (round(held / readable, 4) if readable else None),
            "name": "the Board's stated expectation that interest on reserves "
                    "would floor money market rates, read per day on this "
                    "definitional basis",
            "detail": f"{v}: {why}. above floor {a['above_floor']}, below floor "
                      f"{a['below_floor']}, inside the {FLOOR_BP} bp floor and "
                      f"therefore mapped to no verdict {a['within_floor']}",
            "cells": {"above_floor": a["above_floor"], "below_floor": a["below_floor"],
                      "within_floor_no_verdict": a["within_floor"]}}

    crit["B59-3-IORB"] = {"kind": "own_reading", "passed": True,
        "name": "the net gap printed, no line drawn on it", "detail": str(iorb)}
    crit["B59-3-IOER"] = {"kind": "own_reading", "passed": True,
        "name": "the net gap printed, no line drawn on it", "detail": str(ioer)}

    print()
    def lab(c):
        if c["passed"] is None:
            return "NO-VERDICT"
        return "PASS" if c["passed"] else "FAILED"
    for k, c in crit.items():
        print(f"  {k:12s} {c['kind']:12s} {lab(c):10s} {c['detail'][:96]}")
    print("\n  rival criteria, by the shape of what the rival staked (11e)")
    for k, c in crit.items():
        if c["kind"] != "rival":
            continue
        print(f"    {k:12s} {c['rival_shape']:22s} the rival's prediction held "
              f"on {c['rival_held_days']} of {c['readable_days']} readable days"
              f"  ({c['rival_held_share']:.1%})")
    print("\n  by kind (11d): a total across kinds would name nothing")
    for kind in ("instrument", "premise", "known_answer", "rival",
                 "own_reading", "bookkeeping"):
        g = [c for c in crit.values() if c["kind"] == kind]
        if not g:
            continue
        print(f"    {kind:12s} pass {sum(1 for c in g if c['passed'] is True)}"
              f"  fail {sum(1 for c in g if c['passed'] is False)}"
              f"  no verdict {sum(1 for c in g if c['passed'] is None)}")

    rec = {"stage": "B59",
           "config": {"break": BREAK, "floor_bp": FLOOR_BP,
                      "series": SERIES, "source": FRED},
           "criteria": crit, "IORB_era": iorb, "IOER_era": ioer,
           "note": "gross gap is a rule reading, not in this record: "
                   "12 CFR 204.2(y) is a closed list of four and an FHLB is "
                   "not on it, so its Federal Reserve balance is unremunerated"}
    p = os.path.join(RESULTS, "b59_reserve_class_rate.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"\nwrote {os.path.basename(p)}")
    failed = [k for k, c in crit.items() if c["passed"] is False]
    if failed:
        print("\n  FAILED[" + ",".join(crit[k]["kind"] for k in failed) + "]: "
              + ", ".join(failed))
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
