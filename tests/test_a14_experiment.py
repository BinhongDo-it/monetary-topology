"""What A14's driver reads, and what its record now says about it.

A14 says every cell ran and the construction's own cell reproduces. Its flag
read the number of distinct cells and that the top1% reading was finite, and
nothing else about them, so a grid short of a seed, or one whose two
construction arms disagreed, passed; it now reads both. On the asset carrier
the fields named ``wealth`` read ``claims_recorded``, the last history row;
settled claims and net worth live on the model and are written beside them,
and the grid is run once more with the asset layer held per node.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a14_scale as A  # noqa: E402

from monetary_topology.asset import AssetSpec, carrier_model  # noqa: E402
from monetary_topology.mechanisms import gini  # noqa: E402
from monetary_topology.network import NetworkConfig  # noqa: E402

OLD_KEYS = {
    "n", "fraction", "arm", "seed", "layer1_size", "l1_out_degree",
    "l1_density", "edges", "top1_wealth", "top01_wealth", "gini",
    "support_ratio", "support_close", "volume_ratio", "mr_close",
    "top1_nodes", "top01_nodes",
}


# -- a synthetic grid: 27 cells, the construction's two arms identical ---------

def _value(n: int, fraction: float, arm: str, seed: int, salt: float) -> float:
    a = {"fixed": 1.0, "scaled": 2.0, "null": 3.0}[arm]
    return round(0.1 + (n % 97) * 1e-3 + fraction * 0.3 + a * 0.01
                 + seed * 1e-3 + salt, 6)


def grid_rows(seeds: int = 5, asset: bool = False) -> list[dict]:
    rows = []
    for n in A.SIZES:
        for f in A.FRACTIONS:
            for arm in ("fixed", "scaled", "null"):
                # at the construction's own cell the scaled arm IS the fixed arm
                src = ("fixed" if (n, f, arm) == (200, 0.10, "scaled") else arm)
                for seed in range(seeds):
                    row = {
                        "n": n, "fraction": f, "arm": arm, "seed": seed,
                        "layer1_size": round(n * f), "l1_out_degree": 6,
                        "l1_density": 0.3, "edges": 1000 + seed,
                        "top1_wealth": _value(n, f, src, seed, 0.0),
                        "top01_wealth": _value(n, f, src, seed, 0.01),
                        "gini": (0.007 if arm == "null"
                                 else _value(n, f, src, seed, 0.5)),
                        "support_ratio": _value(n, f, src, seed, 0.2),
                        "support_close": _value(n, f, src, seed, 9.0),
                        "volume_ratio": _value(n, f, src, seed, 20.0),
                        "mr_close": _value(n, f, src, seed, 30.0),
                        "top1_nodes": max(1, n // 100),
                        "top01_nodes": max(1, n // 1000),
                    }
                    if asset:
                        # claims rise with n on the fixed arm and fall on the
                        # scaled one; net worth falls on both; settled sits
                        # just above claims.
                        slope = {200: 0.0, 500: 0.03, 1000: 0.06}[n]
                        claims = 0.30 + (slope if src == "fixed" else -slope) \
                            + seed * 1e-3
                        worth_top = 0.60 - 2 * slope + seed * 1e-3
                        if arm == "null":
                            # identical agents: a top share near k/n, well
                            # outside the span of the eighteen stratified cells
                            claims, worth_top = 0.011, 0.05
                        row["top1_wealth"] = round(claims, 6)
                        held = arm != "null" or n < 1000
                        # held units are 4/5 of net worth at 200 nodes and
                        # 1/2 at 1000 on the stratified arms
                        marked = {200: 400.0, 500: 200.0, 1000: 100.0}[n]
                        row["accounts"] = {
                            "claims_settled": {
                                "top1_wealth": round(claims + 0.002, 6),
                                "top01_wealth": 0.1, "gini": 0.5},
                            "net_worth": {
                                "top1_wealth": round(worth_top, 6),
                                "top01_wealth": 0.2,
                                "gini": 0.4 if held else 0.007},
                            "last_round_cash_moved": held,
                            "last_round_largest_change": 3.5 if held else 0.0,
                            "claims_per_node_initial": round(100.0 / n, 6),
                            "supply_by_tier_initial": [60, 30, 10],
                            "price_initial": [0.5, 1.0, 2.0],
                            "lowest_stretch_gate_initial": 0.166667,
                            "units_initial": 90 if held else 0,
                            "units_initial_by_tier": [60, 30, 0] if held else [0, 0, 0],
                            "owners_initial": 90 if held else 0,
                            "max_units_one_node_initial": 1 if held else 0,
                            "units_close_settled": 90 if held else 0,
                            "owners_close_settled": 20 if held else 0,
                            "max_units_one_node_close_settled": (20 + seed) if held else 0,
                            "marked_units_close_settled": marked if held else 0.0,
                            "claims_close_settled": 100.0,
                            "asset_layer_inert": not held,
                        }
                    rows.append(row)
    return rows


def a14_1(rows: list[dict], seeds: int | None = 5):
    return A.evaluate(rows, 300, seeds)[0]


def marks(rows: list[dict], seeds: int | None = 5) -> list[bool]:
    return [bool(c.passed) for c in A.evaluate(rows, 300, seeds)]


# -- A14-1 reads the seeds of every cell and the two construction arms ---------

def test_an_intact_grid_passes_a14_1_and_says_what_it_read() -> None:
    c = a14_1(grid_rows())
    assert c.passed
    assert "27/27 cells" in c.detail
    assert "Every cell carries seeds 0-4." in c.detail
    assert "agree row for row on all 16 fields" in c.detail


def test_a14_1_fails_when_one_cell_is_short_of_a_seed() -> None:
    # the construction's own fixed arm loses its last seed
    rows = [r for r in grid_rows() if not (
        r["n"] == 200 and r["fraction"] == 0.10 and r["arm"] == "fixed"
        and r["seed"] == 4)]
    assert len(rows) == 134
    assert not a14_1(rows).passed
    # and a cell that has nothing to do with the construction
    rows = [r for r in grid_rows() if not (
        r["n"] == 1000 and r["fraction"] == 0.05 and r["arm"] == "null"
        and r["seed"] == 2)]
    c = a14_1(rows)
    assert not c.passed
    assert "1 cells do not carry seeds 0-4" in c.detail
    # nothing else in the table is moved by it
    assert marks(rows)[1:] == marks(grid_rows())[1:]


def test_a14_1_fails_when_a_seed_is_repeated_in_place_of_another() -> None:
    rows = grid_rows()
    src = next(r for r in rows if (r["n"], r["fraction"], r["arm"], r["seed"])
               == (500, 0.05, "null", 2))
    for i, r in enumerate(rows):
        if (r["n"], r["fraction"], r["arm"], r["seed"]) == (500, 0.05, "null", 3):
            rows[i] = dict(src)
    assert len(rows) == 135
    assert not a14_1(rows).passed


def test_a14_1_fails_when_the_grid_carries_fewer_seeds_than_it_was_asked_for() -> None:
    rows = [r for r in grid_rows() if r["seed"] < 4]
    assert not a14_1(rows, seeds=5).passed
    # asked for four, it is whole
    assert a14_1(rows, seeds=4).passed
    # a caller holding only rows gets the seeds the rows carry
    assert a14_1(rows, seeds=None).passed


def test_a14_1_fails_when_the_two_construction_arms_differ() -> None:
    # every scaled row of the construction's cell reads another share
    rows = grid_rows()
    for r in rows:
        if (r["n"], r["fraction"], r["arm"]) == (200, 0.10, "scaled"):
            r["top1_wealth"] = 0.9
    c = a14_1(rows)
    assert not c.passed
    assert "do not agree row for row" in c.detail and "top1_wealth" in c.detail
    # one seed, one field that the printed means do not show
    rows = grid_rows()
    for r in rows:
        if (r["n"], r["fraction"], r["arm"], r["seed"]) == (200, 0.10, "scaled", 3):
            r["support_close"] += 0.5
    c = a14_1(rows)
    assert not c.passed and "support_close" in c.detail
    # two seeds swapped: the means agree and the rows do not
    rows = grid_rows()
    pair = [r for r in rows if (r["n"], r["fraction"], r["arm"]) == (200, 0.10, "scaled")
            and r["seed"] in (0, 1)]
    for k in ("top1_wealth", "gini"):
        pair[0][k], pair[1][k] = pair[1][k], pair[0][k]
    assert not a14_1(rows).passed
    # on the asset carrier the accounts are a field of the row like any other
    rows = grid_rows(asset=True)
    assert a14_1(rows).passed and "all 17 fields" in a14_1(rows).detail
    for r in rows:
        if (r["n"], r["fraction"], r["arm"], r["seed"]) == (200, 0.10, "scaled", 1):
            r["accounts"] = copy.deepcopy(r["accounts"])
            r["accounts"]["net_worth"]["gini"] = 0.41
    c = a14_1(rows)
    assert not c.passed and "accounts" in c.detail


def test_a14_1_still_fails_on_what_it_always_read() -> None:
    rows = [r for r in grid_rows() if not (
        r["n"] == 1000 and r["fraction"] == 0.20 and r["arm"] == "null")]
    assert not a14_1(rows).passed
    rows = grid_rows()
    rows[7]["top1_wealth"] = float("nan")
    assert not a14_1(rows).passed


def test_the_stored_records_are_judged_as_they_were() -> None:
    for name in ("a14_scale.json", "a14_scale_asset.json"):
        rec = json.loads((A.RESULTS / name).read_text(encoding="utf-8"))
        got = A.evaluate(copy.deepcopy(rec["runs"]), rec["rounds"],
                         rec["seeds_tested"])
        assert [c.name for c in got] == [c["name"] for c in rec["criteria"]]
        assert [bool(c.passed) for c in got] == [c["passed"] for c in rec["criteria"]]
        assert [bool(c.void) for c in got] == [c["void"] for c in rec["criteria"]]
        for c, s in zip(got, rec["criteria"]):
            if c.name.startswith("A14-1"):
                # the sentence that was there is still there, with what the
                # flag now reads after it
                assert c.detail.startswith(s["detail"].split(" Every cell")[0])
            else:
                assert c.detail == s["detail"]


# -- the three accounts on the asset carrier ----------------------------------

def _rebuild(n: int, fraction: float, arm: str, seed: int, rounds: int, asset: bool):
    cfg = NetworkConfig(spec=A.spec_for(n, fraction, arm, seed), seed=seed,
                        rounds=rounds)
    model = carrier_model(cfg, asset=asset)
    return model, model.run()


def _three(v, n: int) -> dict:
    return {"top1_wealth": A.r(A.top_share(v, max(1, n // 100))),
            "top01_wealth": A.r(A.top_share(v, max(1, n // 1000))),
            "gini": A.r(gini(v))}


def test_a_plain_run_is_the_row_it_always_was() -> None:
    row = A.one(200, 0.10, "fixed", 0, 30, asset=False)
    assert set(row) == OLD_KEYS
    model, h = _rebuild(200, 0.10, "fixed", 0, 30, asset=False)
    assert {k: row[k] for k in ("top1_wealth", "top01_wealth", "gini")} == \
        _three(h.holdings[-1], 200)
    # nothing happens after the recorded row on this carrier
    assert np.array_equal(model.holdings, h.holdings[-1])


def test_an_asset_run_keeps_its_claim_reading_and_gains_the_other_two() -> None:
    row = A.one(200, 0.10, "fixed", 0, 30, asset=True)
    assert set(row) == OLD_KEYS | {"accounts"}
    model, h = _rebuild(200, 0.10, "fixed", 0, 30, asset=True)
    recorded = h.holdings[-1]
    # the fields that were there read what they read before: claims_recorded
    assert {k: row[k] for k in ("top1_wealth", "top01_wealth", "gini")} == \
        _three(recorded, 200)
    acc = row["accounts"]
    assert acc["claims_settled"] == _three(model.holdings, 200)
    worth = model.holdings + model.units @ model.price
    assert acc["net_worth"] == _three(worth, 200)
    # and on this run the three are three different numbers
    assert len({row["top1_wealth"], acc["claims_settled"]["top1_wealth"],
                acc["net_worth"]["top1_wealth"]}) == 3
    assert acc["last_round_cash_moved"] is True
    assert acc["last_round_largest_change"] == A.r(
        float(np.max(np.abs(model.holdings - recorded))))
    assert acc["units_close_settled"] == int(round(float(model.units.sum())))
    assert acc["marked_units_close_settled"] == A.r(
        float((model.units @ model.price).sum()))
    assert acc["claims_close_settled"] == A.r(float(model.holdings.sum()))
    assert acc["supply_by_tier_initial"] == [60, 30, 10]
    assert acc["price_initial"] == [0.5, 1.0, 2.0]
    assert acc["asset_layer_inert"] is False


def test_the_null_arm_holds_one_unit_a_node_at_200_and_nothing_at_1000() -> None:
    small = A.one(200, 0.10, "null", 0, 12, asset=True)["accounts"]
    assert small["claims_per_node_initial"] == 0.5
    assert small["lowest_stretch_gate_initial"] == 0.166667
    assert small["units_initial"] == 90
    assert small["units_initial_by_tier"] == [60, 30, 0]
    assert small["owners_initial"] == 90
    assert small["max_units_one_node_initial"] == 1
    assert small["asset_layer_inert"] is False

    with_layer = A.one(1000, 0.10, "null", 0, 12, asset=True)
    without = A.one(1000, 0.10, "null", 0, 12, asset=False)
    big = with_layer["accounts"]
    # 0.1 a node is under the lowest gate, so the allocation hands out nothing
    assert big["claims_per_node_initial"] == 0.1 < big["lowest_stretch_gate_initial"]
    assert big["units_initial"] == 0 and big["units_close_settled"] == 0
    assert big["units_initial_by_tier"] == [0, 0, 0]
    assert big["asset_layer_inert"] is True
    assert big["last_round_cash_moved"] is False
    # and the run is the plain run, field for field
    assert {k: with_layer[k] for k in OLD_KEYS} == without
    three = {k: with_layer[k] for k in ("top1_wealth", "top01_wealth", "gini")}
    assert big["net_worth"] == three and big["claims_settled"] == three


def test_the_printed_block_reads_each_account_from_its_own_numbers() -> None:
    rows = grid_rows(asset=True)
    block = A.asset_account_readings(rows)
    assert set(block) == set(A.ACCOUNTS) | {
        "null_arm_units", "last_round_settlement", "net_worth_against_claims",
        "held_share_of_net_worth"}

    claims = block["claims_recorded"]["direction_by_fraction"]["0.1"]["top1_wealth"]
    worth = block["net_worth"]["direction_by_fraction"]["0.1"]["top1_wealth"]
    # claims: up with degrees fixed, down with density held
    assert claims["fixed"]["change"] == 0.06 and claims["scaled"]["change"] == -0.06
    assert claims["reversed"] is True
    assert claims["fixed"]["seeds_rising"] == 5 and claims["scaled"]["seeds_rising"] == 0
    # net worth: down on both
    assert worth["fixed"]["change"] == -0.12 and worth["scaled"]["change"] == -0.12
    assert worth["reversed"] is False
    assert worth["fixed"]["seeds_rising"] == 0 and worth["fixed"]["seeds"] == 5
    # inside the asset block every account carries the two shared readings
    assert set(block["claims_recorded"]["direction_by_fraction"]["0.1"]) == \
        set(A.SHARE_KEYS)
    # settled claims are their own column, 0.002 above the recorded ones
    assert block["claims_settled"]["construction_cell_top1"] == round(
        block["claims_recorded"]["construction_cell_top1"] + 0.002, 6)
    assert block["net_worth"]["construction_cell_top1"] == 0.602
    lo, hi, width = block["net_worth"]["non_null_top1_span"]
    assert (lo, hi, width) == (0.482, 0.602, 0.12)
    assert block["net_worth"]["null_gini_by_size"] == {
        "200": 0.4, "500": 0.4, "1000": 0.007}
    assert block["net_worth"]["null_gini_lowest_run_by_size"] == {
        "200": 0.4, "500": 0.4, "1000": 0.007}
    # the lowest run is read over every null run at that size, every core share
    low = copy.deepcopy(rows)
    for r in low:
        if (r["n"], r["fraction"], r["arm"], r["seed"]) == (500, 0.05, "null", 2):
            r["accounts"]["net_worth"]["gini"] = 0.3
    again = A.asset_account_readings(low)["net_worth"]
    assert again["null_gini_lowest_run_by_size"]["500"] == 0.3
    assert again["null_gini_by_size"]["500"] == 0.4

    nulls = block["null_arm_units"]
    assert nulls["200"]["units_initial"] == [90] and nulls["1000"]["units_initial"] == [0]
    assert nulls["200"]["runs"] == 15
    assert nulls["200"]["max_units_one_node_initial"] == [1]
    assert nulls["200"]["max_units_one_node_close_settled"] == [20, 24]
    assert nulls["1000"]["runs_asset_layer_inert"] == 15
    assert nulls["500"]["runs_asset_layer_inert"] == 0
    assert nulls["1000"]["claims_per_node_initial"] == [0.1]
    assert nulls["1000"]["supply_by_tier_initial"] == [(60, 30, 10)]

    s = block["last_round_settlement"]
    assert s == {"runs": 135, "runs_cash_moved": 120,
                 "largest_single_node_change": 3.5}


def test_net_worth_is_set_against_claims_cell_by_cell_and_run_by_run() -> None:
    rows = grid_rows(asset=True)
    block = A.asset_account_readings(rows)
    top = block["net_worth_against_claims"]["claims_recorded"]["top1_wealth"]
    # synthetic: net worth 0.60 - 2 slope against claims 0.30 +/- slope, so
    # it is above everywhere except where the claims rise to 0.36 and net
    # worth falls to 0.48, which is still above; then one cell is turned
    assert top == {"cells_net_worth_above": 18, "cells": 18,
                   "runs_net_worth_above": 90, "runs": 90}
    for r in rows:
        if (r["n"], r["fraction"], r["arm"]) == (1000, 0.10, "fixed"):
            r["accounts"]["net_worth"]["top1_wealth"] = 0.2
    block = A.asset_account_readings(rows)
    top = block["net_worth_against_claims"]["claims_recorded"]["top1_wealth"]
    assert top["cells_net_worth_above"] == 17 and top["runs_net_worth_above"] == 85
    # against settled claims it is read on the settled column, not the recorded
    settled = block["net_worth_against_claims"]["claims_settled"]["gini"]
    assert settled["cells_net_worth_above"] == 0      # 0.4 against 0.5
    recorded = block["net_worth_against_claims"]["claims_recorded"]["gini"]
    assert recorded["cells_net_worth_above"] == 0     # 0.4 against about 0.95
    # the null arm is not in it
    assert settled["cells"] == 18 and settled["runs"] == 90
    # a cell whose net worth sits between the two claim columns is above the
    # recorded one and not above the settled one
    rows = grid_rows(asset=True)
    for r in rows:
        if (r["n"], r["fraction"], r["arm"]) == (1000, 0.10, "fixed"):
            r["accounts"]["net_worth"]["top1_wealth"] = round(r["top1_wealth"] + 0.001, 6)
    against = A.asset_account_readings(rows)["net_worth_against_claims"]
    assert against["claims_recorded"]["top1_wealth"]["cells_net_worth_above"] == 18
    assert against["claims_settled"]["top1_wealth"]["cells_net_worth_above"] == 17
    assert against["claims_settled"]["top1_wealth"]["runs_net_worth_above"] == 85


def test_the_held_share_reads_marked_units_against_net_worth() -> None:
    block = A.asset_account_readings(grid_rows(asset=True))
    s = block["held_share_of_net_worth"]
    assert s["stratified_runs"] == 90
    assert (s["lowest"], s["highest"]) == (0.5, 0.8)
    assert s["median_by_size"] == {"200": 0.8, "500": 0.666667, "1000": 0.5}


def test_the_direction_reading_covers_every_core_share() -> None:
    rows = grid_rows(asset=True)
    for row in rows:
        row.pop("accounts")          # a plain grid carries none
    d = A.direction_by_fraction(rows)
    assert list(d) == ["0.05", "0.1", "0.2"]
    for f in d:
        # all six of A14-3's quantities, on claims_recorded
        assert list(d[f]) == list(A.HEADLINE)
        top = d[f]["top1_wealth"]
        assert top["fixed"]["path"] == [0.302, 0.332, 0.362]
        assert top["scaled"]["path"] == [0.302, 0.272, 0.242]
        assert top["reversed"] is True
        assert (top["fixed"]["seeds_rising"], top["scaled"]["seeds_rising"]) == (5, 0)
        # every pair across the two sizes, not only matching seed numbers
        assert (top["fixed"]["pairs_rising"], top["fixed"]["pairs"]) == (25, 25)
        assert top["scaled"]["pairs_rising"] == 0
        # the synthetic Gini rises with n on both arms
        assert d[f]["gini"]["reversed"] is False
        assert d[f]["gini"]["fixed"]["seeds_rising"] == 5
    # at the outer shares the scaled arm is its own rows, not the fixed arm's
    assert d["0.05"]["gini"]["scaled"]["path"] != d["0.05"]["gini"]["fixed"]["path"]
    assert d["0.1"]["gini"]["scaled"]["path"][0] == d["0.1"]["gini"]["fixed"]["path"][0]
    # the pair count does not lean on seed numbers matching: give the largest
    # size the smallest size's five values, seed for seed; no seed rises, and
    # ten of the twenty-five pairs do
    for r in rows:
        if r["arm"] == "fixed" and r["n"] == 1000 and r["fraction"] == 0.05:
            r["top1_wealth"] = round(0.30 + r["seed"] * 1e-3, 6)
    t = A.direction_by_fraction(rows)["0.05"]["top1_wealth"]["fixed"]
    assert t["seeds_rising"] == 0 and t["pairs_rising"] == 10


def test_a14_3_and_the_direction_reading_name_the_same_six_quantities() -> None:
    detail = A.evaluate(grid_rows(), 300, 5)[2].detail
    named = [part.split(":")[0] for part in detail.split(". Read:")[0].split("; ")]
    assert tuple(named) == A.HEADLINE


# -- the control with the asset layer held per node ---------------------------

def test_the_per_node_asset_is_the_registered_layer_at_200_nodes() -> None:
    assert A.per_node_asset(200).units_for(200) == AssetSpec().units_for(200)
    assert A.per_node_asset(200).initial_price == AssetSpec().initial_price
    assert A.per_node_asset(1000).units_for(1000) == (300, 150, 50)
    assert A.per_node_asset(500).initial_price == (0.2, 0.4, 0.8)


def test_the_per_node_control_is_the_asset_grid_at_200_nodes() -> None:
    for arm in ("fixed", "null"):
        grid = A.one(200, 0.10, arm, 1, 12, asset=True)
        control = A.one(200, 0.10, arm, 1, 12, per_node=True)
        assert control == grid


def test_the_per_node_control_holds_units_at_1000_nodes() -> None:
    acc = A.one(1000, 0.10, "null", 0, 3, per_node=True)["accounts"]
    assert acc["supply_by_tier_initial"] == [300, 150, 50]
    assert acc["price_initial"] == [0.1, 0.2, 0.4]
    assert acc["lowest_stretch_gate_initial"] == 0.033333
    assert acc["claims_per_node_initial"] == 0.1
    assert acc["units_initial"] == 450 and acc["max_units_one_node_initial"] == 1
    assert acc["asset_layer_inert"] is False


def test_the_control_block_reads_its_own_rows() -> None:
    grid = grid_rows(asset=True)
    control = copy.deepcopy(grid)
    for r in control:
        if r["n"] != 200:
            r["accounts"]["net_worth"]["top1_wealth"] += 0.1
    block = A.per_node_control(control, grid)
    assert block["rows_at_construction_n_equal_to_the_asset_grid"] == [45, 45]
    assert block["runs"] is control
    assert block["readings"]["net_worth"]["non_null_top1_span"] == [0.582, 0.642, 0.06]
    assert A.asset_account_readings(grid)["net_worth"]["non_null_top1_span"] == \
        [0.482, 0.602, 0.12]
    # one control row at 200 nodes that is not the grid's is counted
    control[3] = copy.deepcopy(control[3])
    control[3]["accounts"]["units_initial"] += 1
    block = A.per_node_control(control, grid)
    assert block["rows_at_construction_n_equal_to_the_asset_grid"] == [44, 45]


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok   ", name)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print("FAIL ", name, "::", type(exc).__name__, str(exc)[:200])
    raise SystemExit(1 if failed else 0)
