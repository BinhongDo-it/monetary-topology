"""B6-16 and B6-17's surface: the order book read at the order level.

The order file itself is a 291 MB third-party checkout that nothing here
fetches, so **every test that would touch it skips with the clone command
attached** rather than passing on an absent fixture. What is tested without it
is the arithmetic, which is where a criterion can go wrong quietly.
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pytest

from monetary_topology import havana_orders as ho
from monetary_topology.cuba_segments import GuardFailed

ROOT = Path(__file__).resolve().parents[1]


def order(sign: str, price: float, volume: float = 100.0) -> dict:
    return {"sign": sign, "price": price, "volume": volume}


def day(buys: list[float], sells: list[float], junk: int = 0) -> list[dict]:
    rows = [order(ho.SIGN_BUY, p) for p in buys]
    rows += [order(ho.SIGN_SELL, p) for p in sells]
    rows += [order("", 1.0) for _ in range(junk)]
    return rows


# ---------------------------------------------------------------------------
# Sides and classification
# ---------------------------------------------------------------------------


def test_the_two_verbs_are_the_two_sides():
    assert (ho.SIGN_BUY, ho.SIGN_SELL) == ("compro", "vendo")


def test_a_side_takes_only_its_own_verb():
    buys, sells = ho.sides(day([100.0, 101.0], [110.0]))
    assert buys == [100.0, 101.0]
    assert sells == [110.0]


def test_an_unclassified_order_joins_neither_side():
    buys, sells = ho.sides(day([100.0], [110.0], junk=5))
    assert len(buys) == 1
    assert len(sells) == 1


def test_a_non_positive_price_is_dropped():
    rows = [order(ho.SIGN_BUY, 0.0), order(ho.SIGN_BUY, 100.0),
            order(ho.SIGN_SELL, -1.0), order(ho.SIGN_SELL, 110.0)]
    assert ho.sides(rows) == ([100.0], [110.0])


def test_the_classified_share_is_counted_and_not_assumed():
    rows = day([100.0], [110.0], junk=2)
    assert ho.classified_share(rows) == pytest.approx(0.5)
    assert ho.classified_share([]) == 0.0


# ---------------------------------------------------------------------------
# The daily quote
# ---------------------------------------------------------------------------


def test_the_quote_is_a_median_on_each_side():
    book = {"2022-01-01": day([100.0, 102.0, 104.0, 106.0, 108.0],
                              [110.0, 112.0, 114.0, 116.0, 118.0])}
    q = ho.daily_quotes(book)["2022-01-01"]
    assert q["bid"] == pytest.approx(104.0)
    assert q["ask"] == pytest.approx(114.0)
    assert (q["n_buy"], q["n_sell"]) == (5.0, 5.0)


def test_a_day_thin_on_either_side_is_left_out():
    thin = {"2022-01-01": day([100.0] * 4, [110.0] * 9)}
    assert ho.daily_quotes(thin) == {}
    assert ho.MIN_PER_SIDE == 5


def test_a_day_at_the_minimum_is_kept():
    ok = {"2022-01-01": day([100.0] * 5, [110.0] * 5)}
    assert set(ho.daily_quotes(ok)) == {"2022-01-01"}


# ---------------------------------------------------------------------------
# A1, and the side a miss falls on
# ---------------------------------------------------------------------------


def test_a_published_median_between_the_two_sides_satisfies_a1():
    q = {"bid": 100.0, "ask": 110.0}
    assert ho.inside(q, 105.0) is True
    assert ho.which_side(q, 105.0) == "inside"


def test_the_endpoints_count_as_inside():
    q = {"bid": 100.0, "ask": 110.0}
    assert ho.inside(q, 100.0) is True
    assert ho.inside(q, 110.0) is True


def test_a_miss_is_reported_with_the_side_it_fell_on():
    """The two sides reverse §3.4's bound in opposite directions, so a count
    without the side adds two different things together."""
    q = {"bid": 100.0, "ask": 110.0}
    assert ho.which_side(q, 120.0) == "above the ask"
    assert ho.which_side(q, 90.0) == "below the bid"
    assert ho.inside(q, 120.0) is False
    assert ho.inside(q, 90.0) is False


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------


def test_the_round_trip_is_the_log_of_ask_over_bid():
    assert ho.round_trip({"bid": 100.0, "ask": 110.0}) == pytest.approx(
        math.log(1.1)
    )


def test_a_crossed_book_gives_a_negative_round_trip_and_is_counted():
    """Medians can cross when the two sides are quoting different sizes. It is
    counted rather than clipped, because a clip would hide it."""
    report = ho.round_trip_report(
        {"a": {"bid": 110.0, "ask": 100.0}}, critical=0.05
    )
    assert report["inverted_days"] == 1
    assert report["median"] < 0


def test_the_round_trip_refuses_a_non_positive_quote():
    with pytest.raises(ValueError):
        ho.round_trip({"bid": 0.0, "ask": 110.0})


def test_the_worst_day_does_not_decide_the_verdict():
    """Ninety-nine narrow days and one very wide one, with the threshold set
    **between** the ninety-ninth percentile and the maximum. A criterion reading
    the worst day would fail here and this one passes, which is the whole reason
    ``ROUND_TRIP_PERCENTILE`` is 99 and not 100: one day's worst pair of medians
    is a statement about that day."""
    quotes = {f"d{i}": {"bid": 100.0, "ask": 101.0} for i in range(100)}
    quotes["d99"] = {"bid": 100.0, "ask": 200.0}
    report = ho.round_trip_report(quotes, critical=0.05)
    assert ho.ROUND_TRIP_PERCENTILE == 99.0
    assert report["p90"] <= report["p99"] < 0.05 < report["max"]
    assert report["passed"] is True
    assert report["days_above_the_critical_spread"] == 1


def test_a_book_wide_at_the_ninety_ninth_percentile_fails():
    """The other side of the same line: widen enough days that the percentile
    itself clears the threshold, and the verdict turns."""
    quotes = {f"d{i}": {"bid": 100.0, "ask": 120.0} for i in range(100)}
    report = ho.round_trip_report(quotes, critical=0.05)
    assert report["p99"] > 0.05
    assert report["passed"] is False


def test_a_narrow_book_clears_the_critical_spread():
    quotes = {f"d{i}": {"bid": 100.0, "ask": 100.5} for i in range(50)}
    report = ho.round_trip_report(quotes, critical=0.05)
    assert report["passed"] is True
    assert report["days_above_the_critical_spread"] == 0


def test_an_empty_set_of_quotes_raises_rather_than_reporting_nothing():
    with pytest.raises(GuardFailed):
        ho.round_trip_report({}, critical=0.05)


# ---------------------------------------------------------------------------
# The artefact guard
# ---------------------------------------------------------------------------


def test_the_span_guard_names_the_counts_it_expects():
    assert (ho.HAVANA_DAYS, ho.HAVANA_ORDERS) == (1_321, 790_705)
    assert (ho.HAVANA_START, ho.HAVANA_END) == (
        date(2021, 7, 23), date(2025, 3, 4)
    )


def test_a_different_checkout_stops_the_run():
    with pytest.raises(GuardFailed):
        ho.guard_span({"2022-01-01": [order(ho.SIGN_BUY, 100.0)]})


def test_the_missing_file_message_carries_the_clone_command():
    """"Not found" is not the useful half of that message."""
    with pytest.raises(GuardFailed) as caught:
        ho.load_orders(ROOT / "data" / "raw" / "no_such_order_file.json")
    text = str(caught.value)
    assert "git clone" in text
    assert ho.ORDERS_REPO in text
    assert ho.ORDERS_PAPER in text


# ---------------------------------------------------------------------------
# The file itself, when it is there
# ---------------------------------------------------------------------------


def test_the_shipped_file_is_the_registered_artefact():
    path = ROOT / ho.ORDERS_PATH
    if not path.exists():
        pytest.skip(
            f"the order book is not cloned. git clone --depth 1 "
            f"{ho.ORDERS_REPO}.git data/raw/havana_lob"
        )
    book = ho.load_orders(path)
    ho.guard_span(book)
    quotes = ho.daily_quotes(book)
    assert len(quotes) == ho.HAVANA_DAYS


def test_the_source_reads_the_orders_and_not_the_simulated_book():
    """Using their bid_price would import their matching model into a question
    that does not need one."""
    source = (ROOT / "src" / "monetary_topology" / "havana_orders.py").read_text(
        encoding="utf-8"
    )
    body = source.split('"""', 2)[2]
    for forbidden in ("daily_info.pickle", "lob_data", "Unpickler", "pickle."):
        assert forbidden not in body, forbidden
