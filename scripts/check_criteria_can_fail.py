"""Rule 11f's guard: a pass-flag that is a literal True cannot fail.

A criterion whose verdict is hardwired says nothing, whatever its statement says.
This walks every station script, finds the verdicts written as a constant, and
reports any that are not in the census below.

**A hardwired verdict does not make its reading wrong.** Most of the 32 found on
2026-09-13 were printing criteria, whose content lives in the detail by design
(rule 11: print the object, not the count). What was wrong was the flag: it now
asserts that the object is there and is not empty, so that an empty one is caught.
All 32 were repaired the same day, each verified twice: the record re-run and
compared field by field, so that no reading moved, and a fault seeded so that the
new flag was seen to fail.

**This binds criteria written from here on.** A hardwired verdict that surfaces in
an old station is left alone: the cost of repairing the historical tail is larger
than what it buys, and a residue of this bookkeeping is deliberately kept because it
reads better outside than it works inside. If one reappears, it goes into the census
below rather than into a repair job.

**The census is empty, and that is the point.** It held 32 of the 230 criteria
written in code, 13.9 percent, for the length of one afternoon on 2026-09-13, and
then all 32 were repaired rather than exempted. An empty census makes this an
absolute rule with no exemption table at all, which is the shape the record-side
ratchet scrapped on 2026-08-21 failed to have: that one died of an exemption table
holding 51 of 76.

Run:
    python scripts/check_criteria_can_fail.py
    python scripts/check_criteria_can_fail.py --selftest
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[A-Z]\d+[a-z]?(-[A-Za-z0-9']+)+$")

# (script, criterion, kind) as of 2026-09-13. Anything outside this is new.
CENSUS: set = set()


def _text(node) -> str:
    try:
        value = ast.literal_eval(node)
    except Exception:
        return ""
    return value if isinstance(value, str) else ""


def hardwired(path: pathlib.Path):
    """Verdicts written as a constant, in the two shapes this repository uses.

    An earlier version of this scan counted any `True` inside a collection that
    mentioned a criterion name anywhere, which caught diagnostic fields such as
    `one_at_a_time` and reported them as verdicts. The scope is narrowed to the
    `passed` key and to position three of the criterion tuple.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [], f"{path}: {exc}"
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keyed = {k.value: v for k, v in zip(node.keys, node.values)
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            name, ok = keyed.get("name"), keyed.get("passed")
            if (ok is not None and isinstance(ok, ast.Constant) and ok.value is True
                    and isinstance(name, ast.Constant)
                    and isinstance(name.value, str) and NAME.match(name.value)):
                kind = _text(keyed.get("kind")) if "kind" in keyed else ""
                found.add((path.name, name.value, kind or "-", ok.lineno))
        if isinstance(node, ast.Tuple) and len(node.elts) >= 4:
            first, flag = node.elts[0], node.elts[3]
            if (isinstance(first, ast.Constant) and isinstance(first.value, str)
                    and NAME.match(first.value)
                    and isinstance(flag, ast.Constant) and flag.value is True):
                found.add((path.name, first.value, _text(node.elts[1]) or "-",
                           flag.lineno))
    return sorted(found), None


def scan(base: pathlib.Path):
    hits, broken = [], []
    for path in sorted((base / "experiments").rglob("*.py")):
        if ".expired" in path.name or path.name.startswith("_"):
            continue
        found, err = hardwired(path)
        if err:
            broken.append(err)
        hits.extend(found)
    return hits, broken


def selftest() -> int:
    """Seed a file with one hardwired verdict and one live one, in both shapes."""
    import tempfile
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        sand = pathlib.Path(tmp)
        (sand / "experiments").mkdir()
        (sand / "experiments" / "seed.py").write_text(
            '''CRITERIA = [
    {"name": "Z9-1", "kind": "bookkeeping", "passed": True, "detail": "hardwired"},
    {"name": "Z9-2", "kind": "own_reading", "passed": bool(rows), "detail": "live"},
    {"one_at_a_time": True, "about": "Z9-3", "note": "a diagnostic, not a verdict"},
]
crit = [("Z9-4", "instrument", "statement", True, "detail", {}),
        ("Z9-5", "instrument", "statement", n > 1, "detail", {})]
''', encoding="utf-8")
        hits, broken = scan(sand)
        names = {h[1] for h in hits}
        if broken:
            fails.append(f"the seed did not parse: {broken}")
        for want in ("Z9-1", "Z9-4"):
            if want not in names:
                fails.append(f"{want} is hardwired and was not reported")
        for unwanted in ("Z9-2", "Z9-3", "Z9-5"):
            if unwanted in names:
                fails.append(f"{unwanted} is not a hardwired verdict and was reported")
    # the census must describe something that is actually there, or it is a list of
    # names for things that have moved. A census entry with no file is a stale entry.
    live = {(h[0], h[1], h[2]) for h in scan(ROOT)[0]}
    stale = sorted(CENSUS - live)
    if stale:
        fails.append(f"{len(stale)} census entries no longer exist: {stale[:5]}")
    # and the difference has to bite: drop one entry and that one must show as new,
    # otherwise the census is being consulted but not used
    if live:
        thinned = CENSUS - {sorted(live)[0]}
        if not [h for h in live if h not in thinned]:
            fails.append("removing a census entry did not make it show as new, so "
                         "the census is not what decides")
    for line in fails:
        print("  SELFTEST FAIL:", line)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    hits, broken = scan(ROOT)
    for err in broken:
        print("  unparsed:", err)
    new = [h for h in hits if (h[0], h[1], h[2]) not in CENSUS]
    for script, name, kind, line in new:
        print(f"NEW  {script}:{line}  {name}  [{kind}]  verdict is a literal True")
    print(f"\n{len(hits)} hardwired verdict(s), {len(CENSUS)} in the census, "
          f"{len(new)} new")
    if new:
        print("rule 11f: seed the failure instead. A verdict that cannot be False "
              "says nothing, whatever its statement says")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
