"""Fetch 2016-04/05 daily closes for the leg B symbol set.

B14_A18 clause 2 registered the slice B bin variable as 5c / P_2016. B14_A18 supplement 1
substituted the 2016 median WA_BBO_Spd for it, on the ground that the Appendix B
carrier holds no price field. That ground is correct and the conclusion was
premature: 2016 daily closes are freely published and were obtainable all along.

So this fetches the REGISTERED variable. The substitute stays on record; slice B
now reports both, and where they disagree the registered one governs.

Checked before writing this: TSPilotChanges20181001.txt records zero ticker
changes touching the 108, so the 2016 ticker equals the 2018 ticker for every
one of them. That is the canon lesson applied before the fetch rather than after.

Sources, in order. Both are free and neither needs a key.
    stooq.com     daily CSV, one request per symbol
    stooq with a .us suffix is the US listing

Nothing is deleted. A symbol already in the cache is not refetched.

Usage
    python experiments/b14_legb_price2016.py --selftest
    python experiments/b14_legb_price2016.py --fetch
    python experiments/b14_legb_price2016.py --report
"""
import argparse
import ast
import json
import os
import re
import sys
import time
import urllib.error
import zipfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SYMS_FILE = os.path.join(ROOT, "results", "b14_legb_symbols.json")
RAW = os.path.join(ROOT, "data", "raw", "b14_legb_px2016")
OUT = os.path.join(ROOT, "results", "b14_legb_price2016.json")

#: B14_A17 clause 6: the split window is 2016-04/05, which predates the pilot's
#: 2016-10-03 effective date by five months.
D1, D2 = "20160401", "20160531"
#: Several free sources, tried in order per symbol. The first attempt used one
#: stooq URL form and every symbol came back 404, so the form is not assumed any
#: more: --probe hits all of them with one symbol and prints what each returns.
#: Each entry is (name, url template taking the lowercase symbol, parser name).
SOURCES = [
    ("stooq_dated",
     "https://stooq.com/q/d/l/?s=%s.us&d1=" + D1 + "&d2=" + D2 + "&i=d", "csv"),
    ("stooq_plain", "https://stooq.com/q/d/l/?s=%s.us&i=d", "csv"),
    ("stooq_nosuffix", "https://stooq.com/q/d/l/?s=%s&i=d", "csv"),
    ("yahoo_v8", "https://query1.finance.yahoo.com/v8/finance/chart/%s"
                 "?period1=1459468800&period2=1464825600&interval=1d", "yahoo"),
    ("yahoo_v8_q2", "https://query2.finance.yahoo.com/v8/finance/chart/%s"
                    "?period1=1459468800&period2=1464825600&interval=1d", "yahoo"),
]
UA = "Mozilla/5.0 (compatible; research/1.0)"
PAUSE_SECONDS = 0.4


def symbols():
    d = json.load(open(SYMS_FILE, encoding="utf-8"))
    return sorted({s for v in d["symbols"].values() for s in v})


def cache_path(sym):
    return os.path.join(RAW, "%s.csv" % sym)


#: stooq blocks scripted per-symbol requests (200 with a noindex HTML page) and
#: yahoo will not serve delisted tickers (404, "symbol may be delisted"), and a
#: large share of these 108 are delisted. stooq does publish a bulk historical
#: archive covering delisted US names, which is one browser download rather than
#: 108 scripted requests, so the anti-bot path is not walked at all.
STOOQ_BULK_PAGE = "https://stooq.com/db/h/"
#: stooq's bulk text rows: TICKER,PER,DATE,TIME,OPEN,HIGH,LOW,CLOSE,VOL,OPENINT
BULK_HEAD = "<TICKER>"


def parse_bulk(text):
    """One stooq bulk .txt member. Returns closes inside the window, or None."""
    lines = [x for x in text.splitlines() if x.strip()]
    if len(lines) < 2:
        return None
    head = [c.strip().strip("<>").lower() for c in lines[0].split(",")]
    if "close" not in head or "date" not in head:
        return None
    ic, id_ = head.index("close"), head.index("date")
    out = []
    for line in lines[1:]:
        p = line.split(",")
        if len(p) <= max(ic, id_):
            continue
        d = p[id_].strip().replace("-", "")
        if not (D1 <= d <= D2):
            continue
        try:
            v = float(p[ic])
        except ValueError:
            continue
        if v > 0:
            out.append(v)
    return out or None


def zip_members(path):
    """symbol -> member name, for every member that looks like <sym>.us.txt."""
    idx = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            base = n.rsplit("/", 1)[-1].lower()
            if not base.endswith(".txt"):
                continue
            stem = base[:-4]
            if stem.endswith(".us"):
                stem = stem[:-3]
            idx.setdefault(stem.upper(), []).append(n)
    return idx


def list_zip(path):
    """Inspect the archive before trusting it: layout, member count, coverage."""
    syms = symbols()
    idx = zip_members(path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    dirs = {}
    for n in names:
        d = n.rsplit("/", 1)[0] if "/" in n else "."
        dirs[d] = dirs.get(d, 0) + 1
    print("archive %s" % os.path.relpath(path, ROOT))
    print("  members %d, distinct symbol stems %d" % (len(names), len(idx)))
    print("  top directories by member count:")
    for d, c in sorted(dirs.items(), key=lambda kv: -kv[1])[:12]:
        print("    %-58s %6d" % (d[:58], c))
    hit = [s for s in syms if s in idx]
    print("\n  of the registered 108: %d present, %d absent" % (len(hit), len(syms) - len(hit)))
    miss = [s for s in syms if s not in idx]
    if miss:
        print("  absent, named not silently dropped: %s" % " ".join(miss))
    dup = {s: idx[s] for s in hit if len(idx[s]) > 1}
    if dup:
        print("  symbols appearing in more than one member (must be resolved, not "
              "picked at random): %d" % len(dup))
        for s in list(dup)[:5]:
            print("    %-6s %s" % (s, "  ".join(dup[s])))
    return 0


def from_zip(path):
    syms = symbols()
    idx = zip_members(path)
    os.makedirs(RAW, exist_ok=True)
    got = miss = empty = 0
    ambiguous = []
    with zipfile.ZipFile(path) as z:
        for s in syms:
            members = idx.get(s)
            if not members:
                miss += 1
                continue
            if len(members) > 1:
                # Never pick one at random. Keep the member whose window parses,
                # and if more than one does, report it and take none.
                ok = [m for m in members
                      if parse_bulk(z.read(m).decode("utf-8", "replace"))]
                if len(ok) != 1:
                    ambiguous.append((s, members))
                    continue
                members = ok
            text = z.read(members[0]).decode("utf-8", "replace")
            if parse_bulk(text) is None:
                empty += 1
                continue
            with open(cache_path(s), "w", encoding="utf-8") as fh:
                fh.write(text)
            with open(cache_path(s) + ".src", "w", encoding="utf-8") as fh:
                fh.write("stooq_bulk\nbulk\n")
            got += 1
    print("  extracted %d, absent from the archive %d, no rows in the window %d"
          % (got, miss, empty))
    if ambiguous:
        print("  AMBIGUOUS, none taken: %s"
              % " ".join("%s(%d)" % (s, len(m)) for s, m in ambiguous))
    return report()


def parse_yahoo(text):
    """Yahoo's chart JSON. Returns closes inside the window, or None."""
    try:
        d = json.loads(text)
    except ValueError:
        return None
    try:
        r = d["chart"]["result"][0]
        ts = r["timestamp"]
        cl = r["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        return None
    out = []
    for t, c in zip(ts, cl):
        if c is None:
            continue
        day = time.strftime("%Y%m%d", time.gmtime(t))
        if D1 <= day <= D2 and c > 0:
            out.append(float(c))
    return out or None


def parse(text):
    """Return the list of daily closes in the window, or None if unusable."""
    lines = [x for x in text.strip().splitlines() if x.strip()]
    if len(lines) < 2:
        return None
    head = [c.strip().lower() for c in lines[0].split(",")]
    if "close" not in head or "date" not in head:
        return None
    ic, id_ = head.index("close"), head.index("date")
    out = []
    for line in lines[1:]:
        p = line.split(",")
        if len(p) <= max(ic, id_):
            continue
        d = p[id_].replace("-", "")
        if not (D1 <= d <= D2):
            continue
        try:
            v = float(p[ic])
        except ValueError:
            continue
        if v > 0:
            out.append(v)
    return out or None


def get(url):
    """One request. Returns (status, body) and never raises on an HTTP error."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return None, str(e)


def probe(sym="AAN"):
    """Hit every source with one symbol and print exactly what came back."""
    print("probing %d sources with %s; nothing is cached and nothing is judged\n"
          % (len(SOURCES), sym))
    for name, tmpl, kind in SOURCES:
        url = tmpl % (sym.lower() if "yahoo" not in name else sym)
        st, body = get(url)
        vals = (parse_yahoo(body) if kind == "yahoo" else parse(body)) if body else None
        print("  %-16s status %-6s bytes %-7s parsed %s"
              % (name, st, len(body) if body else 0,
                 ("%d closes, first %.2f" % (len(vals), vals[0])) if vals else "NONE"))
        print("      %s" % url)
        print("      %r" % (body[:110] if body else ""))
        time.sleep(PAUSE_SECONDS)
    print("\n  pick the first source that parsed, then run --fetch")
    return 0


def try_all(sym):
    """Return (body, source_name) from the first source that parses."""
    for name, tmpl, kind in SOURCES:
        url = tmpl % (sym.lower() if "yahoo" not in name else sym)
        st, body = get(url)
        if not body:
            continue
        vals = parse_yahoo(body) if kind == "yahoo" else parse(body)
        if vals:
            return body, name, kind
        time.sleep(PAUSE_SECONDS)
    return None, None, None


def fetch():
    os.makedirs(RAW, exist_ok=True)
    syms = symbols()
    got = skipped = failed = 0
    used = {}
    for k, s in enumerate(syms):
        p = cache_path(s)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            skipped += 1
            continue
        body, name, kind = try_all(s)
        if body is None:
            print("  %-6s no source returned a usable response" % s)
            failed += 1
            time.sleep(PAUSE_SECONDS)
            continue
        used[name] = used.get(name, 0) + 1
        with open(p + ".src", "w", encoding="utf-8") as fh:
            fh.write(name + "\n" + kind + "\n")
        tmp = p + ".part"
        if os.path.exists(tmp):
            os.rename(tmp, tmp + ".expired_" + time.strftime("%Y%m%d_%H%M%S"))
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.rename(tmp, p)
        got += 1
        if (k + 1) % 20 == 0:
            print("  %d/%d" % (k + 1, len(syms)))
        time.sleep(PAUSE_SECONDS)
    print("\n  fetched %d, already cached %d, failed %d, of %d"
          % (got, skipped, failed, len(syms)))
    if used:
        print("  sources that answered: %s"
              % "  ".join("%s:%d" % kv for kv in sorted(used.items())))
    return report()


def report():
    syms = symbols()
    med, missing = {}, []
    for s in syms:
        p = cache_path(s)
        if not os.path.exists(p):
            missing.append(s)
            continue
        kind = "csv"
        if os.path.exists(p + ".src"):
            parts = open(p + ".src", encoding="utf-8").read().split("\n")
            if len(parts) > 1:
                kind = parts[1].strip() or "csv"
        raw = open(p, encoding="utf-8").read()
        v = (parse_yahoo(raw) if kind == "yahoo"
             else parse_bulk(raw) if kind == "bulk" else parse(raw))
        if not v:
            missing.append(s)
            continue
        v = sorted(v)
        n = len(v)
        med[s] = round((v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2), 4)
    json.dump(med, open(OUT, "w"), indent=2, sort_keys=True)
    vals = sorted(med.values())
    print("  symbols with a 2016-04/05 median close: %d of %d" % (len(med), len(syms)))
    if missing:
        print("  MISSING (%d), named not silently dropped: %s"
              % (len(missing), " ".join(missing)))
    if vals:
        print("  median close $%.2f .. $%.2f, median of medians $%.2f"
              % (vals[0], vals[-1], vals[len(vals) // 2]))
        print("  relative tick 5c/P: %.5f .. %.5f"
              % (0.05 / vals[-1], 0.05 / vals[0]))
        print("  symbols under $2 in 2016: %d" % sum(1 for v in vals if v < 2))
    print("  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the window is B14_A17 clause 6's 2016-04/05, before the 2016-10-03 effective date",
        D1 == "20160401" and D2 == "20160531" and D2 < "20161003")
    if os.path.exists(SYMS_FILE):
        chk("the symbol set is the registered 108", len(symbols()) == 108)
    good = parse("Date,Open,High,Low,Close,Volume\n2016-04-04,1,2,0.5,25.5,10\n"
                 "2016-05-02,1,2,0.5,26.5,10\n2016-09-01,1,2,0.5,99,10\n")
    chk("the parser keeps only dates inside the window: " + str(good), good == [25.5, 26.5])
    chk("a response with no close column is refused, not cached as zero",
        parse("Date,Volume\n2016-04-04,10\n") is None)
    chk("an empty response is refused", parse("") is None)
    chk("more than one source is configured, since the first one 404'd on every "
        "symbol", len(SOURCES) >= 3)
    y = parse_yahoo(json.dumps({"chart": {"result": [{"timestamp": [1459771200, 1472731200],
        "indicators": {"quote": [{"close": [25.5, 99.0]}]}}]}}))
    chk("the yahoo parser also windows on the dates: " + str(y), y == [25.5])
    chk("a yahoo error payload is refused",
        parse_yahoo(json.dumps({"chart": {"result": None, "error": "x"}})) is None)
    b = parse_bulk("<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\n"
                   "AAN.US,D,20160404,,1,2,0.5,25.5,10,0\n"
                   "AAN.US,D,20160502,,1,2,0.5,26.5,10,0\n"
                   "AAN.US,D,20160901,,1,2,0.5,99,10,0\n")
    chk("the bulk parser reads stooq's angle-bracket header and windows on the "
        "dates: " + str(b), b == [25.5, 26.5])
    chk("a bulk member with no close column is refused",
        parse_bulk("<TICKER>,<DATE>\nAAN.US,20160404\n") is None)
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("shutil", "rmtree")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)
    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    chk("no process-spawning module is imported", not (imported & {"subprocess", "pty"}))
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", nargs="?", const="AAN", metavar="SYMBOL",
                    help="hit every source with one symbol and print the responses")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--list-zip", metavar="PATH",
                    help="inspect a stooq bulk archive without extracting anything")
    ap.add_argument("--from-zip", metavar="PATH",
                    help="extract the 108 from a stooq bulk archive, no network")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.probe:
        return probe(a.probe)
    if a.fetch:
        return fetch()
    if a.list_zip:
        return list_zip(a.list_zip)
    if a.from_zip:
        return from_zip(a.from_zip)
    if a.report:
        return report()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
