"""A47 block 4: public housing that keeps itself, with the state behind it.

Checks, each with a planted error that must make it fail (--selftest):
  A47-1   instrument  all rules off is A3 bit for bit
  A47-1b  instrument  block 1, 2 and 3 stored previews reproduce on this module
  A47-5   instrument  the levy carrier is A6Model's run bit for bit
  A47-8   instrument  public housing: units in nodes plus landlord plus unowned equal the
                      opening supply plus private and public building; the pool is never
                      negative; the state's top-up never exceeds what was levied; a
                      self-maintaining pool passes nothing down

Then one seed of each block-4 arm on the block-3 carrier. public_build_rate 0.01 is a
placeholder; block 5 sweeps it.

Run from the repo root:
    python experiments/a47_block4.py
    python experiments/a47_block4.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a47_block2  # noqa: E402
import a47_block3  # noqa: E402
from a47_block1 import reading, reproduction  # noqa: E402

from monetary_topology.housing_rules import HousingRules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a47_block4.json"
CARRIER = a47_block3.CARRIER
SELF = dict(public_build_rate=0.01, public_rent_cost=True, public_maintenance=True,
            state_topup=True, pool_pass_rate=0.0)

ARMS = {
    "carrier": CARRIER,
    "carrier + public housing": replace(CARRIER, **SELF),
    "carrier + public housing + wage cap": replace(CARRIER, **SELF, rent_cap="wage",
                                                   cap_start=a47_block3.CAP_START),
    "bound, public, pass-down (block 3)": replace(CARRIER, residence_bound=True, landlord="public"),
    "bound, public, self-maintaining": replace(CARRIER, residence_bound=True, landlord="public", **SELF),
    "bound, public, self-maintaining, no state": replace(CARRIER, residence_bound=True,
                                                          landlord="public",
                                                          **{**SELF, "state_topup": False}),
}


def run(rules):
    m, secs = a47_block3.run(rules)
    opening = None
    return m, secs


def opening_split(rules, seed=0):
    from a47_block1 import a3_config
    from monetary_topology.housing_rules import A47Config, A47Model
    asset = dict(a47_block3.CARRIER_ASSET)
    if rules.residence_bound:
        asset["max_units"] = 1
    m = A47Model(A47Config(a3=a3_config(seed, 1, **asset), rules=rules))
    return float(m.units.sum()), float(m.landlord_units.sum())


def public_check(m, opening) -> tuple[bool, dict]:
    supply = float(sum(m.supply))
    unowned = supply - opening[0] - opening[1]
    built = float(m.built.sum()) + float(m.public_built.sum())
    count_ok = abs(float(m.units.sum()) + float(m.landlord_units.sum()) + unowned - supply - built) < 1e-9
    pool_ok = min(m.pool_history, default=0.0) >= -1e-12 and m.pool >= -1e-12
    topup_ok = m.topup_total <= m.levied + 1e-9
    pass_ok = not (m.rules.pool_pass_rate == 0.0 and m.passed_down > 0.0)
    ok = count_ok and pool_ok and topup_ok and pass_ok
    return bool(ok), {"count_ok": count_ok, "pool_ok": pool_ok, "topup_ok": topup_ok,
                      "pass_ok": pass_ok, "public_built": float(m.public_built.sum()),
                      "landlord_units_end": float(m.landlord_units.sum()),
                      "pool_end": round(float(m.pool), 4), "topup_total": round(m.topup_total, 4),
                      "levied_total": round(m.levied, 2),
                      "maintenance_paid": round(m.maintenance_paid, 4),
                      "maintenance_unfunded": round(m.maintenance_unfunded, 4),
                      "public_build_paid": round(m.public_build_paid, 4),
                      "public_tenants_end": m.public_tenants_history[-1] if m.public_tenants_history else 0}


def regression() -> tuple[bool, list[str]]:
    d = []
    ok, d1 = a47_block2.block1_regression()
    d += d1
    stored2 = json.loads(a47_block2.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    for name, rules in a47_block2.ARMS.items():
        m, opening, _ = a47_block2.run_with_opening(rules)
        now = {**a47_block2.tenancy_check(m)[1], **a47_block2.supply_check(m, *opening)[1], **reading(m)}
        d += [f"b2 {name}: {k}" for k, v in now.items() if stored2[name].get(k) != v]
    stored3 = json.loads(a47_block3.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    for name, rules in a47_block3.ARMS.items():
        m, _ = a47_block3.run(rules)
        now = {**a47_block3.cap_check(m)[1], **reading(m), **a47_block3.extra(m)}
        d += [f"b3 {name}: {k}" for k, v in now.items() if stored3[name].get(k) != v]
    return not d, d


def selftest() -> None:
    rules = ARMS["carrier + public housing"]
    m, _ = a47_block3.run(replace(rules), rounds=60)
    op = opening_split(rules)
    assert public_check(m, op)[0]
    m.landlord_units[0] += 1.0
    assert not public_check(m, op)[0], "A47-8 must catch a public unit from nothing"
    m.landlord_units[0] -= 1.0
    m.topup_total = m.levied + 1.0
    assert not public_check(m, op)[0], "A47-8 must catch a top-up above the levy"
    m.topup_total = 0.0
    m.pool_history[3] = -1.0
    assert not public_check(m, op)[0], "A47-8 must catch a negative pool"
    m.pool_history[3] = 0.0
    m.passed_down = 1.0
    assert not public_check(m, op)[0], "A47-8 must catch a self-maintaining pool that passed down"
    try:
        HousingRules(public_build_rate=0.01, landlord="listed")
    except ValueError:
        pass
    else:
        raise AssertionError("public housing under a listed landlord must be refused")
    print("selftest ok: A47-8 catches a created unit, an over-topup, a negative pool and a "
          "pass-down; public housing under a listed landlord is refused")


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A47-1 [instrument]: rules off is A3" + (f"; {d1[:3]}" if d1 else ""))
    okr, dr = regression()
    print(f"{'PASS' if okr else 'FAIL'} A47-1b [instrument]: blocks 1-3 previews reproduce"
          + (f"; {dr[:6]}" if dr else ""))
    ok5, d5 = a47_block3.carrier_reproduction()
    print(f"{'PASS' if ok5 else 'FAIL'} A47-5 [instrument]: levy carrier is A6Model" + (f"; {d5[:3]}" if d5 else ""))
    arms, ok8 = {}, True
    for name, rules in ARMS.items():
        m, secs = a47_block3.run(rules)
        p_ok, p = public_check(m, opening_split(rules))
        ok8 &= p_ok
        unh = np.asarray(m.unhoused_history) if m.unhoused_history else np.zeros(1)
        arms[name] = {"seconds": round(secs, 2), "public_ok": p_ok, **p,
                      "unhoused_mean": round(float(unh.mean()), 2), **reading(m),
                      **a47_block3.square(m)}
    print(f"{'PASS' if ok8 else 'FAIL'} A47-8 [instrument]: public housing bookkeeping, {len(ARMS)} arms")
    keys = ["seconds", "price_ratio_end_to_start_low_tier", "owners_end", "public_built",
            "public_tenants_end", "unhoused_mean", "rent_total", "pool_end", "topup_total",
            "levied_total", "maintenance_paid", "maintenance_unfunded", "public_build_paid",
            "net_worth_top_decile_share", "net_worth_production_layer_share", "square"]
    print("\none seed (0), 300 rounds, block-3 carrier:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {
        "stage": "A47-block4",
        "criteria": [
            {"name": "A47-1", "kind": "instrument", "passed": ok1, "detail": "rules off is A3"},
            {"name": "A47-1b", "kind": "instrument", "passed": okr, "detail": "blocks 1-3 reproduce"},
            {"name": "A47-5", "kind": "instrument", "passed": ok5, "detail": "levy carrier is A6Model"},
            {"name": "A47-8", "kind": "instrument", "passed": ok8, "detail": "public housing bookkeeping"},
        ],
        "preview_seed0": arms,
        "config": {"self_maintaining": SELF,
                   "arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__} for k, v in ARMS.items()}},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and okr and ok5 and ok8) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
