#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B16: can the level criterion's noise be bought down, and by what?

Two criteria have now failed gate two on this carrier: the level at 2.08 and
the slope at 5.28. The level is the closer one, so the question left is whether
its band can be narrowed, and the two ways to try are more DAYS and more
SYMBOLS. Both cost money, and both can be priced before spending any, which is
gate five's shape.

    lever B, days     how does sd(log R) scale with the window length T?
                      T^(-1/2) means buying days works and says how many.
                      Flat means low-frequency drift dominates and days are
                      wasted. The bought window is 29+29, so T up to 25 needs
                      no purchase at all.

    lever C, symbols  the band mixes two things: the COMMON drift of rho, and
                      the sampling error of the cross-sectional median. The
                      second one shrinks as 1/sqrt(N) and the first does not.
                      Inside each placebo window the per-symbol spread of y_i
                      gives the median's own se directly, so the split is
                      measurable without buying a single extra symbol.

Nothing here is a criterion. Both outputs are numbers with a reading attached,
and the reading is about what to buy, not about the world.

Reads the reusable cache, so it costs seconds:
    python experiments/b16_rho.py --cache        one gz pass, once
    python experiments/b16_levers.py --run
"""

import argparse
import ast
import importlib.util
import io
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _M():
    spec = importlib.util.spec_from_file_location(
        "b16rho", os.path.join(HERE, "b16_rho.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_cache(M):
    z = np.load(M.NPZ, allow_pickle=False)
    keys = [tuple(k.split("|")) for k in z["keys"]]
    lens = z["lens"]
    rho, off = {}, 0
    for k, n in zip(keys, lens):
        rho[k] = z["rho"][off:off + n]
        off += n
    return rho


def med_by_symbol(rho, syms, wdays):
    out = {}
    for s in syms:
        parts = [rho[(s, d)] for d in wdays if (s, d) in rho]
        if parts:
            out[s] = float(np.median(np.concatenate(parts)))
    return out


def log_R(rho, syms, days, M, k, half):
    """log ratio of the cross-sectional median, with a half-window of `half`
    trading days a side, at boundary offset k. Also returns the per-symbol
    values, which lever C needs."""
    lo = M.offsets_to_days(days, M.BOUNDARY, k - half, k - 1)
    hi = M.offsets_to_days(days, M.BOUNDARY, k, k + half - 1)
    a, b = med_by_symbol(rho, syms, lo), med_by_symbol(rho, syms, hi)
    common = [s for s in sorted(set(a) & set(b)) if a[s] > 0 and b[s] > 0]
    if len(common) < 5:
        return None
    per = {s: math.log(b[s] / a[s]) for s in common}
    va = float(np.median([a[s] for s in common]))
    vb = float(np.median([b[s] for s in common]))
    return math.log(vb / va), per


def run():
    M = _M()
    if not os.path.exists(M.NPZ):
        sys.stderr.write("no cache; run b16_rho.py --cache first\n")
        return 1
    rho = load_cache(M)
    uni = M.load_universe()
    days = M.load_calendar()
    syms = sorted(M.arm_symbols(uni["events"][str(M.ARM)]))
    thr = 2.0 * abs(M.DR) / 0.003114          # section 12.4's threshold, 0.957%
    print("B16 arm e%d   %d symbols   threshold 2|dr|/friction = %.5f"
          % (M.ARM, len(syms), thr))
    print("cache %s\n" % os.path.relpath(M.NPZ, ROOT))

    print("=== LEVER B: does the band shrink with the window length? ===")
    print("  %4s %7s %13s %13s %9s %9s"
          % ("T", "windows", "sd(log R)", "Z90*sd", "ratio", "vs T^-1/2"))
    base = None
    for T in (5, 10, 15, 20, 25):
        offs = [k for k in range(-29 + T, 30 - T) if abs(k) >= T]
        vals = []
        for k in offs:
            r = log_R(rho, syms, days, M, k, T)
            if r:
                vals.append(r[0])
        if len(vals) < 6:
            print("  %4d %7d   too few placebo windows to read" % (T, len(vals)))
            continue
        sd = float(np.std(vals, ddof=1))
        if base is None:
            base = (T, sd)
        pred = base[1] * math.sqrt(base[0] / float(T))
        print("  %4d %7d %13.6f %13.6f %9.3f %9.6f"
              % (T, len(vals), sd, 1.645 * sd, 1.645 * sd / thr, pred))
    print("  the last column is what T^(-1/2) from the first row would give.")
    print("  sd tracking it means days buy power; sd flat means they do not.")

    print("\n=== LEVER C: is the band common drift or the median's own error? ===")
    print("  %4s %13s %13s %9s" % ("T", "sd(log R)", "se(median)", "share"))
    for T in (5, 10, 20):
        offs = [k for k in range(-29 + T, 30 - T) if abs(k) >= T]
        vals, ses = [], []
        for k in offs:
            r = log_R(rho, syms, days, M, k, T)
            if not r:
                continue
            vals.append(r[0])
            y = np.asarray(list(r[1].values()), np.float64)
            #: se of a median, the standard 1.2533/sqrt(N) times the spread
            ses.append(1.2533 * float(np.std(y, ddof=1)) / math.sqrt(len(y)))
        if len(vals) < 6:
            continue
        sd = float(np.std(vals, ddof=1))
        se = float(np.mean(ses))
        print("  %4d %13.6f %13.6f %9.3f" % (T, sd, se, (se / sd) ** 2))
    print("  share = (se/sd)^2, the part of the band that more SYMBOLS can buy.")
    print("  near 1 means the band is sampling error and N helps as 1/sqrt(N).")
    print("  near 0 means it is common drift and N buys nothing.")
    return 0


def selftest():
    n = 0

    def chk(label, cond):
        nonlocal n
        assert cond, label
        n += 1
        print("  ok  %s" % label)

    tree = ast.parse(io.open(os.path.abspath(__file__), encoding="utf-8").read())
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else \
                (f.id if isinstance(f, ast.Name) else "")
            if nm in ("remove", "unlink", "rmtree", "rmdir"):
                bad.add(nm)
    chk("nothing here deletes anything (AST walk)", not bad)

    rng = np.random.RandomState(7)
    #: pure sampling error: sd of the median over windows must match the
    #: within-window se, so lever C's share reads about 1
    y = rng.normal(0, 1, (400, 63))
    sd = float(np.std([np.median(r) for r in y], ddof=1))
    se = float(np.mean([1.2533 * np.std(r, ddof=1) / math.sqrt(63) for r in y]))
    chk("on pure sampling error lever C's share reads near 1",
        0.8 < (se / sd) ** 2 < 1.25)

    #: add a common shift per window and the share must fall
    y2 = y + rng.normal(0, 1.0, (400, 1))
    sd2 = float(np.std([np.median(r) for r in y2], ddof=1))
    se2 = float(np.mean([1.2533 * np.std(r, ddof=1) / math.sqrt(63) for r in y2]))
    chk("a common per-window shift pushes the share toward zero",
        (se2 / sd2) ** 2 < 0.2)

    chk("T^(-1/2) is what independent days would give",
        abs(1.0 * math.sqrt(5 / 20.0) - 0.5) < 1e-12)
    print("\nselftest: PASS  (%d checks)" % n)
    return 0


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
