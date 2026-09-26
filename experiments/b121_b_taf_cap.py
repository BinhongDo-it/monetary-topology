"""B121 arm B: did any Term Auction Facility auction clear above the discount window's posted rate?

The TAF and the discount window are two edges from one lender to one set of borrowers against one
collateral pool: the TAF was open only to depository institutions eligible for primary credit, and it
took the collateral the window takes. The window posts a price, the primary credit rate, and lends at it
on demand to any such institution. So a single price at the position bounds the auction from above: no
eligible bank would pay more at auction than the rate it can borrow at, so the stop-out rate sits at or
below the primary credit rate. The framework reads the two edges as carrying their own prices, so the
bound can be crossed.

Every winner of one auction borrows at one rate (the stop-out), which the Board's loan file prints to
three decimals; the primary credit rate is FRED's DPCREDIT. The reading is a count and a list, with no
estimate in it. Which day's posted rate the auction is held against is a declared knob:

  settle    the loan date (the day the funds arrived)
  bid       the last business day at least three calendar days before it (auctions were held about
            three days before settlement; the loan file does not print the bid day)
  highest   the highest posted rate between those two days
  expected  the posted rate on the bid day plus max(0, three-month OIS minus the target rate) on that
            day, from the rival's own workbook (results/b121_a2_panel.json), to 2008-08-08 only
  realised  the posted rate averaged over the days of the loan's term

The last two exist because a window term loan is not the same instrument as a TAF loan: the Discount
Window site states that when the rate "is changed while an advance is still outstanding, the new rate
will apply on and after the effective date of the change", so a window loan floats and a TAF loan is
fixed for its term. Where rises were expected, a bank could pay above the day's posted rate to lock a
TAF rate. `expected` lifts the bound by the whole three-month expected rise, which for a 28-day loan is
more room than the rival needs; `realised` reads what the window in fact cost over the term.

    python experiments/b121_b_taf_cap.py
    python experiments/b121_b_taf_cap.py --selftest
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAF = ROOT / "data" / "raw" / "b121" / "taf.csv"
PCR = ROOT / "data" / "b59" / "DPCREDIT.csv"
OUT = ROOT / "results" / "b121_b_taf_cap.json"
PANEL = ROOT / "results" / "b121_a2_panel.json"
KNOBS = ("settle", "bid", "highest", "expected", "realised")
TICK = 0.001  # the loan file prints rates to three decimals, in percent


def auctions() -> list[dict]:
    rows = list(csv.reader(TAF.open(encoding="utf-8-sig")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip().lower() == "loan date")
    h = [c.strip() for c in rows[hi]]
    iD, iT, iR, iA = h.index("Loan date"), h.index("Term"), h.index("Interest rate"), h.index("Loan amount")
    a = collections.defaultdict(lambda: {"rates": set(), "loans": 0, "amount_mn": 0.0})
    for r in rows[hi + 1:]:
        if not r or not r[iD].strip():
            continue
        k = (dt.datetime.strptime(r[iD].strip(), "%b %d %Y").date().isoformat(), int(r[iT].strip()))
        a[k]["rates"].add(float(r[iR].strip()))
        a[k]["loans"] += 1
        a[k]["amount_mn"] += float(r[iA].replace(",", ""))
    return [{"settle": d, "term": t, "rates": sorted(v["rates"]), "loans": v["loans"],
             "amount_mn": round(v["amount_mn"], 1)} for (d, t), v in sorted(a.items())]


def posted() -> dict[str, float]:
    return {r[0]: float(r[1]) for r in list(csv.reader(PCR.open(encoding="utf-8")))[1:]
            if len(r) > 1 and r[1] not in ("", ".")}


def rate_on(pcr: dict, day: str) -> tuple[str, float] | None:
    """The posted rate on that day, or on the last business day before it."""
    d = dt.date.fromisoformat(day)
    for k in range(0, 8):
        s = (d - dt.timedelta(days=k)).isoformat()
        if s in pcr:
            return s, pcr[s]
    return None


def expected_rise() -> dict[str, float]:
    """max(0, three-month OIS minus target) on each day of the rival's workbook."""
    rows = json.loads(PANEL.read_text(encoding="utf-8"))["panel"]
    return {r["date"]: max(0.0, r["ois3m"] - r["fft"]) for r in rows
            if r["ois3m"] is not None and r["fft"] is not None}


def against(a: dict, pcr: dict, knob: str, rise: dict | None = None) -> dict | None:
    settle = rate_on(pcr, a["settle"])
    bid = rate_on(pcr, (dt.date.fromisoformat(a["settle"]) - dt.timedelta(days=3)).isoformat())
    if knob == "settle":
        day, cap = settle
    elif knob == "bid":
        day, cap = bid
    elif knob == "highest":
        lo, hi = bid[0], a["settle"]
        cap = max(v for k, v in pcr.items() if lo <= k <= hi)
        day = f"{lo}..{hi}"
    elif knob == "expected":
        on = rate_on(rise or {}, bid[0]) if rise else None
        if on is None or on[0] < (dt.date.fromisoformat(bid[0]) - dt.timedelta(days=7)).isoformat():
            return None  # past the end of the rival's workbook, this bound cannot be written
        day, cap = f"{bid[0]} (+{on[1] * 100:.1f} bp expected)", bid[1] + on[1]
    else:
        start = dt.date.fromisoformat(a["settle"])
        days = [rate_on(pcr, (start + dt.timedelta(days=k)).isoformat()) for k in range(a["term"])]
        cap = sum(d[1] for d in days if d) / sum(1 for d in days if d)
        day = f"{a['settle']}+{a['term']}d"
    stop = a["rates"][0]
    return {"settle": a["settle"], "term": a["term"], "stop_out": stop, "posted_day": day, "posted": cap,
            "margin_bp": round((stop - cap) * 100, 1), "loans": a["loans"], "amount_mn": a["amount_mn"]}


def build_criteria(auc: list[dict], by_knob: dict[str, list[dict]]) -> dict:
    c = {}
    one_rate = all(len(a["rates"]) == 1 for a in auc)
    have = all(len(v) == len(auc) for k, v in by_knob.items() if k != "expected")
    c["B121-24"] = {
        "kind": "instrument",
        "statement": "the loan file groups into auctions with one rate each, and every auction has a posted "
                     "rate under every knob",
        "passed": bool(one_rate and have and len(auc) >= 40),
        "detail": f"{len(auc)} auctions, one rate each: {one_rate}; posted rate found under every knob: {have}",
    }
    above = {k: [r for r in v if r and r["stop_out"] - r["posted"] > TICK / 2] for k, v in by_knob.items()}
    counts = {k: len(v) for k, v in above.items()}
    # Three states, each mapped once (11c): above the bound under every knob, under none, or a knob decides.
    if all(n > 0 for n in counts.values()):
        state, verdict, grid = "above the posted rate under every knob", True, "B"
    elif all(n == 0 for n in counts.values()):
        state, verdict, grid = "at or below the posted rate under every knob", False, "C"
    else:
        state, verdict, grid = "a knob decides", None, "unread"
    c["B121-25"] = {
        "kind": "rival",
        "statement": "at least one auction cleared above the discount window's posted rate for the same "
                     "institutions against the same collateral",
        "passed": verdict, "state": state, "grid": grid,
        "state_map": {"above the posted rate under every knob": "pass, grid B",
                      "at or below the posted rate under every knob": "fail, grid C",
                      "a knob decides": "no verdict, grid unread"},
        "detail": "auctions above the posted rate: " + ", ".join(f"{k} {n}" for k, n in counts.items())
                  + "; under the settle knob: "
                  + ", ".join(f"{r['settle']} ({r['term']}d) {r['stop_out']:.3f} vs {r['posted']:.2f}, +{r['margin_bp']} bp"
                              for r in above.get("settle", [])),
        "rival_shape": "one-sided bound",
        "rival_premise": "one price at the position: an institution eligible for primary credit borrows at "
                         "the posted rate on demand against its discount window collateral",
        "rival_entailment": "no eligible bank bids above the rate it can borrow at, so every stop-out rate is "
                            "at or below the primary credit rate",
    }
    return c


def selftest(auc, pcr) -> int:
    bad = 0
    real = {k: [against(a, pcr, k) for a in auc] for k in ("settle", "bid", "highest", "realised")}
    lowered = {k: [dict(r, stop_out=r["posted"] - 0.1) for r in v] for k, v in real.items()}
    cr = build_criteria(auc, lowered)["B121-25"]
    if cr["passed"] is not False or cr["grid"] != "C":
        print("  B121-25 did not fail when every auction sat below the posted rate"); bad += 1
    split = dict(lowered, settle=[dict(lowered["settle"][0], stop_out=lowered["settle"][0]["posted"] + 0.5)]
                 + lowered["settle"][1:])
    cr = build_criteria(auc, split)["B121-25"]
    if cr["passed"] is not None or cr["grid"] != "unread":
        print("  B121-25 gave a verdict when one knob alone put an auction above"); bad += 1
    at_tick = {k: [dict(r, stop_out=r["posted"]) for r in v] for k, v in real.items()}
    if build_criteria(auc, at_tick)["B121-25"]["passed"] is not False:
        print("  B121-25 counted an auction at exactly the posted rate as above it"); bad += 1
    if build_criteria(auc[:5], real)["B121-24"]["passed"]:
        print("  B121-24 did not fail when the auctions and the readings did not line up"); bad += 1
    two = [dict(auc[0], rates=[1.0, 2.0])] + auc[1:]
    if build_criteria(two, real)["B121-24"]["passed"]:
        print("  B121-24 did not fail on an auction with two rates"); bad += 1
    print("selftest: every criterion failed on its planted input" if not bad
          else f"selftest: {bad} checks did not behave")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    auc, pcr = auctions(), posted()
    if args.selftest:
        return 1 if selftest(auc, pcr) else 0
    rise = expected_rise()
    by_knob = {k: [r for r in (against(a, pcr, k, rise) for a in auc) if r] for k in KNOBS}
    print(f"{len(auc)} auctions, {auc[0]['settle']} to {auc[-1]['settle']}")
    exp = {r["settle"] + str(r["term"]): r for r in by_knob["expected"]}
    rea = {r["settle"] + str(r["term"]): r for r in by_knob["realised"]}
    print("settle      term  stop-out   margin over: settle   bid  expected  realised")
    for s, b in zip(by_knob["settle"], by_knob["bid"]):
        k = s["settle"] + str(s["term"])
        e = f"{exp[k]['margin_bp']:+8.1f}" if k in exp else "     n/a"
        flag = "  <-- above" if s["margin_bp"] > 0 else ""
        print(f"{s['settle']}  {s['term']:>3}  {s['stop_out']:7.3f}   {s['margin_bp']:+18.1f} {b['margin_bp']:+6.1f}"
              f"  {e}  {rea[k]['margin_bp']:+8.1f}{flag}")
    criteria = build_criteria(auc, by_knob)
    print()
    for n, cr in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[cr["passed"]]
        print(f"{flag:<10} {n} [{cr['kind']}] {cr['detail']}")
    record = {"stage": "B121",
              "config": {"tick_percent": TICK, "knobs": list(KNOBS), "bid_offset_days": 3,
                         "expected_rise": "max(0, USSOC - FFT) on the bid day, rival's workbook, to 2008-08-08"},
              "source": {"auctions": "Board of Governors, TAF transaction data, taf.csv",
                         "posted": "FRED DPCREDIT (data/b59/DPCREDIT.csv)"},
              "readings": by_knob,
              "criteria": [dict(v, name=k) for k, v in criteria.items()],
              "diagnostic_only": True,
              "diagnostic_reason": "Arm B of B121; the station has other arms open."}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(v["passed"] is not False for v in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
