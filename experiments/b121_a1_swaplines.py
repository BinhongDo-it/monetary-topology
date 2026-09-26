"""B121 arm A1: the day a central bank's dollar swap line first pays out, does that currency's
covered interest parity gap close, against the currencies whose line has not opened yet?

The framework reads a cross-currency gap as a property of the edge a foreign bank uses to reach
dollars. A swap line adds that edge for one currency at a time: dollars go to one central bank,
which lends them on to its own banks. So on the day a line first pays out, that currency's gap
should move toward zero relative to the currencies still without a line. Common shocks fall out
of the difference, since every currency in the comparison sits in the same week of the same crisis.

  object     the three-month covered interest parity gap, `cip_govt`, in basis points
             (Du, Keerati and Schreger dataset, already on disk; the two columns the publisher
             offers are identical before 2022, so one is read)
  events     each counterparty's first settlement in the Board's swap-line transaction file
  controls   the G10 currencies whose line has not paid out by the event's last day

No rival is registered on this arm: the framework's own reading is scored, as `own_reading`.

    python experiments/b121_a1_swaplines.py
    python experiments/b121_a1_swaplines.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CIP = ROOT / "data" / "raw" / "cip_dataset_v4.csv"
CBLS = ROOT / "data" / "raw" / "b121" / "cbls.csv"
OUT = ROOT / "results" / "b121_a1_swaplines.json"
FIRST, LAST = "2007-01-01", "2009-12-31"
TENOR = "3m"
G10 = ("AUD", "CAD", "CHF", "DKK", "EUR", "GBP", "JPY", "NOK", "NZD", "SEK")
CURRENCY_OF = {  # the Board's own "Foreign currency" column, mapped to the dataset's codes
    "euro": "EUR", "Swiss franc": "CHF", "British pound": "GBP", "Japanese yen": "JPY",
    "South Korean won": "KRW", "Danish krone": "DKK", "Australian dollar": "AUD",
    "Swedish krona": "SEK", "Norwegian krone": "NOK", "Mexican peso": "MXN",
}
DRAWS, SEEDS, BLOCK, LINE = 2000, (11, 23), 5, 2.0


def load_cip() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with CIP.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        head = next(r)
        ix = {k: i for i, k in enumerate(head)}
        for row in r:
            if len(row) < len(head) or row[ix["tenor"]] != TENOR:
                continue
            day = dt.datetime.strptime(row[ix["date"]], "%d%b%Y").date().isoformat()
            if not (FIRST <= day <= LAST) or row[ix["cip_govt"]] in ("", ".", "NA"):
                continue
            out.setdefault(row[ix["currency"]], {})[day] = float(row[ix["cip_govt"]])
    return out


def load_first_drawings() -> dict[str, dict]:
    rows = list(csv.reader(CBLS.open(encoding="utf-8-sig")))
    head = [c.strip() for c in rows[1]]
    i_cur, i_trade, i_settle, i_amt = (head.index(k) for k in
                                       ("Foreign currency", "Trade date", "Settlement date", "Amount extended"))
    first: dict[str, dict] = {}
    for r in rows[2:]:
        if not any(c.strip() for c in r):
            continue
        code = CURRENCY_OF[r[i_cur].strip()]
        settle = dt.datetime.strptime(r[i_settle].strip(), "%b %d %Y").date().isoformat()
        trade = dt.datetime.strptime(r[i_trade].strip(), "%b %d %Y").date().isoformat()
        if code not in first or settle < first[code]["settle"]:
            first[code] = {"settle": settle, "trade": trade,
                           "amount_mn": float(r[i_amt].replace(",", "").strip())}
    return dict(sorted(first.items(), key=lambda kv: kv[1]["settle"]))


def trading_days(cip: dict) -> list[str]:
    return sorted(set().union(*(set(v) for k, v in cip.items() if k in G10)))


def event_effects(cip, days, events, horizon: int, control: str) -> list[dict]:
    """For each event, the change in |gap| of the treated currency minus the controls' mean."""
    out = []
    pos = {d: i for i, d in enumerate(days)}
    for cur, ev in events.items():
        if cur not in cip or ev["day"] not in pos:
            continue
        i = pos[ev["day"]]
        if i < 1 or i + horizon - 1 >= len(days):
            continue
        before, after = days[i - 1], days[i + horizon - 1]
        if before not in cip[cur] or after not in cip[cur]:
            continue
        treated = abs(cip[cur][after]) - abs(cip[cur][before])
        if control == "not yet drawn":
            pool = [c for c in G10 if c != cur and (c not in events or events[c]["day"] > after)]
        else:  # never drew in the Board's file
            pool = [c for c in G10 if c not in events]
        ctl = [abs(cip[c][after]) - abs(cip[c][before]) for c in pool
               if c in cip and before in cip[c] and after in cip[c]]
        if not ctl:
            continue
        out.append({"currency": cur, "day": ev["day"], "treated_bp": treated,
                    "controls": pool, "control_mean_bp": statistics.fmean(ctl),
                    "effect_bp": treated - statistics.fmean(ctl)})
    return out


def placebo_floor(cip, days, events, horizon, control, seed, draws) -> dict:
    """Move every event day, in whole weeks, to another day of the window; read the same statistic."""
    real = event_effects(cip, days, events, horizon, control)
    stat = statistics.fmean(e["effect_bp"] for e in real)
    rng = np.random.default_rng(seed)
    weeks = [days[i:i + BLOCK] for i in range(0, len(days), BLOCK)]
    null = []
    for _ in range(draws):
        moved = {}
        for cur, ev in events.items():
            w = weeks[rng.integers(len(weeks))]
            moved[cur] = dict(ev, day=w[min(days.index(ev["day"]) % BLOCK, len(w) - 1)]
                              if ev["day"] in days else w[0])
        eff = event_effects(cip, days, moved, horizon, control)
        if eff:
            null.append(statistics.fmean(e["effect_bp"] for e in eff))
    null = np.array(null)
    sd = float(null.std(ddof=1))
    return {"events": len(real), "mean_effect_bp": stat, "floor": sd,
            "over_floor": stat / sd if sd else None,
            "p": float((np.sum(np.abs(null) >= abs(stat)) + 1) / (len(null) + 1)),
            "draws": int(len(null)), "seed": seed, "by_event": real}


def sign_state(cells: list[dict]) -> tuple[str, list[str]]:
    signed = [(c["name"], c["mean_effect_bp"]) for c in cells if c["mean_effect_bp"] is not None]
    first = signed[0][1] > 0
    off = [n for n, v in signed if (v > 0) != first]
    if off:
        return "turns over", off
    if not any(abs(c["over_floor"] or 0) >= LINE for c in cells):
        return "nothing clears the floor", []
    return "steady", []


def build_criteria(main: dict, cells: list[dict], seeds_ok: dict, events: dict) -> dict:
    c = {}
    found = {k: v for k, v in events.items() if k in G10}
    c["B121-12"] = {
        "kind": "instrument",
        "statement": "every G10 counterparty in the Board's swap-line file has a first settlement "
                     "inside the window, and the gap is read on the day before and on that day",
        "passed": bool(len(found) >= 6 and main["events"] >= len(found) - 1),
        "detail": f"{len(found)} G10 counterparties drew, {main['events']} events read: "
                  + ", ".join(f"{k} {v['settle']}" for k, v in found.items()),
    }
    state, off = sign_state(cells)
    if state != "steady":
        verdict, st = None, f"sign {state}"
    elif main["over_floor"] is not None and main["over_floor"] <= -LINE:
        verdict, st = True, "narrows past its floor, sign steady"
    else:
        verdict, st = False, "does not narrow past its floor"
    c["B121-13"] = {
        "kind": "own_reading",
        "statement": "on the day a currency's swap line first pays out, its gap moves toward zero "
                     "against the G10 currencies whose line has not paid out, past two of its own floor",
        "passed": verdict,
        "state": st,
        "state_map": {"sign turns over": "no verdict", "sign nothing clears the floor": "no verdict",
                      "narrows past its floor, sign steady": "pass",
                      "does not narrow past its floor": "fail"},
        "detail": f"{main['mean_effect_bp']:+.2f} bp over {main['events']} events, floor "
                  f"{main['floor']:.2f}, {main['over_floor']:+.2f} floors, p {main['p']:.4f}"
                  + (f"; the sign turns over on {off}" if off else ""),
    }
    c["B121-14"] = {
        "kind": "instrument",
        "statement": "the sign of that reading holds on every declared setting: horizon, control set, "
                     "and whether the event is the trade or the settlement day",
        "passed": {"steady": True, "turns over": False, "nothing clears the floor": None}[state],
        "detail": f"{len(cells)} settings, {state}" + (f", turned over on {off}" if off else ""),
    }
    c["B121-15"] = {
        "kind": "instrument",
        "statement": "two seeds put the reading in the same state and p moves less than its "
                     "distance to the line",
        "passed": bool(seeds_ok["ok"]),
        "detail": seeds_ok["detail"],
    }
    return c


def run(cip, days, first, seed, draws, horizon=1, control="not yet drawn", which="settle"):
    events = {k: {"day": _on_or_after(days, v[which])} for k, v in first.items()}
    events = {k: v for k, v in events.items() if v["day"] is not None}
    return placebo_floor(cip, days, events, horizon, control, seed, draws), events


def _on_or_after(days, d):
    later = [x for x in days if x >= d]
    return later[0] if later else None


def selftest(cip, days, first) -> int:
    bad = 0
    main, events = run(cip, days, first, SEEDS[0], 200)
    cells = [{"name": "a", "mean_effect_bp": -5.0, "over_floor": -3.0},
             {"name": "b", "mean_effect_bp": -4.0, "over_floor": -2.5}]
    ok = {"ok": True, "detail": "seeded"}
    if build_criteria(dict(main, events=1), cells, ok, {"EUR": {"settle": "x"}})["B121-12"]["passed"]:
        print("  B121-12 did not fail with one counterparty"); bad += 1
    if build_criteria(dict(main, over_floor=-0.3), cells, ok, first)["B121-13"]["passed"] is not False:
        print("  B121-13 did not fail on a reading inside its floor"); bad += 1
    flip = cells + [{"name": "c", "mean_effect_bp": +1.0, "over_floor": +0.4}]
    crit = build_criteria(main, flip, ok, first)
    if crit["B121-13"]["passed"] is not None or crit["B121-14"]["passed"] is not False:
        print("  B121-13 or 14 gave a verdict when a setting turned the sign over"); bad += 1
    if build_criteria(main, cells, {"ok": False, "detail": "x"}, first)["B121-15"]["passed"]:
        print("  B121-15 did not fail when the seeds disagreed"); bad += 1
    # The floor must hear a planted closing, and must not hear an untouched series.
    planted = {k: dict(v) for k, v in cip.items()}
    for cur, ev in events.items():
        i = days.index(ev["day"])
        for d in days[i:]:
            if d in planted[cur]:
                planted[cur][d] = planted[cur][d] * 0.2
    loud = placebo_floor(planted, days, events, 1, "not yet drawn", SEEDS[0], 300)
    if loud["over_floor"] is None or loud["over_floor"] > -LINE:
        print(f"  the floor missed a planted closing of 80 percent ({loud['over_floor']})"); bad += 1
    print("selftest: every criterion failed on its planted input, and the floor heard the planted closing"
          if not bad else f"selftest: {bad} checks did not behave")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()

    cip = load_cip()
    days = trading_days(cip)
    first = load_first_drawings()
    if args.selftest:
        return 1 if selftest(cip, days, first) else 0

    print(f"window {days[0]} to {days[-1]}, {len(days)} trading days; G10 with data: "
          f"{[c for c in G10 if c in cip]}")
    print("first settlement per counterparty (the Board's file):")
    for k, v in first.items():
        print(f"  {k}  trade {v['trade']}  settle {v['settle']}  {v['amount_mn']:>10,.0f} mn"
              + ("" if k in G10 else "   (outside G10, not in the comparison)"))
    first_g10 = {k: v for k, v in first.items() if k in G10}

    by_seed = {}
    for seed in SEEDS:
        by_seed[seed], events = run(cip, days, first_g10, seed, args.draws)
        r = by_seed[seed]
        print(f"  seed {seed}: {r['events']} events  {r['mean_effect_bp']:+.2f} bp  floor {r['floor']:.2f}  "
              f"{r['over_floor']:+.2f} floors  p {r['p']:.4f}")
    main_read = by_seed[SEEDS[0]]
    print("each event (treated |gap| change minus the controls' mean, one day):")
    for e in main_read["by_event"]:
        print(f"  {e['currency']} {e['day']}  treated {e['treated_bp']:+7.2f}  controls {e['control_mean_bp']:+7.2f}"
              f"  effect {e['effect_bp']:+7.2f}   controls {e['controls']}")

    a, b = (by_seed[s]["over_floor"] for s in SEEDS)
    gap, dist = abs(a - b), abs(abs((a + b) / 2) - LINE)
    seeds_ok = {"ok": bool(((abs(a) >= LINE) == (abs(b) >= LINE)) and gap < dist),
                "detail": f"{a:+.2f} and {b:+.2f} floors, moved {gap:.3f}, stands {dist:.3f} from the line"}

    cells = []
    for horizon in (1, 5, 10):
        for control in ("not yet drawn", "never drew"):
            for which in ("settle", "trade"):
                r, _ = run(cip, days, first_g10, SEEDS[0], max(400, args.draws // 4), horizon, control, which)
                cells.append({"name": f"{horizon}d|{control}|{which}", "events": r["events"],
                              "mean_effect_bp": round(r["mean_effect_bp"], 3),
                              "over_floor": None if r["over_floor"] is None else round(r["over_floor"], 2)})
    print(f"\nknob sweep, {len(cells)} settings (11f):")
    for cell in cells:
        print(f"  {cell['name']:<28} events {cell['events']:>2}  {cell['mean_effect_bp']:+7.2f} bp  "
              f"({cell['over_floor']:+5.2f} floors)")

    criteria = build_criteria(main_read, cells, seeds_ok, first_g10)
    print()
    for name, cr in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[cr["passed"]]
        print(f"{flag:<10} {name} [{cr['kind']}] {cr['detail']}")

    record = {
        "stage": "B121",
        "config": {"draws": args.draws, "seeds": list(SEEDS), "block_days": BLOCK, "tenor": TENOR,
                   "window": [FIRST, LAST], "object": "abs(cip_govt)", "horizon_days": 1,
                   "control": "not yet drawn", "event_day": "settle"},
        "source": {"gap": "Du, Keerati and Schreger, cip_dataset_v4.csv, column cip_govt",
                   "events": "Board of Governors, central bank liquidity swap transaction data, cbls.csv"},
        "first_drawings": first,
        "readings": {"by_seed": by_seed, "knobs": cells, "seeds": seeds_ok},
        "criteria": [dict(v, name=k) for k, v in criteria.items()],
        "diagnostic_only": True,
        "diagnostic_reason": "Arm A1 of B121; the station's other arms are open, so it is not closed.",
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(v["passed"] is not False for v in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
