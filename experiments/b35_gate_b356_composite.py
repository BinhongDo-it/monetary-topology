"""B35-6 recomputed with the composite as the treatment, over the long window.

The criterion is unchanged: a ratio of two responses to a move in the US
domestic chicken market, with a FAIL band of 1/1.5 .. 1.5 declared before any
of this was read. What changes is which series carries the treatment.

The cut-level quotation that carried it before starts in 2022-09, and that start
was what bounded the window to eleven months and seven adjacent steps. The
treatment does not have to be cut-level: the criterion asks for a move in the US
market, not for a move in the same cut. Swapping in the composite frees the
lower bound, and the window is then bounded by the outcomes instead, which run
from the reopening of the trade to the collapse in volume.

A common rescaling of the treatment divides both slopes and both standard errors
by the same factor, so the ratio and both t statistics are untouched by the
composite being a damped version of the cut-level series. The gain is the step
count and nothing else.

Every input is already on disk. This script fetches nothing.
"""

from __future__ import annotations

import csv
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ERS = ROOT / "data" / "raw" / "ers" / "ers_hist_monthly_spreads.csv"
CELLS = ROOT / "data" / "b35"
OUT = ROOT / "results" / "b35_gate_b356_composite.json"

TREATMENT_ITEM = "Wholesale broiler composite"
LEG_QUARTERS = "0207140010"
PAWS = "0207140045"
CTY = "5700"
YEARS = (2020, 2023)          # reopening 2019-11 to the volume collapse in 2024
BAND = 1.5
Z90 = 1.645


def composite() -> dict[str, float]:
    out: dict[str, float] = {}
    with ERS.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["Data_Item"] != TREATMENT_ITEM:
                continue
            v = r["Value"].strip()
            if v in ("", ".", "NA"):
                continue
            out[f"{int(r['Year']):04d}-{int(r['Month-number']):02d}"] = float(v)
    return out


def unit_values() -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    lq: dict[str, float] = {}
    pw: dict[str, float] = {}
    vol: dict[str, float] = {}
    for y in range(YEARS[0], YEARS[1] + 1):
        for m in range(1, 13):
            f = CELLS / f"0207_{y}_{m:02d}_{CTY}_HS10.json"
            if not f.exists():
                continue
            rows = json.loads(f.read_text(encoding="utf-8"))
            ix = {k: i for i, k in enumerate(rows[0])}
            key = f"{y}-{m:02d}"
            for r in rows[1:]:
                code = r[ix["E_COMMODITY"]]
                if code not in (LEG_QUARTERS, PAWS):
                    continue
                val = float(r[ix["ALL_VAL_MO"]])
                qty = float(r[ix["QTY_1_MO"]])
                if qty <= 0:
                    continue
                if code == LEG_QUARTERS:
                    lq[key] = val / qty
                    vol[key] = qty
                else:
                    pw[key] = val / qty
    return lq, pw, vol


def next_month(k: str) -> str:
    y, m = map(int, k.split("-"))
    return f"{y + (m == 12):04d}-{(m % 12) + 1:02d}"


def fit(x: list[float], y: list[float]) -> dict[str, float]:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    b = sxy / sxx
    a = my - b * mx
    resid = [t - (a + b * s) for s, t in zip(x, y)]
    s2 = sum(r * r for r in resid) / (n - 2)
    syy = sum((v - my) ** 2 for v in y)
    return {"a": a, "b": b, "se": math.sqrt(s2 / sxx), "n": n,
            "r2": 1 - sum(r * r for r in resid) / syy}


def main() -> None:
    tr = composite()
    lq, pw, vol = unit_values()
    months = sorted(set(lq) & set(pw) & set(tr))
    steps = [(k, next_month(k)) for k in months
             if next_month(k) in lq and next_month(k) in pw and next_month(k) in tr]

    print(f"months with all three series: {len(months)}  "
          f"{months[0]} .. {months[-1]}")
    print(f"adjacent steps: {len(steps)}\n")
    print(f"{'step':22s} {'dlog treat':>11s} {'dlog LQ':>10s} {'dlog paw':>10s} {'LQ kg':>12s}")
    dtr, dlq, dpw = [], [], []
    for a, b in steps:
        t = math.log(tr[b] / tr[a])
        u = math.log(lq[b] / lq[a])
        w = math.log(pw[b] / pw[a])
        dtr.append(t); dlq.append(u); dpw.append(w)
        print(f"{a}->{b:11s} {t:11.4f} {u:10.4f} {w:10.4f} {vol.get(b, 0):12,.0f}")

    f_lq = fit(dtr, dlq)
    f_pw = fit(dtr, dpw)
    print(f"\n  leg quarters : b = {f_lq['b']:+.4f}  se = {f_lq['se']:.4f}  "
          f"R2 = {f_lq['r2']:+.4f}  n = {f_lq['n']}")
    print(f"  paws         : b = {f_pw['b']:+.4f}  se = {f_pw['se']:.4f}  "
          f"R2 = {f_pw['r2']:+.4f}  n = {f_pw['n']}")

    diff = f_lq["b"] - f_pw["b"]
    se_diff = math.sqrt(f_lq["se"] ** 2 + f_pw["se"] ** 2)
    half = math.log(BAND)
    lhs = Z90 * se_diff
    ratio = abs(f_lq["b"] / f_pw["b"]) if f_pw["b"] else float("inf")
    power = 0.5 * (1 + math.erf((half / se_diff - Z90) / math.sqrt(2)))
    print(f"\n  difference b_lq - b_paw = {diff:+.4f}   "
          f"se(diff, independent bound) = {se_diff:.4f}")
    print(f"  magnitude ratio |b_lq / b_paw| = {ratio:.3f}   "
          f"FAIL band is {1/BAND:.3f} .. {BAND:.3f}")
    print(f"\n  gate two : Z90 * se = {lhs:.4f}   band half width = {half:.4f}   "
          f"{'PASSES' if lhs < half else 'does not pass, short by %.2f x' % (lhs / half)}")
    print(f"  gate three: power at the band edge = {power:.4f}   floor 0.50   "
          f"likelihood ratio of non-rejection = {0.95 / (1 - power):.3f}")

    rec = {
        "stage": "B35", "arm": "B35-6",
        "config": {"treatment": TREATMENT_ITEM, "window": f"{YEARS[0]}-01..{YEARS[1]}-12",
                   "leg_quarters_hs10": LEG_QUARTERS, "paws_hs10": PAWS,
                   "destination_cty": CTY, "band": BAND, "z90": Z90},
        "months": months, "adjacent_steps": len(steps),
        "dlog_treatment": dtr, "dlog_leg_quarters": dlq, "dlog_paws": dpw,
        "leg_quarter_kg": [vol.get(b, 0) for _a, b in steps],
        "fit_leg_quarters": f_lq, "fit_paws": f_pw,
        "b_diff": diff, "se_diff_independent_bound": se_diff,
        "magnitude_ratio": ratio, "band_half_width_log": half,
        "gate_two_lhs": lhs, "gate_two_passes": bool(lhs < half),
        "gate_three_power": power, "gate_three_floor": 0.5,
        "likelihood_ratio_of_non_rejection": 0.95 / (1 - power),
    }
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
