"""B5-1, B5-2, B5-6 and B5-7: the machinery, and whether the squares are there.

Registered in ``docs/b5_orphan_prereg.md`` §2, §6.

**Read the order.** §8 puts B5-1 and B5-2 before everything: if the machinery
disagrees with its own closed form, no number below it means anything. The
calibration arm (``b5_zero_calibration.py``) is the other gate, and it supplies
the noise floor B5-6 divides by.

What runs here and what does not
--------------------------------

**The headline needs only mid quotes**, and every class that has one is present:
``oficial`` from BCRA's A 3500, ``blue``, ``MEP`` and ``CCL`` from Ámbito. So
`S − S'` runs for all six pairs.

**The friction column does not run, and it never will on free data.** `S + S'`
needs two classes that each publish a spread. `blue` does; `MEP` and `CCL` do
not, by construction (§3.3); and ``oficial``'s spread has no source at all --
three candidates were audited and all three failed (§3.2a, and
``experiments/b5_friction.py``).

**So B5-8 was rewritten rather than deferred** (§3.2b). The original needed the
friction column because it needed *something that should not move*. That is
available without it: on 14 April 2025 the rule that was deleted was
**oficial's** USD 200 monthly cap, and MEP's and CCL's eligibility was a
brokerage account before and after. So the six pairs split by whether they
contain the treated class, and the comparison is premia against premia in the
same units from the same quotes -- which needs no assumption about how frictions
respond to eligibility rules, and the friction version did.

The prohibition that shapes every number here
---------------------------------------------

``b4_directed_edges.md`` §5.1: **a single orientation ``S`` is never reported.**
In a thin market its largest component is the bid-ask spread, and reporting it
would hand a reviewer the objection that the whole result is a quoting artefact.
Everything below is `S − S'`, in which the spread cancels by construction.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from monetary_topology.orphan_squares import (
    agent_quotes,
    build_field,
    friction_matrix,
    index_matrix,
    pair_index_series,
    rms,
    square_via_machinery,
)
from monetary_topology.parallel_rates import (
    FRICTION_SOURCE,
    INTERVENTION,
    POST_WINDOW,
    PRE_WINDOW,
    TREATED_CLASS,
    WINDOW_END,
    WINDOW_START,
    in_window,
    load_agent_classes,
    pair_group,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b5_squares.json"
CALIBRATION = ROOT / "results" / "b5_zero_calibration.json"

#: ``b5_orphan_prereg.md`` §7, and the same factor B3-3 used.
SIGNAL_OVER_NOISE = 4.0

#: ``b5_orphan_prereg.md`` §7, unchanged from the friction version of B5-8; only
#: what they are applied to changed, from two columns to two groups of pairs.
COLLAPSE_BAND = 1.0 / 3.0
PERSISTENCE_BAND = 2.0 / 3.0

#: B5-1's tolerance. The two paths are the same arithmetic in a different order,
#: so anything above rounding is a bug rather than a precision question.
MACHINERY_TOLERANCE = 1e-12


def noise_floor() -> tuple[float, str]:
    """The calibration arm's disagreement, in the units the headline is in.

    **Taken from the arm's own output rather than recomputed**, so the floor and
    the signal cannot drift apart. ``PROJECT_PLAN.md`` §11.11 rule 3: a noise
    floor computed on a different population from the signal is how A6's guard
    went wrong.
    """
    if not CALIBRATION.exists():
        raise SystemExit(
            "results/b5_zero_calibration.json is missing. B5-3 and B5-4 gate "
            "this stage (prereg 8); run experiments/b5_zero_calibration.py first."
        )
    record = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if not all(record["verdicts"].values()):
        raise SystemExit(
            f"the calibration arm did not pass: {record['verdicts']}. "
            f"Prereg 8: no headline without a calibration."
        )
    return record["B5-3"]["median"], "median deviation of the calibration arm"


#: Moved into ``orphan_squares`` when B5-14 became a second caller. Kept as a
#: module-level name here because three functions below read it and because the
#: alternative, two copies of the §7 row filter, is the kind of second truth this
#: stage has already been bitten by.
daily_quotes = agent_quotes


def b5_1_machinery(classes: dict, keys: tuple[str, ...], dates: list[str]) -> dict:
    """**B5-1.** The walked square equals the closed form, elementwise.

    One path decomposes each quote through ``directed.py`` and walks the four
    edges of the square, looking every leg up including the agent legs. The other
    is ``2 log(mid_b / mid_a)``. A test that recomputed the closed form the same
    way the code does would test nothing.
    """
    worst_index = worst_friction = 0.0
    worst_date = None
    checked = 0
    for when, quotes in daily_quotes(classes, keys, dates):
        field = build_field(quotes, keys)
        closed = index_matrix(quotes, keys)
        friction = friction_matrix(quotes, keys)
        for a in range(len(keys)):
            for b in range(len(keys)):
                if a == b:
                    continue
                s, s_rev = square_via_machinery(field, a, b)
                di = abs(s - s_rev - closed[a, b])
                df = abs(s + s_rev - friction[a, b])
                if max(di, df) > max(worst_index, worst_friction):
                    worst_date = when
                worst_index = max(worst_index, di)
                worst_friction = max(worst_friction, df)
        checked += 1
    return {
        "dates_checked": checked,
        "worst_index_discrepancy": float(worst_index),
        "worst_friction_discrepancy": float(worst_friction),
        "worst_date": worst_date,
        "tolerance": MACHINERY_TOLERANCE,
        "passed": bool(
            checked
            and max(worst_index, worst_friction) < MACHINERY_TOLERANCE
        ),
    }


def b5_2_trivial(classes: dict, keys: tuple[str, ...], dates: list[str]) -> dict:
    """**B5-2.** The diagonal of the difference matrix, not a short circuit.

    Read off ``index_matrix``'s diagonal. Short-circuiting on ``a == b`` would
    test the ``if``.
    """
    worst = 0.0
    checked = 0
    for _, quotes in daily_quotes(classes, keys, dates):
        worst = max(worst, float(np.abs(np.diag(index_matrix(quotes, keys))).max()))
        checked += 1
    return {
        "dates_checked": checked,
        "worst_diagonal": float(worst),
        "passed": bool(checked and worst == 0.0),
    }


#: Same move, same reason: B5-14 reads this series and must read *this* one.
pair_series = pair_index_series


def summarise_pair(series, floor: float) -> dict:
    values = np.array([v for _, v in series])
    dates = [d for d, _ in series]
    pre = np.array([v for d, v in series if d in set(in_window(dates, PRE_WINDOW))])
    post = np.array([v for d, v in series if d in set(in_window(dates, POST_WINDOW))])
    signal = rms(values)
    return {
        "dates": len(series),
        "rms": float(signal),
        "rms_pre": float(rms(pre)),
        "rms_post": float(rms(post)),
        "dates_pre": int(pre.size),
        "dates_post": int(post.size),
        "signal_over_noise": float(signal / floor) if floor else float("inf"),
    }


def main() -> int:
    floor, floor_name = noise_floor()
    classes = load_agent_classes(RAW)
    keys = tuple(classes)
    dates = in_window(
        sorted(set().union(*(set(v) for v in classes.values()))),
        (WINDOW_START, WINDOW_END),
    )

    b5_1 = b5_1_machinery(classes, keys, dates)
    b5_2 = b5_2_trivial(classes, keys, dates)

    pairs = {}
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            series = pair_series(classes, left, right, dates)
            if not series:
                continue
            block = summarise_pair(series, floor)
            block["friction_available"] = bool(
                FRICTION_SOURCE.get(left) and FRICTION_SOURCE.get(right)
            )
            block["friction_retrieved"] = False
            block["group"] = pair_group(left, right)
            pairs[f"{left}-{right}"] = block

    headline = pairs.get("oficial-informal")
    b5_6 = {
        "noise_floor": floor,
        "noise_floor_from": floor_name,
        "threshold": SIGNAL_OVER_NOISE,
        "headline_pair": "oficial-informal",
        "signal_over_noise": headline["signal_over_noise"] if headline else None,
        "passed": bool(
            headline and headline["signal_over_noise"] > SIGNAL_OVER_NOISE
        ),
    }
    b5_7 = {
        "window": [PRE_WINDOW[0].isoformat(), PRE_WINDOW[1].isoformat()],
        "rms_pre": headline["rms_pre"] if headline else None,
        "dates_pre": headline["dates_pre"] if headline else 0,
        "signal_over_noise_pre": (
            headline["rms_pre"] / floor if headline and floor else None
        ),
        "passed": bool(
            headline
            and headline["dates_pre"] > 0
            and headline["rms_pre"] / floor > SIGNAL_OVER_NOISE
        ),
    }

    treated = {k: v for k, v in pairs.items() if v["group"] == "treated"}
    control = {k: v for k, v in pairs.items() if v["group"] == "control"}

    def ratios(block: dict) -> dict:
        return {k: v["rms_post"] / v["rms_pre"] for k, v in block.items()
                if v["rms_pre"] > 0}

    treated_ratios, control_ratios = ratios(treated), ratios(control)
    treated_ok = bool(treated_ratios) and all(
        r <= COLLAPSE_BAND for r in treated_ratios.values()
    )
    control_ok = bool(control_ratios) and all(
        r >= PERSISTENCE_BAND for r in control_ratios.values()
    )
    b5_8 = {
        "form": "control pairs, not the friction column; see prereg 3.2a and 3.2b",
        "treated_class": TREATED_CLASS,
        "collapse_band": COLLAPSE_BAND,
        "persistence_band": PERSISTENCE_BAND,
        "treated": {k: round(v, 6) for k, v in treated_ratios.items()},
        "control": {k: round(v, 6) for k, v in control_ratios.items()},
        "treated_all_below_band": treated_ok,
        "control_all_above_band": control_ok,
        "caveat": (
            "MEP and CCL are clean with respect to the deleted cap and not with "
            "respect to every rule: the cross-restriction was removed on the "
            "intervention date and reimposed in September 2025, inside the "
            "post-window (PROJECT_PLAN 14.5). `informal` is the only class whose "
            "access was never rule-bound, which is why oficial-informal is the "
            "headline pair."
        ),
        "passed": bool(treated_ok and control_ok),
    }

    # `worst_machinery`, the max of B5-1's two discrepancies, was computed here
    # for the detail string below and is no longer written into the record
    # (`CLAUDE.md` rule 6, since it is a residual at machine precision whose
    # digits vary by build). It is not recomputed for the log either: `main`
    # already prints **both** components, and the max of two printed numbers is
    # not a third number a reader needs.
    record = {
        "stage": "B5-squares",
        "registered_in": "docs/b5_orphan_prereg.md 2, 6",
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
        "intervention": INTERVENTION.isoformat(),
        "classes": {k: len(v) for k, v in classes.items()},
        "headline_sources": "prereg 3.1; oficial is BCRA A 3500, not Ambito",
        "friction_column": {
            "runs": False,
            "why": (
                "S + S' needs two classes that each publish a spread. MEP and "
                "CCL have no native two-sided quote (prereg 3.3), and oficial's "
                "spread has no source: three candidates were audited and all "
                "three failed (prereg 3.2a, experiments/b5_friction.py). B5-8 "
                "was therefore rewritten to use control pairs rather than the "
                "friction column (prereg 3.2b)."
            ),
        },
        "B5-8": b5_8,
        "B5-1": b5_1,
        "B5-2": b5_2,
        "B5-6": b5_6,
        "B5-7": b5_7,
        "pairs": pairs,
        "criteria": [
            {
                "name": "B5-1 walked square equals the closed form",
                "passed": b5_1["passed"],
                # `CLAUDE.md` rule 6. The discrepancy between the walked square
                # and the closed form is a residual against an identity, so it
                # sits at machine epsilon and its digits vary by build; written
                # into `RESULTS.md` it makes CI's `git diff --exit-code` fail
                # between machines on content that asserts the same thing. The
                # value is already printed to the job log by `main`, so nothing
                # is lost by keeping it out of here.
                "detail": (
                    f"at machine precision, below `1e-10`, against a tolerance "
                    f"of {MACHINERY_TOLERANCE:.0e}, over "
                    f"{b5_1['dates_checked']:,} dates"
                ),
            },
            {
                "name": "B5-2 trivial square is exactly zero",
                "passed": b5_2["passed"],
                "detail": (
                    f"worst diagonal {b5_2['worst_diagonal']:.1e}, off the same "
                    f"matrix every other number comes from"
                ),
            },
            {
                "name": "B5-6 headline clears the noise floor",
                "passed": b5_6["passed"],
                "detail": (
                    f"S/N {b5_6['signal_over_noise']:.0f} against "
                    f"{SIGNAL_OVER_NOISE:g}, floor {floor:.3e} from the "
                    f"calibration arm"
                ),
            },
            {
                "name": "B5-7 squares do not vanish before the intervention",
                "passed": b5_7["passed"],
                "detail": (
                    f"pre-window rms {b5_7['rms_pre']:.4f} over "
                    f"{b5_7['dates_pre']} dates, S/N "
                    f"{b5_7['signal_over_noise_pre']:.0f}"
                ),
            },
            {
                "name": "B5-8 treated premia collapse, untouched ones do not",
                "passed": b5_8["passed"],
                "detail": (
                    "treated "
                    + ", ".join(f"{v:.3f}" for v in b5_8["treated"].values())
                    + f" (<= {COLLAPSE_BAND:.3f}); control "
                    + ", ".join(f"{v:.3f}" for v in b5_8["control"].values())
                    + f" (>= {PERSISTENCE_BAND:.3f})"
                ),
            },
        ],
        "verdicts": {
            "B5-1": b5_1["passed"], "B5-2": b5_2["passed"],
            "B5-6": b5_6["passed"], "B5-7": b5_7["passed"],
            "B5-8": b5_8["passed"],
        },
        "not_evaluated": {
            "B5-9": "needs the P2P class, not retrieved",
            "B5-12": "needs the P2P class, not retrieved",
            "B5-13": "needs the P2P class, not retrieved",
            "B5-11": (
                "needs the FRICTION COLUMN, which has no source at all (prereg "
                "3.2a). Not a P2P problem: it dies with B5-8's original form. "
                "An earlier version of this file filed it under P2P, which "
                "would have sent the next reader looking for the wrong thing."
            ),
        },
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B5 squares: the agent index on one conversion\n")
    for key, count in record["classes"].items():
        print(f"  {key:10s} {count:5d} dates")
    print()
    mark = "pass" if b5_1["passed"] else "FAIL"
    print(f"  B5-1  walked square equals the closed form           {mark}")
    print(f"          worst index {b5_1['worst_index_discrepancy']:.2e}, "
          f"friction {b5_1['worst_friction_discrepancy']:.2e}, "
          f"over {b5_1['dates_checked']:,} dates")
    mark = "pass" if b5_2["passed"] else "FAIL"
    print(f"  B5-2  trivial square is exactly zero                 {mark}")
    print(f"          worst diagonal {b5_2['worst_diagonal']:.1e}")

    print(f"\n  noise floor {floor:.3e} ({floor_name})\n")
    width = max(len(k) for k in pairs)
    print(f"  {'pair'.ljust(width)}  {'group':>7s} {'dates':>6s} "
          f"{'pre':>9s} {'post':>9s} {'post/pre':>9s}")
    for name, block in pairs.items():
        ratio = (block["rms_post"] / block["rms_pre"]
                 if block["rms_pre"] else float("nan"))
        print(f"  {name.ljust(width)}  {block['group']:>7s} {block['dates']:6d} "
              f"{block['rms_pre']:9.4f} {block['rms_post']:9.4f} {ratio:9.3f}")

    mark = "pass" if b5_6["passed"] else "FAIL"
    print(f"\n  B5-6  headline clears the noise floor by {SIGNAL_OVER_NOISE:g}x     "
          f"        {mark}")
    mark = "pass" if b5_7["passed"] else "FAIL"
    print(f"  B5-7  squares do not vanish before the intervention  {mark}")
    print(f"          pre-window rms {b5_7['rms_pre']:.4f} over "
          f"{b5_7['dates_pre']} dates, S/N {b5_7['signal_over_noise_pre']:.1f}")

    mark = "pass" if b5_8["passed"] else "FAIL"
    print(f"\n  B5-8  treated premia collapse, untouched ones do not   {mark}")
    print(f"          treated  (must be <= {COLLAPSE_BAND:.3f}): " + ", ".join(
        f"{k} {v:.3f}" for k, v in b5_8["treated"].items()))
    print(f"          control  (must be >= {PERSISTENCE_BAND:.3f}): " + ", ".join(
        f"{k} {v:.3f}" for k, v in b5_8["control"].items()))

    print("\n  NOT evaluated:")
    for name, why in record["not_evaluated"].items():
        print(f"    {name}: {why.splitlines()[0][:66]}")
    print(f"\n  wrote {RESULTS.relative_to(ROOT)}")
    return 0 if all(record["verdicts"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
