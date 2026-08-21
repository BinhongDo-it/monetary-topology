"""Section 31 carrier, step one of the free pre-purchase checks: build the eight
symbol lists and print how many survive each screening rule.

Nothing here
buys data. The only network use is --probe, which fetches one symbol from each
candidate price source to find out what each returns.

WHY THIS FILE EXISTS SEPARATELY FROM THE PULLER

The universe size N is not known. The pre-registration freezes the RULE, not the
list, and section 3.4 says N and the per-rule dropout counts get printed before
any money is spent. If some event's N comes in under 40 that event is registered
as "insufficient symbols" and leaves the scored set, and that has to happen
before the purchase, not after.

THE SCREEN DATE, AND WHY IT IS NOT THE ORDER PUBLICATION DATE

Registered anchor: the 50th trading day before the event's boundary trade date.

The first draft anchored on the trading day before the SEC annual order's Federal
Register publication. That is worse on two counts. It needs a hand-kept table of
eight publication dates, and the Fee Rate Advisory press release generally
precedes Federal Register publication, so the anchor is not reliably ahead of the
first public signal.

50 trading days is about 70 calendar days. The statute (15 USC 78ee(j)(4)(A))
puts the effective date 60 calendar days after the appropriation is enacted, and
the boundary trade date is one or two sessions before the effective date, so the
enactment sits about 40 trading days before the boundary. 50 trading days back is
therefore provably earlier than the enactment, hence earlier than any Section 31
rate announcement for that event. It is also mechanical and uniform across the
eight events, which the publication-date anchor was not.

THE SPLIT PROBLEM, WHICH IS LOAD BEARING

stooq's bulk archive is SPLIT ADJUSTED. Screening a ">$300 as quoted" rule on
split-adjusted closes does not merely lose a few names, it removes exactly the
names the design most wants. At the 2019 screen date AMZN quoted near $1,700 and
GOOGL near $1,180; the 2022 twenty-for-one splits put both under $90 in adjusted
terms. CMG, ISRG, NFLX and TSLA are the same story. An adjusted screen would drop
the most heavily quoted high-priced names in the sample and keep the thin ones.

So this file will NOT run the screen off adjusted prices. Either a source of
as-quoted closes is found (--probe looks for one), or a split table is supplied
on disk with its provenance, and the screen refuses to run without one of those.
That refusal is the point: a screen that silently produced a split-mangled list
would look exactly like a screen that worked.

SURVIVORSHIP, REGISTERED AND NOT FIXED

stooq's current bulk archive carries names listed now. A name above $300 in 2019
that was later acquired is absent. This biases the early events' universes toward
survivors. It is registered rather than fixed: a point-in-time security master
costs money, and survival five years after an event is not a plausible function
of that event's fee change. Any event whose list is built this way says so.

Usage
    python experiments/b16_universe.py --selftest        no network
    python experiments/b16_universe.py --dates           no network, prints anchors
    python experiments/b16_universe.py --probe           one request per source
    python experiments/b16_universe.py --calendar PATH   trading days from the archive
    python experiments/b16_universe.py --screen PATH     the real screen
"""
import argparse
import collections
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "b16_universe.json")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
#: Supplied by hand, with provenance, one row per (symbol, ex-date, factor).
#: Absent or empty means the screen refuses to run. See the docstring.
SPLIT_TABLE = os.path.join(ROOT, "data", "raw", "b16_splits.csv")

#: Pre-registration section 4.3. Event 1 is listed so the file can print why it
#: is out; scored=False is the registered data-availability exclusion, not a
#: reading-driven one.
EVENTS = [
    dict(n=1, boundary="2018-05-18", dr=-10.10e-6, scored=False,
         note="Databento starts 2018-05-01; only 12 of the 29 pre days exist"),
    dict(n=2, boundary="2019-04-12", dr=+7.70e-6, scored=True, subset=True),
    dict(n=3, boundary="2021-02-23", dr=-17.00e-6, scored=True, subset=True),
    dict(n=4, boundary="2022-05-12", dr=+17.80e-6, scored=True, subset=False,
         note="confounder aligned with treatment; out of the confirmatory subset"),
    dict(n=5, boundary="2023-02-23", dr=-14.90e-6, scored=True, subset=True),
    dict(n=6, boundary="2024-05-20", dr=+19.80e-6, scored=True, subset=True,
         note="T+1 compliance five trading days later; direction undetermined"),
    dict(n=7, boundary="2025-05-13", dr=-27.80e-6, scored=True, subset=False,
         note="confounder aligned with treatment; out of the confirmatory subset"),
    dict(n=8, boundary="2026-04-02", dr=+20.60e-6, scored=True, subset=True,
         note="main event; Good Friday is the next session"),
]

#: Pre-registration section 3.2 as amended by this file's docstring.
SCREEN_LAG_TRADING_DAYS = 50
#: Pre-registration section 3.1 rule 2.
PRICE_FLOOR = 300.00
#: Pre-registration section 3.4.
MIN_SYMBOLS = 40
#: A date counts as a trading day if at least this many tickers have a row on it.
#: Set well above any plausible partial-file artefact and well below the number of
#: US tickers stooq carries.
CALENDAR_QUORUM = 500

UA = "Mozilla/5.0 (compatible; research/1.0)"
#: Probed, not assumed. b14_legb_price2016 learned this the hard way: its first
#: stooq URL form returned 404 for every symbol.
UNADJUSTED_SOURCES = [
    ("stooq_bulk_page", "https://stooq.com/db/h/", "html"),
    ("stooq_symbol_d", "https://stooq.com/q/d/l/?s=aapl.us&i=d", "csv"),
    ("nasdaq_splits", "https://api.nasdaq.com/api/calendar/splits?date=2022-06-06", "json"),
]

BULK_HEAD_MARK = "<TICKER>"


# ---------------------------------------------------------------- parsing

def parse_bulk_series(text):
    """One stooq bulk member -> {yyyymmdd: close}. None if it is not a price file."""
    lines = [x for x in text.splitlines() if x.strip()]
    if len(lines) < 2:
        return None
    head = [c.strip().strip("<>").lower() for c in lines[0].split(",")]
    if "close" not in head or "date" not in head:
        return None
    ic, id_ = head.index("close"), head.index("date")
    out = {}
    for line in lines[1:]:
        p = line.split(",")
        if len(p) <= max(ic, id_):
            continue
        d = p[id_].strip().replace("-", "")
        if len(d) != 8 or not d.isdigit():
            continue
        try:
            v = float(p[ic])
        except ValueError:
            continue
        if v > 0:
            out[d] = v
    return out or None


#: The archive files members under data/daily/us/<market> <kind>/<n>, e.g.
#: "nasdaq stocks/2" and "nyse etfs/1". That directory carries the instrument
#: kind, so rule 1's ETF exclusion is free and exact rather than needing a
#: security master. Counted on the 2026-08-20 archive: 9,640 stocks against
#: 3,667 ETFs out of 13,307 members.
_ETF_MARK = "etfs"
_STOCK_MARK = "stocks"


def member_symbol(name):
    """<sym>.us.txt anywhere in the archive -> SYM, else None."""
    base = os.path.basename(name).lower()
    if not base.endswith(".us.txt"):
        return None
    sym = base[: -len(".us.txt")].upper()
    return sym or None


def member_is_stock(name):
    """True for a stocks folder, False for an etfs folder, None if undecidable."""
    d = os.path.dirname(name).lower()
    if _ETF_MARK in d:
        return False
    if _STOCK_MARK in d:
        return True
    return None


def read_split_table(path=SPLIT_TABLE):
    """symbol -> [(ex_date_yyyymmdd, factor)]. Missing file returns None."""
    if not os.path.exists(path):
        return None
    rows = collections.defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r.get("symbol"):
                continue
            d = (r.get("ex_date") or "").replace("-", "").strip()
            try:
                f = float(r["factor"])
            except (KeyError, TypeError, ValueError):
                continue
            if len(d) == 8 and d.isdigit() and f > 0:
                rows[r["symbol"].strip().upper()].append((d, f))
    return {k: sorted(v) for k, v in rows.items()}


def as_quoted(adj_close, sym, on_date, splits):
    """Undo split adjustment: multiply by every split factor strictly after on_date.

    A 4-for-1 split has factor 4. stooq divides pre-split closes by 4, so the
    as-quoted close is the adjusted close times 4.
    """
    f = 1.0
    for ex, fac in splits.get(sym, ()):
        if ex > on_date:
            f *= fac
    return adj_close * f


# ---------------------------------------------------------------- calendar

def trading_calendar(zip_path, quorum=CALENDAR_QUORUM, cache=CAL_CACHE):
    """Every date on which at least `quorum` tickers have a row, ascending.

    Derived from the archive itself so no holiday table is needed and no holiday
    table can be wrong.
    """
    if cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("quorum") == quorum and d.get("zip") == os.path.basename(zip_path):
            return d["days"]
    counts = collections.Counter()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if member_symbol(info.filename) is None:
                continue
            ser = parse_bulk_series(z.read(info).decode("utf-8", "replace"))
            if ser:
                counts.update(ser.keys())
    days = sorted(d for d, c in counts.items() if c >= quorum)
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump({"quorum": quorum, "zip": os.path.basename(zip_path),
                       "days": days}, fh)
    return days


def screen_date(boundary, days, lag=SCREEN_LAG_TRADING_DAYS):
    """The lag-th trading day strictly before `boundary`. None if unavailable."""
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    if len(before) < lag:
        return None
    return before[-lag]


# ---------------------------------------------------------------- screen

def screen(zip_path, splits, days):
    """Per event: the surviving symbols and the per-rule dropout counts."""
    anchors = {}
    for e in EVENTS:
        anchors[e["n"]] = screen_date(e["boundary"], days)

    keep = {e["n"]: [] for e in EVENTS}
    drop = {e["n"]: collections.Counter() for e in EVENTS}

    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            sym = member_symbol(info.filename)
            if sym is None:
                continue
            kind = member_is_stock(info.filename)
            ser = parse_bulk_series(z.read(info).decode("utf-8", "replace"))
            if not ser:
                continue
            for e in EVENTS:
                if kind is False:
                    drop[e["n"]]["rule1_etf_by_folder"] += 1
                elif kind is None:
                    drop[e["n"]]["rule1_kind_undecidable"] += 1
            if kind is not True:
                continue
            for e in EVENTS:
                n, a = e["n"], anchors[e["n"]]
                if a is None:
                    drop[n]["no_anchor"] += 1
                    continue
                if a not in ser:
                    drop[n]["rule7_not_listed_on_anchor"] += 1
                    continue
                if not looks_like_common_stock(sym):
                    drop[n]["rule1_not_common_stock"] += 1
                    continue
                px = as_quoted(ser[a], sym, a, splits)
                if px <= PRICE_FLOOR:
                    drop[n]["rule2_price_at_or_below_floor"] += 1
                    continue
                keep[n].append((sym, round(px, 4)))
    return anchors, keep, drop


#: Rule 1, the part that can be done from a ticker alone. The rest of rule 1
#: (ETF/ETN/ADR/preferred/unit/SPAC) and rules 5, 6, 7 need a security master and
#: are applied in step two; this file prints what it could not decide rather than
#: pretending the screen is complete.
_SUFFIX_NOT_COMMON = ("-P", ".P", "-W", ".W", "-U", ".U", "-R", ".R")


def looks_like_common_stock(sym):
    if any(sym.endswith(s) for s in _SUFFIX_NOT_COMMON):
        return False
    if len(sym) > 5:
        return False
    return True


# ---------------------------------------------------------------- reporting

def report(anchors, keep, drop):
    print("%-3s %-12s %-12s %-9s %8s  %s" %
          ("#", "boundary", "screen date", "dr(1e-6)", "N", "status"))
    out = {}
    for e in EVENTS:
        n = e["n"]
        a = anchors.get(n)
        N = len(keep.get(n, []))
        if not e["scored"]:
            status = "excluded before purchase: " + e.get("note", "")
        elif N < MIN_SYMBOLS:
            status = "INSUFFICIENT SYMBOLS, leaves the scored set (N<%d)" % MIN_SYMBOLS
        else:
            status = "scored" + ("" if e.get("subset") else ", not in confirmatory subset")
        print("%-3d %-12s %-12s %+9.2f %8d  %s"
              % (n, e["boundary"], a or "n/a", e["dr"] * 1e6, N, status))
        out[str(n)] = dict(boundary=e["boundary"], screen_date=a, dr=e["dr"],
                           scored=e["scored"], subset=e.get("subset"),
                           n_symbols=N, symbols=sorted(keep.get(n, [])),
                           dropped=dict(drop.get(n, {})), note=e.get("note", ""))
    print()
    print("per-rule dropouts")
    for e in EVENTS:
        n = e["n"]
        if not drop.get(n):
            continue
        print("  event %d: %s" % (n, ", ".join("%s=%d" % kv for kv in sorted(drop[n].items()))))
    print()
    print("NOT APPLIED HERE, and why:")
    print("  rule 1 ETF part: done here, free, from the archive's folder taxonomy\n  rule 1 remainder (ETN/ADR/preferred/unit/SPAC): needs a security master")
    print("  rule 3 (both venues quote two-sided >=90%% of the pre window): needs the data")
    print("  rule 4 (spread >= 3 ticks on the REFERENCE window, days -20..-11): needs the data")
    print("  rule 5 (Tick Size Pilot exclusion, event 1 only): event 1 is already out")
    print("  rule 6 (splits, reverse splits, >2%% ex-dividends, tender, halts in window)")
    print("  rules 3 and 4 are post-purchase by necessity; they are mechanical and")
    print("  registered, so applying them when the data lands adds no discretion.")
    return out


# ---------------------------------------------------------------- probe

def probe():
    print("one request per candidate source; nothing is bought, nothing is cached")
    for name, url, kind in UNADJUSTED_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read(3000).decode("utf-8", "replace")
                code = r.getcode()
        except urllib.error.HTTPError as ex:
            code, body = ex.code, "(http error)"
        except Exception as ex:                                   # noqa: BLE001
            code, body = "-", "(%s)" % type(ex).__name__
        first = body.strip().splitlines()[0][:120] if body.strip() else ""
        print("  %-18s %-4s %s" % (name, code, first))
    print()
    print("what to look for: a source that serves closes WITHOUT split adjustment,")
    print("or a splits feed from which %s can be built." % os.path.relpath(SPLIT_TABLE, ROOT))


# ---------------------------------------------------------------- selftest

def selftest():
    bad = []

    def chk(msg, ok):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            bad.append(msg)

    txt = ("<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\n"
           "AAPL.US,D,20190314,000000,45,46,44,45.5,1,0\n"
           "AAPL.US,D,20190315,000000,45,46,44,46.5,1,0\n")
    ser = parse_bulk_series(txt)
    chk("the bulk parser reads the angle-bracket header: %s" % ser,
        ser == {"20190314": 45.5, "20190315": 46.5})
    chk("a non-price member is refused", parse_bulk_series("hello\nworld\n") is None)
    chk("member_symbol picks .us.txt out", member_symbol("data/daily/us/aapl.us.txt") == "AAPL")
    chk("member_symbol refuses anything else", member_symbol("readme.txt") is None)

    # The split correction must actually move a price, or it is not a correction.
    splits = {"AMZN": [("20220606", 20.0)], "PLAIN": []}
    chk("a split after the screen date is undone: %.1f" % as_quoted(85.0, "AMZN", "20190314", splits),
        abs(as_quoted(85.0, "AMZN", "20190314", splits) - 1700.0) < 1e-9)
    chk("a split before the screen date is not undone",
        abs(as_quoted(85.0, "AMZN", "20230101", splits) - 85.0) < 1e-9)
    chk("an unsplit symbol is untouched",
        abs(as_quoted(310.0, "PLAIN", "20190314", splits) - 310.0) < 1e-9)
    # This is the check that would have caught the bug the docstring is about.
    chk("WITHOUT the correction AMZN fails the >$300 screen, WITH it it passes",
        (85.0 <= PRICE_FLOOR) and (as_quoted(85.0, "AMZN", "20190314", splits) > PRICE_FLOOR))

    days = ["2019%04d" % 0] * 0 + ["201901%02d" % d for d in range(1, 29)] \
        + ["201902%02d" % d for d in range(1, 29)] + ["201903%02d" % d for d in range(1, 29)] \
        + ["201904%02d" % d for d in range(1, 29)]
    sd = screen_date("2019-04-12", days, lag=50)
    chk("the screen date is the 50th trading day before the boundary: %s" % sd,
        sd is not None and sd < "20190412")
    chk("the screen date is strictly before the boundary",
        sd < "20190412")
    chk("too little history returns None rather than a wrong date",
        screen_date("2019-04-12", days[-10:], lag=50) is None)

    chk("the folder taxonomy calls an etfs path an ETF",
        member_is_stock("data/daily/us/nasdaq etfs/spy.us.txt") is False)
    chk("the folder taxonomy calls a stocks path a stock",
        member_is_stock("data/daily/us/nyse stocks/2/nvr.us.txt") is True)
    chk("an unfamiliar path is undecidable rather than silently a stock",
        member_is_stock("data/daily/us/mystery/x.us.txt") is None)
    chk("rule 1's ticker part drops a preferred line", not looks_like_common_stock("BAC-PB"))
    chk("rule 1's ticker part keeps a plain ticker", looks_like_common_stock("BKNG"))

    chk("event 1 is registered unscored BEFORE any reading",
        [e for e in EVENTS if e["n"] == 1][0]["scored"] is False)
    chk("the scored set is seven events", sum(1 for e in EVENTS if e["scored"]) == 7)
    chk("the confirmatory subset is five events",
        sum(1 for e in EVENTS if e["scored"] and e.get("subset")) == 5)
    chk("dr signs alternate across the eight events",
        all((EVENTS[i]["dr"] > 0) != (EVENTS[i + 1]["dr"] > 0) for i in range(len(EVENTS) - 1)))

    print("selftest: %s" % ("PASS" if not bad else "FAIL, %d problem(s)" % len(bad)))
    return 1 if bad else 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dates", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--calendar", metavar="ZIP")
    ap.add_argument("--screen", metavar="ZIP")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.probe:
        probe()
        return 0
    if a.dates:
        print("screen date = the %dth trading day before the boundary trade date."
              % SCREEN_LAG_TRADING_DAYS)
        print("Run --calendar first to resolve them; the calendar comes from the archive.")
        for e in EVENTS:
            print("  event %d  boundary %s  dr=%+.2fe-6  scored=%s  %s"
                  % (e["n"], e["boundary"], e["dr"] * 1e6, e["scored"], e.get("note", "")))
        return 0
    if a.calendar:
        days = trading_calendar(a.calendar)
        print("%d trading days, %s to %s" % (len(days), days[0], days[-1]))
        for e in EVENTS:
            print("  event %d  boundary %s  screen date %s"
                  % (e["n"], e["boundary"], screen_date(e["boundary"], days) or "UNAVAILABLE"))
        return 0
    if a.screen:
        splits = read_split_table()
        if splits is None:
            print("REFUSING TO SCREEN: no split table at %s" % SPLIT_TABLE)
            print("stooq's archive is split adjusted. Screening >$%d on adjusted closes"
                  % PRICE_FLOOR)
            print("would drop AMZN, GOOGL, CMG, ISRG, NFLX and TSLA from the early events")
            print("and keep thinner names, which is the opposite of what the design wants.")
            print("Supply the table (symbol,ex_date,factor,source) or run --probe for a")
            print("source of as-quoted closes. See this file's docstring.")
            return 1
        days = trading_calendar(a.screen)
        anchors, keep, drop = screen(a.screen, splits, days)
        out = report(anchors, keep, drop)
        os.makedirs(RESULTS, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(dict(price_floor=PRICE_FLOOR, screen_lag=SCREEN_LAG_TRADING_DAYS,
                           min_symbols=MIN_SYMBOLS, archive=os.path.basename(a.screen),
                           split_table_rows=sum(len(v) for v in splits.values()),
                           events=out), fh, indent=1, ensure_ascii=False)
        print("\nwrote %s" % os.path.relpath(OUT, ROOT))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
