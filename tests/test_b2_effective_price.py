"""Tests for B2 loop A.

The first group checks the variance decomposition against constructions whose
answers are known independently. The null being tested against is that the
within-cell share is zero, so a bug that inflates it would manufacture the
conclusion, and these tests exist to make that impossible to do quietly.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.effective_price import (
    CELL_KEYS,
    cell_dispersion,
    make_cell_ids,
    run_loop_a,
    variance_decomposition,
)


def sample(n: int = 4000, seed: int = 0, tract_effect: float = 0.4, noise: float = 0.6):
    rng = np.random.default_rng(seed)
    tracts = np.array([f"{i:011d}" for i in range(40)])
    chosen = rng.choice(tracts, n)
    cols = {
        "activity_year": rng.choice([2023, 2024], n).astype(str),
        "census_tract": chosen,
        "occupancy_type": rng.choice(["1", "2", "3"], n, p=[0.8, 0.05, 0.15]),
        "lien_status": np.full(n, "1"),
        "loan_purpose": np.full(n, "1"),
        "derived_loan_product_type": np.full(n, "Conventional:First Lien"),
        "derived_dwelling_category": np.full(n, "Single Family (1-4 Units):Site-Built"),
    }
    effect = {t: rng.normal(0, tract_effect) for t in tracts}
    spread = np.array([effect[t] for t in chosen]) + rng.normal(0, noise, n)
    return spread, cols


# -- the decomposition, against known answers --------------------------------


def test_law_of_total_variance_holds_exactly() -> None:
    """between + within equals the total variance to floating point.

    If this fails, no other number in the stage means anything.
    """
    rng = np.random.default_rng(1)
    ids = rng.integers(0, 30, size=5000)
    vals = rng.normal(ids * 0.3, 0.7)
    split = variance_decomposition(vals, ids)
    assert split.total == pytest.approx(float(vals.var()), abs=1e-12)


def test_a_pure_position_effect_gives_zero_within_share() -> None:
    """The null, constructed. Every loan in a cell has identical terms, which is
    what a scalar on positions predicts, and the within share must vanish."""
    ids = np.repeat(np.arange(50), 40)
    vals = np.repeat(np.random.default_rng(2).normal(size=50), 40)
    assert variance_decomposition(vals, ids).within_share < 1e-12


def test_a_single_cell_puts_everything_within() -> None:
    ids = np.zeros(2000, dtype=int)
    vals = np.random.default_rng(3).normal(size=2000)
    assert variance_decomposition(vals, ids).within_share == pytest.approx(1.0)


def test_empty_input_is_handled() -> None:
    split = variance_decomposition(np.array([]), np.array([]))
    assert split.total == 0.0
    assert split.within_share == 0.0


def test_within_share_rises_with_borrower_noise() -> None:
    """Monotone in the thing it is supposed to measure."""
    shares = []
    for noise in (0.1, 0.5, 1.5):
        spread, cols = sample(noise=noise, seed=4)
        shares.append(run_loop_a(spread, cols).split.within_share)
    assert shares[0] < shares[1] < shares[2]


def test_within_share_falls_with_position_effect() -> None:
    shares = []
    for effect in (0.1, 0.6, 2.0):
        spread, cols = sample(tract_effect=effect, seed=5)
        shares.append(run_loop_a(spread, cols).split.within_share)
    assert shares[0] > shares[1] > shares[2]


# -- cell construction -------------------------------------------------------


def test_missing_cell_key_raises_rather_than_coarsening() -> None:
    """A coarser cell inflates within-cell dispersion, which biases the answer
    toward the conclusion. So this must fail loudly."""
    cols = {k: np.array(["x"]) for k in CELL_KEYS[:-1]}
    with pytest.raises(KeyError, match="missing cell-defining columns"):
        make_cell_ids(cols)


def test_mismatched_column_lengths_raise() -> None:
    cols = {k: np.array(["x", "y"]) for k in CELL_KEYS}
    cols["census_tract"] = np.array(["x"])
    with pytest.raises(ValueError, match="length"):
        make_cell_ids(cols)


def test_cell_ids_separate_on_every_key() -> None:
    base = {k: np.array(["a", "a"]) for k in CELL_KEYS}
    assert len(np.unique(make_cell_ids(base))) == 1
    for key in CELL_KEYS:
        altered = {k: v.copy() for k, v in base.items()}
        altered[key] = np.array(["a", "b"])
        assert len(np.unique(make_cell_ids(altered))) == 2, key


# -- dispersion --------------------------------------------------------------


def test_small_cells_are_excluded() -> None:
    """A cell of one has zero dispersion by construction and would bias the
    result toward integrability."""
    vals = np.concatenate([np.random.default_rng(6).normal(size=50), np.array([9.0])])
    ids = np.concatenate([np.full(50, "big"), np.array(["tiny"])])
    disp = cell_dispersion(vals, ids, min_size=20)
    assert disp.cell_id.tolist() == ["big"]


def test_dispersion_is_zero_on_a_constant_cell() -> None:
    vals = np.full(40, 1.25)
    ids = np.full(40, "c")
    disp = cell_dispersion(vals, ids, min_size=20)
    assert disp.iqr[0] == 0.0
    assert disp.p90_p10[0] == 0.0


# -- falsification wiring ----------------------------------------------------


def test_falsification_fires_on_a_pure_gradient_sample() -> None:
    """Constructed so the pre-registered failure condition must fire. If it does
    not, the check is not wired to anything."""
    n = 4000
    rng = np.random.default_rng(7)
    tracts = np.array([f"{i:011d}" for i in range(40)])
    chosen = rng.choice(tracts, n)
    cols = {
        "activity_year": np.full(n, "2024"),
        "census_tract": chosen,
        "occupancy_type": np.full(n, "1"),
        "lien_status": np.full(n, "1"),
        "loan_purpose": np.full(n, "1"),
        "derived_loan_product_type": np.full(n, "Conventional:First Lien"),
        "derived_dwelling_category": np.full(n, "SF"),
    }
    effect = {t: rng.normal(0, 0.5) for t in tracts}
    spread = np.array([effect[t] for t in chosen])  # no borrower term at all
    result = run_loop_a(spread, cols)
    fired = result.falsifications()
    assert fired["delta_A_indistinguishable_from_zero"]
    assert fired["dispersion_negligible"]


def test_falsification_does_not_fire_when_dispersion_is_present() -> None:
    spread, cols = sample(seed=8)
    fired = run_loop_a(spread, cols).falsifications()
    assert not fired["delta_A_indistinguishable_from_zero"]
    assert not fired["dispersion_negligible"]


def test_occupancy_breakdown_is_computed_separately() -> None:
    spread, cols = sample(seed=9)
    result = run_loop_a(spread, cols)
    assert set(result.by_occupancy) <= {"1", "2", "3"}
    assert all(0.0 <= v.within_share <= 1.0 for v in result.by_occupancy.values())
