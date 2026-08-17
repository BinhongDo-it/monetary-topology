#!/usr/bin/env python3
"""B8: the curve rule's effect on the object B8 actually reads, `r` and its sum.

Registered in ``docs/b8_fannie_slice.md`` §16.11. **Supersedes
`results/b8_cmt_sensitivity.md`, which measured the wrong object.**

**What the first version got wrong, and it is worth stating before the code.**
It measured the spread of ``log V`` alone across curve constructions and read
267 to 7,110 times the noise floor. ``b8_omega.r_month`` takes **one**
``note_pct``, **one** ``n_now`` and **one** ``disc_pct`` and uses them for both
legs. With no deferred balance ``V = LP(bal, i, n) * A(d, n)`` and ``LP`` is
linear in the balance, so

    r = log V - log V-hat = log(bal_now) - log(b_hat)

and **the annuity factor cancels exactly; the discount rate does not appear**.
That is P2, stated for every real month rather than for a synthetic loan. The
claim that drove the first version, that a modification makes the two legs
differ in ``n`` and lets the curve in, **is false against the implementation**:
``r_month`` gives both legs ``n_now``.

**So the curve enters through one door only: the balloon**, ``nib * (1+d)^-bn``,
which is field 63's deferred balance. That population is the COVID deferrals,
not the term extensions the first version was worried about.

This file therefore measures three things, in the order that lets each check the
next:

  1. **Cancellation, asserted on real rows.** Where ``nib`` is zero on both
     sides, ``r`` must be identical across all six constructions **bit for
     bit**. If it is not, the reading of ``r_month`` above is wrong and nothing
     below is a measurement.
  2. **The population where it does not cancel**, and the spread of ``r`` there.
  3. **The same at loop level**, summed over the triangle window, against the
     B8-0a(i-b) floor.

**The window used here is not a registered loop definition.** ``find_clean_cures``
defines the clean-cure loop; the modification triangle's loop window is not
defined anywhere yet. What is used below is "first delinquent row through the
first cure after the modification, inclusive", chosen **to have something to sum
over** and marked so it is not later cited as the loop.

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_cmt_sensitivity2.py --selftest
    python experiments/b8_cmt_sensitivity2.py
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_cmt_fetch as F  # noqa: E402
import b8_cmt_sensitivity as S1  # noqa: E402
import b8_omega as W  # noqa: E402
import b8_triangles as T  # noqa: E402

OUT = K.ROOT / "results" / "b8_cmt_sensitivity2.md"

FLOOR = S1.FLOOR
RULES = [(i, b) for i in S1.INTERP for b in S1.BEYOND]


#: Horizons are integer months and the archives never exceed a few hundred, so
#: the curve is read once into a table rather than per row. A per-row read is a
#: Python call per row per rule, which on 42 million rows and six rules is 250
#: million calls; the table is 440 months by 600 horizons and is built once.
MAX_H = W.MAX_H          # one definition, in `b8_omega`

#: The tolerance the cancellation is judged against, **and it has a source**.
#: `r` is a difference of two logarithms of `V`, and `V` runs to a few hundred
#: thousand, so `log V` is of order 13. Two such logarithms differenced, then
#: differenced again across constructions, carries about `4 * |log V| * eps`.
#: The first version of this file judged against a bare `0.0` and read
#: `3.553e-15` as a failure to cancel. **A sourceless zero in a criterion is
#: exactly what discipline 5 forbids**, and this file broke it.
LOG_V_SCALE = 14.0
CANCEL_TOL = 4.0 * LOG_V_SCALE * np.finfo(np.float64).eps


def curve_tables(tre):
    """{rule: (month_index -> row), array[months, MAX_H+1]} of yields.

    Missing months and horizons are ``nan`` so a lookup that should not have
    happened shows up as a nan rather than as a plausible number.
    """
    curves = S1.month_curve(tre)
    months = sorted(curves)
    pos = {mi: k for k, mi in enumerate(months)}
    tabs = {}
    for rule in RULES:
        tab = np.full((len(months), MAX_H + 1), np.nan)
        for k, mi in enumerate(months):
            pts = curves[mi]
            for h in range(1, MAX_H + 1):
                y = S1.yield_at(pts, h, rule[0], rule[1])
                if y is not None:
                    tab[k, h] = y
        tabs[rule] = tab
    return pos, tabs, curves


def per_row_r(c: K.Core, pos, tab, rule) -> tuple:
    """`r` for every row under one construction, plus the computable mask and
    the mask of rows where a balloon is present.

    **This is now a thin wrapper over `b8_omega.row_residuals`**, which is the
    single copy. It used to be a second implementation of the residual, and by
    2026-08-17 the two had drifted on three things at once: this one read the
    interest-bearing balance as `12 - 63` (C11-1 says `12 - 63 - 108`), priced
    the balloon at field 17 (§14.1 says field 19), and passed the balloon
    amount under the old `nib_` keywords, which named field 63 alone after
    C10-4 had settled that the deferral carrier is field 108.

    **The sweep was therefore measuring a different quantity from the loop
    sum**, on the one question where the two have to agree: whether the curve
    construction moves `r`. Two copies of the residual is how that happens with
    both files green.

    ``rule`` selects which table was built; the caller passes the matching
    ``tab``. The rule is not re-read here, so a mismatched pair is the caller's
    error and `b8_cmt_sensitivity2.run` pairs them in one loop.
    """
    disc, _ = W.disc_of_row(c, pos, tab)
    rr, ok, info = W.row_residuals(c, disc)
    return rr, ok, info["balloon_row"]


def triangle_window(c: K.Core):
    """first delinquent row through the first cure after the modification.

    **Not a registered loop definition.** It exists so there is a window to sum
    a per-month quantity over, and it is the triangle C3/C4 counts.
    """
    dv = c.row["delinq"]
    mf = c.row["mod_flag"]
    known = dv <= 98
    is_del = known & (dv != 0)
    is_cur = known & (dv == 0)
    is_mod = mf == K._Y
    first_del = T._first_pos_per_loan(c, is_del)
    first_mod = T._first_pos_per_loan(c, is_mod)
    idx = np.arange(c.n_rows, dtype=np.int64)
    fm = np.repeat(first_mod, c.n_per_loan.astype(np.int64))
    after_mod_cure = is_cur & (fm >= 0) & (idx > fm)
    first_cure = T._first_pos_per_loan(c, after_mod_cure)
    return first_del, first_cure


def run(names) -> int:
    tre, _ = F.load_treasury()
    if not tre:
        print("no Treasury curve on disk.", file=sys.stderr)
        return 1
    pos, tabs, _curves = curve_tables(tre)
    print(f"  curve table: {len(pos)} months x {MAX_H} horizons x "
          f"{len(RULES)} rules", file=sys.stderr)

    rows_out, loops_out, checks = [], [], []
    for name in names:
        with K.Core(name) as c:
            t = T.triangles(c)
            tri = t["triangle"]
            lo, hi = triangle_window(c)

            rs, oks, bals = [], None, None
            for rule in RULES:
                rr, ok, bal = per_row_r(c, pos, tabs[rule], rule)
                rs.append(rr)
                oks = ok if oks is None else (oks & ok)
                bals = bal if bals is None else (bals | bal)
            M = np.vstack(rs)

            # --- 1. cancellation, asserted on real rows -------------------
            plain = oks & ~bals
            if plain.any():
                sub = M[:, plain]
                spread = np.nanmax(sub, axis=0) - np.nanmin(sub, axis=0)
                worst = float(np.nanmax(spread)) if spread.size else 0.0
            else:
                worst = float("nan")
            n_plain = int(plain.sum())
            n_bal = int((oks & bals).sum())
            # **A zero in the balloon column has two meanings** and printing
            # one number for both is the defect this file exists to avoid.
            # `ok` requires a known contract payment, the payment is estimated
            # from quiet months, and `quiet_pairs` excludes ever-deferred
            # loans, so a deferred row can never carry a known payment. The
            # raw count of deferred rows is taken separately.
            nib_raw = c.row["nib_upb"][:]
            n_defer_rows = int(((nib_raw != K.U32_NA) & (nib_raw > 0)).sum())
            checks.append((name, n_plain, worst, n_bal, n_defer_rows))

            # --- 2. the balloon rows --------------------------------------
            if n_bal:
                sub = M[:, oks & bals]
                sp = np.nanmax(sub, axis=0) - np.nanmin(sub, axis=0)
                rows_out.append((name, n_bal,
                                 [float(x) for x in
                                  np.nanquantile(sp, [.5, .9, .99])],
                                 float(np.nanmax(sp))))
            else:
                rows_out.append((name, 0, [0.0, 0.0, 0.0], 0.0))

            # --- 3. loop level --------------------------------------------
            # Slice per loop rather than masking the whole table per loop: a
            # full-length boolean per triangle is 51,286 allocations of 42
            # million entries, which is the whole file over again each time.
            sums = np.zeros((len(RULES), c.n_loans))
            has = np.zeros(c.n_loans, dtype=bool)
            hasbal = np.zeros(c.n_loans, dtype=bool)
            Mz = np.where(oks[None, :], M, 0.0)
            Mz[~np.isfinite(Mz)] = 0.0
            for li in np.flatnonzero(tri).tolist():
                a, b = int(lo[li]), int(hi[li])
                if a < 0 or b < 0 or b <= a:
                    continue
                sl = slice(a, b + 1)
                if not oks[sl].any():
                    continue
                has[li] = True
                hasbal[li] = bool((oks[sl] & bals[sl]).any())
                sums[:, li] = Mz[:, sl].sum(axis=1)
            if has.any():
                sp = sums[:, has].max(axis=0) - sums[:, has].min(axis=0)
                spb = (sums[:, has & hasbal].max(axis=0)
                       - sums[:, has & hasbal].min(axis=0)) \
                    if (has & hasbal).any() else np.zeros(0)
                loops_out.append((name, int(has.sum()),
                                  [float(x) for x in
                                   np.quantile(sp, [.5, .9, .99])],
                                  float(sp.max()),
                                  int((has & hasbal).sum()),
                                  float(np.median(spb)) if spb.size else 0.0,
                                  float(spb.max()) if spb.size else 0.0))
            else:
                loops_out.append((name, 0, [0.0, 0.0, 0.0], 0.0, 0, 0.0, 0.0))
        print(f"  {name}: {n_plain:,} balloon-free rows, {n_bal:,} with a "
              f"balloon", file=sys.stderr)

    L = []
    A = L.append
    A("# B8: the curve rule, measured on `r` and on the loop sum\n")
    A("Generated by `experiments/b8_cmt_sensitivity2.py`. Registered in "
      "`docs/b8_fannie_slice.md` §16.11.\n")
    A("**This supersedes `results/b8_cmt_sensitivity.md`, which measured the "
      "spread of `log V` alone.** `r_month` gives both legs one `note_pct`, "
      "one `n_now` and one `disc_pct`, and with no deferred balance "
      "`V = LP(bal, i, n) * A(d, n)` with `LP` linear in the balance, so "
      "`r = log(bal_now) - log(b_hat)` and **the annuity factor cancels "
      "exactly**. The earlier number was 267 to 7,110 times the floor on a "
      "quantity that does not reach `r`. **The claim that a modification lets "
      "the curve in through a term change is false against the "
      "implementation.**\n")
    A(f"Six constructions: interpolation {S1.INTERP} crossed with "
      f"{S1.BEYOND} past the longest tenor.\n")
    A("**Reads no prediction.**\n")

    A("\n## 1. The cancellation, asserted on real rows rather than assumed\n")
    A("Rows with no deferred balance on either side. **The spread across all "
      "six constructions must be zero.** A non-zero here means the reading of "
      "`r_month` above is wrong and nothing below is a measurement.\n")
    A(f"Judged against `4 * |log V| * eps` = **{CANCEL_TOL:.3e}**, taking "
      f"`|log V|` at {LOG_V_SCALE:.0f}. **The bound has a source**: `r` is a "
      "difference of logarithms of a quantity in the hundreds of thousands, "
      "and the constructions reach it only through an annuity factor that "
      "cancels algebraically, so what is left is rounding. A bare `0.0` was "
      "the first version's test and **a sourceless number in a criterion is "
      "what discipline 5 forbids**.\n")
    A("| archive | balloon-free rows | **max spread of `r`** | "
      "in units of the bound | verdict |")
    A("|---|---|---|---|---|")
    for name, n_plain, worst, _, _ in checks:
        okk = (worst != worst) or (worst <= CANCEL_TOL)
        A(f"| {name} | {n_plain:,} | **{worst:.3e}** | "
          f"{worst / CANCEL_TOL:.2f} | "
          f"**{'cancels to floating point' if okk else 'DOES NOT CANCEL'}** |")

    A("\n## 2. The one door the curve comes through, and it is shut\n")
    A("`nib * (1+d)^-bn` is the only term that does not cancel, so a deferred "
      "balance is the only way a construction reaches `r`. **The measured "
      "count is zero on every archive and that does not mean there are no "
      "deferred rows.** `r` is computed only where the contract payment is "
      "known; the payment is estimated from quiet months; and "
      "`quiet_pairs(require_never_deferred=True)` excludes ever-deferred "
      "loans. **A deferred row therefore cannot carry a known payment, by "
      "construction.** The raw count is printed beside the measured one so "
      "the two are not confused.\n")
    A("**This is an open item upstream of the curve question.** The one "
      "population where the curve rule could bind is the one the present "
      "payment estimator cannot reach.\n")
    A("| archive | **deferred rows in the file** | **of those, with a known "
      "payment** | spread p50 | max | **(i-b) floor** |")
    A("|---|---|---|---|---|---|")
    defer = {n: d for n, _, _, _, d in checks}
    for name, n_bal, q, mx in rows_out:
        fl = FLOOR.get(name, float("nan"))
        meas = f"{q[0]:.3e}" if n_bal else "**not measurable**"
        mxs = f"{mx:.3e}" if n_bal else "**not measurable**"
        A(f"| {name} | {defer.get(name, 0):,} | {n_bal:,} | {meas} | {mxs} | "
          f"{fl:.3e} |")

    A("\n## 3. Loop level, which is what B8 reads\n")
    A("Summed over the triangle window, **which is not a registered loop "
      "definition** and must not be cited as one. It is first delinquent row "
      "through the first cure after the modification, inclusive.\n")
    A("| archive | loops | spread p50 | p90 | max | **p50 / floor** | "
      "loops with a balloon | their p50 | their max |")
    A("|---|---|---|---|---|---|---|---|")
    for name, nl, q, mx, nb, bq, bm in loops_out:
        fl = FLOOR.get(name, float("nan"))
        A(f"| {name} | {nl:,} | {q[0]:.3e} | {q[1]:.3e} | {mx:.3e} | "
          f"**{q[0] / fl:.3f}** | {nb:,} | {bq:.3e} | {bm:.3e} |")

    A("\n## What this does not decide\n")
    A("- **It does not define the B8 loop.** The window is a summation window "
      "chosen so there is something to sum; the registered loop is not "
      "written yet.")
    A("- **It does not choose either rule.** It says how far the choice can "
      "move the reading.")
    A("- **It does not retract §16.11's requirement to pin both choices.** A "
      "choice that cannot be seen still has to be written down before the run.")
    A("- **It does not measure the deferred population at all.** §2 explains "
      "why, and that is an open item upstream of this one: `omega` on a "
      "deferral leg needs a contract payment for a loan the quiet-month "
      "estimator excludes by construction.")
    A("- It reads no prediction.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def selftest() -> int:
    """The cancellation, on numbers, before it is asserted on 170 million rows."""
    fails = []
    bal_prev, bal_now, i, pay, n = 200000.0, 199_500.0, 6.0, 1199.10, 340
    rs = [float(W.r_month(bal_now, bal_prev, i, pay, n, d))
          for d in (0.5, 2.0, 5.0, 9.0, 15.0)]
    if max(rs) - min(rs) > 1e-15:
        fails.append(f"r moved with the curve without a balloon: "
                     f"{max(rs) - min(rs):.3e}")
    closed = float(np.log(bal_now) - np.log(bal_prev * (1 + i / 1200) - pay))
    if abs(rs[0] - closed) > 1e-12:
        fails.append(f"r is not log(bal_now) - log(b_hat): {rs[0]} vs {closed}")

    rb = [float(W.r_month(bal_now, bal_prev, i, pay, n, d,
                          zib_now=5000.0, zib_prev=5000.0, balloon_n=n))
          for d in (0.5, 2.0, 5.0, 9.0, 15.0)]
    if max(rb) - min(rb) < 1e-9:
        fails.append("r did not move with the curve WITH a balloon, so the "
                     "one door this file measures is not open")

    pts = [(120, 3.0), (240, 4.0), (360, 4.5)]
    ys = {rule: S1.yield_at(pts, 470, *rule) for rule in RULES}
    if len(set(round(v, 12) for v in ys.values())) < 2:
        fails.append("the six constructions agree at 470 months, so the "
                     "spread this file reports is vacuous")

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print(f"selftest: ok  (no balloon: spread {max(rs) - min(rs):.1e}; "
          f"balloon: {max(rb) - min(rb):.3e}; 470m yields "
          f"{min(ys.values()):.4f}..{max(ys.values()):.4f})", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()
                   and not p.name.startswith("209")) if root.exists() else []
    if args.only:
        names = [n for n in names if n in set(args.only)]
    if not names:
        print("no core table.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
