"""Stage A8: the resolution the surfaces are read at, and the close of the books.

Two things about the instrument, neither of which is a reading of the economy.

**The surfaces are read off a row rounded to six places.** Two of the four ask
for a positive value, and a positive value under half a unit in the sixth place
reads zero. At zero autonomous edges that is what decides the consuming-power
surface: the active ratio is positive at about ``1e-139`` of its opening value
and reads ``0.0``. The registered reading is the rounded one. What these tests
hold in place is that the record says so: every flag the rounding decides is
listed, with the order of magnitude of the value that read zero, and a row the
rounding does not touch lists nothing.

**The conservation identity has to reach the last settlement.** A round's
history row is written before that round's ``_post_round`` hook, which is where
the asset layer settles. A leak in any round but the last shows in the next row.
A leak in the last shows in no row, so the state the run is left in is read as
well, and a planted leak there has to fail A8-3.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import a8_coverage as a8  # noqa: E402

from monetary_topology.asset import A3Model  # noqa: E402

#: The registered length. The zero-edge reading is about where a decaying
#: ratio has got to by the tail window, so a shorter run would test a
#: different number.
ROUNDS = 600

#: Enough rounds for a leak to be planted in a round that is not the last.
SHORT = 8


def scored(row: dict) -> dict:
    row["surfaces"] = a8.surfaces_present(row)
    row["all_four"] = bool(all(row["surfaces"].values()))
    return row


def test_order_is_an_order_of_magnitude_and_refuses_zero() -> None:
    assert a8.order(1.4e-108) == -108
    assert a8.order(1.09e-151) == -151
    assert a8.order(0.5) == -1
    assert a8.order(0.0) is None
    assert a8.order(-1.0) is None


def test_the_zero_edge_is_decided_by_the_rounding_and_says_so() -> None:
    row = scored(a8.one_run(0, 0.9, ROUNDS, 0))
    assert row["mara_ratio"] == 0.0
    assert row["below_resolution"]["mara_ratio"] < -100
    assert row["surfaces"]["two"] is False
    assert row["surfaces_unrounded"]["two"] is True
    # What the zero is: circulation no longer reaches the production layer.
    assert row["layer2_reached_close"] == 0
    report = a8.rounding_report([row], [])
    assert [d["surface"] for d in report["flags_decided"]] == ["two"]
    assert report["edges_where_it_decides"] == [0]
    assert report["orders_reading_zero"]["largest"] < -100


def test_an_interior_edge_is_not_touched_by_the_rounding() -> None:
    row = scored(a8.one_run(1, 0.9, ROUNDS, 0))
    assert row["below_resolution"] == {}
    assert row["surfaces"] == row["surfaces_unrounded"]
    report = a8.rounding_report([row], [])
    assert report["flags_decided"] == []
    assert report["orders_reading_zero"] is None
    assert "no flag is decided" in " ".join(a8.rounding_lines(report))


def test_a_planted_disagreement_is_listed_whichever_way_it_runs() -> None:
    """The report compares two readings and must not assume which one is on."""
    row = scored(a8.one_run(1, 0.9, ROUNDS, 0))
    assert row["surfaces"]["four_a"] is True
    row["surfaces_unrounded"] = dict(row["surfaces_unrounded"], four_a=False)
    report = a8.rounding_report([], [row])
    assert len(report["flags_decided"]) == 1
    flag = report["flags_decided"][0]
    assert (flag["arm"], flag["surface"]) == ("seeds", "four_a")
    assert flag["at_record_resolution"] is True and flag["unrounded"] is False
    assert "both directions" in " ".join(a8.rounding_lines(report))


def test_the_flags_are_one_function_read_on_two_sets_of_values() -> None:
    """``surfaces_present`` is ``surface_flags`` on the rounded row, no more."""
    values = {
        "mr_ratio": 132.0,
        "mara_ratio": 1e-139,
        "m_ratio": 2.0,
        "gini_open": 0.5,
        "gini_close": 0.6,
        "resource_levels": 1,
        "support_ratio": 0.9,
        "wage_funding": 0.8,
        "wage_owed_ratio": 1e-108,
    }
    raw = a8.surface_flags(values)
    assert raw == {"two": True, "three": True, "four_a": True, "four_b": True}
    rounded = {k: a8.r(v) if isinstance(v, float) else v for k, v in values.items()}
    assert a8.surfaces_present(rounded) == {
        "two": False,
        "three": True,
        "four_a": True,
        "four_b": False,
    }


class _Leak(A3Model):
    """An asset carrier that gains one unit of claims after one settlement."""

    leak_round = -1

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        if t == self.leak_round:
            self.holdings[0] += 1.0


def _asset_run(leak_round: int | None) -> dict:
    carrier = a8.carrier_at(a8.BASE_NODES, asset=True)
    built = a8.build_model(1, 0.9, SHORT, 0, carrier)
    if leak_round is None:
        model = built
    else:
        model = _Leak(built.a3)
        model.leak_round = leak_round
    return scored(a8.read_run(model, model.run(), 1, 0.9, 0))


def test_a_leak_at_the_last_settlement_is_caught_at_the_close_only() -> None:
    clean = _asset_run(None)
    assert clean["claims_conserved"] and clean["claims_conserved_at_close"]

    last = _asset_run(SHORT - 1)
    # No row follows the last settlement, so the rows cannot see it.
    assert last["claims_conserved"] is True
    assert last["claims_conserved_at_close"] is False

    earlier = _asset_run(2)
    # A leak before the last round is in the next row, and stays in the books.
    assert earlier["claims_conserved"] is False
    assert earlier["claims_conserved_at_close"] is False


def test_a8_3_fails_on_a_leak_the_rows_cannot_see() -> None:
    carrier = a8.carrier_at(a8.BASE_NODES, asset=True)
    clean = _asset_run(None)
    leaked = _asset_run(SHORT - 1)

    def verdict(rows: list[dict]) -> bool:
        criteria = a8.evaluate(rows, rows, carrier)
        return next(c for c in criteria if c.name.startswith("A8-3")).passed

    assert verdict([clean]) is True
    assert verdict([clean, leaked]) is False
