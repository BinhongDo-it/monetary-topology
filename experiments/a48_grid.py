"""A48 grid: how much the core locks up, what that delays, and who ends up holding the core.

Carrier: A47 block 5's bound cells, public building and private building at 0.002 where the
landlord is public, private building 0.002 where it is listed (a listed landlord runs no
public housing). The top tier is the core.

Grid: landlord {public, listed 0.271} x R0 {1.00, 1.16, 1.45} x g {0, 0.005, 0.01, 0.02}
      x tau_o {0.01, 0.02, 0.03}, plus the same cells with no optional moves (lock off), five
      seeds. R0 = 1.16 and 1.45 are the 2019 Berlin Mietspiegel's median and upper ratio of
      good-location to simple-location rents (A48 design). g and tau_o are knobs.

Readings, every run in the record:
  lock rate (locks over optional draws in the core, pooled over seeds for the tables)
  households' share of the core at rounds 50, 150 and 299, and the first round it is zero
  core holdings that ended: their mean length; core holdings still open at the last round:
  how many, and how long they have run so far; who buys the core (production-layer share)
  who rents the core (production-layer share of its tenants, mean over rounds)
  production-layer and top-decile shares of net worth; the core price at the end

Comparisons (own readings; signs across seeds printed):
  L1  lock rate by g, for each R0 and tau_o (pooled)
  L2  lock on minus off, same cell and seed: the round households' core share first hits
      zero (the delay), and the production-layer share of net worth. Printed for the cells
      at tau_o 0.02, R0 1.16 and 1.45, g 0.005 and 0.01, and for the production-layer share
      over every cell of the grid (360 pairs), by g and by whether households still hold a
      core unit at the last round in either run of the pair
  L3  public minus listed landlord, same cell and seed: households' core share at 299, and
      the production-layer share of net worth

Knob sweep (11f): levy {0.15, 0.25} and maintenance {0.005, 0.015} on R0 1.16, g 0.005,
tau_o 0.02, both landlords, lock on and off. A comparison whose sign moves is not read.

Run from the repo root:
    python experiments/a48_grid.py
"""
from __future__ import annotations

import itertools
import json
import math
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
OUT = ROOT / "results" / "a48_grid.json"
SEEDS = tuple(range(5))
LANDLORDS = ("public", "listed 0.271")
R0S = (1.0, 1.16, 1.45)
GS = (0.0, 0.005, 0.01, 0.02)
TAUS = (0.01, 0.02, 0.03)
KNOBS = {"levy_rate": (0.15, 0.25), "maintenance_rate": (0.005, 0.015)}


def rules_for(landlord: str, R0: float, g: float, tau_o: float, **knob):
    import a47_block5
    base = (a47_block5.rules_for("bound public", 0.002, 0.002, None) if landlord == "public"
            else a47_block5.rules_for("bound listed 0.271", 0.0, 0.002, None))
    return replace(base, core_premium=True, core_R0=R0, core_g=g, optional_move_rate=tau_o, **knob)


def one(args):
    landlord, R0, g, tau_o, seed, knob = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    import a48_block1
    from a47_block1 import reading
    m, secs = a47_block3.run(rules_for(landlord, R0, g, tau_o, **knob), seed=seed)
    ch = np.asarray(m.core_household_history)
    zero = np.flatnonzero(ch <= 0.0)
    tenure = [tr[3] - tr[2] for tr in m.trades if tr[1] == m._core_q]
    still = sorted(a48_block1.open_spells(m))
    buys = m.core_buys
    ten = [(n, p) for n, p in m.core_tenant_history if n > 0]
    r = reading(m)
    return {
        "landlord": landlord, "R0": R0, "g": g, "tau_o": tau_o, "seed": seed, "knob": knob,
        "seconds": round(secs, 3),
        "premium_ok": bool(a48_block1.premium_check(m)[0]), "lock_ok": bool(a48_block1.lock_check(m)[0]),
        "opening_core_buyers": len(m.opening_core_buys),
        "locks": len(m.lock_events), "draws": m.optional_core_draws,
        "core_hh_r50": round(float(ch[50]), 4), "core_hh_r150": round(float(ch[150]), 4),
        "core_hh_r299": round(float(ch[-1]), 4),
        "core_hh_first_zero": int(zero[0]) if zero.size else None,
        "core_tenure_completed_mean": round(float(np.mean(tenure)), 3) if tenure else None,
        "core_spells_completed": len(tenure),
        "core_spells_open": len(still),
        "core_spells_open_observed_mean": round(float(np.mean(still)), 3) if still else None,
        "core_spells_open_observed": still,
        "opening_core_buyers_short": a48_block1.opening_check(m)[1]["opening_core_buyers_short"],
        "core_buys": len(buys),
        "core_buyers_production": round(sum(b[2] for b in buys) / len(buys), 4) if buys else None,
        "core_tenants_production": round(float(np.mean([p / n for n, p in ten])), 4) if ten else None,
        "prod_share": r["net_worth_production_layer_share"],
        "top_decile": r["net_worth_top_decile_share"],
        "core_price_end": round(float(m.price_history[-1][m._core_q]), 4),
    }


def jobs_grid():
    j = []
    for ll, R0, g in itertools.product(LANDLORDS, R0S, GS):
        for tau in (0.0,) + TAUS:
            j += [(ll, R0, g, tau, s, {}) for s in SEEDS]
    return j


def jobs_knobs():
    j = []
    for knob, vals in KNOBS.items():
        for v in vals:
            for ll in LANDLORDS:
                for tau in (0.0, 0.02):
                    j += [(ll, 1.16, 0.005, tau, s, {knob: v}) for s in SEEDS]
    return j


def by(rows, **k):
    return {r["seed"]: r for r in rows if all(r[a] == b for a, b in k.items())}


def first_zero(r):
    return r["core_hh_first_zero"] if r["core_hh_first_zero"] is not None else 300


def comparisons(rows, cells=None):
    out = {}
    cells = cells or [(ll, 1.16, 0.005, 0.02) for ll in LANDLORDS]
    for ll, R0, g, tau in cells:
        on = by(rows, landlord=ll, R0=R0, g=g, tau_o=tau)
        off = by(rows, landlord=ll, R0=R0, g=g, tau_o=0.0)
        if on and off:
            out[f"L2 delay, {ll} R0 {R0} g {g} tau_o {tau}"] = [first_zero(on[s]) - first_zero(off[s]) for s in SEEDS]
            out[f"L2 prod share, {ll} R0 {R0} g {g} tau_o {tau}"] = [round(on[s]["prod_share"] - off[s]["prod_share"], 5) for s in SEEDS]
    pub = by(rows, landlord="public", R0=1.16, g=0.005, tau_o=0.02)
    lst = by(rows, landlord="listed 0.271", R0=1.16, g=0.005, tau_o=0.02)
    if pub and lst:
        out["L3 core hh share r299, public - listed"] = [round(pub[s]["core_hh_r299"] - lst[s]["core_hh_r299"], 4) for s in SEEDS]
        out["L3 prod share, public - listed"] = [round(pub[s]["prod_share"] - lst[s]["prod_share"], 4) for s in SEEDS]
    return out


def full_grid_l2(rows) -> dict:
    """Lock on minus off in the production-layer share, every cell and seed: 360 pairs."""
    off = {(r["landlord"], r["R0"], r["g"], r["seed"]): r for r in rows if r["tau_o"] == 0.0}
    pairs = []
    for r in rows:
        if r["tau_o"] == 0.0:
            continue
        o = off[(r["landlord"], r["R0"], r["g"], r["seed"])]
        pairs.append({"landlord": r["landlord"], "R0": r["R0"], "g": r["g"], "tau_o": r["tau_o"], "seed": r["seed"],
                      "diff": round(r["prod_share"] - o["prod_share"], 5),
                      "core_held_at_end": bool(r["core_spells_open"] or o["core_spells_open"])})
    def block(ps):
        v = [x["diff"] for x in ps]
        return {"pairs": len(v), "min": min(v) if v else None, "max": max(v) if v else None,
                "over_0.005": sum(abs(x) > 0.005 for x in v)}
    out = {"pairs": len(pairs), "by_g": {str(g): block([x for x in pairs if x["g"] == g]) for g in GS},
           "core_gone_in_both": {str(g): block([x for x in pairs if x["g"] == g and not x["core_held_at_end"]]) for g in GS},
           "core_held_in_either": {str(g): block([x for x in pairs if x["g"] == g and x["core_held_at_end"]]) for g in GS},
           "largest": sorted(pairs, key=lambda x: -abs(x["diff"]))[:5]}
    return out


def sign_set(v):
    return sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in v if x is not None})


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs_grid(), chunksize=4))
    t1 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        krows = list(ex.map(one, jobs_knobs(), chunksize=4))
    t2 = time.perf_counter()
    print(f"grid {len(rows)} runs {t1 - t0:.1f} s; knobs {len(krows)} runs {t2 - t1:.1f} s; {workers} workers")
    ok2 = all(r["premium_ok"] for r in rows + krows)
    ok3 = all(r["lock_ok"] for r in rows + krows)
    print(f"{'PASS' if ok2 else 'FAIL'} A48-2 [instrument]: premium path, opening quote and opening payments, "
          f"{len(rows) + len(krows)} runs")
    print(f"{'PASS' if ok3 else 'FAIL'} A48-3 [instrument]: lock classification and the four legs, "
          f"{len(rows) + len(krows)} runs")

    print("\nL1 lock rate, pooled over 5 seeds (locks / optional core draws):")
    l1 = {}
    for ll in LANDLORDS:
        for R0, tau in itertools.product(R0S, TAUS):
            cells = []
            for g in GS:
                rs = [r for r in rows if (r["landlord"], r["R0"], r["g"], r["tau_o"]) == (ll, R0, g, tau)]
                L, D = sum(r["locks"] for r in rs), sum(r["draws"] for r in rs)
                cells.append((g, L, D, round(L / D, 3) if D else None))
            l1[f"{ll} R0 {R0} tau_o {tau}"] = cells
            print(f"  {ll:12s} R0 {R0:4.2f} tau_o {tau:4.2f}: " +
                  "  ".join(f"g {g}: {rate} ({L}/{D})" for g, L, D, rate in cells))

    print("\ncells (mean over seeds): landlord R0 g tau_o | core hh r50 r150 r299 | first zero | "
          "completed tenure | open spells | buyers prod | tenants prod | prod share | top decile")
    summary = {}
    for ll, R0, g in itertools.product(LANDLORDS, R0S, GS):
        for tau in (0.0,) + TAUS:
            rs = [r for r in rows if (r["landlord"], r["R0"], r["g"], r["tau_o"]) == (ll, R0, g, tau)]
            def mean(k):
                v = [r[k] for r in rs if r[k] is not None]
                return round(float(np.mean(v)), 4) if v else None
            fz = [first_zero(r) for r in rs]
            s = {k: mean(k) for k in ("core_hh_r50", "core_hh_r150", "core_hh_r299", "core_tenure_completed_mean",
                                      "core_spells_open_observed_mean",
                                      "core_buyers_production", "core_tenants_production", "prod_share",
                                      "top_decile")}
            s["first_zero_mean"] = round(float(np.mean(fz)), 1)
            s["core_spells_open"] = int(sum(r["core_spells_open"] for r in rs))
            s["opening_core_buyers_mean"] = mean("opening_core_buyers")
            key = f"{ll} | R0 {R0} | g {g} | tau_o {tau}"
            summary[key] = s
            if R0 in (1.0, 1.16) and g in (0.0, 0.005) or tau == 0.02:
                print(f"  {key:44s} {s['core_hh_r50']} {s['core_hh_r150']} {s['core_hh_r299']} | "
                      f"{s['first_zero_mean']} | {s['core_tenure_completed_mean']} | {s['core_spells_open']} | "
                      f"{s['core_buyers_production']} | "
                      f"{s['core_tenants_production']} | {s['prod_share']} | {s['top_decile']}")

    comp = comparisons(rows, cells=[(ll, R0, g, 0.02) for ll in LANDLORDS for R0 in (1.16, 1.45)
                                    for g in (0.005, 0.01)])
    print("\ncomparisons, per seed:")
    for k, v in comp.items():
        print(f"  {k}: {v}")

    full = full_grid_l2(rows)
    held = [r for r in rows if r["core_spells_open"]]
    print(f"\nL2 production-layer share over the whole grid: {full['pairs']} pairs; "
          f"{len(held)} of {len(rows)} runs end with a household still holding a core unit")
    for name in ("by_g", "core_gone_in_both", "core_held_in_either"):
        print(f"  {name}: " + "  ".join(f"g {g}: {b['pairs']} pairs [{b['min']}, {b['max']}], {b['over_0.005']} beyond 0.005"
                                          for g, b in full[name].items()))
    print("  largest: " + "; ".join(f"{x['landlord']} R0 {x['R0']} g {x['g']} tau_o {x['tau_o']} seed {x['seed']}: {x['diff']}"
                                    for x in full["largest"]))
    print("\nopen core spells at the last round (count over 5 seeds, mean rounds observed):")
    for key, s in summary.items():
        if s["core_spells_open"]:
            print(f"  {key}: {s['core_spells_open']} open, observed {s['core_spells_open_observed_mean']}; "
                  f"completed mean {s['core_tenure_completed_mean']}")

    print("\nknob sweep (R0 1.16, g 0.005, tau_o 0.02):")
    knob_signs, unread = {}, []
    base = comparisons(rows)
    for knob, vals in KNOBS.items():
        for v in vals:
            sub = [r for r in krows if r["knob"] == {knob: v}]
            for name, vs in comparisons(sub).items():
                knob_signs.setdefault(name, {})[f"{knob}={v}"] = sign_set(vs)
    for name, bykn in knob_signs.items():
        allsigns = set(sign_set(base.get(name, [])))
        for s in bykn.values():
            allsigns |= set(s)
        flag = "read" if len(allsigns) == 1 else "NOT READ (sign moves)"
        if len(allsigns) != 1:
            unread.append(name)
        print(f"  {name}: base {sign_set(base.get(name, []))}; " +
              ", ".join(f"{k} {s}" for k, s in bykn.items()) + f" -> {flag}")

    record = {"stage": "A48-grid",
              "criteria": [
                  {"name": "A48-2", "kind": "instrument", "passed": ok2,
                   "detail": f"premium path, opening quote and opening payments in {len(rows) + len(krows)} runs"},
                  {"name": "A48-3", "kind": "instrument", "passed": ok3,
                   "detail": f"lock classification and the four legs in {len(rows) + len(krows)} runs"}],
              "grid_rows": rows, "knob_rows": krows, "lock_rate_pooled": l1,
              "cell_summary": summary, "comparisons": comp, "l2_full_grid": full,
              "runs_with_core_held_at_end": len(held), "knob_signs": knob_signs, "unread": unread,
              "config": {"seeds": list(SEEDS), "landlords": LANDLORDS, "R0": R0S, "g": GS,
                         "tau_o": TAUS, "knobs": KNOBS}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok2 and ok3) else 1


def selftest() -> None:
    row = lambda tau, seed, share, still: {"landlord": "public", "R0": 1.0, "g": 0.0, "tau_o": tau, "seed": seed,
                                           "prod_share": share, "core_spells_open": still}
    rows = [row(0.0, 0, 0.40, 0), row(0.01, 0, 0.41, 0), row(0.02, 0, 0.30, 2), row(0.0, 1, 0.40, 0), row(0.01, 1, 0.40, 0)]
    f = full_grid_l2(rows)
    assert f["pairs"] == 3 and f["by_g"]["0.0"]["min"] == -0.1 and f["by_g"]["0.0"]["max"] == 0.01
    assert f["core_held_in_either"]["0.0"]["pairs"] == 1 and f["core_gone_in_both"]["0.0"]["pairs"] == 2
    assert f["by_g"]["0.0"]["over_0.005"] == 2, "a pair beyond 0.005 must be counted"
    rows[2]["prod_share"] = 0.40
    assert full_grid_l2(rows)["by_g"]["0.0"]["over_0.005"] == 1, "and one moved back inside must drop out"
    print("selftest ok: the whole-grid comparison pairs every cell with its lock-off twin, splits by "
          "whether a core unit is still held, and counts the pairs beyond 0.005")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(main())
