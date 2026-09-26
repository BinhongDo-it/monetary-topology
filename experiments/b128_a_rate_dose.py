"""B128 arm A: does the country-by-product interaction of euro area bank rates respond to ECB rate changes?

The object. For each month, take the table of new-business rates r[i, g] (country i, product g) and remove
its row means and column means; what is left, E[i, g], is the interaction. Every square
(r_ig - r_jg) - (r_ih - r_jh) is a sum of interaction cells, and the interaction is zero exactly when every
square is, so reading E reads all squares at once without choosing a reference country or product. The
double demeaning also takes out anything that moves every product of one country together (a sovereign
shock, a country-wide pass-through speed) and anything that moves one product everywhere.

The framework says a rate change moves the potential, and a potential sums to zero round a loop, so E does not
respond to the dose. The rival (impaired transmission: pass-through coefficients that differ by country and
product) says E moves by the interaction of those coefficients times the dose.

The reading. For each cell, regress the monthly change of E on the deposit facility rate change of this month
and the previous L months; the cell's cumulative response is the sum of those coefficients. S is the root mean
square of the cumulative responses over cells. The floor: shift the dose series round the window by every
possible number of months and recompute S; p is the share of shifts at or above the observed S. The shifts are
exhaustive, so there is no seed.

Instrument check with a known answer: the same regression on the level of each product's euro-area mean rate
must see the hikes; if it cannot, a flat interaction says nothing.

Knobs, all printed (`11f`): window, lag L, product set. Countries are those in the euro area in every month of
the window (accession on 1 January of the year printed on the ECB's euro area page, cached at
data/raw/b128/ecb_euro_area_members.html) that report every product of the set in every month.

    python experiments/b128_a_rate_dose.py
    python experiments/b128_a_rate_dose.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b128"
OUT = ROOT / "results" / "b128_a_rate_dose.json"

JOINED = {"AT": 1999, "BE": 1999, "DE": 1999, "ES": 1999, "FI": 1999, "FR": 1999, "IE": 1999, "IT": 1999,
          "LU": 1999, "NL": 1999, "PT": 1999, "GR": 2001, "SI": 2007, "CY": 2008, "MT": 2008, "SK": 2009,
          "EE": 2011, "LV": 2014, "LT": 2015, "HR": 2023, "BG": 2026}
LOANS = ("A2A_F_R_2_2240", "A2A_F_R_3_2240", "A2A_F_R_1_2240", "A2C_F_R_A_2250", "A2B_F_R_A_2250", "A2D_F_R_A_2250")
DEPOSITS = ("L22_F_R_A_2250", "L22_F_R_A_2240", "L21_A_R_A_2250", "L21_A_R_A_2240")
PRODUCT_SETS = {"all": LOANS + DEPOSITS, "loans": LOANS, "deposits": DEPOSITS}
WINDOWS = {"hikes": ("2021-07", "2024-05"), "hikes_and_cuts": ("2021-01", "2025-06")}
LAGS = (0, 1, 2, 3)


def months(a: str, b: str) -> list[str]:
    y, m = int(a[:4]), int(a[5:])
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def load_rates() -> dict[tuple[str, str], dict[str, float]]:
    data: dict[tuple[str, str], dict[str, float]] = {}
    for f in sorted(glob.glob(str(RAW / "mir_B_*.csv"))):
        shape = os.path.basename(f)[6:-10]  # mir_B_<shape>_EUR_N.csv -> <shape>
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["OBS_VALUE"]:
                    data.setdefault((r["REF_AREA"], shape), {})[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    return data


def load_dose() -> dict[str, float]:
    """Deposit facility rate change summed by calendar month of its effective date."""
    dose: dict[str, float] = {}
    with open(RAW / "fm_keyrates.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["KEY"] == "FM.B.U2.EUR.4F.KR.DFR.CHG" and r["OBS_VALUE"]:
                m = r["TIME_PERIOD"][:7]
                dose[m] = dose.get(m, 0.0) + float(r["OBS_VALUE"])
    return dose


def panel(data, shapes, window) -> tuple[list[str], list[str], np.ndarray]:
    ms = months(*window)
    first_year = int(window[0][:4])
    areas = sorted(a for a, y in JOINED.items() if y <= first_year
                   and all(all(m in data.get((a, s), {}) for m in ms) for s in shapes))
    X = np.array([[[data[(a, s)][m] for s in shapes] for a in areas] for m in ms])  # month x country x product
    return ms, areas, X


def interaction(X: np.ndarray) -> np.ndarray:
    return X - X.mean(axis=2, keepdims=True) - X.mean(axis=1, keepdims=True) + X.mean(axis=(1, 2), keepdims=True)


def lagged(dose: np.ndarray, L: int) -> np.ndarray:
    cols = [np.concatenate([np.zeros(k), dose[:len(dose) - k]]) for k in range(L + 1)]
    return np.column_stack([np.ones(len(dose))] + cols)


def cumulative(Y: np.ndarray, dose: np.ndarray, L: int) -> np.ndarray:
    """Y: time x k. Returns the k cumulative responses (sum of lag coefficients), first L months dropped."""
    Z = lagged(dose, L)[L:]
    b = np.linalg.lstsq(Z, Y[L:], rcond=None)[0]
    return b[1:].sum(axis=0)


def read(X: np.ndarray, dose: np.ndarray, L: int) -> dict:
    E = interaction(X)
    dE = np.diff(E, axis=0).reshape(E.shape[0] - 1, -1)
    d = dose[1:]
    s_obs = float(np.sqrt(np.mean(cumulative(dE, d, L) ** 2)))
    null = [float(np.sqrt(np.mean(cumulative(dE, np.roll(d, k), L) ** 2))) for k in range(1, len(d))]
    level = np.diff(X.mean(axis=1), axis=0)  # euro-area mean of each product, month changes
    lv = cumulative(level, d, L)
    lv_null = np.array([cumulative(level, np.roll(d, k), L) for k in range(1, len(d))])
    return {"S": round(s_obs, 4), "p": round(sum(n >= s_obs for n in null) / len(null), 4),
            "null_p90": round(float(np.quantile(null, 0.9)), 4), "shifts": len(null),
            "cells": int(dE.shape[1]), "identity_max": float(np.abs(E.sum(axis=1)).max() + np.abs(E.sum(axis=2)).max()),
            "level_response": [round(float(v), 3) for v in lv],
            "level_p": [round(float((lv_null[:, j] >= lv[j]).mean()), 4) for j in range(len(lv))],
            "cell_response": cumulative(dE, d, L)}


def state(p: float) -> str:
    return "responds" if p <= 0.10 else "no response"


MAPPING = {"responds in every setting": "the interaction moves with the dose",
           "no response in every setting": "the interaction does not move with the dose",
           "differs across settings": "unread (11f), no verdict"}


def build(data, dose_by_month) -> dict:
    rows = []
    for wname, window in WINDOWS.items():
        for pname, shapes in PRODUCT_SETS.items():
            ms, areas, X = panel(data, shapes, window)
            dose = np.array([dose_by_month.get(m, 0.0) for m in ms])
            for L in LAGS:
                r = read(X, dose, L)
                cr = r.pop("cell_response").reshape(len(areas), len(shapes))
                top = sorted(((abs(v), a, s, round(float(v), 3)) for a, row in zip(areas, cr)
                              for s, v in zip(shapes, row)), reverse=True)[:5]
                rows.append({"window": wname, "products": pname, "lag": L, "countries": areas,
                             "dose_total": round(float(dose.sum()), 2), **r, "state": state(r["p"]),
                             "largest_cells": [[a, s, v] for _, a, s, v in top],
                             "level_products": list(shapes)})
    states = {r["state"] for r in rows}
    overall = ("responds in every setting" if states == {"responds"} else
               "no response in every setting" if states == {"no response"} else "differs across settings")
    loan_level_seen = [all(p <= 0.10 for p, s in zip(r["level_p"], r["level_products"]) if s in LOANS)
                       for r in rows if r["products"] in ("all", "loans")]
    crit = [
        {"name": "B128-1", "kind": "instrument",
         "statement": "the interaction sums to zero over countries and over products in every month, and every panel is balanced",
         "passed": bool(rows) and all(r["identity_max"] < 1e-9 and len(r["countries"]) >= 3 for r in rows),
         "detail": f"largest identity residual {max(r['identity_max'] for r in rows):.2e}; countries per setting "
                   f"{sorted({len(r['countries']) for r in rows})}"},
        {"name": "B128-2", "kind": "known_answer",
         "statement": "the same regression on each loan product's euro-area mean rate sees the dose (p <= 0.10 against its own shifts)",
         "passed": bool(loan_level_seen) and all(loan_level_seen),
         "detail": f"{sum(loan_level_seen)} of {len(loan_level_seen)} settings see every loan product move"},
        {"name": "B128-3", "kind": "own_reading",
         "statement": "print S, its shift floor and p for every window, product set and lag, and map the three states",
         "passed": None if overall == "differs across settings" else overall == "no response in every setting",
         "detail": f"state over {len(rows)} settings: {overall}; mapping: " + "; ".join(f"{k} -> {v}" for k, v in MAPPING.items())},
    ]
    return {"stage": "B128", "arm": "A", "rows": rows, "overall": overall, "mapping": MAPPING, "criteria": crit,
            "config": {"windows": WINDOWS, "lags": list(LAGS), "product_sets": {k: list(v) for k, v in PRODUCT_SETS.items()},
                       "dose": "FM.B.U2.EUR.4F.KR.DFR.CHG summed by calendar month", "state_line_p": 0.10},
            "source": {"rates": "data/raw/b128/mir_B_*.csv", "dose": "data/raw/b128/fm_keyrates.csv"}}


def selftest() -> None:
    rng = np.random.default_rng(0)
    ms = months("2021-01", "2024-06")
    dose = np.zeros(len(ms))
    for k, v in ((18, .5), (20, .75), (22, .75), (23, .5), (25, .5), (26, .5), (28, .25), (29, .25), (31, .25), (33, .25)):
        dose[k] = v
    n, g = 12, 6
    base = rng.normal(3, 1, (n, g))
    beta_country = rng.uniform(0.4, 1.2, n)[:, None] * np.ones((1, g))       # country-wide pass-through only
    beta_product = np.ones((n, 1)) * rng.uniform(0.2, 1.0, g)[None, :]
    noise = lambda: rng.normal(0, 0.02, (len(ms), n, g)).cumsum(axis=0) * 0.3
    path = np.cumsum(dose)[:, None, None]
    X_flat = base + path * (beta_country + beta_product)[None] / 2 + noise()
    X_int = X_flat + path * rng.normal(0, 0.3, (n, g))[None]                 # country-by-product pass-through
    flat, inter = read(X_flat, dose, 1), read(X_int, dose, 1)
    assert flat["identity_max"] < 1e-9
    assert flat["p"] > 0.10, flat                  # country-wide and product-wide pass-through do not show up
    assert inter["p"] <= 0.10 and inter["S"] > 3 * flat["S"], (inter, flat)   # interaction pass-through does
    assert all(p <= 0.10 for p in flat["level_p"]), flat["level_p"]            # the known answer is seen
    dead = read(base + noise(), dose, 1)
    assert not all(p <= 0.10 for p in dead["level_p"])                          # no pass-through: known answer fails
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    out = build(load_rates(), load_dose())
    print(f"{'window':<15}{'products':<9}{'L':>2}{'N':>4}{'cells':>6}{'S':>8}{'p90':>8}{'p':>7}  state      largest cells")
    for r in out["rows"]:
        print(f"{r['window']:<15}{r['products']:<9}{r['lag']:>2}{len(r['countries']):>4}{r['cells']:>6}{r['S']:>8.4f}"
              f"{r['null_p90']:>8.4f}{r['p']:>7.3f}  {r['state']:<11}{r['largest_cells'][:2]}")
    for r in out["rows"]:
        if r["products"] == "all" and r["lag"] == 1:
            print(f"level response, {r['window']}: " + ", ".join(f"{s[:8]} {v:+.2f} (p {p})" for s, v, p in
                                                             zip(r["level_products"], r["level_response"], r["level_p"])))
    for c in out["criteria"]:
        flag = "no verdict" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{c['name']} [{c['kind']}] {flag}: {c['detail']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
