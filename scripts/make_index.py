"""Build INDEX.md from RESULTS.md's own section headings.

RESULTS.md is the ledger and the authority. This script does not read it for
content: it reads the `## ` lines, which are one per block, and turns them into
a sorted table of links. That is the whole mapping, so a block cannot be missed
the way the retired RESULTS generator missed four whole stations by requiring a
key the records did not all carry. Every block is a line, and every line becomes
a row.

The hand-written part of INDEX.md is the story map at the top, which lives in
this file as a constant. A station missing from a story line is an incomplete
map rather than a false one; a station missing from the table would be a false
one, which is why the table is not hand-written.

    python scripts/make_index.py              write INDEX.md
    python scripts/make_index.py --check      exit non-zero if INDEX.md is stale
    python scripts/make_index.py --selftest   plant faults and check they are caught

Derived-file discipline: no clock, no paths, no host, encoding pinned at both
ends, iteration order fixed, so two machines write the same bytes.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "RESULTS.md"
INDEX = ROOT / "INDEX.md"
DOCS = ROOT / "docs"

NL = chr(10)

TRACK_ORDER = {"A": 0, "B": 1, "C": 2, "E": 3, "L": 4}

# A station id at the head of a heading: a letter run, a number, then any of a
# single trailing letter, an underscore part, or a hyphen part. A heading that
# does not start that way is a block with no station, and those sort last.
STATION = re.compile(
    r"^([A-Za-z]+\d+(?:[A-Za-z](?![A-Za-z])|_[A-Za-z0-9]+|-[A-Za-z0-9]+)*)"
)

# What a heading carries after the station id starts with some separator: an em
# dash, a colon, a comma, or nothing at all. The whole remainder is kept, since
# cutting at the first dash drops the part of the heading that names the round.
LEAD = " 	,:—–-"

STORY = [
    (
        "A price is not a scalar field on positions",
        "The rival is one scalar per position whose gradient generates every term, "
        "so every closed loop returns zero. These are the stations that put a "
        "number on a loop.",
        "B1, B1H, B2A, B3, B4, B8, B9, B13, B24, B31, B49, B52, B98, B106",
    ),
    (
        "The counting law: how many values a written rule can carry",
        "A programme names classes and writes a figure against each. The law counts "
        "the distinct figures, and it needs no price at all.",
        "B33, B43, B46, B47, B53, B55, B56, B57, B58, B102",
    ),
    (
        "Reachability, and the registration point that opens an edge",
        "Before any price there is whether an edge exists. These stations read the "
        "rule that opens or closes one.",
        "B6-A, B6-B, B15, B36, B48, B62, C1, C2, C3, E1",
    ),
    (
        "Standard price theory, recovered as special cases",
        "Zero data. Each station takes a published result and locates it inside the "
        "same graph object, usually as one member of a family or one value of one "
        "parameter.",
        "B63 to B96",
    ),
    (
        "Index numbers, and what an aggregation hides",
        "An index is a projection. These read the projection itself rather than the "
        "number it returns.",
        "B79, B81, B83, B84, B101, B131, B132, B133, B134",
    ),
    (
        "Cutting a relation, and what it rewrites",
        "What changes when an edge is removed or restored, read before the cut where "
        "the theorem allows that.",
        "B97, B103, B104, B105, B111, B115",
    ),
    (
        "Where new claims go, and how long they stay",
        "New money enters somewhere. These stations ask where it is a round later.",
        "A41, A44, A45, A52, B112, B114, B117",
    ),
    (
        "Housing: residence binding, rent caps, and who keeps the location value",
        "Location demand on the asset carrier. These stations read what a rule tying "
        "ownership, credit or rent to residence does to who stays and who ends up "
        "with the premium.",
        "A47, A48, A49, A50, A51, B129, B130",
    ),
    (
        "The stratified economy: support sets, position and circulation",
        "The simulation track's spine. Positions are fixed before each run and every "
        "mechanism after the first is off by default.",
        "A0, A0b, A2, A2d, A4, A5, A6, A7, A8, A13, A14, A19, A20, A21, A26",
    ),
    (
        "Default, the subsistence floor, and the household ladder",
        "Where the distribution decides who stops, and the one place the track is "
        "asked to meet a measured cross-section.",
        "A1, A1a, A1b, A1c, A1d, A10, A11, A12, A16",
    ),
    (
        "Policy switches, and the time path rather than the closing value",
        "Forbearance, write-offs, levies, withdrawal, and who carries each.",
        "A9, A15, A17, A18, A18_B, A18_C, A18_D, A18_E, A18_F, A23, A32, A33, "
        "A37, A38, A39",
    ),
]


# Which subfield a station's reader comes from. A station sits in one, which is
# a filing decision and not a claim about what it touches; several touch more.
# Every station id in the ledger must appear here or the selftest reports it,
# because a station quietly missing from a field list is a station nobody in
# that field will find.

THEORY = "The theorem itself, and its checks"
MICRO = "Market microstructure and asset pricing"
HH = "Household finance and consumer credit"
INTL = "International finance and exchange rate regimes"
CORP = "Corporate finance and credit"
MACRO = "Macroeconomics, inequality and monetary policy"
PAY = "Payment systems and monetary operations"
CLASSICAL = "Classical and Sraffian price theory"
INDEXNO = "Index numbers and price comparison"
PUBFIN = "Public finance, regulated prices and published schedules"
TRADE = "Trade policy and commodity markets"
LABOUR = "Labour economics"
NET = "Networks, complex systems and agent-based modelling"
METR = "Econometrics, identification and measurement"
HIST = "Economic history"
ADMIN = "Climate, education and administrative conversion factors"

FIELD_ORDER = [
    THEORY, MICRO, HH, INTL, CORP, MACRO, PAY, CLASSICAL, INDEXNO,
    PUBFIN, TRADE, LABOUR, NET, METR, HIST, ADMIN,
]

FIELD = {}


def _put(field, ids):
    for i in ids.split():
        FIELD[i] = field


_put(THEORY, "B1 B1H B1-R B4 B43")
_put(MICRO, "B9 B9-0 B9-A B9-A-1 B9-A-2 B9-A-6 B9-A-9 B13 B14 B16 B18 L2")
_put(HH, "A1 A1a A1b A1c A1d B2A B2B B2c B7 B8 B10 B12")
_put(INTL, "B3 B5 B6-A B6-B B15 B17 B21 B23 B24 B48 B62 B63 B97")
_put(CORP, "B11 B19 B110 B120")
_put(MACRO, "A3 A3b A3h A3i A3j A3k A4 A9 A10 A10H A11 A18 A18_B A18_C A18_D "
            "A18_E A18_F A23 A29 A30 A31 A32 A33 A34 A35 A36 A37 A38 A39 A41 "
            "A44 A45 B65 B66")
_put(PAY, "A25 B59 B112 B113 B114 B117")
_put(CLASSICAL, "B67 B68 B69 B70 B71 B72 B73 B74 B75 B76 B77 B78 B80 B82 B85 "
                "B86 B87 B88 B89 B90 B91 B92 B93 B94 B95 B96 B103 B104 B105")
_put(INDEXNO, "B38 B38b B38c B38d B39 B79 B81 B83 B84 B101")
_put(PUBFIN, "A6 A6-7 B33 B45 B49 B50 B51 B52 B53 B54 B55 B56 B57 B58 B98 "
             "B100 B102 Counting")
_put(TRADE, "B31 B36 B41 B42 B60 B61 B111 B115")
_put(LABOUR, "A27 B34 B106")
_put(NET, "A0 A0b A2 A2c A2d A2e A5 A7 A8 A12 A13 A14 A15 A16 A17 A19 A20 "
          "A21 A22 A24 A26 A40 A42 A43")
_put(METR, "B30 B30-5 D14 FAIL")
_put(HIST, "B40 B44 B46 B47 B64")
_put(ADMIN, "C1 C2 C3 E1")
_put(THEORY, "B29 B124")
_put(MICRO, "B20 B126 B127")
_put(HH, "A47 A48 A49 A51 B130")
_put(INTL, "B37")
_put(MACRO, "A50 A52 B121 B128")
_put(PAY, "B123")
_put(PUBFIN, "B25 B26 B28 B99 B122 B125 B129")
_put(INDEXNO, "B131 B132 B133 B134")
_put(HIST, "B32")
_put(ADMIN, "B27")

HEAD = """# Index

**[RESULTS.md](RESULTS.md) is the record and the authority. This file is a map of
it.** It carries no reading of its own: every row below is one section heading of
the ledger, linked to that section, and the table is generated by
`scripts/make_index.py`, so a block cannot be in the ledger and missing here.

[README.md](README.md) is the entry point and says what the programme claims.
This file says where each piece of it is.

## Lines to read in order

**The station numbers are stable identifiers rather than a reading order.** A
line below is a route through the ledger; the table after it is the whole thing,
sorted by number. A station can sit on more than one line, and a line naming
fewer stations than belong on it is an incomplete map rather than a claim that
the rest are not there.
"""

BY_FIELD_HEAD = """## Which stations are in your field

**A station is filed under one subfield, which is a filing decision rather than a
claim about what it touches.** Several touch more than one, and the table below
is the whole ledger without this cut. `speedrun/README.md` says what each field's
stations found in that field's own vocabulary.
"""

TABLE_HEAD = """## Every block in the ledger

**One row per section of [RESULTS.md](RESULTS.md).** A station that ran in more
than one round carries more than one row. The third column is the station's prose
document where it has one, and a station has one when it holds something a record
cannot: a proof, a derivation, or a carrier specification.

| station | what the block asks | doc |
|---|---|---|"""


def anchor(heading):
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    a = unicodedata.normalize("NFC", heading.strip()).lower()
    a = "".join(ch for ch in a if ch.isalnum() or ch in " -_")
    return a.replace(" ", "-")


def parse(text):
    """Every `## ` line, in file order, with its station id and its subject."""
    blocks = []
    for line in text.split("\n"):
        if not line.startswith("## "):
            continue
        heading = line[3:].strip()
        m = STATION.match(heading)
        sid = m.group(1) if m else ""
        rest = heading[len(sid):] if sid else heading
        subject = rest.lstrip(LEAD).strip()
        blocks.append({"heading": heading, "station": sid, "subject": subject})
    return blocks


def with_anchors(blocks):
    seen = {}
    for b in blocks:
        a = anchor(b["heading"])
        n = seen.get(a, 0)
        seen[a] = n + 1
        b["anchor"] = a if n == 0 else a + "-" + str(n)
    return blocks


def field_key(b):
    """What FIELD is looked up by. A block with no station id keys on its first
    word, so the two that have none are filed rather than silently dropped."""
    return b["station"] or b["heading"].split()[0]


def unfiled(blocks):
    """Station keys the field map does not carry, in ledger order, no repeats."""
    out = []
    for b in blocks:
        k = field_key(b)
        if k not in FIELD and k not in out:
            out.append(k)
    return out

def sort_key(b):
    sid = b["station"]
    if not sid:
        return (9, "", 0, "", b["order"])
    m = re.match(r"^([A-Za-z]+)(\d+)(.*)$", sid)
    track, num, suffix = m.group(1), int(m.group(2)), m.group(3)
    return (TRACK_ORDER.get(track.upper(), 8), track.upper(), num, suffix, b["order"])


def docs_for(sid, docnames):
    """Every published document whose name is built on this station's id."""
    if not sid:
        return []
    stem = sid.lower().replace("-", "_")
    return [n for n in docnames if n[:-3] == stem or n[:-3].startswith(stem + "_")]


def build(results_text, docnames):
    blocks = with_anchors(parse(results_text))
    for i, b in enumerate(blocks):
        b["order"] = i
    blocks = sorted(blocks, key=sort_key)

    out = [HEAD]
    for title, gloss, ids in STORY:
        out.append("**" + title + ".** " + gloss + "\n\n`" + ids + "`\n")
    out.append(BY_FIELD_HEAD)
    seen_field = {}
    for b in blocks:
        k = field_key(b)
        f = FIELD.get(k)
        if f is None:
            continue
        seen_field.setdefault(f, [])
        if k not in seen_field[f]:
            seen_field[f].append(k)
    for f in FIELD_ORDER:
        if f in seen_field:
            out.append("**" + f + "**" + NL + NL + "`" + ", ".join(seen_field[f]) + "`" + NL)
    missing = unfiled(blocks)
    if missing:
        out.append(
            "**Not filed yet**, and named rather than dropped:" + NL + NL
            + "`" + ", ".join(missing) + "`" + NL
        )

    out.append(TABLE_HEAD)

    rows = []
    for b in blocks:
        sid = b["station"] or "—"
        doclinks = ", ".join(
            "[`" + d + "`](docs/" + d + ")" for d in docs_for(b["station"], docnames)
        )
        subject = b["subject"].replace("|", "\\|")
        rows.append(
            "| [" + sid + "](#" + b["anchor"] + ") | " + subject + " | " + doclinks + " |"
        )
    out.append("\n".join(rows))
    return "\n".join(out) + "\n"


def docnames():
    return sorted(p.name for p in DOCS.glob("*.md"))


def render():
    return build(RESULTS.read_text(encoding="utf-8"), docnames())


def selftest():
    sample = "\n".join(
        [
            "# Ledger",
            "## A0 — retention",
            "## A0b — the downward edge",
            "## B9-A-1",
            "## B9 §31 variance decomposition",
            "## A18_B — who pays",
            "## Counting law on something with no station",
            "## A0 — retention",
        ]
    )
    heads = [l for l in sample.split("\n") if l.startswith("## ")]
    text = build(sample, [])
    rows = [l for l in text.split("\n") if l.startswith("| [")]
    failures = []

    if len(rows) != len(heads):
        failures.append("row count %d against %d headings" % (len(rows), len(heads)))

    thin = "\n".join(l for l in sample.split("\n") if "A18_B" not in l)
    if build(thin, []) == text:
        failures.append("dropping a heading did not change the table")

    anchors = re.findall(r"\]\(#([^)]+)\)", text)
    if len(set(anchors)) != len(anchors):
        failures.append("two identical headings collided on one anchor")

    for want in ("A0b", "B9-A-1", "A18_B"):
        if "[" + want + "](#" in text:
            continue
        failures.append("station id %s not parsed" % want)

    if text.count("| [—](#") != 1:
        failures.append("the block with no station id lost its row")

    # A doc must attach to its own station and not to a longer-numbered one.
    with_doc = build("## B1 — x\n## B10 — y\n", ["b1_theorem.md"])
    if with_doc.count("(docs/b1_theorem.md)") != 1:
        failures.append("the doc column matched the wrong station")

    # Every document built on a station's id has to appear, not just the first.
    two = build("## A1 — x\n", ["a1_availability.md", "a1_prereg.md"])
    if two.count("(docs/a1_") != 2:
        failures.append("the doc column kept only one of a station's documents")

    # A heading that names a round must keep that part of itself.
    rounds = build("## A29, second round: bonds that fall due\n", [])
    if "second round: bonds that fall due" not in rounds:
        failures.append("the round was cut out of the subject")

    # Whatever sits between the station id and the dash belongs to the subject.
    step = build("## A3 §16.1 step one — retention at every node\n", [])
    if "§16.1 step one — retention at every node" not in step:
        failures.append("the part before the dash was cut out of the subject")

    # Every row has to be findable by searching for the station id.
    if build("## A0 — x\n## A0 — y\n", []).count("| [A0](#") != 2:
        failures.append("a repeated station id was blanked in the second row")

    # A station with no field has to be named in the file, not dropped from it.
    orphan = build("## B4242 — nobody filed this\n", [])
    if "B4242" not in orphan.split("## Every block in the ledger")[0]:
        failures.append("an unfiled station is not named above the table")

    # A field that has stations has to reach the file under its own name.
    filed = build("## B8 — x\n", [])
    if "**" + HH + "**" not in filed:
        failures.append("a field with stations never reaches the file")

    # And the live ledger must have nothing unfiled.
    live_blocks = parse(RESULTS.read_text(encoding="utf-8"))
    left = unfiled(live_blocks)
    if left:
        failures.append("stations with no field: " + ", ".join(left))

    live = render()
    live_rows = [l for l in live.split("\n") if l.startswith("| [")]
    live_heads = [
        l
        for l in RESULTS.read_text(encoding="utf-8").split("\n")
        if l.startswith("## ")
    ]
    if len(live_rows) != len(live_heads):
        failures.append(
            "on the ledger itself, %d rows against %d headings"
            % (len(live_rows), len(live_heads))
        )

    for f in failures:
        print("SELFTEST FAIL:", f)
    if failures:
        return 1
    print("selftest ok, %d rows on the live ledger" % len(live_rows))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    text = render()
    if args.check:
        if not INDEX.exists():
            print("INDEX.md is missing; run scripts/make_index.py")
            return 1
        if INDEX.read_text(encoding="utf-8") != text:
            print("INDEX.md is stale; run scripts/make_index.py")
            return 1
        print("INDEX.md is current")
        return 0

    INDEX.write_text(text, encoding="utf-8", newline="\n")
    rows = sum(1 for l in text.split("\n") if l.startswith("| ["))
    print("wrote INDEX.md, %d rows" % rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
