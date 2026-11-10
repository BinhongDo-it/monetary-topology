"""B133: how much of the consumer-output price divergence in the pay-productivity gap is borrowed prices.

Reads the BEA NIPA annual flat file and EPI's Table 1 from data/raw/b133/. Nothing is fetched here.

Divergence over a window [a, b]: 100 ln(P_PCE(b)/P_PCE(a)) - 100 ln(P_NFB(b)/P_NFB(a)), in log points.
Borrowed prices: imputed rental of owner-occupied nonfarm housing, and BEA's "financial services furnished
without payment" (PCE line 107: commercial banks, other depository institutions and regulated investment
companies, pension funds; for banks BEA prices the service against the return on safe government securities).
It is not the European household FISIM item for item, and B131's interbank reference rate is not carried over
to it. Their contributions to the PCE price change are BEA's own (Table 2.4.8).

The PCE without the two items is not published and the PCE is a Fisher index, so "without" is a construction,
and two are computed:
  contributions  (PCE change - both contributions) / (1 - their previous-year share of PCE): BEA's Fisher
                 contributions taken off and the rest rescaled by a base-year share. The station's readings
                 have been on this one from the start.
  fisher         a Laspeyres and a Paasche removal from the items' own price indexes and current-dollar
                 values in the two years, and their geometric mean (a Fisher of the published Fishers).
Neither is the Fisher index of the remaining lines recomputed from their own prices and quantities. Both are
calibrated on a removal BEA does publish, PCE excluding food and energy (B133-6): the gap to it is the
operator's measured floor. Either way it is the consumer price without the borrowed prices; it is not what
owners pay for housing (mortgage interest and upkeep are not PCE).

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
                        borrowed share, 1973-2014: a scale conversion on the PCE measure. EPI's own consumer
                        side is a compensation deflator it builds (wages by the CPI-U-RS, health benefits by
                        a medical index) against the NDP deflator; the borrowed share on that measure is not
                        computed here
  B133-6  known_answer  the removal operators against a removal BEA publishes: food and energy taken out of
                        the PCE by each operator, against BEA's PCE excluding food and energy, year by year
                        and cumulated on the main windows; read through where, on every main window, the
                        operator's gap to the published index is smaller than the borrowed amount it reads

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
         "B358RG", "B195RG", "A191RG",
         "DPCCRG", "CE001047", "CE001066", "DFXARG", "DNRGRG", "DFXARC", "DNRGRC",
         "DIMCRC", "DIMNRC", "DPENRC"]
#: An item set to take out of the PCE: BEA's price contributions, the items' price indexes, their values.
BORROWED = {"contrib": ("CE001228", "CE001209"), "price": ("DOWNRG", "DIMPRG"), "nominal": ("DOWNRC", "DIMPRC")}
FOOD_ENERGY = {"contrib": ("CE001047", "CE001066"), "price": ("DFXARG", "DNRGRG"), "nominal": ("DFXARC", "DNRGRC")}
OPERATORS = ("contributions", "fisher")
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


def rest_change(v, y, items=BORROWED, how="contributions") -> float:
    """One year's percent change of the PCE price with `items` taken out, by one of the two operators."""
    F = v["DPCERG"][y] / v["DPCERG"][y - 1]
    if how == "contributions":
        c = sum(v[k][y] for k in items["contrib"])
        s = sum(v[k][y - 1] for k in items["nominal"]) / v["DPCERC"][y - 1]
        return (100 * (F - 1) - c) / (1 - s)
    rel = [v[k][y] / v[k][y - 1] for k in items["price"]]
    s0 = [v[k][y - 1] / v["DPCERC"][y - 1] for k in items["nominal"]]
    s1 = [v[k][y] / v["DPCERC"][y] for k in items["nominal"]]
    las = (F - sum(s * r for s, r in zip(s0, rel))) / (1 - sum(s0))
    paa = (1 - sum(s1)) / (1 / F - sum(s / r for s, r in zip(s1, rel)))
    return 100 * (math.sqrt(las * paa) - 1)


def rest_lp(v, a, b, items=BORROWED, how="contributions"):
    """Log points of the PCE price without `items`, rebuilt year by year."""
    return sum(100 * math.log(1 + rest_change(v, y, items, how) / 100) for y in range(a + 1, b + 1))


def window(v, a, b):
    pce, nfb, rest = lp(v, "DPCERG", a, b), lp(v, "B358RG", a, b), rest_lp(v, a, b)
    wedge, wedge_ex = pce - nfb, rest - nfb
    share = None if wedge <= 0 else 1 - wedge_ex / wedge
    rest_f = rest_lp(v, a, b, how="fisher")
    share_f = None if wedge <= 0 else 1 - (rest_f - nfb) / wedge
    return {"pce": round(pce, 2), "nfb": round(nfb, 2), "pce_without_borrowed": round(rest, 2),
            "divergence": round(wedge, 2), "divergence_without_borrowed": round(wedge_ex, 2),
            "borrowed_share": None if share is None else round(share, 4),
            "pce_without_borrowed_fisher": round(rest_f, 2),
            "divergence_without_borrowed_fisher": round(rest_f - nfb, 2),
            "borrowed_share_fisher": None if share_f is None else round(share_f, 4)}


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
    shares, shares_f, nonpos, above1 = [], [], [], []
    for a in STARTS:
        for b in ENDS:
            w = window(v, a, b)
            if w["borrowed_share"] is None:
                nonpos.append(f"{a}-{b}")
                continue
            shares.append(w["borrowed_share"])
            shares_f.append(w["borrowed_share_fisher"])
            if w["borrowed_share"] > 1:
                above1.append(f"{a}-{b}")
    sh, shf = np.array(shares), np.array(shares_f)
    passed = len(main) == len(MAIN) and sh.size > 0
    detail = ("main windows: " + "; ".join(f"{k} divergence {x['divergence']}, without borrowed "
                                          f"{x['divergence_without_borrowed']}, share {x['borrowed_share']}"
                                          for k, x in main.items()) +
              f". Knob sweep over {len(STARTS) * len(ENDS)} windows: divergence not positive in "
              f"{len(nonpos)}; share ranges {sh.min():.3f} to {sh.max():.3f}, median {np.median(sh):.3f}, "
              f"above 1 (borrowed prices more than the whole divergence) in {len(above1)}")
    detail += (f". With the Fisher removal: " + "; ".join(f"{k} share {x['borrowed_share_fisher']}" for k, x in main.items())
               + f"; sweep {shf.min():.3f} to {shf.max():.3f}, median {np.median(shf):.3f}; the two operators' "
               f"shares differ by at most {np.max(np.abs(sh - shf)):.4f} over the sweep")
    return passed, detail, {"main": main, "sweep": {"n": int(sh.size), "min": round(float(sh.min()), 4),
                            "max": round(float(sh.max()), 4), "median": round(float(np.median(sh)), 4),
                            "divergence_not_positive": nonpos, "share_above_1": above1},
                            "sweep_fisher": {"min": round(float(shf.min()), 4), "max": round(float(shf.max()), 4),
                                             "median": round(float(np.median(shf)), 4),
                                             "largest_gap_to_contributions": round(float(np.max(np.abs(sh - shf))), 4)}}


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
    detail = "; ".join(f"{k}: rent pull {x['imputed_rent_pull']}, unpriced financial services pull "
                       f"{x['fisim_pull']}, rent price {x['imputed_rent_price_lp']} against PCE {x['pce_lp']}"
                       for k, x in rows.items())
    parts = {}
    for y in (2000, 2014, 2024):
        if all(y in v[k] for k in ("DIMCRC", "DIMNRC", "DPENRC", "DIMPRC")):
            parts[str(y)] = {"commercial_banks": v["DIMCRC"][y], "other_depository_and_investment_companies": v["DIMNRC"][y],
                             "pension_funds": v["DPENRC"][y], "line_107_total": v["DIMPRC"][y],
                             "pension_share": round(v["DPENRC"][y] / v["DIMPRC"][y], 4)}
    rows["financial_services_line_107_components_musd"] = parts
    detail += ("; line 107 by provider, pension funds' share of its value: "
               + ", ".join(f"{y} {p['pension_share']:.3f}" for y, p in parts.items()))
    return passed and len(parts) == 3, detail, rows


def c5(data):
    v, epi = data["v"], data["epi"]
    w = window(v, 1973, 2014)
    share, share_f = w["borrowed_share"], w["borrowed_share_fisher"]
    net, gross = epi["net_share"]["1973–2014"], epi["gross_share"]["1973–2014"]
    ok = share is not None
    detail = (f"EPI puts price divergence at {net} % of the net gap and {gross} % of the gross gap, "
              f"1973-2014; with a borrowed share of {share:.3f} on the PCE measure, borrowed prices are "
              f"{net * share:.1f} % and {gross * share:.1f} % of the whole gap (a scale conversion: EPI's "
              f"consumer side is its own compensation deflator, wages by the CPI-U-RS and health benefits by "
              f"a medical index, and the borrowed share on that measure is not computed here); with the "
              f"Fisher removal's share of {share_f:.3f}, {net * share_f:.1f} % and {gross * share_f:.1f} %"
              if ok else "no share")
    return ok, detail, {"borrowed_share": share, "of_net_gap_pct": None if not ok else round(net * share, 2),
                        "of_gross_gap_pct": None if not ok else round(gross * share, 2),
                        "borrowed_share_fisher": share_f,
                        "of_net_gap_pct_fisher": None if not ok else round(net * share_f, 2),
                        "of_gross_gap_pct_fisher": None if not ok else round(gross * share_f, 2)}


def c6(data):
    """The two removal operators on a removal BEA publishes: food and energy out of the PCE."""
    v = data["v"]
    years = [y for y in sorted(v["DPCCRG"]) if y - 1 in v["DPCCRG"] and y in v["CE001047"] and y in v["CE001066"]]
    out, ok = {}, bool(years)
    for how in OPERATORS:
        gaps = [rest_change(v, y, FOOD_ENERGY, how) - 100 * (v["DPCCRG"][y] / v["DPCCRG"][y - 1] - 1) for y in years]
        worst = max(range(len(gaps)), key=lambda k: abs(gaps[k])) if gaps else None
        wins = {}
        for a, b in MAIN:
            cal = rest_lp(v, a, b, FOOD_ENERGY, how) - lp(v, "DPCCRG", a, b)
            borrowed = lp(v, "DPCERG", a, b) - rest_lp(v, a, b, BORROWED, how)
            wins[f"{a}-{b}"] = {"gap_to_published_core_lp": round(cal, 4), "borrowed_lp": round(borrowed, 4),
                                "gap_over_borrowed": round(abs(cal) / abs(borrowed), 4) if borrowed else None}
            ok = ok and abs(cal) < abs(borrowed)
        out[how] = {"years": len(years), "yearly_gap_median_abs": round(float(np.median(np.abs(gaps))), 6),
                    "yearly_gap_max_abs": round(float(np.max(np.abs(gaps))), 6),
                    "yearly_gap_max_year": years[worst] if worst is not None else None, "windows": wins}
    detail = "; ".join(
        f"{how}: against BEA's PCE excluding food and energy, yearly gap median {o['yearly_gap_median_abs']:.4f} "
        f"points, largest {o['yearly_gap_max_abs']:.4f} ({o['yearly_gap_max_year']}); cumulated "
        + ", ".join(f"{k} {w['gap_to_published_core_lp']:+.3f} log points against {w['borrowed_lp']:.2f} read"
                    for k, w in o["windows"].items())
        for how, o in out.items()) if years else "no published core index"
    return bool(ok), detail, out


KINDS = {"B133-1": "instrument", "B133-2": "known_answer", "B133-3": "own_reading", "B133-4": "own_reading",
         "B133-5": "own_reading", "B133-6": "known_answer"}
FUNCS = {"B133-1": c1, "B133-2": c2, "B133-3": c3, "B133-4": c4, "B133-5": c5, "B133-6": c6}


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
    bad = copy.deepcopy(data)
    for y in bad["v"]["DPCCRG"]:
        bad["v"]["DPCCRG"][y] *= 1.004 ** (y - 1929)
    assert not c6(bad)[0], "B133-6 must fail when the published core index runs away from both operators"
    bad = copy.deepcopy(data)
    bad["v"]["DPENRC"] = {}
    assert not c4(bad)[0], "B133-4 must fail without the providers of line 107"
    # a two-good case with no rounding: prices (1, 1) -> (2, 1.1), quantities (1, 1) -> (2, 1).
    # Taking the first good out leaves the second, whose price rose 10 %. Neither operator is exact
    # (each has only the total's Fisher index, not its Laspeyres and Paasche halves); the test is that
    # each runs on the case and that the Fisher removal lands nearer.
    p0, p1, q0, q1 = (1.0, 1.0), (2.0, 1.1), (1.0, 1.0), (2.0, 1.0)
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    f_p = math.sqrt(dot(p1, q0) / dot(p0, q0) * dot(p1, q1) / dot(p0, q1))
    f_q = math.sqrt(dot(p0, q1) / dot(p0, q0) * dot(p1, q1) / dot(p1, q0))
    w = [q1[i] / f_q + q0[i] for i in range(2)]          # the weights of the Fisher price contributions
    contrib_1 = 100 * w[0] * (p1[0] - p0[0]) / sum(w[i] * p0[i] for i in range(2))
    toy = {"DPCERG": {0: 100.0, 1: 100.0 * f_p}, "DPCERC": {0: dot(p0, q0), 1: dot(p1, q1)},
           "P1": {0: 100.0, 1: 200.0}, "C1": {0: p0[0] * q0[0], 1: p1[0] * q1[0]}, "K1": {1: contrib_1}}
    item = {"contrib": ("K1",), "price": ("P1",), "nominal": ("C1",)}
    by_c, by_f = rest_change(toy, 1, item, "contributions"), rest_change(toy, 1, item, "fisher")
    assert abs(by_c - 8.371815) < 1e-5 and abs(by_f - 10.0) < abs(by_c - 10.0), (by_c, by_f)
    print("selftest ok: all six flags pass on the data and each fails on its planted error; on a two-good "
          f"case whose remaining good rose 10 %, the contributions operator gives {by_c:.3f} % and the "
          f"Fisher removal {by_f:.3f} %")


def main() -> int:
    data = load_all()
    res = build(data)
    crit = []
    for name, (passed, detail, obj) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
        crit.append({"name": name, "kind": KINDS[name], "passed": passed, "detail": detail})
    record = {"stage": "B133", "criteria": crit, "objects": {n: o for n, (_, _, o) in res.items()},
              "config": {"main_windows": MAIN, "starts": [min(STARTS), max(STARTS)],
                         "ends": [min(ENDS), max(ENDS)], "epi_tolerance": EPI_TOL,
                         "operators": {"contributions": "(PCE change - BEA contributions) / (1 - previous-year share)",
                                       "fisher": "geometric mean of a Laspeyres and a Paasche removal from the "
                                                 "items' Fisher price indexes and current-dollar values"},
                         "borrowed_items": {"DOWN": "imputed rental of owner-occupied nonfarm housing (line 21)",
                                            "DIMP": "financial services furnished without payment (line 107)"}}}
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
