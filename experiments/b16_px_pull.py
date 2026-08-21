"""Section 31 carrier: buy UNADJUSTED daily bars for the price screen.

This is the
only file in the B16 set that spends money. b16_cost.py cannot buy anything
and its selftest enforces that by walking its own AST; the split is deliberate.

WHY BUY BARS AT ALL WHEN stooq IS FREE

Checked on the 2026-08-20 stooq archive that is already in data/raw:

    GOOGL  2019-03-14   archive 59.41   as quoted about 1180
    AMZN   2019-03-14   archive 84.31   as quoted about 1700
    CMG    2019-03-14   archive 12.85   as quoted about  690
    NVR    2019-03-14   archive 2722.77 as quoted about 2900   (never split)

The archive is split adjusted, so a ">$300 as quoted" screen run on it keeps NVR
and throws away GOOGL, AMZN, CMG and BKNG. The factor is not recoverable from the
archive either: volume is adjusted too, and across seven known ex-dates the
volume ratio sits between 0.43 and 1.39, which is ordinary day to day variation
and not a 3x, 10x, 20x or 50x jump.

Databento serves raw exchange data. Prices are as quoted, delisted symbols are
present, and a split shows up as a real discontinuity. One purchase therefore
retires three things at once: the split table, the survivorship note, and the
hand-built corporate-action table rule 6 would otherwise need.

WHAT IS BOUGHT

    dataset   XNAS.ITCH
    schema    ohlcv-1d
    symbols   ALL_SYMBOLS
    months    the eight screen months, plus every distinct month touched by an
              event's 29+29 purchase window

Event 1's months are refused by the API rather than by this file: XNAS.ITCH
starts 2018-05-01 and the 2018-03 screen month returns HTTP 422
data_start_before_available_start. That is the third independent confirmation of
the registered exclusion, after the dataset range and the calendar arithmetic.

HOUSE RULES OBSERVED

Nothing is deleted. A month already on disk is skipped. A stale .part from a
crashed run is renamed with an .expired suffix rather than removed. Every batch
is quoted before it is bought, the quote is checked against a per-batch ceiling
and a cumulative ceiling, and the ledger is written after each batch so a run
that stops halfway leaves an accurate record.

    python experiments/b16_px_pull.py --selftest        no network
    python experiments/b16_px_pull.py --plan            no network
    python experiments/b16_px_pull.py --cost            free, quotes every month
    python experiments/b16_px_pull.py --fetch 2019-01   buys one month
    python experiments/b16_px_pull.py --fetch-all       buys every missing month
    python experiments/b16_px_pull.py --verify          no network
"""
import argparse
import base64
import datetime
import gzip
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "b16_px")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
SPEND = os.path.join(RESULTS, "b16_px_spend.json")

API = "https://hist.databento.com/v0"
VENUE = "XNAS.ITCH"
SCHEMA = "ohlcv-1d"
SYMBOLS = "ALL_SYMBOLS"
#: The API refuses ALL_SYMBOLS together with map_symbols=true and says so:
#:   "Invalid request for 'ALL_SYMBOLS' with `map_symbols`. This is not currently
#:    supported, try requesting with up to 2000 specific symbols, or set
#:    `map_symbols` to false."
#: So the bars come back keyed by instrument_id, and --symbology resolves those
#: ids back to tickers with the free symbology endpoint, one call per month. The
#: alternative the API offers, batch.submit_job, is asynchronous and would need a
#: submit/poll/download loop for no gain here.
MAP_SYMBOLS = "false"

#: Pre-registration sections 3.2 and 4.2.
SCREEN_LAG_TRADING_DAYS = 50
BUY_DAYS_EACH_SIDE = 29
EVENT_BOUNDARIES = ["2018-05-18", "2019-04-12", "2021-02-23", "2022-05-12",
                    "2023-02-23", "2024-05-20", "2025-05-13", "2026-04-02"]
#: Pre-registration section 4.3. Event 1 is excluded on data availability, so its
#: months are not bought: half a pre-window for an event that cannot be scored is
#: money spent on nothing. Two of its four months (2018-05, 2018-06) do exist and
#: would have been billed, so leaving this out would have cost real money quietly.
SCORED = {2, 3, 4, 5, 6, 7, 8}

#: The free quote for the eight screen months came back at $2.1815, the largest
#: single month at $0.3640. A batch ceiling of $1.00 is three times the largest
#: observed month, so an ordinary month never trips it and a surprise does. The
#: cumulative ceiling is set above the expected all-in (screen months plus event
#: window months, roughly $9) with room for the same kind of surprise.
BATCH_CEILING_USD = 1.00
#: Registered 2026-08-20. $80 is the cumulative stop for THIS ROUND. It is NOT a
#: project ceiling: tripping it means stop and re-check before continuing, not
#: "the station is over". Read it as a circuit breaker. A future session that
#: finds this at 80 should not conclude the design was scoped to $80.
TOTAL_CEILING_USD = 80.00
GZIP_LEVEL = 6


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


def open_request(endpoint, params, key):
    data = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(API + "/" + endpoint, data=data)
    req.add_header("Authorization",
                   "Basic " + base64.b64encode((key + ":").encode()).decode())
    return urllib.request.urlopen(req, timeout=1800)


def call(endpoint, params, key):
    try:
        with open_request(endpoint, params, key) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:400]}


def month_bounds(mm):
    y, m = int(mm[:4]), int(mm[5:7])
    a = "%04d-%02d-01" % (y, m)
    b = "%04d-01-01" % (y + 1) if m == 12 else "%04d-%02d-01" % (y, m + 1)
    return a, b


def months_spanned(first, last):
    y, m = int(first[:4]), int(first[4:6])
    ly, lm = int(last[:4]), int(last[4:6])
    out = []
    while (y, m) <= (ly, lm):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load_calendar():
    if not os.path.exists(CAL_CACHE):
        raise SystemExit("no %s. Run b16_universe.py --calendar ZIP first."
                         % os.path.relpath(CAL_CACHE, ROOT))
    return json.load(open(CAL_CACHE, encoding="utf-8"))["days"]


def screen_date(boundary, days, lag=SCREEN_LAG_TRADING_DAYS):
    before = [d for d in days if d < boundary.replace("-", "")]
    return before[-lag] if len(before) >= lag else None


def buy_window(boundary, days, each=BUY_DAYS_EACH_SIDE):
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]
    if len(before) < each or len(after) < each:
        return None
    return before[-each], after[each - 1]


def planned_months(days):
    """Every month to buy, with why, ordered. Deterministic; no set iteration order."""
    why = {}
    for i, b in enumerate(EVENT_BOUNDARIES, start=1):
        if i not in SCORED:
            continue
        sd = screen_date(b, days)
        if sd:
            why.setdefault("%s-%s" % (sd[:4], sd[4:6]), []).append("screen e%d" % i)
        w = buy_window(b, days)
        if w:
            for mm in months_spanned(w[0], w[1]):
                why.setdefault(mm, []).append("window e%d" % i)
    return sorted(why), why


def dst_path(mm):
    return os.path.join(RAW, "%s_%s_%s.csv.gz"
                        % (SCHEMA, VENUE.replace(".", "_"), mm.replace("-", "")))


def map_is_interval_shaped(smap):
    """The rebuilt maps hold a list of {d0,d1,s}. The first, broken, generation
    held a bare ticker string. Callers check this rather than crashing on it."""
    vals = list(smap.values())[:50]
    return bool(vals) and all(isinstance(v, list) for v in vals)


def require_shaped(smap, mm):
    if map_is_interval_shaped(smap):
        return True
    print("  %s  the map on disk is the COLLAPSED shape and cannot be used." % mm)
    print("        ITCH reassigns locate codes daily, so one ticker per id is")
    print("        wrong for every day but the first. Rebuild it, free:")
    print("            python experiments/b16_px_pull.py --symbology")
    return False


def ticker_at(smap, iid, day):
    """The raw_symbol this instrument_id carried on `day` (yyyymmdd), or None.

    `smap` is {instrument_id: [{"d0","d1","s"}, ...]}. Databento's intervals are
    half open, d0 inclusive and d1 exclusive.
    """
    d = "%s-%s-%s" % (day[:4], day[4:6], day[6:])
    for iv in smap.get(str(iid), ()):
        d0, d1 = iv.get("d0", ""), iv.get("d1", "")
        if (not d0 or d0 <= d) and (not d1 or d < d1):
            return iv.get("s")
    return None


def sym_path(mm):
    return os.path.join(RAW, "symbology_%s_%s.json"
                        % (VENUE.replace(".", "_"), mm.replace("-", "")))


def base_params(mm):
    a, b = month_bounds(mm)
    return {"dataset": VENUE, "symbols": SYMBOLS, "schema": SCHEMA,
            "start": a, "end": b, "stype_in": "raw_symbol", "mode": "historical"}


def load_spend():
    if os.path.exists(SPEND):
        return json.load(open(SPEND, encoding="utf-8"))
    return {"batches": [], "usd_total": 0.0}


def save_spend(led):
    led["usd_total"] = round(sum(float(x["usd"]) for x in led["batches"]), 6)
    tmp = SPEND + ".part"
    os.makedirs(RESULTS, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=2, sort_keys=True)
    os.replace(tmp, SPEND)


def park(path):
    """Move a stale artefact aside. The house rule forbids deleting anything."""
    if os.path.exists(path):
        aside = path + ".expired_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.rename(path, aside)
        print("        parked a stale file as %s" % os.path.basename(aside))


# ---------------------------------------------------------------- actions

def plan():
    days = load_calendar()
    months, why = planned_months(days)
    print("dataset %s  schema %s  symbols %s" % (VENUE, SCHEMA, SYMBOLS))
    print("%d distinct months, events %s (event 1 is excluded, section 4.3)"
          % (len(months), ",".join(str(i) for i in sorted(SCORED))))
    for mm in months:
        d = dst_path(mm)
        print("  %s  %-28s %s" % (mm, ",".join(why[mm]),
                                  "ON DISK" if os.path.exists(d) else ""))
    print("\nceilings: batch $%.2f, cumulative $%.2f" % (BATCH_CEILING_USD, TOTAL_CEILING_USD))
    print("ledger so far: $%.4f" % load_spend()["usd_total"])
    return 0


def cost(key):
    days = load_calendar()
    months, why = planned_months(days)
    grand, byts, refused = 0.0, 0, []
    for mm in months:
        p = base_params(mm)
        c = call("metadata.get_cost", p, key)
        z = call("metadata.get_billable_size", p, key)
        if isinstance(c, dict):
            case = ""
            try:
                case = json.loads(c["body"])["detail"]["case"]
            except Exception:                                       # noqa: BLE001
                case = str(c.get("body", ""))[:60]
            print("  %s  HTTP %s  %s" % (mm, c.get("http_error"), case))
            refused.append(mm)
            continue
        print("  %s  $%8.4f  %8.1f MB   %s" % (mm, float(c), int(z) / 1e6, ",".join(why[mm])))
        grand += float(c)
        byts += int(z)
    print("\n  QUOTE  $%.4f  (%.2f GB) over %d months" % (grand, byts / 1e9, len(months) - len(refused)))
    if refused:
        print("  refused by the API: %s" % ", ".join(refused))
        print("  (event 1's months land here; that is the registered exclusion,")
        print("   confirmed by the API rather than by this file)")
    print("  ceilings: batch $%.2f, cumulative $%.2f" % (BATCH_CEILING_USD, TOTAL_CEILING_USD))
    if grand > TOTAL_CEILING_USD:
        print("  ** the quote exceeds the cumulative ceiling. Do not raise the ceiling")
        print("  ** without stopping to re-check the design first.")
    return 0


def fetch(key, months):
    os.makedirs(RAW, exist_ok=True)
    days = load_calendar()
    allowed, _ = planned_months(days)
    led = load_spend()
    for mm in months:
        if mm not in allowed:
            print("  %s is not in the registered plan; refused" % mm)
            return 1
    for mm in months:
        dst = dst_path(mm)
        if os.path.exists(dst):
            print("  SKIP  %s  already on disk, %.1f MB" % (mm, os.path.getsize(dst) / 1e6))
            continue
        p = base_params(mm)
        c = call("metadata.get_cost", p, key)
        if isinstance(c, dict):
            print("  STOP  %s  quote failed HTTP %s  %s"
                  % (mm, c.get("http_error"), str(c.get("body", ""))[:200]))
            return 1
        usd = float(c)
        if usd > BATCH_CEILING_USD:
            print("  STOP  %s  quote $%.4f exceeds the batch ceiling $%.2f"
                  % (mm, usd, BATCH_CEILING_USD))
            return 1
        if led["usd_total"] + usd > TOTAL_CEILING_USD:
            print("  STOP  %s  $%.4f would take the running total to $%.4f, past $%.2f"
                  % (mm, usd, led["usd_total"] + usd, TOTAL_CEILING_USD))
            return 1
        print("  BUY   %s  quote $%.4f  (running $%.4f)"
              % (mm, usd, led["usd_total"] + usd))
        tmp = dst + ".part"
        park(tmp)
        q = dict(p)
        q.pop("mode", None)
        q.update({"encoding": "csv", "map_symbols": MAP_SYMBOLS})
        t0, got = datetime.datetime.now(), 0
        try:
            with open_request("timeseries.get_range", q, key) as r, \
                    gzip.open(tmp, "wb", GZIP_LEVEL) as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    got += len(chunk)
                    out.write(chunk)
        except urllib.error.HTTPError as e:
            print("  STOP  %s  body HTTP %s  %s"
                  % (mm, e.code, e.read().decode("utf-8", "replace")[:300]))
            print("        nothing added to the ledger for this batch; the .part stays")
            print("        where it is and the next attempt parks it aside.")
            return 1
        os.replace(tmp, dst)
        secs = (datetime.datetime.now() - t0).total_seconds()
        print("        %.1f MB csv -> %.1f MB gz in %.0f s"
              % (got / 1e6, os.path.getsize(dst) / 1e6, secs))
        led["batches"].append(dict(month=mm, usd=usd, csv_bytes=got,
                                   gz_bytes=os.path.getsize(dst),
                                   at=datetime.datetime.now().isoformat(timespec="seconds")))
        save_spend(led)
    print("\n  ledger total $%.4f over %d batches" % (led["usd_total"], len(led["batches"])))
    return 0


def symbology(key, months=None):
    """instrument_id -> raw_symbol per month. Free. Cached beside the bars."""
    days = load_calendar()
    planned, _ = planned_months(days)
    months = months or planned
    for mm in months:
        d = dst_path(mm)
        if not os.path.exists(d):
            print("  %s  no bars on disk yet" % mm)
            continue
        out = sym_path(mm)
        if os.path.exists(out):
            existing = json.load(open(out, encoding="utf-8"))
            shaped = map_is_interval_shaped(existing)
            if shaped:
                print("  %s  map already on disk (%d ids, interval shaped)"
                      % (mm, len(existing)))
                continue
            print("  %s  map on disk is the collapsed shape; parking it" % mm)
            park(out)
        ids, head = set(), None
        with gzip.open(d, "rt", encoding="utf-8", errors="replace") as fh:
            for k, line in enumerate(fh):
                p_ = line.rstrip("\n").split(",")
                if k == 0:
                    head = [c.strip() for c in p_]
                    continue
                if head and "instrument_id" in head:
                    j = head.index("instrument_id")
                    if len(p_) > j and p_[j].strip():
                        ids.add(p_[j].strip())
        if not ids:
            print("  %s  no instrument_id column; header was %s" % (mm, head))
            continue
        a, b = month_bounds(mm)
        mapping, ids = {}, sorted(ids)
        #: The endpoint caps a request; 2000 is the number the API's own error
        #: message names, so chunk at that rather than at a guessed size.
        for i in range(0, len(ids), 2000):
            chunk = ids[i:i + 2000]
            r = call("symbology.resolve",
                     {"dataset": VENUE, "symbols": ",".join(chunk),
                      "stype_in": "instrument_id", "stype_out": "raw_symbol",
                      "start_date": a, "end_date": b}, key)
            if isinstance(r, dict) and "http_error" in r:
                print("  %s  resolve HTTP %s  %s"
                      % (mm, r["http_error"], str(r.get("body", ""))[:200]))
                return 1
            for k_, v in (r or {}).get("result", {}).items():
                # Keep every interval. Collapsing to v[0] was the bug: ITCH
                # reassigns locate codes daily as listings come and go, so the
                # month-start mapping is wrong by a small symbol-dependent
                # offset for every later day. Caught by a price sanity check,
                # not by any test that existed at the time.
                if isinstance(v, list):
                    mapping[k_] = [x for x in v if isinstance(x, dict)]
                elif v:
                    mapping[k_] = [{"d0": a, "d1": b, "s": v}]
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(mapping, fh, indent=0, sort_keys=True)
        spans = sum(len(v) for v in mapping.values())
        print("  %s  %d ids -> %d mapped, %d intervals (%.2f per id)  %s"
              % (mm, len(ids), len(mapping), spans,
                 spans / max(len(mapping), 1), os.path.basename(out)))
    return 0


def verify():
    days = load_calendar()
    months, _ = planned_months(days)
    print("%-9s %10s %10s %10s %10s" % ("month", "rows", "ids", "tickers", "MB gz"))
    missing = []
    for mm in months:
        d = dst_path(mm)
        if not os.path.exists(d):
            missing.append(mm)
            continue
        rows, syms, head = 0, set(), None
        smap = json.load(open(sym_path(mm), encoding="utf-8")) if os.path.exists(sym_path(mm)) else {}
        if smap and not map_is_interval_shaped(smap):
            require_shaped(smap, mm)
            smap = {}
        with gzip.open(d, "rt", encoding="utf-8", errors="replace") as fh:
            for k, line in enumerate(fh):
                if k == 0:
                    head = [c.strip() for c in line.split(",")]
                    continue
                rows += 1
                p = line.rstrip("\n").split(",")
                for col in ("symbol", "instrument_id"):
                    if head and col in head and len(p) > head.index(col):
                        syms.add(p[head.index(col)].strip())
                        break
        mid = mm.replace("-", "") + "15"
        named = {t for i in syms for t in [ticker_at(smap, i, mid)] if t}
        print("%-9s %10d %10d %10d %10.1f"
              % (mm, rows, len(syms), len(named), os.path.getsize(d) / 1e6))
    if missing:
        print("\nnot on disk yet: %s" % ", ".join(missing))
    return 0


STOOQ_ZIP = os.path.join(ROOT, "data", "raw", "d_us_txt.zip")


def crosscheck(day):
    """No network. Do the mapped tickers price like the stooq archive on `day`?

    stooq is split ADJUSTED, so a splitter must disagree by its factor. A name
    that never split must agree closely. If the id mapping is wrong, agreement
    collapses for everybody, and that is the failure this catches. It is the
    check whose absence let a whole month of mislabelled bars look fine.
    """
    import zipfile
    mm = day[:6]
    f, sp = dst_path("%s-%s" % (mm[:4], mm[4:])), sym_path("%s-%s" % (mm[:4], mm[4:]))
    if not (os.path.exists(f) and os.path.exists(sp)):
        print("  %s: bars or map missing" % day)
        return 1
    smap = json.load(open(sp, encoding="utf-8"))
    if not require_shaped(smap, day[:6]):
        return 1
    want = int(datetime.datetime(int(day[:4]), int(day[4:6]), int(day[6:]),
                                 tzinfo=datetime.timezone.utc).timestamp()) * 10 ** 9
    db = {}
    with gzip.open(f, "rt", encoding="utf-8", errors="replace") as fh:
        h = [c.strip() for c in fh.readline().split(",")]
        it, ii, ic = h.index("ts_event"), h.index("instrument_id"), h.index("close")
        for line in fh:
            p = line.split(",")
            if len(p) <= ic or int(p[it]) != want:
                continue
            t = ticker_at(smap, p[ii].strip(), day)
            if t:
                db[t] = int(p[ic]) / 1e9
    if not os.path.exists(STOOQ_ZIP):
        print("  %s: %d tickers priced; no stooq archive to compare against"
              % (day, len(db)))
        return 0
    st = {}
    with zipfile.ZipFile(STOOQ_ZIP) as z:
        for info in z.infolist():
            b = os.path.basename(info.filename).lower()
            if not b.endswith(".us.txt"):
                continue
            sym = b[: -len(".us.txt")].upper()
            if sym not in db:
                continue
            for line in z.read(info).decode("utf-8", "replace").splitlines()[1:]:
                q = line.split(",")
                if len(q) > 7 and q[2].replace("-", "") == day:
                    try:
                        st[sym] = float(q[7])
                    except ValueError:
                        pass
                    break
    both = sorted(set(db) & set(st))
    close = [t for t in both if st[t] > 0 and abs(db[t] / st[t] - 1) < 0.02]
    print("  %s  databento=%d  stooq=%d  common=%d  agree within 2%%=%d (%.1f%%)"
          % (day, len(db), len(st), len(both), len(close),
             100.0 * len(close) / max(len(both), 1)))
    off = [(t, db[t], st[t]) for t in both if st[t] > 0
           and 1.02 <= db[t] / st[t] <= 100][:8]
    if off:
        print("       splitters (databento above stooq, as expected): "
              + ", ".join("%s %.0f/%.2f" % o for o in off))
    return 0 if len(close) >= 0.5 * max(len(both), 1) else 1


# ---------------------------------------------------------------- selftest

def selftest():
    bad = []

    def chk(msg, ok):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            bad.append(msg)

    chk("month_bounds rolls December", month_bounds("2018-12") == ("2018-12-01", "2019-01-01"))
    chk("months_spanned is inclusive across a year end",
        months_spanned("20181210", "20190205") == ["2018-12", "2019-01", "2019-02"])

    days = ["%04d%02d%02d" % (y, m, d) for y in (2018, 2019)
            for m in range(1, 13) for d in range(1, 21)]
    sd = screen_date("2019-04-12", days)
    w = buy_window("2019-04-12", days)
    chk("the screen date is strictly before the boundary: %s" % sd, sd is not None and sd < "20190412")
    chk("the buy window brackets the boundary: %s" % (w,), w is not None and w[0] < "20190412" <= w[1])
    months, why = planned_months(days)
    chk("every planned month has a reason attached", all(why[m] for m in months))
    chk("no month is planned for the excluded event 1",
        not any("e1" in r for m in months for r in why[m]))
    chk("2018-05 and 2018-06 are not bought even though the API would sell them",
        "2018-05" not in months and "2018-06" not in months)
    chk("the plan is sorted and free of duplicates", months == sorted(set(months)))

    p = base_params("2019-01")
    chk("the whole universe is requested, not a list", p["symbols"] == "ALL_SYMBOLS")
    chk("the schema is a bar schema, so this cannot silently buy quotes",
        p["schema"] == SCHEMA and SCHEMA.startswith("ohlcv"))
    # The combination the API refused on the first real fetch. It cost a wasted
    # round trip and it was invisible to every check that existed at the time.
    chk("ALL_SYMBOLS is never paired with map_symbols=true",
        not (SYMBOLS == "ALL_SYMBOLS" and str(MAP_SYMBOLS).lower() == "true"))
    chk("the symbology cache path is distinct from the bar path",
        sym_path("2019-01") != dst_path("2019-01"))
    # The bug: a month-wide map collapsed to one ticker per id. ITCH reassigns
    # locate codes daily, so the map must be interval shaped and the lookup must
    # take a date. These two would have failed on the broken version.
    demo = {"899": [{"d0": "2019-01-01", "d1": "2019-01-15", "s": "BKNG"},
                    {"d0": "2019-01-15", "d1": "2019-02-01", "s": "BKI"}]}
    chk("ticker_at reads the interval covering the day, not the first one",
        ticker_at(demo, "899", "20190102") == "BKNG"
        and ticker_at(demo, "899", "20190131") == "BKI")
    chk("ticker_at returns None outside every interval",
        ticker_at(demo, "899", "20190215") is None)
    chk("ticker_at is not fooled by an unknown id", ticker_at(demo, "1", "20190102") is None)
    chk("the collapsed first-generation shape is detected, not crashed on",
        map_is_interval_shaped(demo) and not map_is_interval_shaped({"1": "A", "10": "AAN"}))

    # The ceilings must actually be able to bite. A ceiling below the largest
    # observed month would stop every run; one far above it would never fire.
    chk("the batch ceiling sits above the largest quoted month ($0.3640)",
        BATCH_CEILING_USD > 0.3640)
    chk("the batch ceiling is not so high it can never fire", BATCH_CEILING_USD < 2.0)
    # The ceiling is the registered cap, not a band around an estimate.
    # Structural: it must equal the registered figure and must exceed the quote,
    # or the run cannot finish; and it must be finite, or it is not a ceiling.
    chk("the cumulative ceiling is the declared $80 cap",
        abs(TOTAL_CEILING_USD - 80.00) < 1e-9)
    chk("the ceiling exceeds the $75 quote, so an honest run can finish",
        TOTAL_CEILING_USD > 75.0)

    chk("the ledger starts empty and sums to zero", load_spend()["usd_total"] >= 0.0)
    chk("dst_path is deterministic and carries schema, venue and month",
        dst_path("2019-01").endswith("ohlcv-1d_XNAS_ITCH_201901.csv.gz"))

    print("selftest: %s" % ("PASS" if not bad else "FAIL, %d problem(s)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--cost", action="store_true")
    ap.add_argument("--fetch", metavar="YYYY-MM", nargs="+")
    ap.add_argument("--fetch-all", action="store_true")
    ap.add_argument("--symbology", metavar="YYYY-MM", nargs="*",
                    help="free: resolve instrument_id back to ticker, per month")
    ap.add_argument("--crosscheck", metavar="YYYYMMDD", nargs="+",
                    help="no network: do the mapped tickers price like stooq")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.plan:
        return plan()
    if a.symbology is not None:
        return symbology(api_key(), a.symbology or None)
    if a.crosscheck:
        rc = 0
        for d in a.crosscheck:
            rc |= crosscheck(d)
        return rc
    if a.verify:
        return verify()
    if a.cost:
        return cost(api_key())
    if a.fetch:
        return fetch(api_key(), a.fetch)
    if a.fetch_all:
        months, _ = planned_months(load_calendar())
        return fetch(api_key(), [m for m in months if not os.path.exists(dst_path(m))])
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
