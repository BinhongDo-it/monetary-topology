"""B70-5 and B70-6: the known answer and the structural checks for joint production.

The statements are proved in docs/b70_joint_production.md. This file reads no data and
measures nothing in the world.

  B70-5   Steedman (1975), Economic Journal 85(337), 114-123: a two-process, two-commodity
          joint production system with a positive rate of profits, positive prices, one
          negative labour value and a negative aggregate surplus value. Every number in that
          example is read back here.
  B70-6a  Theorem 15(1): with the sale leg carrying the whole output bundle, equal cycle sums
          are the price equations, exactly as in B67 under single production. The identity is
          algebraic and holds at any signs; the logarithmic form needs both legs positive, and
          the fraction where that fails is reported rather than filtered away.
  B70-6b  Theorem 15(2): the drawn graph has b1 = n, one independent cycle per process, whatever
          the commodity count m is. n = m is the square assumption, n < m leaves the price
          vector undetermined on a subspace of dimension m - n, and n > m makes the price
          equations inconsistent.
  B70-6c  Theorem 15(3): a negative labour value implies the activity vector producing one net
          unit of that commodity alone has a negative component, so that unit is not a feasible
          net output; and a non-negative inverse gives strictly positive values.
  B70-6d  How many rates of profit carry a positive price vector. Under single production there
          is exactly one; under joint production there can be more.
  B70-6e  Corollary 15.1: fixed capital as joint production, with the machine's age as a
          position. The depreciation schedule is a coordinate of the field: straight-line at
          r = 0 and not straight-line at any positive rate.

Run:

    python experiments\\b70_joint_production.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b70_joint_production.json"

SEED = 0
TOL = 1e-12          # identities that are the same floating point operations on both sides
TOL_CYCLE = 1e-10    # sums of logarithms, where the two legs are computed differently
TOL_RANK = 1e-9      # singular values below this count as zero
N_SYSTEMS = 400
SIZES = (2, 6)
INPUT_COLUMN_SUMS = (0.3, 0.5, 0.7)
JOINT_WEIGHT = (0.0, 0.8)      # how much of a process's output is the other commodities
R_FRACTIONS = (0.0, 0.1, 0.25, 0.5, 0.75)
RATE_GRID = 200                # probes on [0, RATE_MAX] when counting positive-price rates
RATE_MAX = 3.0
FIXED_T = 5                    # the machine lasts this many periods
FIXED_PARAMS = {"q": 1.0, "a": 0.2, "c": 0.5, "l0": 0.3, "l1": 0.1}
FIXED_RATES = (0.0, 0.02, 0.05, 0.10, 0.20)
LINEAR_FLOOR = 1e-6            # below this a schedule would not be distinguishable from linear

# Steedman (1975), p. 115: two processes, two commodities, labour normalised to one per process
STEEDMAN_A = [[5.0, 0.0], [0.0, 10.0]]
STEEDMAN_B = [[6.0, 3.0], [1.0, 12.0]]
STEEDMAN_L = [1.0, 1.0]
STEEDMAN_WAGE_BASKET = [0.5, 5.0 / 6.0]        # the paper prints 0.83 for the second entry
STEEDMAN_VALUES = [-1.0, 2.0]
STEEDMAN_NET = [8.0, 7.0]
STEEDMAN_X = [5.0, 1.0]
STEEDMAN_LABOUR = 6.0
STEEDMAN_WORKERS = [3.0, 5.0]
STEEDMAN_CAPITALISTS = [5.0, 2.0]
STEEDMAN_V = 7.0
STEEDMAN_S = -1.0
STEEDMAN_XW = [9.0, -2.0]
STEEDMAN_XK = [-4.0, 3.0]


def labour_values(a, b, l):
    """v (B - A) = l, so v = l (B - A)^{-1}. Under single production B is the identity and
    this is the usual v = l (I - A)^{-1}."""
    return l @ np.linalg.inv(b - a)


def prices(a, b, l, r, numeraire):
    """p (B - (1 + r) A) = w l, with the given basket priced at one."""
    base = l @ np.linalg.inv(b - (1.0 + r) * a)
    w = 1.0 / float(base @ numeraire)
    return w * base, w


def productive(a, b):
    """There is a non-negative activity vector whose net output is positive in every
    commodity. Sufficient here: (B - A)^{-1} applied to the vector of ones is positive."""
    m = b - a
    if abs(np.linalg.det(m)) < TOL_RANK:
        return False, None
    x = np.linalg.inv(m) @ np.ones(m.shape[0])
    return bool((x > 0.0).all()), x


def random_joint_system(rng):
    """A square system: each process has a main product and may produce the others jointly."""
    n = int(rng.integers(SIZES[0], SIZES[1] + 1))
    column_sum = float(INPUT_COLUMN_SUMS[int(rng.integers(0, len(INPUT_COLUMN_SUMS)))])
    for _ in range(40):
        a = rng.uniform(0.0, 1.0, (n, n))
        a = a / a.sum(axis=0) * column_sum
        joint = rng.uniform(JOINT_WEIGHT[0], JOINT_WEIGHT[1], (n, n))
        np.fill_diagonal(joint, 0.0)
        b = np.eye(n) + joint * rng.uniform(0.0, 1.0, (n, n))
        l = rng.uniform(0.2, 2.0, n)
        ok, _x = productive(a, b)
        if ok and abs(np.linalg.det(b)) > TOL_RANK and abs(np.linalg.det(a)) > TOL_RANK:
            return a, b, l
    return None, None, None


def cycle_legs(a, b, l, p, w, r):
    """Process j's cycle: money -> the input bundle -> the output bundle -> money. The bundle
    costs p a_j and the sale leg returns p b_j - w l_j."""
    cost = p @ a
    back = p @ b - w * l
    return cost, back


def graph_b1(n):
    """The drawn graph: three vertices and three edges per process, plus n - 1 edges holding
    the money vertices at par. b1 = E - V + 1 = n, whatever the commodity count is."""
    vertices = 3 * n
    edges = 3 * n + (n - 1)
    return edges - vertices + 1


def rate_carries_positive_prices(a, b, l, r, tol=0.0):
    """Is there a positive price vector and a positive wage at this rate?"""
    m = b - (1.0 + r) * a
    if abs(np.linalg.det(m)) < TOL_RANK:
        return False
    base = l @ np.linalg.inv(m)
    return bool((base > tol).all())      # base > 0 gives both a positive wage and positive prices


def fixed_capital_system(t, params):
    """A machine that lasts t periods at constant efficiency. Commodity 0 is the good and
    commodity k + 1 is a machine that has been used k times. Process 0 builds a new machine;
    process j uses a machine of age j - 1 and returns it one period older, except the last,
    which scraps it."""
    q, ain, c, l0, l1 = (params["q"], params["a"], params["c"], params["l0"], params["l1"])
    n = t + 1
    a = np.zeros((n, n))
    b = np.zeros((n, n))
    l = np.zeros(n)
    a[0, 0] = c                 # building a machine consumes the good
    b[1, 0] = 1.0               # and delivers a new machine, commodity 1
    l[0] = l0
    for j in range(1, t + 1):
        a[0, j] = ain           # running it consumes the good
        a[j, j] = 1.0           # and a machine of age j - 1, which is commodity j
        b[0, j] = q             # it delivers the good
        if j < t:
            b[j + 1, j] = 1.0   # and the machine one period older
        l[j] = l1
    return a, b, l


# ------------------------------------------ B70-5: Steedman's example, read back


def check_steedman():
    a = np.array(STEEDMAN_A)
    b = np.array(STEEDMAN_B)
    l = np.array(STEEDMAN_L)
    basket = np.array(STEEDMAN_WAGE_BASKET)
    m = b - a
    inv = np.linalg.inv(m)
    v = l @ inv
    y = np.array(STEEDMAN_NET)
    x = inv @ y
    labour = float(l @ x)
    yw = np.array(STEEDMAN_WORKERS)
    yk = np.array(STEEDMAN_CAPITALISTS)
    xw, xk = inv @ yw, inv @ yk
    vv, ss = float(l @ xw), float(l @ xk)
    # the rate: p (B - (1+r) A) = (p b) l, so p (B - b l - (1+r) A) = 0
    c = b - np.outer(basket, l)
    values, vectors = np.linalg.eig((c @ np.linalg.inv(a)).T)
    rates = []
    for k in range(len(values)):
        if abs(values[k].imag) > TOL_RANK:
            continue
        mu = float(values[k].real)
        q = np.real(vectors[:, k])
        if q.sum() < 0:
            q = -q
        if mu > 0.0 and q.min() > 0.0:
            rates.append((mu - 1.0, q / q[0]))
    checks = {
        "values": float(np.abs(v - np.array(STEEDMAN_VALUES)).max()),
        "activity": float(np.abs(x - np.array(STEEDMAN_X)).max()),
        "labour": abs(labour - STEEDMAN_LABOUR),
        "variable_capital": abs(vv - STEEDMAN_V),
        "surplus": abs(ss - STEEDMAN_S),
        "workers_activity": float(np.abs(xw - np.array(STEEDMAN_XW)).max()),
        "capitalists_activity": float(np.abs(xk - np.array(STEEDMAN_XK)).max()),
        "surplus_as_difference": abs((labour - vv) - STEEDMAN_S),
        "net_product": float(np.abs(m @ x - y).max()),
        "basket_scales": float(np.abs(basket * labour - yw).max()),
    }
    worst = max(checks.values())
    ok = worst < TOL_CYCLE and len(rates) >= 1 and rates[0][0] > 0.0
    r0, p0 = (rates[0] if rates else (float("nan"), np.array([float("nan")] * 2)))
    detail = ("Steedman (1975), *Positive Profits with Negative Surplus Value*, Economic Journal "
              "85(337), 114-123, p. 115. Two processes: `5` of commodity 1 and `1` labour give "
              "`6` of commodity 1 and `1` of commodity 2; `10` of commodity 2 and `1` labour "
              "give `3` of commodity 1 and `12` of commodity 2. **Ten published numbers are "
              "read back**, worst gap %.3e: the labour values `(-1, 2)`; the activity levels "
              "`(5, 1)` for the net product `(8, 7)`; total labour `6`; the workers' bundle "
              "`(3, 5)` needing activity `(9, -2)` and so a variable capital of `7`; the "
              "capitalists' bundle `(5, 2)` needing activity `(-4, 3)` and so a surplus value "
              "of `-1`; and the same `-1` again as `L - V`. **The rate of profits comes out "
              "positive, %.4f, with a positive price vector**, so the system has positive "
              "profits and a negative aggregate surplus value at the same time. The wage basket "
              "`(0.5, 5/6)` times the `6` units of labour is the workers' bundle exactly; the "
              "paper prints the second entry rounded to `0.83`"
              % (worst, r0))
    printed = ["worst gap over the ten published numbers %.3e; rate of profits %.6f; "
               "prices relative to commodity 1 %s; positive-price rates found: %d"
               % (worst, r0, np.array2string(p0, precision=4), len(rates)),
               "labour values %s, variable capital %.4f, surplus value %.4f"
               % (np.array2string(v, precision=4), vv, ss)]
    return ok, detail, {"published_numbers": int(len(checks)), "within": TOL_CYCLE,
                        "positive_price_rates": int(len(rates))}, printed


# ------------------------------- B70-6a: equal cycle sums are still the price equations


def check_cycles(rng):
    systems = points = equal = readable = 0
    worst_identity = worst_sum = 0.0
    for _ in range(N_SYSTEMS):
        a, b, l = random_joint_system(rng)
        if a is None:
            continue
        systems += 1
        n = a.shape[0]
        numeraire = np.ones(n)
        for f in R_FRACTIONS:
            r = f
            m = b - (1.0 + r) * a
            if abs(np.linalg.det(m)) < TOL_RANK:
                continue
            p, w = prices(a, b, l, r, numeraire)
            cost, back = cycle_legs(a, b, l, p, w, r)
            points += 1
            worst_identity = max(worst_identity, float(np.abs(back - (1.0 + r) * cost).max()))
            if cost.min() > 0.0 and back.min() > 0.0:
                readable += 1
                sums = np.log(back) - np.log(cost)
                gap = float(np.abs(sums - math.log1p(r)).max())
                worst_sum = max(worst_sum, gap)
                equal += gap < TOL_CYCLE
    ok = (systems > 0 and readable > 0 and equal == readable
          and worst_identity < TOL_CYCLE and worst_sum < TOL_CYCLE)
    detail = ("%d random square joint production systems of 2 to 6 processes, at %d rates each, "
              "%d points where the price system is solvable. **The sale leg returns the whole "
              "output bundle less the wage bill, and it equals `(1 + r)` times what the input "
              "bundle cost**, within %g at every point: the identity is algebraic and holds "
              "whatever the signs are. **Where both legs are positive the cycle sums are all "
              "equal to log(1 + r)**, within %g, at %d of %d points. The remaining %d points "
              "have a non-positive leg, which is joint production's own doing: a price can come "
              "out negative, and then the logarithmic form of the field is undefined on that "
              "edge while the identity still holds. **So Theorem 12(1) of B67 needs no single "
              "production; what it needs is that the legs be positive**"
              % (systems, len(R_FRACTIONS), points, TOL_CYCLE, TOL_CYCLE, equal, readable,
                 points - readable))
    printed = ["worst |back - (1+r) cost| %.3e over %d points; worst |cycle sum - log(1+r)| "
               "%.3e over the %d readable ones; %d points had a non-positive leg"
               % (worst_identity, points, worst_sum, readable, points - readable)]
    return ok, detail, {"systems": int(systems), "points": int(points),
                        "readable": int(readable), "within": TOL_CYCLE}, printed


# ---------------------- B70-6b: one cycle per process, and what the commodity count does


def check_cycle_count(rng):
    systems = square_ok = under_ok = over_ok = 0
    b1_ok = 0
    worst_under = 0
    worst_over = 0.0
    for _ in range(N_SYSTEMS):
        a, b, l = random_joint_system(rng)
        if a is None:
            continue
        systems += 1
        n = a.shape[0]
        b1_ok += graph_b1(n) == n
        m = b - a
        # square: the price system has a unique solution once the wage is fixed
        square_ok += np.linalg.matrix_rank(m, tol=TOL_RANK) == n
        if n < 3:
            continue
        # drop a process: n - 1 equations in n unknowns, so the solution set has dimension 1
        md = (b[:, :-1] - a[:, :-1])
        rank = np.linalg.matrix_rank(md, tol=TOL_RANK)
        dim = n - rank
        under_ok += dim == 1
        worst_under = max(worst_under, abs(dim - 1))
        # add a process: n + 1 equations in n unknowns, generically inconsistent
        extra_a = rng.uniform(0.0, 1.0, (n, 1))
        extra_b = rng.uniform(0.0, 1.0, (n, 1))
        ma = np.hstack([m, extra_b - extra_a])
        rhs = np.append(l, float(rng.uniform(0.2, 2.0)))
        sol, *_ = np.linalg.lstsq(ma.T, rhs, rcond=None)
        residual = float(np.abs(sol @ ma - rhs).max())
        over_ok += residual > TOL_CYCLE
        worst_over = min(worst_over, -residual)
    ok = (systems > 0 and b1_ok == systems and square_ok == systems
          and under_ok > 0 and over_ok > 0 and worst_under == 0)
    detail = ("%d random systems. **The drawn graph has three vertices and three edges per "
              "process plus the money vertices held at par, so `b1 = E - V + 1 = n`, one "
              "independent cycle per process**, on every system, and that number does not "
              "mention the commodity count at all. With `n = m` the matrix `B - A` has full "
              "rank on all %d systems, which is the square assumption written as `b1 = m`. "
              "**Drop a process and the price vector is left undetermined on a subspace of "
              "dimension exactly `m - n = 1`**, on %d of the systems large enough to test. "
              "**Add a process and the price equations have no exact solution**, on %d of them, "
              "the smallest least-squares residual %.3e. So the classical square system is the "
              "coincidence of two index sets, and the inequality methods are what one does when "
              "they come apart"
              % (systems, square_ok, under_ok, over_ok, -worst_over))
    printed = ["b1 = n on %d of %d; full rank on %d; dimension of the undetermined subspace is "
               "1 on %d; no exact solution with an extra process on %d, smallest residual %.3e"
               % (b1_ok, systems, square_ok, under_ok, over_ok, -worst_over)]
    return ok, detail, {"systems": int(systems), "b1_matches": int(b1_ok),
                        "square_full_rank": int(square_ok), "underdetermined": int(under_ok),
                        "overdetermined": int(over_ok)}, printed


# ------------------------- B70-6c: a negative value is a statement about the feasible cone


def check_negative_values(rng):
    systems = with_negative = cone_ok = nonneg_inverse = positive_ok = 0
    smallest_negative = None
    for _ in range(N_SYSTEMS):
        a, b, l = random_joint_system(rng)
        if a is None:
            continue
        systems += 1
        m = b - a
        inv = np.linalg.inv(m)
        v = l @ inv
        if v.min() < 0.0:
            with_negative += 1
            good = True
            for i in range(len(v)):
                if v[i] < 0.0:
                    x_i = inv[:, i]              # the activity giving one net unit of i alone
                    good = good and bool(x_i.min() < 0.0)
                    smallest_negative = (v[i] if smallest_negative is None
                                         else min(smallest_negative, v[i]))
            cone_ok += good
        if inv.min() >= 0.0:
            nonneg_inverse += 1
            positive_ok += bool(v.min() > 0.0)
    ok = (systems > 0 and with_negative > 0 and cone_ok == with_negative
          and nonneg_inverse > 0 and positive_ok == nonneg_inverse)
    detail = ("%d random systems, of which **%d have at least one negative labour value**. "
              "For every one of them, the activity vector that would deliver one net unit of "
              "that commodity and nothing else has a negative component, %d of %d: **the unit "
              "is not a feasible net output, and the number called its value is the labour of "
              "an activity nobody can run.** In the other direction, %d systems have a "
              "non-negative inverse `(B - A)^{-1}`, so every unit vector is a feasible net "
              "output, and **all their labour values are strictly positive**, %d of %d. So the "
              "sign of a labour value under joint production is a statement about the cone of "
              "feasible net outputs, not about labour"
              % (systems, with_negative, cone_ok, with_negative, nonneg_inverse, positive_ok,
                 nonneg_inverse))
    printed = ["systems with a negative value %d of %d, every one of them outside the cone; "
               "systems with a non-negative inverse %d, all values positive on %d; most "
               "negative value seen %.4f"
               % (with_negative, systems, nonneg_inverse, positive_ok,
                  0.0 if smallest_negative is None else smallest_negative)]
    return ok, detail, {"systems": int(systems), "with_negative": int(with_negative),
                        "cone_holds": int(cone_ok), "nonneg_inverse": int(nonneg_inverse),
                        "all_positive": int(positive_ok)}, printed


# ----------------------- B70-6d: how many rates of profit carry a positive price vector


def runs_of_positive_prices(a, b, l):
    marks = []
    for k in range(RATE_GRID + 1):
        r = RATE_MAX * k / RATE_GRID
        marks.append(rate_carries_positive_prices(a, b, l, r))
    runs, prev = 0, False
    for mk in marks:
        if mk and not prev:
            runs += 1
        prev = mk
    return runs, marks


def check_rate_count(rng):
    single = single_one = single_from_zero = joint = joint_none = 0
    counts = {}
    for _ in range(N_SYSTEMS):
        a, b, l = random_joint_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        # the single production control: the same inputs, the identity as the output matrix
        runs_single, marks_single = runs_of_positive_prices(a, np.eye(n), l)
        single += 1
        single_one += runs_single == 1
        single_from_zero += bool(marks_single[0])
        runs_joint, _ = runs_of_positive_prices(a, b, l)
        joint += 1
        joint_none += runs_joint == 0
        counts[runs_joint] = counts.get(runs_joint, 0) + 1
    ok = (single > 0 and single_one == single and single_from_zero == single
          and joint > 0 and joint_none > 0)
    order = sorted(counts.items())
    detail = ("%d systems, each read twice: once with its own output matrix and once with the "
              "identity, which is the same inputs under single production. A rate is counted "
              "here when `l (B - (1+r)A)^{-1}` is positive in every component, which is what "
              "gives a positive wage and positive prices together; the probe is %d points on "
              "`[0, %g]`. **Under single production every system has exactly one stretch and it "
              "begins at a zero rate**, %d of %d. **Under joint production %d of %d systems "
              "have no such rate at all**, and the rest have one: %s. So on these draws joint "
              "production does not multiply the rate, it destroys it: a system can be "
              "productive, with a positive net output available at non-negative activity "
              "levels, and still admit no rate of profit whatever at which every price and the "
              "wage are positive. **Several disjoint stretches are possible in the literature "
              "and did not occur in this sample; that is reported rather than claimed either "
              "way**"
              % (single, RATE_GRID, RATE_MAX, single_one, single, joint_none, joint,
                 ", ".join("%d stretch on %d systems" % (k, c) for k, c in order)))
    printed = ["single production: one stretch on %d of %d, beginning at r = 0 on %d; joint "
               "production stretches by count: %s"
               % (single_one, single, single_from_zero,
                  ", ".join("%d -> %d" % (k, c) for k, c in order))]
    return ok, detail, {"single": int(single), "single_one_stretch": int(single_one),
                        "single_from_zero": int(single_from_zero),
                        "joint": int(joint), "joint_no_stretch": int(joint_none),
                        "stretch_counts": {str(int(k)): int(v) for k, v in order}}, printed


# ------------------------- B70-6e: fixed capital, and the depreciation schedule it implies


def check_fixed_capital():
    t = FIXED_T
    a, b, l = fixed_capital_system(t, FIXED_PARAMS)
    numeraire = np.zeros(t + 1)
    numeraire[0] = 1.0                       # the good is the unit of account
    rows, deviations = [], []
    ok_linear = None
    for r in FIXED_RATES:
        m = b - (1.0 + r) * a
        if abs(np.linalg.det(m)) < TOL_RANK:
            rows.append((r, None, None))
            continue
        p, w = prices(a, b, l, r, numeraire)
        machines = p[1:]                     # the new machine, then one period older, and so on
        new = machines[0]
        straight = np.array([new * (t - k) / t for k in range(t)])
        dev = float(np.abs(machines - straight).max() / abs(new))
        rows.append((r, machines.copy(), dev))
        if r == 0.0:
            ok_linear = dev < TOL_CYCLE and (machines > 0.0).all() and w > 0.0
        else:
            deviations.append((r, dev))
    rising = all(deviations[i][1] < deviations[i + 1][1] for i in range(len(deviations) - 1))
    away = all(d > LINEAR_FLOOR for _r, d in deviations)
    ok = bool(ok_linear) and rising and away and len(deviations) >= 2
    detail = ("A machine of constant efficiency lasting %d periods, written as joint production: "
              "commodity `0` is the good and commodity `k + 1` is a machine that has been used "
              "`k` times; one process builds a new machine and each of the others uses a "
              "machine of one age and returns it one period older, the last one scrapping it. "
              "**The machine's age is a position, exactly as the date is in B69's Corollary "
              "14.2**, and the value of a part-worn machine is then a coordinate of the price "
              "field rather than an accounting convention. **At `r = 0` the schedule is exactly "
              "straight-line**, within %g, because the price equations there make the fall in "
              "the machine's price the same number every period. **At every positive rate it is "
              "not**, and the departure grows with the rate: %s. So straight-line depreciation "
              "is the zero-rate member of this family and nothing more"
              % (t, TOL_CYCLE, ", ".join("r = %g gives %.4f" % (r, d) for r, d in deviations)))
    printed = []
    for r, machines, dev in rows:
        if machines is None:
            printed.append("r = %g: the price system is singular" % r)
        else:
            printed.append("r = %-5g schedule %s  departure from straight-line %.6f"
                           % (r, np.array2string(machines, precision=4), dev))
    return ok, detail, {"periods": t, "rates": list(FIXED_RATES), "within": TOL_CYCLE,
                        "linear_floor": LINEAR_FLOOR}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B70-5", "known_answer",
         "Steedman (1975): positive profits with a negative aggregate surplus value",
         check_steedman()),
        ("B70-6a", "instrument",
         "Theorem 15(1): equal cycle sums are the price equations under joint production too",
         check_cycles(rng)),
        ("B70-6b", "instrument",
         "Theorem 15(2): one independent cycle per process, whatever the commodity count",
         check_cycle_count(rng)),
        ("B70-6c", "instrument",
         "Theorem 15(3): a negative labour value is a statement about the feasible cone",
         check_negative_values(rng)),
        ("B70-6d", "instrument",
         "how many rates of profit carry a positive price vector",
         check_rate_count(rng)),
        ("B70-6e", "instrument",
         "Corollary 15.1: fixed capital, and the depreciation schedule as a coordinate",
         check_fixed_capital()),
    ]
    mapping = {
        "B70-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B70-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B70-5 and B70-6: the known answer and the structural checks for "
          "docs/b70_joint_production.md")
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
        "stage": "B70",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_rank": TOL_RANK,
            "n_systems": N_SYSTEMS, "sizes": list(SIZES),
            "input_column_sums": list(INPUT_COLUMN_SUMS), "joint_weight": list(JOINT_WEIGHT),
            "r_fractions": list(R_FRACTIONS), "rate_grid": RATE_GRID, "rate_max": RATE_MAX,
            "fixed_periods": FIXED_T, "fixed_params": dict(FIXED_PARAMS),
            "fixed_rates": list(FIXED_RATES), "linear_floor": LINEAR_FLOOR,
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all six pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
