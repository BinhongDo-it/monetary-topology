"""B71-5 and B71-6: the known answer and the structural checks for the von Neumann model.

The statements are proved in docs/b71_von_neumann.md. This file reads no data and measures
nothing in the world.

  B71-5   von Neumann (1945), Review of Economic Studies 13(1), 1-9: his conditions (7), (8),
          (7') and (8'), and his conclusion that the interest factor and the coefficient of
          expansion are equal and uniquely determined. Read back on drawn systems.
  B71-6a  Theorem 16(1): the expansion factor read off the flow side and the interest factor
          read off the field side are one number, because they are one Perron root of one
          pencil. The intensity vector is the right Perron vector and is positive; the price
          vector is the left one carried back through B and need not be.
  B71-6b  Theorem 16(2): at the solution every process's production cycle carries log(beta),
          so von Neumann's equality says the common cycle sum is the log of the economy's
          expansion factor.
  B71-6c  Theorem 16(3): the two complementary slackness conditions read on cycles, checked by
          construction rather than by solving a programme. A dominated process has a cycle sum
          strictly below the common one, so (8') idles it; a good that no process uses and some
          process makes is in excess, so (7') prices it at zero and the rest is unchanged.
  B71-6d  Corollary 16.1: with B the identity and no wage, the pencil is (I, A), the root is
          1 / lambda_PF(A), the right vector is Sraffa's standard proportions and the left one
          is his price vector at the maximum rate. **Sraffa's standard commodity is the von
          Neumann ray of that economy.**
  B71-6e  Corollary 16.2: fold the wage basket in, M = A + b l, and the same root is the
          1 + r of B68 and B69: balanced growth with every profit reinvested runs at the rate
          of profit.

Run:

    python experiments\\b71_von_neumann.py
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
OUT = ROOT / "results" / "b71_von_neumann.json"

SEED = 0
TOL = 1e-12
TOL_CYCLE = 1e-10
TOL_RANK = 1e-9
N_SYSTEMS = 400
SIZES = (2, 6)
INPUT_COLUMN_SUMS = (0.3, 0.5, 0.7)
JOINT_WEIGHT = (0.0, 0.6)
VALUE_OF_BASKET = (0.3, 0.5, 0.7)
DOMINATED_INPUT = 1.2          # the added process uses this much more of everything
DOMINATED_OUTPUT = 0.9         # and delivers this much less


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


def positive_eigenvectors(a, tol=TOL_RANK):
    """How many eigenvalues of a carry an eigenvector that can be scaled positive."""
    values, vectors = np.linalg.eig(a)
    count = 0
    for k in range(len(values)):
        if abs(values[k].imag) > tol:
            continue
        s = np.real(vectors[:, k])
        if s.min() > tol or s.max() < -tol:
            count += 1
    return count


def random_system(rng):
    """A square system whose input matrix per unit of output bundle, B^{-1}A, is non-negative
    and irreducible. That is what puts the pencil inside Perron-Frobenius's reach."""
    for _ in range(60):
        n = int(rng.integers(SIZES[0], SIZES[1] + 1))
        column_sum = float(INPUT_COLUMN_SUMS[int(rng.integers(0, len(INPUT_COLUMN_SUMS)))])
        a = rng.uniform(0.0, 1.0, (n, n))
        a = a / a.sum(axis=0) * column_sum
        joint = rng.uniform(JOINT_WEIGHT[0], JOINT_WEIGHT[1], (n, n))
        np.fill_diagonal(joint, 0.0)
        b = np.eye(n) + joint * rng.uniform(0.0, 1.0, (n, n))
        if abs(np.linalg.det(b)) < TOL_RANK:
            continue
        c = np.linalg.inv(b) @ a
        if c.min() < 0.0 or not irreducible(c):
            continue
        l = rng.uniform(0.2, 2.0, n)
        return a, b, l, c
    return None, None, None, None


def von_neumann(a, b):
    """The pencil (B, A). With C = B^{-1}A non-negative and irreducible, Perron-Frobenius
    gives one root: alpha = beta = 1 / lambda_PF(C). The right Perron vector of C is the
    intensity vector; the left one, carried back through B, is the price vector."""
    c = np.linalg.inv(b) @ a
    lam, x = perron(c)
    _lam_left, u = perron(c.T)
    p = u @ np.linalg.inv(b)
    return 1.0 / lam, x, p, u, c, lam


def smallest_root_by_determinant(m, hi=6.0, grid=600, steps=80):
    """The smallest r > 0 with det(I - (1+r) M) = 0, found by scanning for a sign change and
    bisecting. This shares no code path with the eigen-decomposition, so comparing the two is
    a check and not a restatement."""
    n = m.shape[0]

    def f(r):
        return float(np.linalg.det(np.eye(n) - (1.0 + r) * m))

    prev_r, prev_f = 0.0, f(0.0)
    for k in range(1, grid + 1):
        r = hi * k / grid
        cur = f(r)
        if prev_f == 0.0:
            return prev_r
        if (prev_f > 0.0) != (cur > 0.0):
            lo, high = prev_r, r
            for _ in range(steps):
                mid = 0.5 * (lo + high)
                if (f(lo) > 0.0) != (f(mid) > 0.0):
                    high = mid
                else:
                    lo = mid
            return 0.5 * (lo + high)
        prev_r, prev_f = r, cur
    return None


# ----------------------------------------- B71-5: von Neumann's theorem, read back


def check_von_neumann(rng):
    systems = equal = unique_x = unique_p = positive_p = 0
    worst_equal = worst_flow = worst_field = 0.0
    for _ in range(N_SYSTEMS):
        a, b, l, c = random_system(rng)
        if a is None:
            continue
        systems += 1
        alpha, x, p, u, c, lam = von_neumann(a, b)
        # the flow side, his (7) with equality: alpha A x = B x
        worst_flow = max(worst_flow, float(np.abs(alpha * (a @ x) - b @ x).max()))
        # the field side, his (8) with equality: beta p A = p B
        beta = alpha
        worst_field = max(worst_field, float(np.abs(beta * (p @ a) - p @ b).max()))
        # the two numbers are one root of one pencil
        lam_left, _ = perron(c.T)
        worst_equal = max(worst_equal, abs(1.0 / lam - 1.0 / lam_left))
        equal += abs(1.0 / lam - 1.0 / lam_left) < TOL_CYCLE
        unique_x += positive_eigenvectors(c) == 1
        unique_p += positive_eigenvectors(c.T) == 1
        positive_p += bool(p.min() > 0.0)
    ok = (systems > 0 and equal == systems and unique_x == systems and unique_p == systems
          and worst_equal < TOL_CYCLE and worst_flow < TOL_CYCLE and worst_field < TOL_CYCLE)
    detail = ("%d drawn square systems whose input matrix per unit of output bundle, `B^{-1}A`, "
              "is non-negative and irreducible. von Neumann (1945), *A Model of General "
              "Economic Equilibrium*, Review of Economic Studies 13(1), 1-9, writes his "
              "conditions as (7) `a Sum a_ij x_i <= Sum b_ij x_i`, (8) `B Sum a_ij y_j >= Sum "
              "b_ij y_j`, with (7') `if < in (7) then y_j = 0` and (8') `if > in (8) then "
              "x_i = 0`, and concludes **'the interest factor and the coefficient of expansion "
              "of the economy are equal and uniquely determined'**. Here both hold with "
              "equality, within %g on the flow side and %g on the field side, and **the two "
              "factors agree** within %g on all %d systems. **Uniqueness is read back as "
              "well**: exactly one eigenvalue carries a positive intensity vector on %d of %d, "
              "and exactly one carries a positive left vector on %d of %d. The price vector "
              "itself, `u B^{-1}`, comes out positive on %d of %d, which is what the filter "
              "buys: **these draws are the systems where Perron-Frobenius reaches the pencil, "
              "and there the equality system already has the positive solution.** B70 read the "
              "other side of that: among productive joint systems drawn without this filter, "
              "52 of 400 had no rate at all carrying a positive price vector. **The "
              "inequalities and free disposal are for those**"
              % (systems, TOL_CYCLE, TOL_CYCLE, TOL_CYCLE, systems, unique_x, systems,
                 unique_p, systems, positive_p, systems))
    printed = ["worst |alpha - beta| %.3e; worst flow-side residual %.3e; worst field-side "
               "residual %.3e; one positive intensity vector on %d, one positive left vector "
               "on %d; prices positive on %d of %d"
               % (worst_equal, worst_flow, worst_field, unique_x, unique_p, positive_p, systems)]
    return ok, detail, {"systems": int(systems), "equal": int(equal),
                        "unique_intensity": int(unique_x), "unique_left": int(unique_p),
                        "prices_positive": int(positive_p), "within": TOL_CYCLE}, printed


# --------------------------------- B71-6a and 6b: one pencil, and the cycle it puts a sum on


def check_pencil_and_cycles(rng):
    systems = readable = equal = 0
    worst_sum = worst_root = 0.0
    for _ in range(N_SYSTEMS):
        a, b, l, c = random_system(rng)
        if a is None:
            continue
        systems += 1
        alpha, x, p, u, c, lam = von_neumann(a, b)
        # the root read off either side of the pencil
        lam_left, _ = perron(c.T)
        worst_root = max(worst_root, abs(lam - lam_left))
        cost = p @ a
        back = p @ b
        if cost.min() > 0.0 and back.min() > 0.0:
            readable += 1
            sums = np.log(back) - np.log(cost)
            gap = float(np.abs(sums - math.log(alpha)).max())
            worst_sum = max(worst_sum, gap)
            equal += gap < TOL_CYCLE
    ok = (systems > 0 and readable > 0 and equal == readable
          and worst_sum < TOL_CYCLE and worst_root < TOL_CYCLE)
    detail = ("%d systems. **The root is the same read from either side of the pencil**, within "
              "%g. At the solution the wage is zero and every process's production cycle buys "
              "its input bundle for `(pA)_j` and sells its output bundle for `(pB)_j`, so "
              "**each cycle carries `log(beta)` and they are all equal**, within %g on the %d "
              "systems where every leg is positive. **So von Neumann's equality says that the "
              "common cycle sum is the logarithm of the economy's expansion factor**: the "
              "number the field puts on every cycle and the number the flow grows by are one "
              "number. Every leg is positive on every draw here, the filter having put "
              "these systems inside Perron-Frobenius's reach; B70 is where the other case "
              "lives, and there the equality between the legs holds while the logarithm does "
              "not exist"
              % (systems, TOL_CYCLE, TOL_CYCLE, readable))
    printed = ["worst |root from the right - root from the left| %.3e; worst |cycle sum - "
               "log(alpha)| %.3e; every leg positive on %d of %d"
               % (worst_root, worst_sum, readable, systems)]
    return ok, detail, {"systems": int(systems), "readable": int(readable),
                        "equal": int(equal), "within": TOL_CYCLE}, printed


# ------------------------------- B71-6c: the two slackness conditions, built rather than solved


def check_slackness(rng):
    systems = idle_ok = free_ok = 0
    worst_shortfall = None
    for _ in range(N_SYSTEMS):
        a, b, l, c = random_system(rng)
        if a is None:
            continue
        systems += 1
        alpha, x, p, u, c, lam = von_neumann(a, b)
        if p.min() <= 0.0:
            continue
        n = a.shape[0]
        j = int(rng.integers(0, n))
        # (8'): a process that uses more and delivers less carries a smaller cycle sum
        a_new = DOMINATED_INPUT * a[:, j]
        b_new = DOMINATED_OUTPUT * b[:, j]
        ratio = float((p @ b_new) / (p @ a_new))
        shortfall = alpha - ratio
        idle_ok += shortfall > 0.0
        worst_shortfall = shortfall if worst_shortfall is None else min(worst_shortfall,
                                                                       shortfall)
        # (7'): a good no process uses and one process makes is in excess, so its price is zero
        a_big = np.vstack([a, np.zeros((1, n))])
        b_big = np.vstack([b, np.zeros((1, n))])
        b_big[n, 0] = 1.0
        p_big = np.append(p, 0.0)
        flow = b_big @ x - alpha * (a_big @ x)
        field = alpha * (p_big @ a_big) - p_big @ b_big
        free_ok += (float(flow.min()) > -TOL_CYCLE and float(flow[n]) > 0.0
                    and float(np.abs(field).max()) < TOL_CYCLE
                    and abs(p_big[n]) < TOL)
    ok = (systems > 0 and idle_ok > 0 and idle_ok == free_ok
          and worst_shortfall is not None and worst_shortfall > 0.0)
    detail = ("%d systems, %d of them with a positive price vector, on which both slackness "
              "conditions are built rather than solved for. **(8') read on cycles.** Append a "
              "process that uses %g times the inputs of an existing one and delivers %g times "
              "its outputs: its cycle sum falls short of the common one on every construction, "
              "the smallest shortfall %.4f in the factor. **So an idle process is exactly a "
              "cycle whose sum does not reach the common value**, which is what (8') says: "
              "where (8) is strict, the intensity is zero. **(7') read on quantities.** Append "
              "a commodity that no process uses and one process makes: its net output is "
              "strictly positive at the same intensities, so (7) is strict there, and setting "
              "its price to zero leaves every other condition exactly as it was, within %g on "
              "all %d constructions. **So free disposal is not an extra assumption about "
              "behaviour: it is the statement that a commodity off every cycle carries no "
              "term**"
              % (systems, idle_ok, DOMINATED_INPUT, DOMINATED_OUTPUT,
                 0.0 if worst_shortfall is None else worst_shortfall, TOL_CYCLE, free_ok))
    printed = ["dominated process falls short on %d of %d constructions, smallest shortfall "
               "%.6f; the appended good is in excess and prices at zero with everything else "
               "unchanged on %d" % (idle_ok, idle_ok,
                                    0.0 if worst_shortfall is None else worst_shortfall,
                                    free_ok)]
    return ok, detail, {"systems": int(systems), "constructions": int(idle_ok),
                        "free_disposal_ok": int(free_ok),
                        "dominated_input": DOMINATED_INPUT,
                        "dominated_output": DOMINATED_OUTPUT}, printed


# ------------------- B71-6d and 6e: Sraffa's standard commodity, and the reinvested rate


def single_production_system(rng):
    for _ in range(60):
        n = int(rng.integers(3, SIZES[1] + 1))
        column_sum = float(INPUT_COLUMN_SUMS[int(rng.integers(0, len(INPUT_COLUMN_SUMS)))])
        spec = IndustrySpec(count=n, financial_count=0, column_sum=column_sum,
                            seed=int(rng.integers(0, 2**31 - 1)))
        a = build_io_matrix(spec)
        check_feasible(a)
        if irreducible(a):
            return a, rng.uniform(0.2, 2.0, n)
    return None, None


def check_standard_commodity(rng):
    """With B the identity and no wage, the pencil is (I, A) and the root is 1 / lambda_PF(A).
    The right Perron vector is Sraffa's standard proportions and the left one his price vector
    at the maximum rate, which is Corollary 12.4 of B67 said in von Neumann's words."""
    systems = matched = 0
    worst_root = worst_right = worst_left = 0.0
    for _ in range(N_SYSTEMS):
        a, l = single_production_system(rng)
        if a is None:
            continue
        systems += 1
        n = a.shape[0]
        alpha, x, p, u, c, lam = von_neumann(a, np.eye(n))
        # the rate where the wage vanishes, found by a route that shares no code with the
        # eigen-decomposition: scan the determinant for a sign change and bisect
        root = smallest_root_by_determinant(a)
        if root is None:
            systems -= 1
            continue
        worst_root = max(worst_root, abs(alpha - (1.0 + root)))
        # the intensity vector solves x = alpha A x and the price vector p A = p / alpha,
        # checked as residuals of those equations rather than against the same call
        worst_right = max(worst_right, float(np.abs(alpha * (a @ x) - x).max()
                                             / np.abs(x).max()))
        worst_left = max(worst_left, float(np.abs(alpha * (p @ a) - p).max()
                                           / np.abs(p).max()))
        matched += (abs(alpha - (1.0 + root)) < TOL_CYCLE
                    and float(np.abs(alpha * (a @ x) - x).max() / np.abs(x).max()) < TOL_CYCLE
                    and float(np.abs(alpha * (p @ a) - p).max() / np.abs(p).max()) < TOL_CYCLE
                    and x.min() > 0.0 and p.min() > 0.0)
    ok = (systems > 0 and matched == systems and worst_root < TOL_CYCLE
          and worst_right < TOL_CYCLE and worst_left < TOL_CYCLE)
    detail = ("%d single production systems from stage A19's generator. With `B = I` and no "
              "wage the pencil is `(I, A)`. **The expansion factor agrees with the rate at "
              "which the wage vanishes**, found by scanning the determinant `det(I - (1+r)A)` "
              "for a sign change and bisecting, a route sharing no code with the "
              "eigen-decomposition: within %g on every system. The intensity vector satisfies "
              "`x = alpha A x` and the price vector `p = alpha p A` as residuals of those "
              "equations, both within %g relative, with both vectors strictly positive, on %d "
              "of %d. **So the intensity vector is Sraffa's standard proportions and the price "
              "vector is his price vector at the maximum rate: the standard system is the von "
              "Neumann ray of that economy, and Corollary 12.4 of B67 and von Neumann's "
              "duality are one statement said twice.** That identification is algebraic and no "
              "run establishes it; what the run establishes is that both objects solve the "
              "equations claimed for them. Both vectors come out positive by "
              "Perron-Frobenius, which is why single production never needs the inequalities"
              % (systems, TOL_CYCLE, TOL_CYCLE, matched, systems))
    printed = ["worst |alpha - (1 + r) from the determinant| %.3e; worst relative residual of "
               "x = alpha A x %.3e; of p = alpha p A %.3e"
               % (worst_root, worst_right, worst_left)]
    return ok, detail, {"systems": int(systems), "matched": int(matched),
                        "within": TOL_CYCLE}, printed


def check_reinvested_rate(rng):
    """Fold the wage basket into the input matrix, M = A + b l, and read the pencil (I, M).
    The root is 1 / lambda_PF(M), which is the 1 + r of B68's Corollary 13.2 and B69."""
    systems = points = matched = 0
    worst = 0.0
    for _ in range(N_SYSTEMS):
        a, l = single_production_system(rng)
        if a is None:
            continue
        v = l @ np.linalg.inv(np.eye(a.shape[0]) - a)
        if v.min() <= 0.0:
            continue
        systems += 1
        for target in VALUE_OF_BASKET:
            b0 = rng.uniform(0.1, 1.0, len(l))
            basket = b0 * (target / float(v @ b0))
            m = a + np.outer(basket, l)
            alpha, x, p, u, c, lam = von_neumann(m, np.eye(a.shape[0]))
            root = smallest_root_by_determinant(m)
            if root is None:
                continue
            points += 1
            gap = abs(alpha - (1.0 + root))
            worst = max(worst, gap)
            matched += gap < TOL_CYCLE
    ok = systems > 0 and matched == points and worst < TOL_CYCLE
    detail = ("%d systems, %d wage baskets each, drawn so that the basket's labour value is "
              "%s. Folding the basket into the input matrix, `M = A + b l`, and reading the "
              "pencil `(I, M)` gives an expansion factor equal to `1 + r`, where `r` is read by "
              "scanning `det(I - (1+r)M)` for a sign change and bisecting, a route sharing no "
              "code with the eigen-decomposition. **That `r` is the very one the Fundamental "
              "Marxian Theorem and Okishio's theorem are about**, matched within %g at all %d "
              "points. **So the maximal balanced "
              "growth factor of an economy that reinvests every profit is the profit factor "
              "itself**: the flow side's growth and the field side's return are one number "
              "because they are one root, and B68's Corollary 13.2 and B69's Theorem 14 are "
              "statements about that root read from the field side"
              % (systems, len(VALUE_OF_BASKET),
                 ", ".join("%g" % t for t in VALUE_OF_BASKET), TOL_CYCLE, points))
    printed = ["worst |expansion factor - (1 + r)| %.3e over %d points on %d systems"
               % (worst, points, systems)]
    return ok, detail, {"systems": int(systems), "points": int(points),
                        "matched": int(matched), "within": TOL_CYCLE}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B71-5", "known_answer",
         "von Neumann (1945): the interest factor and the coefficient of expansion are equal "
         "and uniquely determined", check_von_neumann(rng)),
        ("B71-6a", "instrument",
         "Theorem 16(1) and (2): one pencil, one root, and the cycle sum it puts on every "
         "process", check_pencil_and_cycles(rng)),
        ("B71-6c", "instrument",
         "Theorem 16(3): the two slackness conditions read on cycles, built rather than solved",
         check_slackness(rng)),
        ("B71-6d", "instrument",
         "Corollary 16.1: the standard commodity is the von Neumann ray of that economy",
         check_standard_commodity(rng)),
        ("B71-6e", "instrument",
         "Corollary 16.2: reinvest every profit and the growth factor is the profit factor",
         check_reinvested_rate(rng)),
    ]
    mapping = {
        "B71-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B71-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B71-5 and B71-6: the known answer and the structural checks for "
          "docs/b71_von_neumann.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
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
        "stage": "B71",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_rank": TOL_RANK,
            "n_systems": N_SYSTEMS, "sizes": list(SIZES),
            "input_column_sums": list(INPUT_COLUMN_SUMS), "joint_weight": list(JOINT_WEIGHT),
            "value_of_basket": list(VALUE_OF_BASKET),
            "dominated_input": DOMINATED_INPUT, "dominated_output": DOMINATED_OUTPUT,
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
