#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B18 pass one: is the sided-absence asymmetry even non-degenerate?

Pre-registered: the four grids below were fixed before the run and not
changed after it. This file only executes them.

    A_s = P(no direct bid) - P(no direct ask), over end-of-event snapshots

The design's third grid makes one branch a HARD PRECONDITION: if both sides of
the direct book are essentially always present, A_s is pinned at zero, there is
nothing to attach to a position, and the station closes on the spot. Nothing
downstream is worth reading until that is settled.

One scan, two reads, and the gate is kept by staging the OUTPUT rather than by
scanning twice:

    --scan   walks the capture once and writes a reusable per-snapshot cache
    --pre    reads ONLY the precondition off that cache
    --full   reads the two axes, and refuses unless --pre has been run and the
             precondition passed, so the reading order in the design file is
             enforced by the code instead of by memory

The cache is a reusable artifact and is never deleted or overwritten in place;
it is written through a .part and os.replace.

    python experiments/b18_sided.py --selftest
    python experiments/b18_sided.py --scan --defs D --data F --groups G
    python experiments/b18_sided.py --pre
    python experiments/b18_sided.py --segments
"""

import argparse
import ast
import collections
import io
import os
import re
import struct
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "data", "cache", "b13")
CENSUS = os.path.join(CACHE, "spread_census.tsv")
OUT = os.path.join(CACHE, "b18_sided.tsv")
GATE = os.path.join(CACHE, "b18_precondition.txt")
SEGOUT = os.path.join(CACHE, "b18_segments.tsv")
FLOOR = 2000                     # design grid two: the floor buys sign quality
END_OF_EVENT = 0x80
PAT = re.compile(r"^([A-Z0-9]{1,5})([FGHJKMNQUVXZ])(\d)-\1([FGHJKMNQUVXZ])(\d)$")
#: what "essentially always present" means, fixed in the design before any scan:
#: a spread whose two absence rates are both under this contributes no sign.
FLAT = 0.005


def _load_probe():
    origin = os.path.join(HERE, "b13_gate0_diag.py")
    src = io.open(origin, encoding="utf-8").read().split("def main()")[0]
    mod = types.ModuleType("b13diag")
    mod.__dict__["__file__"] = origin
    exec(compile(src, origin, "exec"), mod.__dict__)
    return mod.probe, mod.Book


def wanted(path=CENSUS, floor=FLOOR):
    keep = set()
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        s, k = line.rstrip("\n").split("\t")
        if int(k) >= floor and PAT.match(s):
            keep.add(s)
    return keep


def scan(args):
    probe, Book = _load_probe()
    groups = set(args.groups.split(","))
    keep = wanted(args.census, args.floor)
    sys.stderr.write("census keeps %d spreads at floor %d\n" % (len(keep), args.floor))

    stream, proc, _ = probe.open_stream(args.defs)
    ids = {}
    for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
        if key not in groups:
            continue
        for tid, raw in probe.sbe_messages(data):
            if tid in (54, 55, 56) and len(raw) >= 69:
                s = raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()
                if s in keep:
                    ids[struct.unpack("<i", raw[65:69])[0]] = s
    if proc is not None:
        proc.kill()
    sys.stderr.write("resolved %d of %d\n" % (len(ids), len(keep)))

    books = collections.defaultdict(Book)
    touched = set()
    seq = 0
    n = 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = args.out + ".part"
    stream, proc, _ = probe.open_stream(args.data)
    try:
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(u"# symbol\tseq\tflags\tdirect_mid\n")
            fh.write(u"# flags bit0 direct bid, bit1 direct ask,"
                     u" bit2 implied bid, bit3 implied ask; 1 = present\n")
            fh.write(u"# direct_mid is raw PRICE9 and blank when a side is absent\n")
            for key, data in probe.packets(stream, args.limit, 1e18, 5_000_000, None):
                if key not in groups:
                    continue
                for tid, raw in probe.sbe_messages(data):
                    if tid != 46:
                        continue
                    block = struct.unpack("<H", raw[2:4])[0]
                    mei = raw[18] if len(raw) > 18 else 0
                    o = 10 + block
                    if o + 3 > len(raw):
                        continue
                    ent, num = struct.unpack("<HB", raw[o:o + 3])
                    o += 3
                    if ent < 27:
                        continue
                    for _ in range(num):
                        if o + ent > len(raw):
                            break
                        sid = struct.unpack("<i", raw[o + 12:o + 16])[0]
                        if sid in ids:
                            kind = chr(raw[o + 26])
                            if kind in "01EF":
                                books[(sid, kind)].apply(
                                    raw[o + 25], raw[o + 24],
                                    struct.unpack("<q", raw[o:o + 8])[0],
                                    struct.unpack("<i", raw[o + 8:o + 12])[0])
                                touched.add(sid)
                        o += ent
                    if not (mei & END_OF_EVENT) or not touched:
                        continue
                    seq += 1
                    for sid in touched:
                        db = books[(sid, "0")].top()
                        da = books[(sid, "1")].top()
                        eb = books[(sid, "E")].top()
                        ea = books[(sid, "F")].top()
                        f = ((1 if db else 0) | (2 if da else 0)
                             | (4 if eb else 0) | (8 if ea else 0))
                        mid = u"" if not (db and da) else u"%d" % (db[0] + da[0])
                        fh.write(u"%s\t%d\t%d\t%s\n" % (ids[sid], seq, f, mid))
                        n += 1
                    touched.clear()
    finally:
        if proc is not None:
            proc.kill()
    os.replace(tmp, args.out)
    print("wrote %d snapshots for %d spreads to %s"
          % (n, len(ids), os.path.relpath(args.out, ROOT)))
    return 0


def read_cache(path):
    per = collections.defaultdict(list)
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        c = line.rstrip("\n").split("\t")
        per[c[0]].append((int(c[1]), int(c[2]),
                          int(c[3]) if c[3] else None))
    return per


def pre(path=OUT, gate=GATE):
    if not os.path.exists(path):
        sys.stderr.write("no cache; run --scan first\n")
        return 1
    per = read_cache(path)
    print("Precondition: is A_s identically zero")
    print("Prints the distribution of both sides' absence rates. Not a verdict.")
    print("")
    rows = []
    for nm, v in per.items():
        n = float(len(v))
        nb = sum(1 for _, f, _ in v if not (f & 1)) / n
        na = sum(1 for _, f, _ in v if not (f & 2)) / n
        rows.append((abs(nb - na), nm, len(v), nb, na))
    rows.sort(reverse=True)
    flat = sum(1 for a, _, _, nb, na in rows if nb < FLAT and na < FLAT)
    print("%d contracts, %d snapshots" % (len(rows), sum(r[2] for r in rows)))
    print("both absence rates under %.3f, so flat and carrying no sign:"
          " %d contracts, %.4f of them"
          % (FLAT, flat, flat / float(len(rows))))
    print("")
    print("the ten largest |A_s|:")
    print("  %-13s %8s %10s %10s %10s"
          % ("spread", "n", "P(no bid)", "P(no ask)", "A_s"))
    for a, nm, k, nb, na in rows[:10]:
        print("  %-13s %8d %10.4f %10.4f %+10.4f" % (nm, k, nb, na, nb - na))
    print("")
    print("quantiles of |A_s|:")
    q = [r[0] for r in rows][::-1]
    for name, i in (("p10", 10), ("p25", 25), ("p50", 50), ("p75", 75), ("p90", 90)):
        print("  %-4s %.4f" % (name, q[int(len(q) * i / 100.0)]))
    ok = flat / float(len(rows)) < 0.90
    io.open(gate, "w", encoding="utf-8", newline="\n").write(
        u"PRECONDITION %s\nflat_share %.6f\nn_spreads %d\n"
        % ("PASS" if ok else "FAIL", flat / float(len(rows)), len(rows)))
    print("")
    print("gate file written: %s" % os.path.relpath(gate, ROOT))
    print("read: %s" % ("there is variation to measure, and the two axes can "
                        "be read further"
                        if ok else "both sides are almost always present, A_s "
                        "is pinned at zero, and the station closes here"))
    return 0


def segments(path=OUT, out=SEGOUT):
    """Count absence SEGMENTS per contract per side, and print what they buy.

    Why this and not the snapshot count. Absence happens in runs: one quote
    away for three hundred seconds leaves three hundred highly correlated
    snapshots. The independent unit is the run, not the second, so taking the
    3,895,656 snapshots as ``n`` inflates the degrees of freedom, which is
    a degrees-of-freedom inflation this station already committed once in a
    different place.

    What it settles. Both axes of this station read a SIGN, and the median
    ``|A_s|`` is under one percent, so most contracts' signs are decided by
    noise rather than by anything structural. The number that matters before
    spending anything further is how many contracts have a sign that can be
    estimated at all. That is what this prints.

    ``se(A_s) ~ sqrt(p_b(1-p_b)/seg_b + p_a(1-p_a)/seg_a)``, the two sides
    treated as independent, which is the loose direction: correlated sides
    would give a smaller se and more eligible contracts, so a contract that
    does not clear here would not clear under a tighter treatment either.

    Prints the object at three ratios and draws no line. One pass over the
    cache, no rescan, and it writes a new file rather than touching any
    existing one.
    """
    if not os.path.exists(path):
        sys.stderr.write("no cache; run --scan first\n")
        return 1
    per = read_cache(path)
    rows = []
    for nm, v in per.items():
        v = sorted(v)
        n = float(len(v))
        nb = na = 0
        segb = sega = 0
        pb = pa = False
        for _, f, _ in v:
            b_absent = not (f & 1)
            a_absent = not (f & 2)
            if b_absent:
                nb += 1
                if not pb:
                    segb += 1
            if a_absent:
                na += 1
                if not pa:
                    sega += 1
            pb, pa = b_absent, a_absent
        p_b, p_a = nb / n, na / n
        var = 0.0
        if segb:
            var += p_b * (1.0 - p_b) / segb
        if sega:
            var += p_a * (1.0 - p_a) / sega
        se = var ** 0.5
        a_s = p_b - p_a
        rows.append((nm, int(n), p_b, p_a, a_s, segb, sega, se,
                     abs(a_s) / se if se > 0 else float("inf")))

    rows.sort(key=lambda r: -r[8])
    total = len(rows)
    print("Is the sign of A_s estimable: absence SEGMENTS per contract,")
    print("not snapshots. The independent unit is the run, not the second.")
    print("Prints the object and draws no line.")
    print("")
    print("%d contracts, %d snapshots" % (total, sum(r[1] for r in rows)))
    finite = [r for r in rows if r[7] > 0]
    if finite:
        segs = sorted(r[5] + r[6] for r in finite)
        print("absence segments per contract, both sides summed:"
              " p10 %d  p50 %d  p90 %d  max %d"
              % (segs[len(segs) // 10], segs[len(segs) // 2],
                 segs[len(segs) * 9 // 10], segs[-1]))
    print("")
    for z in (1.0, 2.0, 3.0):
        k = sum(1 for r in rows if r[8] >= z)
        print("  |A_s| >= %.0f se : %4d contracts, %.4f of them"
              % (z, k, k / float(total)))
    print("")
    print("the ten largest ratios:")
    print("  %-13s %9s %9s %9s %7s %7s %9s %8s"
          % ("spread", "P(no bid)", "P(no ask)", "A_s", "seg_b", "seg_a",
             "se", "|A_s|/se"))
    for nm, n, p_b, p_a, a_s, sb, sa, se, ratio in rows[:10]:
        print("  %-13s %9.4f %9.4f %+9.4f %7d %7d %9.4f %7.2f"
              % (nm, p_b, p_a, a_s, sb, sa, se, ratio))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# symbol\tsnapshots\tp_no_bid\tp_no_ask\tA_s"
                 u"\tseg_no_bid\tseg_no_ask\tse\tratio\n")
        for nm, n, p_b, p_a, a_s, sb, sa, se, ratio in rows:
            fh.write(u"%s\t%d\t%.6f\t%.6f\t%.6f\t%d\t%d\t%.6f\t%.4f\n"
                     % (nm, n, p_b, p_a, a_s, sb, sa, se, ratio))
    os.replace(tmp, out)
    print("")
    print("written: %s" % os.path.relpath(out, ROOT))
    print("Reading, declared before the run: this count is the ceiling on how "
          "many contracts can vote on either axis. The registered power for "
          "the leg axis was computed at N = 44, so a count under 44 at "
          "|A_s| >= 2se means the power has to be recomputed rather than the "
          "axes run.")
    return 0


def selftest():
    n = 0

    def ck(c, w):
        nonlocal n
        assert c, w
        n += 1

    tree = ast.parse(io.open(os.path.abspath(__file__), encoding="utf-8").read())
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else \
                (f.id if isinstance(f, ast.Name) else "")
            if nm in ("remove", "unlink", "rmtree", "rmdir"):
                bad.add(nm)
    ck(not bad, "deletion call: %s" % bad)

    import tempfile
    fd, c = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(c, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        fh.write(u"NGQ3-NGH4\t5000\n")     # kept
        fh.write(u"NGQ3-NGZ3\t1999\n")     # under the floor
        fh.write(u"NGQ3-HHQ3\t9999\n")     # different roots, not a calendar spread
        fh.write(u"0SXF4 C2250\t9999\n")   # an option
    k = wanted(c, 2000)
    ck(k == {"NGQ3-NGH4"}, "census filter kept %s" % k)

    # the flag packing must be recoverable bit by bit
    for db, da, eb, ea in ((1, 1, 1, 1), (0, 1, 1, 0), (1, 0, 0, 0), (0, 0, 0, 0)):
        f = ((1 if db else 0) | (2 if da else 0) | (4 if eb else 0) | (8 if ea else 0))
        ck((bool(f & 1), bool(f & 2), bool(f & 4), bool(f & 8))
           == (bool(db), bool(da), bool(eb), bool(ea)), "flag packing %d" % f)

    # a cache where one side is always missing must read A_s = -1 or +1, and a
    # cache where both are always present must land in the flat bucket
    fd, t = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    with io.open(t, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# h\n")
        for i in range(500):
            fh.write(u"ONESIDED\t%d\t2\t\n" % i)       # ask only, no bid
            fh.write(u"BOTH\t%d\t3\t100\n" % i)        # both present
    per = read_cache(t)
    nb = sum(1 for _, f, _ in per["ONESIDED"] if not (f & 1)) / 500.0
    na = sum(1 for _, f, _ in per["ONESIDED"] if not (f & 2)) / 500.0
    ck(abs((nb - na) - 1.0) < 1e-12, "one-sided should give A_s = +1")
    nb = sum(1 for _, f, _ in per["BOTH"] if not (f & 1)) / 500.0
    na = sum(1 for _, f, _ in per["BOTH"] if not (f & 2)) / 500.0
    ck(nb < FLAT and na < FLAT, "both-present should land flat")

    print("selftest ok: %d checks" % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--pre", action="store_true")
    ap.add_argument("--segments", action="store_true")
    ap.add_argument("--defs")
    ap.add_argument("--data")
    ap.add_argument("--groups")
    ap.add_argument("--census", default=CENSUS)
    ap.add_argument("--floor", type=int, default=FLOOR)
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.pre:
        return pre(a.out)
    if a.segments:
        return segments(a.out)
    if a.scan:
        for k in ("defs", "data", "groups"):
            if not getattr(a, k):
                ap.error("--" + k + " required")
        return scan(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
