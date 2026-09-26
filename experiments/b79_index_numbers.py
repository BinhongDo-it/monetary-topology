"""B79: the circularity test on index numbers, and GEKS as the projection.

Paper station, zero data. Two published inputs:

  Diewert, W. E. (2021), "Scanner Data, Elementary Price Indexes and the Chain
  Drift Problem", Discussion Paper 20-07, Vancouver School of Economics, UBC,
  revised 2021-10-13, Tables 1 and 2.

  Ivancic, L., W. E. Diewert and K. J. Fox (2011), "Scanner Data, Time
  Aggregation and the Construction of Price Indexes", Journal of Econometrics
  161(1), 24-35, equation (5).

Run:  python experiments/b79_index_numbers.py [--reps N] [--seed S]
Criteria are written into this file and the record carries their wording.
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib

import numpy as np

OUT = pathlib.Path(__file__).resolve().parents[1] / "results" / "b79_index_numbers.json"

SEED = 79
REPS = 20
EARLY_STOP_SPREAD = 1e-14   # rule 12: stop once the arm is this homogeneous
TOL = 1e-12


# ---------------------------------------------------------------- bilateral

def laspeyres(p0, q0, p1, q1):
    return float(np.dot(p1, q0) / np.dot(p0, q0))


def paasche(p0, q0, p1, q1):
    return float(np.dot(p1, q1) / np.dot(p0, q1))


def fisher(p0, q0, p1, q1):
    return float(np.sqrt(laspeyres(p0, q0, p1, q1) * paasche(p0, q0, p1, q1)))


def tornqvist(p0, q0, p1, q1):
    s0 = (p0 * q0) / np.dot(p0, q0)
    s1 = (p1 * q1) / np.dot(p1, q1)
    return float(np.exp(np.dot((s0 + s1) / 2.0, np.log(p1 / p0))))


# ------------------------------------------------- B79-1  the published table

# Diewert (2021) Table 1: four periods, two commodities.  Period 4 repeats
# period 1 exactly, so a chained index that returns anything but 1 has drifted.
DIEWERT_T1 = [
    (np.array([1.0, 1.0]), np.array([10.0, 100.0])),
    (np.array([0.5, 1.0]), np.array([5000.0, 100.0])),
    (np.array([1.0, 1.0]), np.array([1.0, 100.0])),
    (np.array([1.0, 1.0]), np.array([10.0, 100.0])),
]


def chained(formula, table):
    out = 1.0
    links = []
    for t in range(len(table) - 1):
        (p0, q0), (p1, q1) = table[t], table[t + 1]
        link = formula(p0, q0, p1, q1)
        links.append(link)
        out *= link
    return out, links


def check_published_drift():
    """B79-1 known_answer: read back the two percentages Diewert reports."""
    same = (np.array_equal(DIEWERT_T1[0][0], DIEWERT_T1[3][0])
            and np.array_equal(DIEWERT_T1[0][1], DIEWERT_T1[3][1]))
    cf, lf = chained(fisher, DIEWERT_T1)
    ct, lt = chained(tornqvist, DIEWERT_T1)
    bias_f = 100.0 * (cf - 1.0)
    bias_t = 100.0 * (ct - 1.0)
    # reported: chained Fisher about 2 per cent downward, Tornqvist close to 3
    ok = (same
          and bias_f < 0.0 and bias_t < 0.0
          and 1.5 <= abs(bias_f) <= 2.5
          and 2.5 <= abs(bias_t) <= 3.5
          and abs(bias_t) > abs(bias_f))
    detail = (f"period 4 repeats period 1: {same}. chained Fisher {cf:.6f} "
              f"({bias_f:+.2f}%), chained Tornqvist {ct:.6f} ({bias_t:+.2f}%). "
              f"Reported: about 2% and close to 3%, both downward")
    rep = {"chained_fisher": cf, "chained_tornqvist": ct,
           "bias_fisher_pct": bias_f, "bias_tornqvist_pct": bias_t,
           "fisher_links": lf, "tornqvist_links": lt,
           "period4_repeats_period1": bool(same)}
    return bool(ok), detail, rep


# ------------------------------------------------- B79-2  time reversal

def check_time_reversal(rng, reps):
    """B79-2 instrument: Fisher and Tornqvist pass, Laspeyres must not.

    Half of this criterion has to fail.  If all three pass, the check is broken.
    """
    worst = {"fisher": 0.0, "tornqvist": 0.0, "laspeyres": 0.0}
    for _ in range(reps):
        n = int(rng.integers(2, 7))
        p0, p1 = rng.uniform(0.3, 3.0, n), rng.uniform(0.3, 3.0, n)
        q0, q1 = rng.uniform(1.0, 500.0, n), rng.uniform(1.0, 500.0, n)
        for name, f in (("fisher", fisher), ("tornqvist", tornqvist),
                        ("laspeyres", laspeyres)):
            prod = f(p0, q0, p1, q1) * f(p1, q1, p0, q0)
            worst[name] = max(worst[name], abs(prod - 1.0))
    ok = (worst["fisher"] < TOL and worst["tornqvist"] < TOL
          and worst["laspeyres"] > 1e-3)
    detail = (f"worst |P(j,k)P(k,j) - 1| over {reps} draws: "
              f"Fisher {worst['fisher']:.3e}, Tornqvist {worst['tornqvist']:.3e}, "
              f"Laspeyres {worst['laspeyres']:.3e}. Fisher and Tornqvist below "
              f"{TOL:.0e}; Laspeyres above 1e-3, which is what makes omega "
              f"antisymmetric for the first two and not for the third")
    return bool(ok), detail, {"worst_time_reversal_gap": worst}


# ------------------------------------------------- graph helpers

def incidence(n, edges):
    """Rows are edges (j,k) with -1 at j and +1 at k. Only place a graph is built."""
    M = np.zeros((len(edges), n))
    for r, (j, k) in enumerate(edges):
        M[r, j] = -1.0
        M[r, k] = +1.0
    return M


def complete_edges(n):
    return list(itertools.combinations(range(n), 2))


def b1_from_rank(n, edges):
    M = incidence(n, edges)
    return len(edges) - int(np.linalg.matrix_rank(M, tol=1e-10))


# ------------------------------------------------- B79-3  b1 of the comparison graph

def check_b1_closed_form():
    """B79-3 instrument: b1(K_n) = (n-1)(n-2)/2 against the incidence rank."""
    rows, bad = [], 0
    for n in range(3, 13):
        closed = (n - 1) * (n - 2) // 2
        by_rank = b1_from_rank(n, complete_edges(n))
        rows.append({"n": n, "closed_form": closed, "by_rank": by_rank})
        if closed != by_rank:
            bad += 1
    ok = bad == 0
    detail = (f"n = 3..12, b1(K_n) = (n-1)(n-2)/2 against len(E) - rank(incidence): "
              f"{len(rows) - bad} of {len(rows)} agree, from {rows[0]['closed_form']} "
              f"to {rows[-1]['closed_form']}")
    return bool(ok), detail, {"b1_complete_graph": rows}


# ------------------------------------------------- omega from prices

def random_panel(rng, n_periods, n_goods):
    return [(rng.uniform(0.3, 3.0, n_goods), rng.uniform(1.0, 500.0, n_goods))
            for _ in range(n_periods)]


def omega_matrix(panel, formula=fisher):
    n = len(panel)
    W = np.zeros((n, n))
    for j in range(n):
        for k in range(n):
            if j == k:
                continue
            (p0, q0), (p1, q1) = panel[j], panel[k]
            W[j, k] = np.log(formula(p0, q0, p1, q1))
    return W


# ------------------------------------------------- B79-4  GEKS is the projection

def projection_fit(n, edges, W):
    """Path A: least squares onto the exact subspace. Uses the incidence matrix."""
    M = incidence(n, edges)
    y = np.array([W[j, k] for (j, k) in edges])
    psi, *_ = np.linalg.lstsq(M, y, rcond=None)
    fitted = M @ psi
    residual = y - fitted
    return psi, fitted, residual, y


def geks_log(n, W):
    """Path B: the published product formula, in logs. Touches nothing above."""
    G = np.zeros((n, n))
    for j in range(n):
        for k in range(n):
            G[j, k] = sum(W[j, l] + W[l, k] for l in range(n)) / n
    return G


def check_geks_is_projection(rng, reps):
    """B79-4 own_reading: the two paths agree to machine precision."""
    worst, stopped_at, gaps = 0.0, reps, []
    for r in range(reps):
        n = int(rng.integers(3, 9))
        W = omega_matrix(random_panel(rng, n, int(rng.integers(2, 6))))
        edges = complete_edges(n)
        _, fitted, _, _ = projection_fit(n, edges, W)
        G = geks_log(n, W)
        gap = max(abs(fitted[r_] - G[j, k]) for r_, (j, k) in enumerate(edges))
        gaps.append(gap)
        worst = max(worst, gap)
        if r >= 4 and max(gaps) - min(gaps) < EARLY_STOP_SPREAD:
            stopped_at = r + 1
            break
    ok = worst < TOL
    detail = (f"{stopped_at} draws, n = 3..8: worst |d0psi(j,k) - log GEKS(j,k)| "
              f"= {worst:.3e} against {TOL:.0e}. Path A solves the normal equations "
              f"on the incidence matrix; path B multiplies out Ivancic-Diewert-Fox "
              f"eq. (5) and touches nothing path A built")
    return bool(ok), detail, {"worst_projection_gap": worst, "draws": stopped_at,
                              "per_draw_gap": gaps}


# ------------------------------------------------- B79-5  rho is what GEKS discards

def triangle_sums(n, W):
    """Loop sums walked explicitly. Does not see the residual."""
    return [W[j, k] + W[k, l] + W[l, j] for j, k, l in itertools.combinations(range(n), 3)]


def check_rho_against_loops(rng, reps):
    """B79-5 own_reading: rho is zero exactly when every loop sum is zero, and
    rho is one number while the drift depends on the chain."""
    live, exact, bad = [], [], 0
    for _ in range(reps):
        n = int(rng.integers(4, 8))
        # live case: omega from real bilateral indexes
        W = omega_matrix(random_panel(rng, n, int(rng.integers(2, 6))))
        _, _, res, _ = projection_fit(n, complete_edges(n), W)
        rho = float(np.linalg.norm(res))
        loops = triangle_sums(n, W)
        maxloop = max(abs(x) for x in loops)
        live.append({"n": n, "rho": rho, "max_abs_loop": maxloop})
        if not (rho > TOL and maxloop > TOL):
            bad += 1
        # exact case: omega built as a coboundary, so both must be zero
        phi = rng.normal(size=n)
        We = phi[None, :] - phi[:, None]
        _, _, rese, _ = projection_fit(n, complete_edges(n), We)
        rhoe = float(np.linalg.norm(rese))
        maxloope = max(abs(x) for x in triangle_sums(n, We))
        exact.append({"n": n, "rho": rhoe, "max_abs_loop": maxloope})
        if not (rhoe < TOL and maxloope < TOL):
            bad += 1
    # one field, several chains: the drift moves, rho does not
    n = 6
    W = omega_matrix(random_panel(rng, n, 3))
    _, _, res, _ = projection_fit(n, complete_edges(n), W)
    rho_one = float(np.linalg.norm(res))
    drifts = []
    for perm in itertools.islice(itertools.permutations(range(1, n)), 6):
        path = (0,) + perm + (0,)
        drifts.append(float(sum(W[path[i], path[i + 1]] for i in range(len(path) - 1))))
    spread = max(drifts) - min(drifts)
    ok = bad == 0 and spread > TOL
    detail = (f"{reps} live fields and {reps} coboundary fields: rho and the worst "
              f"loop sum are both above {TOL:.0e} in every live case and both below "
              f"it in every coboundary case, {bad} exception(s). On one field six "
              f"chains give drifts spanning {spread:.4f} while rho is the single "
              f"number {rho_one:.6f}")
    return bool(ok), detail, {"live": live, "coboundary": exact,
                              "one_field_rho": rho_one, "chain_drifts": drifts,
                              "drift_spread": spread}


# ------------------------------------------------- B79-6  an incomplete comparison graph

def random_connected_subgraph(rng, n, keep):
    """A spanning tree plus `keep` extra edges, so b1 = keep by construction."""
    perm = list(rng.permutation(n))
    tree = [tuple(sorted((perm[i], perm[i + 1]))) for i in range(n - 1)]
    rest = [e for e in complete_edges(n) if e not in set(tree)]
    extra = [rest[i] for i in rng.choice(len(rest), size=min(keep, len(rest)),
                                         replace=False)] if keep else []
    return sorted(set(tree) | set(extra))


def check_subgraph_degrees_of_freedom(rng, reps):
    """B79-6 own_reading: on a subgraph the count of discarded numbers is b1,
    and the projection on the subgraph is not the projection on K_n."""
    rows, bad = [], 0
    for _ in range(reps):
        n = int(rng.integers(4, 9))
        keep = int(rng.integers(0, (n - 1) * (n - 2) // 2 + 1))
        edges = random_connected_subgraph(rng, n, keep)
        M = incidence(n, edges)
        b1_rank = len(edges) - int(np.linalg.matrix_rank(M, tol=1e-10))
        # dimension of the space the projection throws away
        u, s, _ = np.linalg.svd(M, full_matrices=True)
        dof = len(edges) - int(np.sum(s > 1e-10))
        W = omega_matrix(random_panel(rng, n, 3))
        _, fit_sub, res_sub, _ = projection_fit(n, edges, W)
        _, fit_full, _, _ = projection_fit(n, complete_edges(n), W)
        full_by_edge = {e: fit_full[i] for i, e in enumerate(complete_edges(n))}
        moved = max(abs(fit_sub[i] - full_by_edge[e]) for i, e in enumerate(edges))
        rows.append({"n": n, "edges": len(edges), "b1_by_rank": b1_rank,
                     "b1_closed": keep, "dof": dof, "moved_vs_complete": moved,
                     "rho": float(np.linalg.norm(res_sub))})
        if not (b1_rank == keep == dof):
            bad += 1
    incomplete = [r for r in rows if r["edges"] < r["n"] * (r["n"] - 1) // 2]
    movers = [r for r in incomplete if r["moved_vs_complete"] > TOL]
    ok = bad == 0 and len(movers) == len(incomplete) and len(incomplete) > 0
    detail = (f"{len(rows)} random connected subgraphs: b1 by rank, b1 by "
              f"construction and the discarded dimension agree in {len(rows) - bad} "
              f"of {len(rows)}; b1 runs {min(r['b1_by_rank'] for r in rows)} to "
              f"{max(r['b1_by_rank'] for r in rows)}. Of the {len(incomplete)} that "
              f"are not the complete graph, {len(movers)} give a different fitted "
              f"index than K_n does, which is why a rolling window is a different "
              f"projection and not the same one on less data")
    return bool(ok), detail, {"subgraphs": rows}


# ------------------------------------------------- B79-7  periods times regions

def path_graph(n):
    return list(zip(range(n - 1), range(1, n)))


def cycle_graph(n):
    return list(zip(range(n), list(range(1, n)) + [0]))


def cartesian_product(nG, eG, nH, eH):
    idx = {(g, h): g * nH + h for g in range(nG) for h in range(nH)}
    edges = []
    for (g, gp) in eG:
        for h in range(nH):
            edges.append(tuple(sorted((idx[(g, h)], idx[(gp, h)]))))
    for (h, hp) in eH:
        for g in range(nG):
            edges.append(tuple(sorted((idx[(g, h)], idx[(g, hp)]))))
    return nG * nH, sorted(set(edges))


def check_product_split():
    """B79-7 own_reading: on periods x regions the square part has dimension
    (|V_G| - 1)(|V_H| - 1), whatever the two factor graphs are."""
    rows, bad = [], 0
    makers = {"path": path_graph, "cycle": cycle_graph, "complete": complete_edges}
    for kG, mG in makers.items():
        for kH, mH in makers.items():
            for nG in range(3, 7):
                for nH in range(3, 7):
                    eG, eH = mG(nG), mH(nH)
                    b1G = len(eG) - (nG - 1)
                    b1H = len(eH) - (nH - 1)
                    V, E = cartesian_product(nG, eG, nH, eH)
                    b1G_prod = b1_from_rank(V, E)
                    slice_dim = nH * b1G
                    agent_dim = nG * b1H
                    square = b1G_prod - slice_dim - agent_dim
                    closed = (nG - 1) * (nH - 1)
                    rows.append({"G": kG, "H": kH, "nG": nG, "nH": nH,
                                 "b1_product": b1G_prod, "slice": slice_dim,
                                 "agent": agent_dim, "square": square,
                                 "square_closed_form": closed})
                    if square != closed:
                        bad += 1
    ok = bad == 0
    sq = sorted({(r["nG"], r["nH"], r["square"]) for r in rows})
    detail = (f"{len(rows)} product graphs over path, cycle and complete factors, "
              f"3 to 6 vertices each: b1 splits into slice + agent + square with "
              f"the square part equal to (|V_G| - 1)(|V_H| - 1) in "
              f"{len(rows) - bad} of {len(rows)}. Square dimension runs "
              f"{min(s[2] for s in sq)} to {max(s[2] for s in sq)} and depends on "
              f"the two vertex counts alone, not on how many comparisons are computed")
    return bool(ok), detail, {"product_graphs": rows}


# ------------------------------------------------- B79-8  the 2026-08-13 registration

def check_citation_registered():
    """B79-8 bookkeeping: the names that document was told to carry."""
    doc = pathlib.Path(__file__).resolve().parents[1] / "docs" / "b1_theorem.md"
    text = doc.read_text(encoding="utf-8")
    want = ["Fisher", "circular", "Kirchhoff", "Imrich", "nneth", "HodgeRank"]
    found = {w: text.count(w) for w in want}
    missing = [w for w, c in found.items() if c == 0]
    ok = not missing
    detail = (f"b1_theorem.md word counts {found}; missing {missing if missing else 'none'}. "
              f"Registered 2026-08-13 and not done until this station")
    return bool(ok), detail, {"citation_counts": found}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    results = [
        ("B79-1", "known_answer",
         "the two chain drift percentages Diewert (2021) Table 2 reports are read "
         "back from his Table 1 data",
         check_published_drift()),
        ("B79-2", "instrument",
         "Fisher and Tornqvist satisfy the time reversal test and Laspeyres does "
         "not, which is what makes omega antisymmetric for the first two",
         check_time_reversal(rng, a.reps)),
        ("B79-3", "instrument",
         "b1 of the complete comparison graph equals (n-1)(n-2)/2, against the "
         "rank of its incidence matrix",
         check_b1_closed_form()),
        ("B79-4", "own_reading",
         "GEKS is the least squares projection of the log bilateral index onto the "
         "exact subspace: the fitted coboundary equals the published product "
         "formula edge by edge",
         check_geks_is_projection(rng, a.reps)),
        ("B79-5", "own_reading",
         "rho is the size of what a transitive index discards, it is zero exactly "
         "when every loop sum is zero, and unlike a chain drift it does not depend "
         "on a path",
         check_rho_against_loops(rng, a.reps)),
        ("B79-6", "own_reading",
         "on an incomplete comparison graph the number of independent discarded "
         "numbers is b1 of that graph, and the fitted index is not the one the "
         "complete graph gives",
         check_subgraph_degrees_of_freedom(rng, a.reps)),
        ("B79-7", "own_reading",
         "on periods times regions the obstruction splits into slice, agent and "
         "square parts, and the square part has dimension (|V_G|-1)(|V_H|-1)",
         check_product_split()),
        ("B79-8", "bookkeeping",
         "the names registered for b1_theorem.md on 2026-08-13 are in that file",
         check_citation_registered()),
    ]

    mapping = {
        "B79-1": "both percentages inside the reported bands and both negative -> PASS; "
                 "either outside, either positive, or period 4 not a repeat of period 1 -> FAIL",
        "B79-2": "Fisher and Tornqvist below the tolerance AND Laspeyres above 1e-3 -> PASS; "
                 "all three below -> FAIL, because a check every formula passes is not a check",
        "B79-3": "closed form equals rank at every n -> PASS; any disagreement -> FAIL",
        "B79-4": "worst edgewise gap below the tolerance -> PASS; above -> FAIL",
        "B79-5": "every live field has rho and max loop both above the tolerance, every "
                 "coboundary field has both below, and the chain drifts spread -> PASS; "
                 "any exception, or drifts that do not spread -> FAIL",
        "B79-6": "b1 by rank, b1 by construction and the discarded dimension agree, and "
                 "every proper subgraph fits a different index than K_n -> PASS; else FAIL",
        "B79-7": "square part equals (|V_G|-1)(|V_H|-1) on every product -> PASS; else FAIL",
        "B79-8": "every registered name present -> PASS; any absent -> FAIL, and the fix is "
                 "to write the citation, not to relax the criterion",
    }

    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep) in results:
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail}")

    rec = {
        "stage": "B79",
        "config": {"seed": a.seed, "reps": a.reps, "tol": TOL,
                   "early_stop_spread": EARLY_STOP_SPREAD,
                   "complete_graph_sizes": [3, 12],
                   "product_factor_sizes": [3, 6],
                   "product_factor_families": ["path", "cycle", "complete"]},
        "sources": {
            "chain_drift_table": "Diewert, W. E. (2021), Scanner Data, Elementary Price "
                                 "Indexes and the Chain Drift Problem, Discussion Paper "
                                 "20-07, Vancouver School of Economics, UBC, rev. "
                                 "2021-10-13, Tables 1 and 2",
            "geks_formula": "Ivancic, L., W. E. Diewert and K. J. Fox (2011), Scanner "
                            "Data, Time Aggregation and the Construction of Price "
                            "Indexes, Journal of Econometrics 161(1), 24-35, eq. (5)",
            "least_squares_is_the_usual_derivation":
                "Diewert, W. E. and K. J. Fox (2017), Substitution Bias in Multilateral "
                "Methods for CPI Construction using Scanner Data, Discussion Paper 17-02, "
                "UBC: 'the usual least squares derivation of the GEKS parities; see Balk "
                "(1996) and Diewert (1999)'",
        },
        "criteria": criteria,
        "mapping": mapping,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    failed = [c["name"] for c in criteria if not c["passed"]]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
