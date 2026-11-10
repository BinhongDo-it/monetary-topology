"""Three readings A7's verdict sheet now takes from records and not from prose.

A7-A-5 registers a shape in the seed mean and per seed, and the grid records
carry one seed. Leg B ran on nine of leg A's seventeen grid points. And the two
switch cells recorded as identically zero are read at one point.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a7_continuous_c as A  # noqa: E402
from experiments import a7b_probes as P  # noqa: E402

NEEDED = (
    "a7_continuous_c.json",
    "a7_continuous_c.offparam_grid_preferential_20x300.json",
    "a7_continuous_c.offparam_dfixed_uniform_20x300.json",
    "a7_continuous_c.offparam_dfixed_preferential_20x300.json",
    "a7b_legb.offparam_uniform_20x300.json",
    "a7b_p2_room.offparam_uniform_20x300.json",
    "a7b_p2_room.offparam_preferential_20x300.json",
    "a7b_p1_retention.offparam_uniform_20x300.json",
    "a7b_p1_retention.offparam_preferential_20x300.json",
    "a7_loop_sum_by_seed.json",
    "a7b_im_switch.offparam_uniform_20x300.json",
)


def test_the_shape_is_read_in_the_seed_mean_and_per_seed() -> None:
    got = A.summarise_loop_sum(
        "uniform", (0.0, 0.5, 1.0),
        {0.0: [1.0, 2.0], 0.5: [1.5, 1.0], 1.0: [0.5, 3.0]})
    assert got["mean_by_point"] == [1.5, 1.25, 1.75]
    assert got["peak_multiple_first_seed"] == 1.5
    assert got["peak_multiple_by_seed"] == [1.5, 1.5]
    assert got["peak_multiple_of_the_seed_mean"] == pytest.approx(1.75 / 1.5)
    assert got["rising_steps_of_the_seed_mean"] == 1
    assert got["seeds_rising_above_their_own_first_point"] == 2
    assert got["falls_monotonically_in_the_seed_mean"] is False
    assert got["by_point"] == {"0": [1.0, 2.0], "0.5": [1.5, 1.0], "1": [0.5, 3.0]}
    # a series that only falls: the first seed can still hide a seed that rises
    falls = A.summarise_loop_sum(
        "uniform", (0.0, 0.5, 1.0),
        {0.0: [4.0, 2.0], 0.5: [2.0, 2.5], 1.0: [1.0, 1.0]})
    assert falls["falls_monotonically_in_the_seed_mean"] is True
    assert falls["rising_steps_of_the_seed_mean"] == 0
    assert falls["peak_multiple_first_seed"] == 1.0
    assert falls["seeds_rising_above_their_own_first_point"] == 1
    # the mean falls at every step and seed 1 rises a quarter of its own first
    # value at the first step: the per-seed clause names that step
    assert falls["falls_per_seed_within_tolerance"] is False
    assert falls["seeds_with_a_violation"] == 1
    assert [(v["seed"], v["from"], v["to"]) for v in falls["per_seed_violations"]] \
        == [(1, 0.0, 0.5)]
    # a rise inside the tolerance is not a violation
    flat = A.summarise_loop_sum(
        "uniform", (0.0, 0.5), {0.0: [1.0], 0.5: [1.005]})
    assert flat["falls_per_seed_within_tolerance"] is True
    assert flat["falls_monotonically_in_the_seed_mean"] is False


def test_the_first_seed_of_the_built_models_is_the_grid_records_seed() -> None:
    stored = json.loads(
        (ROOT / "results" / "a7_continuous_c.json").read_text(encoding="utf-8"))
    by_s = {row["s"]: row["mean_abs_loop_sum_fixed"][0] for row in stored["rows"]}
    got = A.loop_sum_by_seed(A._a3c(), "uniform", range(2), 300, grid=(0.0, 0.05))
    assert got["seeds"] == 2
    for s in (0.0, 0.05):
        assert got["by_point"][f"{s:g}"][0] == pytest.approx(by_s[s], abs=1e-9)
    # the second seed is a different graph, so it is a different number
    assert got["by_point"]["0.05"][1] != got["by_point"]["0.05"][0]


@pytest.fixture()
def sheet_dir(tmp_path, monkeypatch) -> Path:
    for name in NEEDED:
        shutil.copy2(ROOT / "results" / name, tmp_path / name)
    monkeypatch.setattr(A, "RESULTS", tmp_path)
    return tmp_path


def verdicts(folder: Path) -> dict:
    sheet = json.loads(A.write_verdicts().read_text(encoding="utf-8"))
    return {c["name"]: c for c in sheet["criteria"]} | {"note": sheet["note"]}


def test_the_sheet_reads_every_seed_and_names_the_first(sheet_dir) -> None:
    got = verdicts(sheet_dir)
    a5 = got["A7-A-5"]
    assert a5["passed"] is False
    assert "1.29 times its s = 0 value" in a5["detail"]
    assert "4.39 in the preferential one" in a5["detail"]
    assert "5 and 10 of 16 steps" in a5["detail"]
    assert "20 and 20 of 20 seeds rise" in a5["detail"]
    assert "peaks at 1.44 and 4.13" in a5["detail"]
    assert "20 and 20 of 20 seeds rise by more than" in a5["detail"]
    assert "docs section 9, changelog entry of 2026-08-16" in a5["detail"]
    assert "9 of the 9 grid points leg B ran" in got["A7-B-1"]["detail"]
    assert "9 of leg A's 17 grid points" in got["note"]
    assert "0.15, 0.3, 0.4, 0.6, 0.7, 0.8, 0.95, 0.99" in got["note"]
    states = [(n, c["passed"], c.get("void", False))
              for n, c in got.items() if n != "note"]
    assert sum(1 for _n, p, v in states if p and not v) == 3
    assert sum(1 for _n, p, v in states if not p and not v) == 4
    assert sum(1 for _n, _p, v in states if v) == 4


def _plant(sheet_dir, series) -> None:
    """Write series(k, i) as the loop sum at the k-th grid point and seed i, in
    the per-seed record and, for seed 0, in both grid records."""
    path = sheet_dir / "a7_loop_sum_by_seed.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    for arm, grid_file in (
            ("uniform", "a7_continuous_c.json"),
            ("preferential",
             "a7_continuous_c.offparam_grid_preferential_20x300.json")):
        block = record["arms"][arm]
        values = {}
        for k, s in enumerate(block["grid"]):
            block["by_point"][f"{s:g}"] = [series(k, i)
                                           for i in range(block["seeds"])]
            values[s] = series(k, 0)
        gpath = sheet_dir / grid_file
        g = json.loads(gpath.read_text(encoding="utf-8"))
        for row in g["rows"]:
            row["mean_abs_loop_sum_fixed"][0] = values[row["s"]]
        gpath.write_text(json.dumps(g), encoding="utf-8")
    path.write_text(json.dumps(record), encoding="utf-8")


def test_the_a7_a_5_flag_passes_when_every_seed_falls(sheet_dir) -> None:
    _plant(sheet_dir, lambda k, i: 100.0 - k)
    assert verdicts(sheet_dir)["A7-A-5"]["passed"] is True


def test_the_a7_a_5_flag_reads_the_per_seed_clause(sheet_dir) -> None:
    # the seed mean falls at every step, and seed 1 goes 90 -> 95 at the second
    # step, a rise of 5% of its own first value
    _plant(sheet_dir, lambda k, i: 100.0 - 10.0 * k
           + (15.0 if (i == 1 and k == 2) else 0.0))
    a5 = verdicts(sheet_dir)["A7-A-5"]
    assert a5["passed"] is False
    assert "1 and 1 of 20 seeds rise by more than" in a5["detail"]


def test_the_a7_a_5_flag_is_not_the_stored_summary(sheet_dir) -> None:
    # a stored flag that disagrees with the values is ignored
    path = sheet_dir / "a7_loop_sum_by_seed.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    for arm in record["arms"].values():
        arm["falls_monotonically_in_the_seed_mean"] = True
        arm["falls_per_seed_within_tolerance"] = True
    path.write_text(json.dumps(record), encoding="utf-8")
    assert verdicts(sheet_dir)["A7-A-5"]["passed"] is False


def test_the_a7_a_2_detail_reads_d_fixed(sheet_dir) -> None:
    a2 = verdicts(sheet_dir)["A7-A-2"]
    assert "On D_fixed, the estimator it names" in a2["detail"]
    assert "negative in 8/20 seeds in the uniform arm and 12/20" in a2["detail"]
    assert "+20.1927 to -0.2439" in a2["detail"]
    assert "on D_reach the same step reads +18.9854 to -0.1157" in a2["detail"]


def test_the_a7_b_4_flag_reads_the_probe_records(sheet_dir) -> None:
    assert verdicts(sheet_dir)["A7-B-4"]["passed"] is True
    path = sheet_dir / "a7b_p1_retention.offparam_preferential_20x300.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["rows"] = record["rows"][:-1]
    path.write_text(json.dumps(record), encoding="utf-8")
    b4 = verdicts(sheet_dir)["A7-B-4"]
    assert b4["passed"] is False
    assert "carry not all of the 9 points" in b4["detail"]


def test_the_sheet_refuses_a_per_seed_record_that_is_another_object(sheet_dir) -> None:
    path = sheet_dir / "a7_loop_sum_by_seed.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["arms"]["preferential"]["by_point"]["0.05"][0] *= 1.01
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="preferential grid record"):
        A.write_verdicts()


def test_the_switch_cells_are_reported_as_read(sheet_dir) -> None:
    b5 = verdicts(sheet_dir)["A7-B-5"]
    assert b5["passed"] is False and b5["void"] is True
    assert "does not hold" in b5["detail"]
    assert "in 20 and 20 of 20 seeds" in b5["detail"]
    assert "-0.0548 for I and -0.0540 for M" in b5["detail"]
    # a record in which one switch cell ends where the control does
    path = sheet_dir / "a7b_im_switch.offparam_uniform_20x300.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["point"]["final_holdings_differ_from_none"]["M"] = 0
    path.write_text(json.dumps(record), encoding="utf-8")
    assert "in 20 and 0 of 20 seeds" in verdicts(sheet_dir)["A7-B-5"]["detail"]


def test_a_difference_is_taken_within_seed() -> None:
    cell = [{"k": 1.0}, {"k": 5.0}, {"k": 2.0}]
    control = [{"k": 2.0}, {"k": 4.0}, {"k": 2.0}]
    got = P.difference_block(cell, control, "k")
    assert got["by_seed"] == [-1.0, 1.0, 0.0]
    assert got["mean"] == 0.0 and got["range"] == [-1.0, 1.0]
    assert (got["n_positive"], got["n_negative"]) == (1, 1)
    assert got["same_sign_across_seeds"] is False
    assert P.difference_block([{"k": 1.0}], [{"k": 3.0}], "k")[
        "same_sign_across_seeds"] is True


def test_the_switch_cells_move_the_holdings(monkeypatch) -> None:
    got = P.im_point(range(2), 120, P.IM_POINT, "uniform")
    assert got["final_holdings_differ_from_none"] == {"I": 2, "M": 2}
    assert set(got["d"]) == {"I", "M"}
    assert got["d"]["I"]["log_inv_hhi_prod"]["n_negative"] == 2
    # a cell that switches nothing on ends exactly where the control does
    monkeypatch.setitem(P.IM_CELLS, "I", {})
    same = P.im_point(range(2), 120, P.IM_POINT, "uniform")
    assert same["final_holdings_differ_from_none"]["I"] == 0
    assert same["d"]["I"]["log_inv_hhi_prod"]["by_seed"] == [0.0, 0.0]
