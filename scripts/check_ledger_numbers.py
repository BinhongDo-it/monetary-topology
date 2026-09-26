"""The ledger's census section must not quote a count that is still growing.

A count of a growing set goes stale the moment the set grows, and nothing reports
it. This guard used to check those counts against a fresh run, and on 2026-09-15
it reported them stale twice in one day: once because the session writing the
ledger added criteria, and once because a second session added records while the
first was typing. The second one is the point. A figure that two sessions can
falsify between them has no correct moment, only a correct run, so the section
stopped quoting them and this stopped checking them.

What is checked now is the other direction: that they have not been written back
in. The shapes below are the ones that were there, and each is a finding if it
reappears. The section names the script instead, and the script lands its own
record.

One figure is still quoted and still checked, because it is the one that speaks
to a theory rather than to tooling, and because it has not moved: the `rival`
count. It is read out of the prose and compared against a fresh census run.

Usage::

    python scripts/check_ledger_numbers.py
    python scripts/check_ledger_numbers.py --selftest
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "RESULTS.md"
CENSUS = ROOT / "scripts" / "fail_census.py"
HEADING = "## FAIL census"

#: The one figure still quoted in the prose, and how to find it in each place.
RIVAL = (r"`rival` is (\w+)", r"the figure to quote is rival: (\d+)")

#: Words for small integers, because the prose writes the number out.
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

#: Shapes that used to be quoted in the census section and must not come back.
#: Each is a count of a set that grows, so re-typing one re-creates the failure
#: this guard was written for.
FORBIDDEN = [
    ("objects with passed = false", r"^\s*\d+\s+objects with passed = false"),
    ("criteria, of which", r"^\s*\d+\s+criteria, of which"),
    ("not inside a criteria array", r"^\s*\d+\s+not inside a criteria array"),
    ("say they were not evaluated", r"^\s*\d+\s+say (in their own detail|they were not)"),
    ("are readings that came out false", r"^\s*\d+\s+are readings that came out false"),
    ("Those N, by what the criterion asks", r"\*\*Those \d+, by what the criterion asks"),
    ("a kind with a count beside it", r"^\| (own_reading|instrument|bookkeeping|known_answer|premise) \| \d+ \|"),
]


def script_figures():
    out = subprocess.run([sys.executable, str(CENSUS)], capture_output=True,
                         text=True, cwd=str(ROOT)).stdout
    got = {}
    for key, _, pat in FIELDS:
        if pat:
            m = re.search(pat, out)
            if m:
                got[key] = m.group(1)
    got["those N"] = got.get("false readings")
    for k, v in re.findall(r"^\s+(\w+)\s+(\d+)\s*$", out, re.M):
        if k in KINDS:
            got[k] = v
    return got


def ledger_figures(text):
    if HEADING not in text:
        return None
    sec = text[text.index(HEADING):]
    got = {}
    for key, pat, _ in FIELDS:
        m = re.search(pat, sec, re.M)
        if m:
            got[key] = m.group(1)
    for k in KINDS:
        m = re.search(r"\|\s*\*?\*?" + k + r"\*?\*?\s*\|\s*\*?\*?(\d+)\*?\*?\s*\|", sec)
        if m:
            got[k] = m.group(1)
    return got


def compare(doc, now):
    stale, missing = [], []
    for key in [f[0] for f in FIELDS] + list(KINDS):
        d, n = doc.get(key), now.get(key)
        if d is None:
            missing.append(key)
        elif n is not None and d != n:
            stale.append((key, d, n))
    return stale, missing


def internal(doc):
    """Figures the ledger states twice, checked against each other.

    One count appears both in the block and in the sentence introducing the kind
    table, and the kind counts should sum to it. Neither needs the records to
    check: a document can disagree with itself, and correcting one occurrence and
    not the other is how it usually happens.
    """
    out = []
    a, b = doc.get("false readings"), doc.get("those N")
    if a is not None and b is not None and a != b:
        out.append(("false readings vs those N", a, b))
    kinds = [doc.get(k) for k in KINDS]
    if a is not None and all(v is not None for v in kinds):
        s = sum(int(v) for v in kinds)
        if s != int(a):
            out.append(("sum of the kind counts vs false readings", str(s), a))
    return out


def selftest():
    text = LEDGER.read_text(encoding="utf-8")
    now = script_figures()
    doc = ledger_figures(text)
    clean, _ = compare(doc, now)
    clean_internal = internal(doc)
    if clean_internal:
        for key, a, b in clean_internal:
            print(f"  live ledger disagrees with itself: {key}: {a} vs {b}")
    # Plant one wrong figure of each shape: one from the prose block, one from
    # the kind table. A version that read either from memory would not see them.
    # Both plantings are asserted to have taken, because "the checker did not
    # fire" and "the seed never went in" look the same in the output otherwise,
    # which is the mistake the sibling checker's first selftest made.
    seeded, n1 = re.subn(r"(\n\s*)\d+(\s+are readings that came out false)",
                         r"\g<1>999\g<2>", text, count=1)
    seeded, n2 = re.subn(r"(\|\s*own_reading\s*\|\s*)\d+(\s*\|)",
                         r"\g<1>42\g<2>", seeded, count=1)
    if not (n1 == 1 and n2 == 1):
        print(f"  seeding failed: prose {n1}, table {n2} (expected 1 and 1)")
        print("selftest FAILED")
        return 1
    bad, _ = compare(ledger_figures(seeded), now)
    keys = sorted(k for k, _, _ in bad)
    seeded_internal = internal(ledger_figures(seeded))
    ok = (not clean) and keys == ["false readings", "own_reading"] and len(seeded_internal) == 2
    print(f"  live ledger    -> {len(clean)} stale, expected 0")
    print(f"  seeded ledger  -> {keys}, plus "
          f"{len(seeded_internal)} internal disagreement(s)\n"
          f"                    expected ['false readings', 'own_reading'] and 2")
    print("selftest " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    section = census_section(LEDGER.read_text(encoding="utf-8"))
    if section is None:
        print("no census section in the ledger")
        return 0
    out = subprocess.run([sys.executable, str(CENSUS)], capture_output=True,
                         text=True).stdout
    findings = check(section, out)
    for what, detail in findings:
        print(f"  {what:24s} {detail}")
    print(f"\n{len(FORBIDDEN)} forbidden shapes checked, one figure compared, "
          f"{len(findings)} finding(s)")
    return 1 if findings else 0


def census_section(ledger):
    i = ledger.find(HEADING)
    if i < 0:
        return None
    j = ledger.find("\n## ", i + len(HEADING))
    return ledger[i:j if j > 0 else len(ledger)]


def check(section, census_out):
    """Findings: a forbidden count is back, or the one quoted figure disagrees."""
    findings = []
    for name, pattern in FORBIDDEN:
        for line in section.split("\n"):
            if re.search(pattern, line):
                findings.append(("count-is-back", f"{name}: {line.strip()[:70]}"))
                break
    m = re.search(RIVAL[0], section)
    n = re.search(RIVAL[1], census_out)
    if not m:
        findings.append(("rival-not-quoted",
                         "the section no longer states what `rival` is"))
    elif not n:
        findings.append(("census-silent", "the census printed no rival figure"))
    else:
        said = WORDS.get(m.group(1).lower())
        if said is None:
            findings.append(("rival-not-a-number",
                             f"the prose says {m.group(1)!r}"))
        elif said != int(n.group(1)):
            findings.append(("rival-stale",
                             f"ledger says {said}, counted now {n.group(1)}"))
    return findings


def selftest():
    good = ("## FAIL census\n\nsome prose. **One number is quoted... `rival` is zero.**\n"
            "| kind | what a failure there says |\n| own_reading | one reading |\n")
    bad = ("## FAIL census\n\n```\n145   objects with passed = false\n"
           " 135  criteria, of which\n  98    are readings that came out false\n```\n"
           "**Those 98, by what the criterion asks.**\n"
           "| own_reading | 66 | one reading |\n`rival` is zero\n")
    out = "the figure to quote is rival: 0"
    ok = True
    g = check(good, out)
    if g:
        ok = False
        print(f"  clean section should give 0 findings, gave {g}")
    b = {w for w, _ in check(bad, out)}
    if b != {"count-is-back"}:
        ok = False
        print(f"  a section with the old counts should report count-is-back, gave {b}")
    n_back = len(check(bad, out))
    if n_back != 5:
        ok = False
        print(f"  expected 5 forbidden shapes in the seeded section, got {n_back}")
    stale = check(good, "the figure to quote is rival: 3")
    if {w for w, _ in stale} != {"rival-stale"}:
        ok = False
        print(f"  a moved rival count should be reported, gave {stale}")
    silent = check("## FAIL census\n\nnothing about it\n", out)
    if {w for w, _ in silent} != {"rival-not-quoted"}:
        ok = False
        print(f"  a section that drops the figure should be reported, gave {silent}")
    print("selftest " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
