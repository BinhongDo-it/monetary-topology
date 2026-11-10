"""What A2c's driver records beside its seven criteria, and that each can fail.

The realized graph is read at a cutoff, so the record says how much the cutoff
decides. The potential graph is compared with its opening copy after every
round. Both Hodge splits are run, and which criteria the choice reaches is
worked out from the columns. And the zero-edge and one-edge arms are continued
to see where the strictly positive count goes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a2c_cycle_structure as A  # noqa: E402
from monetary_topology.network import Network, NetworkSpec  # noqa: E402

#: The same pattern ``test_records_carry_no_rounding_residue`` applies.
RESIDUE = re.compile(r"\d\.\d+[eE]-(?:1[2-9]|[2-9]\d|\d{3,})")

OLD_KEYS = ["stage", "rounds", "seed", "seeds_tested", "churn", "cycle_rank", "criteria"]
NEW_KEYS = ["definitions", "series", "hodge_choice", "cutoff", "cross_seed",
            "continuation", "continuation_one_edge", "potential_graph"]


class DeletesOneEdge(Network):
    """One potential edge is removed as round 10 closes."""

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        if t == 10:
            i, j = np.argwhere(self.adjacency > 0)[0]
            self.adjacency[i, j] = 0.0


class DeletesAndRestores(Network):
    """Removed as round 10 closes and put back as round 20 does."""

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        if t == 10:
            self._ij = tuple(int(x) for x in np.argwhere(self.adjacency > 0)[0])
            self.adjacency[self._ij] = 0.0
        if t == 20:
            self.adjacency[self._ij] = 1.0


# -- the cutoff ----------------------------------------------------------------


def test_cutoff_reading_on_a_matrix_whose_answer_is_known() -> None:
    potential = np.zeros((4, 4))
    for i, j in ((0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)):
        potential[i, j] = 1.0
    flow = np.zeros((4, 4))
    flow[0, 1], flow[1, 2], flow[3, 0] = 2.0, 1.0, 1.0   # a tree above the cutoff
    flow[2, 3], flow[1, 3] = 1e-200, 1e-250              # positive, far below it
    got = A.cutoff_reading(flow, potential, 1e-4)
    assert got["potential_rank"] == 3
    assert got["cutoff_rank"] == 0
    assert got["positive_rank"] == 2
    assert got["directed_edges_above_cutoff"] == 3
    assert got["directed_edges_positive_at_or_below_cutoff"] == 2
    assert got["directed_edges_exactly_zero"] == 1
    assert got["directed_edges_carrying_flow_outside_the_potential_graph"] == 0
    assert got["same_graph_at_zero_cutoff"] is False
    assert got["log10_cutoff"] == -4.0
    assert got["log10_smallest_flow_above_cutoff"] == 0.0
    assert got["log10_largest_flow_at_or_below_cutoff"] == -200.0
    assert got["log10_smallest_positive_flow"] == -250.0
    assert got["decades_of_cutoff_reading_this_graph"] == 200.0
    assert got["log10_share_of_volume_at_or_below_cutoff"] == -200.6

    # nothing between zero and the cutoff: the two counts are one count
    flow[2, 3] = flow[1, 3] = 0.0
    clean = A.cutoff_reading(flow, potential, 1e-4)
    assert clean["same_graph_at_zero_cutoff"] is True
    assert clean["positive_rank"] == clean["cutoff_rank"] == 0
    assert clean["decades_of_cutoff_reading_this_graph"] is None
    assert clean["log10_share_of_volume_at_or_below_cutoff"] is None
    assert clean["log10_smallest_positive_flow"] == clean["log10_smallest_flow_above_cutoff"]

    # a flow on an edge the potential graph does not have is counted, not hidden
    flow[2, 0] = 1.0
    assert A.cutoff_reading(flow, potential, 1e-4)[
        "directed_edges_carrying_flow_outside_the_potential_graph"] == 1


def test_magnitudes_are_written_as_exponents_and_six_figures() -> None:
    assert A.decades(1e-200) == -200.0
    assert A.decades(6.1869862903219225e-148) == -147.2
    assert A.decades(0.0) is None
    assert A.sig(1.0 / 3.0) == 0.333333
    assert A.sig(267.24850618149090) == 267.249


# -- the potential graph ---------------------------------------------------------


def test_the_graph_check_counts_every_round_and_sees_an_edge_go() -> None:
    spec = NetworkSpec(seed=0)
    seen = {}
    for name, klass in (("clean", Network), ("deletes", DeletesOneEdge),
                        ("restores", DeletesAndRestores)):
        before = len(A.GRAPH_CHECKS)
        history = A.go(spec, rounds=60, seed=0, network=klass)
        assert len(A.GRAPH_CHECKS) == before + 1
        seen[name] = A.GRAPH_CHECKS[-1]
        assert seen[name]["rounds"] == 60 == len(history.total_volume)
        assert seen[name]["layers"] == 2
    assert seen["clean"]["rounds_graph_equal_to_opening"] == 60
    assert A.graph_unchanged([seen["clean"]]) is True
    # removed as round 10 closes: rounds 0 to 9 closed on the opening graph
    assert seen["deletes"]["rounds_graph_equal_to_opening"] == 10
    assert A.graph_unchanged([seen["clean"], seen["deletes"]]) is False
    # put back ten rounds later: the closing graph is the opening one, and a
    # comparison made only at the end would have passed it
    assert seen["restores"]["rounds_graph_equal_to_opening"] == 50
    assert A.graph_unchanged([seen["restores"]]) is False
    # no run at all is not a run that left the graph alone
    assert A.graph_unchanged([]) is False


def stub_figures(unchanged):
    f9 = {
        "two_layer": {
            "gradient_norm": [1.0, 1.1],
            "flow_norm": [1.0, 20.0],
            "harmonic_norm": [1.0, 1.2],
            "harmonic_share": [0.1, 0.001],
        },
        "ratio_start": 1.0,
        "ratio_end": 20.0,
    }
    f10 = {
        "potential_rank": {0: 100},
        "final_fraction": {"0": 0.03, "1": 0.8, "30": 0.9},
    }
    if unchanged is not None:
        f10["graph_unchanged"] = unchanged
    return f9, f10


def test_a2c_4_reads_the_graph_check_and_not_its_own_sentence() -> None:
    def a2c_4(unchanged):
        f9, f10 = stub_figures(unchanged)
        found = {c.name[:5]: c for c in A.evaluate(60, 1, f9, f10)}
        return found["A2c-4"]

    assert a2c_4(True).passed is True
    assert a2c_4(False).passed is False
    assert a2c_4(None).passed is False
    # the detail is the registered sentence either way
    assert a2c_4(True).detail == a2c_4(False).detail


def test_figure_10_carries_the_check_of_its_own_runs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(A, "FIGURES", tmp_path)
    real_go = A.go

    def go_that_deletes(spec, **kw):
        return real_go(spec, network=DeletesOneEdge, **kw)

    A.apply_style()
    _, clean = A.figure_10(60, 0)
    assert clean["graph_unchanged"] is True
    assert set(clean["cutoff"]) == {str(k) for k in A.AUTONOMOUS_EDGES}
    assert clean["cutoff_zero_edges_by_snapshot"]["round"] == [0, 50, 59]
    assert clean["cutoff_zero_edges_by_snapshot"]["by_snapshot"][-1] == clean["cutoff"]["0"]
    monkeypatch.setattr(A, "go", go_that_deletes)
    _, faulty = A.figure_10(60, 0)
    assert faulty["graph_unchanged"] is False


# -- both splits -----------------------------------------------------------------


def test_both_splits_are_run_and_the_gradient_is_the_same_in_each() -> None:
    history = A.go(NetworkSpec(seed=0), rounds=60, seed=0)
    m = A.measure(history)
    assert m["round"] == [0, 50, 59]
    assert all(m["splits_agree"])
    for i in range(len(m["round"])):
        bare, curl, harmonic = (m["harmonic_norm_bare"][i], m["curl_norm"][i],
                                m["harmonic_norm"][i])
        assert bare**2 == pytest.approx(curl**2 + harmonic**2, rel=1e-9)
        assert m["flow_norm"][i] ** 2 == pytest.approx(
            m["gradient_norm"][i] ** 2 + bare**2, rel=1e-9)
        assert bare > harmonic
        assert m["net_flow_l1"][i] <= m["gross_volume"][i]
    assert m["gradient_norm_bare"] == m["gradient_norm"]
    choice = A.hodge_choice(m)
    assert choice["splits_agree_at_every_snapshot"] is True
    assert choice["criteria_that_read_the_choice"] == ["A2c-3"]
    assert choice["no_face_filled"]["outside_the_gradient_norm_first_last"] == [
        A.sig(m["harmonic_norm_bare"][0]), A.sig(m["harmonic_norm_bare"][-1])]
    # A2c-2's ratio is the third of these, on the same two snapshots
    ratio = [f / g for f, g in zip(m["flow_norm"], m["gradient_norm"], strict=True)]
    assert choice["growth_of_the_ratio_to_the_gradient_norm_on_the_same_run"][
        "net_flow_per_edge_norm"] == pytest.approx(ratio[-1] / ratio[0], rel=1e-5)


def test_which_criteria_read_the_choice_is_worked_out_from_the_columns(
        monkeypatch) -> None:
    history = A.go(NetworkSpec(seed=0), rounds=10, seed=0)
    real = A.hodge_decomposition
    assert A.criteria_that_read_the_choice(A.measure(history)) == ["A2c-3"]

    # a bare split whose gradient were another vector would reach A2c-1 and A2c-2
    def gradient_moved(flow, adjacency, *, fill_triangles=True):
        split = real(flow, adjacency, fill_triangles=fill_triangles)
        if fill_triangles:
            return split
        return type(split)(split.gradient * 1.001, split.curl, split.harmonic, 0)

    monkeypatch.setattr(A, "hodge_decomposition", gradient_moved)
    assert A.criteria_that_read_the_choice(A.measure(history)) == [
        "A2c-1", "A2c-2", "A2c-3"]

    # and columns that agree under both splits name no criterion
    same = {"gradient_norm": [1.0, 2.0], "harmonic_norm": [0.5, 0.4],
            "harmonic_share": [0.1, 0.01]}
    same.update({f"{k}_bare": list(v) for k, v in same.items()})
    assert A.criteria_that_read_the_choice(same) == []
    same["harmonic_share_bare"] = [0.1, 0.02]
    assert A.criteria_that_read_the_choice(same) == ["A2c-3"]


def test_the_agreement_flag_fails_when_the_two_splits_do_not_agree(monkeypatch) -> None:
    history = A.go(NetworkSpec(seed=0), rounds=10, seed=0)
    real = A.hodge_decomposition

    def faces_ignored(flow, adjacency, *, fill_triangles=True):
        return real(flow, adjacency, fill_triangles=True)

    monkeypatch.setattr(A, "hodge_decomposition", faces_ignored)
    assert not any(A.measure(history)["splits_agree"])

    def gradient_moved(flow, adjacency, *, fill_triangles=True):
        split = real(flow, adjacency, fill_triangles=fill_triangles)
        if fill_triangles:
            return split
        return type(split)(split.gradient * 1.001, split.curl, split.harmonic, 0)

    monkeypatch.setattr(A, "hodge_decomposition", gradient_moved)
    assert not any(A.measure(history)["splits_agree"])


# -- the continuation --------------------------------------------------------------


def test_the_continuation_is_the_same_run_and_the_two_counts_meet() -> None:
    short = A.go(A.three_layer(0, 0), rounds=600, seed=0)
    at_600 = A.last_reading(short)
    assert at_600["positive_rank"] > at_600["cutoff_rank"]
    assert at_600["decades_of_cutoff_reading_this_graph"] > 100.0

    got = A.continued(0, short)
    assert got["rounds"] == A.CONTINUE_ROUNDS
    assert got["reproduces_the_registered_run_at_shared_snapshots"] is True
    assert got["shared_snapshots"] == 12
    assert got["cutoff_rank_values_after_round_0"] == [at_600["cutoff_rank"]]
    assert got["positive_rank_at_last_snapshot"] == at_600["cutoff_rank"]
    assert got["positive_rank_values_after_round_0"][0] > at_600["cutoff_rank"]
    assert got["positive_rank_equals_cutoff_rank_from_snapshot"] > 599
    assert (got["last_snapshot_with_positive_rank_above_cutoff_rank"]
            < got["positive_rank_equals_cutoff_rank_from_snapshot"])

    # stopped before the flows leave the range, the two counts have not met
    early = A.continued(0, short, rounds=800)
    assert early["positive_rank_equals_cutoff_rank_from_snapshot"] is None
    assert early["last_snapshot_with_positive_rank_above_cutoff_rank"] == 799
    assert early["positive_rank_at_last_snapshot"] > early["cutoff_rank_at_last_snapshot"]

    # a run that is not this run continued is reported as such
    class Other:
        epsilon_absolute = short.epsilon_absolute
        snapshots = {t: f.copy() for t, f in short.snapshots.items()}

    Other.snapshots[50] = Other.snapshots[50] + 1.0
    assert A.continued(0, Other, rounds=800)[
        "reproduces_the_registered_run_at_shared_snapshots"] is False


def test_the_one_edge_arm_continued_keeps_its_loops() -> None:
    short = A.go(A.three_layer(0, 1), rounds=600, seed=0)
    got = A.continued(0, short, edges=1)
    assert got["autonomous_edges"] == 1
    assert got["reproduces_the_registered_run_at_shared_snapshots"] is True
    assert got["positive_rank_at_last_snapshot"] == got["cutoff_rank_at_last_snapshot"]
    assert got["positive_rank_at_last_snapshot"] > got["potential_rank"] / 2
    assert got["positive_rank_over_potential_at_last_snapshot"] == A.sig(
        got["positive_rank_at_last_snapshot"] / got["potential_rank"])
    # the other arm's run continued from this one's is not this arm continued
    assert A.continued(0, short, rounds=700)[
        "reproduces_the_registered_run_at_shared_snapshots"] is False


# -- the record ----------------------------------------------------------------


def test_a_small_run_writes_every_old_field_first_and_no_residue(
        tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(A, "ROOT", tmp_path)
    monkeypatch.setattr(A, "FIGURES", tmp_path / "figures")
    monkeypatch.setattr(A, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(A, "CONTINUE_ROUNDS", 300)
    monkeypatch.setattr(sys, "argv", ["a2c", "--rounds", "120", "--seeds", "1"])
    A.main()
    text = (tmp_path / "results" / "a2c_cycle_structure.json").read_text(encoding="utf-8")
    record = json.loads(text)
    assert list(record) == OLD_KEYS + NEW_KEYS
    assert sorted(record["churn"]) == ["ratio_end", "ratio_start"]
    assert sorted(record["cycle_rank"]) == ["final_fraction", "potential_rank"]
    assert len(record["criteria"]) == 7
    assert RESIDUE.findall(text) == []
    graph = record["potential_graph"]
    # figure 9, six arms of figure 10, two per seed, two continuations, A2c-7
    assert graph["runs"] == 1 + len(A.AUTONOMOUS_EDGES) + 2 + 2 + 1 == len(graph["by_run"])
    assert graph["rounds"] == graph["rounds_closing_on_the_opening_graph"]
    assert graph["rounds"] == 10 * 120 + 2 * 300
    assert graph["unchanged_in_every_run"] is True
    assert record["series"]["two_layer"]["round"] == [0, 50, 100, 119]
    assert set(record["series"]["three_layer_realized_rank"]) == {
        str(k) for k in A.AUTONOMOUS_EDGES}
    # each continuation is its own arm continued
    for block, edges in (("continuation", 0), ("continuation_one_edge", 1)):
        (c,) = record[block]
        assert c["autonomous_edges"] == edges
        assert c["rounds"] == 300
        assert c["reproduces_the_registered_run_at_shared_snapshots"] is True
    # A2c-2's ratio over its two ends is the norm's entry here
    assert record["hodge_choice"][
        "growth_of_the_ratio_to_the_gradient_norm_on_the_same_run"][
        "net_flow_per_edge_norm"] == pytest.approx(
        record["churn"]["ratio_end"] / record["churn"]["ratio_start"], rel=1e-5)


def test_the_registered_record_ties_its_new_blocks_to_its_old_numbers() -> None:
    path = ROOT / "results" / "a2c_cycle_structure.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert list(record) == OLD_KEYS + NEW_KEYS
    assert (record["rounds"], record["seed"], record["seeds_tested"]) == (600, 0, 6)
    assert RESIDUE.findall(path.read_text(encoding="utf-8")) == []

    # the rank the criteria read is the rank at the cutoff in the new block
    for k, fraction in record["cycle_rank"]["final_fraction"].items():
        arm = record["cutoff"]["by_autonomous_edges"][k]
        assert arm["potential_rank"] == record["cycle_rank"]["potential_rank"][k]
        assert arm["cutoff_rank"] / arm["potential_rank"] == fraction
        assert arm["directed_edges_carrying_flow_outside_the_potential_graph"] == 0
        assert record["series"]["three_layer_realized_rank"][k]["realized_rank"][-1] == (
            arm["cutoff_rank"])
    for row, collapsed, rescued in zip(record["cutoff"]["by_seed"],
                                       record["cross_seed"]["collapsed"],
                                       record["cross_seed"]["rescued"], strict=True):
        zero, one = row["zero_edges"], row["one_edge"]
        assert A.sig(zero["cutoff_rank"] / zero["potential_rank"]) == collapsed
        assert A.sig(one["cutoff_rank"] / one["potential_rank"]) == rescued
        # the cutoff sits in an empty band: wide below it, and some way above
        assert zero["decades_of_cutoff_reading_this_graph"] > 100.0
        assert zero["log10_largest_flow_at_or_below_cutoff"] < zero["log10_cutoff"] - 100.0
        assert zero["log10_smallest_flow_above_cutoff"] > zero["log10_cutoff"]

    # below the cutoff the flows are not at rest: the largest of them is smaller
    # at every snapshot, and the rank at the cutoff does not move while it falls
    arm = record["cutoff"]["zero_edges_by_snapshot"]
    assert arm["round"] == record["series"]["three_layer_realized_rank"]["0"]["round"]
    later = arm["by_snapshot"][1:]
    assert [s["cutoff_rank"] for s in later] == (
        record["series"]["three_layer_realized_rank"]["0"]["realized_rank"][1:])
    assert len({s["cutoff_rank"] for s in later}) == 1
    largest = [s["log10_largest_flow_at_or_below_cutoff"] for s in later]
    assert all(b < a - 5.0 for a, b in zip(largest, largest[1:]))
    assert later[-1] == record["cutoff"]["by_autonomous_edges"]["0"]
    # an edge that leaves the positive count goes to exactly zero, and the
    # smallest positive flow is never below the smallest a double can hold
    for s in arm["by_snapshot"]:
        assert s["positive_rank"] <= s["potential_rank"]
        assert s["log10_smallest_positive_flow"] >= -324.0
        if s["log10_largest_flow_at_or_below_cutoff"] is not None:
            assert s["log10_smallest_positive_flow"] <= s["log10_largest_flow_at_or_below_cutoff"]

    # continued, the count over every positive flow is the count at the cutoff
    assert [c["seed"] for c in record["continuation"]] == list(range(6))
    for c, row in zip(record["continuation"], record["cutoff"]["by_seed"], strict=True):
        assert c["reproduces_the_registered_run_at_shared_snapshots"] is True
        assert c["cutoff_rank_values_after_round_0"] == [row["zero_edges"]["cutoff_rank"]]
        assert c["positive_rank_at_last_snapshot"] == row["zero_edges"]["cutoff_rank"]
        assert c["positive_rank_equals_cutoff_rank_from_snapshot"] > 599
        assert c["positive_rank_over_potential_at_last_snapshot"] < 0.10

    # the one-edge arm continued keeps its loops, with nothing below the cutoff
    for c, row, rescued in zip(record["continuation_one_edge"], record["cutoff"]["by_seed"],
                               record["cross_seed"]["rescued"], strict=True):
        assert c["autonomous_edges"] == 1
        assert c["reproduces_the_registered_run_at_shared_snapshots"] is True
        assert c["potential_rank"] == row["one_edge"]["potential_rank"]
        assert c["positive_rank_at_last_snapshot"] == c["cutoff_rank_at_last_snapshot"]
        assert c["positive_rank_over_potential_at_last_snapshot"] > 0.5

    # the two-layer run of A2c-7: outside the realized graph the flow is zero
    two = record["cutoff"]["two_layer_by_snapshot"]
    assert two["by_snapshot"][-1]["same_graph_at_zero_cutoff"] is True
    assert two["by_snapshot"][-1]["positive_rank"] == two["realized_rank"][-1]

    # both splits, and which growth the x97 is
    choice = record["hodge_choice"]
    assert choice["splits_agree_at_every_snapshot"] is True
    m = record["series"]["two_layer"]
    # both sides are six-figure roundings, so they agree to five
    assert choice["growth_on_the_same_run"]["net_flow_per_edge_norm"] == pytest.approx(
        m["flow_norm"][-1] / m["flow_norm"][0], rel=1e-5)
    assert choice["growth_on_the_same_run"]["gross_volume"] == pytest.approx(
        m["gross_volume"][-1] / m["gross_volume"][0], rel=1e-5)
    assert record["churn"]["ratio_end"] == pytest.approx(
        m["flow_norm"][-1] / m["gradient_norm"][-1], rel=1e-5)
    assert choice["criteria_that_read_the_choice"] == ["A2c-3"]
    assert choice["growth_of_the_ratio_to_the_gradient_norm_on_the_same_run"][
        "net_flow_per_edge_norm"] == pytest.approx(
        record["churn"]["ratio_end"] / record["churn"]["ratio_start"], rel=1e-5)

    graph = record["potential_graph"]
    assert graph["unchanged_in_every_run"] is True
    assert graph["runs"] == 1 + 6 + 2 * 6 + 2 * 6 + 1
    assert graph["rounds"] == graph["rounds_closing_on_the_opening_graph"] == (
        20 * 600 + 12 * A.CONTINUE_ROUNDS)
    assert {c["name"][:5]: c["passed"] for c in record["criteria"]}["A2c-4"] is True
