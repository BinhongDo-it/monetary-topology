"""B128 arm A, split at the zero floor: the prediction the document ruling gives, read on halves not yet seen.

The ruling (design, cell 1 addendum): an ECB speech of 2016-07-28 says retail deposit rates have a zero lower bound
and that cuts pass more strongly to loan rates. So the deposit edge breathes (a floor fixed at zero, which binds or
not with the rate level) and the loan edge has no rule that moves with the level.

The hike window is cut where the floor lets go. Part 1, 2022-06 to the boundary (the deposit facility rate from
-0.50 to 2.00): the floor releases here. Part 2, the boundary to 2023-12 (2.00 to 4.00): far from zero.

  framework   deposits: part 1 above the dose-free floor, part 2 inside it, and part 2 unrelated to part 1
              loans: both parts inside the floor
  rival       every group moves with the dose in both parts, part 2 about +2.00/2.50 = +0.80 times part 1

Floors: every dose-free window of each part's length (2016-04 to 2019-08, 2019-10 to 2022-06), and every disjoint
pair of such windows for the correlation of part 2 on part 1. Groups: loans, deposits, household deposits (the
retail class the speech names), corporate deposits. Knob (`11f`): the boundary month, 2022-11, 2022-12, 2023-01.

    python experiments/b128_a_split.py
    python experiments/b128_a_split.py --selftest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import b128_a_long_difference as ld
import b128_a_rate_dose as base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b128_a_split.json"
START, END = "2022-06", "2023-12"
BOUNDARIES = ("2022-11", "2022-12", "2023-01")
RIVAL_SLOPE = 2.00 / 2.50
GROUPS = {"loans": base.LOANS, "deposits": base.DEPOSITS,
          "household deposits": ("L22_F_R_A_2250", "L21_A_R_A_2250"),
          "corporate deposits": ("L22_F_R_A_2240", "L21_A_R_A_2240")}
BREATHES = {"loans": False, "deposits": True, "household deposits": True, "corporate deposits": True}


def read(ms: list[str], X: np.ndarray, boundary: str) -> dict:
    E = base.interaction(X).reshape(len(ms), -1)
    ix = {m: i for i, m in enumerate(ms)}
    a, b, c = ix[START], ix[boundary], ix[END]
    d1, d2 = E[b] - E[a], E[c] - E[b]
    f1 = ld.windows_within(ld.DOSE_FREE, b - a, ms)
    f2 = ld.windows_within(ld.DOSE_FREE, c - b, ms)
    r1 = [ld.rms(E[y] - E[x]) for x, y in f1]
    r2 = [ld.rms(E[y] - E[x]) for x, y in f2]
    pairs = [(w1, w2) for w1 in f1 for w2 in f2 if w1[1] <= w2[0]]  # part 1 before part 2, as in the window
    null = np.array([ld.corr_slope(E[w1[1]] - E[w1[0]], E[w2[1]] - E[w2[0]])[0] for w1, w2 in pairs])
    rho, slope = ld.corr_slope(d1, d2)
    return {"boundary": boundary, "R1": round(ld.rms(d1), 4), "floor1_max": round(max(r1), 4),
            "R2": round(ld.rms(d2), 4), "floor2_max": round(max(r2), 4),
            "rho": round(rho, 4), "slope": round(slope, 4), "pairs": len(pairs),
            "null_p05": round(float(np.quantile(null, 0.05)), 4), "null_p95": round(float(np.quantile(null, 0.95)), 4)}


def shape_of(r: dict, breathes: bool) -> str:
    rival = r["rho"] > r["null_p95"]
    inside = r["null_p05"] <= r["rho"] <= r["null_p95"]
    p1 = r["R1"] > r["floor1_max"]
    p2 = r["R2"] > r["floor2_max"]
    if rival:
        return "rival"
    if inside and (p1 and not p2 if breathes else not p1 and not p2):
        return "framework"
    return "neither"


STATE_MAP = {"framework shape at every boundary": "pass, grid B",
             "rival shape at every boundary": "fail, grid C",
             "neither shape at every boundary": "pass, grid both_unmet (both sides read, neither held)",
             "a boundary decides": "no verdict, grid unread"}


def verdict(shapes: list[str]) -> tuple[bool | None, str, str]:
    if set(shapes) == {"framework"}:
        return True, "B", "framework shape at every boundary"
    if set(shapes) == {"rival"}:
        return False, "C", "rival shape at every boundary"
    if set(shapes) == {"neither"}:
        return True, "both_unmet", "neither shape at every boundary"
    return None, "unread", "a boundary decides"


def build(data) -> dict:
    ms = base.months(*ld.SPAN)
    rows, crit = [], []
    for k, (gname, shapes) in enumerate(GROUPS.items()):
        _, areas, X = base.panel(data, shapes, ld.SPAN)
        reads = [read(ms, X, bd) for bd in BOUNDARIES]
        kinds = [shape_of(r, BREATHES[gname]) for r in reads]
        passed, grid, state = verdict(kinds)
        rows.append({"group": gname, "breathes": BREATHES[gname], "countries": areas, "reads": reads, "shapes": kinds})
        framework_says = ("part 1 above its floor, part 2 inside it, part 2 unrelated to part 1" if BREATHES[gname]
                          else "both parts inside their floors, part 2 unrelated to part 1")
        crit.append({"name": f"B128-{6 + k}", "kind": "rival", "grid": grid, "passed": passed, "state": state,
                     "state_map": STATE_MAP, "rival_shape": "point prediction",
                     "rival_premise": "pass-through coefficients to the policy rate differ by country and product, and are the same in every part of a cycle",
                     "rival_entailment": "each cell moves by its interaction coefficient times the dose, so across 2022-12 to 2023-12 (+2.00) it moves +0.80 times what it moved across 2022-06 to 2022-12 (+2.50)",
                     "statement": f"{gname}: the rival's +0.80 does not hold; the framework's registered shape is {framework_says}",
                     "detail": "; ".join(f"{r['boundary']}: R1 {r['R1']} (floor {r['floor1_max']}), R2 {r['R2']} (floor {r['floor2_max']}), "
                                         f"rho {r['rho']} slope {r['slope']} (dose-free 5-95% [{r['null_p05']}, {r['null_p95']}]) -> {s}"
                                         for r, s in zip(reads, kinds))})
    return {"stage": "B128", "arm": "A", "instrument": "long differences split at the zero floor", "rows": rows,
            "criteria": crit, "config": {"start": START, "end": END, "boundaries": BOUNDARIES, "rival_slope": RIVAL_SLOPE,
                                         "groups": {k: list(v) for k, v in GROUPS.items()}, "breathes": BREATHES,
                                         "ruling": "ECB speech 2016-07-28, data/raw/b128/lit/ecb_praet_20160728.html"},
            "source": {"rates": "data/raw/b128/mir_B_*.csv"}}


def selftest() -> None:
    rng = np.random.default_rng(2)
    ms = base.months(*ld.SPAN)
    dfr = {"2022-07": .5, "2022-09": .75, "2022-11": .75, "2022-12": .5, "2023-02": .5, "2023-03": .5, "2023-05": .25,
           "2023-06": .25, "2023-08": .25, "2023-09": .25}
    path = np.cumsum([dfr.get(m, 0.0) for m in ms])[:, None, None]
    n, g = 12, 4
    drift = rng.normal(0, 0.02, (len(ms), n, g)).cumsum(axis=0)
    beta = rng.normal(0, 0.3, (n, g))
    linear = 1 + path * beta[None] + drift                                    # the rival's world
    floor_rel = np.clip(path, None, 2.0)                                      # a floor fully let go before the earliest boundary
    floored = 1 + floor_rel * beta[None] + drift                              # the framework's breathing edge
    flat = 1 + drift                                                          # a non-breathing edge with no pass-through heterogeneity
    s_lin = [shape_of(read(ms, linear, bd), True) for bd in BOUNDARIES]
    s_flo = [shape_of(read(ms, floored, bd), True) for bd in BOUNDARIES]
    s_flat = [shape_of(read(ms, flat, bd), False) for bd in BOUNDARIES]
    assert set(s_lin) == {"rival"}, s_lin
    assert set(s_flo) == {"framework"}, s_flo
    assert set(s_flat) == {"framework"}, s_flat
    assert verdict(s_lin)[:2] == (False, "C") and verdict(s_flo)[:2] == (True, "B")
    assert verdict(["framework", "rival", "framework"])[:2] == (None, "unread")
    assert verdict(["neither"] * 3)[:2] == (True, "both_unmet")
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    out = build(base.load_rates())
    for r in out["rows"]:
        print(f"== {r['group']} (breathes: {r['breathes']}), {len(r['countries'])} countries")
        for x, s in zip(r["reads"], r["shapes"]):
            print(f"   boundary {x['boundary']}: R1 {x['R1']:.3f} (floor {x['floor1_max']:.3f})  R2 {x['R2']:.3f} (floor {x['floor2_max']:.3f})"
                  f"  rho {x['rho']:+.3f} slope {x['slope']:+.3f}  dose-free [{x['null_p05']:+.3f}, {x['null_p95']:+.3f}]  -> {s}")
    for c in out["criteria"]:
        flag = "no verdict" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{c['name']} [rival, grid {c['grid']}] {flag}: {c['state']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
