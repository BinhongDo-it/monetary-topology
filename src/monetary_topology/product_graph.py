"""The enlarged graph `Gamma = G box H` on positions crossed with agent classes.

Proved in ``docs/b1_theorem.md``. This module is the executable half: it builds
the graph, puts the field on it as a 1-cochain, and exposes the three objects the
theorems are about — cycle sums, the potential reconstructed by path integral, and
the four-cycles the theorems call squares.

Why a separate module from ``topology.py``
------------------------------------------
``topology.py`` serves stage A2c, where the complex is a clique complex and the
2-cells are triangles. The natural 2-cells of a Cartesian product are **squares**,
so the two are different complexes on purpose and sharing code between them would
invite exactly the confusion the theorem document flags in its section 10. Nothing
here touches the A2c path.

What the field is
-----------------
A position graph `G` on `n` positions, `m` agent classes, and an antisymmetric
array `W` of shape `(m, n, n)` with

```
W[a, i, j]  =  log of the rate at which class a converts position i into j
W[a, j, i]  =  -W[a, i, j]
```

`Gamma` carries two kinds of edge: position edges `(a,i)-(a,j)` weighted
`W[a,i,j]`, and agent edges `(a,g)-(b,g)` weighted **zero**, because a position is
the same position whoever holds it. When that is false the theorem does not apply,
and section 8 of the document is about exactly which cases those are.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def vertex(a: int, i: int, n: int) -> int:
    """Index of position ``i`` in slice ``a``. Agent index varies slowest."""
    return a * n + i


def undirected_pairs(adjacency: np.ndarray) -> list[tuple[int, int]]:
    """Edges of a symmetric adjacency matrix, each listed once as ``(i, j)``, i<j."""
    idx = np.triu(np.asarray(adjacency) != 0, k=1)
    rows, cols = np.nonzero(idx)
    return [(int(i), int(j)) for i, j in zip(rows, cols, strict=True)]


def complete_agent_graph(m: int) -> np.ndarray:
    """`K_m`. Any class can take over a transferable position from any other."""
    return (
        (np.ones((m, m), dtype=int) - np.eye(m, dtype=int))
        if m > 1
        else np.zeros((1, 1), dtype=int)
    )


def box_product(adj_g: np.ndarray, adj_h: np.ndarray) -> np.ndarray:
    """Adjacency of `G box H`, vertices ordered ``vertex(a, i, n)``."""
    adj_g = np.asarray(adj_g)
    adj_h = np.asarray(adj_h)
    n, m = adj_g.shape[0], adj_h.shape[0]
    out = np.zeros((m * n, m * n), dtype=int)
    for a in range(m):
        for i, j in undirected_pairs(adj_g):
            u, v = vertex(a, i, n), vertex(a, j, n)
            out[u, v] = out[v, u] = 1
    for i in range(n):
        for a, b in undirected_pairs(adj_h):
            u, v = vertex(a, i, n), vertex(b, i, n)
            out[u, v] = out[v, u] = 1
    return out


@dataclass(frozen=True)
class Cochain:
    """A 1-cochain on `Gamma`, stored on oriented edges.

    ``value(u, v) == -value(v, u)`` is enforced on read rather than stored twice,
    so an asymmetric assignment cannot be made by accident.
    """

    weights: dict[tuple[int, int], float]

    def value(self, u: int, v: int) -> float:
        if (u, v) in self.weights:
            return self.weights[(u, v)]
        if (v, u) in self.weights:
            return -self.weights[(v, u)]
        raise KeyError(f"no edge between {u} and {v}")

    def sum_over(self, walk: list[int]) -> float:
        """Sum along a walk given as a vertex list; close it to get a cycle sum."""
        return float(
            sum(self.value(walk[t], walk[t + 1]) for t in range(len(walk) - 1))
        )


def cochain_from_field(adj_g: np.ndarray, field: np.ndarray, m: int) -> Cochain:
    """Put ``W`` on the position edges and zero on the agent edges."""
    adj_g = np.asarray(adj_g)
    field = np.asarray(field, dtype=np.float64)
    n = adj_g.shape[0]
    if field.shape != (m, n, n):
        raise ValueError(f"field must have shape {(m, n, n)}, got {field.shape}")
    asym = np.abs(field + np.swapaxes(field, 1, 2)).max()
    if asym > 1e-12:
        raise ValueError(f"field is not antisymmetric: max |W + W^T| = {asym:.3e}")

    weights: dict[tuple[int, int], float] = {}
    for a in range(m):
        for i, j in undirected_pairs(adj_g):
            weights[(vertex(a, i, n), vertex(a, j, n))] = float(field[a, i, j])
    for i in range(n):
        for a, b in undirected_pairs(complete_agent_graph(m)):
            weights[(vertex(a, i, n), vertex(b, i, n))] = 0.0
    return Cochain(weights)


def tier_positions(n_tiers: int) -> np.ndarray:
    """Adjacency of `G` for stage A3: a star with cash at the centre.

    Position `0` is cash and positions `1..Q` are the tiers. The only edges are
    cash to a tier and back, which is what an acquisition and a sale are, so the
    squares of `Gamma` are exactly the four-cycles A3-4 is stated on:
    `(a, cash) -> (a, q) -> (b, q) -> (b, cash)`.

    No tier-to-tier edge. Moving between tiers is a sale followed by a purchase
    and is already the composition of two edges that exist; adding a direct one
    would create cycles the registered criterion does not name.
    """
    if n_tiers < 1:
        raise ValueError("need at least one tier")
    n = n_tiers + 1
    adj = np.zeros((n, n))
    adj[0, 1:] = 1.0
    adj[1:, 0] = 1.0
    return adj


def tier_field(
    terms: np.ndarray, price_entry: np.ndarray, price_exit: np.ndarray
) -> np.ndarray:
    """Stage A3's field on the star, one slice per agent class.

    `W[a, cash, q] = log( P_q(exit) / (gamma[a, q] * P_q(entry)) )`, the log
    return to class `a` on entering tier `q` at `price_entry` and leaving at
    `price_exit`.

    This module never sees the simulation. It is handed the terms matrix and two
    price vectors and computes a field; whether the exponent that field implies
    matches the divergence a run produced is decided elsewhere, by code that
    does not import this file and that this file does not import. If the two
    were computed together their agreement would be an identity rather than a
    result, and criterion A3-4 would establish nothing.

    The price is expected to cancel out of every square. That is a property of
    the construction and it is left to be **observed** rather than assumed:
    nothing here divides it out.
    """
    terms = np.asarray(terms, dtype=np.float64)
    entry = np.asarray(price_entry, dtype=np.float64)
    exit_ = np.asarray(price_exit, dtype=np.float64)
    if terms.ndim != 2:
        raise ValueError("terms must be (classes, tiers)")
    m, q = terms.shape
    if entry.shape != (q,) or exit_.shape != (q,):
        raise ValueError(f"price vectors must have shape {(q,)}")
    if (terms <= 0).any() or (entry <= 0).any() or (exit_ <= 0).any():
        raise ValueError("terms and prices must be positive to take a logarithm")

    n = q + 1
    field = np.zeros((m, n, n))
    gain = np.log(exit_[None, :] / (terms * entry[None, :]))
    field[:, 0, 1:] = gain
    field[:, 1:, 0] = -gain
    return field


def exact_field(potential: np.ndarray, m: int) -> np.ndarray:
    """`W[a,i,j] = phi[j] - phi[i]`, the one-index null of Theorem 1 condition (1)."""
    phi = np.asarray(potential, dtype=np.float64)
    w = phi[None, :] - phi[:, None]
    return np.repeat(w[None, :, :], m, axis=0)


def per_agent_exact_field(potentials: np.ndarray) -> np.ndarray:
    """`W[a,i,j] = phi_a[j] - phi_a[i]`: every agent internally consistent.

    This is the case section 7 of the theorem document is about. Each `w_a` is
    exact, so no agent sees an inconsistency, and yet the squares are generally
    non-zero because the potentials differ. A field can be a family of gradients
    without being a gradient.
    """
    phi = np.asarray(potentials, dtype=np.float64)
    return phi[:, None, :] - phi[:, :, None]


def shared_field(w: np.ndarray, m: int) -> np.ndarray:
    """`W[a,i,j] = w[i,j]`: every class faces the same terms, exact or not.

    The complement of ``per_agent_exact_field``. That one gives each class its own
    consistent potential and lets the potentials differ, so the squares fire and
    the slice cycles do not. This one gives every class the *same* field without
    requiring it to be a gradient, so the slice cycles fire and the squares are
    identically zero, because a square sum is `w_a(i,j) - w_b(i,j)` and the two
    legs are now the same number.

    It exists because every field this project otherwise constructs makes the
    slice summand vanish by construction, which leaves Theorem 2's decomposition
    checked on only one of its two parts. See ``docs/b1_theorem.md`` section 11.1.
    """
    w = np.asarray(w, dtype=np.float64)
    asym = np.abs(w + w.T).max() if w.size else 0.0
    if asym > 1e-12:
        raise ValueError(f"w is not antisymmetric: max |w + w^T| = {asym:.3e}")
    return np.repeat(w[None, :, :], m, axis=0)


def slice_cycles(adj_g: np.ndarray, m: int) -> list[list[int]]:
    """Lifts of a fundamental cycle basis of `G` into each slice `{a} x N`.

    One list per class per basis cycle, as closed vertex walks, in the same form
    ``squares`` returns so the two can be summed over by the same code.
    """
    n = np.asarray(adj_g).shape[0]
    basis = spanning_tree_cycles(adj_g)
    return [[vertex(a, x, n) for x in cycle] for a in range(m) for cycle in basis]


def squares(adj_g: np.ndarray, m: int) -> list[list[int]]:
    """The four-cycles `(a,i) (a,j) (b,j) (b,i)`, as closed vertex walks."""
    n = np.asarray(adj_g).shape[0]
    out = []
    for i, j in undirected_pairs(adj_g):
        for a, b in undirected_pairs(complete_agent_graph(m)):
            out.append(
                [
                    vertex(a, i, n),
                    vertex(a, j, n),
                    vertex(b, j, n),
                    vertex(b, i, n),
                    vertex(a, i, n),
                ]
            )
    return out


def spanning_tree_cycles(adjacency: np.ndarray) -> list[list[int]]:
    """A fundamental cycle basis: one cycle per non-tree edge of a spanning tree."""
    adj = np.asarray(adjacency)
    parent: dict[int, int | None] = {0: None}
    stack, seen, tree = [0], {0}, set()
    while stack:
        u = stack.pop()
        for v in np.nonzero(adj[u])[0]:
            v = int(v)
            if v not in seen:
                seen.add(v)
                parent[v] = u
                tree.add((min(u, v), max(u, v)))
                stack.append(v)

    def to_root(x: int) -> list[int]:
        path = []
        while parent[x] is not None:
            path.append(x)
            x = parent[x]  # type: ignore[assignment]
        path.append(x)
        return path

    cycles = []
    for i, j in undirected_pairs(adj):
        if (i, j) in tree or i not in seen or j not in seen:
            continue
        pi, pj = to_root(i), to_root(j)
        on_pj = set(pj)
        lca = next(x for x in pi if x in on_pj)
        left = pi[: pi.index(lca) + 1]
        right = pj[: pj.index(lca) + 1]
        walk = left + right[::-1][1:]
        cycles.append(walk + [walk[0]])
    return cycles


def potential_from_cochain(
    adjacency: np.ndarray, omega: Cochain
) -> tuple[np.ndarray, float]:
    """Reconstruct `psi` by path integral, and report how badly it fails.

    Theorem 1's (3) implies (2). Fix a basepoint and integrate along a spanning
    tree; the result satisfies `d0 psi = omega` on every edge **iff** every cycle
    sum vanishes. So the returned residual is zero exactly when the cochain is
    exact, and the function is a test rather than an assumption: it always returns
    something, and the caller reads the residual.
    """
    adj = np.asarray(adjacency)
    k = adj.shape[0]
    psi = np.full(k, np.nan)
    psi[0] = 0.0
    stack = [0]
    while stack:
        u = stack.pop()
        for v in np.nonzero(adj[u])[0]:
            v = int(v)
            if np.isnan(psi[v]):
                psi[v] = psi[u] + omega.value(u, v)
                stack.append(v)

    residual = 0.0
    for i, j in undirected_pairs(adj):
        residual = max(residual, abs((psi[j] - psi[i]) - omega.value(i, j)))
    return psi, float(residual)


def betti_formula(n: int, e_g: int, m: int, e_h: int) -> int:
    """`b1(Gamma) = m*e_G + n*e_H - m*n + 1`, for connected `G` and `H`.

    At `m = 1` this returns `e_G - n + 1 = b1(G)`: the one-index case, in which
    every square degenerates and the obstruction is empty.
    """
    return m * e_g + n * e_h - m * n + 1


def cycle_matrix(adj_g: np.ndarray, m: int) -> np.ndarray:
    """Theorem 2's generating set, as vectors in the edge space of `Gamma`.

    Rows: slice cycles in one slice, agent cycles at one position, and every
    square. The rank of this matrix is the claim being checked; it must equal
    `E - V + C` computed directly on `Gamma`, which is a different computation
    entirely and shares no code with this one.
    """
    adj_g = np.asarray(adj_g)
    n = adj_g.shape[0]
    adj_h = complete_agent_graph(m)

    columns: dict[tuple[int, int], int] = {}
    for a in range(m):
        for i, j in undirected_pairs(adj_g):
            columns[(vertex(a, i, n), vertex(a, j, n))] = len(columns)
    for i in range(n):
        for a, b in undirected_pairs(adj_h):
            columns[(vertex(a, i, n), vertex(b, i, n))] = len(columns)

    def as_vector(walk: list[int]) -> np.ndarray:
        vec = np.zeros(len(columns))
        for t in range(len(walk) - 1):
            u, v = walk[t], walk[t + 1]
            if (u, v) in columns:
                vec[columns[(u, v)]] += 1.0
            else:
                vec[columns[(v, u)]] -= 1.0
        return vec

    rows = [
        as_vector([vertex(0, x, n) for x in cyc]) for cyc in spanning_tree_cycles(adj_g)
    ]
    if m > 1:
        rows += [
            as_vector([vertex(x, 0, n) for x in cyc])
            for cyc in spanning_tree_cycles(adj_h)
        ]
    rows += [as_vector(sq) for sq in squares(adj_g, m)]
    return np.array(rows) if rows else np.zeros((0, len(columns)))


def brute_force_holonomy(values: np.ndarray) -> float:
    """Mean squared square-sum over ordered agent pairs, by enumeration.

    Theorem 3 says this equals `2 * Var(values)`. The point of computing it the
    slow way is that the fast way is the thing being checked: a check that
    evaluates the closed form and compares it to itself establishes nothing.

    Each term is the sum of the four oriented edge weights around one square,
    `w_a + 0 - w_b + 0`, accumulated as a cycle rather than as a difference of
    array entries, so the object being squared is a holonomy and not a residual.
    """
    x = np.asarray(values, dtype=np.float64)
    k = x.size
    if k == 0:
        return 0.0
    total = 0.0
    for p in range(k):
        # +w_a on the first position edge, 0 on the agent edge, -w_b on the
        # return position edge, 0 on the closing agent edge.
        loop_sums = x[p] + 0.0 - x + 0.0
        total += float(np.dot(loop_sums, loop_sums))
    return total / (k * k)


# ---------------------------------------------------------------------------
# The square complex.
#
# Added 2026-08-15. Everything above this line lives on the **1-skeleton** and
# needs no 2-cells, which is ``docs/b1_theorem.md`` section 12.2: Theorem 3's
# quantity is a sum around a closed walk and is invariant under every choice of
# `C_2`. So none of the functions below can move a single figure stage B2
# reports, and they are not here for that.
#
# They are here because there is exactly one claim in this repository that does
# depend on `C_2`, and it had no source. ``docs/b1_setup.md`` section 5 rules
# that deleting an edge has two distinct consequences, a **puncture** where
# `dim H^1` rises because `rank d_2` falls faster than `b_1`, and a
# **disconnection** where the component count rises and `b_1` does not, and it
# quotes measured numbers for both. Those numbers came from a script that was
# never committed. This block is what gives them one.
# ---------------------------------------------------------------------------


def path_graph(k: int) -> np.ndarray:
    """Adjacency of the path on ``k`` vertices. `b1 = 0`, so a product of two
    paths is a grid and every cycle in it is generated by unit squares."""
    if k < 1:
        raise ValueError("need at least one vertex")
    adj = np.zeros((k, k), dtype=int)
    for i in range(k - 1):
        adj[i, i + 1] = adj[i + 1, i] = 1
    return adj


def product_squares(adj_g: np.ndarray, adj_h: np.ndarray) -> list[list[int]]:
    """Cartesian four-cycles of `G box H`, for an arbitrary `H`.

    ``squares(adj_g, m)`` is this with `H = K_m`, and is left untouched because
    every existing caller passes a class count rather than a graph. The general
    form is needed because the carrier section 5 of ``docs/b1_setup.md`` measures
    on is a grid, where `H` is a path and not a complete graph.

    Vertex order matches :func:`vertex`, so the walks compose with everything
    above.
    """
    adj_g = np.asarray(adj_g)
    adj_h = np.asarray(adj_h)
    n = adj_g.shape[0]
    out = []
    for i, j in undirected_pairs(adj_g):
        for a, b in undirected_pairs(adj_h):
            out.append(
                [
                    vertex(a, i, n),
                    vertex(a, j, n),
                    vertex(b, j, n),
                    vertex(b, i, n),
                    vertex(a, i, n),
                ]
            )
    return out


def edge_columns(adjacency: np.ndarray) -> dict[tuple[int, int], int]:
    """One column per undirected edge, keyed by the pair with the lower index
    first. The orientation convention is fixed here and used by everything that
    builds a matrix over the edge space, so a sign error cannot enter twice."""
    return {pair: k for k, pair in enumerate(undirected_pairs(adjacency))}


def boundary_2(adjacency: np.ndarray, cells: list[list[int]]) -> np.ndarray:
    """`d_2` as a matrix of shape ``(len(cells), n_edges)``.

    Row ``t`` is the boundary of cell ``t``, written in the edge basis of
    :func:`edge_columns` with the sign given by the traversal direction. `d_2`
    proper is the transpose; the rank, which is all any caller here needs, is the
    same either way.

    Filling a cell is a claim and not a drawing. A four-cycle in a graph is an
    element of `ker d_1`; adding it to `C_2` declares it a **boundary** and
    changes `H_1`. Section 12.2 of ``docs/b1_theorem.md`` sets out what that does
    and does not change, and the short version is that it changes the
    classification of a square sum and never its value.
    """
    columns = edge_columns(adjacency)
    mat = np.zeros((len(cells), len(columns)))
    for t, walk in enumerate(cells):
        for s in range(len(walk) - 1):
            u, v = walk[s], walk[s + 1]
            if (u, v) in columns:
                mat[t, columns[(u, v)]] += 1.0
            elif (v, u) in columns:
                mat[t, columns[(v, u)]] -= 1.0
            else:
                raise KeyError(f"cell {t} uses a missing edge {(u, v)}")
    return mat


def n_components(adjacency: np.ndarray) -> int:
    """Connected components, by flood fill. ``topology.connected_components``
    does the same job for the A2c complex; this file does not import it, so that
    a change on that path cannot silently move a number on this one."""
    adj = np.asarray(adjacency)
    k = adj.shape[0]
    seen: set[int] = set()
    count = 0
    for start in range(k):
        if start in seen:
            continue
        count += 1
        stack = [start]
        seen.add(start)
        while stack:
            u = stack.pop()
            for v in np.nonzero(adj[u])[0]:
                v = int(v)
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
    return count


@dataclass(frozen=True)
class ComplexRanks:
    """The four numbers section 5 of ``docs/b1_setup.md`` decides on."""

    vertices: int
    edges: int
    components: int
    b1: int
    rank_d2: int
    dim_h1: int

    def line(self) -> str:
        return (
            f"V={self.vertices:4d}  E={self.edges:4d}  c={self.components:2d}  "
            f"b1={self.b1:3d}  rank d2={self.rank_d2:3d}  dim H1={self.dim_h1:3d}"
        )


def complex_ranks(
    adjacency: np.ndarray, cells: list[list[int]], tol: float = 1e-10
) -> ComplexRanks:
    """`b1 = E - V + c`, `rank d_2` by SVD, and `dim H^1 = b1 - rank d_2`.

    With no cells this returns `dim H^1 = b1`, which is the bare graph: there is
    no `d_1`, every 1-cochain is closed, and `H^1 = C^1 / im d_0` has dimension
    `b1`. That case is not a degenerate fallback, it is one of the two readings
    section 12.2 tabulates, and it is reachable by passing ``cells=[]``.
    """
    adj = np.asarray(adjacency)
    v = int(adj.shape[0])
    e = len(undirected_pairs(adj))
    c = n_components(adj)
    b1 = e - v + c
    if cells:
        sv = np.linalg.svd(boundary_2(adj, cells), compute_uv=False)
        rank = int((sv > max(tol, sv[0] * 1e-12 if sv.size else 0.0)).sum())
    else:
        rank = 0
    return ComplexRanks(v, e, c, b1, rank, b1 - rank)


def delete_edge(
    adjacency: np.ndarray, i: int, j: int, cells: list[list[int]]
) -> tuple[np.ndarray, list[list[int]]]:
    """Remove edge ``(i, j)`` and **every cell that used it**.

    The second half is the whole content. A 2-cell whose boundary is no longer in
    the graph is not a 2-cell, so `rank d_2` can fall by more than `b_1` does,
    and that gap is where `dim H^1` comes from. Dropping the edge while keeping
    the cells would be the arithmetic that makes a puncture invisible.
    """
    adj = np.asarray(adjacency).copy()
    if not adj[i, j]:
        raise ValueError(f"no edge between {i} and {j}")
    adj[i, j] = adj[j, i] = 0
    gone = {(min(i, j), max(i, j))}

    def survives(walk: list[int]) -> bool:
        return not any(
            (min(walk[s], walk[s + 1]), max(walk[s], walk[s + 1])) in gone
            for s in range(len(walk) - 1)
        )

    return adj, [w for w in cells if survives(w)]


def hole_kind(
    adjacency: np.ndarray, cells: list[list[int]], i: int, j: int
) -> tuple[str, ComplexRanks, ComplexRanks]:
    """Section 5 of ``docs/b1_setup.md``, executed.

    Returns ``"puncture"``, ``"disconnection"`` or ``"neither"``, with the ranks
    before and after so a caller reports the arithmetic rather than the verdict
    alone.

    **The test is whether the graph is still connected after the deletion**, and
    the two outcomes are different objects: a puncture raises `dim H^1` and is
    the accreditation row of that section, a disconnection raises the component
    count and is the non-assumable mortgage of ``docs/b1_theorem.md`` section
    12.1, which is `H^0` and belongs to loop B. Filing the second under `H^1`
    would hand a reader a number about one and a story about the other.
    """
    before = complex_ranks(adjacency, cells)
    adj, kept = delete_edge(adjacency, i, j, cells)
    after = complex_ranks(adj, kept)
    if after.components > before.components:
        return "disconnection", before, after
    if after.dim_h1 > before.dim_h1:
        return "puncture", before, after
    return "neither", before, after
