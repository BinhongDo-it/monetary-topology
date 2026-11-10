"""What A6's driver writes, and two things its tables are easy to misread as.

The registered file belongs to the full registered run and to nothing else; the
factorial prints eight cells of which six are distinct; and the top decile in
the Palma ratio is a ranking of nodes, not the financial layer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a6_siphon_cost as A  # noqa: E402

REGISTERED = "a6_siphon_cost.json"


def test_only_the_full_registered_run_gets_the_registered_name() -> None:
    assert A.record_name(5, 300, 2000, False) == REGISTERED
    # each of these used to claim the registered file
    assert A.record_name(5, 300, 2000, True) == (
        "a6_siphon_cost.offparam_5x300_nolong.json")
    assert A.record_name(5, 300, 300, False) == (
        "a6_siphon_cost.offparam_5x300_long300.json")
    # off-parameter runs are named by seeds, rounds and the long-horizon flags.
    # The side file results/a6_siphon_cost.offparam_2x300.json predates this
    # naming and holds a --skip-long run (long_rounds null, no A6-5); under
    # this naming that run would be a6_siphon_cost.offparam_2x300_nolong.json
    assert A.record_name(2, 300, 2000, False) == (
        "a6_siphon_cost.offparam_2x300.json")
    assert A.record_name(2, 300, 2000, True) == (
        "a6_siphon_cost.offparam_2x300_nolong.json")
    assert A.record_name(5, 100, 2000, False) == (
        "a6_siphon_cost.offparam_5x100.json")


def test_a_run_that_skips_the_long_horizon_writes_beside(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(A, "ROOT", tmp_path)
    monkeypatch.setattr(A, "RESULTS", tmp_path / "results")
    # what the registered parameters would have done before: seeds and rounds
    # are the registered ones, so only the two long-horizon flags decide
    monkeypatch.setattr(A, "REGISTERED_SEEDS", 1)
    monkeypatch.setattr(A, "REGISTERED_ROUNDS", 160)
    monkeypatch.setattr(sys, "argv", ["a6", "--seeds", "1", "--rounds", "160",
                                      "--skip-long"])
    A.main()
    written = sorted(p.name for p in (tmp_path / "results").iterdir())
    assert written == ["a6_siphon_cost.offparam_1x160_nolong.json"]
    record = json.loads(
        (tmp_path / "results" / written[0]).read_text(encoding="utf-8"))
    assert record["long_rounds"] is None
    assert "A6-5" not in [c["name"] for c in record["criteria"]]
    assert record["distinct_cells"] == 6


def test_the_retention_switch_reaches_one_graph_and_not_the_other() -> None:
    reach = A.retention_reach(0, 300)
    assert reach["access"]["the_switch_changes_the_propensities"] is True
    assert reach["access"]["stratified_low"] == [0.5, 0.875]
    assert reach["flat"]["the_switch_changes_the_propensities"] is False
    assert reach["flat"]["stratified_low"] == [0.620375, 0.620375]
    assert reach["flat"]["fair_low"] == 0.620375
    assert reach["flat"]["fair_high"] == 0.6605


def cells(**rates) -> dict:
    out = {}
    for graph in ("access", "flat"):
        for retention in ("fair", "stratified"):
            for channel in ("T", "I"):
                key = f"{graph}/{retention}/{channel}"
                out[key] = {"rates": rates.get(key.replace("/", "_"), [0.0, 0.0])}
    return out


def test_a_cell_the_switch_cannot_reach_is_marked_as_its_twin() -> None:
    reach = {"access": {"the_switch_changes_the_propensities": True},
             "flat": {"the_switch_changes_the_propensities": False}}
    table = cells()
    assert A.mark_twins(table, reach) == 6
    assert table["flat/stratified/T"]["same_model_as"] == "flat/fair/T"
    assert table["flat/stratified/I"]["same_model_as"] == "flat/fair/I"
    assert table["flat/stratified/I"]["same_rates"] is True
    for key in ("flat/fair/T", "access/stratified/T", "access/fair/I"):
        assert table[key]["same_model_as"] is None
        assert table[key]["same_rates"] is None
    # a twin that came back with other rates is not one model, and it says so
    table = cells(flat_stratified_T=[0.0, 0.005])
    A.mark_twins(table, reach)
    assert table["flat/stratified/T"]["same_rates"] is False
    # a switch that reaches both graphs leaves eight distinct cells
    both = {"access": {"the_switch_changes_the_propensities": True},
            "flat": {"the_switch_changes_the_propensities": True}}
    assert A.mark_twins(cells(), both) == 8


def test_the_top_decile_is_whoever_is_richest() -> None:
    layer = np.array([0, 1])
    held = np.arange(20, dtype=float)          # the two richest are 18 and 19
    assert A.financial_in_top_decile(held, layer) == 0
    held[0] = 100.0                            # one layer node is now on top
    assert A.financial_in_top_decile(held, layer) == 1
    held[1] = 99.0
    assert A.financial_in_top_decile(held, layer) == 2
    # two hundred nodes: the decile is twenty wide, the layer's own size
    big = np.arange(200, dtype=float)
    assert A.financial_in_top_decile(big, np.arange(180, 200)) == 20
    assert A.financial_in_top_decile(big, np.arange(170, 190)) == 10


def test_the_registered_opening_is_not_the_layer() -> None:
    from monetary_topology.redistribution import run_a6

    model, history = run_a6(A.config_for(0, 5, True, True, "transfer"))
    first = np.asarray(history.holdings)[0]
    assert A.financial_in_top_decile(first, model._l1) == 19
    top = set(np.argsort(first, kind="stable")[-20:].tolist())
    assert 125 in top and 14 not in top
    assert 14 in set(model._l1) and 125 not in set(model._l1)
