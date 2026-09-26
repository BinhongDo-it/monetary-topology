"""B74-5 and B74-6: the known answer and the structural checks for roundaboutness.

The statements are proved in docs/b74_roundaboutness.md. This file reads no data and measures
nothing in the world.

  B74-5   Samuelson (1966), the two switch points at 50 and 100 per cent, read back here by
          factoring the difference polynomial rather than by bisection: D(x) = -x(2x-3)(x-2)
          with x = 1 + r, so the roots are exactly 3/2 and 2 and the costs there are 15.75 and
          28.00. Descartes' bound is attained: two sign changes and two switch points.
  B74-6a  Theorem 19(3): on drawn pairs of techniques the number of switch points never exceeds
          the number of sign changes in the difference of their dated labour profiles, and the
          two have the same parity.
  B74-6b  Theorem 19(4): where the difference changes sign once there is at most one switch and
          the cost ordering is monotone; where it changes sign twice, pairs with two switches
          occur.
  B74-6c  Theorem 19(5): the average period of production moves with the rate, its ordering
          between two techniques can reverse, and the rate at which it reverses need not be a
          switch point at all.

Run:

    python experiments\\b74_roundaboutness.py
"""

from __future__ import annotations

import json
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
OUT = ROOT / "results" / "b74_roundaboutness.json"

SEED = 0
TOL = 1e-12
TOL_ROOT = 1e-9
N_PAIRS = 600
MAX_LAG = (2, 6)               # the longest lag a drawn technique carries
LABOUR = (0.0, 3.0)            # labour at a date, zero meaning no input that period
SPARSITY = 0.45                # chance that a given date carries no labour at all
X_MAX = 4.0                    # probes run over 1 < x <= X_MAX, that is 0 < r <= 3
X_GRID = 600
SAMUELSON_A = {2: 7.0}
SAMUELSON_B = {3: 2.0, 1: 6.0}
SAMUELSON_SWITCHES = (0.5, 1.0)
SAMUELSON_COSTS = (15.75, 28.00)
SAMUELSON_SIGN_CHANGES = 2


def profile_to_coefficients(profile, degree):
    c = np.zeros(degree + 1)
    for t, v in profile.items():
        c[t] += v
    return c


def sign_changes(c):
    """How many times the coefficient sequence changes sign, zeros skipped."""
    seq = [float(v) for v in c if abs(v) > TOL]
    return sum(1 for i in range(1, len(seq)) if seq[i] * seq[i - 1] < 0.0)


def switch_points(c):
    """The roots of the difference polynomial with x > 1, that is a positive rate of profit."""
    if np.all(np.abs(c) < TOL):
        return []
    roots = np.roots(c[::-1])
    out = []
    for z in roots:
        if abs(z.imag) > TOL_ROOT:
            continue
        x = float(z.real)
        if x > 1.0 + TOL_ROOT and x <= X_MAX:
            out.append(x)
    return sorted(out)


def positive_roots(c):
    """All roots with x > 0, which is what Descartes' rule bounds."""
    if np.all(np.abs(c) < TOL):
        return []
    roots = np.roots(c[::-1])
    return sorted(float(z.real) for z in roots
                  if abs(z.imag) <= TOL_ROOT and z.real > TOL_ROOT)


def random_technique(rng):
    lag = int(rng.integers(MAX_LAG[0], MAX_LAG[1] + 1))
    profile = {}
    for t in range(lag + 1):
        if t < lag and rng.random() < SPARSITY:
            continue
        profile[t] = float(rng.uniform(LABOUR[0] + 0.05, LABOUR[1]))
    profile[lag] = float(rng.uniform(LABOUR[0] + 0.05, LABOUR[1]))   # the longest lag carries
    return profile, lag


def cost(profile, x):
    return sum(v * x ** t for t, v in profile.items())


def average_period(profile, x):
    """Boehm-Bawerk's measure, weighted by the compounded labour at each date."""
    num = sum(t * v * x ** t for t, v in profile.items())
    den = sum(v * x ** t for t, v in profile.items())
    return num / den if den > 0.0 else float("nan")


# ------------------------------------ B74-5: Samuelson's example, read back by factoring


def check_samuelson():
    degree = max(max(SAMUELSON_A), max(SAMUELSON_B))
    c = profile_to_coefficients(SAMUELSON_A, degree) - profile_to_coefficients(SAMUELSON_B,
                                                                              degree)
    changes = sign_changes(c)
    roots = switch_points(c)
    gaps = [abs((roots[i] - 1.0) - SAMUELSON_SWITCHES[i]) for i in range(min(len(roots), 2))]
    costs = [cost(SAMUELSON_A, x) for x in roots]
    cost_gaps = [abs(costs[i] - SAMUELSON_COSTS[i]) for i in range(min(len(costs), 2))]
    equal = [abs(cost(SAMUELSON_A, x) - cost(SAMUELSON_B, x)) for x in roots]
    ok = (len(roots) == 2 and changes == SAMUELSON_SIGN_CHANGES
          and max(gaps) < TOL_ROOT and max(cost_gaps) < TOL_ROOT and max(equal) < TOL_ROOT)
    detail = ("Samuelson's example of 1966: one technique spends `7` units of labour two "
              "periods before the output, the other `2` three periods before and `6` one "
              "period before. **The difference of their dated labour profiles is `-6x + 7x² - "
              "2x³`, which factors as `-x(2x - 3)(x - 2)`**, so the switch points are exactly "
              "`x = 3/2` and `x = 2`, that is **50 and 100 per cent, matched to %.1e**, with "
              "costs `15.75` and `28.00` matched to %.1e and the two techniques equally costly "
              "there to %.1e. **Descartes' bound is attained**: the coefficient sequence "
              "changes sign %d times and there are %d switch points. B67-6b read the same pair "
              "by bisection on the cost functions; **here the polynomial factors and the roots "
              "are rational**, which is a different route to the same published numbers"
              % (max(gaps), max(cost_gaps), max(equal), changes, len(roots)))
    printed = ["coefficients of the difference, ascending: %s; sign changes %d; roots in x > 1: "
               "%s; rates %s; costs there %s"
               % (np.array2string(c, precision=3), changes,
                  ", ".join("%.6f" % x for x in roots),
                  ", ".join("%.6f" % (x - 1.0) for x in roots),
                  ", ".join("%.4f" % v for v in costs))]
    return ok, detail, {"sign_changes": int(changes), "switch_points": int(len(roots)),
                        "within": TOL_ROOT}, printed


# ------------------------------------------- B74-6a: Descartes' bound, on drawn pairs


def check_bound(rng):
    pairs = within = parity = attained = 0
    table = {}
    worst = 0
    for _ in range(N_PAIRS):
        p1, lag1 = random_technique(rng)
        p2, lag2 = random_technique(rng)
        degree = max(lag1, lag2)
        c = profile_to_coefficients(p1, degree) - profile_to_coefficients(p2, degree)
        if np.all(np.abs(c) < TOL):
            continue
        pairs += 1
        changes = sign_changes(c)
        roots = positive_roots(c)
        switches = switch_points(c)
        within += len(roots) <= changes
        worst = max(worst, len(roots) - changes)
        parity += (len(roots) - changes) % 2 == 0
        attained += len(roots) == changes
        key = (changes, len(switches))
        table[key] = table.get(key, 0) + 1
    ok = pairs > 0 and within == pairs and parity == pairs and worst <= 0
    order = sorted(table.items())
    detail = ("%d drawn pairs of techniques, each with a longest lag between %d and %d and some "
              "dates carrying no labour. **The number of positive roots of the difference never "
              "exceeds the number of sign changes in its coefficients**, on all %d, and **the "
              "two always have the same parity**, on all %d, which is Descartes' rule read on "
              "the dated labour profiles. The bound is attained on %d of them. The joint "
              "distribution of (sign changes, switch points at a positive rate) is %s. **So "
              "how many times the ordering of two techniques can reverse is bounded by a "
              "property of their profiles that does not mention the rate of profit at all**"
              % (pairs, MAX_LAG[0], MAX_LAG[1], within, parity, attained,
                 ", ".join("(%d, %d) on %d" % (a, b, n) for (a, b), n in order)))
    printed = ["pairs %d; bound holds on %d; parity holds on %d; bound attained on %d; worst "
               "excess of roots over sign changes %d" % (pairs, within, parity, attained, worst)]
    return ok, detail, {"pairs": int(pairs), "within_bound": int(within),
                        "parity_holds": int(parity), "bound_attained": int(attained),
                        "table": {"%d,%d" % k: int(v) for k, v in order}}, printed


# ------------------------------- B74-6b: where one number does order the techniques


def check_domain(rng):
    pairs = one_change = one_change_ok = many = two_switches = 0
    monotone = 0
    for _ in range(N_PAIRS):
        p1, lag1 = random_technique(rng)
        p2, lag2 = random_technique(rng)
        degree = max(lag1, lag2)
        c = profile_to_coefficients(p1, degree) - profile_to_coefficients(p2, degree)
        if np.all(np.abs(c) < TOL):
            continue
        pairs += 1
        changes = sign_changes(c)
        switches = switch_points(c)
        if changes == 1:
            one_change += 1
            one_change_ok += len(switches) <= 1
            # the sign of the difference changes at most once over the probes
            signs = []
            for j in range(X_GRID + 1):
                x = 1.0 + (X_MAX - 1.0) * j / X_GRID
                d = float(np.polyval(c[::-1], x))
                if abs(d) > TOL_ROOT:
                    signs.append(d > 0.0)
            flips = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
            monotone += flips <= 1
        elif changes >= 2:
            many += 1
            two_switches += len(switches) >= 2
    ok = (pairs > 0 and one_change > 0 and one_change_ok == one_change
          and monotone == one_change and many > 0 and two_switches > 0)
    detail = ("%d drawn pairs. **Where the difference of the profiles changes sign once there "
              "is at most one switch point**, on all %d such pairs, **and the cost ordering "
              "reverses at most once over the whole range of rates probed**, on all %d: a "
              "single number does order those two techniques, with one reversal. **Where it "
              "changes sign two or more times, pairs with two switch points occur**, %d of the "
              "%d such pairs. So the Austrian intuition is not wrong: **it has a domain, and "
              "the domain is that the two dated labour profiles cross once**"
              % (pairs, one_change_ok, monotone, two_switches, many))
    printed = ["pairs %d; one sign change on %d, of which at most one switch on %d and at most "
               "one reversal of the cost ordering on %d; two or more sign changes on %d, of "
               "which two switch points on %d"
               % (pairs, one_change, one_change_ok, monotone, many, two_switches)]
    return ok, detail, {"pairs": int(pairs), "one_sign_change": int(one_change),
                        "at_most_one_switch": int(one_change_ok), "monotone": int(monotone),
                        "two_or_more_changes": int(many),
                        "two_switches": int(two_switches)}, printed


# -------------------------- B74-6c: the average period moves, and does not track the cost


def check_average_period(rng):
    pairs = moving = reversing = mismatched = 0
    biggest_move = 0.0
    example = None
    for _ in range(N_PAIRS):
        p1, lag1 = random_technique(rng)
        p2, lag2 = random_technique(rng)
        degree = max(lag1, lag2)
        c = profile_to_coefficients(p1, degree) - profile_to_coefficients(p2, degree)
        if np.all(np.abs(c) < TOL):
            continue
        pairs += 1
        xs = [1.0 + (X_MAX - 1.0) * j / X_GRID for j in range(X_GRID + 1)]
        app1 = np.array([average_period(p1, x) for x in xs])
        app2 = np.array([average_period(p2, x) for x in xs])
        move = float(max(app1.max() - app1.min(), app2.max() - app2.min()))
        biggest_move = max(biggest_move, move)
        moving += move > 1e-6
        diff = app1 - app2
        signs = [d > 0.0 for d in diff if abs(d) > 1e-9]
        flips = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
        if flips >= 1:
            reversing += 1
            # where does the average period ordering reverse, and is that a switch point?
            cross = None
            for i in range(1, len(xs)):
                if diff[i] * diff[i - 1] < 0.0:
                    cross = 0.5 * (xs[i] + xs[i - 1])
                    break
            switches = switch_points(c)
            if cross is not None:
                near = min((abs(cross - s) for s in switches), default=float("inf"))
                if near > 1e-3:
                    mismatched += 1
                    if example is None:
                        example = (cross, switches, move)
    ok = (pairs > 0 and moving > 0 and reversing > 0 and mismatched > 0
          and biggest_move > 1e-6)
    detail = ("%d drawn pairs, each read at %d rates from zero up to %g. **The average period "
              "of production moves with the rate on %d of the pairs**, the largest movement "
              "%.4f periods, so it is not a property of a technique alone. **Its ordering "
              "between two techniques reverses somewhere on %d of the pairs**, and on %d of "
              "those **the rate where it reverses is not a switch point at all**: the measure "
              "does not even track the cost ordering it was introduced to stand for. So the "
              "objection to it is not only that it moves, but that **where it moves is not "
              "where the thing it measures moves**"
              % (pairs, X_GRID + 1, X_MAX - 1.0, moving, biggest_move, reversing, mismatched))
    printed = ["pairs %d; the average period moves on %d, largest movement %.4f periods; its "
               "ordering reverses on %d; the reversal is away from every switch point on %d"
               % (pairs, moving, biggest_move, reversing, mismatched)]
    if example is not None:
        cross, switches, move = example
        printed.append("an instance: the average period ordering reverses at r = %.4f while the "
                       "switch points are at %s"
                       % (cross - 1.0,
                          ", ".join("%.4f" % (s - 1.0) for s in switches) or "none"))
    return ok, detail, {"pairs": int(pairs), "moving": int(moving),
                        "reversing": int(reversing), "away_from_switch": int(mismatched),
                        "probes": int(X_GRID + 1)}, printed


# --------------------------------------------------------------------------- run


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B74-5", "known_answer",
         "Samuelson's two switch points, read back by factoring the difference polynomial",
         check_samuelson()),
        ("B74-6a", "instrument",
         "Theorem 19(3): the number of switch points is bounded by the sign changes, with the "
         "same parity", check_bound(rng)),
        ("B74-6b", "instrument",
         "Theorem 19(4): where the profiles cross once, one number does order the techniques",
         check_domain(rng)),
        ("B74-6c", "instrument",
         "Theorem 19(5): the average period moves, and where it moves is not where the cost "
         "ordering moves", check_average_period(rng)),
    ]
    mapping = {
        "B74-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B74-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B74-5 and B74-6: the known answer and the structural checks for "
          "docs/b74_roundaboutness.md")
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
        "stage": "B74",
        "config": {
            "seed": SEED, "tol": TOL, "tol_root": TOL_ROOT, "n_pairs": N_PAIRS,
            "max_lag": list(MAX_LAG), "labour": list(LABOUR), "sparsity": SPARSITY,
            "x_max": X_MAX, "x_grid": X_GRID,
            "samuelson": {"technique_a": {str(k): v for k, v in SAMUELSON_A.items()},
                          "technique_b": {str(k): v for k, v in SAMUELSON_B.items()},
                          "switches": list(SAMUELSON_SWITCHES),
                          "costs": list(SAMUELSON_COSTS),
                          "sign_changes": SAMUELSON_SIGN_CHANGES},
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all four pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
