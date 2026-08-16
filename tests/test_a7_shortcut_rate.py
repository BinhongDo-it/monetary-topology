"""`NetworkSpec.shortcut_rate`: the default reproduces, the arm is not inert,
and it agrees with the availability check elementwise.

`docs/a7_continuous_c.md` section 2 registers A7's construction parameter. Five
claims, and the second and fifth are as necessary as the first.

**The default must reach no code.** `0.0` is what every A2, A3, A4, A5 and A6
number in the repository was produced under. A field that moved a float in the
default position would make every stored number a measurement against a base
that shifted underneath it. `SESSION_INIT.md` lesson four, which has held four
times before this one.

**`replace` is a hand-written field list.** A field left out of it is not a
missing feature, it is a silent reset to the default, and the sweep reaches
every cell through `replace`. The test for that is separate from the test for
the field itself because the two fail differently.

**The endpoints must be exact rather than limits.** `s = 0` is the stratified
graph bit for bit and `s = 1` is what `uniform_access` returns for the
adjacency. Section 2.6 rests on that and so does every reading of the sweep's
two ends.

**It must agree with `experiments/a7a_continuous_c.py`.** The availability
check builds the stratified graph and then adds; this builds and adds inside one
call. Two code paths, and the numbers in section 2.6 were measured on the first
one. If they disagree, the registered figures do not describe the object the
stage runs on.

**And it must not be inert.** `centrality_bins` had a field, a validator, a
documented meaning and no line reading it, so a grid swept it twice and reported
two clean cells that were the registered point recomputed. A parameter that
reaches no code passes every reproduction test perfectly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from monetary_topology.asset import centrality
from monetary_topology.network import (
    _OPENING_PERMUTATION_OFFSET,
    _SHORTCUT_OFFSET,
    NetworkSpec,
    build_graph,
)

ROOT = Path(__file__).resolve().parents[1]

#: The availability check's own grid. Copied rather than imported so that a
#: later edit to the check cannot silently change what this file asserts over.
GRID: tuple[float, ...] = (
    0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4,
    0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0,
)

SEEDS = (0, 1, 2)


def _availability_check():
    """`experiments/a7a_continuous_c.py`, loaded by path like the rest."""
    path = ROOT / "experiments" / "a7a_continuous_c.py"
    spec = importlib.util.spec_from_file_location("a7a_continuous_c", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- the default


@pytest.mark.parametrize("seed", SEEDS)
def test_default_is_zero_and_the_stratified_graph_is_unchanged(seed: int) -> None:
    spec = NetworkSpec(seed=seed)
    assert spec.shortcut_rate == 0.0
    assert np.array_equal(
        build_graph(spec), build_graph(spec.replace(shortcut_rate=0.0))
    )


def test_replace_carries_the_field_rather_than_resetting_it() -> None:
    spec = NetworkSpec(seed=0, shortcut_rate=0.3)
    assert spec.replace(seed=2).shortcut_rate == pytest.approx(0.3)
    assert spec.replace(shortcut_rate=0.7).shortcut_rate == pytest.approx(0.7)


# -------------------------------------------------------------- the endpoints


@pytest.mark.parametrize("seed", SEEDS)
def test_zero_returns_the_stratified_graph(seed: int) -> None:
    spec = NetworkSpec(seed=seed)
    assert np.array_equal(
        build_graph(spec.replace(shortcut_rate=0.0)), build_graph(spec)
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_one_returns_the_complete_graph_and_matches_uniform_access(seed: int) -> None:
    spec = NetworkSpec(seed=seed)
    n = spec.size
    at_one = build_graph(spec.replace(shortcut_rate=1.0))
    assert np.array_equal(at_one, 1.0 - np.eye(n))
    assert np.array_equal(at_one, build_graph(spec.replace(uniform_access=True)))


# ----------------------------------------------- agreement with the check


@pytest.mark.parametrize("seed", SEEDS)
def test_matches_the_availability_check_at_every_grid_point(seed: int) -> None:
    blend = _availability_check().blend
    spec = NetworkSpec(seed=seed)
    for s in GRID:
        assert np.array_equal(
            build_graph(spec.replace(shortcut_rate=s)), blend(spec, s)
        ), f"seed {seed}, s = {s}"


# ------------------------------------------------------------- the mechanism


@pytest.mark.parametrize("seed", SEEDS)
def test_edges_are_nested_as_the_rate_rises(seed: int) -> None:
    """One draw thresholded, so a larger rate can only add. The sweep is a path
    through one family of graphs rather than seventeen unrelated draws."""
    spec = NetworkSpec(seed=seed)
    previous = build_graph(spec.replace(shortcut_rate=GRID[0]))
    for s in GRID[1:]:
        current = build_graph(spec.replace(shortcut_rate=s))
        assert np.all(current >= previous), f"seed {seed}, s = {s}"
        previous = current


@pytest.mark.parametrize("seed", SEEDS)
def test_the_arm_is_not_inert(seed: int) -> None:
    """An interior point must differ from both ends, in the adjacency and in
    the quantity the terms matrix is built from."""
    spec = NetworkSpec(seed=seed)
    low = build_graph(spec.replace(shortcut_rate=0.0))
    mid = build_graph(spec.replace(shortcut_rate=0.2))
    high = build_graph(spec.replace(shortcut_rate=1.0))
    assert not np.array_equal(mid, low)
    assert not np.array_equal(mid, high)
    assert mid.sum() > low.sum()
    assert centrality(mid).std() < centrality(low).std()


#: Measured, not derived. Over twenty seeds the per-seed dispersion is monotone
#: at eighteen of them; the two exceptions rise by at most `7.6e-4`, which is
#: `0.62%` of that seed's own `s = 0` value, and every violation sits at the
#: single grid step `0.01 -> 0.02`. `docs/a7_continuous_c.md` section 2.6 carries
#: the same measurement and the correction it forced to A7-A-5.
_PER_SEED_DISPERSION_TOLERANCE = 1e-3


def _dispersion_curve(seed: int) -> list[float]:
    spec = NetworkSpec(seed=seed)
    return [
        float(centrality(build_graph(spec.replace(shortcut_rate=s))).std())
        for s in GRID
    ]


def test_dispersion_falls_along_the_grid_in_the_seed_mean() -> None:
    """The registered form. Section 2.6's `0.161 -> 0.000` is a five-seed mean,
    and the check that produced it prints means."""
    curves = np.array([_dispersion_curve(seed) for seed in range(5)])
    mean = curves.mean(axis=0)
    assert mean[0] == pytest.approx(0.161, abs=5e-4)
    assert mean[-1] == pytest.approx(0.0, abs=1e-12)
    assert np.all(np.diff(mean) <= 0.0), mean


@pytest.mark.parametrize("seed", SEEDS)
def test_dispersion_is_per_seed_monotone_within_the_measured_tolerance(
    seed: int,
) -> None:
    """Per seed it is *nearly* monotone, and the deviation is noise at the dense
    low end rather than a cliff. Asserting exact per-seed monotonicity would be
    asserting something the availability check never measured, and section 2.6
    records that A7-A-5 was filed that way and corrected."""
    sds = _dispersion_curve(seed)
    assert sds[-1] == pytest.approx(0.0, abs=1e-12)
    assert sds[0] > sds[-1]
    rises = [
        (GRID[i], GRID[i + 1], later - earlier)
        for i, (earlier, later) in enumerate(zip(sds, sds[1:]))
        if later > earlier
    ]
    assert all(
        rise <= _PER_SEED_DISPERSION_TOLERANCE for _, _, rise in rises
    ), f"seed {seed}: {rises}"


def test_the_grid_has_no_cliff() -> None:
    """No single step may account for a large share of the whole fall. A sweep
    whose dispersion sat flat and then dropped at one step would be a two-point
    comparison wearing a grid, which is the thing the availability check existed
    to rule out."""
    curves = np.array([_dispersion_curve(seed) for seed in range(5)])
    mean = curves.mean(axis=0)
    steps = -np.diff(mean)
    assert steps.max() / steps.sum() < 0.25, mean


def test_the_stream_is_fresh() -> None:
    """The added edges must not correlate with the graph's own draw, the payroll
    receiver order or the opening permutation."""
    assert _SHORTCUT_OFFSET not in (0, 4241, _OPENING_PERMUTATION_OFFSET)
    seed = 0
    shortcut = np.random.default_rng(seed + _SHORTCUT_OFFSET).random(64)
    for other in (seed, seed + 4241, seed + _OPENING_PERMUTATION_OFFSET):
        assert not np.array_equal(shortcut, np.random.default_rng(other).random(64))


# -------------------------------------------------------------- validation


@pytest.mark.parametrize("bad", (-0.01, 1.01, 2.0))
def test_out_of_range_is_refused(bad: float) -> None:
    with pytest.raises(ValueError, match="shortcut_rate"):
        NetworkSpec(shortcut_rate=bad)


def test_uniform_access_and_shortcut_rate_cannot_both_be_set() -> None:
    """They are two different objects and A7 never switches `uniform_access`
    on. Silently letting both through would produce an `s = 1` arm that also
    collapsed the payroll incidence, the routing, the propensities and the
    opening holdings, which is exactly the comparison section 2.4 forbids."""
    with pytest.raises(ValueError, match="uniform_access"):
        NetworkSpec(uniform_access=True, shortcut_rate=0.5)
    NetworkSpec(uniform_access=True, shortcut_rate=0.0)
