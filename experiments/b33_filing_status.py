"""B33 arm one, third candidate: the five filing statuses of the Internal Revenue Code.

Arm one asks whether the partition a published schedule writes down is the same
partition its complete clause vectors induce. The scoring action is to look for a
written class that buys nothing: two classes whose members receive the same terms
on every dimension.

Two earlier candidates were closed. A Singapore subsidiary regulation scored, and
a Hong Kong pair was shut at a pre-check because dependent parent and dependent
grandparent are two entries on a list of who qualifies, not two optional identities
for one position, so a taxpayer with only a grandparent got zero before the second
entry existed and the allowance after it.

This candidate is the opposite configuration and it is the one the criterion was
written for. The Code writes five filing statuses and states their mutual exclusions
in the text. Two of them, a joint return and a surviving spouse, take the same cell
in every provision of the Code that prints a number, and are separated only by
provisions that print no number at all: whose income is aggregated, who is liable,
who may elect relief, how long the status lasts, and what household must be kept.

So the reading here is quantitative and it is about where the separation lives:

    over the number-bearing provisions   the partition has four blocks
    over every provision                 the partition has five blocks
    the one merge that the numbers make is undone by terms alone

and the mirror case is in the same table: a single filer and a married individual
filing separately are separated by numbers and coincide on almost every term. The
schedule uses both mechanisms, and they are independent.

Nothing is estimated. Every value is a cell of a published statute, quoted.

Usage
-----
    python b33_filing_status.py
    python b33_filing_status.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b33_filing_status.json"

STATUSES = ["MFJ", "QSS", "HOH", "SINGLE", "MFS"]

LONG = {
    "MFJ": "married individual making a single return jointly with a spouse",
    "QSS": "surviving spouse as defined in section 2(a)",
    "HOH": "head of a household as defined in section 2(b)",
    "SINGLE": "unmarried individual, neither a surviving spouse nor a head of a household",
    "MFS": "married individual filing a separate return",
}

# Every dimension is one published provision. "carries" says whether that
# provision delivers a number or a term. The quote is the address: a phrase that
# appears once in the section it cites, so a reader can grep for it instead of
# following an offset into a document that keeps being amended.
DIMS = [
    {
        "id": "sec1_rate_table",
        "cite": "26 U.S.C. 1(a)-(d)",
        "carries": "number",
        "quote": "Married individuals filing joint returns and surviving spouses",
        "values": {
            "MFJ": "1(a)", "QSS": "1(a)", "HOH": "1(b)",
            "SINGLE": "1(c)", "MFS": "1(d)",
        },
    },
    {
        "id": "sec63c2_basic_standard_deduction",
        "cite": "26 U.S.C. 63(c)(2)",
        "carries": "number",
        "quote": "200 percent of the dollar amount in effect under subparagraph (C) "
                 "for the taxable year in the case of",
        "values": {
            "MFJ": "63(c)(2)(A), two hundred percent of the (C) amount",
            "QSS": "63(c)(2)(A), two hundred percent of the (C) amount",
            "HOH": "63(c)(2)(B), 4,400",
            "SINGLE": "63(c)(2)(C), 3,000",
            "MFS": "63(c)(2)(C), 3,000",
        },
    },
    {
        "id": "sec55d1_amt_exemption",
        "cite": "26 U.S.C. 55(d)(1)",
        "carries": "number",
        "quote": "is not a married individual, and",
        "values": {
            "MFJ": "55(d)(1)(A), 78,750",
            "QSS": "55(d)(1)(A), 78,750",
            "HOH": "55(d)(1)(B), 50,600",
            "SINGLE": "55(d)(1)(B), 50,600",
            "MFS": "55(d)(1)(C), fifty percent of the (A) amount",
        },
    },
    {
        "id": "sec6013d3_tax_base",
        "cite": "26 U.S.C. 6013(d)(3)",
        "carries": "term",
        "quote": "the tax shall be computed on the aggregate income",
        "values": {
            "MFJ": "two persons' income on one return",
            "QSS": "one person's income",
            "HOH": "one person's income",
            "SINGLE": "one person's income",
            "MFS": "one person's income",
        },
    },
    {
        "id": "sec6013d3_liability",
        "cite": "26 U.S.C. 6013(d)(3)",
        "carries": "term",
        "quote": "the liability with respect to the tax shall be joint and several",
        "values": {
            "MFJ": "joint and several",
            "QSS": "several", "HOH": "several",
            "SINGLE": "several", "MFS": "several",
        },
    },
    {
        "id": "sec6015a_relief_election",
        "cite": "26 U.S.C. 6015(a)",
        "carries": "term",
        "quote": "an individual who has made a joint return may elect to seek relief",
        "values": {
            "MFJ": "may elect",
            "QSS": "no election", "HOH": "no election",
            "SINGLE": "no election", "MFS": "no election",
        },
    },
    {
        "id": "sec2a1A_window",
        "cite": "26 U.S.C. 2(a)(1)(A)",
        "carries": "term",
        "quote": "whose spouse died during either of his two taxable years "
                 "immediately preceding the taxable year",
        "values": {
            "MFJ": "no expiry", "QSS": "expires two taxable years after the death",
            "HOH": "no expiry", "SINGLE": "no expiry", "MFS": "no expiry",
        },
    },
    {
        "id": "sec2a2A_remarriage_bar",
        "cite": "26 U.S.C. 2(a)(2)(A)",
        "carries": "term",
        "quote": "the taxpayer has remarried at any time before the close of the taxable year",
        "values": {
            "MFJ": "no such bar", "QSS": "status lost on remarriage",
            "HOH": "no such bar", "SINGLE": "no such bar", "MFS": "no such bar",
        },
    },
    {
        "id": "sec2_household_test",
        "cite": "26 U.S.C. 2(a)(1)(B) and 2(b)(1)",
        "carries": "term",
        "quote": "over half of the cost of maintaining the household during the "
                 "taxable year is furnished by such individual",
        "values": {
            "MFJ": "no household test",
            "QSS": "a household for a dependent child, over half the cost, 2(a)(1)(B)",
            "HOH": "a household for a qualifying person, 2(b)(1)",
            "SINGLE": "no household test", "MFS": "no household test",
        },
    },
    {
        "id": "sec63c6A_zero_standard_deduction",
        "cite": "26 U.S.C. 63(c)(6)(A)",
        "carries": "term",
        "quote": "a married individual filing a separate return where either spouse "
                 "itemizes deductions",
        "values": {
            "MFJ": "no such condition", "QSS": "no such condition",
            "HOH": "no such condition", "SINGLE": "no such condition",
            "MFS": "standard deduction is zero if the other spouse itemizes",
        },
    },
]

# The Code states the exclusions in the text, which is what makes the five a
# partition of a taxpayer-year rather than a list of who qualifies for something.
EXCLUSIONS = [
    ("26 U.S.C. 1(c)",
     "every individual (other than a surviving",
     "the unmarried table names surviving spouses and heads of household out of itself"),
    ("26 U.S.C. 2(b)(1)",
     "is not married at the close of his taxable year, is not a surviving spouse",
     "a head of household is neither married nor a surviving spouse"),
    ("26 U.S.C. 2(a)(2)(A)",
     "the taxpayer has remarried at any time before the close of the taxable year",
     "surviving spouse status ends on remarriage, so it cannot be held with a married status"),
    ("26 U.S.C. 6013(a)",
     "A husband and wife may make a single return jointly",
     "a joint return needs a living spouse, and 2(a)(1)(A) needs a dead one"),
]

VERDICT_MAP = {
    "equal": ("PASS", "the written partition and the delivered one are the same"),
    "read_coarser": ("FAIL", "a written class buys nothing"),
    "read_finer_drawn": ("no failure",
                         "a line inside a written class that a provision draws; "
                         "the position set was written too narrow and must carry "
                         "that dimension"),
    "read_finer_undrawn": ("FAIL",
                           "a line inside a written class that no provision draws"),
    "crossed": ("FAIL", "neither partition refines the other"),
    "incomplete": (None, "the clause vector was not read in full, no verdict"),
}


def refinement(dims, statuses=None):
    """Statuses that carry the same value on every dimension in dims."""
    statuses = statuses or STATUSES
    seen = {}
    for s in statuses:
        seen.setdefault(tuple(d["values"][s] for d in dims), []).append(s)
    return sorted((tuple(v) for v in seen.values()), key=lambda b: STATUSES.index(b[0]))


def refines(fine, coarse):
    """True when every block of fine sits inside some block of coarse."""
    return all(any(set(b) <= set(c) for c in coarse) for b in fine)


def classify(p_written, p_read, undrawn_lines, complete):
    if not complete:
        return "incomplete"
    if sorted(map(sorted, p_written)) == sorted(map(sorted, p_read)):
        return "equal"
    if refines(p_read, p_written):
        return "read_finer_undrawn" if undrawn_lines else "read_finer_drawn"
    if refines(p_written, p_read):
        return "read_coarser"
    return "crossed"


def show(part):
    return " | ".join("{" + ",".join(b) + "}" for b in part)


def analyse(dims):
    nums = [d for d in dims if d["carries"] == "number"]
    terms = [d for d in dims if d["carries"] == "term"]
    p_written = [(s,) for s in STATUSES]
    p_num = refinement(nums) if nums else [tuple(STATUSES)]
    p_term = refinement(terms) if terms else [tuple(STATUSES)]
    p_all = refinement(dims)

    pairs = []
    for a, b in itertools.combinations(STATUSES, 2):
        same_n = [d["id"] for d in nums if d["values"][a] == d["values"][b]]
        same_t = [d["id"] for d in terms if d["values"][a] == d["values"][b]]
        diff_n = [d["id"] for d in nums if d["values"][a] != d["values"][b]]
        diff_t = [d["id"] for d in terms if d["values"][a] != d["values"][b]]
        pairs.append({
            "pair": [a, b],
            "numbers_same": same_n, "numbers_diff": diff_n,
            "terms_same": same_t, "terms_diff": diff_t,
            "all_numbers_coincide": len(diff_n) == 0,
            "separated_by": ("terms only" if not diff_n and diff_t else
                             "numbers only" if diff_n and not diff_t else
                             "both" if diff_n and diff_t else "nothing"),
        })

    # A provision that indexed its classes by the values it delivers would carry
    # one row per distinct vector, so it could never put two statuses in one cell.
    # Scope: the number-bearing provisions, because those are the price list. A
    # term provision names one status and leaves the rest at a residual, and a
    # residual is not a written cell, so counting those would inflate this.
    folds = []
    for d in nums:
        for block in refinement([d]):
            if len(block) > 1:
                folds.append({"dim": d["id"], "cell": d["values"][block[0]],
                              "holds": list(block)})
    return {
        "statuses": {s: LONG[s] for s in STATUSES},
        "dims": [{k: d[k] for k in ("id", "cite", "carries", "quote", "values")}
                 for d in dims],
        "partition_written": [list(b) for b in p_written],
        "partition_numbers_only": [list(b) for b in p_num],
        "partition_terms_only": [list(b) for b in p_term],
        "partition_all": [list(b) for b in p_all],
        "blocks_numbers_only": len(p_num),
        "blocks_terms_only": len(p_term),
        "blocks_all": len(p_all),
        "blocks_written": len(p_written),
        "pairs": pairs,
        "folds": folds,
        "exclusions": [{"cite": c, "quote": q, "reads": r} for c, q, r in EXCLUSIONS],
    }


def criteria(rep, dims, complete=True, undrawn=()):
    nums = [d for d in dims if d["carries"] == "number"]
    terms = [d for d in dims if d["carries"] == "term"]
    full = [p for p in rep["pairs"] if p["all_numbers_coincide"]]
    target = [p for p in rep["pairs"] if p["pair"] == ["MFJ", "QSS"]]
    tgt = target[0] if target else None

    state = classify(rep["partition_written"], rep["partition_all"],
                     undrawn, complete)
    verdict, reads = VERDICT_MAP[state]

    known = [
        (["SINGLE", "HOH"], "sec63c2_basic_standard_deduction"),
        (["MFJ", "MFS"], "sec1_rate_table"),
        (["SINGLE", "MFS"], "sec55d1_amt_exemption"),
        (["QSS", "HOH"], "sec55d1_amt_exemption"),
    ]
    # Look the pair up by its members, not by the order they were typed in. The
    # first run of this control failed on a pair that does differ, because the
    # list here was written SINGLE/HOH and the pairs are built in status order.
    misses = []
    for pr, dim in known:
        got = [p for p in rep["pairs"] if set(p["pair"]) == set(pr)]
        if not got:
            misses.append("%s is not among the pairs" % "/".join(pr))
        elif dim not in got[0]["numbers_diff"]:
            misses.append("%s should differ on %s" % ("/".join(pr), dim))

    cited = [d for d in dims if d.get("cite") and d.get("quote")]

    crit = [
        {
            "name": "B33-6 the candidate clears both shape gates: the five are "
                    "mutually exclusive at one position by the Code's own words, "
                    "and the document delivering the vectors is not itself the "
                    "price list, shown by cells that hold two statuses at once",
            "kind": "instrument",
            "passed": len(EXCLUSIONS) >= 3 and len(rep["folds"]) >= 1,
            "detail": "%d exclusion clauses quoted; %d cells of the price list "
                      "hold two statuses at once (%s), which a value-indexed list "
                      "cannot do"
                      % (len(EXCLUSIONS), len(rep["folds"]),
                         "; ".join("%s holds %s" % (f["dim"], "+".join(f["holds"]))
                                   for f in rep["folds"])),
        },
        {
            "name": "B33-7 over every provision of the Code that prints a number, "
                    "a joint return and a surviving spouse take the same cell, and "
                    "they are the only pair of the ten that does",
            "kind": "own_reading",
            "passed": (tgt is not None and len(tgt["numbers_diff"]) == 0
                       and len(full) == 1),
            "detail": "MFJ/QSS differ on %d of %d number-bearing provisions; "
                      "pairs coinciding on every number: %d (%s); pairs coinciding "
                      "on some but not all: %s"
                      % (0 if tgt is None else len(tgt["numbers_diff"]), len(nums),
                         len(full), ", ".join("/".join(p["pair"]) for p in full),
                         ", ".join("%s on %s" % ("/".join(p["pair"]),
                                                 ",".join(p["numbers_same"]))
                                   for p in rep["pairs"]
                                   if p["numbers_same"] and p["numbers_diff"])
                         or "none"),
        },
        {
            "name": "B33-8 the scalar field's point prediction does not hold here: "
                    "two classes taking the same value in every number-bearing "
                    "provision receive different terms",
            "kind": "rival",
            "grid": "B",
            "grid_note": "the rival stakes that the two classes are interchangeable "
                         "and this framework stakes that a class-indexed term "
                         "exists, so the two differ on this pair and one of them "
                         "is wrong",
            "rival_shape": "point prediction",
            "rival_premise": "a position carries a scalar and every term at that "
                             "position is generated by it, so the object has one "
                             "index and no class index",
            "rival_entailment": "terms are then a function of the scalar, so two "
                                "classes reading the same scalar at the same "
                                "position must receive identical terms; a single "
                                "provision on which they differ falsifies it, and "
                                "the cost of moving between the two classes is "
                                "zero dollars, so no price difference can be "
                                "invoked to absorb the gap",
            "cite": "26 U.S.C. 6013(d)(3), quoted verbatim from the official text "
                    "at uscode.house.gov as well as from a mirror",
            "passed": tgt is not None and len(tgt["terms_diff"]) > 0,
            "detail": "the rival's prediction holds on %d of %d dimensions for "
                      "MFJ/QSS (%d number-bearing, that is every number the Code "
                      "prints for them, and %d term-bearing) and fails on %d, "
                      "every one of them term-bearing: %s"
                      % (0 if tgt is None else len(tgt["numbers_same"])
                         + len(tgt["terms_same"]),
                         len(dims),
                         0 if tgt is None else len(tgt["numbers_same"]),
                         0 if tgt is None else len(tgt["terms_same"]),
                         0 if tgt is None else len(tgt["terms_diff"]),
                         "" if tgt is None else ", ".join(tgt["terms_diff"])),
        },
        {
            "name": "B33-9 arm one on this carrier: the partition the Code writes "
                    "and the partition the complete clause vectors induce",
            "kind": "own_reading",
            "state_map": {k: {"verdict": v[0], "reads": v[1]}
                          for k, v in VERDICT_MAP.items()},
            "state": state,
            "passed": verdict == "PASS",
            "detail": ("Not adjudicable: %s" % reads) if verdict is None else
                      "written %d blocks %s; delivered %d blocks %s; state %s "
                      "maps to %s"
                      % (rep["blocks_written"], show(rep["partition_written"]),
                         rep["blocks_all"], show(rep["partition_all"]),
                         state, verdict),
        },
        {
            "name": "B33-10 control: pairs known to differ on numbers read as "
                    "differing, and every one of the ten pairs is named with what "
                    "separates it",
            "kind": "known_answer",
            "passed": not misses and len(rep["pairs"]) == 10,
            "detail": "%d pairs named, %d known-answer checks, %d missed%s; "
                      "separated by terms only: %s; by numbers only: %s; by both: "
                      "%s; by nothing: %s"
                      % (len(rep["pairs"]), len(known), len(misses),
                         "" if not misses else " (" + "; ".join(misses) + ")",
                         ", ".join("/".join(p["pair"]) for p in rep["pairs"]
                                   if p["separated_by"] == "terms only") or "none",
                         ", ".join("/".join(p["pair"]) for p in rep["pairs"]
                                   if p["separated_by"] == "numbers only") or "none",
                         ", ".join("/".join(p["pair"]) for p in rep["pairs"]
                                   if p["separated_by"] == "both") or "none",
                         ", ".join("/".join(p["pair"]) for p in rep["pairs"]
                                   if p["separated_by"] == "nothing") or "none"),
        },
        {
            "name": "B33-11 every dimension carries a section number and a phrase "
                    "quoted from that section, so the address survives the next "
                    "amendment",
            "kind": "bookkeeping",
            "passed": len(cited) == len(dims),
            "detail": "%d of %d dimensions carry both; %d number-bearing, %d "
                      "term-bearing; sections touched: %s"
                      % (len(cited), len(dims), len(nums), len(terms),
                         ", ".join(sorted({d["cite"].split("(")[0].strip()
                                           for d in dims}))),
        },
    ]
    return crit


def selftest():
    ok = True

    assert VERDICT_MAP["incomplete"][0] is None, \
        "the undecided cell must map to no verdict"

    # Seed one: delete every term-bearing provision. The two classes then coincide
    # on everything read, which is exactly the failure arm one is looking for.
    seed = [d for d in DIMS if d["carries"] == "number"]
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, seed)}
    if crit["B33-8"]["passed"]:
        print("selftest: B33-8 should fail when no term separates the pair")
        ok = False
    if crit["B33-9"]["passed"] or crit["B33-9"]["state"] != "read_coarser":
        print("selftest: B33-9 should read coarser and fail, got %s"
              % crit["B33-9"]["state"])
        ok = False

    # Seed two: a dimension with no citation.
    seed = [dict(d) for d in DIMS]
    seed[0] = dict(seed[0]); seed[0]["quote"] = ""
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, seed)}
    if crit["B33-11"]["passed"]:
        print("selftest: B33-11 should fail on an uncited dimension")
        ok = False

    # Seed three: the vector was not read in full.
    rep = analyse(DIMS)
    crit = {c["name"].split()[0]: c for c in criteria(rep, DIMS, complete=False)}
    if crit["B33-9"]["state"] != "incomplete":
        print("selftest: B33-9 should be incomplete, got %s" % crit["B33-9"]["state"])
        ok = False
    if not crit["B33-9"]["detail"].startswith("Not adjudicable"):
        print("selftest: an unadjudicated criterion must say so in its first words")
        ok = False

    # Seed four: break the control by making a pair known to differ coincide.
    seed = [dict(d, values=dict(d["values"])) for d in DIMS]
    for d in seed:
        d["values"]["HOH"] = d["values"]["SINGLE"]
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, seed)}
    if crit["B33-10"]["passed"]:
        print("selftest: B33-10 should fail when a known-different pair coincides")
        ok = False

    print("selftest: %s" % ("all four seeds behaved" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rep = analyse(DIMS)
    crit = criteria(rep, DIMS)

    print("B33 arm one, third candidate: five filing statuses in the Internal "
          "Revenue Code\n")
    for s in STATUSES:
        print("  %-7s %s" % (s, LONG[s]))
    print()

    w = max(len(d["id"]) for d in DIMS)
    print("%-*s %-7s %s" % (w, "provision", "carries",
                            " ".join("%-46s" % s for s in STATUSES)))
    for d in DIMS:
        print("%-*s %-7s %s" % (w, d["id"], d["carries"],
                                " ".join("%-46s" % d["values"][s][:46]
                                         for s in STATUSES)))
    print()
    print("partition written by the Code   %d blocks  %s"
          % (rep["blocks_written"], show(rep["partition_written"])))
    print("partition over numbers alone    %d blocks  %s"
          % (rep["blocks_numbers_only"], show(rep["partition_numbers_only"])))
    print("partition over terms alone      %d blocks  %s"
          % (rep["blocks_terms_only"], show(rep["partition_terms_only"])))
    print("partition over every provision  %d blocks  %s"
          % (rep["blocks_all"], show(rep["partition_all"])))
    print()
    print("cells of the price list that hold two statuses at once:")
    for f in rep["folds"]:
        print("   %-34s %-46s %s" % (f["dim"], f["cell"][:46], "+".join(f["holds"])))
    print()
    print("%-14s %-14s %s" % ("pair", "separated by", "what separates it"))
    for p in rep["pairs"]:
        print("%-14s %-14s %s"
              % ("/".join(p["pair"]), p["separated_by"],
                 ", ".join(p["numbers_diff"] + p["terms_diff"]) or "-"))
    print()
    print("exclusion clauses that make the five a partition of one taxpayer-year:")
    for e in rep["exclusions"]:
        print("   %-24s %s" % (e["cite"], e["reads"]))
    print()
    for c in crit:
        print("%-5s %-11s %s"
              % ("PASS" if c["passed"] else "FAIL", c["kind"],
                 c["name"].split(" ", 1)[0]))
        print("      %s" % c["detail"])

    OUT.write_text(json.dumps({
        "stage": "B33",
        "config": {
            "arm": "one, the partition claim",
            "carrier": "Internal Revenue Code, five filing statuses",
            "positions": "(taxpayer, taxable year)",
            "classes": STATUSES,
            "dims": len(DIMS),
            "source_level": "official for the load-bearing clause, 26 U.S.C. "
                            "6013(d)(3) read at uscode.house.gov; the remaining "
                            "sections read at an authoritative mirror of the same "
                            "Code, and the two agree word for word where both were "
                            "read",
            "read_on": "2026-09-10",
            "estimates": "none, every value is a cell of a published statute",
        },
        "criteria": crit,
        "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
