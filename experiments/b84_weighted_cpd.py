"""B84: the weighted country-product-dummy method, where weights change the metric.

`docs/b81_cpd.md` section 6 states, and says it does not check, that the weighted
CPD the International Comparison Program runs is the same projection in a weighted
inner product, so the weights change which coboundary is nearest without changing
that it is one. **This station checks it, and finds the boundary where it stops
being true.**

Paper station: zero data. The tableau generator, the design matrix, the incidence
matrix and the cycle basis are B81's and are imported rather than rewritten, so a
disagreement between the two stations is a real disagreement.

Run:
    python experiments/b84_weighted_cpd.py
    python experiments/b84_weighted_cpd.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b81_cpd as B81                                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b84_weighted_cpd.json"

SEED = 84
REPS = 10
SHAPES = ((4, 5), (5, 6), (6, 6), (7, 5), (8, 7))
#: How spread the weights are, as the standard deviation of log w. Zero is the
#: unweighted case and is included so the family contains its own baseline.
DISPERSIONS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
#: The ladder B84-4 walks a single edge's weight down. It stops short of zero on
#: purpose: the claim is about the limit, and the limit has to be approached to be
#: seen rather than evaluated once at the endpoint.
VANISHING = (1e-1, 1e-3, 1e-6, 1e-9, 1e-12)


# ------------------------------------------------- the weighted fit

def weighted_fit(y, mask, w):
    """Weighted least squares of log price on the dummies. Path A, lstsq.

    Exactly B81's fit with each row scaled by the square root of its weight, which
    is what a weighted inner product does to a least squares problem.
    """
    M, R = mask.shape
    obs = B81.cells(mask)
    X = B81.cpd_design(M, R, obs)
    rhs = np.array([y[j, r] for (j, r) in obs])
    s = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(X * s[:, None], rhs * s, rcond=None)
    return coef, X @ coef, rhs, obs, X


def laplacian_fit(y, mask, w):
    """The same solve read as a weighted graph Laplacian. Path B.

    `D35` second clause: the normal equations make these two equal by a theorem, so
    this is an implementation check on the code and not a second route to the fact.
    """
    M, R = mask.shape
    obs = B81.cells(mask)
    B = B81.bipartite_incidence(M, R, obs)
    rhs = np.array([y[j, r] for (j, r) in obs])
    L = B.T @ (w[:, None] * B)
    psi, *_ = np.linalg.lstsq(L, B.T @ (w * rhs), rcond=None)
    return psi, B @ psi


def parities(coef, M):
    """The country side, gauged to the first country so two fits are comparable."""
    beta = coef[M:]
    return beta - beta[0]


def draw_weights(rng, n, dispersion):
    if dispersion == 0.0:
        return np.ones(n)
    return np.exp(rng.normal(0.0, dispersion, n))


# ------------------------------------------------- criteria

def crit_reproduces(rng, reps):
    """B84-1: unit weights give B81's fit, the fit ignores an overall scale, and the
    gauge is both harmless and exercised.

    The gauge clause is here because nothing else holds it. `lstsq` on a rank
    deficient design returns the minimum norm solution, and which solution that is
    depends on the weights, so comparing raw coefficients across two weightings
    compares a real difference plus an arbitrary shift. Both halves are needed: the
    parity differences must not move when the base country changes, **and** the raw
    coefficients must move under a change of weights, or the gauge was never
    exercised and its being harmless says nothing.
    """
    worst_unit, worst_scale, worst_base, least_raw_shift = 0.0, 0.0, 0.0, float("inf")
    connected = 0
    for _ in range(reps):
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False)
        obs = B81.cells(mask)
        n = len(obs)
        c0, f0, _, _, _ = B81.cpd_fit(y, mask)
        c1, f1, _, _, _ = weighted_fit(y, mask, np.ones(n))
        worst_unit = max(worst_unit, float(np.max(np.abs(f0 - f1))))
        w = draw_weights(rng, n, 1.0)
        pa = parities(weighted_fit(y, mask, w)[0], M)
        pb = parities(weighted_fit(y, mask, 7.3 * w)[0], M)
        worst_scale = max(worst_scale, float(np.max(np.abs(pa - pb))))
        if B81.components(M, R, obs) != 1:
            continue                    # one gauge fixes one component, not two
        connected += 1
        beta_u = weighted_fit(y, mask, np.ones(n))[0][M:]
        beta_w = weighted_fit(y, mask, w)[0][M:]
        # re-gauging to another base leaves every pairwise difference alone
        for b in range(1, R):
            g0 = beta_w - beta_w[0]
            gb = beta_w - beta_w[b]
            worst_base = max(worst_base,
                             float(np.max(np.abs((g0 - g0[b]) - gb))))
        # and the raw coefficients do move, so the gauge had something to remove
        least_raw_shift = min(least_raw_shift,
                              float(np.max(np.abs(beta_u - beta_w))))
    ok = (worst_unit < 1e-9 and worst_scale < 1e-9 and worst_base < 1e-9
          and connected > 0 and least_raw_shift > 1e-6)
    detail = (f"unit weights reproduce B81's fitted values to {worst_unit:.2e} over "
              f"{reps} tableaux, importing B81's solver rather than a second copy of "
              f"it; scaling every weight by 7.3 moves the parities by {worst_scale:.2e}. "
              f"On the {connected} connected tableaux, re-gauging to each of the other "
              f"base countries moves no pairwise parity difference by more than "
              f"{worst_base:.2e}, **while the raw coefficients move by at least "
              f"{least_raw_shift:.4f} when the weights change**, which is what makes "
              f"the first half of that sentence say anything")
    return ok, detail, {"worst_unit": worst_unit, "worst_scale": worst_scale,
                        "worst_base_change": worst_base,
                        "least_raw_shift_under_weights": least_raw_shift,
                        "connected_tableaux": connected}


def crit_coboundary(rng, reps):
    """B84-2: the weighted fit telescopes and the raw log prices do not."""
    worst_fit, least_raw, cycles_seen = 0.0, float("inf"), 0
    for _ in range(reps):
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False)
        obs = B81.cells(mask)
        n = len(obs)
        w = draw_weights(rng, n, 1.5)
        _, fitted, rhs, _, _ = weighted_fit(y, mask, w)
        Z = B81.cycle_basis(M, R, obs)
        if not len(Z):
            continue
        cycles_seen += len(Z)
        worst_fit = max(worst_fit, float(np.max(np.abs(Z @ fitted))))
        least_raw = min(least_raw, float(np.max(np.abs(Z @ rhs))))
    # Without this the criterion passes on zero cycles: nothing raises `worst_fit`
    # and `least_raw` stays at infinity, so both halves hold vacuously (rule 11f).
    ok = cycles_seen > 0 and worst_fit < 1e-9 and least_raw > 1e-3
    return ok, (f"every cycle of the bipartite graph sums to at most {worst_fit:.2e} on "
                f"the weighted fitted values, at dispersion 1.5, while the same cycles "
                f"on the raw log prices reach at least {least_raw:.4f} on every "
                f"tableau. **The second half is what stops this reading an identity**: "
                f"a tableau whose raw prices already telescoped would pass the first "
                f"half for free, and so would a tableau with no cycle at all, which "
                f"is why the count is in the verdict: {cycles_seen} cycles were "
                f"tested"), {"worst_fitted_cycle": worst_fit,
                             "least_raw_cycle": least_raw,
                             "cycles_tested": cycles_seen}


def crit_metric_not_topology(rng, reps):
    """B84-3: b1, the rank deficiency and the discarded dimension do not move; the
    parities do. Both halves are required."""
    rows, topo_moved, par_moved = [], 0, 0
    for _ in range(reps):
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False)
        obs = B81.cells(mask)
        n = len(obs)
        B = B81.bipartite_incidence(M, R, obs)
        c = B81.components(M, R, obs)
        b1_form = len(obs) - (M + R) + c
        base = None
        seen_b1, seen_def, spread = set(), set(), 0.0
        for d in DISPERSIONS:
            w = draw_weights(rng, n, d)
            coef, _, _, _, X = weighted_fit(y, mask, w)
            s = np.sqrt(w)
            seen_def.add((M + R) - int(np.linalg.matrix_rank(X * s[:, None])))
            seen_b1.add(len(obs) - int(np.linalg.matrix_rank(B)))
            p = parities(coef, M)
            if base is None:
                base = p
            else:
                spread = max(spread, float(np.max(np.abs(p - base))))
        rows.append({"M": M, "R": R, "edges": n, "components": c,
                     "b1_closed_form": b1_form, "b1_seen": sorted(seen_b1),
                     "rank_deficiency_seen": sorted(seen_def),
                     "parity_spread_over_weights": spread})
        if len(seen_b1) == 1 and len(seen_def) == 1 and seen_def == {c} \
           and seen_b1 == {b1_form}:
            topo_moved += 0
        else:
            topo_moved += 1
        if spread > 1e-6:
            par_moved += 1
    ok = topo_moved == 0 and par_moved == reps
    widest = max(r["parity_spread_over_weights"] for r in rows)
    detail = (f"over {len(DISPERSIONS)} weight dispersions on {reps} tableaux: the "
              f"first Betti number and the design's rank deficiency hold at every "
              f"dispersion on {reps - topo_moved} of {reps}, equal to the closed form "
              f"and to the component count; **and the parities move on {par_moved} of "
              f"{reps}**, by up to {widest:.4f}. Both halves are required: an unchanged "
              f"topology on its own is also what a weight that never reached the solve "
              f"would look like")
    return ok, detail, {"rows": rows, "topology_moved_on": topo_moved,
                        "parities_moved_on": par_moved,
                        "widest_parity_spread": widest}


def crit_zero_is_deletion(rng, reps):
    """B84-4: a weight going to zero is an edge leaving the graph.

    One edge of each kind per tableau where the tableau has one. The first version
    took edge zero and broke, which drew ten cycle edges and no bridge across ten
    tableaux, so the half of the statement about bridges was never reached: a clause
    that is never evaluated cannot fail (rule 11f).
    """
    cyc, bridge = [], []
    for _ in range(reps):
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False)
        obs = B81.cells(mask)
        n = len(obs)
        c0 = B81.components(M, R, obs)
        b0 = n - (M + R) + c0
        want = {"cycle": True}
        for i in range(n):
            kept = obs[:i] + obs[i + 1:]
            c1 = B81.components(M, R, kept)
            b1 = len(kept) - (M + R) + c1
            is_bridge = c1 > c0
            key = "bridge" if is_bridge else "cycle"
            if not want[key]:
                continue
            want[key] = False
            sub = np.zeros((M, R), dtype=bool)
            for (j, r) in kept:
                sub[j, r] = True
            # a bridge splits the graph, so the deleted solution is two parities
            # that no weight makes comparable and there is nothing to converge to
            target = None if is_bridge else parities(B81.cpd_fit(y, sub)[0], M)
            ladder = []
            for eps in VANISHING:
                w = np.ones(n)
                w[i] = eps
                p = parities(weighted_fit(y, mask, w)[0], M)
                ladder.append(None if target is None
                              else float(np.max(np.abs(p - target))))
            row = {"edge": [int(obs[i][0]), int(obs[i][1])], "bridge": bool(is_bridge),
                   "b1_before": b0, "b1_after": b1, "components_before": c0,
                   "components_after": c1, "distance_to_deleted_solution": ladder}
            (bridge if is_bridge else cyc).append(row)
            if not any(want.values()):
                break

    # No bridge exists at this density: the graphs come back two-edge-connected, so
    # the boundary case is not reachable on the family the rest of the station uses.
    # That is itself a reading, and the half of the statement about bridges needs a
    # family where a bridge exists. Sparse tableaux give pendant edges, which are.
    sparse_density, tries = 0.30, 0
    while len(bridge) < reps and tries < 200:
        tries += 1
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False, density=sparse_density)
        obs = B81.cells(mask)
        n = len(obs)
        c0 = B81.components(M, R, obs)
        b0 = n - (M + R) + c0
        for i in range(n):
            kept = obs[:i] + obs[i + 1:]
            c1 = B81.components(M, R, kept)
            if c1 <= c0:
                continue
            bridge.append({"edge": [int(obs[i][0]), int(obs[i][1])], "bridge": True,
                           "b1_before": b0,
                           "b1_after": len(kept) - (M + R) + c1,
                           "components_before": c0, "components_after": c1,
                           "distance_to_deleted_solution": [None] * len(VANISHING),
                           "density": sparse_density})
            break

    good_cyc = [r for r in cyc if r["b1_after"] == r["b1_before"] - 1
                and r["distance_to_deleted_solution"][-1]
                < r["distance_to_deleted_solution"][0]
                and r["distance_to_deleted_solution"][-1] < 1e-6]
    good_br = [r for r in bridge if r["components_after"] == r["components_before"] + 1
               and r["b1_after"] == r["b1_before"]]
    ok = bool(cyc) and bool(bridge) \
        and len(good_cyc) == len(cyc) and len(good_br) == len(bridge)
    worst_tail = max((r["distance_to_deleted_solution"][-1] for r in cyc), default=0.0)
    # The rate, read off the ladder rather than asserted: each step divides the
    # weight by a known factor, so the ratio of successive distances says what power
    # of the weight the approach goes as.
    rates = []
    for r in cyc:
        d = r["distance_to_deleted_solution"]
        for a, b, wa, wb in zip(d, d[1:], VANISHING, VANISHING[1:]):
            if b and b > 0:
                rates.append((a / b) / (wa / wb))
    rate_lo = min(rates) if rates else float("nan")
    rate_hi = max(rates) if rates else float("nan")
    detail = (f"driving one edge's weight down the ladder {VANISHING}. **Inside a "
              f"cycle**: on {len(good_cyc)} of {len(cyc)} edges the parities converge "
              f"to the solution with that edge deleted, worst distance at the bottom of "
              f"the ladder {worst_tail:.2e}, while the first Betti number drops by one "
              f"only at zero itself. The approach is linear in the weight, read off "
              f"the ladder rather than assumed: dividing the weight by a factor "
              f"divides the distance by the same factor, ratio between {rate_lo:.3f} "
              f"and {rate_hi:.3f} over every step of every edge. "
              f"**On a bridge**: {len(good_br)} of {len(bridge)} "
              f"raise the component count by one instead and leave the Betti number "
              f"alone, so what a vanishing weight costs there is not a dimension of "
              f"residual but the comparability of two parities. Both kinds are drawn "
              f"on purpose. **At the density the rest of this station uses the graphs "
              f"come back two-edge-connected**, so no bridge exists there at all and "
              f"the boundary case is unreachable: the {len(bridge)} bridges are drawn "
              f"from tableaux at density {bridge[0]['density'] if bridge else 0}, "
              f"where pendant edges appear. A first version took whichever edge came "
              f"first, drew ten cycles and no bridge, and left this half never "
              f"evaluated")
    return ok, detail, {"cycle_edges": cyc, "bridge_edges": bridge,
                        "rate_in_the_weight": [rate_lo, rate_hi]}


def crit_how_far(rng, reps):
    """B84-5: how far the two projections get, printed against dispersion."""
    table = {}
    for d in DISPERSIONS:
        gaps = []
        for _ in range(reps):
            M, R = SHAPES[int(rng.integers(len(SHAPES)))]
            y, mask = B81.draw_tableau(rng, M, R, complete=False)
            n = len(B81.cells(mask))
            p0 = parities(weighted_fit(y, mask, np.ones(n))[0], M)
            p1 = parities(weighted_fit(y, mask, draw_weights(rng, n, d))[0], M)
            # The spread of the difference, not the largest difference. Parities are
            # only defined up to one constant, so the largest difference carries
            # whatever gauge each fit happened to land on; the spread is the same
            # number under any gauge, and it is the largest change in any pairwise
            # comparison, which is what a user of the parities would feel.
            diff = p0 - p1
            gaps.append(float(np.max(diff) - np.min(diff)))
        table[d] = {"median": float(np.median(gaps)), "max": float(np.max(gaps))}
    ok = bool(table)
    detail = ("largest change in any pairwise parity comparison between the weighted "
              "and the unweighted fit, in logs, by the dispersion of log weight. The "
              "spread of the difference rather than its largest element, since a "
              "parity vector is defined only up to one constant and the spread is the "
              "same number under any gauge: "
              + "; ".join(f"sd {d} -> median {v['median']:.4f} max {v['max']:.4f}"
                          for d, v in table.items())
              + ". No line is drawn on any of these: the reading is that the two "
                "projections are the same operation with different answers, and how "
                "different is a property of the weights rather than a verdict")
    return ok, detail, {"by_dispersion": {str(k): v for k, v in table.items()}}


def crit_two_paths(rng, reps):
    """B84-6: lstsq against the weighted Laplacian. An implementation check."""
    worst = 0.0
    for _ in range(reps):
        M, R = SHAPES[int(rng.integers(len(SHAPES)))]
        y, mask = B81.draw_tableau(rng, M, R, complete=False)
        n = len(B81.cells(mask))
        w = draw_weights(rng, n, 1.0)
        _, fa, _, _, _ = weighted_fit(y, mask, w)
        _, fb = laplacian_fit(y, mask, w)
        worst = max(worst, float(np.max(np.abs(fa - fb))))
    ok = worst < 1e-8
    return ok, (f"the weighted design solved by least squares and the weighted graph "
                f"Laplacian `L_w psi = d0' W y` give fitted values agreeing to "
                f"{worst:.2e} over {reps} tableaux. **This is an implementation check "
                f"and not a second route** (`D35` second clause): the normal equations "
                f"make the two equal by a theorem, so what it can catch is a coding "
                f"error, which is worth exactly that"), {"worst_gap": worst}


def crit_registration():
    """B84-7: B81's section 6 registered this, and the same round has to write back.

    The first version of this check asked only whether section 6 still said the
    claim was unchecked, which is true both before the write-back and after it,
    since the corrected sentence quotes its own old wording. **A bookkeeping check
    that passes whether or not the bookkeeping was done is not a check** (rule 11f).
    It now asks for both halves: the claim is there, and this station is named
    against it.
    """
    text = (ROOT / "docs" / "b81_cpd.md").read_text(encoding="utf-8")
    carries = "stated and not checked here" in text
    written_back = "b84_weighted_cpd.md" in text
    ok = carries and written_back
    detail = ("B81 section 6 "
              + ("carries the claim it registered" if carries else
                 "**no longer carries the claim it registered**, so either it was "
                 "closed elsewhere or the text moved")
              + ", and "
              + ("names this station against it" if written_back else
                 "**does not name this station: the write-back is missing**")
              + ". `D20`: the source of a registration is written back in the round "
                "that discharges it, not later.")
    return ok, detail, {"b81_section_6_carries_the_claim": carries,
                        "b81_section_6_names_b84": written_back}


# ------------------------------------------------- self-test

def selftest() -> int:
    """Rule 11f: seed the failure rather than ask whether one is possible."""
    fails = []
    rng = np.random.default_rng(1234)

    # a two-by-two complete tableau has exactly one cycle, done by hand
    y = np.array([[0.0, 1.0], [2.0, 4.0]])
    mask = np.ones((2, 2), dtype=bool)
    obs = B81.cells(mask)
    Z = B81.cycle_basis(2, 2, obs)
    if len(Z) != 1:
        fails.append(f"a 2x2 complete tableau has one cycle, the basis has {len(Z)}")
    raw = np.array([y[j, r] for (j, r) in obs])
    if abs(float((Z @ raw)[0])) < 1e-9:
        fails.append("the hand tableau's raw prices telescope, so it cannot show that "
                     "the fit is what makes them telescope")
    for w in (np.ones(4), np.array([5.0, 0.2, 3.0, 1.0])):
        _, fitted, _, _, _ = weighted_fit(y, mask, w)
        if abs(float((Z @ fitted)[0])) > 1e-9:
            fails.append(f"the weighted fit does not telescope at weights {w}")

    # unit weights must be B81's answer, and a wrong scaling of the rows would show
    n = len(obs)
    c0 = B81.cpd_fit(y, mask)[1]
    c1 = weighted_fit(y, mask, np.ones(n))[1]
    if float(np.max(np.abs(c0 - c1))) > 1e-12:
        fails.append("unit weights do not reproduce B81")

    # seeded faults: each has to make its own criterion fail
    probes = []
    real = weighted_fit
    try:
        globals()["weighted_fit"] = lambda y_, m_, w_: real(y_, m_, np.ones(len(w_)))
        ok, _, _ = crit_metric_not_topology(np.random.default_rng(7), 3)
        probes.append(("a weight that never reaches the solve", ok))
        # B84-1 also catches it, since its gauge clause requires the raw
        # coefficients to move when the weights change. Before that clause existed
        # this probe expected B84-1 to pass, and the expectation went stale the
        # moment the clause was added: the self-test caught its own staleness.
        ok, _, _ = crit_reproduces(np.random.default_rng(7), 3)
        probes.append(("the same fault seen by the reproduction check", ok))
    finally:
        globals()["weighted_fit"] = real
    for name, passed in probes:
        if passed:
            fails.append(f"{name} left its criterion passing")

    # the ladder has to be walked, not evaluated once
    if len(VANISHING) < 3 or VANISHING[-1] >= VANISHING[0]:
        fails.append("the vanishing ladder is not a descending ladder")

    for line in fails:
        print("  SELFTEST FAIL:", line)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    rng = np.random.default_rng(a.seed)
    spec = [
        ("B84-1", "known_answer", "unit weights reproduce B81's fit, and the fit is "
         "invariant to an overall scaling of the weights", crit_reproduces),
        ("B84-2", "own_reading", "the weighted fitted value is a coboundary, while the "
         "raw log prices are not", crit_coboundary),
        ("B84-3", "own_reading", "the weights change the metric and not the topology: "
         "b1 and the rank deficiency hold while the parities move", crit_metric_not_topology),
        ("B84-4", "own_reading", "zero is not a small weight, it is an edge leaving the "
         "graph", crit_zero_is_deletion),
        ("B84-5", "own_reading", "how far the two projections get, printed against the "
         "dispersion of the weights", crit_how_far),
        ("B84-6", "instrument", "the weighted design and the weighted Laplacian solve "
         "the same system", crit_two_paths),
    ]
    criteria, report = [], {}
    for name, kind, statement, fn in spec:
        ok, detail, rep = fn(np.random.default_rng(a.seed + len(criteria)), a.reps)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:190]}")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B84-7", "kind": "bookkeeping", "passed": bool(ok),
                     "statement": "B81's section 6 registration is discharged",
                     "detail": detail})
    report["B84-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B84-7  [bookkeeping]  {detail[:190]}")

    rec = {"stage": "B84",
           "config": {"seed": a.seed, "reps": a.reps, "shapes": [list(s) for s in SHAPES],
                      "dispersions": list(DISPERSIONS), "vanishing": list(VANISHING),
                      "tableau_density": 0.7, "imports": "b81_cpd"},
           "criteria": criteria, "report": report}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    if bad:
        print("FAILED: " + ", ".join(bad))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
