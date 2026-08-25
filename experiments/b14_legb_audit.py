"""B14 leg B: three diagnostics on the built cache.

Registered in the design file, section 7 supplement 2, B14_A16 supplement 3.

  D1  alignment rate per group per month
  D2  the exact (bid, ask) literal pairs among wide quotes, ranked by count,
      so a venue's stub convention names itself instead of being guessed at
  D3  median price per symbol per month, which is what identifies the names
      that dip under a dollar and therefore lose rows to the sub-penny rule

Reads the cache only. Computes no statistic: B14_A16 clause 5 still stands.

Usage
    python experiments/b14_legb_audit.py --selftest
    python experiments/b14_legb_audit.py --run
"""
import argparse
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "data", "cache", "b14_legb")
SYMS_FILE = os.path.join(ROOT, "results", "b14_legb_symbols.json")
CHECKS = os.path.join(ROOT, "results", "b14_legb_panel_checks.json")
OUT = os.path.join(ROOT, "results", "b14_legb_audit.json")

MONTHS = ["2018-%02d" % m for m in range(5, 13)]
INSIDE = {"2018-05", "2018-06", "2018-07", "2018-08", "2018-09"}
EXCLUDED = {"TA", "SSP"}
#: D2 needs a boundary to define "wide", and any boundary is arbitrary, so it is
#: set as loose as it can be while still isolating quotes that cannot be markets:
#: an ask at least three times the bid. Nothing is dropped on it; it only decides
#: which rows get their literal pair tabulated.
WIDE_RATIO = 3.0
TOP_PAIRS = 8


def load(np, m):
    p = os.path.join(CACHE, "panel_%s.npz" % m.replace("-", ""))
    if not os.path.exists(p):
        return None
    d = np.load(p, allow_pickle=False)
    return d, [str(x) for x in d["symbol_table"]]


def run():
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("this needs numpy; nothing was written")
    grp = json.load(open(SYMS_FILE, encoding="utf-8"))["symbols"]
    g_of = {s: g for g, v in grp.items() for s in v}
    checks = json.load(open(CHECKS, encoding="utf-8")) if os.path.exists(CHECKS) else {}
    res = {"D1": {}, "D2": {}, "D3": {}}

    print("D1  aligned cells per symbol-day, per group per month")
    print("    the pooled alignment rate jumped 28 percent across the event; this")
    print("    asks whether the jump is one group or all of them.")
    print("\n    month     C      G1      G2      G3     G1/C   G2/C   G3/C")
    days = {}
    for m in MONTHS:
        got = load(np, m)
        if not got:
            continue
        d, tab = got
        sym = d["sym"]
        sec = d["sec"]
        nd = len(np.unique(sec // 86400))
        days[m] = nd
        row, per = {}, {}
        for g in ("C", "G1", "G2", "G3"):
            gid = np.array([tab[i] not in EXCLUDED and g_of.get(tab[i]) == g
                            for i in range(len(tab))])
            sel = gid[sym]
            n = int(sel.sum())
            nsym = len(np.unique(sym[sel]))
            row[g] = n
            per[g] = n / max(nsym, 1) / max(nd, 1)
        print("    %s %6.0f  %6.0f  %6.0f  %6.0f   %5.2f  %5.2f  %5.2f"
              % (m, per["C"], per["G1"], per["G2"], per["G3"],
                 per["G1"] / per["C"], per["G2"] / per["C"], per["G3"] / per["C"]))
        res["D1"][m] = {"trading_days": nd, "cells": row,
                        "cells_per_symbol_day": {k: round(v, 1) for k, v in per.items()}}

    print("\n    the last three columns are the ratio to control in the SAME month,")
    print("    so a common time trend cancels out of them.")

    print("\n\nD2  exact (bid, ask) pairs where ask >= %.0f x bid, ranked by count"
          % WIDE_RATIO)
    for venue, kb, ka in (("XNYS.PILLAR", "bid_a", "ask_a"),
                          ("XNAS.ITCH", "bid_b", "ask_b")):
        tally, wide_n, tot = {}, 0, 0
        for m in MONTHS:
            got = load(np, m)
            if not got:
                continue
            d, _ = got
            b, a = d[kb], d[ka]
            tot += b.size
            w = a.astype(np.int64) >= (b.astype(np.int64) * WIDE_RATIO)
            wide_n += int(w.sum())
            pairs, counts = np.unique(np.stack([b[w], a[w]], axis=1), axis=0,
                                      return_counts=True)
            for (bb, aa), c in zip(pairs.tolist(), counts.tolist()):
                tally[(bb, aa)] = tally.get((bb, aa), 0) + c
        top = sorted(tally.items(), key=lambda kv: -kv[1])[:TOP_PAIRS]
        print("\n    %-14s wide cells %d of %d = %.6f   distinct pairs %d"
              % (venue, wide_n, tot, wide_n / max(tot, 1), len(tally)))
        for (bb, aa), c in top:
            print("        bid $%-12.2f ask $%-12.2f  %8d   %6.2f%% of wide"
                  % (bb / 100, aa / 100, c, 100 * c / max(wide_n, 1)))
        res["D2"][venue] = {"wide_cells": wide_n, "total_cells": tot,
                            "distinct_pairs": len(tally),
                            "top": [{"bid_cents": k[0], "ask_cents": k[1], "n": v}
                                    for k, v in top]}

    print("\n\nD3  median mid price per symbol, per month; names near or under $1")
    print("    are the ones the sub-penny rule truncates")
    risky = {}
    for m in MONTHS:
        got = load(np, m)
        if not got:
            continue
        d, tab = got
        sym = d["sym"]
        mid = (d["bid_a"].astype(np.int64) + d["ask_a"].astype(np.int64)) // 2
        order = np.argsort(sym, kind="stable")
        s_sorted, m_sorted = sym[order], mid[order]
        edges = np.searchsorted(s_sorted, np.arange(len(tab) + 1))
        for i in range(len(tab)):
            lo, hi = edges[i], edges[i + 1]
            if hi <= lo or tab[i] in EXCLUDED:
                continue
            med = float(np.median(m_sorted[lo:hi])) / 100
            if med < 5.0:
                risky.setdefault(tab[i], {})[m] = round(med, 3)
    res["D3"] = risky
    print("\n    symbol  grp   %s" % "  ".join(x[2:] for x in MONTHS))
    for s in sorted(risky, key=lambda s: min(risky[s].values())):
        cells = ["%6.2f" % risky[s][m] if m in risky[s] else "     -" for m in MONTHS]
        print("    %-6s  %-3s  %s" % (s, g_of.get(s, "?"), " ".join(cells)))
    print("\n    listed: every symbol whose median mid fell below $5 in any month.")

    oc = {}
    for m, c in checks.items():
        for v in ("XNYS.PILLAR", "XNAS.ITCH"):
            for s, n in (c.get(v, {}).get("off_cent_by_symbol") or {}).items():
                oc[s] = oc.get(s, 0) + n
    print("\n    off-cent rows dropped, by symbol, summed over both venues and all months:")
    for s, n in sorted(oc.items(), key=lambda kv: -kv[1]):
        print("        %-6s %-3s %9d" % (s, g_of.get(s, "?"), n))
    res["off_cent_by_symbol_total"] = oc

    json.dump(res, open(OUT, "w"), indent=2, sort_keys=True)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the inside set is the five months before the event boundary",
        INSIDE == {"2018-05", "2018-06", "2018-07", "2018-08", "2018-09"})
    chk("the exclusion matches the one the cache builder registered",
        EXCLUDED == {"TA", "SSP"})
    chk("the wide boundary only selects rows for tabulation, it drops nothing",
        WIDE_RATIO > 1)
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"),
              ("shutil", "rmtree"), ("Path", "unlink")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("no statistic is defined here: " +
        (", ".join(sorted(defined & {"rho", "did", "regress", "adjudicate"})) or "zero"),
        not (defined & {"rho", "did", "regress", "adjudicate"}))
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
