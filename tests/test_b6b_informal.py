"""B6-B's tests: the registered surface, the guards, and the recorded answers.

Three kinds of test, and the third is the one that has caught things before.

**Definitions are pinned rather than exercised.** ``percentile`` is written out
in ``cuba_informal`` instead of borrowed, so a test states what it returns on a
sample small enough to check by hand. A library that changed its interpolation
would otherwise move a criterion's threshold silently.

**Guards are tested by making them fire.** A guard that has never raised in a
test is a guard nobody has read. Every one of the seven is called twice, once on
the case it exists for and once on the case it must let through.

**The recorded probe answers are used as fixtures.** They were written down
before any criterion existed and the files are still on disk, so
``PROBE_RECORD`` can be checked against the bytes rather than against itself.
``data/raw`` is excluded from the repository, so those tests skip on a fresh
clone and say why instead of passing vacuously.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import pytest

from monetary_topology import cuba_informal as ci
from monetary_topology.cuba_segments import GuardFailed

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

#: The nine externally published official/informal pairs that calibrated
#: B6-15's two thresholds. Sources are in ``b6b_eltoque_prereg.md`` §5.
PUBLISHED_PAIRS = [
    ("2025-12-18", 410, 435), ("2026-01-10", 413, 458),
    ("2026-03-07", 471, 510), ("2026-04-18", 488, 525),
    ("2026-05-29", 514, 572), ("2026-06-21", 565, 695),
    ("2026-07-21", 592, 668), ("2026-08-13", 624, 665),
    ("2026-08-17", 628, 663),
]


# ---------------------------------------------------------------------------
# Definitions, pinned
# ---------------------------------------------------------------------------


def test_the_percentile_is_the_one_written_down_not_a_library_s():
    sample = [1.0, 2.0, 3.0, 4.0]
    got = [ci.percentile(sample, q) for q in (0, 10, 25, 50, 75, 90, 100)]
    assert got == [1.0, 1.3, 1.75, 2.5, 3.25, 3.7, 4.0]


def test_a_one_element_sample_has_one_percentile():
    assert ci.percentile([7.0], 0.0) == 7.0
    assert ci.percentile([7.0], 100.0) == 7.0


def test_an_empty_sample_has_none():
    with pytest.raises(ValueError):
        ci.percentile([], 50.0)


def test_a_percentile_outside_the_range_is_a_mistake_not_a_clamp():
    with pytest.raises(ValueError):
        ci.percentile([1.0, 2.0], 101.0)


def test_the_median_is_the_fiftieth_percentile_of_that_definition():
    assert ci.median([1.0, 2.0, 3.0, 4.0]) == ci.percentile(
        [1.0, 2.0, 3.0, 4.0], 50.0
    )


# ---------------------------------------------------------------------------
# The statistics, against the published record
# ---------------------------------------------------------------------------


def test_a_of_t_reproduces_the_two_ends_of_the_published_record():
    values = [ci.a_statistic(inf, off) for _, off, inf in PUBLISHED_PAIRS]
    assert round(min(values), 4) == 0.0344
    assert round(max(values), 4) == 0.1873


def test_every_published_pair_has_the_informal_dollar_above_the_official_ask():
    values = [ci.a_statistic(inf, off) for _, off, inf in PUBLISHED_PAIRS]
    assert all(v > 0 for v in values)


def test_the_critical_spread_clears_the_registered_threshold():
    values = [ci.a_statistic(inf, off) for _, off, inf in PUBLISHED_PAIRS]
    assert ci.critical_spread(values) > ci.CRITICAL_SPREAD


def test_a_of_t_uses_the_channel_s_ask_and_not_the_headline():
    """``a`` is measured against a price someone will sell at, not the mid."""
    naive = math.log(663) - math.log(628)
    assert ci.a_statistic(663, 628) < naive
    assert round(naive - ci.a_statistic(663, 628), 6) == round(
        math.log(ci.K_VENTA), 6
    )


def test_a_of_t_refuses_a_non_positive_rate():
    with pytest.raises(ValueError):
        ci.a_statistic(0.0, 628)


def test_the_holonomy_is_positive_when_the_havana_euro_is_cheap():
    """2025-12-24: informal cross 1.0909 against a world cross near 1.179."""
    h = ci.holonomy(1.179 * 440, 440, 480, 440)
    assert h > 0
    assert round(h, 4) == 0.0777


def test_the_holonomy_is_near_zero_when_the_two_crosses_agree():
    assert abs(ci.holonomy(1.1510 * 695, 695, 800, 695)) < 0.001


def test_the_holonomy_refuses_a_non_positive_leg():
    with pytest.raises(ValueError):
        ci.holonomy(1.0, 1.0, 1.0, -1.0)


# ---------------------------------------------------------------------------
# The noise floor
# ---------------------------------------------------------------------------


def test_the_tick_is_the_grid_the_publisher_quotes_on():
    assert ci.observed_tick([500.0, 505.0, 515.0, 500.0]) == pytest.approx(5.0)


def test_a_tick_needs_two_distinct_values():
    with pytest.raises(ValueError):
        ci.observed_tick([500.0, 500.0])


def test_the_cross_quantisation_adds_one_tick_from_each_leg():
    assert ci.cross_quantisation(5.0, 500.0, 5.0, 500.0) == pytest.approx(0.02)


def test_the_window_dispersion_is_the_ninetieth_percentile_of_the_log_gap():
    """Ten samples, nine of them zero, so the answer is entirely interpolation.

    The 90th percentile of ten ordered values sits at position ``9 * 0.9 = 8.1``,
    that is one tenth of the way from the ninth value (zero) to the tenth
    (``log(1.1)``). Written this way on purpose: an implementation that took the
    nearest order statistic instead would return zero here, and one that took
    the largest would return ``log(1.1)``. Both are defensible definitions of a
    percentile and both would move B6-13's denominator.
    """
    full = [100.0] * 10
    hour = [100.0] * 9 + [110.0]
    assert ci.window_dispersion(full, hour) == pytest.approx(
        math.log(1.1) * 0.1, rel=1e-9
    )


def test_the_window_dispersion_refuses_unequal_samples():
    with pytest.raises(ValueError):
        ci.window_dispersion([1.0, 2.0], [1.0])


def test_the_floor_is_the_larger_of_the_two_measurements():
    assert ci.noise_floor(0.007, 0.004) == 0.007
    assert ci.noise_floor(0.002, 0.004) == 0.004


def test_the_signal_band_is_four_times_the_floor_and_four_is_b6_a_s():
    assert ci.signal_band(0.007) == pytest.approx(0.028)
    from monetary_topology.cuba_segments import SIGNAL_OVER_NOISE
    assert ci.signal_band(1.0) == SIGNAL_OVER_NOISE


# ---------------------------------------------------------------------------
# The de-noising, and the critical offer ratio
# ---------------------------------------------------------------------------


def test_the_denoising_divides_by_the_root_of_the_ratio_less_one():
    assert ci.denoise(0.01571, 24.0) == pytest.approx(0.01571 / math.sqrt(23.0))


def test_a_ratio_of_one_leaves_nothing_to_divide_by():
    with pytest.raises(ValueError):
        ci.denoise(0.01, 1.0)


def test_the_critical_ratio_is_the_denoising_solved_backwards():
    """At the critical ratio the band equals the effect exactly."""
    dispersion, effect = 0.01571, 0.05595
    r = ci.critical_offer_ratio(dispersion, effect)
    assert ci.signal_band(ci.denoise(dispersion, r)) == pytest.approx(effect)


def test_a_bigger_effect_needs_a_more_concentrated_day_to_break_it():
    d = 0.01571
    assert ci.critical_offer_ratio(d, 0.10) < ci.critical_offer_ratio(d, 0.02)


def test_the_critical_ratio_refuses_a_non_positive_effect():
    with pytest.raises(ValueError):
        ci.critical_offer_ratio(0.01, 0.0)


# ---------------------------------------------------------------------------
# Regimes and the permutation null
# ---------------------------------------------------------------------------


def _dated(signs: str) -> list[tuple[str, int]]:
    """One character per day, ``+`` or ``-``, starting 2021-01-01."""
    from datetime import timedelta
    start = date(2021, 1, 1)
    return [((start + timedelta(days=i)).isoformat(), 1 if c == "+" else -1)
            for i, c in enumerate(signs)]


def test_a_run_shorter_than_the_minimum_is_charged_to_its_neighbour():
    rows = _dated("+" * 40 + "-" * 5 + "+" * 40)
    segments = ci.regimes(rows, min_run=30)
    assert len(segments) == 1
    assert segments[0]["length"] == 85
    assert segments[0]["days_agreeing"] == 80


def test_a_run_at_the_minimum_is_a_regime_of_its_own():
    rows = _dated("+" * 40 + "-" * 30 + "+" * 40)
    segments = ci.regimes(rows, min_run=30)
    assert [r["sign"] for r in segments] == [1, -1, 1]
    assert [r["length"] for r in segments] == [40, 30, 40]


def test_a_clean_series_agrees_with_itself_entirely():
    assert ci.regime_agreement(_dated("+" * 100), 30) == 1.0


def test_the_sweep_reports_the_count_beside_the_agreement():
    rows = _dated(("+" * 20 + "-" * 20) * 5)
    sweep = ci.regime_sweep(rows, (7, 30))
    assert sweep[7]["regimes"] > sweep[30]["regimes"]
    assert sweep[7]["agreement"] >= sweep[30]["agreement"]


def test_the_null_is_degenerate_on_a_marginal_that_cannot_run_thirty_days():
    """The point of the test: a memoryless sign at three in four almost never
    runs a month, so every draw collapses to one regime and the agreement is
    the marginal. A structured series does not."""
    rows = _dated(("+" * 3 + "-") * 200)
    null = ci.regime_null(rows, 30, draws=99, seed=0)
    assert null["null_max"] == pytest.approx(null["null_median"])
    assert null["observed"] == pytest.approx(null["null_median"])


def test_a_blocky_series_beats_the_null_that_its_own_marginal_produces():
    rows = _dated("+" * 600 + "-" * 200)
    null = ci.regime_null(rows, 30, draws=99, seed=0)
    assert null["observed"] == 1.0
    assert null["clears_null_p99"] is True
    assert null["p_value"] == pytest.approx(1 / 100)


def test_the_null_is_seeded_so_the_record_reproduces():
    rows = _dated("+" * 300 + "-" * 100)
    a = ci.regime_null(rows, 30, draws=49, seed=0)
    b = ci.regime_null(rows, 30, draws=49, seed=0)
    assert a == b


def test_the_minimum_run_is_a_month():
    assert ci.REGIME_MIN_RUN == 30


# ---------------------------------------------------------------------------
# B6-13's blocks
# ---------------------------------------------------------------------------


def test_the_blocks_refuse_to_overlap_rather_than_narrowing_to_fit():
    short = [(date(2026, 1, 1), 0.05)] * (2 * ci.BLOCK_DAYS - 1)
    with pytest.raises(GuardFailed):
        ci.block_medians(short)


def test_the_blocks_run_at_exactly_twice_the_block_length():
    dated = [(date.fromordinal(739_000 + n), 0.09 if n < ci.BLOCK_DAYS else 0.01)
             for n in range(2 * ci.BLOCK_DAYS)]
    first, last = ci.block_medians(dated)
    assert first == pytest.approx(0.09)
    assert last == pytest.approx(0.01)


def test_the_blocks_take_the_median_of_the_absolute_value():
    dated = [(date.fromordinal(739_000 + n), -0.09 if n < ci.BLOCK_DAYS else 0.01)
             for n in range(2 * ci.BLOCK_DAYS)]
    first, _ = ci.block_medians(dated)
    assert first == pytest.approx(0.09)


# ---------------------------------------------------------------------------
# The one-sided rule
# ---------------------------------------------------------------------------


def test_a_non_positive_substituted_cycle_is_established():
    verdict = ci.substituted_cycle(-0.01)
    assert verdict["established"] is True
    ci.guard_one_sided(verdict)


def test_a_positive_substituted_cycle_is_not_a_finding():
    verdict = ci.substituted_cycle(0.05)
    assert verdict["established"] is False
    with pytest.raises(GuardFailed):
        ci.guard_one_sided(verdict)


def test_a_zero_cycle_counts_as_non_positive():
    ci.guard_one_sided(ci.substituted_cycle(0.0))


def test_there_is_no_bid_or_ask_on_the_informal_edge():
    for side in ("bid", "ask"):
        with pytest.raises(GuardFailed):
            ci.guard_no_spread(side)


# ---------------------------------------------------------------------------
# The guards
# ---------------------------------------------------------------------------


def test_the_row_key_is_the_request():
    payload = {"date": "2026-08-18"}
    assert ci.guard_row_key(date(2025, 6, 1), payload, "2025-06-01") == "2025-06-01"


def test_the_response_clock_is_refused_as_a_row_key():
    payload = {"date": "2026-08-18"}
    with pytest.raises(GuardFailed) as caught:
        ci.guard_row_key(date(2025, 6, 1), payload, "2026-08-18")
    assert "server clock" in str(caught.value)


def test_a_key_that_is_neither_is_also_refused():
    with pytest.raises(GuardFailed):
        ci.guard_row_key(date(2025, 6, 1), {"date": "2026-08-18"}, "1999-01-01")


def test_an_absent_day_may_not_carry_values():
    with pytest.raises(GuardFailed):
        ci.guard_no_fill({"2021-01-03": {"USD": 41.0}}, {"2021-01-03"})


def test_an_absent_day_that_is_empty_passes():
    ci.guard_no_fill({"2021-01-03": {}}, {"2021-01-03"})


def test_membership_must_exist_for_every_day():
    with pytest.raises(GuardFailed):
        ci.guard_membership({"2021-01-01": {"USD": 40.0}}, {})


def test_membership_must_agree_with_the_values():
    with pytest.raises(GuardFailed):
        ci.guard_membership(
            {"2021-01-01": {"USD": 40.0}}, {"2021-01-01": ("USD", "EUR")}
        )


def test_membership_that_agrees_passes():
    ci.guard_membership({"2021-01-01": {"USD": 40.0}}, {"2021-01-01": ("USD",)})


def test_stored_bytes_that_differ_from_what_arrived_are_caught():
    with pytest.raises(GuardFailed):
        ci.guard_verbatim(b"a", b"b")
    ci.guard_verbatim(b"a", b"a")


# ---------------------------------------------------------------------------
# The request, and what was actually sent
# ---------------------------------------------------------------------------


def test_the_window_is_the_full_day_and_the_strings_are_the_api_s():
    assert ci.day_window(date(2026, 1, 15)) == (
        "2026-01-15 00:00:00", "2026-01-15 23:59:59"
    )


def test_a_fall_back_day_gets_an_hour_less_at_the_top():
    """2021-11-07 in Havana is 25 hours long, and the API refuses it. Learned
    from an HTTP 400 after 310 days of the main pass had already been fetched."""
    assert ci.day_window(date(2021, 11, 7)) == (
        "2021-11-07 00:00:00", "2021-11-07 22:59:59"
    )
    assert ci.window_is_shortened(date(2021, 11, 7)) is True


def test_the_shortened_window_covers_an_ordinary_day_s_worth_of_time():
    assert ci.local_span_seconds(date(2021, 11, 7)) == ci.ORDINARY_SPAN


def test_a_spring_forward_day_keeps_the_window_and_loses_an_hour():
    """This is the kind that does not error. The response is a median over an
    hour less of offers and says nothing about it."""
    assert ci.day_window(date(2026, 3, 8)) == (
        "2026-03-08 00:00:00", "2026-03-08 23:59:59"
    )
    assert ci.window_is_shortened(date(2026, 3, 8)) is False
    assert ci.local_span_seconds(date(2026, 3, 8)) == ci.SPRING_FORWARD_SPAN


def test_one_spring_forward_day_falls_inside_the_b6_a_window():
    """Recorded because it is the only inhomogeneous day any criterion sees."""
    inside = [d for d in ci.HAVANA_SPRING_FORWARD if d >= ci.b6a_window_start()]
    assert inside == [date(2026, 3, 8)]
    assert not [d for d in ci.HAVANA_FALL_BACK if d >= ci.b6a_window_start()]


def test_the_dst_lists_still_agree_with_tzdata():
    """The lists are written out so the constant does not need ``tzdata`` at run
    time. This recomputes them and fails if the zone's history has moved."""
    try:
        from zoneinfo import ZoneInfo
        havana, utc = ZoneInfo("America/Havana"), ZoneInfo("UTC")
    except Exception:  # noqa: BLE001
        pytest.skip("no tzdata on this host; the written-out lists stand")
    from datetime import datetime, timedelta
    long_days, short_days = [], []
    day = ci.TRMI_START
    while day <= date(2026, 8, 18):
        opened = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=havana)
        closed = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=havana)
        elapsed = (closed.astimezone(utc) - opened.astimezone(utc)).total_seconds()
        if elapsed > 24 * 3600:
            long_days.append(day)
        elif elapsed < 23 * 3600:
            short_days.append(day)
        day += timedelta(days=1)
    assert tuple(long_days) == ci.HAVANA_FALL_BACK
    assert tuple(short_days) == ci.HAVANA_SPRING_FORWARD


def test_the_sensitivity_window_is_the_registered_hour():
    assert ci.day_window(date(2026, 1, 15), sensitivity=True) == (
        "2026-01-15 12:00:00", "2026-01-15 12:59:59"
    )


def test_every_recorded_probe_window_is_one_this_builder_produces():
    """The recorded answers correspond to these exact strings and no others."""
    for date_from, date_to in ci.PROBE_RECORD:
        url = ci.trmi_url(date_from, date_to)
        assert url.startswith(ci.ENDPOINT + "?date_from=")
        assert " " not in url
        assert "%20" in url


def test_the_full_day_probe_windows_match_the_builder_exactly():
    for date_from, date_to in ci.PROBE_RECORD:
        if not date_from.endswith("00:00:00"):
            continue
        day = date.fromisoformat(date_from.split(" ")[0])
        assert ci.day_window(day) == (date_from, date_to)


def test_no_probe_window_landed_on_a_day_the_builder_now_shortens():
    """If one had, its recorded answer would be for a window this file no longer
    asks for, and the replay of B6-9 would fail for a reason that is not a
    finding."""
    for date_from, _ in ci.PROBE_RECORD:
        day = date.fromisoformat(date_from.split(" ")[0])
        assert not ci.window_is_shortened(day), date_from


def test_the_sensitivity_dates_are_twelve_fifteenths_of_consecutive_months():
    days = ci.sensitivity_days(date(2026, 8, 17))
    assert len(days) == 12
    assert len(set(days)) == 12
    assert all(d.day == 15 for d in days)
    assert days[0] == date(2025, 8, 15)
    assert days[-1] == date(2026, 7, 15)


def test_the_sensitivity_dates_stop_at_the_last_complete_month():
    assert date(2026, 8, 15) not in ci.sensitivity_days(date(2026, 8, 17))


def test_the_sensitivity_dates_cross_a_year_boundary_correctly():
    """Twelve months ending with January 2026, so the run opens in February
    2025 and not in January 2025. Off by one month in the wrong direction gives
    thirteen months of coverage and a floor measured over a longer stretch than
    the one registered."""
    days = ci.sensitivity_days(date(2026, 2, 3))
    assert days[0] == date(2025, 2, 15)
    assert days[-1] == date(2026, 1, 15)


def test_the_day_list_is_inclusive_at_both_ends():
    days = ci.window_days(date(2026, 1, 1), date(2026, 1, 3))
    assert days == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


def test_the_day_list_refuses_a_backwards_interval():
    with pytest.raises(ValueError):
        ci.window_days(date(2026, 1, 3), date(2026, 1, 1))


def test_the_request_count_is_the_three_passes_added_up():
    end = date(2026, 8, 17)
    assert ci.request_count(ci.TRMI_START, end) == (
        len(ci.window_days(ci.TRMI_START, end))
        + len(ci.sensitivity_days(end))
        + len(ci.PROBE_RECORD)
    )


# ---------------------------------------------------------------------------
# The response
# ---------------------------------------------------------------------------


def test_the_alias_renames_the_euro_and_leaves_everything_else():
    out = ci.rename_alias({"ECU": 500.0, "USD": 440.0, "MLC": 210.0})
    assert out == {"EUR": 500.0, "USD": 440.0, "MLC": 210.0}


def test_the_alias_is_the_only_mapping():
    assert ci.API_ALIAS == {"ECU": "EUR"}


def test_the_digest_does_not_depend_on_key_order():
    assert ci.digest_tasas({"USD": 1.0, "EUR": 2.0}) == ci.digest_tasas(
        {"EUR": 2.0, "USD": 1.0}
    )


def test_the_digest_separates_different_measurements():
    assert ci.digest_tasas({"USD": 1.0}) != ci.digest_tasas({"USD": 1.01})


def test_an_empty_object_is_absence_and_anything_else_is_not():
    assert ci.is_absent({}) is True
    assert ci.is_absent({"USD": 40.0}) is False


def test_the_served_set_is_sorted():
    assert ci.served({"USD": 1.0, "BTC": 2.0, "EUR": 3.0}) == ("BTC", "EUR", "USD")


def test_a_body_without_tasas_is_not_an_empty_day():
    with pytest.raises(KeyError):
        ci.tasas_of({"date": "2026-08-18"})


def test_the_clock_is_named_for_what_it_is():
    stamp = ci.fetched_at(
        {"date": "2026-08-18", "hour": 18, "minutes": 4, "seconds": 56}
    )
    assert stamp == "2026-08-18 18:04:56"


# ---------------------------------------------------------------------------
# Constants that must not drift from B6-A
# ---------------------------------------------------------------------------


def test_the_sell_multiplier_comes_from_the_schedule():
    from monetary_topology.cuba_segments import MARKUP_SCHEDULE
    assert ci.K_VENTA == MARKUP_SCHEDULE[ci.SEGMENT_CHANNEL]["venta"]


def test_the_channel_is_the_one_b6_a_registered():
    """Read out of ``b6_segments.py`` rather than imported, because ``src`` does
    not import from ``experiments`` and the two strings must still agree."""
    source = (ROOT / "experiments" / "b6_segments.py").read_text(encoding="utf-8")
    assert f'SEGMENT_CHANNEL = "{ci.SEGMENT_CHANNEL}"' in source


def test_the_widest_round_trip_is_b6_a_s_number():
    assert round(ci.widest_official_round_trip(), 6) == 0.093896


def test_the_b6_a_window_start_is_not_restated_here():
    from monetary_topology.cuba_segments import WINDOW_START
    assert ci.b6a_window_start() == WINDOW_START


def test_the_registered_and_control_sets_do_not_overlap():
    assert not set(ci.REGISTERED) & set(ci.CONTROL)


def test_the_euro_enters_under_its_renamed_code():
    assert "EUR" in ci.REGISTERED
    assert "ECU" not in ci.REGISTERED


# ---------------------------------------------------------------------------
# The recorded probe answers, against what is on disk
# ---------------------------------------------------------------------------


def _probe_file(name: str) -> Path:
    return RAW / name


PROBE_FILES = {
    ("2025-06-01 00:00:00", "2025-06-01 23:59:59"): "eltoque_probe_past_day.json",
    ("2026-01-15 00:00:00", "2026-01-15 23:59:59"):
        "eltoque_probe_window_day.json",
    ("2026-08-18 00:00:00", "2026-08-18 23:59:59"): "eltoque_probe_today.json",
    ("2018-01-01 00:00:00", "2018-01-01 23:59:59"):
        "eltoque_probe2_far_past_2018.json",
    ("2027-06-01 00:00:00", "2027-06-01 23:59:59"):
        "eltoque_probe2_future_2027.json",
    ("2026-01-16 00:00:00", "2026-01-16 23:59:59"):
        "eltoque_probe2_adjacent_2026_01_16.json",
    ("2026-08-11 00:00:00", "2026-08-11 23:59:59"):
        "eltoque_probe2_known_2026_08_11.json",
    ("2026-01-15 09:00:00", "2026-01-15 09:59:59"):
        "eltoque_probe2_intraday_2026_01_15_09h.json",
    ("2025-09-30 00:00:00", "2025-09-30 23:59:59"):
        "eltoque_probe3_known_2025_09_30.json",
    ("2020-12-31 00:00:00", "2020-12-31 23:59:59"):
        "eltoque_probe3_edge_2020_12_31.json",
    ("2021-01-01 00:00:00", "2021-01-01 23:59:59"):
        "eltoque_probe3_edge_2021_01_01.json",
    ("2021-01-02 00:00:00", "2021-01-02 23:59:59"):
        "eltoque_probe3_edge_2021_01_02.json",
}


@pytest.mark.parametrize("window,name", sorted(PROBE_FILES.items()))
def test_the_recorded_answer_matches_the_body_that_produced_it(window, name):
    path = _probe_file(name)
    if not path.exists():
        pytest.skip(
            f"{name} is under data/raw, which the repository excludes. "
            f"On a fresh clone this fixture is absent and the table in "
            f"cuba_informal.PROBE_RECORD is the only surviving record."
        )
    body = json.loads(path.read_text(encoding="utf-8"))
    assert ci.tasas_of(body) == ci.PROBE_RECORD[window]


def test_every_probe_window_in_the_table_has_a_file_named_for_it():
    assert set(PROBE_FILES) == set(ci.PROBE_RECORD)


def test_the_domain_boundary_is_what_the_table_records():
    """2020-12-31 empty and 2021-01-01 not, which is where ``TRMI_START`` comes
    from. The web page that says the same thing is not what fixed it."""
    before = ci.PROBE_RECORD[("2020-12-31 00:00:00", "2020-12-31 23:59:59")]
    at = ci.PROBE_RECORD[("2021-01-01 00:00:00", "2021-01-01 23:59:59")]
    assert ci.is_absent(before)
    assert not ci.is_absent(at)
    assert ci.TRMI_START == date(2021, 1, 1)


def test_the_known_answers_agree_with_the_probe_record():
    for (day, code), expected in ci.KNOWN_ANSWERS.items():
        window = (f"{day} 00:00:00", f"{day} 23:59:59")
        assert ci.PROBE_RECORD[window][code] == expected


def test_the_euro_identification_rests_on_a_value_and_a_date():
    """``ECU`` is the euro because it reads 500.0 on the day elTOQUE reported the
    euro reaching 500 CUP, not because the code looks like one."""
    window = ("2025-09-30 00:00:00", "2025-09-30 23:59:59")
    assert ci.PROBE_RECORD[window]["ECU"] == 500.0
    assert ci.API_ALIAS["ECU"] == "EUR"


def test_exactly_one_probe_window_was_taken_while_its_day_was_live():
    """2026-08-18 was probed at 18:05 Havana time on 2026-08-18. Every other
    window sampled a day that had already closed, so every other window may be
    replayed for equality and this one may not."""
    assert ci.PROBE_TAKEN_LIVE == {
        ("2026-08-18 00:00:00", "2026-08-18 23:59:59")
    }
    for window in ci.PROBE_RECORD:
        assert ci.probe_is_comparable(window) is (
            window not in ci.PROBE_TAKEN_LIVE
        )


def test_the_live_probe_is_the_latest_window_in_the_record():
    """A probe taken live can only be one taken on the day the probing happened,
    which is the last day any window covers."""
    days = sorted(date.fromisoformat(f.split(" ")[0]) for f, _ in ci.PROBE_RECORD
                  if date.fromisoformat(f.split(" ")[0]) <= date(2026, 8, 18))
    live = {date.fromisoformat(f.split(" ")[0]) for f, _ in ci.PROBE_TAKEN_LIVE}
    assert live == {max(days)}


def test_the_range_refusal_is_recorded_because_it_fixes_the_request_count():
    assert "24 horas" in ci.RANGE_REFUSAL


# ---------------------------------------------------------------------------
# The fetcher, read as source
# ---------------------------------------------------------------------------


FETCHER = (ROOT / "data" / "fetch_eltoque.py").read_text(encoding="utf-8")


def test_the_fetcher_never_keys_a_row_on_the_response_clock():
    for forbidden in ('payload["date"]', "payload['date']", '["date"]]'):
        assert forbidden not in FETCHER, forbidden


def test_the_fetcher_deletes_nothing():
    for forbidden in ("os.remove", "shutil.rmtree", ".unlink(", "os.rmdir"):
        assert forbidden not in FETCHER, forbidden


def test_the_fetcher_reads_the_rate_limit_headers():
    for header in ("x-ratelimit-remaining", "x-ratelimit-reset", "Retry-After"):
        assert header in FETCHER, header


def test_the_fetcher_never_answers_a_429_with_an_immediate_retry():
    """A 429 has been observed carrying ``Retry-After: -11``.

    A clamp on a negative number is an immediate retry wearing a delay's
    clothes, so the backoff comes from a schedule of this file's own whenever
    both headers point into the past.
    """
    assert "max(delay, 1.0)" not in FETCHER
    assert "THROTTLE_FLOOR_SECONDS * (2 ** (attempt - 1))" in FETCHER


def test_the_fetcher_gives_up_after_a_bounded_number_of_429s():
    assert "throttled > THROTTLE_ATTEMPTS" in FETCHER


def test_the_fetcher_reports_a_long_wait_rather_than_sleeping_through_it():
    """The run resumes from disk, so stopping costs one command later, and an
    unannounced hour-long sleep is indistinguishable from a hang."""
    assert "delay > MAX_THROTTLE_WAIT_SECONDS" in FETCHER


def test_the_fetcher_prints_the_limiter_s_own_account_on_a_429():
    """A 429 that does not say what the limiter thinks the state is leaves the
    operator guessing between ten per second and ten per minute."""
    assert "limits(exc.headers)" in FETCHER


def test_the_fetcher_never_prints_the_key():
    body = FETCHER.split("def describe_token")[1].split("\ndef ")[0]
    assert "token[-6:]" in body
    assert "print(f\"{token}" not in FETCHER


def test_the_fetcher_builds_its_url_in_one_place():
    assert FETCHER.count("date_from=") == 0 or "trmi_url(" in FETCHER
    assert "https://tasas.eltoque.com/v1/trmi?" not in FETCHER


def test_the_fetcher_fetches_the_last_complete_day_and_not_today():
    assert "timedelta(days=1)" in FETCHER


def test_the_replay_separates_a_disagreement_from_an_incomparable_window():
    """A live-day sample and a closed-day sample are different statistics, so
    B6-9 compares eleven windows and keeps the twelfth's deltas as a reading."""
    assert "probe_is_comparable(window)" in FETCHER
    assert "live_probe_deltas" in FETCHER
