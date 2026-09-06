"""Push-time self-check on what the public text of this repository may contain.

Two groups of patterns, with different scopes:

  hard bans, every tier      names and relationships that have no place in a
                             public repository, and references that would be a
                             dead link for any reader who followed them
  wording table, tiers 1-2   entrance texts only, where a reader arrives with no
                             context and a word lands before it can be judged.
                             The station documents and the source are tier 3:
                             there these words are the subject matter, and
                             scanning them for an entrance criterion applies a
                             test to the wrong object

Scope is the working tree minus everything .gitignore blocks minus .expired
snapshots. **It is not `git ls-files`**: an untracked file is not a file that
stays out of the repository, it is a file nobody has added yet, and that
distinction has cost this project once already.

Two exit conditions:

  FAIL    a hard ban matched. Non-zero exit, do not push.
  REVIEW  something that needs a human. Printed, exit stays zero.

Run:

    python scripts/check_disclosure.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".md", ".py", ".txt", ".json", ".yml", ".yaml", ".cfg", ".toml", ".ps1"}

# Every pattern below is written with an escape in it, so that this file does not
# match its own scan. A checker that trips on itself teaches the next reader to
# ignore it, which is the failure mode the pit ledger calls a guard that shouts.
HARD = {
    "assistant name": "(?i)clau\u0064e",
    "internal term for the registration": "\u7b97\u672f\u5355",
    "honorifics": "\u965b\u4e0b|\u81e3\u59be|Majest\u0079",
    "operator as third party": r"\bthe use\u0072\b",
}

# These need a human, and neither is decidable from the word alone.
#
# The self-reference pattern is a REVIEW and not a hard ban because the same two
# words can name the person who wrote a cited work. This repository does not use
# them that way: it names the person, as in "Kennickell's own conclusion", and it
# speaks in the first person about its own decisions. So a match here is almost
# always the second case, and the fix is to name whoever is meant.
#
# Money words are the harder case and the reason they are not a hard ban: the
# rule they come from says in as many words that the test is whose money the
# sentence is about, not the shape of the word. This corpus is about currency
# reforms, so a per-person exchange allowance is the object of study and appears
# on almost every page of one station file.
REVIEW_ALL = {
    "third-person self-reference": r"\bthe autho\u0072\b",
    "money words, decide by whose money": ("set aside is \\$|budget of \\$"
                                           "|\u9884\u7b97|\u989d\u5ea6"),
}

# Entrance texts only.
TIER12 = {
    "retraction wording": r"retracted|retraction",
    "performed honesty": r"rather than buried|in its own words",
    "idle-station wording": r"went wrong|nothing has been judged",
}

TIER12_FILES = {"README.md", "RESULTS.md"}
TIER12_PREFIX = ("speedrun/",)
# No self-exemption: the patterns are built from escapes so that this file does
# not match its own scan, which is what an exemption would otherwise be hiding.
EXEMPT = {"docs/MEASUREMENT.md", "docs/b8_pitfalls.md"}


def in_scope():
    cand = [p for p in ROOT.rglob("*")
            if p.is_file() and p.suffix in TEXT and ".expired" not in p.name]
    rel = [str(p.relative_to(ROOT)).replace("\\", "/") for p in cand]
    if not rel:
        return []
    res = subprocess.run(["git", "check-ignore", "-z", "--stdin"],
                         input="\0".join(rel).encode(), capture_output=True,
                         cwd=str(ROOT))
    blocked = set(res.stdout.decode("utf-8", "replace").split("\0")) - {""}
    blocked = {b.replace("\\", "/") for b in blocked}
    return [r for r in rel if r not in blocked]


def is_tier12(rel):
    return rel in TIER12_FILES or rel.startswith(TIER12_PREFIX)


def known_answer():
    """The checker must fire on a planted string, or it is not a checker.

    Built from escapes for the same reason the patterns are.
    """
    planted = ("\u965b\u4e0b " + "clau\u0064e " + "the use\u0072 "
               + "\u7b97\u672f\u5355")
    missed = [k for k, pat in HARD.items() if not re.search(pat, planted)]
    if missed:
        print("KNOWN-ANSWER FAILED: these patterns did not fire on a planted "
              "string: %s" % ", ".join(missed))
        return False
    clean = "an ordinary sentence about prices and positions"
    noisy = [k for k, pat in HARD.items() if re.search(pat, clean)]
    if noisy:
        print("KNOWN-ANSWER FAILED: these fired on clean text: %s"
              % ", ".join(noisy))
        return False
    print("known answer: all %d hard patterns fire on a planted string and none "
          "fires on clean text" % len(HARD))
    return True


def main():
    if not known_answer():
        return 2
    files = in_scope()
    print("=" * 74)
    print("disclosure self-check: %d files in scope" % len(files))
    print("=" * 74)
    fails, reviews = [], []
    for rel in files:
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if rel in EXEMPT:
            continue
        for label, pat in HARD.items():
            n = len(re.findall(pat, text))
            if n:
                fails.append((rel, label, n))
        for label, pat in REVIEW_ALL.items():
            n = len(re.findall(pat, text))
            if n:
                reviews.append((rel, label, n))
        if is_tier12(rel):
            for label, pat in TIER12.items():
                n = len(re.findall(pat, text))
                if n:
                    fails.append((rel, "tier 1-2: " + label, n))

    if fails:
        print("\nFAIL")
        for rel, label, n in fails:
            print("  %-46s %-34s %d" % (rel, label, n))
    else:
        print("\nFAIL      none")

    if reviews:
        print("\nREVIEW    decide by hand, see the note above REVIEW_ALL")
        for rel, label, n in reviews:
            print("  %-46s %-34s %d" % (rel, label, n))
    else:
        print("REVIEW    none")

    print("\ntier 1-2 files scanned for the wording table: %s"
          % ", ".join(sorted(f for f in files if is_tier12(f))))
    print("everything else is tier 3, where those words are the subject matter, "
          "and is not scanned for them.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
