"""A50 block 4: the authority sees what is paid into the accounts.

``provident_visible`` has the carrier's authority count each round's parked contributions
as arrived layer-2 inflow, so it does not issue against that flow. It still sees the lower
spending that follows from workers holding less, and issues against that.

Grid: the five parked arms (both parked, employee parked, employer parked, employee locked,
both locked) at c 0.12, regime {unbound, bound}, levy {0.20, 0.15, 0.25}, five seeds. The
arms "none" and "employer returned" are unaffected by the switch and are block 2's rows.

Checks, each with a planted error that must make it fail (--selftest):
  A50-8   instrument  with the switch off, block 1's reproduction (A49 rows) and block 3's
                      (block 2's c 0.12 rows) hold on the module with the switch in it
  A50-9   instrument  a visible arm withheld something, and never more than gain x what was
                      parked; the switch is refused with no issuance and on a returned arm
  A50-2   instrument  the fund adds up (block 1's check)
  A50-4   instrument  locked accounts never spent (block 2's check)

Readings (A50-10): visible against unseen, side by side: refill ratio, circulation at the
end, and block 2's seven differences.

Run from the repo root:
    python experiments/a50_block4.py
    python experiments/a50_block4.py --selftest
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

import a50_grid  # noqa: E402
from a50_grid import QTY, REGIMES, SEEDS, rules_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block4.json"
C = 0.12
LEVIES = (0.20, 0.15, 0.25)
PARKED = ("both parked", "employee parked", "employer parked", "employee locked", "both locked")


def visible_rules(regime, arm, levy):
    knob = {} if levy == 0.20 else {"levy_rate": levy}
    return replace(rules_for(regime, arm, C, **knob), provident_visible=True)


def visible_check(m) -> tuple[bool, dict]:
    parked = m.pf_contrib_employee + (m.pf_contrib_employer if m.rules.provident_park else 0.0)
    gain = m.config.authority.gain
    ok = 0.0 < m.pf_visible_cut <= gain * parked * (1 + 1e-12)
    return bool(ok), {"visible_cut": round(m.pf_visible_cut, 4), "visible_cut_over_parked":
                      round(m.pf_visible_cut / parked, 4) if parked else None}


def one(args):
    regime, arm, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    import a50_block1
    m, secs = a47_block3.run(visible_rules(regime, arm, levy), seed=seed)
    f_ok, f = a50_block1.fund_check(m)
    l_ok, lk = a50_grid.lock_check(m)
    v_ok, v = visible_check(m)
    f = {k: val for k, val in f.items() if k not in ("account_residual", "cash_residual")}
    h = m.history
    return {"regime": regime, "arm": arm, "c": C, "seed": seed, "levy": levy, "visible": True,
            "seconds": round(secs, 3), "fund_ok": f_ok, "lock_ok": l_ok, "visible_ok": v_ok, **f, **lk, **v,
            "issuance_total": round(float(np.sum(h.issuance)), 4),
            "circulating_end": round(float(np.asarray(h.total_claims)[-1]), 4),
            **a50_block1.preview_row(m)}


def unseen_rows():
    rec = json.loads(a50_grid.OUT.read_text(encoding="utf-8"))
    rows = [dict(x, levy=0.20, visible=False) for x in rec["grid_rows"] if x["c"] in (0.0, C)]
    rows += [dict(x, levy=x["knob"]["levy_rate"], visible=False) for x in rec["knob_rows"]]
    return rows


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(visible_rules("bound", "employee locked", 0.20), rounds=80)
    assert visible_check(m)[0], "the visible arm must withhold within gain x parked"
    m.pf_visible_cut = 0.0
    assert not visible_check(m)[0], "A50-9 must catch a visible arm that withheld nothing"
    m.pf_visible_cut = 10 * (m.pf_contrib_employee + 1.0)
    assert not visible_check(m)[0], "A50-9 must catch withholding beyond what was parked"
    try:
        replace(rules_for("bound", "employer returned", C), provident_visible=True)
    except ValueError:
        pass
    else:
        raise AssertionError("visible on a returned arm must be refused")
    import a50_block3
    try:
        a50_block3.run(visible_rules("bound", "employee locked", 0.20), 0, ("none", 1.0), rounds=5)
    except ValueError:
        pass
    else:
        raise AssertionError("visible with no issuance must be refused")
    print("selftest ok: A50-9 catches withholding nothing and withholding beyond what was parked; "
          "the switch is refused on a returned arm and with no issuance")


def main() -> int:
    import a50_block1
    import a50_block3
    workers = max(1, (os.cpu_count() or 2) - 1)
    ok_a, d_a = a50_block1.reproduction()
    ok_b, d_b = a50_block3.reproduction(workers)
    ok8 = ok_a and ok_b
    print(f"{'PASS' if ok8 else 'FAIL'} A50-8 [instrument]: switch off, A49 rows and block 2 rows reproduce"
          + (f"; {(d_a + d_b)[:6]}" if (d_a or d_b) else ""))
    jobs = [(reg, arm, lv, s) for reg in REGIMES for arm in PARKED for lv in LEVIES for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=2))
    print(f"{len(rows)} runs {time.perf_counter() - t0:.1f} s; {workers} workers")
    ok9 = all(r["visible_ok"] for r in rows)
    ok2 = all(r["fund_ok"] for r in rows)
    ok4 = all(r["lock_ok"] for r in rows)
    print(f"{'PASS' if ok9 else 'FAIL'} A50-9 [instrument]: every visible arm withheld, within gain x parked")
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up in {len(rows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A50-4 [instrument]: locked accounts never spent")

    unseen = unseen_rows()
    shared = [x for x in unseen if x["arm"] in ("none", "employer returned")]
    seen = shared + rows

    print("\ncells, levy 0.20, mean over 5 seeds (unseen -> visible): " + " | ".join(QTY)
          + " | issuance | circulating end | withheld")
    summary = {}
    for reg in REGIMES:
        for arm in a50_grid.ARMS:
            for tag, src in (("unseen", unseen), ("visible", seen)):
                rs = [x for x in src if (x["regime"], x["arm"], x["levy"]) == (reg, arm, 0.20)]
                keys = QTY + ("issuance_total", "circulating_end") + (("visible_cut",) if tag == "visible"
                                                                      and arm in PARKED else ())
                s = {k: round(float(np.mean([x[k] for x in rs if x.get(k) is not None])), 4) for k in keys}
                summary[f"{tag} | {reg} | {arm}"] = s
                if tag == "visible" and arm not in PARKED:
                    continue
                print(f"  {tag:7s} | {reg:7s} | {arm:17s} " + " | ".join(str(s[k]) for k in keys))

    print("\nrefill ratio per seed, levy 0.20 (issuance in the locked arm less block 2's no-fund issuance, "
          "over money locked):")
    ratios = {}
    for tag, src in (("unseen", unseen), ("visible", seen)):
        for reg in REGIMES:
            base = {x["seed"]: x for x in src if (x["regime"], x["arm"], x["levy"]) == (reg, "none", 0.20)}
            for arm in ("employee locked", "both locked"):
                lk = {x["seed"]: x for x in src if (x["regime"], x["arm"], x["levy"]) == (reg, arm, 0.20)}
                v = [round((lk[s]["issuance_total"] - base[s]["issuance_total"]) / lk[s]["parked"], 4) for s in SEEDS]
                ratios[f"{tag} | {reg} | {arm}"] = v
                print(f"  {tag:7s} | {reg:7s} | {arm:15s} {v}")

    print("\ndifferences, prod_share per seed at levy 0.20 (sign over seeds and levies):")
    verdict = {}
    for tag, src in (("unseen", unseen), ("visible", seen)):
        byl = {lv: a50_grid.differences([x for x in src if x["levy"] == lv], cs=(C,)) for lv in LEVIES}
        for name, v in byl[0.20].items():
            allsigns = set()
            for lv in LEVIES:
                allsigns |= set(a50_grid.signs(byl[lv].get(name, [])))
            read = len(allsigns) == 1 and "0" not in allsigns
            verdict[f"{tag} | {name}"] = {"levy_0.20": v, "signs_all_levies": sorted(allsigns), "read": read}
            if name.endswith("prod_share"):
                print(f"  {tag:7s} | {name:58s} {v}  "
                      f"{'read ' + next(iter(allsigns)) if read else 'NOT READ ' + str(sorted(allsigns))}")
    # visible minus unseen, per seed, for the parked arms
    print("\nvisible - unseen, prod_share per seed, levy 0.20:")
    vm = {}
    for reg in REGIMES:
        for arm in PARKED:
            a = {x["seed"]: x for x in unseen if (x["regime"], x["arm"], x["levy"]) == (reg, arm, 0.20)}
            b = {x["seed"]: x for x in rows if (x["regime"], x["arm"], x["levy"]) == (reg, arm, 0.20)}
            vm[f"{reg} | {arm}"] = [round(b[s]["prod_share"] - a[s]["prod_share"], 4) for s in SEEDS]
            print(f"  {reg:7s} | {arm:17s} {vm[f'{reg} | {arm}']}")

    record = {"stage": "A50-block4",
              "criteria": [
                  {"name": "A50-8", "kind": "instrument", "passed": ok8,
                   "detail": "switch off: A49 and block 2 rows reproduce" + (f"; {(d_a + d_b)[:6]}" if (d_a or d_b) else "")},
                  {"name": "A50-9", "kind": "instrument", "passed": ok9,
                   "detail": "every visible arm withheld, within gain x parked"},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2, "detail": f"fund adds up in {len(rows)} runs"},
                  {"name": "A50-4", "kind": "instrument", "passed": ok4, "detail": "locked accounts never spent"}],
              "rows": rows, "cell_summary": summary, "refill_ratio": ratios, "differences": verdict,
              "visible_minus_unseen_prod_share": vm,
              "config": {"provident_visible": True, "c": C, "levies": list(LEVIES), "seeds": list(SEEDS),
                         "arms": list(PARKED), "short_stay_share": 0.1}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok8 and ok9 and ok2 and ok4) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
