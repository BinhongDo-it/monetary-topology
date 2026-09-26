"""B33: where the fold is. Collection, price list, publication, counted separately.

Arm one read a tax code against itself and found that two filing statuses, a joint
return and a surviving spouse, take the same cell in every provision that prints a
number and are separated only by provisions that print none. That reading is
document-internal: both sides came from the statute.

The obvious next question is whether the fold is only in the statute or runs
through the whole administrative system, and it turns out to be answerable by
reading documents rather than by pulling numbers, because the agencies say how
their own classifications are built.

Three layers, three different documents:

    collection    the return form the taxpayer fills in
    price list    the provisions of the code that print numbers
    publication   the statistical tables the revenue service puts out

The middle layer's count is not typed in here. It is read out of arm one's own
record, so that editing arm one's dimension table moves this number with it.

Usage
-----
    python b33_three_layers.py
    python b33_three_layers.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARM_ONE = ROOT / "results" / "b33_filing_status.json"
OUT = ROOT / "results" / "b33_three_layers.json"

# The two outer layers are documented facts, each with the phrase that carries it.
# The inner layer is computed, see middle_layer().
OUTER = {
    "collection": {
        "document": "Instructions for Form 1040, Filing Status",
        "separates": True,
        "classes": 5,
        "quote": "Qualifying surviving spouse",
        "reads": "five checkboxes on the return, and the surviving spouse has one "
                 "of its own, so the taxpayer states which of the two they are at "
                 "the moment of filing",
        "read_in_full": True,
    },
    "publication": {
        "document": "SOI Tax Stats, historical data tables, and the basic tables "
                    "of the complete report, which classify by marital status "
                    "through tax year 2023",
        "separates": True,
        "classes": None,
        "quote": "Individual Income Tax Filing: Returns of Surviving Spouses",
        "reads": "the revenue service publishes a count of returns of surviving "
                 "spouses as a series of its own, annual, with values through "
                 "2016 in the mirror consulted here, so the two are distinguished "
                 "on the way out as well as on the way in",
        "read_in_full": False,
        "not_read": "the stub of the current basic table classified by size of "
                    "adjusted gross income and marital status was not opened, so "
                    "the exact category names now in use are not read here. That "
                    "would settle the class count of this layer; it does not "
                    "affect whether this layer separates the two, which the "
                    "published series already answers",
    },
}


def middle_layer():
    """Read the price list's class count out of arm one's record, not from here."""
    if not ARM_ONE.exists():
        return None
    rec = json.loads(ARM_ONE.read_text(encoding="utf-8"))
    rep = rec.get("report", {})
    blocks = rep.get("blocks_numbers_only")
    part = rep.get("partition_numbers_only")
    folded = [b for b in (part or []) if len(b) > 1]
    return {
        "document": "the provisions of the code that print numbers, as read by "
                    "arm one: the rate table, the basic standard deduction and "
                    "the alternative minimum tax exemption",
        "separates": not any(set(b) >= {"MFJ", "QSS"} for b in folded),
        "classes": blocks,
        "written_classes": rep.get("blocks_written"),
        "folded_cells": folded,
        "quote": "Married individuals filing joint returns and surviving spouses",
        "reads": "the two take the same cell in every one of these, so the price "
                 "list writes one class where the other two layers write two",
        "read_in_full": True,
        "source_record": ARM_ONE.name,
    }


def analyse():
    mid = middle_layer()
    if mid is None:
        mid = {"document": "arm one's record is not on disk, so the price list "
                           "layer could not be read",
               "separates": None, "classes": None, "written_classes": None,
               "folded_cells": None, "quote": "", "reads": "not read",
               "read_in_full": False,
               "not_read": "the record this layer is computed from is absent",
               "source_record": None}
    layers = [
        dict(OUTER["collection"], layer="collection"),
        dict(mid, layer="price_list"),
        dict(OUTER["publication"], layer="publication"),
    ]
    seps = [l.get("separates") for l in layers]
    return {
        "layers": layers,
        "separates": seps,
        "fold_at": [l["layer"] for l in layers if l.get("separates") is False],
        "middle_read_from_record": mid.get("source_record") is not None,
        "layers_read_in_full": sum(1 for l in layers if l.get("read_in_full")),
        "layers_named": len(layers),
    }


def criteria(rep):
    layers = rep["layers"]
    mid = [l for l in layers if l["layer"] == "price_list"][0]
    quoted = [l for l in layers if l.get("quote")]
    return [
        {
            "name": "B33-18 the two classes are distinguished at collection and "
                    "at publication and folded in between, so the fold is a "
                    "property of the price list and not of the administrative "
                    "system that surrounds it",
            "kind": "own_reading",
            "state_map": {
                "middle_only": "the fold sits in the price list alone",
                "everywhere": "every layer folds them, so the distinction is not "
                              "carried anywhere and the reading is about the "
                              "system rather than the price list",
                "nowhere": "no layer folds them, which would contradict arm one",
                "other": "some other pattern, name it rather than forcing it",
            },
            "passed": rep["fold_at"] == ["price_list"],
            "detail": "collection separates: %s; price list separates: %s; "
                      "publication separates: %s; fold at: %s"
                      % (layers[0].get("separates"), mid.get("separates"),
                         layers[2].get("separates"),
                         ", ".join(rep["fold_at"]) or "nowhere"),
        },
        {
            "name": "B33-19 the price list's count is read out of arm one's "
                    "record rather than typed here, so editing arm one's "
                    "dimensions moves this number with it",
            "kind": "instrument",
            "passed": (rep["middle_read_from_record"]
                       and mid.get("classes") is not None
                       and mid.get("written_classes") is not None),
            "detail": "read from %s: %s classes over the number-bearing "
                      "provisions against %s written, folded cells %s"
                      % (mid.get("source_record"), mid.get("classes"),
                         mid.get("written_classes"),
                         mid.get("folded_cells")),
        },
        {
            "name": "B33-20 every layer names its document and carries a phrase "
                    "quoted from it, and the layer that was not read in full says "
                    "so rather than being reported as read",
            "kind": "bookkeeping",
            "passed": (len(quoted) == len(layers)
                       and all(l.get("read_in_full") or l.get("not_read")
                               for l in layers)),
            "detail": "%d of %d layers quoted; read in full %d of %d; not read "
                      "in full and saying so: %s"
                      % (len(quoted), len(layers), rep["layers_read_in_full"],
                         len(layers),
                         ", ".join(l["layer"] for l in layers
                                   if not l.get("read_in_full")) or "none"),
        },
    ]


def selftest():
    ok = True
    rep = analyse()

    # Seed one: a world where the outer layers fold too.
    saved = OUTER["collection"]["separates"], OUTER["publication"]["separates"]
    OUTER["collection"]["separates"] = False
    OUTER["publication"]["separates"] = False
    r = analyse()
    c = {x["name"].split()[0]: x for x in criteria(r)}
    if c["B33-18"]["passed"]:
        print("selftest: B33-18 should fail when every layer folds")
        ok = False
    OUTER["collection"]["separates"], OUTER["publication"]["separates"] = saved

    # Seed two: a layer with no quote and no admission that it was not read.
    saved_q = OUTER["publication"]["quote"]
    OUTER["publication"]["quote"] = ""
    r = analyse()
    c = {x["name"].split()[0]: x for x in criteria(r)}
    if c["B33-20"]["passed"]:
        print("selftest: B33-20 should fail on an unquoted layer")
        ok = False
    OUTER["publication"]["quote"] = saved_q

    # Seed three: arm one's record missing, so the middle layer cannot be read.
    global ARM_ONE
    saved_p = ARM_ONE
    ARM_ONE = ROOT / "results" / "_no_such_record.json"
    r = analyse()
    c = {x["name"].split()[0]: x for x in criteria(r)}
    if c["B33-19"]["passed"]:
        print("selftest: B33-19 should fail when arm one's record is absent")
        ok = False
    ARM_ONE = saved_p

    print("selftest: %s" % ("all three seeds behaved" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rep = analyse()
    crit = criteria(rep)

    print("B33: where the fold is, read across three layers\n")
    for l in rep["layers"]:
        print("%-12s separates: %-5s classes: %-5s  %s"
              % (l["layer"], l.get("separates"),
                 "-" if l.get("classes") is None else l["classes"],
                 l.get("document", "")))
        print("             quote: %s" % l.get("quote"))
        print("             %s" % l.get("reads"))
        if l.get("not_read"):
            print("             NOT READ: %s" % l["not_read"])
        print()
    print("fold at: %s" % (", ".join(rep["fold_at"]) or "nowhere"))
    print()
    for c in crit:
        print("%-5s %-11s %s" % ("PASS" if c["passed"] else "FAIL", c["kind"],
                                 c["name"].split(" ", 1)[0]))
        print("      %s" % c["detail"])

    OUT.write_text(json.dumps({
        "stage": "B33",
        "config": {
            "arm": "one, the observed side of the partition claim",
            "question": "is the fold a property of the price list alone, or does "
                        "the whole administrative system carry it",
            "middle_layer_source": ARM_ONE.name,
            "estimates": "none, no number was pulled; this reads how the "
                         "agencies say their own classifications are built",
            "read_on": "2026-09-11",
            "not_done": "no amounts were read, so this says nothing about whether "
                        "the two classes pay the same effective rate at the same "
                        "income; that is the next cut and it needs one table",
        },
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
