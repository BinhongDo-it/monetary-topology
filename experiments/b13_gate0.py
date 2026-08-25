# -*- coding: utf-8 -*-
"""B13-0: is the exchange's implied price reproducible from the displayed
outright top of book, to the last digit.

Design file section 4. **This gate comes before everything else** because the
station's claim is that one member of the spread book is exactly zero by
construction, and a claim of exactness cannot be built on a price I cannot
reproduce. B9 spent nine sections learning that: its reconstruction reproduced
0.8975 of the closing NBBO, which reads as "close enough" and destroyed the
comparison the stage actually rested on.

What is measured, per design file section 3, is a **proportion of messages at
which an identity holds to the last integer**, not a distance under a tolerance.
Refusing a tolerance is registered: B9 section 31.6 set one below the quantity's
own sampling spread, guaranteed a break, and then two sections were spent
explaining the break away.

The two identities, from design file section 1, on a same-product 1:1 calendar
spread whose price is near month minus deferred:

    implied offer  ==  ask(near)  -  bid(deferred)
    implied bid    ==  bid(near)  -  ask(deferred)

**The legs' books are read direct-only.** Outrights carry implied entries of
their own (implied OUT), and deriving an implied IN from an implied OUT would be
circular. Which convention the exchange uses is not assumed here: both are
computed and both are reported, and the data says which one is exact.

State is taken at end of event, not per message, because CME sends the implied
update as the last message of the event and a mid-event read compares a spread
to legs that have not finished moving. MatchEventIndicator bit 0x80 is that
marker.

Usage:

  python experiments/b13_gate0.py \\
      --defs data/raw/b13/dc3-glbx-a-20230716T110000.pcap.zst \\
      --data data/raw/b13/dc3-glbx-ab-dedup-20230717T133000.pcap.zst \\
      --group 224.0.31.130:14382 --spread CLZ3-CLZ4 \\
      --out data/raw/b13/gate0_CLZ3-CLZ4.txt
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
    """One side of one instrument, as levels 1..n.

    MDP 3.0 sends level positions, not prices to match on, so New shifts the
    levels below it down and Delete shifts them up. Getting that wrong does not
    raise; it silently leaves a stale level 1, which is the only number this
    gate reads. Hence `unhandled`, which counts actions this class does not
    implement rather than ignoring them.
    """

    __slots__ = ("levels", "unhandled")

    def __init__(self):
        self.levels = {}
        self.unhandled = 0

    def apply(self, action, level, price):
        if action == CHANGE or action == OVERLAY:
            self.levels[level] = price
        elif action == NEW:
            for lv in sorted([k for k in self.levels if k >= level], reverse=True):
                self.levels[lv + 1] = self.levels.pop(lv)
            self.levels[level] = price
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
        else:
            self.unhandled += 1

    def top(self):
        return self.levels.get(1)


def symbol_map(path, group):
    """SecurityID to Symbol, from the definition broadcast.

    Templates 54 and 56 both carry definitions on this channel and 55 is never
    sent; 54 is outrights and 56 is spreads. That is measured, not read off a
    schema, and the probe module's docstring records how.
    """
    stream, proc, _ = probe.open_stream(path)
    ids, syms = {}, {}
    wanted = set(group.split(","))
    for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
        if key not in wanted:
            continue
        for tid, raw in probe.sbe_messages(data):
            if tid in (54, 55, 56) and len(raw) >= 69:
                sym = raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()
                sid = struct.unpack("<i", raw[65:69])[0]
                ids[sid] = sym
                syms[sym] = sid
    if proc is not None:
        proc.kill()
    return ids, syms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs", required=True, help="capture carrying the definitions")
    ap.add_argument("--data", required=True, help="capture carrying the trading window")
    ap.add_argument("--group", required=True,
                    help="multicast ip:port, comma separated. **On an A+B "
                         "deduplicated capture pass both sides.** Deduplication "
                         "removes duplicate packets, not the second address: the "
                         "packets that survive from the B feed are exactly the "
                         "ones the A feed dropped, and reading only A silently "
                         "loses them.")
    ap.add_argument("--spread", required=True, help="e.g. CLZ3-CLZ4")
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--every", type=int, default=5_000_000)
    args = ap.parse_args()

    ids, syms = symbol_map(args.defs, args.group)
    spread = args.spread
    m = re.match(r"^([A-Z0-9]+)([FGHJKMNQUVXZ]\d)-\1([FGHJKMNQUVXZ]\d)$", spread)
    if not m:
        return ap.error("%s is not a 1:1 same-product calendar spread symbol" % spread)
    near, far = m.group(1) + m.group(2), m.group(1) + m.group(3)
    for name in (spread, near, far):
        if name not in syms:
            return ap.error("%s has no definition in %s" % (name, args.defs))
    sid_s, sid_n, sid_f = syms[spread], syms[near], syms[far]
    print("%s=%d  %s=%d  %s=%d" % (spread, sid_s, near, sid_n, far, sid_f),
          file=sys.stderr, flush=True)

    books = collections.defaultdict(Book)
    watched = {sid_s, sid_n, sid_f}
    # (identity, book used for the legs) -> counts. **Both leg conventions are
    # carried to the end.** Deciding up front that the exchange derives implied
    # IN from the direct book only would be an assumption doing the work the
    # measurement is supposed to do.
    checked = collections.Counter()
    exact = collections.Counter()
    gaps = collections.defaultdict(collections.Counter)
    lam = collections.Counter()
    lam_n = 0
    events = 0
    paired = 0
    dirty = False
    touched_implied = False
    touched_direct = False

    groups = set(args.group.split(","))
    stream, proc, _ = probe.open_stream(args.data)
    try:
        for key, data in probe.packets(stream, args.limit, 1e18, args.every, None):
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
                    if sid in watched:
                        kind = chr(raw[o + 26])
                        books[(sid, kind)].apply(
                            raw[o + 25], raw[o + 24],
                            struct.unpack("<q", raw[o:o + 8])[0])
                        dirty = True
                        if sid == sid_s and kind in "EF":
                            touched_implied = True
                        if sid == sid_s and kind in "01":
                            touched_direct = True
                    o += ent
                if not (mei & END_OF_EVENT) or not dirty:
                    continue
                dirty = False
                events += 1
                # **Only events that republished the implied book are paired.**
                # Design file section 6: the two sides are read at the same
                # instant on the same contract and never paired across events. An
                # event that moved only a leg leaves last event's implied top
                # standing, and comparing that to the new legs measures the gap
                # between two events rather than the identity.
                if not touched_implied:
                    touched_direct = False
                    continue
                paired += 1
                imp_bid = books[(sid_s, "E")].top()
                imp_ask = books[(sid_s, "F")].top()
                for tag, bid_t, ask_t in (("direct legs", "0", "1"),
                                          ("implied legs", "E", "F")):
                    nb = books[(sid_n, bid_t)].top()
                    na = books[(sid_n, ask_t)].top()
                    fb = books[(sid_f, bid_t)].top()
                    fa = books[(sid_f, ask_t)].top()
                    if None in (nb, na, fb, fa):
                        continue
                    for side, got, want in (("implied offer", imp_ask, na - fb),
                                            ("implied bid", imp_bid, nb - fa)):
                        if got is None:
                            continue
                        checked[(side, tag)] += 1
                        if got == want:
                            exact[(side, tag)] += 1
                        else:
                            gaps[(side, tag)][got - want] += 1
                # The independent side: the same identity, on the spread's own
                # directly quoted book. Section 7's first outcome needs this to
                # be non-zero on the same machine that reads the exact zero.
                nb = books[(sid_n, "0")].top()
                na = books[(sid_n, "1")].top()
                fb = books[(sid_f, "0")].top()
                fa = books[(sid_f, "1")].top()
                d_bid = books[(sid_s, "0")].top()
                d_ask = books[(sid_s, "1")].top()
                if None not in (nb, na, fb, fa, d_ask):
                    lam[d_ask - (na - fb)] += 1
                    lam_n += 1
                touched_implied = False
                touched_direct = False
    finally:
        if proc is not None:
            proc.kill()

    out = []
    out.append("B13-0 on %s (id %d), legs %s (%d) and %s (%d)"
               % (spread, sid_s, near, sid_n, far, sid_f))
    out.append("%d end-of-event states with a book change on one of the three"
               % events)
    out.append("%d of those republished the spread's implied book and are paired"
               % paired)
    out.append("prices are raw PRICE9; 1e9 is one tick, so the tables below are ticks")
    unh = sum(b.unhandled for b in books.values())
    out.append("update actions this book class does not implement: %d" % unh)
    out.append("")
    out.append("%-16s %-14s %10s %10s %9s" % ("identity", "legs read as",
                                              "checked", "exact", "share"))
    for keyt in sorted(checked):
        c, e = checked[keyt], exact[keyt]
        out.append("%-16s %-14s %10d %10d %8.4f"
                   % (keyt[0], keyt[1], c, e, (e / c) if c else 0.0))
    out.append("")
    for keyt in sorted(gaps):
        if not gaps[keyt]:
            continue
        out.append("misses on %s / %s, by size in ticks:" % keyt)
        for diff, num in sorted(gaps[keyt].items(), key=lambda kv: -kv[1])[:12]:
            out.append("  %+8d  %10d" % (diff // 1000000000, num))
        out.append("")
    out.append("independent side: ask(spread, directly quoted) - [ask(%s) - bid(%s)]"
               % (near, far))
    out.append("%d states, %d distinct values" % (lam_n, len(lam)))
    out.append("  %10s %12s %9s" % ("lambda", "states", "share"))
    for val, num in sorted(lam.items()):
        out.append("  %10d %12d %8.4f"
                   % (val // 1000000000, num, num / lam_n if lam_n else 0))
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
