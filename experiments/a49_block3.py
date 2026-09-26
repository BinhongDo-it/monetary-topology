"""A49 block 3: the treasury behind the public lender, checked; one seed previewed.

Checks, each with a planted error that must make it fail (--selftest):
  A49-1c  instrument  A48's stored rows, and blocks 1 and 2's stored previews, reproduce
                      field for field on this module (the pool guards moved nothing)
  A49-8   instrument  under treasury backing the pool never ends a round below minus that
                      round's levy; the loan book closes; with the treasury off no pool is
                      ever negative

Run from the repo root:
    python experiments/a49_block3.py
    python experiments/a49_block3.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a47_block3  # noqa: E402
import a49_block1  # noqa: E402
import a49_block2  # noqa: E402
from a49_block1 import BOUND, UNBOUND, book_check, borrower_check, reading  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a49_block3.json"


def treasury(base, short=0.1, d=0.1, r=0.0):
    return replace(base, commit_loan=True, loan_down=d, loan_lender="public", loan_rate=r,
                   treasury_backing=True, short_stay_share=short, short_stay_rate=0.25)


ARMS = {
    "bound, treasury, short 0.1": treasury(BOUND),
    "bound, treasury, no short": treasury(BOUND, short=0.0),
    "bound, treasury, d 0.2": treasury(BOUND, d=0.2),
    "unbound, treasury, short 0.1": treasury(UNBOUND),
    "unbound, treasury, d 0.2": treasury(UNBOUND, d=0.2),
}


def regression() -> tuple[bool, list[str]]:
    ok_a, d = a49_block1.reproduction()
    ok_b, d1 = a49_block2.block1_regression()
    d += d1
    stored2 = json.loads(a49_block2.OUT.read_text(encoding="utf-8"))["preview_seed0"]
    for name, rl in a49_block2.ARMS.items():
        m, _ = a47_block3.run(rl)
        now = {**a49_block2.fund_check(m)[1], **borrower_check(m)[1], **reading(m)}
        d += [f"b2 {name}: {k}" for k, v in now.items()
              if k not in ("account_residual", "cash_residual") and stored2[name].get(k) != v]
    return not d, d


def treasury_check(m) -> tuple[bool, dict]:
    if m.rules.treasury_backing:
        ok = (m.pool_min_over_cap or 0.0) <= 1.0 + 1e-9
    else:
        ok = min(m.pool_history, default=0.0) >= -1e-12
    ok &= book_check(m)[0]
    return bool(ok), {"pool_min": round(m.pool_min, 4),
                      "pool_min_over_cap": None if m.pool_min_over_cap is None else round(m.pool_min_over_cap, 4),
                      "treasury_repaid": round(m.treasury_repaid, 4), "pool_end": round(m.pool, 4)}


def selftest() -> None:
    m, _ = a47_block3.run(ARMS["unbound, treasury, short 0.1"], rounds=80)
    assert treasury_check(m)[0] and m.loan_log, "the selftest arm must lend within the cap"
    m.pool_min_over_cap = 1.5
    assert not treasury_check(m)[0], "A49-8 must catch an overdraft beyond the round's levy"
    m, _ = a47_block3.run(a49_block1.ARMS["bound, loan public d 0.1"], rounds=80)
    m.pool_history[4] = -0.5
    assert not treasury_check(m)[0], "A49-8 must catch a negative pool with the treasury off"
    try:
        replace(BOUND, commit_loan=True, loan_lender="bank", treasury_backing=True)
    except ValueError:
        pass
    else:
        raise AssertionError("treasury backing for a bank lender must be refused")
    print("selftest ok: A49-8 catches an overdraft beyond the levy and a negative pool without "
          "the treasury; treasury backing for a bank is refused")


def main() -> int:
    okr, dr = regression()
    print(f"{'PASS' if okr else 'FAIL'} A49-1c [instrument]: A48 rows and blocks 1-2 previews reproduce"
          + (f"; {dr[:6]}" if dr else ", field for field"))
    ok8 = True
    arms = {}
    for name, rl in ARMS.items():
        m, secs = a47_block3.run(rl)
        t_ok, t = treasury_check(m)
        ok8 &= t_ok
        arms[name] = {"seconds": round(secs, 2), "treasury_ok": t_ok, **t, **book_check(m)[1],
                      **borrower_check(m)[1], **reading(m)}
    print(f"{'PASS' if ok8 else 'FAIL'} A49-8 [instrument]: overdraft within the levy, book closes, {len(ARMS)} arms")
    keys = ["seconds", "loans", "pool_min", "pool_min_over_cap", "treasury_repaid", "renters_mean_last50",
            "short_share_of_renters_last50", "cleared_nodes", "foreclosures", "written_off",
            "owners_end", "price_ratio", "prod_share", "top_decile"]
    print("\none seed (0), 300 rounds:")
    for name, r in arms.items():
        print(f"  {name}\n    " + ", ".join(f"{k} {r.get(k)}" for k in keys))
    record = {"stage": "A49-block3",
              "criteria": [
                  {"name": "A49-1c", "kind": "instrument", "passed": okr, "detail": "A48 and blocks 1-2 reproduce"},
                  {"name": "A49-8", "kind": "instrument", "passed": ok8, "detail": "treasury overdraft and book"}],
              "preview_seed0": arms,
              "config": {"arms": {k: {f: getattr(v, f) for f in v.__dataclass_fields__} for k, v in ARMS.items()}}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (okr and ok8) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
