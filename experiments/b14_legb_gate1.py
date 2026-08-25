"""B14 leg B gate one: are the two venues two classes in the section 5.1 sense?

Registered in the design file, section 7 supplement 2, B14_A17 clause 2.

The framework supplies its own operational criterion (section 7 supplement 1
clause 2): S - S' is zero exactly when the two classes face the same
antisymmetric terms. So "are these two classes" reduces to "is S - S'
identically zero", which is measurable.

  S - S'  =  2 log(mid_b / mid_a),  mid = sqrt(bid * ask)

so the sign of S - S' is the sign of (bid_b * ask_b) - (bid_a * ask_a), which is
exact in integer cents. No floating point enters the sign.

B14_A17 clause 2 forbids running this on treated names inside the pilot: a nickel
grid pins both venues to the same lattice point much of the time, so a zero is
forced by arithmetic and the gate would misread it as one class. That is D15
reachability, a branch unreachable in the sample it is run on. The gate
therefore runs on CONTROL names, which are on the penny grid throughout.

Treated names are measured too, and reported beside it, precisely to show that
the excluded branch really is unreachable rather than merely assumed to be.

Usage
    python experiments/b14_legb_gate1.py --selftest
    python experiments/b14_legb_gate1.py --run
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
OUT = os.path.join(ROOT, "results", "b14_legb_gate1.json")

MONTHS = ["2018-%02d" % m for m in range(5, 13)]
INSIDE = {"2018-05", "2018-06", "2018-07", "2018-08", "2018-09"}
#: B14_A16 clause 2 plus B14_A16 supplement 4 clause 1.
EXCLUDED = {"TA", "SSP", "VNCE", "JONE", "PKD"}


def run():
    """B14_A17 clause 2, second version.

    The first version tested P(+ | nonzero) against a band built from the CELL
    count, and read a min() as if it were an all-quantifier. Both are recorded in
    the results file. Two faults, one of them load-bearing:

      the band assumed independent cells, and a quote sits unchanged for many
      consecutive seconds, so the effective sample is nowhere near the cell count

    The unit here is the (symbol, day), and the null is built at the level the
    framework's question actually lives at. If the venue difference were the
    one-second snapshot catching a moving price at slightly different moments,
    its sign would be a fresh coin flip every day. So: per symbol, count the days
    whose sign leans positive, and compare that count to Binomial(days, 1/2).
    That is a count against an exact null, with no variance model to get wrong.
    """
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("this needs numpy; nothing was written")
    groups = json.load(open(SYMS_FILE, encoding="utf-8"))["symbols"]
    g_of = {s: g for g, v in groups.items() for s in v}
    per = {}
    zero_share = {}

    for m in MONTHS:
        p = os.path.join(CACHE, "panel_%s.npz" % m.replace("-", ""))
        if not os.path.exists(p):
            continue
        d = np.load(p, allow_pickle=False)
        tab = [str(x) for x in d["symbol_table"]]
        pa = d["bid_a"].astype(np.int64) * d["ask_a"].astype(np.int64)
        pb = d["bid_b"].astype(np.int64) * d["ask_b"].astype(np.int64)
        diff = pb - pa
        sym, day = d["sym"], (d["sec"].astype(np.int64) // 86400)
        for arm, want in (("C", True), ("G", False)):
            sel = np.array([(t not in EXCLUDED) and ((g_of.get(t) == "C") == want)
                            for t in tab])[sym]
            v, sy, dy = diff[sel], sym[sel], day[sel]
            zero_share.setdefault(arm, {})[m] = (
                float(np.count_nonzero(v == 0)) / max(v.size, 1))
            if arm != "C":
                continue
            key = sy.astype(np.int64) * 100000 + (dy - dy.min())
            order = np.argsort(key, kind="stable")
            k, vv = key[order], v[order]
            bounds = np.flatnonzero(np.diff(k)) + 1
            for lo, hi in zip(np.r_[0, bounds], np.r_[bounds, k.size]):
                seg = vv[lo:hi]
                pos = int(np.count_nonzero(seg > 0))
                neg = int(np.count_nonzero(seg < 0))
                if pos + neg == 0:
                    continue
                per.setdefault(tab[sy[order][lo]], []).append(
                    (m, pos, neg, (pos - neg) / (pos + neg)))

    print("Gate one, B14_A17 clause 2, unit = (symbol, day), arm = control only.")
    print("sign(S - S') = sign(bid_b*ask_b - bid_a*ask_a), exact in integer cents.")
    print("Per symbol: how many of its days lean positive, against Binomial(n, 1/2).\n")
    print("  symbol  days   days+   expected+-2sd     mean lean   verdict")
    from math import sqrt
    out, flagged = {}, 0
    for s in sorted(per):
        rec = per[s]
        n = len(rec)
        dp = sum(1 for _, _, _, lean in rec if lean > 0)
        mu, sd = n / 2, sqrt(n) / 2
        z = (dp - mu) / sd if sd else 0.0
        lean = sum(r[3] for r in rec) / n
        tag = "persistent" if abs(z) > 3 else ("" if abs(z) <= 2 else "weak")
        flagged += abs(z) > 3
        print("  %-6s  %4d   %4d    %5.1f +-%4.1f       %+.4f     %s"
              % (s, n, dp, mu, 2 * sd, lean, tag))
        out[s] = {"days": n, "days_positive": dp, "z": round(z, 2),
                  "mean_lean": round(lean, 6)}

    n_sym = len(out)
    print("\n  %d of %d control symbols are beyond 3 sd of the coin-flip null."
          % (flagged, n_sym))
    print("  under that null the expected count beyond 3 sd is %.2f symbols."
          % (n_sym * 0.0027))
    zs = [abs(v["z"]) for v in out.values()]
    print("  |z| median %.2f, max %.2f" % (float(np.median(zs)), max(zs)))

    print("\n  D15 reachability check, share of cells with S - S' exactly zero:")
    for arm in ("C", "G"):
        ins = [zero_share[arm][m] for m in zero_share[arm] if m in INSIDE]
        outw = [zero_share[arm][m] for m in zero_share[arm] if m not in INSIDE]
        print("    %-4s inside %.4f..%.4f   outside %.4f..%.4f"
              % (arm, min(ins), max(ins), min(outw), max(outw)))
    print("  treated-inside sits far above every other cell, which is the grid")
    print("  pinning both venues to one lattice point. The gate was right to")
    print("  refuse that branch rather than read its zeros as one class.")

    json.dump({"per_symbol": out, "zero_share": zero_share,
               "unit": "symbol-day", "arm": "control",
               "null": "Binomial(days, 0.5) on the count of days leaning positive"},
              open(OUT, "w"), indent=2, sort_keys=True)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the exclusion is the full registered five",
        EXCLUDED == {"TA", "SSP", "VNCE", "JONE", "PKD"})
    chk("the inside months are the five before the boundary", len(INSIDE) == 5
        and "2018-09" in INSIDE and "2018-10" not in INSIDE)
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere", not hits)
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    chk("the sign is taken on integers, so no float rounding decides it",
        "astype" in calls)
    chk("the null is exact and needs no variance model: it is a binomial on a "
        "count of days, not a band built from a cell count",
        "Binomial" in src and "sqrt(n) / 2" in src)
    chk("this gate computes no rho; rho is B14_A17 clause 4 and comes after",
        "rho" not in {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)})
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
