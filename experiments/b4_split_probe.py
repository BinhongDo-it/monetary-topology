# -*- coding: utf-8 -*-
"""B4's split, computed on B13's carrier. A feasibility measurement, not a stage.

`docs/b4_directed_edges.md` section 5.1 splits a directed square into

    S + S'  =  2 [ w_bar_a(i,j) + w_bar_b(i,j) ]   <= 0   friction
    S - S'  =  2 [ w_hat_a(i,j) - w_hat_b(i,j) ]         index

and section 5.2 makes the split **unavailable** where a class quotes one side
only. **B5 lost the friction half on exactly that**: `results/b5_friction.json`
records three candidate sources for the official rate's spread and all three
failing, so the Argentine carrier could report `S - S'` and never `S + S'`.

B13's carrier is the first in this repository that quotes all four legs
natively. Taking class a as the implied book and class b as the directly quoted
book on the same calendar spread:

    S + S'  =  -[(F_implied - E_implied) + (F_direct - E_direct)]
    S - S'  =   2 [ mid_direct - mid_implied ]

**What this probe is for, and what it is not.** It measures whether the split is
computable at all, and whether the friction half obeys its sign constraint on
real data. It is **not** the empirical test of section 5.1's invariance claim,
which needs a dated friction change common to both classes and has no carrier
yet. **Whether the implied book and the directly quoted book are two agent
classes in B4's sense has not been adjudicated**; nothing here assumes they are,
and the arithmetic is reported as the arithmetic of two quoting mechanisms.

Theorem 4 says a positive two-cycle means `P(omega)` is empty. So the friction
half going positive even once is not noise: it is an arbitrage at that instant,
or a defect in the book. Counted, not tolerated.
"""
import argparse
import collections
import importlib.util
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
probe, Book = _mod.probe, _mod.Book

END_OF_EVENT = 0x80
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

    names = [n for n in args.spreads.split(",") if n in ids]
    sids = {ids[n]: n for n in names}
    books = collections.defaultdict(Book)
    grid = collections.defaultdict(int)
    stat = collections.defaultdict(collections.Counter)
    friction = collections.defaultdict(list)
    index = collections.defaultdict(list)
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
                    if sid in sids:
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
                    name = sids[sid]
                    eb = books[(sid, "E")].top()
                    ef = books[(sid, "F")].top()
                    db = books[(sid, "0")].top()
                    da = books[(sid, "1")].top()
                    st = stat[name]
                    st["events"] += 1
                    if None in (eb, ef, db, da):
                        st["one side missing, split unavailable"] += 1
                        continue
                    st["split available"] += 1
                    # both spreads, and the sign constraint Theorem 6(1) forces
                    s_imp, s_dir = ef[0] - eb[0], da[0] - db[0]
                    fr = -(s_imp + s_dir)
                    ix = (db[0] + da[0]) - (eb[0] + ef[0])   # 2*(mid_dir - mid_imp)
                    friction[name].append(fr)
                    index[name].append(ix)
                    st["FRICTION POSITIVE"] += fr > 0
                    st["implied spread crossed"] += s_imp < 0
                    st["direct spread crossed"] += s_dir < 0
                    st["index zero"] += ix == 0
                    for v in (s_imp, s_dir, abs(ix)):
                        if v:
                            g = grid[name]
                            grid[name] = v if g == 0 else __import__("math").gcd(g, abs(v))
                touched.clear()
    finally:
        if proc is not None:
            proc.kill()

    out = ["%-14s %8s %8s %9s | %11s %11s | %11s %11s %8s"
           % ("spread", "events", "split", "FR>0", "friction med",
              "friction min", "index med", "index |max|", "idx=0")]
    tot = collections.Counter()
    for name in sorted(stat, key=lambda k: -stat[k]["split available"]):
        st = stat[name]
        tot.update(st)
        f, i = sorted(friction[name]), index[name]
        g = grid[name] or 1
        if not f:
            out.append("%-14s %8d %8d %9d | %s" % (name, st["events"], 0, 0, "no split"))
            continue
        out.append("%-14s %8d %8d %9d | %11.1f %11.1f | %11.1f %11d %8d"
                   % (name, st["events"], len(f), st["FRICTION POSITIVE"],
                      f[len(f) // 2] / g, f[0] / g,
                      sorted(i)[len(i) // 2] / g, max(abs(x) for x in i) / g,
                      st["index zero"]))
    out.append("")
    out.append("events %d, split available %d, unavailable %d"
               % (tot["events"], tot["split available"],
                  tot["one side missing, split unavailable"]))
    out.append("**friction positive: %d**  (Theorem 4: a positive two-cycle means "
               "P(omega) is empty at that instant)" % tot["FRICTION POSITIVE"])
    out.append("implied book crossed %d, direct book crossed %d"
               % (tot["implied spread crossed"], tot["direct spread crossed"]))
    out.append("index exactly zero in %d of %d states"
               % (tot["index zero"], tot["split available"]))
    out.append("units are each instrument's own grid, measured as the gcd of the "
               "observed spreads and index values")
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
