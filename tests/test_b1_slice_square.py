"""Checks for the slice summand: it must fire, and it must separate.

Backs section 11.1 of ``docs/b1_theorem.md``. Every other field in this
repository makes slice cycles vanish by construction, so without these the split
of Theorem 2 is exercised on one summand only.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.product_graph import (
    cochain_from_field,
    per_agent_exact_field,
    shared_field,
    slice_cycles,
    spanning_tree_cycles,
    squares,
)


def ring(n: int) -> np.ndarray:
    """A cycle graph, so ``b1(G) = 1`` and slice cycles exist at all."""
    adj = np.zeros((n, n), dtype=int)
    for i in range(n):
        adj[i, (i + 1) % n] = adj[(i + 1) % n, i] = 1
    return adj


def antisymmetric(n: int, rng: np.random.Generator) -> np.ndarray:
    upper = np.triu(rng.integers(-6, 7, size=(n, n)).astype(np.float64), 1)
    return upper - upper.T


def test_shared_field_rejects_a_field_that_is_not_antisymmetric():
    with pytest.raises(ValueError, match="antisymmetric"):
        shared_field(np.array([[0.0, 1.0], [1.0, 0.0]]), 2)


def test_shared_field_gives_every_class_the_same_terms():
    rng = np.random.default_rng(3)
    w = antisymmetric(5, rng)
    field = shared_field(w, 4)
    assert field.shape == (4, 5, 5)
    for a in range(4):
        assert np.array_equal(field[a], w)


def test_slice_cycles_are_one_basis_per_class():
    adj = ring(6)
    cycles = slice_cycles(adj, 3)
    assert len(cycles) == 3 * len(spanning_tree_cycles(adj))
    # Each lift stays inside its own slice: vertex index is a*n + i.
    for index, cycle in enumerate(cycles):
        expected = index // len(spanning_tree_cycles(adj))
        assert {v // 6 for v in cycle} == {expected}


@pytest.mark.parametrize(("n", "m"), [(4, 2), (5, 3), (6, 4)])
def test_a_shared_non_exact_field_fires_slices_and_silences_squares(n, m):
    rng = np.random.default_rng(n * 10 + m)
    adj = ring(n)
    omega = cochain_from_field(adj, shared_field(antisymmetric(n, rng), m), m)

    slice_sums = [omega.sum_over(c) for c in slice_cycles(adj, m)]
    square_sums = [omega.sum_over(s) for s in squares(adj, m)]

    assert max(abs(s) for s in slice_sums) > 0.0
    # Exactly zero, not small: a square sum is w_a(i,j) - w_b(i,j) and the two
    # legs are the same number, so this is subtraction rather than cancellation.
    assert square_sums and all(s == 0.0 for s in square_sums)


@pytest.mark.parametrize(("n", "m"), [(4, 2), (5, 3), (6, 4)])
def test_each_summand_survives_a_mixture_bitwise(n, m):
    rng = np.random.default_rng(n * 100 + m)
    adj = ring(n)
    w = antisymmetric(n, rng)
    phis = rng.integers(-6, 7, size=(m, n)).astype(np.float64)

    pure_slice = shared_field(w, m)
    pure_square = per_agent_exact_field(phis)
    omega_slice = cochain_from_field(adj, pure_slice, m)
    omega_square = cochain_from_field(adj, pure_square, m)
    omega_mix = cochain_from_field(adj, pure_slice + pure_square, m)

    def sums(omega, walks):
        return np.array([omega.sum_over(x) for x in walks])

    got_slice = sums(omega_mix, slice_cycles(adj, m))
    want_slice = sums(omega_slice, slice_cycles(adj, m))
    got_square = sums(omega_mix, squares(adj, m))
    want_square = sums(omega_square, squares(adj, m))

    assert np.abs(want_slice).max() > 0.0
    assert np.abs(want_square).max() > 0.0
    # Integer fields, so float64 arithmetic is exact along every walk and
    # "identical" is a claim rather than a tolerance in disguise.
    assert got_slice.tobytes() == want_slice.tobytes()
    assert got_square.tobytes() == want_square.tobytes()


def test_a_pure_square_field_leaves_slice_cycles_at_zero():
    """The other half, restated here so the pair reads as a pair."""
    rng = np.random.default_rng(21)
    adj = ring(5)
    phis = rng.integers(-6, 7, size=(3, 5)).astype(np.float64)
    omega = cochain_from_field(adj, per_agent_exact_field(phis), 3)
    slice_sums = [omega.sum_over(c) for c in slice_cycles(adj, 3)]
    assert all(s == 0.0 for s in slice_sums)
    assert max(abs(omega.sum_over(s)) for s in squares(adj, 3)) > 0.0
