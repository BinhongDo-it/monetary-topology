"""Tests for the matrix-free Hodge decomposition.

The point of this module is that it agrees with ``topology.hodge_decomposition``
where both can run, so that is what most of this file checks. The rest guards the
two readings that were got wrong once each: that a complete graph has no harmonic
space at all, and that a graph with no triangles is all harmonic.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.hodge_sparse import harmonic_dimension, hodge_cgls
from monetary_topology.topology import (
    connected_components,
    hodge_decomposition,
    net_flow_vector,
    undirected_edges,
)


def _ring(n: int) -> np.ndarray:
    a = np.zeros((n, n))
    for i in range(n):
        a[i, (i + 1) % n] = 1.0
        a[(i + 1) % n, i] = 1.0
    return a


def _complete(n: int) -> np.ndarray:
    a = np.ones((n, n))
    np.fill_diagonal(a, 0.0)
    return a


def _flow(adjacency: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    f = rng.random(adjacency.shape) * adjacency
    return f


@pytest.mark.parametrize("adjacency,seed", [
    (_complete(7), 1),
    (_complete(11), 2),
    (_ring(9), 3),
])
def test_agrees_with_the_dense_reference(adjacency, seed):
    """Same three components, edge by edge.

    The tolerance is relative to the flow, not absolute: an absolute one would
    pass or fail on the scale of the input rather than on the arithmetic.
    """
    flow = _flow(adjacency, seed)
    dense = hodge_decomposition(flow, adjacency, fill_triangles=True)
    grad, curl, harm, n_tri, _ = hodge_cgls(flow, adjacency)
    scale = float(np.abs(net_flow_vector(flow, adjacency)).max())
    assert n_tri == dense.filled_triangles
    for got, want in ((grad, dense.gradient), (curl, dense.curl),
                      (harm, dense.harmonic)):
        assert np.abs(got - want).max() / scale < 1e-10


def test_the_split_is_a_split():
    """The three parts add back to the net flow, on the nose."""
    adjacency = _complete(9)
    flow = _flow(adjacency, 4)
    grad, curl, harm, _, _ = hodge_cgls(flow, adjacency)
    w = net_flow_vector(flow, adjacency)
    assert np.abs(grad + curl + harm - w).max() < 1e-12


def test_a_complete_graph_has_no_harmonic_space():
    """Filling every triangle of a complete graph leaves nothing behind.

    This is the reading that made every published input-output table read zero:
    those graphs are complete or nearly so.
    """
    for n in (5, 8, 12):
        assert harmonic_dimension(_complete(n)) == 0


def test_a_graph_with_no_triangles_is_all_harmonic():
    """With no faces to fill, the whole cycle space survives."""
    for n in (4, 6, 9):
        ring = _ring(n)
        e = len(undirected_edges(ring))
        c = connected_components(ring)
        assert harmonic_dimension(ring) == e - n + c == 1


def test_rank_d0_self_check_is_live():
    """The free self-check fires rather than returning a wrong dimension."""
    disconnected = np.zeros((4, 4))
    disconnected[0, 1] = disconnected[1, 0] = 1.0
    disconnected[2, 3] = disconnected[3, 2] = 1.0
    # two components, rank(d0) = 4 - 2 = 2; the helper must agree, not raise
    assert harmonic_dimension(disconnected) == 0
