"""L2 gate one: is the pure-slack residue arithmetic, or did behaviour change?

Registered in L2's design file, section 2. The cut this gate makes:

    candidate zero, the nickel lattice projection, is arithmetic ON THE QUOTE.
    It widens a spread without anybody changing their mind, so it predicts NO
    change in how market makers participate.

    candidate four (a direct behavioural response to the increment rule),
    candidate two (the trading-side rules) and candidate three (spillover) all
    require behaviour to change, so all three predict participation moves.

So B.IV separates "pure arithmetic" from "something behavioural", and it does it
without any exposure variable. It cannot separate the three behavioural
candidates from each other; that is gate two and gate three.

Measured before writing this (recorded in B14's results file): B.IV carries no
MPID, so it is used here as an OUTCOME, never as an exposure. B.IV switched to
pilot-only reporting on 2016-09-06 and B.I on 2016-10-01, but the count of PILOT
symbols is flat across all nine months in both, so neither switch touches the
sample.

Everything about the sample and the windows is A11's: the pure-slack definition,
the split window, the placebo segment and the real segment are imported from
b14_recheck, not restated.

Usage
    python experiments/l2_gate1.py --selftest
    python experiments/l2_gate1.py --run
"""
import argparse
import ast
import gzip
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIV = os.path.join(ROOT, "data", "raw", "b14_biv")
ASSIGN = os.path.join(ROOT, "data", "raw", "Tick_Pilot_Test_Group_Assignments.txt")
OUT = os.path.join(ROOT, "results", "l2_gate1.json")

_spec = importlib.util.spec_from_file_location(
    "b14_recheck", os.path.join(HERE, "b14_recheck.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

#: A11's own segments, unchanged. Each is (name, pre months, post months).
SEGMENTS = (("real", ("201608", "201609"), ("201611", "201612")),
            ("placebo", ("201606", "201607"), ("201608", "201609")))
#: The three participation measures L2's design file section 2 registered.
MEASURES = (("mm_count", ("MM_BUY_CT", "MM_SELL_CT")),
            ("share_prtcp", ("SHARE_PRTCP_BUY", "SHARE_PRTCP_SELL")),
            ("inside_quote", ("INSD_QT_SHR_PRTCP_BUY", "INSD_QT_SHR_PRTCP_SELL")))
VENUE = {"NYSE": "N", "NYSEArca": "P"}
MIN_DAYS = 10


def groups():
    g = {}
    for line in open(ASSIGN, encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("|")
        if len(p) >= 5 and p[0] != "Ticker_Symbol" and p[4]:
            g[p[0].replace(" ", "")] = p[4]
    return g


def read_month(path, want):
    """(ctr, sym) -> {measure: [daily value]} for one B.IV month file."""
    out = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        head = fh.readline().rstrip("\n").split("|")
        i = {k: j for j, k in enumerate(head)}
        need = [i[c] for _, cols in MEASURES for c in cols]
        ic, isym = i["TRDNG_CNTR"], i["SYMBOL"]
        wide = max(need + [ic, isym])
        for line in fh:
            if not line.startswith("D|"):
                continue
            r = line.rstrip("\n").split("|")
            if len(r) <= wide:
                continue
            sym = r[isym].replace(" ", "")
            if sym not in want:
                continue
            k = (r[ic], sym)
            d = out.setdefault(k, {name: [] for name, _ in MEASURES})
            for name, cols in MEASURES:
                v = 0.0
                ok = True
                for c in cols:
                    try:
                        v += float(r[i[c]] or 0)
                    except ValueError:
                        ok = False
                if ok and v > 0:
                    d[name].append(v)
    return out


def load(want):
    per = {}
    for stem, ctr in VENUE.items():
        for m in ("201606", "201607", "201608", "201609", "201611", "201612"):
            p = os.path.join(BIV, "%s_MMParticipationStatistics_%s.gzip" % (stem, m))
            if not os.path.exists(p):
                print("  missing %s" % os.path.basename(p))
                return None
            for k, d in read_month(p, want).items():
                per.setdefault((k, m), d)
    return per


def delta(per, key, months_pre, months_post, name):
    """log(median post) - log(median pre) for one (venue, symbol) and measure."""
    def side(ms):
        vals = []
        for m in ms:
            vals += per.get((key, m), {}).get(name, [])
        return vals
    a, b = side(months_pre), side(months_post)
    if len(a) < MIN_DAYS or len(b) < MIN_DAYS:
        return None
    ma, mb = R.median(a), R.median(b)
    if not ma or not mb or ma <= 0 or mb <= 0:
        return None
    return math.log(mb) - math.log(ma)


def run():
    if not os.path.isdir(BIV):
        print("  B.IV is not on disk; run experiments/l2_fetch_biv.py --fetch")
        return 2
    rec16 = R.load_raw(R.E.ROUNDS["2016"]["pre"], R.E.ROUNDS["2016"]["post"],
                       extra_windows=[("aug", R.SPLIT_A), ("sep", R.SPLIT_B),
                                      ("apr", R.W_APR), ("may", R.W_MAY),
                                      ("pre_pl", R.W_PLACEBO_PRE)])
    pure = set()
    for k, r in rec16.items():
        v = r["apr"]["bbo"] + r["may"]["bbo"]
        if v and not any(x < R.NICKEL for x in v):
            pure.add(k)
    grp_of = {}
    for k, r in rec16.items():
        g = R.group_of(r, "post")
        if g:
            grp_of[k] = g
    g_all = groups()
    want = {s for (_, s) in pure}
    print("A11's pure slack: %d (venue, symbol); %d distinct symbols"
          % (len(pure), len(want)))
    per = load(want)
    if per is None:
        return 2
    print("B.IV rows loaded for %d (venue, symbol, month) cells\n" % len(per))

    res = {}
    print("  measure       seg       arm   n      median log delta      vs C")
    for name, _ in MEASURES:
        for seg, mpre, mpost in SEGMENTS:
            by = {}
            for k in pure:
                g = grp_of.get(k) or g_all.get(k[1])
                if not g:
                    continue
                d = delta(per, k, mpre, mpost, name)
                if d is not None:
                    by.setdefault((k[0], g), []).append(d)
            tab = {c + "/" + g: R.median(v) for (c, g), v in by.items()}
            n = {c + "/" + g: len(v) for (c, g), v in by.items()}
            for ctr in ("N", "P"):
                base = tab.get(ctr + "/C")
                for g in ("C", "G1", "G2", "G3"):
                    v = tab.get(ctr + "/" + g)
                    gap = (v - base) if (v is not None and base is not None
                                         and g != "C") else None
                    print("  %-13s %-9s %s/%-3s %-6d %s   %s"
                          % (name, seg, ctr, g, n.get(ctr + "/" + g, 0),
                             "None      " if v is None else "%+.6f " % v,
                             "" if gap is None else "%+.6f" % gap))
            res.setdefault(name, {})[seg] = {"table": tab, "n": n}
        print("")

    print("reading, L2 design section 2, fixed before the run\n")
    verdict = {}
    for name, _ in MEASURES:
        gaps = {}
        for seg, _, _ in SEGMENTS:
            t = res[name][seg]["table"]
            xs = [t[c + "/" + g] - t[c + "/C"]
                  for c in ("N", "P") for g in ("G1", "G2", "G3")
                  if t.get(c + "/" + g) is not None and t.get(c + "/C") is not None]
            gaps[seg] = xs
        rl, pl = gaps["real"], gaps["placebo"]
        if not rl or not pl:
            print("  %-13s not enough cells" % name)
            continue
        moved = sum(1 for x in rl if abs(x) > max(abs(y) for y in pl))
        print("  %-13s real gaps %s" % (name, "  ".join("%+.4f" % x for x in rl)))
        print("  %-13s placebo   %s" % ("", "  ".join("%+.4f" % x for x in pl)))
        print("  %-13s %d of %d real gaps exceed every placebo gap"
              % ("", moved, len(rl)))
        verdict[name] = {"real": rl, "placebo": pl, "beyond_placebo": moved,
                         "n_real": len(rl)}
        print("")
    tot = sum(v["beyond_placebo"] for v in verdict.values())
    print("  across the three measures, %d of %d treated-minus-control gaps sit"
          % (tot, sum(v["n_real"] for v in verdict.values())))
    print("  outside the whole placebo range.\n")
    print("  zero of them  -> pure arithmetic; candidates two, three and four fall,")
    print("                   the residue is candidate zero, and L2 closes here")
    print("  some of them  -> behaviour moved; go to gate two. Candidate zero is")
    print("                   NOT withdrawn, it already holds on bin 1")
    print("  the placebo itself spread wide -> that measure is unusable, say so")
    json.dump({"verdict": verdict, "tables": res}, open(OUT, "w"), indent=2)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("the segments are A11's own, real and placebo",
        SEGMENTS[0][0] == "real" and SEGMENTS[0][1] == ("201608", "201609")
        and SEGMENTS[0][2] == ("201611", "201612")
        and SEGMENTS[1][2] == ("201608", "201609"))
    chk("the placebo lies wholly before the pilot took effect on 2016-10-03",
        max(SEGMENTS[1][1] + SEGMENTS[1][2]) < "201610")
    chk("the real segment straddles it",
        min(SEGMENTS[0][1]) < "201610" < max(SEGMENTS[0][2]))
    chk("the three measures are the ones the design file registered",
        [m[0] for m in MEASURES] == ["mm_count", "share_prtcp", "inside_quote"])
    chk("the inside-quote measure is there, since the Rule 6191 exemptions are "
        "exactly the order types that sit inside a nickel quote",
        "INSD_QT_SHR_PRTCP_BUY" in dict(MEASURES)["inside_quote"])
    chk("B.IV is used as an outcome and never as an exposure: no overlap or "
        "similarity is computed here",
        not ({n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
             & {"exposure", "overlap", "similarity", "peers"}))
    # The point is that this file defines no copy of any of them, not that they
    # all live in one module: median is b14_gate0's and reaches here through
    # b14_recheck, which is the original rather than a copy. The first version of
    # this check demanded one module for all three and failed on a true statement.
    mine = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
    chk("this file defines no copy of the borrowed helpers: " +
        (", ".join(sorted(mine & {"median", "load_raw", "group_of", "six",
                                  "tabulate", "deltas_by"})) or "zero"),
        not (mine & {"median", "load_raw", "group_of", "six", "tabulate", "deltas_by"}))
    chk("and each borrowed helper is the original: median from %s, load_raw from "
        "%s, group_of from %s" % (R.median.__module__, R.load_raw.__module__,
                                  R.group_of.__module__),
        R.median.__module__ == "b14_gate0"
        and R.load_raw.__module__ == R.__name__
        and R.group_of.__module__ == R.__name__)
    chk("the nickel constant comes from there too", R.NICKEL == 0.05)
    chk("a symbol needs enough days on both sides, so a one-day cell cannot set "
        "a median", MIN_DAYS >= 10)
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    chk("no deletion call anywhere",
        not [1 for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and (n.func.value.id, n.func.attr) in banned])
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
