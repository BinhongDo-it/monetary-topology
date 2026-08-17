#!/usr/bin/env python3
"""C10: at the re-contracting row, **did the contract actually move, and which
part of it**.

Registered in ``docs/b8_inputs_availability.md`` §6.6.5 and §6.6.7, and the
reading is fixed **there, before this ran**. Same standing as C8: a counting
question that settles a construction choice, asked against the file rather than
against a result. **Computes no ``omega`` and reads no prediction.**

Two questions, one measurement::

    C10-1  on the 34,621 loops where `t_M == t_B`, did field 9 or field 17 move
           on that row?                                       -> settles O26
    C10-2  on the 8,073 two-arm candidates, did field 9 or field 17 move on the
           row a deferred balance first appeared?             -> settles O27
    C10-3  the same two arms, **cut by window rather than by cohort**, because
           C10-2's control turned out not to be one           -> retries O27

C10-3 exists because C10-2's control failed. It was registered as "a COVID
payment deferral leaves rate and term alone", and it read 0.9191 to 0.9964. The
baseline was not the problem: the same test reads 0.0000 on 919,207 clean-cure
rows. So the population is the problem, and §14.4 already says why it might be
one, "Deferral exists only in the COVID window". **A field-63 onset outside that
window is not a payment deferral, and an acquisition quarter is not a window.**
The reading was fixed in §6.6.8.6 before this ran.

--------------------------------------------------------------------------
The three indicators, and the one that is easy to get backwards
--------------------------------------------------------------------------

At row ``r``, against ``r-1`` of the same loan:

``rate_move``  field 9 differs. **Both sides must be present.** Pit 25: a blank
               note rate is stored as the 65535 sentinel, and comparing it
               straight fires two spurious moves, which is what shattered
               968,761 loans into 1,944,756 contract periods.

``term_move``  field 17 **is not the previous value minus one**. Amortisation
               takes a month off every month, so "unchanged" is *minus one*, not
               *equal*. Writing ``!=`` here calls every ordinary month a term
               change, and the error is silent because the number it produces is
               large and plausible.

``upb_jump``   field 12 rises. C8-4 confirmed the balance steps up at the
               modification month (45,664 / 52,423) as arrears capitalise.

Field 18 is not used: pit 2, it goes blank at the modification month and does
not come back. Field 9 is read **after** ``b8_omega.fill_within_loan``, matching
``contract_periods``; the count of rows undecidable on the raw column is printed
beside it, because that is exactly where pit 25 lives.

--------------------------------------------------------------------------
Arms, and why one of them is a floor rather than a control
--------------------------------------------------------------------------

C10-1 has a **floor**, not a control: ``find_clean_cures``'s cure rows carry no
modification and no deferred balance anywhere in their window, so the contract
cannot have moved there. Whatever they read is reporting noise, and the reading
is a multiple of it. That is §6.2.11.4's shape.

C10-2 has a **control**: the pure deferral arm. A COVID payment deferral moves
the balance to a zero-interest balloon and leaves rate and term alone, so its
rate of movement is what "a deferral and nothing else" looks like on this file.

Usage::

    python experiments/b8_c10_contract_move.py selftest    # no real archive
    python experiments/b8_c10_contract_move.py run
    python experiments/b8_c10_contract_move.py run --only 2019Q1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_0a_gate as G  # noqa: E402
import b8_core as K  # noqa: E402
import b8_loops as L  # noqa: E402
import b8_omega as W  # noqa: E402
import b8_triangles as T  # noqa: E402

OUT = K.ROOT / "results" / "b8_c10_contract_move.md"

#: **The column list `run` opens the core table with.** The selftest opens the
#: fixture with this same list rather than with the default of every column,
#: because a selftest that reads columns the run path does not request cannot
#: see a missing entry here. That is exactly how `defer_amt` reached a real run
#: as a `KeyError`: it was added to `find_loops` and to this module's clean-cure
#: count, the selftest passed on an all-columns Core, and the census died.
COLS = ["period", "rate", "upb", "rem_legal", "delinq", "mod_flag", "nib_upb",
        "defer_amt"]

#: Taken from ``b8_triangles.WINDOWS``, **not re-typed**. §6 registers four
#: windows and the audit's table carries a fifth, `post-2022`; all five are
#: printed and the fifth is labelled, rather than quietly folding it into COVID
#: or dropping it. §16.15's rule is that the triangle criterion has one copy,
#: and the window bounds travel with it.
WINDOWS = T.WINDOWS

#: `b2_measurement.md` §10's floor, the same one C9 applies. A cell below it is
#: **printed with its count and marked unreadable**, not dropped: pit 22, a
#: minimum without its load cannot be read.
MIN_CELL = 20


def contract_move(c: K.Core, rows: np.ndarray, rate_f: np.ndarray) -> dict:
    """The three indicators on ``rows``, each against the preceding row.

    A row whose predecessor belongs to another loan, or whose reporting period
    is not one month later, is **undecidable and is counted rather than
    defaulted to "did not move"**. Silently calling an undecidable row unmoved
    is how a rate of movement gets biased toward zero, and zero is one of the
    two answers this measurement is choosing between.
    """
    if rows.size == 0:
        return {"n": 0, "decidable": 0, "rate": 0, "term": 0, "upb": 0,
                "any": 0, "still": 0, "rate_raw_blank": 0, "undecidable": 0}
    prv = rows - 1
    loan = c.loan_of_row()
    period = c.row["period"][:].astype(np.int64)
    rate_raw = c.row["rate"][:]
    rem = c.row["rem_legal"][:].astype(np.int64)
    upb = c.row["upb"][:].astype(np.int64)

    same = (prv >= 0) & (loan[np.maximum(prv, 0)] == loan[rows])
    step = same & (period[rows] - period[np.maximum(prv, 0)] == 1)

    rate_ok = step & (rate_f[rows] != K.U16_NA) & (rate_f[prv] != K.U16_NA)
    rem_ok = step & (rem[rows] != K.U16_NA) & (rem[prv] != K.U16_NA)
    upb_ok = step & (upb[rows] != K.U32_NA) & (upb[prv] != K.U32_NA)

    rate_mv = rate_ok & (rate_f[rows] != rate_f[prv])
    term_mv = rem_ok & (rem[rows] != rem[prv] - 1)
    upb_mv = upb_ok & (upb[rows] > upb[prv])

    return {
        "n": int(rows.size),
        "decidable": int(step.sum()),
        "undecidable": int((~step).sum()),
        "rate": int(rate_mv.sum()),
        "term": int(term_mv.sum()),
        "upb": int(upb_mv.sum()),
        "any": int((rate_mv | term_mv).sum()),
        # **The conjunction, as its own number.** §14.4's definition of a
        # deferral is "unchanged maturity AND rate and term left alone", and
        # reading one of those two columns and declaring the shape is pit 29,
        # committed on this very table. `still` is both conditions holding at
        # once, so no reader has to conjoin two columns by eye. An indicator
        # that could not be judged does not fire, so it counts as "did not
        # move"; `undecidable` and `rate_raw_blank` bound that.
        "still": int((step & ~(rate_mv | term_mv)).sum()),
        "rate_raw_blank": int((step & ((rate_raw[rows] == K.U16_NA)
                                       | (rate_raw[prv] == K.U16_NA))).sum()),
    }


def window_of(c: K.Core, rows: np.ndarray) -> np.ndarray:
    """Window index per row, from **that row's** reporting month.

    Not from the loan's acquisition quarter. A loan originated in 2002Q1 can
    take a COVID deferral in 2020, so the cohort is not the window, and reading
    C10-2's per-archive split as a window split is the inference §6.6.8.5
    refuses to make.
    """
    period = c.row["period"][:].astype(np.int64)
    out = np.full(rows.size, -1, dtype=np.int8)
    if rows.size == 0:
        return out
    mi = period[rows]
    known = mi != K.U16_NA
    for k, (_name, lo, hi) in enumerate(WINDOWS):
        out = np.where(known & (out < 0)
                       & (mi >= T._to_month_index(lo))
                       & (mi <= T._to_month_index(hi)), k, out)
    return out


def by_window(c: K.Core, rows: np.ndarray, rate_f: np.ndarray,
              extra: np.ndarray | None = None) -> list[dict]:
    """``contract_move`` per window, plus an optional per-window share.

    The per-window rows must partition the arm exactly. That is asserted rather
    than trusted: a window table that silently drops a row reports a rate on a
    denominator nobody can reconstruct.
    """
    win = window_of(c, rows)
    out = []
    for k, (name, _lo, _hi) in enumerate(WINDOWS):
        sel = win == k
        d = contract_move(c, rows[sel], rate_f)
        d["window"] = name
        d["readable"] = d["decidable"] >= MIN_CELL
        if extra is not None:
            d["extra"] = int(extra[sel].sum())
        out.append(d)
    unwin = contract_move(c, rows[win < 0], rate_f)
    unwin["window"] = "no reporting month"
    unwin["readable"] = False
    if extra is not None:
        unwin["extra"] = int(extra[win < 0].sum())
    out.append(unwin)
    assert sum(d["n"] for d in out) == rows.size, \
        "the window table does not partition the arm"
    return out


def measure(c: K.Core) -> dict:
    start, end = W._row_bounds(c)
    rate_f = W.fill_within_loan(c.row["rate"][:], K.U16_NA, start, end)

    lp = L.find_loops(c)
    same_row = lp["t_M"] == lp["t_B"]
    a = {
        # C10-1
        "A": contract_move(c, lp["t_B"][same_row], rate_f),
        "B": contract_move(c, lp["t_M"][~same_row], rate_f),
    }
    # **The floor uses the corrected sample** (field 108 excluded, O28's fix of
    # 2026-08-17). The legacy sample is computed alongside so the contamination
    # this file first surfaced stays reproducible here; the **verdict** on it
    # lives in `b8_0a_gate`, not here.
    t0, _st, cure_end, _k, _drops = G.find_clean_cures(c)
    a["floor"] = contract_move(c, cure_end, rate_f)
    t0L, _stL, cure_L, _kL, _drL = G.find_clean_cures(c, require_no_defer=False)

    # **`find_clean_cures` excludes a modification flag and a positive field 63
    # from its window, and says nothing about field 108.** Before C10-4 nobody
    # had looked at field 108, so the omission could not show. It surfaced here
    # as a fixture loan carrying only a field-108 deferral being admitted as a
    # clean cure. That is pit 14 exactly: a property held by a lucky
    # precondition breaks at the first station that does not carry it.
    #
    # **This is counted, not fixed.** B8-0a(i-a) has already run on this
    # population and passed; changing the sample here would re-base a gate
    # without the double report R01 requires. The count is what a ruling needs.
    dfr = c.row["defer_amt"][:].astype(np.int64)
    dpos = (dfr != K.U32_NA) & (dfr > 0)
    pref = np.concatenate(([0], np.cumsum(dpos.astype(np.int64))))
    inwin = pref[cure_L + 1] - pref[t0L]
    a["clean_cures"] = int(cure_L.size)
    a["clean_cures_with_defer"] = int((inwin > 0).sum())
    a["clean_cures_corrected"] = int(cure_end.size)
    # the corrected sample must carry none, by construction. Asserted rather
    # than trusted: if it does, the fix is not doing what it says.
    inwin_c = pref[cure_end + 1] - pref[t0]
    a["corrected_with_defer"] = int((inwin_c > 0).sum())

    # C10-2. `defer_row` is `n_rows + 1` where the run carried no deferral
    # onset, which is every loop on the modification arm. **The column behind
    # it changed from field 63 to field 108 when C10-4 settled O27**, so these
    # arms are not comparable across that boundary; the pre-C10-4 results file
    # is kept as `.expired_20260817_pre_C10-4` for the diff.
    excl = lp["excluded_two_arms"]
    nib_c = excl["defer_row"]
    mod_c = excl["mod_row"]
    valid = (nib_c <= c.n_rows) & (mod_c <= c.n_rows)
    a["C"] = contract_move(c, nib_c[valid], rate_f)
    a["C_same_row"] = int((nib_c[valid] == mod_c[valid]).sum())
    a["C_nib_first"] = int((nib_c[valid] < mod_c[valid]).sum())
    a["C_mod_first"] = int((nib_c[valid] > mod_c[valid]).sum())
    a["C_valid"] = int(valid.sum())

    pure = lp["arm"] == L.ARM_DEFER
    nib_p = lp["defer_row"][pure]
    nib_p = nib_p[nib_p <= c.n_rows]
    a["control"] = contract_move(c, nib_p, rate_f)

    # C10-3
    a["C_win"] = by_window(c, nib_c[valid], rate_f,
                           extra=(nib_c[valid] == mod_c[valid]))
    a["control_win"] = by_window(c, nib_p, rate_f)

    a["loops"] = lp["counts"]["loops"]
    a["same_row_loops"] = int(same_row.sum())
    a["leg3_loops"] = int((~same_row).sum())
    return a


def _rate(d: dict, k: str) -> float:
    return d[k] / d["decidable"] if d["decidable"] else float("nan")


def _fmt(d: dict, k: str) -> str:
    """A rate, or an explicit `not measurable` on an empty arm.

    Pit 23, and pit 26 which is the same defect surviving a partial fix: an
    empty arm's rate must not print as `0.0000`, which is what "measured and
    nothing moved" also prints.
    """
    return "not measurable" if not d["decidable"] else f"{_rate(d, k):.4f}"


def render(rows: list[dict]) -> str:
    out, A = [], None
    out.append("# C10: did the contract move at the re-contracting row\n")
    A = out.append
    A("Generated by `experiments/b8_c10_contract_move.py`. **The reading was "
      "fixed in `docs/b8_inputs_availability.md` §6.6.7 before this ran**, "
      "which is C8's standing and §8's rule: the map from outcome to "
      "disposition is written first and is not revisited afterwards.\n")
    A("**Computes no `omega` and reads no prediction.**\n")
    A("\n`term_move` is field 17 **not equal to the previous value minus "
      "one**. Amortisation removes a month every month, so *unchanged* is "
      "*minus one*. `rate_move` requires both sides present, per pit 25.\n")

    A("\n## 1. C10-1: the `t_M == t_B` row, against the leg-3 arm and the "
      "noise floor\n")
    A("**A** is the 34,621 loops in question, measured at `t_B`. **B** is the "
      "leg-3-non-empty loops at `t_M`, which are known to be re-contractings "
      "inside a delinquency. **floor** is `find_clean_cures`'s cure rows, "
      "where no modification and no deferred balance exists anywhere in the "
      "window, so the contract **cannot** have moved: whatever it reads is "
      "reporting noise.\n")
    A("| archive | arm | rows | decidable | rate | term | **any (9 or 17)** | "
      "upb up | **x floor** |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        fl = _rate(r["floor"], "any")
        for k, label in (("A", "A `t_M == t_B`"), ("B", "B leg 3 non-empty"),
                         ("floor", "floor clean cure")):
            d = r[k]
            mult = ("-" if k == "floor" or not np.isfinite(fl) or fl == 0
                    else f"**{_rate(d, 'any') / fl:.1f}**")
            A(f"| {r['name']} | {label} | {d['n']:,} | {d['decidable']:,} | "
              f"{_fmt(d, 'rate')} | {_fmt(d, 'term')} | "
              f"**{_fmt(d, 'any')}** | {_fmt(d, 'upb')} | {mult} |")

    A("\n## 2. C10-2: the row a deferred balance first appeared\n")
    A("**C** is the two-arm population §17.4 excludes, measured at the field-63 "
      "onset. **control** is the pure deferral arm at the same kind of row: a "
      "COVID payment deferral leaves rate and term alone, so this is what "
      "\"a deferral and nothing else\" reads on this file.\n")
    A("| archive | arm | rows | decidable | rate | term | **any (9 or 17)** | "
      "upb up | **x control** |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        ct = _rate(r["control"], "any")
        for k, label in (("C", "C two-arm"), ("control", "control pure defer")):
            d = r[k]
            mult = ("-" if k == "control" or not np.isfinite(ct) or ct == 0
                    else f"**{_rate(d, 'any') / ct:.1f}**")
            A(f"| {r['name']} | {label} | {d['n']:,} | {d['decidable']:,} | "
              f"{_fmt(d, 'rate')} | {_fmt(d, 'term')} | "
              f"**{_fmt(d, 'any')}** | {_fmt(d, 'upb')} | {mult} |")

    A("\n### 2.1 The more direct signal: where the two onsets sit\n")
    A("If a modification with principal forbearance is one event, field 42 and "
      "field 63 rise on the **same row**. If they are two events, they do not.\n")
    A("| archive | two-arm runs | **63 and 42 same row** | share | 63 first | "
      "42 first |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        v = r["C_valid"]
        sh = f"{r['C_same_row'] / v:.4f}" if v else "not measurable"
        A(f"| {r['name']} | {v:,} | **{r['C_same_row']:,}** | **{sh}** | "
          f"{r['C_nib_first']:,} | {r['C_mod_first']:,} |")

    A("\n### 1.1 The floor's sample, before and after O28's correction\n")
    A("This file first surfaced that `find_clean_cures` excluded a modification "
      "flag and a positive field 63 and **said nothing about field 108**. That "
      "was corrected on 2026-08-17 (§6.6.17); **the floor above now uses the "
      "corrected sample**, and the legacy figures are kept here so the "
      "contamination stays reproducible. **The verdict on B8-0a lives in "
      "`b8_0a_gate`, not here.** Pit 14's shape.\n")
    A("| archive | legacy clean cures | **with a field-108 deferral** | share | "
      "**corrected** | corrected still carrying one |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        n, k = r["clean_cures"], r["clean_cures_with_defer"]
        A(f"| {r['name']} | {n:,} | **{k:,}** | "
          f"{(k / n if n else float('nan')):.4f} | "
          f"**{r['clean_cures_corrected']:,}** | {r['corrected_with_defer']:,} |")

    A("\n## 3. C10-3: the same two arms cut by window, not by cohort\n")
    A("**C10-2's control failed.** It was registered as \"a COVID payment "
      "deferral leaves rate and term alone\" and read 0.9191 to 0.9964. The "
      "baseline is not the problem: the same test reads 0.0000 on 919,207 "
      "clean-cure rows. §14.4 says deferral exists only in the COVID window, "
      "so the window is cut **from each onset row's own reporting month**. An "
      "acquisition quarter is not a window: a 2002Q1 loan can take a COVID "
      "deferral in 2020, which is why the per-archive split of §2 is not a "
      "window reading.\n")
    A(f"Cells below {MIN_CELL} decidable rows (`b2_measurement.md` §10, the "
      "floor C9 uses) are printed with their counts and marked **NO**, not "
      "dropped. Window bounds come from `b8_triangles.WINDOWS`, not re-typed; "
      "§6 registers four and that table carries a fifth, `post-2022`, which is "
      "printed as itself rather than folded into COVID.\n")

    A("\n### 3.1 control, the pure-deferral arm: `rate` is the column to read\n")
    A("A payment deferral moves the balance to a balloon and leaves the note "
      "rate alone. **If that shape appears inside COVID and not outside it, "
      "§14.3 and §14.4 are each right in their own window.**\n")
    A("| archive | window | rows | decidable | **rate** | term | any | "
      "readable |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        for d in r["control_win"]:
            if not d["n"]:
                continue
            A(f"| {r['name']} | {d['window']} | {d['n']:,} | "
              f"{d['decidable']:,} | **{_fmt(d, 'rate')}** | "
              f"{_fmt(d, 'term')} | {_fmt(d, 'any')} | "
              f"{'yes' if d['readable'] else '**NO**'} |")

    A("\n### 3.2 C, the two-arm population, same cut\n")
    A(f"`same row` is how often the deferral onset (field {L.DEFER_FIELD}) and "
      f"the modification onset (field {L.MOD_FIELDS}) fall on the same row "
      "inside that window.\n")
    A("| archive | window | rows | decidable | rate | term | any | same row | "
      "share | readable |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        for d in r["C_win"]:
            if not d["n"]:
                continue
            sh = f"{d['extra'] / d['n']:.4f}"
            A(f"| {r['name']} | {d['window']} | {d['n']:,} | "
              f"{d['decidable']:,} | {_fmt(d, 'rate')} | {_fmt(d, 'term')} | "
              f"{_fmt(d, 'any')} | {d['extra']:,} | {sh} | "
              f"{'yes' if d['readable'] else '**NO**'} |")

    A("\n### 3.3 Where the deferral onsets actually sit\n")
    A("§14.4 states deferral exists only in the COVID window. **This is that "
      "sentence as a count**, pooled over archives.\n")
    wn = [w[0] for w in WINDOWS] + ["no reporting month"]
    A("| arm | " + " | ".join(wn) + " |")
    A("|---" * (len(wn) + 1) + "|")
    for key, lab in (("control_win", "control pure defer"),
                     ("C_win", "C two-arm")):
        tot = {w: 0 for w in wn}
        for r in rows:
            for d in r[key]:
                tot[d["window"]] += d["n"]
        A(f"| {lab} | " + " | ".join(f"{tot[w]:,}" for w in wn) + " |")

    A("\n## 4. Undecidable rows, printed rather than folded into \"unmoved\"\n")
    A("A row whose predecessor is in another loan, or is not one month back, "
      "cannot be compared. **Calling those unmoved biases the rate toward zero, "
      "and zero is one of the two answers being chosen between.**\n")
    A("| archive | arm | undecidable | of rows | raw field 9 blank (pit 25) |")
    A("|---|---|---|---|---|")
    for r in rows:
        for k in ("A", "B", "floor", "C", "control"):
            d = r[k]
            sh = f"{d['undecidable'] / d['n']:.4f}" if d["n"] else "-"
            A(f"| {r['name']} | {k} | {d['undecidable']:,} | {sh} | "
              f"{d['rate_raw_blank']:,} |")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`.** C10 is a count.\n")
    A("- **It does not change §17's window.** Whatever the reading, the window "
      "rule is unchanged; what moves is arm attribution and reporting.\n")
    A(f"- The deferral onset is cut on **field {L.DEFER_FIELD}** and the "
      f"modification onset on **field {L.MOD_FIELDS}**, both read from "
      "`b8_loops` rather than typed here, so this line cannot go stale the way "
      "it did when the column changed and this block kept saying field 63. "
      "C10-4 (§6.6.11) settled that choice; O24 and B10 §19.9 remain open on "
      "the payment estimator.\n")
    A("- It reads no prediction.\n")
    return "\n".join(out) + "\n"


def run(names: list[str]) -> int:
    rows = []
    for name in names:
        with K.Core(name, cols=COLS, loan_cols=[]) as c:
            a = measure(c)
        a["name"] = name
        rows.append(a)
        print(f"  {name}: A any={_fmt(a['A'], 'any')} "
              f"B any={_fmt(a['B'], 'any')} floor={_fmt(a['floor'], 'any')} | "
              f"C any={_fmt(a['C'], 'any')} "
              f"control={_fmt(a['control'], 'any')} "
              f"same-row={a['C_same_row']:,}/{a['C_valid']:,}",
              file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    """``contract_move`` on a hand-built table, plus the whole path on
    ``b8_loops``'s fixture.

    The indicator test is the one that matters: **an ordinary amortising month
    must read `term_move = 0`**, and a version that compares field 17 for
    equality reads it as a move on every single row.
    """
    fails = []

    class Fake:
        """The smallest thing ``contract_move`` accepts: two loans of four rows."""
        n_rows = 8
        n_loans = 2
        row_start = np.array([0, 4], dtype=np.int64)
        n_per_loan = np.array([4, 4], dtype=np.int64)

        def __init__(self, period, rate, rem, upb):
            self.row = {"period": np.array(period, dtype=np.int64),
                        "rate": np.array(rate, dtype=np.uint16),
                        "rem_legal": np.array(rem, dtype=np.uint16),
                        "upb": np.array(upb, dtype=np.uint32)}

        def loan_of_row(self):
            return np.repeat(np.arange(2, dtype=np.int64), 4)

    NA16, NA32 = K.U16_NA, K.U32_NA
    f = Fake(
        period=[100, 101, 102, 103, 200, 201, 202, 203],
        #      loan 0: ordinary, ordinary, RATE moves, TERM extends
        #      loan 1: ordinary, UPB jumps, blank rate, ordinary
        rate=[5000, 5000, 4000, 4000, 5000, 5000, NA16, 5000],
        rem=[360, 359, 358, 400, 300, 299, 298, 297],
        upb=[200000, 199000, 198000, 197000, 100000, 101000, 100500, 100000],
    )
    rate_f = np.array(f.row["rate"], dtype=np.uint16)      # unfilled, on purpose

    m = contract_move(f, np.array([1, 5]), rate_f)          # ordinary months
    if m["term"] != 0:
        fails.append("an ordinary amortising month reads term_move; field 17 "
                     "is being compared for equality instead of minus one")
    if m["rate"] != 0:
        fails.append("an ordinary month reads rate_move")
    if m["decidable"] != 2:
        fails.append(f"ordinary months decidable={m['decidable']}, expected 2")

    m = contract_move(f, np.array([2]), rate_f)             # the rate move
    if not (m["rate"] == 1 and m["term"] == 0 and m["any"] == 1):
        fails.append(f"rate-move row read {m}")

    m = contract_move(f, np.array([3]), rate_f)             # the term extension
    if not (m["term"] == 1 and m["rate"] == 0 and m["any"] == 1):
        fails.append(f"term-extension row read {m}")

    m = contract_move(f, np.array([5]), rate_f)             # the UPB jump
    if m["upb"] != 1:
        fails.append(f"upb-jump row read upb={m['upb']}, expected 1")

    m = contract_move(f, np.array([6]), rate_f)             # blank rate
    if m["rate"] != 0:
        fails.append("a blank field 9 reads as a rate move; pit 25 is back")
    if m["rate_raw_blank"] != 1:
        fails.append(f"rate_raw_blank={m['rate_raw_blank']}, expected 1")

    m = contract_move(f, np.array([4]), rate_f)             # loan 1's first row
    if m["decidable"] != 0 or m["undecidable"] != 1:
        fails.append(f"a loan's first row must be undecidable, read {m}")
    if _fmt(m, "any") != "not measurable":
        fails.append("an empty arm prints a rate instead of `not measurable`")

    # `window_of` on hand-computed month indices, one per window plus a blank.
    # **The loop fixture is entirely inside HAMP**, so without this the window
    # assignment would be exercised on one value and a wrong bound would pass.
    # Same failure the arm values had one round ago.
    class Periods:
        def __init__(self, v):
            self.row = {"period": np.array(v, dtype=np.uint16)}

    def mi(y, m):
        return (y - K.EPOCH_YEAR) * 12 + (m - 1)

    want = [("2005-06", mi(2005, 6), 0), ("2008-12", mi(2008, 12), 0),
            ("2009-01", mi(2009, 1), 1), ("2010-03", mi(2010, 3), 1),
            ("2016-12", mi(2016, 12), 1), ("2017-01", mi(2017, 1), 2),
            ("2018-07", mi(2018, 7), 2), ("2019-12", mi(2019, 12), 2),
            ("2020-01", mi(2020, 1), 3), ("2021-01", mi(2021, 1), 3),
            ("2022-12", mi(2022, 12), 3), ("2023-01", mi(2023, 1), 4),
            ("2024-05", mi(2024, 5), 4)]
    stub = Periods([v for _lab, v, _w in want] + [K.U16_NA])
    got = window_of(stub, np.arange(len(want) + 1))
    for k, (lab, _v, w) in enumerate(want):
        if int(got[k]) != w:
            fails.append(f"window_of({lab}) = {int(got[k])}, expected {w} "
                         f"({WINDOWS[w][0]})")
    if int(got[-1]) != -1:
        fails.append("a blank reporting month must not land in a window")
    if len(set(int(x) for x in got[:-1])) != 5:
        fails.append("the window test does not reach all five windows")

    # the whole path, on the loop fixture. It exercises `measure` end to end,
    # which is where a wrong dict key would otherwise wait for a real archive.
    tag = L._fixture_tag()
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{tag}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    K.build_archive(zp, force=True, cache_root=root / "cache")
    # opened with COLS, not with every column: see the note on COLS
    with K.Core(zp.stem, cols=COLS, loan_cols=[],
                cache_root=root / "cache") as c:
        a = measure(c)
    for k in ("A", "B", "floor", "C", "control"):
        print(f"  {k:8} n={a[k]['n']:>3} decidable={a[k]['decidable']:>3} "
              f"any={_fmt(a[k], 'any')}", file=sys.stderr)
    if a["A"]["n"] != 1:
        fails.append(f"fixture arm A has {a['A']['n']} rows, expected 1")
    if a["C"]["n"] != 2:
        fails.append(f"fixture arm C has {a['C']['n']} rows, expected 2")
    if a["control"]["n"] != 1:
        fails.append(f"fixture control has {a['control']['n']} rows, expected 1")

    # **The arms must read different numbers.** The first version of this test
    # passed with every arm at 0.0000, because the fixture never moved a
    # contract: it proved the code runs, not that the rows reach the right arm.
    # Pit 19: a check that does not require the two sides to differ is a free
    # pass. The fixture now carries a rate move on the `t_M == t_B` row, a rate
    # and term move on one leg-3 row, a rate blip on one clean-cure row, and
    # nothing on the pure deferral, so each arm has its own expected value.
    # Re-pinned twice, each time because a ruling landed, not because the test
    # was inconvenient. C10-4 moved the deferral arm onto field 108, which put
    # `nib_is_modification` into arm B. **O28's fix then removed
    # `defer_triangle` from the floor**, which is the correction working: a
    # window carrying a payment deferral is not a clean cure. The floor went
    # from 4 rows to 3 and its value from 1/4 to 1/3. Pinned, not loosened.
    # **Re-pinned a third time, 2026-08-17.** `b8_loops` gained a second
    # two-arm case (`two_arms_defer_first`), because one was not enough to
    # check the §17.4 population downstream. Its deferral onset moves neither
    # the rate nor the term, which is what C10-4 says a field-108 onset does
    # (`still = 0.9966`), while `two_arms`' onset row also carries a rate cut.
    # So arm C now holds one moving row and one still one and reads 1/2.
    # **Sharper than before, not looser**: the old single row pinned an
    # average of one number, and two rows that differ pin both of them.
    want = {"A": 1.0, "B": 1 / 6, "floor": 1 / 3, "C": 1 / 2, "control": 0.0}
    for k, w in want.items():
        got = _rate(a[k], "any")
        if not np.isclose(got, w):
            fails.append(f"fixture arm {k} reads {got:.4f}, expected {w:.4f}; "
                         "the rows reaching this arm are not the intended ones")
    if len(set(round(_rate(a[k], "any"), 6) for k in want)) < 4:
        fails.append("the fixture's arms do not separate, so a mis-wired arm "
                     "would pass unnoticed")
    # the per-window tables must partition their arm. `by_window` asserts it,
    # so reaching here at all is the check; the totals are compared anyway
    # because an assert inside a helper is easy to delete.
    for key, arm in (("C_win", "C"), ("control_win", "control")):
        if sum(d["n"] for d in a[key]) != a[arm]["n"]:
            fails.append(f"{key} does not partition arm {arm}")
    # **`render` must not merely not raise: it must contain every section.**
    # The C10-3 section was added to `measure` and its edit to `render` silently
    # did nothing (a string-replace whose target had escaped quotes). `measure`
    # computed the window tables, `render` never printed them, the selftest
    # checked only that `render` did not raise, and a results file went out with
    # the section missing. **A check that a function runs is not a check that
    # its output is complete.**
    txt = render([dict(a, name="fixture")])
    # every table's rows must match its header's width. A published
    # results file was malformed on 2026-08-17 and the person who
    # generated it read it and quoted from it without noticing.
    for _c in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {_c}")
    if a["clean_cures_with_defer"] < 1:
        fails.append("the legacy sample carries no field-108 clean cure, so "
                     "the contamination count is untested")
    if a["corrected_with_defer"] != 0:
        fails.append(f"the corrected sample still carries "
                     f"{a['corrected_with_defer']} field-108 clean cures; "
                     "O28's fix is not doing what it says")
    if a["clean_cures_corrected"] >= a["clean_cures"]:
        fails.append("the correction removed nothing on this fixture")
    if f"field {L.DEFER_FIELD}" not in txt:
        fails.append("the results file never names the deferral column in use")
    if "Field 63 is used" in txt:
        fails.append("the results file still claims field 63 is the deferral "
                     "column; the disclaimer went stale")
    for need in ("## 1. C10-1", "### 1.1 The floor's sample",
                 "## 2. C10-2", "### 2.1", "## 3. C10-3",
                 "### 3.1", "### 3.2", "### 3.3", "## 4. Undecidable"):
        if need not in txt:
            fails.append(f"render omits the section `{need}`")

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
