#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Does this carrier carry Theorem 6(5) at all? The level decides it.

WHY THIS FILE EXISTS, AND WHAT IT RETRACTS
==========================================
b13_cand3.py --asym regressed |index| on the spread asymmetry g and reported
that candidate 3 survives. That reading is WITHDRAWN HERE, before this file was
run, on algebra alone.

b4_directed_edges.md section 5.1 writes the index half as

    S - S'  =  2 log(mid_D / mid_E)              mid = sqrt(bid*ask)

and Theorem 6(5) splits it into

    S - S'  =  2 log(M_D / M_E)                                  midpoint part
             + log(1 - (s_D/2M_D)^2) - log(1 - (s_E/2M_E)^2)     spread part

with the CLASS ASYMMETRY LIVING IN THE SPREAD PART. What b4_two_classes.py
--dump writes is

    index = (db + da) - (eb + ef) = 2 (M_D - M_E)

which is the midpoint part, arithmetic, times a level. **The spread part is not
in it.** So --asym asked whether the midpoint difference depends on the spread
asymmetry, and Theorem 6(5) never claimed it does. The test had no power against
the thing it was built to detect and candidate 3 surviving it is not evidence.

WHAT THIS FILE ASKS INSTEAD
===========================
Whether the log construction is even defined here. A calendar spread's price is
a DIFFERENCE of two futures prices and can sit at zero or below, and then
sqrt(bid*ask) is not a real number and log(mid) does not exist. The whole of
section 5.1 is written in logs of rates.

Registered before the v3 cache existed, all three branches reachable:

  A  a material share of states has bid <= 0
     -> the log construction is undefined on this carrier. Everything computed
        in price units is a SUBSTITUTE for the theorem's quantity. Report the
        share and stop reading the arithmetic rho as if it were the theorem's

  B  bid > 0 everywhere and s/M small
     -> rho_code and rho_thm agree to first order, the chain to date stands, and
        the spread part is measurable. Then report the share of states where
        |spread part| > |midpoint part|, which is Theorem 6(5)'s leak measured
        rather than bounded. B14 leg B got about 3% of cells on its carrier

  C  bid > 0 but s/M not small
     -> the two rhos differ materially. Print both and their correlation. The
        candidate chain has to be re-read on rho_thm before any of it counts

The object printed is the level and the relative spread per instrument, not a
verdict on either.

    python experiments/b13_level.py --selftest
    python experiments/b13_level.py [tsv ...]
"""

import ast
import io
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHES = (os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch382_v3.tsv"),
          os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch386_v3.tsv"))
SMALL = 0.05      # what "s/M small" is taken to mean, fixed here before the run


def load8(path):
    """name -> [(eb, ef, db, da)] in raw PRICE9. No tick division: the level has
    to stay in its own units or s/M is not a ratio of like things."""
    out = defaultdict(list)
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 8:
                continue
            fr, ix, se, sd, eb, db = (int(c[2]), int(c[3]), int(c[4]),
                                      int(c[5]), int(c[6]), int(c[7]))
            if fr != -(se + sd):
                continue
            ef, da = eb + se, db + sd
            if (db + da) - (eb + ef) != ix:
                continue
            out[c[0]].append((eb, ef, db, da))
    return dict(out)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return float(s[n // 2]) if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def parts(eb, ef, db, da):
    """the theorem's two halves in logs, or None when the logs do not exist."""
    if min(eb, ef, db, da) <= 0:
        return None
    ME, MD = 0.5 * (eb + ef), 0.5 * (db + da)
    sE, sD = float(ef - eb), float(da - db)
    mid_part = 2.0 * math.log(MD / ME)
    spr_part = (math.log(1.0 - (sD / (2.0 * MD)) ** 2)
                - math.log(1.0 - (sE / (2.0 * ME)) ** 2))
    fric = math.log(float(eb) / ef) + math.log(float(db) / da)
    return mid_part, spr_part, fric


def run(paths):
    data = {}
    for p in paths:
        if os.path.exists(p):
            data.update(load8(p))
        else:
            sys.stderr.write("missing %s\n" % p)
    if not data:
        sys.stderr.write("no v3 cache; run scripts/b13_redump_v2.cmd first\n")
        return 1

    print("PRICE9 单位，1e9 = 1.0 个报价单位。M = (bid+ask)/2 是水平。")
    print("")
    print("%-13s %8s %11s %11s %9s %9s %9s %9s"
          % ("spread", "n", "min M_D", "med M_D", "P(bid<=0)",
             "med s_E/M_E", "med s_D/M_D", "max s/M"))
    tot = neg = 0
    flag = []
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        n = len(v)
        MD = [0.5 * (db + da) for _, _, db, da in v]
        bad = sum(1 for eb, ef, db, da in v if min(eb, ef, db, da) <= 0)
        rE, rD = [], []
        for eb, ef, db, da in v:
            ME, MDx = 0.5 * (eb + ef), 0.5 * (db + da)
            if ME > 0:
                rE.append((ef - eb) / ME)
            if MDx > 0:
                rD.append((da - db) / MDx)
        mx = max(rE + rD) if (rE or rD) else float("nan")
        print("%-13s %8d %11.4f %11.4f %9.4f %9.4f %9.4f %9.2f"
              % (nm, n, min(MD) / 1e9, median(MD) / 1e9, bad / float(n),
                 median(rE) if rE else float("nan"),
                 median(rD) if rD else float("nan"), mx))
        tot += n
        neg += bad
        flag.append((nm, bad / float(n), median(rE) if rE else float("nan")))

    share = neg / float(tot)
    print("")
    print("全样本 %d 个状态，bid<=0 的占 %.4f" % (tot, share))
    if share > 0.001:
        print("")
        print("分支 A：log 构造在本载体上不成立。")
        print("  sqrt(bid*ask) 在这些状态上不是实数，log(mid) 不存在，")
        print("  而 5.1 整节写在 log 上。价格单位算出来的 rho 是替代品，不是定理的量。")
        return 0

    print("")
    print("bid 全为正，可以形成定理的两半。下面是它们。")
    print("%-13s %8s %12s %12s %12s %10s %10s"
          % ("spread", "n", "med|中点部|", "med|价差部|", "价差部>中点部",
             "corr rho", "med差"))
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        rows = [parts(*t) for t in v]
        rows = [r for r in rows if r]
        if not rows:
            continue
        mp = [abs(a) for a, _, _ in rows]
        sp = [abs(b) for _, b, _ in rows]
        win = sum(1 for a, b, _ in rows if abs(b) > abs(a)) / float(len(rows))
        rt = [abs(a + b) / -c for a, b, c in rows if c < 0]
        rc = []
        for eb, ef, db, da in v:
            f = (ef - eb) + (da - db)
            if f > 0:
                rc.append(abs((db + da) - (eb + ef)) / float(f))
        k = min(len(rt), len(rc))
        cc = float("nan")
        if k > 2:
            ma = sum(rt[:k]) / k
            mb = sum(rc[:k]) / k
            sa = math.sqrt(sum((x - ma) ** 2 for x in rt[:k]))
            sb = math.sqrt(sum((x - mb) ** 2 for x in rc[:k]))
            if sa > 0 and sb > 0:
                cc = sum((x - ma) * (y - mb)
                         for x, y in zip(rt[:k], rc[:k])) / (sa * sb)
        print("%-13s %8d %12.3e %12.3e %12.4f %10.4f %10.4f"
              % (nm, len(rows), median(mp), median(sp), win, cc,
                 median([abs(x - y) for x, y in zip(rt[:k], rc[:k])]) if k else
                 float("nan")))
    return 0



# ------------------------------------------------ the defined subsample only
#: REGISTERED BEFORE THIS PASS RAN. Branch A fired: 14 of 23 instruments have
#: bid <= 0 in EVERY state, and the log construction does not exist there. The
#: other 9 never do, and on those the theorem's quantity is computable for the
#: first time in this station.
#:
#: What is asked on the 9, and the reading, fixed here:
#:
#:   share(|spread part| > |midpoint part|)
#:       this is Theorem 6(5)'s leak MEASURED rather than bounded. B14 leg B
#:       got about 3% of cells on its own carrier. Report the number
#:
#:   corr(rho_thm, rho_code) and the median |rho_thm - rho_code|
#:       near 1 and near 0 means the chain's readings transfer to these 9
#:       unchanged. Otherwise every reading in the chain has to be redone on
#:       rho_thm before any of it counts
#:
#: No threshold on either. The object is the table.
DEFINED_ONLY = True


def defined(paths):
    data = {}
    for p in paths:
        if os.path.exists(p):
            data.update(load8(p))
    if not data:
        sys.stderr.write("no v3 cache\n")
        return 1
    keep = [nm for nm, v in data.items()
            if all(min(t) > 0 for t in v)]
    drop = [nm for nm in data if nm not in keep]
    print("log 构造有定义的 %d 条（每个状态 bid 都为正）：" % len(keep))
    print("  " + ", ".join(sorted(keep)))
    print("无定义的 %d 条，不读：" % len(drop))
    print("  " + ", ".join(sorted(drop)))
    print("")
    print("%-13s %8s %11s %11s %10s %10s %9s %9s %9s"
          % ("spread", "n", "med|中点部|", "med|价差部|", "价差>中点",
             "med rho_thm", "med rho_cd", "corr", "med|差|"))
    tn = tw = 0
    for nm in sorted(keep, key=lambda k: -len(data[k])):
        v = data[nm]
        mp, sp, rt, rc = [], [], [], []
        win = 0
        for eb, ef, db, da in v:
            a, b, c = parts(eb, ef, db, da)
            mp.append(abs(a))
            sp.append(abs(b))
            if abs(b) > abs(a):
                win += 1
            if c < 0:
                rt.append(abs(a + b) / -c)
                f = (ef - eb) + (da - db)
                rc.append(abs((db + da) - (eb + ef)) / float(f) if f > 0 else 0.0)
        n = len(v)
        tn += n
        tw += win
        k = len(rt)
        cc = float("nan")
        if k > 2:
            ma, mb = sum(rt) / k, sum(rc) / k
            sa = math.sqrt(sum((x - ma) ** 2 for x in rt))
            sb = math.sqrt(sum((x - mb) ** 2 for x in rc))
            if sa > 0 and sb > 0:
                cc = sum((x - ma) * (y - mb) for x, y in zip(rt, rc)) / (sa * sb)
        print("%-13s %8d %11.3e %11.3e %10.4f %10.4f %9.4f %9.4f %9.2e"
              % (nm, n, median(mp), median(sp), win / float(n),
                 median(rt), median(rc), cc,
                 median([abs(x - y) for x, y in zip(rt, rc)])))
    print("")
    print("九条合计 %d 个状态，|价差部| > |中点部| 的占 %.4f" % (tn, tw / float(tn)))
    print("定理 6(5) 的泄漏在这里是实测的，不是上界。")
    return 0


def selftest():
    n = 0

    def ck(cond, what):
        nonlocal n
        assert cond, what
        n += 1

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

    # the decomposition is an identity, so it has to close to machine precision
    for eb, ef, db, da in ((100, 102, 101, 103), (5000, 5010, 4990, 5030),
                           (7, 9, 8, 30), (1, 3, 2, 4)):
        mid_part, spr_part, _ = parts(eb, ef, db, da)
        direct = 2.0 * math.log(math.sqrt(float(db) * da)
                                / math.sqrt(float(eb) * ef))
        ck(abs(mid_part + spr_part - direct) < 1e-12,
           "6(5) split does not close on %s: %g vs %g"
           % ((eb, ef, db, da), mid_part + spr_part, direct))

    # equal RELATIVE spreads kill the spread part, which is the theorem's iff
    _, spr, _ = parts(100, 110, 200, 220)          # s/M = 10/105 both sides
    ck(abs(spr) < 1e-12, "equal relative spread left a spread part: %g" % spr)
    _, spr, _ = parts(100, 110, 200, 210)          # unequal
    ck(abs(spr) > 1e-9, "unequal relative spread gave nothing: %g" % spr)

    # a non-positive bid has no logs and must return None rather than a number
    ck(parts(0, 5, 1, 2) is None, "zero bid produced a value")
    ck(parts(-3, 5, 1, 2) is None, "negative bid produced a value")

    # the arithmetic rho equals the log rho to first order when s << M, which is
    # the approximation the whole chain to date rests on
    eb, ef, db, da = 1000000, 1000100, 1000050, 1000170
    mid_part, spr_part, fric = parts(eb, ef, db, da)
    rho_thm = abs(mid_part + spr_part) / -fric
    rho_code = abs((db + da) - (eb + ef)) / float((ef - eb) + (da - db))
    ck(abs(rho_thm - rho_code) < 1e-3,
       "small s/M should make the two rhos agree: %g vs %g" % (rho_thm, rho_code))

    # and it fails when s/M is large, which is why branch C exists
    eb, ef, db, da = 10, 40, 12, 50
    mid_part, spr_part, fric = parts(eb, ef, db, da)
    rho_thm = abs(mid_part + spr_part) / -fric
    rho_code = abs((db + da) - (eb + ef)) / float((ef - eb) + (da - db))
    ck(abs(rho_thm - rho_code) > 1e-3,
       "large s/M should split them: %g vs %g" % (rho_thm, rho_code))

    # load8 drops a row whose stored index contradicts its four prices
    import tempfile
    fd, tp = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(tp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        fh.write(u"X\t1\t-6\t2\t5\t1\t10\t13\n")
        fh.write(u"X\t2\t-6\t9\t5\t1\t10\t13\n")
    ck(len(load8(tp).get("X", [])) == 1, "load8 kept a contradictory row")

    print("selftest ok: %d checks" % n)
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--defined" in argv:
        q = [a for a in argv if not a.startswith("-")]
        return defined(q or list(CACHES))
    paths = [a for a in argv if not a.startswith("-")]
    return run(paths or list(CACHES))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
