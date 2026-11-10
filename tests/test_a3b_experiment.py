"""What A3b's driver reads beside its six checkpoints.

Four readings, each with an input that has to make it say something else: the
opening as distinct from the end of round one, the path between checkpoints,
the tier the occupancy transfer hands out, and A3-4 on each construction.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a3b_construction as B  # noqa: E402

warnings.simplefilter("ignore", B.DesignDeviation)

AUCTION = {**B.FIXED, **B.ARMS["auction"]}
OCCUPANCY = {**B.FIXED, **B.ARMS["occupancy"]}
PRE_A3B = dict(B.ARMS["auction"])


def test_round_one_is_not_the_opening() -> None:
    opening = B._snapshot(B.construct(0, 300, **OCCUPANCY))
    one_round = B._snapshot(B.build(0, 1, **OCCUPANCY))
    assert opening[1] > one_round[1]            # holders already leave in round one
    arm = B.run_arm("occupancy", OCCUPANCY, range(1), 1)
    assert arm.opening["prod_holders"] == opening[1]
    assert arm.prod_holders[1] == one_round[1]
    assert arm.opening["ownership"] == opening[0] != arm.ownership[1]
    # the opening does not depend on how long the run is going to be
    assert B._snapshot(B.construct(0, 1, **OCCUPANCY)) == opening


class Scripted:
    """Three nodes and a script of who holds at the end of each round."""

    def __init__(self, script) -> None:
        self._is_production = np.array([False, True, True])
        self._script = [np.array(row, dtype=float) for row in script]
        self.units = self._script[0][:, None].copy()

    def _post_round(self, t: int) -> None:
        self.units = self._script[t + 1][:, None].copy()

    def run(self) -> None:
        for t in range(len(self._script) - 1):
            self._post_round(t)


def test_the_path_counts_by_hand(monkeypatch) -> None:
    script = [
        [1, 1, 0],    # opening: the financial node and one production node
        [1, 0, 0],    # round 1: the production layer is empty
        [0, 0, 1],    # round 2: another production node enters for the first time
        [1, 0, 0],    # round 3: the financial node, having sold out, holds again
    ]
    monkeypatch.setattr(B, "construct", lambda seed, rounds, **kw: Scripted(script))
    _model, got = B.path(7, 3)
    assert got["seed"] == 7
    assert got["production_layer_empty_from_round"] == 1
    assert got["production_holder_after_it_emptied"] is True
    # a first entry is not a return; nobody in the production layer came back
    assert got["production_returns_after_selling_out"] == 0
    assert got["financial_returns_after_selling_out"] == 1
    assert got["rounds_ending_with_more_holders"] == 0
    assert got["rounds_ending_with_more_financial_holders"] == 1
    assert got["rounds_ending_with_more_production_holders"] == 1

    # a production node that sells out and comes back is counted as that
    monkeypatch.setattr(
        B, "construct",
        lambda seed, rounds, **kw: Scripted([[0, 1, 0], [0, 0, 0], [0, 1, 0]]))
    _model, got = B.path(0, 2)
    assert got["production_returns_after_selling_out"] == 1
    assert got["production_holder_after_it_emptied"] is True

    # the count is of returns, not of nodes: one node back twice counts twice
    monkeypatch.setattr(
        B, "construct",
        lambda seed, rounds, **kw: Scripted(
            [[1, 0, 0], [0, 0, 0], [1, 0, 0], [0, 0, 0], [1, 0, 0]]))
    _model, got = B.path(0, 4)
    assert got["financial_returns_after_selling_out"] == 2
    assert got["production_returns_after_selling_out"] == 0

    # a layer that never empties has no round to report
    monkeypatch.setattr(
        B, "construct",
        lambda seed, rounds, **kw: Scripted([[0, 1, 0], [0, 1, 0]]))
    _model, got = B.path(0, 1)
    assert got["production_layer_empty_from_round"] is None
    assert got["production_holder_after_it_emptied"] is None


def test_the_path_on_the_registered_runs() -> None:
    model, got = B.path(0, 300, **AUCTION)
    assert got["production_layer_empty_from_round"] == 90
    assert got["production_holder_after_it_emptied"] is False
    assert got["production_returns_after_selling_out"] == 0
    assert got["rounds_ending_with_more_holders"] == 11
    assert got["rounds_ending_with_more_production_holders"] == 0
    # reading the path does not change the run
    assert np.array_equal(model.units, B.build(0, 300, **AUCTION).units)
    # the one return on record: the pre-A3b arm, seed 3
    _m, old = B.path(3, 300, **PRE_A3B)
    assert old["production_returns_after_selling_out"] == 1
    assert old["production_holder_after_it_emptied"] is False


def test_the_transfer_hands_the_next_tier_to_the_least_claims() -> None:
    got = B.transfer_tiers(0, 300, **OCCUPANCY)
    assert (got["drawn"], got["low_tier_units"]) == (140, 132)
    assert got["drawn_in_the_production_layer"] == 127
    assert got["drawn_past_the_low_tier"] == 8
    assert got["they_hold_one_unit_of_the_next_tier_and_nothing_else"] is True
    assert got["they_are_in_the_production_layer"] == 8
    assert got["drawn_holding_the_next_tier_and_no_low_unit"] == 8
    # hand it a model whose two poorest drawn nodes hold low-tier units after
    # all: the reading has to say the walk did not do what it describes
    fake = SimpleNamespace(
        _opening_bypass=np.array([True, True, True, True, False]),
        _is_production=np.array([False, True, True, True, True]),
        _claims_0=np.array([9.0, 7.0, 3.0, 1.0, 5.0]),
        supply=[2, 5, 1],
        units=np.array([[1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0], [0, 0, 0]],
                       dtype=float),
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(B, "construct", lambda seed, rounds, **kw: fake)
        wrong = B.transfer_tiers(0, 1)
        assert (wrong["drawn"], wrong["drawn_past_the_low_tier"]) == (4, 2)
        assert wrong["they_hold_one_unit_of_the_next_tier_and_nothing_else"] is False
        fake.units[2] = [0, 1, 0]
        fake.units[3] = [0, 1, 0]
        right = B.transfer_tiers(0, 1)
        assert right["they_hold_one_unit_of_the_next_tier_and_nothing_else"] is True
        assert right["they_are_in_the_production_layer"] == 2
        assert right["drawn_in_the_production_layer"] == 3
    # an arm with no transfer has no drawn set, and the reading says so
    none = B.transfer_tiers(0, 300, **AUCTION)
    assert (none["drawn"], none["drawn_past_the_low_tier"]) == (0, 0)
    assert none["they_hold_one_unit_of_the_next_tier_and_nothing_else"] is False


def test_a3_4_moves_with_the_tier_mix_and_only_with_it() -> None:
    runs = [B.build(0, 300, **AUCTION)]
    got = B.a3_4_reading(runs)
    assert got["void"] is False
    found = B.terms_differential(runs)
    assert got["ledger"] == round(found[0], 10)
    assert got["graph"] == round(found[1], 10)
    rel = abs(found[0] - found[1]) / abs(found[1])
    assert got["relative_error"] == round(rel, 8)
    assert got["within_the_registered_tolerance"] is (rel < B.A3_4_TOLERANCE)
    assert got["tier_mix_term"] == pytest.approx(got["ledger"] - got["graph"], abs=1e-9)
    assert got["the_gap_is_the_tier_mix_term"] is True
    assert got["trades_better_worse_by_seed"] == [[298, 30]]
    # terms that do not factor into a tier part and a node part, for one member
    # of the better-termed group: the gap is then not a tier-mix term and the
    # flag has to drop
    better, _worse = B.terms_pair(runs[0])
    runs[0].terms = runs[0].terms.copy()
    runs[0].terms[int(better[0]), 1] *= 1.02
    assert B.a3_4_reading(runs)["the_gap_is_the_tier_mix_term"] is False


def test_a3_4_has_no_reading_on_the_occupancy_arm() -> None:
    got = B.a3_4_reading([B.build(0, 300, **OCCUPANCY)])
    assert got["void"] is True
    assert got["trades_better_worse_by_seed"] == [[423, 0]]
    assert "ledger" not in got
