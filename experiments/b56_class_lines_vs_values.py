"""B56: how many class lines a rule names, against how many values the schedule writes.

B55 read the collisions inside one fee schedule. This reads a different gap: a
statute or an official notification names N class lines, and the schedule that
implements it writes fewer than N distinct values. The collapse can happen at
two separate steps, and they are recorded separately, because they are different
acts by different parties:

    step 1  the eligibility definition merges two named lines into one class
    step 2  two classes that stayed separate are given the same number

Amounts are in the smallest unit of their currency, as integers. A ceiling is
not a value: 49 U.S.C. 5307(c)(1)(D) caps the reduced fare at 50 percent of the
peak fare, and the cap is recorded beside the actual fare, never in place of it.
"""

import json
from pathlib import Path

CARRIERS = {
    "asi_monument_admission": {
        "jurisdiction": "India",
        "instrument": "Ministry of Culture decision, effective 2016-04-01",
        "source": "Press Information Bureau release, retrieved 2026-09-07",
        "currency": "INR paise",
        "note": "ASI's own site refuses automated retrieval by robots rule, so the "
                "current rate is not retrieved; this station reads the values this "
                "notification wrote, not today's counter price",
        # class lines the instrument itself names
        "class_lines": ["Indian citizens", "SAARC and BIMSTEC nationals",
                        "other foreign nationals"],
        # eligibility step: does the instrument itself merge any named line?
        "eligibility_classes": ["Indian citizens", "SAARC and BIMSTEC nationals",
                                "other foreign nationals"],
        # the values actually written, per eligibility class, for one good
        "good": "world heritage monument, one entry",
        "values": {"Indian citizens": 3000,
                   "SAARC and BIMSTEC nationals": 3000,
                   "other foreign nationals": 50000},
        "second_good": "other ticketed monument, one entry",
        "second_values": {"Indian citizens": 1500,
                          "SAARC and BIMSTEC nationals": 1500,
                          "other foreign nationals": 20000},
        "ceiling": None,
        "full_price_class": "other foreign nationals",
    },
    "mta_reduced_fare": {
        "jurisdiction": "United States, New York",
        "instrument": "49 U.S.C. 5307(c)(1)(D) as a condition of federal assistance",
        "source": "US Code retrieved 2026-09-07; MTA reduced-fare page retrieved "
                  "2026-09-07. FTA's own guidance page refuses automated retrieval "
                  "by robots rule and is recorded as not retrieved",
        "currency": "USD cents",
        "note": "the statute names three lines; MTA's eligibility page folds "
                "Medicare into the disability class, then prices what is left as one",
        "class_lines": ["seniors 65 and over", "persons with listed disabilities",
                        "Medicare card holders"],
        "eligibility_classes": ["65 or over",
                                "qualifying disability, including Medicare"],
        "good": "subway and local bus, one ride",
        "values": {"65 or over": 150, "qualifying disability, including Medicare": 150},
        "second_good": "express bus off peak, one ride",
        "second_values": {"65 or over": 360,
                          "qualifying disability, including Medicare": 360},
        "ceiling": {"rule": "not more than 50 percent of the peak hour fare",
                    "full_fare_cents": 300, "second_full_fare_cents": 725},
        "full_price_class": "everyone else",
    },
}


# The current Agra schedule, retrieved 2026-09-07 with a browser from
# tajmahal.gov.in, the official site of the Department of Tourism, Government of
# Uttar Pradesh. ASI's own site refuses automated retrieval; a browser is not a
# crawler, so this is the same document a visitor reads at the counter.
#
# Three class lines (Indian / foreigner and NRI / SAARC and BIMSTEC) crossed with
# eight monuments and two kinds of day. Amounts in whole rupees as printed.
AGRA_WEEKDAY = {                       # monument: (indian, foreigner, saarc)
    "Taj Mahal":            (50, 1100, 540),
    "Agra Fort":            (50,  650,  90),
    "Fatehpur Sikri":       (50,  610,  50),
    "Akbar's Tomb":         (30,  310,  30),
    "Itimad-Ud-Daulah":     (30,  310,  30),
    "Mehtab Bagh":          (25,  300,  25),
    "Ram Bagh":             (25,  300,  25),
    "Mariyam's Tomb":       (25,  300,  25),
}
AGRA_FRIDAY = {                        # Taj Mahal is closed on Friday, so it is absent
    "Agra Fort":            (40,  600,  40),
    "Fatehpur Sikri":       (40,  600,  40),
    "Akbar's Tomb":         (25,  300,  25),
    "Itimad-Ud-Daulah":     (25,  300,  25),
    "Mehtab Bagh":          (25,  300,  25),
    "Ram Bagh":             (25,  300,  25),
    "Mariyam's Tomb":       (25,  300,  25),
}
AGRA_SOURCE = ("tajmahal.gov.in, official site of the Department of Tourism, "
               "Government of Uttar Pradesh, retrieved 2026-09-07 by browser")


def agra_reading():
    out = {}
    for label, table in (("weekday_except_friday", AGRA_WEEKDAY), ("friday", AGRA_FRIDAY)):
        cells = [v for row in table.values() for v in row]
        per_mon = {m: len(set(row)) for m, row in table.items()}
        saarc_separates = [m for m, (i, f, s) in table.items() if s != i]
        out[label] = {
            "monuments": len(table), "class_lines": 3,
            "cells": len(cells), "distinct_values": len(set(cells)),
            "collisions": len(cells) - len(set(cells)),
            "values": sorted(set(cells)),
            "distinct_values_per_monument": per_mon,
            "monuments_where_saarc_is_its_own_value": sorted(saarc_separates),
            "n_saarc_separates": len(saarc_separates),
        }
    return out


# Four agencies that all take the same federal condition, checked 2026-09-07.
# 49 U.S.C. 5307(c)(1)(D) caps the reduced fare at half the peak fare for three
# named classes. It does NOT require the three to pay the same as each other, so
# "one value for all of them" is each agency's own choice, and an agency that
# priced them apart would read 3 -> 3. That is the way this reading can fail.
#
# checked=False means the class lines are read but the amounts were not: those
# agencies do not get a value count (rule 11c).
TRANSIT_AGENCIES = {
    "mta_new_york": {
        "lines": ["65 or over", "listed disability", "Medicare card"],
        "cents": {"subway and local bus": [150]},
        "checked": True,
        "source": "mta.info reduced-fare page, retrieved 2026-09-07",
        "quote": "seniors and people with disabilities receive the same reduced fares",
    },
    "mbta_boston": {
        "lines": ["65 or over", "person with a disability", "Medicare card",
                  "middle and high school student", "low income 18-64"],
        "cents": {"subway": [110], "bus": [85]},
        "checked": True,
        "source": "mbta.com/fares/reduced, retrieved 2026-09-07",
        "quote": "No matter which type of reduced fare card you have, all reduced "
                 "fare prices are the same",
        # A second block of named lines on the same page, priced at zero. They are
        # part of the same programme and they are what makes this carrier read
        # 10 blocks -> 3 values rather than 6 -> 2.
        "free_lines": ["children 11 and younger", "legally blind",
                       "military personnel", "on-duty police and firefighters",
                       "government officials"],
        "free_cents": 0,
        # The operator DOES condition on which card is held, on a different good.
        # This is the answer to "the farebox cannot tell the cards apart".
        "conditions_on_card_elsewhere": {
            "good": "The RIDE, ADA one-way",
            "cents": 170,
            "open_to": ["65 or over", "low income 18-64"],
            "closed_to": ["person with a disability", "Medicare card",
                          "middle and high school student"],
            "quote": "With senior or income-eligible reduced fare card",
        },
    },
    "nj_transit": {
        "lines": ["62 or over (65 to or from Metro-North stations)",
                  "person with a disability", "military personnel",
                  "Medicare card", "veteran with service-connected disability"],
        "cents": None,
        "checked": False,
        "source": "njtransit.com reduced-fare page, retrieved 2026-09-07",
        "quote": "savings of 50% or more on a regular one-way fare; the page gives "
                 "no dollar amounts, so the value count is NOT READ",
    },
    "mta_maryland": {
        "lines": ["65 or over", "person with a disability", "Medicare card"],
        # the published table has one column headed "Senior/Disability", so the
        # three federal lines arrive as a single priced class
        "cents": {"single trip": [100], "day pass": [230], "monthly pass": [2300]},
        "checked": True,
        "source": "mta.maryland.gov/regular-fares, retrieved 2026-09-07 by browser",
        "quote": "the fare table prints one column headed Senior/Disability; full "
                 "fare single trip is 200 cents, so the reduced single trip sits "
                 "exactly at the federal ceiling, while the monthly pass at 2300 "
                 "against 7700 is far below it",
        # a separate class line the operator drew itself, priced apart
        "own_lines_priced_apart": {"student single trip": 150},
        "full_fare_cents": {"single trip": 200, "day pass": 460, "monthly pass": 7700},
        "not_the_same_commodity": {"mobility single trip": 220},
    },
}


# ----------------------------------------------------------------------------
# The rival for this station, named, with its point prediction written out.
#
# Third-degree price discrimination (Pigou 1920; the textbook three conditions
# as stated in Meurer & Depoorter 2019 and in the A-level entry quoted at
# b30_results.md B30-22 chunk 31): a seller with market power, able to sort
# buyers into groups by their price elasticity of demand and to block resale
# between the groups, charges each group its own price. Two groups get the same
# price when, and only when, their elasticities are equal.
#
# All three conditions hold here and none of them is in dispute. A transit
# agency is a price maker on its own network; it sorts by issuing a different
# photo card per class and checking it at the farebox; the cards are
# non-transferable, so resale is blocked. The sorting cost is paid in full.
#
# The point prediction is NOT "every named line gets its own price", because the
# rival is silent where elasticities happen to coincide. The prediction that can
# be read without measuring any elasticity is this one:
#
#     elasticity is a property of the rider, not of the operator,
#     so the SAME pair of segments must be judged the same way by every operator.
#
# Two operators that draw the same two lines and then merge them in one city and
# price them apart in the other cannot both be reading an elasticity. That is a
# contradiction for the rival whatever the elasticities are, and it costs zero
# data to check.
#
# This is a different cell from B30-22 chunk 19, and the two are complements.
# There the cause (valuation heterogeneity) was ABSENT and the prices SPLIT, and
# the classical account was recorded as not wrong but simply not looking: cell D.
# Here the cause is PRESENT and named by the carrier itself, the classical
# account has every reason to be looking, and the prices MERGE. Cell B, if the
# contradiction is real.
RIVAL = ("third-degree price discrimination: a seller that has paid to sort and "
         "has blocked resale prices each segment by its own elasticity, so two "
         "segments share a price only when their elasticities are equal, and "
         "elasticity is a property of the rider, not of the operator")

# The pair, read from the two operators' own pages 2026-09-07. Both operators
# draw both lines and issue a separate credential for each.
STUDENT_VS_SENIOR = {
    "mbta_boston": {
        "senior_cents": {"subway": 110, "bus": 85},
        "student_cents": {"subway": 110, "bus": 85},
        "student_line": "some middle and high school students, at schools "
                        "enrolled in the MBTA Student Pass Program (S-Card, M7)",
        "verdict": "merged",
        "via": "the page's sentence that all reduced fare prices are the same; "
               "the student amount is not printed as a separate cell",
        "source": "mbta.com/fares/reduced, retrieved 2026-09-07",
    },
    "mta_maryland": {
        "senior_cents": {"single trip": 100},
        "student_cents": {"single trip": 150},
        "student_line": "students aged 13 to 21 at participating private, "
                        "parochial, or Baltimore County public schools, with an "
                        "MTA Student Transit ID",
        "verdict": "priced apart",
        "via": "the fare table prints Student as its own column: full 200, "
               "senior/disability 100, student 150",
        "source": "mta.maryland.gov/regular-fares and /student-fares, "
                  "retrieved 2026-09-07 by browser",
    },
}

# Not the same object, recorded so that nobody reads it as one. Baltimore City
# Public Schools students ride free, and that is a school-system-funded transfer,
# not the operator pricing a segment. It is left out of the pair above.
STUDENT_THIRD_PARTY_PAYER = {
    "mta_maryland": "Baltimore City Public Schools middle and high school "
                    "students ride free; children 12 and under ride free with no "
                    "credential at all. Neither is the operator's own price.",
}


def rival_reading():
    """Print the object: per operator, blocks named and distinct values produced,
    then the pair that both operators draw. No threshold anywhere."""
    per_operator = {}
    for name, a in sorted(TRANSIT_AGENCIES.items()):
        if not a["checked"]:
            per_operator[name] = {"verdict": "not read", "checked": False}
            continue
        free = a.get("free_lines", [])
        blocks = len(a["lines"]) + len(free) + 1          # + the residual full-fare block
        values = {}
        for g, v in a["cents"].items():
            n = len(set(v)) + 1                           # + the full fare itself
            if free:
                n += 1                                    # + zero
            values[g] = n
        vmax = max(values.values())
        per_operator[name] = {
            "checked": True,
            "blocks_named": blocks,
            "reduced_lines": len(a["lines"]),
            "free_lines": len(free),
            "distinct_values_per_good": values,
            "max_distinct_values": vmax,
            "collapse": blocks - vmax,
            "rival_point_prediction": blocks,
            "rival_hits": vmax == blocks,
        }
    read = [k for k, v in per_operator.items() if v["checked"]]
    hits = [k for k in read if per_operator[k]["rival_hits"]]

    # the elasticity-free half: the same pair, judged by two operators
    verdicts = {k: v["verdict"] for k, v in STUDENT_VS_SENIOR.items()}
    distinct = sorted(set(verdicts.values()))
    pair = {
        "pair": "middle/high school student  vs  65 or over",
        "operators": verdicts,
        "detail": STUDENT_VS_SENIOR,
        "third_party_payer_excluded": STUDENT_THIRD_PARTY_PAYER,
        "n_operators": len(verdicts),
        "n_distinct_verdicts": len(distinct),
        "contradiction": len(distinct) > 1,
        # nominal vs independent, D22: the three federal lines are merged
        # everywhere, so student-vs-senior, student-vs-disability and
        # student-vs-Medicare are three names for one fact.
        "nominal_contradicting_pairs": 3,
        "independent_contradictions": 1,
    }
    return {"rival": RIVAL, "per_operator": per_operator,
            "read": len(read), "rival_hits": len(hits),
            "operators_where_rival_hits": hits, "same_pair_two_operators": pair}


def agency_reading():
    out = {}
    for name, a in sorted(TRANSIT_AGENCIES.items()):
        r = {"class_lines": len(a["lines"]), "lines": a["lines"],
             "source": a["source"], "quote": a["quote"], "checked": a["checked"]}
        if a["checked"]:
            per_good = {g: len(set(v)) for g, v in a["cents"].items()}
            r["distinct_values_per_good"] = per_good
            r["max_distinct_values"] = max(per_good.values())
            r["collapse"] = len(a["lines"]) - r["max_distinct_values"]
            r["verdict"] = "collapsed to one value" if r["max_distinct_values"] == 1 \
                           else "prices the classes apart"
        else:
            r["verdict"] = "amounts not read"      # rule 11c: no verdict from an unread cell
        out[name] = r
    return out


def main():
    rows = {}
    for name, c in CARRIERS.items():
        n_lines = len(c["class_lines"])
        n_elig = len(c["eligibility_classes"])
        vals = sorted(set(c["values"].values()))
        vals2 = sorted(set(c["second_values"].values()))
        merged_at_eligibility = n_lines - n_elig
        merged_at_value = n_elig - len(vals)
        rows[name] = {
            "jurisdiction": c["jurisdiction"], "instrument": c["instrument"],
            "source": c["source"], "good": c["good"],
            "class_lines_named": n_lines,
            "eligibility_classes": n_elig,
            "distinct_values": len(vals),
            "collapse_at_eligibility_step": merged_at_eligibility,
            "collapse_at_value_step": merged_at_value,
            "total_collapse": n_lines - len(vals),
            "values": c["values"], "second_good": c["second_good"],
            "second_distinct_values": len(vals2), "second_values": c["second_values"],
            "ceiling": c["ceiling"], "note": c["note"],
        }
        if c["ceiling"]:
            full = c["ceiling"]["full_fare_cents"]
            rows[name]["actual_share_of_full"] = min(vals) / full
            full2 = c["ceiling"]["second_full_fare_cents"]
            rows[name]["second_actual_share_of_full"] = min(vals2) / full2

    crit = {}
    bad = [(k, g, v) for k, c in CARRIERS.items() for g in ("values", "second_values")
           for v in c[g].values() if not isinstance(v, int) or v < 0]
    KIND = {"B56-1": "premise", "B56-2": "instrument",
            "B56-3": "bookkeeping", "B56-4": "bookkeeping",
            "B56-5": "rival", "B56-6": "own_reading"}

    crit["B56-1"] = {"passed": not bad,
        "name": "every price is an exact integer in the smallest currency unit",
        "detail": "%d carriers, %d amounts, %d not exact"
                  % (len(CARRIERS),
                     sum(len(c["values"]) + len(c["second_values"]) for c in CARRIERS.values()),
                     len(bad))}
    ident = all(r["total_collapse"] == r["collapse_at_eligibility_step"]
                + r["collapse_at_value_step"] for r in rows.values())
    crit["B56-2"] = {"passed": ident,
        "name": "collapse = lines named - distinct values, and it splits into the two steps",
        "detail": "; ".join("%s: %d lines -> %d values, collapse %d"
                            % (k, r["class_lines_named"], r["distinct_values"],
                               r["total_collapse"]) for k, r in sorted(rows.items()))}
    crit["B56-3"] = {"passed": all("collapse_at_eligibility_step" in r
                                   and "collapse_at_value_step" in r for r in rows.values()),
        "name": "the eligibility step and the pricing step are recorded separately",
        "detail": "; ".join("%s: %d at eligibility, %d at pricing"
                            % (k, r["collapse_at_eligibility_step"], r["collapse_at_value_step"])
                            for k, r in sorted(rows.items()))}
    noprov = [k for k, c in CARRIERS.items() if not c.get("source") or not c.get("instrument")]
    crit["B56-4"] = {"passed": not noprov,
        "name": "every carrier names its instrument and its retrieval",
        "detail": "%d carriers, %d without provenance" % (len(rows), len(noprov))}

    agra = agra_reading()
    agencies = agency_reading()
    riv = rival_reading()

    # B56-5, kind rival. The rival's point prediction is that a seller which has
    # paid to sort gives each sorted block its own price, i.e. values == blocks.
    # Zero threshold: the reading is the hit count against the read count.
    # Three states, and the middle one maps to no verdict (rule 11c):
    #   every read operator hits          -> the rival is right here, FAIL
    #   no read operator hits             -> PASS
    #   nothing read                      -> undetermined, no verdict
    n_read, n_hit = riv["read"], riv["rival_hits"]
    if n_read == 0:
        b5_pass, b5_state = None, "undetermined: no operator's amounts were read"
    elif n_hit == n_read:
        b5_pass, b5_state = False, "the rival's point prediction holds everywhere it was read"
    else:
        b5_pass, b5_state = True, "the rival's point prediction fails where it was read"
    crit["B56-5"] = {"passed": b5_pass,
        "name": "rival: a seller that has paid to sort gives each sorted block its "
                "own price, so distinct values == blocks named",
        "detail": "%s; %d of %d read operators hit it. %s" % (
            b5_state, n_hit, n_read,
            "; ".join("%s %d blocks -> %d values" % (k, v["blocks_named"],
                                                     v["max_distinct_values"])
                      for k, v in sorted(riv["per_operator"].items()) if v["checked"]))}

    # B56-6, kind own_reading. The elasticity-free half. Elasticity belongs to the
    # rider, so one pair of segments cannot be merged by one operator and priced
    # apart by another. Three states again:
    #   the two operators disagree  -> the contradiction is on the record, PASS
    #   the two operators agree     -> no contradiction, FAIL, and the arm folds
    #   fewer than two read         -> undetermined
    pr = riv["same_pair_two_operators"]
    if pr["n_operators"] < 2:
        b6_pass, b6_state = None, "undetermined: fewer than two operators read on this pair"
    elif pr["contradiction"]:
        b6_pass, b6_state = True, "the same pair is judged two different ways"
    else:
        b6_pass, b6_state = False, "both operators judge the pair the same way"
    crit["B56-6"] = {"passed": b6_pass,
        "name": "the same pair of segments, drawn and credentialed by two operators "
                "under the same federal condition, gets the same verdict",
        "detail": "%s: %s. nominal contradicting pairs %d, independent %d" % (
            b6_state,
            ", ".join("%s %s" % (k, v) for k, v in sorted(pr["operators"].items())),
            pr["nominal_contradicting_pairs"], pr["independent_contradictions"])}

    out = {"stage": "B56",
           "transit_agencies": agencies,
           "agra_current_schedule": {"source": AGRA_SOURCE, "reading": agra},
           "config": {"n_carriers": len(rows), "amounts_in": "smallest currency unit",
                      "ceiling_is_not_a_value": True,
                      "carriers": sorted(rows)},
           "rival_arm": riv,
           "criteria": [{"name": k, "passed": v["passed"], "detail": v["detail"],
                         "kind": KIND[k], "criterion": v["name"]}
                        for k, v in sorted(crit.items())],
           "rows": rows}
    dest = Path(__file__).resolve().parents[1] / "results" / "b56_class_lines_vs_values.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    for k, r in sorted(rows.items()):
        print("=== %s (%s)" % (k, r["jurisdiction"]))
        print("    instrument      %s" % r["instrument"])
        print("    class lines     %d  ->  eligibility classes %d  ->  distinct values %d"
              % (r["class_lines_named"], r["eligibility_classes"], r["distinct_values"]))
        print("    collapse        %d total = %d at the eligibility step + %d at the pricing step"
              % (r["total_collapse"], r["collapse_at_eligibility_step"],
                 r["collapse_at_value_step"]))
        print("    good            %s" % r["good"])
        for cls, v in sorted(r["values"].items(), key=lambda x: x[1]):
            print("        %-46s %d" % (cls, v))
        if r.get("ceiling"):
            print("    ceiling         %s" % r["ceiling"]["rule"])
            print("    actual share    %.4f of full on %s; %.4f on %s"
                  % (r["actual_share_of_full"], r["good"],
                     r["second_actual_share_of_full"], r["second_good"]))
        print()
    print("=== the current Agra schedule (browser, 2026-09-07)")
    for label, r in sorted(agra.items()):
        print("    %-24s %d monuments x 3 class lines = %d cells -> %d values, %d collisions"
              % (label, r["monuments"], r["cells"], r["distinct_values"], r["collisions"]))
        print("        values          %s" % r["values"])
        print("        SAARC is its own value at %d of %d monuments: %s"
              % (r["n_saarc_separates"], r["monuments"],
                 ", ".join(r["monuments_where_saarc_is_its_own_value"]) or "none"))
        byn = {}
        for m, n in r["distinct_values_per_monument"].items():
            byn.setdefault(n, []).append(m)
        for n in sorted(byn):
            print("        %d distinct values at %d monument(s): %s"
                  % (n, len(byn[n]), ", ".join(sorted(byn[n]))))
    print("=== four agencies under the same federal condition")
    print("    %-16s %-6s %-8s %s" % ("agency", "lines", "values", "verdict"))
    for k, r in sorted(agencies.items()):
        print("    %-16s %-6d %-8s %s"
              % (k, r["class_lines"],
                 r.get("max_distinct_values", "-"), r["verdict"]))
    read = [r for r in agencies.values() if r["checked"]]
    print("    read %d of %d; of those, %d collapsed to one value, %d priced the classes apart"
          % (len(read), len(agencies),
             sum(1 for r in read if r["max_distinct_values"] == 1),
             sum(1 for r in read if r["max_distinct_values"] > 1)))
    print()
    print("=== the rival arm")
    print("    rival: %s" % riv["rival"])
    for k, v in sorted(riv["per_operator"].items()):
        if not v["checked"]:
            print("    %-16s not read" % k); continue
        print("    %-16s %2d blocks (%d reduced + %d free + 1 full) -> %d values, "
              "collapse %d, rival hits: %s"
              % (k, v["blocks_named"], v["reduced_lines"], v["free_lines"],
                 v["max_distinct_values"], v["collapse"], v["rival_hits"]))
    pr = riv["same_pair_two_operators"]
    print("    pair            %s" % pr["pair"])
    for k, v in sorted(pr["operators"].items()):
        d = pr["detail"][k]
        print("        %-16s %-13s %s" % (k, v, d["via"]))
    print()
    for k, v in sorted(crit.items()):
        state = "PASS" if v["passed"] is True else ("FAIL" if v["passed"] is False else "----")
        print("%-8s %-5s %-12s %s" % (k, state, KIND[k], v["detail"]))
    # rule 11d: report by kind, never one total
    bykind = {}
    for k, v in crit.items():
        bykind.setdefault(KIND[k], []).append(v["passed"])
    print("by kind: " + "; ".join(
        "%s %d/%d pass, %d undetermined" % (kd, sum(1 for x in s if x is True),
                                            len(s), sum(1 for x in s if x is None))
        for kd, s in sorted(bykind.items())))
    print("wrote", dest.name)
    return 0 if all(v["passed"] is not False for v in crit.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
