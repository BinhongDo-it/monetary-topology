#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Does (1 - at_floor)/2 actually recover the sub-tick half-spread? Tick Pilot.

WHY THIS EXISTS
===============
`tick_transfer.py` showed, in pure construction, that tau cancels in rho and
that the unobservable desired half-spread w is recoverable from the fraction of
quotes sitting at exactly one tick. If that estimator is real, three things
follow: b4 section 9 condition three relaxes from "must not quantize" to "the
quantization transfer must be computed", condition two relaxes from "common" to
"computably non-common", and B16's power failure becomes a failure of the
statistic rather than of the carrier, because a sub-tick fee change is invisible
in the quoted spread and fully visible in the floor fraction.

All three rest on the estimator. This file tests it on bought data.

THE MODEL AND ITS ONE HARD RESTRICTION
======================================
A quoter wants the band [mid - w, mid + w] and must round outward to the grid:

    bid = floor((mid - w)/tau)*tau      ask = ceil((mid + w)/tau)*tau

Write v = w/tau and let f be the mid's position inside its tick, f in (0,1).
Then the posted spread in ticks is

    k = ceil(f + v) - floor(f - v)

and working the two cases out gives, for EVERY v, a distribution on exactly
TWO ADJACENT integers:

    k_lo = max(1, ceil(2v))            P(k_lo + 1) = 2v - (k_lo - 1)

so the estimator inverts:

    v = (k_lo - 1 + P(k_lo + 1)) / 2           w = v * tau

For v < 1/2 this is the special case k_lo = 1 and v = (1 - at_floor)/2, which is
what tick_transfer.py measured. The general form does not saturate.

**Two adjacent integers is a restriction with no free parameter to absorb a
third mode.** That is the part of this test that needs no event at all.

THE READING RULE, WRITTEN BEFORE THE FIRST MONTH WAS SCANNED
============================================================
TEST A, no event needed. Per symbol-day, the share of quoted seconds landing on
the top two ADJACENT tick counts. The model says that share is 1. Registered
reading: the share is printed as a distribution across symbol-days and nothing
is thresholded. A model that puts material mass on a third, non-adjacent count
is wrong, and the estimator built on it has no basis.

TEST B, the invariance. The pilot ended on 2018-09-28 and quoting reverted to a
penny on 2018-10-01. Treated names (G1, G2, G3) see tau go 0.05 -> 0.01.
Control names (C) see no tick change at all. The estimator claims to recover w,
which is measured in dollars and has no reason to care what the grid is, so:

    w in DOLLARS is invariant across 2018-10-01 for treated names.

REGISTERED CAVEAT, and it is load bearing. Ending the pilot may also have moved
w economically; the published work on the pilot found the wider tick changed
liquidity provision. So a move in w for treated names is NOT by itself an
estimator failure. What would be an estimator failure is w moving by roughly
the tick ratio, five, which is what happens if the estimator is really just
reporting the tick back. **The control group carries no tick change, so it
separates a real change in w from an artefact of tau.**

THREE READINGS, all decidable by eye:
  A fails                      -> the model is wrong, everything above dies here
  A passes, w flat on treated  -> the estimator recovers w; the relaxations stand
  A passes, w scales with tau  -> the estimator is reporting the grid, not w

THE TICK IS MEASURED, NOT ASSUMED
=================================
The pilot's group assignment says which names should quote in nickels, but the
rule had exceptions and the BBO can still show sub-nickel prices. So this file
does not take tau from the assignment file. It measures, per symbol-day, the
share of quoted prices that are exact multiples of five cents, and reports that
next to the assignment. The assignment is a label to check against, not an
input to the arithmetic.

WINDOW
======
14:30 to 20:00 UTC, which lies inside regular trading hours under both EST and
EDT, so no daylight-saving rule enters and no month is treated differently from
another. Registered before scanning.
"""

import argparse
import ast
import collections
import csv
import datetime
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "b14_legb")
ASSIGN = os.path.join(ROOT, "data", "raw")
CACHE = os.path.join(ROOT, "data", "cache", "tick_pilot")
RESULTS = os.path.join(ROOT, "results")

PX = 1_000_000_000                    # Databento fixed point, 1e-9 dollars
CENT = PX // 100
NICKEL = 5 * CENT
UNDEF = 9223372036854775807           # INT64_MAX sentinel
WIN = (14 * 3600 + 30 * 60, 20 * 3600)   # seconds past UTC midnight
PILOT_END = "2018-10-01"              # quoting reverts to a penny
TREATED = ("G1", "G2", "G3")
VENUES = {"XNAS": "XNAS_ITCH_bbo-1s", "XNYS": "XNYS_PILLAR_bbo-1s"}


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def park(path):
    if os.path.exists(path):
        os.rename(path, path + ".expired_"
                  + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


#: The treatment label is "was in a treated group on the pilot's last day".
ASOF = "20180928"


def load_groups(asof=ASOF):
    """{ticker: group} as the assignment stood on `asof` (YYYYMMDD).

    Date-aware on purpose, and this is the second thing this file got wrong.
    `TSPilotChanges20181001.txt` is the CUMULATIVE change log exported on the
    day the pilot ended, so 343 of its 1683 rows carry Deleted_Date 20181001,
    and that date is the PILOT TERMINATING, not those names leaving it early.
    Applying the deletions without reading their dates removed every name still
    in a treated group on the last day, which is exactly the treated arm: the
    XNAS universe came back 47 control, 1 treated, 60 unlabelled, and all 60 of
    the unlabelled were G1, G2 or G3 in the base table.

    It was not caught by reading the file. It was caught by the grid measured
    off the quotes: those 60 names sat on a five-cent multiple in every second
    of every day, p10 = p50 = p90 = 1.000, which no penny-grid name does. That
    is the whole reason the grid is measured here instead of taken from the
    label."""
    g = {}
    p = os.path.join(ASSIGN, "Tick_Pilot_Test_Group_Assignments.txt")
    with open(p, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i == 0:
                continue
            f = line.rstrip("\n").split("|")
            if len(f) >= 5 and f[0]:
                g[f[0].strip()] = f[4].strip()
    changes = []
    p2 = os.path.join(ASSIGN, "TSPilotChanges20181001.txt")
    if os.path.exists(p2):
        with open(p2, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i == 0:
                    continue
                f = line.rstrip("\n").split("|")
                if len(f) >= 7 and f[1]:
                    changes.append({"post": f[0].strip(), "tic": f[1].strip(),
                                    "eff": f[4].strip(), "del": f[5].strip(),
                                    "grp": f[6].strip()})
    for c in sorted(changes, key=lambda x: (x["post"], x["tic"])):
        if c["del"] and c["del"] <= asof:
            g.pop(c["tic"], None)
        elif c["grp"] and (not c["eff"] or c["eff"] <= asof):
            g[c["tic"]] = c["grp"]
    return g


def utc_sec(ts_ns):
    return (int(ts_ns) // 1_000_000_000) % 86400


def utc_day(ts_ns):
    return datetime.datetime.utcfromtimestamp(int(ts_ns) // 1_000_000_000).strftime("%Y-%m-%d")


def scan_month(venue, month):
    """{symbol: {day: {"k": {ticks: n}, "n5": n, "n": n, "px": sum}}}

    One pass. Both grids are counted, penny and nickel, so the tick in force is
    read off the data rather than taken from the assignment file."""
    path = os.path.join(RAW, "%s_%s.csv.gz" % (VENUES[venue], month))
    if not os.path.exists(path):
        return None, "no file: %s" % os.path.relpath(path, ROOT)
    out = {}
    n_rows = n_used = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        head = next(r)
        ix = {c: i for i, c in enumerate(head)}
        need = ("ts_recv", "bid_px_00", "ask_px_00", "symbol")
        miss = [c for c in need if c not in ix]
        if miss:
            return None, "missing columns %s; header was %s" % (miss, ",".join(head))
        it, ib, ia, isym = ix["ts_recv"], ix["bid_px_00"], ix["ask_px_00"], ix["symbol"]
        for row in r:
            n_rows += 1
            try:
                b, a = int(row[ib]), int(row[ia])
            except (ValueError, IndexError):
                continue
            if b == UNDEF or a == UNDEF or a <= b or b <= 0:
                continue
            t = int(row[it])
            s = utc_sec(t)
            if not (WIN[0] <= s < WIN[1]):
                continue
            n_used += 1
            sym = row[isym]
            day = utc_day(t)
            d = out.setdefault(sym, {}).setdefault(day, {"k": {}, "n5": 0,
                                                         "n": 0, "px": 0})
            spread = a - b
            #: both grids counted; which one is in force is a reading, not an input
            k1 = (spread + CENT - 1) // CENT
            d["k"][str(k1)] = d["k"].get(str(k1), 0) + 1
            if b % NICKEL == 0 and a % NICKEL == 0:
                d["n5"] += 1
            d["n"] += 1
            d["px"] += (a + b) // 2
    return out, "%d rows, %d inside the window" % (n_rows, n_used)


#: registered before scanning: a symbol-day is on the nickel grid when at least
#: this share of its quoted seconds has BOTH sides on a five-cent multiple. The
#: distribution of the share is printed so the choice of 0.90 is visible rather
#: than load bearing, and the assignment file is printed beside it as a check.
NICKEL_SHARE = 0.90
MIN_SEC = 200          # a symbol-day with fewer quoted seconds carries no shape


def tick_of(day_rec):
    """(tau_in_dollars, share_on_nickel_grid). Measured, not assumed."""
    f5 = day_rec["n5"] / max(1, day_rec["n"])
    return (0.05 if f5 >= NICKEL_SHARE else 0.01), f5


def estimate(day_rec):
    """(v, w_dollars, share_on_top_two_adjacent, k_lo, n). None if too thin.

    The histogram arrives in PENNY units because that is what the raw prices
    are; it is divided into the tick in force before the two-adjacent test, so
    a nickel-grid day is read on the nickel grid."""
    n = day_rec["n"]
    if n < MIN_SEC:
        return None
    tau, _f5 = tick_of(day_rec)
    step = 5 if tau == 0.05 else 1
    h = collections.Counter()
    for k, c in day_rec["k"].items():
        h[max(1, (int(k) + step - 1) // step)] += c
    if not h:
        return None
    #: the best adjacent PAIR, not the two biggest bars. Two big bars that are
    #: not adjacent is exactly the shape the model forbids, and picking them by
    #: size would hide it.
    ks = sorted(h)
    best = None
    for k in ks:
        s = h[k] + h.get(k + 1, 0)
        if best is None or s > best[0]:
            best = (s, k)
    share, k_lo = best[0] / n, best[1]
    pair = h[k_lo] + h.get(k_lo + 1, 0)
    p = h.get(k_lo + 1, 0) / pair if pair else 0.0
    v = (k_lo - 1 + p) / 2.0
    return v, v * tau, share, k_lo, n


def cache_path(venue, month):
    return os.path.join(CACHE, "%s_%s.json" % (venue, month))


def cmd_hist(venue, month):
    if venue not in VENUES:
        print("  venue must be one of %s" % ", ".join(sorted(VENUES)))
        return 1
    cp = cache_path(venue, month)
    if os.path.exists(cp):
        c = json.load(open(cp, encoding="utf-8"))
        print("  already cached: %s, %d symbols. Nothing rescanned."
              % (os.path.relpath(cp, ROOT), len(c["sym"])))
        return 0
    out, note = scan_month(venue, month)
    print("  %s %s: %s" % (venue, month, note))
    if out is None:
        return 1
    days = sorted({d for s in out.values() for d in s})
    print("  %d symbols, %d days (%s .. %s)"
          % (len(out), len(days), days[0] if days else "-", days[-1] if days else "-"))
    os.makedirs(CACHE, exist_ok=True)
    #: written to a side file and moved into place, so a run killed partway
    #: leaves no half-written cache for the next run to read as complete. The
    #: bigger months take longer than one impatient timeout.
    tmp = cp + ".part"
    park(tmp)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"venue": venue, "month": month, "at": now_iso(), "sym": out},
                  fh, indent=None, sort_keys=True)
    park(cp)
    os.replace(tmp, cp)
    print("  wrote %s  (%.1f MB)"
          % (os.path.relpath(cp, ROOT), os.path.getsize(cp) / 1e6))
    return 0


def load_cache():
    recs = []
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        c = json.load(open(p, encoding="utf-8"))
        for sym, days in c["sym"].items():
            for day, rec in days.items():
                recs.append((c["venue"], sym, day, rec))
    return recs


def cmd_test_a(nbin):
    """The restriction that needs no event: two adjacent tick counts, no third."""
    recs = load_cache()
    if not recs:
        print("  no cache. Run --hist VENUE MONTH first.")
        return 1
    g = load_groups()
    print("  %d symbol-days cached, %d symbols in the pilot assignment table\n"
          % (len(recs), len(g)))

    print("  first, the grid is READ rather than assumed. Share of quoted")
    print("  seconds with both sides on a five-cent multiple, by assignment:\n")
    buck = collections.defaultdict(list)
    for _v, sym, day, rec in recs:
        if rec["n"] < MIN_SEC:
            continue
        grp = g.get(sym, "?")
        arm = "treated" if grp in TREATED else ("control" if grp == "C" else "unassigned")
        era = "pilot on" if day < PILOT_END else "pilot off"
        buck[(arm, era)].append(rec["n5"] / rec["n"])
    print("  %-22s %7s %8s %8s %8s %8s"
          % ("arm | era", "n", "p10", "p50", "p90", ">=0.90"))
    for k in sorted(buck):
        v = sorted(buck[k])
        n = len(v)
        print("  %-22s %7d %8.3f %8.3f %8.3f %7.1f%%"
              % (" | ".join(k), n, v[n // 10], v[n // 2], v[9 * n // 10],
                 100.0 * sum(1 for x in v if x >= NICKEL_SHARE) / n))

    print("\n  TEST A. Share of quoted seconds on the top two ADJACENT tick")
    print("  counts. The model has no free parameter that can absorb a third")
    print("  mode, so it says this share is 1.000.\n")
    shares = collections.defaultdict(list)
    klo = collections.defaultdict(collections.Counter)
    for _v, sym, day, rec in recs:
        e = estimate(rec)
        if e is None:
            continue
        grp = g.get(sym, "?")
        arm = "treated" if grp in TREATED else ("control" if grp == "C" else "unassigned")
        era = "pilot on" if day < PILOT_END else "pilot off"
        shares[(arm, era)].append(e[2])
        klo[(arm, era)][e[3]] += 1
    print("  %-22s %7s %8s %8s %8s %8s %8s"
          % ("arm | era", "n", "p10", "p25", "p50", "p90", ">=0.95"))
    for k in sorted(shares):
        v = sorted(shares[k])
        n = len(v)
        print("  %-22s %7d %8.3f %8.3f %8.3f %8.3f %7.1f%%"
              % (" | ".join(k), n, v[n // 10], v[n // 4], v[n // 2],
                 v[9 * n // 10], 100.0 * sum(1 for x in v if x >= 0.95) / n))
    print("\n  and where the lower of the two sits, in ticks of the grid in force:")
    for k in sorted(klo):
        tot = sum(klo[k].values())
        top = ", ".join("%d:%.1f%%" % (kk, 100.0 * c / tot)
                        for kk, c in sorted(klo[k].items())[:6])
        print("  %-22s %s" % (" | ".join(k), top))
    return 0


def cmd_test_b():
    """The invariance: w in dollars across 2018-10-01, treated against control."""
    recs = load_cache()
    if not recs:
        print("  no cache. Run --hist VENUE MONTH first.")
        return 1
    g = load_groups()
    per = collections.defaultdict(lambda: {"pre": [], "post": [],
                                           "tau_pre": [], "tau_post": []})
    #: keyed on (venue, symbol), not symbol. A name quoted on both venues would
    #: otherwise have one venue's pre days averaged against the other's post
    #: days, and with the venues cached one month at a time that is not
    #: hypothetical: it happens the moment the two caches cover different months.
    for ven, sym, day, rec in recs:
        e = estimate(rec)
        if e is None:
            continue
        tau, _f5 = tick_of(rec)
        side = "pre" if day < PILOT_END else "post"
        per[(ven, sym)][side].append(e[1])
        per[(ven, sym)]["tau_" + side].append(tau)

    med = lambda v: sorted(v)[len(v) // 2] if v else None            # noqa: E731
    rows = collections.defaultdict(list)
    for (ven, sym), d in per.items():
        if len(d["pre"]) < 5 or len(d["post"]) < 5:
            continue
        grp = g.get(sym, "?")
        arm = "treated" if grp in TREATED else ("control" if grp == "C" else "unassigned")
        wp, wq = med(d["pre"]), med(d["post"])
        tp, tq = med(d["tau_pre"]), med(d["tau_post"])
        if not wp:
            continue
        rows[arm].append({"sym": sym, "venue": ven, "group": grp,
                          "w_pre": wp, "w_post": wq,
                          "w_ratio": wq / wp, "tau_pre": tp, "tau_post": tq,
                          "tau_ratio": tq / tp, "n_pre": len(d["pre"]),
                          "n_post": len(d["post"])})

    print("  TEST B. w is in DOLLARS and has no reason to care what the grid is.")
    print("  Registered before scanning:")
    print("    w_ratio near 1.00   the estimator recovers w; the relaxations stand")
    print("    w_ratio near tau_ratio   the estimator is reporting the grid back\n")
    print("  %-12s %6s %10s %10s %10s %10s %10s"
          % ("arm", "n", "tau_ratio", "w_pre", "w_post", "w_ratio", "p10..p90"))
    out = {}
    for arm in ("treated", "control", "unassigned"):
        r = rows.get(arm)
        if not r:
            continue
        wr = sorted(x["w_ratio"] for x in r)
        n = len(wr)
        out[arm] = {"n": n, "tau_ratio": med([x["tau_ratio"] for x in r]),
                    "w_pre": med([x["w_pre"] for x in r]),
                    "w_post": med([x["w_post"] for x in r]),
                    "w_ratio_p10": wr[n // 10], "w_ratio_med": wr[n // 2],
                    "w_ratio_p90": wr[9 * n // 10]}
        print("  %-12s %6d %10.3f %10.5f %10.5f %10.3f   %.3f .. %.3f"
              % (arm, n, out[arm]["tau_ratio"], out[arm]["w_pre"],
                 out[arm]["w_post"], out[arm]["w_ratio_med"],
                 out[arm]["w_ratio_p10"], out[arm]["w_ratio_p90"]))

    t, c = out.get("treated"), out.get("control")
    if t and c:
        print("\n  the reading:")
        print("    treated tau moved by %.3f; if the estimator were the grid,"
              % t["tau_ratio"])
        print("    treated w_ratio would sit near %.3f. It sits at %.3f."
              % (t["tau_ratio"], t["w_ratio_med"]))
        print("    control saw no tick change (tau_ratio %.3f) and its w_ratio"
              % c["tau_ratio"])
        print("    is %.3f, which is what an ordinary two-month drift looks like"
              % c["w_ratio_med"])
        print("    on this sample. Treated over control: %.3f"
              % (t["w_ratio_med"] / c["w_ratio_med"]))
        d_grid = abs(t["w_ratio_med"] - t["tau_ratio"])
        d_one = abs(t["w_ratio_med"] - c["w_ratio_med"])
        print("\n    distance to 'estimator is the grid'  %.3f" % d_grid)
        print("    distance to 'estimator recovers w'   %.3f" % d_one)
        print("    -> %s" % ("the estimator RECOVERS w" if d_one < d_grid
                             else "the estimator is REPORTING THE GRID"))
    os.makedirs(RESULTS, exist_ok=True)
    dst = os.path.join(RESULTS, "tick_pilot_what.json")
    park(dst)
    json.dump({"at": now_iso(), "pilot_end": PILOT_END, "window_utc": WIN,
               "nickel_share": NICKEL_SHARE, "min_sec": MIN_SEC,
               "arms": out, "per_symbol": {a: rows[a] for a in rows}},
              open(dst, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(dst, ROOT))
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)

    #: the algebra, checked by brute force rather than trusted
    def sim(v, nf=2000):
        h = collections.Counter()
        for i in range(nf):
            f = (i + 0.5) / nf
            lo = -(-(f - v) // 1)
            import math as _m
            k = _m.ceil(f + v) - _m.floor(f - v)
            h[int(k)] += 1
            del lo
        return h
    for v in (0.05, 0.2, 0.49, 0.7, 1.3, 2.4):
        h = sim(v)
        ks = sorted(h)
        ok = len(ks) <= 2 and (len(ks) == 1 or ks[1] - ks[0] == 1)
        chk("1.%s  v=%.2f puts all mass on adjacent tick counts %s"
            % (str(v).replace(".", ""), v, ks), ok)
        k_lo = ks[0]
        p = h.get(k_lo + 1, 0) / sum(h.values())
        chk("2.%s  and the inversion returns v: (k_lo-1+p)/2 = %.4f"
            % (str(v).replace(".", ""), (k_lo - 1 + p) / 2.0),
            abs((k_lo - 1 + p) / 2.0 - v) < 0.01)

    rec = {"k": {"1": 700, "2": 300}, "n5": 0, "n": 1000, "px": 0}
    e = estimate(rec)
    chk("3  a penny-grid day with 70% at one cent gives v=0.15 and w=$0.0015",
        abs(e[0] - 0.15) < 1e-9 and abs(e[1] - 0.0015) < 1e-9 and e[2] == 1.0)
    rec5 = {"k": {"5": 700, "10": 300}, "n5": 1000, "n": 1000, "px": 0}
    e5 = estimate(rec5)
    chk("4  the SAME shape on the nickel grid gives the same v but five times "
        "the w, which is exactly the confusion this file exists to resolve",
        abs(e5[0] - 0.15) < 1e-9 and abs(e5[1] - 0.0075) < 1e-9)

    #: the third-mode case: the model forbids it and estimate() must report it
    bad = {"k": {"1": 400, "2": 200, "9": 400}, "n5": 0, "n": 1000, "px": 0}
    eb = estimate(bad)
    chk("5  a day with a third, non-adjacent mode is reported at share 0.600, "
        "not silently absorbed",
        abs(eb[2] - 0.6) < 1e-9)
    chk("6  the best ADJACENT pair is taken, not the two tallest bars: 1 and 2 "
        "beat 9 alone even though 9 is as tall as 1",
        eb[3] == 1)

    chk("7  the tick is read from the data: a day with every quote on a "
        "five-cent multiple is called a nickel day, one with none is a penny day",
        tick_of({"n5": 1000, "n": 1000})[0] == 0.05
        and tick_of({"n5": 0, "n": 1000})[0] == 0.01)
    chk("8  a symbol-day thinner than %d quoted seconds returns nothing rather "
        "than a shape read off a handful of points" % MIN_SEC,
        estimate({"k": {"1": 10}, "n5": 0, "n": 10, "px": 0}) is None)

    g = load_groups()
    cnt = collections.Counter(g.values())
    #: The base table has 2395 assigned names. The change log deletes names that
    #: left the pilot over its two years, mostly delistings and mergers, and
    #: applying it leaves 1940: control 1145, and 268 / 263 / 263 in G1 / G2 /
    #: G3. Asserting the post-change-log numbers rather than the base ones is
    #: the point of the assertion; the base numbers would pass while the change
    #: log silently did nothing.
    #: The change log must be applied BY DATE. Asserting the totals alone would
    #: pass for the broken version too, because that version also produced a
    #: plausible-looking 1145 control and 794 treated. What separates them is
    #: that the deletions dated 20181001 are the pilot ending: they must not
    #: bite on the last pilot day and must bite after it.
    g_end = load_groups("20180928")
    g_after = load_groups("20181201")
    t_end = sum(1 for v in g_end.values() if v in TREATED)
    t_after = sum(1 for v in g_after.values() if v in TREATED)
    chk("9  the change log is applied BY DATE: on the pilot's last day %d names "
        "are in a treated arm, and after the 20181001 deletions bite only %d "
        "are, so the terminating deletions are not mistaken for early exits"
        % (t_end, t_after),
        t_end > 1000 and cnt["C"] > 1000
        #: the difference must BE the terminating deletions, not merely be
        #: large. 1136 - 794 = 342, against 343 rows dated 20181001 of which
        #: one is a control name. An inequality here would pass for a wrong
        #: date rule that happened to drop a similar number.
        #: DISTINCT tickers, not rows. One ticker carries two rows dated
        #: 20181001, so the row count is 343 against 342 names, and asserting
        #: the row count fails by exactly one. Counting the object rather than
        #: the lines that mention it.
        and t_end - t_after == len({
            f[1].strip()
            for line in open(os.path.join(ASSIGN, "TSPilotChanges20181001.txt"),
                             encoding="utf-8", errors="replace").read().splitlines()[1:]
            for f in [line.split("|")]
            if len(f) >= 7 and f[5].strip() == "20181001" and f[6].strip() in TREATED}))

    chk("10 the window is inside regular hours under BOTH EST and EDT, so no "
        "daylight-saving rule enters and no month is read differently",
        WIN == (14 * 3600 + 30 * 60, 20 * 3600))
    chk("11 nothing here deletes; park() is the only disposal",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir")])
    doc = ast.get_docstring(tree) or ""
    chk("12 the reading rule, the caveat about w moving on its own, and the "
        "three readings are in the docstring rather than in a chat log",
        "READING RULE" in doc and "REGISTERED CAVEAT" in doc
        and "THREE READINGS" in doc)
    n = 12 + 12
    print("\n  %d/%d" % (n - len(fails), n))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hist", nargs=2, metavar=("VENUE", "MONTH"))
    ap.add_argument("--testa", action="store_true")
    ap.add_argument("--testb", action="store_true")
    ap.add_argument("--bins", type=int, default=10)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.hist:
        return cmd_hist(a.hist[0], a.hist[1])
    if a.testa:
        return cmd_test_a(a.bins)
    if a.testb:
        return cmd_test_b()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
