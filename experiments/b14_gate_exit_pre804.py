"""The exit round on the population it shares with the entry round.

Venue N's Appendix B coverage jumps from 618 distinct symbols in 201803 to 2110 in
201804 and from then on matches venue P's. The entry round therefore runs on about
679 venue-N symbols and the exit round on about 2070, roughly two thirds of which
are Nasdaq-listed names whose venue-N activity is marginal. Thin activity gives
noisy spreads and noisy spreads are what make an answer turn on the weighting
convention, which is the exit round's symptom.

The population here is the symbol set in the 201803 venue-N file: the last month
before the scope change. It is a coverage fact rather than an outcome, it predates
both of the round's windows, and applying it to both venues puts the exit round on
a population comparable to the entry round's, which is the point.

The criterion is sign agreement across the four venue conventions. That is not a
line on an estimate, so it needs no band and carries no threshold.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate_exit as X   # noqa: E402

VENUE_CONV = ("bbo_shr", "bbo_cnt", "bbo_shr_adv", "bbo_shr_adv2")
CELLS = ["N/G1", "N/G2", "N/G3", "P/G1", "P/G2", "P/G3"]
OUT = os.path.join(ROOT, "results", "b14_gate_exit_pre804.json")


def population():
    p = os.path.join(X.CACHE, "panel_v2_NYSE_201803.csv")
    s = set()
    with open(p) as fh:
        fh.readline()
        for line in fh:
            if not line.startswith("#"):
                s.add(X.canon(line.split(",")[2]))
    return s


def run(pre, post, keep):
    rec, files, probe = X.load(pre, post)
    rec = {k: v for k, v in rec.items() if k[1] in keep}
    d, sk = X.deltas(rec, "pre")
    res, ctrs = X.gate(d, -1)
    return res


def main():
    keep = population()
    print("population: %d symbols from the 201803 venue-N file\n" % len(keep))
    windows = [("october", ("20180801", "20180928"), ("20181001", "20181031")),
               ("nov-dec", ("20180801", "20180928"), ("20181101", "20181231"))]
    out = {"stage": "B14", "diagnostic_only": True,
           "diagnostic_reason":
               "the exit round restricted to the venue-N symbol set as it stood in "
               "201803, the last month before that file's coverage tripled. The "
               "restriction is a coverage fact, predates both windows, and puts "
               "this round on a population comparable to the entry round's. B14 "
               "stage two is locked, so this is evidence and not a licensed "
               "reading",
           "population_source": "panel_v2_NYSE_201803.csv",
           "population_size": len(keep), "windows": {}}
    for nm, pre, post in windows:
        res = run(pre, post, keep)
        rec = {"pre": pre, "post": post, "control_delta": {}, "cells": {}}
        t = res["bbo_shr"]["table"]
        for v in ("N", "P"):
            rec["control_delta"][v] = {"delta": t[v + "/C"]["delta"],
                                       "n": t[v + "/C"]["n"]}
        agree = 0
        for c in CELLS:
            g = {}
            for m in VENUE_CONV:
                g[m] = {"%s/%s" % (x["ctr"], x["grp"]): x["raw_gap"]
                        for x in res[m]["inequalities"]}[c]
            signs = {v < 0 for v in g.values()}
            ok = len(signs) == 1
            agree += ok
            rec["cells"][c] = {"gaps": g, "sign_agrees": ok,
                               "all_predicted_direction": ok and all(v < 0 for v in g.values())}
        rec["n_cells_sign_agree"] = agree
        rec["n_cells_agree_and_predicted"] = sum(
            1 for c in CELLS if rec["cells"][c]["all_predicted_direction"])
        out["windows"][nm] = rec
        print("  post = %s" % nm)
        print("    control delta  N %+.4f (n=%d)   P %+.4f (n=%d)"
              % (rec["control_delta"]["N"]["delta"], rec["control_delta"]["N"]["n"],
                 rec["control_delta"]["P"]["delta"], rec["control_delta"]["P"]["n"]))
        for c in CELLS:
            g = rec["cells"][c]["gaps"]
            print("    %-6s %s   %s" % (
                c, "  ".join("%+.4f" % g[m] for m in VENUE_CONV),
                "same sign" + (", predicted" if rec["cells"][c]["all_predicted_direction"] else ", against")
                if rec["cells"][c]["sign_agrees"] else "**crosses zero**"))
        print("    sign agreement %d/6, of those in the predicted direction %d\n"
              % (agree, rec["n_cells_agree_and_predicted"]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
