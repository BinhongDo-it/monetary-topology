"""Guard for rule 0b: a criterion that scores a rival must say which cell it is in.

Two things go wrong on their own and neither announces itself.

One, a criterion whose kind is rival carries no grid, so the reader cannot tell
whether the framework was also right on that cell. Rule 0b says the score is each
theory against reality, not the two against each other, and without the grid the
default reading slides back to us-versus-them.

Two, a criterion sitting in grid A is recorded as a failure. Grid A is both
accounts right, which rule 0b records as us being right. A criterion that maps it
to a failure writes a win as a loss, and it only shows up on the day it fires. Two
such designs were found on 2026-09-08 by a census done for another purpose; both
had never fired, so nothing was corrupted, and nothing would have caught them.

Not retroactive. Records written before kind existed carry neither field and are
skipped, which is discipline 11d's own rule.

    python scripts/check_rival_grid.py
    python scripts/check_rival_grid.py --root ../topology-fingerprints
    python scripts/check_rival_grid.py --selftest

Both arms, because 11d and 11e are project-wide while this file's root used to be
its own repository. On 2026-09-12 the empirical arm recorded its first criterion
with kind rival, and this guard could not see it: not a miss, a scope the tool did
not have. Rule 24's first two examples are the same shape, and the dead-link check
had the identical hole fixed the same morning. So the question belongs on every
checker here: does it scan one arm or two.
"""
from __future__ import annotations
import json, os, pathlib, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arm_root(argv: list[str]) -> str:
    """``--root <dir>`` picks which arm to scan. Default is this file's own repository."""
    if "--root" in argv:
        return os.path.abspath(argv[argv.index("--root") + 1])
    return ROOT
GRIDS = {"A", "B", "C", "D", "D1", "D2", "mixed", "unread", "both_unmet"}

#: "both_unmet" is the fourth row of the score table in the rules file: both
#: sides read, and neither one's prediction held. That row is not a loss. It
#: opens a line towards a wider account than either side carries, and it is
#: marked so rather than filed under C, which is the one row that counts
#: against this framework.

#: "unread" is the grid's own third cell. The four-cell table places a reading of
#: ours beside a reading of the rival's, so when either side produced no reading
#: there is no cell to name. Writing such a criterion as "mixed" and listing the
#: cells it might have landed in puts a key where a reader counts occupancy, and
#: a sentence under it saying the cell is empty does not undo that: the C key is
#: the only thing on this ledger that could make the one losing cell read as
#: filled. So the cells are counts, the prose moves to `grid_note`, and a
#: criterion that placed nothing says so in one word.

# Nobody on the other side wrote a prediction for our cell, and demanding one
# would ask a field that does not speak with one voice to set up our target for
# us. Macro has not settled a single mathematised form of its own claims; inside
# the New Keynesian family alone a written-out version would start an argument,
# and some of what we attack nobody has tried to write out at all. We attack the
# premise, so we state the premise and derive the prediction from it. You need a
# target before you can shoot at one.
#
# What went wrong on 2026-09-08 was not a missing citation. A prediction was
# attached to a premise that does not imply it: a scalar field on positions says
# nothing about two different positions with two different obligors. The target
# was set up in the wrong place. So the fields to require are the premise and the
# derivation, and both are checkable by reading.
#
# A citation is written when there is one. It forecloses the reply that we hit a
# different camp's version, and the premise field forecloses it more widely,
# since escaping that one costs them the index set of their own object.
RIVAL_FIELDS = ("rival_premise", "rival_entailment")

# "mixed" is only legal with a split, because a criterion spanning cells must
# report the split rather than one letter (11e fourth clause).


def scan_obj(obj, path, out):
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if isinstance(kind, str):
            grid = obj.get("grid")
            nm = obj.get("name") or obj.get("criterion") or path
            if kind == "rival" and not grid:
                out.append(("no-grid", path, str(nm)[:90]))
            if kind == "rival":
                for fld in RIVAL_FIELDS:
                    if not str(obj.get(fld, "")).strip():
                        out.append((f"no-{fld[6:]}", path, str(nm)[:90]))
            if isinstance(grid, str) and grid not in GRIDS:
                out.append(("bad-grid", path, f"{nm} -> {grid}"))
            if grid == "mixed" and not isinstance(obj.get("grid_split"), dict):
                out.append(("mixed-no-split", path, str(nm)[:90]))
            split = obj.get("grid_split")
            if isinstance(split, dict):
                for g2 in split:
                    if g2 not in GRIDS - {"mixed", "unread"}:
                        out.append(("bad-split-key", path, f"{nm} -> {g2}"))
                # The split is a count per cell. A sentence here reads as that
                # cell being occupied while saying the opposite, so prose goes
                # to `grid_note` and this field carries numbers only.
                for g2, v in split.items():
                    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                        out.append(("split-not-a-count", path, f"{nm} -> {g2}"))
                if grid != "mixed":
                    out.append(("split-without-mixed", path, f"{nm} -> {grid}"))
            if grid == "unread":
                if obj.get("passed") is not None:
                    out.append(("unread-with-verdict", path, str(nm)[:90]))
            if grid == "A" and obj.get("passed") is False:
                out.append(("A-as-fail", path, str(nm)[:90]))
        for k, v in obj.items():
            scan_obj(v, f"{path}/{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_obj(v, f"{path}[{i}]", out)


def scan_file(p):
    out = []
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return out
    scan_obj(d, os.path.basename(p), out)
    return out


def selftest() -> int:
    """A checker that has not been run against a seeded failure is not a checker."""
    good = {"criteria": [{"kind": "rival", "grid": "B", "passed": True, "name": "ok",
                          "rival_premise": "p", "rival_entailment": "q"},
                         {"kind": "rival", "grid": "mixed", "passed": True,
                          "grid_split": {"A": 48, "B": 39}, "name": "spans cells",
                          "rival_premise": "p", "rival_entailment": "q"},
                         {"kind": "own_reading", "passed": False, "name": "ours failed"},
                         {"name": "old record, no kind", "passed": False}]}
    good["criteria"].append(
        {"kind": "rival", "grid": "unread", "passed": None,
         "name": "neither side produced a reading",
         "grid_note": {"B": "not claimed: no floor was readable here"},
         "rival_premise": "p", "rival_entailment": "e"})
    bad = {"criteria": [{"kind": "rival", "passed": True, "name": "no grid"},
                        {"kind": "rival", "grid": "mixed", "passed": True,
                         "grid_split": {"A": 1, "C": "not claimed, for the same reason"},
                         "name": "a sentence where a count belongs",
                         "rival_premise": "p", "rival_entailment": "e"},
                        {"kind": "rival", "grid": "B", "passed": True,
                         "grid_split": {"B": 3}, "name": "a split on one cell",
                         "rival_premise": "p", "rival_entailment": "e"},
                        {"kind": "rival", "grid": "unread", "passed": False,
                         "name": "unread carrying a verdict",
                         "rival_premise": "p", "rival_entailment": "e"},
                        {"kind": "rival", "grid": "A", "passed": False, "name": "A as fail"},
                        {"kind": "rival", "grid": "Z", "passed": True, "name": "bad grid",
                         "rival_premise": "p", "rival_entailment": "q"},
                        {"kind": "rival", "grid": "mixed", "passed": True,
                         "name": "mixed without a split"},
                        {"kind": "rival", "grid": "mixed", "passed": True,
                         "grid_split": {"A": 1, "Q": 2}, "name": "bad split key"}]}
    g, b = [], []
    scan_obj(good, "good", g)
    scan_obj(bad, "bad", b)
    kinds = sorted({x[0] for x in b})
    want = ["A-as-fail", "bad-grid", "bad-split-key", "mixed-no-split",
            "no-entailment", "no-grid", "no-premise", "split-not-a-count",
            "split-without-mixed", "unread-with-verdict"]
    ok = (not g) and kinds == want
    print(f"  clean record  -> {len(g)} finding(s), expected 0")
    print(f"  seeded record -> {kinds}\n                   expected {want}")
    print("selftest " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    # The scan walks the tree rather than listing the top level. Records live in
    # subdirectories too, forty of them on 2026-09-09, and a listdir cannot see a
    # kind written there. Directories git ignores are skipped, because one of them
    # is a baseline snapshot of 283 older copies of the records above it: a scan
    # that walks without asking git counts every one of those twice, and nothing
    # reports it. That is the same scope the push check uses, worktree minus
    # ignored minus expired.
    root = arm_root(sys.argv)
    results = os.path.join(root, "results")
    print(f"scanning {os.path.basename(root)}")
    findings, n = [], 0
    files = sorted(str(f) for f in pathlib.Path(results).rglob("*.json")
                   if ".expired" not in str(f))
    rel = [os.path.relpath(f, root) for f in files]
    keep = files
    if rel:
        try:
            out = subprocess.run(["git", "-C", root, "check-ignore", "-z", "--stdin"],
                                 input=("\0".join(rel) + "\0").encode(),
                                 capture_output=True)
            ignored = {s for s in out.stdout.decode().split("\0") if s}
            keep = [f for f, r in zip(files, rel) if r not in ignored]
        except Exception:
            keep = files
    for fn in keep:
        n += 1
        findings += scan_file(fn)
    for what, path, nm in findings:
        print(f"  {what:10s} {path}\n             {nm}")
    print(f"\n{n} records scanned, {len(findings)} finding(s)")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
