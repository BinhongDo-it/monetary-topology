"""B147: the fewest common price bases a hospital file needs, with matching bounds.

A set of columns has one common price base when there are column factors alpha_a and item bases beta_i
with every per-item cell of the set inside its printing-grid interval:

    ln P(a, i) - flog(a, i) - EPS/2  <=  alpha_a + beta_i  <=  ln P(a, i) + flog(a, i) + EPS/2.

The fewest common price bases is the smallest number of disjoint column sets, covering every column,
each with one such base. Only per-item cells (a percentage of billed charges or a fee schedule) enter;
a column with no per-item cell imposes nothing and may sit in any set.

Two bounds are computed and the minimum is printed only when they meet.

Lower bound. Two columns conflict when the price-ratio intervals on the per-item rows they share have
no common point: max(r - w) > min(r + w), with r the log ratio and w = flog_a + flog_b + EPS. No set
with one base can hold both, so the columns of any clique of pairwise conflicts need one set each.
Every conflict on the clique is checked again in exact rational arithmetic on the two rows that
attain the extremes. The clique comes from a branch-and-bound search with a node budget; when the
budget runs out the clique found so far is still a valid lower bound, and the record says so.

Upper bound. The conflict graph is coloured greedily (DSATUR). A colour class has no pairwise
conflict, which does not by itself give one base: three columns can agree pair by pair and still
disagree around the cycle. So each class gets a joint check: alpha from the difference constraints
of all its column pairs (a negative cycle means no base), then every cell of the class is checked
with directed rounding on the inner side of its interval, so a pass shows a base exists at the
printed precision with no added tolerance. A class that fails is split, column by column, into sets
that pass the same check. The upper bound is the number of sets that passed.

Eliminating beta: for one item a beta exists exactly when the item's intervals for beta intersect, and
that holds exactly when every pair of the set's columns with a cell on the item satisfies the pair's
ratio interval there. So the pair intervals carry the whole joint constraint, and the negative-cycle
test on them is the joint test.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np

PER_ITEM = (0, 1)                 # the method codes charged per item: percentage of billed charges, fee schedule
EPS_HALF = Fraction(1, 2_000_000_000)   # half of the script's EPS = 1e-9, exactly
CLIQUE_NODE_BUDGET = 2_000_000
MARGIN = 1e-12                    # inward margin when building alpha from pair intervals; the row check decides


def per_item_columns(prep: dict) -> dict:
    """{column id: (rows, log price, floor)} on per-item cells only; columns with none map to empty arrays."""
    out = {}
    for c, col in prep["cols"].items():
        m = np.isin(col["meth"], PER_ITEM)
        out[c] = (col["rows"][m], col["logp"][m], col["flog"][m])
    return out


def pair_intervals(cols: dict, eps: float) -> dict:
    """For each column pair sharing a per-item row: the ratio interval [L, U] and the rows attaining L and U."""
    ids = sorted(cols)
    out = {}
    for x in range(len(ids)):
        ra, ya, fa = cols[ids[x]]
        if not len(ra):
            continue
        for y in range(x + 1, len(ids)):
            rb, yb, fb = cols[ids[y]]
            if not len(rb):
                continue
            common, ia, ib = np.intersect1d(ra, rb, assume_unique=True, return_indices=True)
            if not len(common):
                continue
            r = ya[ia] - yb[ib]
            w = fa[ia] + fb[ib] + eps
            lo, hi = r - w, r + w
            il, iu = int(lo.argmax()), int(hi.argmin())
            out[(ids[x], ids[y])] = {"L": float(lo[il]), "U": float(hi[iu]), "rows": int(len(common)),
                                     "lower_row": int(common[il]), "upper_row": int(common[iu])}
    return out


def _cell(cols, c, row):
    rows, y, f = cols[c]
    j = int(np.searchsorted(rows, row))
    if j >= len(rows) or rows[j] != row:
        raise ValueError("missing cell")
    return Fraction(float(y[j])), Fraction(float(f[j]))


def exact_conflict(cols: dict, a, b, lower_row: int, upper_row: int) -> bool:
    """The pair interval is empty in exact arithmetic on the binary64 values (strict inequality)."""
    ay, af = _cell(cols, a, lower_row)
    by, bf = _cell(cols, b, lower_row)
    lower = ay - by - af - bf - 2 * EPS_HALF
    ay, af = _cell(cols, a, upper_row)
    by, bf = _cell(cols, b, upper_row)
    upper = ay - by + af + bf + 2 * EPS_HALF
    return lower > upper


def maximum_clique(ids, adj: dict, budget: int = CLIQUE_NODE_BUDGET):
    """Branch and bound; returns (clique, finished). An unfinished search still returns a clique."""
    best = []
    nodes = 0
    finished = True

    class Stop(Exception):
        pass

    def search(chosen, candidates):
        nonlocal best, nodes
        nodes += 1
        if nodes > budget:
            raise Stop
        if len(chosen) + len(candidates) <= len(best):
            return
        while candidates:
            if len(chosen) + len(candidates) <= len(best):
                return
            v = max(candidates, key=lambda c: (len(adj[c] & candidates), -c))
            candidates.remove(v)
            more = candidates & adj[v]
            if not more:
                if len(chosen) + 1 > len(best):
                    best = chosen + [v]
            else:
                search(chosen + [v], more)

    try:
        search([], set(ids))
    except Stop:
        finished = False
    return sorted(best), finished


def dsatur(ids, adj: dict) -> list:
    colour = {}
    while len(colour) < len(ids):
        c = max((c for c in ids if c not in colour),
                key=lambda c: (len({colour[v] for v in adj[c] if v in colour}), len(adj[c]), -c))
        used = {colour[v] for v in adj[c] if v in colour}
        colour[c] = next(k for k in range(len(ids)) if k not in used)
    groups = {}
    for c, k in colour.items():
        groups.setdefault(k, []).append(c)
    return [sorted(groups[k]) for k in sorted(groups)]


def alpha_from_pairs(group, pairs: dict, margin: float):
    """Bellman-Ford on alpha_a - alpha_b in [L + margin, U - margin]; None on a negative cycle."""
    s = set(group)
    edges = []
    for (a, b), p in pairs.items():
        if a in s and b in s:
            edges.append((b, a, p["U"] - margin))     # alpha_a <= alpha_b + U
            edges.append((a, b, -p["L"] - margin))    # alpha_b <= alpha_a - L
    d = {c: 0.0 for c in group}
    for _ in range(len(group) + 1):
        changed = False
        for u, v, w in edges:
            if d[v] > d[u] + w:
                d[v] = d[u] + w
                changed = True
        if not changed:
            return d
    return None


def row_check(cols: dict, group, alpha: dict) -> dict:
    """Every per-item cell of the group, with each interval end rounded inward: a pass shows a beta exists per item."""
    rows_all = [cols[c][0] for c in group if len(cols[c][0])]
    if not rows_all:
        return {"passes": True, "cells": 0, "items": 0}
    size = int(max(int(r.max()) for r in rows_all)) + 1
    lower = np.full(size, -np.inf)
    upper = np.full(size, np.inf)
    seen = np.zeros(size, dtype=bool)
    up = lambda v: np.nextafter(v, np.inf)       # noqa: E731
    down = lambda v: np.nextafter(v, -np.inf)    # noqa: E731
    eps_lo = float(np.nextafter(float(EPS_HALF), -np.inf))
    cells = 0
    for c in group:
        rows, y, f = cols[c]
        if not len(rows):
            continue
        a = float(alpha[c])
        np.maximum.at(lower, rows, up(up(up(y - a) - f) - eps_lo))
        np.minimum.at(upper, rows, down(down(down(y - a) + f) + eps_lo))
        seen[rows] = True
        cells += len(rows)
    gap = float((lower[seen] - upper[seen]).max())
    return {"passes": bool(gap <= 0), "cells": int(cells), "items": int(seen.sum())}


def joint_base(cols: dict, group, pairs: dict):
    """(alpha, check) when the group has one common base at the printed precision, else (None, check)."""
    for margin in (MARGIN, 0.0):
        alpha = alpha_from_pairs(group, pairs, margin)
        if alpha is None:
            continue
        chk = row_check(cols, group, alpha)
        if chk["passes"]:
            return alpha, chk
    return None, None


def split_into_bases(cols: dict, group, pairs: dict) -> list:
    """First fit, every placement checked jointly; returns [(members, alpha, check)]."""
    sets = []
    for c in group:
        for k, (members, _, _) in enumerate(sets):
            alpha, chk = joint_base(cols, members + [c], pairs)
            if alpha is not None:
                sets[k] = (members + [c], alpha, chk)
                break
        else:
            alpha, chk = joint_base(cols, [c], pairs)
            if alpha is None:
                raise ValueError("a single column fails its own row check")
            sets.append(([c], alpha, chk))
    return sets


def fewest_bases(prep: dict, read_pairs_out: list | None = None, eps: float = 1e-9,
                 clique_budget: int = CLIQUE_NODE_BUDGET, joint_check: bool = True) -> dict:
    """Lower bound, upper bound and (when they meet) the fewest common price bases for one file.

    read_pairs_out: the column pairs from read_pairs; when given, its per-item verdicts (a square above the floor
    on at least two shared rows) are compared with the conflicts computed here and the disagreements counted.
    joint_check=False skips the joint check of each colour class (selftest only: it must then miss a cycle)."""
    cols = per_item_columns(prep)
    names = {c: v["name"] for c, v in prep["cols"].items()}
    ids = sorted(cols)
    pairs = pair_intervals(cols, eps)
    adj = {c: set() for c in ids}
    float_only = 0
    for (a, b), p in pairs.items():
        if p["L"] > p["U"]:
            if exact_conflict(cols, a, b, p["lower_row"], p["upper_row"]):
                adj[a].add(b)
                adj[b].add(a)
            else:
                float_only += 1
    n_conflicts = sum(len(v) for v in adj.values()) // 2
    disagree = None
    if read_pairs_out is not None:
        theirs = {(p["a"], p["b"]) for p in read_pairs_out
                  if p["per_item"]["rows"] >= 2 and p["per_item"]["above_floor"]}
        mine = {(a, b) for a in adj for b in adj[a] if a < b}
        disagree = len(theirs ^ mine)

    clique, finished = maximum_clique(ids, adj, clique_budget)
    lower = len(clique) if any(len(cols[c][0]) for c in ids) else 0

    sets = []
    split = 0
    for g in dsatur(ids, adj):
        if not joint_check:
            sets.append((g, None, {"cells": 0}))
            continue
        alpha, chk = joint_base(cols, g, pairs)
        if alpha is not None:
            sets.append((g, alpha, chk))
        else:
            parts = split_into_bases(cols, g, pairs)
            split += 1
            sets.extend(parts)
    upper = len(sets)
    covered = sorted(c for g, _, _ in sets for c in g) == ids
    unobserved = [c for c in ids if not len(cols[c][0])]
    return {
        "lower_bound": lower,
        "lower_bound_search_finished": finished,
        "upper_bound": upper,
        "minimum": lower if lower == upper and covered else None,
        "lower_bound_clique": [names[c] for c in clique],
        "upper_bound_sets": [[names[c] for c in g] for g, _, _ in sets],
        "upper_bound_sets_cover_every_column_once": covered,
        "colour_classes_split_by_the_joint_check": split,
        "per_item_cells_checked_jointly": int(sum(chk["cells"] for _, _, chk in sets)),
        "column_pairs_sharing_a_per_item_row": len(pairs),
        "conflicting_column_pairs": n_conflicts,
        "conflicts_in_float_not_confirmed_exactly": float_only,
        "conflicts_differing_from_the_square_reading": disagree,
        "columns_without_per_item_cells": [names[c] for c in unobserved],
    }
