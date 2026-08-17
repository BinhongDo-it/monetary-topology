#!/usr/bin/env python3
"""B8-2: is the sign of the per-period loop sum stable across the windows.

Read map in ``docs/b8_fannie_slice.md`` §20, written before this ran; per
§18.5 it is a record of what was expected and it changes when the run
contradicts it.

§6's discriminant, from ``b1_setup.md`` §7: **a structural wedge shows the
same sign in each window; a one-off repricing shows up in one.**

Three things, and the third decides whether the first two mean anything:

  1. the per-period loop sum's median in each `(window, remaining term at
     t_A)` cell, on the **modification arm only** (§20.1: the deferral arm
     has zero loops in three of the five windows and no download changes
     that);
  2. a bootstrap interval on each median, because "the sign is stable" is
     empty without one (§20.5);
  3. **the leg split, as a check on the criterion itself.** §14.3 makes leg 1
     positive by construction, so a loop sum that is positive everywhere may
     be nothing but leg 1 outweighing leg 2 everywhere -- a fact about how
     servicers price modifications, not a structural wedge. §14.2 says the leg
     split is bookkeeping and carries no claim; that is said of conclusions,
     and using it to ask whether the criterion is vacuous is exactly what it
     is for.

**The two `q` grids give identical loops here** and that is a property of the
construction, not a passed test: §17's window only distinguishes `current`
from not-`current`, so grading delinquency into 30/60/90+ moves nothing
(§20.2). B8-6 is satisfied on B8-2 automatically and the results file says so
rather than printing it as a pass.
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
import b8_loop_omega as Z8                                     # noqa: E402
import b8_0b_floor as F                                        # noqa: E402
import b8_3_paths as P3                                        # noqa: E402
import b8_triangles as T                                       # noqa: E402
import b8_cache as C                                           # noqa: E402

OUT = K.ROOT / "results" / "b8_2_windows.md"

#: **The column list `analyse` opens the core table with.** Pit 30.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
        "mod_flag", "nib_upb", "defer_amt"]

#: §20.3's floor on a cell.
MIN_CELL = 20

#: Bootstrap draws for the interval on each cell's median (§20.5).
#: **Bootstrap, not permutation**: the window is calendar time and shuffling it
#: is not a null of anything.
N_BOOT = 999
BOOT_SEED = 20260817

#: Below this ratio of `|median leg 2|` to `median leg 1`, §20.4 calls the
#: criterion vacuous: the loop sum's sign would then be leg 1's arithmetic
#: rather than a race between two terms. **One order of magnitude**, stated
#: before the run and revisable with it.
LEG_VACUOUS_RATIO = 0.1


def boot_median(x, n=N_BOOT, seed=BOOT_SEED) -> tuple[float, float, float]:
    """Median with a 5-95 bootstrap interval."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return (float("nan"),) * 3
    m = float(np.median(x))
    rng = np.random.default_rng(seed)
    d = np.median(rng.choice(x, size=(n, x.size), replace=True), axis=1)
    return m, float(np.percentile(d, 5)), float(np.percentile(d, 95))


def cells(win, tband, coh, per, om, l1, l2, min_cell=MIN_CELL,
          n_boot=N_BOOT) -> list[dict]:
    """One row per `(window, term band)` on the modification arm.

    `per` is the per-period loop sum, which §14.6 makes the primary statistic;
    `om` is the total beside it, as §3.1 requires. `l1` and `l2` are the legs,
    carried for §20.4's check on the criterion.
    """
    win, tband, coh = np.asarray(win), np.asarray(tband), np.asarray(coh)
    per, om = np.asarray(per, np.float64), np.asarray(om, np.float64)
    l1, l2 = np.asarray(l1, np.float64), np.asarray(l2, np.float64)
    out = []
    for w in range(len(T.WINDOWS)):
        for k in range(len(P3.EDGES_TERM) + 1):
            m = (win == w) & (tband == k)
            n = int(m.sum())
            if n == 0:
                continue
            nc = int(np.unique(coh[m]).size)
            md, lo, hi = boot_median(per[m], n=n_boot)
            row = {"w": w, "k": k, "n": n, "cohorts": nc,
                   "per": md, "lo": lo, "hi": hi,
                   "total": float(np.median(om[m])),
                   "leg1": float(np.median(l1[m])),
                   "leg2": float(np.median(l2[m])),
                   "readable": bool(n >= min_cell and nc > 1)}
            row["sign"] = int(np.sign(md)) if np.isfinite(md) else 0
            row["holds"] = bool(row["readable"] and np.isfinite(lo)
                                and (lo > 0 or hi < 0))
            out.append(row)
    return out


def verdict(rows: list[dict]) -> dict:
    """§20.4 and §20.6, applied to the cell table.

    Reports the sign tally, whether every readable cell agrees, and **whether
    the criterion is vacuous**, which is the one that decides the rest.
    """
    good = [r for r in rows if r["readable"]]
    held = [r for r in good if r["holds"]]
    signs = {s: sum(1 for r in held if r["sign"] == s) for s in (-1, 1)}
    wins = sorted({r["w"] for r in good})
    ratios = [abs(r["leg2"]) / abs(r["leg1"])
              for r in good if r["leg1"] != 0 and np.isfinite(r["leg1"])]
    return {
        "cells": len(rows), "readable": len(good), "holds": len(held),
        "pos": signs.get(1, 0), "neg": signs.get(-1, 0),
        "windows": len(wins),
        "unanimous": bool(held and (signs.get(1, 0) == 0
                                    or signs.get(-1, 0) == 0)),
        "leg_ratio_max": (max(ratios) if ratios else float("nan")),
        "leg_ratio_med": (float(np.median(ratios)) if ratios
                          else float("nan")),
        # **the vacuity test**: if leg 2 never reaches a tenth of leg 1, the
        # loop sum's sign is leg 1's arithmetic and the criterion is not a race
        "vacuous": bool(ratios and max(ratios) < LEG_VACUOUS_RATIO),
    }


def analyse(name: str, cache_root=None, pos=None, tab=None,
            n_boot: int = N_BOOT, use_cache: bool = True,
            core_root=None) -> dict:
    """The cells' inputs for one archive.

    **Reads `b8_cache` by default.** Every station used to rebuild the whole
    pipeline from the core table, so a pass over B8-0b, B8-2 and B8-3 scanned
    170 million rows four times over and paid `contract_payments`' Python loop
    four times with it.

    ``use_cache=False`` keeps the direct path, and the selftest runs both and
    compares: a retrofit that reads the wrong cached field produces a
    perfectly self-consistent wrong answer, which is pit 39's shape.
    """
    if use_cache:
        d = C.get(name, pos=pos, tab=tab, core_root=core_root or cache_root
                  )["sig"]
        meas = d["measurable"].astype(bool)
        arm, rem_A, win = d["arm"], d["rem_A"], d["window"]
        omega, leg1, leg2, n_win = (d["omega"], d["leg1"], d["leg2"],
                                    d["n_win"])
        spl = {k_: d[k_] for k_ in ("l2_balance", "l2_repricing", "l2_rate",
                                    "l2_term", "l2_balloon")}
    else:
        if pos is None or tab is None:
            pos, tab = Z8.curve_table()
        c = K.Core(name, cols=COLS, cache_root=cache_root)
        try:
            disc, _ = W.disc_of_row(c, pos, tab)
            r, ok, _ = W.row_residuals(c, disc)
            lp = L.find_loops(c)
            sig = Z8.loop_sums(lp, r, ok)
            meas, arm = sig["measurable"], lp["arm"]
            win = C._window_of(c, lp["t_M"])
            rem_A = c.row["rem_legal"][:].astype(np.int64)[lp["t_A"]]
            omega, leg1, leg2, n_win = (sig["omega"], sig["leg1"],
                                        sig["leg2"], sig["n_win"])
            q0 = K.quiet_pairs(c)
            pid0 = W.contract_periods(c, fill=True)
            pay0, _kn, _pp = W.contract_payments(c, pid0, q0)
            spl = C.leg2_split(c, lp, disc, pay0, leg2, ok)
            spl.pop("l2_ok", None)
        finally:
            c.close()

    m = meas & (arm == L.ARM_MOD)
    tb = np.searchsorted(np.asarray(P3.EDGES_TERM), rem_A, side="right")
    dur = np.maximum(n_win, 1)                                  # §14.6
    return {"name": name, "n": int(m.sum()),
            "win": np.asarray(win)[m].astype(np.int8),
            "tb": tb[m].astype(np.int8),
            "per": (omega[m] / dur[m]).astype(np.float64),
            "om": omega[m].astype(np.float64),
            "l1": leg1[m].astype(np.float64),
            "l2": leg2[m].astype(np.float64),
            **{k_: np.asarray(v)[m].astype(np.float64)
               for k_, v in spl.items()},
            "n_boot": n_boot}


def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:+.{k}e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-2: the sign of the per-period loop sum across the windows\n")
    A("Generated by `experiments/b8_2_windows.py`. Read map in "
      "`docs/b8_fannie_slice.md` §20, written before this ran.\n")
    A("§6's discriminant, from `b1_setup.md` §7: **a structural wedge shows "
      "the same sign in each window; a one-off repricing shows up in one.**\n")
    A("**Modification arm only** (§20.1). The deferral arm has zero loops in "
      "pre-crisis, HAMP and Flex at every term band, and no additional "
      "acquisition quarter changes that: payment deferral did not exist as a "
      "programme before COVID.\n")
    A("**The two `q` grids give identical loops here**, because §17's window "
      "only distinguishes `current` from not-`current` (§20.2). B8-6 is "
      "satisfied on B8-2 by construction and that is stated rather than "
      "printed as a pass.\n")
    A("Per §14.6 the primary statistic is the loop sum divided by the "
      "**loop's** duration, with the total beside it.\n")

    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"
    win = np.concatenate([a["win"] for a in rows])
    tb = np.concatenate([a["tb"] for a in rows])
    coh = np.concatenate([np.full(a["win"].size, i, np.int8)
                          for i, a in enumerate(rows)])
    per = np.concatenate([a["per"] for a in rows])
    om = np.concatenate([a["om"] for a in rows])
    l1 = np.concatenate([a["l1"] for a in rows])
    l2 = np.concatenate([a["l2"] for a in rows])
    bal_s = np.concatenate([a["l2_balance"] for a in rows])
    rep_s = np.concatenate([a["l2_repricing"] for a in rows])
    rat_s = np.concatenate([a["l2_rate"] for a in rows])
    trm_s = np.concatenate([a["l2_term"] for a in rows])
    bln_s = np.concatenate([a["l2_balloon"] for a in rows])
    tab = cells(win, tb, coh, per, om, l1, l2, n_boot=rows[0]["n_boot"])
    v = verdict(tab)

    A("\n## 1. The cells\n")
    A(f"A cell is readable when `n >= {MIN_CELL}` **and more than one cohort "
      "contributes** (§20.3): inside one cohort the window and the loan's age "
      "are the same variable. `holds` means the bootstrap interval on the "
      "median excludes zero.\n")
    A("| window | remaining term at `t_A` | n | cohorts | **per period** | "
      "5% | 95% | total | leg 1 | leg 2 | readable | **holds** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for g in tab:
        A(f"| {T.WINDOWS[g['w']][0]} | {P3._band(P3.EDGES_TERM, g['k'])} | "
          f"{g['n']:,} | {g['cohorts']} | **{_f(g['per'])}** | {_f(g['lo'])} "
          f"| {_f(g['hi'])} | {_f(g['total'])} | {_f(g['leg1'])} | "
          f"{_f(g['leg2'])} | {'yes' if g['readable'] else 'no'} | "
          f"**{'yes' if g['holds'] else 'no'}** |")

    A("\n## 2. Is the criterion vacuous\n")
    A("**§14.3 makes leg 1 positive by construction**: a missed month leaves "
      "the obligation heavier than the contract said. So a loop sum that is "
      "positive in every window may be nothing but leg 1 outweighing leg 2 "
      "everywhere, which is a fact about how servicers price modifications "
      "and **not a structural wedge**.\n")
    A(f"The test is `\\|median leg 2\\| / \\|median leg 1\\|` across "
      "readable cells. "
      f"Below {LEG_VACUOUS_RATIO:g} everywhere, §20.4 calls the criterion "
      "vacuous and B8-2 is recorded as measuring leg 1's arithmetic rather "
      "than passing.\n")
    A("| readable cells | `\\|leg2\\|/\\|leg1\\|` median | max | "
      "**verdict** |")
    A("|---|---|---|---|")
    A(f"| {v['readable']} | {v['leg_ratio_med']:.4f} | "
      f"{v['leg_ratio_max']:.4f} | "
      + ("**VACUOUS: the sign is leg 1's arithmetic**" if v["vacuous"]
         else "**not vacuous: leg 2 is a real term in the race**") + " |")

    A("\n### 2.1 Where leg 2's sign comes from\n")
    A("**§14.3 predicted leg 2 negative and it came back positive in every "
      "readable cell.** Before that is read as a fact about modifications it "
      "has to be separated from a property of the construction. At `t_M`, "
      "with `V = B*k(i, d, n) + Z*q` and `k = LP(1, i, n) * A(d, n)`:\n")
    A("```\nr(t_M) = log(B_now / B_hat)   the arrears capitalised\n"
      "       + log(k_now / k_hat)   the repricing\n"
      "       + a remainder          the balloon; field 64 is zero here\n```\n")
    A("**This is exact, not an approximation.** At `d = i` the factor `k` is "
      "one and the repricing term is exactly zero; when `d < i` it exceeds one "
      "**and grows with `n`**, so a term extension raises `V` mechanically. "
      "Treasury yields sat far below mortgage note rates through most of this "
      "sample, so that channel is open and has to be measured rather than "
      "assumed small.\n")
    A("The repricing term is split again by moving one contract term at a "
      "time; `cross` is the interaction and is printed rather than "
      "distributed.\n")
    A("| window | remaining term at `t_A` | n | **leg 2** | balance | "
      "repricing | of which rate | term | cross | balloon |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for w in range(len(T.WINDOWS)):
        for k in range(len(P3.EDGES_TERM) + 1):
            m = (win == w) & (tb == k)
            if int(m.sum()) < MIN_CELL or np.unique(coh[m]).size < 2:
                continue
            # **`cross` is the median of the interaction, not the difference
            # of the three medians.** The first version subtracted medians,
            # which measures the median's own non-additivity and prints it
            # under the name of a term in the decomposition.
            g = {f: float(np.nanmedian(x[m])) if np.isfinite(x[m]).any()
                 else float("nan")
                 for f, x in (("bal", bal_s), ("rep", rep_s), ("rate", rat_s),
                              ("term", trm_s), ("bln", bln_s),
                              ("cross", rep_s - rat_s - trm_s))}
            cross = g["cross"]
            A(f"| {T.WINDOWS[w][0]} | {P3._band(P3.EDGES_TERM, k)} | "
              f"{int(m.sum()):,} | **{_f(float(np.median(l2[m])))}** | "
              f"{_f(g['bal'])} | {_f(g['rep'])} | {_f(g['rate'])} | "
              f"{_f(g['term'])} | {_f(cross)} | {_f(g['bln'])} |")
    A("\n**Read it as**: if `repricing` carries leg 2's sign and `term` "
      "carries `repricing`, then leg 2 is positive because the construction "
      "discounts an extended stream at a rate below the note rate, **not "
      "because modifications make households worse off**. If `balance` carries "
      "it, leg 2 is the capitalised arrears and §14.3's expected sign was "
      "simply wrong about which term dominates.\n")

    A("\n## 3. The verdict\n")
    A("| cells | readable | interval excludes zero | positive | negative | "
      "windows covered | **unanimous** |")
    A("|---|---|---|---|---|---|---|")
    A(f"| {v['cells']} | {v['readable']} | {v['holds']} | {v['pos']} | "
      f"{v['neg']} | {v['windows']} | "
      f"**{'yes' if v['unanimous'] else 'NO'}** |")
    A("\n§20.6's map: unanimous with intervals clear of zero is B8-2 holding, "
      "in a version that has been levelled on term. A window reversing sign "
      "is B8-2 failing and is read as a one-off repricing per §6. **Cells "
      "whose interval crosses zero are not counted toward agreement.**\n")

    A("\n## What this does not decide\n")
    A("- **Whether the term effect is mechanical or compositional.** §6.6.30.2: "
      "this data cannot separate them and the claim is not made.")
    A("- **The deferral arm across windows.** It does not exist (§20.1) and no "
      "download creates it.")
    A("- B8-1, which has its own criterion.")
    A("- Causality of any kind.\n")
    return "\n".join(Ls) + "\n"


def selftest() -> int:
    fails: list[str] = []

    # -- boot_median, against a case with a known answer ------------------
    x = np.arange(101.0)
    m, lo, hi = boot_median(x, n=199)
    if m != 50.0:
        fails.append(f"boot_median's point estimate {m}, expected 50.0")
    if not (lo < m < hi):
        fails.append(f"the bootstrap interval [{lo}, {hi}] does not contain "
                     f"the median {m}")
    # a constant sample has a degenerate interval, and the sign must still hold
    m2, lo2, hi2 = boot_median(np.full(50, 3.0), n=99)
    if not (m2 == lo2 == hi2 == 3.0):
        fails.append(f"a constant sample gave [{lo2}, {hi2}] around {m2}")
    # and an interval that straddles zero must be produced when it should be
    m3, lo3, hi3 = boot_median(np.linspace(-1.0, 1.0, 201), n=399)
    if not (lo3 < 0 < hi3):
        fails.append(f"a sample centred on zero gave [{lo3}, {hi3}], which "
                     "does not straddle zero; `holds` would be meaningless")

    # -- cells and verdict, on hand-built arrays --------------------------
    n = MIN_CELL
    win = np.concatenate([np.zeros(2 * n, np.int8), np.ones(2 * n, np.int8)])
    tbb = np.zeros(4 * n, np.int8)
    coh = np.concatenate([np.tile([0, 1], n),          # window 0: 2 cohorts
                          np.zeros(2 * n, np.int8)])   # window 1: 1 cohort
    per = np.concatenate([np.full(2 * n, 0.5), np.full(2 * n, 0.7)])
    l1c = np.full(4 * n, 1.0)
    l2c = np.full(4 * n, -0.5)
    tabl = cells(win, tbb, coh, per, per * 3, l1c, l2c, n_boot=99)
    by = {(g["w"], g["k"]): g for g in tabl}
    if not by[(0, 0)]["readable"]:
        fails.append("a two-cohort cell above MIN_CELL read not readable")
    if by[(1, 0)]["readable"]:
        fails.append("a SINGLE-cohort cell read readable; §20.3's cohort "
                     "requirement is the load-bearing half")
    if not by[(0, 0)]["holds"]:
        fails.append("a constant positive cell's interval did not exclude "
                     "zero")
    # **a readable cell whose interval straddles zero must not `hold`**, or
    # the interval is decoration and `holds` is just `readable`
    win_z = np.concatenate([win, np.full(2 * n, 2, np.int8)])
    tb_z = np.zeros(6 * n, np.int8)
    coh_z = np.concatenate([coh, np.tile([0, 1], n)])
    per_z = np.concatenate([per, np.linspace(-1.0, 1.0, 2 * n)])
    l1_z, l2_z = np.full(6 * n, 1.0), np.full(6 * n, -0.5)
    tz = {(g["w"], g["k"]): g
          for g in cells(win_z, tb_z, coh_z, per_z, per_z * 3, l1_z, l2_z,
                         n_boot=399)}
    if not tz[(2, 0)]["readable"]:
        fails.append("the zero-centred cell was not readable, so nothing "
                     "tests the interval")
    if tz[(2, 0)]["holds"]:
        fails.append("a readable cell whose bootstrap interval straddles zero "
                     "was recorded as holding; `holds` is not reading the "
                     "interval")

    v = verdict(tabl)
    if v["readable"] != 1 or v["pos"] != 1 or v["neg"] != 0:
        fails.append(f"verdict read {v['readable']}/{v['pos']}/{v['neg']}, "
                     "expected 1 readable, 1 positive, 0 negative")
    if v["vacuous"]:
        fails.append("leg 2 at half of leg 1 was called vacuous; the "
                     f"threshold is {LEG_VACUOUS_RATIO}")

    # **the vacuity test must fire when it should**, or section 2 is decoration
    v2 = verdict(cells(win, tbb, coh, per, per * 3, l1c,
                       np.full(4 * n, -0.001), n_boot=99))
    if not v2["vacuous"]:
        fails.append("leg 2 at a thousandth of leg 1 was not called vacuous; "
                     "the check on the criterion cannot fire")
    # and a sign disagreement must break unanimity
    per2 = per.copy()
    per2[:2 * n] = -0.5
    coh2 = np.tile([0, 1], 2 * n)                # both windows get 2 cohorts
    v3 = verdict(cells(win, tbb, coh2, per2, per2 * 3, l1c, l2c, n_boot=99))
    if v3["unanimous"]:
        fails.append("two readable cells of opposite sign were called "
                     "unanimous")

    # -- end to end on `b8_loops`' fixture --------------------------------
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab_ = Z8._flat_curve(months)
    a = analyse(zp.stem, cache_root=cr, pos=pos, tab=tab_, n_boot=19,
                use_cache=False)
    if a["n"] == 0:
        fails.append("no measurable modification loop on the fixture")

    # **Both paths, compared.** A retrofit that reads the wrong cached field
    # returns a perfectly self-consistent wrong answer (pit 39), so the cached
    # path is checked against the direct one rather than trusted.
    a_c = analyse(zp.stem, cache_root=cr, pos=pos, tab=tab_, n_boot=19,
                  use_cache=True, core_root=cr)
    for f in ("n", "win", "tb", "per", "om", "l1", "l2",
              "l2_balance", "l2_repricing", "l2_rate", "l2_term",
              "l2_balloon"):
        if not np.array_equal(np.asarray(a[f]), np.asarray(a_c[f]),
                              equal_nan=True):
            fails.append(f"the cached path and the direct one differ on "
                         f"`{f}`")
    # §2.1's columns have to survive the round trip as numbers, not as NaN on
    # both sides agreeing with each other
    if not np.isfinite(np.asarray(a_c["l2_balance"])).any():
        fails.append("every cached `l2_balance` is NaN, so the comparison "
                     "above passes on two empty arrays and §2.1 is untested")
    # **§14.6: the primary statistic divides by the LOOP's duration**, and the
    # division has to be visible. Recomputed here from the windows rather than
    # taken from `analyse`'s own arithmetic.
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c2:
        disc2, _ = W.disc_of_row(c2, pos, tab_)
        r2, ok2, _ = W.row_residuals(c2, disc2)
        lp2 = L.find_loops(c2)
        sig2 = Z8.loop_sums(lp2, r2, ok2)
        m2 = sig2["measurable"] & (lp2["arm"] == L.ARM_MOD)
        dur2 = np.maximum(sig2["n_win"], 1)[m2]
    if not np.allclose(a["per"] * dur2, a["om"], rtol=0, atol=1e-15):
        fails.append("the per-period statistic is not the loop sum divided by "
                     "the loop's duration (§14.6)")
    if not (dur2 > 1).any():
        fails.append("every loop in the fixture has duration 1, so dividing "
                     "by it changes nothing and §14.6 is untested here")

    txt = render([a])
    # one archive means one cohort, so nothing may be readable
    if "| yes | **yes** |" in txt:
        fails.append("a single-archive run produced a readable cell; the "
                     "cohort requirement is not being applied")
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The cells", "## 2. Is the criterion vacuous",
                 "### 2.1 Where leg 2's sign comes from",
                 "## 3. The verdict"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    print(f"  fixture: {a['n']} modification loops, render ok", file=sys.stderr)

    for m_ in fails:
        print("FAIL " + m_, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the cohort rule bites and the vacuity test fires",
          file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: {a['n']:,} modification loops", file=sys.stderr)
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
    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()) \
        if root.exists() else []
    if args.only:
        keep = set(args.only)
        names = [n for n in names if n in keep]
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
