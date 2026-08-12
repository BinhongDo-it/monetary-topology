"""Tests for the B5 loader: parsing, the collapse, and the no-double-count guard.

**The retriever and the loader are the only parts of stage B5 whose bugs are
silent.** A wrong cycle sum fails against its closed form and criterion B5-1
catches it. A misread decimal separator, or a panel that counts every date
twice, produces something internally consistent that passes every downstream
check and answers a different question. `PROJECT_PLAN.md` §11.2 is the instance
that already cost this project a headline number.

The groups are:

1. the number format, including the two wrong readings a naive parser produces
2. the schema assertions, which must raise rather than shift columns
3. the geometric mid, because an arithmetic one is `MEASUREMENT.md` §3
4. the collapse, which is a registered rule and not a convenience
5. the anomaly scan, which must flag and must not change anything
6. **the loader, whose single job is that no date is counted twice**

Nothing here makes a network request.
"""

from __future__ import annotations

import json
import math
from datetime import date

import pytest

from monetary_topology.parallel_rates import (
    JUMP_THRESHOLD,
    MAX_GAP_DAYS,
    POST_WINDOW,
    PRE_WINDOW,
    SERIES,
    TWO_SIDED_KEYS,
    VALID_NAME,
    OverlappingChunks,
    collapse_to_daily,
    coverage,
    in_window,
    is_superseded,
    load_panel,
    load_series,
    mid_of,
    pair_dates,
    parse_number,
    parse_rows,
    scan_anomalies,
    within_day_dispersion,
)

TWO_SIDED = ("Compra", "Venta")
ONE_SIDED = ("Referencia",)


# ---------------------------------------------------------------- number format


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("1.071,36", 1071.36),
        ("1071,36", 1071.36),
        ("57,25", 57.25),
        ("1.234.567,89", 1234567.89),
    ],
)
def test_comma_decimal_is_read_as_a_decimal(token, expected):
    assert parse_number(token) == pytest.approx(expected)


@pytest.mark.parametrize(
    "token",
    ["1071.36", "1,071.36", "1071", "", "n/d", "abc"],
)
def test_a_token_in_any_other_format_raises(token):
    """**Raises rather than returning a sentinel.**

    A quote that cannot be read is not a missing quote. It is evidence that the
    endpoint's format changed, and the one thing that must not happen is for the
    run to continue with a plausible-looking number.
    """
    with pytest.raises(ValueError):
        parse_number(token)


def test_the_hundredfold_error_is_caught_at_the_2019_end_of_the_window():
    """A plausibility band would not catch this, which is why there is not one.

    In September 2019 the peso was near sixty. A parser that strips the comma
    reads ``57,25`` as ``5725``, which sits inside any band loose enough to admit
    the 2026 end of the window, where levels are in the thousands. The format
    regex rejects the input instead of judging the output.
    """
    assert parse_number("57,25") == pytest.approx(57.25)
    with pytest.raises(ValueError):
        parse_number("5725")


# ---------------------------------------------------------------------- schema


def test_rows_parse_and_sort_by_date():
    payload = [
        ["Fecha", "Compra", "Venta"],
        ["24/04/2025", "1.070,00", "1.124,00"],
        ["22/04/2025", "1.071,36", "1.125,54"],
    ]
    rows = parse_rows(payload, TWO_SIDED)
    assert [r["date"] for r in rows] == ["2025-04-22", "2025-04-24"]
    assert rows[0]["compra"] == pytest.approx(1071.36)


def test_a_renamed_column_raises_instead_of_shifting_values():
    """The failure this prevents is the one that does not look like a failure.

    Located positionally, a renamed or reordered column moves every value one
    place and the series still parses, is still monotone, and is still wrong.
    ``PROJECT_PLAN.md`` §11.4 records the underscore-for-hyphen version: a column
    name that silently dropped.
    """
    payload = [["Fecha", "Compra", "Vta"], ["22/04/2025", "1,0", "2,0"]]
    with pytest.raises(ValueError, match="Venta"):
        parse_rows(payload, TWO_SIDED)


def test_a_changed_date_format_raises():
    with pytest.raises(ValueError, match="not"):
        parse_rows([["Fecha", "Referencia"], ["2025-04-22", "1.100,00"]], ONE_SIDED)


def test_a_renamed_first_column_raises():
    with pytest.raises(ValueError, match="Fecha"):
        parse_rows([["Date", "Referencia"], ["22/04/2025", "1.100,00"]], ONE_SIDED)


@pytest.mark.parametrize("payload", [[], {}, "x"])
def test_a_malformed_response_raises(payload):
    with pytest.raises(ValueError):
        parse_rows(payload, ONE_SIDED)


def test_a_header_with_no_rows_is_empty_rather_than_an_error():
    """A range that predates a series is answered, not failed.

    MEP begins in March 2020, so the 2019 half of the window is legitimately
    empty. Raising here made the fetcher retry forever something that will never
    arrive -- the same shape as ``fetch_hmda.py`` judging every complete file
    truncated (``PROJECT_PLAN.md`` §11.3): the script's own convention mistaken
    for evidence about the data.
    """
    assert parse_rows([["Fecha", "Referencia"]], ONE_SIDED) == []


# ------------------------------------------------------------------------- mid


def test_the_mid_is_geometric_and_not_arithmetic():
    row = {"compra": 1000.0, "venta": 1440.0}
    assert mid_of(row, TWO_SIDED) == pytest.approx(1200.0)
    assert mid_of(row, TWO_SIDED) != pytest.approx(1220.0)


def test_the_geometric_mid_makes_the_friction_term_symmetric():
    """``S + S'`` must not depend on which side of the quote is called the mid.

    With ``mid = sqrt(bid*ask)``, ``log(bid/mid) = -log(ask/mid)`` exactly, which
    is what makes ``omega-bar`` half the log spread and lets it cancel out of the
    headline. An arithmetic mid breaks the identity and leaks spread into the
    index part -- the exact mixing ``b4`` §5.1 exists to prevent.
    """
    bid, ask = 1180.0, 1240.0
    mid = mid_of({"compra": bid, "venta": ask}, TWO_SIDED)
    assert math.log(bid / mid) == pytest.approx(-math.log(ask / mid), abs=1e-12)


# -------------------------------------------------------------------- collapse


def _rows(pairs):
    return [{"date": d, "referencia": v} for d, v in pairs]


def test_a_series_with_one_row_per_date_is_unchanged():
    rows = _rows([("2025-01-01", 1000.0), ("2025-01-02", 1010.0)])
    assert collapse_to_daily(rows, ONE_SIDED) == rows


def test_the_median_row_survives_a_contaminated_date():
    """The 21 August 2024 instance, which is why the rule is the median.

    ``dolar/oficial`` returns three rows for that date, one at a level the peso
    last saw in mid-2023. The mean is 736 and belongs to no market.
    """
    rows = _rows([
        ("2024-08-21", 954.12), ("2024-08-21", 300.76), ("2024-08-21", 953.17),
    ])
    daily = collapse_to_daily(rows, ONE_SIDED)
    assert len(daily) == 1
    assert daily[0]["referencia"] == pytest.approx(953.17)


def test_an_even_count_takes_the_lower_median_deterministically():
    """Fixed so the rule does not depend on sort stability.

    A tie-break inherited from the order the endpoint happened to return is a
    rule nobody registered.
    """
    rows = _rows([("2025-01-01", v) for v in (1000.0, 1010.0, 1020.0, 1030.0)])
    assert collapse_to_daily(rows, ONE_SIDED)[0]["referencia"] == pytest.approx(1010.0)


def test_the_collapse_selects_a_whole_row_so_bid_and_ask_stay_paired():
    """**The registered reason for selecting rather than averaging.**

    ``S + S'`` is ``log(bid/ask)`` from one quote. A median bid paired with a
    median ask is a quote nobody published, and the spread of a manufactured
    quote is not a market's spread.
    """
    rows = [
        {"date": "2025-01-01", "compra": 1180.0, "venta": 1200.0},
        {"date": "2025-01-01", "compra": 1000.0, "venta": 1500.0},
        {"date": "2025-01-01", "compra": 1195.0, "venta": 1215.0},
    ]
    daily = collapse_to_daily(rows, TWO_SIDED)
    assert len(daily) == 1
    assert daily[0] in rows
    assert daily[0]["compra"] != 1000.0


def test_the_collapse_changes_nothing_in_the_input():
    rows = _rows([("2025-01-01", 1000.0), ("2025-01-01", 900.0)])
    before = [dict(r) for r in rows]
    collapse_to_daily(rows, ONE_SIDED)
    assert rows == before


def test_dispersion_reports_only_dates_carrying_more_than_one_row():
    rows = _rows([
        ("2025-01-01", 1000.0), ("2025-01-02", 1000.0), ("2025-01-02", 1100.0),
    ])
    out = within_day_dispersion(rows, ONE_SIDED)
    assert [d["date"] for d in out] == ["2025-01-02"]
    assert out[0]["log_range"] == pytest.approx(math.log(1.1), abs=1e-6)


# --------------------------------------------------------------------- anomaly


def test_a_quiet_series_flags_nothing():
    rows = _rows([(f"2025-01-0{i}", 1000.0 * (1.01**i)) for i in range(1, 6)])
    assert scan_anomalies(rows, ONE_SIDED) == []


def test_within_day_dispersion_is_not_reported_as_a_day_over_day_jump():
    """**A guard bug the first real run exposed.**

    Run on uncollapsed rows, the scan produced findings whose ``previous_date``
    equalled their own ``date``. ``PROJECT_PLAN.md`` §11.11 rule 2: a guard must
    compare the quantity that is actually reported, and here that is daily.
    """
    rows = _rows([
        ("2024-08-20", 953.00),
        ("2024-08-21", 954.12), ("2024-08-21", 300.76), ("2024-08-21", 953.17),
        ("2024-08-22", 955.00),
    ])
    assert scan_anomalies(rows, ONE_SIDED) == []


def test_the_known_23_april_2025_instance_is_flagged():
    """The instance ``b5_orphan_availability.md`` §7.6b describes.

    Both transitions exceed the threshold, so both are recorded: the anomaly is
    the day, and the scan is not asked to decide which edge is the real one. It
    is not asked to decide anything.
    """
    rows = _rows([
        ("2025-04-22", 1098.12), ("2025-04-23", 1291.69), ("2025-04-24", 1096.67),
    ])
    flagged = scan_anomalies(rows, ONE_SIDED)
    assert [f["date"] for f in flagged] == ["2025-04-23", "2025-04-24"]


def test_the_scan_changes_nothing():
    """**The registered policy, as a test.**

    ``b5_orphan_prereg.md`` §10: a flagged row keeps its value and stays in the
    series. Criterion B5-10 computes the headline with and without the flagged
    rows, which is only possible if the rows are still there.
    """
    rows = _rows([
        ("2025-04-22", 1098.12), ("2025-04-23", 1291.69), ("2025-04-24", 1096.67),
    ])
    before = [dict(r) for r in rows]
    scan_anomalies(rows, ONE_SIDED)
    assert rows == before


def test_a_hole_in_the_series_is_not_reported_as_a_jump():
    """**The other guard bug.** A gap is a fact about the retrieval."""
    rows = _rows([("2024-12-30", 1170.41), ("2026-01-01", 1480.74)])
    flagged = scan_anomalies(rows, ONE_SIDED)
    assert len(flagged) == 1
    assert flagged[0]["reason"].startswith("gap in the series")
    assert "log_change" not in flagged[0]


def test_a_long_weekend_is_still_compared():
    """The gap rule must not silence real jumps across ordinary calendar gaps.

    The 14 August 2023 devaluation sits across a Friday-to-Monday break, and it
    is one of the largest genuine moves in the window. A gap rule tight enough to
    skip it would be the failure it was written to prevent, in reverse.
    """
    rows = _rows([("2023-08-11", 294.97), ("2023-08-14", 361.15)])
    flagged = scan_anomalies(rows, ONE_SIDED)
    assert flagged[0]["reason"].startswith("one-day log-mid change")
    assert flagged[0]["gap_days"] == 3


def test_the_thresholds_are_the_registered_ones():
    """Pinned so that changing one requires editing a test and a document.

    A pre-registered constant that only lives in the code it governs is not
    pre-registered.
    """
    assert JUMP_THRESHOLD == 0.10
    assert MAX_GAP_DAYS == 7


# ---------------------------------------------------------------------- naming


def test_the_three_naming_schemes_are_distinguishable():
    whole = VALID_NAME.match("ambito_mep_2024.json")
    assert whole.group("year") == "2024" and whole.group("half") is None
    assert VALID_NAME.match("ambito_mep_2024H1.json").group("half") == "H1"
    piece = VALID_NAME.match("ambito_mep_2025-08-13_2025-08-14.json")
    assert piece.group("start") == "2025-08-13"
    assert piece.group("series") == "mep"


@pytest.mark.parametrize(
    "name",
    [
        "ambito_oficial_2025H3.json",
        "ambito_oficial_2025H1.json.expired.1",
        "ambito_blue_2025H1.json",
        "ambito_ccl_2025-08-13.json",
        "scratch.json",
    ],
)
def test_a_non_conforming_name_is_not_recognised(name):
    """``VALID_NAME`` is why nothing ever has to be deleted.

    ``PROJECT_PLAN.md`` §11.1: the loader recognises what it should read, so a
    stray file is left in place rather than removed.
    """
    assert not VALID_NAME.match(name)


def test_only_the_whole_year_scheme_counts_as_superseded():
    assert is_superseded("ambito_mep_2024.json")
    assert not is_superseded("ambito_mep_2024H1.json")
    assert not is_superseded("ambito_mep_2025-08-13_2025-08-14.json")


def test_the_two_sided_keys_are_exactly_the_ones_with_a_bid_and_an_ask():
    """The friction column exists for oficial and blue and for nothing else.

    Stated as data so that a criterion cannot quietly ask for a friction term
    that does not exist. MEP is a ratio of two bond prices and has no native
    two-sided quote (``b5_orphan_prereg.md`` §3.3).
    """
    assert TWO_SIDED_KEYS == {"oficial", "informal"}
    assert SERIES["ccl"][0] == "dolarrava/cl"


# ---------------------------------------------------------------------- loader


def _write(tmp_path, name, rows):
    payload = [["Fecha", "Referencia"]] + [
        [d, f"{v:.2f}".replace(".", ",")] for d, v in rows
    ]
    (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")


def test_the_loader_reads_half_year_and_bisected_files_together(tmp_path):
    _write(tmp_path, "ambito_ccl_2025H1.json", [("02/01/2025", 1162.12)])
    _write(tmp_path, "ambito_ccl_2025-07-01_2025-07-23.json",
           [("01/07/2025", 1233.08)])
    rows = load_series(tmp_path, "ccl")
    assert [r["date"] for r in rows] == ["2025-01-02", "2025-07-01"]


def test_the_loader_ignores_the_superseded_whole_year_files(tmp_path):
    """**This is the guard, and the failure it prevents is invisible.**

    The whole-year file covers the same span as the half-year files that
    replaced it. Reading both would return every date from 2020 to 2026 twice,
    and a duplicated panel changes no premium, no ratio and no sign -- only the
    counts, which are the one thing nobody checks by eye. So the duplicate is
    not silently dropped either: it is not read at all, and a genuine overlap
    raises.
    """
    _write(tmp_path, "ambito_ccl_2025H1.json", [("02/01/2025", 1162.12)])
    _write(tmp_path, "ambito_ccl_2025.json", [("02/01/2025", 1162.12)])
    rows = load_series(tmp_path, "ccl")
    assert [r["date"] for r in rows] == ["2025-01-02"]


def test_two_current_files_sharing_a_date_raise(tmp_path):
    """A real overlap is an error, not something to silently de-duplicate.

    Silently keeping one would hide a bisection that produced overlapping
    ranges, which is a bug in the retriever that this loader is downstream of.
    """
    _write(tmp_path, "ambito_ccl_2025-07-01_2025-07-23.json",
           [("01/07/2025", 1233.08)])
    _write(tmp_path, "ambito_ccl_2025-07-20_2025-07-31.json",
           [("01/07/2025", 1233.08)])
    with pytest.raises(OverlappingChunks, match="2025-07-01"):
        load_series(tmp_path, "ccl")


def test_an_unrecognised_file_is_left_alone_rather_than_read_or_removed(tmp_path):
    _write(tmp_path, "ambito_ccl_2025H1.json", [("02/01/2025", 1162.12)])
    (tmp_path / "ambito_ccl_notes.txt").write_text("scratch", encoding="utf-8")
    (tmp_path / "ambito_ccl_2025H1.json.expired.1").write_text("[]", encoding="utf-8")
    assert len(load_series(tmp_path, "ccl")) == 1
    assert (tmp_path / "ambito_ccl_notes.txt").exists()
    assert (tmp_path / "ambito_ccl_2025H1.json.expired.1").exists()


def test_an_unknown_series_key_raises(tmp_path):
    with pytest.raises(KeyError):
        load_series(tmp_path, "blue")


def test_pair_dates_is_the_intersection_and_never_fills_a_gap(tmp_path):
    """``b5_orphan_prereg.md`` §7: no imputation, no forward fill.

    A forward-filled quote manufactures a day on which two classes agreed, and
    that is the quantity in dispute.
    """
    _write(tmp_path, "ambito_ccl_2025H1.json",
           [("02/01/2025", 1160.0), ("03/01/2025", 1161.0)])
    _write(tmp_path, "ambito_mep_2025H1.json",
           [("03/01/2025", 1150.0), ("06/01/2025", 1152.0)])
    panel = load_panel(tmp_path, ("ccl", "mep"))
    assert pair_dates(panel, "ccl", "mep") == ["2025-01-03"]


def test_pair_dates_on_a_series_that_was_not_loaded_raises(tmp_path):
    _write(tmp_path, "ambito_ccl_2025H1.json", [("02/01/2025", 1160.0)])
    panel = load_panel(tmp_path, ("ccl",))
    with pytest.raises(KeyError):
        pair_dates(panel, "ccl", "mep")


def test_the_windows_do_not_overlap_and_exclude_the_intervention_date():
    assert PRE_WINDOW[1] < date(2025, 4, 14) < POST_WINDOW[0]
    assert in_window(["2025-04-14"], PRE_WINDOW) == []
    assert in_window(["2025-04-14"], POST_WINDOW) == []


def test_coverage_reports_per_pair_and_says_where_friction_exists(tmp_path):
    """The table §7 requires beside every result, from the loader that produced it.

    Counted separately it would be a second implementation of the date filter,
    and the two would drift.
    """
    _write(tmp_path, "ambito_ccl_2025H1.json", [("02/01/2025", 1160.0)])
    _write(tmp_path, "ambito_mep_2025H1.json", [("02/01/2025", 1150.0)])
    out = coverage(load_panel(tmp_path, ("ccl", "mep")))
    assert out["series"]["ccl"]["dates"] == 1
    assert out["pairs"]["ccl-mep"]["dates"] == 1
    assert out["pairs"]["ccl-mep"]["friction_available"] is False


# --------------------------------------------------- B5-8's treated/control split


def test_a_pair_is_treated_exactly_when_it_contains_the_class_whose_rule_was_deleted():
    """``b5_orphan_prereg.md`` §3.2b.

    On 14 April 2025 the rule that was deleted was **oficial's** USD 200 monthly
    cap. MEP's and CCL's eligibility was a brokerage account before and after,
    and blue's was never rule-bound at all.
    """
    from monetary_topology.parallel_rates import TREATED_CLASS, pair_group

    assert TREATED_CLASS == "oficial"
    for other in ("informal", "mep", "ccl"):
        assert pair_group("oficial", other) == "treated"
        assert pair_group(other, "oficial") == "treated"
    assert pair_group("informal", "mep") == "control"
    assert pair_group("mep", "ccl") == "control"
    assert pair_group("informal", "ccl") == "control"


def test_the_oficial_friction_source_is_recorded_as_absent_rather_than_pending():
    """Three candidates were audited and all three failed (§3.2a).

    ``None`` here is a finding, not a to-do. A later reader who fills it in
    without redoing the audit would reinstate the source §3.2 rejected.
    """
    from monetary_topology.parallel_rates import FRICTION_SOURCE

    assert FRICTION_SOURCE["oficial"] is None
    assert FRICTION_SOURCE["informal"] == "ambito"
    assert FRICTION_SOURCE["mep"] is None and FRICTION_SOURCE["ccl"] is None
