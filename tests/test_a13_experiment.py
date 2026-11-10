"""Stage A13: what the two guards compare, and what a row is a row of.

Three things about the instrument, none of them a reading of the economy.

**A13-1 is about a grid.** It counted arm names and checked one share, so a
grid with a seed missing passed. It now asks for every arm on every seed asked
for, with every share finite, and each test here takes one of those away.

**A13-5a says bitwise.** It compared four of a row's readings at six decimals,
so the null arm could differ from the construction in its top-decile share, in
its counts, or below the sixth decimal anywhere. It now compares every reading
in the row and one hash over the whole run. The run altered below the sixth
decimal is the test that matters: the rows agree and only the hash can tell.

**A row's shares are shares of claims in the last history row.** On the asset
carrier that row precedes the last settlement and holds no asset, so an asset
row prints the same statistics on the claims the run ends with and on net
worth, and its span is set beside A2d's record on the same carrier, account by
account. The edge counts are in every row because four arms move out-degree on
purpose and thirteen must not. ``conserve_degree`` makes every exchange exact
since 2026-10-14; the tests below pin what the rule does to the graph and that
the run refuses to write when an exchange-only arm leaks, so a change to the
rule fails here before a reading is quoted from a record that no longer
describes it.

No test here calls ``main``: it writes the record at its registered path.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a13_mobility as a13  # noqa: E402

#: The registered length. The readings pinned below are the record's.
ROUNDS = 300

#: Long enough for both directions to fire, short enough to run the whole grid.
SHORT, SEEDS = 30, 2

NULL = "demote .005 retain 1"


@pytest.fixture(scope="module")
def grid() -> tuple[dict, dict]:
    by_arm: dict = {}
    digests: dict = {}
    for tag, spec in a13.ARMS.items():
        by_arm[tag] = [a13.one(spec, seed, SHORT, False, digests.setdefault(tag, {}))
                       for seed in range(SEEDS)]
    return by_arm, digests


def crit(by_arm: dict, tag: str, **kw) -> a13.Criterion:
    return next(c for c in a13.evaluate(by_arm, **kw) if c.name.startswith(tag + " "))


def test_the_grid_as_run_passes_both_guards(grid) -> None:
    by_arm, digests = grid
    assert crit(by_arm, "A13-1", seeds=SEEDS).passed
    assert crit(by_arm, "A13-5a", seeds=SEEDS, digests=digests).passed


@pytest.mark.parametrize("arm", ["off", "both", "rank k=1 cluster 1"])
def test_a_missing_seed_fails_a13_1_and_is_named(grid, arm) -> None:
    by_arm = copy.deepcopy(grid[0])
    by_arm[arm] = by_arm[arm][:-1]
    c = crit(by_arm, "A13-1", seeds=SEEDS)
    assert not c.passed
    assert arm in c.detail


def test_a_repeated_seed_is_not_two_seeds(grid) -> None:
    by_arm = copy.deepcopy(grid[0])
    by_arm["both"][1] = dict(by_arm["both"][0])
    assert not crit(by_arm, "A13-1", seeds=SEEDS).passed


def test_a_grid_short_of_what_was_asked_for_fails(grid) -> None:
    by_arm = {arm: rows[:1] for arm, rows in copy.deepcopy(grid[0]).items()}
    assert not crit(by_arm, "A13-1", seeds=SEEDS).passed
    # Without being told, the longest arm is the grid, and one seed is a grid.
    assert crit(by_arm, "A13-1").passed


@pytest.mark.parametrize("key", a13.SHARES)
def test_every_share_has_to_be_finite(grid, key) -> None:
    by_arm = copy.deepcopy(grid[0])
    by_arm["both"][0][key] = float("nan")
    assert not crit(by_arm, "A13-1", seeds=SEEDS).passed


def test_the_null_arm_is_compared_on_every_reading_in_the_row(grid) -> None:
    by_arm, digests = grid
    keys = [k for k in by_arm["off"][0] if k != "seed"]
    assert {"top10_wealth", "promoted", "core_close", "edges_close",
            "edges_initial"} <= set(keys)
    for key in keys:
        wrong = copy.deepcopy(by_arm)
        wrong[NULL][0][key] = wrong[NULL][0][key] + 1
        assert not crit(wrong, "A13-5a", seeds=SEEDS).passed, key
        assert not crit(wrong, "A13-5a", seeds=SEEDS, digests=digests).passed, key


def test_the_null_arm_is_compared_on_the_whole_run(grid, monkeypatch) -> None:
    by_arm, digests = grid
    factory = a13.carrier_model

    def nudged(cfg, *, asset=False):
        # The null arm with a billionth of a claim moved between its two
        # richest nodes in the last round: nothing a six-decimal row can see.
        net = factory(cfg, asset=asset)
        inner = net._rewire

        def rewire(t):
            out = inner(t)
            if t == cfg.rounds - 1:
                order = np.argsort(net.holdings)
                net.holdings[order[-1]] += 1e-9
                net.holdings[order[-2]] -= 1e-9
            return out

        net._rewire = rewire
        return net

    monkeypatch.setattr(a13, "carrier_model", nudged)
    moved: dict = {}
    rows = [a13.one(a13.ARMS[NULL], seed, SHORT, False, moved) for seed in range(SEEDS)]
    monkeypatch.undo()

    planted = dict(copy.deepcopy(by_arm), **{NULL: rows})
    hashes = dict(digests, **{NULL: moved})
    # The plant is below the row's resolution, or this test tests nothing.
    assert rows == by_arm["off"]
    assert crit(planted, "A13-5a", seeds=SEEDS).passed
    assert not crit(planted, "A13-5a", seeds=SEEDS, digests=hashes).passed
    # And the hash is not a constant: two arms that differ, differ.
    assert digests["off"][0] != digests["both"][0]
    assert digests["off"][0] == digests[NULL][0]


@pytest.mark.parametrize("asset", [False, True])
def test_the_hash_covers_the_history_and_the_state_the_run_ends_in(asset) -> None:
    cfg = a13.NetworkConfig(spec=a13.NetworkSpec(seed=0), seed=0, rounds=SHORT,
                            rewire=a13.ARMS["both"])
    net = a13.carrier_model(cfg, asset=asset)
    h = net.run()
    base = a13.state_digest(net, h)
    assert a13.state_digest(net, h) == base

    arrays = {"h." + f.name: getattr(h, f.name) for f in dataclasses.fields(h)
              if isinstance(getattr(h, f.name), np.ndarray) and getattr(h, f.name).size}
    state = ("adjacency", "holdings", "_in_core") + (("units", "price") if asset else ())
    arrays.update({"net." + name: getattr(net, name) for name in state})
    assert {"h.holdings", "h.effective_support", "h.promoted", "net.holdings"} <= set(arrays)
    for name, array in arrays.items():
        flat = array.reshape(-1)
        assert np.shares_memory(flat, array), name
        keep = flat[0].copy()
        flat[0] = (not keep) if array.dtype == bool else keep + 1
        assert a13.state_digest(net, h) != base, name
        flat[0] = keep
    assert a13.state_digest(net, h) == base


def test_a_hash_missing_for_a_seed_is_not_agreement(grid) -> None:
    by_arm, digests = grid
    short = dict(digests, **{NULL: {0: digests[NULL][0]}})
    assert not crit(by_arm, "A13-5a", seeds=SEEDS, digests=short).passed


def record(name: str) -> dict:
    return json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))


def widths(name: str) -> tuple[float, float]:
    ref = record(name)
    out = []
    for g in ("sigma_grid", "structure_grid"):
        vs = [row["top1_wealth"] for row in ref[g]]
        out.append(round(max(vs) - min(vs), 6))
    return out[0], out[1]


def test_the_ruler_is_taken_on_the_carrier_the_run_was_taken_on(grid) -> None:
    by_arm = grid[0]
    plain, asset = widths(a13.A2D_RECORD), widths(a13.A2D_RECORD_ASSET)
    assert plain != asset
    on_plain = crit(by_arm, "A13-3", seeds=SEEDS).detail
    on_asset = crit(by_arm, "A13-3", seeds=SEEDS, asset=True).detail
    assert f"sigma width {plain[0]}, structure width {plain[1]}" in on_plain
    assert f"sigma width {asset[0]}, structure width {asset[1]}" in on_asset
    assert a13.A2D_RECORD_ASSET in on_asset
    assert "Ruler" not in on_plain
    assert a13.ruler_reading(True)["record"] == a13.A2D_RECORD_ASSET
    assert a13.ruler_reading(False)["record"] == a13.A2D_RECORD


@pytest.mark.parametrize("asset", [False, True])
def test_the_ruler_is_a2ds_record_account_by_account(asset) -> None:
    name = a13.A2D_RECORD_ASSET if asset else a13.A2D_RECORD
    readings = record(name)["accounts"]["readings"]
    ruler = a13.ruler_reading(asset)
    assert set(ruler["accounts"]) == set(readings)
    for account, v in readings.items():
        assert ruler["accounts"][account] == {
            "sigma_width": v["sigma"]["width"],
            "structure_width": v["structure"]["width"]}, account
    if asset:
        # Three accounts and three different pairs of widths.
        assert len({tuple(v.values()) for v in ruler["accounts"].values()}) == 3
    else:
        assert set(ruler["accounts"]) == {"claims_recorded"}


def test_the_ruler_refuses_accounts_its_rows_do_not_give(monkeypatch, tmp_path) -> None:
    ref = record(a13.A2D_RECORD_ASSET)
    ref["accounts"]["readings"]["claims_recorded"]["sigma"]["width"] += 0.001
    (tmp_path / a13.A2D_RECORD_ASSET).write_text(json.dumps(ref), encoding="utf-8")
    monkeypatch.setattr(a13, "RESULTS", tmp_path)
    with pytest.raises(ValueError, match="not that record"):
        a13.ruler_reading(True)
    # A record with no accounts block is read off its rows.
    del ref["accounts"]
    (tmp_path / a13.A2D_RECORD_ASSET).write_text(json.dumps(ref), encoding="utf-8")
    got = a13.ruler_reading(True)["accounts"]
    assert set(got) == {"claims_recorded"}
    assert (got["claims_recorded"]["sigma_width"],
            got["claims_recorded"]["structure_width"]) == widths(a13.A2D_RECORD_ASSET)


def test_the_old_fields_still_reproduce_the_record() -> None:
    old_record = record("a13_mobility.json")
    old = ("seed", "top1_wealth", "top10_wealth", "gini", "support", "mr_close",
           "promoted", "demoted", "core_close", "core_open")
    for arm in ("off", "both", "rank k=1 cluster 1"):
        row = a13.one(a13.ARMS[arm], 0, ROUNDS)
        was = next(x for x in old_record["runs"][arm] if x["seed"] == 0)
        assert {k: row[k] for k in old} == {k: was[k] for k in old}, arm


def test_what_conserve_degree_does_to_the_graph() -> None:
    off = a13.one(a13.ARMS["off"], 0, ROUNDS)
    assert off["edges_initial"] == off["edges_close"] == 1489
    assert off["outdeg_nodes_changed"] == 0

    # No cluster, half, always: the same 180 promotions at one edge count.
    for arm in a13.DENSITY_LADDER:
        row = a13.one(a13.ARMS[arm], 0, ROUNDS)
        assert row["promoted"] == 180, arm
        assert row["edges_initial"] == row["edges_close"] == 1489, arm
        assert row["outdeg_moved_rounds"] == 0 and row["outdeg_nodes_changed"] == 0, arm

    # Demotion alone fires and leaves every out-degree where it started.
    demote = a13.one(a13.ARMS["demote .005"], 0, ROUNDS)
    assert demote["demoted"] > 0
    assert demote["outdeg_nodes_changed"] == 0
    assert demote["edges_close"] == demote["edges_initial"]

    # The arm told not to conserve degree still adds edges.
    loose = a13.one(a13.ARMS["both, degree not conserved"], 0, ROUNDS)
    assert loose["edges_close"] > loose["edges_initial"]


def test_an_asset_row_reads_three_objects_and_a_plain_row_one() -> None:
    spec = a13.ARMS["off"]
    row = a13.one(spec, 0, ROUNDS, asset=True)
    was = next(x for x in record("a13_mobility_asset.json")["runs"]["off"] if x["seed"] == 0)
    assert row["top1_wealth"] == was["top1_wealth"]

    # The same run, read here without the stage's code.
    cfg = a13.NetworkConfig(spec=a13.NetworkSpec(seed=0), seed=0, rounds=ROUNDS, rewire=spec)
    net = a13.carrier_model(cfg, asset=True)
    h = net.run()
    k = max(1, h.node_count // 100)
    recorded = a13.r(a13.top_share(h.holdings[-1], k))
    settled = a13.r(a13.top_share(net.holdings, k))
    worth = a13.r(a13.top_share(net.holdings + net.units @ net.price, k))
    assert row["top1_wealth"] == recorded
    assert row["top1_claims_settled"] == settled
    assert row["top1_net_worth"] == worth
    assert len({recorded, settled, worth}) == 3
    assert row["claims_moved_after_sample"] > 0
    assert 0.5 < row["held_value_share"] < 1.0

    plain = a13.one(spec, 0, ROUNDS)
    assert not [key for key in plain if "net_worth" in key or "settled" in key]
    assert "held_value_share" not in plain


def test_on_the_registered_carrier_the_last_row_is_the_state_the_run_ends_in() -> None:
    cfg = a13.NetworkConfig(spec=a13.NetworkSpec(seed=0), seed=0, rounds=SHORT,
                            rewire=a13.ARMS["both"])
    net = a13.carrier_model(cfg)
    h = net.run()
    assert np.array_equal(h.holdings[-1], net.holdings)
    with_asset = a13.carrier_model(cfg, asset=True)
    ha = with_asset.run()
    assert not np.array_equal(ha.holdings[-1], with_asset.holdings)
    # Claims are conserved across the settlement; only who holds them moves.
    assert abs(float(ha.holdings[-1].sum()) - float(with_asset.holdings.sum())) < 1e-8


def test_every_number_a_row_carries_is_rounded() -> None:
    for asset in (False, True):
        row = a13.one(a13.ARMS["both"], 1, SHORT, asset=asset)
        for key, value in row.items():
            if isinstance(value, float):
                assert value == round(value, a13.DIGITS), key


def test_the_ladder_seed_by_seed_is_the_ladder(grid) -> None:
    by_arm = grid[0]
    steps = a13.ladder_by_seed(by_arm)
    assert [(s["from"], s["to"]) for s in steps] == list(zip(a13.LADDER, a13.LADDER[1:]))
    for s in steps:
        lo = {row["seed"]: row["top1_wealth"] for row in by_arm[s["from"]]}
        want = [a13.r(row["top1_wealth"] - lo[row["seed"]]) for row in by_arm[s["to"]]]
        assert s["by_seed"] == want
        assert s["seeds_positive"] == sum(v > 0 for v in want)
        assert abs(s["mean"] - float(np.mean(want))) < 2e-6


def test_differences_from_the_off_arm_are_paired_by_seed(grid) -> None:
    by_arm = grid[0]
    shuffled = dict(copy.deepcopy(by_arm), off=list(reversed(by_arm["off"])))
    for key in ("top1_wealth", "mr_close"):
        assert a13.minus_off(shuffled, "both", key) == a13.minus_off(by_arm, "both", key)
    assert a13.minus_off(by_arm, "off", "top1_wealth") == [0.0] * SEEDS


def fake_rows(top1: list[float], mr: list[float] | None = None, fired: bool = True,
              edges: int = 10) -> list[dict]:
    mr = mr or [1.0] * len(top1)
    return [{"seed": s, "top1_wealth": t, "mr_close": m, "promoted": int(fired),
             "demoted": 0, "edges_initial": edges, "edges_close": edges,
             "outdeg_moved_rounds": 0, "outdeg_nodes_changed": 0,
             "outdeg_max_gain": 0, "outdeg_max_loss": 0}
            for s, (t, m) in enumerate(zip(top1, mr))]


def test_a_difference_from_off_is_a_difference_of_arm_means(grid) -> None:
    # Two seeds chosen so that the mean of the rounded seed differences and the
    # difference of the rounded arm means part in the sixth decimal.
    off, arm = [0.222901, 0.222901], [0.222001, 0.222004]
    by_arm = {"off": fake_rows(off, off, fired=False), "x": fake_rows(arm, arm)}
    of_means = a13.r(a13.mean_over(by_arm["x"], "top1_wealth")
                     - a13.mean_over(by_arm["off"], "top1_wealth"))
    of_seeds = a13.r(float(np.mean(a13.minus_off(by_arm, "x", "top1_wealth"))))
    assert of_means != of_seeds, "the fixture no longer tells the two apart"
    per = a13.graph_reading(by_arm)["per_arm"]["x"]
    assert per["top1_minus_off"] == of_means
    assert per["mr_minus_off"] == of_means
    assert per["top1_minus_off_by_seed"] == a13.minus_off(by_arm, "x", "top1_wealth")
    # And on the grid as run, both columns are the arm mean less the off mean.
    per_arm = a13.graph_reading(grid[0])["per_arm"]
    for a, v in per_arm.items():
        assert v["top1_minus_off"] == a13.r(v["top1"] - per_arm["off"]["top1"]), a
        assert v["mr_minus_off"] == a13.r(v["mr"] - per_arm["off"]["mr"]), a


def test_the_exchange_only_width_is_taken_over_those_arms_alone(grid) -> None:
    # An arm that is not exchange-only is pushed past both ends of the grid:
    # the width over all arms takes it, the exchange-only width does not.
    assert "both, degree not conserved" not in a13.EXCHANGE_ONLY
    by_arm = copy.deepcopy(grid[0])
    for row in by_arm["both, degree not conserved"]:
        row["top1_wealth"] = 0.9
    graph = a13.graph_reading(by_arm)
    means = {a: a13.mean_over(rows, "top1_wealth") for a, rows in by_arm.items()}
    inside = {a: means[a] for a in a13.EXCHANGE_ONLY}
    assert graph["highest"] == "both, degree not conserved"
    assert graph["highest_exchange_only"] in a13.EXCHANGE_ONLY
    assert graph["lowest_exchange_only"] in a13.EXCHANGE_ONLY
    assert graph["width_exchange_only"] == a13.r(max(inside.values()) - min(inside.values()))


def test_an_asset_width_is_also_read_seed_by_seed() -> None:
    def rows(values):
        return [{"seed": s, "top1_wealth": v, "top1_claims_settled": v,
                 "top1_net_worth": 2 * v, "promoted": 1, "demoted": 0}
                for s, v in enumerate(values)]

    # Seed 0 spans 0.1, seed 1 spans 0.3, the means span 0.1.
    by_arm = {"off": rows([0.2, 0.2]), "a": rows([0.3, 0.1]), "b": rows([0.25, 0.4])}
    got = a13.asset_readings(by_arm)
    assert set(got) == set(a13.ACCOUNTS)
    assert got["claims_recorded"]["row_key"] == "top1_wealth"
    assert got["claims_settled"]["row_key"] == "top1_claims_settled"
    assert got["claims_settled"]["width_by_seed"] == [0.1, 0.3]
    assert got["claims_recorded"]["width_by_seed"] == [0.1, 0.3]
    assert got["claims_recorded"]["width"] == 0.125
    assert got["net_worth"]["width_by_seed"] == [0.2, 0.6]


def test_the_graph_block_lists_only_arms_that_fired(grid) -> None:
    by_arm = grid[0]
    graph = a13.graph_reading(by_arm)
    assert graph["per_arm"]["off"]["edges_ratio"] == 1.0
    fixed = graph["fired_with_out_degree_fixed"]
    assert "off" not in fixed and NULL not in fixed
    assert set(fixed) <= set(graph["arms_that_fired"])
    assert graph["density_ladder"] == list(a13.DENSITY_LADDER)
    # An arm leaves the list the moment one seed moves one out-degree, whether
    # the close shows it or only the round-by-round count does.
    assert fixed
    for arm in fixed:
        for key in ("outdeg_nodes_changed", "outdeg_moved_rounds"):
            moved = copy.deepcopy(by_arm)
            moved[arm][0][key] = 1
            assert arm not in a13.graph_reading(moved)["fired_with_out_degree_fixed"], key


REGISTERED_ARMS = [
    "off", "rank k=1 cluster 0", "rank k=1 cluster .5", "rank k=1 cluster 1",
    "rank k=5 cluster .5", "rank k=2 share .001", "rank k=2 share .002",
    "demote .005", "demote .005 retain 0", "demote .005 retain 1", "both",
    "both, degree not conserved", "both, every 10 rounds", "demote, inbound cut",
    "both, inbound cut", "both + propensity", "both + propensity + payroll",
]


def test_the_registered_table() -> None:
    # A24 loads this module, reads two arms by name and sweeps the table.
    assert list(a13.ARMS) == REGISTERED_ARMS
    assert a13.ARMS["both, degree not conserved"].conserve_degree is False
    assert not a13.ARMS["off"].active
    assert len(a13.EXCHANGE_ONLY) == 13
    assert set(REGISTERED_ARMS) - set(a13.EXCHANGE_ONLY) == {
        "both, degree not conserved", "demote, inbound cut", "both, inbound cut",
        "both + propensity + payroll"}


def test_the_first_promotion_points_every_edge_it_can_into_the_core() -> None:
    # One round, seed 0, the cluster always firing. The promoted node keeps its
    # out-degree, and every edge it had outside the core now points into it.
    cfg = a13.NetworkConfig(spec=a13.NetworkSpec(seed=0), seed=0, rounds=1,
                            rewire=a13.ARMS["rank k=1 cluster 1"])
    net = a13.carrier_model(cfg)
    adj0, core0 = net.adjacency.copy(), net._in_core.copy()
    net.run()
    joined = np.flatnonzero(net._in_core & ~core0)
    assert joined.size == 1
    i = int(joined[0])
    before = np.flatnonzero(adj0[i] > 0)
    after = np.flatnonzero(net.adjacency[i] > 0)
    assert after.size == before.size > 0
    assert core0[after].all()
    assert int(net.adjacency.sum()) == int(adj0.sum()) == 1489


@pytest.mark.parametrize("arm", ["rank k=1 cluster 1", "rank k=1 cluster 0", "both",
                                 "demote .005 retain 0", "both, every 10 rounds",
                                 "both + propensity"])
def test_an_exchange_only_arm_holds_every_out_degree(arm) -> None:
    assert arm in a13.EXCHANGE_ONLY
    row = a13.one(a13.ARMS[arm], 0, ROUNDS)
    assert row["promoted"] + row["demoted"] > 0
    assert row["outdeg_moved_rounds"] == 0
    assert row["outdeg_nodes_changed"] == 0
    assert row["edges_close"] == row["edges_initial"]


def test_the_four_arms_that_move_out_degree_do(grid) -> None:
    by_arm = grid[0]
    moving = set(a13.ARMS) - set(a13.EXCHANGE_ONLY)
    assert moving == {"both, degree not conserved", "demote, inbound cut",
                      "both, inbound cut", "both + propensity + payroll"}
    loose = a13.one(a13.ARMS["both, degree not conserved"], 0, SHORT)
    assert loose["outdeg_moved_rounds"] > 0
    assert not a13.exchange_only_check(by_arm)["arms_that_moved"]


def test_the_exchange_check_names_an_arm_that_leaks(grid) -> None:
    by_arm = grid[0]
    check = a13.exchange_only_check(by_arm)
    assert a13.exchange_only_holds(check)
    assert check["arms"] == list(a13.EXCHANGE_ONLY)
    # One round in one seed of one exchange-only arm, or one node at the close.
    for key in ("outdeg_moved_rounds", "outdeg_nodes_changed"):
        leaked = copy.deepcopy(by_arm)
        leaked["both"][1][key] = 1
        got = a13.exchange_only_check(leaked)
        assert got["arms_that_moved"] == ["both"], key
        assert not a13.exchange_only_holds(got), key
    # An arm that moves out-degree on purpose is not checked.
    allowed = copy.deepcopy(by_arm)
    allowed["both, inbound cut"][0]["outdeg_moved_rounds"] = 7
    assert a13.exchange_only_holds(a13.exchange_only_check(allowed))
    # A grid missing an exchange-only arm is not a pass.
    short = {a: rows for a, rows in by_arm.items() if a != "both"}
    assert not a13.exchange_only_holds(a13.exchange_only_check(short))


def test_one_side_of_off_needs_every_seed_and_a_firing() -> None:
    def rows(values, fired=True):
        return [{"seed": s, "x": v, "promoted": int(fired), "demoted": 0}
                for s, v in enumerate(values)]

    by_arm = {
        "off": rows([1.0, 1.0, 1.0], fired=False),
        "below": rows([0.9, 0.8, 0.7]),
        "above": rows([1.1, 1.2, 1.3]),
        "mixed": rows([0.9, 1.1, 0.9]),
        "touching": rows([0.9, 1.0, 0.9]),
        "silent": rows([0.9, 0.9, 0.9], fired=False),
    }
    assert a13.one_side_of_off(by_arm, "x") == ["below", "above"]
