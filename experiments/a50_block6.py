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
from a50_common import C, LEVIES, mean_cells, row, rules  # noqa: E402
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
    return bool(ok), {}


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
    try:
        rules("bound", "employer returned", 0.20, provident_release=5)
    except ValueError:
        pass
    else:
        raise AssertionError("a release on a returned arm must be refused")
    print("selftest ok: A50-12 catches over-release and a release when L exceeds the run; "
          "the switch is refused on a returned arm")


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
    ok12 = all(r["release_ok"] for r in rows + twins) and not d
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
                for a, b in zip(order, order[1:]):
                    diffs = [seq[b][k] - seq[a][k] for k in seq[a] if k in seq[b]]
                    sg[f"{a}->{b if b else 'never'}"] = sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in diffs})
                steps[key] = {"over_none_levy_0.20": v20, "step_signs": sg}
                print(f"  {key}")
                for L in order:
                    print(f"      L {L if L else 'never':>5}: {v20[L]}")
                print(f"      steps: {sg}")

    record = {"stage": "A50-block6",
              "criteria": [
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
    return 0 if (ok12 and ok2 and ok4) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
