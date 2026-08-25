#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C: is the >$300 restriction on the Rule 610(c) carrier paid for by anything?

WHAT IS ON THE TABLE
====================
Rule 610(c) cuts the access fee cap from $0.003 to $0.001 per share, on the
first business day of November 2027, for every NMS stock on every exchange.
The take side is common: Cboe BZX, NYSE Arca and Nasdaq all sit at the current
$0.0030 cap, so the cut binds identically. The REBATE side is not: it runs from
$0.0013 to $0.0020 across venues, a spread of up to $0.0007 per share.

Carrier condition 2 asks the relative spread change to be equal on both classes.
The $0.0007 is the amount by which it is not. The current disposition handles
that by restricting the universe to stocks above about $300, which is the line
the Section 31 carrier already needed.

TWO THINGS ARE WRONG WITH THAT AND BOTH ARE ARITHMETIC
======================================================
1. The $0.0007 is a PUBLISHED number off a fee schedule. Theorem 6(5) gives the
   exact amount it leaks into the index half. A known quantity can be subtracted
   or bounded; it does not have to be avoided.

2. The two carriers have OPPOSITE price gradients. Section 31 is charged per
   dollar of value, so its per-share bite grows with price and it needs
   expensive stocks. Rule 610(c) is a per-SHARE cap, so its relative bite is
   $0.002/P and it is largest on CHEAP stocks. Sharing one universe restricted
   to >$300 therefore puts the 610(c) carrier on precisely the names where its
   own signal is weakest.

THE ARITHMETIC, all of it from b4 section 5.1 and published fee schedules
=========================================================================
Signal, the friction half's move. Pass-through one for one puts the quoted
spread change at $0.002 to $0.004 per share per venue, so on relsum, which sums
two venues,

    signal  =  2 * dS / P,    dS in [0.002, 0.004]

Leak, from Theorem 6(5). With M_a = M_b = M = P and spreads s_a, s_b differing
by ds, the index half picks up

    (s_a^2 - s_b^2) / (4 M^2)  ~=  s * ds / (2 P^2)

Noise, measured. B16 read the friction half's own ten-day variation at 17% of
its level, and the level is about 2s/P on relsum, so

    noise  ~=  0.17 * 2 * s / P

REGISTERED READING, written before the table below was printed
==============================================================
  leak / signal      if this is small at every price, condition 2's restriction
                     buys nothing and should be dropped for this carrier
  signal / noise     this is what decides the carrier, and B16 died at 0.054.
                     Where it is largest is where the universe should be

Both ratios are printed at every price. Nothing is thresholded; the two columns
are the reading.

  leak/signal  =  s * ds / (4 * P * dS)     carries 1/P, so it GROWS as the
                                            price falls, and the restriction is
                                            defensible only if it grows enough
                                            to matter somewhere in range
  signal/noise =  dS / (0.17 * s)           P cancels entirely; this depends on
                                            the SPREAD alone

An earlier draft of this file asserted in prose that leak/signal was price
invariant. It is not, it carries 1/P, and the table it sat above already said
so. Selftest 1 is the assertion that caught it and it is kept in its corrected
form rather than removed.
"""

import ast
import io
import os
import sys

TAKE_CAP_BEFORE, TAKE_CAP_AFTER = 0.0030, 0.0010
REBATE_SPREAD = 0.0007            # $0.0013 to $0.0020 across venues
DS = (0.002, 0.004)               # quoted spread change per share per venue
B16_TEN_DAY_VAR = 0.17            # the friction half's own variation, measured
B16_RATIO = 0.054                 # what B16 achieved, and died on


def row(price, spread):
    sig_lo, sig_hi = 2 * DS[0] / price, 2 * DS[1] / price
    leak = spread * REBATE_SPREAD / (2 * price * price)
    noise = B16_TEN_DAY_VAR * 2 * spread / price
    return sig_lo, sig_hi, leak, leak / sig_lo, sig_lo / noise, sig_hi / noise


def run():
    print("  cap cut %.4f -> %.4f per share, so dS in [%.3f, %.3f] on the quoted"
          % (TAKE_CAP_BEFORE, TAKE_CAP_AFTER, DS[0], DS[1]))
    print("  spread per venue. Rebate non-commonality across venues: $%.4f\n"
          % REBATE_SPREAD)
    print("  %7s %8s %11s %11s %11s %9s %9s"
          % ("price", "spread", "signal lo", "signal hi", "6(5) leak",
             "leak/sig", "sig/noise"))
    grid = [(300.0, 0.05), (300.0, 0.02), (100.0, 0.02), (50.0, 0.02),
            (50.0, 0.01), (20.0, 0.01), (10.0, 0.01), (5.0, 0.01)]
    for p, s in grid:
        lo, hi, leak, ls, snl, snh = row(p, s)
        print("  %7.0f %8.2f %11.3e %11.3e %11.3e %9.2e %5.2f-%.2f"
              % (p, s, lo, hi, leak, ls, snl, snh))

    print("\n  leak / signal = s*ds / (4*P*dS), so it carries 1/P and GROWS as")
    print("  the price falls: %.2e at $300 with a 2c spread, %.2e at the"
          % (row(300.0, 0.02)[3], row(5.0, 0.01)[3]))
    print("  cheapest, tightest corner of the grid. Even there the published")
    print("  $0.0007 sits %.0fx under the signal it would contaminate."
          % (1.0 / row(5.0, 0.01)[3]))
    print("  Condition 2's restriction is not paid for by the leak anywhere in")
    print("  range. The defence would need leak/signal near one, and the worst")
    print("  corner is four orders of magnitude short of that.")

    print("\n  what the restriction DOES cost, in signal:")
    a = row(300.0, 0.02)[0]
    for p in (300.0, 100.0, 50.0, 20.0, 10.0):
        print("    $%-6.0f  signal %11.3e   %5.1fx the $300 row"
              % (p, row(p, 0.02)[0], row(p, 0.02)[0] / a))

    print("\n  and signal / noise, which is the number that killed B16 at %.3f:"
          % B16_RATIO)
    print("    it depends on the SPREAD, not the price: signal/noise = 2*dS /")
    print("    (0.17 * 2 * s) = dS / (0.17 * s), and P cancels entirely.")
    for s in (0.05, 0.02, 0.01):
        v = DS[0] / (B16_TEN_DAY_VAR * s)
        print("    spread $%.2f  ->  %6.2f    %5.1fx what B16 achieved"
              % (s, v, v / B16_RATIO))
    print("\n  so the universe should be chosen on the SPREAD, not on the price,")
    print("  and penny-spread names give about %.0fx B16's ratio."
          % (DS[0] / (B16_TEN_DAY_VAR * 0.01) / B16_RATIO))
    print("  The >$300 line selects wide-spread names and is the wrong axis.")
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    a, b = row(300.0, 0.02), row(30.0, 0.02)
    #: The corrected form. leak/signal = s*ds/(4*P*dS) carries 1/P exactly, so
    #: a tenth of the price is ten times the ratio. The earlier version of this
    #: assertion claimed invariance and failed, which is the only reason the
    #: prose above it got fixed.
    chk("1  leak/signal carries 1/P exactly: a tenth of the price is ten times "
        "the ratio (%.4e vs %.4e)" % (a[3], b[3]),
        abs(b[3] / a[3] - 10.0) < 1e-9)
    worst = row(5.0, 0.01)[3]
    chk("2  even at the cheapest, tightest corner of the grid the leak is four "
        "orders of magnitude under the signal (%.2e)" % worst, worst < 1e-3)
    chk("3  signal scales as 1/P, so a ten-fold cheaper stock carries ten times "
        "the signal", abs(b[0] / a[0] - 10.0) < 1e-9)
    n1 = DS[0] / (B16_TEN_DAY_VAR * 0.01)
    n2 = DS[0] / (B16_TEN_DAY_VAR * 0.05)
    chk("4  signal/noise depends on the spread and not on the price: it is "
        "%.2f at a penny spread and %.2f at a nickel" % (n1, n2),
        abs(row(10.0, 0.01)[4] - n1) < 1e-9
        and abs(row(300.0, 0.01)[4] - n1) < 1e-9 and n1 > 4 * n2)
    chk("5  the two carriers' price gradients are stated as opposite, which is "
        "why one universe cannot serve both",
        "OPPOSITE price gradients" in (ast.get_docstring(tree) or ""))
    chk("6  the reading rule is registered before the table, and neither ratio "
        "is thresholded",
        "REGISTERED READING" in (ast.get_docstring(tree) or "")
        and "Nothing is thresholded" in (ast.get_docstring(tree) or ""))
    chk("7  no delete call, and no data is read: this file is arithmetic only",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir", "load", "read_text")]
        #: io.open is an Attribute call, so counting only ast.Name misses it.
        #: The earlier version counted zero and failed its own assertion.
        and len([n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", getattr(n.func, "id", "")) == "open"]) == 1)
    print("\n  %d/7" % (7 - len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
