"""Section 31 carrier: build the per-event symbol lists from the UNADJUSTED bars.

Supersedes the stooq path
in b16_universe.py for everything except the trading calendar: stooq is split
adjusted, so a ">$300 as quoted" rule cannot be applied to it at all.

No network. Reads only what b16_px_pull already bought.

WHAT THIS FILE DECIDES, AND WHAT IT CANNOT

Applied here, from bars alone:
    rule 1 (part)  ticker form, no preferred/warrant/unit/class lines
    rule 2         close above the floor AS QUOTED on the screen date
    rule 6         no split, reverse split or other single-day dislocation inside
                   the window. In unadjusted data a split is a real jump, so this
                   stops needing the hand-built corporate-action table it needed
                   when the price source was adjusted.
    rule 7         a bar on every trading day of the window

Left for after the quote pull, because they need quotes:
    rule 3         both venues quoting two-sided at least 90% of the pre window
    rule 4         reference-window spread at least 3 ticks

THE COVERAGE RULE, ADDED 2026-08-20

An event is scored only if at least COVERAGE_MIN of its universe has a fee change
worth at least half a tick, that is |dr| * M >= 0.005. The reason it exists:

    The relative move the framework predicts in rho is 2*dr/(s/M). Measured on
    the reference windows that number is 0.4% to 0.9% for every event and it is
    almost INDEPENDENT of the price floor, because s/M is a basis-point quantity
    that does not scale with the price level. The floor does not buy effect size.
    What the floor buys is resolvability against the one cent grid, and that is
    strongly price dependent.

    So "is this event big enough" is a question about grid resolvability, not
    about sample size, and the coverage share is the right gate. Event 2 fails it
    at 34% because its dr is 7.70e-6, the smallest of the eight, and raising the
    floor to $400 only lifts it to 61% while cutting N to 23. Event 2 is weak on
    its own dr, and no floor rescues it.

This replaces the earlier N >= 40 reasoning as the operative exclusion for event
2. The N floor stays as a separate check; an event can fail either.

    python experiments/b16_screen.py --selftest
    python experiments/b16_screen.py --dist        return distribution, sets rule 6
    python experiments/b16_screen.py --screen
"""
import argparse
import collections
import datetime
import gzip
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import b16_px_pull as PX                                          # noqa: E402

RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "b16_universe.json")
CACHE = os.path.join(RESULTS, "b16_screen_cache.json")

#: Pre-registration section 3.1 rule 2. Held at $300, ruled 2026-08-20 after the
#: floor sensitivity was computed; see the docstring.
PRICE_FLOOR = 300.00
#: Pre-registration section 3.4. Kept, but it is no longer what excludes event 2.
MIN_SYMBOLS = 40
#: Half of one tick. Below this the fee change cannot move a quoted spread at all,
#: so the symbol contributes noise and no signal and does not belong in the sample.
#: Applied PER SYMBOL as rule 2b, not as a per-event coverage share.
#:
#: The first draft made it a per-event gate at 75%. That was wrong twice over.
#: It was fitted: 75% was written down after a coarse pass put event 5 at 75%,
#: and the full screen then put event 5 at 74%, so the whole event turned on a
#: number chosen next to it. And it was the wrong shape: whether a SYMBOL can
#: respond is a property of the symbol, not a property of the event. As a per
#: symbol rule it introduces no new parameter at all, because the surviving count
#: is then judged by the MIN_SYMBOLS floor that was already registered.
HALF_TICK = 0.005

#: Rule 6. A single-day absolute log return at or above this drops the symbol.
#: A two for one split is 0.69, so any split is caught with room to spare. The
#: value is set from the carrier in --dist rather than chosen: it is the smallest
#: round number above the 99.9th percentile of ordinary daily moves in the
#: quietest event window, so it fires on dislocations and not on volatility.
RULE6_ABS_LOG_RETURN = 0.40

BOUNDARY = {2: "2019-04-12", 3: "2021-02-23", 4: "2022-05-12", 5: "2023-02-23",
            6: "2024-05-20", 7: "2025-05-13", 8: "2026-04-02"}
DR = {2: 7.70e-6, 3: 17.00e-6, 4: 17.80e-6, 5: 14.90e-6,
      6: 19.80e-6, 7: 27.80e-6, 8: 20.60e-6}
#: Sign of the rate change. The framework predicts sign(log R) = -sign(dr).
DR_SIGN = {2: +1, 3: -1, 4: +1, 5: -1, 6: +1, 7: -1, 8: +1}

_BAD = ("-", ".", "+", "=")

#: Rule 1's ETF exclusion. Databento's ohlcv schema carries no instrument type, and
#: the ticker form does not separate them: SOXL, TECL, VGT, VUG, VOOG and MGK all
#: pass a "three to five letters, no separator" test and all are funds. The stooq
#: bulk archive files its members under ".../nasdaq etfs/..." and ".../nyse etfs/...",
#: so it supplies the classification even though its PRICES are unusable here.
#: Each source used for what it is good at.
#: Registered limitation: the archive lists what is listed now, so a fund that
#: delisted before the archive was taken is not flagged. That biases toward
#: leaving a stale fund in, not toward dropping a stock.
ETF_CACHE = os.path.join(RESULTS, "b16_etf_tickers.json")
STOOQ_ZIP = os.path.join(ROOT, "data", "raw", "d_us_txt.zip")


def etf_tickers(build=True):
    if os.path.exists(ETF_CACHE):
        return set(json.load(open(ETF_CACHE, encoding="utf-8")))
    if not build or not os.path.exists(STOOQ_ZIP):
        return set()
    import zipfile
    out = set()
    with zipfile.ZipFile(STOOQ_ZIP) as z:
        for info in z.infolist():
            b = os.path.basename(info.filename).lower()
            if not b.endswith(".us.txt"):
                continue
            if "etfs" in os.path.dirname(info.filename).lower():
                out.add(b[: -len(".us.txt")].upper())
    os.makedirs(RESULTS, exist_ok=True)
    with open(ETF_CACHE, "w", encoding="utf-8") as fh:
        json.dump(sorted(out), fh)
    return out


def ticker_is_common(sym):
    """Rule 1, the part decidable from the ticker. Class and preferred lines carry
    a separator; five characters is the longest ordinary US common-stock ticker."""
    return bool(sym) and len(sym) <= 5 and not any(c in sym for c in _BAD)


def ns(day):
    return int(datetime.datetime(int(day[:4]), int(day[4:6]), int(day[6:]),
                                 tzinfo=datetime.timezone.utc).timestamp()) * 10 ** 9


def load_calendar():
    p = os.path.join(RESULTS, "b16_trading_calendar.json")
    if not os.path.exists(p):
        raise SystemExit("no trading calendar; run b16_universe.py --calendar ZIP")
    return json.load(open(p, encoding="utf-8"))["days"]


def window_days(boundary, days, each=PX.BUY_DAYS_EACH_SIDE):
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]
    return before[-each:] + after[:each]


def screen_day(boundary, days, lag=PX.SCREEN_LAG_TRADING_DAYS):
    before = [d for d in days if d < boundary.replace("-", "")]
    return before[-lag] if len(before) >= lag else None


def read_days(dayset):
    """ticker -> {day: close}, for the given trading days, from the bought bars."""
    out = collections.defaultdict(dict)
    for mm in sorted({d[:4] + "-" + d[4:6] for d in dayset}):
        sp, bp = PX.sym_path(mm), PX.dst_path(mm)
        if not (os.path.exists(sp) and os.path.exists(bp)):
            continue
        smap = json.load(open(sp, encoding="utf-8"))
        if not PX.map_is_interval_shaped(smap):
            raise SystemExit("%s: symbology map is the collapsed shape; "
                             "run b16_px_pull.py --symbology" % mm)
        stamps = {ns(d): d for d in dayset if d[:4] + "-" + d[4:6] == mm}
        with gzip.open(bp, "rt", encoding="utf-8", errors="replace") as fh:
            h = [c.strip() for c in fh.readline().split(",")]
            it, ii, ic = h.index("ts_event"), h.index("instrument_id"), h.index("close")
            for line in fh:
                p = line.split(",")
                if len(p) <= ic:
                    continue
                d = stamps.get(int(p[it]))
                if d is None:
                    continue
                t = PX.ticker_at(smap, p[ii].strip(), d)
                if t and ticker_is_common(t):
                    out[t][d] = int(p[ic]) / 1e9
    return out


def max_abs_log_return(series, wdays):
    v = [series[d] for d in wdays if d in series and series[d] > 0]
    if len(v) < 2:
        return None
    return max(abs(math.log(v[i + 1] / v[i])) for i in range(len(v) - 1))


def screen(cache=True):
    days = load_calendar()
    etfs = etf_tickers()
    print("rule 1 ETF blacklist from the stooq folder taxonomy: %d tickers" % len(etfs))
    out, dist = {}, {}
    for e in sorted(BOUNDARY):
        sd = screen_day(BOUNDARY[e], days)
        wd = window_days(BOUNDARY[e], days)
        px = read_days(set(wd) | {sd})
        drop = collections.Counter()
        keep = []
        for t, ser in px.items():
            if sd not in ser:
                drop["rule7_no_bar_on_screen_date"] += 1
                continue
            if t in etfs:
                drop["rule1_etf"] += 1
                continue
            if ser[sd] <= PRICE_FLOOR:
                drop["rule2_at_or_below_floor"] += 1
                continue
            if DR[e] * ser[sd] < HALF_TICK:
                drop["rule2b_fee_change_under_half_a_tick"] += 1
                continue
            miss = sum(1 for d in wd if d not in ser)
            if miss > 0:
                drop["rule7_missing_%d_window_days" % min(miss, 9)] += 1
                continue
            m = max_abs_log_return(ser, wd)
            if m is None or m >= RULE6_ABS_LOG_RETURN:
                drop["rule6_dislocation"] += 1
                continue
            keep.append((t, round(ser[sd], 4), round(m, 4)))
        keep.sort()
        Ms = [k[1] for k in keep]
        scored = len(keep) >= MIN_SYMBOLS
        why = [] if scored else ["N=%d < %d after rule 2b" % (len(keep), MIN_SYMBOLS)]
        #: The price at which this event's fee change is exactly half a tick.
        half_at = HALF_TICK / DR[e]
        out[str(e)] = dict(boundary=BOUNDARY[e], screen_date=sd, dr=DR[e],
                           dr_sign=DR_SIGN[e], n_symbols=len(keep),
                           median_price=round(statistics.median(Ms), 2) if Ms else None,
                           half_tick_price=round(half_at, 2),
                           scored=scored, excluded_because=why,
                           symbols=keep, dropped=dict(drop))
        dist[e] = [max_abs_log_return(ser, wd) for ser in px.values()]
        print("e%-2d %s  screen %s  dr=%5.2fe-6  half-tick at $%-6.0f N=%-4d medM=%-6s %s"
              % (e, BOUNDARY[e], sd, DR[e] * 1e6, half_at, len(keep),
                 ("%.0f" % statistics.median(Ms)) if Ms else "-",
                 "SCORED" if scored else "EXCLUDED: " + ", ".join(why)))
        for k, v in sorted(drop.items()):
            print("      %-34s %d" % (k, v))
    kept = [e for e in sorted(BOUNDARY) if out[str(e)]["scored"]]
    print("\nscored set: %s  (%d events)" % (", ".join("e%d" % e for e in kept), len(kept)))
    print("exact binomial under the opponent's null: %d/%d has p = 1/%d = %.4f"
          % (len(kept), len(kept), 2 ** len(kept), 1.0 / 2 ** len(kept)))
    print("confirmatory subset: DEFERRED to the placebo band. The earlier subset was")
    print("built on the direction of the SPREAD confounder, and the scored quantity")
    print("is rho; a shock that lifts numerator and denominator together may not move")
    print("rho at all. The band measures that, and the band needs the quote pull.")
    if cache:
        os.makedirs(RESULTS, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(dict(price_floor=PRICE_FLOOR, min_symbols=MIN_SYMBOLS,
                           half_tick=HALF_TICK,
                           rule6_abs_log_return=RULE6_ABS_LOG_RETURN,
                           source="databento ohlcv-1d, unadjusted",
                           events=out), fh, indent=1, ensure_ascii=False)
        print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def dist():
    """Where does rule 6's threshold come from. D5: from the carrier, not chosen."""
    days = load_calendar()
    print("max single-day |log return| inside each event window, upper percentiles")
    print("%-4s %8s %8s %8s %8s %8s" % ("ev", "n", "p50", "p99", "p99.9", "max"))
    for e in sorted(BOUNDARY):
        wd = window_days(BOUNDARY[e], days)
        px = read_days(set(wd))
        v = sorted(x for x in (max_abs_log_return(s, wd) for s in px.values()) if x)
        if not v:
            continue
        q = lambda f: v[min(len(v) - 1, int(f * len(v)))]
        print("%-4d %8d %8.3f %8.3f %8.3f %8.3f"
              % (e, len(v), q(0.50), q(0.99), q(0.999), v[-1]))
    print("\nrule 6 threshold in force: %.2f  (a two for one split is 0.69)"
          % RULE6_ABS_LOG_RETURN)
    return 0


def selftest():
    bad = []

    def chk(m, ok):
        print(("  ok   " if ok else "  FAIL ") + m)
        if not ok:
            bad.append(m)

    chk("rule 1 keeps a plain ticker", ticker_is_common("BKNG"))
    chk("rule 1 drops a preferred line", not ticker_is_common("BAC-PB"))
    chk("rule 1 drops a class line", not ticker_is_common("BH.A"))
    chk("rule 1 drops a six character ticker", not ticker_is_common("ABCDEF"))
    # These six pass every ticker-form test and are all funds. The form test alone
    # let them into the universe; only the folder taxonomy keeps them out.
    chk("the ticker form alone cannot tell a fund from a stock",
        all(ticker_is_common(x) for x in ("SOXL", "TECL", "VGT", "VUG", "VOOG", "MGK")))
    ef = etf_tickers(build=False)
    if ef:
        chk("the ETF blacklist catches the funds the form test missed: %d loaded" % len(ef),
            all(x in ef for x in ("SOXL", "TECL", "VGT", "VUG", "VOOG", "MGK")))
        chk("the ETF blacklist does not swallow ordinary stocks",
            not any(x in ef for x in ("NVR", "BKNG", "AZO", "MKL", "SEB")))
    else:
        print("  note  no ETF blacklist cached yet; --screen builds it")
    s = {"20190102": 100.0, "20190103": 50.0, "20190104": 50.5}
    chk("rule 6 sees a two for one split as 0.69: %.3f"
        % max_abs_log_return(s, sorted(s)),
        abs(max_abs_log_return(s, sorted(s)) - math.log(2)) < 1e-9)
    chk("rule 6's threshold is below a two for one split, so splits are caught",
        RULE6_ABS_LOG_RETURN < math.log(2))
    chk("rule 6's threshold is above any ordinary daily move",
        RULE6_ABS_LOG_RETURN > 0.20)
    # Rule 2b, and the arithmetic that makes it bite differently per event.
    chk("rule 2b needs $649 for event 2 and $243 for event 8: %.0f vs %.0f"
        % (HALF_TICK / DR[2], HALF_TICK / DR[8]),
        abs(HALF_TICK / DR[2] - 649) < 3 and abs(HALF_TICK / DR[8] - 243) < 3)
    chk("rule 2b binds above the price floor for the small-dr events",
        HALF_TICK / DR[2] > PRICE_FLOOR)
    chk("rule 2b is slack against the floor for the large-dr events",
        HALF_TICK / DR[7] < PRICE_FLOOR)
    chk("rule 2b introduces no threshold beyond half a tick and the tick grid",
        abs(HALF_TICK * 2 - 0.01) < 1e-12)
    chk("half a tick is half of one cent", abs(HALF_TICK - 0.005) < 1e-12)
    chk("the floor is the registered $300", abs(PRICE_FLOOR - 300.0) < 1e-9)
    chk("dr signs alternate across the scored candidates",
        all(DR_SIGN[e] != DR_SIGN[e + 1] for e in range(2, 8)))
    chk("every candidate event has a boundary, a dr and a sign",
        set(BOUNDARY) == set(DR) == set(DR_SIGN))
    print("selftest: %s" % ("PASS" if not bad else "FAIL, %d problem(s)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dist", action="store_true")
    ap.add_argument("--screen", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dist:
        return dist()
    if a.screen:
        return screen()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
