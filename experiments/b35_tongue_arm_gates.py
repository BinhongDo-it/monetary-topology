"""B35: the pre-opening gates on the swine-tongue three-anchor arm.

The arm was registered at cell one of B35-8's read-out ("two or more countries
at ten per cent each, present in every month: open the arm") and never given a
reading. The D23 gate then narrowed it, and the three-year panel widened the
usable window from eight months to twenty. Two gates were still owed before it
opened, the independent count and the resolution floor, and this file runs them
plus the two counting gates that come before both.

The order is the one the discipline fixes, cheapest and most decisive first:

  1. the window and the anchors, printed
  2. D22, the independent-loop count on the graph the arm would use. Pure
     counting, no data, and it can close the arm on its own
  3. D25's third question in its counting form: how many classes sit at each
     position, because a square needs two at each of two
  4. the object itself, printed rather than judged
  5. D24, the resolution floor, measured on this subset rather than asserted
  6. what would have to change for this carrier to carry a square, registered
     and not fetched

Gates two and three are the reason this file exists. They cost nothing and they
decide what kind of reading this carrier can produce at all, which is a
different question from whether the numbers are good enough.

Usage
-----
    python b35_tongue_arm_gates.py
    python b35_tongue_arm_gates.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020649_bycountry_2021-2023.json"
OUT = ROOT / "results" / "b35_tongue_arm_gates.json"

TONG = "0206490010"
ANCHORS = ("CHINA", "JAPAN", "MEXICO")
# 2022-09 is the break the D23 gate found, so the window ends at 2022-08. It
# starts at 2021-01 because that is where the panel starts, not because anything
# was searched over.
WINDOW = [(2021, m) for m in range(1, 13)] + [(2022, m) for m in range(1, 9)]
KG_PER_LB = 2.20462262185
SHARE_FLOOR = 0.10          # the read-out's own cell-one line, not a new number


def is_atom(code: str) -> bool:
    return code.isdigit() and len(code) == 4 and not code.startswith("00")


def cell(rows, cty, ym):
    q = v = 0.0
    for r in rows:
        if r["E_COMMODITY"] != TONG or not is_atom(r["CTY_CODE"]):
            continue
        if r["CTY_NAME"] != cty or (r["_year"], r["_month"]) != ym:
            continue
        q += float(r["QTY_1_MO"])
        v += float(r["ALL_VAL_MO"])
    return q, v


def betti_one(vertices: int, edges: int) -> int:
    """b1 = E - V + 1 for a connected graph. D22's whole arithmetic."""
    return edges - vertices + 1


def run(rows, window=None, anchors=None):
    window = window or WINDOW
    anchors = anchors or ANCHORS
    crit = []
    rep = {}

    # ---- 1. the window and the anchors -------------------------------------
    tot = {}
    for ym in window:
        s = 0.0
        for r in rows:
            if (r["E_COMMODITY"] == TONG and is_atom(r["CTY_CODE"])
                    and (r["_year"], r["_month"]) == ym):
                s += float(r["QTY_1_MO"])
        tot[ym] = s
    grand = sum(tot.values())
    shares, present = {}, {}
    everyone = {}
    for r in rows:
        if (r["E_COMMODITY"] != TONG or not is_atom(r["CTY_CODE"])
                or (r["_year"], r["_month"]) not in set(window)):
            continue
        q = float(r["QTY_1_MO"])
        if q <= 0:
            continue
        everyone[r["CTY_NAME"]] = everyone.get(r["CTY_NAME"], 0.0) + q
        present.setdefault(r["CTY_NAME"], set()).add((r["_year"], r["_month"]))
    for c in anchors:
        shares[c] = everyone.get(c, 0.0) / grand
    others = sorted(((v / grand, k) for k, v in everyone.items()
                     if k not in anchors), reverse=True)
    rep["window_months"] = len(window)
    rep["anchor_share"] = shares
    rep["anchor_months_present"] = {c: len(present.get(c, ())) for c in anchors}
    rep["next_destination"] = ({"name": others[0][1], "share": others[0][0]}
                               if others else None)
    ok1 = (all(shares[c] >= SHARE_FLOOR for c in anchors)
           and all(len(present.get(c, ())) == len(window) for c in anchors))
    crit.append({
        "name": "B35-TG-1",
        "kind": "instrument",
        "passed": bool(ok1),
        "detail": (
            f"{len(window)} consecutive months, 2021-01 through 2022-08, the "
            f"span this code carries one good on every leg; "
            + ", ".join(f"{c} {shares[c]*100:.1f}%" for c in anchors)
            + f", each present in all {len(window)} months, and the next "
              f"destination is {rep['next_destination']['name']} at "
              f"{rep['next_destination']['share']*100:.1f}%; the read-out's "
              f"cell one wanted twelve months and two anchors, and this is "
              f"twenty months and three"),
    })

    # ---- 2. D22: the independent loop count --------------------------------
    # The graph the arm would use has one origin and three destinations, and
    # one edge per shipping leg. Nothing about the price data enters this.
    V = 1 + len(anchors)
    E = len(anchors)
    b1 = betti_one(V, E)
    rep["d22"] = {
        "vertices": V, "edges": E, "b1": b1,
        "shape": "star: one origin, one edge to each destination",
        "meaning": ("b1 is the number of independent closed loops, and an "
                    "obstruction of the H1 kind lives on a loop; a star has "
                    "none, so no amount of price dispersion here can form one"),
        "what_would_change_it": ("a second origin shipping the same good to the "
                                 "same three destinations gives V=5, E=6, b1=2"),
    }
    crit.append({
        "name": "B35-TG-2",
        "kind": "known_answer",
        "passed": b1 == 0,
        "detail": (
            f"the carrier as configured is a star, {V} vertices and {E} edges, "
            f"so b1 = E - V + 1 = {b1}; there is no independent loop on it and "
            f"therefore no H1 obstruction to read, whatever the prices do. A "
            f"second origin on the same three destinations would give "
            f"V=5, E=6, b1=2. This costs nothing and it is decisive, which is "
            f"why it runs before the floor and the count"),
    })

    # ---- 3. how many classes sit at each position --------------------------
    # A square needs two classes at each of two positions. Here each position
    # is a destination and each has exactly one buyer class in this feed, so
    # the square sum has no second term to take a difference against.
    classes = {c: 1 for c in anchors}
    rep["classes_per_position"] = classes
    rep["square_available"] = False
    rep["reading_available"] = ("H0 and dispersion: which class reaches which "
                                "position and at what price, with the price "
                                "difference between positions explainable by a "
                                "potential on the positions")
    crit.append({
        "name": "B35-TG-3",
        "kind": "known_answer",
        "passed": all(v < 2 for v in classes.values()),
        "detail": (
            "a square needs two classes at each of two positions and this feed "
            "gives one buyer class per destination, so the square sum has no "
            "second term; the reading this carrier supports is dispersion "
            "across positions, and a scalar field with one potential per "
            "position accounts for that, which places it in the common-answer "
            "cell rather than the distinguishing one"),
    })

    # ---- 4. the object, printed --------------------------------------------
    series, gaps, sds, top = [], [], [], {}
    for ym in window:
        ps = {}
        for c in anchors:
            q, v = cell(rows, c, ym)
            ps[c] = v / q if q else None
        vals = [ps[c] for c in anchors]
        if any(v is None for v in vals):
            continue
        lo, hi = min(vals), max(vals)
        gaps.append(hi - lo)
        sds.append(statistics.pstdev([math.log(v) for v in vals]))
        top[max(ps, key=ps.get)] = top.get(max(ps, key=ps.get), 0) + 1
        series.append({"month": "%d-%02d" % ym,
                       **{c: round(ps[c], 4) for c in anchors},
                       "max_over_min": hi / lo, "sd_log": sds[-1]})
    rep["series"] = series
    rep["max_over_min"] = {"min": min(s["max_over_min"] for s in series),
                           "max": max(s["max_over_min"] for s in series),
                           "mean": sum(s["max_over_min"] for s in series) / len(series)}
    rep["sd_log"] = {"min": min(sds), "max": max(sds),
                     "mean": sum(sds) / len(sds)}
    rep["most_expensive_anchor_count"] = top
    rep["cheapest_anchor_count"] = {}
    for ym_row in series:
        vals = {c: ym_row[c] for c in anchors}
        k = min(vals, key=vals.get)
        rep["cheapest_anchor_count"][k] = rep["cheapest_anchor_count"].get(k, 0) + 1
    crit.append({
        "name": "B35-TG-4",
        "kind": "own_reading",
        "passed": min(s["max_over_min"] for s in series) > 1.0,
        "detail": (
            f"one good, one origin, three destinations, {len(series)} months: "
            f"the most expensive anchor is between "
            f"{rep['max_over_min']['min']:.3f} and "
            f"{rep['max_over_min']['max']:.3f} times the cheapest, mean "
            f"{rep['max_over_min']['mean']:.3f}, and the gap never closes; the "
            f"ordering is stable, with "
            + ", ".join(f"{k} dearest in {v} of {len(series)}"
                        for k, v in sorted(top.items(), key=lambda kv: -kv[1]))
            + ", and "
            + ", ".join(f"{k} cheapest in {v}"
                        for k, v in sorted(rep["cheapest_anchor_count"].items(),
                                           key=lambda kv: -kv[1]))),
    })

    # ---- 5. D24: the floor, measured ---------------------------------------
    near, n = 0, 0
    for r in rows:
        if (r["E_COMMODITY"] != TONG or not is_atom(r["CTY_CODE"])
                or (r["_year"], r["_month"]) not in set(window)):
            continue
        q, v = float(r["QTY_1_MO"]), float(r["ALL_VAL_MO"])
        if q <= 0:
            continue
        n += 1
        cents = v / q / KG_PER_LB * 100.0
        if abs(cents - round(cents)) < 0.01:
            near += 1
    floor = 0.01 * KG_PER_LB
    rep["d24"] = {"rows": n, "on_a_whole_cent_per_lb": near,
                  "rate": near / n, "uniform_expectation": 0.0002,
                  "floor_usd_per_kg": floor,
                  "smallest_monthly_gap": min(gaps),
                  "gap_over_floor_min": min(gaps) / floor,
                  "gap_over_floor_mean": (sum(gaps) / len(gaps)) / floor}
    crit.append({
        "name": "B35-TG-5",
        "kind": "instrument",
        "passed": min(gaps) / floor > 1.0,
        "detail": (
            f"the floor is measured, not asserted: {near} of {n} destination "
            f"months land within 1e-4 of a whole cent per pound against a "
            f"uniform expectation of 0.02 per cent, so the grid is one cent a "
            f"pound, ${floor:.4f} a kg; the thinnest monthly gap between the "
            f"dearest and cheapest anchor is ${min(gaps):.3f} a kg, "
            f"{min(gaps)/floor:.1f} times that floor, and the mean gap is "
            f"{(sum(gaps)/len(gaps))/floor:.1f} times it"),
    })

    # ---- 6. what would have to change, registered --------------------------
    rep["reshape"] = {
        "status": "registered, not fetched",
        "why": ("gate two is what closes this arm, and it closes it on shape "
                "rather than on data quality: twenty clean months on a star "
                "still have b1 = 0"),
        "second_origin": {
            "b1_after": betti_one(5, 6),
            "candidates": ["EU exports by partner, Eurostat Comext",
                           "Brazil exports by partner, Comex Stat",
                           "Canada exports by partner, Statistics Canada"],
            "what_it_buys": ("two independent loops, so a loop sum exists and "
                             "the scalar-field prediction of exactly zero "
                             "becomes readable on this carrier"),
        },
        "second_class_at_one_position": {
            "what_it_would_be": ("two buyer classes inside one destination "
                                 "paying different prices for the same code, "
                                 "which this feed cannot see because it stops "
                                 "at the border"),
            "where_it_would_come_from": ("the importing country's own customs "
                                         "or wholesale reporting, which is a "
                                         "different channel from this one"),
        },
    }
    # rule 11f, 2026-09-13: two routes, each naming what it buys and where the data
    # sits. That is three counts, and the verdict used to be a literal True.
    _routes = [rep["reshape"]["second_origin"],
               rep["reshape"]["second_class_at_one_position"]]
    crit.append({
        "name": "B35-TG-6",
        "kind": "bookkeeping",
        "passed": (len(_routes) == 2
                   and all(r.get("what_it_buys") or r.get("what_it_would_be")
                           for r in _routes)
                   and all(r.get("where_it_would_come_from") or r.get("candidates")
                           for r in _routes)),
        "detail": ("the two routes that would give this carrier a loop or a "
                   "square are named with what each buys and where the data "
                   "sits; neither is fetched here, and the arm stays shut on "
                   "the counting gate rather than on any number"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True
    # b1 arithmetic, on shapes whose answer is known by hand.
    for v, e, want in ((4, 3, 0), (5, 6, 2), (3, 3, 1), (2, 1, 0)):
        if betti_one(v, e) != want:
            print("SELFTEST FAIL: b1(%d,%d) = %d, want %d"
                  % (v, e, betti_one(v, e), want))
            ok = False

    def row(cty, code_num, y, m, q, v):
        return {"E_COMMODITY": TONG, "CTY_CODE": code_num, "CTY_NAME": cty,
                "_year": y, "_month": m, "QTY_1_MO": str(q),
                "ALL_VAL_MO": str(v)}

    # Three anchors at known shares and known prices, plus one aggregate row
    # that must not be counted and one small fourth destination that must not
    # displace an anchor.
    seed = []
    for (y, m) in WINDOW:
        for cty, num, q, p in (("CHINA", "5700", 300.0, 3.00),
                               ("JAPAN", "5880", 300.0, 2.50),
                               ("MEXICO", "2010", 300.0, 2.00),
                               ("PERU", "3330", 12.0, 2.20)):
            seed.append(row(cty, num, y, m, q, q * p))
        seed.append(row("ASIA", "5XXX", y, m, 600.0, 1650.0))
    crit, rep = run(seed)
    by = {c["name"]: c for c in crit}
    if not by["B35-TG-1"]["passed"]:
        print("SELFTEST FAIL: three equal anchors should clear the window gate")
        ok = False
    if rep["d22"]["b1"] != 0:
        print("SELFTEST FAIL: a star should read b1 = 0")
        ok = False
    if abs(rep["max_over_min"]["mean"] - 1.5) > 1e-9:
        print("SELFTEST FAIL: seeded 3.00/2.00, read %r"
              % rep["max_over_min"]["mean"])
        ok = False
    if rep["most_expensive_anchor_count"].get("CHINA") != len(WINDOW):
        print("SELFTEST FAIL: CHINA was seeded dearest in every month")
        ok = False
    if abs(rep["anchor_share"]["CHINA"] - 300.0 / 912.0) > 1e-9:
        print("SELFTEST FAIL: the aggregate row leaked into the shares (%r)"
              % rep["anchor_share"]["CHINA"])
        ok = False

    # An anchor that drops a month must fail gate one, or gate one reads nothing.
    seed2 = [r for r in seed
             if not (r["CTY_NAME"] == "JAPAN" and r["_year"] == 2021
                     and r["_month"] == 5)]
    c2, _ = run(seed2)
    if {c["name"]: c for c in c2}["B35-TG-1"]["passed"]:
        print("SELFTEST FAIL: a missing anchor month should close gate one")
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
    print("B35 swine-tongue three-anchor arm: the gates before it opens")
    print("=" * 74)
    print("window %d months, anchors %s"
          % (rep["window_months"],
             ", ".join("%s %.1f%% (%d/%d months)"
                       % (c, rep["anchor_share"][c] * 100,
                          rep["anchor_months_present"][c], rep["window_months"])
                       for c in ANCHORS)))
    print("next destination: %s at %.1f%%"
          % (rep["next_destination"]["name"],
             rep["next_destination"]["share"] * 100))
    print()
    print("D22: V=%d E=%d b1=%d   (%s)"
          % (rep["d22"]["vertices"], rep["d22"]["edges"], rep["d22"]["b1"],
             rep["d22"]["shape"]))
    print("classes per position: %s" % rep["classes_per_position"])
    print()
    print("%9s %8s %8s %8s %9s %9s" % ("month", *ANCHORS, "max/min", "sd log"))
    for s in rep["series"]:
        print("%9s %8.3f %8.3f %8.3f %9.3f %9.4f"
              % (s["month"], *[s[c] for c in ANCHORS],
                 s["max_over_min"], s["sd_log"]))
    print("max/min  min %.3f  mean %.3f  max %.3f"
          % (rep["max_over_min"]["min"], rep["max_over_min"]["mean"],
             rep["max_over_min"]["max"]))
    print("dearest: %s      cheapest: %s"
          % (rep["most_expensive_anchor_count"], rep["cheapest_anchor_count"]))
    print()
    d = rep["d24"]
    print("D24 floor: %d of %d rows on a whole cent per lb (%.1f%%), grid "
          "$%.4f/kg; thinnest gap $%.3f = %.1fx floor, mean %.1fx"
          % (d["on_a_whole_cent_per_lb"], d["rows"], d["rate"] * 100,
             d["floor_usd_per_kg"], d["smallest_monthly_gap"],
             d["gap_over_floor_min"], d["gap_over_floor_mean"]))
    print()
    for c in crit:
        print("%-5s %-12s %s" % ("PASS" if c["passed"] else "FAIL",
                                 c["name"], c["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B35-TG",
        "config": {"source": SRC.name, "window": [list(x) for x in WINDOW],
                   "anchors": list(ANCHORS), "share_floor": SHARE_FLOOR,
                   "atom_rule": "four digits, all numeric, not starting 00"},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
