"""Tests for B5-14 and B5-15, the two guards on B5-8's pre-window.

Two of these matter more than the rest.

`test_b5_15_is_a_strict_comparison_with_no_threshold` is the one that carries the
disclosure in `docs/b5_orphan_prereg.md` §6B.3. B5-15 was written after B5-14
failed and after its quantities had been seen, and the defence offered is that
neither leg contains a band, a fraction or a cutoff, so no parameter existed that
could have been moved to produce the outcome. **If a threshold is ever added to
either leg, that defence evaporates**, and this test is what refuses the change.

`test_the_shared_function_is_the_package_one` pins the move that made B5-14
possible. B5-6 through B5-8 and B5-14 all read `S − S'` for a pair, and a second
copy of that would be a second truth about what the headline quantity is. The
copy in `b5_squares.py` is now an alias, and this test says so out loud.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from monetary_topology.orphan_squares import (
    agent_quotes,
    pair_index_series,
)
from monetary_topology.parallel_rates import (
    DEVALUATION,
    POST_WINDOW,
    PRE_WINDOW,
    PRE_WINDOW_LONG,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    """The experiments are scripts; loaded by path like the rest of the suite."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "experiments" / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pt():
    return _load("b5_parallel_trends")


# ------------------------------------------------------------- registered windows


def test_the_second_rung_is_the_eight_quarters_and_it_encloses_the_devaluation():
    """§6A.3's reason for demoting B5-13's window to the second rung.

    It is not a preference. The eight quarters reach back far enough to enclose
    13 December 2023, across which a linear trend describes nothing, and the
    primary rung is the window B5-8's own ratios are computed on.
    """
    assert PRE_WINDOW_LONG == (date(2023, 4, 14), date(2025, 4, 13))
    assert PRE_WINDOW_LONG[0] <= DEVALUATION <= PRE_WINDOW_LONG[1]
    assert not PRE_WINDOW[0] <= DEVALUATION <= PRE_WINDOW[1]


def test_the_two_windows_are_the_same_length_so_the_horizon_is_twelve_buckets(pt):
    """§6A.4 extrapolates a per-bucket slope across ``HORIZON_BUCKETS``.

    That is only twelve if the post-window is twelve buckets of the primary
    rung's width, which holds because both windows are 365 days. If either
    window is ever changed, this is the arithmetic that breaks first.
    """
    pre_days = (PRE_WINDOW[1] - PRE_WINDOW[0]).days + 1
    post_days = (POST_WINDOW[1] - POST_WINDOW[0]).days + 1
    assert pre_days == post_days == 365
    assert pt.HORIZON_BUCKETS == pt.N_BUCKETS_PRIMARY == 12
    assert pt.N_BUCKETS_LONG == 24


def test_the_band_is_the_factor_this_stage_already_uses(pt):
    """§6A.4. One discipline wherever a magnitude has to clear something."""
    assert pt.PRE_TREND_SHARE == 0.25


# ---------------------------------------------------------------------- the slope


def test_the_slope_is_the_closed_form_and_not_whatever_polyfit_defaults_to(pt):
    """An exact line must return its own slope."""
    assert pt.ols_slope([1.0, 3.0, 5.0, 7.0]) == pytest.approx(2.0)
    assert pt.ols_slope([10.0, 8.0, 6.0]) == pytest.approx(-2.0)
    assert pt.ols_slope([4.0, 4.0, 4.0, 4.0]) == pytest.approx(0.0)


def test_a_slope_is_not_defined_on_fewer_than_three_points(pt):
    """Two points fit exactly with no residual, so they are not evidence."""
    assert np.isnan(pt.ols_slope([]))
    assert np.isnan(pt.ols_slope([1.0]))
    assert np.isnan(pt.ols_slope([1.0, 2.0]))


# --------------------------------------------------------------------- bucketing


def _series(window, per_bucket, n_buckets, fill=None, value=1.0):
    """``per_bucket`` observations in each of the first ``fill`` of ``n_buckets``.

    ``n_buckets`` is the division the code under test will use, and ``fill`` is
    how many of those buckets get dates. Slicing the window into ``fill`` pieces
    instead puts the dates in the wrong buckets entirely, which is the second
    way this helper was wrong.

    The first offset of bucket ``i`` is ``ceil(i · span / n)``, which is the
    inverse of ``bucket_series``'s ``offset · n // span``. Writing it as
    ``i · span // n`` instead is off by one at every boundary, and the resulting
    dates land one bucket early — which is how this helper was wrong first.
    """
    start, end = window
    span = (end - start).days + 1
    out = []
    for index in range(n_buckets if fill is None else fill):
        first = start.toordinal() + -(-index * span // n_buckets)
        for offset in range(per_bucket):
            out.append((date.fromordinal(first + offset).isoformat(), value))
    return out


def test_a_bucket_below_the_date_floor_is_dropped_rather_than_averaged(pt):
    """§6A.3. A month with a handful of quotes does not produce an rms.

    Dropping is not the same as averaging a thin bucket in with the rest, and
    the difference shows up in the slope rather than in a coverage number.
    """
    assert pt.MIN_DATES_PER_BUCKET == 10
    thin = _series(PRE_WINDOW, pt.MIN_DATES_PER_BUCKET - 1, 12)
    block = pt.bucket_series(thin, PRE_WINDOW, 12)
    assert block["buckets_kept"] == []
    assert block["usable"] is False
    assert block["slope"] is None


def test_a_rung_that_keeps_too_few_buckets_is_vacuous_and_not_small(pt):
    """``PROJECT_PLAN.md`` §11.11 rule 1, expressed on this carrier.

    Seven buckets out of twelve is below two thirds, so the rung must refuse to
    return a slope rather than fit one to what survived.
    """
    assert pt.MIN_BUCKET_SHARE == pytest.approx(2.0 / 3.0)
    fat = _series(PRE_WINDOW, pt.MIN_DATES_PER_BUCKET, 12, fill=7)
    block = pt.bucket_series(fat, PRE_WINDOW, 12)
    assert block["buckets_kept"] == [1, 2, 3, 4, 5, 6, 7]
    assert block["minimum_buckets"] == 8
    assert block["usable"] is False


def test_the_bucket_index_map_and_the_kept_list_cannot_drift_apart(pt):
    """``by_index`` is what B5-15 reads the final bucket out of.

    If it ever disagreed with ``buckets_kept``, B5-15 would silently read the
    wrong bucket, which is the kind of failure that returns a number.
    """
    full = _series(PRE_WINDOW, pt.MIN_DATES_PER_BUCKET, 12)
    block = pt.bucket_series(full, PRE_WINDOW, 12)
    assert block["buckets_kept"] == list(range(1, 13))
    assert [int(k) for k in block["by_index"]] == block["buckets_kept"]
    assert list(block["by_index"].values()) == block["rms_per_bucket"]


def test_a_date_outside_the_window_never_lands_in_a_bucket(pt):
    """The window is the filter, not the caller's date list."""
    inside = _series(PRE_WINDOW, pt.MIN_DATES_PER_BUCKET, 12)
    outside = [("2019-09-02", 99.0), ("2026-06-29", 99.0)]
    block = pt.bucket_series(inside + outside, PRE_WINDOW, 12)
    assert sum(block["dates_per_bucket"]) == 12 * pt.MIN_DATES_PER_BUCKET


# ---------------------------------------------------------- direction, §6A.5


def _rung(slope_treated, slope_control):
    return {"slope": slope_treated}, {"slope": slope_control}


def test_a_treated_pair_already_falling_faster_is_the_damaging_direction(pt):
    """§6A.5. Damaging is the treated pair converging faster before the event."""
    treated, control = _rung(-0.05, -0.01)
    out = pt.compare(treated, control, ("mep", "ccl"), collapse=1.0)
    assert out["direction"] == "damaging"
    assert out["delta_slope"] < 0.0


def test_a_treated_pair_diverging_carries_no_band_and_passes(pt):
    """§6A.5. A trend running away from the result cannot manufacture it.

    The share is still reported, and it is large here on purpose: a conservative
    direction passes **whatever its magnitude**, and that is registered rather
    than discovered.
    """
    treated, control = _rung(+0.90, -0.01)
    out = pt.compare(treated, control, ("mep", "ccl"), collapse=1.0)
    assert out["direction"] == "conservative"
    assert out["share_of_collapse"] > pt.PRE_TREND_SHARE
    assert out["passed"] is True


def test_the_damaging_band_is_applied_to_the_share_not_to_the_slope(pt):
    """The quantity tested is the share of the collapse, over the horizon."""
    collapse = 1.0
    inside = 0.9 * pt.PRE_TREND_SHARE * collapse / pt.HORIZON_BUCKETS
    outside = 1.1 * pt.PRE_TREND_SHARE * collapse / pt.HORIZON_BUCKETS
    assert pt.compare(*_rung(-inside, 0.0), ("mep", "ccl"), collapse)["passed"]
    assert not pt.compare(*_rung(-outside, 0.0), ("mep", "ccl"), collapse)["passed"]


def test_a_comparison_without_a_slope_is_vacuous_and_fails(pt):
    """Not a pass by default, and not a zero."""
    out = pt.compare({"slope": None}, {"slope": 0.0}, ("mep", "ccl"), 1.0)
    assert out["vacuous"] is True
    assert out["passed"] is False


# ------------------------------------------------------------------ B5-15, §6B


def _edge(last_pre, post, ratio=None):
    mean = float(np.mean(post))
    return {
        "pair": "x-y",
        "last_pre_bucket": last_pre,
        "post_buckets": post,
        "post_max": max(post),
        "post_mean": mean,
        "ratio": ratio if ratio is not None else last_pre / mean,
        "vacuous": False,
    }


def test_b5_15_is_a_strict_comparison_with_no_threshold(pt):
    """**The test that carries §6B.3's disclosure.**

    B5-15 was written after B5-14 failed and after its quantities had been seen.
    The whole defence is that neither leg contains a band, a fraction or a
    cutoff, so no parameter existed that could have been slid to turn a failure
    into a pass. A tie must therefore fail: a strict ``>`` has no room in it,
    and any margin added later would be a number chosen with the answer in view.
    """
    source = (ROOT / "experiments" / "b5_parallel_trends.py").read_text(
        encoding="utf-8"
    )
    body = source.split("def b5_15_edge_of_window")[1].split("\ndef ")[0]
    assert "PRE_TREND_SHARE" not in body
    assert ">=" not in body and "<=" not in body


def test_leg_a_fails_on_a_tie_because_the_comparison_is_strict(pt, monkeypatch):
    """A premium merely equal to its post-window maximum is not elevated."""
    tie = _edge(0.08, [0.08, 0.04, 0.02])
    controls = [_edge(0.01, [0.5, 0.5, 0.5]) for _ in range(3)]
    monkeypatch.setattr(
        pt, "edge_block",
        lambda _c, _d, pair: tie if pair == pt.TREATED_PAIR else controls.pop(),
    )
    out = pt.b5_15_edge_of_window({}, [])
    assert out["leg_a"]["passed"] is False
    assert out["passed"] is False


def test_leg_b_needs_every_control_and_not_a_majority(pt, monkeypatch):
    """§6B.1: the treated ratio must exceed **every** control's.

    Two out of three is how a control group stops being one.
    """
    treated = _edge(0.4, [0.05, 0.05, 0.05])
    ratios = [0.2, 0.3, 99.0]
    monkeypatch.setattr(
        pt, "edge_block",
        lambda _c, _d, pair: (
            treated if pair == pt.TREATED_PAIR
            else _edge(0.01, [0.5, 0.5, 0.5], ratio=ratios.pop())
        ),
    )
    out = pt.b5_15_edge_of_window({}, [])
    assert out["leg_a"]["passed"] is True
    assert out["leg_b"]["passed"] is False
    assert out["passed"] is False


def test_a_missing_final_pre_bucket_is_vacuous_and_not_a_pass(pt, monkeypatch):
    """§6B.4. The edge of the window is the whole criterion; without it there
    is nothing to compare and ``PROJECT_PLAN.md`` §11.11 rule 1 applies."""
    gone = dict(_edge(0.4, [0.05]), last_pre_bucket=None, vacuous=True)
    monkeypatch.setattr(pt, "edge_block", lambda _c, _d, _p: gone)
    out = pt.b5_15_edge_of_window({}, [])
    assert out["vacuous"] is True
    assert out["passed"] is False


def test_leg_a_is_marked_load_bearing_and_leg_b_is_not(pt, monkeypatch):
    """§6B.2. Leg (b)'s controls were treated again inside the post-window, and
    that widening makes leg (b) easier, so the claim rests on leg (a)."""
    treated = _edge(0.4, [0.05, 0.05, 0.05])
    monkeypatch.setattr(
        pt, "edge_block",
        lambda _c, _d, pair: (
            treated if pair == pt.TREATED_PAIR else _edge(0.01, [0.5, 0.5, 0.5])
        ),
    )
    out = pt.b5_15_edge_of_window({}, [])
    assert out["leg_a"]["load_bearing"] is True
    assert out["leg_b"]["load_bearing"] is False
    assert "September 2025" in out["leg_b"]["disclosed_bias"]


# ------------------------------------------------------------------- the shared
# function, and the gate


def test_the_shared_function_is_the_package_one():
    """B5-8 and B5-14 must read the same ``S − S'``, not two copies of it."""
    squares = _load("b5_squares")
    assert squares.pair_series is pair_index_series
    assert squares.daily_quotes is agent_quotes


def test_the_pair_keys_match_the_ones_b5_8_wrote(pt):
    """The comparison reads B5-8's record by key, so the keys must agree.

    Asserted in the module itself as well; pinned here because a rename of a
    class would break it silently at the dictionary lookup rather than loudly.
    """
    assert pt.pair_key(pt.TREATED_PAIR) == "oficial-informal"
    assert [pt.pair_key(p) for p in pt.CONTROL_PAIRS] == [
        "informal-mep", "informal-ccl", "mep-ccl",
    ]


def test_b5_14_refuses_to_run_when_b5_8_did_not_pass(pt, tmp_path, monkeypatch):
    """§6A.6. The denominator is B5-8's collapse; without it there is no ratio.

    Expressed as a read of B5-8's record rather than as a note, the same way
    ``b5_squares.py`` reads the calibration arm instead of recomputing it.
    """
    broken = tmp_path / "b5_squares.json"
    broken.write_text(
        '{"verdicts": {"B5-8": false}, "pairs": {}}', encoding="utf-8"
    )
    monkeypatch.setattr(pt, "SQUARES", broken)
    with pytest.raises(SystemExit, match="vacuous"):
        pt.collapse_from_b5_8()


def test_the_denominator_is_read_from_b5_8_and_not_recomputed(pt):
    """A floor and a signal computed on different populations is `MEASUREMENT`
    rule 3's failure; the same argument applies to a denominator."""
    collapse, detail = pt.collapse_from_b5_8()
    assert detail["from"].startswith("results/b5_squares.json")
    assert collapse == pytest.approx(detail["rms_pre"] - detail["rms_post"])
    assert collapse > 0.0
