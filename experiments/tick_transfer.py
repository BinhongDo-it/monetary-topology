#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Does tick quantization cancel in rho? Pure construction, no data.

WHY
===
Five carrier candidates died of five different causes, and the fifth autopsy
suggested one wall behind all of them: the frictions that do NOT quantize the
price grid turn out not to BIND the quoted spread, and the only friction that
binds by construction is the minimum price increment itself, which b4 section 9
condition (3) excludes precisely because it quantizes the grid.

If that tension is real the search should stop, because no carrier exists. If
it is not real the tick is the carrier, and tick changes are free, dated, and
have happened many times in many markets. Either way the question is settled by
arithmetic, so it is settled before anything else is bought.

THE ALGEBRA, WORKED FIRST
=========================
Write tau = delta/P for the tick as a fraction of price.

Quoted prices sit on the grid, so ask - bid = k*delta with k >= 1 an integer,
and to first order

    -(S+S') = log(ask_A/bid_A) + log(ask_B/bid_B) ~= (k_A + k_B) * tau

A mid is the average of two grid points, so it sits on the HALF-tick grid, and
mid_A - mid_B is an integer multiple of delta/2. Write it m*delta/2. Then

     S-S'  = 2*log(mid_A/mid_B) ~= m * tau

The factor two in the definition and the half in the half-tick cancel, so BOTH
halves are quantized in the same unit tau, and

     rho = |m| / (k_A + k_B)

**tau cancels exactly.** rho is a ratio of two integer tick counts and does not
depend on the tick size at all. That is the encouraging half.

The discouraging half is the FLOORS, which are not the same:

    k_A + k_B >= 2      a spread cannot be narrower than one tick per venue
    |m|       >= 0      two venues' mids can and often do coincide

So the denominator is censored from below at 2 and the numerator is censored at
0. Those are different censorings, and a change in tau moves them differently:
a finer grid lets the numerator escape zero while the denominator stays pinned
at its floor. That raises rho mechanically. A genuine reduction in trading
friction lowers the desired spread, which also raises rho. **Same sign.** If
that holds, the mechanical and the economic effect are collinear and the tick
is confounded as a carrier.

Whether it holds depends on the regime, and the regime is set by two ratios:

    w/tau     the desired half-spread in ticks
    sigma/tau the cross-venue mid dispersion in ticks

Three regimes, and only one of them is any use:

  A. w >> tau and sigma >> tau. Neither half is censored, both recover their
     economic values, and a tick change does nothing at all. No treatment.
  B. w < tau and sigma < tau. Both halves censored. k pinned at 1 each, and m
     confined to a couple of values. rho becomes a two-point distribution and a
     tick change moves it mechanically. Confounded.
  C. w < tau < sigma. The denominator is fully quantized and pinned at 2*tau,
     while the numerator is NOT, because sigma is large enough that rounding it
     to the grid costs little. Then rho ~= sigma/(2*tau) and a tick change moves
     rho by EXACTLY tau_before/tau_after, with the numerator untouched. That is
     a common friction change in the Theorem 6(5) sense, with a parameter-free
     prediction and no fitting.

REGISTERED READING, WRITTEN BEFORE THE SIMULATION WAS RUN
=========================================================
The simulation measures rho_after/rho_before under a tick change, on a grid of
(w/tau, sigma/tau), and compares it to tau_before/tau_after.

  If some region reproduces tau_before/tau_after to within the sampling noise,
  AND membership in that region is decidable from the quotes themselves before
  the event, the tick is a usable carrier restricted to that region.

  If no region reproduces it, or the only region that does cannot be identified
  ex ante, the tick is not usable and the carrier search closes on a
  construction result rather than on another failed purchase.

Region C's membership test is decidable from quotes alone and needs no model:
    w < tau      <=>  the quoted spread is exactly one tick at both venues
    sigma > tau  <=>  |mid_A - mid_B| exceeds one tick
Both are read straight off a quote snapshot.

WHAT THIS FILE DOES NOT DO
==========================
No data. No fitting. No market is named. The only inputs are the two ratios and
the tick change factor.
"""

import argparse
import ast
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "tick_transfer.json")

#: A deterministic generator, because the house forbids a result that cannot be
#: reproduced and this file has no reason to be random. Numerical Recipes LCG.
class LCG:
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def u(self):
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return (self.s + 0.5) / 4294967296.0

    def normal(self):
        #: Box-Muller, one draw per call, second discarded. Wasteful and
        #: obviously correct, which is the right trade for a file this size.
        a, b = self.u(), self.u()
        return math.sqrt(-2.0 * math.log(a)) * math.cos(2.0 * math.pi * b)


def quote(mid_true, w, tick):
    """(bid, ask) on the grid. The quoter wants [mid-w, mid+w] and must round
    outward to the grid, so the posted spread is never narrower than the
    desired one and never narrower than one tick."""
    bid = math.floor((mid_true - w) / tick) * tick
    ask = math.ceil((mid_true + w) / tick) * tick
    if ask <= bid:
        ask = bid + tick
    return bid, ask


def one_asset(rng, price, w, sigma, tick):
    """rho for one asset at one instant, or None if it leaves the domain."""
    a = price * (1.0 + sigma * rng.normal())
    b = price * (1.0 + sigma * rng.normal())
    ba, aa = quote(a, w * price, tick)
    bb, ab = quote(b, w * price, tick)
    if min(ba, bb) <= 0:
        return None
    #: how many venues posted the minimum, one tick. This is the observable
    #: that stands in for the unobservable w: a quoter whose desired band
    #: [mid-w, mid+w] straddles a grid line must round out on both sides and
    #: posts two ticks, and that happens with probability 2w/tau. So the
    #: fraction of venue-quotes at exactly one tick estimates 1 - 2w/tau, from
    #: a snapshot, with no model and no fitting.
    at_floor = ((round((aa - ba) / tick) == 1) + (round((ab - bb) / tick) == 1))
    den = math.log(aa / ba) + math.log(ab / bb)
    num = 2.0 * math.log((0.5 * (ba + aa)) / (0.5 * (bb + ab)))
    if den <= 0:
        return None
    return abs(num) / den, den, abs(num), at_floor


def sweep(w_ticks, sig_ticks, tick, n, seed, price=100.0):
    """Median rho, median denominator, median numerator over n assets."""
    rng = LCG(seed)
    w = w_ticks * tick / price
    sigma = sig_ticks * tick / price
    r, d, u, f = [], [], [], 0
    for _ in range(n):
        g = one_asset(rng, price, w, sigma, tick)
        if g is None:
            continue
        r.append(g[0]); d.append(g[1]); u.append(g[2]); f += g[3]
    if not r:
        return None
    med = lambda v: sorted(v)[len(v) // 2]                            # noqa: E731
    return med(r), med(d), med(u), len(r), f / (2.0 * len(r))


def cmd_map(n, seed, alpha):
    """The transfer map. rho_after/rho_before under tick -> alpha*tick, over a
    grid of (w/tau, sigma/tau), against the parameter-free prediction 1/alpha."""
    tick0 = 0.01
    tick1 = alpha * tick0
    print("  tick change  %.4f -> %.4f   (factor %.3f)" % (tick0, tick1, alpha))
    print("  PREDICTION in region C, parameter free:  rho_after/rho_before = "
          "tau_before/tau_after = %.4f\n" % (1.0 / alpha))
    #: w must reach well below 0.1 ticks. The denominator is pinned at the
    #: floor only while the desired band [mid-w, mid+w] almost never straddles
    #: a grid line, and that straddle probability is 2w/tau, so at w = 0.1 ticks
    #: it is already 20% before the change and 40% after. That is why the first
    #: run of this grid showed den_fac drifting to 0.75 instead of sitting at
    #: alpha: the tick count was RISING as the tick shrank, partly offsetting it.
    W = [0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 0.9, 1.5, 3.0, 8.0]
    G = [0.1, 0.25, 0.5, 0.9, 1.5, 3.0, 8.0, 30.0]
    print("  rows: desired half-spread w in ticks (BEFORE the change)")
    print("  cols: cross-venue mid dispersion sigma in ticks (BEFORE)")
    print("  cell: rho_after / rho_before\n")
    print("       %s" % "".join("%9.2f" % g for g in G))
    grid = {}
    for w in W:
        line = "  %5.2f" % w
        for g in G:
            a = sweep(w, g, tick0, n, seed)
            #: the SAME economic w and sigma, expressed in the NEW tick's units
            b = sweep(w * tick0 / tick1, g * tick0 / tick1, tick1, n, seed)
            if a is None or b is None or a[0] == 0:
                line += "        -"
                continue
            ratio = b[0] / a[0]
            grid["%.2f|%.2f" % (w, g)] = {
                "rho_before": a[0], "rho_after": b[0], "ratio": ratio,
                "den_before": a[1], "den_after": b[1],
                "num_before": a[2], "num_after": b[2],
                "floor_frac_before": a[4], "floor_frac_after": b[4],
                "w_implied_before": (1.0 - a[4]) / 2.0}
            line += "%9.3f" % ratio
        print(line)

    print("\n  the same grid, showing what each HALF did. A usable carrier needs")
    print("  the denominator to carry the whole move and the numerator to sit")
    print("  still: den_fac = alpha = %.3f, num_fac = 1.000, hence rho_fac ="
          % alpha)
    print("  1/alpha = %.3f. (The first run of this map checked den against"
          % (1.0 / alpha))
    print("  1/alpha, which was the wrong direction: a binding floor SHRINKS")
    print("  with the tick, it does not grow.)\n")
    print("  %-12s %9s %9s %9s %9s %9s %9s"
          % ("w | sigma", "den_fac", "num_fac", "rho_fac", "atfloor",
             "w_hat", "w_true"))
    usable = []
    for w in W:
        for g in G:
            k = "%.2f|%.2f" % (w, g)
            if k not in grid:
                continue
            c = grid[k]
            df, nf = c["den_after"] / c["den_before"], c["num_after"] / c["num_before"]
            #: registered before the run: the denominator must carry the whole
            #: move and the numerator must not move. Ten percent on each is the
            #: sampling slack at this n, stated rather than tuned.
            ok = abs(df - alpha) < 0.10 * alpha and abs(nf - 1.0) < 0.10
            if ok:
                usable.append((w, g, df, nf, c["ratio"]))
            if ok or g == 3.0:
                print("  %-12s %9.3f %9.3f %9.3f %9.3f %9.4f %9.4f   %s"
                      % (k, df, nf, c["ratio"], c["floor_frac_before"],
                         c["w_implied_before"], w, "USABLE" if ok else ""))
    print("\n  cells where the denominator carries the move and the numerator "
          "does not: %d of %d" % (len(usable), len(grid)))
    if usable:
        print("  they are:")
        for w, g, df, nf, r in usable:
            print("    w = %.2f ticks, sigma = %.2f ticks   den x%.3f  num x%.3f"
                  "  rho x%.3f" % (w, g, df, nf, r))
        ws = sorted({w for w, _g, _d, _n, _r in usable})
        gs = sorted({g for _w, g, _d, _n, _r in usable})
        print("\n  they span w in %s ticks and sigma in %s ticks."
              % (ws, gs))
        print("  Membership is decidable from a quote snapshot with no model:")
        print("    w < tau      the spread is exactly one tick at both venues")
        print("    sigma > tau  the two mids differ by more than one tick")
        print("  The w side is the hard one: the map says it is not enough for")
        print("  the spread to be one tick, the DESIRED spread has to be far")
        print("  below one tick, and that is not observable.")
    else:
        print("  none. The tick is not a usable carrier and the search closes on")
        print("  a construction result.")
    os.makedirs(RESULTS, exist_ok=True)
    json.dump({"alpha": alpha, "n": n, "seed": seed, "grid": grid,
               "usable": [{"w_ticks": w, "sigma_ticks": g, "den_factor": df,
                           "num_factor": nf, "rho_factor": r}
                          for w, g, df, nf, r in usable]},
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

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)

    b, a = quote(100.0, 0.5, 0.01)
    chk("1  a quote rounds OUTWARD to the grid, never inward",
        b <= 99.5 and a >= 100.5 and abs(b - 99.5) < 1e-9 and abs(a - 100.5) < 1e-9)
    b, a = quote(100.003, 0.0001, 0.01)
    chk("2  a desired spread narrower than one tick is posted at one tick, "
        "which is the floor the whole argument turns on",
        abs((a - b) - 0.01) < 1e-9)

    #: tau cancels: the same economic world on two grids fine enough that
    #: neither half is censored gives the same rho.
    r1 = sweep(8.0, 8.0, 0.01, 4000, 7)
    r2 = sweep(80.0, 80.0, 0.001, 4000, 7)
    chk("3  with both halves far from their floors, rho is the same on a grid "
        "ten times finer: tau cancels (%.4f vs %.4f)" % (r1[0], r2[0]),
        abs(r1[0] - r2[0]) / r1[0] < 0.05)

    #: the floors are different, and that is the whole asymmetry
    #: The floor is 1 tick PER VENUE, so 2 ticks for the pair, but a quoter
    #: whose desired band straddles a grid line has to round out on both sides
    #: and posts 2 ticks. So the pair's denominator is 2, 3 or 4 ticks, never
    #: less than 2, and always an integer count. That integrality IS the claim.
    r3 = sweep(0.1, 0.1, 0.01, 4000, 7)
    tau = 0.01 / 100.0
    ticks = r3[1] / tau
    chk("4  inside one tick the denominator is an integer count of ticks with "
        "a hard floor of two, one per venue (measured %.3f ticks)" % ticks,
        ticks >= 2.0 - 1e-9 and abs(ticks - round(ticks)) < 0.02)

    chk("5  the reading rule, the three regimes and the ex-ante membership "
        "test are in the module docstring, not in a chat log",
        all(k in (ast.get_docstring(tree) or "")
            for k in ("REGISTERED READING", "Region C", "w < tau < sigma",
                      "decidable from quotes alone")))
    chk("6  no delete call anywhere in the tree",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir")])
    chk("7  the generator is deterministic: the same seed gives the same draw",
        LCG(11).normal() == LCG(11).normal())
    #: AST, because the previous shape of this check forbade a path by writing
    #: it out, and its own text tripped it. Fourth time in this repository that
    #: a guard counted its own source; the fix has been the same every time.
    opens = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "open"]
    modes = []
    for n in opens:
        modes.append(str(n.args[1].value) if len(n.args) >= 2
                     and isinstance(n.args[1], ast.Constant) else "r")
    chk("9  this file opens exactly two things: its own source, to read the "
        "docstring back, and the one result it writes. It ingests no data.",
        len(opens) == 2 and sorted(modes) == ["r", "w"])
    chk("8  every quoted price sits on the grid, which is what makes the two "
        "halves integer counts in the first place",
        all(abs(x / 0.01 - round(x / 0.01)) < 1e-9
            for mid in (100.0, 100.003, 99.9971, 100.0049)
            for x in quote(mid, 0.0007, 0.01)))
    print("\n  %d/%d" % (9 - len(fails), 9))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--map", action="store_true")
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20260823)
    ap.add_argument("--alpha", type=float, default=0.5,
                    help="tick multiplier; 0.5 halves the tick")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.map:
        return cmd_map(a.n, a.seed, a.alpha)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
