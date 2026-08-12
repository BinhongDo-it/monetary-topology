"""Tests for stage B6-A: the registered constants, the graph, and the guards.

Three of these matter more than the rest.

`test_the_one_sided_bound_is_a_potential_difference_and_not_a_cycle_sum` refuses
the error this stage was written to avoid and committed anyway before it was
caught. There is no closed loop through a frozen segment, so there is no holonomy
to report, and a number produced as one would be an `H⁰` fact wearing an `H¹`
name (`b1_theorem.md` §12.1, `b4_directed_edges.md` §5.2). The test reads the
source of `b6_6c_bounds` and refuses any path by which a cycle sum could get in.

`test_the_ecb_url_is_the_one_that_was_verified` pins a distinction that cost an
HTTP 400: SDMX addresses a series as `/service/data/{flow}/{key}`, while the
response's `KEY` column carries the two joined. They look like one string. If
someone tidies the two constants into one, this test is what refuses it.

`test_the_base_column_is_not_truncated` pins the other thing only real data
showed. The publisher truncates every channel at the last published place,
including the channel whose multiplier is exactly one, and does **not** truncate
the base column the channels are derived from. On 59 of 1 428 published rows the
two differ in the last place, which is what says the truncation is real rather
than a coincidence of rounding.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import date
from pathlib import Path

import pytest

from monetary_topology import directed
from monetary_topology.cuba_segments import (
    BASE_CURRENCY,
    CROSS_BAND,
    CUP,
    CURRENCIES,
    ECB_FLOW,
    ECB_KEY,
    ECB_SERIES,
    MARKUP_SCHEDULE,
    MODELS,
    ONE_WAY_SEGMENTS,
    PUBLISHED_DECIMALS,
    PUBLISHED_ULP,
    SEGMENTS,
    SIGNAL_OVER_NOISE,
    TWO_WAY_SEGMENT,
    USD_POS,
    VALID_XLSX,
    WINDOW_START,
    GuardFailed,
    build_segment_field,
    channel_quote,
    column_multipliers,
    ecb_url,
    guard_fixed_in_dollars,
    guard_no_imputation,
    guard_pair_is_across_segments,
    guard_paths_reconcile,
    guard_schedule_invariant,
    index_tolerance,
    parse_bcc_rows,
    parse_ecb_rows,
    published_column,
    published_from,
    two_sided_channels,
    vertex,
    widest_friction_band,
    xlsx_files,
    xlsx_skipped,
)

ROOT = Path(__file__).resolve().parents[1]

SEGMENT_KEYS = tuple(SEGMENTS)

#: One plausible day, at the levels the window actually ran at.
BASES = {"I": 24.0, "II": 120.0, "III": 624.0}


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


def _quotes(channel: str = "efectivo_ventanilla"):
    out = {}
    for tag, base in BASES.items():
        bid, ask = channel_quote(base, channel)
        out[tag] = (bid, ask)
    return out


# ------------------------------------------------------------------- constants


def test_the_markup_schedule_is_the_one_the_bank_publishes():
    """The answer key for B6-3 and the object guard 1 validates.

    Written out here rather than summarised, because a single digit changed in
    the module would move one hundred and ninety known answers at once and
    nothing else in the suite would notice.
    """
    assert MARKUP_SCHEDULE == {
        "efectivo_ventanilla": {"compra": 0.980, "venta": 1.020},
        "efectivo_aeropuertos_hoteles": {"compra": 0.970, "venta": 1.060},
        "efectivo_domingos_feriados": {"compra": 0.965, "venta": 1.060},
        "transferencia_externa_a_cuenta": {"compra": 0.990},
        "transferencia_externa_a_efectivo": {"compra": 0.970},
        "compra_con_tarjetas_internacionales": {"compra": 0.980},
        "servicios_de_divisas_a_cup": {"compra": 0.990},
        "transferencia_de_divisas_a_cup": {"compra": 1.000},
        "transferencia_de_cup_a_divisas": {"venta": 1.015},
        "retiro_efectivo_cup_desde_cuenta_en_divisas": {"compra": 0.970},
        "deposito_efectivo_cup_a_cuenta_en_divisas": {"venta": 1.015},
        "deposito_efectivo_en_divisas_a_cuenta": {"compra": 0.980},
        "usd_legal_no_efectivo": {"compra": 0.990},
        "usd_legal_efectivo_cup_entrada_salida": {"compra": 0.980},
        "usd_legal_preferencial": {"compra": 0.990, "venta": 1.010},
    }


def test_a_one_sided_channel_keeps_exactly_one_side():
    """Filling the missing side would manufacture a zero spread on a service
    that has no second direction at all."""
    for name, sides in MARKUP_SCHEDULE.items():
        assert set(sides) <= {"compra", "venta"}, name
        assert sides, name
    assert two_sided_channels() == (
        "efectivo_ventanilla",
        "efectivo_aeropuertos_hoteles",
        "efectivo_domingos_feriados",
        "usd_legal_preferencial",
    )
    bid, ask = channel_quote(100.0, "transferencia_de_cup_a_divisas")
    assert bid is None and ask == pytest.approx(101.5)


def test_the_signal_factor_is_the_one_two_earlier_stages_already_used():
    """B6-6c's multiple is not a constant chosen for this stage: B3-3 and B5-6
    both used it, which is the whole of its defence."""
    assert SIGNAL_OVER_NOISE == 4.0


def test_the_referee_carries_one_clause_and_the_envelope_is_gone():
    """§11 withdrew the `[t-1, t+1]` envelope. If a window constant reappears,
    someone has reinstated a clause whose withdrawal is on the record."""
    import monetary_topology.cuba_segments as mod

    assert CROSS_BAND == 0.01
    assert not hasattr(mod, "CROSS_WINDOW_DAYS")


def test_the_window_starts_at_the_first_publication_day():
    assert WINDOW_START == date(2025, 12, 19)


def test_the_pairs_come_out_at_one_hundred_and_ninety():
    """Twenty columns, the base among them. Excluding the base would silently
    drop nineteen of B6-3's pairs."""
    columns = column_multipliers()
    assert len(columns) == 20
    assert columns["base"] == 1.0
    assert len(columns) * (len(columns) - 1) // 2 == 190


# ------------------------------------------------------------- the publisher


def test_the_publisher_truncates_rather_than_rounds():
    """`615 * 1.015` is `624.2249999...` in binary and the bank prints
    `624.2249`, not `624.2250`. Assuming rounding would put B6-3's fallback
    tolerance a factor of two too tight on every pair."""
    assert published_from(615.0, 1.015) == pytest.approx(624.2249, abs=1e-9)
    assert round(615.0 * 1.015, PUBLISHED_DECIMALS) == pytest.approx(624.225)
    assert PUBLISHED_ULP == pytest.approx(1e-4)


def test_the_base_column_is_not_truncated():
    """`136.908 * 1e4` is `1369079.9999999998`, so putting the base through the
    truncation would drop a digit from a value the bank publishes verbatim."""
    assert published_column(136.908, "base") == 136.908
    assert published_from(136.908, 1.0) == pytest.approx(136.9079, abs=1e-9)


def test_the_channel_whose_multiplier_is_one_is_still_truncated():
    """The evidence that the truncation is the publisher's and not an artefact:
    on 59 of 1 428 rows this column differs from the base in the last place."""
    key = "transferencia_de_divisas_a_cup:compra"
    assert published_column(136.908, key) == pytest.approx(136.9079, abs=1e-9)
    assert published_column(136.908, key) != published_column(136.908, "base")


def test_the_index_tolerance_is_derived_and_not_a_constant():
    """B6-3's fallback. A single registered number would be loose at 624 and
    wrong at 24, which is `MEASUREMENT.md` rule 6."""
    assert index_tolerance(24.0, 24.0) == pytest.approx(
        2.0 * PUBLISHED_ULP * (1 / 24 + 1 / 24)
    )
    assert index_tolerance(24.0, 24.0) > index_tolerance(624.0, 624.0)
    with pytest.raises(ValueError):
        index_tolerance(0.0, 24.0)


# ------------------------------------------------------------------ the referee


def test_the_ecb_url_is_the_one_that_was_verified():
    """Character for character. The request that returned data on 2026-08-12."""
    assert ecb_url(date(2026, 8, 1), date(2026, 8, 12)) == (
        "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
        "?startPeriod=2026-08-01&endPeriod=2026-08-12&format=csvdata"
    )


def test_the_flow_and_the_key_are_two_strings_and_stay_two():
    """The joined form belongs in the response's `KEY` column and nowhere in the
    address. Putting it in the path yields `/EXR/EXR.D.USD...`, which is well
    formed, looks right, and is rejected with a 400."""
    assert ECB_KEY == f"{ECB_FLOW}.{ECB_SERIES}"
    assert ECB_KEY not in ecb_url(date(2026, 1, 1), date(2026, 1, 2))
    assert f"/{ECB_FLOW}/{ECB_SERIES}?" in ecb_url(date(2026, 1, 1), date(2026, 1, 2))


def test_a_neighbouring_ecb_series_is_refused():
    """`EXR` holds many series with this shape and a neighbour would parse
    perfectly and mean something else."""
    header = "KEY,TIME_PERIOD,OBS_VALUE\n"
    assert parse_ecb_rows(header + f"{ECB_KEY},2026-08-11,1.154\n") == {
        "2026-08-11": 1.154
    }
    with pytest.raises(ValueError, match="KEY"):
        parse_ecb_rows(header + "EXR.D.GBP.EUR.SP00.A,2026-08-11,0.86\n")
    with pytest.raises(ValueError, match="TIME_PERIOD"):
        parse_ecb_rows("a,b\n1,2\n")


# -------------------------------------------------------------------- the graph


def test_the_maximal_reading_leaves_a_positive_cycle_and_no_sub_potential():
    """Believing the published columns implies an executable round trip worth
    `log(624 * 0.98 / (24 * 1.02))`, and Theorem 4 then says no price vector
    whatever rationalises the table."""
    field = build_segment_field(_quotes(), SEGMENT_KEYS, "maximal")
    phi, why = directed.sub_potential(field)
    assert phi is None and "positive directed cycle" in why
    worst, witness = directed.worst_directed_cycle(field)
    assert witness is not None
    assert worst == pytest.approx(math.log(624 * 0.98 / (24 * 1.02)))


def test_the_directed_reading_restores_a_sub_potential():
    """The positive cycle is created by the two agent edges the regulation does
    not grant, and removing them removes it."""
    field = build_segment_field(_quotes(), SEGMENT_KEYS, "directed")
    phi, why = directed.sub_potential(field)
    assert phi is not None and why == ""
    assert directed.violation(field, phi) <= 1e-12


def test_the_directed_reading_sinks_are_the_frozen_dollar_positions():
    """Theorem 5's condition, read off the graph rather than asserted."""
    field = build_segment_field(_quotes(), SEGMENT_KEYS, "directed")
    components = directed.strongly_connected_components(field)
    assert len(components) == 3
    sinks = sorted(
        tuple(sorted(c)) for c in components
        if not any(u in set(c) and v not in set(c) for (u, v) in field.weights)
    )
    expected = sorted(
        (vertex(SEGMENT_KEYS.index(tag), USD_POS),) for tag in ONE_WAY_SEGMENTS
    )
    assert sinks == expected


def test_a_frozen_segment_has_no_return_leg_and_asking_for_one_raises():
    """`b4` §5.2. The edge is omitted rather than written as a large number, and
    `DirectedField.value` refuses to invent the reverse."""
    field = build_segment_field(_quotes(), SEGMENT_KEYS, "directed")
    i = SEGMENT_KEYS.index("I")
    assert field.has(vertex(i, CUP), vertex(i, USD_POS))
    assert not field.has(vertex(i, USD_POS), vertex(i, CUP))
    with pytest.raises(KeyError):
        field.value(vertex(i, USD_POS), vertex(i, CUP))


def test_the_frozen_interval_is_unbounded_above_and_the_float_is_not():
    """Theorem 5 in the two cases, from one function on one field."""
    field = build_segment_field(_quotes(), SEGMENT_KEYS, "directed")
    i = SEGMENT_KEYS.index("I")
    f = SEGMENT_KEYS.index(TWO_WAY_SEGMENT)
    lo_i, hi_i = directed.potential_interval(field, vertex(i, CUP), vertex(i, USD_POS))
    lo_f, hi_f = directed.potential_interval(field, vertex(f, CUP), vertex(f, USD_POS))
    assert math.isinf(hi_i) and math.isfinite(lo_i)
    assert math.isfinite(hi_f) and math.isfinite(lo_f)
    assert hi_f - lo_f == pytest.approx(math.log(1.02 / 0.98))


def test_every_reading_is_a_pair_of_switches_and_nothing_else():
    """The four models differ only in which position edges a frozen segment gets
    and where the agent edges live. A fifth field built any other way would be a
    reading nobody registered."""
    assert set(MODELS) == {
        "maximal", "maximal_acquire_only", "directed", "directed_flipped"
    }
    for name, config in MODELS.items():
        assert config["frozen"] in ("both", "cup_to_usd", "usd_to_cup"), name
        assert set(config["agent_at"]) <= {CUP, USD_POS}, name
    with pytest.raises(ValueError, match="unknown model"):
        build_segment_field(_quotes(), SEGMENT_KEYS, "believe_whatever")


def test_the_band_comes_from_the_schedule_and_not_from_a_constant(monkeypatch):
    """B6-6c's denominator. Widening a posted spread must move it, or the
    criterion is judging against a number that has gone stale."""
    name, band = widest_friction_band()
    assert name == "efectivo_domingos_feriados"
    assert band == pytest.approx(math.log(1.060 / 0.965))
    monkeypatch.setitem(
        MARKUP_SCHEDULE, "efectivo_ventanilla", {"compra": 0.5, "venta": 1.5}
    )
    widened, wider_band = widest_friction_band()
    assert widened == "efectivo_ventanilla"
    assert wider_band > band


# ---------------------------------------------------------------- the guards


def test_a_square_inside_one_segment_is_refused():
    """Its index part is the same constant on every date. B6-3 uses that on
    purpose and by a different route; every other caller comes through here."""
    guard_pair_is_across_segments("I", "III")
    with pytest.raises(GuardFailed, match="construction identity"):
        guard_pair_is_across_segments("III", "III")


def test_imputing_the_missing_direction_is_refused_with_the_reason_attached():
    guard_no_imputation(TWO_WAY_SEGMENT, "venta")
    with pytest.raises(GuardFailed, match="no return leg"):
        guard_no_imputation("I", "venta")


def _table(dates, bases, multiplier=None):
    header = ["Fecha", "BCC (Segmento III)"]
    rows = []
    if multiplier is not None:
        header.append("Efectivo en Ventanilla - Compra")
    for when, base in zip(dates, bases, strict=True):
        row = [when, base]
        if multiplier is not None:
            row.append(published_from(base, multiplier))
        rows.append(row)
    return header, rows


def test_a_schedule_departure_stops_the_run():
    """One column is enough to show the shape; the fetcher exercises all
    nineteen against the real export."""
    header, rows = _table(["2026-01-05"], [600.0], multiplier=0.980)
    rows[0][2] = rows[0][2] + 0.0001
    with pytest.raises(GuardFailed, match="truncates to"):
        guard_schedule_invariant(header, rows, "test")


def test_the_two_paths_must_agree_on_a_shared_date():
    api = {"2026-01-05": {"I": 24.0, "II": 120.0, "III": 600.0}}
    header, rows = _table(["2026-01-05"], [601.0])
    with pytest.raises(GuardFailed, match="XLSX"):
        guard_paths_reconcile(api, header, rows, "III", "test", date(2026, 2, 1))


def test_an_extra_xlsx_date_must_be_the_previous_published_value():
    api = {"2026-01-05": {"I": 24.0, "II": 120.0, "III": 600.0}}
    header, rows = _table(["2026-01-05", "2026-01-06"], [600.0, 600.0])
    report = guard_paths_reconcile(
        api, header, rows, "III", "test", date(2026, 2, 1)
    )
    assert report["filled_days"] == ["2026-01-06"]
    assert report["provisional_days"] == []
    header, rows = _table(["2026-01-05", "2026-01-06"], [600.0, 611.0])
    with pytest.raises(GuardFailed, match="not a forward fill"):
        guard_paths_reconcile(api, header, rows, "III", "test", date(2026, 2, 1))


def test_a_back_fill_is_not_a_forward_fill():
    """**The hole that produced a false B6-8 failure.**

    A forward fill copies a value that existed. A back fill manufactures one for
    a day the source published nothing, which is what the export does for a
    currency that joined the table late. Read as forward fills they are silently
    admitted, and eight of them became a criterion failure.
    """
    api = {
        "2026-01-06": {"I": 24.0, "II": 120.0, "III": 600.0},
        "2026-01-07": {"I": 24.0, "II": 120.0, "III": 611.0},
    }
    header, rows = _table(
        ["2026-01-05", "2026-01-06", "2026-01-07"], [600.0, 600.0, 611.0]
    )
    report = guard_paths_reconcile(
        api, header, rows, "III", "test", date(2026, 2, 1)
    )
    assert report["back_filled_days"] == ["2026-01-05"]
    assert report["filled_days"] == []
    assert report["first_published"] == "2026-01-06"


def test_a_provisional_row_may_be_the_day_s_value_or_the_previous_one():
    """Which one it is depends on the minute the export was downloaded, and that
    is not a property of the source. A third value is still refused."""
    api = {
        "2026-01-05": {"I": 24.0, "II": 120.0, "III": 600.0},
        "2026-01-06": {"I": 24.0, "II": 120.0, "III": 617.0},
    }
    for last in (600.0, 617.0):
        header, rows = _table(["2026-01-05", "2026-01-06"], [600.0, last])
        report = guard_paths_reconcile(
            api, header, rows, "III", "test", date(2026, 1, 6)
        )
        assert report["provisional_days"] == ["2026-01-06"]
    header, rows = _table(["2026-01-05", "2026-01-06"], [600.0, 900.0])
    with pytest.raises(GuardFailed, match="neither the day"):
        guard_paths_reconcile(api, header, rows, "III", "test", date(2026, 1, 6))


def test_a_euro_fixed_segment_that_is_constant_is_a_bug():
    """The peg is against the dollar, so the euro leg inherits the cross. An
    implementation that finds it constant has one."""
    usd = {d: {"I": 24.0, "II": 120.0, "III": 600.0} for d in ("a", "b")}
    eur = {
        "a": {"I": 28.14, "II": 140.7, "III": 703.5},
        "b": {"I": 28.10, "II": 140.5, "III": 702.5},
    }
    out = guard_fixed_in_dollars(usd, eur)
    assert out["usd_I"] == 24.0 and out["eur_I_distinct"] == 2
    frozen = {d: dict(v, I=28.14, II=140.7) for d, v in eur.items()}
    with pytest.raises(GuardFailed, match="peg is against the dollar"):
        guard_fixed_in_dollars(usd, frozen)


# ------------------------------------------------------------------ the loader


@pytest.mark.parametrize(
    "name",
    [
        "tasas-historicas-USD-Segmento-III-2026-08-12.xlsx",
        "tasas-historicas-EUR-Segmento-I-2026-08-12.xlsx",
        "tasashistoricasUSDSegmentoII20260812.xlsx",
    ],
)
def test_both_spellings_of_the_export_name_are_accepted(name):
    """The download carries hyphens. A copy of the name that had lost them was
    what the first version of this pattern was written against, and it rejected
    all six real files while reporting the directory as empty."""
    assert VALID_XLSX.match(name)


@pytest.mark.parametrize(
    "name",
    [
        "tasas-historicas-USD-Segmento-III-2026-08-12 (1).xlsx",
        "tasas-historicas-BRL-Segmento-I-2026-08-12.xlsx",
        "notes.xlsx",
    ],
)
def test_a_name_the_loader_does_not_know_is_skipped(name):
    """`BRL` is not on `CURRENCIES`, and a currency the stage has not registered
    is not a bonus observation: the file is skipped and reported."""
    assert not VALID_XLSX.match(name)


def test_every_registered_currency_has_a_name_the_loader_accepts():
    """One list drives the fetcher and the pattern, so they cannot drift."""
    for code in CURRENCIES:
        assert VALID_XLSX.match(
            f"tasas-historicas-{code}-Segmento-III-2026-08-12.xlsx"
        ), code
    assert BASE_CURRENCY in CURRENCIES
    assert len(set(CURRENCIES)) == len(CURRENCIES)


def test_a_skipped_file_is_reported_rather_than_merely_skipped(tmp_path):
    """"Empty" and "six files the loader does not accept" must not produce the
    same message."""
    (tmp_path / "bcc_xlsx").mkdir()
    (tmp_path / "bcc_xlsx" / "tasas historicas USD.xlsx").write_bytes(b"")
    assert xlsx_files(tmp_path) == {}
    assert xlsx_skipped(tmp_path) == ["tasas historicas USD.xlsx"]


def test_two_files_for_one_pair_is_an_error(tmp_path):
    (tmp_path / "bcc_xlsx").mkdir()
    for stamp in ("2026-08-11", "2026-08-12"):
        (tmp_path / "bcc_xlsx" / f"tasas-historicas-USD-Segmento-I-{stamp}.xlsx"
         ).write_bytes(b"")
    with pytest.raises(GuardFailed, match="two files"):
        xlsx_files(tmp_path)


# ------------------------------------------------------------------ the parser


def _row(when="2026-01-05", **over):
    row = {"fecha": when, "tasaOficial": 24, "tasaPublica": 120,
           "tasaEspecial": 600}
    row.update(over)
    return row


def test_a_well_formed_response_parses():
    rows = parse_bcc_rows([_row("2026-01-05"), _row("2026-01-06")])
    assert [r["date"] for r in rows] == ["2026-01-05", "2026-01-06"]
    assert rows[0]["III"] == 600.0


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"fecha": "2026-01-05"}, "JSON array"),
        ([{"tasaOficial": 24}], "no 'fecha'"),
        ([_row(fecha="05/01/2026")], "not ISO"),
        ([{"fecha": "2026-01-05", "tasaPublica": 120, "tasaEspecial": 600}],
         "tasaOficial"),
        ([_row(tasaEspecial="600")], "not a number"),
        ([_row(tasaEspecial=True)], "not a number"),
        ([_row(tasaEspecial=0.0)], "outside"),
        ([_row("2026-01-05"), _row("2026-01-05")], "repeats a date"),
        ([_row("2026-01-06"), _row("2026-01-05")], "not in date order"),
    ],
)
def test_a_malformed_response_is_refused_with_the_reason(payload, message):
    with pytest.raises(ValueError, match=message):
        parse_bcc_rows(payload)


# ------------------------------------------------------- what may be reported


def test_the_one_sided_bound_is_a_potential_difference_and_not_a_cycle_sum():
    """**The test that refuses the error this stage already made once.**

    A frozen segment has no closed loop, so there is no holonomy to report.
    B6-6c must reach its number through `potential_interval` and through nothing
    that walks a square or forms an index part. If any of those appears in its
    body, someone has reported an `H⁰` fact under an `H¹` name.
    """
    source = (ROOT / "experiments" / "b6_segments.py").read_text(encoding="utf-8")
    body = source.split("def b6_6c_bounds")[1].split("\ndef ")[0]
    assert "potential_interval" in body
    for forbidden in ("directed_square", "square_via_machinery", "index_matrix"):
        assert forbidden not in body, forbidden


def test_b6_7_is_a_strict_comparison_with_no_threshold():
    """Its defence is that it contains no band, fraction or cutoff, so nothing
    existed that could have been moved once the answer was in view."""
    source = (ROOT / "experiments" / "b6_segments.py").read_text(encoding="utf-8")
    body = source.split("def b6_7_growth")[1].split("\ndef ")[0]
    assert ">=" not in body and "<=" not in body
    assert "SIGNAL_OVER_NOISE" not in body and "band" not in body


def test_the_referee_is_not_re_registered_against_its_own_failure():
    """B6-4 failed on three of 147 days and a one-business-day lag removes all
    three. The lagged figures are a diagnostic. If they ever reach `passed`,
    the criterion has been fitted to the result it was meant to risk.
    """
    source = (ROOT / "experiments" / "b6_segments.py").read_text(encoding="utf-8")
    body = source.split("def b6_4_referee")[1].split("\ndef ")[0]
    verdict = body.split('"passed":')[1].split(",")[0]
    assert "lag" not in verdict


def test_the_gates_are_the_only_thing_that_voids_a_run():
    """A registered criterion failing is a result, not an invalid run. B6-1 and
    B6-2 are different: if the machinery is wrong, nothing below means anything.
    """
    source = (ROOT / "experiments" / "b6_segments.py").read_text(encoding="utf-8")
    assert 'gates = ("B6-1", "B6-2")' in source


def test_the_experiment_registers_its_channel_and_says_why():
    b6 = _load("b6_segments")
    assert b6.SEGMENT_CHANNEL in two_sided_channels()
    assert b6.MACHINERY_TOLERANCE == 1e-12
    assert b6.TRIANGLE_TOLERANCE == 1e-12
