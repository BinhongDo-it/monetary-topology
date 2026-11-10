"""A49 block 1: the commitment loan and short stays, checked; one seed previewed.

Checks, each with a planted error that must make it fail (--selftest):
  A49-1  instrument  both switches off: A48's stored grid rows reproduce field for field
  A49-2  instrument  claims conserved every round (asserted in the model); the loan book
                     closes: lent = repaid principal + credited on foreclosure + written off
                     + outstanding; no balance is negative
  A49-3  instrument  no short-stayer ever borrowed; every borrower held the down payment

Also printed (design ③, which was inferred and is checked here): with no loan, how many
renters at the end hold less than a low-tier unit costs them.

Run from the repo root:
    python experiments/a49_block1.py
    python experiments/a49_block1.py --selftest
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
import a48_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a49_block1.json"
BOUND = a47_block5.rules_for("bound public", 0.002, 0.002, None)
UNBOUND = a47_block5.rules_for("unbound", 0.0, 0.002, None)


def rules(base, loan=False, d=0.1, lender="public", r=0.0, short=0.0, k=3):
    kw = {}
    if loan:
        kw.update(commit_loan=True, loan_down=d, loan_lender=lender, loan_rate=r, loan_arrears_k=k)
    if short:
        kw.update(short_stay_share=short, short_stay_rate=0.25)
    return replace(base, **kw)


def reproduction() -> tuple[bool, list[str]]:
    stored = json.loads(a48_grid.OUT.read_text(encoding="utf-8"))["grid_rows"]
    want = {("public", 1.16, 0.005, 0.02), ("listed 0.271", 1.45, 0.01, 0.0), ("public", 1.0, 0.0, 0.03)}
    diffs = []
    for row in stored:
        if (row["landlord"], row["R0"], row["g"], row["tau_o"]) not in want or row["knob"]:
            continue
        now = a48_grid.one((row["landlord"], row["R0"], row["g"], row["tau_o"], row["seed"], {}))
        diffs += [f"{row['landlord']} seed {row['seed']}: {k}" for k, v in row.items()
                  if k != "seconds" and now.get(k) != v]
    return not diffs, diffs


def book_check(m) -> tuple[bool, dict]:
    lent = sum(x[2] for x in m.loan_log)
    closes = lent - m.repaid_principal - m.foreclosure_credit - m.written_off - float(m.debt.sum())
    ok = abs(closes) <= 1e-9 * max(1.0, lent) and (m.debt >= -1e-15).all()
    # the interest book: what accrued is paid, still owed, or written off
    owed = float(m.interest_owed.sum())
    i_closes = m.interest_accrued - m.interest_paid - owed - m.interest_written_off
    ok &= abs(i_closes) <= 1e-9 * max(1.0, m.interest_accrued) and (m.interest_owed >= -1e-15).all()
    return bool(ok), {"lent": round(lent, 6), "repaid_principal": round(m.repaid_principal, 6),
                      "foreclosure_credit": round(m.foreclosure_credit, 6),
                      "written_off": round(m.written_off, 6), "outstanding": round(float(m.debt.sum()), 6),
                      "book_residual": closes,
                      "interest_accrued": round(m.interest_accrued, 6),
                      "interest_owed": round(owed, 6),
                      "interest_written_off": round(m.interest_written_off, 6),
                      "interest_residual": i_closes}


def borrower_check(m) -> tuple[bool, dict]:
    short_borrowed = sum(1 for x in m.loan_log if x[5])
    under_down = sum(1 for x in m.loan_log if x[4] + 1e-12 < x[3])
    return short_borrowed == 0 and under_down == 0, {"loans": len(m.loan_log),
                                                     "short_borrowed": short_borrowed,
                                                     "under_down_payment": under_down}


def renters_vs_price(m) -> dict:
    """Renters at the end, and how many hold less than a low-tier unit costs them."""
    held = m.units.sum(axis=1)
    renters = np.flatnonzero((held <= 0) & m._is_production)
    need = m.terms[renters, 0] * float(m.price[0])
    return {"renters_end": int(renters.size),
            "renters_below_low_tier_cost": int((m.holdings[renters] < need).sum()),
            "renters_median_claims": round(float(np.median(m.holdings[renters])), 4) if renters.size else None,
            "low_tier_cost_median": round(float(np.median(need)), 4) if renters.size else None}


def reading(m) -> dict:
    from a47_block1 import reading as base
    r = base(m)
    mix = m.renter_mix_history
    return {"renter_mix_end": list(mix[-1]) if mix else None,
            "renters_mean_last50": round(float(np.mean([x[0] for x in mix[-50:]])), 1) if mix else None,
            "short_share_of_renters_last50": round(float(np.mean([x[1] / x[0] for x in mix[-50:] if x[0]])), 3) if mix else None,
            "cleared_nodes": len(m.cleared_nodes), "foreclosures": len(m.foreclosures),
            "written_off": round(m.written_off, 4), "interest_paid": round(m.interest_paid, 4),
            "prod_share": r["net_worth_production_layer_share"], "top_decile": r["net_worth_top_decile_share"],
            "owners_end": r["owners_end"], "price_ratio": r["price_ratio_end_to_start_low_tier"]}


ARMS = {
    "bound, no loan": rules(BOUND),
    "bound, no loan, short 0.1": rules(BOUND, short=0.1),
    "bound, loan public d 0.1": rules(BOUND, loan=True),
    "bound, loan public d 0.1, short 0.1": rules(BOUND, loan=True, short=0.1),
    "bound, loan bank d 0.1 r 0.02, short 0.1": rules(BOUND, loan=True, lender="bank", r=0.02, short=0.1),
    "unbound, no loan, short 0.1": rules(UNBOUND, short=0.1),
    "unbound, loan bank d 0.1 r 0.02, short 0.1": rules(UNBOUND, loan=True, lender="bank", r=0.02, short=0.1),
    "unbound, loan public d 0.1, short 0.1": rules(UNBOUND, loan=True, short=0.1),
}


def selftest() -> None:
    m, _ = a47_block3.run(ARMS["bound, loan public d 0.1, short 0.1"], rounds=80)
    assert book_check(m)[0] and borrower_check(m)[0]
    assert m.loan_log, "the selftest arm must lend"
    m.repaid_principal += 0.01
    assert not book_check(m)[0], "A49-2 must catch a book that does not close"
    m, _ = a47_block3.run(ARMS["bound, loan bank d 0.1 r 0.02, short 0.1"], rounds=80)
    assert book_check(m)[0] and m.interest_accrued > 0.0, "the bank arm must accrue interest and balance"
    m.interest_owed[0] += 0.01
    assert not book_check(m)[0], "A49-2 must catch interest that is neither paid, owed nor written off"
    m, _ = a47_block3.run(ARMS["bound, loan public d 0.1, short 0.1"], rounds=80)
    x = list(m.loan_log[0]); x[5] = True; m.loan_log[0] = tuple(x)
    assert not borrower_check(m)[0], "A49-3 must catch a short-stayer who borrowed"
    m, _ = a47_block3.run(ARMS["bound, loan public d 0.1, short 0.1"], rounds=80)
    x = list(m.loan_log[0]); x[4] = x[3] - 0.01; m.loan_log[0] = tuple(x)
    assert not borrower_check(m)[0], "A49-3 must catch a borrower short of the down payment"
    class Leak(type(m)):
        def _service_loans(self):
            super()._service_loans()
            self.pool += 0.001
    from monetary_topology.housing_rules import A47Config
    from a47_block1 import a3_config
    try:
        Leak(A47Config(a3=a3_config(0, 40, **{**a47_block3.CARRIER_ASSET, "max_units": 1}),
                       rules=ARMS["bound, loan public d 0.1"])).run()
    except AssertionError:
        pass
    else:
        raise AssertionError("the conservation check must fire on a leak in the loan book")
    try:
        replace(BOUND, loan_lender="nobody")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown lender must be refused")
    print("selftest ok: A49-2 catches an open book and a leak; A49-3 catches a short-stayer "
          "borrowing and a borrower short of the down payment; an unknown lender is refused")


def main() -> int:
    ok1, d1 = reproduction()
    print(f"{'PASS' if ok1 else 'FAIL'} A49-1 [instrument]: switches off reproduce A48's rows"
          + (f"; {d1[:5]}" if d1 else ", field for field"))
    ok2 = ok3 = True
    arms = {}
    for name, rl in ARMS.items():
        m, secs = a47_block3.run(rl)
        b_ok, b = book_check(m)
        c_ok, c = borrower_check(m)
        ok2 &= b_ok
        ok3 &= c_ok
        arms[name] = {"seconds": round(secs, 2), "book_ok": b_ok, **b, "borrower_ok": c_ok, **c,
                      **renters_vs_price(m), **reading(m)}
    print(f"{'PASS' if ok2 else 'FAIL'} A49-2 [instrument]: conservation and a closed loan book, {len(ARMS)} arms")
    print(f"{'PASS' if ok3 else 'FAIL'} A49-3 [instrument]: no short-stayer borrowed, every borrower held the down payment")
    nl = arms["bound, no loan"]
    print(f"---- design ③ check: bound, no loan, end: {nl['renters_below_low_tier_cost']} of "
          f"{nl['renters_end']} renters hold less than a low-tier unit costs them "
          f"(median claims {nl['renters_median_claims']} against median cost {nl['low_tier_cost_median']})")
    keys = ["seconds", "loans", "renters_end", "renter_mix_end", "renters_mean_last50",
            "short_share_of_renters_last50", "cleared_nodes", "foreclosures", "written_off",
            "interest_paid", "owners_end", "price_ratio", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A49-block1",
              "criteria": [
                  {"name": "A49-1", "kind": "instrument", "passed": ok1, "detail": "switches off reproduce A48"},
                  {"name": "A49-2", "kind": "instrument", "passed": ok2, "detail": "conservation and loan book"},
                  {"name": "A49-3", "kind": "instrument", "passed": ok3, "detail": "who borrowed"}],
              "preview_seed0": arms,
              "config": {"arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__} for k, v in ARMS.items()}}}
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
