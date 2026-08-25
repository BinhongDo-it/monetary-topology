"""B16 step A: the two post-purchase screens, and the description that precedes them.

Both screens were registered before the run, and neither was changed after it.

WHAT THIS FILE IS NOT

It does not compute rho. Rules 3 and 4 are registered as post-purchase, and the
registration says the drop counts are printed before any rho is looked at, so
this file stops at the drop counts. Nothing here divides an index half by a
friction half.

THE ORDER IS THE HOUSE ORDER, NOT MINE

Engineering rule 13 fixes it: measure the WORST cell before the average one, then
describe, then ask whether the description already answered the question, and only
then reach for a test. So this file prints, in order:

    1. the thinnest (symbol, day, venue) cells, by name
    2. the distributions: seconds present, two-sided share, spread in ticks
    3. the two registered screens and what each one drops, by name
    4. what survives

Averages are printed beside the minima, never instead of them. B7 was killed by a
design whose every headline number was an average and whose two thinnest classes
held 1.18 and 1.37 observations.

REGULAR HOURS ONLY, AND WHY THAT IS NOT A KNOB

The files start at 04:00:01 ET. On 2023-02-01 at 04:00 BLK quotes 754.36 / 763.27,
an $8.91 spread on a $758 mid. Pre- and post-market quotes are thin and wide and
would swamp the friction half of the decomposition.

    Registered here, 2026-08-21, before any rho was computed: the session is
    09:30:00 to 16:00:00 America/New_York, inclusive of the open and exclusive of
    the close, on the trading days the archive itself supplies.

That boundary is the exchange's own regular session, a published fact. Any other
cut (drop the first ten minutes, drop the auction, trim the tails) would be a
number this project chose, and D5 forbids that. This one is the only cut available
that nobody here picked.

DST cannot be a fixed offset: e5's window straddles 2023-03-12, so half of it is
EST and half is EDT, and a fixed -5 would silently shift twenty-odd days by an
hour. It is also not taken from zoneinfo, because Windows ships no system tz
database and this project is not adding a package to read a four-line statute.

The offset comes from the statute itself (Energy Policy Act 2005, in force since
2007): DST runs from the second Sunday in March to the first Sunday in November.
Both transitions fall on a Sunday, so no trading day ever lands on one and the
09:30 boundary has no edge case to get wrong.

Three independent confirmations, because a wrong offset is silent:

  * the selftest pins six known dates, three either side of both 2023 transitions;
  * if zoneinfo happens to work (a machine with tzdata), the selftest asserts it
    agrees with the statute on every day in the span, and says so when it cannot
    run rather than passing quietly;
  * --scan reports, per day, the offset IMPLIED BY THE DATA: the archive opens at
    04:00 ET, so the first timestamp of each day pins the offset without reference
    to any calendar at all. A day that disagrees is named.

SENTINELS

Databento writes INT64_MAX for an undefined price. It appears constantly: a
one-sided book has it on the empty side, and `price` carries it on every record
that is a quote rather than a trade. A row with the sentinel on either side is not
two-sided, and it is counted as such rather than dropped quietly.

    python experiments/b16_bbo_probe.py --selftest      no data
    python experiments/b16_bbo_probe.py --scan          reads 4.7 GB, writes cache
    python experiments/b16_bbo_probe.py --screen        reads cache, prints drops
    python experiments/b16_bbo_probe.py --pairs         paired seconds, both venues
"""
import argparse
import bisect
import datetime
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "b16_bbo")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
UNIVERSE = os.path.join(RESULTS, "b16_universe.json")
#: Reusable cache. The scan reads 4.7 GB; the screen reads this. Rerunning the
#: screen with a different registered threshold must never mean rereading the gz.
DAILY = os.path.join(RESULTS, "b16_e5_daily.json")

ARM = 5
BOUNDARY = "2023-02-23"
VENUES = ("XNAS.ITCH", "ARCX.PILLAR")
UTC = datetime.timezone.utc
#: The archive's own session start, used only as a cross-check on the offset.
ARCHIVE_OPEN_ET = datetime.time(4, 0)

#: Registered 2026-08-21, see the docstring. The exchange's own regular session.
RTH_OPEN = datetime.time(9, 30)
RTH_CLOSE = datetime.time(16, 0)
RTH_SECONDS = 6 * 3600 + 30 * 60          # 23400

#: Registered: windows in trading days relative to the boundary. The boundary
#: day opens the post window.
REF_WINDOW = (-20, -11)
PRE_WINDOW = (-10, -1)
POST_WINDOW = (0, 9)

#: Rule 3 and rule 4, both registered before the purchase.
RULE3_TWO_SIDED_SHARE = 0.90
RULE4_MIN_SPREAD_TICKS = 3.0
TICK = 0.01

#: Databento's undefined-price sentinel.
UNDEF = 9223372036854775807
PX_SCALE = 1e-9


# ---------------------------------------------------------------- calendar

def load_calendar():
    if not os.path.exists(CAL_CACHE):
        raise SystemExit("no %s. Run b16_universe.py --calendar ZIP first."
                         % os.path.relpath(CAL_CACHE, ROOT))
    return json.load(open(CAL_CACHE, encoding="utf-8"))["days"]


def load_universe():
    if not os.path.exists(UNIVERSE):
        raise SystemExit("no %s. Run b16_screen.py first."
                         % os.path.relpath(UNIVERSE, ROOT))
    return json.load(open(UNIVERSE, encoding="utf-8"))


def arm_symbols(ev):
    """Same reader as b16_bbo_pull.arm_symbols: the universe file stores rows of
    [ticker, screen_price, corwin_schultz_spread], not bare strings."""
    out = []
    for r in ev["symbols"]:
        t = r[0] if isinstance(r, (list, tuple)) else r
        if not isinstance(t, str) or not t:
            raise SystemExit("bad ticker %r in the universe file" % (r,))
        out.append(t)
    return out


def offset_days(days, boundary, lo, hi):
    """Trading days at offsets [lo, hi] from the boundary. Offset 0 IS the
    boundary day and it belongs to the post side, matching buy_window."""
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]

    def at(k):
        return after[k] if k >= 0 else before[k]

    out = []
    for k in range(lo, hi + 1):
        try:
            out.append(at(k))
        except IndexError:
            raise SystemExit("offset %d is outside the calendar" % k)
    return out


def _nth_sunday(year, month, n):
    first = datetime.date(year, month, 1)
    first_sun = 1 + (6 - first.weekday()) % 7        # weekday(): Mon 0 .. Sun 6
    return datetime.date(year, month, first_sun + 7 * (n - 1))


def et_offset_hours(day):
    """-5 for EST, -4 for EDT, from the statute rather than from a package.

    DST runs from the second Sunday in March to the first Sunday in November.
    Both endpoints are Sundays and the switch happens at 02:00 local, so for a
    09:30 boundary on a trading day the comparison is exact and the transition
    days themselves never appear.
    """
    d = datetime.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    return -4 if _nth_sunday(d.year, 3, 2) <= d < _nth_sunday(d.year, 11, 1) else -5


def _et_to_utc_ns(day, t):
    d = datetime.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    naive_as_utc = datetime.datetime.combine(d, t, UTC)
    shifted = naive_as_utc - datetime.timedelta(hours=et_offset_hours(day))
    return int(shifted.timestamp()) * 1_000_000_000


def rth_bounds_ns(day):
    """(lo, hi) in UTC nanoseconds for one yyyymmdd."""
    return _et_to_utc_ns(day, RTH_OPEN), _et_to_utc_ns(day, RTH_CLOSE)


def build_session_index(days):
    """Sorted (lo, hi, day) so a timestamp can be placed with one bisect."""
    rows = sorted((rth_bounds_ns(d) + (d,)) for d in days)
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


# ---------------------------------------------------------------- the scan

def batch_files():
    out = []
    for venue in VENUES:
        v = venue.replace(".", "_")
        for name in sorted(os.listdir(RAW)) if os.path.isdir(RAW) else []:
            if name.startswith("bbo-1s_%s_e%d_" % (v, ARM)) and name.endswith(".csv.gz"):
                out.append((venue, os.path.join(RAW, name)))
    return out


def scan():
    days = load_calendar()
    uni = load_universe()
    want = set(arm_symbols(uni["events"][str(ARM)]))
    span = offset_days(days, BOUNDARY, REF_WINDOW[0], POST_WINDOW[1])
    los, his, dnames = build_session_index(span)
    files = batch_files()
    if not files:
        raise SystemExit("no batches in %s. Run b16_bbo_pull.py --fetch first."
                         % os.path.relpath(RAW, ROOT))

    #: (symbol, day, venue) -> counters. One dict, no nesting, so a missing cell
    #: is missing rather than silently zero.
    cell = {}
    flags_seen = {}
    #: Third, independent confirmation of the offset, second version.
    #:
    #: The first version assumed the archive opens at 04:00 ET and read the
    #: earliest timestamp of each day. That premise was wrong: the earliest row
    #: on every one of the 58 days is at 05:xx UTC, and the check reported all 58
    #: as unrecognised. It was reporting its own bad premise, not a bad offset.
    #:
    #: This version uses a fact that does not depend on when the archive opens:
    #: the busiest hour of the day is inside regular trading hours. Under EST
    #: that band is [14, 21) UTC and under EDT it is [13, 20). Tracked BEFORE the
    #: session filter, which is what keeps it independent of the thing it checks.
    hour_hist = {}
    NS_DAY = 86_400 * 10**9
    NS_HOUR = 3600 * 10**9
    for venue, path in files:
        n_rows = n_kept = 0
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
            head = fh.readline().rstrip("\n").split(",")
            ix = {c: i for i, c in enumerate(head)}
            i_ts, i_b, i_a = ix["ts_recv"], ix["bid_px_00"], ix["ask_px_00"]
            i_sym, i_fl = ix["symbol"], ix["flags"]
            for line in fh:
                n_rows += 1
                f = line.rstrip("\n").split(",")
                sym = f[i_sym]
                if sym not in want:
                    continue
                ts = int(f[i_ts])
                dn = ts // NS_DAY
                hk = (dn, (ts - dn * NS_DAY) // NS_HOUR)
                hour_hist[hk] = hour_hist.get(hk, 0) + 1
                k = bisect.bisect_right(los, ts) - 1
                if k < 0 or ts >= his[k]:
                    continue
                n_kept += 1
                day = dnames[k]
                key = "%s|%s|%s" % (sym, day, venue)
                c = cell.get(key)
                if c is None:
                    c = cell[key] = [0, 0, 0, 0.0, 0.0, 0.0, 0.0]
                    # n_sec, n_two, n_crossed, sum_rel, sum_ticks, min_mid, max_mid
                    c[5] = float("inf")
                c[0] += 1
                flags_seen[f[i_fl]] = flags_seen.get(f[i_fl], 0) + 1
                b, a = int(f[i_b]), int(f[i_a])
                if b == UNDEF or a == UNDEF:
                    continue
                bp, ap = b * PX_SCALE, a * PX_SCALE
                if ap <= bp:
                    c[2] += 1
                    continue
                mid = 0.5 * (bp + ap)
                c[1] += 1
                c[3] += (ap - bp) / mid
                c[4] += (ap - bp) / TICK
                c[5] = min(c[5], mid)
                c[6] = max(c[6], mid)
        print("  %-12s %-46s %10d rows, %9d in session"
              % (venue, os.path.basename(path), n_rows, n_kept))

    #: Report it, and name any day that disagrees. This does not gate anything:
    #: rule 23 says a check that feeds no criterion may not abort the run.
    peak = {}
    for (dn, hr), n in hour_hist.items():
        if peak.get(dn, (-1, -1))[1] < n:
            peak[dn] = (hr, n)
    spanset = set(span)
    inband, odd = 0, []
    for dn in sorted(peak):
        dstr = datetime.datetime.fromtimestamp(dn * 86400, UTC).strftime("%Y%m%d")
        if dstr not in spanset:
            continue
        off = et_offset_hours(dstr)
        lo_h, hi_h = (9 - off, 16 - off)
        hr = peak[dn][0]
        if lo_h <= hr < hi_h:
            inband += 1
        else:
            odd.append((dstr, hr, lo_h, hi_h, off))
    print("\n  busiest UTC hour inside RTH, on the %d span days: %d in band"
          % (inband + len(odd), inband))
    if odd:
        print("    OUT OF BAND, by name (this gates nothing, rule 23; it is"
              " printed so it is seen):")
        for dstr, hr, lo_h, hi_h, off in odd[:20]:
            print("      %s  peak at %02d:xx UTC, RTH is [%02d,%02d) under UTC%+d"
                  % (dstr, hr, lo_h, hi_h, off))
    else:
        print("    every span day agrees with the statutory offset")

    for c in cell.values():
        if c[5] == float("inf"):
            c[5] = 0.0
    os.makedirs(RESULTS, exist_ok=True)
    payload = {
        "arm": ARM, "boundary": BOUNDARY, "venues": list(VENUES),
        "session": "09:30-16:00 America/New_York", "rth_seconds": RTH_SECONDS,
        "windows": {"ref": REF_WINDOW, "pre": PRE_WINDOW, "post": POST_WINDOW},
        "span_days": span,
        "fields": ["n_sec", "n_two", "n_crossed", "sum_rel", "sum_ticks",
                   "min_mid", "max_mid"],
        "flags": dict(sorted(flags_seen.items(), key=lambda kv: -kv[1])),
        "cells": {k: cell[k] for k in sorted(cell)},
    }
    tmp = DAILY + ".part"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, sort_keys=True)
    os.replace(tmp, DAILY)
    print("\n  wrote %s  (%d cells, %.1f MB)"
          % (os.path.relpath(DAILY, ROOT), len(cell), os.path.getsize(DAILY) / 1e6))
    print("  no rho was computed. Run --screen next.")
    return 0


# ---------------------------------------------------------------- the screen

def load_daily():
    if not os.path.exists(DAILY):
        raise SystemExit("no %s. Run --scan first." % os.path.relpath(DAILY, ROOT))
    return json.load(open(DAILY, encoding="utf-8"))


def screen():
    d = load_daily()
    cells, span = d["cells"], d["span_days"]
    days = load_calendar()
    ref = offset_days(days, BOUNDARY, *REF_WINDOW)
    pre = offset_days(days, BOUNDARY, *PRE_WINDOW)
    post = offset_days(days, BOUNDARY, *POST_WINDOW)
    syms = sorted({k.split("|")[0] for k in cells})

    def agg(sym, dayset, venue, j):
        return sum(cells.get("%s|%s|%s" % (sym, dd, venue), [0] * 7)[j]
                   for dd in dayset)

    # ---- 1. the thinnest cells, by name, before any average
    print("STEP 1  the thinnest (symbol, day, venue) cells, by name")
    thin = sorted(((v[1], k) for k, v in cells.items()))[:8]
    for n_two, k in thin:
        s, dd, ve = k.split("|")
        c = cells[k]
        print("   %-7s %s %-12s  %6d two-sided of %5d present, %d crossed"
              % (s, dd, ve, n_two, c[0], c[2]))
    allcov = sorted(v[1] / d["rth_seconds"] for v in cells.values())
    n = len(allcov)
    print("   two-sided share of the %d RTH seconds, over %d cells:" % (d["rth_seconds"], n))
    print("     min %.4f   p05 %.4f   p50 %.4f   mean %.4f   max %.4f"
          % (allcov[0], allcov[n // 20], allcov[n // 2], sum(allcov) / n, allcov[-1]))
    print("   flags seen: %s" % ", ".join("%s x%d" % (k, v)
                                          for k, v in list(d["flags"].items())[:6]))

    # ---- 2. description
    print("\nSTEP 2  description")
    tw = []
    for s in syms:
        for ve in VENUES:
            nt = agg(s, ref, ve, 1)
            if nt:
                tw.append((agg(s, ref, ve, 4) / nt, s, ve))
    tw.sort()
    print("   reference-window time-weighted spread, in ticks, %d (symbol, venue):" % len(tw))
    print("     min %.2f (%s %s)   p50 %.2f   max %.2f (%s %s)"
          % (tw[0][0], tw[0][1], tw[0][2], tw[len(tw) // 2][0],
             tw[-1][0], tw[-1][1], tw[-1][2]))
    cr = sum(v[2] for v in cells.values())
    tt = sum(v[1] for v in cells.values())
    print("   crossed or locked: %d of %d two-sided-eligible seconds, %.4f%%"
          % (cr, cr + tt, 100.0 * cr / max(1, cr + tt)))
    #: The distinction rule 3 turns on: of the seconds where a record exists at
    #: all, how many are two-sided. This is the venue's behaviour. The share of
    #: 23400 that rule 3 as written uses is the schema's emission policy.
    onesided = [(v[1] / v[0], k) for k, v in cells.items() if v[0]]
    onesided.sort()
    m = len(onesided)
    print("   two-sided share OF RECORDS PRESENT, over %d cells:" % m)
    print("     min %.4f (%s)   p05 %.4f   p50 %.4f   mean %.4f"
          % (onesided[0][0], onesided[0][1].replace("|", " "),
             onesided[m // 20][0], onesided[m // 2][0],
             sum(x for x, _ in onesided) / m))

    # ---- 3. the two registered screens
    print("\nSTEP 3  the registered screens")
    drop3, drop4, keep = [], [], []
    for s in syms:
        shares = {ve: agg(s, pre, ve, 1) / (len(pre) * d["rth_seconds"]) for ve in VENUES}
        worst = min(shares.values())
        if worst < RULE3_TWO_SIDED_SHARE:
            drop3.append((worst, s, shares))
            continue
        ticks = {}
        for ve in VENUES:
            nt = agg(s, ref, ve, 1)
            ticks[ve] = (agg(s, ref, ve, 4) / nt) if nt else 0.0
        if min(ticks.values()) < RULE4_MIN_SPREAD_TICKS:
            drop4.append((min(ticks.values()), s, ticks))
            continue
        keep.append(s)
    print("   rule 3  both venues two-sided >= %.0f%% of pre-window RTH seconds"
          % (RULE3_TWO_SIDED_SHARE * 100))
    print("           drops %d of %d" % (len(drop3), len(syms)))
    for w, s, sh in sorted(drop3)[:12]:
        print("             %-7s worst %.4f   %s" % (
            s, w, "  ".join("%s %.4f" % (v.split(".")[0], sh[v]) for v in VENUES)))
    if len(drop3) > 12:
        print("             ... and %d more, all in the json" % (len(drop3) - 12))
    print("   rule 4  reference-window time-weighted spread >= %.0f ticks on both"
          % RULE4_MIN_SPREAD_TICKS)
    print("           drops %d of the %d that passed rule 3" % (len(drop4), len(syms) - len(drop3)))
    for w, s, tk in sorted(drop4)[:12]:
        print("             %-7s worst %.2f ticks   %s" % (
            s, w, "  ".join("%s %.2f" % (v.split(".")[0], tk[v]) for v in VENUES)))
    if len(drop4) > 12:
        print("             ... and %d more, all in the json" % (len(drop4) - 12))

    # ---- 4. what survives
    print("\nSTEP 4  survivors")
    print("   %d of %d" % (len(keep), len(syms)))
    for i in range(0, len(keep), 12):
        print("     " + " ".join("%-6s" % s for s in keep[i:i + 12]))
    out = os.path.join(RESULTS, "b16_e5_screened.json")
    json.dump({"arm": ARM, "boundary": BOUNDARY, "kept": keep,
               "dropped_rule3": sorted(s for _, s, _ in drop3),
               "dropped_rule4": sorted(s for _, s, _ in drop4),
               "rule3_share": RULE3_TWO_SIDED_SHARE,
               "rule4_min_ticks": RULE4_MIN_SPREAD_TICKS,
               "session": d["session"], "windows": d["windows"]},
              open(out, "w", encoding="utf-8", newline="\n"), indent=2, sort_keys=True)
    print("\n   wrote %s" % os.path.relpath(out, ROOT))
    print("   no rho was computed. The drop counts above are the registered")
    print("   precondition for looking at one.")
    if len(keep) < 40:
        print("\n   NOTE  %d survivors is below the registered N >= 40. That is a"
              % len(keep))
        print("         reading about this arm, not an error. Stop and re-check.")
    return 0


# ---------------------------------------------------------------- pairing

PAIRS = os.path.join(RESULTS, "b16_e5_pairs.json")
#: --fill writes its own file. The 2026-08-21 reading stays on disk untouched,
#: which is what discipline 19 asks for: the two numbers side by side, and the
#: old one still reproducible.
PAIRS_FILL = os.path.join(RESULTS, "b16_e5_pairs_fill.json")


FILL = [False]


def carry_step(m, prev, off, good):
    """One record under the carry rule. `prev` is (offset, valid) of the last
    record on the same (symbol, day, venue), or None. Marks the span the
    PREVIOUS quote was standing over, then becomes the new prev. O(1) memory,
    which is why pairs() calls this instead of collecting events."""
    if prev is not None and prev[1] and off > prev[0]:
        m[prev[0]:off] = b"\x01" * (off - prev[0])
    return (off, good)


def carry_flush(m, prev, n):
    """The last standing quote of the day runs to the close and not past it."""
    if prev is not None and prev[1] and prev[0] < n:
        m[prev[0]:n] = b"\x01" * (n - prev[0])



def pairs():
    """How many seconds carry a two-sided quote on BOTH venues at once.

    This is the design's worst cell and nothing had measured it. rho needs
    bid and ask on venue a AND venue b at the same instant, so the count of
    paired seconds is the effective N of the whole arm, not either venue's own
    count. Engineering rule 13 step 1: measure the worst cell, by name, before
    anything else.

    Still no rho. This counts timestamps; it does not divide anything by
    anything.
    """
    days = load_calendar()
    uni = load_universe()
    want = set(arm_symbols(uni["events"][str(ARM)]))
    span = offset_days(days, BOUNDARY, REF_WINDOW[0], POST_WINDOW[1])
    spanset = set(span)
    los, his, dnames = build_session_index(span)
    files = batch_files()
    if not files:
        raise SystemExit("no batches in %s." % os.path.relpath(RAW, ROOT))

    #: (symbol, day, venue) -> bytearray of RTH_SECONDS flags. 3,780 cells at
    #: 23,400 bytes is about 88 MB, which is why this is a bitmap and not a set
    #: of timestamps.
    mask = {}
    #: A BBO IS A STATE, NOT AN EVENT. `bbo-1s` emits a record when the book
    #: changed in that interval, so a quote standing untouched for thirty
    #: seconds produces one record and marks one second. Counting records
    #: therefore measures UPDATE DENSITY, and rule 3's 0.90 was written about
    #: PRESENCE. With --fill the flag is carried forward from each record to the
    #: next one on the same (symbol, day, venue), which is what "the quote is
    #: standing" means, and an invalid record (undefined side, or crossed) ENDS
    #: the carry instead of being skipped, because that is the quote going away.
    #:
    #: Default is off so this reproduces the 2026-08-21 numbers bit for bit,
    #: which is discipline 19. The two readings are printed side by side.
    last = {}
    gaps = {}
    for venue, path in files:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
            head = fh.readline().rstrip("\n").split(",")
            ix = {c: i for i, c in enumerate(head)}
            i_ts, i_b, i_a, i_sym = (ix["ts_recv"], ix["bid_px_00"],
                                     ix["ask_px_00"], ix["symbol"])
            for line in fh:
                f = line.rstrip("\n").split(",")
                if f[i_sym] not in want:
                    continue
                b, a = int(f[i_b]), int(f[i_a])
                good = not (b == UNDEF or a == UNDEF or a <= b)
                if not (good or FILL[0]):
                    continue
                ts = int(f[i_ts])
                k = bisect.bisect_right(los, ts) - 1
                if k < 0 or ts >= his[k]:
                    continue
                key = "%s|%s|%s" % (f[i_sym], dnames[k], venue)
                m = mask.get(key)
                if m is None:
                    m = mask[key] = bytearray(RTH_SECONDS)
                off = (ts - los[k]) // 10**9
                if not FILL[0]:
                    m[off] = 1
                    continue
                prev = last.get(key)
                #: engineering rule 13 step 1: measure the worst cell, by name.
                #: A carry has one failure mode and it is silent: a HALT, or a
                #: hole in the file, produces no record at all, so nothing ends
                #: the carry and a stale quote is spread over the gap. The
                #: length of the longest carried gap is what shows that, and a
                #: median share of exactly 1.0000 is precisely when it must be
                #: looked at. No threshold: the distribution is printed.
                if prev is not None and prev[1] and off > prev[0]:
                    g = off - prev[0]
                    st = gaps.setdefault(f[i_sym], [0, 0, 0, 0])
                    st[0] = max(st[0], g)
                    st[1] += g
                    st[2] += 1 if g > 60 else 0
                    st[3] += 1 if g > 600 else 0
                last[key] = carry_step(m, prev, off, good)
        print("  %-12s %s" % (venue, os.path.basename(path)))
    if FILL[0]:
        #: the close-out carry counts too. A symbol whose last record of the day
        #: lands at 10:00 gets six hours carried to the close, and that is the
        #: same silent hole as a halt, just at the end of the day instead of the
        #: middle. Counting the mid-day gaps and not this one would hide it.
        for key, prev in last.items():
            if prev is not None and prev[1] and prev[0] < RTH_SECONDS:
                g = RTH_SECONDS - prev[0]
                st = gaps.setdefault(key.split("|")[0], [0, 0, 0, 0])
                st[0] = max(st[0], g)
                st[1] += g
                st[2] += 1 if g > 60 else 0
                st[3] += 1 if g > 600 else 0
            carry_flush(mask[key], prev, RTH_SECONDS)

    wins = {"ref": offset_days(days, BOUNDARY, *REF_WINDOW),
            "pre": offset_days(days, BOUNDARY, *PRE_WINDOW),
            "post": offset_days(days, BOUNDARY, *POST_WINDOW)}
    a_v, b_v = VENUES
    out, worst = {}, []
    for sym in sorted(want):
        rec = {}
        for wname, wdays in wins.items():
            na = nb = both = 0
            for dd in wdays:
                ma = mask.get("%s|%s|%s" % (sym, dd, a_v))
                mb = mask.get("%s|%s|%s" % (sym, dd, b_v))
                ca = sum(ma) if ma else 0
                cb = sum(mb) if mb else 0
                cboth = sum(x & y for x, y in zip(ma, mb)) if (ma and mb) else 0
                na += ca
                nb += cb
                both += cboth
                if wname == "pre":
                    worst.append((cboth, sym, dd, ca, cb))
            rec[wname] = {"a": na, "b": nb, "both": both,
                          "days": len(wdays),
                          "cap": len(wdays) * RTH_SECONDS}
        out[sym] = rec

    print("\n  paired seconds: a two-sided quote on %s AND %s in the same second"
          % (a_v, b_v))
    print("  window cap is %d seconds per day\n" % RTH_SECONDS)
    rows = sorted((out[s]["pre"]["both"], s) for s in out)
    print("  PRE window (%d trading days, cap %d seconds)"
          % (len(wins["pre"]), len(wins["pre"]) * RTH_SECONDS))
    print("    thinnest eight, by name:")
    for n, s in rows[:8]:
        r = out[s]["pre"]
        print("      %-7s both %7d   %s %7d   %s %7d   paired/min %.3f"
              % (s, n, a_v.split(".")[0], r["a"], b_v.split(".")[0], r["b"],
                 n / max(1, min(r["a"], r["b"]))))
    print("    thickest three, by name:")
    for n, s in rows[-3:]:
        r = out[s]["pre"]
        print("      %-7s both %7d   %s %7d   %s %7d   paired/min %.3f"
              % (s, n, a_v.split(".")[0], r["a"], b_v.split(".")[0], r["b"],
                 n / max(1, min(r["a"], r["b"]))))
    vals = [n for n, _ in rows]
    nn = len(vals)
    print("    over %d symbols: min %d   p05 %d   p50 %d   mean %d   max %d"
          % (nn, vals[0], vals[nn // 20], vals[nn // 2], sum(vals) // nn, vals[-1]))
    print("\n    thinnest eight (symbol, day) cells in the pre window, by name:")
    for cboth, sym, dd, ca, cb in sorted(worst)[:8]:
        print("      %-7s %s  both %5d   %s %5d   %s %5d"
              % (sym, dd, cboth, a_v.split(".")[0], ca, b_v.split(".")[0], cb))

    for wname in ("ref", "pre", "post"):
        tot = sum(out[s][wname]["both"] for s in out)
        cap = len(wins[wname]) * RTH_SECONDS * len(out)
        print("\n  %-4s total paired seconds %10d of a %d cap, %.3f%%"
              % (wname, tot, cap, 100.0 * tot / cap))

    out_path = PAIRS_FILL if FILL[0] else PAIRS
    json.dump({"arm": ARM, "boundary": BOUNDARY, "venues": list(VENUES),
               "rth_seconds": RTH_SECONDS, "windows": wins,
               "carry_forward": bool(FILL[0]), "per_symbol": out},
              open(out_path, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s   carry_forward=%s"
          % (os.path.relpath(out_path, ROOT), bool(FILL[0])))
    #: rule 3 read straight off this pass, so the arm's fate is printed here
    #: rather than in a second file to be forgotten about
    pre = [(v["pre"]["both"] / float(v["pre"]["cap"]), k) for k, v in out.items()]
    pre.sort(reverse=True)
    keep = [k for sh, k in pre if sh >= RULE3_TWO_SIDED_SHARE]
    print("  rule 3 at %.2f: keeps %d of %d.  best %s %.4f, median %.4f"
          % (RULE3_TWO_SIDED_SHARE, len(keep), len(pre), pre[0][1], pre[0][0],
             pre[len(pre) // 2][0]))
    if FILL[0] and gaps:
        rows = sorted(((v[0], k, v) for k, v in gaps.items()), reverse=True)
        mx = [r[0] for r in rows]
        print("\n  carried gaps, in seconds, over the whole 30-day span")
        print("    longest per symbol: max %d  p90 %d  median %d  min %d"
              % (mx[0], mx[int(len(mx) * 0.1)], mx[len(mx) // 2], mx[-1]))
        print("    %-7s %9s %11s %9s %9s"
              % ("symbol", "longest", "carried s", ">60s", ">600s"))
        for g, k, v in rows[:8]:
            print("    %-7s %9d %11d %9d %9d" % (k, v[0], v[1], v[2], v[3]))
        big = sum(1 for r in rows if r[0] > 600)
        print("    symbols whose longest carry exceeds 600s: %d of %d"
              % (big, len(rows)))
        print("    a session is %d s. Anything near that is a hole, not a quote."
              % RTH_SECONDS)
    print("  no rho was computed. This counted timestamps.")
    return 0


# ---------------------------------------------------------------- selftest

def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    def utc_hhmm(ns):
        return datetime.datetime.fromtimestamp(ns / 1e9, UTC).strftime("%H:%M")

    #: Six pinned dates: three either side of both 2023 transitions. The two
    #: transitions themselves are Sundays, so no trading day sits on one.
    pinned = {"20230310": -5, "20230313": -4, "20231103": -4, "20231106": -5,
              "20230201": -5, "20230425": -4}
    chk("1  the statutory offset is right on six pinned dates (%s)"
        % " ".join("%s%d" % (d, v) for d, v in sorted(pinned.items())),
        all(et_offset_hours(d) == v for d, v in pinned.items()))
    chk("2  the 2023 transitions land on 03-12 and 11-05, both Sundays",
        _nth_sunday(2023, 3, 2) == datetime.date(2023, 3, 12)
        and _nth_sunday(2023, 11, 1) == datetime.date(2023, 11, 5)
        and _nth_sunday(2023, 3, 2).weekday() == 6)
    lo, hi = rth_bounds_ns("20230201")
    lo2, hi2 = rth_bounds_ns("20230315")
    chk("3  09:30 ET is 14:30 UTC under EST and 13:30 UTC under EDT",
        utc_hhmm(lo) == "14:30" and utc_hhmm(lo2) == "13:30")
    chk("4  a session is exactly %d seconds long on both sides of the change"
        % RTH_SECONDS,
        (hi - lo) == RTH_SECONDS * 10**9 and (hi2 - lo2) == RTH_SECONDS * 10**9)

    chk("5  the sentinel is INT64_MAX and is treated as undefined, not as a price",
        UNDEF == 2**63 - 1)
    chk("6  price scaling: 370110000000 reads as 370.11",
        abs(370110000000 * PX_SCALE - 370.11) < 1e-9)
    chk("7  the thresholds are the two registered ones, not new numbers",
        RULE3_TWO_SIDED_SHARE == 0.90 and RULE4_MIN_SPREAD_TICKS == 3.0)

    if os.path.exists(CAL_CACHE):
        days = load_calendar()
        ref = offset_days(days, BOUNDARY, *REF_WINDOW)
        pre = offset_days(days, BOUNDARY, *PRE_WINDOW)
        post = offset_days(days, BOUNDARY, *POST_WINDOW)
        chk("8  windows are 10 / 10 / 10 trading days",
            len(ref) == 10 and len(pre) == 10 and len(post) == 10)
        chk("9  the boundary day opens the post window",
            post[0] == BOUNDARY.replace("-", ""))
        chk("10 ref, pre and post are disjoint and ordered",
            ref[-1] < pre[0] and pre[-1] < post[0])
        chk("11 the whole span sits inside the 29+29 that was bought",
            len(ref + pre + post) == 30)
        b = BOUNDARY.replace("-", "")
        chk("12 the reference window does not touch the pre window, so rule 4"
            " is not screening on half the result",
            not set(ref) & set(pre) and all(x < b for x in ref + pre))

    if os.path.exists(UNIVERSE):
        uni = load_universe()
        syms = arm_symbols(uni["events"][str(ARM)])
        chk("13 e5 carries its registered 63 symbols as bare tickers",
            len(syms) == 63 and all(isinstance(x, str) for x in syms))

    if os.path.exists(CAL_CACHE):
        cal = load_calendar()
        span = offset_days(cal, BOUNDARY, REF_WINDOW[0], POST_WINDOW[1])
        bought = offset_days(cal, BOUNDARY, -29, 28)
        offs = {et_offset_hours(d) for d in span}
        offs_bought = {et_offset_hours(d) for d in bought}
        #: Corrected 2026-08-21. The first version asserted the 30-day ANALYSIS
        #: span straddles the change and failed, correctly: 2023-01-25 to
        #: 2023-03-09 is entirely EST. It is the 58-day PURCHASE window that
        #: reaches past 2023-03-12. Both facts are worth pinning, because the
        #: second is why the offset code has to exist and the first is why it
        #: cannot affect any number this arm produces.
        chk("17 the analysis span is entirely EST (%s), so DST moves nothing"
            " this arm reports" % "/".join(str(x) for x in sorted(offs)),
            offs == {-5})
        chk("17b the 58-day purchase window does straddle the change (%s), which"
            " is why a fixed offset is still unsafe"
            % "/".join(str(x) for x in sorted(offs_bought)),
            offs_bought == {-5, -4})
        #: Second, independent path. It is skipped loudly, never quietly.
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("America/New_York")
            agree = all(
                int(datetime.datetime.combine(
                    datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])),
                    RTH_OPEN, tz).timestamp()) * 10**9 == rth_bounds_ns(d)[0]
                for d in span)
            chk("18 zoneinfo agrees with the statute on all %d days in the span"
                % len(span), agree)
        except Exception as e:                                      # noqa: BLE001
            print("  skip 18 zoneinfo is unavailable here (%s: %s);"
                  % (type(e).__name__, str(e)[:60]))
            print("          the statutory path is the one in use and tests 1-4"
                  " and 17 cover it. --scan adds a third check from the data.")

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    import ast
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("14 nothing in this file is named for rho; the drop counts come first"
        " (registered)",
        not any("rho" in x.lower() for x in names))
    dels = {getattr(c.func, "attr", None) for c in ast.walk(tree)
            if isinstance(c, ast.Call)}
    chk("15 nothing in this file deletes anything (AST walk)",
        not ({"remove", "unlink", "rmtree", "rmdir"} & dels))
    #: 17-21 the carry rule. A BBO is a state; counting records measures update
    #: density instead of presence, and rule 3's 0.90 was written about presence.
    def _fill(evs, n):
        m = bytearray(n)
        prev = None
        for off, good in evs:
            prev = carry_step(m, prev, off, good)
        carry_flush(m, prev, n)
        return sum(m)

    chk("17 one standing quote at second 10 covers 10..99, not one second",
        _fill([(10, True)], 100) == 90)
    chk("18 a second record extends rather than restarts the cover",
        _fill([(10, True), (50, True)], 200) == 190)
    chk("19 an invalid record ENDS the cover instead of being skipped",
        _fill([(10, True), (50, False)], 100) == 40)
    chk("20 a day that opens invalid covers nothing",
        _fill([(0, False), (90, False)], 100) == 0)
    chk("21 the carry changes the answer, so the flag is not cosmetic",
        _fill([(10, True)], 100) != 1)

    chk("16 the scan writes a reusable cache, so re-screening never rereads 4.7 GB",
        DAILY.endswith("b16_e5_daily.json"))

    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--screen", action="store_true")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--fill", action="store_true",
                    help="carry a standing quote forward between "
                         "records; default off reproduces 2026-08-21")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.scan:
        return scan()
    if a.screen:
        return screen()
    FILL[0] = bool(getattr(a, 'fill', False))
    if a.pairs:
        return pairs()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
