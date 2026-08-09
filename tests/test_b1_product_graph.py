"""Unit tests for the enlarged graph. Proofs are in ``docs/b1_theorem.md``.

These target the pieces the experiment composes, so a failure here localises to a
function rather than to a criterion.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.product_graph import (
    betti_formula,
    box_product,
    brute_force_holonomy,
    cochain_from_field,
    complete_agent_graph,
    cycle_matrix,
    exact_field,
    per_agent_exact_field,
    potential_from_cochain,
    squares,
    undirected_pairs,
    vertex,
)
from monetary_topology.topology import cycle_rank

PATH4 = np.array(
    [[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0]], dtype=int
)  # a 4-cycle, so b1(G) = 1


def test_vertex_indexing_is_a_bijection():
    n, m = 4, 3
    seen = {vertex(a, i, n) for a in range(m) for i in range(n)}
    assert seen == set(range(m * n))


def test_box_product_edge_count():
    for m in (1, 2, 4):
        adj = box_product(PATH4, complete_agent_graph(m))
        e_g, e_h = 4, m * (m - 1) // 2
        assert len(undirected_pairs(adj)) == m * e_g + 4 * e_h


def test_cochain_is_antisymmetric_on_read():
    omega = cochain_from_field(PATH4, exact_field(np.arange(4.0), 2), 2)
    u, v = vertex(0, 0, 4), vertex(0, 1, 4)
    assert omega.value(u, v) == pytest.approx(-omega.value(v, u))


def test_cochain_rejects_an_asymmetric_field():
    bad = np.zeros((1, 4, 4))
    bad[0, 0, 1] = 1.0  # no matching -1 at [0, 1, 0]
    with pytest.raises(ValueError, match="antisymmetric"):
        cochain_from_field(PATH4, bad, 1)


def test_agent_edges_carry_zero():
    omega = cochain_from_field(PATH4, exact_field(np.arange(4.0), 3), 3)
    assert omega.value(vertex(0, 2, 4), vertex(1, 2, 4)) == 0.0


def test_shared_potential_gives_zero_squares():
    omega = cochain_from_field(
        PATH4, exact_field(np.array([0.0, 2.0, -1.0, 5.0]), 3), 3
    )
    assert max(abs(omega.sum_over(s)) for s in squares(PATH4, 3)) < 1e-12


def test_per_agent_potentials_give_nonzero_squares():
    """Every w_a exact, yet no global potential. Section 7 of the document."""
    rng = np.random.default_rng(0)
    phis = rng.normal(0, 1.0, (3, 4))
    omega = cochain_from_field(PATH4, per_agent_exact_field(phis), 3)
    assert max(abs(omega.sum_over(s)) for s in squares(PATH4, 3)) > 1e-6
    _, residual = potential_from_cochain(
        box_product(PATH4, complete_agent_graph(3)), omega
    )
    assert residual > 1e-6


def test_potential_reconstruction_is_exact_when_it_should_be():
    omega = cochain_from_field(
        PATH4, exact_field(np.array([0.0, 2.0, -1.0, 5.0]), 2), 2
    )
    psi, residual = potential_from_cochain(
        box_product(PATH4, complete_agent_graph(2)), omega
    )
    assert residual < 1e-12
    assert np.isfinite(psi).all()


@pytest.mark.parametrize("m", [1, 2, 3, 5])
def test_betti_formula_matches_direct_computation(m):
    adj = box_product(PATH4, complete_agent_graph(m))
    assert cycle_rank(adj) == betti_formula(4, 4, m, m * (m - 1) // 2)


@pytest.mark.parametrize("m", [1, 2, 3, 5])
def test_generating_set_spans_the_cycle_space(m):
    adj = box_product(PATH4, complete_agent_graph(m))
    assert int(np.linalg.matrix_rank(cycle_matrix(PATH4, m))) == cycle_rank(adj)


def test_one_agent_class_reproduces_the_one_index_case():
    """Strict generalisation: m=1 has no squares and the same Betti number."""
    assert squares(PATH4, 1) == []
    assert cycle_rank(box_product(PATH4, complete_agent_graph(1))) == cycle_rank(PATH4)


@pytest.mark.parametrize("k", [1, 2, 3, 8, 41])
def test_theorem_3_identity(k):
    rng = np.random.default_rng(k)
    x = rng.normal(0.3, 1.4, k)
    assert brute_force_holonomy(x) == pytest.approx(2.0 * x.var(), rel=1e-12, abs=1e-15)


def test_a_constant_cell_has_zero_holonomy():
    """The integrable null, stated as a test: identical terms, no obstruction."""
    assert brute_force_holonomy(np.full(37, 1.25)) == pytest.approx(0.0, abs=1e-18)
