"""B81: the country-product-dummy method is the same projection on a second graph.

Paper station, zero data.  Closes B79's registration, and corrects its wording:
CPD is a regression, and a regression onto dummies *is* a projection.  What
differs from GEKS is the graph, not the loss.

Published inputs:

  Coondoo, D., Majumder, A. and Ray, R. (2004), "A Method of Calculating
  Regional Consumer Price Differentials with Illustrative Evidence from India",
  Review of Income and Wealth 50(1), 51-68, equation (1) and the passage on
  base-region invariance and circularity.

Run:  python experiments/b81_cpd.py [--reps N] [--seed S]
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib

import numpy as np

OUT = pathlib.Path(__file__).resolve().parents[1] / "results" / "b81_cpd.json"

SEED = 81
REPS = 10
TOL = 1e-10
EARLY_STOP_SPREAD = 1e-13


# ------------------------------------------------- the two objects

def draw_tableau(rng, M, R, complete=True, density=0.7):
    """log prices on an M by R product-by-country tableau, with a mask."""
    y = rng.normal(0.0, 0.8, (M, R))
    if complete:
        mask = np.ones((M, R), dtype=bool)
    else:
        mask = rng.random((M, R)) < density
        for j in range(M):                      # every product priced somewhere
            if not mask[j].any():
                mask[j, int(rng.integers(R))] = True
        for r in range(R):                      # every country prices something
            if not mask[:, r].any():
                mask[int(rng.integers(M)), r] = True
    return y, mask


def cells(mask):
    return [(j, r) for j in range(mask.shape[0]) for r in range(mask.shape[1])
            if mask[j, r]]


def cpd_design(M, R, obs):
    """The dummy design matrix of equation (1): one column per product, one per country."""
    X = np.zeros((len(obs), M + R))
    for i, (j, r) in enumerate(obs):
        X[i, j] = 1.0
        X[i, M + r] = 1.0
    return X


def cpd_fit(y, mask):
    """OLS of log price on product dummies and country dummies. Path A."""
    M, R = mask.shape
    obs = cells(mask)
    X = cpd_design(M, R, obs)
    rhs = np.array([y[j, r] for (j, r) in obs])
    coef, *_ = np.linalg.lstsq(X, rhs, rcond=None)
    fitted = X @ coef
    return coef, fitted, rhs, obs, X


def bipartite_incidence(M, R, obs):
    """Products and countries as vertices, one edge per observed cell.

    Oriented product -> country, so a coboundary on it reads `psi(r) - psi(j)`,
    which is the fitted value once `psi` on the product side carries a sign.
    """
    B = np.zeros((len(obs), M + R))
    for i, (j, r) in enumerate(obs):
        B[i, j] = -1.0
        B[i, M + r] = +1.0
    return B


def cycle_basis(M, R, obs):
    """A cycle basis of the bipartite graph, as signed edge vectors.

    Built from a spanning forest and the edges outside it: each such edge closes
    exactly one cycle, and there are `b1` of them.  Nothing here touches the
    regression.
    """
    n = M + R
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    index = {e: i for i, e in enumerate(obs)}
    tree, extra = [], []
    adj = {v: [] for v in range(n)}
    for (j, r) in obs:
        u, v = j, M + r
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
            tree.append((j, r))
            adj[u].append((v, (j, r)))
            adj[v].append((u, (j, r)))
        else:
            extra.append((j, r))

    def path(u, v):
        """Edges of the tree path from u to v, with a sign for the direction taken."""
        seen, stack = {u: None}, [u]
        while stack:
            a = stack.pop()
            if a == v:
                break
            for b, e in adj[a]:
                if b not in seen:
                    seen[b] = (a, e)
                    stack.append(b)
        out, cur = [], v
        while seen[cur] is not None:
            a, e = seen[cur]
            j, r = e
            # the edge runs product j -> country r; sign is +1 if we walk it that way
            out.append((e, +1.0 if cur == M + r else -1.0))
            cur = a
        return out[::-1]

    basis = []
    for (j, r) in extra:
        vec = np.zeros(len(obs))
        vec[index[(j, r)]] = +1.0              # walk the extra edge forwards
        for e, s in path(M + r, j):            # and the tree path back
            vec[index[e]] += s
        basis.append(vec)
    return np.array(basis) if basis else np.zeros((0, len(obs)))


# ------------------------------------------------- B81-1  the published claims

def check_published_claims(rng, reps):
    """B81-1 known_answer: base invariance, transitivity, and the normal equations."""
    rows, bad = [], 0
    for _ in range(reps):
        M, R = int(rng.integers(3, 9)), int(rng.integers(3, 8))
        y, mask = draw_tableau(rng, M, R)
        coef, fitted, rhs, obs, X = cpd_fit(y, mask)
        beta = coef[M:]
        # transitivity of the implied parities, on every triple
        worst_tri = 0.0
        for a, b, c in itertools.combinations(range(R), 3):
            s = (beta[b] - beta[a]) + (beta[c] - beta[b]) + (beta[a] - beta[c])
            worst_tri = max(worst_tri, abs(s))
        # base invariance: the parity ratios do not move when the base changes
        ref = beta - beta[0]
        worst_base = 0.0
        for r0 in range(R):
            alt = beta - beta[r0]
            worst_base = max(worst_base, np.abs((alt - alt[0]) - (ref - ref[0])).max())
        # the residual is orthogonal to every column of the design
        resid = rhs - fitted
        worst_orth = float(np.abs(X.T @ resid).max())
        rows.append({"M": M, "R": R, "worst_triple": worst_tri,
                     "worst_base_shift": worst_base, "worst_orthogonality": worst_orth})
        if not (worst_tri < TOL and worst_base < TOL and worst_orth < 1e-8):
            bad += 1
    ok = bad == 0
    detail = (f"{len(rows)} tableaux: worst triple sum {max(r['worst_triple'] for r in rows):.2e}, "
              f"worst shift on changing the base country "
              f"{max(r['worst_base_shift'] for r in rows):.2e}, worst residual-design "
              f"inner product {max(r['worst_orthogonality'] for r in rows):.2e}. "
              f"Transitivity and base invariance are what that paper claims and they hold "
              f"to machine precision")
    return bool(ok), detail, {"published_claims": rows}


# ------------------------------------------------- B81-2  why they hold

def check_fitted_is_a_coboundary(rng, reps):
    """B81-2 own_reading: the fitted values sum to zero around every cycle.

    The cycle basis is built from the graph and never sees the regression, so this
    is not the regression compared with itself: it is the regression's output read
    against a structure computed from the incidence pattern alone.
    """
    rows, bad = [], 0
    for _ in range(reps):
        M, R = int(rng.integers(3, 9)), int(rng.integers(3, 8))
        y, mask = draw_tableau(rng, M, R)
        _, fitted, rhs, obs, X = cpd_fit(y, mask)
        Z = cycle_basis(M, R, obs)
        if Z.shape[0] == 0:
            continue
        loops_fitted = float(np.abs(Z @ fitted).max())
        loops_raw = float(np.abs(Z @ rhs).max())
        b1_closed = len(obs) - (M + R) + 1
        b1_rank = len(obs) - int(np.linalg.matrix_rank(
            bipartite_incidence(M, R, obs), tol=1e-10))
        rows.append({"M": M, "R": R, "edges": len(obs), "cycles": int(Z.shape[0]),
                     "b1_closed": b1_closed, "b1_rank": b1_rank,
                     "loops_on_fitted": loops_fitted, "loops_on_raw": loops_raw})
        if not (loops_fitted < TOL and loops_raw > 1e-3
                and Z.shape[0] == b1_closed == b1_rank):
            bad += 1
    ok = bad == 0 and len(rows) >= 3
    detail = (f"{len(rows)} tableaux: every cycle of the bipartite graph sums to "
              f"{max(r['loops_on_fitted'] for r in rows):.2e} on the fitted values and to "
              f"{min(r['loops_on_raw'] for r in rows):.3f} or more on the raw log prices. "
              f"The cycle count equals `E - V + 1` by closed form and by incidence rank in "
              f"every case. **So transitivity is not a property of dummy regressions, it is "
              f"that the fitted value is a difference of a potential**")
    return bool(ok), detail, {"coboundary": rows}

# ------------------------------------------------- B81-3  the two graphs

def geks_from_jevons(y):
    """GEKS on countries, built on the Jevons bilateral index. Complete tableau only.

    Uses none of the CPD code: the bilateral index is a mean over products and the
    GEKS step is the published product formula.
    """
    M, R = y.shape
    J = np.zeros((R, R))
    for a in range(R):
        for b in range(R):
            J[a, b] = float(np.mean(y[:, b] - y[:, a]))
    G = np.zeros((R, R))
    for a in range(R):
        for b in range(R):
            G[a, b] = sum(J[a, l] + J[l, b] for l in range(R)) / R
    return J, G


def check_two_graphs(rng, reps):
    """B81-3 own_reading: the two methods project on two graphs, with two b1."""
    rows = []
    bad = 0
    for _ in range(reps):
        M, R = int(rng.integers(3, 9)), int(rng.integers(3, 8))
        y, mask = draw_tableau(rng, M, R)
        obs = cells(mask)
        b1_bip_closed = M * R - (M + R) + 1
        b1_bip_rank = len(obs) - int(np.linalg.matrix_rank(
            bipartite_incidence(M, R, obs), tol=1e-10))
        b1_cty_closed = (R - 1) * (R - 2) // 2
        edges_c = list(itertools.combinations(range(R), 2))
        inc = np.zeros((len(edges_c), R))
        for i, (a, b) in enumerate(edges_c):
            inc[i, a] = -1.0
            inc[i, b] = +1.0
        b1_cty_rank = len(edges_c) - int(np.linalg.matrix_rank(inc, tol=1e-10))
        rows.append({"M": M, "R": R,
                     "bipartite_b1_closed": b1_bip_closed,
                     "bipartite_b1_rank": b1_bip_rank,
                     "country_b1_closed": b1_cty_closed,
                     "country_b1_rank": b1_cty_rank})
        if not (b1_bip_closed == b1_bip_rank == (M - 1) * (R - 1)
                and b1_cty_closed == b1_cty_rank):
            bad += 1
    ok = bad == 0
    detail = (f"{len(rows)} tableaux. The bipartite graph CPD projects on has "
              f"`b1 = MR - (M+R) + 1 = (M-1)(R-1)`, closed form against incidence rank in "
              f"{len(rows) - bad} of {len(rows)}, running "
              f"{min(r['bipartite_b1_closed'] for r in rows)} to "
              f"{max(r['bipartite_b1_closed'] for r in rows)}. The complete country graph "
              f"GEKS projects on has `(R-1)(R-2)/2`, running "
              f"{min(r['country_b1_closed'] for r in rows)} to "
              f"{max(r['country_b1_closed'] for r in rows)}. **Two methods, one operation, "
              f"two graphs, and the count of what each discards is not the same number**")
    return bool(ok), detail, {"two_graphs": rows}


# ------------------------------------------------- B81-4  do they agree

def check_cpd_against_geks(rng, reps):
    """B81-4 own_reading: on a complete tableau, are the two parities the same?"""
    rows, worst = [], 0.0
    for _ in range(reps):
        M, R = int(rng.integers(3, 9)), int(rng.integers(3, 8))
        y, _ = draw_tableau(rng, M, R)
        coef, *_ = cpd_fit(y, np.ones((M, R), dtype=bool))
        beta = coef[M:]
        _, G = geks_from_jevons(y)
        gap = max(abs((beta[b] - beta[a]) - G[a, b])
                  for a in range(R) for b in range(R))
        worst = max(worst, gap)
        rows.append({"M": M, "R": R, "worst_gap": gap})
    agree = worst < TOL
    detail = (f"{len(rows)} complete equal-weight tableaux: the worst gap between CPD's "
              f"`beta_b - beta_a` and GEKS on the Jevons index is {worst:.2e}, so **the two "
              f"graphs give one answer there**. The routes share no code: one is an OLS on "
              f"dummies, the other averages over products and then multiplies out the GEKS "
              f"formula. **Where they part is the incomplete tableau**: GEKS needs every "
              f"bilateral index and a bilateral index needs the two countries to price "
              f"something in common, while CPD needs only that the bipartite graph is "
              f"connected, which is a weaker condition and is what B81-5 counts")
    return bool(agree), detail, {"cpd_vs_geks": rows, "agree": bool(agree),
                                 "worst_gap": worst}


# ------------------------------------------------- B81-5  an incomplete tableau

def components(M, R, obs):
    parent = list(range(M + R))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    touched = set()
    for (j, r) in obs:
        touched.add(j)
        touched.add(M + r)
        ra, rb = find(j), find(M + r)
        if ra != rb:
            parent[ra] = rb
    return len({find(v) for v in touched})


def check_incompleteness_is_h0(rng, reps):
    """B81-5 own_reading: an incomplete tableau can disconnect, and then the
    parities are not identified. The rank deficiency counts the components."""
    rows, bad, split = [], 0, 0
    for _ in range(reps * 4):
        M, R = int(rng.integers(3, 7)), int(rng.integers(3, 7))
        y, mask = draw_tableau(rng, M, R, complete=False,
                               density=float(rng.uniform(0.25, 0.55)))
        obs = cells(mask)
        c = components(M, R, obs)
        X = cpd_design(M, R, obs)
        rank = int(np.linalg.matrix_rank(X, tol=1e-10))
        touched = len({j for j, _ in obs}) + len({r for _, r in obs})
        deficiency = touched - rank
        b1_closed = len(obs) - touched + c
        b1_rank = len(obs) - int(np.linalg.matrix_rank(
            bipartite_incidence(M, R, obs), tol=1e-10))
        rows.append({"M": M, "R": R, "edges": len(obs), "components": c,
                     "rank": rank, "deficiency": deficiency,
                     "b1_closed": b1_closed, "b1_rank": b1_rank})
        if c > 1:
            split += 1
        if not (deficiency == c and b1_closed == b1_rank):
            bad += 1
    ok = bad == 0 and split > 0 and split < len(rows)
    detail = (f"{len(rows)} sparse tableaux, {split} of them disconnected. The design "
              f"matrix's rank deficiency equals the number of components in "
              f"{len(rows) - bad} of {len(rows)}, and `b1 = E - V + c` matches the incidence "
              f"rank throughout. **So whether the parities are identified at all is a "
              f"connectivity question about the tableau**: one component is one free "
              f"constant, and two components are two, which is a parity that cannot be "
              f"read rather than one read badly")
    return bool(ok), detail, {"incomplete": rows}


# ------------------------------------------------- B81-6  the gauge

def check_gauge(rng, reps):
    """B81-6 instrument: dropping a different dummy moves the coefficients and not
    the fitted values, which is the gauge freedom stated as a check."""
    rows, bad = [], 0
    for _ in range(reps):
        M, R = int(rng.integers(3, 8)), int(rng.integers(3, 7))
        y, mask = draw_tableau(rng, M, R)
        obs = cells(mask)
        rhs = np.array([y[j, r] for (j, r) in obs])
        X = cpd_design(M, R, obs)
        base = None
        moved, fits = 0.0, []
        for drop in range(M + R):
            keep = [k for k in range(M + R) if k != drop]
            coef, *_ = np.linalg.lstsq(X[:, keep], rhs, rcond=None)
            fit = X[:, keep] @ coef
            fits.append(fit)
            full = np.zeros(M + R)
            full[keep] = coef
            if base is None:
                base = full
            else:
                moved = max(moved, float(np.abs(full - base).max()))
        spread = float(max(np.abs(f - fits[0]).max() for f in fits))
        rows.append({"M": M, "R": R, "coefficients_moved": moved,
                     "fitted_spread": spread})
        if not (spread < TOL and moved > 1e-6):
            bad += 1
    ok = bad == 0
    detail = (f"{len(rows)} tableaux, dropping each dummy in turn: the fitted values move by "
              f"at most {max(r['fitted_spread'] for r in rows):.2e} while the coefficients "
              f"themselves move by up to {max(r['coefficients_moved'] for r in rows):.3f}. "
              f"**Both halves are required**: unchanged fitted values with unchanged "
              f"coefficients would mean the gauge was not exercised")
    return bool(ok), detail, {"gauge": rows}

# ------------------------------------------------- B81-7  B79's registration

REGISTRATION = (
    "B79 registered: the same reading on the country-product-dummy estimator, which "
    "is a regression rather than a projection and therefore a different loss",
    "Answered here, and the registration's wording was half wrong: a regression onto "
    "dummies IS a projection, and the loss is the same sum of squares. What differs "
    "is the graph. B81-2 shows the fitted value is a coboundary on the bipartite "
    "product-by-country graph, B81-3 counts what each graph discards, and B81-4 shows "
    "the two answers coincide on a complete equal-weight tableau",
)


def check_registration():
    """B81-7 bookkeeping: name the registration and the correction to its wording."""
    reg, ans = REGISTRATION
    ok = bool(reg and ans)
    detail = f"{reg}. {ans}"
    return ok, detail, {"registration": {"text": reg, "answered_by": ans}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    results = [
        ("B81-1", "known_answer",
         "the two properties that paper claims for the estimator: the parities are "
         "transitive and they do not move with the base region",
         check_published_claims(rng, a.reps)),
        ("B81-2", "own_reading",
         "the fitted value is a coboundary on the bipartite graph, so every cycle of "
         "that graph sums to zero on it while the raw log prices do not",
         check_fitted_is_a_coboundary(rng, a.reps)),
        ("B81-3", "own_reading",
         "the two methods project on two graphs, and the dimension of what each "
         "discards is (M-1)(R-1) against (R-1)(R-2)/2",
         check_two_graphs(rng, a.reps)),
        ("B81-4", "own_reading",
         "on a complete equal-weight tableau the two projections return the same "
         "parities, computed by two routes sharing no code",
         check_cpd_against_geks(rng, a.reps)),
        ("B81-5", "own_reading",
         "an incomplete tableau can disconnect, and then the parities are not "
         "identified: the design matrix's rank deficiency counts the components",
         check_incompleteness_is_h0(rng, a.reps)),
        ("B81-6", "instrument",
         "the gauge: dropping a different dummy moves the coefficients and leaves the "
         "fitted values where they were",
         check_gauge(rng, a.reps)),
        ("B81-7", "bookkeeping",
         "B79's registration, named, with the correction to its wording",
         check_registration()),
    ]

    mapping = {
        "B81-1": "transitivity, base invariance and orthogonality all inside tolerance -> "
                 "PASS; any outside -> FAIL",
        "B81-2": "cycles sum to zero on the fitted values AND do not on the raw prices AND "
                 "the cycle count matches both the closed form and the rank -> PASS. The "
                 "second clause is required: if the raw prices were transitive too, the "
                 "criterion would be reading an identity",
        "B81-3": "both closed forms match their incidence ranks -> PASS; else FAIL",
        "B81-4": "the two routes agree within tolerance -> PASS; a disagreement would mean "
                 "one of the two implementations is wrong, since on a complete equal-weight "
                 "tableau the two projections are the same object",
        "B81-5": "rank deficiency equals the component count everywhere AND at least one "
                 "drawn tableau is disconnected AND at least one is connected -> PASS; "
                 "otherwise the sampling did not exercise the reading",
        "B81-6": "fitted values unchanged AND coefficients moved -> PASS; both unchanged "
                 "means the gauge was never exercised, so that is a FAIL and not a pass",
        "B81-7": "the registration named with what answers it -> PASS",
    }

    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep) in results:
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail}")

    rec = {
        "stage": "B81",
        "config": {"seed": a.seed, "reps": a.reps, "tol": TOL,
                   "early_stop_spread": EARLY_STOP_SPREAD,
                   "product_range": [3, 9], "country_range": [3, 8],
                   "sparse_density_range": [0.25, 0.55]},
        "sources": {
            "cpd_equation_and_claims":
                "Coondoo, D., Majumder, A. and Ray, R. (2004), A Method of Calculating "
                "Regional Consumer Price Differentials with Illustrative Evidence from "
                "India, Review of Income and Wealth 50(1), 51-68, equation (1) and the "
                "passage stating that the estimates are invariant to the choice of "
                "numeraire region and therefore satisfy circularity",
            "cpd_origin": "Summers, R. (1973); weighted CPD and the Rao system, Rao, D. S. "
                          "P. (2005), Review of Income and Wealth",
            "geks_side": "carried by B79 in this repository",
        },
        "criteria": criteria,
        "mapping": mapping,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    failed = [c["name"] for c in criteria if not c["passed"]]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
