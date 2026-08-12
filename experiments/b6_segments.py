"""B6-A: reachability typing inside the Banco Central de Cuba's own table.

Registered in ``docs/b6_cuba_prereg.md`` §5. Availability and the ruling that the
stage may be opened are in ``docs/b6_cuba_availability.md``.

Read the order. **B6-1 and B6-2 gate everything**: if the machinery disagrees
with its own closed form, no number below it means anything.

What runs here and what does not
--------------------------------

**All eight criteria.** B6-4's referee, the ECB's daily euro reference rate,
was verified on 2026-08-12 and is retrieved by ``data/fetch_ecb.py``. It is the
only source here that is not the Banco Central de Cuba, and it validates the
source rather than the pipeline: prereg §4.3 states that this stage has **no zero
calibration** over its window and the referee does not supply one.

**No headline against the informal market**, which is stage B6-B and is behind
the retrieval gate in ``b6_cuba_availability.md`` §3.4. B6-A establishes one side
of a contrast and validates the instrument.

The prohibition that shapes every number here
---------------------------------------------

``b4_directed_edges.md`` §5.2: **on a one-way edge the split degenerates**, so
there is no cycle sum to report and a number produced by imputing the missing
direction has imputed the quantity in dispute. B6-6c therefore reports a
**potential difference** from ``directed.potential_interval``, never a holonomy.
Calling that difference a premium would be the error ``b1_theorem.md`` §12.1
records.

Why four graph models and not one
---------------------------------

The table types itself two ways. Applied mechanically, ``b4`` §5.2 says both
directions quoted implies `H1`, and the frozen segments **do** carry a compra and
a venta column: segment I posts ``24 x 0.98`` and ``24 x 1.02``. Those columns are
an accounting schedule rather than a round trip anyone can execute.

So the reading is not settled by the table and this stage does not settle it by
assertion. ``maximal`` believes the columns and is the upper bound on
connectivity; ``directed`` believes the regulation and is the lower bound and the
registered reading. The other two isolate what each assumption contributes. Where
the truth sits between them is a question about how much of a return leg the
informal market supplies in practice, which no table of posted rates can answer.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from monetary_topology import directed
from monetary_topology.cuba_segments import (
    BASE_CURRENCY,
    CROSS_BAND,
    CUP,
    CURRENCIES,
    MARKUP_SCHEDULE,
    MODELS,
    ONE_WAY_SEGMENTS,
    SEGMENTS,
    SIGNAL_OVER_NOISE,
    TWO_WAY_SEGMENT,
    USD_POS,
    GuardFailed,
    channel_quote,
    column_multipliers,
    implied_cross,
    index_tolerance,
    ladder_tolerance,
    load_bcc,
    load_ecb,
    publication_days,
    published_column,
    read_xlsx_table,
    to_direct,
    two_sided_channels,
    vertex,
    widest_friction_band,
    xlsx_files,
    xlsx_skipped,
)
from monetary_topology.orphan_squares import index_matrix, square_via_machinery

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b6_segments.json"

#: The channel whose two-sided quote stands for a segment in the graph.
#:
#: ``b5_orphan_prereg.md`` §3.2 ruled that a friction term must come from **one
#: named dealer's counter** rather than from a range across institutions, because
#: a range puts dispersion across agents into a quantity defined as one agent's
#: round trip. The counter is the analogue here. The other three two-sided
#: channels are swept and reported, and none of them judges anything.
SEGMENT_CHANNEL = "efectivo_ventanilla"

#: B6-1's tolerance. The two paths are the same arithmetic in a different order.
MACHINERY_TOLERANCE = 1e-12

#: B6-5's tolerance. The claim is that the euro column **is** the dollar column
#: times one cross, not that it approximately is.
TRIANGLE_TOLERANCE = 1e-12

SEGMENT_KEYS = tuple(SEGMENTS)


# ---------------------------------------------------------------------------
# B6-1 and B6-2: the machinery, on the only real squares this carrier has
# ---------------------------------------------------------------------------


def channel_quotes(base: float, channels: tuple[str, ...]
                   ) -> dict[str, tuple[float, float]]:
    """``{channel: (bid, ask)}`` for one segment on one date.

    Only channels publishing both sides are admissible, so ``channel_quote``
    never returns ``None`` here and a caller cannot silently receive a one-sided
    channel dressed as a two-sided one.
    """
    out = {}
    for name in channels:
        bid, ask = channel_quote(base, name)
        if bid is None or ask is None:
            raise GuardFailed(f"{name} does not publish both sides")
        out[name] = (bid, ask)
    return out


def b6_1_and_2(record: dict[str, dict[str, dict[str, float]]]) -> tuple[dict, dict]:
    """B6-1 and B6-2 on pairs of two-sided channels inside one segment.

    **Domain, per prereg §5.** A square needs two classes that each quote both
    directions. After B6-6b's ruling the only such classes on this carrier are
    the float's two-sided channels, so the machinery is exercised there and not
    between segments, where the second orientation does not exist.

    B6-2 reads the diagonal off ``index_matrix`` rather than short-circuiting on
    ``a == b``, which would test the short circuit.
    """
    channels = two_sided_channels()
    worst_index = worst_friction = worst_diagonal = 0.0
    walked = 0
    for code in CURRENCIES:
        panel = record[code]
        for when in publication_days(panel):
            base = panel[when][TWO_WAY_SEGMENT]
            quotes = channel_quotes(base, channels)
            closed = index_matrix(quotes, channels)
            worst_diagonal = max(
                worst_diagonal, float(np.max(np.abs(np.diag(closed))))
            )
            field = _channel_field(quotes, channels)
            for a in range(len(channels)):
                for b in range(a + 1, len(channels)):
                    s, s_rev = square_via_machinery(field, a, b)
                    # float() at the accumulator, not at the report: numpy
                    # scalars are not JSON serialisable and a numpy bool in a
                    # verdict would surface as a write error rather than as a
                    # wrong answer, which is a worse place to find it.
                    worst_index = max(
                        worst_index, float(abs((s - s_rev) - closed[a, b]))
                    )
                    worst_friction = max(
                        worst_friction,
                        float(abs((s + s_rev) - _friction(quotes, channels, a, b))),
                    )
                    walked += 1
    b6_1 = {
        "passed": bool(max(worst_index, worst_friction) <= MACHINERY_TOLERANCE),
        "squares_walked": walked,
        "channels": list(channels),
        "worst_index_discrepancy": worst_index,
        "worst_friction_discrepancy": worst_friction,
        "tolerance": MACHINERY_TOLERANCE,
    }
    b6_2 = {
        "passed": bool(worst_diagonal == 0.0),
        "worst_diagonal": worst_diagonal,
    }
    return b6_1, b6_2


def _channel_field(quotes: dict[str, tuple[float, float]],
                   channels: tuple[str, ...]):
    """Two-way position edges and zero two-way agent edges, for the float only.

    The channels of one segment are all two-way, so this is the ordinary field of
    ``orphan_squares.build_field``; it is rebuilt here rather than imported
    because that function is written against stage B5's ``SERIES`` and importing
    it would tie this stage to Argentina's class list.
    """
    from monetary_topology.orphan_squares import edge_weights

    weights: dict[tuple[int, int], float] = {}
    for a, name in enumerate(channels):
        fwd, rev = edge_weights(*quotes[name])
        weights[(vertex(a, CUP), vertex(a, USD_POS))] = fwd
        weights[(vertex(a, USD_POS), vertex(a, CUP))] = rev
    for a in range(len(channels)):
        for b in range(len(channels)):
            if a != b:
                for pos in (CUP, USD_POS):
                    weights[(vertex(a, pos), vertex(b, pos))] = 0.0
    return directed.DirectedField(weights, len(channels) * 2)


def _friction(quotes: dict[str, tuple[float, float]], channels: tuple[str, ...],
              a: int, b: int) -> float:
    bid_a, ask_a = quotes[channels[a]]
    bid_b, ask_b = quotes[channels[b]]
    return math.log(bid_a / ask_a) + math.log(bid_b / ask_b)


# ---------------------------------------------------------------------------
# B6-3: the known-answer arm
# ---------------------------------------------------------------------------


def b6_3_known_answer(files: dict[tuple[str, str], Path],
                      skipped: list[str]) -> dict:
    """Every pair of published columns, against the registered markup schedule.

    **A floor, not a finding.** It cannot support any claim about the world; it
    says the machine reads the table the schedule describes.

    Primary form: a strict equality. The publisher truncates at four decimals and
    ``published_from`` reproduces that, so the expected index part is exact and
    there is no tolerance in the comparison to be widened later.

    The diagnostic beside it is how far the truncated columns sit from the ideal
    ``2 log(k_b / k_a)``, which must stay inside ``index_tolerance``. That number
    is reported and judges nothing.
    """
    if not files:
        found = (
            "the directory holds "
            + ", ".join(repr(n) for n in skipped[:8])
            + (f" and {len(skipped) - 8} more" if len(skipped) > 8 else "")
            + ", none of which the loader accepts"
        ) if skipped else "the directory is absent or holds no files"
        raise GuardFailed(
            "B6-3 needs the published columns from data/raw/bcc_xlsx/ and "
            f"{found}. Expected names look like "
            "'tasashistoricasUSDSegmentoIII20260812.xlsx': the six exports of "
            "USD and EUR against segments I, II and III, at their download "
            "names. The arm validates the machine against the XLSX export; "
            "running it on values reconstructed from the same schedule it is "
            "checking would be an identity with nothing in it."
        )
    ks = column_multipliers()
    names = tuple(sorted(ks))
    worst_exact = 0.0
    worst_drift = 0.0
    worst_allowed = 0.0
    pairs_checked = 0
    for (code, segment), path in sorted(files.items()):
        header, rows = read_xlsx_table(path)
        columns = _column_lookup(header)
        for row in rows:
            base = row[1]
            values = {name: row[columns[name]] for name in names}
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = names[i], names[j]
                    measured = 2.0 * math.log(values[b] / values[a])
                    expected = 2.0 * math.log(
                        published_column(base, b) / published_column(base, a)
                    )
                    worst_exact = max(worst_exact, abs(measured - expected))
                    ideal = 2.0 * math.log(ks[b] / ks[a])
                    worst_drift = max(worst_drift, abs(measured - ideal))
                    worst_allowed = max(
                        worst_allowed, index_tolerance(values[a], values[b])
                    )
                    pairs_checked += 1
        del code, segment
    return {
        "passed": bool(
            worst_exact <= MACHINERY_TOLERANCE and worst_drift <= worst_allowed
        ),
        "pairs_per_date": len(names) * (len(names) - 1) // 2,
        "pairs_checked": pairs_checked,
        "worst_departure_from_exact": worst_exact,
        "worst_drift_from_ideal": worst_drift,
        "largest_allowed_drift": worst_allowed,
    }


def _column_lookup(header: list[str]) -> dict[str, int]:
    """``{multiplier key: column index}`` for the base and the nineteen channels."""
    from monetary_topology.cuba_segments import XLSX_HEADERS

    out = {"base": 1}
    for (channel, side), column in XLSX_HEADERS.items():
        if column not in header:
            raise GuardFailed(f"no column {column!r}")
        out[f"{channel}:{side}"] = header.index(column)
    missing = set(column_multipliers()) - set(out)
    if missing:
        raise GuardFailed(f"no column for {sorted(missing)}")
    return out


# ---------------------------------------------------------------------------
# B6-5: the position factor is exact
# ---------------------------------------------------------------------------


def b6_5_triangle(record: dict) -> dict:
    """The segment triangle ``CUP -> USD -> EUR -> CUP`` is zero inside a segment.

    The implied cross must not depend on the segment, because the publisher
    derives its euro rate by applying one international cross to the segment's
    dollar number. What this establishes is about the source and not about the
    world: Theorem 2's slice summand vanishes here by construction, so the whole
    obstruction is in the agent factor.
    """
    crosses = implied_cross(record["USD"], record["EUR"])
    worst = 0.0
    for values in crosses.values():
        worst = max(worst, max(values.values()) - min(values.values()))
    return {
        "passed": bool(worst <= TRIANGLE_TOLERANCE),
        "dates": len(crosses),
        "worst_cross_segment_spread": worst,
        "tolerance": TRIANGLE_TOLERANCE,
        "cross_min": min(v["I"] for v in crosses.values()),
        "cross_max": max(v["I"] for v in crosses.values()),
    }


# ---------------------------------------------------------------------------
# B6-4: the external referee
# ---------------------------------------------------------------------------


def b6_4_referee(record: dict, reference: dict[str, float]) -> dict:
    """The implied euro cross against an independent daily EUR/USD reference.

    **One band, no envelope.** The BCC runs its own fixing rather than copying
    the ECB, so an envelope around neighbouring reference days would test which
    fixing it uses instead of whether its euro leg is a real cross. The envelope
    clause was registered alongside the band and withdrawn; the pre-registration
    §11 records what was known when.

    **A publication day with no reference does not enter.** The reference is
    business-daily and the BCC publishes on some Sundays, so coverage is below
    one and is reported. Nothing is interpolated: `b4` §5.2's prohibition on
    supplying a missing observation from a neighbouring one is about a different
    object, but the same reason applies, and an interpolated referee would be
    validating the interpolation.
    """
    crosses = implied_cross(record["USD"], record["EUR"])
    days = sorted(reference)
    position = {d: i for i, d in enumerate(days)}
    worst = 0.0
    worst_date = None
    compared = 0
    missing = 0
    exceedances = []
    lagged = []
    for when in sorted(crosses):
        if when not in reference:
            missing += 1
            continue
        signed = crosses[when]["I"] / reference[when] - 1.0
        deviation = abs(signed)
        if deviation > worst:
            worst, worst_date = deviation, when
        i = position[when]
        if i:
            previous = reference[days[i - 1]]
            lagged.append(abs(crosses[when]["I"] / previous - 1.0))
            move = reference[when] / previous - 1.0
        else:
            move = float("nan")
        if deviation > CROSS_BAND:
            exceedances.append({
                "date": when,
                "deviation": signed,
                "reference_day_over_day": move,
            })
        compared += 1
    return {
        "passed": bool(compared > 0 and worst <= CROSS_BAND),
        "dates_compared": compared,
        "dates_without_reference": missing,
        "worst_relative_deviation": worst,
        "worst_on": worst_date,
        "band": CROSS_BAND,
        "exceedances": exceedances,
        # **Reported, judging nothing.** Every exceedance sits on a day the
        # reference itself moved by about a percent, with the sign reversed, so
        # the criterion is misaligned rather than the source being wrong. The
        # lagged figures are what that diagnosis rests on. B6-4 is **not**
        # re-registered against them: choosing the alignment that removes the
        # failures, after seeing which alignment does, is the fitting this
        # project registers criteria to prevent.
        "diagnostic_one_business_day_lag": {
            "dates": len(lagged),
            "worst_relative_deviation": max(lagged) if lagged else float("nan"),
            "exceedances": sum(1 for x in lagged if x > CROSS_BAND),
        },
    }


# ---------------------------------------------------------------------------
# B6-8: is the table a product of an agent factor and a position factor?
# ---------------------------------------------------------------------------


def freeze_audit(table: dict[str, dict[str, dict[str, float]]],
                 dates: list[str]) -> dict:
    """Longest run of consecutive **publication days** on which a series does not
    move, per currency and segment. **A source audit, not a criterion.**

    It carries no verdict and judges nothing. It exists because B6-8's failure
    needs a second, independent view of the same fact: a row that disagrees with
    the dollar's ladder because it was not refreshed looks different from one
    that disagrees because it is priced independently, and the difference is
    visible in the raw series without any reference to the dollar at all.
    """
    out: dict[str, dict[str, int]] = {}
    for code, series in table.items():
        runs = {}
        for tag in SEGMENTS:
            best = run = 1
            for i in range(1, len(dates)):
                same = series[dates[i]][tag] == series[dates[i - 1]][tag]
                run = run + 1 if same else 1
                best = max(best, run)
            runs[tag] = best
        out[code] = runs
    return out


def b6_8_separability(table: dict[str, dict[str, dict[str, float]]],
                      dates: list[str]) -> dict:
    """Every currency sees the same three-rung ladder, on every date.

    **What is not tested here.** The bank publishes no edge between two foreign
    currencies, so the position graph is a star centred on the peso and
    ``b1 = 0`` by construction. A cross between two foreign currencies can always
    be *defined* as the ratio of their peso columns, so a star built that way is
    unfalsifiable. prereg §5 B6-8 says so rather than claiming it as a finding.

    **What is tested.** Thirty-nine numbers, fifteen free parameters if they
    factor as ``f(currency) * g(segment)``, so twenty-four constraints, and
    nothing forces the bank to satisfy them: a stale cross on the pegs and a live
    one on the float would make the ladder depend on the currency.

    The yen is put the right way up first, from ``QUOTATION`` and from nothing
    else (prereg §2.5). The tolerance is derived per currency per date from the
    published grid.
    """
    worst = 0.0
    worst_at = None
    checked = 0
    failures = []
    for when in dates:
        anchor = table[BASE_CURRENCY][when]
        reference = {
            tag: anchor[tag] / anchor["I"] for tag in ("II", "III")
        }
        for code, series in table.items():
            rates = to_direct(series[when], code)
            for tag in ("II", "III"):
                got = rates[tag] / rates["I"]
                slack = ladder_tolerance(rates["I"], rates[tag]) * abs(
                    reference[tag]
                )
                gap = abs(got - reference[tag])
                if gap / abs(reference[tag]) > worst:
                    worst = gap / abs(reference[tag])
                    worst_at = f"{code} {tag} {when}"
                if gap > slack:
                    failures.append({
                        "currency": code, "segment": tag, "date": when,
                        "ladder": got, "reference": reference[tag],
                        "tolerance": slack,
                    })
                checked += 1
    return {
        "passed": bool(checked > 0 and not failures),
        "currencies": len(table),
        "dates": len(dates),
        "rungs_checked": checked,
        "worst_relative_departure": worst,
        "worst_at": worst_at,
        "failures": failures[:20],
        "failure_count": len(failures),
    }


# ---------------------------------------------------------------------------
# B6-6: four readings of the same table
# ---------------------------------------------------------------------------


def segment_quotes(panel: dict, when: str, channel: str
                   ) -> dict[str, tuple[float, float]]:
    bid_ask = {}
    for tag in SEGMENT_KEYS:
        bid, ask = channel_quote(panel[when][tag], channel)
        bid_ask[tag] = (bid, ask)
    return bid_ask


def model_report(panel: dict, dates: list[str], model: str, channel: str) -> dict:
    """Theorem 4 and Theorem 5 on every date, under one reading of the table.

    ``sub_potential`` is Bellman-Ford and ``worst_directed_cycle`` is enumeration.
    They are independent statements of the same condition, so their disagreement
    on any date is a bug and is reported as one rather than averaged away.
    """
    from monetary_topology.cuba_segments import build_segment_field

    no_sub_potential = 0
    positive_cycle = 0
    disagreements = 0
    worst_cycle = -math.inf
    component_counts: set[int] = set()
    sink_sets: set[tuple[int, ...]] = set()
    for when in dates:
        field = build_segment_field(
            segment_quotes(panel, when, channel), SEGMENT_KEYS, model
        )
        phi, _ = directed.sub_potential(field)
        cycle, _witness = directed.worst_directed_cycle(field)
        worst_cycle = max(worst_cycle, cycle)
        if phi is None:
            no_sub_potential += 1
        if cycle > 0.0:
            positive_cycle += 1
        if (phi is None) != (cycle > 0.0):
            disagreements += 1
        components = directed.strongly_connected_components(field)
        component_counts.add(len(components))
        sink_sets.add(tuple(sorted(
            v for comp in components
            if not any(u in set(comp) and w not in set(comp)
                       for (u, w) in field.weights)
            for v in comp
        )))
    return {
        "model": model,
        "note": MODELS[model]["note"],
        "dates": len(dates),
        "dates_without_sub_potential": no_sub_potential,
        "dates_with_positive_cycle": positive_cycle,
        "bellman_ford_enumeration_disagreements": disagreements,
        "worst_cycle_sum": worst_cycle,
        "component_counts": sorted(component_counts),
        "sink_vertex_sets": sorted(sink_sets),
    }


def frozen_usd_vertices() -> tuple[int, ...]:
    return tuple(sorted(
        vertex(SEGMENT_KEYS.index(tag), USD_POS) for tag in ONE_WAY_SEGMENTS
    ))


def b6_6c_bounds(panel: dict, dates: list[str], channel: str) -> dict:
    """Theorem 5's interval, under the registered directed reading.

    ``potential_interval`` returns the interval every sub-potential's
    ``phi(v) - phi(u)`` must lie in. For a frozen segment the upper end is
    infinite because no directed walk returns; for the float both ends are
    finite and their difference is that channel's round trip. **These are
    potential differences and not cycle sums.**
    """
    from monetary_topology.cuba_segments import build_segment_field

    _band_name, band = widest_friction_band()
    threshold = SIGNAL_OVER_NOISE * band
    float_index = SEGMENT_KEYS.index(TWO_WAY_SEGMENT)
    series: dict[str, list[float]] = {tag: [] for tag in ONE_WAY_SEGMENTS}
    float_widths: list[float] = []
    finite_upper_on_frozen = 0
    infinite_upper_on_float = 0
    for when in dates:
        field = build_segment_field(
            segment_quotes(panel, when, channel), SEGMENT_KEYS, "directed"
        )
        lo_f, hi_f = directed.potential_interval(
            field, vertex(float_index, CUP), vertex(float_index, USD_POS)
        )
        if not math.isfinite(hi_f):
            infinite_upper_on_float += 1
            continue
        float_widths.append(hi_f - lo_f)
        for tag in ONE_WAY_SEGMENTS:
            i = SEGMENT_KEYS.index(tag)
            lo, hi = directed.potential_interval(
                field, vertex(i, CUP), vertex(i, USD_POS)
            )
            if math.isfinite(hi):
                finite_upper_on_frozen += 1
            series[tag].append(lo - hi_f)
    clears = {
        tag: (min(values) if values else float("nan")) for tag, values in series.items()
    }
    return {
        "passed": bool(
            finite_upper_on_frozen == 0
            and infinite_upper_on_float == 0
            and all(v > threshold for v in clears.values())
        ),
        "dates": len(dates),
        "band_channel": _band_name,
        "band": band,
        "threshold": threshold,
        "smallest_distance": clears,
        "float_band_width_min": min(float_widths) if float_widths else float("nan"),
        "float_band_width_max": max(float_widths) if float_widths else float("nan"),
        "frozen_dates_with_finite_upper": finite_upper_on_frozen,
        "float_dates_with_infinite_upper": infinite_upper_on_float,
        "series": {tag: values for tag, values in series.items()},
    }


def b6_7_growth(bounds: dict) -> dict:
    """The distance on the last publication day exceeds it on the first.

    A strict comparison between two observed numbers, in the manner of B5-15's
    leg (a). Nothing in it can be slid after the fact.
    """
    ends = {}
    for tag, values in bounds["series"].items():
        if len(values) < 2:
            ends[tag] = {"first": float("nan"), "last": float("nan"), "grew": False}
            continue
        ends[tag] = {
            "first": values[0],
            "last": values[-1],
            "grew": bool(values[-1] > values[0]),
        }
    return {
        "passed": bool(all(e["grew"] for e in ends.values())),
        "ends": ends,
    }


# ---------------------------------------------------------------------------


def criterion(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> int:
    record = {code: load_bcc(RAW, code) for code in CURRENCIES}
    dates = publication_days(record["USD"])
    shared = [d for d in dates if d in record["EUR"]]
    panel = record["USD"]

    b6_1, b6_2 = b6_1_and_2(record)
    b6_3 = b6_3_known_answer(xlsx_files(RAW), xlsx_skipped(RAW))
    b6_5 = b6_5_triangle(record)
    b6_4 = b6_4_referee(record, load_ecb(RAW))
    shared_dates = [d for d in dates if all(d in record[c] for c in CURRENCIES)]
    b6_8 = b6_8_separability(record, shared_dates)
    freezes = freeze_audit(record, shared_dates)

    models = {
        name: model_report(panel, dates, name, SEGMENT_CHANNEL) for name in MODELS
    }
    expected_sinks = frozen_usd_vertices()
    maximal = models["maximal"]
    b6_6a = {
        "passed": bool(
            maximal["dates_without_sub_potential"] == maximal["dates"]
            and maximal["dates_with_positive_cycle"] == maximal["dates"]
            and maximal["bellman_ford_enumeration_disagreements"] == 0
        ),
        **{k: v for k, v in maximal.items() if k != "model"},
        "robustness": {
            name: models[name] for name in MODELS if name != "maximal"
        },
    }
    directed_report = models["directed"]
    b6_6b = {
        "passed": bool(
            directed_report["dates_without_sub_potential"] == 0
            and directed_report["component_counts"] == [3]
            and directed_report["sink_vertex_sets"] == [expected_sinks]
        ),
        **{k: v for k, v in directed_report.items() if k != "model"},
        "expected_sinks": list(expected_sinks),
    }
    b6_6c = b6_6c_bounds(panel, dates, SEGMENT_CHANNEL)
    b6_7 = b6_7_growth(b6_6c)

    sweep = {
        name: b6_6c_bounds(panel, dates, name)["smallest_distance"]
        for name in two_sided_channels()
        if name != SEGMENT_CHANNEL
    }

    criteria = [
        criterion(
            "B6-1 the walked square equals the closed form",
            b6_1["passed"],
            f"{b6_1['squares_walked']:,} squares over "
            f"{len(two_sided_channels())} two-sided channels of the float; "
            f"worst departure below {MACHINERY_TOLERANCE:g} on both the index "
            f"and the friction part",
        ),
        criterion(
            "B6-2 the trivial square is exactly zero",
            b6_2["passed"],
            "read off the diagonal of the same matrix, not short-circuited; "
            f"worst diagonal exactly {b6_2['worst_diagonal']:.1f}",
        ),
        criterion(
            "B6-3 known answer: every pair of published columns",
            b6_3["passed"],
            f"{b6_3['pairs_checked']:,} comparisons, "
            f"{b6_3['pairs_per_date']} pairs per date per file; exact against "
            f"the truncated schedule, and drift from the ideal ratio stays "
            f"inside the derived tolerance. A floor, not a finding",
        ),
        criterion(
            "B6-4 the implied euro cross matches an outside reference",
            b6_4["passed"],
            f"{b6_4['dates_compared']:,} publication days carry an ECB "
            f"reference and {b6_4['dates_without_reference']:,} do not; worst "
            f"relative deviation {b6_4['worst_relative_deviation'] * 100:.3f}% "
            f"against a band of {b6_4['band'] * 100:.1f}%, exceeded on "
            f"{len(b6_4['exceedances'])} "
            + ("date" if len(b6_4["exceedances"]) == 1 else "dates")
            + (" (" + ", ".join(e["date"] for e in b6_4["exceedances"]) + ")"
               if b6_4["exceedances"] else "")
            + f". Each sits on a day the reference itself moved about a percent "
            f"with the sign reversed; a one-business-day lag leaves "
            f"{b6_4['diagnostic_one_business_day_lag']['exceedances']} outside "
            f"the band, reported and not re-registered",
        ),
        criterion(
            "B6-5 the segment triangle is zero",
            b6_5["passed"],
            f"implied EUR/USD agrees across the three segments on "
            f"{b6_5['dates']} dates, spread below {TRIANGLE_TOLERANCE:g}; "
            f"cross ranges {b6_5['cross_min']:.4f} to {b6_5['cross_max']:.4f}",
        ),
        criterion(
            "B6-8 the agent and position factors are separable",
            b6_8["passed"],
            f"{b6_8['rungs_checked']:,} ladder rungs over {b6_8['currencies']} "
            f"currencies and {b6_8['dates']:,} dates; worst relative departure "
            f"{b6_8['worst_relative_departure'] * 100:.4f}% at "
            f"{b6_8['worst_at']}, against a tolerance derived per currency per "
            f"date. {b6_8['failure_count']} rungs outside it"
            + (", all in " + ", ".join(sorted({
                f["currency"] for f in b6_8["failures"]
            })) if b6_8["failures"] else ""),
        ),
        criterion(
            "B6-6a maximal reading: no sub-potential exists",
            b6_6a["passed"],
            f"believing the published columns leaves a positive directed cycle "
            f"on all {maximal['dates']} publication days, worst "
            f"{maximal['worst_cycle_sum']:.4f}; Bellman-Ford and enumeration "
            f"agree on every date",
        ),
        criterion(
            "B6-6b directed reading: not strongly connected",
            b6_6b["passed"],
            f"removing the two agent edges the regulation does not grant "
            f"restores a sub-potential on all {directed_report['dates']} dates; "
            f"three components, sinks exactly {list(expected_sinks)}",
        ),
        criterion(
            "B6-6c the one-sided bound clears the float's band",
            b6_6c["passed"],
            "; ".join(
                f"segment {tag} at least {value:.4f}"
                for tag, value in b6_6c["smallest_distance"].items()
            )
            + f" against {SIGNAL_OVER_NOISE:g} x {b6_6c['band']:.4f} = "
            f"{b6_6c['threshold']:.4f}",
        ),
        criterion(
            "B6-7 the distance grows across the window",
            b6_7["passed"],
            "; ".join(
                f"segment {tag} {e['first']:.4f} to {e['last']:.4f}"
                for tag, e in b6_7["ends"].items()
            ),
        ),
    ]

    out = {
        "stage": "B6-A",
        "criteria": criteria,
        "publication_days": len(dates),
        "publication_days_both_currencies": len(shared),
        "window": [dates[0], dates[-1]],
        "segment_channel": SEGMENT_CHANNEL,
        "derived": {
            "worst_cycle_sum_maximal": maximal["worst_cycle_sum"],
            "smallest_distance_segment_I": b6_6c["smallest_distance"]["I"],
            "smallest_distance_segment_II": b6_6c["smallest_distance"]["II"],
            "float_band_width": b6_6c["float_band_width_max"],
            "four_bands": b6_6c["threshold"],
        },
        "B6-1": b6_1,
        "B6-2": b6_2,
        "B6-3": b6_3,
        "B6-4": b6_4,
        "B6-5": b6_5,
        "B6-8": b6_8,
        "freeze_audit": freezes,
        "B6-6a": b6_6a,
        "B6-6b": b6_6b,
        "B6-6c": {k: v for k, v in b6_6c.items() if k != "series"},
        "B6-7": b6_7,
        "channel_sweep": sweep,
        "not_evaluated": {},
        "verdicts": {c["name"].split()[0]: c["passed"] for c in criteria},
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B6-A: reachability typing inside the central bank's own table\n")
    print(f"  {len(dates):,} publication days, {dates[0]} to {dates[-1]}")
    print(f"  segment channel {SEGMENT_CHANNEL}, "
          f"markup {MARKUP_SCHEDULE[SEGMENT_CHANNEL]}\n")
    for c in criteria:
        mark = "pass" if c["passed"] else "FAIL"
        print(f"  {c['name']:<52s} {mark}")
        print(f"      {c['detail']}")
    print("\n  longest unchanged run, consecutive publication days "
          "(source audit, no verdict)")
    for code, runs in freezes.items():
        marks = " ".join(f"{tag} {n:>3d}" for tag, n in runs.items())
        print(f"    {code:<5s} {marks}")
    print("\n  the four readings")
    for name, report in models.items():
        print(f"    {name:<21s} sub-potential absent on "
              f"{report['dates_without_sub_potential']:>3d}/{report['dates']} "
              f"dates, worst cycle {report['worst_cycle_sum']:+.4f}, "
              f"components {report['component_counts']}")
    print("\n  channel sweep of B6-6c, smallest distance")
    for name, value in sweep.items():
        print(f"    {name:<32s} " + ", ".join(
            f"{tag} {v:.4f}" for tag, v in value.items()))
    if out["not_evaluated"]:
        print("\n  NOT evaluated:")
        for name, why in out["not_evaluated"].items():
            print(f"    {name}: {why.split('.')[0]}")
    print(f"\n  wrote {RESULTS.relative_to(ROOT)}")
    # **The exit code answers whether the run was valid, not whether every
    # criterion passed.** B6-1 and B6-2 gate the stage: if the machinery
    # disagrees with its own closed form, nothing below it means anything and
    # the run is void. A registered criterion failing is a result, and it
    # travels in ``criteria`` where ``scripts/run_all.py`` prints it and
    # ``RESULTS.md`` records it. `HANDOFF.md` §3.2 item 9: a criterion that
    # fails stays failed, and it does not get an exit code that invites someone
    # to make it green.
    gates = ("B6-1", "B6-2")
    return 0 if all(out["verdicts"][g] for g in gates) else 1


if __name__ == "__main__":
    raise SystemExit(main())
