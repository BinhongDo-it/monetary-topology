# -*- coding: utf-8 -*-
"""Why B13-0 reads 0.92 and not 1.00. Two candidates, one run, opposite predictions.

The gate's misses are all exactly one tick and heavily one-directional, and
**138 of them are published implied bids that are worse than a derivation path
that appeared to be available**. An exchange publishing the best price across
all derivation paths cannot do that. So either

  C  the path was not actually available, because the leg's top of book could
     not support the quantity, or
  B  the book here was stale, so the path computed was not the one standing.

They predict opposite things about the same numbers:

  C  leg top-of-book size at a miss is small relative to a match
  B  the two size distributions look the same, and the staleness shows up as
     gaps in RptSeq

RptSeq is the per-instrument sequence the exchange stamps on every book entry.
**A contiguous RptSeq is a proof that no update was missed**, which kills the
missed-message half of B outright rather than arguing about it.

Nothing here changes the gate. It only measures why the gate reads what it reads.
"""
import argparse
import collections
import importlib.util
import os
import re
import struct
import sys

_spec = importlib.util.spec_from_file_location(
    "b13probe", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "b13_probe_pcap.py"))
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

END_OF_EVENT = 0x80
NEW, CHANGE, DELETE, DELETE_THRU, DELETE_FROM, OVERLAY = 0, 1, 2, 3, 4, 5


class Book:
    """Levels 1..n holding (price, size). Same level algebra as the gate."""

    __slots__ = ("levels",)

    def __init__(self):
        self.levels = {}

    def apply(self, action, level, price, size):
        if action in (CHANGE, OVERLAY):
            self.levels[level] = (price, size)
        elif action == NEW:
            for lv in sorted([k for k in self.levels if k >= level], reverse=True):
                self.levels[lv + 1] = self.levels.pop(lv)
            self.levels[level] = (price, size)
        elif action == DELETE:
            self.levels.pop(level, None)
            for lv in sorted([k for k in self.levels if k > level]):
                self.levels[lv - 1] = self.levels.pop(lv)
        elif action == DELETE_THRU:
            for lv in [k for k in self.levels if k <= level]:
                self.levels.pop(lv, None)
        elif action == DELETE_FROM:
            for lv in [k for k in self.levels if k >= level]:
                self.levels.pop(lv, None)

    def top(self):
        return self.levels.get(1)


def quantiles(xs):
    if not xs:
        return "no observations"
    s = sorted(xs)
    q = lambda f: s[min(len(s) - 1, int(f * len(s)))]
    return ("n=%d  min=%d  p10=%d  p25=%d  median=%d  p75=%d  p90=%d  max=%d  mean=%.1f"
            % (len(s), s[0], q(.10), q(.25), q(.50), q(.75), q(.90), s[-1],
               sum(s) / len(s)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--spread", required=True)
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--out")
    args = ap.parse_args()

    stream, proc, _ = probe.open_stream(args.defs)
    syms = {}
    for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
        if key != args.group:
            continue
        for tid, raw in probe.sbe_messages(data):
            if tid in (54, 55, 56) and len(raw) >= 69:
                syms[raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()] = \
                    struct.unpack("<i", raw[65:69])[0]
    if proc is not None:
        proc.kill()

    m = re.match(r"^([A-Z0-9]+)([FGHJKMNQUVXZ]\d)-\1([FGHJKMNQUVXZ]\d)$", args.spread)
    near, far = m.group(1) + m.group(2), m.group(1) + m.group(3)
    sid_s, sid_n, sid_f = syms[args.spread], syms[near], syms[far]

    books = collections.defaultdict(Book)
    watched = {sid_s, sid_n, sid_f}
    seq = {}
    gaps = collections.Counter()
    entries = collections.Counter()
    # size at the leg level touched by each identity, split by whether the
    # identity held
    sizes = collections.defaultdict(list)
    verdict = collections.Counter()
    touched = False
    dirty = False

    stream, proc, _ = probe.open_stream(args.data)
    try:
        for key, data in probe.packets(stream, args.limit, 1e18, 5_000_000, None):
            if key != args.group:
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
                    if sid in watched:
                        rpt = struct.unpack("<I", raw[o + 16:o + 20])[0]
                        entries[sid] += 1
                        prev = seq.get(sid)
                        if prev is not None and rpt != prev + 1:
                            gaps[sid] += 1
                        seq[sid] = rpt
                        kind = chr(raw[o + 26])
                        books[(sid, kind)].apply(
                            raw[o + 25], raw[o + 24],
                            struct.unpack("<q", raw[o:o + 8])[0],
                            struct.unpack("<i", raw[o + 8:o + 12])[0])
                        dirty = True
                        if sid == sid_s and kind in "EF":
                            touched = True
                    o += ent
                if not (mei & END_OF_EVENT) or not dirty:
                    continue
                dirty = False
                if not touched:
                    continue
                touched = False
                nb = books[(sid_n, "0")].top()
                na = books[(sid_n, "1")].top()
                fb = books[(sid_f, "0")].top()
                fa = books[(sid_f, "1")].top()
                eb = books[(sid_s, "E")].top()
                ef = books[(sid_s, "F")].top()
                if None in (nb, na, fb, fa):
                    continue
                # implied bid uses bid(near) and ask(far)
                if eb is not None:
                    hit = eb[0] == nb[0] - fa[0]
                    worse = eb[0] < nb[0] - fa[0]
                    tag = "bid hit" if hit else ("bid WORSE" if worse else "bid better")
                    verdict[tag] += 1
                    sizes[(tag, "near bid")].append(nb[1])
                    sizes[(tag, "far ask")].append(fa[1])
                    sizes[(tag, "min of the two")].append(min(nb[1], fa[1]))
                # implied offer uses ask(near) and bid(far)
                if ef is not None:
                    hit = ef[0] == na[0] - fb[0]
                    better = ef[0] < na[0] - fb[0]
                    tag = "offer hit" if hit else ("offer better" if better else "offer WORSE")
                    verdict[tag] += 1
                    sizes[(tag, "near ask")].append(na[1])
                    sizes[(tag, "far bid")].append(fb[1])
                    sizes[(tag, "min of the two")].append(min(na[1], fb[1]))
    finally:
        if proc is not None:
            proc.kill()

    out = ["%s=%d  %s=%d  %s=%d" % (args.spread, sid_s, near, sid_n, far, sid_f), ""]
    out.append("RptSeq continuity, the test that kills the missed-message story:")
    for sid in (sid_s, sid_n, sid_f):
        out.append("  id %-8d entries %10d   RptSeq discontinuities %d"
                   % (sid, entries[sid], gaps[sid]))
    out.append("")
    out.append("outcomes:")
    for tag, num in sorted(verdict.items()):
        out.append("  %-14s %8d" % (tag, num))
    out.append("")
    out.append("leg size at the moment of each outcome:")
    for keyt in sorted(sizes):
        out.append("  %-14s %-16s %s" % (keyt[0], keyt[1], quantiles(sizes[keyt])))
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
