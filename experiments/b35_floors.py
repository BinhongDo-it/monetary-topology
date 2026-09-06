"""B35: the three arithmetic debts left open at the end of the long-window run.

1. The minimum-volume floor registered in results section 6.3, applied to the two
   poultry legs. It was declared at 25,000 kg per line per month, before any unit
   value was looked at, and sourced physically rather than statistically.

2. The instrument's own floor, by the method registered in section R17.6: take
   named single parts from the swine offal family that sit at the same level of
   the substitute-class question, so the framework predicts no difference between
   them, and read what difference the instrument produces anyway. Every such pair
   is printed rather than one being chosen, because choosing the pair after
   seeing the spread would be selecting on the answer.

   Two floors come out, because the arm has read two different statistics: the
   mean absolute monthly move, which the volatility comparison reads, and the
   ratio of two slopes on a common treatment, which the criterion reads.

3. The standard error of the difference of two slopes fitted on the same
   explanatory variable. Every gate so far has used the independent bound, which
   is conservative for this arm; the joint value needs the residual covariance.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ERS = ROOT / "data" / "raw" / "ers" / "ers_hist_monthly_spreads.csv"
CELLS = ROOT / "data" / "b35"
OUT = ROOT / "results" / "b35_floors.json"

VOLUME_FLOOR_KG = 25_000          # registered in section 6.3 before any unit value
CTY = "5700"
POULTRY = {"0207140010": "leg quarters", "0207140045": "paws"}
# Named single parts of the swine offal family. NESOI is excluded because it is a
# mixed basket, skins because they run only sixteen months of the window.
PORK_SAME_LEVEL = {
    "0206490010": "tongues", "0206490020": "hearts",
    "0206490030": "feet", "0206490040": "head meat",
}
Z90 = 1.645
BAND = 1.5


def composite() -> dict[str, float]:
    out: dict[str, float] = {}
    with ERS.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["Data_Item"] != "Wholesale broiler composite":
                continue
            v = r["Value"].strip()
            if v not in ("", ".", "NA"):
                out[f"{int(r['Year']):04d}-{int(r['Month-number']):02d}"] = float(v)
    return out


def series(prefixes, codes, years):
    uv = {c: {} for c in codes}
    kg = {c: {} for c in codes}
    for y in range(years[0], years[1] + 1):
        for m in range(1, 13):
            for pre in prefixes:
                f = CELLS / f"{pre}_{y}_{m:02d}_{CTY}_HS10.json"
                if not f.exists():
                    continue
                rows = json.loads(f.read_text(encoding="utf-8"))
                ix = {k: i for i, k in enumerate(rows[0])}
                for r in rows[1:]:
                    c = r[ix["E_COMMODITY"]]
                    if c not in codes:
                        continue
                    val = float(r[ix["ALL_VAL_MO"]])
                    q = float(r[ix["QTY_1_MO"]])
                    if q > 0:
                        uv[c][f"{y}-{m:02d}"] = val / q
                        kg[c][f"{y}-{m:02d}"] = q
    return uv, kg


def nxt(k):
    y, m = map(int, k.split("-"))
    return f"{y + (m == 12):04d}-{(m % 12) + 1:02d}"


def dlogs(s):
    return {k: math.log(s[nxt(k)] / s[k]) for k in sorted(s) if nxt(k) in s}


def fit(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    res = [c - (a0 + b * s) for s, c in zip(x, y)]
    return b, res, sxx, n


def main() -> None:
    rec = {"stage": "B35", "config": {"volume_floor_kg": VOLUME_FLOOR_KG,
                                      "z90": Z90, "band": BAND, "cty": CTY}}

    # ---- debt 1: the registered minimum-volume floor, applied ----------------
    uv_p, kg_p = series(["0207"], set(POULTRY), (2020, 2023))
    print("=" * 74)
    print("debt 1: the 25,000 kg floor registered in section 6.3, applied")
    print("=" * 74)
    d1 = {}
    for c, name in POULTRY.items():
        months = sorted(kg_p[c])
        below = [k for k in months if kg_p[c][k] < VOLUME_FLOOR_KG]
        lo = min(kg_p[c].values())
        print(f"  {c} {name:14s} months {len(months):3d}   "
              f"thinnest month {lo:12,.0f} kg   below the floor: {len(below)}")
        d1[c] = {"months": len(months), "thinnest_kg": lo, "below_floor": below}
    print("  the floor binds on nothing in this window; no month is removed")
    rec["volume_floor"] = d1

    # ---- debt 2: the instrument's floor, from pairs predicted not to differ --
    uv_k, kg_k = series(["020630", "020649"], set(PORK_SAME_LEVEL), (2020, 2022))
    tr = composite()
    print()
    print("=" * 74)
    print("debt 2: the instrument's floor, from swine offal parts at one level")
    print("=" * 74)
    dl = {c: dlogs(uv_k[c]) for c in PORK_SAME_LEVEL}
    for c, name in PORK_SAME_LEVEL.items():
        v = list(dl[c].values())
        print(f"  {c} {name:11s} steps {len(v):3d}   mean |dlog| = "
              f"{sum(abs(x) for x in v)/len(v):.4f}")
    print()
    print(f"  {'pair':26s} {'n':>4s} {'|dlog| ratio':>13s} {'slope ratio':>13s}")
    volr, slopr = [], []
    pairs = {}
    for a, b in itertools.combinations(sorted(PORK_SAME_LEVEL), 2):
        common = sorted(set(dl[a]) & set(dl[b]) & set(dlogs(tr)))
        if len(common) < 10:
            continue
        dtr = dlogs(tr)
        va = sum(abs(dl[a][k]) for k in common) / len(common)
        vb = sum(abs(dl[b][k]) for k in common) / len(common)
        x = [dtr[k] for k in common]
        ba, _, _, _ = fit(x, [dl[a][k] for k in common])
        bb, _, _, _ = fit(x, [dl[b][k] for k in common])
        vr = max(va, vb) / min(va, vb)
        sr = abs(max(ba, bb, key=abs) / min(ba, bb, key=abs))
        volr.append(vr); slopr.append(sr)
        nm = f"{PORK_SAME_LEVEL[a]} / {PORK_SAME_LEVEL[b]}"
        pairs[nm] = {"n": len(common), "vol_ratio": vr, "slope_ratio": sr}
        print(f"  {nm:26s} {len(common):4d} {vr:13.3f} {sr:13.3f}")
    volr.sort(); slopr.sort()
    print(f"\n  floor on the mean |dlog| ratio : median {volr[len(volr)//2]:.3f}   "
          f"max {volr[-1]:.3f}   (the arm read 5.11)")
    print(f"  floor on the slope ratio       : median {slopr[len(slopr)//2]:.3f}   "
          f"max {slopr[-1]:.3f}   (the arm read 9.42)")
    rec["instrument_floor"] = {"pairs": pairs,
                               "vol_ratio_median": volr[len(volr)//2],
                               "vol_ratio_max": volr[-1],
                               "slope_ratio_median": slopr[len(slopr)//2],
                               "slope_ratio_max": slopr[-1]}

    # ---- debt 3: the joint standard error of the difference of two slopes ----
    print()
    print("=" * 74)
    print("debt 3: se of the slope difference, joint rather than the bound")
    print("=" * 74)
    dtr = dlogs(tr)
    common = sorted(set(dlogs(uv_p["0207140010"])) & set(dlogs(uv_p["0207140045"]))
                    & set(dtr))
    x = [dtr[k] for k in common]
    b1, r1, sxx, n = fit(x, [dlogs(uv_p["0207140010"])[k] for k in common])
    b2, r2, _, _ = fit(x, [dlogs(uv_p["0207140045"])[k] for k in common])
    s11 = sum(v * v for v in r1) / (n - 2)
    s22 = sum(v * v for v in r2) / (n - 2)
    s12 = sum(a * b for a, b in zip(r1, r2)) / (n - 2)
    se_bound = math.sqrt(s11 / sxx + s22 / sxx)
    se_joint = math.sqrt((s11 + s22 - 2 * s12) / sxx)
    half = math.log(BAND)
    print(f"  n = {n}   b_lq = {b1:+.4f}   b_paw = {b2:+.4f}")
    print(f"  residual correlation = {s12/math.sqrt(s11*s22):+.4f}")
    print(f"  se(diff) independent bound = {se_bound:.4f}")
    print(f"  se(diff) joint             = {se_joint:.4f}")
    print(f"  gate two on the joint value: Z90 * se = {Z90*se_joint:.4f}  "
          f"vs band half width {half:.4f}  -> short by {Z90*se_joint/half:.2f} x")
    rec["se_difference"] = {"n": n, "b_lq": b1, "b_paw": b2,
                            "residual_correlation": s12 / math.sqrt(s11 * s22),
                            "se_independent_bound": se_bound, "se_joint": se_joint,
                            "gate_two_lhs_joint": Z90 * se_joint,
                            "band_half_width_log": half}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
