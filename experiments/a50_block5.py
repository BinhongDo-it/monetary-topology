"""A50 block 5: the authority's target counts the account balances.

``provident_in_target`` lowers the baseline inflow the authority steers to by the account
balances times the carrier's inflow per unit of circulating claims at baseline (the first
round's layer-2 inflow over the initial claims). The authority then accepts circulation lower
by what the accounts hold and does not issue against it. This is "the central bank counts
the fund as money", written into the rule's own target.

Grid: the five parked arms at c 0.12, regime {unbound, bound}, levy {0.20, 0.15, 0.25}, five
seeds; "none" and "employer returned" are block 2's rows (the switch does not touch them).

Checks, each with a planted error that must make it fail (--selftest):
  A50-8b  instrument  with the switches off, block 1's reproduction (A49 rows) and block 3's
                      (block 2's c 0.12 rows) hold on the module with blocks 5 and 6 in it
  A50-11  instrument  every run withheld something; the velocity it used is the first
                      round's layer-2 inflow over the initial claims, recomputed from the history
  A50-2   instrument  the fund adds up (block 1's check)
  A50-4   instrument  locked accounts never spent (block 2's check)

Readings (A50-13, own_reading): against block 2 (target without the accounts): production
share, issuance, circulation at the end, wages paid in the last 50 rounds; block 2's seven
differences. A difference in shares is read over the pairs in which every run paid at least
half the wages due in its last 50 rounds; the pairs with a stalled run are counted and their
signs printed apart.

Run from the repo root:
    python experiments/a50_block5.py
    python experiments/a50_block5.py --selftest
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

import a50_grid  # noqa: E402
from a50_common import (ACTIVE_FLOOR, C, LEVIES, active, mean_cells, read_by_activity, row,  # noqa: E402
                        rules, unseen_rows)
from a50_grid import QTY, REGIMES, SEEDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block5.json"
PARKED = ("both parked", "employee parked", "employer parked", "employee locked", "both locked")
KEYS = QTY + ("issuance_total", "circulating_end", "wage_paid_last50", "pf_target_cut")
SHARES = ("prod_share", "top_decile")


def target_check(m) -> tuple[bool, dict]:
    h = m.history
    # the network's baseline is the first round's layer-2 inflow
    v = float(np.asarray(h.layer2_inflow)[0]) / float(m.config.initial_claims)
    ok = m.pf_target_cut > 0.0 and m.pf_velocity is not None and abs(m.pf_velocity - v) <= 1e-12 * max(1.0, v)
    return bool(ok), {"velocity": None if m.pf_velocity is None else round(m.pf_velocity, 6)}


def one(args):
    regime, arm, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    m, secs = a47_block3.run(rules(regime, arm, levy, provident_in_target=True), seed=seed)
    t_ok, t = target_check(m)
    return row(m, secs, regime=regime, arm=arm, c=C, seed=seed, levy=levy, target_ok=t_ok, **t)


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(rules("bound", "employee locked", 0.20, provident_in_target=True), rounds=80)
    assert target_check(m)[0], "the target arm must withhold with the recomputed velocity"
    m.pf_velocity *= 1.01
    assert not target_check(m)[0], "A50-11 must catch a velocity that is not the baseline's"
    m, _ = a47_block3.run(rules("bound", "employee locked", 0.20, provident_in_target=True), rounds=80)
    m.pf_target_cut = 0.0
    assert not target_check(m)[0], "A50-11 must catch a target arm that withheld nothing"
    try:
        rules("bound", "employer returned", 0.20, provident_in_target=True)
    except ValueError:
        pass
    else:
        raise AssertionError("the target switch on a returned arm must be refused")
    # the activity rule: a stalled pair is kept out of the direction, and nothing is read with no active pair
    by = read_by_activity([0.1, 0.2, -0.3], [True, True, False])
    assert by["read"] and by["active_pairs"] == 2 and by["signs_stalled"] == ["-"], \
        "a stalled pair with the other sign must not stop the active pairs from being read"
    assert not read_by_activity([0.1, 0.2], [False, False])["read"], "with every pair stalled nothing is read"
    assert not read_by_activity([0.1, -0.2, 0.3], [True, True, False])["read"], "active pairs of two signs are not read"
    assert active({"wage_paid_last50": 200.0}) and not active({"wage_paid_last50": 199.9})
    print("selftest ok: A50-11 catches a wrong velocity and a run that withheld nothing; the switch is "
          "refused on a returned arm; a stalled pair is kept out of the direction")


def main() -> int:
    import a50_block1
    import a50_block3
    workers = max(1, (os.cpu_count() or 2) - 1)
    ok_a, d_a = a50_block1.reproduction()
    ok_b, d_b = a50_block3.reproduction(workers)
    ok8 = ok_a and ok_b
    print(f"{'PASS' if ok8 else 'FAIL'} A50-8b [instrument]: switches off, A49 rows and block 2 rows reproduce"
          + (f"; {(d_a + d_b)[:6]}" if (d_a or d_b) else ""))
    jobs = [(reg, arm, lv, s) for reg in REGIMES for arm in PARKED for lv in LEVIES for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=2))
    print(f"{len(rows)} runs {time.perf_counter() - t0:.1f} s; {workers} workers")
    ok11 = all(r["target_ok"] for r in rows)
    ok2 = all(r["fund_ok"] for r in rows)
    ok4 = all(r["lock_ok"] for r in rows)
    print(f"{'PASS' if ok11 else 'FAIL'} A50-11 [instrument]: every run withheld, velocity recomputed "
          f"({sorted({r['velocity'] for r in rows})[:3]} ...)")
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up in {len(rows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A50-4 [instrument]: locked accounts never spent")

    base = unseen_rows()
    # block 2's rows have no wage column; the none and returned arms are rerun here for it
    extra = [(reg, arm, lv, s) for reg in REGIMES for arm in ("none", "employer returned")
             for lv in LEVIES for s in SEEDS]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        plain = list(ex.map(_plain, extra + [(reg, arm, lv, s) for reg in REGIMES for arm in PARKED
                                             for lv in LEVIES for s in SEEDS], chunksize=2))
    for p in plain:
        b = [x for x in base if (x["regime"], x["arm"], x["levy"], x["seed"]) == (p["regime"], p["arm"], p["levy"], p["seed"])]
        assert b and all(b[0][q] == p[q] for q in QTY), "block 2's rows must reproduce under the plain run"
    shared = [p for p in plain if p["arm"] in ("none", "employer returned")]
    target = shared + rows
    plain20 = [p for p in plain if p["levy"] == 0.20]

    print("\ncells, levy 0.20, mean over 5 seeds (block 2 -> target counts accounts): "
          + " | ".join(KEYS))
    cb = mean_cells(plain20, KEYS, ("regime", "arm"))
    ct = mean_cells([x for x in target if x["levy"] == 0.20], KEYS, ("regime", "arm"))
    summary = {"block2": {" | ".join(k): v for k, v in cb.items()}, "target": {" | ".join(k): v for k, v in ct.items()}}
    for reg in REGIMES:
        for arm in a50_grid.ARMS:
            for tag, cc in (("block2", cb), ("target", ct)):
                if tag == "target" and arm not in PARKED:
                    continue
                s = cc[(reg, arm)]
                print(f"  {tag:6s} | {reg:7s} | {arm:17s} " + " | ".join(str(s[k]) for k in KEYS))

    print("\ndifferences, prod_share per seed at levy 0.20 (sign over seeds and levies):")
    verdict = {}
    byl = {lv: a50_grid.differences([x for x in target if x["levy"] == lv], cs=(C,)) for lv in LEVIES}
    idx = {(x["regime"], x["arm"], x["levy"], x["seed"]): x for x in target}
    for name, v in byl[0.20].items():
        allsigns = set()
        for lv in LEVIES:
            allsigns |= set(a50_grid.signs(byl[lv].get(name, [])))
        read = len(allsigns) == 1 and "0" not in allsigns
        verdict[name] = {"levy_0.20": v, "signs_all_levies": sorted(allsigns), "read": read}
        reg, _, dn, q = name.split(" | ")
        if q in SHARES:
            arms = a50_grid.DIFFS[dn][0] + a50_grid.DIFFS[dn][1]
            vals = [x for lv in LEVIES for x in byl[lv].get(name, [None] * len(SEEDS))]
            act = [all(active(idx[(reg, a, lv, s)]) for a in arms) for lv in LEVIES for s in SEEDS]
            by = read_by_activity(vals, act)
            verdict[name].update(by, read_all_pairs=read)
        if name.endswith("prod_share"):
            r = verdict[name]
            print(f"  {name:58s} {v}  active {r['active_pairs']}/{r['pairs']} {r['signs_active']}"
                  f" stalled {r['signs_stalled']}  {'read' if r['read'] else 'NOT READ'}")
    stalled = sum(1 for x in rows if not active(x))
    print(f"\nruns below the activity floor ({ACTIVE_FLOOR} of wages over the last 50 rounds): {stalled} of {len(rows)}")

    record = {"stage": "A50-block5",
              "criteria": [
                  {"name": "A50-8b", "kind": "instrument", "passed": ok8,
                   "detail": "switches off: A49 and block 2 rows reproduce" + (f"; {(d_a + d_b)[:6]}" if (d_a or d_b) else "")},
                  {"name": "A50-11", "kind": "instrument", "passed": ok11,
                   "detail": "every run withheld; velocity is the first round's layer-2 inflow over initial claims"},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2, "detail": f"fund adds up in {len(rows)} runs"},
                  {"name": "A50-4", "kind": "instrument", "passed": ok4, "detail": "locked accounts never spent"}],
              "rows": rows, "plain_rows": plain, "cell_summary": summary, "differences": verdict,
              "activity": {"floor": ACTIVE_FLOOR, "stalled_runs": stalled, "runs": len(rows)},
              "config": {"provident_in_target": True, "c": C, "levies": list(LEVIES), "seeds": list(SEEDS),
                         "arms": list(PARKED), "short_stay_share": 0.1}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok8 and ok11 and ok2 and ok4) else 1


def _plain(args):
    regime, arm, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    m, secs = a47_block3.run(rules(regime, arm, levy), seed=seed)
    return row(m, secs, regime=regime, arm=arm, c=C if arm != "none" else 0.0, seed=seed, levy=levy)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
