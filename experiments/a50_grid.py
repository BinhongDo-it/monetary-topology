"""A50 block 2: the contribution taken apart, five seeds, with a locked account.

Carrier: A49's grid cells without lending (A47 block 5, levy 0.20, short stays 0.1).
Arms (employee, employer, parked, spendable): none; both parked; employee parked; employer
parked; employer returned; employee locked; both locked. "Locked" keeps the parked money in
the accounts for good: it counts in net worth and is never spent on a dwelling.

Grid: regime {unbound, bound} x (none + six arms x c {0.05, 0.12}) x five seeds.
Knob sweep (11f): levy {0.15, 0.25}, both regimes, seven arms at c 0.12, five seeds.

Checks, each with a planted error that must make it fail (--selftest):
  A50-1b  instrument  block 1's reproduction (A49 contrib-only rows, A48 rows, A49 blocks 1-3
                      previews) still holds with the fourth switch in the module
  A50-2   instrument  the fund adds up in every run (block 1's check)
  A50-4   instrument  a locked arm never spends from its accounts; they end at what was parked
  A50-5   instrument  the account's way into a purchase is the same in both regimes: every run
                      with a spendable account spent from it, unbound as well as bound, and no
                      locked run did

Differences, per seed (A50-3): transfer, parking the employee's money, parking the employer's
money, interaction, shelter alone, the housing use (employee), the housing use (both). One
whose sign moves across seeds or levy values is not read.

Run from the repo root:
    python experiments/a50_grid.py
    python experiments/a50_grid.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_grid.json"
SEEDS = tuple(range(5))
REGIMES = ("unbound", "bound")
CS = (0.05, 0.12)
QTY = ("prod_share", "top_decile", "owners_end", "renters_last50", "price_ratio")

#: arm -> (employee, employer, park, spendable); None is no contribution
ARMS = {
    "none": None,
    "both parked": (True, True, True, True),
    "employee parked": (True, False, True, True),
    "employer parked": (False, True, True, True),
    "employer returned": (False, True, False, True),
    "employee locked": (True, False, True, False),
    "both locked": (True, True, True, False),
}

#: name -> (plus arms, minus arms)
DIFFS = {
    "transfer": (["employer returned"], ["none"]),
    "park employee money": (["employee parked"], ["none"]),
    "park employer money": (["employer parked"], ["employer returned"]),
    "interaction": (["both parked", "none"], ["employee parked", "employer parked"]),
    "shelter alone": (["employee locked"], ["none"]),
    "housing use, employee": (["employee parked"], ["employee locked"]),
    "housing use, both": (["both parked"], ["both locked"]),
}


def rules_for(regime: str, arm: str, c: float, short: float = 0.1, **knob):
    from a49_block1 import BOUND, UNBOUND
    base = BOUND if regime == "bound" else UNBOUND
    kw = dict(short_stay_share=short, short_stay_rate=0.25, **knob)
    s = ARMS[arm]
    if s is not None:
        kw.update(provident_rate=c, provident_employee=s[0], provident_employer=s[1],
                  provident_park=s[2], provident_spendable=s[3])
    return replace(base, **kw)


def lock_check(m) -> tuple[bool, dict]:
    parked = m.pf_contrib_employee + (m.pf_contrib_employer if m.rules.provident_park else 0.0)
    ok = True
    if not m.rules.provident_spendable:
        kept = parked - getattr(m, "pf_released", 0.0)
        ok = m.pf_spent_from_accounts == 0.0 and abs(float(m.account.sum()) - kept) <= 1e-9 * max(1.0, parked)
    return bool(ok), {"parked": round(parked, 4)}


def one(args):
    regime, arm, c, seed, knob = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    import a50_block1
    m, secs = a47_block3.run(rules_for(regime, arm, c, **knob), seed=seed)
    f_ok, f = a50_block1.fund_check(m)
    l_ok, lk = lock_check(m)
    f = {k: v for k, v in f.items() if k not in ("account_residual", "cash_residual")}
    h = m.history
    # the carrier's authority issues gain x the shortfall in layer-2 inflow, at the top node
    mech = {"issuance_total": round(float(np.sum(h.issuance)), 4),
            "circulating_end": round(float(np.asarray(h.total_claims)[-1]), 4)}
    return {"regime": regime, "arm": arm, "c": c, "seed": seed, "knob": knob, "seconds": round(secs, 3),
            "fund_ok": f_ok, "lock_ok": l_ok, **f, **lk, **mech, **a50_block1.preview_row(m)}


def jobs_grid():
    j = []
    for reg in REGIMES:
        for s in SEEDS:
            j.append((reg, "none", 0.0, s, {}))
        for arm in ARMS:
            if arm == "none":
                continue
            for c in CS:
                j += [(reg, arm, c, s, {}) for s in SEEDS]
    return j


def jobs_knob():
    j = []
    for knob in ({"levy_rate": 0.15}, {"levy_rate": 0.25}):
        for reg in REGIMES:
            for arm in ARMS:
                c = 0.0 if arm == "none" else 0.12
                j += [(reg, arm, c, s, knob) for s in SEEDS]
    return j


def pick(rows, regime, arm, c):
    cc = 0.0 if arm == "none" else c
    return {x["seed"]: x for x in rows if x["regime"] == regime and x["arm"] == arm and x["c"] == cc}


def differences(rows, cs=CS) -> dict:
    out = {}
    for reg in REGIMES:
        for c in cs:
            for name, (plus, minus) in DIFFS.items():
                P = [pick(rows, reg, a, c) for a in plus]
                M = [pick(rows, reg, a, c) for a in minus]
                if not all(P) or not all(M):
                    continue
                for q in QTY:
                    v = []
                    for s in SEEDS:
                        xs = [p[s][q] for p in P] + [m[s][q] for m in M]
                        if any(x is None for x in xs):
                            v.append(None)
                            continue
                        v.append(round(sum(p[s][q] for p in P) - sum(m[s][q] for m in M), 4))
                    out[f"{reg} | c {c} | {name} | {q}"] = v
    return out


def signs(v):
    return sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in v if x is not None})


def entry_check(rows) -> tuple[bool, list[str]]:
    """A50-5: a spendable account pays for dwellings in both regimes, a locked one in neither."""
    d = []
    for x in rows:
        s = ARMS[x["arm"]]
        if s is None or not s[2]:
            continue                      # no contribution, or nothing parked
        spent = x["spent_from_accounts"]
        if s[3] and not spent > 0.0:
            d.append(f"{x['regime']} {x['arm']} c{x['c']} seed{x['seed']}: spendable account never spent")
        if not s[3] and spent != 0.0:
            d.append(f"{x['regime']} {x['arm']} c{x['c']} seed{x['seed']}: locked account spent {spent}")
    return not d, d


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(rules_for("bound", "employee locked", 0.12), rounds=80)
    assert lock_check(m)[0] and float(m.account.sum()) > 0, "the locked arm must hold its parked money"
    m.pf_spent_from_accounts = 0.1
    assert not lock_check(m)[0], "A50-4 must catch spending from a locked account"
    m, _ = a47_block3.run(rules_for("bound", "employee locked", 0.12), rounds=80)
    m.account[int(m._wage_receivers[0])] -= 0.01
    assert not lock_check(m)[0], "A50-4 must catch a locked account that shrank"
    m, _ = a47_block3.run(rules_for("bound", "employee parked", 0.12), rounds=80)
    assert m.pf_spent_from_accounts > 0, "under binding a spendable account must be spent"
    rows = [one(j) for j in jobs_grid() if j[0] == "unbound" and "both" in j[1] and j[2] == 0.05 and j[3] == 0]
    assert entry_check(rows)[0], "unbound, the spendable account must be spent and the locked one not"
    i = next(k for k, r in enumerate(rows) if r["arm"] == "both parked")
    assert not entry_check(rows[:i] + [dict(rows[i], spent_from_accounts=0.0)] + rows[i + 1:])[0], \
        "A50-5 must catch an unbound spendable account that was never spent"
    j = next(k for k, r in enumerate(rows) if r["arm"] == "both locked")
    assert not entry_check(rows[:j] + [dict(rows[j], spent_from_accounts=0.5)] + rows[j + 1:])[0], \
        "A50-5 must catch a locked account that was spent"
    for bad in (dict(provident_spendable=False, provident_park=False, provident_employee=False),
                dict(provident_spendable=False, commit_loan=True, loan_lender="provident")):
        try:
            from a49_block1 import BOUND
            replace(BOUND, provident_rate=0.05, **bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be refused")
    print("selftest ok: A50-4 catches spending from and shrinking of a locked account; A50-5 catches an "
          "unbound spendable account never spent and a locked one spent; the two bad switch sets are refused")


def main() -> int:
    import a50_block1
    ok1, d1 = a50_block1.reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A50-1b [instrument]: block 1's reproduction holds"
          + (f"; {d1[:6]}" if d1 else ""))
    workers = max(1, (os.cpu_count() or 2) - 1)
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs_grid(), chunksize=2))
    t1 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        krows = list(ex.map(one, jobs_knob(), chunksize=2))
    t2 = time.perf_counter()
    print(f"grid {len(rows)} runs {t1 - t0:.1f} s; knobs {len(krows)} runs {t2 - t1:.1f} s; {workers} workers")

    ok2 = all(r["fund_ok"] for r in rows + krows)
    ok4 = all(r["lock_ok"] for r in rows + krows)
    ok5, d5 = entry_check(rows + krows)
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up in {len(rows) + len(krows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A50-4 [instrument]: locked accounts never spent, end at what was parked")
    print(f"{'PASS' if ok5 else 'FAIL'} A50-5 [instrument]: spendable accounts spent in both regimes, locked ones never"
          + (f"; {d5[:6]}" if d5 else ""))

    print("\ncells, mean over 5 seeds: " + " | ".join(QTY) + " | parked | accounts end | spent from accounts | issuance | circulating end")
    summary = {}
    for reg in REGIMES:
        for arm in ARMS:
            for c in ((0.0,) if arm == "none" else CS):
                rs = list(pick(rows, reg, arm, c).values())
                s = {k: round(float(np.mean([x[k] for x in rs if x[k] is not None])), 4)
                     for k in QTY + ("parked", "accounts_end", "spent_from_accounts", "issuance_total",
                                     "circulating_end")}
                name = f"{reg} | {arm} | c {c}"
                summary[name] = s
                print(f"  {name:36s} " + " | ".join(str(s[k]) for k in QTY + ("parked", "accounts_end",
                                                                               "spent_from_accounts", "issuance_total",
                                                                               "circulating_end")))

    diffs = differences(rows)
    kd = {json.dumps(k): differences([x for x in krows if x["knob"] == k], cs=(0.12,))
          for k in ({"levy_rate": 0.15}, {"levy_rate": 0.25})}
    print("\ndifferences, per seed (sign over seeds and levy values):")
    verdict = {}
    for name, v in diffs.items():
        allsigns = set(signs(v))
        byk = {}
        for k, dd in kd.items():
            if name in dd:
                byk[k] = signs(dd[name])
                allsigns |= set(byk[k])
        read = len(allsigns) == 1 and "0" not in allsigns
        verdict[name] = {"base": v, "knob_signs": byk, "read": read}
        if name.split(" | ")[-1] in ("prod_share", "owners_end", "price_ratio"):
            print(f"  {name:62s} {v}  {'read ' + next(iter(allsigns)) if read else 'NOT READ ' + str(sorted(allsigns))}")

    record = {"stage": "A50-grid",
              "criteria": [
                  {"name": "A50-1b", "kind": "instrument", "passed": ok1, "detail": "block 1 reproduction"
                   + (f"; {d1[:6]}" if d1 else "")},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2,
                   "detail": f"fund adds up in {len(rows) + len(krows)} runs"},
                  {"name": "A50-4", "kind": "instrument", "passed": ok4,
                   "detail": "locked accounts never spent and end at what was parked"},
                  {"name": "A50-5", "kind": "instrument", "passed": ok5,
                   "detail": "spendable accounts spent in both regimes, locked ones never"
                   + (f"; {d5[:6]}" if d5 else "")}],
              "grid_rows": rows, "knob_rows": krows, "cell_summary": summary, "differences": verdict,
              "config": {"seeds": list(SEEDS), "c": list(CS), "short_stay_share": 0.1, "short_stay_rate": 0.25,
                         "arms": {k: list(v) if v else None for k, v in ARMS.items()},
                         "knobs": [{"levy_rate": 0.15}, {"levy_rate": 0.25}]}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok2 and ok4 and ok5) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
