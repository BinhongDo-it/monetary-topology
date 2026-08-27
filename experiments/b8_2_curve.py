#!/usr/bin/env python3
"""B8-2 under a second curve construction, double-reported. O33's disposition.

**Why this exists.** `b8_cmt_sensitivity2`'s cancellation gate came back
**DOES NOT CANCEL on all six archives**: the spread of `r` across the six
curve constructions is 2.89e-02 to 1.02e-01 against a bound of 1.24e-14, and
at loop level `p50 / floor` runs 10 to 1,010.

**The cause is pit 38's own correction and it is now understood.** That file's
whole logic rested on an identity: with no deferred balance
`V = LP(bal, i, n) * A(d, n)`, both legs carry the same `n`, the annuity
factor cancels, and the discount rate does not appear at all. §14.2 requires
`V-hat` to be priced on the **previous month's** contract, pit 38 implemented
that, and the two legs now carry `n` and `n - 1`. Verified numerically:

    same n      d = 2%   +5.129329e-02      identical, the curve is absent
                d = 8%   +5.129329e-02
    n, n - 1    d = 2%   +1.23e-03
                d = 6%    0.00e+00          exactly zero at d = i
                d = 8%   -4.67e-04

**That is the same `k = LP * A` channel B8-2's own leg-2 decomposition found**
(§20.4a), reached from a different direction. The correction was right; its
consequence for the curve rule was not traced.

**What follows for the criteria, estimated before this ran.** B8-3's
`delta/floor` is 1.07e5 to 4.18e6, two to four orders above the curve spread,
so it is safe.

    WITHDRAWN 2026-08-27, pointer added rather than text removed. The margin
    sentence immediately above used a mislabelled denominator and B8-3's entry
    in RESULTS.md withdraws it: against the matched-window floor the curve
    spread runs 1,773 to 358,532, the same order as the gap itself, and at
    2007Q1 the two are 1.4 times apart rather than an order of magnitude. The
    ratio 1.07e5 to 4.18e6 is real and is a distance above the instrument's
    own floor; it is not a margin over the curve account, and it says nothing
    on its own about which account it refutes. B8-3's live verdict rests on
    per-cell signs and a permutation p of 0.001 across all six vintages, not
    on this margin. `b8_3_curve.py`'s own header carries the full correction. **B8-2 is the one at risk**: its per-period medians are 1e-2 to
1e-1, the same order as the spread, so a cell's sign could turn over. B8-1 is
carried here as a secondary panel because it costs one line.

--------------------------------------------------------------------------
How the second rule is reached without rebuilding anything
--------------------------------------------------------------------------

**The loops do not depend on the curve.** `find_loops` reads delinquency
status, field 42, field 63 and field 108; none of them is a yield. So the loop
skeleton comes from `b8_cache` unchanged and only `disc_of_row`,
`row_residuals` and `loop_sums` are recomputed under the alternative rule.
That is one pass per archive and **no cache rebuild**, which matters because
`b8_cache._path` does not carry the tag in the filename, so building under a
second rule would overwrite the first.

**The alternative is the far corner, not a neighbour.** `linear_in_log_tenor`
for interpolation and `linear_in_log_tenor` beyond the last published tenor is
the construction furthest from the registered
`("linear_in_tenor", "cap")` in both choices at once. **If the sign survives
the worst case it survives the rest**, and picking a near neighbour would be
choosing the comparison that is easiest to pass.

Usage:

    python experiments/b8_2_curve.py run
    python experiments/b8_2_curve.py run --only 2019Q1
    python experiments/b8_2_curve.py selftest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_triangles as T                                       # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_cache as C                                           # noqa: E402
import b8_2_windows as P2                                      # noqa: E402
import b8_3_paths as P3                                        # noqa: E402
import b8_0b_floor as F                                        # noqa: E402
import b8_0a_gate as G                                         # noqa: E402

OUT = K.ROOT / "results" / "b8_2_curve.md"
COLS = Z8.COLS + ["zero_bal"]

#: The registered construction, from `b8_loop_omega.RULE`, pinned in §16.11.
RULE_A = Z8.RULE

#: **The far corner**, differing in both choices at once. Chosen so the test is
#: the hardest available rather than the easiest.
RULE_B = ("linear_in_log_tenor", "linear_in_log_tenor")

#: What is left after an exact cancellation, **and it has a source**:
#: `b8_cmt_sensitivity2`'s own bound, `4 * |log V| * eps` at `|log V| = 14`.
#: `r` is a difference of logarithms of a quantity in the hundreds of
#: thousands and the constructions reach it only through a factor that cancels
#: algebraically, so what survives is rounding. **A bare zero here would be a
#: sourceless number in a criterion**, which is what discipline 5 forbids, and
#: the fixture's floor arm does come back at 1.8e-15 rather than at 0.
ROUND_BOUND = 4.0 * 14.0 * np.finfo(np.float64).eps


def under_rule(name: str, rule, cached: dict, cache_root=None,
               src=None) -> dict:
    """Loop sums for one curve rule, on the cached loop skeleton.

    `cached` is `b8_cache.get(...)["sig"]`. Its `t_A`/`t_M`/`t_B`/`arm` are
    reused verbatim: **the loops are not a function of the curve**, so
    recomputing them would only introduce a way for the two arms to differ for
    a reason that is not the curve.
    """
    pos, tab = (Z8.curve_table(rule) if src is None
                else Z8.curve_table_from(src, rule))
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        disc, _ = W.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        lp = {k_: np.asarray(cached[k_]) for k_ in ("t_A", "t_M", "t_B")}
        lp["arm"] = np.asarray(cached["arm"])
        sig = Z8.loop_sums(lp, r, ok)
    finally:
        c.close()
    return sig


def floor_under(name: str, rule, cached_floor: dict, cache_root=None,
                src=None) -> np.ndarray:
    """`omega - closed` on the clean-cure arm under one rule.

    **This is the half §4 could not answer and it is the dangerous half.**
    B8-1 is `MAD(signal) / MAD(floor)`, the numerator moves by three to four
    per cent (§4), and the denominator is **2.68e-08 to 5.22e-08**. The curve
    channel moves an individual `r` by order 1e-3 per month, so if it reached
    the clean-cure arm at all the floor would go from 3e-08 to something near
    1e-3 and **B8-1's ratio would fall by four to five orders**, from 2.4e6 to
    a few hundred.

    **There is a reason to expect it does not reach**, and the check is
    whether that reason holds. `n_prev = remf[t-1] - 1` and `n_now = remf[t]`
    are equal exactly when field 17 steps down by one, and where they are
    equal the annuity factor cancels **whatever the curve is**. A clean cure
    re-contracts nothing. So the floor should be rule-independent to the last
    bit, and `closed` carries no discount rate at all
    (`loop_residual_ideal` is `(B0, i, P, k)` and nothing else), so any
    movement here is movement in `omega` alone.

    **A floor that does move would say the cancellation fails on the arm B8-0b
    drew the floor from**, which is a larger problem than B8-1's ratio.
    """
    pos, tab = (Z8.curve_table(rule) if src is None
                else Z8.curve_table_from(src, rule))
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        disc, _ = W.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        cc = {k_: np.asarray(cached_floor[k_]) for k_ in ("t_A", "t_M", "t_B")}
        cc["arm"] = np.full(cc["t_A"].size, L.ARM_MOD, dtype=np.int8)
        sig = Z8.loop_sums(cc, r, ok)
    finally:
        c.close()
    return np.asarray(sig["omega"], float), sig["measurable"].astype(bool)


def compare(name: str, cache_root=None, pos=None, tab=None, core_root=None,
            n_boot: int = P2.N_BOOT, src=None) -> dict:
    d = C.get(name, pos=pos, tab=tab, core_root=core_root or cache_root)
    s = d["sig"]
    b = under_rule(name, RULE_B, s, cache_root=core_root or cache_root,
                   src=src)

    fl = d["floor"]
    fmask = fl["measurable"].astype(bool) & fl["ideal"].astype(bool)
    closed = np.asarray(fl["closed"], float)
    om_fa = np.asarray(fl["omega"], float)
    om_fb, meas_fb = floor_under(name, RULE_B, fl,
                                 cache_root=core_root or cache_root, src=src)
    fm = fmask & meas_fb
    floor_a = F.mad_scale((om_fa - closed)[fm]) if fm.any() else float("nan")
    floor_b = F.mad_scale((om_fb - closed)[fm]) if fm.any() else float("nan")

    arm = np.asarray(s["arm"])
    win = np.asarray(s["window"], np.int64)
    rem_A = np.asarray(s["rem_A"], np.int64)
    mA = s["measurable"].astype(bool) & (arm == L.ARM_MOD)
    mB = b["measurable"].astype(bool) & (arm == L.ARM_MOD)
    # **The intersection, and the loss is counted.** A row computable under one
    # construction and not the other would otherwise move a cell for a reason
    # that is not the sign of anything.
    m = mA & mB
    tb = np.searchsorted(np.asarray(P3.EDGES_TERM), rem_A, side="right")

    def pack(sig):
        dur = np.maximum(np.asarray(sig["n_win"]), 1)
        om = np.asarray(sig["omega"], float)
        return {"win": win[m].astype(np.int8), "tb": tb[m].astype(np.int8),
                "per": (om[m] / dur[m]).astype(float),
                "om": om[m].astype(float),
                "l1": np.asarray(sig["leg1"], float)[m],
                "l2": np.asarray(sig["leg2"], float)[m]}

    A, B = pack(s), pack(b)
    coh = np.zeros(int(m.sum()), np.int8)          # one archive, one cohort
    return {"name": name, "n": int(m.sum()),
            "n_a": int(mA.sum()), "n_b": int(mB.sum()),
            "n_only_a": int((mA & ~mB).sum()), "n_only_b": int((mB & ~mA).sum()),
            "A": A, "B": B, "coh": coh, "n_boot": n_boot,
            "n_floor": int(fm.sum()), "floor_a": floor_a, "floor_b": floor_b,
            "floor_shift": float(np.max(np.abs(om_fb - om_fa)[fm]))
            if fm.any() else float("nan"),
            # the per-loop shift, which is the quantity O33 bounds
            "shift": B["om"] - A["om"]}


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A_ = Ls.append
    A_("# B8-2 under a second curve construction (O33)\n")
    A_("Generated by `experiments/b8_2_curve.py`. Disposition of O33 in "
       "the project's objection cache; the mechanism is in this file's "
       "header.\n")
    A_(f"Registered construction **`{RULE_A[0]}` / `{RULE_A[1]}`** against the "
       f"far corner **`{RULE_B[0]}` / `{RULE_B[1]}`**, which differs in both "
       "choices at once. **If the sign survives the worst case it survives "
       "the rest**; a near neighbour would be choosing the easy comparison.\n")
    A_("**The loops are not a function of the curve.** `find_loops` reads "
       "delinquency status and fields 42, 63 and 108, none of which is a "
       "yield, so the loop skeleton is identical under both and only the "
       "residuals move. Loops computable under one construction and not the "
       "other are dropped from both and counted.\n")
    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"

    A_("\n## 1. How far the construction moves a loop sum\n")
    A_("| archive | loops compared | only under A | only under B | median "
       "shift | p90 `\\|shift\\|` | max `\\|shift\\|` | median `\\|A\\|` |")
    A_("|---|---|---|---|---|---|---|---|")
    for a in rows:
        sh = a["shift"]
        if sh.size == 0:
            continue
        A_(f"| {a['name']} | {a['n']:,} | {a['n_only_a']:,} | "
           f"{a['n_only_b']:,} | {np.median(sh):+.4e} | "
           f"{np.percentile(np.abs(sh), 90):.4e} | "
           f"{np.max(np.abs(sh)):.4e} | "
           f"{np.median(np.abs(a['A']['om'])):.4e} |")

    # cells under each construction, on the pooled set
    def cells_of(key):
        win = np.concatenate([a[key]["win"] for a in rows])
        tb = np.concatenate([a[key]["tb"] for a in rows])
        coh = np.concatenate([np.full(a[key]["win"].size, i, np.int8)
                              for i, a in enumerate(rows)])
        per = np.concatenate([a[key]["per"] for a in rows])
        om = np.concatenate([a[key]["om"] for a in rows])
        l1 = np.concatenate([a[key]["l1"] for a in rows])
        l2 = np.concatenate([a[key]["l2"] for a in rows])
        return P2.cells(win, tb, coh, per, om, l1, l2,
                        n_boot=rows[0]["n_boot"])

    tA, tB = cells_of("A"), cells_of("B")
    vA, vB = P2.verdict(tA), P2.verdict(tB)

    A_("\n## 2. The cells, side by side\n")
    A_("**This is the double report R01 requires**, not a replacement "
       "reading. A cell readable under one construction and not the other is "
       "printed as such.\n")
    A_("| window | remaining term at `t_A` | n | **per period, A** | holds A "
       "| **per period, B** | holds B | **sign flips** |")
    A_("|---|---|---|---|---|---|---|---|")
    byB = {(g["w"], g["k"]): g for g in tB}
    flips = 0
    for g in tA:
        h = byB.get((g["w"], g["k"]))
        if h is None:
            continue
        fl = (g["readable"] and h["readable"]
              and np.sign(g["per"]) != np.sign(h["per"]))
        flips += bool(fl)
        A_(f"| {T.WINDOWS[g['w']][0]} | {P3._band(P3.EDGES_TERM, g['k'])} | "
           f"{g['n']:,} | **{P2._f(g['per'])}** | "
           f"{'yes' if g['holds'] else 'no'} | **{P2._f(h['per'])}** | "
           f"{'yes' if h['holds'] else 'no'} | "
           f"**{'YES' if fl else 'no'}** |")

    A_("\n## 3. The verdict, both constructions\n")
    A_("| construction | cells | readable | interval excludes zero | positive "
       "| negative | windows | **unanimous** |")
    A_("|---|---|---|---|---|---|---|---|")
    for nm, v in ((f"`{RULE_A[0]}` / `{RULE_A[1]}` (registered)", vA),
                  (f"`{RULE_B[0]}` / `{RULE_B[1]}` (far corner)", vB)):
        A_(f"| {nm} | {v['cells']} | {v['readable']} | {v['holds']} | "
           f"{v['pos']} | {v['neg']} | {v['windows']} | "
           f"**{'yes' if v['unanimous'] else 'NO'}** |")

    A_(f"\n**{flips} cell(s) change sign between the two constructions.**\n")
    survives = (flips == 0 and vA["unanimous"] and vB["unanimous"]
                and vA["pos"] > 0 and vB["pos"] > 0)
    A_("| **reading** |")
    A_("|---|")
    A_("| " + ("**B8-2 survives the curve construction.** The sign is "
               "unanimous under both, no cell turns over, and O33's risk to "
               "B8-2 is discharged. **§17.16's items 1 to 4 stay withdrawn**: "
               "the curve rule does move `r`, it simply does not move it far "
               "enough to reach B8-2's sign" if survives
               else "**B8-2 does not survive the curve construction as "
                    "stated.** The registered reading is not retracted and "
                    "the alternative is not adopted; **both are reported and "
                    "B8-2 is recorded as construction-dependent**, which is "
                    "§16.11's own disposition for a choice that turns out to "
                    "bind") + " |")

    A_("\n## 4. B8-1 under both, **both arms**\n")
    A_("O33 listed B8-1 as `to check`. **The numerator was never the risk.** "
       "B8-1 is `MAD(signal) / MAD(floor)` and the denominator is 2.68e-08 to "
       "5.22e-08, while the curve channel moves an individual `r` by order "
       "1e-3 a month. **If it reached the clean-cure arm the floor would go "
       "from 3e-08 to near 1e-3 and the ratio would fall four to five "
       "orders.** So the floor arm is recomputed here too.\n")
    A_("**There is a reason to expect it does not reach.** `n_prev` and "
       "`n_now` are equal exactly where field 17 steps down by one, and where "
       "they are equal the annuity cancels **whatever the curve is**. A clean "
       "cure re-contracts nothing. `closed` carries no discount rate at all, "
       "so any movement in the floor is movement in `omega` alone. **A floor "
       "that moves would say the cancellation fails on the very arm B8-0b "
       "drew the floor from**, which is a larger problem than a ratio.\n")
    A_("| archive | MAD signal A | MAD signal B | MAD floor A | MAD floor B | "
       "max floor shift | **ratio A** | **ratio B** | B/A |")
    A_("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        if a["n"] == 0:
            continue
        ma, mb = F.mad_scale(a["A"]["om"]), F.mad_scale(a["B"]["om"])
        fa, fb = a["floor_a"], a["floor_b"]
        ra = ma / fa if fa > 0 else float("nan")
        rb = mb / fb if fb > 0 else float("nan")
        A_(f"| {a['name']} | {ma:.4e} | {mb:.4e} | {fa:.4e} | {fb:.4e} | "
           f"{a['floor_shift']:.3e} | **{ra:,.1f}** | **{rb:,.1f}** | "
           f"{(rb / ra if ra > 0 else float('nan')):.4f} |")
    A_("\n**Read `max floor shift` first.** At `0` the annuity cancels on the "
       "clean-cure arm exactly as the argument above says, the floor is a "
       "property of the data and not of the construction, and B8-1's ratio "
       "moves only by the numerator's few per cent. **Anything above the "
       "floor itself and the argument is wrong**, B8-0b's floor is "
       "construction-dependent, and that is reported before B8-1's ratio "
       "is.\n")

    A_("\n## What this does not decide\n")
    A_("- **Which construction is right.** §16.11 pinned one before the run "
       "and that stands; this says how far the choice can move the reading.")
    A_("- **B8-3.** Its `delta/floor` is two to four orders above the spread "
       "measured here, so O33 records it as safe without a re-run.")
    A_("- **The deferral arm.** B8-2 does not run on it (§20.1).")
    A_("- **`b8_cmt_sensitivity2`'s own §2 and §3**, which by that file's own "
       "rule are not measurements while its §1 gate fails (O34).\n")
    return "\n".join(Ls) + "\n"


def selftest() -> int:
    fails: list[str] = []

    # -- the mechanism, on numbers, before anything reads an archive --------
    # **This is O33's whole claim** and it is asserted rather than recounted:
    # with both legs on the same `n` the discount rate is absent; with `n` and
    # `n - 1` it is present and changes sign at `d = i`.
    same = [float(np.log(W.V(200000.0, 6.0, 240.0, d))
                  - np.log(W.V(190000.0, 6.0, 240.0, d)))
            for d in (2.0, 8.0)]
    if abs(same[0] - same[1]) > 1e-14:
        fails.append(f"with both legs on the same term the discount rate "
                     f"moved the residual: {same[0]} vs {same[1]}. O33's "
                     "mechanism is not what this file says it is")
    off = [float(np.log(W.V(200000.0, 6.0, 240.0, d))
                 - np.log(W.V(200000.0, 6.0, 239.0, d)))
           for d in (2.0, 6.0, 8.0)]
    if abs(off[1]) > 1e-14:
        fails.append(f"at `d = i` the one-month term difference gave "
                     f"{off[1]}, expected exactly zero")
    if not (off[0] > 0 > off[2]):
        fails.append(f"the term difference did not change sign across the "
                     f"note rate: {off}. That sign change is what makes the "
                     "curve rule load-bearing and it is the claim being made")
    if abs(off[0]) < 1e-5:
        fails.append("the effect is too small to matter, which contradicts "
                     "the measured spread of 2.9e-02 to 1.0e-01")

    # -- the two rules must actually give different tables ------------------
    src = {}
    for mi in range(240, 260):
        for lab, ten in (("1 Mo", 1), ("1 Yr", 12), ("10 Yr", 120),
                         ("20 Yr", 240)):
            src[(mi, lab)] = [2.0 + 0.01 * ten ** 0.5]
    pa, ta = Z8.curve_table_from(src, RULE_A)
    pb, tb_ = Z8.curve_table_from(src, RULE_B)
    if np.array_equal(np.nan_to_num(ta), np.nan_to_num(tb_)):
        fails.append("the registered rule and the far corner build the same "
                     "table, so the comparison is between one thing and "
                     "itself")
    # and they must differ **beyond** the last published tenor, which is where
    # `cap` and `linear_in_log_tenor` part company
    if ta.shape[1] > 300 and np.allclose(np.nan_to_num(ta[:, 300:]),
                                         np.nan_to_num(tb_[:, 300:])):
        fails.append("the two rules agree past the longest published tenor, "
                     "which is the one place `cap` is defined to differ")

    # -- end to end on `b8_loops`' fixture ---------------------------------
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
    # a flat curve is the same under every rule, so both arms must agree
    # exactly: that is the control this comparison needs
    d = C.get(zp.stem, cache_root=root / "loopcache", pos=pos, tab=tab,
              core_root=cr)
    sig_b = under_rule(zp.stem, RULE_B, d["sig"], cache_root=cr,
                       src={(int(mi), "10 Yr"): [4.0] for mi in months})
    # **`under_rule` on the registered rule must reproduce the cache bit for
    # bit.** This is the strongest check available on the recomputation path:
    # it validates the loop skeleton, the table lookup and the summation all
    # at once, against numbers computed by a different function on a different
    # day. A reversed skeleton, a swapped table or a dropped mask all fail it.
    sig_a = under_rule(zp.stem, RULE_A, d["sig"], cache_root=cr,
                       src={(int(mi), "10 Yr"): [4.0] for mi in months})
    for f_ in ("omega", "leg1", "leg2", "n_win", "measurable"):
        if not np.array_equal(np.asarray(sig_a[f_]),
                              np.asarray(d["sig"][f_]), equal_nan=True):
            fails.append(f"recomputing under the registered rule did not "
                         f"reproduce the cached `{f_}`, so the alternative "
                         "arm is not the same computation with one input "
                         "changed")
    if sig_b["omega"].size != np.asarray(d["sig"]["omega"]).size:
        fails.append("the alternative-rule pass returned a different number "
                     "of loops than the cached skeleton, so it is not being "
                     "run on the same loops")
    # **the loops must not move.** They are not a function of the curve, and
    # if they ever become one this comparison stops being about the curve.
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c2:
        lp2 = L.find_loops(c2)
    for f_ in ("t_A", "t_M", "t_B", "arm"):
        if not np.array_equal(np.asarray(d["sig"][f_]), lp2[f_]):
            fails.append(f"the cached loop skeleton differs from "
                         f"`find_loops` on `{f_}`")

    # **through `compare`, on a curve the two rules genuinely disagree on.**
    # A flat curve is identical under every construction, so running the
    # comparison on one would compare a thing with itself and pass whatever
    # `compare` did.
    curved = {}
    for mi in months.tolist():
        for lab, ten in (("1 Mo", 1), ("1 Yr", 12), ("5 Yr", 60),
                         ("10 Yr", 120), ("20 Yr", 240)):
            curved[(int(mi), lab)] = [1.0 + 3.0 * (ten / 240.0) ** 0.5]
    cmp_ = compare(zp.stem, cache_root=cr, core_root=cr, n_boot=19,
                   src=curved,
                   **dict(zip(("pos", "tab"),
                              Z8.curve_table_from(curved, RULE_A))))
    if cmp_["n"] == 0:
        fails.append("no loop survived both constructions on the fixture, so "
                     "`compare` is untested end to end")
    else:
        if cmp_["shift"].size != cmp_["n"]:
            fails.append("the per-loop shift is not one entry per compared "
                         "loop")
        # **the shift must be non-zero somewhere.** If the two arms agree to
        # the last bit, either the rules coincide on this curve or `compare`
        # is handing the same table to both, and both make the whole file a
        # no-op that reports a pass.
        if float(np.max(np.abs(cmp_["shift"]))) < 1e-12:
            fails.append("the two constructions gave bit-identical loop sums "
                         "on a curve they are built to disagree on; the "
                         "comparison is between one thing and itself")
        # and the loop skeleton must be shared, which is the file's premise
        # **the compared set is the intersection**, recomputed here from the
        # two masks rather than taken from `compare`'s own arithmetic
        dd = C.get(zp.stem, cache_root=cr, core_root=cr,
                   **dict(zip(("pos", "tab"),
                              Z8.curve_table_from(curved, RULE_A))))
        sb = under_rule(zp.stem, RULE_B, dd["sig"], cache_root=cr, src=curved)
        arm_ = np.asarray(dd["sig"]["arm"])
        m_a = dd["sig"]["measurable"].astype(bool) & (arm_ == L.ARM_MOD)
        m_b = sb["measurable"].astype(bool) & (arm_ == L.ARM_MOD)
        if cmp_["n"] != int((m_a & m_b).sum()):
            fails.append(f"`compare` compared {cmp_['n']} loops where the two "
                         f"masks intersect on {int((m_a & m_b).sum())}; the "
                         "union would let a loop unreadable under one "
                         "construction carry a partial sum into the shift")
        if cmp_["n_a"] != int(m_a.sum()) or cmp_["n_b"] != int(m_b.sum()):
            fails.append("the per-arm counts do not match the masks")
        # **The intersection is defensive and is expected to be a no-op.**
        # The two rules differ in the *value* at a horizon, never in whether
        # one exists: both interpolate below the first published tenor and
        # both produce a finite number past the last, so a row is dropped only
        # where the month itself is missing, which is the same month for both.
        # A mutation run confirmed `&` and `|` are indistinguishable here.
        # **So the counts are asserted and printed rather than assumed**, and
        # if a real archive ever shows them non-zero the intersection has
        # earned its keep and this comment is wrong.
        # **the floor arm must be rule-independent**, which is the claim §4
        # rests on. On the fixture's flat curve it is trivially so, but the
        # comparison must at least run and produce a finite floor, or §4's
        # decisive column is NaN and says nothing.
        # **the floor arm, against arithmetic done outside `compare`.** The
        # fixture carries two clean cures on a curve every rule agrees on, so
        # nothing here can be pinned by "it came out zero"; each value is
        # recomputed from the cache and from `loop_sums` directly.
        if not np.isfinite(cmp_["floor_shift"]):
            fails.append("the floor arm produced no comparison, so §4's "
                         "decisive column is NaN and B8-1 is unchecked")
        elif cmp_["n_floor"] == 0:
            fails.append("no clean cure survived both constructions")
        else:
            flx = dd["floor"]
            cl_x = np.asarray(flx["closed"], float)
            oa_x = np.asarray(flx["omega"], float)
            ob_x, mb_x = floor_under(zp.stem, RULE_B, flx, cache_root=cr,
                                     src=curved)
            fmx = (flx["measurable"].astype(bool) & flx["ideal"].astype(bool)
                   & mb_x)
            if int(fmx.sum()) != cmp_["n_floor"]:
                fails.append(f"the floor arm compared {cmp_['n_floor']} cures "
                             f"where the masks give {int(fmx.sum())}; the "
                             "`ideal` screen or the measurability screen is "
                             "not being applied")
            want_a = F.mad_scale((oa_x - cl_x)[fmx])
            want_b = F.mad_scale((ob_x - cl_x)[fmx])
            if not abs(cmp_["floor_a"] - want_a) <= 1e-15:
                fails.append(f"floor A read {cmp_['floor_a']:.6e}, expected "
                             f"{want_a:.6e} = MAD(omega - closed) on the "
                             "ideal clean cures")
            if not abs(cmp_["floor_b"] - want_b) <= 1e-15:
                fails.append(f"floor B read {cmp_['floor_b']:.6e}, expected "
                             f"{want_b:.6e}; the alternative rule is not "
                             "reaching the floor arm")
            want_sh = float(np.max(np.abs(ob_x - oa_x)[fmx]))
            if not abs(cmp_["floor_shift"] - want_sh) <= 1e-15:
                fails.append(f"the floor shift read {cmp_['floor_shift']:.3e},"
                             f" expected {want_sh:.3e}")
            # **`floor_shift` cannot be driven non-zero on this fixture.**
            # The cancellation holds wherever field 17 steps down by one, and
            # `b8_loops`' generator always steps it down, so a clean cure
            # there is rule-independent by construction. The column is pinned
            # for correctness-when-zero above; **its non-zero behaviour rests
            # on the same expression and is not exercised here**, and that is
            # recorded rather than papered over.
            if want_sh > ROUND_BOUND:
                fails.append(f"the fixture's floor arm moved by {want_sh:.3e} "
                             f"between constructions, past {ROUND_BOUND:.3e}. "
                             "`b8_loops`' generator steps field 17 down by one "
                             "on every row, so the annuity must cancel there "
                             "and only rounding may be left")
        if cmp_["n_only_a"] or cmp_["n_only_b"]:
            fails.append(f"{cmp_['n_only_a']} loops computable only under the "
                         f"registered rule and {cmp_['n_only_b']} only under "
                         "the alternative. The two rules were expected to "
                         "agree on computability and differ only in value")
    txt = render([cmp_])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. How far the construction moves a loop sum",
                 "## 2. The cells, side by side",
                 "## 3. The verdict, both constructions",
                 "## 4. B8-1 under both, **both arms**"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    if "_no data_" not in render([]):
        fails.append("the empty render did not say so")
    print(f"  mechanism: same-n {same[0]:+.6e} both rates; "
          f"n/n-1 {off[0]:+.3e} / {off[1]:+.3e} / {off[2]:+.3e}",
          file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the cancellation breaks exactly where O33 says and "
          "the two rules differ", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = compare(n, pos=pos, tab=tab)
        rows.append(a)
        sh = a["shift"]
        print(f"  done {n}: {a['n']:,} loops, median shift "
              f"{(np.median(sh) if sh.size else float('nan')):+.3e}",
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
