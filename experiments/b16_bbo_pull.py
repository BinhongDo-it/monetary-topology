"""Section 31 carrier: buy bbo-1s quotes, one arm at a time.

WHY ONE ARM

Gate two of the design cannot be computed yet. It needs Z90 * se_lower / band,
and the se lower bound needs the observed dispersion of rho, which needs quotes.
So the registered order (D21) is: buy the smallest arm, e5 with N=63, compute se,
run gate two, and only then decide about the other five. Gate two failing means
the other five are not bought. This file refuses any arm but e5 unless --arm is
given explicitly, and it prints why.

WHAT IS BOUGHT

    datasets  XNAS.ITCH and ARCX.PILLAR      the registered venue pair
    schema    bbo-1s
    symbols   the explicit per-event list from results/b16_universe.json
    dates     the 29+29 trading-day buy window, CLIPPED to the window at both
              month edges. Whole months would bill about 84 days to get 58.

Because the symbol list is explicit and small (63 to 166, the API allows 2000),
map_symbols=true is legal here and the CSV carries raw_symbol directly. That is
the whole reason the daily-bar puller needed a symbology side-file and this one
does not. A selftest keeps the two facts welded: map_symbols may be true only
when the symbol list is explicit.

MONEY

Shares one ledger with b16_px_pull.py, results/b16_px_spend.json, so the
circuit breaker counts every dollar the station has spent, not this file's share.
The registered stop rule is the design's own: quote the batch free, compare with
the extrapolation, and stop if they differ by more than 30 percent. There is no
fitted ceiling anywhere in this file.

    python experiments/b16_bbo_pull.py --selftest         no network
    python experiments/b16_bbo_pull.py --plan             no network
    python experiments/b16_bbo_pull.py --cost             free, quotes every batch
    python experiments/b16_bbo_pull.py --fetch            buys e5, both venues
    python experiments/b16_bbo_pull.py --fetch --accept-quote
    python experiments/b16_bbo_pull.py --verify           no network
"""
import argparse
import ast
import base64
import datetime
import gzip
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "b16_bbo")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
UNIVERSE = os.path.join(RESULTS, "b16_universe.json")
#: One ledger for the whole station. b16_px_pull.py writes the same file.
SPEND = os.path.join(RESULTS, "b16_px_spend.json")
PLANFILE = os.path.join(RESULTS, "b16_bbo_plan.json")

API = "https://hist.databento.com/v0"
VENUES = ("XNAS.ITCH", "ARCX.PILLAR")
SCHEMA = "bbo-1s"
#: Legal here and only here: the symbol list is explicit. ALL_SYMBOLS plus
#: map_symbols is refused by the API, which is what forced the symbology
#: side-file in the daily-bar puller. selftest 5 keeps this honest.
MAP_SYMBOLS = "true"

BUY_DAYS_EACH_SIDE = 29
#: Design cell 4. Boundary day belongs to the post window.
EVENT_BOUNDARIES = {2: "2019-04-12", 3: "2021-02-23", 4: "2022-05-12",
                    5: "2023-02-23", 6: "2024-05-20", 7: "2025-05-13",
                    8: "2026-04-02"}
SCORED = (3, 4, 5, 6, 7, 8)
#: D21. e5 is the smallest scored arm, so it is the cheapest way to learn se.
FIRST_ARM = 5

#: Design cell 2, calibrated off B14's 2018 bbo-1s pull. Dollars per symbol per
#: 21-trading-day month. It is an extrapolation, not a price: its only job is to
#: give the free quote something registered to be compared against.
UNIT_USD_PER_SYMBOL_MONTH = 0.0201
TRADING_DAYS_PER_MONTH = 21.0
#: Design section 10.3 step 2, registered before any quote was seen.
QUOTE_DEVIATION_STOP = 0.30
#: The station's circuit breaker, shared with b16_px_pull.py. Per round, not
#: per project: tripping it means stop and re-check before continuing, not that
#: the station is over.
TOTAL_CEILING_USD = 80.00
#: Refuse to start a batch that cannot fit on disk with room to spare.
DISK_HEADROOM = 3.0
GZIP_LEVEL = 6

FREE_ENDPOINTS = ("metadata.get_cost", "metadata.get_billable_size",
                  "metadata.get_dataset_range", "metadata.list_datasets")
PAID_ENDPOINTS = ("timeseries.get_range",)


# ---------------------------------------------------------------- plumbing

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
    return urllib.request.urlopen(req, timeout=3600)


def call(endpoint, params, key):
    try:
        with open_request(endpoint, params, key) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:400]}


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


def next_day(d):
    dt = datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])) + datetime.timedelta(days=1)
    return dt.strftime("%Y%m%d")


def iso(d):
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:])


# ---------------------------------------------------------------- the plan

def buy_window(boundary, days, each=BUY_DAYS_EACH_SIDE):
    """(first, last) yyyymmdd. The boundary day is the first day of the post side."""
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]
    if len(before) < each or len(after) < each:
        return None
    return before[-each], after[each - 1]


def arm_symbols(ev):
    """The tickers for one event.

    results/b16_universe.json stores each survivor as a row
    [ticker, screen_price, corwin_schultz_spread], not as a bare string, because
    b16_screen.py keeps the two numbers the screen turned on. Only the first
    field goes into the request. A bare string is accepted too so that a
    hand-edited file does not fail here.
    """
    out = []
    for r in ev["symbols"]:
        t = r[0] if isinstance(r, (list, tuple)) else r
        if not isinstance(t, str) or not t or "," in t:
            raise SystemExit("bad ticker %r in the universe file; the symbols "
                             "parameter is comma joined and cannot carry it" % (r,))
        out.append(t)
    return out


def batches_for_arm(arm, days, uni):
    """One batch per (venue, month), date range clipped to the buy window."""
    ev = uni["events"][str(arm)]
    win = buy_window(EVENT_BOUNDARIES[arm], days)
    if win is None:
        raise SystemExit("arm e%d has no full 29+29 window in the calendar" % arm)
    lo, hi = win
    inwin = [d for d in days if lo <= d <= hi]
    bymonth = {}
    for d in inwin:
        bymonth.setdefault(d[:6], []).append(d)
    out = []
    for venue in VENUES:
        for mm in sorted(bymonth):
            dd = bymonth[mm]
            out.append({
                "arm": arm, "venue": venue, "month": "%s-%s" % (mm[:4], mm[4:]),
                "start": iso(dd[0]), "end": iso(next_day(dd[-1])),
                "n_days": len(dd), "n_symbols": ev["n_symbols"],
                "symbols": arm_symbols(ev),
                "extrap_usd": round(ev["n_symbols"] * len(dd) / TRADING_DAYS_PER_MONTH
                                    * UNIT_USD_PER_SYMBOL_MONTH, 4),
            })
    return out, win, len(inwin)


def batch_params(b):
    return {"dataset": b["venue"], "symbols": ",".join(b["symbols"]),
            "schema": SCHEMA, "start": b["start"], "end": b["end"],
            "stype_in": "raw_symbol", "mode": "historical"}


def dst_path(b):
    return os.path.join(RAW, "%s_%s_e%d_%s.csv.gz"
                        % (SCHEMA, b["venue"].replace(".", "_"), b["arm"],
                           b["month"].replace("-", "")))


# ---------------------------------------------------------------- actions

def plan(arm):
    days, uni = load_calendar(), load_universe()
    bs, win, nd = batches_for_arm(arm, days, uni)
    ev = uni["events"][str(arm)]
    print("arm e%d   boundary %s   N=%d   dr=%+.2fe-6   median M=$%.0f"
          % (arm, EVENT_BOUNDARIES[arm], ev["n_symbols"], ev["dr"] * 1e6,
             ev["median_price"]))
    print("window   %s .. %s   %d trading days (%d+%d)"
          % (iso(win[0]), iso(win[1]), nd, BUY_DAYS_EACH_SIDE, BUY_DAYS_EACH_SIDE))
    print("schema   %s   venues %s   map_symbols=%s" % (SCHEMA, " ".join(VENUES), MAP_SYMBOLS))
    print()
    tot = 0.0
    for b in bs:
        tot += b["extrap_usd"]
        print("  %-12s %s  %2d days  extrap $%6.3f  %s"
              % (b["venue"], b["month"], b["n_days"], b["extrap_usd"],
                 "ON DISK" if os.path.exists(dst_path(b)) else ""))
    print("\n  %d batches, extrapolated $%.3f for this arm" % (len(bs), tot))
    print("  ledger so far $%.4f, circuit breaker $%.2f"
          % (load_spend()["usd_total"], TOTAL_CEILING_USD))
    print("\n  the extrapolation is NOT a price. --cost quotes every batch free.")
    return 0


def cost(arm, key):
    days, uni = load_calendar(), load_universe()
    bs, _, _ = batches_for_arm(arm, days, uni)
    quoted, extrap, gbs, rows, bad = 0.0, 0.0, 0, [], []
    for b in bs:
        p = batch_params(b)
        c = call("metadata.get_cost", p, key)
        z = call("metadata.get_billable_size", p, key)
        if isinstance(c, dict):
            detail = ""
            try:
                detail = json.loads(c["body"])["detail"]["case"]
            except Exception:                                       # noqa: BLE001
                detail = str(c.get("body", ""))[:80]
            bad.append((b, c.get("http_error"), detail))
            rows.append((b, None, None))
            continue
        usd, nbytes = float(c), (0 if isinstance(z, dict) else int(z))
        quoted += usd
        extrap += b["extrap_usd"]
        gbs += nbytes
        rows.append((b, usd, nbytes))
        print("  %-12s %s  quote $%7.4f  extrap $%6.3f  %6.2f GB"
              % (b["venue"], b["month"], usd, b["extrap_usd"], nbytes / 1e9))
    for b, code, detail in bad:
        print("  %-12s %s  REFUSED http %s  %s" % (b["venue"], b["month"], code, detail))
    if extrap <= 0:
        print("\n  nothing quotable; not writing a plan file")
        return 1
    dev = quoted / extrap - 1.0
    print("\n  arm e%d   quoted $%.4f   extrapolated $%.4f   deviation %+.1f%%"
          % (arm, quoted, extrap, dev * 100))
    print("  billable %.2f GB   free on this disk %.1f GB"
          % (gbs / 1e9, shutil.disk_usage(ROOT).free / 1e9))
    print("  ledger $%.4f + $%.4f = $%.4f against the breaker $%.2f"
          % (load_spend()["usd_total"], quoted,
             load_spend()["usd_total"] + quoted, TOTAL_CEILING_USD))
    if abs(dev) > QUOTE_DEVIATION_STOP:
        print("\n  STOP registered in design 10.3 step 2: the quote is more than")
        print("  %.0f%% away from the extrapolation. Stop and re-check the design"
              % (QUOTE_DEVIATION_STOP * 100))
        print("  before buying. --fetch will refuse without --accept-quote.")
    os.makedirs(RESULTS, exist_ok=True)
    json.dump({"arm": arm, "at": datetime.datetime.now().isoformat(timespec="seconds"),
               "quoted_usd": round(quoted, 6), "extrap_usd": round(extrap, 6),
               "deviation": round(dev, 6), "billable_bytes": gbs,
               "refused": len(bad), "n_batches": len(bs),
               "batches": [{"venue": b["venue"], "month": b["month"],
                            "usd": u, "bytes": n} for b, u, n in rows]},
              open(PLANFILE, "w", encoding="utf-8"), indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(PLANFILE, ROOT))
    return 0


def fetch(arm, key, accept_quote):
    days, uni = load_calendar(), load_universe()
    bs, _, _ = batches_for_arm(arm, days, uni)
    os.makedirs(RAW, exist_ok=True)
    led = load_spend()
    if not os.path.exists(PLANFILE):
        print("  no %s. Run --cost first; it is free and it is the registered"
              % os.path.relpath(PLANFILE, ROOT))
        print("  checkpoint before any money moves.")
        return 1
    pf = json.load(open(PLANFILE, encoding="utf-8"))
    if pf.get("arm") != arm:
        print("  the plan file on disk is for arm e%s, not e%d. Re-run --cost."
              % (pf.get("arm"), arm))
        return 1
    if pf.get("refused"):
        print("  REFUSED. %d of %d batches would not even quote, so the arm total"
              % (pf["refused"], pf.get("n_batches", 0)))
        print("  in the plan file is a partial number and the deviation test is")
        print("  meaningless. Fix the refusals first; --cost prints the http case.")
        return 1
    if abs(pf["deviation"]) > QUOTE_DEVIATION_STOP and not accept_quote:
        print("  REFUSED. The quote is %+.1f%% off the extrapolation, past the"
              % (pf["deviation"] * 100))
        print("  registered %.0f%% stop: $%.4f quoted against $%.4f extrapolated."
              % (QUOTE_DEVIATION_STOP * 100, pf["quoted_usd"], pf["extrap_usd"]))
        print("  Re-check the design, then re-run with --accept-quote.")
        return 1
    for b in bs:
        dst = dst_path(b)
        if os.path.exists(dst):
            print("  SKIP  %-12s %s  already on disk, %.2f GB"
                  % (b["venue"], b["month"], os.path.getsize(dst) / 1e9))
            continue
        p = batch_params(b)
        c = call("metadata.get_cost", p, key)
        if isinstance(c, dict):
            print("  STOP  %-12s %s  quote failed http %s  %s"
                  % (b["venue"], b["month"], c.get("http_error"),
                     str(c.get("body", ""))[:200]))
            return 1
        usd = float(c)
        z = call("metadata.get_billable_size", p, key)
        need = (0 if isinstance(z, dict) else int(z)) * DISK_HEADROOM
        free = shutil.disk_usage(ROOT).free
        if need and free < need:
            print("  STOP  %-12s %s  needs about %.1f GB free (%.0fx billable),"
                  % (b["venue"], b["month"], need / 1e9, DISK_HEADROOM))
            print("        this disk has %.1f GB. Nothing was bought." % (free / 1e9))
            return 1
        if led["usd_total"] + usd > TOTAL_CEILING_USD:
            print("  STOP  %-12s %s  $%.4f takes the running total to $%.4f,"
                  % (b["venue"], b["month"], usd, led["usd_total"] + usd))
            print("        past the circuit breaker $%.2f. This is a per-round"
                  % TOTAL_CEILING_USD)
            print("        stop, not a project ceiling: re-check before going on.")
            return 1
        print("  BUY   %-12s %s  quote $%.4f  (running $%.4f)"
              % (b["venue"], b["month"], usd, led["usd_total"] + usd))
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
                    chunk = r.read(1 << 22)
                    if not chunk:
                        break
                    got += len(chunk)
                    out.write(chunk)
        except urllib.error.HTTPError as e:
            print("  STOP  %-12s %s  body http %s  %s"
                  % (b["venue"], b["month"], e.code,
                     e.read().decode("utf-8", "replace")[:300]))
            print("        nothing added to the ledger; the .part stays where it is")
            print("        and the next attempt parks it aside.")
            return 1
        os.replace(tmp, dst)
        secs = (datetime.datetime.now() - t0).total_seconds()
        print("        %.2f GB csv -> %.2f GB gz in %.0f s"
              % (got / 1e9, os.path.getsize(dst) / 1e9, secs))
        led["batches"].append(dict(month="e%d %s %s" % (arm, b["venue"], b["month"]),
                                   usd=usd, csv_bytes=got,
                                   gz_bytes=os.path.getsize(dst),
                                   at=datetime.datetime.now().isoformat(timespec="seconds")))
        save_spend(led)
    print("\n  ledger total $%.4f over %d batches" % (led["usd_total"], len(led["batches"])))
    print("  next: gate two. Nothing else is bought until it is computed.")
    return 0


def verify(arm):
    days, uni = load_calendar(), load_universe()
    bs, _, nd = batches_for_arm(arm, days, uni)
    ok, heads = True, {}
    for b in bs:
        d = dst_path(b)
        if not os.path.exists(d):
            print("  MISSING %-12s %s" % (b["venue"], b["month"]))
            ok = False
            continue
        with gzip.open(d, "rt", encoding="utf-8", errors="replace") as fh:
            head = fh.readline().strip()
        heads[(b["venue"], b["month"])] = head
        print("  %-12s %s  %.2f GB  %d cols"
              % (b["venue"], b["month"], os.path.getsize(d) / 1e9,
                 head.count(",") + 1))
    print("\n  arm e%d: %d batches, %d trading days expected" % (arm, len(bs), nd))
    #: Gate two condition 1: every (event, venue, month) batch must have a
    #: bit-identical field layout. Checked here, not by eye.
    distinct = sorted(set(heads.values()))
    if len(distinct) <= 1:
        print("  gate two condition 1: PASS, one field layout across %d batches"
              % len(heads))
        if distinct:
            #: Print the whole header, never a slice of it. A truncated print here
            #: showed 14 of the 17 columns while the count beside it said 17, and
            #: the three it hid included `symbol`, the one column the whole
            #: map_symbols argument was about. The count was right and the object
            #: was wrong, which is the failure this project keeps paying for.
            for i, c in enumerate(distinct[0].split(",")):
                print("    %2d  %s" % (i, c))
    else:
        ok = False
        print("  gate two condition 1: FAIL, %d distinct field layouts" % len(distinct))
        for h in distinct:
            who = [k for k, v in heads.items() if v == h]
            print("    %-70s  %s" % (h[:70], " ".join("%s/%s" % k for k in who)))
    return 0 if ok else 1


# ---------------------------------------------------------------- selftest

def _endpoints_in_source():
    """AST walk, not a substring search. The house pitfall note says a check of
    the form `"x" not in src` fails on its own text; that was caught eight times
    in an earlier round, so the whitelist is built from real call sites."""
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
        if name in ("call", "open_request") and node.args:
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                seen.add(a.value)
    return seen


def _module_tree():
    return ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())


def _all_symbols_literal_present():
    """True if the ALL_SYMBOLS wildcard is a string constant anywhere in this
    module. Built by AST so that this check's own text cannot trip it, which is
    the failure mode the house note warns about."""
    wild = "ALL" + "_SYMBOLS"
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Constant) and node.value == wild:
            return True
    return False


def _park_renames():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == "park":
            calls = {getattr(c.func, "attr", "") for c in ast.walk(node)
                     if isinstance(c, ast.Call)}
            return "rename" in calls
    return False


def _deleters_in_source():
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            attr = getattr(f, "attr", None)
            if attr in ("remove", "unlink", "rmtree", "rmdir"):
                bad.add(attr)
    return bad


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    days = load_calendar() if os.path.exists(CAL_CACHE) else None
    uni = load_universe() if os.path.exists(UNIVERSE) else None

    chk("1  first arm is e5, the smallest scored arm", FIRST_ARM == 5)
    if uni:
        ns = {a: uni["events"][str(a)]["n_symbols"] for a in SCORED}
        chk("2  e5 really is the smallest scored arm (%s)"
            % " ".join("e%d=%d" % (a, ns[a]) for a in SCORED),
            ns[FIRST_ARM] == min(ns.values()))
        chk("3  scored set matches the universe file",
            tuple(sorted(int(k) for k, v in uni["events"].items() if v["scored"])) == SCORED)
    chk("4  ledger is the station ledger, shared with the daily-bar puller",
        os.path.basename(SPEND) == "b16_px_spend.json")
    chk("5  map_symbols is true only because the symbol list is explicit;"
        " the ALL_SYMBOLS literal appears nowhere (AST walk)",
        MAP_SYMBOLS == "true" and not _all_symbols_literal_present())
    if uni:
        biggest = max(uni["events"][str(a)]["n_symbols"] for a in SCORED)
        chk("6  the largest arm (%d) is under the API's 2000-symbol limit for"
            " map_symbols" % biggest, biggest < 2000)
    chk("7  circuit breaker is the registered $80, documented as per-round",
        TOTAL_CEILING_USD == 80.00)
    chk("8  the quote stop is the registered 30 percent, not a fitted number",
        QUOTE_DEVIATION_STOP == 0.30)

    synth = ["%04d%02d%02d" % (2023, m, d) for m in (1, 2, 3, 4)
             for d in range(1, 29)]
    w = buy_window("2023-02-23", synth)
    pre = [d for d in synth if d < "20230223"]
    post = [d for d in synth if d >= "20230223"]
    chk("9  buy window is exactly 29+29 and the boundary opens the post side",
        w is not None and w[0] == pre[-29] and w[1] == post[28])
    inwin = [d for d in synth if w[0] <= d <= w[1]]
    chk("10 window holds 58 trading days, no more", len(inwin) == 58)

    if days and uni:
        bs, real_w, nd = batches_for_arm(5, days, uni)
        chk("11 e5 batches are per (venue, month), %d of them" % len(bs),
            len(bs) == len({(b["venue"], b["month"]) for b in bs}))
        chk("12 both registered venues appear",
            {b["venue"] for b in bs} == set(VENUES))
        chk("13 every batch is clipped inside the window",
            all(iso(real_w[0]) <= b["start"] and b["end"] <= iso(next_day(real_w[1]))
                for b in bs))
        per_venue = sum(b["n_days"] for b in bs if b["venue"] == VENUES[0])
        chk("14 the per-venue day count is the window, %d days" % nd, per_venue == nd)
        chk("15 the extrapolation bills clipped days, not whole months",
            per_venue == 58 and nd == 58)
        chk("16 every batch carries the arm's full symbol list",
            all(len(b["symbols"]) == b["n_symbols"] for b in bs))
        chk("16b every symbol is a bare ticker string, not a screen row",
            all(isinstance(t, str) and t and "," not in t
                for b in bs for t in b["symbols"]))
        chk("16c the joined symbols parameter round-trips to the same tickers",
            all(batch_params(b)["symbols"].split(",") == b["symbols"] for b in bs))

    eps = _endpoints_in_source()
    chk("17 the only paid endpoint used is timeseries.get_range (found %s)"
        % ",".join(sorted(eps)),
        eps.issubset(set(FREE_ENDPOINTS) | set(PAID_ENDPOINTS))
        and eps & set(PAID_ENDPOINTS) == {"timeseries.get_range"})
    chk("18 nothing in this file deletes anything (AST walk)",
        _deleters_in_source() == set())
    chk("19 park() renames rather than deletes (AST walk of its body)",
        _park_renames())

    dev_bad, dev_ok = 0.44, 0.12
    chk("20 a 44 percent deviation trips the stop, a 12 percent one does not",
        abs(dev_bad) > QUOTE_DEVIATION_STOP and abs(dev_ok) <= QUOTE_DEVIATION_STOP)
    chk("21 disk headroom is a multiple of billable size, not a fixed guess",
        DISK_HEADROOM > 1.0)

    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", type=int, default=FIRST_ARM)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--cost", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--accept-quote", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.arm not in SCORED:
        raise SystemExit("e%d is not a scored arm. Scored: %s"
                         % (a.arm, " ".join("e%d" % x for x in SCORED)))
    if a.arm != FIRST_ARM and not (a.plan or a.verify):
        print("e%d is not the first arm. D21 registers e%d first: buy it, compute"
              % (a.arm, FIRST_ARM))
        print("se, run gate two, and only then decide about the rest. Gate two")
        print("failing means the rest are not bought. If gate two has already")
        print("passed, say so and this guard comes out in one line.")
        return 1
    if a.plan:
        return plan(a.arm)
    if a.cost:
        return cost(a.arm, api_key())
    if a.fetch:
        return fetch(a.arm, api_key(), a.accept_quote)
    if a.verify:
        return verify(a.arm)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
