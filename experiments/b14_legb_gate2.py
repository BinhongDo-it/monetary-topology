"""B14 leg B gate two: is the pre/post move in rho anything but the grid's arithmetic?

Registered in the design file, section 7 supplement 2, A17 clause 3 (part a) and
A17 supplement 1 (part b).

Part a, the quantisation counterfactual. The release takes treated names from a
nickel grid to a penny grid. Invariance predicts rho rises. Pure arithmetic may
also predict rho rises, because on a nickel grid the numerator can only take the
values 0, 2.5c, 5c and the denominator is pinned near 10c, so rho collapses onto
the atoms {0, 0.5, 1}. Same sign, so the raw pre/post comparison is not
adjudicable on its own (A17 clause 1).

The move that wins discriminating power is the one A10 used: do not argue about
whether the effect is mechanical, compute what the mechanical hypothesis itself
predicts and see whether the data separates from it. So: take the OUTSIDE cells,
project both venues' quotes onto the nickel grid the way the rule forces (bid
down, ask up), recompute rho, and ask how much of the inside/outside gap that
projection closes.

Part b, Theorem 6(5). S - S' splits exactly into a midpoint term and a spread
term, and the spread term is friction, not index. Both are reported.

Reads the cache only. Nothing is bought and nothing is written to the cache.

Usage
    python experiments/b14_legb_gate2.py --selftest
    python experiments/b14_legb_gate2.py --run
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
OUT = os.path.join(ROOT, "results", "b14_legb_gate2.json")

#: A16 clause 3, the balanced core window.
CORE_INSIDE, CORE_OUTSIDE = "2018-09", "2018-10"
#: A16 clause 2 plus A16 supplement 4 clause 1.
EXCLUDED = {"TA", "SSP", "VNCE", "JONE", "PKD"}
#: A16 supplement 1: the Nasdaq stub pair, dropped at the analysis layer.
STUB_BID_CENTS, STUB_ASK_CENTS = 1, 19999999
NICKEL_CENTS = 5


def stats(np, ba, aa, bb, ab):
    """rho and its two numerator terms, on integer-cent quotes."""
    ba, aa = ba.astype(np.float64), aa.astype(np.float64)
    bb, ab = bb.astype(np.float64), ab.astype(np.float64)
    num_signed = (np.log(bb) + np.log(ab)) - (np.log(ba) + np.log(aa))
    den = (np.log(aa) - np.log(ba)) + (np.log(ab) - np.log(bb))
    rho = np.abs(num_signed) / den
    Ma, Mb = (ba + aa) / 2, (bb + ab) / 2
    sa, sb = aa - ba, ab - bb
    t1 = 2 * (np.log(Mb) - np.log(Ma))
    t2 = np.log1p(-(sb / (2 * Mb)) ** 2) - np.log1p(-(sa / (2 * Ma)) ** 2)
    interior = (rho > 0) & (rho < 1)
    return {
        "n": int(rho.size),
        "share_rho0": float(np.mean(rho <= 0)),
        "share_rho1": float(np.mean(rho >= 1 - 1e-12)),
        "median_interior": float(np.median(rho[interior])) if interior.any() else float("nan"),
        "mean_rho": float(np.mean(rho)),
        "share_t2_dominates_nonzero": float(
            np.mean(np.abs(t2)[num_signed != 0] > np.abs(t1)[num_signed != 0]))
        if np.any(num_signed != 0) else float("nan"),
        "sum_abs_t2_over_sum_abs_t1_plus_t2": float(
            np.sum(np.abs(t2)) / max(np.sum(np.abs(t1)) + np.sum(np.abs(t2)), 1e-300)),
    }


def to_nickel(np, bid, ask):
    """Project onto the nickel grid the way the quoting rule forces it."""
    b = (bid // NICKEL_CENTS) * NICKEL_CENTS
    a = ((ask + NICKEL_CENTS - 1) // NICKEL_CENTS) * NICKEL_CENTS
    return b, a


def load(np, m, g_of, arm):
    p = os.path.join(CACHE, "panel_%s.npz" % m.replace("-", ""))
    d = np.load(p, allow_pickle=False)
    tab = [str(x) for x in d["symbol_table"]]
    want = (arm == "C")
    sel = np.array([(t not in EXCLUDED) and ((g_of.get(t) == "C") == want)
                    for t in tab])[d["sym"]]
    sel &= ~((d["bid_b"] == STUB_BID_CENTS) & (d["ask_b"] == STUB_ASK_CENTS))
    return (d["bid_a"][sel], d["ask_a"][sel], d["bid_b"][sel], d["ask_b"][sel])


def run():
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("this needs numpy; nothing was written")
    g_of = {s: g for g, v in
            json.load(open(SYMS_FILE, encoding="utf-8"))["symbols"].items() for s in v}
    res = {}
    print("Gate two. Core window %s (inside) against %s (outside), 103 symbols."
          % (CORE_INSIDE, CORE_OUTSIDE))
    print("'rounded' projects both venues onto the nickel grid, bid down and ask up.\n")
    print("  arm  month    variant    cells      rho=0     rho=1    med interior   mean rho")
    for arm in ("G", "C"):
        for m in (CORE_INSIDE, CORE_OUTSIDE):
            q = load(np, m, g_of, arm)
            for variant in ("actual", "rounded"):
                qq = q
                if variant == "rounded":
                    ba, aa = to_nickel(np, q[0].astype(np.int64), q[1].astype(np.int64))
                    bb, ab = to_nickel(np, q[2].astype(np.int64), q[3].astype(np.int64))
                    good = (ba > 0) & (bb > 0)
                    qq = (ba[good], aa[good], bb[good], ab[good])
                s = stats(np, *qq)
                res.setdefault(arm, {}).setdefault(m, {})[variant] = s
                print("  %-3s  %s  %-9s %8d   %.4f    %.4f      %.4f       %.4f"
                      % (arm, m, variant, s["n"], s["share_rho0"], s["share_rho1"],
                         s["median_interior"], s["mean_rho"]))
        print("")

    print("\npart a, A17 clause 3: how much of the gap does the grid's arithmetic close")
    print("  the statistic is the share of cells at rho = 0, which A17 clause 4 makes")
    print("  primary because rho carries a large atom there.\n")
    for arm in ("G", "C"):
        ins = res[arm][CORE_INSIDE]["actual"]["share_rho0"]
        out_a = res[arm][CORE_OUTSIDE]["actual"]["share_rho0"]
        out_r = res[arm][CORE_OUTSIDE]["rounded"]["share_rho0"]
        gap = out_a - ins
        left = out_r - ins
        closed = 1 - left / gap if gap else float("nan")
        print("  %-3s  inside actual %.4f   outside actual %.4f   outside ROUNDED %.4f"
              % (arm, ins, out_a, out_r))
        print("       raw gap %+.4f   gap left after rounding %+.4f   closed by arithmetic %.1f%%"
              % (gap, left, 100 * closed))
        res[arm]["gap_share_rho0"] = {"inside": ins, "outside": out_a,
                                      "outside_rounded": out_r, "raw_gap": gap,
                                      "residual_gap": left, "closed_fraction": closed}
    print("\n  reading, A17 clause 3, fixed before the run:")
    print("    rounded ~ inside  -> the whole move is the grid's arithmetic, leg B has")
    print("                        no discriminating power on this carrier, stop")
    print("    rounded != inside -> the residual is what arithmetic cannot make, and")
    print("                        that residual is what the main adjudication is about")

    print("\n\npart b, Theorem 6(5): how much of |S - S'| is the spread term, nonzero cells")
    print("\n  arm  month    variant    share |t2|>|t1|   sum|t2| / (sum|t1|+sum|t2|)")
    for arm in ("G", "C"):
        for m in (CORE_INSIDE, CORE_OUTSIDE):
            for variant in ("actual", "rounded"):
                s = res[arm][m][variant]
                print("  %-3s  %s  %-9s      %.4f              %.4f"
                      % (arm, m, variant, s["share_t2_dominates_nonzero"],
                         s["sum_abs_t2_over_sum_abs_t1_plus_t2"]))
        print("")
    json.dump(res, open(OUT, "w"), indent=2, sort_keys=True)
    print("  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    try:
        import numpy as np
    except ImportError:
        print("  numpy missing")
        return 1
    chk("the core window is the balanced pair A16 clause 3 fixed",
        (CORE_INSIDE, CORE_OUTSIDE) == ("2018-09", "2018-10"))
    chk("the exclusion is the registered five",
        EXCLUDED == {"TA", "SSP", "VNCE", "JONE", "PKD"})
    b, a = to_nickel(np, np.array([100, 101, 104, 105, 106]),
                     np.array([102, 103, 106, 110, 111]))
    chk("bid projects DOWN onto the nickel grid: " + str(b.tolist()),
        b.tolist() == [100, 100, 100, 105, 105])
    chk("ask projects UP onto the nickel grid: " + str(a.tolist()),
        a.tolist() == [105, 105, 110, 110, 115])
    chk("a projected quote never crosses or locks", bool((b < a).all()))
    chk("projection is idempotent on quotes already on the grid",
        to_nickel(np, np.array([105]), np.array([110]))[0].tolist() == [105]
        and to_nickel(np, np.array([105]), np.array([110]))[1].tolist() == [110])
    s = stats(np, np.array([100, 100]), np.array([105, 105]),
              np.array([100, 110]), np.array([105, 115]))
    chk("rho is 0 when the two venues quote identically", s["share_rho0"] >= 0.5)
    chk("rho never exceeds the Theorem 6(4) ceiling of one",
        s["share_rho1"] <= 1.0 and s["mean_rho"] <= 1.0)
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
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
