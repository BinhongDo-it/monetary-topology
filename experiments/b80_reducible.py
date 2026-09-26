"""B80: a reducible economy, and which part alpha and beta are read off.

Paper station, zero data.  Closes three registrations: B75 (which component),
B71 (the Kemeny-Morgenstern-Thompson generalisation) and B77 (joining the active
set to the reducible decomposition).

Published inputs, all from QuantEcon, *Von Neumann Growth Model (and a
Generalization)*: the two example economies with their factors, the definition
of an independent subset, and the statement that a reducible economy has
alpha_0 = max_i alpha_i and beta_0 = min_i beta_i over its irreducible parts.
Original: Kemeny, J. G., Morgenstern, O. and Thompson, G. L. (1956),
Econometrica 24, 115-135.

The solver is B75's and is imported rather than rewritten.

Run:  python experiments/b80_reducible.py [--reps N] [--seed S]
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b75_rectangular_programme as b75      # noqa: E402  solver, not rewritten

OUT = ROOT / "results" / "b80_reducible.json"

SEED = 80
REPS = 10
FACTOR_TOL = 1e-6          # B75's floor: the game value's slope over the solver tolerance
PUBLISHED_TOL = 1e-8
GAP_FLOOR = 1e-4           # a gap this size is not the bisection


# ------------------------------------------------- the KMT independence relation

def independent_by_goods(A, B):
    """Route one: enumerate subsets of goods, take the maximal admissible T.

    S is independent when some set T of activities consumes nothing outside S and
    together produces every good in S.  For a given S the largest such T is forced,
    so enumerating S is enough.
    """
    n, m = A.shape
    out = set()
    for r in range(1, m + 1):
        for S in itertools.combinations(range(m), r):
            inside = set(S)
            T = [i for i in range(n)
                 if all(A[i, j] == 0 for j in range(m) if j not in inside)]
            if T and all(any(B[i, j] > 0 for i in T) for j in S):
                out.add(frozenset(S))
    return out


def independent_by_activities(A, B):
    """Route two: enumerate subsets of activities and read the goods off them.

    A different enumeration over a different index set.  It shares no line with
    route one, so the two agreeing is a check on the translation of the definition.

    The condition on T is two-sided and the first version of this function had only
    one side of it.  T consumes nothing outside S, which is `consumed(T) subset S`,
    and T produces every good in S, which is `S subset produced(T)`.  So every S
    between those two sets is independent, not only `produced(T)` itself.
    """
    n, m = A.shape
    out = set()
    for r in range(1, n + 1):
        for T in itertools.combinations(range(n), r):
            produced = {j for j in range(m) if any(B[i, j] > 0 for i in T)}
            consumed = {j for j in range(m) if any(A[i, j] > 0 for i in T)}
            if not produced or not consumed <= produced:
                continue
            free = sorted(produced - consumed)
            for r2 in range(len(free) + 1):
                for extra in itertools.combinations(free, r2):
                    S = consumed | set(extra)
                    if S:
                        out.add(frozenset(S))
    return out


def minimal_sets(family):
    return [s for s in family if not any(t < s for t in family)]


def restrict(A, B, S):
    """The sub-economy on goods S: its own activities and its own two matrices."""
    S = sorted(S)
    outside = [j for j in range(A.shape[1]) if j not in set(S)]
    T = [i for i in range(A.shape[0]) if all(A[i, j] == 0 for j in outside)]
    return T, A[np.ix_(T, S)], B[np.ix_(T, S)]


def is_irreducible(A, B):
    fam = independent_by_goods(A, B)
    whole = frozenset(range(A.shape[1]))
    return not [s for s in fam if s != whole]


# ------------------------------------------------- B80-1  the published examples

def check_published():
    """B80-1 known_answer: both QuantEcon examples, factors and reducibility."""
    cbrt2 = 2.0 ** (1.0 / 3.0)
    rows = []
    for name, Al, Bl, want in (("example 1", b75.QE1_A, b75.QE1_B, b75.QE1_PUBLISHED),
                               ("example 2", b75.QE2_A, b75.QE2_B, b75.QE2_PUBLISHED)):
        A, B = np.array(Al, float), np.array(Bl, float)
        a = b75.expansion_factor(A, B)
        b = b75.interest_factor(A, B)
        rows.append({"example": name, "alpha": a, "beta": b,
                     "published_alpha": want[0], "published_beta": want[1],
                     "irreducible": bool(is_irreducible(A, B)),
                     "shape": list(A.shape)})
    ok = (all(abs(r["alpha"] - r["published_alpha"]) < PUBLISHED_TOL
              and abs(r["beta"] - r["published_beta"]) < PUBLISHED_TOL for r in rows)
          and rows[0]["irreducible"] and not rows[1]["irreducible"]
          and abs(rows[0]["alpha"] - cbrt2) < FACTOR_TOL
          and abs(rows[1]["beta"] - 1.0) < FACTOR_TOL)
    detail = ("example 1 irreducible, alpha = beta = "
              f"{rows[0]['alpha']:.9f} against the published {rows[0]['published_alpha']:.9f} "
              f"and against 2^(1/3) = {cbrt2:.9f}; example 2 reducible, "
              f"alpha {rows[1]['alpha']:.9f} and beta {rows[1]['beta']:.9f} against the "
              f"published {rows[1]['published_alpha']:.9f} and {rows[1]['published_beta']:.9f}")
    return bool(ok), detail, {"published": rows}


# ------------------------------------------------- B80-2  the two enumerations

def draw_economy(rng, n, m, density=0.35):
    """A random economy. Assumption I and II are enforced so the factors exist."""
    A = (rng.random((n, m)) < density) * rng.uniform(0.5, 2.0, (n, m))
    B = (rng.random((n, m)) < density) * rng.uniform(0.5, 2.0, (n, m))
    for i in range(n):                       # no free lunch: every activity consumes
        if not A[i].any():
            A[i, int(rng.integers(m))] = 1.0
    for j in range(m):                       # every good produced
        if not B[:, j].any():
            B[int(rng.integers(n)), j] = 1.0
    return A, B


def block_economy(rng, sizes):
    """Two or more economies stacked so that each block is independent by construction."""
    blocks = [draw_economy(rng, s, s + 1) for s in sizes]
    n = sum(b[0].shape[0] for b in blocks)
    m = sum(b[0].shape[1] for b in blocks)
    A, B = np.zeros((n, m)), np.zeros((n, m))
    r = c = 0
    for Ab, Bb in blocks:
        A[r:r + Ab.shape[0], c:c + Ab.shape[1]] = Ab
        B[r:r + Bb.shape[0], c:c + Bb.shape[1]] = Bb
        r += Ab.shape[0]
        c += Ab.shape[1]
    return A, B


def check_two_enumerations(rng, reps):
    """B80-2 instrument: enumerating goods and enumerating activities agree."""
    cases, bad = [], 0
    pool = [("example 1", np.array(b75.QE1_A, float), np.array(b75.QE1_B, float)),
            ("example 2", np.array(b75.QE2_A, float), np.array(b75.QE2_B, float))]
    for k in range(reps):
        n, m = int(rng.integers(2, 6)), int(rng.integers(2, 6))
        pool.append((f"draw {k}", *draw_economy(rng, n, m)))
    for k in range(reps // 2):
        pool.append((f"block {k}", *block_economy(rng, [int(rng.integers(2, 4)),
                                                        int(rng.integers(2, 4))])))
    for name, A, B in pool:
        s1 = independent_by_goods(A, B)
        s2 = independent_by_activities(A, B)
        agree = s1 == s2
        cases.append({"case": name, "shape": list(A.shape), "n_independent": len(s1),
                      "agree": bool(agree), "irreducible": bool(is_irreducible(A, B))}) 
        if not agree:
            bad += 1
    red = sum(1 for c in cases if not c["irreducible"])
    ok = bad == 0 and red > 0 and red < len(cases)
    detail = (f"{len(cases)} economies, two enumerations over two different index sets: "
              f"{len(cases) - bad} agree. {red} of them reducible and "
              f"{len(cases) - red} irreducible, so both branches occur")
    return bool(ok), detail, {"enumeration_cases": cases}


# ------------------------------------------------- the simple economy, B = I

def perron(M):
    return float(np.max(np.abs(np.linalg.eigvals(M)))) if M.size else 0.0


def draw_simple(rng, n=None):
    """A simple economy: B is the identity, so activity j is 'produce good j'.

    Built block-wise so that reducible cases occur, with one-way links between the
    blocks so that a block can be strongly connected without being closed.
    """
    n = n or int(rng.integers(4, 7))
    A = np.zeros((n, n))
    cut = int(rng.integers(1, n))
    A[:cut, :cut] = (rng.random((cut, cut)) < 0.7) * rng.uniform(0.2, 1.2, (cut, cut))
    A[cut:, cut:] = (rng.random((n - cut, n - cut)) < 0.7) * rng.uniform(0.2, 1.2,
                                                                        (n - cut, n - cut))
    A[cut:, :cut] = (rng.random((n - cut, cut)) < 0.4) * rng.uniform(0.1, 0.6,
                                                                    (n - cut, cut))
    for i in range(n):
        if not A[i].any():                       # no free lunch
            A[i, int(rng.integers(n))] = 0.5
    return A, np.eye(n)



def strong_components(A):
    """The strongly connected components of the digraph i -> j when A[i, j] > 0.

    Not the same family as the independent subsets: an SCC may consume outside itself.
    """
    n = A.shape[0]
    reach = []
    for i in range(n):
        stack, seen = [i], set()
        while stack:
            u = stack.pop()
            for v in range(n):
                if A[u, v] > 0 and v not in seen:
                    seen.add(v)
                    stack.append(v)
        reach.append(seen)
    placed, out = set(), []
    for i in range(n):
        if i in placed:
            continue
        grp = sorted({j for j in range(n)
                      if j == i or (j in reach[i] and i in reach[j])})
        placed |= set(grp)
        out.append(grp)
    return out


def closed_parts(A, B):
    """The independent subsets that contain no smaller one: the irreducible parts."""
    fam = independent_by_goods(A, B)
    return sorted((sorted(s) for s in minimal_sets(fam)), key=lambda s: (len(s), s))


# ------------------------------------------------- B80-3  the two factors need two families

def check_two_families(rng, reps):
    """B80-3 own_reading: alpha is a max over the closed parts, beta is not a min
    over anything smaller than the whole economy.

    The published line reads `alpha_0 = max alpha_i` and `beta_0 = min beta_i` over
    the irreducible parts of a simple economy.  Solving the two programmes shows the
    two halves do not live on one family.  `x` is semi-positive and the rows outside
    its support must carry no weight, which forces the support to be closed under
    consumption; `p` is semi-positive and a zero price satisfies its row for free, so
    the support of `p` is under no such constraint.
    """
    rows, bad_a, bad_b, bad_naive, bad_cross_a = 0, 0, 0, 0, 0
    detail_rows = []
    for k in range(reps):
        A, B = draw_simple(rng)
        parts = closed_parts(A, B)
        inv = [1.0 / perron(A[np.ix_(S, S)]) for S in parts if perron(A[np.ix_(S, S)]) > 0]
        if not inv:
            continue
        a0 = b75.expansion_factor(A, B)
        b0 = b75.interest_factor(A, B)
        if a0 is None or b0 is None:
            continue
        lam = perron(A)
        if lam <= 0:
            continue
        sccs = strong_components(A)
        inv_scc = [1.0 / perron(A[np.ix_(S, S)]) for S in sccs
                   if perron(A[np.ix_(S, S)]) > 0]
        if not inv_scc:
            continue
        rows += 1
        da = abs(a0 - max(inv))
        db = abs(b0 - 1.0 / lam)
        # the two cross readings, each of which has to be wrong somewhere
        cross_b = abs(b0 - min(inv))              # beta off the closed family
        cross_a = abs(a0 - max(inv_scc))          # alpha off the all-components family
        if da >= FACTOR_TOL:
            bad_a += 1
        if db >= FACTOR_TOL:
            bad_b += 1
        if cross_b >= FACTOR_TOL:
            bad_naive += 1
        if cross_a >= FACTOR_TOL:
            bad_cross_a += 1
        detail_rows.append({"case": k, "n": int(A.shape[0]), "closed_parts": parts,
                            "strong_components": sccs,
                            "alpha0": a0, "max_over_closed": max(inv),
                            "beta0": b0, "one_over_perron_whole": 1.0 / lam,
                            "min_over_all_components": min(inv_scc),
                            "beta_off_closed_family_by": cross_b,
                            "alpha_off_all_components_by": cross_a})
    ok = (rows >= 5 and bad_a == 0 and bad_b == 0
          and bad_naive > 0 and bad_cross_a > 0)
    detail = (f"{rows} simple economies (B = I). **alpha_0 is the max of 1/lambda over the "
              f"parts closed under consumption** in {rows - bad_a} of {rows}, and "
              f"**beta_0 is 1/lambda_PF of the whole matrix**, equivalently the min over "
              f"all strongly connected components, in {rows - bad_b} of {rows}. "
              f"Both cross readings fail: beta_0 off the closed family is wrong in "
              f"{bad_naive} of {rows}, alpha_0 off the all-components family is wrong in "
              f"{bad_cross_a} of {rows}. So neither single family carries both halves")
    return bool(ok), detail, {"two_families": detail_rows}


# ------------------------------------------------- B80-4  why the two supports differ

def check_support_constraint(rng, reps):
    """B80-4 own_reading: the support of x is closed under consumption; p's is not.

    This is B75's registration answered, and B77's: the active set lives inside a
    closed part, and it is the one attaining alpha_0.
    """
    rows, bad, loose = 0, 0, 0
    out = []
    for k in range(reps):
        A, B = draw_simple(rng)
        parts = closed_parts(A, B)
        if not parts:
            continue
        vals = []
        for S in parts:
            lam = perron(A[np.ix_(S, S)])
            vals.append(1.0 / lam if lam > 0 else None)
        if any(v is None for v in vals):
            continue
        a0, x, p = b75.solution(A, B)
        if a0 is None or x is None or p is None:
            continue
        rows += 1
        sup_x = {i for i, v in enumerate(x) if v > 1e-8}
        sup_p = {i for i, v in enumerate(p) if v > 1e-8}
        top = parts[int(np.argmax(vals))]
        inside = sup_x <= set(top)
        # is the support of x closed under consumption on its own
        closed_x = all(A[i, j] == 0 for i in sup_x for j in range(A.shape[1])
                       if j not in sup_x)
        if not (inside and closed_x):
            bad += 1
        if not (sup_p <= set(top)):
            loose += 1
        out.append({"case": k, "support_x": sorted(sup_x), "support_p": sorted(sup_p),
                    "top_part": top, "x_inside_top": bool(inside),
                    "x_support_closed": bool(closed_x),
                    "p_inside_top": bool(sup_p <= set(top))})
    ok = rows >= 5 and bad == 0 and loose > 0
    detail = (f"{rows} simple economies: the support of the intensity vector is closed "
              f"under consumption and sits inside the part attaining alpha_0 in "
              f"{rows - bad} of {rows}. The price vector's support is not confined that "
              f"way in {loose} of {rows}, which is the asymmetry stated as a count")
    return bool(ok), detail, {"supports": out}


# ------------------------------------------------- B80-5  the gap is a connectivity fact

def check_gap_is_connectivity(rng, reps):
    """B80-5 own_reading: irreducible forces alpha_0 = beta_0; reducible permits a gap."""
    irr, red = [], []
    pool = [("example 1", np.array(b75.QE1_A, float), np.array(b75.QE1_B, float)),
            ("example 2", np.array(b75.QE2_A, float), np.array(b75.QE2_B, float))]
    for k in range(reps):
        pool.append((f"simple {k}", *draw_simple(rng)))
    for k in range(reps):
        n = int(rng.integers(3, 6))
        A = rng.uniform(0.2, 1.2, (n, n))          # dense, so irreducible
        pool.append((f"dense {k}", A, np.eye(n)))
    for name, A, B in pool:
        a, b = b75.expansion_factor(A, B), b75.interest_factor(A, B)
        if a is None or b is None:
            continue
        row = {"case": name, "alpha": a, "beta": b, "gap": a - b}
        (irr if is_irreducible(A, B) else red).append(row)
    bad = [r for r in irr if abs(r["gap"]) >= FACTOR_TOL]
    wide = [r for r in red if r["gap"] > GAP_FLOOR]
    ok = not bad and len(irr) >= 3 and len(wide) >= 1
    detail = (f"{len(irr)} irreducible economies, every one with |alpha - beta| below "
              f"{FACTOR_TOL:.0e}, {len(bad)} exception(s); {len(red)} reducible, of which "
              f"{len(wide)} carry a gap above {GAP_FLOOR:.0e}, largest "
              f"{max([r['gap'] for r in red], default=0.0):.6f}. Reducible permits a gap "
              f"and does not force one, so this is stated in one direction only")
    return bool(ok), detail, {"irreducible_cases": irr, "reducible_cases": red}

# ------------------------------------------------- B80-6  H-zero against H-one

def cycle_sums(A, B, p):
    """The field on activities: the sum around activity j's cycle at prices p."""
    out = []
    for j in range(A.shape[0]):
        cost = float(A[j] @ p)
        rev = float(B[j] @ p)
        out.append(np.log(rev / cost) if cost > 1e-12 and rev > 1e-12 else None)
    return out


def check_h0_against_h1(rng, reps):
    """B80-6 own_reading: the gap and the spread of cycle sums are two objects.

    Both off-diagonal cells have to be exhibited.  Failing to find either would say
    they are one object, and that would be a finding rather than a broken check.
    """
    cell_b = None   # irreducible, gap zero, cycle sums not all equal
    cell_c = None   # reducible, gap positive, cycle sums equal inside each part
    # cell c: the published reducible example, read part by part
    A2, B2 = np.array(b75.QE2_A, float), np.array(b75.QE2_B, float)
    a2, b2 = b75.expansion_factor(A2, B2), b75.interest_factor(A2, B2)
    parts2 = closed_parts(A2, B2)
    spreads = []
    for S in parts2:
        T, As, Bs = restrict(A2, B2, S)
        a, x, p = b75.solution(As, Bs)
        if a is None:
            continue
        sums = [s for s in cycle_sums(As, Bs, p) if s is not None]
        spreads.append(max(sums) - min(sums) if sums else None)
    if a2 is not None and b2 is not None and spreads and all(
            s is not None and s < 1e-6 for s in spreads):
        cell_c = {"case": "example 2", "gap": a2 - b2, "parts": parts2,
                  "within_part_spread": spreads}
    # cell b: search irreducible economies for a spread.
    # A simple economy will not supply one: with B = I and A irreducible the Perron
    # vector is strictly positive, so every activity runs and every cycle sum is the
    # same number.  The cell opens exactly when there are more activities than goods,
    # which is B75's bound on the active set seen from the other side.
    square_tried, square_spreads = 0, []
    for k in range(reps * 2):
        nn = int(rng.integers(3, 7))
        A = rng.uniform(0.2, 1.2, (nn, nn))     # dense, hence irreducible
        B = np.eye(nn)
        if not is_irreducible(A, B):
            continue
        a, x, p = b75.solution(A, B)
        if a is None or p is None:
            continue
        s = [v for v in cycle_sums(A, B, p) if v is not None]
        if len(s) >= 2:
            square_tried += 1
            square_spreads.append(max(s) - min(s))
    for k in range(reps * 20):
        n = int(rng.integers(4, 8))
        mg = int(rng.integers(2, n))            # more activities than goods
        A, B = draw_economy(rng, n, mg, density=0.45)
        if not is_irreducible(A, B):
            continue
        a, x, p = b75.solution(A, B)
        b = b75.interest_factor(A, B)
        if a is None or b is None or p is None:
            continue
        sums = [s for s in cycle_sums(A, B, p) if s is not None]
        if len(sums) < 2:
            continue
        spread = max(sums) - min(sums)
        if abs(a - b) < FACTOR_TOL and spread > 1e-3:
            idle = [i for i, v in enumerate(x) if v <= 1e-8]
            cell_b = {"case": f"rectangular {k}", "gap": a - b, "spread": spread,
                      "idle_activities": idle, "n_activities": int(A.shape[0]),
                      "n_goods": int(A.shape[1]),
                      "square_economies_tried": square_tried,
                      "worst_square_spread": max(square_spreads) if square_spreads else None}
            break
    ok = cell_b is not None and cell_c is not None
    if ok:
        ws = cell_b["worst_square_spread"]
        detail = (f"both off-diagonal cells exhibited. Irreducible with a spread: gap "
                  f"{cell_b['gap']:.2e} and cycle sums spanning {cell_b['spread']:.4f} "
                  f"over {cell_b['n_activities']} activities on "
                  f"{cell_b['n_goods']} goods, {len(cell_b['idle_activities'])} of them "
                  f"idle. It takes more activities than goods: on "
                  f"{cell_b['square_economies_tried']} irreducible simple economies the "
                  f"worst spread was "
                  f"{('%.2e' % ws) if ws is not None else 'n/a'}, because with B = I and A "
                  f"irreducible the Perron vector is strictly positive so nothing is idle. "
                  f"Reducible with no spread inside a part: gap {cell_c['gap']:.6f} while "
                  f"each of the {len(cell_c['parts'])} parts carries one common sum to "
                  f"within 1e-6. So a gap is a statement about connectivity and a spread "
                  f"is a statement about the field")
    else:
        detail = (f"cell with an irreducible spread: {'found' if cell_b else 'not found'}; "
                  f"cell with a reducible zero spread: {'found' if cell_c else 'not found'}")
    return bool(ok), detail, {"irreducible_with_spread": cell_b,
                              "reducible_without_spread": cell_c}


# ------------------------------------------------- B80-7  the three registrations

REGISTRATIONS = {
    "B75": ("which component alpha and beta are read off in a reducible system, "
            "which needs the decomposition computed first",
            "B80-3 and B80-4: alpha is the max over the parts closed under "
            "consumption and the intensity vector lives in the one attaining it; "
            "beta is not read off that family at all, it is the whole matrix"),
    "B71": ("the Kemeny-Morgenstern-Thompson generalisation, which relaxes the "
            "positivity assumption",
            "B80-1, B80-2 and B80-5: independence is enumerated two ways, the two "
            "published examples read back, and irreducibility is what forces the "
            "two factors together"),
    "B77": ("joining the continuum's active set to B75's reducible decomposition",
            "B80-4: the active set is confined to a part closed under consumption, "
            "whatever the size of the index set, because the constraint is on the "
            "support and not on the count"),
}


def check_registrations():
    """B80-7 bookkeeping: each registration named with the criterion that answers it."""
    rows = [{"registered_by": k, "text": v[0], "answered_by": v[1]}
            for k, v in REGISTRATIONS.items()]
    ok = len(rows) == 3 and all(r["answered_by"] for r in rows)
    detail = ("three registrations closed by this station: " +
              "; ".join(f"{r['registered_by']} -> {r['answered_by'].split(':')[0]}"
                        for r in rows))
    return bool(ok), detail, {"registrations": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    results = [
        ("B80-1", "known_answer",
         "both published example economies return their published expansion and "
         "interest factors, and their published reducibility",
         check_published()),
        ("B80-2", "instrument",
         "enumerating independent subsets over goods and over activities give the "
         "same family, which checks the translation of the definition",
         check_two_enumerations(rng, a.reps)),
        ("B80-3", "own_reading",
         "on a simple economy alpha_0 is the max over the parts closed under "
         "consumption while beta_0 is 1/lambda_PF of the whole matrix, so the two "
         "factors are not read off one family",
         check_two_families(rng, a.reps)),
        ("B80-4", "own_reading",
         "the support of the intensity vector is closed under consumption and lies "
         "in the part attaining alpha_0; the price vector's support is not confined",
         check_support_constraint(rng, a.reps)),
        ("B80-5", "own_reading",
         "an irreducible economy has alpha_0 = beta_0 and a reducible one may carry "
         "a gap, so the gap is a statement about connectivity",
         check_gap_is_connectivity(rng, a.reps)),
        ("B80-6", "own_reading",
         "the gap between the factors and the spread of the cycle sums are two "
         "objects: both off-diagonal cells are exhibited",
         check_h0_against_h1(rng, a.reps)),
        ("B80-7", "bookkeeping",
         "the three registrations this station closes, each named with the criterion "
         "that answers it",
         check_registrations()),
    ]

    mapping = {
        "B80-1": "both factors inside the published tolerance and the reducibility of each "
                 "example as published -> PASS; else FAIL",
        "B80-2": "the two enumerations agree on every economy AND both reducible and "
                 "irreducible cases occur -> PASS; any disagreement, or only one branch "
                 "present, -> FAIL",
        "B80-3": "alpha_0 matches the max over closed parts everywhere AND beta_0 matches "
                 "1/lambda_PF everywhere AND the one-family reading is wrong somewhere -> "
                 "PASS. The third clause is required: if it were never wrong the two "
                 "families would be one and this criterion would be empty",
        "B80-4": "the intensity support closed and inside the top part everywhere, AND the "
                 "price support outside it somewhere -> PASS; else FAIL",
        "B80-5": "no irreducible economy carries a gap AND at least one reducible economy "
                 "does -> PASS; else FAIL. Stated one way: reducible permits a gap and "
                 "does not force one",
        "B80-6": "both off-diagonal cells exhibited -> PASS; either missing -> FAIL, and a "
                 "missing cell would be a finding about the two objects being one, not a "
                 "broken check",
        "B80-7": "three registrations, each with the criterion that answers it -> PASS",
    }

    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep) in results:
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail}")

    rec = {
        "stage": "B80",
        "config": {"seed": a.seed, "reps": a.reps, "factor_tol": FACTOR_TOL,
                   "published_tol": PUBLISHED_TOL, "gap_floor": GAP_FLOOR,
                   "solver": "b75_rectangular_programme, imported not rewritten",
                   "bisect_iters": b75.BISECT_ITERS},
        "sources": {
            "examples_and_statement":
                "QuantEcon, Von Neumann Growth Model (and a Generalization): the two "
                "example economies, the definition of an independent subset, Theorem I "
                "and Theorem II, and the line alpha_0 = max_i alpha_i and beta_0 = "
                "min_i beta_i stated for a simple economy with B = I",
            "original":
                "Kemeny, J. G., Morgenstern, O. and Thompson, G. L. (1956), A "
                "Generalization of the von Neumann Model of an Expanding Economy, "
                "Econometrica 24, 115-135",
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
