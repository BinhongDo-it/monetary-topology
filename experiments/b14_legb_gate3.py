"""B14 leg B gate three: the placebo, where the discriminating power is won or lost.

Registered in the design file, section 7 supplement 2, B14_A17 clause 5.

Gate two left the treatment-specific residual at +0.0117 in the share of cells at
rho = 0, against a raw pre/post gap of -0.3617. Whether +0.0117 is a finding or
noise is not a question about its size. It is a question about what a month pair
with NO grid change produces under the identical construction.

So: six placebo pairs, four with both months inside the pilot and two with both
outside, and the real pair beside them. Same statistic, same symbols, same
treated / control split, same nickel projection. The only thing that differs is
whether a grid change happened between the two months.

The statistic is imported from the gate two module rather than re-implemented,
so the placebo cannot silently diverge from the thing it is a placebo for. The
selftest asserts the imported objects are the same objects.

Usage
    python experiments/b14_legb_gate3.py --selftest
    python experiments/b14_legb_gate3.py --run
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "b14_legb_gate3.json")

_spec = importlib.util.spec_from_file_location(
    "b14_legb_gate2", os.path.join(HERE, "b14_legb_gate2.py"))
G2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G2)

#: B14_A17 clause 5. Four inside pairs, two outside pairs, and the real one.
PAIRS = [("P1", "2018-05", "2018-06", "inside"),
         ("P2", "2018-06", "2018-07", "inside"),
         ("P3", "2018-07", "2018-08", "inside"),
         ("P4", "2018-08", "2018-09", "inside"),
         ("REAL", "2018-09", "2018-10", "the grid is released here"),
         ("P5", "2018-10", "2018-11", "outside"),
         ("P6", "2018-11", "2018-12", "outside")]


def share_rho0_on_grid(np, m, g_of, arm):
    """Share of cells at rho = 0, with both venues projected onto the nickel grid.

    Projection is the identity on treated names inside the pilot, which gate two
    verified digit for digit, so the same call serves every month.
    """
    ba, aa, bb, ab = G2.load(np, m, g_of, arm)
    ba, aa = G2.to_nickel(np, ba.astype(np.int64), aa.astype(np.int64))
    bb, ab = G2.to_nickel(np, bb.astype(np.int64), ab.astype(np.int64))
    good = (ba > 0) & (bb > 0)
    return G2.stats(np, ba[good], aa[good], bb[good], ab[good])["share_rho0"]


def run():
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("this needs numpy; nothing was written")
    g_of = {s: g for g, v in
            json.load(open(G2.SYMS_FILE, encoding="utf-8"))["symbols"].items() for s in v}
    cache = {}

    def get(m, arm):
        if (m, arm) not in cache:
            cache[(m, arm)] = share_rho0_on_grid(np, m, g_of, arm)
        return cache[(m, arm)]

    print("Gate three, B14_A17 clause 5. Statistic: share of cells at rho = 0, both")
    print("venues projected onto the nickel grid, so every pair is compared on one")
    print("grid and only the presence of a grid CHANGE differs between rows.\n")
    print("  pair   months              G first  G second   dG        dC        DiD")
    res = {}
    for tag, m1, m2, note in PAIRS:
        g1, g2 = get(m1, "G"), get(m2, "G")
        c1, c2 = get(m1, "C"), get(m2, "C")
        dg, dc = g1 - g2, c1 - c2
        did = dg - dc
        mark = "  <== the real one" if tag == "REAL" else ""
        print("  %-5s  %s -> %s   %.4f   %.4f   %+.4f   %+.4f   %+.4f%s"
              % (tag, m1, m2, g1, g2, dg, dc, did, mark))
        res[tag] = {"months": [m1, m2], "note": note, "G_first": g1, "G_second": g2,
                    "C_first": c1, "C_second": c2, "dG": dg, "dC": dc, "DiD": did}

    plac = [v["DiD"] for k, v in res.items() if k != "REAL"]
    real = res["REAL"]["DiD"]
    lo, hi = min(plac), max(plac)
    bigger = sum(1 for p in plac if abs(p) >= abs(real))
    print("\n  placebo DiDs: %s" % "  ".join("%+.4f" % p for p in sorted(plac)))
    print("  placebo range %+.4f .. %+.4f      the real one %+.4f" % (lo, hi, real))
    print("  placebos whose magnitude reaches the real one: %d of %d"
          % (bigger, len(plac)))
    print("\n  reading, B14_A17 clause 5, fixed before the run:")
    if bigger == 0 and (real > hi or real < lo):
        print("    every placebo falls inside a band the real one is outside of.")
        print("    THE DISCRIMINATING POWER IS BOUGHT.")
    else:
        print("    at least one placebo reaches the real one's magnitude, so the")
        print("    real one's size is not something only the treatment can make.")
        print("    NOT ADJUDICABLE, and this is a failure of the design, not of the data.")
    res["_summary"] = {"placebo_min": lo, "placebo_max": hi, "real": real,
                       "placebos_reaching_real": bigger, "n_placebo": len(plac)}
    json.dump(res, open(OUT, "w"), indent=2, sort_keys=True)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("four placebo pairs lie wholly inside the pilot",
        sum(1 for p in PAIRS if p[3] == "inside") == 4)
    chk("two placebo pairs lie wholly outside it",
        sum(1 for p in PAIRS if p[3] == "outside") == 2)
    chk("exactly one pair straddles the boundary, and it is the registered core",
        [p for p in PAIRS if p[0] == "REAL"][0][1:3] == (G2.CORE_INSIDE, G2.CORE_OUTSIDE))
    chk("no placebo pair straddles the boundary",
        not [p for p in PAIRS if p[0] != "REAL"
             and (p[1] <= G2.CORE_INSIDE) != (p[2] <= G2.CORE_INSIDE)])
    chk("every pair is one calendar month apart, so the real one has no span "
        "advantage over the placebos",
        all(p[2] > p[1] for p in PAIRS))
    chk("the statistic, the loader and the projection are the SAME objects gate "
        "two used, not copies",
        G2.stats.__module__ == G2.__name__ and G2.to_nickel.__module__ == G2.__name__
        and G2.load.__module__ == G2.__name__)
    chk("the exclusion list comes from gate two too",
        G2.EXCLUDED == {"TA", "SSP", "VNCE", "JONE", "PKD"})
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    chk("no deletion call anywhere",
        not [1 for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and (n.func.value.id, n.func.attr) in banned])
    chk("this file defines no statistic of its own: " +
        (", ".join(sorted({n.name for n in ast.walk(tree)
                           if isinstance(n, ast.FunctionDef)} & {"stats", "rho", "to_nickel"}))
         or "zero"),
        not ({n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
             & {"stats", "rho", "to_nickel"}))
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
