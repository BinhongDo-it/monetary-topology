"""What the ratchet stage writes behind A6-20 to A6-23.

Four verdicts were scored from three blocks that were computed, printed and not
written, so the record held the verdicts without their numbers. And A6-20's
test on the mismatched pairs is that the overlap occurs in the run, which is
not the same statement as "in every round".
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

from experiments import a6_ratchet as R  # noqa: E402


def test_the_overlap_is_counted_round_by_round() -> None:
    got = R.overlap_stats(np.array([0, 2, 0, 5]))
    assert got == {"most": 5, "fewest": 0, "rounds_with_none": 2, "rounds": 4}
    # a run in which the overlap occurs in every round
    assert R.overlap_stats(np.array([1, 3, 2]))["rounds_with_none"] == 0
    assert R.overlap_stats(np.array([]))== {
        "most": 0, "fewest": 0, "rounds_with_none": 0, "rounds": 0}


def test_a_recorded_block_carries_no_machine_digits() -> None:
    block = {
        "level": 0.123456789012345,
        "collapsed": 3.1e-85,
        "negative_residual": -4.4e-16,
        "zero": 0.0,
        "open": np.bool_(True),
        "count": np.int64(7),
        "unsolved": None,
        "grown": float("inf"),
        "undefined": float("nan"),
        "nested": [(1e-13, 2.5), {"k": np.float64(1.0000000000001)}],
        3: "an integer key",
    }
    got = R.recordable(block)
    assert got["level"] == 0.123456789
    assert got["collapsed"] == "below 1e-12"
    assert got["negative_residual"] == "below 1e-12"
    assert got["zero"] == 0.0
    assert got["open"] is True and got["count"] == 7 and got["unsolved"] is None
    assert got["grown"] == "inf" and got["undefined"] == "nan"
    assert got["nested"] == [["below 1e-12", 2.5], {"k": 1.0}]
    assert got["3"] == "an integer key"
    # and it goes through the strict encoder, which inf and nan would not
    json.dumps(got, allow_nan=False)


def sides(drift: float) -> dict:
    return {
        "worst_claim_drift": drift,
        "cells": {"levy=layer/rebate=layer": {"worst_claim_drift": drift,
                                              "worst_both_sides": 0}},
    }


def test_the_drift_is_recorded_as_under_its_bound_or_not() -> None:
    under = R.sides_for_record(sides(1.9e-11))
    assert under["claim_drift_under_the_bound"] is True
    assert under["claim_drift_bound"] == R.A6_20_DRIFT
    assert "worst_claim_drift" not in under
    cell = under["cells"]["levy=layer/rebate=layer"]
    assert cell == {"worst_both_sides": 0, "claim_drift_under_the_bound": True}
    over = R.sides_for_record(sides(2.0e-6))
    assert over["claim_drift_under_the_bound"] is False
    assert over["cells"]["levy=layer/rebate=layer"][
        "claim_drift_under_the_bound"] is False


@pytest.fixture(scope="module")
def short_sides() -> dict:
    return R.rebate_sides(range(1), 300, R.A6_9_RATE)


def test_the_overlap_occurs_and_not_in_every_round(short_sides) -> None:
    cells = short_sides["cells"]
    for key, cell in cells.items():
        per_seed = cell["both_sides_by_seed"]
        assert [s["seed"] for s in per_seed] == [0]
        assert cell["rounds_counted"] == 300
        assert cell["worst_both_sides"] == max(s["most"] for s in per_seed)
        assert cell["fewest_both_sides"] == min(s["fewest"] for s in per_seed)
        assert cell["rounds_with_none"] == sum(
            s["rounds_with_none"] for s in per_seed)
        if cell["levy_base"] == cell["rebate_base"]:
            # largest zero means every round zero
            assert cell["rounds_with_none"] == 300, key
    mirrored = cells["levy=layer/rebate=threshold"]
    # the criterion's own test passes on this cell: the overlap occurs
    assert mirrored["worst_both_sides"] > 0
    # and it does not occur in every round, which is what the page used to say
    assert mirrored["rounds_with_none"] == 137
    assert mirrored["fewest_both_sides"] == 0
    assert short_sides["passed"] is True


def test_the_record_carries_the_blocks_its_verdicts_are_scored_from(
        tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(sys, "argv", ["a6_ratchet", "--smoke", "--quiet"])
    R.main()
    written = list((tmp_path / "results").iterdir())
    assert len(written) == 1
    record = json.loads(written[0].read_text(encoding="utf-8"))
    names = {c["name"]: c for c in record["criteria"]}
    # each verdict has the block it was scored from beside it
    assert names["A6-20"]["passed"] == record["rebate_sides"]["passed"]
    assert names["A6-21"]["passed"] == record["rho_scaling"]["passed"]
    assert names["A6-22"]["passed"] == record["rebase_curve"]["A6-22"]
    assert names["A6-23"]["passed"] == record["rebase_curve"]["A6-23"]
    cell = record["rebate_sides"]["cells"]["levy=layer/rebate=threshold"]
    assert len(cell["both_sides_by_seed"]) == record["seeds"]
    assert "of the rounds counted over all seeds" in names["A6-20"]["detail"]
    assert f"{cell['rounds_with_none']} of {cell['rounds_counted']}" in (
        names["A6-20"]["detail"])
    # only the mismatched pairs are listed there: for a matched pair every
    # round has nobody on both sides, and that is its criterion, not a caveat
    assert names["A6-20"]["detail"].count(" of 600") == 2
    assert record["rho_scaling"]["cells"] and record["rebase_curve"]["columns"]
    # no residual is written by its digits in the three blocks
    text = json.dumps([record["rebate_sides"], record["rho_scaling"],
                       record["rebase_curve"]])
    assert "worst_claim_drift" not in text
    json.loads(text, parse_constant=lambda name: pytest.fail(name))
