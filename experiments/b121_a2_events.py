"""B121 arm A2, part three: read the doses as event days, not as levels that share a term.

Part two regressed the daily change in LIBOR minus OIS on the change in the TAF balance, and
the sign of that coefficient turned over when the spread's timing changed. The cause is the
twelfth entry of the category-error family in reverse: the object is a difference that carries
OIS inside it, and the TAF balance moves with OIS, so which OIS day enters the object decides
how much of OIS is left in the regressor. That cell is not read (11f), and it stays unread.

Here each dose is a day, named by the rival's own workbook:

  rate days        the target federal funds rate changed
  TAF announce     TAFANNOUNCEFRBNY, the facility was announced or enlarged
  TAF bid          USTAFD, an auction took bids
  TAF settle       TAFSETTLE, an auction settled and the funds arrived

A day carries no OIS variance, so the reading no longer runs through the shared term. The floor
for each set is the same statistic with the event days moved, in whole weeks, so the object's own
lumpiness survives and only the timing of the events is destroyed.

    python experiments/b121_a2_events.py
    python experiments/b121_a2_events.py --selftest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "results" / "b121_a2_panel.json"
OUT = ROOT / "results" / "b121_a2_events.json"

DRAWS = 2000
SEEDS = (11, 23)
BLOCK = 5
LINE = 2.0        # a reading is read when it stands this many of its own floors from zero

EVENTS = {
    "rate_change": "the target federal funds rate changed that day",
    "taf_announce": "TAFANNOUNCEFRBNY, the workbook's own announcement day",
    "taf_bid": "USTAFD, the workbook's own auction bid day",
    "taf_settle": "TAFSETTLE, the workbook's own settlement day",
}


def changes(rows, spread_key: str, start: str, horizon: int):
    """The object over `horizon` trading days, and which days each event set marks."""
    keep = [r for r in rows if r["date"] >= start and r[spread_key] is not None]
    obj, mark = [], {k: [] for k in EVENTS}
    for i in range(horizon, len(keep)):
        cur, prev = keep[i], keep[i - horizon]
        obj.append((cur[spread_key] - prev[spread_key]) * 100.0)
        window = keep[i - horizon + 1:i + 1]
        mark["rate_change"].append(any(
            w["fft"] is not None and p["fft"] is not None and abs(w["fft"] - p["fft"]) > 1e-9
            for p, w in zip(keep[i - horizon:i], window)))
        for key, col in (("taf_announce", "taf_announce_day"), ("taf_bid", "taf_bid_day"),
                         ("taf_settle", "taf_settle_day")):
            mark[key].append(any(w[col] for w in window))
    return np.array(obj), {k: np.array(v) for k, v in mark.items()}, [r["date"] for r in keep]


def block_shift(flags: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Move the event days by shuffling whole weeks of the flag, keeping how many there are."""
    chunks = [flags[i:i + BLOCK] for i in range(0, len(flags), BLOCK)]
    order = rng.permutation(len(chunks))
    return np.concatenate([chunks[i] for i in order])[:len(flags)]


def read_event(obj: np.ndarray, flags: np.ndarray, seed: int, draws: int) -> dict:
    """Mean of the object on the marked days, against a floor built by moving those days."""
    n = int(flags.sum())
    if n == 0 or n == len(flags):
        return {"days": n, "mean_bp": None, "floor": None, "over_floor": None, "p": None}
    real = float(obj[flags].mean() - obj[~flags].mean())
    rng = np.random.default_rng(seed)
    null = np.empty(draws)
    for i in range(draws):
        f = block_shift(flags, rng)
        null[i] = obj[f].mean() - obj[~f].mean() if 0 < f.sum() < len(f) else np.nan
    null = null[~np.isnan(null)]
    sd = float(null.std(ddof=1))
    return {"days": n, "mean_bp": real, "floor": sd,
            "over_floor": real / sd if sd else None,
            "p": float((np.sum(np.abs(null) >= abs(real)) + 1) / (len(null) + 1)),
            "null_median": float(np.median(null)), "draws": int(len(null)), "seed": seed}


def best_of_three(obj: np.ndarray, mark: dict, seed: int, draws: int) -> dict:
    """Three facility sets are looked at, so the floor takes the best of three inside every draw.

    Reading the best of three against one set's own floor hands back part of the choice. Under
    the null the same choice is made in each draw, so the correction costs one pass."""
    keys = ("taf_announce", "taf_bid", "taf_settle")
    real = {k: float(obj[mark[k]].mean() - obj[~mark[k]].mean()) for k in keys}
    pick = min(real, key=real.get)
    rng = np.random.default_rng(seed)
    worst = np.empty(draws)
    for i in range(draws):
        vals = []
        for k in keys:
            f = block_shift(mark[k], rng)
            if 0 < f.sum() < len(f):
                vals.append(obj[f].mean() - obj[~f].mean())
        worst[i] = min(vals) if vals else np.nan
    worst = worst[~np.isnan(worst)]
    return {"picked": pick, "picked_bp": real[pick],
            "p_best_of_three": float((np.sum(worst <= real[pick]) + 1) / (len(worst) + 1)),
            "floor_best_of_three": float(worst.std(ddof=1)),
            "draws": int(len(worst)), "seed": seed, "all_three_bp": real}


EXTENSION = ROOT / "results" / "b121_a2_extension_panel.json"


def announcement_lists(rows) -> dict[str, set[str]]:
    """Which days count as announcements is a knob, so every list this station holds is swept.

    The rival's workbook codes its own announcement column by content, +1 and on one day -1,
    and leaves the releases that only repeat an existing amount unmarked. The Board's TAF page
    lists every release. The first run of this script read the workbook's +1 days only, and
    its reading does not survive the Board's list, so the list is declared here as a knob."""
    lists = {"workbook +1": {r["date"] for r in rows if r["taf_announce_day"]}}
    if EXTENSION.exists():
        ann = json.loads(EXTENSION.read_text(encoding="utf-8"))["announcements"]
        board = {a["date"] for a in ann if a["kind"] == "expansion or schedule"
                 and a["date"] <= rows[-1]["date"]}
        lists["Board page"] = board
        lists["union"] = lists["workbook +1"] | board
    lists["capacity change"] = set(CAPACITY_CHANGE)
    return lists


# The releases whose own text raises the amount offered or adds an instrument or a tenor, read one
# by one from the Board's press releases (data/raw/b121/press/). The rule was written down before
# the texts were read, and after the reading in the station's results R7, which is stated there.
CAPACITY_CHANGE = {
    "2007-12-12": "establishes the TAF, $20 billion per auction; establishes swap lines with the ECB and SNB",
    "2008-01-04": "$30 billion per auction, up from $20 billion in December",
    "2008-03-07": "auctions increased to $50 billion each, amounts outstanding to $100 billion",
    "2008-05-02": "auctions from $50 billion to $75 billion; ECB and SNB swap lines raised",
    "2008-07-30": "introduces 84-day TAF loans; ECB swap line from $50 billion to $55 billion",
}
UNCHANGED = {
    "2007-12-21": "continue TAF auctions as necessary, no amount",
    "2008-02-01": "$30 billion per auction, as before",
    "2008-02-29": "$30 billion per auction, as before",
    "2008-03-28": "$50 billion per auction, as set on March 7",
    "2008-05-29": "$75 billion per auction, as set on May 2",
    "2008-07-01": "$75 billion per auction, as before",
}


def relabel(rows, days: set[str]) -> list[dict]:
    return [dict(r, taf_announce_day=r["date"] in days) for r in rows]


def sweep(rows, seed: int, draws: int) -> list[dict]:
    """Every setting this station has declared: the object's timing, the window, the horizon,
    and which list of days counts as an announcement."""
    out = []
    for list_name, days in announcement_lists(rows).items():
      for spread_key in ("spread", "spread_lagged_ois"):
        for start in ("2007-01-01", "2007-08-09"):
            for horizon in (1, 5):
                obj, mark, _ = changes(relabel(rows, days), spread_key, start, horizon)
                rate_days = mark["rate_change"]
                taf_days = mark["taf_announce"] | mark["taf_bid"] | mark["taf_settle"]
                shared = int((rate_days & taf_days).sum())
                cell = {"name": f"{list_name}|{spread_key}|{start}|{horizon}d", "n": len(obj),
                        "rate_days": int(rate_days.sum()), "shared_with_taf": shared,
                        # A window that holds both doses cannot tell them apart, so it is printed
                        # and left out of the sign test rather than quietly read as the rate's.
                        "separable": bool(shared == 0)}
                for key in EVENTS:
                    r = read_event(obj, mark[key], seed, draws)
                    cell[key] = None if r["mean_bp"] is None else round(r["mean_bp"], 3)
                    cell[key + "_floors"] = None if r["over_floor"] is None else round(r["over_floor"], 2)
                out.append(cell)
    return out


def signs_hold(cells: list[dict], key: str, separable_only: bool = False) -> tuple[str, list[str]]:
    """Three states, not two: steady, turned over, or nothing clears the floor at all (11c).

    The first version of this returned a single boolean, so a set where no setting cleared the
    floor read the same as a set whose sign a knob turned over. Those are opposite signals."""
    # 11f asks whether the sign turns over on a declared knob, at every setting, whether or not
    # that setting clears its floor. The second version looked only at the settings that cleared,
    # which let a list of days whose readings all sat near zero pass as steady.
    use = [c for c in cells if not separable_only or c.get("separable", True)]
    signed = [(c["name"], c[key]) for c in use if c.get(key) is not None]
    if signed:
        first = signed[0][1] > 0
        off = [n for n, v in signed if (v > 0) != first]
        if off:
            return "turns over", off
    if not any(abs(c.get(key + "_floors") or 0) >= LINE for c in use):
        return "nothing clears the floor", []
    return "steady", []


def build_criteria(rows, main: dict, cells: list[dict], seeds_agree: dict,
                   pick: dict | None = None) -> dict:
    c = {}
    announce, bid, settle = main["taf_announce"], main["taf_bid"], main["taf_settle"]
    rate = main["rate_change"]

    c["B121-7"] = {
        "kind": "instrument",
        "statement": "each event set is named by the rival's own workbook and marks days that "
                     "exist in the window, neither none of them nor all of them",
        "passed": bool(all(0 < main[k]["days"] < len(rows) for k in EVENTS)),
        "detail": ", ".join(f"{k} {main[k]['days']}" for k in EVENTS) + f", of {len(rows)} rows",
    }
    # The rate dose is read only where a window holds no facility day, since a window that holds
    # both cannot say which one moved the object. Those settings are printed all the same.
    mixed = [c["name"] for c in cells if not c.get("separable", True)]
    rate_state, off_rate = signs_hold(cells, "rate_change", separable_only=True)
    clearing = [c["name"] for c in cells if c.get("separable", True)
                and c.get("rate_change_floors") is not None
                and abs(c["rate_change_floors"]) >= LINE]
    # Four states, each mapped once, and the two undecided ones carry no verdict (11c).
    if rate_state == "turns over":
        state, verdict = "knob turns the sign over", None
    elif not clearing and abs(rate["over_floor"]) >= LINE:
        state, verdict = "reads only where the doses share a window", None
    elif abs(rate["over_floor"]) < LINE:
        state, verdict = "inside its own floor", True
    else:
        state, verdict = "outside its own floor", False
    c["B121-8"] = {
        "kind": "own_reading",
        "statement": "the days the target rate changed do not move the wedge: the object on those "
                     "days minus the object on the rest sits inside its own floor",
        "passed": verdict,
        "state": state,
        "state_map": {"knob turns the sign over": "no verdict",
                      "reads only where the doses share a window": "no verdict",
                      "inside its own floor": "pass", "outside its own floor": "fail"},
        "windows_holding_both_doses": mixed,
        "detail": f"{rate['mean_bp']:+.2f} bp on {rate['days']} days, floor {rate['floor']:.2f}, "
                  f"{rate['over_floor']:+.2f} floors, p {rate['p']:.4f}"
                  + (f"; not read: the sign turns over on {off_rate} (11f)" if off_rate else "")
                  + (f"; settings whose windows hold both doses: {mixed}" if mixed else ""),
    }
    picked_key = (pick or {}).get("picked", "taf_announce")
    pick_state, off_pick = signs_hold(cells, picked_key, separable_only=True)
    best = main[picked_key]
    corrected = (pick or {}).get("p_best_of_three")
    # Four states, each mapped once (11c). A knob that turns the sign over, or nothing that
    # clears the floor, leaves the cell unread: that is not the rival being right.
    if pick_state != "steady":
        rival_state, verdict, grid = f"sign {pick_state}", None, "unread"
    elif best["over_floor"] is not None and best["over_floor"] <= -LINE and corrected is not None             and corrected <= 0.05:
        rival_state, verdict, grid = "falls past its floor, sign steady", True, "B"
    elif best["over_floor"] is not None and best["over_floor"] >= LINE:
        rival_state, verdict, grid = "rises past its floor, sign steady", None, "both_unmet"
    else:
        rival_state, verdict, grid = "does not clear its floor or the best-of-three floor, sign steady", False, "C"
    c["B121-9"] = {
        "kind": "rival",
        "statement": "the facility's own days do move it: on the day an auction is announced, bid "
                     "or settled, the object falls, past two of its own floor",
        "passed": verdict,
        "state": rival_state,
        "state_map": {"sign turns over": "no verdict, grid unread",
                      "sign nothing clears the floor": "no verdict, grid unread",
                      "falls past its floor, sign steady": "pass, grid B",
                      "rises past its floor, sign steady": "no verdict, both unmet",
                      "does not clear its floor or the best-of-three floor, sign steady": "fail, grid C"},
        "detail": "; ".join(
            f"{k} {main[k]['mean_bp']:+.2f} bp on {main[k]['days']} days, "
            f"{main[k]['over_floor']:+.2f} floors, p {main[k]['p']:.4f}" for k in
            ("taf_announce", "taf_bid", "taf_settle"))
                  + (f"; three sets were looked at, so the floor takes the best of three per draw: "
                     f"{pick['picked']} {pick['picked_bp']:+.2f} bp, p {pick['p_best_of_three']:.4f}"
                     if pick else ""),
        "selection": pick,
        "grid": grid,
        "rival_shape": "point prediction of zero",
        "rival_premise": "the LIBOR-OIS spread is counterparty risk, a property of the borrowing "
                         "bank, not of the edge it borrows on",
        "rival_entailment": "the facility changes neither total liquidity, nor the expected path "
                            "of the overnight rate, nor counterparty risk, so the spread does not "
                            "move on its days; the difference is zero",
        "cite": "Taylor and Williams, A Black Swan in the Money Market, American Economic "
                "Journal: Macroeconomics 1(1): 58-83, 2009",
    }
    c["B121-10"] = {
        "kind": "instrument",
        "statement": "the sign of the facility's reading holds on every declared setting where the "
                     "reading stands clear of its floor, so no knob of this station sets it",
        "passed": {"steady": True, "turns over": False, "nothing clears the floor": None}[pick_state],
        "state": pick_state,
        "state_map": {"steady": "pass", "turns over": "fail",
                      "nothing clears the floor": "no verdict"},
        "detail": f"{len(cells)} settings, {picked_key}: {pick_state}"
                  + (f"; turned over on {off_pick}" if off_pick else ""),
    }
    c["B121-11"] = {
        "kind": "instrument",
        "statement": "two seeds leave every reading in the same state and each p moves by less "
                     "than its distance to the line",
        "passed": bool(seeds_agree["ok"]),
        "detail": seeds_agree["detail"],
    }
    return c


def selftest(rows) -> int:
    obj, mark, _ = changes(rows, "spread", "2007-01-01", 1)
    main = {k: read_event(obj, mark[k], SEEDS[0], 200) for k in EVENTS}
    cells = [{"name": "a", "taf_bid": -3.0, "taf_bid_floors": -3.0, "separable": True},
             {"name": "b", "taf_bid": -2.5, "taf_bid_floors": -2.5, "separable": True}]
    pick_ok = {"picked": "taf_announce", "picked_bp": -3.5, "p_best_of_three": 0.02}
    pick_weak = dict(pick_ok, p_best_of_three=0.21)
    agree = {"ok": True, "detail": "seeded"}
    bad = 0

    empty = dict(main); empty["taf_bid"] = dict(main["taf_bid"], days=0)
    if build_criteria(rows, empty, cells, agree)["B121-7"]["passed"]:
        print("  B121-7 did not fail on an event set that marks no day"); bad += 1


    rate_cells = cells + [{"name": "r1", "rate_change": -4.0, "rate_change_floors": -4.0,
                           "separable": True},
                          {"name": "r2", "rate_change": +4.0, "rate_change_floors": +4.0,
                           "separable": True}]
    if build_criteria(rows, main, rate_cells, agree)["B121-8"]["passed"] is not None:
        print("  B121-8 still gave a verdict when a knob turned its sign over"); bad += 1
    steady = cells + [{"name": "r1", "rate_change": -4.0, "rate_change_floors": -4.0,
                       "separable": True}]
    loud2 = dict(main); loud2["rate_change"] = dict(main["rate_change"], over_floor=-6.0)
    if build_criteria(rows, loud2, steady, agree)["B121-8"]["passed"] is not False:
        print("  B121-8 did not fail on a steady sign far outside its floor"); bad += 1
    shared_only = cells + [{"name": "m1", "rate_change": -4.0, "rate_change_floors": -4.0,
                            "separable": False}]
    if build_criteria(rows, loud2, shared_only, agree)["B121-8"]["passed"] is not None:
        print("  B121-8 gave a verdict where only a shared window cleared the floor"); bad += 1

    cells = [{"name": "a", "taf_announce": -3.0, "taf_announce_floors": -3.0, "separable": True},
             {"name": "b", "taf_announce": -2.5, "taf_announce_floors": -2.5, "separable": True}]
    if build_criteria(rows, main, cells, agree, pick_weak)["B121-9"]["passed"]:
        print("  B121-9 did not fail when the best of three sits inside the corrected floor"); bad += 1

    quiet = {k: dict(v, over_floor=-0.2) for k, v in main.items()}
    quiet["rate_change"] = main["rate_change"]
    if build_criteria(rows, quiet, cells, agree, pick_ok)["B121-9"]["passed"]:
        print("  B121-9 did not fail when every facility day sits inside its floor"); bad += 1

    wrong = {k: dict(v, over_floor=+4.0, mean_bp=+3.0) for k, v in main.items()}
    wrong["rate_change"] = main["rate_change"]
    crit = build_criteria(rows, wrong, cells, agree, pick_ok)["B121-9"]
    if crit["passed"] or crit["grid"] == "B":
        print("  B121-9 did not fail, or still claimed a cell, on a reading of the wrong sign"); bad += 1

    steady_cells = [{"name": "a", "taf_announce": -3.0, "taf_announce_floors": -3.0, "separable": True}]
    quiet_flip = steady_cells + [{"name": "q", "taf_announce": +0.04, "taf_announce_floors": +0.03,
                                  "separable": True}]
    if build_criteria(rows, main, quiet_flip, agree, pick_ok)["B121-10"]["passed"] is not False:
        print("  B121-10 let a sign turn over where the turned setting sat inside its floor"); bad += 1
    turned = steady_cells + [{"name": "c", "taf_announce": +3.0, "taf_announce_floors": +3.0,
                              "separable": True}]
    if build_criteria(rows, main, turned, agree, pick_ok)["B121-10"]["passed"] is not False:
        print("  B121-10 did not fail when a setting turned the sign over"); bad += 1
    if build_criteria(rows, main, steady_cells, agree, pick_ok)["B121-10"]["passed"] is not True:
        print("  B121-10 did not pass on a steady sign"); bad += 1
    nothing = [{"name": "a", "taf_announce": -0.4, "taf_announce_floors": -0.4, "separable": True}]
    if build_criteria(rows, main, nothing, agree, pick_ok)["B121-10"]["passed"] is not None:
        print("  B121-10 gave a verdict when no setting cleared the floor"); bad += 1
    if build_criteria(rows, main, cells, {"ok": False, "detail": "x"})["B121-11"]["passed"]:
        print("  B121-11 did not fail when the seeds disagreed"); bad += 1

    # The floor itself must be able to speak: a set of days planted with a large fall has to
    # come out past the floor, and a set of days drawn at random must not.
    rng = np.random.default_rng(5)
    planted = np.zeros(len(obj), dtype=bool); planted[rng.choice(len(obj), 20, replace=False)] = True
    loud_obj = obj.copy(); loud_obj[planted] -= 25.0
    r = read_event(loud_obj, planted, SEEDS[0], 400)
    if r["over_floor"] is None or r["over_floor"] > -LINE:
        print(f"  the floor missed a planted fall of 25 bp ({r['over_floor']})"); bad += 1
    r2 = read_event(obj, planted, SEEDS[0], 400)
    if r2["over_floor"] is not None and abs(r2["over_floor"]) >= LINE:
        print(f"  the floor called random days a reading ({r2['over_floor']})"); bad += 1

    print("selftest: every criterion failed on its planted input, and the floor answered both probes"
          if not bad else f"selftest: {bad} checks did not behave")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()

    rows = sorted(json.loads(PANEL.read_text(encoding="utf-8"))["panel"], key=lambda r: r["date"])
    if args.selftest:
        return 1 if selftest(rows) else 0

    obj, mark, dates = changes(rows, "spread", "2007-01-01", 1)
    print(f"days read: {len(obj)}, {dates[1]} to {dates[-1]}")
    by_seed = {}
    for seed in SEEDS:
        by_seed[seed] = {k: read_event(obj, mark[k], seed, args.draws) for k in EVENTS}
        for k, r in by_seed[seed].items():
            print(f"  seed {seed} {k:<13} {r['days']:>3} days  {r['mean_bp']:+7.2f} bp  "
                  f"floor {r['floor']:5.2f}  {r['over_floor']:+6.2f} floors  p {r['p']:.4f}")
    main_read = by_seed[SEEDS[0]]

    parts, ok = [], True
    for k in EVENTS:
        a, b = (by_seed[s][k]["over_floor"] for s in SEEDS)
        gap, dist = abs(a - b), abs(abs((a + b) / 2) - LINE)
        same = (abs(a) >= LINE) == (abs(b) >= LINE)
        ok = ok and same and gap < dist
        parts.append(f"{k}: {a:+.2f} and {b:+.2f}, moved {gap:.3f}, stands {dist:.3f} from the line")
    seeds_agree = {"ok": bool(ok), "detail": "; ".join(parts)}
    print("  " + seeds_agree["detail"])

    cells = sweep(rows, SEEDS[0], max(400, args.draws // 4))
    print(f"\nknob sweep, {len(cells)} settings (11f), bp and floors:")
    for c in cells:
        tag = "" if c.get("separable", True) else f"  [both doses in {c['shared_with_taf']} windows]"
        print(f"  {c['name']:<34} n {c['n']:>3} " + "  ".join(
            f"{k.split('_')[-1]} {c[k]:+6.2f} ({c[k + '_floors']:+5.2f})"
            if c[k] is not None else f"{k}: none" for k in EVENTS) + tag)

    pick = best_of_three(obj, mark, SEEDS[0], args.draws)
    print(f"\nbest of the three facility sets: {pick['picked']} {pick['picked_bp']:+.2f} bp, "
          f"p against a best-of-three floor {pick['p_best_of_three']:.4f} ({pick['draws']} draws)")
    criteria = build_criteria(rows, main_read, cells, seeds_agree, pick)
    print()
    for name, c in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"{flag:<10} {name} [{c['kind']}] {c['detail']}")

    record = {
        "stage": "B121",
        "config": {"draws": args.draws, "seeds": list(SEEDS), "block_days": BLOCK,
                   "line_in_floors": LINE, "spread_key": "spread", "horizon_days": 1,
                   "window": [dates[0], dates[-1]]},
        "source": {"main_window": "openICPSR 114040, the rival's own replication data",
                   "event_columns": EVENTS},
        "readings": {"by_seed": by_seed, "knobs": cells, "seeds_agree": seeds_agree,
                     "selection": pick},
        "criteria": [dict(c, name=n) for n, c in criteria.items()],
        "diagnostic_only": True,
        "diagnostic_reason": "Main window only, to 2008-08-08; the extension window past Lehman "
                             "is not read yet, so the station is not closed.",
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] is not False for c in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
