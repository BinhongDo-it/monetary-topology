#!/usr/bin/env python3
"""Report references to documents that are not in this repository.

**Why this exists rather than another entry on a checklist.** The pre-push
self-check is a list of banned words, and a banned word is a property of a
string: ``in`` decides it. A dead link is a property of a string *together with
the filesystem*, and ``in`` cannot decide it at all. So the word check returns
"clean" over a tree full of dead links, every time, no matter how often it runs.
Measurement conventions, failure mode 22, has the instance: two registers moved
out of the repository on 2026-08-18 and 35 pointers to them sat on the published
branch for four days while every pre-push check passed.

**The operation that creates the defect cannot see it.** Moving a file touches
that file. The pointers to it live in other files, which the move does not
visit. So a move leaves dead links by construction and reports nothing, and the
moment the move happens is the last moment anyone knows where the file used to
be. After that only a whole-tree scan finds them, which is this script.

**Scope: documents, not runtime paths.** A ``.md`` target is something a reader
is meant to open, so failing to resolve one is a defect. A ``.json`` or ``.py``
target is usually a path a script reads or writes at run time, and those are
absent for ordinary reasons: the data is not redistributed, the output has not
been produced yet, a marker file names the file whose absence it explains. So
only documents are checked, plus bare CJK document names, which is the shape a
moved-out internal file takes.

**The CJK class is explicit and is not decoration.** A target named in Chinese
does not even look like a path to a naive pattern, so it escapes the coarse
filters that catch ``docs/...`` by prefix. That is the same shape as the
project's rule on counting Chinese with Python rather than shell grep: the tool
works on pure ASCII and fails exactly when there is something Chinese to report,
so it fails at the moment the self-check looks cleanest.

**The residual it was written to measure has been paid off.** On the first run,
2026-08-22, it reported 68 references of which **64 were real**, all of them
pointing at working documents that are not published with this repository, and
concentrated on five such documents. **All sixty-four were cleared on
2026-08-27**, and the way each was cleared is the same: the sentence already
stated the lesson, so the unfollowable file-and-section token was removed and
the lesson stayed. **A reference to a document a reader cannot open was never
carrying the content; the sentence around it was.**

**The residual is now nought, and getting there changed what this check is.**
It stood at five for as long as those five were called noise and left, which
meant the exit code was 1 on every run and could never be anything else. A
gate that cannot go green does not gate: the only reading it ever supports is
the one that ignores it. Cleared 2026-09-02, four by writing the reference
out and one by the classes below.

Two of the four were prose repairs of the kind this check keeps asking for: a
shorthand ``_b.md`` standing in for a file whose full name is three words
longer, and a glob naming a family, both rewritten so a reader can follow
them. One was a path split across two comment lines in a way the wrap repair
below does not catch, rewrapped so it is not split. One was a header carrying
a working file name where the convention asks for a station name.

**The two classes are named below rather than tolerated**: a country-code
domain that ends in ``.md``, and a script declaring the markdown file it
writes. Both were reported for the whole life of this check, both are
decidable, and neither is a link a reader would ever try to follow.

Usage::

    python scripts/check_dead_links.py          # exit 1 if anything is unresolvable
    python scripts/check_dead_links.py --list   # also print what was scanned
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: A document reference: a path-shaped token ending in ``.md``. The character
#: class carries CJK explicitly so a Chinese file name is a candidate and not
#: invisible.
DOC = re.compile(r"(?<![A-Za-z0-9_./%-])[A-Za-z0-9_一-鿿][A-Za-z0-9_./一-鿿-]*\.md\b")

#: A bare internal document name, the form a moved-out file takes once its
#: extension is dropped: a Chinese stem with a ``_v<N>`` version suffix.
CJK_DOC = re.compile(r"[一-鿿][A-Za-z0-9_一-鿿]*_v\d+")

#: Read for references. Anything else is bytes, not prose.
READ = (".md", ".py", ".json", ".ps1", ".txt", ".yml", ".yaml")

#: Targets that are absent on purpose and say so. Each is a file whose whole
#: subject is a file that is not here.
EXEMPT_SOURCES = ("_WHY_ABSENT.md",)

#: Two sources are exempt, and the reasons are different.
#:
#: The measurement ledger's job is to record what broke, and several entries
#: name files that were moved or retired precisely because that is the instance.
#: Forbidding it to name them would delete the evidence to satisfy the check.
#:
#: This file names the pattern it exempts, in a string, which the scanner would
#: otherwise read as a reference.
EXEMPT_FILES = ("docs/MEASUREMENT.md", "scripts/check_dead_links.py",
                # This one holds the moved register's name in a constant and
                # searches the products for it. It is the guard for that string,
                # so carrying it is the point rather than the defect.
                "scripts/run_b8_package.py")

#: **Moldova's country-code top-level domain is ``.md``.** So a hostname like
#: ``legis.md`` or ``bnm.md`` is character-for-character the shape of a markdown
#: file and no amount of context in the regex separates them. This is not a
#: quirk of two sites: any Moldovan domain named anywhere in this repository
#: lands here, and the source-availability sections name them beside
#: ``matsne.gov.ge`` and ``e-qanun.az``, which the pattern never sees because
#: their suffixes are not ``.md``.
#:
#: Listed by name rather than guessed at by shape. A rule of the form "a short
#: lowercase stem with no underscore is probably a host" would also swallow a
#: real missing document called ``notes.md``, and this check exists because a
#: real one went missing.
EXTERNAL_HOSTS = ("legis.md", "bnm.md")

#: A script naming the file it writes is declaring a path, not citing a
#: document, and this file's own scope note already draws that line for
#: ``.json`` and ``.py`` targets. It did not draw it for a ``.md`` product,
#: so two runners that write a markdown result were reported for the whole
#: life of the check as referring to a document a reader cannot open.
#:
#: Narrow on purpose, three ways: only from a ``.py`` source, only for a bare
#: name with no separator in it, and only on a physical line that also carries
#: a quoted ``results`` path segment. That is the shape of a declared output,
#: ``ROOT / "results" / "b8_triangles.md"``, where the directory and the file
#: are two literals and the token the pattern sees is only the second of them.
#:
#: A prose citation keeps its separator, ``results/b8_triangles.md``, so it
#: fails the second test and stays checked. That is what keeps the published
#: result documents inside the net, and those are one of this arm's own
#: classes of published file, so leaving them unchecked would be a bad trade.
PRODUCT_LINE = re.compile("[" + chr(34) + chr(39) + "]results[" + chr(34) + chr(39) + "]")

#: The other arm's repository. A cross-arm reference is not a dead link: it
#: resolves for a reader who has both, which is the intended audience of a
#: methodology appendix that exists in two versions.
EXTERNAL_PREFIXES = ("topology-fingerprints/",)


def candidates() -> list[str]:
    """Every file that could reach the repository: the working tree, minus what
    ``.gitignore`` excludes, minus retired snapshots.

    Untracked is not the same as excluded. A file that is merely not yet added
    is a candidate, and scanning ``git ls-files`` instead of the tree is how a
    stage's unstaged files get skipped by a check that then reports clean.
    """
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")
                   and ".expired" not in d]
        # data/raw and data/processed hold the archives; they are excluded by
        # .gitignore anyway and walking them costs minutes.
        rel_base = os.path.relpath(base, ROOT).replace("\\", "/")
        if rel_base.startswith(("data/raw", "data/processed", "data/cache")):
            dirs[:] = []
            continue
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), ROOT).replace("\\", "/")
            if ".expired" in rel:
                continue
            out.append(rel)
    if not out:
        return []
    r = subprocess.run(["git", "check-ignore", "-z", "--stdin"],
                       input="\0".join(out) + "\0", cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    ignored = {x for x in r.stdout.split("\0") if x}
    return sorted(x for x in out if x not in ignored)


def scan(paths: list[str]) -> dict[str, list[str]]:
    present = set(paths)
    bad: dict[str, list[str]] = {}
    for rel in paths:
        if not rel.endswith(READ) or rel.endswith(EXEMPT_SOURCES):
            continue
        if rel in EXEMPT_FILES:
            continue
        try:
            text = Path(ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        miss = set()
        for m in DOC.finditer(text):
            # A reference wrapped across a line break leaves its tail looking
            # like a whole filename: `b7_interaction_` + newline + `rank.md`.
            # The signature is exact -- the character before the match is a
            # newline and the previous line ends in a word character -- so this
            # is a repair, not an exemption.
            i = m.start()
            head = text[:i]
            stripped = head.rstrip(" \t")
            if stripped.endswith("\n"):
                prev_line = stripped[:-1].rsplit("\n", 1)[-1].rstrip()
                if prev_line and prev_line[-1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
                                                  "abcdefghijklmnopqrstuvwxyz0123456789_-":
                    continue
            tok = m.group(0).strip("./")
            if tok.startswith(EXTERNAL_PREFIXES):
                continue
            if tok in EXTERNAL_HOSTS:
                continue
            if rel.endswith(".py") and "/" not in tok:
                line = (text[:i].rsplit(chr(10), 1)[-1]
                        + text[i:].split(chr(10), 1)[0])
                if PRODUCT_LINE.search(line):
                    continue
            if tok in present or any(p.endswith("/" + tok) for p in present):
                continue
            miss.add(tok)
        miss |= set(CJK_DOC.findall(text))
        if miss:
            bad[rel] = sorted(miss)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="print the scanned count")
    a = ap.parse_args()

    paths = candidates()
    bad = scan(paths)
    if a.list:
        print(f"scanned {len(paths)} candidate files")
    if not bad:
        print(f"0 unresolvable document references across {len(paths)} candidate files")
        return 0
    total = sum(len(v) for v in bad.values())
    print(f"{total} unresolvable document reference(s) in {len(bad)} file(s):")
    for src in sorted(bad):
        print(f"  {src}")
        for tgt in bad[src]:
            print(f"      -> {tgt}")
    print("\nEach is a link a reader cannot follow. Either the document belongs in\n"
          "the repository, or the reference should state the conclusion in place.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
