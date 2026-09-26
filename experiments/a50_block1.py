"""A50 block 1: the contribution taken apart, checked; one seed previewed.

Carrier: A49's grid cells without lending (A47 block 5, levy 0.20, short stays 0.1).
Arms, at contribution rate c: none; both sides parked (A49's "contrib only"); employee
parked; employer parked; employer returned (paid straight into the receivers' holdings,
a wage rise of c).

Checks, each with a planted error that must make it fail (--selftest):
  A50-1  instrument  with the three new switches at their defaults, A49's "contrib only"
                     grid rows (both regimes, c 0.05 and 0.12, short 0 and 0.1, five seeds)
                     reproduce field for field, and so do A48's rows and A49 blocks 1-3's
                     previews
  A50-2  instrument  the fund adds up: a parked arm's accounts and fund cash equal what was
                     parked less what was spent from accounts; a returned arm holds nothing
                     in the fund and returned exactly what the employer side paid; a side
                     that is off paid nothing

Run from the repo root:
    python experiments/a50_block1.py
    python experiments/a50_block1.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a47_block3  # noqa: E402
import a49_block3  # noqa: E402
import a49_grid  # noqa: E402
from a49_block1 import BOUND, UNBOUND, reading  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a50_block1.json"

#: arm -> (employee, employer, park); None is no contribution at all
SIDES = {
    "none": None,
    "both parked": (True, True, True),
    "employee parked": (True, False, True),
    "employer parked": (False, True, True),
    "employer returned": (False, True, False),
}


def rules_for(regime: str, arm: str, c: float, short: float = 0.1, **knob):
    base = BOUND if regime == "bound" else UNBOUND
    kw = dict(short_stay_share=short, short_stay_rate=0.25, **knob)
    s = SIDES[arm]
    if s is not None:
        kw.update(provident_rate=c, provident_employee=s[0], provident_employer=s[1],
                  provident_park=s[2])
    return replace(base, **kw)


# -- checks ---------------------------------------------------------------------------

def _grid_row(args):
    import warnings
    warnings.filterwarnings("ignore")
    return a49_grid.one(args)


def reproduction() -> tuple[bool, list[str]]:
    stored = json.loads(a49_grid.OUT.read_text(encoding="utf-8"))["grid_rows"]
    want = [x for x in stored if x["lender"] == "contrib only"]
    jobs = [(x["regime"], x["lender"], x["c"], x["r"], x["d"], x["short"], x["loan"], x["seed"], {})
            for x in want]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as ex:
        now = list(ex.map(_grid_row, jobs, chunksize=2))
    d = []
    for a, b in zip(want, now):
        d += [f"grid {a['regime']} c{a['c']} short{a['short']} seed{a['seed']}: {k}"
              for k in a if k != "seconds" and a[k] != b.get(k)]
    ok3, d3 = a49_block3.regression()
    d += d3
    stored3 = json.loads(a49_block3.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    for name, rl in a49_block3.ARMS.items():
        m, _ = a47_block3.run(rl)
        now3 = {**a49_block3.treasury_check(m)[1], **reading(m)}
        d += [f"b3 {name}: {k}" for k, v in now3.items() if stored3[name].get(k) != v]
    return (not d) and len(want) == 40, d if len(want) == 40 else d + [f"{len(want)} stored rows, not 40"]


def fund_check(m) -> tuple[bool, dict]:
    r = m.rules
    emp, er = m.pf_contrib_employee, m.pf_contrib_employer
    parked = emp + (er if r.provident_park else 0.0)
    scale = max(1.0, emp + er)
    released = getattr(m, "pf_released", 0.0)
    acc_res = float(m.account.sum()) - (parked - m.pf_spent_from_accounts - released)
    cash_res = m.pf_cash - (parked - m.pf_spent_from_accounts - released)
    ok = abs(acc_res) <= 1e-9 * scale and abs(cash_res) <= 1e-9 * scale
    ok &= bool((m.account >= -1e-12).all()) and m.pf_cash >= -1e-9
    if r.provident_park:
        ok &= m.pf_returned == 0.0
    else:
        ok &= abs(m.pf_returned - er) <= 1e-12 * scale
        ok &= float(abs(m.account).sum()) == 0.0 and m.pf_cash == 0.0
    if r.provident_rate > 0.0:
        ok &= (emp > 0.0) == r.provident_employee
        ok &= (er > 0.0) == r.provident_employer
    return bool(ok), {"employee": round(emp, 4), "employer": round(er, 4),
                      "returned": round(m.pf_returned, 4),
                      "spent_from_accounts": round(m.pf_spent_from_accounts, 4),
                      "accounts_end": round(float(m.account.sum()), 4), "pf_cash_end": round(m.pf_cash, 4),
                      "account_residual": acc_res, "cash_residual": cash_res}


def preview_row(m) -> dict:
    mix = m.renter_mix_history[-50:]
    base = reading(m)
    return {"renters_last50": round(sum(x[0] for x in mix) / len(mix), 2) if mix else None,
            "owners_end": base["owners_end"], "price_ratio": base["price_ratio"],
            "prod_share": base["prod_share"], "top_decile": base["top_decile"]}


def selftest() -> None:
    m, _ = a47_block3.run(rules_for("bound", "employee parked", 0.12), rounds=80)
    assert fund_check(m)[0] and m.pf_contrib_employee > 0, "the employee arm must balance"
    m.pf_contrib_employer = 0.1
    assert not fund_check(m)[0], "A50-2 must catch an employer who paid in an employee-only arm"
    m, _ = a47_block3.run(rules_for("bound", "employer returned", 0.12), rounds=80)
    assert fund_check(m)[0] and m.pf_returned > 0, "the returned arm must balance"
    m.account[int(m._wage_receivers[0])] += 0.01
    assert not fund_check(m)[0], "A50-2 must catch money left in an account in a returned arm"
    m, _ = a47_block3.run(rules_for("bound", "employer returned", 0.12), rounds=80)
    m.pf_returned -= 0.01
    assert not fund_check(m)[0], "A50-2 must catch a return that differs from what was paid"
    m, _ = a47_block3.run(rules_for("unbound", "both parked", 0.12), rounds=80)
    m.pf_cash += 0.01
    assert not fund_check(m)[0], "A50-2 must catch fund cash that does not add up"
    for bad in (dict(provident_employee=True, provident_park=False),
                dict(provident_employee=False, provident_employer=False),
                dict(commit_loan=True, loan_lender="provident", provident_employee=False,
                     provident_park=False)):
        try:
            replace(BOUND, provident_rate=0.05, **bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be refused")
    print("selftest ok: A50-2 catches a stray employer payment, money left in a returned arm, "
          "a short return and unbalanced fund cash; the three bad switch sets are refused")


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A50-1 [instrument]: A49 contrib-only rows (40), A48 rows, "
          f"A49 blocks 1-3 previews reproduce" + (f"; {d1[:6]}" if d1 else ", field for field"))
    ok2, arms = True, {}
    for regime in ("unbound", "bound"):
        for arm in SIDES:
            for c in ((0.12,) if arm != "none" else (0.0,)):
                m, secs = a47_block3.run(rules_for(regime, arm, c))
                f_ok, f = fund_check(m)
                ok2 &= f_ok
                arms[f"{regime}, {arm}, c {c}"] = {"seconds": round(secs, 2), "fund_ok": f_ok, **f,
                                                    **preview_row(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A50-2 [instrument]: fund adds up, sides that are off paid nothing, "
          f"{len(arms)} arms")
    keys = ["employee", "employer", "returned", "accounts_end", "renters_last50", "owners_end",
            "price_ratio", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds, c 0.12, short stays 0.1:")
    for name, r in arms.items():
        print(f"  {name:36s} " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A50-block1",
              "criteria": [
                  {"name": "A50-1", "kind": "instrument", "passed": ok1,
                   "detail": "A49 contrib-only grid rows, A48 rows, A49 blocks 1-3 previews reproduce"
                   + (f"; {d1[:6]}" if d1 else "")},
                  {"name": "A50-2", "kind": "instrument", "passed": ok2,
                   "detail": f"fund adds up in {len(arms)} arms; off sides paid nothing"}],
              "preview_seed0": arms,
              "config": {"arms": {k: list(v) if v else None for k, v in SIDES.items()}, "c": 0.12,
                         "short_stay_share": 0.1, "short_stay_rate": 0.25}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
