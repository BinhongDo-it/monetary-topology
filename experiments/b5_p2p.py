"""Audit the P2P candidate before B5-9, B5-12 and B5-13 rest on it.

`docs/b5_orphan_prereg.md` §2.1 registers a fifth agent class, `ARS/USDT` P2P.
Its eligibility is a **platform account rather than a state licence**, so the
April 2025 intervention did not touch it, which is exactly why it is the control
unit those three criteria are written against.

The candidate is argentinadatos' `cripto` series. Binance publishes no historical
P2P interface, and CriptoYa publishes bid and ask across thirty-six venues **for
the current moment only**, so this is the only free daily history that exists.

The audit, and the one axis it cannot run
-----------------------------------------

This stage has adopted a source on two hand-checked dates twice, and both times
the whole-window behaviour was different: argentinadatos' `mayorista` froze for
**71 days** through the December 2023 devaluation, and its `oficial` froze for
**106**. So a candidate is audited before it is used.

1. **Alive?** The frozen-run test that caught both, at the same threshold.
2. **Covers both windows?** A control that is absent from the pre-window cannot
   control anything.
3. **Refereed?** — **and this one cannot be run.** There is no central bank for a
   crypto market and no second full-window collector. `b5_orphan_availability.md`
   §7.4 otherwise requires an independent referee over the whole window before a
   third-party series carries anything; **this series cannot have one**, and that
   is structural rather than an oversight.

**The bias that absence introduces has no clean sign**, which is worse than a
known direction. A stale control would track `blue` through its own staleness,
and whether that inflates or deflates its premium against `blue` depends on which
way `blue` moved. So the audit reports what it can and the limitation travels
with every number computed from the series.

**Not a pre-registered criterion.** It is a source audit whose verdict is
recorded so that adopting the class is a decision with a date and a reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from monetary_topology.parallel_rates import (
    POST_WINDOW,
    PRE_WINDOW,
    WINDOW_END,
    WINDOW_START,
    in_window,
    load_argentinadatos,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b5_p2p.json"

#: The same threshold `b5_friction.py` registered, and for the same reason: it
#: sits between the 13 days a sound series showed and the 71 a broken one did.
#: **Not re-derived here.** A threshold that exists in two files has two truths.
MAX_FROZEN_RUN_DAYS = 21

#: A control needs enough of both windows to have a pre and a post. Set at the
#: smallest count at which an rms over a year means anything rather than at
#: whatever the candidate happens to have.
MIN_DATES_PER_WINDOW = 60


def longest_frozen_run(rows: list[dict], field: str) -> tuple[int, str | None]:
    """The longest run of consecutive dates carrying an identical quote.

    Both sides of the pairing are sliced; ``zip(rows, rows[1:], strict=True)``
    raises, and adding ``strict=True`` without adjusting the slices is how a lint
    fix became a runtime failure twice in this stage.
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
    try:
        series = load_argentinadatos(RAW, "cripto")
    except FileNotFoundError as exc:
        raise SystemExit(
            "data/raw/argentinadatos_cripto.json is not retrieved. Run "
            "data/fetch_argentinadatos.py; the candidate was added to the "
            "series list in this change and the archive predates it."
        ) from exc

    rows = [
        r for r in series
        if WINDOW_START.isoformat() <= r["date"] <= WINDOW_END.isoformat()
    ]
    if not rows:
        raise SystemExit("no argentinadatos cripto rows in the registered window")

    dates = [r["date"] for r in rows]
    pre, post = in_window(dates, PRE_WINDOW), in_window(dates, POST_WINDOW)
    covers = len(pre) >= MIN_DATES_PER_WINDOW and len(post) >= MIN_DATES_PER_WINDOW

    frozen, frozen_at = longest_frozen_run(rows, "venta")
    alive = frozen <= MAX_FROZEN_RUN_DAYS

    # The two series the frozen-run test already judged, side by side, so the
    # comparison sits in the record rather than in a sentence about the record.
    others = {}
    for casa in ("mayorista", "oficial", "tarjeta"):
        try:
            other = [
                r for r in load_argentinadatos(RAW, casa)
                if WINDOW_START.isoformat() <= r["date"] <= WINDOW_END.isoformat()
            ]
        except FileNotFoundError:
            continue
        run, at = longest_frozen_run(other, "venta")
        others[casa] = {"longest_frozen_run": run, "ending": at}

    two_sided = sum(r["venta"] != r["compra"] for r in rows)

    adopted = bool(alive and covers)
    record = {
        "stage": "B5-p2p-audit",
        "audit": "candidate for the P2P agent class",
        "candidate": "argentinadatos cripto",
        "registered_in": "docs/b5_orphan_prereg.md 2.1, and 9.4 for provenance",
        "is_a_criterion": False,
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
        "dates": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "coverage": {
            "pre_window_dates": len(pre),
            "post_window_dates": len(post),
            "threshold": MIN_DATES_PER_WINDOW,
            "passed": covers,
        },
        "alive": {
            "longest_frozen_run_days": frozen,
            "ending": frozen_at,
            "threshold": MAX_FROZEN_RUN_DAYS,
            "passed": alive,
            "same_test_on_other_series": others,
        },
        "refereed": {
            "possible": False,
            "why": (
                "There is no central bank for a crypto market and no second "
                "full-window collector. CriptoYa publishes bid and ask across "
                "thirty-six venues but only for the current moment. So this is "
                "the one series in stage B5 that b5_orphan_availability.md 7.4's "
                "referee requirement cannot be applied to, and the exemption is "
                "structural rather than an oversight."
            ),
            "bias": (
                "No clean sign, which is worse than a known direction: a stale "
                "control would track blue through its own staleness, and whether "
                "that inflates or deflates its premium against blue depends on "
                "which way blue moved."
            ),
        },
        "two_sided_dates": two_sided,
        "note_on_spread": (
            "Where compra equals venta the series carries no spread, so the "
            "class contributes to the headline and not to any friction column. "
            "That column has no source anyway (prereg 3.2a)."
        ),
        "verdict": "adopt" if adopted else "reject",
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B5 source audit: a candidate for the P2P agent class\n")
    print(f"  argentinadatos cripto, {len(rows):,} dates in window, "
          f"{rows[0]['date']} to {rows[-1]['date']}\n")
    mark = "yes" if covers else "NO"
    print(f"  covers both windows?  {mark}")
    print(f"      pre {len(pre)}, post {len(post)}, "
          f"each must be >= {MIN_DATES_PER_WINDOW}")
    mark = "yes" if alive else "NO"
    print(f"  alive?                {mark}")
    print(f"      longest frozen run {frozen} days"
          + (f", ending {frozen_at}" if frozen_at else ""))
    for casa, block in others.items():
        print(f"      same test, {casa}: {block['longest_frozen_run']} days")
    print("  refereed?             NOT POSSIBLE")
    print("      no central bank and no second full-window collector; the "
          "limitation")
    print("      travels with every number computed from this series")
    print(f"\n  {two_sided:,} of {len(rows):,} dates carry a spread")
    print(f"\n  verdict: {record['verdict'].upper()}")
    print(f"  wrote {RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
