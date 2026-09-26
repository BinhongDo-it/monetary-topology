"""Count the FAILs by what the criterion was asking, per discipline 11d.

A FAIL is not a number. Most criteria in a station's table ask about this run's
tooling and its inputs rather than about a theory, and adding their failures to
"the rival said something true once" produces a figure with no referent. This
walks every record, sorts each failing criterion into one of the six kinds, and
reports the counts apart. The figure to quote is the ``rival`` one.

Two things this script exists to get right, both of which cost a real error the
day it was written.

**Scope.** The records live under ``results/`` in subdirectories as well as at
the top level, and one of those subdirectories is a baseline snapshot of 283
older copies of the records above it. A plain ``rglob`` counts every one of those
twice and nothing reports it: the copies are valid JSON with the same structure
and the same criterion names, so they parse and sort and count exactly like the
originals. The scope here is the one the push check uses, worktree minus what git
ignores minus ``.expired``.

**Void is not failure.** A criterion whose detail says it was not evaluated is
not a reading that came out false. The screen is a word list, and it looks
anywhere in the detail rather than only at the front: the two sharpest cases in
this repository, a pair of complementary criteria where the one that holds was
banked and the other recorded as a failure, put their reading first and the word
``Void`` after it.

Records written before ``kind`` existed do not carry one and are not rewritten.
The table below assigns a kind by station and criterion name, and every
assignment is a sentence about what that criterion asks, checkable by opening
the record. Anything the table does not cover is reported as uncovered rather
than silently dropped.

Usage::

    python scripts/fail_census.py
    python scripts/fail_census.py --list rival
    python scripts/fail_census.py --write     # also lands results/fail_census.json
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

KINDS = ("instrument", "premise", "known_answer", "rival", "own_reading", "bookkeeping")

#: Fields on a criterion that state it was not evaluated, whatever the prose
#: says. Truthy means it says so; `false` and absent both mean it does not.
VOID_FIELDS = ("void", "undecidable", "withdrawn")

#: A detail that says the criterion was not evaluated. Searched anywhere in the
#: text, not only at its start.
#:
#: The prose is the fallback, not the primary place. A criterion can also say it
#: on a field, and 461 of them do. Reading only the prose let three criteria
#: that carry `void: true` be counted as readings that came out false, one of
#: them the criterion the rules file itself names as held void. Both places are
#: read now, and a criterion counts as not evaluated when either says so.
VOID = re.compile(r"\b(void|not evaluated|does not run|no object|nothing to pair"
                  r"|not adjudicable|not run|not reproduced|not tested)\b", re.I)

#: (file pattern, criterion-name pattern, kind, what that criterion asks).
#: First match wins, so put the exceptions above the station-wide rules.
RULES = [
    (r"^a12_", r"A12-5", "premise",
     "no transfer arm ran on this carrier, so the pairing it scores has no object"),
    (r"^a1_default_cascade", r"A1-10", "premise",
     "the main arm has no population at the size the licence names"),
    (r"^a7_verdicts", r"A7-B-5", "premise",
     "two mechanisms are recorded as not run, so their effects have nothing to be read from"),
    (r"^a26_greedy", r"A26-20", "bookkeeping",
     "recorded a failure because the outcome map was short a cell, not because the run was"),
    (r"^b21_cross_section", r"B21-6", "known_answer",
     "a placebo: events with a known answer, run to see whether the instrument returns it"),
    (r"^b2_placebo_pool_width", r"PW-7", "instrument",
     "whether the minimum-size threshold carries the verdict, which is a robustness check "
     "on the tool and not a reading"),
    (r"^b31_second_measure", r"B31-7e", "instrument",
     "sweeps a quantity that would have to be bought over its admissible range, to price "
     "the purchase before making it"),
    (r"^b11_", r".", "instrument",
     "coverage of the source files: how many marked obligors survive to a priceable "
     "instrument, and whether the files carry contract terms at all"),
    (r"^b14_gate0", r".", "instrument",
     "a convention sensitivity on the same arithmetic, or a reproduction check against "
     "another cache"),
    (r"^b14_t1_order_type", r".", "instrument",
     "the margin recomputed on one order type at a time, a decomposition of the input"),
    (r"^b21_liquidity", r"B21-9", "instrument",
     "whether four estimators of one quantity agree on an ordering, which is a statement "
     "about the estimators"),
    (r"^b15_calibration", r"B15-11", "instrument",
     "how far apart two publishers of the same series sit, and the noise floor that implies"),
    (r"^b6_segments", r"B6-4", "instrument",
     "the implied cross checked against an outside reference rate, a calibration"),
    (r"^a6_ratchet\.offparam", r".", "bookkeeping",
     "an off-parameter record whose detail is empty, so nothing was written to read"),
    (r"^b15_structure", r"^$", "bookkeeping",
     "a reading dictionary rather than a criterion: no name and no detail"),
    (r".", r".", "own_reading", "a reading this station registered"),
]


#: This script's own record, which lands in the directory it counts. Left in the
#: scope it would make the file count grow by one every time the script is run,
#: which is the same shape as a link checker that flags its own fixture: a tool
#: has to be outside what it measures. The push check solves it by living outside
#: both repositories; here one filename is enough.
SELF_RECORD = "fail_census.json"


def candidates():
    files = sorted(f for f in RESULTS.rglob("*.json")
                   if ".expired" not in str(f) and f.name != SELF_RECORD)
    rel = [os.path.relpath(str(f), str(ROOT)) for f in files]
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-z", "--stdin"],
                             input=("\0".join(rel) + "\0").encode(), capture_output=True)
        ignored = {s for s in out.stdout.decode().split("\0") if s}
    except Exception:
        ignored = set()
    return [f for f, r in zip(files, rel) if r not in ignored]


def failures(f):
    out = []

    def walk(o, path):
        if isinstance(o, dict):
            if o.get("passed") is False:
                said = [k for k in VOID_FIELDS
                        if o.get(k) not in (None, False, "", 0)]
                out.append({"path": path, "in_criteria": "criteria" in path,
                            "name": str(o.get("name") or o.get("criterion") or ""),
                            "kind": o.get("kind"),
                            "void_field": said,
                            "detail": str(o.get("detail") or "")})
            for k, v in o.items():
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    try:
        walk(json.loads(f.read_text(encoding="utf-8")), "")
    except Exception as e:
        print(f"  unreadable: {f}: {e}")
    return out


def verdict_census(files):
    """Every top-level criterion by what its `passed` field actually is.

    This script was written to count failures, so it only ever looked at
    `passed is False`. Two states are then invisible to it, and both exist on
    disk. `passed: null` is how the undecided cell of a three-way criterion is
    written, which `11c` requires to exist and forbids from being mapped onto a
    verdict; and a criterion can carry no `passed` field at all. Neither is a
    pass and neither is a failure, so a summary that reports only the first two
    quietly drops them, and a dropped count is the shape this repository keeps
    paying for.

    Only the top-level `criteria` array is walked. A verdict nested somewhere
    else is not a criterion, which is the same line the failure census draws.
    """
    counts = collections.Counter()
    undecided, missing = [], []
    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        crits = criteria_of(doc)
        if not crits:
            continue
        for c in crits:
            if "passed" not in c:
                counts["absent"] += 1
                missing.append((f.name, str(c.get("name", ""))[:70], c.get("kind")))
            elif c["passed"] is None:
                counts["undecided"] += 1
                undecided.append((f.name, str(c.get("name", ""))[:70], c.get("kind")))
            elif c["passed"] is True:
                counts["pass"] += 1
            elif c["passed"] is False:
                counts["fail"] += 1
            else:
                counts["other"] += 1
    return counts, undecided, missing


def split_census(files):
    """What sits in `grid_split`, by type, for every rival criterion.

    `check_rival_grid.py` makes a rival criterion on grid `mixed` carry a
    `grid_split` dict and checks its keys against the four cell letters. It
    never looks at the values, and its own fixture puts counts there. Two kinds
    of value are on the ledger. One is a count. The other is a sentence saying
    why that cell is *not* claimed, and that one inverts the field: a key
    present reads as that cell being occupied, and the sentence under it says
    the opposite. Nothing reports the difference, which is the shape of the rule
    about a field with two types whose only consumer tests it for truthiness.

    Grid C is the one cell on the four-cell table that counts against this
    framework, and the ledger reports it as empty. So a stray C key is the only
    thing that could make a reader conclude otherwise, and every C key on the
    ledger today is either void or a sentence denying the cell.
    """
    kinds = collections.Counter()
    prose, cells = [], collections.Counter()
    rival = 0
    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        crits = criteria_of(doc)
        for c in crits:
            if c.get("kind") != "rival":
                continue
            rival += 1
            split = c.get("grid_split")
            if not isinstance(split, dict):
                kinds["no split" if split is None else "not a dict"] += 1
                continue
            for cell, val in sorted(split.items()):
                cells[cell] += 1
                if isinstance(val, bool) or not isinstance(val, int):
                    kinds["prose"] += 1
                    prose.append((f.name, str(c.get("name", ""))[:44], cell,
                                  str(val), c.get("passed")))
                else:
                    kinds["count"] += 1
    return rival, kinds, cells, prose


def duplicate_names(files):
    """Record file names that occur more than once under the scanned tree.

    `results/subset/` holds smaller runs of stations that also have a top-level
    record, and it is not git-ignored, so both copies are in scope. That is
    correct as a count of records and wrong as a count of stations, and the two
    are easy to read as one. The scope is printed rather than silently deduped:
    a count that quietly drops rows is what the rule about scope was written
    against, and so is one that quietly doubles them.
    """
    by = collections.defaultdict(list)
    for f in files:
        by[f.name].append(os.path.relpath(str(f), str(ROOT)))
    return {k: v for k, v in sorted(by.items()) if len(v) > 1}


def assign(fname, name):
    for fp, np_, kind, why in RULES:
        if re.search(fp, fname) and (re.search(np_, name) if np_ != r"^$" else name == ""):
            return kind, why
    return None, None


def criteria_of(doc):
    """A record's top-level criteria, whichever shape they were written in.

    Most stations write a list.  Eight write a dict keyed by criterion name,
    and this census read only the list shape, so those eight were skipped
    whole: 41 criteria, of which 4 are `rival`, 5 read false and 2 are
    undecided.  The figure discipline 11d says to quote was therefore being
    computed without four of the rival criteria on disk.

    Found 2026-09-16.  It is the same shape a fifth time: a tool that picks
    its objects by one spelling and reports a clean count of the rest.  The
    earlier four are in the rules file under discipline 24.
    """
    crits = doc.get("criteria")
    if isinstance(crits, list):
        return [c for c in crits if isinstance(c, dict)]
    if isinstance(crits, dict):
        out = []
        for name, c in crits.items():
            if not isinstance(c, dict):
                continue
            #: the dict shape puts the key where the list shape puts `name`,
            #: and some of those records use `name` for the criterion's text.
            out.append(dict(c, name=c.get("name") or name, _key=name))
        return out
    return []


def selftest() -> int:
    """Plant a record in each criteria shape and require both to be read.

    Discipline 11f.  The failure this grows is the one that was live until
    2026-09-16: a record whose criteria are a dict read as no criteria at all.
    """
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    as_list = {"criteria": [
        {"name": "X-1", "kind": "rival", "passed": False, "detail": "a reading"},
        {"name": "X-2", "kind": "own_reading", "passed": True, "detail": "b"}]}
    as_dict = {"criteria": {
        "X-1": {"kind": "rival", "passed": False, "detail": "a reading"},
        "X-2": {"kind": "own_reading", "passed": True, "detail": "b"}}}

    for label, doc in (("list shape", as_list), ("dict shape", as_dict)):
        got = criteria_of(doc)
        expect(len(got) == 2, f"{label}: both criteria read")
        expect(sum(1 for c in got if c.get("kind") == "rival") == 1,
               f"{label}: the rival one is seen")
        expect(sorted(c["name"] for c in got) == ["X-1", "X-2"],
               f"{label}: each criterion carries its name")

    #: the dict shape puts the criterion's text under `name`, and the key is
    #: the identifier.  Reading the key as the name is what lets one census
    #: line up with the other.
    named = criteria_of({"criteria": {"Y-9": {"name": "a long sentence",
                                              "kind": "instrument",
                                              "passed": True}}})
    expect(named[0]["name"] == "a long sentence" and named[0]["_key"] == "Y-9",
           "dict shape: the key travels as `_key` when `name` is the text")

    expect(criteria_of({}) == [] and criteria_of({"criteria": 7}) == [],
           "a record with no criteria, or a scalar there, reads as none")

    print("\nselftest " + ("FAILED" if fails else "passed"))
    return 1 if fails else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    want = None
    if "--list" in argv:
        want = argv[argv.index("--list") + 1]
    write = "--write" in argv

    cands = candidates()
    rows = []
    for f in cands:
        for r in failures(f):
            r["file"] = f.name
            rows.append(r)

    outside = [r for r in rows if not r["in_criteria"]]
    inside = [r for r in rows if r["in_criteria"]]
    void = [r for r in inside
            if VOID.search(r["detail"]) or r.get("void_field")]
    field_only = [r for r in void
                  if r.get("void_field") and not VOID.search(r["detail"])]
    live = [r for r in inside if r not in void]

    tagged, uncovered = collections.Counter(), []
    for r in live:
        k = r["kind"] or assign(r["file"], r["name"])[0]
        r["assigned"] = k
        if k is None:
            uncovered.append(r)
        else:
            tagged[k] += 1

    print(f"scope: worktree under results/ minus git-ignored minus .expired")
    print(f"  {len(cands)} record files")
    print(f"  {len(rows)} objects with passed=false")
    print(f"    {len(outside):4d} not inside a criteria array, so not criteria")
    print(f"    {len(inside):4d} criteria, of which")
    print(f"      {len(void):4d} say they were not evaluated, in the detail or on a field")
    if field_only:
        print(f"           of those, {len(field_only)} say it only on a field, so a "
              f"census reading the prose alone counts them as failures:")
        for r in field_only:
            print(f"           {r['file']:42s} [{'+'.join(r['void_field'])}] {r['name'][:48]}")
    print(f"      {len(live):4d} are readings that came out false")
    print(f"\nthose {len(live)}, by what the criterion asks (discipline 11d):")
    for k in KINDS:
        print(f"  {k:14s} {tagged[k]:4d}")
    if uncovered:
        print(f"\n  UNCOVERED by the table: {len(uncovered)}")
        for r in uncovered[:20]:
            print(f"    {r['file']:44s} {r['name'][:60]}")
    print(f"\nthe figure to quote is rival: {tagged['rival']}")

    counts, undecided, missing = verdict_census(cands)
    total = sum(counts.values())
    print(f"\nevery top-level criterion by what its passed field is, {total} in all:")
    for key in ("pass", "fail", "undecided", "absent", "other"):
        if counts[key]:
            print(f"  {key:10s} {counts[key]:5d}")
    print(f"  **pass plus fail is {counts['pass'] + counts['fail']} of {total}.** "
          f"The rest are the undecided cell `11c` requires to exist and the ones "
          f"carrying no verdict field at all; neither is a pass and neither is a "
          f"failure, and until this line existed neither was counted anywhere.")
    if missing:
        print(f"\n  carrying no passed field, {len(missing)}, named:")
        for fn, nm, k in missing:
            print(f"    {fn:44s} [{k}] {nm}")
    if undecided:
        seen = collections.Counter(fn for fn, _, _ in undecided)
        print(f"\n  undecided, {len(undecided)} across {len(seen)} records, "
              f"most in one record {max(seen.values())}")

    rival_n, split_kinds, split_cells, prose = split_census(cands)
    print(f"\nrival criteria on the ledger: {rival_n}. What their `grid_split` holds:")
    for key in ("count", "prose", "no split", "not a dict"):
        if split_kinds[key]:
            print(f"  {key:12s} {split_kinds[key]:4d}")
    if split_cells:
        print("  cells named at all: " +
              ", ".join(f"{k} {v}" for k, v in sorted(split_cells.items())))
    if prose:
        print(f"\n  {len(prose)} split entries carry a sentence where the guard's own "
              f"fixture carries a count, so a key present does not mean that cell is "
              f"occupied. Named, because a C key is the only thing that could make the "
              f"empty loss cell read as filled:")
        for fn, nm, cell, val, passed in prose:
            print(f"    [{cell}] passed={passed!s:<5s} {fn}")
            for line in textwrap.wrap(val, 88):
                print(f"          {line}")

    dups = duplicate_names(cands)
    if dups:
        print(f"\n{len(dups)} record names occur more than once under this scope, "
              f"so a count of records is not a count of stations:")
        for name, paths in dups.items():
            print(f"  {name}")
            for path in paths:
                print(f"      {path}")

    if want:
        print(f"\n--- {want} ---")
        for r in live:
            if r.get("assigned") == want:
                print(f"  {r['file']:44s} {r['name'][:70]}")

    if write:
        # The counts move whenever a station is added, so they are a record and
        # not a constant to be typed into a document. Rule 15a: do not pickle a
        # count anywhere; count it when it is wanted. A ledger line quoting these
        # carries the run date and points here.
        rec = {"stage": "FAIL-CENSUS",
               "config": {"scope": "worktree under results/ minus git-ignored minus .expired",
                          "void_words": VOID.pattern,
                          "rule_count": len(RULES)},
               "verdict_census": dict(verdict_census(cands)[0]),
               "duplicate_record_names": {k: v for k, v in duplicate_names(cands).items()},
               "rival_split_value_types": dict(split_kinds),
               "rival_criteria": rival_n,
               "input": {"void_said_only_on_a_field": len(field_only),
                         "record_files": len(cands),
                         "passed_false": len(rows),
                         "outside_criteria_array": len(outside),
                         "criteria": len(inside),
                         "self_declared_not_evaluated": len(void),
                         "readings_that_came_out_false": len(live)},
               "by_kind": {k: tagged[k] for k in KINDS},
               "uncovered": [{"file": r["file"], "name": r["name"]} for r in uncovered]}
        out = RESULTS / "fail_census.json"
        out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nwrote {out.relative_to(ROOT)}")
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
