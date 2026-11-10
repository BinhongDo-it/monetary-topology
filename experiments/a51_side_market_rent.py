"""A51, a side question: a public landlord that charges the core's location rent at market.

A51 read that a public landlord renting at cost leaves the core's location value with its
tenants, and a market landlord collects it. Here the public landlord is kept (rent into the
public pool, not to a listed owner) and only its pricing changes: `public_rent_cost` off. Under
residence binding the other tiers stay at cost, so the change falls on the core's premium.

Carrier: A51's (core share 0.1, s 0.083, R0 1.16, tau_o 0.02, lease 1), g {0, 0.005}, five
seeds. Printed per run: core tenant-rounds and the last occupied round, location rent collected
and left with tenants over the run, the pool at the end, production-layer and top-decile shares.

Run from the repo root:
    python experiments/a51_side_market_rent.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a47_block3  # noqa: E402
import a51_block1  # noqa: E402
from a51_block1 import S_HIGH, split_asset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a51_side_market_rent.json"
SEEDS = tuple(range(5))


def one(g: float, cost: bool, seed: int) -> dict:
    rl = replace(a51_block1.rules_for("public", g, S_HIGH), public_rent_cost=cost)
    m, _ = a47_block3.run(rl, seed=seed, asset=split_asset(0.1))
    loc = np.asarray(m.location_history, dtype=float)
    occ = loc[:, 0] > 0
    r = a51_block1.preview_row(m)
    return {"g": g, "public_rent_cost": cost, "seed": seed,
            "core_tenant_rounds": int(loc[:, 0].sum()),
            "last_occupied_round": int(np.flatnonzero(occ)[-1]) if occ.any() else None,
            "location_rent_collected_total": round(float(loc[:, 3].sum()), 4),
            "location_rent_left_with_tenants_total": round(float(loc[:, 2].sum()), 4),
            "commute_saved_total": r["commute_saved_total"],
            "pool_end": round(float(m.pool), 4),
            "prod_share": r["prod_share"], "top_decile": r["top_decile"]}


def main() -> int:
    rows = [one(g, c, s) for g in (0.0, 0.005) for c in (True, False) for s in SEEDS]
    summary = {}
    for g in (0.0, 0.005):
        a = {r["seed"]: r for r in rows if r["g"] == g and r["public_rent_cost"]}
        b = {r["seed"]: r for r in rows if r["g"] == g and not r["public_rent_cost"]}
        for tag, d in (("cost", a), ("market", b)):
            print(f"g {g} {tag:6s}: core tenant-rounds {[d[s]['core_tenant_rounds'] for s in SEEDS]}, "
                  f"last occupied {[d[s]['last_occupied_round'] for s in SEEDS]}, "
                  f"collected {[d[s]['location_rent_collected_total'] for s in SEEDS]}, "
                  f"pool end {[d[s]['pool_end'] for s in SEEDS]}, prod {[d[s]['prod_share'] for s in SEEDS]}")
        diff = [round(b[s]["prod_share"] - a[s]["prod_share"], 4) for s in SEEDS]
        pool = [round(b[s]["pool_end"] - a[s]["pool_end"], 4) for s in SEEDS]
        summary[f"g {g}"] = {"prod_share_market_minus_cost": diff, "pool_end_market_minus_cost": pool}
        print(f"  market - cost: prod share {diff}; pool at end {pool}")
    OUT.write_text(json.dumps({"stage": "A51-side-market-rent", "rows": rows, "summary": summary,
                               "config": {"landlord": "public", "s": S_HIGH, "core_share": 0.1, "lease": 1,
                                          "R0": a51_block1.R0, "tau_o": a51_block1.TAU_O, "seeds": list(SEEDS)}},
                              indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
