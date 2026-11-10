"""Stage A2d: which account a terminal share is read on.

The stage reads the last row of a run's history. That row is written inside the
round, before ``_post_round``. On the plain network the hook does nothing and
the row is the state the run ends in. With A3's asset layer on the carrier the
hook collects rent, services debt, settles resales and reprices, so the row is
one asset step short of the end state, and claims are no longer the whole of
what a node holds.

What these tests hold in place:

* the six registered fields stay on the last history row, on both carriers, and
  reproduce the records on disk;
* the two further accounts an asset carrier has are the model's own end state
  and its own net worth, not a second copy of the recorded row;
* a reading that splits in sign across seeds is counted as split, gets a name
  of its own, and is not reported as the small number its mean happens to be;
* every number the twenty-seed issuance arm prints is recomputed here from the
  arm's own cells, by a second route;
* the twenty-seed issuance arm begins with the runs the grid made.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a2d_terminal_selector as a2d  # noqa: E402

from monetary_topology.asset import carrier_model  # noqa: E402
from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402

RESULTS = ROOT / "results"

#: Long enough for the asset layer to have traded and repriced.
SHORT = 40
#: The registered length, used only where a record on disk is reproduced.
REGISTERED = 300
#: Every recomputed number is compared at the record's own rounding.
TOL = 1e-6
ACCOUNTS = ["claims_recorded", "claims_settled", "net_worth"]
RULES = ("endogenous", "fixed", "none")


def run(rule="fixed", target="top_node", seed=0, rounds=SHORT, asset=False):
    cfg = NetworkConfig(
        spec=NetworkSpec(seed=seed),
        seed=seed,
        rounds=rounds,
        spend=a2d.spend_from_retention(0.50, 0.0625),
        authority=MonetaryAuthority(rule=rule),
        injection_target=target,
    )
    model = carrier_model(cfg, asset=asset)
    return model, model.run()


# -- the accounts ----------------------------------------------------------


def test_plain_carrier_has_one_account_and_its_last_row_is_the_end_state() -> None:
    model, h = run(asset=False)
    by_account = a2d.closes(model, h)
    assert list(by_account) == ["claims_recorded"]
    assert np.array_equal(by_account["claims_recorded"], model.holdings)


def test_asset_carrier_has_three_accounts_and_its_last_row_is_not_the_end_state() -> None:
    model, h = run(asset=True)
    by_account = a2d.closes(model, h)
    assert list(by_account) == ACCOUNTS
    recorded, settled, net_worth = by_account.values()
    # The settled account is the state the run ends in, and the recorded row is not.
    assert np.array_equal(settled, model.holdings)
    assert not np.array_equal(recorded, settled)
    # The asset step moves claims between nodes and creates none.
    assert abs(float(recorded.sum()) - float(settled.sum())) < 1e-8
    # Net worth is settled claims plus held units at the closing price.
    assert np.array_equal(net_worth, settled + model.units @ model.price)
    assert float(net_worth.sum()) > float(settled.sum())


def test_the_registered_fields_stay_on_the_recorded_row() -> None:
    for asset in (False, True):
        row = a2d.one(0.50, 0.0625, "fixed", "top_node", 0, SHORT, asset=asset)
        assert row["top1_wealth"] == row["_accounts"]["claims_recorded"]["top1"]
        assert row["top10_wealth"] == row["_accounts"]["claims_recorded"]["top10"]
        assert row["gini"] == row["_accounts"]["claims_recorded"]["gini"]
        assert row["claims_close"] == row["_accounts"]["claims_recorded"]["total"]
        assert row["_recorded_row_is_end_state"] is (not asset)
    # On the asset carrier the three accounts are three readings.
    assert row["_accounts"]["net_worth"]["top1"] != row["top1_wealth"]
    assert row["_accounts"]["net_worth"]["total"] > row["claims_close"]


def test_a_row_carries_the_six_fields_the_accounts_and_nothing_underscored() -> None:
    row = a2d.mean_over_seeds(
        2, ret_l1=0.50, ret_l2=0.0625, rule="fixed", target="uniform", rounds=SHORT, asset=True
    )
    assert set(row) == set(a2d.LEGACY) | {"accounts", "recorded_row_is_end_state_runs"}
    assert list(row["accounts"]) == ACCOUNTS
    assert row["recorded_row_is_end_state_runs"] == [0, 2]
    # Per-seed values are in seed order, which is what lets two cells be paired.
    for seed in (0, 1):
        single = a2d.one(0.50, 0.0625, "fixed", "uniform", seed, SHORT, asset=True)
        for name, block in row["accounts"].items():
            assert block["top1_per_seed"][seed] == single["_accounts"][name]["top1"]


@pytest.mark.parametrize(
    "asset, record", [(False, "a2d_terminal_selector.json"), (True, "a2d_terminal_selector_asset.json")]
)
def test_the_registered_fields_reproduce_the_record_on_disk(asset: bool, record: str) -> None:
    stored = json.loads((RESULTS / record).read_text(encoding="utf-8"))
    want = next(
        row for row in stored["issuance_grid"] if (row["rule"], row["target"]) == ("fixed", "uniform")
    )
    got = a2d.mean_over_seeds(
        stored["seeds_tested"], ret_l1=0.50, ret_l2=0.0625, rule="fixed", target="uniform",
        rounds=REGISTERED, asset=asset,
    )
    assert stored["rounds"] == REGISTERED
    for key in a2d.LEGACY:
        assert got[key] == want[key], key


def test_no_issuance_leaves_the_entry_point_nothing_to_place_on_any_account() -> None:
    for asset in (False, True):
        m1, h1 = run(rule="none", target="top_node", asset=asset)
        m2, h2 = run(rule="none", target="uniform", asset=asset)
        assert np.array_equal(h1.holdings, h2.holdings)
        for a, b in zip(a2d.closes(m1, h1).values(), a2d.closes(m2, h2).values()):
            assert np.array_equal(a, b)


# -- the readings, on rows built by hand ------------------------------------


def _row(per_seed, **labels):
    per_seed = [float(x) for x in per_seed]
    top1 = a2d.r(float(np.mean(per_seed)))
    return {
        "top1_wealth": top1,
        "issued": 0.0 if labels.get("rule") == "none" else 2990.0,
        "accounts": {"claims_recorded": {"top1": top1, "top1_per_seed": per_seed}},
        **labels,
    }


def _grids(issuing, off=(0.20, 0.20, 0.20, 0.20, 0.20), sigma_width=0.01):
    """Rows shaped like the three grids. ``issuing`` maps the four issuing
    cells to five per-seed values each."""
    sigma = [
        _row([0.22 + sigma_width * i / (len(a2d.RET_L1) - 1)] * 5, ret_l1=r1, ret_l2=r2)
        for i, r1 in enumerate(a2d.RET_L1)
        for r2 in a2d.RET_L2
    ]
    n_struct = sum(len(values) for _, values in a2d.STRUCTURE)
    structure = [
        _row([0.15 + 0.15 * i / (n_struct - 1)] * 5, knob=knob, value=v)
        for i, (knob, v) in enumerate((k, v) for k, values in a2d.STRUCTURE for v in values)
    ]
    issuance = [_row(issuing[(rule, target)], rule=rule, target=target)
                for rule, target in a2d.ISSUANCE if rule != "none"]
    issuance += [_row(off, rule="none", target=t) for t in ("top_node", "uniform")]
    return sigma, structure, issuance


def _flat(value):
    return {(rule, target): [value] * 5 for rule, target in a2d.ISSUANCE if rule != "none"}


def test_the_recorded_row_reading_is_the_one_the_criteria_print() -> None:
    sigma, structure, issuance = _grids(_flat(0.25))
    reading = a2d.account_reading(sigma, structure, issuance, "claims_recorded")
    criteria = a2d.evaluate(sigma, structure, issuance)
    assert f"width {reading['sigma']['width']}." in criteria[1].detail
    assert f"width {reading['structure']['width']}." in criteria[1].detail
    assert f"is {reading['structural_over_sigma_width']}x" in criteria[1].detail
    assert f"gap {reading['on_off_gap']} against" in criteria[2].detail
    assert f"State: {reading['state_on_the_mean']}." in criteria[2].detail
    assert reading["seeds_with_structural_span_larger"] == 5
    assert reading["top1_by_financial_retention"][str(max(a2d.RET_L1))] == 0.23
    assert reading["seeds_with_retention_lifting_top1"] == 5


def test_each_state_of_the_on_off_gap_has_its_own_name() -> None:
    """Three states on the mean, three seed by seed, each mapped to one wording
    and none to another's. A gap that splits across seeds is not placed."""
    states = {}
    for label, on_value in (("overlap", 0.19), ("inside", 0.205), ("beyond", 0.25)):
        sigma, structure, issuance = _grids(_flat(on_value))
        states[label] = a2d.account_reading(sigma, structure, issuance, "claims_recorded")
    split = _flat(0.25)
    split[("fixed", "uniform")] = [0.25, 0.19, 0.25, 0.19, 0.25]
    states["split"] = a2d.account_reading(*_grids(split), "claims_recorded")

    assert states["overlap"]["state_on_the_mean"] == "overlap: issuance does not separate"
    assert states["overlap"]["state_seed_by_seed"] == "no seed separated"
    assert states["overlap"]["on_off_gap"] == -0.01
    assert states["overlap"]["seeds_with_gap_positive"] == 0
    assert states["inside"]["state_on_the_mean"] == "separated, but by less than sigma's span"
    assert states["inside"]["state_seed_by_seed"] == "every seed separated"
    assert states["inside"]["seeds_with_gap_above_sigma_width"] == 0
    assert states["beyond"]["state_on_the_mean"] == "separated by more than sigma's whole span"
    assert states["beyond"]["state_seed_by_seed"] == "every seed separated"
    assert states["beyond"]["seeds_with_gap_positive"] == 5
    assert states["beyond"]["seeds_with_gap_above_sigma_width"] == 5
    # The split gap: positive on the mean, and positive in three seeds of five.
    assert states["split"]["on_off_gap"] > 0
    assert states["split"]["state_seed_by_seed"] == "not placed at 5 seeds: positive in 3"
    on_the_mean = {s["state_on_the_mean"] for s in states.values()}
    seed_by_seed = {s["state_seed_by_seed"] for s in states.values()}
    assert len({s["state_on_the_mean"] for k, s in states.items() if k != "split"}) == 3
    assert len(seed_by_seed) == 3
    assert not on_the_mean & seed_by_seed
    # A seed whose gap is exactly zero is not separated, on the mean and seed by
    # seed alike, which is how the third criterion reads a gap of zero.
    tie = a2d.account_reading(*_grids(_flat(0.20)), "claims_recorded")
    assert tie["on_off_gap"] == 0.0
    assert tie["state_on_the_mean"] == "overlap: issuance does not separate"
    assert tie["state_seed_by_seed"] == "no seed separated"
    one_tie = _flat(0.25)
    one_tie[("fixed", "uniform")] = [0.25, 0.20, 0.25, 0.25, 0.25]
    one_tie = a2d.account_reading(*_grids(one_tie), "claims_recorded")
    assert one_tie["on_off_gap_per_seed"][1] == 0.0
    assert one_tie["state_seed_by_seed"] == "not placed at 5 seeds: positive in 4"


def test_the_gap_is_set_by_the_lowest_issuing_cell_seed_by_seed() -> None:
    issuing = _flat(0.25)
    # One issuing cell dips under the non-issuing one in two seeds.
    issuing[("fixed", "uniform")] = [0.25, 0.19, 0.25, 0.19, 0.25]
    reading = a2d.account_reading(*_grids(issuing), "claims_recorded")
    assert reading["on_off_gap_per_seed"] == [0.05, -0.01, 0.05, -0.01, 0.05]
    assert reading["seeds_with_gap_positive"] == 3
    # The mean of that cell is 0.226, still above 0.20: the mean does not show it.
    assert reading["on_off_gap"] == 0.026
    assert reading["state_seed_by_seed"] == "not placed at 5 seeds: positive in 3"


def test_the_gap_is_taken_against_the_higher_non_issuing_cell() -> None:
    """The on-off gap is the lowest issuing cell minus the highest non-issuing
    one, on the mean and in every seed. On real runs the two non-issuing cells
    agree bit for bit, so only rows built by hand can tell max from min here."""
    sigma, structure, issuance = _grids(_flat(0.25))
    for i, row in enumerate(issuance):
        if (row["rule"], row["target"]) == ("none", "uniform"):
            issuance[i] = _row([0.22] * 5, rule="none", target="uniform")
    reading = a2d.account_reading(sigma, structure, issuance, "claims_recorded")
    assert reading["on_off_gap"] == 0.03
    assert reading["on_off_gap_per_seed"] == [0.03] * 5


def test_a_pair_that_splits_across_seeds_is_counted_and_not_averaged_away() -> None:
    issuing = _flat(0.25)
    issuing[("fixed", "top_node")] = [0.30, 0.20, 0.30, 0.20, 0.25]
    issuing[("fixed", "uniform")] = [0.25, 0.25, 0.25, 0.25, 0.25]
    reading = a2d.account_reading(*_grids(issuing), "claims_recorded")
    pair = reading["entry_pairs"]["fixed"]
    assert pair["abs_diff_of_means"] == 0.0
    assert pair["top_node_minus_uniform_per_seed"] == [0.05, -0.05, 0.05, -0.05, 0.0]
    assert (pair["seeds_positive"], pair["seeds_negative"]) == (2, 2)
    assert pair["se_across_seeds"] > 0.02
    # With nothing issued the two entry points agree in every seed: no sign at all.
    none = reading["entry_pairs"]["none"]
    assert (none["seeds_positive"], none["seeds_negative"]) == (0, 0)


def test_the_pair_is_held_against_its_own_seeds_gap_by_size() -> None:
    """The fourth criterion's reading, seed by seed: the pair's size, not its
    sign, against the on-off gap of the same seed."""
    issuing = _flat(0.30)
    issuing[("fixed", "top_node")] = [0.30, 0.31, 0.29, 0.30, 0.45]
    issuing[("fixed", "uniform")] = [0.30, 0.30, 0.45, 0.30, 0.30]
    reading = a2d.account_reading(*_grids(issuing), "claims_recorded")
    pair = reading["entry_pairs"]["fixed"]
    gap = reading["on_off_gap_per_seed"]
    # Pair 0, +0.01, -0.16, 0, +0.15 against gaps 0.10, 0.10, 0.09, 0.10, 0.10.
    want = sum(abs(d) < g for d, g in zip(pair["top_node_minus_uniform_per_seed"], gap))
    assert want == 3
    assert pair["seeds_below_the_on_off_gap"] == 3
    # The pair with nothing issued is zero, so it is below a positive gap everywhere.
    assert reading["entry_pairs"]["none"]["seeds_below_the_on_off_gap"] == 5


def _account_block(top1_per_seed, total):
    return {"top1": a2d.r(float(np.mean(top1_per_seed))), "top1_per_seed": list(top1_per_seed),
            "total": total}


def test_net_worth_against_claims_is_read_off_the_rows() -> None:
    rows = [
        # Above in every run.
        {"accounts": {"net_worth": _account_block([0.40, 0.50], 400.0),
                      "claims_settled": _account_block([0.20, 0.20], 100.0)}},
        # Above on the mean and below in one run.
        {"accounts": {"net_worth": _account_block([0.60, 0.10], 1000.0),
                      "claims_settled": _account_block([0.20, 0.20], 100.0)}},
        # Below on the mean.
        {"accounts": {"net_worth": _account_block([0.18, 0.20], 200.0),
                      "claims_settled": _account_block([0.20, 0.20], 100.0)}},
    ]
    got = a2d.net_worth_against_claims(rows)
    assert (got["cells"], got["cells_with_net_worth_top1_above"]) == (3, 2)
    assert (got["runs"], got["runs_with_net_worth_top1_above"]) == (6, 3)
    ratios = sorted(row["accounts"]["net_worth"]["top1"] / row["accounts"]["claims_settled"]["top1"]
                    for row in rows)
    q = got["top1_ratio_net_worth_over_claims_settled"]
    assert q["min"] == pytest.approx(ratios[0], abs=TOL)
    assert q["median"] == pytest.approx(ratios[1], abs=TOL)
    assert q["max"] == pytest.approx(ratios[2], abs=TOL)
    # Held units are what net worth has beyond settled claims: 0.75, 0.9, 0.5.
    assert got["held_units_share"] == {"min": 0.5, "max": 0.9}


# -- the twenty-seed arm ----------------------------------------------------


def _recompute_arm(arm) -> int:
    """Every reading of the arm, from its cells, by a second route: the
    standard library on plain lists instead of the script's numpy arrays.
    Returns how many numbers it compared."""
    cells = {(c["rule"], c["target"]): c for c in arm["cells"]}
    names = list(next(iter(cells.values()))["top1_per_seed"])
    issuing = [k for k in cells if k[0] != "none"]
    checked = 0

    def col(a, k):
        return [float(x) for x in cells[k]["top1_per_seed"][a]]

    def same_numbers(want, d):
        assert want["mean"] == pytest.approx(statistics.fmean(d), abs=TOL)
        assert want["se_across_seeds"] == pytest.approx(
            statistics.stdev(d) / math.sqrt(len(d)), abs=TOL)
        assert want["seeds_positive"] == sum(x > 0 for x in d)
        assert want["seeds_negative"] == sum(x < 0 for x in d)
        return 4

    for a in names:
        got = arm["readings"][a]
        off = col(a, ("none", "top_node"))
        n = len(off)
        assert got["none"] == pytest.approx(statistics.fmean(off), abs=TOL)
        for k in issuing:
            d = [x - y for x, y in zip(col(a, k), off)]
            want = got["minus_none"][f"{k[0]}/{k[1]}"]
            checked += same_numbers(want, d)
            assert want["median"] == pytest.approx(statistics.median(d), abs=TOL)
        gap = [min(col(a, k)[i] for k in issuing)
               - max(col(a, ("none", "top_node"))[i], col(a, ("none", "uniform"))[i])
               for i in range(n)]
        assert got["seeds_with_gap_positive"] == sum(g > 0 for g in gap)
        assert got["on_off_gap_of_means"] == pytest.approx(
            min(statistics.fmean(col(a, k)) for k in issuing) - statistics.fmean(off), abs=TOL)
        for rule in RULES:
            d = [x - y for x, y in zip(col(a, (rule, "top_node")), col(a, (rule, "uniform")))]
            want = got["top_node_minus_uniform"][rule]
            checked += same_numbers(want, d)
            assert want["median"] == pytest.approx(statistics.median(d), abs=TOL)
            assert want["per_seed"] == pytest.approx(d, abs=TOL)
            assert want["seeds_below_the_on_off_gap"] == sum(abs(x) < g for x, g in zip(d, gap))
        checked += 3
    if "claims_settled" in names:
        for k in issuing:
            d = [(s - sn) - (rr - rn) for s, sn, rr, rn in zip(
                col("claims_settled", k), col("claims_settled", ("none", "top_node")),
                col("claims_recorded", k), col("claims_recorded", ("none", "top_node")))]
            checked += same_numbers(arm["last_asset_step"][f"{k[0]}/{k[1]}"], d)
    else:
        assert "last_asset_step" not in arm
    return checked


def _cells(values):
    """Six issuance cells; ``values`` maps (rule, target) to per-seed lists,
    one list per account."""
    return [{"rule": rule, "target": target, "issued": 0.0 if rule == "none" else 2990.0,
             "top1_per_seed": dict(zip(ACCOUNTS, values[(rule, target)]))}
            for rule, target in a2d.ISSUANCE]


def test_the_arm_reads_its_cells_and_a_second_route_agrees() -> None:
    """Ties included on purpose: a seed where an issuing cell equals no issuance,
    and the no-issuance pair, which is zero in every seed."""
    none = [[0.20, 0.20, 0.20, 0.20]] * 3
    values = {
        ("endogenous", "top_node"): [[0.25, 0.20, 0.26, 0.24], [0.24, 0.21, 0.25, 0.22], [0.50, 0.40, 0.45, 0.47]],
        ("endogenous", "uniform"): [[0.24, 0.22, 0.27, 0.23], [0.22, 0.22, 0.24, 0.23], [0.44, 0.46, 0.43, 0.44]],
        ("fixed", "top_node"): [[0.23, 0.24, 0.21, 0.25], [0.22, 0.25, 0.20, 0.24], [0.48, 0.43, 0.49, 0.41]],
        ("fixed", "uniform"): [[0.22, 0.24, 0.19, 0.25], [0.21, 0.21, 0.21, 0.19], [0.42, 0.45, 0.40, 0.44]],
        ("none", "top_node"): none,
        ("none", "uniform"): none,
    }
    cells = _cells(values)
    arm = a2d.read_issuance_arm(cells)
    assert _recompute_arm({"cells": cells, **arm}) > 100
    fixed = arm["readings"]["claims_recorded"]["top_node_minus_uniform"]["fixed"]
    assert fixed["per_seed"] == pytest.approx([0.01, 0.0, 0.02, 0.0], abs=TOL)
    assert (fixed["seeds_positive"], fixed["seeds_negative"]) == (2, 0)
    # The settled account sits closer to no issuance than the recorded row in
    # the fixed uniform cell in three seeds of four.
    step = arm["last_asset_step"]["fixed/uniform"]
    assert (step["seeds_positive"], step["seeds_negative"]) == (1, 3)
    # Without a grid to compare against, the arm does not say it equals one.
    assert arm["first_seeds_equal_the_grid"] is None


def test_the_arm_says_it_equals_the_grid_only_when_every_cell_was_compared() -> None:
    values = {(rule, target): [[0.2 + 0.01 * i] * 3 for i in range(3)]
              for rule, target in a2d.ISSUANCE}
    cells = _cells(values)
    grid = [{"rule": c["rule"], "target": c["target"],
             "accounts": {a: {"top1_per_seed": list(c["top1_per_seed"][a][:2])} for a in ACCOUNTS}}
            for c in cells]
    assert a2d.read_issuance_arm(cells, grid)["first_seeds_equal_the_grid"] is True
    assert a2d.read_issuance_arm(cells, grid[:-1])["first_seeds_equal_the_grid"] is None
    assert a2d.read_issuance_arm(cells, [])["first_seeds_equal_the_grid"] is None
    grid[3]["accounts"]["net_worth"]["top1_per_seed"][1] += 0.001
    assert a2d.read_issuance_arm(cells, grid)["first_seeds_equal_the_grid"] is False


def test_the_seed_arm_begins_with_the_runs_the_grid_made() -> None:
    grid = []
    for rule, target in a2d.ISSUANCE:
        m = a2d.mean_over_seeds(
            2, ret_l1=0.50, ret_l2=0.0625, rule=rule, target=target, rounds=SHORT, asset=True
        )
        grid.append(m | {"rule": rule, "target": target})
    arm = a2d.issuance_by_seed(SHORT, 3, True, grid)
    assert arm["seeds"] == 3 and arm["scored"] is False
    assert arm["first_seeds_equal_the_grid"] is True
    assert list(arm["readings"]) == ACCOUNTS
    for reading in arm["readings"].values():
        none_pair = reading["top_node_minus_uniform"]["none"]
        assert (none_pair["mean"], none_pair["seeds_positive"], none_pair["seeds_negative"]) == (0.0, 0, 0)
        assert set(reading["minus_none"]) == {
            "endogenous/top_node", "endogenous/uniform", "fixed/top_node", "fixed/uniform"
        }
        for cell in reading["minus_none"].values():
            assert cell["seeds_positive"] + cell["seeds_negative"] <= 3
    assert _recompute_arm(arm) > 100
    # A grid that disagrees with the arm in one seed of one cell is noticed.
    grid[2]["accounts"]["net_worth"]["top1_per_seed"][1] += 0.001
    assert a2d.issuance_by_seed(SHORT, 3, True, grid)["first_seeds_equal_the_grid"] is False


# -- the records on disk ------------------------------------------------------


def _width(rows):
    values = [row["top1_wealth"] for row in rows]
    return a2d.r(max(values) - min(values))


def test_the_registered_record_names_its_one_account() -> None:
    record = json.loads((RESULTS / "a2d_terminal_selector.json").read_text(encoding="utf-8"))
    block = record["accounts"]
    assert list(block["definitions"]) == ["claims_recorded"]
    assert block["registered_fields_read"] == "claims_recorded"
    runs = record["seeds_tested"] * (
        len(record["sigma_grid"]) + len(record["structure_grid"]) + len(record["issuance_grid"])
    )
    assert block["recorded_row_is_end_state_runs"] == [runs, runs]
    reading = block["readings"]["claims_recorded"]
    assert reading["sigma"]["width"] == _width(record["sigma_grid"])
    assert reading["structure"]["width"] == _width(record["structure_grid"])
    assert reading["state_seed_by_seed"] == "every seed separated"
    assert "issuance_by_seed" not in record
    assert "net_worth_against_claims" not in block
    assert [c["passed"] for c in record["criteria"]] == [True, True, True, True]


def test_the_asset_record_carries_three_accounts_and_the_seed_arm() -> None:
    record = json.loads((RESULTS / "a2d_terminal_selector_asset.json").read_text(encoding="utf-8"))
    assert record["diagnostic_only"] is True
    block = record["accounts"]
    # The record is written with sorted keys, so the order here is alphabetical.
    assert set(block["definitions"]) == set(ACCOUNTS)
    assert set(block["readings"]) == set(block["definitions"])
    assert block["registered_fields_read"] == "claims_recorded"
    grids = [row for g in ("sigma_grid", "structure_grid", "issuance_grid") for row in record[g]]
    assert block["recorded_row_is_end_state_runs"] == [0, record["seeds_tested"] * len(grids)]
    # The top-level fields are the recorded-row account, row for row.
    for row in grids:
        assert row["top1_wealth"] == row["accounts"]["claims_recorded"]["top1"]
    assert block["readings"]["claims_recorded"]["sigma"]["width"] == _width(record["sigma_grid"])
    # The ordering the stage reports holds on each account, in every seed.
    for reading in block["readings"].values():
        assert reading["structure"]["width"] > reading["sigma"]["width"]
        assert reading["seeds_with_structural_span_larger"] == record["seeds_tested"]
    # On the recorded row the on-off gap is placed; on net worth it is not.
    assert block["readings"]["claims_recorded"]["state_seed_by_seed"] == "every seed separated"
    nw = block["readings"]["net_worth"]
    assert nw["state_seed_by_seed"] == (
        f"not placed at {record['seeds_tested']} seeds: positive in {nw['seeds_with_gap_positive']}"
    )
    # Levels, recomputed from the rows.
    levels = block["net_worth_against_claims"]
    assert levels == a2d.net_worth_against_claims(grids)
    assert levels["cells"] == len(grids)
    assert levels["cells_with_net_worth_top1_above"] == sum(
        row["accounts"]["net_worth"]["top1"] > row["accounts"]["claims_settled"]["top1"] for row in grids)
    arm = record["issuance_by_seed"]
    assert arm["seeds"] == a2d.ISSUANCE_SEEDS and arm["scored"] is False
    assert arm["first_seeds_equal_the_grid"] is True
    assert _recompute_arm(arm) > 100
    assert [c["passed"] for c in record["criteria"]] == [True, True, True, True]

def test_the_account_note_reaches_the_three_share_criteria_and_only_on_request() -> None:
    """The note is what names the account on the asset record. Without it the
    four criteria are the registered ones, word for word; with it the three
    that read a share carry it and the structural one does not."""
    sigma, structure, issuance = _grids(_flat(0.25))
    plain = a2d.evaluate(sigma, structure, issuance)
    noted = a2d.evaluate(sigma, structure, issuance, account_note=a2d.ASSET_ACCOUNT_NOTE)
    assert [c.name for c in noted] == [c.name for c in plain]
    assert [c.passed for c in noted] == [c.passed for c in plain]
    assert noted[0].detail == plain[0].detail
    for p, n in zip(plain[1:], noted[1:]):
        assert n.detail == f"{p.detail} {a2d.ASSET_ACCOUNT_NOTE}"
    assert all("claims_recorded" not in c.detail for c in plain)


def test_each_record_names_the_account_its_criteria_read() -> None:
    """On disk: the asset record's three share criteria say they read
    ``claims_recorded``; the registered record, where claims are all a node
    holds, carries no such sentence."""
    plain = json.loads((RESULTS / "a2d_terminal_selector.json").read_text(encoding="utf-8"))
    asset = json.loads((RESULTS / "a2d_terminal_selector_asset.json").read_text(encoding="utf-8"))
    assert [a2d.ASSET_ACCOUNT_NOTE in c["detail"] for c in plain["criteria"]] == [False] * 4
    assert [a2d.ASSET_ACCOUNT_NOTE in c["detail"] for c in asset["criteria"]] == [False, True, True, True]
    assert asset["accounts"]["registered_fields_read"] == "claims_recorded"
