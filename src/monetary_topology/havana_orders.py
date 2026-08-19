"""B6-16 and B6-17: the Havana order book, read at the least-assumption level.

`docs/b6c_orderbook_availability.md` is the availability check and
`docs/b6b_eltoque_prereg.md` §5 registers the two criteria. This module holds
their constants and their pure functions, and does no I/O beyond reading one
JSON file.

Why this reads the orders and not the reconstructed book
---------------------------------------------------------

The repository ships both: ``all_orders.json``, which is the classified orders,
and ``daily_info.pickle``, which is a simulated limit order book built from them
with matching and execution. **The book is not read here.**

Using ``bid_price`` and ``ask_price`` would import their matching model into a
question that does not need one. A1 asks whether elTOQUE's published median sits
between what the market was bidding and what it was asking, and the
least-assumption form of that is **the median of the day's buy prices against
the median of the day's sell prices**. Nothing has to clear for that to be
defined.

The same choice makes B6-17 conservative. Their ``bid_ask_spread`` is
touch-to-touch, which is what one small order pays; the round trip in B6-15 is an
arbitrage that walks the book, and the median-to-median distance is the wider and
more honest figure. **Wider makes B6-17 harder to pass**, which is the direction a
choice like this should err in.

What the classification does not cover
---------------------------------------

``sign`` is a verb lifted from the message. ``compro`` is a bid and ``vendo`` an
ask; 19.7% of orders carry an empty string and about 1.8% carry one of roughly
350 other tokens, so **the two criteria describe the classified 78.5% and say
so**. The unclassified fifth is not missing at random: a message whose verb the
extractor missed may be systematically different from one it caught, and nothing
inside the dataset corrects for it.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from monetary_topology.cuba_informal import median, percentile
from monetary_topology.cuba_segments import GuardFailed

# ---------------------------------------------------------------------------
# Registered constants. prereg §5, B6-16 and B6-17.
# ---------------------------------------------------------------------------

#: Where the clone lives. `data/raw/` is excluded from the repository, which is
#: where a 291 MB third-party checkout belongs and also what elTOQUE's terms
#: require of anything derived from their offers.
ORDERS_PATH = Path("data") / "raw" / "havana_lob" / "data" / "analytics" / (
    "all_orders.json"
)

#: The upstream source, recorded here so the provenance travels with the code.
ORDERS_REPO = (
    "https://github.com/lolfig/"
    "Looking-into-Informal-Currency-Markets-as-Limit-Order-Books"
)
ORDERS_PAPER = "arXiv:2503.03858"

#: The span the shipped file covers, counted rather than quoted.
HAVANA_START = date(2021, 7, 23)
HAVANA_END = date(2025, 3, 4)
HAVANA_DAYS = 1_321
HAVANA_ORDERS = 790_705

#: The two verbs that classify a side. Everything else is unclassified and is
#: counted rather than guessed at.
SIGN_BUY = "compro"
SIGN_SELL = "vendo"

#: A day needs this many orders on **each** side to carry a median. Every one of
#: the 1,321 days clears it, which is a fact about the file rather than a filter
#: the file had to survive, and it is registered anyway so that a day which
#: stopped clearing it would be dropped by a rule instead of by a judgement.
MIN_PER_SIDE = 5

#: B6-16(a). The share of overlapping days on which A1 must hold.
A1_SHARE = 0.95

#: B6-17(a). Which percentile of the measured round trip is compared against
#: B6-15's critical spread. The ninety-ninth and not the maximum, because one
#: day's worst pair of medians is a statement about that day.
ROUND_TRIP_PERCENTILE = 99.0


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_orders(path: Path = ORDERS_PATH) -> dict[str, list[dict]]:
    """``{date: [{sign, price, volume}]}``, as shipped.

    Raises with the clone command attached rather than with a bare path, because
    the file is 291 MB of somebody else's repository and "not found" is not the
    useful half of that message.
    """
    if not path.exists():
        raise GuardFailed(
            f"no order file at {path}. It is not fetched by any script in this "
            f"project; clone it with\n"
            f"    git clone --depth 1 {ORDERS_REPO}.git "
            f"data/raw/havana_lob\n"
            f"Source: {ORDERS_PAPER}. data/raw/ is excluded from this "
            f"repository and stays that way."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def sides(orders: list[dict]) -> tuple[list[float], list[float]]:
    """One day's classified buy prices and sell prices, in that order.

    A non-positive price is dropped and counted by the caller; a log is taken of
    every price that survives.
    """
    buys = [o["price"] for o in orders
            if o.get("sign") == SIGN_BUY and o.get("price", 0) > 0]
    sells = [o["price"] for o in orders
             if o.get("sign") == SIGN_SELL and o.get("price", 0) > 0]
    return buys, sells


def classified_share(orders: list[dict]) -> float:
    """What fraction of a day's orders carry one of the two verbs."""
    if not orders:
        return 0.0
    named = sum(1 for o in orders if o.get("sign") in (SIGN_BUY, SIGN_SELL))
    return named / len(orders)


def daily_quotes(book: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    """``{date: {bid, ask, n_buy, n_sell, classified}}`` for the usable days.

    ``bid`` is the median of the day's buy prices and ``ask`` the median of its
    sell prices. A day with fewer than ``MIN_PER_SIDE`` on either side is left
    out and the caller is told how many there were, because a day dropped
    silently is a day nobody knows was dropped.
    """
    out: dict[str, dict[str, float]] = {}
    for when in sorted(book):
        buys, sells = sides(book[when])
        if len(buys) < MIN_PER_SIDE or len(sells) < MIN_PER_SIDE:
            continue
        out[when] = {
            "bid": median(buys),
            "ask": median(sells),
            "n_buy": float(len(buys)),
            "n_sell": float(len(sells)),
            "classified": classified_share(book[when]),
        }
    return out


# ---------------------------------------------------------------------------
# The two statistics
# ---------------------------------------------------------------------------


def inside(quote: dict[str, float], published: float) -> bool:
    """Whether the published median lies between the two sides. A1, per day."""
    return quote["bid"] <= published <= quote["ask"]


def which_side(quote: dict[str, float], published: float) -> str:
    """Where a published median that is not inside fell, and it matters.

    A median above the ask and one below the bid reverse §3.4's bound in
    opposite directions, so a count of failures without the side is a count of
    two different things added together.
    """
    if published > quote["ask"]:
        return "above the ask"
    if published < quote["bid"]:
        return "below the bid"
    return "inside"


def round_trip(quote: dict[str, float]) -> float:
    """``log(ask / bid)``: what a full turn costs, in logs, on one day."""
    if quote["bid"] <= 0 or quote["ask"] <= 0:
        raise ValueError(f"non-positive quote {quote['bid']} {quote['ask']}")
    return math.log(quote["ask"] / quote["bid"])


def round_trip_report(quotes: dict[str, dict[str, float]],
                      critical: float) -> dict:
    """B6-17. The measured distribution against B6-15's critical spread."""
    values = [round_trip(q) for q in quotes.values()]
    if not values:
        raise GuardFailed("no usable day, so there is no distribution to report")
    top = percentile(values, ROUND_TRIP_PERCENTILE)
    return {
        "days": len(values),
        "median": median(values),
        "p90": percentile(values, 90.0),
        "p99": top,
        "max": max(values),
        "min": min(values),
        "critical_spread": critical,
        "days_above_the_critical_spread": sum(1 for v in values if v >= critical),
        "passed": bool(top < critical),
        "inverted_days": sum(1 for v in values if v < 0),
    }


def guard_span(book: dict[str, list[dict]]) -> None:
    """The file is the one this project registered against.

    Counts, not a version string: the repository carries no tag and the paper's
    814,233 is a different number from the file's 790,705, so the only thing
    that identifies the artefact is the artefact.
    """
    days = sorted(book)
    orders = sum(len(v) for v in book.values())
    if (len(days), orders) != (HAVANA_DAYS, HAVANA_ORDERS):
        raise GuardFailed(
            f"the order file has {len(days):,} days and {orders:,} orders; the "
            f"registered artefact has {HAVANA_DAYS:,} and {HAVANA_ORDERS:,}. "
            f"A different checkout is not a reason to keep going quietly."
        )
    if days[0] != HAVANA_START.isoformat() or days[-1] != HAVANA_END.isoformat():
        raise GuardFailed(
            f"the order file spans {days[0]} to {days[-1]}; the registered span "
            f"is {HAVANA_START} to {HAVANA_END}."
        )
