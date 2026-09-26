"""A criterion whose sample cannot contain a counterexample has not been tested.

`11f`'s existing guard, `check_criteria_can_fail.py`, finds verdicts written as a
literal. This one finds the other shape, the one that guard is structurally blind
to: the verdict is computed honestly, and the generator that produced the sample
draws from a support that satisfies the predicate by construction.

The instance that bought this scan is `B96-2` on 2026-09-13. Its criterion asks
whether the non-basic block's spectral radius stays under the core's. The
generator drew the non-basic block's own use from `NB_OWN_USE = (0.0, 0.10)`,
small on purpose, so no draw in the main sample could ever put it above. The
verdict was computed, the statement was true, and the arm could not have failed:
0 of 60 draws were able to violate it. The repair was not to rewrite the verdict
but to widen the support in a second arm and sweep across the boundary.

**This scan does not prove anything. It hands over a named list.** Deciding
whether a given support brackets a given comparison is a question about the
mathematics of that station, and the answer is not in the syntax. So the output
is one line per candidate carrying the support constants and the comparison
lines, which is the shape that lets a reader settle it by reading, in keeping
with rule 11: print the object, not the count.

Scope: every station script that both draws from a bounded support named by a
module constant and compares drawn quantities inside a criterion. A script with
no synthetic generator cannot have this defect and is not listed.

Run:
    python scripts/check_welded_premise.py
    python scripts/check_welded_premise.py --selftest
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

DRAW = re.compile(
    r"(?:rng|random|np\.random|generator|_rng)\s*\.\s*"
    r"(uniform|normal|integers|randint|choice|random_sample|lognormal|beta|gamma)\s*\("
)
CRIT = ("crit", "criterion", "criteria")


def numeric_constants(tree):
    """Module-level assignments to an upper-case name with a numeric value.

    A scalar and a two-tuple are both kept: a support can be written either way,
    and `B96`'s was a tuple while other stations write scalar bounds.
    """
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or not target.id.isupper():
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                continue
            if isinstance(value, (int, float)):
                out[target.id] = value
            elif isinstance(value, tuple) and value and all(
                    isinstance(v, (int, float)) for v in value):
                out[target.id] = value
    return out


def draw_supports(source, constants):
    """Constants that appear inside the parentheses of a draw call.

    Matched on the text of the call rather than on the tree, because the repo
    writes the same support three ways: `rng.uniform(*NAME)`, `rng.uniform(lo,
    NAME)`, and `rng.uniform(NAME[0], NAME[1])`.
    """
    found = set()
    for match in DRAW.finditer(source):
        depth, i = 1, match.end()
        while i < len(source) and depth:
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
            i += 1
        inside = source[match.end():i]
        for name in constants:
            if re.search(r"\b" + re.escape(name) + r"\b", inside):
                found.add(name)
    return found


def comparisons(fn, source):
    """Comparison lines inside a criterion, both sides non-literal.

    A comparison against a literal is a threshold and is governed by the banned
    shapes table, not by this scan. What this scan is after is a comparison
    between two quantities that both come out of the sample.
    """
    lines = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        sides = [node.left] + list(node.comparators)
        if any(isinstance(s, ast.Constant) for s in sides):
            continue
        try:
            text = ast.get_source_segment(source, node)
        except Exception:
            text = ""
        if text:
            lines.append((node.lineno, " ".join(text.split())[:110]))
    seen, out = set(), []
    for lineno, text in sorted(lines):
        if text not in seen:
            seen.add(text)
            out.append((lineno, text))
    return out


def is_size(value):
    """An all-integer support sets how big the problem is, not what is compared.

    A predicate about values cannot be welded by a constant that only decides how
    many lands, goods or ages there are. On this corpus the split is exact: every
    dimension constant is all-integer (`LANDS`, `GOODS`, `AGES`, `N_NONBASIC`)
    and every value constant carries a float (`YIELD`, `EFFICIENCY`,
    `NB_OWN_USE`). Separating them is what turns this scan from a list of every
    synthetic station into a list short enough to read.
    """
    if isinstance(value, tuple):
        return all(isinstance(v, int) for v in value)
    return isinstance(value, int)


def at_a_boundary(value):
    """A float support with an endpoint sitting on or just past 0 or 1.

    This is the shape `NB_OWN_USE = (0.0, 0.10)` has and the reason it welded
    `B96-2`: the endpoint is where the predicate's boundary is. It is a smell and
    not a verdict, so it is printed as a mark next to the support rather than
    used to filter anything out.
    """
    if not isinstance(value, tuple) or len(value) != 2:
        return False
    lo, hi = float(value[0]), float(value[1])
    return any(abs(x - b) < 0.1001 for x in (lo, hi) for b in (0.0, 1.0))


def scan_one(path):
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    constants = numeric_constants(tree)
    supports = draw_supports(source, constants)
    values = sorted(s for s in supports if not is_size(constants[s]))
    sizes = sorted(s for s in supports if is_size(constants[s]))
    if not values:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(node.name.lower().startswith(p) for p in CRIT):
            continue
        cmps = comparisons(node, source)
        if cmps:
            marked = [(v + ("  <- endpoint at a boundary"
                            if at_a_boundary(constants[v]) else ""),
                       constants[v]) for v in values]
            out.append((node.name, marked, sizes, cmps))
    return sorted(out)


def scan(root):
    scripts = sorted(p for p in (root / "experiments").glob("*.py")
                     if ".expired" not in p.name)
    hits = []
    for path in scripts:
        for name, values, sizes, cmps in scan_one(path):
            hits.append((path.name, name, values, sizes, cmps))
    return len(scripts), hits


def report(root, verbose):
    total, hits = scan(root)
    files = sorted(set(h[0] for h in hits))
    print(str(total) + " station scripts, " + str(len(files))
          + " whose criteria compare quantities drawn from a bounded value "
          + "support, " + str(len(hits)) + " criteria to read")
    for name in files:
        rows = [h for h in hits if h[0] == name]
        print("\n  " + name)
        for label, value in rows[0][2]:
            print("    value support   " + label + " = " + repr(value))
        if rows[0][3]:
            print("    dimension only  " + ", ".join(rows[0][3])
                  + "   (cannot weld a predicate about values)")
        for _, crit, _, _, cmps in rows:
            print("    " + crit)
            for lineno, text in (cmps if verbose else cmps[:3]):
                print("        L" + str(lineno) + "  " + text)
            if not verbose and len(cmps) > 3:
                print("        ... " + str(len(cmps) - 3) + " more, use --verbose")
    return 0


WELDED = "\n".join([
    "import numpy as np",
    "OWN_USE = (0.0, 0.10)",
    "CORE = (0.5, 0.9)",
    "def draws(rng, n):",
    "    return [{'own': float(rng.uniform(*OWN_USE)),",
    "             'core': float(rng.uniform(*CORE))} for _ in range(n)]",
    "def crit_under(sample):",
    "    under = all(s['own'] < s['core'] for s in sample)",
    "    return under, str(len(sample)) + ' draws'",
    "",
])

CLEAN = "\n".join([
    "import numpy as np",
    "def crit_count(sample):",
    "    return len(sample) > 0, 'nothing is drawn here, the rows come off the disk'",
    "",
])

SIZE_ONLY = "\n".join([
    "import numpy as np",
    "LANDS = (2, 7)",
    "def draws(rng, n):",
    "    return [{'k': int(rng.integers(*LANDS)), 'v': float(rng.random())}",
    "            for _ in range(n)]",
    "def crit_k(sample):",
    "    return all(s['k'] < s['v'] + 9 for s in sample), 'a line'",
    "",
])

THRESHOLD = "\n".join([
    "import numpy as np",
    "B = (0.0, 1.0)",
    "def draws(rng, n):",
    "    return [rng.uniform(*B) for _ in range(n)]",
    "def crit_t(s):",
    "    return max(s) < 0.99, 'a line'",
    "",
])


def selftest():
    import tempfile
    ok = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "experiments").mkdir()
        (root / "experiments" / "welded_seed.py").write_text(WELDED, encoding="utf-8")
        (root / "experiments" / "clean_seed.py").write_text(CLEAN, encoding="utf-8")
        _, hits = scan(root)
        names = set(h[0] for h in hits)
        ok.append(("the welded arm is reported", "welded_seed.py" in names))
        ok.append(("the arm with no generator is not", "clean_seed.py" not in names))
        welded = [h for h in hits if h[0] == "welded_seed.py"]
        named = [lab.split("  ")[0] for lab, _ in welded[0][2]] if welded else []
        ok.append(("its support is named", named == ["CORE", "OWN_USE"]))
        ok.append(("its comparison is quoted",
                   bool(welded) and any("own" in text and "core" in text
                                        for _, text in welded[0][4])))
        ok.append(("the endpoint at a boundary is marked",
                   bool(welded) and any("boundary" in lab
                                        for lab, _ in welded[0][2])))
        (root / "experiments" / "size_seed.py").write_text(
            SIZE_ONLY, encoding="utf-8")
        _, hits3 = scan(root)
        ok.append(("a dimension-only support is not reported",
                   "size_seed.py" not in set(h[0] for h in hits3)))
        (root / "experiments" / "threshold_seed.py").write_text(
            THRESHOLD, encoding="utf-8")
        _, hits2 = scan(root)
        ok.append(("a threshold is not reported",
                   "threshold_seed.py" not in set(h[0] for h in hits2)))
    for label, passed in ok:
        print("  " + ("ok  " if passed else "FAIL") + "  " + label)
    return 0 if all(p for _, p in ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return report(ROOT, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
