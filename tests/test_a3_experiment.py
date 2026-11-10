"""What A3's driver counts, and what its summaries leave out.

Four things the stage prints depend on reading an object for what it is: which
trades a round-zero date stands for, how many nodes a count of cells covers,
which way a holder moved after a transfer, and whether a row has a retention to
read at all. Each has a wrong input here that the reading has to refuse.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a3_asset_channel as A  # noqa: E402


# ---------------------------------------------------------------------------
# round zero
# ---------------------------------------------------------------------------


def ledger(*rows) -> SimpleNamespace:
    return SimpleNamespace(trades=list(rows))


def test_the_opening_units_are_the_head_of_each_queue() -> None:
    model = ledger(
        (1, 0, 0, 3, 2.0, 2.5, 1.0),
        (2, 0, 0, 4, 2.0, 2.5, 1.0),   # node 2 was handed nothing at the opening
        (1, 0, 0, 6, 2.0, 2.5, 1.0),
        (1, 0, 0, 9, 2.0, 2.5, 1.0),   # node 1's third sale: bought on resale
        (1, 1, 0, 9, 2.0, 2.5, 1.0),   # another tier is another queue
    )
    assert A.sold_from_opening(model, {(1, 0): 2}) == [
        True, False, True, False, False]
    assert A.sold_from_opening(model, {}) == [False] * 5


def test_the_date_and_the_origin_differ_on_the_round_zero_resale_alone() -> None:
    model = ledger(
        (1, 0, 0, 5, 2.0, 9.0, 1.0),    # opening unit, stretched: pays what it has
        (1, 0, 0, 9, 3.0, 9.0, 2.0),    # bought on resale in round zero
        (1, 0, 7, 12, 6.0, 9.0, 4.0),   # an ordinary resale
    )
    by_date = A.adjusted_trades(model)
    assert by_date == {(1, 0): [float(np.log(4.0 / 6.0))]}
    flags = A.sold_from_opening(model, {(1, 0): 1})
    by_origin = A.adjusted_trades(model, flags)
    assert by_origin == {
        (1, 0): [float(np.log(2.0 / 3.0)), float(np.log(4.0 / 6.0))]}


def test_the_windows_follow_the_same_switch(monkeypatch) -> None:
    """Node 1 is the better-termed one and its only trade in the first window
    is a unit it bought on resale in round zero. By date that window has
    nothing of node 1 in it; by origin it does, and node 1 wins it."""
    model = ledger(
        (1, 0, 0, 50, 1.0, 9.0, 3.0),     # bought on resale in round zero
        (2, 0, 4, 60, 2.0, 9.0, 3.0),
        (1, 0, 120, 150, 1.0, 9.0, 3.0),
        (2, 0, 120, 150, 2.0, 9.0, 3.0),
    )
    monkeypatch.setattr(
        A, "terms_pair", lambda m: (np.array([1]), np.array([2])))
    assert A.window_signs([model]) == [[False, True, False]]
    origins = [A.sold_from_opening(model, {})]
    assert A.window_signs([model], origins) == [[True, True, False]]


@pytest.fixture(scope="module")
def one_model():
    return A.run(0)


def test_every_opening_unit_is_dated_zero_and_none_is_dated_later(one_model) -> None:
    opening = A.opening_basis(0)
    # units are conserved and every allocated unit was given a cost basis
    assert sum(opening.values()) == int(one_model.units.sum()) == 61
    flags = A.sold_from_opening(one_model, opening)
    assert len(flags) == len(one_model.trades)
    sold: dict[tuple[int, int], int] = {}
    for row, opened in zip(one_model.trades, flags, strict=True):
        key = (int(row[0]), int(row[1]))
        if opened:
            assert row[2] == 0
            sold[key] = sold.get(key, 0) + 1
        if row[2] != 0:
            assert not opened
    assert all(n <= opening[key] for key, n in sold.items())

    got = A.round_zero_resales(range(1), [one_model])
    row = got["per_seed"][0]
    dated_zero = sum(1 for r in one_model.trades if r[2] == 0)
    assert row["rows_dated_round_zero"] == dated_zero
    assert row["of_which_bought_on_resale"] == dated_zero - sum(flags)
    assert got["bought_on_resale_in_round_zero"] == 2
    assert got["they_paid_gamma_times_the_reference_price"] is True
    # counting them moves the reading, so the two are not one number twice
    assert got["a3_4_as_scored"] != got["a3_4_with_them"]
    scored = A.terms_differential([one_model])
    assert got["a3_4_as_scored"]["ledger"] == round(scored[0], 10)
    assert f"{scored[0]:+.5f}" in A.a3_4([one_model]).detail


def test_a3_3_counts_cells_and_nodes_separately(one_model) -> None:
    series = {k: v for k, v in A.adjusted_trades(one_model).items() if len(v) >= 4}
    cells = len(series)
    nodes = len({node for node, _tier in series})
    assert nodes < cells          # some node trades four times in two tiers
    # the same index in two seeds is two agents, so two models double both
    detail = A.a3_3([one_model, one_model]).detail
    assert f"over {2 * cells} (seed, node, tier) cells" in detail
    assert f"on {2 * nodes} nodes counted once per seed" in detail


# ---------------------------------------------------------------------------
# the shock, with its direction
# ---------------------------------------------------------------------------


def series(landing: float, later: float) -> np.ndarray:
    out = np.zeros(300)
    out[A.A3_6_SHOCK_ROUND] = landing
    out[A.A3_6_SHOCK_ROUND + A.A3_6_HORIZON] = later
    return out


def test_the_size_and_the_direction_are_read_off_one_series() -> None:
    down = series(10.0, -4.0)
    assert A._trace_of(down)[0] == 0.4
    response, landing, by_h = A._signed_of(down)
    assert (response, landing) == (-0.4, 10.0)
    assert by_h[str(A.A3_6_HORIZON)] == -0.4
    assert A._below_baseline(response, landing)
    assert not A._below_baseline(0.4, 10.0)
    # a gap that opened downward and is still downward is below baseline too
    assert A._below_baseline(0.4, -10.0)
    assert A._kept_above(0.6, 10.0, 0.5)
    assert not A._kept_above(-0.6, 10.0, 0.5)
    assert not A._kept_above(0.6, -10.0, 0.5)
    assert not A._kept_above(None, 10.0, 0.5)


def test_no_gap_in_the_landing_round_is_no_response() -> None:
    flat = series(0.0, 3.0)
    assert A._trace_of(flat)[:2] == (0.0, 0.0)
    response, landing, by_h = A._signed_of(flat)
    assert response is None and landing == 0.0
    assert set(by_h.values()) == {None}
    assert not A._below_baseline(None, 0.0)
    assert A._response_words([None, -0.00177441, 0.0]) == (
        "no gap in the landing round, -0.177%, +0.000%")


def test_a3_6_prints_the_direction_beside_the_registered_size(monkeypatch) -> None:
    """Three holders: one keeps six tenths, one ends seven tenths *below* its
    own path, one keeps a tenth. On size the median is 0.6 and two clear; with
    the sign one clears and the median is 0.1."""
    base = SimpleNamespace(_is_production=np.zeros(8, dtype=bool))
    later = {0: 6.0, 1: -7.0, 2: 1.0}

    def fake_deviation(seed, target, base=None, **kw):
        if target in later:
            return series(10.0, later[target])
        return series(0.0, 0.5)          # the non-holder: nothing at landing

    monkeypatch.setattr(A, "run", lambda seed, **kw: base)
    monkeypatch.setattr(
        A, "_holders_at_shock",
        lambda seed, **kw: (np.array([0, 1, 2]), np.array([5, 6, 7])))
    monkeypatch.setattr(A, "_shock_deviation", fake_deviation)

    record: dict = {}
    got = A.a3_6(range(1), record=record)
    assert got.passed is True            # the registered statistic is the size
    assert "**2 of 3 holders clear the threshold**" in got.detail
    assert "1 of 3 clear it above their own baseline" in got.detail
    assert "1 of 3 stand below their own baseline" in got.detail
    assert "and the per-seed median averaged over the seeds is 10.0%" in got.detail
    assert got.detail.startswith(
        "holder median of the gap from its own untransferred path")
    assert "taken per seed and averaged over the 1 seeds: 60.0%" in got.detail
    assert "no gap in the landing round" in got.detail
    assert record["holders_clearing_on_size"] == 2
    assert record["holders_clearing_above_baseline"] == 1
    assert record["holders_below_baseline_at_horizon"] == 1
    assert record["median_of_sizes_mean_over_seeds"] == 0.6
    assert record["median_with_sign_mean_over_seeds"] == 0.1
    assert [h["response"] for h in record["holders"]] == [0.6, -0.7, 0.1]
    assert record["nonholders_one_per_seed"] == [
        {"seed": 0, "node": 6, "landing": 0.0, "response": None}]


# ---------------------------------------------------------------------------
# the profile's summary
# ---------------------------------------------------------------------------


def row(node, holder, wealth, retention, *, footprint=1.0, signed=None,
        production=True, seed=0) -> dict:
    """A profile row as ``retention_profile`` stores it.

    An unmeasured row (``footprint=0.0``) is passed ``retention=None``, which
    is what the driver stores; a test that wants the format written before
    2026-10-25 passes ``0.0`` instead.
    """
    by_h = {str(h): retention for h in A.PROFILE_HORIZONS}
    signed = retention if signed is None else signed
    measured = footprint != 0.0
    return {
        "seed": seed, "node": node, "shock_round": 150, "holder": holder,
        "production": production, "retention_by_horizon": by_h,
        "wealth_at_shock": wealth, "net_worth_at_shock": wealth,
        "opening_claims": wealth, "retention": retention,
        "shock_footprint": abs(footprint),
        "signed_footprint": footprint,
        "signed_retention": signed if measured else None,
        "signed_by_horizon": {
            str(h): (signed if measured else None) for h in A.PROFILE_HORIZONS},
    }


def profile_rows() -> list[dict]:
    return [
        row(0, False, 0.0, 0.10),
        row(1, False, 0.0, 0.20),
        row(2, False, 0.0, None, footprint=0.0),     # nothing at landing
        row(3, False, 7.0, 0.05),
        row(4, True, 5.0, 0.30, signed=-0.30),       # ends below its own path
        row(5, True, 9.0, 0.50),
    ]


def test_a_row_with_no_landing_gap_is_listed_and_left_out() -> None:
    got = A.summarise_profile(profile_rows())
    assert got["n_no_measurable_shock"] == 1
    assert [(r["seed"], r["node"]) for r in got["unmeasured"]] == [(0, 2)]
    assert (got["n_nonholders"], got["n_nonholders_measured"]) == (4, 3)
    # folded in as a zero the median would be 0.075
    assert got["nonholder_median"] == 0.10
    group = {g["group"]: g for g in got["by_layer_group"]}
    no_asset = group["production_layer_no_asset"]
    assert (no_asset["n"], no_asset["n_measured"]) == (4, 3)
    assert no_asset["median"] == 0.10
    assert no_asset["by_horizon"]["40"] == 0.10
    assert group["financial_layer_with_asset"] == {
        "group": "financial_layer_with_asset", "n": 0, "n_measured": 0}
    assert sum(d["n_unmeasured"] for d in got["by_wealth_decile"]) == 1
    assert sum(d["n_nonholders"] for d in got["by_wealth_decile"]) == 3
    assert got["gradient_within_nonholders"]["n"] == 3
    # by wealth: 0.10, 0.20, (unmeasured), 0.30, 0.05, 0.50. The largest step
    # is the last one, and its rank is the one it has among all six rows.
    jump = got["largest_jump"][0]
    assert jump["largest_adjacent_jump"] == pytest.approx(0.45)
    assert (jump["at_rank"], jump["of_ranks"]) == (5, 6)


def unmeasured_rows_store_no_number(rows: list[dict]) -> bool:
    """Every row without a landing gap stores ``None`` for its ratio,
    at the registered horizon and at every profile horizon."""
    return all(
        r["retention"] is None
        and all(v is None for v in r["retention_by_horizon"].values())
        for r in rows if r["shock_footprint"] == 0.0
    )


def test_the_profile_stores_no_ratio_for_a_row_with_no_landing_gap(
        monkeypatch) -> None:
    """Three nodes, one of which shows nothing in the landing round. The
    driver must store ``None`` for that node's ratio at every horizon, keep
    its raw deviations, and leave it out of the count of retentions above one.
    """
    n = 3
    model = SimpleNamespace(
        _n=n, _is_production=np.ones(n, dtype=bool),
        _claims_0=np.arange(n, dtype=float),
        holdings=np.arange(n, dtype=float),
        units=np.zeros((n, 1)),
        net_worth=lambda: np.arange(n, dtype=float))
    later = {0: 4.0, 2: 15.0}           # node 2's gap grows past its landing gap

    def fake_deviation(seed, target, base=None, *, shock_round, **kw):
        out = np.zeros(300)
        if target in later:
            out[shock_round] = 10.0
            out[shock_round + 1:] = later[target]
        else:
            out[shock_round + 1:] = 3.0  # moves later, nothing at landing
        return out

    monkeypatch.setattr(A, "run", lambda seed, **kw: model)
    monkeypatch.setattr(A, "_shock_deviation", fake_deviation)
    got = A.retention_profile(range(1))
    rows = {r["node"]: r for r in got["rows"]}
    assert unmeasured_rows_store_no_number(got["rows"])
    flat = rows[1]
    assert (flat["shock_footprint"], flat["signed_footprint"]) == (0.0, 0.0)
    assert flat["signed_retention"] is None
    assert rows[0]["retention"] == pytest.approx(0.4)
    assert got["n_no_measurable_shock"] == 1
    assert got["n_retention_above_one"] == 1
    # the check flips on the format it exists to refuse: a stored zero
    seeded = [dict(r, retention=0.0) if r["node"] == 1 else r
              for r in got["rows"]]
    assert not unmeasured_rows_store_no_number(seeded)
    seeded_h = [dict(r, retention_by_horizon={**r["retention_by_horizon"],
                                              "40": 0.0})
                if r["node"] == 1 else r for r in got["rows"]]
    assert not unmeasured_rows_store_no_number(seeded_h)


def test_a_pair_with_an_unmeasured_member_reads_neither_way() -> None:
    rows = profile_rows()
    rows[3] = row(3, False, 7.0, None, footprint=0.0)  # the richest non-holder
    pair = A.summarise_profile(rows)["boundary_pair"][0]
    assert pair["unmeasured_member"] is True
    assert pair["discriminating"] is False and pair["step"] is False


def test_the_report_names_why_an_unmeasured_pair_reads_neither_way(capsys) -> None:
    rows = profile_rows()
    rows[3] = row(3, False, 7.0, None, footprint=0.0)  # the richest non-holder
    A.print_profile(A.summarise_profile(rows))
    out = capsys.readouterr().out
    assert "one of the two shows no gap in the landing round" in out
    assert "the holder is the richer of the two" not in out
    assert "(1 pairs have a member with no landing gap)" in out
    unsigned = [{k: v for k, v in r.items() if not k.startswith("signed_")}
                for r in rows]
    A.print_profile(A.summarise_profile(unsigned))
    out = capsys.readouterr().out
    assert "size     n/a" in out
    assert "size   0.00%" not in out
    # a record written before 2026-10-25 stores 0.0 for the unmeasured ratio
    old = [dict(r, retention=0.0,
                retention_by_horizon={h: 0.0 for h in r["retention_by_horizon"]})
           if r["shock_footprint"] == 0.0 else r for r in unsigned]
    A.print_profile(A.summarise_profile(old))
    out = capsys.readouterr().out
    assert "size     n/a" in out
    assert "size   0.00%" not in out


def test_tied_values_share_a_rank_and_row_order_does_not_matter() -> None:
    assert A.average_ranks([3.0, 1.0, 1.0, 2.0]).tolist() == [4.0, 1.5, 1.5, 3.0]
    rows = profile_rows()
    forward = A.summarise_profile(rows)["gradient_within_nonholders"]["spearman"]
    backward = A.summarise_profile(rows[::-1])[
        "gradient_within_nonholders"]["spearman"]
    # wealth (0, 0, 7) against retention (0.10, 0.20, 0.05), ties sharing 1.5
    assert forward == pytest.approx(-1.5 / np.sqrt(3.0))
    assert backward == pytest.approx(forward)
    assert A.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert A.spearman([1.0, 2.0], [1.0, 2.0]) is None


def test_the_boundary_pair_is_read_a_second_time_with_the_direction() -> None:
    got = A.summarise_profile(profile_rows())
    pair = got["boundary_pair"][0]
    # the poorer holder (wealth 5) against the richer non-holder (wealth 7)
    assert pair["discriminating"] is True
    assert pair["step"] is True                 # 0.30 against 0.05 on size
    assert pair["poorest_holder_signed"] == -0.30
    assert pair["step_with_sign"] is False      # it ended below its own path
    sign = got["sign"]
    assert sign["below_baseline_at_horizon"] == {"holders": 1, "nonholders": 0}
    assert sign["direction_reversed_by_horizon"] == 1
    assert sign["landing_below_baseline"] == 0
    assert sign["holder_median_with_sign"] == pytest.approx(0.10)
    group = {g["group"]: g for g in got["by_layer_group"]}
    assert group["production_layer_with_asset"]["below_baseline_at_horizon"] == 1


def test_rows_stored_before_the_direction_was_kept_still_summarise() -> None:
    rows = [{k: v for k, v in r.items() if not k.startswith("signed_")}
            for r in profile_rows()]
    got = A.summarise_profile(rows)
    assert got["sign"] is None
    assert "step_with_sign" not in got["boundary_pair"][0]
    assert got["nonholder_median"] == 0.10


def test_the_report_prints_from_the_summary(capsys) -> None:
    A.print_profile(A.summarise_profile(profile_rows()))
    out = capsys.readouterr().out
    assert "no measurable shock 1" in out
    assert "seed 0: nodes [2]" in out
    assert "(1 left out)" in out
    assert "of those 1: step 1, gradient 0" in out
    assert "direction of the response kept, 0 of the 1 read as a step" in out
    assert "1 of 2 holders" in out


# ---------------------------------------------------------------------------
# the rent sweep
# ---------------------------------------------------------------------------


def test_the_rent_summary_reads_the_result_it_describes() -> None:
    result = {
        "rates": [0.0, 0.01],
        "dropped_from_paired_population": 3,
        "zero_calibration_ok": True,
        "per_rate": {
            rate: {
                "renter_delta_median": -0.1, "renter_delta_worst": -0.2,
                "landlord_delta_median": landlord, "landlord_n": 0.2,
                "landlord_seeds": seeds, "seeds": 5,
                "financial_delta_median": 0.3, "financial_n": 16.0,
                "rent_per_round_share": 0.001, "rent_cumulative_share": 0.4,
            }
            for rate, landlord, seeds in (("0", None, 0), ("0.01", -0.5, 1))
        },
    }
    lines = A.rent_sweep_lines(result)
    assert len(lines) == 4
    assert lines[0].endswith("dropped from the paired population: 3")
    assert "zero calibration: ok" in lines[0]
    assert "landlord none (0 of 5 seeds" in lines[1]
    assert "landlord -0.5000 (1 of 5 seeds" in lines[2]
    result["zero_calibration_ok"] = False
    assert "zero calibration: BROKEN" in A.rent_sweep_lines(result)[0]


def test_an_empty_landlord_set_contributes_no_figure() -> None:
    assert A._mean_present([None, -0.5, None]) == -0.5
    assert A._mean_present([0.25, 0.75]) == 0.5
    assert A._mean_present([None, None]) is None
    # seed 0 at the registered length: no production-layer node still holds
    got = A.rent_sweep(range(1), 300)
    assert got["zero_calibration_ok"] is True
    for rate in A.RENT_RATES:
        entry = got["per_rate"][f"{rate:g}"]
        assert entry["landlord_n"] == 0.0
        assert entry["landlord_delta_median"] is None
        assert (entry["landlord_seeds"], entry["seeds"]) == (0, 1)
        assert entry["financial_seeds"] == 1
    lines = A.rent_sweep_lines(got)
    assert len(lines) == len(A.RENT_RATES) + 2
    assert all("landlord none (0 of 1 seeds" in line for line in lines[1:-1])
