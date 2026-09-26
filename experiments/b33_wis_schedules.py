"""B33 arm one: does a published schedule's written partition equal the
partition its full clause vectors induce.

Carrier: Singapore, Central Provident Fund (Revised Workfare Income Supplement
Scheme) (Amendment No. 2) Regulations 2025, S 156/2025, made 5 March 2025,
first published in the Government Gazette, Electronic Edition, 5 March 2025.
33 pages, transcribed in full; the coverage table is criterion B33-4.

The instrument names five classes and gives each a clause vector.  Arm one asks
whether any two of the five receive an identical vector on every dimension.

Criteria are written here and the record carries their text.  No threshold sits
on any estimate: every criterion is an exact rational identity or a set
comparison, so the band-readability and power gates do not apply rather than
failing.  Rational arithmetic throughout; no floating point.
"""

from __future__ import annotations

import json
from fractions import Fraction as F
from pathlib import Path

# --------------------------------------------------------------------------
# Twelfth Schedule (Regulations 8AH and 13C(1), (2)(b) and (4)), pp. 26-27.
# Value of benefits for an eligible employee, eligible platform worker or
# eligible employee-platform worker, applicable year 2025 or later.
# Each cell is (slope on the total monthly sum, intercept), in dollars.
# Columns: attained 30 but below 35 / 35 but below 45 / 45 but below 60 /
# 60 or a specified member.
# --------------------------------------------------------------------------
TWELFTH = {
    1: [(F(0), F(53)), (F(0), F(79)), (F(0), F(131)), (F(0), F(152))],
    2: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(329, 1200), F(49, 4)), (F(1163, 4200), F(512, 21))],
    3: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(1, 6), F(175, 2)), (F(1163, 4200), F(512, 21))],
    4: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(1, 8), F(275, 2)), (F(31, 300), F(698, 3))],
    5: [(F(13, 150), F(341, 6)), (F(223, 1800), F(1459, 18)),
        (F(1, 8), F(275, 2)), (F(31, 300), F(698, 3))],
    6: [(F(0), F(1225, 6)), (F(0), F(875, 3)),
        (F(0), F(350)), (F(0), F(1225, 3))],
    7: [(F(-953, 4200), F(15247, 21)), (F(-1361, 4200), F(43553, 42)),
        (F(-1089, 2800), F(34847, 28)), (F(-3811, 8400), F(40651, 28))],
}

# Thirteenth Schedule (Regulations 8AH, 13C(2)(a) and (3), 13D(1)(a),
# (4)(a)(i) and (5)(a)), pp. 28-29.  Eligible platform worker.
THIRTEENTH = {
    1: [(F(0), F(106, 3)), (F(0), F(158, 3)),
        (F(0), F(262, 3)), (F(0), F(304, 3))],
    2: [(F(1, 12), F(19, 9)), (F(643, 5400), F(80, 27)),
        (F(329, 1800), F(49, 6)), (F(1163, 6300), F(1024, 63))],
    3: [(F(1, 12), F(19, 9)), (F(643, 5400), F(80, 27)),
        (F(1, 9), F(175, 3)), (F(1163, 6300), F(1024, 63))],
    4: [(F(1, 12), F(19, 9)), (F(643, 5400), F(80, 27)),
        (F(1, 12), F(275, 3)), (F(31, 450), F(1396, 9))],
    5: [(F(13, 225), F(341, 9)), (F(223, 2700), F(1459, 27)),
        (F(1, 12), F(275, 3)), (F(31, 450), F(1396, 9))],
    6: [(F(0), F(1225, 9)), (F(0), F(1750, 9)),
        (F(0), F(700, 3)), (F(0), F(2450, 9))],
    7: [(F(-953, 6300), F(30494, 63)), (F(-1361, 6300), F(43553, 63)),
        (F(-363, 1400), F(34847, 42)), (F(-3811, 12600), F(40651, 42))],
}

# Fourteenth Schedule (Regulation 13D(2)(a), (4)(a)(ii) and (7)(a)), pp. 30-31.
# Same grid, read against average monthly income for the relevant year.
FOURTEENTH = {
    1: [(F(0), F(53)), (F(0), F(79)), (F(0), F(131)), (F(0), F(152))],
    2: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(329, 1200), F(49, 4)), (F(1163, 4200), F(512, 21))],
    3: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(1, 6), F(175, 2)), (F(1163, 4200), F(512, 21))],
    4: [(F(1, 8), F(19, 6)), (F(643, 3600), F(40, 9)),
        (F(1, 8), F(275, 2)), (F(31, 300), F(698, 3))],
    5: [(F(13, 150), F(341, 6)), (F(223, 1800), F(1459, 18)),
        (F(1, 8), F(275, 2)), (F(31, 300), F(698, 3))],
    6: [(F(0), F(1225, 6)), (F(0), F(875, 3)),
        (F(0), F(350)), (F(0), F(1225, 3))],
    7: [(F(-953, 4200), F(15247, 21)), (F(-1361, 4200), F(43553, 42)),
        (F(-1089, 2800), F(34847, 28)), (F(-3811, 8400), F(40651, 28))],
}

BANDS = ["<500", "500-700", "700-1200", "1200-1400",
         "1400-1700", "1700-2300", "2300-3000"]
COLS = ["30-35", "35-45", "45-60", "60+"]

# --------------------------------------------------------------------------
# The five classes the instrument writes, and the clause vector each receives.
# Sources are the regulation numbers in S 156/2025 as inserted into the
# principal Regulations.
# --------------------------------------------------------------------------
CLASSES = {
    "8AA eligible employee": {
        "2025 onward": {
            "qualifying_quantity": "total wages for the relevant month",
            "small_sum_exclusion": "$50 from any one employer (reg 8AH(a)(ii))",
            "waiver_top_up": "9/8/6/5/4 by age band (reg 8AI(2))",
            "cash_proportion_month": "two-fifths (reg 13B(1)(b)(i))",
            "benefit_table_month": "Twelfth Schedule (reg 13C(1))",
        },
    },
    "8AB eligible Group A worker": {
        "applicable year 2025-2028": {
            "qualifying_quantity": "total APE for the relevant month",
            "small_sum_exclusion": "$50 from any one platform operator (reg 8AH(b)(ii)(A))",
            "waiver_top_up": "7/7/7/5/4 by age band (reg 8AI(4))",
            "cash_proportion_month": "one-tenth (reg 13B(1)(a)(i))",
            "benefit_table_month": "Thirteenth Schedule (reg 13C(2)(a))",
        },
        "applicable year 2029 onward": {
            "qualifying_quantity": "total APE for the relevant month",
            "small_sum_exclusion": "$50 from any one platform operator (reg 8AH(b)(ii)(A))",
            "waiver_top_up": "7/7/7/5/4 by age band (reg 8AI(4))",
            "cash_proportion_month": "two-fifths (reg 13B(1)(b)(ii))",
            "benefit_table_month": "Twelfth Schedule (reg 13C(2)(b))",
        },
    },
    "8AC eligible Group B worker": {
        "2025 onward": {
            "qualifying_quantity": "total APE for the relevant month",
            "small_sum_exclusion": "$500 from any one platform operator (reg 8AH(b)(ii)(B))",
            "waiver_top_up": "Fifteenth Schedule, age band by annual APE (reg 8AI(6))",
            "cash_proportion_month": "one-tenth (reg 13B(1)(a)(ii))",
            "benefit_table_month": "Thirteenth Schedule (reg 13C(3))",
        },
    },
    "8AD eligible employee-platform worker": {
        "2025 onward": {
            "qualifying_quantity": "aggregate of total wages and total APE",
            "small_sum_exclusion": "per limb, employee and platform separately (reg 8AH)",
            "waiver_top_up": "routed to 8AI(3)-(6) by the worker's group (reg 8AI(7))",
            "cash_proportion_month": "two-fifths (reg 13B(1)(b)(i))",
            "benefit_table_month": "Twelfth Schedule (reg 13C(4))",
        },
    },
    "8AE eligible self-employed person": {
        "2025 onward": {
            "qualifying_quantity": "average monthly income for the relevant year",
            "small_sum_exclusion": "not applicable, the year is the unit",
            "waiver_top_up": "reg 8AJ, by notified income band",
            "cash_proportion_month": "assessed for the year under reg 13B(2)",
            "benefit_table_month": "Fourteenth Schedule (reg 13D(1)(a))",
        },
    },
}

# The one class carrying more than one vector, and the provisions that draw the
# line inside it.  A read partition finer than the written one is a failure only
# where the instrument does not itself draw that line; here it does, twice.
INTERNAL_LINES = {
    "8AB eligible Group A worker": [
        "reg 13B(1)(b)(ii): the cash proportion moves from one-tenth to "
        "two-fifths at applicable year 2029",
        "reg 13C(2)(b): the benefit table moves from the Thirteenth to the "
        "Twelfth Schedule at applicable year 2029",
    ],
}

# Pages of the instrument opened, and what each batch carried.  Recording pages
# that carried nothing is the point: a skipped page and a page read to zero
# look identical in a total.
COVERAGE = [
    {"pages": "1-4", "carried": "reg 2 definitions, deletion of reg 4, "
                                "Part 2/Part 3 headings, reg 8AA, start of 8AB"},
    {"pages": "5-8", "carried": "regs 8AB(b)(ii)-(iii), 8AC, 8AD, 8AE, 8AF, 8AG(1)"},
    {"pages": "9-18", "carried": "8AG(2)-(3), 8AH, 8AI, 8AJ, 8AK, "
                                 "regs 10 and 11-13 amendments, 13A, 13B(1)"},
    {"pages": "19-33", "carried": "13B(1)(b)(ii) and 13B(2), 13C, 13D, 13E, "
                                  "regs 14A/15 and First/Second/Ninth/Tenth/"
                                  "Eleventh Schedule amendments, Twelfth to "
                                  "Fifteenth Schedules, execution page"},
]
PAGES_IN_INSTRUMENT = 33

# --------------------------------------------------------------------------
# The rule that separates a Group A worker from a Group B worker.  Fetched
# 2026-09-16, two hops down an authorising chain: this instrument's regulation
# 3(b) sends both definitions to paragraph 1(1) of the Fourth Schedule to the
# Central Provident Fund Act 1953, and that paragraph sends them on to
# paragraphs 5 and 8 of the same Schedule.  Nothing in the instrument itself
# states it, which is why arm one could not say at first whether 8AB and 8AC
# stand at one position or two.
# --------------------------------------------------------------------------
GROUP_PARTITION = {
    "chain": [
        "S 156/2025 reg 3(b): the two terms have the meanings given by "
        "paragraph 1(1) of the Fourth Schedule to the Act",
        "Fourth Schedule para 1(1): Group A is a platform worker to whom "
        "Part 3 applies as set out in para 5; Group B, Part 4 as set out in "
        "para 8",
    ],
    "group_a": "para 5: born on or after 1 January 1995; or born before and "
               "opting to be a Group A worker under para 4(1)",
    "group_b": "para 8: born before 1 January 2026, subject to paras 5, 6 "
               "and 7",
    "option_one_way": "para 4(3): an option under sub-paragraph (1) cannot be "
                      "withdrawn.  The option runs from B to A only, and a "
                      "worker born on or after 1 January 1995 has no route to "
                      "Group B at all.",
    "same_position": "the eligibility sentences of 8AB and 8AC are the same "
                     "word for word but for the group name: being a Group X "
                     "worker, worked as a platform worker (and not also as an "
                     "employee) in the relevant month.  What the member did is "
                     "identical; the terms are not.",
    "not_reducible_to_age": "both schedules are banded by age, so a reading "
                            "that the terms are a function of age has to be "
                            "answered.  The one-way option answers it: a "
                            "worker born before 1995 who has exercised it is "
                            "Group A while a worker of the same age in the "
                            "same month who has not is Group B.  The class "
                            "index is a label the Board records, not a "
                            "function of any position variable.",
}

#: The pair the rival's entailment bites on: one position, two classes.
RIVAL_PAIR = ("8AB eligible Group A worker", "8AC eligible Group B worker")


def compare_ratio(a: dict, b: dict) -> tuple[set[F], list[dict]]:
    """Ratios b/a over every coefficient where at least one side is non-zero."""
    ratios: set[F] = set()
    anomalies: list[dict] = []
    for band in sorted(a):
        for j, col in enumerate(COLS):
            for k, name in ((0, "slope"), (1, "intercept")):
                x, y = a[band][j][k], b[band][j][k]
                if x == 0 and y == 0:
                    continue
                if x == 0 or y == 0:
                    anomalies.append({"band": BANDS[band - 1], "column": col,
                                      "coefficient": name,
                                      "note": "one side zero"})
                    continue
                ratios.add(y / x)
    return ratios, anomalies


def compare_identity(a: dict, b: dict) -> list[dict]:
    out: list[dict] = []
    for band in sorted(a):
        for j, col in enumerate(COLS):
            for k, name in ((0, "slope"), (1, "intercept")):
                if a[band][j][k] != b[band][j][k]:
                    out.append({"band": BANDS[band - 1], "column": col,
                                "coefficient": name,
                                "twelfth": str(a[band][j][k]),
                                "other": str(b[band][j][k])})
    return out


def pair_differences(classes: dict, pair: tuple) -> list[dict]:
    """Every (period, period) pairing of the two classes, and the dimensions
    on which their clause vectors differ.  The rival says this list is empty."""
    a, b = pair
    out = []
    for pa, va in sorted(classes[a].items()):
        for pb, vb in sorted(classes[b].items()):
            out.append({
                "a": "%s | %s" % (a, pa),
                "b": "%s | %s" % (b, pb),
                "dimensions_differing": sorted(k for k in va if va[k] != vb[k]),
            })
    return out


def build(classes: dict, coverage: list, twelfth: dict, thirteenth: dict,
          fourteenth: dict) -> dict:
    ratios, anomalies = compare_ratio(twelfth, thirteenth)
    n_coeff = sum(
        1
        for band in twelfth
        for j in range(4)
        for k in (0, 1)
        if not (twelfth[band][j][k] == 0 and thirteenth[band][j][k] == 0)
    )
    c1 = (len(ratios) == 1 and ratios == {F(2, 3)} and not anomalies)

    diffs = compare_identity(twelfth, fourteenth)
    n_cells = len(twelfth) * 4 * 2
    c2 = not diffs

    vectors = {
        "%s | %s" % (cls, period): tuple(sorted(vec.items()))
        for cls, periods in classes.items()
        for period, vec in periods.items()
    }
    keys = list(vectors)
    collisions = [
        [a, b]
        for i, a in enumerate(keys)
        for b in keys[i + 1:]
        if vectors[a] == vectors[b]
    ]
    c3 = not collisions

    split_classes = {k: v for k, v in classes.items() if len(v) > 1}
    c5 = set(split_classes) == set(INTERNAL_LINES) and all(
        INTERNAL_LINES.get(k) for k in split_classes
    )

    pages_read = 0
    for batch in coverage:
        lo, hi = batch["pages"].split("-")
        pages_read += int(hi) - int(lo) + 1
    c4 = pages_read == PAGES_IN_INSTRUMENT

    #: The rival's point prediction on the one pair that stands at one
    #: position.  It says the list of differing dimensions is empty in every
    #: period pairing; the criterion passes when it is not.
    pair = pair_differences(classes, RIVAL_PAIR)
    c26 = bool(pair) and all(p["dimensions_differing"] for p in pair)

    distinct_functions = 1 + (0 if c2 else 1) + (1 if c1 else 0)

    record = {
        "stage": "B33",
        "carrier": "Singapore S 156/2025, CPF (Revised Workfare Income "
                   "Supplement Scheme) (Amendment No. 2) Regulations 2025",
        "config": {
            "arithmetic": "exact rationals, no floating point",
            "schedules_compared": ["Twelfth", "Thirteenth", "Fourteenth"],
            "classes_written": len(classes),
            "clause_vectors": sum(len(v) for v in classes.values()),
            "clause_dimensions": 5,
            "pages_in_instrument": PAGES_IN_INSTRUMENT,
            "rival_pair": list(RIVAL_PAIR),
        },
        "criteria": [
            {
                "name": "B33-1",
                "kind": "own_reading",
                "text": "Every coefficient of the Thirteenth Schedule is "
                        "exactly two-thirds of the corresponding coefficient "
                        "of the Twelfth, over all seven bands and four age "
                        "columns, slopes and intercepts alike.",
                "passed": c1,
                "detail": "%d coefficients compared, distinct ratios %s, "
                          "anomalies %d"
                          % (n_coeff, sorted(str(r) for r in ratios),
                             len(anomalies)),
            },
            {
                "name": "B33-2",
                "kind": "own_reading",
                "text": "The Fourteenth Schedule is cell for cell identical to "
                        "the Twelfth; only the variable it is read against "
                        "differs (total monthly sum against average monthly "
                        "income).",
                "passed": c2,
                "detail": "%d cells compared, %d differ" % (n_cells, len(diffs)),
            },
            {
                "name": "B33-3",
                "kind": "own_reading",
                "text": "No two of the classes the instrument writes receive an "
                        "identical clause vector on all five dimensions. A "
                        "collision would put the read partition strictly "
                        "coarser than the written one.",
                "passed": c3,
                "detail": "%d written classes carrying %d clause vectors, "
                          "%d colliding pairs"
                          % (len(classes), len(vectors), len(collisions)),
            },
            {
                "name": "B33-4",
                "kind": "bookkeeping",
                "text": "Every page of the instrument was opened, and the "
                        "coverage table names what each batch carried, "
                        "including batches that carried nothing bearing on the "
                        "criteria.",
                "passed": c4,
                "detail": "%d of %d pages" % (pages_read, PAGES_IN_INSTRUMENT),
            },
            {
                "name": "B33-5",
                "kind": "own_reading",
                "text": "Where the read partition is strictly finer than the "
                        "written one, the extra line is drawn by the instrument "
                        "itself and can be named. Every class carrying more "
                        "than one clause vector has its dividing provisions "
                        "listed; a split with no provision behind it would put "
                        "the read partition finer than the written one and fail "
                        "the arm.",
                "passed": c5,
                "detail": "%d of %d written classes carry more than one vector: "
                          "%s"
                          % (len(split_classes), len(classes),
                             ", ".join(sorted(split_classes)) or "none"),
            },
            {
                "name": "B33-26",
                "kind": "rival",
                "grid": "B",
                "rival_shape": "point prediction",
                "rival_premise":
                    "a position carries a scalar and every term at that "
                    "position is generated by it, so the object has one index "
                    "and no class index",
                "rival_entailment":
                    "8AB and 8AC stand at one position: their eligibility "
                    "sentences are the same word for word but for the group "
                    "name, and what separates the groups is the member's date "
                    "of birth plus an option that runs one way and cannot be "
                    "withdrawn, neither of which is a position variable. "
                    "Terms generated by one scalar at one position must "
                    "therefore coincide across the two classes, on every "
                    "dimension and in every period. One differing dimension "
                    "refutes it.",
                "polarity":
                    "registered as the rival's prediction failing, so passing "
                    "means the rival is wrong (discipline 11e, first clause, "
                    "second part)",
                "opposite_prediction":
                    "the counting law puts the number of distinct clause "
                    "values at the number of classes the programme writes, so "
                    "this frame predicts the two differ where the rival "
                    "predicts they coincide. The cell admits both outcomes "
                    "(discipline 11e, sixth clause).",
                "text": "On the one pair that stands at one position, 8AB and "
                        "8AC, the rival's scalar generates one set of terms, "
                        "so the two classes must receive identical clause "
                        "vectors in every period pairing. The criterion counts "
                        "the dimensions on which they differ and passes when "
                        "every pairing differs on at least one.",
                "passed": c26,
                "detail": "%d period pairing(s); dimensions differing per "
                          "pairing %s"
                          % (len(pair),
                             [len(p["dimensions_differing"]) for p in pair]),
            },
        ],
        "readings": {
            "coefficients_compared_12_vs_13": n_coeff,
            "ratio_13_over_12": sorted(str(r) for r in ratios),
            "cells_compared_12_vs_14": n_cells,
            "cells_differing_12_vs_14": len(diffs),
            "written_benefit_tables": 3,
            "distinct_benefit_functions": distinct_functions,
            "classes_written": len(classes),
            "clause_vectors": len(vectors),
            "colliding_vector_pairs": len(collisions),
            "group_a_merges_with_employee": {
                "dimension_cash_proportion": "one-tenth to two-fifths at "
                                             "applicable year 2029, reg "
                                             "13B(1)(b)(ii)",
                "dimension_benefit_table": "Thirteenth to Twelfth Schedule at "
                                           "applicable year 2029, reg 13C(2)(b)",
                "dimensions_still_separating_after_2029": [
                    "qualifying quantity, APE against wages",
                    "waiver top-up, 7/7/7/5/4 against 9/8/6/5/4",
                    "the exclusivity clause, and not also as the other",
                ],
            },
        },
        "coverage": coverage,
        "classes": classes,
        "internal_lines": INTERNAL_LINES,
        "group_partition": GROUP_PARTITION,
        "rival_pair_differences": pair,
    }

    return record


def main() -> None:
    record = build(CLASSES, COVERAGE, TWELFTH, THIRTEENTH, FOURTEENTH)

    out = Path(__file__).resolve().parents[1] / "results" / "b33_wis_schedules.json"
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for c in record["criteria"]:
        print("%-8s %-12s %-4s %s"
              % (c["name"], c["kind"], "PASS" if c["passed"] else "FAIL",
                 c["detail"]))
    print("written benefit tables 3, distinct benefit functions %d"
          % record["readings"]["distinct_benefit_functions"])
    print("wrote %s" % out.name)


def selftest() -> int:
    """Plant, for each criterion, an input that should make it fail.

    Discipline 11f: do not ask whether a criterion can fail, grow the failure.
    A criterion nobody has seen fail is not a criterion, and the one that
    matters here is B33-26, whose whole content is that two classes at one
    position do not receive the same terms.
    """
    import copy

    fails = []

    def check(label, record, expect_false):
        got = {c["name"]: c["passed"] for c in record["criteria"]}
        for name in expect_false:
            if got[name]:
                fails.append("%s: %s still passed" % (label, name))
        others = [n for n in got if n not in expect_false]
        for name in others:
            if not got[name]:
                fails.append("%s: %s failed and should not have" % (label, name))
        if not fails:
            print("  ok  %-34s %s"
                  % (label,
                     ("%s now fails" % ", ".join(expect_false))
                     if expect_false else "every criterion passes"))

    live = build(CLASSES, COVERAGE, TWELFTH, THIRTEENTH, FOURTEENTH)
    check("untouched inputs", live, [])

    # B33-26 and B33-3: give the two groups one clause vector.  This is the
    # world the rival describes, and both the counting law and the rival
    # criterion have to notice it.
    planted = copy.deepcopy(CLASSES)
    planted["8AC eligible Group B worker"]["2025 onward"] = copy.deepcopy(
        CLASSES["8AB eligible Group A worker"]["applicable year 2025-2028"])
    check("groups given one vector",
          build(planted, COVERAGE, TWELFTH, THIRTEENTH, FOURTEENTH),
          ["B33-26", "B33-3"])

    # There is no plant that fails B33-26 while B33-3 holds, and the reason is
    # worth stating rather than engineering around: any pairing that coincides
    # is a colliding vector, so on this carrier the two criteria fail together
    # by construction.  What separates them is not their arithmetic, it is what
    # they are asked about.  B33-3 is this frame's own reading over every pair
    # of written classes; B33-26 is a named rival's point prediction on the one
    # pair the fetched partition rule puts at a single position, and it carries
    # the premise and the entailment that make a failure mean something about
    # that rival rather than about this instrument.

    # B33-1: break the two-thirds ratio in one cell.
    bad13 = {k: list(v) for k, v in THIRTEENTH.items()}
    bad13[6] = list(bad13[6])
    bad13[6][0] = (bad13[6][0][0], bad13[6][0][1] + F(1))
    check("one coefficient moved",
          build(CLASSES, COVERAGE, TWELFTH, bad13, FOURTEENTH), ["B33-1"])

    # B33-2: break the Twelfth-Fourteenth identity in one cell.
    bad14 = {k: list(v) for k, v in FOURTEENTH.items()}
    bad14[1] = list(bad14[1])
    bad14[1][0] = (bad14[1][0][0], bad14[1][0][1] + F(1))
    check("one Fourteenth cell moved",
          build(CLASSES, COVERAGE, TWELFTH, THIRTEENTH, bad14), ["B33-2"])

    # B33-4: drop a page from the coverage table.
    short = copy.deepcopy(COVERAGE)
    lo, hi = short[-1]["pages"].split("-")
    short[-1]["pages"] = "%s-%d" % (lo, int(hi) - 1)
    check("one page dropped from coverage",
          build(CLASSES, short, TWELFTH, THIRTEENTH, FOURTEENTH), ["B33-4"])

    # B33-5: split a class without naming the provision that splits it.
    unnamed = copy.deepcopy(CLASSES)
    unnamed["8AA eligible employee"]["a second period"] = copy.deepcopy(
        CLASSES["8AA eligible employee"]["2025 onward"])
    unnamed["8AA eligible employee"]["a second period"][
        "cash_proportion_month"] = "one-fifth (no provision)"
    check("a class split with no provision named",
          build(unnamed, COVERAGE, TWELFTH, THIRTEENTH, FOURTEENTH), ["B33-5"])

    if fails:
        print("\nselftest FAILED")
        for x in fails:
            print("   " + x)
        return 1
    print("\nselftest passed")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest() if "--selftest" in sys.argv else (main() or 0))
