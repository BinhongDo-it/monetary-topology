"""B82: the two families on a general rectangular economy, and they are two index sets.

Paper station, zero data.  Closes B80's registration: the two-family statement for
a general rectangular `B`, where the parts are no longer principal blocks of one
matrix.  The support argument generalises and it says something sharper than B80's
version: the family that carries `alpha` is a family of process sets and the family
that carries `beta` is a family of good sets.  `B = I` identifies the two index
sets, which is why B80 could state both over goods.

The solver is B75's and the independence machinery is B80's; both are imported.

Run:  python experiments/b82_rectangular_parts.py [--reps N] [--seed S]
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b75_rectangular_programme as b75      # noqa: E402
import b80_reducible as b80                  # noqa: E402

OUT = ROOT / "results" / "b82_rectangular_parts.json"

SEED = 82
REPS = 8
FACTOR_TOL = 1e-5          # the bisection's floor, looser than B80's because the
                           # sub-economies here are solved on smaller blocks
MAX_N = 6                  # enumeration is over subsets, so the size is capped


# ------------------------------------------------- the two admissible families

def produced(B, T):
    return {j for j in range(B.shape[1]) if any(B[i, j] > 0 for i in T)}


def consumed(A, T):
    return {j for j in range(A.shape[1]) if any(A[i, j] > 0 for i in T)}


def admissible_process_sets(A, B):
    """Process sets T with consumed(T) subset produced(T).

    This is what the quantity programme forces on the support of `x`: for a good the
    set does not produce, the constraint reads `0 >= alpha (x'A)_j`, so the set may
    not consume it either.
    """
    out = []
    for r in range(1, A.shape[0] + 1):
        for T in itertools.combinations(range(A.shape[0]), r):
            pr, co = produced(B, T), consumed(A, T)
            if pr and co <= pr:
                out.append((T, sorted(pr)))
    return out


def admissible_good_sets(A, B):
    """Good sets S such that every process producing into S also consumes from S.

    This is what the price programme forces on the support of `p`: a process that
    consumes nothing priced faces `(Bp)_i <= 0`, so it may not produce anything
    priced either.
    """
    out = []
    n, m = A.shape
    for r in range(1, m + 1):
        for S in itertools.combinations(range(m), r):
            ok = True
            for i in range(n):
                if any(B[i, j] > 0 for j in S) and not any(A[i, j] > 0 for j in S):
                    ok = False
                    break
            if ok:
                out.append(sorted(S))
    return out


def sub_alpha(A, B, T, goods):
    return b75.expansion_factor(A[np.ix_(list(T), goods)], B[np.ix_(list(T), goods)])


def sub_beta(A, B, S):
    rows = [i for i in range(A.shape[0])
            if A[np.ix_([i], S)].any() or B[np.ix_([i], S)].any()]
    if not rows:
        return None
    return b75.interest_factor(A[np.ix_(rows, S)], B[np.ix_(rows, S)])


def draw_rect(rng):
    n = int(rng.integers(3, MAX_N + 1))
    m = int(rng.integers(3, MAX_N + 1))
    return b80.draw_economy(rng, n, m, density=float(rng.uniform(0.3, 0.5)))


# ------------------------------------------------- B82-1  the published pair

def check_published():
    """B82-1 known_answer: both examples, through the same solver B80 used."""
    rows = []
    for name, Al, Bl, want in (("example 1", b75.QE1_A, b75.QE1_B, b75.QE1_PUBLISHED),
                               ("example 2", b75.QE2_A, b75.QE2_B, b75.QE2_PUBLISHED)):
        A, B = np.array(Al, float), np.array(Bl, float)
        rows.append({"example": name, "alpha": b75.expansion_factor(A, B),
                     "beta": b75.interest_factor(A, B),
                     "published": list(want), "shape": list(A.shape)})
    ok = all(abs(r["alpha"] - r["published"][0]) < 1e-8
             and abs(r["beta"] - r["published"][1]) < 1e-8 for r in rows)
    detail = ("; ".join(f"{r['example']} {r['shape']}: alpha {r['alpha']:.9f}, "
                        f"beta {r['beta']:.9f}" for r in rows)
              + ", both inside 1e-8 of the published pair")
    return bool(ok), detail, {"published": rows}


# ------------------------------------------------- B82-2  it specialises to B80

def check_specialises(rng, reps):
    """B82-2 instrument: on a simple economy the process family maps onto B80's
    good family, which is a cross-check between two stations."""
    rows, bad = [], 0
    for _ in range(reps):
        A, B = b80.draw_simple(rng)
        proc = admissible_process_sets(A, B)
        # with B = I, process i produces good i, so produced(T) is T itself
        as_goods = {frozenset(pr) for _, pr in proc}
        good = {frozenset(s) for s in b80.independent_by_goods(A, B)}
        agree = as_goods == good
        rows.append({"n": int(A.shape[0]), "process_sets": len(proc),
                     "as_goods": len(as_goods), "b80_independent": len(good),
                     "agree": bool(agree)})
        if not agree:
            bad += 1
    ok = bad == 0 and len(rows) >= 3
    detail = (f"{len(rows)} simple economies: the image of the process family under "
              f"`T -> produced(T)` is B80's family of independent good sets in "
              f"{len(rows) - bad} of {len(rows)}. **B = I is what identifies the two "
              f"index sets**, and that is why B80 could state both families over goods")
    return bool(ok), detail, {"specialisation": rows}


# ------------------------------------------------- B82-3 and B82-4  the two maxima

def check_two_families(rng, reps):
    """B82-3 and B82-4 in one sweep: alpha is a max over process sets, beta a min
    over good sets, on a general rectangular economy."""
    rows, bad_a, bad_b, used = [], 0, 0, 0
    pool = [("example 2", np.array(b75.QE2_A, float), np.array(b75.QE2_B, float))]
    for k in range(reps):
        pool.append((f"draw {k}", *draw_rect(rng)))
    for name, A, B in pool:
        a0, b0 = b75.expansion_factor(A, B), b75.interest_factor(A, B)
        if a0 is None or b0 is None:
            continue
        av = [v for v in (sub_alpha(A, B, T, g) for T, g in admissible_process_sets(A, B))
              if v is not None]
        bv = [v for v in (sub_beta(A, B, S) for S in admissible_good_sets(A, B))
              if v is not None]
        if not av or not bv:
            continue
        used += 1
        da, db = abs(a0 - max(av)), abs(b0 - min(bv))
        if da >= FACTOR_TOL:
            bad_a += 1
        if db >= FACTOR_TOL:
            bad_b += 1
        rows.append({"case": name, "shape": list(A.shape),
                     "alpha0": a0, "max_over_process_sets": max(av),
                     "beta0": b0, "min_over_good_sets": min(bv),
                     "process_family": len(av), "good_family": len(bv),
                     "gap": a0 - b0})
    ok = used >= 4 and bad_a == 0 and bad_b == 0
    worst_a = max((abs(r["alpha0"] - r["max_over_process_sets"]) for r in rows), default=0.0)
    worst_b = max((abs(r["beta0"] - r["min_over_good_sets"]) for r in rows), default=0.0)
    detail = (f"{used} rectangular economies. **alpha_0 is the max over process sets with "
              f"`consumed(T) subset produced(T)`** in {used - bad_a} of {used}, worst "
              f"departure {worst_a:.2e}; **beta_0 is the min over good sets every process "
              f"producing into which also consumes from**, in {used - bad_b} of {used}, "
              f"worst {worst_b:.2e}, both against {FACTOR_TOL:.0e}")
    return bool(ok), detail, {"two_families": rows}


# ------------------------------------------------- B82-5  two index sets

def check_two_index_sets(rng, reps):
    """B82-5 own_reading: in general the two families are not the same family, and
    they are not even indexed by the same thing."""
    rows, differ = [], 0
    for k in range(reps * 2):
        A, B = draw_rect(rng)
        proc = admissible_process_sets(A, B)
        good = admissible_good_sets(A, B)
        if not proc or not good:
            continue
        as_goods = {frozenset(pr) for _, pr in proc}
        same = as_goods == {frozenset(s) for s in good}
        rows.append({"shape": list(A.shape), "process_family": len(proc),
                     "good_family": len(good), "images_coincide": bool(same)})
        if not same:
            differ += 1
    ok = len(rows) >= 4 and differ > 0
    detail = (f"{len(rows)} rectangular economies: the image of the process family and "
              f"the good family are different families in {differ} of {len(rows)}. "
              f"**The two factors are carried by two index sets, processes and goods**, "
              f"and B80 could state both over goods only because `B = I` identifies them")
    return bool(ok), detail, {"index_sets": rows}


# ------------------------------------------------- B82-6  the supports

def check_supports(rng, reps):
    """B82-6 own_reading: the solution's own supports are admissible, measured."""
    rows, bad, used = [], 0, 0
    pool = [("example 2", np.array(b75.QE2_A, float), np.array(b75.QE2_B, float))]
    for k in range(reps):
        pool.append((f"draw {k}", *draw_rect(rng)))
    for name, A, B in pool:
        a0, x, p = b75.solution(A, B)
        if a0 is None or x is None or p is None:
            continue
        used += 1
        Tx = tuple(i for i, v in enumerate(x) if v > 1e-8)
        Sp = [j for j, v in enumerate(p) if v > 1e-8]
        x_ok = bool(Tx) and consumed(A, Tx) <= produced(B, Tx)
        p_ok = bool(Sp) and all(
            not (any(B[i, j] > 0 for j in Sp) and not any(A[i, j] > 0 for j in Sp))
            for i in range(A.shape[0]))
        rows.append({"case": name, "support_x": list(Tx), "support_p": Sp,
                     "x_admissible": x_ok, "p_admissible": p_ok})
        if not (x_ok and p_ok):
            bad += 1
    ok = used >= 4 and bad == 0
    detail = (f"{used} economies: the intensity vector's support satisfies the process "
              f"condition and the price vector's support satisfies the good condition in "
              f"{used - bad} of {used}. **The two conditions are not imposed anywhere in "
              f"the solver; they are read off the solution it returns**")
    return bool(ok), detail, {"supports": rows}


# ------------------------------------------------- B82-7  B80's registration

def check_registration():
    reg = ("B80 registered: the two-family statement for a general rectangular B, "
           "where the same support argument holds but the parts are no longer "
           "principal blocks of one matrix so the Perron route is unavailable")
    ans = ("Answered by B82-3, which carries both halves in one sweep, and the "
           "answer is sharper than the "
           "registration expected: the two families are not two families over one "
           "index set, they are one family of process sets and one family of good "
           "sets, and B = I is what collapses that distinction")
    return True, f"{reg}. {ans}", {"registration": {"text": reg, "answered_by": ans}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    results = [
        ("B82-1", "known_answer",
         "both published example economies return their published factors through "
         "the same solver B80 used", check_published()),
        ("B82-2", "instrument",
         "on a simple economy the process family's image under T -> produced(T) is "
         "B80's family of independent good sets", check_specialises(rng, a.reps)),
        ("B82-3", "own_reading",
         "alpha_0 is the max over process sets with consumed(T) contained in "
         "produced(T), and beta_0 is the min over good sets every process producing "
         "into which also consumes from", check_two_families(rng, a.reps)),
        ("B82-5", "own_reading",
         "the two families are carried by two different index sets, processes and "
         "goods, and coincide only when B = I identifies them",
         check_two_index_sets(rng, a.reps)),
        ("B82-6", "own_reading",
         "the solution's own supports satisfy the two conditions, which are not "
         "imposed anywhere in the solver", check_supports(rng, a.reps)),
        ("B82-7", "bookkeeping",
         "B80's registration, named, with the way the answer is sharper than it",
         check_registration()),
    ]

    mapping = {
        "B82-1": "both factors inside 1e-8 of the published pair -> PASS",
        "B82-2": "the image of the process family equals B80's good family on every simple "
                 "economy drawn -> PASS; any disagreement -> FAIL, and it would mean one of "
                 "the two stations has the condition wrong",
        "B82-3": "both maxima match their programme's factor everywhere -> PASS; else FAIL",
        "B82-5": "the two families differ somewhere -> PASS; never differing would mean the "
                 "distinction this station draws is empty, which is a finding and not a "
                 "broken check",
        "B82-6": "both supports admissible everywhere -> PASS; else FAIL",
        "B82-7": "the registration named with what answers it -> PASS",
    }

    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep) in results:
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail}")

    rec = {
        "stage": "B82",
        "config": {"seed": a.seed, "reps": a.reps, "factor_tol": FACTOR_TOL,
                   "max_index_size": MAX_N,
                   "solver": "b75_rectangular_programme, imported not rewritten",
                   "independence": "b80_reducible, imported not rewritten"},
        "sources": {
            "examples": "QuantEcon, Von Neumann Growth Model (and a Generalization)",
            "original": "Kemeny, Morgenstern and Thompson (1956), Econometrica 24, 115-135",
        },
        "criteria": criteria, "mapping": mapping, "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    failed = [c["name"] for c in criteria if not c["passed"]]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
