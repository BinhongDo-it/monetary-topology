"""B133: how much of the consumer-output price divergence in the pay-productivity gap is borrowed prices.

Reads the BEA NIPA annual flat file and EPI's Table 1 from data/raw/b133/. Nothing is fetched here.

Divergence over a window [a, b]: 100 ln(P_PCE(b)/P_PCE(a)) - 100 ln(P_NFB(b)/P_NFB(a)), in log points.
Borrowed prices: imputed rental of owner-occupied nonfarm housing and financial services furnished without
payment (household FISIM). Their contributions to the PCE price change are BEA's own (Table 2.4.8). The PCE
without them is rebuilt year by year: the rest's change is (PCE change - both contributions) / (1 - their
previous-year share of PCE). It is the consumer price without the borrowed prices; it is not what owners pay
for housing (mortgage interest and upkeep are not PCE).

Criteria (each has a planted error in --selftest that must make it fail):
  B133-1  instrument    the PCE price index's yearly change equals BEA's printed percent change to its
                        rounding (0.1, so within 0.05); BEA's contributions against share x item price
                        change, printed
  B133-2  known_answer  1973-2014 divergence per year against EPI Table 1 (0.33 net, 0.43 gross); read
                        through when between them or within 0.05 of either (EPI prints to 0.01, the two
                        use different indexes)
  B133-3  own_reading   divergence, divergence without borrowed prices, and the borrowed share, on three
                        main windows and on every window starting 1970-1985 and ending 2007-2024
  B133-4  own_reading   the two items apart, by decade: summed contributions, and each item's price
                        against the PCE price
  B133-5  own_reading   EPI's share of the net gap that is price divergence (29.6 %) times this station's
                        borrowed share, 1973-2014: the borrowed prices' share of the whole gap

Run from the repo root:
    python experiments/b133_readings.py
    python experiments/b133_readings.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b133"
OUT = ROOT / "results" / "b133_readings.json"
CODES = ["DPCERG", "DPCERV", "CE001228", "CE001209", "DOWNRG", "DIMPRG", "DOWNRC", "DIMPRC", "DPCERC",
         "B358RG", "B195RG", "A191RG"]
MAIN = [(1973, 2014), (1979, 2019), (1973, 2024)]
STARTS = range(1970, 1986)
ENDS = range(2007, 2025)
ROUND_HALF = 0.05 + 1e-9
EPI_TOL = 0.05


def load_nipa() -> dict:
    v = {c: {} for c in CODES}
    with open(RAW / "NipaDataA.txt", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for code, per, val in r:
            if code in v:
                try:
                    v[code][int(per)] = float(val.replace(",", ""))
                except ValueError:
                    pass
    return v


def load_epi() -> dict:
    out = {}
    lines = (RAW / "epi_2015_table1.txt").read_text(encoding="utf-8").splitlines()
    header = next(l for l in lines if l.startswith("\t1973"))
    cols = header.split("\t")[1:]
    section = None
    for l in lines:
        if l.startswith("B. "):
            section = "net"
        elif l.startswith("C. "):
            section = "gross"
        elif l.startswith("Relative contribution to net"):
            section = "net_share"
        elif l.startswith("Relative contribution to gross"):
            section = "gross_share"
        parts = l.split("\t")
        if parts[0].startswith("Divergence of consumer and output prices") and section:
            out[section] = {c: float(x.rstrip("%")) for c, x in zip(cols, parts[1:])}
    return out


def load_all() -> dict:
    return {"v": load_nipa(), "epi": load_epi()}


def lp(v, code, a, b):
    return 100 * math.log(v[code][b] / v[code][a])


def rest_lp(v, a, b):
    """Log points of the PCE price without the two borrowed items, rebuilt year by year."""
    acc = 0.0
    for y in range(a + 1, b + 1):
        g = 100 * (v["DPCERG"][y] / v["DPCERG"][y - 1] - 1)
        c = v["CE001228"][y] + v["CE001209"][y]
        s = (v["DOWNRC"][y - 1] + v["DIMPRC"][y - 1]) / v["DPCERC"][y - 1]
        acc += 100 * math.log(1 + ((g - c) / (1 - s)) / 100)
    return acc


def window(v, a, b):
    pce, nfb, rest = lp(v, "DPCERG", a, b), lp(v, "B358RG", a, b), rest_lp(v, a, b)
    wedge, wedge_ex = pce - nfb, rest - nfb
    share = None if wedge <= 0 else 1 - wedge_ex / wedge
    return {"pce": round(pce, 2), "nfb": round(nfb, 2), "pce_without_borrowed": round(rest, 2),
            "divergence": round(wedge, 2), "divergence_without_borrowed": round(wedge_ex, 2),
            "borrowed_share": None if share is None else round(share, 4)}


# ---------- criteria ----------

def c1(data):
    v = data["v"]
    bad, n, dev = [], 0, []
    for y in sorted(v["DPCERV"]):
        if y - 1 not in v["DPCERG"] or y not in v["DPCERG"]:
            continue
        g = 100 * (v["DPCERG"][y] / v["DPCERG"][y - 1] - 1)
        n += 1
        if abs(g - v["DPCERV"][y]) > ROUND_HALF:
            bad.append(f"{y}: index {g:.3f} against printed {v['DPCERV'][y]}")
        for item, pc, cc in (("CE001228", "DOWNRG", "DOWNRC"), ("CE001209", "DIMPRG", "DIMPRC")):
            if y in v[item] and y - 1 in v[pc]:
                s = v[cc][y - 1] / v["DPCERC"][y - 1]
                dev.append(abs(v[item][y] - s * 100 * (v[pc][y] / v[pc][y - 1] - 1)))
    passed = n > 0 and not bad
    detail = (f"{n} years: the index's yearly change matches BEA's printed change to rounding in "
              f"{n - len(bad)}; BEA's contributions against previous-year share x item price change "
              f"differ by a median {np.median(dev):.3f} points (max {max(dev):.3f})")
    return passed, detail, {"years": n, "off": bad, "contribution_dev_median": round(float(np.median(dev)), 4),
                            "contribution_dev_max": round(float(max(dev)), 4)}


def c2(data):
    v, epi = data["v"], data["epi"]
    w = window(v, 1973, 2014)
    rate = w["divergence"] / 41
    net, gross = epi["net"]["1973–2014"], epi["gross"]["1973–2014"]
    ok = (min(net, gross) - EPI_TOL <= rate <= max(net, gross) + EPI_TOL)
    detail = (f"1973-2014 divergence {w['divergence']} log points, {rate:.3f} a year, against EPI's "
              f"{net} (net) and {gross} (gross)")
    return bool(ok), detail, {"rate": round(rate, 4), "epi_net": net, "epi_gross": gross}


def c3(data):
    v = data["v"]
    main = {f"{a}-{b}": window(v, a, b) for a, b in MAIN}
    shares, nonpos, above1 = [], [], []
    for a in STARTS:
        for b in ENDS:
            w = window(v, a, b)
            if w["borrowed_share"] is None:
                nonpos.append(f"{a}-{b}")
                continue
            shares.append(w["borrowed_share"])
            if w["borrowed_share"] > 1:
                above1.append(f"{a}-{b}")
    sh = np.array(shares)
    passed = len(main) == len(MAIN) and sh.size > 0
    detail = ("main windows: " + "; ".join(f"{k} divergence {x['divergence']}, without borrowed "
                                          f"{x['divergence_without_borrowed']}, share {x['borrowed_share']}"
                                          for k, x in main.items()) +
              f". Knob sweep over {len(STARTS) * len(ENDS)} windows: divergence not positive in "
              f"{len(nonpos)}; share ranges {sh.min():.3f} to {sh.max():.3f}, median {np.median(sh):.3f}, "
              f"above 1 (borrowed prices more than the whole divergence) in {len(above1)}")
    return passed, detail, {"main": main, "sweep": {"n": int(sh.size), "min": round(float(sh.min()), 4),
                            "max": round(float(sh.max()), 4), "median": round(float(np.median(sh)), 4),
                            "divergence_not_positive": nonpos, "share_above_1": above1}}


def c4(data):
    v = data["v"]
    rows = {}
    for d0 in range(1970, 2030, 10):
        d1 = min(d0 + 10, max(v["DPCERG"]))
        if d1 <= d0:
            continue
        yrs = range(d0 + 1, d1 + 1)
        rows[f"{d0}-{d1}"] = {"imputed_rent_pull": round(sum(v["CE001228"][y] for y in yrs), 2),
                              "fisim_pull": round(sum(v["CE001209"][y] for y in yrs), 2),
                              "pce_lp": round(lp(v, "DPCERG", d0, d1), 2),
                              "imputed_rent_price_lp": round(lp(v, "DOWNRG", d0, d1), 2),
                              "fisim_price_lp": round(lp(v, "DIMPRG", d0, d1), 2)}
    passed = len(rows) >= 5
    detail = "; ".join(f"{k}: rent pull {x['imputed_rent_pull']}, FISIM pull {x['fisim_pull']}, rent price "
                       f"{x['imputed_rent_price_lp']} against PCE {x['pce_lp']}" for k, x in rows.items())
    return passed, detail, rows


def c5(data):
    v, epi = data["v"], data["epi"]
    share = window(v, 1973, 2014)["borrowed_share"]
    net, gross = epi["net_share"]["1973–2014"], epi["gross_share"]["1973–2014"]
    ok = share is not None
    detail = (f"EPI puts price divergence at {net} % of the net gap and {gross} % of the gross gap, "
              f"1973-2014; with a borrowed share of {share:.3f} on the PCE measure, borrowed prices are "
              f"{net * share:.1f} % and {gross * share:.1f} % of the whole gap (EPI uses the CPI-U-RS, whose "
              f"owner's-equivalent-rent weight is larger than the PCE's)" if ok else "no share")
    return ok, detail, {"borrowed_share": share, "of_net_gap_pct": None if not ok else round(net * share, 2),
                        "of_gross_gap_pct": None if not ok else round(gross * share, 2)}


KINDS = {"B133-1": "instrument", "B133-2": "known_answer", "B133-3": "own_reading", "B133-4": "own_reading",
         "B133-5": "own_reading"}
FUNCS = {"B133-1": c1, "B133-2": c2, "B133-3": c3, "B133-4": c4, "B133-5": c5}


def build(data):
    return {n: f(data) for n, f in FUNCS.items()}


def selftest() -> None:
    data = load_all()
    base = build(data)
    assert all(x[0] for x in base.values()), {k: x[1] for k, x in base.items() if not x[0]}
    bad = copy.deepcopy(data)
    bad["v"]["DPCERG"][1990] *= 1.01
    assert not c1(bad)[0], "B133-1 must catch an index off its printed change"
    bad = copy.deepcopy(data)
    bad["v"]["B358RG"][2014] *= 0.8
    assert not c2(bad)[0], "B133-2 must catch a wrong output price"
    bad = copy.deepcopy(data)
    bad["v"]["DPCERG"] = {y: x for y, x in bad["v"]["DPCERG"].items() if y < 1990}
    try:
        ok = c3(bad)[0]
    except KeyError:
        ok = False
    assert not ok, "B133-3 must fail with the PCE cut short"
    bad = copy.deepcopy(data)
    bad["v"]["DPCERG"] = {y: x for y, x in bad["v"]["DPCERG"].items() if y < 1995}
    try:
        ok = c4(bad)[0]
    except KeyError:
        ok = False
    assert not ok, "B133-4 must fail with the decades cut short"
    bad = copy.deepcopy(data)
    bad["v"]["B358RG"][2014] = bad["v"]["DPCERG"][2014] * bad["v"]["B358RG"][1973] / bad["v"]["DPCERG"][1973] * 1.2
    assert not c5(bad)[0], "B133-5 must fail when there is no positive divergence"
    print("selftest ok: all five flags pass on the data and each fails on its planted error")


def main() -> int:
    data = load_all()
    res = build(data)
    crit = []
    for name, (passed, detail, obj) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
        crit.append({"name": name, "kind": KINDS[name], "passed": passed, "detail": detail})
    record = {"stage": "B133", "criteria": crit, "objects": {n: o for n, (_, _, o) in res.items()},
              "config": {"main_windows": MAIN, "starts": [min(STARTS), max(STARTS)],
                         "ends": [min(ENDS), max(ENDS)], "epi_tolerance": EPI_TOL}}
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
