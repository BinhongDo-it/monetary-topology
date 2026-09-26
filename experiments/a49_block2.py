"""A49 block 2: the provident fund as the third lender, checked; one seed previewed.

Checks, each with a planted error that must make it fail (--selftest):
  A49-1b  instrument  block 1's stored preview reproduces field for field on this module
  A49-7   instrument  the fund's books: accounts equal contributions less what members spent
                      from them; the fund's cash equals contributions less member spending, less
                      what it paid out as lender, plus what it received; no account or cash is
                      negative; every provident borrower had contributed; the loan book closes

Contribution rates 0.05 and 0.12 per side are the regulation's floor and the ceiling most
places applied before the 2026 amendment; the provident loan rate 0.0285 is the first-home,
over-five-years rate from 2024-05-18. Both are swept in the grid.

Run from the repo root:
    python experiments/a49_block2.py
    python experiments/a49_block2.py --selftest
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
import a49_block1  # noqa: E402
from a49_block1 import BOUND, UNBOUND, book_check, borrower_check, reading  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a49_block2.json"


def pf(base, c=0.05, r=0.0, short=0.1, d=0.1):
    return replace(base, commit_loan=True, loan_down=d, loan_lender="provident", loan_rate=r,
                   provident_rate=c, short_stay_share=short, short_stay_rate=0.25)


ARMS = {
    "bound, provident c 0.05 r 0": pf(BOUND, 0.05, 0.0),
    "bound, provident c 0.12 r 0": pf(BOUND, 0.12, 0.0),
    "bound, provident c 0.05 r 0.0285": pf(BOUND, 0.05, 0.0285),
    "unbound, provident c 0.05 r 0": pf(UNBOUND, 0.05, 0.0),
    "unbound, provident c 0.12 r 0.0285": pf(UNBOUND, 0.12, 0.0285),
    "unbound, contributions only, no loan": replace(UNBOUND, provident_rate=0.05,
                                                    short_stay_share=0.1),
}


def block1_regression() -> tuple[bool, list[str]]:
    stored = json.loads(a49_block1.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    d = []
    for name, rl in a49_block1.ARMS.items():
        m, _ = a47_block3.run(rl)
        now = {**book_check(m)[1], **borrower_check(m)[1], **a49_block1.renters_vs_price(m), **reading(m)}
        d += [f"{name}: {k}" for k, v in now.items() if k != "book_residual" and stored[name].get(k) != v]
    return not d, d


def fund_check(m) -> tuple[bool, dict]:
    C = m.pf_contrib_employee + m.pf_contrib_employer
    acc_res = float(m.account.sum()) - (C - m.pf_spent_from_accounts)
    cash_res = m.pf_cash - (C - m.pf_spent_from_accounts - m.pf_out + m.pf_in)
    scale = max(1.0, C)
    ok = abs(acc_res) <= 1e-9 * scale and abs(cash_res) <= 1e-9 * scale
    ok &= (m.account >= -1e-12).all() and m.pf_cash >= -1e-9
    if m.rules.loan_lender == "provident":
        ok &= all(m.contributed[x[1]] > 0.0 for x in m.loan_log)
    ok &= book_check(m)[0]
    return bool(ok), {"contributions": round(C, 4), "employee": round(m.pf_contrib_employee, 4),
                      "employer": round(m.pf_contrib_employer, 4),
                      "spent_from_accounts": round(m.pf_spent_from_accounts, 4),
                      "accounts_end": round(float(m.account.sum()), 4), "pf_cash_end": round(m.pf_cash, 4),
                      "pf_surplus_end": round(m.pf_surplus(), 4), "account_residual": acc_res,
                      "cash_residual": cash_res}


def selftest() -> None:
    m, _ = a47_block3.run(ARMS["bound, provident c 0.05 r 0"], rounds=80)
    assert fund_check(m)[0] and m.loan_log, "the selftest arm must lend and balance"
    m.account[5] += 0.01
    assert not fund_check(m)[0], "A49-7 must catch an account that does not add up"
    m, _ = a47_block3.run(ARMS["bound, provident c 0.05 r 0"], rounds=80)
    m.pf_cash += 0.01
    assert not fund_check(m)[0], "A49-7 must catch fund cash that does not add up"
    m, _ = a47_block3.run(ARMS["bound, provident c 0.05 r 0"], rounds=80)
    m.contributed[m.loan_log[0][1]] = 0.0
    assert not fund_check(m)[0], "A49-7 must catch a borrower who never contributed"
    try:
        replace(BOUND, commit_loan=True, loan_lender="provident", tenant_tier=True)
    except ValueError:
        pass
    else:
        raise AssertionError("a provident lender with no contributions must be refused")
    print("selftest ok: A49-7 catches a wrong account, wrong fund cash and a non-contributing "
          "borrower; a provident lender with no contributions is refused")


def main() -> int:
    okr, dr = block1_regression()
    print(f"{'PASS' if okr else 'FAIL'} A49-1b [instrument]: block 1's preview reproduces"
          + (f"; {dr[:5]}" if dr else ", field for field"))
    ok7 = True
    arms = {}
    for name, rl in ARMS.items():
        m, secs = a47_block3.run(rl)
        f_ok, f = fund_check(m)
        ok7 &= f_ok
        arms[name] = {"seconds": round(secs, 2), "fund_ok": f_ok, **f, **borrower_check(m)[1], **reading(m)}
    print(f"{'PASS' if ok7 else 'FAIL'} A49-7 [instrument]: fund books, {len(ARMS)} arms")
    keys = ["seconds", "loans", "contributions", "employer", "accounts_end", "pf_cash_end",
            "pf_surplus_end", "renters_mean_last50", "short_share_of_renters_last50", "cleared_nodes",
            "foreclosures", "written_off", "interest_paid", "owners_end", "price_ratio", "prod_share",
            "top_decile"]
    print("\none seed (0), 300 rounds, down payment 0.1, short stays 0.1:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A49-block2",
              "criteria": [
                  {"name": "A49-1b", "kind": "instrument", "passed": okr, "detail": "block 1 reproduces"},
                  {"name": "A49-7", "kind": "instrument", "passed": ok7, "detail": "provident fund books"}],
              "preview_seed0": arms,
              "config": {"arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__} for k, v in ARMS.items()}}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (okr and ok7) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
