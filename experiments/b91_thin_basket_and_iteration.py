"""B91: what the irreducibility hypothesis buys, and how much more than the old prices decides.

B85 left two registrations. Both are answered here and both turn out to be about the same
thing: how much of Theorem 14 survives when its hypothesis stops being free.

**The hypothesis is not free once the basket has zeros.** B85's substitutions scale columns
elementwise, so they preserve the zero pattern, and its basket is strictly positive, so
`M' = A' + b l'` is a positive matrix whatever the substitution did. Thin the basket, which is
what a subsistence bundle that does not contain every intermediate good looks like, and allow a
substitution to knock entries of `A` to zero, and `M'` is genuinely reducible on a large minority
of draws.

**What the hypothesis buys is the price vector, and not the direction of the rate.** On the
reducible draws the forward implication holds without exception, while the left Perron vector stops
being guaranteed strictly positive: most reducible draws still carry a positive vector and a
minority do not. **Which goods can price at zero depends on where the dominant block sits**, since
a block that feeds a dominant block downstream still prices positively while one the dominant block
does not reach need not. **The rate comparison is untouched either way**, because it compares
Perron roots and does not need the vector.

**One power iteration does not decide the undecided cell, and the curve is the answer.** The
Collatz-Wielandt bracket at the prices in force cannot decide, and for a structural reason: an
unchanged column returns exactly `lambda`, so the bracket contains it. Iterating moves the
unchanged columns off `lambda` and the bracket tightens. **It is never wrong at any iteration**,
which is Collatz-Wielandt and not a reading, so the iteration is a safe early exit rather than an
approximation.

B69's generator, Perron solver, basket and augmented matrix and B85's cell discriminant are
imported rather than rewritten.

Run:
    python experiments/b91_thin_basket_and_iteration.py
    python experiments/b91_thin_basket_and_iteration.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import b69_okishio as B69                                  # noqa: E402
import b85_simultaneous as B85                             # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b91_thin_basket_and_iteration.json"

SEED = 91
N_THIN = 1200                  # draws for the thin-basket half
N_ITER_SYSTEMS = 30            # systems fed to B85's own generator for the iteration half
KNOCKOUT = 0.6                 # chance an entry of a substituted column is set to zero
MAX_ITER = 60
TOL = B85.TOL


def thin(rng, b, n):
    """A subsistence bundle that does not contain every intermediate good."""
    out = np.zeros(n)
    keep = rng.choice(n, size=max(1, n // 3), replace=False)
    out[keep] = np.asarray(b)[keep]
    return out


def knock_out(rng, a, l, ks):
    """A substitution that changes the zero pattern, which B85's deliberately does not."""
    a2, l2 = a.copy(), l.copy()
    n = a.shape[0]
    for k in ks:
        mask = rng.random(n) < KNOCKOUT
        a2[:, k] = np.where(mask, 0.0, a[:, k] * rng.uniform(*B69.SUB_SPREAD, n))
        l2[k] = l[k] * float(rng.uniform(*B69.SUB_SPREAD))
    return a2, l2


def thin_draws(rng, n_draws):
    out = []
    for _ in range(n_draws):
        a, l = B69.random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = B69.labour_values(a, l)
        if v.min() <= 0.0:
            continue
        b = thin(rng, B69.basket_of_value(rng, v, B69.VALUE_OF_BASKET[0]), n)
        if b.sum() <= 0.0:
            continue
        m = B69.augmented(a, l, b)
        before_irreducible = B69.irreducible(m)
        # prices are the LEFT Perron vector, which is `perron(m.T)`. Taking `perron(m)` gives
        # the right one, and B91-3's forward clause is what caught that here
        lam, _right = B69.perron(m)
        _lam_t, p = B69.perron(m.T)
        if p is None or p.min() <= 0.0 or not (0.0 < lam < 1.0):
            continue
        ks = sorted(rng.choice(n, size=min(2, n), replace=False).tolist())
        a2, l2 = knock_out(rng, a, l, ks)
        m2 = B69.augmented(a2, l2, b)
        lam2, _right2 = B69.perron(m2)
        _lam2_t, p2 = B69.perron(m2.T)
        if lam2 is None or lam2 <= 0.0:
            continue
        ratios = (p @ m2) / p
        changed = [float(ratios[k]) for k in ks]
        out.append({
            "n": n, "ks": ks,
            # the residual of the vector this draw actually used as prices. Storing it here
            # rather than recomputing a fresh one is the point: a criterion that builds its
            # own vector cannot catch a draw that built a different one
            "left_residual": float(np.abs(p @ m - lam * p).max() / np.abs(p).max()),
            "before_irreducible": bool(before_irreducible),
            "after_irreducible": bool(B69.irreducible(m2)),
            "prices_strictly_positive": bool(p2 is not None and p2.min() > 1e-12),
            "zeros_added": int(((a > 0.0) & (a2 == 0.0)).sum()),
            "lam": float(lam), "lam2": float(lam2),
            "bracket_changed": [min(changed), max(changed)],
        })
    return out


def iterate_to_decide(p, m2, lam, max_iter=MAX_ITER):
    """Collatz-Wielandt at successive iterates. Returns (verdict, iterations, brackets)."""
    brackets = []
    p = np.asarray(p, dtype=float).copy()
    for t in range(max_iter + 1):
        r = (p @ m2) / p
        lo, hi = float(r.min()), float(r.max())
        brackets.append((lo, hi))
        if hi < lam - TOL:
            return "below", t, brackets
        if lo > lam + TOL:
            return "above", t, brackets
        p = p @ m2
        s = p.max()
        if s <= 0.0:
            break
        p = p / s
    return None, None, brackets


def iter_draws(rng, n_systems):
    """B85's own draws, so the straddle cell is the one B85 reported."""
    sample = B85.draws(rng, n_systems)
    out = []
    for s in sample:
        cell = B85.cell_of(s)
        a, l, b = np.asarray(s["a"]), np.asarray(s["l"]), np.asarray(s["b"])
        m2 = B69.augmented(np.asarray(s["a2"]), np.asarray(s["l2"]), b)
        _lam, p = B69.perron(B69.augmented(a, l, b).T)      # prices: the LEFT Perron vector
        if p is None or p.min() <= 0.0:
            continue
        verdict, iters, brackets = iterate_to_decide(p, m2, s["lam"])
        truth = ("below" if s["lam2"] < s["lam"] - 1e-12 else
                 "above" if s["lam2"] > s["lam"] + 1e-12 else "equal")
        ev = np.sort(np.abs(np.linalg.eigvals(m2)))[::-1]
        out.append({"cell": cell, "verdict": verdict, "iterations": iters, "truth": truth,
                    "lam": s["lam"], "lam2": s["lam2"],
                    "relative_move": abs(s["lam2"] - s["lam"]) / s["lam"],
                    "second_ratio": float(ev[1] / ev[0]) if len(ev) > 1 and ev[0] > 0
                    else float("nan"),
                    "brackets": brackets[:3]})
    return out


def draws(rng, n_thin=N_THIN, n_iter=N_ITER_SYSTEMS):
    return {"thin": thin_draws(rng, n_thin), "iter": iter_draws(rng, n_iter)}


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B91-1: B85's readings come back, and the vector used as prices is a left eigenvector."""
    rng = np.random.default_rng(85)
    ref = B85.draws(rng, 8)
    cells = {}
    for s in ref:
        cells[B85.cell_of(s)] = cells.get(B85.cell_of(s), 0) + 1
    # B85's own load-bearing facts, re-read here from its own generator
    positive_basket = all(np.asarray(s["b"]).min() > 0.0 for s in ref)
    pattern_kept = all(((np.asarray(s["a"]) > 0.0) == (np.asarray(s["a2"]) > 0.0)).all()
                       for s in ref)
    irreducible = all(B69.irreducible(B69.augmented(np.asarray(s["a2"]), np.asarray(s["l2"]),
                                                    np.asarray(s["b"]))) for s in ref)
    # the vector this station calls prices has to be a LEFT eigenvector. Taking `perron(m)`
    # gives the right one, and that fault reached the full run before it reached a fixture:
    # B91-3's forward clause caught it on one draw in about five hundred, which is too rare
    # for a self-test to rely on. This clause catches it on the first draw
    used = [s["left_residual"] for s in sample["thin"]]
    left_gap = max(used) if used else float("inf")
    left_ok = bool(used) and left_gap < 1e-9
    ok = (bool(ref) and positive_basket and pattern_kept and irreducible and len(cells) == 3
          and left_ok)
    detail = (f"the vector this station calls prices is a left eigenvector of `M` to "
              f"{left_gap:.2e} relative, checked because the right one is what "
              f"`perron(m)` returns and the two are not interchangeable. "
              f"B85's own generator, run here, gives a strictly positive basket on every draw, "
              f"a substitution that leaves the zero pattern of `A` exactly where it was, and an "
              f"irreducible `M'` on all {len(ref)} draws, with all three cells occupied: "
              + ", ".join(f"{k} {v}" for k, v in sorted(cells.items()))
              + ". **Those three facts are what this station removes one at a time**, so they "
                "are read from B85's generator rather than asserted about it")
    return ok, detail, {"reference_draws": len(ref), "cells": cells,
                        "positive_basket": positive_basket, "zero_pattern_kept": pattern_kept,
                        "all_irreducible": irreducible, "left_eigenvector_gap": left_gap}


def crit_reducible(sample):
    """B91-2: thin the basket and change the zero pattern, and the hypothesis stops being free."""
    thin = sample["thin"]
    before = sum(1 for s in thin if s["before_irreducible"])
    after = sum(1 for s in thin if s["after_irreducible"])
    zeros = [s["zeros_added"] for s in thin]
    med_zeros = int(np.median(zeros)) if zeros else 0
    ok = bool(thin) and before == len(thin) and after < len(thin)
    detail = (f"with a subsistence bundle that does not contain every intermediate good and a "
              f"substitution allowed to set entries of `A` to zero, `M'` is reducible on "
              f"{len(thin) - after} of {len(thin)} draws. **Before the substitution it is "
              f"irreducible on {before} of {len(thin)}**, so what breaks the hypothesis is the "
              f"substitution and what stops the basket from repairing it is the zeros in the "
              f"bundle. A median of {med_zeros} entries of `A` are newly zero. "
              f"**B85's hypothesis was supplied by its generator**: a strictly positive basket "
              f"against a strictly positive labour vector makes `b l'` positive and `M'` positive "
              f"whatever the substitution did")
    return ok, detail, {"draws": len(thin), "irreducible_before": before,
                        "irreducible_after": after,
                        "median_zeros_added": med_zeros}


def crit_what_it_buys(sample):
    """B91-3: the rate survives reducibility and the price vector does not."""
    red = [s for s in sample["thin"] if not s["after_irreducible"]]
    irr = [s for s in sample["thin"] if s["after_irreducible"]]
    def forward(rows):
        met = [s for s in rows if s["bracket_changed"][1] < s["lam"] - TOL]
        held = [s for s in met if s["lam2"] < s["lam"] - 1e-12]
        return len(met), len(held)
    met_r, held_r = forward(red)
    met_i, held_i = forward(irr)
    pos_r = sum(1 for s in red if s["prices_strictly_positive"])
    pos_i = sum(1 for s in irr if s["prices_strictly_positive"])
    ok = (bool(red) and bool(irr) and met_r > 0 and held_r == met_r and held_i == met_i
          and pos_r < len(red) and pos_i == len(irr))
    detail = (f"on the {len(red)} reducible draws the forward implication holds without "
              f"exception: every changed column cheaper at the prices in force on {met_r} of "
              f"them, and the Perron root falls on {held_r} of those {met_r}. **The price "
              f"vector is what does not survive**: the left Perron vector is strictly positive "
              f"on {pos_r} of {len(red)} reducible draws against {pos_i} of {len(irr)} "
              f"irreducible ones. **So the hypothesis buys the prices and not the direction of "
              f"the rate**: irreducibility guarantees a strictly positive price vector and "
              f"reducibility does not, which {len(red) - pos_r} of the reducible draws show. "
              f"**It does not follow that everything outside a dominant block prices at zero**, "
              f"and {pos_r} of these draws are reducible with every price positive: a block the "
              f"dominant one feeds still prices off it, and a zero appears where the dominant "
              f"block is not reached from. **A comparison of Perron roots needs none of this.** "
              f"Both halves are counted on the same draws, so the contrast is not between two "
              f"samples")
    return ok, detail, {"reducible": len(red), "irreducible": len(irr),
                        "forward_met_reducible": met_r, "forward_held_reducible": held_r,
                        "forward_met_irreducible": met_i, "forward_held_irreducible": held_i,
                        "positive_prices_reducible": pos_r,
                        "positive_prices_irreducible": pos_i}


def crit_curve(sample):
    """B91-4: how much more than the prices in force decides the undecided cell."""
    rows = [s for s in sample["iter"] if s["cell"] == "straddle"]
    solved = [s for s in rows if s["iterations"] is not None]
    at = {}
    for s in solved:
        at[s["iterations"]] = at.get(s["iterations"], 0) + 1
    cum, run = {}, 0
    for t in sorted(at):
        run += at[t]
        cum[t] = run
    # No line is drawn on how much any one iteration buys. That is the reading, and rule 11
    # says a reading is an object printed with a stated way of reading it, not a threshold.
    # What is asserted is that the cell is exhausted and that the curve has somewhere to go.
    ok = bool(rows) and len(solved) == len(rows) and max(cum, default=0) > 1
    denom = max(1, len(rows))
    shown = "; ".join(f"by {t}: {cum[t]} ({cum[t] / denom:.1%})"
                      for t in sorted(cum) if t in (0, 1, 2, 3, 5, 10, 20, 40))
    worst = max(cum) if cum else 0
    detail = (f"of {len(rows)} draws the prices in force leave undecided, **one power iteration "
              f"decides {cum.get(1, 0)} ({cum.get(1, 0) / denom:.1%})**, and all "
              f"{len(solved)} are decided within {worst} iterations. Cumulative: {shown}. "
              f"**So the registration's guess is half right**: one iteration is not enough on "
              f"its own, and a handful is. **The reason the old prices decide nothing at all "
              f"is structural rather than numerical**: an unchanged column returns exactly "
              f"`lambda`, so the bracket contains it until iteration moves those columns off "
              f"it. **No threshold is placed on the curve**, which is the reading itself")
    return ok, detail, {"straddling": len(rows), "solved": len(solved),
                        "cumulative": {str(k): v for k, v in cum.items()},
                        "worst_case_iterations": worst, "max_iter": MAX_ITER}


def crit_never_wrong(sample):
    """B91-5: an implementation check. Collatz-Wielandt cannot be wrong."""
    rows = [s for s in sample["iter"]
            if s["verdict"] is not None and s["truth"] != "equal"]
    wrong = [s for s in rows if s["verdict"] != s["truth"]]
    ok = bool(rows) and not wrong
    straddles = [s for s in sample["iter"] if s["cell"] == "straddle"]
    at_zero = sum(1 for s in straddles if s["iterations"] == 0)
    ok = ok and at_zero == 0
    detail = (f"the bracket's verdict agrees with the recomputed Perron root on "
              f"{len(rows) - len(wrong)} of {len(rows)} decided draws, and it decides "
              f"{at_zero} of {len(straddles)} straddling draws at zero iterations. **Both are "
              f"implementation checks and not readings** (`D35` second clause). The second is "
              f"a theorem about the cell's own definition: an unchanged column returns exactly "
              f"`lambda`, so the full bracket contains `lambda` at the prices in force, and "
              f"where every column changed the full bracket is the changed one, which straddles "
              f"by definition. **This is an "
              f"implementation check and not a reading** (`D35` second clause): "
              f"`min_j (pM')_j / p_j <= lambda' <= max_j (pM')_j / p_j` holds at every strictly "
              f"positive `p`, so a bracket entirely below `lambda` puts `lambda'` below it and "
              f"a bracket entirely above puts it above, at any iteration. **What that makes the "
              f"iteration is a safe early exit rather than an approximation**: stopping early "
              f"costs a verdict, never a wrong one")
    return ok, detail, {"decided": len(rows), "wrong": len(wrong),
                        "straddling": len(straddles), "decided_at_zero": at_zero}


def crit_what_governs(sample):
    """B91-6: what sets the number of iterations, measured rather than asserted."""
    rows = [s for s in sample["iter"]
            if s["cell"] == "straddle" and s["iterations"] is not None
            and np.isfinite(s["second_ratio"])]
    if len(rows) < 20:
        return False, f"only {len(rows)} straddling draws were decided", {"rows": len(rows)}
    it = np.array([s["iterations"] for s in rows], dtype=float)
    move = np.array([s["relative_move"] for s in rows], dtype=float)
    gap = np.array([s["second_ratio"] for s in rows], dtype=float)

    def ranks(v):
        """Average ranks, because a double `argsort` breaks ties by position.

        The iteration counts here are small integers and nearly every one of them is tied, so
        ordering tied values by where they happen to sit in the array is not a rank at all.
        """
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v), dtype=float)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            r[order[i:j + 1]] = 0.5 * (i + j) + 1.0
            i = j + 1
        return r

    def spearman(x, y):
        return float(np.corrcoef(ranks(x), ranks(y))[0, 1])

    s_move, s_gap = spearman(it, move), spearman(it, gap)
    tied = int(len(it) - len(set(it.tolist())))
    ok = s_move < -0.2 and s_gap > 0.2
    detail = (f"over {len(rows)} decided straddling draws the iterations needed fall with the "
              f"size of the move in the Perron root, Spearman {s_move:+.3f}, and rise with the "
              f"ratio of the second modulus to the first, Spearman {s_gap:+.3f}, median "
              f"{np.median(it):.0f} iterations, on **average ranks**: {tied} of {len(rows)} "
              f"values share a count with another, so a double `argsort` would be ordering ties "
              f"by position in the array. **Both signs are the ones the mechanism "
              f"predicts and both are read off the draws**: a bracket has further to travel "
              f"when the two roots are close, and it travels more slowly when the second "
              f"eigenvalue is near the first. **Rank correlations rather than a fit**, since "
              f"neither relation is claimed to be linear")
    return ok, detail, {"rows": len(rows), "spearman_move": s_move, "spearman_gap": s_gap,
                        "median_iterations": float(np.median(it))}


def crit_registration():
    """B91-7: the same round writes back to the station that registered both halves."""
    doc = (ROOT / "docs" / "b85_simultaneous.md").read_text(encoding="utf-8")
    named = "b91_thin_basket_and_iteration.md" in doc
    return named, (f"B85's file "
                   f"{'names this station against both registrations it opened' if named else '**does not name this station**'}, "
                   f"so a reader of it finds what its hypothesis was buying and what the "
                   f"undecided cell costs. `D20`"), {"b85_names_b91": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(7)
    sample = draws(rng, 220, 5)
    if len(sample["thin"]) < 80 or len(sample["iter"]) < 80:
        fails.append(f"the fixture drew {len(sample['thin'])} thin and "
                     f"{len(sample['iter'])} iteration rows")

    named = (("B91-1", crit_reduces), ("B91-2", crit_reducible),
             ("B91-3", crit_what_it_buys), ("B91-4", crit_curve),
             ("B91-5", crit_never_wrong), ("B91-6", crit_what_governs))
    empty = {"thin": [], "iter": []}
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:130]}")
        # B91-1 reads B85's generator rather than this station's draws, so an empty sample
        # says nothing about it. Its own probe is the one below
        if name != "B91-1" and fn(empty)[0]:
            fails.append(f"{name} passes on an empty sample")

    # B91-1: a draw whose stored residual says the vector was not a left eigenvector has to
    # be rejected, otherwise that clause only looks load-bearing
    bent_left = {"thin": [dict(s, left_residual=1e-3) for s in sample["thin"]],
                 "iter": sample["iter"]}
    if crit_reduces(bent_left)[0]:
        fails.append("B91-1 passes when the vector used as prices is not a left eigenvector")

    # B91-1's probe: the three facts it reads off B85's generator have to come back false on
    # this station's own construction, which removes all three on purpose
    rng2 = np.random.default_rng(3)
    bad_basket = bad_pattern = bad_irr = 0
    tried = 0
    while tried < 30:
        a, l = B69.random_system(rng2)
        if a is None:
            continue
        n = a.shape[0]
        v = B69.labour_values(a, l)
        if v.min() <= 0.0:
            continue
        b = thin(rng2, B69.basket_of_value(rng2, v, B69.VALUE_OF_BASKET[0]), n)
        if b.sum() <= 0.0:
            continue
        tried += 1
        ks = sorted(rng2.choice(n, size=min(2, n), replace=False).tolist())
        a2, l2 = knock_out(rng2, a, l, ks)
        bad_basket += int(b.min() <= 0.0)
        bad_pattern += int(not ((a > 0.0) == (a2 > 0.0)).all())
        bad_irr += int(not B69.irreducible(B69.augmented(a2, l2, b)))
    if not (bad_basket and bad_pattern and bad_irr):
        fails.append(f"this station's construction does not remove all three of B85's facts: "
                     f"basket {bad_basket}, pattern {bad_pattern}, irreducibility {bad_irr}")

    # B91-2: with the zero pattern preserved the hypothesis is free again, which is B85's
    # setting and has to read as such
    kept = {"thin": [dict(s, after_irreducible=True) for s in sample["thin"]],
            "iter": sample["iter"]}
    if crit_reducible(kept)[0]:
        fails.append("B91-2 passes when no draw is reducible")

    # B91-3: the contrast is between the two halves of one sample, so a fixture in which the
    # reducible draws also have strictly positive prices says the hypothesis buys nothing
    allpos = {"thin": [dict(s, prices_strictly_positive=True) for s in sample["thin"]],
              "iter": sample["iter"]}
    if crit_what_it_buys(allpos)[0]:
        fails.append("B91-3 passes when reducible draws keep strictly positive prices")

    # and a fixture in which the forward implication fails on a reducible draw has to be caught,
    # since that is the half this station reports as surviving
    broken = []
    for s in sample["thin"]:
        if not s["after_irreducible"] and s["bracket_changed"][1] < s["lam"] - TOL:
            broken.append(dict(s, lam2=s["lam"] * 1.5))
        else:
            broken.append(s)
    if crit_what_it_buys({"thin": broken, "iter": sample["iter"]})[0]:
        fails.append("B91-3 passes when the forward implication fails on a reducible draw")

    # B91-4: if one iteration decided most of the cell the registration's hope would be right,
    # and the criterion reports the opposite, so it has to reject that fixture
    quick = {"thin": sample["thin"],
             "iter": [dict(s, iterations=1 if s["iterations"] is not None else None)
                      for s in sample["iter"]]}
    if crit_curve(quick)[0]:
        fails.append("B91-4 passes when one iteration decides the whole cell")

    # B91-5: a verdict that disagreed with the recomputed root would mean the bracket was
    # being read the wrong way round
    flipped = {"thin": sample["thin"],
               "iter": [dict(s, verdict=("above" if s["verdict"] == "below" else "below")
                             if s["verdict"] else None) for s in sample["iter"]]}
    if crit_never_wrong(flipped)[0]:
        fails.append("B91-5 passes when every verdict is the opposite of the truth")

    # B91-6: shuffling the iteration counts against the systems destroys both relations, and
    # the criterion has to notice rather than report whatever correlation turns up
    shuf = list(sample["iter"])
    order = np.random.default_rng(0).permutation(len(shuf))
    scrambled = [dict(s, iterations=shuf[order[i]]["iterations"])
                 for i, s in enumerate(shuf)]
    got6 = crit_what_governs({"thin": sample["thin"], "iter": scrambled})
    if got6[0]:
        fails.append("B91-6 passes on iteration counts shuffled against their systems")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample['thin'])} thin and "
          f"{len(sample['iter'])} iteration rows")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--thin", type=int, default=N_THIN)
    ap.add_argument("--iter-systems", type=int, default=N_ITER_SYSTEMS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.thin, args.iter_systems)
    print(f"{len(sample['thin'])} thin-basket draws, {len(sample['iter'])} iteration draws\n")

    criteria, report = [], {}
    for name, kind, fn in (("B91-1", "known_answer", crit_reduces),
                           ("B91-2", "own_reading", crit_reducible),
                           ("B91-3", "own_reading", crit_what_it_buys),
                           ("B91-4", "own_reading", crit_curve),
                           ("B91-5", "instrument", crit_never_wrong),
                           ("B91-6", "own_reading", crit_what_governs)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B91-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B91-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B91-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B91",
        "config": {"seed": args.seed, "thin_draws": args.thin,
                   "iteration_systems": args.iter_systems, "knockout": KNOCKOUT,
                   "max_iter": MAX_ITER,
                   "imports": "b69_okishio, b85_simultaneous"},
        "report": report,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    print(f"all {len(criteria)} criteria pass; record written" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
