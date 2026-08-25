#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Candidate 3 of the rival's mechanism list: SIMULTANEOUS DETERMINATION,
plus the edge-shape pass that decides whether the top of rho is a wall.

WHY THIS FILE EXISTS
====================
b4 section 5.1's rival says friction sets a band and the index half fills it.
Five ways that could happen have been tested and four are dead:

    1  hard boundary, rho pushed back from 1      see --edge below; the pooled
                                                  reading was drawn on three
                                                  instruments and does not carry
    2  soft causal, friction leads the index      dead: every off-zero median
                                                  inside +-0.029 out to +-2000 updates
    4  states selected on the friction level      dead: median seq gap flat across
                                                  all five friction quintiles
    5  a persistent wedge inside the index        alive on RBU3-RBV3 only, and that
                                                  instrument carries no conclusion
    6  shared quotes, a bookkeeping identity      knocked down, and it explains the
                                                  lag-0 correlation away

Candidate 3 is the one with no dynamics in it at all: the quote setter picks the
displacement and the spread in the SAME decision, so the index is scaled by the
friction and rho stays off 1 without anything ever adjusting. Nothing leads
anything, nothing is selected, so tests 2 and 4 are blind to it by construction.

THE OBJECT
==========
Writing the two halves out,

    friction = -(s_E + s_D)          s_E implied book spread, s_D direct
    index    = 2 * (mid_D - mid_E)
    rho      = 2|mid_D - mid_E| / (s_E + s_D)

so rho = 1 is exactly the two books touching, which is the no-arbitrage edge.
The discriminating object is the conditional law of |index| GIVEN friction:

    fully simultaneous     E[|index| | f] proportional to f, so beta = 1 and
                           E[rho | f] flat in f
    fully independent      E[|index| | f] constant, so beta = 0 and
                           E[rho | f] falls like 1/f

with beta = d log E|index| / d log f, estimated on five friction quintiles by
weighted least squares on the bin means. One printed number, one reading fixed
before the run:

    beta >= 0.70 on four or more of the resolvable instruments   candidate 3 alive
    beta <= 0.30 on four or more                                 candidate 3 dead
    anything else                                                report beta, no verdict

THE THIRD STATE IS NOT DECORATION. The middle branch has to exist here because
beta is a slope on a coarse integer grid and a slope near 0.5 means the data has
not answered the question.

AND A CHECK ON CANDIDATE 1, WHICH THIS RUN GETS FOR FREE
========================================================
"0.00% of states above rho 0.70" was read off three instruments. But at the
friction floor, f = 2 ticks, |index| can only be 0, 1 or 2 ticks and rho can
only be 0, 0.5 or 1. If tail mass lives at low friction and low-friction states
are simply rare, a pooled zero is a mixture artefact. So this run prints
P(rho >= 0.70) and max rho PER FRICTION BIN, and --edge prints the density of
rho next to what the grid could have represented there.

Same reachability gate as the tail run, recomputed here rather than copied:
median |index| >= 3 ticks, because an instrument whose index half never leaves
{0, 1, 2} cannot express a slope.

    python experiments/b13_cand3.py --selftest
    python experiments/b13_cand3.py [tsv ...]
    python experiments/b13_cand3.py --edge [tsv ...]
"""

import ast
import io
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHES = (
    os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch382.tsv"),
    os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch386.tsv"),
)
CACHES_V2 = tuple(p.replace(".tsv", "_v2.tsv") for p in CACHES)
NBIN = 5
MIN_MED_INDEX = 3      # ticks; the tail run's reachability gate
TAIL_CUT = 0.70
BETA_ALIVE = 0.70
BETA_DEAD = 0.30
EDGE_STEP = 20         # rho bins of width 1/20


def load(path):
    """name -> [(friction, |index|)] in TICKS, the tick read off the data as the
    gcd of every printed magnitude for that instrument."""
    raw = defaultdict(list)
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 4:
                continue
            fr, ix = int(f[2]), int(f[3])
            if fr >= 0:
                continue
            raw[f[0]].append((-fr, abs(ix)))
    out = {}
    for nm, v in raw.items():
        g = 0
        for a, b in v:
            for x in (a, b):
                while x:
                    g, x = x, g % x
        if not g:
            continue
        out[nm] = [(a // g, b // g) for a, b in v]
    return out


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return 0.0
    return float(s[n // 2]) if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def quantile_bins(vals, k):
    """k contiguous groups of the sorted distinct friction levels, split so that
    the counts are as close to equal as the integer grid permits. Split points
    are levels, never counts, so a level is never torn across two bins."""
    lv = sorted(set(vals))
    if len(lv) <= k:
        return lv[:-1]
    cnt = defaultdict(int)
    for v in vals:
        cnt[v] += 1
    target = len(vals) / float(k)
    cuts, run, made = [], 0, 0
    for v in lv[:-1]:
        run += cnt[v]
        if run >= target * (made + 1) and made < k - 1:
            cuts.append(v)
            made += 1
    return cuts


def binof(f, cuts):
    i = 0
    while i < len(cuts) and f > cuts[i]:
        i += 1
    return i


def wls(xs, ys, ws):
    """weighted least squares slope; returns None when it is not identified."""
    sw = sum(ws)
    if sw <= 0 or len(xs) < 2:
        return None
    mx = sum(w * x for w, x in zip(ws, xs)) / sw
    my = sum(w * y for w, y in zip(ws, ys)) / sw
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
    if sxx <= 0:
        return None
    sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys))
    return sxy / sxx


def analyse(pairs):
    """the per-instrument object: one row per friction bin, then beta."""
    cuts = quantile_bins([f for f, _ in pairs], NBIN)
    rows = defaultdict(list)
    for f, a in pairs:
        rows[binof(f, cuts)].append((f, a))
    table = []
    for b in sorted(rows):
        v = rows[b]
        n = len(v)
        mf = sum(f for f, _ in v) / float(n)
        ma = sum(a for _, a in v) / float(n)
        rho = [a / float(f) for f, a in v]
        table.append({
            "bin": b, "n": n,
            "f_lo": min(f for f, _ in v), "f_hi": max(f for f, _ in v),
            "mean_f": mf, "mean_absix": ma,
            "mean_rho": sum(rho) / n,
            "p_tail": sum(1 for r in rho if r >= TAIL_CUT) / float(n),
            "max_rho": max(rho),
            "n_absix_levels": len(set(a for _, a in v)),
        })
    good = [t for t in table if t["mean_absix"] > 0 and t["mean_f"] > 0]
    beta = wls([math.log(t["mean_f"]) for t in good],
               [math.log(t["mean_absix"]) for t in good],
               [float(t["n"]) for t in good])
    ratio = None
    if len(good) >= 2:
        lo, hi = good[0], good[-1]
        if hi["mean_f"] > lo["mean_f"]:
            ratio = math.log(hi["mean_absix"] / lo["mean_absix"]) / \
                math.log(hi["mean_f"] / lo["mean_f"])
    return table, beta, ratio, len(table) - len(good)


def run(paths):
    data = {}
    for p in paths:
        if not os.path.exists(p):
            sys.stderr.write("missing %s\n" % p)
            continue
        for nm, v in load(p).items():
            data[nm] = v
    if not data:
        sys.stderr.write("no cache read\n")
        return 1

    keep, drop = [], []
    for nm, v in sorted(data.items()):
        (keep if median([a for _, a in v]) >= MIN_MED_INDEX else drop).append(nm)
    print("可达闸：med |index| >= %d ticks" % MIN_MED_INDEX)
    print("  过闸 %d 条：%s" % (len(keep), ", ".join(keep)))
    print("  不可达 %d 条（不读）：%s" % (len(drop), ", ".join(drop)))
    print("")

    verdicts = {}
    for nm in keep:
        table, beta, ratio, dead_bins = analyse(data[nm])
        verdicts[nm] = beta
        print("%s   n=%d" % (nm, len(data[nm])))
        print("  %3s %7s %11s %9s %9s %9s %11s %9s %7s"
              % ("bin", "n", "f范围", "mean_f", "mean|ix|", "mean_rho",
                 "P(rho>=.7)", "max_rho", "|ix|值"))
        for t in table:
            print("  %3d %7d %11s %9.2f %9.3f %9.4f %11.4f %9.4f %7d"
                  % (t["bin"], t["n"], "%d-%d" % (t["f_lo"], t["f_hi"]),
                     t["mean_f"], t["mean_absix"], t["mean_rho"],
                     t["p_tail"], t["max_rho"], t["n_absix_levels"]))
        print("  beta(WLS 5 bins) = %s    beta(top/bottom) = %s%s"
              % ("None" if beta is None else "%.4f" % beta,
                 "None" if ratio is None else "%.4f" % ratio,
                 "" if not dead_bins else "    (%d bin(s) with mean|ix|=0 dropped)"
                 % dead_bins))
        print("")

    live = sum(1 for b in verdicts.values() if b is not None and b >= BETA_ALIVE)
    dead = sum(1 for b in verdicts.values() if b is not None and b <= BETA_DEAD)
    print("跑前登记的读法：beta>=%.2f 计 alive，beta<=%.2f 计 dead，四条及以上定案"
          % (BETA_ALIVE, BETA_DEAD))
    print("  alive %d / dead %d / 中间 %d，共 %d 条"
          % (live, dead, len(verdicts) - live - dead, len(verdicts)))
    if live >= 4:
        print("  裁：候选 3 成立")
    elif dead >= 4:
        print("  裁：候选 3 不成立")
    else:
        print("  裁：不裁，只报 beta（三态的中间那个）")
    return 0


# ---------------------------------------------------------------- edge shape
#: Registered before this pass was run. The tail table alone cannot tell a
#: BINDING boundary from a distribution that simply peters out, because both
#: put zero mass at the very top. What separates them is the shape of the last
#: populated bins next to what the grid could have represented there:
#:
#:   cliff   the top populated bin is comparable to the one below it, and the
#:           bins above it are REPRESENTABLE and empty
#:   decay   the counts fall smoothly to zero with no discontinuity
#:
#: So this prints the count and the representable count per 0.05 bin. No
#: threshold is drawn on anything; the object is the two rows of integers.


def representable(k, lo20, hi20):
    """can an integer index a in [0, k] land in [lo20/20, hi20/20) at friction
    k? exact integer arithmetic, no float compare near the bin walls."""
    lo = -(-lo20 * k // EDGE_STEP)                 # ceil(lo20*k/20)
    hi = (hi20 * k + EDGE_STEP - 1) // EDGE_STEP   # ceil(hi20*k/20)
    if hi20 * k % EDGE_STEP == 0:
        hi = hi20 * k // EDGE_STEP
    return lo <= min(hi - 1, k)


def edge(paths):
    data = {}
    for q in paths:
        if os.path.exists(q):
            data.update(load(q))
    lo0 = 10
    print("rho 密度，宽 0.05 的桶。上行 n = 落在桶里的状态数；")
    print("下行 r = 该桶在自己的 friction 网格上可被表示的状态数。")
    print("r>0 而 n=0 的桶，是网格能表示而世界没去的地方。")
    print("")
    heads = ["%.2f" % (b / float(EDGE_STEP)) for b in range(lo0, EDGE_STEP)]
    print("%-13s %6s %s" % ("spread", "n", "".join("%7s" % h for h in heads)))
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        cn = [0] * (EDGE_STEP - lo0)
        rp = [0] * (EDGE_STEP - lo0)
        for f, a in v:
            for i, b in enumerate(range(lo0, EDGE_STEP)):
                if b * f <= a * EDGE_STEP < (b + 1) * f:
                    cn[i] += 1
                if representable(f, b, b + 1):
                    rp[i] += 1
        print("%-13s %6d %s" % (nm, len(v), "".join("%7d" % c for c in cn)))
        print("%-13s %6s %s" % ("", "r", "".join("%7d" % c for c in rp)))
    return 0



# ------------------------------------------------------------------ the gap
#: Registered before this pass was run. --edge showed every instrument stopping
#: dead somewhere between rho 0.60 and 0.95 with the bins above it fully
#: representable, but at SIX DIFFERENT PLACES. A no-arbitrage edge sits at
#: rho = 1 for all of them, so the rival's remaining move is a cost-adjusted
#: edge at rho = 1 - c/k with an instrument-specific cost c in ticks.
#:
#: That variant is testable without any fee schedule, because c is a distance
#: in TICKS, not in rho. Take
#:
#:     gap = friction - |index|            both in ticks, gap >= 0 by rho <= 1
#:
#: and a binding cost edge at c says gap has a HARD FLOOR at c with mass piled
#: on it, the same way a price floor puts mass on the floor. No edge says the
#: floor is wherever the thinnest states happen to fall and the mass sits well
#: above it.
#:
#:     floor small and common within a product, with a pile on it   edge binds
#:     floor large, instrument-specific, no pile                    no edge
#:
#: The object printed is the low end of the gap histogram, per instrument, plus
#: the same restricted to the top friction quintile: a cost floor is a constant
#: number of ticks, so widening the friction must not move it.
GAPS = 10


def gap(paths):
    data = {}
    for q in paths:
        if os.path.exists(q):
            data.update(load(q))
    print("gap = friction - |index|，单位 tick。cost 边界的预言是硬地板加堆积。")
    print("每条两行：上行全样本，下行只取 friction 最高的那一档（地板不该随之移动）。")
    print("")
    print("%-13s %6s %6s %6s %s" % ("spread", "n", "min", "med",
                                    "".join("%7d" % g for g in range(GAPS))))
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        for tag, sub in (("all", v), ("hi-f", None)):
            if sub is None:
                cuts = quantile_bins([f for f, _ in v], NBIN)
                sub = [(f, a) for f, a in v if binof(f, cuts) == NBIN - 1]
                if not sub:
                    continue
            gs = [f - a for f, a in sub]
            h = [sum(1 for g in gs if g == i) for i in range(GAPS)]
            print("%-13s %6d %6d %6.1f %s"
                  % (nm if tag == "all" else "", len(sub), min(gs), median(gs),
                     "".join("%7d" % c for c in h)))
    return 0



# --------------------------------------------------- the asymmetry, stage two
#: REGISTERED BEFORE THE V2 DUMP EXISTED. The file this reads has not been
#: written yet at the time these lines were fixed; only the four-column cache
#: is on disk.
#:
#: With the four class prices eb, ef (implied bid, ask) and db, da (direct),
#:
#:     u = ef - eb      v = da - db      m = mid_D - mid_E
#:     f = u + v        g = |u - v|      index = 2m
#:
#: and the ONLY constraint tying m to u and v is the pair ef >= db, da >= eb,
#: which is |index| <= f and nothing else. So g does not bound the index at any
#: given f: a dependence of |index| on g HOLDING f FIXED is not mechanical.
#: That is what makes this test the one that separates the two accounts.
#:
#:   Theorem 6(5)   the spread term in S - S' vanishes iff s_a/M_a = s_b/M_b,
#:                  and the two classes quote the same instrument so M_a = M_b.
#:                  The class difference therefore enters through g, the spread
#:                  ASYMMETRY, and |index| must rise with g at fixed f
#:   candidate 3    the quote setter picks displacement and width together, so
#:                  only the width f matters and |index| is flat in g
#:
#: THE OBJECT is the two-way table: f quintile by g tercile within that
#: quintile, mean |index| in each cell. The reading fixed here:
#:
#:   mean |index| rising across g within most f rows, most instruments
#:                                              -> the index carries the class
#:                                                 asymmetry, candidate 3 falls
#:   flat or non-monotone on most               -> band filling, candidate 3 stands
#:   anything else                              -> report, no verdict
#:
#: The OLS coefficient on g controlling for f is printed beside the table as a
#: summary. NO LINE IS DRAWN ON IT: discipline 11. The table is the criterion.
#:
#: Collinearity is checked first and can void the whole test: if g is nearly a
#: function of f the two cannot be separated and the run reads nothing (D15).


def load6(path):
    """the v2 cache: name, seq, friction, index, s_e, s_d. Ticks, gcd read off
    the data exactly as load() does, so the two agree on the tick."""
    raw = defaultdict(list)
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 6:
                continue
            fr, ix, se, sd = int(c[2]), int(c[3]), int(c[4]), int(c[5])
            if fr >= 0 or fr != -(se + sd):
                continue
            raw[c[0]].append((-fr, abs(ix), abs(se - sd)))
    out = {}
    for nm, v in raw.items():
        gg = 0
        for t in v:
            for x in t:
                while x:
                    gg, x = x, gg % x
        if not gg:
            continue
        out[nm] = [(a // gg, b // gg, c // gg) for a, b, c in v]
    return out


def ols3(rows):
    """|index| on [1, f, g]; returns (coefficients, standard errors) or None."""
    n = len(rows)
    if n < 10:
        return None
    X = [[1.0, float(f), float(g)] for f, _, g in rows]
    y = [float(a) for _, a, _ in rows]
    A = [[sum(X[i][r] * X[i][c] for i in range(n)) for c in range(3)] + \
         [sum(X[i][r] * y[i] for i in range(n))] for r in range(3)]
    inv = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for c in range(3):
        piv = max(range(c, 3), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-9:
            return None
        A[c], A[piv] = A[piv], A[c]
        inv[c], inv[piv] = inv[piv], inv[c]
        d = A[c][c]
        A[c] = [x / d for x in A[c]]
        inv[c] = [x / d for x in inv[c]]
        for r in range(3):
            if r == c:
                continue
            k = A[r][c]
            A[r] = [a - k * b for a, b in zip(A[r], A[c])]
            inv[r] = [a - k * b for a, b in zip(inv[r], inv[c])]
    beta = [A[r][3] for r in range(3)]
    rss = sum((y[i] - sum(beta[j] * X[i][j] for j in range(3))) ** 2
              for i in range(n))
    s2 = rss / float(n - 3)
    se = [math.sqrt(max(s2 * inv[j][j], 0.0)) for j in range(3)]
    return beta, se


def corr(xs, ys):
    n = len(xs)
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx <= 0 or sy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def asym(paths):
    data = {}
    for q in paths:
        if os.path.exists(q):
            data.update(load6(q))
        else:
            sys.stderr.write("missing %s\n" % q)
    if not data:
        sys.stderr.write("no v2 cache read; run the --dump with the two extra "
                         "columns first\n")
        return 1
    print("f = s_e + s_d（摩擦），g = |s_e - s_d|（两类价差的不对称）")
    print("给定 f，g 不对 |index| 施加任何约束，所以这一列的斜率不是机械的。")
    print("")
    up = flat = 0
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        c = corr([float(f) for f, _, _ in v], [float(g) for _, _, g in v])
        r = ols3(v)
        cuts = quantile_bins([f for f, _, _ in v], NBIN)
        rows = defaultdict(list)
        for t in v:
            rows[binof(t[0], cuts)].append(t)
        print("%s   n=%d   corr(f,g)=%s" % (nm, len(v),
              "None" if c is None else "%.4f" % c))
        if c is not None and abs(c) > 0.90:
            print("  共线，本条不读（D15：只有一个可达分支的判据不承载信息）")
            print("")
            continue
        print("  %5s %7s %9s   %s" % ("f档", "n", "mean_f",
              "  ".join("g档%d: mean|ix| (n)" % i for i in range(3))))
        rising = 0
        total = 0
        for b in sorted(rows):
            sub = rows[b]
            gc = quantile_bins([g for _, _, g in sub], 3)
            cell = defaultdict(list)
            for t in sub:
                cell[binof(t[2], gc)].append(t)
            ms = []
            for j in range(3):
                s = cell.get(j, [])
                ms.append((sum(a for _, a, _ in s) / float(len(s)), len(s))
                          if s else (float("nan"), 0))
            got = [m for m, k in ms if k]
            if len(got) >= 2:
                total += 1
                if all(got[i] < got[i + 1] for i in range(len(got) - 1)):
                    rising += 1
            print("  %5d %7d %9.2f   %s"
                  % (b, len(sub), sum(f for f, _, _ in sub) / float(len(sub)),
                     "  ".join("%14s" % ("%.2f (%d)" % m if m[1] else "-") for m in ms)))
        tag = "升" if total and rising * 2 > total else "平/非单调"
        (globals().__setitem__("_", 0))
        if total and rising * 2 > total:
            up += 1
        else:
            flat += 1
        print("  g 档单调上升的 f 档：%d / %d   →  %s" % (rising, total, tag))
        if r:
            beta, se = r
            print("  OLS |ix| = a + b*f + c*g :  b = %.4f (%.4f)   c = %.4f (%.4f)"
                  % (beta[1], se[1], beta[2], se[2]))
        print("")
    print("跑前登记的读法：多数 f 档单调上升记「升」")
    print("  升 %d 条 / 平 %d 条，共 %d 条" % (up, flat, up + flat))
    if up * 2 > up + flat:
        print("  裁：|index| 载着两类价差的不对称，候选 3 倒")
    elif flat * 2 > up + flat:
        print("  裁：|index| 只随 f 走，候选 3 站住，本载体读不出 5.1")
    else:
        print("  裁：不裁（三态的中间那个）")
    return 0



# ------------------------------------------- the asymmetry again, right shape
#: REGISTERED BEFORE THIS PASS RAN, and it exists because the FIRST shape was
#: one this repository has already banned. --asym cut g into terciles inside
#: each f quintile and asked for a monotone rise across three cells. Cells came
#: back with n = 1, 2, 5. "monotone across three cells" is the all-vote shape
#: that discipline 11 forbids: one thin cell flips the whole row. The verdict it
#: returned stands in the record and so does this note; the criterion was mine
#: and it was badly built.
#:
#: Right shape, three changes and nothing else:
#:   1  g on a FIXED grid 0, 1, 2, 3, >=4, not a data-dependent split
#:   2  a cell with fewer than MIN_CELL observations is not read at all
#:   3  no monotonicity across three points. One comparison per row: the mean
#:      |index| at the highest readable g against the lowest readable g
#:
#: What is printed is the table. What is counted is how many (instrument, f row)
#: comparisons come out positive, out of the readable ones. THE COUNT IS
#: REPORTED, NOT THRESHOLDED. Theorem 6(5) wants positive nearly everywhere;
#: candidate 3 wants a coin flip. A count near half is the third state and says
#: the carrier did not answer.
MIN_CELL = 30
GGRID = (0, 1, 2, 3, 4)


def asym2(paths):
    data = {}
    for q in paths:
        if os.path.exists(q):
            data.update(load6(q))
    if not data:
        sys.stderr.write("no v2 cache read\n")
        return 1
    print("g 固定网格 0,1,2,3,>=4；每格少于 %d 个观测就不读（印成 -）" % MIN_CELL)
    print("每个 f 档只做一次比较：可读的最高 g 档 减 可读的最低 g 档")
    print("")
    pos = neg = 0
    per = []
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        c = corr([float(f) for f, _, _ in v], [float(g) for _, _, g in v])
        if c is not None and abs(c) > 0.90:
            per.append((nm, len(v), c, None))
            continue
        cuts = quantile_bins([f for f, _, _ in v], NBIN)
        rows = defaultdict(list)
        for t in v:
            rows[binof(t[0], cuts)].append(t)
        tab, p, q_ = [], 0, 0
        for b in sorted(rows):
            sub = rows[b]
            cell = defaultdict(list)
            for f, a, g in sub:
                cell[min(g, GGRID[-1])].append(a)
            ms = []
            for g in GGRID:
                s = cell.get(g, [])
                ms.append((sum(s) / float(len(s)), len(s)) if len(s) >= MIN_CELL
                          else (None, len(s)))
            got = [(g, m) for g, (m, k) in zip(GGRID, ms) if m is not None]
            d = None
            if len(got) >= 2:
                d = got[-1][1] - got[0][1]
                if d > 0:
                    p += 1
                else:
                    q_ += 1
            tab.append((b, len(sub), sum(f for f, _, _ in sub) / float(len(sub)),
                        ms, d))
        pos += p
        neg += q_
        per.append((nm, len(v), c, (tab, p, q_)))

    for nm, n, c, r in per:
        print("%s   n=%d   corr(f,g)=%s" % (nm, n, "None" if c is None else "%.4f" % c))
        if r is None:
            print("  共线，本条不读")
            print("")
            continue
        tab, p, q_ = r
        print("  %4s %7s %8s   %s   %8s"
              % ("f档", "n", "mean_f",
                 " ".join("%13s" % ("g=%d" % g if g < GGRID[-1] else "g>=%d" % g)
                          for g in GGRID), "高-低"))
        for b, k, mf, ms, d in tab:
            print("  %4d %7d %8.2f   %s   %8s"
                  % (b, k, mf,
                     " ".join("%13s" % ("%.2f(%d)" % (m, kk) if m is not None
                                        else "-(%d)" % kk) for m, kk in ms),
                     "-" if d is None else "%+.2f" % d))
        print("  本条：正 %d / 负或平 %d" % (p, q_))
        print("")
    print("可读的比较共 %d 次：正 %d，负或平 %d，正的占 %.4f"
          % (pos + neg, pos, neg, pos / float(pos + neg) if pos + neg else 0.0))
    print("定理 6(5) 要的是几乎全正，候选 3 要的是掷硬币。只报这个数，不卡线。")
    return 0


def selftest():
    n = 0

    def ck(cond, what):
        nonlocal n
        assert cond, what
        n += 1

    # 1  the module contains no deletion call. AST walk, so this check does not
    #    count its own text: the eight-times pitfall in this repository.
    tree = ast.parse(io.open(os.path.abspath(__file__), encoding="utf-8").read())
    banned = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else \
                (f.id if isinstance(f, ast.Name) else "")
            if nm in ("remove", "unlink", "rmtree", "rmdir"):
                banned.add(nm)
    ck(not banned, "deletion call present: %s" % banned)

    # 2  beta = 1 when the index is a fixed fraction of the friction
    syn = [(f, f // 2) for f in range(4, 60) for _ in range(20)]
    _, b, _, _ = analyse(syn)
    ck(b is not None and abs(b - 1.0) < 0.05, "proportional beta %s" % b)

    # 3  beta = 0 when the index is drawn independently of the friction
    ix = [1, 2, 3, 4, 5, 6, 7, 8]
    syn = [(f, ix[i % len(ix)]) for f in range(20, 80) for i in range(20)]
    _, b, _, _ = analyse(syn)
    ck(b is not None and abs(b) < 0.05, "independent beta %s" % b)

    # 4  rho never exceeds 1 on real data: a counterexample is a code error and
    #    voids the run, exactly as b4_two_classes R1 has it
    seen = 0
    for p in CACHES:
        if not os.path.exists(p):
            continue
        for nm, v in load(p).items():
            for f, a in v:
                ck(a <= f, "rho>1 on %s: %d/%d" % (nm, a, f))
                seen += 1
    ck(seen > 0, "no real rows read")

    # 5  the grid guard fires: at the friction floor the index has three levels
    syn = [(2, i % 3) for i in range(500)]
    t, _, _, _ = analyse(syn)
    ck(max(x["n_absix_levels"] for x in t) <= 3, "floor grid not flagged")

    # 6  bins never tear one friction level across two bins
    syn = [(f, 1) for f in (3, 3, 3, 3, 9, 9, 20, 20, 20, 41)]
    cuts = quantile_bins([f for f, _ in syn], NBIN)
    ck(len(set(binof(f, cuts) for f, _ in syn if f == 3)) == 1, "level torn")

    # 7  wls declines to answer when x has no spread
    ck(wls([1.0, 1.0], [0.0, 1.0], [1.0, 1.0]) is None, "wls should decline")

    # 8  representable agrees with brute force on every small friction
    for k in range(1, 140):
        for b in range(10, EDGE_STEP):
            brute = any(b * k <= a * EDGE_STEP < (b + 1) * k for a in range(k + 1))
            ck(representable(k, b, b + 1) == brute,
               "representable k=%d bin=%d" % (k, b))

    # 9  the gap is non-negative on every real row, which is rho <= 1 again
    #    stated in tick units, and it is the quantity --gap floors
    for p in CACHES:
        if not os.path.exists(p):
            continue
        for nm, v in load(p).items():
            ck(min(f - a for f, a in v) >= 0, "negative gap on %s" % nm)

    # 10  ols3 recovers a planted coefficient on g at fixed f
    syn = [(f, 3 + 2 * g, g) for f in range(10, 40) for g in range(0, 8)]
    beta, se = ols3(syn)
    ck(abs(beta[2] - 2.0) < 1e-6, "planted g coefficient %s" % beta[2])
    ck(abs(beta[1]) < 1e-6, "f should not load: %s" % beta[1])

    # 11  and returns zero on g when the index ignores it
    syn = [(f, f // 3, g) for f in range(10, 40) for g in range(0, 8)]
    beta, se = ols3(syn)
    ck(abs(beta[2]) < 1e-6, "g should not load: %s" % beta[2])

    # 12  ols3 declines rather than inverting a singular design
    ck(ols3([(f, 1, f) for f in range(20)]) is None, "singular design accepted")

    # 13  corr is 1 on a copy and 0 on an orthogonal pair
    ck(abs(corr([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) - 1.0) < 1e-12, "corr copy")
    ck(abs(corr([1.0, 2.0, 3.0], [1.0, 0.0, 1.0])) < 1e-12, "corr orthogonal")

    # 14  load6 rejects a row whose friction contradicts its two spreads, which
    #     is the identity the dump writes and the only guard on the new columns
    import tempfile
    fd, tp = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(tp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        fh.write(u"X\t1\t-6\t2\t5\t1\n")     # consistent
        fh.write(u"X\t2\t-6\t2\t4\t1\n")     # 4+1 != 6, must be dropped
    got = load6(tp)
    ck(len(got.get("X", [])) == 1, "load6 kept a contradictory row")

    # 15  the fixed g grid puts everything at or above the top level into the
    #     top cell, which is what makes that cell readable at all
    ck(min(7, GGRID[-1]) == 4 and min(2, GGRID[-1]) == 2, "g grid clamp")

    print("selftest ok: %d checks" % n)
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = [a for a in argv if not a.startswith("-")]
    if "--edge" in argv:
        return edge(paths or list(CACHES))
    if "--gap" in argv:
        return gap(paths or list(CACHES))
    if "--asym2" in argv:
        return asym2(paths or list(CACHES_V2))
    if "--asym" in argv:
        return asym(paths or list(CACHES_V2))
    return run(paths or list(CACHES))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
