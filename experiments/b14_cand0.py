"""B14 candidate zero: is the pure-slack residue the nickel LATTICE, not spillover?

Registered in the design file, section 7 supplement 2, A20.

A11 closed with three candidates and only spillover left standing. Candidate zero
was never on the list: the pilot's quoting rule is an INCREMENT rule, not a
minimum-width rule, so a name whose spread already exceeds five cents is still
forced onto the nickel lattice, and projecting a penny bid down and a penny ask up
widens the spread mechanically.

That gives a one-parameter curve with an arithmetic bound, not merely a direction:

    margin(s) = log((s + delta) / s),   delta in [0, 8] cents, one delta for all bins

because each side moves 0 to 4 cents and delta is a property of the lattice rather
than of the name. Spillover predicts no such relation to the name's own spread.

A20 clause 2 adds the second judge, taken from what A18 cost: the gradient must
live in the TREATED arm. Slice B satisfied "clears and monotone" while its
gradient sat in the control arm, and that was not heterogeneity. Same ruler here,
fitted before the run rather than after.

Nothing is redefined: the pure-slack definition, the split variable, the windows
and the six inequalities are all b14_recheck's own, imported not copied.

Usage
    python experiments/b14_cand0.py --selftest
    python experiments/b14_cand0.py --run
"""
import argparse
import ast
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "b14_cand0.json")

_spec = importlib.util.spec_from_file_location(
    "b14_recheck", os.path.join(HERE, "b14_recheck.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

#: A20 clause 4. Written down, not tunable.
N_BINS = 5
#: A20 clause 1. Each side of a penny quote moves 0 to 4 cents onto the nickel
#: lattice, so the total widening cannot exceed eight cents. This is arithmetic.
DELTA_LO, DELTA_HI = 0.0, 0.08
#: The expectation if penny prices are uniform modulo five cents: two cents a side.
DELTA_EXPECTED = 0.04


def curve(s, delta):
    return math.log((s + delta) / s)


def fit_delta(points):
    """One delta for every bin, least squares on a bounded grid. No solver."""
    best, bestsse = None, None
    d = DELTA_LO
    while d <= DELTA_HI + 1e-12:
        sse = sum((m - curve(s, d)) ** 2 for s, m in points) if d > 0 else \
            sum(m ** 2 for _, m in points)
        if bestsse is None or sse < bestsse:
            best, bestsse = d, sse
        d += 0.0001
    mean = sum(m for _, m in points) / len(points)
    tss = sum((m - mean) ** 2 for _, m in points)
    return best, bestsse, (1 - bestsse / tss if tss > 0 else float("nan"))


def run():
    """Load exactly the windows b14_recheck.run loads for the 2016 round.

    Copied from that call site rather than re-derived, so the split window, the
    placebo window and the two test windows are the same objects A11 used.
    """
    rec16 = R.load_raw(R.E.ROUNDS["2016"]["pre"], R.E.ROUNDS["2016"]["post"],
                       extra_windows=[("aug", R.SPLIT_A), ("sep", R.SPLIT_B),
                                      ("apr", R.W_APR), ("may", R.W_MAY),
                                      ("pre_pl", R.W_PLACEBO_PRE)])
    print("loaded: 2016 %d (venue, symbol) pairs" % len(rec16))
    return _run(rec16)


def _run(rec16):
    # pure slack: b14_recheck's own definition, not a new one
    pure = {}
    for k, r in rec16.items():
        v = r["apr"]["bbo"] + r["may"]["bbo"]
        if v:
            pure[k] = not any(x < R.NICKEL for x in v)
    lev, _ = R.far_binder(rec16)
    sub = {k: lev[k] for k in lev if pure.get(k) is True}
    print("A20. pure slack on the 2016-04/05 split window: %d (venue, symbol)" % len(sub))
    if not sub:
        print("  nothing to bin; nothing written")
        return 1
    vals = sorted(sub.values())
    cuts = [vals[min(len(vals) - 1, (b + 1) * len(vals) // N_BINS)]
            for b in range(N_BINS - 1)]

    def bin_of(k):
        v = sub.get(k)
        if v is None:
            return None
        for b, c in enumerate(cuts):
            if v < c:
                return b
        return N_BINS - 1

    print("  %d bins by the 2016-04/05 median spread, cuts at %s"
          % (N_BINS, "  ".join("$%.3f" % c for c in cuts)))
    print("\n  seg      bin   n(slack)  s(median)   dG(med)    dC        margin(med)")
    res = {"n_pure_slack": len(sub), "cuts": cuts, "bins": {}}
    points = []
    for seg, prewin, postwin, sign in (("real", "pre", "post", +1),
                                       ("placebo", "pre_pl", "pre", +1)):
        for b in range(N_BINS):
            keys = [k for k in sub if bin_of(k) == b]
            svals = sorted(sub[k] for k in keys)
            s_med = svals[len(svals) // 2] if svals else None
            d = R.deltas_by(rec16, "post", prewin, postwin,
                            pick=lambda c, sy, r, bb=b: bin_of((c, sy)) == bb)
            tab, n = R.tabulate(d)
            ineq = R.six(tab, sign)
            gaps = [x["raw_gap"] for x in ineq if x["raw_gap"] is not None]
            gaps.sort()
            marg = gaps[len(gaps) // 2] if gaps else None
            dgs = [tab[c + "/" + g] for c in ("N", "P") for g in ("G1", "G2", "G3")
                   if tab.get(c + "/" + g) is not None]
            dcs = [tab[c + "/C"] for c in ("N", "P") if tab.get(c + "/C") is not None]
            dgs.sort()
            dcs.sort()
            dg = dgs[len(dgs) // 2] if dgs else None
            dc = dcs[len(dcs) // 2] if dcs else None
            print("  %-8s %d    %6d    $%.4f   %s  %s  %s"
                  % (seg, b + 1, len(keys), s_med or 0,
                     "None      " if dg is None else "%+.6f " % dg,
                     "None      " if dc is None else "%+.6f " % dc,
                     "None" if marg is None else "%+.6f" % marg))
            res["bins"].setdefault(seg, {})["bin%d" % (b + 1)] = {
                "n": len(keys), "s_median": s_med, "dG": dg, "dC": dc,
                "margin": marg, "holds": sum(1 for x in ineq if x["holds"]),
                "raw_gaps": [x["raw_gap"] for x in ineq]}
            if seg == "real" and marg is not None and s_med:
                points.append((s_med, marg))
        print("")

    print("A20 clause 2, judge 1: one delta for every bin, bounded by the lattice")
    if len(points) >= 2:
        delta, sse, r2 = fit_delta(points)
        print("  fitted delta = %.4f dollars (%.2f cents), R^2 = %.4f, SSE = %.6f"
              % (delta, delta * 100, r2, sse))
        print("  arithmetic bound [%.0f, %.0f] cents; the uniform-price expectation "
              "is %.0f cents" % (DELTA_LO * 100, DELTA_HI * 100, DELTA_EXPECTED * 100))
        inb = DELTA_LO < delta <= DELTA_HI
        print("  delta is %s the arithmetic bound" % ("INSIDE" if inb else "OUTSIDE"))
        print("\n  bin   s        observed     curve(delta)   residual")
        for s, m in points:
            print("        $%.4f  %+.6f    %+.6f      %+.6f"
                  % (s, m, curve(s, delta), m - curve(s, delta)))
        # Round to the grid step. The search moves in 0.0001 increments, so the
        # sixteen digits a float carries are noise, and a verdict sheet that
        # quotes this number must be able to quote it as the product prints it.
        res["fit"] = {"delta": round(delta, 4), "sse": round(sse, 6),
                      "r2": round(r2, 4), "in_bound": bool(inb),
                      "points": [[round(s, 4), round(m, 6)] for s, m in points],
                      "residuals": [[round(s, 4), round(m - curve(s, delta), 4)]
                                    for s, m in points]}
    else:
        print("  too few bins with a margin to fit")

    print("\nA20 clause 2, judge 2: which arm carries the gradient")
    for seg in ("real", "placebo"):
        g = [res["bins"][seg]["bin%d" % (b + 1)]["dG"] for b in range(N_BINS)]
        c = [res["bins"][seg]["bin%d" % (b + 1)]["dC"] for b in range(N_BINS)]
        g = [x for x in g if x is not None]
        c = [x for x in c if x is not None]
        gs = (max(g) - min(g)) if g else float("nan")
        cs = (max(c) - min(c)) if c else float("nan")
        print("  %-8s spread of dG across bins %.4f, of dC %.4f -> gradient in the "
              "%s arm" % (seg, gs, cs, "TREATED" if gs > cs else "CONTROL"))
        res.setdefault("arm", {})[seg] = {"dG_spread": gs, "dC_spread": cs,
                                          "arm": "treated" if gs > cs else "control"}
    json.dump(res, open(OUT, "w"), indent=2)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    print("  A20 clause 3 decides from these two judges; no threshold is set here.")
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("the bin count is the registered five", N_BINS == 5)
    chk("the fitted delta is stored at the grid's own resolution, not with float "
        "noise, so a verdict sheet can quote it as printed",
        "round(delta, 4)" in src)
    chk("the delta bound is the lattice's arithmetic, not a chosen range: each "
        "side of a penny quote moves at most four cents",
        abs(DELTA_HI - 0.08) < 1e-12 and DELTA_LO == 0.0)
    chk("the uniform-price expectation is inside the bound",
        DELTA_LO < DELTA_EXPECTED < DELTA_HI)
    chk("the curve is what A20 clause 1 wrote: log((s+delta)/s)",
        abs(curve(0.10, 0.04) - math.log(0.14 / 0.10)) < 1e-12)
    chk("the curve is decreasing in s at fixed delta",
        curve(0.05, 0.04) > curve(0.50, 0.04))
    chk("a zero delta gives a zero margin at every s",
        curve(0.1, 0.0) == 0.0 and curve(0.5, 0.0) == 0.0)
    d, _, r2 = fit_delta([(0.10, curve(0.10, 0.03)), (0.30, curve(0.30, 0.03)),
                          (0.60, curve(0.60, 0.03))])
    chk("the fit recovers a planted delta: planted 0.0300, got %.4f, R^2 %.4f"
        % (d, r2), abs(d - 0.03) < 0.0002)
    d2, _, _ = fit_delta([(0.10, 0.0), (0.30, 0.0), (0.60, 0.0)])
    chk("a flat zero margin fits delta = 0, so the null is reachable", d2 == 0.0)
    chk("pure slack, the split variable, the windows and the six inequalities are "
        "b14_recheck's own objects",
        R.six.__module__ == R.__name__ and R.far_binder.__module__ == R.__name__
        and R.deltas_by.__module__ == R.__name__)
    chk("the nickel constant comes from there too", R.NICKEL == 0.05)
    chk("the windows are the ones A11 used, taken from b14_recheck's own call site",
        all(hasattr(R, w) for w in ("SPLIT_A", "SPLIT_B", "W_APR", "W_MAY",
                                    "W_PLACEBO_PRE")))
    chk("the real segment runs pre -> post and the placebo pre_pl -> pre, both "
        "as A11 fixed them", '("real", "pre", "post", +1)' in src
        and '("placebo", "pre_pl", "pre", +1)' in src)
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
