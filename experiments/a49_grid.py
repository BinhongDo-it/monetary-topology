"""A49 grid: three lenders, residence binding or not, five seeds.

Carrier: A47 block 5's cells (levy 0.20, 1.1 dwellings per node, tenancy by unit, cost floor;
private building 0.002, and under binding a public landlord keeping itself with public
building 0.002).

Grid (A49 design, rewritten 2026-09-24): regime {unbound, bound} x lender {none, treasury,
provident (c 0.05, 0.12; r 0, 0.0285), bank (r 0.02)} x down payment {0.1, 0.2} x short stays
{none, 0.1}, plus contributions without lending (c 0.05, 0.12), five seeds.

A bank lending at zero interest (down payment 0.1) is added beside the bank at 0.02, so that
what the rate does can be read apart from who holds the loans.

Knob sweep (11f): arrears k {1, 6} and levy {0.15, 0.25}, both regimes x three lenders and the
zero-interest bank, down payment 0.1, short stays 0.1, five seeds.

Every run's loan book, interest book and fund book are checked (A49-2g, A49-7g). Beside the
net-worth share each run carries the same share with the lender's loan claims left out: net
worth counts a bank's loans to its owners, the financial layer, and a treasury's or a fund's
loans to no node.

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
                if d == 0.1:
                    out.append((reg, "bank", 0.0, 0.0, d, short, True))
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
    import a49_block1
    import a49_block2
    book_ok = a49_block1.book_check(m)[0]
    fund_ok = a49_block2.fund_check(m)[0] if c > 0.0 else True
    nw = m.net_worth()
    prod = m._is_production
    apart = nw - float(m.debt.sum()) * m._prior_owner_weights() if (loan and lender == "bank") else nw
    fs = m.renter_fund_short_history[-50:]
    return {
        "book_ok": bool(book_ok), "fund_ok": bool(fund_ok),
        "prod_share_loans_apart": round(float(apart[prod].sum() / apart.sum()), 4),
        "prod_share_cash": round(float(m.holdings[prod].sum() / m.holdings.sum()), 4),
        "loans_outstanding": round(float(m.debt.sum()), 4),
        "interest_owed": round(float(m.interest_owed.sum()), 4),
        "interest_written_off": round(m.interest_written_off, 4),
        "pf_cash_min": round(m.pf_cash_min, 6), "pf_rent": round(m.pf_rent, 4),
        "pf_units": float(m.pf_units.sum()),
        "fund_short_renters_last50": round(float(np.mean(fs)), 3) if fs else None,
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
    b0 = by_seed(rows, regime="bound", d=0.1, short=0.1, lender="bank", c=0.0, r=0.0)
    for name in ("treasury", "provident"):
        x = by_seed(rows, regime="bound", d=0.1, short=0.1, **L[name])
        if x and bb:
            out[f"M3 prod share, bound, {name} - bank"] = [round(x[s]["prod_share"] - bb[s]["prod_share"], 4) for s in SEEDS]
            out[f"M3 prod share with loans left out, bound, {name} - bank"] = [
                round(x[s]["prod_share_loans_apart"] - bb[s]["prod_share_loans_apart"], 4) for s in SEEDS]
    tr = by_seed(rows, regime="bound", d=0.1, short=0.1, **L["treasury"])
    if b0 and bb:
        out["M3r prod share, bound, bank r 0 - bank r 0.02"] = [round(b0[s]["prod_share"] - bb[s]["prod_share"], 4) for s in SEEDS]
    if b0 and tr:
        out["M3o prod share, bound, treasury - bank r 0"] = [round(tr[s]["prod_share"] - b0[s]["prod_share"], 4) for s in SEEDS]
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
            for lender, c, r in (("treasury", 0.0, 0.0), ("provident", 0.12, 0.0285), ("bank", 0.0, 0.02),
                                 ("bank", 0.0, 0.0)):
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
                                  "prod_share", "top_decile", "interest", "treasury_repaid", "pf_surplus",
                                  "prod_share_loans_apart", "prod_share_cash", "loans_outstanding",
                                  "interest_owed", "interest_written_off", "pf_rent", "pf_units",
                                  "fund_short_renters_last50")}
        name = f"{cl[0]} | {cl[1]} c{cl[2]} r{cl[3]} d{cl[4]} | short {cl[5]}"
        summary[name] = s
        print(f"  {name:52s} {s['renters_last50']} | {s['short_share_of_renters']} | {s['below_down_share_of_renters']} | "
              f"{s['loans']} | {s['foreclosures']} | {s['written_off']} | {s['owners_end']} | {s['price_ratio']} | "
              f"{s['prod_share']} | {s['top_decile']}")

    ok2, ok7, bad = books(rows + krows)
    print(f"\n{'PASS' if ok2 else 'FAIL'} A49-2g [instrument]: loan and interest books close in every run"
          + (f"; {bad[:4]}" if not ok2 else f", {len(rows) + len(krows)} runs"))
    print(f"{'PASS' if ok7 else 'FAIL'} A49-7g [instrument]: fund books close and fund cash is never negative"
          + (f"; {bad[:4]}" if not ok7 else ""))

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

    record = {"stage": "A49-grid",
              "criteria": [
                  {"name": "A49-2g", "kind": "instrument", "passed": ok2,
                   "detail": "loan and interest books close in every grid and knob run"},
                  {"name": "A49-7g", "kind": "instrument", "passed": ok7,
                   "detail": "fund books close and fund cash is never negative in every run with a fund"}],
              "grid_rows": rows, "knob_rows": krows, "cell_summary": summary,
              "comparisons": comp, "knob_signs": knob_signs, "unread": unread,
              "config": {"seeds": list(SEEDS), "cells": [list(c) for c in cells()]}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok2 and ok7) else 1


def books(rows) -> tuple[bool, bool, list]:
    bad = [(x["regime"], x["lender"], x["c"], x["r"], x["d"], x["short"], x["seed"], str(x["knob"]))
           for x in rows if not (x["book_ok"] and x["fund_ok"])]
    return all(x["book_ok"] for x in rows), all(x["fund_ok"] for x in rows), bad


def selftest() -> None:
    rows = [one(("bound", "provident", 0.05, 0.0, 0.1, 0.1, True, 0, {})),
            one(("bound", "bank", 0.0, 0.02, 0.1, 0.1, True, 0, {}))]
    assert books(rows)[:2] == (True, True)
    rows[0]["fund_ok"] = False
    assert books(rows)[1] is False, "A49-7g must fail on one run whose fund book does not close"
    rows[0]["fund_ok"], rows[1]["book_ok"] = True, False
    assert books(rows)[0] is False, "A49-2g must fail on one run whose loan book does not close"
    assert rows[1]["prod_share_loans_apart"] > rows[1]["prod_share"], \
        "leaving the bank's loans out of net worth must raise the production layer's share"
    print("selftest ok: A49-2g and A49-7g each fail on one bad run; the bank's loans are in its "
          "owners' net worth")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(main())
