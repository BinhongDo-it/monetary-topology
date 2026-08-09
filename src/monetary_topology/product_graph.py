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
