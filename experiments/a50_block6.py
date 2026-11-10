"""A50 block 6: how long the money stays parked.

``provident_release`` ``L`` pays each round's parked money back to its owner's holdings
``L`` rounds later, as far as the account still holds it. A round carries a trend and not a
calendar span (A6), so ``L`` reads as short against long.

Grid: L {1, 5, 25, 100} x authority {refills (block 2), target counts accounts (block 5)} x
arms {employee locked, both locked, both parked} x regime {unbound, bound} x levy {0.20,
0.15, 0.25} x five seeds. Never releasing is block 2's and block 5's rows.

Checks, each with a planted error that must make it fail (--selftest):
  A50-12  instrument  nothing released beyond what was parked; L = 300 releases nothing in
                      300 rounds and equals never releasing field for field (an
                      implementation check, D35)
  A50-2   instrument  the fund adds up, released money included (block 1's check)
  A50-4   instrument  a locked account is never spent and holds what was parked less what
                      went back (block 2's check)

Readings (A50-14, own_reading): production share, circulation at the end and wages in the
last 50 rounds against L, both authorities side by side.

Run from the repo root:
    python experiments/a50_block6.py
    python experiments/a50_block6.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a50_block5  # noqa: E402
from a50_common import C, LEVIES, active, mean_cells, read_by_activity, row, rules  # noqa: E402
from a50_grid import QTY, REGIMES, SEEDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block6.json"
LS = (1, 5, 25, 100)
ARMS = ("employee locked", "both locked", "both parked")
AUTH = {"refills": {}, "target": {"provident_in_target": True}}
KEYS = ("prod_share", "top_decile", "owners_end", "circulating_end", "wage_paid_last50", "issuance_total",
        "pf_released", "parked")


def release_check(m) -> tuple[bool, dict]:
    parked = m.pf_contrib_employee + (m.pf_contrib_employer if m.rules.provident_park else 0.0)
    ok = 0.0 <= m.pf_released <= parked * (1 + 1e-12)
    if m.rules.provident_release >= len(m.history.issuance):
        ok &= m.pf_released == 0.0
    # what is still scheduled for release, round by round, is exactly what the accounts hold
    if m.rules.provident_release and m._pf_vintages:
        left = np.sum(m._pf_vintages, axis=0)
        ok &= bool(np.all(np.abs(left - m.account) <= 1e-9 * max(1.0, parked)))
    return bool(ok), {}


def vintage_probe(cls=None) -> bool:
    """Money parked, spent on a dwelling, then parked again: the first round's release date
    must pay back nothing, since nothing of that round is left."""
    from a47_block1 import a3_config
    import a47_block3
    from monetary_topology.housing_rules import A47Config, A47Model
    asset = dict(a47_block3.CARRIER_ASSET, max_units=1)
    m = (cls or A47Model)(A47Config(a3=a3_config(0, 1, **asset),
                                    rules=rules("bound", "both parked", 0.20, provident_release=2)))
    b = int(np.flatnonzero(m.units.sum(axis=1) == 0)[0])
    one_unit = np.zeros(m._n)
    one_unit[b] = 1.0
    m.account[:] = 0.0
    m.pf_cash = 0.0
    m.account[b] += 1.0
    m.pf_cash += 1.0
    m._release(one_unit.copy())           # round 0: parked
    m.holdings[b] = 0.0
    m._spend(b, 1.0)                      # ... and spent on a dwelling
    m._release(np.zeros(m._n))            # round 1
    m.account[b] += 1.0
    m.pf_cash += 1.0
    m._release(one_unit.copy())           # round 2: new money parked as round 0 falls due
    return m.pf_released == 0.0 and abs(float(m.account[b]) - 1.0) < 1e-12


def one(args):
    regime, arm, auth, L, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    extra = dict(AUTH[auth])
    if L:
        extra["provident_release"] = L
    m, secs = a47_block3.run(rules(regime, arm, levy, **extra), seed=seed)
    r_ok, _ = release_check(m)
    return row(m, secs, regime=regime, arm=arm, c=C, auth=auth, L=L, levy=levy, seed=seed, release_ok=r_ok)


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(rules("bound", "employee locked", 0.20, provident_release=5), rounds=80)
    assert release_check(m)[0] and m.pf_released > 0.0, "a release arm must pay back within what was parked"
    m.pf_released = 10 * (m.pf_contrib_employee + 1.0)
    assert not release_check(m)[0], "A50-12 must catch a release beyond what was parked"
    m, _ = a47_block3.run(rules("bound", "employee locked", 0.20, provident_release=300), rounds=80)
    assert release_check(m)[0] and m.pf_released == 0.0, "L beyond the run must release nothing"
    m.pf_released = 0.5
    assert not release_check(m)[0], "A50-12 must catch a release when L exceeds the run"
    m, _ = a47_block3.run(rules("bound", "both parked", 0.20, provident_release=25), rounds=80)
    assert release_check(m)[0] and m.pf_spent_from_accounts > 0.0, "a spendable release arm must spend and balance"
    m._pf_vintages[0] = m._pf_vintages[0] + 0.01
    assert not release_check(m)[0], "A50-12 must catch a release schedule that is not what the accounts hold"
    from monetary_topology.housing_rules import A47Model

    class SpendsWithoutVintage(A47Model):     # the rule before the 2026-10-04 fix
        def _use_vintages(self, i, amount):
            return

    assert vintage_probe(), "money spent before a later deposit must not be released from that deposit"
    assert not vintage_probe(SpendsWithoutVintage), "A50-12 must catch an early release of later money"
    assert pairing({"a": {"1->5": {"pairs": 15}}})[0] and not pairing({"a": {"1->5": {"pairs": 5}}})[0], \
        "A50-12b must catch a step paired at one levy only"
    try:
        rules("bound", "employer returned", 0.20, provident_release=5)
    except ValueError:
        pass
    else:
        raise AssertionError("a release on a returned arm must be refused")
    print("selftest ok: A50-12 catches over-release, a release when L exceeds the run, a schedule that is "
          "not the accounts and an early release of later money; A50-12b catches a step paired at one "
          "levy; the switch is refused on a returned arm")


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    b5 = json.loads(a50_block5.OUT.read_text(encoding="utf-8"))
    never = [dict(x, auth="refills", L=0) for x in b5["plain_rows"]] + \
            [dict(x, auth="target", L=0) for x in b5["rows"]]
    # L = 300 against never, both authorities, seed by seed at levy 0.20
    twin_jobs = [(reg, arm, auth, 300, 0.20, s) for reg in REGIMES for arm in ARMS for auth in AUTH for s in SEEDS]
    jobs = [(reg, arm, auth, L, lv, s) for reg in REGIMES for arm in ARMS for auth in AUTH for L in LS
            for lv in LEVIES for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        twins = list(ex.map(one, twin_jobs, chunksize=2))
        rows = list(ex.map(one, jobs, chunksize=2))
    print(f"{len(rows)} runs + {len(twins)} twins {time.perf_counter() - t0:.1f} s; {workers} workers")
    d = []
    for t in twins:
        n = [x for x in never if (x["regime"], x["arm"], x["auth"], x["levy"], x["seed"]) ==
             (t["regime"], t["arm"], t["auth"], 0.20, t["seed"])]
        if not n:
            d.append(f"no never-row for {t['regime']} {t['arm']} {t['auth']} seed {t['seed']}")
            continue
        d += [f"{t['regime']} {t['arm']} {t['auth']} seed{t['seed']}: {k}"
              for k in QTY + ("issuance_total", "circulating_end", "wage_paid_last50", "parked")
              if n[0][k] != t[k]]
    ok12 = all(r["release_ok"] for r in rows + twins) and not d and vintage_probe()
    ok2 = all(r["fund_ok"] for r in rows)
    ok4 = all(r["lock_ok"] for r in rows)
    print(f"{'PASS' if ok12 else 'FAIL'} A50-12 [instrument]: release within parked; L = 300 equals never"
          + (f"; {d[:6]}" if d else ""))
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up in {len(rows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A50-4 [instrument]: locked accounts never spent")

    allrows = rows + [x for x in never if x["arm"] in ARMS or x["arm"] == "none"]
    cells = mean_cells([x for x in allrows if x["levy"] == 0.20], KEYS, ("auth", "regime", "arm", "L"))
    print("\ncells, levy 0.20, mean over 5 seeds (L 0 = never): " + " | ".join(KEYS))
    summary = {}
    for auth in AUTH:
        for reg in REGIMES:
            for arm in ARMS:
                for L in (1, 5, 25, 100, 0):
                    s = cells[(auth, reg, arm, L)]
                    summary[f"{auth} | {reg} | {arm} | L {L}"] = s
                    print(f"  {auth:7s} | {reg:7s} | {arm:15s} | L {L:3d}  " + " | ".join(str(s[k]) for k in KEYS))
            nn = cells.get((auth, reg, "none", 0))
            if nn:
                print(f"  {auth:7s} | {reg:7s} | none            |         " + " | ".join(str(nn[k]) for k in KEYS))

    # per seed: prod share minus the no-fund arm, against L, and the sign of each step in L
    print("\nprod share over the no-fund arm, per seed, levy 0.20; then the sign of each step in L over seeds and levies:")
    steps = {}
    base = {(x["regime"], x["levy"], x["seed"]): x for x in never if x["arm"] == "none"}
    run = {(r["auth"], r["regime"], r["arm"], r["L"], r["levy"], r["seed"]): r for r in allrows}
    for auth in AUTH:
        for reg in REGIMES:
            for arm in ARMS:
                seq = {}
                for L in (1, 5, 25, 100, 0):
                    for lv in LEVIES:
                        for s in SEEDS:
                            x = [r for r in allrows if (r["auth"], r["regime"], r["arm"], r["L"], r["levy"], r["seed"])
                                 == (auth, reg, arm, L, lv, s)]
                            if x:
                                seq.setdefault(L, {})[(lv, s)] = x[0]["prod_share"] - base[(reg, lv, s)]["prod_share"]
                key = f"{auth} | {reg} | {arm}"
                v20 = {L: [round(seq[L][(0.20, s)], 4) for s in SEEDS] for L in seq}
                sg = {}
                order = (1, 5, 25, 100, 0)
                by_step = {}
                for a, b in zip(order, order[1:]):
                    ks = [k for k in seq[a] if k in seq[b]]
                    diffs = [seq[b][k] - seq[a][k] for k in ks]
                    name = f"{a}->{b if b else 'never'}"
                    sg[name] = sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in diffs})
                    act = [active(run[(auth, reg, arm, a) + k]) and active(run[(auth, reg, arm, b) + k]) for k in ks]
                    by_step[name] = read_by_activity(diffs, act)
                steps[key] = {"over_none_levy_0.20": v20, "step_signs": sg, "steps_by_activity": by_step}
                print(f"  {key}")
                for L in order:
                    print(f"      L {L if L else 'never':>5}: {v20[L]}")
                print(f"      steps: {sg}")
                print("      active pairs: " + ", ".join(
                    f"{n} {v['active_pairs']}/{v['pairs']} {v['signs_active']}" for n, v in by_step.items()))

    okp, dp = pairing({k: v["steps_by_activity"] for k, v in steps.items()})
    print(f"\n{'PASS' if okp else 'FAIL'} A50-12b [instrument]: every step in L is paired at all three levies"
          + (f"; {dp[:6]}" if dp else f", {len(LEVIES) * len(SEEDS)} pairs each"))
    record = {"stage": "A50-block6",
              "criteria": [
                  {"name": "A50-12b", "kind": "instrument", "passed": okp,
                   "detail": "every step in L, never included, is paired at all three levies and five seeds"},
                  {"name": "A50-12", "kind": "instrument", "passed": ok12,
                   "detail": "release within parked; L = 300 equals never field for field" + (f"; {d[:6]}" if d else "")},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2, "detail": f"fund adds up in {len(rows)} runs"},
                  {"name": "A50-4", "kind": "instrument", "passed": ok4, "detail": "locked accounts never spent"}],
              "rows": rows, "twin_rows": twins, "cell_summary": summary, "steps": steps,
              "config": {"L": list(LS), "authorities": {k: v for k, v in AUTH.items()}, "arms": list(ARMS), "c": C,
                         "levies": list(LEVIES), "seeds": list(SEEDS), "short_stay_share": 0.1}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok12 and ok2 and ok4 and okp) else 1


def pairing(by) -> tuple[bool, list[str]]:
    want = len(LEVIES) * len(SEEDS)
    d = [f"{k} {n}: {v['pairs']} pairs" for k, st in by.items() for n, v in st.items() if v["pairs"] != want]
    return not d, d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
