"""B34 step 3: the difference in differences for arm five, and the verdict.

Reads results/b34_ashe_cells.json, written by step 2. Applies B34_design
sections 8.3, 8.4 and 9 exactly as they were pinned before any difference was
taken:

  scale       logs, because the two groups have different bases and the
              counterfactual is common proportional growth, and because the
              published CV is natively the standard error of the log
  se          sqrt of the sum of four squared CVs, CVs taken as fractions
  floor       1.645, the same constant as gates two and three
  undecided   1.4 < |t| <= 1.9
  verdict     treatment percentiles 10 and 20 must clear the floor upward,
              placebo percentiles 60 70 80 must not, and the control group
              must not move against 30-39 at 10 and 20

Every registered cell is printed whether or not it helps.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

Z = 1.645
UND_LO, UND_HI = 1.4, 1.9

TREAT = "22-29"
CONTROL = "18-21"
FULLDOSE = "30-39"
CARRY = ["10", "20"]
PLACEBO = ["60", "70", "80"]


def verdict(t):
    if UND_LO < abs(t) <= UND_HI:
        return "undecided"
    return "clears" if t > Z else ("clears-negative" if t < -Z else "flat")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default=None)
    ap.add_argument("--y0", default="2015")
    ap.add_argument("--y1", default="2017")
    ap.add_argument("--sheet", default="All")
    ap.add_argument("--mode", choices=["main", "pretrend"], default=None,
                    help="which criterion to apply; inferred from the window if "
                         "omitted. main is design 8.4, pretrend is design 10.1 "
                         "and its carrying percentiles must NOT clear upward")
    args = ap.parse_args()

    mode = args.mode or ("main" if (args.y0, args.y1) == ("2015", "2017")
                         else "pretrend")
    root = Path(__file__).resolve().parent.parent
    cells = Path(args.cells) if args.cells else root / "results" / "b34_ashe_cells.json"
    rows = json.loads(cells.read_text(encoding="utf-8"))
    rows = [r for r in rows if r["sheet"] == args.sheet]

    val = {(r["year"], r["agegroup"], str(r["stat"])): r["value"]
           for r in rows if r["kind"] == "value"}
    cv = {(r["year"], r["agegroup"], str(r["stat"])): r["value"]
          for r in rows if r["kind"] == "cv"}

    missing = [s for s in CARRY + PLACEBO
               if (args.y0, TREAT, s) not in val or (args.y1, TREAT, s) not in val]
    if missing:
        raise SystemExit("registered statistics absent from the record: %s" % missing)

    def growth(g, st):
        a, b = val[(args.y0, g, st)], val[(args.y1, g, st)]
        return math.log(b / a), a, b

    def did(g_t, g_c, st):
        gt, a_t, b_t = growth(g_t, st)
        gc, a_c, b_c = growth(g_c, st)
        cvs = [cv[(args.y0, g_t, st)], cv[(args.y1, g_t, st)],
               cv[(args.y0, g_c, st)], cv[(args.y1, g_c, st)]]
        se = math.sqrt(sum((c / 100.0) ** 2 for c in cvs))
        d = gt - gc
        lvl = (b_t - a_t) - (b_c - a_c)
        return d, se, d / se if se else float("nan"), lvl, (a_t, b_t, a_c, b_c)

    out = {"design": "B34 sections 8.3 8.4 9", "y0": args.y0, "y1": args.y1,
           "sheet": args.sheet, "z": Z, "contrasts": {}}

    for name, gt, gc in (("main", TREAT, CONTROL),
                         ("control_check", CONTROL, FULLDOSE),
                         ("fulldose", FULLDOSE, CONTROL)):
        print("=" * 78)
        print("%s: %s against %s, %s to %s, sheet %s"
              % (name, gt, gc, args.y0, args.y1, args.sheet))
        print("=" * 78)
        print("  %-8s %8s %8s %8s %8s | %9s %8s %7s  %-16s %9s"
              % ("stat", "t.y0", "t.y1", "c.y0", "c.y1", "logDiD", "se", "t",
                 "verdict", "levelDiD"))
        block = {}
        for st in ["10", "20", "25", "30", "40", "Median", "60", "70", "75", "80", "90"]:
            if (args.y0, gt, st) not in val or (args.y0, gc, st) not in val:
                continue
            d, se, t, lvl, (a_t, b_t, a_c, b_c) = did(gt, gc, st)
            tag = verdict(t)
            mark = "*" if st in CARRY else ("p" if st in PLACEBO else " ")
            print("%s %-8s %8.2f %8.2f %8.2f %8.2f | %+9.4f %8.4f %7.2f  %-16s %+9.4f"
                  % (mark, st, a_t, b_t, a_c, b_c, d, se, t, tag, lvl))
            block[st] = {"logDiD": d, "se": se, "t": t, "verdict": tag,
                         "levelDiD": lvl,
                         "cells": {"treat_y0": a_t, "treat_y1": b_t,
                                   "ctrl_y0": a_c, "ctrl_y1": b_c}}
        out["contrasts"][name] = block
        print()

    m = out["contrasts"]["main"]
    c = out["contrasts"]["control_check"]
    cleared = [s for s in CARRY if m[s]["verdict"] == "clears"]
    und = [s for s in CARRY + PLACEBO if m[s]["verdict"] == "undecided"] + \
          [s for s in CARRY if c[s]["verdict"] == "undecided"]

    print("=" * 78)
    if mode == "main":
        print("design section 8.4, three conditions, all printed either way")
        print("=" * 78)
        cond1 = all(m[s]["verdict"] == "clears" for s in CARRY)
        cond2 = all(m[s]["verdict"] != "clears" for s in PLACEBO)
        cond3 = all(c[s]["verdict"] != "clears" for s in CARRY)
        print("  1 carrying %s clear upward            : %s" % (CARRY, cond1))
        print("  2 placebo %s do not clear         : %s" % (PLACEBO, cond2))
        print("  3 control does not clear against %s  : %s" % (FULLDOSE, cond3))
        conds = {"c1": cond1, "c2": cond2, "c3": cond3}
        if und:
            res = "UNDECIDED"
            print("\n  inside the undecided band 1.4 < |t| <= 1.9: %s" % und)
        elif cond1 and cond2 and cond3:
            res = "PASS"
        else:
            res = "FAIL"
        label = "ARM FIVE, main window"
    else:
        print("design section 10.1, the pre trend placebo")
        print("the criterion is REVERSED: the carrying percentiles must NOT")
        print("clear upward, because both years precede the announcement")
        print("=" * 78)
        cond1 = not cleared
        print("  carrying %s do not clear upward       : %s" % (CARRY, cond1))
        print("    cleared upward: %s" % (cleared if cleared else "none"))
        conds = {"c1_no_upward_clear": cond1, "cleared": cleared}
        if [x for x in und if x in CARRY]:
            res = "UNDECIDED"
            print("\n  a carrying percentile is inside the undecided band: %s"
                  % [x for x in und if x in CARRY])
        elif cond1:
            res = "PASS"
        else:
            res = "FAIL"
            print("\n  design 10.1: the main window reading is DOWNGRADED to")
            print("  undecided, because the divergence predates the policy.")
        label = "ARM FIVE, pre trend"

    print("\n  %s: %s" % (label, res))
    out["mode"] = mode
    out["result"] = res
    out["conditions"] = conds
    out["undecided_cells"] = und

    p = root / "results" / ("b34_arm5_did_%s_%s_%s.json"
                            % (mode, args.y0, args.y1))
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True),
                 encoding="utf-8")
    print("\nwritten: %s" % p)


if __name__ == "__main__":
    main()
