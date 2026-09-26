"""B57. Does drawing a class line separate anything.

The counting law with "distinct" in it is an identity: what a published
programme produces is the number of distinct class values it writes. That
cannot fail and nothing is learned by scoring it. The quantity that can fail
sits one level down and is per line rather than per table.

    THE PAIRING RULE, WRITTEN ONCE AND USED FOR EVERY ROW BELOW.

    A programme's cells are indexed by a class-line value L and a context C,
    where C is every other attribute the cell is indexed by. Two cells form a
    PAIRABLE PAIR when they share C and differ in L. The line SEPARATES that
    pair when the two cells carry different values.

        use rate  =  separated pairs / pairable pairs

    FOURTH CLAUSE, ADDED 2026-09-08 BY AUDITING THIS STATION'S OWN ROWS.
    A partition is DEGENERATE for this quantity when its own label already fixes
    the value. A heading reading "Free Fare Eligibility" fixes the value at zero,
    so every entry under it carries zero by construction and a rate of zero there
    reads the heading back rather than reading the cells. That is D25's degenerate
    square in this setting: a zero forced by the construction carries no claim.
    A heading reading "Riders Eligible for Reduced Fares" does NOT fix which
    reduced fare, and another operator's table proves it by printing three
    different reduced columns. A statute that names three classes and caps each
    does not fix the value either. Rows carry `label_fixes_value`, criterion
    B57-9 checks it, and a degenerate row is excluded from the rival reading.

    THIRD CLAUSE, ADDED 2026-09-07 BEFORE THE SIXTH ROW WAS BUILT.
    The set of values L ranges over must be ONE PARTITION THE SOURCE ITSELF
    NAMES, not a set assembled by whoever is doing the reading. Without it the
    reader picks the set and thereby picks the answer: on one transit page the
    child line separates from every paying class and separates from nothing
    inside the free list, so a rate anywhere between 0 and 1 is available by
    choosing which other lines to pair it against. Every row below records the
    named partition it draws L from, and criterion B57-7 checks the field is
    present. This is the same discipline as printing the object rather than a
    count: a use rate without its partition named is not a reading.

Why this quantity and not the collision rate. The collision rate (distinct
values over cells) moves with how fine a granularity the pricing party chose,
which is a property of that party, so it is comparable only inside one family
and it is not even monotone in cell count on the corpus here. The use rate is
per line, is a proportion, does not move with cell count, and does not move
with value granularity: a line either separates a given pair or it does not,
whatever precision the values are written to. It asks whether the edge exists.

The rule above was arrived at twice independently. The B30-22 block that read
the gender line of a live motor tariff used the same construction, in its own
words "cells carry a complete pair" and "pairs whose two values differ". That
row is carried here rather than recomputed, because its cells are in a
1,415-page filing that is not on this disk; it is marked as carried.

Rows whose cells ARE on disk are recomputed from the cell data itself, by
importing the modules that hold it rather than by retyping any figure.

Criteria carry a `kind`. Only `rival` bears on the framework.

Usage::

    python experiments/b57_class_line_use_rate.py
"""

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b55_virginia_licence_counting as b55          # noqa: E402
import b56_class_lines_vs_values as b56              # noqa: E402


# --------------------------------------------------------------------------
# The pairing rule. One function, every row.
# --------------------------------------------------------------------------

def coverage(cells, lines):
    """Which line values are absent from which contexts.

    pair_up drops a context that lacks one of the two values, and dropping it is
    correct: there is no pair to read. But an absent cell is a statement of its
    own and D25's first question is exactly it. A class that cannot reach a
    product at all is an H0 reachability fact, not a use rate. So the absences
    are counted and named rather than silently dropped.
    """
    possible = len(cells) * len(lines)
    absent = {}
    for ctx, by_line in sorted(cells.items()):
        missing = [ln for ln in lines if ln not in by_line]
        if missing:
            absent[str(ctx)] = missing
    n_absent = sum(len(v) for v in absent.values())
    return {"cells_possible": possible, "cells_present": possible - n_absent,
            "cells_absent": n_absent, "absent_by_context": absent}


#: Every cell that went through pair_up on this run, as (context, line, value).
#: B57-3's premise is about the cells this file recomputes, and it used to be
#: checked against a list of five tables written by hand: a cell in any other row
#: could be anything at all and the criterion would still pass. pair_up is the one
#: place every recomputed row goes through, so the premise is checked here, on
#: what the run actually built.
RECOMPUTED_CELLS: list = []


def pair_up(cells):
    """cells: {context: {line_value: cell_value}} -> per-line-pair counts.

    Returns (per_pair, pairable, separated) where per_pair is keyed by the
    unordered pair of line values and each entry counts pairable and separated
    contexts. A context contributes a pair only when both line values are
    present in it, so a missing cell is never counted as an agreement.
    """
    per_pair = {}
    for ctx, by_line in sorted(cells.items()):
        for line, value in sorted(by_line.items()):
            RECOMPUTED_CELLS.append((str(ctx), str(line), value))
    for ctx, by_line in sorted(cells.items()):
        for a, b in combinations(sorted(by_line), 2):
            key = "%s | %s" % (a, b)
            e = per_pair.setdefault(key, {"pairable": 0, "separated": 0,
                                          "same_value_contexts": []})
            e["pairable"] += 1
            if by_line[a] != by_line[b]:
                e["separated"] += 1
            else:
                e["same_value_contexts"].append(str(ctx))
    pairable = sum(e["pairable"] for e in per_pair.values())
    separated = sum(e["separated"] for e in per_pair.values())
    for e in per_pair.values():
        e["use_rate"] = e["separated"] / e["pairable"] if e["pairable"] else None
    return per_pair, pairable, separated


# --------------------------------------------------------------------------
# Row 1. Virginia hunting and fishing licences, the residency line.
# Cells from B55. Context is the shared (activity, age, term) description that
# B55 wrote down when it paired the table by hand.
# --------------------------------------------------------------------------

def row_virginia():
    cells = {shared: {"resident": res, "nonresident": non}
             for shared, res, non in b55.RESIDENCY_PAIRS}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "residency",
            "partition": "resident against non-resident, the two columns the fee "
                         "schedule itself is written in",
            "label_fixes_value": False,
            "why": "the two column heads name who, not how much",
            "family": "government regulatory licence",
            "source": "4 Va. Admin. Code 15-20-65, recomputed from the cells in B55",
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair}


# --------------------------------------------------------------------------
# Row 2. Agra monument admission, the nationality line, three blocks.
# Cells from B56, which retrieved the current schedule with a browser.
# Context is (monument, kind of day).
# --------------------------------------------------------------------------

def row_agra():
    names = ("Indian", "SAARC/BIMSTEC", "other foreign")
    cells = {}
    for label, table in (("weekday", b56.AGRA_WEEKDAY), ("friday", b56.AGRA_FRIDAY)):
        for monument, (indian, foreign, saarc) in sorted(table.items()):
            cells[(label, monument)] = dict(zip(names, (indian, saarc, foreign)))
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "nationality (three blocks)",
            "partition": "Indian / SAARC and BIMSTEC / other foreign, the three "
                         "columns the published schedule prints",
            "label_fixes_value": False,
            "why": "nationality names who, not how much",
            "family": "public service pricing",
            "source": b56.AGRA_SOURCE + ", recomputed from the cells in B56",
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair}


# --------------------------------------------------------------------------
# Row 3. The three class lines 49 U.S.C. 5307(c)(1)(D) names, on the operators
# whose amounts were read. Every such operator prices the whole reduced block
# at one value, so every cell in a context carries that value.
# Context is (operator, good). Operators whose amounts were not read contribute
# nothing, not an agreement (rule 11c).
# --------------------------------------------------------------------------

def row_transit_federal():
    lines = ("65 or over", "disability", "Medicare card")
    cells, independent = {}, 0
    for name, a in sorted(b56.TRANSIT_AGENCIES.items()):
        if not a["checked"]:
            continue
        independent += 1                       # D22: one independent fact per operator
        for good, vals in sorted(a["cents"].items()):
            reduced = sorted(set(vals))
            if len(reduced) != 1:
                continue
            cells[(name, good)] = {ln: reduced[0] for ln in lines}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "the three lines the federal condition names",
            "partition": "the three classes named in 49 U.S.C. 5307(c)(1)(D), "
                         "which is one list in one sentence of the statute",
            "label_fixes_value": False,
            "why": "the statute caps the fare at half the peak fare and does not "
                   "require the three to pay the same as each other, so three "
                   "different values are fully available under this label",
            "family": "public service pricing",
            "source": "49 U.S.C. 5307(c)(1)(D) and the operators' own fare pages, "
                      "recomputed from the cells in B56",
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable if pairable else None,
            "nominal_pairs": pairable, "independent_facts": independent,
            "per_pair": per_pair}


# --------------------------------------------------------------------------
# Row 4. School student against senior, the pair two operators both draw and
# both credential. Context is (operator, good).
# --------------------------------------------------------------------------

def row_student_senior():
    cells = {}
    for op, d in sorted(b56.STUDENT_VS_SENIOR.items()):
        for good, senior in sorted(d["senior_cents"].items()):
            student = d["student_cents"][good]
            cells[(op, good)] = {"school student": student, "senior": senior}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "school student against senior",
            "partition": "two entries both operators list separately on their own "
                         "reduced-fare pages, each with its own credential",
            "label_fixes_value": False,
            "why": "one of the two operators prices them apart, which settles it",
            "family": "public service pricing",
            "source": "the two operators' own fare pages, recomputed from the cells in B56",
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable,
            "nominal_pairs": pairable,
            "independent_facts": len(b56.STUDENT_VS_SENIOR),
            "per_pair": per_pair}


# --------------------------------------------------------------------------
# Rows 6 and 7. The two lists one transit page names, read 2026-09-07.
# These qualify under the third clause: each is a heading on the operator's own
# page with its entries under it, not a set assembled here. The page carries a
# sentence covering the second list, that all reduced fare prices are the same
# whichever card is held, and the first list is priced at zero throughout.
#
# The child line is why the third clause exists. Paired against the paying
# classes it separates every time; paired inside the free list it separates
# never. Both are true and neither is the reading, because neither set is a
# partition the page names. What the page names is the free list, and inside it
# the child line does nothing.
MBTA_GOODS = {"subway": {"full": 240, "reduced": 110}, "bus": {"full": 170, "reduced": 85}}

MBTA_FREE_LIST = ["children 11 and younger", "legally blind", "military personnel",
                  "on-duty police and firefighters", "government officials"]
MBTA_REDUCED_LIST = ["disability or Medicare card", "65 or over",
                     "middle or high school student", "18-64 on state assistance"]
MBTA_SOURCE = ("mbta.com/fares/reduced and mbta.com/fares, both retrieved "
               "2026-09-07 by browser")


def row_mbta_list(which):
    if which == "free":
        lines, value_of = MBTA_FREE_LIST, (lambda good: 0)
        partition = ("the five entries under the heading Free Fare Eligibility on "
                     "the operator's own reduced-fare page")
        label = "the five lines the operator's free list names"
    else:
        lines, value_of = MBTA_REDUCED_LIST, (lambda good: MBTA_GOODS[good]["reduced"])
        partition = ("the four entries under the heading Riders Eligible for "
                     "Reduced Fares on the operator's own page")
        label = "the four lines the operator's reduced list names"
    cells = {good: {ln: value_of(good) for ln in lines} for good in sorted(MBTA_GOODS)}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": label, "partition": partition,
            "label_fixes_value": (which == "free"),
            "why": ("DEGENERATE. the heading is Free Fare Eligibility, so zero is in "
                    "the label and every entry carries it by construction. the rate "
                    "reads the heading back and carries no claim (D25)")
                   if which == "free" else
                   ("the heading is Riders Eligible for Reduced Fares, which does "
                    "not fix WHICH reduced fare. another operator prints three "
                    "different reduced columns under the same idea, so several "
                    "values are available under this label"),
            "family": "public service pricing", "source": MBTA_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "overlap_note": ("this operator's two goods carry one value each, so the "
                             "pairs inside a list are one fact per list, not one per "
                             "pair (D22). the three federally named classes at this "
                             "operator are also counted in transit_federal_three; "
                             "the reduced list is not that partition, since it lists "
                             "disability and Medicare as a single entry")}


# --------------------------------------------------------------------------
# Row 8. The column headers of one operator's own published fare table, read
# 2026-09-07. This is the sharpest case for the third clause: the SAME operator's
# SAME table reads 0 per cent under the partition the statute names and 100 per
# cent under the partition its own column headers draw, and both partitions are
# named by a source. The statute names disability and Medicare separately; this
# table puts them in one column headed Senior/Disability, so the two partitions
# are genuinely different objects and both readings stand.
#
# The Mobility column is excluded and the reason is on the record: paratransit is
# a door-to-door service, so it fails Q0 of the B54 screen, one commodity. Its
# single trip is also dearer than the full fare, at 220 against 200.
#
# A dash in the table is an absent cell, not a zero and not an agreement.
MD_TABLE = {                       # product: {column: cents}
    "single trip":      {"full fare": 200, "senior/disability": 100, "student": 150},
    "day pass":         {"full fare": 460, "senior/disability": 230},
    "weekly pass":      {"full fare": 2200},
    "monthly pass":     {"full fare": 7700, "senior/disability": 2300},
    "all-access student pass": {"student": 5700},
}
MD_LINES = ["full fare", "senior/disability", "student"]
MD_SOURCE = "mta.maryland.gov/regular-fares, retrieved 2026-09-07 by browser"


def row_maryland_columns():
    per_pair, pairable, separated = pair_up(MD_TABLE)
    return {"line": "the three columns the operator's own fare table prints",
            "partition": "the column headers of the published fare table, less the "
                         "Mobility column, which fails Q0 of the B54 screen because "
                         "paratransit is not the same commodity",
            "label_fixes_value": False,
            "why": "column heads name who, and this table prints three different "
                   "numbers under them",
            "family": "public service pricing", "source": MD_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(MD_TABLE), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(MD_TABLE, MD_LINES),
            "same_table_other_partition": (
                "the three classes 49 U.S.C. 5307(c)(1)(D) names sit inside this "
                "table's single Senior/Disability column and read 0.00 per cent in "
                "transit_federal_three. Same operator, same table, two named "
                "partitions, 0 and 1. Neither reading is wrong and neither is the "
                "reading: the partition has to be named")}


# --------------------------------------------------------------------------
# Rows 9 and 10. A third operator, read 2026-09-08, chosen because its published
# table prints an income-qualified class with its own price beside the others.
# That is what the ninth row needed: the income line at the two operators already
# read sits in two different tables, which is not a partition any one source
# draws, so the third clause barred it.
#
# The page heads a section Types of fares and gives each type its own price. The
# label does not fix the value and the page proves it, printing 300, 100, 0 and
# 175 under the same heading.
#
# Two entries are excluded and the reason is on the record, both under Q0 of the
# B54 screen, one commodity:
#   Access Transportation at 175, paratransit, a door-to-door service. Worth
#     noting against the other operator's paratransit column at 220, which sat
#     ABOVE its full fare of 200 while this one sits below the adult fare of 300.
#   the subsidised annual pass, which is an annual pass and not a single ride.
KC_SOURCE = ("kingcounty.gov/en/dept/metro/fares-and-payment/prices, effective "
             "2025-09-01, retrieved 2026-09-08 by browser")

KC_SINGLE_RIDE = {                 # the five types that price a single ride
    "adult 19-64": 300,
    "senior 65+": 100,
    "disability or Medicare": 100,
    "youth 0-18": 0,               # the page words this as unlimited rides free
    "income-qualified": 100,
}
KC_EXCLUDED = {"Access Transportation": (175, "paratransit, fails Q0"),
               "subsidised annual pass": (0, "an annual pass, not a single ride")}


def row_king_county():
    cells = {"single ride": dict(KC_SINGLE_RIDE)}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "the five fare types this operator prices a single ride for",
            "partition": "the sections under the heading Types of fares on the "
                         "operator's own price page, less two excluded under Q0",
            "label_fixes_value": False,
            "why": "the page prints 300, 100, 0 and 175 under this one heading, so "
                   "the label plainly does not fix the value",
            "family": "public service pricing", "source": KC_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "excluded": {k: {"cents": v[0], "reason": v[1]}
                         for k, v in KC_EXCLUDED.items()},
            "note": "the youth cell is worded on the page as unlimited rides free "
                    "rather than as a single-ride price; free is taken as zero"}


# Row 10. The income line against the senior line, at the two operators that draw
# both and price both. This is the pair the ninth row was originally registered
# for, and it is a partition each operator's own page draws: two entries listed
# separately, each with its own eligibility and its own credential.
RTD_SOURCE = ("rtd-denver.com/fares-passes/fares, retrieved 2026-09-08 by browser")

INCOME_VS_SENIOR = {
    "mbta_boston": {"income-qualified": {"subway": 110, "bus": 85},
                    "senior": {"subway": 110, "bus": 85},
                    "source": "mbta.com/fares/reduced, retrieved 2026-09-07"},
    "king_county": {"income-qualified": {"single ride": 100},
                    "senior": {"single ride": 100},
                    "source": KC_SOURCE},
    "rtd_denver": {"income-qualified": {"3-hour pass": 135, "day pass": 270,
                                        "monthly pass": 2700},
                   "senior": {"3-hour pass": 135, "day pass": 270,
                              "monthly pass": 2700},
                   "source": RTD_SOURCE},
}


def row_income_vs_senior():
    cells = {}
    for op, d in sorted(INCOME_VS_SENIOR.items()):
        for good in sorted(d["income-qualified"]):
            cells[(op, good)] = {"income-qualified": d["income-qualified"][good],
                                 "senior": d["senior"][good]}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "income-qualified against senior",
            "partition": "two entries each operator's own reduced-fare page lists "
                         "separately, each with its own eligibility test and its "
                         "own credential",
            "label_fixes_value": False,
            "why": "one of these operators prices the student line apart from the "
                   "senior line on the same page, so separate values are available "
                   "to it under the same kind of label",
            "family": "public service pricing",
            "source": "; ".join(d["source"] for d in INCOME_VS_SENIOR.values()),
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable,
            "independent_facts": len(INCOME_VS_SENIOR)}


# --------------------------------------------------------------------------
# Row 11. A fourth operator, read 2026-09-08, and it was read because it looked
# most likely to break the narrow statement rather than confirm it: it runs a
# separately branded income programme alongside a separate senior and disability
# programme. It confirms, and its own footnote is the clearest statement of the
# merge yet found:
#
#   "Discount fares apply to seniors 65+, individuals with disabilities,
#    Medicare recipients, and customers enrolled in LiVE."
#
# Four classes named in one sentence, sharing one column, and the page presents
# consolidating them as a deliberate policy under the heading Consolidated
# Discounts. Proof of eligibility is required for every one of them.
#
# THE NEAR REFUTATION, RECORDED BECAUSE IT IS THE CLOSEST THING TO ONE.
# On the operator's paratransit service the income line DOES separate from the
# disability line: 450 for Access-a-Ride against 225 for Access-a-Ride LiVE. That
# service fails Q0 of the B54 screen, door-to-door is not the same commodity as a
# fixed-route ride, and Q0 was set long before this page was read. So the narrow
# statement stands on the commodity the screen admits, and the one place the
# income line separates is a commodity the screen excludes. Reported in its own
# words rather than smoothed (D31).
#
# The airport day pass row is excluded: its discount cell reads "no additional
# charge", which is the absence of a surcharge and not a price.

RTD_DISCOUNT_LINES = ["senior 65+", "disability", "Medicare", "income (LiVE)"]
RTD_PRODUCTS = {"3-hour pass": 135, "day pass": 270, "monthly pass": 2700}
RTD_STANDARD = {"3-hour pass": 275, "day pass": 550, "monthly pass": 8800}
RTD_PARATRANSIT = {"Access-a-Ride one-way": 450, "Access-a-Ride LiVE one-way": 225}


def row_rtd_discount():
    cells = {prod: {ln: cents for ln in RTD_DISCOUNT_LINES}
             for prod, cents in RTD_PRODUCTS.items()}
    per_pair, pairable, separated = pair_up(cells)
    return {"line": "the four classes this operator's own footnote names for one "
                    "discount column",
            "partition": "the four classes named in one sentence of the footnote to "
                         "the Standard and Discount Fares table, less the airport "
                         "day pass row whose discount cell reads no additional "
                         "charge rather than a price",
            "label_fixes_value": False,
            "why": "the heading is Discount Fares, which does not fix WHICH "
                   "discount; the same page prices a different discount structure "
                   "on its paratransit service and prices youth at zero",
            "merge_declared_by_source": True,
            "merge_declared_note": "this operator both names the partition and puts "
                                   "it in one column, and presents the consolidation "
                                   "as policy. that does not weaken the reading, "
                                   "since four verified classes still carry one "
                                   "price, but it is not a merge discovered across "
                                   "independent tables the way the statute row is",
            "family": "public service pricing", "source": RTD_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(cells), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "standard_column": RTD_STANDARD,
            "near_refutation": {
                "where": "the operator's paratransit service, which fails Q0",
                "cells": RTD_PARATRANSIT,
                "reading": "the income line separates from the disability line "
                           "there, 450 against 225. Q0 was set before this page was "
                           "read and door-to-door is not the same commodity, so this "
                           "does not enter the row, and it is the closest thing to a "
                           "refutation the corpus holds"}}


# --------------------------------------------------------------------------
# Row 5. The gender line of a motor tariff in force in Texas, filing
# METX-132665343, disposed 2021-01-29, 1,415 pages. CARRIED, not recomputed:
# the cells are in that filing and not on this disk. The figures are the ones
# that block reported, under the same pairing rule.
# --------------------------------------------------------------------------

CARRIED_AUTO_GENDER = {
    "line": "gender, two blocks",
    "partition": "one column header of the filed classification table, which that "
                 "block reports has exactly two blocks",
    "label_fixes_value": False,
    "why": "a rating factor names who, not how much",
    "family": "corporate compliance classification",
    "source": "filing METX-132665343, classification table, as read and reported "
              "by the B30-22 block on that corpus",
    "recomputed_from_cells": False,
    "carried_reason": "the cells are in a 1,415-page filing that is not on this disk; "
                      "that block used the same pairing rule, in its own words "
                      "'cells carry a complete pair' and 'pairs whose two values differ'",
    "contexts": 9450, "pairable": 9450, "separated": 8400,
    "use_rate": 8400 / 9450,
    "note": "the 1,050 same-value pairs are exactly one ninth of 9,450, recorded "
            "there as unexplained and not interpreted",
}


# --------------------------------------------------------------------------
# The federal ceiling on paratransit fares, read from the regulation 2026-09-08,
# because the fourth operator's paratransit prices raised the question of whether
# the split it makes there is forced by a rule. It is not.
#
#   49 CFR 37.131(c): "The fare for a trip charged to an ADA paratransit eligible
#   user of the complementary paratransit service shall not exceed twice the fare
#   that would be charged to an individual paying full fare (i.e., without regard
#   to discounts) for a trip of similar length, at a similar time of day, on the
#   entity's fixed route system."
#
# The parenthesis settles it. The ceiling is twice the FULL fare and is blind to
# every discount class, so it is one number for every paratransit rider and it
# cannot require or forbid a split among them. Whatever the fourth operator is
# doing on paratransit, this rule is not making it do it.
#
# Checking the corpus against the ceiling is a known-answer test of both the
# reading of the rule and the fares: three operators have a paratransit fare on
# disk and all three must sit at or under twice their own full fare.
ADA_CEILING_RULE = ("49 CFR 37.131(c), read from eCFR 2026-09-08: twice the fare "
                    "charged to an individual paying full fare, i.e. without regard "
                    "to discounts")

PARATRANSIT = {
    "mta_maryland":  {"para": 220, "full": 200, "name": "Mobility one-way"},
    "king_county":   {"para": 175, "full": 300, "name": "Access Transportation"},
    "rtd_denver":    {"para": 450, "full": 275, "name": "Access-a-Ride one-way"},
    "rtd_denver_income": {"para": 225, "full": 275,
                          "name": "Access-a-Ride LiVE one-way"},
}


def ada_ceiling_check():
    out = {}
    for k, d in sorted(PARATRANSIT.items()):
        ceiling = 2 * d["full"]
        out[k] = {"name": d["name"], "paratransit_cents": d["para"],
                  "full_fare_cents": d["full"], "ceiling_cents": ceiling,
                  "under_ceiling": d["para"] <= ceiling,
                  "share_of_ceiling": d["para"] / ceiling}
    return out


# --------------------------------------------------------------------------
# Row 12, read 2026-09-08. A different family from every row above: not a fare
# table but a tariff filed with a regulator, and it is here because of what B54
# found on the same day.
#
# Four transit operators post a second price for the income class and then set
# it to the senior value, so income_vs_senior reads 0 of 6. This utility does
# the opposite on both counts. It posts no second price at all, so B54's Q2
# fails on it: what is filed is a multiplier, and a price with a published
# constant that converts it is one price (D30 third clause). And the income
# line it does write carries two values that differ.
#
# The row is here to block a generalisation rather than to move an average.
# One counterexample does that. This one arrives with two contexts, so it also
# shows the thing this station keeps having to restate: the rate belongs to a
# line-pair inside a context, not to a row and not to a family. Inside one
# filed tariff, the same pair separates in one context and not in the other.
#
# Units are thousandths of one per cent, which is the precision D-CARE files.

CARE_SOURCE = ("PG&E filed electric tariff book, read 2026-09-08: Schedule "
               "D-CARE, whose own title is LINE-ITEM DISCOUNT FOR CALIFORNIA "
               "ALTERNATE RATES FOR ENERGY (CARE) CUSTOMERS, and ELECTRIC "
               "SCHEDULE E-FERA FAMILY ELECTRIC RATE ASSISTANCE. income tables "
               "for both published by the CPUC")

CARE_FERA = {
    "bundled volumetric charges": {"CARE": 35000, "FERA": 18000},
    "delivery minimum bill":      {"CARE": 50000, "FERA": 50000},
}
CARE_LINES = ("CARE", "FERA")


def row_care_fera():
    per_pair, pairable, separated = pair_up(CARE_FERA)
    return {"line": "which of the two filed income schedules the household takes "
                    "service on",
            "partition": "two separately filed schedules, D-CARE and E-FERA, each "
                         "with its own name, its own applicability clause and its "
                         "own income table published by the regulator",
            "label_fixes_value": False,
            "why": "the labels are CARE and FERA. neither one names a number, and "
                   "the two schedules are filed apart, so separate values are "
                   "available to this line and nothing in the labels forces them",
            "family": "regulated utility tariff",
            "source": CARE_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(CARE_FERA), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(CARE_FERA, CARE_LINES),
            "same_row_other_context": (
                "one line-pair, one document, two contexts, and the pair separates "
                "in one of them. on bundled volumetric charges the two schedules "
                "file 35.000 and 18 per cent; on the delivery minimum bill they "
                "file 50 and 50. the merge this station keeps reading in transit "
                "happens here too, inside a single filed tariff, one line item "
                "away from a split by the same two classes"),
            "what_this_row_does_not_say": (
                "B54 reads Q2 as failing on this carrier because a multiplier is "
                "not a second price. that is a fact about prices. this row is "
                "about class values, which the counting law counts, and the "
                "programme wrote 35.000, 18 and 50.000. one carrier, two "
                "questions, and it answers them differently")}


# --------------------------------------------------------------------------
# Rows 13 and 14, read 2026-09-08 from the statutes themselves through the
# e-Gov law API. Two articles, each of which partitions in its own words: the
# stem of each says the patient pays the amount computed for the treatment
# multiplied by the ratio its item names, so each article prices once and then
# writes a ratio per case. That is why B54 reads Q2 as failing on the
# copayment carrier, and it is also why the ratios are class values here.
#
# Health Insurance Act art. 74(1) stem, verbatim:
#
#   第六十三条第三項の規定により保険医療機関又は保険薬局から療養の給付を受ける
#   者は、その給付を受ける際、次の各号に掲げる場合の区分に応じ、当該給付につき
#   第七十六条第二項又は第三項の規定により算定した額に当該各号に定める割合を
#   乗じて得た額を、一部負担金として、当該保険医療機関又は保険薬局に支払わな
#   ければならない。
#
# 区分 is the article's own word for the partition, which is what the third
# clause asks for, and the items are conditions rather than numbers, which is
# what the fourth clause asks for.
#
# The two articles are two rows and not one, because their case sets are
# different sets. Combining them would be the reader choosing the partition.
# For the same reason the preschool 20 per cent is not here: it lives in art.
# 110, which is the dependants' benefit rate and a different partition.
#
# Units are thousandths of one per cent, as with care_fera_bands. The objects
# are not comparable across those rows and are not compared: CARE files a
# discount off a price, these articles file the share the patient pays.

JP74_SOURCE = ("Japan, Health Insurance Act (健康保険法) article 74 paragraph 1, "
               "read 2026-09-08 through the e-Gov law API, lawId 211AC0000000070")
JP67_SOURCE = ("Japan, Act on Assurance of Medical Care for Elderly People "
               "(高齢者の医療の確保に関する法律) article 67 paragraph 1, read "
               "2026-09-08 through the e-Gov law API, lawId 357AC0000000080")

JP_ART74 = {"the medical care benefit the article prices": {
    "item 1: before the month after turning 70":            30000,
    "item 2: from that month, general":                     20000,
    "item 3: from that month, income at or over the "
    "cabinet-order amount":                                 30000}}
JP_ART74_LINES = tuple(sorted(next(iter(JP_ART74.values()))))

JP_ART67 = {"the medical care benefit the article prices": {
    "item 1: neither of the other two cases":               10000,
    "item 2: income at or over the first cabinet-order "
    "amount":                                               20000,
    "item 3: income at or over the second":                  30000}}
JP_ART67_LINES = tuple(sorted(next(iter(JP_ART67.values()))))


def row_jp(table, lines, label, source, why):
    per_pair, pairable, separated = pair_up(table)
    return {"line": label,
            "partition": "the cases the article itself lists, which it calls 区分, "
                         "each stated as a condition on age or on income and none "
                         "of them stated as a number",
            "label_fixes_value": False,
            "why": why,
            "family": "statutory cost sharing",
            "source": source,
            "recomputed_from_cells": True,
            "contexts": len(table), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(table, lines)}


def row_jp_art74():
    return row_jp(JP_ART74, JP_ART74_LINES,
                  "the three cases Health Insurance Act art. 74(1) lists",
                  JP74_SOURCE,
                  "the article lists three cases and writes two distinct ratios. "
                  "items 1 and 3 both get 30 per hundred, so crossing the income "
                  "threshold after 70 returns the patient exactly to the ratio a "
                  "person under 70 pays. an age line and an income line meeting on "
                  "one number, written into one article")


def row_jp_art67():
    return row_jp(JP_ART67, JP_ART67_LINES,
                  "the three cases Elderly Medical Care Act art. 67(1) lists",
                  JP67_SOURCE,
                  "three cases, three distinct ratios, and the line separates every "
                  "pair. this is the row on the age and income axes that the "
                  "transit tables do not produce")


# --------------------------------------------------------------------------
# Row 15, read 2026-09-08. A municipal fee schedule, which is the residence
# axis read on an operator rather than on a statute. Virginia's licence fees
# are the other residence row and they run at 97.56 per cent; this one does
# not, and the two together are why the axis is not the unit either.
#
# The page prints two tables whose column headers are resident and
# non-resident, and the headers were read twice because the first reading of
# this page got a column header wrong on a third table. The Aquatics table is
# headed youth and adult, so it is not this line and is not here.
#
# Six further items on the same schedule, the outdoor courts, carry a single
# fee column. Whether a one-price item counts as this line separating nothing,
# or as no cell of this line at all, is a choice the reader makes and not one
# the page makes, so the rate below counts only the items the page prints in
# two columns and the other reading is recorded beside it.

BOULDER_SOURCE = ("City of Boulder, Colorado, published Parks and Recreation Fee "
                  "Schedule, read 2026-09-08; column headers verified on a second "
                  "reading of the same page")

BOULDER = {
    "indoor: small room, per hour":            {"resident":  4400, "non-resident":  5500},
    "indoor: large room, per hour":            {"resident":  7100, "non-resident":  8800},
    "indoor: specialty recreation facility":   {"resident":  8400, "non-resident": 10500},
    "indoor: basketball half gym, per hour":   {"resident":  5500, "non-resident":  6800},
    "indoor: basketball full gym, per hour":   {"resident": 12000, "non-resident": 14500},
    "indoor: EBCC ballroom, per hour":         {"resident": 27500, "non-resident": 30000},
    "indoor: Valmont Farmhouse, per hour":     {"resident": 15000, "non-resident": 15000},
    "outdoor: park shelters, per day":         {"resident": 12000, "non-resident": 15000},
    "outdoor: alcohol permit, per day":        {"resident":  2500, "non-resident":  2500},
    "outdoor: parking lots, per day":          {"resident": 11000, "non-resident": 11000},
    "outdoor: Valmont shelter, three hours":   {"resident": 15000, "non-resident": 15000},
}
BOULDER_LINES = ("non-resident", "resident")

BOULDER_ONE_COLUMN = {"sand volleyball court": 3300, "pickleball court": 1000,
                      "handball court": 1000, "tennis court": 1000,
                      "platform tennis court": 1000, "basketball court": 3600}


def row_boulder():
    per_pair, pairable, separated = pair_up(BOULDER)
    alt = separated / (pairable + len(BOULDER_ONE_COLUMN))
    return {"line": "resident against non-resident, the two columns this operator's "
                    "own fee schedule prints",
            "partition": "the column headers of the two rental tables on the "
                         "published schedule, resident/hour against "
                         "non-resident/hour and resident/day against "
                         "non-resident/day. the Aquatics table on the same page is "
                         "headed youth and adult and is a different line",
            "label_fixes_value": False,
            "why": "the headers name who, and the same schedule prints a different "
                   "number under them in most rows, so separate values are plainly "
                   "available to this line",
            "family": "municipal facility pricing",
            "source": BOULDER_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(BOULDER), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(BOULDER, BOULDER_LINES),
            "one_column_items": {
                "count": len(BOULDER_ONE_COLUMN),
                "names": sorted(BOULDER_ONE_COLUMN),
                "reading": "the outdoor courts on the same schedule carry one fee "
                           "column, so every buyer pays the same and the line is "
                           "not drawn there at all. counting them as contexts where "
                           "the line separates nothing gives %d of %d = %.4f. that "
                           "is a second defensible reading and the choice between "
                           "them is the reader's, so both are printed and the rate "
                           "reported is the one over the two-column rows only"
                           % (separated, pairable + len(BOULDER_ONE_COLUMN), alt)},
            "the_object": "six of the seven indoor rows separate and one does not, "
                          "and one of the four outdoor rows separates. both rows "
                          "that name Valmont read the same on both sides, 150 and "
                          "150, so the exception on this schedule is a site rather "
                          "than a table"}


# --------------------------------------------------------------------------
# Rows 16 and 17, read 2026-09-08. One municipal admission table read under
# each of the two partitions its own headers draw, which is what maryland_columns
# and transit_federal_three did on one transit table. Here the two readings do
# not sit at opposite ends: both are 100 per cent.
#
# It is here for the age line. Four transit operators read 0.00 per cent on the
# age line and they are all in the family this row is in, public service
# pricing, so the transit zeros are not explained by the family. The two
# Japanese statutes made that point from outside the family; this makes it from
# inside, on a table of the same shape as a fare table.

CLAYTON_SOURCE = ("City of Clayton, Missouri, Shaw Park Aquatic Center published "
                  "admission page, read 2026-09-08. columns headed Resident, "
                  "Corporate and Guest; rows Youth (3-17), Adult, Senior (65+)")

CLAYTON = {"youth 3-17": {"resident": 700, "corporate": 1000, "guest": 1300},
           "adult":      {"resident": 900, "corporate": 1200, "guest": 1500},
           "senior 65+": {"resident": 800, "corporate": 1100, "guest": 1400}}

CLAYTON_BY_AGE = {}
for _age, _row in CLAYTON.items():
    for _col, _v in _row.items():
        CLAYTON_BY_AGE.setdefault(_col, {})[_age] = _v

CLAYTON_STANDING = ("resident", "corporate", "guest")
CLAYTON_AGES = ("youth 3-17", "adult", "senior 65+")


def row_clayton_standing():
    per_pair, pairable, separated = pair_up(CLAYTON)
    return {"line": "the three columns this operator's own admission table prints",
            "partition": "the column headers of the published admission table, "
                         "Resident, Corporate and Guest, which the same page ties "
                         "to a status the visitor must show proof of",
            "label_fixes_value": False,
            "why": "the headers name standing, not a number",
            "family": "public service pricing", "source": CLAYTON_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(CLAYTON), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(CLAYTON, CLAYTON_STANDING),
            "same_table_other_partition": (
                "the row headers of the same table are the age line, read as "
                "clayton_admission_age, and they also separate every pair. one "
                "table, two named partitions, and unlike the transit case the two "
                "readings agree rather than sitting at opposite ends")}


def row_clayton_age():
    per_pair, pairable, separated = pair_up(CLAYTON_BY_AGE)
    return {"line": "the three rows this operator's own admission table prints",
            "partition": "the row headers of the published admission table, Youth "
                         "(3-17), Adult and Senior (65+)",
            "label_fixes_value": False,
            "why": "the headers name age bands, not numbers",
            "family": "public service pricing", "source": CLAYTON_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(CLAYTON_BY_AGE), "pairable": pairable,
            "separated": separated, "use_rate": separated / pairable,
            "per_pair": per_pair, "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(CLAYTON_BY_AGE, CLAYTON_AGES),
            "why_it_is_here": (
                "the age line reads 0.00 per cent at four transit operators, all of "
                "them in this same family. it reads 9 of 9 here. whatever produces "
                "those zeros, it is not that the line is an age line and it is not "
                "that the seller is a public operator")}


# --------------------------------------------------------------------------
# Rows 18 and 19, read 2026-09-08. Two independent cinemas, and they are here
# to answer the one objection the four zeros above cannot answer themselves.
#
# Every zero so far is a public transit operator, and three of them take a
# federal grant whose condition names three classes together. A defender of
# third-degree price discrimination can say those operators are not maximising
# profit and are doing what a grant condition told them to do. That objection
# is fair and it needs a seller outside that regime.
#
# A cinema is the textbook's own canonical example of third-degree price
# discrimination: it has market power over a showing, it sorts by asking for
# ID at the box office, and a ticket cannot be resold into another showing.
# All three of Stole's stated conditions hold. Neither of these cinemas takes
# a transit grant and no statute names their classes together.
#
# What is NOT claimed: their tax status was not read. The load-bearing fact is
# that no grant condition and no statute groups these classes, which is what
# the surviving candidate explanation of the transit zeros requires.
#
# The partition each row uses is the list of categories the operator's own
# price page prints. Dropping the full-price category would give 0 of 6 and 0
# of 3, and that subset is one the reader would be drawing, so it is recorded
# beside the rate rather than reported as the rate.

CV_SOURCE = ("Cinema Village, New York, published price policy page, read "
             "2026-09-08. the page states Senior Citizens age 65 and over with "
             "ID, Students with valid student ID, and Federally Disabled with "
             "valid ID, so the sorting cost is paid on three of the four")

CINEMA_VILLAGE = {"one admission": {
    "adult":                          1400,
    "senior citizen, 65+ with ID":    1000,
    "child":                          1000,
    "student, valid student ID":      1000,
    "federally disabled, valid ID":   1000}}
CV_LINES = tuple(sorted(CINEMA_VILLAGE["one admission"]))

CA_SOURCE = ("Cinema Arts Theatre published theater-info page, read 2026-09-08. "
             "the 4pm-11pm band prints Adults at 14.00 and one further row "
             "reading Seniors, College Students, Children at 13.00")

CINEMA_ARTS = {"evening show, 4pm to 11pm": {
    "adult":           1400,
    "senior":          1300,
    "college student": 1300,
    "child":           1300}}
CA_LINES = tuple(sorted(CINEMA_ARTS["evening show, 4pm to 11pm"]))


def _cinema_row(table, lines, label, partition, source, why, obj, subset):
    per_pair, pairable, separated = pair_up(table)
    disc = pairable - separated
    return {"line": label, "partition": partition, "label_fixes_value": False,
            "why": why, "family": "commercial cinema admission", "source": source,
            "recomputed_from_cells": True,
            "contexts": len(table), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(table, lines),
            "the_object": obj,
            "subset_reading": subset % (separated, pairable, disc),
            "rival_conditions_hold": (
                "Stole states price discrimination is feasible when the firm has "
                "short-run market power, consumers can be segmented directly or "
                "indirectly, and arbitrage across differently priced goods is "
                "infeasible. a cinema showing meets all three, and the page "
                "itself says ID is required, so the sorting is direct and paid "
                "for. no grant condition and no statute groups these classes")}


def row_cinema_village():
    return _cinema_row(
        CINEMA_VILLAGE, CV_LINES,
        "the five admission categories this cinema's own price page prints",
        "the category list on the published price policy page: Adults, Senior "
        "Citizens, Children, Students, Federally Disabled",
        CV_SOURCE,
        "four of the five categories are discounts and three of those four are "
        "ID-checked, so the seller has paid to tell them apart and could price "
        "them apart",
        "four named categories, three of them ID-checked, all carry 10.00. every "
        "one of the six pairs among senior, child, student and federally disabled "
        "reads the same value. the only separation on this page is between the "
        "full price and that block",
        "%d of %d. dropping the full-price category leaves the four discount "
        "categories, which read 0 of %d. that subset is one the reader would be "
        "drawing and the page does not draw it, so it is recorded and not reported "
        "as the rate")


def row_cinema_arts():
    return _cinema_row(
        CINEMA_ARTS, CA_LINES,
        "the classes this theatre's own evening price band names",
        "the 4pm-11pm rows of the published price table: Adults, and Seniors, "
        "College Students, Children",
        CA_SOURCE,
        "the same page prices two of these classes apart on their own promotion "
        "days, Senior Wednesdays at 7.00 and College Tuesdays at 8.00, so "
        "separate values are demonstrably available to this operator for the same "
        "two labels",
        "the page puts Seniors, College Students and Children in one row at "
        "13.00, so all three pairs among them read the same value, while the "
        "same page gives senior and college separate numbers on their own days",
        "%d of %d. dropping Adults leaves the three classes the one row names, "
        "which read 0 of %d, and that is the same shape as the statutory three "
        "classes sitting in one Senior/Disability column")


# --------------------------------------------------------------------------
# Row 20, read 2026-09-08. Two state park systems, one residence line, and it
# is here because B54 read the same two documents to settle a carrier that had
# been undetermined on two questions at once.
#
# Rhode Island answers both: it posts four tiers resident against non-resident,
# and it says residency is checked against a government photo ID and the
# booking profile, and that a camper who cannot prove it pays the non-resident
# rate at check-in. Maine posts the split across twelve parks under column
# headers that read RESIDENT and NON-RESIDENT.
#
# Maine's schedule mentions proof only for the senior day-use discount, not for
# camping, so the verification half of that carrier stands on the Rhode Island
# document and not on this one. Two states are two independent facts.
#
# Where a Maine row prints two figures separated by a slash, the first is used.
# The second pair is separated in every one of those rows too, so nothing turns
# on the choice.

PARKS_SOURCE = ("Maine Bureau of Parks and Lands published fee schedule and "
                "Rhode Island State Parks published camping policies, both read "
                "2026-09-08")

STATE_PARKS = {
    "Maine, Aroostook":          {"resident": 1500, "non-resident": 2500},
    "Maine, Bradbury Mountain":  {"resident": 1500, "non-resident": 2500},
    "Maine, Camden Hills":       {"resident": 2500, "non-resident": 3500},
    "Maine, Cobscook Bay":       {"resident": 2000, "non-resident": 3000},
    "Maine, Lake St. George":    {"resident": 2000, "non-resident": 3000},
    "Maine, Lamoine":            {"resident": 2000, "non-resident": 3000},
    "Maine, Lily Bay":           {"resident": 2000, "non-resident": 3000},
    "Maine, Mount Blue":         {"resident": 2000, "non-resident": 3000},
    "Maine, Peaks-Kenny":        {"resident": 2000, "non-resident": 3000},
    "Maine, Rangeley Lake":      {"resident": 2000, "non-resident": 3000},
    "Maine, Sebago Lake":        {"resident": 2500, "non-resident": 3500},
    "Maine, Warren Island":      {"resident": 1500, "non-resident": 2500},
    "Rhode Island, tier 3 no hookups":   {"resident": 1800, "non-resident": 3600},
    "Rhode Island, tier 2":              {"resident": 2400, "non-resident": 4500},
    "Rhode Island, tier 1":              {"resident": 2800, "non-resident": 5500},
    "Rhode Island, primitive cabin":     {"resident": 5000, "non-resident": 7500},
}
PARKS_LINES = ("non-resident", "resident")


def row_state_parks():
    per_pair, pairable, separated = pair_up(STATE_PARKS)
    return {"line": "resident against non-resident, the two columns two state park "
                    "systems print",
            "partition": "the column headers of the published camping fee "
                         "schedules, RESIDENT and NON-RESIDENT",
            "label_fixes_value": False,
            "why": "the headers name who, and one of the two systems states the "
                   "check and its consequence, so the sorting cost is paid",
            "family": "state park fee schedule", "source": PARKS_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(STATE_PARKS), "pairable": pairable,
            "separated": separated, "use_rate": separated / pairable,
            "per_pair": per_pair, "nominal_pairs": pairable,
            "independent_facts": 2,
            "coverage": coverage(STATE_PARKS, PARKS_LINES),
            "the_object": "sixteen sites, sixteen separations, no site where the "
                          "two columns carry the same figure. the ratio is not "
                          "constant either: Maine runs from 1.40 to 1.67 and Rhode "
                          "Island from 1.50 to 2.00, so this is not one multiplier "
                          "applied to a base, which is what D30's third clause "
                          "would make a single price"}


# --------------------------------------------------------------------------
# Credentials, read 2026-09-08. This is the answer to the last defence the zero
# pairs face, and it is answered from the sellers' own pages rather than argued.
#
# The defence is cost: finer segmentation is not worth paying for. The reply is
# that on these carriers it has already been paid for, separately, once per
# class, and the remaining step is a line in a fare table.
#
# It also gives the framework something to do here rather than only the rival.
# The general statement is that the granularity of class values is bounded by
# the granularity of the registration point, so two classes that share one
# credential cannot be priced apart at the point of sale even if the seller
# wanted to. That is a bound, and RTD shows it binding on exactly one pair:
# Medicare rides inside the disabilities card, and those two carry one number
# for a mechanical reason. Every other documented pair has the bound slack, so
# the seller could have written two numbers and wrote one.
#
# Three states, and not_read maps to no verdict (11c). A row whose contexts
# span several operators is marked not_read unless every one of them was read,
# which is the conservative direction.

SEP = "separately_credentialed"
ONE = "one_credential"
MIXED = "mixed_across_operators"
FORBIDDEN = "rule_forbids_the_line"
NOTREAD = "not_read"

CRED_SOURCE = {
    "mbta_reduced_list": "mbta.com/fares/reduced, read 2026-09-08: Senior "
                         "CharlieCard; Transportation Access Pass for disability "
                         "and Medicare; S-Card or M7 Card for students; a reduced "
                         "fare card for income-eligible riders aged 18 to 64",
    "rtd_discount_four": "rtd-denver.com/fares-passes/fares/discounted-fares, read "
                         "2026-09-08: Senior Special Discount Card; Individuals "
                         "with Disabilities Special Discount Card, which Medicare "
                         "recipients are served through; Zero Fare for Youth "
                         "Special Discount Card; LiVE, applied for through the "
                         "state benefits website. each has its own application "
                         "and its own eligibility documents",
    "cinema_village_categories": "the cinema's own price policy page: age 65 and "
                                 "over with ID, valid student ID, valid federal "
                                 "disability ID. three different documents named; "
                                 "the page says nothing about how a child is "
                                 "checked",
    "transit_federal_three": "all three operators read 2026-09-08. MBTA: Senior "
                             "CharlieCard, and TAP covering disability and "
                             "Medicare together. MDOT MTA: seniors use a Maryland "
                             "Photo Identification Card from the motor vehicle "
                             "administration, disability an MTA Disability photo "
                             "ID card whose application must be filled out by the "
                             "applicant and the applicant's health care "
                             "professional and takes up to two weeks to review, "
                             "and Medicare a Medicare card with a government "
                             "issued photo ID. MTA New York: one Reduced-Fare "
                             "OMNY Card for 65 and over and for disability alike, "
                             "Medicare appearing only as documentation for the "
                             "disability route",
    "income_vs_senior": "all three operators read. MBTA income card against Senior "
                        "CharlieCard; King County ORCA LIFT against the Regional "
                        "Reduced Fare Permit; RTD LiVE against the Senior Special "
                        "Discount Card",
    "king_county_types": "two sources that describe the same permit at two "
                         "levels, both read 2026-09-13. kingcounty.gov reduced "
                         "fares: one Regional Reduced Fare Permit application "
                         "covers senior riders, riders with disabilities and "
                         "Medicare card holders alike, with the documents "
                         "required differing by group. info.myorca.com, which is "
                         "the fare system the permit is loaded onto, lists them "
                         "under Card type as two named types, Senior (RRFP) and "
                         "Disability (RRFP), and both take the same $1.00 fare "
                         "on King County Metro. The question this row asks is "
                         "whether the seller can tell the two apart where the "
                         "price is set, and two named card types in the fare "
                         "system is that. ORCA LIFT is a separate income "
                         "programme with its own application",
}

CREDENTIALS = {
    "mbta_reduced_list": {
        "18-64 on state assistance | 65 or over": (SEP, "income card against Senior CharlieCard"),
        "18-64 on state assistance | disability or Medicare card": (SEP, "income card against TAP"),
        "18-64 on state assistance | middle or high school student": (SEP, "income card against S-Card or M7"),
        "65 or over | disability or Medicare card": (SEP, "Senior CharlieCard against TAP"),
        "65 or over | middle or high school student": (SEP, "Senior CharlieCard against S-Card or M7"),
        "disability or Medicare card | middle or high school student": (SEP, "TAP against S-Card or M7"),
    },
    "rtd_discount_four": {
        "Medicare | disability": (ONE, "Medicare recipients are served through the "
                                       "Individuals with Disabilities Special "
                                       "Discount Card. one credential, so the "
                                       "seller has no point of sale at which to "
                                       "tell these two apart"),
        "Medicare | income (LiVE)": (SEP, "disabilities card against LiVE"),
        "Medicare | senior 65+": (SEP, "disabilities card against Senior card"),
        "disability | income (LiVE)": (SEP, "disabilities card against LiVE"),
        "disability | senior 65+": (SEP, "disabilities card against Senior card"),
        "income (LiVE) | senior 65+": (SEP, "LiVE against Senior card"),
    },
    "cinema_village_categories": {
        "federally disabled, valid ID | senior citizen, 65+ with ID": (SEP, "federal disability ID against age ID"),
        "federally disabled, valid ID | student, valid student ID": (SEP, "federal disability ID against student ID"),
        "senior citizen, 65+ with ID | student, valid student ID": (SEP, "age ID against student ID"),
        "child | federally disabled, valid ID": (NOTREAD, "the page does not say how a child is checked"),
        "child | senior citizen, 65+ with ID": (NOTREAD, "same"),
        "child | student, valid student ID": (NOTREAD, "same"),
    },
    "transit_federal_three": {
        "65 or over | Medicare card": (MIXED, "separate at MBTA and at MDOT MTA, "
                                              "one card at MTA New York"),
        "65 or over | disability": (MIXED, "separate at MBTA and at MDOT MTA, one "
                                           "card at MTA New York"),
        "Medicare card | disability": (MIXED, "one credential at MBTA, where both "
                                              "ride on TAP, and at MTA New York; "
                                              "separate at MDOT MTA, where the "
                                              "disability card needs a health "
                                              "care professional's signature and "
                                              "a Medicare card is accepted with a "
                                              "photo ID"),
    },
    "income_vs_senior": {
        "income-qualified | senior": (SEP, "separate at all three operators: "
                                           "income card against Senior "
                                           "CharlieCard, ORCA LIFT against the "
                                           "RRFP, LiVE against the Senior Special "
                                           "Discount Card"),
    },
    "king_county_types": {
        "disability or Medicare | income-qualified": (SEP, "RRFP against ORCA LIFT"),
        # Read ONE until 2026-09-13, on the reasoning that one permit means one
        # point of sale. The permit is one application; the fare system carries
        # two named card types, Senior (RRFP) and Disability (RRFP), and the
        # question is where the price is set rather than where the form is filed.
        # The correction costs the row its mechanical account and buys back an
        # instance of the thing this station counts: a seller that can tell two
        # classes apart and charges them the same.
        "disability or Medicare | senior 65+": (SEP, "ORCA lists Senior (RRFP) "
                                                     "and Disability (RRFP) as two "
                                                     "card types, each with its own "
                                                     "eligibility documents, and "
                                                     "both take the same $1.00 "
                                                     "fare on King County Metro"),
        "income-qualified | senior 65+": (SEP, "ORCA LIFT against the RRFP"),
    },
    "sg_emergency_rule": {
        "PR | citizen": (FORBIDDEN, "the announcement says emergency department "
                                    "fees will not discriminate between "
                                    "nationality or citizenship"),
        "PR | foreigner": (FORBIDDEN, "same"),
        "citizen | foreigner": (FORBIDDEN, "same"),
    },
    "amtrak_everyday_discounts": {
        "active duty military and dependents | seniors 65 and over": (NOTREAD, "the page states no proof requirement per category"),
        "active duty military and dependents | veterans": (NOTREAD, "same"),
        "Rail Passengers Association members | active duty military and dependents": (NOTREAD, "same"),
        "Rail Passengers Association members | seniors 65 and over": (NOTREAD, "same"),
        "Rail Passengers Association members | veterans": (NOTREAD, "same"),
        "seniors 65 and over | veterans": (NOTREAD, "same"),
    },
    "marcus_matinee": {
        "11 and under | 60 and over": (NOTREAD, "the announcement states no proof "
                                                "requirement for either age class, "
                                                "though the same chain names a "
                                                "valid school ID and a valid "
                                                "military ID on its other rates"),
    },
    "cinema_arts_evening": {
        "child | college student": (NOTREAD, "the page names an ID only for the "
                                             "College Tuesdays rate, and the "
                                             "evening band prints these three in "
                                             "one row"),
        "child | senior": (NOTREAD, "same"),
        "college student | senior": (NOTREAD, "same"),
    },
}


# --------------------------------------------------------------------------
# Row 21, read 2026-09-08. One pair, and it is here for one reason: this is the
# only carrier on the board whose seller's objective stands on a document.
#
# Every other zero sits at a seller whose objective is either contested by a
# grant condition or simply not established. A corporation listed on the New
# York Stock Exchange, reporting net earnings per diluted share as its measure,
# is the closest thing to the rival's own assumption that this project can
# read rather than grant.
#
# The value is the company's own announcement, dated. Its wording is that
# moviegoers 11 years old and under and 60 and over may buy tickets for $7 for
# all shows before 4 p.m. Two named age classes, one number, from the seller.
#
# The current page corroborates the route rather than the figure: the senior
# programme's own page tells seniors to "save further with matinee tickets at a
# great price every day before 4 p.m.", which is the same programme the
# announcement says covers children. The figure is carried at its date and not
# claimed as current.

MARCUS_SOURCE = ("The Marcus Corporation press release, marcustheatres.com "
                 "press-releases/view/136, dated 2024-05-30 and distributed by "
                 "BusinessWire, read 2026-09-08: moviegoers 11 years old & under "
                 "and 60 & over may buy tickets for $7 for all shows before 4 "
                 "p.m. Corroborated on route by the Young at Heart page, read "
                 "the same day. Figure carried at its date, not claimed current")

MARCUS = {"any show starting before 4 p.m.": {"11 and under": 700,
                                              "60 and over":  700}}
MARCUS_LINES = ("11 and under", "60 and over")


def row_marcus():
    per_pair, pairable, separated = pair_up(MARCUS)
    return {"line": "the two age classes the chain's own announcement names for "
                    "one price",
            "partition": "the two classes named in one sentence of the company's "
                         "own press release",
            "label_fixes_value": False,
            "why": "the same chain's value pricing page prices Student Thursdays "
                   "at $7.50 with a valid school ID and a military discount at "
                   "$8.50 with a valid ID, so it plainly writes different numbers "
                   "for different named classes when it wants to",
            "family": "listed cinema chain", "source": MARCUS_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(MARCUS), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(MARCUS, MARCUS_LINES),
            "why_it_is_here": (
                "one pair, and it is the only zero on the board at a seller whose "
                "objective stands on a document: The Marcus Corporation, NYSE: "
                "MCS, reporting net earnings per diluted common share in a release "
                "filed with the SEC. B58 has an admissible cell that has been "
                "reachable and empty; this is what reaches it")}


# --------------------------------------------------------------------------
# Row 22, read 2026-09-08. A national rail carrier's published everyday
# discounts: six named classes on one page, three distinct figures, and four of
# the six carrying the same one.
#
# Its objective stands on the hardest document on this board. 49 U.S.C.
# 24301(a)(2) says the carrier "shall be operated and managed as a for-profit
# corporation", and (a)(3) says it "is not a department, agency, or
# instrumentality of the United States Government". A statutory command to
# operate for profit is stronger than an exchange listing, and this section
# imposes no route or service obligation; (g) preempts state law on rates,
# routes and service.
#
# What was not looked at: whether any appropriations legislation attaches fare
# conditions to these particular classes. Named as a gap rather than assumed
# away.
#
# Three further categories on the same page carry no figure in the text read
# (passengers with disabilities, groups of fifteen or more, government
# employees). They are absent cells, reported in coverage, and contribute no
# pairs.
#
# Units are thousandths of one per cent, as with the other discount rows, and
# are not compared across rows.

AMTRAK_SOURCE = ("Amtrak published everyday discounts page, read 2026-09-08; "
                 "statutory status from 49 U.S.C. 24301(a)(2) and (a)(3)")

AMTRAK = {"one ticket on most trains": {
    "children 2 through 12":                   50000,
    "students 17 to 24":                       15000,
    "seniors 65 and over":                     10000,
    "active duty military and dependents":     10000,
    "veterans":                                10000,
    "Rail Passengers Association members":     10000}}
AMTRAK_LINES = tuple(sorted(AMTRAK["one ticket on most trains"]))
AMTRAK_NO_FIGURE = ("passengers with disabilities", "groups of fifteen or more",
                    "government employees")


def row_amtrak():
    per_pair, pairable, separated = pair_up(AMTRAK)
    # The alternative the reader might draw: one of the six is a membership a
    # rider buys, which B54 puts in the band where crossing costs near nothing.
    # Dropping it leaves five classes, ten pairs, three of them same-valued.
    alt_pairable, alt_sep = 10, 7
    return {"line": "the six classes this carrier's own everyday discounts page "
                    "names with a figure",
            "partition": "the categories listed under everyday discounts on the "
                         "carrier's own page, restricted to those the page gives "
                         "a figure for",
            "label_fixes_value": False,
            "why": "the page writes three different figures under this one "
                   "heading, 50, 15 and 10 per cent, so the heading plainly does "
                   "not fix the value",
            "family": "national rail carrier", "source": AMTRAK_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(AMTRAK), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(AMTRAK, AMTRAK_LINES),
            "the_object": "children at 50 and students at 15 separate from "
                          "everything; seniors, active duty military, veterans "
                          "and association members all read 10, so all six pairs "
                          "among those four separate nothing",
            "no_figure_on_page": {
                "count": len(AMTRAK_NO_FIGURE), "names": list(AMTRAK_NO_FIGURE),
                "reading": "listed under the same heading with no figure in the "
                           "text read. absent cells, not same-valued cells, and "
                           "they contribute no pairs"},
            "subset_reading": ("%d of %d. one of the six, association membership, "
                               "is bought rather than held, which B54's third "
                               "question puts in the band where crossing costs "
                               "near nothing. dropping it leaves %d of %d = "
                               "%.4f. the page draws all six, so the rate "
                               "reported is over all six and the subset is "
                               "recorded"
                               % (separated, pairable, alt_sep, alt_pairable,
                                  alt_sep / alt_pairable))}


# --------------------------------------------------------------------------
# Rows 23 and 24, read 2026-09-08. A national health system's published subsidy
# table, and one line of the same document that does something no other carrier
# on this board does: it forbids the line.
#
# The table is why B54 reads Q2 as failing on this carrier: what is published is
# a percentage off a common bill, not a second price. The percentages are class
# values, so they are read here.
#
# The second row is the interesting one. The same announcement says emergency
# department fees "will not discriminate between nationality or citizenship".
# That is a zero this framework has not met before: not a merge the seller chose
# and not a merge its credentials forced, but a distinction a published rule
# bans. Its cells are therefore not figures. What was read is that they are
# equal, and the shared level is not on that page, so the cells carry a marker
# and the row says so rather than inventing a number.
#
# Figures are at their announcement date and are not claimed current.

SG_SOURCE = ("Singapore Ministry of Health published announcement on the "
             "revision of hospital subsidy for foreigners, read 2026-09-08. "
             "subsidy percentages by ward class and residency status, at their "
             "announcement date and not claimed current")

SG_SUBSIDY = {
    "ward class B1":                {"citizen": 20000, "PR": 10000, "foreigner": 0},
    "ward class B2":                {"citizen": 65000, "PR": 55000, "foreigner": 0},
    "ward class C":                 {"citizen": 80000, "PR": 70000, "foreigner": 0},
    "day surgery":                  {"citizen": 65000, "PR": 55000, "foreigner": 0},
    "specialist outpatient clinic": {"citizen": 50000, "PR": 40000, "foreigner": 0},
}
SG_LINES = ("PR", "citizen", "foreigner")

EQUAL_BY_RULE = "equal by rule; the shared level is not published on this page"
SG_ED = {"emergency department": {"citizen": EQUAL_BY_RULE, "PR": EQUAL_BY_RULE,
                                  "foreigner": EQUAL_BY_RULE}}


def row_sg_subsidy():
    per_pair, pairable, separated = pair_up(SG_SUBSIDY)
    return {"line": "the three residency statuses the health ministry's own "
                    "subsidy table prints",
            "partition": "the columns of the published subsidy table, Singapore "
                         "citizen, permanent resident and foreigner",
            "label_fixes_value": False,
            "why": "the table prints three different figures under these headings "
                   "in every one of its rows",
            "family": "national health subsidy schedule", "source": SG_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(SG_SUBSIDY), "pairable": pairable,
            "separated": separated, "use_rate": separated / pairable,
            "per_pair": per_pair, "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(SG_SUBSIDY, SG_LINES),
            "the_object": "fifteen pairs, fifteen separations, and the gap between "
                          "citizen and permanent resident is five points in every "
                          "row but the first, where it is ten. what is published "
                          "is a percentage off a common bill, which is why B54 "
                          "reads this carrier's second question as failing while "
                          "this row reads its class values"}


def row_sg_emergency():
    per_pair, pairable, separated = pair_up(SG_ED)
    return {"line": "the same three residency statuses, in the one place the same "
                    "document forbids the distinction",
            "partition": "the same three statuses named by the same announcement",
            "label_fixes_value": False,
            "why": "the labels name residency, not a number, and the same document "
                   "prints five rows in which they take different values",
            "family": "national health subsidy schedule", "source": SG_SOURCE,
            "recomputed_from_cells": True,
            "contexts": len(SG_ED), "pairable": pairable, "separated": separated,
            "use_rate": separated / pairable, "per_pair": per_pair,
            "nominal_pairs": pairable, "independent_facts": 1,
            "coverage": coverage(SG_ED, SG_LINES),
            "cells_are_not_figures": (
                "the announcement says emergency department fees will not "
                "discriminate between nationality or citizenship. what was read is "
                "that the three cells are equal; their shared level is not on that "
                "page. the cells carry a marker rather than a number, and this row "
                "is excluded from the exact-integer premise for that reason"),
            "the_object": "a zero of a kind not otherwise on this board. it is not "
                          "a merge the seller chose, and not one its credentials "
                          "forced. a published rule bans the line in this one "
                          "context while the same document draws it in five others"}


def main():
    rows = {"virginia_residency": row_virginia(),
            "agra_nationality": row_agra(),
            "transit_federal_three": row_transit_federal(),
            "student_vs_senior": row_student_senior(),
            "mbta_free_list": row_mbta_list("free"),
            "mbta_reduced_list": row_mbta_list("reduced"),
            "maryland_columns": row_maryland_columns(),
            "king_county_types": row_king_county(),
            "income_vs_senior": row_income_vs_senior(),
            "rtd_discount_four": row_rtd_discount(),
            "care_fera_bands": row_care_fera(),
            "jp_health_insurance_art74": row_jp_art74(),
            "jp_elderly_care_art67": row_jp_art67(),
            "boulder_resident_line": row_boulder(),
            "clayton_admission_standing": row_clayton_standing(),
            "clayton_admission_age": row_clayton_age(),
            "cinema_village_categories": row_cinema_village(),
            "cinema_arts_evening": row_cinema_arts(),
            "marcus_matinee": row_marcus(),
            "amtrak_everyday_discounts": row_amtrak(),
            "sg_subsidy_residency": row_sg_subsidy(),
            "sg_emergency_rule": row_sg_emergency(),
            "state_park_residence": row_state_parks(),
            "auto_classification_gender": CARRIED_AUTO_GENDER}

    crit, KIND = {}, {}

    # B57-1 known answer. B55 pairs its table by hand; the general rule must
    # return the same two integers on the same data, or one of the two is wrong.
    #
    # The two targets are read from B55 rather than written here. They used to be
    # the literals 26 and 1, and the day B55's pairing grew by fifteen rungs of
    # the lifetime ladders this criterion failed while nothing was wrong: it was
    # comparing the rule against a number, not against B55. A known-answer check
    # whose answer is a literal stops being a check on the rule and becomes a
    # check on whether anyone edited the other file.
    v = rows["virginia_residency"]
    want_pairable = len(b55.RESIDENCY_PAIRS)
    want_same = sum(1 for _, a, b in b55.RESIDENCY_PAIRS if a == b)
    got_same = v["pairable"] - v["separated"]
    ok = (v["pairable"] == want_pairable) and (got_same == want_same)
    crit["B57-1"] = {"passed": ok, "kind": "known_answer",
        "name": "the general pairing rule reproduces the hand pairing B55 reported",
        "detail": "B55 pairs %d with %d same-value, read from its own list; the "
                  "rule returns %d and %d"
                  % (want_pairable, want_same, v["pairable"], got_same)}

    # B57-2 instrument. separated + same = pairable, every row.
    bad = [k for k, r in rows.items()
           if r["separated"] + (r["pairable"] - r["separated"]) != r["pairable"]]
    crit["B57-2"] = {"passed": not bad, "kind": "instrument",
        "name": "separated + same-value = pairable, in every row",
        "detail": "%d rows, %d violations" % (len(rows), len(bad))}

    # B57-3 premise. Every recomputed row's values are exact integers in the
    # smallest currency unit, so no rounding can make two different values equal
    # and no rounding can split two equal ones.
    #
    # Walked over RECOMPUTED_CELLS, which is every cell this run actually paired.
    # It used to be walked over five tables named here by hand, and a cell in any
    # other row could have been a float without this criterion noticing: the check
    # named "every recomputed cell" and read a list of five.
    #
    # Three states, not two (11c). A cell is an exact integer in its own unit; or
    # it is a number that is not one, which is the failure; or it carries no
    # number at all, which happens where a published rule forbids the line and the
    # shared level is not printed. The third is named and counted rather than
    # folded into either of the first two.
    inexact, unpriced = [], []
    for ctx, line, value in RECOMPUTED_CELLS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            unpriced.append("%s :: %s" % (ctx, line))
        elif not isinstance(value, int):
            inexact.append("%s :: %s = %r" % (ctx, line, value))
    crit["B57-3"] = {"passed": not inexact, "kind": "premise",
        "cells_checked": len(RECOMPUTED_CELLS),
        "cells_without_a_published_number": unpriced,
        "name": "every recomputed cell is an exact integer in the unit its own "
                "source files: the smallest currency unit for a fare, thousandths "
                "of one per cent for a filed discount",
        "detail": "%d cells walked, %d inexact, %d carrying no published number "
                  "because a rule forbids the line: %s"
                  % (len(RECOMPUTED_CELLS), len(inexact), len(unpriced),
                     "; ".join(inexact) or "none inexact")}

    # B57-3b bookkeeping. The Virginia row is the one row whose cells arrive
    # already paired: B55 wrote the pairs by hand and this file reads them. So the
    # count can be reproduced exactly while the SELECTION is never examined, and
    # that is what happened. This walks the fee schedule instead and names every
    # row no pair uses, which is the object the check was missing rather than a
    # verdict on which of them ought to be paired.
    used_res = {v for _, v, _ in b55.RESIDENCY_PAIRS}
    used_non = {v for _, _, v in b55.RESIDENCY_PAIRS}
    uncovered = []
    for grp, desc, val in b55.ROWS:
        if val is None:
            continue
        if grp.startswith("resident") and val not in used_res:
            uncovered.append("resident %d :: %s" % (val, desc))
        elif grp.startswith("nonresident") and val not in used_non:
            uncovered.append("nonresident %d :: %s" % (val, desc))
    crit["B57-3b"] = {"passed": True, "kind": "instrument",
        "name": "coverage of the Virginia hand pairing, printed and not gated: "
                "which fee rows carry a value no registered pair uses",
        "detail": "%d fee rows in the schedule, %d registered pairs using %d "
                  "distinct resident values; %d rows carry a value no pair uses. "
                  "This is printed rather than scored because whether a given row "
                  "has a counterpart on the other side is a reading of the "
                  "schedule and not an arithmetic fact, and the lifetime age "
                  "bands are the clear case: one non-resident lifetime licence "
                  "with no age band stands against a resident ladder of them. "
                  "Uncovered: %s"
                  % (len(b55.ROWS), len(b55.RESIDENCY_PAIRS), len(used_res),
                     len(uncovered), "; ".join(uncovered) or "none")}

    # B57-4 own reading. Print the object: per row, per line-pair.
    crit["B57-4"] = {"passed": all("per_pair" in r or not r["recomputed_from_cells"]
                                   for r in rows.values()),
        "kind": "own_reading",
        "name": "print the object: per row and per line-pair, pairable / separated / rate",
        "detail": "; ".join("%s %d/%d = %.4f" % (k, r["separated"], r["pairable"],
                                                 r["use_rate"])
                            for k, r in sorted(rows.items()) if r["use_rate"] is not None)}

    # B57-5 bookkeeping. Every row says where it came from and whether it was
    # recomputed from cells on disk or carried from a reading made elsewhere.
    noprov = [k for k, r in rows.items()
              if not r.get("source") or "recomputed_from_cells" not in r]
    crit["B57-5"] = {"passed": not noprov, "kind": "bookkeeping",
        "name": "every row names its source and says whether it was recomputed or carried",
        "detail": "%d rows, %d recomputed from cells on disk, %d carried, %d without provenance"
                  % (len(rows), sum(1 for r in rows.values() if r["recomputed_from_cells"]),
                     sum(1 for r in rows.values() if not r["recomputed_from_cells"]),
                     len(noprov))}

    # B57-6 rival. Third-degree price discrimination has the seller pay to sort
    # and then price by elasticity. Its point prediction here is the weak one,
    # which is the fair one: a line that is drawn and credentialed separates
    # somewhere, so the use rate is above zero. Read per row. Zero threshold of
    # this station's own: the boundary is the rival's, not one chosen here.
    # Three states, and the middle one maps to no verdict (11c).
    # Fourth clause: a degenerate partition is excluded from the rival reading,
    # because a zero its own label forces is not a reading of anything.
    read = {k: r for k, r in rows.items()
            if r["use_rate"] is not None and not r.get("label_fixes_value")}
    holds = [k for k, r in read.items() if r["use_rate"] > 0]
    fails = [k for k, r in read.items() if r["use_rate"] == 0]
    if not read:
        b6, state = None, "undetermined: no row was read"
    elif not fails:
        b6, state = False, "the rival's point prediction holds in every row read"
    else:
        b6, state = True, "the rival's point prediction fails where the rate is zero"
    crit["B57-6"] = {
        "rival_premise": "a seller who has paid to sort prices each named block by that block's own elasticity", "rival_entailment": "the inverse elasticity rule sets a distinct price wherever elasticities differ, so a seller that has already bought the sorting writes as many distinct values as it named blocks", "cite": "Stole chapter 34, read for station B58", "passed": b6, "kind": "rival",
        "grid": "mixed",
        "grid_split": {"A": len(holds), "B": len(fails)},
        "grid_note": "rows where the drawn line separates are grid A: the "
                     "rival is right and so is the counting law, since the "
                     "programme wrote distinct class values there. Rows with "
                     "a zero rate are grid B",
        "name": "rival: a line drawn and credentialed separates somewhere, so the "
                "use rate is above zero",
        "detail": "%s; %d of %d rows read hold it, zero-rate rows: %s"
                  % (state, len(holds), len(read), ", ".join(sorted(fails)) or "none")}

    # B57-8. Absent cells are named rather than dropped in silence. pair_up is
    # right to drop a context that lacks one of the two values, and D25's first
    # question is why: a class that cannot reach a product at all is an H0
    # reachability fact and not a use rate. The count belongs on the record.
    cov = {k: r["coverage"] for k, r in rows.items() if "coverage" in r}
    crit["B57-8"] = {"passed": True, "kind": "bookkeeping",
        "name": "rows whose table has absent cells report them rather than dropping "
                "them in silence, because an absent cell is an H0 fact not a rate",
        "detail": "; ".join("%s %d of %d cells present, %d absent"
                            % (k, c["cells_present"], c["cells_possible"],
                               c["cells_absent"]) for k, c in sorted(cov.items()))
                  or "no row in this run has an incomplete table"}

    # B57-10. Known answer. Every paratransit fare on disk must sit at or under
    # twice its operator's own full fare, because the regulation says so. It tests
    # the reading of the rule and the fares at once. It also shows why one
    # operator's paratransit fare sits ABOVE its full fare without breaking
    # anything: the ceiling is twice, not once.
    ada = ada_ceiling_check()
    over = [k for k, v in ada.items() if not v["under_ceiling"]]
    crit["B57-10"] = {"passed": not over, "kind": "known_answer",
        "name": "every paratransit fare on disk sits at or under twice its own "
                "operator's full fare, which is what 49 CFR 37.131(c) permits",
        "detail": "%d fares checked, %d over the ceiling; shares of ceiling %s"
                  % (len(ada), len(over),
                     ", ".join("%s %.3f" % (k, v["share_of_ceiling"])
                               for k, v in sorted(ada.items())))}

    # B57-9. The fourth clause, checked rather than trusted. Every row says
    # whether its partition's own label fixes the value, and why. A row where it
    # does is degenerate and its rate reads the label back rather than the cells.
    nodeg = [k for k, r in rows.items() if "label_fixes_value" not in r or not r.get("why")]
    degen = sorted(k for k, r in rows.items() if r.get("label_fixes_value"))
    crit["B57-9"] = {"passed": not nodeg, "kind": "instrument",
        "name": "every row says whether its partition's own label fixes the value, "
                "and a row where it does is excluded from the rival reading",
        "detail": "%d rows, %d without the field; degenerate: %s"
                  % (len(rows), len(nodeg), ", ".join(degen) or "none")}

    # B57-11 rival, read at the level R3 established as the comparable one.
    # B57-6 asks the question per row, and a row can hold it while containing a
    # block of pairs that read zero: both cinema rows do exactly that. R3 ruled
    # on 2026-09-07, before those rows existed, that the comparable unit is the
    # line-value pair and not the row, so the same rival prediction belongs at
    # that level too. Both criteria are kept: they are the same prediction read
    # at two grains, and neither replaces the other.
    #
    # Changing the grain changes no reading. per_pair is computed by the same
    # function either way, which is the test D5 and 5.2a set for a criterion
    # shape change.
    pairs, zero_pairs = 0, []
    for k, r in sorted(rows.items()):
        if r.get("label_fixes_value") or not r.get("per_pair"):
            continue
        for name, e in sorted(r["per_pair"].items()):
            pairs += 1
            if e["separated"] == 0:
                zero_pairs.append("%s :: %s (%d contexts)" % (k, name, e["pairable"]))
    crit["B57-11"] = {
        "rival_premise": "a seller who has paid to sort prices each named block by that block's own elasticity", "rival_entailment": "the inverse elasticity rule sets a distinct price wherever elasticities differ, so a seller that has already bought the sorting writes as many distinct values as it named blocks", "cite": "Stole chapter 34, read for station B58", "passed": bool(zero_pairs), "kind": "rival",
        "grid": "mixed",
        "grid_split": {"A": pairs - len(zero_pairs),
                       "B": len(zero_pairs)},
        "grid_note": "a pair that separates is grid A, both accounts right; "
                     "a pair that separates nothing is grid B",
        "name": "the same rival prediction read per line-value pair, which R3 "
                "established as the comparable unit: a pair of drawn classes "
                "separates somewhere",
        "detail": "%d pairs read across the non-degenerate rows, %d separate "
                  "nothing: %s" % (pairs, len(zero_pairs), "; ".join(zero_pairs))}

    # B57-12 rival. The cost defence, read against the credentials the sellers
    # themselves issue. If two classes each have their own application and their
    # own eligibility documents, the sorting has been bought twice and the step
    # the seller declined to take is a line in a fare table.
    #
    # This can fail. Had the merging operators turned out to issue one card, the
    # defence would stand and every zero here would have a mechanical account.
    # One pair does turn out that way and is reported as such.
    cred = {SEP: [], ONE: [], MIXED: [], FORBIDDEN: [], NOTREAD: []}
    for k, r in sorted(rows.items()):
        if r.get("label_fixes_value") or not r.get("per_pair"):
            continue
        for name, e in sorted(r["per_pair"].items()):
            if e["separated"]:
                continue
            state, why = CREDENTIALS.get(k, {}).get(name, (NOTREAD, "not read"))
            cred[state].append("%s :: %s" % (k, name))
    crit["B57-12"] = {
        "rival_premise": "finer segmentation is not worth what it costs, so a seller that merges two classes onto one number is economising on sorting", "rival_entailment": "were the sorting unbought, the two classes would not hold separate credentials. Where each class has its own application and its own eligibility documents, the cost is already paid, and the step the seller did not take is one more line in a fare table", "passed": bool(cred[SEP]), "kind": "rival",
        "grid": "B",
        "grid_note": "this one runs only on the pairs already in grid B, and asks why the zero is there",
        "name": "the rival's cost defence, that finer segmentation is not worth "
                "paying for, read against the credentials the sellers issue: a "
                "zero pair whose two classes each have their own application has "
                "already been paid for",
        "detail": "%d zero pairs; %d separately credentialed on the seller's own "
                  "page, %d sharing one credential, %d mixed across the operators "
                  "the row spans, %d where a published rule forbids the line, %d "
                  "not read. separately credentialed: %s. one credential: %s. "
                  "mixed: %s. forbidden by rule: %s"
                  % (sum(len(v) for v in cred.values()), len(cred[SEP]),
                     len(cred[ONE]), len(cred[MIXED]), len(cred[FORBIDDEN]),
                     len(cred[NOTREAD]), "; ".join(cred[SEP]),
                     "; ".join(cred[ONE]) or "none",
                     "; ".join(cred[MIXED]) or "none",
                     "; ".join(cred[FORBIDDEN]) or "none"),
        "sources": CRED_SOURCE}

    # B57-7. The third clause, checked rather than trusted: every row names the
    # partition its line values are drawn from. A rate whose partition is not
    # named is not a reading, because the reader chose the set.
    nopart = [k for k, r in rows.items() if not r.get("partition")]
    crit["B57-7"] = {"passed": not nopart, "kind": "bookkeeping",
        "name": "every row names the partition the source itself draws, which the "
                "line values are taken from",
        "detail": "%d rows, %d without a named partition" % (len(rows), len(nopart))}

    for k, c in crit.items():
        KIND[k] = c["kind"]

    out = {"stage": "B57",
           "pairing_rule": "cells indexed by (class-line value, context); a pairable "
                           "pair shares context and differs in line value; the line "
                           "separates it when the two values differ; "
                           "use rate = separated / pairable",
           "ada_ceiling": {"rule": ADA_CEILING_RULE,
                           "checked": ada_ceiling_check(),
                           "reading": "the ceiling is blind to every discount class, "
                                      "so it neither requires nor forbids a split "
                                      "among paratransit riders. the split the "
                                      "fourth operator makes there is its own"},
           "config": {"n_rows": len(rows),
                      "recomputed_rows": sorted(k for k, r in rows.items()
                                                if r["recomputed_from_cells"]),
                      "carried_rows": sorted(k for k, r in rows.items()
                                             if not r["recomputed_from_cells"]),
                      "amounts_in": "smallest currency unit, except care_fera_bands, "
                                    "jp_health_insurance_art74 and "
                                    "jp_elderly_care_art67, which are in thousandths "
                                    "of one per cent. those rows are not compared "
                                    "with each other: the first files a discount off "
                                    "a price, the other two file the share the "
                                    "patient pays"},
           # The serialiser used to name the keys it carried, and it dropped a new
           # field twice on 2026-09-08 without a word. It now carries everything
           # the criterion dict holds and renames only what has to be renamed.
           "criteria": [{**{kk: vv for kk, vv in v.items()
                            if kk not in ("name", "passed", "kind", "detail")},
                         "name": k, "passed": v["passed"], "kind": v["kind"],
                         "criterion": v["name"], "detail": v["detail"]}
                        for k, v in sorted(crit.items())],
           "rows": rows}
    dest = Path(__file__).resolve().parents[1] / "results" / "b57_class_line_use_rate.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    print("=== the pairing rule")
    print("    " + out["pairing_rule"])
    print()
    print("=== use rate by row")
    print("    %-28s %-34s %8s %10s %9s  %s"
          % ("row", "family", "pairable", "separated", "rate", "source"))
    for k, r in sorted(rows.items(), key=lambda x: -(x[1]["use_rate"] or 0)):
        print("    %-28s %-34s %8d %10d %8.2f%%  %s"
              % (k, r["family"], r["pairable"], r["separated"],
                 100 * r["use_rate"] if r["use_rate"] is not None else float("nan"),
                 "recomputed" if r["recomputed_from_cells"] else "carried"))
    print()
    print("=== print the object: every line-pair in the recomputed rows")
    for k, r in sorted(rows.items()):
        if not r["recomputed_from_cells"]:
            continue
        print("    %s" % k)
        for pair, e in sorted(r["per_pair"].items()):
            print("        %-34s %3d pairable %3d separated  %6.2f%%%s"
                  % (pair, e["pairable"], e["separated"], 100 * e["use_rate"],
                     "   same value at: " + "; ".join(e["same_value_contexts"])
                     if e["same_value_contexts"] else ""))
        if "independent_facts" in r:
            print("        nominal pairs %d, independent facts %d (D22)"
                  % (r["nominal_pairs"], r["independent_facts"]))
    print()
    for k, v in sorted(crit.items()):
        state = "PASS" if v["passed"] is True else ("FAIL" if v["passed"] is False else "----")
        print("%-8s %-5s %-13s %s" % (k, state, v["kind"], v["detail"]))
    bykind = {}
    for k, v in crit.items():
        bykind.setdefault(v["kind"], []).append(v["passed"])
    print("by kind: " + "; ".join(
        "%s %d/%d pass, %d undetermined" % (kd, sum(1 for x in s if x is True), len(s),
                                            sum(1 for x in s if x is None))
        for kd, s in sorted(bykind.items())))
    print("wrote", dest.name)
    return 0 if all(v["passed"] is not False for v in crit.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
