"""B128 arm B, second dose: the national guarantee schemes' envelopes, read beside TLTRO take-up.

Registered in the design (cell 1, "B 臂第二个剂量") before this reading. Each sovereign wrote an envelope for its
COVID-19 loan guarantee scheme in spring 2020 (ECB Occasional Paper 257, tables A.3 and A.4). The guarantee falls on
corporate loans only, so where the envelope is large relative to corporate lending, corporate loan rates should fall
against house-purchase rates: b_G < 0. TLTRO take-up is the second regressor.

Cross-country regression dG_i = a + b_T * TLTRO_i + b_G * guarantee_i, over 2020-02 to the window's end. Floor: the
same two dose vectors against dG over every same-length window in 2017-04 to 2019-06. The correlation of the two
doses is printed first; if they move together the two coefficients cannot be told apart and that is said.

    python experiments/b128_b_guarantees.py
    python experiments/b128_b_guarantees.py --selftest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import b128_a_rate_dose as base
import b128_b_tltro as tl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b128_b_guarantees.json"
OUT_TAKEUP = ROOT / "results" / "b128_b_takeup.json"
TAKEUP_FILE = ROOT / "data" / "raw" / "b128" / "eba_pgs_volumes.csv"
TAKEUP_Q = {"2020-12": "Dec-20", "2021-03": "Mar-21", "2021-06": "Jun-21"}
# ECB Occasional Paper 257, tables A.3 and A.4, EUR billions; CY lists no scheme
ENVELOPE = {"AT": 15, "BE": 50, "CY": 0, "DE": 822, "EE": 1.8, "ES": 100, "FI": 12, "FR": 300, "GR": 2, "IE": 2,
            "IT": 307, "LU": 2.5, "LT": 0.7, "LV": 0.25, "MT": 0.35, "NL": 12.8, "PT": 4.2, "SK": 4.5, "SI": 2}
NFC = ("A2A_F_R_2_2240", "A2A_F_R_3_2240", "A2A_F_R_1_2240")
OBJECTS = {"eligible minus house": tl.ELIGIBLE, "corporate minus house": NFC}
STATE_MAP = {"b_G negative past the floor in every setting": "pass",
             "b_G positive past the floor in every setting": "fail",
             "anything else": "no verdict (11c, 11f)"}


def load_takeup() -> dict[str, dict[str, float]]:
    """EBA dashboard volumes of newly originated loans under public guarantee schemes, bn EUR; '-' read as 0."""
    import csv
    out: dict[str, dict[str, float]] = {}
    with open(TAKEUP_FILE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["country"], {})[r["quarter"]] = 0.0 if r["bn_eur"] == "-" else float(r["bn_eur"])
    return out


def ols2(x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    X = np.column_stack([np.ones(len(y)), x1, x2])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(b[1]), float(b[2])


def read(G, ms, t_dose, g_dose, end) -> dict:
    ix = {m: i for i, m in enumerate(ms)}
    a, b = ix[tl.START], ix[end]
    L = b - a
    bT, bG = ols2(t_dose, g_dose, G[b] - G[a])
    p0, p1 = ix[tl.PLACEBO[0]], ix[tl.PLACEBO[1]]
    null = np.array([ols2(t_dose, g_dose, G[s + L] - G[s]) for s in range(p0, p1 - L + 1)])
    return {"end": end, "b_T": round(bT, 4), "b_G": round(bG, 4), "windows": len(null),
            "b_T_floor": [round(float(null[:, 0].min()), 4), round(float(null[:, 0].max()), 4)],
            "b_G_floor": [round(float(null[:, 1].min()), 4), round(float(null[:, 1].max()), 4)]}


def state_of(v: float, lo_hi: list[float]) -> str:
    return "negative past the floor" if v < lo_hi[0] else "positive past the floor" if v > lo_hi[1] else "inside the floor"


def build(data, mode: str = "envelope") -> dict:
    ms = base.months("2016-06", "2021-06")
    nfc_stock = tl.by_area("bsi_loans_nfc.csv")
    rows = []
    for oname, eligible in OBJECTS.items():
        areas = sorted(a for a, y in base.JOINED.items() if y <= 2016 and a in ENVELOPE
                       and all(all(m in data.get((a, s), {}) for m in ms) for s in eligible + (tl.HOUSE,))
                       and "2019-12" in nfc_stock.get(a, {}))
        G = tl.gaps(data, areas, eligible, ms)
        loans = [tl.by_area(f) for f in ("bsi_loans_nfc.csv", "bsi_loans_hh_consumption.csv", "bsi_loans_hh_other.csv")]
        stock = np.array([sum(l[a][tl.STOCK_MONTH] for l in loans) for a in areas])
        g_dose_all = np.array([ENVELOPE[a] * 1000.0 / nfc_stock[a]["2019-12"] for a in areas])
        takeup = load_takeup() if mode == "takeup" else None
        for nname, nfile in tl.NUMERATORS.items():
            num = tl.by_area(nfile)
            keep = [i for i, a in enumerate(areas) if all(m in num.get(a, {}) for m in (tl.START,) + tl.ENDS)]
            for end in tl.ENDS:
                t_dose = np.array([(num[areas[i]][end] - num[areas[i]][tl.START]) / stock[i] for i in keep])
                if takeup is None:
                    g_dose = g_dose_all[keep]
                else:
                    g_dose = np.array([takeup.get(areas[i], {}).get(TAKEUP_Q[end], 0.0) * 1000.0 / nfc_stock[areas[i]]["2019-12"]
                                       for i in keep])
                r = read(G[:, keep], ms, t_dose, g_dose, end)
                rows.append({"object": oname, "numerator": nname, "countries": [areas[i] for i in keep],
                             "dose_corr": round(float(np.corrcoef(t_dose, g_dose)[0, 1]), 4),
                             "guarantee_dose": {areas[i]: round(float(d), 4) for i, d in zip(keep, g_dose)},
                             **r, "b_G_state": state_of(r["b_G"], r["b_G_floor"]),
                             "b_T_state": state_of(r["b_T"], r["b_T_floor"])})
    states = {r["b_G_state"] for r in rows}
    if states == {"negative past the floor"}:
        passed, st = True, "b_G negative past the floor in every setting"
    elif states == {"positive past the floor"}:
        passed, st = False, "b_G positive past the floor in every setting"
    else:
        passed, st = None, "anything else"
    crit = [{"name": "B128-12" if mode == "envelope" else "B128-13", "kind": "own_reading",
             "statement": "with TLTRO take-up held in the same regression, the gap falls more where the sovereign wrote a larger guarantee envelope (b_G < 0), past the floor",
             "passed": passed, "state": st, "state_map": STATE_MAP,
             "detail": "; ".join(f"{r['object']}, {r['numerator']}, to {r['end']}: dose corr {r['dose_corr']}, b_G {r['b_G']} "
                                 f"(floor {r['b_G_floor']}) -> {r['b_G_state']}, b_T {r['b_T']} (floor {r['b_T_floor']}) -> {r['b_T_state']}"
                                 for r in rows)}]
    return {"stage": "B128", "arm": "B", "dose": mode, "rows": rows, "criteria": crit,
            "config": {"envelope_eur_bn": ENVELOPE, "envelope_source": "ECB Occasional Paper 257, tables A.3 and A.4",
                       "objects": {k: list(v) for k, v in OBJECTS.items()}, "stock_for_guarantee": "BSI A20 NFC loans, 2019-12"},
            "source": {"rates": "data/raw/b128/mir_B_*.csv", "paper": "data/raw/b128/lit/ecb_op257.pdf",
                       "takeup": "data/raw/b128/eba_pgs_volumes.csv" if mode == "takeup" else None}}


def selftest() -> None:
    rng = np.random.default_rng(4)
    ms = base.months("2016-06", "2021-06")
    n = 16
    t_dose, g_dose = rng.uniform(0, 0.3, n), rng.uniform(0, 1.0, n)
    drift = rng.normal(0, 0.03, (len(ms), n)).cumsum(axis=0)
    step = np.array([1.0 if m > tl.START else 0.0 for m in ms])[:, None]
    moved = drift - step * g_dose[None, :] * 1.0
    moved -= moved.mean(axis=1, keepdims=True)
    still = drift - drift.mean(axis=1, keepdims=True)
    r1, r0 = read(moved, ms, t_dose, g_dose, "2021-03"), read(still, ms, t_dose, g_dose, "2021-03")
    assert state_of(r1["b_G"], r1["b_G_floor"]) == "negative past the floor", r1
    assert state_of(r0["b_G"], r0["b_G_floor"]) == "inside the floor", r0
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--takeup", action="store_true", help="dose from EBA take-up instead of the envelopes")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    out = build(base.load_rates(), "takeup" if a.takeup else "envelope")
    print(f"guarantee dose ({out['dose']} / NFC stock):", dict(sorted(out["rows"][0]["guarantee_dose"].items(), key=lambda kv: -kv[1])))
    for r in out["rows"]:
        print(f"{r['object']:<22} {r['numerator']:<25} to {r['end']}: N {len(r['countries'])} dose corr {r['dose_corr']:+.2f}  "
              f"b_G {r['b_G']:+.3f} floor {r['b_G_floor']} -> {r['b_G_state']};  b_T {r['b_T']:+.3f} floor {r['b_T_floor']} -> {r['b_T_state']}")
    c = out["criteria"][0]
    print(f"{c['name']} [{c['kind']}] {'no verdict' if c['passed'] is None else ('PASS' if c['passed'] else 'FAIL')}: {c['state']}")
    (OUT_TAKEUP if a.takeup else OUT).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
