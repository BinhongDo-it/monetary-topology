"""B121 arm D, part one: describe commercial paper outstanding around the two facilities.

No criteria yet (discipline 13: describe the object before testing anything). Everything is on
disk; nothing is fetched.

  objects   COMPOUT, all commercial paper outstanding, weekly, billions
            ABCOMP, asset-backed commercial paper outstanding, weekly, billions
            COMPOUT minus WCPFF: what is held outside the Commercial Paper Funding Facility.
            The facility's own purchases are counted in COMPOUT, so the total rises by one for each
            one the Fed buys; that part is mechanical and says nothing about the edge conducting.
  dates     AMLF announced 2008-09-19; CPFF announced 2008-10-07, first purchase 2008-10-27
            (both from the Board's own facility pages, saved in data/raw/b121/reform_*.html)
  doses     WABCMMF (AMLF outstanding), WCPFF (CPFF holdings), and the target rate

    python experiments/b121_d_cp.py
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b121"
OUT = ROOT / "results" / "b121_d_cp.json"
FIRST, LAST = "2007-01-01", "2009-12-31"
DATES = {"AMLF announced": "2008-09-19", "CPFF announced": "2008-10-07",
         "CPFF first purchase": "2008-10-27"}


def fred(sid: str) -> dict[str, float]:
    rows = list(csv.reader((RAW / f"{sid}.csv").open(encoding="utf-8")))[1:]
    return {r[0]: float(r[1]) for r in rows if len(r) > 1 and r[1] not in ("", ".", "NA")}


def weekly_after(series: dict[str, float], weeks: list[str], day: str, k: int) -> float | None:
    """Change from the last week before `day` to the k-th week on or after it."""
    before = [w for w in weeks if w < day]
    after = [w for w in weeks if w >= day]
    if not before or len(after) < k:
        return None
    return series[after[k - 1]] - series[before[-1]]


def main() -> int:
    total, abcp = fred("COMPOUT"), fred("ABCOMP")
    cpff = fred("WCPFF")
    amlf = fred("WABCMMF")
    target = {**fred("DFEDTAR"), **fred("DFEDTARU")}

    weeks = sorted(w for w in total if FIRST <= w <= LAST and w in abcp)
    # CPFF holdings are weekly on Wednesdays; COMPOUT is weekly on Wednesdays too. Check they align.
    cpff_w = {w: cpff.get(w, 0.0) for w in weeks}
    unmatched = [w for w in cpff if FIRST <= w <= LAST and w not in total]
    private = {w: total[w] - cpff_w[w] for w in weeks}
    unsecured = {w: total[w] - abcp[w] for w in weeks}
    print(f"{len(weeks)} weeks, {weeks[0]} to {weeks[-1]}; CPFF weeks not on a COMPOUT week: {len(unmatched)}")

    def at(s, w):
        return f"{s[w]:8.1f}" if w in s else "     n/a"

    marks = ["2007-01-03", "2007-08-01", "2007-12-26", "2008-06-25", "2008-09-10", "2008-09-17",
             "2008-09-24", "2008-10-01", "2008-10-08", "2008-10-22", "2008-10-29", "2008-11-26",
             "2008-12-31", "2009-03-25", "2009-06-24", "2009-12-30"]
    print("\nweek         total    ABCP  unsecured  held by CPFF  outside CPFF  AMLF out")
    for w in marks:
        w2 = min((x for x in weeks if x >= w), default=None)
        if w2 is None:
            continue
        print(f"{w2}  {at(total, w2)} {at(abcp, w2)} {at(unsecured, w2)}     {cpff_w[w2]:8.1f}      "
              f"{at(private, w2)}  {amlf.get(w2, 0.0):8.1f}")

    # How each object moved after each date, against how it moves in any week of the window.
    objects = {"total": total, "ABCP": abcp, "unsecured": unsecured, "outside CPFF": private}
    moves = {}
    print("\nchange after each date (billions), and where it sits among every week's own change "
          "over the same span (the object's own distribution, percentile):")
    for name, s in objects.items():
        moves[name] = {}
        for label, day in DATES.items():
            row = {}
            for k in (1, 4, 8):
                ch = weekly_after(s, weeks, day, k)
                all_k = [s[weeks[i + k]] - s[weeks[i]] for i in range(len(weeks) - k)]
                pct = None if ch is None else 100.0 * sum(1 for x in all_k if x <= ch) / len(all_k)
                row[f"{k}w"] = {"change": None if ch is None else round(ch, 1),
                                "percentile": None if pct is None else round(pct, 1)}
            moves[name][label] = row
            print(f"  {name:<13} {label:<20} " + "  ".join(
                f"{k}: {v['change']:+7.1f} (p{v['percentile']:5.1f})" for k, v in row.items()))

    steps = []
    prev = None
    for d in sorted(t for t in target if FIRST <= t <= LAST):
        if prev is not None and abs(target[d] - target[prev]) > 1e-9:
            steps.append({"date": d, "step_pp": round(target[d] - target[prev], 4)})
        prev = d
    print(f"\nrate steps in the window: {len(steps)}")
    rate_moves = []
    for s in steps:
        ch = weekly_after(private, weeks, s["date"], 4)
        rate_moves.append(dict(s, outside_cpff_4w=None if ch is None else round(ch, 1)))
        print(f"  {s['date']}  {s['step_pp']:+.2f}   outside-CPFF change over 4 weeks: "
              f"{'n/a' if ch is None else f'{ch:+.1f}'}")

    record = {
        "stage": "B121",
        "diagnostic_only": True,
        "diagnostic_reason": "Arm D, part one: a description of the object before any criterion "
                             "is written (discipline 13).",
        "config": {"window": [FIRST, LAST], "dates": DATES},
        "source": {"COMPOUT": "FRED, commercial paper outstanding, weekly",
                   "ABCOMP": "FRED, asset-backed commercial paper outstanding, weekly",
                   "WCPFF": "FRED, net portfolio holdings of CPFF LLC, weekly",
                   "WABCMMF": "FRED, Reserve Bank credit: AMLF, weekly",
                   "dates": "Board of Governors facility pages, reform_amlf.htm and reform_cpff.htm"},
        "levels": {w: {"total": total[w], "abcp": abcp[w], "cpff": cpff_w[w],
                       "outside_cpff": round(private[w], 3), "amlf": amlf.get(w, 0.0)} for w in weeks},
        "moves_after_dates": moves,
        "rate_steps": rate_moves,
        "cpff_weeks_off_grid": unmatched,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
