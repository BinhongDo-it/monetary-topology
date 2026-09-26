"""B103: what an action that changes the world state does to the prices set before it.

The time side of the framework's P3. Inside one world state claims move across dates
in both directions (lending and borrowing, `docs/b63_trilemma.md` section 1), so loops
through dated positions close there and are ordinary loop sums. An action that changes
the contract graph itself cannot be undone, and the world where it was taken and the
world where it was not are joined by no transaction. What is left to ask is what the
pre-action graph says about the relation the action creates, and that is a question
about reachability.

  B103-1  joining two positions that could not reach each other: before, their
          relative level is a free constant; after, the new edge fixes it.
  B103-2  joining two positions that could: rho^2 rises by w_e D^2 / (1 + w_e R),
          every potential moves by w_e D L^+ b / (1 + w_e R), and the relative level
          of the two ends moves by the fraction w_e R / (1 + w_e R) of D, where D is
          the new edge's term minus the pre-action difference and R is the effective
          resistance between the ends before the action.
  B103-3  the two are one formula: R growing without bound gives B103-1, R going to
          zero moves nothing.
  B103-4  B84-4's ladder, read back: the distances it recorded are the closed form on
          every rung, and the rate it printed, 0.849 to 1.003, is (1 + w_b R)/(1 + w_a R)
          at its low end and the floor at its high end.

Paper station: zero data. B84-4's tableaux are redrawn from B81's generator with the
seed B84 recorded, so B103-4 reads the same edges B84 wrote down.

Run:
    python experiments/b103_time_reachability.py
    python experiments/b103_time_reachability.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b81_cpd as B81                                    # noqa: E402
import b84_weighted_cpd as B84                           # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b103_time_reachability.json"
B84_RECORD = ROOT / "results" / "b84_weighted_cpd.json"

SEED = 103
#: Every labelled simple graph on 2 to this many vertices, and every missing edge.
MAX_ENUM_N = 5
#: Random weighted connected graphs for the closed form of B103-2.
SIZES = (8, 16, 32)
GRAPHS_PER_SIZE = 200
#: Identities between quantities of order one are compared at this tolerance. What
#: the run reaches is printed; only the tolerance goes into the record, because the
#: last digits belong to the BLAS build.
TOL = 1e-9
#: B84-4's distances run from 1e-1 down to 1e-13. This absolute tolerance sits about two
#: orders above the float floor of those fits (B84-6 recorded 6.3e-15 between its
#: two solvers) and below every distance on the first three rungs, so the comparison
#: is exact where it can be and says nothing where it cannot.
TOL_ABS_LADDER = 1e-12
#: Conductance of the one edge joining two blocks, walked down (B103-3).
BRIDGE_LADDER = (1.0, 1e-1, 1e-2, 1e-3, 1e-4)
#: Uniform weight on a complete graph with one edge missing, walked up (B103-3).
DENSE_LADDER = (1.0, 10.0, 100.0, 1e4)
#: B84 seeds criterion k with seed + k, and B84-4 is its fourth.
B84_4_INDEX = 3


def sig(x, digits=6):
    """A float through an explicit format spec, so the record does not carry BLAS digits."""
    return float(f"{x:.{digits}g}")


# ------------------------------------------------- the objects

def incidence(n, edges):
    B = np.zeros((len(edges), n))
    for k, (i, j) in enumerate(edges):
        B[k, i] -= 1.0
        B[k, j] += 1.0
    return B


def labels(n, edges):
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in edges:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    return [find(v) for v in range(n)]


def components(n, edges):
    """Isolated vertices count, as they do in b1 = E - V + c."""
    return len(set(labels(n, edges)))


def fit(n, edges, w, omega):
    """Theorem 5's projection in the inner product the weights define.

    Returns the minimum-norm nearest potential, rho^2, the weighted Laplacian and its
    pseudoinverse. Every nearest potential is this one plus a constant per component.

    The potential and the pseudoinverse come from the singular value decomposition of the
    weighted incidence matrix, whose condition number the Laplacian squares. On B103-3's
    bridge ladder, at its weakest rung, the two are about 9e2 and 7e5, and D reads constant
    across the ladder to about 4e-11 through the Laplacian and to about 5e-12 this way.
    """
    B = incidence(n, edges)
    w = np.asarray(w, dtype=float)
    omega = np.asarray(omega, dtype=float)
    L = B.T @ (w[:, None] * B)
    if not edges:
        return np.zeros(n), 0.0, L, np.zeros((n, n))
    s = np.sqrt(w)
    A = s[:, None] * B
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    keep = S > S.max() * max(A.shape) * np.finfo(float).eps
    U, S, Vt = U[:, keep], S[keep], Vt[keep]
    phi = Vt.T @ ((U.T @ (s * omega)) / S)
    Lp = (Vt.T / (S * S)) @ Vt
    res = omega - B @ phi
    return phi, float(np.sum(w * res * res)), L, Lp


def unit(n, i, j):
    b = np.zeros(n)
    b[j] += 1.0
    b[i] -= 1.0
    return b


def pinned(L, Lp, b):
    """Whether every nearest potential gives the same phi(j) - phi(i), i.e. b is in range(L)."""
    return bool(np.max(np.abs(L @ (Lp @ b) - b)) <= TOL)


def closed_form(Lp, phi, n, i, j, we, oe, mutate=None):
    """Proposition 2. `mutate` names a seeded error the self-test must catch."""
    b = unit(n, i, j)
    u = Lp @ b
    R = float(b @ u)
    delta = float(oe - (phi[j] - phi[i]))
    k = 1.0 if mutate == "drop_weight" else float(we)
    denom = 1.0 + k * R
    residual = delta * k * R / denom if mutate == "residual" else delta / denom
    return {"R": R, "delta": delta, "drho2": k * delta * delta / denom,
            "psi": (k * delta / denom) * u, "level": delta * k * R / denom,
            "residual": residual}


def random_connected(rng, n, extra):
    """A random spanning tree plus each other pair with probability `extra`, oriented at random."""
    order = [int(v) for v in rng.permutation(n)]
    und = set()
    for k in range(1, n):
        a, b = order[k], order[int(rng.integers(k))]
        und.add((min(a, b), max(a, b)))
    for (a, b) in itertools.combinations(range(n), 2):
        if (a, b) not in und and rng.random() < extra:
            und.add((a, b))
    und = sorted(und)
    edges = [(a, b) if rng.random() < 0.5 else (b, a) for (a, b) in und]
    return edges, und


# ------------------------------------------------- B103-1

def enumerate_actions(rng, max_n, wrong_components=False):
    """Every labelled simple graph on 2..max_n vertices, every missing edge added once."""
    rows = []
    for n in range(2, max_n + 1):
        pairs = list(itertools.combinations(range(n), 2))
        for code in range(1 << len(pairs)):
            edges = [pairs[k] for k in range(len(pairs)) if code >> k & 1]
            m = len(edges)
            w = np.exp(rng.normal(0.0, 1.0, m))
            om = rng.normal(0.0, 1.0, m)
            phi, rho2, L, Lp = fit(n, edges, w, om)
            lab = labels(n, edges)
            c0 = 1 if wrong_components else len(set(lab))
            present = set(edges)
            for (i, j) in pairs:
                if (i, j) in present:
                    continue
                we = float(np.exp(rng.normal(0.0, 1.0)))
                oe = float(rng.normal(0.0, 1.0))
                e1 = edges + [(i, j)]
                phi1, rho2_1, L1, Lp1 = fit(n, e1, np.append(w, we), np.append(om, oe))
                c1 = 1 if wrong_components else components(n, e1)
                b = unit(n, i, j)
                rows.append({"n": n, "same": lab[i] == lab[j],
                             "pinned_before": pinned(L, Lp, b),
                             "pinned_after": pinned(L1, Lp1, b),
                             "level_err": abs((phi1[j] - phi1[i]) - oe),
                             "drho2": rho2_1 - rho2,
                             "b1_before": m - n + c0, "b1_after": m + 1 - n + c1,
                             "c_before": c0, "c_after": c1})
    return rows


def judge_unreachable(rows):
    far = [r for r in rows if not r["same"]]
    near = [r for r in rows if r["same"]]
    bad_far = [r for r in far if r["pinned_before"] or not r["pinned_after"]
               or r["level_err"] > TOL or abs(r["drho2"]) > TOL
               or r["b1_after"] != r["b1_before"] or r["c_after"] != r["c_before"] - 1]
    bad_near = [r for r in near if not r["pinned_before"]
                or r["b1_after"] != r["b1_before"] + 1 or r["c_after"] != r["c_before"]]
    ok = bool(far) and bool(near) and not bad_far and not bad_near
    return ok, far, near, bad_far, bad_near


# ------------------------------------------------- B103-2

def closed_form_cases(rng, sizes, per_size, mutate=None):
    rows = []
    for n in sizes:
        extra = 3.0 / n
        for _ in range(per_size):
            while True:
                edges, und = random_connected(rng, n, extra)
                present = set(und)
                missing = [p for p in itertools.combinations(range(n), 2) if p not in present]
                if missing:
                    break
            a, b = missing[int(rng.integers(len(missing)))]
            i, j = (a, b) if rng.random() < 0.5 else (b, a)
            m = len(edges)
            w = np.exp(rng.normal(0.0, 1.0, m))
            om = rng.normal(0.0, 1.0, m)
            we = float(np.exp(rng.normal(0.0, 1.0)))
            oe = float(rng.normal(0.0, 1.0))
            phi0, r0, _, Lp0 = fit(n, edges, w, om)
            cf = closed_form(Lp0, phi0, n, i, j, we, oe, mutate)
            phi1, r1, _, _ = fit(n, edges + [(i, j)], np.append(w, we), np.append(om, oe))
            shift = phi1 - phi0
            shift = shift - shift.mean()
            psi = cf["psi"] - cf["psi"].mean()
            level = (phi1[j] - phi1[i]) - (phi0[j] - phi0[i])
            # the floor: the same action with the discrepancy set to zero, which moves nothing
            oz = float(phi0[j] - phi0[i])
            phiz, rz, _, _ = fit(n, edges + [(i, j)], np.append(w, we), np.append(om, oz))
            moved = phiz - phi0
            rows.append({"n": n, "we": we, "R": cf["R"],
                         "theta": we * cf["R"] / (1.0 + we * cf["R"]),
                         "d_rho2": abs((r1 - r0) - cf["drho2"]),
                         "d_psi": float(np.max(np.abs(shift - psi))),
                         "d_level": abs(level - cf["level"]),
                         "d_residual": abs((oe - (phi1[j] - phi1[i])) - cf["residual"]),
                         "floor": max(abs(rz - r0),
                                      float(np.max(np.abs(moved - moved.mean()))))})
    return rows


def judge_closed_form(rows):
    worst = max(max(r["d_rho2"], r["d_psi"], r["d_level"], r["d_residual"]) for r in rows)
    floor = max(r["floor"] for r in rows)
    return bool(rows) and worst <= TOL and floor <= TOL, worst, floor


# ------------------------------------------------- B103-3

def identity(x):
    return x


def limits(rng, theta_fn=identity):
    """Walk R up across a bridge and down inside a dense block, and measure what moves.

    The fraction of D absorbed into the ends' relative level is measured from the two fits,
    not read off Proposition 2, so the walk says something the closed form has not already
    said. `theta_fn` is applied to that measurement; the self-test plants an inverted one.
    Each walk's term on the new edge is set one to three units away from the pre-action
    difference, so no seed can make D small enough to blur the measured fraction.
    """
    size = 6
    ea, _ = random_connected(rng, size, 0.5)
    eb, _ = random_connected(rng, size, 0.5)
    eb = [(a + size, b + size) for (a, b) in eb]
    n = 2 * size
    base = ea + eb
    wb = np.exp(rng.normal(0.0, 1.0, len(base)))
    ob = rng.normal(0.0, 1.0, len(base))
    of = float(rng.normal(0.0, 1.0))
    i, j, we = 0, n - 1, 1.0
    edges = base + [(size - 1, size)]
    phi_first = fit(n, edges, np.append(wb, BRIDGE_LADDER[0]), np.append(ob, of))[0]
    z = float(rng.normal(0.0, 1.0))
    oe = float(phi_first[j] - phi_first[i]) + np.copysign(1.0 + abs(z), z)
    ladder = []
    for eps in BRIDGE_LADDER:
        w, om = np.append(wb, eps), np.append(ob, of)
        phi0, r0, _, Lp0 = fit(n, edges, w, om)
        cf = closed_form(Lp0, phi0, n, i, j, we, oe)
        e1, w1 = edges + [(i, j)], np.append(w, we)
        phi1, r1, _, _ = fit(n, e1, w1, np.append(om, oe))
        moved = float((phi1[j] - phi1[i]) - (phi0[j] - phi0[i]))
        # the floor: the same action with D set to zero, which moves nothing
        oz = float(phi0[j] - phi0[i])
        phiz, rz, _, _ = fit(n, e1, w1, np.append(om, oz))
        ladder.append({"conductance": eps, "R": cf["R"], "delta": cf["delta"],
                       "theta": float(theta_fn(moved / cf["delta"])),
                       "theta_closed": we * cf["R"] / (1.0 + we * cf["R"]),
                       "drho2": float(r1 - r0),
                       "gap": float(abs(oe - (phi1[j] - phi1[i]))),
                       "floor": float(max(abs(rz - r0), abs(oz - (phiz[j] - phiz[i]))))})
    phi0, r0, _, _ = fit(n, base, wb, ob)
    phi1, r1, _, _ = fit(n, base + [(i, j)], np.append(wb, we), np.append(ob, oe))
    removed = {"gap": float(abs(oe - (phi1[j] - phi1[i]))), "drho2": float(r1 - r0)}
    m = 8
    und = [p for p in itertools.combinations(range(m), 2) if p != (0, 1)]
    od = rng.normal(0.0, 1.0, len(und))
    phi_first = fit(m, und, np.full(len(und), DENSE_LADDER[0]), od)[0]
    z = float(rng.normal(0.0, 1.0))
    oe_d = float(phi_first[1] - phi_first[0]) + np.copysign(1.0 + abs(z), z)
    dense = []
    for s in DENSE_LADDER:
        w = np.full(len(und), s)
        phi0, r0, _, Lp0 = fit(m, und, w, od)
        cf = closed_form(Lp0, phi0, m, 0, 1, 1.0, oe_d)
        phi1, r1, _, _ = fit(m, und + [(0, 1)], np.append(w, 1.0), np.append(od, oe_d))
        moved = float((phi1[1] - phi1[0]) - (phi0[1] - phi0[0]))
        dense.append({"weight": s, "R": cf["R"], "delta": cf["delta"],
                      "theta": float(theta_fn(moved / cf["delta"])),
                      "theta_closed": cf["R"] / (1.0 + cf["R"]),
                      "level_move": abs(moved)})
    return ladder, removed, dense


def strictly(seq, direction):
    return all((b > a) if direction > 0 else (b < a) for a, b in zip(seq, seq[1:]))


def judge_limits(ladder, removed, dense):
    deltas = [r["delta"] for r in ladder]
    closed = max(abs(r["theta"] - r["theta_closed"]) for r in ladder + dense)
    checks = {
        "the same action with D set to zero moves nothing at any rung":
            max(r["floor"] for r in ladder) <= TOL,
        "D does not depend on the bridge's conductance": max(deltas) - min(deltas) <= TOL,
        "R rises as the bridge weakens": strictly([r["R"] for r in ladder], +1),
        "the measured fraction of D absorbed rises toward one":
            strictly([r["theta"] for r in ladder], +1),
        "the measured fraction is w_e R / (1 + w_e R) on every rung of both walks":
            closed <= TOL,
        "rho^2's increase falls toward zero": strictly([r["drho2"] for r in ladder], -1),
        "the new edge's residual falls toward zero": strictly([r["gap"] for r in ladder], -1),
        "with the bridge removed the level is pinned exactly":
            removed["gap"] <= TOL and abs(removed["drho2"]) <= TOL,
        "the measured fraction falls toward zero as the ends are tied tighter":
            strictly([r["theta"] for r in dense], -1),
        "the ends' relative level moves less and less":
            strictly([r["level_move"] for r in dense], -1),
    }
    checks = {k: bool(v) for k, v in checks.items()}
    return all(checks.values()), checks


# ------------------------------------------------- B103-4

def b84_ladders(record, wrong_baseline=False, inverted=False):
    """Redraw B84-4's tableaux and edges, and read the closed form against its record."""
    cfg = record["config"]
    ladder = [float(x) for x in cfg["vanishing"]]
    recorded = record["report"]["B84-4"]["cycle_edges"]
    rng = np.random.default_rng(int(cfg["seed"]) + B84_4_INDEX)
    rows = []
    for rep in range(int(cfg["reps"])):
        M, Rc = B84.SHAPES[int(rng.integers(len(B84.SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, Rc, complete=False)
        obs = B81.cells(mask)
        c0 = B81.components(M, Rc, obs)
        k = next(k for k in range(len(obs))
                 if B81.components(M, Rc, obs[:k] + obs[k + 1:]) == c0)
        kept = obs[:k] + obs[k + 1:]
        j0, r0 = obs[k]
        use = obs if wrong_baseline else kept
        B = B81.bipartite_incidence(M, Rc, use)
        rhs = np.array([y[a, c] for (a, c) in use])
        Lp = np.linalg.pinv(B.T @ B, hermitian=True)
        psi = Lp @ (B.T @ rhs)
        n = M + Rc
        b = np.zeros(n)
        b[M + r0] = 1.0
        b[j0] = -1.0
        u = Lp @ b
        R = float(b @ u)
        delta = float(y[j0, r0] - (psi[M + r0] - psi[j0]))
        base = float(np.max(np.abs(u[M:] - u[M])))
        pred = [abs(delta) * base * w / (1.0 + w * R) for w in ladder]
        row = recorded[rep]
        got = [float(x) for x in row["distance_to_deleted_solution"]]
        rates_got = [(got[p] / got[p + 1]) / (ladder[p] / ladder[p + 1])
                     for p in range(len(ladder) - 1)]
        if inverted:
            rates_pred = [(1.0 + ladder[p] * R) / (1.0 + ladder[p + 1] * R)
                          for p in range(len(ladder) - 1)]
        else:
            rates_pred = [(1.0 + ladder[p + 1] * R) / (1.0 + ladder[p] * R)
                          for p in range(len(ladder) - 1)]
        noise = [TOL_ABS_LADDER / got[p] + TOL_ABS_LADDER / got[p + 1]
                 for p in range(len(ladder) - 1)]
        rows.append({"edge": [int(j0), int(r0)], "edge_recorded": list(row["edge"]),
                     "R": R, "delta": delta, "pred": pred, "got": got,
                     "rates_got": rates_got, "rates_pred": rates_pred, "noise": noise,
                     "informative": [abs(1.0 - rp) > nz
                                     for rp, nz in zip(rates_pred, noise)]})
    return rows, [float(x) for x in record["report"]["B84-4"]["rate_in_the_weight"]]


def judge_ladders(rows, printed):
    same_edges = all(r["edge"] == r["edge_recorded"] for r in rows)
    worst = max(abs(p - g) for r in rows for p, g in zip(r["pred"], r["got"]))
    cells = [(r["rates_got"][p], r["rates_pred"][p], r["noise"][p], r["informative"][p], p + 1)
             for r in rows for p in range(len(r["rates_got"]))]
    lo = min(cells, key=lambda c: c[0])
    hi = max(cells, key=lambda c: c[0])
    lo_explained = lo[3] and abs(lo[0] - lo[1]) <= lo[2] * lo[0]
    hi_at_floor = not hi[3]
    printed_match = abs(lo[0] - printed[0]) <= 1e-12 and abs(hi[0] - printed[1]) <= 1e-12
    ok = same_edges and worst <= TOL_ABS_LADDER and lo_explained and hi_at_floor \
        and printed_match
    return ok, {"same_edges": same_edges, "worst": worst, "lo": lo, "hi": hi,
                "lo_explained": lo_explained, "hi_at_floor": hi_at_floor,
                "printed_match": printed_match}


# ------------------------------------------------- the run

def selftest() -> int:
    """Every criterion passes on a clean fixture and fails on a planted error (rule 11f)."""
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    rows = enumerate_actions(np.random.default_rng(7), 4)
    expect(judge_unreachable(rows)[0], "B103-1 fails on a clean fixture")
    near = [k for k, r in enumerate(rows) if r["same"]]
    expect(bool(near), "seed not planted: the fixture has no reachable pair")
    if near:
        planted = [dict(r) for r in rows]
        planted[near[0]]["same"] = False
        expect(not judge_unreachable(planted)[0],
               "B103-1 passes a reachable pair read as unreachable")
    expect(not judge_unreachable(enumerate_actions(np.random.default_rng(7), 4,
                                                   wrong_components=True))[0],
           "B103-1 passes with component counting broken")

    clean = closed_form_cases(np.random.default_rng(8), (8,), 10)
    expect(judge_closed_form(clean)[0], "B103-2 fails on a clean fixture")
    dropped = closed_form_cases(np.random.default_rng(8), (8,), 10, mutate="drop_weight")
    expect(any(abs(r["we"] - 1.0) > 1e-3 for r in dropped),
           "seed not planted: every new edge has weight one")
    expect(not judge_closed_form(dropped)[0], "B103-2 passes with the weight dropped")
    expect(not judge_closed_form(closed_form_cases(np.random.default_rng(8), (8,), 10,
                                                   mutate="residual"))[0],
           "B103-2 passes with the residual written as the moved fraction")

    expect(judge_limits(*limits(np.random.default_rng(9)))[0],
           "B103-3 fails on a clean fixture")
    expect(not judge_limits(*limits(np.random.default_rng(9), theta_fn=lambda x: 1.0 - x))[0],
           "B103-3 passes with the residual's share read as the level's")

    record = json.loads(B84_RECORD.read_text(encoding="utf-8"))
    expect(judge_ladders(*b84_ladders(record))[0], "B103-4 fails on B84's record")
    expect(not judge_ladders(*b84_ladders(record, wrong_baseline=True))[0],
           "B103-4 passes with the full tableau as the pre-action baseline")
    expect(not judge_ladders(*b84_ladders(record, inverted=True))[0],
           "B103-4 passes with the rate inverted")

    for f in fails:
        print(f"SELFTEST FAIL  {f}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    criteria, report = [], {}
    t0 = time.perf_counter()

    # B103-1
    rows = enumerate_actions(np.random.default_rng(a.seed + 0), MAX_ENUM_N)
    ok, far, near, bad_far, bad_near = judge_unreachable(rows)
    per_n = {}
    for r in rows:
        d = per_n.setdefault(str(r["n"]), {"unreachable_ends": 0, "reachable_ends": 0})
        d["unreachable_ends" if not r["same"] else "reachable_ends"] += 1
    print(f"B103-1  worst level error {max(r['level_err'] for r in far):.2e}, "
          f"worst rho^2 change {max(abs(r['drho2']) for r in far):.2e}")
    criteria.append({
        "name": "B103-1", "kind": "own_reading", "passed": bool(ok),
        "statement": "joining two positions that could not reach each other: before, their "
                     "relative level is a free constant; after, the new edge fixes it",
        "detail": (f"every labelled simple graph on 2 to {MAX_ENUM_N} vertices, every missing "
                   f"edge added once: {len(far)} additions join two components and {len(near)} "
                   f"do not. On all {len(far) - len(bad_far)} of the first kind the difference "
                   f"phi(j) - phi(i) is not fixed by any nearest potential before the action, "
                   f"is fixed after it at exactly the new edge's term, rho^2 does not move, "
                   f"b1 holds and the component count falls by one. On all "
                   f"{len(near) - len(bad_near)} of the second kind the difference was already "
                   f"fixed before, b1 rises by one and the component count holds. "
                   f"Compared below {TOL:.0e}")})
    report["B103-1"] = {"per_vertex_count": per_n, "compared_below": f"{TOL:.0e}",
                        "failures": len(bad_far) + len(bad_near)}

    # B103-2
    rows2 = closed_form_cases(np.random.default_rng(a.seed + 1), SIZES, GRAPHS_PER_SIZE)
    ok2, worst2, floor2 = judge_closed_form(rows2)
    print(f"B103-2  worst closed-form discrepancy {worst2:.2e}, floor {floor2:.2e}")
    by_size = {}
    for n in SIZES:
        sub = [r for r in rows2 if r["n"] == n]
        th = np.array([r["theta"] for r in sub])
        rr = np.array([r["R"] for r in sub])
        by_size[str(n)] = {"graphs": len(sub),
                           "rewriting_fraction_min_median_max":
                               [sig(th.min(), 4), sig(float(np.median(th)), 4), sig(th.max(), 4)],
                           "effective_resistance_min_median_max":
                               [sig(rr.min(), 4), sig(float(np.median(rr)), 4), sig(rr.max(), 4)]}
    criteria.append({
        "name": "B103-2", "kind": "own_reading", "passed": bool(ok2),
        "statement": "joining two positions that could reach each other: rho^2 rises by "
                     "w_e D^2 / (1 + w_e R), every potential moves by w_e D L^+ b / (1 + w_e R), "
                     "and the ends' relative level moves by the fraction w_e R / (1 + w_e R) of D",
        "detail": (f"{len(rows2)} random weighted connected graphs on {', '.join(map(str, SIZES))} "
                   f"vertices, a missing edge with a random weight and term added to each. The "
                   f"three closed forms and the new edge's residual D / (1 + w_e R) agree with "
                   f"the numerical projection on every graph, below {TOL:.0e}, and the same "
                   f"action with D set to zero moves nothing, also below {TOL:.0e}. The "
                   f"fraction of the discrepancy absorbed into the ends' relative level runs "
                   f"from {min(r['theta'] for r in rows2):.3f} to "
                   f"{max(r['theta'] for r in rows2):.3f} across these graphs")})
    report["B103-2"] = {"by_size": by_size, "compared_below": f"{TOL:.0e}"}

    # B103-3
    ladder, removed, dense = limits(np.random.default_rng(a.seed + 2))
    ok3, checks3 = judge_limits(ladder, removed, dense)
    spread = max(r["delta"] for r in ladder) - min(r["delta"] for r in ladder)
    floor3 = max(r["floor"] for r in ladder)
    for r in ladder:
        print(f"B103-3  bridge {r['conductance']:.0e}  R {r['R']:.6g}  fraction measured "
              f"{r['theta']:.9f} closed form {r['theta_closed']:.9f}  rho^2 up "
              f"{r['drho2']:.3e}  residual {r['gap']:.3e}")
    share = max(abs(r["theta"] - r["theta_closed"]) for r in ladder + dense)
    print(f"B103-3  D {ladder[0]['delta']:.6f}, spread over the ladder {spread:.2e}, "
          f"floor {floor3:.2e}, worst |measured share - closed form| {share:.2e}")
    print(f"B103-3  bridge removed: residual {removed['gap']:.2e}, rho^2 change "
          f"{removed['drho2']:.2e}")
    for r in dense:
        print(f"B103-3  dense weight {r['weight']:.0e}  R {r['R']:.6g}  fraction measured "
              f"{r['theta']:.6e} closed form {r['theta_closed']:.6e}  level moves "
              f"{r['level_move']:.3e}")
    criteria.append({
        "name": "B103-3", "kind": "own_reading", "passed": bool(ok3),
        "statement": "the two cases are one formula: R growing without bound gives B103-1, "
                     "R going to zero moves nothing",
        "detail": (f"two six-vertex blocks joined by one edge whose conductance walks down "
                   f"{', '.join(f'{e:.0e}' for e in BRIDGE_LADDER)}, and an action joining "
                   f"the far ends. R rises from {ladder[0]['R']:.3f} to {ladder[-1]['R']:.1f}; "
                   f"the fraction of D absorbed into the ends' relative level, measured from "
                   f"the two fits, rises from {ladder[0]['theta']:.4f} to "
                   f"{ladder[-1]['theta']:.6f}; the rise in rho^2 and the new edge's residual "
                   f"fall toward zero; D itself does not move; and with the joining edge "
                   f"removed the level is pinned exactly. At the other end, a complete graph "
                   f"on eight vertices less the joined pair, weights walked up "
                   f"{', '.join(f'{s:.0e}' for s in DENSE_LADDER)}: the measured fraction "
                   f"falls from {dense[0]['theta']:.4f} to {dense[-1]['theta']:.2e} and the "
                   f"ends' relative level moves less at every step. On every rung of both "
                   f"walks the measured fraction is w_e R / (1 + w_e R), compared below "
                   f"{TOL:.0e}. Checks: "
                   + "; ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in checks3.items()))})
    report["B103-3"] = {
        "bridge_ladder": [{"conductance": r["conductance"], "R": sig(r["R"]),
                           "D": sig(r["delta"]), "fraction_measured": sig(r["theta"], 9),
                           "rho2_rise": sig(r["drho2"], 4),
                           "new_edge_residual": sig(r["gap"], 4)} for r in ladder],
        "dense_ladder": [{"weight": r["weight"], "R": sig(r["R"]),
                          "fraction_measured": sig(r["theta"], 6),
                          "level_move": sig(r["level_move"], 4)} for r in dense],
        "compared_below": f"{TOL:.0e}",
        "checks": checks3}

    # B103-4
    record = json.loads(B84_RECORD.read_text(encoding="utf-8"))
    rows4, printed = b84_ladders(record)
    ok4, j4 = judge_ladders(rows4, printed)
    print(f"B103-4  worst |closed form - B84 record| over all rungs {j4['worst']:.2e}")
    for r in rows4:
        print(f"B103-4  edge {r['edge']}  R {r['R']:.6f}  rates recorded "
              f"{[round(x, 7) for x in r['rates_got']]}  predicted "
              f"{[round(x, 7) for x in r['rates_pred']]}  informative {r['informative']}")
    lo, hi = j4["lo"], j4["hi"]
    criteria.append({
        "name": "B103-4", "kind": "known_answer", "passed": bool(ok4),
        "statement": "B84-4's ladder is the closed form: its distances on every rung, and the "
                     "range of the rate it printed",
        "detail": (f"B84-4's {len(rows4)} tableaux redrawn from B81's generator with seed "
                   f"{record['config']['seed']} + {B84_4_INDEX}; the same edges come back "
                   f"({'yes' if j4['same_edges'] else 'NO'}). With R computed from each "
                   f"tableau, not fitted, the closed form matches the recorded distance on "
                   f"every rung below {TOL_ABS_LADDER:.0e}. The printed low end "
                   f"{printed[0]:.6f} is the rate on step {lo[4]} of {len(rows4[0]['rates_got'])}, "
                   f"informative, and equals (1 + w_b R)/(1 + w_a R) there to its noise; the "
                   f"printed high end {printed[1]:.6f} is the rate on step {hi[4]}, where the "
                   f"closed form bends by less than the float noise of the distances it divides, "
                   f"so the rate carries nothing. So B84's reading that the approach is linear "
                   f"holds as the weight goes to zero, and the spread it printed is the curvature "
                   f"(1 + w_b R)/(1 + w_a R) at the top of the ladder and noise at the bottom")})
    report["B103-4"] = {
        "edges": [{"edge": r["edge"], "R": sig(r["R"]), "D": sig(r["delta"]),
                   "rate_recorded": [sig(x, 7) for x in r["rates_got"]],
                   "rate_closed_form": [sig(x, 7) for x in r["rates_pred"]],
                   "rate_informative": r["informative"]} for r in rows4],
        "printed_range": [sig(printed[0], 9), sig(printed[1], 9)],
        "compared_below": f"{TOL_ABS_LADDER:.0e}"}

    print(f"(run took {time.perf_counter() - t0:.1f} s; not written to the record)")
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['detail'][:180]}")

    rec = {"stage": "B103",
           "config": {"seed": a.seed, "max_enum_n": MAX_ENUM_N, "sizes": list(SIZES),
                      "graphs_per_size": GRAPHS_PER_SIZE, "tol": f"{TOL:.0e}",
                      "tol_abs_ladder": f"{TOL_ABS_LADDER:.0e}",
                      "bridge_ladder": list(BRIDGE_LADDER), "dense_ladder": list(DENSE_LADDER),
                      "b84_record": "results/b84_weighted_cpd.json",
                      "imports": ["b81_cpd", "b84_weighted_cpd"]},
           "criteria": criteria, "report": report}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
