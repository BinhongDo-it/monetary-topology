"""Stage A11: what the rows record, and what the criteria are allowed to read.

**The criteria are judged only on the registered grid.** Both graphs, the floor
off and every floor and grace, each at every seed, once. A single firing row, or
a grid with the complete graph's rows removed, used to pass all four; here
A11-2 to A11-4 are not evaluated on such rows, and the record carries the
coverage it was judged on.

**The close and the path are two readings.** Under ``drawdown`` the complete
graph at the pool per node has all two hundred nodes below the floor in every
other round and none in the rest, so the close reads zero or two hundred by
phase. The rows carry the path beside the close, and the sentence the criterion
prints about the path is built from those fields: a field that is absent is
reported as not recorded, never as zero.

**Three accounts at the close.** The history row is written before the round's
settlement step. The asset carrier settles there; the plain carrier does not,
so on the plain carrier the three accounts are one vector.

**One switch between the graphs, and what it collapses.** The structure check
compares each graph's floor arms with that graph's own control and the two
controls with each other, and the record names what the switch builds
differently, on the carrier the record runs on. The printed arms move one
thing at a time.

Short runs are 40 and 41 rounds at one or two seeds. None of these tests calls
``main``, which writes the record names.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a11_subsistence as a11  # noqa: E402

from monetary_topology.asset import carrier_model  # noqa: E402

RESULTS = ROOT / "results"
SHORT = 40


def record(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def grid_rows(seeds: int, **over) -> list[dict]:
    """A synthetic registered grid: every graph, cell and seed once."""
    rows = []
    for graph in a11.GRAPHS:
        for m, g in a11.expected_cells():
            for s in range(seeds):
                rows.append({
                    "graph": graph, "need_multiple": m, "grace": g, "seed": s,
                    "starved": 0, "claims_conserved": True,
                    "starved_rate_financial": 0.0, "starved_rate_production": 0.0,
                    "below_floor_peak": 0, "round_gap_max": 0.0,
                    "path_rate_financial": 0.0, "path_rate_production": 0.0,
                    "below_rounds": 0, **over,
                })
    return rows


def fire(row: dict, fin: float, prod: float) -> None:
    row.update(starved=1, starved_rate_financial=fin, starved_rate_production=prod,
               below_floor_peak=1, below_rounds=1)


def by_name(criteria) -> dict:
    return {c.name.split()[0]: c for c in criteria}


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

def test_coverage_names_what_is_missing() -> None:
    rows = grid_rows(2)
    assert a11.coverage(rows, 2)["complete"] is True
    assert a11.coverage(rows, 2)["expected_runs"] == 36

    short = rows[1:]
    cov = a11.coverage(short, 2)
    assert cov["complete"] is False and len(cov["missing"]) == 1
    assert cov["duplicates"] == 0 and cov["outside_grid"] == []

    twice = rows + rows[:1]
    cov = a11.coverage(twice, 2)
    assert cov["complete"] is False and cov["duplicates"] == 1 and cov["missing"] == []

    stray = rows + [{**rows[0], "need_multiple": 0.3}]
    cov = a11.coverage(stray, 2)
    assert cov["complete"] is False and len(cov["outside_grid"]) == 1

    # The registered seed count is a separate question from the grid's shape.
    assert a11.coverage(rows, 5)["complete"] is False


def test_a_complete_firing_without_a_firing_twin_is_counted() -> None:
    rows = grid_rows(1)
    comp = [x for x in rows if x["graph"] == "complete" and x["need_multiple"] == 0.5][0]
    fire(comp, 0.5, 0.5)
    assert a11.coverage(rows, 1)["complete_firing_without_firing_twin"] == 1
    strat = [x for x in rows if x["graph"] == "stratified"
             and (x["need_multiple"], x["grace"]) == (0.5, comp["grace"])][0]
    fire(strat, 0.0, 1.0)
    assert a11.coverage(rows, 1)["complete_firing_without_firing_twin"] == 0


def test_an_incomplete_grid_is_not_judged() -> None:
    rows = record("a11_subsistence")["runs"]
    one = [x for x in rows if x["graph"] == "stratified" and x["starved"] > 0][:1]
    got = by_name(a11.evaluate(one, (True, "probe"), 5))
    for name in ("A11-2", "A11-3", "A11-4"):
        assert got[name].void is True and got[name].passed is False
        assert got[name].detail.startswith("not evaluated")

    no_complete = [x for x in rows if x["graph"] != "complete"]
    got = by_name(a11.evaluate(no_complete, (True, "probe"), 5))
    assert got["A11-4"].void is True
    assert "not an absence of data" not in got["A11-4"].detail
    assert got["A11-1"].void is False and got["A11-1"].passed is True


def test_full_grid_details_are_the_recorded_ones() -> None:
    for name in ("a11_subsistence", "a11_subsistence_drawdown", "a11_subsistence_asset"):
        rec = record(name)
        assert rec["coverage"]["complete"] is True
        shared = (rec["criteria"][0]["passed"], rec["criteria"][0]["detail"])
        got = a11.evaluate(rec["runs"], shared, rec["seeds_tested"])
        assert [(c.name, c.passed, c.detail, c.void) for c in got] == [
            (c["name"], c["passed"], c["detail"], c["void"]) for c in rec["criteria"]]


def test_exit_code_reads_the_criteria_and_the_coverage() -> None:
    ok = [a11.Criterion("a", True, ""), a11.Criterion("b", False, "", void=True)]
    full = a11.coverage(grid_rows(1), 1)
    assert a11.exit_code(ok, full) == 0
    part = a11.coverage(grid_rows(1)[1:], 1)
    assert a11.exit_code(ok, part) == 1
    assert a11.exit_code([a11.Criterion("a", False, "")], full) == 1


def test_record_names_are_reserved_for_the_registered_run() -> None:
    reg = (a11.REGISTERED_ROUNDS, a11.REGISTERED_SEEDS)
    assert a11.record_name(False, False, False, *reg) == "a11_subsistence.json"
    assert a11.record_name(False, True, False, *reg) == "a11_subsistence_drawdown.json"
    assert a11.record_name(True, False, False, *reg) == "a11_subsistence_asset.json"
    assert a11.record_name(False, False, True, *reg) == "a11_subsistence_arms.json"
    off = a11.record_name(False, False, False, SHORT, 2)
    assert "offparam" in off and off != "a11_subsistence.json"
    assert "offparam" in a11.record_name(False, False, True, a11.REGISTERED_ROUNDS, 2)


# ---------------------------------------------------------------------------
# The path, and the sentence built from it
# ---------------------------------------------------------------------------

def test_complete_graph_under_drawdown_crosses_whole() -> None:
    row = a11.one_run(1.0, 1, 0, SHORT, True, mode="drawdown")
    assert row["below_floor_close"] == 0 and row["below_floor_peak"] == 200
    assert row["below_rounds"] == SHORT // 2
    assert row["round_gap_max"] == 0.0
    assert row["returns"] == (SHORT // 2) * 200
    assert row["ever_below_financial"] == 20 and row["ever_below_production"] == 180
    assert row["below_node_rounds_production"] == (SHORT // 2) * 180
    assert row["path_rate_financial"] == row["path_rate_production"] == 0.5
    odd = a11.one_run(1.0, 1, 0, SHORT + 1, True, mode="drawdown")
    assert odd["below_floor_close"] == 200


def test_no_comp_branch_says_close_and_carries_the_peak() -> None:
    rows = grid_rows(1)
    for x in rows:
        if x["graph"] == "stratified" and x["need_multiple"] > 0:
            fire(x, 0.0, 1.0)
    comp = [x for x in rows if x["graph"] == "complete" and x["need_multiple"] == 1.0][0]
    comp.update(below_floor_peak=200, below_rounds=150)
    a4 = by_name(a11.evaluate(rows, (True, ""), 1))["A11-4"]
    assert a4.passed is True and a4.void is False
    assert a4.detail.startswith("at the close")
    assert "200 at the peak" in a4.detail
    assert "1 of its 9 runs" in a4.detail
    assert "crosses whole" in a4.detail
    assert "at any rate on this grid" not in a4.detail


def test_the_path_sentence_stands_on_the_fields() -> None:
    rows = grid_rows(1)
    comp = [x for x in rows if x["graph"] == "complete" and x["need_multiple"] == 1.0][0]
    comp.update(below_floor_peak=200, round_gap_max=0.3)
    text = a11.path_sentence(rows)
    assert "0.300" in text
    assert "crosses whole" not in text and "removes the question" not in text

    bare = grid_rows(1)
    for x in bare:
        x.pop("below_floor_peak")
        x.pop("round_gap_max")
    text = a11.path_sentence(bare)
    assert "not recorded" in text and "0.000" not in text and "removes the question" not in text

    quiet = grid_rows(1)
    text = a11.path_sentence(quiet)
    assert "0 of its 9 runs" in text and "nobody is below the floor in any round" in text


def test_exit_is_absorbing_in_the_registered_corner() -> None:
    row = a11.one_run(0.5, 1, 0, SHORT, False)
    assert row["starved"] > 0
    assert row["returns"] == 0
    assert row["ever_below_financial"] + row["ever_below_production"] == row["starved"]


def test_last_left_is_the_last_departure() -> None:
    out = np.array([[False], [True], [False], [True], [True]])
    assert a11._last_left(out).tolist() == [3]
    assert a11._last_left(np.zeros((4, 2), dtype=bool)).tolist() == [-1, -1]


# ---------------------------------------------------------------------------
# What reached the departed, and the three accounts
# ---------------------------------------------------------------------------

def test_accrual_is_what_arrived_after_leaving() -> None:
    row = a11.one_run(0.5, 1, 0, SHORT, False)
    assert 0.0 < row["accrued_after_leaving"] <= row["frozen_holdings"] + 1e-6
    assert row["gini_close_less_accrual"] != row["gini_close"]

    cut = a11.one_run(0.5, 1, 0, SHORT, False, sub_kw={"cut_payroll": True})
    assert cut["starved"] > 0 and cut["accrued_after_leaving"] == 0.0

    dd = a11.one_run(0.5, 1, 0, SHORT, False, mode="drawdown")
    assert dd["accrued_after_leaving"] is None and dd["gini_close_less_accrual"] is None

    off = a11.one_run(0.0, 1, 0, SHORT, False)
    assert off["accrued_after_leaving"] == 0.0
    assert off["gini_close_less_accrual"] == off["gini_close"]


def test_sampling_points_are_named() -> None:
    asset = a11.one_run(0.5, 1, 0, SHORT, False, asset=True)
    assert asset["claims_moved_after_record"] > 0
    assert asset["gini_claims_settled"] != asset["gini_close"]
    assert asset["gini_net_worth"] != asset["gini_claims_settled"]

    plain = a11.one_run(0.5, 1, 0, SHORT, False)
    assert plain["claims_moved_after_record"] == 0.0
    assert plain["gini_claims_settled"] == plain["gini_close"] == plain["gini_net_worth"]
    assert plain["frozen_share_claims_recorded"] == plain["frozen_share_claims_settled"]


# ---------------------------------------------------------------------------
# The structure, and the arms
# ---------------------------------------------------------------------------

def test_structure_names_the_one_switch() -> None:
    flag, detail, diffs = a11.structure_check(0, SHORT)
    assert flag is True
    assert detail == "fields differing from the control across all arms: ['subsistence']"
    assert diffs["within_graph"] == {"stratified": ["subsistence"], "complete": ["subsistence"]}
    assert diffs["between_graphs_config"] == ["spec"]
    assert diffs["between_graphs_spec"] == ["uniform_access"]

    planted = {"stratified": a11.base_config(0, SHORT, False),
               "complete": dataclasses.replace(a11.base_config(0, SHORT, True), rounds=SHORT + 1)}
    flag, _, diffs = a11.structure_check(0, SHORT, controls=planted)
    assert flag is False and diffs["between_graphs_config"] == ["rounds", "spec"]


def _floats(x):
    if isinstance(x, float):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _floats(v)
    elif isinstance(x, list):
        for v in x:
            yield from _floats(v)


def test_structure_block_is_built_on_the_records_carrier() -> None:
    plain = a11.structure_block(1, SHORT, "exit", False)
    assert plain["carrier"] == "plain"
    s, c = plain["collapsed_with_the_adjacency"][0]["stratified"], \
        plain["collapsed_with_the_adjacency"][0]["complete"]
    assert (s["wage_payers_initial"], s["wage_receivers_initial"]) == (5, 90)
    assert (c["wage_payers_initial"], c["wage_receivers_initial"]) == (200, 200)
    assert s["propensity_low_initial"]["financial"] != s["propensity_low_initial"]["production"]
    assert c["propensity_low_initial"]["financial"] == c["propensity_low_initial"]["production"]
    assert len(c["propensity_low_initial"]["financial"]) == 1
    assert s["holdings_initial_min"] < s["holdings_initial_max"]
    assert c["holdings_initial_min"] == c["holdings_initial_max"]
    assert s["routes_financial_to_production_initial"] == 0
    assert all(x == round(x, 6) for x in _floats(plain))

    asset = a11.structure_block(1, SHORT, "exit", True)
    assert asset["carrier"] == "asset"
    sa, ca = asset["collapsed_with_the_adjacency"][0]["stratified"], \
        asset["collapsed_with_the_adjacency"][0]["complete"]
    assert sa["holdings_initial_min"] != s["holdings_initial_min"]
    assert ca["holdings_initial_min"] < ca["holdings_initial_max"]
    for graph in a11.GRAPHS:
        cfg = a11.base_config(0, SHORT, graph == "complete")
        assert abs(carrier_model(cfg, asset=True).holdings.sum()
                   - carrier_model(cfg, asset=False).holdings.sum()) < 1e-9


def test_arms_move_one_thing() -> None:
    def build(arm):
        cfg = a11.arm_config(arm, 0, SHORT)
        net = carrier_model(cfg, asset=False)
        op = a11.arm_opening(arm, 0, SHORT)
        if op is not None:
            net.holdings[:] = op
        return cfg, net

    scfg, strat = build("stratified")
    ucfg = a11.base_config(0, SHORT, True)
    unif = carrier_model(ucfg, asset=False)

    acfg, adj = build("adjacency_complete")
    p = a11.primitives(adj, acfg)
    assert p["edges_initial"] == 200 * 199
    assert p["routes_financial_to_production_initial"] > 0
    assert (p["wage_payers_initial"], p["wage_receivers_initial"]) == (5, 90)
    assert p["propensity_low_initial"]["financial"] != p["propensity_low_initial"]["production"]
    assert set(adj._wage_receivers.tolist()) == set(strat._wage_receivers.tolist())
    assert acfg.spec.uniform_access is False

    _, held = build("adjacency_complete_opening_held")
    assert np.array_equal(held.holdings, strat.holdings)
    assert not np.array_equal(adj.holdings, strat.holdings)

    fcfg, flat = build("propensity_flat")
    assert np.array_equal(np.asarray(flat.adjacency), np.asarray(strat.adjacency))
    assert set(flat._p_low.tolist()) == set(unif._p_low.tolist())
    assert set(flat._p_high.tolist()) == set(unif._p_high.tolist())
    assert len(set(flat._p_low.tolist())) == 1


# ---------------------------------------------------------------------------
# The records
# ---------------------------------------------------------------------------

def test_one_run_reproduces_recorded_rows() -> None:
    for name, mode, asset in (("a11_subsistence", "exit", False),
                              ("a11_subsistence_drawdown", "drawdown", False),
                              ("a11_subsistence_asset", "exit", True)):
        rec = record(name)
        for row in rec["runs"][::31]:
            fresh = a11.one_run(row["need_multiple"], row["grace"], row["seed"],
                                rec["rounds"], row["graph"] == "complete",
                                asset=asset, mode=mode)
            assert fresh == row, (name, row["graph"], row["need_multiple"], row["seed"])
