"""B14 leg B depth gate: a few symbols, a few days, before any bulk purchase.

Registered in the design file, section 7 supplement 2, A14. D21 / gate five: run
the statistic the bulk pull would use on a small sample first, and count the cells
that MEET the requirement, not the average per cell.

Four things get judged, all fixed before the run (A14 clause 2):

  1  does bbo-1s carry PRICES (bid_px / ask_px) and not just a width  [binary]
  2  can the two venues' seconds be aligned, and on how many
  3  do the prices sit on integer grid points, and what share of states are
     odd-parity (design file section 7 supplement 3; B13 measured 54.4% there)
  4  how many (symbol, second) cells carry all four prices  [the D21 count]

Cost: asks metadata.get_cost first and stops if the quote exceeds the ceiling.

The API key is read from the environment or from the repo .env; it is never
printed, never written to a file, and never passed on a command line.

Usage
    python experiments/b14_legb_probe.py --selftest
    python experiments/b14_legb_probe.py --cost      # quote only, buys nothing
    python experiments/b14_legb_probe.py --fetch
    python experiments/b14_legb_probe.py --judge     # the four checks, no network
"""
import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "b14_legb")
OUT = os.path.join(ROOT, "results", "b14_legb_probe.json")
SYMS_FILE = os.path.join(ROOT, "results", "b14_legb_symbols.json")

API = "https://hist.databento.com/v0"
VENUES = ["XNYS.PILLAR", "XNAS.ITCH"]
SCHEMA = "bbo-1s"
#: Two sessions before the pilot's termination (2018-09-28 close) and two after.
DAYS = ["2018-09-26", "2018-09-27", "2018-10-01", "2018-10-02"]
#: One or two per group, from results/b14_legb_symbols.json. Fixed here so the
#: probe is reproducible rather than depending on whatever sorts first.
PROBE_SYMBOLS = ["AAN", "ARC", "BKS", "AROC", "ACCO"]
COST_CEILING_USD = 1.00
#: Measured on the first probe pull, 2026-08-20, and fixed here so the reader is
#: not guessing at the wire format:
#:   prices are 1e-9 fixed point integers   (38110000000 == $38.11)
#:   INT64_MAX  is the null sentinel for a missing price or size
#:   UINT64_MAX is the null sentinel for ts_event, so ts_recv is the usable clock
#:   there is no symbol column unless map_symbols is requested
PX_SCALE = 1e9
NULL_I64 = 9223372036854775807
NULL_U64 = 18446744073709551615


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


def call(endpoint, params, key, binary=False):
    url = API + "/" + endpoint
    data = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(url, data=data)
    tok = base64.b64encode((key + ":").encode()).decode()
    req.add_header("Authorization", "Basic " + tok)
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body if binary else json.loads(body)


def window():
    return DAYS[0] + "T00:00", DAYS[-1] + "T23:59"


def cost(key):
    out = {}
    a, b = window()
    for ds in VENUES:
        q = call("metadata.get_cost",
                 {"dataset": ds, "symbols": ",".join(PROBE_SYMBOLS),
                  "schema": SCHEMA, "start": a, "end": b,
                  "stype_in": "raw_symbol", "mode": "historical"}, key)
        sz = call("metadata.get_billable_size",
                  {"dataset": ds, "symbols": ",".join(PROBE_SYMBOLS),
                   "schema": SCHEMA, "start": a, "end": b,
                   "stype_in": "raw_symbol", "mode": "historical"}, key)
        out[ds] = {"usd": q, "bytes": sz}
        print("  %-14s  quote $%s   billable %s bytes" % (ds, q, sz))
    total = sum(float(v["usd"]) for v in out.values())
    print("  total quote: $%.4f   (ceiling $%.2f)" % (total, COST_CEILING_USD))
    return out, total


def fetch(key):
    os.makedirs(RAW, exist_ok=True)
    a, b = window()
    got = {}
    for ds in VENUES:
        dst = os.path.join(RAW, "%s_%s_mapped.csv" % (ds.replace(".", "_"), SCHEMA))
        if os.path.exists(dst):
            print("  %-14s already on disk, %d bytes" % (ds, os.path.getsize(dst)))
            got[ds] = dst
            continue
        body = call("timeseries.get_range",
                    {"dataset": ds, "symbols": ",".join(PROBE_SYMBOLS),
                     "schema": SCHEMA, "start": a, "end": b,
                     "stype_in": "raw_symbol", "encoding": "csv",
                     "map_symbols": "true"}, key, binary=True)
        tmp = dst + ".part"
        with open(tmp, "wb") as fh:
            fh.write(body)
        os.replace(tmp, dst)
        print("  %-14s fetched %d bytes" % (ds, len(body)))
        got[ds] = dst
    return got


def load_csv(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split(",")
        idx = {k: i for i, k in enumerate(head)}
        for line in fh:
            rows.append(line.rstrip("\n").split(","))
    return head, idx, rows


def judge():
    res = {"schema": SCHEMA, "venues": VENUES, "days": DAYS,
           "symbols": PROBE_SYMBOLS}
    books = {}
    for ds in VENUES:
        path = os.path.join(RAW, "%s_%s_mapped.csv" % (ds.replace(".", "_"), SCHEMA))
        if not os.path.exists(path):
            print("  %s not on disk; run --fetch first" % ds)
            return 2
        head, idx, rows = load_csv(path)
        books[ds] = (head, idx, rows)
        print("  %-14s %d rows, %d columns" % (ds, len(rows), len(head)))

    # check 1: are there price fields at all
    print("\ncheck 1  does the schema carry PRICES (binary)")
    ok1 = True
    for ds in VENUES:
        head = books[ds][0]
        px = [c for c in head if c.endswith("_px") or c in ("bid_px_00", "ask_px_00")]
        print("    %-14s price-like columns: %s" % (ds, px if px else "NONE"))
        ok1 = ok1 and bool(px)
    res["check1_price_columns"] = ok1
    print("    -> %s" % ("PASS" if ok1 else "**FAIL: leg B is not feasible on this schema**"))
    if not ok1:
        json.dump(res, open(OUT, "w"), indent=2, sort_keys=True)
        return 1

    def col(ds, *names):
        idx = books[ds][1]
        for n in names:
            if n in idx:
                return idx[n]
        return None

    # build (symbol, second) -> (bid, ask) per venue
    per = {}
    for ds in VENUES:
        head, idx, rows = books[ds]
        cb = col(ds, "bid_px_00", "bid_px")
        ca = col(ds, "ask_px_00", "ask_px")
        ct = col(ds, "ts_recv")
        cs = col(ds, "symbol", "raw_symbol")
        if cs is None:
            print("\n    %-14s **no symbol column**; re-fetch with map_symbols" % ds)
            return 2
        d, nulls, bad = {}, 0, 0
        for r in rows:
            try:
                bi, ai = int(r[cb]), int(r[ca])
            except (ValueError, IndexError):
                bad += 1
                continue
            if bi == NULL_I64 or ai == NULL_I64 or bi <= 0 or ai <= 0:
                nulls += 1
                continue
            b, a = bi / PX_SCALE, ai / PX_SCALE
            # ts_recv is nanoseconds since epoch; the second is the first 10 digits
            sec = r[ct][:10]
            d[(r[cs], sec)] = (b, a)
        per[ds] = d
        print("\n    %-14s rows %d, one-sided or null %d, unparsable %d, "
              "usable quote seconds %d" % (ds, len(rows), nulls, bad, len(d)))

    # check 2 and 4: alignment and complete cells
    A, B = per[VENUES[0]], per[VENUES[1]]
    both = set(A) & set(B)
    print("\ncheck 2  seconds where BOTH venues quote: %d" % len(both))
    print("    of %d on %s and %d on %s" % (len(A), VENUES[0], len(B), VENUES[1]))
    res["check2_aligned_seconds"] = len(both)
    res["check4_complete_cells"] = len(both)
    bysym = {}
    for (s, _) in both:
        bysym[s] = bysym.get(s, 0) + 1
    print("\ncheck 4  complete cells per symbol (all four prices present):")
    for s in PROBE_SYMBOLS:
        print("    %-6s %d" % (s, bysym.get(s, 0)))
    res["check4_per_symbol"] = bysym

    # check 3: grid points and parity
    print("\ncheck 3  do prices sit on integer grid points, and parity")
    onpenny = onnickel = tot = odd = 0
    for k in sorted(both):
        b1, a1 = A[k]
        b2, a2 = B[k]
        tot += 1
        cents = [round(x * 100, 4) for x in (b1, a1, b2, a2)]
        if all(abs(c - round(c)) < 1e-6 for c in cents):
            onpenny += 1
            if all(abs(round(c) % 5) < 1e-9 for c in cents):
                onnickel += 1
            # parity: index and friction share parity mod 2 (design file 7 supp 3)
            if int(sum(round(c) for c in cents)) % 2:
                odd += 1
    print("    all four on a whole cent : %d / %d  (%.4f)"
          % (onpenny, tot, onpenny / tot if tot else 0))
    print("    all four on a whole nickel: %d / %d  (%.4f)"
          % (onnickel, tot, onnickel / tot if tot else 0))
    print("    odd-parity states         : %d / %d  (%.4f)   B13 measured 0.544"
          % (odd, onpenny, odd / onpenny if onpenny else 0))
    res["check3"] = {"on_penny": onpenny, "on_nickel": onnickel,
                     "odd_parity": odd, "total": tot}

    res["stage"] = "B14"
    res["diagnostic_only"] = True
    res["diagnostic_reason"] = ("leg B depth gate registered in design file section 7 "
                                "supplement 2 A14; the station is not closed and no "
                                "bulk data has been bought")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=2, sort_keys=True)
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    print("\nRead these against the four rows of design file A14 clause 3 before")
    print("deciding anything. Nothing here authorises a bulk pull on its own.")
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the probe straddles the pilot termination date 2018-09-28",
        any(d < "2018-09-28" for d in DAYS) and any(d > "2018-09-28" for d in DAYS))
    chk("no probe day IS the termination date itself", "2018-09-28" not in DAYS)
    chk("the second venue is not NYSE Group, which is what settles T3",
        not any(v.startswith("ARCX") or v.startswith("XNYS") for v in VENUES[1:]))
    chk("a cost ceiling is set and small", 0 < COST_CEILING_USD <= 5)
    chk("the probe is small: five symbols, four days", len(PROBE_SYMBOLS) == 5
        and len(DAYS) == 4)
    if os.path.exists(SYMS_FILE):
        d = json.load(open(SYMS_FILE))
        allsym = {s for v in d["symbols"].values() for s in v}
        chk("every probe symbol comes from the registered leg B set",
            set(PROBE_SYMBOLS) <= allsym)
        chk("the probe covers the control group and all three treated groups",
            all(any(s in d["symbols"][g] for s in PROBE_SYMBOLS)
                for g in ("C", "G1", "G2", "G3")))
    # Walk the AST rather than matching strings. A string match here fires on this
    # check's own literals, which is a check biting the wrong object -- the fourth
    # time that pattern has shown up in this station, so it gets done properly.
    import ast
    import re
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

    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
    chk("no process-spawning module is imported: " +
        (", ".join(sorted(imported & {"subprocess", "os2", "pty"})) or "zero"),
        not (imported & {"subprocess", "pty"}))
    chk("and that import check does see the modules this file really imports",
        {"json", "os", "urllib"} <= imported)
    chk("the wire format constants match what the first pull showed",
        PX_SCALE == 1e9 and NULL_I64 == 2 ** 63 - 1 and NULL_U64 == 2 ** 64 - 1)
    chk("map_symbols is requested, since the raw pull carries no symbol column",
        '"map_symbols": "true"' in src)
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cost", action="store_true", help="quote only, buys nothing")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--judge", action="store_true", help="the four checks, no network")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.judge:
        return judge()
    if a.cost or a.fetch:
        key = api_key()
        print("cost quote for %d symbols x %d days x %d venues, schema %s"
              % (len(PROBE_SYMBOLS), len(DAYS), len(VENUES), SCHEMA))
        _, total = cost(key)
        if a.fetch:
            if total > COST_CEILING_USD:
                print("\n  quote exceeds the ceiling; nothing fetched. Raise "
                      "COST_CEILING_USD deliberately if this is expected.")
                return 1
            print("\nfetching")
            fetch(key)
            print("\nnext: python experiments/b14_legb_probe.py --judge")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
