"""B7-16: the cross-fold second moment, which takes the noise off the diagonal.

Pre-registered in the project's document set as B7's design file, section 2,
**before this file was written**. Every reading it can return is declared there.

Why
---
B7-4 was withdrawn because `S` is a diagonal matrix of nineteen class noise
levels. Write `gamma(c,a) = mu(c,a) + e(c,a)` with `Var(e) = sigma_a^2 / n(c,a)`:

    a != b :  E[S(a,b)] = E[mu(c,a) mu(c,b)]                    clean
    a == b :  E[S(a,a)] = E[mu(c,a)^2] + E[sigma_a^2 / n(c,a)]  the artefact

**Every bit of the artefact is in that second term and it lives only on the
diagonal.** So split each cell-class entry's loans into two halves, centre each
half on its own, and take

    Stilde(a,b) = mean over cells of gamma0(c,a) * gamma1(c,b), symmetrised.

`e0` and `e1` come from disjoint loans, so they are independent and

    E[Stilde(a,a)] = E[mu(c,a)^2]

with **no noise term**. This is the leave-out variance-component construction
(Kline-Saggio-Solvsten and the value-added literature). Its one requirement is
`n(c,a) >= 2`, which is what `--depth` measures before anything is estimated.

Two consequences that are features and not defects
--------------------------------------------------
* **`Stilde` is not positive semi-definite and will show negative eigenvalues.**
  A negative eigenvalue is direct evidence that the noise correction removed more
  than there was, that is, that the direction held nothing. **Nothing is clipped
  to zero here.** The whole spectrum prints.
* **The null changes with it.** `Stilde` has the noise differenced out, so the
  null hypothesis can be stated as the thing that was actually in doubt: `M` is
  diagonal, classes share no direction. It is drawn by permuting, per class, the
  cell index of the pair `(gamma0, gamma1)` **jointly**. That leaves each class's
  own diagonal entry **exactly** unchanged and randomises every off-diagonal.
  B7's original null could not do this, and that is why it was biased low.

The reading is a `z`, not an exceedance count
---------------------------------------------
`lambda_1` under this null sits just above `max(diag)`, so "did it beat all the
draws" wastes the information in the draws. This prints the null's mean and sd
and the observed margin in sd units, plus the sd's own relative error so the
draw count can be judged rather than assumed. Per engineering rule 12 there is **no
threshold anywhere in this file**.

Usage::

    python experiments/b7_crossfold.py --depth     # the gate, estimates nothing
    python experiments/b7_crossfold.py --run       # the estimator

Writes ``results/b7_crossfold_depth.json`` / ``results/b7_crossfold.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b7_design import build_design, describe_partition  # noqa: E402
from monetary_topology.interaction_rank import (  # noqa: E402
    CENTRE_MAX_ITER,
    CENTRE_TOL,
    alternating_centre,
    cell_class_table,
    pairwise_second_moment,
)

RESULTS = ROOT / "results"

#: One seed for the fold assignment and one for the null. Both are recorded in
#: the output so a run is reproducible from its own record.
SEED_FOLD = 20260816
SEED_NULL = 20260817

#: Default null draws. **Not a pinned constant**: the reading is a `z` against
#: the null's own sd, an sd on `d` draws carries relative error `1/sqrt(2(d-1))`,
#: and the run prints that error so the count can be revised against the arm
#: rather than inherited. engineering rule 13.
DRAWS_DEFAULT = 20


def entry_folds(cells, classes, n_classes, rng):
    """Split each cell-class entry's loans alternately into two folds.

    A balanced alternating split rather than an independent coin: every entry
    holding `n >= 2` loans then contributes to **both** folds with certainty,
    so the usable set is exactly `{n(c,a) >= 2}` and `--depth` measures it
    without reference to the draw. Entries holding one loan land in one fold and
    are dropped by the both-present mask.
    """
    flat = np.asarray(cells, dtype=np.int64) * n_classes + np.asarray(classes)
    key = rng.random(flat.size)
    order = np.lexsort((key, flat))
    f_sorted = flat[order]
    new = np.empty(f_sorted.size, dtype=bool)
    new[0] = True
    new[1:] = f_sorted[1:] != f_sorted[:-1]
    grp = np.cumsum(new) - 1
    start = np.flatnonzero(new)
    pos = np.arange(f_sorted.size) - start[grp]
    # **The parity offset is drawn per entry, not fixed at zero.** With a fixed
    # start every odd entry hands its extra loan to fold 0 and every `n = 1`
    # entry lands entirely in fold 0, which put 9,355,723 loans against 6,679,675
    # in the first run: a 58/42 split. That biases nothing, since both folds
    # estimate the same additive fit, but it leaves fold 1's centring on 29% less
    # data, which raises `Var(Stilde)` while its mean stays put. A per-entry
    # offset balances the folds and costs one array.
    offset = (rng.random(start.size) < 0.5).astype(np.int8)
    fold = np.empty(f_sorted.size, dtype=np.int8)
    fold[order] = ((pos + offset[grp]) % 2).astype(np.int8)
    return fold


def cross_second_moment(g0, g1, present2):
    """`Stilde(a,b)` over cells where both classes are present in both folds."""
    p = present2.astype(np.float64)
    cooccur = p.T @ p
    numer = (g0 * present2).T @ (g1 * present2)
    s = np.divide(numer, cooccur, out=np.zeros_like(numer), where=cooccur > 0)
    return 0.5 * (s + s.T), cooccur


def null_spectrum(g0, g1, present2, rng, keep=None):
    """One draw under `M` diagonal: permute each class's cells, both folds alike."""
    g0p = np.zeros_like(g0)
    g1p = np.zeros_like(g1)
    for a in range(g0.shape[1]):
        idx = np.flatnonzero(present2[:, a])
        if idx.size == 0:
            continue
        perm = rng.permutation(idx)
        g0p[perm, a] = g0[idx, a]
        g1p[perm, a] = g1[idx, a]
    s, _ = cross_second_moment(g0p, g1p, present2)
    if keep is not None:
        s = s[np.ix_(keep, keep)]
    vals, vecs = np.linalg.eigh(s)
    return vals[::-1], vecs[:, ::-1]


#: The class scale, low to high. **The estimator never sees this.** To the code
#: the classes are unordered labels, and the null permutes cells within a class,
#: so a null draw's off-diagonals carry no ordering at all. That is what makes an
#: ordered loading vector evidence rather than description.
DTI_ORDER = (["<20%", "20%-<30%", "30%-<36%"]
             + [str(i) for i in range(36, 50)]
             + ["50%-60%", ">60%"])


def kendall_tau_dec(x) -> float:
    """Net share of pairs that fall along the given order. `+1` is monotone down."""
    n = len(x)
    if n < 2:
        return float("nan")
    c = d = 0
    for p in range(n):
        for q in range(p + 1, n):
            if x[q] < x[p]:
                c += 1
            elif x[q] > x[p]:
                d += 1
    return (c - d) / (n * (n - 1) / 2.0)


def ordering_statistic(v, rank_of):
    """`|tau|` of the loadings along the class scale, **dropping the largest one**.

    Three choices, each because the same function has to be computable on a null
    draw as on the observation:

    * **the dropped coordinate is a rule, not a name.** Whichever entry carries
      the largest `|loading|` goes, so a null draw whose leading direction sits on
      a different class is treated identically. Naming `<20%` would have measured
      the observation with one ruler and the null with another.
    * **absolute value**, because an eigenvector's sign is arbitrary and monotone
      in either direction is the same structure.
    * **dropping at all**, because the leading coordinate is where the diagonal
      lives, and the question is whether what is *left over* is ordered.
    """
    j = int(np.argmax(np.abs(v)))
    keep = sorted((i for i in range(len(v)) if i != j), key=lambda i: rank_of[i])
    return abs(kendall_tau_dec([float(v[i]) for i in keep])), j


def centre_with_effects(table):
    """`alternating_centre`, but keeping the two main effects it subtracts.

    The library returns only `gamma`. The class main effect `m(a)` is needed here
    because of one alternative that nothing so far can rule out: if a cell's DTI
    **measurement axis** is shifted (a different income definition, a different
    rounding habit, a different lender mix), every loan in that cell moves along
    the class index together, and the residual is

        gamma(c,a) ~ -delta(c) * m'(a)

    which is **rank one with a loading proportional to the derivative of the class
    main effect**. If `m` is convex, `m'` is monotone, and that measurement story
    produces exactly the shape a pricing story produces. The two are told apart by
    which of `m` and `m'` the loading actually tracks.

    A self-check asserts this reproduces the library's `gamma`, because a second
    copy of a centring is a second chance for two copies to stop agreeing.
    """
    w = table.counts * table.present
    gamma = table.means * table.present
    cell_eff = np.zeros(gamma.shape[0])
    class_eff = np.zeros(gamma.shape[1])
    residual, it = np.inf, 0
    for it in range(1, CENTRE_MAX_ITER + 1):
        row_w = w.sum(axis=1)
        row_mean = np.divide((w * gamma).sum(axis=1), row_w,
                             out=np.zeros_like(row_w), where=row_w > 0)
        gamma = (gamma - row_mean[:, None]) * table.present
        cell_eff += row_mean
        col_w = w.sum(axis=0)
        col_mean = np.divide((w * gamma).sum(axis=0), col_w,
                             out=np.zeros_like(col_w), where=col_w > 0)
        gamma = (gamma - col_mean[None, :]) * table.present
        class_eff += col_mean
        residual = float(max(np.abs(row_mean).max(), np.abs(col_mean).max()))
        if residual < CENTRE_TOL:
            break
    return gamma, cell_eff, class_eff, it, residual


def abs_corr(x, y):
    """`|Pearson|`. Absolute because an eigenvector's sign is arbitrary."""
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    y = np.asarray(y, dtype=np.float64) - np.mean(y)
    dx, dy = np.sqrt((x * x).sum()), np.sqrt((y * y).sum())
    return float(abs((x * y).sum() / (dx * dy))) if dx > 0 and dy > 0 else float("nan")


#: The DTI midpoint of each class, in percentage points. **The class index is not
#: the scale.** `<20%` spans twenty points, `20%-<30%` ten, `30%-<36%` six, and
#: `36` through `49` one each. A derivative taken per class index is therefore
#: inflated six- to twenty-fold on the wide buckets, and those buckets sit at one
#: end of the order, so the mis-scaled slope correlates with the profile far more
#: than the correct one does. **The first run of this file used the index and its
#: reading of `m'` is void.**
DTI_MID = {"<20%": 10.0, "20%-<30%": 25.0, "30%-<36%": 33.0,
           "50%-60%": 55.0, ">60%": 65.0}


def dti_mid(level: str) -> float:
    if level in DTI_MID:
        return DTI_MID[level]
    return float(level)


def profile_and_slope(m, rank_of, labels=None):
    """`m` and `dm/d(DTI)`, both in label order.

    The measurement-shift alternative predicts a loading proportional to the
    derivative of the class main effect **with respect to DTI**, so the spacing
    has to be DTI and not the class index. Taking it per index also collapses the
    separability the test depends on: per index `|corr(m, m')| = 0.760`
    (`VIF 2.37`), per DTI `0.285` (`VIF 1.09`). **The wrong scale did not merely
    bias the answer, it removed the power to give one.**

    `labels=None` falls back to the index spacing, kept so the superseded reading
    stays computable rather than being erased.
    """
    order = sorted(range(len(m)), key=lambda i: rank_of[i])
    k = len(order)
    if labels is None:
        x = [float(t) for t in range(k)]
    else:
        x = [dti_mid(labels[i]) for i in order]
    slope = np.zeros(k)
    for t in range(k):
        lo, hi = max(t - 1, 0), min(t + 1, k - 1)
        span = x[hi] - x[lo]
        slope[t] = (m[order[hi]] - m[order[lo]]) / span if span > 0 else 0.0
    out = np.zeros(k)
    for t, i in enumerate(order):
        out[i] = slope[t]
    return np.asarray(m, dtype=np.float64), out


def profile_statistic(v, m, mp, drop_j):
    """`|corr|` of the loading against the profile and against its slope.

    Reported with the dominant coordinate dropped as well as whole, because that
    coordinate carries most of the loading's variance and would decide both
    correlations on its own.
    """
    keep = [i for i in range(len(v)) if i != drop_j]
    return (abs_corr(v, m), abs_corr(v, mp),
            abs_corr([v[i] for i in keep], [m[i] for i in keep]),
            abs_corr([v[i] for i in keep], [mp[i] for i in keep]))


def restrict_and_recentre(g0, g1, present2, cols):
    """The balanced arm: keep only cells where **every** class in `cols` is usable.

    B7-16's first run estimated each entry of `Stilde` on the cells where that
    **pair** was usable, and the usable share runs from 0.127 to 0.981 across
    classes. So every entry sat on a different subpopulation of cells, and a
    contrast direction could in principle be a picture of which cells each class
    contributed rather than of the classes. **This removes that freedom**: one
    cell set, shared by the whole matrix.

    The class effect has to be re-centred on the restricted set. The centring in
    the main run zeroed each class's mean over **all** its cells; over a subset
    the means are not zero, and a matrix of `E[g_a] E[g_b]` is a rank-one outer
    product that would arrive looking exactly like a spread direction. Each fold
    is re-centred with its own mean, so the folds stay independent. **The means
    before re-centring are printed**, because their size is the size of the
    problem this guards against.
    """
    cols = np.asarray(cols)
    rows = present2[:, cols].all(axis=1)
    p = np.zeros_like(present2)
    if rows.any():
        p[np.ix_(rows, cols)] = True
    a0, a1 = g0.copy(), g1.copy()
    pre = {}
    for a in cols:
        pre[int(a)] = (float(a0[rows, a].mean()), float(a1[rows, a].mean()))
    # **Both margins, not just the columns.** The first version subtracted class
    # means and left the row means alone, and the row means over `cols` are not
    # zero: the original centring zeroed the **count-weighted** row mean over all
    # nineteen classes, and this block asks for the **unweighted** one over
    # seventeen. What is left over enters `Stilde` as an all-ones component, which
    # is the same shape of contamination the class means would have produced. The
    # function guarded one margin and not the other.
    #
    # `rows x cols` is a **complete** block by construction, since `rows` is the
    # set of cells where every class in `cols` is usable. On a complete block the
    # two centrings commute and one pass of each is exact, so no iteration is
    # needed and none is done.
    #
    # **Unweighted, and that is a choice worth naming**: `cross_second_moment`
    # averages over cells without weights, so the centring is matched to the
    # moment it feeds. The library's `alternating_centre` is count-weighted, which
    # is a mismatch it inherited; changing that would move the unbalanced arms and
    # is not done here.
    for arr in (a0, a1):
        blk = arr[np.ix_(np.flatnonzero(rows), cols)]
        blk = blk - blk.mean(axis=1, keepdims=True)
        blk = blk - blk.mean(axis=0, keepdims=True)
        arr[np.ix_(np.flatnonzero(rows), cols)] = blk
    return a0, a1, p, rows, pre


def depth_table(table, levels):
    """Per class: how many present entries hold two or more loans."""
    rows = []
    for a in range(table.counts.shape[1]):
        present = table.present[:, a]
        c = table.counts[present, a]
        n_entries = int(present.sum())
        n_two = int((c >= 2).sum())
        rows.append({
            "level": levels[a],
            "entries": n_entries,
            "entries_ge_2": n_two,
            "usable_share": (n_two / n_entries) if n_entries else 0.0,
            "loans": float(c.sum()),
            "loans_per_entry": float(c.sum() / n_entries) if n_entries else 0.0,
            "loans_in_usable": float(c[c >= 2].sum()),
        })
    return rows


def cmd_depth() -> int:
    print("B7-16 gate: entries holding two or more loans, class by class.")
    print("**Nothing is estimated here.** This decides which classes the "
          "cross-fold estimator can carry at all.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = design["class_levels"]
    print("  class codes and their level names (§3.21 guard):")
    for code, names in sorted(describe_partition(classes, classes, lv).items()):
        print(f"    {code:>3}  {names}")
    table = cell_class_table(cells, classes, np.asarray(values, dtype=np.float64),
                             n_cells, n_classes)
    rows = depth_table(table, lv)
    order = sorted(range(n_classes), key=lambda i: rows[i]["usable_share"])
    print(f"\n    {'level':<12} {'entries':>9} {'>=2 loans':>10} {'usable':>8} "
          f"{'n/entry':>8} {'loan share kept':>16}")
    for i in order:
        r = rows[i]
        print(f"    {r['level']:<12} {r['entries']:>9d} {r['entries_ge_2']:>10d} "
              f"{r['usable_share']:>8.3f} {r['loans_per_entry']:>8.2f} "
              f"{r['loans_in_usable'] / max(r['loans'], 1.0):>16.3f}")
    print("\n  Read: a class whose usable share is small contributes few cells to "
          "`Stilde`,\n  so its row is estimated on that many cells and no more. "
          "The retirement list,\n  if any, is decided from this table and printed "
          "beside the spectrum.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_crossfold_depth.json"
    out.write_text(json.dumps(
        {"stage": "B7", "step": "crossfold_depth", "n_cells": n_cells,
         "n_classes": n_classes, "n_loans": int(np.asarray(values).size),
         "classes": rows}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_run(draws: int, balanced: bool = False) -> int:
    print(f"B7-16: cross-fold second moment, {draws} null draws.\n")
    cells, classes, values, design = build_design()
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    lv = design["class_levels"]
    values = np.asarray(values, dtype=np.float64)
    print("  class codes and their level names (§3.21 guard):")
    for code, names in sorted(describe_partition(classes, classes, lv).items()):
        print(f"    {code:>3}  {names}")

    table = cell_class_table(cells, classes, values, n_cells, n_classes)
    naive = alternating_centre(table)
    g_chk, _cell_eff, class_eff, _it, _res = centre_with_effects(table)
    chk = float(np.abs(g_chk - naive.gamma).max())
    print(f"  centring self-check: second copy agrees with the library to {chk:.3e}")
    s_naive, _ = pairwise_second_moment(naive.gamma, table.present)
    eig_naive = np.linalg.eigvalsh(s_naive)[::-1]

    fold = entry_folds(cells, classes, n_classes,
                       np.random.default_rng(SEED_FOLD))
    m0, m1 = fold == 0, fold == 1
    t0 = cell_class_table(cells[m0], classes[m0], values[m0], n_cells, n_classes)
    t1 = cell_class_table(cells[m1], classes[m1], values[m1], n_cells, n_classes)
    c0, c1 = alternating_centre(t0), alternating_centre(t1)
    present2 = t0.present & t1.present

    print(f"  folds {int(m0.sum()):,} / {int(m1.sum()):,} loans; "
          f"centring converged {c0.converged} / {c1.converged} "
          f"({c0.iterations} / {c1.iterations} iterations)")
    print(f"  entries usable in both folds {int(present2.sum()):,} of "
          f"{int(table.present.sum()):,} "
          f"({present2.sum() / table.present.sum():.4f})")

    s, cooccur = cross_second_moment(c0.gamma, c1.gamma, present2)
    # **The three-way comparison, because two of them are not the same data.**
    # The naive spectrum above is computed on all 4,485,519 entries and `Stilde`
    # on the 2,969,372 that hold two or more loans, and the entries left out are
    # exactly the noisiest ones. Quoting `1.4674` against `0.4207` therefore mixes
    # an estimator change with a domain change. The middle row holds the domain
    # fixed and changes only the estimator, and it is the one the reading needs.
    s_naive_r, _ = pairwise_second_moment(naive.gamma, present2)
    eig_naive_r = np.linalg.eigvalsh(s_naive_r)[::-1]
    rows = depth_table(table, lv)
    thin = sorted(range(n_classes), key=lambda i: rows[i]["loans_per_entry"])[:2]
    keep = np.array([i for i in range(n_classes) if i not in thin])

    rng = np.random.default_rng(SEED_NULL)
    arms = {}
    plan = [("all_%d" % n_classes, None, False), ("drop_thinnest_2", keep, False)]
    if balanced:
        plan += [("all_%d_balanced" % n_classes, np.arange(n_classes), True),
                 ("drop_thinnest_2_balanced", keep, True)]
    for name, sel, bal in plan:
        g0u, g1u, pu = c0.gamma, c1.gamma, present2
        if bal:
            g0u, g1u, pu, rows_ok, pre = restrict_and_recentre(
                c0.gamma, c1.gamma, present2, sel)
            worst = max(max(abs(x), abs(y)) for x, y in pre.values())
            print(f"\n  [balanced] {name}: cells with every class usable "
                  f"{int(rows_ok.sum()):,} of {n_cells:,}; "
                  f"largest class mean before re-centring {worst:.3e}")
            if rows_ok.sum() < 2:
                print("  too few cells for this arm, skipped")
                continue
            sub = cross_second_moment(g0u, g1u, pu)[0][np.ix_(sel, sel)]
        else:
            sub = s if sel is None else s[np.ix_(sel, sel)]
        vals, vecs = np.linalg.eigh(sub)
        vals = vals[::-1]
        vecs = vecs[:, ::-1]
        labels = lv if sel is None else [lv[i] for i in sel]
        missing = [l for l in labels if l not in DTI_ORDER]
        if missing:
            print(f"  !! labels outside DTI_ORDER, ordering not read: {missing}")
        rank_of = [DTI_ORDER.index(l) if l in DTI_ORDER else 999 for l in labels]
        tau_obs, drop_j = ordering_statistic(vecs[:, 0], rank_of)
        m_arm = class_eff if sel is None else class_eff[sel]
        prof, slope = profile_and_slope(m_arm, rank_of, labels)
        _p_idx, slope_idx = profile_and_slope(m_arm, rank_of)
        sep = abs_corr(prof, slope)
        po = profile_statistic(vecs[:, 0], prof, slope, drop_j)
        nl1, nl2, ntau, nprof = [], [], [], []
        for _ in range(draws):
            nv, nvec = null_spectrum(g0u, g1u, pu, rng, keep=sel)
            nl1.append(float(nv[0]))
            # `lambda_2` was computed by every draw of the first run and thrown
            # away, because this loop was written around `lambda_1` before the
            # ordering statistic existed and nobody came back. **That is an
            # oversight, not a decision**: section 8's first row says "several
            # eigenvalues", so the second one was always part of the reading.
            nl2.append(float(nv[1]) if nv.size > 1 else float("nan"))
            t, dj = ordering_statistic(nvec[:, 0], rank_of)
            ntau.append(t)
            nprof.append(profile_statistic(nvec[:, 0], prof, slope, dj))
        draws_l1 = np.array(nl1)
        draws_l2 = np.array(nl2)
        draws_tau = np.array(ntau)
        draws_prof = np.array(nprof)
        mu, sd = float(draws_l1.mean()), float(draws_l1.std(ddof=1))
        z = (float(vals[0]) - mu) / sd if sd > 0 else float("nan")
        sd_relerr = (1.0 / np.sqrt(2.0 * (draws - 1))
                     if draws > 1 else float("inf"))
        diag = np.diag(sub)
        print(f"\n  === arm {name} ({sub.shape[0]} classes) ===")
        print("  spectrum (all of it, negatives included):")
        print("    " + ", ".join(f"{v:+.4f}" for v in vals))
        print(f"  max diagonal entry {diag.max():+.4f} on "
              f"{labels[int(np.argmax(diag))]}; "
              f"negative eigenvalues {int((vals < 0).sum())} of {vals.size}")
        print(f"  null (M diagonal, {draws} draws): mean {mu:+.4f}, sd {sd:.4f} "
              f"(sd's own relative error {sd_relerr:.2f})")
        print(f"  observed lambda_1 {vals[0]:+.4f}, margin over the null "
              f"**z = {z:+.2f}**")
        if vals.size < 2:
            print("  one class in this arm, so there is no lambda_2 to read")
            arms[name] = {"labels": labels,
                          "eigenvalues": [float(v) for v in vals]}
            continue
        mu2 = float(np.nanmean(draws_l2))
        sd2 = float(np.nanstd(draws_l2, ddof=1))
        z2 = (float(vals[1]) - mu2) / sd2 if sd2 > 0 else float("nan")
        dsort = np.sort(diag)[::-1]
        print(f"  observed lambda_2 {vals[1]:+.4f} against second-largest "
              f"diagonal {dsort[1]:+.4f}; null {mu2:+.4f} +- {sd2:.4f}   "
              f"**z = {z2:+.2f}**")
        tmu, tsd = float(draws_tau.mean()), float(draws_tau.std(ddof=1))
        tz = (tau_obs - tmu) / tsd if tsd > 0 else float("nan")
        diagpart = float(sum(vecs[i, 0] ** 2 * diag[i] for i in range(sub.shape[0])))
        k_arm = sub.shape[0]
        all_ones = float(sub.sum() / k_arm)
        v1_ones = float(vecs[:, 0].sum() / np.sqrt(k_arm))
        print(f"  all-ones component: 1'S1/k = {all_ones:+.5f}; v1's projection "
              f"on it {v1_ones:+.4f} (a pure all-ones direction would give 1.0)")
        print(f"  lambda_1 splits: diagonal {diagpart:+.5f}, off-diagonal "
              f"{float(vals[0]) - diagpart:+.5f} "
              f"({100 * (float(vals[0]) - diagpart) / float(vals[0]):.1f}% off)")
        print(f"  ordering |tau| of v1 along the class scale, largest coordinate "
              f"({labels[drop_j]}) dropped:")
        print(f"    observed {tau_obs:.3f}   null {tmu:.3f} +- {tsd:.3f}   "
              f"**z = {tz:+.2f}**")
        pm, ps = draws_prof.mean(axis=0), draws_prof.std(axis=0, ddof=1)
        pz = [(po[k] - pm[k]) / ps[k] if ps[k] > 0 else float("nan") for k in range(4)]
        sep_idx = abs_corr(prof, slope_idx)
        print(f"  [superseded] per class index the separability was "
              f"{sep_idx:.3f}; this run uses the DTI scale")
        print(f"  class profile m(a) vs its slope m'(a): |corr| = {sep:.3f} "
              f"**this is the separability of the next two lines; near 1 means "
              f"the test cannot tell them apart**")
        print(f"    |corr(v1, m)|   whole {po[0]:.3f} (z {pz[0]:+.2f})   "
              f"drop {labels[drop_j]} {po[2]:.3f} (z {pz[2]:+.2f})")
        print(f"    |corr(v1, m')|  whole {po[1]:.3f} (z {pz[1]:+.2f})   "
              f"drop {labels[drop_j]} {po[3]:.3f} (z {pz[3]:+.2f})")
        print("    m(a) by the class scale: "
              + "  ".join(f"{labels[i]}:{prof[i]:+.4f}"
                          for i in sorted(range(sub.shape[0]),
                                          key=lambda i: rank_of[i])))
        ordered = sorted(range(sub.shape[0]), key=lambda i: rank_of[i])
        print("  v1 by the class scale, low to high:")
        print("    " + "  ".join(f"{labels[i]}:{vecs[i, 0]:+.3f}" for i in ordered))
        print("  leading eigenvector loadings:")
        top = np.argsort(-np.abs(vecs[:, 0]))[:5]
        print("    " + ", ".join(f"{labels[i]} {vecs[i, 0]:+.4f}" for i in top))
        print("  second eigenvector loadings:")
        top2 = np.argsort(-np.abs(vecs[:, 1]))[:5]
        print("    " + ", ".join(f"{labels[i]} {vecs[i, 1]:+.4f}" for i in top2))
        arms[name] = {
            "labels": labels,
            "eigenvalues": [float(v) for v in vals],
            "diag": [float(v) for v in diag],
            "max_diag_level": labels[int(np.argmax(diag))],
            "n_negative": int((vals < 0).sum()),
            "null_mean": mu, "null_sd": sd, "null_draws": draws,
            "lambda2_null_mean": mu2, "lambda2_null_sd": sd2, "lambda2_z": float(z2),
            "second_largest_diag": float(dsort[1]),
            "null_sd_relative_error": float(sd_relerr),
            "z": float(z),
            "diag_part_of_lambda1": diagpart,
            "all_ones_component": all_ones, "v1_on_all_ones": v1_ones,
            "off_diag_part_of_lambda1": float(vals[0]) - diagpart,
            "class_profile": [float(x) for x in prof],
            "class_slope": [float(x) for x in slope],
            "profile_slope_separability": float(sep),
            "profile_slope_separability_by_index_superseded": float(sep_idx),
            "class_slope_by_index_superseded": [float(x) for x in slope_idx],
            "corr_v1_profile": float(po[0]), "corr_v1_slope": float(po[1]),
            "corr_v1_profile_dropped": float(po[2]),
            "corr_v1_slope_dropped": float(po[3]),
            "corr_z": [float(x) for x in pz],
            "tau_observed": float(tau_obs), "tau_dropped_level": labels[drop_j],
            "tau_null_mean": tmu, "tau_null_sd": tsd, "tau_z": float(tz),
            "balanced": bool(bal),
            "cells_used": int(rows_ok.sum()) if bal else None,
            "v1": [float(x) for x in vecs[:, 0]],
            "v2": [float(x) for x in vecs[:, 1]],
        }

    print("\n  Three spectra, and only the last two are on the same entries:")
    print(f"    naive, all {int(table.present.sum()):,} entries        "
          + ", ".join(f"{v:+.4f}" for v in eig_naive[:5]))
    print(f"    naive, the {int(present2.sum()):,} usable entries  "
          + ", ".join(f"{v:+.4f}" for v in eig_naive_r[:5]))
    print("    cross-fold, the same entries          "
          + ", ".join(f"{v:+.4f}" for v in np.linalg.eigvalsh(s)[::-1][:5]))
    print("  **Row 1 to row 2 is the domain. Row 2 to row 3 is the estimator.**")
    print("\n  per class, the same three, and the two ratios:")
    print(f"    {'level':<12} {'naive all':>10} {'naive same':>11} "
          f"{'crossfold':>10} {'domain x':>9} {'estimator x':>12}")
    dn, dr, dc = np.diag(s_naive), np.diag(s_naive_r), np.diag(s)
    for a in sorted(range(n_classes), key=lambda i: -dn[i]):
        dom = dn[a] / dr[a] if dr[a] else float("nan")
        est = dr[a] / dc[a] if dc[a] else float("nan")
        print(f"    {lv[a]:<12} {dn[a]:>10.5f} {dr[a]:>11.5f} {dc[a]:>10.5f} "
              f"{dom:>9.2f} {est:>12.2f}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_crossfold.json"
    out.write_text(json.dumps(
        {"stage": "B7", "step": "crossfold", "n_cells": n_cells,
         "n_classes": n_classes, "n_loans": int(values.size),
         "seed_fold": SEED_FOLD, "seed_null": SEED_NULL,
         "fold_sizes": [int(m0.sum()), int(m1.sum())],
         "centring_converged": [bool(c0.converged), bool(c1.converged)],
         "entries_usable": int(present2.sum()),
         "entries_total": int(table.present.sum()),
         "naive_eigenvalues": [float(v) for v in eig_naive],
         "naive_eigenvalues_same_entries": [float(v) for v in eig_naive_r],
         "naive_diag_all_entries": [float(v) for v in np.diag(s_naive)],
         "naive_diag_same_entries": [float(v) for v in np.diag(s_naive_r)],
         "dropped_thinnest": [lv[i] for i in thin],
         "arms": arms}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--depth", action="store_true",
                    help="the gate: entries with two or more loans, per class")
    ap.add_argument("--run", action="store_true", help="the estimator")
    ap.add_argument("--draws", type=int, default=DRAWS_DEFAULT)
    ap.add_argument("--balanced", action="store_true",
                    help="add the arms restricted to cells where every class is "
                         "usable, which removes the per-pair cell selection")
    a = ap.parse_args(argv)
    if a.depth:
        return cmd_depth()
    if a.run:
        return cmd_run(a.draws, a.balanced)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
