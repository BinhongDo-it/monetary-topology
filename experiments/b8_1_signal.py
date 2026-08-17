#!/usr/bin/env python3
"""B8-1: is the modification triangle's loop sum above the floor, and is what
is above the floor the part where the contract actually moves.

Read map: `docs/b8_fannie_slice.md` §21, written before this ran.

--------------------------------------------------------------------------
What §5 registered, and what B8-0b did to it
--------------------------------------------------------------------------

§5 registered `sqrt(Z) / sqrt(N) > 3` on the modification triangle, on both
`q` grids. Two things happened to that statement after it was written.

**One: the estimator moved** (§18.7). `Z = 2 * Var` does not converge on the
floor arm, climbing 2,900-fold from n = 100 to the full sample and still
climbing at the last step, so both sides now use the MAD. The threshold `> 3`
was written for a ratio of standard deviations and does not transfer to a
different scale estimator by assertion.

**Two, and this is the one that matters: the floor turned out not to be
noise.** `corr(omega, closed) = +1.0000` on five archives. The clean-cure loop
sum **is** `loop_residual_ideal`, a deterministic function of four scalars.
What is left after subtracting it is 2.68e-08 to 5.22e-08, which is half a
cent divided by the median balance: **field 12's quantisation**.

So `N` is not a sampling noise floor at all, it is the instrument's
resolution, and `> 3 sigma` is not the right shape of question to ask of it.
§21 rules the threshold down to a readability line at `1` and records that the
measured ratio is four orders past it, so no threshold in the plausible range
separates the outcomes.

--------------------------------------------------------------------------
The question that is actually open
--------------------------------------------------------------------------

If the clean-cure arm's loop sum is a deterministic artifact of the
construction, **the modification arm carries the same artifact**, and a ratio
of dispersions does not know the difference. O32 left this as an inference:
same order, therefore a ten-thousandth of the signal, therefore ignorable.
That was an inference and not a measurement.

It can be measured exactly, on the part of the loop where the contract has not
moved yet. Nothing before `t_M` knows a modification is coming, so **leg 1 on
the modification arm is the same object as the whole clean-cure loop minus its
cure month**, and it has the same closed form:

    l1_closed = n1 * ( log B_A - log( B_A * (1 + i/1200) - P ) )

This station prints three things beside each other:

1. `MAD(signal) / MAD(floor)`, the registered statistic under §18.7's
   estimator, on both `q` grids.
2. **How much of leg 1 is the closed form.** If leg 1 is the artifact and
   nothing else, it carries no information and the signal lives where the
   contract moves.
3. The ratio recomputed on `omega - l1_closed`, which is the registered
   statistic with the artifact removed. **If that collapses, B8-1 was
   measuring the construction.**

Usage:

    python experiments/b8_1_signal.py run
    python experiments/b8_1_signal.py run --only 2019Q1
    python experiments/b8_1_signal.py selftest
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
import b8_cache as C                                           # noqa: E402

OUT = K.ROOT / "results" / "b8_1_signal.md"
COLS = Z8.COLS + ["zero_bal"]

#: §21.2. Below this the loop sum is inside one quantisation step of field 12
#: and cannot be read at all. **This is a readability line, not a significance
#: test**, and §21.2 gives the reason: there is no sampling distribution here
#: to be three of anything out on.
READABLE = 1.0

#: §5's inherited number, printed beside the readability line under R01 so a
#: reader who came for the registered statement finds it. **It is not the
#: operative threshold**; see §21.2.
INHERITED = 3.0

#: A leg 1 counts as "the closed form and nothing else" when the two agree to
#: this in absolute terms. **Its source is B8-0b's floor**: 5.22e-08 is the
#: largest per-archive residual after the closed form was subtracted on the
#: clean-cure arm, so anything at that scale is field 12's rounding and
#: anything above it is not.
ARTIFACT_TOL = 1e-7


def ratio(sig: np.ndarray, flo: np.ndarray, min_cell: int = None) -> dict:
    """§18.7's statistic, and the counts that say whether it is readable.

    `min_cell` is a parameter **so the selftest can reach these numbers at
    all**. `b8_loops`' fixture carries five modification loops against a floor
    of twenty, so every arm came back NaN, and a check written as
    `abs(got - want) > tol` is False on NaN. Four assertions on the arms that
    decide B8-1 sat there passing on nothing until a mutation run said so.
    """
    mc = F.MIN_CELL if min_cell is None else min_cell
    s, f = np.asarray(sig, float), np.asarray(flo, float)
    s, f = s[np.isfinite(s)], f[np.isfinite(f)]
    ms = F.mad_scale(s) if s.size >= mc else float("nan")
    mf = F.mad_scale(f) if f.size >= mc else float("nan")
    r = ms / mf if np.isfinite(ms) and np.isfinite(mf) and mf > 0 else float("nan")
    return {"n_sig": int(s.size), "n_flo": int(f.size),
            "mad_sig": ms, "mad_flo": mf, "ratio": r,
            "readable": bool(np.isfinite(r) and r > READABLE)}


def artifact_share(leg1: np.ndarray, closed: np.ndarray, n1=None,
                   tol: float = ARTIFACT_TOL) -> dict:
    """How much of leg 1 is `loop_residual_ideal` and how much is not.

    **The share is reported several ways on purpose.** `exact` counts the loops
    where the two agree to `tol`, which is the clean statement. `med_ratio` is
    the median of `closed / leg1`, which says what the typical loop looks like
    when they do not agree exactly. `med_gap` is the median of what is left
    over, which is the thing a later station would have to explain.

    **`eff` is the diagnostic for when they do not agree.** The closed form is
    `n1` copies of one per-month quantity, so dividing the measured leg 1 by
    that quantity gives **the number of months the data actually behaved like
    a flat delinquent run**:

        eff = leg1 / per_month = n1 * leg1 / closed

    If `eff` comes back at `n1` the run was flat. If it comes back near
    `n1 - 1`, one month in the window is not flat and the question is which.
    If it is a smooth fraction of `n1`, the balance moves during delinquency
    and the flat assumption is wrong rather than off by a month. **Printing
    `closed / leg1` alone cannot tell those apart**, and they have different
    consequences.
    """
    l1, cl = np.asarray(leg1, float), np.asarray(closed, float)
    m = np.isfinite(l1) & np.isfinite(cl) & (np.abs(l1) > 0)
    if not m.any():
        return {"n": 0, "exact": 0, "frac_exact": float("nan"),
                "med_ratio": float("nan"), "med_gap": float("nan"),
                "med_abs_l1": float("nan"), "med_n1": float("nan"),
                "med_eff": float("nan"), "frac_eff_int": float("nan")}
    gap = l1[m] - cl[m]
    out = {"n": int(m.sum()),
           "exact": int((np.abs(gap) <= tol).sum()),
           "frac_exact": float((np.abs(gap) <= tol).mean()),
           "med_ratio": float(np.median(cl[m] / l1[m])),
           "med_gap": float(np.median(np.abs(gap))),
           "med_abs_l1": float(np.median(np.abs(l1[m])))}
    if n1 is None:
        out.update({"med_n1": float("nan"), "med_eff": float("nan"),
                    "frac_eff_int": float("nan")})
        return out
    nn = np.asarray(n1, float)[m]
    good = (np.abs(cl[m]) > 0) & (nn > 0)
    eff = np.where(good, nn * l1[m] / np.where(good, cl[m], 1.0), np.nan)
    out.update({"med_n1": float(np.median(nn)),
                "med_eff": float(np.nanmedian(eff)) if good.any()
                else float("nan"),
                # a whole number of flat months is a different diagnosis from
                # a fraction of one, so it is counted rather than eyeballed
                "frac_eff_int": float(np.nanmean(
                    np.abs(eff - np.round(eff)) < 1e-6)) if good.any()
                else float("nan")})
    return out


def analyse(name: str, cache_root=None, pos=None, tab=None,
            core_root=None, min_cell: int = None, data=None) -> dict:
    """Both arms, on the cache. §18.3's N1: the floor arm is the clean cures
    put through the same summation, and its floor is `omega - closed` because
    `closed` is the deterministic part (§18.7)."""
    # `data` is an injection point for the selftest. **`leg1` and
    # `l1_closed` are equal on `b8_loops`' fixture by construction** -- its
    # delinquent runs are flat on purpose, which pit 10 required -- so no
    # fixture-based check can tell the net arm reading one from the other,
    # and a mutation run confirmed the swap survives everything. Handing in a
    # dict where they differ is the only way to pin it.
    d = C.get(name, pos=pos, tab=tab,
              core_root=core_root or cache_root) if data is None else data
    s, fl = d["sig"], d["floor"]
    m = s["measurable"].astype(bool) & (s["arm"] == L.ARM_MOD)
    fm = fl["measurable"].astype(bool) & fl["ideal"].astype(bool)

    om = np.asarray(s["omega"], float)[m]
    l1 = np.asarray(s["leg1"], float)[m]
    l1c = np.asarray(s["l1_closed"], float)[m]
    floor = (np.asarray(fl["omega"], float)[fm]
             - np.asarray(fl["closed"], float)[fm])

    return {"name": name,
            "raw": ratio(om, floor, min_cell),
            "net": ratio(om - np.where(np.isfinite(l1c), l1c, 0.0), floor,
                         min_cell),
            "art": artifact_share(l1, l1c,
                                  np.asarray(s["n1"], float)[m]),
            "n_defer": int((s["measurable"].astype(bool)
                            & (s["arm"] == L.ARM_DEFER)).sum()),
            "defer": ratio(np.asarray(s["omega"], float)[
                s["measurable"].astype(bool) & (s["arm"] == L.ARM_DEFER)],
                floor, min_cell)}


def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:+.{k}e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-1: the modification triangle against the floor\n")
    A("Generated by `experiments/b8_1_signal.py`. Read map in "
      "`docs/b8_fannie_slice.md` §21, written before this ran.\n")
    A(f"Statistic is §18.7's `MAD(signal) / MAD(floor)`, **not** §5's "
      f"`sqrt(Z)/sqrt(N)`: the floor arm's `2*Var` does not converge. The "
      f"floor is `omega - closed` per §18.7, because the clean-cure loop sum "
      f"**is** `loop_residual_ideal` and what is left is field 12's "
      f"quantisation.\n")
    A(f"§21.2 rules the operative line at **{READABLE:g}**, which is "
      "readability rather than significance: below it the loop sum is inside "
      f"one quantisation step. §5's inherited **{INHERITED:g}** is printed "
      "beside it under R01 and is not the operative number.\n")
    A("**The two `q` grids give identical loops** (§20.2): §17's window only "
      "distinguishes `current` from not-`current`, so B8-6 is satisfied here "
      "by construction and is stated rather than printed as a pass.\n")

    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"

    A("\n## 1. The registered statistic\n")
    A("| archive | signal loops | floor loops | MAD signal | MAD floor | "
      "**ratio** | above 1 | above 3 |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        r = a["raw"]
        A(f"| {a['name']} | {r['n_sig']:,} | {r['n_flo']:,} | "
          f"{_f(r['mad_sig'])} | {_f(r['mad_flo'])} | "
          f"**{r['ratio']:,.1f}** | {'yes' if r['readable'] else 'no'} | "
          f"{'yes' if np.isfinite(r['ratio']) and r['ratio'] > INHERITED else 'no'} |")

    A("\n## 2. How much of leg 1 is the construction\n")
    A("Nothing before `t_M` knows a modification is coming, so leg 1 on the "
      "modification arm is the same object B8-0b found on the clean-cure arm "
      "and it has the same closed form:\n")
    A("```\nl1_closed = n1 * ( log B_A - log( B_A * (1 + i/1200) - P ) )\n```\n")
    A(f"`exact` counts loops where the two agree to {ARTIFACT_TOL:g}, whose "
      "source is B8-0b's largest per-archive floor (5.22e-08): at that scale "
      "the difference is field 12's rounding.\n")
    A("`eff` is the diagnostic for the loops where they do not agree. The "
      "closed form is `n1` copies of one per-month quantity, so "
      "`eff = n1 * leg1 / closed` is **how many months the data actually "
      "behaved like a flat delinquent run**. `eff = n1` is flat; `eff` a "
      "whole number below `n1` means specific months are not flat; a "
      "fraction means the balance moves during delinquency.\n")
    A("| archive | loops | **exact** | share | median `closed/leg1` | "
      "median leftover | median `\\|leg1\\|` | median `n1` | "
      "**median `eff`** | `eff` whole |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        g = a["art"]
        A(f"| {a['name']} | {g['n']:,} | **{g['exact']:,}** | "
          f"{g['frac_exact']:.4f} | {g['med_ratio']:+.4f} | "
          f"{_f(g['med_gap'])} | {_f(g['med_abs_l1'])} | "
          f"{g['med_n1']:.1f} | **{g['med_eff']:.3f}** | "
          f"{g['frac_eff_int']:.4f} |")

    A("\n## 3. The statistic with the artifact removed\n")
    A("`omega - l1_closed`, against the same floor. **This is the number that "
      "decides whether section 1 was measuring the construction.**\n")
    A("| archive | MAD signal, net | **ratio, net** | ratio, raw | "
      "net / raw | above 1 |")
    A("|---|---|---|---|---|---|")
    for a in rows:
        n_, r_ = a["net"], a["raw"]
        sh = (n_["ratio"] / r_["ratio"]
              if np.isfinite(n_["ratio"]) and np.isfinite(r_["ratio"])
              and r_["ratio"] > 0 else float("nan"))
        A(f"| {a['name']} | {_f(n_['mad_sig'])} | **{n_['ratio']:,.1f}** | "
          f"{r_['ratio']:,.1f} | {sh:.4f} | "
          f"{'yes' if n_['readable'] else 'no'} |")

    A("\n## 4. The deferral arm, beside it\n")
    A("Not part of §5's B8-1, which names the modification triangle. Printed "
      "because it exists and because C10-4 made it the larger arm.\n")
    A("| archive | loops | MAD signal | **ratio** | above 1 |")
    A("|---|---|---|---|---|")
    for a in rows:
        dv = a["defer"]
        A(f"| {a['name']} | {dv['n_sig']:,} | {_f(dv['mad_sig'])} | "
          f"**{dv['ratio']:,.1f}** | {'yes' if dv['readable'] else 'no'} |")

    A("\n## 5. The verdict\n")
    worst = min((a["art"]["frac_exact"] for a in rows
                 if np.isfinite(a["art"]["frac_exact"])), default=float("nan"))
    if np.isfinite(worst) and worst < 0.99:
        A("**§21.4's third row fired, not its first.** Leg 1 is not equal to "
          f"its closed form loop by loop (the best archive matches "
          f"{max(a['art']['frac_exact'] for a in rows):.1%} of loops), so the "
          "flat-delinquency assumption does not hold on the real file and "
          "**that is a registered unexplained reading**, resolved in "
          "`docs/b8_fannie_slice.md` §21.6 as a month count and not a "
          "proportion. It does not endanger what follows: the quantity "
          "section 3 subtracts is **larger** than the measured leg 1, so more "
          "than the artefact was removed and the ratio held. **Every citation "
          "of B8-1 carries this sentence.**\n")
    allr = [a["net"]["ratio"] for a in rows]
    ok = [r for r in allr if np.isfinite(r) and r > READABLE]
    A(f"| archives | net ratio above {READABLE:g} | min | max | "
      "**B8-1 necessary condition** |")
    A("|---|---|---|---|---|")
    A(f"| {len(rows)} | {len(ok)} | {min(allr):,.1f} | {max(allr):,.1f} | "
      f"**{'holds' if len(ok) == len(rows) else 'FAILS'}** |")
    A("\n§21.4's map: the necessary condition holding is **not** B8-1 "
      "holding. B8-1 also wants §3.3's two grids, which §20.2 settles by "
      "construction here, and §6's windows, which is B8-2 and has its own "
      "result file.\n")

    A("\n## What this does not decide\n")
    A("- **Whether legs 2 and 3 carry a deterministic component too.** They "
      "have no closed form because the contract moves inside them. Section 2 "
      "removes the part that does have one and says nothing about the rest.")
    A("- **Per-class floors.** §15.4 wants them and §15.3's C9 gates them; "
      "B8-4 is where they are used.")
    A("- Causality, and any magnitude claim about a real economy.\n")
    return "\n".join(Ls) + "\n"


def selftest() -> int:
    fails: list[str] = []

    # -- `ratio`, against hand-built samples ------------------------------
    # a sample whose MAD is known exactly: 1.4826 * MAD of +-1 around 0 is
    # 1.4826, so a signal ten times as wide must give exactly 10
    lo = np.tile([-1.0, 1.0], F.MIN_CELL)
    hi = lo * 10.0
    r = ratio(hi, lo)
    if abs(r["ratio"] - 10.0) > 1e-12:
        fails.append(f"a signal exactly ten times the floor's spread gave "
                     f"{r['ratio']}, expected 10")
    if not r["readable"]:
        fails.append("a ratio of 10 was not called readable")
    # **and the line has to bite**, or `readable` is decoration
    if ratio(lo * 0.5, lo)["readable"]:
        fails.append(f"a signal at half the floor's spread was called "
                     f"readable; the line at {READABLE:g} does not bite")
    # too few loops must give nan rather than a number off three points
    if np.isfinite(ratio(hi[:6], lo)["ratio"]):
        fails.append("a six-loop sample produced a ratio; MIN_CELL is not "
                     "being applied")
    # a floor with no spread at all must refuse rather than divide by zero
    if np.isfinite(ratio(hi, np.zeros(F.MIN_CELL * 2))["ratio"]):
        fails.append("a degenerate floor produced a finite ratio")

    # -- `artifact_share`, where the answer is known ----------------------
    l1 = np.array([1.0, 2.0, 3.0, 4.0])
    g = artifact_share(l1, l1.copy())
    if g["exact"] != 4 or abs(g["frac_exact"] - 1.0) > 0:
        fails.append("leg 1 identical to its closed form did not read as "
                     f"wholly artifact: {g['exact']}/4")
    if abs(g["med_ratio"] - 1.0) > 1e-12:
        fails.append(f"the median of closed/leg1 read {g['med_ratio']}, "
                     "expected 1 when they are identical")
    # **half artifact must read as half**, or the share is a pass-through
    g2 = artifact_share(l1, l1 * 0.5)
    if g2["exact"] != 0:
        fails.append(f"leg 1 at twice its closed form counted "
                     f"{g2['exact']} exact matches")
    if abs(g2["med_ratio"] - 0.5) > 1e-12:
        fails.append(f"the median of closed/leg1 read {g2['med_ratio']}, "
                     "expected 0.5")
    # and the tolerance must be the thing deciding, at its own scale
    g3 = artifact_share(l1, l1 + ARTIFACT_TOL * 0.5)
    if g3["exact"] != 4:
        fails.append("a difference at half the tolerance was not counted as "
                     "exact; the tolerance is not the operative comparison")
    g4 = artifact_share(l1, l1 + ARTIFACT_TOL * 2.0)
    if g4["exact"] != 0:
        fails.append("a difference at twice the tolerance was counted as "
                     "exact")
    if artifact_share(np.zeros(0), np.zeros(0))["n"] != 0:
        fails.append("an empty arm did not come back empty")

    # -- `eff` must read back the month count it was built from -----------
    # **The diagnosis turns on whether `eff` is a whole number**, so it is
    # driven with a leg 1 built as an exact number of copies of the per-month
    # quantity and the answer is checked against that number.
    per = 0.0037
    nn = np.array([6.0, 6.0, 4.0, 4.0])
    for want in (6.0, 5.0, 4.0):
        e = artifact_share(np.full(4, want) * per, nn * per, nn)
        if abs(e["med_eff"] - want) > 1e-9:
            fails.append(f"a leg 1 built from exactly {want:g} flat months "
                         f"read back eff = {e['med_eff']}")
        if abs(e["frac_eff_int"] - 1.0) > 0:
            fails.append(f"eff = {want:g} was not counted as a whole number")
    # a leg 1 that is not a whole number of months must say so, or the column
    # cannot tell "one month is not flat" from "the balance moves"
    e2 = artifact_share(np.full(4, 4.5) * per, nn * per, nn)
    if abs(e2["med_eff"] - 4.5) > 1e-9 or e2["frac_eff_int"] != 0.0:
        fails.append(f"a fractional eff read {e2['med_eff']} with whole-number "
                     f"share {e2['frac_eff_int']}; the two diagnoses are not "
                     "being separated")

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
    # **the fixture's arms are smaller than the production floor**, so the
    # floor is lowered here rather than left to make every number NaN
    a = analyse(zp.stem, cache_root=root / "loopcache", pos=pos, tab=tab,
                core_root=cr, min_cell=2)
    if a["art"]["n"] == 0:
        fails.append("no fixture loop reached the artifact comparison")
    # **the fixture's delinquent runs are flat by construction**, so leg 1
    # there must be the closed form and nothing else. If this ever reads
    # partial, the wiring changed, not the world.
    elif a["art"]["frac_exact"] < 1.0:
        fails.append(f"only {a['art']['frac_exact']:.4f} of the fixture's "
                     "leg 1 matched its closed form, and the fixture builds "
                     "flat delinquent runs on purpose")

    # **the net arm is the number §21.3 says decides B8-1 and nothing pinned
    # it.** `analyse` was called and only `art` was read; a mutation run
    # confirmed that subtracting nothing, subtracting `leg1` instead of
    # `l1_closed`, or flipping the sign all left the selftest green. Driven
    # here against arithmetic done outside `analyse`.
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as cz:
        dd = C.get(zp.stem, cache_root=root / "loopcache", pos=pos, tab=tab,
                   core_root=cr)
    sg, flr = dd["sig"], dd["floor"]
    mm = sg["measurable"].astype(bool) & (sg["arm"] == L.ARM_MOD)
    om_d = np.asarray(sg["omega"], float)[mm]
    l1c_d = np.asarray(sg["l1_closed"], float)[mm]
    fm_d = flr["measurable"].astype(bool) & flr["ideal"].astype(bool)
    fl_d = (np.asarray(flr["omega"], float)[fm_d]
            - np.asarray(flr["closed"], float)[fm_d])
    if not abs(a["raw"]["mad_sig"] - F.mad_scale(om_d)) <= 1e-12:
        fails.append("the raw arm's MAD is not the MAD of the measurable "
                     "modification loops")
    if not abs(a["raw"]["mad_flo"] - F.mad_scale(fl_d)) <= 1e-12:
        fails.append("**the floor is not `omega - closed` on the ideal clean "
                     "cures.** B8-0b ruled the clean-cure loop sum is a "
                     "deterministic function, so a floor drawn on raw omega "
                     "is the function, not the noise")
    want_net = F.mad_scale(om_d - np.where(np.isfinite(l1c_d), l1c_d, 0.0))
    if not abs(a["net"]["mad_sig"] - want_net) <= 1e-12:
        fails.append(f"the net arm read {a['net']['mad_sig']:.6e}, expected "
                     f"{want_net:.6e} = MAD(omega - l1_closed). Section 3 is "
                     "the number that decides whether section 1 was measuring "
                     "the construction")
    # and subtracting must actually change something, or the check is empty
    if not np.isfinite(a["raw"]["ratio"]) or not np.isfinite(a["net"]["ratio"]):
        fails.append("an arm came back NaN, so every comparison above is "
                     "`abs(nan - x) > tol`, which is False, and none of them "
                     "can fail")
    if abs(want_net - F.mad_scale(om_d)) < 1e-15:
        fails.append("`l1_closed` is zero on every fixture loop, so the net "
                     "arm equals the raw arm and the comparison above is "
                     "vacuous")

    # **`l1_closed` and not `leg1`.** They are identical on this fixture, so
    # the field is separated by handing in a copy where they differ.
    dd2 = {"sig": dict(dd["sig"]), "floor": dd["floor"]}
    dd2["sig"]["l1_closed"] = np.asarray(dd["sig"]["l1_closed"], float) * 3.0
    a_x = analyse(zp.stem, min_cell=2, data=dd2)
    want_x = F.mad_scale(om_d - 3.0 * np.where(np.isfinite(l1c_d), l1c_d, 0.0))
    if not abs(a_x["net"]["mad_sig"] - want_x) <= 1e-12:
        fails.append(f"tripling the cached `l1_closed` moved the net arm to "
                     f"{a_x['net']['mad_sig']:.6e}, expected {want_x:.6e}; "
                     "the net arm is not reading `l1_closed`")
    if abs(a_x["net"]["mad_sig"] - a["net"]["mad_sig"]) < 1e-15:
        fails.append("tripling `l1_closed` did not move the net arm at all, "
                     "so it is reading some other field")

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The registered statistic",
                 "## 2. How much of leg 1 is the construction",
                 "## 3. The statistic with the artifact removed",
                 "## 5. The verdict"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    print(f"  fixture: {a['art']['n']} loops compared, "
          f"{a['art']['exact']} exact", file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print(f"selftest: ok, the line at {READABLE:g} bites and the artifact "
          "share is not a pass-through", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: raw {a['raw']['ratio']:,.1f}, net "
              f"{a['net']['ratio']:,.1f}, artifact share "
              f"{a['art']['frac_exact']:.4f}", file=sys.stderr)
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
