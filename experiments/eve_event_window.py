#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EVE Online sales-tax event windows: does the floor of the spread
distribution step on the day the tax changes?

WHY THIS FILE EXISTS
====================
`eve_market_probe.py` settled availability. 8,654 item types are two-sided at
both Jita 4-4 and Amarr VIII in every snapshot read, and roughly 200 of them
sit inside the spread cap the size criterion needs. This file is the
measurement that availability was for.

THE OBJECT
==========
b4 section 5.1 splits a two-venue quote pair into an index half and a friction
half. The friction half is

    S + S' = log(bid_a/ask_a) + log(bid_b/ask_b)          (both terms negative)

so the quantity that moves when a cost of trading moves is

    relsum := -(S + S') = log(ask_a/bid_a) + log(ask_b/bid_b)

which to first order is the sum of the two venues' one-way relative spreads.
`relsum` is the primary reading in this file. The per-hub spreads are printed
as its decomposition, never as a ratio: no cross-hub mid ratio is formed
anywhere here, same discipline as the probe.

WHY A SALES TAX MOVES THAT OBJECT
=================================
A market maker who buys at the bid and sells at the ask pays, per round trip,
a broker fee on each of the two orders and a sales tax on the completed sale.
Buying carries no sales tax. So the break-even one-way spread at one venue is

    (ask - bid)/mid  >=  2 * broker + tax

and the LOWER EDGE of the spread distribution is that break-even line, drawn
by whichever traders are closest to it. Raise the tax by d and the lower edge
moves up by d. Raise it at both venues, which a game-wide tax does by
construction, and `relsum` moves up by 2d.

This is the whole design. It is a shape on a page, not a regression.

THE READING RULE, WRITTEN BEFORE ANY WINDOW WAS DOWNLOADED
==========================================================
Registered here, on 2026-08-23, before the first byte of either window was
fetched. Everything below is arithmetic on numbers already in hand.

1.  EVENT.  2025-03-12, sales tax base 4% -> 7.5%, +3.50pp, broker fee
    unchanged in the same patch notes. That last clause is why this date is
    usable and why the 2022-era "Restructuring Taxes After Relief" change is
    not: that one moved sales tax 5->8 AND broker fee 5->3 on the same day,
    which is two treatments, so its floor step is uninterpretable.

2.  PREDICTED SIZE.  The Accounting skill damps the sales tax multiplicatively,
    `effective = base * (1 - r * level)`. The skill text gives r = 11%/level;
    the EVE University wiki reports Accounting V under a 7.5% base as 3.3%,
    which implies r = 11.2%/level. The two disagree in the third digit and
    nothing here needs them to agree, so the prediction is printed as the band
    they span rather than as a point.

        per hub, Accounting V   : +1.540 to +1.575 pp
        relsum, Accounting V    : +3.080 to +3.150 pp
        relsum, Accounting 0    : +7.000 pp

    The marginal market maker in a competitive hub has Accounting V, so the
    Accounting V band is the prediction and the unskilled figure is the upper
    bound. A measured step ANYWHERE inside [3.08, 7.00] pp on `relsum` is
    consistent with the tax and nothing else in the patch.

3.  THE EVENT DAY IS SPLIT, NOT SKIPPED.  EVE patches go live at the daily
    downtime, 11:00 UTC. So on 2025-03-12 itself the 06:00 snapshot is PRE and
    the 18:00 snapshot is POST. The step should therefore be visible inside a
    single calendar day, twelve hours apart, with no overnight gap to hide a
    trend in. That is the sharpest form of this test and it is free.

4.  SLOTS ARE FIXED IN ADVANCE.  Two snapshots per day, the one nearest 06:00
    UTC and the one nearest 18:00 UTC, the same two hours every day of both
    windows. Registered because the probe measured a 2.6x intraday swing in the
    tight-end count across three snapshots of one day: an unfixed slot would
    let time of day walk in wearing the event's clothes. 11:00-12:00 UTC is
    avoided by construction, which also steps around the archive's own daily
    hole (11:15 absent, 11:45 present at 37 bytes).

5.  THE SUBSET IS FIXED ON THE PRE WINDOW.  A tax that raises the floor pushes
    some items out through the top of any spread cap, so a cap re-applied each
    day would make the surviving set a function of the treatment. The set is
    therefore chosen once, from pre-window snapshots only, and carried forward
    by type_id. Membership: two-sided at both hubs in at least 80% of pre
    snapshots, and median pre `relsum` <= 0.20, which is the <=10% per-hub cap
    the probe's funnel used. The count at 60/70/80/90/100% presence is printed
    so the choice of 80 is visible rather than load-bearing.

6.  THE READING IS A DAILY SERIES, NOT A BAND.  Every snapshot's floor is
    printed on its own line in time order. B16's placebo band could not see the
    drift its real window was sitting on, because no placebo sub-window
    straddled offset 0 by construction. A printed series does not have that
    problem: a step and a trend look different on the page. Read the stream,
    not the summary.

7.  WHAT WOULD BE READ AS FAILURE.  Three shapes, all decidable by eye:
      - no step, floor flat through offset 0            -> the tax does not
        reach the quoted spread, the carrier is dead;
      - a step much smaller than 3.08pp                 -> the marginal quoter
        is not the taxed party, or is not at break-even;
      - a slope through offset 0 rather than a step     -> something else moved
        in this window and the design cannot separate it.
    None of the three is a crash. All three are readings.

8.  2024-07-25 IS NOT REGISTERED.  It was carried in from the carrier search as
    a second sales-tax-only date. Two lookups on 2026-08-23 failed to find any
    such change on that date, so it is in the EVENTS table with `status:
    UNVERIFIED` and with its rate fields set to None. Nothing downstream can
    read a prediction off it, by construction, until the patch notes are in
    hand. It can still be downloaded and looked at; it just cannot be scored.

WHAT THIS FILE DOES NOT DO
==========================
No cross-hub mid ratio. No regression. No placebo band. Nothing is deleted;
files already on disk are never refetched and anything about to be overwritten
is parked with an .expired suffix.

USAGE
=====
    python eve_event_window.py --selftest
    python eve_event_window.py --plan 2025-03-12
    python eve_event_window.py --fetch 2025-03-12 --confirm
    python eve_event_window.py --floor 2025-03-12
"""

import argparse
import ast
import datetime
import json
import os
import math
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: One reader of the archive, not two. `scan_one` is the streaming best-bid /
#: best-ask extractor and `day_index` is the directory listing with its
#: index.html retry; both were paid for once in the probe and are imported
#: rather than reimplemented. Selftest 6 asserts this file defines no scanner
#: of its own, which is the only thing that keeps that true over time.
from eve_market_probe import HUBS, day_index, get, park, scan_one   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "eve_market")
BASE = "https://data.everef.net/market-orders/history"

JITA, AMARR = 60003760, 60008494
SLOT_HOURS = (6, 18)
DOWNTIME_MIN = 11 * 60          # EVE daily downtime; patches go live here
CAP_RELSUM = 0.20               # <=10% per hub, expressed on the sum
PRESENCE = 0.80
HALF_DEFAULT = 14
BYTES_PER_SNAP = 18.1e6         # measured: three 2025-02-26 snapshots, 18.09-18.15 MB

#: Per-snapshot cache of {type_id: relsum} over ALL types two-sided at both
#: hubs, not just the chosen subset. v1 kept only the quantiles, so the first
#: reading threw the per-item object away and any second question had to pay
#: for a full rescan of 58 files at sixteen million rows each. That was a
#: miss against the house rule on reusable caches. The cache is keyed on the
#: snapshot filename, so a refetched or corrected file misses and rescans.
CACHE = os.path.join(ROOT, "data", "cache", "eve_relsum")
CACHE_ROUND = 8

#: v2. The v1 cache above stored `relsum` only, which is a SUMMARY, and the
#: first question asked after it was built (what does rho do?) needed the two
#: mids and could not be answered without a rescan. Caching the summary instead
#: of the object is the same mistake twice, so v2 stores the four raw quotes and
#: every derived quantity is computed from them. It lives in its own directory
#: so the v1 cache stays readable and nothing is parked or overwritten.
QCACHE = os.path.join(ROOT, "data", "cache", "eve_quotes")
Q_SIG = "%.10g"          # explicit float format, never repr

#: Registered AFTER the first reading, and recorded as such (D3, revision
#: class three). The p50 series converges over roughly five days after the
#: patch, so "settled" is the post window from event+5 onward. Both the full
#: post window and the settled one are printed everywhere, so this cut is a
#: description of the convergence and never the thing a reading rests on.
SETTLE_DAYS = 5

STAMP_RE = re.compile(r"market-orders-(\d{4}-\d\d-\d\d)_(\d\d)-(\d\d)-(\d\d)")

#: `effective = base * (1 - r * level)`. See reading rule 2.
ACCT_R = (0.110, 0.112)
ACCT_LEVEL = 5

EVENTS = {
    "2025-03-12": {
        "status": "CONFIRMED",
        #: base tier only. The minimum tier is not quoted in the patch notes, so
        #: prediction() derives it by damping the tax with ACCT_R. That is exact
        #: here because the broker fee did not move, so no broker term survives.
        "rates": {"base": {"tax": (4.0, 7.5), "broker": (3.0, 3.0)},
                  "minimum": None},
        "source": "patch notes 2025-03-12: 'Sales Tax has been increased from 4% to 7.5%'. "
                  "No broker fee change in the same notes. Confirmed 2026-08-23 against "
                  "the EVE University Tax wiki and the forum thread that surfaced it. "
                  "JUDGED: two shocks, not one. Revenant shipped the same day and moved "
                  "manufacturing and mining; --shape read the step as proportional "
                  "(cv 0.056 on the ratio against 0.365 on the addition) and --rho read "
                  "both halves moving by the same factor (x1.2390 and x1.1929), which is "
                  "a volatility shock. The tax prediction was rejected at 10.24 se.",
    },
    "2021-10-13": {
        "status": "CANDIDATE",
        #: Version 19.09. The patch notes quote BOTH tiers, so no skill model is
        #: needed and prediction() uses them verbatim.
        "rates": {"base": {"tax": (5.0, 8.0), "broker": (5.0, 3.0)},
                  "minimum": {"tax": (2.25, 3.6), "broker": (3.0, 1.0)}},
        "source": "Patch Notes Version 19.09, initial release date. Sales tax base "
                  "5.0->8.0 and minimum 2.25->3.6; broker fee base 5.0->3.0 and minimum "
                  "3.0->1.0. Both levers are on the friction half and neither touches "
                  "item supply. The bundle in 19.09 is narrow: drone mutaplasmids, one "
                  "CONCORD blueprint, drop rates. One of THREE candidate live dates, all "
                  "three named before any byte of this window was read.",
    },
    "2021-10-19": {
        "status": "CANDIDATE",
        "rates": {"base": {"tax": (5.0, 8.0), "broker": (5.0, 3.0)},
                  "minimum": {"tax": (2.25, 3.6), "broker": (3.0, 1.0)}},
        "source": "Same change as 2021-10-13. This is the devblog publication date "
                  "('Restructuring Taxes After Relief'), which need not be the live date. "
                  "Second of the three candidates.",
    },
    "2021-11-03": {
        "status": "CANDIDATE",
        "rates": {"base": {"tax": (5.0, 8.0), "broker": (5.0, 3.0)},
                  "minimum": {"tax": (2.25, 3.6), "broker": (3.0, 1.0)}},
        "source": "Same change. This is the final-update date given in the 19.09 patch "
                  "notes. Third of the three candidates. The archive covers this day only "
                  "partially, 34 names against 48.",
    },
    "2024-07-25": {
        "status": "UNVERIFIED",
        "rates": None,
        "source": "Carried in from the carrier search as a sales-tax-only date and NOT "
                  "reconfirmed. Two lookups on 2026-08-23 found no sales-tax change on "
                  "this date. Rates are None on purpose: no prediction can be read off "
                  "this row until the patch notes for the date are in hand.",
    },
}


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def prediction(ev):
    """The two competing models' predicted step on relsum, in percentage points.

    ROUND TRIP.  A market maker pays a broker fee on each of the two orders and
    a sales tax on the completed sale. Buying carries no sales tax. So the
    break-even one-way spread is `2*broker + tax`, a change in it is
    `d_tax + 2*d_broker`, and relsum, being the sum over two hubs, moves twice
    that.

    TAX ONLY.  The model that reads the sales tax by itself. It is carried
    because on the 2021 event the two models have OPPOSITE SIGNS: the tax rose
    3.0pp while the broker fee fell 2.0pp, so tax-only predicts a widening and
    round-trip predicts a narrowing. That turns the SIGN of the measured step
    into the criterion, and a sign needs no threshold.

    Each event carries rates at two tiers: `base`, meaning no skills and no
    standings, and `minimum`, meaning everything trained. The prediction is the
    band those two tiers span, and the marginal quoter in a competitive hub
    sits near the minimum end. When the patch notes do not quote a minimum
    tier, the tax is damped by ACCT_R instead, which is exact only if the
    broker fee did not move; if it did move and no minimum tier is quoted, this
    returns None rather than guess.

    Returns None for an event whose rates are None. That is what keeps an
    unverified date unscorable, by construction rather than by remembering."""
    r = ev.get("rates")
    if not r:
        return None

    def rt(t):
        return (t["tax"][1] - t["tax"][0]) + 2.0 * (t["broker"][1] - t["broker"][0])

    def tx(t):
        return t["tax"][1] - t["tax"][0]

    base = r["base"]
    rt_base, tx_base = 2.0 * rt(base), 2.0 * tx(base)
    if r.get("minimum"):
        m = r["minimum"]
        rt_sk = (2.0 * rt(m), 2.0 * rt(m))
        tx_sk = (2.0 * tx(m), 2.0 * tx(m))
    else:
        if base["broker"][0] != base["broker"][1]:
            return None          # broker moved, no quoted minimum: not scorable
        d = sorted(1.0 - k * ACCT_LEVEL for k in ACCT_R)
        rt_sk = (2.0 * rt(base) * d[0], 2.0 * rt(base) * d[1])
        tx_sk = (2.0 * tx(base) * d[0], 2.0 * tx(base) * d[1])
    rt_band = (min(rt_base, *rt_sk), max(rt_base, *rt_sk))
    tx_band = (min(tx_base, *tx_sk), max(tx_base, *tx_sk))
    return {"rt_base": rt_base, "rt_skilled": rt_sk, "rt_band": rt_band,
            "tx_base": tx_base, "tx_skilled": tx_sk, "tx_band": tx_band,
            "opposite": rt_band[1] * tx_band[0] < 0 or rt_band[0] * tx_band[1] < 0}


def window_days(event, half):
    e = datetime.date(*[int(x) for x in event.split("-")])
    return [(e + datetime.timedelta(days=k)).isoformat()
            for k in range(-half, half + 1)]


def phase(day, hour, event):
    """pre / post. The event day is SPLIT at downtime, not skipped."""
    if day < event:
        return "pre"
    if day > event:
        return "post"
    return "pre" if hour * 60 < DOWNTIME_MIN else "post"


def pick_slots(names, hours=SLOT_HOURS):
    """[(hour, filename, minutes_off)]. Nearest by wrap-around clock distance."""
    out = []
    for h in hours:
        target = h * 60
        best = None
        for n in names:
            m = STAMP_RE.match(n)
            if not m:
                continue
            mins = int(m.group(2)) * 60 + int(m.group(3))
            d = abs(mins - target)
            d = min(d, 1440 - d)
            if best is None or d < best[0]:
                best = (d, n)
        if best is not None:
            out.append((h, best[1], best[0]))
    return out


def quant(v, q):
    """Same index convention as the probe: floor(q * n), on a sorted list."""
    if not v:
        return None
    return v[min(len(v) - 1, int(q * len(v)))]


def quotes(book):
    """{type_id: (bid_j, ask_j, bid_a, ask_a)} over types two-sided at BOTH hubs.

    The raw quotes, not a derived number. Everything downstream is a function
    of these four, so no later question can force another scan of the archive."""
    #: The predicate here is EXACTLY relsums()'. A stricter one would make the
    #: v2 cache drop rows the v1 reading kept, and --floor would quietly stop
    #: reproducing the numbers already on the page. Non-positive quotes are
    #: filtered where the logs are taken, not here: the cache stores the object.
    out = {}
    for (sid, t), b in book.items():
        if sid != JITA:
            continue
        if b[0] is None or b[1] is None or b[1] <= b[0]:
            continue
        o = book.get((AMARR, t))
        if o is None or o[0] is None or o[1] is None or o[1] <= o[0]:
            continue
        mj, ma = 0.5 * (b[0] + b[1]), 0.5 * (o[0] + o[1])
        if mj <= 0 or ma <= 0:
            continue
        out[t] = (b[0], b[1], o[0], o[1])
    return out


def q_relsum(q):
    """-(S+S') to first order, the v1 definition, kept verbatim so that --floor
    and --shape reproduce the numbers read on 2026-08-23 to the last digit."""
    bj, aj, ba, aa = q
    return (aj - bj) / (0.5 * (bj + aj)) + (aa - ba) / (0.5 * (ba + aa))


def q_logsum(q):
    """-(S+S') exactly: log(ask_j/bid_j) + log(ask_a/bid_a). Positive.

    None when any of the four quotes is non-positive, which the linear
    definition tolerates and the log one does not. Filtering here rather than
    in quotes() keeps the cache a faithful copy of the book."""
    bj, aj, ba, aa = q
    if min(q) <= 0:
        return None
    return math.log(aj / bj) + math.log(aa / ba)


def q_logdiff(q):
    """S-S' exactly: 2*log(mid_j/mid_a). The index half. Signed."""
    bj, aj, ba, aa = q
    mj, ma = 0.5 * (bj + aj), 0.5 * (ba + aa)
    if mj <= 0 or ma <= 0:
        return None
    return 2.0 * math.log(mj / ma)


def q_rho(q):
    """|S-S'| / -(S+S'). Theorem 6(4) puts this in [0,1]; a value above 1 is a
    domain exclusion, not a clip, and is counted rather than squashed."""
    d, n = q_logsum(q), q_logdiff(q)
    if d is None or n is None or d <= 0:
        return None
    return abs(n) / d


def relsums(book):
    """{type_id: relsum} over types two-sided at BOTH hubs. relsum is the sum
    of the two one-way relative spreads, which is -(S + S') to first order.
    No ratio between the hubs is formed."""
    out = {}
    for (sid, t), b in book.items():
        if sid != JITA:
            continue
        if b[0] is None or b[1] is None or b[1] <= b[0]:
            continue
        o = book.get((AMARR, t))
        if o is None or o[0] is None or o[1] is None or o[1] <= o[0]:
            continue
        mj, ma = 0.5 * (b[0] + b[1]), 0.5 * (o[0] + o[1])
        if mj <= 0 or ma <= 0:
            continue
        out[t] = (b[1] - b[0]) / mj + (o[1] - o[0]) / ma
    return out


def cache_path(day, hour, name):
    return os.path.join(CACHE, "%s_%02d.json" % (day, hour))


def cached_quotes(day, hour, name, path):
    """{type_id: (bid_j, ask_j, bid_a, ask_a)} for one snapshot.

    Returns (mapping, "hit"|"scan", head_or_None); (None, "bad", head) on a
    malformed snapshot, reported and skipped exactly as in the probe."""
    cp = os.path.join(QCACHE, "%s_%02d.json" % (day, hour))
    if os.path.exists(cp):
        try:
            c = json.load(open(cp, encoding="utf-8"))
            if c.get("file") == name and c.get("v") == 2:
                return {int(k): tuple(v) for k, v in c["q"].items()}, "hit", None
        except Exception:                                            # noqa: BLE001
            pass                       # a bad cache file is re-derived, never removed
    book, n_rows, n_hit, head = scan_one(path)
    if book is None:
        return None, "bad", head
    qs = quotes(book)
    os.makedirs(QCACHE, exist_ok=True)
    park(cp)
    json.dump({"v": 2, "file": name, "day": day, "hour": hour, "rows": n_rows,
               "hub_rows": n_hit, "n_joint": len(qs),
               "q": {str(t): [float(Q_SIG % x) for x in v] for t, v in qs.items()}},
              open(cp, "w", encoding="utf-8", newline="\n"),
              indent=None, sort_keys=True)
    return qs, "scan", None


def cached_relsums(day, hour, name, path):
    """{type_id: relsum} for one snapshot, from cache when the cache was built
    from this same filename, otherwise by scanning and then writing it.

    Returns (mapping, "hit"|"scan", head_or_None). A malformed snapshot is
    reported and skipped exactly as in the probe: (None, "bad", head)."""
    cp = cache_path(day, hour, name)
    if os.path.exists(cp):
        try:
            c = json.load(open(cp, encoding="utf-8"))
            if c.get("file") == name:
                return {int(k): v for k, v in c["relsum"].items()}, "hit", None
        except Exception:                                            # noqa: BLE001
            pass                       # a bad cache file is re-derived, never removed
    #: v1 miss falls through to the v2 cache and derives relsum from the raw
    #: quotes, so one archive read serves both and the v1 directory is left
    #: exactly as it was found.
    qs, how, head = cached_quotes(day, hour, name, path)
    if qs is None:
        return None, "bad", head
    return {t: q_relsum(q) for t, q in qs.items()}, how, None


def fixed_set(per_snap_pre):
    """The subset, chosen from pre-window snapshots only. See reading rule 5.

    per_snap_pre: [{type_id: relsum}] in any order.
    Returns (chosen_set, presence_counts_at_several_thresholds)."""
    n_snap = len(per_snap_pre)
    seen = {}
    vals = {}
    for d in per_snap_pre:
        for t, r in d.items():
            seen[t] = seen.get(t, 0) + 1
            vals.setdefault(t, []).append(r)
    counts = {}
    for thr in (0.60, 0.70, 0.80, 0.90, 1.00):
        need = thr * n_snap
        counts["%.2f" % thr] = sum(
            1 for t, c in seen.items()
            if c >= need and quant(sorted(vals[t]), 0.5) <= CAP_RELSUM)
    need = PRESENCE * n_snap
    chosen = {t for t, c in seen.items()
              if c >= need and quant(sorted(vals[t]), 0.5) <= CAP_RELSUM}
    return chosen, counts


def on_disk(event, half):
    """[(day, hour, path_or_None, name_or_None)] in time order."""
    rows = []
    for day in window_days(event, half):
        d = os.path.join(RAW, day)
        names = sorted(f for f in os.listdir(d)) if os.path.isdir(d) else []
        names = [n for n in names if n.endswith(".csv.bz2")]
        got = {h: (n, off) for h, n, off in pick_slots(names)}
        for h in SLOT_HOURS:
            if h in got:
                rows.append((day, h, os.path.join(d, got[h][0]), got[h][0]))
            else:
                rows.append((day, h, None, None))
    return rows


def cmd_coverage(dates):
    """How far back does the archive go, and is a candidate date downloadable?

    One index read per date, no snapshot fetched, so this is free. It exists
    because the carrier search reopened: the criterion is not "one treatment"
    but "moves the friction half and leaves the index half alone", and two
    friction levers pulled together satisfy that better than one. That put the
    older market-fee dates back on the table, and the first thing to know about
    an older date is whether the archive reaches it at all.

    A date whose index cannot be read falls back to a TEMPLATED name list
    inside day_index. That fallback is a guess, so it is reported as NOT
    COVERED here rather than as a name count, which would read as coverage."""
    print("  %-12s %-9s %s" % ("date", "names", "how"))
    out = []
    for d in dates:
        names, note = day_index(d)
        fell_back = note.startswith("index unreadable")
        print("  %-12s %-9s %s"
              % (d, "NOT" if fell_back else len(names),
                 "no index; the templated list is a guess, treat as not covered"
                 if fell_back else note))
        out.append({"date": d, "covered": not fell_back,
                    "n_names": 0 if fell_back else len(names), "note": note})
    ok = [o for o in out if o["covered"]]
    if ok:
        print("\n  earliest covered date probed: %s" % min(o["date"] for o in ok))
    else:
        print("\n  none of the probed dates has a readable index.")
    print("  a covered date costs one 29-day window: about 1.0 GB and 4 minutes"
          " of scan.")
    return 0


def cmd_plan(event, half):
    ev = EVENTS.get(event)
    if ev is None:
        print("  %s is not in the EVENTS table. Known: %s"
              % (event, ", ".join(sorted(EVENTS))))
        return 1
    days = window_days(event, half)
    print("  event      %s   status %s" % (event, ev["status"]))
    print("  window     %s .. %s   (%d days, offsets %+d..%+d)"
          % (days[0], days[-1], len(days), -half, half))
    print("  slots      %s UTC, fixed; event day split at %02d:00 UTC downtime"
          % ("/".join("%02d:00" % h for h in SLOT_HOURS), DOWNTIME_MIN // 60))
    p = prediction(ev)
    if p is None:
        print("\n  NO PREDICTION. This row's rates are None because the change on this")
        print("  date is unverified. The window can be downloaded and looked at; it")
        print("  cannot be scored. %s" % ev["source"])
    else:
        b = ev["rates"]["base"]
        m = ev["rates"].get("minimum")
        print("\n  registered prediction, before any byte of this window was read:")
        print("    base tier      sales tax %.2f%% -> %.2f%%   broker fee %.2f%% -> %.2f%%"
              % (b["tax"][0], b["tax"][1], b["broker"][0], b["broker"][1]))
        if m:
            print("    minimum tier   sales tax %.2f%% -> %.2f%%   broker fee %.2f%% -> %.2f%%"
                  % (m["tax"][0], m["tax"][1], m["broker"][0], m["broker"][1]))
        else:
            print("    minimum tier   not quoted; the tax is damped by ACCT_R instead,"
                  " which is exact because the broker fee did not move")
        print("\n    ROUND TRIP  2*broker + tax, doubled for two hubs:")
        print("      unskilled %+.3f pp    trained %+.3f to %+.3f pp    band %+.3f to %+.3f pp"
              % (p["rt_base"], p["rt_skilled"][0], p["rt_skilled"][1],
                 p["rt_band"][0], p["rt_band"][1]))
        print("    TAX ONLY    the sales tax read by itself:")
        print("      unskilled %+.3f pp    trained %+.3f to %+.3f pp    band %+.3f to %+.3f pp"
              % (p["tx_base"], p["tx_skilled"][0], p["tx_skilled"][1],
                 p["tx_band"][0], p["tx_band"][1]))
        if p["opposite"]:
            print("\n    THE TWO MODELS HAVE OPPOSITE SIGNS ON THIS DATE.")
            print("    The sign of the measured step is therefore the criterion, and a")
            print("    sign needs no threshold. Round trip says the floor NARROWS;")
            print("    tax only says it WIDENS.")
    have = sum(1 for _d, _h, pth, _n in on_disk(event, half) if pth)
    want = len(days) * len(SLOT_HOURS)
    print("\n  snapshots  %d wanted, %d already on disk, %d to fetch"
          % (want, have, want - have))
    print("  size       about %.2f GB to fetch at %.1f MB per snapshot"
          % ((want - have) * BYTES_PER_SNAP / 1e9, BYTES_PER_SNAP / 1e6))
    print("\n  nothing was fetched. Re-run with --fetch %s --confirm" % event)
    return 0


def cmd_fetch(event, half, confirm):
    if event not in EVENTS:
        print("  %s is not in the EVENTS table." % event)
        return 1
    if not confirm:
        print("  --confirm not given. Showing the plan instead.\n")
        return cmd_plan(event, half)
    ledger_path = os.path.join(RESULTS, "eve_event_%s_ledger.json" % event)
    os.makedirs(RESULTS, exist_ok=True)
    ledger = {}
    if os.path.exists(ledger_path):
        try:
            ledger = json.load(open(ledger_path, encoding="utf-8"))
        except Exception:                                            # noqa: BLE001
            ledger = {}
    n_get = n_skip = n_fail = 0
    for day in window_days(event, half):
        d = os.path.join(RAW, day)
        os.makedirs(d, exist_ok=True)
        have = [f for f in sorted(os.listdir(d)) if f.endswith(".csv.bz2")]
        need = [h for h, _n, _o in pick_slots(have)]
        if len(need) == len(SLOT_HOURS):
            print("  %s  both slots already on disk" % day)
            n_skip += len(SLOT_HOURS)
            continue
        names, note = day_index(day)
        picks = pick_slots(names)
        if len(picks) < len(SLOT_HOURS):
            print("  %s  index gave %d usable slot(s). %s" % (day, len(picks), note))
        for h, name, off in picks:
            dst = os.path.join(d, name)
            if os.path.exists(dst):
                print("  %s %02d:00  SKIP  %s  %.1f MB"
                      % (day, h, name, os.path.getsize(dst) / 1e6))
                n_skip += 1
                continue
            url = "%s/%s/%s/%s" % (BASE, day[:4], day, name)
            status, body, err = get(url)
            if status != 200 or not body:
                print("  %s %02d:00  ---   %s  http %s %s" % (day, h, name, status, err))
                ledger["%s_%02d" % (day, h)] = {"name": name, "status": status,
                                                "err": err, "at": now_iso()}
                n_fail += 1
            else:
                tmp = dst + ".part"
                park(tmp)
                with open(tmp, "wb") as fh:
                    fh.write(body)
                os.replace(tmp, dst)
                print("  %s %02d:00  GET   %s  %.1f MB  (%+d min off target)"
                      % (day, h, name, len(body) / 1e6, off))
                ledger["%s_%02d" % (day, h)] = {"name": name, "status": 200,
                                                "bytes": len(body),
                                                "minutes_off": off, "at": now_iso()}
                n_get += 1
            # the ledger is written after every fetch, so an interrupted run
            # resumes from disk and the failures are not lost with the process
            json.dump(ledger, open(ledger_path, "w", encoding="utf-8", newline="\n"),
                      indent=2, sort_keys=True)
    print("\n  %d fetched, %d already on disk, %d failed" % (n_get, n_skip, n_fail))
    print("  ledger %s" % os.path.relpath(ledger_path, ROOT))
    print("  nothing was deleted; a file already on disk was not refetched.")
    return 0


def cmd_floor(event, half):
    ev = EVENTS.get(event)
    if ev is None:
        print("  %s is not in the EVENTS table." % event)
        return 1
    rows = on_disk(event, half)
    present = [r for r in rows if r[2]]
    if not present:
        print("  no snapshots on disk for this window. Run --fetch first.")
        return 1
    p = prediction(ev)
    print("  event %s (%s), %d of %d snapshots on disk\n"
          % (event, ev["status"], len(present), len(rows)))
    if p is None:
        print("  NO REGISTERED PREDICTION for this date. See the EVENTS table.")
        print("  The series below is printed anyway; it cannot be scored.\n")
    else:
        print("  PREDICTION, registered before this window was downloaded:")
        print("    ROUND TRIP  relsum floor steps by %+.3f to %+.3f pp"
              % (p["rt_band"][0], p["rt_band"][1]))
        print("    TAX ONLY    relsum floor steps by %+.3f to %+.3f pp"
              % (p["tx_band"][0], p["tx_band"][1]))
        if p["opposite"]:
            print("    the two have OPPOSITE SIGNS here, so the sign decides.")
        print("    Either way it is a STEP at the 11:00 UTC downtime on %s," % event)
        print("    not a slope through it.\n")

    # pass 1: read every snapshot once, keep only the per-type relsum maps
    per = []
    bad = []
    n_hit_cache = {}
    for day, hour, path, name in rows:
        if path is None:
            per.append((day, hour, None, None))
            continue
        rs, how, head = cached_relsums(day, hour, name, path)
        if rs is None:
            print("  %s %02d:00  UNREADABLE, skipped: %s  (%d bytes, %d header fields)"
                  % (day, hour, head["error"], head["file_bytes"],
                     head["n_header_fields"]))
            print("      header seen: %s" % head["header_seen"])
            bad.append({"day": day, "hour": hour, "file": name, **head})
            per.append((day, hour, None, None))
            continue
        n_hit_cache[how] = n_hit_cache.get(how, 0) + 1
        per.append((day, hour, rs, name))

    if n_hit_cache:
        print("  snapshots read: %s"
              % ", ".join("%d from %s" % (v, k) for k, v in sorted(n_hit_cache.items())))
        if n_hit_cache.get("scan"):
            print("  the scanned ones are now cached under %s; every later"
                  % os.path.relpath(CACHE, ROOT))
            print("  reading of this window is a file read, not a rescan.\n")
    pre = [d for day, hour, d, _n in per
           if d is not None and phase(day, hour, event) == "pre"]
    if not pre:
        print("  no readable PRE snapshot. Cannot fix the subset.")
        return 1
    chosen, counts = fixed_set(pre)
    print("  subset fixed on %d pre snapshot(s): %d types" % (len(pre), len(chosen)))
    print("    presence threshold sensitivity (median pre relsum <= %.2f throughout):"
          % CAP_RELSUM)
    for thr in sorted(counts):
        mark = "   <- registered" if abs(float(thr) - PRESENCE) < 1e-9 else ""
        print("      >= %s of pre snapshots: %6d types%s" % (thr, counts[thr], mark))
    if not chosen:
        print("\n  empty subset. Nothing further can be read.")
        return 1

    # pass 2: the daily series, in time order, one line per snapshot
    print("\n  daily series. relsum = -(S+S') in percentage points, on the fixed subset.")
    print("  %-10s %-5s %-4s %6s %8s %8s %8s %8s %8s"
          % ("day", "slot", "ph", "n", "p1", "p5", "p10", "p25", "p50"))
    series = []
    ev_day = event
    for day, hour, d, name in per:
        if d is None:
            print("  %-10s %02d:00 %-4s %6s   %s"
                  % (day, hour, phase(day, hour, ev_day), "-", "absent or unreadable"))
            continue
        v = sorted(d[t] for t in chosen if t in d)
        ph = phase(day, hour, ev_day)
        if not v:
            print("  %-10s %02d:00 %-4s %6d" % (day, hour, ph, 0))
            continue
        row = {"day": day, "hour": hour, "phase": ph, "n": len(v),
               "p1": quant(v, 0.01), "p5": quant(v, 0.05), "p10": quant(v, 0.10),
               "p25": quant(v, 0.25), "p50": quant(v, 0.50), "file": name}
        series.append(row)
        sep = "  <-- downtime, tax changes here" if (day == ev_day and hour == SLOT_HOURS[0]) else ""
        print("  %-10s %02d:00 %-4s %6d %7.3f%% %7.3f%% %7.3f%% %7.3f%% %7.3f%%%s"
              % (day, hour, ph, len(v), 100 * row["p1"], 100 * row["p5"],
                 100 * row["p10"], 100 * row["p25"], 100 * row["p50"], sep))

    # the step, read off the series rather than estimated
    print("\n  step, as median of each phase's per-snapshot quantile:")
    out = {"at": now_iso(), "event": event, "event_status": ev["status"],
           "half": half, "cap_relsum": CAP_RELSUM, "presence": PRESENCE,
           "slot_hours": list(SLOT_HOURS), "n_types": len(chosen),
           "presence_sensitivity": counts, "series": series, "unreadable": bad,
           "prediction_pp": p}
    steps = {}
    for q in ("p1", "p5", "p10", "p25", "p50"):
        a = sorted(r[q] for r in series if r["phase"] == "pre")
        b = sorted(r[q] for r in series if r["phase"] == "post")
        if not a or not b:
            continue
        step = 100 * (quant(b, 0.5) - quant(a, 0.5))
        steps[q] = step
        verdict = ""
        if p is not None:
            lo, hi = p["rt_band"]
            if lo <= step <= hi:
                verdict = "  inside the ROUND TRIP band"
            elif p["tx_band"][0] <= step <= p["tx_band"][1]:
                verdict = "  inside the TAX ONLY band"
            elif step < lo:
                verdict = "  below both bands"
            else:
                verdict = "  above both bands"
        print("    %-4s pre %7.3f%%  post %7.3f%%  step %+7.3f pp%s"
              % (q, 100 * quant(a, 0.5), 100 * quant(b, 0.5), step, verdict))
    out["steps_pp"] = steps
    if p is not None:
        print("\n    round trip band %+.3f to %+.3f pp;  tax only band %+.3f to %+.3f pp"
              % (p["rt_band"][0], p["rt_band"][1], p["tx_band"][0], p["tx_band"][1]))
    print("\n  the series above is the reading. A step and a slope look different")
    print("  on it, which is the thing a placebo band could not do in B16.")

    os.makedirs(RESULTS, exist_ok=True)
    dst = os.path.join(RESULTS, "eve_event_%s_floor.json" % event)
    park(dst)
    json.dump(out, open(dst, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("  wrote %s" % os.path.relpath(dst, ROOT))
    print("  no cross-hub price ratio was formed.")
    return 0


def rho_map(qs, chosen):
    """({type_id: rho} inside Theorem 6(4)'s domain, n_computable, n_excluded).

    Every (snapshot, type) pair is decided HERE and nowhere else, exactly once.
    The first shape of this code put the decision in a helper that three
    separate passes each called over overlapping data, so the number it
    reported was a touch count rather than an exclusion count: 10,222 against
    4,672 real exclusions. One increment site was not enough, because the site
    was reached three times. Counting belongs where the pass is, not where the
    predicate is."""
    keep, n_comp, n_over = {}, 0, 0
    for t in chosen:
        q = qs.get(t)
        if q is None:
            continue
        r = q_rho(q)
        if r is None:
            continue
        n_comp += 1
        if r > 1.0:
            n_over += 1
            continue
        keep[t] = r
    return keep, n_comp, n_over


def window_read(event, half, settle_days=None, quiet=True):
    """One window's reading, and the ONLY place the two halves are computed.

    `cmd_rho` prints what this returns and `cmd_nulls` loops it, so a placebo
    date and a real event can never be read by two different pieces of
    arithmetic. That property is the whole point of the function existing: a
    null distribution built by a second code path measures the second code
    path.

    Returns None when the window has no readable pre or post side. Everything
    it needs is in the quote cache, so a window already scanned costs nothing."""
    settle_days = SETTLE_DAYS if settle_days is None else settle_days
    rows = [r for r in on_disk(event, half) if r[2]]
    if not rows:
        return None
    e = datetime.date(*[int(x) for x in event.split("-")])
    settle = (e + datetime.timedelta(days=settle_days)).isoformat()
    snaps, bad, n_how = [], [], {}
    for day, hour, path, name in rows:
        qs, how, head = cached_quotes(day, hour, name, path)
        if qs is None:
            bad.append(name)
            continue
        n_how[how] = n_how.get(how, 0) + 1
        ph = phase(day, hour, event)
        snaps.append((day, hour, ph, day >= settle and ph == "post", qs))
    pre = [x for x in snaps if x[2] == "pre"]
    post = [x for x in snaps if x[2] == "post"]
    sett = [x for x in snaps if x[3]]
    if not pre or not sett:
        return None
    chosen, _c = fixed_set([{t: q_relsum(q) for t, q in x[4].items()} for x in pre])
    if not chosen:
        return None
    RM = {(x[0], x[1]): rho_map(x[4], chosen) for x in snaps}

    def med(v):
        v = sorted(v)
        return v[len(v) // 2] if v else None

    def pool(group, fn):
        per = []
        for x in group:
            v = [fn(x[4][t]) for t in chosen if t in x[4]]
            v = [y for y in v if y is not None and y == y]
            if v:
                per.append(med(v))
        return med(per), len(per)

    def pool_rho(group):
        per = [med(list(RM[(x[0], x[1])][0].values()))
               for x in group if RM[(x[0], x[1])][0]]
        return med(per), len(per)

    def excl(group):
        c = sum(RM[(x[0], x[1])][1] for x in group)
        o = sum(RM[(x[0], x[1])][2] for x in group)
        return c, o, (100.0 * o / c if c else float("nan"))

    absdiff = lambda q: None if q_logdiff(q) is None else abs(q_logdiff(q))  # noqa: E731
    rel_j = lambda q: (q[1] - q[0]) / (0.5 * (q[0] + q[1]))                  # noqa: E731
    rel_a = lambda q: (q[3] - q[2]) / (0.5 * (q[2] + q[3]))                  # noqa: E731
    gj0, _ = pool(pre, rel_j)
    gj1, _ = pool(sett, rel_j)
    ga0, _ = pool(pre, rel_a)
    ga1, _ = pool(sett, rel_a)
    n0, _ = pool(pre, absdiff)
    n1, _ = pool(sett, absdiff)
    d0, _ = pool(pre, q_logsum)
    d1, _ = pool(sett, q_logsum)
    r0, np_ = pool_rho(pre)
    r1, ns_ = pool_rho(sett)
    cp, op, rp = excl(pre)
    cs, os_, rs = excl(sett)
    ca, oa, ra = excl(post)
    series = []
    for day, hour, ph, st_, qs in snaps:
        v = list(RM[(day, hour)][0].values())
        if not v:
            continue
        series.append({"day": day, "hour": hour, "phase": ph, "settled": st_,
                       "n": len(v), "rho": med(v),
                       "num": med([abs(x) for x in
                                   (q_logdiff(qs[t]) for t in chosen if t in qs)
                                   if x is not None]),
                       "den": med([x for x in
                                   (q_logsum(qs[t]) for t in chosen if t in qs)
                                   if x is not None])})
    return {
        "event": event, "half": half, "settle_from": settle,
        "settle_days": settle_days, "n_types": len(chosen),
        "n_pre": len(pre), "n_post": len(post), "n_settled": len(sett),
        "how": n_how, "unreadable": bad,
        "gate": {"jita_ratio": gj1 / gj0, "amarr_ratio": ga1 / ga0,
                 "jita_pre": gj0, "jita_settled": gj1,
                 "amarr_pre": ga0, "amarr_settled": ga1,
                 "abs_diff": abs(gj1 / gj0 - ga1 / ga0), "sd_scale": 0.071,
                 "common": abs(gj1 / gj0 - ga1 / ga0) <= 3 * 0.071},
        "halves": {"num_pre": n0, "num_settled": n1, "num_factor": n1 / n0,
                   "den_pre": d0, "den_settled": d1, "den_factor": d1 / d0,
                   #: the statistic the null is for. 1.0 means both halves
                   #: scaled together, which is what a volatility shock does
                   #: and what 2025 read. Below 1.0 means the friction half
                   #: outgrew the index half, which is what a friction lever
                   #: should do.
                   "factor_ratio": (n1 / n0) / (d1 / d0)},
        "rho": {"pre": r0, "settled": r1, "ratio": r1 / r0,
                "predicted_ratio": d0 / d1, "gap": r1 / r0 - d0 / d1,
                "n_pre_snaps": np_, "n_settled_snaps": ns_},
        "domain": {"pre": {"computable": cp, "excluded": op, "rate_pct": rp},
                   "settled": {"computable": cs, "excluded": os_, "rate_pct": rs},
                   "all_post": {"computable": ca, "excluded": oa, "rate_pct": ra},
                   "rate_move_pp": rs - rp},
        "series": series,
    }


def cmd_nulls(event, half, settle_days, step):
    """The null distribution for `factor_ratio`, built from placebo dates that
    lie entirely inside the real window's PRE period.

    Why this is needed. `--rho` returned 1.0387 on the 2025 window and 0.8911
    on the 2021 one, and the second is read as a friction-specific component.
    Two numbers are not a distribution, and B16 died of exactly this: a band
    that could not see the drift its real window sat on, because no placebo
    sub-window straddled offset 0 by construction. Here every placebo does
    straddle its own offset 0, and every one is read by window_read, the same
    function that reads the real event.

    Registered before the first run: the real event's factor_ratio is read
    against the spread of the placebos', and nothing is thresholded. If the
    real value sits inside the placebo spread, the friction-specific component
    is not distinguishable from what this market does on an ordinary week."""
    if event not in EVENTS:
        print("  %s is not in the EVENTS table." % event)
        return 1
    e = datetime.date(*[int(x) for x in event.split("-")])
    #: a placebo is admissible only if its whole window, both sides, lies
    #: strictly before the event day. Otherwise the "null" contains the event.
    first = None
    for k in range(-400, 0):
        d = (e + datetime.timedelta(days=k)).isoformat()
        if os.path.isdir(os.path.join(RAW, d)):
            first = d
            break
    if first is None:
        print("  no days on disk before %s." % event)
        return 1
    f = datetime.date(*[int(x) for x in first.split("-")])
    cands = []
    k = half
    while True:
        c = f + datetime.timedelta(days=k)
        if (c + datetime.timedelta(days=half)) >= e:
            break
        cands.append(c.isoformat())
        k += step
    print("  real event   %s" % event)
    print("  pre period   %s .. %s" % (first, (e - datetime.timedelta(days=1)).isoformat()))
    print("  placebos     %d dates, each with a full +-%d day window strictly"
          " inside that period" % (len(cands), half))
    print("  settle_days  %d  (0 means the whole post side counts)\n" % settle_days)
    if not cands:
        print("  the pre period is too short for a +-%d window. Use a smaller --half."
              % half)
        return 1

    print("  %-12s %6s %9s %9s %11s %9s %9s"
          % ("date", "types", "num_fac", "den_fac", "factor_ratio", "rho_fac", "excl_pp"))
    out = []
    for c in cands:
        r = window_read(c, half, settle_days)
        if r is None:
            print("  %-12s  unreadable window, skipped" % c)
            continue
        out.append(r)
        print("  %-12s %6d %9.4f %9.4f %11.4f %9.4f %+9.2f"
              % (c, r["n_types"], r["halves"]["num_factor"], r["halves"]["den_factor"],
                 r["halves"]["factor_ratio"], r["rho"]["ratio"],
                 r["domain"]["rate_move_pp"]))
    real = window_read(event, half, settle_days)
    if real is None:
        print("\n  the real window is unreadable at this half.")
        return 1
    print("  %s" % ("-" * 74))
    print("  %-12s %6d %9.4f %9.4f %11.4f %9.4f %+9.2f   <== REAL"
          % (event, real["n_types"], real["halves"]["num_factor"],
             real["halves"]["den_factor"], real["halves"]["factor_ratio"],
             real["rho"]["ratio"], real["domain"]["rate_move_pp"]))

    v = sorted(r["halves"]["factor_ratio"] for r in out)
    x = real["halves"]["factor_ratio"]
    if len(v) >= 2:
        m = v[len(v) // 2]
        sd = (sum((y - sum(v) / len(v)) ** 2 for y in v) / (len(v) - 1)) ** 0.5
        below = sum(1 for y in v if y < x)
        print("\n  factor_ratio, the statistic:")
        print("    placebos  n %d   min %.4f   median %.4f   max %.4f   sd %.4f"
              % (len(v), v[0], m, v[-1], sd))
        print("    real      %.4f   %d of %d placebos are below it   %+.2f sd from"
              " the placebo median" % (x, below, len(v), (x - m) / sd if sd else 0))
        print("    %s" % ("the real value is OUTSIDE the placebo range"
                          if (x < v[0] or x > v[-1]) else
                          "the real value is INSIDE the placebo range, so the "
                          "friction-specific component is not distinguishable "
                          "from an ordinary week"))
    os.makedirs(RESULTS, exist_ok=True)
    dst = os.path.join(RESULTS, "eve_event_%s_nulls.json" % event)
    park(dst)
    json.dump({"at": now_iso(), "event": event, "half": half,
               "settle_days": settle_days, "step": step,
               "real": {k: real[k] for k in ("halves", "rho", "domain", "gate",
                                             "n_types")},
               "placebos": [{"date": r["event"], "n_types": r["n_types"],
                             "halves": r["halves"], "rho": r["rho"],
                             "domain_move_pp": r["domain"]["rate_move_pp"]}
                            for r in out]},
              open(dst, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(dst, ROOT))
    return 0


def cmd_rho(event, half):
    """rho = |S-S'| / -(S+S') across the event, with the commonality gate first.

    THE GATE COMES FIRST AND CAN STOP THIS COMMAND.
    Theorem 6(5) needs the relative spread change to be COMMON to both classes.
    Here the classes are the two hubs, so before rho means anything, Jita's own
    relative spread and Amarr's own relative spread must have widened by the
    same factor. If they did not, the shock was not common, rho's move mixes a
    friction change with an index change, and this command says so and stops
    reading rather than printing a number that cannot be interpreted.

    THE PREDICTION, derived not assumed.
    --shape measured the denominator widening at x1.270 over bins 2-10, sd
    0.071. If the widening is common the numerator |S-S'| is untouched, so

        rho_post / rho_pre  =  1 / (denominator widening)

    which the code computes from the denominator ratio it measures here, so a
    different denominator gives a different prediction rather than a silent
    agreement with a hardcoded 0.787.

    Three readings, all decidable by eye:
      rho falls by 1/ratio        -> the widening was common; 6(5) holds here
      rho flat                    -> the index half widened by the same factor,
                                     so the shock was not a pure friction move
      rho moves some other way    -> report the amount, claim nothing"""
    ev = EVENTS.get(event)
    if ev is None:
        print("  %s is not in the EVENTS table." % event)
        return 1
    rows = [r for r in on_disk(event, half) if r[2]]
    if not rows:
        print("  no snapshots on disk. Run --fetch first.")
        return 1
    e = datetime.date(*[int(x) for x in event.split("-")])
    settle = (e + datetime.timedelta(days=SETTLE_DAYS)).isoformat()

    snaps, bad, n_how = [], [], {}
    for day, hour, path, name in rows:
        qs, how, head = cached_quotes(day, hour, name, path)
        if qs is None:
            bad.append(name)
            continue
        n_how[how] = n_how.get(how, 0) + 1
        ph = phase(day, hour, event)
        snaps.append((day, hour, ph, day >= settle and ph == "post", qs))
    print("  snapshots read: %s%s"
          % (", ".join("%d from %s" % (v, k) for k, v in sorted(n_how.items())),
             ", %d unreadable" % len(bad) if bad else ""))
    pre = [x for x in snaps if x[2] == "pre"]
    post = [x for x in snaps if x[2] == "post"]
    sett = [x for x in snaps if x[3]]
    if not pre or not sett:
        print("  need both a pre and a settled-post window.")
        return 1
    chosen, _c = fixed_set([{t: q_relsum(q) for t, q in x[4].items()} for x in pre])
    print("  subset %d types, fixed on %d pre snapshot(s); settled post from %s"
          % (len(chosen), len(pre), settle))

    def med(v):
        v = sorted(v)
        return v[len(v) // 2] if v else None

    def pool(group, fn):
        """median across snapshots of the within-snapshot median over the subset"""
        per = []
        for _d, _h, _p, _s, qs in group:
            v = [fn(qs[t]) for t in chosen if t in qs]
            v = [x for x in v if x is not None and x == x]
            if v:
                per.append(med(v))
        return med(per), len(per)

    #: decided once per (snapshot, type), then read from here by everything
    RM = {(x[0], x[1]): rho_map(x[4], chosen) for x in snaps}

    def pool_rho(group):
        per = [med(list(RM[(x[0], x[1])][0].values()))
               for x in group if RM[(x[0], x[1])][0]]
        return med(per), len(per)

    def excl(group):
        comp = sum(RM[(x[0], x[1])][1] for x in group)
        over = sum(RM[(x[0], x[1])][2] for x in group)
        return comp, over, (100.0 * over / comp if comp else float("nan"))

    rel_j = lambda q: (q[1] - q[0]) / (0.5 * (q[0] + q[1]))          # noqa: E731
    rel_a = lambda q: (q[3] - q[2]) / (0.5 * (q[2] + q[3]))          # noqa: E731

    print("\n  GATE: is the widening COMMON to both hubs?")
    print("  the two must agree; --shape measured the bin-to-bin sd of the")
    print("  widening at 0.071, which is the scale a disagreement is read against.")
    gj_pre, _ = pool(pre, rel_j)
    gj_post, _ = pool(sett, rel_j)
    ga_pre, _ = pool(pre, rel_a)
    ga_post, _ = pool(sett, rel_a)
    rj, ra = gj_post / gj_pre, ga_post / ga_pre
    print("    Jita     pre %7.3f%%  settled %7.3f%%   x%.3f" % (100 * gj_pre, 100 * gj_post, rj))
    print("    Amarr    pre %7.3f%%  settled %7.3f%%   x%.3f" % (100 * ga_pre, 100 * ga_post, ra))
    print("    difference between the two factors: %.3f  (bin-to-bin sd was 0.071)"
          % abs(rj - ra))
    common = abs(rj - ra) <= 3 * 0.071
    print("    -> %s" % ("COMMON to within three times that sd; rho is readable"
                         if common else
                         "NOT common; the two hubs moved by different factors, so "
                         "rho below mixes a friction move with an index move"))

    print("\n  the two halves, exact logs, on the fixed subset:")
    num_pre, _ = pool(pre, lambda q: None if q_logdiff(q) is None else abs(q_logdiff(q)))
    num_post, _ = pool(sett, lambda q: None if q_logdiff(q) is None else abs(q_logdiff(q)))
    den_pre, _ = pool(pre, q_logsum)
    den_post, _ = pool(sett, q_logsum)
    print("    |S-S'|  index half     pre %8.5f  settled %8.5f   x%.3f"
          % (num_pre, num_post, num_post / num_pre))
    print("    -(S+S') friction half  pre %8.5f  settled %8.5f   x%.3f"
          % (den_pre, den_post, den_post / den_pre))
    pred = den_pre / den_post
    print("\n  PREDICTION, computed from the denominator just measured, not hardcoded:")
    print("    if the widening is common, |S-S'| is untouched and")
    print("    rho_post / rho_pre = 1 / %.3f = %.3f  (a fall of %.1f%%)"
          % (den_post / den_pre, pred, 100 * (1 - pred)))

    r_pre, n1 = pool_rho(pre)
    r_post, n2 = pool_rho(sett)
    got = r_post / r_pre
    print("\n  rho = |S-S'| / -(S+S'):")
    print("    pre     %.5f   (%d snapshots)" % (r_pre, n1))
    print("    settled %.5f   (%d snapshots)" % (r_post, n2))
    print("    ratio   %.3f    predicted %.3f    gap %+.3f" % (got, pred, got - pred))

    #: The exclusion is a selection, so its RATE has to be read on both sides.
    #: If the post window drops more readings, the surviving post sample leans
    #: toward small rho and the measured move is understated. Printed here
    #: rather than left to a script, because it is part of the reading.
    cp, op, rp_ = excl(pre)
    cs, os_, rs_ = excl(sett)
    ca, oa, ra_ = excl(post)
    print("\n    outside [0,1], excluded and not clipped, per type-snapshot pair:")
    print("      pre       %6d of %6d  %5.2f%%" % (op, cp, rp_))
    print("      settled   %6d of %6d  %5.2f%%" % (os_, cs, rs_))
    print("      all post  %6d of %6d  %5.2f%%" % (oa, ca, ra_))
    print("      the rate moves %+.2f pp across the event. A rate that rises on"
          % (rs_ - rp_))
    print("      the post side biases the kept sample toward small rho, so it")
    print("      makes the measured move an understatement, never an artefact.")

    print("\n  daily series, median rho per snapshot. Read the stream.")
    series = []
    for day, hour, ph, st_, qs in snaps:
        v = list(RM[(day, hour)][0].values())
        if not v:
            continue
        m = med(v)
        series.append({"day": day, "hour": hour, "phase": ph, "settled": st_,
                       "n": len(v), "rho": m,
                       "num": med([abs(x) for x in
                                   (q_logdiff(qs[t]) for t in chosen if t in qs)
                                   if x is not None]),
                       "den": med([x for x in
                                   (q_logsum(qs[t]) for t in chosen if t in qs)
                                   if x is not None])})
        mark = "  <== downtime" if (day == event and hour == SLOT_HOURS[0]) else ""
        print("    %-10s %02d:00 %-4s n %5d  rho %.5f  |S-S'| %8.5f  -(S+S') %8.5f%s"
              % (day, hour, ph, len(v), m, series[-1]["num"], series[-1]["den"], mark))

    out = {"at": now_iso(), "event": event, "event_status": ev["status"],
           "settle_from": settle, "n_types": len(chosen),
           "gate": {"jita_ratio": rj, "amarr_ratio": ra, "abs_diff": abs(rj - ra),
                    "sd_scale": 0.071, "common": common},
           "halves": {"num_pre": num_pre, "num_settled": num_post,
                      "den_pre": den_pre, "den_settled": den_post},
           "rho": {"pre": r_pre, "settled": r_post, "ratio": got,
                   "predicted_ratio": pred, "gap": got - pred},
           "domain": {"pre": {"computable": cp, "excluded": op, "rate_pct": rp_},
                      "settled": {"computable": cs, "excluded": os_, "rate_pct": rs_},
                      "all_post": {"computable": ca, "excluded": oa, "rate_pct": ra_},
                      "rate_move_pp": rs_ - rp_},
           "series": series, "unreadable": bad}
    os.makedirs(RESULTS, exist_ok=True)
    dst = os.path.join(RESULTS, "eve_event_%s_rho.json" % event)
    park(dst)
    json.dump(out, open(dst, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(dst, ROOT))
    return 0


def cv(v):
    """Coefficient of variation, |sd/mean|. Used only to say which of two
    printed columns is the flatter one. No line is drawn on it."""
    n = len(v)
    if n < 2:
        return None
    m = sum(v) / n
    if m == 0:
        return None
    var = sum((x - m) ** 2 for x in v) / (n - 1)
    return abs(var ** 0.5 / m)


def cmd_shape(event, half, nbin):
    """Additive or proportional? The two stories make different pictures and
    this prints both columns of it.

    A sales tax raises the break-even spread `2*broker + tax` by the same
    number of percentage points for every item, whatever that item is and
    however wide its own spread was. So the tax story says the Delta column is
    FLAT across pre-spread bins, sitting inside the registered band.

    A cost or supply shock scales with the item's own price process, so it says
    the RATIO column is flat instead and Delta grows with the bin.

    Registered before this command was first run: whichever of the two columns
    is flatter, by its own coefficient of variation across bins, is the shape
    this window has. No threshold is placed on either number."""
    ev = EVENTS.get(event)
    if ev is None:
        print("  %s is not in the EVENTS table." % event)
        return 1
    rows = [r for r in on_disk(event, half) if r[2]]
    if not rows:
        print("  no snapshots on disk. Run --fetch first.")
        return 1
    e = datetime.date(*[int(x) for x in event.split("-")])
    settle = (e + datetime.timedelta(days=SETTLE_DAYS)).isoformat()
    pre_maps, post_maps, set_maps, bad = [], [], [], []
    n_how = {}
    for day, hour, path, name in rows:
        rs, how, head = cached_relsums(day, hour, name, path)
        if rs is None:
            bad.append(name)
            continue
        n_how[how] = n_how.get(how, 0) + 1
        if phase(day, hour, event) == "pre":
            pre_maps.append(rs)
        else:
            post_maps.append(rs)
            if day >= settle:
                set_maps.append(rs)
    print("  snapshots read: %s%s"
          % (", ".join("%d from %s" % (v, k) for k, v in sorted(n_how.items())),
             ", %d unreadable" % len(bad) if bad else ""))
    if not pre_maps or not set_maps:
        print("  need both a pre and a settled-post window.")
        return 1
    chosen, _counts = fixed_set(pre_maps)
    print("  subset %d types, fixed on %d pre snapshot(s)" % (len(chosen), len(pre_maps)))
    print("  settled post = %s onward (%d snapshots); full post = %d snapshots"
          % (settle, len(set_maps), len(post_maps)))

    p = prediction(ev)
    if p is not None:
        print("\n  the two stories, stated before the columns below were printed:")
        print("    FEE          Delta is FLAT at %+.3f to %+.3f pp in every bin"
              % (p["rt_band"][0], p["rt_band"][1]))
        print("    COST/SUPPLY  Ratio is FLAT instead, and Delta grows with the bin")

    #: per item, the median across snapshots. An item needs at least five
    #: readings on each side; five is the project's reference repetition count
    #: and nothing here is estimating a rate.
    def med(v):
        v = sorted(v)
        return v[len(v) // 2]

    items = []
    for t in sorted(chosen):
        a = [m[t] for m in pre_maps if t in m]
        b = [m[t] for m in set_maps if t in m]
        c = [m[t] for m in post_maps if t in m]
        if len(a) < 5 or len(b) < 5:
            continue
        items.append((med(a), med(b), med(c)))
    if not items:
        print("  no item has five readings on both sides.")
        return 1
    items.sort()
    print("\n  %d of %d types have >= 5 readings on each side\n" % (len(items), len(chosen)))

    print("  %-4s %6s %9s %10s %11s %9s %11s %9s"
          % ("bin", "n", "pre", "post(set)", "DELTA(set)", "RATIO", "DELTA(all)", "RATIO"))
    per_bin = max(1, len(items) // nbin)
    dset, rset, dall, rall = [], [], [], []
    for i in range(nbin):
        chunk = items[i * per_bin: (i + 1) * per_bin if i < nbin - 1 else len(items)]
        if not chunk:
            continue
        a = med([x[0] for x in chunk])
        b = med([x[1] for x in chunk])
        c = med([x[2] for x in chunk])
        d1, d2 = 100 * (b - a), 100 * (c - a)
        r1, r2 = (b / a if a else float("nan")), (c / a if a else float("nan"))
        dset.append(d1); rset.append(r1); dall.append(d2); rall.append(r2)
        flag = ""
        if p is not None and p["rt_band"][0] <= d1 <= p["rt_band"][1]:
            flag = "  <- in band"
        print("  %-4d %6d %8.3f%% %9.3f%% %+10.3fpp %9.3fx %+10.3fpp %9.3fx%s"
              % (i + 1, len(chunk), 100 * a, 100 * b, d1, r1, d2, r2, flag))

    print("\n  flatness, coefficient of variation across bins (smaller is flatter):")
    print("    settled:  Delta %.3f    Ratio %.3f    ->  %s"
          % (cv(dset), cv(rset),
             "ADDITIVE, the tax shape" if cv(dset) < cv(rset)
             else "PROPORTIONAL, not the tax shape"))
    print("    full post:Delta %.3f    Ratio %.3f    ->  %s"
          % (cv(dall), cv(rall),
             "ADDITIVE, the tax shape" if cv(dall) < cv(rall)
             else "PROPORTIONAL, not the tax shape"))
    if p is not None:
        print("\n    the registered round-trip band was %+.3f to %+.3f pp, flat."
              % (p["rt_band"][0], p["rt_band"][1]))
    print("\n  this is a picture, not a regression. Nothing was fitted.")

    out = {"at": now_iso(), "event": event, "event_status": ev["status"],
           "settle_from": settle, "n_items": len(items), "n_bins": nbin,
           "bins": [{"n": len(items[i * per_bin:(i + 1) * per_bin]),
                     "delta_settled_pp": dset[i], "ratio_settled": rset[i],
                     "delta_allpost_pp": dall[i], "ratio_allpost": rall[i]}
                    for i in range(len(dset))],
           "cv": {"delta_settled": cv(dset), "ratio_settled": cv(rset),
                  "delta_allpost": cv(dall), "ratio_allpost": cv(rall)},
           "prediction_pp": p}
    os.makedirs(RESULTS, exist_ok=True)
    dst = os.path.join(RESULTS, "eve_event_%s_shape.json" % event)
    park(dst)
    json.dump(out, open(dst, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("  wrote %s" % os.path.relpath(dst, ROOT))
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    top = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

    # --- 1..3 the window and the split ------------------------------------
    d = window_days("2025-03-12", 14)
    chk("1  window is 2*half+1 days and centred on the event",
        len(d) == 29 and d[14] == "2025-03-12"
        and d[0] == "2025-02-26" and d[-1] == "2025-03-26")
    chk("2  the event day is SPLIT at downtime, 06:00 pre and 18:00 post",
        phase("2025-03-12", 6, "2025-03-12") == "pre"
        and phase("2025-03-12", 18, "2025-03-12") == "post")
    chk("3  phase is monotone across the window",
        all(phase(day, h, "2025-03-12") == ("pre" if (day, h) <= ("2025-03-12", 6) else "post")
            for day in d for h in SLOT_HOURS))

    # --- 4..5 slot picking -------------------------------------------------
    names = ["market-orders-2025-03-12_%02d-%02d-06.v3.csv.bz2" % (h, m)
             for h in range(24) for m in (15, 45)]
    got = dict((h, n) for h, n, _o in pick_slots(names))
    chk("4  nearest slot to 06:00 is 05:45, not 06:15, and to 18:00 is 17:45",
        got[6].endswith("05-45-06.v3.csv.bz2") and got[18].endswith("17-45-06.v3.csv.bz2"))
    chk("5  clock distance wraps at midnight",
        pick_slots(["market-orders-2025-03-12_23-45-06.v3.csv.bz2",
                    "market-orders-2025-03-12_03-15-06.v3.csv.bz2"], (0,))[0][2] == 15)

    # --- 6..7 one reader of the archive ------------------------------------
    chk("6  this file defines no scanner of its own; scan_one is imported",
        "scan_one" not in top and "scan" not in top and "day_index" not in top)
    chk("7  scan_one, day_index, park and HUBS all come from eve_market_probe",
        any(isinstance(n, ast.ImportFrom) and n.module == "eve_market_probe"
            and {a.name for a in n.names} >= {"scan_one", "day_index", "park", "HUBS"}
            for n in ast.walk(tree)))

    # --- 8..10 the prediction is computed, not asserted ---------------------
    p = prediction(EVENTS["2025-03-12"])
    chk("8  2025 reproduces the band registered on 2026-08-23 to the digit: "
        "trained +3.080 to +3.150 pp, unskilled +7.000 pp",
        p is not None and abs(p["rt_skilled"][0] - 3.080) < 1e-9
        and abs(p["rt_skilled"][1] - 3.150) < 1e-9
        and abs(p["rt_base"] - 7.0) < 1e-9)
    chk("9  2025 moved no broker fee, so round trip and tax only coincide "
        "there and cannot disagree in sign",
        p["rt_band"] == p["tx_band"] and p["opposite"] is False)

    q = prediction(EVENTS["2021-10-13"])
    #: base 2*(8.0-5.0 + 2*(3.0-5.0)) = -2.0 ; minimum 2*(3.6-2.25 + 2*(1.0-3.0)) = -5.3
    chk("10 2021 round trip is 2*d_broker + d_tax at both quoted tiers: "
        "-2.000 pp unskilled, -5.300 pp trained",
        abs(q["rt_base"] + 2.0) < 1e-9 and abs(q["rt_skilled"][0] + 5.3) < 1e-9)
    #: tax alone: base 2*3.0 = +6.0 ; minimum 2*1.35 = +2.7
    chk("11 2021 tax-only is positive at both tiers, +6.000 and +2.700 pp, so "
        "the two models disagree in SIGN and the sign is the criterion",
        abs(q["tx_base"] - 6.0) < 1e-9 and abs(q["tx_skilled"][0] - 2.7) < 1e-9
        and q["opposite"] is True and q["rt_band"][1] < 0 < q["tx_band"][0])

    # --- 12 the unverified row cannot be scored ----------------------------
    chk("12 the UNVERIFIED date has None rates, so prediction() returns None "
        "by construction and not by remembering",
        EVENTS["2024-07-25"]["rates"] is None
        and prediction(EVENTS["2024-07-25"]) is None
        and EVENTS["2025-03-12"]["status"] == "CONFIRMED")

    # --- 13..14 quantile and relsum, against hand arithmetic ---------------
    v = [float(i) for i in range(100)]
    chk("13 quant uses floor(q*n) on a sorted list, same as the probe",
        quant(v, 0.01) == 1.0 and quant(v, 0.5) == 50.0 and quant(v, 1.0) == 99.0)
    book = {(JITA, 1): [99.0, 101.0], (AMARR, 1): [98.0, 102.0],
            (JITA, 2): [10.0, 11.0], (AMARR, 2): [None, 12.0],
            (JITA, 3): [5.0, 4.0]}
    rs = relsums(book)
    #: type 1: 2/100 + 4/100 = 0.06. type 2 one-sided at Amarr, type 3 crossed.
    chk("14 relsum is the SUM of the two one-way spreads; crossed and "
        "one-sided books are dropped",
        set(rs) == {1} and abs(rs[1] - 0.06) < 1e-12)

    # --- 15..16 the subset is fixed on pre, and both filters bite ----------
    pre = [{1: 0.05, 2: 0.05, 3: 0.50}, {1: 0.05, 3: 0.50},
           {1: 0.05, 2: 0.05, 3: 0.50}, {1: 0.05, 2: 0.05, 3: 0.50},
           {1: 0.05, 2: 0.05, 3: 0.50}]
    chosen, counts = fixed_set(pre)
    chk("15 a type absent from more than 20% of pre snapshots is kept at 0.80 "
        "but dropped at 0.90",
        chosen == {1, 2} and counts["0.90"] == 1 and counts["0.80"] == 2)
    chk("16 a type whose median pre relsum exceeds the cap is dropped at every "
        "presence threshold",
        3 not in chosen and all(c <= 2 for c in counts.values()))

    # --- 17..19 house rules -------------------------------------------------
    #: These two walk the tree rather than grepping the text. A substring
    #: check here would match the forbidden names inside its OWN literal list
    #: and inside this comment, which is the eight-times pitfall this project
    #: has already paid for once: a guard that counts its own source.
    banned = {"remove", "rmtree", "unlink", "rmdir", "removedirs"}
    deletes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
               and ((isinstance(n.func, ast.Attribute) and n.func.attr in banned)
                    or (isinstance(n.func, ast.Name) and n.func.id in banned))]
    chk("17 no delete call anywhere in the tree; park() is the only disposal",
        not deletes and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "park" for n in ast.walk(tree)))

    opens, bad_open = 0, []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "open"):
            continue
        opens += 1
        mode = ""
        if len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
            mode = str(n.args[1].value)
        kw = {k.arg for k in n.keywords}
        if "b" in mode:
            if kw & {"encoding", "newline"}:
                bad_open.append("binary open carrying a text kwarg")
        elif any(c in mode for c in "wax"):
            if not {"encoding", "newline"} <= kw:
                bad_open.append("text write without encoding+newline: mode %r" % mode)
        elif "encoding" not in kw:
            bad_open.append("text read without encoding")
    chk("18 every text write pins encoding and newline, every text read pins "
        "encoding, and no binary open pretends to be text (%d open calls)" % opens,
        opens >= 5 and not bad_open)
    for b in bad_open:
        print("       " + b)
    chk("19 --fetch refuses to run without --confirm",
        "if not confirm:" in src)

    # --- 20 the reading rule is in the file, not in a chat log --------------
    doc = ast.get_docstring(tree) or ""
    chk("20 the reading rule, the predicted band and the failure shapes are in "
        "the module docstring",
        "READING RULE" in doc and "3.080" in doc and "READ AS FAILURE" in doc)

    # --- 21..24 the cache and the shape discriminator ----------------------
    import tempfile                                                  # noqa: PLC0415
    global CACHE
    real_cache, CACHE = CACHE, tempfile.mkdtemp(prefix="eve_cache_selftest_")
    try:
        os.makedirs(CACHE, exist_ok=True)
        cp = cache_path("2099-01-01", 6, "snap-A.csv.bz2")
        json.dump({"file": "snap-A.csv.bz2", "relsum": {"7": 0.0625, "9": 0.125}},
                  open(cp, "w", encoding="utf-8", newline="\n"),
                  indent=None, sort_keys=True)
        got, how, _h = cached_relsums("2099-01-01", 6, "snap-A.csv.bz2", "/no/such/file")
        chk("21 a cache written for this filename is read back with int keys, "
            "without touching the snapshot",
            how == "hit" and got == {7: 0.0625, 9: 0.125})
        #: The path handed in does not exist, so if the filename check failed to
        #: bite, cached_relsums would fall through to scan_one and raise. The
        #: raise IS the assertion: a cache keyed on the wrong file is not used.
        try:
            cached_relsums("2099-01-01", 6, "snap-B.csv.bz2", "/no/such/file")
            missed = False
        except Exception:                                            # noqa: BLE001
            missed = True
        chk("22 a cache built from a DIFFERENT filename is not reused; the "
            "snapshot is rescanned", missed)
    finally:
        CACHE = real_cache

    chk("23 cv is |sd/mean|: zero on a constant column, and it ranks a flat "
        "column below a sloped one",
        cv([3.1, 3.1, 3.1]) == 0.0
        and cv([1.0, 2.0, 3.0, 4.0]) > cv([2.4, 2.5, 2.6, 2.5]))
    chk("24 the settled cut is registered as a post-hoc description and says so "
        "in the source, per D3 revision class three",
        "SETTLE_DAYS" in src and "Registered AFTER the first reading" in src
        and "delta_allpost_pp" in src and "delta_settled_pp" in src)

    # --- 25..30 the two halves, rho, and the exclusion counter -------------
    #: mids equal, so the index half is exactly zero and rho is exactly zero.
    q0 = (99.0, 101.0, 98.0, 102.0)
    chk("25 q_logsum is log(ask/bid) summed over the two hubs; q_logdiff is "
        "2*log(mid_j/mid_a); equal mids give a zero index half and zero rho",
        abs(q_logsum(q0) - (math.log(101 / 99) + math.log(102 / 98))) < 1e-15
        and abs(q_logdiff(q0)) < 1e-15 and q_rho(q0) == 0.0)

    #: wide spreads, close mids -> inside Theorem 6(4)'s [0,1].
    qin = (90.0, 110.0, 88.0, 108.0)
    #: tight spreads, mids a factor of two apart -> outside it.
    qout = (99.0, 101.0, 49.0, 51.0)
    chk("26 rho lands in [0,1] when the index half is small against the "
        "friction half, and above 1 when it is not",
        0.0 < q_rho(qin) < 1.0 and q_rho(qout) > 1.0)

    bk = {(JITA, 5): [90.0, 110.0], (AMARR, 5): [88.0, 108.0],
          (JITA, 6): [10.0, 11.0], (AMARR, 6): [None, 12.0],
          (JITA, 7): [5.0, 4.0], (AMARR, 7): [4.0, 5.0],
          (JITA, 8): [0.0, 3.0], (AMARR, 8): [1.0, 2.0]}
    qs, v1 = quotes(bk), relsums(bk)
    chk("27 q_relsum reproduces the v1 relsums() definition to the last bit, so "
        "--floor and --shape are unchanged by the v2 cache",
        set(qs) == set(v1)
        and all(abs(q_relsum(qs[t]) - v1[t]) < 1e-15 for t in qs))
    chk("28 quotes() drops one-sided and crossed books; a zero bid survives "
        "into the cache and is filtered at the log, not at the cache",
        set(qs) == {5, 8} and q_relsum(qs[8]) == v1[8]
        and q_logsum(qs[8]) is None and q_rho(qs[8]) is None)

    #: The real assertion is behavioural: run rho_map on a known set and check
    #: the count is per pair. An AST check that "only one line increments" was
    #: true of the broken version too, because the line was reached three times.
    fn = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "cmd_rho"]
    qmap = {1: qin, 2: qout, 3: qout, 4: q0, 9: qin}
    keep, ncomp, nover = rho_map(qmap, {1, 2, 3, 4, 5})
    chk("29 rho_map decides each (snapshot, type) pair once: five candidates, "
        "one absent, four computable, two outside the domain",
        set(keep) == {1, 4} and ncomp == 4 and nover == 2
        and not [n for n in ast.walk(fn[0]) if isinstance(n, ast.AugAssign)])

    #: AST again. The previous shape of this check forbade a literal by naming
    #: it, so the assertion's own text tripped it. Third time in this file that
    #: a guard counted itself; the fix is always the same, look at the tree.
    consts = [n.value for n in ast.walk(fn[0])
              if isinstance(n, ast.Constant) and isinstance(n.value, float)]
    div = [n for n in ast.walk(fn[0])
           if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)
           and isinstance(n.left, ast.Name) and n.left.id == "den_pre"
           and isinstance(n.right, ast.Name) and n.right.id == "den_post"]
    chk("30 the rho prediction is a division of two measured numbers and no "
        "float near it is baked into cmd_rho",
        len(div) == 1 and not [c for c in consts if 0.70 <= c <= 0.90])

    #: --coverage must report a templated fallback as NOT covered. day_index
    #: returns a full 48-name list in that case, and a name count would read as
    #: coverage when nothing was actually found.
    cfn = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "cmd_coverage"][0]
    csrc = ast.get_source_segment(src, cfn) or ""
    chk("31 --coverage reads a templated fallback as NOT covered, and fetches "
        "no snapshot",
        "index unreadable" in csrc and '"NOT"' in csrc
        and "cmd_fetch" not in csrc and "urlopen" not in csrc)

    #: The null distribution must be produced by the SAME arithmetic as the real
    #: reading. A null built by a second code path measures the second code path.
    nfn = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "cmd_nulls"][0]
    calls = {getattr(n.func, "id", getattr(n.func, "attr", ""))
             for n in ast.walk(nfn) if isinstance(n, ast.Call)}
    chk("32 cmd_nulls computes nothing of its own: it calls window_read and "
        "touches neither the halves nor rho_map nor fixed_set directly",
        "window_read" in calls
        and not (calls & {"q_logsum", "q_logdiff", "q_rho", "rho_map",
                          "fixed_set", "cached_quotes", "scan_one"}))
    chk("33 cmd_nulls never scores a placebo against a registered band; "
        "prediction() is not reachable from it",
        "prediction" not in calls)

    #: admissibility, checked as arithmetic rather than trusted
    ev = datetime.date(2021, 10, 13)
    first = datetime.date(2021, 9, 22)
    half, step = 5, 2
    cands, k = [], half
    while True:
        c = first + datetime.timedelta(days=k)
        if (c + datetime.timedelta(days=half)) >= ev:
            break
        cands.append(c)
        k += step
    chk("34 every placebo's FULL window, both sides, lies strictly before the "
        "event day, so no null contains the event (%d candidates at half=%d)"
        % (len(cands), half),
        len(cands) >= 3
        and all(c - datetime.timedelta(days=half) >= first for c in cands)
        and all(c + datetime.timedelta(days=half) < ev for c in cands))

    print("\n  %d/%d" % (34 - len(fails), 34))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan", metavar="EVENT")
    ap.add_argument("--fetch", metavar="EVENT")
    ap.add_argument("--floor", metavar="EVENT")
    ap.add_argument("--shape", metavar="EVENT")
    ap.add_argument("--rho", metavar="EVENT")
    ap.add_argument("--nulls", metavar="EVENT",
                    help="placebo distribution for factor_ratio, built from "
                         "dates inside this event's own pre period")
    ap.add_argument("--settle", type=int, default=0,
                    help="--nulls only: days after the date before the post "
                         "side counts. 0 uses the whole post side.")
    ap.add_argument("--step", type=int, default=2,
                    help="--nulls only: spacing between placebo dates")
    ap.add_argument("--coverage", metavar="DATES",
                    help="comma-separated YYYY-MM-DD; one free index read each")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--half", type=int, default=HALF_DEFAULT)
    ap.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.plan:
        return cmd_plan(a.plan, a.half)
    if a.fetch:
        return cmd_fetch(a.fetch, a.half, a.confirm)
    if a.floor:
        return cmd_floor(a.floor, a.half)
    if a.shape:
        return cmd_shape(a.shape, a.half, a.bins)
    if a.rho:
        return cmd_rho(a.rho, a.half)
    if a.nulls:
        return cmd_nulls(a.nulls, a.half, a.settle, a.step)
    if a.coverage:
        return cmd_coverage([x.strip() for x in a.coverage.split(",") if x.strip()])
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
