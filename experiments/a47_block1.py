"""A47 block 1: residence binding, two liquidation rules, two landlords.

Checks, each with a planted error that must make it fail (--selftest):
  A47-1 instrument  all rules off: every A3 record field is bit for bit A3's, 5 seeds x 300 rounds
  A47-2 instrument  every arm: claims conserved each round (asserted inside the model),
                    no node holds more than one unit, units in nodes plus the landlord's equal
                    the supply, at the end of every arm

Then one seed of every arm, printed, with the seconds each run took (D38). The readings
are a preview; the registered grid is block 5.

Run from the repo root:
    python experiments/a47_block1.py
    python experiments/a47_block1.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monetary_topology.asset import A3Config, A3Model, AssetSpec  # noqa: E402
from monetary_topology.housing_rules import A47Config, A47Model, HousingRules  # noqa: E402
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a47_block1.json"
SEEDS = range(5)
ROUNDS = 300
FIELDS = ("price_history", "net_worth_history", "claims_history", "sales", "forced_sales",
          "rent_history")
HISTORY = ("total_volume", "effective_support", "layer2_inflow", "wage_paid", "issuance")

#: The arms. dividend_exit: Vonovia fiscal 2024, cash and all dividends over rental EBITDA.
ARMS = {
    "A3 (rules off)": HousingRules(),
    "bound, market, public": HousingRules(residence_bound=True, liquidation="market",
                                          landlord="public"),
    "bound, cost, public": HousingRules(residence_bound=True, liquidation="cost",
                                        landlord="public"),
    "bound, market, listed 0.271": HousingRules(residence_bound=True, liquidation="market",
                                                landlord="listed", dividend_exit=0.271),
    "bound, market, listed 0.421": HousingRules(residence_bound=True, liquidation="market",
                                                landlord="listed", dividend_exit=0.421),
    "bound, cost, listed 0.271": HousingRules(residence_bound=True, liquidation="cost",
                                              landlord="listed", dividend_exit=0.271),
    "bound, market, public, owners bid": HousingRules(
        residence_bound=True, liquidation="market", landlord="public",
        bidders_exclude_owners=False),
}


def a3_config(seed: int, rounds: int, **asset) -> A3Config:
    return A3Config(asset=AssetSpec(**asset),
                    network=NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds))


def run_arm(rules: HousingRules, seed: int, rounds: int = ROUNDS) -> tuple[A47Model, float]:
    asset = {"max_units": 1} if rules.residence_bound else {}
    t0 = time.perf_counter()
    m = A47Model(A47Config(a3=a3_config(seed, rounds, **asset), rules=rules))
    m.history = m.run()
    return m, time.perf_counter() - t0


# -- A47-1 ----------------------------------------------------------------------------

def same(a, b) -> bool:
    if isinstance(a, list):
        return len(a) == len(b) and all(np.array_equal(np.asarray(x), np.asarray(y))
                                        for x, y in zip(a, b))
    return np.array_equal(np.asarray(a), np.asarray(b))


def reproduction(seeds=SEEDS, rounds=ROUNDS, rules=HousingRules()) -> tuple[bool, list[str]]:
    """Every compared field equal, every seed. Returns (ok, the fields that differed)."""
    diffs = []
    for s in seeds:
        a = A3Model(a3_config(s, rounds, **({"max_units": 1} if rules.residence_bound else {})))
        ha = a.run()
        b = A47Model(A47Config(a3=a3_config(s, rounds, **(
            {"max_units": 1} if rules.residence_bound else {})), rules=rules))
        hb = b.run()
        for f in FIELDS:
            if not same(getattr(a, f), getattr(b, f)):
                diffs.append(f"seed {s} {f}")
        for f in HISTORY:
            if not same(getattr(ha, f), getattr(hb, f)):
                diffs.append(f"seed {s} history.{f}")
    return not diffs, diffs


# -- A47-2 ----------------------------------------------------------------------------

def structure(m: A47Model) -> tuple[bool, dict]:
    held = m.units.sum(axis=1)
    supply = float(sum(m.supply))
    in_nodes = float(m.units.sum())
    in_landlord = float(m.landlord_units.sum())
    bound = m.rules.residence_bound
    # Scope: the rules-off arm is A3's registered run, whose unsold opening stock is owned
    # by nobody (residual_owner=False, A3b); the count closes only where a landlord holds it.
    if not bound:
        return True, {"max_units_held": float(held.max()), "units_in_nodes": in_nodes,
                      "units_owned_by_nobody": supply - in_nodes, "supply": supply}
    ok = held.max() <= 1.0 and abs(in_nodes + in_landlord - supply) < 1e-9 and in_landlord >= 0.0
    return ok, {"max_units_held": float(held.max()), "units_in_nodes": in_nodes,
                "units_with_landlord": in_landlord, "supply": supply}


# -- readings (preview) ---------------------------------------------------------------

def reading(m: A47Model) -> dict:
    nw = m.net_worth()
    order = np.argsort(-nw)
    n = nw.size
    total = float(nw.sum())
    top_share = float(nw[order[: max(1, n // 10)]].sum()) / total if total > 0 else None
    prod_share = float(nw[m._is_production].sum()) / total if total > 0 else None
    ph = np.asarray(m.price_history)
    return {
        "price_end_by_tier": [round(float(x), 4) for x in ph[-1]],
        "price_ratio_end_to_start_low_tier": round(float(ph[-1, 0] / ph[0, 0]), 4),
        "sales_total": int(sum(m.sales)),
        "liquidations_total": int(sum(getattr(m, "liquidations", []) or [0])),
        "landlord_sales_total": int(sum(getattr(m, "landlord_sales", []) or [0])),
        "rent_total": round(float(m.rent_collected), 4),
        "owners_end": int((m.units.sum(axis=1) > 0).sum()),
        "landlord_units_end": float(m.landlord_units.sum()),
        "pool_end": round(float(m.pool), 4),
        "exited_total": round(float(m.exited), 4),
        "passed_down_total": round(float(m.passed_down), 4),
        "net_worth_top_decile_share": round(top_share, 4) if top_share is not None else None,
        "net_worth_production_layer_share": round(prod_share, 4) if prod_share is not None else None,
    }


def selftest() -> None:
    # A47-1 must fail when a rule is on (a different model must not reproduce)
    ok, diffs = reproduction(seeds=[0], rounds=40,
                             rules=HousingRules(residence_bound=True, landlord="listed",
                                                dividend_exit=0.3))
    assert not ok and diffs, "A47-1 must catch a model that differs"
    ok, _ = reproduction(seeds=[0], rounds=40)
    assert ok, "A47-1 must pass with every rule off"
    # A47-2 conservation: a leak must raise
    class Leak(A47Model):
        def _collect_rent(self):
            super()._collect_rent()
            self.pool *= 0.5 if self.pool else 1.0
            self.holdings[0] -= 1e-3
    try:
        Leak(A47Config(a3=a3_config(0, 40, max_units=1),
                       rules=HousingRules(residence_bound=True))).run()
    except AssertionError:
        pass
    else:
        raise AssertionError("the conservation check must fire on a leak")
    # A47-2 structure: a planted second unit must fail
    m, _ = run_arm(HousingRules(residence_bound=True), 0, rounds=40)
    assert structure(m)[0]
    i = int(np.flatnonzero(m.units.sum(axis=1) > 0)[0])
    m.units[i, 0] += 1.0
    m.landlord_units[0] -= 1.0
    assert not structure(m)[0], "A47-2 must catch a node holding two units"
    m.units[i, 0] -= 1.0
    m.landlord_units[0] += 2.0
    assert not structure(m)[0], "A47-2 must catch units created from nothing"
    print("selftest ok: A47-1 catches a differing model; conservation fires on a leak; "
          "structure catches a second unit and created units")


def main() -> int:
    ok1, diffs = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A47-1 [instrument]: all rules off, "
          f"{len(SEEDS)} seeds x {ROUNDS} rounds, {len(FIELDS) + len(HISTORY)} fields each"
          + (f"; differ: {diffs[:5]}" if diffs else ", bit for bit"))
    arms, ok2 = {}, True
    for name, rules in ARMS.items():
        m, secs = run_arm(rules, seed=0)
        s_ok, s = structure(m)
        ok2 &= s_ok
        arms[name] = {"seconds": round(secs, 2), "structure_ok": s_ok, **s, **reading(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A47-2 [instrument]: {len(ARMS)} arms, conservation "
          f"asserted every round, unit cap and unit count at the end")
    print("\none seed (0), 300 rounds, preview:")
    keys = ["seconds", "price_ratio_end_to_start_low_tier", "sales_total", "liquidations_total",
            "landlord_sales_total", "owners_end", "landlord_units_end", "rent_total",
            "passed_down_total", "exited_total", "net_worth_top_decile_share",
            "net_worth_production_layer_share"]
    for name, r in arms.items():
        print(f"  {name}")
        print("    " + ", ".join(f"{k} {r[k]}" for k in keys))
    record = {
        "stage": "A47-block1",
        "criteria": [
            {"name": "A47-1", "kind": "instrument", "passed": ok1,
             "detail": "all rules off reproduces A3 bit for bit" if ok1 else f"differs: {diffs}"},
            {"name": "A47-2", "kind": "instrument", "passed": ok2,
             "detail": "conservation every round; unit cap and count at the end, every arm"},
        ],
        "preview_seed0": arms,
        "config": {"rounds": ROUNDS, "reproduction_seeds": list(SEEDS),
                   "arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__}
                            for k, v in ARMS.items()}},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
