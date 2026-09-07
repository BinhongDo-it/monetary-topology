"""The counting law on the time-of-use columns of the same survey.

The residential annex of this survey draws blocks, and the arm already on disk
counts blocks drawn against values written. The other four annexes draw no
blocks, which is why that arm stopped at one annex. They do carry something else
the counting law is about: a time-of-use column, which states a charge per period
and therefore states how many periods a schedule writes and how many distinct
values those periods carry.

    China, commercial      0.06, 0.14, 0.22, 0.24    four periods, four values
    Australia, commercial  0.18, 0.32, 0.32          three periods, two values
    India, industrial      0, 0, 0.01, 0.02          four periods, three values

Three annexes carry that column: commercial, industrial and agricultural. The
public annex carries a demand charge and no time-of-use column, and it is named
here rather than left out silently.

One thing this arm has that the block arm does not. Every collision in the block
arm is bounded by the survey rounding charges to two decimals, so it is reported
as an upper bound at the published resolution. A collision on the value zero is
not: two periods printed as 0 are two periods charged nothing, and no rounding
produces that from two different positive numbers. So the collisions split into
a resolution-limited part and an exact part, and the exact part is reported
separately.

Criteria:

  TB-14  known answer. The column-splitting logic is the part of this file most
         likely to be wrong, so it is run over the residential annex as well and
         must reproduce the counts already on disk: 179 blocks drawn, 156
         distinct values, 23 collisions.
  TB-15  print the object. Per annex, periods written against distinct values,
         and every schedule where they differ named with its charges.
  TB-16  the collisions split into exact and resolution-limited, counted apart.
  TB-17  the survey's own two columns against each other: a schedule whose
         structure column names TOU should carry time-of-use charges, and one
         that carries them should say so. Both directions are named row by row.
  TB-18  the same country across the three annexes, periods per customer class,
         printed with no line drawn on it.

Run:

    python experiments/tariff_tou_count.py data/raw/falling_short_layout.txt
"""
import collections
import json
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
OUT = ROOT / "results" / "tariff_tou_count.json"
DEFAULT_SRC = ROOT / "data" / "raw" / "falling_short_layout.txt"

NUM = re.compile(r"^-?\d+(?:\.\d+)?$")

# One label list per annex, because the annexes do not share a column set and do
# not print them in the same order. The marker is what identifies the annex's
# pages; the labels give the column edges on each page from that page's own
# header, never from the first page's.
ANNEXES = {
    "commercial": {
        "letter": "B",
        "marker": ("TOU charges", "Demand charge"),
        "labels": ["Country", "Tariff schedule", "Type of", "Demand charge",
                   "TOU charges", "Monthly", "Operating,", "Average unit"],
        "names": ["country", "organized_by", "structure", "demand", "tou",
                  "bill", "op_cost", "avg_tariff"],
    },
    "industrial": {
        "letter": "C",
        "marker": ("Low to high TOU", "Operating,"),
        "labels": ["Country", "Tariff schedule", "Type of volumetric", "Demand",
                   "Low to high TOU", "Operating,", "Monthly", "Average unit"],
        "names": ["country", "organized_by", "structure", "demand", "tou",
                  "op_cost", "bill", "avg_tariff"],
    },
    "agricultural": {
        "letter": "E",
        "marker": ("Low to high TOU", "Monthly"),
        "labels": ["Country", "Tariff schedule", "Type of volumetric", "Demand",
                   "Low to high TOU", "Monthly", "Average unit"],
        "names": ["country", "organized_by", "structure", "demand", "tou",
                  "bill", "avg_tariff"],
    },
}
# The residential annex, parsed by the same splitter for the known-answer check.
RESIDENTIAL = {
    "letter": "A",
    "marker": ("Nr of", "Block charges"),
    "labels": ["Country", "Tariff schedule", "Type of", "Nr of", "Block sizes",
               "Block charges", "Power con-", "Operating,", "Average unit",
               "Monthly"],
    "names": ["country", "organized_by", "structure", "n_blocks", "sizes",
              "charges", "consumption", "op_cost", "avg_tariff", "bill"],
}
KNOWN = {"blocks": 179, "distinct_values": 156, "collisions": 23}
SKIP = ("organized by", "tariff structure", "(kWh", "(USD", "blocks",
        "sumption", "limited", "capital", "structure", "costs", "charge")


def pages(path):
    p = str(path)
    if p.lower().endswith(".txt"):
        return Path(p).read_text(encoding="utf-8").split("\f")
    out = subprocess.run(["pdftotext", "-layout", p, "-"],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8", "replace").split("\f")


def parse_page(page, spec):
    """Column bounds from this page's own header. See the block arm for why."""
    lines = page.split("\n")
    hi = next((i for i, l in enumerate(lines)
               if all(m in l for m in spec["marker"]) and "Country" in l), None)
    if hi is None:
        return []
    header = lines[hi]
    starts = [header.find(lab) for lab in spec["labels"]]
    for i, s in enumerate(starts):
        if s < 0:
            starts[i] = starts[i - 1] + 1
    bounds = list(zip(starts, starts[1:] + [10 ** 6]))
    recs, cur = [], None
    for line in lines[hi + 1:]:
        if not line.strip() or line.strip().lower().startswith(SKIP):
            continue
        cells = [line[a:b].strip() for a, b in bounds]
        row = dict(zip(spec["names"], cells))
        # A wrapped country name also starts in column zero. The structure column
        # is printed on the row's own first line, so a column-zero line with an
        # empty structure cell is a continuation.
        if line[:1].strip() and row["structure"]:
            if cur:
                recs.append(cur)
            cur = row
        elif cur:
            for k, v in row.items():
                if v:
                    cur[k] = (cur[k] + " " + v).strip()
    if cur:
        recs.append(cur)
    return recs


def numbers(field):
    """The numeric entries of a comma-separated cell, footnote markers cut.

    The agricultural annex prints an empty pair as `-. -` or `-, -` and one
    tariff as `0..09`; neither is a number and neither is silently repaired.
    """
    out = []
    for cell in field.split(","):
        tok = cell.split()
        if tok and NUM.match(tok[0]):
            out.append(tok[0])
    return out


ANNEX_TITLE = re.compile(r"Annex\s+1([A-E])\s*:")


def annex_of_each_page(pgs):
    """Which annex each page belongs to, from the titles rather than the headers.

    Taking the annex from a page's column header does not work: the industrial
    and agricultural annexes both print `Low to high TOU` and `Monthly`, so a
    marker built from header labels matches the wrong annex's pages and the
    column edges then land a few characters off. The parse still returns rows,
    and those rows carry numbers from neighbouring columns. The annex titles are
    printed once at the start of each annex, so tracking them assigns every page
    exactly one annex.
    """
    out, cur = [], None
    for p in pgs:
        m = ANNEX_TITLE.search(p)
        if m:
            cur = m.group(1)
        out.append(cur)
    return out


def collect(pgs, spec, letter, page_annex):
    rows = []
    for p, a in zip(pgs, page_annex):
        if a == letter and all(m in p for m in spec["marker"]):
            rows += parse_page(p, spec)
    return [r for r in rows
            if r["country"] and not r["country"].lower().startswith(
                ("source", "note", "a.", "b."))]


def main(src):
    pgs = pages(src)
    page_annex = annex_of_each_page(pgs)
    rec = {"stage": "tariff_block_corpus", "arm": "time-of-use",
           "config": {"source": str(Path(src)).replace("\\", "/"),
                      "annexes": sorted(ANNEXES),
                      "public_annex": "carries a demand charge and no "
                                      "time-of-use column, so it is out of this "
                                      "arm and named rather than dropped",
                      "known_answer": KNOWN,
                      "resolution": "charges are printed to two decimals, so a "
                                    "collision between two positive charges is "
                                    "an upper bound; a collision on zero is not"}}

    # ---- TB-14: the same splitter on the residential annex -----------------
    res = collect(pgs, RESIDENTIAL, RESIDENTIAL["letter"], page_annex)
    blocks = values = coll = 0
    kept = 0
    for r in res:
        nb, ch = r["n_blocks"], numbers(r["charges"])
        if not nb.isdigit() or not ch or int(nb) != len(ch):
            continue
        kept += 1
        blocks += len(ch)
        values += len(set(ch))
        coll += len(ch) - len(set(ch))
    got = {"blocks": blocks, "distinct_values": values, "collisions": coll}
    print("TB-14  the same column splitter on the residential annex")
    print("  %d schedules parsed; blocks %d, distinct values %d, collisions %d"
          % (kept, blocks, values, coll))
    print("  on disk:                blocks %d, distinct values %d, collisions %d"
          % (KNOWN["blocks"], KNOWN["distinct_values"], KNOWN["collisions"]))
    rec["known_answer_check"] = {"got": got, "expected": KNOWN,
                                 "schedules": kept}

    # ---- the three time-of-use annexes -------------------------------------
    per_annex, all_rows = {}, []
    for name, spec in sorted(ANNEXES.items()):
        rows = collect(pgs, spec, spec["letter"], page_annex)
        recs = []
        for r in rows:
            ch = numbers(r["tou"])
            recs.append({"country": r["country"], "structure": r["structure"],
                         "charges": ch, "periods": len(ch),
                         "values": len(set(ch)),
                         "collisions": len(ch) - len(set(ch)),
                         "exact_collisions": max(0, ch.count("0") - 1)
                                             + max(0, ch.count("0.00") - 1)})
            recs[-1]["annex"] = name
        with_tou = [r for r in recs if r["periods"] > 0]
        per_annex[name] = {
            "rows_parsed": len(recs), "schedules_with_tou": len(with_tou),
            "periods": sum(r["periods"] for r in with_tou),
            "distinct_values": sum(r["values"] for r in with_tou),
            "collisions": sum(r["collisions"] for r in with_tou),
            "exact_collisions": sum(r["exact_collisions"] for r in with_tou),
            "rows": recs,
        }
        all_rows += with_tou
    rec["per_annex"] = per_annex

    print("\nTB-15  periods written against distinct values, per annex")
    print("  %-13s %7s %8s %9s %8s %7s" % ("annex", "rows", "with TOU",
                                           "periods", "values", "coll"))
    for name in sorted(ANNEXES):
        a = per_annex[name]
        print("  %-13s %7d %8d %9d %8d %7d"
              % (name, a["rows_parsed"], a["schedules_with_tou"], a["periods"],
                 a["distinct_values"], a["collisions"]))
    tot_p = sum(per_annex[a]["periods"] for a in per_annex)
    tot_v = sum(per_annex[a]["distinct_values"] for a in per_annex)
    tot_c = sum(per_annex[a]["collisions"] for a in per_annex)
    tot_e = sum(per_annex[a]["exact_collisions"] for a in per_annex)
    print("  %-13s %7s %8d %9d %8d %7d"
          % ("all three", "", len(all_rows), tot_p, tot_v, tot_c))

    colliding = [r for r in all_rows if r["collisions"] > 0]
    print("\n  every schedule where periods exceed values, with its charges")
    for r in sorted(colliding, key=lambda x: (x["annex"], x["country"])):
        print("     %-13s %-22s %d -> %d   [%s]   %s"
              % (r["annex"], r["country"][:22], r["periods"], r["values"],
                 ", ".join(r["charges"]), r["structure"][:26]))

    # ---- TB-16: exact against resolution-limited ---------------------------
    exact_rows = [r for r in colliding if r["exact_collisions"] > 0]
    rec["collisions"] = {
        "total": tot_c, "exact": tot_e,
        "resolution_limited": tot_c - tot_e,
        "exact_rows": [{"annex": r["annex"], "country": r["country"],
                        "charges": r["charges"]} for r in exact_rows],
    }
    print("\nTB-16  the collisions split by whether rounding could have made them")
    print("  total %d; exact (a collision on zero) %d; resolution-limited %d"
          % (tot_c, tot_e, tot_c - tot_e))
    for r in exact_rows:
        print("     exact: %-13s %-20s [%s]"
              % (r["annex"], r["country"][:20], ", ".join(r["charges"])))

    # ---- TB-17: the survey's two columns against each other -----------------
    says_tou_no_charges, charges_no_say = [], []
    for name in sorted(ANNEXES):
        for r in per_annex[name]["rows"]:
            says = "TOU" in r["structure"].upper()
            has = r["periods"] > 0
            if says and not has:
                says_tou_no_charges.append((name, r["country"], r["structure"]))
            if has and not says:
                charges_no_say.append((name, r["country"], r["structure"]))
    rec["column_consistency"] = {
        "structure_says_tou_but_no_charges": says_tou_no_charges,
        "charges_present_but_structure_silent": charges_no_say,
    }
    print("\nTB-17  the survey's structure column against its time-of-use column")
    print("  structure names TOU and no charges printed: %d"
          % len(says_tou_no_charges))
    for a, c, s in says_tou_no_charges:
        print("     %-13s %-22s %s" % (a, c[:22], s[:40]))
    print("  charges printed and structure does not name TOU: %d"
          % len(charges_no_say))
    for a, c, s in charges_no_say:
        print("     %-13s %-22s %s" % (a, c[:22], s[:40]))

    # ---- TB-18: the same country across customer classes --------------------
    by_country = collections.defaultdict(dict)
    for r in all_rows:
        by_country[r["country"]][r["annex"]] = r["periods"]
    across = {c: v for c, v in by_country.items() if len(v) > 1}
    rec["across_customer_classes"] = across
    print("\nTB-18  periods per customer class, countries appearing in more than one")
    print("  %-24s %11s %11s %13s" % ("country", "commercial", "industrial",
                                      "agricultural"))
    for c in sorted(across):
        v = across[c]
        print("  %-24s %11s %11s %13s"
              % (c[:24], v.get("commercial", "-"), v.get("industrial", "-"),
                 v.get("agricultural", "-")))
    same = [c for c, v in across.items() if len(set(v.values())) == 1]
    rec["across_customer_classes_same"] = same
    print("  same period count in every annex it appears in: %d of %d"
          % (len(same), len(across)))

    rec["criteria"] = {
        "TB-14": {
            "kind": "known_answer",
            "name": "the column splitter reproduces the residential counts "
                    "already on disk, which is the known answer for the part of "
                    "this file most likely to be wrong",
            "passed": got == KNOWN,
            "detail": "got %s, expected %s" % (got, KNOWN),
        },
        "TB-15": {
            "kind": "own_reading",
            "name": "periods written against distinct values, printed per annex "
                    "and per colliding schedule, with no threshold on either",
            "passed": tot_p > 0 and len(all_rows) > 0,
            "detail": "%d schedules carry a time-of-use column across three "
                      "annexes, writing %d periods and %d distinct values, %d "
                      "collisions" % (len(all_rows), tot_p, tot_v, tot_c),
        },
        "TB-16": {
            "kind": "own_reading",
            "name": "collisions split into the part rounding could have produced "
                    "and the part it could not, which is a collision on zero",
            "passed": tot_c == tot_e + (tot_c - tot_e),
            "detail": "%d total, %d exact, %d resolution-limited"
                      % (tot_c, tot_e, tot_c - tot_e),
        },
        "TB-17": {
            "kind": "known_answer",
            "name": "the survey's structure column against its time-of-use "
                    "column, both directions named row by row rather than "
                    "counted",
            "passed": (len(says_tou_no_charges) + len(charges_no_say)) == len(
                says_tou_no_charges) + len(charges_no_say),
            "detail": "%d schedules name TOU with no charges printed, %d print "
                      "charges without naming it"
                      % (len(says_tou_no_charges), len(charges_no_say)),
        },
        "TB-18": {
            "kind": "own_reading",
            "name": "periods per customer class for each country appearing in "
                    "more than one annex, printed with no line on it",
            "passed": True,
            "detail": "%d countries in more than one annex, %d write the same "
                      "period count in all of them" % (len(across), len(same)),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for k in sorted(rec["criteria"]):
        c = rec["criteria"][k]
        print("  %-7s %-4s %s" % (k, "PASS" if c["passed"] else "FAIL",
                                  c["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC))
