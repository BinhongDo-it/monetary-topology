"""Stage A12: what the rows record, and what the criteria are allowed to read.

**The criteria are judged only on the registered grid.** Every arm at every
edge and elasticity, once. Five rows taken out of the record used to leave all
seven PASS; here A12-2 to A12-7 are not evaluated on such rows.

**``starved`` counts two objects.** Under the exit floor it counts nodes that
have left the graph; under drawdown it counts nodes below the floor this round,
all still in the graph. A12-5 reads each family on its own pairs, so a count
on one object cannot decide the branch printed for the other.

**The reversible boolean is read on the rows.** It leaves the edge sets
alone and moves nodes underneath them; A12-6 prints how many.

Each test that guards a flag first plants the error the flag exists for and
checks that the flag moves. The fixture is the registered record on disk;
the short runs are 30 rounds. None of these tests calls ``main``.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a12_mechanisms as a12  # noqa: E402

RESULTS = ROOT / "results"
SHORT = 30
OLD_FIELDS = {
    "arm", "f2i", "elasticity", "mr_ratio", "mara_ratio", "m_ratio",
    "gini_open", "gini_close", "top1_wealth", "top10_wealth", "top1_open",
    "top10_open", "resource_levels", "support_ratio", "wage_funding",
    "wage_owed_ratio", "starved", "transfer_rate", "written_off_total",
    "claims_conserved", "surfaces", "all_four",
}


def record() -> dict:
    return json.loads((RESULTS / "a12_mechanisms.json").read_text(encoding="utf-8"))


def a8() -> dict:
    return json.loads((RESULTS / "a8_coverage.json").read_text(encoding="utf-8"))


def judge(rows: list[dict]) -> dict:
    crit = a12.build_criteria(rows, a12.ARMS, a12.BASE_CARRIER,
                              a12.REGISTERED_ROUNDS, a12.REGISTERED_SEED,
                              a8(), "a8_coverage.json")
    return {c.name[:6]: c for c in crit}


def by_cell(rows, arm):
    return {(x["f2i"], x["elasticity"]): x for x in rows if x["arm"] == arm}


# --- the grid ---------------------------------------------------------------

def test_record_judges_seven_pass_on_its_own_grid():
    rows = record()["runs"]
    assert a12.coverage(rows, a12.ARMS, a12.BASE_CARRIER)["complete"]
    crit = judge(rows)
    assert all(c.passed and not c.void for c in crit.values())
    assert a12.exit_code(list(crit.values())) == 0


def test_five_rows_removed_void_six_criteria():
    rows = [x for x in record()["runs"]
            if not (x["arm"] == "off" and x["f2i"] == 30)]
    assert len(rows) == 625
    crit = judge(rows)
    assert crit["A12-1 "].passed and not crit["A12-1 "].void
    for k in ("A12-2 ", "A12-3 ", "A12-4 ", "A12-5 ", "A12-6 ", "A12-7 "):
        assert crit[k].void and not crit[k].passed
    assert a12.exit_code(list(crit.values())) == 1


def test_a_repeated_row_voids():
    rows = record()["runs"]
    rows = rows + [rows[0]]
    cov = a12.coverage(rows, a12.ARMS, a12.BASE_CARRIER)
    assert cov["duplicates"] == 1 and not cov["complete"]
    assert judge(rows)["A12-2 "].void


def test_a_row_off_the_grid_voids():
    rows = copy.deepcopy(record()["runs"])
    rows[0]["f2i"] = 7
    cov = a12.coverage(rows, a12.ARMS, a12.BASE_CARRIER)
    assert cov["outside_grid"] and cov["missing"] and not cov["complete"]
    assert judge(rows)["A12-7 "].void


def test_undecidable_is_not_void_in_the_exit_code():
    ok = a12.Criterion("x", False, "", undecidable=True)
    void = a12.Criterion("y", False, "", undecidable=True, void=True)
    assert a12.exit_code([ok]) == 0
    assert a12.exit_code([ok, void]) == 1


# --- A12-3 ------------------------------------------------------------------

def test_a12_3_names_what_it_compares_and_fails_on_a_different_set():
    rows = record()["runs"]
    c = judge(rows)["A12-3 "]
    assert c.passed and "600 rounds" in c.detail and "this run 300" in c.detail
    rows = copy.deepcopy(rows)
    for x in rows:
        if x["arm"] == "off" and x["f2i"] == 20:
            x["all_four"] = False
    assert not judge(rows)["A12-3 "].passed


# --- A12-5 ------------------------------------------------------------------

def test_a12_5_reads_each_family_on_its_own_object():
    reading = a12.transfer_reading(record()["runs"])
    assert set(reading) == {"exit", "drawdown"}
    assert reading["exit"]["branch"].startswith("branch C")
    assert reading["exit"]["totals_down_level_up"]["starved"] == [21, 19, 50]
    assert reading["drawdown"]["branch"].startswith("branch A")
    assert reading["drawdown"]["dropped_one_directional"] == ["support_ratio"]
    assert "not a return to circulation" in reading["drawdown"]["branch"]


def test_the_pooled_count_would_have_read_another_branch():
    """The planted error: the old reading added the two families together."""
    rows = record()["runs"]
    pooled = [0, 0, 0]
    for b, a in a12.TRANSFER_PAIRS:
        for i, v in enumerate(a12._direction_counts(rows, b, a, "starved")):
            pooled[i] += v
    assert pooled == [64, 20, 51]          # better than worse: branch A pooled
    assert a12.transfer_reading(rows)["exit"]["branch"].startswith("branch C")


def test_the_drawdown_pair_cannot_move_the_exit_branch():
    rows = copy.deepcopy(record()["runs"])
    for x in rows:
        if x["arm"] == "drawdown+transfer":
            x["starved"] = 0
    reading = a12.transfer_reading(rows)
    assert reading["exit"]["branch"].startswith("branch C")
    assert reading["exit"]["totals_down_level_up"]["starved"] == [21, 19, 50]


def test_a12_5_unpaired_cells_fail_and_say_so():
    rows = [x for x in record()["runs"]
            if not (x["arm"] == "drawdown+transfer" and x["f2i"] == 30)]
    c = a12.transfer_criterion(rows, a12.hits_of(rows, a12.ARMS))
    assert not c.passed and not c.undecidable and "PAIRING FAILED" in c.detail


def test_a12_5_family_with_nothing_left_reads_undecidable():
    rows = copy.deepcopy(record()["runs"])
    for x in rows:
        if x["arm"] in ("floor+transfer", "both+transfer"):
            base = by_cell(rows, "floor" if x["arm"] == "floor+transfer" else "both")
            b = base[(x["f2i"], x["elasticity"])]
            x["starved"] = b["starved"] + 1
            x["support_ratio"] = b["support_ratio"] + 1
    reading = a12.transfer_reading(rows)
    assert reading["exit"]["judged_on"] == []
    assert reading["exit"]["branch"].startswith("undecidable")


def test_a12_5_asset_carrier_has_no_object():
    rows = [x for x in record()["runs"] if x["transfer_rate"] == 0.0]
    c = a12.transfer_criterion(rows, a12.hits_of(rows, a12.ARMS))
    assert c.undecidable and not c.passed


# --- A12-6 ------------------------------------------------------------------

def test_a12_6_prints_what_the_reversible_boolean_moves():
    rows = record()["runs"]
    rev = a12.reversible_reading(rows)
    assert rev["returns"] == 375
    assert rev["cells_closing_membership_differs"] == 4
    assert rev["cells_all_four_differs"] == 0
    assert rev["gini_close_gap_max"] == 0.271975
    assert rev["in_graph_close_at_that_cell"] == {"floor": 49, "floor payroll kept": 125}
    c = judge(rows)["A12-6 "]
    assert c.passed and "375 returns" in c.detail and "moves nothing" not in c.detail


def test_a12_6_rows_without_path_fields_say_not_recorded():
    rows = copy.deepcopy(record()["runs"])
    for x in rows:
        x.pop("returns", None)
    assert a12.reversible_reading(rows) == {"cells": 45, "recorded": False}
    assert "not recorded" in judge(rows)["A12-6 "].detail


def test_a12_6_reading_follows_the_rows():
    rows = copy.deepcopy(record()["runs"])
    floor = by_cell(rows, "floor")
    for x in rows:
        if x["arm"] == "floor payroll kept":
            x["returns"] = 0
            x["in_graph_close"] = floor[(x["f2i"], x["elasticity"])]["in_graph_close"]
            x["gini_close"] = floor[(x["f2i"], x["elasticity"])]["gini_close"]
    rev = a12.reversible_reading(rows)
    assert rev["returns"] == 0 and rev["cells_closing_membership_differs"] == 0
    assert rev["gini_close_gap_max"] == 0.0
    detail = judge(rows)["A12-6 "].detail
    assert "moves nothing on this carrier" in detail and "not inert" not in detail


# --- the rows ---------------------------------------------------------------

def test_switches_off_leave_the_row_as_it_was():
    row = a12.one_run("floor", 8, 0.5, SHORT, 0)
    assert set(row) == OLD_FIELDS
    on = a12.one_run("floor", 8, 0.5, SHORT, 0, clocks=True, paths=True)
    assert all(on[k] == row[k] for k in OLD_FIELDS)


def test_starved_object_is_named_per_mode():
    dd = a12.one_run("floor drawdown", 30, 0.0, SHORT, 0, paths=True)
    assert dd["starved_object"] == "below_floor_in_graph"
    assert dd["in_graph_close"] == a12.BASE_CARRIER.nodes
    ex = a12.one_run("floor", 30, 0.0, SHORT, 0, paths=True)
    assert ex["starved_object"] == "out_of_graph"
    assert ex["in_graph_close"] == a12.BASE_CARRIER.nodes - ex["starved"]
    assert ex["returns"] == 0                      # absorbing wall
    off = a12.one_run("off", 30, 0.0, SHORT, 0, paths=True)
    assert off["starved_object"] == "none" and off["ever_out"] == 0


def test_the_clocks_separate_on_the_fiscal_arm():
    row = a12.one_run("floor+transfer", 8, 0.5, SHORT, 0, clocks=True, paths=True)
    assert row["gini_init"] != row["gini_open"]
    assert row["claims_moved_after_record"] > 0
    assert row["gini_post"] != row["gini_close"]
    plain = a12.one_run("floor", 8, 0.5, SHORT, 0, clocks=True, paths=True)
    assert plain["claims_moved_after_record"] == 0.0
    assert plain["gini_post"] == plain["gini_close"]
    assert plain["gini_net_worth_post"] == plain["gini_post"]


def test_record_name_keeps_off_parameter_runs_apart():
    c = a12.BASE_CARRIER
    assert a12.record_name(c, 300, 0) == "a12_mechanisms.json"
    assert a12.record_name(c, 20, 0) == "a12_mechanisms.offparam_s0x20.json"
    assert a12.record_name(c, 300, 1) == "a12_mechanisms.offparam_s1x300.json"
