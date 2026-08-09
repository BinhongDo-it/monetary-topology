"""A2c: cycle structure of the realized circulation graph.

What this is, and what it is not
--------------------------------
Volume II of the source framework argues that a price field on an economy is
non-integrable: there is no global potential whose gradient it is, so the local
signals cannot be aggregated into a global view. That argument is structural and
universal, and no simulation can establish it. This module does **not** attempt
to.

What it does is measure, on the graph the A2 model already produces, the object
that argument is about: **cycle structure**. Two things follow from having a
graph and a flow on it, both exactly computable, neither requiring a price.

1. The first Betti number, ``E - V + C``: the number of independent cycles. This
   is pure combinatorics on the incidence matrix.
2. The discrete Hodge decomposition of the net flow into a gradient part, a curl
   part and a harmonic part.

The distinction that makes this worth doing is the same one stage A2 rests on.
The **potential** graph is fixed: no edge is ever deleted and no transaction is
ever forbidden. The **realized** graph, the edges actually carrying claims, is
not. If its cycle rank falls while nothing is prohibited, then circulation is
losing independent loops without anything being closed.

Three things are deliberately avoided
-------------------------------------
**No invented price field.** Decomposing net claim flow is not decomposing a
price field, and calling one the other would be the substitution this project
refused at stage A0. The gradient part of a *flow* means the flow is explainable
by a scalar potential on nodes, a pressure. The gradient part of a *price field*
means an integrable price level. These are different objects that share a name.
Volume II is about the second; this module measures the first, and is an analogue
rather than an instance.

**No holes punched by hand.** Deleting edges and observing that the cycle rank
changes verifies ``E - V + C``, not economics. Holes here appear because flow
stops traversing edges, which is endogenous. The hand-punched version is kept
only as a self-check on the code and is labelled as such.

**No claim that this motivates the theorem beyond illustration.** A universal
non-existence statement is not supported by instances of it.

The one modelling choice, stated rather than buried
---------------------------------------------------
On a bare graph the Hodge decomposition has only two parts: gradient and cycle
space. Splitting the cycle space further into a curl part and a harmonic part
requires deciding which cycles are *filled in*, that is, which loops are declared
not to be holes. The standard choice, and the one used here, is to fill every
triangle: any three mutually connected nodes bound a face.

In economic terms, filling a triangle asserts that a three-way trading loop is
not a structural hole. That is a modelling decision and not a mathematical fact.
``fill_triangles=False`` reports the two-way split instead, and the experiment
runs both so a reader can see which conclusions survive the choice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Rank computations use this as the singular-value cutoff, relative to the
#: largest singular value. Structural ranks of an incidence matrix are robust,
#: so this does not sit near any decision boundary.
RANK_TOLERANCE = 1e-10


def undirected_edges(adjacency: np.ndarray) -> np.ndarray:
    """Edge list ``(i, j)`` with ``i < j`` for the underlying undirected graph.

    Cycle structure is a property of connectivity, so a pair of nodes linked in
    either or both directions contributes one edge.
    """
    linked = (adjacency > 0) | (adjacency > 0).T
    return np.argwhere(np.triu(linked, k=1))


def incidence_matrix(adjacency: np.ndarray) -> np.ndarray:
    """The ``(E, V)`` incidence operator ``d0`` of the undirected graph.

    Row ``e = (i, j)`` has ``-1`` at ``i`` and ``+1`` at ``j``, so that for a
    node potential ``p`` the product ``d0 @ p`` is the discrete gradient: the
    potential difference along each edge.
    """
    edges = undirected_edges(adjacency)
    d0 = np.zeros((len(edges), adjacency.shape[0]))
    for e, (i, j) in enumerate(edges):
        d0[e, i] = -1.0
        d0[e, j] = 1.0
    return d0


def connected_components(adjacency: np.ndarray) -> int:
    """Number of connected components of the underlying undirected graph."""
    linked = (adjacency > 0) | (adjacency > 0).T
    n = linked.shape[0]
    seen = np.zeros(n, dtype=bool)
    count = 0
    for start in range(n):
        if seen[start]:
            continue
        count += 1
        frontier = np.zeros(n, dtype=bool)
        frontier[start] = True
        seen[start] = True
        while frontier.any():
            nxt = linked[frontier].any(axis=0) & ~seen
            seen |= nxt
            frontier = nxt
    return count


def cycle_rank(adjacency: np.ndarray) -> int:
    """First Betti number ``E - V + C`` of the underlying undirected graph.

    The number of independent cycles: how many distinct closed loops circulation
    could traverse. Exact integer combinatorics, no tolerance involved.
    """
    edges = len(undirected_edges(adjacency))
    nodes = adjacency.shape[0]
    return int(edges - nodes + connected_components(adjacency))


def triangles(adjacency: np.ndarray) -> np.ndarray:
    """Index triples ``(i, j, k)``, ``i < j < k``, mutually connected.

    These are the faces filled in by the default choice. See the module
    docstring: filling a triangle asserts a three-way loop is not a hole.
    """
    linked = ((adjacency > 0) | (adjacency > 0).T).astype(bool)
    np.fill_diagonal(linked, False)
    found = []
    n = linked.shape[0]
    for i in range(n):
        nbrs_i = np.flatnonzero(linked[i])
        nbrs_i = nbrs_i[nbrs_i > i]
        for idx, j in enumerate(nbrs_i):
            for k in nbrs_i[idx + 1 :]:
                if linked[j, k]:
                    found.append((i, int(j), int(k)))
    return np.array(found, dtype=int).reshape(-1, 3)


def curl_matrix(adjacency: np.ndarray) -> np.ndarray:
    """The ``(T, E)`` operator ``d1`` taking an edge flow to its loop sums.

    Row ``t = (i, j, k)`` sums the flow around that triangle with consistent
    orientation, so ``d1 @ w`` is zero exactly when ``w`` has no net gain around
    any filled face.
    """
    edges = undirected_edges(adjacency)
    index = {(int(i), int(j)): e for e, (i, j) in enumerate(edges)}
    tris = triangles(adjacency)
    d1 = np.zeros((len(tris), len(edges)))
    for t, (i, j, k) in enumerate(tris):
        for a, b, sign in ((i, j, 1.0), (j, k, 1.0), (i, k, -1.0)):
            d1[t, index[(int(a), int(b))]] = sign
    return d1


def net_flow_vector(flow: np.ndarray, adjacency: np.ndarray) -> np.ndarray:
    """Net claim flow as a value per undirected edge, oriented ``i -> j``.

    The Hodge decomposition acts on antisymmetric edge functions, so gross
    payments in both directions are collapsed to their difference. What is being
    decomposed is therefore the net movement of claims, not the turnover.
    """
    edges = undirected_edges(adjacency)
    return np.array([flow[i, j] - flow[j, i] for i, j in edges])


@dataclass(frozen=True)
class HodgeSplit:
    """Decomposition of an edge flow into three mutually orthogonal parts."""

    gradient: np.ndarray
    curl: np.ndarray
    harmonic: np.ndarray
    filled_triangles: int

    @property
    def total(self) -> np.ndarray:
        return self.gradient + self.curl + self.harmonic

    def energies(self) -> tuple[float, float, float]:
        return (
            float(np.dot(self.gradient, self.gradient)),
            float(np.dot(self.curl, self.curl)),
            float(np.dot(self.harmonic, self.harmonic)),
        )

    def shares(self) -> tuple[float, float, float]:
        """Fractions of the flow's energy in each component.

        The gradient share is the part of net circulation a scalar node
        potential accounts for. It is the flow-side analogue of an integrable
        field, and the module docstring says why that is an analogue rather than
        the thing Volume II is about.
        """
        g, c, h = self.energies()
        total = g + c + h
        if total <= 0.0:
            return (0.0, 0.0, 0.0)
        return (g / total, c / total, h / total)


def hodge_decomposition(
    flow: np.ndarray, adjacency: np.ndarray, *, fill_triangles: bool = True
) -> HodgeSplit:
    """Split the net flow into gradient, curl and harmonic components.

    With ``fill_triangles=False`` no faces are filled, the curl component is
    empty by construction, and everything not a gradient is reported as
    harmonic. That is the honest two-way split for a bare graph; the experiment
    reports both so the effect of the choice is visible.
    """
    w = net_flow_vector(flow, adjacency)
    d0 = incidence_matrix(adjacency)

    # Gradient part: least-squares projection onto the image of d0.
    potential, *_ = np.linalg.lstsq(d0, w, rcond=None)
    grad = d0 @ potential
    residual = w - grad

    if not fill_triangles:
        return HodgeSplit(grad, np.zeros_like(w), residual, 0)

    d1 = curl_matrix(adjacency)
    if d1.size == 0:
        return HodgeSplit(grad, np.zeros_like(w), residual, 0)

    # Curl part: the component of the residual generated by loop sums around
    # filled faces, again by least squares onto the image of d1 transposed.
    coeffs, *_ = np.linalg.lstsq(d1.T, residual, rcond=None)
    curl = d1.T @ coeffs
    harmonic = residual - curl
    return HodgeSplit(grad, curl, harmonic, d1.shape[0])


def realized_adjacency(flow: np.ndarray, epsilon: float) -> np.ndarray:
    """Edges actually carrying claims this round.

    The potential graph is what the economy permits; this is what it does. No
    edge is deleted here, and nothing is forbidden: an edge is absent from the
    realized graph only because nothing traversed it.
    """
    return (flow > epsilon).astype(float)
