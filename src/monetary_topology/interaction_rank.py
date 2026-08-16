"""The matrix rank of a two-way interaction, on an incomplete design.

Pre-registered in ``docs/b7_interaction_rank.md``. ``b1_theorem.md`` Corollary 4
says the interaction term `gamma` is non-zero and stage B2 measured its
magnitude; this module estimates its **shape**, which is the number of
independent directions in it.

Why not an SVD of the cell-by-class matrix
------------------------------------------
Because that matrix has holes. With nineteen classes against a minimum cell size
of twenty, a complete cell-by-class block does not exist, and restricting to one
would select cells on the diversity of their borrowers, which is a selection on
the object being measured. So the rank is taken from a **pairwise-complete class
second-moment matrix**, which needs no imputation: every entry `S(a, b)` is a
mean over the cells that hold both classes, and cells are dropped pairwise with
the count reported. That rule is ``docs/b3_cip_slice.md`` section 7's, adopted
verbatim.

The price is that `S` need not be positive semidefinite. Its negative eigenvalues
are returned with the positive ones and section 7 of the pre-registration says
what happens if a negative one clears the null.

Two specification points, fixed before any computation
------------------------------------------------------
1. **The centring is count-weighted.** An entry standing for one loan and an
   entry standing for two hundred are not equally informative, and centring them
   equally is a choice that puts the most weight where the least data is. The
   weights are the loan counts behind each cell-class mean.
2. **`S` is a plain mean over co-occurring cells**, which is the pre-registration's
   literal wording and is left literal.

Neither was in the pre-registration when it was written. Both are recorded here
and in section 3.4 of that document, and both were fixed before any HMDA row was
read, which is the only thing that makes them specification rather than tuning.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

#: Iteration controls for the alternating centring. Neither is a criterion: the
#: achieved residual is reported and a run that does not converge says so.
CENTRE_TOL = 1e-12
CENTRE_MAX_ITER = 500


#: Default worker count for the null. Half the logical cores, capped, because a
#: draw allocates about four hundred megabytes transiently and the operations are
#: memory-bound well before they are core-bound.
def default_jobs() -> int:
    return max(1, min(8, (os.cpu_count() or 2) // 2))


def _null_seeds(rng: np.random.Generator, draws: int) -> np.ndarray:
    """One seed per draw, drawn sequentially from the parent.

    **The result does not depend on the worker count.** Seeds are taken in order
    from the parent generator before any work starts, so a run at one job and a
    run at eight draw the same permutations and return the same `null_max`. A
    scheduler cannot move a number.
    """
    return rng.integers(0, 2**62, size=draws, dtype=np.int64)


def _max_over_draws(work, seeds: np.ndarray, jobs: int) -> float:
    """Largest value of ``work(seed)`` over the seeds, on ``jobs`` threads.

    Threads rather than processes: the draw is `argsort`, `bincount` and dense
    elementwise arithmetic, every one of which releases the GIL in numpy, so the
    parallelism is real and the sixteen-million-row arrays are shared rather than
    pickled to each worker. Measured at 1.67x on two cores.

    **This is not the GIL's doing.** The reason one core was busy is that numpy's
    sort, bincount and elementwise loops are single-threaded by construction;
    only BLAS level 3 is multithreaded and that is four percent of a draw here.
    """
    if jobs <= 1:
        return max(float(work(int(s))) for s in seeds)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return max(float(v) for v in pool.map(lambda s: work(int(s)), seeds))


@dataclass(frozen=True)
class CellClassTable:
    """Loan-level data collapsed to cell-by-class means, with the holes kept."""

    means: np.ndarray  # (n_cells, n_classes), zero where absent
    counts: np.ndarray  # (n_cells, n_classes), loans behind each mean
    present: np.ndarray  # (n_cells, n_classes) bool

    @property
    def fill(self) -> float:
        return float(self.present.mean())


def cell_class_table(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    counts: np.ndarray | None = None,
) -> CellClassTable:
    """Collapse loans to cell-by-class means by two bincounts, no Python loop.

    ``counts`` may be supplied by a caller drawing many nulls: the per-entry loan
    count is **invariant** under a within-cell label permutation, so recomputing
    it per draw is the same bincount every time. Supplying it is an optimisation
    and never a result; passing a stale one would be, which is why nothing here
    caches it on its own behalf.
    """
    flat = np.asarray(cell_ids) * n_classes + np.asarray(class_ids)
    size = n_cells * n_classes
    if counts is None:
        counts = np.bincount(flat, minlength=size).astype(np.float64)
    else:
        counts = np.asarray(counts, dtype=np.float64).ravel()
    totals = np.bincount(flat, weights=np.asarray(values, dtype=np.float64),
                         minlength=size)
    present = counts > 0
    means = np.zeros(size)
    means[present] = totals[present] / counts[present]
    shape = (n_cells, n_classes)
    return CellClassTable(
        means.reshape(shape), counts.reshape(shape), present.reshape(shape)
    )


@dataclass(frozen=True)
class Centred:
    gamma: np.ndarray
    iterations: int
    residual: float
    converged: bool


def alternating_centre(
    table: CellClassTable,
    tol: float = CENTRE_TOL,
    max_iter: int = CENTRE_MAX_ITER,
) -> Centred:
    """Remove the cell effect and the class effect, alternately, to a fixed point.

    On a complete design one pass of each suffices and the two centrings commute.
    **On an incomplete design they do not**, so this iterates and reports what it
    achieved rather than assuming one pass was enough. What remains is `gamma`.
    """
    w = table.counts * table.present
    gamma = table.means * table.present
    residual = np.inf
    it = 0
    for it in range(1, max_iter + 1):
        row_w = w.sum(axis=1)
        row_mean = np.divide(
            (w * gamma).sum(axis=1), row_w, out=np.zeros_like(row_w), where=row_w > 0
        )
        gamma = (gamma - row_mean[:, None]) * table.present

        col_w = w.sum(axis=0)
        col_mean = np.divide(
            (w * gamma).sum(axis=0), col_w, out=np.zeros_like(col_w), where=col_w > 0
        )
        gamma = (gamma - col_mean[None, :]) * table.present

        residual = float(max(np.abs(row_mean).max(), np.abs(col_mean).max()))
        if residual < tol:
            break
    return Centred(gamma, it, residual, residual < tol)


def pairwise_second_moment(
    gamma: np.ndarray, present: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """`S(a,b)` = mean over cells holding both `a` and `b`, plus the counts.

    Pairs that never co-occur get `S = 0` and a count of zero, and the caller
    reports how many there were. A zero that stands for "no data" and a zero that
    stands for "no interaction" are different objects, so the count travels with
    the matrix rather than being folded into it.
    """
    g = np.asarray(gamma) * present
    cooccur = (present.astype(np.float64).T @ present.astype(np.float64))
    numer = g.T @ g
    s = np.divide(numer, cooccur, out=np.zeros_like(numer), where=cooccur > 0)
    return 0.5 * (s + s.T), cooccur


#: Bits of randomness per cell in :func:`within_cell_order`. Two rows in one cell
#: colliding leaves them in their existing order, which is a deviation from
#: uniformity of order `n^2 / 2^41` per cell: about one collision in ten million
#: rows at the scale this stage runs at.
TIE_BITS = 40


def within_cell_order(
    cell_ids: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Indices grouped by cell, uniformly shuffled inside each cell.

    A two-key ``lexsort`` does this and costs about nine seconds on sixteen
    million rows, which is the whole cost of a null draw. Packing the cell and a
    random tail into **one** int64 and taking a single stable argsort is the same
    ordering and costs about one second, because numpy radix-sorts integers.

    The permutation distribution is unchanged, the **stream** is not: a run under
    this function draws different permutations from the same null than a run under
    the lexsort did. Monte Carlo nulls are compared by their verdict and not by
    their bytes, so that is a speed change and not a result change, but it is why
    a re-run does not reproduce an earlier `null_max` digit for digit.
    """
    cell_ids = np.asarray(cell_ids, dtype=np.int64)
    shift = np.int64(1) << TIE_BITS
    top = (int(cell_ids.max()) + 1) * int(shift) if cell_ids.size else 0
    if top >= (1 << 62):
        return np.lexsort((rng.random(cell_ids.size), cell_ids))
    key = cell_ids * shift + rng.integers(0, shift, cell_ids.size, dtype=np.int64)
    return np.argsort(key, kind="stable")


def permute_within_cells(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    rng: np.random.Generator,
    stable_order: np.ndarray | None = None,
) -> np.ndarray:
    """Shuffle class labels among the loans of each cell.

    Preserves the cell size, the class counts inside that cell, the within-cell
    dispersion and the whole missingness pattern. **Destroys only whether a
    class's position in one cell travels to another**, which is what a non-zero
    rank asserts.

    Vectorised through a lexsort rather than a loop over cells, so the null can
    be drawn as many times on the real sample as on a toy one. ``stable_order``
    may be supplied by a caller drawing many nulls on one design; it depends only
    on ``cell_ids``, so recomputing it per draw is the same argsort every time.

    **The loan counts per cell-class entry are invariant under this**, because
    the multiset of labels in a cell is preserved and only their assignment to
    loans changes. So the null moves the means and not the design, which is what
    makes it a null about the field rather than about the holes.
    """
    cell_ids = np.asarray(cell_ids)
    shuffled_order = within_cell_order(cell_ids, rng)
    if stable_order is None:
        stable_order = np.argsort(cell_ids, kind="stable")
    out = np.empty_like(np.asarray(class_ids))
    out[stable_order] = np.asarray(class_ids)[shuffled_order]
    return out


@dataclass(frozen=True)
class RankEstimate:
    """Everything a caller needs to report, including what it had to drop."""

    eigenvalues: np.ndarray  # descending, positive and negative alike
    eigenvectors: np.ndarray  # columns matching ``eigenvalues``, same order
    null_max: float
    null_draws: int
    rank: int
    negative_beyond_null: int
    empty_pairs: int
    fill: float
    iterations: int
    residual: float
    converged: bool

    def line(self) -> str:
        head = ", ".join(f"{v:.4g}" for v in self.eigenvalues[:6])
        return (
            f"rank={self.rank}  null_max={self.null_max:.4g}  "
            f"top eigenvalues [{head}]  neg_beyond_null={self.negative_beyond_null}  "
            f"fill={self.fill:.3f}  empty_pairs={self.empty_pairs}  "
            f"centring iters={self.iterations} residual={self.residual:.2e}"
        )


def spectrum(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    counts: np.ndarray | None = None,
) -> tuple[np.ndarray, Centred, np.ndarray, CellClassTable]:
    """One pass of the whole pipeline: table, centre, `S`, eigenvalues.

    The eigen**vectors** come back too, in the same descending order. B7-8 needs
    the leading class loading, not only how many directions clear the null, and
    an estimator that returns a count and throws the direction away cannot answer
    a question about whether the direction is stable.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes, counts)
    centred = alternating_centre(table)
    s, cooccur = pairwise_second_moment(centred.gamma, table.present)
    vals, vecs = np.linalg.eigh(s)
    return vals[::-1], vecs[:, ::-1], centred, cooccur, table


def estimate_rank(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    draws: int,
    rng: np.random.Generator,
    stable_order: np.ndarray | None = None,
    jobs: int | None = None,
) -> RankEstimate:
    """Criterion B7-4: eigenvalues of `S` above the permutation null's maximum.

    **The null runs the identical code path**, centring iteration included, so
    any bias the centring leaves on an incomplete design is present in the null
    too and cancels out of the comparison. That is the whole reason the estimator
    is allowed to be this involved.

    No percentile and no threshold is chosen here. The null statistic is the
    largest eigenvalue observed over the draws, which is a number the data
    produces.

    ``stable_order`` is an optimisation and never a result: it depends only on
    ``cell_ids``, so supplying it skips an argsort that would return the same
    permutation on every draw.
    """
    eig, vecs, centred, cooccur, table = spectrum(
        cell_ids, class_ids, values, n_cells, n_classes
    )

    counts = table.counts.ravel()
    if stable_order is None:
        stable_order = np.argsort(np.asarray(cell_ids), kind="stable")

    def one(seed: int) -> float:
        permuted = permute_within_cells(
            cell_ids, class_ids, np.random.default_rng(seed), stable_order
        )
        eig_n, _, _, _, _ = spectrum(
            cell_ids, permuted, values, n_cells, n_classes, counts
        )
        return float(eig_n[0])

    null_max = _max_over_draws(
        one, _null_seeds(rng, draws), default_jobs() if jobs is None else jobs
    )

    return RankEstimate(
        eigenvalues=eig,
        eigenvectors=vecs,
        null_max=float(null_max),
        null_draws=draws,
        rank=int((eig > null_max).sum()),
        negative_beyond_null=int((-eig > null_max).sum()),
        empty_pairs=int((cooccur == 0).sum()),
        fill=table.fill,
        iterations=centred.iterations,
        residual=centred.residual,
        converged=centred.converged,
    )


def synthetic_sample(
    rng: np.random.Generator,
    n_cells: int,
    n_classes: int,
    rank: int,
    noise: float,
    presence: float,
    loans_per_entry: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A field with an interaction of **exactly** the requested matrix rank.

    `U` and `V` are drawn and then column-centred, so `gamma = U V^T` has zero
    row means and zero column means by construction and is a pure interaction
    rather than something the additive part could absorb. Its rank is the
    requested one, not approximately.

    The missingness is imposed after the field is built and independently of it,
    so a class is not absent from a cell *because of* its own value. That is a
    stronger assumption than the real data satisfies and it is the right one for
    a criterion about the estimator: a recovery failure here would be the
    estimator's, not the design's.
    """
    if rank > 0:
        u = rng.normal(size=(n_cells, rank))
        v = rng.normal(size=(n_classes, rank))
        gamma = (u - u.mean(axis=0)) @ (v - v.mean(axis=0)).T
    else:
        gamma = np.zeros((n_cells, n_classes))

    phi = rng.normal(scale=2.0, size=n_cells)
    a_eff = rng.normal(scale=2.0, size=n_classes)
    field = phi[:, None] + a_eff[None, :] + gamma

    present = rng.random((n_cells, n_classes)) < presence
    present[np.arange(n_cells), rng.integers(0, n_classes, n_cells)] = True

    cells, classes = np.nonzero(present)
    reps = rng.integers(1, loans_per_entry + 1, cells.size)
    cell_ids = np.repeat(cells, reps)
    class_ids = np.repeat(classes, reps)
    values = field[cell_ids, class_ids] + rng.normal(scale=noise, size=cell_ids.size)
    return cell_ids, class_ids, values


def within_entry_sd(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
) -> float:
    """Pooled standard deviation of loans around their own cell-class mean.

    The noise the estimator has to see through, taken from the data rather than
    assumed. Entries holding one loan contribute no deviation and no degree of
    freedom, so they neither inflate nor deflate it.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes)
    resid = np.asarray(values, dtype=np.float64) - table.means[cell_ids, class_ids]
    dof = float(table.present.sum())
    n = float(np.asarray(values).size)
    return float(np.sqrt((resid @ resid) / max(n - dof, 1.0)))


def calibration_sample(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    rank: int,
    rng: np.random.Generator,
    spectrum_shape: np.ndarray | None = None,
) -> np.ndarray:
    """New values on the **observed design**, from a field of known matrix rank.

    Same rows, same cells, same classes, same loan counts, same holes. Only the
    numbers change. The synthetic interaction is scaled so its Frobenius norm
    over the present entries matches the observed `gamma`'s, and the noise is the
    observed within-entry dispersion, so the calibration asks the one question
    that matters: **on this design, at this signal strength, does the estimator
    return the rank it was given?**

    ``spectrum_shape`` gives the **relative** eigenvalues the constructed field
    should present, normally that design's own observed top `r`. Without it the
    random factors put roughly equal energy in every direction, so the constructed
    field has a **flat** spectrum and the gate only ever establishes that the
    design resolves a flat one. The observed spectrum on this stage's carrier runs
    about two to one, and whether a **skewed** field is resolved is precisely what
    decides whether the second direction sits near the null. §3.15's VOID 3.

    The amplitude weight is `sqrt(lambda_i / lambda_1)` because `S` is a second
    moment of `gamma`: an eigenvalue of `S` scales as the square of a direction's
    amplitude. The factors are orthonormalised first, without which a direction's
    weight would be confounded with its overlap with the others and the requested
    shape would not be the shape that arrives.

    This exists because the estimator inflates the rank when the design is
    sparse, and inflates it upward, which is the direction of the interesting
    reading. Section 6 of ``docs/b7_interaction_rank.md`` makes a rank-one pass
    of this the gate on the whole trichotomy.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes)
    observed = alternating_centre(table).gamma
    scale = float(np.sqrt((observed**2).sum()))

    if rank > 0:
        u = rng.normal(size=(n_cells, rank))
        v = rng.normal(size=(n_classes, rank))
        u = u - u.mean(axis=0)
        v = v - v.mean(axis=0)
        if spectrum_shape is None:
            weight = np.ones(rank)
        else:
            lam = np.asarray(spectrum_shape, dtype=np.float64)[:rank]
            if lam.size < rank or (lam <= 0).any():
                raise ValueError(
                    f"spectrum_shape must give {rank} positive eigenvalues, got {lam}"
                )
            # S is a second moment of gamma, so its eigenvalues scale as the
            # square of a direction's amplitude. sqrt is the amplitude ratio.
            weight = np.sqrt(lam / lam[0])
        # Orthonormalise so a direction's weight is its own and not its overlap
        # with the others; without this the requested shape is not what arrives.
        u = np.linalg.qr(u)[0] if rank > 1 else u / np.linalg.norm(u)
        v = np.linalg.qr(v)[0] if rank > 1 else v / np.linalg.norm(v)
        gamma = (u * weight) @ v.T
        gamma *= table.present
        norm = float(np.sqrt((gamma**2).sum()))
        gamma *= (scale / norm) if norm > 0 else 0.0
    else:
        gamma = np.zeros((n_cells, n_classes))

    sd = within_entry_sd(cell_ids, class_ids, values, n_cells, n_classes)
    return gamma[cell_ids, class_ids] + rng.normal(scale=sd, size=len(cell_ids))


def additive_fit(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """The additive part of the field at loan level, and what it leaves over.

    **Invariant across null draws**, because it is computed from the observed
    values and the draws only move the leftovers. Split out so a caller drawing a
    hundred nulls computes it once; recomputing it per draw is a second and a
    half of the same arithmetic each time.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes)
    gamma = alternating_centre(table).gamma
    fitted = table.means[cell_ids, class_ids] - gamma[cell_ids, class_ids]
    return fitted, np.asarray(values, dtype=np.float64) - fitted


def draw_residual_null(
    cell_ids: np.ndarray,
    fitted: np.ndarray,
    resid: np.ndarray,
    rng: np.random.Generator,
    stable_order: np.ndarray | None = None,
) -> np.ndarray:
    """One draw: the additive fit stays, the residual moves within its cell."""
    cells = np.asarray(cell_ids)
    shuffled = within_cell_order(cells, rng)
    if stable_order is None:
        stable_order = np.argsort(cells, kind="stable")
    moved = np.empty_like(resid)
    moved[stable_order] = resid[shuffled]
    return fitted + moved


def permute_residuals_within_cells(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    rng: np.random.Generator,
    stable_order: np.ndarray | None = None,
) -> np.ndarray:
    """The secondary null of §4: fit the additive model, shuffle what is left.

    ``permute_within_cells`` moves the class labels, which also redistributes the
    class main effect `A(a)` across cells and inflates the null. That inflation is
    harmless for the direction §4 argues about and it is still an inflation. This
    null removes it: the additive fit stays where it is and only the residual
    moves, within each cell.

    The residual is taken from the **additive** fit, so it carries `gamma` as well
    as the within-entry noise. Shuffling it within a cell destroys the alignment
    of `gamma` with the class labels but leaves its magnitude in the pool, so the
    interaction is recycled into the null as extra dispersion. **That makes this
    null conservative**, which is the safe direction and is the reason it is worth
    running beside the primary one rather than instead of it.

    A first version of this function differenced against the cell-class mean
    instead, which removes `gamma` *and* the between-entry noise from the pool. It
    understated the null by roughly a factor of two and read a constructed rank of
    one back as six. Recorded because the two differences look alike and only one
    of them is a null.

    Returns new values, not new labels, so the caller runs it through the same
    ``estimate_rank`` as the primary null and the two differ in nothing else.
    """
    fitted, resid = additive_fit(cell_ids, class_ids, values, n_cells, n_classes)
    return draw_residual_null(cell_ids, fitted, resid, rng, stable_order)


def estimate_rank_residual_null(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
    draws: int,
    rng: np.random.Generator,
    stable_order: np.ndarray | None = None,
    jobs: int | None = None,
) -> RankEstimate:
    """B7-5's second arm. Identical to :func:`estimate_rank` but for the null.

    The observed spectrum is the same object computed the same way; only the
    draws differ. So a disagreement between the two is a fact about the null and
    cannot be a fact about the estimator.
    """
    eig, vecs, centred, cooccur, table = spectrum(
        cell_ids, class_ids, values, n_cells, n_classes
    )
    fitted, resid = additive_fit(cell_ids, class_ids, values, n_cells, n_classes)
    counts = table.counts.ravel()
    if stable_order is None:
        stable_order = np.argsort(np.asarray(cell_ids), kind="stable")

    def one(seed: int) -> float:
        drawn = draw_residual_null(
            cell_ids, fitted, resid, np.random.default_rng(seed), stable_order
        )
        eig_n, _, _, _, _ = spectrum(
            cell_ids, class_ids, drawn, n_cells, n_classes, counts
        )
        return float(eig_n[0])

    null_max = _max_over_draws(
        one, _null_seeds(rng, draws), default_jobs() if jobs is None else jobs
    )
    return RankEstimate(
        eigenvalues=eig,
        eigenvectors=vecs,
        null_max=float(null_max),
        null_draws=draws,
        rank=int((eig > null_max).sum()),
        negative_beyond_null=int((-eig > null_max).sum()),
        empty_pairs=int((cooccur == 0).sum()),
        fill=table.fill,
        iterations=centred.iterations,
        residual=centred.residual,
        converged=centred.converged,
    )


# ---------------------------------------------------------------------------
# §3.16. The calibration matched to the observed field, not only shaped to it.
# ---------------------------------------------------------------------------
#
# :func:`calibration_sample` above is kept and is not called by the live gates
# any more. Nothing in this repository is deleted, and leaving it in place is
# also the only way a reader can check that the two constructions differ where
# §3.16 says they do and nowhere else.


def _second_moment(gamma_masked: np.ndarray, cooccur: np.ndarray) -> np.ndarray:
    """`S` from an already-masked `gamma` and a precomputed co-occurrence count.

    :func:`pairwise_second_moment` recomputes ``present.T @ present`` on every
    call, which allocates a float copy of the cell-by-class mask each time. The
    mask does not move across repetitions of a gate arm, so a caller running
    sixty of them on one design can compute it once. Same arithmetic, same
    result.
    """
    numer = gamma_masked.T @ gamma_masked
    s = np.divide(numer, cooccur, out=np.zeros_like(numer), where=cooccur > 0)
    return 0.5 * (s + s.T)


@dataclass(frozen=True)
class CalibrationBasis:
    """Everything a constructed sample takes from the observed field.

    Invariant across constructed ranks and across repetitions, so a caller
    running sixty gate arms on one design computes it once instead of sixty
    times. Every quantity in it is read off the observed sample and none is
    chosen.
    """

    additive: np.ndarray  # loan level: the observed field's additive part
    sd: float  # observed within-entry dispersion
    eigenvalues: np.ndarray  # observed spectrum of S, descending
    present: np.ndarray  # (n_cells, n_classes) bool
    cooccur: np.ndarray  # (n_classes, n_classes) cells holding both
    n_cells: int
    n_classes: int

    @property
    def fill(self) -> float:
        return float(self.present.mean())

    def shape(self, rank: int, floor: float = 0.0) -> np.ndarray:
        """The observed top-`rank` eigenvalues net of the noise floor, or a refusal.

        ``floor`` is §3.17's `c`, the contribution sampling noise makes to every
        direction of `S`, measured by :func:`measure_noise_floor`. The observed
        `lambda_i` already contains it, so a construction aimed at `lambda_i` and
        then given the same noise lands at `lambda_i + c`. Subtracting it here is
        what makes the **recovered** spectrum land on the observed one.

        A rank-`r` arm on a design whose observed `lambda_r` does not clear the
        floor has no observed level for a rank-`r` construction to be set to.
        **That is reported and not substituted**: falling back to a flat spectrum
        would be VOID 3 again, and falling back to the previous positive
        eigenvalue would invent a number. The caller catches this and records the
        arm as unavailable, which is a fact about the design.
        """
        lam = np.asarray(self.eigenvalues, dtype=np.float64)[:rank] - float(floor)
        if lam.size < rank or (lam <= 0).any():
            raise ValueError(
                f"the observed top {rank} does not clear the noise floor "
                f"{float(floor):.6g}: "
                f"{np.asarray(self.eigenvalues)[:max(rank, 1)]}"
            )
        return lam


def calibration_basis(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
) -> CalibrationBasis:
    """One pass over the observed sample, giving everything :func:`matched_sample` needs.

    Costs about what one null draw costs, once per design rather than once per
    repetition.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes)
    centred = alternating_centre(table)
    s, cooccur = pairwise_second_moment(centred.gamma, table.present)
    eig = np.linalg.eigvalsh(s)[::-1]

    entry = table.means[cell_ids, class_ids]
    additive = entry - centred.gamma[cell_ids, class_ids]

    resid = np.asarray(values, dtype=np.float64) - entry
    dof = float(table.present.sum())
    n = float(np.asarray(values).size)
    sd = float(np.sqrt((resid @ resid) / max(n - dof, 1.0)))

    return CalibrationBasis(
        additive=additive,
        sd=sd,
        eigenvalues=eig,
        present=table.present,
        cooccur=cooccur,
        n_cells=int(n_cells),
        n_classes=int(n_classes),
    )


def matched_sample(
    basis: CalibrationBasis,
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    rank: int,
    rng: np.random.Generator,
    floor: float = 0.0,
    noise_sd: np.ndarray | float | None = None,
) -> np.ndarray:
    """New loan values on the observed design, differing from it in **rank alone**.

    Registered in ``docs/b7_interaction_rank.md`` §3.16. It differs from
    :func:`calibration_sample` in three places, and each of the three moves the
    gate in the same direction: **towards being harder than the reading it
    licenses, rather than easier.**

    **1. The additive part is the observed one, not absent.** The old
    construction returned `gamma + noise` and no cell or class main effect. The
    primary null shuffles class labels within a cell, so the spread it draws from
    is the spread of values inside that cell, and a class main effect `A(a)` is
    part of that spread in the observed sample and was not part of it in the
    constructed one. A constructed sample with no `A` therefore faced a **thinner
    null** than the reading faces. Here the observed additive fit is carried
    across unchanged, so the null the gate faces is the null the reading faces.

    **2. The interaction is set to the observed eigenvalues, not to the observed
    Frobenius norm.** `S`'s trace is the whole of the observed interaction's
    energy, its top `r` directions are a part of it, and scaling a rank-`r`
    construction to the total hands those `r` directions everything the tail was
    carrying. That is stronger than what was observed **by construction**, for
    any design whose tail is non-zero, which is every design. Here the
    construction is scaled so that its own `S` has the observed `lambda_1`, with
    the remaining directions in the observed ratios, so the constructed field is
    the size of the thing the reading claims to have seen.

    **3. The directions are orthonormalised before they are weighted.** Without
    it a direction's amplitude is confounded with its overlap with the others and
    the requested shape is not the shape that arrives.

    **4. The level is set net of the noise floor**, `floor`, which is §3.17 and
    which the first version of this function did not do. The level match is
    applied to `gamma` before the sampling noise adds its own energy to every
    direction of `S`, so aiming at the observed `lambda_i` lands at
    `lambda_i + c`. Passing `floor = c` from :func:`measure_noise_floor` aims at
    `lambda_i - c` so that the **recovered** spectrum lands on the observed one.
    The default of zero reproduces §3.16's first version exactly, which is what
    `experiments/b7_calib_check.py` compares against.

    ``noise_sd`` takes an array of one standard deviation per class, which is
    §3.25's B7-13 and the direct test of the approximation named below. Left at
    ``None`` the noise is the pooled scalar, which is every gate this stage ran.

    What is still an approximation at ``noise_sd=None``, said plainly. The noise is
    homoskedastic at the pooled within-entry dispersion and the observed noise is
    not; and the
    floor is one number subtracted from every direction, which is exact only if
    the noise's expected second moment is a multiple of the identity in class
    space, which it is not, because classes hold different loan counts.
    `experiments/b7_calib_check.py` measures what the construction actually
    recovers, so neither approximation has to be trusted.
    """
    cell_ids = np.asarray(cell_ids)
    if rank > 0:
        lam = basis.shape(rank, floor)
        u = rng.normal(size=(basis.n_cells, rank))
        v = rng.normal(size=(basis.n_classes, rank))
        # Centred first, so the construction is a pure interaction that the
        # additive part could not absorb; the QR of a matrix whose columns each
        # sum to zero has columns that each sum to zero, so orthonormalising
        # afterwards does not undo it.
        u = np.linalg.qr(u - u.mean(axis=0))[0]
        v = np.linalg.qr(v - v.mean(axis=0))[0]
        gamma = ((u * np.sqrt(lam)) @ v.T) * basis.present
        # S is quadratic in gamma and the mask does not move, so one rescale is
        # exact: multiplying gamma by alpha multiplies every eigenvalue of S by
        # alpha squared. No iteration is needed and none is done.
        top = float(np.linalg.eigvalsh(_second_moment(gamma, basis.cooccur))[-1])
        gamma *= float(np.sqrt(lam[0] / top)) if top > 0 else 0.0
    else:
        gamma = np.zeros((basis.n_cells, basis.n_classes))

    class_ids = np.asarray(class_ids)
    if noise_sd is None:
        scale = basis.sd
    else:
        sd = np.asarray(noise_sd, dtype=np.float64)
        scale = basis.sd if sd.ndim == 0 else sd[class_ids]
    return (
        basis.additive
        + gamma[cell_ids, class_ids]
        + rng.normal(size=cell_ids.size) * scale
    )


def measure_noise_floor(
    basis: CalibrationBasis,
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    rng: np.random.Generator,
    draws: int = 3,
) -> tuple[float, list[float]]:
    """§3.17's `c`: what sampling noise alone contributes to each direction of `S`.

    A cell-class entry's mean is a mean of finitely many loans, so it carries
    sampling noise of order `sd^2 / n`, and `S` is a second moment of those
    means. The observed `lambda_i` is therefore the field's `i`-th eigenvalue
    **plus** the noise's contribution to that direction, and a construction aimed
    at `lambda_i` that then receives the same noise overshoots by exactly that
    contribution.

    Measured, not derived. The closed form is the mean over classes of the mean
    over cells of `sd^2 / n_ca`, and it ignores the alternating centring, which
    removes part of the noise before `S` sees it. Running a rank-zero matched
    sample through the identical code path the reading uses gets the centring for
    free, and it costs one pass. That is the same argument :func:`estimate_rank`
    makes for putting its null through the identical path.

    Returns `(c, per_draw)` where `c` is the mean over draws of `trace(S) /
    n_classes`. The per-draw values travel with it because a floor whose draws
    disagree is a floor that is not the same object on every repetition, and the
    caller should be able to see that rather than take a mean on faith.
    """
    per_draw: list[float] = []
    for _ in range(max(1, draws)):
        v = matched_sample(basis, cell_ids, class_ids, 0,
                           np.random.default_rng(rng.integers(0, 2**62)))
        eig, _vecs, _c, _co, _t = spectrum(
            cell_ids, class_ids, v, basis.n_cells, basis.n_classes
        )
        per_draw.append(float(eig.sum() / basis.n_classes))
    return float(np.mean(per_draw)), per_draw


@dataclass(frozen=True)
class SolvedFloor:
    """The floor a design's constructed rank-`r` arm actually uses, and its miss."""

    rank: int
    floor: float
    start: float
    steps: list[dict]
    achieved: list[float]  # recovered top-r, mean over the final draws
    target: list[float]  # observed top-r
    draws: int

    def _miss(self, recovered) -> float:
        a = np.asarray(recovered, dtype=np.float64)
        t = np.asarray(self.target, dtype=np.float64)
        if a.size == 0:
            return 0.0
        return float(np.abs(a / t - 1.0).max())

    @property
    def worst_relative_miss(self) -> float:
        """Largest relative distance between a recovered and an observed eigenvalue.

        **This travels with every rate the arm produces.** §3.18 gates nothing on
        it, for the reason §3.15's VOID 1 gates nothing on a rate: a number that
        is reported beside the thing it qualifies is more use than a threshold
        that throws it away.
        """
        return self._miss(self.achieved)

    @property
    def miss_before_solve(self) -> float:
        """The same, at the starting floor. §3.18's one hard condition compares them."""
        return self._miss(self.steps[0]["recovered"]) if self.steps else self._miss(
            self.achieved
        )

    @property
    def improved(self) -> bool:
        return self.worst_relative_miss <= self.miss_before_solve

    def line(self) -> str:
        got = ", ".join(f"{v:.4g}" for v in self.achieved)
        want = ", ".join(f"{v:.4g}" for v in self.target)
        return (
            f"rank {self.rank}  floor {self.start:.6f} -> {self.floor:.6f}   "
            f"recovered [{got}] against observed [{want}]   "
            f"miss {self.miss_before_solve * 100:.2f}% -> "
            f"{self.worst_relative_miss * 100:.2f}%"
            f"{'' if self.improved else '   [SOLVE DID NOT IMPROVE]'}"
        )


def solve_floor(
    basis: CalibrationBasis,
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    rank: int,
    rng: np.random.Generator,
    draws: int = 3,
    start: float | None = None,
    iters: int = 1,
) -> SolvedFloor:
    """§3.18: choose the floor so the **recovered** top-`rank` lands on the observed.

    **Voided by §3.19 and no longer called by the gate.** It computes its step
    from a three-draw mean whose sampling error it never measures, and its own
    acceptance test uses that same three-draw measurement, so the test cannot
    separate a real improvement from the draw it happened to get. The residue it
    was chasing turned out to be the same size as the construction's own
    draw-to-draw scatter, which the gate now measures for free out of its own
    repetitions. Kept because nothing here is deleted and because a reader
    checking that claim needs the function that produced it.

    §3.17 subtracts one number from every direction, which is exact only if the
    noise's expected second moment is a multiple of the identity in class space.
    It is not, because classes hold very different loan counts, and a rank-`r`
    construction's directions are not the noise's own eigendirections. So the
    starting floor leaves a residue, and the residue is in the same direction as
    every defect §3.15 through §3.17 corrected: the constructed field lands
    **above** the observed one and the gate is easier than the reading.

    **What is solved for is the construction's input, not the gate's answer.**
    The target is the observed spectrum, which is fixed before this runs. Whether
    the estimator then returns `rank` on the constructed field is not an input to
    this and is not touched by it. A calibration that hits its declared target is
    the precondition for the gate meaning anything, and reaching it by measuring
    rather than by assuming isotropy is the same choice `measure_noise_floor`
    already makes.

    One step is the default. The map from floor to recovered spectrum is
    `lambda_i - floor + offset(floor)` with the offset nearly flat in the floor,
    so a step of the mean excess lands within its own sampling error. ``steps``
    records every iterate and ``achieved`` records what the final floor actually
    recovers, so a solve that did not converge is visible instead of assumed.
    """
    target = np.asarray(basis.eigenvalues, dtype=np.float64)[:rank]
    c = (
        measure_noise_floor(basis, cell_ids, class_ids, rng, draws)[0]
        if start is None
        else float(start)
    )
    c0 = c
    steps: list[dict] = []

    def recover(floor: float) -> np.ndarray:
        """Mean recovered top-`rank` over ``draws`` constructions at this floor."""
        got = []
        for _ in range(max(1, draws)):
            v = matched_sample(
                basis, cell_ids, class_ids, rank,
                np.random.default_rng(rng.integers(0, 2**62)), floor=floor,
            )
            eig, _vecs, _cen, _co, _t = spectrum(
                cell_ids, class_ids, v, basis.n_cells, basis.n_classes
            )
            got.append(np.asarray(eig)[:rank])
        return np.mean(got, axis=0)

    achieved = recover(c)
    for _ in range(max(0, iters)):
        excess = float(np.mean(achieved - target))
        steps.append(
            {
                "floor": float(c),
                "recovered": [float(v) for v in achieved],
                "mean_excess": excess,
            }
        )
        c = c + excess
        achieved = recover(c)

    return SolvedFloor(
        rank=int(rank),
        floor=float(c),
        start=float(c0),
        steps=steps,
        achieved=[float(v) for v in achieved],
        target=[float(v) for v in target],
        draws=int(draws),
    )



def class_dispersions(
    cell_ids: np.ndarray,
    class_ids: np.ndarray,
    values: np.ndarray,
    n_cells: int,
    n_classes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Two per-class dispersions, which bracket a class's own noise. §3.25's B7-13.

    Returns ``(within_entry, within_cell)``.

    ``within_entry`` is the dispersion of a class-`a` loan about its own
    cell-class mean, over the entries holding two or more of them. It is the noise
    proper, and for a class at about one loan per entry it is estimated on a
    **selected** minority of cells, the ones where that class is common, so it is
    a **lower** bracket whose bias is not signable in advance.

    ``within_cell`` is the dispersion about the **cell** mean, over every loan of
    the class with no selection at all. It still contains the class main effect and
    `gamma`, so it is an **upper** bracket.

    §3.24 voided comparing these two to `S(a,a)` algebraically, because for a class
    at one loan per entry the upper one is nearly an identity with it. **Used as
    the noise level of a constructed field they are not compared to anything**:
    they bracket an outcome that the full estimator and its null produce, which is
    what B7-13 does with them.

    A class with no entry holding two or more loans falls back to the pooled
    within-entry dispersion and the fallback is reported by the caller. That does
    not arise on this stage's sample.
    """
    table = cell_class_table(cell_ids, class_ids, values, n_cells, n_classes)
    values = np.asarray(values, dtype=np.float64)
    cell_ids = np.asarray(cell_ids)
    class_ids = np.asarray(class_ids)

    cell_n = np.bincount(cell_ids, minlength=n_cells).astype(np.float64)
    cell_sum = np.bincount(cell_ids, weights=values, minlength=n_cells)
    dev_cell = values - (cell_sum / np.maximum(cell_n, 1.0))[cell_ids]
    dev_entry = values - table.means[cell_ids, class_ids]
    n_ca = table.counts[cell_ids, class_ids]

    pooled = within_entry_sd(cell_ids, class_ids, values, n_cells, n_classes)
    entry = np.full(n_classes, pooled)
    cell = np.full(n_classes, pooled)
    for a in range(n_classes):
        m = class_ids == a
        if not m.any():
            continue
        cell[a] = float(np.sqrt(np.mean(dev_cell[m] ** 2)))
        big = m & (n_ca >= 2)
        counts_a = table.counts[table.present[:, a], a]
        dof = float((counts_a >= 2).sum())
        if big.sum() > dof:
            entry[a] = float(np.sqrt((dev_entry[big] ** 2).sum()
                                     / (big.sum() - dof)))
    return entry, cell

def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial rate. `z` is the two-sided 95% normal quantile.

    Used for the power arm of §3.15's VOID 1, which has no nominal to be tested
    against and so gets an interval rather than a line. Wilson rather than
    Wald because the arm is expected to sit near `1`, where Wald's interval
    leaves the unit interval and its coverage collapses.
    """
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def binomial_tail_at_least(k: int, n: int, p: float) -> float:
    """`P(X >= k)` for `X ~ Binomial(n, p)`, exactly, by summing the pmf.

    The size arms of §3.15's VOID 1 are compared against the estimator's own
    nominal `1/(d+1)`, and this is that comparison. Exact rather than normal,
    because `n` is twenty and `p` is about `0.02`, where the normal
    approximation is worthless.

    Written out rather than taken from `scipy.stats`, because this repository's
    dependency list is `numpy` and one function is not a reason to change that.
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    # Log-space, so n choose j does not overflow for any n this is called with.
    j = np.arange(k, n + 1, dtype=np.float64)
    from math import lgamma

    log_c = np.array(
        [lgamma(n + 1) - lgamma(int(x) + 1) - lgamma(n - int(x) + 1) for x in j]
    )
    log_p = log_c + j * np.log(p) + (n - j) * np.log1p(-p)
    m = log_p.max()
    return float(np.exp(m) * np.exp(log_p - m).sum())
