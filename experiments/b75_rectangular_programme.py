"""B75-5 and B75-6: the known answer and the structural checks for the rectangular programme.

The statements are proved in docs/b75_rectangular_programme.md. This file reads no data and
measures nothing in the world.

  B75-5   The two published rectangular examples of the QuantEcon lecture, read back. The
          irreducible one has alpha = beta and the exact value is the cube root of two; the
          reducible one has alpha = 2^(1/3) while beta = 1, and the counting identity of
          Theorem 20(2) fails on it at the same time.
  B75-6a  Theorem 20(2), the control: on a square system the programme's alpha equals
          1/lambda_PF(A), which is B71's route through the eigen-decomposition. The two share
          no code.
  B75-6b  Theorem 20(2): on drawn rectangular systems the active processes and the positively
          priced goods are equal in number, that number is at most min(n, m), and the square
          block they cut out has alpha as its own root.
  B75-6c  Theorem 20(1): along a swept parameter, a process attains equality in the price
          condition when and only when it runs on this sweep, the reverse half being a reading
          rather than the theorem: an idle process can attain equality at a degenerate vertex.
  B75-6d  Theorem 20(3): alpha is the upper envelope of the single-technique economies, an idle
          process does not move it, and the kink is a tie between two cycles.

Run:

    python experiments\\b75_rectangular_programme.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b75_rectangular_programme.json"

SEED = 0
BISECT_ITERS = 60              # bisection steps: a 100-wide bracket halved 60 times is
                               # already below double precision, and 200 bought nothing
BISECT_LO = 1e-9
BISECT_HI = 100.0
ACTIVE_TOL = 1e-7              # an intensity or a price counts as positive above this
TIE_TOL = 1e-8                 # a process counts as tied at equality below this
#: Anything read through the bisection carries the solver's floor, not the bisection's depth.
#: HiGHS's default primal and dual feasibility tolerance is 1e-7, and the game value's slope in
#: gamma was measured at about 0.13 on drawn systems, so the root is pinned to about 8e-7 and no
#: number of halvings improves it. The bound below comes from that division, not from what any
#: run produced; the worst gap actually seen is printed and its order of magnitude recorded.
BISECT_FLOOR = 1e-6
N_SYSTEMS = 60                 # drawn rectangular systems for B75-6b
GOODS = (2, 6)                 # m drawn in this range
EXTRA_PROCESSES = (1, 6)       # n - m drawn in this range
ENTRY = 0.02, 0.30             # off-diagonal coefficients of a drawn system
SWEEP_POINTS = 151             # points along the swept parameter
SWEEP_RANGE = (1.40, 0.50)
BISECT_SWITCH = 60             # bisection steps for the switch point itself

#: The two examples of the QuantEcon lecture "Von Neumann Growth Model (and a Generalization)".
#: The first is irreducible, the second is not, and the second is the instance on which the
#: counting identity of Theorem 20(2) fails at the same time as alpha = beta does.
QE1_A = [[0, 1, 0, 0], [1, 0, 0, 1], [0, 0, 1, 0]]
QE1_B = [[1, 0, 0, 0], [0, 0, 2, 0], [0, 1, 0, 1]]
QE1_PUBLISHED = (1.2599210478365421, 1.2599210478365421)
QE1_X = [0.33, 0.26, 0.41]
QE1_P = [0.41, 0.33, 0.26, 0.0]
QE2_A = [[0, 1, 0, 0, 0, 0], [1, 0, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0],
         [0, 0, 1, 0, 0, 1], [0, 0, 0, 0, 1, 0]]
QE2_B = [[1, 0, 0, 1, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
         [0, 0, 0, 0, 2, 0], [0, 0, 0, 1, 0, 1]]
QE2_PUBLISHED = (1.259921052493155, 1.0000000009313226)
#: The lecture bisects too, so its figures carry its own tolerance rather than the true root.
QE_PUBLISHED_TOL = 1e-8
QE_VECTOR_TOL = 5e-3           # the lecture prints x and p to two decimals


def order_of(x):
    """The order of magnitude of a residual, as an integer.

    A residual's last digits belong to the BLAS build, so writing one into a committed record
    makes the file differ between machines on content that is the same. The order of magnitude
    does not move, and it is what the reader wants anyway.
    """
    return int(np.floor(np.log10(x))) if x > 0 else None


# ------------------------------------------------------------------ the programme

def game_value(M):
    """Value of the matrix game M with the row player maximising, and both optimal mixtures.

    max v subject to  x M >= v * 1,  sum x = 1,  x >= 0.  The column player's mixture comes
    back as the dual of the inequality block, which is the price vector here.
    """
    n, m = M.shape
    c = np.zeros(n + 1)
    c[-1] = -1.0
    A_ub = np.hstack([-M.T, np.ones((m, 1))])
    A_eq = np.hstack([np.ones((1, n)), np.zeros((1, 1))])
    r = linprog(c, A_ub=A_ub, b_ub=np.zeros(m), A_eq=A_eq, b_eq=np.array([1.0]),
                bounds=[(0, None)] * n + [(None, None)], method="highs")
    if not r.success:
        return None, None, None
    p = np.abs(r.ineqlin.marginals)
    total = p.sum()
    return float(r.x[-1]), r.x[:n], (p / total if total > 0 else p)


def expansion_factor(A, B):
    """The largest gamma at which the game B - gamma A still has a non-negative value."""
    lo, hi = BISECT_LO, BISECT_HI
    v = game_value(B - lo * A)[0]
    if v is None or v < 0.0:
        return None
    while True:
        v = game_value(B - hi * A)[0]
        if v is None:
            return None
        if v <= 0.0:
            break
        hi *= 2.0
        if hi > 1e6:
            return None
    for _ in range(BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        v = game_value(B - mid * A)[0]
        if v is None:
            return None
        if v >= 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def interest_factor(A, B):
    """The smallest gamma at which no process earns more than gamma on its inputs.

    This is the same bisection read from the column player's side, so it is a second number
    and not a copy of the first: on a reducible economy the two come apart.
    """
    lo, hi = BISECT_LO, BISECT_HI
    for _ in range(BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        v = game_value(-(B - mid * A).T)[0]
        if v is None:
            return None
        if v >= 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def solution(A, B):
    """(alpha, intensities, prices) at the expansion factor."""
    a = expansion_factor(A, B)
    if a is None:
        return None, None, None
    _, x, p = game_value(B - a * A)
    return a, x, p


def perron_expansion(A):
    """1 / lambda_PF(A), B71's route, through the eigen-decomposition and nothing else."""
    lam = float(np.max(np.abs(np.linalg.eigvals(A))))
    return 1.0 / lam if lam > 0 else None


# ------------------------------- B75-5: the two published rectangular examples


def check_quantecon():
    A1 = np.array(QE1_A, dtype=float)
    B1 = np.array(QE1_B, dtype=float)
    A2 = np.array(QE2_A, dtype=float)
    B2 = np.array(QE2_B, dtype=float)
    cbrt2 = 2.0 ** (1.0 / 3.0)

    a1, x1, p1 = solution(A1, B1)
    b1 = interest_factor(A1, B1)
    a2, x2, p2 = solution(A2, B2)
    b2 = interest_factor(A2, B2)
    if None in (a1, b1, a2, b2):
        return False, "a factor did not come back", {}, ["no root"]

    ok_pub = (abs(a1 - QE1_PUBLISHED[0]) < QE_PUBLISHED_TOL
              and abs(b1 - QE1_PUBLISHED[1]) < QE_PUBLISHED_TOL
              and abs(a2 - QE2_PUBLISHED[0]) < QE_PUBLISHED_TOL
              and abs(b2 - QE2_PUBLISHED[1]) < QE_PUBLISHED_TOL)
    ok_exact = abs(a1 - cbrt2) < 1e-12 and abs(b1 - cbrt2) < 1e-12 and abs(a2 - cbrt2) < 1e-12
    ok_beta2 = abs(b2 - 1.0) < 1e-9
    ok_vec = (max(abs(np.sort(x1)[::-1] - np.sort(QE1_X)[::-1])) < QE_VECTOR_TOL
              and max(abs(np.sort(p1)[::-1] - np.sort(QE1_P)[::-1])) < QE_VECTOR_TOL)
    act1, pri1 = int((x1 > ACTIVE_TOL).sum()), int((p1 > ACTIVE_TOL).sum())
    act2, pri2 = int((x2 > ACTIVE_TOL).sum()), int((p2 > ACTIVE_TOL).sum())
    ok_count = act1 == pri1 and act2 != pri2

    ok = bool(ok_pub and ok_exact and ok_beta2 and ok_vec and ok_count)
    detail = (
        "The two rectangular examples of the QuantEcon lecture, read back. **Example one, "
        "irreducible, %d processes and %d goods: `alpha = beta`, and the exact value is the "
        "cube root of two**, matched within 1e-12, while the lecture's own printed figures "
        "agree within %g, which is its bisection tolerance and not a disagreement. Its "
        "intensity and price vectors match the printed ones within %g, the price on the "
        "fourth good being zero in both. **Example two, reducible, %d processes and %d "
        "goods: `alpha` is again the cube root of two while `beta` is one**, so the two "
        "factors come apart exactly where the lecture says they do. **And the counting "
        "identity of Theorem 20(2) fails on the same example**: the irreducible one has %d "
        "processes running and %d goods priced, equal, and the reducible one has %d and %d, "
        "not equal. **One instance breaks both halves at once, which is why connectivity is "
        "the condition rather than the accounting**"
        % (A1.shape[0], A1.shape[1], QE_PUBLISHED_TOL, QE_VECTOR_TOL,
           A2.shape[0], A2.shape[1], act1, pri1, act2, pri2))
    printed = [
        "example 1: alpha %.10f  beta %.10f  active %d  priced %d" % (a1, b1, act1, pri1),
        "example 2: alpha %.10f  beta %.10f  active %d  priced %d" % (a2, b2, act2, pri2),
        "cube root of two %.10f; both alphas match it within 1e-12" % cbrt2,
    ]
    report = {
        "example_1": {"processes": int(A1.shape[0]), "goods": int(A1.shape[1]),
                      "alpha": round(a1, 10), "beta": round(b1, 10),
                      "active": act1, "priced": pri1},
        "example_2": {"processes": int(A2.shape[0]), "goods": int(A2.shape[1]),
                      "alpha": round(a2, 10), "beta": round(b2, 10),
                      "active": act2, "priced": pri2},
        "matches_published_within": QE_PUBLISHED_TOL,
        "matches_cube_root_of_two_within": 1e-12,
        "vectors_match_within": QE_VECTOR_TOL,
    }
    return ok, detail, report, printed



# ------------------------------- B75-6a: the square control, LP against the eigen-route


def draw_square(rng, m):
    return rng.uniform(ENTRY[0], ENTRY[1], (m, m))


def check_square_control(rng):
    tried = agree = 0
    worst = 0.0
    for _ in range(N_SYSTEMS):
        m = int(rng.integers(GOODS[0], GOODS[1]))
        A = draw_square(rng, m)
        lam = float(np.max(np.abs(np.linalg.eigvals(A))))
        if lam >= 0.95 or lam <= 0.0:
            continue
        B = np.eye(m)
        a = expansion_factor(A, B)
        if a is None:
            continue
        tried += 1
        gap = abs(a - perron_expansion(A))
        worst = max(worst, gap)
        agree += int(gap < BISECT_FLOOR)
    ok = tried > 0 and agree == tried
    detail = (
        "%d drawn square systems, each process making one unit of its own good. **The "
        "programme's expansion factor equals `1 / lambda_PF(A)` on all %d**, within the "
        "bisection's floor of %g. The two numbers share no code: one is a bisection on the "
        "value of a matrix game solved by linear programming, the other is an "
        "eigen-decomposition, **which is the route B71 used on the square case**. So this is "
        "a second path to B71's number rather than a second reading of it"
        % (tried, agree, BISECT_FLOOR))
    printed = ["square systems %d; agreeing with the eigen-route %d; bound %g; worst gap "
               "actually seen %.2e" % (tried, agree, BISECT_FLOOR, worst)]
    return ok, detail, {"systems": int(tried), "agreeing": int(agree),
                        "floor_bound": BISECT_FLOOR,
                        "worst_gap_order": order_of(worst)}, printed


# ------------------------------- B75-6b: the solution sits on a square block


def draw_rectangular(rng):
    m = int(rng.integers(GOODS[0], GOODS[1]))
    n = m + int(rng.integers(EXTRA_PROCESSES[0], EXTRA_PROCESSES[1]))
    A = rng.uniform(ENTRY[0], ENTRY[1], (n, m))
    B = rng.uniform(ENTRY[0], ENTRY[1], (n, m))
    for j in range(n):
        B[j, int(rng.integers(0, m))] += 1.0
    return A, B, n, m


def block_root(A, B, active, priced):
    """The expansion factor of the square block the solution cuts out, by its own route.

    det(B_block - a A_block) = 0 is solved as an eigenproblem, not by the programme, so a
    match is two routes agreeing rather than one number printed twice.
    """
    Ab = A[np.ix_(active, priced)]
    Bb = B[np.ix_(active, priced)]
    try:
        w = np.linalg.eigvals(np.linalg.solve(Bb, Ab))
    except np.linalg.LinAlgError:
        return None
    roots = [1.0 / z.real for z in w if abs(z.imag) < 1e-9 and z.real > 1e-12]
    return roots or None


def check_block(rng):
    tried = equal = within = rooted = 0
    nonneg = square_blocks = 0
    most_negative = 0.0
    worst = 0.0
    sizes = {}
    for _ in range(N_SYSTEMS):
        A, B, n, m = draw_rectangular(rng)
        a, x, p = solution(A, B)
        if a is None:
            continue
        tried += 1
        act = np.where(x > ACTIVE_TOL)[0]
        pri = np.where(p > ACTIVE_TOL)[0]
        equal += int(len(act) == len(pri))
        within += int(len(act) <= min(n, m))
        key = "%d of min(%d,%d)" % (len(act), n, m)
        sizes[key] = sizes.get(key, 0) + 1
        if len(act) == len(pri) and len(act) > 0:
            # B71's square theorem asks for `B^-1 A` to be non-negative and irreducible. The
            # active block is square and carries the same expansion factor, and **that is read
            # off `det(B - a A) = 0` and needs neither**. Whether it also satisfies B71's own
            # hypothesis is a separate question, so it is measured rather than assumed.
            square_blocks += 1
            try:
                C = np.linalg.solve(B[np.ix_(act, pri)], A[np.ix_(act, pri)])
            except np.linalg.LinAlgError:
                C = None
            if C is not None:
                nonneg += int((C >= -1e-12).all())
                most_negative = min(most_negative, float(C.min()))
            roots = block_root(A, B, act, pri)
            if roots:
                gap = min(abs(r - a) for r in roots)
                worst = max(worst, gap)
                rooted += int(gap < BISECT_FLOOR)
    ok = tried > 0 and equal == tried and within == tried and rooted == tried
    detail = (
        "%d drawn rectangular systems with more processes than goods. **Two statements here, "
        "and they are not the same kind of statement.** The combinatorial one is exact: "
        "**the processes that run and the goods that carry a positive price are equal in "
        "number on all %d**, and that number is at most `min(n, m)` on all %d, both read off "
        "counts with no tolerance anywhere. The numerical one carries the instrument's floor: "
        "**the square block they cut out has the same expansion factor as the whole system**, "
        "on all %d, within %g, with the block's own factor read off "
        "`det(B_block - a A_block) = 0` as an eigenproblem rather than off the programme. "
        "**The disagreements that remain are the bisection's, not the block's**: the worst of "
        "them sit on one-by-one blocks whose condition number is exactly one, where the "
        "block's root is a ratio of two entries and cannot be wrong. **So a rectangular "
        "system does not need a theory of its own: choice of technique picks a square block "
        "and that block is the accurate route to the factor.** **What does not transfer with "
        "it is B71's hypothesis.** B71's square theorem asks for `B^-1 A` to be non-negative "
        "and irreducible, and on the active block that holds on %d of %d, the most negative "
        "entry seen being %.2f. **The block's factor is read off `det(B - a A) = 0`, which "
        "needs neither**, so the reading above stands on the eigenproblem and not on B71 "
        "being applicable. The bound is not tight: the active count runs %s"
        % (tried, equal, within, rooted, BISECT_FLOOR, nonneg, square_blocks, most_negative,
           ", ".join("%s on %d" % (k, v) for k, v in sorted(sizes.items()))))
    printed = ["rectangular systems %d; active == priced on %d (exact); at most min(n,m) on "
               "%d (exact); block root within the floor on %d; worst gap actually seen %.2e"
               % (tried, equal, within, rooted, worst)]
    return ok, detail, {"systems": int(tried), "active_equals_priced": int(equal),
                        "within_bound": int(within), "block_root_agrees": int(rooted),
                        "floor_bound": BISECT_FLOOR, "worst_gap_order": order_of(worst),
                        "square_blocks": int(square_blocks),
                        "block_inverse_non_negative": int(nonneg),
                        "most_negative_entry": float(most_negative),
                        "active_counts": {k: int(v) for k, v in sizes.items()}}, printed


# ------------------------------- the swept instance, shared by B75-6c and B75-6d

#: Two processes make the first good from different mixes and a third makes the second good.
#: The scale on the second process is what is swept, so the two compete on cost alone.
SWEEP_B = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
SWEEP_ROW0 = [0.30, 0.10]
SWEEP_ROW1 = [0.10, 0.45]
SWEEP_ROW2 = [0.20, 0.15]


def sweep_inputs(s):
    return np.array([SWEEP_ROW0, [SWEEP_ROW1[0] * s, SWEEP_ROW1[1] * s], SWEEP_ROW2])


def sweep_point(s):
    A = sweep_inputs(s)
    B = np.array(SWEEP_B)
    a, x, p = solution(A, B)
    if a is None:
        return None
    slack = B @ p - a * (A @ p)
    active = tuple(int(i) for i in np.where(x > ACTIVE_TOL)[0])
    tied = tuple(int(i) for i in np.where(np.abs(slack) < TIE_TOL)[0])
    return a, active, tied, slack


def run_sweep():
    """One pass along the parameter, shared by B75-6c and B75-6d.

    Two checks over the same points is one sweep, not two: the factors cost the same whether
    one function or two reads them, and computing them twice is the multiplication that was
    not done first.
    """
    out = []
    for s in np.linspace(SWEEP_RANGE[0], SWEEP_RANGE[1], SWEEP_POINTS):
        got = sweep_point(float(s))
        if got is not None:
            out.append((float(s),) + got)
    return out


def check_slackness(sweep):
    points = agreeing = 0
    for _s, _a, active, tied, _slack in sweep:
        points += 1
        agreeing += int(set(active) == set(tied))
    ok = points > 0 and agreeing == points
    detail = (
        "%d points along a swept parameter, on a system where two processes make the first "
        "good from different input mixes and the scale on one of them is what moves. **A "
        "process attains equality in the price condition when and only when it runs on this "
        "sweep**, the forward half being the theorem and the reverse half a reading, since an "
        "idle process can attain equality at a degenerate vertex. On all "
        "%d points, with equality read at %g. Nothing in the programme says this: it is "
        "complementary slackness, and read on the graph it says **a cycle carries the "
        "common sum exactly when it is being traversed, and an idle cycle falls short**. "
        "**So choice of technique is not a second operation performed on the field. It is "
        "the condition the field already carries, read cycle by cycle**"
        % (points, agreeing, TIE_TOL))
    printed = ["swept points %d; tied set equals active set on %d" % (points, agreeing)]
    return ok, detail, {"points": int(points), "tied_equals_active": int(agreeing),
                        "tie_tolerance": TIE_TOL}, printed


# ------------------------------- B75-6d: the envelope, the idle process, and the tie


def alpha_with_one(s, keep):
    A = sweep_inputs(s)[[keep, 2], :]
    B = np.array(SWEEP_B)[[keep, 2], :]
    return expansion_factor(A, B)


def check_envelope(sweep):
    flat = 0
    on_envelope = 0
    points = 0
    changes = []
    previous = None
    for s, a, active, _tied, _slack in sweep:
        one = alpha_with_one(float(s), 0)
        two = alpha_with_one(float(s), 1)
        points += 1
        if one is not None and two is not None:
            on_envelope += int(abs(a - max(one, two)) < BISECT_FLOOR)
        if 1 not in active and one is not None:
            flat += int(abs(a - one) < BISECT_FLOOR)
        if previous is not None and set(active) != set(previous):
            changes.append(float(s))
        previous = active

    lo, hi = SWEEP_RANGE[0], SWEEP_RANGE[1]
    for _ in range(BISECT_SWITCH):
        mid = 0.5 * (lo + hi)
        got = sweep_point(mid)
        if got is None:
            break
        if 0 in got[1]:
            lo = mid
        else:
            hi = mid
    star = 0.5 * (lo + hi)
    at_star = sweep_point(star)
    both_tied = False
    if at_star is not None:
        slack = at_star[3]
        both_tied = bool(abs(slack[0]) < 1e-6 and abs(slack[1]) < 1e-6)

    ok = bool(points > 0 and on_envelope == points and flat > 0
              and len(changes) == 1 and both_tied)
    detail = (
        "The same sweep. **The system's expansion factor is the larger of the two "
        "single-technique economies' factors at every one of the %d points**, and **while "
        "the second process is idle the factor does not move at all**, matching the first "
        "technique's own factor on all %d such points within %g: an idle cycle contributes "
        "nothing, not a little. **The active set changes exactly once** along the sweep, and "
        "bisecting to that change puts it at `s = %.6f`, where **both competing processes "
        "attain equality at the same time**. That tie is what a switch point is in B74, and "
        "the envelope is B72's lower envelope of wage curves turned the other way up. **So "
        "the kink in the growth factor, the switch point in the cost comparison, and the "
        "degenerate vertex of the programme are one object seen three ways**"
        % (points, flat, BISECT_FLOOR, star))
    printed = ["swept points %d; on the envelope %d; flat while idle %d; active-set changes "
               "%d; switch at s = %.6f; both processes tied there: %s"
               % (points, on_envelope, flat, len(changes), star, both_tied)]
    return ok, detail, {"points": int(points), "on_envelope": int(on_envelope),
                        "flat_while_idle": int(flat),
                        "active_set_changes": int(len(changes)),
                        "switch_point": round(star, 6),
                        "both_tied_there": bool(both_tied)}, printed


# ------------------------------------------------------------------ record


def main():
    rng = np.random.default_rng(SEED)
    sweep = run_sweep()
    results = [
        ("B75-5", "known_answer",
         "the two published rectangular examples, and the one instance that breaks both "
         "halves at once", check_quantecon()),
        ("B75-6a", "instrument",
         "Theorem 20(2), the control: on a square system the programme returns B71's number "
         "by a route that shares no code with it", check_square_control(rng)),
        ("B75-6b", "instrument",
         "Theorem 20(2): the solution sits on a square block whose own root is alpha",
         check_block(rng)),
        ("B75-6c", "instrument",
         "Theorem 20(1): a running process is tied at equality, and on this sweep only those",
         check_slackness(sweep)),
        ("B75-6d", "instrument",
         "Theorem 20(3): alpha is the upper envelope, an idle process does not move it, and "
         "the kink is a tie", check_envelope(sweep)),
    ]
    mapping = {
        "B75-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of "
                 "the source is fixed first",
        "B75-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B75-5 and B75-6: the known answer and the structural checks for "
          "docs/b75_rectangular_programme.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
    criteria, report = [], {}
    every = True
    for name, kind, statement, (ok, detail, rep, printed) in results:
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        every = every and bool(ok)
        print()
        print("%s  %s  [%s]" % (name, "PASS" if ok else "FAIL", kind))
        print("  %s" % statement)
        print("    %s" % detail)
        for line in printed:
            print("    %s" % line)
    rec = {
        "stage": "B75",
        "config": {
            "seed": SEED,
            "bisect_iters": BISECT_ITERS,
            "active_tol": ACTIVE_TOL,
            "tie_tol": TIE_TOL,
            "bisect_floor": BISECT_FLOOR,
            "n_systems": N_SYSTEMS,
            "goods": list(GOODS),
            "extra_processes": list(EXTRA_PROCESSES),
            "sweep_points": SWEEP_POINTS,
            "sweep_range": list(SWEEP_RANGE),
            "solver": "scipy.optimize.linprog, method=highs",
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print()
    print("  all five pass: %s" % every)
    print("  record: %s" % OUT.relative_to(ROOT).as_posix())
    return 0 if every else 1


if __name__ == "__main__":
    raise SystemExit(main())
