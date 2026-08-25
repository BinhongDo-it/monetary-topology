"""B14 leg B bulk pull.

Authorised by the design file, section 7 supplement 2, B14_A14 clause 3 row one: all
four probe checks passed, so the full set is bought. The specification is B14_A15.

  108 symbols from results/b14_legb_symbols.json
  2018-05-01 through 2018-12-31
  venues XNYS.PILLAR and XNAS.ITCH
  schema bbo-1s

The pull is cut into (venue, month) batches, sixteen of them, so a human can
audit each one as it lands. Nothing is overwritten and nothing is deleted: a
batch whose file is already on disk is skipped, and a stale .part from a crashed
run is renamed with an .expired suffix rather than removed.

The event boundary is B14_A15 clause 1: the pilot was in force for the whole session
of 2018-09-28, so inside ends 09-28 inclusive and outside begins 10-01.

The API key is read from the environment or from the repo .env; it is never
printed, never written to a file, and never passed on a command line.

Order of operations
    python experiments/b14_legb_pull.py --selftest        no network
    python experiments/b14_legb_pull.py --resolve         free, finds bad symbols
    python experiments/b14_legb_pull.py --cost            free, quotes every batch
    python experiments/b14_legb_pull.py --plan            no network
    python experiments/b14_legb_pull.py --fetch 2018-05   buys one month
    python experiments/b14_legb_pull.py --verify          no network
"""
import argparse
import ast
import base64
import datetime
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "b14_legb")
SYMS_FILE = os.path.join(ROOT, "results", "b14_legb_symbols.json")
SPEND = os.path.join(ROOT, "results", "b14_legb_spend.json")
RESOLVED = os.path.join(ROOT, "results", "b14_legb_resolve.json")

API = "https://hist.databento.com/v0"
VENUES = ["XNYS.PILLAR", "XNAS.ITCH"]
SCHEMA = "bbo-1s"
MONTHS = ["2018-%02d" % m for m in range(5, 13)]

#: B14_A15 clause 3. $100 is the cumulative stop, set so that the second-venue
#: extension of B14_A15 clause 5 still has room under it.
BATCH_CEILING_USD = 15.00
TOTAL_CEILING_USD = 100.00

#: Level 9 was the default and it is slow. On the first batch the wire delivered
#: about 1.9 MB/s of CSV, so compression was not the bottleneck; if --wire-zstd
#: lifts the wire rate then level 9 would become one, and 6 costs about 2% ratio.
GZIP_LEVEL = 6
#: Print a running byte count during a fetch. The first batch ran silent for ten
#: minutes and there was no way to tell a slow pull from a hung one.
PROGRESS_EVERY_BYTES = 100 << 20

#: B14_A15 clause 1, measured on the probe rather than read off the prospectus.
LAST_INSIDE_DAY = "2018-09-28"
FIRST_OUTSIDE_DAY = "2018-10-01"

#: Wire format, fixed by the probe (results file, B14_A14 reading 2).
PX_SCALE = 1e9
NULL_I64 = 9223372036854775807
NULL_U64 = 18446744073709551615
NICKEL_FIXED = 50000000
ET_2018 = datetime.timezone(datetime.timedelta(hours=-4))


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


def symbols():
    d = json.load(open(SYMS_FILE, encoding="utf-8"))
    return d, sorted({s for v in d["symbols"].values() for s in v})


def month_window(m):
    y, mm = int(m[:4]), int(m[5:7])
    a = "%04d-%02d-01" % (y, mm)
    b = "%04d-01-01" % (y + 1) if mm == 12 else "%04d-%02d-01" % (y, mm + 1)
    return a, b


def dst_path(venue, m):
    return os.path.join(RAW, "%s_%s_%s.csv.gz"
                        % (venue.replace(".", "_"), SCHEMA, m.replace("-", "")))


def open_request(endpoint, params, key):
    url = API + "/" + endpoint
    data = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(url, data=data)
    tok = base64.b64encode((key + ":").encode()).decode()
    req.add_header("Authorization", "Basic " + tok)
    return urllib.request.urlopen(req, timeout=1800)


def call(endpoint, params, key):
    try:
        with open_request(endpoint, params, key) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:600]}


def base_params(syms, venue, a, b):
    return {"dataset": venue, "symbols": ",".join(syms), "schema": SCHEMA,
            "start": a, "end": b, "stype_in": "raw_symbol", "mode": "historical"}


def load_spend():
    if os.path.exists(SPEND):
        return json.load(open(SPEND, encoding="utf-8"))
    return {"batches": [], "usd_total": 0.0}


def save_spend(led):
    led["usd_total"] = round(sum(float(b["usd"]) for b in led["batches"]), 6)
    tmp = SPEND + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=2, sort_keys=True)
    os.replace(tmp, SPEND)


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def park(path):
    """Move a stale artefact aside. The house rule forbids deleting anything."""
    if os.path.exists(path):
        aside = path + ".expired_" + stamp()
        os.rename(path, aside)
        print("    parked a stale file as %s" % os.path.basename(aside))


def resolve(key):
    d, syms = symbols()
    a, _ = month_window(MONTHS[0])
    _, b = month_window(MONTHS[-1])
    out = {}
    print("resolving %d symbols over %s .. %s" % (len(syms), a, b))
    for venue in VENUES:
        r = call("symbology.resolve",
                 {"dataset": venue, "symbols": ",".join(syms),
                  "stype_in": "raw_symbol", "stype_out": "instrument_id",
                  "start_date": a, "end_date": b}, key)
        if "http_error" in r:
            print("  %-14s HTTP %s  %s" % (venue, r["http_error"], r["body"][:300]))
            out[venue] = r
            continue
        nf = sorted(r.get("not_found") or [])
        pt = sorted(r.get("partial") or [])
        print("  %-14s not_found %d  partial %d" % (venue, len(nf), len(pt)))
        if nf:
            print("      not_found: %s" % " ".join(nf))
        if pt:
            print("      partial  : %s" % " ".join(pt))
        out[venue] = {"not_found": nf, "partial": pt}
    json.dump({"window": [a, b], "venues": out}, open(RESOLVED, "w"),
              indent=2, sort_keys=True)
    print("\n  written %s" % os.path.relpath(RESOLVED, ROOT))
    print("  a symbol listed above is NOT silently dropped; B14_A15 clause 4 says it")
    print("  gets named in the results file before any decision is taken.")
    return 0


def cost(key, months=None):
    _, syms = symbols()
    months = months or MONTHS
    grand, table = 0.0, []
    print("quoting %d symbols, schema %s, %d months x %d venues"
          % (len(syms), SCHEMA, len(months), len(VENUES)))
    for venue in VENUES:
        print("\n=== %s ===" % venue)
        sub, subb = 0.0, 0
        for m in months:
            a, b = month_window(m)
            p = base_params(syms, venue, a, b)
            c = call("metadata.get_cost", p, key)
            z = call("metadata.get_billable_size", p, key)
            if isinstance(c, dict):
                print("  %s  HTTP %s  %s" % (m, c.get("http_error"), c.get("body", "")[:220]))
                continue
            usd, byts = float(c), int(z)
            done = os.path.exists(dst_path(venue, m))
            print("  %s  $%8.4f  %9.1f MB  %s"
                  % (m, usd, byts / 1e6, "ON DISK" if done else ""))
            table.append({"venue": venue, "month": m, "usd": usd, "bytes": byts,
                          "on_disk": done})
            sub += usd
            subb += byts
        print("  subtotal      $%8.4f  %9.1f MB" % (sub, subb / 1e6))
        grand += sub
    left = sum(r["usd"] for r in table if not r["on_disk"])
    print("\n  GRAND QUOTE   $%.4f   (%.2f GB billable)"
          % (grand, sum(r["bytes"] for r in table) / 1e9))
    print("  still to buy  $%.4f" % left)
    print("  ceilings: batch $%.2f, cumulative $%.2f"
          % (BATCH_CEILING_USD, TOTAL_CEILING_USD))
    over = [r for r in table if r["usd"] > BATCH_CEILING_USD]
    if over:
        print("  ** %d batch(es) exceed the batch ceiling: %s"
              % (len(over), ", ".join("%s %s" % (r["venue"], r["month"]) for r in over)))
    if left > TOTAL_CEILING_USD:
        print("  ** the remaining quote exceeds the cumulative ceiling")
    return 0


def plan():
    print("batches: %d venues x %d months = %d" % (len(VENUES), len(MONTHS),
                                                   len(VENUES) * len(MONTHS)))
    todo = 0
    for venue in VENUES:
        for m in MONTHS:
            p = dst_path(venue, m)
            if os.path.exists(p):
                print("  DONE  %-14s %s  %9.1f MB gz" % (venue, m, os.path.getsize(p) / 1e6))
            else:
                print("  TODO  %-14s %s" % (venue, m))
                todo += 1
    led = load_spend()
    print("\n  %d batches left; spent so far $%.4f over %d recorded batches"
          % (todo, led["usd_total"], len(led["batches"])))
    return 0


def zstd_reader(resp):
    """Databento can compress the wire body. The saved file stays gzip either way,
    so --verify and every downstream reader see one format."""
    try:
        import zstandard
    except ImportError:
        raise SystemExit(
            "--wire-zstd needs the zstandard package; install it or drop the flag. "
            "Nothing was written and the batch was not charged twice: the quote "
            "call already happened but no timeseries body was consumed.")
    return zstandard.ZstdDecompressor().stream_reader(resp)


def fetch(key, months, wire_zstd=False):
    _, syms = symbols()
    os.makedirs(RAW, exist_ok=True)
    led = load_spend()
    for m in months:
        if m not in MONTHS:
            print("  %s is outside the registered window %s..%s; refused"
                  % (m, MONTHS[0], MONTHS[-1]))
            return 1
    for m in months:
        a, b = month_window(m)
        for venue in VENUES:
            dst = dst_path(venue, m)
            if os.path.exists(dst):
                print("  SKIP  %-14s %s  already on disk, %9.1f MB"
                      % (venue, m, os.path.getsize(dst) / 1e6))
                continue
            p = base_params(syms, venue, a, b)
            c = call("metadata.get_cost", p, key)
            if isinstance(c, dict):
                print("  STOP  %-14s %s  quote failed HTTP %s  %s"
                      % (venue, m, c.get("http_error"), c.get("body", "")[:300]))
                return 1
            usd = float(c)
            if usd > BATCH_CEILING_USD:
                print("  STOP  %-14s %s  quote $%.4f exceeds the batch ceiling $%.2f"
                      % (venue, m, usd, BATCH_CEILING_USD))
                return 1
            if led["usd_total"] + usd > TOTAL_CEILING_USD:
                print("  STOP  %-14s %s  $%.4f would take the running total to $%.4f, "
                      "past the cumulative ceiling $%.2f"
                      % (venue, m, usd, led["usd_total"] + usd, TOTAL_CEILING_USD))
                return 1
            print("  BUY   %-14s %s  quote $%.4f  (running $%.4f)"
                  % (venue, m, usd, led["usd_total"] + usd))
            tmp = dst + ".part"
            park(tmp)
            got = 0
            q = dict(p)
            q.update({"encoding": "csv", "map_symbols": "true"})
            q.pop("mode", None)
            if wire_zstd:
                q["compression"] = "zstd"
            t0 = datetime.datetime.now()
            mark = [PROGRESS_EVERY_BYTES]

            def tick(n):
                if n >= mark[0]:
                    mark[0] += PROGRESS_EVERY_BYTES
                    el = (datetime.datetime.now() - t0).total_seconds()
                    print("        %7.0f MB csv  %6.0f s  %5.2f MB/s"
                          % (n / 1e6, el, n / 1e6 / max(el, 1e-9)))

            try:
                with open_request("timeseries.get_range", q, key) as r, \
                        gzip.open(tmp, "wb", GZIP_LEVEL) as out:
                    src = zstd_reader(r) if wire_zstd else r
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        got += len(chunk)
                        out.write(chunk)
                        tick(got)
            except urllib.error.HTTPError as e:
                # Stop cleanly with the ledger intact rather than tracebacking out
                # of a fourteen-batch run. The .part stays where it is; the house
                # rule forbids deleting it, and the next attempt parks it aside.
                print("  STOP  %-14s %s  body HTTP %s  %s"
                      % (venue, m, e.code, e.read().decode("utf-8", "replace")[:400]))
                print("        nothing was added to the ledger for this batch;")
                print("        %s is incomplete and will be parked on the next try."
                      % os.path.basename(tmp))
                return 1
            secs = (datetime.datetime.now() - t0).total_seconds()
            os.rename(tmp, dst)
            led["batches"].append({"venue": venue, "month": m, "usd": usd,
                                   "csv_bytes": got,
                                   "gz_bytes": os.path.getsize(dst),
                                   "wire_zstd": bool(wire_zstd),
                                   "seconds": round(secs, 1),
                                   "at": datetime.datetime.now().isoformat(timespec="seconds")})
            save_spend(led)
            print("        %9.1f MB csv -> %7.1f MB gz   %.0f s   %.2f MB/s%s"
                  % (got / 1e6, os.path.getsize(dst) / 1e6, secs,
                     got / 1e6 / max(secs, 1e-9), "   wire zstd" if wire_zstd else ""))
    print("\n  running total $%.4f over %d batches" % (led["usd_total"], len(led["batches"])))
    print("  next: python experiments/b14_legb_pull.py --verify")
    return 0


def verify(month=None):
    d, _ = symbols()
    grp = {s: g for g, v in d["symbols"].items() for s in v}
    files = [(v, m) for v in VENUES for m in MONTHS
             if os.path.exists(dst_path(v, m)) and (month is None or m == month)]
    if not files:
        print("  nothing on disk for that selection")
        return 2
    for venue, m in files:
        path = dst_path(venue, m)
        rows = kept = 0
        seen_sym, seen_day = set(), set()
        per_sym = {}
        by = {}
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            head = fh.readline().rstrip("\n").split(",")
            i = {k: j for j, k in enumerate(head)}
            cb, ca, ct, cs = i["bid_px_00"], i["ask_px_00"], i["ts_recv"], i["symbol"]
            for line in fh:
                r = line.rstrip("\n").split(",")
                rows += 1
                try:
                    bi, ai = int(r[cb]), int(r[ca])
                except (ValueError, IndexError):
                    continue
                if bi == NULL_I64 or ai == NULL_I64 or bi <= 0 or ai <= 0:
                    continue
                kept += 1
                seen_sym.add(r[cs])
                day = datetime.datetime.fromtimestamp(
                    int(r[ct]) // 10 ** 9, ET_2018).strftime("%Y-%m-%d")
                seen_day.add(day)
                per_sym.setdefault(r[cs], set()).add(day)
                g = grp.get(r[cs], "?")
                w = "inside" if day <= LAST_INSIDE_DAY else "outside"
                k = (g, w)
                cell = by.setdefault(k, [0, 0])
                cell[1] += 1
                if bi % NICKEL_FIXED == 0 and ai % NICKEL_FIXED == 0:
                    cell[0] += 1
        print("\n%-14s %s   rows %d   two-sided %d   symbols %d   days %d (%s..%s)"
              % (venue, m, rows, kept, len(seen_sym), len(seen_day),
                 min(seen_day) if seen_day else "-", max(seen_day) if seen_day else "-"))
        missing = sorted(set(grp) - seen_sym)
        if missing:
            print("    symbols with no two-sided quote all month (%d): %s"
                  % (len(missing), " ".join(missing)))
        full = len(seen_day)
        thin = sorted((len(v), s) for s, v in per_sym.items() if len(v) < full)
        if thin:
            print("    symbols short of the %d-day month (%d): %s" % (
                full, len(thin), " ".join("%s(%d)" % (s, n) for n, s in thin[:20])))
        else:
            print("    every symbol present has all %d days" % full)
        for k in sorted(by):
            o, c = by[k]
            print("    %-3s %-8s  on5 %8d / %9d = %.4f" % (k[0], k[1], o, c, o / c))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the window is the registered one, 2018-05 through 2018-12",
        MONTHS[0] == "2018-05" and MONTHS[-1] == "2018-12" and len(MONTHS) == 8)
    chk("month windows are half open and chain with no gap and no overlap",
        all(month_window(MONTHS[k])[1] == month_window(MONTHS[k + 1])[0]
            for k in range(len(MONTHS) - 1))
        and month_window("2018-12") == ("2018-12-01", "2019-01-01"))
    chk("the whole window brackets the pilot termination on both sides",
        month_window(MONTHS[0])[0] < LAST_INSIDE_DAY < month_window(MONTHS[-1])[1])
    chk("the event boundary is the one B14_A15 clause 1 fixed from the probe",
        LAST_INSIDE_DAY == "2018-09-28" and FIRST_OUTSIDE_DAY == "2018-10-01")
    chk("the schema is the probe's; changing it needs its own registration",
        SCHEMA == "bbo-1s")
    chk("venues are the two B14_A15 clause 2 registered, and no third one crept in",
        VENUES == ["XNYS.PILLAR", "XNAS.ITCH"])
    chk("both ceilings are set, and the batch one is below the cumulative one",
        0 < BATCH_CEILING_USD < TOTAL_CEILING_USD <= 124.50)
    chk("the wire constants match what the probe measured",
        PX_SCALE == 1e9 and NULL_I64 == 2 ** 63 - 1 and NULL_U64 == 2 ** 64 - 1
        and NICKEL_FIXED == int(0.05 * PX_SCALE))
    if os.path.exists(SYMS_FILE):
        d, syms = symbols()
        chk("the symbol set is the registered 108", len(syms) == 108 and d["n"] == 108)
        chk("every group is represented", all(d["symbols"][g] for g in ("C", "G1", "G2", "G3")))
        chk("no symbol is in two groups at once",
            sum(len(v) for v in d["symbols"].values()) == len(syms))
    chk("the gzip level is set and sane", 1 <= GZIP_LEVEL <= 9)
    chk("a progress interval is set, so a slow pull is distinguishable from a hung one",
        PROGRESS_EVERY_BYTES > 0)
    chk("no two batches write to the same file",
        len({dst_path(v, m) for v in VENUES for m in MONTHS}) == len(VENUES) * len(MONTHS))

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)

    def names_in(node):
        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

    leaked = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        for arg in node.args:
            if names_in(arg) & {"key", "tok"}:
                leaked.append(getattr(node, "lineno", "?"))
    chk("the key is never an argument to print: " +
        (("lines " + ", ".join(map(str, leaked))) if leaked else "zero"), not leaked)

    # The house rule forbids deletion outright. Walk the AST rather than matching
    # strings, because a string match fires on this check's own literals.
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"),
              ("shutil", "rmtree"), ("Path", "unlink")}
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            v = node.func.value
            if isinstance(v, ast.Name) and (v.id, node.func.attr) in banned:
                hits.append(getattr(node, "lineno", "?"))
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)

    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
    chk("no process-spawning module is imported", not (imported & {"subprocess", "pty"}))
    chk("and that import check does see what this file really imports",
        {"json", "os", "gzip", "urllib"} <= imported)
    chk("map_symbols is requested, since the raw pull carries no symbol column",
        '"map_symbols": "true"' in src)
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--resolve", action="store_true", help="free, names bad symbols")
    ap.add_argument("--cost", action="store_true", help="free, quotes every batch")
    ap.add_argument("--plan", action="store_true", help="no network")
    ap.add_argument("--fetch", nargs="+", metavar="YYYY-MM", help="buys these months")
    ap.add_argument("--wire-zstd", action="store_true",
                    help="ask the server to compress the body; the file stays gzip")
    ap.add_argument("--verify", nargs="?", const="__all__", metavar="YYYY-MM",
                    help="no network")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.plan:
        return plan()
    if a.verify:
        return verify(None if a.verify == "__all__" else a.verify)
    if a.resolve:
        return resolve(api_key())
    if a.cost:
        return cost(api_key())
    if a.fetch:
        return fetch(api_key(), a.fetch, a.wire_zstd)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
