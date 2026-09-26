"""B121 arm A2, part two: read the main window, score the criteria, and check itself.

The panel comes from part one (`results/b121_a2_panel.json`), which is built from the rival's
own data. Two doses are read against one object:

  object   the three-month LIBOR minus the three-month OIS, in basis points, in daily changes
  dose 1   how much of the federal funds target has been taken away, in percentage points
  dose 2   the Term Auction Facility's outstanding balance, in billions

The framework says the rate dose does not reach a wedge that lives on an edge, and that adding
the edge does. Taylor and Williams say the spread is counterparty risk, which the facility does
not touch, so the facility's dose reads zero. The two sides give opposite signs on dose 2, which
is why that one is registered as `rival`.

    python experiments/b121_a2_read.py
    python experiments/b121_a2_read.py --selftest     # the probes, then the mutations
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "results" / "b121_a2_panel.json"
OUT = ROOT / "results" / "b121_a2_read.json"

DRAWS = 2000          # D51 wants the sampling error of p small against its distance to the line
SEEDS = (11, 23)
BLOCK = 5             # one trading week, so a permutation keeps the dose's own local shape
PEAK = 5.25           # the target rate at the window's start; the dose is how far below it we are


def load(path: Path = PANEL) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))["panel"]
    return sorted(rows, key=lambda r: r["date"])


def series(rows: list[dict], spread_key: str, taf_key: str, control: bool, start: str):
    """Daily changes of the object and of each dose, on the days where all of them exist."""
    keep = [r for r in rows if r["date"] >= start]
    out = {"date": [], "d_spread": [], "d_cut": [], "d_taf": [], "d_cds": []}
    for prev, cur in zip(keep, keep[1:]):
        need = [cur[spread_key], prev[spread_key], cur["fft"], prev["fft"],
                cur[taf_key], prev[taf_key]]
        if control:
            need += [cur["cds_median"], prev["cds_median"]]
        if any(v is None for v in need):
            continue
        out["date"].append(cur["date"])
        out["d_spread"].append((cur[spread_key] - prev[spread_key]) * 100.0)
        out["d_cut"].append((PEAK - cur["fft"]) - (PEAK - prev["fft"]))
        out["d_taf"].append(cur[taf_key] - prev[taf_key])
        out["d_cds"].append((cur["cds_median"] - prev["cds_median"]) if control else 0.0)
    return {k: (np.array(v) if k != "date" else v) for k, v in out.items()}


def fit(s: dict, control: bool) -> dict:
    """One least squares, both doses at once, so neither carries the other's movement."""
    cols = [np.ones_like(s["d_spread"]), s["d_cut"], s["d_taf"]]
    names = ["const", "cut", "taf"]
    if control:
        cols.append(s["d_cds"])
        names.append("cds")
    X = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(X, s["d_spread"], rcond=None)
    return {n: float(b) for n, b in zip(names, beta)}


def block_permute(x: np.ndarray, rng: np.random.Generator, block: int = BLOCK) -> np.ndarray:
    """Shuffle whole weeks of a dose, so its own lumpiness survives and its timing does not."""
    chunks = [x[i:i + block] for i in range(0, len(x), block)]
    order = rng.permutation(len(chunks))
    return np.concatenate([chunks[i] for i in order])[:len(x)]


def floor_for(s: dict, control: bool, which: str, seed: int, draws: int = DRAWS) -> dict:
    """The floor is measured, never declared: the same fit with that dose's weeks shuffled."""
    rng = np.random.default_rng(seed)
    real = fit(s, control)[which]
    null = np.empty(draws)
    for i in range(draws):
        shuffled = dict(s)
        shuffled["d_" + which] = block_permute(s["d_" + which], rng)
        null[i] = fit(shuffled, control)[which]
    sd = float(np.std(null, ddof=1))
    p_two = float((np.sum(np.abs(null) >= abs(real)) + 1) / (draws + 1))
    return {"coef": real, "null_sd": sd, "over_floor": real / sd if sd else float("nan"),
            "p": p_two, "draws": draws, "seed": seed,
            "null_median": float(np.median(null))}


# ---------------------------------------------------------------- criteria

def build_criteria(rows: list[dict], panel_meta: dict, main: dict, knobs: list[dict],
                   seeds_agree: dict) -> dict:
    c = {}
    dates = [r["date"] for r in rows]
    covered = sum(1 for r in rows if r["spread"] is not None)
    c["B121-1"] = {
        "kind": "instrument",
        "statement": "the panel carries one row per trading day of the window, no date twice, "
                     "and the object exists on the days the reading uses",
        "passed": bool(len(dates) == len(set(dates)) and covered >= 380 and len(rows) >= 400),
        "detail": f"{len(rows)} rows, {len(set(dates))} distinct dates, object on {covered}",
    }
    chk = panel_meta["libor_reconstruction_check"]
    c["B121-2"] = {
        "kind": "known_answer",
        "statement": "the LIBOR the extension window will use, TEDRATE plus DTB3, returns the "
                     "workbook's own US0003M within one basis point on every overlapping day",
        "passed": bool(chk["days"] > 300 and chk["largest_gap_bp"] is not None
                       and chk["largest_gap_bp"] <= 1.0),
        "detail": f"{chk['days']} days, median gap {chk['median_gap_bp']} bp, "
                  f"largest {chk['largest_gap_bp']} bp",
    }
    cut = main["cut"]
    c["B121-3"] = {
        "kind": "own_reading",
        "statement": "the rate dose does not move the wedge: the response of the daily change in "
                     "LIBOR minus OIS to the cut taken that day sits inside its own floor",
        "passed": bool(abs(cut["over_floor"]) < 2.0),
        "detail": f"{cut['coef']:+.2f} bp per point of cut, floor {cut['null_sd']:.2f}, "
                  f"{cut['over_floor']:+.2f} of its own floor, p {cut['p']:.4f}",
    }
    taf = main["taf"]
    flips = [k for k in knobs if k["taf_sign"] != knobs[0]["taf_sign"]]
    # A sign that a declared knob turns over leaves the cell unread, with no verdict (11c, 11f).
    if flips:
        verdict, grid = None, "unread"
    elif taf["coef"] < 0 and taf["over_floor"] <= -2.0:
        verdict, grid = True, "B"
    else:
        verdict, grid = False, "C"
    c["B121-4"] = {
        "kind": "rival",
        "statement": "the facility's dose does move it: the response to a billion of TAF "
                     "outstanding is negative and past two of its own floor",
        "passed": verdict,
        "state_map": {"a declared knob turns the sign over": "no verdict, grid unread",
                      "negative past two floors, sign steady": "pass, grid B",
                      "otherwise, sign steady": "fail, grid C"},
        "detail": f"{taf['coef']:+.4f} bp per billion, floor {taf['null_sd']:.4f}, "
                  f"{taf['over_floor']:+.2f} of its own floor, p {taf['p']:.4f}"
                  + (f"; not read: {len(flips)} of {len(knobs)} declared settings turn the sign over"
                     if flips else ""),
        "grid": grid,
        "rival_shape": "point prediction of zero",
        "rival_premise": "the LIBOR-OIS spread is counterparty risk, a property of the borrowing "
                         "bank, not of the edge it borrows on",
        "rival_entailment": "the Term Auction Facility changes neither total liquidity, nor the "
                            "expected path of the overnight rate, nor counterparty risk, so it "
                            "changes nothing in the spread; the dose response is zero",
        "cite": "Taylor and Williams, A Black Swan in the Money Market, American Economic "
                "Journal: Macroeconomics 1(1): 58-83, 2009",
    }
    c["B121-5"] = {
        "kind": "instrument",
        "statement": "the sign of the facility's dose response holds on every setting this "
                     "station has already declared, so the cell is read rather than set by a knob",
        "passed": bool(not flips),
        "detail": f"{len(knobs)} settings, signs "
                  + ", ".join(f"{k['name']}:{k['taf_sign']:+d}" for k in knobs)
                  + (f"; flipped on {[k['name'] for k in flips]}" if flips else ""),
    }
    c["B121-6"] = {
        "kind": "instrument",
        "statement": "two seeds put every reading in the same state, and each p moves by less "
                     "than its distance to the line it is read against",
        "passed": bool(seeds_agree["ok"]),
        "detail": seeds_agree["detail"],
    }
    return c


def knob_sweep(rows: list[dict]) -> list[dict]:
    out = []
    for spread_key in ("spread", "spread_lagged_ois"):
        for taf_key in ("taf_frb", "taf_tot"):
            for control in (False, True):
                for start in ("2007-01-01", "2007-08-09"):
                    s = series(rows, spread_key, taf_key, control, start)
                    b = fit(s, control)
                    out.append({
                        "name": f"{spread_key}|{taf_key}|{'cds' if control else 'no cds'}|{start}",
                        "n": len(s["date"]), "cut": round(b["cut"], 4), "taf": round(b["taf"], 5),
                        "taf_sign": 1 if b["taf"] > 0 else -1,
                        "cut_sign": 1 if b["cut"] > 0 else -1,
                    })
    return out


def selftest(rows: list[dict], panel_meta: dict) -> int:
    """Every criterion is fed an input that should make it fail (11f)."""
    s = series(rows, "spread", "taf_frb", False, "2007-01-01")
    main = {"cut": floor_for(s, False, "cut", SEEDS[0], draws=200),
            "taf": floor_for(s, False, "taf", SEEDS[0], draws=200)}
    knobs = [{"name": "a", "taf_sign": -1}, {"name": "b", "taf_sign": -1}]
    agree = {"ok": True, "detail": "seeded"}
    bad = 0

    thin = rows[:50]
    if build_criteria(thin, panel_meta, main, knobs, agree)["B121-1"]["passed"]:
        print("  B121-1 did not fail on a panel cut to 50 rows"); bad += 1
    twice = rows + rows[:1]
    if build_criteria(twice, panel_meta, main, knobs, agree)["B121-1"]["passed"]:
        print("  B121-1 did not fail on a date carried twice"); bad += 1

    meta_bad = json.loads(json.dumps(panel_meta))
    meta_bad["libor_reconstruction_check"]["largest_gap_bp"] = 38.8
    if build_criteria(rows, meta_bad, main, knobs, agree)["B121-2"]["passed"]:
        print("  B121-2 did not fail on a gap of 38.8 bp"); bad += 1

    loud = {"cut": dict(main["cut"], over_floor=-7.0), "taf": main["taf"]}
    if build_criteria(rows, panel_meta, loud, knobs, agree)["B121-3"]["passed"]:
        print("  B121-3 did not fail on a rate dose far outside its floor"); bad += 1

    quiet = {"cut": main["cut"], "taf": dict(main["taf"], coef=-0.001, over_floor=-0.3)}
    if build_criteria(rows, panel_meta, quiet, knobs, agree)["B121-4"]["passed"]:
        print("  B121-4 did not fail on a facility dose inside its floor"); bad += 1
    wrongway = {"cut": main["cut"], "taf": dict(main["taf"], coef=+0.02, over_floor=+4.0)}
    crit = build_criteria(rows, panel_meta, wrongway, knobs, agree)["B121-4"]
    if crit["passed"] or crit["grid"] == "B":
        print("  B121-4 did not fail, or still claimed a cell, on a dose of the wrong sign"); bad += 1

    flipped = [{"name": "a", "taf_sign": -1}, {"name": "b", "taf_sign": +1}]
    if build_criteria(rows, panel_meta, main, flipped, agree)["B121-5"]["passed"]:
        print("  B121-5 did not fail when a knob flipped the sign"); bad += 1
    crit = build_criteria(rows, panel_meta, main, flipped, agree)["B121-4"]
    if crit["passed"] is not None or crit["grid"] != "unread":
        print("  B121-4 gave a verdict when a knob flipped the sign"); bad += 1
    if build_criteria(rows, panel_meta, main, knobs, {"ok": False, "detail": "x"})["B121-6"]["passed"]:
        print("  B121-6 did not fail when the seeds disagreed"); bad += 1

    print("selftest: every criterion failed on its planted input" if not bad
          else f"selftest: {bad} criteria did not fail when they should have")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()

    meta = json.loads(PANEL.read_text(encoding="utf-8"))
    rows = sorted(meta["panel"], key=lambda r: r["date"])
    if args.selftest:
        return 1 if selftest(rows, meta) else 0

    s = series(rows, "spread", "taf_frb", False, "2007-01-01")
    print(f"days read: {len(s['date'])}, {s['date'][0]} to {s['date'][-1]}")
    print(f"the object moves {statistics.stdev(s['d_spread']):.2f} bp a day, "
          f"largest one-day move {max(abs(s['d_spread'])):.1f} bp")

    by_seed = {}
    for seed in SEEDS:
        by_seed[seed] = {"cut": floor_for(s, False, "cut", seed, args.draws),
                         "taf": floor_for(s, False, "taf", seed, args.draws)}
        for which, r in by_seed[seed].items():
            print(f"  seed {seed} {which:<4} {r['coef']:+.4f}  floor {r['null_sd']:.4f}  "
                  f"{r['over_floor']:+.2f} floors  p {r['p']:.4f}")
    main_read = by_seed[SEEDS[0]]

    # D51: a p that moves more between seeds than it stands from its line has not been measured.
    lines = {"cut": 2.0, "taf": 2.0}
    parts, ok = [], True
    for which in ("cut", "taf"):
        a, b = (by_seed[sd][which]["over_floor"] for sd in SEEDS)
        gap, dist = abs(a - b), abs(abs((a + b) / 2) - lines[which])
        same = (abs(a) >= lines[which]) == (abs(b) >= lines[which])
        ok = ok and same and gap < dist
        parts.append(f"{which}: {a:+.2f} and {b:+.2f} floors, moved {gap:.3f}, "
                     f"stands {dist:.3f} from the line")
    seeds_agree = {"ok": bool(ok), "detail": "; ".join(parts)}
    print("  " + seeds_agree["detail"])

    knobs = knob_sweep(rows)
    print(f"\nknob sweep, {len(knobs)} settings (11f):")
    for k in knobs:
        print(f"  {k['name']:<52} n {k['n']:>3}  cut {k['cut']:+8.3f}  taf {k['taf']:+8.5f}")

    criteria = build_criteria(rows, meta, main_read, knobs, seeds_agree)
    print()
    for name, c in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"{flag:<10} {name} [{c['kind']}] {c['detail']}")

    record = {
        "stage": "B121",
        "config": {"draws": args.draws, "seeds": list(SEEDS), "block_days": BLOCK,
                   "peak_target_rate": PEAK, "window": [rows[0]["date"], rows[-1]["date"]],
                   "spread_key": "spread", "taf_key": "taf_frb", "control": None},
        "source": meta["source"],
        "readings": {"by_seed": by_seed, "knobs": knobs, "seeds_agree": seeds_agree,
                     "days": len(s["date"])},
        "criteria": [dict(c, name=n) for n, c in criteria.items()],
        "diagnostic_only": True,
        "diagnostic_reason": "Main window only, to 2008-08-08. The extension window past Lehman "
                             "is not read yet, so the station is not closed.",
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] is not False for c in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
