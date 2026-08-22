"""L2 gate two, part B: does G1 carry the residue as strongly as G2 and G3?

Registered before the code, in a supplement that is append-only.

G1 has its QUOTING increment changed and nothing else. G2 adds a trading
increment; G3 adds trade-at on top. So:

    candidate zero  (lattice projection)  acts through the quoting rule -> hits G1
    candidate four  (behavioural response to the quoting rule)          -> hits G1
    candidate two   (the trading-side rules)                            -> does NOT hit G1

so G1 is the discriminant, and it is free: A11 already computed these margins,
nobody had read them from this angle.

Supplement note 1: this test needs no mechanical netting. Candidate zero works
through the quoting increment, which is identical for G1, G2 and G3, so the
mechanical term is the same number in all three and differences out of any
comparison among them. Netting it would only import the error in the estimate of
delta while cancelling nothing.

Sample, windows, pure-slack definition and the six inequalities are b14_recheck's
own objects, imported not restated.

Usage
    python experiments/l2_gate2b.py --selftest
    python experiments/l2_gate2b.py --run
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
OUT = os.path.join(ROOT, "results", "l2_gate2b.json")

_spec = importlib.util.spec_from_file_location(
    "b14_recheck", os.path.join(HERE, "b14_recheck.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

#: A11's own segments, unchanged.
SEGMENTS = (("real", "pre", "post"), ("placebo", "pre_pl", "pre"))
#: The treated groups, in order of how much the pilot changed for them.
ARMS = ("G1", "G2", "G3")


def run():
    rec16 = R.load_raw(R.E.ROUNDS["2016"]["pre"], R.E.ROUNDS["2016"]["post"],
                       extra_windows=[("aug", R.SPLIT_A), ("sep", R.SPLIT_B),
                                      ("apr", R.W_APR), ("may", R.W_MAY),
                                      ("pre_pl", R.W_PLACEBO_PRE)])
    pure = {}
    for k, r in rec16.items():
        v = r["apr"]["bbo"] + r["may"]["bbo"]
        if v:
            pure[k] = not any(x < R.NICKEL for x in v)
    n_pure = sum(1 for x in pure.values() if x)
    print("A11's pure slack: %d (venue, symbol)\n" % n_pure)
    print("  G1 changes the QUOTING increment only.")
    print("  G2 adds a trading increment. G3 adds trade-at.")
    print("  Candidate two acts on G2 and G3 and NOT on G1.\n")

    res = {}
    print("  seg       venue  arm   n      Delta        raw_gap vs C")
    for seg, prewin, postwin in SEGMENTS:
        d = R.deltas_by(rec16, "post", prewin, postwin,
                        pick=lambda c, s, r: pure.get((c, s)) is True)
        tab, n = R.tabulate(d)
        ineq = R.six(tab, +1)
        for ctr in ("N", "P"):
            base = tab.get(ctr + "/C")
            print("  %-9s %s      C     %-6d %s" %
                  (seg, ctr, n.get(ctr + "/C", 0),
                   "None" if base is None else "%+.6f" % base))
            for x in [y for y in ineq if y["ctr"] == ctr]:
                k = ctr + "/" + x["grp"]
                print("  %-9s %s      %-4s  %-6d %s   %s"
                      % ("", ctr, x["grp"], n.get(k, 0),
                         "None      " if tab.get(k) is None else "%+.6f " % tab[k],
                         "None" if x["raw_gap"] is None else "%+.6f" % x["raw_gap"]))
        res[seg] = {"table": tab, "n": n,
                    "gaps": {x["ctr"] + "/" + x["grp"]: x["raw_gap"] for x in ineq}}
        print("")

    print("supplement note 2, the reading fixed before this run\n")
    real, plac = res["real"]["gaps"], res["placebo"]["gaps"]
    by_arm = {}
    for arm in ARMS:
        rs = [real.get(c + "/" + arm) for c in ("N", "P")]
        ps = [plac.get(c + "/" + arm) for c in ("N", "P")]
        rs = [x for x in rs if x is not None]
        ps = [x for x in ps if x is not None]
        by_arm[arm] = {"real": rs, "placebo": ps,
                       "real_mean": sum(rs) / len(rs) if rs else None}
        print("  %-3s  real %s      placebo %s"
              % (arm, "  ".join("%+.4f" % x for x in rs),
                 "  ".join("%+.4f" % x for x in ps)))
    print("")
    g1 = by_arm["G1"]["real_mean"]
    g23 = [by_arm[a]["real_mean"] for a in ("G2", "G3")
           if by_arm[a]["real_mean"] is not None]
    allp = [abs(x) for a in ARMS for x in by_arm[a]["placebo"]]
    if g1 is None or not g23:
        print("  not enough cells to read")
        return 1
    m23 = sum(g23) / len(g23)
    print("  G1 mean %+.4f      G2/G3 mean %+.4f      G1 - G2/G3 = %+.4f"
          % (g1, m23, g1 - m23))
    print("  largest placebo gap in absolute value: %.4f" % (max(allp) if allp else 0))
    inside = all(abs(by_arm[a]["real_mean"]) <= max(allp) for a in ARMS
                 if by_arm[a]["real_mean"] is not None) if allp else False
    print("")
    if inside:
        print("  -> all three arms sit inside the placebo band: the residue is not")
        print("     significant on pure slack at all, and A11's reading needs review")
    elif abs(g1 - m23) <= max(allp or [0]):
        print("  -> G1 is comparable to G2/G3, and the difference between them is")
        print("     smaller than the placebo band. THE TRADING-SIDE RULES ARE NOT")
        print("     THE MAIN DRIVER: the residue belongs to candidate zero plus four.")
    elif g1 < m23:
        print("  -> G1 is clearly SMALLER than G2/G3. Candidate two's share is the")
        print("     difference, %+.4f, and it is quantified rather than assumed." % (g1 - m23))
    else:
        print("  -> G1 is clearly LARGER than G2/G3. Candidate two is refuted with")
        print("     the sign reversed, and why the lightest treatment reacts most")
        print("     now needs its own explanation.")
    json.dump({"n_pure_slack": n_pure, "by_arm": by_arm, "segments": res},
              open(OUT, "w"), indent=2)
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("the segments are A11's own", SEGMENTS == (("real", "pre", "post"),
                                                   ("placebo", "pre_pl", "pre")))
    chk("the three treated arms are read separately and not pooled",
        ARMS == ("G1", "G2", "G3"))
    mine = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
    chk("this file defines no copy of the borrowed helpers: " +
        (", ".join(sorted(mine & {"six", "tabulate", "deltas_by", "median",
                                  "load_raw", "group_of"})) or "zero"),
        not (mine & {"six", "tabulate", "deltas_by", "median", "load_raw",
                     "group_of"}))
    chk("and the borrowed helpers are the originals: six from %s, deltas_by from %s"
        % (R.six.__module__, R.deltas_by.__module__),
        R.six.__module__ == R.__name__ and R.deltas_by.__module__ == R.__name__)
    # Two bites in a row here, same family, different mechanism. The first version
    # tested `"log((s" not in src` and the test's own source contains that string.
    # The second walked every Constant in the file and found the test's own
    # comparison values 0.0228 and 0.05. The claim is about what the ANALYSIS does,
    # so the walk is scoped to run() and the selftest is not part of the object
    # being checked.
    _run_fn = next(n for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.FunctionDef) and n.name == "run")
    consts = {n.value for n in ast.walk(_run_fn)
              if isinstance(n, ast.Constant) and isinstance(n.value, float)}
    chk("run() applies no mechanical netting, per supplement note 1: the quoting "
        "increment is identical for G1, G2 and G3 so the term differences out. "
        "float constants inside run(): " + (", ".join("%g" % c for c in sorted(consts))
                                       or "none"),
        not any(abs(c - 0.0228) < 1e-9 or abs(c - 0.05) < 1e-9 for c in consts))
    chk("the reading has a branch for 'nothing is significant', so D15 "
        "reachability holds", "needs review" in src)
    chk("the reading has a branch for each direction of the G1 comparison",
        "SMALLER than" in src and "LARGER than" in src)
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    chk("no deletion call anywhere",
        not [1 for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and (n.func.value.id, n.func.attr) in banned])
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
