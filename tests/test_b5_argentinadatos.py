"""Tests for the argentinadatos retriever's schema assertions.

**The two conventions must never meet in one parser.** Ámbito serves
`["12/06/2025","1176,00","1185,00"]`; this API serves
`{"compra":1176,"venta":1185,"fecha":"2025-06-12"}`. The zero calibration in
`b5_orphan_prereg.md` §4.4 is built on those being handled by two separate
pieces of code that then have to agree on the number. A parser lenient enough to
read both would be lenient enough to misread either, and the arm would be
testing nothing.

So the tests here are mostly about **refusing** things: a comma-decimal string,
a `DD/MM/YYYY` date, a row from a different series. Each is a change that would
still parse under a permissive reader.

Nothing here makes a network request.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
_SPEC = importlib.util.spec_from_file_location(
    "fetch_argentinadatos", _ROOT / "data" / "fetch_argentinadatos.py"
)
assert _SPEC and _SPEC.loader
fad = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fad)


def _row(casa="mayorista", compra=1176, venta=1185, fecha="2025-06-12"):
    return {"casa": casa, "compra": compra, "venta": venta, "fecha": fecha}


# ------------------------------------------------------------------ happy path


def test_a_normal_response_parses_and_sorts():
    rows = fad.parse_argentinadatos_rows(
        [_row(fecha="2025-06-12"), _row(compra=1171.5, venta=1180.5,
                                        fecha="2025-06-02")],
        "mayorista",
    )
    assert [r["date"] for r in rows] == ["2025-06-02", "2025-06-12"]
    assert rows[1]["compra"] == pytest.approx(1176.0)


def test_integers_are_accepted_as_quotes():
    """This API returns bare integers for round values; Ámbito never does.

    ``1176`` and ``1176.0`` are the same number here, and rejecting the integer
    form would fail on roughly half the series.
    """
    rows = fad.parse_argentinadatos_rows(
        [_row(compra=1176, venta=1185)], "mayorista"
    )
    assert rows[0]["compra"] == pytest.approx(1176.0)


# ---------------------------------------------------- the two conventions stay apart


def test_a_comma_decimal_string_is_refused_rather_than_parsed():
    """**The load-bearing refusal.**

    If this parser accepted `"1.176,00"` it would have to guess a decimal
    convention, and the zero calibration would then be comparing one lenient
    reader against itself instead of two strict readers against each other.
    """
    with pytest.raises(ValueError, match="string"):
        fad.parse_argentinadatos_rows([_row(compra="1.176,00")], "mayorista")


def test_an_ambito_style_date_is_refused():
    """`12/06/2025` here means the two conventions have been crossed."""
    with pytest.raises(ValueError, match="ISO"):
        fad.parse_argentinadatos_rows([_row(fecha="12/06/2025")], "mayorista")


def test_the_refusal_message_names_both_conventions():
    """The message has to be enough to diagnose from, at three in the morning."""
    with pytest.raises(ValueError) as caught:
        fad.parse_argentinadatos_rows([_row(fecha="12/06/2025")], "mayorista")
    assert "DD/MM/YYYY" in str(caught.value)
    assert "ISO" in str(caught.value)


# ---------------------------------------------------------------------- schema


def test_a_row_from_a_different_series_raises():
    """The series name is in the path, so a typo returns a valid wrong answer.

    This is the failure the CCL path already produced once in this stage, in the
    form that does 404. This is the form that does not.
    """
    with pytest.raises(ValueError, match="requested"):
        fad.parse_argentinadatos_rows([_row(casa="blue")], "mayorista")


def test_a_repeated_date_raises_rather_than_being_collapsed():
    """Ámbito's collapse rule is registered for Ámbito and may not be borrowed.

    This API is expected to publish one row per date. If it stops doing so, that
    is a change in what the series is, and folding it with a rule nobody
    registered for it would hide the change.
    """
    with pytest.raises(ValueError, match="twice"):
        fad.parse_argentinadatos_rows([_row(), _row(compra=1177)], "mayorista")


@pytest.mark.parametrize("payload", [[], {}, "x", [1, 2]])
def test_a_malformed_response_raises(payload):
    with pytest.raises(ValueError):
        fad.parse_argentinadatos_rows(payload, "mayorista")


def test_a_missing_field_raises():
    row = _row()
    del row["venta"]
    with pytest.raises(ValueError, match="not a number"):
        fad.parse_argentinadatos_rows([row], "mayorista")


@pytest.mark.parametrize("value", [1.176, 5.0, 250_000.0])
def test_a_quote_outside_the_plausible_band_raises(value):
    """The band catches a decimal convention flipping, not bad data.

    `1.176` is what `1.176,00` becomes if something upstream strips the comma
    and keeps the period, which is one of the two wrong readings of the Ámbito
    format.
    """
    with pytest.raises(ValueError, match="outside"):
        fad.parse_argentinadatos_rows([_row(compra=value)], "mayorista")


def test_the_band_admits_both_ends_of_the_real_window():
    rows = fad.parse_argentinadatos_rows(
        [_row(compra=60.0, venta=63.0, fecha="2019-12-23"),
         _row(compra=1878.5, venta=1943.5, fecha="2026-06-29")],
        "mayorista",
    )
    assert len(rows) == 2


# --------------------------------------------------------------------- summary


def test_the_window_filter_reports_and_does_not_prune_the_archive():
    """``b5_orphan_prereg.md`` §7 filters at analysis, never at retrieval.

    The file keeps everything that arrived. Trimming on the way in would make
    the archive depend on a constant that §7 allows to be revised, and a later
    revision would then need a refetch rather than a re-read.
    """
    rows = fad.parse_argentinadatos_rows(
        [_row(fecha="2019-01-02"), _row(fecha="2025-06-12", compra=1177)],
        "mayorista",
    )
    assert len(rows) == 2
    assert len(fad.in_window(rows)) == 1


def test_covers_window_end_is_false_while_the_series_is_short():
    """The series grows daily, so a cached file is stale rather than wrong.

    ``--check`` has to say which, because "stale" is fixed by refetching and
    "wrong" is not.
    """
    rows = fad.parse_argentinadatos_rows([_row(fecha="2025-06-12")], "mayorista")
    assert fad.summarise(rows, "mayorista")["covers_window_end"] is False
    late = fad.parse_argentinadatos_rows([_row(fecha="2026-06-30")], "mayorista")
    assert fad.summarise(late, "mayorista")["covers_window_end"] is True


def test_both_registered_series_have_a_stated_purpose():
    """Neither is an agent class, and the manifest has to say what each is for.

    ``tarjeta`` in particular is **not** a known-answer arm (§5), and a reader
    who assumes it is would read a construction identity as a validation.

    The purposes live in the package beside the parser, not in this script, for
    the reason the module docstring gives: a registered fact that exists in two
    files has two truths.
    """
    from monetary_topology.parallel_rates import ARGENTINADATOS_CASAS

    assert fad.ARGENTINADATOS_CASAS is ARGENTINADATOS_CASAS
    assert set(ARGENTINADATOS_CASAS) == {
        "mayorista", "tarjeta", "oficial", "cripto",
    }
    assert "zero calibration" in ARGENTINADATOS_CASAS["mayorista"]
    assert "dating" in ARGENTINADATOS_CASAS["tarjeta"]
    # **The purpose string carries each series' standing**, so a reader of the
    # manifest cannot mistake a rejected candidate or an unaudited one for a
    # settled source. `oficial` was audited and failed all three axes
    # (`b5_friction.py`); `cripto` has not been audited yet (`b5_p2p.py`).
    assert "REJECTED" in ARGENTINADATOS_CASAS["oficial"]
    assert "unvalidated" in ARGENTINADATOS_CASAS["cripto"]


def test_the_parser_is_the_packages_and_not_a_local_copy():
    """The two conventions are kept apart by two functions, not two files.

    ``fetch_ambito`` and this script both import their parser from
    ``parallel_rates``. If either grew a local copy, the pair in
    ``b5_orphan_prereg.md`` §4.4b would stop being two independent readers of one
    market and start being one reader compared with itself.
    """
    from monetary_topology.parallel_rates import (
        parse_argentinadatos_rows,
        parse_rows,
    )

    assert fad.parse_argentinadatos_rows is parse_argentinadatos_rows
    # And it is **not** bound to the name the Ambito parser uses. The two
    # conventions are kept apart by having different names; an alias here would
    # remove the only thing keeping them apart at the call site.
    assert getattr(fad, "parse_rows", None) is not parse_rows
    assert not hasattr(fad, "parse_rows")
