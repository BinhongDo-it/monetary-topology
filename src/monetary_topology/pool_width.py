"""Pool width at fixed position, from the borrower fields HMDA does publish.

Pre-registered in ``docs/b2_placebo_pool_width.md``. This module supports the
validation of the one premise stage B2's graded placebo asserts rather than
measures: that the VA borrower pool is comparable in width to the conventional
pool and wider than the FHA pool.

Why this exists at all
----------------------
``docs/b2_measurement.md`` section 8 argues the premise from programme rule:
VA eligibility is service-based rather than credit-based, so the pool is wide
while the price grid is flat. That is an institutional argument and it was never
measured. If it is false, the pool-width account reclaims the conventional-VA
gap and the placebo's identifying power goes to zero.

Why not credit score
--------------------
The public HMDA loan-level file redacts credit score everywhere, so the premise
cannot be tested on the variable it is stated in. FHFA's NMDB aggregates publish
credit-score bands but their ``MARKET`` dimension has no VA-only or FHA-only
value: appendix A of the NMDB data dictionary defines
``Government / Non-Conventional`` as FHA **plus** VA **plus** USDA RHS pooled,
which merges precisely the two arms the comparison needs kept apart. So NMDB
cannot answer this and the fields already retrieved can, on the same loans.

Streaming rather than in-memory
-------------------------------
A cell is keyed on year and census tract, and a tract lies inside one state, so
every cell is contained in a single state-year file. Per-cell sufficient
statistics can therefore be accumulated file by file and the full-sample arrays
never have to exist. That is what lets this run on a machine that cannot hold
twenty-eight million rows of Python objects, and it is why this module works on
``(count, sum, sum of squares)`` rather than on arrays.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .binned_dispersion import variance_lower_bound
from .effective_price import VarianceSplit

# ---------------------------------------------------------------------------
# Debt-to-income, as the public file actually reports it
# ---------------------------------------------------------------------------

#: HMDA's public disclosure rule reports debt-to-income exactly on `[36, 50)` and
#: as bands elsewhere, so the column is a mixture of point values and intervals.
#: Both are intervals here, which is what makes one bound cover the whole column.
#:
#: The integer values are widened to `[v, v+1)` rather than treated as the point
#: `[v, v]`. A filer reports a rounded percentage, so the true ratio lies inside
#: a unit interval, and widening a bucket can only shrink the gaps between
#: buckets and therefore only lower the bound. That is the conservative
#: direction, which is the whole reason for using a bound.
#:
#: The top bucket is open above, carried through as ``None`` exactly as in
#: ``binned_dispersion``.
DTI_BUCKETS: tuple[tuple[str, float, float | None], ...] = (
    ("<20%", 0.0, 20.0),
    ("20%-<30%", 20.0, 30.0),
    ("30%-<36%", 30.0, 36.0),
    *tuple((str(v), float(v), float(v + 1)) for v in range(36, 50)),
    ("50%-60%", 50.0, 60.0),
    (">60%", 60.0, None),
)

#: Label to index, built once. ``NA`` and ``Exempt`` are absent on purpose: a row
#: carrying either is not a small value, it is no value, and treating it as one
#: would put a fabricated observation into a dispersion measure.
DTI_INDEX: dict[str, int] = {label: i for i, (label, _, _) in enumerate(DTI_BUCKETS)}


def dti_bucket(value: str) -> int:
    """Index into ``DTI_BUCKETS``, or ``-1`` when the row carries no ratio.

    Unrecognised strings return ``-1`` rather than raising, and the caller counts
    them. A column whose vocabulary drifts should show up as a rising count of
    unusable rows in the record, not as a crash halfway through a four-hour pass
    and not as a silent reclassification.
    """
    return DTI_INDEX.get(value.strip(), -1)


# ---------------------------------------------------------------------------
# Per-cell sufficient statistics
# ---------------------------------------------------------------------------


@dataclass
class MomentAccumulator:
    """Per-cell count, sum and sum of squares for one continuous variable.

    Keyed on whatever hashable cell identifier the caller supplies. Nothing is
    ever removed from the mapping; the minimum-size restriction is applied when
    the split is computed, so the same accumulation supports every threshold.
    """

    count: dict[object, int] = field(default_factory=dict)
    total: dict[object, float] = field(default_factory=dict)
    total_sq: dict[object, float] = field(default_factory=dict)
    skipped: int = 0

    def add(self, cell: object, value: float) -> None:
        self.count[cell] = self.count.get(cell, 0) + 1
        self.total[cell] = self.total.get(cell, 0.0) + value
        self.total_sq[cell] = self.total_sq.get(cell, 0.0) + value * value

    @property
    def n(self) -> int:
        return sum(self.count.values())

    def arrays(self, min_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """``(counts, sums, sums of squares)`` over cells of at least ``min_size``."""
        keys = [k for k, c in self.count.items() if c >= min_size]
        keys.sort(key=repr)  # deterministic, so a rendered result is reproducible
        counts = np.array([self.count[k] for k in keys], dtype=np.float64)
        sums = np.array([self.total[k] for k in keys], dtype=np.float64)
        sums_sq = np.array([self.total_sq[k] for k in keys], dtype=np.float64)
        return counts, sums, sums_sq

    def split(self, min_size: int = 0) -> VarianceSplit:
        """Between and within components, from the sufficient statistics alone.

        Identical in value to ``effective_price.variance_decomposition`` on the
        same rows. That equivalence is checked in the test suite rather than
        asserted, because a second implementation of a decomposition is exactly
        the kind of thing that drifts.
        """
        counts, sums, sums_sq = self.arrays(min_size)
        if counts.size == 0 or counts.sum() == 0:
            return VarianceSplit(0.0, 0.0, 0, 0)

        n = float(counts.sum())
        means = sums / counts
        # Clipped for the same reason as in ``variance_decomposition``: a
        # constant cell can come back at -1e-17 through cancellation.
        variances = np.maximum(sums_sq / counts - means * means, 0.0)
        weights = counts / n
        grand = float(sums.sum() / n)
        between = float(np.sum(weights * (means - grand) ** 2))
        within = float(np.sum(weights * variances))
        return VarianceSplit(between, within, int(counts.size), int(n))


@dataclass
class SplitFold:
    """Running totals that let per-file cells be discarded as soon as they close.

    A cell is keyed on year and census tract, so every cell closes at the end of
    the state-year file it lives in. Once closed it contributes four numbers and
    nothing else is ever needed from it, which is what keeps the pass over
    twenty-eight million rows independent of how many cells there are.

    The identity used is the law of total variance rewritten so both components
    come out of running sums::

        between = Σ n_c·mean_c² / N  −  (Σ n_c·mean_c / N)²
        within  = Σ n_c·var_c  / N

    which is algebra on the definition and not an approximation.
    """

    n: int = 0
    sum_mean: float = 0.0  # Σ n_c · mean_c
    sum_mean_sq: float = 0.0  # Σ n_c · mean_c²
    sum_var: float = 0.0  # Σ n_c · var_c
    n_cells: int = 0

    def absorb(self, acc: MomentAccumulator, min_size: int) -> None:
        counts, sums, sums_sq = acc.arrays(min_size)
        if counts.size == 0:
            return
        means = sums / counts
        variances = np.maximum(sums_sq / counts - means * means, 0.0)
        self.n += int(counts.sum())
        self.sum_mean += float(np.sum(counts * means))
        self.sum_mean_sq += float(np.sum(counts * means * means))
        self.sum_var += float(np.sum(counts * variances))
        self.n_cells += int(counts.size)

    def split(self) -> VarianceSplit:
        if self.n == 0:
            return VarianceSplit(0.0, 0.0, 0, 0)
        grand = self.sum_mean / self.n
        between = max(self.sum_mean_sq / self.n - grand * grand, 0.0)
        within = self.sum_var / self.n
        return VarianceSplit(between, within, self.n_cells, self.n)


@dataclass
class BoundFold:
    """The same fold for the binned bound, which needs no second moment."""

    n: int = 0
    weighted: float = 0.0  # Σ n_c · bound_c
    n_cells: int = 0

    def absorb(self, acc: BucketAccumulator, min_size: int) -> None:
        bound, cells, loans = acc.within_cell_bound(min_size)
        if loans == 0:
            return
        self.n += loans
        self.weighted += bound * loans
        self.n_cells += cells

    @property
    def bound(self) -> float:
        return self.weighted / self.n if self.n else 0.0


@dataclass
class BucketAccumulator:
    """Per-cell counts across the ``DTI_BUCKETS``.

    Kept separate from ``MomentAccumulator`` because a binned column admits a
    bound and not a variance, and collapsing the two would invite someone to
    read the bound as a point estimate later.
    """

    counts: dict[object, np.ndarray] = field(default_factory=dict)
    n_buckets: int = len(DTI_BUCKETS)
    skipped: int = 0

    def add(self, cell: object, index: int) -> None:
        row = self.counts.get(cell)
        if row is None:
            row = np.zeros(self.n_buckets, dtype=np.int64)
            self.counts[cell] = row
        row[index] += 1

    @property
    def n(self) -> int:
        return int(sum(int(r.sum()) for r in self.counts.values()))

    def within_cell_bound(self, min_size: int = 0) -> tuple[float, int, int]:
        """Loan-weighted mean of the per-cell variance lower bound.

        Returns ``(bound, cells used, loans in those cells)``. The bound is the
        same quadratic form as loop B's, applied per cell instead of per quarter,
        so a cell whose borrowers all sit in one bucket contributes zero and the
        aggregate can only understate the true within-cell dispersion.
        """
        keys = [k for k, r in self.counts.items() if int(r.sum()) >= min_size]
        keys.sort(key=repr)
        if not keys:
            return 0.0, 0, 0
        table = np.vstack([self.counts[k] for k in keys]).astype(np.float64)
        sizes = table.sum(axis=1)
        # ``variance_lower_bound`` normalises each row itself, so raw counts are
        # as good as percentages here and avoid a rounding step.
        bounds = variance_lower_bound(table, DTI_BUCKETS)
        weights = sizes / sizes.sum()
        return float(np.sum(weights * bounds)), len(keys), int(sizes.sum())
