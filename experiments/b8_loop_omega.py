#!/usr/bin/env python3
"""B8 omega, block two: **the loop sum**.

Registered in ``docs/b8_fannie_slice.md`` §14.2, §14.6 and §17. Block one built
the windows (`b8_loops.py`) and the residual (`b8_omega.py`); this puts them
together::

    omega(loop) = sum of r(t) for t in (t_A, t_B]

    leg 1 = (t_A, t_M)     current -> delinquent
    leg 2 = t_M            delinquent -> modified   (one month)
    leg 3 = (t_M, t_B]     modified -> current

**No prediction is read here.** B8-1 judges the loop sum against B8-0b's floor
and that floor is not computed on loops yet. What this file reports is how much
of the file carries a measurable loop, whether the assembly is internally
consistent, and the distribution the next stage will be reading. The
distribution is printed because a construction that produces numbers nobody
looks at until the prediction stage is a construction whose defects surface at
the worst possible moment.

--------------------------------------------------------------------------
The identity §17.11 asks for is **vacuous under a prefix-sum implementation**
--------------------------------------------------------------------------

§17.11 requires asserting ``leg1 + leg2 + leg3 == omega(loop)`` and gives the
reason: it catches a window implementation that is off by a row, and such a
misalignment is silent everywhere else.

**Under the obvious implementation the assertion cannot do that job.** All four
quantities come from one prefix-sum array::

    omega = P[t_B+1] - P[t_A+1]
    leg1  = P[t_M]   - P[t_A+1]
    leg2  = P[t_M+1] - P[t_M]
    leg3  = P[t_B+1] - P[t_M+1]

The three legs telescope to the loop sum **whatever ``t_M`` is**, including a
``t_M`` off by a row, off by ten rows, or belonging to a different loop. The
identity holds by construction and tests the floating-point adder.

So the check is done twice and the second one is the real one:

* **`identity`** is the registered assertion, kept because §17.11 registered it
  and because it does catch a genuinely broken prefix-sum or range helper.
* **`replay`** re-sums a random sample of loops **month by month in Python**,
  from the window indices, and compares against the vectorised answer. That one
  fails if `t_A`, `t_M` or `t_B` is misplaced, if the inclusive/exclusive
  convention drifts, or if the `ok` mask and the residual array disagree.

**This is a correction to §17.11 and it is filed as one**, not folded in
silently: the section's stated reason for the assertion is wrong, the
requirement survives, and the job it was supposed to do now has something that
actually does it.

--------------------------------------------------------------------------
Measurability
--------------------------------------------------------------------------

§17.10: a loop is measurable when **every** month in ``(t_A, t_B]`` carries a
computable ``r``. One unreadable month anywhere in the window drops the whole
loop, because the sum is over the window and a partial sum is a different
quantity.

Drops are counted **split at ``t_M``**, which §17.10 requires. That section's
original reason for the split was that the deferral arm had zero payment
coverage after the onset; O24 killed that reason (the deferral arm reads 92.86
per cent full-path coverage). The requirement survives on a different reason,
recorded in §14.4 as amended: **the two arms have different contract-period
structure.** `contract_periods` cuts at a field-63 rising edge, which is the
modification arm's onset, and deliberately does not cut at a field-108 rising
edge (§6.6.17.2). So the modification arm's window crosses a boundary by
construction and the deferral arm's does not, and a merged drop count hides
that the two arms fail for different reasons.

--------------------------------------------------------------------------
What travels with every figure
--------------------------------------------------------------------------

The loans carrying both zero-interest balances are refused by `V` (C13,
§6.6.20.6) and the count is printed beside every table here, at the same rank
as §9's truncation limits. So is `b8_loops`' `excluded_two_arms` (§17.4), which
is a different exclusion for a different reason and must not be added to it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_cmt_fetch as F                                       # noqa: E402
import b8_cmt_sensitivity as S1                                # noqa: E402

OUT = K.ROOT / "results" / "b8_loop_omega.md"

#: **The registered curve rules**, §17.14 and §17.15. Not a sweep: the sweep is
#: `b8_cmt_sensitivity2` and it answers a different question.
RULE = ("linear_in_tenor", "cap")

#: Horizons are integer months, so the curve is read once into a table rather
#: than per row. **One definition**, in `b8_omega`, shared with
#: `b8_cmt_sensitivity2`, which used to carry its own copy of both this and the
#: lookup below.
MAX_H = W.MAX_H
disc_of_row = W.disc_of_row

#: **The column list `run` opens the core table with.** Pit 30: hoisted so the
#: selftest opens its fixture with the same one, and swept by
#: `scripts/b8_col_sweep.py`.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
        "mod_flag", "nib_upb", "defer_amt"]

#: How many loops `replay` re-sums month by month. The whole point is that it
#: is a **different** implementation, so it is Python and therefore capped.
#: **The cap is printed**, because a silent truncation reads as full coverage.
REPLAY_N = 4000

#: The identity's tolerance, **with a source**. `r` is a difference of two
#: logarithms of `V`; `V` runs to a few hundred thousand so `log V` is of order
#: 13, and a window of a few hundred months accumulates at most a few hundred
#: such differences. Four cancelling partial sums of that size carry about
#: `4 * 300 * 14 * eps`. A misaligned window moves the sum by one month's
#: residual, which is of order 1e-3, so this tolerance is nine orders of
#: magnitude away from what it has to distinguish and the choice is not close
#: to any boundary.
IDENTITY_TOL = 4.0 * 300.0 * 14.0 * np.finfo(np.float64).eps


# ---------------------------------------------------------------------------
# the curve, as a row-indexed array
# ---------------------------------------------------------------------------

def curve_table(rule=RULE):
    """``(month_index -> table row, table[months, MAX_H+1])`` of yields.

    Missing months and horizons are NaN, so a lookup that should not have
    happened surfaces as a NaN rather than as a plausible number.
    """
    curves = S1.month_curve(F.load_treasury())
    months = sorted(curves)
    pos = {mi: k for k, mi in enumerate(months)}
    tab = np.full((len(months), MAX_H + 1), np.nan)
    for k, mi in enumerate(months):
        pts = curves[mi]
        for h in range(1, MAX_H + 1):
            y = S1.yield_at(pts, h, rule[0], rule[1])
            if y is not None:
                tab[k, h] = y
    return pos, tab


# ---------------------------------------------------------------------------
# the sum
# ---------------------------------------------------------------------------

def _prefix(a: np.ndarray) -> np.ndarray:
    out = np.zeros(a.size + 1, dtype=np.float64)
    np.cumsum(a, out=out[1:])
    return out


def loop_sums(lp: dict, r: np.ndarray, ok: np.ndarray) -> dict:
    """The loop sum and the three legs, per §14.2, §17.11 and §17.1.

    ``lp`` is `b8_loops.find_loops`' return. Ranges are **inclusive at both
    ends** here; §17's `(t_A, t_B]` becomes `[t_A + 1, t_B]`.

    An empty leg (§17.3's ``t_M == t_B`` gives leg 3 no months) comes back as
    an exact ``0.0`` from a range whose end is one before its start, which is
    what a sum over no months is. **It is not the same object as a leg that
    summed to zero**, so `n3` carries the month count beside it and every
    renderer prints both.
    """
    t_A, t_M, t_B = lp["t_A"], lp["t_M"], lp["t_B"]
    rz = np.where(ok, r, 0.0)
    P = _prefix(rz)
    C = np.concatenate(([0], np.cumsum(ok.astype(np.int64))))

    def s(a, b):                      # inclusive [a, b]; b < a gives 0.0
        return P[b + 1] - P[a]

    def cnt(a, b):
        return C[b + 1] - C[a]

    n_win = t_B - t_A                                   # months in (t_A, t_B]
    have = cnt(t_A + 1, t_B)
    measurable = have == n_win

    om = s(t_A + 1, t_B)
    l1 = s(t_A + 1, t_M - 1)
    l2 = s(t_M, t_M)
    l3 = s(t_M + 1, t_B)

    resid = np.abs(l1 + l2 + l3 - om)
    return {
        "omega": om, "leg1": l1, "leg2": l2, "leg3": l3,
        "n_win": n_win, "n_have": have, "measurable": measurable,
        "n1": t_M - 1 - t_A, "n2": np.ones_like(n_win), "n3": t_B - t_M,
        "identity_max": float(resid.max()) if resid.size else 0.0,
        # §17.10: split at t_M, and the two sides are counted separately
        "miss_before": (t_M - t_A) - cnt(t_A + 1, t_M),
        "miss_after": (t_B - t_M) - cnt(t_M + 1, t_B),
    }


def replay(lp: dict, r: np.ndarray, ok: np.ndarray, sums: dict,
           n: int = REPLAY_N, seed: int = 20260817) -> dict:
    """Re-sum a sample of loops **month by month**, and compare.

    This is the check §17.11 was reaching for. The vectorised answer comes from
    a prefix-sum array in which the three legs telescope to the loop sum no
    matter where ``t_M`` sits, so the registered identity cannot see a
    misplaced vertex. This one walks the window from the indices themselves and
    therefore can.

    **It is a different implementation, not the same one twice.** Python loop,
    explicit bounds, no prefix array, and it recomputes measurability from the
    per-month mask rather than from a count.
    """
    t_A, t_M, t_B = lp["t_A"], lp["t_M"], lp["t_B"]
    k = int(min(n, t_A.size))
    if k == 0:
        return {"checked": 0, "capped": False, "worst": 0.0,
                "worst_leg": 0.0, "mismatched": 0, "meas_mismatched": 0}
    rng = np.random.default_rng(seed)
    pick = rng.choice(t_A.size, size=k, replace=False)

    worst = worst_leg = 0.0
    bad = meas_bad = 0
    for e in pick.tolist():
        a, m, b = int(t_A[e]), int(t_M[e]), int(t_B[e])
        tot = 0.0
        legs = [0.0, 0.0, 0.0]
        allok = True
        for t in range(a + 1, b + 1):
            if not ok[t]:
                allok = False
                continue
            tot += float(r[t])
            legs[0 if t < m else (1 if t == m else 2)] += float(r[t])
        if allok != bool(sums["measurable"][e]):
            meas_bad += 1
        d = abs(tot - float(sums["omega"][e]))
        dl = max(abs(legs[0] - float(sums["leg1"][e])),
                 abs(legs[1] - float(sums["leg2"][e])),
                 abs(legs[2] - float(sums["leg3"][e])))
        worst = max(worst, d)
        worst_leg = max(worst_leg, dl)
        if d > IDENTITY_TOL or dl > IDENTITY_TOL:
            bad += 1
    return {"checked": k, "capped": k < t_A.size, "worst": worst,
            "worst_leg": worst_leg, "mismatched": bad,
            "meas_mismatched": meas_bad}


def analyse(name: str, cache_root=None, pos=None, tab=None,
            replay_n: int = REPLAY_N) -> dict:
    if pos is None or tab is None:
        pos, tab = curve_table()
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        lp = L.find_loops(c)
        disc, dinfo = disc_of_row(c, pos, tab)
        r, ok, rinfo = W.row_residuals(c, disc)
        sums = loop_sums(lp, r, ok)
        rep = replay(lp, r, ok, sums, n=replay_n)

        arm = lp["arm"]
        a = {"name": name, "n_rows": c.n_rows, "n_loans": c.n_loans,
             "n_loops": int(arm.size), "curve": dinfo, "rows": rinfo,
             "replay": rep, "identity_max": sums["identity_max"],
             "excluded_two_arms": int(np.size(lp["excluded_two_arms"])),
             "loans_refused_c13": rinfo["V"]["loans_dropped_c13"],
             "c13_edges": rinfo["V"]["carrier"]["both_edges"],
             "c13_beyond": rinfo["V"]["carrier"]["excluded_beyond_c13"],
             "arms": {}}

        meas = sums["measurable"]
        # §14.6: the per-period statistic divides by the **loop's** duration
        dur = np.maximum(sums["n_win"], 1)
        for tag, code in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
            m = arm == code
            mm = m & meas
            d = {"loops": int(m.sum()), "measurable": int(mm.sum()),
                 "miss_before": int(sums["miss_before"][m].sum()),
                 "miss_after": int(sums["miss_after"][m].sum()),
                 "loops_miss_before": int((sums["miss_before"][m] > 0).sum()),
                 "loops_miss_after": int((sums["miss_after"][m] > 0).sum()),
                 "leg3_empty": int((sums["n3"][m] == 0).sum()),
                 "leg3_empty_meas": int((sums["n3"][mm] == 0).sum())}
            for key in ("omega", "leg1", "leg2", "leg3"):
                v = sums[key][mm]
                d[key + "_q"] = (np.percentile(v, [10, 50, 90]).tolist()
                                 if v.size else [float("nan")] * 3)
                d[key + "_absmed"] = (float(np.median(np.abs(v)))
                                      if v.size else float("nan"))
            v = sums["omega"][mm] / dur[mm]
            d["per_month_q"] = (np.percentile(v, [10, 50, 90]).tolist()
                                if v.size else [float("nan")] * 3)
            d["dur_q"] = (np.percentile(sums["n_win"][mm],
                                        [10, 50, 90]).tolist()
                          if v.size else [float("nan")] * 3)
            # leg 3 measured only where it exists, §17.3 and §14.3 as amended
            nz = mm & (sums["n3"] > 0)
            d["leg3_where_it_exists"] = int(nz.sum())
            d["leg3_nz_absmed"] = (float(np.median(np.abs(sums["leg3"][nz])))
                                   if nz.any() else float("nan"))
            a["arms"][tag] = d
    finally:
        c.close()
    return a


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _f(x):
    return "nan" if not np.isfinite(x) else f"{x:+.4e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8 omega block two: the loop sum\n")
    A("Generated by `experiments/b8_loop_omega.py`. Windows from "
      "`b8_loops.find_loops` (§17), residual from `b8_omega.row_residuals` "
      "(§14.2), curve rules `linear_in_tenor` / `cap` (§17.14–§17.15).\n")
    A("**This reads no prediction.** B8-1 judges the loop sum against B8-0b's "
      "floor, and that floor is not computed on loops here. What follows is "
      "the assembly's own coverage and consistency, and the distribution the "
      "next stage will read.\n")

    A("\n## 1. What was refused, and by which rule\n")
    A("**Three different exclusions, never added together.** They answer "
      "different questions and a single total would hide all three.\n")
    A("| archive | loops | refused: both balances (C13) | of those, C13 edge "
      "pairs | beyond C13 | two arms in one window (§17.4) |")
    A("|---|---|---|---|---|---|")
    for a in rows:
        A(f"| {a['name']} | {a['n_loops']:,} | {a['loans_refused_c13']:,} | "
          f"{a['c13_edges']:,} | {a['c13_beyond']:,} | "
          f"{a['excluded_two_arms']:,} |")

    A("\n## 2. Why a row carries no residual\n")
    A("**In the order applied, so the counts partition.** A row dropped by an "
      "earlier condition is not counted again by a later one.\n")
    names = [n for n, _ in rows[0]["rows"]["dropped"]] if rows else []
    A("| archive | " + " | ".join(names) + " | **kept** |")
    A("|---|" + "---|" * (len(names) + 1))
    for a in rows:
        d = dict(a["rows"]["dropped"])
        A(f"| {a['name']} | "
          + " | ".join(f"{d.get(n, 0):,}" for n in names)
          + f" | **{a['rows']['ok']:,}** |")

    A("\n**The curve's own reach**, before any of the above.\n")
    A("| archive | rows | no curve that month | horizon past the table | "
      "curve NaN | **usable** |")
    A("|---|---|---|---|---|---|")
    for a in rows:
        cv = a["curve"]
        A(f"| {a['name']} | {cv['rows']:,} | {cv['no_curve_that_month']:,} | "
          f"{cv['horizon_out_of_table']:,} | {cv['curve_nan']:,} | "
          f"**{cv['usable']:,}** |")

    A("\n**Rows carrying a balloon**, which is the only door the curve rules "
      "reach through (§17.16). Before 2026-08-17 this was zero by "
      "construction, because the balloon read field 63 and field 63's rows "
      "had no payment.\n")
    A("| archive | rows with a balloon at t | at t-1 |")
    A("|---|---|---|")
    for a in rows:
        A(f"| {a['name']} | {a['rows']['rows_with_balloon']:,} | "
          f"{a['rows']['rows_with_balloon_prev']:,} |")

    A("\n## 3. Is the assembly consistent\n")
    A("**Two checks, and the second one is the real one.** `identity` is "
      "§17.11's registered assertion. Under a prefix-sum implementation the "
      "three legs telescope to the loop sum **whatever `t_M` is**, so it "
      "cannot catch the misplaced vertex §17.11 says it catches. `replay` "
      "re-sums a sample of loops month by month from the window indices and "
      "can.\n")
    A(f"Tolerance `{IDENTITY_TOL:.3e}`, derived in the module docstring. A "
      "misaligned window moves a sum by one month's residual, of order 1e-3, "
      "**nine orders away**.\n")
    A("| archive | identity, worst | replayed | capped | worst loop | "
      "worst leg | **mismatched** | measurability mismatched |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        rp = a["replay"]
        A(f"| {a['name']} | {a['identity_max']:.3e} | {rp['checked']:,} | "
          f"{'yes' if rp['capped'] else 'no'} | {rp['worst']:.3e} | "
          f"{rp['worst_leg']:.3e} | **{rp['mismatched']:,}** | "
          f"{rp['meas_mismatched']:,} |")

    A("\n## 4. How many loops are measurable\n")
    A("§17.10: **every** month in the window must carry a residual. Drops are "
      "split at `t_M`, which §17.10 requires; the reason it gives for the "
      "split was killed by O24 and the surviving reason is in §14.4 as "
      "amended, that the two arms have different contract-period structure.\n")
    A("| archive | arm | loops | **measurable** | rate | loops missing before "
      "`t_M` | after | months missing before | after |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {d['loops']:,} | "
              f"**{d['measurable']:,}** | {pct2(d['measurable'], d['loops'])} "
              f"| {d['loops_miss_before']:,} | {d['loops_miss_after']:,} | "
              f"{d['miss_before']:,} | {d['miss_after']:,} |")

    A("\n## 5. The distribution, **not read against anything**\n")
    A("Per §14.6 the per-period statistic divides by the **loop's** duration, "
      "not the leg's, and the total is printed beside it.\n")
    A("| archive | arm | n | omega p10 | p50 | p90 | median abs | "
      "per month p50 | duration p50 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {d['measurable']:,} | "
              + " | ".join(_f(v) for v in d["omega_q"])
              + f" | {d['omega_absmed']:.4e} | {_f(d['per_month_q'][1])} | "
              f"{d['dur_q'][1]:.0f} |")

    A("\n**The legs.** §14.2: the split is bookkeeping and no claim rests on "
      "it. Leg 3 is printed twice, because §17.3's `t_M == t_B` shape gives it "
      "**no months at all** on much of the sample, and a median over an empty "
      "leg is not a measurement of zero (坑 23).\n")
    A("| archive | arm | leg1 p50 | leg2 p50 | leg3 p50 | leg3 empty | "
      "**leg3 where it exists** | its median abs |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {_f(d['leg1_q'][1])} | "
              f"{_f(d['leg2_q'][1])} | {_f(d['leg3_q'][1])} | "
              f"{d['leg3_empty_meas']:,} | "
              f"**{d['leg3_where_it_exists']:,}** | "
              + ("not measurable" if not np.isfinite(d["leg3_nz_absmed"])
                 else f"{d['leg3_nz_absmed']:.4e}") + " |")

    A("\n## What this does not decide\n")
    A("- **It reads no prediction.** B8-1, B8-2 and B8-3 all judge against "
      "B8-0b's floor, which is not computed on loops here.")
    A("- **The leg split is bookkeeping** (§14.2). Arrears capitalisation "
      "lands in leg 2 rather than leg 1 and the loop sum does not care.")
    A("- **`omega3` is not evidence about HAMP trial periods.** §14.3 as "
      "amended: the multi-onset carrier is 38 loops across six archives.")
    A("- The loans carrying both zero-interest balances are **refused, not "
      "estimated** (C13). Their count is in section 1 and travels with every "
      "figure above.")
    A("- §7's four filters (single family, first lien, owner occupied, fixed "
      "rate) are **still not applied**.\n")
    txt = "\n".join(Ls) + "\n"
    return txt


def pct2(x, y):
    return f"{x / y:.4f}" if y else "-"


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def _flat_curve(months, y=4.0):
    """A flat curve at ``y`` per cent for every month, as a table.

    **Flat on purpose.** P2 proved the curve cancels completely on the contract
    triple, so a flat curve does not weaken any check that does not involve a
    balloon, and it removes the Treasury fetch from this selftest's path. The
    balloon case is checked separately, where the curve does not cancel.
    """
    pos = {int(m): k for k, m in enumerate(sorted(months))}
    return pos, np.full((len(pos), MAX_H + 1), float(y))


#: How far the hand computation may sit from the code's answer.
#:
#: **Sourced, not picked.** The fixture writes balances to the cent, so the
#: payment the code recovers from the quiet months differs from the generator's
#: by up to half a cent on a balance of order 2e5, a relative 2.5e-8. `r` is a
#: log ratio, so that carries through at about the same size, and a factor of
#: forty is left over for the rounding of the balances themselves. **What it
#: has to distinguish is the two defects it was written for, which move `r(t_M)`
#: by 1e-1 and 1e-3**, five to seven orders away.
LEG2_TOL = 1e-6

#: ``(case, months after t_M)`` pinned against hand arithmetic.
#:
#: Three rows, each for a term the others cannot reach. ``plain_mod+0`` moves
#: the rate and the term. ``defer_triangle+0`` **raises** a balloon, so it sees
#: `V`'s balloon but not `V-hat`'s, which is still zero there.
#: ``defer_triangle+1`` has the balloon **standing on both rows**, which is the
#: only shape in which `V-hat`'s own balloon horizon multiplies something other
#: than zero. Without the third one, stepping that horizon back a month or not
#: makes no difference to any number in this repository.
PINNED = [("plain_mod", 0), ("defer_triangle", 0), ("defer_triangle", 1)]


def _selftest_leg2(cache_root, pos, tab) -> list[str]:
    """`r` at the modification month, written out from §14.2 by hand.

    Two cases, and the second one is why there are two: ``plain_mod`` moves the
    rate and the term, ``defer_triangle`` carries a **balloon**, which is the
    only term of `V` the curve reaches through and the only one with a horizon
    of its own to get wrong.
    """
    out: list[str] = []
    zp = K.CACHE / "_selftest_loops" / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    names = list(L.CASES)
    saw_balloon = saw_standing = False
    with K.Core(zp.stem, cols=COLS, cache_root=cache_root) as c:
        disc, _ = W.disc_of_row(c, pos, tab)
        r, ok, _info = W.row_residuals(c, disc)
        lp = L.find_loops(c)

        upb = c.row["upb"][:].astype(np.float64)
        nib = c.row["nib_upb"][:].astype(np.float64)
        dfr = c.row["defer_amt"][:].astype(np.float64)
        nib = np.where(nib == K.U32_NA, 0.0, nib)
        dfr = np.where(dfr == K.U32_NA, 0.0, dfr)
        zib = (nib + dfr) / 100.0
        bal_c = (upb - nib - dfr) / 100.0
        rate_c = c.row["rate"][:].astype(np.float64) / 1000.0
        rem_c = c.row["rem_legal"][:].astype(np.float64)
        bn_c = (c.row["mat_date"][:].astype(np.float64)
                - c.row["period"][:].astype(np.float64))
        P0 = float(K.level_payment([200000.0], [5.0], [360.0])[0])

        def ann(y, n):
            i = y / 1200.0
            return n if i <= 0 else (1.0 - (1.0 + i) ** (-n)) / i

        def lvl(b, y, n):
            i = y / 1200.0
            return b / n if i <= 0 else b * i / (1.0 - (1.0 + i) ** (-n))

        for want_case, off in PINNED:
            ln = names.index(want_case)
            idx = [k for k in range(lp["t_A"].size)
                   if int(lp["loan"][k]) == ln]
            if len(idx) != 1:
                out.append(f"{want_case} did not produce exactly one loop")
                continue
            tM = int(lp["t_M"][idx[0]]) + off
            if tM > int(lp["t_B"][idx[0]]):
                out.append(f"{want_case}+{off} is past its return vertex")
                continue
            if not ok[tM]:
                out.append(f"{want_case}+{off} carries no residual, so the "
                           "value this file pins is not computed")
                continue
            d = float(disc[tM])
            dd = d / 1200.0
            got = float(r[tM])

            # V(t_M): the contract as it now stands
            v_now = (lvl(bal_c[tM], rate_c[tM], rem_c[tM]) * ann(d, rem_c[tM])
                     + zib[tM] * (1.0 + dd) ** (-bn_c[tM]))
            # V-hat(t_M): §14.2, the UNCHANGED contract one month forward.
            # Same rate, same balloon, horizon and term each one month nearer.
            b_hat = bal_c[tM - 1] * (1.0 + rate_c[tM - 1] / 1200.0) - P0
            v_hat = (lvl(b_hat, rate_c[tM - 1], rem_c[tM - 1] - 1.0)
                     * ann(d, rem_c[tM - 1] - 1.0)
                     + zib[tM - 1] * (1.0 + dd) ** (-(bn_c[tM - 1] - 1.0)))
            want = float(np.log(v_now) - np.log(v_hat))

            if abs(got - want) > LEG2_TOL:
                out.append(f"pinned {want_case}+{off}: code {got:+.8e}, hand "
                           f"{want:+.8e}, difference {abs(got-want):.2e} over "
                           f"{LEG2_TOL:.0e}")
            moved = (rate_c[tM] != rate_c[tM - 1]
                     or rem_c[tM] != rem_c[tM - 1] - 1.0
                     or zib[tM] != zib[tM - 1])
            if not moved and off == 0:
                out.append(f"{want_case}'s onset month moves neither the "
                           "rate, the term nor the balloon, so this check "
                           "cannot see a counterfactual on the wrong contract")
            if zib[tM] > 0 or zib[tM - 1] > 0:
                saw_balloon = True
            if zib[tM - 1] > 0:
                saw_standing = True
            print(f"  pinned {want_case}+{off}: {got:+.8e} vs {want:+.8e} "
                  f"(rate {rate_c[tM-1]:.3f}->{rate_c[tM]:.3f}, term "
                  f"{rem_c[tM-1]:.0f}->{rem_c[tM]:.0f}, balloon "
                  f"{zib[tM-1]:.0f}->{zib[tM]:.0f})", file=sys.stderr)

    if not saw_balloon:
        out.append("no pinned row carries a balloon, so the one term of `V` "
                   "the curve reaches through is never checked")
    if not saw_standing:
        out.append("no pinned row has a balloon **standing on the previous "
                   "row**, so `V-hat`'s balloon and its horizon are always "
                   "multiplied by zero and `balloon_n_prev` could be off by a "
                   "month with nothing to say so")
    return out


def selftest() -> int:
    fails: list[str] = []

    # -- the range helper, against hand arithmetic -------------------------
    r = np.array([np.nan, 1.0, 2.0, 4.0, 8.0, 16.0])
    ok = np.array([False, True, True, True, True, True])
    lp = {"t_A": np.array([0]), "t_M": np.array([2]), "t_B": np.array([4]),
          "excluded_two_arms": np.array([]), "arm": np.array([L.ARM_MOD])}
    s = loop_sums(lp, r, ok)
    # window (0, 4] = rows 1..4 = 1 + 2 + 4 + 8 = 15
    # leg1 = rows 1..1 = 1 ; leg2 = row 2 = 2 ; leg3 = rows 3..4 = 12
    for key, want in (("omega", 15.0), ("leg1", 1.0), ("leg2", 2.0),
                      ("leg3", 12.0)):
        if float(s[key][0]) != want:
            fails.append(f"range helper: {key} = {s[key][0]}, want {want}")
    if not bool(s["measurable"][0]):
        fails.append("range helper: a fully covered window read unmeasurable")
    if int(s["n3"][0]) != 2:
        fails.append(f"range helper: n3 = {s['n3'][0]}, want 2")

    # an empty leg 3, §17.3's shape: t_M == t_B
    lp2 = {"t_A": np.array([0]), "t_M": np.array([4]), "t_B": np.array([4]),
           "excluded_two_arms": np.array([]), "arm": np.array([L.ARM_MOD])}
    s2 = loop_sums(lp2, r, ok)
    if float(s2["leg3"][0]) != 0.0 or int(s2["n3"][0]) != 0:
        fails.append(f"empty leg 3 read {s2['leg3'][0]} over "
                     f"{s2['n3'][0]} months, want 0.0 over 0")
    if float(s2["omega"][0]) != 15.0:
        fails.append("t_M == t_B changed the loop sum, it must not")

    # one unreadable month anywhere drops the loop, and the side is counted
    ok3 = ok.copy()
    ok3[3] = False
    s3 = loop_sums(lp, r, ok3)
    if bool(s3["measurable"][0]):
        fails.append("a window with an unreadable month read measurable")
    if int(s3["miss_after"][0]) != 1 or int(s3["miss_before"][0]) != 0:
        fails.append(f"the missing month landed before={s3['miss_before'][0]} "
                     f"after={s3['miss_after'][0]}, want 0 and 1")
    ok4 = ok.copy()
    ok4[1] = False
    s4 = loop_sums(lp, r, ok4)
    if int(s4["miss_before"][0]) != 1 or int(s4["miss_after"][0]) != 0:
        fails.append("the split at t_M does not separate the two sides")

    # -- replay must catch what the identity cannot ------------------------
    # **This is the check on the check.** Move `t_M` by one row: the identity
    # still holds exactly, because the legs telescope. Replay must not.
    lp_bad = {"t_A": np.array([0]), "t_M": np.array([3]),
              "t_B": np.array([4]), "excluded_two_arms": np.array([]),
              "arm": np.array([L.ARM_MOD])}
    s_bad = loop_sums(lp_bad, r, ok)
    # the identity, computed the way §17.11 asks, on a deliberately wrong t_M
    if abs(float(s_bad["leg1"][0] + s_bad["leg2"][0] + s_bad["leg3"][0]
                 - s_bad["omega"][0])) > IDENTITY_TOL:
        fails.append("the telescoping identity failed on its own terms")
    # now hand replay the CORRECT sums against the WRONG window: it must差
    rp = replay(lp, r, ok, s_bad, n=10)
    if rp["mismatched"] == 0:
        fails.append("replay agreed with a leg split taken from a window one "
                     "row away; it cannot see a misplaced t_M and the whole "
                     "point of it is that it can")
    print(f"  identity vs replay: identity holds on a wrong t_M, replay "
          f"reports {rp['mismatched']} mismatch(es) on 1 loop",
          file=sys.stderr)

    # -- end to end on `b8_loops`' own fixture -----------------------------
    # **`b8_loops`' own fixture**, not a new one. Its fourteen hand-placed
    # cases are the windows this file sums over, so the two are tested on the
    # same object; a second fixture here would let the window rules and the
    # summation drift apart while both stayed green.
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cache_root = root / "cache"
    K.build_archive(zp, force=True, cache_root=cache_root)
    with K.Core(zp.stem, cols=COLS, cache_root=cache_root) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab = _flat_curve(months)
    a = analyse(zp.stem, cache_root=cache_root,
                pos=pos, tab=tab, replay_n=10_000)
    if a["n_loops"] == 0:
        fails.append("the loops fixture produced no loop at all")
    tot_meas = sum(a["arms"][t]["measurable"] for t in ("mod", "defer"))
    if tot_meas == 0:
        fails.append("no loop on the fixture is measurable, so every "
                     "distribution below is an empty set and the end-to-end "
                     "run proves nothing")
    if a["replay"]["mismatched"] != 0:
        fails.append(f"replay disagreed with the vectorised sum on "
                     f"{a['replay']['mismatched']} loop(s), worst "
                     f"{a['replay']['worst']:.3e}")
    if a["replay"]["meas_mismatched"] != 0:
        fails.append("replay and the vectorised code disagree about which "
                     "loops are measurable")
    if a["replay"]["checked"] < a["n_loops"]:
        fails.append("the fixture's loops were sampled rather than all "
                     "replayed, so the end-to-end check is partial")
    if a["identity_max"] > IDENTITY_TOL:
        fails.append(f"identity worst {a['identity_max']:.3e} over tolerance")
    # **Both arms, or one arm's whole column is an empty set that prints like a
    # measurement** (坑 23). The deferral arm is one loop in this fixture and
    # that is enough to keep the column honest.
    for tag in ("mod", "defer"):
        if a["arms"][tag]["measurable"] == 0:
            fails.append(f"no measurable loop on the {tag} arm, so its whole "
                         "row of the distribution is an empty set")
    # leg 3 must exist somewhere, or §17.3's `t_M == t_B` shape is the only one
    # tested and the leg-3 column is never exercised
    if sum(a["arms"][t]["leg3_where_it_exists"] for t in ("mod", "defer")) == 0:
        fails.append("every measurable loop has an empty leg 3, so the leg-3 "
                     "sum is never actually computed")
    if sum(a["arms"][t]["leg3_empty_meas"] for t in ("mod", "defer")) == 0:
        fails.append("no measurable loop has `t_M == t_B`, so §17.3's shape "
                     "and the empty-sum path are untested")
    print(f"  end to end: {a['n_loops']} loops, {tot_meas} measurable, "
          f"replay {a['replay']['checked']} checked / "
          f"{a['replay']['mismatched']} mismatched, identity "
          f"{a['identity_max']:.3e}", file=sys.stderr)

    # -- the modification month, against arithmetic done by hand -----------
    # **Every check above is structural**: ranges, masks, telescoping, replay.
    # None of them pins a *value*, and two defects walked straight through the
    # whole set on 2026-08-17: pricing `V-hat` on the new contract, and taking
    # the counterfactual's payment from the modification month's own contract
    # period instead of the previous one. Both produce a perfectly
    # self-consistent number.
    #
    # So `r(t_M)` is written out here from §14.2's definition, using the
    # fixture generator's own payment rather than anything the code estimated,
    # and compared. This is the only place in block two where an absolute value
    # is asserted.
    fails += _selftest_leg2(cache_root, pos, tab)

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 3. Is the assembly consistent", "replay", "leg3 empty"):
        if need not in txt:
            fails.append(f"render omits `{need}`")

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the loop sum assembles and replay can see a "
          "misplaced vertex", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: {a['n_loops']:,} loops, "
              f"{sum(a['arms'][t]['measurable'] for t in ('mod','defer')):,} "
              f"measurable, replay {a['replay']['mismatched']} mismatched",
              file=sys.stderr)
    txt = render(rows)
    bad = K.check_markdown_tables(txt)
    if bad:
        for b in bad:
            print("MALFORMED " + b, file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt, encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["run", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args()
    if args.command == "selftest":
        raise SystemExit(selftest())
    names = args.only or sorted(
        p.name for p in (K.CACHE / K.SCHEMA_VERSION).iterdir() if p.is_dir())
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
