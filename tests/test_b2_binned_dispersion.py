"""Unit tests for the binned lower bound. Registered in ``docs/b2_loop_b.md``."""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.binned_dispersion import (
    RATE_BUCKETS,
    gap_squared_matrix,
    shares_are_usable,
    variance_lower_bound,
)


def test_gap_matrix_is_symmetric_with_zero_diagonal():
    d2 = gap_squared_matrix()
    assert np.allclose(d2, d2.T)
    assert np.allclose(np.diag(d2), 0.0)


def test_adjacent_buckets_contribute_nothing():
    """Two loans either side of a boundary can be arbitrarily close."""
    d2 = gap_squared_matrix()
    for b in range(len(RATE_BUCKETS) - 1):
        assert d2[b, b + 1] == 0.0


def test_the_extreme_pair_is_nine():
    """Below 3% against at or above 6% is a gap of three points."""
    assert gap_squared_matrix()[0, -1] == 9.0


def test_null_all_mass_in_one_bucket():
    """L4, first half. A degenerate distribution has no dispersion to find."""
    for b in range(len(RATE_BUCKETS)):
        shares = np.zeros((1, len(RATE_BUCKETS)))
        shares[0, b] = 100.0
        assert variance_lower_bound(shares)[0] == pytest.approx(0.0, abs=1e-15)


def test_null_split_between_the_extremes():
    """L4, second half. Registered as exactly 0.25 * 9."""
    shares = np.array([[50.0, 0, 0, 0, 50.0]])
    assert variance_lower_bound(shares)[0] == pytest.approx(2.25, rel=1e-12)


def test_bound_is_never_negative():
    rng = np.random.default_rng(0)
    shares = rng.random((200, len(RATE_BUCKETS)))
    shares = 100.0 * shares / shares.sum(axis=1, keepdims=True)
    assert (variance_lower_bound(shares) >= 0.0).all()


def test_bound_is_below_the_true_variance_on_a_known_sample():
    """The bound must not exceed the variance of a distribution consistent with it."""
    rng = np.random.default_rng(1)
    x = np.clip(rng.normal(4.5, 1.6, 200_000), 0.0, None)
    edges = [0.0, 3.0, 4.0, 5.0, 6.0, np.inf]
    pairs = list(zip(edges[:-1], edges[1:], strict=True))
    shares = np.array([[((x >= lo) & (x < hi)).mean() * 100 for lo, hi in pairs]])
    assert variance_lower_bound(shares)[0] <= x.var() + 1e-9


def test_scale_invariance_of_the_input():
    """Shares are normalised, so passing them twice as large changes nothing."""
    a = np.array([[20.0, 30.0, 20.0, 15.0, 15.0]])
    assert variance_lower_bound(a)[0] == pytest.approx(
        variance_lower_bound(a * 2.0)[0], rel=1e-12
    )


def test_wrong_bucket_count_is_loud():
    with pytest.raises(ValueError, match="buckets"):
        variance_lower_bound(np.array([[50.0, 50.0]]))


def test_usable_rejects_rows_that_do_not_sum_to_a_hundred():
    rows = np.array([[20, 30, 20, 15, 15], [10, 10, 10, 10, 10]], dtype=float)
    assert list(shares_are_usable(rows)) == [True, False]
