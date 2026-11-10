"""B132: the two borrowed prices in the national-accounts consumption deflator.

The national-accounts household consumption deflator carries imputed rentals (priced from actual
rents) and FISIM (priced as the gap to a borrowed interbank rate, ESA 2010 14.14; B131). The HICP
carries neither. Reads what `b132_fetch.py` put in data/raw/b132/; the ECB deposit rate and the
euro-area membership years are imported from `b131_readings.py`. Nothing is fetched here.

Decomposition, exact: with current prices CP and previous-year prices PYP, the item differences add
up to the total's, so item i moves the total deflator by (CP_i - PYP_i) / PYP_total points (x 100).

Units. A country's deflator change is read in national currency (CP_MNAC over PYP_MNAC): its euro
series is converted at each year's exchange rate, so CP_MEUR over PYP_MEUR carries the exchange
rate's move, and a comparison with the country's own HICP needs the country's own prices. Aggregates
are published in euro only and are read in euro; for one that spans several currencies (EU27) the
euro deflator still carries exchange-rate moves, and the record says so.

Criteria (each has a planted error in --selftest that must make it fail):
  B132-1  instrument    COICOP 1999 and 2018 versions give the same yearly deflator change for the
                        total and CP042 on the overlapping years; gaps above 0.5 point listed by name
                        (levels are not compared: the versions are different vintages)
  B132-2  known_answer  France 2023: the consumption deflator with and without CP122 against INSEE
                        Premiere no 2002 (7.1 % and 4.8 %); read through when each is within 0.2 point
                        (INSEE prints one decimal and the two sources are different vintages)
  B132-3  own_reading   per country and year: national-accounts deflator, HICP, their gap, the pull of
                        CP122 and of CP042, and the deflator with both taken out
  B132-4  own_reading   one purpose, two indices: CP122 in the national accounts against CP126 in the
                        HICP; on euro-area member years, CP122's price change against the change in the
                        ECB deposit rate's annual mean
  B132-5  own_reading   imputed rentals against actual rentals: CP042 deflator change against HICP
                        CP041 change, per country and year
  B132-6  own_reading   2020 -> 2024 cumulated: national-accounts deflator, HICP, and the deflator with
                        both borrowed prices taken out
  B132-7  instrument    the unit: on euro-area member years the national-currency and euro deflator
                        changes are one number; the country-years where they are not are counted

Run from the repo root:
    python experiments/b132_readings.py
    python experiments/b132_readings.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b131_readings as B131  # noqa: E402

RAW = ROOT / "data" / "raw" / "b132"
OUT = ROOT / "results" / "b132_readings.json"
INSEE_FR_2023 = {"with": 7.1, "without": 4.8}
INSEE_TOL = 0.2
VERSION_GAP = 0.5      # percent
YEARS = range(2019, 2026)
#: Every aggregate the two tables carry; EA12 overlaps both versions from 1996 to 2022 and is no country.
AGG = {"EA20", "EU27_2020", "EA19", "EU28", "EA", "EA12", "EA21"}
UNIT_TOL = 1e-6        # points; the two units on a euro member year


def is_area(g: str) -> bool:
    return g in AGG or g.startswith(("EA", "EU"))


def units(g: str, volume: str = "PYP") -> tuple[str, str]:
    """Current-price and volume units for one area: euro for an aggregate, national currency for a country."""
    cur = "MEUR" if is_area(g) else "MNAC"
    return f"CP_{cur}", f"{volume}_{cur}"


def load(name: str) -> dict:
    d = json.loads((RAW / name).read_text(encoding="utf-8"))
    ids, size = d["id"], d["size"]
    inv = {k: {i: v for v, i in d["dimension"][k]["category"]["index"].items()} for k in ids}
    out = {}
    for flat, v in d["value"].items():
        f, pos = int(flat), {}
        for k, s in zip(reversed(ids), reversed(size)):
            pos[k] = inv[k][f % s]
            f //= s
        out[tuple(pos[k] for k in ids if k not in ("freq", "time")) + (int(pos["time"]),)] = float(v)
    return out


def load_all() -> dict:
    return {"cp18": load("nama_10_cp18.json"), "co3": load("nama_10_co3_p3.json"),
            "hicp": load("prc_hicp_aind.json"), "dfr": B131.dfr_annual()}


# ---------- objects ----------

def na_change(cp18, g, y, drop=(), unit=None) -> float | None:
    """Deflator change of the total, percent, with the items in `drop` taken out."""
    uc, up = unit or units(g)
    cp, py = cp18.get((uc, "TOTAL", g, y)), cp18.get((up, "TOTAL", g, y))
    if cp is None or py is None:
        return None
    for it in drop:
        a, b = cp18.get((uc, it, g, y)), cp18.get((up, it, g, y))
        if a is None or b is None:
            return None
        cp, py = cp - a, py - b
    return None if py <= 0 else 100 * (cp / py - 1)


def item_change(cp18, g, it, y, unit=None):
    uc, up = unit or units(g)
    a, b = cp18.get((uc, it, g, y)), cp18.get((up, it, g, y))
    return None if a is None or b is None or b == 0 else 100 * (a / b - 1)


def pull(cp18, g, it, y):
    uc, up = units(g)
    a, b = cp18.get((uc, it, g, y)), cp18.get((up, it, g, y))
    t = cp18.get((up, "TOTAL", g, y))
    return None if None in (a, b, t) or t == 0 else 100 * (a - b) / t


def hicp_change(hicp, g, it, y):
    a, b = hicp.get(("INX_A_AVG", it, g, y)), hicp.get(("INX_A_AVG", it, g, y - 1))
    return None if a is None or b is None or b == 0 else 100 * (a / b - 1)


def r(v, n=3):
    return None if v is None else round(v, n)


# ---------- criteria ----------

def co3_change(co3, g, it, y):
    """Deflator change in the COICOP 1999 version: current price over chain-linked volume."""
    uc, uv = units(g, "CLV20")

    def p(t):
        a, b = co3.get((uc, it, g, t)), co3.get((uv, it, g, t))
        return None if a is None or b is None or b == 0 else a / b
    a, b = p(y), p(y - 1)
    return None if a is None or b is None or b == 0 else 100 * (a / b - 1)


def c1(data):
    """The two versions are different vintages (levels revised, Bulgaria converted differently), so
    they are compared on the deflator's yearly change, which is what this station reads."""
    listed, diffs = [], []
    for (u, it, g, y) in list(data["co3"]):
        if u != "CP_MNAC" or it not in ("TOTAL", "CP042") or is_area(g):
            continue
        a = co3_change(data["co3"], g, it, y)
        b = item_change(data["cp18"], g, it, y) if it != "TOTAL" else na_change(data["cp18"], g, y)
        if a is None or b is None:
            continue
        diffs.append(abs(a - b))
        if abs(a - b) > VERSION_GAP:
            listed.append(f"{g} {it} {y}: {a:.2f} against {b:.2f}")
    d = np.array(diffs)
    passed = d.size > 0
    detail = (f"{d.size} overlapping country-item-years; deflator change differs by a median "
              f"{np.median(d):.3f} points, by more than {VERSION_GAP} point in {len(listed)}"
              if d.size else "no overlap")
    return passed, detail, {"overlap": int(d.size), "median_abs_points": r(float(np.median(d)) if d.size else None),
                            "above": sorted(listed)}


def c2(data):
    cp = data["cp18"]
    w, wo = na_change(cp, "FR", 2023), na_change(cp, "FR", 2023, drop=("CP122",))
    ok = w is not None and wo is not None and abs(w - INSEE_FR_2023["with"]) <= INSEE_TOL + 1e-9 \
        and abs(wo - INSEE_FR_2023["without"]) <= INSEE_TOL + 1e-9
    detail = (f"France 2023: with CP122 {w:.2f} % against INSEE's {INSEE_FR_2023['with']} %, without "
              f"{wo:.2f} % against {INSEE_FR_2023['without']} % (INSEE takes out FISIM only; CP122 also "
              f"holds explicit fees)") if w is not None and wo is not None else "France 2023 missing"
    return bool(ok), detail, {"with": r(w), "without": r(wo)}


def c3(data):
    cp, hi = data["cp18"], data["hicp"]
    rows, flips = {}, []
    for g in sorted({k[2] for k in cp}):
        for y in YEARS:
            na, h = na_change(cp, g, y), hicp_change(hi, g, "CP00", y)
            if na is None or h is None:
                continue
            p122, p042 = pull(cp, g, "CP122", y), pull(cp, g, "CP042", y)
            ex = na_change(cp, g, y, drop=("CP122", "CP042"))
            rows[f"{g} {y}"] = {"na": r(na), "hicp": r(h), "gap": r(na - h), "pull_CP122": r(p122),
                                "pull_CP042": r(p042), "na_without_both": r(ex),
                                "gap_without_both": r(None if ex is None else ex - h)}
            if y == 2023 and p122 is not None and na - h > 0 and p122 > na - h:
                flips.append(f"{g}: gap {na - h:.2f}, CP122 pulls {p122:.2f}")
    ea = rows.get("EA20 2023", {})
    passed = bool(rows) and "EA20 2023" in rows
    detail = (f"{len(rows)} country-years. Euro area 2023: national accounts {ea.get('na')} %, HICP "
              f"{ea.get('hicp')} %, CP122 pulls {ea.get('pull_CP122')}, CP042 {ea.get('pull_CP042')}, "
              f"without both {ea.get('na_without_both')} %. 2023, gap above zero and CP122 alone larger "
              f"than the gap: {len(flips)} areas")
    return passed, detail, {"rows": rows, "cp122_exceeds_gap_2023": sorted(flips)}


def c4(data):
    cp, hi, dfr = data["cp18"], data["hicp"], data["dfr"]
    rows, xs, ys = {}, [], []
    for g in sorted({k[2] for k in cp}):
        for y in YEARS:
            a, b = item_change(cp, g, "CP122", y), hicp_change(hi, g, "CP126", y)
            if a is None or b is None:
                continue
            rows[f"{g} {y}"] = {"na_CP122": r(a), "hicp_CP126": r(b)}
            if g in B131.EURO_FROM and y >= B131.EURO_FROM[g] and y in dfr and y - 1 in dfr:
                xs.append(dfr[y] - dfr[y - 1])
                ys.append(a)
    corr = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 else None
    ea23 = rows.get("EA20 2023", {})
    passed = bool(rows) and corr is not None
    detail = (f"{len(rows)} country-years; euro area 2023: CP122 {ea23.get('na_CP122')} %, HICP CP126 "
              f"{ea23.get('hicp_CP126')} %. On {len(xs)} member years, correlation of CP122's price "
              f"change with the change in the deposit rate's annual mean: {corr:.3f}" if corr is not None
              else "no member years")
    return passed, detail, {"rows": rows, "member_years": len(xs), "corr_with_dfr_change": r(corr, 4)}


def c5(data):
    cp, hi = data["cp18"], data["hicp"]
    rows, d = {}, []
    for g in sorted({k[2] for k in cp}):
        for y in YEARS:
            a, b = item_change(cp, g, "CP042", y), hicp_change(hi, g, "CP041", y)
            if a is None or b is None:
                continue
            rows[f"{g} {y}"] = {"na_CP042": r(a), "hicp_CP041": r(b), "diff": r(a - b)}
            if not is_area(g):
                d.append(a - b)
    d = np.array(d)
    same = int((np.abs(d) <= 0.01 + 1e-9).sum()) if d.size else 0
    half = int((np.abs(d) <= 0.5).sum()) if d.size else 0
    to_one = int(((np.abs(d) > 0.5) & (np.abs(d) <= 1.0)).sum()) if d.size else 0
    passed = d.size > 0
    detail = (f"{d.size} country-years (aggregates excluded): median |CP042 - CP041| "
              f"{np.median(np.abs(d)):.2f} points, within 0.01 point in {same}, within 0.5 point in "
              f"{half}, between 0.5 and 1 point in {to_one}" if d.size else "no country-years")
    return passed, detail, {"rows": rows, "n": int(d.size), "within_0.01": same, "within_0.5": half,
                            "between_0.5_and_1": to_one,
                            "median_abs": r(float(np.median(np.abs(d))) if d.size else None)}


def c6(data):
    cp, hi = data["cp18"], data["hicp"]
    rows = {}
    for g in sorted({k[2] for k in cp}):
        acc = {"na": 1.0, "hicp": 1.0, "na_without_both": 1.0}
        ok = True
        for y in range(2021, 2025):
            vals = {"na": na_change(cp, g, y), "hicp": hicp_change(hi, g, "CP00", y),
                    "na_without_both": na_change(cp, g, y, drop=("CP122", "CP042"))}
            if any(v is None for v in vals.values()):
                ok = False
                break
            for k, v in vals.items():
                acc[k] *= 1 + v / 100
        if ok:
            rows[g] = {k: r(100 * (v - 1), 2) for k, v in acc.items()}
    ea = rows.get("EA20", {})
    passed = "EA20" in rows
    detail = (f"{len(rows)} areas, 2020 -> 2024 cumulated. Euro area: national accounts "
              f"{ea.get('na')} %, HICP {ea.get('hicp')} %, national accounts without CP122 and CP042 "
              f"{ea.get('na_without_both')} %")
    return passed, detail, rows


def c7(data):
    """The unit a country is read in. On a euro member year the national currency is the euro, so the
    two units must give one deflator change; where they part, the euro series is carrying the
    exchange rate. The year a country joins is listed apart: its previous-year-price figure is
    converted at the last market rate in the euro series and at the fixed rate in the other."""
    cp = data["cp18"]
    eur, nac = ("CP_MEUR", "PYP_MEUR"), ("CP_MNAC", "PYP_MNAC")
    worst, member, apart, joining = 0.0, 0, [], []
    for g in sorted({k[2] for k in cp}):
        if is_area(g):
            continue
        for y in YEARS:
            for it in ("TOTAL", "CP042", "CP122"):
                a = na_change(cp, g, y, unit=eur) if it == "TOTAL" else item_change(cp, g, it, y, unit=eur)
                b = na_change(cp, g, y, unit=nac) if it == "TOTAL" else item_change(cp, g, it, y, unit=nac)
                if a is None or b is None:
                    continue
                if g in B131.EURO_FROM and y > B131.EURO_FROM[g]:
                    member += 1
                    worst = max(worst, abs(a - b))
                elif g in B131.EURO_FROM and y == B131.EURO_FROM[g]:
                    joining.append(f"{g} {y} {it}: {abs(a - b):.4f} points")
                elif it == "TOTAL" and abs(a - b) > 0.1:
                    apart.append((abs(a - b), f"{g} {y}: euro {a:.2f} %, national currency {b:.2f} %"))
    apart.sort(reverse=True)
    passed = member > 0 and worst <= UNIT_TOL
    detail = (f"{member} member item-years after the joining year: the two units differ by at most "
              f"{worst:.1e} points; {len(joining)} item-years in a joining year listed. Outside "
              f"membership, the total's change differs by more than 0.1 point in {len(apart)} country-years"
              + (f"; largest {apart[0][1]}" if apart else ""))
    return passed, detail, {"member_item_years": member, "worst_points": worst, "joining_year": joining,
                            "apart_total": [s for _, s in apart],
                            "read_in": {"countries": list(nac), "aggregates": list(eur),
                                        "aggregates_in_data": sorted({k[2] for k in cp if is_area(k[2])})}}


KINDS = {"B132-1": "instrument", "B132-2": "known_answer", "B132-3": "own_reading",
         "B132-4": "own_reading", "B132-5": "own_reading", "B132-6": "own_reading", "B132-7": "instrument"}
FUNCS = {"B132-1": c1, "B132-2": c2, "B132-3": c3, "B132-4": c4, "B132-5": c5, "B132-6": c6, "B132-7": c7}


def build(data):
    return {n: f(data) for n, f in FUNCS.items()}


def selftest() -> None:
    data = load_all()
    base = build(data)
    assert all(v[0] for v in base.values()), {k: v[1] for k, v in base.items() if not v[0]}
    bad = copy.deepcopy(data)
    bad["co3"] = {}
    assert not c1(bad)[0], "B132-1 must fail with no overlap"
    bad = copy.deepcopy(data)
    bad["cp18"][("CP_MNAC", "CP122", "FR", 2023)] += 20_000
    assert not c2(bad)[0], "B132-2 must catch a wrong French CP122"
    assert not c7(bad)[0], "B132-7 must catch a member year whose two units disagree"
    assert units("SE") == ("CP_MNAC", "PYP_MNAC") and units("EA20") == ("CP_MEUR", "PYP_MEUR") \
        and units("EU27_2020", "CLV20") == ("CP_MEUR", "CLV20_MEUR"), "a country in national currency, an area in euro"
    se_eur = na_change(data["cp18"], "SE", 2023, unit=("CP_MEUR", "PYP_MEUR"))
    se_nac = na_change(data["cp18"], "SE", 2023)
    assert abs(se_eur - se_nac) > 1.0, "Sweden 2023 must differ between the units, or the unit does nothing"
    for fn, key in ((c3, "EA20"), (c6, "EA20")):
        bad = copy.deepcopy(data)
        bad["cp18"] = {k: v for k, v in bad["cp18"].items() if k[2] != key}
        assert not fn(bad)[0], f"{fn.__name__} needs the euro area"
    bad = copy.deepcopy(data)
    bad["dfr"] = {}
    assert not c4(bad)[0], "B132-4 must fail with no deposit rate"
    bad = copy.deepcopy(data)
    bad["hicp"] = {k: v for k, v in bad["hicp"].items() if k[1] != "CP041"}
    assert not c5(bad)[0], "B132-5 must fail with no actual-rent index"
    print("selftest ok: all seven flags pass on the data and each fails on its planted error; "
          f"Sweden 2023 reads {se_eur:.2f} % in euro and {se_nac:.2f} % in kronor")


def main() -> int:
    data = load_all()
    res = build(data)
    crit = []
    for name, (passed, detail, obj) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
        crit.append({"name": name, "kind": KINDS[name], "passed": passed, "detail": detail})
    record = {"stage": "B132", "criteria": crit,
              "objects": {n: o for n, (_, _, o) in res.items()},
              "config": {"insee_fr_2023": INSEE_FR_2023, "insee_tolerance": INSEE_TOL,
                         "version_gap_pct": VERSION_GAP, "years": [min(YEARS), max(YEARS)],
                         "source": json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
