"""B5-14: parallel trends, asked of the control pairs that exist.

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

#: ``b5_orphan_prereg.md`` §6A.4. A linear trend already present before the
#: intervention may account for at most a quarter of the change the intervention
#: is credited with. The ``1/4`` is the factor of four B5-3, B5-6 and B3-3
#: already use; its value carries no independent meaning, and what it carries is
#: that one discipline applies wherever a magnitude has to clear something.
PRE_TREND_SHARE = 0.25

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
#: return a slope. Below it the rung is ``vacuous`` rather than small, per
#: ``PROJECT_PLAN.md`` §11.11 rule 1: a criterion with an empty comparison side
#: must fail and say so rather than return a number.
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


def compare(treated: dict, control: dict, control_pair: tuple[str, str],
            collapse: float) -> dict:
    """One treated-against-control slope difference, with its direction.

    §6A.5 fixes both directions in advance. A treated pair already falling
    **faster** than its control is the damaging case and the band applies to it.
    A treated pair already diverging cannot manufacture the collapse, only make
    it harder to produce, so it is reported with magnitude and sign and carries
    no band.
    """
    if treated["slope"] is None or control["slope"] is None:
        return {
            "control_pair": pair_key(control_pair),
            "vacuous": True,
            "why": "a rung did not keep enough buckets to fit a slope",
            "passed": False,
        }
    delta = treated["slope"] - control["slope"]
    damaging = delta < 0.0
    share = abs(delta) * HORIZON_BUCKETS / collapse
    return {
        "control_pair": pair_key(control_pair),
        "shares_a_leg_with_treated": shares_a_leg(TREATED_PAIR, control_pair),
        "slope_treated": treated["slope"],
        "slope_control": control["slope"],
        "delta_slope": round(delta, 12),
        "direction": "damaging" if damaging else "conservative",
        "share_of_collapse": round(share, 9),
        "band": PRE_TREND_SHARE,
        "vacuous": False,
        "passed": bool((not damaging) or share <= PRE_TREND_SHARE),
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
        "vacuous": not usable,
        "passed": bool(usable and all(c["passed"] for c in comparisons)),
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

    Registered in §6B **after B5-14 failed**, and §6B.3 discloses that the
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
        "band": PRE_TREND_SHARE,
        "collapse_under_test": round(collapse, 12),
        "collapse_detail": collapse_detail,
        "primary_rung": primary,
        "second_rung": second,
        "verdict_decided_on": "primary rung; the second is reported alongside",
        "second_rung_agrees": bool(primary["passed"] == second["passed"]),
        "does_not_repair_b5_12": (
            "B5-12 is unevaluated for two reasons that live in the post-window "
            "and in retrieval: MEP's and CCL's second treatment in September "
            "2025 (prereg 8.1) and the absence of the P2P class (prereg 8.2). A "
            "pre-window trend result speaks to neither, so this record does not "
            "convert B5-12 from unevaluated to identified (prereg 6A.7)."
        ),
        "B5-15": edge,
        "why_b5_15_exists": (
            "B5-14 failed, and its own registered output shows why: the "
            "pre-window bucket series is not trend-stationary, so a linear "
            "extrapolation does not describe it. B5-15 asks the surviving "
            "question at the edge of the window instead, where no extrapolation "
            "is needed. Written after that failure and after its quantities were "
            "seen; prereg 6B.3 is the disclosure, and neither of its legs "
            "contains a threshold that could have been moved."
        ),
        "b5_14_verdict_not_revised": (
            "B5-15 does not convert B5-14 from failed to passed and does not "
            "remove prereg 8's consequence for B5-8 (prereg 6B.3)."
        ),
        "criteria": [
            {
                "name": (
                    "B5-14 no pre-existing trend explains B5-8's collapse"
                ),
                "detail": _detail(primary, collapse),
                "passed": primary["passed"],
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
        "verdicts": {"B5-14": primary["passed"], "B5-15": edge["passed"]},
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
    parts = []
    for c in rung["comparisons"]:
        parts.append(
            f"{c['control_pair']} {c['direction'][:4]} "
            f"{c['share_of_collapse']:.3f}"
        )
    return (
        f"collapse under test {collapse:.4f}; "
        + "; ".join(parts)
        + f"; band {PRE_TREND_SHARE}"
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
    print("B5-14: parallel trends, on the control pairs that exist\n")
    print(f"  collapse under test  {record['collapse_under_test']:.6f}"
          f"  ({record['collapse_detail']['rms_pre']:.4f} pre"
          f" -> {record['collapse_detail']['rms_post']:.4f} post,"
          f" read from B5-8)")
    print(f"  band                 {record['band']}"
          f"   over {record['horizon_buckets']} buckets\n")

    for label, key in (("PRIMARY", "primary_rung"), ("SECOND ", "second_rung")):
        rung = record[key]
        flag = " (encloses the December 2023 devaluation)" if rung[
            "encloses_december_2023_devaluation"] else ""
        print(f"  {label} rung {rung['window'][0]} to {rung['window'][1]}"
              f", {rung['treated']['nominal_buckets']} buckets{flag}")
        if rung["vacuous"]:
            print("      VACUOUS: not enough buckets survived the date filter")
        slope = rung["treated"]["slope"]
        if slope is not None:
            print(f"      treated {rung['treated_pair']}: "
                  f"slope {slope:+.6f} per bucket, "
                  f"{len(rung['treated']['buckets_kept'])} buckets kept")
        for c in rung["comparisons"]:
            if c.get("vacuous"):
                print(f"      {c['control_pair']:16s}  VACUOUS")
                continue
            mark = "ok " if c["passed"] else "NO "
            leg = " (shares a leg)" if c["shares_a_leg_with_treated"] else ""
            print(f"      {mark}{c['control_pair']:16s} "
                  f"slope {c['slope_control']:+.6f}, "
                  f"delta {c['delta_slope']:+.6f}, "
                  f"{c['direction']}, share {c['share_of_collapse']:.4f}{leg}")
        print(f"      rung verdict: {'PASS' if rung['passed'] else 'FAIL'}\n")

    print(f"  B5-14 verdict (decided on the primary rung): "
          f"{'PASS' if record['verdicts']['B5-14'] else 'FAIL'}")
    if not record["second_rung_agrees"]:
        print("  NOTE: the second rung disagrees with the primary; both are "
              "reported, and neither was chosen after the fact")

    edge = record["B5-15"]
    print("\n  B5-15: the edge of the window, written AFTER B5-14 failed")
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

    print("\n  B5-14's verdict is not revised by B5-15, and neither reaches "
          "B5-12.")
    print(f"  wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
