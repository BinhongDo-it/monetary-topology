"""B68-6 and B68-7: the known answer and the structural checks for the value field.

The statements are proved in docs/b68_value_field.md. This file checks their
algebra on random productive systems built by the industry generator of stage
A19. It reads no data and measures nothing in the world.

  B68-6   The Fundamental Marxian Theorem, Okishio (1963) and Morishima (1973):
          the rate of profits is positive exactly when the rate of exploitation
          is, which here reads r > 0 if and only if the labour value of the wage
          basket is below one unit of labour, with 1 + r = 1 / lambda_PF(A + b l).
  B68-7a  Theorem 13(1) and (3): the labour values are the r = 0 member of the
          family of B67, every production cycle sums to zero there, and the
          distance of Theorem 5 is zero: the value field is exact.
  B68-7b  Corollary 13.1: with the net product as the unit of account the total
          price of the net product equals its total value at every rate, and the
          total profits equal the total surplus value exactly when the wage
          basket costs what it is worth, which a basket in the proportions of the
          net product does.
  B68-7c  Corollary 13.3: redraw each cycle so that the return on the advance is
          bought as an input and every cycle sums to zero and the distance
          vanishes, while r is the same number as before. The distance moves with
          the drawing and the rate does not.
  B68-7d  Corollary 13.1's last clause: prices are proportional to values at
          every rate when every industry has the same composition, and generally
          not otherwise.

Run:

    python experiments\\b68_value_field.py
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
OUT = ROOT / "results" / "b68_value_field.json"

SEED = 0
TOL = 1e-12          # identities that are the same floating point operations on both sides
TOL_CYCLE = 1e-10    # sums of logarithms, where the two legs are computed differently
TOL_EIGEN = 1e-9     # the eigenvector residual of the augmented matrix, relative to its size
TOL_AGG = 1e-10      # aggregates, relative to the labour employed
GAP_FLOOR = 1e-9     # below this a generic basket's aggregate gap would not be readable
SPREAD_FLOOR = 1e-6  # below this prices and values would not be distinguishable in proportion
N_SYSTEMS = 200
SIZES = (3, 8)
COLUMN_SUMS = (0.3, 0.5, 0.7)
R_FRACTIONS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)
VALUE_OF_BASKET = (0.2, 0.5, 0.8, 1.0, 1.2, 1.5)   # the labour value of the wage basket
WAGE_SHARES = (0.2, 0.5, 0.8)                      # the same thing read as a share of the net product
N_BASKETS = 4                                       # net products drawn per system, for the aggregates


def incidence(nodes, edges):
    index = {v: k for k, v in enumerate(nodes)}
    B = np.zeros((len(nodes), len(edges)))
    for e, (u, v) in enumerate(edges):
        B[index[v], e] += 1.0
        B[index[u], e] -= 1.0
    return B


def distance(B, omega):
    """Theorem 5's distance from omega to the fields with a potential."""
    psi, *_ = np.linalg.lstsq(B.T, omega, rcond=None)
    return float(np.linalg.norm(omega - B.T @ psi))


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
    """v = v A + l: the labour embodied in one unit of each commodity."""
    return l @ np.linalg.inv(np.eye(a.shape[0]) - a)


def prices(a, l, r, numeraire):
    """p = (1 + r) p A + w l, with the given basket priced at one."""
    base = l @ np.linalg.inv(np.eye(a.shape[0]) - (1.0 + r) * a)
    w = 1.0 / float(base @ numeraire)
    return w * base, w


def rate_from_basket(a, l, b):
    """With the real wage basket b per unit of labour, the augmented matrix is
    A + b l and the rate of profits is 1 / lambda_PF - 1."""
    lam, _ = perron(a + np.outer(b, l))
    return 1.0 / lam - 1.0, lam


def cycle_graph(a, l, p, w, r, returns_inside=False):
    """Each industry: money, its bundle, its output. Without `returns_inside`
    the bundle is the commodities advanced and the sale leg returns the price
    less the wage bill, so the cycle sums to log(1 + r). With it, the return on
    the advance is bought along with the inputs, and the cycle sums to zero."""
    n = a.shape[0]
    advance = p @ a
    bundle = (1.0 + r) * advance + w * l if returns_inside else advance
    back = p if returns_inside else p - w * l
    nodes, edges, omega = [], [], []
    for j in range(n):
        nodes += [(j, "M"), (j, "B"), (j, "Q")]
        edges += [((j, "M"), (j, "B")), ((j, "B"), (j, "Q")), ((j, "Q"), (j, "M"))]
        omega += [-math.log(bundle[j]), 0.0, math.log(back[j])]
        if j > 0:
            edges.append(((0, "M"), (j, "M")))
            omega.append(0.0)
    return nodes, edges, np.array(omega)


def cycle_sums(omega, n):
    sums, k = [], 0
    for j in range(n):
        sums.append(float(omega[k] + omega[k + 1] + omega[k + 2]))
        k += 3 + (1 if j > 0 else 0)
    return np.array(sums)


# ------------------------------------ B68-6: the Fundamental Marxian Theorem


def check_fmt(rng):
    """Okishio (1963) and Morishima (1973): the rate of profits is positive exactly when
    the rate of exploitation is. Here the wage basket b is drawn to a chosen labour value
    v b = t, so the rate of exploitation is (1 - t) / t and the theorem says the sign of r
    is the sign of 1 - t. The proof step v M = v - (1 - v b) l is checked alongside it."""
    systems = points = agree = eigen_points = 0
    worst_identity = worst_eigen = worst_rate = 0.0
    smallest_positive = None
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = labour_values(a, l)
        if v.min() <= 0.0:
            continue
        systems += 1
        for t in VALUE_OF_BASKET:
            b0 = rng.uniform(0.1, 1.0, n)
            b = b0 * (t / float(v @ b0))
            m = a + np.outer(b, l)
            r, lam = rate_from_basket(a, l, b)
            worst_identity = max(worst_identity,
                                 float(np.abs(v @ m - (v - (1.0 - t) * l)).max()))
            lam_left, q = perron(m.T)
            if q.min() > 0.0:
                eigen_points += 1
                worst_eigen = max(worst_eigen, float(np.abs(q @ m - lam_left * q).max()
                                                     / np.abs(q).max()))
                worst_rate = max(worst_rate, abs(lam_left - lam))
            points += 1
            if t < 1.0:
                agree += r > GAP_FLOOR
                smallest_positive = r if smallest_positive is None else min(smallest_positive, r)
            elif t > 1.0:
                agree += r < -GAP_FLOOR
            else:
                agree += abs(r) <= GAP_FLOOR
    ok = (systems > 0 and agree == points and worst_identity < TOL
          and worst_eigen < TOL_EIGEN and worst_rate < TOL_EIGEN)
    detail = ("%d random productive systems, %d wage baskets each, drawn so that the labour "
              "value of the basket takes the values %s. **The rate of profits is positive "
              "exactly when the basket is worth less than the labour it buys**, at all %d "
              "points, with `1 + r = 1 / lambda_PF(A + b l)`. This is the Fundamental Marxian "
              "Theorem of Okishio (1963, *Weltwirtschaftliches Archiv* 91(2)) and Morishima "
              "(1973, *Marx's Economics*, Cambridge, p. 53), read back here on drawn systems. "
              "The step the proof turns on, `v (A + b l) = v - (1 - v b) l`, holds within %g: "
              "**the augmented matrix moves the value vector down by the surplus and by nothing "
              "else**, so the value vector is a positive left vector shrunk by the matrix "
              "exactly when the surplus is positive. The left Perron vector of the augmented "
              "matrix is positive and solves the price equation within %g relative on all %d "
              "points where it was drawn"
              % (systems, len(VALUE_OF_BASKET), ", ".join("%g" % x for x in VALUE_OF_BASKET),
                 points, TOL, TOL_EIGEN, eigen_points))
    printed = ["worst |v M - (v - (1 - v b) l)| %.3e; worst eigenvector residual %.3e; "
               "worst |lambda(M^T) - lambda(M)| %.3e; smallest positive rate seen %.4f"
               % (worst_identity, worst_eigen, worst_rate,
                  0.0 if smallest_positive is None else smallest_positive)]
    return ok, detail, {"systems": systems, "points": points, "sign_agrees": agree,
                        "identity_within": TOL}, printed


# -------------------------- B68-7a: the values are the member at a zero rate of profits


def check_value_member(rng):
    """Theorem 13: with labour as the unit of account the member at r = 0 is the value
    vector itself, its production cycles close, and the distance of Theorem 5 is zero. At
    a positive rate the same drawing gives log(1 + r) on every cycle and a distance of
    sqrt(n / 3) times it, which is the number B67 measured on this graph."""
    systems = zero_points = rate_points = 0
    worst_price = worst_zero_cycle = worst_zero_rho = 0.0
    worst_cycle = worst_rho = 0.0
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = labour_values(a, l)
        if v.min() <= 0.0:
            continue
        lam, _ = perron(a)
        systems += 1
        R = 1.0 / lam - 1.0
        unit = np.zeros(n)
        unit[0] = 1.0 / v[0]                       # the basket that makes the wage one unit
        p0, w0 = prices(a, l, 0.0, unit)
        worst_price = max(worst_price, float(np.abs(p0 - v).max()))
        nodes, edges, omega = cycle_graph(a, l, v, 1.0, 0.0)
        B = incidence(nodes, edges)
        worst_zero_cycle = max(worst_zero_cycle, float(np.abs(cycle_sums(omega, n)).max()))
        worst_zero_rho = max(worst_zero_rho, distance(B, omega))
        zero_points += 1
        for f in R_FRACTIONS[1:]:
            r = f * R
            p, w = prices(a, l, r, unit)
            nodes, edges, omega = cycle_graph(a, l, p, w, r)
            B = incidence(nodes, edges)
            worst_cycle = max(worst_cycle,
                              float(np.abs(cycle_sums(omega, n) - math.log1p(r)).max()))
            worst_rho = max(worst_rho,
                            abs(distance(B, omega) - math.sqrt(n / 3.0) * math.log1p(r)))
            rate_points += 1
    ok = (systems > 0 and worst_price < TOL and worst_zero_cycle < TOL_CYCLE
          and worst_zero_rho < TOL_CYCLE and worst_cycle < TOL_CYCLE and worst_rho < TOL_CYCLE)
    detail = ("%d systems. **With labour as the unit of account the member of the family at "
              "r = 0 is the labour value vector itself**, within %g on every system: the two "
              "systems of equations `v = v A + l` and `p = (1 + r) p A + w l` are the same "
              "equations at `r = 0`, `w = 1`. On the value field every production cycle sums "
              "to zero and the distance of Theorem 5 is zero within %g at all %d systems, so "
              "**the value field is exact and sits in the zero set of Corollary 5.4**. At the "
              "%d positive rates the same drawing gives log(1 + r) on every cycle and a "
              "distance of sqrt(n / 3) times it, within %g at all %d points"
              % (systems, TOL, TOL_CYCLE, zero_points, len(R_FRACTIONS) - 1, TOL_CYCLE,
                 rate_points))
    printed = ["worst |p(0) - v| %.3e; on the value field worst |cycle sum| %.3e and worst "
               "distance %.3e; at positive rates worst |cycle sum - log(1+r)| %.3e and worst "
               "|rho - sqrt(n/3) log(1+r)| %.3e"
               % (worst_price, worst_zero_cycle, worst_zero_rho, worst_cycle, worst_rho)]
    return ok, detail, {"systems": systems, "zero_points": zero_points,
                        "rate_points": rate_points, "within": TOL_CYCLE}, printed


# -------------------------------- B68-7b: which aggregates survive the move along the family


def check_aggregates(rng):
    """Corollary 13.1. The net product is drawn first and the gross output follows, so the
    total labour is l x and the total value of the net product is v y, the same number. The
    price vector is normalised so that the net product costs what it is worth, which is one
    choice of unit and no more. Then the total profits equal the total surplus value exactly
    when the wage basket costs what it is worth, and a basket in the proportions of the net
    product does."""
    systems = std_points = gen_points = std_equal = gen_apart = 0
    worst_total = worst_identity = worst_std = 0.0
    smallest_gap = None
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = labour_values(a, l)
        if v.min() <= 0.0:
            continue
        systems += 1
        leontief = np.linalg.inv(np.eye(n) - a)
        for _draw in range(N_BASKETS):
            y = rng.uniform(0.2, 2.0, n)                  # the net product
            x = leontief @ y                              # the gross output that leaves it
            labour = float(l @ x)
            worst_total = max(worst_total, abs(float(v @ y) - labour) / labour)
            for t in WAGE_SHARES:
                for standard in (True, False):
                    if standard:
                        b = (t / labour) * y              # the wage basket in the net product's
                    else:                                 # own proportions
                        b0 = rng.uniform(0.1, 1.0, n)
                        b = b0 * (t / float(v @ b0))
                    r, _lam = rate_from_basket(a, l, b)
                    _lam_left, q = perron((a + np.outer(b, l)).T)
                    if q.min() <= 0.0:
                        continue
                    p = q * (labour / float(q @ y))       # total price = total value
                    profits = float(p @ y) - labour * float(p @ b)
                    surplus = labour * (1.0 - float(v @ b))
                    worst_identity = max(worst_identity,
                                         abs(profits - surplus
                                             - labour * (float(v @ b) - float(p @ b))) / labour)
                    gap = abs(profits - surplus) / labour
                    if standard:
                        std_points += 1
                        std_equal += gap < TOL_AGG
                        worst_std = max(worst_std, gap)
                    else:
                        gen_points += 1
                        gen_apart += gap > GAP_FLOOR
                        smallest_gap = gap if smallest_gap is None else min(smallest_gap, gap)
    ok = (systems > 0 and std_equal == std_points and gen_apart == gen_points
          and worst_total < TOL_AGG and worst_identity < TOL_AGG and worst_std < TOL_AGG)
    detail = ("%d systems, %d net products each, %d wage shares, two baskets per share. The "
              "total value of the net product is the labour employed, within %g. With the net "
              "product as the unit of account **the first aggregate equality is a choice of "
              "unit and the second one is not**: the gap between total profits and total "
              "surplus value is the labour employed times the gap between what the wage basket "
              "costs and what it is worth, `Pi - S = L (v b - p b)`, an identity that holds "
              "within %g at all %d points. **A basket in the proportions of the net product "
              "closes both at once**, within %g at all %d points, because pricing the net "
              "product at its value prices any multiple of it at its value. A basket drawn "
              "without that proportion leaves them apart at all %d points. **So whether the "
              "two aggregates survive the move along the family is a statement about which "
              "flow is paired with the field, not about the prices**"
              % (systems, N_BASKETS, len(WAGE_SHARES), TOL_AGG, TOL_AGG,
                 std_points + gen_points, TOL_AGG, std_points, gen_points))
    printed = ["worst |v y - l x| / L %.3e; worst departure from Pi - S = L (v b - p b) %.3e; "
               "on the proportional basket worst |Pi - S| / L %.3e; on drawn baskets the "
               "smallest |Pi - S| / L %.3e"
               % (worst_total, worst_identity, worst_std,
                  0.0 if smallest_gap is None else smallest_gap)]
    return ok, detail, {"systems": systems, "standard_points": std_points,
                        "drawn_points": gen_points, "within": TOL_AGG,
                        "gap_floor": GAP_FLOOR}, printed


# ------------------------------- B68-7c: the return read as a cost, and the rate that does not move


def check_redraw(rng):
    """Corollary 13.3. The same system, the same prices, the same rate of profits, drawn
    twice. With the return on the advance bought along with the inputs, every cycle sums to
    zero and the distance vanishes. The rate is the same number in both drawings: it was
    never read off the drawing."""
    systems = points = closed = 0
    worst_outside = worst_inside = worst_rho_in = worst_drop = 0.0
    smallest_rho_out = None
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        lam, _ = perron(a)
        systems += 1
        R = 1.0 / lam - 1.0
        unit = np.ones(n)
        for f in R_FRACTIONS[1:]:
            r = f * R
            p, w = prices(a, l, r, unit)
            nodes, edges, omega_out = cycle_graph(a, l, p, w, r, returns_inside=False)
            _, _, omega_in = cycle_graph(a, l, p, w, r, returns_inside=True)
            B = incidence(nodes, edges)
            sums_out = cycle_sums(omega_out, n)
            sums_in = cycle_sums(omega_in, n)
            worst_outside = max(worst_outside, float(np.abs(sums_out - math.log1p(r)).max()))
            worst_inside = max(worst_inside, float(np.abs(sums_in).max()))
            worst_drop = max(worst_drop,
                             float(np.abs(sums_out - sums_in - math.log1p(r)).max()))
            worst_rho_in = max(worst_rho_in, distance(B, omega_in))
            rho_out = distance(B, omega_out)
            smallest_rho_out = rho_out if smallest_rho_out is None else min(smallest_rho_out,
                                                                           rho_out)
            points += 1
            closed += float(np.abs(sums_in).max()) < TOL_CYCLE
    ok = (systems > 0 and closed == points and worst_outside < TOL_CYCLE
          and worst_inside < TOL_CYCLE and worst_drop < TOL_CYCLE
          and worst_rho_in < TOL_CYCLE and smallest_rho_out is not None
          and smallest_rho_out > SPREAD_FLOOR)
    detail = ("%d systems at %d positive rates each, each drawn twice. With the advance in the "
              "bundle and the return left on the sale leg, every production cycle sums to "
              "log(1 + r) and the distance is positive. **With the return on the advance "
              "bought along with the inputs, the bundle costs exactly what the product sells "
              "for**: every cycle sums to zero and the distance vanishes, within %g at all %d "
              "points. The two drawings differ by log(1 + r) on every cycle, within %g. "
              "**The prices, the wage and the rate are the same numbers in both drawings**, so "
              "whether the normal return on capital is read as a cost or as a profit is a "
              "choice of where to draw the edge, and `r` is what does not move when it is "
              "made. It follows that the distance is not a measure of the gap between values "
              "and prices: **the distance counts the drawing, and the family's parameter is "
              "the rate itself**"
              % (systems, len(R_FRACTIONS) - 1, TOL_CYCLE, points, TOL_CYCLE))
    printed = ["with the return outside, worst |cycle sum - log(1+r)| %.3e and the smallest "
               "distance seen %.4f; with it inside, worst |cycle sum| %.3e and worst distance "
               "%.3e; worst departure from the drop of log(1+r) %.3e"
               % (worst_outside, 0.0 if smallest_rho_out is None else smallest_rho_out,
                  worst_inside, worst_rho_in, worst_drop)]
    return ok, detail, {"systems": systems, "points": points, "closed": closed,
                        "within": TOL_CYCLE}, printed


# ------------------------- B68-7d: when prices are proportional to values, and when they are not


def check_proportionality(rng):
    """The last clause of Corollary 13.1. Prices are proportional to values at every rate
    exactly when the value vector is proportional to the direct labour vector, which is
    equal composition across industries. Drawn systems do not have it; a system whose
    labour vector is the left Perron vector of A does, by construction."""
    systems = drawn_points = equal_points = drawn_apart = equal_together = 0
    smallest_spread = None
    worst_equal = 0.0
    for _ in range(N_SYSTEMS):
        a, l = random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        lam, _ = perron(a)
        lam_left, left = perron(a.T)
        if left.min() <= 0.0:
            continue
        systems += 1
        R = 1.0 / lam - 1.0
        for labour, equal in ((l, False), (left / left.max() + 0.0, True)):
            v = labour_values(a, labour)
            if v.min() <= 0.0:
                continue
            for f in R_FRACTIONS[1:]:
                r = f * R
                p, _w = prices(a, labour, r, np.ones(n))
                ratio = p / v
                spread = float(ratio.max() / ratio.min() - 1.0)
                if equal:
                    equal_points += 1
                    equal_together += spread < SPREAD_FLOOR
                    worst_equal = max(worst_equal, spread)
                else:
                    drawn_points += 1
                    drawn_apart += spread > SPREAD_FLOOR
                    smallest_spread = (spread if smallest_spread is None
                                       else min(smallest_spread, spread))
    ok = (systems > 0 and drawn_apart == drawn_points and equal_together == equal_points
          and worst_equal < SPREAD_FLOOR)
    detail = ("%d systems at %d positive rates each, with two labour vectors. **With the "
              "labour vector drawn at random, prices are not proportional to values at any "
              "positive rate**, at all %d points. **With the labour vector taken to be the "
              "left Perron vector of A, they are proportional at every rate**, within %g at "
              "all %d points, because then `v` is a multiple of `l` and the price equation "
              "reproduces that multiple at every rate. Equal composition in the classical "
              "sense is exactly `v` proportional to `l`, so **the condition for prices to "
              "stay proportional to values along the family is a condition on the technique, "
              "not on the rate**"
              % (systems, len(R_FRACTIONS) - 1, drawn_points, SPREAD_FLOOR, equal_points))
    printed = ["on drawn systems the smallest spread of p / v across industries %.4f; on the "
               "equal composition systems the worst spread %.3e"
               % (0.0 if smallest_spread is None else smallest_spread, worst_equal)]
    return ok, detail, {"systems": systems, "drawn_points": drawn_points,
                        "equal_points": equal_points, "spread_floor": SPREAD_FLOOR}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B68-6", "known_answer",
         "Corollary 13.2, the Fundamental Marxian Theorem: the rate of profits is positive "
         "exactly when the rate of exploitation is", check_fmt(rng)),
        ("B68-7a", "instrument",
         "Theorem 13(1) and (3): the labour values are the member of the family at r = 0, and "
         "that member is the only exact one", check_value_member(rng)),
        ("B68-7b", "instrument",
         "Corollary 13.1: which aggregates survive the move is a statement about the flow "
         "they are paired with", check_aggregates(rng)),
        ("B68-7c", "instrument",
         "Corollary 13.3: the return read as a cost closes every cycle, and the rate does "
         "not move", check_redraw(rng)),
        ("B68-7d", "instrument",
         "Corollary 13.1(5): prices stay proportional to values exactly under equal "
         "composition", check_proportionality(rng)),
    ]
    mapping = {
        "B68-6": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B68-7": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B68-6 and B68-7: the known answer and the structural checks for "
          "docs/b68_value_field.md")
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
        "stage": "B68",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_eigen": TOL_EIGEN,
            "tol_aggregate": TOL_AGG, "gap_floor": GAP_FLOOR, "spread_floor": SPREAD_FLOOR,
            "n_systems": N_SYSTEMS, "sizes": list(SIZES), "column_sums": list(COLUMN_SUMS),
            "r_fractions": list(R_FRACTIONS), "value_of_basket": list(VALUE_OF_BASKET),
            "wage_shares": list(WAGE_SHARES), "n_baskets": N_BASKETS,
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
