"""A50 block 7: why "both parked" under binding reads lower at L 100 than at L 25.

Block 6 found, for the spendable arm under binding, the production share over the no-fund
arm rising from L 1 to L 25, falling at L 100, and rising again to "never", every seed and
levy, under both authorities. This block prints the objects: where the parked money went
(paid back at L, spent on dwellings, still in the accounts at the end), and what the
production layer holds at the end (holdings, dwellings at their marks, accounts).

Grid: bound, both parked, c 0.12, L {5, 25, 50, 100, 150, never} x authority {refills,
target counts accounts} x five seeds, levy 0.20.

Checks, each with a planted error that must make it fail (--selftest):
  A50-15  instrument  every parked unit is accounted for: parked = spent on dwellings + paid
                      back + still in the accounts, per run
Readings (A50-16, own_reading): the three exits and the production layer's end holdings,
against L; per seed, the sign of "spent" across L and of the end balance from L 25 to L 100.

Run from the repo root:
    python experiments/a50_block7.py
    python experiments/a50_block7.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a50_common import rules  # noqa: E402
from a50_grid import SEEDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block7.json"
LS = (5, 25, 50, 100, 150, 0)
AUTH = {"refills": {}, "target": {"provident_in_target": True}}
KEYS = ("prod_share", "prod_holdings", "prod_dwellings", "accounts_end", "nonprod_net_worth", "parked",
        "spent", "released", "owners_end", "sales", "rent", "pool_end", "issuance_total", "circulating_end")


def exits_check(m) -> tuple[bool, float]:
    parked = m.pf_contrib_employee + m.pf_contrib_employer
    res = parked - (m.pf_spent_from_accounts + m.pf_released + float(m.account.sum()))
    return abs(res) <= 1e-9 * max(1.0, parked), res


def one(args):
    auth, L, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    extra = dict(AUTH[auth])
    if L:
        extra["provident_release"] = L
    m, _ = a47_block3.run(rules("bound", "both parked", 0.20, **extra), seed=seed)
    p = m._is_production
    marks = m.cost_price() if m.rules.liquidation == "cost" else m.price
    nw = m.net_worth()
    ok, res = exits_check(m)
    h = m.history
    return {"auth": auth, "L": L, "seed": seed, "exits_ok": ok,
            "prod_share": round(float(nw[p].sum() / nw.sum()), 4),
            "prod_holdings": round(float(m.holdings[p].sum()), 4),
            "prod_dwellings": round(float((m.units @ marks)[p].sum()), 4),
            "accounts_end": round(float(m.account.sum()), 4),
            "nonprod_net_worth": round(float(nw[~p].sum()), 4),
            "parked": round(m.pf_contrib_employee + m.pf_contrib_employer, 4),
            "spent": round(m.pf_spent_from_accounts, 4), "released": round(m.pf_released, 4),
            "owners_end": int((m.units.sum(axis=1) > 0).sum()), "sales": int(sum(m.sales)),
            "rent": round(float(m.rent_collected), 4), "pool_end": round(float(m.pool), 4),
            "issuance_total": round(float(np.sum(h.issuance)), 4),
            "circulating_end": round(float(np.asarray(h.total_claims)[-1]), 4)}


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(rules("bound", "both parked", 0.20, provident_release=25), rounds=80)
    assert exits_check(m)[0] and m.pf_released > 0 and m.pf_spent_from_accounts > 0, \
        "the arm must use both exits and balance"
    m.pf_spent_from_accounts += 1.0
    assert not exits_check(m)[0], "A50-15 must catch a unit of parked money that went nowhere"
    print("selftest ok: A50-15 catches parked money that is not accounted for")


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    jobs = [(a, L, s) for a in AUTH for L in LS for s in SEEDS]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=2))
    ok15 = all(r["exits_ok"] for r in rows)
    print(f"{'PASS' if ok15 else 'FAIL'} A50-15 [instrument]: parked = spent + paid back + still in accounts, "
          f"{len(rows)} runs")
    print("\nbound, both parked, c 0.12, levy 0.20, mean over 5 seeds (L 0 = never): " + " | ".join(KEYS))
    summary = {}
    for a in AUTH:
        for L in LS:
            rs = [r for r in rows if r["auth"] == a and r["L"] == L]
            s = {k: round(float(np.mean([r[k] for r in rs])), 4) for k in KEYS}
            summary[f"{a} | L {L}"] = s
            print(f"  {a:7s} | L {L:3d}  " + " | ".join(str(s[k]) for k in KEYS))
    print("\nper seed:")
    signs = {}
    for a in AUTH:
        by = {(r["L"], r["seed"]): r for r in rows if r["auth"] == a}
        order = (5, 25, 50, 100, 150, 0)
        spent_up = [all(by[(y, s)]["spent"] > by[(x, s)]["spent"] for x, y in zip(order, order[1:])) for s in SEEDS]
        acc_down = [by[(100, s)]["accounts_end"] < by[(25, s)]["accounts_end"] for s in SEEDS]
        share_down = [by[(100, s)]["prod_share"] < by[(25, s)]["prod_share"] for s in SEEDS]
        dwell = [round(by[(100, s)]["prod_dwellings"] - by[(25, s)]["prod_dwellings"], 4) for s in SEEDS]
        acc = [round(by[(100, s)]["accounts_end"] - by[(25, s)]["accounts_end"], 4) for s in SEEDS]
        signs[a] = {"spent_rises_with_L": spent_up, "accounts_end_L100_below_L25": acc_down,
                    "share_L100_below_L25": share_down, "dwellings_L100_minus_L25": dwell,
                    "accounts_L100_minus_L25": acc}
        print(f"  {a}: spent rises at every step of L {spent_up}; accounts at the end lower at L 100 than L 25 "
              f"{acc_down}; share lower {share_down}\n      dwellings L100 - L25 {dwell}; accounts L100 - L25 {acc}")
    record = {"stage": "A50-block7",
              "criteria": [{"name": "A50-15", "kind": "instrument", "passed": ok15,
                            "detail": f"parked = spent + paid back + still in accounts, {len(rows)} runs"}],
              "rows": rows, "cell_summary": summary, "per_seed": signs,
              "config": {"regime": "bound", "arm": "both parked", "c": 0.12, "levy": 0.20, "L": list(LS),
                         "authorities": AUTH, "seeds": list(SEEDS), "short_stay_share": 0.1}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if ok15 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
