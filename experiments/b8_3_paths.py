#!/usr/bin/env python3
"""B8-3: two realisable paths to the same terminal state, different `omega`.

Read map in ``docs/b8_fannie_slice.md`` §19, written before this ran. Per
§18.5's amended standing that map is **a record of what was expected, not a
commitment**; where the run contradicts it the map changes and the change is
recorded with what the old one got wrong.

    primary pair:  delinquent -> modified -> current
                   delinquent -> deferred -> current

Three readings, and only the first is B8-3's own bar (§19.5):

  1. **existence** -- `median(omega | mod) - median(omega | defer)`, against
     B8-0b's floor. §15.7 makes B8-3 Corollary-1 shaped: an existence claim
     about the state space, **not a causal claim about which route a servicer
     chose**, so it does not have to win composition.
  2. **stratified** -- the same difference inside `(window, missed months,
     months to cure)` cells, size-weighted, **plus how many cells agree in
     sign**. Sign agreement is the load-bearing part: composition flips signs
     across cells, a path effect does not.
  3. **permutation null** -- arm labels shuffled **inside each cell**, so what
     is tested is whether the label still carries information given the path
     and the window.

Medians and MAD throughout, not means and variances: §6.6.26 measured that
`omega`'s variance does not converge on the floor arm and §18.7 moved the
stage's scale estimator for that reason.
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
import b8_triangles as T                                       # noqa: E402

OUT = K.ROOT / "results" / "b8_3_paths.md"

#: **The column list `analyse` opens the core table with.** Pit 30.
#:
#: `zero_bal` was here, copied from `b8_0b_floor`, which needs it for the
#: payoff diagnostic. **Nothing in this file reads it.** `scripts/b8_col_sweep.py`
#: found it by deleting each entry and re-running the selftest; a dead entry
#: costs a column of memory-mapped reads on every archive and, worse, reads
#: like a claim that the file uses field 44.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
        "mod_flag", "nib_upb", "defer_amt"]

#: §19.4's floor on a cell, from §6.4.
MIN_CELL = 20

#: Permutation draws for the within-cell null.
N_PERM = 999
PERM_SEED = 20260817

#: §3.3's coarse grid, months. **Path quantities only** (§19.4): the note rate,
#: the term, the payment, the balloon and the balance are all barred. The first
#: four are `omega`'s own arguments. The balance is barred too even though
#: `omega` is homogeneous of degree zero in it, so stratifying on it could not
#: drive the result mechanically; the line is drawn one step tighter than
#: necessary because §6.6.16's circularity was only found after the run.
EDGES_MISSED = (1, 2, 3, 6, 12)
EDGES_CURE = (0, 1, 2, 3, 6, 12)


def med(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.median(x)) if x.size else float("nan")


def cell_name(cid: int) -> str:
    """Decode a cell id back into `window / missed / cure`.

    **A tally of four positive and two negative is not readable as two
    numbers.** The cells have to be printed, and printed as what they are
    rather than as an integer nobody can invert.
    """
    w, rest = divmod(int(cid), 64)
    i, j = divmod(rest, 8)
    wn = T.WINDOWS[w][0] if 0 <= w < len(T.WINDOWS) else f"w{w}"
    return (f"{wn} / missed {_band(EDGES_MISSED, i)} / "
            f"cure {_band(EDGES_CURE, j)}")


def _band(edges, k: int) -> str:
    """The half-open interval `np.searchsorted(edges, v, "right") == k` means.

    `searchsorted(..., "right")` returns **how many edges are at or below the
    value**, so bin `k` is `[edges[k-1], edges[k])`, closed below and open
    above. The first version of this decoder wrote `edges[k-1] + 1` to
    `edges[k]`, which is off by one at both ends: it labelled the bin holding
    exactly 1 missed month as "2-2". **Nothing computed with it, so no number
    was wrong; every cell name in a published table would have been.**
    """
    if k <= 0:
        return f"<{edges[0]}"
    if k >= len(edges):
        return f">={edges[-1]}"
    lo, hi = edges[k - 1], edges[k] - 1
    return f"{lo}" if lo == hi else f"{lo}-{hi}"


def cell_of(window, missed, cure) -> np.ndarray:
    """§19.4's cell id. **Window, missed months, months to cure. Nothing else.**

    The arm is deliberately absent: it is the thing being compared, so it
    cannot also be a stratifier.
    """
    w = np.asarray(window, dtype=np.int64)
    i = np.searchsorted(np.asarray(EDGES_MISSED), np.asarray(missed),
                        side="right")
    j = np.searchsorted(np.asarray(EDGES_CURE), np.asarray(cure),
                        side="right")
    return (w * 64 + i * 8 + j).astype(np.int64)


def stratified_delta(om, arm, cell, min_cell=MIN_CELL) -> dict:
    """Size-weighted within-cell median difference, and the sign tally.

    A cell counts only when **both** arms reach ``min_cell`` in it, because a
    difference needs two sides. Cells that fail are counted, not dropped
    quietly.
    """
    om = np.asarray(om, dtype=np.float64)
    arm = np.asarray(arm)
    cell = np.asarray(cell)
    out = {"cells": 0, "cells_used": 0, "loops_used": 0,
           "cells_one_sided": 0, "cells_too_small": 0,
           "delta": float("nan"), "pos": 0, "neg": 0, "per_cell": []}
    if om.size == 0:
        return out
    for cid in np.unique(cell):
        out["cells"] += 1
        m = cell == cid
        a = om[m & (arm == L.ARM_MOD)]
        b = om[m & (arm == L.ARM_DEFER)]
        if a.size < min_cell and b.size < min_cell:
            out["cells_too_small"] += 1
            continue
        if a.size < min_cell or b.size < min_cell:
            out["cells_one_sided"] += 1
            continue
        d = med(a) - med(b)
        n = int(a.size + b.size)
        out["per_cell"].append({"cell": int(cid), "n_mod": int(a.size),
                                "n_defer": int(b.size), "delta": d,
                                "med_mod": med(a), "med_defer": med(b)})
        out["cells_used"] += 1
        out["loops_used"] += n
        out["pos"] += int(d > 0)
        out["neg"] += int(d < 0)
    if out["per_cell"]:
        num = sum(c["delta"] * (c["n_mod"] + c["n_defer"])
                  for c in out["per_cell"])
        out["delta"] = num / out["loops_used"]
    return out


def permutation_null(om, arm, cell, n=N_PERM, seed=PERM_SEED,
                     min_cell=MIN_CELL) -> dict:
    """Shuffle the arm label **within cell** and recompute the weighted delta.

    Within cell, so the null holds the path and the window fixed and asks only
    whether the label still carries information. A global shuffle would also
    destroy the composition and would therefore be easy to reject for a reason
    that is not the one being tested.
    """
    om = np.asarray(om, dtype=np.float64)
    arm = np.asarray(arm)
    cell = np.asarray(cell)
    obs = stratified_delta(om, arm, cell, min_cell)["delta"]
    if not np.isfinite(obs) or om.size == 0:
        return {"obs": obs, "n": 0, "ge": 0, "p": float("nan"),
                "null_q": [float("nan")] * 3}
    rng = np.random.default_rng(seed)
    order = np.argsort(cell, kind="stable")
    cs = cell[order]
    starts = np.flatnonzero(np.concatenate(([True], cs[1:] != cs[:-1])))
    counts = np.diff(np.append(starts, cs.size))
    a_sorted = arm[order].copy()
    draws = np.empty(n)
    for t in range(n):
        shuf = a_sorted.copy()
        for s, cnt in zip(starts.tolist(), counts.tolist()):
            shuf[s:s + cnt] = rng.permutation(shuf[s:s + cnt])
        draws[t] = stratified_delta(om[order], shuf, cs, min_cell)["delta"]
    fin = draws[np.isfinite(draws)]
    ge = int((np.abs(fin) >= abs(obs)).sum())
    return {"obs": float(obs), "n": int(fin.size), "ge": ge,
            "p": (ge + 1) / (fin.size + 1) if fin.size else float("nan"),
            "null_q": (np.percentile(fin, [10, 50, 90]).tolist() if fin.size
                       else [float("nan")] * 3)}


def analyse(name: str, cache_root=None, pos=None, tab=None,
            n_perm: int = N_PERM) -> dict:
    if pos is None or tab is None:
        pos, tab = Z8.curve_table()
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        disc, _ = W.disc_of_row(c, pos, tab)
        r, ok, rinfo = W.row_residuals(c, disc)
        lp = L.find_loops(c)
        sig = Z8.loop_sums(lp, r, ok)

        # the floor, from B8-0b, on the same archive and the same code path
        cc = F.clean_cure_loops(c)
        flo = Z8.loop_sums(cc, r, ok)
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _k0, _p0 = W.contract_payments(c, pid0, q0)
        es = F.G.episode_sums(c, pay0, cc["t_A"], cc["t_B"], cc["k"])
        fm = flo["measurable"] & es[2]
        floor = F.mad_scale((flo["omega"] - es[1])[fm])

        meas = sig["measurable"]
        arm = lp["arm"]
        # §19.6: measurability itself differs by arm and stratifying cannot fix
        # it, so it is printed rather than absorbed.
        win = T.window_of(c, lp["t_M"]) if hasattr(T, "window_of") \
            else _window_of(c, lp["t_M"])
        cell = cell_of(win, sig["n1"] + 1, sig["n3"])

        a = {"name": name, "floor": floor,
             "floor_n": int(fm.sum()),
             "arms": {}, "windows": []}
        for tag, code in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
            s = arm == code
            m = s & meas
            v = sig["omega"][m]
            a["arms"][tag] = {
                "loops": int(s.sum()), "measurable": int(m.sum()),
                "rate": (float(m.sum() / s.sum()) if s.sum() else float("nan")),
                "median": med(v), "mad": F.mad_scale(v),
                "q": (np.percentile(v, [10, 25, 50, 75, 90]).tolist()
                      if v.size else [float("nan")] * 5)}

        # 1. existence
        dm = a["arms"]["mod"]["median"] - a["arms"]["defer"]["median"]
        a["existence"] = {
            "delta": dm,
            "over_floor": (abs(dm) / floor if floor > 0 else float("nan"))}

        # 2. stratified, and 3. the null
        st = stratified_delta(sig["omega"][meas], arm[meas], cell[meas])
        a["strat"] = st
        a["perm"] = permutation_null(sig["omega"][meas], arm[meas], cell[meas],
                                     n=n_perm)

        # per window, because deferral is overwhelmingly COVID (§19.6)
        for wi, (wname, _lo, _hi) in enumerate(T.WINDOWS):
            wm = meas & (win == wi)
            row = {"window": wname}
            for tag, code in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
                v = sig["omega"][wm & (arm == code)]
                row[tag] = {"n": int(v.size), "median": med(v)}
            row["delta"] = row["mod"]["median"] - row["defer"]["median"]
            row["readable"] = bool(row["mod"]["n"] >= MIN_CELL
                                   and row["defer"]["n"] >= MIN_CELL)
            a["windows"].append(row)
    finally:
        c.close()
    return a


def _window_of(c: K.Core, rows: np.ndarray) -> np.ndarray:
    """Fallback if `b8_triangles` does not expose one."""
    per = c.row["period"][:].astype(np.int64)[rows]
    out = np.full(rows.size, -1, dtype=np.int64)
    for k, (_n, lo, hi) in enumerate(T.WINDOWS):
        m = (per >= T._to_month_index(lo)) & (per <= T._to_month_index(hi))
        out[m] = k
    return out


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:.{k}e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-3: two paths to the same terminal state\n")
    A("Generated by `experiments/b8_3_paths.py`. Read map in "
      "`docs/b8_fannie_slice.md` §19, written before this ran; per §18.5 that "
      "map is a record of what was expected and it changes when the run "
      "contradicts it.\n")
    A("```\ndelinquent -> modified -> current    against\n"
      "delinquent -> deferred -> current\n```\n")
    A("**B8-3 is Corollary-1 shaped** (§15.7): an existence claim about the "
      "state space, not a causal claim about which route a servicer chose. "
      "Section 1 is its bar. Sections 2 and 3 are stronger and are not "
      "required for it to hold.\n")
    A("Medians and MAD throughout: §6.6.26 measured that `omega`'s variance "
      "does not converge on the floor arm.\n")

    A("\n## 1. Existence\n")
    A("The floor is B8-0b's, computed on the same archive through the same "
      "code path: `MAD(omega - closed)` on the ideal-path clean cures "
      "(§6.6.27), which is the cent field 12 is written to.\n")
    A("| archive | arm | loops | measurable | rate | median `omega` | `MAD` | "
      "p10 | p90 | floor | **`delta`** | **`delta` / floor** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("mod", "defer"):
            d = a["arms"][tag]
            ex = a["existence"]
            A(f"| {a['name']} | {tag} | {d['loops']:,} | "
              f"{d['measurable']:,} | {d['rate']:.4f} | {_f(d['median'])} | "
              f"{_f(d['mad'])} | {_f(d['q'][0])} | {_f(d['q'][4])} | "
              + (f"{_f(a['floor'])} | **{_f(ex['delta'])}** | "
                 f"**{ex['over_floor']:,.3e}** |" if tag == "mod"
                 else " | | |"))

    A("\n**Measurability differs by arm and stratifying cannot repair it** "
      "(§19.6): a loop with no `omega` is in no cell. The rates are printed "
      "above rather than absorbed.\n")

    A("\n## 2. Stratified, and the sign tally\n")
    A("Cells are `(window, missed months, months to cure)` on §3.3's coarse "
      "grid. **The arm is not a cell key**, being the thing compared, and no "
      "contract quantity is one either (§19.4). A cell counts only when both "
      "arms reach "
      f"{MIN_CELL} in it; the rest are counted, not dropped quietly.\n")
    A("**The sign tally is the load-bearing column.** Composition flips sign "
      "across cells; a path effect does not.\n")
    A("| archive | cells | used | one-sided | too small | loops used | "
      "**weighted `delta`** | / floor | **cells `delta` > 0** | < 0 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        s = a["strat"]
        of = (abs(s["delta"]) / a["floor"]
              if a["floor"] > 0 and np.isfinite(s["delta"]) else float("nan"))
        A(f"| {a['name']} | {s['cells']:,} | {s['cells_used']:,} | "
          f"{s['cells_one_sided']:,} | {s['cells_too_small']:,} | "
          f"{s['loops_used']:,} | **{_f(s['delta'])}** | {of:,.3e} | "
          f"**{s['pos']}** | {s['neg']} |")

    A("\n**Every used cell, printed.** A tally of four against two is not "
      "readable as two numbers, and with this few cells the reader has to see "
      "which ones and how big they are.\n")
    A("| archive | cell | n mod | n defer | median mod | median defer | "
      "**`delta`** | / floor |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for cl in sorted(a["strat"]["per_cell"],
                         key=lambda d: -(d["n_mod"] + d["n_defer"])):
            of = (abs(cl["delta"]) / a["floor"] if a["floor"] > 0
                  else float("nan"))
            A(f"| {a['name']} | {cell_name(cl['cell'])} | {cl['n_mod']:,} | "
              f"{cl['n_defer']:,} | {_f(cl['med_mod'])} | "
              f"{_f(cl['med_defer'])} | **{_f(cl['delta'])}** | "
              f"{of:,.3e} |")

    A("\n## 3. The within-cell permutation null\n")
    A(f"Arm labels shuffled inside each cell, {N_PERM} draws. **Within cell**, "
      "so the path and the window are held fixed and what is tested is "
      "whether the label still carries information. `p` is two-sided, "
      "`(ge + 1) / (draws + 1)`.\n")
    A("| archive | observed | draws | at least as extreme | **p** | "
      "null p10 | median | p90 |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        p = a["perm"]
        A(f"| {a['name']} | {_f(p['obs'])} | {p['n']:,} | {p['ge']:,} | "
          f"**{p['p']:.4f}** | " + " | ".join(_f(v) for v in p["null_q"])
          + " |")

    A("\n## 4. By window\n")
    A("**Deferral is overwhelmingly COVID** (§14.4: 31,057 of 32,533 inside "
      "it), so the pre-COVID cells are expected to be thin. That is a "
      "countable fact and is printed as one; a window that cannot be read is "
      f"marked, not silently merged. `MIN_CELL` is {MIN_CELL}.\n")
    A("| archive | window | mod n | mod median | defer n | defer median | "
      "`delta` | **readable** |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for w in a["windows"]:
            A(f"| {a['name']} | {w['window']} | {w['mod']['n']:,} | "
              f"{_f(w['mod']['median'])} | {w['defer']['n']:,} | "
              f"{_f(w['defer']['median'])} | "
              + (f"{_f(w['delta'])}" if w["readable"] else "not readable")
              + f" | {'yes' if w['readable'] else 'no'} |")

    A("\n## What this does not decide\n")
    A("- **It makes no causal claim.** B8-3 is an existence claim about the "
      "state space (§15.7, §19.1). Section 2 is stronger than B8-3 needs and "
      "section 3 tests only whether the arm label carries information given "
      "the path and the window.")
    A("- **Section 2 cannot repair the measurability difference** between the "
      "arms; a loop with no `omega` is in no cell.")
    A("- §5's secondary timing pairs are **registered and not run** (§19.2).")
    A("- B8-1 and B8-2 have their own criteria and are not read here.\n")
    return "\n".join(Ls) + "\n"


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails: list[str] = []

    # -- stratified_delta, against hand arithmetic ------------------------
    # **Cells of different size on purpose.** With equal cells the weighted
    # mean and the plain mean of the cell deltas coincide, and then nothing
    # can tell them apart; the first version of this fixture had that bug and
    # a mutation dropping the weighting passed.
    n = MIN_CELL
    om = np.concatenate([np.full(n, 1.0), np.full(n, 0.0),            # cell 0
                         np.full(3 * n, 5.0), np.full(3 * n, 3.0)])   # cell 1
    arm = np.concatenate([np.full(n, L.ARM_MOD), np.full(n, L.ARM_DEFER),
                          np.full(3 * n, L.ARM_MOD),
                          np.full(3 * n, L.ARM_DEFER)])
    cell = np.concatenate([np.zeros(2 * n, int), np.ones(6 * n, int)])
    # cell 0: delta 1.0 over 2n loops; cell 1: delta 2.0 over 6n.
    # weighted (1*2 + 2*6)/8 = 1.75; the plain mean of the deltas is 1.5.
    s = stratified_delta(om, arm, cell)
    if s["cells_used"] != 2 or abs(s["delta"] - 1.75) > 1e-12:
        fails.append(f"stratified_delta used {s['cells_used']} cells and read "
                     f"{s['delta']}, hand computation 2 cells and 1.75")
    if s["pos"] != 2 or s["neg"] != 0:
        fails.append(f"sign tally {s['pos']}/{s['neg']}, expected 2/0")
    # a cell where the sign flips must show in the tally, or the column is
    # decorative -- **this is the load-bearing read of section 2**
    om2 = om.copy()
    om2[2 * n:5 * n] = 1.0                       # cell 1's mod below its defer
    s2 = stratified_delta(om2, arm, cell)
    if s2["pos"] != 1 or s2["neg"] != 1:
        fails.append(f"a flipped cell gave tally {s2['pos']}/{s2['neg']}, "
                     "expected 1/1")
    # one-sided and too-small cells are counted, not dropped silently
    cell3 = cell.copy()
    cell3[:n] = 7                                # cell 7 is mod only
    s3 = stratified_delta(om, arm, cell3)
    if s3["cells_one_sided"] + s3["cells_too_small"] != 2:
        fails.append(f"one-sided {s3['cells_one_sided']} too-small "
                     f"{s3['cells_too_small']}, expected two cells accounted")

    # -- the null must be able to fail to reject -------------------------
    rng = np.random.default_rng(7)
    om_null = rng.normal(size=8 * n)
    arm_null = np.where(np.arange(8 * n) % 2 == 0, L.ARM_MOD, L.ARM_DEFER)
    cell_null = np.repeat(np.arange(4), 2 * n)
    pn = permutation_null(om_null, arm_null, cell_null, n=199, seed=3)
    if not (pn["p"] > 0.05):
        fails.append(f"the null rejected on data with no arm effect, p="
                     f"{pn['p']}; it is not a null")
    # and it must reject a planted one, or it cannot see anything
    om_hit = om_null + np.where(arm_null == L.ARM_MOD, 3.0, 0.0)
    ph = permutation_null(om_hit, arm_null, cell_null, n=199, seed=3)
    if not (ph["p"] <= 0.01):
        fails.append(f"the null failed to reject a planted 3.0 arm effect, "
                     f"p={ph['p']}")

    # -- cell keys: the arm cannot be one, and no contract quantity ------
    import inspect
    params = list(inspect.signature(cell_of).parameters)
    if params != ["window", "missed", "cure"]:
        fails.append(f"cell_of takes {params}; §19.4 allows exactly "
                     "['window', 'missed', 'cure'] and the arm is barred "
                     "because it is the thing being compared")
    # four paths that must separate: they differ in window, in missed months
    # and in cure months respectively
    ids = cell_of([0, 0, 1, 0], [1, 20, 1, 1], [0, 20, 0, 9])
    if len(set(ids.tolist())) != 4:
        fails.append(f"cell_of collapsed four distinct paths to "
                     f"{set(ids.tolist())}")
    # and two that must NOT separate, or the binning is an identity map and
    # every cell holds one loop
    same = cell_of([0, 0], [7, 11], [4, 5])
    if same[0] != same[1]:
        fails.append(f"cell_of split 7 and 11 missed months, which share the "
                     f"[6, 12) bin, into {same.tolist()}; it is not binning")

    # **`cell_name` must invert `cell_of`.** It computes nothing, so a wrong
    # decoder costs no number and every cell label in the published table. The
    # first one was off by one at both ends of every band.
    for w, m_, cu in ((3, 1, 0), (3, 7, 4), (4, 20, 20), (0, 2, 1), (1, 3, 3)):
        cid = int(cell_of([w], [m_], [cu])[0])
        nm = cell_name(cid)
        if T.WINDOWS[w][0] not in nm:
            fails.append(f"cell_name({cid}) = {nm!r}, window should be "
                         f"{T.WINDOWS[w][0]}")
        for label, val, edges in (("missed", m_, EDGES_MISSED),
                                  ("cure", cu, EDGES_CURE)):
            k = int(np.searchsorted(np.asarray(edges), val, side="right"))
            want = _band(edges, k)
            if f"{label} {want}" not in nm:
                fails.append(f"cell_name({cid}) = {nm!r}: {label}={val} is in "
                             f"bin {k}, which is {want!r}")
    # and the bands must actually contain what they say
    for edges in (EDGES_MISSED, EDGES_CURE):
        for v in range(0, int(edges[-1]) + 4):
            k = int(np.searchsorted(np.asarray(edges), v, side="right"))
            b = _band(edges, k)
            if b.startswith("<"):
                okb = v < edges[0]
            elif b.startswith(">="):
                okb = v >= edges[-1]
            elif "-" in b:
                lo, hi = (int(x) for x in b.split("-"))
                okb = lo <= v <= hi
            else:
                okb = v == int(b)
            if not okb:
                fails.append(f"_band({edges}, {k}) = {b!r} does not contain "
                             f"{v}, which lands in that bin")

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
    a = analyse(zp.stem, cache_root=cr, pos=pos, tab=tab, n_perm=19)
    for tag in ("mod", "defer"):
        if a["arms"][tag]["measurable"] == 0:
            fails.append(f"no measurable loop on the {tag} arm, so the "
                         "existence reading is nan")
    if not np.isfinite(a["floor"]) or a["floor"] <= 0:
        fails.append(f"the floor came back {a['floor']}; section 1's ratio "
                     "cannot be read")
    print(f"  fixture: mod {a['arms']['mod']['measurable']} / defer "
          f"{a['arms']['defer']['measurable']} measurable, floor "
          f"{a['floor']:.3e}, delta {a['existence']['delta']:+.4e}",
          file=sys.stderr)

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. Existence", "## 2. Stratified, and the sign tally",
                 "**Every used cell, printed.**",
                 "## 3. The within-cell permutation null", "## 4. By window"):
        if need not in txt:
            fails.append(f"render omits `{need}`")

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the sign tally sees a flip and the null both fails "
          "to reject and rejects", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: delta {a['existence']['delta']:+.4e} = "
              f"{a['existence']['over_floor']:,.3e} floors; stratified "
              f"{a['strat']['delta']:+.4e} over {a['strat']['cells_used']} "
              f"cells, signs {a['strat']['pos']}+/{a['strat']['neg']}-, "
              f"p={a['perm']['p']:.4f}", file=sys.stderr)
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
