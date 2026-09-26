"""B128 arm B: TLTRO, a tool whose rule splits both by country (take-up) and by product (house purchase out).

Registered in the design (cell 1, "B 臂落定") before any of the 2020-21 readings: in each country take the gap
between eligible lending rates (corporate loans in three size bands and consumer credit, optionally other household
lending) and the house-purchase rate, remove the cross-country mean each month, and read its change across the
TLTRO III recalibration against each country's take-up. The framework says the countries that took more see their
gap fall more: a negative cross-country correlation.

Dose, demand side (chosen by the banks, the same weakness as B121 R8): the increase in each national central bank's
longer-term refinancing (ILM A050200) from 2020-02 to the window's end, over the country's eligible loan stock in
2019-02 (BSI NFC loans A20 plus household consumption A21 plus household other A23; the TLTRO III allowance rule's
reference date is 2019-02-28).

Floor: the same take-up vector against the gap's change over every window of the same length between 2017-04 and
2019-06, when no new TLTRO operation ran; it carries any country trend that lines up with take-up.

Knobs (`11f`): window end (2020-12, 2021-03, 2021-06), other household lending in or out of the eligible side, and
the numerator (ILM longer-term refinancing, or BSI total borrowing from the Eurosystem).

    python experiments/b128_b_tltro.py
    python experiments/b128_b_tltro.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

import b128_a_rate_dose as base

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b128"
OUT = ROOT / "results" / "b128_b_tltro.json"
START = "2020-02"
ENDS = ("2020-12", "2021-03", "2021-06")
PLACEBO = ("2017-04", "2019-06")
STOCK_MONTH = "2019-02"
ELIGIBLE = ("A2A_F_R_2_2240", "A2A_F_R_3_2240", "A2A_F_R_1_2240", "A2B_F_R_A_2250")
OTHER = "A2D_F_R_A_2250"
HOUSE = "A2C_F_R_A_2250"
NUMERATORS = {"ILM longer-term": "ilm_ltro.csv", "BSI Eurosystem borrowing": "bsi_eurosystem_borrowing.csv"}
STATE_MAP = {"negative past the floor in every setting": "pass: the gap fell more where more was taken",
             "positive past the floor in every setting": "fail: the gap rose more where more was taken",
             "anything else": "no verdict (11c, 11f)"}


def by_area(fname: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with open(RAW / fname, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["OBS_VALUE"]:
                out.setdefault(r["REF_AREA"], {})[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    return out


def corr_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x, y = x - x.mean(), y - y.mean()
    return float((x @ y) / np.sqrt((x @ x) * (y @ y))), float((x @ y) / (x @ x))


def gaps(data, areas, eligible, months) -> np.ndarray:
    """month x country: mean eligible rate minus house-purchase rate, cross-country mean removed."""
    g = np.array([[np.mean([data[(a, s)][m] for s in eligible]) - data[(a, HOUSE)][m] for a in areas] for m in months])
    return g - g.mean(axis=1, keepdims=True)


def read(G: np.ndarray, ms: list[str], dose: np.ndarray, end: str) -> dict:
    ix = {m: i for i, m in enumerate(ms)}
    a, b = ix[START], ix[end]
    L = b - a
    rho, slope = corr_slope(dose, G[b] - G[a])
    p0, p1 = ix[PLACEBO[0]], ix[PLACEBO[1]]
    null = np.array([corr_slope(dose, G[s + L] - G[s])[0] for s in range(p0, p1 - L + 1)])
    return {"end": end, "rho": round(rho, 4), "slope_pp_per_unit": round(slope, 4), "placebo_windows": len(null),
            "null_p05": round(float(np.quantile(null, 0.05)), 4), "null_p95": round(float(np.quantile(null, 0.95)), 4),
            "null_min": round(float(null.min()), 4), "null_max": round(float(null.max()), 4)}


def state(r: dict) -> str:
    if r["rho"] < r["null_min"]:
        return "negative past the floor"
    if r["rho"] > r["null_max"]:
        return "positive past the floor"
    return "inside the floor"


def verdict(states: list[str]) -> tuple[bool | None, str]:
    if set(states) == {"negative past the floor"}:
        return True, "negative past the floor in every setting"
    if set(states) == {"positive past the floor"}:
        return False, "positive past the floor in every setting"
    return None, "anything else"


def build(data) -> dict:
    ms = base.months("2016-06", "2021-06")
    loans = [by_area(f) for f in ("bsi_loans_nfc.csv", "bsi_loans_hh_consumption.csv", "bsi_loans_hh_other.csv")]
    rows = []
    for with_other in (False, True):
        eligible = ELIGIBLE + ((OTHER,) if with_other else ())
        areas = sorted(a for a, y in base.JOINED.items() if y <= 2016
                       and all(all(m in data.get((a, s), {}) for m in ms) for s in eligible + (HOUSE,))
                       and all(STOCK_MONTH in l.get(a, {}) for l in loans))
        G = gaps(data, areas, eligible, ms)
        stock = np.array([sum(l[a][STOCK_MONTH] for l in loans) for a in areas])
        for nname, nfile in NUMERATORS.items():
            num = by_area(nfile)
            keep = [i for i, a in enumerate(areas) if all(m in num.get(a, {}) for m in (START,) + ENDS)]
            for end in ENDS:
                dose = np.array([(num[areas[i]][end] - num[areas[i]][START]) / stock[i] for i in keep])
                r = read(G[:, keep], ms, dose, end)
                rows.append({"other_household_in": with_other, "numerator": nname, "countries": [areas[i] for i in keep],
                             "dose": {areas[i]: round(float(d), 4) for i, d in zip(keep, dose)}, **r, "state": state(r)})
    passed, st = verdict([r["state"] for r in rows])
    crit = [{"name": "B128-11", "kind": "own_reading",
             "statement": "across countries, the eligible-minus-house-purchase gap falls more where more TLTRO III was taken, past the floor from dose-free windows",
             "passed": passed, "state": st, "state_map": STATE_MAP,
             "detail": "; ".join(f"{r['numerator']}, other {'in' if r['other_household_in'] else 'out'}, to {r['end']}: "
                                 f"rho {r['rho']} (floor {r['null_min']} to {r['null_max']}, {r['placebo_windows']} windows) -> {r['state']}"
                                 for r in rows)}]
    return {"stage": "B128", "arm": "B", "rows": rows, "criteria": crit,
            "config": {"start": START, "ends": ENDS, "placebo": PLACEBO, "stock_month": STOCK_MONTH, "eligible": ELIGIBLE,
                       "other": OTHER, "house": HOUSE, "numerators": NUMERATORS},
            "source": {"rates": "data/raw/b128/mir_B_*.csv", "dose": list(NUMERATORS.values()),
                       "stock": ["bsi_loans_nfc.csv", "bsi_loans_hh_consumption.csv", "bsi_loans_hh_other.csv"],
                       "rule": "ECB Decision 2014/34 art. 1(3), data/raw/b128/lit/ecb_decision_2014_34.html"}}


def selftest() -> None:
    rng = np.random.default_rng(3)
    ms = base.months("2016-06", "2021-06")
    n = 15
    dose = rng.uniform(0, 0.3, n)
    drift = rng.normal(0, 0.03, (len(ms), n)).cumsum(axis=0)
    step = np.array([1.0 if m > START else 0.0 for m in ms])[:, None]
    moved = drift - step * dose[None, :] * 3.0
    moved -= moved.mean(axis=1, keepdims=True)
    still = drift - drift.mean(axis=1, keepdims=True)
    assert state(read(moved, ms, dose, "2021-03")) == "negative past the floor"
    assert state(read(still, ms, dose, "2021-03")) == "inside the floor"
    assert state(read(-moved, ms, dose, "2021-03")) == "positive past the floor"
    assert verdict(["negative past the floor"] * 3)[0] is True
    assert verdict(["negative past the floor", "inside the floor"])[0] is None
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    out = build(base.load_rates())
    for r in out["rows"]:
        print(f"{r['numerator']:<25} other {'in ' if r['other_household_in'] else 'out'} to {r['end']}: N {len(r['countries'])}  "
              f"rho {r['rho']:+.3f} slope {r['slope_pp_per_unit']:+.3f}  floor [{r['null_min']:+.3f}, {r['null_max']:+.3f}] "
              f"({r['placebo_windows']} windows) -> {r['state']}")
    r0 = out["rows"][1]
    print("dose (ILM, other out, to 2021-03):", dict(sorted(r0["dose"].items(), key=lambda kv: -kv[1])))
    c = out["criteria"][0]
    print(f"{c['name']} [{c['kind']}] {'no verdict' if c['passed'] is None else ('PASS' if c['passed'] else 'FAIL')}: {c['state']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
