# -*- coding: utf-8 -*-
"""Design file section 5.2: the spread's tick must equal its legs'.

**Measured, not read off a field.** The grid an instrument actually trades on is
the greatest common divisor of the prices it publishes, so this counts the
publications instead of trusting `MinPriceIncrement`. If the spread's grid is
finer than the legs', an exact-equality criterion between them is not even
defined, which is why section 5.2 makes this a pre-run check rather than an
assumption.

It was skipped when the gate was first run. Recording that here rather than
quietly running it late: the readings in results section 7 were taken before
this check existed.
"""
import argparse
import collections
import importlib.util
import math
import os
import re
import struct
import sys
import types

_origin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b13_gate0_diag.py")
_src = open(_origin, encoding="utf-8").read().split("def main()")[0]
_mod = types.ModuleType("b13diag")
_mod.__dict__["__file__"] = _origin
exec(compile(_src, _origin, "exec"), _mod.__dict__)
probe = _mod.probe

CAL = re.compile(r"^([A-Z0-9]+)([FGHJKMNQUVXZ]\d)-\1([FGHJKMNQUVXZ]\d)$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--groups", required=True)
    ap.add_argument("--spreads", required=True)
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

    want = {}
    for name in args.spreads.split(","):
        m = CAL.match(name)
        near, far = m.group(1) + m.group(2), m.group(1) + m.group(3)
        for w in (name, near, far):
            if w in ids:
                want[ids[w]] = w
        if name in ids:
            want[ids[name]] = name
    triples = []
    for name in args.spreads.split(","):
        m = CAL.match(name)
        triples.append((name, m.group(1) + m.group(2), m.group(1) + m.group(3)))

    grid = collections.defaultdict(int)
    low = {}
    seen = collections.Counter()
    stream, proc, _ = probe.open_stream(args.data)
    try:
        for key, data in probe.packets(stream, args.limit, 1e18, 5_000_000, None):
            if key not in groups:
                continue
            for tid, raw in probe.sbe_messages(data):
                if tid != 46:
                    continue
                block = struct.unpack("<H", raw[2:4])[0]
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
                    if sid in want and chr(raw[o + 26]) in "01EF":
                        px = struct.unpack("<q", raw[o:o + 8])[0]
                        seen[sid] += 1
                        if sid not in low:
                            low[sid] = px
                        elif px < low[sid]:
                            grid[sid] = math.gcd(grid[sid], low[sid] - px)
                            low[sid] = px
                        else:
                            grid[sid] = math.gcd(grid[sid], px - low[sid])
                    o += ent
    finally:
        if proc is not None:
            proc.kill()

    out = ["%-14s %14s %10s | %-12s %14s | %-12s %14s   %s"
           % ("spread", "grid", "obs", "near", "grid", "far", "grid", "verdict")]
    agree = disagree = nodata = 0
    for name, near, far in triples:
        g = [grid.get(ids.get(x, -1), 0) for x in (name, near, far)]
        n = seen.get(ids.get(name, -1), 0)
        if min(g) == 0:
            nodata += 1
            verdict = "no data"
        elif g[0] == g[1] == g[2]:
            agree += 1
            verdict = "EQUAL"
        else:
            disagree += 1
            verdict = "DIFFERENT, section 5.2 says change instrument"
        out.append("%-14s %14d %10d | %-12s %14d | %-12s %14d   %s"
                   % (name, g[0], n, near, g[1], far, g[2], verdict))
    out.append("")
    out.append("equal %d, different %d, no data %d" % (agree, disagree, nodata))
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
