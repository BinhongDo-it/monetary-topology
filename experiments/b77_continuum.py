"""B77-5 and B77-6: the known answers and the structural checks for a continuum of techniques.

The statements are proved in docs/b77_continuum.md. This file reads no data and measures
nothing in the world.

  B77-5   Two classical facts, read back exactly on constructed instances: the lower envelope
          of a family of affine functions is concave, so the owner's slope never rises; and the
          envelope theorem, E'(x) = dC_theta/dx at the owner. A closed-form family is also read
          back: C_theta(x) = theta^2 + (1-theta)^2 x has envelope exactly x/(1+x).
  B77-6a  Theorem 22(1): refining a continuum of processes does not enlarge the active set.
  B77-6b  Theorem 22(2): the switch count on the same family grows without bound, so the two
          counts move in opposite directions and counting stops being the question.
  B77-6c  Theorem 22(3): the owner's label wanders while the coefficient it carries does not,
          and every candidate reversal in the quadratic class collapses under grid refinement.
  B77-6d  Theorem 22(4): adding land qualities never changes b_1, and total rent converges as a
          Riemann sum while the marginal quality contributes nothing to it.

Run:

    python experiments\\b77_continuum.py
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
OUT = ROOT / "results" / "b77_continuum.json"

SEED = 0
TOL = 1e-12
ACTIVE_TOL = 1e-7
BISECT_ITERS = 60
BISECT_LO, BISECT_HI = 1e-9, 100.0
BISECT_FLOOR = 1e-6            # the solver's floor, as measured in B75

GOODS = 4                      # m, held fixed while the process set is refined
REFINE = (10, 50, 200, 600)    # discretisations of the continuum of processes
BASKET_A0 = [0.20, 0.05, 0.10, 0.04]
BASKET_A1 = [0.04, 0.18, 0.06, 0.12]
BASKET_B0 = [0.05, 0.02, 0.03, 0.02]
BASKET_B1 = [0.02, 0.06, 0.02, 0.05]

X_RANGE = (0.05, 20.0)
X_POINTS = 4000
SWITCH_KS = (5, 20, 80, 320, 1280)
CLOSED_THETA = 20001           # grid for the closed-form family
FAMILIES = 400                 # drawn coefficient families
FAMILY_X = (0.05, 6.0, 2000)
FAMILY_THETA = 600
REFINE_THETA = (600, 1200, 2400)
SEARCH = 1500                  # search for a reversal in the quadratic class
LANDS = (1, 5, 20, 50)
RENT_KS = (10, 100, 1000, 10000)

#: QuantEcon's first published rectangular example, whose expansion factor is the cube root of
#: two. The programme below is the construction of B75 written out again here rather than
#: imported, so that a change to one station's file cannot reach another's. **It is pinned
#: against this external number rather than against B75's code**, which is what makes the copy
#: checkable instead of merely duplicated.
PIN_A = [[0, 1, 0, 0], [1, 0, 0, 1], [0, 0, 1, 0]]
PIN_B = [[1, 0, 0, 0], [0, 0, 2, 0], [0, 1, 0, 1]]


# ------------------------------------------------------------------ the programme

def game_value(M):
    n, m = M.shape
    c = np.zeros(n + 1)
    c[-1] = -1.0
    r = linprog(c, A_ub=np.hstack([-M.T, np.ones((m, 1))]), b_ub=np.zeros(m),
                A_eq=np.hstack([np.ones((1, n)), np.zeros((1, 1))]), b_eq=np.array([1.0]),
                bounds=[(0, None)] * n + [(None, None)], method="highs")
    if not r.success:
        return None, None, None
    p = np.abs(r.ineqlin.marginals)
    total = p.sum()
    return float(r.x[-1]), r.x[:n], (p / total if total > 0 else p)


def expansion_factor(A, B):
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


def solution(A, B):
    a = expansion_factor(A, B)
    if a is None:
        return None, None, None
    _, x, p = game_value(B - a * A)
    return a, x, p


# ------------------------------------------------------------------ envelopes

def owner_runs(idx):
    runs = [int(idx[0])]
    for a in idx[1:]:
        if int(a) != runs[-1]:
            runs.append(int(a))
    return runs


def reversal(path):
    """Depth of the deepest V or tallest Lambda in a path: zero exactly when it is monotone."""
    pmax = np.maximum.accumulate(path)
    smax = np.maximum.accumulate(path[::-1])[::-1]
    pmin = np.minimum.accumulate(path)
    smin = np.minimum.accumulate(path[::-1])[::-1]
    return float(max(np.minimum(pmax - path, smax - path).max(),
                     np.minimum(path - pmin, path - smin).max()))


def coefficient_curves(co, theta):
    basis = np.stack([np.ones_like(theta), theta, theta ** 2, theta ** 3])
    a, b, c = (co[0] @ basis), (co[1] @ basis), (co[2] @ basis)
    return a - a.min() + 0.05, b - b.min() + 0.05, c - c.min() + 0.01


def family_envelope(co, n_theta, n_x, quadratic):
    theta = np.linspace(0.0, 1.0, n_theta)
    xs = np.linspace(FAMILY_X[0], FAMILY_X[1], n_x)
    a, b, c = coefficient_curves(co, theta)
    if not quadratic:
        c = np.zeros_like(c)
    C = a[:, None] + b[:, None] * xs[None, :] + c[:, None] * xs[None, :] ** 2
    idx = np.argmin(C, axis=0)
    return xs, theta[idx], b[idx] + 2.0 * c[idx] * xs


# ------------------------------- B77-5: two classical facts and one closed form


def check_classical(rng):
    # (a) the lower envelope of affine functions is concave: the owner's slope never rises
    worst_rise = -np.inf
    wander = families = 0
    for _ in range(FAMILIES):
        co = rng.uniform(-1.0, 1.0, (3, 4))
        _, path, slope = family_envelope(co, FAMILY_THETA, FAMILY_X[2], quadratic=False)
        families += 1
        worst_rise = max(worst_rise, float(np.diff(slope).max()))
        d = np.diff(path)
        wander += int((d > 1e-9).any() and (d < -1e-9).any())
    concave = worst_rise <= 0.0

    # (b) the closed form, and the envelope theorem on it
    ths = np.linspace(0.0, 1.0, CLOSED_THETA)
    xs = np.linspace(X_RANGE[0], X_RANGE[1], 41)
    worst_e = worst_t = worst_d = 0.0
    for x in xs:
        C = ths ** 2 + (1.0 - ths) ** 2 * x
        i = int(np.argmin(C))
        worst_e = max(worst_e, abs(float(C[i]) - x / (1.0 + x)))
        worst_t = max(worst_t, abs(float(ths[i]) - x / (1.0 + x)))
        h = 1e-6
        numeric = ((x + h) / (1.0 + x + h) - (x - h) / (1.0 + x - h)) / (2.0 * h)
        partial = (1.0 - x / (1.0 + x)) ** 2
        worst_d = max(worst_d, abs(numeric - partial))
    closed = worst_e < 1e-6 and worst_d < 1e-8

    ok = bool(concave and closed)
    detail = (
        "Two classical facts, read back on constructed instances rather than quoted. **(a) The "
        "lower envelope of a family of affine functions is concave**, so the slope carried by "
        "the owner can never rise: over %d drawn families the largest rise is **exactly "
        "%.1e**, and it is exact because concavity is not an approximation. **(b) The envelope "
        "theorem**, `E'(x) = dC_theta/dx` at the owner, holds within %.1e on a family with a "
        "closed form. **That family is `C_theta(x) = theta^2 + (1-theta)^2 x`, whose envelope "
        "is exactly `x/(1+x)` with owner `theta*(x) = x/(1+x)`**, and a grid of %d values of "
        "theta reproduces both within %.1e and %.1e. **The owner moves continuously from one "
        "end of the index set to the other, so every point of this envelope is a switch "
        "point**, which is what makes counting them the wrong question"
        % (families, worst_rise, worst_d, CLOSED_THETA, worst_e, worst_t))
    printed = ["affine families %d; largest rise in the owner's slope %.1e"
               % (families, worst_rise),
               "closed form: worst |E - x/(1+x)| %.2e; worst |theta* - x/(1+x)| %.2e; "
               "worst envelope-theorem gap %.2e" % (worst_e, worst_t, worst_d)]
    return ok, detail, {"affine_families": int(families),
                        "owner_slope_never_rises": bool(concave),
                        "closed_form_ok": bool(closed),
                        "closed_form_theta_points": CLOSED_THETA}, printed


# ------------------------------- B77-6a: refining the book does not enlarge the active set


def continuum_system(k):
    th = np.linspace(0.0, 1.0, k)
    a0, a1 = np.array(BASKET_A0), np.array(BASKET_A1)
    b0, b1 = np.array(BASKET_B0), np.array(BASKET_B1)
    A = np.zeros((k, GOODS))
    B = np.zeros((k, GOODS))
    for j, t in enumerate(th):
        A[j] = (1 - t) * a0 + t * a1
        B[j] = (1 - t) * b0 + t * b1
        B[j, j % GOODS] += 1.0
    return A, B


def check_active(rng):
    pin_a = expansion_factor(np.array(PIN_A, float), np.array(PIN_B, float))
    pinned = pin_a is not None and abs(pin_a - 2.0 ** (1.0 / 3.0)) < 1e-9
    rows = []
    ok = pinned
    for k in REFINE:
        A, B = continuum_system(k)
        a, x, p = solution(A, B)
        if a is None:
            ok = False
            continue
        act = int((x > ACTIVE_TOL).sum())
        pri = int((p > ACTIVE_TOL).sum())
        ok = ok and act <= GOODS
        rows.append((k, round(a, 8), act, pri))
    grew = len({r[2] for r in rows}) > 1
    ok = bool(ok and not grew and rows)
    detail = (
        "A continuum of processes on %d goods, discretised at %s. **The number of processes "
        "that run is %d at every one of them and does not grow**, while the expansion factor "
        "converges: %s. B75's Theorem 20(2) bounds the active set by the number of goods and "
        "**that bound never mentions how many processes there are**, so the book can be a "
        "continuum and at most `m` of it runs. **The thickness of the book does not enter.** "
        "The programme used here is written out again rather than imported, and it is pinned "
        "against an external number: on QuantEcon's published example it returns the cube root "
        "of two within 1e-9, %s"
        % (GOODS, ", ".join(str(k) for k in REFINE), rows[0][2],
           ", ".join("k=%d gives %.8f" % (k, a) for k, a, _, _ in rows),
           "which it does" if pinned else "which it does NOT"))
    printed = ["k, alpha, active, priced: "
               + "; ".join("%d %.8f %d %d" % r for r in rows),
               "pinned against the cube root of two: %s" % pinned]
    return ok, detail, {"goods": GOODS, "rows": [{"k": k, "alpha": a, "active": ac,
                                                  "priced": pr} for k, a, ac, pr in rows],
                        "active_count_grew": bool(grew),
                        "pinned_to_external_number": bool(pinned)}, printed


# ------------------------------- B77-6b: the switch count runs the other way


def check_switch_growth():
    xs = np.linspace(X_RANGE[0], X_RANGE[1], X_POINTS)
    rows = []
    for k in SWITCH_KS:
        th = np.linspace(0.0, 1.0, k)
        C = th[:, None] ** 2 + (1 - th[:, None]) ** 2 * xs[None, :]
        runs = owner_runs(np.argmin(C, axis=0))
        rows.append((k, len(runs) - 1, len(set(runs))))
    growing = all(rows[i][1] < rows[i + 1][1] for i in range(len(rows) - 1))
    ok = bool(growing)
    detail = (
        "The closed-form family of B77-5, discretised at %s. **The envelope's switch count "
        "grows at every refinement**: %s. Put beside B77-6a, **the two counts move in opposite "
        "directions under the same refinement**: the number of techniques that run stays at "
        "%d, and the number of times the owner changes grows without bound. **So in the "
        "continuum the count of switch points is not a property of the economy, it is a "
        "property of how finely the book was written**, and B76's `lambda_s(k)` bound, while "
        "still true at every `k`, says nothing in the limit. What replaces it is the "
        "derivative identity of B77-5"
        % (", ".join(str(k) for k in SWITCH_KS),
           ", ".join("k=%d gives %d" % (k, s) for k, s, _ in rows), GOODS))
    printed = ["k, switches, distinct owners: " + "; ".join("%d %d %d" % r for r in rows)]
    return ok, detail, {"rows": [{"k": k, "switches": s, "distinct_owners": d}
                                 for k, s, d in rows], "monotone_growth": bool(growing)}, printed


# ------------------------------- B77-6c: the label is not the invariant


def check_label(rng):
    wander = nonmono = families = 0
    worst_rise = -np.inf
    for _ in range(FAMILIES):
        co = rng.uniform(-1.0, 1.0, (3, 4))
        _, path, slope = family_envelope(co, FAMILY_THETA, FAMILY_X[2], quadratic=False)
        families += 1
        d = np.diff(path)
        wander += int((d > 1e-9).any() and (d < -1e-9).any())
        worst_rise = max(worst_rise, float(np.diff(slope).max()))
        nonmono += int(np.diff(slope).max() > 1e-9)
    # the quadratic class: search for a reversal, then refine the grid and watch it
    best, best_co = 0.0, None
    for _ in range(SEARCH):
        co = rng.uniform(-1.0, 1.0, (3, 4))
        _, _, slope = family_envelope(co, FAMILY_THETA, FAMILY_X[2], quadratic=True)
        rise = float(np.diff(slope).max())
        if rise > best:
            best, best_co = rise, co
    ladder = []
    if best_co is not None:
        for nt in REFINE_THETA:
            _, _, slope = family_envelope(best_co, nt, FAMILY_X[2] * (nt // FAMILY_THETA),
                                          quadratic=True)
            ladder.append((nt, round(float(np.diff(slope).max()), 8)))
    collapses = len(ladder) >= 2 and ladder[-1][1] < 0.5 * ladder[0][1]
    ok = bool(wander > 0 and nonmono == 0 and worst_rise <= 0.0 and collapses)
    detail = (
        "**In the affine class the owner's label wanders up and down on %d of %d families, "
        "while the slope it carries never rises on any of them**, the largest rise being "
        "exactly %.1e. So a continuum can send the owner back to a neighbourhood it left "
        "**without anything about the envelope turning around**: the index is a name, and "
        "names are dense. **The well-posed statement is about the coefficient the owner "
        "carries, not about which member carries it.** In the quadratic class a search over %d "
        "families was run for a slope that does rise. The largest candidate was taken through "
        "a grid ladder and **it collapses**: %s. **A real feature holds under refinement and a "
        "discretisation artefact halves**, so this is recorded as **not found in this family "
        "class, which is not the same as shown not to exist**"
        % (wander, families, worst_rise, SEARCH,
           ", ".join("theta grid %d gives %.6f" % (nt, v) for nt, v in ladder)))
    printed = ["affine: %d families, label wanders on %d, slope non-monotone on %d, "
               "largest rise %.1e" % (families, wander, nonmono, worst_rise),
               "quadratic ladder: " + "; ".join("%d -> %.6f" % (nt, v) for nt, v in ladder)]
    return ok, detail, {"affine_families": int(families), "label_wanders": int(wander),
                        "slope_non_monotone": int(nonmono),
                        "quadratic_search": int(SEARCH),
                        "quadratic_ladder": [{"theta_grid": nt, "largest_rise": v}
                                             for nt, v in ladder],
                        "candidate_collapses": bool(collapses)}, printed


# ------------------------------- B77-6d: land


def first_betti(n_nodes, edges):
    inc = np.zeros((n_nodes, len(edges)))
    for e, (u, v) in enumerate(edges):
        inc[u, e] += 1.0
        inc[v, e] -= 1.0
    return len(edges) - int(np.linalg.matrix_rank(inc))


def check_land():
    # a ring of 4 processes over 4 goods, then lands hung off it one at a time
    base_nodes = 4
    base_edges = [(i, (i + 1) % base_nodes) for i in range(base_nodes)]
    rows = []
    for k in LANDS:
        nodes = base_nodes + k
        edges = list(base_edges) + [(i % base_nodes, base_nodes + i) for i in range(k)]
        rows.append((k, first_betti(nodes, edges)))
    unchanged = len({b for _, b in rows}) == 1
    # total rent as a Riemann sum: q(theta) = 1 + theta, the marginal quality is theta = 0
    #: Left endpoints, not midpoints. The midpoint rule is exact for a linear integrand, so a
    #: midpoint sum reads 1/2 at every k and the check could not fail whatever the limit was.
    sums = []
    for k in RENT_KS:
        th = np.linspace(0.0, 1.0, k, endpoint=False)
        sums.append((k, round(float(((1.0 + th) - 1.0).sum() / k), 8)))
    converging = (all(sums[i][1] < sums[i + 1][1] for i in range(len(sums) - 1))
                  and abs(sums[-1][1] - 0.5) < 1e-4 and abs(sums[0][1] - 0.5) > 1e-2)
    ok = bool(unchanged and converging)
    detail = (
        "**Land qualities are pendant vertices**, so hanging one on adds a vertex and an edge "
        "and leaves `b_1` where it was: on a ring of %d processes, `b_1` is %d with %s lands "
        "alike. **A continuum of qualities therefore adds no cycles either**, since it adds "
        "none at any discretisation. **What does change is that the marginal quality becomes a "
        "single point of measure zero**: total rent is the Riemann sum %s, climbing to the "
        "integral `1/2`, **while the quality attaining the envelope pays nothing "
        "and contributes nothing to that total, yet still pins the wage**. B72's Theorem 17 "
        "survives the limit unchanged in kind, and the only thing the continuum takes away is "
        "the marginal land's share of the total, which was already zero"
        % (base_nodes, rows[0][1], ", ".join(str(k) for k, _ in rows),
           ", ".join("k=%d gives %.6f" % (k, v) for k, v in sums)))
    printed = ["lands, b_1: " + "; ".join("%d %d" % r for r in rows),
               "rent Riemann sums: " + "; ".join("%d %.6f" % s for s in sums)]
    return ok, detail, {"betti": [{"lands": k, "b1": b} for k, b in rows],
                        "b1_unchanged": bool(unchanged),
                        "rent_sums": [{"k": k, "total": v} for k, v in sums],
                        "converges_to_half": bool(converging)}, printed


# ------------------------------------------------------------------ record


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B77-5", "known_answer",
         "the concavity of a min of affine functions and the envelope theorem, read back on "
         "constructed instances, plus a closed-form envelope", check_classical(rng)),
        ("B77-6a", "instrument",
         "Theorem 22(1): refining the book does not enlarge the active set", check_active(rng)),
        ("B77-6b", "instrument",
         "Theorem 22(2): the switch count runs the other way, so counting stops being the "
         "question", check_switch_growth()),
        ("B77-6c", "instrument",
         "Theorem 22(3): the label wanders while the coefficient it carries does not",
         check_label(rng)),
        ("B77-6d", "instrument",
         "Theorem 22(4): land qualities are pendant, so a continuum of them adds no cycles",
         check_land()),
    ]
    mapping = {
        "B77-5": "read back -> PASS; not read back -> FAIL, and the code or the reading of the "
                 "source is fixed first",
        "B77-6": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed. "
                 "These read no data and decide nothing about the world",
    }
    print("=" * 78)
    print("B77-5 and B77-6: the known answers and the structural checks for "
          "docs/b77_continuum.md")
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
        "stage": "B77",
        "config": {
            "seed": SEED,
            "goods": GOODS,
            "refine": list(REFINE),
            "bisect_iters": BISECT_ITERS,
            "bisect_floor": BISECT_FLOOR,
            "active_tol": ACTIVE_TOL,
            "switch_ks": list(SWITCH_KS),
            "closed_theta_points": CLOSED_THETA,
            "families": FAMILIES,
            "family_theta": FAMILY_THETA,
            "refine_theta": list(REFINE_THETA),
            "search": SEARCH,
            "lands": list(LANDS),
            "rent_ks": list(RENT_KS),
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
