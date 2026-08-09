"""B2 loop A: dispersion of financing terms at fixed position and date.

What is computed, and why it is the right statistic
---------------------------------------------------
The field is the two-index effective cost `P(a, g)`: the terms on which agent
class `a` can hold position `g`. A single price vector is the special case
`P(a, g) = p(g)`, which asserts that terms do not depend on who is transacting.

Fix the position and the date. Same census tract, same quarter, same lien
position, same loan purpose, same occupancy type, same dwelling category. If the
field were a gradient of a scalar on positions, every applicant in that cell would
face the same terms and the **within-cell dispersion would be exactly zero**.

So the headline is a variance decomposition:

```
Var(rate spread)  =  between-cell  +  within-cell
                     ^^^^^^^^^^^^     ^^^^^^^^^^^
                     what a position   what no position
                     index explains    index can explain
```

and the reported scalar is the **within share**. A gradient field gives zero. The
within share is the fraction of observed terms that cannot be reproduced by any
scalar on positions, which is the non-integrable part expressed in the units the
data actually come in.

No Hodge decomposition is needed for this. The decomposition is over a partition
rather than a graph, and reaching for the heavier machinery would obscure that the
claim reduces to something this simple.

What cannot contaminate this
----------------------------
Property tax rates, state income tax and local price episodes are constant within a
tract-year, so the cell absorbs them entirely and they cannot enter the within
term. They do enter through composition, since a shift in who buys in a tract moves
the within-cell spread, and composition is the object rather than a nuisance.

The estimate is a lower bound. HMDA records financed purchases only, so all-cash
buyers, who face no financing term at all, are absent. They are the favourable
extreme of the distribution being measured, and they are most absent in the markets
where the pattern is strongest, so the censoring runs against the claim.

What this cannot do
-------------------
The public HMDA file redacts credit score, so this establishes that dispersion
exists at fixed position and date without attributing it. Non-integrability needs
a non-zero loop sum; it does not need the loop sum to be explained. Attribution is
a separate and weaker claim, made against FHFA's credit-score-banded aggregates.

Rate spread is the loan's APR minus the average prime offer rate for a comparable
transaction at the date the rate was set. Because it is already stated against a
common benchmark, differences within a cell are directly pairwise loop sums and
need no further normalisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: Columns that jointly define a position and a date. Two loans agreeing on all
#: of these are, for the purpose of this measurement, the same transition
#: undertaken by different agents. Everything here is a property of the loan or
#: the property, never of the borrower.
CELL_KEYS: tuple[str, ...] = (
    "activity_year",
    "census_tract",
    "occupancy_type",
    "lien_status",
    "loan_purpose",
    "derived_loan_product_type",
    "derived_dwelling_category",
)

#: Minimum loans in a cell before its dispersion is used. Small cells produce
#: unstable spreads and, more importantly, a cell of one has zero dispersion by
#: construction, which would bias the answer toward integrability.
MIN_CELL_SIZE = 20

#: Values outside this band are not interest-rate differences and are excluded.
#:
#: This bound was added after the first result was read, so it is recorded here in
#: full rather than presented as if it had always been there. The changelog entry
#: is section 10 of ``docs/b2_measurement.md``.
#:
#: What went wrong. The first run reported a within share of 0.975000 at three
#: different subsamples, agreeing to six decimals. That is 39/40, and it was
#: literally that fraction. A single reported spread of -9999997 sat in a cell
#: holding forty loans. An isolated value `M` in a cell of size `k` contributes
#: `M^2(k-1)/(nk)` to the within term and `M^2/(nk)` to the between term, so the
#: share it forces is `(k-1)/k` with `M` cancelling out entirely. The arithmetic
#: closed to six significant figures: `M^2/n` predicted a total variance of
#: 6,181,523.5 against 6,181,526.7 observed, the residual 3.1 being the whole
#: contribution of the twenty million real loans.
#:
#: What the bad values are. 115 rows out of 20,071,900 lie outside +-50. They are
#: filer placeholders, not a parsing fault: one filer writes 1111 into rate spread,
#: interest rate and loan term together; others write 99.99, 100.0 or 123.0 as a
#: ceiling sentinel; a few report a plausible loan with a single impossible spread
#: such as -968 alongside an interest rate of 3.49 and a term of 180 months.
#:
#: Why the band can be argued before looking at the data. Rate spread is the loan's
#: APR minus the average prime offer rate for a comparable transaction. Both are
#: annual percentage rates on a first-lien purchase mortgage. APOR has not exceeded
#: nine points in the series' history, so a spread below -20 implies a negative
#: APR, and a spread above +20 implies an APR more than twenty points over prime,
#: which is above every state usury ceiling for this product. Nothing in that
#: argument refers to the result.
#:
#: Why the exact number does not matter. ``bound_sensitivity`` recomputes the
#: decomposition across the whole sweep below, and ``rank_decomposition`` computes a
#: bound-free analogue on every row including the 115. If the reported figure moved
#: with the bound, the bound would be doing the work and the pre-registered
#: falsification ``bound_choice_drives_result`` fires.
SPREAD_BOUND = 20.0

#: Bounds the result is required to be insensitive to.
BOUND_SWEEP: tuple[float, ...] = (10.0, 15.0, 20.0, 25.0, 30.0, 50.0)


@dataclass(frozen=True)
class VarianceSplit:
    """Between and within components of a partitioned variance."""

    between: float
    within: float
    n_cells: int
    n_loans: int

    @property
    def total(self) -> float:
        return self.between + self.within

    @property
    def within_share(self) -> float:
        """The fraction no scalar on positions can account for.

        Zero if and only if the field is a gradient on the cell partition, which
        is the null this measurement is against.
        """
        return self.within / self.total if self.total > 0 else 0.0


def as_codes(cell_ids: np.ndarray) -> tuple[np.ndarray, int]:
    """Factorise cell identifiers to contiguous integer codes.

    Everything downstream works on codes rather than on the identifiers
    themselves, which is what makes the aggregations vectorisable.
    """
    _, codes = np.unique(np.asarray(cell_ids), return_inverse=True)
    return codes.astype(np.int64), int(codes.max()) + 1 if codes.size else 0


def variance_decomposition(
    values: np.ndarray, cell_ids: np.ndarray, *, min_size: int = 0
) -> VarianceSplit:
    """Split the variance of ``values`` into between-cell and within-cell parts.

    Uses the exact law of total variance, so the two components sum to the total
    up to floating point and no residual is swept anywhere.

    Vectorised over cells. The obvious implementation loops over cells and masks
    the full array once per cell, which is quadratic and does not finish on a
    twenty-million-row sample. This one is a pair of ``bincount`` passes and is
    linear.

    ``min_size`` restricts the computation to cells holding at least that many
    observations, and it matters more than it looks.

    A cell of one has zero within-cell variance by construction, and its entire
    deviation is booked to the between term. Sparse cells therefore push the
    within share **down**, toward the integrable null. Computing over all cells
    gives a conservative figure; restricting to well-populated cells gives a
    cleaner one. Both are reported, and the unrestricted figure is the one to
    quote when a conservative number is wanted.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return VarianceSplit(0.0, 0.0, 0, 0)

    codes, n_cells = as_codes(cell_ids)

    if min_size > 1:
        counts_all = np.bincount(codes, minlength=n_cells)
        keep_rows = counts_all[codes] >= min_size
        if not keep_rows.any():
            return VarianceSplit(0.0, 0.0, 0, 0)
        values = values[keep_rows]
        codes, n_cells = as_codes(codes[keep_rows])

    n = values.size

    counts = np.bincount(codes, minlength=n_cells).astype(np.float64)
    sums = np.bincount(codes, weights=values, minlength=n_cells)
    sums_sq = np.bincount(codes, weights=values * values, minlength=n_cells)

    means = sums / counts
    # Population variance per cell, from the first two moments. Clipped at zero
    # because catastrophic cancellation can make a constant cell come out at
    # -1e-17, and a negative variance would propagate into the share.
    variances = np.maximum(sums_sq / counts - means * means, 0.0)

    weights = counts / n
    grand_mean = float(values.mean())
    between = float(np.sum(weights * (means - grand_mean) ** 2))
    within = float(np.sum(weights * variances))
    return VarianceSplit(between, within, int(n_cells), int(n))


def plausible_mask(values: np.ndarray, bound: float = SPREAD_BOUND) -> np.ndarray:
    """Rows whose reported spread is an interest-rate difference at all.

    See ``SPREAD_BOUND`` for why the band is what it is and why the exact number
    is not load-bearing.
    """
    values = np.asarray(values, dtype=np.float64)
    return np.isfinite(values) & (np.abs(values) <= bound)


def average_ranks(values: np.ndarray) -> np.ndarray:
    """Tie-averaged ranks, scaled to (0, 1). One sort, no scipy dependency.

    Ties matter here rather than being a technicality. Under the integrable null
    every loan in a cell reports the same spread, those loans are tied, tied values
    receive identical ranks, and the within-cell rank variance is therefore exactly
    zero. The null is preserved by the transform, which is what makes the ranked
    decomposition a test of the same hypothesis rather than of a different one.
    """
    values = np.asarray(values, dtype=np.float64)
    n = values.size
    if n == 0:
        return np.array([], dtype=np.float64)

    order = np.argsort(values, kind="stable")
    sorted_v = values[order]

    is_new = np.empty(n, dtype=bool)
    is_new[0] = True
    np.not_equal(sorted_v[1:], sorted_v[:-1], out=is_new[1:])
    group = np.cumsum(is_new) - 1

    counts = np.bincount(group)
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    # One-based average rank of a tie group running from ``start`` for ``count``
    # positions is ``start + (count + 1) / 2``.
    avg = starts + (counts + 1) / 2.0

    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = avg[group]
    return (ranks - 0.5) / n


def rank_decomposition(
    values: np.ndarray, cell_ids: np.ndarray, *, min_size: int = 0
) -> VarianceSplit:
    """The same decomposition, on ranks, so no cleaning decision enters it.

    This is deliberately computed on the **raw sample including every implausible
    row**. A rank is bounded by the sample size no matter how large the value is,
    so the 115 placeholder rows move the statistic by at most 115/20,071,900. The
    figure therefore answers the objection that the exclusion band produced the
    result, without any appeal to the band being correct.

    The share is not comparable in level to the unranked one, because ranking
    compresses the tail that the unranked variance is mostly made of. It is
    comparable in what it rules out: a gradient field gives exactly zero here too.
    """
    return variance_decomposition(
        average_ranks(values), np.asarray(cell_ids), min_size=min_size
    )


def bound_sensitivity(
    values: np.ndarray,
    cell_ids: np.ndarray,
    *,
    bounds: tuple[float, ...] = BOUND_SWEEP,
    min_size: int = MIN_CELL_SIZE,
) -> list[dict[str, float]]:
    """Recompute the decomposition at each exclusion band.

    The point is the spread of the resulting shares, not any one of them. A result
    that survives a band of 10 and a band of 50 does not depend on the band.
    """
    values = np.asarray(values, dtype=np.float64)
    cell_ids = np.asarray(cell_ids)
    out: list[dict[str, float]] = []
    for bound in bounds:
        mask = plausible_mask(values, bound)
        split = variance_decomposition(values[mask], cell_ids[mask], min_size=min_size)
        out.append(
            {
                "bound": float(bound),
                "excluded": int(values.size - int(mask.sum())),
                "within_share": split.within_share,
                "n_cells": split.n_cells,
                "n_loans": split.n_loans,
            }
        )
    return out


@dataclass
class CellDispersion:
    """Per-cell spread statistics, reported as a distribution not a mean."""

    cell_id: np.ndarray
    n: np.ndarray
    iqr: np.ndarray
    p90_p10: np.ndarray
    std: np.ndarray
    median_spread: np.ndarray

    def summary(self) -> dict[str, float]:
        return {
            "cells": int(self.cell_id.size),
            "loans": int(self.n.sum()),
            "median_iqr": float(np.median(self.iqr)),
            "median_p90_p10": float(np.median(self.p90_p10)),
            "share_of_cells_with_iqr_above_25bp": float((self.iqr > 0.25).mean()),
            "share_of_cells_with_p90_p10_above_1pt": float((self.p90_p10 > 1.0).mean()),
        }


def cell_dispersion(
    values: np.ndarray, cell_ids: np.ndarray, *, min_size: int = MIN_CELL_SIZE
) -> CellDispersion:
    """Within-cell spread of ``values``, one row per cell above ``min_size``.

    Robust statistics are reported alongside the standard deviation because the
    rate-spread distribution has a long right tail and a mean-based summary would
    be dominated by it.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        empty_f = np.array([], dtype=float)
        return CellDispersion(
            np.array([]), np.array([], dtype=int), empty_f, empty_f, empty_f, empty_f
        )

    uniq, codes = np.unique(np.asarray(cell_ids), return_inverse=True)
    counts = np.bincount(codes, minlength=uniq.size)

    # Sort once by (cell, value). Every per-cell quantile is then a lookup into a
    # contiguous slice, so the whole pass is one sort rather than one pass per
    # cell. The loop below touches each cell's slice and nothing else.
    order = np.lexsort((values, codes))
    sorted_vals = values[order]
    starts = np.concatenate(([0], np.cumsum(counts)))

    keep = np.flatnonzero(counts >= min_size)
    ids, ns, iqrs, ranges, stds, meds = [], [], [], [], [], []
    for c in keep:
        group = sorted_vals[starts[c] : starts[c + 1]]
        q1, med, q3 = np.quantile(group, [0.25, 0.5, 0.75])
        p10, p90 = np.quantile(group, [0.10, 0.90])
        ids.append(uniq[c])
        ns.append(group.size)
        iqrs.append(q3 - q1)
        ranges.append(p90 - p10)
        stds.append(group.std(ddof=1))
        meds.append(med)

    return CellDispersion(
        cell_id=np.array(ids),
        n=np.array(ns, dtype=int),
        iqr=np.array(iqrs, dtype=float),
        p90_p10=np.array(ranges, dtype=float),
        std=np.array(stds, dtype=float),
        median_spread=np.array(meds, dtype=float),
    )


@dataclass
class LoopAResult:
    """Everything loop A reports, with the falsification checks evaluated."""

    split: VarianceSplit
    dispersion: CellDispersion
    by_occupancy: dict[str, VarianceSplit] = field(default_factory=dict)
    #: The same decomposition over cells above ``min_size`` only. Sparse cells
    #: bias the unrestricted figure toward the integrable null, so this is the
    #: cleaner estimate and the unrestricted one is the conservative bound.
    restricted: VarianceSplit | None = None
    by_occupancy_restricted: dict[str, VarianceSplit] = field(default_factory=dict)
    #: Rows dropped by the plausibility band, and the band that dropped them.
    excluded_implausible: int = 0
    spread_bound: float = SPREAD_BOUND
    #: The same decomposition at every band in ``BOUND_SWEEP``.
    bound_sweep: list[dict[str, float]] = field(default_factory=list)
    #: Ranked decomposition on the raw sample, excluding nothing at all.
    rank_split: VarianceSplit | None = None
    rank_split_restricted: VarianceSplit | None = None

    def bound_spread(self) -> float:
        """Range of the within share across the exclusion bands swept."""
        if not self.bound_sweep:
            return 0.0
        shares = [row["within_share"] for row in self.bound_sweep]
        return float(max(shares) - min(shares))

    def falsifications(self) -> dict[str, bool]:
        """Pre-registered failure conditions from `docs/b2_measurement.md`.

        ``True`` means the condition fired, meaning the claim is in trouble.
        """
        return {
            "delta_A_indistinguishable_from_zero": self.split.within_share < 0.01,
            "dispersion_negligible": float(np.median(self.dispersion.iqr)) < 0.05,
            "vanishes_within_occupancy": bool(
                self.by_occupancy
                and max(v.within_share for v in self.by_occupancy.values()) < 0.05
            ),
            # Added with the plausibility band. If moving the band from 10 to 50
            # moves the answer, then the band is the answer.
            "bound_choice_drives_result": bool(
                self.bound_sweep and self.bound_spread() > 0.05
            ),
            # The ranked statistic excludes nothing, so if it collapses while the
            # banded one does not, the exclusion is manufacturing the result.
            "vanishes_under_ranking": bool(
                self.rank_split is not None and self.rank_split.within_share < 0.01
            ),
        }


def make_cell_ids(columns: dict[str, np.ndarray]) -> np.ndarray:
    """Combine cell-defining columns into a single identifier array.

    Raises if a required key is missing, rather than silently forming coarser
    cells. A coarser cell inflates within-cell dispersion and would bias the
    answer toward the conclusion, so this failure must be loud.
    """
    missing = [k for k in CELL_KEYS if k not in columns]
    if missing:
        raise KeyError(f"missing cell-defining columns: {missing}")
    n = len(next(iter(columns.values())))

    # Factorise each column to codes and fold them together, re-factorising at
    # every step so the running code stays small. Building one long string per
    # row instead, which is the obvious way, allocates seven string arrays the
    # length of the sample and does not fit in memory at twenty million rows.
    combined: np.ndarray | None = None
    for key in CELL_KEYS:
        col = np.asarray(columns[key])
        if len(col) != n:
            raise ValueError(f"column {key} has length {len(col)}, expected {n}")
        _, codes = np.unique(col, return_inverse=True)
        codes = codes.astype(np.int64)
        if combined is None:
            combined = codes
        else:
            combined = combined * (codes.max() + 1) + codes
            _, combined = np.unique(combined, return_inverse=True)
            combined = combined.astype(np.int64)
    return combined if combined is not None else np.array([], dtype=np.int64)


def run_loop_a(
    rate_spread: np.ndarray,
    columns: dict[str, np.ndarray],
    *,
    min_size: int = MIN_CELL_SIZE,
    spread_bound: float = SPREAD_BOUND,
) -> LoopAResult:
    """Compute loop A on one prepared sample.

    ``rate_spread`` must already be filtered to originated loans with a reported
    spread. Sample selection happens in the fetch step so that the exclusions are
    recorded there rather than buried here.

    The one exclusion applied at this stage is the plausibility band, because it is
    not a sample-selection rule but a statement about which numbers are the
    quantity at all. It is argued in ``SPREAD_BOUND``, swept in ``bound_sweep``,
    and bypassed entirely by ``rank_split``, which is computed before it.
    """
    rate_spread = np.asarray(rate_spread, dtype=np.float64)
    cell_ids_all = make_cell_ids(columns)

    # Computed first, on everything, so that no cleaning decision precedes it.
    rank_split = rank_decomposition(rate_spread, cell_ids_all)
    rank_split_restricted = rank_decomposition(
        rate_spread, cell_ids_all, min_size=min_size
    )
    sweep = bound_sensitivity(rate_spread, cell_ids_all, min_size=min_size)

    keep = plausible_mask(rate_spread, spread_bound)
    excluded = int(rate_spread.size - int(keep.sum()))
    rate_spread = rate_spread[keep]
    columns = {k: np.asarray(v)[keep] for k, v in columns.items()}

    cell_ids = make_cell_ids(columns)
    split = variance_decomposition(rate_spread, cell_ids)
    restricted = variance_decomposition(rate_spread, cell_ids, min_size=min_size)
    dispersion = cell_dispersion(rate_spread, cell_ids, min_size=min_size)

    by_occupancy: dict[str, VarianceSplit] = {}
    by_occupancy_restricted: dict[str, VarianceSplit] = {}
    occ = np.asarray(columns["occupancy_type"]).astype(str)
    for level in np.unique(occ):
        mask = occ == level
        if mask.sum() < min_size:
            continue
        by_occupancy[str(level)] = variance_decomposition(
            rate_spread[mask], cell_ids[mask]
        )
        by_occupancy_restricted[str(level)] = variance_decomposition(
            rate_spread[mask], cell_ids[mask], min_size=min_size
        )

    return LoopAResult(
        split=split,
        dispersion=dispersion,
        by_occupancy=by_occupancy,
        restricted=restricted,
        by_occupancy_restricted=by_occupancy_restricted,
        excluded_implausible=excluded,
        spread_bound=float(spread_bound),
        bound_sweep=sweep,
        rank_split=rank_split,
        rank_split_restricted=rank_split_restricted,
    )
