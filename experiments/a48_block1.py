"""A48 block 1: the core premium and the lock, checked; one seed previewed.

Checks, each with a planted error that must make it fail (--selftest):
  A48-1  instrument    both switches off: A47 block 5's stored grid rows reproduce field for
                       field (the bound-public, the listed and the unbound cells, five seeds)
  A48-2  instrument    with the premium on, every round the core price is the price the other
                       rules set times R0 (1+g)^t, and no unit is built in the core
  A48-3  instrument    every optional draw in the core is either a move or a lock; a lock only
                       where the gap exceeds the owner's claims; with tau_o = 0 nothing is optional
  A48-4  known_answer  R0 = 1, g = 0: the lock rate that the terms alone produce, printed

Carrier: A47 block 5's bound-public cell (public and private building 0.002, no cap).

Run from the repo root:
    python experiments/a48_block1.py
    python experiments/a48_block1.py --selftest
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
import a47_block5  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a48_block1.json"
BASE = a47_block5.rules_for("bound public", 0.002, 0.002, None)


def rules(R0=None, g=0.0, tau_o=0.0):
    kw = {}
    if R0 is not None:
        kw.update(core_premium=True, core_R0=R0, core_g=g)
    if tau_o:
        kw.update(optional_move_rate=tau_o)
    return replace(BASE, **kw)


def reproduction() -> tuple[bool, list[str]]:
    stored = json.loads(a47_block5.OUT.read_text(encoding="utf-8"))["grid_rows"]
    cells = {("bound public", 0.002, 0.002, None), ("bound listed 0.271", 0.0, 0.002, None),
             ("unbound", 0.002, 0.002, "wage")}
    diffs = []
    for row in stored:
        if (row["regime"], row["public"], row["private"], row["cap"]) not in cells or row["knob"]:
            continue
        now = a47_block5.one((row["regime"], row["public"], row["private"], row["cap"], row["seed"], {}))
        for k, v in row.items():
            if k != "seconds" and now.get(k) != v:
                diffs.append(f"{row['regime']} seed {row['seed']}: {k}")
    return not diffs, diffs


def premium_check(m) -> tuple[bool, float]:
    if not m.rules.core_premium:
        return True, 0.0
    q = m._core_q
    worst = 0.0
    for t, (p, raw) in enumerate(zip(m.price_history, m.raw_core_price_history)):
        want = raw * m.rules.core_R0 * (1.0 + m.rules.core_g) ** t
        worst = max(worst, abs(p[q] - want) / max(abs(want), 1e-300))
    no_core_build = m.built[q] == 0 and m.public_built[q] == 0
    return worst <= 1e-12 and no_core_build and len(m.raw_core_price_history) == len(m.price_history), worst


def lock_check(m) -> tuple[bool, dict]:
    ok = all(gap > have for _, _, gap, have in m.lock_events)
    ok &= m.optional_core_moved + len(m.lock_events) == m.optional_core_draws
    if m.rules.optional_move_rate == 0.0:
        ok &= m.optional_core_draws == 0 and not m.lock_events and m.optional_other_moved == 0
    return bool(ok), {"optional_core_draws": m.optional_core_draws, "locks": len(m.lock_events),
                      "optional_core_moved": m.optional_core_moved,
                      "optional_other_moved": m.optional_other_moved}


def reading(m) -> dict:
    draws = m.optional_core_draws
    core_trades = [tr for tr in m.trades if tr[1] == m._core_q]
    tenure = [tr[3] - tr[2] for tr in core_trades]
    buys = m.core_buys
    from a47_block1 import reading as a47_reading
    r = a47_reading(m)
    return {"lock_rate": round(len(m.lock_events) / draws, 4) if draws else None,
            "locks": len(m.lock_events), "optional_core_draws": draws,
            "core_sales": len(core_trades),
            "core_tenure_mean": round(float(np.mean(tenure)), 2) if tenure else None,
            "core_buys": len(buys),
            "core_buys_production_share": round(sum(b[2] for b in buys) / len(buys), 4) if buys else None,
            "locked_production_share": round(float(np.mean([m._is_production[e[1]] for e in m.lock_events])), 4)
            if m.lock_events else None,
            "core_price_end": round(float(m.price_history[-1][m._core_q]), 4),
            "prod_share": r["net_worth_production_layer_share"], "top_decile": r["net_worth_top_decile_share"]}


def selftest() -> None:
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    assert premium_check(m)[0] and lock_check(m)[0]
    m.price_history[10] = m.price_history[10].copy()
    m.price_history[10][m._core_q] *= 1.001
    assert not premium_check(m)[0], "A48-2 must catch a core price off the premium path"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    m.built[m._core_q] = 1.0
    assert not premium_check(m)[0], "A48-2 must catch building in the core"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    m.lock_events.append((1, 0, 0.1, 5.0))
    m.optional_core_draws += 1
    assert not lock_check(m)[0], "A48-3 must catch a lock where the owner could pay"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    m.optional_core_moved += 1
    assert not lock_check(m)[0], "A48-3 must catch a draw counted twice"
    try:
        replace(a47_block3.CARRIER, optional_move_rate=0.02)
    except ValueError:
        pass
    else:
        raise AssertionError("optional moves without residence binding must be refused")
    print("selftest ok: A48-2 catches an off-path price and core building; A48-3 catches a lock "
          "the owner could pay and a double count; optional moves without binding are refused")


PREVIEW = {
    "R0 1.00 g 0 tau_o 0.02 (known answer)": dict(R0=1.0, g=0.0, tau_o=0.02),
    "R0 1.16 g 0 tau_o 0.02": dict(R0=1.16, g=0.0, tau_o=0.02),
    "R0 1.16 g 0.005 tau_o 0.02": dict(R0=1.16, g=0.005, tau_o=0.02),
    "R0 1.45 g 0.01 tau_o 0.02": dict(R0=1.45, g=0.01, tau_o=0.02),
    "R0 1.16 g 0.005, no optional moves": dict(R0=1.16, g=0.005, tau_o=0.0),
}


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A48-1 [instrument]: switches off reproduce A47 block 5's rows"
          + (f"; {d1[:5]}" if d1 else ", field for field"))
    ok2 = ok3 = True
    arms = {}
    for name, kw in PREVIEW.items():
        m, secs = a47_block3.run(rules(**kw))
        p_ok, worst = premium_check(m)
        l_ok, l = lock_check(m)
        ok2 &= p_ok
        ok3 &= l_ok
        arms[name] = {"seconds": round(secs, 2), "premium_ok": p_ok, "premium_worst_rel": worst,
                      "lock_ok": l_ok, **l, **reading(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A48-2 [instrument]: premium path exact, no core building, {len(PREVIEW)} arms")
    print(f"{'PASS' if ok3 else 'FAIL'} A48-3 [instrument]: lock classification, {len(PREVIEW)} arms")
    ka = arms["R0 1.00 g 0 tau_o 0.02 (known answer)"]
    print(f"---- A48-4 [known_answer]: R0 = 1, g = 0 -> lock rate {ka['lock_rate']} "
          f"({ka['locks']} of {ka['optional_core_draws']} optional core draws), the floor the terms alone give")
    keys = ["seconds", "lock_rate", "locks", "optional_core_draws", "locked_production_share",
            "core_sales", "core_tenure_mean", "core_buys", "core_buys_production_share",
            "core_price_end", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A48-block1",
              "criteria": [
                  {"name": "A48-1", "kind": "instrument", "passed": ok1, "detail": "switches off reproduce A47"},
                  {"name": "A48-2", "kind": "instrument", "passed": ok2, "detail": "premium path and no core building"},
                  {"name": "A48-3", "kind": "instrument", "passed": ok3, "detail": "lock classification"},
                  {"name": "A48-4", "kind": "known_answer", "passed": None, "detail": f"lock rate {ka['lock_rate']} printed"}],
              "preview_seed0": arms,
              "config": {"carrier": "A47 block 5 bound public, public and private building 0.002",
                         "preview": PREVIEW}}
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
