"""Checks for ``pool_width``: the streaming split must equal the array one."""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.effective_price import variance_decomposition
from monetary_topology.pool_width import (
    DTI_BUCKETS,
    BoundFold,
    BucketAccumulator,
    MomentAccumulator,
    SplitFold,
    dti_bucket,
)


def test_buckets_are_ordered_and_contiguous_where_they_should_be():
    lowers = [lo for _, lo, _ in DTI_BUCKETS]
    assert lowers == sorted(lowers)
    # The published vocabulary tiles [0, inf) with no hole: every upper edge is
    # the next lower edge. A hole would silently inflate a gap and the bound
    # would stop being a bound on the reported data.
    for (_, _, hi), (_, lo_next, _) in zip(DTI_BUCKETS, DTI_BUCKETS[1:], strict=False):
        assert hi == lo_next
    assert DTI_BUCKETS[-1][2] is None


def test_dti_bucket_maps_the_published_vocabulary():
    assert dti_bucket("<20%") == 0
    assert dti_bucket("20%-<30%") == 1
    assert dti_bucket("30%-<36%") == 2
    assert dti_bucket("36") == 3
    assert dti_bucket("49") == 16
    assert dti_bucket("50%-60%") == 17
    assert dti_bucket(">60%") == 18
    # No ratio reported is not a small ratio.
    assert dti_bucket("NA") == -1
    assert dti_bucket("Exempt") == -1
    assert dti_bucket("") == -1


@pytest.mark.parametrize("min_size", [0, 2, 5])
def test_streaming_split_equals_array_split(min_size):
    rng = np.random.default_rng(11)
    cells = rng.integers(0, 40, size=4000)
    values = rng.normal(0.0, 1.0, size=4000) + cells * 0.05

    acc = MomentAccumulator()
    for c, v in zip(cells, values, strict=True):
        acc.add(int(c), float(v))

    got = acc.split(min_size=min_size)
    want = variance_decomposition(values, cells, min_size=min_size)

    assert got.n_loans == want.n_loans
    assert got.n_cells == want.n_cells
    assert got.between == pytest.approx(want.between, rel=0, abs=1e-9)
    assert got.within == pytest.approx(want.within, rel=0, abs=1e-9)
    assert got.within_share == pytest.approx(want.within_share, rel=0, abs=1e-9)


def test_constant_cell_contributes_no_within_variance():
    acc = MomentAccumulator()
    for _ in range(50):
        acc.add("flat", 3.25)
    assert acc.split().within == pytest.approx(0.0, abs=1e-12)


def test_bucket_bound_is_zero_when_every_borrower_shares_a_bucket():
    acc = BucketAccumulator()
    for _ in range(30):
        acc.add("one", dti_bucket("42"))
    bound, cells, loans = acc.within_cell_bound(min_size=5)
    assert (cells, loans) == (1, 30)
    assert bound == pytest.approx(0.0, abs=1e-12)


def test_bucket_bound_is_positive_and_conservative_across_a_real_gap():
    # Half the cell at <20%, half above 60%. The reported gap is 60 - 20 = 40,
    # so the bound is 0.5 * 2 * 0.5 * 0.5 * 40**2 = 400, and the true variance of
    # any configuration consistent with those shares is at least that.
    acc = BucketAccumulator()
    for _ in range(20):
        acc.add("split", dti_bucket("<20%"))
        acc.add("split", dti_bucket(">60%"))
    bound, _, _ = acc.within_cell_bound(min_size=5)
    assert bound == pytest.approx(400.0, rel=1e-12)


@pytest.mark.parametrize("min_size", [0, 5, 20])
def test_fold_over_chunks_equals_one_pass(min_size):
    """Cells never straddle a chunk, which is the property the fold relies on."""
    rng = np.random.default_rng(7)
    cells = rng.integers(0, 60, size=6000)
    values = rng.normal(0.0, 1.0, size=6000) + cells * 0.03

    # Chunk by cell, the way state-year files chunk by tract-year.
    fold = SplitFold()
    for lo in range(0, 60, 7):
        block = (cells >= lo) & (cells < lo + 7)
        acc = MomentAccumulator()
        for c, v in zip(cells[block], values[block], strict=True):
            acc.add(int(c), float(v))
        fold.absorb(acc, min_size)

    got = fold.split()
    want = variance_decomposition(values, cells, min_size=min_size)
    assert (got.n_loans, got.n_cells) == (want.n_loans, want.n_cells)
    assert got.between == pytest.approx(want.between, rel=0, abs=1e-9)
    assert got.within == pytest.approx(want.within, rel=0, abs=1e-9)


def test_bound_fold_is_the_loan_weighted_mean_of_its_parts():
    fold = BoundFold()
    for _ in range(3):
        acc = BucketAccumulator()
        for _ in range(20):
            acc.add("a", dti_bucket("<20%"))
            acc.add("a", dti_bucket(">60%"))
        fold.absorb(acc, 5)
    assert fold.n == 120
    assert fold.bound == pytest.approx(400.0, rel=1e-12)


def test_adjacent_buckets_contribute_nothing():
    # 30%-<36% against 36: the edges touch, so two observations either side can
    # be arbitrarily close and the bound must not claim otherwise.
    acc = BucketAccumulator()
    for _ in range(20):
        acc.add("adj", dti_bucket("30%-<36%"))
        acc.add("adj", dti_bucket("36"))
    bound, _, _ = acc.within_cell_bound(min_size=5)
    assert bound == pytest.approx(0.0, abs=1e-12)
