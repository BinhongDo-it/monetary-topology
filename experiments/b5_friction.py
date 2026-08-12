"""Validate a candidate for the oficial friction leg, before anything uses it.

``docs/b5_orphan_prereg.md`` §3.2 requires the oficial class's friction term to
come from **one named dealer**. Ámbito's ``dolar/oficial`` is a range across
retail bank counters, and reading it as `ω̄` would put dispersion between banks --
an agent index -- into a quantity B4 defines as one agent's round-trip cost. That
inverts the separation the whole stage rests on.

Banco de la Nación's own historical page did not answer a plain request, so the
candidate is **argentinadatos' ``oficial``**, which in Argentine practice is the
BNA counter board. That is a claim about a source, and this stage has already
been burned once by adopting a source on two hand-checked dates: argentinadatos'
``mayorista`` was taken as one half of the calibration arm and turned out to
freeze for up to 71 days, flat through the December 2023 devaluation.

**So the candidate is validated over the window before it is adopted**, on the
three axes that would each disqualify it:

1. **Is it one dealer?** A single posted board has a spread that is round and
   nearly constant. A range across banks has a spread that is neither.
2. **Is it the right level?** The mid must track BCRA's A 3500 inside the same
   bounds the calibration arm registered, or it is measuring something else.
3. **Is it alive?** The failure that disqualified ``mayorista`` was long runs of
   an unchanged quote. The same test is applied here, with the same threshold.

**Nothing here is a pre-registered criterion.** It is a source audit, run so that
a later criterion can rest on the answer, and its verdict is recorded so that
adopting the leg is a decision with a date and a reason rather than an
assumption.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from monetary_topology.parallel_rates import (
    ALL_AMBITO,
    WINDOW_END,
    WINDOW_START,
    chunk_files,
    collapse_to_daily,
    load_argentinadatos,
    load_bcra_reference,
    parse_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b5_friction.json"
CALIBRATION = ROOT / "results" / "b5_zero_calibration.json"

#: A posted board's spread is round. Anything within this of a whole peso counts
#: as round; the alternative it must be distinguished from is a cross-bank range,
#: whose spread lands anywhere.
ROUND_TOLERANCE_ARS = 0.005

#: What fraction of dates must carry the modal spread for "one dealer" to be the
#: better reading. A single board changes its spread rarely and deliberately; a
#: range changes it daily.
MODAL_SPREAD_SHARE = 0.50

#: The disqualifier that caught ``mayorista``: its longest run of an unchanged
#: sell quote was 71 days, against 13 for a series that was fine. Registered at
#: 21 -- three weeks -- which is comfortably above a holiday cluster and far
#: below what a frozen series shows.
MAX_FROZEN_RUN_DAYS = 21


def longest_frozen_run(rows: list[dict], field: str) -> tuple[int, str | None]:
    """The longest run of consecutive dates carrying an identical quote.

    **Both sides of the pairing are sliced.** ``zip(rows, rows[1:], strict=True)``
    raises: the sequences differ in length by one, and ``strict=True`` is not a
    formatting detail but a behaviour change. Adding it to satisfy B905 without
    adjusting the slices is how a lint fix becomes a runtime failure, which has
    now happened twice in this stage.
    """
    if len(rows) < 2:
        return len(rows), None
    longest, run, where = 1, 1, None
    for previous, current in zip(rows[:-1], rows[1:], strict=True):
        if current[field] == previous[field]:
            run += 1
            if run > longest:
                longest, where = run, current["date"]
        else:
            run = 1
    return longest, where


def main() -> int:
    if not CALIBRATION.exists():
        raise SystemExit(
            "results/b5_zero_calibration.json is missing; run "
            "experiments/b5_zero_calibration.py first."
        )
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    systematic_bound = calibration["B5-3"]["systematic_bound"]

    try:
        candidate = load_argentinadatos(RAW, "oficial")
    except FileNotFoundError as exc:
        raise SystemExit(
            "data/raw/argentinadatos_oficial.json is not retrieved. Run "
            "data/fetch_argentinadatos.py; the candidate was added to the "
            "series list in this change and the archive predates it."
        ) from exc
    rows = [
        r for r in candidate
        if WINDOW_START.isoformat() <= r["date"] <= WINDOW_END.isoformat()
    ]
    if not rows:
        raise SystemExit(
            "no argentinadatos oficial rows in the window; run "
            "data/fetch_argentinadatos.py first."
        )

    # 1. one dealer, or a range across banks
    spreads = [round(r["venta"] - r["compra"], 4) for r in rows]
    modal, modal_count = Counter(spreads).most_common(1)[0]
    modal_share = modal_count / len(spreads)
    round_share = sum(
        abs(s - round(s)) <= ROUND_TOLERANCE_ARS for s in spreads
    ) / len(spreads)
    one_dealer = modal_share >= MODAL_SPREAD_SHARE

    # 2. the right level
    ref = load_bcra_reference(RAW)
    devs = [
        abs(2.0 * (math.log(ref[r["date"]])
                   - math.log(math.sqrt(r["compra"] * r["venta"]))))
        for r in rows if r["date"] in ref
    ]
    devs.sort()
    median_dev = devs[len(devs) // 2] if devs else float("nan")
    right_level = bool(devs) and median_dev <= systematic_bound

    # 3. alive, by the test that caught mayorista
    frozen, frozen_at = longest_frozen_run(rows, "venta")
    alive = frozen <= MAX_FROZEN_RUN_DAYS

    # and the same test on the series that failed it, side by side, so the
    # comparison is in the record rather than in a sentence about the record
    others = {}
    for casa in ("mayorista", "tarjeta"):
        try:
            other = [
                r for r in load_argentinadatos(RAW, casa)
                if WINDOW_START.isoformat() <= r["date"] <= WINDOW_END.isoformat()
            ]
        except FileNotFoundError:
            continue
        run, at = longest_frozen_run(other, "venta")
        others[casa] = {"longest_frozen_run": run, "ending": at}

    # what Ambito's oficial looks like on the same axis, since it is the source
    # 3.2 rejected and the contrast is the argument
    fields = ALL_AMBITO["oficial"][1]
    ambito = collapse_to_daily(
        sorted(
            (r for p in chunk_files(RAW, "oficial")
             for r in parse_rows(json.loads(p.read_text(encoding="utf-8")), fields)),
            key=lambda r: r["date"],
        ),
        fields,
    )
    ambito = [r for r in ambito if WINDOW_START.isoformat() <= r["date"]
              <= WINDOW_END.isoformat()]
    ambito_spreads = [round(r["venta"] - r["compra"], 4) for r in ambito]
    ambito_modal, ambito_count = Counter(ambito_spreads).most_common(1)[0]

    adopted = one_dealer and right_level and alive
    record = {
        "stage": "B5-friction-audit",
        "audit": "candidate for the oficial friction leg",
        "candidate": "argentinadatos oficial",
        "registered_in": "docs/b5_orphan_prereg.md 3.2",
        "is_a_criterion": False,
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
        "dates": len(rows),
        "one_dealer": {
            "modal_spread_ars": modal,
            "modal_share": round(modal_share, 4),
            "round_spread_share": round(round_share, 4),
            "threshold": MODAL_SPREAD_SHARE,
            "passed": one_dealer,
            "ambito_oficial_for_contrast": {
                "modal_spread_ars": ambito_modal,
                "modal_share": round(ambito_count / len(ambito_spreads), 4),
                "note": (
                    "the source 3.2 rejected: a range across bank counters, "
                    "whose spread is neither round nor stable"
                ),
            },
        },
        "right_level": {
            "median_deviation_from_bcra": round(median_dev, 8),
            "bound": systematic_bound,
            "bound_from": "the calibration arm's registered systematic bound",
            "passed": right_level,
        },
        "alive": {
            "longest_frozen_run_days": frozen,
            "ending": frozen_at,
            "threshold": MAX_FROZEN_RUN_DAYS,
            "passed": alive,
            "same_test_on_other_series": others,
        },
        "verdict": "adopt" if adopted else "reject",
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B5 source audit: a candidate for the oficial friction leg\n")
    print(f"  argentinadatos oficial, {len(rows):,} dates in window\n")
    mark = "yes" if one_dealer else "NO"
    print(f"  one dealer?      {mark}")
    print(f"      modal spread {modal:.2f} ARS on {modal_share:.1%} of dates, "
          f"{round_share:.1%} round")
    print(f"      Ámbito oficial for contrast: modal {ambito_modal:.2f} on "
          f"{ambito_count / len(ambito_spreads):.1%}")
    mark = "yes" if right_level else "NO"
    print(f"  right level?     {mark}")
    print(f"      median deviation from BCRA {median_dev:.3e} "
          f"against {systematic_bound}")
    mark = "yes" if alive else "NO"
    print(f"  alive?           {mark}")
    print(f"      longest frozen run {frozen} days"
          + (f", ending {frozen_at}" if frozen_at else ""))
    for casa, block in others.items():
        print(f"      same test, {casa}: {block['longest_frozen_run']} days")
    print(f"\n  verdict: {record['verdict'].upper()}")
    print(f"  wrote {RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
