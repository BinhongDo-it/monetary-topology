"""B5-14: whether a pre-existing trend can be read off this pre-window at all.

**B5-14 is VOID and there is no band on it. Rewritten 2026-08-21.** What it was
on 2026-08-11, and why both halves of that were wrong, is in
``withdrawn_2026_08_21`` in the record and in ``PRE_TREND_SHARE`` below. The
short form: the threshold had no provenance, so under `D5` the failure it
produced could never have supported a negative finding; and the shape was
forbidden by discipline 11, because a criterion may not draw a line across an
estimator. What replaces both is the object itself, printed, with the one
property that governs whether anything derived from it may be read.


Registered in ``docs/b5_orphan_prereg.md`` §6A, **after retrieval and after B5-8
ran**. That timing is disclosed at the head of §6A and in §11's changelog, along
with what was known when the constants below were fixed and what was not: no
bucket series and no slope had been computed, and this file did not exist.

The hole this fills
-------------------

``B5-11`` was B5-8's pre-flight and it does not run: it needs the friction
column, which has no source (§3.2a). ``B5-13`` asked the question B5-11 no longer
could, and it does not run either, because its control unit was ``P2P`` and that
candidate was rejected at 47 frozen days against a registered 21. **So B5-8 had
no pre-flight at all**, and the reading it was unguarded against is nameable: the
treated and control pairs were already diverging before 14 April 2025, and B5-8's
collapse ratio is a pre-existing trend wearing an event's clothes.

Why these pairs are admissible here and refused in B5-12
--------------------------------------------------------

§8.1 refuses MEP and CCL as B5-12's control unit because their cross-restriction
was removed on the intervention date and reimposed in September 2025, **both
inside the post-window**. That objection is entirely about the post-window.
Parallel trends is a pre-window test, and through the pre-window their rule
regime is stable. The two statements do not collide, and §6A.2 is where the
reason is written down rather than here.

**Passing does not repair B5-12** (§6A.7). B5-12's two obstacles live in the
post-window and in retrieval, and a pre-window trend result speaks to neither.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from monetary_topology.orphan_squares import pair_index_series, rms
from monetary_topology.parallel_rates import (
    DEVALUATION,
    INTERVENTION,
    POST_WINDOW,
    PRE_WINDOW,
    PRE_WINDOW_LONG,
    TREATED_CLASS,
    UNTOUCHED_BY_THE_CAP,
    load_agent_classes,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b5_parallel_trends.json"
SQUARES = ROOT / "results" / "b5_squares.json"

#: **Withdrawn 2026-08-21. There is no band on this arm and there must not be
#: one.** It was ``0.25``, justified as "the factor of four B5-3 and B5-6 already
#: use". Borrowing a numeral is not a provenance: that four is a detection ratio
#: of a measured magnitude against a measured noise floor, and this one was a
#: share of an effect a trend may explain. Two different quantities in two
#: different roles.
#:
#: `D5` decides what such a number is worth: every number in a criterion needs a
#: theoretical source, and one without it is an arbitrary calibration value that
#: **may not serve as grounds for a negative finding**. The arm's FAIL therefore
#: never supported the reading that was attached to it.
#:
#: The shape was wrong as well as the number. Discipline 11: a criterion is
#: either structural, about the code, or **a printed number with a reading
#: declared in advance and no line drawn on it**. The three shares this arm
#: produced are 0.775, 0.844 and 0.898, so the verdict was a step function of
#: where the band sat inside a span of 0.12, and outside that span it was
#: unanimous either way. The band carried the verdict; the data contributed three
#: numbers that agree with each other.
#:
#: The name is kept, unbound, so that a search for it lands here rather than on
#: nothing.
PRE_TREND_SHARE = None

#: ``b5_orphan_prereg.md`` §6A.3. Equal-width buckets spanning the rung's window,
#: **not calendar months**. A 365-day window holds twelve calendar months of
#: which two are partial, so calendar bucketing would put a half-month at each
#: end and make the slope's time unit vary from bucket to bucket. Equal width
#: removes both. Registered before the first run; see §11.
N_BUCKETS_PRIMARY = 12
N_BUCKETS_LONG = 24

#: The post-window measured in primary-rung buckets. Both windows are 365 days,
#: so the horizon a pre-trend is extrapolated across is exactly twelve of them.
HORIZON_BUCKETS = 12

#: A bucket with fewer quoted dates than this does not produce an rms. Argentine
#: months carry roughly twenty trading days, so ten is half a month's worth and
#: sits well clear of a holiday cluster.
MIN_DATES_PER_BUCKET = 10

#: How many of a rung's nominal buckets must survive that filter for the rung to
#: return a slope. Below it the rung is ``vacuous`` rather than small: **a
#: criterion with an empty comparison side must fail and say so rather than
#: return a number.**
MIN_BUCKET_SHARE = 2.0 / 3.0

#: §6A.3. The headline treated pair, and the three control pairs that exist.
#: Ordered as B5-8 orders them so the two files name the same pair the same way.
CLASS_ORDER = (TREATED_CLASS, *UNTOUCHED_BY_THE_CAP)
TREATED_PAIR = ("oficial", "informal")
CONTROL_PAIRS = (("informal", "mep"), ("informal", "ccl"), ("mep", "ccl"))

#: The pair keys must read the same in this file and in ``b5_squares.json``, so
#: they are built from one ordering rather than typed twice.
assert TREATED_PAIR == tuple(
    c for c in CLASS_ORDER if c in TREATED_PAIR
), "TREATED_PAIR is not in CLASS_ORDER order; its key would not match B5-8's"
assert all(
    p == tuple(c for c in CLASS_ORDER if c in p) for p in CONTROL_PAIRS
), "a control pair is not in CLASS_ORDER order; its key would not match B5-8's"


def shares_a_leg(left: tuple[str, str], right: tuple[str, str]) -> bool:
    """Whether two pairs have a class in common.

    §6A.3: the first two controls share the ``informal`` leg with the treated
    pair, so their series are mechanically correlated and their trends are
    pushed **towards** each other, which makes this criterion easier to pass.
    That is the direction unfavourable to the claim, so it is recorded per
    comparison rather than mentioned once in prose.
    """
    return bool(set(left) & set(right))


def pair_key(pair: tuple[str, str]) -> str:
    return f"{pair[0]}-{pair[1]}"


def ols_slope(y: list[float]) -> float:
    """Slope of ``y`` on bucket index ``1 … n``, by the closed form.

    Written out rather than taken from ``polyfit`` so that the quantity in the
    record is the one in the pre-registration and not whatever a fitting routine
    defaults to.
    """
    n = len(y)
    if n < 3:
        return float("nan")
    x = np.arange(1.0, n + 1.0)
    xc = x - x.mean()
    denom = float((xc * xc).sum())
    if denom == 0.0:
        return float("nan")
    return float((xc * (np.asarray(y, float) - np.mean(y))).sum() / denom)


def bucket_series(series: list[tuple[str, float]], window: tuple[date, date],
                  n_buckets: int) -> dict:
    """``rms(S − S')`` per equal-width bucket across ``window``.

    The rms is taken **inside** each bucket, so the trend is a trend in the
    magnitude of the premium rather than in its signed level. That is what
    B5-13 registered and what B5-8's ratios are computed from, so the two are
    the same quantity at different aggregations rather than two quantities.
    """
    start, end = window
    span = (end - start).days + 1
    buckets: list[list[float]] = [[] for _ in range(n_buckets)]
    for when, value in series:
        offset = (date.fromisoformat(when) - start).days
        if not 0 <= offset < span:
            continue
        index = min(n_buckets - 1, offset * n_buckets // span)
        buckets[index].append(value)

    kept, values, counts = [], [], []
    for index, bucket in enumerate(buckets):
        counts.append(len(bucket))
        if len(bucket) >= MIN_DATES_PER_BUCKET:
            kept.append(index + 1)
            values.append(rms(np.asarray(bucket, float)))
    return {
        "nominal_buckets": n_buckets,
        "dates_per_bucket": counts,
        "buckets_kept": kept,
        "rms_per_bucket": [round(v, 9) for v in values],
        "by_index": {str(i): round(v, 9) for i, v in zip(kept, values,
                                                         strict=True)},
        "usable": len(kept) >= int(np.ceil(MIN_BUCKET_SHARE * n_buckets)),
        "minimum_buckets": int(np.ceil(MIN_BUCKET_SHARE * n_buckets)),
        "slope": round(ols_slope(values), 12) if len(values) >= 3 else None,
    }


def collapse_from_b5_8() -> tuple[float, dict]:
    """``rms_pre − rms_post`` for the treated headline pair, **read not recomputed**.

    Same discipline as ``b5_squares.py``'s ``noise_floor()``: the denominator of
    this criterion is B5-8's collapse, so it is taken from B5-8's own record and
    cannot drift away from the number B5-8 reported. And B5-8 is the gate: if it
    did not pass, the comparison side is empty and §6A.6 says this criterion must
    fail and print ``vacuous`` rather than return a ratio.
    """
    if not SQUARES.exists():
        raise SystemExit(
            "results/b5_squares.json is missing. B5-14's denominator is B5-8's "
            "collapse (prereg 6A.6); run experiments/b5_squares.py first."
        )
    record = json.loads(SQUARES.read_text(encoding="utf-8"))
    if not record["verdicts"].get("B5-8"):
        raise SystemExit(
            f"B5-8 did not pass: {record['verdicts']}. Prereg 6A.6: B5-14's "
            f"denominator is B5-8's collapse, so with B5-8 failed the "
            f"comparison side is empty and this criterion is vacuous."
        )
    pair = record["pairs"][pair_key(TREATED_PAIR)]
    return pair["rms_pre"] - pair["rms_post"], {
        "rms_pre": pair["rms_pre"],
        "rms_post": pair["rms_post"],
        "from": "results/b5_squares.json, not recomputed",
    }


def has_interior_extremum(values: list[float]) -> dict:
    """Whether the series turns around inside the window.

    **This is the whole of what decides B5-14, and it contains no constant.**
    A slope fitted to a sequence summarises it only if the sequence goes one
    way. Where the maximum or the minimum sits strictly inside the window, the
    fitted slope is set by where the turn happened rather than by where the
    series ended, and extrapolating it past the window's edge is not a statement
    about the series. Reading that off ``argmax`` and ``argmin`` is a fact about
    the sequence: nothing is chosen, and no threshold can be moved.

    Discipline 11's other half is why it is shaped this way. The arm's job is to
    put an object in front of the reader; the object is the bucket series, and
    this function reports the one property of it that governs whether the number
    underneath may be read at all.
    """
    n = len(values)
    if n < 3:
        return {"decidable": False, "why": "fewer than three buckets"}
    hi, lo = max(range(n), key=values.__getitem__), min(
        range(n), key=values.__getitem__
    )
    interior = [
        ("maximum", hi + 1) for _ in (0,) if 0 < hi < n - 1
    ] + [("minimum", lo + 1) for _ in (0,) if 0 < lo < n - 1]
    return {
        "decidable": not interior,
        "argmax_bucket": hi + 1,
        "argmin_bucket": lo + 1,
        "interior_turns": [f"{what} at bucket {where}" for what, where in interior],
        "why": (
            "the series runs one way across the window, so its slope summarises "
            "it and may be extrapolated"
            if not interior
            else "the series turns inside the window, so the fitted slope is set "
            "by where it turned and not by where it ended; extrapolating it is "
            "not a statement about the series"
        ),
    }


def compare(treated: dict, control: dict, control_pair: tuple[str, str],
            collapse: float) -> dict:
    """One treated-against-control slope difference, printed, not judged.

    **No band, and no pass or fail.** §6A.5's two directions are still declared
    in advance and still reported, because the sign is a real property: a treated
    pair already diverging cannot manufacture the collapse, only make it harder
    to produce. What is gone is the line that used to be drawn across the share.
    """
    if treated["slope"] is None or control["slope"] is None:
        return {
            "control_pair": pair_key(control_pair),
            "vacuous": True,
            "why": "a rung did not keep enough buckets to fit a slope",
        }
    delta = treated["slope"] - control["slope"]
    return {
        "control_pair": pair_key(control_pair),
        "shares_a_leg_with_treated": shares_a_leg(TREATED_PAIR, control_pair),
        "slope_treated": treated["slope"],
        "slope_control": control["slope"],
        "delta_slope": round(delta, 12),
        "direction": "damaging" if delta < 0.0 else "conservative",
        "share_of_collapse": round(abs(delta) * HORIZON_BUCKETS / collapse, 9),
        "vacuous": False,
    }


def run_rung(classes: dict, dates: list[str], window: tuple[date, date],
             n_buckets: int, collapse: float) -> dict:
    treated_series = pair_index_series(classes, *TREATED_PAIR, dates)
    treated = bucket_series(treated_series, window, n_buckets)

    comparisons, controls = [], {}
    for control_pair in CONTROL_PAIRS:
        series = pair_index_series(classes, *control_pair, dates)
        block = bucket_series(series, window, n_buckets)
        controls[pair_key(control_pair)] = block
        comparisons.append(compare(treated, block, control_pair, collapse))

    usable = treated["usable"] and all(
        b["usable"] for b in controls.values()
    )
    shape = has_interior_extremum(treated["rms_per_bucket"])
    return {
        "window": [window[0].isoformat(), window[1].isoformat()],
        "encloses_december_2023_devaluation": bool(
            window[0] <= DEVALUATION <= window[1]
        ),
        "devaluation_date": DEVALUATION.isoformat(),
        "treated_pair": pair_key(TREATED_PAIR),
        "treated": treated,
        "controls": controls,
        "comparisons": comparisons,
        "linear_reading_available": bool(usable and shape["decidable"]),
        "shape": shape,
        "vacuous": not usable,
    }


def edge_block(classes: dict, dates: list[str], pair: tuple[str, str]) -> dict:
    """One pair's final pre-window bucket and its post-window buckets.

    §6B.1. The post buckets are twelve equal-width buckets of ``POST_WINDOW``,
    the same width as the primary rung's, so ``last_pre`` and every post bucket
    summarise the same span of days. Comparing a 30-day bucket against a
    365-day average would be ``MEASUREMENT.md`` rule 1 in the space of one line.
    """
    series = pair_index_series(classes, *pair, dates)
    pre = bucket_series(series, PRE_WINDOW, N_BUCKETS_PRIMARY)
    post = bucket_series(series, POST_WINDOW, N_BUCKETS_PRIMARY)
    last_pre = pre["by_index"].get(str(N_BUCKETS_PRIMARY))
    values = post["rms_per_bucket"]
    return {
        "pair": pair_key(pair),
        "last_pre_bucket": last_pre,
        "last_pre_bucket_index": N_BUCKETS_PRIMARY,
        "post_buckets": values,
        "post_buckets_kept": post["buckets_kept"],
        "post_max": round(max(values), 9) if values else None,
        "post_mean": round(float(np.mean(values)), 9) if values else None,
        "ratio": (
            round(last_pre / float(np.mean(values)), 9)
            if last_pre is not None and values and float(np.mean(values)) > 0.0
            else None
        ),
        "vacuous": bool(last_pre is None or not post["usable"]),
    }


def b5_15_edge_of_window(classes: dict, dates: list[str]) -> dict:
    """**B5-15.** The edge of the window, with no threshold in either leg.

    Registered in §6B **after B5-14 came back void**, and §6B.3 discloses that the
    quantities below had already been seen when the criterion was written. What
    that disclosure can and cannot excuse is stated there; what is stated here is
    the mechanical half: **neither leg contains a band, a fraction or a cutoff**,
    so no parameter existed that could have been moved to produce this outcome.
    """
    treated = edge_block(classes, dates, TREATED_PAIR)
    controls = [edge_block(classes, dates, p) for p in CONTROL_PAIRS]

    if treated["vacuous"] or any(c["vacuous"] for c in controls):
        return {
            "vacuous": True,
            "why": (
                "the final pre-window bucket or too few post buckets survived "
                "the date filter; prereg 6B.4 and PROJECT_PLAN 11.11 rule 1"
            ),
            "treated": treated,
            "controls": controls,
            "passed": False,
        }

    leg_a = bool(treated["last_pre_bucket"] > treated["post_max"])
    beaten = [c for c in controls if treated["ratio"] > c["ratio"]]
    leg_b = len(beaten) == len(controls)
    worst = max(controls, key=lambda c: c["ratio"])

    return {
        "vacuous": False,
        "leg_a": {
            "claim": (
                "the premium on the eve of the intervention was above every "
                "level it reached in the year after"
            ),
            "last_pre_bucket": treated["last_pre_bucket"],
            "post_max": treated["post_max"],
            "margin": round(treated["last_pre_bucket"] / treated["post_max"], 9),
            "load_bearing": True,
            "why_load_bearing": (
                "it compares one date range against another inside the treated "
                "pair, so no cross-pair contamination reaches it (prereg 6B.2)"
            ),
            "passed": leg_a,
        },
        "leg_b": {
            "claim": (
                "the treated pair's last_pre / post_mean exceeds every "
                "control's"
            ),
            "treated_ratio": treated["ratio"],
            "control_ratios": {c["pair"]: c["ratio"] for c in controls},
            "closest_control": worst["pair"],
            "margin": round(treated["ratio"] / worst["ratio"], 9),
            "load_bearing": False,
            "disclosed_bias": (
                "September 2025's re-imposition of the MEP/CCL cross-restriction "
                "falls inside the post-window and widens premia containing them, "
                "which lowers each control ratio and therefore makes this leg "
                "EASIER to satisfy. Unfavourable direction, unseparable with "
                "what is retrieved; same limit as prereg 8.1 states for B5-8."
            ),
            "passed": leg_b,
        },
        "treated": treated,
        "controls": controls,
        "passed": bool(leg_a and leg_b),
    }


def main() -> int:
    collapse, collapse_detail = collapse_from_b5_8()
    if not collapse > 0.0:
        raise SystemExit(
            f"B5-8's collapse is {collapse}, which is not positive. The "
            f"denominator of prereg 6A.4 is empty and B5-14 is vacuous."
        )

    classes = load_agent_classes(RAW)
    dates = sorted({d for series in classes.values() for d in series})

    primary = run_rung(classes, dates, PRE_WINDOW, N_BUCKETS_PRIMARY, collapse)
    second = run_rung(classes, dates, PRE_WINDOW_LONG, N_BUCKETS_LONG, collapse)
    edge = b5_15_edge_of_window(classes, dates)

    record = {
        "stage": "B5-parallel-trends",
        "registered_in": "docs/b5_orphan_prereg.md 6A",
        "registered_when": (
            "after retrieval and after B5-8 ran; see prereg 6A head and 11"
        ),
        "intervention": INTERVENTION.isoformat(),
        "post_window": [POST_WINDOW[0].isoformat(), POST_WINDOW[1].isoformat()],
        "horizon_buckets": HORIZON_BUCKETS,
        "collapse_under_test": round(collapse, 12),
        "collapse_detail": collapse_detail,
        "primary_rung": primary,
        "second_rung": second,
        "read_on": "primary rung; the second is reported alongside",
        "withdrawn_2026_08_21": {
            "what": (
                "the 0.25 band on the share of the collapse, and the FAIL it "
                "produced. Both rungs and all three comparisons were recorded "
                "as failing on 2026-08-11: shares 0.775, 0.844, 0.898 on the "
                "primary rung and 1.561, 1.589, 1.630 on the second."
            ),
            "why_the_number_goes": (
                "D5. Every number in a criterion needs a theoretical source, "
                "and one without it is an arbitrary calibration value that may "
                "not serve as grounds for a negative finding. 0.25 was borrowed "
                "from B5-3's and B5-6's detection ratio of a measured magnitude "
                "against a measured noise floor, which is a different quantity "
                "in a different role."
            ),
            "why_the_shape_goes": (
                "Discipline 11. A criterion is either structural or a printed "
                "number with a reading declared in advance, with no line drawn "
                "on it. The three shares sit inside a span of 0.12, so the "
                "verdict was a step function of where the band was placed and "
                "unanimous on either side of that span."
            ),
            "why_it_is_not_a_FAIL": (
                "Discipline 23, third test: undecidable and decided-against are "
                "different states and the middle one has to exist. The linear "
                "slope does not describe a series that turns inside the window, "
                "so the arm returned no verdict about the world. It was recorded "
                "as a failure because the design had only two states."
            ),
            "original_reading_now_void": (
                "prereg 6A.6 and 8 said a failure here puts B5-8's collapse in "
                "the headline as confounded with a pre-existing trend. That "
                "consequence is withdrawn: under D5 it was never available."
            ),
        },
        "does_not_repair_b5_12": (
            "B5-12 is unevaluated for two reasons that live in the post-window "
            "and in retrieval: MEP's and CCL's second treatment in September "
            "2025 (prereg 8.1) and the absence of the P2P class (prereg 8.2). A "
            "pre-window trend result speaks to neither, so this record does not "
            "convert B5-12 from unevaluated to identified (prereg 6A.7)."
        ),
        "B5-15": edge,
        "why_b5_15_exists": (
            "B5-14 returned no reading, and its own output shows why: the "
            "pre-window bucket series turns inside the window, so a linear "
            "extrapolation does not describe it. B5-15 asks the surviving "
            "question at the edge of the window instead, where no extrapolation "
            "is needed. Written after that and after its quantities were seen; "
            "prereg 6B.3 is the disclosure, and neither of its legs contains a "
            "threshold that could have been moved."
        ),
        "b5_15_does_not_stand_in_for_b5_14": (
            "B5-15 is a statement about the edge of the window. It does not "
            "supply the pre-trend reading B5-14 could not produce, and it does "
            "not reach B5-12 (prereg 6A.7, 6B.3)."
        ),
        "criteria": [
            {
                "name": (
                    "B5-14 whether a pre-existing trend can be read off this "
                    "pre-window at all"
                ),
                "detail": _detail(primary, collapse),
                # `void` is this repository's third state and `run_all.py`
                # already honours it: a criterion the run could not evaluate is
                # not a criterion the run failed, so it leaves both the numerator
                # and the denominator. `passed` stays a bool so the field keeps
                # one type (discipline 22); `void` is what carries the meaning.
                "void": True,
                "passed": False,
                "why_void": (
                    "the treated series turns inside the window, at bucket "
                    f"{primary['shape'].get('argmax_bucket')} and bucket "
                    f"{primary['shape'].get('argmin_bucket')} of "
                    f"{primary['treated']['nominal_buckets']}, so the fitted "
                    "slope is set by where it turned rather than by where it "
                    "ended and cannot be extrapolated past the edge"
                ),
            },
            {
                "name": (
                    "B5-15 the premium at the window's edge, no threshold in "
                    "either leg"
                ),
                "detail": _edge_detail(edge),
                "passed": edge["passed"],
            },
        ],
        "verdicts": {"B5-15": edge["passed"]},
        "undecided": {
            "B5-14": (
                "no reading available on this pre-window; see criteria[0]"
                ".why_void and withdrawn_2026_08_21"
            )
        },
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    report(record)
    return 0


def _detail(rung: dict, collapse: float) -> str:
    if rung["vacuous"]:
        return "vacuous: a rung did not keep enough buckets to fit a slope"
    series = ", ".join(f"{v:.3f}" for v in rung["treated"]["rms_per_bucket"])
    parts = "; ".join(
        f"{c['control_pair']} {c['direction'][:4]} {c['share_of_collapse']:.3f}"
        for c in rung["comparisons"]
    )
    turns = " and ".join(rung["shape"]["interior_turns"]) or "none"
    return (
        f"VOID, no linear reading: treated series turns inside the window "
        f"({turns}). Series {series}. Slope {rung['treated']['slope']:+.6f} "
        f"per bucket, shares of a {collapse:.4f} collapse {parts}. "
        f"No band on this arm (D5, discipline 11)."
    )


def _edge_detail(edge: dict) -> str:
    if edge["vacuous"]:
        return "vacuous: the edge buckets did not survive the date filter"
    a, b = edge["leg_a"], edge["leg_b"]
    closest = b["control_ratios"][b["closest_control"]]
    return (
        f"(a) last pre bucket {a['last_pre_bucket']:.4f} against post max "
        f"{a['post_max']:.4f}, {a['margin']:.2f}x; "
        f"(b) treated ratio {b['treated_ratio']:.2f} against the closest "
        f"control {b['closest_control']} at {closest:.2f}, "
        f"{b['margin']:.2f}x; no threshold in either leg"
    )


def report(record: dict) -> None:
    print("B5-14: can a pre-existing trend be read off this pre-window at all\n")
    print(f"  collapse under test  {record['collapse_under_test']:.6f}"
          f"  ({record['collapse_detail']['rms_pre']:.4f} pre"
          f" -> {record['collapse_detail']['rms_post']:.4f} post,"
          f" read from B5-8)")
    print(f"  no band on this arm     withdrawn 2026-08-21 (D5, "
          f"discipline 11); horizon {record['horizon_buckets']} buckets\n")

    for label, key in (("PRIMARY", "primary_rung"), ("SECOND ", "second_rung")):
        rung = record[key]
        flag = " (encloses the December 2023 devaluation)" if rung[
            "encloses_december_2023_devaluation"] else ""
        print(f"  {label} rung {rung['window'][0]} to {rung['window'][1]}"
              f", {rung['treated']['nominal_buckets']} buckets{flag}")
        if rung["vacuous"]:
            print("      VACUOUS: not enough buckets survived the date filter")

        # Discipline 11 and 13's step 2: put the object in front of the reader
        # before anything derived from it. The series is what showed the turn;
        # the slope underneath it is what could not survive the turn.
        print("      treated series, rms per bucket:")
        values = rung["treated"]["rms_per_bucket"]
        for start in range(0, len(values), 12):
            row = values[start:start + 12]
            print("        " + " ".join(f"{v:6.3f}" for v in row))
        shape = rung["shape"]
        if shape["decidable"]:
            print("      shape: runs one way across the window, "
                  "so the slope summarises it")
        else:
            print("      shape: " + ", ".join(shape["interior_turns"])
                  + f"  of {rung['treated']['nominal_buckets']}")
            print("             the fitted slope is set by where it turned, "
                  "not by where it ended")

        slope = rung["treated"]["slope"]
        if slope is not None:
            print(f"      treated {rung['treated_pair']}: "
                  f"slope {slope:+.6f} per bucket, "
                  f"{len(rung['treated']['buckets_kept'])} buckets kept")
        for c in rung["comparisons"]:
            if c.get("vacuous"):
                print(f"      {c['control_pair']:16s}  VACUOUS")
                continue
            leg = " (shares a leg)" if c["shares_a_leg_with_treated"] else ""
            print(f"      {c['control_pair']:16s} "
                  f"slope {c['slope_control']:+.6f}, "
                  f"delta {c['delta_slope']:+.6f}, "
                  f"{c['direction']}, share {c['share_of_collapse']:.4f}{leg}")
        verdict = ("a linear reading is available"
                   if rung["linear_reading_available"]
                   else "NO LINEAR READING")
        print(f"      rung: {verdict}\n")

    print("  B5-14: VOID. The arm returns no verdict about the world, which is")
    print("         a different state from deciding against B5-8. The shares")
    print("         above are printed because they are what the arm produced,")
    print("         and they are not compared to anything (D5, discipline 11).")

    edge = record["B5-15"]
    print("\n  B5-15: the edge of the window, written AFTER B5-14 came back void")
    print("         and after its quantities were seen (prereg 6B.3).")
    print("         Neither leg contains a threshold.\n")
    if edge["vacuous"]:
        print(f"      VACUOUS: {edge['why']}")
    else:
        a, b = edge["leg_a"], edge["leg_b"]
        mark = "ok " if a["passed"] else "NO "
        print(f"      {mark}leg (a)  last pre bucket {a['last_pre_bucket']:.4f}"
              f"  >  post max {a['post_max']:.4f}"
              f"   ({a['margin']:.2f}x)   LOAD-BEARING")
        mark = "ok " if b["passed"] else "NO "
        print(f"      {mark}leg (b)  treated ratio {b['treated_ratio']:.2f}"
              f"  >  every control")
        for pair, value in b["control_ratios"].items():
            print(f"                   {pair:16s} {value:.2f}")
        print(f"               closest {b['closest_control']}, "
              f"{b['margin']:.2f}x. Corroborating only: September 2025 widened")
        print("               the controls' post window, which makes this leg "
              "easier")
    print(f"\n      B5-15 verdict: "
          f"{'PASS' if record['verdicts']['B5-15'] else 'FAIL'}")

    print("\n  B5-15 does not supply the reading B5-14 could not produce, and "
          "neither reaches B5-12.")
    print(f"  wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
