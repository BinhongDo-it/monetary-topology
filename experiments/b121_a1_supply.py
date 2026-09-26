"""B121 arm A1, part two: the dose on the supply side, the days a swap line was set up or enlarged.

Part one read each currency's first drawing, and a drawing is requested by the foreign central bank
against its own banks' dollar shortfall, so it lands on that currency's tightest days. The edge this
framework speaks of is the line's existence and size, and those are set by announcements. Each
announcement below names the counterparties whose line it establishes or enlarges, read from the
Board's own release (data/raw/b121/press/). The control on each day is every G10 currency the release
does not touch.

The release of 2008-09-29 enlarged every line at once and leaves no control, so it is not read.

    python experiments/b121_a1_supply.py
    python experiments/b121_a1_supply.py --selftest
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b121_a1_supply.json"
_spec = importlib.util.spec_from_file_location("a1", ROOT / "experiments" / "b121_a1_swaplines.py")
a1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a1)
G10, BLOCK, LINE, SEEDS, DRAWS = a1.G10, a1.BLOCK, a1.LINE, a1.SEEDS, a1.DRAWS

RELEASES = {  # day: (currencies touched, what the Board's release says, release file)
    "2007-12-12": (("EUR", "CHF"), "swap lines established with the ECB ($20bn) and the SNB ($4bn)", "20071212a"),
    "2008-05-02": (("EUR", "CHF"), "ECB and SNB lines raised to $50bn and $12bn", "20080502a"),
    "2008-07-30": (("EUR",), "ECB line raised from $50bn to $55bn", "20080730a"),
    "2008-09-18": (("EUR", "CHF", "JPY", "GBP", "CAD"),
                   "ECB and SNB lines raised; new lines with the BoJ ($60bn), BoE ($40bn), BoC ($10bn)", "20080918a"),
    "2008-09-24": (("AUD", "SEK", "DKK", "NOK"),
                   "new lines with the RBA and Riksbank ($10bn each), Danmarks Nationalbank and Norges Bank ($5bn each)",
                   "20080924a"),
    "2008-10-13": (("GBP", "EUR", "CHF"), "BoE, ECB and SNB lines sized to accommodate full allotment", "20081013a"),
    "2008-10-14": (("JPY",), "the BoJ line increased (title on the Board's release list)", "20081014a"),
}


def effects(cip, days, releases, horizon):
    pos = {d: i for i, d in enumerate(days)}
    out = []
    for day, (touched, _, _) in releases.items():
        d = next((x for x in days if x >= day), None)
        if d is None:
            continue
        i = pos[d]
        if i < 1 or i + horizon - 1 >= len(days):
            continue
        before, after = days[i - 1], days[i + horizon - 1]
        pool = [c for c in G10 if c not in touched and c in cip and before in cip[c] and after in cip[c]]
        if not pool:
            continue
        ctl = statistics.fmean(abs(cip[c][after]) - abs(cip[c][before]) for c in pool)
        for cur in touched:
            if cur in cip and before in cip[cur] and after in cip[cur]:
                t = abs(cip[cur][after]) - abs(cip[cur][before])
                out.append({"release": day, "currency": cur, "treated_bp": t, "control_mean_bp": ctl,
                            "effect_bp": t - ctl, "controls": pool})
    return out


def floor(cip, days, releases, horizon, seed, draws):
    real = effects(cip, days, releases, horizon)
    stat = statistics.fmean(e["effect_bp"] for e in real)
    rng = np.random.default_rng(seed)
    weeks = [days[i:i + BLOCK] for i in range(0, len(days), BLOCK)]
    null = []
    for _ in range(draws):
        moved = {}
        for day, v in releases.items():
            w = weeks[rng.integers(len(weeks))]
            moved[w[rng.integers(len(w))]] = v
        eff = effects(cip, days, moved, horizon)
        if eff:
            null.append(statistics.fmean(e["effect_bp"] for e in eff))
    null = np.array(null)
    sd = float(null.std(ddof=1))
    return {"events": len(real), "mean_effect_bp": stat, "floor": sd,
            "over_floor": stat / sd if sd else None,
            "p": float((np.sum(np.abs(null) >= abs(stat)) + 1) / (len(null) + 1)),
            "draws": int(len(null)), "seed": seed, "by_event": real}


def build_criteria(main, cells, seeds_ok):
    c = {}
    c["B121-16"] = {
        "kind": "instrument",
        "statement": "every release is read from the Board's own text and every touched currency is read "
                     "against at least one untouched G10 currency",
        "passed": bool(main["events"] >= 10 and all(e["controls"] for e in main["by_event"])),
        "detail": f"{len(RELEASES)} releases, {main['events']} currency-events",
    }
    state, off = a1.sign_state(cells)
    if state != "steady":
        verdict, st = None, f"sign {state}"
    elif main["over_floor"] is not None and main["over_floor"] <= -LINE:
        verdict, st = True, "narrows past its floor, sign steady"
    else:
        verdict, st = False, "does not narrow past its floor"
    c["B121-17"] = {
        "kind": "own_reading",
        "statement": "on the day a release sets up or enlarges a currency's swap line, that currency's gap "
                     "moves toward zero against the G10 currencies the release does not touch, past two of "
                     "its own floor",
        "passed": verdict, "state": st,
        "state_map": {"sign turns over": "no verdict", "sign nothing clears the floor": "no verdict",
                      "narrows past its floor, sign steady": "pass",
                      "does not narrow past its floor": "fail"},
        "detail": f"{main['mean_effect_bp']:+.2f} bp over {main['events']} currency-events, floor "
                  f"{main['floor']:.2f}, {main['over_floor']:+.2f} floors, p {main['p']:.4f}"
                  + (f"; the sign turns over on {off}" if off else ""),
    }
    c["B121-18"] = {
        "kind": "instrument",
        "statement": "the sign holds on every declared horizon",
        "passed": {"steady": True, "turns over": False, "nothing clears the floor": None}[state],
        "detail": f"{len(cells)} settings, {state}" + (f", turned over on {off}" if off else ""),
    }
    c["B121-19"] = {
        "kind": "instrument",
        "statement": "two seeds leave the reading in one state and p moves less than its distance to the line",
        "passed": bool(seeds_ok["ok"]), "detail": seeds_ok["detail"],
    }
    return c


def selftest(cip, days) -> int:
    bad = 0
    main = floor(cip, days, RELEASES, 1, SEEDS[0], 200)
    cells = [{"name": "a", "mean_effect_bp": -5.0, "over_floor": -3.0}]
    ok = {"ok": True, "detail": "seeded"}
    if build_criteria(dict(main, events=3), cells, ok)["B121-16"]["passed"]:
        print("  B121-16 did not fail on three events"); bad += 1
    if build_criteria(dict(main, over_floor=-0.2), cells, ok)["B121-17"]["passed"] is not False:
        print("  B121-17 did not fail inside its floor"); bad += 1
    flip = cells + [{"name": "b", "mean_effect_bp": +0.5, "over_floor": +0.2}]
    cr = build_criteria(main, flip, ok)
    if cr["B121-17"]["passed"] is not None or cr["B121-18"]["passed"] is not False:
        print("  B121-17 or 18 gave a verdict when the sign turned over"); bad += 1
    if build_criteria(main, cells, {"ok": False, "detail": "x"})["B121-19"]["passed"]:
        print("  B121-19 did not fail when seeds disagreed"); bad += 1
    planted = {k: dict(v) for k, v in cip.items()}
    for day, (touched, _, _) in RELEASES.items():
        d = next(x for x in days if x >= day)
        for cur in touched:
            for x in days[days.index(d):]:
                if x in planted.get(cur, {}):
                    planted[cur][x] *= 0.7
    loud = floor(planted, days, RELEASES, 1, SEEDS[0], 300)
    if loud["over_floor"] is None or loud["over_floor"] > -LINE:
        print(f"  the floor missed a planted closing ({loud['over_floor']})"); bad += 1
    print("selftest: every criterion failed on its planted input, and the floor heard the planted closing"
          if not bad else f"selftest: {bad} checks did not behave")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()
    cip = a1.load_cip()
    days = a1.trading_days(cip)
    if args.selftest:
        return 1 if selftest(cip, days) else 0

    by_seed = {s: floor(cip, days, RELEASES, 1, s, args.draws) for s in SEEDS}
    for s, r in by_seed.items():
        print(f"seed {s}: {r['events']} currency-events  {r['mean_effect_bp']:+.2f} bp  floor {r['floor']:.2f}  "
              f"{r['over_floor']:+.2f} floors  p {r['p']:.4f}")
    main_read = by_seed[SEEDS[0]]
    print("each currency-event, one day (treated |gap| change minus the untouched G10 mean):")
    for e in main_read["by_event"]:
        print(f"  {e['release']} {e['currency']}  treated {e['treated_bp']:+7.2f}  control {e['control_mean_bp']:+7.2f}"
              f"  effect {e['effect_bp']:+7.2f}")
    a, b = (by_seed[s]["over_floor"] for s in SEEDS)
    gap, dist = abs(a - b), abs(abs((a + b) / 2) - LINE)
    seeds_ok = {"ok": bool(((abs(a) >= LINE) == (abs(b) >= LINE)) and gap < dist),
                "detail": f"{a:+.2f} and {b:+.2f} floors, moved {gap:.3f}, stands {dist:.3f} from the line"}
    cells = []
    for h in (1, 2, 5, 10):
        r = floor(cip, days, RELEASES, h, SEEDS[0], max(400, args.draws // 4))
        cells.append({"name": f"{h}d", "events": r["events"], "mean_effect_bp": round(r["mean_effect_bp"], 3),
                      "over_floor": None if r["over_floor"] is None else round(r["over_floor"], 2)})
        print(f"  horizon {h:>2}d  {r['mean_effect_bp']:+7.2f} bp  ({r['over_floor']:+5.2f} floors)")
    criteria = build_criteria(main_read, cells, seeds_ok)
    print()
    for n, cr in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[cr["passed"]]
        print(f"{flag:<10} {n} [{cr['kind']}] {cr['detail']}")
    record = {
        "stage": "B121",
        "config": {"draws": args.draws, "seeds": list(SEEDS), "block_days": BLOCK, "horizon_days": 1,
                   "object": "abs(cip_govt), 3m", "control": "G10 currencies the release does not touch"},
        "source": {"gap": "Du, Keerati and Schreger, cip_dataset_v4.csv",
                   "releases": {d: {"currencies": list(v[0]), "text": v[1], "file": f"data/raw/b121/press/{v[2]}.html"}
                                for d, v in RELEASES.items()}},
        "readings": {"by_seed": by_seed, "horizons": cells, "seeds": seeds_ok},
        "criteria": [dict(v, name=k) for k, v in criteria.items()],
        "diagnostic_only": True,
        "diagnostic_reason": "Arm A1 of B121, supply side; the station has other arms open.",
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(v["passed"] is not False for v in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
