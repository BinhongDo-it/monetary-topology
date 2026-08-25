#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B16, third criterion: the cross-sectional SLOPE instead of the level.

Pre-registered: this is the third criterion, fixed before the run and not
changed after it. This file only executes it.

WHY A THIRD CRITERION
=====================
The first criterion is the before/after ratio of a cross-sectional
median, and section 12.4 measured what that fights: the common market drift
pushes the placebo band out to +-0.0155 while the fee is worth about 1% of the
friction, so gate two fails on all six arms by two to four times.

The fee is a RELATIVE charge, so it adds the same dr to every symbol's relative
spread. The denominator it lands in does not: the friction varies by about seven
times across this universe. So the same fee change is a seven times larger
relative shock to a tight-spread name than to a wide one, while the common drift
is the same for both. Regress the per-symbol response on 1/friction and the
drift goes into the intercept.

    y_i = log(rho_post,i / rho_pre,i)
    x_i = 1 / friction_i          measured on the REFERENCE window
    y   = -2*dr * x + intercept

    framework   slope = -2*dr = +2.98e-5 on e5
    rival       slope = 0

The 2 in 2*dr is the number of venues, each of whose relative spread takes dr.

x COMES FROM THE REFERENCE WINDOW AND NOT THE PRE WINDOW. The pre window is half
of y; regressing y on something built from it is category error fourteen, and
the first criterion's rule 4 already uses the reference window for exactly this
reason.

The band is built the same way as the first criterion's: the twenty placebo
sub-windows each give a slope, and the band is their 10-90 percentile. No extra
data, no random numbers.

Also printed, with no threshold on it: the MEDIAN of the twenty placebo slopes.
Far from zero means friction correlates with rho's own drift and the slope is
biased. The band construction catches it; nothing separate is added.

    python experiments/b16_slope.py --selftest
    python experiments/b16_slope.py --run
"""

import argparse
import ast
import importlib.util
import io
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "b16_e5_slope.json")


def _rho_module():
    spec = importlib.util.spec_from_file_location(
        "b16rho", os.path.join(HERE, "b16_rho.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.FILL[0] = True          # section 12.2: the un-filled mask counts updates
    return m


def ols(x, y):
    """slope and intercept, and None when the design is not identified."""
    n = len(x)
    if n < 3:
        return None
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    mx, my = x.mean(), y.mean()
    sxx = float(((x - mx) ** 2).sum())
    if sxx <= 0:
        return None
    b = float(((x - mx) * (y - my)).sum()) / sxx
    return b, float(my - b * mx)


def per_symbol_logR(R, syms, days, k, M):
    """y_i for one boundary offset k, using the module's own window logic."""
    pre, post = M.window_for(days, M.BOUNDARY, k)
    a = M.window_median_per_symbol(R, syms, pre)
    b = M.window_median_per_symbol(R, syms, post)
    out = {}
    for s in sorted(set(a) & set(b)):
        if a[s] > 0 and b[s] > 0:
            out[s] = math.log(b[s] / a[s])
    return out


def run():
    M = _rho_module()
    days = M.load_calendar()
    uni = M.load_universe()
    syms = sorted(M.arm_symbols(uni["events"][str(M.ARM)]))
    print("B16 arm e%d  slope criterion  boundary %s  dr %+.2fe-6  %d symbols"
          % (M.ARM, M.BOUNDARY, M.DR * 1e6, len(syms)))
    print("carry_forward=True (section 12.2)\n")

    rho, denom, _relsum, n_pair, n_viol, states = M.scan_fill(days, set(syms))
    print("\n  paired seconds %d   distinct states %d   outside domain %d"
          % (n_pair, sum(states.values()), n_viol))

    # ---- x from the REFERENCE window, never the pre window
    ref = M.offsets_to_days(days, M.BOUNDARY, *M.REF_WINDOW)
    x = {}
    for s in syms:
        parts = [denom[(s, d)] for d in ref if (s, d) in denom]
        if not parts:
            continue
        f = float(np.mean(np.concatenate(parts)))
        if f > 0:
            x[s] = 1.0 / f
    fr = sorted(1.0 / v for v in x.values())
    n = len(fr)
    print("\n  friction on the reference window, %d symbols" % n)
    print("    min %.6f  p10 %.6f  median %.6f  p90 %.6f  max %.6f"
          % (fr[0], fr[int(n * .1)], fr[n // 2], fr[int(n * .9)], fr[-1]))
    print("    p90/p10 = %.2f     effect 2|dr|/friction: median %.4f%%,"
          " p10 %.4f%%, p90 %.4f%%"
          % (fr[int(n * .9)] / fr[int(n * .1)],
             100 * 2 * abs(M.DR) / fr[n // 2],
             100 * 2 * abs(M.DR) / fr[int(n * .9)],
             100 * 2 * abs(M.DR) / fr[int(n * .1)]))

    pred = -2.0 * M.DR
    print("\n=== PLACEBO BAND (printed before the reading) ===")
    rows = []
    for k in list(M.PLACEBO_PRE) + list(M.PLACEBO_POST):
        y = per_symbol_logR(rho, syms, days, k, M)
        common = sorted(set(y) & set(x))
        r = ols([x[s] for s in common], [y[s] for s in common])
        if r is None:
            continue
        rows.append((k, r[0], r[1], len(common)))
        print("  offset %+3d   slope %+.6e   intercept %+.6f   n %d"
              % (k, r[0], r[1], len(common)))
    vals = [r[1] for r in rows]
    blo, bhi = M.band(vals)
    half = 0.5 * (bhi - blo)
    med = float(np.median(vals))
    print("\n  %d placebo slopes, %g-%g band  [%+.6e, %+.6e]  half %.6e"
          % (len(vals), M.BAND_LO, M.BAND_HI, blo, bhi, half))
    print("  placebo median %+.6e   (far from zero = friction correlates with"
          " rho's own drift; no threshold is drawn on this)" % med)

    y0 = per_symbol_logR(rho, syms, days, 0, M)
    common = sorted(set(y0) & set(x))
    real = ols([x[s] for s in common], [y0[s] for s in common])
    print("\n=== READING ===")
    print("  slope %+.6e   intercept %+.6f   n %d" % (real[0], real[1], len(common)))
    print("  framework predicts %+.6e   rival predicts 0" % pred)
    out = real[0] < blo or real[0] > bhi
    same = (real[0] > 0) == (pred > 0)
    cell = "A" if (out and same) else ("C" if out else "B")
    print("  outside the band: %s     sign matches the framework: %s" % (out, same))
    print("  CELL %s   (A framework, B undecidable, C rival)" % cell)

    sd = half / 1.2816
    print("\n=== GATE TWO, on the slope ===")
    print("  band half %.6e -> sd %.6e -> Z90*sd %.6e" % (half, sd, 1.645 * sd))
    print("  threshold |2*dr| %.6e   ratio %.3f   %s"
          % (abs(pred), 1.645 * sd / abs(pred),
             "PASS, the instrument resolves it"
             if 1.645 * sd / abs(pred) < 1.0 else
             "FAIL, the instrument does not resolve it"))

    json.dump({"arm": M.ARM, "boundary": M.BOUNDARY, "dr": M.DR,
               "criterion": "cross-sectional slope of log R on 1/friction",
               "x_window": "reference", "carry_forward": True,
               "n_symbols": len(common), "paired_seconds": n_pair,
               "distinct_states": sum(states.values()),
               "domain_excluded": n_viol,
               "predicted_slope": pred,
               "placebo": [{"offset": k, "slope": b, "intercept": a, "n": m}
                           for k, b, a, m in rows],
               "placebo_median_slope": med,
               "band": [blo, bhi], "band_half_width": half,
               "reading": {"slope": real[0], "intercept": real[1],
                           "n": len(common)},
               "cell": cell,
               "gate_two_ratio": 1.645 * sd / abs(pred)},
              open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
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

    b, a = ols([1.0, 2.0, 3.0, 4.0], [3.0, 5.0, 7.0, 9.0])
    chk("ols recovers a planted slope and intercept",
        abs(b - 2.0) < 1e-12 and abs(a - 1.0) < 1e-12)
    chk("ols declines a design with no spread in x",
        ols([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None)

    #: the whole point: a common additive drift must not move the slope
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0 * v for v in x]
    b0, _ = ols(x, y)
    b1, a1 = ols(x, [v + 7.0 for v in y])
    chk("a drift common to every symbol lands in the intercept, not the slope",
        abs(b0 - b1) < 1e-12 and abs(a1 - 7.0) < 1e-12)

    #: and a drift proportional to x DOES move it, which is the bias the placebo
    #: median is printed to expose
    b2, _ = ols(x, [v + 0.5 * xx for v, xx in zip(y, x)])
    chk("a drift proportional to x does move the slope, which is why the "
        "placebo median is printed", abs(b2 - 2.5) < 1e-12)

    M = _rho_module()
    chk("the criterion registers -2*dr and dr is the registered e5 value",
        abs(M.DR - (-14.90e-6)) < 1e-18 and abs(-2.0 * M.DR - 2.98e-5) < 1e-12)
    chk("twenty placebo offsets, ten a side, same as the first criterion",
        len(M.PLACEBO_PRE) == 10 and len(M.PLACEBO_POST) == 10)
    chk("x is taken from the reference window and it does not overlap pre",
        M.REF_WINDOW == (-20, -11))
    chk("the module is driven with the carry on", M.FILL[0] is True)

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
