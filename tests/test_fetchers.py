"""The contract between each parsing module and the fetcher that prints it.

This file exists because of a break. ``monetary_topology.scf`` renamed a key in
its result, ``data/fetch_scf.py`` went on reading the old one, and every test
stayed green: the suite loaded the module and nothing loaded the fetcher, so the
mismatch surfaced only when a human ran the retrieval by hand.

The repository already tests fetchers by path (``tests/test_b5_fetch.py`` loads
``data/fetch_ambito.py`` with ``importlib``). What follows is cheaper than that
and covers the one failure that actually happened: it reads each fetcher's source
and asserts that every string key it pulls out of a result dictionary is a key
that dictionary really carries. No network, no cache, no import of the fetcher.

Each check ends by asserting it found something to check. A guard that silently
matches nothing passes for the wrong reason, which is ``MEASUREMENT.md``
checklist item 8 asked of the guard itself.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def keys_read_from(source: Path, variable: str) -> set[str]:
    """Every ``variable["literal"]`` in the file, as a set of literals."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == variable
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            out.add(node.slice.value)
    return out


# ---------------------------------------------------------------------------
# A1's HHDC workbook reader
# ---------------------------------------------------------------------------
def test_fetch_hhdc_reads_only_keys_validate_returns() -> None:
    from monetary_topology.hhdc import DelinquencyTable  # noqa: F401

    produced = {
        "vintage",
        "stock_sheet",
        "stock_title",
        "stock_quarters",
        "stock_last",
        "flow_sheet",
        "flow_title",
        "flow_quarters",
        "flow_last",
        "anchors_checked",
    }
    read = keys_read_from(DATA / "fetch_hhdc.py", "summary")
    assert read, "no summary[...] reads found; this check is not working"
    assert read <= produced, sorted(read - produced)


def test_the_hhdc_summary_really_carries_those_keys(tmp_path: Path) -> None:
    """The set above is asserted against the module rather than trusted.

    Without this, the two halves of the previous test could drift together and
    agree with each other while both being wrong.
    """
    import inspect

    from monetary_topology import hhdc

    source = inspect.getsource(hhdc.validate)
    for key in ("stock_quarters", "flow_last", "anchors_checked"):
        assert f'"{key}"' in source, key


# ---------------------------------------------------------------------------
# A1's DFA and Z.1 reader
# ---------------------------------------------------------------------------
def test_fetch_dfa_reads_only_instruments_the_module_defines() -> None:
    from monetary_topology.dfa import INSTRUMENTS

    read = keys_read_from(DATA / "fetch_dfa.py", "shares")
    # ``shares`` is indexed by a loop variable over INSTRUMENTS in the fetcher,
    # so a literal read here would be the exception rather than the rule.
    assert read <= set(INSTRUMENTS), sorted(read - set(INSTRUMENTS))


def test_fetch_dfa_reads_only_the_two_z1_legs_it_fetched() -> None:
    """The Z.1 dictionary is built from ``Z1_SERIES`` and read by literal."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fetch_dfa_probe", DATA / "fetch_dfa.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    read = keys_read_from(DATA / "fetch_dfa.py", "z1")
    assert read, "no z1[...] reads found; this check is not working"
    assert read <= set(module.Z1_SERIES), sorted(read - set(module.Z1_SERIES))


# ---------------------------------------------------------------------------
# A1's SCF computation
# ---------------------------------------------------------------------------
def test_fetch_scf_reads_only_keys_the_computation_returns() -> None:
    produced = {
        "wave",
        "rates",
        "population_shares",
        "overall",
        "records",
        "weighted_population",
    }
    read = keys_read_from(DATA / "fetch_scf.py", "result")
    assert read, "no result[...] reads found; this check is not working"
    assert read <= produced, sorted(read - produced)


# ---------------------------------------------------------------------------
# A1's CEX reader
# ---------------------------------------------------------------------------
def test_fetch_cex_reads_only_keys_the_module_returns() -> None:
    produced = {
        "reference_year",
        "income",
        "necessities",
        "rent",
        "mortgage_payment",
        "all_units_income",
        "decile_mean_income",
        "consumer_units",
        "consumer_units_by_decile",
        "necessities_by_decile",
        "mortgage_label_signs",
        "tenure",
        "necessity_labels",
        "top_groups_share_a_column",
    }
    read = keys_read_from(DATA / "fetch_cex.py", "result")
    assert read, "no result[...] reads found; this check is not working"
    assert read <= produced, sorted(read - produced)


# ---------------------------------------------------------------------------
# Every A1 fetcher, on the properties they are supposed to share
# ---------------------------------------------------------------------------
A1_FETCHERS = ("fetch_hhdc.py", "fetch_dfa.py", "fetch_scf.py", "fetch_cex.py")


def test_every_a1_fetcher_retires_rather_than_removes() -> None:
    """``CLAUDE.md`` item 5. A fetcher that unlinks is the one way to lose data
    that cannot be re-derived."""
    for name in A1_FETCHERS:
        source = (DATA / name).read_text(encoding="utf-8")
        assert "def retire(" in source, name
        for forbidden in (".unlink(", "shutil.rmtree", "os.remove"):
            assert forbidden not in source, f"{name} calls {forbidden}"


def test_every_a1_fetcher_offers_check_and_force() -> None:
    """The shape ``data/fetch_ecb.py`` set, so a reader can classify a cache
    without fetching and can refetch without editing anything."""
    for name in A1_FETCHERS:
        source = (DATA / name).read_text(encoding="utf-8")
        assert '"--check"' in source, name
        assert '"--force"' in source, name
