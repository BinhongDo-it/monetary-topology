"""A rigorous lower bound on dispersion, from binned shares alone.

Pre-registered in ``docs/b2_loop_b.md``. Used by stage B2 loop B, where FHFA
publishes the contract-rate distribution of the outstanding mortgage stock as five
bucket shares and nothing finer.

The identity this rests on
--------------------------
For independent copies `X, X'` of a distribution,

```
Var(X)  =  ½ · E[(X − X')²]
```

which is Theorem 3 of ``docs/b1_theorem.md`` stated without any graph, because the
identity is algebraic and the graph was never doing the work. If `X` falls in
bucket `b` and `X'` in bucket `c > b`, then `X' − X ≥ l_c − u_b`, so

```
Var(X)  ≥  Σ_{b < c}  p_b · p_c · d(b,c)²        d(b,c) = max(0, l_c − u_b)
```

Adjacent buckets contribute nothing: two observations either side of a shared
boundary can be arbitrarily close. Only the gaps between non-adjacent buckets
count, which is what makes this a bound rather than a guess.

Why a bound rather than a point estimate
----------------------------------------
It runs in the conservative direction. The framework wants this dispersion to be
large, so a quantity that can only understate it cannot be accused of having been
built to flatter the claim.

It needs no distributional assumption. Fitting a within-bucket shape would put
part of the answer in the assumption, and with five buckets and an open top the
assumption would carry real weight.

It is exact rather than approximate. Every configuration consistent with the
reported shares has variance at least this large, including the one that minimises
it, so there is no error term to argue about.

What it is *not*
----------------
On the mortgage stock this bound is **not** a holonomy. A below-market mortgage
cannot be transferred to another borrower, so the agent edge of ``product_graph``
is absent, the enlarged graph disconnects, and the four-cycle is not a cycle. The
bound measures how far apart the components sit, which is an `H⁰` statement.
Loop A's within share is `H¹`. Same units, same algebraic form, different object,
and section 1 of ``docs/b2_loop_b.md`` is about why that distinction has to be
stated rather than quietly enjoyed.
"""

from __future__ import annotations

import numpy as np

#: The five FHFA contract-rate buckets: (series id, lower edge, upper edge).
#: ``None`` upper means open above.
RATE_BUCKETS: tuple[tuple[str, float, float | None], ...] = (
    ("PCT_INTRATE_LT_3", 0.0, 3.0),
    ("PCT_INTRATE_3_4", 3.0, 4.0),
    ("PCT_INTRATE_4_5", 4.0, 5.0),
    ("PCT_INTRATE_5_6", 5.0, 6.0),
    ("PCT_INTRATE_GE_6", 6.0, None),
)

#: Published shares are percentages. A quarter is used only if they sum to within
#: this many percentage points of 100; anything else is dropped and reported,
#: never rescaled into shape.
SHARE_SUM_TOLERANCE = 1.0


def gap_squared_matrix(
    buckets: tuple[tuple[str, float, float | None], ...] = RATE_BUCKETS,
) -> np.ndarray:
    """`D[b, c] = d(b, c)²`, symmetric with a zero diagonal.

    The open top bucket contributes its lower edge and nothing more, which can
    only make the bound smaller. That is the right direction for a bound whose
    job is to be conservative.
    """
    lowers = np.array([lo for _, lo, _ in buckets], dtype=np.float64)
    uppers = np.array(
        [hi if hi is not None else np.inf for _, _, hi in buckets], dtype=np.float64
    )
    k = len(buckets)
    d = np.zeros((k, k), dtype=np.float64)
    for b in range(k):
        for c in range(b + 1, k):
            # Finite because a bucket that is open above is never the lower one.
            d[b, c] = d[c, b] = max(0.0, lowers[c] - uppers[b])
    return d * d


def variance_lower_bound(
    shares: np.ndarray,
    buckets: tuple[tuple[str, float, float | None], ...] = RATE_BUCKETS,
) -> np.ndarray:
    """Lower bound on the variance, one value per row of ``shares``.

    ``shares`` is `(T, K)` in **percent** and each row must sum to about 100;
    rows are normalised to fractions here so that a caller cannot silently pass
    fractions and get an answer ten thousand times too small.

    The computation is `½ · p' D p`, which is the same quadratic form as the
    mean squared pairwise difference in Theorem 3.
    """
    p = np.atleast_2d(np.asarray(shares, dtype=np.float64))
    if p.shape[1] != len(buckets):
        raise ValueError(f"expected {len(buckets)} buckets, got {p.shape[1]}")
    totals = p.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError("a row of shares sums to zero or less")
    p = p / totals

    d2 = gap_squared_matrix(buckets)
    out = 0.5 * np.einsum("tb,bc,tc->t", p, d2, p)
    # The form is positive semidefinite in exact arithmetic; clip so that a
    # rounding artefact cannot present as a negative variance downstream.
    return np.maximum(out, 0.0)


def shares_are_usable(
    shares: np.ndarray, tolerance: float = SHARE_SUM_TOLERANCE
) -> np.ndarray:
    """Rows whose bucket shares are present, finite and sum to about 100."""
    p = np.atleast_2d(np.asarray(shares, dtype=np.float64))
    finite = np.isfinite(p).all(axis=1)
    close = np.abs(p.sum(axis=1) - 100.0) <= tolerance
    return finite & close


def bucket_midpoint_mean(
    shares: np.ndarray,
    buckets: tuple[tuple[str, float, float | None], ...] = RATE_BUCKETS,
    open_top_width: float = 1.0,
) -> np.ndarray:
    """Mean implied by bucket midpoints. Diagnostic only, never a criterion.

    This one *does* need an assumption — that mass sits at bucket centres, and
    that the open top bucket has some finite width. It is reported alongside the
    published ``AVE_INTRATE`` purely as a check that the buckets and the average
    describe the same population, and nothing is concluded from it.
    """
    mids = np.array(
        [
            (lo + hi) / 2.0 if hi is not None else lo + open_top_width / 2.0
            for _, lo, hi in buckets
        ],
        dtype=np.float64,
    )
    p = np.atleast_2d(np.asarray(shares, dtype=np.float64))
    return (p @ mids) / p.sum(axis=1)
