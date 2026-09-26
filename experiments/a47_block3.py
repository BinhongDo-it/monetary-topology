"""A47 block 3: the levy carrier, the cost floor, and two rent caps.

Checks, each with a planted error that must make it fail (--selftest):
  A47-1   instrument  all rules off is A3 bit for bit
  A47-1b  instrument  block 1's and block 2's stored previews reproduce on this module
  A47-5   instrument  levy on, housing closed: A6Model's run bit for bit (5 seeds x 300 rounds)
  A47-6   instrument  under a cap, regulated rent paid never exceeds the caps or the uncapped
                      rent, every capped round; rounds before cap_start are the uncapped run's
                      bit for bit
  A47-7   instrument  under the cost floor, every tier's price is at or above its cost price,
                      every round

Then one seed of each block-3 arm on the carrier, printed with seconds (D38). The carrier
is A3's registered network with A9's transfer levy at 0.20 (A47 results §R3), 1.1 units
per node with residual stock kept by its prior owner (A3b), tenancy by unit, new supply at
0.01 and the cost floor. The cap starts at round 150, so B129's square (regulated against
new, before against after) can be read inside one run.

Run from the repo root:
    python experiments/a47_block3.py
    python experiments/a47_block3.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a47_block2  # noqa: E402
from a47_block1 import a3_config, reading, reproduction  # noqa: E402
from a47_block1 import ARMS as BLOCK1_ARMS  # noqa: E402

from monetary_topology.asset import CLOSED, A3Config  # noqa: E402
from monetary_topology.housing_rules import A47Config, A47Model, HousingRules  # noqa: E402
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402
from monetary_topology.redistribution import A6Config, A6Model, FiscalSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a47_block3.json"
LEVY = 0.20
CAP_START = 150
CARRIER_ASSET = {"units_per_node": 1.1, "residual_owner": True}
CARRIER = HousingRules(levy_rate=LEVY, tenant_tier=True, new_supply_rate=0.01, cost_floor=True)

ARMS = {
    "carrier": CARRIER,
    "carrier + wage cap": replace(CARRIER, rent_cap="wage", cap_start=CAP_START),
    "carrier + berlin cap": replace(CARRIER, rent_cap="berlin", cap_start=CAP_START),
    "bound, market, public": replace(CARRIER, residence_bound=True, landlord="public"),
    "bound, market, listed 0.271": replace(CARRIER, residence_bound=True, landlord="listed",
                                           dividend_exit=0.271),
    "bound, market, public + wage cap": replace(CARRIER, residence_bound=True, landlord="public",
                                                rent_cap="wage", cap_start=CAP_START),
}


def run(rules: HousingRules, seed: int = 0, rounds: int = 300, asset=None) -> tuple[A47Model, float]:
    asset = dict(CARRIER_ASSET if asset is None else asset)
    if rules.residence_bound:
        asset["max_units"] = 1
    t0 = time.perf_counter()
    m = A47Model(A47Config(a3=a3_config(seed, rounds, **asset), rules=rules))
    m.history = m.run()
    return m, time.perf_counter() - t0


# -- checks ---------------------------------------------------------------------------

def carrier_reproduction(seeds=range(5), rounds=300, rate=LEVY) -> tuple[bool, list[str]]:
    diffs = []
    for s in seeds:
        net = NetworkConfig(spec=NetworkSpec(seed=s), seed=s, rounds=rounds)
        a = A6Model(A6Config(fiscal=FiscalSpec(rate=rate), network=net))
        ha = a.run()
        b = A47Model(A47Config(a3=A3Config(asset=CLOSED, network=net),
                               rules=HousingRules(levy_rate=LEVY)))
        hb = b.run()
        if not np.array_equal(a.holdings, b.holdings):
            diffs.append(f"seed {s} holdings")
        for f in ("total_volume", "effective_support", "layer2_inflow", "wage_paid", "issuance"):
            if not np.array_equal(getattr(ha, f), getattr(hb, f)):
                diffs.append(f"seed {s} {f}")
    return not diffs, diffs


def cap_check(m: A47Model) -> tuple[bool, dict]:
    rows = [r for r in m.rent_class_history if r[1]]
    if m.rules.rent_cap is None:
        return True, {}
    bad = [r[0] for r in rows if r[2] > r[7] + 1e-9 or r[2] > r[6] + 1e-9]
    ok = bool(rows) and not bad
    return ok, {"capped_rounds": len(rows), "violations": bad[:5],
                "regulated_paid_over_uncapped_end": round(rows[-1][2] / rows[-1][6], 4)
                if rows and rows[-1][6] > 0 else None}


def prefix_check(m: A47Model, seed=0) -> bool:
    """Rounds before cap_start equal the same run without the cap, bit for bit."""
    if m.rules.rent_cap is None:
        return True
    base, _ = run(replace(m.rules, rent_cap=None, cap_start=0), seed=seed,
                  rounds=len(m.claims_history))
    k = m.rules.cap_start
    return all(np.array_equal(a, b) for a, b in zip(m.claims_history[:k], base.claims_history[:k]))


def floor_check(m: A47Model) -> tuple[bool, float]:
    if not m.rules.cost_floor:
        return True, float("nan")
    gaps = [float(np.min(p - c)) for p, c in zip(m.price_history, m.cost_price_history)]
    return min(gaps) >= -1e-12, min(gaps)


def square(m: A47Model) -> dict:
    """B129's square in the model: log(new rent per unit / regulated rent per unit),
    mean over the 50 rounds before the cap against the 50 after."""
    rows = m.rent_class_history
    k = m.rules.cap_start if m.rules.rent_cap else None
    if not k:
        return {}
    def gap(sel):
        v = [np.log((r[4] / r[5]) / (r[2] / r[3])) for r in sel
             if r[3] > 0 and r[5] > 0 and r[2] > 0 and r[4] > 0]
        return float(np.mean(v)) if v else None
    pre = gap([r for r in rows if k - 50 <= r[0] < k])
    post = gap([r for r in rows if k <= r[0] < k + 50])
    return {"gap_pre": None if pre is None else round(pre, 4),
            "gap_post": None if post is None else round(post, 4),
            "square": None if None in (pre, post) else round(post - pre, 4)}


def extra(m: A47Model) -> dict:
    ph = np.asarray(m.price_history)
    unh = np.asarray(m.unhoused_history) if m.unhoused_history else np.zeros(1)
    return {"levied_total": round(float(m.levied), 2), "unhoused_mean": round(float(unh.mean()), 2),
            "built": float(m.built.sum()), "sale_price_low_tier_r149": round(float(ph[149, 0]), 4),
            "sale_price_low_tier_r199": round(float(ph[199, 0]), 4), **square(m)}


def selftest() -> None:
    ok, _ = carrier_reproduction(seeds=[0], rounds=40)
    assert ok, "A47-5 must pass on the levy with housing closed"
    ok, _ = carrier_reproduction(seeds=[0], rounds=40, rate=0.10)
    assert not ok, "A47-5 must catch a different levy"
    m, _ = run(ARMS["carrier + wage cap"], rounds=170)
    assert cap_check(m)[0] and prefix_check(m) and floor_check(m)[0]
    r = list(m.rent_class_history[-1]); r[2] = r[7] + 1.0
    m.rent_class_history[-1] = tuple(r)
    assert not cap_check(m)[0], "A47-6 must catch rent paid above the caps"
    m.claims_history[3] = m.claims_history[3] + 1e-6
    assert not prefix_check(m), "A47-6 must catch a pre-cap round that moved"
    m.price_history[5] = m.cost_price_history[5] - 1.0
    assert not floor_check(m)[0], "A47-7 must catch a price under cost"
    try:
        HousingRules(rent_cap="wage")
    except ValueError:
        pass
    else:
        raise AssertionError("a cap without tenancy must be refused")
    print("selftest ok: A47-5 catches a different levy; A47-6 catches rent above the cap and a "
          "moved pre-cap round; A47-7 catches a price under cost; a cap without tenancy is refused")


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A47-1 [instrument]: rules off is A3" + (f"; {d1[:3]}" if d1 else ""))
    ok1b1, d1b1 = a47_block2.block1_regression()
    stored2 = json.loads(a47_block2.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    d1b2 = []
    for name, rules in a47_block2.ARMS.items():
        m2, opening, _ = a47_block2.run_with_opening(rules)
        now = {**a47_block2.tenancy_check(m2)[1], **a47_block2.supply_check(m2, *opening)[1], **reading(m2)}
        for k, v in now.items():
            if stored2[name].get(k) != v:
                d1b2.append(f"{name}: {k}")
    ok1b = ok1b1 and not d1b2
    print(f"{'PASS' if ok1b else 'FAIL'} A47-1b [instrument]: block 1 and block 2 previews reproduce"
          + (f"; {(d1b1 + d1b2)[:5]}" if not ok1b else ""))
    ok5, d5 = carrier_reproduction()
    print(f"{'PASS' if ok5 else 'FAIL'} A47-5 [instrument]: levy {LEVY} with housing closed is "
          f"A6Model's run, 5 seeds x 300 rounds" + (f"; {d5[:3]}" if d5 else ", bit for bit"))
    arms, ok6, ok7 = {}, True, True
    for name, rules in ARMS.items():
        m, secs = run(rules)
        c_ok, c = cap_check(m)
        p_ok = prefix_check(m)
        f_ok, fgap = floor_check(m)
        ok6 &= c_ok and p_ok
        ok7 &= f_ok
        arms[name] = {"seconds": round(secs, 2), "cap_ok": c_ok, "prefix_ok": p_ok, **c,
                      "floor_ok": f_ok, "min_price_minus_cost": round(fgap, 6),
                      **reading(m), **extra(m)}
    print(f"{'PASS' if ok6 else 'FAIL'} A47-6 [instrument]: caps hold and pre-cap rounds unmoved")
    print(f"{'PASS' if ok7 else 'FAIL'} A47-7 [instrument]: cost floor holds every round")
    keys = ["seconds", "price_ratio_end_to_start_low_tier", "sale_price_low_tier_r149",
            "sale_price_low_tier_r199", "sales_total", "owners_end", "unhoused_mean", "built",
            "rent_total", "levied_total", "net_worth_top_decile_share",
            "net_worth_production_layer_share", "regulated_paid_over_uncapped_end",
            "gap_pre", "gap_post", "square"]
    print("\none seed (0), 300 rounds, carrier = levy 0.20, 1.1 units/node, tenancy, supply 0.01, floor:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {
        "stage": "A47-block3",
        "criteria": [
            {"name": "A47-1", "kind": "instrument", "passed": ok1, "detail": "rules off is A3"},
            {"name": "A47-1b", "kind": "instrument", "passed": ok1b, "detail": "block 1-2 previews reproduce"},
            {"name": "A47-5", "kind": "instrument", "passed": ok5, "detail": "levy carrier is A6Model"},
            {"name": "A47-6", "kind": "instrument", "passed": ok6, "detail": "caps enforced; pre-cap unmoved"},
            {"name": "A47-7", "kind": "instrument", "passed": ok7, "detail": "cost floor"},
        ],
        "preview_seed0": arms,
        "config": {"levy_rate": LEVY, "cap_start": CAP_START, "carrier_asset": CARRIER_ASSET,
                   "arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__} for k, v in ARMS.items()}},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok1b and ok5 and ok6 and ok7) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
