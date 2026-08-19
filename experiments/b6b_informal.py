"""B6-B: the informal leg, and the three things a one-sided quote can still say.

`docs/b6b_eltoque_prereg.md` is the authority. Criteria B6-9 to B6-15, continuing
B6-A's numbering rather than opening a second namespace inside one stage.

**What this file may not conclude, stated before anything it may.** elTOQUE
publishes one median per instrument, so the informal edge has an index part and
no friction part. Substituting the median into the field gives an upper bound on
every directed weight through that edge, so a cycle that is non-positive under
substitution is non-positive in truth and one that is positive is not
established. **Nothing here certifies a positive cycle through the informal
edge**, and B6-12 is the guard that keeps it that way. B6-A's positive cycle of
`3.2181` runs inside the BCC table and is untouched by this.

What is left, and it is not small:

* whether the two markets price the euro against the dollar the same way, and
  whether the disagreement decays (**B6-13**);
* whether three claims denominated in the same unit carry three different prices
  in the same market on the same day (**B6-14**);
* whether the return leg the BCC posts is one anyone transacts on (**B6-15**).

The estimator is defined on the BCC's publication days, not on calendar days.
The informal side answers every day and the official side does not, and putting
a moving quote against a stale one is `MEASUREMENT.md` failure mode 1 with the
error correlated with the level being measured. `publication_days` is B6-A's
rule and this file inherits it rather than restating it.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import date
from pathlib import Path

from monetary_topology.cuba_informal import (
    API_ALIAS,
    BLOCK_DAYS,
    CONTROL,
    CRITICAL_SPREAD,
    HAVANA_SPRING_FORWARD,
    KNOWN_ANSWERS,
    OFFER_RATIO,
    PROBE_RECORD,
    REGIME_MIN_RUN,
    REGISTERED,
    TRMI_START,
    a_statistic,
    block_medians,
    critical_offer_ratio,
    critical_spread,
    cross_quantisation,
    denoise,
    digest_tasas,
    guard_no_spread,
    guard_one_sided,
    holonomy,
    local_span_seconds,
    median,
    noise_floor,
    observed_tick,
    percentile,
    probe_is_comparable,
    regime_null,
    regime_sweep,
    regimes,
    rename_alias,
    signal_band,
    substituted_cycle,
    tasas_of,
    widest_official_round_trip,
    window_days,
    window_dispersion,
)
from monetary_topology.cuba_segments import (
    TWO_WAY_SEGMENT,
    WINDOW_START,
    GuardFailed,
    load_bcc,
    publication_days,
)
from monetary_topology.havana_orders import (
    A1_SHARE,
    ORDERS_PATH,
    daily_quotes,
    guard_span,
    inside,
    load_orders,
    round_trip_report,
    which_side,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TRMI_DIR = RAW / "eltoque"
MANIFEST = RAW / "eltoque_manifest.json"
RESULTS = ROOT / "results" / "b6b_informal.json"

#: The world price of the three control instruments, for the triangle of §4.2.
#:
#: Downloaded by hand on 2026-08-19 rather than fetched by a script, so the
#: provenance lives here and in ``data/SOURCES.md`` and the digests below are
#: the only thing standing between a swapped file and a silent wrong answer.
#: CryptoDataDownload's daily Binance spot files, newest row first, two header
#: lines, ``Date`` in ISO and ``Close`` in USDT.
CDD_FILES = {
    "BTC": RAW / "Binance_BTCUSDT_d.csv",
    "TRX": RAW / "Binance_TRXUSDT_d.csv",
    "BNB": RAW / "Binance_BNBUSDT_d.csv",
}

#: B6-15(a). Registered in prereg §5.
#:
#: B6-14(a) and (b) carry no share of this kind. A share of days is not a
#: falsifiable statement about persistence: it is a property of a mixture, and
#: the same number is produced by two clean eras and by a coin flipped every
#: morning. They are judged against a permutation null instead, which has no
#: constant to choose.
POSITIVE_SHARE = 0.95

#: The variance-ratio horizons of §4.2's estimator diagnostic. A median series
#: sits near one at every horizon and a smoothed one climbs.
VR_HORIZONS = (2, 5, 10)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def criterion(name: str, passed: bool, detail: str, *,
              void: bool = False) -> dict:
    """One criterion's cell, with the void flag the renderer reads.

    **A criterion the run could not evaluate is not a criterion the run
    failed**, and `render_results.mark_of` draws that distinction where
    `run_all.criteria_from` counts it. The flag is carried on every criterion
    rather than only on the voided one, so a reader can tell "this stage does
    not use voids" from "this criterion is not voided".
    """
    return {"name": name, "passed": bool(passed), "void": bool(void),
            "detail": detail}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_informal(raw: Path = TRMI_DIR
                  ) -> tuple[dict[str, dict[str, float]], dict[str, dict]]:
    """``({date: {code: rate}}, {date: {code: rate}})``: the span, then the rest.

    The sub-day files are excluded by the pattern, so a sensitivity window
    cannot be read as a day by accident. **The three replay windows outside the
    span share the directory and the naming**, because they are days like any
    other and the fetcher had no reason to file them apart. They are separated
    here rather than in the glob, so that B6-9 can say how many there are
    instead of a count silently coming out three too high.

    ``rename_alias`` happens here and nowhere else downstream.
    """
    everything: dict[str, dict[str, float]] = {}
    pattern = "trmi_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"
    for path in sorted(raw.glob(pattern)):
        when = path.stem[len("trmi_"):]
        payload = json.loads(path.read_text(encoding="utf-8"))
        everything[when] = rename_alias(tasas_of(payload))
    inside = {d: v for d, v in everything.items() if d >= TRMI_START.isoformat()
              and d <= max(x for x in everything if x <= "2026-12-31")}
    outside = {d: v for d, v in everything.items() if d not in inside}
    return inside, outside


def load_sensitivity(raw: Path = TRMI_DIR) -> dict[str, dict[str, float]]:
    """``{date: {code: rate}}`` for the twelve registered one-hour windows."""
    out: dict[str, dict[str, float]] = {}
    for path in sorted(raw.glob("trmi_*_12-00-00.json")):
        when = path.stem[len("trmi_"):-len("_12-00-00")]
        payload = json.loads(path.read_text(encoding="utf-8"))
        out[when] = rename_alias(tasas_of(payload))
    return out


def load_manifest(path: Path = MANIFEST) -> dict:
    if not path.exists():
        raise GuardFailed(
            f"no manifest at {path}. B6-9 reads the retrieval's own account of "
            f"itself and will not reconstruct one from the directory listing, "
            f"because a directory cannot say what was asked for."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_cdd(path: Path) -> dict[str, float]:
    """``{date: close}`` from one CryptoDataDownload daily file.

    Two header lines: a provenance URL and then the column row. Rows are newest
    first, which does not matter to a dict, and the file carries days the
    collector missed rather than days the market was shut, so **the gaps are
    real absences and are left as absences**.
    """
    text = path.read_text(encoding="utf-8")
    body = text.split("\n", 1)[1]
    out: dict[str, float] = {}
    for row in csv.DictReader(io.StringIO(body)):
        when = row["Date"][:10]
        if when in out:
            raise GuardFailed(f"{path.name}: {when} appears twice")
        out[when] = float(row["Close"])
    return out


def informal_window(informal: dict[str, dict[str, float]],
                    days: list[str]) -> list[str]:
    """The days both sides have, in order."""
    return [d for d in days if d in informal]


# ---------------------------------------------------------------------------
# The noise floor. prereg §4.3.
# ---------------------------------------------------------------------------


def quantisation_floor(informal: dict[str, dict[str, float]],
                       days: list[str], left: str, right: str) -> dict:
    """One tick from each leg of a cross, measured on the days it is used on.

    **The window matters here.** The dollar sat near 40 in 2021 and near 665 in
    2026 on the same half-peso grid, so a tick measured over the whole series
    would be a tick from a different market. It is measured on the days the
    criterion runs on.
    """
    series = {
        code: [informal[d][code] for d in days if code in informal[d]]
        for code in (left, right)
    }
    ticks = {code: observed_tick(values) for code, values in series.items()}
    levels = {code: median(values) for code, values in series.items()}
    floor = cross_quantisation(
        ticks[left], levels[left], ticks[right], levels[right]
    )
    return {
        "ticks": ticks,
        "levels": levels,
        "floor": floor,
        "gap_percentiles": {
            code: {
                str(q): percentile(
                    [b - a for a, b in zip(sorted(set(v)), sorted(set(v))[1:],
                                           strict=False) if b > a], q
                )
                for q in (10.0, 50.0)
            }
            for code, v in series.items()
        },
    }


def window_floor(informal: dict[str, dict[str, float]],
                 hourly: dict[str, dict[str, float]],
                 left: str, right: str) -> dict:
    """The instrument against itself, on twelve registered dates.

    The raw figure is a statement about a one-hour estimator, which is not the
    one any criterion uses, so ``denoise`` turns it into the full-day
    estimator's own scale. **The ratio that conversion needs is not observed**,
    and B6-13 reports the value at which its verdict would flip instead of
    leaning on the one registered here.
    """
    dates = sorted(d for d in hourly
                   if d in informal
                   and all(c in informal[d] and c in hourly[d]
                           for c in (left, right)))
    full = [informal[d][left] / informal[d][right] for d in dates]
    hour = [hourly[d][left] / hourly[d][right] for d in dates]
    raw = window_dispersion(full, hour) if dates else 0.0
    return {
        "dates": dates,
        "raw_dispersion": raw,
        "offer_ratio": OFFER_RATIO,
        "floor": denoise(raw) if raw else 0.0,
        "per_date": {
            d: round(math.log(h / f), 6)
            for d, f, h in zip(dates, full, hour, strict=True)
        },
    }


# ---------------------------------------------------------------------------
# B6-9 to B6-12: the retrieval and the typing
# ---------------------------------------------------------------------------


def b6_9_retrieval(manifest: dict, informal: dict[str, dict[str, float]]) -> dict:
    """Completeness, digests, absence, and the replay of the probe windows."""
    window_end = date.fromisoformat(manifest["window"][1])
    wanted = [d.isoformat() for d in window_days(TRMI_START, window_end)]
    missing = sorted(set(wanted) - set(informal))
    extra = sorted(d for d in informal if d not in set(wanted))

    responses = manifest["responses"]
    # **The replay pass writes a second record for a date the main pass already
    # holds**, which is the point of a replay and not a second fetch. Counting
    # both as one date seen twice reported eight duplicates on a run that had
    # none, so the replay rows are excluded here by the field only they carry.
    day_rows = [r for r in responses
                if r["date_from"].split(" ")[0] in set(wanted)
                and r["date_from"].endswith("00:00:00")
                and "replay_agrees" not in r]
    seen: dict[str, int] = {}
    for row in day_rows:
        when = row["date_from"].split(" ")[0]
        seen[when] = seen.get(when, 0) + 1
    duplicated = sorted(w for w, n in seen.items() if n > 1)
    undigested = sorted(r["date_from"] for r in responses
                        if not r.get("sha256_tasas") or not r.get("sha256_body"))

    absent = set(manifest.get("absent_days", []))
    filled = sorted(d for d in absent if informal.get(d))

    replayed = [r for r in responses if "replay_agrees" in r]
    comparable = [r for r in replayed if r.get("replay_comparable")]
    disagreeing = sorted(r["date_from"] for r in comparable
                         if not r["replay_agrees"])
    not_compared = sorted(r["date_from"] for r in replayed
                          if not r.get("replay_comparable"))

    passed = not (missing or extra or duplicated or undigested or filled
                  or disagreeing)
    return {
        "passed": bool(passed),
        "days_expected": len(wanted),
        "days_present": len(informal),
        "missing": missing[:20],
        "extra": extra[:20],
        "duplicated": duplicated,
        "without_digests": undigested,
        "absent_days": len(absent),
        "absent_days_carrying_values": filled,
        "replay_compared": len(comparable),
        "replay_disagreeing": disagreeing,
        "replay_not_compared": not_compared,
        "shortened_windows": manifest.get("shortened_windows", []),
        "short_span_days": manifest.get("short_span_days", []),
    }


def b6_10_known(informal: dict[str, dict[str, float]],
                outside: dict[str, dict[str, float]]) -> dict:
    """The three externally published values, and the domain boundary."""
    checks = {}
    for (when, api_code), expected in sorted(KNOWN_ANSWERS.items()):
        code = API_ALIAS.get(api_code, api_code)
        got = informal.get(when, {}).get(code)
        checks[f"{when} {code}"] = {
            "expected": expected, "got": got, "agrees": got == expected,
        }
    boundary = {
        "2021-01-01 served": bool(informal.get("2021-01-01")),
        "2020-12-31 empty": outside.get("2020-12-31") == {},
        "2018-01-01 empty": outside.get("2018-01-01") == {},
        "2027-06-01 empty": outside.get("2027-06-01") == {},
    }
    passed = all(c["agrees"] for c in checks.values()) and all(boundary.values())
    return {"passed": bool(passed), "checks": checks, "boundary": boundary}


def b6_11_no_spread() -> dict:
    """The informal edge has no second side, and asking raises."""
    raised = {}
    for side in ("bid", "ask"):
        try:
            guard_no_spread(side)
            raised[side] = False
        except GuardFailed:
            raised[side] = True
    # The needles are assembled rather than written, because a source read that
    # searches for a literal it contains itself always finds one. B6-A's tests
    # solved the same problem by slicing one function's body out of the file;
    # this is the cheaper half of the same idea.
    needles = ["informal_" + "bid", "informal_" + "ask", "impute_" + "spread"]
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = [n for n in needles if n in source]
    return {
        "passed": bool(all(raised.values()) and not forbidden),
        "guard_raises": raised,
        "forbidden_names_in_this_file": forbidden,
    }


def b6_12_one_sided() -> dict:
    """A positive substituted cycle is an upper bound and not a finding."""
    non_positive = substituted_cycle(-0.01)
    positive = substituted_cycle(0.05)
    zero = substituted_cycle(0.0)
    refused = False
    try:
        guard_one_sided(positive)
    except GuardFailed:
        refused = True
    allowed = True
    try:
        guard_one_sided(non_positive)
        guard_one_sided(zero)
    except GuardFailed:
        allowed = False
    return {
        "passed": bool(refused and allowed
                       and non_positive["established"]
                       and not positive["established"]),
        "non_positive_established": non_positive["established"],
        "positive_established": positive["established"],
        "positive_refused_by_guard": refused,
        "non_positive_allowed_by_guard": allowed,
        "reading": positive["reading"],
    }


# ---------------------------------------------------------------------------
# B6-13: the two markets' euro-dollar crosses
# ---------------------------------------------------------------------------


def b6_13_cross(informal: dict[str, dict[str, float]],
                bcc_usd: dict, bcc_eur: dict, days: list[str],
                floor: float, raw_dispersion: float,
                breaks: tuple[date, ...]) -> dict:
    """``h(t)`` on the publication days, in two blocks of ninety.

    The channel multiplier cancels out of a cross, so the official leg is the
    float's own two numbers and no channel is chosen here.
    """
    series: list[tuple[date, float]] = []
    for when in days:
        inf = informal.get(when, {})
        if "USD" not in inf or "EUR" not in inf:
            continue
        if when not in bcc_usd or when not in bcc_eur:
            continue
        h = holonomy(
            bcc_eur[when][TWO_WAY_SEGMENT], bcc_usd[when][TWO_WAY_SEGMENT],
            inf["EUR"], inf["USD"],
        )
        series.append((date.fromisoformat(when), h))

    band = signal_band(floor)
    report: dict[str, object] = {
        "publication_days_used": len(series),
        "days_needed_for_two_blocks": 2 * BLOCK_DAYS,
        "margin": len(series) - 2 * BLOCK_DAYS,
        "noise_floor": floor,
        "band": band,
    }
    if len(series) < 2 * BLOCK_DAYS:
        report["passed"] = False
        report["void"] = (
            f"{len(series)} publication days against {2 * BLOCK_DAYS} needed "
            f"for two disjoint blocks. The blocks are not narrowed to fit."
        )
        return report

    first, last = block_medians(series)
    report.update({
        "first_block_median_abs_h": first,
        "last_block_median_abs_h": last,
        "first_block": [series[0][0].isoformat(),
                        series[BLOCK_DAYS - 1][0].isoformat()],
        "last_block": [series[-BLOCK_DAYS][0].isoformat(),
                       series[-1][0].isoformat()],
        "a_first_block_clears_the_band": bool(first > band),
        "b_last_block_smaller": bool(last < first),
        "passed": bool(first > band and last < first),
        "critical_offer_ratio": critical_offer_ratio(raw_dispersion, first),
        "critical_offer_share_of_day": (
            1.0 / critical_offer_ratio(raw_dispersion, first)
        ),
        "h_min": min(h for _, h in series),
        "h_max": max(h for _, h in series),
        "h_median": median([h for _, h in series]),
    })

    cut = max(breaks)
    before = [(d, h) for d, h in series if d < cut]
    report["break_diagnostic"] = {
        "break": cut.isoformat(),
        "days_before": len(before),
        "median_abs_h_before_break": (
            median([abs(h) for _, h in before]) if before else None
        ),
        "median_abs_h_after_break": (
            median([abs(h) for d, h in series if d >= cut])
            if any(d >= cut for d, _ in series) else None
        ),
    }
    return report


# ---------------------------------------------------------------------------
# B6-14: three claims on the dollar
# ---------------------------------------------------------------------------


def b6_14_three_dollars(informal: dict[str, dict[str, float]],
                        window_days_list: list[str]) -> dict:
    """The dollar against MLC and against the tether, cut into regimes.

    **The share of days on which a sign holds is a statistic about a mixture.**
    Over 2021 to 2026 the dollar sits above MLC on 75% of days, and that number
    is compatible with a coin flip every morning and with two clean eras either
    side of one switch. Those are different worlds and only one of them is a
    claim about stratification, so the series is segmented first and the share
    is measured **inside** the regimes.

    A sign that were day-to-day noise would yield no regime at any minimum run
    length, so the segmentation is a test rather than a smoother.
    """
    def signed(numerator: str, denominator: str) -> list[tuple[str, int]]:
        rows = []
        for when, v in sorted(informal.items()):
            if numerator not in v or denominator not in v:
                continue
            if v[numerator] <= 0 or v[denominator] <= 0:
                continue
            x = math.log(v[numerator] / v[denominator])
            rows.append((when, 1 if x > 0 else (-1 if x < 0 else 0)))
        return rows

    report: dict[str, object] = {}
    nulls: dict[str, dict] = {}
    for label, (num, den) in {
        "USD/MLC": ("USD", "MLC"),
        "USDT_TRC20/USD": ("USDT_TRC20", "USD"),
    }.items():
        rows = signed(num, den)
        segments = regimes(rows)
        total = sum(r["length"] for r in segments)
        agree = sum(r["days_agreeing"] for r in segments)
        raw_positive = sum(1 for _, sgn in rows if sgn > 0)
        nulls[label] = regime_null(rows, REGIME_MIN_RUN)
        report[label] = {
            "days": len(rows),
            "raw_share_positive": raw_positive / len(rows) if rows else 0.0,
            "regimes": len(segments),
            "agreement_inside_regimes": agree / total if total else 0.0,
            "sweep": regime_sweep(rows),
            "null": nulls[label],
            "segments": segments,
        }

    usd_mlc_window = [
        abs(math.log(informal[d]["USD"] / informal[d]["MLC"]))
        for d in window_days_list
        if d in informal and "USD" in informal[d] and "MLC" in informal[d]
        and informal[d]["MLC"] > 0
    ]
    band = widest_official_round_trip()
    c_median = median(usd_mlc_window) if usd_mlc_window else 0.0

    latest = max(informal)
    return {
        "passed": bool(nulls["USD/MLC"]["clears_null_p99"]
                       and nulls["USDT_TRC20/USD"]["clears_null_p99"]
                       and c_median > band),
        "a_clears_null": nulls["USD/MLC"]["clears_null_p99"],
        "a_observed": nulls["USD/MLC"]["observed"],
        "a_null_p99": nulls["USD/MLC"]["null_p99"],
        "a_p_value": nulls["USD/MLC"]["p_value"],
        "b_clears_null": nulls["USDT_TRC20/USD"]["clears_null_p99"],
        "b_observed": nulls["USDT_TRC20/USD"]["observed"],
        "b_null_p99": nulls["USDT_TRC20/USD"]["null_p99"],
        "b_p_value": nulls["USDT_TRC20/USD"]["p_value"],
        "c_days_in_window": len(usd_mlc_window),
        "c_median_abs_log_usd_over_mlc": c_median,
        "c_widest_official_round_trip": band,
        "c_multiple_of_the_band": c_median / band if band else None,
        "pairs": report,
        "minimum_run_days": REGIME_MIN_RUN,
        "spread_now": {"date": latest, **informal[latest]},
    }


# ---------------------------------------------------------------------------
# B6-15: the posted return leg
# ---------------------------------------------------------------------------


def b6_15_return_leg(informal: dict[str, dict[str, float]],
                     bcc_usd: dict, days: list[str]) -> dict:
    """``a(t)``, its sign, and the informal spread the conclusion survives."""
    series = [
        (d, a_statistic(informal[d]["USD"], bcc_usd[d][TWO_WAY_SEGMENT]))
        for d in days
        if d in informal and "USD" in informal[d] and d in bcc_usd
    ]
    values = [a for _, a in series]
    if not values:
        return {"passed": False, "void": "no overlapping publication day"}
    positive = sum(1 for a in values if a > 0)
    share = positive / len(values)
    star = critical_spread(values)
    band = widest_official_round_trip()
    return {
        "passed": bool(share >= POSITIVE_SHARE and star > CRITICAL_SPREAD),
        "days": len(values),
        "a_share_positive": share,
        "a_threshold": POSITIVE_SHARE,
        "critical_spread": star,
        "critical_spread_threshold": CRITICAL_SPREAD,
        "a_min": min(values),
        "a_max": max(values),
        "a_median": median(values),
        "a_first": {"date": series[0][0], "value": series[0][1]},
        "a_last": {"date": series[-1][0], "value": series[-1][1]},
        "widest_official_round_trip_diagnostic": {
            "band": band,
            "a_median_over_band": median(values) / band,
            "note": (
                "a different channel's round trip, reported and judging "
                "nothing. The arbitrage's own cost is the informal spread, "
                "which is what critical_spread reports instead."
            ),
        },
    }


# ---------------------------------------------------------------------------
# B6-16 and B6-17: the order book, on the dollar leg
# ---------------------------------------------------------------------------


def b6_16_assumption_a1(informal: dict[str, dict[str, float]],
                        quotes: dict[str, dict[str, float]]) -> dict:
    """Whether the published median sits between the market's two sides.

    §3.3 assumes it and §3.4's bound depends on the direction. This measures it
    on the dollar leg, on every day both sources serve.
    """
    rows = [
        (when, quotes[when], informal[when]["USD"])
        for when in sorted(quotes)
        if when in informal and "USD" in informal[when]
        and informal[when]["USD"] > 0
    ]
    if not rows:
        return {"passed": False, "void": "no overlapping day"}
    held = sum(1 for _, q, m in rows if inside(q, m))
    share = held / len(rows)
    misses = [
        {"date": w, "side": which_side(q, m), "bid": q["bid"], "ask": q["ask"],
         "published": m}
        for w, q, m in rows if not inside(q, m)
    ]
    above = sum(1 for x in misses if x["side"] == "above the ask")
    below = sum(1 for x in misses if x["side"] == "below the bid")
    return {
        "passed": bool(share >= A1_SHARE),
        "days": len(rows),
        "share_inside": share,
        "threshold": A1_SHARE,
        "misses_above_the_ask": above,
        "misses_below_the_bid": below,
        "first_misses": misses[:20],
        "classified_share_median": median(
            [q["classified"] for _, q, _ in rows]
        ),
        "scope": (
            "the dollar leg only, and the classified share of it. A1 remains an "
            "assumption for the euro, MLC and tether legs, and this span ends "
            "before B6-A's window opens."
        ),
    }


def b6_17_round_trip(quotes: dict[str, dict[str, float]],
                     critical: float) -> dict:
    """The measured informal round trip against B6-15's critical spread."""
    report = round_trip_report(quotes, critical)
    report["scope"] = (
        "median-to-median rather than touch-to-touch, which is the wider of the "
        "two and the one an arbitrage that walks the book would pay."
    )
    return report


# ---------------------------------------------------------------------------
# Diagnostics. prereg §4.2. None of these judges anything.
# ---------------------------------------------------------------------------


def replay_from_disk(informal: dict[str, dict[str, float]]) -> dict:
    """Recompute the replay from the files rather than trusting the manifest.

    The manifest is written by the same run that did the fetching, so a bug in
    that run would be recorded by itself. This reads the day files B6-13 and
    B6-15 actually consume and compares them against the probe answers written
    down before any criterion existed.
    """
    checked, disagreeing, skipped = 0, [], []
    for window, expected in sorted(PROBE_RECORD.items()):
        date_from, _ = window
        when = date_from.split(" ")[0]
        if not date_from.endswith("00:00:00") or when not in informal:
            continue
        if not probe_is_comparable(window):
            skipped.append(when)
            continue
        checked += 1
        if digest_tasas(informal[when]) != digest_tasas(rename_alias(expected)):
            disagreeing.append(when)
    return {"checked": checked, "disagreeing": disagreeing, "not_compared": skipped}


def contiguous_run(informal: dict[str, dict[str, float]], code: str) -> list[str]:
    """The longest run of consecutive days on which one instrument is served.

    A variance ratio over a series with holes in it is a variance ratio of
    something else, so the diagnostic runs on the longest clean stretch and says
    how long that was.
    """
    days = sorted(d for d in informal if code in informal[d])
    best: list[str] = []
    run: list[str] = []
    previous: date | None = None
    for when in days:
        current = date.fromisoformat(when)
        if previous is not None and (current - previous).days != 1:
            run = []
        run.append(when)
        previous = current
        if len(run) > len(best):
            best = list(run)
    return best


def variance_ratio(levels: list[float], horizon: int) -> float:
    """``Var(x_t - x_{t-k}) / (k * Var(x_t - x_{t-1}))`` on log levels.

    Near one for a series whose increments are unpredictable, and above one for
    a smoothed series, because smoothing moves variance from the short horizon
    to the long one. This is the signature §2.6 needs: elTOQUE names the dollar,
    the euro and MLC as median-based and the thin currencies as exponentially
    smoothed, and does not say which the tether is.
    """
    logs = [math.log(v) for v in levels]
    one = [b - a for a, b in zip(logs, logs[1:], strict=False)]
    k = [b - a for a, b in zip(logs, logs[horizon:], strict=False)]
    if len(one) < 2 or len(k) < 2:
        raise ValueError("too short for a variance ratio")
    var_one = sum(x * x for x in one) / len(one)
    var_k = sum(x * x for x in k) / len(k)
    if var_one == 0:
        raise ValueError("no day-to-day variation to normalise by")
    return var_k / (horizon * var_one)


def ema_signature(informal: dict[str, dict[str, float]]) -> dict:
    """Variance ratios for the four registered instruments, side by side."""
    out: dict[str, dict] = {}
    for code in REGISTERED:
        run = contiguous_run(informal, code)
        levels = [informal[d][code] for d in run]
        entry: dict[str, object] = {
            "longest_clean_run": len(run),
            "from": run[0] if run else None,
            "to": run[-1] if run else None,
        }
        for horizon in VR_HORIZONS:
            try:
                entry[f"vr_{horizon}"] = variance_ratio(levels, horizon)
            except ValueError as exc:
                entry[f"vr_{horizon}"] = f"not computed: {exc}"
        out[code] = entry
    return out


def control_arm(informal: dict[str, dict[str, float]],
                world: dict[str, dict[str, float]]) -> dict:
    """The three control instruments, and the reading that fixes their units.

    **They are not prices of a coin.** ``BTC`` sat at 737.75 on 2026-08-18 while
    a bitcoin was worth 64,725 dollars, so the column cannot be pesos per
    bitcoin; it is pesos per dollar of bitcoin, quoted beside pesos per dollar of
    cash and pesos per dollar of tether. The median of ``BTC / USD`` is 0.9930
    over 2,027 overlapping days and the correlation between the daily change in
    ``BTC`` and the daily change in the world bitcoin price is -0.02.
    **The world price series is what establishes that**, and having established
    it, it enters nothing else.

    So the control coins are three more claims on a dollar rather than a placebo
    against an outside market, and what they measure is thinness: how far their
    peso rate sits from cash, and how much of its day-to-day movement is
    anything at all.
    """
    usd_days = {d: v["USD"] for d, v in informal.items() if "USD" in v}

    def steps(values: list[float]) -> float:
        logs = [math.log(v) for v in values]
        diffs = [b - a for a, b in zip(logs, logs[1:], strict=False)]
        return (sum(x * x for x in diffs) / len(diffs)) ** 0.5 if diffs else 0.0

    def correlate(xs: list[float], ys: list[float]) -> float | None:
        if len(xs) < 3:
            return None
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sx = (sum((x - mx) ** 2 for x in xs) / n) ** 0.5
        sy = (sum((y - my) ** 2 for y in ys) / n) ** 0.5
        if sx == 0 or sy == 0:
            return None
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (
            n * sx * sy
        )

    out: dict[str, dict] = {}
    for code in CONTROL:
        days = sorted(d for d in informal
                      if code in informal[d] and d in usd_days
                      and informal[d][code] > 0 and usd_days[d] > 0)
        if len(days) < 3:
            out[code] = {"days": len(days), "note": "too few days"}
            continue
        ratios = [informal[d][code] / usd_days[d] for d in days]
        coin = [informal[d][code] for d in days]
        cash = [usd_days[d] for d in days]
        entry: dict[str, object] = {
            "days": len(days),
            "from": days[0],
            "to": days[-1],
            "over_cash_median": median(ratios),
            "over_cash_p10": percentile(ratios, 10.0),
            "over_cash_p90": percentile(ratios, 90.0),
            "sd_daily_step": steps(coin),
            "sd_daily_step_cash": steps(cash),
        }
        entry["noise_multiple_of_cash"] = (
            entry["sd_daily_step"] / entry["sd_daily_step_cash"]
            if entry["sd_daily_step_cash"] else None
        )
        prices = world.get(code, {})
        both = [d for d in days if d in prices and prices[d] > 0]
        if len(both) > 3:
            dc = [math.log(informal[b][code] / informal[a][code])
                  for a, b in zip(both, both[1:], strict=False)]
            dw = [math.log(prices[b] / prices[a])
                  for a, b in zip(both, both[1:], strict=False)]
            entry["units_check"] = {
                "days": len(both),
                "corr_daily_change_against_world_price": correlate(dc, dw),
                "reading": (
                    "near zero confirms the column is pesos per dollar of the "
                    "coin rather than pesos per coin"
                ),
            }
        out[code] = entry
    return out


def membership(informal: dict[str, dict[str, float]]) -> dict:
    """When each instrument enters and leaves the served set.

    prereg §2.5: the coming and going is a measurement of how thin a leg is, and
    interpolating it would delete the measurement.
    """
    out: dict[str, dict] = {}
    for code in tuple(REGISTERED) + tuple(CONTROL):
        days = sorted(d for d in informal if code in informal[d])
        if not days:
            out[code] = {"days": 0}
            continue
        out[code] = {
            "days": len(days),
            "first": days[0],
            "last": days[-1],
            "gaps": len(days) - (
                date.fromisoformat(days[-1]).toordinal()
                - date.fromisoformat(days[0]).toordinal() + 1
            ),
        }
    return out


# ---------------------------------------------------------------------------


def main() -> int:
    informal, outside = load_informal()
    hourly = load_sensitivity()
    manifest = load_manifest()
    bcc_usd = load_bcc(RAW, "USD")
    bcc_eur = load_bcc(RAW, "EUR")

    pub = publication_days(bcc_usd)
    days = [d for d in pub if d in bcc_eur and d >= WINDOW_START.isoformat()]
    overlap = informal_window(informal, days)

    world = {}
    digests = {}
    for code, path in CDD_FILES.items():
        if path.exists():
            world[code] = load_cdd(path)
            digests[code] = sha256(path)

    quant = quantisation_floor(informal, overlap, "EUR", "USD")
    window = window_floor(informal, hourly, "EUR", "USD")
    floor = noise_floor(quant["floor"], window["floor"])

    replay = replay_from_disk(informal)
    b6_9 = b6_9_retrieval(manifest, informal)
    b6_9["independent_replay"] = replay
    b6_9["outside_the_span"] = sorted(outside)
    b6_9["passed"] = bool(b6_9["passed"] and not replay["disagreeing"])
    b6_10 = b6_10_known(informal, outside)
    b6_11 = b6_11_no_spread()
    b6_12 = b6_12_one_sided()
    b6_13 = b6_13_cross(informal, bcc_usd, bcc_eur, overlap, floor,
                        window["raw_dispersion"],
                        (date(2025, 12, 18), date(2026, 6, 18)))
    b6_14 = b6_14_three_dollars(informal, overlap)
    b6_15 = b6_15_return_leg(informal, bcc_usd, overlap)

    # B6-16 and B6-17 need a 291 MB third-party checkout that no script here
    # fetches. Absent, they are recorded as not evaluated rather than as failed:
    # a criterion nobody could run is not a criterion that lost.
    quotes: dict[str, dict[str, float]] = {}
    order_note = ""
    if ORDERS_PATH.exists():
        book = load_orders()
        guard_span(book)
        quotes = daily_quotes(book)
    else:
        order_note = (
            f"not evaluated: {ORDERS_PATH} is absent. "
            f"See docs/b6c_orderbook_availability.md for the clone command."
        )
    b6_16 = (b6_16_assumption_a1(informal, quotes) if quotes
             else {"passed": None, "void": order_note})
    b6_17 = (b6_17_round_trip(quotes, b6_15.get("critical_spread", 0.0))
             if quotes else {"passed": None, "void": order_note})

    criteria = [
        criterion(
            "B6-9 retrieval integrity",
            b6_9["passed"],
            f"{b6_9['days_present']:,} of {b6_9['days_expected']:,} days, "
            f"{b6_9['absent_days']} empty, {b6_9['replay_compared']} probe "
            f"windows compared and {len(b6_9['replay_disagreeing'])} "
            f"disagreeing; independent replay checked "
            f"{replay['checked']} with {len(replay['disagreeing'])} "
            f"disagreeing",
        ),
        criterion(
            "B6-10 the known-answer arm",
            b6_10["passed"],
            "; ".join(
                f"{k} {v['got']} against {v['expected']}"
                for k, v in b6_10["checks"].items()
            ),
        ),
        criterion(
            "B6-11 the informal edge has no friction column",
            b6_11["passed"],
            "asking for either side raises, and no reporting path names one",
        ),
        criterion(
            "B6-12 a positive substituted cycle is not a finding",
            b6_12["passed"],
            b6_12["reading"],
        ),
        criterion(
            "B6-13 the euro crosses disagree, and the disagreement decays",
            b6_13.get("passed", False),
            b6_13.get("void") or (
                f"{b6_13['publication_days_used']} publication days, margin "
                f"{b6_13['margin']}; floor {floor:.5f}, band "
                f"{b6_13['band']:.5f}; first block "
                f"{b6_13['first_block_median_abs_h']:.5f}, last block "
                f"{b6_13['last_block_median_abs_h']:.5f}; the verdict flips "
                f"only if one hour holds "
                f"{b6_13['critical_offer_share_of_day']:.0%} of a day's offers"
            ),
        ),
        criterion(
            "B6-14 three claims on the dollar, three prices",
            b6_14["passed"],
            f"USD/MLC {b6_14['pairs']['USD/MLC']['regimes']} regimes, "
            f"{b6_14['a_observed']:.1%} against a null whose 99th percentile "
            f"is {b6_14['a_null_p99']:.1%}; tether "
            f"{b6_14['pairs']['USDT_TRC20/USD']['regimes']} regimes, "
            f"{b6_14['b_observed']:.1%} against {b6_14['b_null_p99']:.1%}; "
            f"median |log(USD/MLC)| "
            f"{b6_14['c_median_abs_log_usd_over_mlc']:.4f} against a widest "
            f"official round trip of "
            f"{b6_14['c_widest_official_round_trip']:.4f}",
        ),
        criterion(
            "B6-15 the posted return leg does not clear the informal market",
            b6_15["passed"],
            b6_15.get("void") or (
                f"a(t) positive on {b6_15['a_share_positive']:.1%} of "
                f"{b6_15['days']} publication days; critical spread "
                f"{b6_15['critical_spread']:.4f} against a threshold of "
                f"{CRITICAL_SPREAD}; a runs {b6_15['a_min']:.4f} to "
                f"{b6_15['a_max']:.4f}"
            ),
        ),
    ]

    if b6_16.get("passed") is not None:
        criteria.append(criterion(
            "B6-16 assumption A1, measured on the dollar leg",
            b6_16["passed"],
            f"published median inside the book on "
            f"{b6_16['share_inside']:.1%} of {b6_16['days']:,} days; "
            f"{b6_16['misses_above_the_ask']} above the ask, "
            f"{b6_16['misses_below_the_bid']} below the bid",
        ))
    if b6_17.get("passed") is not None:
        # **Void, not failed.** The two sides of this comparison describe
        # different periods: the round trip is measured 2021-07 to 2025-03 and
        # the critical spread it is compared against is measured 2025-12 to
        # 2026-08. The order book ends before B6-A's window opens, so there is
        # no day on which both quantities exist, and no arrangement of this
        # dataset produces one. A verdict here reports which period each side
        # came from. prereg §5, B6-17.
        b6_17["void"] = True
        b6_17["void_reason"] = (
            "the round trip is measured 2021-07-23 to 2025-03-04 and the "
            "critical spread it is compared against is measured over B6-A's "
            "window from 2025-12-19. The spans do not overlap and cannot be "
            "made to: the order book ends before the window opens."
        )
        criteria.append(criterion(
            "B6-17 the informal round trip, measured",
            b6_17["passed"],
            f"VOID: {b6_17['void_reason']} The distribution stands as a "
            f"reading: median {b6_17['median']:.4f}, p90 {b6_17['p90']:.4f}, "
            f"p99 {b6_17['p99']:.4f}, max {b6_17['max']:.4f} over "
            f"{b6_17['days']:,} days",
            void=True,
        ))

    out = {
        "stage": "B6-B",
        "window": [min(informal), max(informal)],
        "informal_days": len(informal),
        "publication_days_in_window": len(overlap),
        "criteria": criteria,
        "B6-9": b6_9,
        "B6-10": b6_10,
        "B6-11": b6_11,
        "B6-12": b6_12,
        "B6-13": b6_13,
        "B6-14": b6_14,
        "B6-15": b6_15,
        "B6-16": b6_16,
        "B6-17": b6_17,
        "noise_floor": {
            "quantisation": quant,
            "window": window,
            "used": floor,
            "band": signal_band(floor),
        },
        "ema_signature": ema_signature(informal),
        "control_arm": control_arm(informal, world),
        "membership": membership(informal),
        "world_price_digests": digests,
        "spring_forward_days_in_window": [
            d.isoformat() for d in HAVANA_SPRING_FORWARD
            if d.isoformat() in set(overlap)
        ],
        "window_span_seconds": {
            d: local_span_seconds(date.fromisoformat(d))
            for d in overlap
            if local_span_seconds(date.fromisoformat(d)) != 86_399
        },
        "not_evaluated": (
            {} if quotes else {"B6-16": order_note, "B6-17": order_note}
        ),
        "verdicts": {
            c["name"].split()[0]: c["passed"]
            for c in criteria if not c.get("void")
        },
        "voided": {
            c["name"].split()[0]: c["detail"]
            for c in criteria if c.get("void")
        },
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B6-B: the informal leg, and what a one-sided quote can establish\n")
    print(f"  {len(informal):,} informal days, {min(informal)} to {max(informal)}")
    print(f"  {len(overlap)} of them are BCC publication days in B6-A's window")
    print(f"  noise floor {floor:.5f} (quantisation {quant['floor']:.5f}, "
          f"window {window['raw_dispersion']:.5f} raw -> "
          f"{window['floor']:.5f} de-noised at {OFFER_RATIO:.0f}x)\n")
    for c in criteria:
        mark = "VOID" if c.get("void") else ("pass" if c["passed"] else "FAIL")
        print(f"  {c['name']:<58s} {mark}")
        print(f"      {c['detail']}")
    print("\n  diagnostics, judging nothing")
    for code, entry in out["ema_signature"].items():
        vrs = " ".join(
            f"VR{h}={entry.get(f'vr_{h}'):.2f}"
            if isinstance(entry.get(f"vr_{h}"), float) else f"VR{h}=-"
            for h in VR_HORIZONS
        )
        print(f"    {code:<12} run {entry['longest_clean_run']:>5}d  {vrs}")
    for code, entry in out["control_arm"].items():
        if entry.get("noise_multiple_of_cash") is not None:
            units = entry.get("units_check", {})
            corr = units.get("corr_daily_change_against_world_price")
            print(f"    {code:<12} {entry['over_cash_median']:.4f}x cash, "
                  f"{entry['noise_multiple_of_cash']:.1f}x its daily noise, "
                  f"corr with world price "
                  f"{corr:+.3f}" if corr is not None else "")
    print(f"\n  wrote {RESULTS.relative_to(ROOT)}")

    gates = ("B6-9", "B6-10", "B6-11", "B6-12")
    return 0 if all(out["verdicts"][g] for g in gates) else 1


if __name__ == "__main__":
    raise SystemExit(main())
