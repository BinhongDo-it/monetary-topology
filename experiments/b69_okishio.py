"""B69-5 and B69-6: the known answer and the structural checks for Okishio's theorem.

The statements are proved in docs/b69_okishio.md. This file checks their algebra on random
productive systems built by the industry generator of stage A19. It reads no data and measures
nothing in the world.

  B69-5   Okishio (1961), Kobe University Economic Review 7: with the real wage basket held
          fixed, a technique that lowers cost at the current prices does not lower the general
          rate of profit. Read back on drawn systems.
  B69-6a  Theorem 14(2): the cost criterion is exactly a statement about a cycle. The new
          method's production cycle, evaluated in the OLD field, carries a sum greater than
          log(1 + r) if and only if the new column is cheaper at the old prices. Checked as an
          equivalence on every draw, cheaper or dearer, and the inequality on the rate is
          strict wherever the augmented matrix stays irreducible.
  B69-6b  Theorem 14(1) is an equivalence, and this is its other half: a substitution that is
          dearer at the current prices lowers the rate of profit, every time. The upper
          Collatz-Wielandt bound gives Okishio's half and the lower one gives this half.
  B69-6c  Corollary 14.1: one bound, a family of test vectors. For any positive row vector u,
          lambda_PF(M) <= max_j (u M)_j / u_j. The family of Theorem 13 of B68 supplies the test
          vectors: its member at r = 0 is the labour value vector, which gives the Fundamental
          Marxian Theorem, and its member at the current rate is the price vector itself, which
          gives Okishio's. Both the family membership of p and the bounds are checked.
  B69-6d  Theorem 14(3): the conclusion is carried by the constant real wage. For a
          cost-reducing substitution there is a rise in the wage basket that exactly cancels it,
          and that threshold is found by bisection and printed.

Run:

    python experiments\\b69_okishio.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monetary_topology.industry import IndustrySpec, build_io_matrix, check_feasible

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b69_okishio.json"

SEED = 0
TOL = 1e-12          # identities that are the same floating point operations on both sides
TOL_CYCLE = 1e-10    # sums of logarithms, where the two legs are computed differently
TOL_BOUND = 1e-12    # slack allowed before a bound counts as violated
N_SYSTEMS = 200
SIZES = (3, 8)
COLUMN_SUMS = (0.3, 0.5, 0.7)
VALUE_OF_BASKET = (0.3, 0.5, 0.7)    # the labour value of the wage basket, so the rate is positive
N_SUBSTITUTIONS = 3                  # new columns drawn per system and basket
SUB_SPREAD = (0.6, 1.4)              # the new column is the old one scaled elementwise in here
R_FRACTIONS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)   # the test vectors, as fractions of R
BISECTION_STEPS = 60
WAGE_MAX = 20.0                      # the largest basket multiple the bisection will look at


def irreducible(a) -> bool:
    n = a.shape[0]
    reach = (a > 0.0).astype(float) + np.eye(n)
    for _ in range(int(math.ceil(math.log2(max(n, 2)))) + 1):
        reach = (reach @ reach > 0.0).astype(float)
    return bool((reach > 0.0).all())


def perron(a):
    values, vectors = np.linalg.eig(a)
    k = int(np.argmax(values.real))
    s = np.real(vectors[:, k])
    if s.sum() < 0:
        s = -s
    return float(values[k].real), s


def random_system(rng):
    n = int(rng.integers(SIZES[0], SIZES[1] + 1))
    column_sum = float(COLUMN_SUMS[int(rng.integers(0, len(COLUMN_SUMS)))])
    for _ in range(60):
        spec = IndustrySpec(count=n, financial_count=0, column_sum=column_sum,
                            seed=int(rng.integers(0, 2**31 - 1)))
        a = build_io_matrix(spec)
        check_feasible(a)
        if irreducible(a):
            return a, rng.uniform(0.2, 2.0, n)
    return None, None


def labour_values(a, l):
    """v = v A + l."""
    return l @ np.linalg.inv(np.eye(a.shape[0]) - a)


def family_member(a, l, r):
    """The member of Theorem 13's family at the rate r, up to the unit of account:
    l (I - (1 + r) A)^{-1}. At r = 0 this is the labour value vector."""
    return l @ np.linalg.inv(np.eye(a.shape[0]) - (1.0 + r) * a)


def augmented(a, l, b):
    """M = A + b l, the matrix whose Perron root fixes the rate when wages are advanced."""
    return a + np.outer(b, l)


def rate_and_prices(a, l, b):
    """1 + r = 1 / lambda_PF(M), and p is the left Perron vector of M."""
    m = augmented(a, l, b)
    lam, _ = perron(m)
    _, p = perron(m.T)
    return 1.0 / lam - 1.0, p, m, lam


def basket_of_value(rng, v, target):
    """A random basket whose labour value is exactly the target."""
    b0 = rng.uniform(0.1, 1.0, len(v))
    return b0 * (target / float(v @ b0))


def substitution(rng, a, l, k):
    """A new method for industry k: the old column scaled elementwise, which keeps the zero
    pattern and so keeps the matrix irreducible."""
    a2 = a.copy()
    l2 = l.copy()
    a2[:, k] = a[:, k] * rng.uniform(SUB_SPREAD[0], SUB_SPREAD[1], a.shape[0])
    l2[k] = l[k] * float(rng.uniform(SUB_SPREAD[0], SUB_SPREAD[1]))
    return a2, l2


def collatz_bound(u, m):
    """lambda_PF(M) <= max_j (u M)_j / u_j for any positive row vector u."""
    return float(np.max((u @ m) / u))


def draws(rng):
    """Every (system, basket, substitution) triple the checks below share, drawn once so that
    the five criteria are read off the same sample."""
    out = []
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = labour_values(a, l)
        if v.min() <= 0.0:
            continue
        for target in VALUE_OF_BASKET:
            b = basket_of_value(rng, v, target)
            r, p, m, lam = rate_and_prices(a, l, b)
            if p.min() <= 0.0 or r <= 0.0:
                continue
            for _s in range(N_SUBSTITUTIONS):
                k = int(rng.integers(0, n))
                a2, l2 = substitution(rng, a, l, k)
                lam2_a, _ = perron(a2)
                if lam2_a >= 1.0:
                    continue
                r2, p2, m2, lam2 = rate_and_prices(a2, l2, b)
                if p2.min() <= 0.0:
                    continue
                out.append({"a": a, "l": l, "v": v, "b": b, "n": n, "k": k,
                            "r": r, "p": p, "m": m, "lam": lam,
                            "a2": a2, "l2": l2, "r2": r2, "p2": p2, "m2": m2, "lam2": lam2,
                            "cheaper": float((p @ m2)[k]) < float((p @ m)[k])})
    return out


# -------------------------------------------------- B69-5: the theorem, read back


def check_okishio(sample):
    """With the real wage basket held fixed, a column that is cheaper at the current prices
    does not lower the rate of profit."""
    cheaper = holds = strict = 0
    smallest_gain = None
    worst_violation = 0.0
    for d in sample:
        if not d["cheaper"]:
            continue
        cheaper += 1
        gain = d["r2"] - d["r"]
        holds += gain >= -TOL_BOUND
        strict += gain > 0.0
        worst_violation = max(worst_violation, -gain)
        smallest_gain = gain if smallest_gain is None else min(smallest_gain, gain)
    ok = cheaper > 0 and holds == cheaper and strict == cheaper
    detail = ("%d of %d drawn substitutions are cheaper at the current prices, and **every one "
              "of them raises the rate of profit**, with the real wage basket held fixed in "
              "kind. Zero counterexamples. This is Okishio's theorem of 1961, *Technical "
              "Changes and the Rate of Profit*, Kobe University Economic Review 7, read back "
              "here on drawn systems; the starting page is given as 85 in one secondary source "
              "and 86 in another, and both are reported rather than merged. The rate is "
              "`1 / lambda_PF(A + b l) - 1` throughout, so the theorem is a statement about a "
              "Perron root and the wage basket is what is held fixed"
              % (cheaper, len(sample)))
    printed = ["cheaper draws %d, rate rises on %d, strictly on %d; smallest gain in the rate "
               "%.6f; worst move against the theorem %.3e"
               % (cheaper, holds, strict, 0.0 if smallest_gain is None else smallest_gain,
                  worst_violation)]
    return ok, detail, {"draws": len(sample), "cheaper": cheaper, "holds": holds,
                        "strict": strict}, printed


# ------------------------------ B69-6a: the cost criterion is a statement about a cycle


def check_cycle_reading(sample):
    """In the OLD field, industry k's production cycle run with the NEW method carries
    log(p_k / (p M')_k). The old cycle carries log(1 + r). So the cycle sum exceeds the old one
    exactly when the new column is cheaper at the old prices: the cost criterion and the cycle
    reading are the same statement."""
    points = agree = 0
    worst_gap = 0.0
    smallest_margin = None
    for d in sample:
        k, p = d["k"], d["p"]
        old_cost = float((p @ d["m"])[k])
        new_cost = float((p @ d["m2"])[k])
        # the old cycle sum is log(1 + r) by construction; check it, then compare the new one
        worst_gap = max(worst_gap, abs(math.log(p[k] / old_cost) - math.log1p(d["r"])))
        excess = math.log(p[k] / new_cost) - math.log1p(d["r"])
        points += 1
        agree += (excess > 0.0) == d["cheaper"]
        margin = abs(excess)
        smallest_margin = margin if smallest_margin is None else min(smallest_margin, margin)
    ok = points > 0 and agree == points and worst_gap < TOL_CYCLE
    detail = ("%d draws. **The old field's production cycle for industry k carries log(1 + r)** "
              "within %g, and the same cycle run with the new method carries more than that "
              "exactly when the new column is cheaper at the old prices, on all %d draws. "
              "**So the cost criterion is not an extra assumption about behaviour: it is the "
              "statement that the new method's cycle shows an excess sum in the field that is "
              "in force**, and the theorem says that excess survives the re-solving of the "
              "whole field rather than turning negative"
              % (points, TOL_CYCLE, points))
    printed = ["worst |old cycle sum - log(1+r)| %.3e; the equivalence holds on %d of %d draws; "
               "smallest |excess| seen %.3e"
               % (worst_gap, agree, points, 0.0 if smallest_margin is None else smallest_margin)]
    return ok, detail, {"points": points, "agree": agree, "within": TOL_CYCLE}, printed


# ------------------------------------ B69-6b: the hypothesis is doing work


def check_dearer(sample):
    """The other half of the equivalence. Off column k the two matrices agree, so the minimum
    of (p M')_j / p_j is still lambda, and the lower Collatz-Wielandt bound gives lambda' >=
    lambda whenever the new column is dearer."""
    dearer = falls = rises = 0
    worst_fall = 0.0
    for d in sample:
        if d["cheaper"]:
            continue
        dearer += 1
        if d["r2"] < d["r"]:
            falls += 1
            worst_fall = min(worst_fall, d["r2"] - d["r"])
        else:
            rises += 1
    ok = dearer > 0 and falls == dearer
    detail = ("%d of %d drawn substitutions are dearer at the current prices, and **the rate "
              "of profit falls on every one of them**, %d of %d, rising on %d. **So Theorem "
              "14(1) is an equivalence and not an implication**: the sign of the change in the "
              "general rate of profit is the sign of the cost saving on the one column that "
              "changed, read at the prices in force. Okishio's half is the upper "
              "Collatz-Wielandt bound and this half is the lower one, and off column k the two "
              "matrices agree so both extrema are still attained at lambda. The largest fall "
              "seen is %.4f in the rate. What this does not say: nobody adopts a dearer column "
              "in this setting, and the arm is here because an equivalence is a stronger "
              "statement than the published implication and has to be shown on both sides"
              % (dearer, len(sample), falls, dearer, rises, -worst_fall))
    printed = ["dearer draws %d, of which the rate falls on %d and rises on %d; largest fall "
               "%.6f" % (dearer, falls, rises, -worst_fall)]
    return ok, detail, {"dearer": dearer, "falls": falls, "rises": rises}, printed


# ----------------------------- B69-6c: one bound, and the family that supplies its test vectors


def check_test_vectors(sample):
    """For any positive row vector u, lambda_PF(M) <= max_j (u M)_j / u_j. The family of
    Theorem 13 of B68 supplies the test vectors: at r = 0 it is the labour value vector, and at
    the current rate it is, up to scale, the price vector itself. So the Fundamental Marxian
    Theorem and Okishio's theorem are the same bound at two members of one family."""
    points = valid = member_ok = 0
    worst_member = 0.0
    tight_counts = {}
    worst_bound_gap = None
    for d in sample:
        a, l, r = d["a"], d["l"], d["r"]
        # the price vector is the family's member at the current rate, up to the unit of account
        member = family_member(a, l, r)
        u_p = d["p"] / d["p"].max()
        u_m = member / member.max()
        worst_member = max(worst_member, float(np.abs(u_p - u_m).max()))
        member_ok += float(np.abs(u_p - u_m).max()) < TOL_CYCLE
        # every member of the family is a legitimate test vector for the NEW matrix
        lam_new = d["lam2"]
        best_f, best_bound = None, None
        for f in R_FRACTIONS:
            lam_a, _ = perron(a)
            r0 = f * (1.0 / lam_a - 1.0)
            u = family_member(a, l, r0)
            if u.min() <= 0.0:
                continue
            bound = collatz_bound(u, d["m2"])
            points += 1
            valid += bound >= lam_new - TOL_BOUND
            slack = bound - lam_new
            worst_bound_gap = slack if worst_bound_gap is None else min(worst_bound_gap, slack)
            if best_bound is None or bound < best_bound:
                best_bound, best_f = bound, f
        if best_f is not None:
            tight_counts[best_f] = tight_counts.get(best_f, 0) + 1
    ok = (points > 0 and valid == points and member_ok == len(sample)
          and worst_member < TOL_CYCLE)
    order = sorted(tight_counts.items(), key=lambda kv: -kv[1])
    detail = ("%d draws, %d test vectors each. **The price vector is the family's member at the "
              "current rate, up to the unit of account**, within %g on every draw, since "
              "`p = (1 + r)(p b) l (I - (1 + r) A)^{-1}` follows from the price equation. "
              "**Every member of the family bounds the Perron root of the new augmented "
              "matrix**, at all %d points: the member at `r = 0` is the labour value vector and "
              "gives the Fundamental Marxian Theorem, the member at the current rate gives "
              "Okishio's theorem, and the rest give bounds nobody has asked for. **The two "
              "theorems are one inequality evaluated at two points of one family**"
              % (len(sample), len(R_FRACTIONS), TOL_CYCLE, points))
    printed = ["worst |p - family member at r| after scaling %.3e on %d of %d draws; every "
               "bound valid on %d of %d points, worst slack %.3e; tightest member by count: %s"
               % (worst_member, member_ok, len(sample), valid, points,
                  0.0 if worst_bound_gap is None else worst_bound_gap,
                  ", ".join("r = %g R on %d" % (f, c) for f, c in order[:3]))]
    return ok, detail, {"draws": len(sample), "points": points, "valid": valid,
                        "member_within": TOL_CYCLE}, printed


# --------------------------- B69-6d: the constant real wage is what carries the conclusion


def check_wage(sample):
    """For a cost-reducing substitution, raise the wage basket by a factor and the gain in the
    rate is cancelled. The factor at which it is exactly cancelled is found by bisection, so
    the statement is a number rather than an assertion."""
    cheaper = found = 0
    thresholds = []
    for d in sample:
        if not d["cheaper"]:
            continue
        cheaper += 1
        a2, l2, b, r = d["a2"], d["l2"], d["b"], d["r"]

        def rate_at(g):
            lam, _ = perron(augmented(a2, l2, b * (1.0 + g)))
            return 1.0 / lam - 1.0

        if rate_at(WAGE_MAX) >= r:
            continue                      # the cancelling rise is beyond the window searched
        lo, hi = 0.0, WAGE_MAX
        for _ in range(BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if rate_at(mid) > r:
                lo = mid
            else:
                hi = mid
        found += 1
        thresholds.append(0.5 * (lo + hi))
    ok = cheaper > 0 and found == cheaper and len(thresholds) > 0
    arr = np.array(thresholds) if thresholds else np.array([0.0])
    detail = ("%d cheaper substitutions. **For every one of them there is a rise in the real "
              "wage basket that exactly cancels the gain in the rate of profit**, found by "
              "bisection inside a window of %g, on %d of %d. The median cancelling rise is "
              "%.4f of the basket and the range is %.4f to %.4f. **So the direction the rate "
              "moves after a technical change is fixed by two inputs, the technique and the "
              "basket, and the theorem holds the second one still.** Which way the basket moves "
              "is not a statement this framework supplies"
              % (cheaper, WAGE_MAX, found, cheaper, float(np.median(arr)), float(arr.min()),
                 float(arr.max())))
    printed = ["cheaper draws %d, cancelling rise found on %d; median %.4f, min %.4f, max %.4f"
               % (cheaper, found, float(np.median(arr)), float(arr.min()), float(arr.max()))]
    return ok, detail, {"cheaper": cheaper, "found": found,
                        "window": WAGE_MAX, "bisection_steps": BISECTION_STEPS}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    sample = draws(rng)
    results = [
        ("B69-5", "known_answer",
         "Okishio (1961): with the real wage fixed, a technique cheaper at the current prices "
         "does not lower the rate of profit", check_okishio(sample)),
        ("B69-6a", "instrument",
         "Theorem 14(2): the cost criterion is the statement that the new method's cycle shows "
         "an excess sum in the field in force", check_cycle_reading(sample)),
        ("B69-6b", "instrument",
         "Theorem 14(1) is an equivalence: a dearer column lowers the rate, every time",
         check_dearer(sample)),
        ("B69-6c", "instrument",
         "Corollary 14.1: one bound, and the family of Theorem 13 supplies its test vectors",
         check_test_vectors(sample)),
        ("B69-6d", "instrument",
         "Theorem 14(3): a rise in the wage basket cancels the gain, and the cancelling rise "
         "is a number", check_wage(sample)),
    ]
    mapping = {
        "B69-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B69-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B69-5 and B69-6: the known answer and the structural checks for docs/b69_okishio.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
    print("\n  %d (system, basket, substitution) draws shared by all five" % len(sample))
    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep, printed) in results:
        print("\n%s  %s  [%s]\n  %s\n  %s" % (name, "PASS" if ok else "FAIL", kind, statement,
                                              detail))
        for line in printed:
            print("    " + line)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
    rec = {
        "stage": "B69",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_bound": TOL_BOUND,
            "n_systems": N_SYSTEMS, "sizes": list(SIZES), "column_sums": list(COLUMN_SUMS),
            "value_of_basket": list(VALUE_OF_BASKET), "n_substitutions": N_SUBSTITUTIONS,
            "sub_spread": list(SUB_SPREAD), "r_fractions": list(R_FRACTIONS),
            "bisection_steps": BISECTION_STEPS, "wage_max": WAGE_MAX,
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all five pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
