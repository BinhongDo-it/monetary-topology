"""A50 block 3: is the authority's refill what makes a locked account pay?

The carrier's authority is MonetaryAuthority(rule="endogenous", gain=1.0): it issues gain x
the shortfall in layer-2 inflow against baseline, at the top node. A fund account is money
that has left cross-layer circulation, outside that instrument's view. Block 2 printed the
refill matching what was locked one for one under binding. Here the same seven arms run
with the refill halved (gain 0.5) and with no issuance (rule "none").

Grid: authority {gain 0.5, none} x regime {unbound, bound} x seven arms at c 0.12 x levy
{0.20, 0.15, 0.25} x five seeds.

Checks, each with a planted error that must make it fail (--selftest):
  A50-6   instrument  this block's run path with the authority written out as endogenous,
                      gain 1.0 reproduces block 2's c 0.12 rows field for field
  A50-2   instrument  the fund adds up in every run (block 1's check)
  A50-4   instrument  locked accounts never spent, end at what was parked (block 2's check)

Readings (A50-7, own_reading): block 2's seven differences under each authority, and the
refill ratio (issuance in a locked arm less issuance with no fund) / money locked.

Run from the repo root:
    python experiments/a50_block3.py
    python experiments/a50_block3.py --selftest
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
from a50_grid import ARMS, QTY, REGIMES, SEEDS, rules_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block3.json"
C = 0.12
AUTHORITIES = {"gain 0.5": ("endogenous", 0.5), "none": ("none", 1.0)}
LEVIES = (0.20, 0.15, 0.25)


def run(rules, seed: int, authority: tuple[str, float], rounds: int = 300):
    """a47_block3.run with the network's authority written out."""
    from a47_block3 import CARRIER_ASSET
    from monetary_topology.asset import A3Config, AssetSpec
    from monetary_topology.config import MonetaryAuthority
    from monetary_topology.housing_rules import A47Config, A47Model
    from monetary_topology.network import NetworkConfig, NetworkSpec
    asset = dict(CARRIER_ASSET)
    if rules.residence_bound:
        asset["max_units"] = 1
    net = NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds,
                        authority=MonetaryAuthority(rule=authority[0], gain=authority[1]))
    t0 = time.perf_counter()
    m = A47Model(A47Config(a3=A3Config(asset=AssetSpec(**asset), network=net), rules=rules))
    m.history = m.run()
    return m, time.perf_counter() - t0


def one(args):
    regime, arm, auth, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a50_block1
    c = 0.0 if arm == "none" else C
    knob = {} if levy == 0.20 else {"levy_rate": levy}
    m, secs = run(rules_for(regime, arm, c, **knob), seed, AUTHORITIES.get(auth, ("endogenous", 1.0)))
    f_ok, f = a50_block1.fund_check(m)
    l_ok, lk = a50_grid.lock_check(m)
    f = {k: v for k, v in f.items() if k not in ("account_residual", "cash_residual")}
    h = m.history
    return {"regime": regime, "arm": arm, "c": c, "seed": seed, "authority": auth, "levy": levy,
            "knob": knob, "seconds": round(secs, 3), "fund_ok": f_ok, "lock_ok": l_ok, **f, **lk,
            "issuance_total": round(float(np.sum(h.issuance)), 4),
            "circulating_end": round(float(np.asarray(h.total_claims)[-1]), 4),
            **a50_block1.preview_row(m)}


def reproduction(workers: int) -> tuple[bool, list[str]]:
    stored = json.loads(a50_grid.OUT.read_text(encoding="utf-8"))["grid_rows"]
    want = [x for x in stored if x["c"] in (0.0, C)]
    jobs = [(x["regime"], x["arm"], "gain 1.0", 0.20, x["seed"]) for x in want]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        now = list(ex.map(one, jobs, chunksize=2))
    skip = {"seconds", "authority", "levy"}
    d = []
    for a, b in zip(want, now):
        d += [f"{a['regime']} {a['arm']} seed{a['seed']}: {k}" for k in a if k not in skip and a[k] != b.get(k)]
    return (not d) and len(want) == 70, d if len(want) == 70 else d + [f"{len(want)} stored rows, not 70"]


def refill(rows, regime, auth, levy):
    """Per seed: (issuance in a locked arm - issuance with no fund) / money locked."""
    out = {}
    for arm in ("employee locked", "both locked"):
        base = {x["seed"]: x for x in rows if (x["regime"], x["arm"], x["authority"], x["levy"]) ==
                (regime, "none", auth, levy)}
        lk = {x["seed"]: x for x in rows if (x["regime"], x["arm"], x["authority"], x["levy"]) ==
              (regime, arm, auth, levy)}
        out[arm] = [round((lk[s]["issuance_total"] - base[s]["issuance_total"]) / lk[s]["parked"], 4)
                    if lk[s]["parked"] else None for s in SEEDS]
    return out


def selftest() -> None:
    m, _ = run(rules_for("bound", "employee locked", C), 0, AUTHORITIES["none"], rounds=80)
    assert float(np.sum(m.history.issuance)) == 0.0, "rule none must issue nothing"
    m2, _ = run(rules_for("bound", "employee locked", C), 0, AUTHORITIES["gain 0.5"], rounds=80)
    assert float(np.sum(m2.history.issuance)) > 0.0, "gain 0.5 must issue"
    rows = [one(("bound", "none", "gain 1.0", 0.20, s)) for s in (0,)]
    stored = [x for x in json.loads(a50_grid.OUT.read_text(encoding="utf-8"))["grid_rows"]
              if x["regime"] == "bound" and x["arm"] == "none" and x["seed"] == 0]
    assert all(stored[0][k] == rows[0][k] for k in stored[0] if k not in ("seconds",)), \
        "the written-out authority must reproduce block 2's row"
    bad = dict(rows[0], prod_share=rows[0]["prod_share"] + 0.001)
    assert any(stored[0][k] != bad[k] for k in stored[0] if k != "seconds"), \
        "A50-6's comparison must catch a changed field"
    print("selftest ok: rule none issues nothing, gain 0.5 issues, the written-out authority reproduces "
          "block 2 and the comparison catches a changed field")


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    ok6, d6 = reproduction(workers)
    print(f"{'PASS' if ok6 else 'FAIL'} A50-6 [instrument]: block 2's c 0.12 rows reproduce with the authority "
          f"written out" + (f"; {d6[:6]}" if d6 else ""))
    jobs = [(reg, arm, auth, levy, s) for auth in AUTHORITIES for reg in REGIMES for arm in ARMS
            for levy in LEVIES for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=2))
    print(f"{len(rows)} runs {time.perf_counter() - t0:.1f} s; {workers} workers")
    ok2 = all(r["fund_ok"] for r in rows)
    ok4 = all(r["lock_ok"] for r in rows)
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up in {len(rows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A50-4 [instrument]: locked accounts never spent")

    stored = [dict(x, authority="gain 1.0", levy=0.20) for x in
              json.loads(a50_grid.OUT.read_text(encoding="utf-8"))["grid_rows"] if x["c"] in (0.0, C)]
    stored += [dict(x, authority="gain 1.0", levy=x["knob"]["levy_rate"]) for x in
               json.loads(a50_grid.OUT.read_text(encoding="utf-8"))["knob_rows"]]
    allrows = stored + rows

    print("\ncells, levy 0.20, mean over 5 seeds: " + " | ".join(QTY) + " | issuance | circulating end")
    summary = {}
    for auth in ("gain 1.0",) + tuple(AUTHORITIES):
        for reg in REGIMES:
            for arm in ARMS:
                rs = [x for x in allrows if (x["authority"], x["regime"], x["arm"], x["levy"]) == (auth, reg, arm, 0.20)]
                s = {k: round(float(np.mean([x[k] for x in rs if x[k] is not None])), 4)
                     for k in QTY + ("issuance_total", "circulating_end", "spent_from_accounts")}
                name = f"{auth} | {reg} | {arm}"
                summary[name] = s
                print(f"  {name:40s} " + " | ".join(str(s[k]) for k in QTY + ("issuance_total", "circulating_end")))

    print("\nrefill ratio per seed, levy 0.20:")
    ratios = {}
    for auth in ("gain 1.0",) + tuple(AUTHORITIES):
        for reg in REGIMES:
            ratios[f"{auth} | {reg}"] = refill(allrows, reg, auth, 0.20)
            print(f"  {auth} | {reg}: {ratios[f'{auth} | {reg}']}")

    print("\ndifferences, prod_share and owners per seed at levy 0.20 (sign over seeds and levies):")
    verdict = {}
    for auth in ("gain 1.0",) + tuple(AUTHORITIES):
        byl = {lv: a50_grid.differences([dict(x, c=C if x["arm"] != "none" else 0.0) for x in allrows
                                         if x["authority"] == auth and x["levy"] == lv], cs=(C,))
               for lv in LEVIES}
        for name, v in byl[0.20].items():
            allsigns = set()
            for lv in LEVIES:
                allsigns |= set(a50_grid.signs(byl[lv].get(name, [])))
            read = len(allsigns) == 1 and "0" not in allsigns
            key = f"{auth} | {name}"
            verdict[key] = {"levy_0.20": v, "signs_all_levies": sorted(allsigns), "read": read}
            if name.split(" | ")[-1] in ("prod_share", "owners_end"):
                print(f"  {key:66s} {v}  {'read ' + next(iter(allsigns)) if read else 'NOT READ ' + str(sorted(allsigns))}")

    record = {"stage": "A50-block3",
              "criteria": [
                  {"name": "A50-6", "kind": "instrument", "passed": ok6,
                   "detail": "block 2 c 0.12 rows reproduce with the authority written out" + (f"; {d6[:6]}" if d6 else "")},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2, "detail": f"fund adds up in {len(rows)} runs"},
                  {"name": "A50-4", "kind": "instrument", "passed": ok4, "detail": "locked accounts never spent"}],
              "rows": rows, "cell_summary": summary, "refill_ratio": ratios, "differences": verdict,
              "config": {"authorities": {k: list(v) for k, v in AUTHORITIES.items()}, "c": C,
                         "levies": list(LEVIES), "seeds": list(SEEDS), "short_stay_share": 0.1}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok6 and ok2 and ok4) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
