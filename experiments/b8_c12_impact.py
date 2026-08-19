#!/usr/bin/env python3
"""C12: the blast radius of O29's fix. **It judges nothing.**

Registered in the B8 inputs register §6.6.15.4. C12 exists to turn
"would a re-run give a different answer" from a guess into a number, so that a
ruling on O28 and O29 is made against the size of the change rather than against
the shape of the rule. **Computes no ``omega``, reads no prediction, and settles
no objection.**

--------------------------------------------------------------------------
What §6.6.15 already settled without running anything
--------------------------------------------------------------------------

**O28's verdict is invariant, by algebra.** ``b8_0a_gate`` passes when
``ratio_max < 1.0`` and ``ratio_max`` is a maximum over the qualifying loops.
Dropping loops cannot raise a maximum, and the gate currently passes on all six
archives with zero loops over the bound, so removing the field-108-contaminated
clean cures cannot turn PASS into FAIL.

**O29's first direction changes no existing number, by code structure.**
``quiet_pairs`` excludes per loan; ``contract_payments`` clusters per contract
period; ``contract_periods`` always breaks at a loan boundary. A contract period
therefore belongs to exactly one loan, so re-admitting loan X's pairs cannot
touch loan Y's estimate.

**O29's second direction is the only one that rewrites existing numbers**, and
for a loan carrying neither field 63 nor field 108 it rewrites nothing, because
``12 - 0 - 0 = 12``. So the blast radius is bounded by the loans that carry one
of those fields, and that is what this file measures.

Usage::

    python experiments/b8_c12_impact.py selftest    # touches no real archive
    python experiments/b8_c12_impact.py run
    python experiments/b8_c12_impact.py run --only 2019Q1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_omega as W  # noqa: E402

OUT = K.ROOT / "results" / "b8_c12_impact.md"

#: Pit 30: the selftest opens the fixture with this same list.
COLS = ["period", "rate", "upb", "rem_legal", "delinq", "mod_flag", "nib_upb",
        "defer_amt"]

#: A payment estimate counts as changed above this relative move. The reported
#: balance is printed to the cent, so a payment of order 1e3 carries about 1e-5
#: of rounding; 1e-4 is an order of magnitude above that and is stated here
#: rather than chosen inside a table.
CHANGED_TOL = 1e-4


def _estimates(c: K.Core, period: np.ndarray, **kw):
    q = K.quiet_pairs(c, **kw)
    pay_row, known_row, per = W.contract_payments(c, period, q)
    return pay_row, known_row, per, q


def measure(c: K.Core) -> dict:
    period = W.contract_periods(c, fill=True)
    loan = c.loan_of_row()

    # **Both ends are explicit.** This file compares two readings, so neither
    # may be spelled as "whatever the default is": the 2026-08-17 flip would
    # otherwise silently make the two ends identical and the table would read
    # as "nothing changes".
    pay_a, known_a, _pa, qa = _estimates(
        c, period, require_never_deferred=True, ib_net=False)
    pay_b, known_b, _pb, _qb = _estimates(
        c, period, require_never_deferred=True, ib_net=True)

    # direction one: admit the field-63 loans, on the corrected balance
    pay_c, known_c, _pc, _qc = _estimates(
        c, period, require_never_deferred=False, ib_net=True)

    dfr = c.row["defer_amt"][:].astype(np.int64)
    nib = c.row["nib_upb"][:].astype(np.int64)
    has_d = c.cummax_within_loan((dfr != K.U32_NA) & (dfr > 0))
    has_n = c.cummax_within_loan((nib != K.U32_NA) & (nib > 0))
    last = (c.row_start.astype(np.int64) + c.n_per_loan.astype(np.int64) - 1)
    loan_d = has_d[last]
    loan_n = has_n[last]

    # per loan: does the estimate move. Read at the loan's last row, which
    # carries the final contract period; a loan whose estimate is unknown on
    # either side is counted separately rather than folded into "unchanged".
    ka, kb = known_a[last], known_b[last]
    pa, pb = pay_a[last], pay_b[last]
    both = ka & kb
    rel = np.full(c.n_loans, np.nan)
    ok = both & (pa > 0)
    rel[ok] = np.abs(pb[ok] - pa[ok]) / pa[ok]
    changed = ok & (rel > CHANGED_TOL)

    def blk(sel):
        n = int(sel.sum())
        r = rel[sel & ok]
        r = r[np.isfinite(r)]
        return {
            "loans": n,
            "comparable": int((sel & ok).sum()),
            "only_one_known": int((sel & (ka ^ kb)).sum()),
            "changed": int((sel & changed).sum()),
            "p50": float(np.percentile(r, 50)) if r.size else float("nan"),
            "p90": float(np.percentile(r, 90)) if r.size else float("nan"),
            "max": float(r.max()) if r.size else float("nan"),
        }

    a = {
        "n_loans": int(c.n_loans),
        "defer_loans": blk(loan_d),
        "neither": blk(~loan_d & ~loan_n),
        # direction one, pure increment
        "excluded_63": int(loan_n.sum()),
        "gained": int((loan_n & ~known_a[last] & known_c[last]).sum()),
        "gained_any": int((~known_a[last] & known_c[last]).sum()),
    }

    # why it moves: quiet pairs before against after the first deferral onset
    qc = qa["cur"]
    on = (dfr != K.U32_NA) & (dfr > 0)
    e = np.zeros(c.n_rows, dtype=bool)
    same = np.zeros(c.n_rows, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]
    e[1:] = on[1:] & ~on[:-1] & same[1:]
    rows = np.flatnonzero(e)
    first = np.full(c.n_loans, -1, dtype=np.int64)
    if rows.size:
        lr = loan[rows]
        first[lr[::-1]] = rows[::-1]
    fo = first[loan[qc]]
    sel = fo >= 0
    pre = int((sel & (qc < fo)).sum())
    post = int((sel & (qc > fo)).sum())
    a["quiet_pre"] = pre
    a["quiet_post"] = post
    a["pre_share"] = (pre / (pre + post)) if (pre + post) else float("nan")
    return a


def _f(x, spec=".4f"):
    return "not measurable" if x != x else format(x, spec)


def render(rows: list[dict]) -> str:
    L, A = [], None
    L.append("# C12: the blast radius of O29's fix\n")
    A = L.append
    A("Generated by `experiments/b8_c12_impact.py`. Registered in "
      "the B8 inputs register §6.6.15.4. **It judges nothing**: it "
      "measures how much a fix already implied by two settled rulings (C8-1, "
      "C11-1) would move, so the double-report question is answered against a "
      "number.\n")
    A("\n**Settled without running anything** (§6.6.15): O28's verdict is "
      "invariant because `pass = ratio_max < 1.0` and a maximum cannot rise "
      "when loops are removed; O29's first direction changes no existing "
      "number because a contract period belongs to exactly one loan. **Only "
      "the balance correction rewrites anything, and only on loans carrying "
      "field 63 or field 108.**\n")

    A("\n## 1. The loans that cannot move, checked rather than asserted\n")
    A("`12 - 0 - 0 = 12`, so a loan with neither field must read an identical "
      "estimate. **A non-zero `changed` here would mean the switch does "
      "something it was not supposed to do.**\n")
    A("| archive | loans with neither field | comparable | **changed** | max |")
    A("|---|---|---|---|---|")
    for r in rows:
        b = r["neither"]
        A(f"| {r['name']} | {b['loans']:,} | {b['comparable']:,} | "
          f"**{b['changed']:,}** | {_f(b['max'], '.2e')} |")

    A("\n## 2. The blast radius: loans carrying field 108\n")
    A(f"Changed means a relative move above {CHANGED_TOL:.0e}, an order of "
      "magnitude above the cent rounding the reported balance carries.\n")
    A("| archive | field-108 loans | comparable | **changed** | share | "
      "move p50 | p90 | max |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        b = r["defer_loans"]
        sh = (f"{b['changed'] / b['comparable']:.4f}" if b["comparable"]
              else "not measurable")
        A(f"| {r['name']} | {b['loans']:,} | {b['comparable']:,} | "
          f"**{b['changed']:,}** | **{sh}** | {_f(b['p50'])} | "
          f"{_f(b['p90'])} | {_f(b['max'])} |")

    A("\n## 3. Why it moves, or does not: where the quiet months sit\n")
    A("The estimate is a modal cluster over a contract period, and "
      "`contract_periods` does **not** break at a field-108 onset, so one "
      "period spans both sides. **The mode lands on whichever side has more "
      "months**, which is why the share below predicts the direction of §2.\n")
    A("| archive | quiet pairs before the onset | after | **share before** |")
    A("|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['quiet_pre']:,} | {r['quiet_post']:,} | "
          f"**{_f(r['pre_share'])}** |")

    A("\n## 4. Direction one: what re-admitting the field-63 loans adds\n")
    A("**Pure increment.** These loans have no estimate today because "
      "`require_never_deferred=True` removes them entirely; nothing they gain "
      "can change another loan's number.\n")
    A("| archive | loans carrying field 63 | **newly estimable** | "
      "newly estimable, any loan |")
    A("|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['excluded_63']:,} | **{r['gained']:,}** | "
          f"{r['gained_any']:,} |")

    A("\n## What this does not decide\n")
    A("- **It does not rule on O28 or O29.** It measures the size of a change "
      "whose justification is C8-1 and C11-1, not this table.\n")
    A("- **A small blast radius is not a reason to skip the fix** "
      "(§6.6.15.5). It decides what a double report should contain, not "
      "whether the correction happens.\n")
    A("- It computes no `omega` and reads no prediction.\n")
    return "\n".join(L) + "\n"


def run(names: list[str]) -> int:
    out = []
    for name in names:
        with K.Core(name, cols=COLS, loan_cols=[]) as c:
            a = measure(c)
        a["name"] = name
        out.append(a)
        d = a["defer_loans"]
        print(f"  {name}: neither-field changed={a['neither']['changed']} | "
              f"108 loans {d['loans']:,} changed {d['changed']:,} "
              f"p50={_f(d['p50'])} | gained {a['gained']:,}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(out), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


def selftest() -> int:
    """Runs on ``b8_core``'s own fixture, which carries field 63 and no field
    108, so it exercises direction one and the invariance of untouched loans."""
    fails = []
    tag = K._fixture_tag()
    zp = K.SELFTEST_DIR / "raw" / f"2098Q1_{tag}.zip"
    if not zp.exists():
        K._synth(zp)
    K.build_archive(zp, force=True, cache_root=K.SELFTEST_DIR / "cache")
    with K.Core(zp.stem, cols=COLS, loan_cols=[],
                cache_root=K.SELFTEST_DIR / "cache") as c:
        a = measure(c)
    print(f"  neither-field loans {a['neither']['loans']} changed "
          f"{a['neither']['changed']}", file=sys.stderr)
    print(f"  field-63 loans {a['excluded_63']} newly estimable {a['gained']}",
          file=sys.stderr)
    if a["neither"]["changed"] != 0:
        fails.append("a loan carrying neither field changed; `12 - 0 - 0 = 12` "
                     "is violated and the switch is doing something else")
    if a["neither"]["comparable"] < 1:
        fails.append("no comparable loan without either field, so the "
                     "invariance check is vacuous")
    if a["excluded_63"] < 1:
        fails.append("the fixture carries no field-63 loan, so direction one "
                     "is untested")
    if a["gained"] < 1:
        fails.append("re-admitting the field-63 loans gained nothing, so the "
                     "increment is untested")
    txt = render([dict(a, name="fixture")])
    # every table's rows must match its header's width. A published
    # results file was malformed on 2026-08-17 and the person who
    # generated it read it and quoted from it without noticing.
    for _c in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {_c}")
    for need in ("## 1. The loans that cannot move", "## 2. The blast radius",
                 "## 3. Why it moves", "## 4. Direction one"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    if fails:
        print("\nSELFTEST FAILED", file=sys.stderr)
        for x in fails:
            print(f"  - {x}", file=sys.stderr)
        return 1
    print("\nselftest ok", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["selftest", "run"])
    ap.add_argument("--only", action="append", default=None)
    a = ap.parse_args()
    if a.cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(run(a.only or ["2002Q1", "2006Q1", "2007Q1", "2012Q1",
                                    "2017Q1", "2019Q1"]))


if __name__ == "__main__":
    main()
