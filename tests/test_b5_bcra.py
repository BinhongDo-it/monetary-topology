"""Tests for the BCRA A 3500 parser's schema assertions.

The parser itself lives in ``monetary_topology.parallel_rates`` beside Ámbito's
and argentinadatos', so that the three conventions cannot drift apart; the
fetcher imports it. These tests exercise the package function and check that the
fetcher has no local copy of it.

This is the one authoritative series in stage B5 and it supplies the oficial
class's headline mid, so a silent change in it moves the headline directly.
Every test here is about a way the response could change **and still parse**: a
renamed field, a second currency in the detail list, a page cut off at its limit.
Those are the failures that do not announce themselves.

Nothing here makes a network request.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from monetary_topology.parallel_rates import (
    BCRA_CODE,
    BCRA_PLAUSIBLE,
    parse_bcra_rows,
)

#: The fetcher is a script rather than a package module, which is how every
#: retriever in this repository is arranged, so it is loaded by path.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
_SPEC = importlib.util.spec_from_file_location(
    "fetch_bcra", _ROOT / "data" / "fetch_bcra.py"
)
assert _SPEC and _SPEC.loader
fetch_bcra = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fetch_bcra)


def _payload(rows, count=None, limit=1000, status=200):
    return {
        "status": status,
        "metadata": {"resultset": {
            "count": len(rows) if count is None else count,
            "offset": 0, "limit": limit,
        }},
        "results": [
            {"fecha": d, "detalle": [{
                "codigoMoneda": "REF",
                "descripcion": "DOLAR REFERENCIA COM 3500",
                "tipoPase": 0.0, "tipoCotizacion": v,
            }]}
            for d, v in rows
        ],
    }


# ------------------------------------------------------------------- happy path


def test_a_normal_response_parses_and_sorts():
    rows = parse_bcra_rows(
        _payload([("2025-06-09", 1186.4167), ("2025-06-02", 1181.1667)])
    )
    assert [r["date"] for r in rows] == ["2025-06-02", "2025-06-09"]
    assert rows[0]["reference"] == pytest.approx(1181.1667)


def test_the_currency_code_is_the_reference_rate_and_not_usd():
    """``USD`` is a different series on the same API.

    ``b5_orphan_prereg.md`` §3.1 registers Comunicacion A 3500, which is listed
    in ``/Maestros/Divisas`` as ``REF``. Picking ``USD`` here would retrieve a
    series that looks right, parses right, and answers a different question.
    """
    assert BCRA_CODE == "REF"
    # And the fetcher has no local copy: a registered constant in two files has
    # two truths, and the one that gets edited is whichever is opened first.
    assert not hasattr(fetch_bcra, "CODE")
    assert fetch_bcra.parse_bcra_rows is parse_bcra_rows
    assert BCRA_PLAUSIBLE == (10.0, 100_000.0)


# ------------------------------------------------------------------ truncation


def test_a_page_at_its_limit_is_refused_rather_than_accepted():
    """**The guard that matters most, because the failure is well formed.**

    A range wider than the page limit returns a valid response holding a prefix
    of the answer. Nothing downstream distinguishes a quarter that is missing
    from a quarter the central bank did not publish, and the headline would be
    computed on whatever survived.
    """
    payload = _payload([("2025-06-02", 1181.17)], count=1000, limit=1000)
    with pytest.raises(ValueError, match="truncated"):
        parse_bcra_rows(payload)


def test_a_page_below_its_limit_is_accepted():
    assert len(parse_bcra_rows(_payload([("2025-06-02", 1181.17)]))) == 1


def test_the_half_year_chunks_stay_well_under_the_page_limit():
    """Roughly 130 business days per chunk against a limit of 1000.

    So the truncation guard should never fire. It exists anyway, because a guard
    that only runs when something is already wrong is the only kind worth having.
    """
    spans = fetch_bcra.chunk_halves()
    assert spans[0][2] == fetch_bcra.WINDOW_START
    assert spans[-1][3] == fetch_bcra.WINDOW_END
    for _, _, start, end in spans:
        assert (end - start).days <= 184


# ---------------------------------------------------------------------- schema


def test_a_non_200_status_raises():
    with pytest.raises(ValueError, match="status"):
        parse_bcra_rows(_payload([("2025-06-02", 1181.17)], status=400))


def test_a_missing_results_list_raises():
    with pytest.raises(ValueError, match="results"):
        parse_bcra_rows({"status": 200, "metadata": {}})


def test_a_second_currency_in_the_detail_list_raises():
    """Two entries means the response is not what this parser was written for.

    Taking the first would silently pick one, and which one would depend on the
    order the API happened to serve.
    """
    payload = _payload([("2025-06-02", 1181.17)])
    payload["results"][0]["detalle"].append(
        {"codigoMoneda": "REF", "tipoCotizacion": 1.0}
    )
    with pytest.raises(ValueError, match="exactly one"):
        parse_bcra_rows(payload)


def test_a_detail_list_without_the_reference_code_raises():
    payload = _payload([("2025-06-02", 1181.17)])
    payload["results"][0]["detalle"][0]["codigoMoneda"] = "USD"
    with pytest.raises(ValueError, match="exactly one"):
        parse_bcra_rows(payload)


def test_a_renamed_rate_field_raises_instead_of_defaulting():
    payload = _payload([("2025-06-02", 1181.17)])
    del payload["results"][0]["detalle"][0]["tipoCotizacion"]
    with pytest.raises(ValueError, match="not a number"):
        parse_bcra_rows(payload)


def test_a_non_iso_date_raises():
    payload = _payload([("02/06/2025", 1181.17)])
    with pytest.raises(ValueError, match="ISO"):
        parse_bcra_rows(payload)


def test_a_repeated_date_raises():
    """Unlike Ámbito, this API is expected to publish one row per date.

    If it ever does not, that is a change in what the series is, and it must
    stop the run rather than be collapsed by a rule nobody registered for it.
    """
    payload = _payload([("2025-06-02", 1181.17), ("2025-06-02", 1181.20)])
    with pytest.raises(ValueError, match="twice"):
        parse_bcra_rows(payload)


# ------------------------------------------------------------ decimal convention


@pytest.mark.parametrize("value", [0.5, 5.0, 250_000.0])
def test_a_rate_outside_the_plausible_band_raises(value):
    """The band's job is to catch a decimal convention flipping.

    This API returns JSON floats with a period; Ámbito returns strings with a
    comma. Two parsers, two conventions, and each asserts its own. Pointing one
    at the other's payload must fail loudly rather than produce a series that is
    wrong by a factor of a hundred.
    """
    with pytest.raises(ValueError, match="outside"):
        parse_bcra_rows(_payload([("2025-06-02", value)]))


def test_the_band_admits_both_ends_of_the_real_window():
    """Near 56 pesos in September 2019 and near 1500 in 2026.

    A band tight enough to be interesting would be a forecast, so it is wide on
    purpose and is not a data-quality judgement.
    """
    rows = parse_bcra_rows(
        _payload([("2019-09-02", 56.15), ("2026-06-29", 1498.0)])
    )
    assert len(rows) == 2


def test_a_comma_decimal_string_is_not_silently_accepted():
    """The Ámbito convention arriving here is a wrong-parser error, not data."""
    with pytest.raises(ValueError, match="not a number"):
        parse_bcra_rows(_payload([("2025-06-02", "1.181,17")]))
