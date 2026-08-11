"""Directed edges: sub-potentials, strong connectivity, and the canonical split.

Proved in ``docs/b4_directed_edges.md``. This module is the executable half.

Why a separate module from ``product_graph.py``
-----------------------------------------------
``product_graph.py`` enforces antisymmetry on read: ``Cochain.value(u, v)``
returns ``-value(v, u)`` when only one orientation is stored, and
``cochain_from_field`` rejects a field whose ``W + W^T`` is non-zero. Those
guards are correct for Theorem 1 and they are exactly what a directed field
violates. Relaxing them in place would remove the guard from the stages that
need it, so the directed machinery lives here and the two do not share a field
representation.

The field
---------
A directed field is a mapping ``{(u, v): weight}`` over **ordered** pairs. The
reverse of a present edge may be absent, and when present it is an independent
number. ``ω(u, v)`` is the log of the rate at which the move ``u -> v`` can
actually be made, so a directed cycle with a **positive** sum is an arbitrage.

What is deliberately not here
-----------------------------
No generalisation of Theorem 2. The directed cycles of a graph form a cone
rather than a vector space, and a cone does not decompose as a direct sum;
``docs/b4_directed_edges.md`` §6 states this. Anything that looked like a
directed ``cycle_matrix`` would be asserting a splitting that is not proved.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Edges = dict[tuple[int, int], float]


@dataclass(frozen=True)
class DirectedField:
    """A weight on ordered pairs. No antisymmetry, no implied reverse edge."""

    weights: Edges
    n_vertices: int

    def __post_init__(self) -> None:
        for u, v in self.weights:
            if u == v:
                raise ValueError(f"self-loop at {u}; a position is not a move")
            if not (0 <= u < self.n_vertices and 0 <= v < self.n_vertices):
                raise ValueError(f"edge ({u}, {v}) outside 0..{self.n_vertices - 1}")

    def value(self, u: int, v: int) -> float:
        """The weight of the directed edge, or ``KeyError``.

        Deliberately does **not** fall back to ``-value(v, u)``. That fallback is
        what ``product_graph.Cochain`` does and it is right there and wrong here:
        the whole subject of this module is fields where the reverse leg is a
        different number, or is not available at all.
        """
        return self.weights[(u, v)]

    def has(self, u: int, v: int) -> bool:
        return (u, v) in self.weights

    def out_edges(self, u: int) -> list[tuple[int, float]]:
        return [(v, w) for (a, v), w in self.weights.items() if a == u]

    def sum_over(self, walk: list[int]) -> float:
        """Sum along a directed walk given as a vertex list."""
        return float(
            sum(self.value(walk[t], walk[t + 1]) for t in range(len(walk) - 1))
        )

    def two_way(self) -> list[tuple[int, int]]:
        """Unordered pairs present in both directions, each listed once, u < v."""
        return sorted(
            {
                (min(u, v), max(u, v))
                for (u, v) in self.weights
                if (v, u) in self.weights
            }
        )

    def one_way(self) -> list[tuple[int, int]]:
        """Ordered pairs present in one direction only."""
        return sorted((u, v) for (u, v) in self.weights if (v, u) not in self.weights)


def from_antisymmetric(cochain_weights: dict[tuple[int, int], float], n: int):
    """Build a directed field from an antisymmetric one, both legs written out.

    The bridge used by the reduction check. Given ``{(u, v): w}`` with each
    unordered pair listed once, write ``(v, u): -w`` explicitly, so the directed
    machinery sees a field with no implied reverses and Theorem 6 (3) applies.
    """
    out: Edges = {}
    for (u, v), w in cochain_weights.items():
        out[(u, v)] = float(w)
        out[(v, u)] = -float(w)
    return DirectedField(out, n)


# ---------------------------------------------------------------------------
# Theorem 4
# ---------------------------------------------------------------------------


def simple_directed_cycles(field: DirectedField) -> list[list[int]]:
    """Every simple directed cycle, by brute force, as closed vertex walks.

    Exponential and meant to be. It is the independent witness against which the
    Bellman-Ford construction is checked, and a check that shares the fast
    algorithm's reasoning establishes nothing. Callers keep the graph small.

    Each cycle is emitted once, rooted at its smallest vertex.
    """
    adj: dict[int, list[int]] = {u: [] for u in range(field.n_vertices)}
    for u, v in field.weights:
        adj[u].append(v)

    cycles: list[list[int]] = []

    def walk(start: int, path: list[int], on_path: set[int]) -> None:
        for v in adj[path[-1]]:
            if v == start:
                cycles.append([*path, start])
            elif v > start and v not in on_path:
                on_path.add(v)
                path.append(v)
                walk(start, path, on_path)
                path.pop()
                on_path.discard(v)

    for start in range(field.n_vertices):
        walk(start, [start], {start})
    return cycles


def worst_directed_cycle(field: DirectedField) -> tuple[float, list[int] | None]:
    """The largest directed cycle sum, by enumeration. Positive means arbitrage."""
    best, witness = -np.inf, None
    for cyc in simple_directed_cycles(field):
        s = field.sum_over(cyc)
        if s > best:
            best, witness = s, cyc
    return (float(best), witness) if witness is not None else (float("-inf"), None)


def sub_potential(field: DirectedField) -> tuple[np.ndarray | None, str]:
    """Theorem 4's construction. Returns ``(phi, "")`` or ``(None, reason)``.

    Bellman-Ford on the longest-walk problem from a super source joined to every
    vertex at weight zero, which is what initialising ``phi`` to zeros is. If a
    relaxation still fires on pass ``n``, a positive directed cycle is reachable
    and no sub-potential exists.

    Never enumerates a cycle, which is the point: ``worst_directed_cycle`` is the
    independent statement of the same condition.
    """
    n = field.n_vertices
    phi = np.zeros(n, dtype=np.float64)
    items = list(field.weights.items())
    for _ in range(n):
        changed = False
        for (u, v), w in items:
            if phi[u] + w > phi[v] + 1e-15:
                phi[v] = phi[u] + w
                changed = True
        if not changed:
            return phi, ""
    return None, "a positive directed cycle is reachable"


def violation(field: DirectedField, phi: np.ndarray) -> float:
    """Worst breach of ``omega(u,v) <= phi(v) - phi(u)``. Zero or below is a pass."""
    worst = -np.inf
    for (u, v), w in field.weights.items():
        worst = max(worst, w - (phi[v] - phi[u]))
    return float(worst)


def slack(field: DirectedField, phi: np.ndarray) -> Edges:
    """``s(u,v) = phi(v) - phi(u) - omega(u,v)``, non-negative for ``phi`` valid."""
    return {
        (u, v): float(phi[v] - phi[u] - w) for (u, v), w in field.weights.items()
    }


# ---------------------------------------------------------------------------
# Theorem 5
# ---------------------------------------------------------------------------


def strongly_connected_components(field: DirectedField) -> list[list[int]]:
    """Kosaraju. Returned in reverse topological order, so sinks come first."""
    n = field.n_vertices
    adj: dict[int, list[int]] = {u: [] for u in range(n)}
    rev: dict[int, list[int]] = {u: [] for u in range(n)}
    for u, v in field.weights:
        adj[u].append(v)
        rev[v].append(u)

    seen, order = set(), []

    def push(u: int) -> None:
        stack = [(u, iter(adj[u]))]
        seen.add(u)
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                order.append(node)
                stack.pop()
            elif nxt not in seen:
                seen.add(nxt)
                stack.append((nxt, iter(adj[nxt])))

    for u in range(n):
        if u not in seen:
            push(u)

    assigned, comps = set(), []
    for u in reversed(order):
        if u in assigned:
            continue
        comp, stack = [], [u]
        assigned.add(u)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in rev[x]:
                if y not in assigned:
                    assigned.add(y)
                    stack.append(y)
        comps.append(sorted(comp))
    return comps[::-1]


def sink_component(field: DirectedField) -> list[int] | None:
    """A strongly connected component with no directed edge leaving it.

    ``None`` when the graph is strongly connected, which is the case Theorem 5
    calls bounded. Returns the whole vertex set only if that set is a single
    component, in which case the caller is told ``None`` instead.
    """
    comps = strongly_connected_components(field)
    if len(comps) <= 1:
        return None
    for comp in comps:
        inside = set(comp)
        if not any(u in inside and v not in inside for (u, v) in field.weights):
            return comp
    return None


def longest_walk(field: DirectedField, source: int) -> np.ndarray:
    """Max ``omega``-sum of a directed walk from ``source``; ``-inf`` if unreachable.

    Finite exactly when no positive directed cycle is reachable, which Theorem 4
    already requires. Distinct from ``sub_potential`` in initialisation, and the
    distinction is the whole point: that one starts every vertex at zero, which
    is the super-source construction, and this one starts every vertex except the
    source at ``-inf``, which pins the basepoint.
    """
    n = field.n_vertices
    phi = np.full(n, -np.inf)
    phi[source] = 0.0
    items = list(field.weights.items())
    for _ in range(n):
        changed = False
        for (u, v), w in items:
            if np.isfinite(phi[u]) and phi[u] + w > phi[v] + 1e-15:
                phi[v] = phi[u] + w
                changed = True
        if not changed:
            break
    return phi


def potential_interval(field: DirectedField, u: int, v: int) -> tuple[float, float]:
    """The interval every sub-potential's ``phi(v) - phi(u)`` must lie in.

    Lower bound: the best directed walk ``u -> v``. Upper bound: minus the best
    directed walk ``v -> u``. Either is infinite when the corresponding direction
    is unreachable, and both are finite exactly on a strongly connected graph,
    which is Theorem 5.
    """
    lo = float(longest_walk(field, u)[v])
    back = float(longest_walk(field, v)[u])
    hi = float("inf") if back == -np.inf else -back
    return lo, hi


def ray_is_valid(field: DirectedField, phi: np.ndarray, subset: list[int],
                 shifts: np.ndarray) -> float:
    """Theorem 5's ray, verified rather than argued.

    Returns the worst violation over the grid of shifts of ``phi + t * 1_subset``.
    Non-positive means every shift is still a sub-potential, so the polytope is
    unbounded in that direction.
    """
    mask = np.zeros(field.n_vertices)
    mask[list(subset)] = 1.0
    return max(violation(field, phi + float(t) * mask) for t in shifts)


def shift_breaks(field: DirectedField, phi: np.ndarray, subset: list[int],
                 shift: float) -> float:
    """The counterpart check: on a strongly connected graph every proper subset
    eventually breaks. Returns the worst violation, which must go positive."""
    mask = np.zeros(field.n_vertices)
    mask[list(subset)] = 1.0
    return violation(field, phi + float(shift) * mask)


# ---------------------------------------------------------------------------
# Theorem 6
# ---------------------------------------------------------------------------


def split(field: DirectedField) -> tuple[Edges, Edges]:
    """``(w_hat, w_bar)`` on the two-way part, keyed by ordered pairs ``u < v``.

    Defined only where both directions exist. A one-way edge is not given a
    value, an imputed reverse, or a sentinel: ``docs/b4_directed_edges.md`` §5.2
    makes the absence itself the criterion for which failure is in front of you,
    so filling it in would erase the distinction the module exists to draw.
    """
    hat: Edges = {}
    bar: Edges = {}
    for u, v in field.two_way():
        f, b = field.value(u, v), field.value(v, u)
        hat[(u, v)] = 0.5 * (f - b)
        bar[(u, v)] = 0.5 * (f + b)
    return hat, bar


def directed_square(field: DirectedField, a: int, b: int, i: int, j: int,
                    n_positions: int) -> tuple[float, float]:
    """``(S, S')`` for classes ``a, b`` on position edge ``(i, j)``.

    Vertices are ``product_graph.vertex(a, i, n)``: agent index varies slowest.
    The agent legs are **looked up in the field**, not written in as zeros. They
    are zero in the fields this project builds, but hard-coding that here would
    make the function unable to report a violation of the assumption it depends
    on, and ``docs/b1_theorem.md`` §8 is entirely about when that assumption
    fails. A missing agent leg raises rather than defaulting.
    """

    def vx(cls: int, pos: int) -> int:
        return cls * n_positions + pos

    s = (
        field.value(vx(a, i), vx(a, j))
        + field.value(vx(a, j), vx(b, j))
        + field.value(vx(b, j), vx(b, i))
        + field.value(vx(b, i), vx(a, i))
    )
    s_rev = (
        field.value(vx(b, i), vx(b, j))
        + field.value(vx(b, j), vx(a, j))
        + field.value(vx(a, j), vx(a, i))
        + field.value(vx(a, i), vx(b, i))
    )
    return float(s), float(s_rev)
