"""B16 step C: the same two readings taken across the cross-section instead of
across time.

The criteria were registered before the run. Prior step: b16_rho.py.

WHY THIS EXISTS

b16_rho.py judged both halves against a placebo band built from time-series
windows. That band is ±17% on the friction half, and Section 31's largest arm can
move it by 1.7%, so the gate could never have been passed by any arm. But the
band is that wide because it is dominated by the common volatility factor, and
the design never asked for a time-series test. The separation was registered in
the other direction, verbatim:

    Section 31 :  Δ(s/M) = Δr                  additive, identical for every name
    volatility :  Δ(s/M) = −k · (s/M)_pre      multiplicative, in the pre level
    so run     :  Δ(s/M)_i = α + β·(s/M)_{i,ref} + ε_i

β eats the common shock by construction and α keeps the fee. The noise that
matters stops being the aggregate wiggle and becomes sd(ε)/√n across symbols.
Whether that rescues the arm is one number, and this file prints it.

THE NUMBER THAT DECIDES IT

    sd(ε) must be under  |Δr| · √n / Z90  for the fee to be detectable at all.

With n = 63 and Δr = −14.90e-6 that is 71.9e-6, which against a spread level of
about 1630e-6 is 4.4% of the level. The file computes the tolerance from the run
rather than carrying 4.4% as a constant, so it stays right if n or the level move.

THE SECOND HALF GETS THE SAME TREATMENT

rho was also read as a median of medians against a time-series band, and that
band cannot see the drift the real window sits on: no placebo sub-window straddles
the middle of the sample, by construction. So rho is re-read per symbol, log R_i =
log(rho_post,i / rho_pre,i), and the dispersion across symbols gives a second,
independent width. Both widths are printed beside the old one. Nothing registered
is discarded: the design's statistic is the cross-sectional median and it is still
reported first.

WHAT THIS FILE DOES NOT DO

It does not re-read the archive with a second scanner. It imports scan() from
b16_rho, so there is one reader of the gz files and one place to fix.

    python experiments/b16_xsec.py --selftest
    python experiments/b16_xsec.py --run
"""
import argparse
import ast
import json
import math
import os
import sys

import numpy as np

import b16_rho as R

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "b16_e5_xsec.json")

Z90 = 1.6448536269514722
#: The reference window is 10 days ending 11 days before the boundary, so a
#: placebo boundary needs k-20 >= -29 to keep it inside what was bought. That is
#: k >= -9, and the pre-side placebo offsets are -19..-10, so ONLY the post-side
#: ten can carry the registered regressor. Ten points is a thin null and it is
#: reported as ten, not padded.
ALPHA_PLACEBO = R.PLACEBO_POST


def ols_with_se(x, y):
    """alpha, beta, se(alpha), residual sd. Two columns, written out rather than
    called from a library so the standard error is visible in the file."""
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    resid = y - X @ beta
    s2 = float(resid @ resid) / (n - 2)
    return (float(beta[0]), float(beta[1]),
            float(math.sqrt(s2 * xtx_inv[0, 0])), float(math.sqrt(s2)))


def spread_window(relsum, sym, venue, wdays):
    """Time-weighted mean relative spread over a window, one venue, one symbol."""
    tot, cnt = 0.0, 0
    for d in wdays:
        v = relsum.get((sym, d, venue))
        if v:
            tot += v[0]
            cnt += v[1]
    return (tot / cnt) if cnt else None


def segment_one(relsum, syms, days, k, venue):
    """The registered regression at boundary k, one venue."""
    ref = R.offsets_to_days(days, R.BOUNDARY, k - 20, k - 11)
    pre, post = R.window_for(days, R.BOUNDARY, k)
    xs, ys = [], []
    for s in syms:
        a = spread_window(relsum, s, venue, ref)
        b = spread_window(relsum, s, venue, pre)
        c = spread_window(relsum, s, venue, post)
        if a is None or b is None or c is None:
            continue
        xs.append(a)
        ys.append(c - b)
    if len(ys) < 10:
        return None
    x = np.asarray(xs, np.float64)
    y = np.asarray(ys, np.float64)
    alpha, beta, se, sd_e = ols_with_se(x, y)
    return {"n": len(ys), "alpha": alpha, "beta": beta, "se_alpha": se,
            "sd_resid": sd_e, "level": float(np.mean(x))}


def rho_per_symbol(rho, syms, days, k):
    """log R_i per symbol at boundary k."""
    pre, post = R.window_for(days, R.BOUNDARY, k)
    out = {}
    for s in syms:
        a = [rho[(s, d)] for d in pre if (s, d) in rho]
        b = [rho[(s, d)] for d in post if (s, d) in rho]
        if not a or not b:
            continue
        va = float(np.median(np.concatenate(a)))
        vb = float(np.median(np.concatenate(b)))
        if va > 0 and vb > 0:
            out[s] = math.log(vb / va)
    return out


def run():
    days = R.load_calendar()
    uni = R.load_universe()
    syms = sorted(R.arm_symbols(uni["events"][str(R.ARM)]))
    print("B16 arm e%d  boundary %s  dr %+.2fe-6  %d symbols"
          % (R.ARM, R.BOUNDARY, R.DR * 1e6, len(syms)))
    print("the same scan as b16_rho.py, imported, not rewritten\n")
    rho, denom, relsum, n_pair, n_viol = R.scan(days, set(syms))
    print("\n  paired seconds %d   outside the Theorem 6(4) domain %d (%.4f%%)"
          % (n_pair, n_viol, 100.0 * n_viol / max(1, n_pair)))

    # ================= first segment, the transmission regression =============
    print("\n=== FIRST SEGMENT: the registered cross-sectional regression ===")
    print("    d(s/M)_i = alpha + beta * (s/M)_i,ref + e_i     per venue\n")
    seg = {}
    for venue in (R.VENUE_A, R.VENUE_B):
        r = segment_one(relsum, syms, days, 0, venue)
        if r is None:
            print("  %-12s no regression" % venue)
            continue
        seg[venue] = r
        tol = abs(R.DR) * math.sqrt(r["n"]) / Z90
        print("  %-12s n %d   level (s/M)_ref %.2f bp" % (venue, r["n"], r["level"] * 1e4))
        print("      alpha %+.4e   se %.4e   t %+.3f   theta = alpha/dr %+.3f"
              % (r["alpha"], r["se_alpha"], r["alpha"] / r["se_alpha"],
                 r["alpha"] / R.DR))
        print("      beta  %+.4f  (the multiplicative shock this absorbs)" % r["beta"])
        print("      sd(e) %.4e = %.2f%% of the level" % (r["sd_resid"],
                                                          100 * r["sd_resid"] / r["level"]))
        print("      TOLERANCE  sd(e) must be below %.4e = %.2f%% of the level"
              % (tol, 100 * tol / r["level"]))
        print("      -> %s" % ("PASS, the fee is detectable on this arm"
                               if r["sd_resid"] <= tol else
                               "FAIL, sd(e) is %.1fx the tolerance"
                               % (r["sd_resid"] / tol)))
        n_need = (Z90 * r["sd_resid"] / abs(R.DR)) ** 2
        print("      symbols needed at this dispersion: %.0f   (all six arms hold 673)"
              % n_need)

    # placebo null for alpha, post side only
    print("\n  placebo null for alpha (%d post-side boundaries; the pre-side ten"
          % len(ALPHA_PLACEBO))
    print("  cannot carry the registered reference window and are not padded in)")
    for venue in seg:
        vals = []
        for k in ALPHA_PLACEBO:
            r = segment_one(relsum, syms, days, k, venue)
            if r:
                vals.append(r["alpha"])
        if len(vals) >= 5:
            lo, hi = np.percentile(vals, [R.BAND_LO, R.BAND_HI], method="linear")
            seg[venue]["placebo_band"] = [float(lo), float(hi)]
            seg[venue]["placebo_sd"] = float(np.std(vals, ddof=1))
            print("    %-12s band [%+.3e, %+.3e]  sd %.3e  real alpha %+.3e  %s"
                  % (venue, lo, hi, np.std(vals, ddof=1), seg[venue]["alpha"],
                     "OUTSIDE" if not (lo <= seg[venue]["alpha"] <= hi) else "inside"))

    # ================= second segment, rho across the cross-section ===========
    print("\n=== SECOND SEGMENT: rho, per symbol ===")
    real = rho_per_symbol(rho, syms, days, 0)
    v = np.asarray([real[s] for s in sorted(real)], np.float64)
    med, mean = float(np.median(v)), float(np.mean(v))
    sd_xs = float(np.std(v, ddof=1))
    se_xs = sd_xs / math.sqrt(len(v))
    print("  n %d   median log R_i %+.6f   mean %+.6f" % (len(v), med, mean))
    print("  sd across symbols %.6f   se of the mean %.6f" % (sd_xs, se_xs))

    print("\n  placebo band on the SAME cross-sectional statistic, %d sub-windows:"
          % (len(R.PLACEBO_PRE) + len(R.PLACEBO_POST)))
    pb_med, pb_mean = [], []
    for k in list(R.PLACEBO_PRE) + list(R.PLACEBO_POST):
        d = rho_per_symbol(rho, syms, days, k)
        if len(d) >= 10:
            w = np.asarray(list(d.values()), np.float64)
            pb_med.append(float(np.median(w)))
            pb_mean.append(float(np.mean(w)))
    blo_m, bhi_m = np.percentile(pb_med, [R.BAND_LO, R.BAND_HI], method="linear")
    half_m = 0.5 * (bhi_m - blo_m)
    print("    on the median: [%+.6f, %+.6f]  half width %.6f"
          % (blo_m, bhi_m, half_m))
    blo_a, bhi_a = np.percentile(pb_mean, [R.BAND_LO, R.BAND_HI], method="linear")
    half_a = 0.5 * (bhi_a - blo_a)
    print("    on the mean:   [%+.6f, %+.6f]  half width %.6f"
          % (blo_a, bhi_a, half_a))

    # ================= gate two, three ways ===================================
    print("\n=== GATE TWO ===")
    dpre = None
    dr_read = R.reading(denom, syms, days, 0)
    if dr_read:
        dpre = dr_read[0]
    if dpre:
        pred = -math.log(1.0 + 2.0 * R.DR / dpre)
        print("  friction half pre = %.6f, so at theta = 1 the fee moves it by"
              % dpre)
        print("  2*dr/pre = %+.4f%%, and the framework's log R is the negative of"
              % (100 * 2 * R.DR / dpre))
        print("  that move: %+.6f\n" % pred)
        for name, half in (("time-series band (b16_rho)", 0.012730),
                           ("cross-sectional band, median", half_m),
                           ("cross-sectional band, mean", half_a),
                           ("Z90 * se of the mean", Z90 * se_xs)):
            ratio = pred / half
            print("    %-32s half %.6f   effect/half %.3f  %s"
                  % (name, half, ratio, "PASS" if ratio >= 1.0 else "fail"))
        print("\n  the first line is what b16_rho used. It is carried here as a")
        print("  constant so the comparison is visible; it is not recomputed.")

    json.dump({"arm": R.ARM, "boundary": R.BOUNDARY, "dr": R.DR,
               "first_segment": seg,
               "second_segment": {"n": len(v), "median": med, "mean": mean,
                                  "sd_across_symbols": sd_xs, "se_mean": se_xs,
                                  "band_median": [float(blo_m), float(bhi_m)],
                                  "band_mean": [float(blo_a), float(bhi_a)]},
               "paired_seconds": n_pair, "domain_excluded": n_viol},
              open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    #: OLS against a case with a known answer.
    rng_x = np.arange(20, dtype=np.float64) / 100.0
    y = 3.0 + 2.0 * rng_x
    a, b, se, sd = ols_with_se(rng_x, y)
    chk("1  OLS recovers an exact line (alpha 3, beta 2) with zero residual",
        abs(a - 3) < 1e-9 and abs(b - 2) < 1e-9 and sd < 1e-9)
    y2 = y.copy()
    y2[0] += 1.0
    a2, _, se2, sd2 = ols_with_se(rng_x, y2)
    chk("2  a single perturbation moves alpha and gives a positive se",
        a2 != a and se2 > 0 and sd2 > 0)

    #: the tolerance arithmetic, stated in the docstring, recomputed here
    tol = abs(R.DR) * math.sqrt(63) / Z90
    chk("3  the detectability tolerance at n=63 is %.3e, about 4.4%% of a"
        " 1630e-6 level" % tol,
        abs(tol - 71.9e-6) < 1.0e-6 and abs(tol / 1630e-6 - 0.044) < 0.002)

    days = R.load_calendar() if os.path.exists(R.CAL_CACHE) else None
    if days:
        bought = set(R.offsets_to_days(days, R.BOUNDARY, -R.BOUGHT_EACH_SIDE,
                                       R.BOUGHT_EACH_SIDE - 1))
        okpost = all(set(R.offsets_to_days(days, R.BOUNDARY, k - 20, k - 11))
                     <= bought for k in ALPHA_PLACEBO)
        badpre = any(k - 20 < -R.BOUGHT_EACH_SIDE for k in R.PLACEBO_PRE)
        chk("4  the post-side ten carry the registered reference window", okpost)
        chk("5  the pre-side ten cannot, which is why the alpha null has ten"
            " points and is reported as ten", badpre)
        ref = R.offsets_to_days(days, R.BOUNDARY, -20, -11)
        pre, _ = R.window_for(days, R.BOUNDARY, 0)
        chk("6  the regressor window does not overlap the pre window, so the"
            " regression is not screening on half its own outcome",
            not (set(ref) & set(pre)))

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("7  this file defines no scanner of its own; scan() is imported so there"
        " is one reader of the archive", "scan" not in fns)
    chk("8  scan is reached through the b16_rho module, not copied",
        hasattr(R, "scan") and callable(R.scan))
    calls = {getattr(c.func, "attr", None) for c in ast.walk(tree)
             if isinstance(c, ast.Call)}
    chk("9  nothing here deletes anything (AST walk)",
        not ({"remove", "unlink", "rmtree", "rmdir"} & calls))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    chk("10 no randomness: this design has no draw count and no seed",
        "random" not in mods)
    chk("11 the design's registered statistic is the median and it is printed"
        " first; the mean is carried beside it, not instead of it",
        src.index("median log R_i") < src.index("sd across symbols"))

    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


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
