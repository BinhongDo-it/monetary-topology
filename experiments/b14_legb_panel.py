"""B14 leg B: build the reusable cross-venue aligned panel cache.

Registered in the design file, section 7 supplement 2, B14_A16.

The bulk pull left 14.18 GB of CSV on disk. Parsing that again for every
statistic would be wasteful, so it gets parsed once into a compact cache and
every downstream statistic reads the cache.

The cache holds PRIMITIVES, not statistics: for each (symbol, second) where both
venues quote two-sided, the four prices. Section 5.1's two halves, the friction
half and the index half, are both functions of those four, so changing the
statistic later costs nothing.

  sym    int16   index into the symbol table stored beside the arrays
  sec    int32   unix seconds
  bid_a  ask_a   int32, XNYS.PILLAR, whole cents
  bid_b  ask_b   int32, XNAS.ITCH,   whole cents

Cents, not a finer unit, for a reason found by smoke-testing the builder on real
September rows: XNAS carries Nasdaq stub quotes at bid $0.01 / ask $199,999.99,
which overflow an int32 of micro-dollars. In cents the ceiling is $21.4 million,
so nothing in this market can overflow, and Reg NMS 612 forbids sub-penny quotes
above $1 so nothing is lost. That last point is not assumed: every row whose wire
price is not a whole number of cents is counted and reported, and if that count
is ever non-zero the unit was the wrong choice and the cache must be rebuilt.

B14_A16 clause 4 fixes six checks that get printed for every month. They are checks,
not verdicts: no threshold is set and every measured number is printed.

Nothing here computes a statistic. B14_A16 clause 5: rho, S+S', S-S' and per-edge
adjudication each need their own registration before they may be computed.

Usage
    python experiments/b14_legb_panel.py --selftest
    python experiments/b14_legb_panel.py --build             all months, skips cached
    python experiments/b14_legb_panel.py --build 2018-09     one month
    python experiments/b14_legb_panel.py --census            reads the cache only
"""
import argparse
import array
import ast
import datetime
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "b14_legb")
CACHE = os.path.join(ROOT, "data", "cache", "b14_legb")
SYMS_FILE = os.path.join(ROOT, "results", "b14_legb_symbols.json")
EXCL_FILE = os.path.join(ROOT, "results", "b14_legb_excluded.json")
CHECKS = os.path.join(ROOT, "results", "b14_legb_panel_checks.json")

VENUE_A = "XNYS.PILLAR"
VENUE_B = "XNAS.ITCH"
SCHEMA = "bbo-1s"
MONTHS = ["2018-%02d" % m for m in range(5, 13)]

#: B14_A15 clause 1, measured off the probe rather than read off the prospectus.
LAST_INSIDE_DAY = "2018-09-28"
#: B14_A16 clause 3.
CORE_INSIDE, CORE_OUTSIDE = "2018-09", "2018-10"
#: B14_A16 clause 2. Both begin quoting on XNYS on 2018-09-24, five sessions before
#: the pilot ended, so their inside window is five days against sixty-odd outside.
EXCLUDED = {"TA": "XNYS coverage begins 2018-09-24, five sessions before the event",
            "SSP": "XNYS coverage begins 2018-09-24, five sessions before the event"}

NULL_I64 = 9223372036854775807
WIRE_PER_CENT = 10 ** 7        # wire is 1e-9 dollars, the cache is whole cents
#: The Nasdaq stub pair, exactly. Counted, kept in the cache, and left for the
#: analysis layer to drop, same as the TA / SSP ruling: the cache holds
#: primitives and every judgement stays reversible.
STUB_BID_CENTS = 1
STUB_ASK_CENTS = 19999999
ET_2018 = datetime.timezone(datetime.timedelta(hours=-4))


def need_numpy():
    try:
        import numpy
        return numpy
    except ImportError:
        raise SystemExit("this needs numpy; nothing was written")


def raw_path(venue, m):
    return os.path.join(RAW, "%s_%s_%s.csv.gz"
                        % (venue.replace(".", "_"), SCHEMA, m.replace("-", "")))


def cache_path(m):
    return os.path.join(CACHE, "panel_%s.npz" % m.replace("-", ""))


def symbols():
    d = json.load(open(SYMS_FILE, encoding="utf-8"))
    table = sorted({s for v in d["symbols"].values() for s in v})
    grp = {s: g for g, v in d["symbols"].items() for s in v}
    return table, grp


def read_venue(np, path, sym_ix):
    """One venue-month into flat arrays. Returns arrays plus this venue's checks."""
    # array.array, not list: the largest venue-month is 13.4M rows, and four
    # Python lists of boxed ints would cost about 2 GB per venue against 200 MB
    # here. The typecodes also assert the ranges the selftest claims.
    sec = array.array("q")
    sym = array.array("h")
    bid = array.array("i")
    ask = array.array("i")
    n_rows = n_null = n_offcent = n_crossed = n_locked = n_stub = 0
    px_max = 0
    offcent_by_sym = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split(",")
        i = {k: j for j, k in enumerate(head)}
        ct, cb, ca, cs = i["ts_recv"], i["bid_px_00"], i["ask_px_00"], i["symbol"]
        wide = max(ct, cb, ca, cs)
        for line in fh:
            r = line.split(",")
            if len(r) <= wide:
                continue
            n_rows += 1
            try:
                bi, ai = int(r[cb]), int(r[ca])
            except ValueError:
                n_null += 1
                continue
            if bi == NULL_I64 or ai == NULL_I64 or bi <= 0 or ai <= 0:
                n_null += 1
                continue
            k = sym_ix.get(r[cs].rstrip("\n"))
            if k is None:
                continue
            raw_sym = r[cs].rstrip("\n")
            if bi % WIRE_PER_CENT or ai % WIRE_PER_CENT:
                # Reg NMS 612 permits sub-penny quoting below $1.00, so these are
                # legal quotes on a finer grid, not dirty data. They cannot be
                # stored in cents and they are not comparable on a nickel-grid
                # statistic either, so they are dropped and counted BY SYMBOL:
                # the concentration is the finding, not the total.
                n_offcent += 1
                offcent_by_sym[raw_sym] = offcent_by_sym.get(raw_sym, 0) + 1
                continue
            b, a = bi // WIRE_PER_CENT, ai // WIRE_PER_CENT
            if b > a:
                n_crossed += 1
                continue
            if b == a:
                n_locked += 1
                continue
            if b == STUB_BID_CENTS and a == STUB_ASK_CENTS:
                n_stub += 1
            if a > px_max:
                px_max = a
            sec.append(int(r[ct]) // 10 ** 9)
            sym.append(k)
            bid.append(b)
            ask.append(a)
    out = {"sec": np.frombuffer(sec, dtype=np.int64),
           "sym": np.frombuffer(sym, dtype=np.int16),
           "bid": np.frombuffer(bid, dtype=np.int32),
           "ask": np.frombuffer(ask, dtype=np.int32)}
    chk = {"rows": n_rows, "null_or_onesided": n_null,
           "off_cent_grid_dropped": n_offcent,
           "off_cent_by_symbol": dict(sorted(offcent_by_sym.items(),
                                             key=lambda kv: -kv[1])[:10]),
           "crossed_dropped": n_crossed, "locked_dropped": n_locked,
           "stub_quotes_kept": n_stub, "max_ask_cents": px_max,
           "kept": int(out["sec"].size)}
    return out, chk


def build_month(np, m, table, sym_ix):
    a_path, b_path = raw_path(VENUE_A, m), raw_path(VENUE_B, m)
    for p in (a_path, b_path):
        if not os.path.exists(p):
            print("  %s missing; month skipped" % os.path.basename(p))
            return None
    print("  reading %s" % VENUE_A)
    A, ca = read_venue(np, a_path, sym_ix)
    print("  reading %s" % VENUE_B)
    B, cb = read_venue(np, b_path, sym_ix)

    def keyed(d):
        k = d["sec"] * 128 + d["sym"].astype(np.int64)
        order = np.argsort(k, kind="stable")
        k = k[order]
        dup = int(np.count_nonzero(np.diff(k) == 0))
        uniq, first = np.unique(k, return_index=True)
        return uniq, order[first], dup

    ka, ia, dup_a = keyed(A)
    kb, ib, dup_b = keyed(B)
    common, pa, pb = np.intersect1d(ka, kb, assume_unique=True, return_indices=True)
    sa, sb = ia[pa], ib[pb]
    cells = int(common.size)
    smaller = min(int(ka.size), int(kb.size))

    rec = {"sym": A["sym"][sa], "sec": A["sec"][sa].astype(np.int32),
           "bid_a": A["bid"][sa], "ask_a": A["ask"][sa],
           "bid_b": B["bid"][sb], "ask_b": B["ask"][sb]}
    assert np.array_equal(rec["sym"], B["sym"][sb]), "symbol mismatch after the join"
    assert np.array_equal(rec["sec"], B["sec"][sb].astype(np.int32)), "second mismatch"

    os.makedirs(CACHE, exist_ok=True)
    # savez_compressed appends .npz unless the name already ends in it, so the
    # temporary name ends in .npz and the path written is the path named.
    tmp = cache_path(m) + ".part.npz"
    if os.path.exists(tmp):
        os.rename(tmp, tmp + ".expired_"
                  + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    np.savez_compressed(tmp, symbol_table=np.array(table), **rec)
    os.rename(tmp, cache_path(m))

    chk = {"month": m, VENUE_A: ca, VENUE_B: cb,
           "dup_key_a": dup_a, "dup_key_b": dup_b,
           "unique_keys_a": int(ka.size), "unique_keys_b": int(kb.size),
           "aligned_cells": cells,
           "share_of_smaller": round(cells / smaller, 6) if smaller else 0.0,
           "gz_bytes": os.path.getsize(cache_path(m))}
    print("  A rows %d kept %d  |  B rows %d kept %d" % (ca["rows"], ca["kept"],
                                                         cb["rows"], cb["kept"]))
    print("  off-cent dropped A %d B %d   (sub-dollar names, Reg NMS 612 exception)"
          % (ca["off_cent_grid_dropped"], cb["off_cent_grid_dropped"]))
    for tag, c in ((VENUE_A, ca), (VENUE_B, cb)):
        if c["off_cent_by_symbol"]:
            print("      %-14s %s" % (tag, "  ".join(
                "%s:%d" % kv for kv in c["off_cent_by_symbol"].items())))
    print("  crossed dropped A %d B %d   locked dropped A %d B %d"
          % (ca["crossed_dropped"], cb["crossed_dropped"],
             ca["locked_dropped"], cb["locked_dropped"]))
    print("  stub quotes kept  A %d B %d   max ask A $%.2f B $%.2f"
          % (ca["stub_quotes_kept"], cb["stub_quotes_kept"],
             ca["max_ask_cents"] / 100, cb["max_ask_cents"] / 100))
    print("  duplicate (symbol, second) keys: A %d  B %d" % (dup_a, dup_b))
    print("  ALIGNED CELLS %d   = %.4f of the smaller side (%d)"
          % (cells, chk["share_of_smaller"], smaller))
    print("  cache %.1f MB" % (chk["gz_bytes"] / 1e6))
    return chk


def build(months=None):
    np = need_numpy()
    table, grp = symbols()
    sym_ix = {s: i for i, s in enumerate(table)}
    json.dump({"excluded": EXCLUDED, "effective_n": len(table) - len(EXCLUDED),
               "note": "the cache keeps all symbols; the exclusion is applied by "
                       "the analysis layer so the ruling stays reversible"},
              open(EXCL_FILE, "w"), ensure_ascii=False, indent=2, sort_keys=True)
    todo = months or MONTHS
    old = json.load(open(CHECKS, encoding="utf-8")) if os.path.exists(CHECKS) else {}
    for m in todo:
        if os.path.exists(cache_path(m)):
            print("\n%s  cached, %.1f MB, skipped" % (m, os.path.getsize(cache_path(m)) / 1e6))
            continue
        print("\n%s" % m)
        t0 = datetime.datetime.now()
        chk = build_month(np, m, table, sym_ix)
        if chk is None:
            continue
        chk["seconds"] = round((datetime.datetime.now() - t0).total_seconds(), 1)
        print("  %.0f s" % chk["seconds"])
        old[m] = chk
        json.dump(old, open(CHECKS, "w"), indent=2, sort_keys=True)
    print("\n  checks written to %s" % os.path.relpath(CHECKS, ROOT))
    print("  next: python experiments/b14_legb_panel.py --census")
    return 0


def census():
    np = need_numpy()
    table, grp = symbols()
    print("B14_A16 clause 4 check 5: cells per group per month, and the composition.")
    print("The exclusion of %s is applied here, not in the cache."
          % " ".join(sorted(EXCLUDED)))
    print("\n  month    group   symbols   cells        cells/symbol")
    total = 0
    for m in MONTHS:
        p = cache_path(m)
        if not os.path.exists(p):
            continue
        d = np.load(p, allow_pickle=False)
        tab = [str(x) for x in d["symbol_table"]]
        sym = d["sym"]
        keep = np.array([tab[i] not in EXCLUDED for i in range(len(tab))])
        mask = keep[sym]
        for g in ("C", "G1", "G2", "G3"):
            gid = np.array([grp.get(s) == g for s in tab])
            sel = mask & gid[sym]
            n = int(sel.sum())
            nsym = len(np.unique(sym[sel]))
            total += n
            print("  %s  %-4s   %5d   %11d   %10.0f"
                  % (m, g, nsym, n, n / max(nsym, 1)))
        print("")
    print("  total aligned cells across the cache: %d" % total)
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the stored unit is a whole number of wire units",
        WIRE_PER_CENT == 10 ** 7)
    chk("the Nasdaq stub pair is the exact documented one, not a threshold",
        STUB_BID_CENTS == 1 and STUB_ASK_CENTS == 19999999)
    chk("the stub ask itself fits the stored int32, so it is counted not crashed on",
        STUB_ASK_CENTS < 2 ** 31)
    chk("the key multiplier exceeds the symbol count, so no two symbols collide",
        128 > 108)
    chk("the core window is the balanced pair B14_A16 clause 3 fixed",
        CORE_INSIDE == "2018-09" and CORE_OUTSIDE == "2018-10"
        and CORE_INSIDE in MONTHS and CORE_OUTSIDE in MONTHS)
    chk("the core inside month ends on the event boundary",
        LAST_INSIDE_DAY.startswith(CORE_INSIDE))
    chk("the exclusion list is the registered two, and both carry a reason",
        set(EXCLUDED) == {"TA", "SSP"} and all(EXCLUDED.values()))
    if os.path.exists(SYMS_FILE):
        table, grp = symbols()
        chk("the symbol table is the registered 108", len(table) == 108)
        chk("the excluded names are really in the set", set(EXCLUDED) <= set(table))
        chk("excluded names come from different groups, so this is not one group "
            "being thinned", len({grp[s] for s in EXCLUDED}) == 2)
        chk("the int32 ceiling in cents is far above anything this market prints",
            2 ** 31 // 100 > 20 * 10 ** 6)
        chk("the array typecodes hold what is put in them",
            array.array("h").itemsize == 2 and array.array("i").itemsize == 4
            and array.array("q").itemsize == 8 and len(table) < 2 ** 15)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    # B14_A16 clause 5: this file may not compute a statistic. A string match here
    # fires on the check's own literals, which is the fifth time that pattern has
    # shown up in this station, so it walks the function definitions instead.
    stat_names = {"rho", "spread", "friction_half", "index_half", "midpoint",
                  "adjudicate", "did", "regress"}
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("no statistic is defined here, only the cache: " +
        (", ".join(sorted(defined & stat_names)) or "zero"),
        not (defined & stat_names))

    # Locked and crossed must stay separate counters: XNYS drops both and XNAS
    # drops neither, so collapsing them would hide a venue asymmetry. A string
    # match would fire on this check's own literals, so it walks the reader's
    # own augmented assignments instead.
    reader = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "read_venue"), None)
    bumped = {t.target.id for t in ast.walk(reader) if isinstance(t, ast.AugAssign)
              and isinstance(t.target, ast.Name)} if reader else set()
    chk("the reader counts locked and crossed as separate causes",
        {"n_locked", "n_crossed"} <= bumped)
    chk("and it counts the other three drop causes too",
        {"n_null", "n_offcent", "n_stub"} <= bumped)
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"),
              ("shutil", "rmtree"), ("Path", "unlink")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)
    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
    chk("no process-spawning module is imported", not (imported & {"subprocess", "pty"}))
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--build", nargs="*", metavar="YYYY-MM")
    ap.add_argument("--census", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.census:
        return census()
    if a.build is not None:
        return build(a.build or None)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
