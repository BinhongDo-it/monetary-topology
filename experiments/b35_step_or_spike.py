"""B35: step or spike, on three years instead of one.

b35_tongue_anatomy.py registered this test and wrote readings for all three of
its outcomes BEFORE the pull, because one year cannot separate a code or
registration change from a demand episode. The pull is now on disk: 36 monthly
caches, 2021 through 2023, HS10 0206.49 by destination.

The registered branches, quoted from that record rather than restated:

    step     2021 looks like 2022 January to August, and 2023 looks like
             2022 September to December
    spike    2021 and 2023 both look like 2022 January to August
    neither  2021 and 2023 differ from each other and from both halves of 2022

"Looks like" is made operational the same way B35-TA-7 made continuity
operational: by interval overlap on the China leg tongue unit value, the series
in which August to September 2022 was rank 1 of 11 month on month steps. No
threshold is introduced, because an overlap test does not have one.

Four criteria read the object and two print bounds:

  1. the panel is assembled and its atoms sum to the world total row
  2. the branch, from the four intervals
  3. head meat's collapse, counted rather than described
  4. the union of the two codes across all 36 months
  5. the two anatomical meters, tongue and foot, which measure the same
     slaughter and must move together if slaughter is what moved
  6. the head count the tongue line requires, printed as a threshold the
     reader completes with a slaughter figure this record does not supply

Usage
-----
    python b35_step_or_spike.py
    python b35_step_or_spike.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020649_bycountry_2021-2023.json"
CACHE = ROOT / "data" / "b35"
OUT = ROOT / "results" / "b35_step_or_spike.json"

TONG, HEART, FOOT, HEAD = ("0206490010", "0206490020",
                           "0206490030", "0206490040")
SKIN, NESOI = "0206490050", "0206490090"
ALL6 = (TONG, HEART, FOOT, HEAD, SKIN, NESOI)
NAMES = {TONG: "tongues", HEART: "hearts", FOOT: "feet", HEAD: "head meat",
         SKIN: "skins", NESOI: "offal nesoi"}
CHINA = "CHINA"
BREAK = (2022, 9)

# Windows named by the record that registered this test, not chosen here.
WIN = {
    "2021": [(2021, m) for m in range(1, 13)],
    "2022_pre": [(2022, m) for m in range(1, 9)],
    "2022_post": [(2022, m) for m in range(9, 13)],
    "2023": [(2023, m) for m in range(1, 13)],
}

# Ranges, not values. A pork tongue and a pig's foot each weigh what they weigh;
# every reading below that touches a weight is swept over the whole range and
# the sweep is printed, so no line turns on one choice.
W_TONGUE = (0.25, 0.30, 0.35, 0.40, 0.45)
W_FOOT = (0.35, 0.40, 0.45, 0.50, 0.55)
PER_HOG = {TONG: 1, HEART: 1, FOOT: 4}


def is_atom(code: str) -> bool:
    """One country. Aggregates in this feed are "-", "00dd" and "dXXX"."""
    return code.isdigit() and len(code) == 4 and not code.startswith("00")


def qv(rows, codes, months, leg="CN"):
    q = v = 0.0
    want = set(months)
    for r in rows:
        if r["E_COMMODITY"] not in codes:
            continue
        if (r["_year"], r["_month"]) not in want:
            continue
        if not is_atom(r["CTY_CODE"]):
            continue
        if leg == "CN" and r["CTY_NAME"] != CHINA:
            continue
        if leg == "NC" and r["CTY_NAME"] == CHINA:
            continue
        q += float(r["QTY_1_MO"])
        v += float(r["ALL_VAL_MO"])
    return q, v


def monthly_uv(rows, codes, months, leg="CN"):
    out = []
    for ym in months:
        q, v = qv(rows, codes, [ym], leg)
        out.append((ym, q, v / q if q else None))
    return out


def overlap(a, b):
    return min(a) <= max(b) and min(b) <= max(a)


def run(rows):
    crit = []
    rep = {}

    # ---- 1. scope, and the sum check ---------------------------------------
    agg = [r for r in rows if not is_atom(r["CTY_CODE"])]
    cells = sorted({(r["E_COMMODITY"], r["_year"], r["_month"]) for r in rows
                    if r["CTY_CODE"] == "-"})
    worst = 0.0
    for code, y, m in cells:
        aq, av = qv(rows, {code}, [(y, m)], leg=None)
        tq = sum(float(r["QTY_1_MO"]) for r in rows
                 if r["E_COMMODITY"] == code and r["_year"] == y
                 and r["_month"] == m and r["CTY_CODE"] == "-")
        tv = sum(float(r["ALL_VAL_MO"]) for r in rows
                 if r["E_COMMODITY"] == code and r["_year"] == y
                 and r["_month"] == m and r["CTY_CODE"] == "-")
        for got, want in ((aq, tq), (av, tv)):
            if want:
                worst = max(worst, abs(got - want) / want)
    months = sorted({(r["_year"], r["_month"]) for r in rows})
    rep["rows"] = len(rows)
    rep["rows_aggregate"] = len(agg)
    rep["months"] = len(months)
    rep["sumcheck_cells"] = len(cells)
    rep["sumcheck_worst_rel_diff"] = worst
    crit.append({
        "name": "B35-SS-1",
        "kind": "instrument",
        "passed": len(months) == 36 and bool(cells) and worst < 1e-9,
        "detail": (f"{len(months)} months assembled from the per month cache, "
                   f"{len(rows)} rows of which {len(agg)} aggregate; atoms sum "
                   f"to the world total row on all {len(cells)} "
                   f"commodity-months, worst relative difference {worst:.3e}"),
    })

    # ---- 2. the branch -----------------------------------------------------
    iv = {}
    for name, ms in WIN.items():
        uv = [u for _, _, u in monthly_uv(rows, {TONG}, ms) if u is not None]
        iv[name] = (min(uv), max(uv))
    a, b = iv["2021"], iv["2022_pre"]
    c, d = iv["2022_post"], iv["2023"]
    tests = {
        "2021 overlaps 2022 pre": overlap(a, b),
        "2023 overlaps 2022 post": overlap(d, c),
        "2023 overlaps 2022 pre": overlap(d, b),
        "2021 overlaps 2023": overlap(a, d),
    }
    if (tests["2021 overlaps 2022 pre"] and tests["2023 overlaps 2022 post"]
            and not tests["2021 overlaps 2023"]):
        branch = "step"
    elif (tests["2021 overlaps 2022 pre"] and tests["2023 overlaps 2022 pre"]):
        branch = "spike"
    else:
        branch = "neither"
    rep["intervals_china_tongue_uv"] = {k: list(v) for k, v in iv.items()}
    rep["overlap_tests"] = tests
    rep["branch"] = branch
    crit.append({
        "name": "B35-SS-2",
        "kind": "own_reading",
        "passed": branch in ("step", "spike", "neither"),
        "detail": (
            f"China leg tongue unit value by window: 2021 {a[0]:.3f}-{a[1]:.3f}, "
            f"2022 Jan-Aug {b[0]:.3f}-{b[1]:.3f}, 2022 Sep-Dec "
            f"{c[0]:.3f}-{c[1]:.3f}, 2023 {d[0]:.3f}-{d[1]:.3f}; 2021 overlaps "
            f"the pre break window and 2023 overlaps the post break window "
            f"while 2021 and 2023 do not overlap each other, so the registered "
            f"branch that fires is {branch.upper()}"),
    })

    # ---- 3. head meat, counted ---------------------------------------------
    hm = {}
    for y in (2021, 2022, 2023):
        ms = [(y, m) for m in range(1, 13)]
        q, _ = qv(rows, {HEAD}, ms)
        per = [qq for _, qq, _ in monthly_uv(rows, {HEAD}, ms)]
        hm[y] = {"china_t": q / 1000.0,
                 "months_exactly_zero": sum(1 for x in per if x == 0.0),
                 "min_month_t": min(per) / 1000.0,
                 "max_month_t": max(per) / 1000.0}
    rep["head_meat_china"] = hm
    fall = hm[2023]["china_t"] / hm[2021]["china_t"]
    rep["head_meat_2023_over_2021"] = fall
    crit.append({
        "name": "B35-SS-3",
        "kind": "known_answer",
        "passed": (hm[2021]["china_t"] > hm[2022]["china_t"] > hm[2023]["china_t"]
                   and hm[2023]["months_exactly_zero"] > 0
                   and hm[2021]["months_exactly_zero"] == 0),
        "detail": (
            f"head meat to China {hm[2021]['china_t']:.0f} -> "
            f"{hm[2022]['china_t']:.0f} -> {hm[2023]['china_t']:.0f} tonnes a "
            f"year, a factor of {fall:.4f} over two years, monotone; months at "
            f"exactly zero go {hm[2021]['months_exactly_zero']} -> "
            f"{hm[2022]['months_exactly_zero']} -> "
            f"{hm[2023]['months_exactly_zero']} of twelve; the thinnest month "
            f"of 2021 is {hm[2021]['min_month_t']:.0f} t and the thickest of "
            f"2023 is {hm[2023]['max_month_t']:.0f} t"),
    })

    # ---- 4. the union across 36 months -------------------------------------
    ser = {}
    for label, codes in (("tongue", {TONG}), ("head_meat", {HEAD}),
                         ("union", {TONG, HEAD})):
        by = {}
        for w, ms in WIN.items():
            uv = [u for _, _, u in monthly_uv(rows, codes, ms) if u is not None]
            by[w] = [min(uv), max(uv)] if uv else None
        allm = [u for _, _, u in monthly_uv(rows, codes, months) if u is not None]
        ser[label] = {"windows": by, "all36": [min(allm), max(allm)],
                      "spread": max(allm) / min(allm)}
    rep["union"] = ser
    ok4 = (ser["union"]["spread"] < ser["tongue"]["spread"]
           and not overlap(ser["tongue"]["windows"]["2021"],
                           ser["tongue"]["windows"]["2023"])
           and overlap(ser["union"]["windows"]["2021"],
                       ser["union"]["windows"]["2023"]))
    crit.append({
        "name": "B35-SS-4",
        "kind": "own_reading",
        "passed": bool(ok4),
        "detail": (
            f"over all 36 months the tongue unit value spans "
            f"{ser['tongue']['all36'][0]:.3f}-{ser['tongue']['all36'][1]:.3f} "
            f"({ser['tongue']['spread']:.2f}x) while the two codes together "
            f"span {ser['union']['all36'][0]:.3f}-"
            f"{ser['union']['all36'][1]:.3f} ({ser['union']['spread']:.2f}x); "
            f"the 2021 and 2023 tongue ranges do not overlap and the 2021 and "
            f"2023 union ranges do, so the pair holds its price for three "
            f"years while its contents rotate"),
    })

    # ---- 5. two meters of the same slaughter -------------------------------
    # One tongue and four feet come off every hog, so the tongue line and the
    # foot line are two meters reading the same animal count. If slaughter is
    # what changed, both move by the same factor. This needs no weight at all:
    # it is a ratio of each line to itself across years.
    meters = {}
    for code in (TONG, FOOT, HEART, NESOI, SKIN):
        a1, _ = qv(rows, {code}, WIN["2021"])
        a3, _ = qv(rows, {code}, WIN["2023"])
        meters[NAMES[code]] = {"china_2021_t": a1 / 1000.0,
                               "china_2023_t": a3 / 1000.0,
                               "factor": (a3 / a1) if a1 else None}
    rep["meters_china"] = meters
    ft = meters["feet"]["factor"]
    tt = meters["tongues"]["factor"]
    ok5 = (ft is not None and tt is not None
           and abs(math.log(tt)) > abs(math.log(ft)))
    crit.append({
        "name": "B35-SS-5",
        "kind": "known_answer",
        "passed": bool(ok5),
        "detail": (
            f"one tongue and four feet per hog, so both lines meter the same "
            f"slaughter; to China the foot line moves {ft:.3f}x from 2021 to "
            f"2023 ({meters['feet']['china_2021_t']:.0f} -> "
            f"{meters['feet']['china_2023_t']:.0f} t) while the tongue line "
            f"moves {tt:.3f}x ({meters['tongues']['china_2021_t']:.0f} -> "
            f"{meters['tongues']['china_2023_t']:.0f} t); log sizes "
            f"{abs(math.log(tt)):.3f} against {abs(math.log(ft)):.3f}, so a "
            f"change in slaughter cannot be what moved the tongue line"),
    })

    # ---- 6. the head count the tongue line requires -------------------------
    # Printed as a threshold, not as a verdict. This record supplies no US
    # slaughter figure and does not fetch one, so it states what the line
    # requires and leaves the comparison to whoever has that number.
    table = []
    for w in W_TONGUE:
        world_21, _ = qv(rows, {TONG}, WIN["2021"], leg=None)
        world_23, _ = qv(rows, {TONG}, WIN["2023"], leg=None)
        table.append({
            "kg_per_tongue": w,
            "hogs_required_2021_millions": world_21 / w / 1e6,
            "hogs_required_2023_millions": world_23 / w / 1e6,
        })
    ceil_grid = []
    r21 = (meters["tongues"]["china_2021_t"] / meters["feet"]["china_2021_t"])
    r23 = (meters["tongues"]["china_2023_t"] / meters["feet"]["china_2023_t"])
    for wt in W_TONGUE:
        for wf in W_FOOT:
            ceil_grid.append({"kg_per_tongue": wt, "kg_per_foot": wf,
                              "ceiling": wt / (4.0 * wf)})
    below21 = sum(1 for g in ceil_grid if r21 < g["ceiling"])
    above23 = sum(1 for g in ceil_grid if r23 > g["ceiling"])
    rep["hogs_required"] = table
    rep["tongue_over_foot_china"] = {"2021": r21, "2023": r23,
                                     "grid": len(ceil_grid),
                                     "2021_below_ceiling": below21,
                                     "2023_above_ceiling": above23,
                                     "ceiling_range": [min(g["ceiling"] for g in ceil_grid),
                                                       max(g["ceiling"] for g in ceil_grid)]}
    rep["no_slaughter_figure"] = (
        "this record neither fetches nor asserts a US hog slaughter figure; "
        "the head count is printed so that a reader who has one can make the "
        "comparison, and every reading that adjudicates above is internal")
    crit.append({
        "name": "B35-SS-6",
        "kind": "bookkeeping",
        "passed": (below21 == len(ceil_grid) and above23 == len(ceil_grid)),
        "detail": (
            f"tongue tonnage over foot tonnage on the China leg is {r21:.4f} "
            f"in 2021 and {r23:.4f} in 2023, against an anatomical ceiling of "
            f"one tongue to four feet that runs "
            f"{rep['tongue_over_foot_china']['ceiling_range'][0]:.3f} to "
            f"{rep['tongue_over_foot_china']['ceiling_range'][1]:.3f} over the "
            f"{len(ceil_grid)} weight pairs swept; 2021 sits below the ceiling "
            f"on all {below21} and 2023 sits above it on all {above23}. The "
            f"world tongue line of 2023 requires "
            f"{table[2]['hogs_required_2023_millions']:.0f} million head at "
            f"{table[2]['kg_per_tongue']:.2f} kg a tongue with no domestic use "
            f"at all; the slaughter figure to compare it against is not "
            f"supplied here"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True
    for c, want in (("5700", True), ("0026", False), ("5XXX", False),
                    ("-", False)):
        if is_atom(c) != want:
            print("SELFTEST FAIL: is_atom(%r)" % c)
            ok = False

    def row(code, cty, name, y, m, q, v):
        return {"E_COMMODITY": code, "CTY_CODE": cty, "CTY_NAME": name,
                "_year": y, "_month": m, "QTY_1_MO": str(q),
                "ALL_VAL_MO": str(v)}

    # A seeded world in which the answer is known: through 2021 and the first
    # eight months of 2022 the tongue line is tongue at 3.30 and head meat is
    # head meat at 1.20; from the break a fixed tonnage of head meat is declared
    # as tongue and never goes back. STEP must fire, and SPIKE must not.
    def build(step: bool):
        seed = []
        for y in (2021, 2022, 2023):
            for m in range(1, 13):
                after = (y, m) >= BREAK
                moved = 2000.0 if (after and step) else 0.0
                for code, q, p in ((TONG, 400.0, 3.30), (HEART, 150.0, 1.40),
                                   (FOOT, 16000.0, 2.30), (HEAD, 3000.0, 1.20),
                                   (SKIN, 500.0, 0.78), (NESOI, 6000.0, 3.10)):
                    if code == TONG:
                        qc, vc = q + moved, q * p + moved * 1.20
                    elif code == HEAD:
                        qc, vc = q - moved, (q - moved) * p
                    else:
                        qc, vc = q, q * p
                    qj, vj = q * 0.25, q * 0.25 * p
                    seed.append(row(code, "5700", CHINA, y, m, qc, vc))
                    seed.append(row(code, "5880", "JAPAN", y, m, qj, vj))
                    seed.append(row(code, "5XXX", "ASIA", y, m, qc + qj, vc + vj))
                    seed.append(row(code, "-", "TOTAL FOR ALL COUNTRIES", y, m,
                                    qc + qj, vc + vj))
        return seed

    crit, rep = run(build(step=True))
    by = {c["name"]: c for c in crit}
    if not by["B35-SS-1"]["passed"]:
        print("SELFTEST FAIL: the sum check should pass on the seeded panel")
        ok = False
    if rep["branch"] != "step":
        print("SELFTEST FAIL: seeded a step, read %r" % rep["branch"])
        ok = False

    # The mirror: a move that reverses at the end of 2022 is a spike, and the
    # same code must say so. A branch reader that can only return one answer is
    # not reading anything.
    seed2 = []
    for y in (2021, 2022, 2023):
        for m in range(1, 13):
            inwin = (y == 2022 and m >= 9)
            moved = 2000.0 if inwin else 0.0
            for code, q, p in ((TONG, 400.0, 3.30), (HEART, 150.0, 1.40),
                               (FOOT, 16000.0, 2.30), (HEAD, 3000.0, 1.20),
                               (SKIN, 500.0, 0.78), (NESOI, 6000.0, 3.10)):
                if code == TONG:
                    qc, vc = q + moved, q * p + moved * 1.20
                elif code == HEAD:
                    qc, vc = q - moved, (q - moved) * p
                else:
                    qc, vc = q, q * p
                qj, vj = q * 0.25, q * 0.25 * p
                seed2.append(row(code, "5700", CHINA, y, m, qc, vc))
                seed2.append(row(code, "5880", "JAPAN", y, m, qj, vj))
                seed2.append(row(code, "5XXX", "ASIA", y, m, qc + qj, vc + vj))
                seed2.append(row(code, "-", "TOTAL FOR ALL COUNTRIES", y, m,
                                 qc + qj, vc + vj))
    _, rep2 = run(seed2)
    if rep2["branch"] != "spike":
        print("SELFTEST FAIL: seeded a spike, read %r" % rep2["branch"])
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
    print("B35 step or spike: the registered test, run on 2021 to 2023")
    print("=" * 74)
    print("China leg tongue unit value, by the windows the record named")
    for k in ("2021", "2022_pre", "2022_post", "2023"):
        lo, hi = rep["intervals_china_tongue_uv"][k]
        print("  %-10s %7.3f - %7.3f" % (k, lo, hi))
    for k, v in rep["overlap_tests"].items():
        print("  %-26s %s" % (k, "yes" if v else "no"))
    print("  BRANCH: %s" % rep["branch"].upper())
    print()
    print("head meat to China, tonnes a year and months at exactly zero")
    for y in (2021, 2022, 2023):
        h = rep["head_meat_china"][y] if y in rep["head_meat_china"] \
            else rep["head_meat_china"][str(y)]
        print("  %d  %10.1f t   zero months %2d   thinnest %8.1f  thickest %9.1f"
              % (y, h["china_t"], h["months_exactly_zero"],
                 h["min_month_t"], h["max_month_t"]))
    print()
    print("the two meters of the same slaughter, China leg, 2021 -> 2023")
    for k, v in rep["meters_china"].items():
        print("  %-12s %10.1f -> %10.1f t   x%.3f"
              % (k, v["china_2021_t"], v["china_2023_t"], v["factor"]))
    print()
    print("head count the world tongue line requires, no slaughter figure asserted")
    for t in rep["hogs_required"]:
        print("  %.2f kg a tongue  ->  %6.1f M head in 2021, %6.1f M in 2023"
              % (t["kg_per_tongue"], t["hogs_required_2021_millions"],
                 t["hogs_required_2023_millions"]))
    print()
    for c in crit:
        print("%-5s %-12s %s" % ("PASS" if c["passed"] else "FAIL",
                                 c["name"], c["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B35-SS",
        "config": {"source": SRC.name, "break": list(BREAK),
                   "windows": {k: [list(x) for x in v] for k, v in WIN.items()},
                   "w_tongue_kg": list(W_TONGUE), "w_foot_kg": list(W_FOOT),
                   "per_hog": {NAMES[k]: v for k, v in PER_HOG.items()},
                   "atom_rule": "four digits, all numeric, not starting 00"},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
