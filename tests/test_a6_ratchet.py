"""Unit tests for the frontier ratchet. Registered in ``docs/a6_siphon_cost.md``.

Two of these are criteria rather than ordinary tests.

**A6-7, the reduction guard.** ``A6RatchetModel`` under a default ``RatchetSpec``
must be bit-identical to ``A6Model``. The comparison runs both classes in one
process, so it is a statement about two code paths and cannot be broken by a
difference between two machines. What is here is a **fast subset**: two seeds,
two rates, a hundred and fifty rounds. The registered scope, eight cells by five
seeds by four rates by three hundred rounds, runs as the startup gate of
``experiments/a6_ratchet.py`` and refuses to let the experiment continue.

**A6-8, the fixed point.** The two state equations must settle where section 12.2
says they do, and the within-round ordering is what decides that, so the ordering
is pinned by a test rather than by a comment.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from monetary_topology.config import MonetaryAuthority
from monetary_topology.network import NetworkConfig, NetworkSpec
from monetary_topology.redistribution import (
    SHAPES,
    A6Config,
    A6Model,
    A6RatchetModel,
    FiscalSpec,
    RatchetSpec,
    open_band,
    run_a6,
)

# --------------------------------------------------------------------------
# the spec
# --------------------------------------------------------------------------


def test_default_spec_is_the_reduction_point():
    """A default ratchet is today's model, which is what A6-7 reduces to."""
    spec = RatchetSpec()
    assert spec.absorption == 0.0
    assert spec.decay == 0.0
    assert spec.shape == "clip"
    assert spec.is_reduction


@pytest.mark.parametrize(
    "kwargs",
    [
        {"absorption": -0.1},
        {"absorption": 1.5},
        {"decay": -0.1},
        {"decay": 1.0},
        {"shape": "linear"},
    ],
)
def test_spec_rejects_out_of_range(kwargs):
    with pytest.raises(ValueError):
        RatchetSpec(**kwargs)


@pytest.mark.parametrize("shape", ["exp", "hill"])
def test_smooth_shapes_are_not_the_reduction(shape):
    assert not RatchetSpec(shape=shape).is_reduction


# --------------------------------------------------------------------------
# g
# --------------------------------------------------------------------------


def test_clip_is_exactly_the_wall_the_code_has_today():
    g = SHAPES["clip"]
    for x in (0.0, 1e-9, 0.3, 0.999, 1.0, 1.0000001, 5.0, 1e12):
        assert g(x) == min(1.0, x)


@pytest.mark.parametrize("name", ["clip", "exp", "hill"])
def test_every_shape_has_unit_slope_at_the_origin(name):
    """The first tax point must buy the same thing under all three.

    That is what makes the arms comparable where the arm is small and confines
    the difference between the shapes to saturation, which is section 13.3's
    reason for choosing these two smooth shapes rather than any others.
    """
    g = SHAPES[name]
    assert g(0.0) == 0.0
    for h in (1e-6, 1e-7, 1e-8):
        assert g(h) / h == pytest.approx(1.0, rel=1e-5)


@pytest.mark.parametrize("name", ["clip", "exp", "hill"])
def test_every_shape_is_bounded_and_non_decreasing(name):
    g = SHAPES[name]
    xs = np.concatenate([np.linspace(0.0, 5.0, 200), np.logspace(0.7, 6, 60)])
    ys = np.array([g(float(x)) for x in xs])
    assert np.all(ys >= 0.0)
    assert np.all(ys <= 1.0)
    assert np.all(np.diff(ys) >= 0.0)


def test_where_each_shape_becomes_the_wall():
    """Both smooth shapes do reach exactly one, at very different arguments.

    In real arithmetic neither ever seals the leak. In float64 both do, and the
    crossovers are what section 13.3's argument actually rests on: **`exp`
    becomes the wall at `x >= 37.43`** and `hill` not until `x >= 1.2e16`,
    which nothing on the registered grid reaches. So section 9.2's collapse
    channel stays open under `exp` and is closed by construction under `hill`,
    which is why `exp` is the default and `hill` the axis.

    This is mechanism and not an artefact of the arithmetic. At the crossover
    the surviving leak is already below one part in `1e16`, so a route weight
    carrying it is below one ulp of the weights beside it and the layer is
    starved whether or not the last bit rounds away.
    """
    assert SHAPES["clip"](1.0) == 1.0

    assert SHAPES["exp"](37.0) < 1.0
    assert SHAPES["exp"](37.5) == 1.0
    assert SHAPES["hill"](1e6) < 1.0
    assert SHAPES["hill"](1e15) < 1.0

    # The separation across the middle of the grid, which is the range
    # section 13.3 quotes.
    assert 1.0 - SHAPES["exp"](5.0) == pytest.approx(0.0067, abs=1e-4)
    assert 1.0 - SHAPES["hill"](5.0) == pytest.approx(0.1667, abs=1e-4)
    assert 1.0 - SHAPES["exp"](34.0) == pytest.approx(1.7e-15, rel=0.1)
    assert 1.0 - SHAPES["hill"](34.0) == pytest.approx(0.0286, abs=1e-4)


# --------------------------------------------------------------------------
# A6-8: the fixed point, and the ordering that decides where it is
# --------------------------------------------------------------------------


def bench(absorption: float, injection: float, rounds: int) -> float:
    """The two state equations and nothing else, in the model's own order."""
    built = baseline = 0.0
    for _ in range(rounds):
        baseline += absorption * (built - baseline)
        built += injection
    return built - baseline


@pytest.mark.parametrize("absorption", [1e-3, 1e-2, 1e-1])
@pytest.mark.parametrize("injection", [1.0, 0.0034, 250.0])
def test_gap_settles_at_injection_over_absorption(absorption, injection):
    """A6-8. ``K - B -> I / λ``, which is section 12.2's fixed point."""
    rounds = int(20 * 9 / absorption) + 1000
    gap = bench(absorption, injection, rounds)
    assert gap == pytest.approx(injection / absorption, rel=1e-9)


def test_absorbing_before_building_is_what_puts_the_fixed_point_there():
    """The within-round order is load-bearing and is pinned here.

    Absorbing after the build instead settles at ``I·(1−λ)/λ``, which agrees to
    first order and is ten percent low at the top of the registered grid. The
    model absorbs first, because what was built this instant cannot already be
    taken for granted.
    """
    absorption, injection, rounds = 0.1, 1.0, 5000

    built = baseline = 0.0
    for _ in range(rounds):
        built += injection
        baseline += absorption * (built - baseline)
    other = built - baseline

    assert bench(absorption, injection, rounds) == pytest.approx(
        injection / absorption, rel=1e-9
    )
    assert other == pytest.approx(
        injection * (1.0 - absorption) / absorption, rel=1e-9
    )
    assert other != pytest.approx(injection / absorption, rel=1e-3)


# --------------------------------------------------------------------------
# A6-7: the reduction guard
# --------------------------------------------------------------------------


def config_for(
    seed: int,
    rounds: int,
    access: bool,
    fair: bool,
    channel: str,
    rate: float,
    ratchet: RatchetSpec | None = None,
) -> A6Config:
    """One cell of section 4's factorial, at one levy rate."""
    return A6Config(
        fiscal=FiscalSpec(channel=channel, fair_retention=fair, rate=rate),
        network=NetworkConfig(
            spec=NetworkSpec(seed=seed, uniform_access=not access),
            seed=seed,
            rounds=rounds,
            authority=MonetaryAuthority(rule="none"),
        ),
        ratchet=ratchet or RatchetSpec(),
    )


@pytest.mark.parametrize(
    ("access", "fair", "channel"),
    list(itertools.product((True, False), (True, False),
                           ("transfer", "infrastructure"))),
)
@pytest.mark.parametrize("rate", [0.0, 0.06])
def test_reduction_guard_is_bitwise(access, fair, channel, rate):
    """A6-7, fast subset. Not ``allclose``: identical bits or nothing."""
    for seed in range(2):
        cfg = config_for(seed, 150, access, fair, channel, rate)
        base, base_h = run_a6(cfg)
        ratchet, ratchet_h = run_a6(cfg, model_cls=A6RatchetModel)

        assert np.array_equal(
            base_h.effective_support, ratchet_h.effective_support
        )
        assert np.array_equal(base_h.holdings, ratchet_h.holdings)
        assert np.array_equal(base_h.total_volume, ratchet_h.total_volume)
        assert base.leak_factor == ratchet.leak_factor
        assert base.invested == ratchet.invested
        assert np.array_equal(
            np.asarray(base.palma_history), np.asarray(ratchet.palma_history)
        )


def test_reduction_leaves_the_baseline_at_zero_and_the_stock_on_invested():
    """With ``λ = 0`` the gap *is* cumulative investment, bit for bit.

    That identity is why the reduction holds at all: the argument of ``g``
    becomes the same expression the old line computed.
    """
    cfg = config_for(0, 150, True, True, "infrastructure", 0.06)
    model, _ = run_a6(cfg, model_cls=A6RatchetModel)
    assert model.B == 0.0
    assert model.K == model.invested
    assert model.gap_history[-1] == model.invested


def test_a_shape_change_alone_moves_the_answer():
    """A guard on the guard: the arms must not be silently identical.

    If ``exp`` and ``clip`` produced the same trajectory, the reduction test
    above would pass for a reason that has nothing to do with the reduction.
    """
    cfg = config_for(0, 150, True, True, "infrastructure", 0.06)
    _, clipped = run_a6(cfg, model_cls=A6RatchetModel)
    smooth_cfg = config_for(
        0, 150, True, True, "infrastructure", 0.06,
        ratchet=RatchetSpec(shape="exp"),
    )
    _, smooth = run_a6(smooth_cfg, model_cls=A6RatchetModel)
    assert not np.array_equal(
        clipped.effective_support, smooth.effective_support
    )


# --------------------------------------------------------------------------
# the feedback the ratchet exists to create
# --------------------------------------------------------------------------


def test_the_baseline_keeps_absorbing_when_the_levy_collects_nothing():
    """A starved financial layer must not freeze the arm.

    This is the loop the ratchet is adopted for: no levy means no building,
    the baseline catches up regardless, the gap shrinks, the leak reopens and
    the layer refills. Returning early on an empty levy would break it and
    would make A6-9 fail for a reason in the code rather than in the mechanism.
    """
    cfg = config_for(
        0, 10, True, True, "infrastructure", 0.06,
        ratchet=RatchetSpec(absorption=0.1, shape="exp"),
    )
    model = A6RatchetModel(cfg)
    # Three opening stocks of building, so the gap sits where ``g`` still has
    # room to move. Picking an absolute number instead would put ``x`` far
    # enough out that both rounds underflow to a sealed leak and the test would
    # compare two zeros.
    model.K = 3.0 * model._opening_claims
    model.B = 0.0
    model.holdings[model._l1_idx] = 0.0
    model._post_round(0)
    first_gap, first_leak = model.gap_history[-1], model.leak_history[-1]
    model.holdings[model._l1_idx] = 0.0
    model._post_round(1)

    assert model.B > 0.0
    assert model.gap_history[-1] < first_gap
    assert model.leak_history[-1] > first_leak


def test_decay_floors_the_effect_rather_than_walking_it_back():
    """Section 12.3: the cliff is registered and never simulated.

    Decay can drive the built stock under the absorbed baseline. When it does,
    the effect floors at zero. It does not go negative and it does not retrace
    the marginal curve downward, because that path is not one this stage runs.
    """
    cfg = config_for(
        0, 10, True, True, "infrastructure", 0.06,
        ratchet=RatchetSpec(absorption=0.05, decay=0.9, shape="exp"),
    )
    model = A6RatchetModel(cfg)
    model.K = 1.0
    model.B = 1.0e6
    model.holdings[model._l1_idx] = 0.0
    model._post_round(0)

    assert model.gap_history[-1] == 0.0
    assert model.leak_history[-1] == 1.0


# --------------------------------------------------------------------------
# A6-12's band
# --------------------------------------------------------------------------


def test_open_band_reads_a_contiguous_run():
    grid = (0.0, 0.005, 0.01, 0.02, 0.04)
    verdicts = [True, True, False, False, True]
    assert open_band(grid, verdicts) == (0.01, 0.02, True)


def test_open_band_reports_a_hole():
    """A band with a gap in it is a different object from a band."""
    grid = (0.0, 0.005, 0.01, 0.02, 0.04)
    verdicts = [True, False, True, False, True]
    low, high, contiguous = open_band(grid, verdicts)
    assert (low, high) == (0.005, 0.02)
    assert not contiguous


def test_open_band_with_nothing_open():
    grid = (0.0, 0.005, 0.01)
    assert open_band(grid, [True, True, True]) == (None, None, True)


def test_open_band_admits_a_zero_rate():
    """A flat cell needs no levy at all, and zero is a legitimate low end."""
    grid = (0.0, 0.005)
    assert open_band(grid, [False, False]) == (0.0, 0.005, True)


# --------------------------------------------------------------------------
# the class the guard reduces to is still the one that produced section 9.2
# --------------------------------------------------------------------------


def test_base_model_ignores_the_ratchet_entirely():
    """``A6Model`` must not read ``config.ratchet``, whatever it says.

    If it did, the reduction guard would be comparing two ratchets and would
    pass without establishing anything.
    """
    plain = config_for(0, 150, True, True, "infrastructure", 0.06)
    loud = config_for(
        0, 150, True, True, "infrastructure", 0.06,
        ratchet=RatchetSpec(absorption=0.5, decay=0.5, shape="hill"),
    )
    _, a = run_a6(plain, model_cls=A6Model)
    _, b = run_a6(loud, model_cls=A6Model)
    assert np.array_equal(a.effective_support, b.effective_support)
    assert np.array_equal(a.holdings, b.holdings)
