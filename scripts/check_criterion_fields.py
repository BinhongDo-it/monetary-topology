#!/usr/bin/env python3
"""Two things about the shape of a criterion object, neither of them watched.

One, the gate, and it is aimed at the census rather than at the records. A
criterion can say it was not evaluated in two independent places: a field on
itself and the wording of its own `detail`. The census reads the prose by word
list and the fields by name list, and a name list is a closed set that the next
station can step outside of without anything saying so. This gate names a field
whose name states that same thing, carried truthily by a criterion that says it
nowhere the census can read. That is one finding per spelling the census has
gone blind to, and it found the first three the day it was written: `void` was
not on the list, 461 criteria carry it, and three of them were being counted as
readings that came out false, one being the criterion the rules file holds void
by name.

Companion fields are not findings. `why_void`, `withdrawn_reason` and
`withdrawn_form` carry the reason for a flag that is itself read, so the
criterion is already excluded and the spelling costs nothing.

Two, the census, reported and not gated. `undecidable` is a bool in seven
criteria and an integer in one. `withdrawn` is a reason string in three and a
bool in one. Every consumer tests these for truthiness, so both spellings work
and nothing has ever hit it. That is the shape of the rule about a field with
two types whose only consumer asks whether it is true, and it has now bitten
twice under two different names, so this counts the whole schema rather than
waiting for the third.

Top-level record keys are deliberately not gated. A station names its own
fields, so `rows` holding an integer in one station and a list in another is two
stations using the same English word, not a defect: eighty top-level keys carry
more than one type and the ones checked are all that. The schema shared across
stations is the criterion object, and there the count is five.

`grid_split` is a third depth and is counted in scripts/fail_census.py. That
field is always a dict, and it is the values inside it that carry two types.

    python scripts/check_criterion_fields.py
    python scripts/check_criterion_fields.py --root ../topology-fingerprints
    python scripts/check_criterion_fields.py --selftest
"""
import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from fail_census import VOID, VOID_FIELDS as NOT_DECIDED
    VOID_FROM = "fail_census, which is the list the census actually reads"
except Exception:                          # pragma: no cover
    VOID = re.compile(r"void|not evaluated|does not run|no object|nothing to "
                      r"pair|not adjudicable|not run|not tested|not reproduced",
                      re.I)
    NOT_DECIDED = ("void", "undecidable", "withdrawn")
    VOID_FROM = "a local copy, because fail_census would not import"
SMELL = re.compile(r"void|undecid|withdraw|not_(run|scored|evaluated|judged)", re.I)


def tname(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


def candidates(root):
    """Worktree under results, minus git-ignored, minus .expired.

    The same scope the other record scanners use. A plain rglob is what pulled
    in a directory of shadow copies once, and a listdir of the top level is what
    missed a subdirectory of real ones.
    """
    root = pathlib.Path(root).resolve()
    res = root / "results"
    if not res.is_dir():
        return []
    files = [p for p in res.rglob("*.json") if ".expired" not in p.name]
    rel = [str(p.relative_to(root)) for p in files]
    try:
        out = subprocess.run(["git", "-C", str(root), "check-ignore", "-z", "--stdin"],
                             input="\0".join(rel), capture_output=True, text=True)
        ign = {x for x in out.stdout.split("\0") if x}
    except Exception:
        ign = set()
    return [p for p, r in zip(files, rel) if r not in ign]


def criteria_of(path):
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(doc, dict):
        return []
    cs = doc.get("criteria")
    if not isinstance(cs, list):
        return []
    return [c for c in cs if isinstance(c, dict)]


def scan(files):
    findings, types, flagged = [], collections.defaultdict(collections.Counter), []
    smelly = collections.defaultdict(list)
    for p in files:
        for c in criteria_of(p):
            for k, v in c.items():
                types[k][tname(v)] += 1
            says = [k for k in NOT_DECIDED
                    if k in c and c[k] not in (None, False, "", 0)]
            det = str(c.get("detail", ""))
            readable = bool(says) or bool(VOID.search(det))
            for k, v in c.items():
                if not SMELL.search(k) or k in NOT_DECIDED:
                    continue
                if v in (None, False, "", 0):
                    continue
                smelly[k].append((p.name, str(c.get("name", ""))[:44], readable))
                if not readable:
                    findings.append((p.name, str(c.get("name", ""))[:70], [k]))
            if says:
                flagged.append((p.name, str(c.get("name", ""))[:44], c.get("passed"),
                                says, bool(VOID.search(det))))
    return findings, types, flagged, smelly


def selftest():
    seeded = {"criteria": [
        # the finding: a spelling the census does not read, on a criterion that
        # says it nowhere the census can read
        {"name": "a spelling the census has gone blind to", "passed": False,
         "not_judged": True, "detail": "the two arms disagree on the sign"},
        # not a finding: a companion field beside a flag that is read
        {"name": "a reason beside a flag that is read", "passed": False,
         "void": True, "why_void": "the threshold was never registered",
         "detail": "unstable"},
        # not a finding: the prose says it, so the census already has it
        {"name": "an odd spelling with the word in the prose", "passed": False,
         "withdrawn_form": {"kind": "grid"},
         "detail": "Void: no base returned a verdict"},
        # not findings, and flagged as excluded by a field the census reads
        {"name": "undecided verdict", "passed": None, "undecidable": True,
         "detail": "below the floor"},
        {"name": "a pass carrying a count", "passed": True, "undecidable": 17,
         "detail": "seventeen loops could not be closed"},
        {"name": "ordinary", "passed": True, "detail": "clears"},
    ]}
    with tempfile.TemporaryDirectory() as d:
        res = pathlib.Path(d) / "results"
        res.mkdir()
        (res / "seeded.json").write_text(json.dumps(seeded), encoding="utf-8")
        findings, types, flagged, smelly = scan([res / "seeded.json"])
    ok = True
    if len(findings) != 1 or findings[0][2] != ["not_judged"]:
        ok = False
        print(f"  gate: expected the one blind spelling, got {findings}")
    if sorted(smelly) != ["not_judged", "why_void", "withdrawn_form"]:
        ok = False
        print(f"  smell: expected three odd spellings seen, got {sorted(smelly)}")
    if len(flagged) != 3:
        ok = False
        print(f"  flagged: expected 3 excluded by a field the census reads, "
              f"got {len(flagged)}")
    multi = sorted(k for k, v in types.items()
                   if len([x for x in v if x != "null"]) > 1)
    if multi != ["undecidable"]:
        ok = False
        print(f"  census: expected undecidable to be the one multi-typed key, got {multi}")
    if "void" not in NOT_DECIDED:
        ok = False
        print("  the field list does not contain the field that cost three criteria")
    if not VOID.search("Void: no base returned a verdict"):
        ok = False
        print("  the void word list does not match its own example")
    print("selftest " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    root = argv[argv.index("--root") + 1] if "--root" in argv else str(HERE.parent)
    files = candidates(root)
    findings, types, flagged, smelly = scan(files)

    print(f"scanning {pathlib.Path(root).resolve().name}")
    print(f"  {len(files)} record files")
    print(f"  fields the census reads as not-evaluated: {', '.join(NOT_DECIDED)}")
    print(f"  word list from {VOID_FROM}\n")

    print(f"{len(flagged)} criteria are excluded by one of those fields:")
    tally = collections.Counter()
    for fn, nm, passed, says, voidword in flagged:
        tally[("+".join(says), str(passed), voidword)] += 1
    for (says, passed, voidword) in sorted(tally):
        also = "prose says it too" if voidword else "prose does not say it"
        print(f"  {tally[(says, passed, voidword)]:4d}  {says:12s} passed={passed:5s}  {also}")

    if smelly:
        print(f"\n{len(smelly)} other field name(s) state the same thing:")
        for k in sorted(smelly):
            seen = smelly[k]
            blind = [s for s in seen if not s[2]]
            print(f"  {k:20s} on {len(seen)} criteria, "
                  f"{len(blind)} of them readable nowhere else")

    multi = {k: v for k, v in types.items()
             if len([t for t in v if t != "null"]) > 1}
    print(f"\n{len(types)} distinct criterion keys, {len(multi)} carry more than "
          f"one non-null type:")
    for k, v in sorted(multi.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {k:20s} " + "  ".join(f"{x}:{n}" for x, n in v.most_common()))

    if findings:
        print(f"\n{len(findings)} criterion(s) say on a field that they were not "
              f"evaluated, in a spelling the census does not read, and say it "
              f"nowhere the census does read. Each is counted as a reading that "
              f"came out false:")
        for fn, nm, says in findings:
            print(f"  {fn:46s} [{'+'.join(says)}] {nm}")
        print("  add the field to VOID_FIELDS in scripts/fail_census.py, or "
              "write the word into the detail")
        return 1
    print(f"\n0 criterion is excluded by a spelling the census cannot read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
