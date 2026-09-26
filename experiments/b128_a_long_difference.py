"""B128 arm A, second instrument: long differences of the interaction against windows with no rate change.

Why a second instrument. The first (`b128_a_rate_dose.py`) regressed monthly changes on the dose and built its
floor by shifting the dose round a 35-month window. The hikes sit in 15 of those months, so shifted doses still
land on rising rates, and the floor was too high to see even the level pass-through that everyone saw: its own
known-answer check failed in 10 of 16 settings. A reading from an instrument that cannot see the known answer
carries nothing.

The object is the same: E[i, g], the country-by-product interaction of new-business rates (row and column means
removed each month), which is zero exactly when every square is.

Three readings:
  1. Magnitude. R = root mean square over cells of E(end) - E(start) across the hike window (2022-06 to
     2023-12, the deposit facility rate up 4.50) and across the cut window (2024-05 to 2025-09, down 2.00).
     The floor is the same statistic over every window of the same length that contains no rate change
     (2016-04 to 2019-08 and 2019-10 to 2022-06).
  2. Known answer. The same long difference of each product's euro-area mean level: the hikes must show far
     above the drift of the dose-free windows, or the instrument is blind.
  3. Sign. The rival's linear pass-through gives each cell a change proportional to the dose, so the cell
     changes across the cut window are -2.00/4.50 = -0.44 times those across the hike window: a point
     prediction on the slope, and a negative correlation. The framework says the two are unrelated. The floor
     is the correlation and slope between pairs of disjoint dose-free windows of the same two lengths, which
     carries whatever mean reversion the interaction has without any dose.

Knob: the product set (all ten, loans, deposits), printed. Countries: in the euro area in every month from 2016-01
to 2025-12 and reporting every product of the set in every month.

    python experiments/b128_a_long_difference.py
    python experiments/b128_a_long_difference.py --selftest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import b128_a_rate_dose as base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b128_a_long_difference.json"
SPAN = ("2016-01", "2025-12")
HIKE = ("2022-06", "2023-12")
CUT = ("2024-05", "2025-09")
DOSE_FREE = (("2016-04", "2019-08"), ("2019-10", "2022-06"))
RIVAL_SLOPE = -2.00 / 4.50


def windows_within(spans, length: int, ms: list[str]) -> list[tuple[int, int]]:
    out = []
    for a, b in spans:
        i0, i1 = ms.index(a), ms.index(b)
        out += [(s, s + length) for s in range(i0, i1 - length + 1)]
    return out


def rms(v: np.ndarray) -> float:
    return float(np.sqrt(np.mean(v ** 2)))


def corr_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x, y = x - x.mean(), y - y.mean()
    return float((x @ y) / np.sqrt((x @ x) * (y @ y))), float((x @ y) / (x @ x))


def read(ms: list[str], X: np.ndarray) -> dict:
    E = base.interaction(X).reshape(len(ms), -1)
    L = X.mean(axis=1)  # month x product, euro-area mean levels
    ix = {m: i for i, m in enumerate(ms)}
    h0, h1, c0, c1 = ix[HIKE[0]], ix[HIKE[1]], ix[CUT[0]], ix[CUT[1]]
    dh, dc = E[h1] - E[h0], E[c1] - E[c0]
    kh, kc = h1 - h0, c1 - c0
    free_h, free_c = windows_within(DOSE_FREE, kh, ms), windows_within(DOSE_FREE, kc, ms)
    floor_h = [rms(E[b] - E[a]) for a, b in free_h]
    floor_c = [rms(E[b] - E[a]) for a, b in free_c]
    lvl_h = np.abs(L[h1] - L[h0])
    lvl_free = np.array([np.abs(L[b] - L[a]) for a, b in free_h])
    pairs = [(w1, w2) for w1 in free_h for w2 in free_c if w1[1] <= w2[0] or w2[1] <= w1[0]]
    null = [corr_slope(E[w1[1]] - E[w1[0]], E[w2[1]] - E[w2[0]]) for w1, w2 in pairs]
    rho, slope = corr_slope(dh, dc)
    nr = np.array([n[0] for n in null])
    return {"R_hike": round(rms(dh), 4), "R_cut": round(rms(dc), 4),
            "floor_hike_max": round(max(floor_h), 4), "floor_hike_p90": round(float(np.quantile(floor_h, 0.9)), 4),
            "floor_cut_max": round(max(floor_c), 4), "windows_hike": len(floor_h), "windows_cut": len(floor_c),
            "level_hike": [round(float(v), 3) for v in lvl_h],
            "level_free_max": [round(float(v), 3) for v in lvl_free.max(axis=0)],
            "rho": round(rho, 4), "slope": round(slope, 4), "rival_slope": round(RIVAL_SLOPE, 4),
            "null_pairs": len(null), "null_rho_p05": round(float(np.quantile(nr, 0.05)), 4) if len(nr) else None,
            "null_rho_p95": round(float(np.quantile(nr, 0.95)), 4) if len(nr) else None,
            "null_rho_share_at_or_below": round(float((nr <= rho).mean()), 4) if len(nr) else None,
            "cells": int(E.shape[1])}


def build(data) -> dict:
    ms = base.months(*SPAN)
    rows = []
    for pname, shapes in base.PRODUCT_SETS.items():
        _, areas, X = base.panel(data, shapes, SPAN)
        r = read(ms, X)
        rows.append({"products": pname, "countries": areas, "level_products": list(shapes), **r})
    seen = [all(h > f for h, f, s in zip(r["level_hike"], r["level_free_max"], r["level_products"]) if s in base.LOANS)
            for r in rows if r["products"] in ("all", "loans")]
    crit = [
        {"name": "B128-4", "kind": "known_answer",
         "statement": "across the hike window every loan product's euro-area mean level moves more than it does in any dose-free window of the same length",
         "passed": bool(seen) and all(seen),
         "detail": "; ".join(f"{r['products']}: hike {r['level_hike']} vs dose-free max {r['level_free_max']}" for r in rows)},
        {"name": "B128-5", "kind": "own_reading",
         "statement": "print, per product set, the interaction's change across the hike and cut windows against the dose-free floor, and the cut-on-hike slope against the rival's -0.44 and the dose-free pairs",
         "passed": bool(rows) and all(r["null_pairs"] > 0 and r["windows_hike"] > 0 for r in rows),
         "detail": "; ".join(f"{r['products']}: R hike {r['R_hike']} (floor max {r['floor_hike_max']}), R cut {r['R_cut']} "
                             f"(floor max {r['floor_cut_max']}), rho {r['rho']}, slope {r['slope']} vs rival {r['rival_slope']}, "
                             f"dose-free rho 5-95% [{r['null_rho_p05']}, {r['null_rho_p95']}]" for r in rows)},
    ]
    return {"stage": "B128", "arm": "A", "instrument": "long difference against dose-free windows", "rows": rows,
            "criteria": crit, "config": {"span": SPAN, "hike": HIKE, "cut": CUT, "dose_free": DOSE_FREE},
            "source": {"rates": "data/raw/b128/mir_B_*.csv"}}


def selftest() -> None:
    rng = np.random.default_rng(1)
    ms = base.months(*SPAN)
    dfr = {"2022-07": .5, "2022-09": .75, "2022-11": .75, "2022-12": .5, "2023-02": .5, "2023-03": .5, "2023-05": .25,
           "2023-06": .25, "2023-08": .25, "2023-09": .25, "2024-06": -.25, "2024-09": -.25, "2024-10": -.25,
           "2024-12": -.25, "2025-02": -.25, "2025-03": -.25, "2025-04": -.25, "2025-06": -.25}
    path = np.cumsum([dfr.get(m, 0.0) for m in ms])[:, None, None]
    n, g = 12, 6
    drift = rng.normal(0, 0.03, (len(ms), n, g)).cumsum(axis=0)
    flat = 3 + path * (rng.uniform(.4, 1.2, n)[:, None] + rng.uniform(.2, 1, g)[None, :]) / 2 + drift
    inter = flat + path * rng.normal(0, 0.3, (n, g))[None]
    a, b = read(ms, flat), read(ms, inter)
    assert a["R_hike"] <= a["floor_hike_max"] * 1.5, a                     # no interaction pass-through: near the floor
    assert b["R_hike"] > 3 * b["floor_hike_max"], b                         # interaction pass-through: far above it
    assert b["slope"] < -0.3 and b["rho"] < b["null_rho_p05"], b            # and the cut undoes it at about -0.44
    assert all(h > f for h, f in zip(a["level_hike"], a["level_free_max"])), a   # the known answer is seen
    blind = read(ms, 3 + drift)
    assert not all(h > f for h, f in zip(blind["level_hike"], blind["level_free_max"]))  # no pass-through: not seen
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    out = build(base.load_rates())
    for r in out["rows"]:
        print(f"== {r['products']}: {len(r['countries'])} countries, {r['cells']} cells")
        print(f"   interaction R: hike {r['R_hike']}  (dose-free {r['windows_hike']} windows, p90 {r['floor_hike_p90']}, max {r['floor_hike_max']})"
              f";  cut {r['R_cut']}  (dose-free max {r['floor_cut_max']})")
        print(f"   cut on hike: rho {r['rho']}, slope {r['slope']} (rival {r['rival_slope']}); dose-free pairs {r['null_pairs']}, "
              f"rho 5-95% [{r['null_rho_p05']}, {r['null_rho_p95']}], share at or below observed {r['null_rho_share_at_or_below']}")
        print(f"   level |change| hike {r['level_hike']}\n   level dose-free max {r['level_free_max']}")
    for c in out["criteria"]:
        print(f"{c['name']} [{c['kind']}] {'PASS' if c['passed'] else 'FAIL'}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
