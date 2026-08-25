# -*- coding: utf-8 -*-
"""Are the implied book and the directly quoted book two agent classes in the
sense of `docs/b4_directed_edges.md` section 5.1?

Pre-registered, criteria fixed before the code and none rewritten after. B13
section 5.1 hands over an
operational criterion for its own question:

    S - S'  is zero exactly when the two classes face the same antisymmetric
            terms on that transition

so "are these two classes" is the measurable question "is S - S' identically
zero, and if not, does the non-zero carry a persistent sign".

A bound that travels with it, and which this repository had not written down.
`S` and `S'` are each a directed four-cycle, so Theorem 4 forces **each** of
them below zero and not merely their sum. From `S <= 0` and `S' <= 0`,
`-4 S S' <= 0`, hence `(S - S')^2 <= (S + S')^2`:

    |S - S'| <= -(S + S')       equality iff one of S, S' is zero

so define `rho = |S - S'| / -(S + S')` in `[0, 1]`. A counterexample to the
bound is a code error, not a finding: R1 below voids the whole run on one.

Two phases, because a single call on the local VM is time-limited and the
capture takes minutes to decompress:

    python experiments/b4_two_classes.py --dump  --defs D --data F --groups G --spreads S [--limit N]
    python experiments/b4_two_classes.py --analyse data/cache/b13/two_classes_ch382.tsv
    python experiments/b4_two_classes.py --selftest

The dump is a reusable cache and is not deleted.
"""
import argparse
import collections
import importlib.util  # noqa: F401  (kept: the loader below mirrors b4_split_probe)
import math
import os
import struct
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_CACHE = os.path.join(ROOT, "data", "cache", "b13", "two_classes_ch382.tsv")
END_OF_EVENT = 0x80
LAGS = (1, 10, 100, 1000, 10000)


def _load_probe():
    origin = os.path.join(HERE, "b13_gate0_diag.py")
    src = open(origin, encoding="utf-8").read().split("def main()")[0]
    mod = types.ModuleType("b13diag")
    mod.__dict__["__file__"] = origin
    exec(compile(src, origin, "exec"), mod.__dict__)
    return mod.probe, mod.Book


def dump(args):
    probe, Book = _load_probe()
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
    sys.stderr.write("resolved %d of %d spread names\n"
                     % (len(names), len(args.spreads.split(","))))

    books = collections.defaultdict(Book)
    touched = set()
    seq = 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = args.out + ".part"
    n = 0
    stream, proc, _ = probe.open_stream(args.data)
    try:
        with open(tmp, "w") as fh:
            fh.write("# name\tseq\tfriction\tindex\n")
            fh.write("# friction = S + S' <= 0 ; index = S - S' ; raw PRICE9\n")
            fh.write("# s_e = implied ask - implied bid ; s_d = direct ask -"
                     " direct bid ; friction = -(s_e + s_d)\n")
            fh.write("# eb = implied bid ; db = direct bid ; so"
                     " M_E = eb + s_e/2 and M_D = db + s_d/2, the LEVELS."
                     " Theorem 6(5) needs s/2M and this is the only way to"
                     " get it\n")
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
                    seq += 1
                    for sid in sorted(touched):
                        eb = books[(sid, "E")].top()
                        ef = books[(sid, "F")].top()
                        db = books[(sid, "0")].top()
                        da = books[(sid, "1")].top()
                        if None in (eb, ef, db, da):
                            continue
                        se = ef[0] - eb[0]
                        sd = da[0] - db[0]
                        fr = -(se + sd)
                        ix = (db[0] + da[0]) - (eb[0] + ef[0])
                        fh.write("%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n"
                                 % (sids[sid], seq, fr, ix, se, sd,
                                    eb[0], db[0]))
                        n += 1
                    touched.clear()
    finally:
        if proc is not None:
            proc.kill()
    os.replace(tmp, args.out)
    print("wrote %d states to %s" % (n, os.path.relpath(args.out, ROOT)))
    return 0


def read_cache(path):
    per = collections.defaultdict(list)
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            name, seq, fr, ix = f[0], f[1], f[2], f[3]
            per[name].append((int(seq), int(fr), int(ix)))
    return per


def tick_of(per):
    """One tick in raw PRICE9. CME sends prices as integers scaled by 1e9 per
    tick on this channel, which `gate0_CLZ3-CLZ4_AB.txt` records; the gcd of the
    observed values reproduces it and is used rather than assumed."""
    g = 0
    for rows in per.values():
        for _, fr, ix in rows:
            for v in (abs(fr), abs(ix)):
                if v:
                    g = v if g == 0 else math.gcd(g, v)
    return g or 1


def grid_of(rows):
    """Each instrument's own tick, measured as the gcd of what was observed."""
    g = 0
    for _, fr, ix in rows:
        for v in (abs(fr), abs(ix)):
            if v:
                g = v if g == 0 else math.gcd(g, v)
    return g or 1


def same_sign_rate(signs, lag):
    if len(signs) <= lag:
        return None, 0
    hit = tot = 0
    for i in range(len(signs) - lag):
        a, b = signs[i], signs[i + lag]
        if a and b:
            tot += 1
            hit += (a == b)
    return (hit / tot if tot else None), tot


def analyse(path):
    per = read_cache(path)
    if not per:
        print("cache is empty:", path)
        return 1

    print("R1  structural check: |S - S'| <= -(S + S'), Theorem 4 on each of the "
          "two four-cycles separately")
    viol = 0
    allrows = []
    for name, rows in per.items():
        for _, fr, ix in rows:
            allrows.append((fr, ix))
            if abs(ix) > -fr:
                viol += 1
    print("    %d states, %d violations" % (len(allrows), viol))
    if viol:
        print("    **the bound is a theorem, so this is a code error and every "
              "reading below is void (design file section 14.3 R1)**")
        return 1
    print("    zero violations, so the readings below stand\n")

    print("R2  rho = |S - S'| / -(S + S'), in [0, 1]")
    rho = sorted(abs(ix) / -fr for fr, ix in allrows if fr < 0)
    deg = sum(1 for fr, _ in allrows if fr == 0)
    print("    median %.4f   rho=0 in %d (%.4f)   rho=1 in %d (%.4f)   "
          "friction exactly zero in %d"
          % (rho[len(rho) // 2],
             sum(1 for r in rho if r == 0), sum(1 for r in rho if r == 0) / len(rho),
             sum(1 for r in rho if r == 1), sum(1 for r in rho if r == 1) / len(rho),
             deg))
    print("    (a state at rho=1 has one of S, S' exactly zero: one direction of "
          "the round trip is free)\n")

    print("R3  is S - S' identically zero?")
    nz = sum(1 for _, ix in allrows if ix)
    print("    non-zero in %d of %d states (%.4f). identically zero: %s\n"
          % (nz, len(allrows), nz / len(allrows), "yes" if nz == 0 else "**no**"))

    print("R5  per instrument, share of non-zero states with index > 0 "
          "(symmetric noise gives about 0.5)")
    print("    %-14s %8s %8s %10s %10s %10s"
          % ("spread", "states", "non-zero", "share > 0", "rho med", "grid"))
    per_share = {}
    for name in sorted(per, key=lambda k: -len(per[k])):
        rows = per[name]
        g = grid_of(rows)
        nzr = [ix for _, _, ix in rows if ix]
        share = (sum(1 for x in nzr if x > 0) / len(nzr)) if nzr else None
        r = sorted(abs(ix) / -fr for _, fr, ix in rows if fr < 0)
        per_share[name] = share
        print("    %-14s %8d %8d %10s %10s %10d"
              % (name, len(rows), len(nzr),
                 "-" if share is None else "%.4f" % share,
                 "-" if not r else "%.4f" % r[len(r) // 2], g))
    off = [s for s in per_share.values() if s is not None and abs(s - 0.5) > 0.25]
    print("    %d of %d instruments sit further than 0.25 from 0.5\n"
          % (len(off), len(per_share)))

    print("R4  sign persistence against the null computed from the data's own "
          "marginal, p^2 + (1-p)^2")
    print("    %-14s %8s %8s %s"
          % ("spread", "p(>0)", "null", "  ".join("lag%-7d" % L for L in LAGS)))
    for name in sorted(per, key=lambda k: -len(per[k])):
        rows = sorted(per[name])
        signs = [(1 if ix > 0 else -1 if ix < 0 else 0) for _, _, ix in rows]
        nzr = [s for s in signs if s]
        if not nzr:
            continue
        p = sum(1 for s in nzr if s > 0) / len(nzr)
        null = p * p + (1 - p) * (1 - p)
        cells = []
        for L in LAGS:
            r, tot = same_sign_rate(signs, L)
            cells.append("   -    " if r is None else "%.4f  " % r)
        print("    %-14s %8.4f %8.4f %s" % (name, p, null, "".join(cells)))
    print("\n    read per design file section 14.3 R4: no threshold, the curve is "
          "the reading. **Declared on reading, 2026-08-19: this null absorbs the "
          "very thing R5 measures.** p is the whole-sample marginal, so a constant "
          "one-sided wedge raises the null by exactly as much as it raises the "
          "agreement rate. R4 therefore tests for structure *in excess of* a "
          "constant wedge and does not bear on whether there is a wedge. R5 and "
          "R6 are the readings that do.\n")

    print("R6  parity control (post hoc, declared 2026-08-19, not in the "
          "pre-registration)")
    print("    All four tops are integers on the instrument's tick grid, and")
    print("      index = (db+da) - (eb+ef),   friction = -[(da-db) + (ef-eb)]")
    print("    both reduce mod 2 to db+da+eb+ef, so **index and friction always "
          "share parity**.")
    print("    Where the friction is an odd number of ticks, index = 0 is not "
          "among the available values, and a non-zero index there says nothing "
          "about the two classes. The reading below is R3 and R5 restricted to "
          "the states where zero was available and was not taken.\n")
    T = tick_of(per)
    par_bad = sum(1 for name in per for _, fr, ix in per[name]
                  if ((fr // T) - (ix // T)) % 2)
    print("    parity identity violated in %d of %d states (must be 0)"
          % (par_bad, len(allrows)))
    if par_bad:
        print("    **the identity is arithmetic, so this is a code error**")
        return 1
    print()
    print("    %-14s %8s %8s %8s %10s %10s"
          % ("spread", "states", "fr odd", "fr even", "even, ix=0", "even>0 share"))
    tot = [0, 0, 0, 0, 0]
    for name in sorted(per, key=lambda k: -len(per[k])):
        rows = per[name]
        odd = sum(1 for _, fr, _ in rows if (fr // T) % 2)
        ev = [ix // T for _, fr, ix in rows if (fr // T) % 2 == 0]
        z = sum(1 for x in ev if x == 0)
        nzp = [x for x in ev if x]
        sh = (sum(1 for x in nzp if x > 0) / len(nzp)) if nzp else None
        print("    %-14s %8d %8d %8d %10d %10s"
              % (name, len(rows), odd, len(ev), z,
                 "-" if sh is None else "%.4f" % sh))
        tot[0] += len(rows); tot[1] += odd; tot[2] += len(ev); tot[3] += z
        tot[4] += len(nzp)
    print("    %-14s %8d %8d %8d %10d" % ("all", tot[0], tot[1], tot[2], tot[3]))
    print("\n    where parity allowed a zero, the index is zero in %.4f of states; "
          "over the whole sample it is zero in %.4f"
          % (tot[3] / tot[2], tot[3] / tot[0]))
    print("    read per design file section 14: the verdict is **per position "
          "edge**, because section 5.1's construction is about one edge (i, j) "
          "and not about the two mechanisms in general.")
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    # the bound, on the algebra rather than on data
    import random
    rng = random.Random(11)
    worst = 0.0
    for _ in range(20000):
        s = -abs(rng.gauss(0, 3))
        s2 = -abs(rng.gauss(0, 3))
        worst = max(worst, abs(s - s2) + (s + s2))
    chk("|S - S'| <= -(S + S') for 20000 random pairs with S, S' <= 0", worst <= 1e-12)
    chk("equality when one of them is zero", abs(abs(0 - (-4.0)) - 4.0) < 1e-12)

    chk("same-sign rate of a constant sign is 1",
        same_sign_rate([1] * 50, 1)[0] == 1.0)
    chk("same-sign rate of a strict alternation at lag 1 is 0",
        same_sign_rate([1, -1] * 25, 1)[0] == 0.0)
    chk("same-sign rate of a strict alternation at lag 2 is 1",
        same_sign_rate([1, -1] * 25, 2)[0] == 1.0)
    chk("zeros are skipped, not counted as agreeing",
        same_sign_rate([1, 0, 1], 1)[1] == 0)
    chk("lag longer than the series returns None",
        same_sign_rate([1, 1], 5)[0] is None)

    chk("index and friction share parity, on the algebra",
        all(((db + da) - (eb + ef)) % 2 == (-((da - db) + (ef - eb))) % 2
            for db in range(4) for da in range(4)
            for eb in range(4) for ef in range(4)))
    chk("tick_of picks the gcd across instruments",
        tick_of({"a": [(0, -6 * 10 ** 9, 4 * 10 ** 9)],
                 "b": [(0, -9 * 10 ** 9, 0)]}) == 10 ** 9)
    chk("grid is the gcd of what was observed",
        grid_of([(0, -6, 4), (1, -9, 0)]) == 1 and grid_of([(0, -6, 4), (1, -8, 0)]) == 2)

    r = rng.Random if False else random.Random(3)
    signs = [1 if r.random() < 0.5 else -1 for _ in range(20000)]
    p = sum(1 for s in signs if s > 0) / len(signs)
    obs, _ = same_sign_rate(signs, 1)
    chk("independent signs land on the null within 0.02",
        abs(obs - (p * p + (1 - p) ** 2)) < 0.02)

    print("\n  " + ("全部通过" if ok else "有失败"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--analyse")
    ap.add_argument("--defs")
    ap.add_argument("--data")
    ap.add_argument("--groups")
    ap.add_argument("--spreads")
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--out", default=DEFAULT_CACHE)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.analyse:
        return analyse(a.analyse)
    if a.dump:
        for k in ("defs", "data", "groups", "spreads"):
            if not getattr(a, k):
                ap.error("--dump needs --" + k)
        return dump(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
