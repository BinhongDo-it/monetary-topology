"""Widen a station's sampling support and see which of its criteria can then fail.

`check_welded_premise.py` hands over a named list of criteria whose sample comes
from a bounded generator. Reading that list settles nothing on its own, because
whether a support brackets a predicate is a question about the station's
mathematics. This is the experiment that settles it, and it is the one `B96-8`
ran by hand on 2026-09-13: widen the support, redraw, and score the same
criteria. A criterion that flips from true to false was being held up by the
support rather than by the mechanism.

**A negative result here means nothing without the positive control**, because
"no criterion flipped" and "the probe never reached the criteria" print the same
way. That is the lesson the rules record about a seeded self-test: a guard that
did not fire and a seed that was never planted look alike. So `--selftest` runs
the known instance, `B96`'s `NB_OWN_USE`, and requires `B96-2` to fall.

Nothing is written to disk. The station module is imported, its module-level
constants are set and restored, and its own criterion functions are called.

**A flip answers yes or no, and the width answers how far.** `--sweep` walks one
endpoint of one support across a grid and scores the criteria at every point, so
what comes back is not a verdict but the place the verdict changes. That number
is the scope of the reading, and this repository has never printed one: the exact
string `support_width` appears nowhere, and of the station scripts only two carry
a sweep at all. A grid is used rather than a bisection because a flip has no
reason to be monotone in the endpoint, and printing the whole walk is the same
rule as printing the object rather than the count.

Run:
    python scripts/widen_support_probe.py --selftest
    python scripts/widen_support_probe.py b95_joint_lives EFFICIENCY 0.02 5.0
    python scripts/widen_support_probe.py b88_two_margins YIELD 0.5 2.0 \
        CORN_FACTOR 0.3 3.0 LABOUR_FACTOR 0.3 3.0
    python scripts/widen_support_probe.py --sweep b95_joint_lives EFFICIENCY \
        lo 0.20 0.02 7 --draw-args 1500 120
"""

from __future__ import annotations

import argparse
import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

SKIP = ("crit_registration",)


def criteria_of(module):
    return [n for n in dir(module)
            if n.startswith("crit") and n not in SKIP
            and callable(getattr(module, n))]


def score(module, sample):
    out = {}
    for name in criteria_of(module):
        fn = getattr(module, name)
        try:
            arity = len(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            arity = 1
        try:
            result = fn(sample) if arity >= 1 else fn()
            out[name] = bool(result[0] if isinstance(result, tuple) else result)
        except Exception as exc:
            out[name] = "skipped, " + type(exc).__name__
    return out


def draw_and_score(module, draw_args):
    import numpy as np
    rng = np.random.default_rng(getattr(module, "SEED", 0))
    sample = module.draws(rng, *draw_args)
    return score(module, sample), sample


def run(name, overrides, draw_args, quiet=False):
    module = __import__(name)
    if not hasattr(module, "draws"):
        print(name + " has no draws(), so this probe does not reach it")
        return {}, {}, []
    keep = {}
    for key in overrides:
        if not hasattr(module, key):
            print(name + " has no constant named " + key)
            return {}, {}, []
        keep[key] = getattr(module, key)
    base, _ = draw_and_score(module, draw_args)
    for key, value in overrides.items():
        setattr(module, key, value)
    try:
        wide, _ = draw_and_score(module, draw_args)
    finally:
        for key, value in keep.items():
            setattr(module, key, value)
    flipped = [k for k in base if base.get(k) is True and wide.get(k) is False]
    if not quiet:
        print(name + "   " + ", ".join(
            k + " " + str(keep[k]) + " -> " + str(overrides[k]) for k in overrides))
        for key in sorted(set(base) | set(wide)):
            mark = "   <- flips" if key in flipped else ""
            print("    " + key.replace("crit_", "").ljust(22)
                  + " as registered=" + str(base.get(key))
                  + "  widened=" + str(wide.get(key)) + mark)
        print("    flipped: " + (", ".join(flipped) if flipped else "none"))
    return base, wide, flipped


def selftest():
    """The positive control. `B96`'s support is the known welded one."""
    checks = []
    base, wide, flipped = run("b96_basics_and_subsystems",
                              {"NB_OWN_USE": (0.0, 0.60)}, (250,), quiet=True)
    scored = [k for k, v in base.items() if isinstance(v, bool)]
    checks.append(("the probe reaches the criteria", len(scored) >= 4))
    checks.append(("B96-2 holds at the registered support",
                   base.get("crit_rate_from_basics") is True))
    checks.append(("B96-2 falls once the support is widened",
                   wide.get("crit_rate_from_basics") is False))
    checks.append(("and the flip is reported",
                   "crit_rate_from_basics" in flipped))
    base2, wide2, flipped2 = run("b96_basics_and_subsystems",
                                 {"NB_OWN_USE": (0.0, 0.10)}, (250,), quiet=True)
    checks.append(("re-stating the registered support flips nothing",
                   not flipped2))
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sweep("b96_basics_and_subsystems", "NB_OWN_USE", "hi", 0.10, 0.80, 4, (120,))
    text = buf.getvalue()
    checks.append(("the sweep prints a row for every point",
                   text.count("0.1,") + text.count("0.1 ") >= 1
                   and text.count("True") >= 1 and text.count("False") >= 1))
    checks.append(("the sweep names where the known welded arm stops holding",
                   "rate_from_basics: last holds at" in text))
    for label, passed in checks:
        print("  " + ("ok  " if passed else "FAIL") + "  " + label)
    return 0 if all(p for _, p in checks) else 1


def sweep(name, const, which, start, stop, steps, draw_args):
    """Walk one endpoint across a grid and score the criteria at every point.

    The other endpoint stays at the value the station registered, so what moves
    is one number and the walk says where each criterion stops holding. A grid
    rather than a bisection: a flip is not owed monotonicity in the endpoint, and
    a bisection that assumes it would report a boundary that is not there.
    """
    module = __import__(name)
    if not hasattr(module, const):
        print(name + " has no constant named " + const)
        return 0
    registered = tuple(float(x) for x in getattr(module, const))
    if which not in ("lo", "hi"):
        print("which endpoint: lo or hi")
        return 0
    points = [start + (stop - start) * i / max(1, steps - 1) for i in range(steps)]
    print(name + "  " + const + " registered " + str(registered)
          + ", walking the " + which + " endpoint from " + format(start, ".4g")
          + " to " + format(stop, ".4g") + " in " + str(steps) + " steps")
    keep = getattr(module, const)
    table, names = [], []
    try:
        for value in points:
            edge = ((value, registered[1]) if which == "lo"
                    else (registered[0], value))
            setattr(module, const, edge)
            scored, _ = draw_and_score(module, draw_args)
            if not names:
                names = sorted(k for k, v in scored.items() if isinstance(v, bool))
            table.append((edge, scored))
    finally:
        setattr(module, const, keep)
    head = "  " + const.ljust(14) + "  " + "  ".join(
        k.replace("crit_", "")[:13].ljust(13) for k in names)
    print(head)
    for edge, scored in table:
        row = "  " + (format(edge[0], ".4g") + ", " + format(edge[1], ".4g")).ljust(14)
        row += "  " + "  ".join(
            ("True " if scored.get(k) is True else
             "False" if scored.get(k) is False else "  .  ").ljust(13) for k in names)
        print(row)
    print("")
    for key in names:
        seq = [(edge, scored.get(key)) for edge, scored in table]
        flips = [(seq[i - 1][0], seq[i][0]) for i in range(1, len(seq))
                 if seq[i - 1][1] is True and seq[i][1] is False]
        if flips:
            first = flips[0]
            print("  " + key.replace("crit_", "")
                  + ": last holds at " + str(tuple(format(x, ".4g") for x in first[0]))
                  + ", first fails at " + str(tuple(format(x, ".4g") for x in first[1]))
                  + ("  (and flips " + str(len(flips)) + " times across the walk, "
                     "so the boundary is not a single point)" if len(flips) > 1 else ""))
        elif all(v is True for _, v in seq):
            print("  " + key.replace("crit_", "")
                  + ": holds across the whole walk, so this walk does not reach its edge")
        elif all(v is False for _, v in seq):
            print("  " + key.replace("crit_", "")
                  + ": fails across the whole walk, including at the registered endpoint")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module", nargs="?")
    ap.add_argument("spec", nargs="*",
                    help="NAME LO HI, repeated; with --sweep, NAME lo|hi FROM TO STEPS")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--draw-args", nargs="*", type=int, default=[],
                    help="positional arguments passed to the module's draws()")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.sweep:
        if not args.module or len(args.spec) != 5:
            ap.error("--sweep takes MODULE NAME lo|hi FROM TO STEPS")
        return sweep(args.module, args.spec[0], args.spec[1],
                     float(args.spec[2]), float(args.spec[3]), int(args.spec[4]),
                     tuple(args.draw_args))
    if not args.module or len(args.spec) % 3:
        ap.error("give a module and then NAME LO HI for each support")
    overrides = {}
    for i in range(0, len(args.spec), 3):
        overrides[args.spec[i]] = (float(args.spec[i + 1]), float(args.spec[i + 2]))
    run(args.module, overrides, tuple(args.draw_args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
