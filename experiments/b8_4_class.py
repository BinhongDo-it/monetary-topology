#!/usr/bin/env python3
"""B8-4a: does the class ordering by median loop sum replicate across windows.

Read map: `docs/b8_fannie_slice.md` §23, written before this ran.

**B8-4b does not run.** §16.12's C9 gate: eleven grids, minimum cell 0 or 1,
because the Flex modification window is 2017-2019 and the 2019Q1 cohort has at
most a year of age inside it. §15.3 says in terms that this is not B8's
failure, and §15.6's branch lands on corporate credit. Not reopened here.

--------------------------------------------------------------------------
What is measured, and the ceiling written into the prediction
--------------------------------------------------------------------------

§15.5: **the ordering of classes by per-class median loop sum, and whether it
is stable across §6's windows.** Statistic is the mean pairwise Spearman
correlation of the orderings; the null permutes class labels **within window**
on the same design.

**N2, and it is in the prediction rather than discovered afterwards**: this
cannot claim that a *particular* class carries idiosyncratic variation
separable from that class's own sampling noise. What it can claim is that the
class index carries **shared structure that replicates**.

**Association, not causation** (§9). **The bottom of the class range is
truncated by construction** and the truncation points toward the null, so
dispersion is harder to find here, not easier. That sentence travels.

--------------------------------------------------------------------------
Three requirements that are not optional
--------------------------------------------------------------------------

**`k >= 3` (§23.3).** Spearman over two items takes only `+1` and `-1`; two
things do not have an ordering. `fthb` has two levels and therefore does not
run, decided before the run rather than after seeing it. This is pit 47's
lesson applied in advance: a criterion whose difficulty moves with the number
of levels is measuring the number of levels.

**Equal `n` (§15.5).** Recomputed with every class subsampled to the sparsest
class's count. Both figures printed. **An effect present only at unequal `n`
is a thinness artefact and is reported as one**, which is the defect B7 died
of and the reason §15.5 wrote this requirement.

**Cohort conditioning (§13.4).** The 2002-2007 cohorts originated at six to
seven per cent, where cutting the rate is a lever; the 2012-2019 cohorts at
three to four and a half, where only term extension remains. The modification's
value decomposes differently by cohort, so **the ordering is computed inside a
cohort and the cohorts are printed side by side**; a pooled figure is printed
too and labelled pooled.

Usage:

    python experiments/b8_4_class.py run
    python experiments/b8_4_class.py run --only 2019Q1
    python experiments/b8_4_class.py selftest
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_triangles as T                                       # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_cache as C                                           # noqa: E402
import b8_c9_cells as C9                                       # noqa: E402
import b8_0b_floor as F                                        # noqa: E402

OUT = K.ROOT / "results" / "b8_4_class.md"

#: §23.3. `fthb` has two levels and is out: Spearman over two items takes only
#: two values. **Decided before the run.**
GRIDS = ("purpose", "fico_llpa_coarse5", "dti_complement15", "fico_llpa9")

#: §23.3. Below this the statistic cannot resolve an ordering at all and no
#: null rescues it.
MIN_LEVELS = 3

#: Loops a class needs in a window before its median is read.
MIN_CELL = 20

#: §21.2's readability line, reused as §23.2's gate. A class whose own signal
#: dispersion does not clear its own floor contributes no ordering.
FLOOR_RATIO = 1.0

N_PERM = 999
PERM_SEED = 20260817
SUB_REPS = 21                    # subsample draws for the equal-`n` recompute


def _ranks(x: np.ndarray) -> np.ndarray:
    """Ranks with ties averaged, which is what makes the Pearson below a
    Spearman rather than a Spearman-when-nothing-ties."""
    x = np.asarray(x, float)
    order = np.argsort(x, kind="stable")
    r = np.empty(x.size, float)
    r[order] = np.arange(1, x.size + 1, dtype=float)
    uniq, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    if (cnt > 1).any():
        sums = np.bincount(inv, weights=r, minlength=uniq.size)
        r = (sums / cnt)[inv]
    return r


def spearman(a, b) -> float:
    """Spearman's rho as Pearson on tie-averaged ranks. No scipy, and the
    formula `1 - 6*sum(d^2)/(n^3-n)` is not used because it is wrong under
    ties and the medians here can tie."""
    ra, rb = _ranks(a), _ranks(b)
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = float(np.sqrt((ra * ra).sum() * (rb * rb).sum()))
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def class_medians(om: np.ndarray, lab: np.ndarray, win: np.ndarray,
                  classes: np.ndarray, windows: np.ndarray,
                  min_cell: int = MIN_CELL) -> np.ndarray:
    """`(window, class)` matrix of median loop sums, NaN where under the floor."""
    out = np.full((windows.size, classes.size), np.nan)
    for i, w in enumerate(windows):
        mw = win == w
        if not mw.any():
            continue
        ow, lw = om[mw], lab[mw]
        for j, cl in enumerate(classes):
            m = lw == cl
            if int(m.sum()) >= min_cell:
                out[i, j] = float(np.median(ow[m]))
    return out


def mean_pairwise(med: np.ndarray) -> dict:
    """Mean pairwise Spearman over window pairs.

    **A class present in one window and not the other is dropped from that
    pair and counted**: ranking over a changing set is not ranking, which is
    §22.4's rule and applies here for the same reason.
    """
    n = med.shape[0]
    rhos, pairs, used = [], [], []
    for i in range(n):
        for j in range(i + 1, n):
            both = np.isfinite(med[i]) & np.isfinite(med[j])
            if int(both.sum()) < MIN_LEVELS:
                continue
            r = spearman(med[i][both], med[j][both])
            if np.isfinite(r):
                rhos.append(r)
                pairs.append((i, j))
                used.append(int(both.sum()))
    return {"rho": float(np.mean(rhos)) if rhos else float("nan"),
            "n_pairs": len(rhos), "pairs": pairs, "k_used": used,
            "rhos": rhos}


def _blocks(lab: np.ndarray, win: np.ndarray, om: np.ndarray,
            classes: np.ndarray, windows: np.ndarray, min_cell: int):
    """Per window: the loop sums sorted into contiguous class blocks.

    **This is what makes the null affordable.** Permuting labels within a
    window is the same experiment as permuting the loop sums while the labels
    stay put, and if the labels are pre-sorted the class blocks are contiguous,
    so a permutation costs one shuffle and `k` slice medians rather than a
    fresh sort per draw.
    """
    out = []
    for w in windows:
        mw = win == w
        ow, lw = om[mw], lab[mw]
        keep = np.zeros(ow.size, bool)
        cols, bounds = [], []
        order = np.argsort(lw, kind="stable")
        ow, lw = ow[order], lw[order]
        start = 0
        for j, cl in enumerate(classes):
            m = lw == cl
            n = int(m.sum())
            if n >= min_cell:
                cols.append(j)
                bounds.append((start, start + n))
                keep[np.flatnonzero(m)] = True
                start += n
        vals = ow[keep[np.argsort(np.argsort(lw, kind="stable"),
                                  kind="stable")]] if False else ow[keep]
        out.append({"vals": vals, "cols": cols, "bounds": bounds})
    return out


def perm_null(blocks, med: np.ndarray, obs: float, n_perm: int = N_PERM,
              seed: int = PERM_SEED) -> float:
    """§23.6: class labels permuted **within window**, on the same design.

    The design is held fixed: the same windows, the same class column set and
    the same per-class counts. Only which loop carries which label moves.
    """
    if not np.isfinite(obs):
        return float("nan")
    rng = np.random.default_rng(seed)
    shape = med.shape
    ge = 0
    for _ in range(n_perm):
        m = np.full(shape, np.nan)
        for i, b in enumerate(blocks):
            v = b["vals"]
            if v.size == 0:
                continue
            v = rng.permutation(v)
            for j, (lo, hi) in zip(b["cols"], b["bounds"]):
                m[i, j] = np.median(v[lo:hi])
        r = mean_pairwise(m)["rho"]
        if np.isfinite(r) and r >= obs:
            ge += 1
    return (ge + 1) / (n_perm + 1)


def equal_n(om, lab, win, classes, windows, reps: int = SUB_REPS,
            seed: int = PERM_SEED, min_cell: int = None) -> dict:
    """§15.5's equal-`n` recompute: every class cut to the sparsest class's
    count **inside each window**, then the whole statistic again.

    **The point is that thin classes disperse more from sampling alone.** If
    the ordering survives only while the counts are unequal, that is the
    artefact and not the finding.
    """
    rng = np.random.default_rng(seed)
    rhos = []
    for _ in range(reps):
        keep = np.zeros(om.size, bool)
        for w in windows:
            mw = np.flatnonzero(win == w)
            if mw.size == 0:
                continue
            lw = lab[mw]
            mc = MIN_CELL if min_cell is None else min_cell
            sizes = [int((lw == cl).sum()) for cl in classes]
            live = [s for s in sizes if s >= mc]
            if len(live) < MIN_LEVELS:
                continue
            floor = min(live)
            for cl, s in zip(classes, sizes):
                if s < mc:
                    continue
                idx = mw[lw == cl]
                keep[rng.choice(idx, floor, replace=False)] = True
        med = class_medians(om[keep], lab[keep], win[keep], classes, windows)
        r = mean_pairwise(med)["rho"]
        if np.isfinite(r):
            rhos.append(r)
    if not rhos:
        return {"rho": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "reps": 0}
    return {"rho": float(np.median(rhos)), "lo": float(np.min(rhos)),
            "hi": float(np.max(rhos)), "reps": len(rhos)}


def loading(med: np.ndarray, classes: np.ndarray, grid: str) -> list[dict]:
    """§15.5: **which classes carry the ordering**, printed beside it.

    Per class, the mean of its rank across the windows where it was read, and
    the spread of that rank. A class pinned to one end of every window's
    ordering is carrying the correlation; a class that wanders is not.
    """
    out = []
    for j, cl in enumerate(classes):
        rs = []
        for i in range(med.shape[0]):
            both = np.isfinite(med[i])
            kk = int(both.sum())
            if both[j] and kk >= MIN_LEVELS:
                # **`(rank - 1) / (k - 1)`, not `rank / k`.** The latter pins
                # the top of every window at exactly 1.0 while putting the
                # bottom at `1/k`, so with `k` varying across windows a class
                # that never moved off the bottom reports a span. Eight of the
                # twenty-two published cells have a varying `k`.
                rs.append(float((_ranks(med[i][both])[
                    int(np.flatnonzero(np.flatnonzero(both) == j)[0])] - 1.0)
                    / (kk - 1.0)))
        if rs:
            out.append({"level": int(cl), "name": C9.level_name(grid, int(cl)),
                        "n_win": len(rs), "rank_mean": float(np.mean(rs)),
                        "rank_span": float(np.max(rs) - np.min(rs))})
    return sorted(out, key=lambda o: o["rank_mean"])


def floor_by_class(fom, fclosed, flab, classes, min_cell=None) -> dict:
    """§15.4's per-class floor, in §18.7 and section 21.1's definition.

    ``N(a) = MAD(omega - closed)`` on that class's clean cures. **Both
    corrections are in it**: the MAD rather than `2*Var`, because the floor
    arm's variance does not converge; and the closed form subtracted, because
    the clean-cure loop sum **is** `loop_residual_ideal` and what remains is
    field 12's quantisation.

    A pooled floor would let a thin class read as dispersed for the reason B7
    died of, which is why §15.4 requires this one drawn per class.
    """
    out = {}
    mc = MIN_CELL if min_cell is None else min_cell
    res = fom - fclosed
    for cl in classes:
        m = (flab == cl) & np.isfinite(res)
        out[int(cl)] = (float(F.mad_scale(res[m])) if int(m.sum()) >= mc
                        else float("nan"))
    return out


def analyse(name: str, cache_root=None, pos=None, tab=None, core_root=None,
            n_perm: int = N_PERM, min_cell: int = None) -> dict:
    """`min_cell` is a parameter **so the selftest can reach these paths.**
    `b8_loops`' fixture carries five modification loops and two clean cures
    against a production floor of twenty, so every class was gated out, every
    median was NaN, and the checks written against them compared NaN to NaN
    and could not fail. A mutation run said so."""
    mc = MIN_CELL if min_cell is None else min_cell
    d = C.get(name, pos=pos, tab=tab, core_root=core_root or cache_root)
    s, fl = d["sig"], d["floor"]
    with K.Core(name, cols=Z8.COLS + ["zero_bal"],
                cache_root=core_root or cache_root) as c:
        grids = {g: C9.build_grids(c)[g] for g in GRIDS}

    keep = s["measurable"].astype(bool) & (s["arm"] == L.ARM_MOD)
    om, win, loan = (np.asarray(s["omega"], float)[keep],
                     np.asarray(s["window"], np.int64)[keep],
                     np.asarray(s["loan"], np.int64)[keep])
    fk = fl["measurable"].astype(bool) & fl["ideal"].astype(bool)
    fom = np.asarray(fl["omega"], float)[fk]
    fcl = np.asarray(fl["closed"], float)[fk]
    floan = np.asarray(fl["loan"], np.int64)[fk]

    rows = []
    for g in GRIDS:
        lab = np.asarray(grids[g])[loan]
        flab = np.asarray(grids[g])[floan]
        drop = set(C9.EXCLUDED.get(g, {}))
        classes = np.array([v for v in np.unique(lab) if int(v) not in drop])
        windows = np.arange(len(T.WINDOWS))
        if classes.size < MIN_LEVELS:
            rows.append({"grid": g, "skip": f"only {classes.size} levels"})
            continue
        fl_a = floor_by_class(fom, fcl, flab, classes, mc)

        med = class_medians(om, lab, win, classes, windows, mc)
        # §23.2's gate, and **the honest report is that it cannot bite on
        # this data**. `Z(a)/N(a)` is B8-1's own statistic drawn per class,
        # and B8-1 measured it at 2.4e6 to 6.8e6 pooled: the signal sits six
        # orders above the floor, so no class fails a ratio test against it,
        # and §23.2's alternative wording (the class's median against its
        # floor) fails for the same reason, medians being 1e-2 and floors
        # 3e-8. **The gate is kept, run, and reported as inoperative rather
        # than deleted**, because a gate that never fires and a gate that is
        # not there are different facts about the data.
        #
        # What the column actually counted in the first run was classes with
        # no readable floor at all -- fewer than MIN_CELL clean cures of their
        # own -- which is floor-arm thinness and not a floor failure. The two
        # are now counted apart.
        gated_ratio = gated_nofloor = 0
        for j, cl in enumerate(classes):
            m = lab == cl
            z = F.mad_scale(om[m]) if int(m.sum()) >= mc else np.nan
            nf = fl_a.get(int(cl), np.nan)
            if not (np.isfinite(nf) and nf > 0) or not np.isfinite(z):
                med[:, j] = np.nan
                gated_nofloor += 1
            elif z / nf <= FLOOR_RATIO:
                med[:, j] = np.nan
                gated_ratio += 1
        gated = gated_ratio + gated_nofloor
        # **the gate has to reach the null and the equal-`n` recompute too**,
        # or the observed statistic and its null are drawn on different class
        # sets, which is exactly what §23.6 forbids and what B8-5 was fixed for
        live_cls = classes[np.isfinite(med).any(axis=0)]
        in_live = np.isin(lab, live_cls)
        r = mean_pairwise(med)
        blocks = _blocks(lab[in_live], win[in_live], om[in_live], live_cls,
                         windows, mc)
        med_live = med[:, np.isfinite(med).any(axis=0)]
        rows.append({
            "grid": g, "skip": None, "k": int(classes.size), "gated": gated,
            "gated_ratio": gated_ratio, "gated_nofloor": gated_nofloor,
            "n": int(om.size), "rho": r["rho"], "n_pairs": r["n_pairs"],
            "k_used": r["k_used"], "rhos": r["rhos"], "pairs": r["pairs"],
            "p": perm_null(blocks, med_live, r["rho"], n_perm=n_perm),
            # the null's design, printed nowhere but asserted: it must be the
            # observed design and not the ungated one
            "null_cols": [len(b["cols"]) for b in blocks],
            "live_cols": int(np.isfinite(med).any(axis=0).sum()),
            "eq": equal_n(om[in_live], lab[in_live], win[in_live], live_cls,
                          windows, min_cell=mc),
            "load": loading(med, classes, g),
            "floor": {int(cl): fl_a.get(int(cl), float("nan"))
                      for cl in classes},
        })
    return {"name": name, "rows": rows, "n_loops": int(om.size),
            "n_floor": int(fom.size)}


def sign_test(rhos) -> dict:
    """Two-sided sign test on the per-cohort correlations.

    **§23.7's pass condition names cohort agreement and the first version of
    this file did not compute it.** The verdict checked "more than one cohort
    reached significance", which is a different and weaker question: six
    cohorts all leaning the same way is evidence even when no single one
    clears 0.05 on its own, and it is the cross-cohort replication §13.4 asks
    for. Exact zeros are dropped and counted; they are not evidence either way.
    """
    r = [x for x in rhos if np.isfinite(x)]
    pos = sum(1 for x in r if x > 0)
    neg = sum(1 for x in r if x < 0)
    zero = len(r) - pos - neg
    n = pos + neg
    if n == 0:
        return {"n": 0, "pos": 0, "neg": 0, "zero": zero, "p": float("nan")}
    k = max(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / (2.0 ** n)
    return {"n": n, "pos": pos, "neg": neg, "zero": zero,
            "p": float(min(1.0, 2.0 * tail))}


def verdict(n_sig: int, n_surv: int, agree: list) -> str:
    """§23.7's map, as one function so it can be driven on hand-built counts.

    It was four nested conditionals inside `render`, where the only way to
    reach the branches was to have data that hit them. §23.7 registers four
    outcomes and each has to be reachable in a test.
    """
    if n_surv > 0 and agree:
        return ("**B8-4a holds**: the class index carries structure that "
                "replicates across windows, on `" + "`, `".join(agree) + "`")
    if n_surv > 0:
        return ("**not established**: individual cells reach 0.05 but no "
                "grid's sign agrees across cohorts, so a cohort effect "
                "wearing a class effect's clothes is not excluded (§13.4)")
    if n_sig > 0:
        return "**thinness artefact**: significant only at unequal `n`"
    return "**not established on this data**"


def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:+.{k}f}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-4a: does the class ordering replicate across windows\n")
    A("Generated by `experiments/b8_4_class.py`. Read map in "
      "`docs/b8_fannie_slice.md` §23, written before this ran.\n")
    A("**B8-4b does not run** (§16.12): C9 gave eleven grids a minimum cell of "
      "0 or 1, because the Flex window is 2017-2019 and the 2019Q1 cohort has "
      "at most a year inside it. §15.3 says in terms that this is not B8's "
      "failure.\n")
    A(f"**`fthb` does not run** (§23.3): two levels, and Spearman over two "
      "items takes only `+1` and `-1`. Decided before the run, not after "
      "seeing it.\n")
    A("**N2, written into the prediction**: this cannot claim that a "
      "particular class carries idiosyncratic variation separable from its own "
      "sampling noise. It can claim the class index carries **shared, "
      "replicating** structure.\n")
    A("**Association, not causation** (§9). **The bottom of the class range is "
      "truncated by construction** and the truncation points toward the null, "
      "so dispersion is harder to find here. **This sentence travels with "
      "every citation.**\n")
    A("**Read per cohort** (§13.4): the 2002-2007 cohorts originated at six to "
      "seven per cent, where cutting the rate is a lever; the 2012-2019 "
      "cohorts at three to four and a half, where only term extension remains. "
      "A pooled reading would let a cohort effect present as a class effect.\n")
    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"

    A("\n## 1. The statistic, per cohort\n")
    A("Mean pairwise Spearman of the per-window class orderings. `gated` "
      "counts classes dropped because their own signal dispersion did not "
      "clear their own floor `N(a) = MAD(omega - closed)` (§23.2).\n")
    A("**`gated` cannot bite on this data and is reported as such.** "
      "`Z(a)/N(a)` is B8-1's own statistic drawn per class, and B8-1 measured "
      "it at 2.4e6 to 6.8e6: the signal sits six orders above the floor, so "
      "no class fails a ratio test against it. `no floor` counts classes with "
      "fewer than "
      f"{MIN_CELL} clean cures of their own, which is floor-arm thinness and "
      "**a different fact** from failing the floor.\n")
    A("| cohort | grid | levels | gated: ratio | gated: no floor | window "
      "pairs | classes per pair | **rho** | **p** | equal-`n` rho | "
      "equal-`n` range |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for r in a["rows"]:
            if r["skip"]:
                A(f"| {a['name']} | `{r['grid']}` | - | - | - | - | - | - | "
                  f"- | - | _{r['skip']}_ |")
                continue
            ku = (f"{min(r['k_used'])}-{max(r['k_used'])}" if r["k_used"]
                  else "-")
            A(f"| {a['name']} | `{r['grid']}` | {r['k']} | "
              f"{r['gated_ratio']} | {r['gated_nofloor']} | "
              f"{r['n_pairs']} | {ku} | **{_f(r['rho'])}** | "
              f"**{_f(r['p'], 3)}** | {_f(r['eq']['rho'])} | "
              f"{_f(r['eq']['lo'])} to {_f(r['eq']['hi'])} |")

    A("\n## 2. Equal `n`, which is where a thinness artefact dies\n")
    A(f"§15.5: every class cut to the sparsest class's count inside each "
      f"window, {SUB_REPS} draws, the whole statistic recomputed. **An effect "
      "present only at unequal `n` is a thinness artefact and is reported as "
      "one.** That is the defect `b7_interaction_rank.md` died of.\n")
    A("| cohort | grid | rho, all loops | rho, equal `n` | ratio | "
      "**survives** |")
    A("|---|---|---|---|---|---|")
    for a in rows:
        for r in a["rows"]:
            if r["skip"]:
                continue
            q = (r["eq"]["rho"] / r["rho"]
                 if np.isfinite(r["rho"]) and abs(r["rho"]) > 1e-12
                 else float("nan"))
            ok = (np.isfinite(r["eq"]["rho"]) and np.isfinite(r["rho"])
                  and r["eq"]["lo"] > 0 and r["rho"] > 0)
            A(f"| {a['name']} | `{r['grid']}` | {_f(r['rho'])} | "
              f"{_f(r['eq']['rho'])} | {_f(q)} | "
              f"**{'yes' if ok else 'no'}** |")

    A("\n## 3. The loading: which classes carry it\n")
    A("§15.5, and the reason it is a requirement: `b7_interaction_rank.md` "
      "read a rank for a day and a half before anyone printed the "
      "eigenvectors. `rank` is the class's position in the window's ordering "
      "as a fraction, averaged over the windows it was read in; `span` is how "
      "far that position moved. **A class pinned to one end of every window "
      "carries the correlation; one that wanders does not.**\n")
    A("| cohort | grid | class | windows read | mean rank | span | "
      "floor `N(a)` |")
    A("|---|---|---|---|---|---|---|")
    for a in rows:
        for r in a["rows"]:
            if r["skip"] or not np.isfinite(r["rho"]):
                continue
            for o in r["load"]:
                A(f"| {a['name']} | `{r['grid']}` | `{o['name']}` | "
                  f"{o['n_win']} | {o['rank_mean']:.3f} | "
                  f"{o['rank_span']:.3f} | "
                  f"{r['floor'].get(o['level'], float('nan')):.4e} |")

    A("\n## 4. Does the sign agree across cohorts\n")
    A("**§23.7's pass condition names this and section 1 cannot answer it.** "
      "Six cohorts leaning the same way is evidence even where no single one "
      "clears 0.05 alone, and it is exactly the cross-cohort replication "
      "§13.4 asks for. Exact zeros are dropped and counted: they are not "
      "evidence either way.\n")
    A("| grid | cohorts read | positive | negative | zero | **sign test `p`** "
      "| rho by cohort |")
    A("|---|---|---|---|---|---|---|")
    signs = {}
    for g in GRIDS:
        rs = [r["rho"] for a in rows for r in a["rows"]
              if not r["skip"] and r["grid"] == g and np.isfinite(r["rho"])]
        st = sign_test(rs)
        signs[g] = st
        A(f"| `{g}` | {len(rs)} | {st['pos']} | {st['neg']} | {st['zero']} | "
          f"**{_f(st['p'], 4)}** | "
          + ", ".join(f"{x:+.2f}" for x in rs) + " |")
    A("\n**A cell resting on one window pair is nearly vacuous** and is "
      "marked in section 1 by `window pairs = 1`: a single Spearman over "
      f"{MIN_LEVELS} classes takes four values, so its `p` cannot go below "
      "about 0.08 whatever the data does.\n")

    A("\n## 5. The verdict\n")
    live = [r for a in rows for r in a["rows"]
            if not r["skip"] and np.isfinite(r["rho"])]
    sig = [r for r in live if r["p"] < 0.05 and r["rho"] > 0]
    surv = [r for r in sig if r["eq"]["lo"] > 0]
    coh = {a["name"] for a in rows for r in a["rows"]
           if not r["skip"] and np.isfinite(r["rho"]) and r["p"] < 0.05
           and r["rho"] > 0}
    agree = [g for g, st in signs.items()
             if st["n"] >= 3 and st["p"] < 0.05]
    A("| readable cells | positive and `p` < 0.05 | **and survives equal "
      "`n`** | cohorts carrying it | grids agreeing across cohorts | "
      "**reading** |")
    A("|---|---|---|---|---|---|")
    A(f"| {len(live)} | {len(sig)} | {len(surv)} | {len(coh)} | "
      f"{len(agree)} | {verdict(len(sig), len(surv), agree)} |")
    A("\n§23.7's map. **Whatever this says, N2's ceiling stands**: the claim "
      "is about the class index carrying shared replicating structure, never "
      "about a particular class's own variation.\n")

    A("\n## What this does not decide\n")
    A("- **Whether any single class carries idiosyncratic variation.** N2, "
      "not separable on this design, written into the prediction.")
    A("- **B8-4b.** §16.12's C9 gate settled it; §15.6's branch goes to "
      "corporate credit.")
    A("- **Why servicers order classes this way.** No servicer-side variable "
      "exists in this file.")
    A("- Causality of any kind.\n")
    return "\n".join(Ls) + "\n"


def selftest() -> int:
    fails: list[str] = []

    # -- spearman, against cases with known answers -----------------------
    if abs(spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) > 1e-12:
        fails.append("identical orderings did not give rho = 1")
    if abs(spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) > 1e-12:
        fails.append("reversed orderings did not give rho = -1")
    # **monotone but not linear must still be exactly 1**, which is the whole
    # difference between Spearman and Pearson and the reason ranks are taken
    if abs(spearman([1, 2, 3, 4], [1, 10, 1000, 1e6]) - 1.0) > 1e-12:
        fails.append("a monotone non-linear map did not give rho = 1; this is "
                     "Pearson on the values, not on the ranks")
    # ties must be averaged, not broken by position
    if abs(spearman([1, 1, 2, 2], [1, 1, 2, 2]) - 1.0) > 1e-12:
        fails.append("tied values did not give rho = 1")
    if abs(spearman([1, 1, 2, 2], [2, 2, 1, 1]) + 1.0) > 1e-12:
        fails.append("tied values reversed did not give rho = -1")
    if np.isfinite(spearman([1, 1, 1], [1, 2, 3])):
        fails.append("a constant vector gave a finite rho; the correlation is "
                     "undefined there and must say so")

    # -- class_medians and mean_pairwise on a built table ------------------
    classes, windows = np.array([0, 1, 2]), np.arange(3)
    n = MIN_CELL
    lab = np.tile(np.repeat(classes, n), 3)
    win = np.repeat(windows, 3 * n)
    # a perfectly stable ordering: class 0 lowest, class 2 highest, everywhere
    om = np.tile(np.repeat([1.0, 2.0, 3.0], n), 3) + 0.0
    med = class_medians(om, lab, win, classes, windows)
    r = mean_pairwise(med)
    if abs(r["rho"] - 1.0) > 1e-12 or r["n_pairs"] != 3:
        fails.append(f"a perfectly stable ordering gave rho {r['rho']} over "
                     f"{r['n_pairs']} pairs, expected 1.0 over 3")
    # one window reversed must pull the mean down, and by a known amount:
    # two pairs at -1 and one at +1 average to -1/3
    om2 = om.copy()
    om2[:3 * n] = np.repeat([3.0, 2.0, 1.0], n)
    r2 = mean_pairwise(class_medians(om2, lab, win, classes, windows))
    if abs(r2["rho"] + 1.0 / 3.0) > 1e-12:
        fails.append(f"one reversed window gave rho {r2['rho']}, expected "
                     "-0.333333 from two pairs at -1 and one at +1")
    # **a class below MIN_CELL must not get a median**, or a three-loop class
    # sets the ordering
    lab3 = lab.copy()
    thin = np.flatnonzero((lab == 2) & (win == 0))[:-3]
    keep3 = np.ones(lab.size, bool)
    keep3[thin] = False
    m3 = class_medians(om[keep3], lab3[keep3], win[keep3], classes, windows)
    if np.isfinite(m3[0, 2]):
        fails.append("a class with 3 loops in a window got a median; "
                     f"MIN_CELL = {MIN_CELL} is not being applied")
    # and a pair that drops below MIN_LEVELS must be skipped, not ranked on 2
    if mean_pairwise(np.array([[1.0, 2.0, np.nan],
                               [1.0, 2.0, np.nan]]))["n_pairs"] != 0:
        fails.append("a window pair sharing only two classes was ranked; "
                     f"MIN_LEVELS = {MIN_LEVELS} does not bite")
    # **only the classes read in BOTH windows enter a pair.** A class read in
    # one window and not the other has no ordering to contribute, and taking
    # the union instead ranks a NaN.
    lop = np.array([[1.0, 2.0, 3.0, np.nan],           # window 0 lacks class 3
                    [np.nan, 2.0, 3.0, 4.0]])          # window 1 lacks class 0
    if mean_pairwise(lop)["n_pairs"] != 0:
        fails.append("a pair sharing only two classes ran; the shared set is "
                     "being taken as the union rather than the intersection")
    lop2 = np.array([[1.0, 2.0, 3.0, 4.0],
                     [np.nan, 9.0, 5.0, 7.0]])         # shared {1,2,3}
    r_int = mean_pairwise(lop2)
    if r_int["n_pairs"] != 1 or r_int["k_used"] != [3]:
        fails.append(f"the shared set read {r_int['k_used']}, expected [3]")
    elif abs(r_int["rho"] - spearman([2.0, 3.0, 4.0], [9.0, 5.0, 7.0])) > 1e-12:
        fails.append("the pair's rho is not the rho of the shared classes")

    # -- the null must hold its size and see a real ordering ---------------
    blocks = _blocks(lab, win, om, classes, windows, MIN_CELL)
    p_sig = perm_null(blocks, med, 1.0, n_perm=199)
    if not p_sig < 0.05:
        fails.append(f"a perfectly stable ordering gave p = {p_sig}")
    rng = np.random.default_rng(11)
    om_n = rng.normal(size=lab.size)
    med_n = class_medians(om_n, lab, win, classes, windows)
    obs_n = mean_pairwise(med_n)["rho"]
    p_noise = perm_null(_blocks(lab, win, om_n, classes, windows, MIN_CELL),
                        med_n, obs_n, n_perm=399)
    if p_noise < 0.05:
        fails.append(f"pure noise gave p = {p_noise}; the null does not hold "
                     "its size")
    # **the null must be drawn on the same design**: same per-class counts. If
    # it were not, the observed and null statistics would not be comparable.
    b = _blocks(lab, win, om, classes, windows, MIN_CELL)
    if [len(x["cols"]) for x in b] != [3, 3, 3]:
        fails.append(f"the null design lost columns: {[len(x['cols']) for x in b]}")
    if [x["vals"].size for x in b] != [3 * n] * 3:
        fails.append("the null design lost loops")
    # **a class below the floor must not become a block.** It has no observed
    # median, so giving it one under the null compares two different designs.
    kt = np.ones(lab.size, bool)
    kt[np.flatnonzero((lab == 2) & (win == 0))[:-3]] = False
    bt = _blocks(lab[kt], win[kt], om[kt], classes, windows, MIN_CELL)
    if [len(x["cols"]) for x in bt] != [2, 3, 3]:
        fails.append(f"a 3-loop class became a null block: "
                     f"{[len(x['cols']) for x in bt]}, expected [2, 3, 3]")
    if bt[0]["vals"].size != 2 * n:
        fails.append(f"the thin class's loops stayed in the null's pool "
                     f"({bt[0]['vals'].size}), so the permutation deals them "
                     "into classes the observation never gave them to")

    # -- equal `n` must be able to kill a thinness artefact ----------------
    # class 2 gets three times the loops and a wider spread; at equal `n` the
    # ordering has to be recomputed on the same counts
    eq = equal_n(om, lab, win, classes, windows, reps=5)
    if abs(eq["rho"] - 1.0) > 1e-12:
        fails.append(f"equal-`n` on a perfectly stable ordering gave "
                     f"{eq['rho']}, expected 1.0")
    if eq["reps"] != 5:
        fails.append(f"equal-`n` completed {eq['reps']} of 5 draws")
    # **on unequal counts it must cut to the sparsest.** Every class here has
    # the same count, so nothing above can tell the sparsest from the largest;
    # this builds a cell where class 2 is half the size of class 0.
    cnt = [n, n + 10, n + 20]
    lab_u = np.tile(np.repeat(classes, cnt), 3)
    win_u = np.repeat(windows, sum(cnt))
    om_u = np.tile(np.repeat([1.0, 2.0, 3.0], cnt), 3)
    sizes = [int(((lab_u == cl) & (win_u == 0)).sum()) for cl in classes]
    if sizes != cnt:
        fails.append(f"the unequal-count fixture is not unequal: {sizes}")
    eq2 = equal_n(om_u, lab_u, win_u, classes, windows,
                  reps=5)
    if eq2["reps"] != 5 or abs(eq2["rho"] - 1.0) > 1e-12:
        fails.append(f"equal-`n` on unequal counts gave rho {eq2['rho']} over "
                     f"{eq2['reps']} draws; cutting to the largest class "
                     "rather than the sparsest cannot draw without "
                     "replacement and would not get here")

    # -- loading must name the ends ---------------------------------------
    lo = loading(med, classes, "purpose")
    if len(lo) != 3:
        fails.append(f"loading returned {len(lo)} classes, expected 3")
    elif not (lo[0]["level"] == 0 and lo[-1]["level"] == 2):
        fails.append("loading did not put class 0 at the bottom and class 2 "
                     "at the top of a strictly increasing ordering")
    elif max(o["rank_span"] for o in lo) > 1e-12:
        fails.append("a class pinned to the same position in every window "
                     "reported a non-zero span")
    elif abs(lo[0]["rank_mean"]) > 1e-12 or abs(lo[-1]["rank_mean"] - 1.0) > 1e-12:
        fails.append(f"the ends read {lo[0]['rank_mean']} and "
                     f"{lo[-1]['rank_mean']}, expected 0 and 1")
    # **the rank must not depend on how many classes the window read.** A
    # class at the bottom of a 9-class window and the bottom of a 4-class
    # window is at the bottom both times, and `rank / k` would call that a
    # move of 0.14. Eight of the twenty-two published cells have a varying k.
    vk = loading(np.array([[0.0, 1.0, 2.0, 3.0, 4.0],
                           [0.0, 1.0, 2.0, np.nan, np.nan]]),
                 np.arange(5), "purpose")
    by_lv = {o["level"]: o for o in vk}
    if abs(by_lv[0]["rank_span"]) > 1e-12:
        fails.append(f"a class at the bottom of a 5-class window and the "
                     f"bottom of a 3-class window reported span "
                     f"{by_lv[0]['rank_span']:.4f}; the rank is normalised by "
                     "`k` at one end only")
    if abs(by_lv[2]["rank_mean"] - 0.75) > 1e-12:
        fails.append(f"class 2 read rank {by_lv[2]['rank_mean']}, expected "
                     "0.75 = mean of 2/4 and 2/2")
    # **and a class that moves must report that it moved.** The span is the
    # only column saying whether a class is carrying the correlation or
    # wandering, so a span that is always zero is worse than no column.
    mv = loading(np.array([[1.0, 2.0, 3.0],
                           [1.0, 3.0, 2.0],
                           [1.0, 2.0, 3.0]]), classes, "purpose")
    spans = {o["level"]: o["rank_span"] for o in mv}
    if spans.get(0, -1) > 1e-12:
        fails.append("the pinned class reported a moving rank")
    if not (spans.get(1, 0) > 0.3 and spans.get(2, 0) > 0.3):
        fails.append(f"two classes swapped position between windows and the "
                     f"span read {spans}; it is not measuring movement")

    # -- the per-class floor ----------------------------------------------
    # **Built in the empirical shape B8-0b found**: the clean-cure loop sum
    # swings over orders of magnitude and the closed form tracks it at
    # `corr = +1.0000`, so the raw dispersion is huge and the residual is
    # tiny. A floor that forgets to subtract, or that uses `2*Var` instead of
    # the MAD, is invisible on a fixture where the two are both zero.
    res20 = np.concatenate([np.full(5, -2.0), np.full(5, -1.0),
                            np.full(5, 1.0), np.full(5, 2.0)])
    closed0 = np.linspace(100.0, 500.0, MIN_CELL)
    fom = np.concatenate([closed0 + res20, np.full(MIN_CELL, 7.0)])
    fcl = np.concatenate([closed0, np.full(MIN_CELL, 7.0)])
    flab = np.repeat([0, 1], MIN_CELL)
    fl_a = floor_by_class(fom, fcl, flab, np.array([0, 1, 2]))
    # median of the residual is 0, median |residual| is 1.5, so 1.4826 * 1.5
    want = 1.4826 * 1.5
    if abs(fl_a[0] - want) > 1e-12:
        fails.append(f"the per-class floor read {fl_a[0]:.6f}, expected "
                     f"{want:.6f} = 1.4826 * MAD of the residual. Either the "
                     "closed form is not subtracted or the estimator is not "
                     "the MAD (`2*Var` of the same residual is 5.0)")
    if fl_a[1] != 0.0:
        fails.append(f"a class whose loops equal their closed form gave a "
                     f"non-zero floor: {fl_a[1]}")
    if np.isfinite(fl_a[2]):
        fails.append("a class with no floor loops got a finite floor")

    # -- the cross-cohort sign test ---------------------------------------
    # **Six of six one way is p = 0.03125 exactly**, and that number is what
    # §23.7's cohort-agreement condition rests on, so it is pinned rather than
    # trusted to a library.
    st = sign_test([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    if abs(st["p"] - 2.0 / 64.0) > 1e-15 or st["pos"] != 6:
        fails.append(f"six positives out of six gave p = {st['p']}, expected "
                     f"{2 / 64}")
    if abs(sign_test([-0.1] * 6)["p"] - 2.0 / 64.0) > 1e-15:
        fails.append("the sign test is one-sided; six negatives must give the "
                     "same p as six positives")
    # five of six is 2 * (6 + 1) / 64
    if abs(sign_test([0.1, 0.2, 0.3, 0.4, 0.5, -0.6])["p"]
           - 2.0 * 7.0 / 64.0) > 1e-15:
        fails.append("five of six did not give p = 0.21875")
    # a split must not be evidence
    if sign_test([0.1, -0.2, 0.3, -0.4])["p"] < 0.99:
        fails.append("an even split read as evidence")
    # **exact zeros are dropped, not counted as agreement**, or a grid that
    # read 0.0 in half its cohorts would look unanimous
    z = sign_test([0.1, 0.2, 0.0, 0.0])
    if z["n"] != 2 or z["zero"] != 2:
        fails.append(f"zeros were not dropped: {z}")
    if not np.isnan(sign_test([np.nan, np.nan])["p"]):
        fails.append("a grid with no readable cohort produced a sign-test p")
    # **a NaN cohort is absent, not a tie.** Counting it as one inflates the
    # zero column and makes a grid look like it read cohorts it did not.
    nz = sign_test([0.1, 0.2, np.nan])
    if nz["n"] != 2 or nz["zero"] != 0:
        fails.append(f"an unreadable cohort was counted as a zero: {nz}")

    # -- §23.7's four outcomes, each reachable ----------------------------
    if "holds" not in verdict(3, 2, ["fico_llpa9"]):
        fails.append("survival plus cohort agreement did not read as holding")
    if "holds" in verdict(3, 2, []):
        fails.append("**cells reaching 0.05 with no cohort agreement read as "
                     "holding.** §23.7 names cohort agreement in the pass "
                     "condition and this is the branch that enforces it")
    if "thinness" not in verdict(3, 0, []):
        fails.append("significant cells that all died at equal `n` did not "
                     "read as a thinness artefact")
    if "not established on this data" not in verdict(0, 0, []):
        fails.append("nothing significant did not read as not established")

    # -- end to end on `b8_loops`' fixture ---------------------------------
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    with K.Core(zp.stem, cols=Z8.COLS, cache_root=cr) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab = Z8._flat_curve(months)
    a = analyse(zp.stem, cache_root=root / "loopcache", pos=pos, tab=tab,
                core_root=cr, n_perm=19, min_cell=2)
    if a["n_loops"] == 0:
        fails.append("no measurable modification loop on the fixture")
    # **the null must be drawn on the classes the observation used.** The gate
    # NaNs columns out of `med`; if `_blocks` is still built from every class,
    # the permutation deals loops to columns the observed statistic never had
    # and its `p` is anti-conservative. Checked through `analyse`, because the
    # hand-built block tests above cannot see which arguments it passes.
    for r_ in a["rows"]:
        if r_["skip"]:
            continue
        if max(r_["null_cols"], default=0) > r_["live_cols"]:
            fails.append(f"`{r_['grid']}`: the null carries "
                         f"{max(r_['null_cols'])} class columns where the "
                         f"observed statistic read {r_['live_cols']}")
    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The statistic, per cohort", "## 2. Equal `n`",
                 "## 3. The loading", "## 4. Does the sign agree across "
                 "cohorts", "## 5. The verdict"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    if "fthb" in [r["grid"] for r in a["rows"]]:
        fails.append("`fthb` entered the run; §23.3 rules it out at two levels")
    print(f"  fixture: {a['n_loops']} loops, {a['n_floor']} clean cures, "
          f"{len(a['rows'])} grids", file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, rho reads a known ordering and the null holds its "
          "size", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        best = [f"{r['grid']}={r['rho']:+.3f}(p={r['p']:.3f})"
                for r in a["rows"] if not r["skip"] and np.isfinite(r["rho"])]
        print(f"  done {n}: " + ", ".join(best), file=sys.stderr)
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
