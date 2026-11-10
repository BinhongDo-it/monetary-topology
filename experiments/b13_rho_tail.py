#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Route A: does the no-arbitrage band ever get approached?

WHY
===
The rival to b4 section 5.1 is that friction sets the band and the index half
fills it. A reductio against that rival needs the band to be APPROACHED and it
is not enough to note that it is never exactly touched: Theorem 6(4)'s equality
holds iff `S*S' = 0`, one orientation exactly free, which is a measure-zero
knife edge that no continuous process hits. "rho = 1 occurred 0 times in 49,116"
is therefore a prediction shared by every model including the rival's, and it
refutes nothing.

The statistic that does carry the reductio is the UPPER TAIL MASS: how much of
the distribution sits at rho >= 0.8, 0.9, 0.95.

AND THE THIRD BRANCH, which is the whole reason this file is more than one line
=============================================================================
In B13 both halves are integer counts of the instrument's tick: on ch382 the
friction runs from 2 to 12 ticks on the CL spreads and up to 129 on RB, and
the index half from 0 to 5 on CL and up to 64 on RB. So rho lives on a
COARSE GRID, and a high rho needs the index count to come close to the friction
count. If the grid cannot represent the tail, an empty tail says nothing about
the world.

  tail non-empty                    the band is approached; route B is feasible here
  tail empty AND reachable          the band is genuinely never approached, and
                                    that is the reductio, correctly made
  tail empty AND NOT reachable      the carrier cannot represent the tail. Reads
                                    nothing. D15: a criterion with one reachable
                                    branch carries no information

WHAT THE GRID CAN SHOW, WITH THE PARITY IN IT
=============================================
Both orientations are whole ticks on one grid. With both strictly inside the
band, S and S' are negative integers, the friction count is k = -(S + S') and
the index is i = S - S'. Then k + i = -2S' and k - i = -2S, so

    the index has the friction count's parity, and |i| <= k - 2

and the largest rho a state with friction count k can show is (k-2)/k. The tail
at cut c is representable for that state only if (k-2)/k >= c. Until 2026-10-10
this file printed (k-1)/k, a value the grid does not contain, and compared k
with the float 1/(1-c), which at c = 0.8 is a hair above 5 and so dropped k = 5
from its own count. Both made an empty tail look reachable where it is not:
CLQ3-CLV3 at 0.8 read 2,493 states able to show the cut and has none. The
comparison is now in integers and the three branches are printed per
instrument and per cut.

Registered before the cache was opened. The object printed is the joint
distribution of the two integer counts, per instrument, not a summary of it.
"""

import ast
import io
import os
import sys
from collections import Counter, defaultdict
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
#: The carrier is an argument. ch382 is CL and RB, ch386 is NG and TTF, ch360
#: is COMEX metals: same capture day and same exchange, but different products,
#: different ticks and an order of magnitude less depth. Second carrier, not a
#: second look at the first.
TSV = os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch382.tsv")
CUTS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)


def exact(cut):
    """The cut as the decimal fraction it was written as, not as a float."""
    return Fraction(str(cut))


def interior_top(k):
    """Largest |index| at friction count ``k`` with both orientations strictly
    inside the band: the index has k's parity and stops two short of it."""
    return k - 2


def reaches(k, cut):
    """Can a state with friction count ``k`` show rho >= cut strictly inside?

    (k - 2)/k >= cut, cross-multiplied, so nothing is decided by a float.
    """
    c = exact(cut)
    return k >= 2 and interior_top(k) * c.denominator >= c.numerator * k


def in_tail(friction, index, cut):
    """rho >= cut for one state, on the two integers it is made of."""
    c = exact(cut)
    return index * c.denominator >= c.numerator * friction


def branch(tail, reachable):
    """Which of the three registered branches a cell is in.

    A state in the tail whose own friction count cannot represent the cut
    contradicts the grid the count is made on, so that combination is refused
    and not given a letter.
    """
    if tail > reachable:
        raise ValueError(
            "%d states sit in a tail only %d could represent: the two halves "
            "are not whole ticks on one grid here" % (tail, reachable))
    if tail > 0:
        return "approached"
    return "empty, reachable" if reachable > 0 else "not representable"


def grid_breaks(fr, ix):
    """States that are off the grid the reachability is computed on:
    wrong parity, and an index above k - 2 (the knife edge is index == k)."""
    parity = sum(1 for k, i in zip(fr, ix) if (k - i) % 2)
    beyond = sum(1 for k, i in zip(fr, ix) if i > interior_top(k) and i != k)
    edge = sum(1 for k, i in zip(fr, ix) if i == k)
    return parity, beyond, edge


def load(path=None):
    global TSV
    if path:
        TSV = path
    rows = defaultdict(list)
    tick = {}
    with io.open(TSV, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 4:
                continue
            fr, ix = int(f[2]), int(f[3])
            if fr >= 0:
                continue
            rows[f[0]].append((-fr, abs(ix)))
    #: the tick is read off the data: the gcd of every printed magnitude, which
    #: for a grid-quantised price is the grid. Not taken from a config.
    for nm, v in rows.items():
        g = 0
        for a, b in v:
            for x in (a, b):
                while x:
                    g, x = x, g % x
        tick[nm] = g
    return rows, tick


def run(path=None):
    print("  carrier: %s\n"
          % os.path.relpath(path or TSV, ROOT).replace(os.sep, "/"))
    rows, tick = load(path)
    print("  the tick is the gcd of every printed magnitude, read off the data\n")
    print("  %-11s %7s %6s %9s %9s %9s %9s"
          % ("spread", "n", "tick", "fric min", "fric max", "idx max", "rho max"))
    per = {}
    for nm in sorted(rows, key=lambda k: -len(rows[k])):
        v = rows[nm]
        t = tick[nm]
        fr = [a // t for a, _ in v]
        ix = [b // t for _, b in v]
        rho = [b / a for a, b in v]
        per[nm] = (v, t, fr, ix, rho)
        print("  %-11s %7d %6.0e %9d %9d %9d %9.4f"
              % (nm, len(v), t, min(fr), max(fr), max(ix), max(rho)))

    print("\n  UPPER TAIL, share of states at or above each cut")
    print("  %-11s %s" % ("spread", "".join("%9.2f" % c for c in CUTS)))
    for nm in per:
        v, t, fr, ix, rho = per[nm]
        n = len(rho)
        print("  %-11s %s"
              % (nm, "".join("%8.4f%%"
                             % (100.0 * sum(1 for a, b in v if in_tail(a, b, c)) / n)
                             for c in CUTS)))

    print("\n  THE GRID. Both halves are whole ticks on one grid, so the index has")
    print("  the friction count's parity and, strictly inside the band, stops at")
    print("  k - 2. States that break either, and states on the knife edge:")
    print("  %-11s %9s %9s %9s" % ("spread", "parity", "above k-2", "index = k"))
    for nm in per:
        v, t, fr, ix, rho = per[nm]
        print("  %-11s %9d %9d %9d" % ((nm,) + grid_breaks(fr, ix)))

    print("\n  REACHABILITY. Given each state's own friction count k, the largest")
    print("  rho the grid can produce for it strictly inside the band is (k-2)/k,")
    print("  and k/k = 1 is the knife edge. So the tail at cut c is representable")
    print("  for a state only if (k-2)/k >= c, compared in integers.")
    print("  %-11s %9s %s" % ("spread", "med k", "share of states whose k allows the cut"))
    print("  %-11s %9s %s" % ("", "", "".join("%9.2f" % c for c in CUTS[:-1])))
    for nm in per:
        v, t, fr, ix, rho = per[nm]
        n = len(fr)
        s = sorted(fr)
        line = ""
        for c in CUTS[:-1]:
            line += "%8.1f%%" % (100.0 * sum(1 for k in fr if reaches(k, c)) / n)
        print("  %-11s %9d %s" % (nm, s[n // 2], line))

    print("\n  THE THREE BRANCHES, per instrument and cut: states in the tail over")
    print("  states whose k can represent it.  A approached   E empty, reachable")
    print("  X not representable, reads nothing")
    print("  %-11s %s" % ("spread", "".join("%15.2f" % c for c in CUTS[:-1])))
    letters = {"approached": "A", "empty, reachable": "E", "not representable": "X"}
    for nm in per:
        v, t, fr, ix, rho = per[nm]
        line = ""
        for c in CUTS[:-1]:
            tail = sum(1 for a, b in v if in_tail(a, b, c))
            can = sum(1 for k in fr if reaches(k, c))
            line += "%15s" % ("%d/%d %s" % (tail, can, letters[branch(tail, can)]))
        print("  %-11s %s" % (nm, line))

    print("\n  THE OBJECT: joint distribution of (friction ticks, index ticks),")
    print("  the two busiest instruments, counts")
    for nm in list(per)[:2]:
        v, t, fr, ix, rho = per[nm]
        j = Counter(zip(fr, ix))
        ks = sorted({a for a, _ in j})
        js = sorted({b for _, b in j})
        print("\n    %s   rows = friction ticks, cols = index ticks" % nm)
        print("      %6s %s" % ("", "".join("%8d" % b for b in js)))
        for a in ks:
            print("      %6d %s" % (a, "".join("%8d" % j.get((a, b), 0) for b in js)))
    return 0


def cross(paths):
    """Across instruments: does the index half know how deep the friction is?

    The tail says the band is not what holds the index half. This asks the next
    question, and it is the one with leverage: across instruments whose friction
    differs by more than an order of magnitude in ticks, does the index half
    scale with it?

      rival      |index| tracks friction, so median rho is FLAT across depth
      framework  |index| is set elsewhere, so median rho falls roughly as 1/k

    Registered before the two files were combined. Both columns are printed at
    every instrument and nothing is thresholded; the shape across the column is
    the reading. The confound is stated in advance: a deeper contract is also a
    more liquid one, and liquidity plausibly tightens the mids as well as the
    spread, so a falling rho is consistent with a common liquidity driver too.
    What it is NOT consistent with is the rival, which needs rho flat."""
    all_rows = []
    for path in paths:
        rows, tick = load(path)
        tag = os.path.basename(path).split("two_classes_")[-1].replace(".tsv", "")
        for nm, v in rows.items():
            t = tick[nm]
            fr = sorted(a // t for a, _ in v)
            ix = sorted(b // t for _, b in v)
            rho = sorted(b / a for a, b in v)
            n = len(v)
            all_rows.append((tag, nm, n, fr[n // 2], ix[n // 2], rho[n // 2]))
    all_rows.sort(key=lambda r: r[3])
    print("  %-8s %-12s %7s %7s %8s %9s %11s"
          % ("chan", "spread", "n", "med k", "med idx", "med rho", "rho * k"))
    for tag, nm, n, k, i, r in all_rows:
        print("  %-8s %-12s %7d %7d %8d %9.4f %11.2f" % (tag, nm, n, k, i, r, r * k))
    lo = [r for r in all_rows if r[3] <= 8]
    hi = [r for r in all_rows if r[3] >= 16]
    med = lambda v: sorted(v)[len(v) // 2]                            # noqa: E731
    print("\n  %d instruments with med k <= 8   : med rho %.4f   med |index| %d ticks"
          % (len(lo), med([r[5] for r in lo]), med([r[4] for r in lo])))
    print("  %d instruments with med k >= 16  : med rho %.4f   med |index| %d ticks"
          % (len(hi), med([r[5] for r in hi]), med([r[4] for r in hi])))
    kl, kh = med([r[3] for r in lo]), med([r[3] for r in hi])
    rl, rh = med([r[5] for r in lo]), med([r[5] for r in hi])
    print("\n  friction deepens %.1fx across those two groups." % (kh / kl))
    print("    rival, rho flat            -> rho ratio 1.00")
    print("    framework, |index| fixed   -> rho ratio %.2f" % (kl / kh))
    print("    observed                   -> rho ratio %.2f" % (rh / rl))
    print("  and the index half itself goes from %d to %d ticks, a factor of %.1f,"
          % (med([r[4] for r in lo]), med([r[4] for r in hi]),
             med([r[4] for r in hi]) / max(1, med([r[4] for r in lo]))))
    print("  against %.1f for the friction. The index half uses %.0f%% of the"
          % (kh / kl, 100.0 * (med([r[4] for r in hi]) / max(1, med([r[4] for r in lo]))) / (kh / kl)))
    print("  extra room the deeper contracts give it.")
    return 0


def lead(paths, lags=(-20, -10, -5, -2, -1, 0, 1, 2, 5, 10, 20)):
    """Which of the two halves moves first?

    Three mechanisms are still standing for the observed relation between the
    two halves, and they say different things about TIME:

      common driver   both halves are functions of one latent state, so they
                      move together and the correlation peaks at lag zero
      soft causal     the friction widens and the mids drift afterwards, so the
                      friction LEADS and the peak sits at a positive lag
      framework       the index half is set elsewhere and there is no peak

    Registered before the first correlation was computed. The statistic is the
    correlation between the change in the friction half at t-L and the change in
    the absolute index half at t, per instrument, over the sequence order that
    is already in the file. Changes, not levels, because both levels are
    integer-valued and highly persistent and a level correlation would mostly
    report that persistence.

    ONLY THE SIX RESOLVABLE INSTRUMENTS ARE READ. The other seventeen have a
    median index half of one or two ticks, which is the grid floor, and a change
    in a quantity pinned at its floor is mostly the grid. That gate is the one
    this file applied to the tail and then failed to apply to the cross section
    one step later; it is applied here before anything is printed."""
    per = []
    for path in paths:
        rows, tick = load(path)
        for nm, v in rows.items():
            t = tick[nm]
            ix = sorted(b // t for _, b in v)
            if ix[len(ix) // 2] < 3:
                continue
            per.append((nm, [(a / t, b / t) for a, b in v]))
    if not per:
        print("  no instrument resolves the index half. Nothing to read.")
        return 1
    print("  %d instruments pass the resolution gate; the other rows in the"
          % len(per))
    print("  file are pinned at the grid floor and are not read.")
    print("  negative lag = friction leads the index half.")
    print("")
    print("  %-13s %7s %s" % ("spread", "n", "".join("%8d" % L for L in lags)))
    tot = {L: [] for L in lags}
    for nm, v in per:
        df = [v[i][0] - v[i - 1][0] for i in range(1, len(v))]
        di = [v[i][1] - v[i - 1][1] for i in range(1, len(v))]
        line = ""
        for L in lags:
            a = df[max(0, -L):len(df) - max(0, L)]
            b = di[max(0, L):len(di) - max(0, -L)]
            n = min(len(a), len(b))
            a, b = a[:n], b[:n]
            if n < 50:
                line += "%8s" % "-"
                continue
            ma, mb = sum(a) / n, sum(b) / n
            va = sum((x - ma) ** 2 for x in a)
            vb = sum((y - mb) ** 2 for y in b)
            if va <= 0 or vb <= 0:
                line += "%8s" % "-"
                continue
            c = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb) ** 0.5
            tot[L].append(c)
            line += "%8.4f" % c
        print("  %-13s %7d %s" % (nm, len(v), line))
    print("  %-13s %7s %s"
          % ("median", "", "".join("%8.4f" % (sorted(tot[L])[len(tot[L]) // 2]
                                              if tot[L] else float("nan"))
                                   for L in lags)))
    med = {L: (sorted(tot[L])[len(tot[L]) // 2] if tot[L] else 0.0) for L in lags}
    peak = max(med, key=lambda L: abs(med[L]))
    print("")
    print("  peak of the median at lag %+d, value %+.4f" % (peak, med[peak]))
    print("    lag 0        -> both halves move together, a common driver")
    print("    lag negative -> the friction leads, the soft causal story")
    print("    no peak      -> no relation at this horizon")
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    doc = ast.get_docstring(tree) or ""
    chk("1  the file states, before any number, why 'rho = 1 occurred 0 times' "
        "refutes nothing: equality is a measure-zero knife edge",
        "measure-zero" in doc and "refutes nothing" in doc)
    chk("2  the three branches are registered, including the one where an empty "
        "tail reads nothing because the grid cannot represent it",
        "tail empty AND NOT reachable" in doc and "D15" in doc)
    rows, tick = load()
    chk("3  the tick is derived from the data as a gcd, not taken from a config "
        "(%d instruments, ticks %s)"
        % (len(tick), sorted({v for v in tick.values()})),
        len(tick) >= 8 and all(v > 0 for v in tick.values()))
    tot = sum(len(v) for v in rows.values())
    chk("4  every state in the cache with a negative friction is loaded "
        "(%d of the 49,116 the station reported)" % tot,
        48000 <= tot <= 49116)
    chk("5  no delete call",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir")])

    # 6  the bound is what the grid contains, by enumeration and not by algebra:
    #    every pair of negative integers S, S' with S + S' = -k
    worst = None
    for k in range(2, 141):
        idx = [abs(s - (-k - s)) for s in range(-k + 1, 0)]
        if max(idx) != interior_top(k) or any((k - i) % 2 for i in idx):
            worst = k
            break
    chk("6  enumerating both orientations for k = 2..140, the largest interior "
        "index is k - 2 and every index has k's parity", worst is None)

    # 7  the comparison is in integers. k = 5 at cut 0.8 is where the float
    #    form went wrong: 1/(1 - 0.8) is a hair above 5
    chk("7  reaches() is exact at the cut: k=10 shows 0.8 and k=9 does not, "
        "k=5 shows 0.6 and not 0.8, k=20 shows 0.9 and k=19 does not; and the "
        "float 1/(1-0.8) is above 5 (%r)" % (1.0 / (1.0 - 0.8)),
        reaches(10, 0.8) and not reaches(9, 0.8) and reaches(5, 0.6)
        and not reaches(5, 0.8) and reaches(20, 0.9) and not reaches(19, 0.9)
        and 1.0 / (1.0 - 0.8) > 5)

    # 8  the three branches map as registered, and the impossible cell is
    #    refused instead of being given a letter
    refused = False
    try:
        branch(3, 2)
    except ValueError:
        refused = True
    chk("8  branch(): tail>0 approached, tail=0 with reachable>0 empty and "
        "reachable, reachable=0 not representable; a tail larger than what "
        "could represent it is refused",
        branch(1, 5) == "approached" and branch(0, 5) == "empty, reachable"
        and branch(0, 0) == "not representable" and refused)

    # 9  the cache is on the grid the reachability assumes, and a planted
    #    off-grid state is counted
    fr_all, ix_all = [], []
    for nm, v in rows.items():
        t = tick[nm]
        fr_all += [a // t for a, _ in v]
        ix_all += [b // t for _, b in v]
    parity, beyond, edge = grid_breaks(fr_all, ix_all)
    planted = grid_breaks(fr_all + [5, 6], ix_all + [4, 5])
    chk("9  every loaded state has the friction count's parity and an index "
        "of at most k - 2 (parity breaks %d, above k-2 %d, on the knife edge "
        "%d); two planted off-grid states are counted" % (parity, beyond, edge),
        parity == 0 and beyond == 0 and planted[0] == parity + 2)

    # 10 the three cells this file got wrong, as known answers on the default
    #    carrier: states whose k can represent the cut
    def can(nm, cut):
        t = tick[nm]
        return sum(1 for a, _ in rows[nm] if reaches(a // t, cut))

    known = (("CLQ3-CLV3", 0.8, 0), ("CLU3-CLV3", 0.6, 0), ("RBU3-RBV3", 0.9, 252))
    got = [(nm, cut, can(nm, cut)) for nm, cut, _ in known if nm in rows]
    chk("10 on the default carrier the cut is representable for %s"
        % ", ".join("%s at %.1f: %d states" % g for g in got),
        os.path.basename(TSV) != "two_classes_ch382.tsv"
        or got == list(known))
    print("\n  %d/10" % (10 - len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--lead" in sys.argv:
        sys.exit(lead(a))
    sys.exit(cross(a) if "--cross" in sys.argv else run(a[0] if a else None))
