"""A49 grid: three lenders, residence binding or not, five seeds.

Carrier: A47 block 5's cells (levy 0.20, 1.1 dwellings per node, tenancy by unit, cost floor;
private building 0.002, and under binding a public landlord keeping itself with public
building 0.002).

Grid (A49 design, rewritten 2026-09-24): regime {unbound, bound} x lender {none, treasury,
provident (c 0.05, 0.12; r 0, 0.0285), bank (r 0.02)} x down payment {0.1, 0.2} x short stays
{none, 0.1}, plus contributions without lending (c 0.05, 0.12), five seeds.

Knob sweep (11f): arrears k {1, 6} and levy {0.15, 0.25}, both regimes x three lenders, down
payment 0.1, short stays 0.1, five seeds.

Every run is in the record. Comparisons M1 to M4 are read per seed; one whose sign moves
across seeds or knob values is not read.

Run from the repo root:
    python experiments/a49_grid.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a49_grid.json"
SEEDS = tuple(range(5))
REGIMES = ("unbound", "bound")
SHORTS = (0.0, 0.1)
DOWNS = (0.1, 0.2)


def cells():
    """(regime, lender, c, r, d, short, loan) for every grid cell."""
    out = []
    for reg in REGIMES:
        for short in SHORTS:
            out.append((reg, "none", 0.0, 0.0, 0.1, short, False))
            for c in (0.05, 0.12):
                out.append((reg, "contrib only", c, 0.0, 0.1, short, False))
            for d in DOWNS:
                out.append((reg, "treasury", 0.0, 0.0, d, short, True))
                out.append((reg, "bank", 0.0, 0.02, d, short, True))
                for c in (0.05, 0.12):
                    for r in (0.0, 0.0285):
                        out.append((reg, "provident", c, r, d, short, True))
    return out


def rules_for(reg, lender, c, r, d, short, loan, **knob):
    import a49_block1
    base = a49_block1.BOUND if reg == "bound" else a49_block1.UNBOUND
    kw = dict(short_stay_share=short, short_stay_rate=0.25)
    if loan:
        lend = {"treasury": "public", "bank": "bank", "provident": "provident"}[lender]
        kw.update(commit_loan=True, loan_down=d, loan_lender=lend, loan_rate=r)
        if lender == "treasury":
            kw.update(treasury_backing=True)
    if c > 0.0:
        kw.update(provident_rate=c)
    kw.update(knob)
    return replace(base, **kw)


def one(args):
    reg, lender, c, r, d, short, loan, seed, knob = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    from a47_block1 import reading
    m, secs = a47_block3.run(rules_for(reg, lender, c, r, d, short, loan, **knob), seed=seed)
    mix = m.renter_mix_history[-50:]
    base = reading(m)
    return {
        "regime": reg, "lender": lender, "c": c, "r": r, "d": d, "short": short, "loan": loan,
        "seed": seed, "knob": knob, "seconds": round(secs, 3),
        "renters_last50": round(float(np.mean([x[0] for x in mix])), 2) if mix else None,
        "short_share_of_renters": round(float(np.mean([x[1] / x[0] for x in mix if x[0]])), 4)
        if mix and any(x[0] for x in mix) else None,
        "below_down_share_of_renters": round(float(np.mean([x[2] / x[0] for x in mix if x[0]])), 4)
        if mix and any(x[0] for x in mix) else None,
        "loans": len(m.loan_log), "cleared": len(m.cleared_nodes), "foreclosures": len(m.foreclosures),
        "written_off": round(m.written_off, 4), "interest": round(m.interest_paid, 4),
        "treasury_repaid": round(m.treasury_repaid, 4), "pf_surplus": round(m.pf_surplus(), 4),
        "owners_end": base["owners_end"], "price_ratio": base["price_ratio_end_to_start_low_tier"],
        "prod_share": base["net_worth_production_layer_share"],
        "top_decile": base["net_worth_top_decile_share"],
    }


def key(row):
    return (row["regime"], row["lender"], row["c"], row["r"], row["d"], row["short"], row["loan"])


def by_seed(rows, **k):
    return {x["seed"]: x for x in rows if all(x[a] == b for a, b in k.items())}


def comparisons(rows, lenders=None) -> dict:
    out = {}
    L = {"treasury": dict(lender="treasury", c=0.0, r=0.0),
         "provident": dict(lender="provident", c=0.12, r=0.0285),
         "bank": dict(lender="bank", c=0.0, r=0.02)}
    for name, spec in L.items():
        ub = by_seed(rows, regime="unbound", d=0.1, short=0.1, **spec)
        bd = by_seed(rows, regime="bound", d=0.1, short=0.1, **spec)
        if ub and bd:
            out[f"M1 foreclosures unbound - bound, {name}"] = [ub[s]["foreclosures"] - bd[s]["foreclosures"] for s in SEEDS]
            out[f"M1 written off unbound - bound, {name}"] = [round(ub[s]["written_off"] - bd[s]["written_off"], 4) for s in SEEDS]
            out[f"M1 renters unbound - bound, {name}"] = [round(ub[s]["renters_last50"] - bd[s]["renters_last50"], 2) for s in SEEDS]
            out[f"M2 short share of renters, bound, {name}"] = [bd[s]["short_share_of_renters"] for s in SEEDS]
    bb = by_seed(rows, regime="bound", d=0.1, short=0.1, **L["bank"])
    for name in ("treasury", "provident"):
        x = by_seed(rows, regime="bound", d=0.1, short=0.1, **L[name])
        if x and bb:
            out[f"M3 prod share, bound, {name} - bank"] = [round(x[s]["prod_share"] - bb[s]["prod_share"], 4) for s in SEEDS]
    none = by_seed(rows, regime="bound", lender="none", short=0.1)
    for name in ("treasury", "provident", "bank"):
        x = by_seed(rows, regime="bound", d=0.1, short=0.1, **L[name])
        if x and none:
            out[f"M4 renters, bound, {name} - none"] = [round(x[s]["renters_last50"] - none[s]["renters_last50"], 2) for s in SEEDS]
            out[f"M4 prod share, bound, {name} - none"] = [round(x[s]["prod_share"] - none[s]["prod_share"], 4) for s in SEEDS]
    return out


def signs(v):
    return sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in v if x is not None})


def knob_jobs():
    j = []
    for knob in ({"loan_arrears_k": 1}, {"loan_arrears_k": 6}, {"levy_rate": 0.15}, {"levy_rate": 0.25}):
        for reg in REGIMES:
            for lender, c, r in (("treasury", 0.0, 0.0), ("provident", 0.12, 0.0285), ("bank", 0.0, 0.02)):
                j += [(reg, lender, c, r, 0.1, 0.1, True, s, knob) for s in SEEDS]
            j += [(reg, "none", 0.0, 0.0, 0.1, 0.1, False, s, knob) for s in SEEDS]
    return j


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    jobs = [(*cl, s, {}) for cl in cells() for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    t1 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        krows = list(ex.map(one, knob_jobs(), chunksize=4))
    t2 = time.perf_counter()
    print(f"grid {len(rows)} runs {t1 - t0:.1f} s; knobs {len(krows)} runs {t2 - t1:.1f} s; {workers} workers")

    print("\ncells, mean over 5 seeds: renters | short share | below-down share | loans | foreclosures | "
          "written off | owners | price | prod share | top decile")
    summary = {}
    for cl in cells():
        rs = [x for x in rows if key(x) == cl]
        def mean(k):
            v = [x[k] for x in rs if x[k] is not None]
            return round(float(np.mean(v)), 4) if v else None
        s = {k: mean(k) for k in ("renters_last50", "short_share_of_renters", "below_down_share_of_renters",
                                  "loans", "foreclosures", "written_off", "owners_end", "price_ratio",
                                  "prod_share", "top_decile", "interest", "treasury_repaid", "pf_surplus")}
        name = f"{cl[0]} | {cl[1]} c{cl[2]} r{cl[3]} d{cl[4]} | short {cl[5]}"
        summary[name] = s
        print(f"  {name:52s} {s['renters_last50']} | {s['short_share_of_renters']} | {s['below_down_share_of_renters']} | "
              f"{s['loans']} | {s['foreclosures']} | {s['written_off']} | {s['owners_end']} | {s['price_ratio']} | "
              f"{s['prod_share']} | {s['top_decile']}")

    comp = comparisons(rows)
    print("\ncomparisons, per seed:")
    for k, v in comp.items():
        print(f"  {k}: {v}")

    print("\nknob sweep:")
    knob_signs, unread = {}, []
    for knob in ({"loan_arrears_k": 1}, {"loan_arrears_k": 6}, {"levy_rate": 0.15}, {"levy_rate": 0.25}):
        sub = [x for x in krows if x["knob"] == knob]
        for name, vals in comparisons(sub).items():
            if name.startswith("M2"):
                continue
            knob_signs.setdefault(name, {})[json.dumps(knob)] = signs(vals)
    for name, byk in knob_signs.items():
        allsigns = set(signs(comp.get(name, [])))
        for sg in byk.values():
            allsigns |= set(sg)
        flag = "read" if len(allsigns) == 1 else "NOT READ (sign moves)"
        if len(allsigns) != 1:
            unread.append(name)
        print(f"  {name}: base {signs(comp.get(name, []))}; " +
              ", ".join(f"{k} {s}" for k, s in byk.items()) + f" -> {flag}")

    record = {"stage": "A49-grid", "grid_rows": rows, "knob_rows": krows, "cell_summary": summary,
              "comparisons": comp, "knob_signs": knob_signs, "unread": unread,
              "config": {"seeds": list(SEEDS), "cells": [list(c) for c in cells()]}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
