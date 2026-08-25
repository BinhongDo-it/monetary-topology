#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The chain re-read on the theorem's own quantity, on the nine instruments
where that quantity exists.

WHY
===
Every reading in this station so far used

    rho_code = |(db+da) - (eb+ef)| / ((ef-eb) + (da-db))

which is arithmetic mids over arithmetic spreads. Section 5.1 is written in logs
and Theorem 6(5) splits its numerator in two:

    S - S'  =  2 log(M_D/M_E)                                  midpoint part
             + log(1-(s_D/2M_D)^2) - log(1-(s_E/2M_E)^2)        spread part
    S + S'  =  log(bid_E/ask_E) + log(bid_D/ask_D)              friction
    rho_thm =  |midpoint + spread| / -(S+S')

b13_level.py established that 14 of 23 instruments have bid <= 0 in every state,
so log(mid) does not exist there, and that on the other nine the two rhos
correlate 0.9936 to 1.0000 while the SPREAD PART EXCEEDS THE MIDPOINT PART ON
31.10% OF STATES. Those two facts together are the reason for this file: the
ordering barely moves, and yet on a third of the states the numerator is mostly
spread asymmetry rather than the two classes disagreeing about the price.

REGISTERED BEFORE THIS RAN
==========================
R1 structural, voids the run on failure: rho_thm <= 1 on every state, which is
   Theorem 6(4) restated in the units the theorem actually uses. b4_two_classes
   checks it on the arithmetic version; nobody has checked it on this one.

R2 the tail of rho_thm at each cut, beside the tail of rho_code already on
   record. Same to within a state or two -> the chain's tail reading transfers.
   Materially different -> the tail reading was on the wrong quantity.

R3 THE ONE THIS FILE EXISTS FOR. Among states in the tail, what share has
   |spread part| > |midpoint part|?

     low, so the leak sits at low rho     the tail is class disagreement and
                                          section 5.1's reading of a high rho
                                          stands
     high, so the leak reaches the tail   a high rho does not mean the classes
                                          disagree about the price, it can mean
                                          they carry different relative spreads.
                                          B16's gate three is then load bearing
                                          rather than precautionary
     no tail states at all                reads nothing, and say so (D15)

   The object printed is the share per cut per instrument, no threshold on it.

    python experiments/b13_thm.py --selftest
    python experiments/b13_thm.py [tsv ...]
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
CUTS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


def load(path):
    """name -> [(seq, mid_part, spread_part, friction, rho_thm, rho_code)],
    only states where all four prices are positive."""
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
            if (db + da) - (eb + ef) != ix or min(eb, ef, db, da) <= 0:
                continue
            ME, MD = 0.5 * (eb + ef), 0.5 * (db + da)
            mid = 2.0 * math.log(MD / ME)
            spr = (math.log(1.0 - (sd / (2.0 * MD)) ** 2)
                   - math.log(1.0 - (se / (2.0 * ME)) ** 2))
            fric = math.log(float(eb) / ef) + math.log(float(db) / da)
            if fric >= 0:
                continue
            out[c[0]].append((int(c[1]), mid, spr, fric,
                              abs(mid + spr) / -fric,
                              abs(ix) / float(se + sd) if se + sd else 0.0))
    return dict(out)


def median(xs):
    s = sorted(xs)
    n = len(s)
    return float("nan") if not n else (
        float(s[n // 2]) if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2]))


def run(paths):
    data = {}
    for p in paths:
        if os.path.exists(p):
            for k, v in load(p).items():
                if v:
                    data[k] = v
        else:
            sys.stderr.write("missing %s\n" % p)
    if not data:
        sys.stderr.write("no v3 cache\n")
        return 1

    bad = sum(1 for v in data.values() for r in v if r[4] > 1.0)
    print("R1  rho_thm <= 1 违反 %d 例（定理 6(4)，本文件第一次在 log 单位上查）" % bad)
    if bad:
        print("    非零即代码错，本轮读数全部作废")
        return 1
    print("")

    print("R2  rho_thm 的上尾，与已在册的 rho_code 上尾并排")
    print("%-13s %8s %6s %s" % ("spread", "n", "量", "".join("%9.2f" % c for c in CUTS)))
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        n = float(len(v))
        for tag, idx in (("thm", 4), ("code", 5)):
            print("%-13s %8s %6s %s"
                  % (nm if tag == "thm" else "", len(v) if tag == "thm" else "", tag,
                     "".join("%8.4f%%" % (100.0 * sum(1 for r in v if r[idx] >= c) / n)
                             for c in CUTS)))
    print("")

    print("R3  尾部里 |价差部| > |中点部| 的占比。分母是该档的状态数，括号里是它。")
    print("%-13s %8s %s" % ("spread", "全样本", "".join("%15s" % ("rho>=%.2f" % c)
                                                    for c in CUTS[:4])))
    agg = defaultdict(lambda: [0, 0])
    for nm in sorted(data, key=lambda k: -len(data[k])):
        v = data[nm]
        base = sum(1 for r in v if abs(r[2]) > abs(r[1])) / float(len(v))
        cells = []
        for c in CUTS[:4]:
            sub = [r for r in v if r[4] >= c]
            agg[c][0] += sum(1 for r in sub if abs(r[2]) > abs(r[1]))
            agg[c][1] += len(sub)
            cells.append("-" if not sub else "%.4f (%d)"
                         % (sum(1 for r in sub if abs(r[2]) > abs(r[1]))
                            / float(len(sub)), len(sub)))
        print("%-13s %8.4f %s" % (nm, base, "".join("%15s" % x for x in cells)))
    print("")
    tot = sum(len(v) for v in data.values())
    lk = sum(1 for v in data.values() for r in v if abs(r[2]) > abs(r[1]))
    print("九条合计 %d 个状态，全样本泄漏占 %.4f" % (tot, lk / float(tot)))
    for c in CUTS[:4]:
        w, k = agg[c]
        print("  rho >= %.2f 的 %6d 个状态里，泄漏占 %s"
              % (c, k, "-" if not k else "%.4f" % (w / float(k))))
    return 0


def selftest():
    n = 0

    def ck(c, w):
        nonlocal n
        assert c, w
        n += 1

    tree = ast.parse(io.open(os.path.abspath(__file__), encoding="utf-8").read())
    b = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else \
                (f.id if isinstance(f, ast.Name) else "")
            if nm in ("remove", "unlink", "rmtree", "rmdir"):
                b.add(nm)
    ck(not b, "deletion call: %s" % b)

    import tempfile
    fd, tp = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    rows = [(1000, 1010, 1002, 1014), (5000, 5040, 5010, 5030),
            (200, 210, 201, 209), (100, 130, 105, 125)]
    with io.open(tp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        for i, (eb, ef, db, da) in enumerate(rows):
            se, sd = ef - eb, da - db
            fh.write(u"X\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n"
                     % (i, -(se + sd), (db + da) - (eb + ef), se, sd, eb, db))
    got = load(tp)["X"]
    ck(len(got) == len(rows), "load dropped a good row")

    # the split is an identity: midpoint + spread must equal the direct log
    for (eb, ef, db, da), r in zip(rows, got):
        direct = 2.0 * math.log(math.sqrt(float(db) * da)
                                / math.sqrt(float(eb) * ef))
        ck(abs(r[1] + r[2] - direct) < 1e-12, "split does not close")

    # equal relative spreads leave no spread part, unequal do
    fd, tp2 = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(tp2, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        for eb, ef, db, da in ((100, 110, 200, 220), (100, 110, 200, 210)):
            se, sd = ef - eb, da - db
            fh.write(u"Y\t0\t%d\t%d\t%d\t%d\t%d\t%d\n"
                     % (-(se + sd), (db + da) - (eb + ef), se, sd, eb, db))
    y = load(tp2)["Y"]
    ck(abs(y[0][2]) < 1e-12, "equal relative spread left a spread part")
    ck(abs(y[1][2]) > 1e-9, "unequal relative spread gave nothing")

    # a non-positive bid is dropped rather than turned into a complex number
    fd, tp3 = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(tp3, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        fh.write(u"Z\t0\t-4\t2\t2\t2\t-1\t0\n")
    ck("Z" not in load(tp3), "kept a state with a non-positive bid")

    print("selftest ok: %d checks" % n)
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    q = [a for a in argv if not a.startswith("-")]
    return run(q or list(CACHES))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
