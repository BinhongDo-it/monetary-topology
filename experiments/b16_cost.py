"""Section 31 carrier, steps two and three of the free pre-purchase checks.

This file CANNOT buy
data: there is no download path in it at all. It only calls the free Databento
metadata endpoints.

    metadata.list_datasets        does ARCX.PILLAR exist, spelled that way
    metadata.get_dataset_range    when does each venue's history actually start
    symbology.resolve             which tickers do not resolve, or resolve oddly
    metadata.get_cost             the price of each (event, venue, month) batch
    metadata.get_billable_size    the billable bytes of the same

WHY THE VENUE CODES ARE LOOKED UP RATHER THAN ASSUMED

b14_legb_price2016 records the lesson: its first stooq URL form returned 404 for
every symbol because the form had been assumed. ARCX.PILLAR is written from
memory here, so --datasets checks it against the live list before anything else
uses it, and --resolve refuses to run if either code is absent.

WHY THE DATASET RANGE MATTERS

The pre-registration excludes event 1 on data availability: Databento's US
equities history is recorded elsewhere in this repo as starting 2018-05-01, and
the event needs 29 trading days before 2018-05-18. --datasets re-derives that
from the live endpoint rather than trusting the note, and prints, per event and
venue, whether the full 29+29 purchase window exists. If it turns out event 1 is
buyable after all, that is a finding and the pre-registration changes BEFORE any
reading, not after.

WHAT COMES OUT

--cost prints a per-event, per-venue, per-month table plus a grand quote, and
compares that quote with the estimate in pre-registration section 10.2. Section
10.3 step 4 says a divergence over 30% stops the run rather than proceeding.

Usage
    python experiments/b16_cost.py --selftest     no network
    python experiments/b16_cost.py --datasets     free, venue codes and ranges
    python experiments/b16_cost.py --resolve      free, symbol forms
    python experiments/b16_cost.py --cost         free, the quote
"""
import argparse
import ast
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
UNIVERSE = os.path.join(RESULTS, "b16_universe.json")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
QUOTE_OUT = os.path.join(RESULTS, "b16_quote.json")

API = "https://hist.databento.com/v0"
#: Pre-registration section 4.1. Checked against metadata.list_datasets by
#: --datasets before anything else uses them.
VENUES = ["XNAS.ITCH", "ARCX.PILLAR"]
SCHEMA = "bbo-1s"
#: Pre-registration section 4.2.
BUY_DAYS_EACH_SIDE = 29
#: Boundary trade dates, pre-registration section 4.3. Repeated here so
#: --cost-ohlcv can run before b16_universe.json exists.
EVENT_BOUNDARIES = ["2018-05-18", "2019-04-12", "2021-02-23", "2022-05-12",
                    "2023-02-23", "2024-05-20", "2025-05-13", "2026-04-02"]
#: The registered estimate, plan A: 200 symbols, ~$155.
ESTIMATE_USD = 155.0
#: Pre-registration section 10.3 step 4.
DIVERGENCE_STOP = 0.30
#: The only endpoints this file is allowed to reach (five). --selftest walks the AST and
#: requires the set of call() endpoints to equal this exactly, so adding a sixth
#: has to be a deliberate edit here rather than a quiet edit down in the body.
FREE_ENDPOINTS = {
    "metadata.list_datasets",
    "metadata.get_dataset_range",
    "symbology.resolve",
    "metadata.get_cost",
    "metadata.get_billable_size",
}
#: The screen needs AS-QUOTED prices. stooq's bulk archive adjusts both price
#: and volume (checked on the 2026-08-20 archive: GOOGL reads 59.41 on
#: 2019-03-14 against about 1,180 as quoted, and volume shows no jump across
#: any known ex-date), so the factor is not recoverable from it. Databento
#: serves raw exchange data, which is unadjusted, carries delisted symbols,
#: and makes a split a visible discontinuity. That removes the split table,
#: the survivorship registration, and the hand part of rule 6 at once.
OHLCV_SCHEMA = "ohlcv-1d"
#: Attribute names that would mean this module can pull bytes to disk. Checked as
#: attribute names on Call nodes, not as substrings of the source.
DOWNLOADER_ATTRS = {"urlretrieve", "copyfileobj", "get_range", "submit_job"}

#: Per (symbol, venue, month) unit price implied by B14 leg B's actual spend,
#: kept here only so --selftest can check the arithmetic in section 10.1.
B14_GB, B14_USD, B14_UNITS = 14.18, 34.6896, 108 * 2 * 8


def api_key():
    k = os.environ.get("DATABENTO_API_KEY")
    if k:
        return k.strip()
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            line = line.strip()
            if line.startswith("DATABENTO_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "no DATABENTO_API_KEY in the environment or in .env; nothing was requested")


def call(endpoint, params, key, method="POST"):
    url = API + "/" + endpoint
    data = urllib.parse.urlencode(params, doseq=True).encode() if params else None
    if method == "GET":
        url = url + ("?" + data.decode() if data else "")
        data = None
    req = urllib.request.Request(url, data=data)
    tok = base64.b64encode((key + ":").encode()).decode()
    req.add_header("Authorization", "Basic " + tok)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:600]}
    except Exception as ex:                                        # noqa: BLE001
        return {"http_error": type(ex).__name__, "body": str(ex)[:300]}


# ------------------------------------------------------------ windows

def load_universe():
    if not os.path.exists(UNIVERSE):
        raise SystemExit(
            "no %s. Run b16_universe.py --screen first; the pre-registration\n"
            "(section 3.4) puts the symbol counts before any spending."
            % os.path.relpath(UNIVERSE, ROOT))
    return json.load(open(UNIVERSE, encoding="utf-8"))


def load_calendar():
    if not os.path.exists(CAL_CACHE):
        raise SystemExit(
            "no %s. Run b16_universe.py --calendar ZIP first."
            % os.path.relpath(CAL_CACHE, ROOT))
    return json.load(open(CAL_CACHE, encoding="utf-8"))["days"]


def buy_window(boundary, days, each=BUY_DAYS_EACH_SIDE):
    """(first_day, last_day) as yyyymmdd, or None if the calendar is too short."""
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]          # the boundary day is in the post side
    if len(before) < each or len(after) < each:
        return None
    return before[-each], after[each - 1]


def months_spanned(first, last):
    """['YYYY-MM', ...] inclusive. Batching matches b14_legb_pull's (venue, month)."""
    y, m = int(first[:4]), int(first[4:6])
    ly, lm = int(last[:4]), int(last[4:6])
    out = []
    while (y, m) <= (ly, lm):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def month_bounds(mm):
    y, m = int(mm[:4]), int(mm[5:7])
    a = "%04d-%02d-01" % (y, m)
    b = "%04d-01-01" % (y + 1) if m == 12 else "%04d-%02d-01" % (y, m + 1)
    return a, b


def base_params(syms, venue, a, b):
    return {"dataset": venue, "symbols": ",".join(syms), "schema": SCHEMA,
            "start": a, "end": b, "stype_in": "raw_symbol", "mode": "historical"}


# ------------------------------------------------------------ steps

def datasets(key):
    live = call("metadata.list_datasets", {}, key, method="GET")
    if isinstance(live, dict) and "http_error" in live:
        print("list_datasets failed: %s %s" % (live["http_error"], live["body"][:200]))
        return 1
    live = set(live)
    print("venue codes, checked against the live list rather than assumed")
    missing = []
    for v in VENUES:
        ok = v in live
        print("  %-14s %s" % (v, "present" if ok else "ABSENT"))
        if not ok:
            missing.append(v)
    if missing:
        near = sorted(d for d in live if any(t in d for t in ("ARCX", "XNAS", "PILLAR", "ITCH")))
        print("\n  candidates that look close: %s" % ", ".join(near[:20]))
        print("  REFUSING to go further with a venue code that is not in the list.")
        return 1

    print("\ndataset ranges")
    ranges = {}
    for v in VENUES:
        r = call("metadata.get_dataset_range", {"dataset": v}, key, method="GET")
        ranges[v] = r
        print("  %-14s %s" % (v, json.dumps(r)[:160]))

    print("")
    print("per event: does the registered 29+29 purchase window exist")
    print("(calendar only. This has to run BEFORE the screen, because what it")
    print(" decides is which events are buyable at all.)")
    days = load_calendar()
    for idx, b in enumerate(EVENT_BOUNDARIES, start=1):
        w = buy_window(b, days)
        if w is None:
            print("  event %-2d %s  calendar too short" % (idx, b))
            continue
        note = ""
        for v in VENUES:
            r = ranges.get(v)
            start = r.get("start", "") if isinstance(r, dict) else ""
            if start and start[:10].replace("-", "") > w[0]:
                note += "  %s starts %s, AFTER the window opens" % (v, start[:10])
        print("  event %-2d %s  window %s..%s  %s" % (idx, b, w[0], w[1], note or "ok"))
    print("\nif an event marked scored=False turns out to be buyable, that is a finding:")
    print("amend the pre-registration BEFORE any reading, not after.")
    return 0


def resolve(key):
    days, uni = load_calendar(), load_universe()["events"]
    bad = 0
    for n in sorted(uni, key=int):
        e = uni[n]
        if not e["scored"]:
            continue
        syms = [s[0] if isinstance(s, (list, tuple)) else s for s in e["symbols"]]
        if not syms:
            print("event %s: no symbols; run b16_universe.py --screen" % n)
            bad += 1
            continue
        w = buy_window(e["boundary"], days)
        for v in VENUES:
            r = call("symbology.resolve",
                     {"dataset": v, "symbols": ",".join(syms), "stype_in": "raw_symbol",
                      "stype_out": "instrument_id",
                      "start_date": "%s-%s-%s" % (w[0][:4], w[0][4:6], w[0][6:]),
                      "end_date": "%s-%s-%s" % (w[1][:4], w[1][4:6], w[1][6:])}, key)
            if isinstance(r, dict) and "http_error" in r:
                print("event %s %s: HTTP %s %s" % (n, v, r["http_error"], r["body"][:160]))
                bad += 1
                continue
            res = (r or {}).get("result", {})
            nf = sorted((r or {}).get("not_found", []) or [])
            multi = sorted(k for k, val in res.items() if isinstance(val, list) and len(val) > 1)
            print("event %-2s %-14s resolved=%d  not_found=%d  multi_mapping=%d"
                  % (n, v, len(res), len(nf), len(multi)))
            if nf:
                print("    not found: %s" % ", ".join(nf[:20]))
            if multi:
                print("    ** ticker form changes inside the window: %s" % ", ".join(multi[:20]))
                print("    ** B14 hit this once (AMSW A -> AMSWA) and three call sites")
                print("       matched literally. Fix before the pull, not after.")
    return 1 if bad else 0


def cost_ohlcv(key):
    """Free quote for the unadjusted daily-bar screen. Buys nothing.

    One month around each event's screen date, ALL_SYMBOLS, one venue. If this
    comes back cheap the price screen moves off stooq entirely and three
    registered caveats go away with it.
    """
    days = load_calendar()
    print("quoting %s, ALL_SYMBOLS, one venue, one month per screen date" % OHLCV_SCHEMA)
    grand, tot = 0.0, 0
    for e in EVENT_BOUNDARIES:
        before = [d for d in days if d < e.replace("-", "")]
        if len(before) < 50:
            print("  %s  calendar too short" % e)
            continue
        sd = before[-50]
        mm = "%s-%s" % (sd[:4], sd[4:6])
        a, b = month_bounds(mm)
        p = dict(dataset=VENUES[0], symbols="ALL_SYMBOLS", schema=OHLCV_SCHEMA,
                 start=a, end=b, stype_in="raw_symbol", mode="historical")
        c = call("metadata.get_cost", p, key)
        z = call("metadata.get_billable_size", p, key)
        if isinstance(c, dict):
            print("  %s screen %s  HTTP %s %s"
                  % (e, sd, c.get("http_error"), str(c.get("body", ""))[:160]))
            continue
        print("  boundary %s  screen date %s  month %s  $%8.4f  %8.1f MB"
              % (e, sd, mm, float(c), int(z) / 1e6))
        grand += float(c)
        tot += int(z)
    print("  screen months subtotal  $%.4f  (%.2f GB)" % (grand, tot / 1e9))

    # Rule 6 (no split, reverse split, >2% ex-dividend, tender or long halt inside
    # the window) is checkable from UNADJUSTED daily bars as a price discontinuity.
    # That needs bars over the event window, not the screen date, so price those too
    # and report one number rather than two.
    print("")
    print("event-window months, for rule 6 read off price discontinuities")
    g2, t2, seen = 0.0, 0, set()
    for b in EVENT_BOUNDARIES:
        w = buy_window(b, days)
        if w is None:
            continue
        for mm in months_spanned(w[0], w[1]):
            if mm in seen:
                continue
            seen.add(mm)
            a, bb = month_bounds(mm)
            pp = dict(dataset=VENUES[0], symbols="ALL_SYMBOLS", schema=OHLCV_SCHEMA,
                      start=a, end=bb, stype_in="raw_symbol", mode="historical")
            c = call("metadata.get_cost", pp, key)
            z = call("metadata.get_billable_size", pp, key)
            if isinstance(c, dict):
                print("  %s  HTTP %s %s"
                      % (mm, c.get("http_error"), str(c.get("body", ""))[:120]))
                continue
            print("  %s  $%8.4f  %8.1f MB" % (mm, float(c), int(z) / 1e6))
            g2 += float(c)
            t2 += int(z)
    print("  event-window months subtotal  $%.4f  (%.2f GB, %d distinct months)"
          % (g2, t2 / 1e9, len(seen)))
    print("")
    print("  DAILY-BAR SCREEN, ALL IN   $%.4f   (%.2f GB)"
          % (grand + g2, (tot + t2) / 1e9))
    print("  what this buys, against the free stooq route:")
    print("    prices are AS QUOTED, so the >$300 rule can be applied at all")
    print("    delisted symbols are present, so the survivorship note goes away")
    print("    a split is a visible discontinuity, so rule 6 stops needing a hand table")
    return 0


def cost(key):
    days, uni = load_calendar(), load_universe()["events"]
    grand, table = 0.0, []
    for n in sorted(uni, key=int):
        e = uni[n]
        if not e["scored"]:
            print("event %s: excluded before purchase (%s)" % (n, e.get("note", "")))
            continue
        syms = [s[0] if isinstance(s, (list, tuple)) else s for s in e["symbols"]]
        w = buy_window(e["boundary"], days)
        if w is None or not syms:
            print("event %s: no window or no symbols" % n)
            continue
        print("\n=== event %s  boundary %s  window %s..%s  %d symbols ==="
              % (n, e["boundary"], w[0], w[1], len(syms)))
        for v in VENUES:
            sub, subb = 0.0, 0
            for mm in months_spanned(w[0], w[1]):
                a, b = month_bounds(mm)
                p = base_params(syms, v, a, b)
                c = call("metadata.get_cost", p, key)
                z = call("metadata.get_billable_size", p, key)
                if isinstance(c, dict):
                    print("  %-14s %s  HTTP %s %s"
                          % (v, mm, c.get("http_error"), str(c.get("body", ""))[:160]))
                    continue
                usd, byts = float(c), int(z)
                print("  %-14s %s  $%8.4f  %9.1f MB" % (v, mm, usd, byts / 1e6))
                table.append(dict(event=n, venue=v, month=mm, usd=usd, bytes=byts))
                sub += usd
                subb += byts
            print("  %-14s subtotal $%8.4f  %9.1f MB" % (v, sub, subb / 1e6))
            grand += sub

    tot_b = sum(r["bytes"] for r in table)
    print("\nGRAND QUOTE   $%.4f   (%.2f GB billable)" % (grand, tot_b / 1e9))
    print("registered estimate, plan A: $%.2f" % ESTIMATE_USD)
    if ESTIMATE_USD > 0:
        div = (grand - ESTIMATE_USD) / ESTIMATE_USD
        print("divergence from the estimate: %+.1f%%" % (div * 100))
        if abs(div) > DIVERGENCE_STOP:
            print("** OVER THE %.0f%% STOP (section 10.3 step 4). Do not proceed to the"
                  % (DIVERGENCE_STOP * 100))
            print("** purchase. Re-cost the design before anything is bought.")
    os.makedirs(RESULTS, exist_ok=True)
    with open(QUOTE_OUT, "w", encoding="utf-8") as fh:
        json.dump(dict(schema=SCHEMA, venues=VENUES, buy_days_each_side=BUY_DAYS_EACH_SIDE,
                       grand_usd=round(grand, 6), billable_bytes=tot_b,
                       estimate_usd=ESTIMATE_USD, batches=table), fh, indent=1)
    print("wrote %s" % os.path.relpath(QUOTE_OUT, ROOT))
    return 0


# ------------------------------------------------------------ selftest

def selftest():
    bad = []

    def chk(msg, ok):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            bad.append(msg)

    days = ["2019%02d%02d" % (m, d) for m in range(1, 7) for d in range(1, 21)]
    w = buy_window("2019-04-12", days, each=29)
    chk("the buy window is 29 each side and the boundary sits in the post side: %s" % (w,),
        w is not None and w[0] < "20190412" <= w[1])
    chk("a short calendar returns None rather than a truncated window",
        buy_window("2019-04-12", days[:10], each=29) is None)

    chk("months_spanned is inclusive and crosses a year end: %s"
        % months_spanned("20181210", "20190205"),
        months_spanned("20181210", "20190205") == ["2018-12", "2019-01", "2019-02"])
    chk("month_bounds rolls December into the next year",
        month_bounds("2018-12") == ("2018-12-01", "2019-01-01"))

    p = base_params(["A", "B"], "XNAS.ITCH", "2019-04-01", "2019-05-01")
    chk("the request carries the registered schema", p["schema"] == SCHEMA)
    chk("symbols go over as raw_symbol", p["stype_in"] == "raw_symbol")

    # Section 10.1's unit price, recomputed here so a typo in the doc would show.
    unit_usd = B14_USD / B14_UNITS
    unit_mb = B14_GB * 1000.0 / B14_UNITS
    chk("B14's implied unit price is $0.0201 per symbol-venue-month: $%.4f" % unit_usd,
        abs(unit_usd - 0.0201) < 0.0005)
    chk("B14's implied unit size is 8.2 MB: %.1f MB" % unit_mb, abs(unit_mb - 8.2) < 0.3)
    est = 200 * 2 * (58 / 21.0) * 7 * unit_usd
    chk("plan A's $155 reproduces from the unit price: $%.0f" % est,
        abs(est - ESTIMATE_USD) / ESTIMATE_USD < 0.10)

    # The file must be structurally unable to buy. This is the check that matters,
    # and it is the one this repo has got wrong before: a `"..." not in src` string
    # self-check reads its own forbidden list out of its own source and fails, or
    # worse, passes for the wrong reason. So walk the AST and scope the domain.
    #
    # Positive whitelist, not a blacklist: collect the endpoint literal of every
    # call(<str>, ...) site and require the set to be exactly the free four. A new
    # endpoint added anywhere in the file then has to be declared here on purpose.
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    endpoints, url_attrs = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "call" and node.args:
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    endpoints.add(a0.value)
                else:
                    endpoints.add("<COMPUTED>")
            if isinstance(f, ast.Attribute):
                url_attrs.add(f.attr)
    chk("every endpoint reached by call() is a literal, none is computed at runtime",
        "<COMPUTED>" not in endpoints)
    chk("the daily-bar screen uses a bar schema, not a quote schema",
        OHLCV_SCHEMA.startswith("ohlcv"))
    chk("eight boundary dates are declared for --cost-ohlcv",
        len(EVENT_BOUNDARIES) == 8)
    chk("the endpoint set is exactly the free five: %s" % sorted(endpoints),
        endpoints == FREE_ENDPOINTS)
    chk("no downloader is invoked anywhere in the module",
        not (url_attrs & DOWNLOADER_ATTRS))

    print("selftest: %s" % ("PASS" if not bad else "FAIL, %d problem(s)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--datasets", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--cost", action="store_true")
    ap.add_argument("--cost-ohlcv", action="store_true",
                    help="free quote for the unadjusted daily-bar price screen")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.datasets:
        return datasets(api_key())
    if a.resolve:
        return resolve(api_key())
    if a.cost_ohlcv:
        return cost_ohlcv(api_key())
    if a.cost:
        return cost(api_key())
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
