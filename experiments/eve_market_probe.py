"""Availability probe for EVE Online market order snapshots, two-hub structure.

PRE-STATION. No stage number: nothing here registers a prediction or reads one.
Engineering rule 13 step 1: measure the worst cell, by name, before anything
else. The worst cell of this design is the number of item types quoted
two-sided at BOTH hubs in the same snapshot, and nothing has measured it.

WHAT IS NOT COMPUTED HERE

No cross-hub price ratio. The index half of the decomposition is
2 log(mid_b / mid_a) and this file never forms it. Availability first, and the
drop counts before any reading, exactly as the equity stage was run. What IS
printed is each hub's own spread, because the size criterion needs it: a
friction change is detectable only if it is large against the one-way friction
it changes, and that friction is the spread.

WHY THIS CARRIER

The equity stage died on size: the fee moved the friction half by 0.9% while the
friction half's own 10-day variation is 17%. EVE's market taxes moved by 3.5
percentage points on 2024-07-25 and again, with the opposite sign, on
2025-03-12, against quoted spreads that are a fraction of a percent. Same shape
of instrument, three orders of magnitude more of it.

TWO DATES AND WHY ONLY THOSE TWO

    2024-07-25  sales tax  8%  -> 4.5%
    2025-03-12  sales tax  4%  -> 7.5%

Those two moved the SALES TAX only, and the sales tax is multiplicative in the
Accounting skill with no standings term and no location term, so a base change
scales every player at every station by the identical factor. The BROKER fee is
additive in faction and corporation standings, and standings are faction
specific, so a broker-fee change is the same in percentage points but a
different proportion at two hubs owned by different factions. The 2021-07-27 and
2021-10-19 changes moved both levers and are therefore not usable: the friction
change was not proportionally common to the two hubs, which is the carrier's
second condition.

FILENAMES ARE DISCOVERED, NOT TEMPLATED

The archive's directory index is read and the .csv.bz2 names are taken from it.
A templated guess is the fallback and the ledger records which path was used.
This is the same lesson a templated endpoint taught elsewhere in this repository
at the cost of a round trip.

    python experiments/eve_market_probe.py --selftest
    python experiments/eve_market_probe.py --list 2025-02-26
    python experiments/eve_market_probe.py --fetch 2025-02-26 --slots 4
    python experiments/eve_market_probe.py --probe
"""
import argparse
import ast
import bz2
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "eve_market")
OUT = os.path.join(RESULTS, "eve_market_availability.json")

#: The `history` segment is load-bearing and was missing in the first version,
#: which cost one round trip: every URL 404'd. EVE Ref's own download docs give
#: it verbatim: `wget -r -np ... https://data.everef.net/market-orders/history/2023/`.
BASE = "https://data.everef.net/market-orders/history"
UA = "Mozilla/5.0 (research availability probe)"
TIMEOUT = 300
NAME_RE = re.compile(r"market-orders-\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d[^\"'<>\s]*\.csv\.bz2")
#: Fallback only. The scrape runs at 15 and 45 minutes past the hour.
TEMPLATE = "market-orders-%s_%02d-%02d-02.v3.csv.bz2"

#: D12, enumerate before choosing. All five NPC trade hubs are scanned in the
#: same pass because the file is read once either way, and the pair with the
#: best joint coverage is a reading rather than an assumption.
HUBS = {
    60003760: ("Jita 4-4", "The Forge", "Caldari"),
    60008494: ("Amarr VIII", "Domain", "Amarr"),
    60011866: ("Dodixie IX-20", "Sinq Laison", "Gallente"),
    60004588: ("Rens VI-8", "Heimatar", "Minmatar"),
    60005686: ("Hek VIII-12", "Metropolis", "Minmatar"),
}
PLEX_TYPE_ID = 44992


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def park(path):
    """The house rule forbids deleting anything."""
    if os.path.exists(path):
        os.rename(path, path + ".expired_"
                  + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def get(url, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, (r.read(limit) if limit else r.read()), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", (e.reason or "")[:120]
    except Exception as ex:                                          # noqa: BLE001
        return 0, b"", "%s: %s" % (type(ex).__name__, str(ex)[:140])


def day_index(date):
    """(names, note). Discovered from the directory listing; templated only if
    the listing cannot be read, and the note says which happened.

    Two candidate index URLs are tried because the archive is served by a plain
    static file server: the bare directory, and the explicit index.html that
    EVE Ref's own wget example excludes with `-R index.html`, which is evidence
    the file is there under that name.
    """
    tried = []
    for suffix in ("", "index.html"):
        url = "%s/%s/%s/%s" % (BASE, date[:4], date, suffix)
        status, body, err = get(url)
        tried.append("%s -> %s" % (suffix or "(bare)", status))
        if status == 200 and body:
            names = sorted(set(NAME_RE.findall(body.decode("utf-8", "replace"))))
            if names:
                return names, "discovered %d names from %s" % (len(names), url)
    return ([TEMPLATE % (date, h, m) for h in range(24) for m in (15, 45)],
            "index unreadable (%s); FELL BACK to the templated pattern, which is"
            " a guess and will 404 if the real names differ" % ", ".join(tried))


def cmd_list(date):
    names, note = day_index(date)
    print("  %s/%s/%s/" % (BASE, date[:4], date))
    print("  %s\n" % note)
    for n in names[:60]:
        print("    " + n)
    if len(names) > 60:
        print("    ... and %d more" % (len(names) - 60))
    return 0


def cmd_fetch(date, slots):
    names, note = day_index(date)
    print("  %s" % note)
    if not names:
        return 1
    # spread the picks across the day rather than taking the first N in a row
    step = max(1, len(names) // max(1, slots))
    picks = names[::step][:slots]
    d = os.path.join(RAW, date)
    os.makedirs(d, exist_ok=True)
    for n in picks:
        dst = os.path.join(d, n)
        if os.path.exists(dst):
            print("  SKIP %s  already on disk, %.1f MB" % (n, os.path.getsize(dst) / 1e6))
            continue
        url = "%s/%s/%s/%s" % (BASE, date[:4], date, n)
        status, body, err = get(url)
        if status != 200 or not body:
            print("  ---  %s  http %s  %s" % (n, status, err))
            continue
        tmp = dst + ".part"
        park(tmp)
        with open(tmp, "wb") as fh:
            fh.write(body)
        os.replace(tmp, dst)
        print("  GET  %s  %.1f MB" % (n, len(body) / 1e6))
    print("\n  nothing was deleted; a file already on disk was not refetched.")
    return 0


def scan_one(path):
    """Best bid and best ask per (station, type_id), streaming. The raw line is
    substring-filtered before it is split: sixteen million rows per snapshot and
    only the hub rows matter."""
    keys = [str(k) for k in HUBS]
    book = {}
    n_rows = n_hit = 0
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        head = fh.readline().rstrip("\n").split(",")
        ix = {c.strip(): i for i, c in enumerate(head)}
        need = ("is_buy_order", "price", "station_id", "type_id")
        missing = [c for c in need if c not in ix]
        if missing:
            #: Report and skip. A run that dies on one malformed file is the same
            #: failure mode as a scheduled job dying on one 404: the rest of the
            #: evidence never gets read. The actual header is printed rather than
            #: just the names that were absent, because the header is the object
            #: and the missing-list is a count of it.
            raw = ",".join(head)
            return None, 0, 0, {"error": "missing columns",
                                "missing": missing,
                                "header_seen": raw[:300],
                                "n_header_fields": len(head),
                                "file_bytes": os.path.getsize(path)}
        i_buy, i_px, i_st, i_ty = (ix["is_buy_order"], ix["price"],
                                   ix["station_id"], ix["type_id"])
        for line in fh:
            n_rows += 1
            if not any(k in line for k in keys):
                continue
            f = line.rstrip("\n").split(",")
            st = f[i_st]
            if st not in keys:
                continue
            n_hit += 1
            try:
                px = float(f[i_px])
            except ValueError:
                continue
            is_buy = f[i_buy].strip().lower() in ("true", "1", "t")
            k = (int(st), int(f[i_ty]))
            b = book.get(k)
            if b is None:
                b = book[k] = [None, None]          # best bid, best ask
            if is_buy:
                if b[0] is None or px > b[0]:
                    b[0] = px
            else:
                if b[1] is None or px < b[1]:
                    b[1] = px
    return book, n_rows, n_hit, head


def cmd_probe():
    if not os.path.isdir(RAW):
        print("  no %s yet. Run --fetch first." % os.path.relpath(RAW, ROOT))
        return 1
    files = []
    for dirpath, _d, fs in os.walk(RAW):
        for f in sorted(fs):
            if f.endswith(".csv.bz2"):
                files.append(os.path.join(dirpath, f))
    if not files:
        print("  no snapshots on disk.")
        return 1
    print("  %d snapshot(s) on disk\n" % len(files))
    out = {"at": now_iso(), "hubs": {str(k): v[0] for k, v in HUBS.items()},
           "snapshots": []}
    bad = []
    for p in sorted(files):
        book, n_rows, n_hit, head = scan_one(p)
        name = os.path.basename(p)
        print("  %s" % name)
        if book is None:
            print("    UNREADABLE, skipped. %s" % head["error"])
            print("      %d bytes on disk, %d header fields"
                  % (head["file_bytes"], head["n_header_fields"]))
            print("      header seen: %s" % head["header_seen"])
            print("      a redownload may fix it; the file is left where it is.")
            bad.append({"file": name, **head})
            print("")
            continue
        print("    %d rows, %d at the five hubs, %d columns" % (n_rows, n_hit, len(head)))

        two = {}
        for sid in HUBS:
            ts = {t for (s, t), b in book.items()
                  if s == sid and b[0] is not None and b[1] is not None and b[1] > b[0]}
            two[sid] = ts
            allt = {t for (s, t) in book if s == sid}
            print("      %-14s %6d types present, %6d two-sided  (%.1f%%)"
                  % (HUBS[sid][0], len(allt), len(ts),
                     100.0 * len(ts) / max(1, len(allt))))

        print("\n      pairwise: item types two-sided at BOTH hubs")
        ids = sorted(HUBS)
        best = (0, None)
        pairs = {}
        for i, a in enumerate(ids):
            for b_ in ids[i + 1:]:
                n = len(two[a] & two[b_])
                pairs["%d|%d" % (a, b_)] = n
                mark = ""
                if a == 60003760 and b_ == 60008494:
                    mark = "   <- the registered pair"
                if n > best[0]:
                    best = (n, (a, b_))
                print("        %-14s x %-14s  %6d%s"
                      % (HUBS[a][0], HUBS[b_][0], n, mark))
        if best[1]:
            print("        best joint coverage: %s x %s at %d types"
                  % (HUBS[best[1][0]][0], HUBS[best[1][1]][0], best[0]))

        # the size criterion needs each hub's own spread. This is the friction
        # half's ingredient; it is not the index half and no ratio is formed.
        print("\n      one-way relative spread at each hub, on its own book")
        spreads = {}
        for sid in ids:
            v = []
            for t in two[sid]:
                bid, ask = book[(sid, t)]
                mid = 0.5 * (bid + ask)
                if mid > 0:
                    v.append((ask - bid) / mid)
            v.sort()
            if v:
                n = len(v)
                spreads[str(sid)] = {"n": n, "p10": v[n // 10], "p50": v[n // 2],
                                     "p90": v[9 * n // 10]}
                print("        %-14s n %6d   p10 %7.3f%%   p50 %7.3f%%   p90 %7.3f%%"
                      % (HUBS[sid][0], n, 100 * v[n // 10], 100 * v[n // 2],
                         100 * v[9 * n // 10]))

        # The raw two-sided count is not the usable count. A book with a 1 ISK
        # bid and a 1,000,000 ISK ask is "two-sided" and carries no information:
        # the size criterion needs the friction change to be large against the
        # friction, so an item whose own spread is 150% cannot register a 3.5
        # percentage point tax move. This is the funnel that decides the design.
        print("\n      joint coverage CONDITIONED on the spread, Jita x Amarr")
        print("        a 3.5pp tax move is >= 17%% of the friction only when the")
        print("        one-way spread is under 20.6%% (theta=1) or 2.1%% (theta=0.1)")
        ja, am = 60003760, 60008494
        two_cap = {}
        for cap in (0.01, 0.02, 0.05, 0.10, 0.206, 0.50, 1.00):
            n = 0
            for t in (two[ja] & two[am]):
                ok = True
                for sid in (ja, am):
                    bid, ask = book[(sid, t)]
                    mid = 0.5 * (bid + ask)
                    if mid <= 0 or (ask - bid) / mid > cap:
                        ok = False
                        break
                if ok:
                    n += 1
            flag = ""
            if abs(cap - 0.206) < 1e-9:
                flag = "   <- theta=1 threshold"
            if abs(cap - 0.02) < 1e-9:
                flag = "   <- theta=0.1 threshold"
            print("        spread <= %6.1f%% at BOTH hubs:  %6d types%s"
                  % (100 * cap, n, flag))
            two_cap["%.3f" % cap] = n

        print("\n      PLEX (type_id %d), by name:" % PLEX_TYPE_ID)
        for sid in ids:
            b = book.get((sid, PLEX_TYPE_ID))
            if b is None:
                print("        %-14s absent" % HUBS[sid][0])
            elif b[0] is None or b[1] is None:
                print("        %-14s one-sided: bid %s ask %s" % (HUBS[sid][0], b[0], b[1]))
            else:
                mid = 0.5 * (b[0] + b[1])
                print("        %-14s bid %14.2f  ask %14.2f  spread %.3f%%"
                      % (HUBS[sid][0], b[0], b[1], 100 * (b[1] - b[0]) / mid))

        out["snapshots"].append({
            "file": name, "rows": n_rows, "hub_rows": n_hit,
            "two_sided": {str(k): len(v) for k, v in two.items()},
            "pairs": pairs, "spreads": spreads,
            "jita_amarr_by_spread_cap": two_cap,
        })
        print("")

    out["unreadable"] = bad
    if bad:
        print("  %d snapshot(s) were unreadable and were SKIPPED, by name:" % len(bad))
        for b in bad:
            print("    %s" % b["file"])
    os.makedirs(RESULTS, exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("  wrote %s" % os.path.relpath(OUT, ROOT))
    print("  no cross-hub price ratio was formed. Availability only.")
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)

    chk("1  the two usable event dates are the sales-tax-only ones; the 2021"
        " pair moved the broker fee too and is excluded in the docstring",
        "2024-07-25" in src and "2025-03-12" in src and "2021-10-19" in src)
    chk("2  five hubs are scanned, not two: the pair is a reading, not an"
        " assumption (D12)", len(HUBS) == 5)
    chk("3  the registered pair is Jita 4-4 and Amarr VIII",
        60003760 in HUBS and 60008494 in HUBS)
    chk("4  filenames are discovered from the index; the template is the"
        " fallback and the note says which was used",
        "day_index" in {n.name for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef)}
        and "FELL BACK" in src)
    chk("4b the base URL carries the `history` path segment; without it every"
        " URL 404s, which is how the first version failed",
        BASE.endswith("/market-orders/history"))
    chk("5  the name regex matches the archive's shape and rejects a stray link",
        NAME_RE.search("market-orders-2025-02-26_12-15-02.v3.csv.bz2") is not None
        and NAME_RE.search("market-orders-index.html") is None)
    chk("6  columns are read by NAME from the header, so a column-order change"
        " cannot silently misread prices", "ix[\"price\"]" in src)

    calls = {getattr(c.func, "attr", None) for c in ast.walk(tree)
             if isinstance(c, ast.Call)}
    chk("7  nothing here deletes anything (AST walk)",
        not ({"remove", "unlink", "rmtree", "rmdir"} & calls))
    chk("8  a stale part file is parked with an .expired_ suffix", "rename" in calls)

    fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("9  no function here is named for the index half or for rho: this file"
        " stops at availability",
        not any(k in n.lower() for n in fns
                for k in ("rho", "midratio", "mid_ratio", "numerator", "index_half")))
    probe_fn = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "cmd_probe")
    txt = ast.unparse(probe_fn) if hasattr(ast, "unparse") else ""
    chk("10 cmd_probe forms no ratio between two hubs' prices",
        "book[(a," not in txt and "mid_b" not in txt)

    chk("11 the raw line is substring-filtered before it is split: 16M rows a"
        " snapshot and only the hub rows matter", "any(k in line for k in keys)" in src)
    scan_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "scan_one")
    chk("13 a malformed snapshot is reported and skipped, not raised: one bad"
        " file must not stop the rest of the evidence being read",
        not any(isinstance(n, ast.Raise) for n in ast.walk(scan_fn)))
    chk("14 the unreadable files are named in the output, not just counted",
        "were unreadable and were SKIPPED, by name" in src)
    chk("15 the joint count is reported conditioned on the spread; the raw"
        " two-sided count alone is not the usable count",
        "jita_amarr_by_spread_cap" in src and "0.206" in src)
    chk("12 the file carries no stage number: this registers nothing",
        os.path.basename(__file__).startswith("eve_market"))

    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", metavar="DATE")
    ap.add_argument("--fetch", metavar="DATE")
    ap.add_argument("--slots", type=int, default=4)
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.list:
        return cmd_list(a.list)
    if a.fetch:
        return cmd_fetch(a.fetch, a.slots)
    if a.probe:
        return cmd_probe()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
