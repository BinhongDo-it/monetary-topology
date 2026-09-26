"""Resolve every address in the B30 index column against the results file.

**What this guards.** `RESULTS.md` carries an index of the B30 arms whose third
column says where each arm's blocks are. It carried line numbers into
`docs/b30_results.md` until 2026-09-16, and `20` of the `55` of them pointed into
another arm's block by then. Nothing reported it. A chunk inserted in the middle of
the results file moves every address below it, and a moved line number is still an
integer, so it prints clean and points elsewhere. That is discipline `D24`.

**Why headings work.** The results file's top-level headings are all distinct, its
``<arm>, chunk <word>`` pairs are all distinct, and no sub-heading repeats inside a
single chunk. A heading is therefore an address that survives an insertion, and it
is checkable: this script resolves each one and requires exactly one hit.

**Scope, and it is deliberately wider than the B30 table.** The same column shape
could carry line numbers anywhere in `RESULTS.md`, so the second pass scans every
row of the ledger for a last column that is a bare list of integers and reports it.
A guard that can only see the one table it was written for is the failure it is
meant to catch.

Usage::

    python scripts/check_b30_index.py
    python scripts/check_b30_index.py --selftest
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "RESULTS.md"
RESULTS = ROOT / "docs" / "b30_results.md"

WORDS = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()

ROW = re.compile(r"^\| \*\*(B30-[0-9a-z]+)\*\* \|.*\| ([^|]*?) \|$")
ANY_ROW = re.compile(r"^\| \*\*([^|*]+)\*\* \|.*\| ([^|]*?) \|$")
NUM = re.compile(r"\b\d{3,6}\b")

#: prose that carries no address and is skipped when a cell is split on commas
PROSE = {"results file", "design file", "and results file", "and the two sections above",
         "and the sections above", "the two sections above", ""}


def norm(s):
    """Lowercase, drop everything that is not a letter, digit or space, squeeze spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z ]+", "", s.lower())).strip()


def headings(text):
    return [l.strip() for l in text.split("\n") if re.match(r"# \S", l)]


def chunk_pattern(owner, word):
    """Match a chunk heading exactly, because ``chunk four`` is a prefix of
    ``chunk fourteen``.

    This is the trap `D24` names: an address that looks unique and is not. The
    ``<arm>, chunk <word>`` pairs in the results file are all distinct as pairs, so
    checking them by exact pair is sound; checking them by substring is not, and the
    only arm that shows the difference is the one that ran past chunk thirteen.
    """
    return re.compile(r"^#\s*" + re.escape(owner) + r",\s*chunk\s+" +
                      re.escape(word) + r"\s*[,:]")


def anchors(arm, cell):
    """Split one index cell into the addresses it names.

    Chunk addresses come back as compiled patterns and are matched against the raw
    heading. Phrase addresses come back as normalised strings and are looked for
    inside a normalised heading.
    """
    out = []
    headed = re.search(r"headed `([^`]+)`", cell)
    owner = headed.group(1) if headed else arm
    body = re.sub(r",?\s*headed `[^`]+`", "", cell)

    rng = re.search(r"chunks ([a-z]+) to ([a-z]+)", body)
    lst = re.search(r"chunks ([a-z]+(?:(?:,| and) [a-z]+)+)", body)
    one = re.search(r"chunk ([a-z]+)\b", body)
    got_chunks = False
    if rng and rng.group(1) in WORDS and rng.group(2) in WORDS:
        a, b = WORDS.index(rng.group(1)), WORDS.index(rng.group(2))
        out += [chunk_pattern(owner, WORDS[i]) for i in range(a, b + 1)]
        got_chunks = True
        body = body.replace(rng.group(0), "")
    elif lst:
        ws = [w for w in re.split(r",| and ", lst.group(1)) if w.strip() in WORDS]
        out += [chunk_pattern(owner, w.strip()) for w in ws]
        got_chunks = True
        body = body.replace(lst.group(0), "")
    elif one and one.group(1) in WORDS:
        out.append(chunk_pattern(owner, one.group(1)))
        got_chunks = True
        body = body.replace(one.group(0), "")

    for frag in body.split(","):
        f = frag.strip()
        if norm(f) in {norm(p) for p in PROSE} or not norm(f):
            continue
        f = re.sub(r"^and\s+", "", f)
        if norm(f):
            out.append(norm(f))
    if not out and not got_chunks:
        out.append(norm(cell))
    return out


def resolve(ledger_text, results_text):
    """Return (checked, problems). A problem is (arm, anchor, how_many_headings)."""
    raw = headings(results_text)
    heads = [norm(h) for h in raw]
    checked, problems = 0, []
    for ln in ledger_text.split("\n"):
        m = ROW.match(ln)
        if not m:
            continue
        arm, cell = m.group(1), m.group(2)
        if NUM.search(cell):
            problems.append((arm, f"cell carries a bare line number: {cell!r}", -1))
            continue
        for a in anchors(arm, cell):
            checked += 1
            if hasattr(a, "search"):
                hits = sum(1 for h in raw if a.search(h))
                shown = a.pattern
            else:
                hits = sum(1 for h in heads if a in h)
                shown = a
            if hits != 1:
                problems.append((arm, shown, hits))
    return checked, problems


def bare_number_columns(ledger_text):
    """Any index row anywhere in the ledger whose last column is only integers.

    **Scope, and the first version had it too wide.** Firing on "the last column is
    only integers" reported a data table whose last column is a daily standard
    deviation in basis points, which is a reading and not an address. An index column
    is one under a header whose last cell is named ``block``, so the scan tracks the
    most recent header row and only fires under those. That is `D24`'s second
    question asked of this guard: too narrow misses what it should see, too wide
    counts what it should not.
    """
    out, in_index = [], False
    for i, ln in enumerate(ledger_text.split("\n"), 1):
        if ln.startswith("|") and "|---" not in ln:
            cells = [c.strip().lower() for c in ln.strip("|").split("|")]
            if cells and cells[-1] in {"block", "blocks", "where"}:
                in_index = True
                continue
        if not ln.startswith("|"):
            if ln.strip() == "":
                pass
            else:
                in_index = False
        if not in_index:
            continue
        m = ANY_ROW.match(ln)
        if not m:
            continue
        cell = m.group(2).strip()
        if cell and re.fullmatch(r"[\d,\s]+", cell) and NUM.search(cell):
            out.append((i, m.group(1), cell))
    return out


def report(ledger_text, results_text):
    checked, problems = resolve(ledger_text, results_text)
    print(f"{checked} address(es) in the B30 index resolved against the results file")
    for arm, a, hits in problems:
        if hits < 0:
            print(f"  {arm}: {a}")
        else:
            print(f"  {arm}: {a!r} lands on {hits} heading(s), not one")
    bare = bare_number_columns(ledger_text)
    print(f"{len(bare)} ledger row(s) anywhere whose last column is only integers")
    for i, name, cell in bare:
        print(f"  line {i}: {name} -> {cell!r}")
    return problems, bare


def selftest():
    led = LEDGER.read_text(encoding="utf-8")
    res = RESULTS.read_text(encoding="utf-8")
    problems, bare = report(led, res)
    assert not problems, "the ledger as it stands does not resolve; fix it before seeding"
    assert not bare, "the ledger as it stands still has an integer-only column"

    print("\nseeding faults:")
    # 1. an address that names no heading
    bad = re.sub(r"(\| \*\*B30-19\*\* \|.*\| )results file, chunk one( \|)",
                 r"\1results file, chunk nineteen\2", led)
    assert bad != led, "the B30-19 seed did not apply"
    p = resolve(bad, res)[1]
    assert any("nineteen" in a for _, a, _ in p), "a nonexistent chunk was not reported"
    print("  an address naming no heading is reported")

    # 2. a line number put back into the column
    bad2 = re.sub(r"(\| \*\*B30-19\*\* \|.*\| )results file, chunk one( \|)",
                  r"\g<1>3509\2", led)
    assert bad2 != led, "the line-number seed did not apply"
    p2 = resolve(bad2, res)[1]
    assert any("bare line number" in a for _, a, _ in p2), "a line number was not reported"
    b2 = bare_number_columns(bad2)
    assert any(name == "B30-19" for _, name, _ in b2), "the wider scan missed the seeded number"
    print("  a line number put back into the column is reported by both passes")

    # 3. an address that names two headings, which is the ambiguity a bare
    #    sub-heading name would introduce
    bad3 = re.sub(r"(\| \*\*B30-19\*\* \|.*\| )results file, chunk one( \|)",
                  r"\1results file, chunk\2", led)
    p3 = resolve(bad3, res)[1]
    assert p3, "an address matching many headings was not reported"
    print("  an address matching more than one heading is reported")

    # 4. the prefix trap. B30-23 runs to chunk twenty, so `chunk four` sits inside
    #    `chunk fourteen` and a substring matcher reports two hits for a correct
    #    address. This asserts the resolver is not that matcher.
    for w, near in (("four", "fourteen"), ("six", "sixteen"), ("seven", "seventeen"),
                    ("eight", "eighteen"), ("nine", "nineteen")):
        pat = chunk_pattern("B30-23", w)
        hits = [h for h in headings(res) if pat.search(h)]
        assert len(hits) == 1, f"chunk {w} resolves to {len(hits)} headings, not one"
        assert near not in hits[0], f"chunk {w} resolved to the chunk {near} heading"
        loose = norm(f"B30-23, chunk {w}")
        assert sum(1 for h in headings(res) if loose in norm(h)) == 2, (
            f"the chunk {w} / chunk {near} prefix trap is no longer present, so this "
            f"probe no longer tests anything")
    print("  the chunk four inside chunk fourteen prefix trap resolves to one heading")
    print("\nnothing was written; the seeds live in memory only")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    problems, bare = report(LEDGER.read_text(encoding="utf-8"),
                            RESULTS.read_text(encoding="utf-8"))
    return 0 if not problems and not bare else 2


if __name__ == "__main__":
    sys.exit(main())
