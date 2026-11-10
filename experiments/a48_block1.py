"""A48 block 1: the core premium and the lock, checked; one seed previewed.

Checks, each with a planted error that must make it fail (--selftest):
  A48-1  instrument    both switches off: A47 block 5's stored grid rows reproduce field for
                       field (the bound-public, the listed and the unbound cells, five seeds)
  A48-2  instrument    with the premium on, every round the core price is the price the other
                       rules set times R0 (1+g)^t, and no unit is built in the core; the opening
                       allocation quotes the core at R0 times its initial price, every opening
                       buyer was charged its terms on that quote and paid what A3's opening rule
                       takes (the charge, or its claims where it was admitted short of it), and
                       round 0's core sales fetch the quote
  A48-3  instrument    every optional draw in the core is either a move or a lock; with tau_o = 0
                       nothing is optional; and, recomputed here from the quotes and the terms,
                       the four legs of the round trip (sell the core, buy low, sell low, buy
                       the core back) leave a mover with claims left and a locked owner short
  A48-4  known_answer  R0 = 1, g = 0: the lock rate that the terms alone produce, printed; and
                       terms 1, core 2, low 0.5, flat prices, no claims: the round trip pays

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
    return (worst <= 1e-12 and no_core_build and len(m.raw_core_price_history) == len(m.price_history)
            and opening_check(m)[0]), worst


def opening_quote(m) -> float:
    return float(m.a3.asset.initial_price[m._core_q]) * m.rules.core_R0


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-12 * max(abs(b), 1e-300)


def opening_due(m, i: int, quote: float, cash: float, n_bought: int) -> float:
    """What A3's opening allocation takes from an admitted buyer: its terms on the quote, less
    the opening discount, or the claims it has if those are short (a stretched entry). Written
    from the rule, not read back from the model. Where the node took more than one unit in the
    allocation its claims at this purchase are not on record, and the charge is the bound."""
    charge = float(m.terms[i, m._core_q]) * quote * (1.0 - m.a3.asset.opening_discount)
    if n_bought != 1:
        return charge
    return max(min(charge, cash), 1e-12)


def opening_check(m) -> tuple[bool, dict]:
    """The opening allocation and round 0's trades carry R0."""
    q, want = m._core_q, opening_quote(m)
    ok = m.opening_core_price is not None and _close(m.opening_core_price, want)
    paid_ok = all(_close(ref, want) and _close(pay, opening_due(m, i, want, cash, n))
                  for i, pay, ref, cash, n in m.opening_core_buys)
    first_sales = [tr for tr in m.trades if tr[1] == q and tr[3] == 0]
    sales_ok = m.rules.liquidation == "cost" or all(_close(tr[5], want) for tr in first_sales)
    short = sum(1 for i, pay, ref, cash, n in m.opening_core_buys
                if pay < float(m.terms[i, q]) * ref * (1.0 - m.a3.asset.opening_discount) * (1.0 - 1e-12))
    return bool(ok and paid_ok and sales_ok), {"opening_core_price": m.opening_core_price,
                                               "opening_core_buyers": len(m.opening_core_buys),
                                               "opening_core_buyers_short": short,
                                               "round0_core_sales": len(first_sales)}


def quotes_at(m, t: int) -> tuple[float, float]:
    """Core and low-tier quotes standing when round t's offers are drawn."""
    q = m._core_q
    if t > 0:
        p = np.asarray(m.price_history[t - 1], dtype=float)
        return float(p[q]), float(p[0])
    core = m.opening_core_price if m.rules.core_premium else float(m.a3.asset.initial_price[q])
    return float(core), float(m.a3.asset.initial_price[0])


def round_trip_left(m, t: int, i: int, have: float) -> float:
    """Claims left after the four legs, from the quotes standing at round t's offers and the
    node's own terms. Written out leg by leg, not through the model's gap."""
    p_core, p_low = quotes_at(m, t)
    grow = (1.0 + m.rules.core_g) ** m.a3.asset.holding_period if m.rules.core_premium else 1.0
    cash = have
    cash += p_core                                          # sell the core
    cash -= float(m.terms[i, 0]) * p_low                    # buy a low-tier unit
    cash += p_low                                           # sell it on returning, at par
    cash -= float(m.terms[i, m._core_q]) * p_core * grow    # buy the core back
    return cash


def lock_check(m) -> tuple[bool, dict]:
    ok = all(gap > have for _, _, gap, have in m.lock_events)
    ok &= m.optional_core_moved + len(m.lock_events) == m.optional_core_draws
    ok &= len(m.optional_core_passes) == m.optional_core_moved
    tol = 1e-9
    ok &= all(round_trip_left(m, t, i, have) < tol for t, i, _, have in m.lock_events)
    ok &= all(round_trip_left(m, t, i, have) > -tol for t, i, _, have in m.optional_core_passes)
    if m.rules.optional_move_rate == 0.0:
        ok &= m.optional_core_draws == 0 and not m.lock_events and m.optional_other_moved == 0
    return bool(ok), {"optional_core_draws": m.optional_core_draws, "locks": len(m.lock_events),
                      "optional_core_moved": m.optional_core_moved,
                      "optional_other_moved": m.optional_other_moved}


def open_spells(m) -> list[int]:
    """Rounds observed so far of each core holding that has not ended by the last round."""
    last = len(m.price_history) - 1
    q = m._core_q
    return [last - int(t) for (i, tier), lots in m.basis.items() if tier == q and m.units[i, tier] > 0
            for _, t, _ in lots]


def reading(m) -> dict:
    draws = m.optional_core_draws
    core_trades = [tr for tr in m.trades if tr[1] == m._core_q]
    tenure = [tr[3] - tr[2] for tr in core_trades]
    still = sorted(open_spells(m))
    buys = m.core_buys
    from a47_block1 import reading as a47_reading
    r = a47_reading(m)
    return {"lock_rate": round(len(m.lock_events) / draws, 4) if draws else None,
            "locks": len(m.lock_events), "optional_core_draws": draws,
            "core_sales": len(core_trades),
            "core_tenure_completed_mean": round(float(np.mean(tenure)), 2) if tenure else None,
            "core_spells_open": len(still),
            "core_spells_open_observed_mean": round(float(np.mean(still)), 2) if still else None,
            "core_spells_open_observed": still,
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
    # the opening quote
    m, _ = a47_block3.run(rules(R0=1.45, g=0.0, tau_o=0.02), rounds=20)
    assert opening_check(m)[0] and m.opening_core_buys, "the opening check needs opening buyers"
    m.opening_core_price = float(m.a3.asset.initial_price[m._core_q])
    assert not premium_check(m)[0], "A48-2 must catch an opening quote without R0"
    m, _ = a47_block3.run(rules(R0=1.45, g=0.0, tau_o=0.02), rounds=20)
    i, pay, ref, cash, n = m.opening_core_buys[0]
    m.opening_core_buys[0] = (i, pay, ref / 1.45, cash, n)
    assert not premium_check(m)[0], "A48-2 must catch an opening buyer charged on the bare price"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.0, tau_o=0.02), rounds=20)
    k = next(j for j, (i, pay, ref, cash, n) in enumerate(m.opening_core_buys) if m.stretched[i])
    i, pay, ref, cash, n = m.opening_core_buys[k]
    m.opening_core_buys[k] = (i, 0.0, ref, cash, n)
    assert not premium_check(m)[0], "A48-2 must catch a stretched opening buyer recorded as paying nothing"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.0, tau_o=0.02), rounds=20)
    k = next(j for j, (i, pay, ref, cash, n) in enumerate(m.opening_core_buys) if not m.stretched[i])
    i, pay, ref, cash, n = m.opening_core_buys[k]
    m.opening_core_buys[k] = (i, 0.5 * pay, ref, cash, n)
    assert not premium_check(m)[0], "A48-2 must catch a buyer with the claims to pay recorded as paying half"
    # the round trip, leg by leg
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    assert m.lock_events and m.optional_core_passes, "the planted errors need both kinds of draw"
    t, i, gap, have = m.lock_events[0]
    m.lock_events[0] = (t, i, gap + 2.0, gap + 1.0)     # recorded gap above claims, true gap below
    assert not lock_check(m)[0], "A48-3 must catch a lock whose round trip pays"
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    t, i, gap, have = m.optional_core_passes[0]
    m.optional_core_passes[0] = (t, i, gap, gap - 1.0)
    assert not lock_check(m)[0], "A48-3 must catch a mover whose round trip cannot be paid"
    # a budget that leaves out the low tier's resale locks movers the four legs clear
    m, _ = a47_block3.run(rules(R0=1.16, g=0.005, tau_o=0.02), rounds=80)
    shifted = [e for e in m.optional_core_passes if e[2] + quotes_at(m, e[0])[1] > e[3]]
    assert shifted, "some mover must be one the budget without the resale would have locked"
    m.lock_events += [(t, i, gap + quotes_at(m, t)[1], have) for t, i, gap, have in shifted]
    m.optional_core_passes = [e for e in m.optional_core_passes if e not in shifted]
    m.optional_core_moved -= len(shifted)
    assert not lock_check(m)[0], "A48-3 must catch locks produced by a budget that leaves out the resale"
    # the open spells
    m, _ = a47_block3.run(rules(R0=1.45, g=0.02, tau_o=0.03), seed=2, rounds=80)
    n_open = len(open_spells(m))
    assert n_open == int(m.units[:, m._core_q].sum()), "one open spell per core unit still held"
    # known answer: the minimal account
    assert minimal_account() == 0.0, "terms 1, core 2, low 0.5, flat prices: the round trip costs nothing"
    try:
        replace(a47_block3.CARRIER, optional_move_rate=0.02)
    except ValueError:
        pass
    else:
        raise AssertionError("optional moves without residence binding must be refused")
    print("selftest ok: A48-2 catches an off-path price, core building, an opening quote without R0, "
          "an opening buyer charged on the bare price, a stretched buyer recorded as paying nothing and "
          "a solvent one recorded as paying half; A48-3 catches a lock the owner could pay, a double "
          "count, a lock whose round trip pays, a mover whose round trip cannot be paid and the budget "
          "without the low tier's resale; open spells count the core units still held; the minimal "
          "account costs nothing; optional moves without binding are refused")


def minimal_account() -> float:
    """Terms 1, core 2, low 0.5, flat prices: sell at 2, buy at 0.5, sell at 0.5, buy at 2."""
    m, _ = a47_block3.run(rules(R0=1.0, g=0.0, tau_o=0.02), rounds=1)
    m.terms[:] = 1.0
    m.price = np.array([0.5, 1.0, 2.0])
    return float(m.lock_gap(0))


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
                      "lock_ok": l_ok, **l, **opening_check(m)[1], **reading(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A48-2 [instrument]: premium path exact, no core building, {len(PREVIEW)} arms")
    print(f"{'PASS' if ok3 else 'FAIL'} A48-3 [instrument]: lock classification, {len(PREVIEW)} arms")
    ka = arms["R0 1.00 g 0 tau_o 0.02 (known answer)"]
    print(f"---- A48-4 [known_answer]: R0 = 1, g = 0 -> lock rate {ka['lock_rate']} "
          f"({ka['locks']} of {ka['optional_core_draws']} optional core draws), the floor the terms alone give")
    mini = minimal_account()
    ok4 = mini == 0.0
    print(f"{'PASS' if ok4 else 'FAIL'} A48-4 [known_answer]: terms 1, core 2, low 0.5, flat prices, no claims "
          f"-> gap {mini}, the round trip pays")
    keys = ["seconds", "lock_rate", "locks", "optional_core_draws", "locked_production_share",
            "opening_core_price", "opening_core_buyers", "opening_core_buyers_short", "round0_core_sales",
            "core_sales", "core_tenure_completed_mean", "core_spells_open", "core_spells_open_observed_mean",
            "core_buys", "core_buys_production_share", "core_price_end", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A48-block1",
              "criteria": [
                  {"name": "A48-1", "kind": "instrument", "passed": ok1, "detail": "switches off reproduce A47"},
                  {"name": "A48-2", "kind": "instrument", "passed": ok2,
                   "detail": "premium path, no core building, opening quote carries R0, every opening payment is "
                             "what the opening rule takes"},
                  {"name": "A48-3", "kind": "instrument", "passed": ok3,
                   "detail": "lock classification; the four legs recomputed leave movers solvent and locked owners short"},
                  {"name": "A48-4", "kind": "known_answer", "passed": ok4,
                   "detail": f"minimal account gap {mini}; R0 = 1, g = 0 lock rate {ka['lock_rate']} printed"}],
              "preview_seed0": arms,
              "config": {"carrier": "A47 block 5 bound public, public and private building 0.002",
                         "preview": PREVIEW}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok2 and ok3 and ok4) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
