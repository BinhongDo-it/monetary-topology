"""The spread level, month by month, for a fixed population.

Every reading in this stage is a difference between two windows, and a difference
cannot say whether one of its windows is unusual. So this prints the level rather
than the difference: for a fixed set of symbols, the median of log(spread ratio) in
each month from 201604 to 201903.

The full-population run is what found the coverage break. Venue N's control level
steps +0.1085 across 201803 to 201804 while its symbol count goes 301 to 681, and
that step is the whole of what made the exit round unreadable. On --pop pre804 the
same step is +0.0021 on a count of 301 to 299.

The reading this file was written to test, that the shared pre window was what both
post windows were reacting to, is not what the series shows. The pre window months
201808 and 201809 read -2.280 and -2.314 against an in-pilot plateau of -2.185 to
-2.412 on the restricted population. The cause was the population.

The population is fixed by the published group list rather than by each month's
own label. Reading the label per month would silently change the population on
2018-10, when every pilot security opens in the control group, and a series whose
membership changes at the moment of interest cannot be read across that moment.

No threshold, no verdict. The output is the series.

THE POPULATION SWITCH

--pop pre804 restricts to the 618 symbols in the 201803 venue-N file, the same set
the restricted exit round and its band stand on, so that the picture and the
readings are of the same securities. --pop full is the default and reproduces the
series already in results/b14_level_series.json field for field, which the selftest
checks by running rather than by reading the source.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate0 as G             # noqa: E402
import b14_gate_exit as X         # noqa: E402
import b14_gate_exit_pre804 as R  # noqa: E402  the 201803 population, imported not copied

CACHE = X.CACHE
MEASURES = X.MEASURES
median = G.median
canon = X.canon


GROUPS = ("C", "G1", "G2", "G3")
OUT = os.path.join(ROOT, "results", "b14_level_series_pre804.json")


def series(measure="bbo_shr", keep=None):
    idx = {m[0]: m for m in MEASURES}
    name, inum, idens, _ = idx[measure]
    auth = dict(G.load_authoritative())
    per = {}                      # (month, ctr, grp) -> {sym: [log v, ...]}
    for fn in sorted(f for f in os.listdir(CACHE)
                     if f.startswith("panel_v2_") and f.endswith(".csv")):
        with open(os.path.join(CACHE, fn)) as fh:
            assert fh.readline().startswith("date,ctr,symbol,test_group,")
            for line in fh:
                if line.startswith("#"):
                    continue
                p = line.rstrip("\n").split(",")
                sym = canon(p[2])
                if keep is not None and sym not in keep:
                    continue
                grp = auth.get(sym)
                if grp is None:
                    continue
                den = sum(float(p[i]) for i in idens)
                if den <= 0:
                    continue
                v = float(p[inum]) / den
                if v <= 0:
                    continue
                import math
                per.setdefault((p[0][:6], p[1], grp), {}).setdefault(sym, []).append(math.log(v))
    out = {}
    for k, syms in per.items():
        vals = [median(xs) for xs in syms.values() if xs]
        if vals:
            out[k] = (median(vals), len(vals))
    return out


def key(m, c, g):
    return "%s|%s|%s" % (m, c, g)


def selftest():
    bad = []

    def chk(msg, ok):
        print("  %-4s %s" % ("ok" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    chk("the population is imported from the restricted exit round, not copied",
        R.population.__module__ == "b14_gate_exit_pre804")
    chk("the group list is the external one, so membership cannot change in 201810",
        G.load_authoritative.__module__ == "b14_gate0")
    # Rule 19, read by running: the default must be the series already on disk.
    p = os.path.join(ROOT, "results", "b14_level_series.json")
    if not os.path.exists(p):
        chk("the full-population series is on disk to reproduce against", False)
    else:
        prev = json.load(open(p, encoding="utf-8"))["level_bbo_shr"]
        now = series("bbo_shr")
        got = {key(m, c, g): [round(v, 12), n] for (m, c, g), (v, n) in now.items()}
        want = {k: [round(v["median_log_ratio"], 12), v["n_symbols"]]
                for k, v in prev.items()}
        diff = [k for k in sorted(set(got) | set(want)) if got.get(k) != want.get(k)]
        chk("default reproduces all %d cells of the series on disk: %s"
            % (len(want), diff[:4] or "no differences"), not diff)
    print("\nselftest: %s" % ("PASS" if not bad else "FAIL (%d)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", default="bbo_shr")
    ap.add_argument("--pop", choices=("full", "pre804"), default="full")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="write the restricted series to results/ (pre804 only)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    keep = R.population() if a.pop == "pre804" else None
    s = series(a.measure, keep)
    months = sorted({k[0] for k in s})
    print("measure %s   population %s   groups from the published list\n"
          % (a.measure, "all" if keep is None else "%d symbols" % len(keep)))
    head = "  month  "
    for c in ("N", "P"):
        for g in GROUPS:
            head += "%-11s" % ("%s/%s" % (c, g))
        head += " | %-7s %-7s %-7s |" % ("g1-c", "g2-c", "g3-c")
    print(head)
    rows = {}
    for m in months:
        row, rec = "", {}
        for c in ("N", "P"):
            lv = {}
            for g in GROUPS:
                v = s.get((m, c, g))
                lv[g] = v[0] if v else None
                row += "%-11s" % ("%+.3f" % v[0] if v else "-")
            row += " |"
            for g in ("G1", "G2", "G3"):
                d = None if (lv[g] is None or lv["C"] is None) else lv[g] - lv["C"]
                row += " %-7s" % ("%+.3f" % d if d is not None else "-")
                rec["%s/%s-C" % (c, g)] = d
            row += " |"
            rec["%s/C" % c] = lv["C"]
        rows[m] = rec
        mark = ""
        if m in ("201808", "201809"):
            mark = "  pre window"
        elif m == "201809":
            mark = "  pilot ends 09-28"
        elif m == "201810":
            mark = "  first month with the tick back at a penny"
        print("  %s %s%s" % (m, row, mark))
    if a.write and a.pop == "pre804":
        out = {"stage": "B14", "diagnostic_only": True,
               "diagnostic_reason":
                   "the spread level month by month on the 618 symbols the "
                   "restricted exit round and its bands stand on, group membership "
                   "fixed by the published list so it cannot change in 201810 when "
                   "every pilot security opens in the control condition. A picture, "
                   "not a criterion: no threshold is drawn on it. B14 stage two is "
                   "locked",
               "measure": a.measure, "population": "pre804",
               "population_size": len(keep),
               "level": {key(m, c, g): {"median_log_ratio": v[0], "n_symbols": v[1]}
                         for (m, c, g), v in s.items()},
               "gap_to_control": rows}
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
        print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
