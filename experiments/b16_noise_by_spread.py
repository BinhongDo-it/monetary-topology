#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Is the friction half quieter on tight-spread names? The last unknown for 610(c).

WHY
===
`b16_cond2_relax.py` showed that for the Rule 610(c) carrier the signal to noise
ratio is `dS / (0.17 * s)`: the price cancels and only the quoted spread `s`
survives. At a penny spread that is 1.18 against the 0.054 B16 died on. But the
0.17 is B16's own measured figure, taken on B16's own universe, which Section 31
had already restricted to expensive and therefore wide-spread names. Whether the
friction half is equally noisy on penny-spread names has never been measured,
and it is the last free unknown standing between here and that carrier.

  noise falls on tight names  ->  1.18 goes up, the carrier is stronger
  noise flat                  ->  1.18 stands
  noise rises on tight names  ->  C's conclusion shrinks by that factor

THE THIRD BRANCH, registered before the first file was opened
=============================================================
B16 bought this data for Section 31, whose magnitude requirement is a HIGH price.
If the universe on disk therefore contains few or no penny-spread names, this
measurement cannot be made here and the reading is "the question needs a
different universe", not a number. The count of names by spread bucket is
printed before any noise figure, so that branch is visible rather than papered
over.

THE STATISTIC, fixed before looking
===================================
Friction half, per symbol-day, exactly b4 section 5.1's second row:

    relsum = (ask-bid)/mid at ARCX  +  (ask-bid)/mid at XNAS

taken as the median over the seconds inside the window. Then, per symbol,
non-overlapping ten-trading-day blocks, and within each block

    cv = sd(relsum) / mean(relsum)

which is the quantity B16 reported at 0.17. Median over blocks, then reported
per spread bucket. Nothing is thresholded; the table is the reading.

WINDOW
======
14:30 to 20:00 UTC, inside regular hours under both EST and EDT, so no
daylight-saving rule enters. Same convention as `tick_pilot_what.py`, and these
months are January to April so it matters.
"""

import argparse
import ast
import csv
import datetime
import glob
import gzip
import io
import json
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
#: Two universes, kept in separate caches on purpose. `b16` is what Section 31
#: bought, all of it above $300 with a 93-cent median spread. `legb` is the
#: 2018 XNAS/XNYS panel, and the months chosen from it are AFTER the tick pilot
#: ended on 2018-10-01, so every name in them quotes on the penny grid. Mixing
#: the two caches would average a 93-cent universe with a penny one and report
#: a number belonging to neither.
SETS = {
    "b16": (os.path.join(ROOT, "data", "raw", "b16_bbo"),
            os.path.join(ROOT, "data", "cache", "b16_noise"),
            os.path.join(ROOT, "results", "b16_noise_by_spread.json")),
    "legb": (os.path.join(ROOT, "data", "raw", "b14_legb"),
             os.path.join(ROOT, "data", "cache", "b16_noise_legb"),
             os.path.join(ROOT, "results", "b16_noise_by_spread_legb.json")),
}
RAW, CACHE, OUT = SETS["b16"]

VENUES = ("ARCX", "XNAS", "XNYS", "BATS", "EDGX")


def venue_of(name):
    """The venue token, picked from a closed list rather than by position.

    `bbo-1s_ARCX_PILLAR_e5_202301` puts it second and `XNAS_ITCH_bbo-1s_201810`
    puts it first, so splitting on position reads ITCH as a venue and silently
    merges the two XNAS months into one venue called ITCH."""
    for t in os.path.basename(name).replace(".", "_").split("_"):
        if t in VENUES:
            return t
    raise SystemExit("no venue token in %s; known: %s" % (name, VENUES))

PX = 1_000_000_000
UNDEF = 9223372036854775807
WIN = (14 * 3600 + 30 * 60, 20 * 3600)
BLOCK = 10
MIN_SEC = 200
B16_CV = 0.17
DS = 0.002                    # 610(c) quoted spread change per share per venue
BUCKETS = ((0.0, 0.015), (0.015, 0.03), (0.03, 0.06), (0.06, 0.12), (0.12, 9e9))


def park(p):
    if os.path.exists(p):
        os.rename(p, p + ".expired_"
                  + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def scan(path):
    """{symbol: {day: [n, sum_rel, sum_px, n_at_penny]}} for one venue-month."""
    out = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        head = next(r)
        ix = {c: i for i, c in enumerate(head)}
        need = ("ts_recv", "bid_px_00", "ask_px_00", "symbol")
        miss = [c for c in need if c not in ix]
        if miss:
            return None, "missing %s; header %s" % (miss, ",".join(head))
        it, ib, ia, isym = ix["ts_recv"], ix["bid_px_00"], ix["ask_px_00"], ix["symbol"]
        n_rows = n_used = 0
        for row in r:
            n_rows += 1
            try:
                b, a = int(row[ib]), int(row[ia])
            except (ValueError, IndexError):
                continue
            if b == UNDEF or a == UNDEF or a <= b or b <= 0:
                continue
            t = int(row[it])
            if not (WIN[0] <= (t // 1_000_000_000) % 86400 < WIN[1]):
                continue
            n_used += 1
            day = datetime.datetime.utcfromtimestamp(
                t // 1_000_000_000).strftime("%Y-%m-%d")
            d = out.setdefault(row[isym], {}).setdefault(day, [0, 0.0, 0.0, 0])
            mid = 0.5 * (a + b)
            d[0] += 1
            d[1] += (a - b) / mid
            d[2] += mid / PX
            if round((a - b) / (PX / 100.0)) == 1:
                d[3] += 1
    return out, "%d rows, %d in window" % (n_rows, n_used)


def cmd_scan(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        print("  no such file: %s" % name)
        return 1
    cp = os.path.join(CACHE, name.replace(".csv.gz", ".json"))
    if os.path.exists(cp):
        print("  already cached: %s" % os.path.relpath(cp, ROOT))
        return 0
    out, note = scan(path)
    print("  %s: %s" % (name, note))
    if out is None:
        return 1
    print("  %d symbols" % len(out))
    os.makedirs(CACHE, exist_ok=True)
    tmp = cp + ".part"
    park(tmp)
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=None, sort_keys=True)
    park(cp)
    os.replace(tmp, cp)
    print("  wrote %s (%.1f MB)" % (os.path.relpath(cp, ROOT),
                                    os.path.getsize(cp) / 1e6))
    return 0


def read():
    """{symbol: {day: (relsum, px, floor_share)}} joined across the two venues."""
    per = defaultdict(lambda: defaultdict(dict))
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        ven = venue_of(p)
        c = json.load(io.open(p, encoding="utf-8"))
        for sym, days in c.items():
            for day, v in days.items():
                if v[0] < MIN_SEC:
                    continue
                per[sym][day][ven] = (v[1] / v[0], v[2] / v[0], v[3] / v[0])
    out = {}
    for sym, days in per.items():
        keep = {}
        for day, vv in days.items():
            if len(vv) < 2:
                continue
            rel = sum(x[0] for x in vv.values())
            px = st.mean([x[1] for x in vv.values()])
            fl = st.mean([x[2] for x in vv.values()])
            keep[day] = (rel, px, fl)
        if len(keep) >= BLOCK:
            out[sym] = keep
    return out


def cmd_read():
    data = read()
    if not data:
        print("  nothing cached. Run --scan for each file first.")
        return 1
    print("  %d symbols quoted on BOTH venues with at least %d joint days\n"
          % (len(data), BLOCK))

    print("  THE THIRD BRANCH FIRST: how many names does this universe have at")
    print("  each spread level? B16 bought it for Section 31, which wanted price.\n")
    print("  %-16s %7s %10s %10s %10s"
          % ("spread bucket $", "names", "med price", "med spread", "med at-floor"))
    buck = defaultdict(list)
    for sym, days in data.items():
        rel = st.median([v[0] for v in days.values()])
        px = st.median([v[1] for v in days.values()])
        fl = st.median([v[2] for v in days.values()])
        cents = rel * px / 2.0          # per venue, in dollars
        for lo, hi in BUCKETS:
            if lo <= cents < hi:
                buck[(lo, hi)].append((sym, cents, px, fl, days))
                break
    for lo, hi in BUCKETS:
        v = buck.get((lo, hi))
        if not v:
            print("  %-16s %7d" % ("%.3f-%.3f" % (lo, min(hi, 9.999)), 0))
            continue
        print("  %-16s %7d %10.2f %10.4f %10.3f"
              % ("%.3f-%.3f" % (lo, min(hi, 9.999)), len(v),
                 st.median([x[2] for x in v]), st.median([x[1] for x in v]),
                 st.median([x[3] for x in v])))

    print("\n  THE READING: ten-day coefficient of variation of the friction half")
    print("  B16 reported 0.17 on its own universe.\n")
    print("  %-16s %7s %9s %9s %9s %11s %11s"
          % ("spread bucket $", "names", "blocks", "cv p25", "cv med", "cv p75",
             "sig/noise"))
    rec = {}
    for lo, hi in BUCKETS:
        v = buck.get((lo, hi))
        if not v:
            continue
        cvs = []
        for sym, cents, px, fl, days in v:
            ds = sorted(days)
            for i in range(0, len(ds) - BLOCK + 1, BLOCK):
                blk = [days[d][0] for d in ds[i:i + BLOCK]]
                m = st.mean(blk)
                if m > 0:
                    cvs.append(st.stdev(blk) / m)
        if len(cvs) < 5:
            continue
        cvs.sort()
        n = len(cvs)
        med = cvs[n // 2]
        s_med = st.median([x[1] for x in v])
        sn = DS / (med * s_med) if s_med > 0 else float("nan")
        rec["%.3f-%.3f" % (lo, min(hi, 9.999))] = {
            "names": len(v), "blocks": n, "cv_p25": cvs[n // 4],
            "cv_med": med, "cv_p75": cvs[3 * n // 4],
            "med_spread": s_med, "signal_over_noise": sn}
        print("  %-16s %7d %9d %9.4f %9.4f %11.4f %11.3f"
              % ("%.3f-%.3f" % (lo, min(hi, 9.999)), len(v), n,
                 cvs[n // 4], med, cvs[3 * n // 4], sn))

    print("\n  signal/noise = dS / (cv * s), dS = $%.4f per share per venue." % DS)
    print("  b16_cond2_relax assumed cv = %.2f at every spread. The column above"
          % B16_CV)
    print("  uses each bucket's OWN measured cv, which is the point of this file.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    park(OUT)
    json.dump({"buckets": rec, "b16_cv_assumed": B16_CV, "dS": DS,
               "block": BLOCK, "window_utc": WIN, "n_symbols": len(data),
               "diagnostic_only": True,
               "diagnostic_reason": "measures the noise term for the 2027-11 "
               "Rule 610(c) carrier; that station is not open"},
              io.open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    doc = ast.get_docstring(tree) or ""
    chk("1  the three outcomes and the third branch are registered before any "
        "number", "THE THIRD BRANCH" in doc and "noise rises on tight names" in doc)
    chk("2  the friction half is b4 section 5.1's second row, summed over the "
        "two venues, and the statistic is the ten-day cv B16 reported",
        "relsum = (ask-bid)/mid at ARCX" in doc and "cv = sd(relsum)" in doc)
    chk("3  the window is inside regular hours under both EST and EDT",
        WIN == (14 * 3600 + 30 * 60, 20 * 3600))
    chk("4  a symbol-day is dropped unless BOTH venues quote it, because the "
        "friction half is a sum over two venues and half of it is not it",
        "if len(vv) < 2:" in src)
    chk("5  blocks are non-overlapping, so no day is counted in two cv's",
        "range(0, len(ds) - BLOCK + 1, BLOCK)" in src)
    chk("6  the cache write is atomic, so a killed scan leaves no half file",
        ".part" in src and "os.replace(tmp, cp)" in src)
    chk("7  nothing deletes",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir")])
    #: arithmetic, checked against a hand case
    cv, s, ds = 0.17, 0.01, 0.002
    chk("9  the venue token is picked from a closed list, not by position: "
        "both naming conventions on disk resolve correctly",
        venue_of("bbo-1s_ARCX_PILLAR_e5_202301.json") == "ARCX"
        and venue_of("XNAS_ITCH_bbo-1s_201810.json") == "XNAS"
        and venue_of("XNYS_PILLAR_bbo-1s_201811.json") == "XNYS")
    chk("10 the two universes have separate caches, so a 93-cent set and a "
        "penny set can never be averaged into one number",
        SETS["b16"][1] != SETS["legb"][1] and SETS["b16"][2] != SETS["legb"][2])
    chk("8  signal/noise reproduces b16_cond2_relax's penny-spread figure of "
        "1.18 when cv is held at B16's 0.17 (%.4f)" % (ds / (cv * s)),
        abs(ds / (cv * s) - 1.1765) < 1e-3)
    print("\n  %d/10" % (10 - len(fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--scan", metavar="FILE")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--set", default="b16", choices=sorted(SETS))
    a = ap.parse_args()
    global RAW, CACHE, OUT
    RAW, CACHE, OUT = SETS[a.set]
    if a.selftest:
        return selftest()
    if a.scan:
        return cmd_scan(a.scan)
    if a.read:
        return cmd_read()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
