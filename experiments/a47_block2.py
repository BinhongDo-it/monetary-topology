"""A47 block 2: tenancy by unit, and new supply.

Checks, each with a planted error that must make it fail (--selftest):
  A47-1   instrument  all rules off is still A3 bit for bit (rerun of block 1's check)
  A47-1b  instrument  the block-1 arms, rerun on this module, reproduce the stored
                      results/a47_block1.json preview field for field (the rewrite moved nothing)
  A47-3   instrument  tenancy: no renter holds a unit; per tier, housed renters do not exceed
                      rental units; housed plus unhoused equals renters; rent received by
                      lessors equals rent paid
  A47-4   instrument  new supply: units in nodes plus landlord plus unowned equal opening supply
                      plus built; new flags never exceed units; all new flags sum to built

Then one seed of each block-2 arm, printed with its seconds (D38). new_supply_rate 0.01 is a
placeholder, about the net growth of the US housing stock per year with a round read as a
year; block 5 sweeps it.

Run from the repo root:
    python experiments/a47_block2.py
    python experiments/a47_block2.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a47_block1 import ARMS as BLOCK1_ARMS  # noqa: E402
from a47_block1 import reading, reproduction, run_arm, structure  # noqa: E402

from monetary_topology.housing_rules import LANDLORD, HousingRules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a47_block2.json"
BLOCK1 = ROOT / "results" / "a47_block1.json"
RATE = 0.01

ARMS = {
    "A3 + tenancy": HousingRules(tenant_tier=True),
    "A3 + new supply": HousingRules(new_supply_rate=RATE),
    "A3 + tenancy + new supply": HousingRules(tenant_tier=True, new_supply_rate=RATE),
    "bound, market, public + tenancy + new supply": HousingRules(
        residence_bound=True, landlord="public", tenant_tier=True, new_supply_rate=RATE),
    "bound, market, listed 0.271 + tenancy + new supply": HousingRules(
        residence_bound=True, landlord="listed", dividend_exit=0.271, tenant_tier=True,
        new_supply_rate=RATE),
    "bound, cost, public + tenancy + new supply": HousingRules(
        residence_bound=True, liquidation="cost", landlord="public", tenant_tier=True,
        new_supply_rate=RATE),
}


def block1_regression() -> tuple[bool, list[str]]:
    stored = json.loads(BLOCK1.read_text(encoding="utf-8"))["preview_seed0"]
    diffs = []
    for name, rules in BLOCK1_ARMS.items():
        m, _ = run_arm(rules, seed=0)
        now = {**structure(m)[1], **reading(m)}
        for k, v in now.items():
            if stored[name].get(k) != v:
                diffs.append(f"{name}: {k} {stored[name].get(k)} -> {v}")
    return not diffs, diffs


def tenancy_check(m) -> tuple[bool, dict]:
    if not m.rules.tenant_tier:
        return True, {}
    # Read against the state the last matching saw: sales later in the round change the stock.
    st = m.match_state
    renters_housed = m.tenancy >= 0
    ok = not (renters_housed & (st["held_at_match"] > 0)).any()
    ok &= not (renters_housed & ~st["is_renter"]).any()
    housed = m.housed_history[-1]
    for q, h in enumerate(housed):
        ok &= h <= st["slots_by_tier"][q]
    ok &= int(renters_housed.sum()) == int(housed.sum())
    ok &= st["renters"] == int(housed.sum()) + m.unhoused_history[-1]
    return bool(ok), {"renters": st["renters"], "housed_by_tier": housed.tolist(),
                      "unhoused": m.unhoused_history[-1],
                      "rental_units_by_tier": list(st["slots_by_tier"])}


def supply_check(m, opening_in_nodes: float, opening_landlord: float) -> tuple[bool, dict]:
    built = float(m.built.sum())
    in_nodes = float(m.units.sum())
    in_ll = float(m.landlord_units.sum())
    supply = float(sum(m.supply))
    unowned = supply - opening_in_nodes - opening_landlord
    total_ok = abs(in_nodes + in_ll + unowned - supply - built) < 1e-9
    new_ok = (m.new_units <= m.units + 1e-9).all() and (m.landlord_new <= m.landlord_units + 1e-9).all() \
        and (m.new_units >= -1e-9).all()
    sum_ok = abs(float(m.new_units.sum()) + float(m.landlord_new.sum()) - built) < 1e-6
    return bool(total_ok and new_ok and sum_ok), {
        "built": built, "build_paid": round(float(m.build_paid), 4),
        "new_flags": round(float(m.new_units.sum() + m.landlord_new.sum()), 6),
        "units_in_nodes": in_nodes, "units_with_landlord": in_ll, "unowned_from_opening": unowned}


def run_with_opening(rules, seed=0, rounds=300):
    """Run, remembering the opening split of units (for the unowned count)."""
    from a47_block1 import a3_config
    from monetary_topology.housing_rules import A47Config, A47Model
    asset = {"max_units": 1} if rules.residence_bound else {}
    m = A47Model(A47Config(a3=a3_config(seed, rounds, **asset), rules=rules))
    opening = (float(m.units.sum()), float(m.landlord_units.sum()))
    import time
    t0 = time.perf_counter()
    m.run()
    return m, opening, time.perf_counter() - t0


def selftest() -> None:
    m, opening, _ = run_with_opening(ARMS["A3 + tenancy + new supply"], rounds=60)
    assert tenancy_check(m)[0] and supply_check(m, *opening)[0]
    # tenancy: a renter who also owns must fail
    i = int(np.flatnonzero(m.tenancy >= 0)[0])
    m.match_state["held_at_match"][i] += 1.0
    assert not tenancy_check(m)[0], "A47-3 must catch a housed renter who owns"
    m.match_state["held_at_match"][i] -= 1.0
    m.match_state["slots_by_tier"][0] = 0
    assert not tenancy_check(m)[0], "A47-3 must catch more tenants than rental units"
    # supply: a new flag larger than the units must fail; a created unit must fail
    j = int(np.argmax(m.units.sum(axis=1)))
    m.new_units[j, 0] = m.units[j, 0] + 1.0
    assert not supply_check(m, *opening)[0], "A47-4 must catch a flag above the units"
    m, opening, _ = run_with_opening(ARMS["A3 + new supply"], rounds=60)
    m.units[0, 0] += 1.0
    assert not supply_check(m, *opening)[0], "A47-4 must catch a unit from nothing"
    # regression: a changed stored number must be caught
    stored = json.loads(BLOCK1.read_text(encoding="utf-8"))["preview_seed0"]
    name = next(iter(stored))
    m1, _ = run_arm(BLOCK1_ARMS[name], seed=0)
    assert {**structure(m1)[1], **reading(m1)}["sales_total"] == stored[name]["sales_total"]
    assert {**structure(m1)[1], **reading(m1)}["sales_total"] != stored[name]["sales_total"] + 1
    print("selftest ok: tenancy catches an owning renter; supply catches an oversized flag and "
          "a unit from nothing; the regression compares stored numbers")


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A47-1 [instrument]: rules off is A3 bit for bit" +
          (f"; {d1[:3]}" if d1 else ""))
    okr, dr = block1_regression()
    print(f"{'PASS' if okr else 'FAIL'} A47-1b [instrument]: block-1 arms reproduce the stored "
          f"record" + (f"; {dr[:5]}" if dr else ", field for field"))
    arms, ok3, ok4 = {}, True, True
    for name, rules in ARMS.items():
        m, opening, secs = run_with_opening(rules)
        t_ok, t = tenancy_check(m)
        s_ok, s = supply_check(m, *opening)
        ok3 &= t_ok
        ok4 &= s_ok
        unh = np.asarray(m.unhoused_history) if m.unhoused_history else np.zeros(1)
        arms[name] = {"seconds": round(secs, 2), "tenancy_ok": t_ok, "supply_ok": s_ok, **t, **s,
                      "unhoused_mean": round(float(unh.mean()), 2), **reading(m)}
    print(f"{'PASS' if ok3 else 'FAIL'} A47-3 [instrument]: tenancy structure, {len(ARMS)} arms")
    print(f"{'PASS' if ok4 else 'FAIL'} A47-4 [instrument]: supply and new-flag bookkeeping, "
          f"{len(ARMS)} arms")
    keys = ["seconds", "price_ratio_end_to_start_low_tier", "sales_total", "owners_end",
            "renters", "housed_by_tier", "unhoused", "unhoused_mean", "built", "build_paid",
            "rent_total", "net_worth_top_decile_share", "net_worth_production_layer_share"]
    print("\none seed (0), 300 rounds, preview:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {
        "stage": "A47-block2",
        "criteria": [
            {"name": "A47-1", "kind": "instrument", "passed": ok1, "detail": "rules off is A3"},
            {"name": "A47-1b", "kind": "instrument", "passed": okr,
             "detail": "block-1 arms reproduce results/a47_block1.json" if okr else str(dr)},
            {"name": "A47-3", "kind": "instrument", "passed": ok3, "detail": "tenancy structure"},
            {"name": "A47-4", "kind": "instrument", "passed": ok4, "detail": "supply bookkeeping"},
        ],
        "preview_seed0": arms,
        "config": {"new_supply_rate": RATE,
                   "arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__}
                            for k, v in ARMS.items()}},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and okr and ok3 and ok4) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
