"""Leg A read again on the post window the original design dropped.

WHY THE ORIGINAL DESIGN DROPPED OCTOBER, AND WHY THAT REASON DOES NOT TRANSFER

The 2016 round drops October 2016 because the pilot phased in across that month:
the test groups entered in waves between October 3 and October 31, so the month is
a mixed state and neither a pre nor a post observation. Leg A mirrored that drop
into 2018.

The 2018 end has no such property. Cboe's expiration notice: "The SEC granted an
exemption to permit Tick Pilot Plan Participants to end the quoting and trading
requirements of the Tick Pilot Program at the close of trading on September 28,
2018", and "As of October 1, 2018, all securities in Tick Pilot Test Groups will
open in the Control Group." One moment, every test group, no waves. FINRA's notice
carries the same date in its title.

So the mirror carried the calendar shape of the drop without carrying its reason,
and October 2018 is a clean, whole, fully post-treatment month.

HOW THIS WINDOW WAS ARRIVED AT, STATED RATHER THAN IMPLIED

This is a redesign after the fact and it is recorded as one. The order of events
was: leg A returned three negative margins; the control group's own delta in leg
A's record was +0.2766 on venue N, larger than all eighteen placebo blocks; an
enumeration of every post window anchored on 2018-09-28 showed October to be the
only one whose control delta sits inside the placebo band. So the defect was found
by looking at the data.

The justification for the change is separate from how it was found, and it is
structural: the phase-in that justified dropping October existed in 2016 and did
not exist in 2018. That argument was available before any window was run. Both
facts belong in the record; reporting only the second would make a data-driven
discovery look like a design decision.

The original verdict is not withdrawn and results/b14_gate_exit.json is not
edited beyond a pointer. Project discipline: a redesign after the fact is
permitted, its reason is recorded, and the original reading is kept.

SCOPE

This window is two months of pre, no month dropped, one month of post. The
placebo band in results/b14_placebo_band.json was measured on two-month post
windows and does not apply: a one-month window carries more sampling noise, and
reading one against the other would put criterion and object in different scopes.
results/b14_placebo_band_1m.json is the band at this shape, and it is what the
margins here are read against.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate_exit as X   # noqa: E402  load / deltas / gate, reused not copied

PRE = ("20180801", "20180928")
POST = ("20181001", "20181031")
BAND = os.path.join(ROOT, "results", "b14_placebo_band_1m.json")
OUT = os.path.join(ROOT, "results", "b14_gate_exit_oct.json")


def quantile(xs, p):
    xs = sorted(xs)
    i = p * (len(xs) - 1)
    lo = int(i)
    return xs[lo] if lo == i else xs[lo] + (xs[lo + 1] - xs[lo]) * (i - lo)


def main():
    band = json.load(open(BAND, encoding="utf-8"))
    blocks = band["blocks"]
    rec, files, probe = X.load(PRE, POST)
    d, sk = X.deltas(rec, "pre")
    res, ctrs = X.gate(d, -1)
    out = {
        "stage": "B14", "round": "2018-october", "pre": PRE, "post": POST,
        "sign": -1, "grp_from": "pre", "diagnostic_only": True,
        "diagnostic_reason":
            "leg A re-read on the post window the original design dropped; the "
            "drop mirrored the 2016 phase-in month, and the 2018 end had no "
            "phase-in (all test groups ended at the close on 2018-09-28 and "
            "opened in the control group on October 1). This is a redesign after "
            "the fact: the defect was found by reading the control group's own "
            "delta, the justification for the window is structural and predates "
            "the reading, and results/b14_gate_exit.json stands unwithdrawn. B14 "
            "stage two is still locked, so this record is evidence and not a "
            "licensed reading",
        "band_source": os.path.relpath(BAND, ROOT),
        "band_blocks": len(blocks),
        "band_independent": band["independent_subset"],
        "band_note":
            "the band blocks overlap; their count is consistency and not a sample "
            "size, and the largest non-overlapping subset has %d members"
            % len(band["independent_subset"]),
        "measures": {},
    }
    for name in res:
        tab = res[name]["table"]
        gaps = {"%s/%s" % (x["ctr"], x["grp"]): x["raw_gap"]
                for x in res[name]["inequalities"]}
        cells = {}
        for c, g in gaps.items():
            xs = [b["measures"][name]["gaps"][c] for b in blocks]
            lo, hi = quantile(xs, 0.10), quantile(xs, 0.90)
            cells[c] = {"raw_gap": g, "band_p10": lo, "band_p90": hi,
                        "outside_band": bool(g < lo or g > hi),
                        "twin": blocks[band["twin"]]["measures"][name]["gaps"][c]}
        cd = {}
        for v in ctrs:
            xs = [b["measures"][name]["control_delta"][v] for b in blocks]
            lo, hi = quantile(xs, 0.10), quantile(xs, 0.90)
            cd[v] = {"delta": tab[v + "/C"]["delta"], "n": tab[v + "/C"]["n"],
                     "band_p10": lo, "band_p90": hi,
                     "outside_band": bool(tab[v + "/C"]["delta"] < lo
                                          or tab[v + "/C"]["delta"] > hi)}
        out["measures"][name] = {
            "desc": res[name]["desc"], "control_delta": cd, "cells": cells,
            "table": tab,
            "outside_band": sum(1 for c in cells.values() if c["outside_band"]),
            "outside_band_and_predicted_sign":
                sum(1 for c in cells.values()
                    if c["outside_band"] and c["raw_gap"] < 0),
        }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    for name in ("bbo_shr", "bbo_cnt", "nbbo_shr", "bbo_shr_adv", "bbo_shr_adv2"):
        m = out["measures"][name]
        print("  %-14s outside band %d/6, of those in the predicted direction %d"
              % (name, m["outside_band"], m["outside_band_and_predicted_sign"]))
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
