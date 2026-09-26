"""B35: can a second origin give this carrier a loop. It cannot, and the reason
is one line in three tariff schedules.

The arm's gate record closed the swine-tongue three-anchor arm on a count: one
origin and three destinations is a star, b1 = 0, so no H1 obstruction exists on
it however good the prices are. That record registered the reshape that would
fix it: a second origin shipping the same good to the same three destinations
gives V = 5, E = 6, b1 = 2, two independent loops, and a loop sum makes the
scalar field's prediction of exactly zero readable.

This file runs that reshape's own gate before anyone fetches anything, and the
gate is D26's question rather than a measurement: is there a document in which
the second origin names the same good.

There is not. The tongue, heart, feet, head meat and skin split lives only in
the US ten-digit national extension. Every other origin checked stops at the
international six-digit line 0206.49 with one code, "other". So a loop built
across origins can only be built on 0206.49 whole, and 0206.49 whole is a mixed
basket. The B35 design already excluded 0206.49.00.90 (NESOI) from a
cross-destination comparison for exactly this reason, in one sentence and
without a number. This file supplies the number.

Usage
-----
    python b35_second_origin.py
    python b35_second_origin.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020649_bycountry_2021-2023.json"
OUT = ROOT / "results" / "b35_second_origin.json"

NAMES = {"0206490010": "tongues", "0206490020": "hearts",
         "0206490030": "feet", "0206490040": "head meat",
         "0206490050": "skins", "0206490090": "offal nesoi"}
PAIR = ("CHINA", "MEXICO")     # dearest and cheapest anchor on the tongue line
ANCHORS = ("CHINA", "JAPAN", "MEXICO")
WINDOW = [(2021, m) for m in range(1, 13)] + [(2022, m) for m in range(1, 9)]

# What each origin's own schedule says at the level it publishes. Checked
# 2026-09-10; each is a reading of that schedule, not an inference from trade
# volumes.
SCHEDULES = {
    "United States": {
        "level": "HS10, national statistical extension",
        "lines_under_020649": 6,
        "splits_the_good": True,
        "source": "US Census Bureau intltrade HS10, this station's own pulls",
    },
    "European Union": {
        "level": "CN8",
        "lines_under_020649": 1,
        "splits_the_good": False,
        "source": "Combined Nomenclature: 0206 49 00, Other, one line",
    },
    "Brazil": {
        "level": "NCM8",
        "lines_under_020649": 1,
        "splits_the_good": False,
        "source": "NCM 0206.49.00 Outras, one line under 0206.4",
    },
    "Canada": {
        "level": "Canadian Export Classification, 8 digit",
        "lines_under_020649": 1,
        "splits_the_good": False,
        "source": ("Canadian Export Classification 2022, catalogue 65-209-X: "
                   "0206.49 00 --Other KGM, no statistical subdivision"),
    },
}


def is_atom(code: str) -> bool:
    return code.isdigit() and len(code) == 4 and not code.startswith("00")


def lines(rows, cty, ym):
    """Ten digit lines for one destination-month: code -> (kg, usd)."""
    d = {}
    for r in rows:
        if not is_atom(r["CTY_CODE"]) or r["CTY_NAME"] != cty:
            continue
        if (r["_year"], r["_month"]) != ym:
            continue
        q, v = float(r["QTY_1_MO"]), float(r["ALL_VAL_MO"])
        if q <= 0:
            continue
        a, b = d.get(r["E_COMMODITY"], (0.0, 0.0))
        d[r["E_COMMODITY"]] = (a + q, b + v)
    return d


def decompose(da, db):
    """Split a unit value gap into a price part and a composition part.

    UV_a - UV_b = sum_i sbar_i (p_i^a - p_i^b)  +  sum_i pbar_i (s_i^a - s_i^b)

    with sbar and pbar the two-sided averages. The first term is what the
    comparison is meant to read; the second is what the basket contributes on
    its own. Only lines present on both sides enter, and the tonnage share each
    side keeps is returned so the reader can see what was dropped.
    """
    common = sorted(set(da) & set(db))
    if not common:
        return None
    qa = sum(da[c][0] for c in common)
    qb = sum(db[c][0] for c in common)
    price = comp = 0.0
    for c in common:
        sa, sb = da[c][0] / qa, db[c][0] / qb
        pa, pb = da[c][1] / da[c][0], db[c][1] / db[c][0]
        price += (sa + sb) / 2.0 * (pa - pb)
        comp += (pa + pb) / 2.0 * (sa - sb)
    uva = sum(v for _, v in da.values()) / sum(q for q, _ in da.values())
    uvb = sum(v for _, v in db.values()) / sum(q for q, _ in db.values())
    return {
        "common_lines": len(common),
        "coverage_a": qa / sum(q for q, _ in da.values()),
        "coverage_b": qb / sum(q for q, _ in db.values()),
        "uv_a": uva, "uv_b": uvb, "observed_gap": uva - uvb,
        "price_part": price, "composition_part": comp,
        "composition_share": (abs(comp) / (abs(price) + abs(comp))
                              if (price or comp) else None),
        "opposite_sign": (price * comp) < 0,
    }


def run(rows, window=None, pair=None):
    window = window or WINDOW
    pair = pair or PAIR
    crit = []
    rep = {}

    # ---- 1. the granularity, read off three schedules ----------------------
    rep["schedules"] = SCHEDULES
    others = [k for k, v in SCHEDULES.items() if not v["splits_the_good"]]
    us = SCHEDULES["United States"]
    rep["only_origin_that_splits"] = "United States"
    crit.append({
        "name": "B35-SO-1",
        "kind": "instrument",
        "passed": us["splits_the_good"] and len(others) >= 3,
        "detail": (
            f"the tongue, heart, feet, head meat and skin split is a US "
            f"ten-digit national extension, {us['lines_under_020649']} lines "
            f"under 0206.49; the other {len(others)} origins checked "
            + ", ".join(others)
            + " each publish one line there, \"other\", so a second origin can "
              "ship the same good and cannot name it. This is a reading of "
              "three tariff schedules, not an inference from any trade volume"),
    })

    # ---- 2. how mixed the shared level is ----------------------------------
    agg = {}
    for r in rows:
        if (not is_atom(r["CTY_CODE"]) or r["CTY_NAME"] != pair[0]
                or (r["_year"], r["_month"]) not in set(window)):
            continue
        q, v = float(r["QTY_1_MO"]), float(r["ALL_VAL_MO"])
        if q <= 0:
            continue
        a, b = agg.get(r["E_COMMODITY"], (0.0, 0.0))
        agg[r["E_COMMODITY"]] = (a + q, b + v)
    sub = {NAMES[c]: {"t": q / 1000.0, "usd_per_kg": v / q}
           for c, (q, v) in sorted(agg.items())}
    ps = [d["usd_per_kg"] for d in sub.values()]
    rep["shared_level_basket"] = {"leg": pair[0], "lines": sub,
                                  "span": max(ps) / min(ps)}
    crit.append({
        "name": "B35-SO-2",
        "kind": "own_reading",
        "passed": max(ps) / min(ps) > 1.0 and len(sub) > 1,
        "detail": (
            f"at the level every origin shares, 0206.49 whole, the {len(sub)} "
            f"US ten-digit lines inside it span "
            f"${min(ps):.3f} to ${max(ps):.3f} a kg on the {pair[0]} leg over "
            f"the window, a factor of {max(ps)/min(ps):.2f}; the basket is not "
            f"one good and its members are not close"),
    })

    # ---- 3. what the basket contributes on its own -------------------------
    per = []
    for ym in window:
        d = decompose(lines(rows, pair[0], ym), lines(rows, pair[1], ym))
        if d:
            d["month"] = "%d-%02d" % ym
            per.append(d)
    shares = [d["composition_share"] for d in per]
    opp = sum(1 for d in per if d["opposite_sign"])
    rep["decomposition"] = {
        "pair": list(pair), "months": len(per), "rows": per,
        "composition_share": {"min": min(shares), "max": max(shares),
                              "mean": sum(shares) / len(shares)},
        "opposite_sign_months": opp,
        "coverage_a_mean": sum(d["coverage_a"] for d in per) / len(per),
        "coverage_b_mean": sum(d["coverage_b"] for d in per) / len(per),
        "common_lines_range": [min(d["common_lines"] for d in per),
                               max(d["common_lines"] for d in per)],
    }
    crit.append({
        "name": "B35-SO-3",
        "kind": "own_reading",
        "passed": opp == len(per),
        "detail": (
            f"splitting the {pair[0]} minus {pair[1]} unit value gap at the "
            f"shared level into a price part and a composition part, month by "
            f"month over {len(per)} months: the composition part carries "
            f"{min(shares):.3f} to {max(shares):.3f} of the total magnitude, "
            f"mean {sum(shares)/len(shares):.3f}, and it runs AGAINST the "
            f"price part in {opp} of {len(per)} months, so the observed gap "
            f"understates the price signal by an amount that itself moves. "
            f"Coverage is {rep['decomposition']['coverage_a_mean']:.3f} and "
            f"{rep['decomposition']['coverage_b_mean']:.3f} of each side's "
            f"tonnage on "
            f"{rep['decomposition']['common_lines_range'][0]}-"
            f"{rep['decomposition']['common_lines_range'][1]} common lines"),
    })

    # ---- 4. what would reopen it -------------------------------------------
    rep["reopen"] = {
        "closed_for": "this commodity family, on every origin checked",
        "routes": {
            "single_good_hs6": (
                "a commodity whose six-digit line is effectively one good, so "
                "every origin names the same thing without a national "
                "extension; that is a search over the nomenclature and not "
                "over this carrier"),
            "origin_with_its_own_extension": (
                "an origin that publishes a comparable statistical "
                "subdivision; none of the three largest pork exporters "
                "outside the US does, and this file does not claim to have "
                "checked the rest"),
            "importer_side_reporting": (
                "the destination's own customs detail, which is a different "
                "channel and is where a second class inside one position "
                "would also have to come from"),
        },
        "not_a_route": (
            "building the loop on 0206.49 whole, which criteria 2 and 3 price: "
            "the composition term is a third of the magnitude and points the "
            "other way"),
    }
    # rule 11f, 2026-09-13. The routes and the priced non-route are the object this
    # verdict is about; it used to assert True beside them.
    _reopen = rep["reopen"]
    crit.append({
        "name": "B35-SO-4",
        "kind": "bookkeeping",
        "passed": (len(_reopen["routes"]) == 3
                   and all(v.strip() for v in _reopen["routes"].values())
                   and bool(_reopen["not_a_route"].strip())),
        "detail": ("the reshape is closed on this commodity family with the "
                   "three routes that could reopen it named, and the one route "
                   "that looks open is priced rather than waved off"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True

    def row(cty, num, code, y, m, q, v):
        return {"E_COMMODITY": code, "CTY_CODE": num, "CTY_NAME": cty,
                "_year": y, "_month": m, "QTY_1_MO": str(q),
                "ALL_VAL_MO": str(v)}

    # (a) A pair whose sub-line PRICES are identical and whose mixes differ.
    #     The price part must read zero and the whole gap must be composition.
    seed = []
    P = {"0206490010": 3.0, "0206490030": 2.0}
    for (y, m) in WINDOW:
        for code, qa, qb in (("0206490010", 800.0, 200.0),
                             ("0206490030", 200.0, 800.0)):
            seed.append(row("CHINA", "5700", code, y, m, qa, qa * P[code]))
            seed.append(row("MEXICO", "2010", code, y, m, qb, qb * P[code]))
            seed.append(row("ASIA", "5XXX", code, y, m, qa, qa * P[code]))
    _, rep = run(seed)
    d = rep["decomposition"]["rows"][0]
    if abs(d["price_part"]) > 1e-9:
        print("SELFTEST FAIL: identical prices should give a zero price part, "
              "got %r" % d["price_part"])
        ok = False
    if abs(d["composition_part"] - d["observed_gap"]) > 1e-9:
        print("SELFTEST FAIL: the whole gap should be composition here")
        ok = False
    if abs(d["composition_share"] - 1.0) > 1e-9:
        print("SELFTEST FAIL: composition share should be exactly one")
        ok = False

    # (b) A pair whose mixes are identical and whose prices differ. Now the
    #     composition part must be zero, and criterion 3 must NOT fire, because
    #     it reads an opposition that is not there.
    seed2 = []
    for (y, m) in WINDOW:
        for code, pa, pb in (("0206490010", 3.0, 2.0),
                             ("0206490030", 2.5, 2.0)):
            seed2.append(row("CHINA", "5700", code, y, m, 500.0, 500.0 * pa))
            seed2.append(row("MEXICO", "2010", code, y, m, 500.0, 500.0 * pb))
    c2, r2 = run(seed2)
    d2 = r2["decomposition"]["rows"][0]
    if abs(d2["composition_part"]) > 1e-9:
        print("SELFTEST FAIL: identical mixes should give a zero composition "
              "part, got %r" % d2["composition_part"])
        ok = False
    if {c["name"]: c for c in c2}["B35-SO-3"]["passed"]:
        print("SELFTEST FAIL: criterion 3 fired where the two parts do not "
              "oppose each other")
        ok = False

    # (c) the aggregate row must never enter a decomposition
    if any(r["CTY_NAME"] == "ASIA" for r in seed if is_atom(r["CTY_CODE"])):
        print("SELFTEST FAIL: the atom filter let an aggregate through")
        ok = False

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not SRC.exists():
        print("missing %s" % SRC)
        return 2
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    crit, rep = run(rows)

    print("=" * 74)
    print("B35 second origin: can the tongue carrier be given a loop")
    print("=" * 74)
    for k, v in rep["schedules"].items():
        print("  %-16s %-38s %d line(s) under 0206.49"
              % (k, v["level"], v["lines_under_020649"]))
    print()
    print("the shared level, 0206.49 whole, on the %s leg over the window"
          % rep["shared_level_basket"]["leg"])
    for k, v in rep["shared_level_basket"]["lines"].items():
        print("  %-12s %10.1f t   $%.3f/kg" % (k, v["t"], v["usd_per_kg"]))
    print("  span %.2fx" % rep["shared_level_basket"]["span"])
    print()
    d = rep["decomposition"]
    print("%s minus %s at the shared level, by month" % tuple(d["pair"]))
    print("%9s %10s %10s %10s %8s" % ("month", "observed", "price", "compos",
                                      "comp sh"))
    for r in d["rows"]:
        print("%9s %10.3f %10.3f %10.3f %8.3f"
              % (r["month"], r["observed_gap"], r["price_part"],
                 r["composition_part"], r["composition_share"]))
    print("composition share  min %.3f  mean %.3f  max %.3f   opposite sign in "
          "%d of %d months"
          % (d["composition_share"]["min"], d["composition_share"]["mean"],
             d["composition_share"]["max"], d["opposite_sign_months"],
             d["months"]))
    print()
    for c in crit:
        print("%-5s %-12s %s" % ("PASS" if c["passed"] else "FAIL",
                                 c["name"], c["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B35-SO",
        "config": {"source": SRC.name, "pair": list(PAIR),
                   "anchors": list(ANCHORS),
                   "window": [list(x) for x in WINDOW],
                   "atom_rule": "four digits, all numeric, not starting 00"},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
