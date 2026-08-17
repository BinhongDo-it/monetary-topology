#!/usr/bin/env python3
"""B8-0b: the noise floor for the loop sum.

Pre-registered in ``docs/b8_fannie_slice.md`` §18, **written before this ran and
not revisited** (§8). Read that section first; this file implements it and adds
nothing.

    Z := 2 * Var(omega)   over the loops being compared          §18.1
    N := 2 * Var(omega)   over CLEAN CURES, whose true value      §18.3
                          is zero by construction
    M := 2 * Var(omega)   within (arm, missed months, months to   §18.4
                          cure) cells, size-weighted

**`N` is the zero-calibration arm, not the matched-cell dispersion.** §18.2
settles that and gives three reasons; the load-bearing one is that matched-cell
dispersion is a *subset of the signal*, so using it as the floor drives the
ratio toward one by an amount that depends on how finely the cells are cut.
`M` is still computed and printed, because it says how much of `omega` the
realised path explains, which is B8-4's precondition. **It does not enter the
ratio.**

--------------------------------------------------------------------------
The clean cure's window
--------------------------------------------------------------------------

§18.3's N2: a clean cure has no modification onset, so `t_M` has no meaning
there. It is defined as **the first delinquent month**, which makes the window
`(t_A, t_B]` exactly as §17 defines it and keeps the three-leg split formally
valid. **`N` uses the loop sum only.** Leg 2 on this arm is not a
re-contracting and nothing here reads it.

--------------------------------------------------------------------------
Two computations of Z that must agree
--------------------------------------------------------------------------

`b3_cip_slice.md` B3-1, adopted verbatim: `Z` is computed by enumeration over
ordered pairs **and** as `2 * Var`, and they must agree to a relative error
below 1e-12. That is a gate on the code, not a reading. Enumeration is
quadratic, so it runs on a capped random sample and **the cap is printed**.
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
import b8_0a_gate as G                                         # noqa: E402

OUT = K.ROOT / "results" / "b8_0b_floor.md"

#: **The column list `analyse` opens the core table with.** Pit 30.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
        "mod_flag", "nib_upb", "defer_amt", "zero_bal"]

#: §6.4's floor on a cell, adopted by §18.4.
MIN_CELL = 20

#: How many loops the quadratic enumeration of `Z` is drawn from. **The cap is
#: printed**, because a silent truncation reads as full coverage.
ENUM_CAP = 3000

#: B3-1's tolerance on "the two computations of `Z` agree", verbatim.
ENUM_TOL = 1e-12

#: §3.3's coarse grid, reused as the cell edges for `M`. Months.
#: **Path quantities only.** §18.4 forbids any contract-derived key, because
#: `omega` is a function of the contract and cutting on it would drive the
#: within-cell variance to zero and the ratio to infinity. That is C11's
#: criterion B (§6.6.16) in a different costume, and that one was only caught
#: after the run.
EDGES_MISSED = (1, 2, 3, 6, 12)
EDGES_CURE = (0, 1, 2, 3, 6, 12)


def zed(x: np.ndarray) -> float:
    """`Z = 2 * Var(x)`, §18.1. Population variance, not the sample one."""
    x = np.asarray(x, dtype=np.float64)
    return 2.0 * float(np.var(x)) if x.size else float("nan")


#: Sample sizes the variance is re-estimated at, to see whether it converges.
#: **A sample variance that keeps climbing with `n` is not estimating a
#: population variance**; it is reporting how far into the tail the draw
#: reached. Every ratio built on it is then a function of the sample size.
CONV_NS = (100, 300, 1000, 3000, 10000, 30000)
CONV_REPS = 21


def scale_convergence(om: np.ndarray, ns=CONV_NS, reps=CONV_REPS,
                      seed: int = 20260817) -> list[dict]:
    """`2*Var` and the robust scale, both as a function of sample size.

    The variance answers **the question the run is actually asking**: is `Z`
    a property of the population or of how many loops were drawn. The robust
    scale is carried beside it because if one converges and the other does not,
    that is the whole finding in two columns.
    """
    om = np.asarray(om, dtype=np.float64)
    rng = np.random.default_rng(seed)
    out = []
    for n in list(ns) + [om.size]:
        if n > om.size or n < 8:
            continue
        vs, ms = [], []
        for _ in range(reps):
            s = om[rng.choice(om.size, n, replace=False)]
            vs.append(zed(s))
            ms.append(mad_scale(s))
        vs, ms = np.array(vs), np.array(ms)
        out.append({"n": int(n), "var_med": float(np.median(vs)),
                    "var_lo": float(np.percentile(vs, 10)),
                    "var_hi": float(np.percentile(vs, 90)),
                    "mad_med": float(np.median(ms)),
                    "mad_lo": float(np.percentile(ms, 10)),
                    "mad_hi": float(np.percentile(ms, 90))})
    return out


def mad_scale(x: np.ndarray) -> float:
    """Normal-consistent median absolute deviation.

    **The candidate replacement for `sqrt(2*Var)` on both sides of the ratio.**
    It is the same object computed the same way on the signal and on the floor,
    which is what B3's shape actually requires; what B3 did not have to worry
    about is a variable whose distribution spans five orders of magnitude, and
    `omega` on mortgages does. `1.4826` makes it agree with the standard
    deviation on a normal sample, so the two columns are readable side by side.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("nan")
    med = np.median(x)
    return 1.4826 * float(np.median(np.abs(x - med)))


def zed_by_enumeration(x: np.ndarray) -> float:
    """`(1/k^2) * sum over ordered pairs of (x_i - x_j)^2`, §18.1 verbatim.

    Quadratic. The caller caps the sample; this does no capping of its own so
    that what it is given is what it measures.
    """
    x = np.asarray(x, dtype=np.float64)
    k = x.size
    if k == 0:
        return float("nan")
    d = x[:, None] - x[None, :]
    return float((d * d).sum()) / (k * k)


def check_enumeration(x: np.ndarray, cap: int = ENUM_CAP,
                      seed: int = 20260817) -> dict:
    """B3-1: the two computations of `Z` must agree to machine precision."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return {"n": 0, "capped": False, "var": float("nan"),
                "enum": float("nan"), "rel": float("nan"), "ok": False}
    take = x
    capped = x.size > cap
    if capped:
        take = x[np.random.default_rng(seed).choice(x.size, cap,
                                                    replace=False)]
    v, e = zed(take), zed_by_enumeration(take)
    rel = abs(v - e) / max(abs(v), 1e-300)
    return {"n": int(take.size), "capped": capped, "var": v, "enum": e,
            "rel": rel, "ok": bool(rel < ENUM_TOL)}


#: Two-sided trim fractions the floor is recomputed at. **Added 2026-08-17,
#: after the first run**, and the reason is in the results file: `sqrt(N)` came
#: back 1,669 to 6,592 times the median absolute loop sum on the same arm, and
#: a 3,000-loop subsample of the same population gave `N` between 0.07 and 4.86
#: times the full-population value. **A variance that moves seventy-fold under
#: resampling is a tail statistic**, and a floor made of one is set by a handful
#: of loops rather than by the measurement error of a typical one.
#:
#: This does not replace `N`. §18.1 fixed the statistic as `2*Var` and that is
#: what B3 uses; the trimmed values sit beside it so a reader can see how much
#: of the floor is tail and decide what to do about it. **Reporting a
#: tail-dominated floor without saying it is tail-dominated is the defect.**
TRIMS = (0.0, 0.001, 0.01, 0.05)

#: How many of the largest-|omega| clean cures to print with their diagnostics.
N_EXAMPLES = 5


def trimmed_floor(om: np.ndarray, trims=TRIMS) -> list[dict]:
    """`2*Var` after removing the largest and smallest `q` of the sample."""
    om = np.asarray(om, dtype=np.float64)
    out = []
    if om.size == 0:
        return [{"trim": q, "n": 0, "Z": float("nan")} for q in trims]
    s = np.sort(om)
    for q in trims:
        k = int(np.floor(q * s.size))
        v = s[k:s.size - k] if k else s
        out.append({"trim": q, "n": int(v.size), "Z": zed(v)})
    return out


def freeze_counts(c: K.Core, lp: dict, r: np.ndarray) -> np.ndarray:
    """Months inside each window where the interest-bearing balance did not
    move at all.

    §6.2.7 measured this: field 12 reads identical on consecutive months for
    4.881 per cent of quiet months across the six archives, about four in ten
    of those never recover, and **an unrecovered freeze contributes exactly one
    missed month's worth of `omega1`**. On the clean-cure arm the true loop sum
    is zero, so a freeze is the obvious candidate for what the tail is made of.
    Counted rather than assumed.
    """
    bal = K.zero_interest_split(c)[0]
    same = np.zeros(c.n_rows, dtype=np.int64)
    same[1:] = (bal[1:] == bal[:-1]).astype(np.int64)
    same[c.row_start.astype(np.int64)] = 0
    pre = np.concatenate(([0], np.cumsum(same)))
    a, b = lp["t_A"] + 1, lp["t_B"]
    return pre[b + 1] - pre[a]


# ---------------------------------------------------------------------------
# the clean-cure arm, through the same machinery
# ---------------------------------------------------------------------------

def clean_cure_loops(c: K.Core) -> dict:
    """Clean-cure windows shaped like `b8_loops.find_loops`' return.

    §18.3 N1: the zero-calibration arm runs through **the same** summation as
    the signal, so this returns the same three indices and nothing else does
    the summing. §18.3 N2: `t_M` is the **first delinquent month**, because a
    clean cure has no modification onset.

    The population is `b8_0a_gate.find_clean_cures`, unmodified, which screens
    field 42, field 63 and field 108 (O28).
    """
    t0, st, en, k, drops = G.find_clean_cures(c, require_no_defer=True)
    # `t0` is the departure vertex and `en` the return vertex, which is exactly
    # §17's `t_A` and `t_B`. The first delinquent month is `t_A + 1` by
    # construction: `find_clean_cures` anchors `t0` at the last current row
    # before the episode, so the row after it is the first delinquent one.
    return {"t_A": t0, "t_M": t0 + 1, "t_B": en, "k": k,
            "arm": np.full(t0.size, L.ARM_MOD, dtype=np.int8),
            "loan": c.loan_of_row()[t0] if t0.size else np.zeros(0, np.int32),
            "drops": drops}


# ---------------------------------------------------------------------------
# the matched cells
# ---------------------------------------------------------------------------

def cell_of(arm, missed, cure) -> np.ndarray:
    """§18.4's cell id. **Three path keys and no contract key.**"""
    a = np.asarray(arm, dtype=np.int64)
    i = np.searchsorted(np.asarray(EDGES_MISSED), np.asarray(missed),
                        side="right")
    j = np.searchsorted(np.asarray(EDGES_CURE), np.asarray(cure),
                        side="right")
    return (a * 64 + i * 8 + j).astype(np.int64)


def emm(om: np.ndarray, cell: np.ndarray, min_cell: int = MIN_CELL) -> dict:
    """`M`, §18.4: within-cell `2*Var`, weighted by cell size."""
    om = np.asarray(om, dtype=np.float64)
    if om.size == 0:
        return {"M": float("nan"), "cells": 0, "cells_used": 0,
                "loops_used": 0, "loops_dropped_small": 0}
    order = np.argsort(cell, kind="stable")
    cs, os_ = cell[order], om[order]
    starts = np.flatnonzero(np.concatenate(([True], cs[1:] != cs[:-1])))
    counts = np.diff(np.append(starts, cs.size))
    num = den = 0.0
    used = small = 0
    for s, n in zip(starts.tolist(), counts.tolist()):
        if n < min_cell:
            small += n
            continue
        num += n * zed(os_[s:s + n])
        den += n
        used += 1
    return {"M": (num / den) if den else float("nan"),
            "cells": int(starts.size), "cells_used": used,
            "loops_used": int(den), "loops_dropped_small": small}


# ---------------------------------------------------------------------------
# per archive
# ---------------------------------------------------------------------------

def analyse(name: str, cache_root=None, pos=None, tab=None) -> dict:
    if pos is None or tab is None:
        pos, tab = Z8.curve_table()
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        disc, _dinfo = W.disc_of_row(c, pos, tab)
        r, ok, rinfo = W.row_residuals(c, disc)

        lp = L.find_loops(c)
        sig = Z8.loop_sums(lp, r, ok)
        cc = clean_cure_loops(c)
        flo = Z8.loop_sums(cc, r, ok)

        # **The ideal-path subset, which is where the zero actually lives.**
        # §14.5 splits B8-0a into (i), the gate, whose clean cure reinstates by
        # paying every missed payment at once so that the balance lands exactly
        # where the uninterrupted schedule would have it and **the round trip is
        # zero by arithmetic**; and (ii), the same loans with fees,
        # capitalisation and forgiveness on, which that section says returns
        # non-zero **for real reasons**.
        #
        # `N` was drawn on (ii)'s population and the zero-calibration property
        # belongs to (i). That is why five loans out of 47,412 carried 78 per
        # cent of the floor: their balance ran from 56,813.89 to 0.01 across
        # nine months, which is a retirement wearing a cure's delinquency code,
        # and nothing about it is measurement error.
        #
        # **This needs no new threshold.** `b8_0a_gate.episode_sums` already
        # returns the ideal-path flag and B8-0a(i-a) already runs on it.
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _known0, _p0 = W.contract_payments(c, pid0, q0)
        es = G.episode_sums(c, pay0, cc["t_A"], cc["t_B"], cc["k"])
        ideal = es[2]

        a = {"name": name, "n_rows": c.n_rows,
             "loans_refused_c13": rinfo["V"]["loans_dropped_c13"],
             "cc_drops": cc["drops"], "arms": {}}

        # ---- N, the zero-calibration arm -----------------------------------
        fm = flo["measurable"] & ideal
        a["N_all"] = {
            "measurable": int(flo["measurable"].sum()),
            "Z": zed(flo["omega"][flo["measurable"]]),
            "absmed": (float(np.median(np.abs(flo["omega"][flo["measurable"]])))
                       if flo["measurable"].any() else float("nan"))}
        n_om = flo["omega"][fm]
        a["N"] = {"loops": int(fm.size), "measurable": int(fm.sum()),
                  "ideal": int(ideal.sum()),
                  "Z": zed(n_om),
                  "absmed": float(np.median(np.abs(n_om))) if n_om.size
                  else float("nan"),
                  "q": (np.percentile(n_om, [10, 50, 90]).tolist()
                        if n_om.size else [float("nan")] * 3),
                  "enum": check_enumeration(n_om),
                  "enough": bool(n_om.size >= MIN_CELL),
                  "trimmed": trimmed_floor(n_om),
                  "mad": mad_scale(n_om),
                  "conv": scale_convergence(n_om)}

        # **What the tail is made of.** Freezes are the registered suspect
        # (§6.2.7); this counts them rather than asserting them, and prints the
        # largest loops beside their counts so the reader sees the rows.
        fz = freeze_counts(c, cc, r)[fm]
        wl = flo["n_win"][fm]
        # **What the balance did across the window.** `omega = -15.5` on a
        # clean cure means `V` at the return vertex is 1.8e-7 of the
        # counterfactual, that is a two hundred thousand dollar loan reporting
        # a few cents. That is a **payoff**, not a cure: the delinquency field
        # returns to `00` and `find_clean_cures` counts it, while what actually
        # happened is the loan was retired. A zero-calibration arm cannot
        # contain those. Two reads settle it and neither needs a threshold
        # chosen by hand: the balance ratio at the two vertices, and field 44,
        # the zero-balance code, which §6.2.6.3 ruled needed no filter **for a
        # different purpose**.
        balc = K.zero_interest_split(c)[0].astype(np.float64)
        ta, tb = cc["t_A"][fm], cc["t_B"][fm]
        with np.errstate(divide="ignore", invalid="ignore"):
            bratio = np.where(balc[ta] > 0, balc[tb] / balc[ta], np.nan)
        # **`omega` is a log ratio, so its noise scales inversely with the
        # balance.** A fixed dollar deviation on a 3,385 balance is a large log
        # move and the same deviation on a 300,000 one is nothing. The floor's
        # tail turned out to be small balances; modifications happen on live
        # mortgages. **A floor drawn from one balance regime does not judge a
        # signal drawn from another**, so the balance at the departure vertex
        # is carried for both arms and the floor is recomputed on the range
        # where the signal actually lives.
        bal_A = balc[ta] / 100.0
        zb = c.row["zero_bal"][:]
        zb_set = ((zb != K.U8_NA) & (zb != 0))
        pre_zb = np.concatenate(([0], np.cumsum(zb_set.astype(np.int64))))
        zb_in_win = (pre_zb[tb + 1] - pre_zb[ta + 1]) > 0
        if n_om.size:
            big = np.argsort(-np.abs(n_om))[:N_EXAMPLES]
            a["N"]["examples"] = [
                {"omega": float(n_om[i]), "window": int(wl[i]),
                 "frozen": int(fz[i]), "bratio": float(bratio[i]),
                 "zb": bool(zb_in_win[i]),
                 "bal_A": float(balc[ta[i]]) / 100.0,
                 "bal_B": float(balc[tb[i]]) / 100.0} for i in big.tolist()]
            hot = np.abs(n_om) >= np.percentile(np.abs(n_om), 99.0)
            a["N"]["tail"] = {
                "cut": float(np.percentile(np.abs(n_om), 99.0)),
                "n_hot": int(hot.sum()),
                "share_of_Z": float(
                    (n_om[hot] ** 2).sum() / max((n_om ** 2).sum(), 1e-300)),
                "frozen_hot": float(fz[hot].mean()) if hot.any() else float("nan"),
                "frozen_rest": float(fz[~hot].mean()) if (~hot).any() else float("nan"),
                "any_frozen_hot": float((fz[hot] > 0).mean()) if hot.any() else float("nan"),
                "any_frozen_rest": float((fz[~hot] > 0).mean()) if (~hot).any() else float("nan"),
                "win_hot": float(wl[hot].mean()) if hot.any() else float("nan"),
                "win_rest": float(wl[~hot].mean()) if (~hot).any() else float("nan"),
                "bratio_hot": (np.nanpercentile(bratio[hot], [10, 50, 90]).tolist()
                               if hot.any() else [float("nan")] * 3),
                "bratio_rest": (np.nanpercentile(bratio[~hot], [10, 50, 90]).tolist()
                                if (~hot).any() else [float("nan")] * 3),
                "zb_hot": float(zb_in_win[hot].mean()) if hot.any() else float("nan"),
                "zb_rest": float(zb_in_win[~hot].mean()) if (~hot).any() else float("nan"),
                "tiny_hot": float((bratio[hot] < 0.01).mean()) if hot.any() else float("nan"),
                "tiny_rest": float((bratio[~hot] < 0.01).mean()) if (~hot).any() else float("nan"),
                "balA_hot": (np.percentile(bal_A[hot], [10, 50, 90]).tolist()
                             if hot.any() else [float("nan")] * 3),
                "balA_rest": (np.percentile(bal_A[~hot], [10, 50, 90]).tolist()
                              if (~hot).any() else [float("nan")] * 3)}
        else:
            a["N"]["examples"], a["N"]["tail"] = [], {}
        a["N"]["balA_q"] = (np.percentile(bal_A, [10, 50, 90]).tolist()
                            if bal_A.size else [float("nan")] * 3)

        # ---- Z and M, per arm and pooled ------------------------------------
        meas = sig["measurable"]
        arm = lp["arm"]
        sig_balA = balc[lp["t_A"]] / 100.0
        cell = cell_of(arm, sig["n1"] + 1, sig["n3"])
        for tag, sel in (("mod", arm == L.ARM_MOD),
                         ("defer", arm == L.ARM_DEFER),
                         ("pooled", np.ones_like(meas))):
            m = sel & meas
            om = sig["omega"][m]
            d = {"loops": int(sel.sum()), "measurable": int(m.sum()),
                 "Z": zed(om),
                 "q": (np.percentile(om, [10, 50, 90]).tolist() if om.size
                       else [float("nan")] * 3),
                 "enum": check_enumeration(om),
                 "M": emm(om, cell[m])}
            # the floor **on the balance range this arm actually occupies**
            sb = sig_balA[m]
            if sb.size and bal_A.size:
                lo, hi = np.percentile(sb, [10, 90])
                keep = (bal_A >= lo) & (bal_A <= hi)
                d["N_matched"] = {
                    "lo": float(lo), "hi": float(hi), "n": int(keep.sum()),
                    "Z": zed(n_om[keep]) if keep.any() else float("nan")}
            else:
                d["N_matched"] = {"lo": float("nan"), "hi": float("nan"),
                                  "n": 0, "Z": float("nan")}
            d["balA_q"] = (np.percentile(sb, [10, 50, 90]).tolist()
                           if sb.size else [float("nan")] * 3)
            nm = d["N_matched"]["Z"]
            d["ratio_matched"] = (float(np.sqrt(d["Z"]) / np.sqrt(nm))
                                  if (np.isfinite(nm) and nm > 0
                                      and np.isfinite(d["Z"]))
                                  else float("nan"))
            d["mad"] = mad_scale(om)
            d["conv"] = scale_convergence(om)
            d["ratio_mad"] = (float(d["mad"] / a["N"]["mad"])
                              if (np.isfinite(a["N"]["mad"])
                                  and a["N"]["mad"] > 0) else float("nan"))
            zz, nn = d["Z"], a["N"]["Z"]
            d["ratio"] = (float(np.sqrt(zz) / np.sqrt(nn))
                          if (np.isfinite(zz) and np.isfinite(nn) and nn > 0)
                          else float("nan"))
            d["ratio_M"] = (float(np.sqrt(zz) / np.sqrt(d["M"]["M"]))
                            if (np.isfinite(zz) and np.isfinite(d["M"]["M"])
                                and d["M"]["M"] > 0) else float("nan"))
            a["arms"][tag] = d
    finally:
        c.close()
    return a


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:.{k}e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-0b: the noise floor for the loop sum\n")
    A("Generated by `experiments/b8_0b_floor.py`. **Pre-registered in "
      "`docs/b8_fannie_slice.md` §18, before this ran.** The map from outcome "
      "to disposition is §18.5 and is not revisited here.\n")
    A("```\nZ := 2 * Var(omega)  over the loops compared\n"
      "N := 2 * Var(omega)  over CLEAN CURES, true value zero by construction\n"
      "M := 2 * Var(omega)  within (arm, missed months, months to cure) cells\n"
      "```\n")
    A("**`N` is the floor, `M` is not** (§18.2). Matched-cell dispersion is a "
      "subset of the signal, so using it as the floor drives the ratio toward "
      "one by an amount that depends on how finely the cells are cut. `M` is "
      "printed because it says how much of `omega` the realised path explains, "
      "which is B8-4's precondition.\n")

    A("\n## 1. The gate: two computations of `Z` must agree\n")
    A("`b3_cip_slice.md` B3-1, verbatim. Enumeration over ordered pairs "
      f"against `2*Var`, relative error below `{ENUM_TOL:.0e}`. Enumeration is "
      f"quadratic so it draws at most {ENUM_CAP:,} loops, **and the cap is "
      "printed**.\n")
    A("| archive | arm | n | capped | `2*Var` | enumeration | rel. error | "
      "**agrees** |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("pooled", "mod", "defer"):
            e = a["arms"][tag]["enum"]
            A(f"| {a['name']} | {tag} | {e['n']:,} | "
              f"{'yes' if e['capped'] else 'no'} | {_f(e['var'])} | "
              f"{_f(e['enum'])} | {_f(e['rel'], 2)} | "
              f"**{'yes' if e['ok'] else 'NO'}** |")
        e = a["N"]["enum"]
        A(f"| {a['name']} | N (clean cures) | {e['n']:,} | "
          f"{'yes' if e['capped'] else 'no'} | {_f(e['var'])} | "
          f"{_f(e['enum'])} | {_f(e['rel'], 2)} | "
          f"**{'yes' if e['ok'] else 'NO'}** |")

    A("\n## 2. `N`, the zero calibration\n")
    A("Clean cures from `b8_0a_gate.find_clean_cures` (O28's population: never "
      "field 42 `Y`, never a positive field 63, never a positive field 108), "
      "summed by **the same** `loop_sums` the signal uses (§18.3 N1). `t_M` is "
      "the first delinquent month (§18.3 N2). **The contract genuinely does "
      "not change on this arm, so the true loop sum is zero and what is left "
      "is construction error, reporting noise and freezes.**\n")
    A("**`N` is drawn on the IDEAL-PATH subset, changed 2026-08-17 after the "
      "run.** §14.5 splits B8-0a into (i), the gate, whose clean cure "
      "reinstates by paying every missed payment at once so the balance lands "
      "exactly on the uninterrupted schedule and **the round trip is zero by "
      "arithmetic**; and (ii), the same loans with fees and capitalisation on, "
      "which that section says returns non-zero **for real reasons**. `N` was "
      "drawn on (ii). The zero-calibration property belongs to (i).\n")
    A("That is why **five loans out of 47,412 carried 78 per cent of the "
      "floor**: one ran from 56,813.89 to 0.01 across nine months and then "
      "reported delinquency `00`. That is a retirement wearing a cure's code, "
      "and nothing about it is measurement error. **The correction needs no "
      "new threshold**: `b8_0a_gate.episode_sums` already returns the "
      "ideal-path flag and B8-0a(i-a) already runs on it.\n")
    A("Both populations are printed. `all` is what this file reported before "
      "the correction (R01).\n")
    A("| archive | clean cures | measurable | **ideal path** | `N` | "
      "`sqrt(N)` | median abs | p10 | p50 | p90 | `N` on all | `sqrt` | "
      "median abs |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        n, na = a["N"], a["N_all"]
        A(f"| {a['name']} | {n['loops']:,} | {na['measurable']:,} | "
          f"**{n['measurable']:,}** | {_f(n['Z'])} | {_f(np.sqrt(n['Z']))} | "
          f"{_f(n['absmed'])} | " + " | ".join(_f(v) for v in n["q"])
          + f" | {_f(na['Z'])} | {_f(np.sqrt(na['Z']))} | "
          f"{_f(na['absmed'])} |")

    A("\n### 2.1 `N` is a tail statistic, and this is the read that says so\n")
    A("**Added after the first run.** `sqrt(N)` came back between 1,669 and "
      "6,592 times the median absolute loop sum on the same arm, and a "
      f"{ENUM_CAP:,}-loop subsample of the same population gave `N` between "
      "0.07 and 4.86 times the full-population value. **A variance that moves "
      "seventy-fold under resampling is made of its tail.** §18.1 fixed the "
      "statistic as `2*Var` and that stays; these columns say how much of it "
      "is tail, so the ratio in section 3 is read for what it is.\n")
    A("| archive | `sqrt(N)` | median abs | ratio | " +
      " | ".join(f"trim {q:.1%}" for q in TRIMS) + " |")
    A("|---|---|---|" + "---|" * (len(TRIMS) + 1))
    for a in rows:
        n = a["N"]
        A(f"| {a['name']} | {_f(np.sqrt(n['Z']))} | {_f(n['absmed'])} | "
          f"{np.sqrt(n['Z']) / max(n['absmed'], 1e-300):,.0f}x | "
          + " | ".join(_f(np.sqrt(d["Z"])) for d in n["trimmed"]) + " |")

    A("\n**What the tail is made of.** The top one per cent by `|omega|` "
      "against the rest. §6.2.7 registered the suspect: field 12 reads "
      "identical on consecutive months for 4.881 per cent of quiet months, "
      "four in ten of those never recover, and **an unrecovered freeze "
      "contributes exactly one missed month's worth of `omega1`** on an arm "
      "whose true loop sum is zero.\n")
    A("| archive | 99th pct of \\|omega\\| | loops above | share of `Z` | "
      "frozen months, hot | rest | any freeze, hot | rest | window, hot | "
      "rest |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        tl = a["N"].get("tail") or {}
        if not tl:
            continue
        A(f"| {a['name']} | {_f(tl['cut'])} | {tl['n_hot']:,} | "
          f"{tl['share_of_Z']:.4f} | {tl['frozen_hot']:.2f} | "
          f"{tl['frozen_rest']:.2f} | {tl['any_frozen_hot']:.4f} | "
          f"{tl['any_frozen_rest']:.4f} | {tl['win_hot']:.1f} | "
          f"{tl['win_rest']:.1f} |")

    A("\n**Is the tail a payoff rather than a cure.** `bal(t_B)/bal(t_A)` is "
      "what the balance did across the window; a cure leaves it near one, a "
      "retirement drives it to nothing. Field 44 is the zero-balance code, "
      "which §6.2.6.3 ruled needed no filter **for a different purpose**. "
      "Neither column needs a threshold picked by hand.\n")
    A("| archive | balance ratio, hot p10 | p50 | p90 | rest p10 | p50 | p90 | "
      "ratio < 1% , hot | rest | field 44 set in window, hot | rest |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        tl = a["N"].get("tail") or {}
        if not tl:
            continue
        A(f"| {a['name']} | "
          + " | ".join(_f(v, 3) for v in tl["bratio_hot"]) + " | "
          + " | ".join(_f(v, 3) for v in tl["bratio_rest"])
          + f" | {tl['tiny_hot']:.4f} | {tl['tiny_rest']:.4f} | "
          f"{tl['zb_hot']:.4f} | {tl['zb_rest']:.4f} |")

    A(f"\n**The {N_EXAMPLES} largest by `|omega|` per archive, printed.**\n")
    A("| archive | omega | window months | frozen months | balance at `t_A` | "
      "at `t_B` | ratio | field 44 in window |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for e in a["N"].get("examples", []):
            A(f"| {a['name']} | {e['omega']:+.4e} | {e['window']:,} | "
              f"{e['frozen']:,} | {e['bal_A']:,.2f} | {e['bal_B']:,.2f} | "
              f"{_f(e['bratio'], 3)} | {'yes' if e['zb'] else 'no'} |")

    A("\n### 2.2 The floor and the signal live at different balances\n")
    A("**`omega` is a log ratio, so its noise scales inversely with the "
      "balance.** A fixed dollar deviation on a 3,385 balance is a large log "
      "move; the same deviation on a 300,000 one is nothing. The floor's tail "
      "is small balances and modifications happen on live mortgages, so a "
      "floor drawn from one balance regime does not judge a signal drawn from "
      "another. **`N` matched** is the same floor restricted to the p10-p90 "
      "balance range of the arm it is judging.\n")
    A("| archive | floor balance p10 | p50 | p90 | floor tail p50 | "
      "floor rest p50 | arm | signal balance p10 | p50 | p90 | matched range | "
      "n | `N` matched | **`sqrt(Z)/sqrt(N)` matched** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        n = a["N"]
        tl = n.get("tail") or {}
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            nm = d["N_matched"]
            A(f"| {a['name']} | "
              + " | ".join(f"{v:,.0f}" for v in n.get("balA_q", [0, 0, 0]))
              + f" | {tl.get('balA_hot', [0, 0, 0])[1]:,.0f} | "
              f"{tl.get('balA_rest', [0, 0, 0])[1]:,.0f} | {tag} | "
              + " | ".join(f"{v:,.0f}" for v in d["balA_q"])
              + f" | {nm['lo']:,.0f}-{nm['hi']:,.0f} | {nm['n']:,} | "
              f"{_f(nm['Z'])} | **{_f(d['ratio_matched'], 3)}** |")

    A("\n### 2.3 Does the variance converge, and does anything else\n")
    A("**Three defensible population choices moved the modification arm's "
      "ratio through 1.45, 54.70 and 1,008.** At that point the question is "
      "not which population is right, it is whether `2*Var` estimates "
      "anything on this distribution. `omega` on the floor arm spans five "
      "orders of magnitude between its median and its maximum; B3's `Z` was "
      "written for CIP deviations, which are bounded basis-point quantities.\n")
    A("The table draws random subsamples at each size, 21 times, and reports "
      "the median with the 10th and 90th percentiles. **A statistic that "
      "estimates a population parameter settles down as `n` grows. One that "
      "reports how far into the tail the draw reached does not.** `MAD` is "
      "the normal-consistent median absolute deviation, carried beside it "
      "because if one converges and the other does not, that is the finding.\n")
    A("| archive | arm | n | `2*Var` p10 | median | p90 | spread | "
      "`MAD` p10 | median | p90 | spread |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag, src in (("N (clean cures)", a["N"]),
                         ("mod", a["arms"]["mod"])):
            for c in src.get("conv", []):
                vs = (c["var_hi"] / c["var_lo"]) if c["var_lo"] > 0 else float("inf")
                ms = (c["mad_hi"] / c["mad_lo"]) if c["mad_lo"] > 0 else float("inf")
                A(f"| {a['name']} | {tag} | {c['n']:,} | {_f(c['var_lo'])} | "
                  f"{_f(c['var_med'])} | {_f(c['var_hi'])} | {vs:.1f}x | "
                  f"{_f(c['mad_lo'])} | {_f(c['mad_med'])} | "
                  f"{_f(c['mad_hi'])} | {ms:.1f}x |")

    A("\n**The same ratio computed with `MAD` on both sides.** Same object on "
      "the signal and on the floor, which is what B3's shape requires; the "
      "only change is the scale estimator.\n")
    A("| archive | arm | `MAD` signal | `MAD` floor | **`MAD` ratio** | "
      "`sqrt(Z)/sqrt(N)` | `sqrt(Z)/sqrt(N)` matched |")
    A("|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {_f(d['mad'])} | {_f(a['N']['mad'])} | "
              f"**{_f(d['ratio_mad'], 3)}** | {_f(d['ratio'], 3)} | "
              f"{_f(d['ratio_matched'], 3)} |")

    A("\n## 3. The headline, `sqrt(Z)/sqrt(N)`\n")
    A("§18.5's map: above 3 is B8-1's **necessary** condition, not B8-1. "
      "Between 1 and 3 is a recorded failure. At or below 1 the signal is "
      "under the floor. **None of those changes the floor, the cells or the "
      "statistic.**\n")
    A("| archive | arm | loops | **measurable** | `Z` | `sqrt(Z)` | "
      "**`sqrt(Z)/sqrt(N)`** | omega p10 | p50 | p90 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {d['loops']:,} | "
              f"**{d['measurable']:,}** | {_f(d['Z'])} | "
              f"{_f(np.sqrt(d['Z']))} | **{_f(d['ratio'], 3)}** | "
              + " | ".join(_f(v, 3) for v in d["q"]) + " |")

    A("\n## 4. `M`, the matched cells, **not the floor**\n")
    A("Cells are `(arm, missed months, months to cure)` on §3.3's coarse grid. "
      "**No contract quantity is a cell key** (§18.4): `omega` is a function "
      "of the contract, so cutting on it would drive the within-cell variance "
      "to zero and the ratio to infinity, which is C11's criterion B in a "
      "different costume. `M < N` would mean the cells are cut too fine or a "
      "contract quantity leaked in, and §18.5 sends that back to the keys "
      "rather than accepting the number.\n")
    A(f"Cells smaller than {MIN_CELL} are dropped and counted.\n")
    A("| archive | arm | cells | used | loops used | dropped, small cell | "
      "`M` | `sqrt(M)` | `sqrt(Z)/sqrt(M)` | `M` vs `N` |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        nn = a["N"]["Z"]
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            m = d["M"]
            rel = ("n/a" if not (np.isfinite(m["M"]) and np.isfinite(nn)
                                 and nn > 0)
                   else ("**M < N**" if m["M"] < nn else f"{m['M'] / nn:.1f}x"))
            A(f"| {a['name']} | {tag} | {m['cells']:,} | {m['cells_used']:,} | "
              f"{m['loops_used']:,} | {m['loops_dropped_small']:,} | "
              f"{_f(m['M'])} | {_f(np.sqrt(m['M']))} | "
              f"{_f(d['ratio_M'], 3)} | {rel} |")

    A("\n## What this does not decide\n")
    A("- **B8-1 is not read here.** This supplies its floor. B8-1 needs both "
      "`q` grids of §3.3 and §6's windows.")
    A("- **`M` does not enter any ratio that B8-1 uses** (§18.2).")
    A("- The per-class floor `sqrt(Z(a))/sqrt(N(a))` of §15.4 is **not** "
      "computed here; it is gated by C9 and belongs to B8-4a.")
    A("- Loans carrying both zero-interest balances are **refused** (C13), "
      "count in section 2's neighbour and in `b8_loop_omega.md` §1.\n")
    return "\n".join(Ls) + "\n"


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails: list[str] = []

    # -- Z, both ways, against hand arithmetic ----------------------------
    x = np.array([1.0, 2.0, 4.0, 8.0])
    # 2*Var: mean 3.75, var = (7.5625+3.0625+0.0625+18.0625)/4 = 7.1875
    if abs(zed(x) - 14.375) > 1e-12:
        fails.append(f"zed = {zed(x)}, hand computation 14.375")
    if abs(zed_by_enumeration(x) - 14.375) > 1e-12:
        fails.append(f"enumeration = {zed_by_enumeration(x)}, hand 14.375")
    # a constant vector has Z = 0 exactly, both ways
    if zed(np.full(9, 2.5)) != 0.0 or zed_by_enumeration(np.full(9, 2.5)) != 0.0:
        fails.append("Z on a constant vector is not exactly zero")
    ck = check_enumeration(x)
    if not ck["ok"]:
        fails.append(f"check_enumeration says the two disagree: {ck}")
    # **And the gate must be able to fire.** Both quantities are the same
    # number mathematically, so no input can distinguish them: a
    # `check_enumeration` that computed `2*Var` twice would agree perfectly and
    # look like a passing gate forever. So the disagreement is injected. Pit
    # 33's rule: after adding a check, make the thing it should catch happen.
    _real = globals()["zed_by_enumeration"]
    try:
        globals()["zed_by_enumeration"] = lambda v: _real(v) * 1.001
        fired = check_enumeration(x)
    finally:
        globals()["zed_by_enumeration"] = _real
    if fired["ok"]:
        fails.append("the enumeration gate passed a 0.1 per cent "
                     "disagreement; it is comparing a number to itself")

    # -- the cells: no contract key can reach `cell_of` -------------------
    # **A signature check, not a comment.** §18.4's ban is the load-bearing
    # part of `M`, and a ban enforced only by prose is enforced by nobody.
    import inspect
    params = list(inspect.signature(cell_of).parameters)
    if params != ["arm", "missed", "cure"]:
        fails.append(f"cell_of takes {params}; §18.4 allows exactly "
                     "['arm', 'missed', 'cure'] and every one of them is a "
                     "path quantity")
    # cells must separate, or `M` is one big cell
    ar = np.array([0, 0, 0, 1])
    ms = np.array([1, 5, 20, 1])
    cu = np.array([0, 4, 20, 0])
    ids = cell_of(ar, ms, cu)
    if len(set(ids.tolist())) != 4:
        fails.append(f"cell_of collapsed four distinct paths to {set(ids.tolist())}")

    # -- M: weighting, and the small-cell drop ----------------------------
    om = np.concatenate([np.zeros(25), np.ones(25) * 3.0, np.array([9.0] * 5)])
    cl = np.concatenate([np.zeros(25, int), np.ones(25, int),
                         np.full(5, 2, int)])
    m = emm(om, cl)
    if m["cells"] != 3 or m["cells_used"] != 2:
        fails.append(f"emm used {m['cells_used']} of {m['cells']} cells, "
                     "expected 2 of 3")
    if m["loops_dropped_small"] != 5:
        fails.append(f"emm dropped {m['loops_dropped_small']} loops in small "
                     "cells, expected 5")
    if abs(m["M"]) > 1e-12:
        fails.append(f"emm on two constant cells read {m['M']}, expected 0")
    # a cell with spread must move it, or the weighting is inert
    om2 = om.copy()
    om2[:25] = np.linspace(0.0, 1.0, 25)
    m2 = emm(om2, cl)
    if not m2["M"] > 0:
        fails.append("emm did not react to a cell with spread")

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
        pos, tab = Z8._flat_curve(months)
        cc = clean_cure_loops(c)
    a = analyse(zp.stem, cache_root=cr, pos=pos, tab=tab)

    # the clean-cure arm must exist and t_M must be the first delinquent month
    if cc["t_A"].size == 0:
        fails.append("the fixture yields no clean cure, so `N` is an empty "
                     "set and every ratio below is nan")
    if cc["t_A"].size and not bool((cc["t_M"] == cc["t_A"] + 1).all()):
        fails.append("t_M on the clean-cure arm is not the first delinquent "
                     "month; §18.3 N2 is not implemented")
    if a["N"]["measurable"] == 0:
        fails.append("no clean cure is measurable on the fixture, so `N` is "
                     "nan and the gate below proves nothing")
    # **The ideal path's loop sum is zero by arithmetic** (§14.5's B8-0a(i)),
    # so on a fixture built to it `N` is machine noise, not a number. If this
    # ever reads like a real quantity the ideal-path screen has stopped
    # screening. The old population, drawn on B8-0a(ii), read 1e-2 here.
    elif not (a["N"]["Z"] < 1e-10):
        fails.append(f"N on the ideal-path arm reads {a['N']['Z']:.3e}; the "
                     "fixture's clean cures reinstate exactly onto the "
                     "schedule so it must be machine noise")
    # -- MAD, against hand arithmetic and against a heavy tail ------------
    # 1, 2, 3, 4, 5: median 3, deviations 2,1,0,1,2, their median 1
    if abs(mad_scale(np.array([1., 2., 3., 4., 5.])) - 1.4826) > 1e-12:
        fails.append(f"mad_scale = {mad_scale(np.array([1.,2.,3.,4.,5.]))}, "
                     "hand computation 1.4826")
    # **and it must be the thing the variance is not**: one outlier moves
    # `2*Var` by orders and `MAD` not at all. If that stops being true the two
    # columns of section 2.3 are the same column.
    base = np.concatenate([np.arange(999.0), np.array([1e6])])
    plain = np.arange(1000.0)
    if not (zed(base) > 100 * zed(plain)):
        fails.append("one outlier in a thousand did not move `2*Var`; the "
                     "convergence table cannot show anything")
    if abs(mad_scale(base) / mad_scale(plain) - 1.0) > 0.01:
        fails.append(f"one outlier in a thousand moved MAD by "
                     f"{mad_scale(base) / mad_scale(plain):.3f}x; it is not "
                     "the robust half of the comparison")

    # the balance match must actually restrict, or column 2.2 is a copy of `N`
    nm = a["arms"]["mod"]["N_matched"]
    if nm["n"] >= a["N"]["measurable"]:
        fails.append(f"the balance-matched floor kept {nm['n']} of "
                     f"{a['N']['measurable']} loops, so it restricts nothing "
                     "and section 2.2 is `N` printed twice")
    if a["N_all"]["measurable"] <= a["N"]["measurable"]:
        fails.append("the ideal-path screen removed nothing, so the two "
                     "floor populations are the same and the double report "
                     "is two copies of one number")
    for tag in ("pooled", "mod", "defer"):
        if not a["arms"][tag]["enum"]["ok"]:
            fails.append(f"the two computations of Z disagree on {tag}: "
                         f"{a['arms'][tag]['enum']}")
    if not a["N"]["enum"]["ok"]:
        fails.append(f"the two computations of Z disagree on N: "
                     f"{a['N']['enum']}")
    print(f"  fixture: N over {a['N']['measurable']} clean cures = "
          f"{a['N']['Z']:.4e}; pooled Z = {a['arms']['pooled']['Z']:.4e}; "
          f"ratio {a['arms']['pooled']['ratio']:.3f}", file=sys.stderr)

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    # -- the tail diagnostic must actually discriminate -------------------
    tr = trimmed_floor(np.concatenate([np.zeros(98), np.array([50.0, -50.0])]))
    if not (tr[0]["Z"] > 100 * tr[-1]["Z"]):
        fails.append(f"trimming 5 per cent off a sample that is 98 per cent "
                     f"zeros and two outliers moved the floor from "
                     f"{tr[0]['Z']:.3e} to {tr[-1]['Z']:.3e}; it cannot see a "
                     "tail")
    if tr[0]["n"] != 100 or tr[-1]["n"] != 90:
        fails.append(f"trim kept {tr[0]['n']} and {tr[-1]['n']}, expected "
                     "100 and 90")
    # freezes, on a hand-built two-loan case
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c2:
        fz = freeze_counts(c2, cc, r=None) if cc["t_A"].size else np.zeros(0)
        bal = K.zero_interest_split(c2)[0]
        # count them independently, the slow way, on the same windows
        want = np.array([
            sum(1 for x in range(int(cc["t_A"][i]) + 1, int(cc["t_B"][i]) + 1)
                if bal[x] == bal[x - 1])
            for i in range(cc["t_A"].size)], dtype=np.int64)
    if cc["t_A"].size and not np.array_equal(fz, want):
        fails.append("freeze_counts disagrees with a direct count on the "
                     "same windows")

    for need in ("## 1. The gate", "## 2. `N`, the zero calibration",
                 "### 2.1 `N` is a tail statistic",
                 "### 2.2 The floor and the signal live at different balances",
                 "### 2.3 Does the variance converge",
                 "## 4. `M`, the matched cells"):
        if need not in txt:
            fails.append(f"render omits `{need}`")

    for m_ in fails:
        print("FAIL " + m_, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, Z agrees both ways and the floor arm runs end to end",
          file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: N over {a['N']['measurable']:,} clean cures = "
              f"{a['N']['Z']:.4e}, pooled ratio "
              f"{a['arms']['pooled']['ratio']:.3f}", file=sys.stderr)
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
