# -*- coding: utf-8 -*-
"""B13-0 out of sample, design file section 4.A.

The criterion under test was frozen before this ran, in section 4.A.2:

  load bearing   implied offer <= ask(near) - bid(far)
                 implied bid   >= bid(near) - ask(far)
                 **zero violations**, because publishing a price worse than a
                 path that was available cannot happen once under a
                 best-over-all-paths rule. One violation kills the premise.

  reported       the equality rate, i.e. how often the two-leg path *is* the
                 best path. **Not a criterion**: it moves with how complete our
                 enumeration is, and a threshold on it would be a threshold on
                 our own engineering.

Instruments come from section 4.A.4's rule, not from a pick: no leg shared with
the in-sample CLZ3-CLZ4, min(implied, direct) at least 1000, and **every
qualifying candidate is run and reported**. A prediction of zero violations gets
harder to survive with each instrument added, so widening the set strengthens
the test instead of diluting it.

Both multicast groups are read. On an A+B deduplicated capture the packets
surviving from the B feed are exactly the ones the A feed dropped; reading only
A cost 2% of the updates and produced a 0.92 that looked like a finding about
the exchange (results file section 4.3).
"""
import argparse
import collections
import importlib.util
import os
import re
import struct
import sys

_spec = importlib.util.spec_from_file_location(
    "b13diag", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "b13_gate0_diag.py"))
_src = open(_spec.origin, encoding="utf-8").read().split("def main()")[0]
import types
_mod = types.ModuleType("b13diag")
_mod.__dict__["__file__"] = _spec.origin
exec(compile(_src, _spec.origin, "exec"), _mod.__dict__)
probe, Book = _mod.probe, _mod.Book

END_OF_EVENT = 0x80
CAL = re.compile(r"^([A-Z0-9]+)([FGHJKMNQUVXZ]\d)-\1([FGHJKMNQUVXZ]\d)$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--groups", required=True, help="comma separated ip:port")
    ap.add_argument("--spreads", required=True, help="comma separated symbols")
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--out")
    args = ap.parse_args()
    groups = set(args.groups.split(","))

    stream, proc, _ = probe.open_stream(args.defs)
    ids = {}
    for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
        if key not in groups:
            continue
        for tid, raw in probe.sbe_messages(data):
            if tid in (54, 55, 56) and len(raw) >= 69:
                ids[raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()] = \
                    struct.unpack("<i", raw[65:69])[0]
    if proc is not None:
        proc.kill()

    tri = {}
    for name in args.spreads.split(","):
        m = CAL.match(name)
        if not m:
            return ap.error("%s is not a 1:1 same-product calendar spread" % name)
        near, far = m.group(1) + m.group(2), m.group(1) + m.group(3)
        for w in (name, near, far):
            if w not in ids:
                return ap.error("%s has no definition" % w)
        tri[name] = (ids[name], ids[near], ids[far], near, far)
    watched = set()
    for sid_s, sid_n, sid_f, _n, _f in tri.values():
        watched |= {sid_s, sid_n, sid_f}
    by_spread = collections.defaultdict(list)
    for name, (sid_s, _n, _f, _a, _b) in tri.items():
        by_spread[sid_s].append(name)

    books = collections.defaultdict(Book)
    stat = collections.defaultdict(collections.Counter)
    lam = collections.defaultdict(collections.Counter)
    lam_bid = collections.defaultdict(collections.Counter)
    touched = set()

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
                    if sid in watched:
                        kind = chr(raw[o + 26])
                        books[(sid, kind)].apply(
                            raw[o + 25], raw[o + 24],
                            struct.unpack("<q", raw[o:o + 8])[0],
                            struct.unpack("<i", raw[o + 8:o + 12])[0])
                        if kind in "EF" and sid in by_spread:
                            touched.update(by_spread[sid])
                    o += ent
                if not (mei & END_OF_EVENT) or not touched:
                    continue
                for name in touched:
                    sid_s, sid_n, sid_f, _a, _b = tri[name]
                    nb = books[(sid_n, "0")].top()
                    na = books[(sid_n, "1")].top()
                    fb = books[(sid_f, "0")].top()
                    fa = books[(sid_f, "1")].top()
                    if None in (nb, na, fb, fa):
                        continue
                    st = stat[name]
                    eb = books[(sid_s, "E")].top()
                    if eb is not None:
                        want = nb[0] - fa[0]
                        st["bid states"] += 1
                        st["bid equal"] += eb[0] == want
                        st["bid better"] += eb[0] > want
                        st["BID VIOLATION"] += eb[0] < want
                    ef = books[(sid_s, "F")].top()
                    if ef is not None:
                        want = na[0] - fb[0]
                        st["offer states"] += 1
                        st["offer equal"] += ef[0] == want
                        st["offer better"] += ef[0] < want
                        st["OFFER VIOLATION"] += ef[0] > want
                    # The independent side, design file section 7. Same event,
                    # same contract, same message stream: the spread's own
                    # directly quoted book against the same leg derivation the
                    # implied side was just held to. **No threshold is being
                    # applied here.** Section 7 asks only whether it is non-zero,
                    # so this reports a distribution and scores nothing.
                    da = books[(sid_s, "1")].top()
                    if da is not None:
                        lam[name][da[0] - (na[0] - fb[0])] += 1
                    db = books[(sid_s, "0")].top()
                    if db is not None:
                        lam_bid[name][db[0] - (nb[0] - fa[0])] += 1
                touched.clear()
    finally:
        if proc is not None:
            proc.kill()

    out = ["%-14s %8s %8s %8s %9s | %8s %8s %8s %9s"
           % ("spread", "bid n", "equal", "better", "VIOLATE",
              "off n", "equal", "better", "VIOLATE")]
    tot = collections.Counter()
    for name in sorted(stat, key=lambda k: -stat[k]["offer states"]):
        st = stat[name]
        for k, v in st.items():
            tot[k] += v
        out.append("%-14s %8d %8d %8d %9d | %8d %8d %8d %9d"
                   % (name, st["bid states"], st["bid equal"], st["bid better"],
                      st["BID VIOLATION"], st["offer states"], st["offer equal"],
                      st["offer better"], st["OFFER VIOLATION"]))
    out.append("%-14s %8d %8d %8d %9d | %8d %8d %8d %9d"
               % ("TOTAL", tot["bid states"], tot["bid equal"], tot["bid better"],
                  tot["BID VIOLATION"], tot["offer states"], tot["offer equal"],
                  tot["offer better"], tot["OFFER VIOLATION"]))
    out.append("")
    viol = tot["BID VIOLATION"] + tot["OFFER VIOLATION"]
    out.append("load-bearing criterion, section 4.A.2: %d violations in %d states"
               % (viol, tot["bid states"] + tot["offer states"]))
    out.append("verdict: %s" % ("PASS, zero violations" if viol == 0
                                else "FAIL, the premise that the exchange publishes "
                                     "the best available path is refuted"))
    out.append("reported only, not a criterion: equality rate bid %.4f, offer %.4f"
               % (tot["bid equal"] / tot["bid states"] if tot["bid states"] else 0,
                  tot["offer equal"] / tot["offer states"] if tot["offer states"] else 0))
    out.append("")
    out.append("independent side, design file section 7. lambda_offer = "
               "ask(spread, directly quoted) - [ask(near) - bid(far)], "
               "lambda_bid = bid(spread) - [bid(near) - ask(far)], in ticks")
    out.append("%-14s %9s %9s %9s   %s" % ("spread", "states", "non-zero",
                                           "share", "distribution"))
    for side, table in (("offer", lam), ("bid", lam_bid)):
        out.append("  -- %s side --" % side)
        grand = collections.Counter()
        for name in sorted(table, key=lambda k: -sum(table[k].values())):
            c = table[name]
            grand.update(c)
            n = sum(c.values())
            nz = n - c.get(0, 0)
            shown = " ".join("%+d:%d" % (v // 1000000000, k)
                             for v, k in sorted(c.items())[:9])
            out.append("  %-14s %9d %9d %8.4f   %s"
                       % (name, n, nz, nz / n if n else 0, shown))
        n = sum(grand.values())
        nz = n - grand.get(0, 0)
        out.append("  %-14s %9d %9d %8.4f   %s"
                   % ("TOTAL", n, nz, nz / n if n else 0,
                      " ".join("%+d:%d" % (v // 1000000000, k)
                               for v, k in sorted(grand.items()))))
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
