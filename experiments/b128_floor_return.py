"""B128: do household overnight deposit rates go back to zero in the 2024-25 cuts where the lag account says?

R5 read that most countries' household overnight deposit rates reached zero near a deposit facility rate of -0.40
on the way down (2012-2021) and left it at +2 to +4 on the way up (2022-23). Two readings of that gap, registered in
the design (cell 1, second addendum) before the 2024-26 levels were read:

  lag only     a country returns to zero once the policy rate has fallen back below the level at which it left
               (L_up), after a delay: those with L_up >= 2.50 return while the rate sits at 2.00 (2025-06 to
               2026-05); those with L_up <= 2.00 stay above zero
  hysteresis   once off the floor a country stays off until the rate is back near where it reached zero, so none
               returns while the rate is at or above 2.00

Within one country from 2022 to 2026, and no country entered or left an assistance programme or capital controls in
that span, so the sovereign graph is the same on both sides of the comparison. CY, GR and PT never left zero; HR and
BG were not in the euro area for both parts. Knob: the zero line, 0.05 and 0.10.

    python experiments/b128_floor_return.py
    python experiments/b128_floor_return.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import b128_a_rate_dose as base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b128_floor_return.json"
PRODUCT = "L21_A_R_A_2250"
UP = ("2022-06", "2023-12")
BACK = ("2024-06", "2026-05")
LINES = (0.05, 0.10)
CUT_AT = 2.50
OUT_OF_TEST = {"HR", "BG"}

STATE_MAP = {"every L_up >= 2.50 country returns and every L_up <= 2.00 country stays": "lag only",
             "no country returns": "hysteresis",
             "anything else": "neither branch, printed, no mapping"}


def dfr_by_month() -> dict[str, float]:
    lev = {}
    with open(ROOT / "data" / "raw" / "b128" / "fm_keyrates.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["KEY"] == "FM.B.U2.EUR.4F.KR.DFR.LEV" and r["OBS_VALUE"]:
                lev[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    out, cur = {}, None
    days = sorted(lev)
    for m in base.months("1999-01", "2026-12"):
        for d in days:
            if d[:7] <= m:
                cur = lev[d]
        out[m] = cur
    return out


def classify(series: dict[str, dict[str, float]], dfr: dict[str, float], line: float) -> dict:
    rows = []
    for a, s in sorted(series.items()):
        up = next((m for m in base.months(*UP) if m in s and s[m] > line), None)
        if up is None:
            rows.append({"country": a, "L_up": None, "left_zero": None, "returns": None})
            continue
        back = next((m for m in base.months(*BACK) if m in s and s[m] <= line), None)
        low = min((s[m] for m in base.months(*BACK) if m in s), default=None)
        rows.append({"country": a, "left_zero": up, "L_up": dfr[up], "returns": back is not None,
                     "returned": back, "lowest_after": low})
    tested = [r for r in rows if r["L_up"] is not None]
    high = [r for r in tested if r["L_up"] >= CUT_AT]
    low_ = [r for r in tested if r["L_up"] < CUT_AT]
    if tested and all(r["returns"] for r in high) and not any(r["returns"] for r in low_) and high:
        state = "lag only"
    elif tested and not any(r["returns"] for r in tested):
        state = "hysteresis"
    else:
        state = "neither branch"
    return {"line": line, "rows": rows, "state": state,
            "high_return": f"{sum(r['returns'] for r in high)}/{len(high)}",
            "low_return": f"{sum(r['returns'] for r in low_)}/{len(low_)}"}


def build(series, dfr) -> dict:
    reads = [classify(series, dfr, ln) for ln in LINES]
    states = {r["state"] for r in reads}
    agreed = states.pop() if len(states) == 1 else "the line decides"
    crit = [{"name": "B128-10", "kind": "own_reading",
             "statement": "which of the two registered readings of the R5 gap the 2024-26 levels give, at both zero lines",
             "passed": None if agreed in ("the line decides", "neither branch") else True,
             "state": agreed, "state_map": STATE_MAP,
             "detail": "; ".join(f"line {r['line']}: {r['state']} (L_up >= 2.50 returned {r['high_return']}, "
                                 f"L_up < 2.50 returned {r['low_return']})" for r in reads)}]
    return {"stage": "B128", "reading": "return to the floor in the 2024-25 cuts", "reads": reads, "criteria": crit,
            "config": {"product": PRODUCT, "up": UP, "back": BACK, "lines": LINES, "cut_at": CUT_AT,
                       "out_of_test": sorted(OUT_OF_TEST)},
            "source": {"rates": "data/raw/b128/mir_B_L21_A_R_A_2250_EUR_N.csv", "dfr": "data/raw/b128/fm_keyrates.csv"}}


def selftest() -> None:
    ms = base.months("2022-01", "2026-07")
    dfr = {m: (-0.5 if m < "2022-09" else 0.75 if m < "2022-12" else 2.0 if m < "2023-04" else 3.0 if m < "2023-10"
               else 4.0 if m < "2024-07" else 3.0 if m < "2025-01" else 2.0) for m in ms}
    def country(left: str, back: str | None) -> dict[str, float]:
        return {m: (0.0 if m < left or (back and m >= back) else 0.5) for m in ms}
    lag = {"A": country("2023-05", "2025-03"), "B": country("2022-10", None)}   # high L_up returns, low stays
    hyst = {"A": country("2023-05", None), "B": country("2022-10", None)}
    mixed = {"A": country("2023-05", None), "B": country("2022-10", "2025-03")}
    assert classify(lag, dfr, 0.05)["state"] == "lag only"
    assert classify(hyst, dfr, 0.05)["state"] == "hysteresis"
    assert classify(mixed, dfr, 0.05)["state"] == "neither branch"
    assert build(mixed, dfr)["criteria"][0]["passed"] is None
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    data = base.load_rates()
    series = {a: s for (a, p), s in data.items() if p == PRODUCT and a in base.JOINED and a not in OUT_OF_TEST}
    out = build(series, dfr_by_month())
    for r in out["reads"]:
        print(f"== line {r['line']}: {r['state']}  (L_up >= 2.50 returned {r['high_return']}, L_up < 2.50 returned {r['low_return']})")
        for x in sorted(r["rows"], key=lambda x: (x["L_up"] is None, x["L_up"] or 0)):
            if x["L_up"] is None:
                print(f"   {x['country']}: never left zero in 2022-23")
            else:
                print(f"   {x['country']}: left {x['left_zero']} at {x['L_up']:+.2f}; 2024-06..2026-05 lowest {x['lowest_after']:.2f}; "
                      f"{'back at zero ' + x['returned'] if x['returns'] else 'stays above'}")
    c = out["criteria"][0]
    print(f"{c['name']} [{c['kind']}] {'no verdict' if c['passed'] is None else 'PASS'}: {c['state']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
