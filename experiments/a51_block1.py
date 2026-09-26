"""A51 block 1: location demand, and who lives in the core; checks and a one-seed preview.

Carrier: A48's bound cells (A47 block 5, levy 0.20, cost floor, tenancy by unit, residence
binding, public landlord keeping itself with public and private building 0.002, or a listed
landlord with dividend exit 0.271 and private building 0.002), core premium R0 1.16, optional
moves 0.02. The core is moved off the top tier: the low tier is split into a plain and a core
tier of one size and price (units 60 -> 60(1 - share) and 60 share, price 0.5, terms 1.00), so
the core differs from the low tier by location alone. Location demand: a renter with a wage
pays s times it in commuting if it lives outside the core (s from US DOT's 50 % of the wage
per hour of travel and a 13 to 40 minute one-way gap between inner and outer suburbs: 0.027 to
0.083).

Checks, each with a planted error that must make it fail (--selftest):
  A51-1  instrument   every A51 switch off: A50 block 1's reproduction holds (A49's rows, A48's
                      rows, A49 blocks 1-3's previews)
  A51-2  instrument   on the split carrier the core is never built, its price is the plain price
                      times R0 (1 + g)^t, no renter holds two units, and every choice is the
                      cheapest rent-plus-commute among the units the renter can pay
  A51-3  known_answer s near zero and g zero, market rent (listed landlord): the located matching
                      gives the old matching's run, field for field, since the core's rent is then
                      strictly above the plain tier's and both pick the lowest tier first. Not
                      under a cost-renting public landlord: there the core and the plain tier rent
                      at one cost price, and any commuting cost, however small, decides for the core

Run from the repo root:
    python experiments/a51_block1.py
    python experiments/a51_block1.py --selftest
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

import a47_block3  # noqa: E402
import a48_grid  # noqa: E402
from a47_block1 import reading  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a51_block1.json"
R0, TAU_O = 1.16, 0.02
S_LOW, S_HIGH = 0.027, 0.083


def split_asset(share: float) -> dict:
    core = int(round(60 * share))
    return dict(a47_block3.CARRIER_ASSET, tiers=4, units=(60 - core, core, 30, 10),
                initial_price=(0.5, 0.5, 1.0, 2.0), base_terms=(1.00, 1.00, 1.05, 1.15))


def rules_for(landlord: str, g: float, s: float, **kw):
    base = a48_grid.rules_for(landlord, R0, g, TAU_O)
    return replace(base, core_tier=1, location_s=s, **kw)


def run(landlord, g, s, share, seed=0, rounds=300):
    return a47_block3.run(rules_for(landlord, g, s), seed=seed, rounds=rounds, asset=split_asset(share))


# -- checks ------------------------------------------------------------------------------

def structure_check(m) -> tuple[bool, list[str]]:
    bad = []
    q = m._core_q
    if float(np.asarray(m.built)[q]) != 0.0:
        bad.append("the core was built")
    raw = np.asarray(m.raw_core_price_history, dtype=float)
    ph = np.asarray(m.price_history, dtype=float)[:, q]
    fac = np.array([m.rules.core_R0 * (1.0 + m.rules.core_g) ** t for t in range(len(raw))])
    if raw.size and not np.allclose(ph[-raw.size:], raw * fac, rtol=1e-12, atol=0.0):
        bad.append("core price is not the plain price times the premium")
    per_round: dict[int, list[int]] = {}
    for t, i, _, c, best in m.location_choices:
        per_round.setdefault(t, []).append(i)
        if c > best * (1 + 1e-12) + 1e-15:
            bad.append(f"round {t}: node {i} did not take its cheapest option")
            break
    if any(len(v) != len(set(v)) for v in per_round.values()):
        bad.append("a renter holds two units in one round")
    return not bad, bad


def known_answer(landlord: str) -> tuple[bool, list[str]]:
    return known_answer_arm(replace(a48_grid.rules_for(landlord, R0, 0.0, TAU_O), core_tier=1),
                            rules_for(landlord, 0.0, 1e-12))


def known_answer_arm(old_rules, new_rules) -> tuple[bool, list[str]]:
    from a47_block1 import same
    a, _ = a47_block3.run(old_rules, seed=0, rounds=120, asset=split_asset(0.1))
    b, _ = a47_block3.run(new_rules, seed=0, rounds=120, asset=split_asset(0.1))
    d = []
    for f in ("holdings", "units", "landlord_units", "price_history", "tenancy", "rent_history",
              "housed_history", "lock_events"):
        if not same(getattr(a, f), getattr(b, f)):
            d.append(f)
    return not d, d


def preview_row(m) -> dict:
    loc = np.asarray(m.location_history[-50:], dtype=float)
    ten = np.asarray(m.match_state["is_renter"])
    rec = np.zeros(m._n, dtype=bool)
    rec[np.asarray(m._wage_receivers, dtype=int)] = True
    renters_emp = float((ten & rec).sum()) / max(1.0, float(ten.sum()))
    q = m._core_q
    slots = m.match_state["slots_by_tier"][q]
    r = reading(m)
    return {
        "core_tenants_last50": round(float(loc[:, 0].mean()), 2) if loc.size else None,
        "core_rental_slots_end": int(slots),
        "employed_share_of_core_tenants": round(float(loc[:, 1].sum() / loc[:, 0].sum()), 4)
        if loc.size and loc[:, 0].sum() else None,
        "employed_share_of_renters_end": round(renters_emp, 4),
        "location_rent_left_with_tenants_per_round": round(float(loc[:, 2].mean()), 4) if loc.size else None,
        "location_rent_collected_per_round": round(float(loc[:, 3].mean()), 4) if loc.size else None,
        "core_households_end": round(float(m.core_household_history[-1]), 4),
        "locks": len(m.lock_events),
        "prod_share": r["net_worth_production_layer_share"],
        "top_decile": r["net_worth_top_decile_share"],
    }


def selftest() -> None:
    m, _ = run("public", 0.005, S_HIGH, 0.1, rounds=80)
    assert structure_check(m)[0] and m.location_choices, "the arm must pass before the plants"
    m.location_choices[5] = m.location_choices[5][:3] + (m.location_choices[5][4] + 1.0, m.location_choices[5][4])
    assert not structure_check(m)[0], "A51-2 must catch a renter that did not take its cheapest option"
    m, _ = run("public", 0.005, S_HIGH, 0.1, rounds=80)
    m.built = np.asarray(m.built, dtype=float).copy()
    m.built[m._core_q] = 1.0
    assert not structure_check(m)[0], "A51-2 must catch a core that was built"
    m, _ = run("public", 0.005, S_HIGH, 0.1, rounds=80)
    t, i = m.location_choices[0][:2]
    m.location_choices.append((t, i, 0, 0.0, 0.0))
    assert not structure_check(m)[0], "A51-2 must catch a renter placed twice in a round"
    for bad in (dict(location_s=0.05, tenant_tier=False), dict(location_s=-0.1),
                dict(location_s=0.05, commit_loan=True)):
        try:
            replace(a48_grid.rules_for("public", R0, 0.0, TAU_O), **bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be refused")
    ok, d = known_answer_arm(replace(a48_grid.rules_for("public", R0, 0.0, TAU_O), core_tier=1),
                             rules_for("public", 0.0, 1e-12))
    assert not ok, "A51-3's comparison must fail where the core rents at the plain tier's cost"
    print("selftest ok: A51-3 fails on a cost-renting landlord; A51-2 catches a non-cheapest choice, a built core and a double placement; "
          "three bad switch sets are refused")


def main() -> int:
    import a50_block1
    ok1, d1 = a50_block1.reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A51-1 [instrument]: switches off, A49/A48 rows and previews reproduce"
          + (f"; {d1[:6]}" if d1 else ""))
    ok3 = True
    d3 = {}
    for ll in ("listed 0.271",):
        ok, d = known_answer(ll)
        ok3 &= ok
        d3[ll] = d
    print(f"{'PASS' if ok3 else 'FAIL'} A51-3 [known_answer]: s near zero, g zero, market rent equals the old matching"
          + (f"; {d3}" if not ok3 else ""))
    ok2, arms = True, {}
    for ll in ("public", "listed 0.271"):
        for g in (0.0, 0.005):
            for share in (0.1, 0.3):
                for s in (S_LOW, S_HIGH):
                    m, secs = run(ll, g, s, share)
                    c_ok, c = structure_check(m)
                    ok2 &= c_ok
                    arms[f"{ll} | g {g} | core share {share} | s {s}"] = {"seconds": round(secs, 2),
                                                                         "structure_ok": c_ok, **preview_row(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A51-2 [instrument]: core never built, priced by the premium, "
          f"one unit per renter, every choice the cheapest affordable ({len(arms)} arms)")
    keys = ["core_tenants_last50", "core_rental_slots_end", "employed_share_of_core_tenants",
            "employed_share_of_renters_end", "location_rent_left_with_tenants_per_round",
            "location_rent_collected_per_round", "core_households_end", "locks", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds, R0 1.16, tau_o 0.02:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A51-block1",
              "criteria": [
                  {"name": "A51-1", "kind": "instrument", "passed": ok1,
                   "detail": "switches off: A49/A48 rows and previews reproduce" + (f"; {d1[:6]}" if d1 else "")},
                  {"name": "A51-2", "kind": "instrument", "passed": ok2,
                   "detail": f"core never built, priced by the premium, one unit per renter, cheapest affordable choice, {len(arms)} arms"},
                  {"name": "A51-3", "kind": "known_answer", "passed": ok3,
                   "detail": "s near zero, g zero, market rent (listed): the old matching field for field" + (f"; {d3}" if not ok3 else "")}],
              "preview_seed0": arms,
              "config": {"R0": R0, "tau_o": TAU_O, "s": [S_LOW, S_HIGH], "core_share": [0.1, 0.3], "g": [0.0, 0.005],
                         "asset": split_asset(0.1) | {"units_at_share_0.3": list(split_asset(0.3)["units"])}}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok2 and ok3) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
