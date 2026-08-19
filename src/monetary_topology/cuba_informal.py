"""B6-B's registered surface: the informal leg, and the rules it is read under.

``b6b_eltoque_prereg.md`` is the authority for everything in this file. Nothing
here is a preference; every constant either was measured from the instrument
before the series was fetched or is inherited from B6-A, and the docstring beside
it says which.

Why this is a separate module from ``cuba_segments``
----------------------------------------------------

``cuba_segments`` is B6-A's registered surface and it is closed. B6-B reads a
different publisher, under a different typing, with a different failure mode, and
adding it there would put a stage that has not run inside a file that fifty-odd
tests already hold in place. The dependency runs one way: this module imports
from ``cuba_segments`` and ``cuba_segments`` does not know this file exists.

The three things this instrument does that the BCC's does not
--------------------------------------------------------------

**One number per instrument, with no side.** elTOQUE pools buy and sell offers
and publishes a single median. There is no bid and no ask, so the informal edge
carries an index part and no friction part (prereg §2.1). ``guard_no_spread``
below refuses to supply one.

**The response cannot say which day it describes.** Its ``date``, ``hour``,
``minutes`` and ``seconds`` are the server clock at the moment of the request.
Three probes for three different past days returned the same ``date`` and
correctly different rates (prereg §2.3). Two consequences run through this file:
the row key comes from the request and never from the payload, and **the same day
refetched produces different bytes**, so a digest over the whole body is worth
nothing as an equality test and ``digest_tasas`` exists to give one that is
stable.

**Absence is a value.** A window the instrument cannot serve comes back with an
empty ``tasas`` object rather than with an error or with the latest figure,
measured at both ends of the domain (prereg §2.4). That is what makes a silent
fallback detectable here, and it is what replaced ``b6_cuba_prereg.md`` §10 rule
1, which asked the fetcher to compare spans that the response does not carry.

One arithmetic fact worth knowing before B6-13 runs
----------------------------------------------------

B6-13 compares two disjoint blocks of ``BLOCK_DAYS`` publication days, so it
needs at least ``2 * BLOCK_DAYS = 180`` of them inside B6-A's window. B6-A
reported 207 publication days as of 2026-08-12. **The margin is about twenty-five
days and it is not comfortable.** ``block_medians`` raises rather than silently
overlapping the blocks, because two blocks that share days would compare a
quantity against itself and still return a number.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta

from monetary_topology.cuba_segments import (
    MARKUP_SCHEDULE,
    SIGNAL_OVER_NOISE,
    WINDOW_START,
    GuardFailed,
    widest_friction_band,
)

# ---------------------------------------------------------------------------
# Registered constants. prereg §6.1.
# ---------------------------------------------------------------------------

#: The endpoint, in one place. ``b6_cuba_prereg.md`` §11 records what splitting
#: the ECB's flow from its key cost when that was learned the other way.
ENDPOINT = "https://tasas.eltoque.com/v1/trmi"

#: The published specification, kept beside the endpoint so a reader can check
#: the parameter set without finding it again.
SPEC_URL = "https://tasas.eltoque.com/static/swagger.json"

#: First day the instrument answers, **measured and not claimed**. 2018-01-01,
#: 2020-12-31 and 2027-06-01 all return an empty object; 2021-01-01 returns
#: ``{"ECU": 46.0, "USD": 40.0, "USDT_TRC20": 34.17}``. elTOQUE's own chart page
#: says the series starts on this date, which agrees, and which is not why this
#: constant has this value.
TRMI_START = date(2021, 1, 1)

#: The estimator's window, as literal strings in the API's own format.
#:
#: **This is a measurement decision, not a formatting one.** The published figure
#: is a median of the offers inside the requested window, so a different window is
#: a different statistic: on 2026-01-15 an hour at 09:00 moves MLC by 3.71% and
#: the dollar by nothing. The full day is registered because it is the window
#: that reproduces the series elTOQUE publishes to the public, checked against
#: two externally published values before this was written (prereg §3.2).
WINDOW_OPEN = "00:00:00"
WINDOW_CLOSE = "23:59:59"

#: The days the registered window cannot be used as written, and the days on
#: which it silently measures something narrower. **Both lists were forced by
#: the instrument, and one of them was forced by an error.**
#:
#: The API reads ``date_from`` and ``date_to`` as Havana wall-clock times, which
#: no documentation states. It was established by a refusal: the main pass ran
#: 310 days and then returned HTTP 400 with ``El intervalo de tiempo debe ser
#: menor a 24 horas`` on 2021-11-07, a window of ``00:00:00`` to ``23:59:59``
#: that is 23 hours 59 minutes 59 seconds on any ordinary reading. It is 25
#: hours less a second in ``America/Havana``, because the clocks go back that
#: night. **The timezone is a reading taken from an error message.**
#:
#: On a fall-back day the only window that both clears the 24-hour cap and
#: covers a full day of elapsed time is ``00:00:00`` to ``22:59:59``, which is
#: 86,399 seconds, the same as every ordinary day. Neither endpoint lands in the
#: repeated hour, so neither is ambiguous.
#:
#: **The spring-forward days are the dangerous ones and they do not error.** The
#: registered window on those spans 23 hours rather than 24, so the median is
#: taken over an hour less of offers and the response says nothing about it.
#: There is no window inside one local calendar day that fixes this. It is
#: recorded per day instead, in ``local_span_seconds``, and
#: **2026-03-08 falls inside B6-A's window** while no fall-back day does.
#:
#: Written out rather than computed at run time so the constant does not depend
#: on the host having ``tzdata`` installed. A test recomputes both lists from
#: ``zoneinfo`` and fails if they have drifted.
HAVANA_FALL_BACK = (
    date(2021, 11, 7), date(2022, 11, 6), date(2023, 11, 5),
    date(2024, 11, 3), date(2025, 11, 2),
)
HAVANA_SPRING_FORWARD = (
    date(2021, 3, 14), date(2022, 3, 13), date(2023, 3, 12),
    date(2024, 3, 10), date(2025, 3, 9), date(2026, 3, 8),
)

#: The window's real duration, in seconds, on an ordinary day, a fall-back day
#: with the shortened window, and a spring-forward day.
ORDINARY_SPAN = 86_399
SPRING_FORWARD_SPAN = 82_799

#: The second window §4.3 uses to measure the instrument's own noise. One hour in
#: the middle of the day, fixed before the fetch so that it cannot be chosen
#: afterwards to make a floor come out convenient.
SENSITIVITY_OPEN = "12:00:00"
SENSITIVITY_CLOSE = "12:59:59"

#: The instruments that enter criteria. The euro arrives under the API's own
#: code and is renamed once, in ``rename_alias`` and nowhere else.
REGISTERED = ("USD", "EUR", "MLC", "USDT_TRC20")

#: Retrieved with everything else at no marginal cost, because a request is keyed
#: on the date and not on the instrument. **These enter no criterion**; prereg
#: §4.2 registers two diagnostics for them.
CONTROL = ("BTC", "TRX", "BNB")

#: Guard 6. The one place the rename happens.
#:
#: elTOQUE's public site lists the informal instruments as USD, EUR, MLC, CAD,
#: MXN, ZELLE and CLA and uses the string ``ECU`` nowhere. The identification
#: rests on a value and a date agreeing: on 2025-09-30 the API returns
#: ``ECU = 500.0`` and elTOQUE's article of that date reports the euro reaching
#: 500 CUP for the first time. ``PROBE_RECORD`` holds that row and the test
#: pins this mapping to it.
API_ALIAS = {"ECU": "EUR"}

#: Every value seen from this instrument carries at most two decimals. Used as a
#: sanity bound on the measured tick of §4.3, **not** as the tick itself.
TRMI_ULP = 0.01

#: B6-A's channel, restated here rather than imported because it lives in
#: ``experiments/b6_segments.py`` and ``src`` does not import from
#: ``experiments``. A test asserts the two strings agree; if they ever diverge
#: the test is the thing that fails, not a reading.
SEGMENT_CHANNEL = "efectivo_ventanilla"

#: The sell multiplier of that channel, taken from the schedule rather than
#: written down, so that a revision to the schedule moves B6-15's baseline
#: instead of silently leaving it stale.
K_VENTA = MARKUP_SCHEDULE[SEGMENT_CHANNEL]["venta"]

#: B6-15(b). The largest informal round trip the standing gap must survive.
#:
#: elTOQUE's own microstructure study of this market puts market-maker spreads at
#: about 0.93% in normal conditions in July 2022, widening to 1.8% under stress.
#: Two percent sits above that publisher's own stressed figure, and the 2022
#: vintage of the estimate is why the threshold is registered above it rather
#: than at it.
CRITICAL_SPREAD = 0.02

#: B6-15(b) reads the critical spread off this percentile of ``a(t)``. A
#: percentile and not a mean, because §3.6's official rate moves in steps and a
#: mean over a stepped series is not a statement about any day.
CRITICAL_PERCENTILE = 10.0

#: B6-13's two blocks, in publication days.
BLOCK_DAYS = 90

#: Declared before the fetch, so that neither can later be presented as a
#: discovery. The first is why the stage exists; the second lands inside
#: B6-13's second block and prereg §3.5 registers the diagnostic that excludes
#: it.
BREAKS = (date(2025, 12, 18), date(2026, 6, 18))

#: The limiter, measured on this key on 2026-08-19. **Not what the
#: specification says.**
#:
#: The published document states 60 requests per minute with a 10-per-second
#: burst cap and adds that a key may carry a different quota. This key carries
#: **ten requests per 156-second window**, which is a twenty-fourth of the
#: documented rate, and the difference is nine hours against thirty-five
#: minutes on the main pass.
#:
#: Measured, not inferred. A rate probe at one request per second returned nine
#: 200s and then three 429s with ``X-RateLimit-Reset`` unmoved throughout, which
#: fixed the count at ten and put a floor of 155 seconds under the window. What
#: that could not separate is a whole window from the tail of one started by
#: earlier refusals, since a refused request still counts. So a second probe
#: waited 420 seconds, longer than any candidate window, and made one request:
#: **that request is necessarily the first of its own window**, and its
#: ``X-RateLimit-Reset`` minus the moment it was sent is the window and nothing
#: else. It read 156.
RATE_WINDOW_SECONDS = 156.0
RATE_LIMIT = 10

#: Sustained pacing, with one request per window of headroom.
#:
#: ``RATE_WINDOW_SECONDS / RATE_LIMIT`` is 15.6, and pacing at exactly that puts
#: exactly ten requests in every window, on the boundary, where one slow response
#: is enough to carry an eleventh into a window it does not belong to. Dividing
#: by nine instead leaves a request of room and costs 9% of the run.
POLITE_DELAY_SECONDS = round(RATE_WINDOW_SECONDS / (RATE_LIMIT - 1), 1)

# ---------------------------------------------------------------------------
# What had already been seen. prereg §11, and the fixture B6-9 replays against.
# ---------------------------------------------------------------------------

#: Twelve of the thirteen probe windows and what they returned, recorded before
#: any criterion was written. **The thirteenth is the over-long range**, which
#: returned HTTP 400 and no ``tasas`` object at all, so it cannot live in a table
#: of tasas objects; it is held in ``RANGE_REFUSAL`` below. prereg §11 lists all
#: thirteen windows and all fourteen requests.
#:
#: **This is a known-answer table and not a cache.** B6-9 re-requests every one of
#: these windows during the fetch and compares ``digest_tasas`` against what is
#: here. Since the response carries no echo of the date it answers for, replaying
#: windows whose answers are already written down is the only check available
#: that the fetch asked for the days it believes it asked for.
#:
#: Keys are ``(date_from, date_to)`` exactly as sent. Values are the ``tasas``
#: object exactly as returned, before ``rename_alias``.
PROBE_RECORD: dict[tuple[str, str], dict[str, float]] = {
    ("2018-01-01 00:00:00", "2018-01-01 23:59:59"): {},
    ("2020-12-31 00:00:00", "2020-12-31 23:59:59"): {},
    ("2021-01-01 00:00:00", "2021-01-01 23:59:59"): {
        "ECU": 46.0, "USD": 40.0, "USDT_TRC20": 34.17,
    },
    ("2021-01-02 00:00:00", "2021-01-02 23:59:59"): {
        "ECU": 46.25, "USD": 40.0, "USDT_TRC20": 67.08,
    },
    ("2025-06-01 00:00:00", "2025-06-01 23:59:59"): {
        "BNB": 395.0, "BTC": 393.22, "ECU": 395.0, "MLC": 265.0,
        "TRX": 108.98, "USD": 370.0, "USDT_TRC20": 405.0,
    },
    ("2025-09-30 00:00:00", "2025-09-30 23:59:59"): {
        "BNB": 360.0, "BTC": 452.91, "ECU": 500.0, "MLC": 210.0,
        "TRX": 164.52, "USD": 440.0, "USDT_TRC20": 488.0,
    },
    ("2026-01-15 00:00:00", "2026-01-15 23:59:59"): {
        "BNB": 561.11, "BTC": 468.94, "ECU": 520.0, "MLC": 400.0,
        "TRX": 156.92, "USD": 480.0, "USDT_TRC20": 545.0,
    },
    ("2026-01-15 09:00:00", "2026-01-15 09:59:59"): {
        "BNB": 561.11, "BTC": 467.26, "ECU": 511.98, "MLC": 385.16,
        "TRX": 155.32, "USD": 480.0, "USDT_TRC20": 535.09,
    },
    ("2026-01-16 00:00:00", "2026-01-16 23:59:59"): {
        "BNB": 560.0, "BTC": 468.48, "ECU": 520.0, "MLC": 407.5,
        "TRX": 158.21, "USD": 485.0, "USDT_TRC20": 550.0,
    },
    ("2026-08-11 00:00:00", "2026-08-11 23:59:59"): {
        "BTC": 735.08, "ECU": 780.0, "MLC": 460.0,
        "USD": 670.0, "USDT_TRC20": 688.34,
    },
    ("2026-08-18 00:00:00", "2026-08-18 23:59:59"): {
        "BTC": 737.75, "ECU": 770.0, "MLC": 445.17,
        "USD": 665.0, "USDT_TRC20": 688.24,
    },
    ("2027-06-01 00:00:00", "2027-06-01 23:59:59"): {},
}

#: The one probe window that may not be replayed for equality, and why.
#:
#: The 2026-08-18 probe was taken at 18:05 Havana time **on 2026-08-18**, so it
#: sampled a day that still had six hours to run. The main pass fetched the same
#: window after the day closed. The two are medians over different amounts of
#: the same day, which is the distinction ``fetch_eltoque`` already refuses to
#: blur when it stops the main pass at the last complete day, and B6-9 was
#: written to compare. Asking the two for equality compares two different
#: statistics, so B6-9 does not ask.
#:
#: **The difference is a reading, not a fault**, and it carries the same
#: signature as the hour-against-day probe of §2.2: the dollar and the euro do
#: not move at all, MLC moves +1.12% and the tether −1.83%. It is reported as a
#: second window-sensitivity observation rather than discarded.
#:
#: Every other probe window sampled a day that had already closed, so this set
#: has one member and a test asserts that no other window was taken live.
PROBE_TAKEN_LIVE = {
    ("2026-08-18 00:00:00", "2026-08-18 23:59:59"),
}


def probe_is_comparable(window: tuple[str, str]) -> bool:
    """Whether a probe window's recorded answer may be replayed for equality."""
    return window not in PROBE_TAKEN_LIVE


#: The known-answer arm of prereg §4.1: three values published outside this
#: project, on named dates, before this document was written.
KNOWN_ANSWERS: dict[tuple[str, str], float] = {
    ("2025-09-30", "ECU"): 500.0,
    ("2026-08-11", "USD"): 670.0,
    ("2021-01-01", "USD"): 40.0,
}

#: A range longer than a day is refused. Recorded because the refusal is what
#: fixes the request count at one per day and because ``b6_cuba_prereg.md`` §10
#: rule 1 assumed the opposite.
RANGE_REFUSAL = "El intervalo de tiempo debe ser menor a 24 horas"


# ---------------------------------------------------------------------------
# The request
# ---------------------------------------------------------------------------


def day_window(day: date, *, sensitivity: bool = False) -> tuple[str, str]:
    """``(date_from, date_to)`` for one day, in the API's own format.

    Ordinary days get the registered window. A fall-back day gets one hour less
    at the top, because the registered window is 25 hours long in Havana that
    night and the API refuses it. The shortened window is 86,399 seconds of
    elapsed time, which is what every ordinary day is, so the estimator's
    exposure is unchanged even though the wall-clock endpoints are not.
    """
    if sensitivity:
        return (f"{day.isoformat()} {SENSITIVITY_OPEN}",
                f"{day.isoformat()} {SENSITIVITY_CLOSE}")
    close = "22:59:59" if day in HAVANA_FALL_BACK else WINDOW_CLOSE
    return (f"{day.isoformat()} {WINDOW_OPEN}", f"{day.isoformat()} {close}")


def local_span_seconds(day: date) -> int:
    """How much elapsed time the registered window actually covers on one day.

    Recorded per day in the manifest so that the one inhomogeneous kind of day
    is visible to anything downstream rather than having to be rediscovered. A
    spring-forward day is an hour short and nothing in the response says so.
    """
    if day in HAVANA_SPRING_FORWARD:
        return SPRING_FORWARD_SPAN
    return ORDINARY_SPAN


def window_is_shortened(day: date) -> bool:
    """Whether ``day_window`` moved the closing endpoint for this day."""
    return day in HAVANA_FALL_BACK


def trmi_url(date_from: str, date_to: str) -> str:
    """The endpoint, assembled in one place.

    Spaces are percent-encoded and nothing else is, which is what the four probe
    rounds sent and what the recorded answers in ``PROBE_RECORD`` correspond to.
    A second place that built this string could drift from the first without any
    test noticing, which is the mistake ``ecb_url`` exists to prevent on the
    other arm.
    """
    return (f"{ENDPOINT}"
            f"?date_from={date_from.replace(' ', '%20')}"
            f"&date_to={date_to.replace(' ', '%20')}")


def sensitivity_days(end: date) -> list[date]:
    """The twelve registered dates for §4.3's window measurement.

    The fifteenth of each month, for twelve consecutive months ending with the
    last month that is complete at ``end``. Registered as a rule rather than as a
    list so that it cannot be nudged after the floor is seen.
    """
    year, month = end.year, end.month
    month -= 1
    if month == 0:
        year, month = year - 1, 12
    out: list[date] = []
    for _ in range(12):
        out.append(date(year, month, 15))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return sorted(out)


# ---------------------------------------------------------------------------
# The response
# ---------------------------------------------------------------------------


def tasas_of(payload: dict) -> dict[str, float]:
    """The only part of the body that carries a measurement.

    Everything else in the response is the server clock. ``KeyError`` here is the
    right failure: a body without ``tasas`` is not an empty day, it is a body
    this project does not understand, and treating the two alike is how an empty
    day gets manufactured.
    """
    return dict(payload["tasas"])


def fetched_at(payload: dict) -> str:
    """The server clock, named for what it is.

    **This is not the date the answer describes** (prereg §2.3). It is recorded
    because it is evidence about when the fetch ran, and it is named
    ``fetched_at`` so that no caller can reach for it thinking it is a key.
    """
    return (f"{payload['date']} "
            f"{payload['hour']:02d}:{payload['minutes']:02d}:"
            f"{payload['seconds']:02d}")


def is_absent(tasas: dict[str, float]) -> bool:
    """An empty object is the instrument saying it has no data for that window.

    Measured at both ends of the domain and at both ends of time, so this is a
    statement about the source rather than an interpretation of a blank.
    """
    return not tasas


def rename_alias(tasas: dict[str, float]) -> dict[str, float]:
    """Guard 6. ``ECU`` becomes ``EUR`` here and nowhere else."""
    return {API_ALIAS.get(k, k): v for k, v in tasas.items()}


def digest_tasas(tasas: dict[str, float]) -> str:
    """A digest that survives a refetch.

    ``sha256`` of the whole body does not, because the body carries the clock, so
    the same day fetched twice hashes differently. Every equality test in this
    stage that means anything runs through this function.
    """
    canonical = json.dumps(tasas, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def served(tasas: dict[str, float]) -> tuple[str, ...]:
    """The instrument set on one day, sorted.

    The set moves: three instruments on 2021-01-01, seven on 2026-01-15, five on
    2026-08-18. Recording it per day is what makes prereg §2.5's thinness reading
    possible, and it is why guard 4 forbids interpolating a missing instrument.
    """
    return tuple(sorted(tasas))


# ---------------------------------------------------------------------------
# The statistics. prereg §5.
# ---------------------------------------------------------------------------


def percentile(values: list[float], q: float) -> float:
    """Linear interpolation between order statistics, defined here on purpose.

    Written out rather than inherited so that the definition is pinned by a test
    and does not change with a library version. ``q`` is in percent.
    """
    if not values:
        raise ValueError("percentile of an empty sample")
    if not 0.0 <= q <= 100.0:
        raise ValueError(f"percentile {q} outside [0, 100]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def median(values: list[float]) -> float:
    """The 50th percentile under the definition above, for one reading of it."""
    return percentile(values, 50.0)


def a_statistic(m_usd: float, tasa_especial: float) -> float:
    """B6-15's ``a(t)``: how far the informal dollar sits above the official ask.

    ``log(m_USD) - log(tasaEspecial * K_VENTA)``. The official sell price is the
    registered channel's, so this is the excess over the price at which the
    counter will actually sell a dollar, rather than over the bank's headline
    reference.
    """
    if m_usd <= 0 or tasa_especial <= 0:
        raise ValueError(f"non-positive rate {m_usd} {tasa_especial}")
    return math.log(m_usd) - math.log(tasa_especial * K_VENTA)


def critical_spread(a_values: list[float]) -> float:
    """B6-15(b). The largest informal round trip the standing gap survives.

    The arbitrage earns ``a(t)`` less the informal round trip, which prereg §2.1
    leaves unobserved. Rather than assume a width, this reports the width at
    which the conclusion would stop holding, so a reader with their own estimate
    substitutes it and reads off the answer.
    """
    return percentile(a_values, CRITICAL_PERCENTILE)


def holonomy(bcc_eur: float, bcc_usd: float,
             inf_eur: float, inf_usd: float) -> float:
    """B6-13's ``h``: the two markets' euro-dollar crosses, differenced in logs.

    Positive means the official market prices the euro higher against the dollar
    than the informal market does, which is the sign the record carries for most
    of the window.
    """
    for name, value in (("bcc_eur", bcc_eur), ("bcc_usd", bcc_usd),
                        ("inf_eur", inf_eur), ("inf_usd", inf_usd)):
        if value <= 0:
            raise ValueError(f"non-positive {name} {value}")
    return math.log(bcc_eur / bcc_usd) - math.log(inf_eur / inf_usd)


def observed_tick(values: list[float]) -> float:
    """§4.3's first noise measurement: the grid the publisher quotes on.

    The smallest positive gap between two distinct observed values. Informal
    quotes are posted on a coarse grid and this measures its step from the series
    itself, rather than assuming ``TRMI_ULP`` is the effective resolution. The
    two are different quantities: ``TRMI_ULP`` is what the format can express and
    this is what the market actually uses.
    """
    distinct = sorted(set(values))
    if len(distinct) < 2:
        raise ValueError("a tick needs at least two distinct values")
    gaps = [b - a for a, b in zip(distinct, distinct[1:], strict=False)]
    return min(g for g in gaps if g > 0)


def cross_quantisation(tick_a: float, level_a: float,
                       tick_b: float, level_b: float) -> float:
    """One tick on each leg, propagated into ``log(a / b)``.

    Same form as ``cuba_segments.index_tolerance``: an absolute step of ``tick``
    on a value of magnitude ``level`` carries ``tick / level`` into the log, and
    the two legs add.
    """
    return tick_a / level_a + tick_b / level_b


def window_dispersion(full_day: list[float], one_hour: list[float]) -> float:
    """§4.3's second noise measurement, over the twelve registered dates.

    The ninetieth percentile of ``|log(m_1h / m_full)|``. **This overstates the
    floor**, because a one-hour median is noisier than a twenty-four hour one, so
    B6-13 becomes harder to pass rather than easier. The bias is in the
    conservative direction and it is stated in prereg §4.3 rather than left for a
    referee to find.
    """
    if len(full_day) != len(one_hour):
        raise ValueError(
            f"{len(full_day)} full-day values against {len(one_hour)} hourly"
        )
    ratios = [
        abs(math.log(h / f))
        for f, h in zip(full_day, one_hour, strict=True)
        if f > 0 and h > 0
    ]
    return percentile(ratios, 90.0)


#: How much of a day's offers a one-hour window is assumed to hold, for the
#: purpose of turning the hour-against-day dispersion into a statement about the
#: full-day estimator. **Not observed**: elTOQUE publishes no offer counts, so
#: this is the window-length ratio and nothing stronger.
OFFER_RATIO = 24.0


def denoise(dispersion: float, ratio: float = OFFER_RATIO) -> float:
    """The full-day estimator's own scale, from the hour-against-day difference.

    The one-hour median is built from about ``1/ratio`` of the day's offers, so
    if they are exchangeable within the day it carries ``ratio`` times the
    variance of the full-day median, and the full-day median is nested inside
    it. Then ``Var(m_1h - m_full) = (ratio - 1) * Var(m_full)`` and the observed
    dispersion divides by ``sqrt(ratio - 1)``.

    **The ratio is the weak part and it is not treated as known.**
    ``critical_offer_ratio`` reports the value at which a criterion using this
    would flip, which is a statement a reader can check against their own belief
    about how concentrated the trading day is, rather than a constant they have
    to accept.
    """
    if ratio <= 1.0:
        raise ValueError(f"offer ratio {ratio} leaves no degrees of freedom")
    return dispersion / math.sqrt(ratio - 1.0)


def critical_offer_ratio(dispersion: float, effect: float,
                         over_noise: float = SIGNAL_OVER_NOISE) -> float:
    """The offer ratio at which ``effect`` stops clearing the band.

    Solves ``over_noise * dispersion / sqrt(r - 1) = effect`` for ``r``. A small
    answer means the conclusion needs a badly concentrated trading day to fail,
    which is the form B6-15's critical spread takes and for the same reason.
    """
    if effect <= 0:
        raise ValueError(f"effect {effect} is not positive")
    return 1.0 + (over_noise * dispersion / effect) ** 2


def noise_floor(quantisation: float, dispersion: float) -> float:
    """The larger of the two measurements. prereg §4.3.

    ``dispersion`` is the de-noised figure from ``denoise``, not the raw
    hour-against-day number, which is a statement about a one-hour estimator and
    not about the one the criteria use.
    """
    return max(quantisation, dispersion)


#: The shortest run that counts as a regime rather than a flicker, in days.
#:
#: A month is the shortest span over which a Havana pricing order could be
#: called a regime: the MLC stores' stock cycle, the remittance cycle and the
#: BCC's own step schedule all run at that length or longer. Registered before
#: any regime was counted.
REGIME_MIN_RUN = 30


#: The permutation null of §5, B6-14. Registered before it was run.
#:
#: A share of days is not falsifiable on its own and neither is an agreement
#: measured inside regimes, because pushing ``min_run`` to one makes every run
#: its own regime and the agreement one by construction. What is falsifiable is
#: the comparison against a series with **the same marginal and no order**: the
#: observed signs shuffled. A memoryless sign that is positive three days in
#: four almost never runs thirty days one way, so the null produces one regime
#: and an agreement equal to its own marginal, and a structured series does not.
REGIME_NULL_DRAWS = 999
REGIME_NULL_SEED = 0

#: The run lengths the sweep reports. Cutting finer raises the agreement and the
#: regime count together, so both are reported at every length and neither is
#: read alone.
REGIME_SWEEP = (7, 14, 30, 60, 90)


def regimes(dated: list[tuple[str, int]],
            min_run: int = REGIME_MIN_RUN) -> list[dict]:
    """Segment a sign series into regimes, absorbing runs shorter than a month.

    **This is what turns a share into a structure.** "The sign is positive on
    75% of days" is a statement about a mixture and says nothing about whether
    the ordering is stable; "there are five regimes, each internally clean, and
    here are the switch dates" is a statement about the series' shape. A sign
    that were day-to-day noise would produce no clean regimes at any minimum run
    length, so the filter is a test and not a smoother.

    ``dated`` is ``(date, sign)`` in order, sign in ``{-1, 0, +1}``. A switch is
    recognised only when the opposite sign holds for ``min_run`` consecutive
    days; anything shorter is charged to the prevailing regime and counted as a
    day that disagrees with it.
    """
    if not dated:
        return []
    blocks: list[list[tuple[str, int]]] = [[dated[0]]]
    for row in dated[1:]:
        if row[1] == blocks[-1][-1][1]:
            blocks[-1].append(row)
        else:
            blocks.append([row])

    out: list[dict] = []
    for block in blocks:
        if out and len(block) < min_run:
            out[-1]["days"].extend(block)
            continue
        if out and out[-1]["sign"] == block[0][1]:
            out[-1]["days"].extend(block)
            continue
        out.append({"sign": block[0][1], "days": list(block)})

    report = []
    for entry in out:
        days = entry["days"]
        agree = sum(1 for _, sign in days if sign == entry["sign"])
        report.append({
            "sign": entry["sign"],
            "from": days[0][0],
            "to": days[-1][0],
            "length": len(days),
            "days_agreeing": agree,
            "internal_agreement": agree / len(days),
        })
    return report


def regime_agreement(dated: list[tuple[str, int]], min_run: int) -> float:
    """The share of days whose sign is their regime's, at one run length."""
    segments = regimes(dated, min_run)
    total = sum(r["length"] for r in segments)
    return sum(r["days_agreeing"] for r in segments) / total if total else 0.0


def regime_sweep(dated: list[tuple[str, int]],
                 lengths: tuple[int, ...] = REGIME_SWEEP) -> dict[int, dict]:
    """Regime count and agreement at each run length, reported together.

    Read either column alone and the answer is trivial: agreement rises to one
    as the length falls and the count rises with it. The pair is what says
    whether the series is few clean blocks or many short ones.
    """
    out = {}
    for length in lengths:
        segments = regimes(dated, length)
        total = sum(r["length"] for r in segments)
        agree = sum(r["days_agreeing"] for r in segments)
        out[length] = {
            "regimes": len(segments),
            "agreement": agree / total if total else 0.0,
        }
    return out


def regime_null(dated: list[tuple[str, int]], min_run: int,
                draws: int = REGIME_NULL_DRAWS,
                seed: int = REGIME_NULL_SEED) -> dict:
    """The same statistic on the same signs with the order destroyed.

    Seeded, so the record is reproducible to the byte. The dates are kept in
    place and the signs are permuted, which preserves the marginal exactly and
    removes every trace of persistence.
    """
    import random

    rng = random.Random(seed)
    signs = [sign for _, sign in dated]
    dates = [when for when, _ in dated]
    values = []
    for _ in range(draws):
        rng.shuffle(signs)
        values.append(regime_agreement(list(zip(dates, signs, strict=True)),
                                       min_run))
    observed = regime_agreement(dated, min_run)
    beaten = sum(1 for v in values if v >= observed)
    return {
        "observed": observed,
        "draws": draws,
        "null_median": percentile(values, 50.0),
        "null_p99": percentile(values, 99.0),
        "null_max": max(values),
        "draws_at_or_above_observed": beaten,
        "p_value": (beaten + 1) / (draws + 1),
        "clears_null_p99": bool(observed > percentile(values, 99.0)),
    }


def signal_band(floor: float) -> float:
    """What B6-13(a) has to clear: ``SIGNAL_OVER_NOISE`` times the floor.

    The multiplier is B6-A's, which is B3-3's and B5-6's before that. It is not
    re-chosen here.
    """
    return SIGNAL_OVER_NOISE * floor


def block_medians(dated: list[tuple[date, float]]) -> tuple[float, float]:
    """B6-13's two blocks: the median of ``|value|`` early and late.

    ``dated`` is one entry per publication day, in order. The blocks are the
    first and last ``BLOCK_DAYS`` entries and they must not overlap, which needs
    at least ``2 * BLOCK_DAYS`` publication days in the window.

    **The overlap case raises rather than returning a number.** Two blocks that
    share days compare a quantity partly against itself and still produce a
    plausible float, which is precisely the shape of failure
    ``MEASUREMENT.md`` calls a guard error.
    """
    if len(dated) < 2 * BLOCK_DAYS:
        raise GuardFailed(
            f"B6-13 needs {2 * BLOCK_DAYS} publication days for two disjoint "
            f"blocks of {BLOCK_DAYS} and the window has {len(dated)}. The "
            f"blocks are not narrowed to fit; the criterion does not run."
        )
    ordered = sorted(dated)
    first = [abs(v) for _, v in ordered[:BLOCK_DAYS]]
    last = [abs(v) for _, v in ordered[-BLOCK_DAYS:]]
    return median(first), median(last)


# ---------------------------------------------------------------------------
# The one-sided rule and the guards. prereg §3.4, §6.2.
# ---------------------------------------------------------------------------


def substituted_cycle(weight: float) -> dict[str, object]:
    """What a cycle weight computed with the median substituted in means.

    Under prereg §3.3's assumption the median lies inside the unobserved bid-ask
    interval, so substituting it gives an **upper bound** on every directed
    weight through the informal edge and therefore on the cycle. A non-positive
    result is therefore non-positive in truth. A positive result is an upper
    bound that happens to be positive, which establishes nothing.
    """
    established = bool(weight <= 0.0)
    return {
        "weight": float(weight),
        "established": established,
        "reading": (
            "non-positive under substitution, therefore non-positive in truth"
            if established else
            "positive under substitution, which is an upper bound and "
            "therefore NOT established"
        ),
    }


def guard_one_sided(verdict: dict[str, object]) -> None:
    """B6-12. A positive substituted cycle may not be recorded as a finding."""
    if not verdict["established"]:
        raise GuardFailed(
            f"cycle weight {verdict['weight']:.6f} is positive only as an upper "
            f"bound. prereg §3.4 forbids reporting it as a finding, for the "
            f"same reason b4 §5.2 forbids imputing a missing direction: the "
            f"quantity that would make it a finding is the one in dispute."
        )


def guard_no_spread(side: str) -> None:
    """B6-11. The informal edge has no second side to ask for.

    elTOQUE pools buy and sell offers and publishes one number, so a bid and an
    ask on this edge are undefined rather than missing. There is no code path
    that supplies one and this function exists so that an attempt raises with the
    reason attached instead of returning a plausible float.
    """
    raise GuardFailed(
        f"the informal edge publishes one median, so its {side} side is "
        f"undefined rather than absent. prereg §2.1 and §3.4. Use "
        f"substituted_cycle and read only the direction it establishes."
    )


def guard_row_key(requested: date, payload: dict, candidate: str) -> str:
    """Guard 1. The row key is the request, never the payload.

    The payload's ``date`` is the server clock (prereg §2.3). A fetcher that
    keyed on it would collapse two thousand rows onto one day and overwrite them
    in silence, and nothing in the body would say so.

    **The candidate key is an argument on purpose.** A guard that only returned
    the right answer would be a convenience function; a caller that had already
    reached for ``payload["date"]`` would never call it. This one is handed the
    key the caller intends to use and names the mistake when it sees it.
    """
    expected = requested.isoformat()
    if candidate == expected:
        return expected
    stamp = str(payload.get("date", ""))
    if candidate == stamp:
        raise GuardFailed(
            f"the row key {candidate!r} is the response's own date field, "
            f"which is the server clock at the moment of the request and not "
            f"the day the answer describes. The key for this row is "
            f"{expected!r}. prereg §2.3."
        )
    raise GuardFailed(
        f"row key {candidate!r} is neither the requested day {expected!r} nor "
        f"the response clock {stamp!r}."
    )


def guard_no_fill(record: dict[str, dict[str, float]],
                  absent: set[str]) -> None:
    """Guard 2. A day the instrument did not serve stays empty.

    Neither forward nor backward. B6-A's guard 2 admitted a back-fill as a
    forward-fill once, the failure it produced was diagnosed as an economic
    finding for several hours, and the retraction is in ``b6_cuba_prereg.md``
    §11. The lesson is cheap to encode and was expensive to learn.
    """
    for when in sorted(absent):
        if record.get(when):
            raise GuardFailed(
                f"{when} returned an empty object and carries "
                f"{len(record[when])} values. Neither direction of fill is "
                f"permitted; the day is absent and absence is a reading."
            )


def guard_membership(record: dict[str, dict[str, float]],
                     membership: dict[str, tuple[str, ...]]) -> None:
    """Guard 4. Every day carries an explicit served set.

    An instrument present on one day and gone the next is recorded as gone. The
    coming and going is a measurement of how thin that leg is and interpolating
    it would delete the measurement.
    """
    missing = sorted(set(record) - set(membership))
    if missing:
        raise GuardFailed(
            f"{len(missing)} days carry values with no membership record, "
            f"first {missing[0]}. prereg §2.5."
        )
    for when, tasas in record.items():
        if served(tasas) != tuple(membership[when]):
            raise GuardFailed(
                f"{when}: values {served(tasas)} against membership "
                f"{tuple(membership[when])}. One of the two was written by "
                f"something that did not read the other."
            )


def guard_verbatim(source: bytes, stored: bytes) -> None:
    """Bytes are stored as they arrived.

    ``fetch_bcc`` records a source digest and a stored digest separately because
    a modified stored file compared against a source hash gives a guard that
    cries every time. Here the two coincide by construction, so the manifest
    records one digest and this assertion carries the claim that made recording
    one enough.
    """
    if hashlib.sha256(source).hexdigest() != hashlib.sha256(stored).hexdigest():
        raise GuardFailed(
            "the stored bytes differ from what arrived. The manifest records a "
            "single body digest on the strength of this check, so a failure "
            "here invalidates every digest in it."
        )


def window_days(start: date, end: date) -> list[date]:
    """Every calendar day in the closed interval, which is the request list.

    Publication days are a BCC notion. This instrument answers for every day and
    says so with an empty object when it has nothing, so the fetcher asks for all
    of them and the emptiness is data.
    """
    if end < start:
        raise ValueError(f"end {end} before start {start}")
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def request_count(start: date, end: date) -> int:
    """What the run costs, for the dry run to print before anything is fetched."""
    return len(window_days(start, end)) + len(sensitivity_days(end)) + len(
        PROBE_RECORD
    )


def official_ask(tasa_especial: float) -> float:
    """The registered channel's sell price, for one day's ``tasaEspecial``."""
    return tasa_especial * K_VENTA


def widest_official_round_trip() -> float:
    """B6-14(c)'s yardstick, inherited from B6-A rather than re-derived."""
    return widest_friction_band()[1]


def b6a_window_start() -> date:
    """B6-A's window start, so the two stages cannot drift apart on it."""
    return WINDOW_START
