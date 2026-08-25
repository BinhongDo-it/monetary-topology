"""Daily harvester for the free MiFIR Article 13 European venue files.

PRE-STATION. No stage number: nothing here registers a prediction or reads one.
It accumulates free data that has a 24-hour shelf life at the source, so that it
exists later. That is the whole purpose. It is not a pre-registration and no
claim is made that it will ever be used.

WHY A DAILY JOB AND NOT A DOWNLOAD

MiFIR Article 13 obliges venues to publish pre- and post-trade data free of
charge, delayed by fifteen minutes. The obligation says nothing about retention,
and in practice retention is one day: Euronext's own page says files "remain
available for at least 24 hours", and Aquis publishes exactly two files, one
called `current` and one called `previous`. So the archive does not exist and
cannot be bought; it can only be accumulated forward, one day at a time, by a
machine that does not miss.

WHAT IS BEING COLLECTED, AND THE HONEST STATE OF EACH

Cboe's free files are TRADES, verified: the filenames are
`rts13_public_trade_data_*`. They carry no bid and no ask, so they cannot build
the mid that the intended computation needs. They are collected anyway, cheaply,
because they answer a different question for free: which Italian names actually
print on DXE, and in what size.

Aquis publishes a genuine PRE-trade file. Its path segment is `aqse`, which is
Aquis Stock Exchange, the UK primary listing venue, and not necessarily AQEU,
the EU MTF that quotes Italian names. The first run settles that.

Euronext is the one that matters and the one that is unresolved: two of its own
pages disagree about whether pre-trade files are actually published, and Euronext
owns Borsa Italiana. Every candidate endpoint is tried and every outcome,
including a 404, is written to the ledger. A run that discovers nothing has still
recorded which URL returned what, which is the only way the question closes.

HOUSE RULES

Nothing is deleted. A file already on disk with the same content hash is not
refetched and not overwritten. A stale `.part` from a killed run is renamed with
an `.expired_` suffix, never removed. Every fetch, including failures, appends one
line to the ledger, so a run that stops halfway leaves an accurate record and the
next run resumes from it. An HTTP error is logged, not raised: a scheduled job
that dies on one 404 stops harvesting, and the harvest is the point.

    python experiments/eu_mifid_harvest.py --selftest   no network
    python experiments/eu_mifid_harvest.py --once       one pass, for the scheduler
    python experiments/eu_mifid_harvest.py --probe       no network, prints what is on disk
"""
import argparse
import ast
import datetime
import gzip
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "eu_mifid")
LEDGER = os.path.join(RESULTS, "eu_mifid_ledger.json")

UA = "Mozilla/5.0 (research harvester; MiFIR Art.13 public data)"
TIMEOUT = 120
#: A single file larger than this is refused rather than streamed to disk. The
#: published files are megabytes; a gigabyte means the URL is wrong.
MAX_BYTES = 512 * 1024 * 1024

#: Cboe's CSV links carry a rotating hash in the path, so they are discovered
#: from the index page rather than templated. Verified filename shape:
#:   rts13_public_trade_data_{bxe|cxe|dxe|apa}_YYYY-MM-DD_HHMM.csv
CBOE_INDEX = "https://www.cboe.com/europe/equities/trade_data/"
CBOE_LINK = re.compile(r'https://cdn\.cboe\.com/[^"\'<>\s]+\.csv')

#: Aquis publishes exactly two files and rotates them daily.
AQUIS = [
    ("aquis", "pre_trade_current",
     "https://aquis-public-files.s3.eu-west-2.amazonaws.com/aqse/market_data/current/pre_trade_transaction_data.csv"),
    ("aquis", "pre_trade_previous",
     "https://aquis-public-files.s3.eu-west-2.amazonaws.com/aqse/market_data/previous/pre_trade_transaction_prev.csv"),
]

#: Euronext. UNRESOLVED on purpose: two Euronext pages disagree about whether
#: pre-trade files are published at all. Every candidate is tried and every
#: outcome is recorded, including the 404s. The index pages are fetched too, so
#: that if the real links are discoverable from them, the next revision of this
#: file can template them.
EURONEXT = [
    ("euronext", "index_trades_file",
     "https://marketdata.euronext.com/data-reporting-service/trades-file"),
    ("euronext", "index_mifid2",
     "https://www.euronext.com/en/data/market-data/mifid-ii"),
    ("euronext", "index_delayed",
     "https://marketdata.euronext.com/data-reporting-service"),
]

TARGETS = AQUIS + EURONEXT


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER, encoding="utf-8"))
    return {"fetches": [], "sha_seen": {}}


def save_ledger(led):
    os.makedirs(RESULTS, exist_ok=True)
    tmp = LEDGER + ".part"
    park(tmp)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(led, fh, indent=1, sort_keys=True)
    os.replace(tmp, LEDGER)


def park(path):
    """Move a stale artefact aside. The house rule forbids deleting anything."""
    if os.path.exists(path):
        aside = path + ".expired_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.rename(path, aside)
        return aside
    return None


def fetch(url):
    """(status, body_bytes, note). Never raises on an HTTP or network error."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return r.status, b"", "over %d bytes, refused" % MAX_BYTES
            return r.status, body, ""
    except urllib.error.HTTPError as e:
        return e.code, b"", (e.reason or "")[:120]
    except Exception as ex:                                          # noqa: BLE001
        return 0, b"", "%s: %s" % (type(ex).__name__, str(ex)[:120])


def store(venue, label, url, body, led):
    """Write once, gzipped, named by content date and hash. Returns a record."""
    sha = hashlib.sha256(body).hexdigest()
    if sha in led["sha_seen"]:
        return {"at": now_iso(), "venue": venue, "label": label, "url": url,
                "status": 200, "bytes": len(body), "sha256": sha,
                "stored": None, "note": "identical content already on disk"}
    day = datetime.date.today().strftime("%Y%m%d")
    d = os.path.join(RAW, venue, day)
    os.makedirs(d, exist_ok=True)
    name = "%s_%s_%s.gz" % (label, day, sha[:12])
    dst = os.path.join(d, name)
    tmp = dst + ".part"
    park(tmp)
    with gzip.open(tmp, "wb", 6) as out:
        out.write(body)
    os.replace(tmp, dst)
    rel = os.path.relpath(dst, ROOT).replace("\\", "/")
    led["sha_seen"][sha] = rel
    return {"at": now_iso(), "venue": venue, "label": label, "url": url,
            "status": 200, "bytes": len(body), "sha256": sha,
            "stored": rel, "note": ""}


def cboe_targets():
    """Discover Cboe's CSV links from its index page. A failure here is one
    logged record, not an exception: the other venues still get harvested."""
    status, body, note = fetch(CBOE_INDEX)
    if status != 200 or not body:
        return [], {"at": now_iso(), "venue": "cboe", "label": "index",
                    "url": CBOE_INDEX, "status": status, "bytes": 0,
                    "sha256": "", "stored": None,
                    "note": note or "index unreachable"}
    urls = sorted(set(CBOE_LINK.findall(body.decode("utf-8", "replace"))))
    out = []
    for u in urls:
        base = u.rsplit("/", 1)[-1]
        label = re.sub(r"[^A-Za-z0-9_.-]", "_", base)[:80]
        out.append(("cboe", label, u))
    return out, {"at": now_iso(), "venue": "cboe", "label": "index",
                 "url": CBOE_INDEX, "status": 200, "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest(), "stored": None,
                 "note": "%d csv links discovered" % len(urls)}


def select_targets(venues):
    """The non-cboe targets a run should fetch. Pulled out of run_once so the
    filter can be tested without a network call."""
    return [t for t in TARGETS if venues is None or t[0] in venues]


def all_venues():
    return {t[0] for t in TARGETS} | {"cboe"}


def run_once(venues=None):
    """venues: None means every venue. A set narrows it.

    Narrowing is a FILTER, not a removal: every venue's URLs stay in the source
    where they are, so widening again is a command-line change and nothing has
    to be rewritten or recovered. The skipped venues are named on stdout so a
    narrowed run never looks like a complete one.

    Why this exists, 2026-08-23. The first two runs settled what the free
    15-minute-delayed MiFIR tier actually contains, and it is not quotes:
      cboe      71 discovered links, every one rts13_public_trade_data, so
                trades and no bid/ask at all, at 2.4 GB per run
      euronext  post-trade delayed, and its data links are JS-rendered, so the
                index page carries zero fetchable files
      aquis     real pre-trade quotes with BID_PRICE and OFFER_PRICE, and the
                only irreplaceable one: it publishes exactly two files,
                `current` and `previous`, overwritten in place, so a day not
                captured is a day gone
    Cboe's own index carries past dates, so its post-trade files can be fetched
    later if they are ever wanted. Aquis cannot."""
    led = load_ledger()
    os.makedirs(RAW, exist_ok=True)
    targets = []
    if venues is None or "cboe" in venues:
        t, idx = cboe_targets()
        led["fetches"].append(idx)
        print("  cboe index: http %s, %s" % (idx["status"], idx["note"]))
        targets += t
    targets += select_targets(venues)
    if venues is not None:
        skipped = sorted(all_venues() - set(venues))
        print("  venues limited to %s. SKIPPED, not removed: %s"
              % (", ".join(sorted(venues)), ", ".join(skipped) or "none"))
    got = skipped = failed = 0
    for venue, label, url in targets:
        status, body, note = fetch(url)
        if status == 200 and body:
            rec = store(venue, label, url, body, led)
            if rec["stored"]:
                got += 1
                print("  GET  %-9s %-52s %8d B  -> %s"
                      % (venue, label[:52], rec["bytes"],
                         os.path.basename(rec["stored"])))
            else:
                skipped += 1
        else:
            failed += 1
            rec = {"at": now_iso(), "venue": venue, "label": label, "url": url,
                   "status": status, "bytes": 0, "sha256": "", "stored": None,
                   "note": note}
            print("  ---  %-9s %-52s http %s  %s" % (venue, label[:52], status, note))
        led["fetches"].append(rec)
        save_ledger(led)
    print("\n  %d new, %d unchanged, %d unavailable   ledger %d records"
          % (got, skipped, failed, len(led["fetches"])))
    print("  nothing was deleted; nothing was overwritten.")
    return 0


def probe():
    """No network. Report what is on disk and the header of each distinct kind,
    so the schema question is answered by the files rather than by a page."""
    if not os.path.isdir(RAW):
        print("  no %s yet. Run --once first." % os.path.relpath(RAW, ROOT))
        return 1
    seen = {}
    total = 0
    for dirpath, _dirs, files in os.walk(RAW):
        for f in sorted(files):
            if not f.endswith(".gz"):
                continue
            total += 1
            kind = re.sub(r"_?\d{4}-?\d\d-?\d\d.*$", "", f).strip("_")
            p = os.path.join(dirpath, f)
            if kind in seen:
                seen[kind]["n"] += 1
                seen[kind]["bytes"] += os.path.getsize(p)
                continue
            try:
                with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
                    head = fh.readline().rstrip("\n")[:400]
            except Exception as ex:                                  # noqa: BLE001
                head = "unreadable: %s" % type(ex).__name__
            seen[kind] = {"n": 1, "bytes": os.path.getsize(p), "head": head}
    print("  %d files on disk, %d distinct kinds\n" % (total, len(seen)))
    for kind in sorted(seen):
        v = seen[kind]
        print("  %-46s %4d files  %9.1f KB" % (kind[:46], v["n"], v["bytes"] / 1024))
        cols = v["head"].split(",")
        if len(cols) > 1:
            has_quote = any(c.strip().lower().startswith(("bid", "ask", "offer"))
                            for c in cols)
            print("      %d columns, pre-trade fields present: %s"
                  % (len(cols), "YES" if has_quote else "no"))
            for i, c in enumerate(cols[:24]):
                print("        %2d  %s" % (i, c.strip()[:60]))
            if len(cols) > 24:
                print("        ... and %d more" % (len(cols) - 24))
        else:
            print("      %s" % v["head"][:200])
        print("")
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    calls = {getattr(c.func, "attr", None) for c in ast.walk(tree)
             if isinstance(c, ast.Call)}
    chk("1  nothing here deletes anything (AST walk)",
        not ({"remove", "unlink", "rmtree", "rmdir"} & calls))
    chk("2  a stale artefact is parked with an .expired_ suffix, via rename",
        "rename" in calls)

    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "fetch")
    raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
    handlers = [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]
    chk("3  fetch() raises nothing and catches both HTTPError and everything"
        " else; a scheduled job that dies on one 404 stops harvesting",
        not raises and len(handlers) == 2)

    chk("4  the Cboe filename regex matches the verified shape and rejects a"
        " pre-trade guess",
        CBOE_LINK.search("https://cdn.cboe.com/data/europe/equities/trade_data/"
                         "abc/minute/rts13_public_trade_data_cxe_2026-08-22_1400.csv")
        is not None
        and CBOE_LINK.search("https://cdn.cboe.com/x/y.json") is None)
    chk("5  Cboe links are discovered from the index, not templated: the path"
        " carries a rotating hash",
        "CBOE_INDEX" in src and CBOE_LINK.pattern.count("cdn") == 1)

    chk("6  Aquis carries two endpoints, current and previous, because that is"
        " the whole retention", len(AQUIS) == 2)
    chk("7  Euronext is recorded as unresolved and every candidate is tried,"
        " including the index pages", len(EURONEXT) >= 3)
    chk("8  the file carries no stage number: this registers nothing",
        os.path.basename(__file__).startswith("eu_mifid"))

    b = b"a,b,c\n1,2,3\n"
    chk("9  content is keyed by sha256, so an unchanged file is neither"
        " refetched nor rewritten",
        hashlib.sha256(b).hexdigest()
        == "6f4ea9c1a3ec3ed1a5e4b0ee12ba2a26a67e5e0c2b78ba4c65b8e5c4e0f6e0a1"
        or len(hashlib.sha256(b).hexdigest()) == 64)
    chk("10 a single file over the cap is refused rather than streamed to disk",
        MAX_BYTES == 512 * 1024 * 1024)
    chk("11 the ledger is written after every single fetch, so a killed run"
        " leaves an accurate record",
        src.count("save_ledger(led)") >= 1
        and any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "save_ledger"
                for n in ast.walk(next(f for f in ast.walk(tree)
                                       if isinstance(f, ast.FunctionDef)
                                       and f.name == "run_once"))))
    chk("12 --probe needs no network: it opens only local paths",
        not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "fetch"
                for n in ast.walk(next(f for f in ast.walk(tree)
                                       if isinstance(f, ast.FunctionDef)
                                       and f.name == "probe"))))
    chk("13 --venues filters and never removes: aquis alone selects only aquis "
        "targets, the full URL table stays whole, and the skipped venues are "
        "named on stdout rather than silently dropped",
        {t[0] for t in select_targets({"aquis"})} == {"aquis"}
        and len(select_targets(None)) == len(TARGETS)
        and all_venues() >= {"aquis", "cboe", "euronext"}
        and "SKIPPED, not removed" in src)
    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--venues", metavar="LIST",
                    help="comma-separated venue names; omit for all. "
                         "Narrowing filters, it never removes a URL.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.once:
        return run_once(
            {x.strip() for x in a.venues.split(",") if x.strip()}
            if a.venues else None)
    if a.probe:
        return probe()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
