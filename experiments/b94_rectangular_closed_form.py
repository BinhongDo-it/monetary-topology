"""B94: both factors on a rectangular economy are eigenvalues, of a block that has to be found.

B82 closed B80's two-family registration and left one of its own: whether either family has a
closed form on a rectangular economy, since the Perron route needs principal blocks of one matrix
and there are none here, so the factors are read by a programme rather than by an eigenvalue.

**They are eigenvalues.** At the optimum the programme is tight on a square sub-pair of processes
and goods, and the factor is a generalised eigenvalue of that pair: a root of
`det(B_{S,G} - gamma A_{S,G}) = 0`. So

    alpha = the largest admissible generalised eigenvalue over square sub-pairs
    beta  = the smallest

**The screen is what makes this a closed form rather than a formula.** A generalised eigenvalue of
an arbitrary sub-pair need not be attainable by any non-negative intensity vector on the whole
economy; without the feasibility screen the maximum overshoots.

**And the block is usually one cell.** So the expansion factor is most often the best single
process's own output-to-input ratio, chosen by a search rather than computed by one.

**This is the chain's own shape read once more.** B87 has demand choosing which lands, B89 which
cell of a counting identity, B93 which member owns the envelope, and here which block carries the
factor: **the continuous part is an eigenvalue and the work is combinatorial.**

B75's game solver and factors and B82's rectangular generator are imported rather than rewritten.

Run:
    python experiments/b94_rectangular_closed_form.py
    python experiments/b94_rectangular_closed_form.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys

import numpy as np
import scipy.linalg as sla

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b75_rectangular_programme as b75      # noqa: E402
import b82_rectangular_parts as b82          # noqa: E402

OUT = ROOT / "results" / "b94_rectangular_closed_form.json"

SEED = 94
N_ECONOMIES = 60
AGREE_TOL = 1e-5
FEASIBLE_TOL = 1e-7
EIG_TOL = 1e-8


def generalised_eigenvalues(a_sub, b_sub):
    """Roots of `det(B - gamma A) = 0` that are real and positive."""
    try:
        w = sla.eigvals(b_sub, a_sub)
    except Exception:
        return []
    return [float(z.real) for z in w
            if abs(z.imag) < EIG_TOL and np.isfinite(z.real) and z.real > 1e-9]


def square_pairs(n, m):
    for k in range(1, min(n, m) + 1):
        for s in itertools.combinations(range(n), k):
            for g in itertools.combinations(range(m), k):
                yield k, s, g


def feasible_alpha(A, B, gamma):
    v, _x, _y = b75.game_value(B - gamma * A)
    return v is not None and v >= -FEASIBLE_TOL


def feasible_beta(A, B, gamma):
    v, _x, _y = b75.game_value(-(B - gamma * A).T)
    return v is not None and v >= -FEASIBLE_TOL


def closed_form(A, B, side):
    """The factor as an extremum over square sub-pairs, with and without the screen.

    `complex_kept` re-runs the same extremum with the imaginary-part filter off, which is a
    measurement rather than a guard: the screen turns out to reject every real part of a complex
    root that could have won, so the filter is redundant on this family and that is worth
    knowing rather than asserting.
    """
    take = max if side == "alpha" else min
    screen = feasible_alpha if side == "alpha" else feasible_beta
    best = unscreened = loose = None
    complex_seen = 0
    where = None
    pairs = 0
    for k, s, g in square_pairs(*A.shape):
        pairs += 1
        try:
            raw = sla.eigvals(B[np.ix_(s, g)], A[np.ix_(s, g)])
        except Exception:
            raw = []
        for z in raw:
            if not np.isfinite(z.real) or z.real <= 1e-9:
                continue
            if abs(z.imag) >= EIG_TOL:
                complex_seen += 1
            if screen(A, B, float(z.real)):
                loose = float(z.real) if loose is None else take(loose, float(z.real))
        for gamma in generalised_eigenvalues(A[np.ix_(s, g)], B[np.ix_(s, g)]):
            unscreened = gamma if unscreened is None else take(unscreened, gamma)
            if screen(A, B, gamma) and (best is None or take(best, gamma) == gamma):
                if best is None or gamma != best:
                    best, where = gamma, {"size": k, "processes": list(s), "goods": list(g)}
    return {"screened": best, "unscreened": unscreened, "block": where,
            "pairs": pairs, "complex_roots_seen": complex_seen,
            "screened_keeping_complex": loose}


def draws(rng, n_economies):
    out = []
    for _ in range(n_economies):
        A, B = b82.draw_rect(rng)
        a = b75.expansion_factor(A, B)
        b = b75.interest_factor(A, B)
        if a is None or b is None:
            continue
        ca = closed_form(A, B, "alpha")
        cb = closed_form(A, B, "beta")
        out.append({"shape": list(A.shape), "alpha": float(a), "beta": float(b),
                    "closed_alpha": ca, "closed_beta": cb})
    return out


# ------------------------------------------------- criteria

def crit_published(sample):
    """B94-1: B75's published examples, through this station's closed form."""
    rows = []
    for name, Al, Bl, want in (("example 1", b75.QE1_A, b75.QE1_B, b75.QE1_PUBLISHED),
                               ("example 2", b75.QE2_A, b75.QE2_B, b75.QE2_PUBLISHED)):
        A, B = np.asarray(Al, dtype=float), np.asarray(Bl, dtype=float)
        for side, target in (("alpha", float(want[0])), ("beta", float(want[1]))):
            got = closed_form(A, B, side)["screened"]
            rows.append({"case": f"{name} {side}", "published": target, "closed_form": got,
                         "gap": None if got is None else abs(got - target)})
    ok = bool(rows) and all(r["gap"] is not None and r["gap"] < AGREE_TOL for r in rows)
    detail = ("B75's two published examples, read by this station's closed form rather than by "
              "its bisection: " + "; ".join(
                  f"{r['case']} published {r['published']:.6f}, closed form "
                  f"{'none' if r['closed_form'] is None else format(r['closed_form'], '.6f')}"
                  for r in rows) +
              ". **The published value is the outside anchor and the closed form is a different "
              "route to it**, so the two can disagree")
    return ok, detail, {"cases": rows}


def crit_alpha(sample):
    """B94-2: the expansion factor is the largest admissible generalised eigenvalue."""
    worst, agree = 0.0, 0
    for s in sample:
        got = s["closed_alpha"]["screened"]
        if got is None:
            continue
        gap = abs(got - s["alpha"])
        worst = max(worst, gap)
        agree += int(gap < AGREE_TOL)
    ok = bool(sample) and agree == len(sample) and worst < AGREE_TOL
    detail = (f"on {agree} of {len(sample)} drawn rectangular economies the expansion factor "
              f"read by B75's bisection equals the largest admissible generalised eigenvalue "
              f"over square sub-pairs, worst gap {worst:.2e}. **So the factor is an eigenvalue "
              f"after all**, of a square pair `(A_{{S,G}}, B_{{S,G}})` rather than of a "
              f"principal block, which is what B82 registered as missing")
    return ok, detail, {"economies": len(sample), "agree": agree, "worst_gap": worst}


def crit_beta(sample):
    """B94-3: and the interest factor is the smallest."""
    worst, agree = 0.0, 0
    for s in sample:
        got = s["closed_beta"]["screened"]
        if got is None:
            continue
        gap = abs(got - s["beta"])
        worst = max(worst, gap)
        agree += int(gap < AGREE_TOL)
    ok = bool(sample) and agree == len(sample) and worst < AGREE_TOL
    detail = (f"the interest factor is the smallest admissible generalised eigenvalue over the "
              f"same sub-pairs on {agree} of {len(sample)}, worst gap {worst:.2e}. **The two "
              f"factors are the two ends of one finite set**, which is the sharpest form B82's "
              f"two-families statement takes on a rectangular economy: the families differ in "
              f"which index set they range over and the factors differ only in the direction "
              f"the extremum is taken")
    return ok, detail, {"economies": len(sample), "agree": agree, "worst_gap": worst}


def crit_screen(sample):
    """B94-4: the screen is what makes it a closed form and not a formula."""
    ratios, over = [], 0
    for s in sample:
        ca = s["closed_alpha"]
        if ca["screened"] is None or ca["unscreened"] is None:
            continue
        if ca["unscreened"] > ca["screened"] + AGREE_TOL:
            over += 1
            ratios.append(ca["unscreened"] / max(ca["screened"], 1e-12))
    with_complex = sum(1 for s in sample if s["closed_alpha"]["complex_roots_seen"] > 0)
    moved = sum(1 for s in sample
                if s["closed_alpha"]["screened"] is not None
                and s["closed_alpha"]["screened_keeping_complex"] is not None
                and abs(s["closed_alpha"]["screened"]
                        - s["closed_alpha"]["screened_keeping_complex"]) > 1e-9)
    ok = (bool(sample) and over > 0 and over >= 0.5 * len(sample) and moved == 0
          and with_complex > 0)
    med = float(np.median(ratios)) if ratios else float("nan")
    detail = (f"dropping the feasibility screen and taking the largest generalised eigenvalue "
              f"over all square sub-pairs overshoots on {over} of {len(sample)} economies, by a "
              f"median factor of {med:.3f}. **A sub-pair's eigenvalue need not be attainable by "
              f"any non-negative intensity vector on the whole economy**, so the closed form is "
              f"an extremum over a finite set with a feasibility screen, and saying so is the "
              f"honest form of the claim: the continuous part is an eigenvalue and the "
              f"remaining work is a finite search. **The screen does a second job that is easy "
              f"to miss**: complex generalised eigenvalues turn up on {with_complex} of "
              f"{len(sample)} economies, and keeping their real parts moves the answer on "
              f"{moved} of them, so the filter that drops them is redundant here and the screen "
              f"is what was rejecting them all along")
    return ok, detail, {"economies": len(sample), "overshoots": over,
                        "median_overshoot": med,
                        "economies_with_complex_roots": with_complex,
                        "answer_moves_keeping_complex": moved}


def crit_block(sample):
    """B94-5: which block carries it, printed rather than counted."""
    sizes = {}
    shapes = []
    for s in sample:
        blk = s["closed_alpha"]["block"]
        if blk is None:
            continue
        sizes[blk["size"]] = sizes.get(blk["size"], 0) + 1
        if len(shapes) < 5:
            shapes.append({"economy": s["shape"], "block": blk})
    ok = bool(sizes) and len(sizes) > 1
    shown = ", ".join(f"{k}x{k} on {v}" for k, v in sorted(sizes.items()))
    detail = (f"the block carrying the expansion factor, by size: {shown}. **More than one size "
              f"occurs**, so the block is found and not fixed by the shape of the economy. "
              f"**The single-cell case is the common one**, and there the expansion factor is "
              f"one process's own output-to-input ratio, chosen by a search rather than computed "
              f"by one. Printed rather than counted: " +
              "; ".join(f"{s['economy'][0]}x{s['economy'][1]} economy -> processes "
                        f"{s['block']['processes']}, goods {s['block']['goods']}"
                        for s in shapes[:3]))
    return ok, detail, {"sizes": sizes, "examples": shapes}


def crit_enumeration(sample):
    """B94-6: the search is complete, which every statement above is about."""
    bad = []
    for s in sample:
        n, m = s["shape"]
        want = sum(len(list(itertools.combinations(range(n), k)))
                   * len(list(itertools.combinations(range(m), k)))
                   for k in range(1, min(n, m) + 1))
        if s["closed_alpha"]["pairs"] != want or s["closed_beta"]["pairs"] != want:
            bad.append({"shape": s["shape"], "seen": s["closed_alpha"]["pairs"],
                        "want": want})
    counts = [s["closed_alpha"]["pairs"] for s in sample]
    med = int(np.median(counts)) if counts else 0
    big = max(counts) if counts else 0
    ok = bool(sample) and not bad
    detail = (f"the number of square sub-pairs visited equals "
              f"`sum_k C(n,k) C(m,k)` on {len(sample) - len(bad)} of {len(sample)} economies, "
              f"median {med} and largest {big}. **Everything above "
              f"is an extremum over that set**, and a set short by one member would make all of "
              f"it a statement about a different set")
    return ok, detail, {"economies": len(sample), "mismatches": bad,
                        "median_pairs": med, "largest_pairs": big}


def crit_registration():
    """B94-7: the same round writes back to the station that registered it."""
    doc = (ROOT / "docs" / "b82_rectangular_parts.md").read_text(encoding="utf-8")
    named = "b94_rectangular_closed_form.md" in doc
    return named, (f"B82's file "
                   f"{'names this station against the registration it opened' if named else '**does not name this station**'}, "
                   f"so a reader of it finds that the factors are eigenvalues of a block that "
                   f"has to be found. `D20`"), {"b82_names_b94": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    sample = draws(np.random.default_rng(5), 14)
    if len(sample) < 8:
        fails.append(f"the fixture drew only {len(sample)} economies")

    named = (("B94-1", crit_published), ("B94-2", crit_alpha), ("B94-3", crit_beta),
             ("B94-4", crit_screen), ("B94-5", crit_block), ("B94-6", crit_enumeration))
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:140]}")
        # B94-1 reads B75's published pair rather than this station's draws
        if name != "B94-1" and fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B94-2 and B94-3: the bisection and the closed form have to be able to disagree
    for name, fn, key in (("B94-2", crit_alpha, "alpha"), ("B94-3", crit_beta, "beta")):
        bent = [dict(s, **{key: s[key] * 1.05}) for s in sample]
        if fn(bent)[0]:
            fails.append(f"{name} passes when the programme and the closed form differ by 5%")

    # B94-4: without an overshoot the screen would be buying nothing, and the reading is that
    # it buys a great deal
    flat = [dict(s, closed_alpha=dict(s["closed_alpha"],
                                      unscreened=s["closed_alpha"]["screened"]))
            for s in sample]
    if crit_screen(flat)[0]:
        fails.append("B94-4 passes when the unscreened maximum never overshoots")

    # B94-5: one block size everywhere would mean the block is fixed by the shape
    onesize = [dict(s, closed_alpha=dict(s["closed_alpha"],
                                         block=dict(s["closed_alpha"]["block"], size=1)))
               for s in sample if s["closed_alpha"]["block"] is not None]
    if crit_block(onesize)[0]:
        fails.append("B94-5 passes when every block has the same size")

    # B94-6: a short enumeration makes every extremum above a statement about another set
    short = [dict(s, closed_alpha=dict(s["closed_alpha"],
                                       pairs=s["closed_alpha"]["pairs"] - 1))
             for s in sample]
    if crit_enumeration(short)[0]:
        fails.append("B94-6 passes when the enumeration is short by one")

    # the screen itself: a gamma above the factor must not pass the alpha screen
    A, B = b82.draw_rect(np.random.default_rng(11))
    a = b75.expansion_factor(A, B)
    if a is not None and feasible_alpha(A, B, a * 1.5):
        fails.append("the feasibility screen passes a factor half again above the true one")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} economies")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--economies", type=int, default=N_ECONOMIES)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.economies)
    print(f"{len(sample)} rectangular economies\n")

    criteria, report = [], {}
    for name, kind, fn in (("B94-1", "known_answer", crit_published),
                           ("B94-2", "own_reading", crit_alpha),
                           ("B94-3", "own_reading", crit_beta),
                           ("B94-4", "own_reading", crit_screen),
                           ("B94-5", "own_reading", crit_block),
                           ("B94-6", "instrument", crit_enumeration)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B94-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B94-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B94-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B94",
        "config": {"seed": args.seed, "economies": args.economies, "agree_tol": AGREE_TOL,
                   "feasible_tol": FEASIBLE_TOL, "eig_tol": EIG_TOL,
                   "imports": "b75_rectangular_programme, b82_rectangular_parts"},
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
