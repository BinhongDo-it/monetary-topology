"""A47 block 5: the grid, on the levy carrier, five seeds.

Carrier (A47 results §R3, §R4): A3's registered network with A9's transfer levy at 0.20,
1.1 units per node with residual stock kept by its prior owner (A3b), tenancy by unit and
the cost floor. Every arm below is that carrier plus the named rules.

Grid: regime x public building x private building x rent cap, five seeds.

  regime            unbound | bound, public, self-maintaining | bound, listed 0.271 | 0.421
  public building   0 | 0.002 | 0.005   (share of opening supply per round; 0 means none)
  private building  0 | 0.002 | 0.005
  rent cap          none | wage cap from round 150

Readings, every run printed into the record (印全):
  production-layer and top-decile shares of net worth, low-tier price end over start,
  sales, owners at the end, mean unhoused, private and public rent, the state's top-up over
  the levy, public units built, unfunded maintenance, regulated rent paid over uncapped at
  the end, and B129's square (log of new rent per unit over regulated, 50 rounds after the
  cap against 50 before) with the sale price at rounds 149 and 199.

Comparisons read off the grid (own readings, no thresholds; signs across seeds are printed):
  K1  bound self-maintaining public minus unbound: production-layer net worth share
  K2  bound public minus bound listed 0.271: the same
  K3  unbound with public building minus without: the same
  K4  under the wage cap, regulated rent paid over uncapped
  K5  B129: under the wage cap with private building, the square, and the sale price at 199
      over the uncapped run's, same seed and cell

Knob sweep (11f): cap_wage_share {0.25, 0.30, 0.35}, maintenance_rate {0.005, 0.0093,
0.015}, levy_rate {0.15, 0.20, 0.25}, one at a time, on the cells K1 to K5 read. A
comparison whose sign moves on any knob value in any seed is not read.

Run from the repo root:
    python experiments/a47_block5.py
"""
from __future__ import annotations

import itertools
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
OUT = ROOT / "results" / "a47_block5.json"
SEEDS = tuple(range(5))
CAP_START = 150
SELF = dict(public_rent_cost=True, public_maintenance=True, state_topup=True, pool_pass_rate=0.0)

REGIMES = {
    "unbound": dict(),
    "bound public": dict(residence_bound=True, landlord="public"),
    "bound listed 0.271": dict(residence_bound=True, landlord="listed", dividend_exit=0.271),
    "bound listed 0.421": dict(residence_bound=True, landlord="listed", dividend_exit=0.421),
}
PUBLIC = (0.0, 0.002, 0.005)
PRIVATE = (0.0, 0.002, 0.005)
CAPS = (None, "wage")
KNOBS = {"cap_wage_share": (0.25, 0.30, 0.35), "maintenance_rate": (0.005, 0.0093, 0.015),
         "levy_rate": (0.15, 0.20, 0.25)}


def rules_for(regime: str, public: float, private: float, cap, **knob):
    from monetary_topology.housing_rules import HousingRules
    kw = dict(levy_rate=0.20, tenant_tier=True, cost_floor=True, new_supply_rate=private)
    kw.update(REGIMES[regime])
    listed = kw.get("landlord") == "listed"
    if public > 0.0 and not listed:
        kw.update(SELF, public_build_rate=public)
    elif kw.get("landlord") == "public":
        kw.update(SELF)
    if cap:
        kw.update(rent_cap=cap, cap_start=CAP_START)
    kw.update(knob)
    return HousingRules(**kw)


def cell_valid(regime: str, public: float) -> bool:
    # A listed landlord cannot run public housing (refused by the rules).
    return not (regime.startswith("bound listed") and public > 0.0)


def one(args):
    regime, public, private, cap, seed, knob = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    from a47_block1 import reading
    rules = rules_for(regime, public, private, cap, **knob)
    m, secs = a47_block3.run(rules, seed=seed)
    ph = np.asarray(m.price_history)
    r = reading(m)
    unh = np.asarray(m.unhoused_history) if m.unhoused_history else np.zeros(1)
    capped = [row for row in m.rent_class_history if row[1]]
    return {
        "regime": regime, "public": public, "private": private, "cap": cap, "seed": seed,
        "knob": knob, "seconds": round(secs, 3),
        "prod_share": r["net_worth_production_layer_share"],
        "top_decile": r["net_worth_top_decile_share"],
        "price_ratio": r["price_ratio_end_to_start_low_tier"],
        "sales": r["sales_total"], "owners_end": r["owners_end"],
        "unhoused_mean": round(float(unh.mean()), 3),
        "rent_private": round(float(m.rent_collected - m.landlord_rent), 3),
        "rent_public": round(float(m.landlord_rent), 3),
        "topup_over_levy": round(m.topup_total / m.levied, 5) if m.levied else None,
        "public_built": float(m.public_built.sum()), "private_built": float(m.built.sum()),
        "maintenance_unfunded": round(m.maintenance_unfunded, 4),
        "reg_over_uncapped_end": round(capped[-1][2] / capped[-1][6], 4)
        if capped and capped[-1][6] > 0 else None,
        "sale_r149": round(float(ph[149, 0]), 6), "sale_r199": round(float(ph[199, 0]), 6),
        **{k: v for k, v in a47_block3.square(m).items()},
    }


def grid_jobs():
    jobs = []
    for regime, public, private, cap in itertools.product(REGIMES, PUBLIC, PRIVATE, CAPS):
        if cell_valid(regime, public):
            jobs += [(regime, public, private, cap, s, {}) for s in SEEDS]
    return jobs


def knob_jobs():
    """K1-K5's cells, every knob value one at a time."""
    cells = [("unbound", 0.0, 0.002, None), ("unbound", 0.002, 0.002, None),
             ("unbound", 0.0, 0.002, "wage"), ("bound public", 0.002, 0.002, None),
             ("bound listed 0.271", 0.0, 0.002, None), ("bound public", 0.002, 0.002, "wage")]
    jobs = []
    for knob, values in KNOBS.items():
        for v in values:
            for c in cells:
                jobs += [(*c, s, {knob: v}) for s in SEEDS]
    return jobs


def pick(rows, **k):
    return {r["seed"]: r for r in rows
            if all(r[key] == val for key, val in k.items())}


def comparisons(rows) -> dict:
    """K1-K5 per seed, from rows with the same knob."""
    out = {}
    base = dict(private=0.002)
    ub = pick(rows, regime="unbound", public=0.0, cap=None, **base)
    ubp = pick(rows, regime="unbound", public=0.002, cap=None, **base)
    bp = pick(rows, regime="bound public", public=0.002, cap=None, **base)
    bl = pick(rows, regime="bound listed 0.271", public=0.0, cap=None, **base)
    ucap = pick(rows, regime="unbound", public=0.0, cap="wage", **base)
    if ub and bp:
        out["K1 bound public - unbound, prod share"] = [round(bp[s]["prod_share"] - ub[s]["prod_share"], 4) for s in SEEDS]
    if bp and bl:
        out["K2 bound public - bound listed, prod share"] = [round(bp[s]["prod_share"] - bl[s]["prod_share"], 4) for s in SEEDS]
    if ub and ubp:
        out["K3 unbound public building - none, prod share"] = [round(ubp[s]["prod_share"] - ub[s]["prod_share"], 4) for s in SEEDS]
    if ucap:
        out["K4 regulated paid / uncapped (unbound, wage cap)"] = [ucap[s]["reg_over_uncapped_end"] for s in SEEDS]
        out["K5 square (unbound, wage cap)"] = [ucap[s].get("square") for s in SEEDS]
        if ub:
            out["K5 sale price r199, capped / uncapped - 1"] = [
                round(ucap[s]["sale_r199"] / ub[s]["sale_r199"] - 1, 5) for s in SEEDS]
    return out


def signs(vals, ref=0.0):
    v = [x for x in vals if x is not None]
    return {"+" if x > ref else ("-" if x < ref else "0") for x in v}


def main() -> int:
    t0 = time.perf_counter()
    workers = max(1, (os.cpu_count() or 2) - 1)
    jobs = grid_jobs()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    t1 = time.perf_counter()
    kjobs = knob_jobs()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        krows = list(ex.map(one, kjobs, chunksize=4))
    t2 = time.perf_counter()
    print(f"grid: {len(jobs)} runs in {t1 - t0:.1f} s; knobs: {len(kjobs)} runs in {t2 - t1:.1f} s; "
          f"{workers} workers; mean seconds per run {np.mean([r['seconds'] for r in rows]):.3f}")

    # cell summary: mean and range over seeds
    print("\ncell means over 5 seeds (min-max): prod share | top decile | price ratio | owners | unhoused | public built | topup/levy")
    summary = {}
    for regime, public, private, cap in itertools.product(REGIMES, PUBLIC, PRIVATE, CAPS):
        if not cell_valid(regime, public):
            continue
        rs = [r for r in rows if (r["regime"], r["public"], r["private"], r["cap"]) == (regime, public, private, cap)]
        def f(k):
            v = [r[k] for r in rs if r[k] is not None]
            return (round(float(np.mean(v)), 4), round(min(v), 4), round(max(v), 4)) if v else None
        key = f"{regime} | pub {public} | priv {private} | cap {cap}"
        summary[key] = {k: f(k) for k in ("prod_share", "top_decile", "price_ratio", "owners_end",
                                          "unhoused_mean", "public_built", "topup_over_levy",
                                          "reg_over_uncapped_end")}
        s = summary[key]
        print(f"  {key:52s} {s['prod_share']} | {s['top_decile']} | {s['price_ratio']} | "
              f"{s['owners_end'][0]} | {s['unhoused_mean'][0]} | {s['public_built'][0]} | "
              f"{s['topup_over_levy'][0] if s['topup_over_levy'] else None}")

    comp = comparisons(rows)
    print("\ncomparisons, per seed:")
    for k, v in comp.items():
        print(f"  {k}: {v}")

    # knob sweep: sign of each comparison under every knob value
    knob_signs, unread = {}, []
    for knob, values in KNOBS.items():
        for v in values:
            sub = [r for r in krows if r["knob"] == {knob: v}]
            c = comparisons(sub)
            for name, vals in c.items():
                ref = 1.0 if name.startswith("K4") else 0.0
                knob_signs.setdefault(name, {})[f"{knob}={v}"] = sorted(signs(vals, ref))
    base_signs = {name: sorted(signs(vals, 1.0 if name.startswith("K4") else 0.0)) for name, vals in comp.items()}
    print("\nknob sweep, signs of each comparison (K4 read against 1):")
    for name, by in knob_signs.items():
        allsigns = set(base_signs.get(name, []))
        for s in by.values():
            allsigns |= set(s)
        flag = "read" if len(allsigns) == 1 else "NOT READ (sign moves)"
        if len(allsigns) != 1:
            unread.append(name)
        print(f"  {name}: base {base_signs.get(name)}; " +
              ", ".join(f"{k} {s}" for k, s in by.items()) + f"  -> {flag}")

    record = {"stage": "A47-block5",
              "carrier": "A3 network + levy 0.20 + 1.1 units/node, residual owner + tenancy + cost floor",
              "grid_rows": rows, "knob_rows": krows, "cell_summary": summary,
              "comparisons": comp, "knob_signs": knob_signs, "unread": unread,
              "config": {"seeds": list(SEEDS), "cap_start": CAP_START, "public": PUBLIC,
                         "private": PRIVATE, "regimes": REGIMES, "knobs": KNOBS}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
