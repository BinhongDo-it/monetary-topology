#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gate five for route three: count the qualifying cells on the capture already
on disk, before pricing anything.

WHY
===
Route three needs legs that appear as the NEAR leg of one calendar spread and
the FAR leg of another, because only those make the framework and the rival
predict opposite signs. Two contracts sharing a near leg move together when that
leg moves, so both accounts predict the same sign there and the comparison reads
nothing.

The listed count is not the constraint. Harvesting every instrument definition
off channels 382 and 386 gives 49,236 two-leg same-root calendar spreads across
170 roots and 23,788 discriminating comparisons; NG alone lists 1,127 spreads
and 551 comparisons.

The 23 instruments the b13 caches contain came from a --spreads list somebody
typed. **That list, not the market, is where "5 discriminating comparisons"
came from.** So the number that decides whether route three opens is how many
listed spreads are actually quoted two-sided on both books during the capture,
and that is measurable on the file already on disk. Discipline 21, gate five:
count qualifying cells before buying, and count qualifying cells rather than an
average.

REGISTERED BEFORE THIS RAN
==========================
Report the count at several state floors rather than picking one, then:

    >= 13 qualifying legs              route three opens on this capture, zero
                                       purchase, sign test power 0.80 at p=0.85
    8 to 12                            opens at D17's 0.50 floor only; print the
                                       power and let that stand as the reading
    < 8                                this capture cannot carry it. Only then
                                       is a purchase worth pricing

A spread counts as quoted when a single end-of-event state has all four books
non-empty, which is the same condition b4_two_classes.py --dump uses. No new
definition is introduced here.

    python experiments/b13_census.py --selftest
    python experiments/b13_census.py --defs D --data F --groups G --out O
    python experiments/b13_census.py --read O
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
END_OF_EVENT = 0x80
FLOORS = (100, 200, 500, 1000, 2000)
PAT = re.compile(r"^([A-Z0-9]{1,5})([FGHJKMNQUVXZ])(\d)-\1([FGHJKMNQUVXZ])(\d)$")


def _load_probe():
    origin = os.path.join(HERE, "b13_gate0_diag.py")
    src = io.open(origin, encoding="utf-8").read().split("def main()")[0]
    mod = types.ModuleType("b13diag")
    mod.__dict__["__file__"] = origin
    exec(compile(src, origin, "exec"), mod.__dict__)
    return mod.probe, mod.Book


def census(args):
    probe, Book = _load_probe()
    groups = set(args.groups.split(","))

    stream, proc, _ = probe.open_stream(args.defs)
    ids = {}
    for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
        if key not in groups:
            continue
        for tid, raw in probe.sbe_messages(data):
            if tid in (54, 55, 56) and len(raw) >= 69:
                s = raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()
                if PAT.match(s):
                    ids[struct.unpack("<i", raw[65:69])[0]] = s
    if proc is not None:
        proc.kill()
    sys.stderr.write("two-leg same-root calendar spreads listed: %d\n" % len(ids))

    books = collections.defaultdict(Book)
    touched = set()
    n = collections.Counter()
    stream, proc, _ = probe.open_stream(args.data)
    try:
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
                for sid in touched:
                    if all(books[(sid, k)].top() is not None for k in "EF01"):
                        n[sid] += 1
                touched.clear()
    finally:
        if proc is not None:
            proc.kill()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = args.out + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(u"# symbol\tstates_with_all_four_books\n")
        for sid, k in sorted(n.items(), key=lambda t: (-t[1], ids[t[0]])):
            fh.write(u"%s\t%d\n" % (ids[sid], k))
    os.replace(tmp, args.out)
    print("wrote %d quoted spreads to %s"
          % (len(n), os.path.relpath(args.out, ROOT)))
    return read(args.out)


def legs(symbols):
    near, far = collections.defaultdict(list), collections.defaultdict(list)
    for s in symbols:
        m = PAT.match(s)
        if not m:
            continue
        r = m.group(1)
        near[r + m.group(2) + m.group(3)].append(s)
        far[r + m.group(4) + m.group(5)].append(s)
    both = set(near) & set(far)
    #: ONE independent discriminating comparison per qualifying leg, not
    #: min(near, far) and not near+far-1. Contracts sharing the leg on the SAME
    #: side are predicted to agree by BOTH accounts, so the whole near group
    #: carries one sign and the whole far group carries one sign, and the datum
    #: is whether those two signs match. Counting the pairs inside a group as
    #: separate comparisons is the inflated-degrees-of-freedom error, category
    #: error eleven, committed against this very design on 2026-08-23 when it
    #: was first counted by hand as 5.
    disc = len(both)
    same = sum(len(v) - 1 for v in near.values() if len(v) > 1) + \
        sum(len(v) - 1 for v in far.values() if len(v) > 1)
    return len(both), disc, same


def read(path):
    rows = []
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        s, k = line.rstrip("\n").split("\t")
        rows.append((s, int(k)))
    print("")
    print("报价过的两腿同根日历价差：%d 份" % len(rows))
    print("%8s %10s %12s %14s %14s"
          % ("状态下限", "达标价差", "既近既远的腿", "可区分比较", "同向比较"))
    for f in FLOORS:
        keep = [s for s, k in rows if k >= f]
        b, d, sm = legs(keep)
        print("%8d %10d %12d %14d %14d" % (f, len(keep), b, d, sm))
    print("")
    print("跑前登记的读法：>=13 开站且功效 0.80；8..12 只到 D17 的 0.50 地板；<8 本 capture 不够")
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

    ck(PAT.match("NGQ3-NGH4") and PAT.match("TTFQ3-TTFU3"), "should match")
    ck(not PAT.match("NGQ3-HHQ3"), "different roots must not match")
    ck(not PAT.match("0SXF4 C2250"), "an option must not match")

    # the 23 names actually in the b13 caches must reproduce the 5 that was
    # counted by hand, or this function disagrees with the pre-registration
    have = ["CLQ3-CLV3", "CLQ3-CLX3", "CLZ3-CLZ4", "CLU3-CLX3", "CLU3-CLV3",
            "CLV3-CLM4", "RBU3-RBX3", "RBU3-RBV3", "NGH4-NGQ4", "NGQ3-NGH4",
            "NGQ3-NGK4", "NGQ3-NGJ4", "NGQ3-NGF4", "NGV3-NGK4", "NGU3-NGK4",
            "NGQ3-NGZ3", "NGU3-NGJ4", "TTFQ3-TTFU3", "NGU3-NGF4", "NGV3-NGF4",
            "NGU3-NGZ3", "NGX3-NGF4", "NGZ3-NGK4"]
    b, d, sm = legs(have)
    ck(b == 3, "expected 3 legs both near and far, got %d" % b)
    ck(d == 3, "expected 3 discriminating comparisons, got %d" % d)

    # a hand construction where the answer is obvious
    ck(legs(["AZ3-AH4", "AH4-AQ4"])[1] == 1, "one crossing leg")
    ck(legs(["AZ3-AH4", "AZ3-AQ4"])[1] == 0, "shared near leg discriminates nothing")
    ck(legs(["AZ3-AH4", "AH4-AQ4", "AH4-AZ4"])[1] == 1,
       "one leg is one comparison however many contracts hang off it")

    print("selftest ok: %d checks" % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--read")
    ap.add_argument("--defs")
    ap.add_argument("--data")
    ap.add_argument("--groups")
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "data", "cache", "b13", "spread_census.tsv"))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.read:
        return read(a.read)
    for k in ("defs", "data", "groups"):
        if not getattr(a, k):
            ap.error("--" + k + " required")
    return census(a)


if __name__ == "__main__":
    sys.exit(main())
