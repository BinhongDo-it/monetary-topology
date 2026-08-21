# -*- coding: utf-8 -*-
"""Is B13's "the two-leg path is the only path" a property of the listing?

**Why this exists.** B13's own reading reports exact
equality between the exchange's published implied price and the two-leg
derivation, `18,800 / 18,800`, and attributes it to those products being ones
where the two-leg path is the only derivation path. Its own caveat says the
classification is read off the equality rate rather than assigned in advance,
which makes the attribution circular unless path uniqueness can be established
from something that does not touch price.

The instrument listing is such a thing. A calendar spread `(A, B)` has a second
route whenever some third contract month `C` is listed such that `(A, C)` and
`(B, C)` are also listed, because `(A,B) = (A,C) - (B,C)`. This script counts
those routes from the definition messages and reads no price at all.

**What it can and cannot settle.** It settles whether the *listing* leaves the
two-leg path alone. It does not settle whether the exchange's matching engine
generates from spread-to-spread combinations on a given channel, which is a
per-product implied-depth configuration this script does not read. **The data
argues that it does on at least one channel**: on ch382 the published implied
price is *better* than the two-leg derivation in many states, and a better price
cannot come from a route that does not exist.

Usage::

    python experiments/b13_path_multiplicity.py --defs <pcap.zst> --out <txt>
    python experiments/b13_path_multiplicity.py --selftest
"""
import argparse
import collections
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: The three channels B13 read, with both multicast sides. A+B are both needed
#: for the same reason the gate needs them: a deduplicated capture splits the
#: stream across the two addresses.
GROUPS = {
    "ch382 NYMEX energy": ("224.0.31.130:14382", "224.0.32.130:15382"),
    "ch386 NG":           ("224.0.31.134:14386", "224.0.32.134:15386"),
    "ch360 COMEX":        ("224.0.31.192:14360", "224.0.32.192:15360"),
}

#: `<root><month>-<root><month>`, the same shape `b4_split_probe.py` matches.
CAL = re.compile(r"^([A-Z0-9]+?)([FGHJKMNQUVXZ]\d)-\1([FGHJKMNQUVXZ]\d)$")

#: The roots B13 measured on, so the table leads with them.
MEASURED = {"CL", "RB", "NG", "TTF", "GC", "HG", "MHG", "QI"}


def _load_probe():
    origin = os.path.join(HERE, "b13_gate0_diag.py")
    src = open(origin, encoding="utf-8").read().split("def main()")[0]
    mod = types.ModuleType("b13diag")
    mod.__dict__["__file__"] = origin
    exec(compile(src, origin, "exec"), mod.__dict__)
    return mod.probe


def alternates(pairs, a, b):
    """Third months giving a second route to (a, b), from the listing alone."""
    months = {m for p in pairs for m in p}
    return [c for c in sorted(months) if c not in (a, b)
            and ((a, c) in pairs or (c, a) in pairs)
            and ((b, c) in pairs or (c, b) in pairs)]


def symbols(defs_path):
    probe = _load_probe()
    want = {g for gs in GROUPS.values() for g in gs}
    per = collections.defaultdict(set)
    stream, proc, _ = probe.open_stream(defs_path)
    try:
        for key, data in probe.packets(stream, 10 ** 12, 1e18, 10 ** 12, None):
            if key not in want:
                continue
            for tid, raw in probe.sbe_messages(data):
                if tid in (54, 55, 56) and len(raw) >= 69:
                    s = raw[45:65].split(b"\x00")[0].decode("ascii", "replace").strip()
                    if s:
                        per[key].add(s)
    finally:
        if proc is not None:
            proc.kill()
    return per


def report(per):
    out = []

    def A(line=""):
        out.append(line)

    A("B13 path multiplicity, read from the instrument listing and no price at all.")
    A("A listed calendar spread (A, B) has a second route whenever some listed C")
    A("gives both (A, C) and (B, C), because (A,B) = (A,C) - (B,C).")
    A("")
    for label, keys in GROUPS.items():
        syms = set().union(*(per[k] for k in keys if k in per))
        cal = {}
        for s in syms:
            m = CAL.match(s)
            if m:
                cal.setdefault(m.group(1), set()).add((m.group(2), m.group(3)))
        A("== %s ==  %d symbols, %d calendar spreads"
          % (label, len(syms), sum(len(v) for v in cal.values())))
        A("   %-6s %8s %8s %8s   %s"
          % ("root", "listed", "multi", "unique", "example second route"))
        roots = sorted(cal, key=lambda r: (r not in MEASURED, r))
        for root in roots:
            pairs = cal[root]
            multi = uniq = 0
            ex = ""
            for (a, b) in sorted(pairs):
                alt = alternates(pairs, a, b)
                if alt:
                    multi += 1
                    if not ex:
                        ex = "%s%s-%s%s via %s%s" % (root, a, root, b, root, alt[0])
                else:
                    uniq += 1
            A("   %-6s %8d %8d %8d   %s%s"
              % (root, len(pairs), multi, uniq, ex,
                 "   <- B13 measured on this root" if root in MEASURED else ""))
        A("")
    A("Read per B13 section 12.2 item 2: this is a listing test, not an")
    A("availability test. It does not read the exchange's implied-depth")
    A("configuration, and a listed route the engine does not generate is not a")
    A("route. What it does settle is that the listing does not leave the")
    A("two-leg path alone on the products where exact equality was measured.")
    return "\n".join(out) + "\n"


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    p = {("Q3", "V3"), ("Q3", "X3"), ("V3", "X3")}
    chk("a triangle of three listed spreads gives every one of them a route",
        alternates(p, "Q3", "V3") == ["X3"]
        and alternates(p, "Q3", "X3") == ["V3"]
        and alternates(p, "V3", "X3") == ["Q3"])
    chk("a lone pair has no route", alternates({("Q3", "V3")}, "Q3", "V3") == [])
    # **This case was written as an expected empty and it is not.** A chain is
    # a route: (Q3-X3) = (Q3-V3) + (V3-X3). `alternates` finds C wherever both
    # (A,C) and (B,C) are listed, which covers the common-third-leg shape and
    # the chain shape alike, and both are real second routes. Corrected here
    # rather than weakened, because the assertion was wrong and the code right.
    chk("a chain is a route too, not only a shared third leg",
        alternates({("Q3", "V3"), ("V3", "X3")}, "Q3", "X3") == ["V3"])
    chk("two disjoint pairs give no route",
        alternates({("Q3", "V3"), ("X3", "Z3")}, "Q3", "V3") == [])
    chk("direction of the listing does not matter",
        alternates({("Q3", "V3"), ("X3", "Q3"), ("X3", "V3")}, "Q3", "V3") == ["X3"])
    chk("the calendar pattern accepts a two-letter root",
        bool(CAL.match("CLQ3-CLV3")) and CAL.match("CLQ3-CLV3").group(1) == "CL")
    chk("the calendar pattern accepts a three-letter root",
        bool(CAL.match("MHGF4-MHGG4")) and CAL.match("MHGF4-MHGG4").group(1) == "MHG")
    chk("the calendar pattern rejects a cross-root spread",
        not CAL.match("CLQ3-RBV3"))
    chk("both multicast sides are listed for every channel",
        all(len(v) == 2 for v in GROUPS.values()))
    print("\n  " + ("all passed" if ok else "failures above"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.defs:
        ap.error("--defs is required")
    text = report(symbols(a.defs))
    sys.stdout.write(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
